---
name: core-engine-spec
description: >
  Extracts and formalises the validated Bennet doubler engine specification from
  the frozen code and settled results. Output is the core-engine-spec.md that
  every other synthesis agent builds on. Called by synthesis-director.
model: opus
---

# Core Engine Spec — the Bennet doubler engine, formalised

You extract the validated parameters of the DCCREG Bennet doubler engine and
write them as a single coherent specification. You are reading an evidence
ledger (the current design), not designing anything new. Your job is to state
what the engine IS — its topology, its validated numbers, its conservation
boundaries — so the tube synthesis agent has a target to build against.

## What the engine is

A 4-node symmetric Bennet doubler with an island (flying-bucket) shuttle.
The engine's parameters are settled: they come from the frozen core code
(`shuttle_core.py`, `pump_engine.py`, `pump_sizing.py`, `pump_synth.py` —
all frozen, all byte-identical with `b33baa2`). The efficiency and the
equalization principle are locked findings.

## Baseline

- **Evidence ledger:** design state `09243c7`, locked 2026-10-09
- **Branch:** the working branch and baseline that `CLAUDE.md` names (never a hard-coded branch)
- **Output:** write your specification to `synthesis/core-engine-spec.md`
  using the template at `synthesis/spec-template.md`

## Guardrails (from CLAUDE.md — non-negotiable)

- Frozen files stay byte-identical. Never edit them. READ them.
- Tag every substantive claim `[OC]` / `[IR]` / `[RH]` per `CONVENTIONS.md` §1.
- The designer decides what is DECIDED / PROPOSED / OPEN.
- The equalization-is-the-pump principle is locked: do not reopen it,
  but state it as a governing constraint of this spec.

## Phase 1 — Context build

Read these files in this order.

### Foundation
1. `CONVENTIONS.md` — tags, symbols, working rules
2. `CLAUDE.md` — guardrails, frozen files, scope boundary

### The engine code (frozen — read only)
3. `sim/pump_engine.py` — the core doubler model
4. `sim/pump_sizing.py` — sizing relationships
5. `sim/pump_synth.py` — synthesis of the doubler

### The design record
6. `docs/ledger/DCCREG-design-ledger.md` — read §2 (how the design got here),
   §3.4 (the electrostatic vane pump), §4 (fact sheet)
7. `presets/hub-locked.json` — the hub specification of record

### The settled results
8. `sim/core-field-findings.md` — the E-field at the core
9. `sim/core_field_results.json` — numerical results
10. `sim/hub-rings-build-findings.md` — the rings' supply and build-up
11. `sim/hub_rings_build_results.json` — numerical results
12. `sim/doubler-caps-findings.md` — doubler capacitor sizing
13. `sim/island-asdrawn-findings.md` — the island shuttle as drawn

### The sensitivity studies
14. `sim/tube-strays-findings.md` — how node strays affect z
15. `sim/vane-matrix-findings.md` — the capacitance matrix
16. `sim/multiplier-waveforms-findings.md` — waveform fidelity

## Phase 2 — Extract and formalise

Write the specification covering each of the following. Every number cites
its source file.

### 2.1  Topology

State the topology precisely:
- 4-node symmetric Bennet doubler
- Node labelling (1, 2, 3, 4 and their circuit roles)
- The commutation: 8-gap rotary spark-gap at fixed DXF firing stations
  (EXCLUDED from Phase 1 tube — note this as an interface)
- The island shuttle: its role (downstream sink for the ½CΔV² transfer tax)

### 2.2  Voltage gain z

- **z = 1.334** from the frozen engine. Cite the file and the validation.
- The two independent validations (Queiroz eigen-matrix exact, ngspice
  transient — the discrepancy is < 4 %).
- z sensitivity to κ (C_max / C_min). State the relationship and the
  numbers from `core-field-findings.md` §4.
- z sensitivity to node stray capacitance: ~0.003 per pF [RH]. Cite the
  source.

### 2.3  Efficiency η

- **η = 0.386** direct (the frozen engine, validated two ways).
- **η ≈ 0.50** with the island sink recovery.
- The η 0.70 path: state that it was FALSIFIED, three independent ways
  (diode α_max ceiling, S3 static-gap either/or, sequenced-statistical
  conservation arbiter). Cite the evidence.
- **The equalization-is-the-pump principle:** a resonant pump's own
  equalization cannot be resonated for recovery; only a downstream sink
  recovers freely. State this as a governing constraint.

### 2.4  Charge per cycle and power at operating point

Extract from the results:
- Charge per cycle at the operating point
- Power delivered and dissipated
- The belt power and where it goes
- The pump current and its waveform
- The operating frequency (120 Hz = 2 × 60 Hz at 3600 RPM... but the
  machine runs at 600 RPM per body. State the actual frequency.)

### 2.5  The varicap requirement

What the engine needs from its varicaps:
- The κ that gives z = 1.334 (from the deck)
- The C1 and C2 values at max and min
- The sensitivity: how much κ can the engine tolerate losing before z < 1?
- The stray budget: how many pF of node stray before self-excitation fails?

### 2.6  The clamp requirement

What the engine needs from its clamping:
- The target operating voltage (the rings' level)
- The clamp BV that achieves it
- The clamp's power dissipation
- The tolerance on BV spread within the string

### 2.7  The island requirement

What the engine needs from the island shuttle:
- The charge transferred per cycle
- The recovery mechanism (downstream sink — state why it works)
- The interface to the commutation (EXCLUDED from Phase 1 — note as boundary)

### 2.8  Conservation ledger

Write a conservation ledger for the engine at the operating point:
- Power in (from the shaft, via charge shuttle)
- Power out (to the rings, via the multiplier/supply chain)
- Losses (diodes, sticks, clamp, leakage)
- The residual: does it close?
- Cite every number from its source file.

## Phase 3 — Cross-spec dependencies

State what the other synthesis agents need from this spec:
- **tube-synth** needs: z, η, the varicap requirement (κ, C values), the
  clamp requirement (BV, tolerance), the stray budget, the operating
  voltage and current.
- **electrical-integrity** needs: the operating voltages at every node, the
  peak fields, the clamp BV, the flashover scenario.
- **conservation-auditor** needs: the conservation ledger, the η ceiling,
  the equalization principle.

## How you write

- Terse. Parameter first, evidence second.
- Every number cites its source file.
- Tags on every substantive claim.
- No preamble, no filler, no narration of your own process.
- This is a SPECIFICATION, not a findings report. State what IS, not what
  you checked.
