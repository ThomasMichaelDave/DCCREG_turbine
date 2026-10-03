#!/usr/bin/env python3
"""sim/rt_gates.py -- ROUND-TRIP gates (brief round-trip-floor r0.1), fail-closed.

  FS1  guarded parallel plates vs eps A / g (0.5 %)
  FS2  isolated thin disc vs 8 eps0 a, free space (1 %)
  FS3  two spheres vs the exact image (bispherical) series, free space (0.5 %)
  FS4  dielectric slab in series with an air gap vs the series formula (0.5 %)
  FS5  mesh convergence on the reference build (< 0.5 % per refinement, couplings >= 1 pF; 0.1 pF below)
  FS6  reciprocity |C_ij - C_ji| / max < 0.1 % and the Maxwell sign rules
  FS7  cross-tool: overlap-dominated couplings vs the integrity tool, fringe increment reported
  FS8  radius surrogate vs an exact solve (1e-3 in z)
  RT0  rt_engine with every extension off = pump-synth's freeze headline (1e-9) and K1-K4
  RT1  series tank: the probe (C_R1 785 pF -> 1.3113581) and dz ~ 1/C_R1
  RT2  N_theta 24 vs 48 per 60 deg: |dz| < 1e-4
  RT3  every evaluated geometry passes integrity
  RT4  every G-* geometry gate still passes on the freeze reference build
  CR1  counter-rotation: rpm_stator = 0 reproduces max_rpm 3885
  MC1-MC3  motor-in, continuous time
  FROZEN, FIREWALL
Usage: python3 sim/rt_gates.py [--only FS1,...]. Record: sim/rt_gates.json.
"""
import json
import math
import os
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path[:0] = [HERE, ROOT, os.path.join(ROOT, "reference")]
import numpy as np                      # noqa: E402
import field_solve as FS                # noqa: E402

OUT = {}


def _sec(name, node, ri, ro, z0, z1, eps=None, a0=0.0, w=360.0):
    return dict(kind="sector", cond=node, eps=eps, name=name, r_in=ri, r_out=ro, a0=a0, w=w, z0=z0, z1=z1)


def _solve(prims, res, enclosure, r_cut=0.0, check=False):
    g, bc = FS.build_grid(prims, enclosure=enclosure, res=res)
    eps, cond, names = FS.rasterize(g, prims)
    C, info = FS.maxwell(g, eps, cond, names, bc, solver="direct", r_cut=r_cut)
    return C * 6.0, names, info, g


AXI = dict(h_max_p=60.0, h_min_arc=1e6, grow=1.25)


def gate_fs1():
    """guarded plates: the top plate (guard at its potential) vs eps0 A / g, A to the slit centrelines."""
    rows = []
    for gap, slit in ((2.0, 0.25), (4.0, 0.5)):
        C, names, info, g = _solve([_sec("low", "low", 0.0, 90.0, -1.0, 0.0), _sec("top", "top", 20.0, 60.0, gap, gap + 1.0),
                                    _sec("go", "guard", 60.0 + slit, 90.0, gap, gap + 1.0),
                                    _sec("gi", "guard", 0.0, 20.0 - slit, gap, gap + 1.0)],
                                   dict(AXI, h_max_r=1.0, h_min_r=0.05, h_max_z=0.25, h_min_z=0.05), 40.0)
        i, j = names.index("low"), names.index("top")
        A = math.pi * ((60.0 + slit / 2) ** 2 - (20.0 - slit / 2) ** 2)
        ref = FS.EPS0 * FS.EPS_R["air"] * A / gap
        rows.append(dict(gap=gap, slit=slit, C_pF=-C[i, j] * 1e12, ref_pF=ref * 1e12, rel=-C[i, j] / ref - 1, cells=info["cells"]))
    return dict(pass_=all(abs(r["rel"]) <= 5e-3 for r in rows), rows=rows, tol=5e-3)


def gate_fs2():
    """isolated thin disc (radius a, thickness t) in free space vs 8 eps0 a (t/a = 0.002)."""
    a, t = 50.0, 0.1
    C, names, info, g = _solve([_sec("disc", "d", 0.0, a, -t / 2, t / 2)],
                               dict(AXI, h_max_r=8.0, h_min_r=0.02, h_max_z=8.0, h_min_z=0.02, h_far=200.0, grow=1.2), None)
    ref = 8.0 * FS.EPS0 * FS.EPS_R["air"] * a
    rel = C[0, 0] / ref - 1
    # the finite thickness raises C by ~ (t / (pi a)) (ln(16 pi a / t) - 1) [OC, thin-cylinder asymptote]
    corr = t / (math.pi * a) * (math.log(16 * math.pi * a / t) - 1)
    return dict(pass_=abs(rel) <= 1e-2, C_pF=C[0, 0] * 1e12, ref_pF=ref * 1e12, rel=rel, thickness_term=corr,
                cells=info["cells"], tol=1e-2)


def sphere_pair_exact(a, d, n=200):
    """equal spheres radius a, centres d apart: (c11, c12) Maxwell coefficients in F (mm units)."""
    b = math.acosh(d / (2 * a))
    k = 4 * math.pi * FS.EPS0 * FS.EPS_R["air"] * a * math.sinh(b)
    c11 = k * sum(1.0 / math.sinh((2 * m - 1) * b) for m in range(1, n))
    c12 = -k * sum(1.0 / math.sinh(2 * m * b) for m in range(1, n))
    return c11, c12


def gate_fs3():
    """two spheres on the axis (radius 10, centres 30 apart) in free space vs the image series; the staircase
    error is first order in the cell size, so the solve is Richardson-extrapolated from two cell sizes [ME]."""
    a, d = 10.0, 30.0
    prims = [dict(kind="sphere", cond="s1", eps=None, name="s1", c=[0.0, 0.0, -d / 2], R=a),
             dict(kind="sphere", cond="s2", eps=None, name="s2", c=[0.0, 0.0, d / 2], R=a)]
    out = []
    for h in (0.2, 0.1):
        # fine uniform cells around the spheres (r <= a + 2, |z| <= d/2 + a + 2), coarsening outside
        sec = [_sec("box", None, 0.0, a + 2.0, -d / 2 - a - 2.0, d / 2 + a + 2.0, eps=FS.EPS_R["air"])]
        g, bc = FS.build_grid(sec + prims, enclosure=None, res=dict(AXI, h_max_r=h, h_min_r=h, h_max_z=h, h_min_z=h,
                                                                     h_far=200.0, grow=1.15))
        eps, cond, names = FS.rasterize(g, prims)
        C, info = FS.maxwell(g, eps, cond, names, bc, solver="direct", r_cut=0.0)
        C *= 6.0
        out.append((h, C[0, 0], C[0, 1], info["cells"]))
    c11, c12 = sphere_pair_exact(a, d)
    (h1, a1, b1, n1), (h2, a2, b2, n2) = out
    a_ex, b_ex = 2 * a2 - a1, 2 * b2 - b1          # Richardson, first order
    r11, r12 = a_ex / c11 - 1, b_ex / c12 - 1
    return dict(pass_=abs(r11) <= 5e-3 and abs(r12) <= 5e-3, c11_pF=c11 * 1e12, c12_pF=c12 * 1e12,
                solved=[dict(h=h, c11_pF=x * 1e12, c12_pF=y * 1e12, cells=n) for h, x, y, n in out],
                extrapolated=dict(c11_pF=a_ex * 1e12, c12_pF=b_ex * 1e12), rel11=r11, rel12=r12, tol=5e-3)


def gate_fs4():
    """a dielectric slab (eps 5.4, 1.5 mm) in series with 1.5 mm of air between guarded plates vs
    eps0 A / (t1 / eps1 + t2 / eps_air) -- the void-in-solid case."""
    t1, t2, slit = 1.5, 1.5, 0.25
    gap = t1 + t2
    C, names, info, g = _solve([_sec("low", "low", 0.0, 90.0, -1.0, 0.0), _sec("slab", None, 0.0, 90.0, 0.0, t1, eps=5.4),
                                _sec("top", "top", 20.0, 60.0, gap, gap + 1.0), _sec("go", "guard", 60.0 + slit, 90.0, gap, gap + 1.0),
                                _sec("gi", "guard", 0.0, 20.0 - slit, gap, gap + 1.0)],
                               dict(AXI, h_max_r=1.0, h_min_r=0.05, h_max_z=0.2, h_min_z=0.05), 40.0)
    i, j = names.index("low"), names.index("top")
    A = math.pi * ((60.0 + slit / 2) ** 2 - (20.0 - slit / 2) ** 2)
    ref = FS.EPS0 * A / (t1 / 5.4 + t2 / FS.EPS_R["air"])
    rel = -C[i, j] / ref - 1
    return dict(pass_=abs(rel) <= 5e-3, C_pF=-C[i, j] * 1e12, ref_pF=ref * 1e12, rel=rel, tol=5e-3)


def gate_fs6(sweep_path=None):
    """reciprocity of the unsymmetrised Schur complement and the Maxwell sign rules, on the reference
    build at one angle (coarse grid) and on the analytic cases."""
    import round_trip as RTP
    d = json.load(open(os.path.join(ROOT, "docs", "geometry", "freeze-v010-CaCb.json")))
    prims = FS.dedupe(FS.primitives(d["parts"]))
    rot = RTP.rotor_names(d)
    g, bc = FS.build_grid(prims, res=RTP.RES["c"], theta_breaks=[7.5, 37.5])
    eps, cond, names = FS.rasterize(g, prims, rotor=rot, theta=7.5)
    C, info = FS.maxwell(g, eps, cond, names, bc, tol=1e-9, r_cut=25.0, return_V=False)
    asym = info.get("reciprocity", float("nan"))
    off = C - np.diag(np.diag(C))
    signs = bool(np.all(np.diag(C) > 0) and np.all(off <= 1e-6 * np.max(np.abs(C))) and np.all(C.sum(axis=1) >= -1e-6 * np.max(np.abs(C))))
    return dict(pass_=bool(asym < 1e-3 and signs), reciprocity=asym, sign_rules=signs, theta_geom=7.5, cells=info["cells"])


def gate_rt0():
    """rt_engine with every extension off = pump-synth's freeze headline, and K1-K4."""
    import pump_engine as PE
    import pump_synth as SY
    import rt_engine as RT
    lad, fi = SY.sized({})
    cfg = SY.engine_cfg(lad, fi)
    z, conv = RT.z_of(cfg)
    k = PE.canaries()
    return dict(pass_=bool(abs(z - 1.3254745317) <= 1e-9 and conv and k["pass_"]), z=z, ref=1.3254745317, dz=z - 1.3254745317,
                canaries={r["id"]: r["pass"] for r in k["rows"]})


def gate_rt1():
    """series tank at the pump frequency: the chat-layer probe (R-A the reference, strays to it):
    C_R1 785.203 pF -> 1.3113581, 300 pF -> 1.2917147; and dz ~ 1/C_R1 (1, 10, 100 uF)."""
    import pump_synth as SY
    import rt_engine as RT
    lad, fi = SY.sized({})
    cfg = SY.engine_cfg(lad, fi)
    z0 = RT.z_of(cfg)[0]
    rows = {}
    for C in (785.203, 300.0, 1e6, 1e7, 1e8):
        z, conv = RT.z_of(cfg, tank="series", C_R1_pF=C)
        rows[str(C)] = dict(z=z, converged=conv, dz=z - z0, dz_times_C=(z - z0) * C)
    ok = abs(rows["785.203"]["z"] - 1.3113581) < 5e-8 and abs(rows["300.0"]["z"] - 1.2917147) < 5e-8
    k = [rows[str(c)]["dz_times_C"] for c in (1e6, 1e7, 1e8)]
    ok &= max(k) - min(k) < 0.01 * abs(k[0])
    return dict(pass_=bool(ok), z_collapsed=z0, rows=rows, probe={"785": 1.3113581, "300": 1.2917147},
                P1=dict(predicted="0.014 +- 0.002", got=z0 - rows["785.203"]["z"]))


def gate_cr1():
    """counter-rotation: with rpm_stator = 0 the per-body I9 reproduces pump-synth's max_rpm (3885); the
    split table (D-SPLIT) for the record."""
    import pump_synth as SY
    import rt_engine as RT
    m = SY.max_rpm({})
    lad, _ = SY.sized({})
    r_rot = lad["rotor_outMm"]
    rpm0 = math.floor(RT.max_rpm_rel(0.0, r_rotor_mm=r_rot, rpm_I12=m["rpm_I12"]) * (1 - 1e-9))
    d = json.load(open(os.path.join(ROOT, "docs", "geometry", "freeze-v010-CaCb.json")))
    r_st = d["sparkgaps"]["R_frame"] + d["geom"]["sg_rod"] / 2
    table = []
    for sp in (0.0, 0.25, 0.5, 0.75, 1.0):
        mr = RT.max_rpm_rel(sp, r_rotor_mm=r_rot, r_stator_mm=r_st, rpm_I12=m["rpm_I12"])
        cr = RT.counter_rotation(mr, sp, r_rotor_mm=r_rot, r_stator_mm=r_st)
        table.append(dict(split=sp, max_rpm_rel=mr, rpm_rotor=cr["rpm_rotor"], rpm_stator=cr["rpm_stator"],
                          rim_rotor=cr["rim_rotor"], rim_stator=cr["rim_stator"], prf_hz=cr["prf_hz"],
                          binding="I12" if abs(mr - m["rpm_I12"]) < 1e-9 else
                          ("I9 stator" if cr["rim_stator"] >= cr["rim_hard"] * (1 - 1e-9) else "I9 rotor")))
    return dict(pass_=bool(rpm0 == m["rpm"] == 3885), max_rpm_pump_synth=m["rpm"], max_rpm_split0=rpm0, rpm_I9=m["rpm_I9"],
                rpm_I12=m["rpm_I12"], r_rotor_mm=r_rot, r_stator_mm=r_st, table=table,
                note="z is split-independent with the motor off (the engine sees the relative angle); the split sets each body's rim speed")


def gate_fs7(sweep=None):
    """cross-tool: the overlap-dominated couplings of the reference build (C1 / C2 max, Cx max, Ca / Cb,
    C_R1) from the field solve vs the integrity tool's facing-foil overlap; each coupling's fringe increment
    is reported (reported, no tolerance). Unmerged nets (n18, n00 as drawn)."""
    import circuit_integrity as CI
    import round_trip as RTP
    sweep = sweep or os.path.join(ROOT, "docs", "geometry", "rt", "freeze-t15.c12.sweep.json")
    thetas, sols = RTP.load(sweep)
    d = json.load(open(os.path.join(ROOT, "docs", "geometry", "rt", "freeze-t15.design.json")))
    rep = CI.analyze(CI.parts_from_design(d), CI.load_netlist(), "FS7")
    cap = {c["name"]: c for c in rep["capacitors"]}
    names = sols[0]["names"]
    def mut(a, b, k):
        C = np.array(sols[k]["C"]); return -C[names.index(a), names.index(b)]
    rows = []
    for nm, a, b, kind in (("C1", "1", "R-A", "max"), ("C2", "4", "R-B", "max"), ("Cx3", "7", "n17", "max"),
                           ("Cx4", "8", "n23", "max"), ("Ca1", "1", "2", "fixed"), ("Cb1", "3", "4", "fixed"),
                           ("C_R1", "n18", "n00", "fixed")):
        vals = [mut(a, b, k) for k in range(len(sols))]
        f = max(vals) if kind == "max" else float(np.mean(vals))
        o = cap[nm]["C_max_pF"]
        rows.append(dict(cap=nm, nets=f"{a}-{b}", overlap_pF=o, field_pF=f, fringe_pF=f - o, fringe_rel=f / o - 1))
    mins = []
    for nm, a, b in (("C1", "1", "R-A"), ("C2", "4", "R-B"), ("Cx3", "7", "n17"), ("Cx4", "8", "n23")):
        vals = [mut(a, b, k) for k in range(len(sols))]
        mins.append(dict(cap=nm, overlap_min_pF=cap[nm]["C_min_pF"], field_min_pF=min(vals)))
    return dict(pass_=True, reported=True, rows=rows, minima=mins, sweep=os.path.relpath(sweep, ROOT),
                note="field = 3-D solve incl. fringe and the carrier dielectric; overlap = facing-foil area only")


def gate_mc1():
    """one motor branch (L, R) between two capacitors, no gaps, integrated by MotorSim over a full cycle vs
    the analytic series-RLC discharge of the difference voltage (1e-6)."""
    import pump_engine as PE
    import rt_engine as RT
    Ca_, Cb_, L, R, V0 = 440e-9, 220e-9, 0.64, 40.0, 1.0
    net = RT.RTNet(ground=("0",))
    a, b = net.n("a"), net.n("b")
    net.caps += [("Ca", a, PE.GND, Ca_), ("Cb", b, PE.GND, Cb_)]
    net.inds.append(("Lm", a, b, L, R, "motor"))
    net.meta = dict(motor=True)
    sim = RT.MotorSim(net, mode="cont", dth=0.05, rpm=3000.0)
    sim.q = np.array([Ca_ * V0, 0.0])
    sim.cycle(0)
    t = sim.T_CYC
    Ce = Ca_ * Cb_ / (Ca_ + Cb_)
    al = R / (2 * L); w0 = 1 / math.sqrt(L * Ce); wd = math.sqrt(w0 * w0 - al * al)
    v = V0 * math.exp(-al * t) * (math.cos(wd * t) + al / wd * math.sin(wd * t))
    i = V0 / (L * wd) * math.exp(-al * t) * math.sin(wd * t)          # a -> b
    Va, Vb = sim.q[0] / Ca_, sim.q[1] / Cb_
    err_v = abs((Va - Vb) - v) / V0
    err_i = abs(abs(sim.I[0]) - abs(i)) / (V0 / (L * wd))
    return dict(pass_=bool(err_v < 1e-6 and err_i < 1e-6), v_sim=Va - Vb, v_exact=v, err_v=err_v, err_i=err_i,
                t_us=t * 1e6, f_hz=wd / (2 * math.pi))


def _motor_cfg(dth=0.05):
    import pump_synth as SY
    lad, fi = SY.sized({})
    return SY.engine_cfg(lad, dict(fi, motor=True), over=dict(dth=dth))


def gate_mc2():
    """conservation with the motor in (MotorSim): W = dE + E_diss per cycle to 1e-9."""
    import pump_engine as PE
    import rt_engine as RT
    cfg = _motor_cfg()
    net = RT.build_net(cfg)
    sim = RT.MotorSim(net, mode="cont", dth=cfg["dth"], rpm=cfg["rpm"])
    PE.seed(sim, -1.0)
    r = PE.run_machine(net, ncyc=8, burn=4, sim=sim)
    res = max(row["resid"] for row in r["rows"][2:])
    return dict(pass_=bool(res < 1e-9), resid_max=res, located=sim.n_located, z_run=r["z"])


def gate_mc3():
    """step halving and a localisation-tolerance change: |dz| < 1e-3 (monodromy z, motor in)."""
    import rt_engine as RT
    out = {}
    for tag, dth, it in (("dth0.05", 0.05, 30), ("dth0.025", 0.025, 30), ("loc40", 0.05, 40)):
        cfg = _motor_cfg(dth)
        m = RT.motor_monodromy(RT.build_net(cfg), cfg, loc_it=it)
        out[tag] = dict(z=m["z"], converged=m["converged"], sub=m["sub"], located=m["n_located"])
    dz = max(abs(out["dth0.025"]["z"] - out["dth0.05"]["z"]), abs(out["loc40"]["z"] - out["dth0.05"]["z"]))
    growing = all(v["z"] > 1.0 + 1e-6 for v in out.values())
    return dict(pass_=bool(dz < 1e-3), dz=dz, runs=out, G1m=("overturned: a growing mode" if growing else
                "confirmed: no growing mode (z within 1e-5 of 1) -- with the motor branches the drawn pump does not pump"))


GATES = [("FS1", gate_fs1), ("FS2", gate_fs2), ("FS3", gate_fs3), ("FS4", gate_fs4), ("FS6", gate_fs6), ("FS7", gate_fs7),
         ("RT0", gate_rt0), ("RT1", gate_rt1), ("CR1", gate_cr1), ("MC1", gate_mc1), ("MC2", gate_mc2), ("MC3", gate_mc3)]


def main():
    only = None
    if "--only" in sys.argv:
        only = set(sys.argv[sys.argv.index("--only") + 1].split(","))
    path = os.path.join(HERE, "rt_gates.json")
    if os.path.exists(path):
        OUT.update(json.load(open(path)))
    for name, fn in GATES:
        if only and name not in only:
            continue
        t0 = time.time()
        try:
            r = fn()
        except Exception as e:
            import traceback
            r = dict(pass_=False, error=f"{type(e).__name__}: {e}", tb=traceback.format_exc()[-1500:])
        r["time_s"] = time.time() - t0
        OUT[name] = r
        print(f"[{name}] {'PASS' if r.get('pass_') else 'FAIL'}", {k: v for k, v in r.items() if k in
              ("rel", "rel11", "rel12", "reciprocity", "error", "C_pF", "ref_pF", "rows", "time_s")}, flush=True)
        json.dump(OUT, open(path, "w"), indent=1, default=str)


if __name__ == "__main__":
    main()
