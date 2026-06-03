# Changelog

Format adapted from [Keep a Changelog](https://keepachangelog.com/). Git holds the authoritative history; this file is the human-readable audit trail. The discipline is inherited from the DCCREG programme conventions; the physics is mainstream (no DCCREG theory).

## [Unreleased]

### Added
- Project scaffolding: `README.md`, `CONVENTIONS.md`, `CLAUDE.md`, `.gitignore`.
- `docs/brief-blockC1-geometry-to-rotorcap.md` — **Block C-I** implementation brief (geometry → rotor-cap front end). Consolidated from two prior drafts:
  - *draft 0.1* — capacitor model (parallel-plate with rotation-dependent overlap), dielectric presets (mica / Kapton / air / vacuum) incl. the moist-air refractivity model, and the symbol-hygiene convention. Targeted a **standalone React extension** of the area engine.
  - *draft 0.2* — **retargeted to integration** into the existing `index.html` doubler in its vanilla-JS idiom; established the producer/consumer pattern (`solveDoubler4` left untouched); added the rotary-varcap dielectric-practicality note (§3.3) and the host-field-id mapping (§1.1).
- `reference/SectoredDiscCalculator.jsx` — parametric area engine (sectored disc + ring; alternating kept sectors, central ring, rotation-overlap). Source for the vanilla-JS port.
- `index.html` — Symmetric Bennet Doubler 4-node pump-action simulator (host; provided, working, self-tested).

### Pending
- Block C-I implementation in `index.html` (see `docs/brief-blockC1-geometry-to-rotorcap.md`).
- Plate-engine self-tests appended to the host `runSelfTest` (brief §6.7).

### Notes
- Adopted **flat filenames + this changelog** as the audit trail, replacing the earlier `_vNN`-suffixed brief files now that the project lives under git.
