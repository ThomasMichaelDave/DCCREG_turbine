# Variable Capacitor → Symmetric Bennet Doubler

A browser-based design tool. A parametric **sectored-disc + ring** capacitor plate, whose geometry, plate gap, and dielectric set the **rotor-capacitance extremes** that drive a **Symmetric Bennet Doubler** switched-capacitor solver. One self-contained `index.html`, no build step.

> **Status.** Host doubler simulator: working, self-tested. **Block C-I** (geometry → rotor-cap front end): *specified, not yet implemented* — see `docs/`.

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
| `index.html` | The app — Symmetric Bennet Doubler 4-node simulator (**host**; Block C-I extends it) |
| `docs/brief-blockC1-geometry-to-rotorcap.md` | Implementation brief for the geometry → rotor-cap module |
| `reference/SectoredDiscCalculator.jsx` | Area-math source to **port** into `index.html` (reference only — not built/served) |
| `CONVENTIONS.md` | Epistemic tags + symbol-hygiene table + host-field-id mapping |
| `CHANGELOG.md` | Human-readable audit trail (git owns the authoritative history) |
| `CLAUDE.md` | Handoff + guardrails for the Claude Code agent |

## Read order (fresh agent or contributor)

`README.md` → `CONVENTIONS.md` → `docs/brief-blockC1-geometry-to-rotorcap.md` → `index.html` (host) → `reference/SectoredDiscCalculator.jsx` (math to port).

## Run

Open `index.html` in any modern browser. No build, no server, no dependencies. State is shareable via the URL hash ("copy share-url").

## Current task

Implement **Block C-I** per `docs/brief-blockC1-geometry-to-rotorcap.md`: add a plate-geometry panel that computes `Cmin`/`Cmax` and drives the rotor fields, leaving `solveDoubler4` untouched (producer/consumer pattern).

## Verification

The page self-tests on load (engine badge + expandable self-test table). Block C-I must (a) keep the existing self-tests green and (b) add plate-engine self-tests — dry-air ε_r ≈ 1.000576 and a fixed-geometry capacitance check — per brief §6.7. These are deterministic and make a clean pass/fail gate for a commit or PR.

## Versioning policy

Git owns history. `CHANGELOG.md` is the human-readable audit trail. **Flat filenames — no `_vNN` suffixes and no in-file revision tables** (git replaces both). Conventional-commit style suggested: `feat:`, `fix:`, `docs:`, `test:`, `refactor:`.

## Open forks

Carried from brief §7: field-range policy (raise-max vs clamp-and-warn); hash round-trip for non-numeric controls; solid-dielectric rotary realisability; optional θ-sweep visualisation; dielectric-strength / safe-voltage bound (the genuine next block); fringing correction.
