# Conservation Audit

**Date:** 2026-10-14
**Baseline evidence:** design state `09243c7` (locked 2026-10-09), branch `claude/new-session-0az7f9`
**Synthesis branch:** `claude/synthesis-phase1`
**Agent:** conservation-auditor

**Verdict: CONCERNS.** Energy and charge are conserved and the equalization principle holds; the cross-spec power
summation carries errors of ≤ 2.6 W nominal (5–9 W at the high end) and the thermal budget is met only at nominal heat
(§3).

**Status legend.** This audit decides nothing. Status columns carry the designer's status of the choice behind a value
(ledger §5.1–§5.2) as the audited spec records it. "Derived" marks arithmetic done here on committed numbers; nothing
was re-run. Every discrepancy found is stated, with its size, its direction and the test that settles it.

## Purpose

This audit gates the Phase 1 synthesis on conservation. It reads the four gated specs together —
`synthesis/core-engine-spec.md` (2026-10-13, with the designer's decisions of 2026-10-14 in its Recommendations 2, 4
and 5), `synthesis/tube-spec.md` (2026-10-14, gate-3 corrections in), `synthesis/electrical-integrity-audit.md` and
`synthesis/retainer-spec.md` — and checks:
1. the equalization-is-the-pump principle;
2. the energy ledger from shaft to heat;
3. the charge balance at every node;
4. that the specs' numbers agree with each other and with the committed results;
5. the η claim;
6. the steady-state heat balance.

It re-reads the committed results behind every number it uses (`sim/*_results.json`). It does not audit insulation
(electrical-integrity) or structure (retainer-spec), except where a power or a charge crosses them.

## Governing constraints

1. **Energy and charge are conserved** at every boundary, at the steady state, per cycle. `[OC]`
2. **Equalization is the pump (LOCKED).** No energy is recovered from the pump's own rectifying transfers; only a
   downstream sink transfer recovers freely (`CONVENTIONS.md` working rule; `docs/efficiency-resolution.md` §2, §4;
   `synthesis/core-engine-spec.md` Governing 1). `[OC]`
3. **η 0.70 is falsified; η ≈ 0.50 and 0.386 are the disc machine's anchors.** Applying either to the diode tube fails
   its gate (`synthesis/synthesis-plan.md` framing condition, line 40; `synthesis/core-engine-spec.md` Governing 2).
   `[OC]`
4. **Gate 4's criteria** (`synthesis/synthesis-plan.md` line 63): the power budget closes (pumps + windage + bearings
   = heat); η not imported onto the tube; charge balance per chain (208.5 nC = clamp 207.2 + ring 1.27); equalization
   intact.
5. **Pre-committed verdict.** A budget that does not close is reported as not closing. No term is adjusted here to
   make anything close.
6. **Frozen files untouched** (`CLAUDE.md` guardrail 1). This audit writes only this file.

**A note on the brief.** The auditor's brief lists "η ≈ 0.50" as the CLEAN condition. That is the disc machine's
island-sink anchor. Under constraint 3 the tube must *not* carry it; this audit therefore checks that no spec imports
it (§2.5), and does not test the tube against it. `[OC]`

## Specification

### 2.1 The equalization-is-the-pump principle

| Check | Finding | Source | Tag | Result |
|:------|:--------|:-------|:----|:-------|
| Any spec claims recovery from the doubler's own equalization (D1–D12, Ca / Cb, C3–C8) | **None.** core-engine Governing 1 forbids it; tube-spec Governing 1 and its budget ("No term is recovered", line 612); EI Governing 7 ("no insulation fix may add a recovery path"); retainer Governing 1 | the four specs | `[OC]` | **PASS** |
| A resonant or regenerative element on the ES pump | none: no inductor, tank or commutator on nodes 1–4, l1–r2, xa / xb. The magnetic pump's La / Lb and AH bypass belong to its own circuit and recover nothing either (all their power is heat, tube-spec budget) | tube-spec A.0, B.2–B.3 | `[OC]` | **PASS** |
| Island-sink recovery | the tube has **no island** (superseded with the spark gaps; with diodes an island becomes a multiplier, island node at 8× node 1). The disc machine's island (≈ 31 % of the tax recovered, η 0.386 → ≈ 0.45–0.50, S2 < 0.6 %) is kept as an ANCHOR only, correctly attributed | core-engine §2.7; `sim/diode-stack-findings.md` Reading 3; `docs/efficiency-resolution.md` §3 | `[OC]` | **PASS** (not applicable to the tube; anchor intact) |
| The tube's sinks | the clamps Z1 / Z4 and the rings' leakage, both dissipative. The only "product" is the rings' static field, held against 100 GΩ per ring | core-engine §2.3, §2.8; tube-spec Governing 1 | `[OC]`; `[RH]` 100 GΩ | **PASS** |
| η quoted for the tube | none. tube-spec Governing 2 names z 1.334 / η 0.386 / ≈ 0.50 as disc-machine anchors; core-engine §2.3 gives the tube "η of record: none" and the transfer 1.00 (ideal diodes, smooth C(θ)); no spec quotes 0.70 except as FALSIFIED | core-engine §2.3; tube-spec line 48; grep of all four specs | `[OC]` | **PASS** |
| Transfer η 1.00 vs the principle | consistent: with smooth C(θ) and diodes the transfer has no tax to recover (`sim/diode-stack-findings.md` table); the 0.39–0.52 range is a property of the stepped two-state schedule. 1.00 is a statement about the transfer, not a claim of recovery, and every watt of the belt is still dissipated | core-engine §2.3 rows 151–152 | `[OC]` deck; `[IR]` ideal diodes | **PASS** |

**Verdict on §2.1: PASS.** The principle is stated in all four specs and violated by none. `[OC]`

---

### 2.2 Energy ledger at the operating point

Operating point: 600 rpm each body, opposite (ω 62.83 rad/s; ω_rel 125.66 rad/s); pump 120 Hz; §3.9 redesign as laid
out, 60-part clamps, V_op 11.94 kV, rings ±14.77 kV (tube-spec target engine). Three columns: **nominal** (magnetic
pump on the 3-D utrons + neck map, the ledger's best estimate), **deck basis** (the 2-D magnetic deck of record) and
**high** (every range at its top). "Corrected" marks a value this audit derives where the specs' own differs (§2.4).

#### 2.2a  The ledger, shaft → heat (W, both bodies)

| # | Term | Nominal | Deck basis | High | Source (spec → evidence) | Tag |
|--:|:-----|--:|--:|--:|:-------------------------|:----|
| 1 | ES belt → varicaps (ideal diodes; = clamps 0.594 + rings 0.0045) | 0.599 | 0.599 | 0.634 | tube-spec budget → `sim/multiplier_waveforms_results.json` (Z 207.24 nC × 120 Hz × 11.94 kV × 2); high = as built, `sim/integrated_multiplier_results.json` 0.6341 | `[OC]` deck; `[RH]` strays |
| 2 | Magnetic belt (with the AH bypass) | 12.7–15.0 | 18.13 | 18.13 | tube-spec / retainer → ledger line 140; `sim/rotor_mechanics_results.json` `belt_W.magnetic_W` 18.126 | `[OC]` deck; `[IR]` 3-D |
| 3 | Utron iron | 1.25 | 1.25 | 1.25 | ledger line 140 ("+ iron" on the 3-D figure too); `sim/rotor_mechanics_results.json` `iron_W` 1.2496 | `[RH]` |
| 4 | La / Lb iron (not in any deck) | 0.33 | 0.33 | 0.42 | tube-spec B.2 → `sim/parts-first-cut-findings.md` §1 (0.12–0.21 each) | `[RH]` |
| 5 | Windage, all (of which outside the cage 2.61) | 12.14 | 12.14 | 25.15 | retainer §6 → `sim/rotor_mechanics_results.json` `windage.total_W` | `[IR]`; `[RH]` coefficients |
| 6 | Guard increment on the outside windage (2.6 → ≈ 3.8) | 1.2 | 1.2 | 1.2 | retainer §6 line 224 (not carried into its shaft total) | `[RH]` |
| 7 | Bearings, the layout's 6 × 6205 (corrected, §2.4 D1) | 5.52 | 5.52 | 14.64 | derived: Ca\|rel A 1.28 + B 0.87, bridge ring A 1.27 + B 0.86, end A 0.95, frame B 0.29 (`sim/rotor_mechanics_results.json` `bearings`; `sim/bridge-ring-bearings-findings.md` §4); hub-face pair removed (tube-spec C.3) | `[IR]` Palmgren |
| 8 | Gear (two meshes, pinion bearings) | 2.6 | 2.6 | 2.6 | retainer §6 → `docs/drive-gear-belt.md` §4.1 | `[IR]` |
| | **Σ = P_shaft required at the rotor's shaft** | **36.3–38.6** | **41.8** | **64.0** | derived | `[OC]` sum |
| | retainer-spec's stated shaft power | ≈ 36 | 42 | "bound 59" | retainer §6 line 211 | — |
| | **Difference (stated − itemised)** | **−0.3 … −2.6** | **+0.2** | **−5.0** | derived | — |

#### 2.2b  Where the shaft's power ends (nominal, deck basis in brackets)

| Destination | W | Share | Note | Tag |
|:------------|--:|--:|:-----|:----|
| **Delivered product: the rings' leakage** | **0.0045** | 0.012 % (0.011 %) | 2 × 14.77 kV × 0.148 µA (= 14.77 kV / 100 GΩ); the static field is the product, the leakage is its upkeep | `[OC]`; `[RH]` 100 GΩ |
| Clamps Z1 + Z4 (ideal diodes) | 0.594 | 1.6 % | 2 × 24.87 µA × 11.94 kV | `[OC]` |
| ES real-part leakage (sticks + strings), typ / max / hot | 0.004 / 0.060 / 0.142 | — | **out of the clamps' share, not on top** (§2.4 D2) | `[OC]` deck; `[IR]` / `[RH]` classes |
| Surge resistors R1–R4 | ≤ 0.006 | — | record duty; out of the clamps' share, as the leakage | `[IR]` |
| Magnetic pump's copper, diodes, AH coils, snubbers, ESR | 12.7–15.0 (18.13) | ≈ 36 % (43 %) | of which D1*–D4* 2.42, La / Lb Cu 0.66, AH coils 2.0 (deck) / 2.44 (as wound), snubbers ≤ 0.034, ESR 0.008; the rest utron copper | `[OC]` deck; `[IR]` |
| Iron (utrons, La / Lb) | 1.58 | ≈ 4 % | rows 3 + 4 | `[RH]` |
| Windage (+ guard) | 13.3 | ≈ 36 % (32 %) | rows 5 + 6 | `[IR]` / `[RH]` |
| Bearings | 5.52 | ≈ 15 % (13 %) | row 7 | `[IR]` |
| Gear | 2.6 | ≈ 7 % (6 %) | row 8, in the drive bay | `[IR]` |

Upstream of the shaft (not the tube's): HTD belt ≈ 1.8 W (61 W at the motor for 59.2 W at the shaft, drive's sizing case);
motor + driver ≈ 15 W (76 W electrical) (`docs/drive-gear-belt.md` §4.1, §6) `[IR]`.

#### 2.2c  The residual

- **P_shaft − P_rings − Σ losses = 0 by construction** at the ledger level: no spec carries an independently measured
  or simulated shaft power. The audit's residual is therefore the specs' bookkeeping, row "Difference" above: −0.3 to
  −2.6 W nominal (the retainer under-states the load by ≤ 7 %), +0.2 W deck basis, and −5 W against the high column.
  It is **negative in the sense of under-counting the load, not of energy appearing**: no term anywhere creates energy.
- **The independent closures are the decks'**, and every one closes `[OC]`:
  - ES record: belt 2.14381 W (integrator) against 2.14381 W from the waveforms, to 5e-7 (`sim/hub_rings_build_results.json`
    `record_supply.P_belt_W`, `P_belt_wave_W`);
  - ES redesign (ideal): belt against clamps + rings within 0.1 mW of 0.63 W (`sim/integrated-multiplier-findings.md`
    energy balance); laid out: 0.599 W = 0.594 + 0.0045;
  - ES real sticks: G-ENERGY ≤ 9e-8 of the belt (`sim/diodes-real-findings.md` line 391);
  - magnetic: G-ENERGY ≤ 1.0e-5 of the belt over 10 runs (`sim/diodes-real-findings.md` line 183).
- **The drive covers the load** `[IR]`: belt 0.94 N·m / 59.2 W at the shaft, motor 61 W of a 200 W rating
  (`docs/drive-gear-belt.md` §4.1). The drive's own torque table closes: 59.2 W = pumps 21.5 + inner bearings 8.7 +
  inner windage 20.0 + outside windage 5.0 + end bearings 1.4 + gear 2.6; and at the gear, rotor-side 0.52 N·m in
  (32.7 W) → counter-rotor 0.48 N·m out (30.2 W) + 2.6 W loss (derived, `[OC]`). Against the itemised high column
  (64 W) the motor runs at ≈ 66 W shaft, ≈ 33 % of rated: covered, but **"design bound 59" is not a bound** (§2.4 D4).

**Verdict on §2.2: CLOSES** at the level of the decks `[OC]`; the specs' summation carries bookkeeping errors of
≤ 2.6 W nominal and 5 W at the high end, all in the direction of under-stating the load (§2.4).

---

### 2.3 Charge conservation at every node

Per cycle (1/120 s), side A / chain 1 shown; side B / chain 2 mirror within the stated figures. DC charge only: every
capacitor passes zero net charge per settled cycle, so a node's balance is its diodes, clamp and leakage. Source:
`sim/multiplier_waveforms_results.json` (diodes' charges by Kirchhoff in 1° bins; `charge_balance.worst`), via
tube-spec budget and core-engine §2.4.

| Node | In (nC / cycle) | Out (nC / cycle) | Imbalance | Tag | Result |
|:-----|:----------------|:-----------------|:----------|:----|:-------|
| 0 (REF, shaft) | chain 1 leaves REF through D1 (208.48) and returns through Z4 (207.24) + ring B's leakage (1.23) = 208.47; chain 2, reversed, enters through D2 (208.5) and leaves through Z1 (207.24) + ring A's leakage (1.23) | — | 0.01 % per chain; link DC 0.19 nA (record) | `[OC]` | PASS |
| 2 | D1 208.48 | D3 208.50 | 0.01 % | `[OC]` | PASS |
| r1 | D3 208.50 | D6 208.51 | chain 1 to 0.011 % | `[OC]` | PASS |
| l2 | D6 208.51 | D7 208.49 | 0.011 % | `[OC]` | PASS |
| 4 | D7 208.49 | Z4 207.24 + D9 1.27 = 208.51 | **0.009 %** (`node 4: D7 = D9 + z4` 8.7e-5) | `[OC]` | PASS |
| 1 (chain 2) | D8 208.5 | Z1 207.24 + D11 1.27 | 0.009 % (9.1e-5) | `[OC]` | PASS |
| 3, l1, r2 | chain 2: D2 = D4 = D5 = D8 to 8.5e-5 | — | 0.009 % | `[OC]` | PASS |
| xb (ring B's stage) | D9 1.272 | D10 1.289 | **1.4 %** (`ring B's stage: D9 = D10` 0.0135); A 1.6 % | `[OC]` read; `[IR]` binning | PASS within the read's error (below) |
| eb (ring B) | D10 1.289 | leakage 14.769 kV / 100 GΩ / 120 Hz = **1.231** | **+4.7 %** (A +4.5 %) (`ring_stage_over_leak`) | `[OC]` | **DISCREPANCY (read artefact, below)** |
| counter-rotor (s) | — | — | within 0.1 µV of REF; link 0.02 µA rms, AC only | `[OC]` | PASS |
| a, b, c, d (motor) | not published per node | — | the deck enforces KCL; its G-ENERGY closes to 1e-5. Published averages (D1* / D2* 0.81 A, D3* / D4* 1.07 A, La / Lb mean 1.05 A; `sim/rotor_parts_duty_results.json`, `sim/parts-first-cut-findings.md` §2.1) cannot be checked node by node from the specs: the motor circuit is the ES doubler's dual, so its diode averages need not be equal | `[OC]` deck; `[IR]` | **NOT AUDITABLE from the specs** |
| AH bypass, snubbers | AC only (capacitors): ≤ 1.3 mV reverse on the bypass | — | no DC path | `[OC]` | PASS |

**The ring-node discrepancy, stated** `[OC]`:
- The study reads 4.5–4.7 % more charge into each ring than its leakage takes, and explains it as "the charge its
  capacitors still take up" (`sim/multiplier-waveforms-findings.md` §3).
- **That explanation does not survive the study's own record.** 0.058 nC a cycle into ≈ 108 pF (Csa 100 + 7.21 to REF
  + 0.99 ring to ring) is +0.54 V a cycle per ring, +1.07 V a cycle on the ring-to-ring gap, ≈ +75 V over the last 70
  cycles. The recorded gap (`rings.gap_per_cycle_kV`) wanders 29.5378–29.5418 kV over those cycles, ±2 V, with no trend
  (derived).
- **So the excess is the Kirchhoff read's error, not charge**: the same ring stages show D9 ≠ D10 by 1.4–1.6 %, 0.75 %
  backward conduction and 1.3 % conduction under reverse bias — the study notes the bins' C ΔV terms nearly cancel
  there (§1). Charge is conserved on the voltages; the published 1.27 / 1.29 nC are ≈ 5 % high.
- **Size:** 7 nA a ring, ≈ 0.1 mW-equivalent — immaterial to energy; it matters only if someone sizes the ring stage
  from 0.15 µA instead of the leakage's 0.148 µA.
- **The test that settles it:** fit dV/dt of `ea` / `eb` over the last 100 cycles of the deck (expected 0 ± 0.03 V a
  cycle), or re-read the ring stages' charge at 2× steps (G3 shows ≤ 0.03 % moves only for the chain's large charges).
  If dV/dt ≠ 0, the run is unsettled and the 60-part ring level is low by up to 75 V; if 0, the read is the artefact.

**Gate-4 identity** (synthesis-plan line 63): 208.5 nC = 207.2 + 1.27 → 208.47 against 208.49–208.51: **closes to 0.01 %**
`[OC]`.

**Verdict on §2.3: PASS** for every ES node; the ring-node over-read is an artefact of the measurement (ambiguity
stated with its test); the motor nodes are not auditable from the specs.

---

### 2.4 Power-budget consistency across specs

Every discrepancy found, however small. "Direction" says whether it over- or under-states the load the drive and the
cooling must carry.

| # | Item | Spec A says | Spec B / evidence says | Size | Direction | Rounding or error? | Tag |
|--:|:-----|:-----------|:-----------------------|--:|:----------|:-------------------|:----|
| D1 | **Bearing friction** | retainer §6: "4 inner + 2 frame" 5.1 W **plus** the bridge-ring pair 2.1 W = 7.2 W (3.2–14.2 + 6.1) | tube-spec C.3: 6 × 6205 — 2 Ca\|rel, 2 bridge-ring, 2 end/frame, **no hub-face bearings**. The 5.1 W includes hub face A / B, 0.87 W each (`sim/rotor_mechanics_results.json` `bearings.nominal.each_W`). Layout: **5.52 W** (14.64 high). The drive sizes "five inner (four of record + gear-end)" 8.7 W + ends 1.4 W = 10.1 W (`docs/drive-gear-belt.md` §4.1) | +1.7 W nominal (+5.7 high) in retainer; +4.6 W in the drive | over-states | **Error** (a removed pair still counted). Three bearing counts across three documents. Test: count the 6205s on BRG-800–814 / P-001 (qty 6) and sum their friction | `[IR]` |
| D2 | **ES real-part leakage** | tube-spec budget lists leakage 4 / 60 / 142 mW and R 6 mW as rows beside clamps 0.594; retainer §6 adds them: "0.6 (≤ 0.74 hot)" | `sim/integrated_multiplier_results.json` HV runs: typ belt 0.6189 = clamps 0.6110 + rings 0.0043 + other 0.0036; max 0.6189 = 0.5545 + 0.0041 + 0.0602; **hot 0.5818 = 0.4362 + 0.0039 + 0.1417**. `sim/diodes-real-findings.md` line 312: "the leakage's power comes out of the clamps' share". EI line 393 agrees ("from the clamps' share") | +0.16 W hot | over-states | **Double count** (bookkeeping). Physically the ES total never exceeds its belt, ≤ 0.634 W | `[OC]` |
| D3 | **ES belt "unchanged" hot** | EI line 393: "belt unchanged" | the same runs: belt 0.6341 (ideal) → 0.6189 (typ, max) → 0.5818 (hot), −8 % | 52 mW | — | **Imprecise wording** in EI; immaterial | `[OC]` |
| D4 | **"Design bound 59 W"** | retainer §6 line 211: shaft power ≈ 36 nominal, 42 deck basis, **bound 59** | 59.2 W is the drive's sizing case with a 25 W windage *allowance* and the record's 2.14 W ES belt. The retainer's own items at their tops: 0.74 + 19.38 + 25.1 + 14.2 + 6.1 + 0.06 + 2.6 = **68.2 W**; this audit's high column **64.0 W** | 5–9 W | under-states | **Error of labelling**: 59 W is a sizing case, not a bound. The motor still covers 64–68 W (≈ 33–36 % of 200 W) | `[IR]` |
| D5 | **Utron iron on the 3-D basis** | retainer §6: magnetic 12.7–15.0 W "(… utron Cu and iron)" | ledger line 140: "12.7–15.0 W with the neck's field map as well, **+ iron**" (1.25 W) | 1.25 W | under-states | **Error** (iron omitted from the nominal). Test: read `sim/neck-nonlinear-findings.md` §6–§7 for whether its belt includes the core loss | `[IR]` |
| D6 | **Guard drag** | retainer line 224: guard raises outside windage 2.6 → ≈ 3.8 W | not carried into retainer's shaft total (line 211) or its heat table | ≈ 1.2 W | under-states | **Omission** | `[RH]` |
| D7 | **ES belt in the drive's sizing** | `docs/drive-gear-belt.md` §4.1: electrostatic 2.14 W (record, no strays) | synthesis: 0.599 W laid out (tube-spec budget) | 1.54 W | drive over-sized | **Stale input**, conservative; the drive is not re-cut on the redesign | `[OC]` |
| D8 | **Magnetic belt, real Schottky set** | tube-spec / retainer: 18.1 W deck basis | `sim/diodes-real-findings.md` §3.3: SBM set with 22 mF, belt 18.01 W, diodes 2.42 W (the 18.13 W is the ideal-diode deck, `rotor_mechanics_results.json`) | 0.12 W | over-states | **Rounding of basis** (tube-spec pairs 18.1 W with the SBM diodes' 2.42 W, from different runs) | `[IR]` |
| D9 | **AH coils** | tube-spec budget "AH coils 2.44 (1.22 each, as wound)" as an "of which" of the 18.1 W belt | the deck's coils are 0.27 Ω, as wound 0.333 Ω (ledger line 986); deck P_AH 2.00 W (`sim/rotor_parts_duty_results.json` τ 0.5). The "of which" items mix bases, so they cannot be summed against the belt | 0.44 W | — | **Basis mix**; the as-wound coil changes the belt and the AH field. Test: re-run the magnetic deck at 0.333 Ω | `[IR]` |
| D10 | **"ES ≈ 3 % of the tube's dissipation"** | tube-spec line 612 | 0.6 / 19.98 W (pumps only, deck) = 3.0 %; of the whole tube load 0.6 / 37.5 = **1.6 %** | — | — | **Wording**: the denominator is the pumps', not the tube's | `[OC]` |
| D11 | **La / Lb copper** | tube-spec B.2: 0.33 W each at R 0.276 Ω (20 °C) | 1.051 A rms² × 0.276 = 0.305 W; the deck's 0.322 W uses 0.292 Ω (`rotor_parts_duty_results.json`) | 0.03 W | — | **Rounding** (warm vs cold R) | `[OC]` |
| D12 | **Surge-resistor loss** | tube-spec 4 × ≈ 1.4 mW (record duty) | the redesign's D1 / D3 carry 25 µA avg (record 81 µA); I²R scales down ≈ 10× | ≈ 5 mW | over-states | **Stale basis**, immaterial | `[IR]` |
| D13 | **Ring-stage charge** | tube-spec / core-engine: ring stage 1.27 nC, 0.15 µA | the ring's leakage 1.231 nC, 0.148 µA (§2.3) | 4.7 % | — | **Read artefact** (§2.3, with its test) | `[OC]` |

**Agreements checked, no discrepancy** `[OC]`:
- belt power: tube-spec 0.599 W laid out / 0.634 W as built ↔ core-engine §2.4 (0.646 W record supply as built; 0.63 W
  clamps, redesign) ↔ `sim/integrated_multiplier_results.json` 0.6341 / `sim/multiplier_waveforms_results.json`;
- core-engine §2.8 ledger ↔ `sim/hub_rings_build_results.json` `record_supply` (2.14381 / 1.06984 / 1.06945 / 0.00448 /
  0.00004 W): exact;
- hot leakage: EI 142 mW ↔ tube-spec 142 mW ↔ deck 0.1417 W;
- voltages: V_op 11.94 kV (clamp target, deck `vop` 11938 V) and node 1's −11.99 kV swing (EI's gap voltage) are
  different quantities (the string's slope under 0.516 mA), consistent; rings ±14.77 kV in tube-spec, EI, retainer;
  record 13.13 kV / ±14.96 kV only as evidence in all four;
- drive torques: retainer 0.48 / 0.52 / 1.00 N·m ↔ `docs/drive-gear-belt.md` §4.1, and the gear's power closes (§2.2c);
- windage 12.1 W (7.9–25.1) in retainer ↔ `sim/rotor_mechanics_results.json` 12.14 (7.86–25.15).

**Verdict on §2.4: CONCERNS.** Thirteen discrepancies; none creates energy. Two are errors that move the load by more
than 1 W (D1 over-counts 1.7 W; D5 + D6 under-count 2.5 W, netting to ≈ +0.8 W under-stated), one mislabels the high
end (D4, 5–9 W). All the rest are below 0.2 W or wording.

---

### 2.5 The η check

| Quantity | Value | Basis | Tag |
|:---------|--:|:------|:----|
| η_machine = P_rings / P_shaft | **1.2e-4** (0.0045 / 37.5 W nominal); 1.1e-4 deck basis; 7e-5 high | §2.2 | `[OC]` arithmetic; `[RH]` 100 GΩ |
| η_ES = P_rings / P_belt,ES | **0.0075** (0.0045 / 0.599 W) | tube-spec budget | `[OC]` |
| η_ES, record (no strays) | 0.0021 (0.00448 / 2.1438 W) | core-engine §2.8 | `[OC]` |
| transfer η, diode core, smooth C(θ), ideal diodes | 1.00 | core-engine §2.3; `sim/diode-stack-findings.md` | `[OC]` deck; `[IR]` |
| disc-machine anchors (not the tube) | 0.386 direct; ≈ 0.45–0.50 with the island sink; 0.70 FALSIFIED | core-engine §2.3; `docs/efficiency-resolution.md` | `[OC]` ANCHOR |

**Reading** `[OC]`:
- The tube's η is **not** ≈ 0.50, and must not be. The brief's comparison target is the disc machine's island-sink
  anchor; importing it fails gate 4 (synthesis-plan lines 40, 63). No spec imports it (§2.1).
- The machine's η is ≈ 1e-4 because its product is a static field held against 100 GΩ: the shaft's power buys the
  pumps' governor losses (clamps), the magnetic pump's copper and the air's drag. That is not a defect of the
  conservation ledger — it is the ledger. The ES pump's own surplus goes 99.3 % to its governor, the clamps.
- A ratio P_rings / P_belt that is small is the expected consequence of the equalization principle applied to a
  clamped pump with no downstream non-dissipative sink: **no recovery term exists, and none is claimed.**
- If a later spec ever states η_ES > 0.0075 for this operating point, or quotes a machine efficiency above the
  itemised ledger's, it must show a new sink; the transfers cannot supply one (Governing 2).

**Verdict on §2.5: PASS** — η is not imported onto the tube; the computed η is consistent with the ledger. The brief's
"η ≈ 0.50" criterion is the disc machine's and is set aside under the locked framing (Governing 3).

---

### 2.6 Thermal power balance

At steady state every watt of §2.2 is heat. The limit is EI's: rotor air ≤ room + 5 K, set by the hub's equatorial gel
(glass ≤ 37.3 °C at room 29.8 °C; `synthesis/electrical-integrity-audit.md` line 321; `sim/hub-thermal-findings.md`).

#### 2.6a  Heat by compartment (W)

| Compartment | Terms | Nominal | Deck basis | High | Tag |
|:------------|:------|--:|--:|--:|:----|
| **Inside the counter-rotor's cage** (closed) | ES 0.6; magnetic incl. utron iron 13.95–16.25 (20.63 deck); La / Lb iron 0.33 (0.42); inner windage 9.53 (21.76 high; total less the outside 2.61 / 3.39); inner bearings Ca\|rel + bridge ring 4.28 (12.16) | **28.7–31.0** | **34.1** | **54.3** | `[IR]` / `[RH]` |
| Outside the cage, inside the guard | outside windage 2.61 + guard 1.2; frame bearings 1.24 (2.48) | 5.1 | 5.1 | 7.1 | `[RH]` |
| Drive bay (partitioned) | gear 2.6; motor + driver ≈ 15 (outside the guard) | 2.6 (+15) | 2.6 (+15) | 2.6 (+15) | `[IR]` |

retainer-spec's "≈ 34–40 W into the tube compartment, ≤ 56 W bound" (line 214) is the sum of both guard
compartments; it agrees with 33.8–36.1 / 39.2 / 61.4 W here to within D1, D5, D6 (§2.4) except at the high end (+5 W).

#### 2.6b  Temperature rise of the inner air (derived from retainer §6's model and numbers)

retainer's model: inner air → cage wall, U ≈ 12 W/m²K over ≈ 0.9 m² (UA ≈ 10.8 W/K); then the guard's annulus, a
natural chimney of ≈ 7 L/s at 2.5 K mean (ρ c_p Q ≈ 8.4 W/K), flow ∝ √ΔT. Re-solved here with the heat of 2.6a
`[RH]` (every coefficient is the retainer's `[RH]`):

| Case | Into the annulus (W) | Annulus exit / mean rise (K) | Wall drop (K) | **Inner air over room (K)** | vs + 5 K |
|:-----|--:|--:|--:|--:|:--|
| Nominal | 33.8–36.1 | 4.3–4.5 / 2.2–2.3 | 2.7–2.9 | **4.8–5.1** | at the limit |
| Deck basis | 39.2 | 4.8 / 2.4 | 3.2 | **5.5** | **over by 0.5 K** |
| High | 61.4 | 6.4 / 3.2 | 5.0 | **8.2** | **over by 3.2 K** |
| High, with the retainer's fan (3 × flow, ≈ 21 L/s) | 61.4 | ≈ 2.4 / 1.2 | 5.0 | **≈ 6.2** | over by 1.2 K |

**Reading** `[RH]`:
- retainer §6 says "≈ 5–7 K total, matching the +5 K". **5–7 K does not match ≤ 5 K**: it meets the limit only at the
  nominal heat and exceeds it on the deck basis and at the high end. With room ≤ 29 °C the hub glass's 37.3 °C is then
  crossed by ≈ 0.5–3 K, i.e. the room ceiling falls to ≈ 29.3 °C (deck) and ≈ 26.6 °C (high).
- **The fan does not cure the high case.** The wall's own drop (5.0 K at 54 W inside the closed cage) uses the whole
  budget; outside flow cannot remove it. The levers are inside: the windage's high end (21.8 W inside) and the bearings'
  grease (12.2 W inside at 70 mm²/s), both settled by the bench's coast-down (retainer-spec, Items deferred to bench; `sim/rotor-mechanics-findings.md` §6, §8).
- **No thermal runaway in the ES pump**: its heat is ≤ 0.63 W, and its leakage term, the only temperature-dependent ES
  loss, is ≤ 0.14 W even at the hot class (D2). At room + 5–15 K the sticks leak ≈ 100–200 nA (EI line 323), far
  from the 5 µA hot class `[RH]`. The thermal limit is the hub glass's, not the sticks'.
- **No forced-cooling requirement is proven** at the nominal heat; the margin is zero there. Whether the inner air
  holds + 5 K is a bench measurement (retainer: thermocouples in the guard air and on the cage, at 25 and 29 °C room).

**Verdict on §2.6: CONCERN.** The heat balance closes (every watt has a path), but the stated temperature limit holds
only at the nominal heat, with no margin, and fails by 0.5–3.2 K on the deck basis and at the high end.

---

### 3. Verdict

| Check | Result | Where |
|:------|:-------|:------|
| Equalization-is-the-pump | **PASS**: no recovery claimed anywhere; no island in the tube; anchor intact | §2.1 |
| Energy conservation | **CLOSES** at the decks (5e-7 … 1e-5); the specs' summation under-states the load by ≤ 2.6 W nominal, 5 W high | §2.2 |
| Charge conservation | **PASS** at every ES node (0.009–0.011 %); ring-stage over-read 4.7 % is a measurement artefact (test stated); motor nodes not auditable from the specs | §2.3 |
| Cross-spec consistency | **CONCERNS**: 13 discrepancies, none creating energy; errors D1 (bearings +1.7 W), D2 (leakage double count +0.16 W), D4 (59 W is not a bound), D5 + D6 (−2.5 W) | §2.4 |
| η | **PASS**: not imported; η_machine ≈ 1.2e-4, η_ES 0.0075, consistent with a clamped pump | §2.5 |
| Thermal balance | **CONCERN**: + 5 K met only at nominal heat with zero margin; + 5.5 K deck basis; + 8.2 K high | §2.6 |

## **Overall verdict: CONCERNS — the synthesis passes conservation; it does not pass clean.**

- **No conservation violation** `[OC]`: every watt from the shaft ends as heat or as the rings' 4.5 mW leakage; no
  term creates energy; no spec recovers energy from the doubler's equalization; the charge closes at every ES node.
- **The concerns are bookkeeping and margin, not physics**: the shaft-power total and its "bound" (D1, D4, D5, D6),
  the ES leakage double count (D2), and a thermal budget met only at nominal heat (§2.6).
- **Nothing here is a FAIL by the gate's terms.** The audit was pre-committed to report a non-closing budget as such;
  the budget closes, and the specs' summation errors are stated with their sizes rather than absorbed.

## Evidence ledger

| Item | Current design | Evidence | Issue (if any) |
|:-----|:---------------|:---------|:---------------|
| ES belt / clamps / rings | 0.599 / 0.594 / 0.0045 W (laid out, ideal) | `sim/multiplier_waveforms_results.json`; `sim/integrated_multiplier_results.json` | real sticks: leakage from the clamps' share (D2) |
| ES record ledger | 2.14381 = 1.06984 + 1.06945 + 0.00448 + 0.00004 W | `sim/hub_rings_build_results.json` `record_supply` | P_other is the remainder by construction; the waveform check is the independent one (5e-7) |
| ES real-stick runs | belt 0.6189 / 0.6189 / 0.5818 W; leakage 3.6 / 60.2 / 141.7 mW | `sim/integrated_multiplier_results.json` HV-typ / -max / -hot | belt falls hot (D3) |
| Magnetic belt | 18.13 W ideal-diode deck; 18.01 W SBM; 12.7–15.0 W 3-D + neck, + iron 1.25 | `sim/rotor_mechanics_results.json`; `sim/diodes-real-findings.md` §3.3; ledger line 140 | iron omitted in retainer's nominal (D5); AH coil basis mixed (D9) |
| Windage | 12.14 W (7.86–25.15), 2.61 outside the cage | `sim/rotor_mechanics_results.json` `windage` | guard +1.2 W not carried (D6) |
| Bearings | record 5.12 W incl. hub-face pair 1.74; bridge-ring pair 2.13 | `sim/rotor_mechanics_results.json`; `sim/bridge-ring-bearings-findings.md` §4 | layout has no hub-face pair: 5.52 W, not 7.2 (D1) |
| Drive | 59.2 W at the shaft, 0.48 / 0.52 / 1.00 N·m; motor 61 W of 200 | `docs/drive-gear-belt.md` §4.1, §6 | sized on the record's ES 2.14 W (D7) and 25 W windage; not a bound (D4) |
| Charge per chain | 208.5 nC = 207.24 + 1.27 (0.011 %) | `sim/multiplier_waveforms_results.json` `charge_balance` | ring stage over-read 4.7 % vs the ring's flat voltage (§2.3) |
| Thermal | inner air + 4.8–5.1 K nominal, + 8.2 K high (derived) | retainer-spec §6 model `[RH]` | + 5 K limit met with zero margin (§2.6) |

## Cross-spec dependencies

| Item | Value | Needed by | Note |
|:-----|:------|:----------|:-----|
| Bearing count and friction | 6 × 6205, 5.52 W nominal / 14.64 W high | retainer-spec §6; drive re-cut | D1 |
| ES dissipation, hot | ≤ 0.634 W total (leakage inside it) | retainer-spec §6 | D2 |
| Shaft power, high | 64 W itemised (68 W on retainer's own items) | retainer-spec §2, §6 | D4; replace "bound 59" |
| Magnetic pump on the 3-D basis | 12.7–15.0 W + 1.25 W iron | retainer-spec §6 | D5 |
| Guard drag | + ≈ 1.2 W outside the cage | retainer-spec §6 | D6 |
| ES belt for the drive | 0.6 W (redesign), not 2.14 W | drive re-cut | D7 |
| Motor nodes a–d charge balance | per-node DC sums | tube-spec B | not published (§2.3) |
| Inner-cage heat | 28.7–31.0 W nominal, 34.1 deck, 54.3 high | retainer-spec §6, electrical-integrity §2.6 | §2.6a |
| "Leakage from the clamps' share; belt falls 8 % hot" | — | electrical-integrity line 393 | D3 wording |

## Items deferred to bench

| Item | Why it is open | What the bench measures | Source |
|:-----|:---------------|:-----------------------|:-------|
| Windage + bearing drag | 7.9–25.1 W and 3.2–14.6 W; the high ends set the thermal verdict | coast-down from 600 rpm, with and without the guard | `sim/rotor-mechanics-findings.md` §6, §8; retainer-spec |
| Inner-air rise | the + 5 K budget is met at nominal heat with zero margin `[RH]` | thermocouples in the cage air, on the cage tube and in the guard air at 25 / 29 °C room | `sim/hub-thermal-findings.md`; retainer-spec §6 |
| Shaft power | no spec has a measured P_shaft | the driver's current × the motor's constant at steady 600 rpm, against §2.2's 36–42 W | `docs/drive-gear-belt.md` §6 |
| Rings' leakage | 100 GΩ is `[RH]`; it is the whole "product" term | DC leakage per ring at ± 14.8 kV, warm | `docs/bench-test-rings.md` |
| Sticks' and strings' leakage, warm | sets the ES leakage term 4–142 mW and the seed | leakage vs temperature at working voltage | `sim/diodes-real-findings.md` §6 |

## Recommendations for the designer

All PROPOSED. The designer decides.

1. **PROPOSED:** retainer-spec §6 restates the shaft power on the layout's six bearings (5.52 W, not 5.1 + 2.1),
   adds the 3-D basis's utron iron (1.25 W) and the guard's drag (≈ 1.2 W), and replaces "design bound 59" with the
   itemised high end (≈ 64 W), noting the 200 W motor covers it.
2. **PROPOSED:** tube-spec's budget shows the real-part leakage and the surge resistors as *of which* the clamps'
   share (belt 0.634 → 0.582 W hot), not as added rows; retainer-spec §6 then carries the ES pump at ≤ 0.63 W.
3. **PROPOSED:** tube-spec B publishes the motor nodes' DC balance (a, b, c, d) from the deck, so the charge audit can
   close them as it closes the ES nodes.
4. **PROPOSED:** settle the ring-stage read (§2.3): fit dV/dt of the rings over the last 100 cycles of
   `sim/multiplier_waveforms.py`'s deck; if zero, record the 1.27 / 1.29 nC as an over-read and carry the leakage's
   1.231 nC.
5. **PROPOSED:** treat the + 5 K inner-air budget as unmet until the bench's coast-down and thermocouples say
   otherwise (§2.6); the designer may set the room ceiling (≈ 26.6 °C at the high heat) or require the inner-side
   lever (grease choice, windage), since the outside fan alone does not reach the high case.
6. **PROPOSED:** the drive's re-cut on the sixth-gap tube takes the redesign's ES belt (0.6 W) and the corrected
   bearing set.
