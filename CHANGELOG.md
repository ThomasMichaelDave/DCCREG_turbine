# Changelog

Format adapted from [Keep a Changelog](https://keepachangelog.com/). Git holds the authoritative history; this file is the human-readable audit trail. The discipline is inherited from the DCCREG programme conventions; the physics is mainstream (no DCCREG theory).

## [Unreleased]

### Added
- **Block C-I** implemented in `index.html` — *"Rotor plate — geometry → capacitance"* panel (producer/consumer pattern; `solveDoubler4` untouched):
  - Ported the sectored-disc + ring area math from `reference/SectoredDiscCalculator.jsx` to vanilla JS (`plateGeom`, SI; kept fraction = `ceil(Nsec/2)/Nsec`).
  - Capacitance model `C = ε₀·εr·A/g` with rotation extremes `Cmax`/`Cmin` and the ring as the `Cmin` floor (`plateCaps`); azimuthally-symmetric ring ⇒ rotation-independent floor. **[OC/IR]**
  - Dielectric model: Vacuum (exact 1), live moist-air (`epsAir` — Smith–Weintraub refractivity + Buck 1981 saturation pressure), and fixed-nominal Kapton/Mica with tolerance bands. Env inputs shown only for Air. **[OC; IR for solids]**
  - Plate inputs `pnsec pdia prouter prinner pgap ptempc ppatm prh` added to `FIELDS` (hash-serialise for free); non-numeric controls `pdiel pring plink psrc punit` serialised manually in `writeHash`/`loadFromHash`.
  - Producer pre-step at top of `recompute()`: in `psrc:"plate"` mode geometry drives `c1{min,max}` (and `c2` when `plink`), the derived inputs are disabled, and the rotor-field max is raised to 10000 pF (**raise-max** field-range policy, brief §6.5/§7.1). **[IR]**
  - Warnings: ring inner ≥ outer, ring outer > plate ⌀, `gap ≤ 0`, fringing heuristic (`gap ≳ 10%` of smallest in-plane feature), ring-off (`Cmin=0`, κ_C→∞), `Cmax` clamped, solid-dielectric-in-rotary caveat (§3.3).
  - Presets `plate-air`, `plate-mica` (set `psrc:"plate"`); existing electrical presets now imply `psrc:"manual"`.
  - Plate self-tests added to `runSelfTest()` (brief §6.7): dry-air εr ≈ 1.000576 and fixed-geometry `Cmax` ≈ 347.7 pF — both passing; engine badge stays "engine verified".
- Project scaffolding: `README.md`, `CONVENTIONS.md`, `CLAUDE.md`, `.gitignore`.
- `docs/brief-blockC1-geometry-to-rotorcap.md` — **Block C-I** implementation brief (geometry → rotor-cap front end). Consolidated from two prior drafts:
  - *draft 0.1* — capacitor model (parallel-plate with rotation-dependent overlap), dielectric presets (mica / Kapton / air / vacuum) incl. the moist-air refractivity model, and the symbol-hygiene convention. Targeted a **standalone React extension** of the area engine.
  - *draft 0.2* — **retargeted to integration** into the existing `index.html` doubler in its vanilla-JS idiom; established the producer/consumer pattern (`solveDoubler4` left untouched); added the rotary-varcap dielectric-practicality note (§3.3) and the host-field-id mapping (§1.1).
- `reference/SectoredDiscCalculator.jsx` — parametric area engine (sectored disc + ring; alternating kept sectors, central ring, rotation-overlap). Source for the vanilla-JS port.
- `index.html` — Symmetric Bennet Doubler 4-node pump-action simulator (host; provided, working, self-tested).

### Pending
- Deferred open forks (brief §7): θ-sweep C-vs-θ visualisation; gating solids behind a fixed-gap sub-mode; dielectric-strength → safe-voltage bound and leakage loss (the genuine next block); fringing correction for non-small `gap`.

### Notes
- Adopted **flat filenames + this changelog** as the audit trail, replacing the earlier `_vNN`-suffixed brief files now that the project lives under git.
