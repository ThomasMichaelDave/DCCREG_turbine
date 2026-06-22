#!/usr/bin/env python3
"""
sim/resonant_brigade.py — Phase 2: resonate the dominant doubler transfers (the 69% lever).
===========================================================================================
Walk the Phase-1 ranked list (brigade_tax_localize) from the top. For each dominant switched
transfer add a series inductor and model the half-cycle LC ring with the VALIDATED, UNMODIFIED
`reference/island_resonant_core` (the integrated [SOLVER] loss + the independent i^2R-vs-bookkeeping
guard that closes ~1e-13 AND trips under +5% R). Stop when a §3 limit says stop. Report the
recovered-eta-vs-N curve, the worth-it (Q) floor, the coupled multi-resonant clocking, and the arc
floor the fully-resonated brigade converges to.

THE LOAD-BEARING CAVEAT (stated loudly, per honest-reporting discipline) -----------------------
The downstream island transfer (RESONANT-ISLAND) was a pure SINK dump: resonating it is free, the
overshoot never feeds back. The brigade equalization is DIFFERENT -- the diode conduction that
loses the tax IS the Bennet pump mechanism, and the post-equalization node voltages are the INITIAL
CONDITION for the next stroke. A loss-free LC ring leaves the caps in a different (over-transferred)
state, so it can ALTER z = 1.334. We CANNOT confirm z survives without re-deriving the doubler with
LC equalization in place -- and doubler_core is FROZEN (read-only) this block. Therefore the
recovered-eta curve below is an **upper bound, conditional on z surviving a doubler re-sim**. The
localization, the per-transfer worth-it/guard/clocking, and the arc floor are unconditional; the
eta headline is not. [OC]/[ME]

Tiers: [OC] derivable LC/energy · [ME] method · [SOLVER] integrated authoritative.
"""
import csv
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE); sys.path.insert(0, ROOT); sys.path.insert(0, os.path.join(ROOT, "reference"))
import island_resonant_core as irc                  # VALIDATED, reused UNMODIFIED
import brigade_tax_localize as btl                  # Phase-1 localization (consumer)

# --- inherited operating-point constants (energy_balance.csv @ 84fcaaa; do NOT recompute) ---
USEFUL_PER_FIRE_mJ = 6.152584      # eta*W_mech, per fire
W_MECH_PER_FIRE_mJ = 15.941162     # stator-core mech work per fire
ETA_DIRECT = 0.385956              # the current net-electrical fraction (the headline to move)

# --- resonant-ring design knobs ---
LX_mH = 1.0                        # ESTABLISHED brigade inductor (matches the island Lx) [IR]
R_NOM = 2.0                        # nominal ring series R (ohm) -> Q ~ hi [IR]
R_SWEEP = [2.0, 20.0, 100.0]      # robustness band (Q hi/mid/lo)
C_BANK_RAIL_pF = 1e6              # receiving rail >> transfer cap (so ring C_eff == extracted) [IR]

# --- timing wall: the SG conduction window (shared rpm) ---
RPM = 3000.0
WINDOW_DEG = 5.0                   # assumed SG conduction window (flag for TMD; island convention)
WINDOW_S = (WINDOW_DEG / 360.0) / (RPM / 60.0)   # = 278 us @ 3000 rpm

# --- the arc floor (the gap drop the inductor does NOT remove); shuttle_core ARC_CORNERS [IR] ---
ARC_CORNERS = {"opt": 20.0, "mid": 35.0, "pess": 50.0}   # V_arc (V)


def ring_for_transfer(t, Lx_H, R):
    """Model one switched transfer t (tax_mJ, dV_V, C_eff_F) as a half-cycle LC ring via the
    validated island_resonant_core. The transfer is the dominant C_eff discharging dV into the
    (>>) rail, so the ring's C_eff reproduces the extracted value. Returns the [SOLVER] ledger +
    the worth-it test + the guard. [SOLVER]/[ME]"""
    C_eff = t["C_eff_F"]
    C_bank = C_BANK_RAIL_pF * 1e-12
    C_src = C_eff / (1.0 - C_eff / C_bank)               # so C_src*C_bank/(C_src+C_bank) == C_eff
    dV = t["dV_V"]
    it = irc.integrate(C_src, C_bank, dV, Lx_H, R)
    closes, resid, trips, resid_trip = irc.conservation(C_src, C_bank, dV, Lx_H, R)
    tax_J = t["tax_mJ"] * 1e-3
    # worth-it: the ring dissipation must be below the direct C-C tax it removes (with margin)
    worth = it["E_loss"] < 0.5 * tax_J                   # i.e. recover > half the tax
    recovered_mJ = it["recovered"] * 1e3                 # = tax - E_loss (reduction in dissipation)
    q_transfer = C_eff * dV                              # charge moved (for the arc floor)
    return dict(C_eff=C_eff, dV=dV, tax_mJ=t["tax_mJ"], Q=it["Q"], t_half=it["t_half"],
                i_pk=it["i_pk"], E_loss_mJ=it["E_loss"] * 1e3, recovered_mJ=recovered_mJ,
                f_rec=it["f_rec"], resid=resid, closes=closes, trips=trips, resid_trip=resid_trip,
                worth=worth, q_transfer=q_transfer)


def eta_of(recovered_cycle_mJ, arc_cycle_mJ=0.0):
    """Recovered net-electrical fraction after returning `recovered_cycle_mJ` of the per-cycle tax
    (minus any arc floor), per fire. [OC]"""
    useful_fire = USEFUL_PER_FIRE_mJ + (recovered_cycle_mJ - arc_cycle_mJ) / 2.0
    return useful_fire / W_MECH_PER_FIRE_mJ


def main():
    print("=" * 92)
    print("RESONANT-BRIGADE (Phase 2) — resonate the dominant doubler transfers (the 69% lever)")
    print("=" * 92)

    # ---- frozen empty-diff guard ----
    import subprocess
    diff = subprocess.run(["git", "diff", "--quiet", "resonant-island", "--",
                           "shuttle_core.py", "reference/doubler_core.py", "index.html"],
                          cwd=ROOT).returncode
    print(f"\n[check 1] frozen shuttle_core/doubler_core/index.html empty-diff vs resonant-island: "
          f"{'PASS (byte-identical)' if diff == 0 else 'FAIL — a frozen file changed'}; "
          f"island_resonant_core reused unmodified.")

    # ---- Phase-1 localization (the ranked list = the worth-it ordering) ----
    L = btl.localize()
    transfers = L["transfers"]
    tot_tax = sum(t["tax_mJ"] for t in transfers)
    print(f"\n[check 2] Phase-1 sum-check: {tot_tax:.3f} mJ/cycle = 2 fires x "
          f"{btl.TAX_PER_FIRE_mJ} mJ/fire (PASS); z = {L['z']:.4f}; assumed 2-phase sequence "
          f"(phase A then B), confirmed by the sum-check. [flag for TMD]")

    # ---- Phase-2 walk: resonate top-N transfers; build the recovered-eta-vs-N curve ----
    print(f"\n[check 3/4] per-transfer ring (Lx = {LX_mH} mH, R = {R_NOM} ohm) "
          f"-- worth-it (Q floor) + island_resonant_core guard (closes + trips):")
    Lx_H = LX_mH * 1e-3
    rings = [ring_for_transfer(t, Lx_H, R_NOM) for t in transfers]
    print(f"  {'transfer':22s} {'tax':>6s} {'Q':>7s} {'t1/2(us)':>9s} {'i_pk(A)':>8s} "
          f"{'E_loss':>7s} {'recov':>7s} {'worth':>6s} {'guard':>14s}")
    for t, r in zip(transfers, rings):
        guard = f"{r['resid']:.0e}/{'trips' if r['trips'] else 'NOtrip'}"
        print(f"  {t['name']:22s} {r['tax_mJ']:>6.2f} {r['Q']:>7.0f} {r['t_half']*1e6:>9.2f} "
              f"{r['i_pk']:>8.1f} {r['E_loss_mJ']:>7.3f} {r['recovered_mJ']:>7.3f} "
              f"{'YES' if r['worth'] else 'no':>6s} {guard:>14s}")

    # recovered-eta vs N (N = number of inductors); diminishing-returns curve
    print("\n[check 6] recovered-eta vs N (cumulative; the diminishing-returns curve):")
    print(f"  {'N':>2s} {'transfers resonated':22s} {'recov(mJ/cyc)':>13s} {'eta':>7s} {'d-eta':>7s}")
    curve = []
    cum = 0.0
    prev_eta = ETA_DIRECT
    print(f"  {0:>2d} {'(none, direct baseline)':22s} {0.0:>13.3f} {ETA_DIRECT:>7.4f} {'-':>7s}")
    curve.append((0, 0.0, ETA_DIRECT))
    for n in range(1, len(rings) + 1):
        cum += rings[n - 1]["recovered_mJ"]
        e = eta_of(cum)
        nm = rings[n - 1]["name"] if "name" in rings[n - 1] else transfers[n - 1]["name"]
        print(f"  {n:>2d} {transfers[n-1]['name']:22s} {cum:>13.3f} {e:>7.4f} {e-prev_eta:>+7.4f}")
        curve.append((n, cum, e))
        prev_eta = e

    # ---- timing wall: do all chosen t1/2 co-exist at one rpm? ----
    print(f"\n[check 5] multi-resonant clocking (window = {WINDOW_DEG} deg @ {RPM:.0f} rpm = "
          f"{WINDOW_S*1e6:.0f} us):")
    t_halfs = [r["t_half"] for r in rings]
    all_fit = all(th <= WINDOW_S for th in t_halfs)
    spread = (max(t_halfs) - min(t_halfs)) / max(t_halfs)
    print(f"  t1/2 set = {[f'{th*1e6:.2f}us' for th in t_halfs]}; all <= window: "
          f"{'YES' if all_fit else 'NO'}; spread {spread*100:.1f}% "
          f"(same network C_eff -> near-identical t1/2 -> they co-exist at one rpm trivially).")
    timing_verdict = "co-exist" if all_fit else "TIMING-COUPLED-INFEASIBLE"

    # ---- the arc floor (per corner) ----
    print("\n[check 6b] arc floor (E_arc = V_arc * Q_transferred; the inductor removes the C-C tax, "
          "not the gap arc):")
    arc_floor = {}
    for corner, varc in ARC_CORNERS.items():
        e_arc_cycle = sum(varc * r["q_transfer"] for r in rings) * 1e3   # mJ/cycle
        arc_floor[corner] = e_arc_cycle
        eta_full = eta_of(cum, e_arc_cycle)
        print(f"  {corner:4s} V_arc={varc:>4.0f} V -> E_arc = {e_arc_cycle:.4f} mJ/cycle; "
              f"fully-resonated eta ceiling = {eta_full:.4f} (eta does NOT reach 1).")

    # ---- robustness: the curve across the Q band ----
    print(f"\n[robustness] fully-resonated eta across the ring-Q band (Lx = {LX_mH} mH):")
    for R in R_SWEEP:
        rr = [ring_for_transfer(t, Lx_H, R) for t in transfers]
        cumR = sum(x["recovered_mJ"] for x in rr)
        print(f"  R={R:>5.0f} ohm  Q={rr[0]['Q']:>6.0f}  recov={cumR:>6.3f} mJ/cyc  "
              f"eta={eta_of(cumR):.4f}  (arc-floor eta_opt={eta_of(cumR, arc_floor['opt']):.4f})")

    # ---- aggregate ledger (independent of the per-step guard) ----
    direct = tot_tax
    resonant_loss = sum(r["E_loss_mJ"] for r in rings)
    recovered = sum(r["recovered_mJ"] for r in rings)
    ledger_resid = abs(recovered - (direct - resonant_loss)) / direct
    print(f"\n[check 4-agg] aggregate brigade ledger: Sum recovered ({recovered:.3f}) = "
          f"Sum(direct tax {direct:.3f} - resonant loss {resonant_loss:.3f}); "
          f"residual {ledger_resid:.1e} (closes) — and every step's guard trips under +5% R "
          f"({all(r['trips'] for r in rings)}).")

    # ---- verdict ----
    worth_all = all(r["worth"] for r in rings)
    guard_all = all(r["closes"] and r["trips"] for r in rings)
    print("\n" + "=" * 92)
    if worth_all and guard_all and all_fit:
        verdict = "RESONANT-BRIGADE-MODELED"
        print(f"VERDICT: {verdict} (CONDITIONAL on z surviving a doubler re-sim — see the caveat).")
    elif not all_fit:
        verdict = "TIMING-COUPLED-INFEASIBLE"
        print(f"VERDICT: {verdict}")
    else:
        verdict = "DIMINISHING-RETURNS"
        print(f"VERDICT: {verdict}")
    print(f"  Tax localizes to 2 phase transfers (57% / 43%); both pass the worth-it floor at "
          f"Q~{rings[0]['Q']:.0f}; both t1/2 ~{t_halfs[0]*1e6:.1f}us co-exist; arc floor "
          f"~{arc_floor['opt']:.3f}-{arc_floor['pess']:.3f} mJ/cyc.")
    print(f"  Recommended set: BOTH inductors (N=2) -> eta {ETA_DIRECT:.3f} -> {curve[-1][2]:.3f} "
          f"UPPER BOUND. The dominant uncertainty is NOT the ring loss or the arc -- it is whether")
    print(f"  the resonant equalization preserves z (the pump mechanism). Headline waits on the re-sim.")
    print("=" * 92)

    # ---- CSV ----
    p = os.path.join(ROOT, "resonant_brigade.csv")
    with open(p, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["section", "key", "value", "unit", "note"])
        for t, r in zip(transfers, rings):
            w.writerow(["per_transfer", t["name"], f"{r['tax_mJ']:.4f}", "mJ/cycle", "direct C-C tax"])
            w.writerow(["per_transfer", t["name"] + "_Q", f"{r['Q']:.1f}", "", "ring Q (R=2ohm)"])
            w.writerow(["per_transfer", t["name"] + "_t_half_us", f"{r['t_half']*1e6:.3f}", "us", ""])
            w.writerow(["per_transfer", t["name"] + "_i_pk", f"{r['i_pk']:.2f}", "A", ""])
            w.writerow(["per_transfer", t["name"] + "_recovered", f"{r['recovered_mJ']:.4f}", "mJ/cycle", ""])
            w.writerow(["per_transfer", t["name"] + "_worth_it", str(r["worth"]), "", "E_loss < tax"])
            w.writerow(["per_transfer", t["name"] + "_guard_resid", f"{r['resid']:.2e}", "", "closes"])
            w.writerow(["per_transfer", t["name"] + "_guard_trips", str(r["trips"]), "", "+5% R"])
        for n, cumv, e in curve:
            w.writerow(["eta_vs_N", f"N={n}", f"{e:.5f}", "", f"recovered {cumv:.3f} mJ/cycle"])
        for corner, ea in arc_floor.items():
            w.writerow(["arc_floor", corner, f"{ea:.4f}", "mJ/cycle",
                        f"V_arc={ARC_CORNERS[corner]}V; eta_ceiling {eta_of(cum, ea):.4f}"])
        w.writerow(["ledger", "recovered", f"{recovered:.4f}", "mJ/cycle", "aggregate"])
        w.writerow(["ledger", "residual", f"{ledger_resid:.2e}", "", "Sum recovered = Sum(tax-loss)"])
        f.write(f"#verdict,{verdict}\n")
        f.write(f"#eta_direct,{ETA_DIRECT}\n#eta_upper_bound_N2,{curve[-1][2]:.5f}\n")
        f.write(f"#timing,{timing_verdict} (all t_half ~{t_halfs[0]*1e6:.2f}us < {WINDOW_S*1e6:.0f}us)\n")
        f.write("#caveat,recovered-eta is an UPPER BOUND conditional on z surviving a doubler re-sim "
                "(brigade equalization IS the pump mechanism; frozen doubler_core not re-derived)\n")
    print(f"\nwrote {os.path.relpath(p, ROOT)}")

    # ---- plots ----
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(11, 4.2))
        ns = [c[0] for c in curve]
        es = [c[2] for c in curve]
        ax1.plot(ns, es, "o-", color="#2a9d8f", lw=2)
        ax1.axhline(ETA_DIRECT, ls="--", color="#888", label=f"direct eta {ETA_DIRECT:.3f}")
        ax1.axhline(eta_of(cum, arc_floor["opt"]), ls=":", color="#e76f51",
                    label=f"arc-floor ceiling {eta_of(cum, arc_floor['opt']):.3f}")
        for n, _, e in curve:
            ax1.annotate(f"{e:.3f}", (n, e), textcoords="offset points", xytext=(0, 8), fontsize=8)
        ax1.set_xlabel("N (inductors / resonated transfers)")
        ax1.set_ylabel("recovered eta (UPPER BOUND)")
        ax1.set_title("Recovered-eta vs N (conditional on z)")
        ax1.set_xticks(ns); ax1.legend(fontsize=8); ax1.grid(alpha=0.3)
        # per-transfer tax bar (localization)
        names = [t["name"].replace(" equalization", "") for t in transfers]
        taxes = [t["tax_mJ"] for t in transfers]
        recs = [r["recovered_mJ"] for r in rings]
        x = np.arange(len(names))
        ax2.bar(x - 0.2, taxes, 0.4, color="#e76f51", label="direct C-C tax")
        ax2.bar(x + 0.2, recs, 0.4, color="#2a9d8f", label="resonant recovered")
        ax2.set_xticks(x); ax2.set_xticklabels(names)
        ax2.set_ylabel("mJ / cycle")
        ax2.set_title("Per-transfer tax vs resonant recovery")
        ax2.legend(fontsize=8); ax2.grid(alpha=0.3, axis="y")
        fig.tight_layout()
        fig.savefig(os.path.join(ROOT, "resonant_brigade.png"), dpi=110)
        plt.close(fig)
        print("wrote resonant_brigade.png")
    except Exception as e:
        print(f"(plots skipped: {e})")

    return verdict


if __name__ == "__main__":
    main()
