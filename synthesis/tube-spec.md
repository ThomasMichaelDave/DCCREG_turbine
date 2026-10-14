# Tube Specification

**Date:** 2026-10-14
**Baseline evidence:** design state `09243c7` (locked 2026-10-09), branch `claude/new-session-0az7f9`
**Synthesis branch:** `claude/synthesis-phase1`
**Agent:** tube-synth

**Status legend.** The Status column carries the designer's status of the *choice* behind each value, as the ledger
records it (`docs/ledger/DCCREG-design-ledger.md` §5.1–§5.2). A computed consequence carries its choice's status. Where
this spec recommends, it says **PROPOSED (synthesis)**; it decides nothing. "Derived" marks arithmetic done here on
committed numbers; nothing was re-run.

**Designer's decisions of 2026-10-14 (DECIDED), applied throughout:**
1. **Paired records.** "The engine theory should keep both ideal and real HV diode simulation records for the empirical
   proof to come." Every gain, ring level and seed is carried as a pair: **ideal diodes** and **real HV sticks**
   (typical / maximum / hot leakage, `sim/diodes-real-findings.md` §4, §6; `sim/integrated-multiplier-findings.md` §5).
   Neither replaces the other; the bench arbitrates. Where only one record exists, the other is marked *not run* (OPEN).
   (`synthesis/core-engine-spec.md` Recommendation 2.)
2. **Sixth Ca / Cb gap.** "Sixth gap ok": Ca / Cb take 7 plates / 6 gaps of 6 mm per side, the rule's 1.1 C_max =
   495 pF (`sim/tube-strays-findings.md` §6), not the layout's 5 gaps (480.5 / 482.3 pF). Every layout result computed
   on 5 gaps is flagged **5-gap basis — re-run OPEN** (§A.8 lists them); no new value is invented here.
3. **No HV seed source.** The designer reports, as experimentally established, that the simple four-diode de Queiroz
   doubler self-starts without an HV seed, in dry and humid weather alike (dry starts more easily); if slow,
   triboelectric injection from a rubbed PVC tube starts it (`synthesis/core-engine-spec.md` Recommendation 5). This
   tube carries **no seed-source part**. The model's seed thresholds stay beside that evidence (§A.3); whether the §3.9
   redesign self-starts the same way is OPEN for the bench; an injection point is specified (§A.3a).

**Target engine.** The §3.9 redesign: the multiplier stacked into the doubler — circuit DECIDED "for now" (10-11);
layout, capacitor mounts, bridge-ring bearings and AH-drive parts' places PROPOSED (ledger §5.1). The record's doubler
with its separate 2 + 2 Cockcroft–Walton chains is carried as evidence only (`synthesis/core-engine-spec.md`
Recommendation 1).

## Purpose

This spec states the tube: everything on the two turning bodies except a spark-gap commutator (none exists; Phase 2).
It covers the electrostatic pump as the §3.9 redesign lays it out (varicaps C1 / C2, Ca / Cb, the ladder C3–C6, the ring
stages C7 / C8 and Csa / Csb, the HV sticks D1–D12, the surge resistors R1–R4, the clamp strings Z1 / Z4), the node
stray budget, the air insulation stack, the motor parts carried on the rotor (D1*–D4*, La / Lb, the AH bypass, the eight
node snubbers, K4) and the physical arrangement up to the shaft's interface. It excludes bearings, motor, drive and cage
as structures (retainer-spec), and the rings and hub (interface only). It depends on `synthesis/core-engine-spec.md` for
z, κ requirement, the clamp requirement and the conservation principle.

## Governing constraints

1. **Equalization-is-the-pump (LOCKED).** No component of this tube recovers energy from the rectifying transfers
   (D1–D12, Ca / Cb, C3–C8). The tube's sinks are the clamps Z1 / Z4 and the rings' leakage; both dissipate. The belt's
   power to the ES pump ends as heat (`synthesis/core-engine-spec.md` Governing 1; `CONVENTIONS.md`). `[OC]`
2. **No disc-machine numbers on the tube.** z 1.334 and η 0.386 / ≈ 0.50 are anchors of the superseded disc machine
   (`synthesis/core-engine-spec.md` §2.2–§2.3). The tube has no η of record; its engine numbers are z 1.0142 (redesign as
   built) → 1.0164 (laid out) → 1.01589 (with the mounts), ideal diodes. `[OC]`
3. **The designer's DECIDED items bind** (ledger §5.1): the stack of record (6 + 6 Al vanes, 6 mm air gaps, 22° / 22°,
   r 150, V_op = breakdown / 1.5, Ca = 1.1 C_max); the clamps Z1 / Z4 on nodes 1 / 4; the HV side on the rotor; the
   symmetric supply; the multiplier stacked into the doubler (10-10); its circuit "for now" (10-11). `[IR]`
4. **The clamps are mandatory.** Without them the pump arcs at the stack with 25–47 A through the diodes
   (`sim/electrostatic-no-clamp-findings.md`). `[OC]`
5. **Every part is from the latest design files** (the drawing set `docs/drawings/set-index.json`, Rev A drafts; the
   first cuts `sim/parts-first-cut-findings.md`). No part is invented here.
6. **Frozen files untouched** (`CLAUDE.md` guardrail 1). This spec edits nothing outside `synthesis/`.

## Specification

### A. Electrostatic pump

#### A.0  Circuit of the target (per `sim/integrated-multiplier-findings.md`, `sim/multiplier-waveforms-findings.md`)

| Parameter | Value | Source / basis | Tag | Status |
|:----------|:------|:---------------|:----|:-------|
| Doubler core | C1 node 1 → REF, C2 node 4 → REF; Ca 1–2, Cb 3–4 | ledger §3.4, §3.9 | `[OC]` | DECIDED |
| Chain 1 (side A → ring B) | 0 → D1 → 2 → D3 → r1 → D6 → l2 → D7 → 4 → D9 → xb → D10 → ring B | `sim/multiplier-waveforms-findings.md` §1 | `[OC]` | DECIDED for now |
| Chain 2 (reversed, → ring A) | the mirror, every diode reversed: D2, D4, D5, D8, D11, D12 | `sim/integrated-multiplier-findings.md` Headline | `[OC]` | DECIDED for now |
| Ladder | C3 (2–l1), C5 (l1–l2) on node 2; C4 (3–r1), C6 (r1–r2) on node 3 | ledger §3.9 | `[OC]` | DECIDED (10-10) |
| Ring stages | C7 from l2 with D9 / D10 → ring B; C8 from r2 with D11 / D12 → ring A | ledger §3.9 | `[OC]` | DECIDED for now |
| Smoothing | Csa (ring A → shaft), Csb (ring B → shaft), 100 pF each | ledger §3.9 | `[IR]` | DECIDED for now |
| Polarity | bipolar: side A negative, side B positive; the null at the shaft's potential | `sim/integrated-multiplier-findings.md` §2 | `[OC]` | DECIDED for now |
| Varicap phasing | C1 / C2 **in phase** (C2's rotor sectors aligned with C1's). In antiphase the redesign does not pump (z 1.0000 as built) | `sim/integrated-multiplier-findings.md` Headline | `[OC]` | DECIDED for now |
| Reference link | Q1 = −Q2: 0.02 µA rms; the counter-rotor may float (z 1.0142 on 100 pF) | `sim/integrated-multiplier-findings.md` §6 | `[OC]` | DECIDED for now |

**Rationale.** A bipolar four-diode doubler peaks at z 1.098 in phase (2-D) against the unipolar 1.31; the clamp diodes
give back part of each transfer `[OC]` (`sim/integrated-multiplier-findings.md` §2). That structural penalty is the
price of the bipolar rings; it is the designer's choice, carried, not reopened.

---

#### A.1  Varicap vanes (C1, C2)

| Parameter | Value | Source / basis | Tag | Status |
|:----------|:------|:---------------|:----|:-------|
| Stack (per side) | 6 stator (REF, counter-rotor) + 6 rotor (node 1 / 4) vanes; Al 3 mm; every exposed edge full round R1.5; 11 gaps of 6 mm air | ledger §3.4, §4 | `[IR]` | DECIDED |
| Sectors | 6 on a 60° pitch, 22° stator / 22° rotor; r 50–150 mm; 8° clearance each side at C_min | ledger §4 | `[IR]` | DECIDED |
| Vane rings | stator ring r 150–162; rotor ring r 20.5–50 on the G10 sleeve (r 12.5–20.5) | ledger §4 | `[IR]` | DECIDED (record) |
| Stack order (layout) | the record's 6 + 6 with ends swapped: a rotor vane at the hub end, a stator vane outward; \|z\| 171–273 mm from the hub's centre | `sim/multiplier-layout-findings.md` Headline | `[IR]` | PROPOSED (layout) |
| C_min / C_max, deck (2-D cell + 2 pF rim floor) | 54.9 / 409.9 pF, κ 7.47 | `sim/core_field_results.json` design | `[IR]` 2-D cell | DECIDED (record basis) |
| C_min / C_max, as built (3-D solve) | **128.4 / 450.6 pF, κ 3.51**; rims add 65 pF to C_min, 37 pF to C_max | `sim/tube-strays-findings.md` §4 | `[OC]` solve; `[IR]` solids | OPEN (accept or remedy, ledger §5.2) |
| **Target κ for this synthesis** | **3.51 (as built) for every performance number; 7.47 kept as the record's basis only** | this spec, rationale below | `[IR]` | PROPOSED (synthesis) |
| Node-total ratio, nodes 1 / 4, with the mounts' strays | (450.6 + 74.61) / (128.4 + 74.61) = **2.59** | derived from `sim/tube-strays-findings.md` §4, `sim/doubler-caps-findings.md` §4 | `[IR]` | PROPOSED (layout) |
| z at start-up, **ideal diodes**: as built / laid out / with mounts | 1.0142 / 1.0164 / **1.01589** (the last two on the 5-gap Ca: re-run OPEN) | `sim/integrated-multiplier-findings.md` §4; `sim/multiplier-layout-findings.md` §6; `sim/doubler-caps-findings.md` §5 | `[OC]` deck; `[RH]` strays | DECIDED for now / PROPOSED / PROPOSED |
| z from 1 kV, **real HV sticks** (as built): typical / maximum / hot | 1.0129 / 1.0039 / **0.9870**; laid out and with mounts: *not run* | `sim/integrated-multiplier-findings.md` §5 | `[OC]` deck; `[IR]` classes; `[RH]` hot | OPEN |
| Mounts, rotor vanes | G10 spacer rings r 20.5–32 × 15 (10), three G10 dowels Ø5 × 93 (6); no node-1 metal on the sleeve below the first rotor vane | `sim/doubler-caps-findings.md` §1; DCCREG-CAP-604, -605 | `[IR]` | PROPOSED |
| Mounts, stator vanes | six lugs per vane at r 173; six glass-epoxy M8 tie rods with G10 spacer tubes, from a G10 end ring to the Ca\|reluctance spider; cage moves to r 182–186 | `sim/doubler-caps-findings.md` §1; DCCREG-CAP-603, -606, -607; P-008 | `[IR]` | PROPOSED |
| Varicap torque ripple, 120 Hz | 191 mN·m p-p (in phase; the record's antiphase 63) | `sim/integrated-multiplier-findings.md` §6 | `[OC]` | DECIDED for now |
| Masses (both sides) | rotor vanes 2.9 kg; stator vanes 3.4 kg | ledger §4 | `[IR]` | DECIDED |

**z against κ** (the record's unipolar doubler, 20 pF strays, Ca 1.1 C_max; `synthesis/core-engine-spec.md` §2.2 grid,
from `sim/core_swing_grid.json`) `[OC]` deck, `[IR]` cosine C(θ):

| C_max \ κ | 3 | 5 | 8 | 13 |
|--:|--:|--:|--:|--:|
| 250 pF | 1.046 | 1.171 | 1.265 | 1.339 |
| 450 pF | 1.083 | 1.224 | 1.332 | 1.417 |

- The unipolar doubler's bare threshold sits near a **node-total ratio of 2.4** (`synthesis/core-engine-spec.md` §2.2,
  `[IR]` grid reading). The redesign's 2.59 is above it, and the redesign self-excites with ideal diodes (z 1.0159).
- **The bipolar redesign's own κ threshold is not mapped.** No study sweeps κ on the redesign's deck. OPEN.
- Larger lever: radius. κ 9.0 / 10.5 / 17.7 at r 175 / 200 / 300 (`sim/vane-matrix-findings.md` §1) `[OC]` deck,
  `[IR]` 2-D cell. The 6 + 6 cap and r 150 are the designer's.
- Solved cheap remedies on the record (rim clearance 6 / 12 mm; PTFE sleeve): z with the record's chains 1.041–1.059 at
  best (`sim/tube-strays-findings.md` §6) `[RH]`. Not run on the redesign.

**Paired records — the redesign's gain, rings and seed** (decision 1; record V_op 13.13 kV, 66-part clamps, 24.5 pF
new-node strays, 5-gap Ca 480.5 pF; `sim/integrated-multiplier-findings.md` §4–§5) `[OC]` deck, `[IR]` stick classes,
`[RH]` hot leakage and strays:

| Record | z at start-up / from 1 kV | z from 10 V | Smallest seed | Rings | Field at null | Ring ripple |
|:--|--:|--:|--:|--:|--:|--:|
| **ideal diodes** | 1.0142 | 1.0142 (scale-free) | any (> 0) | ±14.93 kV | 7.60 kV/cm | 13 V p-p |
| **real sticks, typical (25 nA)** | 1.0129 | 0.9980 | 51 V | ±14.67 kV | 7.47 kV/cm | 20 V |
| **real sticks, maximum (2 µA, 25 °C)** | 1.0039 | 0.9843 | 947 V | ±14.40 kV | 7.33 kV/cm | 148 V |
| **real sticks, hot (5 µA, 100 °C)** † | 0.9870 | 0.9760 | 4.87 kV | ±13.95 kV | 7.10 kV/cm | 328 V |

† **Thermal note (kept, not deleted — decision 1).** The binding temperature is the hub's: glass ≤ 37 °C, so a room of
≤ ≈ 29 °C and rotor air ≤ room + 5 K (`synthesis/electrical-integrity-audit.md` §2.6; `synthesis/retainer-spec.md` §6;
`sim/hub-thermal-findings.md`). At that envelope the decks sit at ≈ room + 5–15 K and the sticks leak ≈ 100–200 nA
(25 nA doubling per 10 K) `[RH]`. The 100 °C / 5 µA "hot" class is a junction state, **not a credible deck temperature**
unless the enclosure fails; the hot rows stay as the record's bounding case.
| *record supply as built, ideal / typ / max / hot (evidence)* | *1.0322 / 1.0244 / 1.0038 / 0.9672* | — | *any / 122 V / 1.0 kV / 3.65 kV* | *±13.86 / ±13.39 / ±12.38 / ±10.80* | *7.06 / 6.82 / 6.31 / 5.50* | — |

As laid out (60-part clamps, layout strays, 5-gap Ca): **ideal** z 1.0164 (1.01589 with mounts), rings ±14.77 kV,
7.50 kV/cm, 11.8 V ripple (`sim/multiplier-waveforms-findings.md`); **real sticks: not run** — the layout's higher ideal
z can only improve them (`sim/multiplier-layout-findings.md` §6) `[IR]`. OPEN. With the sixth gap, both records need a
re-run (OPEN).

**Rationale — the κ discrepancy.** The deck's κ 7.47 is the 2-D cell with a 2 pF rim floor; the 3-D solve of the solids
gives κ 3.51 because each stator sector's inner rim sits over the rotor ring's edge and each rotor sector's outer rim
under the stator ring's, 6 mm apart (`sim/tube-strays-findings.md` §4) `[OC]`. Every redesign number (1.0142 → 1.01589,
the rings, the seeds) already runs on the as-built set (`sim/integrated-multiplier-findings.md` Tags). So 3.51 is the
consistent basis; 7.47 would overstate z by ~0.25 on the record's doubler. **PROPOSED (synthesis):** specify the varicap
by its node-total ratio, not its own κ, and require the redesign's own stack to be field-solved (the in-phase vanes and
the new parts are not solved: `sim/integrated-multiplier-findings.md` Caveats).

---

#### A.2  Node stray budget

Three estimates exist; they describe physically different nodes.

| Estimate | Nodes 1 / 4 | Nodes 2 / 3 | New nodes (l1, r1, l2, r2, xa, xb) | Basis | Tag |
|:--|--:|--:|--:|:--|:--|
| Record placeholder | 20 pF | 20 pF | — | `sim/core_field.py` | `[RH]` |
| Record as built (3-D solve) | 66.2 pF | 24.5 pF | — | `sim/tube-strays-findings.md` §3 | `[OC]` solve |
| Redesign study (assumed) | 66.2 | 24.5 | 24.5 each | `sim/integrated-multiplier-findings.md` Tags | `[RH]` |
| Redesign laid out | 70.80 (+4.6) | 13.66 (−10.8) | l1 / r1 3.3; r2 / l2 1.5; xa / xb 1.1 | `sim/multiplier-layout-findings.md` §6 | `[RH]` formulas |
| **With the capacitors' mounts (allocated here)** | **74.61** (+3.81) | **18.30** (+4.64) | as laid out | `sim/doubler-caps-findings.md` §4 | `[RH]` |

| Parameter | Value | Source / basis | Tag | Status |
|:----------|:------|:---------------|:----|:-------|
| **Budget, nodes 1 / 4** | **≤ 75 pF** (74.61 allocated) | `sim/doubler-caps-findings.md` §4 | `[RH]` | PROPOSED (synthesis) |
| **Budget, nodes 2 / 3** | **≤ 19 pF** (18.30 allocated) | the same | `[RH]` | PROPOSED (synthesis) |
| **Budget, new nodes** | **1–3.5 pF each** (laid-out values) | `sim/multiplier-layout-findings.md` §6 | `[RH]` | PROPOSED (synthesis) |
| Ring strays (behind diodes, beside 100 pF) | 7.21 pF to REF each, 0.99 pF ring to ring (with the can) | `sim/multiplier-layout-findings.md` §5 | `[OC]` solve | PROPOSED (layout) |
| z cost, mounts' increment (+3.81 / +4.64 pF), **ideal** | −0.00048 (1.01636 → 1.01589); **real sticks: not run** | `sim/doubler-caps-findings.md` §5 | `[OC]` deck; `[RH]` strays | PROPOSED; 5-gap basis, re-run OPEN |
| z cost, new-node strays 0 → 40 pF, **ideal** | 1.0165 → 1.0131; **real sticks: not run** | `sim/integrated-multiplier-findings.md` §4 | `[OC]` deck | — |
| Rings vs new-node strays (record V_op), **ideal** | 0 / 5 / 24.5 / 40 pF → ±16.33 / ±15.94 / ±14.98 / ±14.54 kV; **real sticks: not run** | the same | `[OC]` deck | — |
| **Retainer's earthed guard** (Al perforated cylinder, inner r 220; decks 88 mm from it) | **≈ 2–3 pF on each deck node** (sphere-to-plane), against new-node budgets of 1.1–3.5 pF; ≈ −0.15 … −0.3 kV on the rings, about one clamp part. **The clamp trim is set with the guard fitted.** The layout is not re-run with a REF plane at r 220 | `synthesis/retainer-spec.md` §4 (guard strays); `sim/integrated-multiplier-findings.md` §4 | `[RH]` | PROPOSED; re-run OPEN |
| Strays with the sixth Ca gap | the combs' columns and riser lengthen; nodes 1 / 4 and 2 / 3 strays not recomputed | decision 2 | — | OPEN (re-run) |
| Node-1 metal on the sleeve | forbidden; a conductive spacer ring takes node 1 to 105 pF (record z with chains → 1.008) | ledger §6 item 60 | `[OC]` | DECIDED (corrected) |
| Node 1 / 4 in a shaft bore | forbidden: 3.0 pF on 80 mm, 0.008 of z | `sim/multiplier-layout-findings.md` Headline | `[OC]` | PROPOSED (layout) |

**Rationale.** The 66 / 25 pF set is the record's solids; the redesign moves the nodes (no Ca plate faces the utrons now;
the deck's parts are compact discretes), so its own layout estimate is the credible one for the target, and the mounts'
increment is the latest. It remains `[RH]`: formulas, not a field solve. The new-node strays are what matter most here,
because they — not z — set the rings' level (above). **The clamp trim holds at this stray level:** the mounts move the
rings at 66 parts by 9 V (±16.248 → ±16.239 kV, `sim/doubler-caps-findings.md` §5), so the 60-part trim's ±14.77 kV
carries over to within that `[IR]` (not re-run with the mounts at 60).

---

#### A.3  HV sticks (D1–D12) and surge resistors (R1–R4)

| Parameter | Value | Source / basis | Tag | Status |
|:----------|:------|:---------------|:----|:-------|
| Count | **12 sticks**, one per position (D1–D12); none doubled (the record took 14) | `sim/integrated-multiplier-findings.md` Headline; DCCREG-P-002 qty 12 | `[OC]` | DECIDED for now (circuit); PROPOSED (part) |
| Part | 20 kV, 5 mA avalanche HV rectifier stick, 2CL77 class (candidate XCH 2CL77); one lot, no grading resistors | DCCREG-P-002; `sim/parts-first-cut-findings.md` §2.2 | `[IR]` datasheet class | PROPOSED |
| Housing | potted module Ø24 × 66 (body Ø8 × 40), 8 mm silicone | `sim/multiplier-layout-findings.md` §3; DCCREG-DCK-504 | `[RH]` envelope | PROPOSED |
| Reverse peaks, laid out (60-part clamps) | D1 / D2 4.11; D3 / D4 5.86; D5 / D6 5.71; D7 / D8 6.11; D9 / D11 6.10; D10 / D12 3.37 kV | `sim/multiplier-waveforms-findings.md` §2 | `[OC]` deck; `[RH]` strays | PROPOSED |
| Rating margin | worst 6.11 kV → ×3.3 on a 20 kV stick (guidance ×2) | derived | `[IR]` rule | PROPOSED |
| Forward duty | D1–D8: 208.5 nC/cycle, 25.0 µA avg; peaks (1° bins) D1 / D2 0.612, D3 / D4 0.229, D5 / D6 0.146, D7 / D8 0.140 mA. D9–D12: 1.27–1.29 nC, 0.15 µA, ≤ 0.033 mA | `sim/multiplier-waveforms-findings.md` §2 | `[OC]` | PROPOSED |
| Leakage, per stick (model classes) | **typical 25 nA**; **maximum 2 µA (25 °C)**; **hot 5 µA (100 °C)** | `sim/diodes-real-findings.md` (stick model, three levels) | `[IR]` typical/max; `[RH]` hot | OPEN (bench) |
| Leakage loss, all sticks + strings | 4 / 60 / 142 mW (typical / max / hot), redesign as built | `sim/integrated-multiplier-findings.md` Gates | `[OC]` deck; `[IR]` classes | OPEN |
| Surge resistors | **4: R1 (REF → D1, side A), R3 (node 2 → D3, side A); side B the mirror (R2, R4)** | `sim/multiplier-layout-findings.md` §3 (deck A's chain: REF – R1 – D1 – 2 – R3 – D3); ledger Fig. 10 | `[IR]` | PROPOSED |
| Surge resistors on D5–D12 | **8 more of the R1–R4 part** (22 kΩ, ≥ 15 kV, ≥ 1 W, ≥ 0.1 J), one in series with each of D5–D12. Without them a flashover step on the ladder is limited only by the arc and wiring: a 180 pF capacitor at ≈ 6 kV gives amps against a 5 mA stick (FAIL by analogy). RC 22 kΩ × 180 pF ≈ 4 µs ≪ 8.3 ms, so z is not touched to first order. Deck housings and the layout's pair checks then need re-running | `synthesis/electrical-integrity-audit.md` §2.4, §2.5 (A′); record's chain-input resistors `sim/parts-first-cut-findings.md` §2.2 | `[IR]`; `[OC]` RC | **PROPOSED**, pending the redesign's vane-flashover run (**OPEN**) |
| Surge resistor part | 22 kΩ ±5 %, ≥ 15 kV across the body, ≥ 1 W, ≥ 0.1 J single pulse (HV thick-film, or 6 × 3.9 kΩ 0.5 W metal-glaze ≥ 2.5 kV each) | `sim/parts-first-cut-findings.md` §2.2; DCCREG-P-005 qty 4; DCK-505 | `[IR]` | PROPOSED |
| Surge resistor duty | normal ≈ 1.4 mW; record's vane-flashover case 0.30 A peak, 10.3 mJ, τ 10 µs | `sim/parts-first-cut-findings.md` §2.2 | `[IR]` record's case | PROPOSED; redesign flashover not run (OPEN) |

**Seed and self-excitation** (redesign as built, record V_op, 24.5 pF new-node strays; `sim/integrated-multiplier-findings.md` §5):

| Leakage | z from 10 V | z from 1 kV | Smallest seed | Rings | Field at null |
|:--|--:|--:|--:|--:|--:|
| *ideal diodes (paired record)* | *1.0142* | *1.0142* | *any* | *±14.93 kV* | *7.60 kV/cm* |
| typical | 0.9980 | 1.0129 | **51 V** | ±14.67 kV | 7.47 kV/cm |
| maximum | 0.9843 | 1.0039 | **947 V** | ±14.40 kV | 7.33 kV/cm |
| hot † | 0.9760 | **0.9870** | **4.87 kV** | ±13.95 kV | 7.10 kV/cm |
| *record supply as built (evidence)* | *0.9966 / 0.9518 / 0.8808* | *1.0244 / 1.0038 / 0.9672* | *122 V / 1.0 kV / 3.65 kV* | — | — |

Two records and one experiment, side by side (decisions 1 and 3); the bench arbitrates:
- **Model, ideal diodes:** self-excites from any seed (scale-free between diode events) `[OC]`.
- **Model, real sticks:** does **not** self-excite from a few-volt seed — z from 10 V is below 1 at every leakage
  level; seeds 51 V / 947 V / 4.87 kV (typical / maximum / hot); hot it does not start from 1 kV (z 0.9870)
  (`sim/integrated-multiplier-findings.md` §5; ledger §6 items 46, 65) `[OC]` deck; `[IR]` stick classes; `[RH]` hot
  stick and clamp leakage — the likely point where model and experiment part.
- **Designer's experiment (DECIDED as evidence, 2026-10-14):** the simple four-diode doubler self-starts with no HV
  seed, dry or humid (dry easier); a rubbed PVC tube starts it if slow. Not reproduced here; **no data file in the
  repository yet** `[IR]` (reported).
- **The §3.9 redesign** (bipolar, in phase, the C3–C8 ladder, the solved strays) is not the circuit of that
  experiment: **whether it self-starts the same way is OPEN for the bench** (`docs/bench-test-rings.md` phase 4).
- The layout's higher ideal z (1.0164 vs 1.0142) can only improve the real-stick seeds; **not re-run** (OPEN).
- **No seed-source part** (decision 3). K4 (B.5) seeds the magnetic pump only.

#### A.3a  Charge-injection point (PROPOSED (synthesis); geometry OPEN)

| Parameter | Value | Source / basis | Tag | Status |
|:----------|:------|:---------------|:----|:-------|
| Node | **node 1** (side A), the node the model seeds (`sim/integrated-multiplier-findings.md` §5, seeds "on nodes 1 / 4") | the same | `[OC]` | PROPOSED (synthesis) |
| Sign | **negative** on node 1 (side A runs negative, A.0). A rubbed PVC tube charges negative `[OC]` triboelectric series, order of magnitude — it matches node 1 without a sign change. Node 4 (side B) is the positive mirror; a second point there is optional | A.0; `synthesis/core-engine-spec.md` Rec. 5 | `[OC]` sign; `[IR]` PVC | PROPOSED (synthesis) |
| Whether one-sided injection excites the bipolar growing mode | a seed with any component in the growing mode grows (linear between diode events) `[OC]` for ideal diodes; with real sticks not run | `sim/integrated-multiplier-findings.md` | `[IR]` | OPEN (bench) |
| Terminal | a dedicated, smooth full-round electrode on deck A's node-1 junction (outer lane, r 132), not a part lead; potted like the other junctions except its face | `sim/multiplier-layout-findings.md` §3 | `[IR]` | PROPOSED (synthesis); layout OPEN |
| Access | a closable port in the counter-rotor's G10 cage at deck A's station (\|z\| 30–78), turned into line with the terminal with the rotor stopped; insulating tool only (the PVC tube itself, or an insulated probe); port closed in operation | this spec | `[IR]` | PROPOSED (synthesis); OPEN (designer) |
| Clearance, rotor stopped | terminal (r 132) to the cage's bore (r 182): ≈ 50 mm of air (derived), against 12 mm needed deck → cage at 14.9 kV (A.6) | derived from `sim/multiplier-layout-findings.md` §3–§4, `sim/doubler-caps-findings.md` §1 | `[IR]` | PROPOSED |
| Before access | the rings (≈ 107 pF each at ±14.77 kV), Ca / Cb, C3–C8 and the varicaps hold charge after stopping; ground nodes 1 / 4 and both rings with a grounding stick through the port before any approach; the counter-rotor may float (A.0) and is grounded too | A.0; `sim/multiplier-layout-findings.md` §5 | `[IR]` | PROPOSED (synthesis) |
| Injection at rest vs at speed | a charge placed at rest must survive the 32 s run-up against the sticks' and clamps' leakage; not modelled. Injection at speed through the port is a non-contact (induction) act only | `docs/drive-gear-belt.md` (run-up); this spec | `[IR]` | OPEN (bench) |

**Rationale.** One stick per position is sufficient at ×3.3; the surge resistors sit at the two positions that see the
flashover's forward step in the record (D1 / D2, D3 / D4 by analogy) `[IR]`. Whether the ring stages need their own
(the record's chain-input resistors) is not answered: the redesign's flashover case is not run.

---

#### A.4  Clamp strings (Z1, Z4)

| Parameter | Value | Source / basis | Tag | Status |
|:----------|:------|:---------------|:----|:-------|
| Role | avalanche string node 1 → REF (Z1), node 4 → REF (Z4); governor and sink | ledger §3.4 | `[OC]` | DECIDED (10-09) |
| **Count, this synthesis** | **60 × 200 V per string** (120 parts), bench-trimmed | `sim/multiplier-layout-findings.md` §6; ledger §3.9 | `[RH]` strays | PROPOSED (layout) |
| Count, record | 66 × 200 V (13.13 kV) | `sim/parts-first-cut-findings.md` §2.4 | `[IR]` | PROPOSED (first cut) |
| Part | TVS 1.5KE200A class: VBR 190–210 V at IT 1 mA; 1.5 kW 10/1000 µs; 6.5 W steady at 75 °C lead. Alternate: 5 W Zener 1N5388B class | `sim/parts-first-cut-findings.md` §2.4; DCCREG-P-006 | `[IR]` datasheet class | PROPOSED |
| **Target V_op** | **11.94 kV** (deck); 60 × 200 V = 12.0 kV nominal | `sim/multiplier-waveforms-findings.md` | `[OC]` deck | PROPOSED |
| Tolerance | ±5 % parts → ±0.6 kV worst; random lot σ 0.36 %. Sort by VBR at 1 mA; trim with whole parts (1.5 % each, 1.6 % on the rings); a lower-voltage part at the REF end for the last 1 % | `sim/parts-first-cut-findings.md` §2.4; `sim/multiplier-layout-findings.md` §6 | `[IR]` | PROPOSED |
| Temperature | +0.1 %/K → +11.9 V/K on 60 parts; +25 K lifts V_op ≈ 0.30 kV. Trim warm | derived from `sim/parts-first-cut-findings.md` §2.4 | `[IR]` | PROPOSED |
| Duty, each string | 207.2 nC/cycle, 24.87 µA avg, 0.516 mA peak, conducts 25.2–30.2° of 60° | `sim/multiplier-waveforms-findings.md` §2 | `[OC]` deck | PROPOSED |
| Power, each string / both | **0.297 W / 0.594 W** (24.87 µA × 11.94 kV) | derived | `[OC]` | PROPOSED |
| Power per device | ≈ 5.0 mW avg, ≈ 0.10 W peak (0.516 mA × 199 V), against ≥ 1.5 W | derived | `[OC]` | PROPOSED |
| Leakage model (string) | typical 10 nA, maximum 0.5 µA, hot 5 µA; the hot value sets the hot seed | `sim/diodes-real-findings.md` (clamp model); ledger §3.4 | `[RH]` | OPEN (bench) |
| Junction capacitance | C_j / n adds ≈ 1–2 pF to node 1 / 4; in the layout 1.45 pF counted | `sim/parts-first-cut-findings.md` §2.4; `sim/multiplier-layout-findings.md` §6 | `[RH]` | — |
| Module | meander in a potted module, body 34 × 134 × 20, housing 50 × 150 × 36; HV and REF ends at opposite ends; arc on the deck's inner lane | `sim/multiplier-layout-findings.md` §3; DCCREG-DCK-509 | `[RH]` envelope | PROPOSED |

**Rings vs string length** (layout's strays, C3–C6 180 pF, 5-gap Ca; `sim/multiplier-layout-findings.md` §6) `[OC]` deck,
`[RH]` strays. **Ideal-diode record only; the real-stick record at 59–66 parts is not run (OPEN). The whole table is on
the 5-gap basis: the 60-part trim must be re-run with the sixth gap (OPEN).**

| parts | 59 | **60** | 61 | 62 | 66 |
|:--|--:|--:|--:|--:|--:|
| rings | ±14.52 | **±14.77** | ±15.02 | ±15.26 | ±16.25 kV |

**Rationale — the 66 → 60 trim: carried, PROPOSED.** The rings' level follows V_op almost wholly (1.6 % per part); C3–C8
cannot bring the layout's ±16.25 kV down (±16.08 kV even at 100 pF). At 66 the rings stand 8.6 % over the record's
±14.96 kV, where the polar bead sits 0.4 % under its rating (ledger §3.6). 60 is the largest count at or below that
level. Its basis is `[RH]` strays, so the number is a starting length: **the bench sets the final count** (ledger §5.2).
Note: the drawing set still orders 132 parts (DCCREG-P-006 = 2 × 66) — a 12-part over-order, harmless as trim stock.
Hot real-stick operation at 60 parts is not run; the as-built hot rings at 66 sag to ±13.95 kV (A.3), so at 60 they will
sit lower. OPEN.

---

#### A.5  The rings' supply chain (the §3.9 ladder and ring stages)

The record's 2 + 2 CW chains (8 sticks, 8 × 100 pF / 30 kV, 2 chain-input resistors) are **superseded in circuit** by
§3.9 and are not part of this tube. They stay as evidence (ledger §3.6).

| Parameter | Value | Source / basis | Tag | Status |
|:----------|:------|:---------------|:----|:-------|
| Chain diodes | D3–D12 as A.3 (the ladder D3–D8, the ring stages D9–D12); one 20 kV stick each | A.3 | `[OC]` | DECIDED for now / PROPOSED (part) |
| Ring-stage leakage selection | the ring stages (D9–D12) carry only the rings' leakage (0.15 µA): select for IR ≤ 25 nA at working voltage, as the record's chain diodes (3e11 Ω a stage), kept cool | `sim/parts-first-cut-findings.md` §2.3 (record's rule, carried) | `[IR]` | PROPOSED (synthesis) |
| C3–C6 | **4 × 180 pF**, class-1 HV ceramic or PP / PTFE film, 30 kV DC; candidate 190 pF / 30 kV N4700 (Vishay 715C30KTT19) | `sim/integrated-multiplier-findings.md` §4; DCCREG-P-003 qty 4 | `[IR]` | DECIDED for now (value); PROPOSED (part) |
| C7 / C8 | **2 × 100 pF**, 30 kV class | `sim/multiplier-layout-findings.md` §3 | `[IR]` record's chain value | DECIDED for now |
| Csa / Csb | **2 × 100 pF**, 40 kV class (body Ø30 × 24) | the same | `[IR]` | DECIDED for now |
| C7 / C8 / Csa / Csb candidate | 100 pF / 40 kV N4700 (Vishay 715C40KTT10), qty 4 | DCCREG-P-004 | `[IR]` | PROPOSED |
| DC duty (record V_op, the study) | C3 / C4 6.4–9.0 kV; C5 / C6 11.6–12.8; C7 / C8 6.3–6.9; Csa / Csb 14.9; Ca / Cb 11.6–13.2 | `sim/integrated-multiplier-findings.md` §4 | `[OC]` deck | DECIDED for now |
| Rating margin | C5 / C6 12.8 kV on 30 kV: ×2.3; Csa / Csb 14.9 on 40 kV: ×2.7 | derived | `[IR]` | PROPOSED |
| Insulation resistance | ≥ 1e11 Ω guaranteed, ≥ 1e12 Ω measured at working voltage; PD-free at 1.25 × | `sim/parts-first-cut-findings.md` §2.3 (record's chain rule, carried) | `[IR]` | PROPOSED (synthesis) |
| Class-2 ceramics | second choice: DC capacitance loss, piezoelectric on a vibrating rotor | `sim/parts-first-cut-findings.md` §2.3 | `[IR]` | — |
| Envelope conflict | candidates Ø21 × 28 / Ø21 × 31; potted standing 44 / 47 mm, over the deck's 42 mm zone | ledger §6 item 72 | `[RH]` | OPEN |
| Stages | 2-stage ladder per side + 1 ring stage | ledger §3.9 | `[OC]` | DECIDED for now |
| Rings, laid out (60 parts) | **ideal** ±14.77 kV; **real sticks: not run** | `sim/multiplier-waveforms-findings.md` | `[OC]` deck; `[RH]` strays | PROPOSED; 5-gap basis, re-run OPEN |
| Rings, as built (66 parts) | **ideal** ±14.93; **real** ±14.67 / ±14.40 / ±13.95 kV (typ / max / hot) | `sim/integrated-multiplier-findings.md` §4–§5 | `[OC]` deck | DECIDED for now (circuit) |
| Ripple | **ideal** 11.8 V (laid out), 13 V p-p (as built); **real** 20 / 148 / 328 V (as built, typ / max / hot) | `sim/multiplier-waveforms-findings.md`; `sim/integrated-multiplier-findings.md` §4–§5 | `[OC]` deck | — |
| Start-up, 95 % | **ideal** 1.22 s (laid out, cycle 146), 1.45 s (as built), from 1 kV; **real** 1.53 s from 1 kV (typ), 2.73 s from 1.2 kV (max), 0.90 s from 6.1 kV (hot), as built | the same | `[OC]` | — |

**Rationale.** C3–C6 at 180 pF is the study's pick (largest keeping the rings ≤ ±14.96 kV with 24.5 pF strays); with the
layout's strays no value meets that rule, and 180 pF stays where z is highest (`sim/multiplier-layout-findings.md` §6).
The ring stages' 100 pF parts take the record's chain value `[IR]`. C3–C8 are discrete, not plates: as plates C3 / C4
would add a third node to each column and C5 / C6 could not join it (`sim/multiplier-layout-findings.md` §2).

---

#### A.6  Air insulation stack

All gaps in air at atmospheric pressure; vacuum exists only inside the hub's vessel (ledger §3.5).

| Parameter | Value | Source / basis | Tag | Status |
|:----------|:------|:---------------|:----|:-------|
| Vane gap | 6 mm air, uniform-field breakdown 19.7 kV | ledger §3.4, §4 | `[IR]` | DECIDED |
| Margin, record V_op 13.13 kV | 1.50 | ledger §4 | `[RH]` margin rule | DECIDED |
| Margin at 11.94 kV (60 parts) | 1.65 | derived | `[IR]` | PROPOSED |
| Face field | 21.9 kV/cm at 13.13 kV; ≈ 19.9 at 11.94 | ledger §4; derived (linear) | `[OC]` | — |
| Rim field (R1.5) | 44.4 kV/cm at 13.13 kV (0.80 of Peek's 55.7); ≈ 40.4 at 11.94 (0.73) | ledger §3.4; derived | `[OC]`; `[RH]` Peek m | — |
| Rim corona onset | 16.5 kV smooth, 14.0 kV handled → margins ×1.26 / ×1.07 at 13.13; ×1.38 / ×1.17 at 11.94 | `sim/air_stack_sizing_results.json`; derived | `[OC]` solve; `[RH]` m 0.85 | — |
| Ca / Cb gaps | 5 gaps of 6 mm, 13.2 kV DC → 1.49 to breakdown | `sim/multiplier-layout-findings.md` §2 | `[IR]` | DECIDED (layout's DC PROPOSED) |
| Ca tab crossing (other comb's bore edge) | 45.0 kV/cm vs 47.3 handled → margin **1.052** at 11 mm; < 1 below 7 mm; posts ≥ 8 mm from the other bore | `sim/doubler-caps-findings.md` §3 | `[OC]` solve; `[RH]` m | PROPOSED |

**Interfaces** (clearance IEC 60664-1 F.2 case A at 1.5 × peak; creepage at PD2 × 1.25; `sim/multiplier-layout-findings.md` §4, `sim/doubler-caps-findings.md` §2) `[IR]` method:

| Interface | Peak / rms kV | Needed: clearance; creepage PTFE / G10 | Layout gives | Status |
|:--|--:|:--|:--|:--|
| Ca plates node 1 ↔ 2 | 13.2 / 12.3 | —; 77 / 153 mm | no support touches two adjacent plates (combs) | PROPOSED |
| column node-2 plate ↔ can disc | 4.5 / 3.1 | 6.5; 20 / 39 | 30 mm steatite standoffs | PROPOSED |
| column node-2 ↔ deck parts | 19.5 / 17.7 | 38.9; 110 / 221 | 39 mm (sets the column) | PROPOSED |
| riser (node 1) ↔ node-2 bores | 13.2 / 12.3 | 24.7 | PTFE HV wire ≥ 20 kV DC, 13.5 mm off | PROPOSED |
| post ↔ post | — | 24.7 | 27 mm | PROPOSED |
| deck A ↔ deck B | 29.9 / 29.9 | 67.2; 187 / 373 | 72 mm | PROPOSED |
| decks ↔ cage | 14.9 | 12 (record rule) | 32 mm (cage r 182) | PROPOSED |
| cross nets ↔ can | 6.4 / 5.2 | 10.4; 33 / 66 | 82 mm | PROPOSED |
| ring lead ↔ can wall | 14.9 | 28.8 | PTFE bushing (DCCREG-CAN-403), continuous insulation | PROPOSED |
| sleeve, first rotor vane ↔ can disc | 13.2 / 9.9 | —; 62 / 123 | 84 mm under a PTFE cover (SHF-306) | PROPOSED |
| **sleeve outer end, last rotor vane ↔ Ca\|reluctance bearing** | 13.2 / 9.9 | —; 62 / 123 | **17.5 mm + two 12 mm PTFE sheds = 65.5 mm** (SHF-307): 1.06 counted at PTFE's rate, but **0.92–1.01 (FAIL) counting the bare 17.5 mm as G10** (`synthesis/electrical-integrity-audit.md` §2.2). **Carry a third shed (+24 mm) or a PTFE cover over the 17.5 mm** | PROPOSED (synthesis) |
| C1 rims ↔ new G10 | 11.99 | 12 (record rule); **≈ 22.5 mm on the IEC case A basis** | 15–18 mm: 1.13–1.30 on the IEC basis | PROPOSED; **CONCERN for the designer**: the 12 mm rule is unaudited — field-solve rim-to-G10 with the G10's REF backing, or open to ≥ 22.5 mm (`synthesis/electrical-integrity-audit.md` §2.1) |
| deck worst pair (D12–Z1) | 11.4 | 21.0 bare | 21.7 mm bare (+ ≥ 16 mm silicone) | PROPOSED |
| clamp HV end ↔ can | — | 24.7 | 25 mm | PROPOSED |
| cross-hub LV leads | coax estimate 1.34 kV/mm vs PEEK 5.55 | — | in grooves at r 39 | PROPOSED; field solve OPEN |

**The field at the hub shell.** The grounded Al can (r 46–48, |z| ≤ 85, DCCREG-CAN-401) is the hub's REF boundary and
screens it from the decks' ±3 kV 120 Hz swing; it scales the null's field × 0.9973 → **7.50 kV/cm at ±14.77 kV**
(`sim/multiplier-layout-findings.md` §5) `[OC]`. Inside the hub (locked, interface only): gel at the beads 4.98 / 4.46
kV/mm at ±14.96 kV as drawn; the air outside the coupler ≤ 0.55 kV/mm (ledger §3.5–§3.6). At ±14.77 kV these scale by
0.987 `[IR]` linear. **Potting:** addition-cure silicone, vacuum-cast void-free, ≥ 8 mm over 13.2 kV parts; accept on
< 10 pC at 1.25 × working voltage (`sim/parts-first-cut-findings.md` §5) `[IR]`. Full audit: electrical-integrity.

---

#### A.7  Integrated multiplier layout

Per side, |z| from the hub's centre, side A below, side B the mirror (`sim/multiplier-layout-findings.md` Headline;
`sim/doubler-caps-findings.md`; ledger §3.9) `[IR]` — all PROPOSED (layout):

| \|z\| (mm) | What | Body |
|:--|:--|:--|
| 0–72 / 72–80 | the hub as locked (PEEK retainer, G10 coupler to r 33); the shaft half's flange r 32 × 8 | rotor |
| 0–85 (r 46–48) | grounded Al can, Ø96 × 2 × 170, end discs at 85–87 (CAN-400 to -403) | rotor (REF) |
| 30–36 / 36–78 | **the deck**: G10 ring plate r 50–150 × 6 (DCK-502), its parts potted | rotor |
| 117–165 (5-gap basis) | **the column**: Ca (Cb), full-annulus Al plates; node-2 comb toward the deck on 3 steatite standoffs; node-1 comb hung from the first rotor vane on Ø8 Al posts. **DECIDED 10-14: 7 plates / 6 gaps → 57 mm, +9 mm a side (A.8); the stations outward of it shift unless re-laid (OPEN)** | rotor |
| 171–273 | **the vane stack** C1 (C2), 6 + 6, rotor vane at hub end | rotor / counter-rotor |
| 289 | Ca\|reluctance bearing on its G10 spider (Ø364) | — |
| 299–487 | reluctance section (utrons, bridges, the AH-drive wedges) and end slots | rotor / counter-rotor |

**Deck placement** (`sim/multiplier-layout-findings.md` §2–§3) `[OC]` graph, `[IR]` plan:
- **Deck A:** D1, D3, D5, D8, D11, D12; C3, C6, C8, Csa; Z1; R1, R3. **Deck B:** D2, D4, D6, D7, D9, D10; C4, C5, C7,
  Csb; Z4; R2, R4.
- **Only l1 and r1 cross** between the decks (mirror nets, −6.4 … +6.4 kV), on PTFE HV wire (FEP 20 kV, DCCREG-P-009):
  the minimum, since the ladder's graph holds two odd cycles.
- **Outer lane r 132:** the eight sticks and two resistors as one chain REF – R1 – D1 – 2 – R3 – D3 – r1 | l1 – D5 – r2
  – D8 – 1 – D11 – xa – D12 – ea, junctions in potted blocks (DCK-503, 20 per machine).
- **Inner lane r 85–102:** C3, C6, C8 standing; Z1 arc module. **Csa at r 126.** A 44° open sector parts ring A's lead
  from R1's REF end. REF straps to the can.
- **Node-1 riser:** PTFE HV wire in the column's bore at r 35, landing under the first post at Ca_05.
- **Rings' leads:** each from its equatorial bead along the coupler to |z| ≈ 50, out through the can in a PTFE
  bushing to its Csa / Csb.
- **Deck mass:** 1.85 kg each (1.16 parts + silicone, 0.70 plate); centroid 13.3 mm off axis (24.6 kg·mm); balanced with
  the rotor to G2.5 by masses on the can `[RH]`.
- **3-D check:** 552 solids (with the mounts), no clash in 1447 pairs, no sweep hit; least housing gap 1.86 mm (D5–C8)
  (`sim/doubler-caps-findings.md` Headline; `sim/multiplier-layout-3d-findings.md`) `[OC]` geometry.

**Node voltages, laid out, 60-part clamps** (side A; side B sign-flipped within 0.07 V; `sim/multiplier-waveforms-findings.md` §2) `[OC]` deck, `[RH]` strays:

| node | 1 | 2 | l1 | r1 | r2 | xa | ring A |
|:--|:--|:--|:--|:--|:--|:--|:--|
| kV min / max | −11.99 / −6.45 | 0 / +4.11 | −5.86 / −2.99 | +2.99 / +5.86 | −8.70 / −5.29 | −14.77 / −11.40 | −14.78 / −14.76 |

**Cycle order** (0° aligned): D5 / D6 10.5–22.8°; D1 / D2 22.7–26.3°; Z1 / Z4 25.2–30.2°; D9 / D11 25.3–26.5°;
D10 / D12 39.7–40.0°; D3 / D4 39.8–59.7°; D7 / D8 41.2–59.8° (`sim/multiplier-waveforms-findings.md` Headline) `[OC]`.

---

#### A.8  Transfer capacitors Ca / Cb

| Parameter | Value | Source / basis | Tag | Status |
|:----------|:------|:---------------|:----|:-------|
| **Gap count** | **7 full-annulus Al plates / 6 gaps of 6 mm per side** | designer 2026-10-14 ("sixth gap ok"); `sim/tube-strays-findings.md` §6 | `[IR]` rule | **DECIDED (10-14)** |
| **Target value** | **495 pF = 1.1 C_max** (1.1 × 450 pF solved) | `sim/tube-strays-findings.md` §6; ledger §6 item 55 | `[OC]` rule | DECIDED |
| Column length per side | 7 × 3 mm + 6 × 6 mm = **57 mm** (5-gap 48 mm): **+9 mm a side, +18 mm the machine** | derived from ledger §4 (48 mm for 6 plates / 5 gaps) | `[OC]` arithmetic | DECIDED (consequence) |
| Added plate mass | ≈ +0.51 kg a side (6.1 kg / 12 plates), +≈ 0.01 kg tabs; ≈ +1.0 kg on the rotor; plus one comb's longer posts (not counted) | derived from ledger §4, `sim/doubler-caps-findings.md` §6 | `[IR]` | DECIDED (consequence) |
| Capacitance of 6 identical gaps | the laid-out plates give 480.5 pF on 5 gaps (≈ 96 pF a gap); 6 identical gaps scale to ≈ 577 pF (1.28 C_max) `[IR]` linear. **Meeting 495 pF exactly needs a smaller plate overlap; how is not specified** | derived from `sim/doubler-caps-findings.md` §4 | `[IR]` | **OPEN** (designer / solve) |
| Comb parity | 7 plates leave both column ends on one node: either node 1 at both ends (a node-1 plate toward the deck and the can's disc, where the 5-gap layout puts node 2 and sets its 39 mm and 30 mm standoff on node 2's 19.5 / 4.5 kV) or node 2 at both ends (a node-2 plate facing the first rotor vane across a 6 mm gap). Neither is laid out. **Constraint: node 1 at both column ends.** Node 2 at the vane end faces the first rotor vane with ≈ 16.1 kV (node 2 +4.11 against node 1 −11.99) on 6 mm: margin 1.21 (1.04 hot / 0.98 at altitude), FAIL as a bound. Node 1 at the deck end then needs the column ↔ deck (39 mm) and the standoffs (30 mm steatite, ≈ 12 kV → 1.92, CONCERN) re-checked | derived from `sim/doubler-caps-findings.md` §1, `sim/multiplier-layout-findings.md` §4; `synthesis/electrical-integrity-audit.md` §2.1, §2.2 | `[IR]` | **PROPOSED** (node 1 both ends); **the designer confirms**; re-lay OPEN |
| Construction (5-gap layout, carried for method) | two combs on posts in the column's bore (r 50 → 27 tabs); no support touches two adjacent plates | `sim/doubler-caps-findings.md` §1; CAP-610 to -617 | `[IR]`; `[RH]` sizes | PROPOSED (mounts); re-draw OPEN |
| 5-gap values (superseded as target) | 480.5 pF laid out; 482.3 pF with the tab fringe (1.072 C_max) | `sim/doubler-caps-findings.md` §4 | `[OC]` / `[RH]` | evidence |
| DC | 11.6–13.2 kV (the record's 6.9) — 5-gap, record-V_op deck | `sim/integrated-multiplier-findings.md` §4 | `[OC]` deck | DECIDED for now; re-run OPEN |
| Posts | node-1 comb: Ø8 Al spacers + M4 studs (30, CAP-616); node-2 comb: glazed steatite standoffs Ø16 × 30, M4 inserts (6, CAP-617; custom part, PTFE alternate) | `sim/doubler-caps-findings.md`; ledger §5.2 | `[IR]` | PROPOSED |
| Plates' Al mass (both sides), 5-gap | 6.1 kg (+0.105 kg tabs); 7-plate ≈ 7.1 kg (derived) | ledger §4; `sim/doubler-caps-findings.md` §6 | `[IR]` | — |

**Results computed on the 5-gap Ca (480.5 / 482.3 pF) — re-run OPEN with the sixth gap** (none re-valued here):

| Result | 5-gap value | Source |
|:--|:--|:--|
| z at start-up, ideal (laid out / with mounts) | 1.0164 / 1.01589 | `sim/multiplier-layout-findings.md` §6; `sim/doubler-caps-findings.md` §5 |
| z, rings, seed with real sticks (as built) | A.1 paired table | `sim/integrated-multiplier-findings.md` §5 (as-built set's Ca) |
| Ring levels (66 / 60 parts) and the 60-part trim | ±16.25 / ±14.77 kV | `sim/multiplier-layout-findings.md` §6 |
| Node voltages, charge per cycle, conduction angles, reverse peaks | A.7, A.3 | `sim/multiplier-waveforms-findings.md` |
| Node strays 1 / 4 and 2 / 3 (combs, riser) | 74.61 / 18.30 pF | `sim/doubler-caps-findings.md` §4 |
| Tab-crossing count and corona margin 1.052 | 15 crossings | `sim/doubler-caps-findings.md` §3 |
| Column ↔ deck 39 mm, standoff 30 mm (set on node 2 facing the deck) | A.6 | `sim/multiplier-layout-findings.md` §4 |
| Tube length 1014 mm; machine −105.5 to 1014 | C.1 | ledger §3.9; `sim/rotor-parts-drive-findings.md` |
| Rotor mass 35.88 kg; f1 79–85 Hz; f2 108–117 Hz | C.1, C.3 | `sim/doubler-caps-findings.md` §6; `sim/rotor-parts-drive-findings.md` |
| Clamp power, ES belt power | A.4, budget | `sim/multiplier-waveforms-findings.md` |

---

### B. Motor parts (provisioned from the current design)

All PROVISIONED: carried with their validated ratings from the first cuts, not redesigned. Places per
`sim/rotor-parts-drive-findings.md` (PROPOSED, 10-12).

#### B.1  D1*–D4* (motor rectifier diodes)

| Parameter | Value | Source / basis | Tag | Status |
|:----------|:------|:---------------|:----|:-------|
| Type | Schottky, DO-201AD; candidates on DCCREG-P-016 (2 + 2) | `sim/parts-first-cut-findings.md` §2.1; P-016 | `[IR]` datasheet class | PROPOSED |
| D1* / D2* | 200 V (VR 113 / 104 V with start-up, ×1.8); IF 0.81 A avg, 1.00 A rms, 1.90 A peak | the same | `[OC]` duty; `[IR]` rating | PROPOSED |
| D3* / D4* | 150 V (100 V minimum); VR 58 / 60 V (×2.5); IF 1.07 A avg, 1.45 A rms, 2.27 A peak | the same | `[OC]`; `[IR]` | PROPOSED |
| Current rating | ≥ 3 A average, 5 A preferred (heat) | the same | `[IR]` | PROPOSED |
| Loss | 2.42 W the four, with the bypass (0.44–0.59 W each) | `sim/diodes-real-findings.md` §3.3; `sim/parts-first-cut-findings.md` §2.1 | `[IR]` | PROPOSED |
| Place | side A wedge S2 (180°): D1*, D3*; side B S2: D2*, D4* | `sim/rotor-parts-drive-findings.md` | `[IR]` | PROPOSED |

**Rationale — Schottky over silicon PN.** A 1N540x-class rectifier drops 0.85 V at 1 A against the deck's 0.54 V: z_early
1.139 → 1.074, AH 449 → 423 A-turns, 3.04 W in the diodes, and a 25–28 % kick threshold that K4's 20 % seed does not
meet. The Schottky set keeps z 1.141 and a 16.4–17.2 % threshold (`sim/parts-first-cut-findings.md` §2.1;
`sim/diodes-real-findings.md` §3) `[IR]`. With the 3-D utrons and the neck map, the threshold is 25–30 % for every set
(`sim/start-3d-findings.md`; `sim/neck-nonlinear-findings.md` §7) — the drop then matters for running gain, not for
whether K4 can start it at full speed.

#### B.2  La / Lb (chokes)

| Parameter | Value | Source / basis | Tag | Status |
|:----------|:------|:---------------|:----|:-------|
| Inductance | 0.146 H DC | ledger §4 | `[OC]` deck | DECIDED (the pick) |
| Core | EI-84 × 35 mm stack, M400-50A class (M235-35A alternate) | `sim/parts-first-cut-findings.md` §1; REL-720; P-019 | `[IR]` | PROPOSED |
| Winding | 150 turns Ø1.40 mm grade-2 enamelled Cu, 7 layers × 24 | `sim/parts-first-cut-findings.md` §1; REL-721 | `[IR]` | PROPOSED |
| Gap | 0.126 mm (spacer 0.063 mm), trimmed on test to 0.146 H | the same | `[IR]` | PROPOSED; trim OPEN (bench) |
| R (20 °C) | 0.276 Ω (deck 0.29 Ω); τ 0.53 s | the same | `[OC]` | PROPOSED |
| Duty | 0.87–1.15 A at 120 Hz; ≤ 110 V (La), 101 V (Lb) | ledger §4; `sim/rotor-parts-duty-findings.md` | `[OC]` | — |
| B_pk | 1.20 T; knee at 1.39 A (×1.21) | `sim/parts-first-cut-findings.md` §1 | `[OC]` | PROPOSED |
| Losses, each | copper 0.33 W; iron 0.21 W (M400-50A) / 0.12 W (M235-35A) | the same | `[OC]`; `[RH]` iron | PROPOSED |
| Mass / outline | 1.665 kg; 84 × 70 × 61 mm over the bobbin's flanges | ledger §6 item 75; `sim/rotor-parts-drive-findings.md` | `[IR]` | PROPOSED |
| Place | wedge S1 (60°) of each reluctance bay; wedge centroid r 70.6 mm, 545 N at 600 rpm (852 N at 750) | `sim/rotor-parts-drive-findings.md` §2 | `[OC]` | PROPOSED |
| Alternate | compact EI-66 choke, 1.19 kg — cuts the ballast by about a third | ledger §5.2 | `[IR]` | OPEN (designer) |
| Coupling to the utrons | not computed | ledger §5.2 | — | OPEN |

#### B.3  AH bypass capacitors

| Parameter | Value | Source / basis | Tag | Status |
|:----------|:------|:---------------|:----|:-------|
| Count / value | 2 × 22 mF, one across each AH coil (LC 34 Hz) | `sim/ah-steady-cusp-findings.md`; ledger §3.3 | `[OC]` | PROPOSED |
| Part | 6.3–10 V Al electrolytic, 105 °C, ≥ 2 A rms at 120 Hz, ESR ≤ 20 mΩ; snap-in 22 mF 10 V (P-018) | `sim/parts-first-cut-findings.md` §2.6; P-018 | `[IR]` | PROPOSED |
| Polarity | + to nodes d / b; ≤ 1.3 mV reverse in every run | the same | `[OC]` | PROPOSED |
| Duty | −0.54 … −0.44 V; 0.63 A rms; 7.9 mW the pair at 10 mΩ `[RH]` | the same | `[OC]` | — |
| Effect | null within ±0.44 mm (±6.4 mm without); 290–308 A-turns per coil | ledger §3.3 | `[OC]` | — |
| Place | wedge S2, bypass A / bypass B; "behind the bore's leads" routing OPEN | `sim/rotor-parts-drive-findings.md`; ledger §5.2 | `[IR]` | PROPOSED; routing OPEN |
| Do not use | 2.2 mF: resonates near 107 Hz | ledger §3.3 | `[OC]` | — |

#### B.4  Node snubbers

| Parameter | Value | Source / basis | Tag | Status |
|:----------|:------|:---------------|:----|:-------|
| Count | 8: side A at a, d, x1, f2; side B at b, c, x2, f3 | `sim/rotor-parts-drive-findings.md` | `[IR]` | PROPOSED |
| C | 22 nF ±10 % polypropylene film, 250 V DC, pulse-rated (deck 21 nF) | `sim/parts-first-cut-findings.md` §2.5; P-017 | `[IR]` | PROPOSED |
| R | 240 Ω E24 (deck 243 Ω), 0.5 W, pulse-rated, non-inductive | the same | `[IR]` | PROPOSED |
| Duty | ≤ 113 V, ≤ 1.7 V/µs; R ≤ 4.2 mW avg (1.1–3.9 by node), ≤ 0.30 W peak | the same | `[OC]` | — |
| Tuning | to the real winding capacitance on the bench | the same | `[IR]` | OPEN (bench) |

#### B.5  K4 start kick (the magnetic pump's seed)

| Parameter | Value | Source / basis | Tag | Status |
|:----------|:------|:---------------|:----|:-------|
| Storage | 470 µF bipolar electrolytic, 25 V | `sim/parts-first-cut-findings.md` §3; REL-730 | `[IR]` | PROPOSED |
| Source | 9 V lithium primary cell through 10 kΩ | the same | `[IR]` | PROPOSED |
| Switch | SCR ≥ 400 V, ≥ 1 A; gate pulsed by a rotor reed switch past an outside magnet | the same | `[IR]` | PROPOSED |
| Dump | across La, + to node a: 19 mJ, 0.60 A peak, 17 ms; one kick per charge | the same | `[OC]` deck | PROPOSED |
| Seed need | record 2-D: 16 % of Ψs (2.2 mJ); 20 % seeds 0.110 A, 3.48 mJ; fast dump needs ≈ 8 mJ stored. 3-D utrons 20–25 %; with the neck map 25–30 % | ledger §4; `sim/start-3d-findings.md`; `sim/neck-nonlinear-findings.md` §7 | `[OC]` | — |
| Fire speed | full speed, 600 rpm each way; never below 500 (550 with the 3-D utrons) | the same | `[IR]` | PROPOSED |
| Place | side A wedge S3 (300°); the reed magnet's place OPEN | `sim/rotor-parts-drive-findings.md`; ledger §5.2 | `[IR]` | PROPOSED; magnet OPEN |
| Alternate | 22 µF PP film at 50 V (27.5 mJ, 4.5 ms), needs a 50 V source | `sim/parts-first-cut-findings.md` §3 | `[IR]` | — |

**K4 is not the electrostatic pump's seed.** The ES pump carries no seed-source part (decision 3, DECIDED 10-14): the
designer's experiment self-starts the four-diode doubler; the injection point A.3a is the fallback. The ledger's §5.2
candidates (a one-shot HV seed fired with K4; a tap through an HV diode) are not carried.

---

### C. Physical arrangement

#### C.1  Tube envelope

| Parameter | Value | Source / basis | Tag | Status |
|:----------|:------|:---------------|:----|:-------|
| Tube length (layout, bridge-ring bearings), 5-gap | **1014 mm** (record 940; layout without them 974) | ledger §3.9 | `[IR]` solids | PROPOSED |
| Tube length with the sixth Ca gap | 1014 + 2 × 9 = **≈ 1032 mm** if every station outward of the columns shifts (derived); machine to ≈ 1032, frame bearings ≈ 1078 mm apart. Not laid out | derived (A.8) | `[IR]` | DECIDED (gap) / OPEN (re-lay) |
| Machine extent with the drive (re-cut, side A) | z −105.5 (bell's foot) to 1014 mm; frame bearings 1060 mm apart | `sim/rotor-parts-drive-findings.md` Headline | `[IR]` | PROPOSED |
| Outer radius (counter-rotor) | cage tube G10 r 182–186 (Ø364 / 372, CGE-901); spiders to r 182 | `sim/doubler-caps-findings.md` §1 | `[IR]` | PROPOSED |
| Rotor's outer radius in the vane bays | r 150 (rotor vanes, decks, Ca plates) | ledger §4; `sim/multiplier-layout-findings.md` | `[IR]` | DECIDED / PROPOSED |
| Reluctance bays | utrons r 57–130; bridges r 130.5–144.5 in a G10 ring r 131.5–156.5 (counter-rotor) | ledger §4 | `[IR]` | DECIDED |
| Rotor mass, layout with mounts (5-gap) | 35.88 kg; **+≈ 1.0 kg with the sixth gap (≈ 36.9 kg, derived)** | `sim/doubler-caps-findings.md` §6; A.8 | `[IR]` solids | PROPOSED; re-count OPEN |
| + AH-drive parts (choke, cradles, small parts, ballast) | +9.74 kg (4.88 a side, 3.27 ballast a side) → 45.6 kg (derived); the two-body model reads 50.4 kg with the parts and the drive's rotor-side solids | `sim/rotor-parts-drive-findings.md` | `[OC]` / `[IR]` | PROPOSED |
| Counter-rotor mass | 36.40 kg | `sim/doubler-caps-findings.md` §6 | `[IR]` | PROPOSED |
| Balance | each body G2.5 (1732 g·mm limit); wedges balance per side to 0.013 g·mm residual; decks by masses on the can after potting | `sim/rotor-parts-drive-findings.md` §2; `sim/multiplier-layout-findings.md` §3 | `[OC]` / `[RH]` | PROPOSED |
| Rotating loads | no banding (factors ≥ 19 at 750 rpm) if studs preloaded and joints bonded | ledger §3.1 | `[OC]` | DECIDED (record) |

#### C.2  Parts list and placement (both sides; the drawing set's quantities)

| Part | Qty | Spec | Location | Sheet | Status |
|:--|--:|:--|:--|:--|:--|
| Rotor vanes | 12 | Al 3 mm, R1.5 (r01 first vane, hands A / B) | vane stacks, \|z\| 171–273 | CAP-601, -602 | PROPOSED (drawn) |
| Stator vanes | 12 | Al 3 mm with six lugs | vane stacks (counter-rotor) | CAP-603 | PROPOSED |
| Vane mounts | 10 + 6 + 72 + 2 + 12 rods | G10 spacer rings, dowels, spacer tubes, end rings; glass-epoxy M8 | vane stacks | CAP-604–607; P-008 | PROPOSED |
| Ca / Cb plates | **14** (7 a side, DECIDED 10-14; the drawing set has 12) | Al full annuli with 3 tabs; overlap to give 495 pF OPEN | columns, \|z\| 117 → ≈ 174 | CAP-611–615 (re-draw OPEN) | DECIDED (count) |
| Comb posts / standoffs | 30 / 6 | Ø8 Al, M4 / steatite Ø16 × 30 | column bores, r 35 | CAP-616, -617 | PROPOSED |
| HV sticks D1–D12 | 12 | 20 kV, 5 mA, 2CL77 class, potted | decks, outer lane r 132 | P-002; DCK-504 | PROPOSED |
| Surge resistors R1–R4 | 4 (+8 on D5–D12, PROPOSED pending the flashover run, A.3) | 22 kΩ, ≥ 15 kV, ≥ 1 W, ≥ 0.1 J | decks, outer lane | P-005; DCK-505 | PROPOSED |
| C3–C6 | 4 | 180 pF / 30 kV class 1 (190 pF candidate) | decks, inner lane | P-003; DCK-506 | DECIDED for now (value) |
| C7 / C8 | 2 | 100 pF, 30–40 kV class 1 | decks, inner lane (C8 under r2) | P-004; DCK-507 | DECIDED for now |
| Csa / Csb | 2 | 100 pF / 40 kV | decks, r 126 | P-004; DCK-508 | DECIDED for now |
| Clamp strings Z1 / Z4 | 2 × 60 (P-006 orders 132) | 1.5KE200A class, sorted, potted meander | decks, inner lane arc | P-006; DCK-509 | PROPOSED |
| Junction blocks | 20 | potted terminals | decks | DCK-503 | PROPOSED |
| Deck plates | 2 | G10 r 50–150 × 6 | \|z\| 30–36 | DCK-502 | PROPOSED |
| Can | 1 | Al Ø96 × 2 × 170, two end discs, two PTFE lead bushings | over the hub, REF | CAN-400–403 | PROPOSED |
| HV wire, deck nets | per DCK-501 | FEP 20 kV 18 AWG (UL3239) | node-1 riser, cross nets l1 / r1 | P-009 | PROPOSED |
| HV wire, **rings' leads** | 2 | **≥ 30 kV DC** (30 kV UL3239, or a ≥ 40 kV DC silicone lead); UL3239's ratings are AC, DC rating to confirm with the maker. A 20 kV lead holds 1.35 at 14.77 kV and 1.06 in the flashover case: FAIL against the record's rule | ring bead → coupler → CAN-403 bushing → Csa / Csb | DCK-501, CAN-403, P-009; `synthesis/electrical-integrity-audit.md` §2.2, §2.4 | PROPOSED |
| Sleeve cover / sheds | 2 / 4 (+2 if the third shed is taken, A.6) | PTFE | vane-bay sleeve, outer ends | SHF-306, -307 | PROPOSED |
| D1*–D4* | 4 | Schottky 200 / 150 V, ≥ 3 A | wedges S2 | P-016 | PROPOSED |
| La / Lb | 2 | EI-84 × 35, 150 t, 0.146 H | wedges S1 | REL-720, -721; P-019 | PROPOSED |
| AH bypass | 2 | 22 mF 10 V snap-in | wedges S2 | P-018 | PROPOSED |
| Snubbers | 8 + 8 | 22 nF PP 250 V + 240 Ω 0.5 W | wedges S2 | P-017 | PROPOSED |
| K4 | 1 | 470 µF + 9 V cell + 10 kΩ + SCR + reed | side A wedge S3 | REL-730 | PROPOSED |
| Wedge cradles | 6 | G10 end plates + backplate r 110–116; 8 × M5 a wedge | reluctance bays | `sim/rotor-parts-drive-findings.md` §1 | PROPOSED |
| Brass ballast | 1.09 kg (S2) ×2; 1.02 (S3 A); 1.16 (S3 B) | — | wedges S2 / S3 | `sim/rotor-parts-drive-findings.md` §2 | PROPOSED |
| LV cable | 2 | the magnetic pump's leads, 8 mm shaft bore | shaft halves | P-010; SHF-301 / -302 | PROPOSED |
| Cross-hub LV leads | 2 | b → bay A, d → bay B, flange grooves, coupler r 39 | through the can | `sim/rotor-parts-drive-findings.md` §3 | PROPOSED |

**Balance consideration.** The ES decks are mirror-placed; their static sums cancel but leave a couple (24.6 kg·mm per
deck), so the rotor is balanced after potting with masses on the can `[RH]`. The AH-drive parts balance per side by
solved brass ballast `[OC]`. Three equal wedge moments 120° apart sum to zero, and the utrons' pulls are three-fold
symmetric (ledger §6 item 77).

#### C.3  Shaft interface

| Parameter | Value | Source / basis | Tag | Status |
|:----------|:------|:---------------|:----|:-------|
| Diameter | **Ø25 drawn** (SHF-301 / -302) vs **d 30** in the hub's register | ledger §3.1, §6 items 2, 30 | `[IR]` | **OPEN (designer)** |
| Journals | 25 mm (a 6205 needs them) | ledger §3.1 | `[OC]` | DECIDED (bearing class) |
| Material | annealed austenitic stainless, μ_r ≤ 1.05 (Ti drops f1 to 21 Hz) | ledger §3.1 | `[IR]` | DECIDED |
| Split | two halves at the hub; flanges r 32 × 8 at ±72–80 mm (locked hub), turned to Ø60 for the G10 coupler (SHF-303) | ledger §3.5; `presets/hub-locked.json` | `[IR]` | DECIDED (layout) / PROPOSED (Ø60) |
| Sleeves | G10, vane bay r 12.5–20.5 (SHF-304); reluctance bay (SHF-305) | ledger §4; drawing set | `[IR]` | PROPOSED |
| **Sleeve bond** | **bonded void-free** to the shaft at the bore and to the rotor vanes' ring (as SHF-300's notes). An unbonded film ≥ ≈ 60 µm at the bore sees ≈ 9 kV/mm at 11.99 kV and discharges every 120 Hz cycle (Paschen margin 0.96 at 100 µm, 0.79 at 200 µm); the ring-to-sleeve film holds 1.28–1.98 (CONCERN). Alternative of record: a conductive bore at REF | `synthesis/electrical-integrity-audit.md` §2.1 (sub-millimetre films); `sim/core-field-findings.md` §7 | `[OC]` Paschen | PROPOSED; bond inspection OPEN (bench) |
| LV bore | 8 mm in each half, flange face → reluctance bay, ≈ 1 % of stiffness | ledger §6 item 67 | `[IR]` | PROPOSED |
| Bearings (layout) | 6 × SKF 6205-2Z (25 / 52 / 15, C 14.8 kN, C0 7.8 kN, P5): 2 Ca\|reluctance (\|z\| 289), 2 bridge-ring, 2 end/frame; **no hub-face bearings** | `sim/bridge-ring-bearings-findings.md`; P-001 qty 6; BRG-800–814 | `[IR]` catalogue via web | PROPOSED |
| Bridge-ring bearings | in the record's end slots, stainless cartridges in 8 mm G10 spiders + 6 mm G10 ring adapter, 9 mm from the utrons' end turns; bottom locates the counter-rotor (331 N, L10 217 000 h) | `sim/bridge-ring-bearings-findings.md` | `[IR]` | PROPOSED |
| Side A after the drive re-cut | bridge-ring bearing A (machine z 22.5–37.5) takes the gear-end bearing; frame end bearing A goes, the case-floor locating bearing (z −63.5 to −48.5) is the frame bearing; shaft to z −102.5 with the rotor gear's keyway | `sim/rotor-parts-drive-findings.md` Headline | `[IR]` | PROPOSED |
| Preload | record 100 N spring vs SKF rule 125–250 N at d 25 | `sim/bridge-ring-bearings-findings.md` | `[IR]` | OPEN (designer) |
| Runout budget | ≤ 0.027 mm per inner bearing as laid out (P5, axial spring preload); 0.05 mm with the eighth pair | ledger §3.1 | `[OC]` | — |
| Drive | bevel reverser at side A (two stainless side gears z 30 m 2, three POM-C pinions); HTD 5M 4 : 1 from a 200 W BLDC; 0.48 / 0.52 N·m on the bodies, 1.00 N·m into the frame; 32 s run-up | `docs/drive-gear-belt.md`; ledger §3.1 | `[IR]` | PROPOSED (first cut, re-cut 10-12) |
| Modes, d 25 (with mounts) | f1 81.1 Hz (G10 spiders) / 85.1 (stiff) | `sim/doubler-caps-findings.md` §6 | `[OC]` beam | PROPOSED |
| Modes, d 25, with AH-drive parts and drive | f1 79.3–83.9; **f2 107.9–116.8 Hz**, 3–10 % under the 120 Hz pump | `sim/rotor-parts-drive-findings.md`; ledger §6 item 77 | `[OC]` | **OPEN** |
| Modes, d 30 (with mounts) | f1 93.7–102.4 Hz | `sim/doubler-caps-findings.md` §6 | `[OC]` | OPEN (with d) |

---

## Power and charge budget (both sides, laid out, ideal diodes unless stated)

| Term | W | Source | Tag |
|:--|--:|:--|:--|
| ES belt → varicaps, **ideal**, laid out (5-gap) | ≈ 0.599 (derived: clamps + rings) | `sim/multiplier-waveforms-findings.md` §2 | `[OC]` deck; `[RH]` strays |
| ES belt, **ideal**, as built (record V_op) | 0.634 (clamps 0.63) | `sim/integrated-multiplier-findings.md` §4 | `[OC]` deck |
| ES belt, **real sticks** | not integrated on its own; the extra is the leakage loss below | `sim/integrated-multiplier-findings.md` Gates | OPEN |
| Clamps Z1 + Z4 | 0.594 (2 × 0.297) | derived from the same | `[OC]` |
| Rings' leakage (the product) | 0.0045 (2 × 14.77 kV × 0.153 µA) | the same; 100 GΩ per ring `[RH]` | `[OC]` |
| Sticks' + strings' leakage, real parts | 0.004 / 0.060 / 0.142 (typical / max / hot; redesign as built, record V_op) | `sim/integrated-multiplier-findings.md` Gates | `[IR]` |
| Surge resistors | ≈ 0.006 (4 × ≈ 1.4 mW, record duty) | `sim/parts-first-cut-findings.md` §2.2 | `[IR]` |
| Magnetic pump belt (with bypass) | 18.1, + iron 1.25 | ledger §3.2 | `[OC]` deck (2-D utrons) |
| — of which D1*–D4* (first-cut set) | 2.42 | `sim/diodes-real-findings.md` §3.3 | `[IR]` |
| — of which La / Lb copper | 0.66 | ledger §3.2 | `[OC]` |
| La / Lb iron | 0.24–0.42 | `sim/parts-first-cut-findings.md` §1 | `[RH]` |
| AH coils | 2.44 (1.22 each, as wound) | ledger §3.5 | `[IR]` |
| Snubbers / bypass | ≤ 0.034 / 0.008 | `sim/parts-first-cut-findings.md` §2.5–§2.6 | `[OC]` |
| Magnetic belt, 3-D utrons + neck map (best estimate) | 12.7–15.0 | ledger §3.2 | `[IR]` |
| Windage / bearings / bridge-ring pair | ≈ 12 / 5 / +2.1 (6.1 high) + 0.06 | ledger §3.1, §3.9 | `[RH]` / `[IR]` |

All of it ends as heat (Governing 1). No term is recovered. The ES part is ≈ 3 % of the tube's dissipation.

**Charge per cycle, each chain** (`sim/multiplier-waveforms-findings.md` §2) `[OC]`: D1–D8 208.5 nC (25.0 µA); clamp
207.2 nC (24.87 µA); ring stage D9–D12 1.27–1.29 nC (0.15 µA). Balance closes to 0.011 % per chain, 0.009 % at nodes
1 / 4. Reference link 0.02 µA rms (as built); the counter-rotor within 0.1 µV of REF. Mean pull torque ≈ 4.8 mN·m
(0.599 W / 125.7 rad/s, derived); 120 Hz ripple 191 mN·m p-p.

## Evidence ledger

| Item | Current design | Evidence | Issue (if any) |
|:-----|:---------------|:---------|:---------------|
| varicap κ | 7.47 deck / 3.51 as built | `sim/core_field_results.json`; `sim/tube-strays-findings.md` §4 | the 2 pF rim floor is +65 pF; redesign's own stack unsolved |
| node strays | 66.2 / 24.5 record; 74.61 / 18.30 / 1–3.3 redesign | `sim/tube-strays-findings.md` §3; `sim/doubler-caps-findings.md` §4 | redesign values `[RH]`, no field solve |
| z | 1.0142 → 1.0164 → 1.01589 (ideal) | §3.9 studies | real sticks hot 0.9870 from 1 kV: no start |
| seed | model: ideal any; real 51 V / 947 V / 4.87 kV. Designer's experiment: four-diode doubler self-starts, PVC if slow | `sim/integrated-multiplier-findings.md` §5; `synthesis/core-engine-spec.md` Rec. 5 | no seed source (DECIDED 10-14); experiment has no data file; redesign's self-start OPEN (bench) |
| clamps | 66 drawn and ordered (P-006 = 132); 60 per the layout | `sim/multiplier-layout-findings.md` §6 | drawing set lags the trim |
| HV sticks | 12 × 20 kV, ≤ 6.11 kV each | `sim/multiplier-waveforms-findings.md` | leakage classes `[IR]` / hot `[RH]` |
| C3–C8, Csa / Csb envelopes | candidates taller than the deck's zone | ledger §6 item 72 | OPEN |
| Ca | 482.3 pF = 1.072 C_max on 5 gaps | `sim/doubler-caps-findings.md` §4 | sixth gap DECIDED 10-14 (495 pF); every 5-gap result to re-run (A.8) |
| ideal vs real records | ideal everywhere; real only for the as-built redesign | `sim/integrated-multiplier-findings.md` §5 | both kept (DECIDED 10-14); real for layout / mounts / 60 parts / 6 gaps not run |
| sleeve outer end | 17.5 mm + sheds = 65.5 mm vs 62 | `sim/multiplier-layout-findings.md` §4 | margin 1.06 |
| tab crossing corona | margin 1.052 | `sim/doubler-caps-findings.md` §3 | < 1 below 7 mm |
| flashover with ring stages | not run | `sim/integrated-multiplier-findings.md` Caveats | record's case: ring B 19.0 kV (item 41) |
| bays' mode f2 | 108–117 Hz | `sim/rotor-parts-drive-findings.md` | near 120 Hz (item 77) |
| shaft d | 25 drawn / 30 register | ledger §6 items 2, 30 | OPEN |
| varicap torque ripple at the gear | 191 mN·m p-p at the varicaps | `sim/integrated-multiplier-findings.md` §6 | share at the gear not run |
| record's chain-input resistors | in the record supply | `sim/parts-first-cut-findings.md` §2.2 | no counterpart decided for D9–D12 |

## Cross-spec dependencies

| Item | Value | Needed by | Note |
|:-----|:------|:----------|:-----|
| Node voltages | A.7 table (60-part clamps); Ca / Cb 11.6–13.2 kV DC; deck A ↔ B 29.9 kV; rings ±14.77 kV | electrical-integrity | redesign values rest on `[RH]` strays |
| Gaps, clearances, creepage | A.6 tables | electrical-integrity | sleeve outer end and tab crossing are the thinnest |
| Corona margins | rims ×1.17 handled at 11.94 kV; tab crossing 1.052 | electrical-integrity | Peek m 0.85 `[RH]` |
| Flashover scenarios | vane flashover with ring stages (not run); record ring B → 19.0 kV; no-clamp 25–47 A | electrical-integrity | surge resistors' adequacy for D9–D12 |
| Hot limits | sticks 5 µA at 100 °C; string +11.9 V/K | electrical-integrity, conservation-auditor | sets hot seed 4.87 kV |
| Tube envelope | 1014 mm on 5 gaps; ≈ 1032 mm with the sixth gap (derived, not laid out); machine −105.5 to ≈ 1032; cage r 182–186 | retainer-spec | re-lay OPEN |
| Masses | rotor 35.88 + 9.74 kg (two-body reading 50.4); counter-rotor 36.40 kg | retainer-spec | |
| Shaft and seats | C.3 table; d OPEN; 6 × 6205-2Z; preload OPEN | retainer-spec | |
| Bearing loads | bottom bridge-ring 331 N; wedges 545 N each (balanced) | retainer-spec | |
| Torque | mean ≈ 4.8 mN·m ES; varicap ripple 191 mN·m p-p at 120 Hz; gear 0.48 / 0.52 N·m | retainer-spec | ripple share at gear not run |
| Modes | f1 79–85 Hz; f2 108–117 Hz vs 120 Hz | retainer-spec | needs seat stiffness |
| Heat | power table above | retainer-spec (thermal), conservation-auditor | |
| Power and charge | power table; 208.5 nC/cycle/chain | conservation-auditor | ES belt = clamps + rings + leakage |
| **From core-engine-spec** | z set, node-total threshold ≈ 2.4 (unipolar), clamp requirement, equalization principle | this spec | bipolar threshold not mapped |
| **From retainer-spec** | bearing stiffness, preload, seat design | this spec | for the f2 / 120 Hz check |

## Items deferred to bench

| Item | Why it is open | What the bench measures | Source |
|:-----|:---------------|:-----------------------|:-------|
| Clamp string length | rings' level rests on `[RH]` strays; 1.6 % per part | VBR of the sorted string, warm; the rings' level | ledger §3.9; `sim/parts-first-cut-findings.md` §2.4 |
| Sticks' and strings' leakage, hot | decides the model's real-stick seed (51 V – 4.87 kV) | leakage vs T at working voltage; the smallest seed | `sim/diodes-real-findings.md` |
| Self-start of the §3.9 redesign | the designer's self-start evidence is on the four-diode doubler, with no data file; the model's real-stick record says it needs a seed | start with no injection, dry and humid; time to clamp; then PVC injection at A.3a | `synthesis/core-engine-spec.md` Rec. 5; `docs/bench-test-rings.md` phase 4 |
| Paired records | ideal vs real-stick records for every gain / ring / seed | the rings' level and growth with the real parts | decision 1 |
| Sixth Ca gap | 495 pF from 7 plates needs an overlap not yet set | Ca as built | decision 2 |
| As-built varicap and node strays | 3-D solve omits leads, parts; redesign stack unsolved | C_max / C_min; growth per cycle from a known seed, clamps out | `sim/tube-strays-findings.md` caveats |
| Corona onset | margins 1.05–1.17 on handled surfaces | onset of the assembled column at 1.45 × V_op | `sim/doubler-caps-findings.md` caveats |
| La / Lb gap trim | to 0.146 H | inductance at 1 A | `sim/parts-first-cut-findings.md` §1 |
| Snubber tuning | real winding capacitance | ringing at commutation | `sim/parts-first-cut-findings.md` §2.5 |
| Potting PD | void-free silicone | < 10 pC at 1.25 × | `sim/parts-first-cut-findings.md` §5 |
| Rings' hold-off and leakage | 1 / 5 kV/mm and 100 GΩ `[RH]` | DC hold-off to ±20 kV; leakage | `docs/bench-test-rings.md` |
| Bays' mode | f2 108–117 Hz | tap test on the rotor with its parts | `sim/rotor-parts-drive-findings.md` |

## Recommendations for the designer

All PROPOSED (synthesis). The designer decides.

1. **Accept κ 3.51 (as built) as the performance basis** and specify the varicap by its node-total ratio (2.59 with the
   mounts); field-solve the redesign's own in-phase stack with its decks and mounts to replace the `[RH]` strays.
2. **Carry the 60-part clamp strings** as the starting length; let the bench set the final count warm. Update
   DCCREG-P-006 / DCK-509 from 66 when decided.
3. **Map the bipolar redesign's self-excitation threshold** (z vs node-total ratio on its own deck); the 2.4 figure is the
   unipolar doubler's.
4. **Run the redesign's real-stick start-up on the layout** (not re-run since 1.0142 → 1.01589), and put the designer's
   self-start experiment on record (a data file: weather, seed, time to clamp), then repeat it on the §3.9 redesign at
   the bench. Accept or set otherwise the injection point A.3a (node 1, negative, a closable cage port).
5. **Run a vane flashover with the ring stages** and decide whether D9–D12 need surge resistors like the record's
   chain-input resistors.
6. **Settle the decks' real part envelopes** (item 72) before the deck plan is released.
7. **Re-lay and re-run on the sixth Ca gap** (DECIDED 10-14): choose the plate overlap that gives 495 pF and the
   column's end-node parity, then re-run the layout's deck (z, rings, 60-part trim, strays), the mounts' fields, the
   solids (length, masses) and the shafts' modes — each with both the ideal and the real-stick record.
8. **Resolve f2 vs 120 Hz** (item 77): the compact EI-66 choke, stiffer seats, or d 30 — jointly with retainer-spec.
