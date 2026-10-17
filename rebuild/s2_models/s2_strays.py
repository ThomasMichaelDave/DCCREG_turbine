"""rebuild/s2_models/s2_strays.py -- S2b: the field solve on the S2a model (rebuild/s2_models/s2b-plan.md).

The record's finite-volume solver, imported from sim/tube_strays.py (not edited): node-based finite volumes on a
cylindrical tensor grid, Shortley-Weller boundaries, CG with smoothed-aggregation AMG (pyamg), the Maxwell matrix from
the conductors' charges [OC: the method]. The S2a model's parts come from rebuild/s2_models/s2_fv.py (S2b-1).

Steps (each its own flag; every solve kept in s2_strays_results.json by its key, --resume reuses them):
  --cell   S2b-2: one gap of the infinite periodic stack, a 30 deg mirror wedge, at the spacings 1.0 / 0.5 / 0.25 mm,
           without rims (the vanes' sectors only, Neumann at r 50 / 150) and with them (the record's radial build):
           - G-CELL: the record's 3 mm cell (sim/tube_strays_results.json "cell") reproduced within 0.2 %;
           - the gaps of S2a's stack: 3 | 3, and the end vanes' 4 | 3 (the first rotor vane) and 3 | 4.5 (the last
             stator vane) [IR: a periodic cell of those two thicknesses].
  (the stack W, the hub H, the axisymmetric A, the whole F, the profile and the fields follow, s2b-plan.md §4)
Writes rebuild/s2_models/s2_strays_results.json.
Tags: [OC] derivable; [IR] a modelling choice; [RH] a heuristic (CONVENTIONS.md §1). g is a gap, never d.
Usage: python3 rebuild/s2_models/s2_strays.py --cell [--procs 6] [--resume]
"""
import os
os.environ.setdefault("OPENBLAS_NUM_THREADS", "1")
os.environ.setdefault("OMP_NUM_THREADS", "1")
import argparse        # noqa: E402
import json            # noqa: E402
import math            # noqa: E402
import sys             # noqa: E402
import time            # noqa: E402
from multiprocessing import Pool    # noqa: E402

import numpy as np     # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, os.path.join(ROOT, "sim"))
sys.path.insert(0, HERE)
import tube_strays as TS   # noqa: E402
import stack_sizing as SS  # noqa: E402

RESULTS = os.path.join(HERE, "s2_strays_results.json")
CELL_H = TS.CELL_H                     # 1.0, 0.5, 0.25 mm: the record's cell spacings
CELL_CASES = [(3.0, 3.0), (4.0, 3.0), (3.0, 4.5)]     # (rotor vane, stator vane) mm: S2a's gaps (s2_geometry.py)


# ============================================================================================== S2b-2: the cell
def build_cell(h=0.5, unaligned=False, rims=True, t_rot=3.0, t_sta=3.0, log=print):
    """sim/tube_strays.build_cell with the two vanes' thicknesses their own: mirrors at the stator vane's and the next
    rotor vane's mid-planes (z 0 and t_sta / 2 + g + t_rot / 2), the 30 deg mirror wedge; each vane's exposed edges a
    full round of half its own thickness [IR, the record's]. rims: the record's radial build (shaft, G10 sleeve, the
    rotor ring on the sleeve, the stator ring, the G10 cage, the REF wall at r 400); else Neumann at r 50 / 150."""
    I = TS.inputs()
    rec = I["rec"]
    g, half = rec["gap_mm"], 0.5 * rec["wr_deg"]
    zs, zr = 0.0, 0.5 * t_sta + g + 0.5 * t_rot
    z = TS.axis(zs, zr, [0.5 * t_sta, zr - 0.5 * t_rot], [(zs, zr, h)])
    ctr = 30.0 if unaligned else 0.0
    edges = [half] + ([ctr - half] if unaligned else [])
    th = TS.axis(0, 30.0, [0, 30] + edges, [(e - 2.5, e + 2.5, 0.4 * h) for e in edges] + [(0, 30, 1.2 * h)],
                 h_far=1.2 * h, grow=1.2)
    ri, ro = SS.TUBE_DEFAULTS["r_inMm"], SS.TUBE_DEFAULTS["r_outMm"]
    if rims:
        rf = [3.0, SS.SHAFT_R, SS.SLEEVE_R, ro + 12, ro + 16, TS.R_BOX] + [x + s * 0.5 * t for x in (ri, ro)
                                                                          for t in (t_rot, t_sta) for s in (-1, 0, 1)]
        r = TS.axis(3.0, TS.R_BOX, rf, [(ri - 5, ri + 5, h), (ro - 5, ro + 5, h), (12.5, 45, 2 * h), (155, 170, 2 * h),
                                        (55, 145, 4 * h), (3, 12.5, 3.0)], h_far=30.0, grow=1.18)
    else:
        r = TS.axis(ri, ro, [], [(ri, ro, 5.0)])
    P = TS.Problem(r, np.radians(th), z, eps_bg=I["eps_air"])
    T0, T1 = -1.0, 2.0
    if rims:
        st = TS.Vane("stator", zs - 0.5 * t_sta, zs + 0.5 * t_sta, ctr, half, ri, ro, ro, ro + 12.0)
        rt = TS.Vane("rotor", zr - 0.5 * t_rot, zr + 0.5 * t_rot, 0.0, half, ri, ro, SS.SLEEVE_R, ro + 12.0)
        g10 = I["hub"]["shaft_coupler"]["value"]["eps_r"]
        P.add_dielectric(g10, TS.ann_c(SS.SHAFT_R, SS.SLEEVE_R, -1, zr + 1), (SS.SHAFT_R, SS.SLEEVE_R, T0, T1, -1, zr + 1))
        P.add_dielectric(g10, TS.ann_c(ro + 12, ro + 16, -1, zr + 1), (ro + 12, ro + 16, T0, T1, -1, zr + 1))
        P.add_conductor(TS.SID["SHAFT"], "SHAFT", lambda R, T, Z: R <= SS.SHAFT_R + TS.TOL, (0, SS.SHAFT_R, T0, T1, -1, zr + 1))
        P.cid[-1, :, :] = TS.SID["W"]; P.names[TS.SID["W"]] = "W"
    else:
        st = TS.Vane("stator", zs - 0.5 * t_sta, zs + 0.5 * t_sta, ctr, half, 0.0, 1000.0)
        rt = TS.Vane("rotor", zr - 0.5 * t_rot, zr + 0.5 * t_rot, 0.0, half, 0.0, 1000.0, 0.0)
    P.add_conductor(TS.SID["N1v"], "N1v", rt.inside, (0, 1e4, T0, T1, zr - t_rot, zr + t_rot))
    P.add_conductor(TS.SID["SA"], "SA", st.inside, (0, 1e4, T0, T1, zs - t_sta, zs + t_sta))
    return P


def _cell_job(job):
    t0 = time.time()
    kw = job["kw"]
    P = build_cell(log=lambda s: None, **kw)
    P.assemble(log=lambda s: None)
    C, its = P.maxwell([TS.SID["N1v"]], log=lambda s: None)
    n1, sa = TS.SID["N1v"], TS.SID["SA"]
    out = dict(key=job["key"], kw=kw, per_gap_pF=-12.0 * C[sa, n1], nodes=int(P.cid.size), run_s=time.time() - t0)
    if kw["rims"]:
        out["rotor_vane_shaft_pF"] = -12.0 * C[TS.SID["SHAFT"], n1]
        out["rotor_vane_wall_pF"] = -12.0 * C[TS.SID["W"], n1]
    print(f"[{job['key']}] {out['per_gap_pF']:.4f} pF per gap ({out['run_s']:.0f} s)", flush=True)
    return out


def cell_jobs():
    out = []
    for (tr, ts) in CELL_CASES:
        for rims in (False, True):
            for h in CELL_H:
                for un in (False, True):
                    kw = dict(h=h, unaligned=un, rims=rims, t_rot=tr, t_sta=ts)
                    out.append(dict(key="cell:" + ",".join(f"{k}={v}" for k, v in sorted(kw.items())), kw=kw))
    return out


def cell_analyse(rows):
    """per case and spacing: the aligned / unaligned per-gap C, kappa per gap; Richardson over the three spacings;
    G-CELL at 3 | 3 against the record's cell."""
    rec = json.load(open(os.path.join(ROOT, "sim", "tube_strays_results.json")))["cell"]
    by = {r["key"]: r for r in rows}
    out, gate = {}, []
    for (tr, ts) in CELL_CASES:
        case = {}
        for rims in (False, True):
            lv = []
            for h in CELL_H:
                g = lambda un: by["cell:" + ",".join(f"{k}={v}" for k, v in sorted(dict(h=h, unaligned=un, rims=rims,  # noqa
                                                                                          t_rot=tr, t_sta=ts).items()))]
                a, u = g(False), g(True)
                lv.append(dict(h_mm=h, aligned=a["per_gap_pF"], unaligned=u["per_gap_pF"],
                               kappa_gap=a["per_gap_pF"] / u["per_gap_pF"]))
            ex = {k: TS.richardson([q[k] for q in lv], list(CELL_H))[0] for k in ("aligned", "unaligned")}
            case["with_rims" if rims else "no_rims"] = dict(levels=lv, extrapolated=ex,
                                                             kappa_gap=ex["aligned"] / ex["unaligned"])
            if (tr, ts) == (3.0, 3.0):
                ref = rec["with_rims" if rims else "no_rims"]
                for q, rq in zip(lv, ref):
                    for k in ("aligned", "unaligned"):
                        dev = q[k] / rq[k] - 1
                        gate.append(dict(rims=rims, h_mm=q["h_mm"], which=k, here=q[k], record=rq[k], dev=dev))
        out[f"{tr:g}|{ts:g}"] = case
    worst = max(abs(x["dev"]) for x in gate)
    return out, dict(rows=gate, worst_dev=worst, tol=0.002, pass_=worst <= 0.002)


# ============================================================================================== the orchestration
def load():
    return json.load(open(RESULTS)) if os.path.exists(RESULTS) else dict(solves={})


def save(res):
    json.dump(res, open(RESULTS, "w"), indent=1, default=float)


def run(jobs, fn, procs, res, resume):
    todo = [j for j in jobs if not (resume and j["key"] in res["solves"])]
    print(f"{len(jobs)} solves, {len(todo)} to run on {procs} processes", flush=True)
    if todo:
        with Pool(procs) as pool:
            for r in pool.imap_unordered(fn, todo):
                res["solves"][r["key"]] = r
                save(res)
    return [res["solves"][j["key"]] for j in jobs]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--cell", action="store_true")
    ap.add_argument("--procs", type=int, default=6)
    ap.add_argument("--resume", action="store_true")
    a = ap.parse_args()
    res = load()
    res["note"] = "S2b: the field solve on the S2a model (rebuild/s2_models/s2b-plan.md)"
    if a.cell:
        rows = run(cell_jobs(), _cell_job, a.procs, res, a.resume)
        res["cell"], res["G_CELL"] = cell_analyse(rows)
        save(res)
        g = res["G_CELL"]
        print(f"G-CELL: worst {g['worst_dev']:+.3%} against the record's cell ({'pass' if g['pass_'] else 'FAIL'})")
        for k, c in res["cell"].items():
            print(f"  {k}: no rims kappa {c['no_rims']['kappa_gap']:.3f}, with rims {c['with_rims']['kappa_gap']:.3f} "
                  f"(per gap {c['with_rims']['extrapolated']['aligned']:.3f} / {c['with_rims']['extrapolated']['unaligned']:.3f} pF)")


if __name__ == "__main__":
    main()
