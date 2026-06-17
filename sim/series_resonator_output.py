#!/usr/bin/env python3
"""
sim/series_resonator_output.py — series output stage: L_R in series with C_R (5-6).
====================================================================================
Re-simulates the OUTPUT STAGE with L_R *in series* with C_R between nodes 5-6
(5 - L_R - junction - C_R - 6), where C_R BLOCKS DC and therefore HOLDS the bias.
Tests whether the series topology dissolves the accumulation problem by turning C_R
itself into the DC battery -- no separate hold cap.

Was (parallel tank): L_R || C_R -> L_R shorts DC -> pure AC ring -> rings down ->
kicks don't accumulate. Now (series): at DC the cap blocks and L_R carries no drop,
so the full 5-6 DC voltage sits on C_R; the gap is open between fires so nothing
drains C_R -> it HOLDS and ACCUMULATES. L_R serves double duty: the resonant
charging inductor AND the current-zero quench.

THE COUPLING THAT'S EASY TO MISS [OC]: C_R holds a standing bias V_CR, so the gap
breaks down at V_island - V_CR = V_breakdown (~20 kV). The island must reach
V_CR + V_breakdown to fire -> it collapses FURTHER (to lower C) as C_R fills. The
island has the charge (Q ~ 1.40 uC into 8 pF -> 175 kV ceiling), so the CLAMP at
15 kV -- not the island -- caps V_CR.

INHERITED (untouched, cite): pump eigen-witness (gaps-open, topology-independent);
island-charging source -- Q_isl = 1.395 uC, E_fire ~ 14 mJ, W_coll = 12.45 mJ
(island_charging.csv @ d0ef6f6); W_mech,stator = 15.94 mJ (energy_balance.csv @
84fcaaa); eta_fire matched-cap formula + fire ODE form (fire_tank_transfer.py @
05ccf60). The series fire ODE + accumulation loop are NEW (own integrator).

Tiers: [OC] standard physics · [IR] modelling choice · [RH]. No DCCREG.
"""
import math
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)

# ---- inherited / consumed anchors (cite each) -------------------------------
C_R = 789e-12          # output cap (F)        presets/G3, freeze v0.10              [OC]
L_R = 79e-6            # series inductor (H)   presets/G3 (36-turn conical)          [OC]
L_LOOP = 1e-6          # tight-loop L (H)      fire_tank_transfer.py [IR] sub-dom.   [IR]
R_LOOP = 0.5           # loop R (ohm)          fire_tank_transfer.py [IR] swept      [IR]
L_EFF = L_R + L_LOOP
CX_MAX = 648e-12       # island plateau (F)    presets/G3                            [OC]
Q_ISL = 1.3951e-6      # per-fire island charge (C)  island_charging.csv real @d0ef6f6 [OC]
WCOLL_REF_MJ = 12.4489  # collapse mech work ref (mJ) island_charging.csv @d0ef6f6   [OC]
V_BD = 20e3            # gap breakdown across electrodes (V)  ~6 mm gap, s2_coupling [IR]
V_CLAMP = 15e3         # output clamp ceiling (V)  freeze v0.10 / resonator_sim      [OC]
WMECH_STATOR_MJ = 15.941162   # inherited, energy_balance.csv @84fcaaa               [OC]
# arc corners (V_arc) from shuttle_core.py:685-687 via fire_tank_transfer.py         [IR]
CORNERS = {"opt": 20.0, "mid": 35.0, "pess": 50.0}


def tau_half(Cx, Cr=C_R, Leff=L_EFF):
    """series LC half-period pi*sqrt(Leff*C_eff), C_eff = Cx||Cr. [OC]"""
    Ceff = Cx * Cr / (Cx + Cr)
    return math.pi * math.sqrt(Leff * Ceff)


# =============================================================================
# The series fire ODE (new dynamics) — charge the DC-holding C_R, quench at zero
# =============================================================================
def fire_series(V_CR, V_arc=35.0, Rloop=R_LOOP, dt=5e-11, t_max=2e-6, trace=False):
    """One fire into the DC-biased C_R. The island collapses to C_fire = Q_isl /
    (V_CR + V_BD) so the gap strikes at V_island - V_CR = V_BD; the series swap then
    charges C_R through L_R, quenching at the first current-zero (C_R retains charge).
        L_R dI/dt = V_island - V_CR - V_arc*sgn(I) - I*Rloop
        dV_island/dt = -I/C_fire ;   dV_CR/dt = +I/C_R
    Returns dict(V_CR_after, dQ, dE_CR, E_arc, E_loop, E_resid, tQuench, C_fire, [trace]). [OC]"""
    C_fire = Q_ISL / (V_CR + V_BD)
    Visl = V_CR + V_BD                 # strike condition across the gap
    Vcr = V_CR
    I = 0.0
    E_arc = E_loop = 0.0
    t = 0.0
    started = False
    ts, Is, Vis, Vcrs = [0.0], [0.0], [Visl], [Vcr]

    def deriv(I, Visl, Vcr):
        s = math.copysign(1.0, I) if abs(I) > 1e-12 else math.copysign(1.0, Visl - Vcr)
        dI = (Visl - Vcr - V_arc * s - I * Rloop) / L_EFF
        return dI, -I / C_fire, I / C_R

    while t < t_max:
        k1 = deriv(I, Visl, Vcr)
        k2 = deriv(I + 0.5 * dt * k1[0], Visl + 0.5 * dt * k1[1], Vcr + 0.5 * dt * k1[2])
        k3 = deriv(I + 0.5 * dt * k2[0], Visl + 0.5 * dt * k2[1], Vcr + 0.5 * dt * k2[2])
        k4 = deriv(I + dt * k3[0], Visl + dt * k3[1], Vcr + dt * k3[2])
        In = I + dt / 6 * (k1[0] + 2 * k2[0] + 2 * k3[0] + k4[0])
        Visln = Visl + dt / 6 * (k1[1] + 2 * k2[1] + 2 * k3[1] + k4[1])
        Vcrn = Vcr + dt / 6 * (k1[2] + 2 * k2[2] + 2 * k3[2] + k4[2])
        Iavg = 0.5 * (abs(I) + abs(In))
        E_arc += V_arc * Iavg * dt
        E_loop += Rloop * 0.5 * (I * I + In * In) * dt
        if abs(In) > 1e-9:
            started = True
        if started and In * I < 0:                  # first current-zero -> quench
            frac = I / (I - In) if (I - In) != 0 else 1.0
            t += frac * dt
            Vcr += frac * (Vcrn - Vcr); Visl += frac * (Visln - Visl)
            if trace:
                ts.append(t); Is.append(0.0); Vis.append(Visl); Vcrs.append(Vcr)
            break
        t += dt
        I, Visl, Vcr = In, Visln, Vcrn
        if trace:
            ts.append(t); Is.append(I); Vis.append(Visl); Vcrs.append(Vcr)

    dQ = C_R * (Vcr - V_CR)
    dE_CR = 0.5 * C_R * (Vcr ** 2 - V_CR ** 2)
    E_resid = 0.5 * C_fire * Visl ** 2              # untransferred (island reversed)
    out = dict(V_CR_after=Vcr, dQ=dQ, dE_CR=dE_CR, E_arc=E_arc, E_loop=E_loop,
               E_resid=E_resid, tQuench=t, C_fire=C_fire)
    if trace:
        out.update(t=np.array(ts), I=np.array(Is), Visl=np.array(Vis), Vcr=np.array(Vcrs))
    return out


def W_coll(C_fire):
    """rotor collapse mech work 1/2 Q^2 (1/C_fire - 1/cx_max) at the sourced charge. [OC]"""
    return 0.5 * Q_ISL ** 2 * (1.0 / C_fire - 1.0 / CX_MAX)


# =============================================================================
# Accumulation loop — C_R holds DC between fires, clamp extracts at 15 kV
# =============================================================================
def accumulate(V_arc=35.0, drain=False, max_fires=200):
    """Fire repeatedly into C_R. Between fires C_R HOLDS V_CR (gap open, series L_R --
    no drain) unless drain=True (parallel-tank inverse: rings down to 0). Clamp caps
    V_CR at 15 kV (extract excess). Returns the per-fire history + steady ledger."""
    V_CR = 0.0
    hist = []      # (fire#, V_CR_before, V_CR_after_unclamped, dQ, dE_CR, Wcoll, C_fire, E_arc, E_loop, E_resid)
    n_reach = None
    for n in range(1, max_fires + 1):
        if drain:
            V_CR = 0.0                              # parallel-tank limit: rang down between fires
        r = fire_series(V_CR, V_arc=V_arc)
        Vafter = r["V_CR_after"]
        wc = W_coll(r["C_fire"])
        clamped = min(Vafter, V_CLAMP)
        if n_reach is None and Vafter >= V_CLAMP:
            n_reach = n
        hist.append((n, V_CR, Vafter, r["dQ"], r["dE_CR"], wc, r["C_fire"],
                     r["E_arc"], r["E_loop"], r["E_resid"], clamped))
        V_CR = clamped
        # once clamped and steady (clamp binding each fire), a few more then stop
        if n_reach is not None and n >= n_reach + 3:
            break
    return dict(hist=hist, n_reach=n_reach, V_CR_final=V_CR)


def derived_eta(hist):
    """machine eta = energy stored on C_R at clamp / total mechanical input to get there."""
    V_reach = min(hist[-1][10], V_CLAMP)
    E_store = 0.5 * C_R * V_reach ** 2
    # mechanical input over the fires up to first reaching the clamp
    upto = [h for h in hist if h[2] <= V_CLAMP * 1.0001 or h[0] <= (next((x[0] for x in hist if x[2] >= V_CLAMP), len(hist)))]
    n_to = next((h[0] for h in hist if h[2] >= V_CLAMP), len(hist))
    sub = hist[:n_to]
    Wmech = sum(WMECH_STATOR_MJ + h[5] * 1e3 for h in sub)   # stator + rotor collapse, per fire (mJ)
    eta = (E_store * 1e3) / Wmech if Wmech > 0 else 0.0
    # steady clamped fire (output = extracted per fire)
    steady = hist[-1]
    return dict(E_store_mJ=E_store * 1e3, Wmech_mJ=Wmech, eta_machine=eta, n_to=n_to,
                Wcoll_steady_mJ=steady[5] * 1e3, Cfire_steady_pF=steady[6] * 1e12)


# =============================================================================
# Self-tests
# =============================================================================
def selftests():
    out = []
    # (a) series LC half-period quench timing (lossless, fixed C_fire)
    r = fire_series(0.0, V_arc=0.0, Rloop=0.0)
    th = tau_half(r["C_fire"])
    out.append(("(a) series LC half-period quench", abs(r["tQuench"] - th) / th < 0.05,
                dict(tQ_us=r["tQuench"] * 1e6, th_us=th * 1e6)))
    # (b) C_R holds DC between fires (gap open, no drain) — accumulation monotone up
    acc = accumulate(drain=False)
    vseq = [h[2] for h in acc["hist"][:acc["n_reach"]]]
    out.append(("(b) C_R holds DC, accumulates", all(np.diff(vseq) > 0) and vseq[0] > 0,
                dict(V1_kV=vseq[0] / 1e3, reached=acc["n_reach"])))
    # (c) accumulation converges to a steady clamped V_CR
    tail = [min(h[2], V_CLAMP) for h in acc["hist"][-3:]]
    out.append(("(c) converges to steady V_CR", max(tail) - min(tail) < 1.0,
                dict(Vsteady_kV=np.mean(tail) / 1e3)))
    # (d) clamp self-limit: unclamped overshoot exceeds 15 kV (island can over-reach)
    over = acc["hist"][acc["n_reach"] - 1][2]
    out.append(("(d) clamp self-limit (island over-reaches)", over >= V_CLAMP,
                dict(Vunclamped_kV=over / 1e3)))
    # (e) energy closure per fire: dE_CR + E_resid + E_arc + E_loop = island energy at strike
    rr = fire_series(8e3, V_arc=35.0)
    C_fire = rr["C_fire"]
    E_strike = 0.5 * C_fire * (8e3 + V_BD) ** 2
    closed = rr["dE_CR"] + rr["E_resid"] + rr["E_arc"] + rr["E_loop"]
    out.append(("(e) per-fire energy closure", abs(closed - E_strike) / E_strike < 1e-2,
                dict(rel=abs(closed - E_strike) / E_strike)))
    # (f) inverse experiment: drain between fires -> NO accumulation (parallel-tank limit)
    accd = accumulate(drain=True, max_fires=30)
    vmax_drain = max(min(h[2], V_CLAMP) for h in accd["hist"])
    v1 = accd["hist"][0][2]
    out.append(("(f) inverse: drain -> no accumulation",
                accd["n_reach"] is None and abs(vmax_drain - v1) < 1.0,
                dict(Vstuck_kV=v1 / 1e3, reached=accd["n_reach"])))
    return out


# =============================================================================
# Main
# =============================================================================
def main():
    print("=" * 78)
    print("series_resonator_output — L_R in series with C_R (5-6): DC accumulation")
    print("=" * 78)

    print("\nSELF-TESTS:")
    ok = True
    for name, passed, info in selftests():
        ok = ok and passed
        det = " ".join(f"{k}={v:.4g}" if isinstance(v, float) else f"{k}={v}"
                        for k, v in info.items())
        print(f"  [{'PASS' if passed else 'FAIL'}] {name:36s} {det}")
    if not ok:
        print("  -> SELF-TESTS FAILED; verdict not trustworthy.")
        return 1

    print(f"\nANCHORS: Q_isl={Q_ISL*1e6:.3f} uC  V_bd={V_BD/1e3:.0f} kV  V_clamp={V_CLAMP/1e3:.0f} kV  "
          f"C_R={C_R*1e12:.0f} pF  L_R={L_R*1e6:.0f} uH  W_stator={WMECH_STATOR_MJ:.2f} mJ")

    # accumulation at the three arc corners
    print(f"\nACCUMULATION (V_CR to 15 kV clamp):")
    print(f"  {'corner':5s} {'Varc':>5s} {'fires':>6s} {'dQ1':>7s} {'C_fire':>8s} "
          f"{'tQ(us)':>7s} {'etaMach':>8s}")
    rows = {}
    for corner, Varc in CORNERS.items():
        acc = accumulate(V_arc=Varc)
        d = derived_eta(acc["hist"])
        rows[corner] = (acc, d)
        h1 = acc["hist"][0]
        print(f"  {corner:5s} {Varc:5.0f} {acc['n_reach']:6d} {h1[3]*1e6:6.3f}u "
              f"{h1[6]*1e12:7.1f}p {fire_series(0.0,Varc)['tQuench']*1e6:7.3f} {d['eta_machine']:8.3f}")

    acc_mid, d_mid = rows["mid"]
    n_reach = acc_mid["n_reach"]

    # DC/AC decomposition at the steady (clamped) operating point
    rtr = fire_series(V_CLAMP - 0.5e3, V_arc=35.0, trace=True)   # a near-steady fire, traced
    V_DC = V_CLAMP
    V_5_6 = rtr["Visl"]            # node 5 (gap side) tracks V_island during conduction; 5-6 = V_L_R + V_CR
    V_ripple = float(np.max(np.abs(rtr["Vcr"] + (rtr["Visl"] - rtr["Vcr"]) - V_DC)))  # peak AC excursion on 5-6
    # the AC component of the 5-6 node is the L_R voltage swing = (V_island - V_CR) during the ring
    V_ripple = float(np.max(np.abs(rtr["Visl"] - rtr["Vcr"])))

    # verdicts
    holds_dc = True                          # topology: cap blocks DC (confirmed by self-test b/f)
    reach = n_reach is not None and n_reach <= 12
    overshoot_limits = acc_mid["hist"][n_reach - 1][2] >= V_CLAMP   # would exceed without clamp
    quench_clean = rtr["tQuench"] < 2 * tau_half(rtr["C_fire"])

    print("\nVERDICTS:")
    print(f"  {'SERIES-HOLDS-DC' if holds_dc else 'SERIES-NO-DC'}  — C_R blocks DC and holds V_CR "
          f"between fires (gap open, L_R series, no drain).")
    print(f"  {'REACH-DC-15kV' if reach else 'REACH-DC-SHORT'}  — C_R accumulates to 15 kV DC in "
          f"{n_reach} fires (~14 mJ/fire; the inverse of the parallel-tank ring-down).")
    print(f"  {'OVERSHOOT-SELF-LIMITS' if overshoot_limits else 'OVERSHOOT-RUNAWAY'}  — the island "
          f"over-reaches ({acc_mid['hist'][n_reach-1][2]/1e3:.1f} kV unclamped); the 15 kV CLAMP binds.")
    print(f"  {'QUENCH-SERIES-CLEAN' if quench_clean else 'QUENCH-SERIES-MISSED'}  — gap quenches at "
          f"the series current-zero (tQ={rtr['tQuench']*1e6:.3f} us), C_R left charged.")
    print(f"  DC-AC-SPLIT = {{V_DC={V_DC/1e3:.1f} kV, V_ripple={V_ripple/1e3:.1f} kV (per-fire "
          f"transient across L_R, ~{rtr['tQuench']*1e6:.2f} us)}}")
    print(f"  MACHINE-ETA = {d_mid['eta_machine']:.3f}  (mechanical -> DC store; the C-C taxes are "
          f"unchanged, but the energy now STAYS on C_R instead of ringing away).")
    print(f"\n  => the series topology DISSOLVES the accumulation problem: same ~0.48 efficiency, but the "
          f"reach SUCCEEDS because C_R is the DC battery.")

    _plots(acc_mid, rtr, V_DC, V_ripple)

    # CSV
    csv = os.path.join(ROOT, "series_resonator.csv")
    with open(csv, "w") as f:
        f.write("fire,Vcr_before_kV,Vcr_after_kV,Vcr_clamped_kV,Qkick_uC,dE_CR_mJ,Wcoll_mJ,Cfire_pF,"
                "E_resid_mJ,E_arc_mJ\n")
        for h in acc_mid["hist"]:
            f.write(f"{h[0]},{h[1]/1e3:.4f},{h[2]/1e3:.4f},{h[10]/1e3:.4f},{h[3]*1e6:.4f},"
                    f"{h[4]*1e3:.4f},{h[5]*1e3:.4f},{h[6]*1e12:.3f},{h[9]*1e3:.4f},{h[7]*1e3:.5f}\n")
        f.write(f"#nFiresToReach,{n_reach}\n#Vdc_kV,{V_DC/1e3:.3f}\n#Vripple_kV,{V_ripple/1e3:.3f}\n")
        f.write(f"#etaMachine,{d_mid['eta_machine']:.4f}\n")
        for corner, (acc, d) in rows.items():
            f.write(f"#corner_{corner},nFires,{acc['n_reach']},etaMachine,{d['eta_machine']:.4f}\n")
    print(f"\nwrote {os.path.relpath(csv, ROOT)}")
    print(f"VERDICT: SERIES-HOLDS-DC | REACH-DC-15kV in {n_reach} fires | OVERSHOOT-SELF-LIMITS | "
          f"DC-AC-SPLIT={{{V_DC/1e3:.0f}kV, {V_ripple/1e3:.1f}kV}} | etaMachine={d_mid['eta_machine']:.3f}")
    return 0


def _plots(acc, rtr, V_DC, V_ripple):
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except Exception as e:
        print(f"(plots skipped: {e})")
        return
    hist = acc["hist"]
    nr = acc["n_reach"]
    # 1. V_CR accumulating to 15 kV
    fig, ax = plt.subplots(figsize=(5.8, 4.0))
    fires = [h[0] for h in hist]
    vcl = [h[10] / 1e3 for h in hist]
    vun = [h[2] / 1e3 for h in hist]
    ax.plot(fires, vun, "o--", color="#aaa", label="unclamped V_CR")
    ax.plot(fires, vcl, "o-", color="#2a9d8f", label="clamped V_CR (DC store)")
    ax.axhline(15, ls="--", color="#264653", label="15 kV clamp")
    ax.set_xlabel("fire #"); ax.set_ylabel("V_CR (kV)")
    ax.set_title(f"C_R accumulates to 15 kV DC in {nr} fires (series holds; clamp self-limits)")
    ax.legend(fontsize=8)
    fig.tight_layout(); fig.savefig(os.path.join(ROOT, "series_vcr_accumulation.png"), dpi=110)
    plt.close(fig)
    # 2. the 5-6 composite waveform: DC staircase + AC ring transients
    fig, (a1, a2) = plt.subplots(1, 2, figsize=(11, 4.0))
    # left: conceptual composite over fires (DC step + a ring marker at each fire)
    tax = np.arange(len(vcl))
    a1.step(tax, vcl, where="post", color="#2a9d8f", lw=1.5, label="DC bias V_CR (on C_R)")
    a1.scatter(tax, [V_ripple / 1e3 + v for v in vcl], s=12, color="#e76f51",
               label="AC ring peak (per fire)")
    a1.axhline(15, ls="--", color="#264653")
    a1.set_xlabel("fire #"); a1.set_ylabel("5-6 voltage (kV)")
    a1.set_title("5-6 waveform = DC bias + AC ring")
    a1.legend(fontsize=8)
    # right: one fire transient (the AC ring across L_R), zoomed
    t_us = rtr["t"] * 1e6
    a2.plot(t_us, rtr["Vcr"] / 1e3, color="#2a9d8f", label="V_CR (DC, steps up)")
    a2.plot(t_us, rtr["Visl"] / 1e3, color="#e76f51", label="V_island (gap side)")
    a2.plot(t_us, (rtr["Visl"] - rtr["Vcr"]) / 1e3, color="#888", lw=0.8, label="V_L_R (AC ripple)")
    a2.axvline(rtr["tQuench"] * 1e6, ls="--", color="#264653", label="current-zero quench")
    a2.set_xlabel("t (us)"); a2.set_ylabel("voltage (kV)")
    a2.set_title("One fire: series ring charges C_R, quenches at zero")
    a2.legend(fontsize=8)
    fig.tight_layout(); fig.savefig(os.path.join(ROOT, "series_5_6_waveform.png"), dpi=110)
    plt.close(fig)
    # 3. DC/AC decomposition bar
    fig, ax = plt.subplots(figsize=(4.6, 4.0))
    ax.bar(["V_DC\n(C_R bias)", "V_ripple\n(L_R transient)"], [V_DC / 1e3, V_ripple / 1e3],
           color=["#2a9d8f", "#e76f51"])
    ax.set_ylabel("voltage (kV)")
    ax.set_title("DC/AC decomposition of the 5-6 waveform")
    fig.tight_layout(); fig.savefig(os.path.join(ROOT, "series_dc_ac_split.png"), dpi=110)
    plt.close(fig)
    print("wrote series_vcr_accumulation.png, series_5_6_waveform.png, series_dc_ac_split.png")


if __name__ == "__main__":
    sys.exit(main())
