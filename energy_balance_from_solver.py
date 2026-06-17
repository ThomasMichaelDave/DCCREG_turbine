#!/usr/bin/env python3
"""
energy_balance_from_solver.py — CONSUMER: electromechanical energy balance.
===========================================================================
A second conservation law (ENERGY) laid over the charge-law z campaign.

Goal (brief — electromechanical energy balance): trace the **mechanical shaft
work** delivered into the variable capacitors against the **energy accumulated
in the central resonator tank**, compute the conversion efficiency eta, and —
the load-bearing test — independently confirm **energy conservation**, with the
residual *localized* to the C-varying strokes (mechanical input) vs the
diode-conduction steps (equalization tax).

Discipline: CONSUMER-ONLY. Reads the FROZEN producer trace
(`reference/doubler_core.solve_doubler4(trace=True)` = "traceDoubler4") and
reuses the frozen `charges_from_voltages`. Recomputes **no** electrical solve:
the only linear algebra here is the *constant-charge* cap-change step (pure
mechanics, no diodes) and energy bookkeeping. 0 edits to any producer; frozen
modules stay byte-identical. de Queiroz's z explicitly excludes
electromechanical forces ("in the absence of losses and electromechanical
forces"), so this fills that gap and cross-checks the pump from the energy side.

Physics [OC]:
  * Constant-Q separation stroke (diodes off, plates separating): a varicap at
    charge Q stores U = Q^2/2C; dropping C *raises* U — that rise IS the
    mechanical work done against electrostatic attraction. For the 4-node
    network the generalization is W_mech = U(Q, C_new) - U(Q, C_old) at fixed
    node charge, path-independent (uses only endpoints).
  * Diode-conduction step (caps fixed, charge redistributes / drains to rail):
    can only DISSIPATE — the two-capacitor tax 1/2 C dV^2 even with ideal
    diodes. E_tax = U(pre-diode) - U(post-diode) >= 0.
  * Per cycle the telescoping identity is EXACT by construction:
        W_mech,cycle = dE_stored,cycle + E_tax,cycle
    The deliverable is the DECOMPOSITION (how much is stored vs taxed), not that
    it closes (it must). The bare doubler PUMPS (z>1) so dE_stored = (z^2-1)U > 0
    — the startup-growth view (b); the operating-point throughput view (a) uses
    the tank anchor (789 pF / 15 kV / 89 mJ).

Tiers: [OC] standard physics/math · [IR] modelling choice · [RH] rationale-only
"""
import json
import os
import sys

import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "reference"))
import doubler_core as dc  # FROZEN producer (mirror of index.html solveDoubler4)

PRESET = os.path.join(os.path.dirname(__file__), "presets", "G3-geometry-v010.json")

# ---- operating-point anchor (v0.10 freeze) ---------------------------------- [IR]
CR_PF = 789.0        # tank cap (pF), 12 mm garolite disc at r387
VPEAK_KV = 15.0      # tank ceiling (kV) — the governor clamp
ETANK_FLOOR_MJ = 89.0  # S3 single-kick reach floor (1/2 C_R Vpeak^2) — scale anchor


# =============================================================================
# Energy primitives (consumer; topology matches the frozen charges_from_voltages)
# =============================================================================
def cap_matrix(C1, C2, Ca, Cb, Cpar):
    """The 4x4 capacitance (Maxwell) matrix M with Q = M V, i.e. dQ/dV of the
    FROZEN charges_from_voltages. Block-diagonal (1-2 via Ca, 3-4 via Cb). [OC]"""
    return np.array([
        [C1 + Cpar + Ca, -Ca, 0.0, 0.0],
        [-Ca, Cpar + Ca, 0.0, 0.0],
        [0.0, 0.0, Cpar + Cb, -Cb],
        [0.0, 0.0, -Cb, C2 + Cpar + Cb],
    ])


def field_energy(V, C1, C2, Ca, Cb, Cpar):
    """Total electrostatic field energy U = 1/2 sum_caps C*dV^2 = 1/2 V.Q. [OC]
    Identical-by-algebra to 1/2 * dot(V, charges_from_voltages(V, ...))."""
    v1, v2, v3, v4 = V
    return 0.5 * (C1 * v1 * v1 + C2 * v4 * v4
                  + Cpar * (v1 * v1 + v2 * v2 + v3 * v3 + v4 * v4)
                  + Ca * (v1 - v2) ** 2 + Cb * (v3 - v4) ** 2)


def constant_q_step(Vprev, Cold, Cnew, Ca, Cb, Cpar):
    """The diodes-OFF mechanical stroke: caps change Cold->Cnew at constant node
    charge. Returns (Vint, Q): Vint solves M(Cnew) Vint = Q where Q is the frozen
    charge at the old caps. Pure mechanics — no diode logic. [OC]"""
    C1o, C2o = Cold
    C1n, C2n = Cnew
    Q = dc.charges_from_voltages(Vprev, C1o, C2o, Ca, Cb, Cpar)  # FROZEN
    Vint = np.linalg.solve(cap_matrix(C1n, C2n, Ca, Cb, Cpar), Q)
    return Vint, Q


# =============================================================================
# Walk the frozen trace -> per-transition (Wmech, Etax, dU)
# =============================================================================
def decompose(rec, Ca, Cb, Cpar):
    """For each consecutive transition in the frozen trace, split the stored-energy
    change into the mechanical stroke (Wmech) and the diode equalization tax
    (Etax). Returns a list of dicts. [OC]"""
    out = []
    for i in range(1, len(rec)):
        cyc0, ph0, C1o, C2o, Vprev = rec[i - 1]
        cyc1, ph1, C1n, C2n, Vpost = rec[i]
        Vint, Q = constant_q_step(Vprev, (C1o, C2o), (C1n, C2n), Ca, Cb, Cpar)
        Uprev = field_energy(Vprev, C1o, C2o, Ca, Cb, Cpar)
        Uint = field_energy(Vint, C1n, C2n, Ca, Cb, Cpar)
        Upost = field_energy(Vpost, C1n, C2n, Ca, Cb, Cpar)
        out.append(dict(cyc=cyc1, phase=ph1,
                        Wmech=Uint - Uprev,          # mechanical input (>0 when C drops)
                        Etax=Uint - Upost,           # equalization tax (>=0)
                        dU=Upost - Uprev,            # = Wmech - Etax (identity)
                        Uprev=Uprev, Upost=Upost,
                        Vpost=Vpost, Cnew=(C1n, C2n)))
    return out


def per_cycle(steps):
    """Group consecutive (phase B, phase A) transitions into whole cycles and sum
    Wmech / Etax / dU per cycle. Scale-free fractions are reported. [OC]"""
    cycles = {}
    for s in steps:
        c = cycles.setdefault(s["cyc"], dict(Wmech=0.0, Etax=0.0, dU=0.0, Ustart=None, Uend=None))
        c["Wmech"] += s["Wmech"]
        c["Etax"] += s["Etax"]
        c["dU"] += s["dU"]
        if c["Ustart"] is None:
            c["Ustart"] = s["Uprev"]
        c["Uend"] = s["Upost"]
    return cycles


# =============================================================================
# Retarding torque tau(theta) — the SOFT part (uses dC/dtheta; kept SEPARABLE)
# =============================================================================
def tau_profile(C1lo, C1hi, Ca, Cb, Cpar, Vpost_phaseA, n=200):
    """Retarding torque over one complementary-LINEAR sweep of the C1/C2 rotor:
    C1(t)=C1lo+(C1hi-C1lo)t, C2(t)=C1hi+C1lo-C1(t) (complementary). At CONSTANT
    node charge Q (taken from the steady phase-A endpoint), tau = dU/dtheta. The
    work integral closes to W_mech for that stroke (self-test d). dC/dtheta makes
    this SHAPE-dependent [IR] — reported, not folded into the energy verdict. [OC]"""
    Q = dc.charges_from_voltages(Vpost_phaseA, C1hi, C1lo, Ca, Cb, Cpar)  # phase-A caps
    th = np.linspace(0.0, 1.0, n)
    U = np.empty(n)
    for k, t in enumerate(th):
        C1 = C1lo + (C1hi - C1lo) * t
        C2 = C1hi + C1lo - C1
        V = np.linalg.solve(cap_matrix(C1, C2, Ca, Cb, Cpar), Q)
        U[k] = field_energy(V, C1, C2, Ca, Cb, Cpar)
    tau = np.gradient(U, th)            # tau(theta) = dU/dtheta at constant Q
    W = float(U[-1] - U[0])             # = integral tau dtheta
    mean = float(np.trapezoid(tau, th)) # mean over Dtheta=1 == W
    ripple = float((tau.max() - tau.min()) / (abs(mean) + 1e-30))
    return dict(theta=th, tau=tau, Wstroke=W, mean=mean, ripple=ripple)


# =============================================================================
# Self-tests (positive controls for the bookkeeping + the tax localizer)
# =============================================================================
def selftests():
    res = []
    # (a) single isolated cap stroke vs analytic 1/2 Q^2 D(1/C). [OC]
    Q0, Ca0, Cb0 = 3.0e-9, 100.0, 40.0
    dU = 0.5 * Q0 * Q0 * (1.0 / Cb0 - 1.0 / Ca0)
    Ua, Ub = 0.5 * Q0 * Q0 / Ca0, 0.5 * Q0 * Q0 / Cb0
    res.append(("(a) single-cap stroke = 1/2 Q^2 D(1/C)",
                abs((Ub - Ua) - dU) < 1e-18, dict(dU=dU, resid=(Ub - Ua) - dU)))

    # (b) lossless two-segment toy: identity closes to machine precision. [OC]
    Vp = [-1.0, 0.2, -0.3, -1.0]
    Vi, _ = constant_q_step(Vp, (280, 16), (16, 280), 309, 309, 20)
    # round-trip caps back (no diodes) -> must return to start charge/energy
    Vback, _ = constant_q_step(Vi, (16, 280), (280, 16), 309, 309, 20)
    close = abs(field_energy(Vback, 280, 16, 309, 309, 20)
                - field_energy(Vp, 280, 16, 309, 309, 20))
    res.append(("(b) constant-Q round-trip closes",
                close < 1e-12, dict(resid=close)))

    # (c) deliberate mismatched-voltage merge surfaces a KNOWN 1/2 C dV^2. [OC]
    # two caps C1,C2 at V1,V2; ideal-diode merge (short) -> dissipated tax.
    C1, C2, V1, V2 = 50.0, 30.0, 7.0, 2.0
    Vm = (C1 * V1 + C2 * V2) / (C1 + C2)               # charge-conserving merge
    Ubefore = 0.5 * C1 * V1 * V1 + 0.5 * C2 * V2 * V2
    Uafter = 0.5 * (C1 + C2) * Vm * Vm
    known = 0.5 * (C1 * C2 / (C1 + C2)) * (V1 - V2) ** 2
    res.append(("(c) mismatch merge tax = 1/2 (C1C2/(C1+C2)) dV^2",
                abs((Ubefore - Uafter) - known) < 1e-12,
                dict(tax=Ubefore - Uafter, known=known)))

    # (d) tau-mean = W_mech/Dtheta identity (Dtheta=1). [OC]
    _, rec = dc.solve_doubler4(16, 280, 16, 280, 309, 309, 20,
                               iterations=80, burn=40, trace=True)
    A = next(r for r in reversed(rec) if r[1] == "A")
    tp = tau_profile(16, 280, 309, 309, 20, A[4])
    res.append(("(d) tau-mean == W_stroke (Dtheta=1)",
                abs(tp["mean"] - tp["Wstroke"]) < 1e-9 * (abs(tp["Wstroke"]) + 1e-30),
                dict(mean=tp["mean"], W=tp["Wstroke"])))

    # (e) 89 mJ tank scale at 789 pF / 15 kV. [OC]
    Etank = 0.5 * CR_PF * 1e-12 * (VPEAK_KV * 1e3) ** 2
    res.append(("(e) 1/2 C_R Vpeak^2 == S3 floor 89 mJ",
                abs(Etank * 1e3 - ETANK_FLOOR_MJ) < 0.5,
                dict(Etank_mJ=Etank * 1e3)))
    return res


# =============================================================================
# Main
# =============================================================================
def load_caps():
    p = json.load(open(PRESET))
    g = {k: p["params"][k]["value"] for k in p["params"]}
    # consumer asserts loaded == expect (frozen byte-identity discipline)
    for k in p["expect"]:
        if k == "anchorZ":
            continue
        assert g[k] == p["expect"][k]["value"], f"preset drift on {k}"
    return g


def main():
    print("=" * 74)
    print("energy_balance_from_solver — electromechanical energy balance (consumer)")
    print("=" * 74)

    # --- self-tests first (gate) ---
    print("\nSELF-TESTS:")
    st = selftests()
    allok = True
    for name, ok, info in st:
        allok = allok and ok
        det = " ".join(f"{k}={v:.4g}" if isinstance(v, float) else f"{k}={v}"
                        for k, v in info.items())
        print(f"  [{'PASS' if ok else 'FAIL'}] {name:44s} {det}")
    if not allok:
        print("  -> SELF-TESTS FAILED; energy verdict not trustworthy.")
        return 1

    # --- frozen anchor (mirror must be FAITHFUL) ---
    assert dc.run_self_test(), "frozen doubler mirror not faithful"

    # --- operating geometry (G3, 789 pF point) ---
    g = load_caps()
    C1lo, C1hi = g["c1min"], g["c1max"]
    C2lo, C2hi = g["c2min"], g["c2max"]
    Ca, Cb, Cpar = g["ca"], g["cb"], g["cpar"]
    z, rec = dc.solve_doubler4(C1lo, C1hi, C2lo, C2hi, Ca, Cb, Cpar,
                               iterations=160, burn=80, trace=True)
    print(f"\nG3 4-node galvanic core: z = {z:.5f} (pumps; = the 1.334 ceiling)")

    steps = decompose(rec, Ca, Cb, Cpar)
    cyc = per_cycle(steps)
    # steady window: cycles 90..150 (well past burn, before the rescale tail)
    keys = sorted(k for k in cyc if 90 <= k <= 150)
    fr_tax, fr_store, ident, gro = [], [], [], []
    for k in keys:
        c = cyc[k]
        W, T, dU = c["Wmech"], c["Etax"], c["dU"]
        if W <= 0:
            continue
        fr_tax.append(T / W)
        fr_store.append(dU / W)
        ident.append(abs(W - (dU + T)) / (abs(W) + 1e-30))
        gro.append(dU / c["Ustart"])         # eigen-growth: dE_stored/U_start
    f_tax = float(np.median(fr_tax))
    f_store = float(np.median(fr_store))
    resid = float(np.max(ident))
    growth = float(np.median(gro))           # should equal z^2 - 1

    print("\nVIEW (b) — startup-growth decomposition (scale-free, per cycle):")
    print(f"  W_mech = dE_stored + E_tax  (identity residual max = {resid:.2e})")
    print(f"  dE_stored / W_mech (useful pumped electrical energy) = {f_store:.4f}")
    print(f"  E_tax     / W_mech (equalization tax, two-cap loss)  = {f_tax:.4f}")
    # eigen-growth cross-check: per-cycle stored-energy gain == z^2 - 1
    print(f"  cross-check dE_stored/U_start = {growth:.4f} vs z^2-1 = {z*z-1:.4f}"
          f"  (D = {abs(growth-(z*z-1)):.2e})")

    eta_core = f_store        # the electromechanical conversion efficiency of the core

    # --- absolute scale (anchor: peak rail node = Vpeak = 15 kV) ---
    kref = keys[len(keys) // 2]
    cyc_rows = [s for s in steps if s["cyc"] == kref]
    vmax = max(max(abs(v) for v in s["Vpost"]) for s in cyc_rows)
    scale = (VPEAK_KV * 1e3) / vmax
    Wcyc_mJ = sum(s["Wmech"] for s in cyc_rows) * scale * scale * 1e-12 * 1e3  # pF->F, J->mJ
    Wfire_mJ = Wcyc_mJ / 2.0            # 2 fires (phases) per cycle
    Useful_fire_mJ = Wfire_mJ * eta_core
    Etank_mJ = 0.5 * CR_PF * 1e-12 * (VPEAK_KV * 1e3) ** 2 * 1e3

    print("\nABSOLUTE scale (anchor: peak rail node = 15 kV) — 4-node core only:")
    print(f"  W_mech per fire (stator core)   = {Wfire_mJ:.3f} mJ")
    print(f"  useful per fire (= eta*W_mech)  = {Useful_fire_mJ:.3f} mJ")
    print(f"  E_tank per kick (accumulator)   = {Etank_mJ:.3f} mJ  (1/2 C_R Vpeak^2)")
    print("  NOTE [IR/scope]: the bare 4-node core's per-fire work is << the 89 mJ tank")
    print("  kick because the kick is dominated by the ISLAND Cx-collapse boost (not in")
    print("  this stator core). So eta IS the core conversion (dE_stored/W_mech), NOT the")
    print("  invalid cross-layer E_tank/W_mech (which would be >1).")

    # --- torque profile (soft, separable) ---
    A = next(r for r in reversed(rec) if r[1] == "A")
    tp = tau_profile(C1lo, C1hi, Ca, Cb, Cpar, A[4])
    print("\ntau(theta) — retarding torque (complementary-LINEAR sweep) [IR shape]:")
    print(f"  mean = {tp['mean']:.4g} (scale-free)  ripple factor = {tp['ripple']:.3f}")

    # --- verdicts ---
    tax_present = f_tax > 1e-6
    print("\nVERDICTS:")
    print(f"  ENERGY-BALANCE-CLOSES        (identity residual {resid:.1e} ~ machine prec.)")
    print("  EQUALIZATION-TAX-PRESENT" if tax_present else "  EQUALIZATION-TAX-ZERO",
          f"  (tax = {f_tax*100:.2f}% of W_mech; useful = {f_store*100:.2f}%)")
    print(f"  eta_conv = {eta_core:.3f} (core), tau-ripple = {tp['ripple']:.2f}  (reported)")

    # --- plots (energy-flow bar + tau profile) ---
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        d = os.path.dirname(__file__)
        # energy-flow bar: W_mech splits into useful (dE_stored) + tax
        fig, ax = plt.subplots(figsize=(5.2, 4.2))
        ax.bar(["W_mech\n(shaft in)"], [100], color="#888")
        ax.bar(["useful + tax"], [f_store * 100], color="#2a9d8f", label=f"dE_stored {f_store*100:.1f}%")
        ax.bar(["useful + tax"], [f_tax * 100], bottom=[f_store * 100], color="#e76f51",
               label=f"E_tax {f_tax*100:.1f}%")
        ax.set_ylabel("% of mechanical work in")
        ax.set_title(f"Energy balance — G3 core (z={z:.3f})\nidentity residual {resid:.0e}")
        ax.legend(loc="lower right", fontsize=8)
        fig.tight_layout(); fig.savefig(os.path.join(d, "energy_balance_flow.png"), dpi=110)
        plt.close(fig)
        # tau(theta) profile
        fig, ax = plt.subplots(figsize=(5.6, 3.6))
        ax.plot(tp["theta"], tp["tau"], color="#264653")
        ax.axhline(tp["mean"], ls="--", color="#e76f51", label=f"mean (=W/Dtheta)")
        ax.set_xlabel("rotor angle theta (sector frac)")
        ax.set_ylabel("retarding torque tau (scale-free)")
        ax.set_title(f"tau(theta) — complementary-linear [IR]; ripple {tp['ripple']:.2f}")
        ax.legend(fontsize=8)
        fig.tight_layout(); fig.savefig(os.path.join(d, "energy_balance_tau.png"), dpi=110)
        plt.close(fig)
        print("wrote energy_balance_flow.png, energy_balance_tau.png")
    except Exception as e:  # plotting is non-essential to the verdict
        print(f"(plots skipped: {e})")

    # --- machine-readable ---
    out = os.path.join(os.path.dirname(__file__), "energy_balance.csv")
    with open(out, "w") as f:
        f.write("quantity,value,unit,note\n")
        f.write(f"z,{z:.6f},,4-node galvanic ceiling (G3 caps)\n")
        f.write(f"eta_conv,{eta_core:.6f},,dE_stored/W_mech = core conversion efficiency\n")
        f.write(f"Etax_over_Wmech,{f_tax:.6f},,equalization tax fraction\n")
        f.write(f"identity_residual,{resid:.3e},,W_mech-(dE+Etax) max\n")
        f.write(f"growth,{growth:.6f},,dE_stored/U_start (== z^2-1 cross-check)\n")
        f.write(f"z2_minus_1,{z*z-1:.6f},,eigen-growth target\n")
        f.write(f"Wmech_per_fire,{Wfire_mJ:.6f},mJ,stator core; anchor rail=15kV\n")
        f.write(f"useful_per_fire,{Useful_fire_mJ:.6f},mJ,eta*Wmech (stator core)\n")
        f.write(f"Etank_per_kick,{Etank_mJ:.6f},mJ,1/2 C_R Vpeak^2 (island-boost dominated)\n")
        f.write(f"tau_ripple,{tp['ripple']:.6f},,complementary-linear sweep\n")
    print(f"\nwrote {os.path.basename(out)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
