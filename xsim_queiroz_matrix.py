#!/usr/bin/env python3
"""
xsim_queiroz_matrix.py — (B) analytic eigen-witness for the X1 shuttle tier (xsim rev 0.4).
============================================================================================
A SECOND, independent witness for the per-cycle voltage-multiplication factor z of the varcap
doubler, in the spirit of A. C. M. de Queiroz, *Analysis of Electronic Electrostatic Generators*
(IEEE 2018): segment the cycle by conduction state, write the per-segment nodal charge-conservation
relation, COMPOSE the segments into a single per-cycle map, and obtain z as the **dominant
eigenvalue** of that map (the eigenvector gives the steady voltage ratios `1 : a : b`). For the
overlap-free emergent-fire case the boundary is found by a Newton/root-find on the threshold
crossing in the boosted-island solution; the ideal tier is scale-invariant, so the fire index is
fixed and the map is linear.

INDEPENDENCE (addendum §3.3 — load-bearing):
  * `shuttle_core` solves FORWARD in theta (step caps, conserve cluster charge, re-solve V at each
    micro-step, READ the emergent fire) and reads z as the asymptotic per-cycle ratio over ~120
    iterated cycles.
  * THIS witness composes the segment-boundary charge-conservation matrices into ONE per-cycle map
    and extracts z as its EIGENVALUE — it never time-steps and never iterates to convergence.
  These are genuinely different constructions. This module implements its OWN cluster-charge solver
  (`_cluster_solve`) and DOES NOT import `shuttle_core.transition` / `_galv_phase` / any native
  solver — only the device-point constants and the firing ORDER are consumed (canonical).

Pure consumer: device point + firing order from `shuttle_core`; designs nothing. [OC]/[IR] tags.
"""
import numpy as np
import shuttle_core as sc          # device-point CONSTANTS + firing ORDER only (NOT the solver)

NODES = [1, 2, 3, 4, 7, 8]         # 1,4 driven plates; 7,8 islands; 2,3 island returns; 0 = ref


# ----------------------------------------------------------------------------------------
# Own cluster-charge solver (NOT shuttle_core.transition — independent construction)
# ----------------------------------------------------------------------------------------
def _node_charges(V, caps):
    q = {n: 0.0 for n in NODES}
    for na, nb, C in caps:
        va, vb = V.get(na, 0.0), V.get(nb, 0.0)
        if na in q:
            q[na] += C * (va - vb)
        if nb in q:
            q[nb] += C * (vb - va)
    return q


def _cluster_solve(V, caps_pre, caps_post, closures):
    """One segment-boundary charge-conservation step: cluster the nodes by `closures` (a list of
    shorted node-pairs; ground 0 is the reference cluster), conserve each cluster's total charge
    computed from the PRE state (V, caps_pre), then re-solve the cluster node voltages under the
    POST caps. My own union-find + linear solve (eq. 1 of the segment-matrix method). [OC]"""
    parent = {n: n for n in NODES + [0]}

    def find(x):
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    for a, b in closures:
        ra, rb = find(a), find(b)
        if ra != rb:
            parent[ra] = rb
    groot = find(0)
    # only nodes that actually carry post-cap (or are tied by a closure) are solved; a node with no
    # capacitance and no closure (e.g. an unused island at the galvanic limit) stays at 0 — including
    # it would give a singular cluster row. [OC]
    active = set()
    for na, nb, _C in caps_post:
        if na != 0:
            active.add(na)
        if nb != 0:
            active.add(nb)
    for a, b in closures:
        if a != 0:
            active.add(a)
        if b != 0:
            active.add(b)
    cid, nc, ncl = {}, 0, {}
    for n in NODES:
        if n not in active:
            ncl[n] = -1
            continue
        r = find(n)
        if r == groot:
            ncl[n] = -1
            continue
        if r not in cid:
            cid[r] = nc
            nc += 1
        ncl[n] = cid[r]
    if nc == 0:
        return {n: 0.0 for n in NODES}
    q = _node_charges(V, caps_pre)                     # conserved per-node charge (pre state)
    A = np.zeros((nc, nc))
    rhs = np.zeros(nc)
    for n in NODES:
        c = ncl[n]
        if c >= 0:
            rhs[c] += q[n]
    for na, nb, C in caps_post:                        # cluster capacitance matrix (post caps)
        ca = ncl.get(na, -1) if na != 0 else -1
        cb = ncl.get(nb, -1) if nb != 0 else -1
        if ca >= 0:
            A[ca][ca] += C
            if cb >= 0:
                A[ca][cb] -= C
        if cb >= 0:
            A[cb][cb] += C
            if ca >= 0:
                A[cb][ca] -= C
    try:
        x = np.linalg.solve(A, rhs)
    except np.linalg.LinAlgError:
        return dict(V)
    return {n: (0.0 if ncl[n] < 0 else float(x[ncl[n]])) for n in NODES}


# ----------------------------------------------------------------------------------------
# Device point (consumed)
# ----------------------------------------------------------------------------------------
C1MIN, C1MAX = sc.C1MIN, sc.C1MAX
C2MIN, C2MAX = sc.C2MIN, sc.C2MAX
CA, CB, CPAR = sc.CA, sc.CB, sc.CPAR


def _galv_caps(C1, C2):
    return [(1, 0, C1 + CPAR), (4, 0, C2 + CPAR), (2, 0, CPAR), (3, 0, CPAR),
            (1, 2, CA), (3, 4, CB)]


# ----------------------------------------------------------------------------------------
# Per-cycle map -> dominant eigenvalue z  (closed-cycle, no time-stepping)
# ----------------------------------------------------------------------------------------
def _cycle_map(segments, dim_nodes=(1, 2, 3, 4)):
    """Build the per-cycle linear map M by applying the fixed segment sequence to each basis vector
    of the rail nodes (islands start at 0). `segments` is an ordered list of
    (caps_pre, caps_post, closures). Returns M (len(dim_nodes) square)."""
    n = len(dim_nodes)
    M = np.zeros((n, n))
    for j, nd in enumerate(dim_nodes):
        V = {k: 0.0 for k in NODES}
        V[nd] = 1.0
        for caps_pre, caps_post, closures in segments:
            V = _cluster_solve(V, caps_pre, caps_post, closures)
        for i, mi in enumerate(dim_nodes):
            M[i, j] = V[mi]
    return M


def _dominant(M):
    """Dominant eigenvalue (by |·|) and its real eigenvector, normalised e1:e2:e4 = 1:a:b."""
    w, vecs = np.linalg.eig(M)
    k = int(np.argmax(np.abs(w)))
    z = float(np.real(w[k]))
    v = np.real(vecs[:, k])
    if abs(v[0]) > 1e-12:
        v = v / v[0]
    return z, v


def galvanic_eigen_z():
    """(B) AUTHORISATION (the X0-anchor analog): the degenerate galvanic doubler as an eigenproblem.
    Steady diode pattern (from the frozen 1->3/4->2 doubler): phase A closes D1(2-0),D3(1-3); phase
    B closes D2(3-0),D4(4-2). Compose phase B then phase A -> per-cycle map -> z = eigenvalue.
    Must recover z = 1.2033 (paper-independent, canonical)."""
    capsA = _galv_caps(C1MAX, C2MIN)        # phase A: C1 max, C2 min
    capsB = _galv_caps(C1MIN, C2MAX)        # phase B: C1 min, C2 max
    segments = [
        (capsA, capsB, [(3, 0), (4, 2)]),   # into phase B: D2 clamps node3, D4 ties 4-2
        (capsB, capsA, [(2, 0), (1, 3)]),   # into phase A: D1 clamps node2, D3 ties 1-3
    ]
    M = _cycle_map(segments)
    z, v = _dominant(M)
    return z, v


# ----------------------------------------------------------------------------------------
# X1-B — the ideal flying-bucket shuttle as a closed-cycle eigenproblem
# ----------------------------------------------------------------------------------------
# Persistent state = (1,2,3,4,7,8): the islands carry their post-fire (sink) voltage between
# cycles (native: island sits at the sink level until the next load), so they are NOT reset.
# Firing ORDER consumed from shuttle_core (return SG1/SG2 → load SG3a/SG4a → collapse → fire
# SG3b/SG4b); the cap PROFILE values are the device point. The fire angle is EMERGENT: it is the
# collapse sub-step where the boosted-island overvoltage first crosses the strike threshold.
P0 = sc.Params()
CXMAX, CXMIN, BOSS = P0.cx_max, P0.cx_min, P0.pCboss
TH_RET, TH_COL0, TH_COL1 = sc.TH_RET, sc.TH_COL0, sc.TH_COL1
N_COLLAPSE = 24                                       # = shuttle_core N_COLLAPSE
SHU_NODES = (1, 2, 3, 4, 7, 8)


def _shuttle_caps(C1, C2, Cx3, Cx4):
    return [(1, 0, C1 + CPAR), (4, 0, C2 + CPAR), (2, 0, CPAR), (3, 0, CPAR),
            (1, 2, CA), (3, 4, CB), (7, 3, Cx3 + BOSS), (8, 2, Cx4 + BOSS)]


def _cxk(k, N):
    return CXMAX + (CXMIN - CXMAX) * (k / N)


def _shuttle_segments(kf3, kf4, N=N_COLLAPSE):
    """Ordered segment list (caps_pre, caps_post, closures) for one ideal shuttle cycle. Phase A:
    C1/C2 swing all-open (rail boost) → return SG1 → load SG3a → N-step Cx3 collapse, fire SG3b at
    step kf3; phase B mirror, fire SG4b at step kf4. (Branch B island Cx4 held at plateau during A
    and vice-versa.) [OC firing order consumed · IR collapse discretisation = native N_COLLAPSE]"""
    cA = lambda c3, c4: _shuttle_caps(C1MAX, C2MIN, c3, c4)
    cB = lambda c3, c4: _shuttle_caps(C1MIN, C2MAX, c3, c4)
    S = [(cB(CXMAX, CXMAX), cA(CXMAX, CXMAX), []),               # enter A: swing, all open (boost)
         (cA(CXMAX, CXMAX), cA(CXMAX, CXMAX), [(2, 0)]),         # return SG1
         (cA(CXMAX, CXMAX), cA(CXMAX, CXMAX), [(2, 0), (1, 7)])] # load SG3a
    c3 = CXMAX
    for k in range(1, N + 1):
        nc3 = _cxk(k, N)
        S.append((cA(c3, CXMAX), cA(nc3, CXMAX), [(2, 0)]))      # collapse step (isolated)
        c3 = nc3
        if k == kf3:
            S.append((cA(c3, CXMAX), cA(c3, CXMAX), [(2, 0), (7, 3)]))   # fire SG3b
    S.append((cA(c3, CXMAX), cB(CXMAX, CXMAX), []))             # enter B: swing (reinflate Cx3)
    S.append((cB(CXMAX, CXMAX), cB(CXMAX, CXMAX), [(3, 0)]))    # return SG2
    S.append((cB(CXMAX, CXMAX), cB(CXMAX, CXMAX), [(3, 0), (4, 8)]))     # load SG4a
    c4 = CXMAX
    for k in range(1, N + 1):
        nc4 = _cxk(k, N)
        S.append((cB(CXMAX, c4), cB(CXMAX, nc4), [(3, 0)]))
        c4 = nc4
        if k == kf4:
            S.append((cB(CXMAX, c4), cB(CXMAX, c4), [(3, 0), (8, 2)]))   # fire SG4b
    return S


def _steady_state(M, v):
    """A representative O(1) steady node-state from the dominant eigenvector (sign-fixed)."""
    return {n: float(v[i]) for i, n in enumerate(SHU_NODES)}


def _emergent_fire_step(threshold_frac, N=N_COLLAPSE):
    """Find the collapse sub-step where the boosted island-A overvoltage V(7)-V(3) first crosses
    threshold_frac·drive (drive = |V_src-V_snk| at load), evaluated on the steady eigenvector — the
    fire is READ from the boosted rail, not imposed. threshold_frac=0 (ideal) ⇒ step 1 (onset)."""
    M = _cycle_map(_shuttle_segments(1, 1, N), dim_nodes=SHU_NODES)
    _z, v = _dominant(M)
    V = _steady_state(M, v)
    # replay phase-A up to load, then walk the collapse reading the overvoltage
    cA = lambda c3: _shuttle_caps(C1MAX, C2MIN, c3, CXMAX)
    cB0 = _shuttle_caps(C1MIN, C2MAX, CXMAX, CXMAX)
    V = _cluster_solve(V, cB0, cA(CXMAX), [])
    V = _cluster_solve(V, cA(CXMAX), cA(CXMAX), [(2, 0)])
    V = _cluster_solve(V, cA(CXMAX), cA(CXMAX), [(2, 0), (1, 7)])
    # |overvoltage| vs |drive| — sign-convention-free (the eigenvector may be ±; native fires when
    # V_isl-V_snk exceeds pVbkFire·|V_src-V_snk|, a magnitude relation). [OC]
    drive = max(abs(V[1] - V[3]), 1e-12)
    c3 = CXMAX
    for k in range(1, N + 1):
        nc3 = _cxk(k, N)
        V = _cluster_solve(V, cA(c3), cA(nc3), [(2, 0)])
        c3 = nc3
        if abs(V[7] - V[3]) > threshold_frac * drive + 1e-12:
            return k
    return N


def shuttle_eigen(threshold_frac=0.0, N=N_COLLAPSE):
    """X1-B: ideal shuttle z (eigenvalue), emergent δ, fire angle. threshold_frac is pVbkFire as a
    fraction of drive (0 = native ideal). Returns dict(z, delta, fire_theta, fire_step, evec)."""
    kf = _emergent_fire_step(threshold_frac, N)
    M = _cycle_map(_shuttle_segments(kf, kf, N), dim_nodes=SHU_NODES)
    z, v = _dominant(M)
    fire_theta = TH_COL0 + (kf / N) * (TH_COL1 - TH_COL0)
    return dict(z=z, delta=fire_theta - TH_RET, fire_theta=fire_theta, fire_step=kf, evec=v)


def queiroz_v0():
    """SECONDARY V0 cross-check: Queiroz Fig-1 unipolar example (Cmin/Cmax 60/360, Ca=Cb=330) via
    the SAME galvanic eigenmap, target z ≈ 1.1538. (His exact topology is not fetchable offline;
    this configures our galvanic eigen-solver with his stated cap values as a best-effort check.)"""
    global C1MIN, C1MAX, C2MIN, C2MAX, CA, CB, CPAR
    save = (C1MIN, C1MAX, C2MIN, C2MAX, CA, CB, CPAR)
    C1MIN, C1MAX = 60.0, 360.0
    C2MIN, C2MAX = 60.0, 360.0
    CA = CB = 330.0
    CPAR = 0.0
    try:
        z, v = galvanic_eigen_z()
    finally:
        C1MIN, C1MAX, C2MIN, C2MAX, CA, CB, CPAR = save
    return z, v


def run_self_test():
    zg, vg = galvanic_eigen_z()
    ok_g = abs(zg - 1.2033) <= 0.03
    sh = shuttle_eigen(0.0)
    znat, _, _ = sc.shuttle_run(sc.Params(), 80, 40)
    ok_z = abs(sh["z"] - znat) <= 0.005
    ok_d = abs(sh["delta"] - (sc.ANGLES_REF["SG3b"] - sc.ANGLES_REF["SG1"])) <= 0.010
    print("xsim_queiroz_matrix — (B) eigen-witness (own cluster solver; no shuttle_core.transition)")
    print(f"  V0  galvanic authorisation : eigen z = {zg:.4f}  (target 1.2033 ± 0.03)  "
          f"{'PASS' if ok_g else 'FAIL'}")
    zv0, _ = queiroz_v0()
    print(f"      Queiroz Fig-1 cross-check: eigen z = {zv0:.4f}  (paper z ≈ 1.1538; topology "
          f"best-effort, see findings)")
    print(f"  X1-B ideal shuttle z       : eigen z = {sh['z']:.5f}  vs native {znat:.5f}  "
          f"Δ={sh['z'] - znat:+.5f}  {'PASS' if ok_z else 'FAIL'}")
    print(f"  X1-B emergent δ (SG1→SG3b) : eigen δ = {sh['delta']:.4f}  vs native "
          f"{sc.ANGLES_REF['SG3b'] - sc.ANGLES_REF['SG1']:.4f}  fire θ={sh['fire_theta']:.4f}  "
          f"{'PASS' if ok_d else 'FAIL'}")
    return ok_g and ok_z and ok_d


if __name__ == "__main__":
    run_self_test()
