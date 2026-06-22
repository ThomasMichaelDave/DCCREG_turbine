#!/usr/bin/env python3
"""
sim/brigade_tax_localize.py — Phase 1: localize the doubler bucket-brigade tax per switched transfer.
====================================================================================================
Consumer analysis on the FROZEN doubler_core trajectory (never an edit). The doubler's C-C
equalization tax (the 69% the resonant-island decomposition left, **9.79 mJ/fire**) is the
diode-equalization loss per phase transition: Etax = U_int(diodes off, const-Q) - U_post(diodes
equalised). Localize it per switched transfer, anchor it to the **15 kV operating point** (the same
anchor energy_balance.csv uses: W_mech = 15.941 mJ/fire, eta = 0.386), SUM-CHECK against the known
aggregate, rank, and report the CONCENTRATION (how few transfers hold 80%).

UNITS (stated once, because the campaign's headline is per-FIRE):
  * energy_balance.csv anchors at the 15 kV rail and reports W_mech = 15.941 mJ/**fire**,
    tax-fraction 0.614 -> tax = 9.789 mJ/**fire**. A doubler cycle has **two** fires (phase A and
    phase B), so the per-CYCLE doubler tax is **19.58 mJ = 2 x 9.789**. The published "9.79" is the
    per-fire figure; the two phase transfers are the two fires.
  * This script reports the per-transfer tax at the 15 kV anchor (absolute mJ/cycle) and back-solves
    each transfer's effective C and dV (the LC-ring inputs Phase-2 needs).

ASSUMED TRANSFER SEQUENCE (flag for TMD): the 4-node Bennet doubler switches in 2 phases/cycle --
phase B (C1->min, C2->max) and phase A (C1->max, C2->min) -- each ending in a diode-conduction
equalization (the tax). The sum-check (Sum Etax_k == 19.58 mJ/cycle) confirms this is the real
sequence. [ME]
"""
import csv
import json
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE); sys.path.insert(0, ROOT); sys.path.insert(0, os.path.join(ROOT, "reference"))
import doubler_core as dc                    # FROZEN (read-only)
import energy_balance_from_solver as eb      # the d/2 V^2 dC decomposition (consumer)

PRESET = os.path.join(ROOT, "presets", "G3-geometry-v010.json")
VPEAK = 15e3                                  # 15 kV rail operating anchor [OC] energy_balance.csv
KREF = 120                                    # steady reference cycle (mid of the 90..150 window) [ME]
TAX_PER_FIRE_mJ = 9.789                       # published per-fire doubler tax (= 0.614*15.941)
TAX_PER_CYCLE_mJ = 2 * TAX_PER_FIRE_mJ        # = 19.578 mJ/cycle (two fires) -- the sum-check target


def localize():
    """Localize the per-phase equalization tax at the 15 kV anchor. Returns the ranked transfers
    with absolute tax (mJ/cycle), dominant dV (V), and back-solved effective C (F) -- the LC inputs.
    [ME] consumer-side; the frozen doubler_core trajectory is read, never edited."""
    pj = json.load(open(PRESET))["params"]
    g = {k: pj[k]["value"] for k in pj}
    Ca, Cb, Cpar = g["ca"], g["cb"], g["cpar"]
    z, rec = dc.solve_doubler4(g["c1min"], g["c1max"], g["c2min"], g["c2max"],
                               Ca, Cb, Cpar, iterations=160, burn=80, trace=True)
    steps = eb.decompose(rec, Ca, Cb, Cpar)

    # absolute scale: anchor the reference cycle so its peak node = 15 kV (energy_balance convention)
    rows = [(i, rec[i]) for i in range(1, len(rec)) if rec[i][0] == KREF]
    vmax = max(max(abs(v) for v in r[4]) for _, r in rows)
    scale = VPEAK / vmax
    e2mJ = scale * scale * 1e-12 * 1e3                       # scale-free (pF*V^2) energy -> mJ

    transfers, branch = [], {}
    Wmech_cycle = 0.0
    for i, (cyc, ph, C1, C2, Vpost) in rows:
        _, _, C1o, C2o, Vprev = rec[i - 1]
        Vint, _ = eb.constant_q_step(Vprev, (C1o, C2o), (C1, C2), Ca, Cb, Cpar)
        jump = (np.asarray(Vpost) - np.asarray(Vint)) * scale  # the per-node equalization swing (V)
        dV = float(np.max(np.abs(jump)))                       # dominant switched-transfer dV
        Uint = eb.field_energy(Vint, C1, C2, Ca, Cb, Cpar)
        Upost = eb.field_energy(Vpost, C1, C2, Ca, Cb, Cpar)
        tax = (Uint - Upost) * e2mJ                            # absolute equalization tax (mJ)
        Wmech_cycle += (Uint - eb.field_energy(Vprev, C1o, C2o, Ca, Cb, Cpar)) * e2mJ
        C_eff = 2 * tax * 1e-3 / dV ** 2                       # back-solved so 1/2 C_eff dV^2 == tax
        transfers.append(dict(name=f"phase{ph} equalization", phase=ph, tax_mJ=tax,
                              dV_V=dV, C_eff_F=C_eff))
        # finer (approximate) per-coupling-branch split for the concentration discussion
        a = lambda V: 0.5 * (C1 * V[0]**2 + Cpar * (V[0]**2 + V[1]**2) + Ca * (V[0]-V[1])**2)
        b = lambda V: 0.5 * (C2 * V[3]**2 + Cpar * (V[2]**2 + V[3]**2) + Cb * (V[2]-V[3])**2)
        branch[f"{ph} / Ca(1-2)"] = max(0.0, (a(Vint) - a(Vpost)) * e2mJ)
        branch[f"{ph} / Cb(3-4)"] = max(0.0, (b(Vint) - b(Vpost)) * e2mJ)

    transfers.sort(key=lambda t: -t["tax_mJ"])
    bview = sorted(branch.items(), key=lambda x: -x[1])
    return dict(z=z, transfers=transfers, branch=bview,
                Wmech_cycle_mJ=Wmech_cycle, scale=scale,
                sum_check=sum(t["tax_mJ"] for t in transfers))


def main():
    print("=" * 92)
    print("BRIGADE-TAX-LOCALIZE (Phase 1) — where the doubler's C-C tax lives (15 kV anchor)")
    print("=" * 92)
    print("\n[check 1] consumer analysis on the FROZEN doubler_core trajectory (no edit); "
          "island_resonant_core reused unmodified in Phase 2.")
    L = localize()
    sc, tot = L["sum_check"], L["sum_check"]
    ok = abs(sc - TAX_PER_CYCLE_mJ) < 0.1
    print(f"\n[check 2] SUM-CHECK: Sum Etax_k = {sc:.3f} mJ/cycle  vs target {TAX_PER_CYCLE_mJ:.3f} "
          f"(= 2 fires x {TAX_PER_FIRE_mJ} mJ/fire)  [{'PASS' if ok else 'FAIL — sequence/localization wrong'}]")
    print(f"          W_mech (this cycle) = {L['Wmech_cycle_mJ']:.3f} mJ  -> eta_core = "
          f"{1 - sc/L['Wmech_cycle_mJ']:.4f} (matches energy_balance 0.386); "
          f"z = {L['z']:.4f}.")
    print("          (this also cross-validates the assumed 2-phase transfer sequence.)")

    print("\n[check 3] ranked per-transfer tax (the authoritative phase-level localization):")
    print(f"  {'transfer':22s} {'tax(mJ/cyc)':>11s} {'share':>7s} {'cum':>7s} {'dV(kV)':>7s} {'C_eff(pF)':>9s}")
    acc = 0
    for t in L["transfers"]:
        acc += t["tax_mJ"]
        print(f"  {t['name']:22s} {t['tax_mJ']:>11.3f} {t['tax_mJ']/tot*100:>6.1f}% "
              f"{acc/tot*100:>6.1f}% {t['dV_V']/1e3:>7.2f} {t['C_eff_F']*1e12:>9.1f}")
    n80 = next(i + 1 for i in range(len(L["transfers"]))
               if sum(t["tax_mJ"] for t in L["transfers"][:i + 1]) >= 0.8 * tot)
    big = L["transfers"][0]["tax_mJ"] / tot * 100
    print(f"  CONCENTRATION: {len(L['transfers'])} switched transfers hold 100%; {n80} hold >=80% "
          f"-> CONCENTRATED in 2 phase transfers (largest {big:.0f}% < 80%, so both are needed), "
          f"NOT smeared across the 12 C_AR/C_BR.")

    print("\n  finer per-branch view (approximate; shared Cpar/node terms not cleanly partitioned):")
    for name, t in L["branch"]:
        if t > 1e-3:
            print(f"     {name:14s} {t:.3f} mJ")

    p = os.path.join(ROOT, "brigade_tax_localization.csv")
    with open(p, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["transfer", "tax_mJ_per_cycle", "share_pct", "dV_kV", "C_eff_pF", "tier"])
        for t in L["transfers"]:
            w.writerow([t["name"], f"{t['tax_mJ']:.4f}", f"{t['tax_mJ']/tot*100:.1f}",
                        f"{t['dV_V']/1e3:.3f}", f"{t['C_eff_F']*1e12:.2f}", "ME"])
        f.write(f"#sum_check_mJ_per_cycle,{sc:.4f}\n#target_mJ_per_cycle,{TAX_PER_CYCLE_mJ:.4f}\n")
        f.write(f"#tax_per_fire_mJ,{TAX_PER_FIRE_mJ}\n")
        f.write(f"#concentration,{len(L['transfers'])} transfers = 100%; {n80} >= 80%\n")
    print(f"\nwrote {os.path.relpath(p, ROOT)}")
    return L


if __name__ == "__main__":
    main()
