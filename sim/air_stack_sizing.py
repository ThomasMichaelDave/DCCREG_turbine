"""sim/air_stack_sizing.py -- the electrostatic vane stacks resized for AIR: a wider gap holds more voltage, so the vanes
are spaced further apart and their number N chosen to win the capacitance back. Writes sim/air_stack_sizing_results.json.

For each vane gap g (the Ca / Cb plates get the same gap, plate pitch g + t):
- breakdown in air at 1 atm, 20 C (sim/stack_sizing.gap_breakdown_kV, uniform field) and the operating peak
  V_op = V_bd / MARGIN, the vacuum design's margin (30 / 20 kV) [RH: the vane edges lower the real hold-off];
- C per working gap, aligned and opposed, from stack_sizing's 2-D vane cell (air), so the fringing that raises C_min at
  wider gaps is in kappa;
- N rotor (= stator) vanes per varicap for two targets:
    "same C"     -- C_max at least the vacuum design's 1113 pF (the same ladder: Ca = Cb = 1.1 C_max, Cpar 20 pF);
    "same power" -- the clamped pump power at V_op at least the vacuum design's (at 1200 rpm relative, 120 Hz);
- for each: kappa, the gain z of the bare de Queiroz core (stack_sizing.z_stack, topology 'core'), the clamped power at
  V_op (sim/bicone_drive.py's netlist in ngspice, clamp BV = V_op), the electrostatic stacks' length per side (first
  varicap vane to the last Ca plate) and the tube's length, both from stack_sizing.layout (the tube: the wound build's
  802 mm plus the layout's change), the rotor-vane mass.
The tube's other dimensions are unchanged: r 50..150 mm, 6 sectors (stator 30 deg, rotor 22 deg), 1.5 mm Al vanes.
Stage 2 (geometry_search): at 6 / 8 / 10 mm, the sector count (3, 4, 6) and the stator / rotor widths, because at wide
gaps the fringe field between a rotor vane and the next stator sector keeps C_min high and kappa collapses; ranked by
the eigen-cycle power (stack_sizing ledger at V_op) per mm of stack.
Stage 4 (thick_vanes, --thick): the designer's vanes on the best 6 mm geometry, at least 4 mm thick with full-round
edges (sim/vane_cell.py), against the 1.5 mm square-cut vanes the search used; the rims' peak field against corona.
Stage 4b (thick_search, --thick-search): the sector count and widths searched again for those vanes.
Stage 4c (thick_compare, --thick-compare): other thicknesses and vane counts on the chosen widths.
Usage: python3 sim/air_stack_sizing.py            (about 40 min: 11 ngspice runs, one at a time)
       python3 sim/air_stack_sizing.py --finish   (the derived columns only, from the saved results)
       python3 sim/air_stack_sizing.py --thick    (stage 4 only, into the saved results: about 10 min)
       python3 sim/air_stack_sizing.py --thick-search   (stage 4b, after --thick: 4 processes, about 15 min)
       python3 sim/air_stack_sizing.py --thick-compare 3:rule 3:6 ...   (stage 4c: t:n, n = rule or a vane count)
"""
import json
import math
import os
import subprocess
import sys
import tempfile

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import bicone_drive as BD          # noqa: E402
import stack_sizing as SS          # noqa: E402
import vane_cell as VC             # noqa: E402

GAPS = (3.0, 5.0, 6.0, 8.0, 10.0, 12.0, 15.0)
MARGIN = 30.0 / 20.0               # the vacuum design's breakdown / operating ratio
RPM, F = 1200.0, 120.0
L_TUBE_WOUND = 802.0               # the built tube (sim/tube_geometry.py --rel wound)
T_VANE = SS.TUBE_DEFAULTS["t_vaneMm"]


def plates(g, n, diel, geo=None):
    return dict(dict(g_vMm=g, n_plates=n, dielectric=diel, pitch_fixed_mm=g + T_VANE, bucket=False), **(geo or {}))


_CAPS = {}
_tube_caps = SS.tube_caps


def _cached_tube_caps(p):
    """stack_sizing.tube_caps (sim/vane_cell's for rounded vane edges) with the per-gap cell solutions cached by
    geometry (N only multiplies them)."""
    edge = p.get("edge", "square")
    key = tuple(p[k] for k in ("g_vMm", "t_vaneMm", "N_sec", "ws_deg", "wr_deg", "r_inMm", "r_outMm", "h_mm", "n_r",
                               "dielectric")) + (edge,)
    if key not in _CAPS:
        _CAPS[key] = (_tube_caps if edge == "square" else VC.tube_caps)(dict(p, n_plates=1))
    one = _CAPS[key]
    n_gap = 2 * int(p["n_plates"]) - 1
    return dict(one, n_gap=n_gap, C_max=n_gap * one["per_gap_max_pF"],
                C_min=n_gap * one["per_gap_min_pF"] + p["C_edge_pF"])


SS.tube_caps = _cached_tube_caps


def es_lengths(tg):
    """from stack_sizing.layout's elements (the layout that is drawn and built): the electrostatic stacks' axial length
    per side (side A: first C1 vane to the last Ca plate) and the layout's tube length."""
    es = [e for e in tg["elements"] if e["side"] == "A" and e["kind"] in ("C1 vane", "Ca plate")]
    return max(e["z1"] for e in es) - min(e["z0"] for e in es), tg["L_total_mm"]


def stack(g, n, diel, geo=None, v_op=None):
    lad = SS.size_stack("tube", plates(g, n, diel, geo), dict(rpm=RPM))
    tc, tg = lad["tube_caps"], lad["tube_geometry"]
    L_es, L_lay = es_lengths(tg)
    if v_op:
        SS.V_OP = v_op                                     # the eigen-cycle ledger at this stack's operating peak
    z = SS.z_stack(lad, topology="core", ledger=bool(v_op))
    return dict(n_plates=n, n_gap=tc["n_gap"], C_max_pF=tc["C_max"], C_min_pF=tc["C_min"], kappa=tc["C_max"] / tc["C_min"],
                Ca_pF=lad["ladder"]["Ca"]["value"], z=z["z"], L_varicap_mm=tg["L_varicap_mm"], n_gap_ca=tg["n_gap_ca"],
                L_ca_mm=tg["L_ca_mm"], L_es_side_mm=L_es, L_layout_mm=L_lay, m_rotor_vanes_kg=tg["m_rotor_vanes_kg"],
                per_gap_max_pF=tc["per_gap_max_pF"],
                per_gap_min_pF=tc["per_gap_min_pF"], cycles_per_rev=(geo or {}).get("N_sec", SS.TUBE_DEFAULTS["N_sec"]) // 2,
                P_eigen_W=(z.get("ledger") or {}).get("P_surplus_W"))


def clamped_power(args):
    """the clamped pump power (W) at 1200 rpm: sim/bicone_drive.py's diodes-only netlist with this stack's caps,
    the clamp's breakdown at V_op and the stack's pump frequency f (sectors x rpm / 60)."""
    cmin, cmax, ca, v_op, f = args
    BD.F, BD.CMIN, BD.CMAX, BD.CA, BD.V_OP = f, cmin * 1e-12, cmax * 1e-12, ca * 1e-12, v_op
    txt, vecs, pk = BD.deck("diodes")
    txt = txt.replace("wrdata out.dat " + " ".join(vecs), "wrdata out.dat v(e_limit)")      # one vector: small file
    with tempfile.TemporaryDirectory() as d:
        open(os.path.join(d, "x.cir"), "w").write(txt)
        subprocess.run(["ngspice", "-b", "x.cir"], capture_output=True, text=True, timeout=3600, cwd=d)
        raw = np.loadtxt(os.path.join(d, "out.dat"))
    t, y = raw[:, 0], raw[:, 1]
    t0 = (24 - 8) / f
    return float((np.interp(t[-1], t, y) - np.interp(t0, t, y)) / (t[-1] - t0))


SEARCH_GAPS = (6.0, 8.0, 10.0)
SEARCH_SECTORS = (3, 4, 6)
SEARCH_WS, SEARCH_WR = (0.4, 0.5), (0.25, 0.3, 0.367)      # stator / rotor width as a fraction of the sector period


def geometry_search():
    """at each gap: sector count and widths, N for the vacuum design's C_max; ranked by the eigen-cycle power per
    millimetre of electrostatic stack (varicap + Ca, per side) among the designs with z >= 1.3."""
    base = stack(3.0, 8, "vacuum")
    out = []
    for g in SEARCH_GAPS:
        v_op = SS.gap_breakdown_kV(g, "air") / MARGIN * 1e3
        for ns in SEARCH_SECTORS:
            per = 360.0 / ns
            for fs in SEARCH_WS:
                for fr in SEARCH_WR:
                    if fs + fr >= 0.95:
                        continue
                    geo = dict(N_sec=2 * ns, ws_deg=fs * per, wr_deg=fr * per)
                    one = stack(g, 1, "air", geo)
                    n = max(1, math.ceil((base["C_max_pF"] / one["per_gap_max_pF"] + 1) / 2))
                    q = stack(g, n, "air", geo, v_op=v_op)
                    q.update(gap_mm=g, V_op_kV=v_op / 1e3, sectors=ns, ws_deg=geo["ws_deg"], wr_deg=geo["wr_deg"])
                    q["P_eigen_per_m"] = q["P_eigen_W"] / (q["L_es_side_mm"] * 1e-3)
                    out.append(q)
                    print(f"g {g:4.1f} sectors {ns} ws {geo['ws_deg']:5.1f} wr {geo['wr_deg']:5.1f}: N {n:3d} k {q['kappa']:5.2f} "
                          f"z {q['z']:.3f} P_eig {q['P_eigen_W']:6.2f} W  stacks {q['L_es_side_mm']:.0f} mm/side", flush=True)
    return out


def _clamp_job(q, v_op_kV):
    return (q["C_min_pF"], q["C_max_pF"], q["Ca_pF"], v_op_kV * 1e3, q["cycles_per_rev"] * RPM / 60.0)


def main():
    base = stack(3.0, 8, "vacuum", v_op=20e3)              # the built design
    base.update(V_op_kV=20.0, V_bd_kV=30.0, L_tube_mm=L_TUBE_WOUND)
    # stage 1: today's 6-sector vanes, wider gaps, N for the same C_max
    gaps = []
    for g in GAPS:
        v_bd = SS.gap_breakdown_kV(g, "air")
        v_op = v_bd / MARGIN
        one = stack(g, 1, "air")
        n = max(1, math.ceil((base["C_max_pF"] / one["per_gap_max_pF"] + 1) / 2))
        q = stack(g, n, "air", v_op=v_op * 1e3)
        q.update(gap_mm=g, V_bd_kV=v_bd, V_op_kV=v_op)
        gaps.append(q)
        print(f"gap {g:4.1f} mm: V_op {v_op:.1f} kV, N {n}, kappa {q['kappa']:.2f}, z {q['z']:.3f}", flush=True)
    # stage 2: the sector geometry at 6 / 8 / 10 mm
    search = geometry_search()
    best = []
    for g in SEARCH_GAPS:
        ok = [q for q in search if q["gap_mm"] == g and q["z"] >= 1.3]
        if ok:
            best.append(max(ok, key=lambda q: q["P_eigen_per_m"]))
    # stage 3: the clamped power (ngspice, one run at a time: ~0.4 GB of vectors each)
    rows = [base] + gaps + best
    for q in rows:
        q["P_clamped_W"] = clamped_power(_clamp_job(q, q["V_op_kV"]))
        print(f"clamped: {q.get('gap_mm', 3.0)} mm {q.get('sectors', 6)} sectors -> {q['P_clamped_W']:.2f} W", flush=True)
    out = dict(rpm=RPM, margin=MARGIN, base_vacuum=base, gap_sweep=gaps, geometry_search=search, best_per_gap=best)
    finish(out)


P_REACHED = 0.05                   # W: below this the pump did not reach its clamp in the 24-cycle run (z too low)


def _geo(q):
    return dict(N_sec=2 * q["sectors"], ws_deg=q["ws_deg"], wr_deg=q["wr_deg"]) if "sectors" in q else None


def finish(out):
    """the derived columns: the stack and tube lengths from stack_sizing.layout (filled in for results saved before they
    were), the clamped power per metre of stack, and the vane count / stack length that would give the vacuum design's
    clamped power (power scales with the working gaps at a fixed geometry and V_op)."""
    base = out["base_vacuum"]
    rows = [(base, "vacuum")] + [(q, "air") for q in out["gap_sweep"] + out["geometry_search"] + out["best_per_gap"]]
    for q, diel in rows:
        if "L_layout_mm" not in q:
            lad = SS.size_stack("tube", plates(q.get("gap_mm", 3.0), q["n_plates"], diel, _geo(q)), dict(rpm=RPM))
            q["L_es_side_mm"], q["L_layout_mm"] = es_lengths(lad["tube_geometry"])
    for q in out["geometry_search"]:
        q["P_eigen_per_m"] = q["P_eigen_W"] / (q["L_es_side_mm"] * 1e-3)
    for b in out["best_per_gap"]:                          # the clamped powers belong to these designs: same ranking
        ok = [q for q in out["geometry_search"] if q["gap_mm"] == b["gap_mm"] and q["z"] >= 1.3]
        top = max(ok, key=lambda q: q["P_eigen_per_m"])
        assert (top["sectors"], top["ws_deg"], top["wr_deg"]) == (b["sectors"], b["ws_deg"], b["wr_deg"]), b["gap_mm"]
        b["P_eigen_per_m"] = top["P_eigen_per_m"]
    base_es_side = base["L_es_side_mm"]
    base["P_clamped_per_m"] = base["P_clamped_W"] / (base_es_side * 1e-3)
    for q in out["gap_sweep"] + out["best_per_gap"]:
        q["L_tube_mm"] = L_TUBE_WOUND + q["L_layout_mm"] - base["L_layout_mm"]
        if q["P_clamped_W"] < P_REACHED:
            q.update(reached_clamp=False, P_clamped_per_m=None, same_power=None)
            continue
        q["reached_clamp"] = True
        q["P_clamped_per_m"] = q["P_clamped_W"] / (q["L_es_side_mm"] * 1e-3)
        k = base["P_clamped_W"] / q["P_clamped_W"]
        q["same_power"] = dict(n_plates=math.ceil(((2 * q["n_plates"] - 1) * k + 1) / 2), scale=k,
                               L_es_side_mm=q["L_es_side_mm"] * k,
                               L_tube_mm=q["L_tube_mm"] + 2 * q["L_es_side_mm"] * (k - 1))
    json.dump(out, open(os.path.join(HERE, "air_stack_sizing_results.json"), "w"), indent=1, default=float)


T_THICK = 4.0                      # the designer's minimum vane thickness, with full-round edges (radius t / 2)
RHO_AL = SS.TUBE_DEFAULTS["rho_vane"]


def masses(q, t_plate, ro=None):
    """kg of aluminium, both sides: rotor vanes (sectors + inner ring), and on the counter-rotor the stator vanes (sectors
    + outer ring) and the Ca / Cb plates (full annuli), for vanes out to ro (default the tube's). The rounds take < 1 %
    off and are ignored."""
    ri, rs, ring = SS.TUBE_DEFAULTS["r_inMm"], SS.SLEEVE_R, 12.0
    ro = ro or SS.TUBE_DEFAULTS["r_outMm"]
    ann = math.pi * (ro * ro - ri * ri)
    a_rot = q["sectors"] * q["wr_deg"] / 360.0 * ann + math.pi * (ri * ri - rs * rs)
    a_sta = q["sectors"] * q["ws_deg"] / 360.0 * ann + math.pi * ((ro + ring) ** 2 - ro * ro)
    kg = lambda area, t, n: 2 * n * area * t * 1e-9 * RHO_AL
    t, n = q["t_vaneMm"], q["n_plates"]
    return dict(rotor_vanes_kg=kg(a_rot, t, n), stator_vanes_kg=kg(a_sta, t, n),
                ca_plates_kg=kg(ann, t_plate, q["n_gap_ca"] + 1), t_plate_mm=t_plate)


def thick_vanes(out, t_plate=None, clamp=True):
    """stage 4: the designer's vanes on the best 6 mm geometry (6 sectors of 24 / 22 deg), T_THICK with full-round
    edges, against the 1.5 mm square-cut vanes the search used and 4 mm square-cut (thickness and rounding apart).
    Each: N for the vacuum design's C_max, kappa, z and the eigen-cycle power at V_op. The 4 mm round one also: the
    clamped power (ngspice), stack and tube lengths (stack_sizing.layout) and masses, with the Ca / Cb plates t_plate
    thick (default: as thick as the vanes; the layout gives the fixed plates the vanes' thickness). Then the rims' peak
    field at V_op (sim/vane_cell.edge_field) against Peek's onset."""
    b = out["best_per_gap"][0]
    g, v_op = b["gap_mm"], b["V_op_kV"] * 1e3
    base = out["base_vacuum"]
    res = dict(geometry=dict(gap_mm=g, sectors=b["sectors"], ws_deg=b["ws_deg"], wr_deg=b["wr_deg"], V_op_kV=b["V_op_kV"]),
               rows=[])
    for t, edge in ((T_VANE, "square"), (T_THICK, "square"), (T_THICK, "round")):
        tp = t if t_plate is None or t == T_VANE else t_plate
        geo = dict(_geo(b), t_vaneMm=t, edge=edge, pitch_fixed_mm=g + tp)
        one = stack(g, 1, "air", geo)
        n = max(1, math.ceil((base["C_max_pF"] / one["per_gap_max_pF"] + 1) / 2))
        q = stack(g, n, "air", geo, v_op=v_op)
        q.update(gap_mm=g, V_op_kV=b["V_op_kV"], sectors=b["sectors"], ws_deg=b["ws_deg"], wr_deg=b["wr_deg"],
                 t_vaneMm=t, edge=edge, t_plate_mm=tp, L_tube_mm=L_TUBE_WOUND + q["L_layout_mm"] - base["L_layout_mm"])
        q.update(masses(q, tp))
        if t == T_THICK and edge == "round" and clamp:
            q["P_clamped_W"] = clamped_power(_clamp_job(q, q["V_op_kV"]))
            q["P_clamped_per_m"] = q["P_clamped_W"] / (q["L_es_side_mm"] * 1e-3)
        res["rows"].append(q)
        print(f"t {t:g} {edge}: N {n} per gap {q['per_gap_min_pF']:.3f} / {q['per_gap_max_pF']:.3f} pF, C {q['C_min_pF']:.1f}"
              f" / {q['C_max_pF']:.1f}, kappa {q['kappa']:.2f}, z {q['z']:.4f}, P_eig {q['P_eigen_W']:.2f} W"
              + (f", clamped {q['P_clamped_W']:.2f} W" if "P_clamped_W" in q else "")
              + f"; ES {q['L_es_side_mm']:.1f} mm/side, tube {q['L_tube_mm']:.0f} mm", flush=True)
    edges = []
    for t in (T_VANE, T_THICK):
        e = VC.edge_field(t, g, "round")
        E = e["E_peak_per_V"] * b["V_op_kV"] * 10.0                      # kV/cm at V_op
        edges.append(dict(t_mm=t, r_edge_mm=0.5 * t, E_peak_kV_cm=E, enhancement=e["enhancement"], angle_deg=e["angle_deg"],
                          E_face_kV_cm=b["V_op_kV"] / g * 10.0, peek_kV_cm=VC.peek_kV_per_cm(0.5 * t),
                          ratio_to_onset=E / VC.peek_kV_per_cm(0.5 * t)))
        print(f"rim, {t:g} mm full round: {E:.1f} kV/cm at {b['V_op_kV']:.1f} kV (x{e['enhancement']:.2f} the face field), "
              f"Peek {VC.peek_kV_per_cm(0.5 * t):.1f} kV/cm", flush=True)
    res["rim_field"] = edges
    out["thick_vanes"] = res
    return res


THICK_SEARCH = {6: ((16.0, 18.0, 20.0, 22.0, 24.0, 26.0), (14.0, 16.0, 18.0, 20.0, 22.0, 24.0, 26.0)),   # stator / rotor
                4: ((27.0, 31.5, 36.0), (22.5, 27.0, 33.0)),
                3: ((36.0, 42.0, 48.0), (30.0, 36.0, 44.0))}


def _thick_design(args):
    """one design of the thick-vane search (a worker process): N for the vacuum design's C_max, then the stack at V_op."""
    g, ns, ws, wr, t, c_max, v_op = args
    geo = dict(N_sec=2 * ns, ws_deg=ws, wr_deg=wr, t_vaneMm=t, edge="round", pitch_fixed_mm=g + t)
    one = stack(g, 1, "air", geo)
    n = max(1, math.ceil((c_max / one["per_gap_max_pF"] + 1) / 2))
    q = stack(g, n, "air", geo, v_op=v_op)
    q.update(gap_mm=g, V_op_kV=v_op / 1e3, sectors=ns, ws_deg=ws, wr_deg=wr, t_vaneMm=t, edge="round", t_plate_mm=t)
    q["P_eigen_per_m"] = q["P_eigen_W"] / (q["L_es_side_mm"] * 1e-3)
    return q


KNEE = 0.03                        # the choice: the most gain within this fraction of the best power per metre [IR]


def thick_search(out, procs=4):
    """stage 4b: the sector count and widths again, for T_THICK vanes and Ca / Cb plates with full-round edges at the
    best gap (6 mm): the thicker edges fringe more at minimum C, so narrower sectors may win kappa back. Ranked as
    stage 2 (eigen-cycle power per mm of stack, z >= 1.3). That ranking is nearly flat here, so the design carried on
    ('chosen') is the one with the most z within KNEE of the best; both get the clamped power, lengths and masses.
    Designs already in the results are not run again."""
    from multiprocessing import Pool
    tv = out["thick_vanes"]
    g, v_op = tv["geometry"]["gap_mm"], tv["geometry"]["V_op_kV"] * 1e3
    base = out["base_vacuum"]
    key = lambda q: (q["sectors"], q["ws_deg"], q["wr_deg"])
    done = {key(q): q for q in tv.get("search", [])}
    jobs = [(g, ns, ws, wr, T_THICK, base["C_max_pF"], v_op) for ns, (wss, wrs) in THICK_SEARCH.items()
            for ws in wss for wr in wrs if ws >= wr and (ns, ws, wr) not in done]
    with Pool(procs) as pool:
        rows = list(done.values()) + pool.map(_thick_design, jobs, chunksize=1)
    rows.sort(key=lambda q: (-q["sectors"], q["ws_deg"], q["wr_deg"]))
    for q in rows:
        q["L_tube_mm"] = L_TUBE_WOUND + q["L_layout_mm"] - base["L_layout_mm"]
        print(f"t {T_THICK:g} round, {q['sectors']} sectors {q['ws_deg']:4.1f} / {q['wr_deg']:4.1f}: N {q['n_plates']:3d} "
              f"k {q['kappa']:5.2f} z {q['z']:.3f} P_eig {q['P_eigen_W']:5.2f} W  {q['L_es_side_mm']:.0f} mm/side "
              f"-> {q['P_eigen_per_m']:.2f} W/m", flush=True)
    ok = [q for q in rows if q["z"] >= 1.3]
    best = max(ok, key=lambda q: q["P_eigen_per_m"])
    chosen = max([q for q in ok if q["P_eigen_per_m"] >= (1 - KNEE) * best["P_eigen_per_m"]], key=lambda q: q["z"])
    before = {key(tv[k]): tv[k] for k in ("best", "chosen") if k in tv}
    for q in (best, chosen) if chosen is not best else (best,):
        if "P_clamped_W" in before.get(key(q), {}):
            q["P_clamped_W"] = before[key(q)]["P_clamped_W"]
        else:
            q["P_clamped_W"] = clamped_power(_clamp_job(q, q["V_op_kV"]))
        q["P_clamped_per_m"] = q["P_clamped_W"] / (q["L_es_side_mm"] * 1e-3)
        q.update(masses(q, T_THICK))
        print(f"clamped: {q['sectors']} sectors {q['ws_deg']:.1f} / {q['wr_deg']:.1f} -> {q['P_clamped_W']:.2f} W", flush=True)
    tv.pop("best_6_sectors", None)
    tv.update(search=rows, best=dict(best), chosen=dict(chosen), knee=KNEE)
    return tv


def _thick_variant(args):
    """one variant of stage 4c (a worker process): t thick full-round vanes and Ca / Cb plates on the chosen widths,
    n vanes (None: the C_max rule); the stack, the clamped power, the lengths, the masses."""
    g, ns, ws, wr, t, n, c_max, v_op = args
    geo = dict(N_sec=2 * ns, ws_deg=ws, wr_deg=wr, t_vaneMm=t, edge="round", pitch_fixed_mm=g + t)
    if n is None:
        one = stack(g, 1, "air", geo)
        n = max(1, math.ceil((c_max / one["per_gap_max_pF"] + 1) / 2))
    q = stack(g, n, "air", geo, v_op=v_op)
    q.update(gap_mm=g, V_op_kV=v_op / 1e3, sectors=ns, ws_deg=ws, wr_deg=wr, t_vaneMm=t, edge="round", t_plate_mm=t,
             n_rule=args[5] is None)
    q["P_eigen_per_m"] = q["P_eigen_W"] / (q["L_es_side_mm"] * 1e-3)
    q["P_clamped_W"] = clamped_power(_clamp_job(q, q["V_op_kV"]))
    q["P_clamped_per_m"] = q["P_clamped_W"] / (q["L_es_side_mm"] * 1e-3)
    q.update(masses(q, t))
    return q


def thick_compare(out, variants, procs=4):
    """stage 4c: other vane thicknesses (and vane counts) on the chosen widths, each with full-round edges: variants is
    a list of (t_mm, n or None for the C_max rule). Adds each rim's field. Replaces variants already in the results."""
    from multiprocessing import Pool
    tv = out["thick_vanes"]
    c = tv["chosen"]
    base = out["base_vacuum"]
    jobs = [(c["gap_mm"], c["sectors"], c["ws_deg"], c["wr_deg"], t, n, base["C_max_pF"], c["V_op_kV"] * 1e3)
            for t, n in variants]
    with Pool(procs) as pool:
        rows = pool.map(_thick_variant, jobs, chunksize=1)
    for q in rows:
        q["L_tube_mm"] = L_TUBE_WOUND + q["L_layout_mm"] - base["L_layout_mm"]
    keep = [q for q in tv.get("compare", []) if (q["t_vaneMm"], q["n_plates"]) not in {(r["t_vaneMm"], r["n_plates"])
                                                                                     for r in rows}]
    tv["compare"] = sorted(keep + rows, key=lambda q: (q["t_vaneMm"], -q["n_plates"]))
    have = {e["t_mm"] for e in tv["rim_field"]}
    for t in sorted({t for t, _ in variants} - have):
        e = VC.edge_field(t, c["gap_mm"], "round")
        E = e["E_peak_per_V"] * c["V_op_kV"] * 10.0
        tv["rim_field"].append(dict(t_mm=t, r_edge_mm=0.5 * t, E_peak_kV_cm=E, enhancement=e["enhancement"],
                                    angle_deg=e["angle_deg"], E_face_kV_cm=c["V_op_kV"] / c["gap_mm"] * 10.0,
                                    peek_kV_cm=VC.peek_kV_per_cm(0.5 * t), ratio_to_onset=E / VC.peek_kV_per_cm(0.5 * t)))
    tv["rim_field"].sort(key=lambda e: e["t_mm"])
    for q in rows:
        print(f"t {q['t_vaneMm']:g} round {q['ws_deg']:g}/{q['wr_deg']:g}, N {q['n_plates']}"
              f"{' (rule)' if q['n_rule'] else ''}: C {q['C_min_pF']:.0f} / {q['C_max_pF']:.0f} pF, kappa {q['kappa']:.2f}, "
              f"z {q['z']:.3f}, clamped {q['P_clamped_W']:.2f} W, ES {q['L_es_side_mm']:.0f} mm/side, tube "
              f"{q['L_tube_mm']:.0f}, Al rotor {q['rotor_vanes_kg']:.1f} / counter {q['stator_vanes_kg'] + q['ca_plates_kg']:.1f}"
              f" kg", flush=True)
    return tv


if __name__ == "__main__":
    RES = os.path.join(HERE, "air_stack_sizing_results.json")
    if sys.argv[1:] == ["--finish"]:                       # recompute the derived columns of an existing results file
        finish(json.load(open(RES)))
    elif sys.argv[1:2] == ["--thick-compare"]:             # stage 4c: t:n pairs, n "rule" for the C_max rule
        o = json.load(open(RES))
        thick_compare(o, [(float(a.split(":")[0]), None if a.split(":")[1] == "rule" else int(a.split(":")[1]))
                          for a in sys.argv[2:]])
        json.dump(o, open(RES, "w"), indent=1, default=float)
    elif sys.argv[1:] == ["--thick-search"]:               # stage 4b into the existing results file
        o = json.load(open(RES))
        thick_search(o)
        json.dump(o, open(RES, "w"), indent=1, default=float)
    elif sys.argv[1:2] == ["--thick"]:                     # stage 4 into the existing results file
        o = json.load(open(RES))
        thick_vanes(o, t_plate=float(sys.argv[2]) if len(sys.argv) > 2 else None)
        json.dump(o, open(RES, "w"), indent=1, default=float)
    else:
        main()
