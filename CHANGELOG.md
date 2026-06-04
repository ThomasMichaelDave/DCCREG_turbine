# Changelog

Format adapted from [Keep a Changelog](https://keepachangelog.com/). Git holds the authoritative history; this file is the human-readable audit trail. The discipline is inherited from the DCCREG programme conventions; the physics is mainstream (no DCCREG theory).

## [Unreleased]

### Added
- **Stator plates in the Block M cross-section** — a fixed stator plate above and below the rotor, each separated from the rotor electrode by the capacitor gap `g` (C-I `pgap`), with **stator ⌀ = rotor/plate ⌀** and a central clearance at the hub for the cone. Drawn as annular bands (`--edge`) with a dashed gap leader; labelled (stator ⌀ · gap g) when dimensions are on. The gap is drawn to scale but clamped to ≥2 px for legibility. **[IR render]**

### Changed
- **Blocks C-I ↔ M now geometrically coupled** (user-directed; supersedes the briefs' warn-only "do not hard-link" stance, recorded here per the *correct openly* convention):
  - **Plate ⌀ (`pdia`) → disc ⌀ (`mdiscdia`)** — the outer (electrical) diameter family drives the structural disc.
  - **Ring-outer ⌀ (`prouter`) → quadricone/hub ⌀** — `hubDia = prouter`, `coneR = hubDia/2`. The hub is no longer *derived* from key sizing; instead the DIN key/void/shaft assembly becomes a **boundary condition** checked against the ring-set hub (new hard guard *"hub fits ring (key sizing ≤ ring ⌀)"*).
  - Sectors (`pnsec`) remain the primary structural input in C-I (12 → 6 kept/6 gap; 8 → 4/4) and are surfaced in the M panel.
  - Coupling is a toggle (`couple`, default **on**, hashed as `cpl`); when on, the M disc-⌀ input is disabled and tracks the plate ⌀. Standalone mode (and the Block M self-tests, which exercise the key-sizing hub) are unchanged.
  - Defaults retuned to a coherent coupled landing device (1 m plate/disc, 12 sectors, ring/hub ⌀ 150 mm, void 40 / shaft 20 / disc-thick 10 mm) so all guards land green; `rotor-core` preset rebuilt as the coupled showcase, `plate-air`/`plate-mica` set `couple:false`.
  - Ring diameter field maxes raised 50 → 100 cm to allow larger hubs.

### Added
- **Block M — Rotor mechanical core** implemented in `index.html` as a second, independent producer (never writes the rotor caps, never calls `solveDoubler4`; brief §6.4):
  - `docs/brief-blockM-rotor-mechanical-core.md` — the implementation brief.
  - Quadricone + stub-shaft + spherical-void + dielectric-disc geometry ported to vanilla JS (`quadriconeCore`): hub from key sizing (`hubDia = voidDia + shaftDia + 2·keyLen − discH = 2·coneR`), spherical caps + septum belt + bore volumes, and the four hard guards (collar / void-seat / wall / key-fit) + keyway-collar soft guard with a binding-guard readout. **[OC]**
  - DIN 6885-1 key sizing: `keyLenFor` (≈1.5·D snapped up the standard-length ladder) and a key cross-section table (`keySectionFor`) for the keyway/`t₂`. **[OC]**
  - HV-geometry distances reported (`clearN`, `clearEE`, `creepEE`) — geometry only, no safe-voltage assertion (deferred). **[OC]**
  - Inputs `mvoid mdiscvoid mdisch mshaft mwall mdiscdia` added to `FIELDS` (mm); `munit/mfit/mdims` hashed manually. `hubDia` is derived, not an input.
  - **Live axial cross-section** (`drawCrossSection`, canvas, host idiom): isotropic auto-fit with `fit | lock-scale` toggle, mm scale bar + px/mm, toggle-able dimension annotations, and guard-coloured features. Hooked into `drawCharts()`.
  - Warn-only coupling vs the C-I plate (`plateDia` vs `discDia`, hub vs electrode annulus) — panels are deliberately not hard-linked (§4 / open fork §7.1).
  - Preset `rotor-core` (15 cm-class worked example, `hubDia = 150 mm`), leaving electrical/C-I fields untouched.
  - Self-tests added to `runSelfTest()` (§6.6): `hubDia = 197 mm`, void-partition identity (`2·cap + belt = sphere`), and `keyLenFor(35) → DIN 56` — all passing.
  - **[IR] correction:** the brief specified a `cm/in` unit toggle, but `mm` is the realistic base for these component sizes (void 50, disc 1000); Block M works in mm with an `mm | in` toggle. Recorded here per the "correct openly" convention.
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
