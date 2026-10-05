#!/usr/bin/env python3
"""sim/motor_field.py -- the pump with the placed motor, in the 3-D field model, against netlist v4.

Design: r5N2f (= the CAD build il2f-6563b90d) plus the motor of sim/motor_geometry.py, in the field solver's
primitives (annular sectors):
  * C-EM cores (with their coils): the squared core section, decomposed into (r, z) boxes, 30 mm tangential
    (a sector of constant angle, set at each box's mid radius). Nodes: A cores on '2', B cores on '3'
    (bonded to the coil's rail end, D-6). The coil winding is lumped with its core.            [IR]
  * utrons (with their open coils): one floating conductor each, the envelope sector. Net 'U'; the six are
    one net by the 60-degree periodicity.                                                       [IR]
  * v4: SG1 spheres and stems -> net 'mA', SG2 -> net 'mB' (the coil-gap node). Their leads stay on
    '2' / '3', standing in for the screen of a screened lead whose inner conductor is the mid node.  [OC]
Sweep: round_trip.sweep (level c, free basis like r5N2f). Engine: rt_engine with the CModel, plus the v4
wiring: SG1 re-noded 2 -> mA, the lumped coil 2 -> mA (L/6, R/6), the screen capacitance across it, and the
parallel tank across R-A / R-B.
Usage: python3 sim/motor_field.py design | sweep [n_theta] | z
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
BASE = os.path.join(RT_DIR, "r5N2f.design.json")
TAG = "r5N2f-motor"
MOTOR_JSON = os.path.join(ROOT, "docs", "geometry", "motor", "motor-il2f-6563b90d-rc40.json")
COND = "Cu (conductor proxy) "                         # field_solve conductor key ("cu ")


def core_boxes(step_dir=None, h=1.0, snap=2.0):
    """the squared C-EM core section at y = 0 (local x radial, z axial) as a few rectangles."""
    from OCP.STEPControl import STEPControl_Reader
    from OCP.BRepClass3d import BRepClass3d_SolidClassifier
    from OCP.gp import gp_Pnt
    from OCP.TopAbs import TopAbs_IN
    step_dir = step_dir or os.path.join(ROOT, "docs", "geometry", "motor", "src")
    r = STEPControl_Reader(); r.ReadFile(os.path.join(step_dir, "cem_core.step")); r.TransferRoots(); s = r.OneShape()
    xs = np.arange(-15.0, 150.0, h); zs = np.arange(-62.0, 62.0 + 1e-9, h)
    rows = []
    for z in zs:
        ins = np.array([BRepClass3d_SolidClassifier(s, gp_Pnt(float(x), 0.0, float(z)), 1e-4).State() == TopAbs_IN for x in xs])
        iv = []
        k = 0
        while k < len(xs):
            if ins[k]:
                j = k
                while j + 1 < len(xs) and ins[j + 1]:
                    j += 1
                iv.append((round((xs[k] - h / 2) / snap) * snap, round((xs[j] + h / 2) / snap) * snap))
                k = j + 1
            else:
                k += 1
        rows.append((float(z), tuple(iv)))
    boxes = []                                            # merge runs of rows with the same intervals
    k = 0
    while k < len(rows):
        j = k
        while j + 1 < len(rows) and rows[j + 1][1] == rows[k][1]:
            j += 1
        for a, b in rows[k][1]:
            boxes.append(dict(x0=a, x1=b, z0=rows[k][0] - h / 2, z1=rows[j][0] + h / 2))
        k = j + 1
    return boxes


# the squared core section (local x radial from the utron centre, z axial), from a scan of src/cem_core.step at
# y = 0 (core_boxes() at 5 mm columns): jaw tips x -6..14 (inner face z 30), arms x 14..93 (window face z 34..39,
# taken as 37), spine x 93..118 (|z| <= 46..57, taken as 52); bolt holes filled.                    [IR]
CORE_BOXES = [dict(x0=-6.0, x1=14.0, z0=30.0, z1=59.0), dict(x0=-6.0, x1=14.0, z0=-59.0, z1=-30.0),
              dict(x0=14.0, x1=93.0, z0=37.0, z1=59.0), dict(x0=14.0, x1=93.0, z0=-59.0, z1=-37.0),
              dict(x0=93.0, x1=118.0, z0=-52.0, z1=52.0)]


def sector(name, r0, r1, z0, z1, th_mid, w_mm, node, body, mat):
    rm = 0.5 * (r0 + r1)
    w = math.degrees(w_mm / rm)
    return dict(name=name, shape="sector", r_in=float(r0), r_out=float(r1), start_deg=float((th_mid - w / 2) % 360.0),
                w_deg=float(w), z0=float(z0), z1=float(z1), node=node, body=body, material=mat, role="motor")


def design():
    d = json.load(open(BASE))
    m = json.load(open(MOTOR_JSON))
    ru = m["placement"]["r_utron_centre"]
    pcs = m["pieces"]
    for p in d["parts"]:                                  # v4: the rail-gap spheres and stems are the mid node
        if p["name"].startswith(("SG1_sph", "SG1_stem")):
            p["node"] = "mA"
        elif p["name"].startswith(("SG2_sph", "SG2_stem")):
            p["node"] = "mB"
    boxes = CORE_BOXES
    cw = 30.0                                             # core plate, mm (cem_squaring)
    coil = pcs["cem_coil"]; u = pcs["utron_core"]
    cu = [pcs[k] for k in ("utron_core", "utron_coil_1", "utron_coil_2")]
    ux0 = min(q["bb_min"][0] for q in cu); ux1 = max(q["bb_max"][0] for q in cu)
    uy = max(max(abs(q["bb_min"][1]), abs(q["bb_max"][1])) for q in cu)
    uz = max(max(abs(q["bb_min"][2]), abs(q["bb_max"][2])) for q in cu)
    seen = set()
    for p in m["parts"]:
        th = p["place"]["theta_deg"]
        if p["piece"] == "cem_core":
            lab = p["name"].split("_")[1]; node = "2" if lab[0] == "A" else "3"
            for i, b in enumerate(boxes):
                d["parts"].append(sector(f"CEM_{lab}_core_{i}", ru + b["x0"], ru + b["x1"], b["z0"], b["z1"], th, cw, node,
                                         "stator", COND + "C-EM core"))
            cb = coil
            d["parts"].append(sector(f"CEM_{lab}_coil", ru + cb["bb_min"][0], ru + cb["bb_max"][0], cb["bb_min"][2], cb["bb_max"][2],
                                     th, cb["bb_max"][1] - cb["bb_min"][1], node, "stator", COND + "C-EM coil (lumped on the core)"))
        elif p["piece"] == "utron_core" and th not in seen:
            seen.add(th)
            d["parts"].append(sector(f"UTRON_{p['name'].split('_')[1]}", ru + ux0, ru + ux1, -uz, uz, th, 2 * uy, "U",
                                     "rotor AB", COND + "utron (core + open coil), floating"))
    d["motor"] = dict(source=os.path.relpath(MOTOR_JSON, ROOT), r_utron_centre=ru, core_boxes=boxes)
    return d


def write_design():
    d = design()
    path = os.path.join(RT_DIR, f"{TAG}.design.json")
    json.dump(d, open(path, "w"))
    return path, d


def grid_estimate(d, res=None):
    import field_solve as FS
    import round_trip as RTR
    prims = FS.dedupe(FS.primitives(d["parts"]))
    g, _ = FS.build_grid(prims, enclosure=None, res=res or RTR.RES["c"], theta_breaks=[0.0, 7.5, 15.0, 22.5])
    return list(g.shape), int(np.prod(g.shape))


def _main():
    cmd = sys.argv[1] if len(sys.argv) > 1 else "design"
    if cmd == "design":
        path, d = write_design()
        print(path, len(d["parts"]), "parts;", len(d["motor"]["core_boxes"]), "core boxes")
        for b in d["motor"]["core_boxes"]:
            print("  ", b)
        print("grid (coarse):", grid_estimate(d))


# ---------------------------------------------------------------------------------------------------------
# the two local field models (the full machine + motor does not fit: ~14-16 M cells against ~11 M)
# ---------------------------------------------------------------------------------------------------------
def _within(p, rlo, rhi=1e9, zlim=1e9):
    import motor_geometry as MG
    r0, r1, z0, z1 = MG.revolved(p)
    return r1 >= rlo and r0 <= rhi and z1 >= -zlim and z0 <= zlim


def gap_model(d=None):
    """everything around the rail gaps (r 380..563, |z| <= 90), no motor; SG1 / SG2 spheres + stems on their
    own nets mA / mB. Merging mA -> 2, mB -> 3 in the result gives the same region before v4 (exact)."""
    d = d or design()
    parts = [p for p in d["parts"] if p.get("role") != "motor" and _within(p, 380.0, 563.0, 90.0)]
    return dict(d, parts=parts)


def motor_model(d=None):
    """the motor and everything beyond r 450; the motor conductors on their own nets (cA, cB, U)."""
    d = d or design()
    parts = []
    for p in d["parts"]:
        if p.get("role") == "motor":
            q = dict(p)
            if q["node"] in ("2", "3"):
                q["node"] = "cA" if q["node"] == "2" else "cB"
            parts.append(q)
        elif _within(p, 450.0):
            parts.append(p)
    return dict(d, parts=parts)


def write_models():
    d = design()
    out = {}
    for tag, m in ((f"{TAG}-gap", gap_model(d)), (f"{TAG}-mot", motor_model(d))):
        path = os.path.join(RT_DIR, f"{tag}.design.json")
        json.dump(m, open(path, "w"))
        out[tag] = path
    return out


# ---------------------------------------------------------------------------------------------------------
# the capacitance model: the r5N2f 12-angle sweep + the two deltas, resampled onto its angles
# ---------------------------------------------------------------------------------------------------------
def _resample(th_src, v, th_dst, period=60.0):
    """uniform samples from 0 over the period -> values at th_dst (Fourier interpolation)."""
    n = len(th_src)
    c = np.fft.rfft(np.asarray(v, float)) / n
    k = np.arange(c.size)
    w = np.where((k == 0) | ((n % 2 == 0) & (k == n // 2)), 1.0, 2.0)
    out = []
    for t in th_dst:
        x = 2 * math.pi * (t % period) / period
        out.append(float(np.sum(w * (c.real * np.cos(k * x) - c.imag * np.sin(k * x)))))
    return np.array(out)


def _key(a, b):
    import round_trip as RTR
    return RTR._key(a, b)


def assemble(steps=("split", "motor", "utron")):
    """{key: pF over the base angles} for the requested steps:
      split -- the v4 coil-gap nodes mA / mB from the gap model (exact merge gives its before-state);
      motor -- the C-EM cores' couplings (cA -> '2', cB -> '3'), new conductors only [IR: the shielding they
               add to existing pairs is neglected, conservative];
      utron -- the floating utron net U and its couplings."""
    import round_trip as RTR
    th, sols = RTR.load(os.path.join(RT_DIR, "r5N2f.c12.sweep.json"))
    prof, _ = RTR.reduce(sols)
    prof = {k: np.array(v, float) for k, v in prof.items()}
    info = {}
    if "split" in steps:
        tg, sg = RTR.load(os.path.join(RT_DIR, f"{TAG}-gap.c{GAP_N}.sweep.json"))
        split, _ = RTR.reduce(sg)
        merged, _ = RTR.reduce(sg, merge=dict(RTR.MERGE, mA="2", mB="3"))
        for k in set(split) | set(merged):
            dv = _resample(tg, split.get(k, np.zeros(len(tg))) - merged.get(k, np.zeros(len(tg))), th)
            prof[k] = prof.get(k, np.zeros(len(th))) + dv
        info["mA_total_pF"] = float(np.mean(sum(v for k, v in split.items() if "mA" in k and "2" not in k)))
        info["mA_to_2_pF"] = float(np.mean(split.get(_key("2", "mA"), [0.0])))
        info["mA_couplings_pF"] = {f"{k[0]}|{k[1]}": float(np.mean(v)) for k, v in split.items() if "mA" in k}
    if "motor" in steps or "utron" in steps:
        tm, sm = RTR.load(os.path.join(RT_DIR, f"{TAG}-mot.c{MOT_N}.sweep.json"))
        mot, _ = RTR.reduce(sm)
        rename = {"cA": "2", "cB": "3"}
        added = {}
        for (a, b), v in mot.items():
            if not ({a, b} & {"cA", "cB", "U"}):
                continue                                   # existing pairs: left at the full-machine values
            if "U" in (a, b) and "utron" not in steps:
                continue
            if "U" not in (a, b) and "motor" not in steps:
                continue
            a2, b2 = rename.get(a, a), rename.get(b, b)
            if a2 == b2:
                continue                                   # internal to one net (core to its own rail)
            k = _key(a2, b2)
            dv = _resample(tm, v, th)
            prof[k] = prof.get(k, np.zeros(len(th))) + dv
            added[f"{a}|{b}"] = [float(np.min(v)), float(np.max(v))]
        info["motor_couplings_pF_minmax"] = added
    return th, prof, info


GAP_N, MOT_N = 12, 12
L1_H, R1_OHM = 0.64, 40.0                                 # one C-EM (engine default; geometry-derived pending) [RH]
SCREEN_PF_PER_COIL = 57.0                                 # screened lead, ~100 pF/m x 0.567 m (G-MOT-LEAD) [RH]
L_TANK, C_TANK_Q = 425e-6, 30.0                           # the RA tank chain


def z_case(th, prof, coils=True, tank=True, screen=True, mid_floor_pF=0.5, g_v=3.0, tip=15.0):
    import pump_synth as SY
    import rt_engine as RT
    import round_trip as RTR
    cfg = SY.engine_cfg(*SY.sized(dict(g_vMm=g_v)))
    cm = RTR.CModel(th, prof, tip_deg=tip)
    net = RT.build_net(cfg, cmodel=cm)
    GND = RT.GND
    if tank:                                             # v4 parallel tank: the coil chain across R-A / R-B
        R_t = (1 / math.sqrt(L_TANK * 789e-12)) * L_TANK / C_TANK_Q
        net.inds.append(("L_tank_chain", net.n("R-A"), net.n("R-B"), L_TANK, R_t, "lx"))
    if coils:                                            # v4: 2 -> L_A (x6, lumped) -> mA -> SG1 -> R-A; B mirrored
        for gname, node, mid in (("SG1", "2", "mA"), ("SG2", "3", "mB")):
            k = [i for i, g in enumerate(net.gaps) if g[0] == gname][0]
            g = list(net.gaps[k]); ni, nm = net.n(node), net.n(mid)
            j = 1 if g[1] == ni else 2
            assert g[j] == ni, (gname, g[:3])
            g[j] = nm; net.gaps[k] = tuple(g)
            net.inds.append((f"L_{mid}", ni, nm, L1_H / 6, R1_OHM / 6, "lx"))
            if mid_floor_pF:
                net.caps.append((f"Cfloor_{mid}", nm, GND, mid_floor_pF * 1e-12))
            if screen:
                net.caps.append((f"Cscreen_{mid}", nm, ni, 6 * SCREEN_PF_PER_COIL * 1e-12))
    m = RT.run(net, cfg)
    return m["z"], bool(m["converged"])


def ledger():
    import round_trip as RTR
    th, base = RTR.load(os.path.join(RT_DIR, "r5N2f.c12.sweep.json"))
    p0, _ = RTR.reduce(base)
    rows = []

    def run(label, prof, **kw):
        z, c = z_case(th, prof, **kw)
        rows.append(dict(case=label, z=z, converged=c)); print(f"{label:70s} z {z:.4f} {'conv' if c else 'NOT conv'}", flush=True)
    run("0  r5N2f as solved (series-tank basis, old netlist; record 1.2400)", p0, coils=False, tank=False)
    run("1  + v4 parallel tank (coil chain across R-A / R-B)", p0, coils=False, tank=True)
    run("2  + v4 series C-EMs (L 0.107 H lumped), mid node 0.5 pF only", p0, coils=True, tank=True, screen=False)
    _, ps, info = assemble(("split",))
    run("3  + field: SG1 / SG2 spheres + stems are the mid node", ps, coils=True, tank=True, screen=False)
    run("4  + screened lead: 6 x 57 pF across each coil group", ps, coils=True, tank=True, screen=True)
    _, pm, info_m = assemble(("split", "motor"))
    run("5  + C-EM cores (bonded to 2 / 3) in the field", pm, coils=True, tank=True, screen=True)
    _, pu, info_u = assemble(("split", "motor", "utron"))
    run("6  + floating utrons (carrier between the A and B cores)", pu, coils=True, tank=True, screen=True)
    info.update(info_u)
    out = dict(rows=rows, info=info, screen_pF_per_coil=SCREEN_PF_PER_COIL, L1_H=L1_H, R1_ohm=R1_OHM)
    json.dump(out, open(os.path.join(HERE, "motor_field_results.json"), "w"), indent=1)
    return out


def _time_one(tag, theta=0.0):
    import time
    import round_trip as RTR
    d = json.load(open(os.path.join(RT_DIR, f"{tag}.design.json")))
    t0 = time.time()
    s = RTR.solve_theta(d, theta, "c", enclosure=None)
    print(tag, s["info"]["cells"], "cells", round(time.time() - t0), "s", s["names"], flush=True)
    return s


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "models":
        print(write_models())
    elif len(sys.argv) > 1 and sys.argv[1] == "ledger":
        ledger()
    elif len(sys.argv) > 2 and sys.argv[1] == "sweep":
        import round_trip as RTR
        tag, n = sys.argv[2], int(sys.argv[3]) if len(sys.argv) > 3 else 12
        procs = int(sys.argv[4]) if len(sys.argv) > 4 else 1
        th = [60.0 * k / n for k in range(n)]
        sols = RTR.sweep(os.path.join(RT_DIR, f"{tag}.design.json"), th, level="c", enclosure=None, procs=procs, log=print)
        RTR.save(os.path.join(RT_DIR, f"{tag}.c{n}.sweep.json"), th, sols)
    elif len(sys.argv) > 2 and sys.argv[1] == "time":
        _time_one(sys.argv[2])
    else:
        _main()
