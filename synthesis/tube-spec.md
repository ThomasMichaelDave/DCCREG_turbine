# Tube Specification

**Date:** 2026-10-13
**Baseline evidence:** design state `09243c7` (locked 2026-10-09), branch `claude/new-session-0az7f9`
**Synthesis branch:** `claude/synthesis-phase1`
**Agent:** tube-synth

## Purpose

This specification covers the complete rotating assembly (the tube) without its
spark-gap commutator: the electrostatic pump (varicaps, supply chain, HV sticks,
clamps), the motor parts on the rotor (D1*-D4*, La/Lb, bypass, snubbers, K4), and
the air insulation stack. It depends on `synthesis/core-engine-spec.md` for the
target parameters. It does not cover the spark-gap commutator (Phase 2), bearings,
motor, drive, or cage (retainer-spec), or the rings as stator (interface only).

## Governing constraints

1. **The core engine spec** (`synthesis/core-engine-spec.md`): z = 1.334 (G3),
   eta = 0.386 / approx 0.50, V_op = 13.13 kV, F = 120 Hz. [OC]
2. **The equalization-is-the-pump principle** (LOCKED): no energy recovery from
   the doubler core's own equalization. [OC]
3. **Frozen files** (`CLAUDE.md`): the engine code is read-only.
4. **Every component from the latest design files.** No invented parts.

## Specification

### A. Electrostatic pump

#### A.1  Varicap vanes (C1, C2)

| Parameter | Value | Source / basis | Tag | Status |
|:----------|:------|:---------------|:----|:-------|
| Target kappa | 7.47 (deck geometry), 3.51 (as-built) -- OPEN | `core_field_results.json`, `tube_strays_results.json` | `[OC]` | OPEN |
| C_max (deck) | 409.9 pF (37.3 pF per gap x 11 gaps) | `core_field_results.json` design | `[OC]` | DECIDED |
| C_min (deck) | 54.9 pF (4.8 pF per gap x 11 gaps) | `core_field_results.json` design | `[OC]` | DECIDED |
| C_max (as-built) | 450.2 pF | `tube_strays_results.json` "as built, the record" | `[OC]` | DECIDED |
| C_min (as-built) | 128.1 pF | `tube_strays_results.json` "as built, the record" | `[OC]` | DECIDED |
| Vane count | 6 stator + 6 rotor per side (11 gaps) | `air_stack_sizing_results.json` | `[IR]` | DECIDED |
| Vane material | Aluminium, 3 mm, full rounds R1.5 | `DCCREG-design-ledger.md` §4 | `[IR]` | DECIDED |
| Sector geometry | 6 on 60 deg pitch, 22 deg stator / 22 deg rotor | `DCCREG-design-ledger.md` §4 | `[IR]` | DECIDED |
| Radial extent | r 50-150 mm | `DCCREG-design-ledger.md` §4 | `[IR]` | DECIDED |
| Gap | 6 mm air | `air-stack-sizing-findings.md` §6.5 | `[IR]` | DECIDED |
| Stack length per side | 102 mm (C1) + 6 mm + 48 mm (Ca) = 156 mm | `DCCREG-design-ledger.md` §4 | `[IR]` | DECIDED |
| Rotor vane mass (both sides) | 2.9 kg | `DCCREG-design-ledger.md` §4 | `[IR]` | DECIDED |
| Stator vane mass (both sides) | 3.4 kg | `DCCREG-design-ledger.md` §4 | `[IR]` | DECIDED |

**Rationale -- the kappa discrepancy:** The deck geometry assumes minimal rim
fringe and gives kappa = 7.47 (C_min 54.9 pF). The 3-D field solve of the as-built
geometry gives kappa = 3.51 (C_min 128.1 pF) because the vane rims and the G10
sleeve add 65 pF (outer nodes) and 37 pF (inner nodes) of parasitic capacitance at
the unaligned position [OC] (`tube-strays-findings.md` §4). This halves kappa and
drops z from 1.31 to 1.06.

The synthesis carries BOTH values: kappa 7.47 is the target the pump was designed
for; kappa 3.51 is what the as-built geometry delivers. The tube-spec uses kappa
3.51 for all performance estimates and power budgets (conservative). Recovering
kappa toward 7.47 requires redesigning the vane rims and sleeve -- this is OPEN for
the designer. The `air-stack-sizing-findings.md` §3 shows that reshaping the sectors
(narrower stator, wider clearance at minimum C) can recover kappa to 5.8-8.4 at the
6 mm gap [OC]. PROPOSED.

**Sensitivity:** z vs kappa (from `air-stack-sizing-findings.md` §2):

| kappa | z | clamped power | note |
|:------|:--|:--------------|:-----|
| 15.7 | 1.515 | 18.5 W | vacuum, 3 mm gap |
| 7.47 | 1.31 | 2.14 W | deck, 6 mm air |
| 3.51 | 1.058 | 0.64 W | as-built, 6 mm air |
| 2.2 | 1.02 | never clamps | 15 mm air |

Self-excitation requires z > 1 including all losses (sticks, chains). The minimum
kappa for self-excitation with the current stray budget is approximately 3.0 [RH].
At kappa 3.51 the machine self-excites but barely; kappa 5 or above gives
comfortable margin.

#### A.2  Node stray budget

| Parameter | Value | Source / basis | Tag | Status |
|:----------|:------|:---------------|:----|:-------|
| Nodes 1/4 stray | 66.2 pF | `tube_strays_results.json` decks.sets.strays Cp.1 | `[OC]` | DECIDED |
| Nodes 2/3 stray | 24.5 pF | `tube_strays_results.json` decks.sets.strays Cp.2 | `[OC]` | DECIDED |
| Cross-coupling 1-2 / 3-4 | 1.15 pF | `tube_strays_results.json` Cx | `[OC]` | DECIDED |
| Cross-coupling 1-4 | 0.048 pF | `tube_strays_results.json` Cx | `[OC]` | DECIDED |
| Record placeholder | 20 pF uniform | `core_field_results.json` CPAR_pF | `[IR]` | DECIDED |
| z cost (strays -> as-built) | 1.31 -> 1.058 | comparison | `[OC]` | DECIDED |
| Clamp at this stray | BV 13.1 kV holds (belt power 0.64 W < clamp capacity) | tube_strays pump results | `[OC]` | DECIDED |

**Rationale:** The strays are ASYMMETRIC -- nodes 1/4 see 66.2 pF from vane rims,
shaft coupling, and adjacent conductors; nodes 2/3 see 24.5 pF. The 20 pF
placeholder underestimates the outer nodes by 3.3x. The strays devastate the pump:
they load every equalization cycle, increasing the effective capacitance that must
be equalised.

**Allocation of the 66.2 pF on node 1/4** (from `tube_strays_results.json` capacitance matrix):
- Vane rims to stator ring assembly (SA): 75.0 pF (dominant)
- Vane rims to utrons (UT): 0.001 pF (negligible)
- Vane caps (N1c) cross-cap to neighbouring nodes: 8.1 pF
- Vane to shaft: included in the SA coupling

The redesign's stray budget depends on the vane geometry chosen. If the rims are
trimmed (narrower sectors, wider clearance), the 66.2 pF could drop to 20-30 pF
[RH], recovering z toward 1.2. OPEN for the designer.

#### A.3  HV sticks (D1-D4)

| Parameter | Value | Source / basis | Tag | Status |
|:----------|:------|:---------------|:----|:-------|
| D1, D2 | 1 x 20 kV avalanche stick, 5 mA class, each | `parts-first-cut-findings.md` §4 | `[IR]` | PROPOSED |
| D3, D4 | 2 x 20 kV sticks in series (or 1 x 30 kV), each | `parts-first-cut-findings.md` §4 | `[IR]` | PROPOSED |
| Surge resistors | 22 kOhm +/-5%, >=15 kV, >=1 W, >=0.1 J pulse, each stick | `parts-first-cut-findings.md` §4 | `[IR]` | PROPOSED |
| Leakage (25 C typical) | 2 uA per stick | `diodes-real-findings.md` sticks | `[IR]` | DECIDED |
| Leakage (25 C maximum) | 5 uA per stick | `diodes-real-findings.md` sticks | `[IR]` | DECIDED |
| Leakage (100 C) | 5 uA per stick | `diodes-real-findings.md` sticks | `[IR]` | DECIDED |
| VR margin D1/D2 | x3.3 (20 kV / 6.12 kV) | `parts-first-cut-findings.md` §4 | `[OC]` | DECIDED |
| VR margin D3/D4 | x3.0 (40 kV / 13.18 kV) or x2.3 (30 kV) | `parts-first-cut-findings.md` §4 | `[OC]` | DECIDED |
| Self-excitation from few-volt seed | NO with real sticks | `diodes-real-findings.md` §4.1 | `[OC]` | DECIDED |

**Rationale:** Real HV sticks leak. At 25 C, 2 uA typical; at 100 C, 5 uA. This
leakage opposes the pump's small net current (81 uA average), stealing charge from
the doubler's ratchet. The machine does NOT self-excite from a few-volt seed with
real sticks -- it needs a seed of 122 V (typical leakage), 1.0 kV (max), or 3.65 kV
(hot) [OC] (`diodes-real-findings.md` §6.3). At 100 C the as-built machine does not
start from -1 kV at all. [OC]

The chain-input resistors (22 kOhm, same part as the surge resistors) were added
by `parts-first-cut-findings.md` to protect the chain's first diodes in a vane
flashover: in that event the chains see 5.8 kV forward, limited only by the arc
without the resistor [IR].

#### A.4  Clamp strings (Z1, Z4)

| Parameter | Value | Source / basis | Tag | Status |
|:----------|:------|:---------------|:----|:-------|
| Clamp count | 66 x 200 V TVS per string | `DCCREG-design-ledger.md` §3.4 | `[IR]` | DECIDED |
| Part class | 1.5KE200A (190-210 V at 1 mA) or 5 W Zener 1N5388B class | `parts-first-cut-findings.md` §4 | `[IR]` | PROPOSED |
| BV | 13.1 kV (66 x 198 V nominal) | `core_field_results.json` design | `[OC]` | DECIDED |
| Power per string | 1.07 W | `core_field_results.json` clamped Z1/Z4 | `[OC]` | DECIDED |
| Total clamp power | 2.14 W (= belt power at operating point) | `core_field_results.json` | `[OC]` | DECIDED |
| Power per device | 16 mW (against >=1.5 W rating, x90 margin) | `parts-first-cut-findings.md` §4 | `[OC]` | DECIDED |
| Conduction duty | 14% of each cycle | `parts-first-cut-findings.md` §4 | `[OC]` | DECIDED |
| PROPOSED trim | 60 x 200 V TVS (BV approx 11.9 kV) | `DCCREG-design-ledger.md` §3.9 | `[IR]` | PROPOSED |

**Rationale -- the 66 to 60 trim:** The redesign (§3.9) proposes reducing the clamp
from 66 to 60 TVS, lowering BV from 13.1 to approximately 11.9 kV. This is
PROPOSED. The effect: V_op drops, the rings sit at lower voltage (approximately
+/-13.6 kV with 60 TVS and redesigned multiplier, vs +/-14.96 kV with 66 TVS), but
the pump operates at lower stress and the stick leakage fraction improves (less
voltage, proportionally less leakage). Whether 60 TVS is correct depends on the
kappa achieved -- at kappa 3.51, belt power is only 0.64 W and a lower clamp
reduces it further. At kappa 7.47, 60 TVS is comfortable.

Decision deferred to the designer. The synthesis carries 66 TVS as the baseline. [IR]

#### A.5  Chain diodes and capacitors

| Parameter | Value | Source / basis | Tag | Status |
|:----------|:------|:---------------|:----|:-------|
| Chain diodes | 8 total (4 per side) | `DCCREG-design-ledger.md` §4 | `[IR]` | DECIDED |
| Chain diode type | 20 kV avalanche stick, selected for IR <=25 nA at 7.5 kV, 25 C | `parts-first-cut-findings.md` §4 | `[IR]` | PROPOSED |
| Chain diode VR | 7.50 kV each | `parts-first-cut-findings.md` §4 | `[OC]` | DECIDED |
| Chain diode margin | x2.7 (20 kV / 7.5 kV) | `parts-first-cut-findings.md` §4 | `[OC]` | DECIDED |
| Chain capacitors | 8 total (4 per side) | `DCCREG-design-ledger.md` §4 | `[IR]` | DECIDED |
| Chain cap value | 100 pF +/-10% | `DCCREG-design-ledger.md` §4 | `[IR]` | DECIDED |
| Chain cap rating | 30 kV DC, HV ceramic class 1 (or PP/PTFE film) | `parts-first-cut-findings.md` §4 | `[IR]` | PROPOSED |
| Chain cap IR | >=1e11 Ohm guaranteed | `parts-first-cut-findings.md` §4 | `[IR]` | PROPOSED |
| Chain cap margin | x2.3 (Co1 at 13.22 kV), x4.0 (general), x5.3 (Coa1) | `parts-first-cut-findings.md` §4 | `[OC]` | DECIDED |
| Chain-input resistors | 2 total (22 kOhm, same as surge resistors) | `parts-first-cut-findings.md` §4 | `[IR]` | PROPOSED |
| Topology | 2+2 CW stages from shaft (redesign: stacked into doubler) | `DCCREG-design-ledger.md` §3.9 | `[IR]` | PROPOSED |

**Rationale:** The chain CW multiplier steps the doubler's operating voltage up to
the rings' supply voltage. Each stage adds approximately 7.5 kV. The chain diodes
must be selected for very low leakage (<=25 nA) because any leakage in the chain
bleeds the rings' charge -- the rings hold their voltage only against their own
leakage (100 GOhm assumed). The chain caps must be partial-discharge-free at 1.25x
rated voltage [IR]. The chain-input resistors limit the surge from a vane
flashover. [IR]

#### A.6  Air insulation stack

| Parameter | Value | Source / basis | Tag | Status |
|:----------|:------|:---------------|:----|:-------|
| Vane gap | 6 mm air at 1 atm | `air-stack-sizing-findings.md` | `[IR]` | DECIDED |
| Breakdown voltage (6 mm, 1 atm, 20 C) | 19.7 kV (Paschen, uniform field) | `air-stack-sizing-findings.md` §1 | `[OC]` | DECIDED |
| Operating peak | 13.13 kV | `core_field_results.json` | `[OC]` | DECIDED |
| Safety factor | x1.5 (19.7 / 13.1 kV) | `air-stack-sizing-findings.md` §1 | `[RH]` | DECIDED |
| Face field | 21.9 kV/cm (operating) | `DCCREG-design-ledger.md` §4 | `[OC]` | DECIDED |
| Rim field | 44.4 kV/cm (0.80 of corona onset) | `DCCREG-design-ledger.md` §4 | `[OC]` | DECIDED |
| Ca/Cb gap | 6 mm air (same as varicap) | `DCCREG-design-ledger.md` §4 | `[IR]` | DECIDED |

**Rationale:** Air at atmospheric pressure breaks down at approximately 3.28 kV/mm
for a 6 mm gap (Paschen). The x1.5 safety factor from the vacuum design is
carried into air operation. The rim field at 44.4 kV/cm is 0.80 of corona onset
(about 56 kV/cm for the R1.5 edge profile) -- this is adequate but not generous.
Full audit deferred to electrical-integrity agent. [OC/RH]

#### A.7  Integrated multiplier layout

| Parameter | Value | Source / basis | Tag | Status |
|:----------|:------|:---------------|:----|:-------|
| Layout | CW multiplier stacked into the doubler (redesign §3.9) | `DCCREG-design-ledger.md` §3.9 | `[IR]` | PROPOSED |
| Arrangement | C1/C2 in phase, bipolar, ring stages | `DCCREG-design-ledger.md` §3.9 | `[IR]` | PROPOSED |
| Node positions | From `multiplier-layout-findings.md` | `multiplier-layout-findings.md` | `[IR]` | PROPOSED |
| 3D layout | From `multiplier-layout-3d-findings.md` | `multiplier-layout-3d-findings.md` | `[IR]` | PROPOSED |

**Rationale:** The redesign (§3.9) proposes stacking the multiplier into the doubler
vane stack, with C1 and C2 pumping in phase and a bipolar arrangement. This
simplifies the tube layout but requires careful clearance management. The 2D and 3D
layout studies confirm feasibility. PROPOSED -- the designer decides the layout. [IR]

---

### B. Motor parts (provisioned from current design)

#### B.1  D1*-D4* (motor rectifier diodes)

| Parameter | Value | Source / basis | Tag | Status |
|:----------|:------|:---------------|:----|:-------|
| D1*, D2* | Schottky, 200 V, >=3 A (5 A preferred) | `parts-first-cut-findings.md` §2, §4 | `[IR]` | PROPOSED |
| D3*, D4* | Schottky, 150 V (100 V minimum), >=3 A (5 A preferred) | `parts-first-cut-findings.md` §2, §4 | `[IR]` | PROPOSED |
| VR peaks | D1* 113 V, D2* 104 V, D3* 58 V, D4* 60 V (incl. start-up) | `rotor_parts_duty_results.json` | `[OC]` | DECIDED |
| IF peaks | 1.90 A (D1*/D2*), 2.27 A (D3*/D4*) | `parts-first-cut-findings.md` §4 | `[OC]` | DECIDED |
| VR margin D1*/D2* | x1.8 (Schottky 200 V), x3.6 (Si 400 V) | `parts-first-cut-findings.md` §4 | `[OC]` | DECIDED |
| VR margin D3*/D4* | x2.5 (Schottky 150 V), x1.7 (100 V minimum) | `parts-first-cut-findings.md` §4 | `[OC]` | DECIDED |
| Diode losses (Schottky, with bypass) | 2.42 W total (4 diodes) | `diodes-real-findings.md` §3.3 | `[OC]` | DECIDED |

**Rationale:** Schottky rectifiers are PROPOSED over silicon PN because the silicon
1N540x-class drops 0.85 V at 1 A (vs the deck's 0.54 V), which kills 6% of the AH
field (z 1.139 to 1.074, AH 449 to 423 A-turns) and raises the seed threshold from
16% to 25%. Schottky parts preserve the modelled performance. D3*/D4* see lower
reverse voltage (58/60 V) and can use 100 V Schottky for lower V_F. [IR]

#### B.2  La / Lb (chokes)

| Parameter | Value | Source / basis | Tag | Status |
|:----------|:------|:---------------|:----|:-------|
| Core | EI-84 x 35 mm stack, M400-50A class | `parts-first-cut-findings.md` §1 | `[IR]` | PROPOSED |
| Winding | 150 turns Dia 1.40 mm grade-2 enamelled Cu, 7 layers x 24 | `parts-first-cut-findings.md` §1 | `[IR]` | PROPOSED |
| Gap | 0.126 mm (spacer 0.063 mm); trimmed on test to 0.146 H | `parts-first-cut-findings.md` §1 | `[IR]` | PROPOSED |
| L | 0.146 H (target) | `rotor_parts_duty_results.json` | `[OC]` | DECIDED |
| R (20 C) | 0.276 Ohm | `parts-first-cut-findings.md` §1 | `[OC]` | DECIDED |
| Duty | 0.87-1.15 A at 120 Hz, 1.05 A rms | `rotor_parts_duty_results.json` | `[OC]` | DECIDED |
| V_pk across | 110 V (La), 101 V (Lb) | `rotor_parts_duty_results.json` | `[OC]` | DECIDED |
| B_pk | 1.20 T (knee at 1.39 A, x1.21 margin) | `parts-first-cut-findings.md` §1 | `[OC]` | DECIDED |
| Copper loss | 0.33 W each | `parts-first-cut-findings.md` §1 | `[OC]` | DECIDED |
| Iron loss | 0.21 W (M400-50A), 0.12 W (M235-35A) | `parts-first-cut-findings.md` §1 | `[RH]` | PROPOSED |
| Mass | 1.66 kg each (1.54 kg iron + copper, 0.12 kg bobbin) | `parts-first-cut-findings.md` §1 | `[IR]` | PROPOSED |
| Outline | 84 x 70 x 59 mm | `parts-first-cut-findings.md` §1 | `[IR]` | PROPOSED |

**Rationale:** The EI-84 x 35 mm is the lightest standard size meeting the model's
0.292 Ohm resistance requirement (it gives 0.276 Ohm, 6% to spare). tau = 0.53 s
(above the model's 0.5 s). The gap is small and must be trimmed on test. Mount the
pair 180 deg apart for balance. At r 80 mm each sees 32 g and 490 N centrifugal at
600 rpm. [IR]

#### B.3  AH bypass capacitors

| Parameter | Value | Source / basis | Tag | Status |
|:----------|:------|:---------------|:----|:-------|
| Value | 22 mF each, ESR <=20 mOhm | `parts-first-cut-findings.md` §4 | `[IR]` | PROPOSED |
| Type | 6.3-10 V aluminium electrolytic, 105 C, >=2 A rms at 120 Hz | `parts-first-cut-findings.md` §4 | `[IR]` | PROPOSED |
| Polarity | + to nodes d / b | `parts-first-cut-findings.md` §4 | `[OC]` | DECIDED |
| Reverse voltage seen | <=1.3 mV (never reverse-biased in any run) | `parts-first-cut-findings.md` §3 | `[OC]` | DECIDED |
| LC resonance | 34 Hz | `DCCREG-design-ledger.md` §4 | `[OC]` | DECIDED |
| Power (pair) | 8 mW | `DCCREG-design-ledger.md` §4 | `[OC]` | DECIDED |

#### B.4  Node snubbers

| Parameter | Value | Source / basis | Tag | Status |
|:----------|:------|:---------------|:----|:-------|
| Count | 8 (one per motor node per side) | `parts-first-cut-findings.md` §4 | `[IR]` | PROPOSED |
| C | 22 nF +/-10% polypropylene film, 250 V DC | `parts-first-cut-findings.md` §4 | `[IR]` | PROPOSED |
| R | 240 Ohm, 0.5 W, pulse-rated, non-inductive | `parts-first-cut-findings.md` §4 | `[IR]` | PROPOSED |
| Power | <=4.2 mW average, <=0.30 W peak per snubber | `parts-first-cut-findings.md` §4 | `[OC]` | DECIDED |

#### B.5  K4 start kick

| Parameter | Value | Source / basis | Tag | Status |
|:----------|:------|:---------------|:----|:-------|
| Storage | 470 uF bipolar electrolytic, 25 V | `parts-first-cut-findings.md` §3 | `[IR]` | PROPOSED |
| Source | 9 V lithium primary cell + 10 kOhm charge resistor | `parts-first-cut-findings.md` §3 | `[IR]` | PROPOSED |
| Switch | SCR >=400 V, >=1 A; reed switch + external magnet | `parts-first-cut-findings.md` §3 | `[IR]` | PROPOSED |
| Dump | across La, + to node a; 19 mJ, 0.60 A peak, 17 ms | `parts-first-cut-findings.md` §3 | `[OC]` | DECIDED |
| Fire speed | 600 rpm each way, never below 500 | `parts-first-cut-findings.md` §3 | `[IR]` | PROPOSED |
| Energy | 3.48 mJ needed (seed at 20% Psi_s); 8 mJ minimum stored for fast dump | `diodes_real_results.json` | `[OC]` | DECIDED |

---

### C. Physical arrangement

#### C.1  Tube envelope

| Parameter | Value | Source / basis | Tag | Status |
|:----------|:------|:---------------|:----|:-------|
| Tube length | 940 mm (record in solids) | `DCCREG-design-ledger.md` §4 | `[IR]` | DECIDED |
| Tube max radius | 150 mm (vane outer) + cage r 162-166 mm | `DCCREG-design-ledger.md` §4 | `[IR]` | DECIDED |
| Rotor mass (without La/Lb + parts) | 30.4 kg | `shaft_bearings_record_results.json` | `[OC]` | DECIDED |
| Rotor mass (with all parts) | 38.2 kg (layout); 50.4 kg (with AH-drive parts + ballast) | `rotor-parts-drive-findings.md` | `[OC]` | DECIDED |
| Counter-rotor mass | 33.1 kg | `shaft_bearings_record_results.json` | `[OC]` | DECIDED |
| Machine length (with drive) | z -105.5 to 1014 mm (approx 1120 mm) | `rotor-parts-drive-findings.md` | `[IR]` | PROPOSED |

#### C.2  Parts placement

The AH-drive parts sit in the reluctance bays' three free wedges (60, 180, 300 deg)
between the utrons (at 0, 120, 240 deg), per `rotor-parts-drive-findings.md`:

| Wedge | Side A | Side B |
|:------|:-------|:-------|
| S1 (60 deg) | La | Lb |
| S2 (180 deg) | D1*, D3*, snubbers (a,d,x1,f2), bypass A, ballast | D2*, D4*, snubbers (b,c,x2,f3), bypass B, ballast |
| S3 (300 deg) | K4 kick, ballast | ballast |

**Balance:** Each side balanced by brass ballast to equal m.r per wedge. Three equal
moments 120 deg apart sum to zero. Ballast: 1.09 kg (S2), 1.02 kg (S3 A), 1.16 kg
(S3 B). Residual 0.013 g.mm against G2.5's 1732 g.mm limit. [OC]

**Mass price:** +9.74 kg on the rotor (+29% on the layout's 33.8 kg), of which
3.27 kg per side is ballast. [OC]

#### C.3  Shaft interface

| Parameter | Value | Source / basis | Tag | Status |
|:----------|:------|:---------------|:----|:-------|
| Shaft diameter | d 25 (tube model) or d 30 (hub register) -- OPEN | `DCCREG-design-ledger.md` §4 | `[IR]` | OPEN |
| Shaft material | Non-magnetic, mu_r <=1.05 | `DCCREG-design-ledger.md` §4 | `[IR]` | DECIDED |
| Bearings | 6 x 6205-class (25/52/15 mm) on G10 spiders | `DCCREG-design-ledger.md` §4 | `[IR]` | DECIDED |
| Modes (d 25, layout) | f1 27-29 Hz | `tube-shaft-findings.md` §0 | `[OC]` | DECIDED |
| Modes (d 25, with parts) | f1 83.9 Hz, f2 116.8 Hz (with drive) | `rotor-parts-drive-findings.md` | `[OC]` | DECIDED |
| Gap change under 1 g lateral (d 25) | 123 um | `DCCREG-design-ledger.md` §4 | `[OC]` | DECIDED |
| Bridge-ring bearings (PROPOSED) | SKF 6205-2Z at each bridge ring outer end | `bridge-ring-bearings-findings.md` | `[IR]` | PROPOSED |
| Drive interface | Bevel reverser at side A, POM-C pinions | `drive-gear-belt.md` | `[IR]` | PROPOSED |

---

## Power budget summary (as-built, kappa 3.51)

| Source/sink | Power (W) | Source |
|:------------|:----------|:------|
| ES belt power (input) | 0.64 | `tube_strays_results.json` as-built |
| Clamp Z1 | 0.32 | proportional to belt power |
| Clamp Z4 | 0.32 | proportional to belt power |
| Stick leakage (4 sticks, 2 uA, typical) | negligible (< 0.1 W) | `diodes-real-findings.md` |
| Chain losses | negligible | chain current << 1 uA |
| **ES pump total** | **0.64** | |
| Magnetic belt power (input) | 18.1 (with bypass) | `DCCREG-design-ledger.md` §4 |
| Motor diodes D1*-D4* | 2.42 | `diodes-real-findings.md` §3.3 |
| La/Lb copper (pair) | 0.66 | `rotor-parts-duty-findings.md` |
| La/Lb iron (pair) | 0.42 | `parts-first-cut-findings.md` §1 |
| Snubbers (8) | 0.034 | `parts-first-cut-findings.md` §4 |
| Bypass (pair) | 0.008 | `DCCREG-design-ledger.md` §4 |
| AH coils (pair) | 2.44 | `DCCREG-design-ledger.md` §4 |
| Utron iron (6) | 1.25 | `DCCREG-design-ledger.md` §4 |
| AH delivered field power | ~11 | remainder |
| **Magnetic pump total** | **18.1** | |
| Windage | 12 | `DCCREG-design-ledger.md` §4 |
| Bearing drag | 5 | `DCCREG-design-ledger.md` §4 |
| **Shaft power total** | **approx 36** | |

## Evidence ledger

| Item | Current design | Evidence | Issue |
|:-----|:---------------|:---------|:------|
| kappa | 7.47 deck / 3.51 as-built | `core_field_results.json`, `tube_strays_results.json` | As-built devastates z |
| Strays 1/4 | 66.2 pF (3.3x placeholder) | `tube_strays_results.json` | Vane rims dominate |
| Clamp | 66 x 200V TVS, PROPOSED trim to 60 | `DCCREG-design-ledger.md` §3.9 | Depends on achieved kappa |
| La/Lb | first cut EI-84 x 35 | `parts-first-cut-findings.md` §1 | PROPOSED, not yet built |
| D1*-D4* | Schottky PROPOSED | `diodes-real-findings.md` §3.3 | Si PN kills 6% of gain |
| K4 | 470 uF + SCR + reed | `parts-first-cut-findings.md` §3 | PROPOSED |
| Hot start | fails at 100 C from -1 kV | `diodes-real-findings.md` §6 | OPEN |

## Cross-spec dependencies

| Item | Value | Needed by | Note |
|:-----|:------|:----------|:-----|
| Tube envelope | 940 mm length, r max 166 mm (cage), mass 50.4 kg rotor | retainer-spec | For bearings, cage |
| Shaft interface | d 25 (OPEN: d 30), 6 x 6205 bearings, G10 spiders | retainer-spec | For bearing seats |
| Total heat | approx 36 W shaft - rings power | retainer-spec | For thermal management |
| Every voltage, every gap | V_op 13.13 kV, gaps 6 mm, rim field 44.4 kV/cm | electrical-integrity | For breakdown audit |
| Power budget | 0.64 W ES + 18.1 W mag + 17 W mech | conservation-auditor | Must close |
| Bay mode f2 | 116.8 Hz (stiff) / 107.9 Hz (G10 spiders) | retainer-spec | Near 120 Hz -- OPEN |

## Items deferred to bench

| Item | Why open | What bench measures | Source |
|:-----|:---------|:--------------------|:-------|
| As-built kappa | 3-D solve vs reality | C_max, C_min at aligned/unaligned | direct measurement |
| Clamp BV trim | depends on achieved kappa | V_op under clamp | varies with kappa |
| Hot start seed | stick leakage at temperature | minimum seed V vs T | `diodes-real-findings.md` §6 |
| Bay mode f2 | 108-117 Hz vs 120 Hz | tap test on rotor with parts | `rotor-parts-drive-findings.md` |

## Recommendations for the designer

1. **PROPOSED:** Redesign the vane geometry to reduce C_min and recover kappa
   toward 5+. The `air-stack-sizing-findings.md` §3 shows that narrower sectors
   (24/18 deg at 6 mm gap) can reach kappa 8.4.

2. **PROPOSED:** Accept the EI-84 x 35 mm choke design for La/Lb. It meets the
   model's resistance requirement and is a standard buildable form.

3. **PROPOSED:** Use Schottky rectifiers for D1*-D4*. Silicon PN kills 6% of the
   AH field and raises the seed threshold from 16% to 25%.

4. **PROPOSED:** Defer the 66/60 TVS clamp trim decision until the redesigned kappa
   is known. At kappa 3.51 the belt power is too low for a further voltage
   reduction.

5. **PROPOSED:** Plan for a 3+ kV seed capability in K4 to handle hot starts.
   The current 9 V / 470 uF circuit provides 19 mJ but the seed voltage may need
   to be higher than -1 kV at 100 C.
