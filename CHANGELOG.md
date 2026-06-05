# Changelog

Format adapted from [Keep a Changelog](https://keepachangelog.com/). Git holds the authoritative history; this file is the human-readable audit trail. The discipline is inherited from the DCCREG programme conventions; the physics is mainstream (no DCCREG theory).

## [Unreleased]

### Added
- **Block T v0.1 — built-in transfer caps Ca / Cb** (`docs/brief-blockT-transfer-caps-v01.md`): a producer that designs the physical transfer caps as a **solid annular bus ring** on legs over the stator sectors + Mylar + upper electrode = Ca (top face) / Cb (bottom face).
  - **Bus ring is a full annulus (no keptFrac)** — it buses the otherwise-unconnected stator sectors *and* is the lower Ca/Cb plate (node 1 ↔ 2; mirrored 4 ↔ 3). `transferCaps` consumes `rActiveInner`/`rActiveOuter` from `plateGeom` (Block C-I). **[OC]**
  - **Inverse** (desired Ca → ring width) and **forward** (width → Ca) modes; **inside placement default** (inner edge pinned at `rActiveInner + bracket`, grows outward to clear the rim quadricones, must stay ≤ `rActiveOuter`), **outside** toggle (outer edge pinned at the leg radius, grows inward). Round-trip exact. Worked point: 7 nF → ≈191 mm width at 1 mm Mylar (εr 3.2).
  - **Outputs:** ring width, inner/outer radii, plate area, realised Ca = Cb, band-max Ca, dielectric field (kV/mm), and ½·C·V² energy. **Five warnings:** band overrun (clamps the drawn ring), Ca above band-max, thin-bracket live-clearance, high-field (>40 warn / >100 bad), and the solid-annulus note.
  - **§5d cross-section render:** the copper–Mylar–copper sandwich draws on the **back of each stator plate** in the Block-M axial view (legs → bus ring → Mylar → upper electrode), radial span and Mylar thickness tracking the real producer values; `Ca`/`Cb` labelled with the dimensions overlay; legend swatches added.
  - **Solver hand-off (no `solveDoubler4` edit):** a `tcDrive` toggle routes the realised Ca = Cb into the solver's `ca`/`cb` state at the call site only, raising their field max (Block T is nF-scale, far above the manual 500 pF range) and disabling manual entry — mirroring the rotor-cap raise-max policy.
  - New `tc*` namespace (CONVENTIONS §4), seven self-tests (inverse widths 129/191/258 mm, round-trip, band-max ≈12.3 nF + overrun, Ca=Cb symmetry, field, inside>outside width, 1.4 J energy). Page stamped `T v0.1`.

### Changed
- **Block C-I v0.2 — active-overlap squeeze + C_R decoupling.** `plateGeom` now returns **two** areas: `Ametal_full` (the full rotor face) **and** `Ametal_active` (the swinging rotor↔stator overlap band `[ro+void, plateR−bus−(quadfoot+quadclr)]`). The counter-rotating stator can't reach the central HV tank (inner `pvoid`) nor overlap the 6 rim steel cores (outer `pquadfoot + pquadclr`), so the pump area is squeezed inward at both ends.
  - **`plateCaps` uses the active area** → pump `Cmax` shrinks ≈ ×0.58 at defaults (94 mm steel-core band + 10 mm clearance + 9 mm bus + 20 mm inner void; `A_active ≈ 0.221 m²` vs `A_full ≈ 0.384 m²`).
  - **`resonatorCore` uses `Ametal_full` for `C_R`** — `C_R` is rotor↔rotor through the mica disc, so it's decoupled from the stator clearances and `C_R`/`f0` stay unchanged (verified by a C_R-invariance self-test). **[OC]**
  - New `p`-inputs (mm): `pvoid`, `pbus`, `pquadfoot`, `pquadclr`. New readouts: `A_full`, `A_active`, active band (mm), squeeze ratio. Three warnings: band-collapsed (hard), HV-void floor from the Block-D bias at 1 kV/mm (derated), and the standing decoupling note. Five self-tests (squeeze applied, band radii, **C_R invariance**, pump ∝ active area, collapse guard). Page stamped `C-I v0.2`. `solveDoubler4` untouched.

### Added
- **Block D — Distributed electromagnets (reluctance spin-up motor)** (`docs/brief-blockD-distributed-electromagnets.md`): a fourth independent producer (never writes the rotor caps, never calls `solveDoubler4`) modelling the 12-C-EM stator reluctance motor that spins the machine up.
  - **Iron-rotor reluctance model:** 12 stator C-electromagnets in two interleaved groups of 6 (odd → group A on transfer cap C3, even → group B on C4), uniform winding. The N-S-N-S ring pattern is a *consequence* of the two transfer caps swinging antiphase (push-pull); a parity self-test asserts the A↔C3 / B↔C4 grouping and the adjacent-pole alternation (the assumption the whole map rests on). **[OC]**
  - **Series resonant DC-block cap** (default 440 nF / 20 kV): blocks the kV DC bias, passes the low-frequency stepping drive at minimum impedance (≈R_coil), and stays a high-Z spectator at the central f0 tank — one component doing the DC block, torque tuning, and f0 isolation.
  - **Q / turns / voltage budget** (`demMotor`): resonant `L_coil = 1/((2π·f)²·C)`, `Z0 = √(L/C)`, gapped turns `N = √(L·l_gap/(μ0·A))`, coil R/Q from AWG (reuses `awgToCond`, `MU0`, `RHO_CU`), ripple ceiling `(V_rating−V_bias)/Q`, circulating current `(V_rating−V_bias)/Z0`, peak cap voltage `V_bias + Q·V_ripple`, and the **closed-form ampere-turn limit** `N·I = (V_rating−V_bias)·√(C·l_gap/(μ0·A))` — frequency- and turns-independent (adding turns raises L and Z0 so I drops to compensate). Validated against the brief §4.5 worked example (150 Hz: L≈2.56 H, Z0≈2411 Ω, N≈3190, N·I≈10 585 A-t; 300 Hz: same N·I at half the turns). **[OC]**
  - **Drive-frequency pin (4× swing):** `PRF = events/rev·rpm/60`; alt-stroke (push-pull) ⇒ coil runs at PRF/2, per-stroke ⇒ PRF — a `demDriveMode` toggle, since it sets `L` (and N) by 4×.
  - **Per-coil (×12) vs per-group (×2) caps** toggle (`demCapTopology`): same total stored energy (≈1.06 kJ at 20 kV — lethal HV on the spinning stator), reported per-cap and total.
  - **Over-voltage warnings:** `V_cap,peak > rating`, ripple over ceiling, bias ≥ rating (no torque), plus the standing antiphase-push-pull reminder.
  - **Top-view projection panel** (user-directed, supersedes the brief's §8 side-ring): an axial projection showing the sectored electrode disc (from `pnsec`), the 6 salient rotor iron poles, and the 12 stator C-EMs (steel core + copper coil, group A/B tint, N-S-N-S polarity chips at the C3⁺ instant), with an optional angle/index label overlay and a dedicated legend (`--cem-coil/--cem-core/--cem-a/--cem-b`). Preset `spin-up` at the brief's worked design point.
  - **Seven self-tests** (brief §7): resonance round-trip, Z0 identity, ampere-turn invariance (PRF vs PRF/2, from separate N and I), over-voltage flag, 88 J energy, N-S-N-S antiphase parity, per-group cap = 6·C. New `dem*` namespace documented in `CONVENTIONS.md` §4. Parallel producer; the solver is untouched.
- **Per-parameter inline help.** A single "? param help" toggle in the header (off by default — zero added clutter) reveals a one-line description under every parameter across all four panels (40 descriptions from one `DESC` map; numeric rows + non-numeric controls). Native `title` tooltips are also set on every label. The toggle state round-trips in the URL hash (`help`).
- **Block R — Central resonator** (`docs/brief-blockR-central-resonator.md`): an independent producer (never writes the rotor caps, never calls `solveDoubler4`) modelling the `C_R ∥ L` tank formed by the two conical coils (series, aiding) and the through-mica inter-electrode capacitor.
  - **Inductance** via an exact conical loop-stack: HF self-inductance + Maxwell mutual inductance over all turn pairs, with complete elliptic integrals K/E by the **AGM** (no library); decimation to ≤400 nodes for very fine wire (flagged).
  - **Capacitance** `C_R = ε0·εr_mica·A_align/discH` (electrodes fully aligned — locked premise), a Medhurst self-capacitance estimate, and the coil self-resonant frequency.
  - **LC + loss:** `f0, f_d, Z0, Q (copper-only upper bound), τ, R_dc/R_ac, skin δ`; conductor as **wire (AWG) / tube / manual-OD**, with the verified capillary-tube ≈ solid-rod HF identity (equal f0 & Q at less copper).
  - **Drive from RPM:** `prf = ⌈Nsec/2⌉·rpm/60`, ring cycles per pulse, `settle = τ·prf` and the isolated-ringdown vs build-up regime.
  - Adds the coil to the cross-section (copper band hugging each cone slant, per-turn hatch, tube/wire hint, guard-coloured) and a **colour + hatch legend** (`--copper/--steel/--diel`) toggled with the dimensions overlay; swatches tie readouts to drawing regions. Preset `resonator`. Six self-tests (AGM, C_R, validated L, tube≡rod, AWG, PRF).
  - **Honest correction:** the brief's quoted `L ≈ 235 µH / f0 ≈ 238 kHz` came from a cruder cylindrical estimate; the validated conical loop-stack (cross-checked against Nagaoka) gives `L ≈ 131 µH / f0 ≈ 316 kHz`. The validated value is used and the self-test asserts it. **[corrected openly]**

### Corrected
- **C-I sectored-metal area** now uses the annulus *outside the ring* (`ring-out → plate`) instead of the full disc, removing a ~2 % overcount (the inner disc is the ring/hub, not free sectors). Slightly lowers `Cmax` (default 7237 → 7080 pF; `Cmin` unchanged) and feeds the corrected `A_align` to Block R. The C-I fixed-geometry self-test (ring off) is unchanged. **[review finding]**

### Changed
- **Rotor caps now inherited from the plate-geometry capacitance by default** (`psrc:"plate"`): `C1/C2 min/max` are driven by the Block C-I `Cmin/Cmax` (both rotors via `plink`, the symmetric design) and their inputs are disabled. Only **transfer + stray (Ca/Cb/Cpar)** stay user input (can't be estimated yet). The manual override toggle remains; the Rotor-caps panel shows an "← inherited from plate geometry" tag.

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
