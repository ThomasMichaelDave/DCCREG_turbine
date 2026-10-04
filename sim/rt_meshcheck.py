#!/usr/bin/env python3
"""sim/rt_meshcheck.py -- mesh convergence at a final design, one direction at a time (design loop) [ME].

A full c -> m refinement of an interleaved build exceeds the session's memory, so each direction is refined on
its own at two relative angles (aligned 0, disaligned 30 deg geometric):
  c_r : radial cells (h_min_r 1.0 -> 0.6 mm, h_max_r 6 -> 5; plate edges, rims)
  c_z : axial cells (h_min_z 1.0 -> 0.6 mm, h_max_z 5 -> 4; foils, gaps, facings)
  c_p : angular cells (h_max_p 2.5 -> 2.0 deg, h_min_arc 1.5 -> 1.0 mm; sector edges)
Every reduced coupling is compared with the coarse solve at the same angle. The per-coupling ratio (fine / coarse,
mean of the two angles) is applied to the coarse 12-angle (or 6-angle) profiles and z is recomputed, per
direction and all together (product of the ratios) -- the estimated z on a finer mesh.
Usage: python3 sim/rt_meshcheck.py <tag> <g_vMm> [n_theta]   -> sim/round_trip_runs.json ['mesh'][tag]
"""
import json
import os
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path[:0] = [HERE, os.path.join(ROOT, "reference")]
import numpy as np                       # noqa: E402
import field_solve as FS                 # noqa: E402
import round_trip as RTP                 # noqa: E402

LEVELS = {
    "c_r": dict(RTP.RES["c"], h_min_r=0.6, h_max_r=5.0),
    "c_z": dict(RTP.RES["c"], h_min_z=0.6, h_max_z=4.0),
    "c_p": dict(RTP.RES["c"], h_max_p=2.0, h_min_arc=1.0),
}
MEM = 13.5e9                             # bytes for one process (the session limit is ~15 GB) [ME]
BYTES_PER_CELL = 950.0                   # measured: 7.3 GB at 8.4 M cells mid-solve (interleaved N = 2) [ME]


def run(tag, g_v, n_theta=12, thetas=(0.0, 30.0), log=print):
    RTP.RES.update(LEVELS)
    rt = os.path.join(ROOT, "docs", "geometry", "rt")
    design = json.load(open(os.path.join(rt, f"{tag}.design.json")))
    th_all, sols = RTP.load(os.path.join(rt, f"{tag}.c{n_theta}.sweep.json"))
    coarse = {t: sols[[round(x, 9) for x in th_all].index(round(t, 9))] for t in thetas}
    cache = os.path.join(rt, f"{tag}.mesh.json")
    rec = json.load(open(cache)) if os.path.exists(cache) else {}
    prims = FS.dedupe(FS.primitives(design["parts"]))
    for L in LEVELS:
        g, _ = FS.build_grid(prims, enclosure=None, res=RTP.RES[L], theta_breaks=[0.0, 7.5, 15.0, 22.5])
        est = BYTES_PER_CELL * 1.15 * float(np.prod(g.shape))
        if est > MEM:
            log(f"{L}: ~{np.prod(g.shape) / 1e6:.1f} M cells, ~{est / 1e9:.1f} GB > budget, skipped")
            rec[L + "_skipped"] = float(np.prod(g.shape))
            continue
        for t in thetas:
            k = f"{L}@{t:g}"
            if k in rec:
                continue
            t0 = time.time()
            rec[k] = RTP.solve_theta(design, t, L, enclosure=None)
            log(f"{k}: {rec[k]['info']['cells']} cells, {time.time() - t0:.0f} s")
            json.dump(rec, open(cache, "w"))
    out = dict(tag=tag, thetas=list(thetas), levels={})
    prof_c, _ = RTP.reduce(sols)
    ratios_all = {}
    for L in LEVELS:
        if not all(f"{L}@{t:g}" in rec for t in thetas):
            continue
        ratio, rows, worst = {}, [], {">=100pF": 0.0, ">=10pF": 0.0, ">=1pF": 0.0}
        for t in thetas:
            pc, _ = RTP.reduce([coarse[t]])
            pf, _ = RTP.reduce([rec[f"{L}@{t:g}"]])
            for key in pf:
                vc, vf = float(pc[key][0]), float(pf[key][0])
                if abs(vc) < 1e-9:
                    continue
                r = vf / vc
                ratio.setdefault(key, []).append(r)
                for lim, name in ((100, ">=100pF"), (10, ">=10pF"), (1, ">=1pF")):
                    if abs(vf) >= lim:
                        worst[name] = max(worst[name], abs(r - 1))
        ratio = {k: float(np.mean(v)) for k, v in ratio.items()}
        ratios_all[L] = ratio
        ladder = {nm: ratio.get(RTP._key(*ab), float("nan")) - 1 for nm, ab in RTP.VARICAP_KEYS.items()}
        p = {k: v * ratio.get(k, 1.0) for k, v in prof_c.items()}
        z, c = RTP.z_cmodel(th_all, p, dict(g_vMm=g_v), RTP.RT_GEOM["sg_tip_deg"])
        out["levels"][L] = dict(worst_change=worst, ladder_change=ladder, z_corrected=z, converged=c)
        log(f"{L}: worst change {json.dumps({k: round(v, 4) for k, v in worst.items()})}; z corrected {z:.4f} {'conv' if c else ''}")
    z0, c0 = RTP.z_cmodel(th_all, prof_c, dict(g_vMm=g_v), RTP.RT_GEOM["sg_tip_deg"])
    out["z_coarse"] = z0
    if len(ratios_all) >= 2:
        p = {}
        for k, v in prof_c.items():
            f = 1.0
            for L in ratios_all:
                f *= ratios_all[L].get(k, 1.0)
            p[k] = v * f
        z, c = RTP.z_cmodel(th_all, p, dict(g_vMm=g_v), RTP.RT_GEOM["sg_tip_deg"])
        out["z_corrected_both"] = z
        out["converged_both"] = c
        log(f"both directions: z corrected {z:.4f} {'conv' if c else ''} (coarse {z0:.4f})")
    RTP._record("mesh", {**(json.load(open(RTP.RUNS)).get("mesh", {}) if os.path.exists(RTP.RUNS) else {}), tag: out})
    return out


if __name__ == "__main__":
    tag, g_v = sys.argv[1], float(sys.argv[2])
    n = int(sys.argv[3]) if len(sys.argv) > 3 else 12
    run(tag, g_v, n)
