# DCCREG Scrutiny Bench

Multi-agent adversarial scrutiny of the DCCREG turbine's locked design.

## What it is

A structured investigation that tests the locked design (`09243c7`, 2026-10-09)
across four domains — electrostatic pump, reluctance motor, mechanical integrity,
and cost/sourcing — then cross-references the findings at the domain boundaries.

The scrutiny does not change the design. It tests it.

## Architecture

```
scrutiny-director (opus)
├── es-pump-scrutiny    — electrostatic domain
├── mag-pump-scrutiny   — reluctance motor / magnetic pump
├── mech-scrutiny       — mechanical integrity
└── cost-scrutiny       — cost and sourcing
```

The **director** reads the full design context, dispatches the four specialists
in parallel, collects their findings, and checks the cross-domain dependencies
that no single specialist can see.

Agent definitions live in `.claude/agents/`.

## How to run

From the repo root, invoke the director:

```
claude --agent scrutiny-director
```

The director will:
1. Read the design context (CONVENTIONS, CLAUDE.md, review guide, ledger, hub-locked)
2. Write `scrutiny/investigation-plan.md`
3. Dispatch the four specialists in parallel
4. Collect findings and check cross-domain dependencies
5. Write `scrutiny/scrutiny-report.md`

To run a single specialist (e.g. for a partial re-check):

```
claude --agent es-pump-scrutiny
```

## Outputs

| File | Contents |
|:-----|:---------|
| `scrutiny/investigation-plan.md` | What is under scrutiny, specialist assignments, cross-domain targets |
| `scrutiny/es-pump-scrutiny-findings.md` | Electrostatic domain findings |
| `scrutiny/mag-pump-scrutiny-findings.md` | Magnetic pump / motor findings |
| `scrutiny/mech-scrutiny-findings.md` | Mechanical integrity findings |
| `scrutiny/cost-scrutiny-findings.md` | Cost and sourcing findings |
| `scrutiny/scrutiny-report.md` | Consolidated report with cross-domain verdicts |

All findings use the template in `scrutiny/findings-template.md`.

## Cross-domain dependencies

These are the seams between domains — where one domain's numbers feed another's
margins. The director checks these after collecting all findings.

### Electrical ↔ Mechanical
- Magnetic pull per utron (mag) + 1 g deflection (mech) vs 500 µm gap
- Shaft first mode (mech) vs pump excitation frequency 2× PRF (es-pump)

### Electrostatic ↔ Electrostatic (redesign coherence)
- Stray assumption (24.5 pF [RH]) vs as-laid-out (1–3 pF) — does clamp trim hold?
- TVS rating shift → rings voltage → hub field clearance

### Cost ↔ Design
- Discontinued parts → design dependency
- Single-source risk (borosilicate spheres) → fallback

## Design context

The scrutiny reads from:
- `CONVENTIONS.md` — epistemic tags, symbols
- `CLAUDE.md` — guardrails, frozen files
- `docs/review-and-scrutiny-guide.md` — the master map
- `docs/ledger/DCCREG-design-ledger.md` — the design record
- `presets/hub-locked.json` — hub specification
- `sim/*-findings.md` — individual study findings
- `sim/*_results.json` — numerical results
- `docs/cost/` — cost data
- `docs/drawings/` — drawing set
