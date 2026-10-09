# Claude Code — Handoff

## The project now
The DCCREG turbine's design is **LOCKED** (the designer, 2026-10-09; design state `09243c7`). The current fact sheet is
`docs/ledger/DCCREG-design-ledger.md`. The work is settling its open points (§5), resolving its known inconsistencies
(§6), and keeping the records, studies and drawings consistent with it. Every change of the record is made against
the locked baseline and recorded in `CHANGELOG.md` and the ledger.

## Guardrails (non-negotiable)
1. **The frozen files stay byte-identical** with `b33baa2`: `shuttle_core.py`, `reference/`, `sim/pump_engine.py`,
   `sim/pump_sizing.py`, `sim/pump_synth.py`, `spice/`, `index.html`, `tools/pump-calc*`, `tools/pump-synth*`,
   `tools/charge-pump-synth-live.html`, `tools/schematic.svg`. The check in `README.md` must print 0 before every push.
2. **`index.html` is the retired Bennet-doubler tool.** Never modify `solveDoubler4` or its diode / phase /
   self-test logic. If the tool is ever unfrozen, `docs/brief-blockC1-geometry-to-rotorcap.md` and `CONVENTIONS.md`
   §2–§4 govern it: `FIELDS` / `state` / `$()` / `bindField` / `scheduleRecompute`, URL-hash state (no
   `localStorage`), the CSS-variable dark theme, canvas charts, and its self-tests green.
3. **Tag** every substantive claim and modelling choice [OC] / [IR] / [RH] with `CONVENTIONS.md` §1's meanings, and
   follow its symbol hygiene (never a bare `d`; `g` for a gap; θ / `rotor` for the rotor angle; `pVap`, not `e`).
4. **Every number cites the file that holds it.** A study ships as a script, its `*_results.json` and its
   `*-findings.md`; every figure and drawing is redrawn by its script, never by hand.
5. **The designer decides.** What is DECIDED, PROPOSED or OPEN is the designer's call; the presets and the ledger
   record it. When a choice is the designer's, ask; don't infer.

## Read order
`README.md` → `CONVENTIONS.md` → `docs/ledger/DCCREG-design-ledger.md` → the findings it cites →
`presets/hub-locked.json`.

## Run / verify
- **A study:** `python3 sim/<study>.py`; ngspice runs the circuit decks. Results go to `sim/<study>_results.json`.
- **The ledger:** `python3 docs/ledger/make_ledger_figures.py`, then `python3 docs/ledger/make_ledger.py` (needs
  markdown-it-py, mdit-py-plugins, pypdf and playwright with Chromium). Look at the rendered pages before committing.
- **The frozen-file check** prints 0.

## Commits
Conventional commits, small and reviewable: `feat:`, `fix:`, `docs:`, `test:`, `build:`, `chore:`. `CHANGELOG.md`
records every change of the record, with its reason.

## Scope boundary
The locked design is the baseline. Quantities only the bench can settle (the hold-off ratings, the rings' leakage,
the conductivities) stay OPEN until it measures them (`docs/bench-test-rings.md`).
