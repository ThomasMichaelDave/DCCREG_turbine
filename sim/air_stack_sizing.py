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
  V_op (sim/bicone_drive.py's netlist in ngspice, clamp BV = V_op), the varicap and Ca stack lengths, the tube's length
  (the wound build's 802 mm with its electrostatic stacks swapped), the rotor-vane mass.
The tube's other dimensions are unchanged: r 50..150 mm, 6 sectors (stator 30 deg, rotor 22 deg), 1.5 mm Al vanes.
Stage 2 (geometry_search): at 6 / 8 / 10 mm, the sector count (3, 4, 6) and the stator / rotor widths, because at wide
gaps the fringe field between a rotor vane and the next stator sector keeps C_min high and kappa collapses; ranked by
the eigen-cycle power (stack_sizing ledger at V_op) per mm of stack.
Usage: python3 sim/air_stack_sizing.py
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

GAPS = (3.0, 5.0, 6.0, 8.0, 10.0, 12.0, 15.0)
MARGIN = 30.0 / 20.0               # the vacuum design's breakdown / operating ratio
RPM, F = 1200.0, 120.0
L_TUBE_WOUND, L_ES_SIDE_WOUND = 802.0, None       # the built tube; its electrostatic stacks are measured below
T_VANE = SS.TUBE_DEFAULTS["t_vaneMm"]


def plates(g, n, diel, geo=None):
    return dict(dict(g_vMm=g, n_plates=n, dielectric=diel, pitch_fixed_mm=g + T_VANE, bucket=False), **(geo or {}))


_CAPS = {}
_tube_caps = SS.tube_caps


def _cached_tube_caps(p):
    """stack_sizing.tube_caps with the per-gap cell solutions cached by geometry (N only multiplies them)."""
    key = tuple(p[k] for k in ("g_vMm", "t_vaneMm", "N_sec", "ws_deg", "wr_deg", "r_inMm", "r_outMm", "h_mm", "n_r",
                               "dielectric"))
    if key not in _CAPS:
        _CAPS[key] = _tube_caps(dict(p, n_plates=1))
    one = _CAPS[key]
    n_gap = 2 * int(p["n_plates"]) - 1
    return dict(one, n_gap=n_gap, C_max=n_gap * one["per_gap_max_pF"],
                C_min=n_gap * one["per_gap_min_pF"] + p["C_edge_pF"])


SS.tube_caps = _cached_tube_caps


def stack(g, n, diel, geo=None, v_op=None):
    lad = SS.size_stack("tube", plates(g, n, diel, geo), dict(rpm=RPM))
    tc, tg = lad["tube_caps"], lad["tube_geometry"]
    if v_op:
        SS.V_OP = v_op                                     # the eigen-cycle ledger at this stack's operating peak
    z = SS.z_stack(lad, topology="core", ledger=bool(v_op))
    return dict(n_plates=n, n_gap=tc["n_gap"], C_max_pF=tc["C_max"], C_min_pF=tc["C_min"], kappa=tc["C_max"] / tc["C_min"],
                Ca_pF=lad["ladder"]["Ca"]["value"], z=z["z"], L_varicap_mm=tg["L_varicap_mm"], n_gap_ca=tg["n_gap_ca"],
                L_ca_mm=tg["L_ca_mm"], m_rotor_vanes_kg=tg["m_rotor_vanes_kg"], per_gap_max_pF=tc["per_gap_max_pF"],
                per_gap_min_pF=tc["per_gap_min_pF"], cycles_per_rev=(geo or {}).get("N_sec", SS.TUBE_DEFAULTS["N_sec"]) // 2,
                P_eigen_W=(z.get("ledger") or {}).get("P_surplus_W"))


def clamped_power(args):
    """the clamped pump power (W) at 1200 rpm: sim/bicone_drive.py's diodes-only netlist with this stack's caps."""
    cmin, cmax, ca, v_op = args
    BD.F, BD.CMIN, BD.CMAX, BD.CA, BD.V_OP = F, cmin * 1e-12, cmax * 1e-12, ca * 1e-12, v_op
    txt, vecs, pk = BD.deck("diodes")
    txt = txt.replace("wrdata out.dat " + " ".join(vecs), "wrdata out.dat v(e_limit)")      # one vector: small file
    with tempfile.TemporaryDirectory() as d:
        open(os.path.join(d, "x.cir"), "w").write(txt)
        subprocess.run(["ngspice", "-b", "x.cir"], capture_output=True, text=True, timeout=3600, cwd=d)
        raw = np.loadtxt(os.path.join(d, "out.dat"))
    t, y = raw[:, 0], raw[:, 1]
    t0 = (24 - 8) / F
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
                    q.update(gap_mm=g, V_op_kV=v_op / 1e3, sectors=ns, ws_deg=geo["ws_deg"], wr_deg=geo["wr_deg"],
                             L_es_side_mm=q["L_varicap_mm"] + q["L_ca_mm"])
                    q["P_eigen_per_m"] = q["P_eigen_W"] / (q["L_es_side_mm"] * 1e-3)
                    out.append(q)
                    print(f"g {g:4.1f} sectors {ns} ws {geo['ws_deg']:5.1f} wr {geo['wr_deg']:5.1f}: N {n:3d} k {q['kappa']:5.2f} "
                          f"z {q['z']:.3f} P_eig {q['P_eigen_W']:6.2f} W  stacks {q['L_es_side_mm']:.0f} mm/side", flush=True)
    return out


def main():
    base = stack(3.0, 8, "vacuum")                         # the built design
    base_es_side = base["L_varicap_mm"] + base["L_ca_mm"]
    rows, jobs = [], [(base["C_min_pF"], base["C_max_pF"], base["Ca_pF"], 20e3)]
    for g in GAPS:
        v_bd = SS.gap_breakdown_kV(g, "air")
        v_op = v_bd / MARGIN
        one = stack(g, 1, "air")                           # per-gap C (N enters only as the 2N - 1 gaps)
        n_c = max(1, math.ceil((base["C_max_pF"] / one["per_gap_max_pF"] + 1) / 2))
        r = dict(gap_mm=g, V_bd_kV=v_bd, V_op_kV=v_op, same_C=stack(g, n_c, "air"))
        rows.append(r)
        q = r["same_C"]
        jobs.append((q["C_min_pF"], q["C_max_pF"], q["Ca_pF"], v_op * 1e3))
    print(f"stacks sized; {len(jobs)} clamped-power runs", flush=True)
    P = [clamped_power(j) for j in jobs]                  # one at a time: each ngspice run holds ~0.4 GB of vectors
    base["P_clamped_W"] = P[0]
    for r, p in zip(rows, P[1:]):
        r["same_C"]["P_clamped_W"] = p
        # the power scales with the number of working gaps at fixed kappa and V_op: the N for the vacuum design's power
        n_gap_p = r["same_C"]["n_gap"] * base["P_clamped_W"] / p
        n_p = max(1, math.ceil((n_gap_p + 1) / 2))
        q = stack(r["gap_mm"], n_p, "air")
        q["P_clamped_W_est"] = p * q["n_gap"] / r["same_C"]["n_gap"]
        r["same_power"] = q
        for key in ("same_C", "same_power"):
            s = r[key]
            s["L_es_side_mm"] = s["L_varicap_mm"] + s["L_ca_mm"]
            s["L_tube_mm"] = L_TUBE_WOUND + 2 * (s["L_es_side_mm"] - base_es_side)
    out = dict(rpm=RPM, margin=MARGIN, base_vacuum=dict(base, L_es_side_mm=base_es_side, L_tube_mm=L_TUBE_WOUND,
                                                         V_op_kV=20.0, V_bd_kV=30.0), rows=rows)
    json.dump(out, open(os.path.join(HERE, "air_stack_sizing_results.json"), "w"), indent=1, default=float)
    b = base
    print(f"vacuum 3 mm, N 8: C {b['C_min_pF']:.0f}-{b['C_max_pF']:.0f} pF k {b['kappa']:.1f} z {b['z']:.3f} "
          f"P {b['P_clamped_W']:.1f} W at 20 kV; stacks {base_es_side:.0f} mm/side, tube {L_TUBE_WOUND:.0f} mm")
    for r in rows:
        for key in ("same_C", "same_power"):
            s = r[key]
            P_ = s.get("P_clamped_W", s.get("P_clamped_W_est"))
            print(f"air {r['gap_mm']:4.1f} mm ({r['V_bd_kV']:.1f} kV bd, V_op {r['V_op_kV']:.1f} kV) {key:10s}: N {s['n_plates']:3d} "
                  f"C {s['C_min_pF']:.0f}-{s['C_max_pF']:.0f} pF k {s['kappa']:.1f} z {s['z']:.3f} P {P_:.1f} W | "
                  f"varicap {s['L_varicap_mm']:.0f} + Ca {s['L_ca_mm']:.0f} mm/side, tube {s['L_tube_mm']:.0f} mm, "
                  f"rotor vanes {s['m_rotor_vanes_kg']:.1f} kg")


if __name__ == "__main__":
    main()
