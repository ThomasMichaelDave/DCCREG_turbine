# Core Engine Specification

**Date:** 2026-10-13
**Baseline evidence:** design state `09243c7` (locked 2026-10-09), branch `claude/new-session-0az7f9`
**Synthesis branch:** `claude/synthesis-phase1`
**Agent:** core-engine-spec

## Purpose

This specification formalises the validated Bennet doubler engine: its topology,
growth factor z, efficiency eta, the equalization-is-the-pump principle, and the
varicap/clamp/stray requirements that the tube-synth agent must satisfy. It does
not specify individual components (that is the tube spec's job) or the spark-gap
commutator (Phase 2). It depends on nothing from other specs -- it is the target.

## Governing constraints

1. **The equalization-is-the-pump principle** (LOCKED). A resonant pump's own
   equalization cannot be resonated for recovery -- the equalization IS the pump.
   Only a downstream sink (the island) recovers freely. This was established by
   the falsification of eta 0.70 via three independent methods: the diode alpha_max
   ceiling, the S3 static-gap either/or, and the sequenced-statistical conservation
   arbiter. Source: `reference/commutator_real_core.py` docstring,
   `reference/doubler_resonant_core.py` docstring. [OC]

2. **Conservation closure.** The power budget must close at every interface. The
   belt power equals the sum of all losses (clamp dissipation, stick leakage,
   chain losses, motor-circuit losses) plus the delivered ring power. [OC]

3. **The frozen engine is read-only.** `reference/doubler_core.py`,
   `sim/pump_engine.py`, `sim/pump_sizing.py`, `sim/pump_synth.py` are frozen
   files and the anchors for all numerical values. Source: `CLAUDE.md` guardrail 1.

## Specification

### 1. Topology

| Parameter | Value | Source / basis | Tag | Status |
|:----------|:------|:---------------|:----|:-------|
| Type | 4-node symmetric Bennet doubler | `reference/doubler_core.py` | `[OC]` | DECIDED |
| Diode map | D1(2,0), D2(3,0), D3(1,3), D4(4,2) | `reference/doubler_core.py` DIODES | `[OC]` | DECIDED |
| Outer nodes | 1, 4 (high-voltage, antisymmetric) | `reference/doubler_core.py` seed | `[OC]` | DECIDED |
| Inner nodes | 2, 3 (low-voltage, clamped to rail) | `reference/doubler_core.py` seed | `[OC]` | DECIDED |
| Seed voltage | V = [-1, 0, 0, -1] (normalised) | `reference/doubler_core.py` | `[OC]` | DECIDED |
| Symmetry | Nodes 1/4 mirror, nodes 2/3 mirror; C1 = C2, Ca = Cb | layout | `[IR]` | DECIDED |
| Phase sequence | (C1min, C2max) then (C1max, C2min) per cycle | `reference/doubler_core.py` | `[OC]` | DECIDED |

**Rationale:** The 4-node Bennet doubler is the established pump topology. The
diode map implements the ratchet: D1/D2 are rail-return (clamp v2, v3 to zero),
D3/D4 are cross-coupled (transfer charge between outer nodes). The growth factor z
depends only on capacitance ratios [OC] -- this is the scale-free property of
electrostatic machines (`sim/pump_synth.py` line 36).

### 2. Growth factor z

| Parameter | Value | Source / basis | Tag | Status |
|:----------|:------|:---------------|:----|:-------|
| z (analytic, G3 caps) | 1.334 per cycle | `reference/doubler_core.py` anchors; G3 = {C1: 16-280, Ca: 309, Cpar: 20} | `[OC]` | DECIDED |
| z (ngspice validation) | 1.3095 per cycle | `sim/core_field_results.json` row "free none" | `[OC]` | DECIDED |
| z (analytic-ngspice gap) | ~4 % (1.334 vs 1.310) | comparison of frozen engine vs transient sim | `[OC]` | DECIDED |
| z (as-built, bare) | 1.058 per cycle | `sim/tube_strays_results.json` decks "as built" pump | `[OC]` | DECIDED |
| z (as-built, with chains) | 1.031 per cycle | `docs/ledger/DCCREG-design-ledger.md` §4 | `[OC]` | DECIDED |
| G3 reference caps (pF) | C1min=16, C1max=280, Ca=Cb=309, Cpar=20 | `reference/doubler_resonant_core.py` G3 | `[IR]` | DECIDED |

**Rationale:** z = 1.334 is the 4-node galvanic ceiling at the G3 capacitance
ratios. The frozen engine (`doubler_core.py`) computes it by iterative phase
solving with galvanic equalization -- the reference anchor. The ngspice transient
gives 1.3095 (the `core_field` study), a ~4 % gap attributed to the transient
simulation's finite time step and SPICE solver tolerances [OC]. The as-built z of
1.058 (bare) and 1.031 (with chains) reflects the devastating effect of the real
geometry's strays (§5 below). The machine works but pumps slowly.

### 3. Efficiency eta

| Parameter | Value | Source / basis | Tag | Status |
|:----------|:------|:---------------|:----|:-------|
| eta (direct, no recovery) | 0.386 | `reference/commutator_real_core.py` DIRECT_ETA | `[OC]` | DECIDED |
| eta (with island sink) | approx 0.50 | S2 island recovery, ngspice < 0.6 % | `[OC]` | DECIDED |
| eta (claimed brigade) | 0.70 -- FALSIFIED | `reference/commutator_real_core.py` docstring | `[OC]` | DECIDED |
| W_mech per cycle | 31.882 mJ (2 x 15.941 mJ/fire) | `reference/commutator_real_core.py` W_MECH_CYCLE_mJ | `[OC]` | DECIDED |
| Direct tax per cycle | 19.577 mJ (2 x 9.789 mJ/fire) | `reference/commutator_real_core.py` DIRECT_TAX_CYCLE_mJ | `[OC]` | DECIDED |

**Rationale:** The direct eta of 0.386 means 61.4 % of the mechanical work is
consumed by the equalization tax -- the diodes equalise charge to the mean, and
the energy difference is dissipated. The island (a downstream, true-sink resonant
recovery) recovers roughly half of this tax, lifting eta to approximately 0.50.
The brigade (doubler-core) tax is NOT recoverable because the equalization IS the
pump (the diode alpha_max ceiling is structural: the rail-return diodes D1/D2
re-conduct and clamp when the over-transfer drives v2, v3 positive). This is the
load-bearing physics, validated three ways. [OC]

### 4. The equalization-is-the-pump principle

This is the governing constraint of the synthesis. Stated precisely:

> **The equalization-is-the-pump principle** [OC]: In a Bennet doubler, the
> charge-equalizing diodes (D1-D4) implement the ratchet that produces net
> charge transfer. The energy dissipated in equalization (the two-cap tax
> 1/2 C_eff dV^2) is the thermodynamic cost of the pumping action. Resonating
> the equalization (adding inductors to recover the dV^2 energy) attempts to
> recover the pump's own operating cost. The rectification clamp (alpha_max)
> prevents this: the over-transfer drives inner nodes positive, forward-biasing
> the rail-return diodes, which re-conduct and cap the recovery. Alpha_max is
> structural (set by v2, v3 approaching 0), not a tuning artefact.
>
> Only a **downstream sink** -- a separate load circuit that receives the
> pumped charge and has its own equalization -- recovers freely, because the
> sink's equalization is not the pump's ratchet.
>
> **Consequence:** eta from the doubler core alone cannot exceed approximately
> 0.50 (direct 0.386 + island sink). Any model claiming eta > 0.50 from the
> doubler must be checked for a conservation violation.

Source: `reference/doubler_resonant_core.py` docstring (the physics),
`reference/commutator_real_core.py` (the falsification), the sequenced-statistical
conservation arbiter (the independent guard).

### 5. Varicap requirement

| Parameter | Value | Source / basis | Tag | Status |
|:----------|:------|:---------------|:----|:-------|
| kappa (deck) | 7.47 | `sim/core_field_results.json` design.kappa | `[OC]` | DECIDED |
| kappa (as-built, 3-D solve) | 3.51 | `sim/tube_strays_results.json` "as built, the record" | `[OC]` | DECIDED |
| C1 range, deck (pF) | 54.9 -- 409.9 | `sim/core_field_results.json` design | `[OC]` | DECIDED |
| C1 range, as-built (pF) | 128.1 -- 450.2 | `sim/tube_strays_results.json` "as built, the record" | `[OC]` | DECIDED |
| Ca = Cb, deck (pF) | 450.9 | `sim/core_field_results.json` design.Ca_pF | `[OC]` | DECIDED |
| Ca = Cb, as-built (pF) | 480.4 | `sim/tube_strays_results.json` "as built, the record" Ca_pF | `[OC]` | DECIDED |
| Ca rule | Ca = 1.1 x C_max | `sim/pump_sizing.py` CHOICE_DEFAULTS ratio_Ca | `[IR]` | DECIDED |

**Rationale:** The kappa discrepancy (7.47 deck vs 3.51 as-built) is the central
design issue. The 3-D field solve shows that the vane rims and sleeve add parasitic
capacitance to C_min (the unaligned position), raising it from 54.9 to 128.1 pF.
C_max rises only slightly (409.9 to 450.2 pF) because the aligned capacitance is
dominated by the plate area, which is the same. The result: kappa drops by more
than 2x, z drops from 1.31 to 1.06, and belt power drops from 2.14 W to 0.64 W.

The tube-spec must address this: either accept kappa 3.51 and the reduced
performance, or redesign the vane geometry to recover kappa. The deck value of
7.47 assumed minimal rim stray -- the 3-D solve refuted this. [OC]

### 6. Stray budget

| Parameter | Value | Source / basis | Tag | Status |
|:----------|:------|:---------------|:----|:-------|
| Node 1/4 stray (3-D solve) | 66.2 pF | `sim/tube_strays_results.json` decks.sets.strays Cp.1 | `[OC]` | DECIDED |
| Node 2/3 stray (3-D solve) | 24.5 pF | `sim/tube_strays_results.json` decks.sets.strays Cp.2 | `[OC]` | DECIDED |
| Placeholder (record) | 20 pF uniform | `sim/core_field_results.json` CPAR_pF | `[IR]` | DECIDED |
| Cross-coupling 1-2 / 3-4 | 1.15 pF | `sim/tube_strays_results.json` decks.sets.strays Cx "1 2" | `[OC]` | DECIDED |
| Cross-coupling 1-4 / 2-3 | < 0.05 pF | `sim/tube_strays_results.json` decks.sets.strays Cx | `[OC]` | DECIDED |
| Effect on z | 1.31 (20 pF) -> 1.06 (as built) | comparison of record vs as-built pump | `[OC]` | DECIDED |

**Rationale:** The strays are asymmetric -- nodes 1/4 (outer, high-voltage) see
66.2 pF from the vane rims, shaft, and nearby conductors, while nodes 2/3 (inner)
see only 24.5 pF. The record's 20 pF placeholder was optimistic by 3.3x on the
outer nodes. The strays load the pump -- they participate in every equalization
cycle, adding to the effective capacitance that must be equalised, increasing the
tax. The cross-couplings (1-2, 3-4 at 1.15 pF) are small but not negligible at
high voltage -- they reduce the effective swing. The tube-spec must allocate each
stray to its physical source and state the stray budget for the redesigned geometry. [OC]

### 7. Clamp requirement

| Parameter | Value | Source / basis | Tag | Status |
|:----------|:------|:---------------|:----|:-------|
| Clamp voltage BV | 13.1 kV (66 x 200 V TVS) | `docs/ledger/DCCREG-design-ledger.md` §3.4 | `[IR]` | DECIDED |
| Clamp strings | Z1 (node 1), Z4 (node 4) | topology | `[OC]` | DECIDED |
| Clamp power (each) | 1.07 W | `sim/core_field_results.json` clamped row Z1, Z4 | `[OC]` | DECIDED |
| Total clamp power | 2.14 W (= belt power at operating point) | `sim/core_field_results.json` | `[OC]` | DECIDED |
| PROPOSED trim | 66 -> 60 TVS (BV 11.9 kV) | `docs/ledger/DCCREG-design-ledger.md` §3.9 redesign | `[IR]` | PROPOSED |

**Rationale:** At steady state, ALL belt power goes into the clamps -- they are the
load on the electrostatic pump (in the absence of the rings' real load). The clamp
sets the operating voltage: V_op = BV / sqrt(2) approximately. The PROPOSED trim
from 66 to 60 TVS (§3.9 redesign) would lower V_op but increase the rings' voltage
fraction from the pump's perspective. The tube-spec must decide this or leave it
OPEN. [OC/IR]

### 8. Operating voltages and currents

| Parameter | Value | Source / basis | Tag | Status |
|:----------|:------|:---------------|:----|:-------|
| V_op (peak node 1/4) | 13.13 kV | `sim/core_field_results.json` design.V_op_kV | `[OC]` | DECIDED |
| V1 swing | -5.70 to -13.23 kV (pp 7.53 kV) | `sim/core_field_results.json` clamped "none" V.1 | `[OC]` | DECIDED |
| V2 swing | 0 to -6.12 kV (pp 6.12 kV) | `sim/core_field_results.json` clamped "none" V.2 | `[OC]` | DECIDED |
| Diode reverse peaks | D1: 6.12, D2: 6.12, D3: 13.18, D4: 13.18 kV | `sim/core_field_results.json` clamped VR_pk_kV | `[OC]` | DECIDED |
| Link current (rms AC) | 0.41 mA (deck), 0.34 mA (ngspice float) | `sim/core_field_results.json` link | `[OC]` | DECIDED |
| V_rings (ideal) | +/- 14.96 kV | `docs/ledger/DCCREG-design-ledger.md` §4 | `[OC]` | DECIDED |
| V_rings (as-built) | +/- 13.86 kV | `sim/tube_strays_results.json` as-built pump V_A/V_B | `[OC]` | DECIDED |
| Operating frequency | 120 Hz (1200 rpm relative, 600 rpm each body) | `sim/core_field_results.json` F_Hz | `[IR]` | DECIDED |

**Rationale:** These voltages define the insulation requirements for every component
in the tube. D3/D4 see the full operating voltage (13.18 kV reverse); D1/D2 see
half (6.12 kV). The rings sit at approximately V_op + V_supply_drop, ideally
+/- 14.96 kV. The link current of 0.41 mA rms (at 120 Hz) is the AC shuttle
current through the cone capacitors. [OC]

### 9. Charge per cycle and power budget

| Parameter | Value | Source / basis | Tag | Status |
|:----------|:------|:---------------|:----|:-------|
| Q per transfer | 1.16 uC | `reference/commutator_real_core.py` Q_TRANSFER_C | `[OC]` | DECIDED |
| Belt power (deck, clamped) | 2.14 W | `sim/core_field_results.json` design.P_clamped_W | `[OC]` | DECIDED |
| Belt power (as-built) | 0.64 W | `sim/tube_strays_results.json` as-built pump P_clamped_W | `[OC]` | DECIDED |
| LC half-cycle (brigade) | 0.82 us | `reference/commutator_real_core.py` T_HALF | `[OC]` | DECIDED |
| SG window | 278 us (5 deg at 3000 rpm) | `reference/commutator_real_core.py` SG_WINDOW | `[IR]` | DECIDED |

**Rationale:** The belt power is 2.14 W with the deck capacitances, dropping to
0.64 W as-built due to the reduced kappa. At steady state with only the clamp as
load, all belt power is dissipated in the clamp strings. With the rings connected,
the power splits between clamp dissipation and ring supply. The tube-spec must
account for every watt. [OC]

### 10. Seed and start-up

| Parameter | Value | Source / basis | Tag | Status |
|:----------|:------|:---------------|:----|:-------|
| Seed threshold (ND model) | 122 V (kick frac 0.164) | `sim/diodes_real_results.json` thresholds ND none | `[OC]` | DECIDED |
| Seed (real sticks, 25 C) | approx 1.0 kV | `sim/diodes-real-findings.md` | `[OC]` | DECIDED |
| Seed (real sticks, hot) | 3.65 kV | `sim/diodes-real-findings.md` §6 | `[RH]` | OPEN |
| Hot start failure | at 100 C, as-built does not start from -1 kV | `sim/diodes-real-findings.md` §6 | `[OC]` | OPEN |
| K4 kick energy | 3.48 mJ | `sim/diodes_real_results.json` magnetic.kick_record.kick_mJ | `[IR]` | DECIDED |

**Rationale:** The machine needs a seed voltage to start. With ideal diodes (ND
model) the threshold is low (122 V), but real HV sticks with their leakage require
approximately 1.0 kV at room temperature. At 100 C the leakage rises to 5 uA per
stick and the machine may not start at all from the standard -1 kV seed -- this is
an OPEN item that the bench must resolve. The K4 kick circuit provides the seed
pulse. [OC/RH]

### 11. Supply chain interface

| Parameter | Value | Source / basis | Tag | Status |
|:----------|:------|:---------------|:----|:-------|
| Chain diodes (per side) | 4 diodes at 7.5 kV reverse | `docs/ledger/DCCREG-design-ledger.md` §4 | `[IR]` | DECIDED |
| Chain caps (per side) | 4 x 100 pF / 30 kV | `docs/ledger/DCCREG-design-ledger.md` §4 | `[IR]` | DECIDED |
| Chain topology | CW multiplier, stacked into doubler (redesign) | `docs/ledger/DCCREG-design-ledger.md` §3.9 | `[IR]` | PROPOSED |
| Null-field coefficient | k = 0.242 kV/cm per kV | `sim/hub_rings_build_results.json` record_in.k_kV_cm_per_kV | `[OC]` | DECIDED |

**Rationale:** The chain diodes and caps form the CW multiplier that supplies the
rings from the doubler's operating voltage. The chain sees the same AC swing as
the doubler nodes. The null-field coefficient k relates the ring voltage to the
field at the hub's equatorial plane -- this governs the rings' insulation. [OC/IR]

## Evidence ledger

| Item | Current design | Evidence | Issue (if any) |
|:-----|:---------------|:---------|:---------------|
| z | 1.334 (G3), 1.31 (deck), 1.06 (as-built) | `doubler_core.py`, `core_field_results.json`, `tube_strays_results.json` | As-built z devastated by strays |
| kappa | 7.47 (deck) vs 3.51 (as-built) | `core_field_results.json`, `tube_strays_results.json` | Vane rims add 65/37 pF to C_min |
| eta | 0.386 direct, approx 0.50 with island | `commutator_real_core.py`, S2 study | eta 0.70 falsified |
| Strays | 20 pF placeholder vs 66.2/24.5 pF solved | `tube_strays_results.json` decks | 3.3x underestimate on outer nodes |
| Belt power | 2.14 W (deck) vs 0.64 W (as-built) | `core_field_results.json`, `tube_strays_results.json` | 3.3x reduction from strays |
| Seed voltage | 122 V (ND) vs 1.0 kV (real) vs 3.65 kV (hot) | `diodes_real_results.json` | Hot start failure OPEN |
| Clamp trim | 66 TVS (13.1 kV) vs 60 TVS (11.9 kV) PROPOSED | `DCCREG-design-ledger.md` §3.9 | Redesign proposes 60 |

## Cross-spec dependencies

| Item | Value | Needed by | Note |
|:-----|:------|:----------|:-----|
| Operating voltage V_op | 13.13 kV | tube-synth, electrical-integrity | Sets insulation requirements |
| Node voltage swings | V1: 7.53 kV pp, V2: 6.12 kV pp | tube-synth | Sets component ratings |
| Diode reverse peaks | D1/D2: 6.12 kV, D3/D4: 13.18 kV | tube-synth | Sets stick ratings |
| Belt power | 2.14 W (deck) | conservation-auditor | Must equal losses + ring power |
| eta ceiling | approx 0.50 | conservation-auditor | Any higher is a violation |
| Operating frequency | 120 Hz | retainer-spec | 2x PRF for shaft excitation |
| Stray budget | 66.2/24.5 pF | tube-synth | Must be allocated to physical sources |
| Kappa discrepancy | 7.47 vs 3.51 | tube-synth | Must be resolved or documented |

## Items deferred to bench

| Item | Why it is open | What the bench measures | Source |
|:-----|:---------------|:-----------------------|:-------|
| Hot start threshold | Stick leakage at temperature not reliably modelled | Minimum seed voltage vs temperature | `diodes-real-findings.md` §6 |
| As-built z confirmation | 3-D solve vs reality | Voltage growth rate from seed | direct measurement |
| Island sink eta | ngspice gives approx 0.50, bench confirms | Delivered ring power / shaft power | `bench-test-rings.md` |

## Recommendations for the designer

1. **PROPOSED:** The kappa discrepancy (3.51 vs 7.47) should drive the vane
   geometry redesign. Reducing C_min (the unaligned parasitic) is the highest-
   leverage improvement to the pump's performance. The tube-spec will address
   geometry options.

2. **PROPOSED:** The clamp trim (66 to 60 TVS) should be evaluated together with
   the redesigned varicap kappa -- a lower clamp BV is acceptable if the higher
   kappa delivers adequate belt power at the reduced voltage.

3. **PROPOSED:** The hot-start problem (100 C, real sticks) may require a higher
   seed voltage from K4, or a staged start-up sequence. This is deferred to the
   bench but should be planned for in the K4 circuit design.
