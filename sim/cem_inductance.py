#!/usr/bin/env python3
"""sim/cem_inductance.py -- the C-EM's inductance against the utron's angle, its winding, and what it gives.

MAGNETIC MODEL (scalar-potential analogy, classic) [ME/IR]:
  * the C-EM core and the utron are ideal iron (mu -> infinity): magnetic equipotentials. The utron uses the
    laminated M235-35A stack; its mu_eff ~ 270 adds < 1 % of the gap reluctance (sim/utron_material.py).
  * the winding (bobbin on the spine, |z| <= WIN_HALF) sets the spine surface potential, linear in z:
    12 thin spine plates (1 mm iron, 3 mm gap) at psi = (z + WIN_HALF) / (2 WIN_HALF); the top half-core
    (top jaw, arm, spine stub) at psi = 1, the bottom half at 0.
  * Laplace for psi with mu0 everywhere else = Laplace for V with eps0: the solver's Maxwell matrix C (F) is the
    permeance matrix times eps0/mu0. The utron floats: zero net flux, so it is eliminated (Schur complement).
  * L = N^2 mu0 (psi^T C_red psi / eps0) / 6 (the solver's C counts the 6 periodic copies).
  * spurious term: the 11 plate gaps carry parallel-plate energy that iron would not have: subtracted
    analytically (A_spine / g * dpsi^2 per gap); it does not depend on the angle, so dL/dtheta is unaffected.
WINDING: the bobbin window from the STEP (sim/motor_geometry.py src): ~48 mm between flanges, ~13 mm deep, on a
spine of 25 x 30 mm with a ~2 mm bobbin tube. HV coil: enamelled wire with interlayer film, fill 0.45.  [RH]
Usage: python3 sim/cem_inductance.py design | sweep | report
"""
import json
import math
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path[:0] = [HERE]
RT_DIR = os.path.join(ROOT, "docs", "geometry", "rt")
TAG = "cem-magnetic"
MOTOR_JSON = os.path.join(ROOT, "docs", "geometry", "motor", "motor-il2f-6563b90d-rc40.json")
COND = "Cu (conductor proxy) "
MU0 = 4e-7 * math.pi
EPS0_MM = 8.8541878128e-15                      # F/mm (field_solve units)

# geometry (local x radial from the utron centre, z axial), from the squared core and bobbin scans [IR]
JAW = (-6.0, 14.0, 30.0, 59.0)                  # x0, x1, z0, z1 (top; bottom mirrored)
ARM = (14.0, 93.0, 37.0, 59.0)
SPINE_X = (93.0, 118.0)
SPINE_Z = 52.0
CORE_W = 30.0                                   # tangential, mm
WIN_HALF = 24.0                                 # winding |z| (flange inner faces ~ +-24.5)
N_PLATE, PLATE_T = 12, 1.0                      # spine plates under the winding (1 mm iron, 3 mm gap)
THETAS = [round(1.5 * k, 3) for k in range(21)] # rotor angle; the utron (15) aligns with C-EM A (30) at 15


def _sector(name, x0, x1, z0, z1, ru, th, w_mm, node, body):
    r0, r1 = ru + x0, ru + x1
    w = math.degrees(w_mm / (0.5 * (r0 + r1)))
    return dict(name=name, shape="sector", r_in=r0, r_out=r1, start_deg=(th - w / 2) % 360.0, w_deg=w,
                z0=z0, z1=z1, node=node, body=body, material=COND + "iron (magnetic equipotential)", role="magnetic")


def design():
    m = json.load(open(MOTOR_JSON))
    ru = m["placement"]["r_utron_centre"]
    pcs = m["pieces"]
    th = 30.0                                     # C-EM A2 station
    parts = []
    for s, net in ((1, "top"), (-1, "bot")):
        for nm, (x0, x1, z0, z1) in (("jaw", JAW), ("arm", ARM)):
            a, b = sorted((s * z0, s * z1))
            parts.append(_sector(f"{nm}_{net}", x0, x1, a, b, ru, th, CORE_W, net, "stator"))
        a, b = sorted((s * WIN_HALF, s * SPINE_Z))
        parts.append(_sector(f"spine_{net}", SPINE_X[0], SPINE_X[1], a, b, ru, th, CORE_W, net, "stator"))
    pitch = 2 * WIN_HALF / N_PLATE
    for k in range(N_PLATE):
        zc = -WIN_HALF + (k + 0.5) * pitch
        parts.append(_sector(f"plate_{k:02d}", SPINE_X[0], SPINE_X[1], zc - PLATE_T / 2, zc + PLATE_T / 2, ru, th, CORE_W,
                             f"p{k:02d}", "stator"))
    u = pcs["utron_core"]                         # the iron only (the coils are open / omitted)
    parts.append(_sector("utron", u["bb_min"][0], u["bb_max"][0], u["bb_min"][2], u["bb_max"][2], ru, 15.0,
                         u["bb_max"][1] - u["bb_min"][1], "U", "rotor AB"))
    d = dict(schema="pump-geometry/1", parts=parts, note="magnetic analogue of one C-EM per 60 deg (A2) and its utron",
             r_utron_centre=ru)
    path = os.path.join(RT_DIR, f"{TAG}.design.json")
    json.dump(d, open(path, "w"), indent=0)
    return path, d


def psi_vector(names):
    pitch = 2 * WIN_HALF / N_PLATE
    v = {}
    for n in names:
        if n == "top":
            v[n] = 1.0
        elif n == "bot":
            v[n] = 0.0
        elif n.startswith("p"):
            k = int(n[1:]); zc = -WIN_HALF + (k + 0.5) * pitch
            v[n] = (zc + WIN_HALF) / (2 * WIN_HALF)
    return v


def permeance(names, C_pF):
    """mm (P / mu0, per C-EM): psi^T C_red psi / eps0 / 6, the utron eliminated, minus the plate-gap term."""
    C = np.asarray(C_pF, float) * 1e-12
    fi = [i for i, n in enumerate(names) if n == "U"]
    di = [i for i, n in enumerate(names) if n != "U"]
    Cr = C[np.ix_(di, di)] - (C[np.ix_(di, fi)] @ np.linalg.solve(C[np.ix_(fi, fi)], C[np.ix_(fi, di)]) if fi else 0.0)
    v = psi_vector([names[i] for i in di])
    x = np.array([v[names[i]] for i in di])
    P = float(x @ Cr @ x) / EPS0_MM / 6.0
    A = (SPINE_X[1] - SPINE_X[0]) * CORE_W
    g = 2 * WIN_HALF / N_PLATE - PLATE_T
    spur = (N_PLATE - 1) * A / g * (1.0 / N_PLATE) ** 2
    return P - spur, P, spur


# ---------------------------------------------------------------------------------------------------------
# winding and electrical numbers
# ---------------------------------------------------------------------------------------------------------
WIN_LEN, WIN_DEPTH, TUBE = 48.0, 13.0, (29.0, 33.0)   # mm: window length, depth; bobbin tube outside (x, y)
FILL = 0.45
RHO_CU = 1.72e-8
AWG = [(0.25, "0.25 mm"), (0.315, "0.315 mm"), (0.4, "0.40 mm"), (0.5, "0.50 mm"), (0.63, "0.63 mm"), (0.8, "0.80 mm"),
       (1.0, "1.00 mm")]


def winding(d_mm, grade_add=0.04):
    """turns, layers, resistance for bare copper diameter d (grade-2 enamel adds ~0.04-0.06 mm)."""
    do = d_mm + grade_add
    N = int(FILL * WIN_LEN * WIN_DEPTH / (math.pi / 4 * do ** 2))
    layers = max(1, int(round(N / (WIN_LEN / do))))
    mlt = 2 * (TUBE[0] + TUBE[1]) + 4 * WIN_DEPTH       # mm, mean turn (square-ish around the tube)
    R = RHO_CU * N * mlt * 1e-3 / (math.pi / 4 * (d_mm * 1e-3) ** 2)
    return dict(d_mm=d_mm, N=N, layers=layers, mlt_mm=mlt, wire_m=N * mlt * 1e-3, R_ohm=R)


def _main():
    cmd = sys.argv[1] if len(sys.argv) > 1 else "design"
    if cmd == "design":
        p, d = design(); print(p, len(d["parts"]))
    elif cmd == "sweep":
        import round_trip as RTR
        procs = int(sys.argv[2]) if len(sys.argv) > 2 else 2
        sols = RTR.sweep(os.path.join(RT_DIR, f"{TAG}.design.json"), THETAS, level="c", enclosure=None, procs=procs, log=print)
        json.dump(dict(thetas=THETAS, sols=sols), open(os.path.join(RT_DIR, f"{TAG}.sweep.json"), "w"))
    elif cmd == "report":
        report()


def report():
    d = json.load(open(os.path.join(RT_DIR, f"{TAG}.sweep.json")))
    rows = []
    for th, s in zip(d["thetas"], d["sols"]):
        P, Praw, spur = permeance(s["names"], s["C"])
        rows.append((th, P, Praw, spur))
    out = dict(thetas=[r[0] for r in rows], P_mm=[r[1] for r in rows], P_raw_mm=[r[2] for r in rows], spur_mm=rows[0][3])
    json.dump(out, open(os.path.join(HERE, "cem_inductance_results.json"), "w"), indent=1)
    for r in rows:
        print(f"theta {r[0]:5.1f}  P {r[1]:8.2f} mm  (raw {r[2]:.2f}, gap term {r[3]:.2f})")
    return out


if __name__ == "__main__":
    _main()


# ---------------------------------------------------------------------------------------------------------
# the pump with a given C-EM (L, R per coil): z, and the per-pulse integral of i^2 from the engine ledger
# ---------------------------------------------------------------------------------------------------------
def pump_with(L1_H, R1_ohm, steps=("split", "motor", "utron"), v_peak=20e3):
    """the field-ledger case (sim/motor_field.py step 6) with the C-EM L1 / R1 per coil. Returns z and, per side
    and per firing, int I^2 dt of the lumped group (A^2 s), with the eigen-state scaled so the largest node
    voltage over the cycle is v_peak."""
    import motor_field as MF
    import rt_engine as RT
    import pump_synth as SY
    import round_trip as RTR
    th, prof, _ = MF.assemble(steps)
    cfg = SY.engine_cfg(*SY.sized(dict(g_vMm=3.0)))
    cm = RTR.CModel(th, prof, tip_deg=15.0)
    net = RT.build_net(cfg, cmodel=cm)
    R_t = (1 / math.sqrt(MF.L_TANK * 789e-12)) * MF.L_TANK / MF.C_TANK_Q
    net.inds.append(("L_tank_chain", net.n("R-A"), net.n("R-B"), MF.L_TANK, R_t, "lx"))
    for gname, node, mid in (("SG1", "2", "mA"), ("SG2", "3", "mB")):
        k = [i for i, g in enumerate(net.gaps) if g[0] == gname][0]
        g = list(net.gaps[k]); ni, nm = net.n(node), net.n(mid)
        j = 1 if g[1] == ni else 2
        g[j] = nm; net.gaps[k] = tuple(g)
        net.inds.append((f"L_{mid}", ni, nm, L1_H / 6, R1_ohm / 6, "lx"))
        net.caps.append((f"Cfloor_{mid}", nm, RT.GND, 0.5e-12))
        net.caps.append((f"Cscreen_{mid}", nm, ni, 6 * MF.SCREEN_PF_PER_COIL * 1e-12))
    m = RT.run(net, cfg, record=True)
    rec = m["rec"]
    V = np.array([p["V"] for p in rec["points"]])
    s = v_peak / np.abs(V).max()
    by = rec["by"]
    i2 = {mid: by.get(f"L_{mid}_R", 0.0) * s ** 2 / (R1_ohm / 6) for mid in ("mA", "mB")}
    return dict(z=m["z"], converged=bool(m["converged"]), int_I2_lumped=i2, W_belt_J=rec["ledger"]["W"] * s ** 2,
                scale=s, by={k: v * s ** 2 for k, v in by.items()})
