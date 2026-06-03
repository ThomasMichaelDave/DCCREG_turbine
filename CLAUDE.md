# Claude Code — Handoff

## Task
Implement **Block C-I** exactly as specified in `docs/brief-blockC1-geometry-to-rotorcap.md`: add a *"Rotor plate — geometry → capacitance"* panel to `index.html` that computes `Cmin`/`Cmax` from plate geometry + gap + dielectric and drives the existing rotor-cap fields.

## Guardrails (non-negotiable)
1. **Do not modify `solveDoubler4` or the diode/phase/self-test logic.** The geometry module is a *producer* of `state.c1min/c1max/c2min/c2max`; the solver is the *consumer*. Wire it via **one pre-step** at the top of `recompute()`.
2. **Use the symbol names and host-field ids in `CONVENTIONS.md` verbatim** — `p`-prefix for plate inputs; no bare `d`; vapour pressure `pVap` not `e`; rotor angle `rotor` not `phi`.
3. **Keep the existing self-tests green**, and **add** the plate self-tests from brief §6.7 (dry-air ε_r ≈ 1.000576; a fixed-geometry C check) into the same self-test table.
4. **Match the host idiom:** `FIELDS`/`state`/`$()`/`bindField`/`scheduleRecompute`, URL-hash state (**no `localStorage`**), CSS-variable dark theme, canvas charts.
5. **Tag modelling choices** with `[OC]`/`[IR]`/`[RH]` in comments.

## Read order
`README.md` → `CONVENTIONS.md` → `docs/brief-blockC1-geometry-to-rotorcap.md` → `index.html` → `reference/SectoredDiscCalculator.jsx`.

## Run / verify
Open `index.html` in a browser. The engine badge must read **"engine verified"** and the self-test table must pass — including the new plate rows. No console errors.

## Commits
Conventional commits, small and reviewable, e.g.:
`feat: add plate geometry panel` · `feat: dielectric model (presets + moist air)` · `feat: wire plate caps into rotor fields` · `test: plate-engine self-tests` · `docs: changelog`.

## Scope boundary
Build the geometry → rotor-cap front end only. Dielectric-breakdown / safe-voltage limits, loss/leakage, and fringing are **out of scope** for this block (listed in brief §7 / README open forks).
