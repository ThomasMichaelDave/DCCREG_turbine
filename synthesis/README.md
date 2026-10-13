# DCCREG Synthesis Bench — Phase 1

Ground-up design synthesis of the DCCREG tube (without spark gaps), using the
locked design branch as a read-only evidence ledger.

## What it is

A structured synthesis that rebuilds the tube's design from validated principles,
informed by the evidence and lessons learned from the locked baseline (`09243c7`,
2026-10-09). The synthesis does not edit the evidence — it produces new
specifications.

## Architecture

```
synthesis-director (opus)
├── core-engine-spec     — the Bennet doubler engine, formalised
├── tube-synth           — the tube assembly (ES pump + motor parts + insulation)
├── electrical-integrity — breakdown, creepage, field clearance audit
├── retainer-spec        — bearings, drive, cage, base frame
└── conservation-auditor — adversarial conservation phase gate
```

The **director** reads the full design context, sequences the specialists
with conservation gates, and produces the consolidated synthesis report.

**Sequencing:**
1. `core-engine-spec` runs first (alone) — produces the target
2. `tube-synth` runs next (needs core spec) — produces the tube design
3. `electrical-integrity` + `retainer-spec` run in parallel (need tube spec)
4. `conservation-auditor` runs last (needs all four specs) — gates the synthesis

Agent definitions live in `.claude/agents/`.

## How to run

From the repo root, invoke the director:

```
claude --agent synthesis-director
```

The director will:
1. Read the design context (CONVENTIONS, CLAUDE.md, review guide, ledger, hub-locked)
2. Write `synthesis/synthesis-plan.md`
3. Dispatch `core-engine-spec` → gate → dispatch `tube-synth` → gate →
   dispatch `electrical-integrity` + `retainer-spec` in parallel → gate →
   dispatch `conservation-auditor` → gate
4. Check cross-spec dependencies
5. Write `synthesis/synthesis-report.md`

To run a single specialist (e.g. to re-run after corrections):

```
claude --agent tube-synth
```

## Outputs

| File | Contents |
|:-----|:---------|
| `synthesis/synthesis-plan.md` | What is being synthesised, agent sequence, cross-spec targets |
| `synthesis/core-engine-spec.md` | The validated Bennet doubler engine: z, η, κ, stray budget, conservation ledger |
| `synthesis/tube-spec.md` | The tube: varicaps, diodes, clamp, sticks, chokes, kick, insulation, envelope |
| `synthesis/electrical-integrity-audit.md` | Breakdown, creepage, field clearance, flashover, hot operation |
| `synthesis/retainer-spec.md` | Bearings, motor, drive, cage, base frame, thermal management |
| `synthesis/conservation-audit.md` | Energy and charge conservation across all specs |
| `synthesis/synthesis-report.md` | Consolidated report with cross-spec verdicts |

All specs use the template in `synthesis/spec-template.md`.

## Phase 1 scope

**Included:**
- The core Bennet doubler engine (validated parameters from the frozen code)
- The tube without spark gaps: varicaps (C1/C2), rings supply chain (chain
  diodes, chain caps), HV sticks (D1–D4), clamp strings (Z1/Z4), motor
  diodes (D1*–D4*), chokes (La/Lb), bypass caps, snubbers, K4 kick
- Air insulation stack
- Electrical integrity against breakdown physics
- The retainer: shaft bearings, motor mount, belt drive, safety cage
- Conservation closure across all specs

**Excluded (Phase 2+):**
- Spark-gap commutator
- The rings as stator assembly
- Control electronics beyond the K4 kick
- Hub structure (interface only)

## Evidence ledger

The synthesis reads from (all on branch `claude/new-session-0az7f9`):
- `CONVENTIONS.md` — epistemic tags, symbols
- `CLAUDE.md` — guardrails, frozen files
- `docs/review-and-scrutiny-guide.md` — the master map
- `docs/ledger/DCCREG-design-ledger.md` — the design record
- `presets/hub-locked.json` — hub specification
- `sim/*-findings.md` — individual study findings
- `sim/*_results.json` — numerical results
- `docs/cost/` — cost data
- `docs/drawings/` — drawing set
- `docs/drive-gear-belt.md` — drive design
- `docs/bench-test-rings.md` — bench plan

## Conservation gates

Every spec must pass conservation before the synthesis proceeds:
1. After core-engine-spec: is z consistent with η?
2. After tube-spec: do the component losses sum correctly?
3. After all specs: does the full power budget close?
4. At every gate: is η ≈ 0.50, not 0.70? Is the equalization principle intact?

The conservation-auditor is pre-committed to the falsification verdict:
if the budget does not close, the synthesis does not pass.
