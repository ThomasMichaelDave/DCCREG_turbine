# Findings — island-charging co-sim: M1 vs M2 resolved, reach re-grounded

**Branch** `island-charging` (off `machine-energy-balance` `05ccf60`). **Verdict:** **`M2-PARTIAL`** —
`ISLAND-FIRE-ENERGY = 14.0 mJ` · `kick-count = 6.5 fires` (single-kick reach **WRONG**, escalate) ·
`η_machine = 0.484` (now **physical**, resolves the prior > 1 paradox).

**The deferred coupling choice, resolved.** Since project start the campaign carried M1-rail-increment vs
M2-island-dump as an *unmade* decision (`s2_coupling.py:14` BLOCKED on it; `run_X1` anchored the island at
20 kV *by assumption*). The prior block then showed that assumption gives η_machine = 7.3 > 1 — impossible.
This co-sim sources the island self-consistently and finds the truth is **neither** pure scheme: the
physical gap fires **mid-collapse** at ~14 mJ/fire, taking **~6–7 fires** to reach the 89 mJ tank. The reach
is real but **multi-fire**, not single-kick.

**Scope:** consumes the frozen cap topology (Cx-swing 8↔648 pF + 8 pF boss, Ca/Cb 309 pF, z = 1.307), the
inherited anchors (η_fire 0.985 @ `05ccf60`, W_mech,stator 15.94 mJ + useful_per_fire 6.15 mJ @ `84fcaaa`),
and V_strike = 20 kV. The **steady-state iteration + the charge/energy ledger are new**. Frozen modules
(`shuttle_core.py`, `reference/doubler_core.py`, `index.html`) **byte-identical** (0 producer edits,
asserted). Ordinary circuit + electromechanics — no DCCREG.

---

## 1. Why charge is decisive `[OC]`

At the strike, **E_fire = ½·Q·V_strike** — set entirely by the **charge Q the rail puts on the island**. The
mechanical collapse only raises V toward the fixed 20 kV strike; it adds no charge. So the whole verdict
reduces to *how much charge/energy the rail sources per cycle*, bounded by **two independent ceilings**:

1. **Charge / dilution** — the 309 pF rail at 20 kV holds ~6.2 µC; when the 648 pF island couples in they
   share to V* = C_rail·V_rail/(C_rail+Cx) = **6.46 kV** on first pickup (self-test e), far below 20 kV. The
   pickup is a **C-C equalization — the same two-cap tax that costs the stator core 61 %; here the island
   keeps only 24 %** of the drawn energy (r/(1+r), r = C_rail/(C_rail+Cx)).
2. **Energy / budget** — the doubler makes only **useful_per_fire = 6.15 mJ** net electrical per cycle
   (inherited). The island cannot be charged faster than this.

The binding ceiling sets the steady-state per-cycle charging → E_fire → kick-count.

## 2. The steady-state co-sim `[OC]`

One island cycle, iterated to a periodic steady state (converges to rel-spread 2×10⁻¹⁶, self-test b):
**(1)** doubler restores the rail (capped at the 20 kV design reservoir and the 6.15 mJ budget); **(2)**
pickup at cx_max = 648 pF: C-C equalize rail↔island, track ΔQ, the C-C loss, the rail draw, rail sags;
**(3)** fire at V_strike — `real` (physical gap, fires mid-collapse the instant V hits 20 kV), `M1`
(fire-after-full-collapse, the 8 pF bucket), `M2` (fire-at-648 pF, accumulate to the reservoir); **(4)**
carry residual forward. Ledger closes exactly (self-test c, rel 8×10⁻¹⁶):
**rail-draw + collapse-work = E_fire + pickup-loss**.

## 3. Results — the three schemes (rail Ca = 309 pF)

| scheme | E_fire | C_fire | Q | W_coll (rotor) | cyc/fire | E_tank | **kicks** | **η_machine** |
|---|---|---|---|---|---|---|---|---|
| **M1** (full collapse, 8 pF bucket) | 1.60 mJ | 8 pF | 0.16 µC | 1.58 mJ | 1 | 1.58 mJ | **56.3** | 0.090 |
| **real** (physical, mid-collapse) | **13.95 mJ** | 70 pF | 1.40 µC | 12.45 mJ | 1 | 13.75 mJ | **6.5** | **0.484** |
| **M2** (forced, fire at 648 pF) | 129.4 mJ | 648 pF | 12.95 µC | 0 | **37** | 127.4 mJ | 0.7 | 0.216 |

Rail-reservoir sensitivity (scheme `real`, C_rail swept 309 → 898 pF): E_fire **14.0 → 17.1 mJ**, kicks
**6.5 → 5.3**, η_machine **0.48 → 0.55** — the verdict is robust to the rail model (the budget ceiling
binds, not the dilution detail).

## 4. The resolution `[OC]`

**`M2-PARTIAL`. ISLAND-FIRE-ENERGY = 14.0 mJ.** The physical spark gap fires the instant the collapse boost
reaches 20 kV — at ~70 pF, **mid-collapse**, every cycle. That delivers ~14 mJ/fire, so the 89 mJ tank takes
**~6–7 fires**: the reach is real but **multi-fire, not single-kick** — escalate.

**η_machine = 0.484 is now physical (< 1), resolving the prior 7.3 paradox.** The fix is the charge: the
literal-trace block charged W_mech,island with the wrong (8 pF bucket) charge, getting 1.6 mJ. At the
*sourced* charge (1.40 µC), the **rotor's collapse mech work ½Q²Δ(1/C) = 12.4 mJ** is recovered — and it
**dominates E_fire** (the rail only seeds 1.5 mJ after the 4.7 mJ / 76 % pickup C-C tax). So the island fire
is mostly the *rotor's* electromechanical work, not the rail's charge; once that is counted on **both** sides
of the ledger, η_machine drops to a physical 0.48.

**Why M2 single-kick fails two ways:** (i) the physical gap fires mid-collapse long before the island could
accumulate to 648 pF @ 20 kV; (ii) *forcing* M2 (suppressing the boost-fire) needs **37 accumulation
cycles/fire** — 590 mJ of stator work per 130 mJ fire — for η_machine = 0.22, worse than the physical
scheme. The 130 mJ M2 reservoir the S2/S3 89 mJ single-kick reach assumed is **not sourceable** at the
6.15 mJ/cycle budget through the 76 % pickup tax.

**Consequence for the reach.** The S2/S3 single-kick "isolated knock" must be **reframed as a pumped swing**:
~6–7 fires of ~14 mJ accumulating in the tank (Q ~ 500, ring-down ms-scale, consistent with the multi-fire
window). The reach floor is still clearable in energy terms, but **not in one kick** — the margin must be
re-derived in the multi-fire regime, and the whole-machine efficiency is **η_machine ≈ 0.48–0.55**, not the
optimistic 0.88. This is the number the machine-level efficiency had been waiting on.

## 5. Verdicts (pre-committed, brief §4)

- **`M2-PARTIAL`** ✓ — E_fire = 14.0 mJ ∈ (1.6, 130) mJ; the physical gap fires mid-collapse.
- **`ISLAND-FIRE-ENERGY = 14.0 mJ`**, **kick-count = 6.5**, **η_machine = 0.484** — reported, robust across
  the rail sweep (14–17 mJ, 0.48–0.55).
- **Escalate** — single-kick reach is wrong; reframe as a ~6–7-fire pumped swing; re-derive the margin in
  the multi-fire regime. (`M2-SOURCED` rejected: 130 mJ unsourceable; `M1-ONLY` rejected: the rotor's
  collapse work lifts E_fire to ~14 mJ, well above the 1.6 mJ bucket.)

## 6. Self-tests (all PASS)

(a) M1 literal limit = 1.58 mJ (continuity with the prior block); (b) steady-state convergence (rel-spread
2×10⁻¹⁶); (c) ledger closure rail-draw+collapse = E_fire+pickup-loss (rel 8×10⁻¹⁶); (d) M2 ceiling
12.96 µC / 129.6 mJ; (e) rail-dilution — one 648 pF pickup lands at 6.46 kV < 20 kV.

## 7. Deliverables

`sim/island_charging_cosim.py` (steady-state co-sim + ledger + 5 self-tests) ·
`island-charging-findings.md` (this) · `island_charging.csv` · `island_energy_ledger.png` (E_fire brackets
+ per-fire ledger) · `island_kickcount.png` (E_fire vs kick-count vs the 89 mJ target) ·
`island_rail_sensitivity.png`. Frozen modules byte-identical; **not merged** — the verdict re-opens the
reach for TMD review.
