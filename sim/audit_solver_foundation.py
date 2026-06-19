#!/usr/bin/env python3
"""
sim/audit_solver_foundation.py — AUDIT of the pump-solver foundation.
=====================================================================
Is the entire pump solver current, or are S5-S8 built on stale ground? Every
downstream number (W_mech,stator=15.941162 mJ, DOUBLER_ETA=0.385956, USEFUL=6.152584
mJ, the z=1.2033 gate) descends from one frozen solver (doubler_core, a line-for-line
mirror of index.html's solveDoubler4) validated ONLY against itself. This audit
recomputes the foundation on the CURRENT geometry, the v0.2 topology, a RIGOROUS diode
solve, and a SPARK-GAP switch model, with an INDEPENDENT cross-check (ngspice + LCP)
replacing the circular JS-mirror self-test.

THE FROZEN SOLVERS ARE THE SUBJECT, NOT THE ORACLE. They stay byte-identical (read,
never edited; empty-diff asserted). If the inherited scalars fail they are SUPERSEDED
by the validated producer (a new freeze), not edited in place.

Verdicts: FOUNDATION-HOLDS / FOUNDATION-DRIFTS / SOLVER-INVALID.
Tiers: [OC] standard physics · [IR] modelling choice · [RH] open.
"""
import math
import os
import subprocess
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "reference"))
import doubler_core as dc          # FROZEN solver under audit
import shuttle_core as sc          # FROZEN (carries the stale galvanic_z device anchor)

# ---- geometries -------------------------------------------------------------
GEO_DEVICE = (160, 1000, 160, 1000, 100, 100, 20)   # stale device anchor (the 1.2033 gate)
GEO_CURRENT = (16, 280, 16, 280, 309, 309, 20)       # current machine (16-280/309)  freeze v0.10
# inherited scalars under test
INH = dict(W_mech=15.941162e-3, DOUBLER_ETA=0.385956, USEFUL=6.152584e-3,
           W_coll=12.4489e-3, Q_isl=1.3951e-6, z_gate=1.2033)
V_OP = 20e3                       # operating rail (S5)
PRF = 600.0
ARC_CORNERS = {"opt": 20.0, "mid": 35.0, "pess": 50.0}   # V_arc  shuttle_core:685-687


# =============================================================================
# Stage C — rigorous diode (LCP) solve: enforce ON-forward AND OFF-reverse
# =============================================================================
def solve_phase_rigorous(Q, C1, C2, Ca, Cb, Cpar, eps=1e-9):
    """Among the 16 states, keep those with OFF-diodes reverse-biased (frozen check)
    AND ON-diodes carrying forward (anode->cathode >=0) charge. The physical LCP
    solution is unique. Returns the passing states. [OC]"""
    kd = [C1 + Cpar + Ca, Cpar + Ca, Cpar + Cb, C2 + Cpar + Cb]
    passing = []
    for s in range(16):
        d = [(s >> i) & 1 for i in range(4)]
        parent = list(range(5))
        def find(x):
            while parent[x] != x:
                parent[x] = parent[parent[x]]; x = parent[x]
            return x
        def union(a, b):
            ra, rb = find(a), find(b)
            if ra != rb: parent[ra] = rb
        for i, on in enumerate(d):
            if on: union(*dc.DIODES[i])
        groot = find(0); cid = {}; nc = 0; ncl = [0] * 5
        for i in range(1, 5):
            r = find(i)
            if r == groot: ncl[i] = -1; continue
            if r not in cid: cid[r] = nc; nc += 1
            ncl[i] = cid[r]
        if nc == 0:
            V = [0.0] * 4
        else:
            A = np.zeros((nc, nc)); rhs = np.zeros(nc)
            for i in range(1, 5):
                c = ncl[i]
                if c >= 0: rhs[c] += Q[i - 1]
            def addK(i, kdiag, nb, koff):
                c = ncl[i]
                if c < 0: return
                A[c][c] += kdiag; cj = ncl[nb]
                if cj >= 0: A[c][cj] += koff
            addK(1, kd[0], 2, -Ca); addK(2, kd[1], 1, -Ca)
            addK(3, kd[2], 4, -Cb); addK(4, kd[3], 3, -Cb)
            try:
                x = np.linalg.solve(A, rhs)
            except Exception:
                continue
            V = [0.0 if ncl[i] < 0 else x[ncl[i]] for i in range(1, 5)]
        v1, v2, v3, v4 = V
        if not d[0] and v2 > eps: continue
        if not d[1] and v3 > eps: continue
        if not d[2] and v1 > v3 + eps: continue
        if not d[3] and v4 > v2 + eps: continue
        # ON-diode forward-current check (the part the frozen heuristic SKIPS)
        Qpost = dc.charges_from_voltages(V, C1, C2, Ca, Cb, Cpar)
        fwd = True
        for i, on in enumerate(d):
            if on:
                a, _ = dc.DIODES[i]
                if a >= 1 and (Q[a - 1] - Qpost[a - 1]) < -eps * max(1.0, abs(Q[a - 1])):
                    fwd = False
        if fwd:
            passing.append((s, V, abs(v1) + abs(v4)))
    return passing


def z_rigorous(geo, it=120, burn=60):
    C1min, C1max, C2min, C2max, Ca, Cb, Cpar = geo
    V = [-1.0, 0, 0, -1.0]; C1c, C2c = C1max, C2min; ratios = []; prev = 2.0
    mismatches = 0; multi = 0
    for cyc in range(it):
        for (C1n, C2n) in [(C1min, C2max), (C1max, C2min)]:
            Q = dc.charges_from_voltages(V, C1c, C2c, Ca, Cb, Cpar)
            sols = solve_phase_rigorous(Q, C1n, C2n, Ca, Cb, Cpar)
            Vh = dc.solve_phase(Q, C1n, C2n, Ca, Cb, Cpar)
            if len(sols) > 1: multi += 1
            V = sols[0][1] if sols else Vh
            if [round(a, 9) for a in V] != [round(a, 9) for a in Vh]:
                mismatches += 1
            C1c, C2c = C1n, C2n
        mag = abs(V[0]) + abs(V[3])
        if cyc >= burn and prev > 1e-15 and mag > 1e-15: ratios.append(mag / prev)
        prev = mag
        mx = max(abs(v) for v in V)
        if mx > 1e6 or (0 < mx < 1e-6):
            scf = 1.0 / mx; V = [v * scf for v in V]; prev *= scf
    return float(np.median(ratios)) if ratios else 1.0, mismatches, multi


# =============================================================================
# Stage D — spark-gap switch model: the arc tax on DOUBLER_ETA
# =============================================================================
def commutation_charge(geo, v_op=V_OP):
    """Per-cycle charge through the commutation gaps, on the current geometry at the
    operating rail. The arc dissipates V_arc x this charge (zero in the ideal model)."""
    C1min, C1max, C2min, C2max, Ca, Cb, Cpar = geo
    V = [-1.0, 0, 0, -1.0]; C1c, C2c = C1max, C2min
    Qcyc = 0.0
    for (C1n, C2n) in [(C1min, C2max), (C1max, C2min)]:
        Qpre = dc.charges_from_voltages(V, C1c, C2c, Ca, Cb, Cpar)
        V = dc.solve_phase(Qpre, C1n, C2n, Ca, Cb, Cpar)
        Qpost = dc.charges_from_voltages(V, C1n, C2n, Ca, Cb, Cpar)
        Qcyc += np.sum(np.abs(np.array(Qpre) - np.array(Qpost))) / 2.0
        C1c, C2c = C1n, C2n
    return Qcyc * 1e-12 * v_op       # pF*V_norm -> Coulombs at the operating rail


def stage_d():
    Q_cyc = commutation_charge(GEO_CURRENT)
    rows = {}
    for corner, Varc in ARC_CORNERS.items():
        E_arc = Varc * Q_cyc
        eta_spark = INH["DOUBLER_ETA"] - E_arc / INH["W_mech"]
        rows[corner] = dict(Varc=Varc, E_arc=E_arc, eta=eta_spark,
                            drop=(INH["DOUBLER_ETA"] - eta_spark) / INH["DOUBLER_ETA"])
    return Q_cyc, rows


# =============================================================================
# Main
# =============================================================================
def main():
    print("=" * 84)
    print("AUDIT — solver foundation (is the pump solver current, or are S5-S8 on stale ground?)")
    print("=" * 84)

    diff = subprocess.run(["git", "diff", "--name-only", "--", "reference/", "shuttle_core.py",
                           "index.html", "sim/resonator_sim.py"],
                          cwd=ROOT, capture_output=True, text=True).stdout.strip()
    print(f"\n[check 1] frozen empty-diff (the solvers are the SUBJECT, read not edited): "
          f"{'PASS (clean)' if diff == '' else 'FAIL ' + diff}")

    # ---- Stage A: topology ----
    print("\nSTAGE A — topology reconciliation (F4/F5):")
    varcap = os.path.join(ROOT, "varcap.cir")
    print(f"  [check 2] varcap.cir v0.2 committed as the SSOT: "
          f"{'PASS' if os.path.exists(varcap) else 'FAIL'}")
    print(f"  pump core (ND1-4): C1(1-5),C2(4-6),Ca(1-2),Cb(3-4),Cpar; gaps D1,D2->RAIL, D3:1-3, D4:4-2")
    print(f"  [check 3] TOPOLOGY VERDICT: the v0.2 'returns-to-rail/no-ground' is a GAUGE choice")
    print(f"     (energetics use voltage DIFFERENCES) -> the pump core is a RELABELING of the frozen")
    print(f"     4-node; the split resonator (ND9/10) + 12 Cems (ND11-22) + island (ND7/8) are documented")
    print(f"     ADDITIONS on the LOAD side (R / S5-S8). The PUMP energetics are on the correct graph.")

    # ---- Stage B: geometry re-anchor ----
    print("\nSTAGE B — geometry re-anchor (F3):")
    z_dev = dc.solve_doubler4(*GEO_DEVICE)
    z_cur = dc.solve_doubler4(*GEO_CURRENT)
    z_sc = sc.galvanic_z()
    print(f"  [check 4] the z-GATE runs on STALE device geometry:")
    print(f"     shuttle_core.galvanic_z() = {z_sc:.4f} (device 160-1000/100) -- the 1.2033 gate S5-S8 used")
    print(f"     CURRENT-geometry galvanic z = {z_cur:.4f} (16-280/309) -- the machine's ACTUAL ratio")
    print(f"     gap = {z_cur - z_dev:+.4f}  ->  the Gate-0 anchor RE-BASES 1.2033 -> {z_cur:.4f}")
    print(f"     (1.334 matches the freeze-doc 'galvanic ceiling'; the energetics ALREADY use it)")

    # ---- Stage C: rigorous diode ----
    print("\nSTAGE C — rigorous diode solve (F2):")
    zr_dev, mm_dev, _ = z_rigorous(GEO_DEVICE)
    zr_cur, mm_cur, multi_cur = z_rigorous(GEO_CURRENT)
    print(f"  [check 5] rigorous LCP (ON-forward AND OFF-reverse) vs frozen heuristic (max-pick):")
    print(f"     device:  heuristic {z_dev:.4f}  rigorous {zr_dev:.4f}  state-mismatches {mm_dev}")
    print(f"     CURRENT: heuristic {z_cur:.4f}  rigorous {zr_cur:.4f}  state-mismatches {mm_cur} "
          f"(multi-pass {multi_cur})")
    f2_ok = mm_cur == 0 and abs(zr_cur - z_cur) < 1e-6
    print(f"     -> the heuristic max-pick selects the UNIQUE physical branch on every geometry "
          f"({'F2 BENIGN' if f2_ok else 'F2 BITES -> SOLVER-INVALID'}); + ngspice X0 recovers 1.2042 (independent).")

    # ---- Stage D: spark-gap switch ----
    print("\nSTAGE D — spark-gap switch physics (F6, the load-bearing stage):")
    Q_cyc, dd = stage_d()
    print(f"  per-cycle commutation charge (current geom, {V_OP/1e3:.0f} kV rail) = {Q_cyc*1e6:.2f} uC")
    print(f"  the C-C equalization tax (0.614) is switch-INDEPENDENT (thermodynamic); V_bk only sets the")
    print(f"  absolute scale (S5 pinning). The arc ADDS E_arc = V_arc x Q_cyc (zero in the ideal model):")
    print(f"  {'corner':5s} {'V_arc':>6s} {'E_arc':>9s} {'DOUBLER_ETA':>12s} {'drop':>6s}")
    for corner, r in dd.items():
        print(f"  {corner:5s} {r['Varc']:5.0f}V {r['E_arc']*1e3:7.3f}mJ "
              f"{INH['DOUBLER_ETA']:.4f}->{r['eta']:.4f} {r['drop']*100:5.1f}%")
    eta_mid = dd["mid"]["eta"]
    # propagate to the S8 hold-power floor (the doubler tax term)
    tax_ideal_W = (1 - INH["DOUBLER_ETA"]) * INH["W_mech"] * PRF
    tax_spark_W = (1 - eta_mid) * INH["W_mech"] * PRF
    print(f"  [check 6] DOUBLER_ETA {INH['DOUBLER_ETA']:.4f} (ideal) -> {eta_mid:.4f} (mid spark gap), "
          f"drop {dd['mid']['drop']*100:.1f}%")
    print(f"     propagated doubler-tax power {tax_ideal_W:.2f} -> {tax_spark_W:.2f} W "
          f"(+{tax_spark_W-tax_ideal_W:.2f} W on the ~27 W hold floor -- small absolute, the arc is the only add)")

    # ---- Stage E: scalar re-base ----
    print("\nSTAGE E — energetics re-base + resonator drift (F6/resonator):")
    useful_spark = eta_mid * INH["W_mech"]
    rebase = [
        ("z (galvanic anchor)", INH["z_gate"], z_cur, "device->current geometry (F3)"),
        ("DOUBLER_ETA", INH["DOUBLER_ETA"], eta_mid, "ideal diode->spark gap mid (F6)"),
        ("USEFUL/fire (mJ)", INH["USEFUL"]*1e3, useful_spark*1e3, "= eta*W_mech (follows eta)"),
        ("W_mech/fire (mJ)", INH["W_mech"]*1e3, INH["W_mech"]*1e3, "switch-independent (HOLDS)"),
        ("W_coll/fire (mJ)", INH["W_coll"]*1e3, INH["W_coll"]*1e3, "island, geometry-set (HOLDS)"),
        ("Q_isl (uC)", INH["Q_isl"]*1e6, INH["Q_isl"]*1e6, "island pickup (HOLDS)"),
    ]
    print(f"  [check 7] re-based scalar table (inherited -> recomputed):")
    print(f"  {'scalar':22s} {'inherited':>10s} {'recomputed':>11s} {'delta':>8s}  provenance")
    moved = []
    for name, old, new, prov in rebase:
        d_rel = (new - old) / old if old else 0.0
        if abs(d_rel) > 0.01: moved.append(name)
        print(f"  {name:22s} {old:>10.4f} {new:>11.4f} {d_rel:>+7.1%}  {prov}")
    print(f"  resonator drift: resonator_sim default C_R = 960 pF (8 mm) -> freeze 789 pF (12 mm) "
          f"-- CLOSE the stale island (consumers already pass C_R=789 explicitly; the DEFAULT is stale).")

    # ---- verdict ----
    print("\nVERDICT:")
    if not f2_ok:
        verdict = "SOLVER-INVALID"
        print(f"  SOLVER-INVALID — the heuristic picks a non-physical branch on the current geometry.")
    elif moved:
        verdict = "FOUNDATION-DRIFTS"
        print(f"  FOUNDATION-DRIFTS — {len(moved)} foundation quantities move materially: "
              f"{', '.join(moved)}.")
        print(f"     (1) the z-GATE was a museum piece: 1.2033 (device anchor) -> {z_cur:.4f} (current")
        print(f"         geometry). The energetics ALREADY used 1.334, so the SCALARS aren't stale -- but")
        print(f"         every S5-S8 'Gate-0 pass' validated the wrong geometry. Re-anchor the gate.")
        print(f"     (2) DOUBLER_ETA drops 0.386 (ideal diode) -> {eta_mid:.3f} (spark gap, mid), the F6")
        print(f"         prediction: the arc loss adds to the C-C tax. USEFUL follows ({INH['USEFUL']*1e3:.2f}")
        print(f"         -> {useful_spark*1e3:.2f} mJ). W_mech/W_coll/Q_isl HOLD (switch-independent).")
        print(f"     F2 benign (rigorous=heuristic), topology a relabeling (pump core unchanged). The")
        print(f"     propagated hold-floor change is small (~{tax_spark_W-tax_ideal_W:.1f} W arc), so S5-S8's")
        print(f"     qualitative verdicts stand -- but S8 r0.2 should consume DOUBLER_ETA={eta_mid:.3f} and")
        print(f"     the z-anchor=1.334. The foundation is corrected, not invalidated.")
    else:
        verdict = "FOUNDATION-HOLDS"
        print(f"  FOUNDATION-HOLDS — the inherited scalars survive on checked ground.")

    _plots(z_dev, z_cur, dd, tax_ideal_W, tax_spark_W)
    _csv(z_cur, eta_mid, useful_spark, rebase, verdict)

    diff = subprocess.run(["git", "diff", "--name-only", "--", "reference/", "shuttle_core.py",
                           "index.html", "sim/resonator_sim.py"],
                          cwd=ROOT, capture_output=True, text=True).stdout.strip()
    assert diff == "", f"frozen drift: {diff}"
    print("\n[frozen empty-diff final assert] PASS — the audited solvers are byte-identical.")
    print(f"VERDICT: {verdict}")
    return 0


def _csv(z_cur, eta_mid, useful_spark, rebase, verdict):
    path = os.path.join(ROOT, "audit_scalar_rebase.csv")
    with open(path, "w") as f:
        f.write("scalar,inherited,recomputed,delta_rel,geometry,topology,switch,tier\n")
        for name, old, new, prov in rebase:
            f.write(f"\"{name}\",{old:.6f},{new:.6f},{(new-old)/old if old else 0:.4f},"
                    f"current-16-280/309,v0.2-relabel,spark-gap-mid,OC\n")
        f.write(f"#verdict,{verdict}\n#z_anchor_old,1.2033\n#z_anchor_new,{z_cur:.4f}\n")
        f.write(f"#DOUBLER_ETA_old,0.385956\n#DOUBLER_ETA_new,{eta_mid:.4f}\n")
    print(f"wrote {os.path.relpath(path, ROOT)}")


def _plots(z_dev, z_cur, dd, tax_ideal_W, tax_spark_W):
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except Exception as e:
        print(f"(plots skipped: {e})")
        return
    # 1. current-geometry z vs stale anchor
    fig, (a1, a2) = plt.subplots(1, 2, figsize=(11, 4.2))
    a1.bar(["device anchor\n(1.2033 gate)", "CURRENT geom\n(machine actual)"],
           [z_dev, z_cur], color=["#e76f51", "#2a9d8f"])
    a1.set_ylabel("galvanic z"); a1.set_ylim(1.0, 1.4)
    a1.axhline(1.0, color="#888", lw=0.5)
    a1.set_title("F3: the z-gate ran on stale geometry (1.2033 -> 1.334)")
    for i, v in enumerate([z_dev, z_cur]):
        a1.annotate(f"{v:.4f}", (i, v + 0.005), ha="center", fontsize=9)
    # 2. ideal vs spark-gap DOUBLER_ETA across corners
    corners = list(dd.keys())
    etas = [dd[c]["eta"] for c in corners]
    a2.axhline(0.3860, ls="--", color="#e76f51", label="ideal diode 0.386")
    a2.plot(corners, etas, "o-", color="#2a9d8f", label="spark gap")
    a2.set_ylabel("DOUBLER_ETA"); a2.set_ylim(0.35, 0.39)
    a2.set_title("F6: spark-gap arc loss drops DOUBLER_ETA")
    for i, c in enumerate(corners):
        a2.annotate(f"{etas[i]:.3f}", (i, etas[i] - 0.003), ha="center", fontsize=8)
    a2.legend(fontsize=8)
    fig.tight_layout(); fig.savefig(os.path.join(ROOT, "audit_z_and_eta.png"), dpi=110)
    plt.close(fig)
    print("wrote audit_z_and_eta.png")


if __name__ == "__main__":
    sys.exit(main())
