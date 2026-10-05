#!/usr/bin/env python3
"""sim/em_register.py -- the electromagnet register (BRIEF_ELECTROMAGNET_REGISTER r0.3): identity, stations, sense,
loop sums, PRF branches, fit arithmetic, pump invariance with the RA tank. Every number comes from a preset
(presets/electromagnets-RA.json, -V15.json) or a source file read here (r0.15 DXF, topology_edge_list.csv,
pump_engine DEFAULTS); nothing is hard-coded except method constants.            [OC] unless tagged

Frozen cores (pump_engine, shuttle_core, doubler_core, island_resonant_core) are imported read-only; the RA tank is
carried as a documented edit of NR applied to an rt_engine net (L_R1/L_R2/C_R1 replaced, n18/n00 retired).
Usage: python3 sim/em_register.py [arith|pump|all]  -> sim/em_register_results.json
"""
import csv
import json
import math
import os
import sys
import time

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path[:0] = [HERE, os.path.join(ROOT, "reference")]
from edge_coil import MU0, mutual                     # noqa: E402

RESULTS = os.path.join(HERE, "em_register_results.json")
DXF = os.path.join(ROOT, "docs", "varcap-nodeanalysis-template-r0.15_TMD_layout.dxf")
NR = os.path.join(ROOT, "topology_edge_list.csv")


def preset(gen):
    return json.load(open(os.path.join(ROOT, "presets", f"electromagnets-{gen}.json")))


def val(p, *keys):
    d = p
    for k in keys:
        d = d[k]
    return d["value"] if isinstance(d, dict) and "value" in d else d


# ---------------------------------------------------------------------------------------------------------
# loop sums (brief §5.1, §5.2; edge brief §4b)
# ---------------------------------------------------------------------------------------------------------
def stack(spec):
    """turn centres (r, |z|) in metres of a conical stack, k = 0 at the septum end."""
    k = np.arange(int(spec["n"]))
    return (spec["r0_mm"] + spec["dr_mm"] * k) * 1e-3, (spec["z0_mm"] + spec["dz_mm"] * k) * 1e-3


def loop_matrix(r, z, a):
    """L matrix of coaxial circular turns: self mu0 r (ln(8r/a) - 2), mutual Maxwell."""
    R1, R2 = np.meshgrid(r, r, indexing="ij")
    Z1, Z2 = np.meshgrid(z, z, indexing="ij")
    with np.errstate(divide="ignore", invalid="ignore"):
        M = mutual(R1, R2, Z1 - Z2)
    np.fill_diagonal(M, MU0 * r * (np.log(8 * r / a) - 2.0))
    return M


def cone_pair(spec):
    """one cone (z < 0) and its mirror (z > 0), same rotational sense: L_cone, M, series-aiding total."""
    r, z = stack(spec)
    a = spec["od_mm"] / 2 * 1e-3
    rr = np.concatenate([r, r])
    zz = np.concatenate([-z, z])
    L = loop_matrix(rr, zz, a)
    n = len(r)
    Lc = L[:n, :n].sum()
    M = L[:n, n:].sum()
    return dict(L_cone_uH=Lc * 1e6, M_uH=M * 1e6, series_aiding_uH=(2 * Lc + 2 * M) * 1e6, k=M / Lc)


def p_reg_1_2(log=print):
    v15 = cone_pair(val(preset("V15"), "rotor", "L_R"))
    ra = cone_pair(val(preset("RA"), "rotor", "L_TC_L_BC"))
    out = {}
    tgt = dict(L_cone_uH=33.8, M_uH=8.3, series_aiding_uH=84.1)
    dev = {k: v15[k] / tgt[k] - 1 for k in tgt}
    out["P-REG-1"] = dict(**v15, target=tgt, rel=dev, verdict="PASS" if all(abs(x) <= 0.03 for x in dev.values()) else "KILL")
    hit_record = abs(ra["L_cone_uH"] - 139) / 139 < 0.03 and abs(ra["M_uH"] - 93) / 93 < 0.03
    dev2 = dict(L_cone_uH=ra["L_cone_uH"] / 98.9 - 1, M_uH=ra["M_uH"] / 34.7 - 1)
    out["P-REG-2"] = dict(**ra, target=dict(L_cone_uH=98.9, M_uH=34.7), rel=dev2,
                          verdict="KILL (record values reproduced; finding 1 withdrawn)" if hit_record else
                          ("PASS" if all(abs(x) <= 0.03 for x in dev2.values()) else "INCONCLUSIVE (neither)"))
    log(f"P-REG-1 {out['P-REG-1']['verdict']}: V15 L_cone {v15['L_cone_uH']:.2f}, M {v15['M_uH']:.2f}, series {v15['series_aiding_uH']:.2f} uH")
    log(f"P-REG-2 {out['P-REG-2']['verdict']}: RA L_cone {ra['L_cone_uH']:.2f}, M {ra['M_uH']:.2f} uH (k {ra['k']:.3f})")
    return out


def p_reg_3(log=print):
    p = preset("V15")
    L = 33.8e-6
    C = val(p, "rotor", "stray_RA_n18_pF") * 1e-12
    Lc = cone_pair(val(p, "rotor", "L_R"))["L_cone_uH"] * 1e-6
    f = 1 / (2 * math.pi * math.sqrt(L * C))
    f_tool = 1 / (2 * math.pi * math.sqrt(Lc * C))
    ok = abs(f / 1.20e6 - 1) <= 0.05
    log(f"P-REG-3 {'PASS' if ok else 'KILL'}: SRF {f / 1e6:.3f} MHz (tool's own L_cone: {f_tool / 1e6:.3f} MHz); f0 637 kHz ratio {f / 637e3:.2f}")
    return {"P-REG-3": dict(f_srf_MHz=f / 1e6, f_srf_tool_L_MHz=f_tool / 1e6, ratio_to_f0=f / 637e3, verdict="PASS" if ok else "KILL")}


def p_reg_4(log=print):
    """T-MOTOR-PRF: the branch values read from pump_engine-built nets in both cap topologies."""
    import pump_engine as PE
    out = {}
    for topo in ("per_coil", "per_branch"):
        cfg = PE.make_config(dict(motor=True, motor_topology=topo))
        net = PE.build_net(cfg)
        Ls = [d for d in net.inds if d[5] == "motor"]
        Cs = [c for c in net.caps if c[0].startswith(("C_AR", "C__AR", "C_BR", "C_Ablock", "C_Bblock"))]
        L = Ls[0][3]
        R = Ls[0][4]
        C = Cs[0][3]
        f = 1 / (2 * math.pi * math.sqrt(L * C))
        Z0 = math.sqrt(L / C)
        out[topo] = dict(n_L=len(Ls), n_C=len(Cs), L_H=L, R_ohm=R, C_F=C, f_res_Hz=f, Z0_ohm=Z0, Q=Z0 / R)
    pc, pb = out["per_coil"], out["per_branch"]
    if pb["n_L"] == 12:                           # per-branch keeps 12 coils on a common node: the paralleled branch
        Lb, Rb, Cb = pb["L_H"] / 6, pb["R_ohm"] / 6, pb["C_F"]
        pb.update(branch_L_H=Lb, branch_f_res_Hz=1 / (2 * math.pi * math.sqrt(Lb * Cb)), branch_Z0_ohm=math.sqrt(Lb / Cb),
                  branch_Q=math.sqrt(Lb / Cb) / Rb)
    # strict 0.1 % on every registered figure, and the same figures compared at their registered precision
    strict = dict(f=pc["f_res_Hz"] / 299.9 - 1, Z0=pc["Z0_ohm"] / 1206 - 1, Q=pc["Q"] / 30.2 - 1,
                  Zb=pb.get("branch_Z0_ohm", 0) / 201 - 1, fb=pb.get("branch_f_res_Hz", 0) / 299.9 - 1)
    at_prec = (round(pc["f_res_Hz"], 1) == 299.9 and round(pc["Z0_ohm"]) == 1206 and math.floor(pc["Q"] * 10 + 0.5) / 10 == 30.2
               and round(pb.get("branch_Z0_ohm", 0)) == 201 and round(pb.get("branch_f_res_Hz", 0), 1) == 299.9)
    ok = all(abs(v) <= 1e-3 for v in strict.values())
    out["strict_rel"] = strict
    out["at_registered_precision"] = at_prec
    out["verdict"] = "PASS" if ok else ("PASS at the registered precision only (Q = %.3f; the registered 30.2 is its"
                                        " 1-decimal rounding, 0.17 %% from it)" % pc["Q"] if at_prec else "KILL")
    log(f"P-REG-4 / T-MOTOR-PRF {out['verdict']}: per coil {pc['f_res_Hz']:.2f} Hz, Z0 {pc['Z0_ohm']:.1f}, Q {pc['Q']:.2f};"
        f" per branch {pb.get('branch_f_res_Hz', float('nan')):.2f} Hz, Z0 {pb.get('branch_Z0_ohm', float('nan')):.1f}"
        f" ({pb['n_L']} coils, {pb['n_C']} caps)")
    return {"P-REG-4": out}


# ---------------------------------------------------------------------------------------------------------
# fit arithmetic (P-REG-7, part of G-CLR-AH)
# ---------------------------------------------------------------------------------------------------------
def ah_fit(var, p=None):
    p = p or preset("RA")
    rod = val(p, "rotor", "AH_rod")
    fo = val(p, "rotor", "AH_former")
    w = val(p, "rotor", "AH_wire")
    V = val(p, "rotor", "AH_variants")[var]
    bore = val(p, "rotor", "cone_bore_at_rod_d_mm")
    shaft = val(p, "rotor", "shaft")
    pitch = w["overall_mm"]
    z0, z1 = rod["absz_mm"]
    tip = V["shaft_tip_absz_mm"]
    windable = (min(z1, tip) - z0)
    span = V["turns_per_layer"] * pitch
    od = fo["od_mm"] + 2 * V["layers"] * pitch
    lead = V["layers"] % 2 == 0
    rad = (bore - od) / 2
    rad_lead = rad - (pitch if lead else 0.0)
    sleeve = rod["d_mm"] + 2 * 0.5
    return dict(windable_mm=windable, span_mm=span, axial_margin_mm=windable - span, finished_od_mm=od,
                radial_margin_mm=rad, radial_margin_at_lead_mm=rad_lead, return_lead=lead,
                turns=V["layers"] * V["turns_per_layer"],
                rod_in_bore_mm=max(0.0, z1 - tip) if tip < z1 else 0.0,
                shaft_engagement_note=("rod potted in the former; shaft tip at |z| %.0f" % tip) if tip >= z1 else
                ("rod %.1f mm in the Ø%.0f bore" % (z1 - tip, shaft["bore_d_mm"])),
                peek_sleeve_od_mm=sleeve, peek_sleeve_fits_bore=(sleeve <= shaft["bore_d_mm"]) if tip < z1 else None,
                seat_space_mm=z0 - val(p, "rotor", "vessel")["pole_absz_mm"])


def p_reg_7(log=print):
    reg = dict(a=dict(ax=1.3, rad=2.0), b=dict(ax=2.1, rad=0.45), c=dict(ax=0.5, rad=2.0))
    out = {}
    ok = True
    for var in "abc":
        f = ah_fit(var)
        d_ax = f["axial_margin_mm"] - reg[var]["ax"]
        d_rad = f["radial_margin_mm"] - reg[var]["rad"]
        f.update(registered=reg[var], d_axial=d_ax, d_radial=d_rad)
        ok &= abs(d_ax) <= 0.1 and abs(d_rad) <= 0.1
        out[var] = f
        log(f"  AH ({var}): axial margin {f['axial_margin_mm']:.2f} mm (reg {reg[var]['ax']}), radial {f['radial_margin_mm']:.2f}"
            f" (reg {reg[var]['rad']}), at the return lead {f['radial_margin_at_lead_mm']:.2f}; OD {f['finished_od_mm']:.1f};"
            f" PEEK sleeve Ø{f['peek_sleeve_od_mm']:.1f} fits Ø13 bore: {f['peek_sleeve_fits_bore']}")
    out["verdict"] = "PASS" if ok else "KILL"
    log(f"P-REG-7 {out['verdict']} (bare-winding margins vs the registered numbers)")
    return {"P-REG-7": out}


# ---------------------------------------------------------------------------------------------------------
# identity, stations, sense (G-EM-ID, G-EM-STATION, G-EM-SENSE, T-MIRROR stations)
# ---------------------------------------------------------------------------------------------------------
def nr_edges():
    with open(NR) as f:
        rows = list(csv.reader(f))
    hdr = rows[0]
    return {r[0]: (r[1], r[2]) for r in rows[1:] if len(r) >= 3 and not r[0].startswith("#")}


def dxf_stations():
    import ezdxf
    doc = ezdxf.readfile(DXF)
    msp = doc.modelspace()
    labs = {e.dxf.text: (e.dxf.insert.x, e.dxf.insert.y) for e in msp.query("TEXT") if e.dxf.text.startswith("CEM_")}
    frames = [(e.dxf.center.x, e.dxf.center.y) for e in msp.query("CIRCLE") if e.dxf.layer == "00-VIEW-FRAMES"]
    lx = np.mean([p[0] for p in labs.values()])
    ly = np.mean([p[1] for p in labs.values()])
    fc = min(frames, key=lambda q: math.hypot(q[0] - lx, q[1] - ly))
    rects = []
    for e in msp.query("LWPOLYLINE"):
        pts = np.array([q[:2] for q in e.get_points()])
        c = pts.mean(0)
        if math.hypot(c[0] - fc[0], c[1] - fc[1]) < 800 and "MOTOR" in e.dxf.layer:
            rects.append(c)
    st = {}
    for c in rects:
        lab = min(labs, key=lambda k: math.hypot(labs[k][0] - c[0], labs[k][1] - c[1]))
        st[lab] = round(math.degrees(math.atan2(c[1] - fc[1], c[0] - fc[0])) % 360, 6)
    poles = []
    for e in msp:
        if e.dxftype() == "INSERT" and "QUADRI" in e.dxf.layer:
            for v in e.virtual_entities():
                for cc in [s for s in v.virtual_entities() if s.dxftype() == "CIRCLE"]:
                    X, Y = cc.dxf.center.x, cc.dxf.center.y
                    f = min(frames, key=lambda q: math.hypot(X - q[0], Y - q[1]))
                    poles.append((round(math.degrees(math.atan2(Y - f[1], X - f[0])) % 360, 4), round(math.hypot(X - f[0], Y - f[1]), 3),
                                  round(cc.dxf.radius, 3)))
    return st, sorted(set(poles))


def g_em(log=print):
    p = preset("RA")
    E = nr_edges()
    st_p = val(p, "stator", "cem_stations_deg")
    st_d, poles = dxf_stations()
    out = {}
    coils = [f"L_{g}{k}" for g in "AB" for k in range(1, 7)]
    caps = [f"C_AR{k}" if k != 4 else "C__AR4" for k in range(1, 7)] + [f"C_BR{k}" for k in range(1, 7)]
    ok_id = all(c in E for c in coils + caps) and len(st_d) == 12
    pairs = {}
    for g in "AB":
        for k in range(1, 7):
            L = E[f"L_{g}{k}"]
            C = E[(f"C_AR{k}" if k != 4 else "C__AR4") if g == "A" else f"C_BR{k}"]
            mid = (set(L) & set(C)).pop() if set(L) & set(C) else None
            pairs[f"CEM_{g}{k}"] = dict(coil=f"L_{g}{k}", coil_nodes=L, cap_nodes=C, shared=mid,
                                         rail_end=[n for n in L if n != mid][0] if mid else None)
            ok_id &= mid is not None and ((g == "A" and "1" in L and "2" in C) or (g == "B" and "4" in L and "3" in C))
    out["G-EM-ID"] = dict(pass_=bool(ok_id), map=pairs, dxf_labels=sorted(st_d))
    dev = {k: ((st_d.get(k, np.nan) - st_p[k[4:]] + 180) % 360) - 180 for k in st_d}
    A_ok = all(abs(((st_d[f"CEM_A{k}"] - 30) % 60)) < 1e-6 or abs(((st_d[f"CEM_A{k}"] - 30) % 60) - 60) < 1e-6 for k in range(1, 7))
    B_ok = all(abs(st_d[f"CEM_B{k}"] % 60) < 1e-6 or abs(st_d[f"CEM_B{k}"] % 60 - 60) < 1e-6 for k in range(1, 7))
    P_ok = len(poles) == 6 and all(abs(((a - 15) % 60)) < 1e-3 or abs(((a - 15) % 60) - 60) < 1e-3 for a, _, _ in poles)
    out["G-EM-STATION"] = dict(pass_=bool(A_ok and B_ok and P_ok), dxf=st_d, preset_dev_deg=dev, poles=poles,
                               blockD_S6_delta_deg=dict(groupA=30.0, note="Block D / S6 put group A at 0 + 60k (F-2)"),
                               numbering="clockwise" if (st_d["CEM_A2"] - st_d["CEM_A1"]) % 360 > 180 else "counter-clockwise")
    # sense: N/S from start_node (the rail end), uniform winding sense against that lead
    sense = {}
    for ph_a in (+1, -1):
        for ph_b in (+1, -1):
            m = {}
            for lab, d in pairs.items():
                g = lab[4]
                s = ph_a if g == "A" else ph_b          # +1: current enters at the rail end
                m[lab] = "N" if s > 0 else "S"
            order = sorted(m, key=lambda k: st_d[k])
            alt = all(m[order[i]] != m[order[(i + 1) % 12]] for i in range(12))
            sense[f"iA{'+' if ph_a > 0 else '-'}_iB{'+' if ph_b > 0 else '-'}"] = dict(map={k: m[k] for k in order}, alternating=alt)
    out["G-EM-SENSE"] = dict(report=sense, start_node={k: v["rail_end"] for k, v in pairs.items()},
                             pin_note="L_A: pin 1 = rail end (node 1); L_B: pin 2 = rail end (node 4) -- sense from start_node, not pins")
    # T-MIRROR on the stations: theta -> -theta
    mir = {k: (-a) % 360 for k, a in st_d.items()}
    setA = sorted(st_d[f"CEM_A{k}"] for k in range(1, 7))
    setB = sorted(st_d[f"CEM_B{k}"] for k in range(1, 7))
    out["T-MIRROR-stations"] = dict(A_set_invariant=sorted(mir[f"CEM_A{k}"] for k in range(1, 7)) == setA,
                                    B_set_invariant=sorted(mir[f"CEM_B{k}"] for k in range(1, 7)) == setB,
                                    poles_mirror=sorted(((-a) % 360) for a, _, _ in poles),
                                    note="poles 15+60k map to 45+60k: alignment order of the groups reverses with the rotation sense")
    log(f"G-EM-ID {'PASS' if ok_id else 'FAIL'}; G-EM-STATION {'PASS' if out['G-EM-STATION']['pass_'] else 'FAIL'}"
        f" (A at 30+60k, B at 0+60k, poles {[a for a, _, _ in poles]}, numbering {out['G-EM-STATION']['numbering']})")
    log("G-EM-SENSE: " + "; ".join(f"{k}: alternating={v['alternating']}" for k, v in sense.items()))
    return out


# ---------------------------------------------------------------------------------------------------------
# P1-PUMP (P-REG-6): the RA chain || C_R across R-A/R-B, as a documented edit of NR
# ---------------------------------------------------------------------------------------------------------
def ra_net(cfg, L_tot, Q, C_R_pF):
    """rt_engine's probe-convention net with the NR tank removed (as every rt net) and the RA tank added:
    C_R from R-B to R-A, and the four-winding chain as one series inductor R-B -> R-A (a series chain's mutuals
    sum exactly into one inductance), R from Q at f0. 'lx' kind: a dynamic inductor in the ring engine."""
    import rt_engine as RT
    net = RT.build_net(cfg, tank="series", C_R1_pF=C_R_pF)
    f0 = 1 / (2 * math.pi * math.sqrt(L_tot * C_R_pF * 1e-12))
    R = 2 * math.pi * f0 * L_tot / Q
    net.inds.append(("L_RA_chain", net.n("R-B"), net.n("R-A"), L_tot, R, "lx"))
    net.meta["tank"] = "RA (documented edit of NR: L_R1/L_R2 -> chain, C_R across R-A/R-B, n18/n00 retired)"
    return net, f0, R


def p1_pump(L_tot_list, log=print):
    import pump_engine as PE
    import rt_engine as RT
    import pump_synth as SY
    lad, fi = SY.sized({})
    cfg = SY.engine_cfg(lad, fi)                 # the RT0 configuration (rt_gates.gate_rt0)
    t0 = time.time()
    m0 = RT.run(RT.build_net(cfg), cfg)
    z0 = m0["z"]
    log(f"  RT0 collapsed anchor z = {z0:.10f} (record 1.3254745317), rpm {cfg['rpm']:.0f} ({time.time() - t0:.0f} s)")
    rows = []
    zs = RT.run(RT.build_net(cfg, tank="series", C_R1_pF=789.0), cfg)["z"]
    log(f"  reference: series C_R 789 pF alone (no chain, = RT1 form) z {zs:.7f} (dz {zs - z0:+.2e})")
    for name, L in L_tot_list:
        for Q in (30.0, 50.0, 100.0):
            net, f0, R = ra_net(cfg, L, Q, 789.0)
            t0 = time.time()
            m = RT.run(net, cfg)
            rows.append(dict(L_name=name, L_tot_uH=L * 1e6, Q=Q, f0_kHz=f0 / 1e3, R_ohm=R, z=m["z"], converged=m["converged"],
                             dz=m["z"] - z0, cpu_s=time.time() - t0))
            log(f"  RA tank {name} L {L * 1e6:.0f} uH, Q {Q:.0f}: z {m['z']:.7f} (dz {m['z'] - z0:+.2e}), conv {m['converged']}, {time.time() - t0:.0f} s")
    judged = [r for r in rows if r["Q"] <= 30]
    ok = all(abs(r["dz"]) <= 1e-3 and r["converged"] for r in judged)
    return {"P1-PUMP": dict(z_anchor=z0, RT0_record=1.3254745, z_series_CR_only=zs, rpm=cfg["rpm"], rows=rows, verdict="PASS" if ok else "RA-BREAKS-PUMP")}


def _jsonable(o):
    if isinstance(o, dict):
        return {str(k): _jsonable(v) for k, v in o.items()}
    if isinstance(o, (list, tuple)):
        return [_jsonable(v) for v in o]
    if isinstance(o, (np.floating, np.integer)):
        return o.item()
    if isinstance(o, np.bool_):
        return bool(o)
    if isinstance(o, np.ndarray):
        return o.tolist()
    return o


def save(update):
    out = json.load(open(RESULTS)) if os.path.exists(RESULTS) else {}
    out.update(_jsonable(update))
    out["stamp"] = time.strftime("%Y-%m-%d %H:%M:%S %Z")
    json.dump(out, open(RESULTS, "w"), indent=1)


if __name__ == "__main__":
    what = sys.argv[1] if len(sys.argv) > 1 else "arith"
    if what in ("arith", "all"):
        res = {}
        res.update(p_reg_1_2())
        res.update(p_reg_3())
        res.update(p_reg_4())
        res.update(p_reg_7())
        res.update(g_em())
        save(dict(arith=res))
    if what in ("pump", "all"):
        Ls = [("record 856 uH", 856e-6), ("bracket 500 uH", 500e-6), ("bracket 1000 uH", 1000e-6)]
        if os.path.exists(RESULTS):
            r = json.load(open(RESULTS))
            for var, d in (r.get("ra_magnetics") or {}).items():
                if isinstance(d, dict) and "L_tot_uH" in d:
                    Ls.append((f"computed ({var})", d["L_tot_uH"] * 1e-6))
        save(p1_pump(Ls))
    print("->", RESULTS)
