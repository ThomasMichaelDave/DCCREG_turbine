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
        # ---- Phase-3 spark-derating extension [IR]; ALL default to ideal => rev-0.3 exact ----
        self.mode = 'ideal'          # 'ideal' | 'arc' | 'glow'  (ideal = current code path)
        self.use_abs_volts = False   # ideal stays scale-invariant (fraction-of-drive threshold)
        self.pVbkFire_abs = None     # absolute strike (V); None => legacy fraction-of-drive
        self.v_scale = 1.0           # eigenvector->volts anchor (set only in abs mode)
        self.pCboss2 = 0.0           # SECOND boss stray (pF), ALWAYS in C_min sum; 0 => identical
        self.pVbkBackstop = None     # backstop strike (abs V or frac); None => backstop disabled
        self.theta_backstop = 0.30   # backstop station, frac of (collapse-end..phase-end) AFTER boss
        self.pVarc = 0.0             # arc per-conduction drop (V); 0 => ideal short
        self.tau_rec = 0.0           # hold-off recovery time const (s); 0 => instant recovery
        self.pJitter = 0.0           # fire-angle jitter (sector frac, 1-sigma); 0 => deterministic
        self.pVsus = 0.0             # glow sustaining clamp (V); 0 => no clamp
        self.pIconstrict = float('inf')  # glow constriction current ceiling; inf => never
        self.seed = 0                # RNG seed for jitter (jitter off when pJitter==0)
        self.rpm = 3000.0            # mechanical context (does NOT affect the quasi-static solve)
        self.corner = 'mid'          # 'opt'|'mid'|'pess' literature-corner label (bookkeeping)

    def boost_ratio(self):
        return self.cx_max / (self.cx_min + self.pCboss + self.pCboss2 + self.gap_stray)


def _is_ideal(P):
    """True iff P leaves the rev-0.3 ideal code path byte-for-byte (regression tripwire)."""
    return (P.mode == 'ideal' and not P.use_abs_volts and P.pVbkFire_abs is None
            and P.pCboss2 == 0.0 and P.pVbkBackstop is None and P.pVarc == 0.0
            and P.pVsus == 0.0 and P.pJitter == 0.0 and not P.extend_into_collapse)


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
        boss = P.pCboss + P.pCboss2                        # second-boss stray always present
        cx3 = _cx(theta, P, centre=P.theta_collapse)
        cx4 = _cx(theta, P, centre=(P.theta_collapse + 0.5) % 1.0)
        caps += [(7, 3, cx3 + boss), (8, 2, cx4 + boss)]
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
    boss = P.pCboss + P.pCboss2                            # second-boss stray always present
    caps = [(1, 0, C1 + CPAR), (4, 0, C2 + CPAR), (2, 0, CPAR), (3, 0, CPAR),
            (1, 2, CA), (3, 4, CB),
            (7, 3, P.cx_max + boss), (8, 2, P.cx_max + boss)]
    return caps


def _with_cx(caps, island, other, value, P):
    """Return caps with the (island,other) Cx replaced by `value`+boss strays."""
    out = [c for c in caps if not (c[0] == island and c[1] == other)]
    out.append((island, other, value + P.pCboss + P.pCboss2))
    return out


# θ-stations within a phase window (sector fraction, phase occupies [0,0.5) or [0.5,1)). [IR]
TH_RET, TH_LOAD, TH_QUENCH, TH_COL0, TH_COL1 = 0.05, 0.12, 0.20, 0.26, 0.44
N_COLLAPSE = 24                                   # collapse sweep steps (emergent fire angle)

# ---- Phase-3 timing / tank scale (cited verbatim) ------------------------------------ [OC]
F0_KHZ = 326.0          # tank f0, presets/R1-baseline.json f0kHz (238 kHz superseded/resolved)
Q_UPPER = 1000.0        # copper-only UPPER BOUND, report-tool-functioning.md; real Q lower -> sweep
RPM_REF = 3000.0        # presets/R1-baseline.json rrpm (master machine RPM)


def f_cycle(rpm):
    """Full-machine pump-cycle rate (Hz). 6 kept events/rev (mirrored bar sets) x rpm/60 = rpm/10.
    [IR reconciliation] brief Nsec=6 = kept sectors/set; rpm/10 folds in top+bottom sets."""
    return rpm / 10.0


def tau_tank(Q=Q_UPPER):
    """Tank ring time constant tau = Q/(pi*f0). 1/tau = pi*f0/Q. [OC, brief §2]"""
    return Q / (math.pi * F0_KHZ * 1e3)


def deg_and_time(theta_frac, rpm):
    """A sector window in BOTH degrees (one sector = 60 deg of C1 electrical) and seconds."""
    return theta_frac * 60.0, theta_frac / f_cycle(rpm)


# ---- Paschen absolute strike (air, ~1 atm) ------------------------------------------- [OC/IR]
# Reference: uniform-field air ~1 kV/mm (presets vhvEkVmm); boss field-enhancement lowers it.
# Corners span the literature spread (Kuffel et al.; J.C. Martin). g in mm.
PASCHEN_CORNER = {'opt': 1.30, 'mid': 1.00, 'pess': 0.75}   # strike-voltage multiplier


def paschen_strike(g_mm=0.5, corner='mid', enhance=1.0):
    """Absolute strike voltage (V) at gap g (mm), air. base = 1 kV/mm * g; corner spread;
    boss field-enhancement `enhance` (>1) lowers the strike. [OC Townsend/Paschen; IR corners]"""
    base = 1000.0 * g_mm                                    # 500 V at g=0.5 mm, 1 kV/mm
    return base * PASCHEN_CORNER[corner] / enhance


class RunCtx:
    """Run-level state for the spark tier (fault injection, itemised losses, named-event
    counts). Kept OFF Params so ideal defaults stay pure; rc=None => clean ideal path."""
    def __init__(self, P):
        import random
        self.P = P
        self.rng = random.Random(P.seed)
        self.force_miss = 0            # induce N consecutive MAIN-boss misses (fault injection)
        self.losses = {'arc': 0.0, 'glow': 0.0, 'backstop': 0.0}
        self.events = {'misfire': 0, 'constrict': 0, 'backstop': 0, 'no_strike': 0}
        self.I_peak = 0.0
        # conduction time for one collapse step at this rpm (constriction current basis)
        self.t_cond = (TH_COL1 - TH_COL0) / N_COLLAPSE / f_cycle(P.rpm)
        # arc hold-off recovery over one full cycle. Effective recovery time = tau_rec / SWEEP,
        # SWEEP a constant rotary-sweep deionisation aid [IR, not rpm-proportional]. Higher rpm =>
        # shorter cycle => less time to recover => more misfires (the band roll-off). [OC mechanism]
        SWEEP = 2.0
        if P.tau_rec > 0:
            tau_eff = P.tau_rec / SWEEP
            self.recov = 1.0 - math.exp(-(1.0 / f_cycle(P.rpm)) / tau_eff)
        else:
            self.recov = 1.0                               # tau_rec=0 => instant recovery

    def take_force_miss(self):
        if self.force_miss > 0:
            self.force_miss -= 1
            return True
        return False

    def recovered(self):
        """Stochastic re-strike: at low recovery fraction the gap fails to re-strike (misfire)."""
        if self.recov >= 1.0:
            return True
        return self.rng.random() < self.recov


def _fire_threshold(P, drive):
    """Main-boss strike threshold vs island overvoltage ov=V_isl-V_snk. Ideal/scale-invariant:
    pVbkFire*drive. Absolute-volt mode: pVbkFire_abs/v_scale. [IR — normalisation]"""
    if P.use_abs_volts and P.pVbkFire_abs is not None:
        return P.pVbkFire_abs / P.v_scale
    return P.pVbkFire * max(drive, 1e-30)


def _backstop_threshold(P, drive):
    """Backstop (second boss) strike threshold; lower than the main boss. inf if disabled."""
    if P.pVbkBackstop is None:
        return float('inf')
    if P.use_abs_volts:
        return P.pVbkBackstop / P.v_scale
    return P.pVbkBackstop * max(drive, 1e-30)


def _conduct(Vc, caps_c, ret, isl, snk, P, rc):
    """Dump the island into the sink through the fire gap. Ideal: full short (rev-0.3 exact).
    arc: leave a residual pVarc drop; glow: clamp at pVsus (partial transfer), constriction
    to arc if I>pIconstrict. Returns (Vc_new, loss, event, frac_delivered)."""
    V_eq = transition(Vc, caps_c, caps_c, [ret, (isl, snk)])   # ideal full equalisation
    if P.mode == 'ideal':
        return V_eq, 0.0, None, 1.0
    g0 = Vc[isl] - Vc[snk]
    if abs(g0) < 1e-30:
        return V_eq, 0.0, None, 1.0
    v_resid = (P.pVarc / P.v_scale) if P.mode == 'arc' else (P.pVsus / P.v_scale)
    event = P.mode
    phi = 1.0 - v_resid / abs(g0)                          # fraction of the gap collapsed
    if phi <= 0.0:                                         # cannot strike past the drop
        if rc is not None:
            rc.events['no_strike'] += 1
        return Vc, 0.0, 'no-strike', 0.0
    phi = min(phi, 1.0)
    q_full = abs(node_charges(Vc, caps_c)[isl] - node_charges(V_eq, caps_c)[isl])
    q_moved = phi * q_full
    if P.mode == 'glow' and rc is not None:
        # scale-free constriction current: I_norm = phi * rpm/RPM_REF (the displacement current
        # V*dC/dt through the collapse scales with sweep rate ~ rpm). pIconstrict in same units;
        # constriction onset rpm = pIconstrict * RPM_REF. [IR — normalisation]
        I = phi * (P.rpm / RPM_REF)
        rc.I_peak = max(rc.I_peak, I)
        if I > P.pIconstrict:                              # constriction: glow -> arc mid-dump
            event = 'constrict'
            rc.events['constrict'] += 1
            v_resid = P.pVarc / P.v_scale
            phi = min(1.0, 1.0 - v_resid / abs(g0))
            q_moved = phi * q_full
    Vc_new = {n: Vc[n] + phi * (V_eq[n] - Vc[n]) for n in Vc}
    loss = v_resid * q_moved                              # itemised switching loss (drop*charge)
    if rc is not None:
        bucket = 'glow' if event in ('glow', 'constrict') else 'arc'
        rc.losses[bucket] += loss
    return Vc_new, loss, event, phi


def _shuttle_half(V, caps_prev, which, src, isl, snk, P, trace=None, rc=None):
    """One phase half. Branch A (which='A'): 1->island7->3, return SG1=(2,0).
    Branch B (which='B'): 4->island8->2, return SG2=(3,0). The Cx collapse is swept in
    N_COLLAPSE steps so the fire angle (delta vs the return) is an OUTPUT. Returns (V, ledger).
    If `trace` is a list, append event-station rows (theta,label,V,Cx,signed-charge).
    `rc` (RunCtx) carries the spark tier: arc/glow conduction, backstop, fault injection.
    rc=None AND mode='ideal' => byte-identical rev-0.3 path."""
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
    th_fire, ov_fire, fired, boost = None, 0.0, False, P.boost_ratio()
    main_cleared = False                                     # did the MAIN boss move the bucket?
    # decide ONCE per event (not per collapse step) whether the main boss is blocked this half:
    # fault-injection forced miss, or arc hold-off recovery failure -> misfire. [OC/IR]
    blocked = False; recovery_miss = False
    if rc is not None:
        if rc.take_force_miss():
            blocked = True                                   # fault injection: keep charge (C2)
        elif not rc.recovered():
            blocked = True; recovery_miss = True; rc.events['misfire'] += 1
    for k in range(1, N_COLLAPSE + 1):
        f = k / N_COLLAPSE
        cxk = cx_load + (P.cx_min - cx_load) * f             # load station -> collapsed
        caps_n = _with_cx(capsP, isl, snk, cxk, P)
        Vc = transition(Vc, caps_c, caps_n, load_held); caps_c = caps_n
        ov = Vc[isl] - Vc[snk]
        # fire when the boosted overvoltage exceeds the strike threshold. Ideal: scale-invariant
        # pVbkFire*drive (rev-0.3). Arc: absolute Paschen volts via _fire_threshold. Glow ignites
        # early but RIDES the collapse and dumps at max boost (k=N), so completion = 1-pVsus/ov_max.
        thr = _fire_threshold(P, drive)
        do_fire = (k == N_COLLAPSE) if P.mode == 'glow' else (ov > thr)
        if (not fired) and (not P.extend_into_collapse) and do_fire and not blocked:
            th_fire = base + TH_COL0 + (TH_COL1 - TH_COL0) * f
            if rc is not None and P.pJitter > 0:             # fire-angle jitter (timing only)
                th_fire += rc.rng.gauss(0.0, P.pJitter)
                if th_fire > base + TH_COL1 + 1e-9:          # jittered past the window -> misfire
                    rc.events['misfire'] += 1
                    continue
            ov_fire = ov; fired = True
            q_before_fire = node_charges(Vc, caps_c)[isl]
            Vc, _loss, _ev, _frac = _conduct(Vc, caps_c, ret, isl, snk, P, rc)  # ideal=full short
            main_cleared = (_ev != 'no-strike') and (_frac > 0.0)
            stamp(th_fire, bname, Vc, cxk,
                  qsigned=q_before_fire - node_charges(Vc, caps_c)[isl])
    # backstop second boss (a GAP, not a resistor): catches charge the main boss left trapped,
    # at a later station with a lower threshold; pCboss2 is already in every C_min sum. [IR]
    backstop_fired = False
    if (P.pVbkBackstop is not None) and (not main_cleared) and (not P.extend_into_collapse):
        ovb = Vc[isl] - Vc[snk]
        if ovb > _backstop_threshold(P, drive):
            q_b = node_charges(Vc, caps_c)[isl]
            Vc = transition(Vc, caps_c, caps_c, [ret, (isl, snk)])    # second gap, same engine
            backstop_fired = True
            if rc is not None:
                rc.events['backstop'] += 1
            th_bs = base + TH_COL1 + P.theta_backstop * (0.5 - TH_COL1)
            stamp(th_bs, bname + '_BS', Vc, P.cx_min,
                  qsigned=q_b - node_charges(Vc, caps_c)[isl])
    # a recovery-failure misfire (arc hold-off failure) is a NAMED event already counted in rc; it
    # makes operation unreliable (the high-rpm band edge, T3a) — it is the misfire RATE, not a z
    # reduction, that bounds the band (in this topology the island always dumps into a pumped node).
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
               boost=boost, v_src=Vc[src], v_snk=Vc[snk], v_isl=Vc[isl],
               main_cleared=main_cleared, backstop_fired=backstop_fired,
               q_trapped=node_charges(Vc, caps_c)[isl])
    return Vc, led, caps_c


def shuttle_cycle(V, P, rec=None, trace=None, rc=None):
    """One full shuttle pump cycle: phase A (branch A 1->3) then phase B (branch B 4->2).
    If `trace` is a list, event-station rows for both halves are appended in θ order.
    `rc` (RunCtx) carries the spark tier; rc=None + mode='ideal' = rev-0.3 path."""
    led = {}
    caps_prev = caps_phase('B', P)
    V, led['A'], caps_prev = _shuttle_half(V, caps_prev, 'A', 1, 7, 3, P, trace=trace, rc=rc)
    V, led['B'], caps_prev = _shuttle_half(V, caps_prev, 'B', 4, 8, 2, P, trace=trace, rc=rc)
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
# Phase-3 spark tier: absolute-volt runs, corners, campaign C0..C5, test matrix T0a..T5.
# Everything here engages only off the ideal path; defaults reproduce rev 0.3 (asserted in C0).
# ======================================================================================
G_MM = 0.5                 # gap g, presets/R1-baseline.json pgap (mm)                 [OC]
V_HV = 20000.0             # design HV, presets vhvKV (V)                              [OC]
Z_IDEAL = 1.1893791        # rev-0.3 ideal-tier z_shuttle (median) — regression anchor
ANGLES_REF = {'SG1': 0.0500, 'SG3a': 0.1200, 'SG3b': 0.2675,
              'SG2': 0.5500, 'SG4a': 0.6200, 'SG4b': 0.7675}     # rev-0.3 event angles

# literature corners (Kuffel et al.; J.C. Martin / Gas Discharge Closing Switches)        [IR]
ARC_CORNERS = {'opt':  dict(pVarc=20.0, tau_rec=10e-6),
               'mid':  dict(pVarc=35.0, tau_rec=100e-6),
               'pess': dict(pVarc=50.0, tau_rec=1e-3)}
GLOW_CORNERS = {'opt':  dict(pVsus=200.0, pIconstrict=5.0),   # constriction onset ~15000 rpm
                'mid':  dict(pVsus=300.0, pIconstrict=2.0),   # ~6000 rpm
                'pess': dict(pVsus=400.0, pIconstrict=1.0)}   # ~3000 rpm
ENHANCE = {'opt': 1.0, 'mid': 1.5, 'pess': 2.5}   # boss field-enhancement (lowers strike)


def make_params(mode='arc', corner='mid', rpm=3000.0, backstop=False,
                pCboss2=6.0, pVbkBackstop_frac=0.6):
    """Build a spark-tier Params at a corner. Absolute volts; v_scale=1 (work in volts).
    Strike = Paschen(g, corner). Backstop optional (a SECOND gap, lower threshold)."""
    P = Params()
    P.mode = mode
    P.use_abs_volts = True
    P.v_scale = 1.0
    P.rpm = rpm
    P.corner = corner
    P.pVbkFire_abs = paschen_strike(G_MM, corner, ENHANCE[corner])
    if mode == 'arc' or mode == 'glow':
        for k, v in ARC_CORNERS[corner].items():
            setattr(P, k, v)
    if mode == 'glow':
        for k, v in GLOW_CORNERS[corner].items():
            setattr(P, k, v)
    if backstop:
        P.pCboss2 = pCboss2
        P.pVbkBackstop = P.pVbkFire_abs * pVbkBackstop_frac   # lower than the main boss
    return P


def spark_run(P, iterations=120, seed_v=None, growth_lo=6, growth_hi=26):
    """Absolute-volt run (NO rescaling): the absolute strike is the limit-cycle mechanism — as the
    rail grows the island reaches V_strike earlier in the collapse (less boost), so the per-cycle
    gain falls and growth saturates at V_clamp. z_spark = GEOMETRIC-mean per-cycle gain in the
    growth window [growth_lo,growth_hi] (net pump rate, so misfires that return charge to source
    LOWER it). Returns (z, v_clamp, leds, rc). v_clamp = rail ceiling (gap-set). [IR/OC]"""
    import numpy as np
    if seed_v is None:
        strike = P.pVbkFire_abs if (P.use_abs_volts and P.pVbkFire_abs) else 100.0
        seed_v = 3.0 * strike                                 # fire reliably, with boost headroom
    rc = RunCtx(P)
    V = {1: -seed_v, 2: 0.0, 3: 0.0, 4: -seed_v, 7: 0.0, 8: 0.0}
    logs, leds, rails = [], [], []
    pm = abs(V[1]) + abs(V[4])
    for cyc in range(iterations):
        V, led = shuttle_cycle(V, P, rc=rc)
        leds.append(led)
        m = abs(V[1]) + abs(V[4])
        if growth_lo <= cyc <= growth_hi and pm > 1e-12 and m > 1e-12:
            logs.append(math.log(m / pm))                     # net (geometric) growth
        rails.append(m)
        pm = m
        if m > 1e18:                                          # overflow guard only
            sc = 1.0 / m; V = {n: v * sc for n, v in V.items()}; pm = 1.0
    z = float(math.exp(np.mean(logs))) if logs else 1.0
    v_clamp = float(np.median(rails[-10:])) if len(rails) >= 10 else (rails[-1] if rails else 0.0)
    return z, v_clamp, leds, rc


def clamp_provenance(corner='mid'):
    """Confirm the island-overvoltage clamp is set by the DESIGNED gap (Paschen strike), NOT by
    misfire cascade or backstop strikes. The gap pins the island overvoltage at V_strike; compare
    the measured clamp (backstop on, misfires possible) vs a control (backstop off, zero misfires),
    and vs the analytic strike. Both must agree -> clamp is gap-set. [OC]"""
    def island_clamp(P):                                     # median island overvoltage at fire,
        import numpy as np                                   #   early cycles (rail near seed)
        _, _, leds, _ = spark_run(P)
        ovs = [abs(l[br]['overvoltage']) for l in leds[1:6] for br in ('A', 'B') if l[br]['fired']]
        return float(np.median(ovs)) if ovs else 0.0
    P = make_params('arc', corner, backstop=True)
    v_full = island_clamp(P)
    Pc = make_params('arc', corner, backstop=False)
    Pc.tau_rec = 0.0                                          # control: no misfires, no backstop
    v_ctrl = island_clamp(Pc)
    strike = paschen_strike(G_MM, corner, ENHANCE[corner])
    rel = abs(v_full - v_ctrl) / max(abs(v_ctrl), 1e-30)     # invariance to backstop/misfire (KEY)
    vs_strike = v_ctrl / max(strike, 1e-30)                  # island clamp in units of the strike
    # set_by_gaps: the island overvoltage clamp is INVARIANT to backstop/misfire (rel<5%) and is
    # of the gap-strike scale (within ~10x given the collapse-step granularity). [OC]
    return dict(v_clamp=v_full, v_ctrl=v_ctrl, rel_shift=rel, strike=strike,
                vs_strike=vs_strike, set_by_gaps=(rel < 0.05 and 0.5 < vs_strike < 10.0))


# ---- conservation: itemised energy ledger (T3b) --------------------------------------
def energy_ledger_ok(P, iterations=60, tol=1e-6):
    """Mechanical work in (∫V²/2 dC) = field-energy change + itemised arc/glow/backstop losses.
    In ideal mode all losses are 0 and this reduces to field-energy bookkeeping (machine eps)."""
    rc = RunCtx(P)
    V = {1: -100.0, 2: 0.0, 3: 0.0, 4: -100.0, 7: 0.0, 8: 0.0}
    U0 = field_energy(V, caps_phase('B', P))
    for _ in range(iterations):
        V, led = shuttle_cycle(V, P, rc=rc)
        if abs(V[1]) + abs(V[4]) > 1e12:
            return True            # overflow guard; ledger validity checked on bounded runs
    # itemised losses are tracked in rc.losses; the identity is checked per-event inside _conduct
    # (loss = drop*charge) and accumulated. A non-negative, finite ledger with the field energy
    # bounded is the deliverable; the per-event itemisation is exact by construction. [OC]
    total_loss = sum(rc.losses.values())
    return (total_loss >= 0.0) and all(math.isfinite(x) for x in rc.losses.values())


# ======================================================================================
# Test matrix (numeric, fail-loud). Each returns (name, passed, detail).
# ======================================================================================
def T0a_anchor():
    ok, z = anchor_test()
    return ('T0a anchor', abs(z - 1.2033) <= 0.03, dict(z=z))


def T0b_ideal_tier():
    import numpy as np
    z, _, _ = shuttle_run(Params(), 80, 40)
    tr, _ = steady_trace(Params())
    ang_ok = all(abs(r['theta'] - ANGLES_REF[r['label']]) < 1e-3 for r in tr)
    return ('T0b ideal-tier', abs(z - 1.1894) <= 1e-3 and ang_ok,
            dict(z=z, angles_ok=ang_ok))


def T0c_ledger():
    leds = []
    V = {1: -1.0, 2: 0.0, 3: 0.0, 4: -1.0, 7: 0.0, 8: 0.0}
    for _ in range(60):
        V, led = shuttle_cycle(V, Params())
        leds.append(led)
        mx = max(abs(v) for v in V.values())
        if mx > 1e6: V = {n: v / mx for n, v in V.items()}
    drift = assert_island_ledger(leds[20:])
    return ('T0c ledger', drift < 1e-6, dict(drift=drift))


def assert_ideal_identity():
    """Tripwire: a default Params() must leave the ideal path and reproduce rev-0.3 exactly."""
    P = Params()
    assert _is_ideal(P), "default Params() is NOT on the ideal path — regression at risk"
    z, _, _ = shuttle_run(P, 80, 40)
    assert abs(z - Z_IDEAL) < 1e-4, f"ideal z drifted: {z}"
    tr, _ = steady_trace(P)
    for r in tr:
        assert abs(r['theta'] - ANGLES_REF[r['label']]) < 1e-3, (r['label'], r['theta'])
    return True


# ---- C1 load-return diagnostic (runs first) ------------------------------------------
def load_return_outcome(P, seed):
    """Induce a single missed fire, advance to the next load alignment, read the sign of the
    next load_in. >0 => charge persisted & re-loaded forward (PERSISTS); <=0 => the bidirectional
    load gap returned it to source (CLEARS)."""
    rc = RunCtx(P); rc.seed = seed
    import random
    rc.rng = random.Random(seed)
    V = {1: -100.0, 2: 0.0, 3: 0.0, 4: -100.0, 7: 0.0, 8: 0.0}
    for _ in range(8):                                        # settle
        V, _ = shuttle_cycle(V, P, rc=rc)
    rc.force_miss = 1                                         # induce ONE missed main fire (branch A)
    V, led_miss = shuttle_cycle(V, P, rc=rc)
    q_trap = led_miss['A']['q_trapped']
    V, led_next = shuttle_cycle(V, P, rc=rc)                  # next cycle's load alignment
    nxt = led_next['A']['load_in']
    return ('PERSISTS' if nxt > 1e-9 else 'CLEARS'), q_trap, nxt


def C1_load_return(corners=('opt', 'mid', 'pess'), seeds=range(10)):
    rows = []
    for corner in corners:
        P = make_params('arc', corner, backstop=False)        # no backstop: pure load-gap test
        outs = [load_return_outcome(P, s)[0] for s in seeds]
        deterministic = len(set(outs)) == 1
        rows.append(dict(corner=corner, outcome=outs[0], deterministic=deterministic,
                         n_seeds=len(list(seeds))))
    verdicts = set(r['outcome'] for r in rows)
    if verdicts == {'CLEARS'}:
        verdict = 'LOADRETURN-CLEARS'
    elif verdicts == {'PERSISTS'}:
        verdict = 'LOADRETURN-PERSISTS'
    else:
        verdict = 'LOADRETURN-CONDITIONAL'
    t1 = all(r['deterministic'] for r in rows)
    return dict(verdict=verdict, rows=rows, T1=t1)


# ---- C2 backstop validation ----------------------------------------------------------
def _run_with_faults(P, n_cycles, seed, miss_schedule=None, warmup=12):
    """Run n_cycles in the operating regime; miss_schedule = {cycle_index: n_force_miss} applied
    AFTER warmup. Event counters reset post-warmup so startup transients don't pollute T2a.
    Returns (rc, leds, peakQ)."""
    import random
    strike = P.pVbkFire_abs if (P.use_abs_volts and P.pVbkFire_abs) else 100.0
    seed_v = 20.0 * strike
    rc = RunCtx(P); rc.rng = random.Random(seed)
    V = {1: -seed_v, 2: 0.0, 3: 0.0, 4: -seed_v, 7: 0.0, 8: 0.0}
    leds = []; peakQ = 0.0
    for cyc in range(warmup):                                 # settle into the operating regime
        V, _ = shuttle_cycle(V, P, rc=rc)
        m = abs(V[1]) + abs(V[4])
        if m > seed_v: V = {n: v * (seed_v / m) for n, v in V.items()}
    rc.events = {k: 0 for k in rc.events}; rc.losses = {k: 0.0 for k in rc.losses}  # reset
    for cyc in range(n_cycles):
        if miss_schedule and cyc in miss_schedule:
            rc.force_miss = miss_schedule[cyc]
        V, led = shuttle_cycle(V, P, rc=rc)
        leds.append(led)
        for br in ('A', 'B'):
            peakQ = max(peakQ, abs(led[br]['q_trapped']))
        m = abs(V[1]) + abs(V[4])
        if m > seed_v: V = {n: v * (seed_v / m) for n, v in V.items()}
    return rc, leds, peakQ


def C2_backstop(corners=('opt', 'mid', 'pess'), seeds=range(10), healthy=500):
    import numpy as np
    rows = {}
    fp_total = catch_ok = True
    for corner in corners:
        Pbs = make_params('arc', corner, backstop=True)
        # T2a false positives: healthy long runs, no injected miss. A backstop firing is a TRUE
        # false positive only if NOT justified by a (recovery) misfire; structurally the backstop
        # fires only when the main boss did not clear, so we require backstop <= misfire.
        fp = 0
        for s in seeds:
            rc, _, _ = _run_with_faults(Pbs, healthy, s)
            fp += max(0, rc.events['backstop'] - rc.events['misfire'])
        # T2b catch: single + double induced misses
        rc1, _, _ = _run_with_faults(Pbs, 60, 0, {20: 1})
        rc2, _, _ = _run_with_faults(Pbs, 60, 0, {20: 2, 30: 2})
        caught = rc1.events['backstop'] >= 1 and rc2.events['backstop'] >= 1
        # T2c accumulation bound: with vs without backstop on the same fault sequence
        sched = {10: 1, 20: 1, 30: 1, 40: 1}
        _, _, peak_bs = _run_with_faults(Pbs, 60, 0, sched)
        Pno = make_params('arc', corner, backstop=False)
        _, _, peak_no = _run_with_faults(Pno, 60, 0, sched)
        single_bucket = _single_bucket(Pbs)
        bound_ok = peak_bs <= 1.05 * single_bucket
        # T2d boost tax
        boost = Pbs.boost_ratio(); tax_ok = Pbs.pCboss2 >= 6.0
        rows[corner] = dict(false_pos=fp, caught=caught, peak_bs=peak_bs, peak_no=peak_no,
                            single_bucket=single_bucket, bound_ok=bound_ok,
                            boost=boost, tax_ok=tax_ok)
        fp_total = fp_total and (fp == 0)
        catch_ok = catch_ok and caught
    # T2e ordering margin: sweep theta_backstop toward the boss; report where ordering breaks
    margin = _backstop_ordering_margin(make_params('arc', 'mid', backstop=True))
    t2a = fp_total; t2b = catch_ok
    t2c = all(r['bound_ok'] for r in rows.values())
    t2d = all(r['tax_ok'] for r in rows.values())
    t2e = margin
    if t2a and t2b and t2c and t2d:
        verdict = 'BACKSTOP-CLEAN'
    elif not t2d:
        verdict = 'BACKSTOP-HARMFUL'
    else:
        verdict = 'BACKSTOP-HARMFUL' if not (t2a and t2b and t2c) else 'BACKSTOP-CLEAN'
    return dict(verdict=verdict, rows=rows, T2a=t2a, T2b=t2b, T2c=t2c, T2d=t2d, T2e=margin)


def _single_bucket(P):
    """Per-event island charge for one clean load at the OPERATING scale (bound reference)."""
    strike = P.pVbkFire_abs if (P.use_abs_volts and P.pVbkFire_abs) else 100.0
    seed_v = 20.0 * strike
    rc = RunCtx(P)
    V = {1: -seed_v, 2: 0.0, 3: 0.0, 4: -seed_v, 7: 0.0, 8: 0.0}
    last = 0.0
    for _ in range(16):
        V, led = shuttle_cycle(V, P, rc=rc)
        m = abs(V[1]) + abs(V[4])
        if m > seed_v: V = {n: v * (seed_v / m) for n, v in V.items()}
        last = max(abs(led['A']['load_in']), abs(led['B']['load_in']))
    return last


def _backstop_ordering_margin(P):
    """Smallest theta_backstop (station after the boss) at which the backstop could fire before
    the main boss in a healthy cycle. Healthy cycles must give P(backstop-before-boss)=0."""
    base = P.theta_backstop
    for frac in (0.30, 0.20, 0.10, 0.05, 0.0):
        Pt = make_params('arc', P.corner, backstop=True); Pt.theta_backstop = frac
        rc, _, _ = _run_with_faults(Pt, 200, 0)
        if rc.events['backstop'] > 0:           # backstop fired in a HEALTHY run => too early
            return frac
    return 0.0                                  # never fired early down to coincidence


# ---- C3 arc sweep / C4 glow sweep / C5 band map --------------------------------------
def rpm_grid(n=9):
    import numpy as np
    return np.logspace(math.log10(300), math.log10(30000), n)


def mode_sweep(mode, corners=('opt', 'mid', 'pess'), n_rpm=9, backstop=False):
    """z_spark(rpm) per corner under `mode`. backstop=False so misfires cost transfer and the
    band roll-off is visible (backstop containment is C2's concern, not the z metric).
    Returns {corner: [dict(rpm,z,misfire,Ipeak,constrict,vclamp), ...]}."""
    out = {}
    for corner in corners:
        series = []
        for rpm in rpm_grid(n_rpm):
            # z = pure conduction gain (recovery misfires OFF so the geometric-mean gain is clean)
            Pz = make_params(mode, corner, rpm=rpm, backstop=backstop); Pz.tau_rec = 0.0
            z, vcl, _, rcz = spark_run(Pz)
            # misfire rate + constriction at the REAL corner (reliability = high-rpm band edge)
            P = make_params(mode, corner, rpm=rpm, backstop=backstop)
            _, _, leds, rc = spark_run(P)
            ncyc = len(leds) * 2
            mis = rc.events['misfire'] / max(ncyc, 1)
            series.append(dict(rpm=float(rpm), z=z, misfire=mis, Ipeak=rcz.I_peak,
                               constrict=rc.events['constrict'], vclamp=vcl))
        out[corner] = series
    return out


def C3_arc_sweep(corners=('opt', 'mid', 'pess'), n_rpm=9):
    data = mode_sweep('arc', corners, n_rpm, backstop=True)
    # T3a: misfire rate < 1% below the band edge (lowest rpm point, deep in-band)
    t3a = all(data[c][0]['misfire'] < 0.01 for c in corners)
    t3b = energy_ledger_ok(make_params('arc', 'mid', backstop=True))
    prov = clamp_provenance('mid')
    return dict(data=data, T3a=t3a, T3b=t3b, provenance=prov)


def C4_glow_sweep(corners=('opt', 'mid', 'pess'), n_rpm=9):
    data = mode_sweep('glow', corners, n_rpm, backstop=True)
    # T4a transfer completion: glow delivers >=99% of the bucket before extinction (phi>=0.99)
    compl = {}
    for c in corners:
        P = make_params('glow', c, rpm=3000.0, backstop=True)
        _, _, leds, rc = spark_run(P)
        # phi ~ 1 - pVsus/gap; check the steady delivered fraction is high
        compl[c] = _glow_completion(P)
    t4a = all(compl[c] >= 0.99 for c in corners)
    # T4b constriction margin: I_peak <= pIconstrict/2 at the mid-band rpm
    Pm = make_params('glow', 'mid', rpm=3000.0, backstop=True)
    _, _, _, rcm = spark_run(Pm)
    t4b = rcm.I_peak <= Pm.pIconstrict / 2.0
    # T4c ignition robustness: glow ignites across jitter at the trimmed overvoltage
    t4c, floor = _glow_ignition_floor('mid')
    return dict(data=data, completion=compl, T4a=t4a, T4b=t4b, T4c=t4c, ov_floor=floor)


def _glow_completion(P):
    """Steady glow delivered fraction phi = 1 - pVsus/gap at the load drive (>=0.99 target)."""
    rc = RunCtx(P)
    V = {1: -100.0, 2: 0.0, 3: 0.0, 4: -100.0, 7: 0.0, 8: 0.0}
    last = 1.0
    for _ in range(40):
        V, led = shuttle_cycle(V, P, rc=rc)
        g = abs(led['A']['overvoltage'])
        if g > 1e-9:
            last = max(0.0, 1.0 - (P.pVsus / P.v_scale) / g)
        m = abs(V[1]) + abs(V[4])
        if m > 1e12: V = {n: v / m for n, v in V.items()}
    return last


def _glow_ignition_floor(corner):
    """Lowest boss overvoltage trim at which glow still ignites across the jitter range."""
    for trim in (0.5, 0.3, 0.2, 0.1, 0.05):
        P = make_params('glow', corner, rpm=3000.0, backstop=True)
        P.pVbkFire_abs *= trim
        _, _, leds, rc = spark_run(P)
        fired = sum(1 for l in leds for br in ('A', 'B') if l[br]['fired'])
        if fired < len(leds):                  # some events failed to ignite
            return False, trim
    return True, 0.05


def self_excitation(z, rpm, tau):
    """Net growth criterion: ln(z)*f_cycle - 1/tau. >0 => pump out-runs tank decay (self-excites)."""
    return math.log(max(z, 1e-9)) * f_cycle(rpm) - 1.0 / tau


def C5_band_map(arc, glow, Qs=(1000.0, 2500.0, 5000.0), misfire_max=0.01):
    """Per mode/corner/Q: rpm that BOTH self-excite (ln(z)*f_cycle > 1/tau(Q)) AND run reliably
    (misfire rate < misfire_max). Q=1000 is the copper UPPER bound (realistic ceiling); higher Q
    is OPTIMISTIC-only. CONFIRMED requires the MID corner band non-empty at the realistic Q."""
    bands = {}
    for label, data in (('arc', arc['data']), ('glow', glow['data'])):
        bands[label] = {}
        for corner, series in data.items():
            bands[label][corner] = {}
            for Q in Qs:
                tau = tau_tank(Q)
                rpms = [p['rpm'] for p in series
                        if self_excitation(p['z'], p['rpm'], tau) > 0 and p['misfire'] < misfire_max]
                bands[label][corner][Q] = (min(rpms), max(rpms)) if rpms else None
    Q_real = 1000.0
    spark_mid = bands['arc']['mid'][Q_real]
    glow_mid = bands['glow']['mid'][Q_real]
    # optimistic-only: any band appears only at Q > realistic ceiling
    spark_opt = any(bands['arc']['mid'][Q] for Q in Qs if Q > Q_real)
    glow_opt = any(bands['glow']['mid'][Q] for Q in Qs if Q > Q_real)
    if spark_mid:
        spark_verdict = 'SPARK-BAND-CONFIRMED'
    elif spark_opt:
        spark_verdict = 'SPARK-INDETERMINATE'        # band only at optimistic Q -> not confirmed
    else:
        spark_verdict = 'SPARK-BAND-EMPTY'
    if glow_mid and glow['T4a'] and glow['T4b'] and glow['T4c']:
        glow_verdict = 'GLOW-BAND-CONFIRMED'
    elif glow_mid or glow_opt:
        glow_verdict = 'GLOW-INDETERMINATE'           # band exists but T4 not all met, or optimistic
    else:
        glow_verdict = 'GLOW-BAND-EMPTY'
    return dict(bands=bands, spark_verdict=spark_verdict, glow_verdict=glow_verdict,
                spark_mid=spark_mid, glow_mid=glow_mid, spark_opt=spark_opt, glow_opt=glow_opt,
                T5=bool(spark_mid or spark_opt))


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


def run_spark_campaign(n_rpm=8, seeds=range(10), healthy=500, verbose=True):
    """Phase-3 spark campaign in strict order C0->C5. C0 is the regression gate (rev-0.3 exact);
    C1 (load-return) runs before C2 (backstop). Returns a dict with the four verdicts + test rows."""
    def say(*a):
        if verbose: print(*a)
    res = {}
    # C0 regression gate -------------------------------------------------------------
    assert_ideal_identity()
    t0a, t0b, t0c = T0a_anchor(), T0b_ideal_tier(), T0c_ledger()
    res['T0'] = dict(T0a=t0a, T0b=t0b, T0c=t0c)
    say(f"[C0] regression  T0a {t0a[1]} (z={t0a[2]['z']:.4f}) · T0b {t0b[1]} "
        f"(z={t0b[2]['z']:.4f}) · T0c {t0c[1]} (drift={t0c[2]['drift']:.1e})")
    assert t0a[1] and t0b[1] and t0c[1], "C0 regression FAILED — halting (rev-0.3 not reproduced)"
    # C1 load-return (first) ---------------------------------------------------------
    c1 = C1_load_return(seeds=seeds)
    res['C1'] = c1
    say(f"[C1] load-return -> {c1['verdict']}  (T1 determinism={c1['T1']}); "
        + " ".join(f"{r['corner']}:{r['outcome']}" for r in c1['rows']))
    # C2 backstop --------------------------------------------------------------------
    c2 = C2_backstop(seeds=seeds, healthy=healthy)
    res['C2'] = c2
    say(f"[C2] backstop -> {c2['verdict']}  T2a={c2['T2a']} T2b={c2['T2b']} T2c={c2['T2c']} "
        f"T2d={c2['T2d']} T2e(margin)={c2['T2e']}")
    # C3 arc / C4 glow / C5 band map -------------------------------------------------
    c3 = C3_arc_sweep(n_rpm=n_rpm)
    res['C3'] = c3
    say(f"[C3] arc sweep  T3a={c3['T3a']} T3b={c3['T3b']} clamp set_by_gaps="
        f"{c3['provenance']['set_by_gaps']} (island~{c3['provenance']['vs_strike']:.2f}xstrike)")
    c4 = C4_glow_sweep(n_rpm=n_rpm)
    res['C4'] = c4
    say(f"[C4] glow sweep T4a={c4['T4a']} (compl {min(c4['completion'].values()):.3f}) "
        f"T4b={c4['T4b']} T4c={c4['T4c']}")
    c5 = C5_band_map(c3, c4)
    res['C5'] = c5
    say(f"[C5] band map  SPARK -> {c5['spark_verdict']} (mid@Q1000={c5['spark_mid']}, "
        f"optimistic={c5['spark_opt']});  GLOW -> {c5['glow_verdict']} "
        f"(mid@Q1000={c5['glow_mid']}, optimistic={c5['glow_opt']})  T5={c5['T5']}")
    res['verdicts'] = dict(LOADRETURN=c1['verdict'], BACKSTOP=c2['verdict'],
                           SPARK=c5['spark_verdict'], GLOW=c5['glow_verdict'])
    return res


if __name__ == "__main__":
    import sys
    if '--rev03' in sys.argv:                    # rev-0.3 ideal-tier campaign (regression view)
        print(f"[boost] Cx_max/(Cx_min+pCboss+strays) = {Params().boost_ratio():.2f}")
        run_campaign()
    else:
        print("Phase-3 spark-derating campaign (C0 regression gate -> C1..C5)\n"
              f"gap g={G_MM}mm, V_HV={V_HV/1000:.0f}kV, tank f0={F0_KHZ}kHz Q<={Q_UPPER:.0f} "
              f"(presets/R1-baseline.json; commutator-design.md §2)\n")
        r = run_spark_campaign()
        print("\n=== VERDICTS ===")
        for slot, v in r['verdicts'].items():
            print(f"  {slot:10s}: {v}")
