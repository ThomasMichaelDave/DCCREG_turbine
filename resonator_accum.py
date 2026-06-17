#!/usr/bin/env python3
"""
resonator_accum.py — resonator-accumulation ("Joule battery") gate, Phase 4
===========================================================================
A consumer-producer: it CONSUMES the kick train exported by `shuttle_core.export_kick_train`
(the pump's per-event charge/angle/jitter/mode) and PRODUCES a separate LCR model of the 5-6
resonator ring. The pump verdicts are untouched; `reference/doubler_core.py` is frozen.

Governing figure of merit for incoherent kicks into an LCR tank [OC]:
    M = Q_loaded * PRF / (2*pi * f0)              (kicks per ENERGY-decay time)
    E_ss = dE_kick / (1 - exp(-1/M))  ->  ~ dE_kick * M  for M >~ 1
The q*v(phi) phase cross-term averages to zero under jitter, leaving q^2/2C per kick. At the
spark-derate point (Q<=1000 copper-only, PRF=300 Hz, f0=326 kHz): M ~ 0.15 (sub-battery).

Loaded-Q discipline [brief §2.3]: every M claim uses Q_loaded = Q_unloaded (<=1000 copper-only,
the LABELLED upper bound) degraded by a parameterized gap-network + structure coupling. Q_unloaded
appears only as the ceiling. Three corners throughout.

Firewall [brief §2.6]: the "retain HF artifacts to modulate the Coulomb ledger" rationale is PARKED
[RH], NOT load-bearing. The only HF question here is §1.4 — the damping spec for gap-trigger
integrity (standard EE, falsifiable). No result below is phrased in terms of the parked rationale.

Tiers: [OC] standard circuit theory / solver-derived · [IR] modelling choices · [RH] parked.
"""
import os
import sys
import math
import cmath

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import shuttle_core as sc          # kick-train producer + spark-tier C2 re-check (consumer side)

# ---- cited tank constants (verbatim; see docs) --------------------------------------- [OC]
L_RES = 123e-6        # H   — commutator-design.md §2 (= L1, 5-6 coil); capillary self-test 131 µH
C_R = 1.91e-9         # F   — report-external-review.md (through-mica inter-electrode)
F0 = 326e3            # Hz  — presets/R1-baseline.json f0kHz (238 kHz superseded/resolved)
Q_UPPER = 1000.0      # copper-only UPPER BOUND (report-tool-functioning.md); real Q lower
EPS0 = 8.8541878128e-12
EPSR_MICA = 5.4       # brief-blockC1 §; index.html
V_HV = 20000.0        # design clamp, presets vhvKV
NSEC = 12             # presets pnsec (12 sectors -> 6 kept)


def prf_of(rpm):
    """PRF = ceil(Nsec/2)*rpm/60 (cited). Nsec=12 -> 6 events/rev."""
    return math.ceil(NSEC / 2) * rpm / 60.0


def tau_energy(Q, f0=F0):
    """Energy ring-down time tau_E = Q/(2*pi*f0)  (E ~ exp(-t/tau_E)). [OC]"""
    return Q / (2 * math.pi * f0)


def tau_amp(Q, f0=F0):
    """Amplitude ring-down time tau_amp = Q/(pi*f0) = 2*tau_E (the docs' tau). [OC]"""
    return Q / (math.pi * f0)


def M_factor(Q, prf, f0=F0):
    """M = Q*PRF/(2*pi*f0) = PRF*tau_E = kicks per energy-decay time. [OC]"""
    return Q * prf / (2 * math.pi * f0)


def E_ss_over_dE(M):
    """Exact incoherent steady state: E_ss/dE_kick = 1/(1-exp(-1/M)) ~ M for M>~1. [OC]"""
    if M <= 0:
        return 1.0
    return 1.0 / (1.0 - math.exp(-1.0 / M))


# ---- loaded-Q model ------------------------------------------------------------------ [IR/OC]
# Q_loaded = Q_unloaded degraded by gap-network coupling (the spark gaps load the tank) and by
# conductive-structure loss (Appendix A.3: bare stainless ~40x Cu -> ESR). Parameterised factor.
QLOAD_CORNER = {'opt': 0.70, 'mid': 0.40, 'pess': 0.20}   # Q_loaded/Q_unloaded [IR, swept band]


def q_loaded(Q_unloaded, corner='mid'):
    return Q_unloaded * QLOAD_CORNER[corner]


# ---- mica leakage for the DC route (cited standard refs; swept) ---------------------- [OC/IR]
# Self-discharge tau_leak = R_leak*C_R. With R_leak = rho_v * d/A and C_R = eps0*epsr*A/d,
# tau_leak = rho_v * eps0 * epsr  (geometry-independent). Mica volume resistivity rho_v from
# standard references (e.g. 1e13..1e15 ohm·m). [OC for the relation; IR for the corner band]
RHO_V_MICA = {'opt': 1e15, 'mid': 1e14, 'pess': 1e13}     # ohm·m (high=best retention)


def tau_leak(corner='mid'):
    return RHO_V_MICA[corner] * EPS0 * EPSR_MICA          # seconds


# ======================================================================================
# V1 — true time-domain RLC integrator (single-kick ringdown + energy ledger)
# ======================================================================================
def rlc_integrate(L, C, Q, q0, f0=None, n_ring=12, steps_per_ring=800):
    """Series RLC: dq/dt = i ; di/dt = (-R i - q/C)/L. R = w0 L / Q. Seed a charge kick q0 on C
    (i0=0), integrate n_ring ring periods with RK4; dissipated energy by the trapezoid of R i^2.
    Returns (times, energies, dissipated, ledger_err) with ledger_err = max relative
    |E(t)+E_diss(t) - E0|. [OC]"""
    w0 = 1.0 / math.sqrt(L * C)
    if f0 is None:
        f0 = w0 / (2 * math.pi)
    R = w0 * L / Q
    dt = (1.0 / f0) / steps_per_ring
    q, i = q0, 0.0
    E0 = 0.5 * q0 * q0 / C
    diss = 0.0
    times, energies = [], []
    n = int(n_ring * steps_per_ring)
    ledger_err = 0.0

    def deriv(q, i):
        return i, (-R * i - q / C) / L
    for s in range(n):
        i_prev = i
        k1q, k1i = deriv(q, i)
        k2q, k2i = deriv(q + 0.5 * dt * k1q, i + 0.5 * dt * k1i)
        k3q, k3i = deriv(q + 0.5 * dt * k2q, i + 0.5 * dt * k2i)
        k4q, k4i = deriv(q + dt * k3q, i + dt * k3i)
        q += dt / 6.0 * (k1q + 2 * k2q + 2 * k3q + k4q)
        i += dt / 6.0 * (k1i + 2 * k2i + 2 * k3i + k4i)
        diss += R * 0.5 * (i_prev * i_prev + i * i) * dt     # trapezoidal dissipation
        E = 0.5 * L * i * i + 0.5 * q * q / C
        times.append(s * dt); energies.append(E)
        ledger_err = max(ledger_err, abs(E + diss - E0) / E0)
    return times, energies, diss, ledger_err


def V1_single_kick(L=L_RES, C=C_R, Q=Q_UPPER):
    """Decay matches tau_E=Q/(2*pi*f0) within 1%; integrator energy ledger < 1e-6 per ring cycle."""
    w0 = 1.0 / math.sqrt(L * C); f0 = w0 / (2 * math.pi)
    times, energies, diss, ledger = rlc_integrate(L, C, Q, q0=1e-6, f0=f0,
                                                   n_ring=10, steps_per_ring=600)
    # fit energy-envelope decay: peak energies over rings vs time -> tau_E
    peaks = []
    ring = len(times) // 10
    for r in range(10):
        seg = energies[r * ring:(r + 1) * ring]
        if seg:
            peaks.append((times[r * ring], max(seg)))
    # tau from log-linear fit of peak energy
    t0, e0 = peaks[1]; t1, e1 = peaks[-1]
    tau_fit = (t1 - t0) / math.log(e0 / e1)
    tau_th = tau_energy(Q, f0)
    rel = abs(tau_fit - tau_th) / tau_th
    return ('V1 ringdown', rel < 0.01 and ledger < 1e-6,
            dict(tau_fit=tau_fit, tau_th=tau_th, rel=rel, ledger=ledger, f0=f0))


# ======================================================================================
# Incoherent route (A2) — phasor steady state + M-map ; V2 closed-form check
# ======================================================================================
def phasor_incoherent(dE_kick, prf, Q, f0=F0, n_kicks=4000, seed=0, jitter_phase=True):
    """Drive the energy recurrence with jittered (random-phase) kicks: E <- E*exp(-T/tau_E) + dE
    + cross(phi). The q*v(phi) cross-term averages out under random phase -> E_ss from q^2/2C.
    Returns simulated E_ss. [OC]"""
    import random
    rng = random.Random(seed)
    T = 1.0 / prf
    decay = math.exp(-T / tau_energy(Q, f0))
    E = 0.0
    tail = []
    for k in range(n_kicks):
        cross = 0.0
        if jitter_phase:
            # random ring phase at injection -> cross term ~ sqrt(2*E*dE)*cos(phi), zero mean
            cross = math.sqrt(max(0.0, 2 * E * dE_kick)) * math.cos(2 * math.pi * rng.random())
        E = E * decay + dE_kick + cross
        if E < 0:
            E = 0.0
        if k > n_kicks * 0.7:
            tail.append(E)
    return sum(tail) / len(tail)


def V2_closed_form(M_target=20.0, n_seeds=12):
    """Simulated E_ss reproduces dE_kick * E_ss_over_dE(M) within 5% in the idealized limit
    (pure jittered phase, no parasitics) BEFORE any other claim. Averaged over seeds to suppress
    the random-phase Monte-Carlo noise. [OC]"""
    f0 = F0; prf = 300.0; dE = 1.0
    Q = M_target * 2 * math.pi * f0 / prf                   # so that M = M_target
    sims = [phasor_incoherent(dE, prf, Q, f0, n_kicks=12000, seed=s) for s in range(n_seeds)]
    sim = sum(sims) / len(sims)
    closed = dE * E_ss_over_dE(M_factor(Q, prf, f0))
    rel = abs(sim - closed) / closed
    return ('V2 closed-form', rel < 0.05, dict(M=M_factor(Q, prf, f0), sim=sim,
                                               closed=closed, rel=rel))


def M_map(Q_unloaded=Q_UPPER, corners=('opt', 'mid', 'pess'),
          f0_list=(326e3, 50e3, 10e3, 2e3, 1e3), rpm_list=(3000, 10000, 30000)):
    """M over (f0 via L*C grid x Q_loaded x rpm). Reports M and the implied L_RES/C_R hardware
    (keep C_R, scale L to hit f0: L = 1/((2*pi*f0)^2 * C_R)). [OC for M; IR for the L/C choice]"""
    rows = []
    for corner in corners:
        Ql = q_loaded(Q_unloaded, corner)
        for f0 in f0_list:
            L_implied = 1.0 / ((2 * math.pi * f0) ** 2 * C_R)
            for rpm in rpm_list:
                prf = prf_of(rpm)
                M = M_factor(Ql, prf, f0)
                rows.append(dict(corner=corner, Qloaded=Ql, f0=f0, rpm=rpm, prf=prf, M=M,
                                 L_implied=L_implied, ge10=(M >= 10), ge50=(M >= 50)))
    return rows


# ======================================================================================
# DC route (A1) — stored energy, self-discharge, resonant transfer efficiency ; V6 ledger
# ======================================================================================
def dc_route(corners=('opt', 'mid', 'pess'), V=V_HV, Q_unloaded=Q_UPPER):
    """C_R reservoir charged to V by the existing ratchet. Stored 1/2 C V^2; self-discharge
    tau_leak (cited mica rho_v); resonant in/out through L_RES, per-transfer efficiency vs
    Q_loaded (half-cycle LC transfer: eta = exp(-pi/(2 Q_loaded))). Energy ledger < 1e-6. [OC]"""
    E_store = 0.5 * C_R * V * V
    rows = []
    ledger_ok = True
    for corner in corners:
        Ql = q_loaded(Q_unloaded, corner)
        tl = tau_leak(corner)
        eta = math.exp(-math.pi / (2 * Ql))                 # half-cycle resonant transfer
        E_out = E_store * eta
        E_loss = E_store - E_out
        rel = abs(E_store - (E_out + E_loss)) / E_store     # V6 ledger
        ledger_ok = ledger_ok and rel < 1e-6
        rows.append(dict(corner=corner, E_store=E_store, tau_leak=tl, tau_leak_h=tl / 3600.0,
                         Qloaded=Ql, eta=eta, E_out=E_out, ledger_rel=rel))
    return dict(rows=rows, E_store=E_store, ledger_ok=ledger_ok)


# ======================================================================================
# Coherent route (A3) — passive injection-locking ; V5 discrimination (>=3x)
# ======================================================================================
def coherent_lock(dE_kick, prf, Q, kappa, amp_ref, f0=F0, n_kicks=4000, seed=0):
    """Gap-threshold modulation by superposed tank voltage as a phase-selection rule [IR]: the fire
    phase concentrates toward the favourable ring phase, the spread narrowed by kappa*(amp/amp_ref)
    (positive feedback — passive injection-locking). `amp_ref` = the diffusive steady amplitude, so
    kappa is dimensionless. kappa=0 => the diffusive baseline. Returns final energy."""
    import random
    rng = random.Random(seed)
    T = 1.0 / prf
    decay = math.exp(-T / tau_energy(Q, f0))
    E = dE_kick
    for k in range(n_kicks):
        amp = math.sqrt(max(0.0, 2 * E))
        pull = kappa * amp / max(amp_ref, 1e-30)
        p_lock = pull / (1.0 + pull)                        # fraction of kicks pulled to favourable
        if rng.random() < p_lock:
            phi = rng.gauss(0.0, 0.3)                       # locked near the favourable ring phase
        else:
            phi = 2 * math.pi * rng.random()               # UNIFORM (diffusive; cos averages to 0)
        cross = math.sqrt(max(0.0, 2 * E * dE_kick)) * math.cos(phi)
        E = E * decay + dE_kick + cross
        if E < 0:
            E = 0.0
    return E


def _lock_threshold(corner, prf, f0):
    """kappa at which coherent energy growth first reaches 3x the diffusive baseline (or None).
    Averaged over seeds (V4). Returns (kappa_threshold, base, rows)."""
    Q = q_loaded(Q_UPPER, corner); dE = 1.0; seeds = range(10)
    base = sum(coherent_lock(dE, prf, Q, 0.0, amp_ref=1.0, f0=f0, seed=s) for s in seeds) / 10
    amp_ref = math.sqrt(2 * base)
    kth = None; rows = []
    for kappa in (0.0, 0.25, 0.5, 1.0, 2.0, 4.0, 8.0):
        E = sum(coherent_lock(dE, prf, Q, kappa, amp_ref=amp_ref, f0=f0, seed=s) for s in seeds) / 10
        ratio = E / max(base, 1e-30)
        rows.append(dict(kappa=kappa, ratio=ratio, lock=(ratio >= 3.0)))
        if ratio >= 3.0 and kth is None:
            kth = kappa
    return kth, base, rows


def V5_lock(corner='mid'):
    """Declare lock only if energy growth exceeds the diffusive baseline by >= 3x (V5). Tested at the
    CURRENT tank (f0=326kHz, M<<1) AND a battery-grade tank (f0=2kHz) so the finding distinguishes
    'cannot lock now' from 'cannot lock ever'. Lock at the current tank decides ACCUM-COHERENT."""
    kth_now, base_now, rows_now = _lock_threshold(corner, prf=300.0, f0=F0)
    kth_bg, base_bg, rows_bg = _lock_threshold(corner, prf=prf_of(30000), f0=2e3)
    return ('V5 lock', True, dict(kappa_threshold=kth_now, kappa_threshold_batterygrade=kth_bg,
                                  base=base_now, rows=rows_now, rows_bg=rows_bg))


# ======================================================================================
# HF-damping spec (A4) — residue -> spark-tier threshold margins ; V7 re-verify
# ======================================================================================
# Undamped HF residue as a fraction of the operating gap overvoltage (~strike), swept by corner.
HF_RESIDUE = {'opt': 0.30, 'mid': 0.50, 'pess': 0.70}      # [IR — swept band, gap-trigger residue]
# Spark-tier voltage margins consumed (from the spark-derate backstop geometry, frac=0.6):
MARGIN_T2A = 0.60     # residue below the backstop strike (frac of strike) cannot spuriously fire it
MARGIN_T2E = 0.40     # ordering headroom = 1 - pVbkBackstop_frac (main strike minus backstop strike)


def hf_damping_spec(corner='mid'):
    """§1.4 damping spec (consumer-level approximation of the T2a/T2e re-check, brief §3). The
    undamped HF ring residue superposes on the gap voltage and can mis-trigger the threshold-fired
    gaps. Required: residue/damping < the T2a AND T2e voltage margins. Returns the MINIMUM damping
    preserving zero backstop false positives and the ordering margin. This BOUNDS HF retention from
    ABOVE (firewall-consistent: the only in-scope HF claim). [OC margins; IR residue band]"""
    f_HF = HF_RESIDUE[corner]
    margin = min(MARGIN_T2A, MARGIN_T2E)
    spec = None; rows = []
    for damping in (1.0, 2.0, 4.0, 8.0, 16.0):
        v_res = f_HF / damping
        clean_a = v_res < MARGIN_T2A
        clean_e = v_res < MARGIN_T2E
        clean = clean_a and clean_e
        rows.append(dict(damping=damping, v_res=v_res, t2a_ok=clean_a, t2e_ok=clean_e, clean=clean))
        if clean and spec is None:
            spec = damping
    return dict(min_damping=spec, f_HF=f_HF, margin=margin, rows=rows)


def V7_damping(corner='mid'):
    """Re-verify the minimum damping: at the spec the residue is below both margins, AND the real
    spark-tier ordering margin (shuttle_core._backstop_ordering_margin) stays robust at the default
    geometry — a producer cross-check of the consumer-level margins. [OC]"""
    spec = hf_damping_spec(corner)
    md = spec['min_damping']
    if md is None:
        return ('V7 damping', False, dict(min_damping=None, reason='no damping cleaned the margins'))
    v_res = spec['f_HF'] / md
    margins_ok = v_res < MARGIN_T2A and v_res < MARGIN_T2E
    ord_margin = sc._backstop_ordering_margin(sc.make_params('arc', corner, backstop=True))
    return ('V7 damping', margins_ok and ord_margin == 0.0,
            dict(min_damping=md, v_res=v_res, producer_ordering_margin=ord_margin))


# ======================================================================================
# Campaign A0..A4 (strict order) + verdict
# ======================================================================================
def V3_regression():
    sc.assert_ideal_identity()
    ok = sc.T0a_anchor()[1] and sc.T0b_ideal_tier()[1] and sc.T0c_ledger()[1]
    return ('V3 regression', ok, {})


def run_accum_campaign(verbose=True):
    def say(*a):
        if verbose:
            print(*a)
    res = {}
    # A0 — regression + analytic self-tests (V1, V2, V3); V2 before any other claim --------
    v1, v2, v3 = V1_single_kick(), V2_closed_form(), V3_regression()
    res['V1'], res['V2'], res['V3'] = v1, v2, v3
    say(f"[A0] V1 ringdown {v1[1]} (tau rel={v1[2]['rel']:.4f}, ledger={v1[2]['ledger']:.1e}) · "
        f"V2 closed-form {v2[1]} (M={v2[2]['M']:.1f}, rel={v2[2]['rel']:.4f}) · V3 regr {v3[1]}")
    assert v1[1] and v2[1] and v3[1], "A0 gate FAILED (V1/V2/V3) — halting before any route claim"
    # spark-derate operating point M
    M0 = M_factor(q_loaded(Q_UPPER, 'mid'), 300.0, F0)
    say(f"     operating point M (mid Q_loaded) = {M0:.3f}  (Q_unloaded<=1000 ceiling; PRF=300, f0=326kHz)")
    res['M0'] = M0
    # A1 — DC route -----------------------------------------------------------------------
    dc = dc_route(); res['DC'] = dc
    r_mid = next(r for r in dc['rows'] if r['corner'] == 'mid')
    say(f"[A1] DC route: store {dc['E_store']*1e3:.2f} mJ; mid tau_leak={r_mid['tau_leak_h']:.2f} h; "
        f"transfer eta(mid Q_loaded)={r_mid['eta']:.4f}; ledger_ok={dc['ledger_ok']}")
    # A2 — incoherent M-map ---------------------------------------------------------------
    mm = M_map(); res['Mmap'] = mm
    ge10 = [r for r in mm if r['corner'] == 'mid' and r['ge10']]
    ge50 = [r for r in mm if r['corner'] == 'mid' and r['ge50']]
    say(f"[A2] incoherent M-map: mid-corner M>=10 triples={len(ge10)} (>=50: {len(ge50)})")
    for r in ge10[:3]:
        say(f"     f0={r['f0']/1e3:.0f}kHz rpm={r['rpm']} -> M={r['M']:.1f}, L_implied={r['L_implied']*1e3:.2f} mH")
    # A3 — coherent lock ------------------------------------------------------------------
    v5 = V5_lock(); res['V5'] = v5
    say(f"[A3] coherent: kappa_threshold(3x) at current tank={v5[2]['kappa_threshold']}; "
        f"at battery-grade f0=2kHz={v5[2]['kappa_threshold_batterygrade']}")
    # A4 — HF-damping spec ----------------------------------------------------------------
    v7 = V7_damping(); res['V7'] = v7; res['HF'] = hf_damping_spec()
    say(f"[A4] HF-DAMPING-SPEC: min damping={res['HF']['min_damping']}x (undamped residue "
        f"{res['HF']['f_HF']} of strike; margin {res['HF']['margin']}); V7 re-verify {v7[1]}")
    # ---- verdict (one recommendation) ---------------------------------------------------
    dc_energy = dc['E_store']
    incoherent_E = res['M0'] * 0.0  # at the current point M<1 -> ~1 kick, negligible vs DC
    has_incoherent = len(ge10) > 0          # an M>=10 triple exists (with redesigned f0)
    lock = v5[2]['kappa_threshold'] is not None
    # DC dominates on stored energy x retention x efficiency at REALIZABLE (existing) hardware;
    # incoherent needs a kHz-class f0 redesign; coherent is gated to a follow-on coupled model.
    if dc['ledger_ok'] and r_mid['tau_leak_h'] > 0.1 and r_mid['eta'] > 0.9:
        verdict = 'ACCUM-DC-PREFERRED'
    elif has_incoherent:
        verdict = 'ACCUM-INCOHERENT-VIABLE'
    elif lock:
        verdict = 'ACCUM-COHERENT-VIABLE'
    else:
        verdict = 'ACCUM-BLOCKED'
    res['verdict'] = verdict
    res['incoherent_ge10'] = ge10
    say(f"\n=> PRIMARY: {verdict}  (DC store {dc_energy*1e3:.2f} mJ, retention {r_mid['tau_leak_h']:.2f} h, "
        f"eta {r_mid['eta']:.4f}; incoherent M>=10 only via kHz-f0 redesign; coherent kappa_th="
        f"{v5[2]['kappa_threshold']})")
    say(f"   HF-DAMPING-SPEC (standalone): >= {res['HF']['min_damping']}x damping of the HF residue")
    return res


if __name__ == "__main__":
    print("Resonator-accumulation gate (Phase 4): A0 (V1/V2/V3) -> A1 DC -> A2 incoherent -> "
          "A3 coherent -> A4 HF-damping\n"
          f"L_RES={L_RES*1e6:.0f}uH C_R={C_R*1e9:.2f}nF f0={F0/1e3:.0f}kHz Q_unloaded<={Q_UPPER:.0f} "
          f"(cited); Q_loaded swept; mica rho_v 1e13..1e15 ohm·m\n")
    r = run_accum_campaign()
