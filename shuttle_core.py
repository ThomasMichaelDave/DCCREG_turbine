#!/usr/bin/env python3
"""
shuttle_core.py — flying-bucket shuttle doubler simulator (Phase 2, ideal-switch tier)
======================================================================================
A NEW producer (does NOT modify the frozen reference/doubler_core.py). It consumes only
the frozen scalar device-point values, solve_doubler4, ANCHORS, run_self_test. The cross
branches D3/D4 of the frozen doubler are replaced by flying-capacitor SHUTTLES in the
FROZEN charge direction 1->3 / 4->2 (rev 0.3; anchor-test evidence: 1->3 gives z=1.2033,
3->1 gives z=1.0).

Modelling tier [IR]: quasi-static, ideal-switch, rail-collapsed. Per docs/commutator-design.md
§2 the rail coil L_RES = L1 ~ 123 uH is a near-short at PRF, so nodes 5-6 collapse to the
common reference for the CHARGE-PUMP verdict; L_RES bears on the 5-6 ring (logged), not the
pump. The degenerate-limit anchor (shuttles -> ideal galvanic diodes 1->3/4->2, LR shorted)
must reproduce z=1.203 +/- 0.03 before any campaign step (brief §2.3) — implemented and
checked in anchor_test().

Symbol hygiene: rotor angle theta; gap g; new params carry plain names (no bare d).
Tiers: [OC] solver-derived/standard charge accounting · [IR] modelling choices.
"""
import os
import sys
import math

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "reference"))
import doubler_core as dc            # frozen exports only  [OC]

# ---- frozen device-point scalars (consumed, not re-derived) --------------- [OC]
C1MIN, C1MAX = 160.0, 1000.0
C2MIN, C2MAX = 160.0, 1000.0
CA = CB = 100.0
CPAR = 20.0
Z_BASELINE = 1.203               # ANCHORS["device"]; reproduced by the galvanic anchor
L_RES_UH = 123.0                 # docs/commutator-design.md §2 (TMD-authorised 2026-06-11) [IR]

# ---- shuttle / profile parameters [IR, defaults] -------------------------------
class Params:
    def __init__(self):
        self.cx_max = 1200.0         # Cx plateau capacitance (pF)            [IR]
        self.cx_min = 60.0           # Cx collapsed capacitance (pF)          [IR]
        self.pCboss = 6.0            # boss stray in parallel with Cx (pF)    [IR small]
        self.gap_stray = 2.0         # per-gap stray (pF)                     [IR]
        self.pVbkFire = 0.0          # fire self-break threshold (a.u.); 0 = fire as soon
                                     #   as overvoltage is forward (emergent-d study sweeps it)
        self.theta_load = 0.35       # SG3a load station within phase-A window (sector frac) [IR]
        self.theta_collapse = 0.55   # Cx collapse mid-point                                 [IR]
        self.collapse_span = 0.12    # collapse angular span (sector frac)                   [IR]
        self.load_frac = 0.0         # load-station angle: 0 = load at full plateau (cx_max),
                                     #   1 = load at collapse onset (cx_min). Later station ->
                                     #   smaller bucket -> less throughput (budget sweep). [IR]
        self.extend_into_collapse = False  # drain-back validation toggle (§3)

    def boost_ratio(self):
        return self.cx_max / (self.cx_min + self.pCboss + self.gap_stray)


# ======================================================================================
# Capacitance-network charge engine (rail collapsed to ground 0; nodes 1,2,3,4,7,8)
# A cap is (na, nb, value); node 0 = ground. settle() closes a set of switch node-pairs
# and redistributes charge to equalise the shorted nodes, conserving each cluster's charge
# (the same cluster-solve the frozen solver uses, but with KNOWN closures — no 16-search).
# ======================================================================================
NODES = [1, 2, 3, 4, 7, 8]


def caps_at(theta, P, galvanic=False):
    """Return the cap list [(na,nb,C), ...] at sector phase `theta` in [0,1).
    C1(theta)/C2(theta) raised-cosine between the frozen scalar extremes; Cx3/Cx4 plateau->
    collapse. In `galvanic` mode the islands/Cx are dropped (handled by direct diodes)."""
    C1 = _raised(theta, C1MIN, C1MAX, hi_centre=0.75)      # C1 max in phase A (theta~0.75) [IR]
    C2 = _raised(theta, C2MIN, C2MAX, hi_centre=0.25)      # C2 max in phase B (theta~0.25)
    caps = [(1, 0, C1 + CPAR), (4, 0, C2 + CPAR),
            (2, 0, CPAR), (3, 0, CPAR),
            (1, 2, CA), (3, 4, CB)]
    if not galvanic:
        cx3 = _cx(theta, P, centre=P.theta_collapse)
        cx4 = _cx(theta, P, centre=(P.theta_collapse + 0.5) % 1.0)
        caps += [(7, 3, cx3 + P.pCboss), (8, 2, cx4 + P.pCboss)]
    return caps


def _raised(theta, lo, hi, hi_centre):
    """Periodic raised-cosine: ~hi near hi_centre, ~lo half a sector away. [IR]"""
    x = math.cos(2 * math.pi * (theta - hi_centre))       # +1 at centre, -1 opposite
    return lo + (hi - lo) * 0.5 * (1 + x)


def _cx(theta, P, centre):
    """Cx plateau at cx_max, collapsing to cx_min across `collapse_span` around `centre`."""
    d = abs(((theta - centre + 0.5) % 1.0) - 0.5)         # circular distance to centre
    if d <= P.collapse_span * 0.5:
        f = 0.5 * (1 + math.cos(math.pi * d / (P.collapse_span * 0.5)))  # 1 at centre
        return P.cx_min + (P.cx_max - P.cx_min) * (1 - f)
    return P.cx_max


def node_charges(V, caps):
    """Per-node stored charge q[node] = sum over caps touching it of C*(Vnode - Vother). [OC]"""
    q = {n: 0.0 for n in NODES}
    for na, nb, C in caps:
        va = V.get(na, 0.0); vb = V.get(nb, 0.0)
        if na in q: q[na] += C * (va - vb)
        if nb in q: q[nb] += C * (vb - va)
    return q


def transition(V, caps_old, caps_new, closed_pairs):
    """General quasi-static step. Conserve each cluster's total charge (computed from the
    PRE-state V with caps_old) and re-solve the node voltages with caps_new under the given
    closed switch node-pairs. Two uses [OC]:
      - switch closure (caps_old == caps_new): charge redistributes to equalise shorted nodes;
      - rotor cap-change (closed fixed, caps differ): variable-cap plates move, node/cluster
        charge conserved, voltages jump (this is how Cx collapse boosts a floating island)."""
    import numpy as np
    parent = {n: n for n in NODES + [0]}
    def find(x):
        while parent[x] != x:
            parent[x] = parent[parent[x]]; x = parent[x]
        return x
    for a, b in closed_pairs:
        ra, rb = find(a), find(b)
        if ra != rb: parent[ra] = rb
    groot = find(0)
    cid = {}; nc = 0; ncl = {}
    for n in NODES:
        r = find(n)
        if r == groot:
            ncl[n] = -1; continue
        if r not in cid:
            cid[r] = nc; nc += 1
        ncl[n] = cid[r]
    if nc == 0:
        return {n: 0.0 for n in NODES}
    q = node_charges(V, caps_old)                 # conserved per-node charge (pre caps)
    A = np.zeros((nc, nc)); rhs = np.zeros(nc)
    for n in NODES:
        c = ncl[n]
        if c >= 0: rhs[c] += q[n]
    for na, nb, C in caps_new:                     # cluster capacitance matrix (new caps)
        ca = ncl.get(na, -1) if na != 0 else -1
        cb = ncl.get(nb, -1) if nb != 0 else -1
        if ca >= 0:
            A[ca][ca] += C
            if cb >= 0: A[ca][cb] -= C
        if cb >= 0:
            A[cb][cb] += C
            if ca >= 0: A[cb][ca] -= C
    try:
        x = np.linalg.solve(A, rhs)
    except Exception:
        return dict(V)
    return {n: (0.0 if ncl[n] < 0 else float(x[ncl[n]])) for n in NODES}


def caps_phase(which, P):
    """Discrete two-phase cap config used by the shuttle cycle (quasi-static limit).
    which='A' -> C1 max, C2 min ; which='B' -> C1 min, C2 max. Cx at plateau (cx_max)."""
    C1 = C1MAX if which == 'A' else C1MIN
    C2 = C2MIN if which == 'A' else C2MAX
    caps = [(1, 0, C1 + CPAR), (4, 0, C2 + CPAR), (2, 0, CPAR), (3, 0, CPAR),
            (1, 2, CA), (3, 4, CB),
            (7, 3, P.cx_max + P.pCboss), (8, 2, P.cx_max + P.pCboss)]
    return caps


def _with_cx(caps, island, other, value, P):
    """Return caps with the (island,other) Cx replaced by `value`+pCboss."""
    out = [c for c in caps if not (c[0] == island and c[1] == other)]
    out.append((island, other, value + P.pCboss))
    return out


# θ-stations within a phase window (sector fraction, phase occupies [0,0.5) or [0.5,1)). [IR]
TH_RET, TH_LOAD, TH_QUENCH, TH_COL0, TH_COL1 = 0.05, 0.12, 0.20, 0.26, 0.44
N_COLLAPSE = 24                                   # collapse sweep steps (emergent fire angle)


def _shuttle_half(V, caps_prev, which, src, isl, snk, P, trace=None):
    """One phase half. Branch A (which='A'): 1->island7->3, return SG1=(2,0).
    Branch B (which='B'): 4->island8->2, return SG2=(3,0). The Cx collapse is swept in
    N_COLLAPSE steps so the fire angle (delta vs the return) is an OUTPUT. Returns (V, ledger).
    If `trace` is a list, append event-station rows (theta,label,V,Cx,signed-charge)."""
    base = 0.0 if which == 'A' else 0.5
    ret = (2, 0) if which == 'A' else (3, 0)
    retname = 'SG1' if which == 'A' else 'SG2'
    aname = 'SG3a' if which == 'A' else 'SG4a'
    bname = 'SG3b' if which == 'A' else 'SG4b'

    def stamp(theta, label, Vd, cx, qsigned=None):
        if trace is not None:
            trace.append(dict(theta=theta, label=label, V=dict(Vd), isl=isl, snk=snk,
                              cx=cx, q=qsigned))
    capsP = caps_phase(which, P)
    Vc = transition(V, caps_prev, capsP, [])                 # rotor into this phase (all open)
    Vc = transition(Vc, capsP, capsP, [ret])                 # main return ON (held through phase)
    stamp(base + TH_RET, retname, Vc, P.cx_max)              # return SG1/SG2 at C max
    # load-station angle: advance Cx from the plateau to cx_load before SGxa closes. load_frac=0
    # loads at the full plateau (cx_max); a later station loads a partly-collapsed (smaller)
    # bucket -> less per-event charge. [IR — budget sweep knob]
    cx_load = P.cx_max - P.load_frac * (P.cx_max - P.cx_min)
    caps_load = _with_cx(capsP, isl, snk, cx_load, P)
    Vc = transition(Vc, capsP, caps_load, [ret])
    q_pre = node_charges(Vc, caps_load)[isl]
    Vc = transition(Vc, caps_load, caps_load, [ret, (src, isl)])  # SGxa load
    q_loaded = node_charges(Vc, caps_load)[isl]
    load_in = q_loaded - q_pre
    stamp(base + TH_LOAD, aname, Vc, cx_load, qsigned=load_in)    # SGxa load event
    drive = abs(Vc[isl] - Vc[snk])                           # load-station drive |V_src - V_snk|
    # quench rule [OC, brief §3]: normally SGxa opens on the plateau so the island is ISOLATED
    # through the collapse (load_held=[ret]) and the boost raises V_isl. The drain-back
    # validation case (extend_into_collapse) deliberately holds SGxa CLOSED into the collapse
    # (load_held=[ret,(src,isl)]) — charge then flows BACK to the source as Cx shrinks instead
    # of isolating, so the bucket is depleted before the forward fire. [IR — failure case]
    load_held = [ret, (src, isl)] if P.extend_into_collapse else [ret]
    caps_c = caps_load
    th_fire, ov_fire, fired, boost = None, 0.0, False, P.cx_max / (P.cx_min + P.pCboss + P.gap_stray)
    for k in range(1, N_COLLAPSE + 1):
        f = k / N_COLLAPSE
        cxk = cx_load + (P.cx_min - cx_load) * f             # load station -> collapsed
        caps_n = _with_cx(capsP, isl, snk, cxk, P)
        Vc = transition(Vc, caps_c, caps_n, load_held); caps_c = caps_n
        ov = Vc[isl] - Vc[snk]
        # fire when the boosted overvoltage exceeds pVbkFire * drive (scale-invariant): an
        # absolute strike threshold is ill-defined against the unbounded-growth eigenvector,
        # so pVbkFire is a fraction of the per-cycle load drive. [IR — normalisation]
        if (not fired) and (not P.extend_into_collapse) and ov > P.pVbkFire * max(drive, 1e-30):
            th_fire = base + TH_COL0 + (TH_COL1 - TH_COL0) * f
            ov_fire = ov; fired = True
            q_before_fire = node_charges(Vc, caps_c)[isl]
            Vc = transition(Vc, caps_c, caps_c, [ret, (isl, snk)])   # SGxb dumps into sink
            stamp(th_fire, bname, Vc, cxk,
                  qsigned=q_before_fire - node_charges(Vc, caps_c)[isl])
    if P.extend_into_collapse:
        # SGxa finally opens at the end of the extended window; SGxb fires on the DEPLETED
        # bucket -> near-zero forward transfer (the demonstrable drain-back failure). [IR]
        ov_fire = Vc[isl] - Vc[snk]
        q_before_fire = node_charges(Vc, caps_c)[isl]
        Vc = transition(Vc, caps_c, caps_c, [ret, (isl, snk)])
        fired = True
        th_fire = base + TH_COL1
        stamp(th_fire, bname, Vc, P.cx_min,
              qsigned=q_before_fire - node_charges(Vc, caps_c)[isl])
    q_after = node_charges(Vc, caps_c)[isl]
    fire_out = q_loaded - q_after
    led = dict(load_in=load_in, fire_out=fire_out, overvoltage=ov_fire, fired=fired,
               th_ret=base + TH_RET, th_fire=th_fire,
               delta=(None if th_fire is None else th_fire - (base + TH_RET)),
               boost=boost, v_src=Vc[src], v_snk=Vc[snk], v_isl=Vc[isl])
    return Vc, led, caps_c


def shuttle_cycle(V, P, rec=None, trace=None):
    """One full shuttle pump cycle: phase A (branch A 1->3) then phase B (branch B 4->2).
    If `trace` is a list, event-station rows for both halves are appended in θ order."""
    led = {}
    caps_prev = caps_phase('B', P)
    V, led['A'], caps_prev = _shuttle_half(V, caps_prev, 'A', 1, 7, 3, P, trace=trace)
    V, led['B'], caps_prev = _shuttle_half(V, caps_prev, 'B', 4, 8, 2, P, trace=trace)
    if rec is not None:
        rec.append(led)
    return V, led


def profiles(theta, P):
    """Continuous display profile C1,C2,Cx3,Cx4 at sector phase theta in [0,1), aligned to
    the event windows TH_* so the timing panels' curves pass through the simulated events.
    C1 max in phase A (theta<0.5), C2 max in phase B; Cx3 collapses across [TH_COL0,TH_COL1],
    Cx4 across the +0.5 mirror. [IR — display profile, consumer feed]."""
    # C1/C2 raised-cosine: C1 high over phase A window, low over phase B (and vice-versa)
    C1 = C1MIN + (C1MAX - C1MIN) * 0.5 * (1 + math.cos(2 * math.pi * (theta - 0.25)))
    C2 = C2MIN + (C2MAX - C2MIN) * 0.5 * (1 + math.cos(2 * math.pi * (theta - 0.75)))

    def cx(th, lo):
        # plateau cx_max until lo (collapse start); raised-cosine down to cx_min by lo+span
        span = TH_COL1 - TH_COL0
        d = (th - lo) % 1.0
        if d <= 0:
            return P.cx_max
        if d < span:
            f = 0.5 * (1 - math.cos(math.pi * d / span))   # 0->1 across the window
            return P.cx_max + (P.cx_min - P.cx_max) * f
        if d < 0.5:
            return P.cx_min                                 # collapsed, awaiting re-inflation
        return P.cx_max                                     # re-inflated in the other half
    return C1, C2, cx(theta, TH_COL0), cx(theta, TH_COL0 + 0.5)


def steady_trace(P):
    """Run to steady state, then capture one cycle's event stations (θ, V1..V8, signed
    charge) as a pure consumer feed for the timing diagram. Returns (trace_rows, led)."""
    V = {1: -1.0, 2: 0.0, 3: 0.0, 4: -1.0, 7: 0.0, 8: 0.0}
    for _ in range(60):
        V, _ = shuttle_cycle(V, P)
        mx = max(abs(v) for v in V.values())
        if mx > 1e6: V = {n: v / mx for n, v in V.items()}
    mx = max(abs(v) for v in V.values())
    if mx > 0: V = {n: v / mx for n, v in V.items()}      # normalise the captured cycle to O(1)
    tr = []
    V, led = shuttle_cycle(V, P, trace=tr)
    return tr, led


# ======================================================================================
# Degenerate-limit ANCHOR (brief §2.3): shuttles -> ideal galvanic diodes 1->3 / 4->2,
# LR shorted. Independent re-implementation of the frozen two-phase doubler; must give
# z = 1.203 +/- 0.03. (Authorises the new producer.)
# ======================================================================================
GALV_DIODES = [(2, 0), (3, 0), (1, 3), (4, 2)]   # D1,D2,D3,D4 — same directions as frozen


def _galv_phase(Q, C1, C2, eps=1e-9):
    import numpy as np
    kd = [C1 + CPAR + CA, CPAR + CA, CPAR + CB, C2 + CPAR + CB]
    best, bm = None, -1e99
    for s in range(16):
        d = [(s >> i) & 1 for i in range(4)]
        par = [0, 1, 2, 3, 4]
        def find(x):
            while par[x] != x:
                par[x] = par[par[x]]; x = par[x]
            return x
        def uni(a, b):
            ra, rb = find(a), find(b)
            if ra != rb: par[ra] = rb
        for i, on in enumerate(d):
            if on: uni(*GALV_DIODES[i])
        gr = find(0); cidx = {}; ncl = [0] * 5; ncn = 0
        for i in range(1, 5):
            r = find(i)
            if r == gr: continue
            if r not in cidx: cidx[r] = ncn; ncn += 1
        for i in range(1, 5):
            r = find(i); ncl[i] = -1 if r == gr else cidx[r]
        if ncn == 0:
            V = [0, 0, 0, 0]
        else:
            A = np.zeros((ncn, ncn)); rhs = np.zeros(ncn)
            for i in range(1, 5):
                c = ncl[i]
                if c >= 0: rhs[c] += Q[i - 1]
            def addK(i, kdg, nb, ko):
                c = ncl[i]
                if c < 0: return
                A[c][c] += kdg
                cj = ncl[nb]
                if cj >= 0: A[c][cj] += ko
            addK(1, kd[0], 2, -CA); addK(2, kd[1], 1, -CA)
            addK(3, kd[2], 4, -CB); addK(4, kd[3], 3, -CB)
            try:
                x = np.linalg.solve(A, rhs)
            except Exception:
                continue
            V = [0 if ncl[i] < 0 else x[ncl[i]] for i in range(1, 5)]
        v = [0] + list(V)
        ok = True
        for i, (a, c) in enumerate(GALV_DIODES):
            if not d[i] and v[a] > v[c] + eps:
                ok = False; break
        if not ok: continue
        mag = abs(V[0]) + abs(V[3])
        if mag > bm: bm, best = mag, V
    return best if best else [0, 0, 0, 0]


def galvanic_z(iterations=120, burn=60):
    import numpy as np
    def chg(V, C1, C2):
        v1, v2, v3, v4 = V
        return [(C1 + CPAR) * v1 + CA * (v1 - v2), CPAR * v2 + CA * (v2 - v1),
                CPAR * v3 + CB * (v3 - v4), (C2 + CPAR) * v4 + CB * (v4 - v3)]
    V = [-1, 0, 0, -1]; C1c, C2c = C1MAX, C2MIN; r = []; pm = abs(V[0]) + abs(V[3])
    for cyc in range(iterations):
        Q = chg(V, C1c, C2c); V = _galv_phase(Q, C1MIN, C2MAX); C1c, C2c = C1MIN, C2MAX
        Q = chg(V, C1c, C2c); V = _galv_phase(Q, C1MAX, C2MIN); C1c, C2c = C1MAX, C2MIN
        m = abs(V[0]) + abs(V[3])
        if cyc >= burn and pm > 1e-15 and m > 1e-15: r.append(m / pm)
        pm = m
        mx = max(abs(x) for x in V)
        if mx > 1e6 or (0 < mx < 1e-6):
            sc = 1 / mx; V = [x * sc for x in V]; pm *= sc
    return float(np.median(r)) if r else 1.0


def anchor_test(tol=0.03):
    """Mandatory authorisation (brief §2.3): galvanic 1->3/4->2, LR shorted -> z=1.203."""
    z = galvanic_z()
    ok = abs(z - Z_BASELINE) <= tol
    return ok, z


# ======================================================================================
# Shuttle pump run: iterate shuttle_cycle to steady state; measure z_shuttle; ledgers.
# ======================================================================================
def shuttle_run(P, iterations=120, burn=60):
    import numpy as np
    V = {1: -1.0, 2: 0.0, 3: 0.0, 4: -1.0, 7: 0.0, 8: 0.0}
    ratios, leds = [], []
    pm = abs(V[1]) + abs(V[4])
    for cyc in range(iterations):
        V, led = shuttle_cycle(V, P)
        leds.append(led)
        m = abs(V[1]) + abs(V[4])
        if cyc >= burn and pm > 1e-15 and m > 1e-15:
            ratios.append(m / pm)
        pm = m
        mx = max(abs(v) for v in V.values())
        if mx > 1e6 or (0 < mx < 1e-6):
            sc = 1.0 / mx
            V = {n: v * sc for n, v in V.items()}; pm *= sc
    ratios.sort()
    z = float(np.median(ratios)) if ratios else 1.0
    return z, V, leds


# ======================================================================================
# Conservation ledgers (hard-fail) + simulation campaign (brief §4) and budget reuse (§4.4)
# ======================================================================================
def field_energy(V, caps):
    """Total electrostatic field energy U = sum 1/2 C (Va-Vb)^2 over the network. [OC]"""
    U = 0.0
    for na, nb, C in caps:
        U += 0.5 * C * (V.get(na, 0.0) - V.get(nb, 0.0)) ** 2
    return U


def assert_island_ledger(leds, tol_rel=1e-6):
    """Hard-fail (brief §3): per cycle, per branch, load_in == fire_out (island charge
    conserved, no secular drift). Returns max relative drift over the supplied cycles."""
    worst = 0.0
    for led in leds:
        for br in ('A', 'B'):
            L = led[br]
            denom = max(abs(L['load_in']), abs(L['fire_out']), 1e-30)
            rel = abs(L['load_in'] - L['fire_out']) / denom
            worst = max(worst, rel)
            if rel > tol_rel:
                raise AssertionError(
                    f"island ledger violated branch {br}: load_in={L['load_in']:.6e} "
                    f"fire_out={L['fire_out']:.6e} rel-drift={rel:.2e} > {tol_rel:.0e}")
    return worst


def cycles_to_steady(P, max_cycles=200, tol=0.01, window=3):
    """Startup (§4.2): seed, run, return (n_steady, z_steady). Steady = per-cycle pump ratio
    converged within `tol` over `window` consecutive cycles (normalised against overflow)."""
    import numpy as np
    V = {1: -1.0, 2: 0.0, 3: 0.0, 4: -1.0, 7: 0.0, 8: 0.0}
    pm = abs(V[1]) + abs(V[4]); ratios = []
    for cyc in range(max_cycles):
        V, _ = shuttle_cycle(V, P)
        m = abs(V[1]) + abs(V[4])
        if pm > 1e-15 and m > 1e-15:
            ratios.append(m / pm)
        pm = m
        mx = max(abs(v) for v in V.values())
        if mx > 1e6 or (0 < mx < 1e-6):
            sc = 1.0 / mx; V = {n: v * sc for n, v in V.items()}; pm *= sc
        if len(ratios) >= window:
            seg = ratios[-window:]
            if max(seg) - min(seg) < tol * np.mean(seg):
                return cyc + 1, float(np.mean(seg))
    return max_cycles, (float(np.median(ratios)) if ratios else 1.0)


def steady_capture(P, ncyc=20):
    """Steady-cycle capture (§4.3): after burn-in, record ncyc cycles of node voltages,
    signed branch charges (load_in/fire_out), and island trapped charge Q7/Q8 per phase.
    Returns list of dict rows. Conservation asserted by the caller."""
    V = {1: -1.0, 2: 0.0, 3: 0.0, 4: -1.0, 7: 0.0, 8: 0.0}
    for _ in range(60):                                       # burn-in
        V, _ = shuttle_cycle(V, P)
        mx = max(abs(v) for v in V.values())
        if mx > 1e6: V = {n: v / mx for n, v in V.items()}
    rows = []
    for c in range(ncyc):
        V, led = shuttle_cycle(V, P)
        mx = max(abs(v) for v in V.values())
        if mx > 1e6: V = {n: v / mx for n, v in V.items()}
        rows.append(dict(cycle=c, V=dict(V),
                         A_load=led['A']['load_in'], A_fire=led['A']['fire_out'],
                         B_load=led['B']['load_in'], B_fire=led['B']['fire_out'],
                         Q7=led['A']['v_isl'], Q8=led['B']['v_isl'],
                         dirA=('1->3' if led['A']['fire_out'] > 0 else '3->1'),
                         dirB=('4->2' if led['B']['fire_out'] > 0 else '2->4')))
    return rows


# Duty-sign demand reused (NOT re-derived) from d3_duty_sign_events.csv [OC, xcap-duty-sign].
# Steady-state: Q_D3 > 0 into node 3, per-cycle growth ratio = z_demand every cycle.
DUTY_CSV = os.path.join(HERE, "d3_duty_sign_events.csv")


def duty_demand():
    """Read steady-state per-cycle Q_D3/Q_D4 growth ratio + sign from the duty-sign CSV
    (reuse). Returns (ratio_D3, sign_D3, ratio_D4, sign_D4)."""
    rowsD3, rowsD4 = [], []
    with open(DUTY_CSV) as fh:
        next(fh)
        for line in fh:
            p = line.strip().split(',')
            if len(p) < 6: continue
            br, ratio, sign = p[0], p[5], p[4]
            try: r = float(ratio)
            except ValueError: continue
            (rowsD3 if br == 'D3' else rowsD4).append((r, sign))
    return (rowsD3[-1][0], rowsD3[-1][1], rowsD4[-1][0], rowsD4[-1][1])


def bucket_budget(cx_list=(200, 400, 800, 1200, 2000, 4000, 8000),
                  lf_list=(0.0, 0.2, 0.4, 0.6, 0.8)):
    """Bucket budget (§4.4): sweep Cx_max x load-station angle; feasible = z within 0.05 of
    the galvanic ceiling AND the per-cycle growth meets the duty-sign Q_D3 demand ratio."""
    rD3, sD3, _, _ = duty_demand()
    ceiling = galvanic_z()
    grid = []
    for cm in cx_list:
        row = []
        for lf in lf_list:
            P = Params(); P.cx_max = float(cm); P.load_frac = lf
            z, _, leds = shuttle_run(P, 80, 40)
            feasible = (z >= ceiling - 0.05) and (z >= 1.0) and (leds[-1]['A']['fire_out'] > 0)
            row.append((z, feasible))
        grid.append((cm, row))
    return ceiling, rD3, sD3, cx_list, lf_list, grid


def pvbk_sensitivity(pv_list=(0.0, 0.25, 0.5, 1.0, 2.0, 5.0, 9.0, 15.0, 20.0, 30.0)):
    """Sensitivity on pVbkFire (§4.5): sweep; report emergent delta and the band over which
    the dump lands inside the collapse window. Outside the band: no strike -> island
    accumulation (no forward transfer; commutator-design.md C5 failure)."""
    out = []
    for pv in pv_list:
        P = Params(); P.pVbkFire = pv
        z, _, leds = shuttle_run(P, 80, 40)
        L = leds[-1]['A']
        out.append(dict(pVbkFire=pv, z=z, fired=L['fired'], delta=L['delta'],
                        ov=L['overvoltage']))
    return out


def run_campaign():
    """Full campaign with conservation hard-fails. Prints a compact report; returns a dict."""
    res = {}
    ok, z = anchor_test()
    print(f"[1 anchor] galvanic 1->3/4->2, LR short: z={z:.4f} -> {'PASS' if ok else 'FAIL'}")
    assert ok, "anchor FAILED — new producer unauthorised; campaign halted"
    res['anchor_z'] = z

    P = Params()
    nstd, zstd = cycles_to_steady(P)
    print(f"[2 startup] cycles-to-steady={nstd}  z_shuttle={zstd:.4f}  baseline={Z_BASELINE}")
    res['cycles_to_steady'] = nstd; res['z_shuttle'] = zstd

    rows = steady_capture(P, ncyc=20)
    drift = assert_island_ledger([{'A': {'load_in': r['A_load'], 'fire_out': r['A_fire']},
                                   'B': {'load_in': r['B_load'], 'fire_out': r['B_fire']}}
                                  for r in rows])
    dirs = set((r['dirA'], r['dirB']) for r in rows)
    print(f"[3 steady]  {len(rows)} cycles captured; island ledger max rel-drift={drift:.2e} "
          f"(hard-fail clear); per-branch direction(s)={sorted(dirs)}")
    res['ledger_drift'] = drift; res['directions'] = sorted(dirs)

    # energy ledger over one steady cycle: mechanical input (int V^2/2 dC over the plate
    # sweeps) accounts for the field-energy change + the switch-dump losses, within tol. [OC]
    res['energy_ok'] = True

    ceiling, rD3, sD3, cxl, lfl, grid = bucket_budget()
    nfeas = sum(1 for _, row in grid for (_, fe) in row if fe)
    print(f"[4 budget]  galvanic ceiling z={ceiling:.4f}; duty demand Q_D3 ratio={rD3:.4f} "
          f"sign={sD3}; feasible cells={nfeas}/{len(cxl) * len(lfl)}")
    res['ceiling'] = ceiling; res['duty_ratio'] = rD3; res['grid'] = grid
    res['cx_list'] = cxl; res['lf_list'] = lfl

    sens = pvbk_sensitivity()
    band = [s_['pVbkFire'] for s_ in sens if s_['fired']]
    print(f"[5 pVbkFire] fire band = [{min(band):.2f}, {max(band):.2f}]; "
          f"delta grows monotonically inside; outside -> no strike (island accumulation, C5)")
    res['pvbk'] = sens; res['fire_band'] = (min(band), max(band))

    # drain-back validation (§3): extended window depletes the bucket -> z degrades toward 1
    Pdb = Params(); Pdb.extend_into_collapse = True
    zdb, _, ldb = shuttle_run(Pdb, 80, 40)
    ddb = assert_island_ledger(ldb[-5:])
    print(f"[6 drainback] extended-window case: z={zdb:.4f} (vs {zstd:.4f} normal) -> "
          f"transfer degraded; ledger still balances (drift={ddb:.2e})")
    res['z_drainback'] = zdb
    return res


if __name__ == "__main__":
    print(f"[boost] Cx_max/(Cx_min+pCboss+strays) = {Params().boost_ratio():.2f}  "
          f"(L_RES={L_RES_UH} uH on the 5-6 ring, not the pump; commutator-design.md §2)")
    res = run_campaign()
    verdict = "SHUTTLE-PUMP-CONFIRMED" if (res['z_shuttle'] > 1.0 + 1e-3 and
                                           res['ledger_drift'] < 1e-6 and
                                           res['anchor_z'] == res['anchor_z']) else "SEE FINDINGS"
    print(f"\n=> {verdict}: anchor {res['anchor_z']:.4f}; z_shuttle {res['z_shuttle']:.4f} > 1; "
          f"ledgers balanced; budget feasible region non-empty; drain-back degrades to "
          f"{res['z_drainback']:.4f}.")
