# Findings — electromechanical energy balance → **ENERGY-BALANCE-CLOSES · EQUALIZATION-TAX-PRESENT**

**Branch** `energy-balance` (off `s2recheck-s3-spark` `c1754da`, the 789 pF / 12 mm-disc operating point).
**Verdict line:** `ENERGY-BALANCE-CLOSES` (identity residual 1.4×10⁻¹⁶) · `EQUALIZATION-TAX-PRESENT`
(61.4 % of shaft work) · η_conv = **0.386** (core) · τ-ripple **7.8** — both reported, not pass/fail.

Consumer-only: `reference/doubler_core.py`, `shuttle_core.py`, `index.html` **byte-identical to the base**
(0 producer edits, asserted). The module reads the FROZEN `solve_doubler4(trace=True)` ("traceDoubler4")
and reuses the frozen `charges_from_voltages`; it recomputes **no** electrical solve — the only linear
algebra is the *constant-charge* cap-change step (pure mechanics, no diodes) and energy bookkeeping.
Mainstream electromechanics only (no DCCREG). This is a **second conservation law** (energy) laid over the
charge-law z campaign — de Queiroz's z explicitly excludes electromechanical forces, so this fills that gap.

---

## Base-branch confirmation (brief: "flag if the 789 pF head isn't where expected")

The 789 pF / 12 mm-disc operating point is split across two heads, and the brief's "geometry/freeze head"
needs disambiguating:
- **`freeze-v0.10`** carries the 789 pF **design** (the `varcap-design-freeze-v0.10.md` doc) but **not** a
  runnable preset.
- **`s2recheck-s3-spark`** carries the runnable **operating-point preset** `presets/G3-geometry-v010.json`
  (`cR = 789`, the 12 mm disc; C1/C2 16/280, Ca/Cb 309, Cpar 20) **plus** the tank/sim infrastructure.

So the correct **computational** base is `s2recheck-s3-spark` — flagged, and built there. (Both descend from
`effcee1`; the new `sim-evidence-consolidated` branch is a superset but is not "the freeze head".)

---

## 1. Method — what is computed, and why it is consumer-only

The frozen `solve_doubler4(trace=True)` returns the full per-phase trajectory of the 4-node galvanic core:
each cycle holds the node charge `Q = charges_from_voltages(V, old caps)`, changes the rotor caps, and
`solve_phase` lands the diode equilibrium. Injected with the **G3 geometry caps**, the core pumps at
**z = 1.334** (= the known galvanic ceiling — independent cross-check).

For each transition the stored-energy change is split into two physically distinct pieces:

| Segment | What happens | Energy |
|---|---|---|
| **mechanical stroke** | caps change at **constant node charge** (diodes off, plates separating) | `W_mech = U(Q, C_new) − U(Q, C_old)` |
| **diode-conduction step** | caps fixed; charge redistributes / drains to rail (the merge) | `E_tax = U(pre-diode) − U(post-diode) ≥ 0` |

The pre-diode endpoint `V_int` is obtained by the **constant-Q** solve `M(C_new)·V_int = Q` (the cap matrix
`M` = ∂Q/∂V of the frozen `charges_from_voltages`) — pure mechanics, no diode logic, so this is **read +
arithmetic**, not a re-solve. Energy `U = ½ Σ_caps C·ΔV² = ½ V·Q`.

**The per-cycle identity is exact by construction (telescoping U):**
```
W_mech,cycle  =  ΔE_stored,cycle  +  E_tax,cycle
```
so the deliverable is the **decomposition** (how much is stored vs taxed), not that it closes (it must).

## 2. Results (G3 operating geometry, steady eigen-window cycles 90–150)

**The load-bearing test — the identity closes to machine precision:**
```
identity residual  max |W_mech − (ΔE_stored + E_tax)| / W_mech  =  1.4×10⁻¹⁶
```
**Eigen-growth cross-check (independent):** the per-cycle stored-energy gain `ΔE_stored / U_start =
0.7796` equals **z² − 1 = 0.7796** to **2×10⁻¹⁶** — the energy bookkeeping reproduces the charge-law pump
growth exactly. This is the orthogonal (energy-law) confirmation the brief sought: **the z campaign is
energetically self-consistent.**

**The decomposition (scale-free, per cycle):**

| Fraction of W_mech | value | meaning |
|---|---|---|
| **ΔE_stored / W_mech** | **0.386** | useful pumped electrical energy (the z²-growth) = **η_conv** |
| **E_tax / W_mech** | **0.614** | equalization tax — capacitive merge loss, even with **ideal** diodes |

⇒ **`EQUALIZATION-TAX-PRESENT`** (the named sub-outcome): the ideal charge-conservation transfer carries a
**real, quantified** capacitive-equalization loss the charge-only (z) analysis never showed — **61.4 % of the
mechanical shaft work** at the G3 swing (z = 1.334). This is the two-capacitor paradox manifesting at every
diode merge: charge sloshing into the rail/ground node at unequal potential dissipates ½C·ΔV² with no
resistor needed. **η_conv = 38.6 %** is therefore the electromechanical conversion efficiency of the stator
doubler core. *(Positive control: self-test (c) shows the localizer recovers a known ½·(C₁C₂/(C₁+C₂))·ΔV²
merge tax to machine precision, so the 61.4 % is a real tax, not a bookkeeping artifact.)*

## 3. Absolute scale + the honest η scope `[IR]`

Anchoring the peak rail node to **V_peak = 15 kV** (the governor clamp): per fire the stator core does
**W_mech ≈ 15.9 mJ**, of which **≈ 6.2 mJ** is useful (η_conv) and **≈ 9.8 mJ** is taxed. The tank
accumulator holds `E_tank = ½·C_R·V_peak² = ` **88.8 mJ** at 789 pF / 15 kV (matches the S3 reach floor of
89 mJ — self-test (e)).

**Scope flag (reported, not buried):** the bare 4-node core's per-fire work (15.9 mJ) is **much smaller**
than the 89 mJ tank kick, because the kick is dominated by the **island Cx-collapse boost** (the flying
bucket, nodes 7/8 in `shuttle_core`), which is **not** part of this stator core. So the meaningful
efficiency is the **core conversion η_conv = ΔE_stored/W_mech**, *not* the cross-layer `E_tank/W_mech`
(which exceeds 1 and is therefore not an efficiency — a deliberate tell, surfaced not smoothed). A full
machine-level η that folds in the island mechanical work is the natural next block (it needs the
shuttle-layer trace, out of this core's scope).

## 4. Retarding torque τ(θ) — the motor load (soft, separable) `[IR]`

Over one complementary-**linear** rotor sweep at constant node charge, τ(θ) = dU/dθ. Mean τ = W_mech/Δθ
(self-test (d), exact), **ripple factor ≈ 7.8** (the torque is strongly peaked where C is small and the
voltage high). This is the load Block D must overcome; it is the **only** quantity that uses `dC/dθ`, so it
is **shape-dependent** and kept strictly separate from the hard energy verdict (see the robustness split).

## 5. Robustness split (brief §2)

The **energy balance, η_conv, and the identity use only segment endpoints** — ½Q²·Δ(1/C) is
path-independent at constant Q — so they are **robust to the C(θ) shape**. Only **τ(θ) uses dC/dθ** (the
complementary-linear law). A soft torque-ripple shape therefore **cannot** contaminate the hard energy
verdict; the two are reported separately. The ideal lossless energy core is **corner-independent**
(opt/mid/pess differ only through arc/leakage losses, which are not in the ideal trace); folding the arc
ledger in for a lossy-corner η is the natural follow-on the brief anticipates.

## 6. Verdicts (pre-committed)

- **`ENERGY-BALANCE-CLOSES`** ✓ — W_mech reconciles with ΔE_stored + E_tax to **1.4×10⁻¹⁶** (machine
  precision); the eigen-growth ΔE_stored/U_start = z²−1 to 2×10⁻¹⁶. Energy conservation holds; the charge
  (z) campaign is energetically self-consistent — an independent confirmation by a second conservation law.
- **`EQUALIZATION-TAX-PRESENT`** ✓ — quantified at **61.4 %** of W_mech (η_conv = 38.6 %) at the G3 swing.
  A real efficiency tax the charge-only analysis could not see — the more informative of the two sub-outcomes.
- **`ENERGY-BALANCE-GAP`** — **not triggered**: no finite residual beyond the (now-quantified) tax.
- **η_conv = 0.386 · τ-ripple ≈ 7.8** — reported quantities (the conversion efficiency and the motor load).

## 7. Deliverables

`energy_balance_from_solver.py` (consumer + 5 self-tests) · `energy-balance-findings.md` (this) ·
`energy_balance.csv` · `energy_balance_flow.png` (W_mech → ΔE_stored + E_tax bar) · `energy_balance_tau.png`
(τ(θ) profile). Frozen modules byte-identical; 0 producer edits; **not merged** — left for TMD review.
