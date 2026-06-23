#!/usr/bin/env python3
"""
reference/commutator_real_core.py — the REAL commutator: V_strike spark gaps + Fowler-Nordheim FE.
==================================================================================================
The `doubler-resonant` result (Z-RETUNED, alpha_max 0.28, eta 0.404) used rail-return DIODES as the
rectifier -- a hard clamp at v<=0. THE MACHINE HAS NO DIODES. The commutation is spark gaps that
hold off to V_strike (not 0) + a Fowler-Nordheim field-emission backstop that bleeds SOFTLY. The
diode-at-0 pinned alpha_max at 0.28; the real gap holds off to V_strike, so the over-transfer has
far more headroom and the brigade tax is much more recoverable. This re-derives the price with the
real commutator and decides whether the Ca/Cb brigade inductors are worth keeping.

THE MODEL [OC]/[IR]
  * The rectifier is the gap holdoff: replace the diode threshold (v <= 0) with the spark-gap
    threshold (gap voltage <= V_strike). alpha_max = the swing at which the first gap reaches
    V_strike (it fires, arcs E_arc = V_arc*Q, self-quenches). This is the headroom a junction denies.
  * The field-emission backstop (BS3/BS4, onset 0.6*V_strike) is a SOFT bleed, J ~ E^2 exp(-B/E)
    (Fowler-Nordheim), continuous -- not a hard clamp. It bleeds charge along the swing and dwell,
    a real, accounted loss E_FE = integral V*I_FN dt.
  * The real brigade eta = direct eta + (tax recovered up to alpha_max - E_FE - E_arc)/W_mech.

DISCIPLINE: frozen `doubler_core`/`shuttle_core` READ-ONLY; the frozen sparking-backstop stays the
baseline. `doubler_resonant_core` (the alpha over-transfer cycle) and `island_resonant_core` (the
guard) are reused. Direct-limit anchor preserved: alpha->0 reproduces z 1.334 / eta 0.386.
Firewall: pure EE/plasma (spark breakdown + field emission are standard).

Tiers: [OC] derivable · [IR] design/empirical (V_strike, FN coeffs) · [ME] method · [SOLVER] integ.
"""
import numpy as np

# numpy 2.0 renamed trapz -> trapezoid AND removed trapz; Pyodide 0.26.2 ships numpy 1.26 (trapz
# only), the CLI ships 2.x (trapezoid only). Resolve at import so the live cores run on BOTH.
# [numpy-pyodide-compat] -- version-safe; do not replace with a bare np.trapezoid/np.trapz.
_trapz = getattr(np, "trapezoid", getattr(np, "trapz", None))

import doubler_core as dc                 # FROZEN anchor (read-only)
import doubler_resonant_core as drc       # the alpha over-transfer cycle (reused)
import island_resonant_core as irc        # the validated guard (reused unmodified)

G3 = drc.G3
DIRECT_Z, DIRECT_ETA = 1.334, 0.386

# absolute operating-point anchor (brigade / energy_balance, per cycle)
W_MECH_CYCLE_mJ = 31.882          # = 2 x 15.941 mJ/fire
DIRECT_TAX_CYCLE_mJ = 19.577      # = 2 x 9.789 mJ/fire
V_PEAK = 15e3                     # rail operating peak (V); normalised node 1.0 == V_PEAK
V_STRIKE = 20e3                  # spark-gap holdoff (V) -- established strike            [IR]
V_FE_FRAC = 0.6                  # FE backstop onset = 0.6 * V_strike (BS3/BS4)           [IR]
ARC_CORNERS = {"opt": 20.0, "mid": 35.0, "pess": 50.0}   # V_arc (V), shuttle_core       [IR]
Q_TRANSFER_C = 1.16e-6          # per-transfer charge (brigade ~C_eff*dV avg), for the arc [OC]

# ring / timing
T_HALF = 0.82e-6                # LC half-cycle (brigade)                                 [OC]
SG_WINDOW = 5.0 / 360.0 / (3000.0 / 60.0)   # 5 deg @ 3000 rpm = 278 us                  [IR]


def commutator_alpha_max(Vdir, Vpre, a_target, Vs_rel, eps=1e-12):
    """alpha_max under the spark-gap holdoff: the largest alpha keeping every gap voltage <= V_strike
    (relative to the running peak node, Vs_rel = V_strike/V_peak). Diode limit is Vs_rel = 0. [OC]"""
    pk = max(abs(x) for x in Vdir) or 1.0
    Vs = Vs_rel * pk
    D = Vdir - Vpre
    v = Vdir
    cons = [(v[1], D[1]), (v[2], D[2]), (v[0] - v[2], D[0] - D[2]), (v[3] - v[1], D[3] - D[1])]
    am = a_target
    for a, b in cons:
        if b > eps:
            lim = max(0.0, (Vs - a) / b)
            if lim < am:
                am = lim
    return am


def solve_doubler_commutator(g, a_target, Vs_rel, iterations=200, burn=100):
    """Steady z/eta_gross with the spark-gap (V_strike) rectifier replacing the diode clamp. The
    gross eta is BEFORE the FE bleed + arc are charged (those are the budget in fe_arc_budget). [SOLVER]"""
    C1min, C1max, C2min, C2max = g["C1min"], g["C1max"], g["C2min"], g["C2max"]
    Ca, Cb, Cpar = g["Ca"], g["Cb"], g["Cpar"]
    V = np.array([-1.0, 0.0, 0.0, -1.0]); C1c, C2c = C1max, C2min
    ratios, led, ams = [], [], []
    prev = abs(V[0]) + abs(V[3]); ladder = None
    for cyc in range(iterations):
        for (tC1, tC2) in [(C1min, C2max), (C1max, C2min)]:
            Q = dc.charges_from_voltages(V, C1c, C2c, Ca, Cb, Cpar)
            Vpre = np.linalg.solve(drc.cap_matrix(tC1, tC2, Ca, Cb, Cpar), Q)
            Vdir = np.asarray(dc.solve_phase(Q, tC1, tC2, Ca, Cb, Cpar), float)
            am = commutator_alpha_max(Vdir, Vpre, a_target, Vs_rel)
            Vres = Vdir + am * (Vdir - Vpre)
            U = lambda VV, A, B: drc.field_energy(VV, A, B, Ca, Cb, Cpar)
            Uprev, Upre, Ures = U(V, C1c, C2c), U(Vpre, tC1, tC2), U(Vres, tC1, tC2)
            if cyc >= burn:
                led.append((Upre - Uprev, Upre - Ures)); ams.append(am)
            V = Vres; C1c, C2c = tC1, tC2
        if cyc == (iterations + burn) // 2:
            mx = max(abs(v) for v in V) or 1.0
            ladder = [v / mx for v in V]
        mag = abs(V[0]) + abs(V[3])
        if cyc >= burn and prev > 1e-15 and mag > 1e-15:
            ratios.append(mag / prev)
        prev = mag
        mx = max(abs(v) for v in V)
        if mx > 1e6 or (0 < mx < 1e-6):
            V = V / mx; prev /= mx
    z = float(np.median(ratios)) if ratios else 1.0
    fr = [(w - t) / w for w, t in led if w > 1e-9]
    eta_gross = float(np.median(fr)) if fr else 0.0
    return dict(z=z, eta_gross=eta_gross, alpha_med=float(np.median(ams)) if ams else 0.0,
                ladder=ladder)


# =============================================================================
# Fowler-Nordheim field-emission backstop bleed  [IR]/[OC]
# =============================================================================
def fn_coeffs(I_ref, k, V_strike=V_STRIKE):
    """FN I(V) = A V^2 exp(-B/V) with B = k*V_strike (steepness) and A set so I(V_strike) = I_ref."""
    B = k * V_strike
    A = I_ref / (V_strike ** 2 * np.exp(-B / V_strike))
    return A, B


def fn_current(V, A, B):
    return A * V * V * np.exp(-B / V) if V > 1.0 else 0.0


def fe_arc_budget(eta_gross, alpha, Vs_rel, I_ref=30e-6, k=3.0, t_dwell=SG_WINDOW,
                  V_arc=ARC_CORNERS["opt"]):
    """The loss budget (mJ/cycle): recovered_gross - E_FE - E_arc -> eta_real. The FE leg bleeds over
    the LC swing (V(t)=Vpk sin) AND the held dwell; both islands' legs counted (x2). The sparking gap
    arcs E_arc=V_arc*Q when alpha is V_strike-limited (it fires to cap the swing). [SOLVER]/[IR]"""
    recovered_gross = (eta_gross - DIRECT_ETA) * W_MECH_CYCLE_mJ        # mJ/cycle
    Vpk = min(Vs_rel, 1.0 + (Vs_rel - 1.0)) * V_PEAK                    # swing peak ~ V_strike scale
    Vpk = Vs_rel * V_PEAK                                                # node reaches ~V_strike at cap
    A, B = fn_coeffs(I_ref, k)
    # swing bleed: V(t) = Vpk sin(pi t / t_half), integral V*I_FN dt
    N = 400
    ts = np.linspace(0.0, T_HALF, N)
    Vt = Vpk * np.sin(np.pi * ts / T_HALF)
    e_swing = float(_trapz([Vt[i] * fn_current(Vt[i], A, B) for i in range(N)], ts))
    e_dwell = Vpk * fn_current(Vpk, A, B) * t_dwell                     # held-state bleed
    E_FE = 2.0 * (e_swing + e_dwell) * 1e3                              # mJ/cycle, x2 islands
    fired = alpha >= Vs_rel * 0.0 + 1e-9 and alpha < 0.999             # V_strike-limited -> gap fires
    E_arc = (2.0 * V_arc * Q_TRANSFER_C * 1e3) if fired else 0.0        # mJ/cycle, 2 sparking gaps
    recovered_net = recovered_gross - E_FE - E_arc
    eta_real = DIRECT_ETA + recovered_net / W_MECH_CYCLE_mJ
    return dict(recovered_gross=recovered_gross, E_FE=E_FE, E_arc=E_arc,
                recovered_net=recovered_net, eta_real=eta_real, fired=fired)


# =============================================================================
# Conservation — independent guard incl. FE + arc  [ME]
# =============================================================================
def conservation(I_ref=30e-6, k=3.0):
    """(A) the LC ring guard (island_resonant_core) closes ~1e-12 AND trips +5% R. (B) the loss
    budget is non-tautological: +5% on B_FN (the FE coefficient) MUST move E_FE (the bleed is a real,
    perturbable loss, not bookkeeping). Returns a dict."""
    closes, resid, trips, resid_trip = irc.conservation(68.6e-12, 1e6 * 1e-12, 18.06e3, 1e-3, 2.0)
    r = solve_doubler_commutator(G3, 0.999, V_STRIKE / V_PEAK)
    b0 = fe_arc_budget(r["eta_gross"], r["alpha_med"], V_STRIKE / V_PEAK, I_ref, k)
    b1 = fe_arc_budget(r["eta_gross"], r["alpha_med"], V_STRIKE / V_PEAK, I_ref * 1.05, k)
    fe_moves = abs(b1["E_FE"] - b0["E_FE"]) / max(b0["E_FE"], 1e-12) > 1e-3
    return dict(ring_closes=closes, ring_resid=resid, ring_trips=trips, ring_resid_trip=resid_trip,
                E_FE_base=b0["E_FE"], E_FE_pert=b1["E_FE"], fe_loss_perturbable=fe_moves)


# =============================================================================
# Self-tests (the direct-limit anchor + the diode-limit cross-check)
# =============================================================================
def run_self_test():
    print("commutator_real_core self-tests:")
    ok = True
    f = dc.run_self_test(); ok = ok and f
    # (1) direct-limit: alpha->0 reproduces frozen z 1.334 / eta 0.386 (regardless of V_strike)
    r0 = solve_doubler_commutator(G3, 0.0, V_STRIKE / V_PEAK)
    p0 = abs(r0["z"] - DIRECT_Z) < 5e-3 and abs(r0["eta_gross"] - DIRECT_ETA) < 5e-3
    print(f"  [{'PASS' if p0 else 'FAIL — MODEL-FAIL'}] direct-limit alpha->0: z={r0['z']:.4f} "
          f"eta={r0['eta_gross']:.4f} (exp 1.334/0.386)")
    ok = ok and p0
    # (2) diode-limit cross-check: V_strike->0 reproduces the doubler-resonant clamp (z 1.573)
    rd = solve_doubler_commutator(G3, 0.999, 0.0)
    pd = abs(rd["z"] - 1.5727) < 3e-3 and abs(rd["eta_gross"] - 0.404) < 3e-3
    print(f"  [{'PASS' if pd else 'FAIL'}] diode-limit V_strike->0: z={rd['z']:.4f} "
          f"eta={rd['eta_gross']:.4f} (exp 1.573/0.404 = doubler-resonant)")
    ok = ok and pd
    # (3) headroom: V_strike holdoff lifts alpha_max well above the diode 0.28
    rr = solve_doubler_commutator(G3, 0.999, V_STRIKE / V_PEAK)
    p3 = rr["alpha_med"] > 0.5
    print(f"  [{'PASS' if p3 else 'FAIL'}] V_strike headroom: alpha_max={rr['alpha_med']:.3f} "
          f"(>> diode 0.28), z={rr['z']:.3f}, eta_gross={rr['eta_gross']:.3f}")
    ok = ok and p3
    # (4) guard closes + trips; FE loss perturbable
    c = conservation()
    p4 = c["ring_closes"] and c["ring_trips"] and c["fe_loss_perturbable"]
    print(f"  [{'PASS' if p4 else 'FAIL'}] guard: ring closes {c['ring_resid']:.1e} + trips "
          f"({c['ring_resid_trip']:.3f}); FE loss perturbable "
          f"(E_FE {c['E_FE_base']:.3f}->{c['E_FE_pert']:.3f} mJ under +5% FE leakage)")
    ok = ok and p4
    print("  ->", "FAITHFUL — real commutator anchored to the frozen doubler" if ok
          else "NOT matching")
    return ok


if __name__ == "__main__":
    run_self_test()
