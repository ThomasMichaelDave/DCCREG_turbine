"""sim/vane_matrix.py -- the electrostatic vane stack for AIR as a full matrix (the designer's sweep): the vane gap g,
the vane thickness t (full-round edges; the Ca / Cb plates alike), the outer radius r_out of the rotor and stator vanes
(r_in 50 mm), the vanes per varicap per side N (stator = rotor) and the sector width w (6 sectors, stator = rotor).
Each design goes through sim/air_stack_sizing.stack (stack_sizing's ladder, layout and bare de Queiroz core; the
full-round cell of sim/vane_cell, cached by geometry):
  - the air hold-off and the operating peak V_op = V_bd(g) / 1.5 [RH: the margin];
  - C_max, C_min, kappa, Ca; the core's z and its eigen-cycle power at V_op, 1200 rpm relative;
  - the stacks' length per side and the tube's length (layout), the aluminium (rotor; counter-rotor), the rotor vanes'
    inertia;
  - the rims' corona onset (vane_cell.edge_field + Peek, per t and g): the operating peak at which the rim field reaches
    the onset, on a smooth (m 1) and a handled (m 0.85) surface [RH].
A dozen designs also get the clamped power (sim/bicone_drive.py's netlist in ngspice) to calibrate the eigen-cycle
figure; the ratio tracks the gain, so it is fitted as a + b (z - 1) and every row carries the calibrated estimate. Writes sim/vane_matrix_results.json and .csv.
[OC] the field solves and the core; [IR] the 2-D cell, the full round, the fixed 20 pF stray and 2 pF rim floor;
[RH] the 1.5 margin, the surface factor, the calibration's spread.
Usage: python3 sim/vane_matrix.py [--procs 4]      (about 30 min on 4 cores)
       python3 sim/vane_matrix.py --finish         (the calibrated columns only, from the saved results)
"""
import csv
import json
import math
import os
import sys
import time

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import air_stack_sizing as AS      # noqa: E402
import stack_sizing as SS          # noqa: E402
import vane_cell as VC             # noqa: E402

GAPS = (3.0, 4.0, 5.0, 6.0, 8.0, 10.0)
THICK = (1.5, 2.0, 2.5, 3.0, 4.0)
R_OUT = (150.0, 175.0, 200.0, 250.0, 300.0)
NV = (4, 6, 8, 10, 12, 16)
WIDTHS = (18.0, 22.0, 26.0)                       # stator = rotor sector width (deg), 6 sectors on a 60 deg pitch
SECTORS = 6
M_HANDLED = 0.85                                  # Peek's surface factor for a handled surface [RH]
Z_FLOOR = 1.3                                     # the gain floor of the searches
CALIB = [(g, 3.0, ro, 22.0, n) for ro in (150.0, 300.0) for g in (4.0, 8.0) for n in (6, 16)] + \
        [(6.0, 2.5, 200.0, 26.0, 10), (3.0, 1.5, 250.0, 18.0, 8), (10.0, 4.0, 250.0, 22.0, 4), (5.0, 2.0, 175.0, 22.0, 12)]
OUT = os.path.join(HERE, "vane_matrix_results")


def geo(t, ro, w, g):
    return dict(N_sec=2 * SECTORS, ws_deg=w, wr_deg=w, t_vaneMm=t, edge="round", pitch_fixed_mm=g + t, r_outMm=ro)


def inertia(q, ro):
    """the rotor vanes' moment of inertia (kg m^2), sectors + inner rings, both sides."""
    ri, rs = SS.TUBE_DEFAULTS["r_inMm"] * 1e-3, SS.SLEEVE_R * 1e-3
    r1 = ro * 1e-3
    t, n = q["t_vaneMm"] * 1e-3, q["n_plates"]
    a_sec = SECTORS * q["ws_deg"] / 360.0 * math.pi * (r1 * r1 - ri * ri)
    a_ring = math.pi * (ri * ri - rs * rs)
    rho = SS.TUBE_DEFAULTS["rho_vane"]
    return 2 * n * rho * t * (a_sec * 0.5 * (ri * ri + r1 * r1) + a_ring * 0.5 * (rs * rs + ri * ri))


def _geometry(args):
    """one geometry (a worker): every N on it."""
    g, t, ro, w, base_layout = args
    v_op = SS.gap_breakdown_kV(g, "air") / AS.MARGIN * 1e3
    rows = []
    for n in NV:
        q = AS.stack(g, n, "air", geo(t, ro, w, g), v_op=v_op)
        q.update(gap_mm=g, t_vaneMm=t, r_outMm=ro, ws_deg=w, wr_deg=w, sectors=SECTORS, V_op_kV=v_op / 1e3,
                 V_bd_kV=SS.gap_breakdown_kV(g, "air"), L_tube_mm=AS.L_TUBE_WOUND + q["L_layout_mm"] - base_layout)
        q.update(AS.masses(q, t, ro=ro))
        q["I_rotor_kgm2"] = inertia(q, ro)
        q["P_eigen_per_m"] = q["P_eigen_W"] / (q["L_es_side_mm"] * 1e-3)
        for k in ("m_rotor_vanes_kg",):
            q.pop(k, None)
        rows.append(q)
    return rows


def _clamp(args):
    g, t, ro, w, n = args
    v_op = SS.gap_breakdown_kV(g, "air") / AS.MARGIN * 1e3
    q = AS.stack(g, n, "air", geo(t, ro, w, g), v_op=v_op)
    return dict(gap_mm=g, t_vaneMm=t, r_outMm=ro, ws_deg=w, n_plates=n, P_eigen_W=q["P_eigen_W"],
                P_clamped_W=AS.clamped_power(AS._clamp_job(q, v_op / 1e3)))


def main(procs=4):
    from multiprocessing import Pool
    t0 = time.time()
    base_layout = AS.stack(3.0, 8, "vacuum")["L_layout_mm"]
    jobs = [(g, t, ro, w, base_layout) for ro in R_OUT[::-1] for g in GAPS for t in THICK for w in WIDTHS]
    rows = []
    with Pool(procs) as pool:
        for k, part in enumerate(pool.imap_unordered(_geometry, jobs, chunksize=1)):
            rows += part
            if k % 25 == 0:
                print(f"{k + 1} / {len(jobs)} geometries, {time.time() - t0:.0f} s", flush=True)
    rims = {}
    for t in THICK:
        for g in GAPS:
            e = VC.edge_field(t, g, "round")
            v_op = SS.gap_breakdown_kV(g, "air") / AS.MARGIN
            E = e["E_peak_per_V"] * v_op * 10.0
            on = VC.peek_kV_per_cm(0.5 * t)
            rims[(t, g)] = dict(t_mm=t, gap_mm=g, E_peak_kV_cm=E, enhancement=e["enhancement"], peek_kV_cm=on,
                                V_onset_kV=v_op * on / E, V_onset_handled_kV=M_HANDLED * v_op * on / E)
    print(f"rims done, {time.time() - t0:.0f} s", flush=True)
    with Pool(procs) as pool:
        cal = pool.map(_clamp, CALIB, chunksize=1)
    print(f"calibration runs done, {time.time() - t0:.0f} s", flush=True)
    for q in rows:
        r = rims[(q["t_vaneMm"], q["gap_mm"])]
        q.update(V_onset_kV=r["V_onset_kV"], V_onset_handled_kV=r["V_onset_handled_kV"],
                 corona_ok=r["V_onset_handled_kV"] >= q["V_op_kV"], gain_ok=q["z"] >= Z_FLOOR)
    rows.sort(key=lambda q: (q["r_outMm"], q["gap_mm"], q["t_vaneMm"], q["ws_deg"], q["n_plates"]))
    out = dict(axes=dict(gap_mm=GAPS, t_mm=THICK, r_out_mm=R_OUT, n_per_varicap=NV, width_deg=WIDTHS, sectors=SECTORS),
               margin=AS.MARGIN, rpm=AS.RPM, m_handled=M_HANDLED, z_floor=Z_FLOOR, calibration=dict(rows=cal),
               rims=list(rims.values()), rows=rows)
    finish(out)


def finish(out):
    """the calibrated clamped power: the ratio clamped / eigen-cycle tracks the gain, so it is fitted as a + b (z - 1)
    over the calibration designs [IR] and applied to every row; then the files are written."""
    rows = out["rows"]
    idx = {(q["gap_mm"], q["t_vaneMm"], q["r_outMm"], q["ws_deg"], q["n_plates"]): q for q in rows}
    cal = out["calibration"]["rows"]
    for c in cal:
        c["z"] = idx[(c["gap_mm"], c["t_vaneMm"], c["r_outMm"], c["ws_deg"], c["n_plates"])]["z"]
        c["ratio"] = c["P_clamped_W"] / c["P_eigen_W"]
    zz, rr = np.array([c["z"] - 1.0 for c in cal]), np.array([c["ratio"] for c in cal])
    b, a = np.polyfit(zz, rr, 1)
    for c in cal:
        c["fit_residual"] = c["ratio"] / (a + b * (c["z"] - 1.0)) - 1.0
    out["calibration"].update(a=float(a), b=float(b), residual_min=min(c["fit_residual"] for c in cal),
                              residual_max=max(c["fit_residual"] for c in cal))
    for q in rows:
        k = a + b * (q["z"] - 1.0)
        q.update(k_cal=k, P_clamped_est_W=k * q["P_eigen_W"], P_clamped_est_per_m=k * q["P_eigen_per_m"])
    print(f"calibration: clamped / eigen = {a:.3f} + {b:.3f} (z - 1), residuals {100 * out['calibration']['residual_min']:+.1f}"
          f" to {100 * out['calibration']['residual_max']:+.1f} %", flush=True)
    json.dump(out, open(OUT + ".json", "w"), indent=0, default=float)
    cols = ["gap_mm", "t_vaneMm", "r_outMm", "ws_deg", "n_plates", "V_op_kV", "C_min_pF", "C_max_pF", "kappa", "Ca_pF", "z",
            "P_eigen_W", "P_clamped_est_W", "P_clamped_est_per_m", "L_es_side_mm", "L_tube_mm", "rotor_vanes_kg",
            "stator_vanes_kg", "ca_plates_kg", "I_rotor_kgm2", "V_onset_kV", "V_onset_handled_kV", "corona_ok", "gain_ok"]
    with open(OUT + ".csv", "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(cols)
        for q in rows:
            w.writerow([round(q[c], 4) if isinstance(q[c], float) else q[c] for c in cols])
    print(f"{len(rows)} designs -> {OUT}.json / .csv", flush=True)


if __name__ == "__main__":
    if sys.argv[1:] == ["--finish"]:                   # re-derive the calibrated columns from the saved results
        finish(json.load(open(OUT + ".json")))
    else:
        main(int(sys.argv[sys.argv.index("--procs") + 1]) if "--procs" in sys.argv else 4)
