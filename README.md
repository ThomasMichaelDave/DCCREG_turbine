# Variable Capacitor → Symmetric Bennet Doubler

A browser-based design tool.

> **Efficiency (validated):** the machine is the **direct Bennet doubler (η 0.386) + the downstream island resonant sink** → **η ≈ 0.45–0.50** (computed in `sim/design_synth.py`). The earlier **η ≈ 0.70** (doubler-core over-transfer) is **forbidden** and superseded — the authoritative record is [`docs/efficiency-resolution.md`](docs/efficiency-resolution.md).
 A parametric **sectored-disc + ring** capacitor plate, whose geometry, plate gap, and dielectric set the **rotor-capacitance extremes** that drive a **Symmetric Bennet Doubler** switched-capacitor solver. One self-contained `index.html`, no build step.

> **Status.** Host doubler simulator: working, self-tested. **Block C-I** (geometry → rotor-cap front end): *implemented and self-tested* in `index.html` — see `docs/` for the brief and `CHANGELOG.md` for the audit trail.

---

## Working discipline

Every substantive claim in the docs (and modelling choices in code comments) carries a tier tag:

- **[OC] Operational Core** — standard, derivable physics/math; true independent of this project.
- **[IR] Interpretive Reading** — a modelling / engineering choice; internally consistent, chosen rather than forced.
- **[RH] Resonance / Heuristic** — suggestive, not load-bearing.

Keep the tiers honest; do not let **[RH]** drift into **[OC]**. Correct openly when rigor demands and record it in `CHANGELOG.md`.

The *methodology* (tier tags, versioned consolidation, open-fork tracking, symbol hygiene, handoff README) is adapted from the **DCCREG programme conventions**. **The physics in this repo is entirely mainstream** — parallel-plate capacitance, rotary variable capacitors, and the Bennet charge doubler. **No DCCREG theory is included or required.**

---

## Repo map

| Path | Role |
|:--|:--|
| `index.html` | The app — Symmetric Bennet Doubler 4-node simulator (**host**; Blocks C-I and M extend it) |
| `docs/brief-blockC1-geometry-to-rotorcap.md` | Implementation brief for the geometry → rotor-cap module |
| `docs/commutator-design.md` | Switching design — physical realisation of the solver's diodes D1–D4 (rotary commutator); geometry frozen, transfer model open |
| `docs/brief-blockM-rotor-mechanical-core.md` | Implementation brief for the rotor mechanical core (quadricone + shaft + void + disc) |
| `docs/brief-blockR-central-resonator.md` | Implementation brief for the central resonator (conical coil + inter-electrode capacitor) |
| `docs/report-tool-functioning.md` | Standalone functional report on the whole tool |
| `reference/SectoredDiscCalculator.jsx` | Area-math source to **port** into `index.html` (reference only — not built/served) |
| `CONVENTIONS.md` | Epistemic tags + symbol-hygiene table + host-field-id mapping |
| `CHANGELOG.md` | Human-readable audit trail (git owns the authoritative history) |
| `CLAUDE.md` | Handoff + guardrails for the Claude Code agent |

## Read order (fresh agent or contributor)

`README.md` → `CONVENTIONS.md` → `docs/brief-blockC1-geometry-to-rotorcap.md` → `index.html` (host) → `docs/commutator-design.md` (switching realisation) → `reference/SectoredDiscCalculator.jsx` (math to port).

## Run

Open `index.html` in any modern browser. No build, no server, no dependencies. State is shareable via the URL hash ("copy share-url").

## Current task

Blocks **C-I** (geometry → rotor caps) and **M** (rotor mechanical core) are implemented in `index.html`. Both follow the producer/consumer discipline: C-I drives the rotor caps; M is an independent producer (geometry + cross-section readout) that never touches `solveDoubler4`.

## Verification

The page self-tests on load (engine badge + expandable self-test table). The gate is deterministic: the four original solver tests + swap symmetry, the C-I plate tests (dry-air ε_r ≈ 1.000576; fixed-geometry capacitance), and the Block M tests (`hubDia = 197 mm`; void-partition identity; `keyLenFor(35) → DIN 56`) must all pass — badge reads "engine verified".

## Versioning policy

Git owns history. `CHANGELOG.md` is the human-readable audit trail. **Flat filenames — no `_vNN` suffixes and no in-file revision tables** (git replaces both). Conventional-commit style suggested: `feat:`, `fix:`, `docs:`, `test:`, `refactor:`.

## Open forks

Carried from brief §7: field-range policy (raise-max vs clamp-and-warn); hash round-trip for non-numeric controls; solid-dielectric rotary realisability; optional θ-sweep visualisation; dielectric-strength / safe-voltage bound (the genuine next block); fringing correction.
