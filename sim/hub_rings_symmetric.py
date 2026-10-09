"""sim/hub_rings_symmetric.py -- the rings on a symmetric supply, against the record's asymmetric one.

The designer's question (2026-10-09): what if both rings are driven by a symmetric circuit?
  identical circuits   the same peak detector on each pumping node: nodes 1 and 4 carry the same waveform half a cycle
                       apart, so both rings charge to the same negative peak; nothing across them, and by the hub's
                       mirror symmetry no field at the null [OC] (the record's supply run gives both nodes' peaks);
  mirror circuits      ring A on its own negative Cockcroft-Walton chain from the shaft on node 1's swing, ring B on the
                       positive one on node 4's (sim/core_field.py n_cw_a with a_ref "shaft"): n stages each, the rings
                       at about -/+ 7.5 kV per stage. Sized like the record (sim/hub_rings_build.py phase 5): the gap
                       along the glass at the interface rating, both beads at the gel's rating, the best at each pair
                       of ratings solved again directly.
Against: the record and the best asymmetric design at each pair (sim/hub_rings_build_results.json).
Usage: python3 sim/hub_rings_symmetric.py [--procs 4]   (writes sim/hub_rings_symmetric_results.json)
"""
import argparse
import json
import os
import sys
import time
from multiprocessing import Pool

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import hub_rings_build as B        # noqa: E402

SYM = (1, 2, 3)                    # stages on each ring


def parts(d):
    """the supply's HV diodes and 100 pF capacitors: Dk + C_A unless ring A's chain starts at the shaft; two of each per
    stage."""
    dk = 0 if d.get("a_ref") == "shaft" else 1
    return dict(diodes=dk + 2 * (d["n_a"] + d["n_cw"]), capacitors=dk + 2 * (d["n_a"] + d["n_cw"]))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--procs", type=int, default=4)
    a = ap.parse_args()
    t0 = time.time()
    rec_lock = json.load(open(os.path.join(HERE, "hub_locked_results.json")))["record"]
    build = json.load(open(os.path.join(HERE, "hub_rings_build_results.json")))
    sup = build["record_supply"]
    same = dict(node1_peak_kV=sup["V"]["1"]["min"], node4_peak_kV=sup["V"]["4"]["min"],
                across_kV=sup["V"]["4"]["min"] - sup["V"]["1"]["min"])
    print(f"identical peak detectors: ring A {same['node1_peak_kV']:.2f}, ring B {same['node4_peak_kV']:.2f} kV, "
          f"{same['across_kV']:.2f} kV across: no field at the null", flush=True)
    with Pool(a.procs) as pool:
        stages = list(pool.imap(B._stage_run, [(n, B.R_LEAK_EST, n, "shaft") for n in SYM]))
    for q in stages:
        print(f"mirror chains, {q['n_cw']} + {q['n_cw']} stages: A {q['V_A_kV']:.2f}, B {q['V_B_kV']:.2f} kV, "
              f"z {q['z_start']:.3f}, diodes <= {max(q['VR_pk_kV'].values()):.1f} kV", flush=True)
    designs, best, tables, t5 = B.phase5(stages, a.procs, rec_lock)
    rows = []
    for key in build["best_edges"]:
        asym, sym = build["best_edges"][key], best.get(key)
        rows.append(dict(ratings=key, asym=dict(asym, **parts(asym)), sym=dict(sym, **parts(sym)) if sym else None))
        s_ = (f"mirror {sym['n_cw']} + {sym['n_cw']}: {sym['V_A_kV']:.1f} / +{sym['V_B_kV']:.1f} kV, bands "
              f"{sym['theta_p']:.2f}-{sym['theta_e']:.2f}, beads {sym['rho_pol_mm']:.1f} / {sym['rho_eq_mm']:.1f} mm: "
              f"{sym['E_null_kV_cm']:.2f} kV/cm (verified {sym['verified']})" if sym else "mirror: none holds")
        print(f"{key} kV/mm: asymmetric A{asym['n_a']} B{asym['n_cw']} {asym['E_null_kV_cm']:.2f} kV/cm | {s_}", flush=True)
    out = dict(note="see the module docstring", identical=same, stages=stages, designs=designs, best_edges=best,
               compare=rows, record=build["record"], run_s=time.time() - t0)
    json.dump(out, open(os.path.join(HERE, "hub_rings_symmetric_results.json"), "w"), indent=1, default=float)
    print(f"done in {time.time() - t0:.0f} s")


if __name__ == "__main__":
    main()
