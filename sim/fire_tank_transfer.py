#!/usr/bin/env python3
"""
sim/fire_tank_transfer.py — island -> tank fire-path dynamic ODE + machine eta.
==============================================================================
The S3-deferred local-loop fire transfer, integrated in time, + the whole-machine
mechanical-to-tank efficiency (the headline the user originally asked for).

The stator block (`energy-balance`, commit 84fcaaa) found the 4-node doubler core
is only 38.6% efficient (a real 61% C-C equalization tax) but flagged that the
~89 mJ tank kick is NOT that path: it is the island Cx -> tank C_R fire, an
inductive C-L-C swap that should bypass the two-capacitor tax. This module builds
that fire as a time-domain ODE, accounts arc + loop losses, and folds in the
stator to report eta_machine.

SCOPE [OC]: this is NOT consumer-only. All *state* (pre-fire island, Cx, tank
C_R/L_R, V_arc) is CONSUMED from the frozen `shuttle_core` trace + Block R; the
fire transfer itself is a NEW time-domain ODE with its own RK4 integrator (the
frozen quasi-static solver cannot do the L-coupled dynamics — every prior run
SHORTED the 5-6 tank). Frozen modules (`shuttle_core.py`,
`reference/doubler_core.py`, `index.html`) stay byte-identical; the new dynamics
live here. Ordinary circuit dynamics + electromechanics only — no DCCREG.

KEY MODELLING DECISION (user: "literal trace, may escalate"): W_mech,island is
the LITERAL flying-bucket 1/2 Q^2 D(1/C) from the frozen shuttle trace (~1.6
mJ/fire), NOT the M2 island-dump energy. The fire ODE uses the brief's M2 island
(Cx=648 pF at V_island~20 kV -> E_island,pre~130 mJ). If the efficient fire
delivers far more than the literal mechanical work accounts for, eta_machine > 1
-> reported as ENERGY-BALANCE-GAP (the M1-trace vs M2-reach inconsistency the
campaign never pinned).

Tiers: [OC] standard physics · [IR] modelling choice (undocumented param) · [RH]
"""
import json
import math
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT)
import shuttle_core as sc  # FROZEN producer (state consumer only)

PRESET = os.path.join(ROOT, "presets", "G3-geometry-v010.json")

# ---- parameters (cite each; [IR] = undocumented estimate) -------------------
C_R = 789e-12        # tank cap (F)        presets/G3 + freeze v0.10 (f0 637 kHz) [OC]
L_R = 79e-6          # tank coil (H)       presets/G3 (36-turn conical)            [OC]
CX = 648e-12         # island plateau (F)  G3 cx3max; s2recheck_s3_spark.py:47     [OC]
L_LOOP = 1e-6        # tight fire-loop L (H)  UNDOCUMENTED -> estimate, sub-dom.   [IR]
R_LOOP = 0.5         # loop resistance (ohm)  UNDOCUMENTED -> estimate, swept      [IR]
L_EFF = L_R + L_LOOP
V_HV = 20e3          # island fire anchor (V)  s2_coupling.py:129 (sweep 18/23)    [IR]
VPEAK = 15e3         # tank operating ceiling (V)  freeze v0.10                    [OC]
PRF = 300.0          # branch PRF (Hz)     s2recheck_s3_spark.py:52               [OC]
FAV_HALF = 1.0 / (2 * PRF)   # favourable half-window 1.67 ms                     [OC]
WMECH_STATOR_MJ = 15.941162  # inherited, energy_balance.csv @ 84fcaaa            [OC]

# arc corners (V_arc, tau_rec) from shuttle_core.py:685-687 (ARC_CORNERS)        [IR]
CORNERS = {"opt": (20.0, 10e-6), "mid": (35.0, 100e-6), "pess": (50.0, 1e-3)}


def eta_matched(cx, cr):
    """S2 matched-cap LC transfer efficiency (the 0.990 to be tested). [OC]"""
    return 4.0 * cx * cr / (cx + cr) ** 2


# =============================================================================
# 1. Consume the pre-fire island state from the FROZEN shuttle trace
# =============================================================================
def island_state():
    """Read the flying-bucket island ledger at the G3 operating point and return
    the literal W_mech,island (1/2 Q^2 D(1/C)) anchored to V_HV, plus the trace
    provenance (boost ratio, ledger balance). No re-solve. [OC]"""
    p = json.load(open(PRESET))
    g = {k: p["params"][k]["value"] for k in p["params"]}
    sc.set_device_caps(C1MIN=g["c1min"], C1MAX=g["c1max"], C2MIN=g["c2min"],
                       C2MAX=g["c2max"], CA=g["ca"], CB=g["cb"], CPAR=g["cpar"])
    P = sc.Params()
    P.cx_min = float(g["cx3min"])   # 8 pF
    P.cx_max = float(g["cx3max"])   # 648 pF
    z, V, leds = sc.shuttle_run(P)
    L = leds[-1]["A"]
    # ledger balance (load_in == fire_out -> clean flying bucket) [OC]
    bal = abs(L["load_in"] - L["fire_out"]) / max(abs(L["load_in"]), 1e-30)
    cx_min, cx_max = P.cx_min * 1e-12, P.cx_max * 1e-12
    # LITERAL flying-bucket charge, anchored: the collapsed bucket at fire = V_HV
    # carries Q = cx_min * V_HV (the charge held constant through the collapse).
    Q = cx_min * V_HV
    Wmech_island = 0.5 * Q * Q * (1.0 / cx_min - 1.0 / cx_max)   # 1/2 Q^2 D(1/C)
    return dict(z=z, boost=L["boost"], ledger_bal=bal, cx_min=cx_min, cx_max=cx_max,
                Q_bucket=Q, Wmech_island_J=Wmech_island,
                E_bucket_J=0.5 * cx_min * V_HV * V_HV)   # what the bucket actually holds


# =============================================================================
# 2. The fire ODE (new dynamics) — RK4, quench at the first current-zero
# =============================================================================
def fire_ode(V_island, Cx, Cr, Leff, Rloop, V_arc, dt=2e-10, t_max=4e-6):
    """Integrate the local loop from (island @ V_island, tank @ 0, I=0) to the
    FIRST natural current-zero (quench). Returns trace arrays + the energy ledger.
        Leff dI/dt = V_isl - V_tank - V_arc*sgn(I) - I*Rloop
        dV_isl/dt  = -I/Cx ;  dV_tank/dt = +I/Cr
    No artificial cutoff: I->0 sets the quench. [OC]"""
    def deriv(I, Visl, Vtank):
        # arc drop opposes current; at I~0 use the driving sign so it can start
        s = math.copysign(1.0, I) if abs(I) > 1e-12 else math.copysign(1.0, Visl - Vtank)
        dI = (Visl - Vtank - V_arc * s - I * Rloop) / Leff
        return dI, -I / Cx, I / Cr

    t, I, Visl, Vtank = 0.0, 0.0, V_island, 0.0
    ts, Is, Vis, Vts = [t], [I], [Visl], [Vtank]
    E_arc = E_loop = 0.0
    started = False
    while t < t_max:
        # RK4 step
        k1 = deriv(I, Visl, Vtank)
        k2 = deriv(I + 0.5 * dt * k1[0], Visl + 0.5 * dt * k1[1], Vtank + 0.5 * dt * k1[2])
        k3 = deriv(I + 0.5 * dt * k2[0], Visl + 0.5 * dt * k2[1], Vtank + 0.5 * dt * k2[2])
        k4 = deriv(I + dt * k3[0], Visl + dt * k3[1], Vtank + dt * k3[2])
        In = I + dt / 6 * (k1[0] + 2 * k2[0] + 2 * k3[0] + k4[0])
        Visln = Visl + dt / 6 * (k1[1] + 2 * k2[1] + 2 * k3[1] + k4[1])
        Vtankn = Vtank + dt / 6 * (k1[2] + 2 * k2[2] + 2 * k3[2] + k4[2])
        # loss accounting over the step (trapezoid on |I|)
        Iavg = 0.5 * (abs(I) + abs(In))
        E_arc += V_arc * Iavg * dt
        E_loop += Rloop * 0.5 * (I * I + In * In) * dt
        if abs(In) > 1e-9:
            started = True
        # quench: first current-zero AFTER the pulse has started
        if started and In * I < 0:
            # linear-interpolate the zero crossing
            frac = I / (I - In) if (I - In) != 0 else 1.0
            t += frac * dt
            Visl += frac * (Visln - Visl)
            Vtank += frac * (Vtankn - Vtank)
            I = 0.0
            ts.append(t); Is.append(0.0); Vis.append(Visl); Vts.append(Vtank)
            break
        t += dt
        I, Visl, Vtank = In, Visln, Vtankn
        ts.append(t); Is.append(I); Vis.append(Visl); Vts.append(Vtank)

    E_pre = 0.5 * Cx * V_island ** 2
    E_tank = 0.5 * Cr * Vtank ** 2
    E_resid = 0.5 * Cx * Visl ** 2
    return dict(t=np.array(ts), I=np.array(Is), Visl=np.array(Vis), Vtank=np.array(Vts),
                tQuench=t, E_pre=E_pre, E_tank=E_tank, E_arc=E_arc, E_loop=E_loop,
                E_resid=E_resid, Vtank_final=Vtank, Visl_final=Visl)


def tau_half(Leff, Cx, Cr):
    """Quench half-period pi*sqrt(Leff*C_eff), C_eff = series Cx||Cr. [OC]"""
    Ceff = Cx * Cr / (Cx + Cr)
    return math.pi * math.sqrt(Leff * Ceff)


# =============================================================================
# 3. Self-tests
# =============================================================================
def selftests():
    out = []
    # (a) lossless MATCHED LC swap -> full transfer, eta_fire -> 1
    r = fire_ode(V_HV, C_R, C_R, L_EFF, 0.0, 0.0)
    eta = r["E_tank"] / r["E_pre"]
    out.append(("(a) lossless matched LC swap eta->1", abs(eta - 1.0) < 1e-3,
                dict(eta=eta)))
    # (b) arc-dominated limit -> eta collapses monotonically, attributed to arc
    r_lo = fire_ode(V_HV, CX, C_R, L_EFF, 0.0, 100.0)     # small arc
    r_hi = fire_ode(V_HV, CX, C_R, L_EFF, 0.0, 8000.0)    # large arc
    eta_lo = r_lo["E_tank"] / r_lo["E_pre"]
    eta_hi = r_hi["E_tank"] / r_hi["E_pre"]
    out.append(("(b) arc-dominated -> eta collapses",
                (eta_hi < eta_lo - 0.2) and (r_hi["E_arc"] > 10 * r_lo["E_arc"]),
                dict(eta_lo=eta_lo, eta_hi=eta_hi, Earc_hi_mJ=r_hi["E_arc"] * 1e3)))
    # (c) ODE energy closure: delivered+arc+loop+residual = E_pre
    r3 = fire_ode(V_HV, CX, C_R, L_EFF, R_LOOP, 35.0)
    closure = abs((r3["E_tank"] + r3["E_arc"] + r3["E_loop"] + r3["E_resid"]) - r3["E_pre"])
    out.append(("(c) ODE energy closure", closure / r3["E_pre"] < 1e-3,
                dict(rel=closure / r3["E_pre"])))
    # (d) 89 mJ tank scale
    Etank = 0.5 * C_R * VPEAK ** 2
    out.append(("(d) 1/2 C_R Vpeak^2 = 89 mJ", abs(Etank * 1e3 - 89.0) < 0.5,
                dict(mJ=Etank * 1e3)))
    # (e) quench half-period matches pi*sqrt(Leff*Ceff)
    r4 = fire_ode(V_HV, CX, C_R, L_EFF, 0.0, 0.0)   # lossless -> clean half-ring
    th = tau_half(L_EFF, CX, C_R)
    out.append(("(e) tQuench ~ pi*sqrt(Leff*Ceff)", abs(r4["tQuench"] - th) / th < 0.05,
                dict(tQ_us=r4["tQuench"] * 1e6, th_us=th * 1e6)))
    return out


# =============================================================================
# 4. Main
# =============================================================================
def main():
    print("=" * 76)
    print("fire_tank_transfer — island->tank C-L-C fire + machine energy balance")
    print("=" * 76)

    print("\nSELF-TESTS:")
    ok = True
    for name, passed, info in selftests():
        ok = ok and passed
        det = " ".join(f"{k}={v:.4g}" if isinstance(v, float) else f"{k}={v}"
                        for k, v in info.items())
        print(f"  [{'PASS' if passed else 'FAIL'}] {name:38s} {det}")
    if not ok:
        print("  -> SELF-TESTS FAILED; verdict not trustworthy.")
        return 1

    # --- consume the literal flying-bucket island state (frozen) ---
    isl = island_state()
    Wmech_isl_mJ = isl["Wmech_island_J"] * 1e3
    print(f"\nFROZEN island trace (G3): z={isl['z']:.4f}  boost={isl['boost']:.1f}  "
          f"ledger_bal={isl['ledger_bal']:.1e}")
    print(f"  W_mech,island (LITERAL flying-bucket 1/2 Q^2 D(1/C), anchored {V_HV/1e3:.0f} kV)"
          f" = {Wmech_isl_mJ:.3f} mJ")
    print(f"  (the collapsed bucket holds E_bucket = {isl['E_bucket_J']*1e3:.3f} mJ at fire)")
    print(f"  W_mech,stator (inherited, 84fcaaa) = {WMECH_STATOR_MJ:.3f} mJ")

    th = tau_half(L_EFF, CX, C_R)
    print(f"\nFIRE ODE: M2 island Cx={CX*1e12:.0f} pF -> tank C_R={C_R*1e12:.0f} pF through "
          f"L_eff={L_EFF*1e6:.0f} uH")
    print(f"  matched-cap LC ceiling eta = 4 Cx C_R/(Cx+C_R)^2 = {eta_matched(CX, C_R):.4f} "
          f"(the S2 0.990 to test)")
    print(f"  quench half-period pi*sqrt(Leff*Ceff) = {th*1e6:.3f} us; "
          f"ring-back at 2x = {2*th*1e6:.3f} us; favourable half = {FAV_HALF*1e3:.2f} ms")

    # --- corner sweep ---
    print("\nCORNER SWEEP (anchor V_island = 20 kV):")
    print(f"  {'corner':5s} {'Varc':>5s} {'etaFire':>8s} {'Etank':>8s} {'Earc':>7s} "
          f"{'Eloop':>7s} {'Eresid':>7s} {'tQ(us)':>7s} {'etaMach':>8s}")
    rows = []
    for corner, (Varc, trec) in CORNERS.items():
        r = fire_ode(V_HV, CX, C_R, L_EFF, R_LOOP, Varc)
        etaF = r["E_tank"] / r["E_pre"]
        etaM = (r["E_tank"] * 1e3) / (WMECH_STATOR_MJ + Wmech_isl_mJ)
        rows.append((corner, Varc, trec, etaF, r, etaM))
        print(f"  {corner:5s} {Varc:5.0f} {etaF:8.4f} {r['E_tank']*1e3:7.2f}m "
              f"{r['E_arc']*1e3:6.3f}m {r['E_loop']*1e3:6.4f}m {r['E_resid']*1e3:6.3f}m "
              f"{r['tQuench']*1e6:7.3f} {etaM:8.3f}")

    # --- verdicts ---
    mid = next(x for x in rows if x[0] == "mid")
    etaF_mid, etaM_mid, r_mid, trec_mid = mid[3], mid[5], mid[4], mid[2]
    eta_s2 = eta_matched(CX, C_R)

    fire_recovers = etaF_mid > 0.90
    s2_confirmed = abs(etaF_mid - eta_s2) < 0.02
    quench_clean = trec_mid > 2 * r_mid["tQuench"]   # arc recovers >> before ring-back
    gap = etaM_mid > 1.0

    print("\nVERDICTS:")
    print(f"  {'FIRE-PATH-RECOVERS' if fire_recovers else 'FIRE-PATH-LOSSY'}"
          f"   (eta_fire(mid) = {etaF_mid:.4f} vs S2 matched {eta_s2:.4f})")
    print(f"  {'S2-ETA-CONFIRMED' if s2_confirmed else 'S2-ETA-OPTIMISTIC'}"
          f"   (dynamic transfer {'reproduces' if s2_confirmed else 'undercuts'} the 0.990 formula)")
    print(f"  {'QUENCH-AT-ZERO-CLEAN' if quench_clean else 'QUENCH-MISSED'}"
          f"   (arc tau_rec {trec_mid*1e6:.0f} us >> ring-back {2*r_mid['tQuench']*1e6:.2f} us)")
    if gap:
        print(f"  ENERGY-BALANCE-GAP  (eta_machine(mid) = {etaM_mid:.2f} > 1 -> the M2 island-dump")
        print(f"     reach is energetically INCONSISTENT with the literal flying-bucket trace:")
        print(f"     the efficient fire delivers E_tank={r_mid['E_tank']*1e3:.0f} mJ from a 648 pF")
        print(f"     /20 kV/130 mJ island, but the traced flying-bucket mechanical work is only")
        print(f"     {WMECH_STATOR_MJ+Wmech_isl_mJ:.1f} mJ (stator {WMECH_STATOR_MJ:.1f} + island "
              f"{Wmech_isl_mJ:.1f}). ESCALATE.)")
        print(f"  MACHINE-ETA = {etaM_mid:.2f} (mid) -> UNPHYSICAL (>1): M1 trace cannot source M2 reach.")
    else:
        print(f"  MACHINE-ETA = {etaM_mid:.3f} (mid)")

    # --- plots ---
    _plots(rows, r_mid)

    # --- CSV ---
    csv = os.path.join(ROOT, "machine_energy_balance.csv")
    with open(csv, "w") as f:
        f.write("corner,Varc_V,etaFire,Etank_mJ,Earc_mJ,Eloop_mJ,Eresid_mJ,tQuench_us,etaMachine\n")
        for corner, Varc, trec, etaF, r, etaM in rows:
            f.write(f"{corner},{Varc:.0f},{etaF:.6f},{r['E_tank']*1e3:.5f},{r['E_arc']*1e3:.5f},"
                    f"{r['E_loop']*1e3:.6f},{r['E_resid']*1e3:.5f},{r['tQuench']*1e6:.4f},{etaM:.4f}\n")
        f.write(f"#Wmech_stator_mJ,{WMECH_STATOR_MJ:.4f}\n")
        f.write(f"#Wmech_island_literal_mJ,{Wmech_isl_mJ:.4f}\n")
        f.write(f"#eta_S2_matched,{eta_s2:.6f}\n")
    print(f"\nwrote {os.path.relpath(csv, ROOT)}")
    return 0


def _plots(rows, r_mid):
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except Exception as e:
        print(f"(plots skipped: {e})")
        return
    # transfer trace
    fig, ax1 = plt.subplots(figsize=(6.2, 4.0))
    t_us = r_mid["t"] * 1e6
    ax1.plot(t_us, r_mid["Visl"] / 1e3, color="#e76f51", label="V_island")
    ax1.plot(t_us, r_mid["Vtank"] / 1e3, color="#2a9d8f", label="V_tank")
    ax1.axvline(r_mid["tQuench"] * 1e6, ls="--", color="#264653", label="current-zero quench")
    ax1.set_xlabel("t (us)"); ax1.set_ylabel("voltage (kV)")
    ax2 = ax1.twinx()
    ax2.plot(t_us, r_mid["I"], color="#888", alpha=0.6, label="I")
    ax2.set_ylabel("loop current I (A)")
    ax1.set_title("Fire transfer (mid corner): island -> tank C-L-C swap")
    ax1.legend(loc="center right", fontsize=8)
    fig.tight_layout(); fig.savefig(os.path.join(ROOT, "fire_transfer_trace.png"), dpi=110)
    plt.close(fig)
    # loss ledger bar (mid)
    fig, ax = plt.subplots(figsize=(5.0, 4.0))
    labels = ["delivered", "arc", "loop-R", "residual"]
    vals = [r_mid["E_tank"] * 1e3, r_mid["E_arc"] * 1e3, r_mid["E_loop"] * 1e3, r_mid["E_resid"] * 1e3]
    ax.bar(labels, vals, color=["#2a9d8f", "#e76f51", "#f4a261", "#aaa"])
    ax.set_ylabel("energy (mJ)")
    ax.set_title(f"Fire loss ledger (mid) — E_pre = {r_mid['E_pre']*1e3:.1f} mJ")
    fig.tight_layout(); fig.savefig(os.path.join(ROOT, "fire_loss_ledger.png"), dpi=110)
    plt.close(fig)
    # eta_machine vs corner
    fig, ax = plt.subplots(figsize=(5.2, 3.8))
    cs = [x[0] for x in rows]; etam = [x[5] for x in rows]; etaf = [x[3] for x in rows]
    ax.plot(cs, etaf, "o-", color="#2a9d8f", label="eta_fire")
    ax.plot(cs, etam, "s--", color="#e76f51", label="eta_machine")
    ax.axhline(1.0, ls=":", color="#264653", label="eta=1 (physical bound)")
    ax.set_ylabel("efficiency"); ax.set_title("eta_fire (clean) vs eta_machine (>1 = GAP)")
    ax.legend(fontsize=8)
    fig.tight_layout(); fig.savefig(os.path.join(ROOT, "machine_eta_vs_corner.png"), dpi=110)
    plt.close(fig)
    print("wrote fire_transfer_trace.png, fire_loss_ledger.png, machine_eta_vs_corner.png")


if __name__ == "__main__":
    sys.exit(main())
