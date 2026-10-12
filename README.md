# DCCREG turbine

A counter-rotating machine that holds two static fields at the centre of a glass vacuum sphere: the steady magnetic
cusp of an anti-Helmholtz (AH) coil pair, with its null at the centre, and a DC electric field at the same null. Both
fields come from charge pumps driven by the relative rotation of the machine's two bodies.

> **Status: the design is LOCKED for now** (the designer, 2026-10-09; design state `09243c7`). The current fact sheet
> is the ledger, [`docs/ledger/DCCREG-design-ledger.md`](docs/ledger/DCCREG-design-ledger.md) (and `.pdf`). Later
> changes are recorded against it, in `CHANGELOG.md` and the ledger.

## Start here

| what | where |
|:--|:--|
| the overview, the design logic, each component's working principle, the fact sheet, the status and open items, the known inconsistencies | `docs/ledger/DCCREG-design-ledger.md` (print form `.pdf`) |
| a guide for a reviewer and for the scrutiny bench: what to share, where every study, script, drawing and document lives, and what the models leave to measurement | `docs/review-and-scrutiny-guide.md` |
| every technical drawing, one A3 sheet each, behind a register | `docs/ledger/DCCREG-drawings-bundle.pdf` (register: `docs/ledger/register.py`) |
| the drawing set (PROPOSED, Rev A drafts): a drawing with a small 3-D view for every part, a source-control sheet for every bought part, the sub-assemblies and the general arrangement, of the layout and of the first cuts' parts outside it (the chokes, the kick, the drive) | `docs/drawings/set/` (its order: `docs/drawings/set-index.json`; generator `docs/make_drawing_set.py`; the first cuts in solids: `sim/unmodelled_parts.py`, `sim/unmodelled-parts-findings.md`); the bundle's Part D |
| the hub's specification of record | `presets/hub-locked.json` |
| the rings: design, manufacturing drawing, bench test | `docs/rings-design.md`, `docs/drawings/DCCREG-HUB-201.pdf`, `docs/bench-test-rings.md` |
| the utron's manufacturing drawing | `docs/drawings/DCCREG-UTR-101.pdf` |
| the cost sheet (placeholders) | `docs/cost/README.md`, `docs/cost/dccreg-air-build-cost-sheet.xlsx` |

## The machine, in brief

- **Two bodies on one vertical axis,** side A below, side B above, mirror images about the hub. The rotor turns at
  +600 rpm and the counter-rotor at −600 rpm, through a 1 : −1 reversing gear driven by a belt: 1200 rpm relative.
- **The magnetic pump:** three wound utrons per side on the rotor pass six passive SiFe bridges on the counter-rotor
  (120 Hz), wired as the planar dual of a diode charge doubler. It drives the AH coil pair.
- **The electrostatic pump:** an air vane stack per side (6 + 6 aluminium vanes, 6 mm gaps) in a de Queiroz diode
  doubler, clamped at 13.1 kV. Two mirrored Cockcroft-Walton chains lift two copper rings on the sphere to ±15.0 kV.
  - **Being redesigned (2026-10-10):** the designer is stacking the multipliers into the doubler. The proposal runs
    it bipolar with the varicaps in phase and feeds each ring from one stage past its varicap node: ±14.93 kV as
    built (`sim/integrated-multiplier-findings.md`; the ledger's §3.9). The designer took it "for now" (2026-10-11).
  - **Its layout** (2026-10-11, PROPOSED): every diode and the multiplier's capacitors go on a potted deck round a
    grounded can over the hub, and Ca / Cb's plates go between the deck and the vanes. The machine is 974 mm (1014 with
    its bridge-ring bearings), with no hub-face bearings; the clamp strings drop to about 60 parts
    (`sim/multiplier-layout-findings.md`; `docs/figures/multiplier-layout.png`).
  - **In 3-D, its circuit running:** the layout in solids (`sim/tube_geometry.py --layout`, 552 solids) and its
    circuit simulated through a cycle and its start-up (`sim/multiplier_waveforms.py`). The viewer is
    `tools/step-viewer/layout.html`: every conductor coloured by its potential, each diode lit while it conducts
    (`sim/multiplier-layout-3d-findings.md`, `sim/multiplier-waveforms-findings.md`).
  - **Its bridge-ring bearings** (2026-10-11, PROPOSED): an SKF 6205-2Z between the shaft and each bridge ring's outer
    end, in the record's end-bearing slot, with the end bearing one slot out (1014 mm). They hold the shaft's first
    mode at 83–87 Hz at d 25 (`sim/bridge_ring_bearings.py`, `sim/bridge-ring-bearings-findings.md`).
  - **Its capacitors' mounts** (2026-10-11, PROPOSED): Ca / Cb as two combs, each on its own posts in the column's
    bore, C1 / C2 on G10 spacer rings and glass-epoxy tie rods, the cage moved out to r 182. They hold the record's HV
    rules at every new interface (`sim/doubler_caps.py`, `sim/doubler-caps-findings.md`).
  - **Its drawing set** (2026-10-11, Rev A drafts): 103 sheets drawn from the solids, every part with its own drawing
    and 3-D view (`docs/make_drawing_set.py`, `docs/drawings/set/`). 24 of them draw the first cuts' parts outside
    the layout: La / Lb, the start kick, the bevel reverser and the belt drive, with their bought parts. Drawn, the
    drive's first cut needs five changes (`sim/unmodelled-parts-findings.md`; the ledger's §6 item 74).
- **The hub:** a 50 mm borosilicate vacuum sphere in a PEEK retainer with a silicone-gel interface, the AH's MnZn
  cores on the axis. At its centre: the AH's null and 7.62 kV/cm from ring B to ring A, steady (8.2 once settled).
- **The model checks** (2026-10-09; the ledger's §6 items 31–34) found both pumps weaker than recorded: the AH holds
  about 250–270 A-turns in the best estimate, not 300, and the electrostatic pump as built (its vanes' rims and the
  tube's strays solved, real HV diodes) does not self-excite and holds about 6.8 kV/cm. The record's values stay as
  its basis, with the corrected ones beside them, until the designer decides (the ledger's §5.2).
- **The physics is mainstream throughout** [OC]. The ratings, the leakage and several parts are placeholders that
  the bench test qualifies.

## Working discipline

Every substantive claim in the docs, and every modelling choice in code comments, carries a tier tag
(`CONVENTIONS.md` §1):

- **[OC] Operational Core** — standard, derivable physics/math; true independent of this project.
- **[IR] Interpretive Reading** — a modelling / engineering choice; internally consistent, chosen rather than forced.
- **[RH] Resonance / Heuristic** — suggestive, not load-bearing.

Keep the tiers honest; do not let **[RH]** drift into **[OC]**. Correct openly when rigor demands and record it in
`CHANGELOG.md`. Every number cites the file that holds it. A study ships as a script, its results JSON and its
findings markdown; every figure and drawing is redrawn by its script.

The *methodology* (tier tags, versioned consolidation, open-fork tracking, symbol hygiene, handoff README) is
adapted from the **DCCREG programme conventions**. The physics in this repository is entirely mainstream.

## Repo map

| path | role |
|:--|:--|
| `docs/ledger/` | the ledger, the drawings bundle, and their builder (`make_ledger.py`, `make_ledger_figures.py`) |
| `presets/` | the specifications of record (`hub-locked.json`) and the registers of earlier phases |
| `sim/` | the studies: a script, its `*_results.json` and its `*-findings.md` each |
| `docs/` | design documents; `drawings/`, `figures/`, the schematics and their `make_*.py` generators; `cost/` |
| `docs/geometry/` | the 3-D model's outputs (STEP, GLB, part lists, sections) |
| `tools/` | the browser tools of the earlier phases (see `tools/README.md`) |
| `index.html`, `reference/`, `shuttle_core.py`, `spice/` | the first phase's browser tool and cores (frozen, history) |
| `CONVENTIONS.md`, `CHANGELOG.md`, `CLAUDE.md` | conventions, the audit trail, the agent handoff |

## Read order (fresh agent or contributor)

`README.md` → `CONVENTIONS.md` → `docs/ledger/DCCREG-design-ledger.md` → the findings it cites →
`presets/hub-locked.json`.

## Regenerate

The ledger's §8 lists the studies, drawings and figures in the order to regenerate them. The ledger itself:
`python3 docs/ledger/make_ledger_figures.py`, then `python3 docs/ledger/make_ledger.py` (needs markdown-it-py,
mdit-py-plugins, pypdf and playwright with Chromium). The circuit studies need ngspice.

## Frozen files

These stay byte-identical with commit `b33baa2`: `shuttle_core.py`, `reference/`, `sim/pump_engine.py`,
`sim/pump_sizing.py`, `sim/pump_synth.py`, `spice/`, `index.html`, `tools/pump-calc*`, `tools/pump-synth*`,
`tools/charge-pump-synth-live.html`, `tools/schematic.svg`. The check, which must print 0:

```
git diff b33baa2 -- shuttle_core.py reference/ sim/pump_engine.py sim/pump_sizing.py sim/pump_synth.py spice/ \
  index.html tools/pump-calc* tools/pump-synth* tools/charge-pump-synth-live.html tools/schematic.svg | wc -l
```

## History

The repository began as a browser design tool, `index.html`: a sectored-disc variable capacitor driving a symmetric
Bennet doubler (Blocks C-I, M, R, D, T, S; it self-tests on load, "engine verified"). It went on through:
1. a disc spark-gap machine, frozen at v0.10;
2. the exact pump engines (PUMP-CALC, PUMP-SYNTH);
3. the round trip and the design loop;
4. the tube with diode stacks;
5. the pivot to two geared pumps;
6. the air build, the field at the core, the locked hub and the rings.

The ledger's §2 tells that path, step by step.

- **Efficiency:** the η ≈ 0.45–0.50 of `docs/efficiency-resolution.md` (the direct Bennet doubler 0.386 + a
  downstream island sink) belongs to the disc spark-gap machine. `index.html`'s banner still reads η ≈ 0.70, which
  that resolution forbids; the file is frozen, so it is flagged, not edited. The current machine has no efficiency
  of record: its products are static fields, and the belt's power ends as heat.
- **The first phase's brief and verification:** `docs/brief-blockC1-geometry-to-rotorcap.md`; open `index.html` in a
  browser, and the engine badge reads "engine verified" with every self-test passing.

## Versioning policy

Git owns history. `CHANGELOG.md` is the human-readable audit trail. **Flat filenames — no `_vNN` suffixes and no
in-file revision tables** (git replaces both). Conventional-commit style: `feat:`, `fix:`, `docs:`, `test:`,
`refactor:`, `build:`.
