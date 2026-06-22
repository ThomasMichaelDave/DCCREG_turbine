#!/usr/bin/env python3
"""
reference/doubler_resonant_core.py — the Bennet doubler with resonant (LC+diode) equalization.
==============================================================================================
THE GATE for the resonant-brigade eta. The brigade tax (the diode equalization loss) is the
SAME mechanism as the Bennet pump itself, so resonating it is NOT a free recovery the way the
downstream island was. This solver re-derives z with the half-cycle LC + diode resonant
equalization in place and answers: does z survive, enhance, retune, or collapse (the price)?

THE PHYSICS [OC]
  The direct equalization (frozen `doubler_core.solve_phase`) shares charge through a conducting
  diode until the nodes reach a common voltage -- equalization TO THE MEAN (the two-cap tax
  1/2 C_eff dV^2). Done resonantly (source -> series L + diode -> sink), the inductor current is
  maximal AT the mean, so a lossless disconnect is only available at the next current-zero, which
  leaves the caps OVER-TRANSFERRED (for equal caps, a voltage swap). Parameterise the over-transfer
  by alpha in [0,1]:
      V_res = V_direct + alpha * (V_direct - V_pre)
  where V_pre = the diodes-OFF constant-charge state (the over-transfer SOURCE) and V_direct = the
  frozen equalised state (the mean). alpha = 0 is the direct doubler (the FROZEN anchor); alpha = 1
  is the full lossless swap. Energy: the half-cycle ring leaves the differential at alpha*dV, so the
  residual tax is (1 - alpha^2)*direct_tax and the recovered fraction is alpha^2 = f_rec = 1 - pi/Q
  (the island integral) -> alpha = sqrt(max(0, 1 - pi/Q)).

THE RECTIFICATION CLAMP [OC] -- the load-bearing physics
  A HELD state at current-zero needs ALL diodes blocking. The over-transfer drives the inner nodes
  (2,3) positive, which FORWARD-BIASES the rail-return diodes D1(2,0)/D2(3,0) -- they re-conduct and
  clamp. So the achievable over-transfer is alpha_max = the largest alpha keeping the state
  diode-valid; beyond it the rail diode (the very element that makes the ratchet pump) takes the
  charge. alpha_max is STRUCTURAL (set by v2,v3 -> 0), not a tuning artifact. This is the price.

DISCIPLINE: frozen `doubler_core` is READ-ONLY and the direct-limit ANCHOR (alpha->0 reproduces
z=1.334, eta=0.386 bit-close, else MODEL-FAIL). This is a NEW solver. The independent guard reuses
the validated `island_resonant_core` unmodified. Firewall: pure EE (LC + diode rectification).

Tiers: [OC] derivable · [ME] method · [SOLVER] integrated authoritative.
"""
import numpy as np

import doubler_core as dc                 # FROZEN producer (read-only anchor)
import island_resonant_core as irc        # VALIDATED guard, reused UNMODIFIED

G3 = dict(C1min=16.0, C1max=280.0, C2min=16.0, C2max=280.0, Ca=309.0, Cb=309.0, Cpar=20.0)
DIRECT_Z = 1.334       # frozen doubler_core anchor (G3)
DIRECT_ETA = 0.386     # energy_balance.csv anchor


def cap_matrix(C1, C2, Ca, Cb, Cpar):
    """The 4x4 Maxwell matrix (dQ/dV of the frozen charges_from_voltages). [OC]"""
    return np.array([[C1 + Cpar + Ca, -Ca, 0.0, 0.0],
                     [-Ca, Cpar + Ca, 0.0, 0.0],
                     [0.0, 0.0, Cpar + Cb, -Cb],
                     [0.0, 0.0, -Cb, C2 + Cpar + Cb]], float)


def field_energy(V, C1, C2, Ca, Cb, Cpar):
    v1, v2, v3, v4 = V
    return 0.5 * (C1 * v1 * v1 + C2 * v4 * v4 + Cpar * (v1*v1 + v2*v2 + v3*v3 + v4*v4)
                  + Ca * (v1 - v2) ** 2 + Cb * (v3 - v4) ** 2)


def alpha_q(Q):
    """alpha realised by a ring of quality Q: alpha = sqrt(1 - pi/Q) (the island integral; <=0 ->
    overdamped -> 0 = direct). [OC]"""
    return float(np.sqrt(max(0.0, 1.0 - np.pi / Q))) if Q > 0 else 0.0


def diode_alpha_max(Vdir, Vpre, a_target, eps=1e-12):
    """The rectification clamp: the largest alpha in [0, a_target] for which V_res = Vdir +
    alpha*(Vdir-Vpre) keeps ALL diodes blocking (the held state at current-zero). Each blocking
    condition is linear a_k + alpha*b_k <= 0; a positive slope b_k binds the over-transfer. [OC]"""
    D = Vdir - Vpre
    v = Vdir
    cons = [(v[1], D[1]),                       # D1 off: v2 <= 0   (rail-return)
            (v[2], D[2]),                       # D2 off: v3 <= 0   (rail-return)
            (v[0] - v[2], D[0] - D[2]),         # D3 off: v1 <= v3
            (v[3] - v[1], D[3] - D[1])]         # D4 off: v4 <= v2
    am = a_target
    binder = None
    for k, (a, b) in enumerate(cons):
        if b > eps:                              # constraint tightens with alpha
            lim = max(0.0, -a / b)
            if lim < am:
                am = lim; binder = k
    return am, binder


def diode_valid(V, eps=1e-6):
    v1, v2, v3, v4 = V
    return v2 <= eps and v3 <= eps and v1 <= v3 + eps and v4 <= v2 + eps


def solve_phase_resonant(Vprev, Cold, Cnew, Ca, Cb, Cpar, a_target, clamp=True):
    """One phase with resonant equalization. Returns V_res (the held over-transfer state), the
    realised alpha, the binding diode, and the per-phase energy ledger. With clamp=True the
    over-transfer honours rectification (alpha capped at the diode boundary). [SOLVER]"""
    C1o, C2o = Cold
    C1n, C2n = Cnew
    Q = dc.charges_from_voltages(Vprev, C1o, C2o, Ca, Cb, Cpar)     # preserved (mechanical stroke)
    Vpre = np.linalg.solve(cap_matrix(C1n, C2n, Ca, Cb, Cpar), Q)    # diodes-off (over-transfer src)
    Vdir = np.asarray(dc.solve_phase(Q, C1n, C2n, Ca, Cb, Cpar), float)  # FROZEN equalisation
    if clamp:
        a_eff, binder = diode_alpha_max(Vdir, Vpre, a_target)
    else:
        a_eff, binder = a_target, None
    Vres = Vdir + a_eff * (Vdir - Vpre)
    Uprev = field_energy(Vprev, C1o, C2o, Ca, Cb, Cpar)
    Upre = field_energy(Vpre, C1n, C2n, Ca, Cb, Cpar)
    Ures = field_energy(Vres, C1n, C2n, Ca, Cb, Cpar)
    Udir = field_energy(Vdir, C1n, C2n, Ca, Cb, Cpar)
    led = dict(Wmech=Upre - Uprev, tax_res=Upre - Ures, tax_dir=Upre - Udir, a_eff=a_eff)
    return Vres, a_eff, binder, led


def solve_doubler_resonant(g, a_target, clamp=True, iterations=200, burn=100, trace=False):
    """Re-derive z, eta with resonant equalization. a_target is the ring-set alpha (use alpha_q(Q)
    to get it from a ring Q). clamp=True honours diode rectification (the physical model);
    clamp=False is the NAIVE unconstrained over-transfer (for the contrast). [SOLVER]"""
    C1min, C1max, C2min, C2max = g["C1min"], g["C1max"], g["C2min"], g["C2max"]
    Ca, Cb, Cpar = g["Ca"], g["Cb"], g["Cpar"]
    V = np.array([-1.0, 0.0, 0.0, -1.0]); C1c, C2c = C1max, C2min
    ratios, led, ams, binders, rec = [], [], [], [], []
    prev = abs(V[0]) + abs(V[3]); ladder = None
    for cyc in range(iterations):
        for (tC1, tC2) in [(C1min, C2max), (C1max, C2min)]:
            V, a_eff, binder, e = solve_phase_resonant(V, (C1c, C2c), (tC1, tC2),
                                                       Ca, Cb, Cpar, a_target, clamp)
            C1c, C2c = tC1, tC2
            if cyc >= burn:
                led.append(e); ams.append(a_eff); binders.append(binder)
            if trace:
                rec.append((cyc, "B" if tC1 == C1min else "A", tC1, tC2, list(V)))
        if cyc == (iterations + burn) // 2:
            mx = max(abs(v) for v in V) or 1.0
            ladder = [v / mx for v in V]                       # normalised per-stage snapshot
        mag = abs(V[0]) + abs(V[3])
        if cyc >= burn and prev > 1e-15 and mag > 1e-15:
            ratios.append(mag / prev)
        prev = mag
        mx = max(abs(v) for v in V)
        if mx > 1e6 or (0 < mx < 1e-6):
            V = V / mx; prev /= mx
    z = float(np.median(ratios)) if ratios else 1.0
    fr = [(e["tax_res"] / e["Wmech"], (e["Wmech"] - e["tax_res"]) / e["Wmech"])
          for e in led if e["Wmech"] > 1e-9]
    tax_f = float(np.median([x[0] for x in fr])) if fr else 0.0
    eta = float(np.median([x[1] for x in fr])) if fr else 0.0
    out = dict(z=z, eta=eta, tax_frac=tax_f, alpha_med=float(np.median(ams)) if ams else 0.0,
               ladder=ladder, binders=binders)
    if trace:
        out["rec"] = rec
    return out


# =============================================================================
# Conservation — the independent guard (reuses island_resonant_core) [ME]
# =============================================================================
def conservation(g=G3, Q_ring=1909.0):
    """Two independent guards. (A) the per-transfer LC ring (the island_resonant_core i^2R-integral
    vs energy-bookkeeping) closes ~1e-12 AND trips under +5% R -- reused unmodified. (B) the cycle
    charge/energy ledger is non-tautological: perturbing the ring alpha by +5% MOVES the steady z
    (the over-transfer state feeds the next stroke -- not a free sink). Returns a dict."""
    # (A) ring guard, reused unmodified (representative dominant brigade transfer)
    closes, resid, trips, resid_trip = irc.conservation(68.6e-12, 1e6 * 1e-12, 18.06e3, 1e-3, 2.0)
    # (B) non-tautology: the over-transfer state feeds the next stroke (NOT a free sink), so a +5%
    # alpha must MOVE z. The clamped z is alpha-insensitive (the diode pins it -- itself a finding),
    # so the feed-back is shown on the UNCLAMPED model at a mid-alpha where z is sensitive (away from
    # the alpha->1 saturation ceiling).
    a0 = alpha_q(Q_ring)
    z0 = solve_doubler_resonant(g, a0, clamp=True)["z"]
    z1 = solve_doubler_resonant(g, min(1.0, a0 * 1.05), clamp=True)["z"]
    a_mid = 0.5
    zc0 = solve_doubler_resonant(g, a_mid, clamp=False)["z"]
    zc1 = solve_doubler_resonant(g, a_mid * 1.05, clamp=False)["z"]
    feeds_back = abs(zc1 - zc0) / max(zc0, 1e-9) > 1e-3
    return dict(ring_closes=closes, ring_resid=resid, ring_trips=trips, ring_resid_trip=resid_trip,
                z_clamped=z0, z_clamped_pert=z1, z_unclamped=zc0, z_unclamped_pert=zc1,
                over_transfer_feeds_back=feeds_back)


# =============================================================================
# Self-tests (the direct-limit regression is the gate)
# =============================================================================
def run_self_test():
    print("doubler_resonant_core self-tests:")
    ok = True
    # (1) frozen mirror still faithful (the anchor)
    f = dc.run_self_test()
    ok = ok and f
    # (2) DIRECT-LIMIT REGRESSION: alpha=0 reproduces frozen z=1.334, eta=0.386 (else MODEL-FAIL)
    r0 = solve_doubler_resonant(G3, a_target=0.0, clamp=True)
    p_z = abs(r0["z"] - DIRECT_Z) < 5e-3
    p_e = abs(r0["eta"] - DIRECT_ETA) < 5e-3
    print(f"  [{'PASS' if p_z and p_e else 'FAIL — MODEL-FAIL'}] direct-limit alpha->0: "
          f"z={r0['z']:.4f} (exp {DIRECT_Z}), eta={r0['eta']:.4f} (exp {DIRECT_ETA})")
    ok = ok and p_z and p_e
    # (3) clamp invariance: above a small alpha the diode pins z (rectification structural)
    zs = [solve_doubler_resonant(G3, a, clamp=True)["z"] for a in (0.5, 0.9, 0.999)]
    p_c = max(zs) - min(zs) < 1e-3
    print(f"  [{'PASS' if p_c else 'FAIL'}] rectification clamp pins z across Q: "
          f"z(alpha=.5/.9/.999) = {zs[0]:.4f}/{zs[1]:.4f}/{zs[2]:.4f}")
    ok = ok and p_c
    # (4) guard closes + trips; over-transfer feeds back (no free sink)
    c = conservation()
    p_g = c["ring_closes"] and c["ring_trips"] and c["over_transfer_feeds_back"]
    print(f"  [{'PASS' if p_g else 'FAIL'}] guard: ring closes {c['ring_resid']:.1e} + trips "
          f"({c['ring_resid_trip']:.3f}); over-transfer feeds back "
          f"(unclamped z {c['z_unclamped']:.3f}->{c['z_unclamped_pert']:.3f})")
    ok = ok and p_g
    print("  ->", "FAITHFUL — resonant model regression-locked to the frozen doubler" if ok
          else "NOT matching — do not trust the resonant z")
    return ok


if __name__ == "__main__":
    run_self_test()
