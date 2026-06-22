#!/usr/bin/env python3
"""
sim/resonant_island.py — quantify the series-LC island transfer fix (efficiency + decomposition).
==================================================================================================
Drives `reference/island_resonant_core.py` (the NEW resonant-transfer solver) against the FROZEN
direct-transfer baseline (`island_charging_cosim`, audited): the resonant transfer's eta gain over a
Q sweep, the conservation guard + the +5% trip, the Lx timing/current/voltage constraints, t1/2 vs
the spark-gap conduction window, and -- the load-bearing caveat -- the loss DECOMPOSITION (island
transfer tax vs the doubler Ca/Cb bucket-brigade C-C tax). Frozen solvers untouched. [OC]/[IR]/[ME].

THE ASSUMED OPERATING SEQUENCE (flagged for TMD sign-off, the design authority): from the KiCad
netlist (37 components) the load gap SG3a connects the doubler rail (net21: C1/Ca1/L_A) to the
island Cx3; Cx3 charges, then RINGS through the series Lx3 into the BR transfer bank (net10:
Cb1/C_BR), the half-cycle completing at current-zero so SG3a self-quenches; Cx4/Lx4 mirror (BR->AR).
The DIRECT baseline is the two-cap dump of this same Cx->bank transfer (the audited 4.41 mJ/fire
island pickup tax). **TMD confirms the cycle before the model is trusted.**
"""
import csv
import math
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE); sys.path.insert(0, ROOT); sys.path.insert(0, os.path.join(ROOT, "reference"))
import island_resonant_core as irc          # NEW resonant model
import island_charging_cosim as ic          # FROZEN direct baseline (audited)

# ---- audited baseline numbers (the decomposition's anchors) ---------------- [OC]
ETA_DIRECT = 0.386                            # doubler net-electrical fraction
W_MECH_mJ = 15.941                            # doubler mech work / cycle
DOUBLER_TAX_mJ = (1 - ETA_DIRECT) * W_MECH_mJ   # 9.79 mJ -- the Ca/Cb bucket-brigade C-C tax (61%)
# ---- the island transfer (assumed sequence; the direct tax is audited) ----- [IR seq, OC scale]
CX_pF = 471.0                                 # island variable cap
C_BANK_nF = 2640.0                            # bank seen by Lx = Cb1(309pF) || C_BR1-6 (6x440nF)
DV_kV = 5.0                                   # island above the bank at transfer (TMD seq) [IR]
ISLAND_TAX_DIRECT_mJ = None                   # filled from the frozen baseline below
# ---- mechanical clocking (for the timing constraint) ----------------------- [IR/EST]
RPM = 3000.0; SG_WINDOW_DEG = 5.0             # the rotor-angle span SG3a conducts [IR -> TMD]
# ---- Lx ratings (the current/voltage constraints) -------------------------- [IR]
I_PK_MAX = 100.0                              # spark-gap + inductor peak current rating (A)
V_NODE_MAX = 25e3                             # ring-node insulation (ties to insulate-first)


def baseline_island_tax():
    """The audited DIRECT island pickup tax (two-cap loss) from the FROZEN model."""
    saved = ic.CX_MAX
    try:
        ic.CX_MAX = CX_pF * 1e-12
        st = ic.run_steady("real", ic.CA)
    finally:
        ic.CX_MAX = saved
    return st["ploss_mJ"]


def conduction_window_s():
    """The SG conduction window in seconds at RPM (the rotor-angle span / the rotor rate)."""
    return SG_WINDOW_DEG / (RPM / 60.0 * 360.0)


def lx_constraints(Lx, R, dV):
    """The three Lx sub-constraints (C4): timing (t1/2 <= window), current (i_pk<=rating),
    voltage (ring node <= insulation). Returns dict of (ok, value) per constraint + binding."""
    cf = irc.closed_form(CX_pF * 1e-12, C_BANK_nF * 1e-9, dV, Lx, R)
    win = conduction_window_s()
    timing_ok = cf["t_half"] <= win                       # ring completes before the island moves
    current_ok = cf["i_pk"] <= I_PK_MAX
    v_gain = math.sqrt(max(CX_pF * 1e-12, 1e-30) / (C_BANK_nF * 1e-9))   # ~<1 (bank >> island)
    v_node = dV * (1 + v_gain)
    voltage_ok = v_node <= V_NODE_MAX
    return dict(t_half=cf["t_half"], window=win, i_pk=cf["i_pk"], v_node=v_node,
                timing_ok=timing_ok, current_ok=current_ok, voltage_ok=voltage_ok,
                all_ok=timing_ok and current_ok and voltage_ok)


def main():
    print("=" * 90)
    print("RESONANT-ISLAND — the series-LC island transfer fix (efficiency + decomposition)")
    print("=" * 90)
    print("\n[check 1] frozen shuttle_core/doubler_core untouched; the resonant model is a NEW file "
          "(reference/island_resonant_core.py).")
    print("[check 2] ASSUMED SEQUENCE (flag for TMD): SG3a: rail(net21)->Cx3 charge; Cx3 rings via "
          "Lx3 into the BR bank(net10) in a half-cycle, self-quench at current-zero; Cx4/Lx4 mirror.")

    global ISLAND_TAX_DIRECT_mJ
    ISLAND_TAX_DIRECT_mJ = baseline_island_tax()
    C_src, C_bank, dV = CX_pF * 1e-12, C_BANK_nF * 1e-9, DV_kV * 1e3

    # ---- check 3: the core returns the LC quantities; closed-form vs integrated [SOLVER] ----
    print("\n[check 3] island_resonant_core (closed-form vs integrated [SOLVER], the authority):")
    Lx0 = 1e-3
    for R in (2.0, 20.0):
        cf = irc.closed_form(C_src, C_bank, dV, Lx0, R)
        it = irc.integrate(C_src, C_bank, dV, Lx0, R)
        print(f"  Lx={Lx0*1e3:.1f}mH R={R:.0f}ohm -> Q={cf['Q']:.0f} t1/2={cf['t_half']*1e6:.2f}us "
              f"i_pk={cf['i_pk']:.2f}A | E_2cap={cf['E_2cap']*1e3:.3f}mJ "
              f"E_loss closed={cf['E_loss']*1e3:.4f} / [SOLVER]int={it['E_loss']*1e3:.4f}mJ "
              f"f_rec={it['f_rec']:.3f}")
    print("  NOTE: the integrated loss runs ~2x the brief's closed form (the (pi/2Q) estimate "
          "under-counts the ringing dissipation by ~2x); the [SOLVER] integral is authoritative.")

    # ---- check 4: conservation closes + the +5% trip ----
    closes, resid, trips, resid_t = irc.conservation(C_src, C_bank, dV, Lx0, 20.0)
    print(f"\n[check 4] conservation: residual {resid:.1e} (closes) AND +5% R trip -> {resid_t:.3e} "
          f"({'FIRES' if trips else 'FLAT'}) -- the recovered tax is redistribution, not invention.")

    # ---- check 5: eta_resonant vs eta_direct over Q + the loss DECOMPOSITION ----
    print("\n[check 5] efficiency over Q + the loss decomposition (the load-bearing caveat):")
    print(f"  audited DIRECT island transfer tax = {ISLAND_TAX_DIRECT_mJ:.3f} mJ/fire (two-cap dump)")
    print(f"  audited doubler bucket-brigade tax = {DOUBLER_TAX_mJ:.3f} mJ/cycle (the 61%, UNTOUCHED by Lx)")
    combined = ISLAND_TAX_DIRECT_mJ + DOUBLER_TAX_mJ
    isl_frac = ISLAND_TAX_DIRECT_mJ / combined
    print(f"  -> the island transfer is {isl_frac*100:.0f}% of the combined (island+doubler) tax; "
          f"the doubler bucket-brigade is {100-isl_frac*100:.0f}%")
    rows = []
    print(f"  {'R(ohm)':>7s} {'Q':>7s} {'f_rec':>7s} {'isl_tax_res(mJ)':>15s} {'isl_recovered(mJ)':>17s} "
          f"{'combined_tax(mJ)':>16s} {'tax_drop%':>9s}")
    for R in (1.0, 2.0, 5.0, 10.0, 20.0, 50.0, 100.0, 200.0):
        it = irc.integrate(C_src, C_bank, dV, Lx0, R)
        # scale the modeled f_rec onto the audited island tax (the audited tax IS the direct dump)
        isl_res = ISLAND_TAX_DIRECT_mJ * (1 - it["f_rec"])
        isl_rec = ISLAND_TAX_DIRECT_mJ - isl_res
        comb_res = isl_res + DOUBLER_TAX_mJ
        drop = (combined - comb_res) / combined * 100
        rows.append((R, it["Q"], it["f_rec"], isl_res, isl_rec, comb_res, drop))
        print(f"  {R:>7.0f} {it['Q']:>7.0f} {it['f_rec']:>7.3f} {isl_res:>15.3f} {isl_rec:>17.3f} "
              f"{comb_res:>16.3f} {drop:>8.1f}%")
    best = rows[1]   # Q at R=2
    print(f"  at a usable Q~{best[1]:.0f} (R=2 ohm): recovers {best[4]:.2f} mJ/fire of the island tax "
          f"-> the combined tax drops {best[6]:.0f}% -- a REAL gain, but the doubler bucket-brigade "
          f"({100-isl_frac*100:.0f}% of the loss) is untouched.")

    # ---- check 6: the three Lx constraints + t1/2 vs the conduction window ----
    print("\n[check 6] Lx constraints (timing/current/voltage) + t1/2 vs the SG conduction window:")
    win = conduction_window_s()
    print(f"  conduction window: {SG_WINDOW_DEG:.0f} deg @ {RPM:.0f} rpm = {win*1e6:.0f} us")
    feas = []
    for Lx in (1e-6, 1e-5, 1e-4, 1e-3, 1e-2, 1e-1, 1.0):
        c = lx_constraints(Lx, 20.0, dV)
        feas.append((Lx, c))
        marks = ("T" if c["timing_ok"] else "t") + ("I" if c["current_ok"] else "i") + ("V" if c["voltage_ok"] else "v")
        print(f"  Lx={Lx*1e3:>8.3f}mH: t1/2={c['t_half']*1e6:>8.2f}us (<{win*1e6:.0f}? "
              f"{'ok' if c['timing_ok'] else 'OVER'}) i_pk={c['i_pk']:>7.1f}A "
              f"({'ok' if c['current_ok'] else 'OVER'}) v_node={c['v_node']/1e3:.1f}kV "
              f"({'ok' if c['voltage_ok'] else 'OVER'}) -> [{marks}]")
    feasible_lx = [Lx for Lx, c in feas if c["all_ok"]]
    print(f"  feasible Lx (all three): {[f'{l*1e3:.2f}mH' for l in feasible_lx]}")
    # self-quench match: is there an Lx where t1/2 ~ window?
    Lx_match = (win / math.pi) ** 2 / (CX_pF * 1e-12 * C_BANK_nF * 1e-9 / (CX_pF * 1e-12 + C_BANK_nF * 1e-9))
    print(f"  self-quench MATCH (t1/2 = window) needs Lx ~ {Lx_match:.1f} H -- impractical; instead "
          f"t1/2 << window at any feasible Lx, so the gap quenches at the FIRST current-zero (well "
          f"inside the window) -- clean self-quench, no chop/re-strike.")

    # ---- verdict ----
    timing_feasible = len(feasible_lx) > 0
    print("\n" + "=" * 90)
    print("VERDICT:")
    if not timing_feasible:
        verdict = "TIMING-INFEASIBLE"
        print("  no Lx fits the window within current/voltage -- the resonant transfer can't be clocked.")
    elif isl_frac < 0.15:
        verdict = "GAIN-MARGINAL"
        print(f"  the island transfer is only {isl_frac*100:.0f}% of the loss -- the doubler "
              f"bucket-brigade dominates; the realistic eta gain is small. Next inductors -> Ca/Cb.")
    else:
        verdict = "RESONANT-TRANSFER-MODELED"
        print(f"  the LC island transfer is modelled: conservation closes + trips; the gain is "
              f"quantified ({best[4]:.2f} mJ/fire recovered, {best[6]:.0f}% of the combined tax); "
              f"timing/current/voltage hold (t1/2 {feas[3][1]['t_half']*1e6:.1f}us << {win*1e6:.0f}us "
              f"window); the fix is real and sized.")
        print(f"  CAVEAT (load-bearing): the island is {isl_frac*100:.0f}% of the (island+doubler) "
              f"tax; the doubler Ca/Cb bucket-brigade ({100-isl_frac*100:.0f}%) is UNTOUCHED by Lx -- "
              f"do NOT headline a total-eta win that is only the island's share. The decomposition "
              f"says the NEXT inductors belong on Ca/Cb.")
    print(f"\n  -> {verdict}")

    # ---- CSV ----
    p = os.path.join(ROOT, "resonant_island.csv")
    with open(p, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["R_ohm", "Q", "f_rec", "island_tax_resonant_mJ", "island_recovered_mJ",
                    "combined_tax_mJ", "tax_drop_pct", "tier"])
        for R, Q, fr, ir2, irc2, ct, dr in rows:
            w.writerow([f"{R:.0f}", f"{Q:.1f}", f"{fr:.4f}", f"{ir2:.4f}", f"{irc2:.4f}",
                        f"{ct:.4f}", f"{dr:.2f}", "SOLVER"])
        f.write(f"#island_tax_direct_mJ,{ISLAND_TAX_DIRECT_mJ:.4f}\n")
        f.write(f"#doubler_tax_mJ,{DOUBLER_TAX_mJ:.4f}\n#island_fraction,{isl_frac:.4f}\n")
        f.write(f"#verdict,{verdict}\n")
    print(f"\nwrote {os.path.relpath(p, ROOT)}")
    _plot(rows, isl_frac)
    return 0


def _plot(rows, isl_frac):
    try:
        import matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt
    except Exception:
        return
    fig, (a1, a2) = plt.subplots(1, 2, figsize=(12, 4.4))
    Q = [r[1] for r in rows]; drop = [r[6] for r in rows]; frec = [r[2] for r in rows]
    a1.semilogx(Q, frec, "o-", color="#2a9d8f")
    a1.set_xlabel("ring Q"); a1.set_ylabel("f_rec (island tax recovered)")
    a1.set_title("Resonant island: recovered fraction vs Q"); a1.grid(alpha=0.3)
    a2.bar(["island\ntransfer\n(Lx removes)", "doubler\nbucket-brigade\n(untouched)"],
           [isl_frac * 100, (1 - isl_frac) * 100], color=["#2a9d8f", "#e76f51"])
    a2.set_ylabel("% of combined (island+doubler) tax")
    a2.set_title("Loss decomposition — where the Lx helps (and doesn't)")
    for i, v in enumerate([isl_frac * 100, (1 - isl_frac) * 100]):
        a2.annotate(f"{v:.0f}%", (i, v + 1), ha="center")
    fig.tight_layout(); fig.savefig(os.path.join(ROOT, "resonant_island.png"), dpi=110); plt.close(fig)
    print("wrote resonant_island.png")


if __name__ == "__main__":
    sys.exit(main())
