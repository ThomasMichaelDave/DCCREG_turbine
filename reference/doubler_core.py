#!/usr/bin/env python3
"""
doubler_core.py  —  read-only Python MIRROR of the frozen JS solveDoubler4.
===========================================================================
Ported line-for-line from index.html (solveLinear / chargesFromVoltages /
solvePhase / solveDoubler4). The JS in the repo remains the authority; this
mirror exists only to expose the per-phase node-voltage TRACE for plotting
(producer/consumer discipline — the solver logic is not changed, only read).

Fidelity is asserted by run_self_test(): it must reproduce the JS anchors
(no-swing 1.000, device 1.203, narrow 1.000, wide 1.438).

Tiers: [OC] standard physics/math · [IR] modelling choice
"""
import numpy as np

DIODES = [(2, 0), (3, 0), (1, 3), (4, 2)]   # D1,D2,D3,D4  (anode -> cathode)  [OC]

def charges_from_voltages(V, C1, C2, Ca, Cb, Cpar):
    v1, v2, v3, v4 = V
    return np.array([
        (C1 + Cpar) * v1 + Ca * (v1 - v2),
        Cpar * v2 + Ca * (v2 - v1),
        Cpar * v3 + Cb * (v3 - v4),
        (C2 + Cpar) * v4 + Cb * (v4 - v3),
    ])

def solve_linear(A, b):
    try:
        return np.linalg.solve(A, b)
    except np.linalg.LinAlgError:
        return None

def solve_phase(Q, C1, C2, Ca, Cb, Cpar, eps=1e-9):
    kd1, kd2, kd3, kd4 = C1 + Cpar + Ca, Cpar + Ca, Cpar + Cb, C2 + Cpar + Cb
    bestV, bestMag = None, -np.inf
    for s in range(16):
        d = [(s >> i) & 1 for i in range(4)]
        parent = [0, 1, 2, 3, 4]
        def find(x):
            while parent[x] != x:
                parent[x] = parent[parent[x]]; x = parent[x]
            return x
        def union(a, b):
            ra, rb = find(a), find(b)
            if ra != rb: parent[ra] = rb
        for i, on in enumerate(d):
            if on: union(*DIODES[i])
        groot = find(0)
        cluster_id, nc = {}, 0
        for i in range(1, 5):
            r = find(i)
            if r == groot: continue
            if r not in cluster_id: cluster_id[r] = nc; nc += 1
        node_cluster = [0] * 5
        for i in range(1, 5):
            r = find(i)
            node_cluster[i] = -1 if r == groot else cluster_id[r]
        if nc == 0:
            V = [0.0, 0.0, 0.0, 0.0]
        else:
            A = np.zeros((nc, nc)); rhs = np.zeros(nc)
            for i in range(1, 5):
                c = node_cluster[i]
                if c >= 0: rhs[c] += Q[i - 1]
            def addK(i, kdiag, neighbour, kOff):
                c = node_cluster[i]
                if c < 0: return
                A[c][c] += kdiag
                cj = node_cluster[neighbour]
                if cj >= 0: A[c][cj] += kOff
            addK(1, kd1, 2, -Ca); addK(2, kd2, 1, -Ca)
            addK(3, kd3, 4, -Cb); addK(4, kd4, 3, -Cb)
            x = solve_linear(A, rhs)
            if x is None: continue
            V = [0.0 if node_cluster[i] < 0 else x[node_cluster[i]] for i in range(1, 5)]
        v1, v2, v3, v4 = V
        if not d[0] and v2 > eps: continue          # D1: V2 <= 0
        if not d[1] and v3 > eps: continue          # D2: V3 <= 0
        if not d[2] and v1 > v3 + eps: continue     # D3: V1 <= V3
        if not d[3] and v4 > v2 + eps: continue     # D4: V4 <= V2
        mag = abs(v1) + abs(v4)
        if mag > bestMag: bestMag, bestV = mag, V
    return bestV if bestV is not None else [0.0, 0.0, 0.0, 0.0]

def solve_doubler4(C1min, C1max, C2min, C2max, Ca, Cb, Cpar,
                   iterations=120, burn=60, trace=False):
    """Returns z (median asymptotic |V1|+|V4| ratio). If trace=True also returns
    a list of per-phase records over ALL cycles: (cycle, phase, C1, C2, [v1..v4])."""
    V = [-1.0, 0.0, 0.0, -1.0]                  # down-pumping seed, |V|=2     [OC]
    C1cur, C2cur = C1max, C2min                 # notional end of phase A
    ratios, rec = [], []
    prevMag = abs(V[0]) + abs(V[3])
    for cyc in range(iterations):
        # phase B: C1 -> min, C2 -> max
        Q = charges_from_voltages(V, C1cur, C2cur, Ca, Cb, Cpar)
        V = solve_phase(Q, C1min, C2max, Ca, Cb, Cpar)
        C1cur, C2cur = C1min, C2max
        if trace: rec.append((cyc, "B", C1cur, C2cur, list(V)))
        # phase A: C1 -> max, C2 -> min
        Q = charges_from_voltages(V, C1cur, C2cur, Ca, Cb, Cpar)
        V = solve_phase(Q, C1max, C2min, Ca, Cb, Cpar)
        C1cur, C2cur = C1max, C2min
        if trace: rec.append((cyc, "A", C1cur, C2cur, list(V)))

        mag = abs(V[0]) + abs(V[3])
        if cyc >= burn and prevMag > 1e-15 and mag > 1e-15:
            ratios.append(mag / prevMag)
        prevMag = mag
        maxV = max(abs(v) for v in V)
        if maxV > 1e6 or (0 < maxV < 1e-6):
            sc = 1.0 / maxV
            V = [v * sc for v in V]; prevMag *= sc
    z = float(np.median(ratios)) if ratios else 1.0
    return (z, rec) if trace else z

ANCHORS = [
    ("no-swing", (500, 500, 500, 500, 100, 100, 10), 1.000, 0.005),
    ("device",   (160, 1000, 160, 1000, 100, 100, 20), 1.203, 0.03),
    ("narrow",   (400, 600, 400, 600, 100, 100, 20), 1.000, 0.04),
    ("wide",     (100, 2000, 100, 2000, 100, 100, 20), 1.438, 0.06),
]

def run_self_test():
    print("Python mirror vs frozen JS solveDoubler4 anchors:")
    ok = True
    for name, args, exp, tol in ANCHORS:
        z = solve_doubler4(*args)
        p = abs(z - exp) <= tol
        ok = ok and p
        print(f"  {name:9s} z = {z:7.4f}  expected {exp:6.3f} ±{tol:<5.3f}  {'PASS' if p else 'FAIL'}")
    print("  -> mirror is", "FAITHFUL" if ok else "NOT matching — do not trust the trace")
    return ok

if __name__ == "__main__":
    run_self_test()
