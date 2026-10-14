# Core Engine Specification

**Date:** 2026-10-13
**Baseline evidence:** design state `09243c7` (locked 2026-10-09), branch `claude/new-session-0az7f9`
**Synthesis branch:** `claude/synthesis-phase1`
**Agent:** core-engine-spec

**Status legend.** The Status column carries the ledger's status of the *design choice* behind each value
(`docs/ledger/DCCREG-design-ledger.md` §5.1–§5.2). A computed consequence of a choice carries that choice's status.
This spec decides nothing; the designer does. **ANCHOR** marks a frozen-engine number of the superseded disc machine,
kept as a regression anchor, not as a property of the tube.

## Purpose

This spec states the electrostatic engine of the DCCREG tube: the 4-node symmetric Bennet doubler in de Queiroz's
diode form, on the air vane stack of record. It gives the topology, the gain z, the efficiency and the principle that
governs it, the charge and power at the operating point, what the engine needs from its varicaps, clamps and node
strays, and a conservation ledger. Two engines carry the numbers [IR]:
- **the frozen disc-machine engine** (`reference/doubler_core.py`, `sim/pump_engine.py`, `sim/pump_sizing.py`,
  `sim/pump_synth.py`). It is the source of z 1.334 and η 0.386, and of the equalization principle;
- **the tube's diode core** (`sim/core_field.py` and the studies built on it). This is the design of record.

Excluded: the spark-gap commutator, the islands and the shuttle. The tube has none of them; they are superseded
(ledger §2.4). They appear here only as anchors and as an interface for Phase 2. This spec depends on no other
synthesis spec. tube-synth, electrical-integrity and conservation-auditor build on it.

## Governing constraints

1. **The equalization-is-the-pump principle (LOCKED).** A resonant pump's own equalization cannot be resonated for
   energy recovery, because the equalization *is* the pump. Resonating it either clamps it (the ratchet holds and the
   tax is lost) or breaks the ratchet (the pump dies). Sequencing and statistics only sample those two arms. **Only a
   downstream sink transfer recovers freely.** Sources: `CONVENTIONS.md` (working rule); `docs/efficiency-resolution.md`
   §2, §4. `[OC]`
   - **What it means for the tube:**
     - no spec may claim energy recovery from the rectifying transfers (D1–D4, Ca / Cb, the §3.9 ladder);
     - the tube's only downstream sinks are the clamps Z1 / Z4 and the rings' leakage. Both dissipate: the belt's
       power ends as heat (ledger §3.4; `CONVENTIONS.md`). `[OC]`
2. **η ≈ 0.70 is forbidden.** It is falsified three independent ways (§2.3). Any spec that applies η 0.70, or η ≈ 0.50
   (the disc machine's island-sink figure), to the diode tube fails its gate (`synthesis/synthesis-plan.md`, framing
   condition). `[OC]`
3. **Conservation closes at the engine's boundary.** At the steady state, belt power = clamps + leakage + diode/other
   losses + the change in stored energy. The record's deck closes it to 4e-5 W in 2.14 W (§2.8). `[OC]`
4. **The frozen files stay byte-identical** (`CLAUDE.md` guardrail 1). The numbers here are read from them and from
   committed results; nothing was re-run.
5. **The designer's DECIDED items bind this spec** (ledger §5.1, all as of 2026-10-09 unless dated):
   - the stack of record (6 mm gaps, V_op = breakdown / 1.5, 22° / 22°, r 150, Ca = 1.1 C_max) and the clamps Z1 / Z4;
   - the HV side on the rotor;
   - the symmetric supply;
   - the multiplier stacked into the doubler (10-10), and its circuit "for now" (10-11).

## Specification

### 2.1 Topology

| Parameter | Value | Source / basis | Tag | Status |
|:----------|:------|:---------------|:----|:-------|
| Type | 4-node symmetric Bennet doubler, de Queiroz diode form ("Fig. 1 with every diode reversed": negative polarity) | ledger §3.4; `sim/core_field.py` | `[OC]` | DECIDED |
| Varicaps | C1 node 1 → REF (side A), C2 node 4 → REF (side B) | ledger §3.4 | `[OC]` | DECIDED |
| Transfer caps | Ca node 1 – node 2, Cb node 3 – node 4 | ledger §3.4 | `[OC]` | DECIDED |
| Diodes (canonical) | D1 2→0, D2 3→0 (rail return); D3 1→3, D4 4→2 (cross-couple) | `CONVENTIONS.md` §2; `reference/doubler_core.py` `DIODES` | `[OC]` | DECIDED |
| Node roles | 1 / 4: HV varicap nodes, clamped; 2 / 3: inner nodes, swinging between REF and about −6.1 kV | `sim/core_field_results.json` row `none` | `[OC]` | DECIDED |
| REF (node 0) | the rotor shaft. The stator vanes (counter-rotor) join it through one inner bearing; the redesign lets the counter-rotor float | ledger §3.4, §5.1; `sim/integrated-multiplier-findings.md` §6 | `[IR]` | DECIDED ("for now") |
| HV parts' body | Ca / Cb, D1–D4, Z1 / Z4 on the rotor; the counter-rotor carries no HV | `sim/core-field-findings.md` §1, §7 | `[IR]` | DECIDED |
| Varicap phasing, record | C1 / C2 half a pitch apart (antiphase), 6 swings per relative revolution | ledger §3.4, §6 item 58 | `[IR]` | DECIDED (record) |
| Varicap phasing, redesign | C1 / C2 **in phase**, bipolar (chain 2 reversed); in antiphase the redesign does not pump (z 1.000 as built) | ledger §3.9 | `[OC]` | DECIDED for now (10-11) |
| Rings' supply, record | 2 + 2 mirror Cockcroft–Walton chains from the shaft; ring A on node 1 (negative), ring B on node 4 (positive) | `sim/hub-rings-build-findings.md` §4; `docs/rings-design.md` | `[IR]` | DECIDED (superseded in circuit by §3.9) |
| Rings' supply, redesign | each cross diode becomes a three-diode chain through a two-stage ladder (C3–C6 180 pF, D5–D8), plus one ring stage per side (C7 / C8, D9–D12); each ring on 100 pF to the shaft | ledger §3.9; `presets/hub-locked.json` pumps | `[OC]` | DECIDED for now (10-11) |
| Commutation | **none**: ideal or real diodes, not spark gaps. The disc machine's 8-gap rotary spark-gap commutator at the DXF stations is superseded | ledger §2.4; `sim/diode-stack-findings.md` | `[IR]` | DECIDED |
| Island / shuttle | **none** in the tube. With diodes, islands become voltage multipliers (island node 8 at 8× node 1) and the output collapses | `sim/diode-stack-findings.md` Reading 3 | `[OC]` | DECIDED (superseded) |

**Rationale.** Between diode events the circuit is linear and scale-free, so z depends only on capacitance ratios
`[OC]` (`sim/pump_synth.py` docstring; ledger §3.4). One half cycle runs in three steps:
1. The shrinking varicap holds its charge (its diode blocks), so its voltage rises as Q / C.
2. Through Ca or Cb that rise lifts the next node until a diode conducts.
3. The charge pours onto the other varicap while it is large.

Smooth C(θ) with diodes makes the transfer lossless (§2.3).

**Interface (Phase 2, excluded):** a spark-gap commutator, if it is ever reinstated. The frozen engine's DXF station
phasing *binds*: armed at its stations, the galvanic doubler gives z 1.5225, not 1.3340
(`sim/island-asdrawn-findings.md` H3). `solve_doubler4` is the anchor only for a machine whose switches settle
together. `[OC]`

---

### 2.2 Voltage gain z

| Parameter | Value | Source / basis | Tag | Status |
|:----------|:------|:---------------|:----|:-------|
| z, frozen engine (G3: C 16–280 pF, Ca 309, Cpar 20) | **1.334** | `reference/commutator_real_core.py` `DIRECT_Z`; `reference/doubler_resonant_core.py` `G3`; island-asdrawn H3 1.3340016 | `[OC]` | ANCHOR |
| validation of 1.334 | Queiroz eigen-matrix 0.002 %; ngspice transient 4.3 % | `docs/efficiency-resolution.md` §1 | `[OC]` | ANCHOR |
| z, tube record (the eigen-cycle of the stack of record) | **1.3090** | `sim/core_field_results.json` `design.z` | `[OC]` | DECIDED |
| z, tube record (ngspice transient, bare, 20 pF strays) | **1.3095** (Δ 0.04 % on the eigen-cycle) | `sim/core_field_results.json` row `free none`; `sim/core-field-findings.md` §1 | `[OC]` | DECIDED |
| z with the record's 2 + 2 chains, start-up | 1.1907 | `sim/hub_rings_build_results.json` `record_supply_free`; `sim/tube-strays-findings.md` §5 | `[OC]` | DECIDED |
| z as built (every capacitance solved), bare / with the chains | **1.0579 / 1.0310** | `sim/tube-strays-findings.md` §5 | `[OC]` solve; `[IR]` model | OPEN (accept or remedy, ledger §5.2) |
| z, redesign as built (record V_op), ideal diodes | 1.0142 | ledger §3.9; `sim/integrated-multiplier-findings.md` | `[OC]` deck; `[RH]` new-node strays | DECIDED for now |
| z, redesign as laid out / with the capacitors' mounts | 1.0164 / 1.01589 | `sim/multiplier-layout-findings.md`; `sim/doubler-caps-findings.md` §5 | `[OC]` deck; `[RH]` strays | PROPOSED |
| z with real HV sticks from 1 kV, record supply as built: typical / max / hot leakage | 1.0244 / 1.0038 / **0.9672** | `sim/integrated-multiplier-findings.md` table; `sim/diodes-real-findings.md` §6 | `[OC]` deck; `[RH]` hot leakage | OPEN |
| the same, redesign as built | 1.0129 / 1.0039 / **0.9870** | the same | `[OC]` / `[RH]` | OPEN |

**z against κ** (bare, the record's 20 pF on every node, Ca = 1.1 C_max; `sim/core_swing_grid.json` rows; the grid is
`sim/core-field-findings.md` §3) `[OC]` deck, `[IR]` cosine C(θ):

| C_max \ κ | 3 | 5 | 8 | 13 | 22 |
|--:|--:|--:|--:|--:|--:|
| 250 pF | 1.046 | 1.171 | 1.265 | 1.339 | 1.393 |
| 450 pF | 1.083 | 1.224 | 1.332 | 1.417 | 1.482 |
| 800 pF | 1.105 | 1.255 | 1.373 | — | — |

- At r 150 the record's κ 7.47 gives z 1.309. Radius buys κ and z: κ 9.0 / 10.5 / 17.7 give z 1.375 / 1.426 / 1.552
  at r 175 / 200 / 300 (`sim/vane-matrix-findings.md` §1) `[OC]` deck; `[IR]` the 2-D cell.
- **As built** (`sim/tube-strays-findings.md` §4–§5): the varicap's own κ falls from 7.47 to 3.51, and the node-1
  total (varicap plus strays) from 5.74 to 2.57. So z bare falls from 1.3095 to 1.0579. The varicap as solved with
  20 pF strays elsewhere gives z 1.1307. `[OC]`
- **The governing ratio is the node total** (C_max + strays) / (C_min + strays), not the varicap's own κ [IR, read from
  the grid rows]:
  - node total 2.37 → z 0.995 (C_max 130, κ 3);
  - 2.61 → 1.046;
  - 2.76 → 1.083;
  - as built, 2.57 → 1.058.
  - **The bare self-excitation threshold therefore sits near a node-total ratio of 2.4** (ideal diodes, this Ca rule).

**z against node strays:**

| configuration | price per pF | Source | Tag |
|:--|:--|:--|:--|
| the record's caps, nodes 1 and 4 together | 0.0027 (≈ 0.003) | `sim/tube-strays-findings.md` §5; `sim/core-field-findings.md` §4 | `[RH]` linear price |
| the record's caps, nodes 2 and 3 together | 0.0018 | `sim/tube-strays-findings.md` §5 | `[RH]` |
| either way, for electrodes (the shaft-side + ring-to-ring table) | ≈ 0.003; z ≥ 1.30 allows about 2 pF each | `sim/core-field-findings.md` §4 | `[RH]` |
| as built, nodes 1 / 4 (secant 66.7 → 104.9 pF), bare / with the chains | 0.00084 / 0.00060 | derived here from `sim/tube-strays-findings.md` §3 variants (1.058 → 1.026; 1.031 → 1.008) | `[IR]` two-point secant |
| redesign layout (+3.81 pF on 1 / 4, +4.64 pF on 2 / 3) | 0.00048 for the set | `sim/doubler-caps-findings.md` §5 | `[OC]` deck; `[RH]` strays |

**Rationale.** z 1.334 belongs to the disc machine's stepped two-state schedule at G3. It does not describe the tube.
The tube's validated number is 1.3095 bare, a second, independent validation: ngspice against the stack's eigen-cycle,
Δ 0.04 %. As built the solved rims and strays take it to 1.058 / 1.031, and with real sticks hot it no longer
self-excites. That loss of margin, not the gain of record, is the engine's binding fact.

---

### 2.3 Efficiency η

| Parameter | Value | Source / basis | Tag | Status |
|:----------|:------|:---------------|:----|:-------|
| η direct, frozen engine (G3, simultaneous switching, the post-phase-A cut) | **0.386** (0.385956) | `reference/commutator_real_core.py` `DIRECT_ETA`; `sim/island-asdrawn-findings.md` H3 | `[OC]` | ANCHOR |
| validation of 0.386 | Queiroz eigen-matrix 0.002 %; ngspice transient 4.3 % (S1) | `docs/efficiency-resolution.md` §1 | `[OC]` | ANCHOR |
| η with the island sink (disc machine) | **≈ 0.45–0.50**; S2 island transfer validated in ngspice to < 0.6 % | `docs/efficiency-resolution.md` §1, §3 | `[OC]` | ANCHOR |
| tax split (disc machine) | island ≈ 31 % (recoverable, a sink); doubler core / Ca–Cb brigade ≈ 69 % (not recoverable) | `docs/efficiency-resolution.md` §3 | `[OC]` | ANCHOR |
| per-cycle energy (disc machine) | W_mech 31.882 mJ; direct tax 19.577 mJ | `reference/commutator_real_core.py` | `[OC]` | ANCHOR |
| η 0.70 | **FALSIFIED** (three roads, below) | `docs/efficiency-resolution.md` §4 | `[OC]` | LOCKED |
| cut dependence | η of a growing, unloaded pump depends on the cycle cut. Simultaneous doubler: 0.386 at every cut. Station-armed: 0.559 at 0°, 0.329 at 29° | `sim/island-asdrawn-findings.md` §2 | `[OC]` | — |
| stepped-model qualification | 0.39–0.52 is a property of the two-state stepped schedule; with smooth C(θ) the same diode core is lossless | `sim/diode-stack-findings.md` Reading 2 | `[IR]` | — |
| η of the transfer, tube diode core (smooth caps, ideal diodes) | **1.00** (de Queiroz core, tube ladder of that study: 3.01 W belt, 3.01 W surplus) | `sim/diode-stack-findings.md` table | `[OC]` deck; `[IR]` ideal diodes | DECIDED (the diode core) |
| η of record for the tube | **none**. The products are static fields; the belt's power ends as heat | `CONVENTIONS.md`; ledger §6 item 12 | `[IR]` | — |

**The three roads that falsify η 0.70** (`docs/efficiency-resolution.md` §4) `[OC]`:
1. **The diode α_max ceiling** (`reference/doubler_resonant_core.py`). The rail-return diodes re-conduct and clamp the
   over-transfer at α_max ≈ 0.28. z re-tunes 1.334 → 1.573, but η only reaches 0.404.
2. **S3, a static gap in an independent engine** (ngspice). The clamping gap and the holding-off gap are one element:
   - S3-A ratchets with no over-transfer (z 1.39);
   - S3-B over-swings and breaks the pump (z 1.01).
3. **The sequenced-statistical conservation arbiter.** Gaps fire at their DXF stations, with V_strike scatter and
   formative lag Monte-Carlo'd. Every realisation lands on z ≈ 1.0 or z ≈ 1.32. The tax energy relocates and never
   reaches the output.

**Rationale.** The disc machine's figures stay as anchors and as the proof of the principle. For the tube the
principle takes this form:
- the transfers are lossless with smooth C(θ) and diodes, so no tax exists to recover;
- the surplus the engine makes above its losses must go to a sink, and the clamps are the sink of record;
- the clamps are dissipative by design. A non-dissipative downstream sink for the tube is not in the record.

---

### 2.4 Charge per cycle and power at the operating point

Operating point of record: the stack of record, clamped at V_op, 1200 rpm relative. Values are per side unless stated.

| Parameter | Value | Source / basis | Tag | Status |
|:----------|:------|:---------------|:----|:-------|
| speed | 600 rpm each body, opposite; 1200 rpm relative | ledger §4 | `[IR]` | DECIDED |
| pump frequency | **120 Hz** = 6 sectors × 1200 rpm / 60. Not 3600 rpm or 2 × 60 Hz | ledger §4; `sim/core_field_results.json` `F_Hz`, `rpm_rel` | `[OC]` | DECIDED |
| charge through each clamp per cycle (record) | **676 nC** (81.1 µA avg ÷ 120 Hz) | derived from `sim/core_field_results.json` row `none` `Z1.I_avg_mA` | `[OC]` | DECIDED |
| clamp energy per cycle, each | 8.9 mJ | `sim/parts-first-cut-findings.md` §2.4 | `[OC]` | DECIDED |
| clamp current waveform | 0.957 mA peak, 81 µA avg, 0.24 mA rms; conducts 14 % of each cycle, near minimum C | `sim/core_field_results.json` row `none`; `sim/parts-first-cut-findings.md` §2.4 | `[OC]` | DECIDED |
| belt power into the ES engine, both sides (record, no rings) | **2.1423 W** (waveform check 2.1423 W) | `sim/core_field_results.json` row `none` `P_belt_W`, `P_belt_wave_W` | `[OC]` | DECIDED |
| belt power, record with the symmetric rings' supply | 2.1438 W | `sim/hub_rings_build_results.json` `record_supply` | `[OC]` | DECIDED |
| belt power as built: record supply / redesign | **0.646 W** / clamps 0.63 W | `sim/tube-strays-findings.md` §5; `sim/integrated-multiplier-findings.md` | `[OC]` deck; `[IR]` model | OPEN |
| mean pull torque between the bodies | 17 mN·m at 2.14 W (P / ω_rel, ω_rel 125.7 rad/s); 5.1 / 5.0 mN·m as built, record / redesign | derived; `sim/integrated-multiplier-findings.md` §6 | `[OC]` | — |
| varicaps' 120 Hz torque ripple | 63 mN·m p-p (record, antiphase); **191 mN·m p-p** (redesign, in phase) | `sim/integrated-multiplier-findings.md` | `[OC]` | DECIDED for now |
| reference-link current (record) | 0.41 mA rms, 0.92 mA peak, pure AC (C1 / C2 displacement); 0.165 mA rms as built | `sim/core_field_results.json` row `none` `link`; `sim/integrated-multiplier-findings.md` | `[OC]` | DECIDED |
| reference-link current (redesign) | 0.02 µA rms (Q1 = −Q2); the counter-rotor can float on 100 pF | `sim/integrated-multiplier-findings.md` §6 | `[OC]` | DECIDED for now |
| redesign as laid out (60-part clamps, V_op 11.94 kV): charge per chain per cycle | 208.5 nC (25.0 µA); clamp 207.2 nC (24.9 µA); ring stage 1.27 nC (0.15 µA, its leakage) | `sim/multiplier-waveforms-findings.md` §2 | `[OC]` deck; `[RH]` strays | PROPOSED |
| redesign diode currents, peak in 1° bins | D1 / D2 0.612 mA (22.7–26.3°); D3 / D4 0.229 mA (39.8–59.7°); clamps 0.516 mA (25.2–30.2°) | `sim/multiplier-waveforms-findings.md` §2 | `[OC]` | PROPOSED |
| start-up, 95 % of the rings | record 0.24 s; as built 0.63 s (ideal) / 0.575 s (typical sticks, −1 kV); redesign 1.45 s; layout 1.22 s (cycle 146) | `sim/tube-strays-findings.md` §5; ledger §3.4, §3.9; `sim/multiplier-waveforms-findings.md` | `[OC]` | — |

**Rationale.** All of the belt's power to the engine leaves through the clamps; the rings take milliwatts (§2.8). The
mean torque is small. The redesign's in-phase stacks triple the 120 Hz ripple, and how much of it reaches the gear was
not run (ledger §3.9).

---

### 2.5 The varicap requirement

| Parameter | Value | Source / basis | Tag | Status |
|:----------|:------|:---------------|:----|:-------|
| stack | 6 stator (REF) + 6 rotor (node 1 / 4) Al vanes, 3 mm, full round R1.5; 11 gaps of 6 mm in air; 6 × 22° / 22° sectors on a 60° pitch, r 50–150 | ledger §3.4, §4 | `[IR]` | DECIDED |
| C1 = C2, deck (the 2-D cell + 2 pF) | **54.9–409.9 pF, κ 7.47** | `sim/core_field_results.json` `design` | `[IR]` 2-D cell | DECIDED (the record) |
| C1 = C2, as built (3-D solve) | **128.4–450.6 pF, κ 3.51**; the rims add 65 pF to C_min and 37 pF to C_max | `sim/tube-strays-findings.md` §4 | `[OC]` solve; `[IR]` solids | OPEN |
| node 1 to REF in all, as built | 199.2–512.2 pF, ratio 2.57 (record 74.9–429.9, 5.74) | `sim/tube-strays-findings.md` §4 | `[OC]` | OPEN |
| Ca = Cb | rule 1.1 C_max = 450.9 pF; laid out 480.5 pF (5 gaps, count rounded up); with the mounts 482.3 pF (1.072 C_max as solved). 1.1 × 450.6 = 495 pF needs a sixth gap | ledger §3.4; `sim/tube-strays-findings.md` §4; `sim/doubler-caps-findings.md` §4 | `[OC]` / `[IR]` rule | DECIDED (rule); OPEN (gap count) |
| κ for z 1.31 (bare, 20 pF strays) | 7.47 at C_max 410 pF | `sim/core_field_results.json` | `[OC]` | DECIDED |
| κ that can be lost before bare z < 1 | node total from 5.74 down to about 2.4 (§2.2); as built 2.57 leaves z 1.058 | `sim/core_swing_grid.json`; `sim/tube-strays-findings.md` §4 | `[IR]` grid reading | OPEN |
| node-stray budget, record (z ≥ 1.30) | about 2 pF per electrode node | `sim/core-field-findings.md` §4 | `[RH]` | — |
| node strays solved | 66.2 pF on 1 / 4 (40.2 sleeve-to-shaft, 14.6–23.1 Ca_01 through the last rotor vane, 7.0 other); 24.5 pF on 2 / 3 (11.5 to the utrons); across the hub ≤ 0.05 pF; 1–2 coupling 1.15 pF | `sim/tube-strays-findings.md` §3 | `[OC]` solve; `[IR]` model | OPEN |
| stray headroom to z = 1 on nodes 1 / 4, ideal diodes, as built | ≈ 70 pF bare, ≈ 50 pF with the chains (secant extrapolation) | derived from `sim/tube-strays-findings.md` §3 | `[RH]` extrapolation | OPEN |
| stray headroom with real HV sticks, hot | **none**: z 0.967 (record supply) / 0.987 (redesign) already | `sim/integrated-multiplier-findings.md` | `[OC]` deck; `[RH]` hot leakage | OPEN |
| solved remedies (designer's options, not the record) | 6 / 12 mm rim clearance: z with the chains 1.046 / 1.041; PTFE sleeve 1.045; both 1.059, 0.91 W | `sim/tube-strays-findings.md` §6 | `[RH]` | PROPOSED by the study; not adopted |

**Rationale.** The engine needs the node-total ratio, not the varicap's own κ. The rims and the G10 sleeve take most
of it: the sleeve alone gives 40 pF on node 1. A node-1 spacer ring mounting takes node 1 to 104.9 pF and z with the
chains to 1.008, so the varicap's mounts must insulate, as the doubler-caps proposal does
(`sim/doubler-caps-findings.md` §1). In a larger stack the fixed strays weigh less: at r 200, C_max 755 pF and κ 10.5
(`sim/vane-matrix-findings.md` §1). The 6 + 6 cap and r 150 are the designer's.

---

### 2.6 The clamp requirement

| Parameter | Value | Source / basis | Tag | Status |
|:----------|:------|:---------------|:----|:-------|
| role | stops z > 1 growth: avalanche strings on nodes 1 / 4 to REF, conducting once a cycle near the peak; all surplus to heat | ledger §3.4 | `[OC]` | DECIDED |
| target V_op (record) | **13.13 kV** = the 6 mm gap's 19.7 kV breakdown / 1.5 | `sim/core_field_results.json` `design.V_op_kV`; ledger §4 | `[RH]` margin | DECIDED |
| string, record | 66 × 200 V (1.5KE200A class, VBR 190–210 V at 1 mA) = 13.2 kV nominal | `sim/parts-first-cut-findings.md` §2.4 | `[IR]` | PROPOSED (first cut) |
| string, redesign layout | **60 parts, V_op 11.94 kV**. At 66 the layout's small strays raise the rings to ±16.25 kV; at 60 they hold ±14.77 kV | ledger §3.9; `sim/multiplier-waveforms-findings.md` | `[RH]` strays | PROPOSED |
| dissipation, record | **1.07 W each** (2.14 W both); 0.95 mA peak; 16 mW avg / 0.19 W peak per part | `sim/core_field_results.json` row `none`; `sim/parts-first-cut-findings.md` §2.4 | `[OC]` | DECIDED |
| dissipation, as built | about 0.32 W each (0.64 W record supply, 0.63 W redesign, both sides) | `sim/integrated-multiplier-findings.md` | `[OC]` | OPEN |
| dissipation, redesign layout | about 0.30 W each (24.87 µA × 11.94 kV) | derived from `sim/multiplier-waveforms-findings.md` §2 | `[OC]` | PROPOSED |
| BV tolerance | ±5 % parts → 12.54–13.86 kV at worst; a random lot ±47 V (σ 0.36 %). Sort by VBR at 1 mA; trim with whole parts (1.5 % a part); a lower-voltage part at the REF end | `sim/parts-first-cut-findings.md` §2.4 | `[IR]` | PROPOSED |
| temperature | +0.1 %/K, +13 V/K for the string; +25 K lifts V_op 0.33 kV (gap margin 1.5 → 1.46; rim corona ×1.07 → ×1.04). Trim warm | `sim/parts-first-cut-findings.md` §2.4 | `[IR]` datasheet class | PROPOSED |
| junction capacitance | C_j / 66 adds about 1–2 pF to node 1 / 4 (0.003–0.006 of z) | `sim/parts-first-cut-findings.md` §2.4 | `[RH]` | — |
| clamps' leakage, hot | 5 µA a string; it sets the 3.65 kV hot seed | ledger §3.4 | `[RH]` | OPEN (bench) |
| without clamps | relaxation oscillator: arcs at the stack, 25–47 A through D1–D4, 38 A peak / 1.8 A rms / 2.1 mC per strike through the bearing link. **The clamps are mandatory** | `sim/electrostatic-no-clamp-findings.md`; ledger §3.4 | `[OC]` | DECIDED |

**Rationale.** The clamps are the engine's governor and its sink. The rings' level follows V_op through each stage's
swing, so the bench trims the string length to the rings' target before the hub sees it (ledger §3.9).

---

### 2.7 The island requirement

| Parameter | Value | Source / basis | Tag | Status |
|:----------|:------|:---------------|:----|:-------|
| island in the tube | **none** (superseded with the spark gaps, the shuttles and the resonant tank) | ledger §2.4 | `[IR]` | DECIDED |
| why it cannot be carried over | with diodes the Cx / Lx islands become voltage multipliers (island node 8 at 8× node 1), and under the breakdown cap the output collapses | `sim/diode-stack-findings.md` Reading 3 | `[OC]` | — |
| disc machine's island (anchor) | a downstream Cx / Lx sink; its LC transfer recovers ≈ 31 % of the combined tax, η 0.386 → ≈ 0.45–0.50; S2 to < 0.6 % (t½, i_pk, V_bank) | `docs/efficiency-resolution.md` §3; `sim/island-asdrawn-findings.md` H1 | `[OC]` | ANCHOR |
| why a sink recovers | the sink's equalization is not the pump's ratchet, so resonating it breaks nothing (the principle, §Governing 1) | `docs/efficiency-resolution.md` §2 | `[OC]` | LOCKED |
| as-drawn island harness | HARNESS-FAIL at H3 (station phasing binds). No as-drawn island z / η verdict exists | `sim/island-asdrawn-findings.md` | `[OC]` | — |
| the tube's sink in its place | the clamps Z1 / Z4 (dissipative) and the rings' leakage (100 GΩ per ring) | §2.6, §2.8 | `[OC]` | DECIDED |
| commutation interface | Phase 2. A reinstated spark-gap stage would have to re-anchor on the station-armed machine (z 1.5225 at the canary) and fix a cycle cut for η | `sim/island-asdrawn-findings.md` §Consequence | `[IR]` | OPEN (Phase 2) |

---

### 2.8 Conservation ledger (the engine at the operating point, both sides)

Record's deck, the symmetric 2 + 2 supply at 100 GΩ per ring (`sim/hub_rings_build_results.json` `record_supply`):
steady state, the last 8 cycles, 120 Hz.

| term | W | per cycle | Source | Tag |
|:--|--:|--:|:--|:--|
| **in:** belt → varicaps (integrator) | **2.14381** | 17.87 mJ | `record_supply.P_belt_W` | `[OC]` |
| in, cross-check from the waveforms (ΔC·ω·sin·(V1² − V4²)/4) | 2.14381 | — | `record_supply.P_belt_wave_W` | `[OC]` |
| **out:** clamp Z1 | 1.06984 | 8.92 mJ | `record_supply.Z1.P_W` | `[OC]` |
| out: clamp Z4 | 1.06945 | 8.91 mJ | `record_supply.Z4.P_W` | `[OC]` |
| out: the rings' leakage (to the rings, the delivered product) | 0.00448 | 37 µJ | `record_supply.P_leak_W`; ledger §4 "4.5 mW" | `[OC]`; `[RH]` 100 GΩ |
| out: other (the deck's diodes, the bearing link's 1 Ω, stored-energy drift) | 0.00004 | 0.3 µJ | `record_supply.P_other_W` | `[OC]` |
| **residual** (in − out) | **≈ 0** by construction (P_other is the remainder); the independent check: the waveform belt agrees with the integrator to 5e-7 | — | `sim/core_field.py`:248–254 | `[OC]` |

**Charge.** Each clamp passes 81.0 µA avg (675 nC a cycle, `record_supply.Z1.I_avg_mA`). The ring stages pass their
leakage: 14.96 kV / 100 GΩ = 0.15 µA. The link carries 0.19 nA DC (`record_supply.link.I_avg_uA`), so no DC crosses
the bearing. `[OC]`

**As built** (`sim/tube-strays-findings.md` §5): belt 0.646 W, almost all into the clamps.
**Redesign as laid out** (`sim/multiplier-waveforms-findings.md` §2, G2): the charge balance closes to 0.011 % per
chain and to 0.009 % at nodes 1 / 4. `[OC]`

**Does it close?** Yes `[OC]`:
- the belt power equals clamps + leakage + others to 2e-5;
- the delivered fraction (the rings' leakage) is 0.21 % of the belt power;
- the rest is heat in the clamps, the dissipative sink the principle allows. No recovery term exists, and none may be
  added.

**Outside this boundary** (for the conservation-auditor, not part of the engine; ledger §4):
- the magnetic pump: belt 17.6 W (18.1 with the bypass) + iron 1.25 W;
- windage about 12 W; bearings 5 W;
- the bridge-ring bearings +2.1 W (6.1 high).

## Evidence ledger

| Item | Current design | Evidence | Issue (if any) |
|:-----|:---------------|:---------|:---------------|
| z anchor | 1.334 (frozen, G3) | `reference/commutator_real_core.py`; `docs/efficiency-resolution.md` | belongs to the disc machine's stepped schedule, not the tube |
| z tube | 1.3095 bare / 1.191 chains (record); 1.058 / 1.031 as built | `sim/core_field_results.json`; `sim/tube-strays-findings.md` §5 | as built barely self-excites with ideal diodes; with hot sticks it does not (0.967) |
| η | 0.386 / ≈ 0.50 disc; transfer 1.00 tube | `docs/efficiency-resolution.md`; `sim/diode-stack-findings.md` | 0.386 is stepped-model and cut-dependent; the tube has no η of record |
| κ | 7.47 deck vs 3.51 as built | `sim/core_field_results.json`; `sim/tube-strays-findings.md` §4 | the 2-D cell's 2 pF rim floor is in fact +65 pF |
| strays | 20 pF placeholder vs 66.2 / 24.5 pF solved | `sim/tube-strays-findings.md` §3 | the G10 sleeve is 40 pF of node 1's |
| Ca | rule 1.1 C_max; laid out 1.068–1.072 C_max | `sim/tube-strays-findings.md` §4; `sim/doubler-caps-findings.md` §4 | the DECIDED rule needs a sixth gap (495 pF) |
| clamps | 66 parts, V_op 13.13 kV (record); 60 parts, 11.94 kV (layout) | `sim/parts-first-cut-findings.md` §2.4; ledger §3.9 | the trim rests on estimated new-node strays [RH] |
| belt power | 2.14 W record; 0.65 W as built | `sim/core_field_results.json`; `sim/tube-strays-findings.md` §5 | 3.3× loss to the strays |
| seed | 122 V / 1.0 kV / 3.65 kV (record as built); 51 V / 947 V / 4.87 kV (redesign) | ledger §3.4, §5.2 | no seed source designed |
| frozen engine's station phasing | z 1.5225 station-armed vs 1.3340 simultaneous | `sim/island-asdrawn-findings.md` H3 | binds for any Phase 2 commutator |
| D1–D4 reverse | 6.1 / 6.1 / 13.2 / 13.2 kV (record); ≤ 6.11 kV (redesign layout) | `sim/core_field_results.json`; `sim/multiplier-waveforms-findings.md` | — |
| varicap phase in the solids | the record drew C1 / C2 in phase against an antiphase circuit | ledger §6 item 58 | corrected for the record; the redesign wants in phase |

## Cross-spec dependencies

| Item | Value | Needed by | Note |
|:-----|:------|:----------|:-----|
| z target and margin | 1.3095 bare (record); as built 1.058 / 1.031; redesign 1.0142–1.0164 | tube-synth | the tube must state its node-total ratio and z with real sticks hot |
| node-total ratio threshold | ≈ 2.4 for bare z = 1 (ideal diodes, Ca 1.1 C_max) | tube-synth | `[IR]` grid reading |
| varicap C | 54.9–409.9 pF (deck), 128.4–450.6 pF (as built) | tube-synth | solve what is built |
| Ca / Cb | 1.1 C_max rule; 480.5–482.3 pF as laid out | tube-synth | gap count OPEN |
| stray prices | 0.0027 / pF (1 / 4) and 0.0018 / pF (2 / 3) at the record's caps; 0.0006–0.0008 / pF as built | tube-synth | every lead and mount adds stray |
| clamp BV / tolerance | 13.13 kV (66 parts) or 11.94 kV (60, layout); 1.5 % a part; σ 0.36 %; +13 V/K | tube-synth, electrical-integrity | trim warm on the bench |
| operating current | clamp 81 µA avg, 0.95 mA peak (record); 24.9 µA (layout); link 0.41 mA rms (record) / 0.02 µA (redesign) | tube-synth, retainer-spec | the link's AC passes a bearing in the record |
| node voltages, record | 1 / 4: −13.2 ↔ −5.7 kV (mean −8.6); 2 / 3: 0 ↔ −6.1 kV; V_Ca −5.7 ↔ −7.4 kV; V(1) − V(4) ±7.4 kV at 120 Hz; rings ∓14.96 kV | `sim/core_field_results.json`; `sim/hub_rings_build_results.json` | electrical-integrity |
| node voltages, redesign layout | 1: −11.99 / −6.45; 2: 0 / +4.11; l1 −5.86 / −2.99; r1 +2.99 / +5.86; r2 −8.70 / −5.29; xa −14.77 / −11.40; ring A −14.77 kV (side B mirrored); Ca / Cb 13.2 kV DC | `sim/multiplier-waveforms-findings.md` §2; ledger §3.9 | electrical-integrity |
| peak fields | gap face 21.9 kV/cm; rims 44.4 kV/cm (0.80 of Peek's 55.7 smooth); corona onset 16.5 kV smooth, 14.0 kV handled (×1.26 / ×1.07); tab crossings 1.052; G10 sleeve 2.1 kV/mm at the shaft, a bore air film about 10 kV/mm | ledger §3.4, §4; `sim/doubler-caps-findings.md` §3; `sim/core-field-findings.md` §7 | electrical-integrity |
| flashover scenario | a vane flashover at node 4, at its lowest point, lifts ring B 14.96 → 19.03 kV (+27 %), 2 % over the bench's ±18.7 kV hold-off; not run with the redesign's ring stages | `sim/parts-first-cut-findings.md` §2.7; ledger §5.2 | electrical-integrity; OPEN |
| no-clamp failure | 25–47 A diode surges; 38 A through the bearing | `sim/electrostatic-no-clamp-findings.md` | electrical-integrity |
| conservation ledger | §2.8: 2.1438 W in, 2.1393 W clamps, 4.5 mW rings, 41 µW other | `sim/hub_rings_build_results.json` | conservation-auditor |
| η ceiling | tube: no η of record; transfer 1.00 (ideal); disc anchors 0.386 / ≈ 0.50; 0.70 forbidden | §2.3 | conservation-auditor gates any η claim |
| equalization principle | no recovery from rectifying transfers; sinks only | `CONVENTIONS.md`; `docs/efficiency-resolution.md` | conservation-auditor |
| torque | mean 17 mN·m at 2.14 W (5 mN·m as built); 120 Hz ripple 63 (record) / 191 mN·m p-p (redesign) | §2.4 | retainer-spec (gear, the bays' mode near 120 Hz, ledger §6 item 77) |
| pump frequency | 120 Hz at 600 rpm a body | ledger §4 | retainer-spec: f2 108–117 Hz sits near it |

## Items deferred to bench

| Item | Why it is open | What the bench measures | Source |
|:-----|:---------------|:-----------------------|:-------|
| HV sticks' and clamp strings' leakage, hot | the 5 µA hot string and the stick leakage are [RH]; they decide self-excitation | leakage vs temperature at working voltage; the smallest seed | ledger §3.4; `sim/diodes-real-findings.md` §6 |
| as-built z | the 3-D solve omits leads, mounts and parts | growth per cycle from a known seed, clamps out | `sim/tube-strays-findings.md` caveats |
| clamp string length | V_op and the rings' level rest on [RH] new-node strays | VBR of the sorted string, warm; the rings' level | ledger §3.9; `sim/parts-first-cut-findings.md` §2.4 |
| corona onset at the rims and the tab crossings | margins 1.05–1.07 on a handled surface; Peek's m 0.85 is [RH] | onset of the assembled column at 1.45 × V_op | `sim/doubler-caps-findings.md` caveats |
| the rings' hold-off and leakage | the 1 / 5 kV/mm ratings and 100 GΩ are [RH] | DC hold-off to ±20 kV; leakage | `docs/bench-test-rings.md` |

## Recommendations for the designer

All PROPOSED. The designer decides.

1. **PROPOSED:** state which engine tube-synth builds against: the record's doubler with 2 + 2 chains, or the §3.9
   redesign (DECIDED "for now", its layout PROPOSED). The numbers differ in z, Ca / Cb's DC, the clamp length and the
   torque ripple.
2. **DECIDED** (the designer, 2026-10-14): "the engine theory should keep both ideal and real HV diode simulation
   records for the empirical proof to come." Every engine figure is carried in pairs: ideal-diode z (the theory's
   limit) and real-HV-stick z at typical, maximum and hot leakage (`sim/diodes-real-findings.md` §4, §6), with
   neither replacing the other; the bench (phase 4, `docs/bench-test-rings.md`) arbitrates. As built the real hot
   values fall under 1 (0.967 / 0.987), which the record keeps beside the ideal 1.031 / 1.0164. The acceptance
   criterion itself is not set by this decision.
3. **PROPOSED:** specify the varicap by its node-total ratio (≥ the 2.4 bare threshold, plus a margin the designer
   sets). Require insulating mounts on node 1 / 4; every mm of node-1 metal on the sleeve costs about 0.5 pF.
4. **DECIDED** (the designer, 2026-10-14): "sixth gap ok". Ca / Cb take a sixth gap, 495 pF, which meets the
   DECIDED 1.1 C_max rule (`sim/tube-strays-findings.md` §6), against the layout's 5 gaps (480.5 pF; 482.3 pF with the
   mounts' tabs, `sim/doubler-caps-findings.md`). Consequences to carry [IR]: the column grows by one 6 mm gap and one
   plate per side, so the tube length, the masses, the shaft modes and the strays of the layout studies shift; the
   redesign's ring levels and clamp trim were computed on 5 gaps and need re-running.
5. **DECIDED** (the designer, 2026-10-14): no HV seed source. The designer reports, as experimentally established,
   that the simple de Queiroz doubler with four diodes self-starts without an HV seed impulse, in dry sunny weather
   and in high humidity alike, the dry condition starting more easily. If it starts with difficulty, charge injection
   from a rubbed PVC tube (triboelectric) starts it.
   - **Status of the evidence:** the designer's experiment, not reproduced in this repository; no data file holds it
     yet. It stands beside the model, as decision 2 requires, and the bench arbitrates.
   - **What it contradicts in the model** [IR]: `sim/diodes-real-findings.md` §4.1 / §6 and the ledger's §6 items 46 / 65
     ("a contact potential or a triboelectric charge does not start it"; seeds of 122 V / 1.0 kV / 3.65 kV as built,
     4.87 kV hot for the redesign). The model's real-stick leakage and the clamps' hot 5 µA [RH] are the likely
     points where the two part; the bench's phase 4 measures them.
   - **What it does not yet cover** [IR]: the experiment is on the simple four-diode schematic. Whether the §3.9
     redesign (bipolar, C1 / C2 in phase, the C3–C8 ladder, the solved strays, z 1.0164 ideal) self-starts the same
     way is OPEN for the bench. A rubbed PVC tube charges to kV-class potentials [OC, order of magnitude], so as a
     fallback it covers the model's hot seed too; the tube spec must give an accessible injection point and its
     sign.
6. **PROPOSED:** retire z 1.334 / η 0.386 / ≈ 0.50 from any tube-facing table, except as labelled anchors of the disc
   machine.
