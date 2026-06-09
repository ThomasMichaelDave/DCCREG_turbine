# External Review Report — Rotary-Varicap Bennet-Doubler Design Calculator

**Artifact under review:** `index.html` — a single, self-contained web page (no build, no server, no dependencies, no network, no `localStorage`).
**Build stamp:** `C-I v0.2 · T v0.1 · flow+presets v0.2 · xsec v0.2.2 · S v0.1 · commutator v0.1` (shown in the page header).
**Reviewed against:** commit `df5b9fe` (2026-06-08). Every numeric anchor in this report was re-verified by a headless run of the page's own self-test battery and producer functions on this commit.
**Companion document:** `docs/report-tool-functioning.md` — a deeper functional walk-through of the host solver and Blocks C-I/M. This report is the authoritative, current overview: it covers all blocks (host, C-I, M, R, D, T, design-flow, S, and the commutator render) and supersedes the companion's block coverage where they differ.
**Purpose:** give an external reviewer everything needed to judge the tool's correctness, scope, and honesty — what it claims, how each claim is validated, what was deliberately corrected, and what is explicitly out of scope.

---

## 0. Provenance firewall (read first)

The **working methodology** — epistemic tier tags, a `CHANGELOG.md` audit trail, symbol-hygiene rules, and producer/consumer discipline — is adapted from the "DCCREG programme conventions."

**The physics and mathematics are entirely mainstream.** Specifically: parallel-plate capacitance, a rotary variable capacitor, the cross-coupled Bennet charge doubler, standard solid-mechanics geometry, the Smith–Weintraub air-refractivity relation, the Buck (1981) saturation-vapour-pressure correlation, DIN 6885 parallel-key sizing, circular-loop self/mutual inductance via complete elliptic integrals (AGM), the skin effect, LC resonance, series-resonant DC-block coupling, and the salient-pole reluctance-torque relation `T = ½·i²·dL/dθ`. **No proprietary or unconventional theory is used or required.** Every substantive claim in code and docs carries a tier tag so a reader can separate standard results from modelling choices:

- **[OC] Operational Core** — standard derivable physics/math; true independent of this project.
- **[IR] Interpretive Reading** — a modelling / engineering choice; internally consistent, chosen.
- **[RH] Resonance / Heuristic** — suggestive framing, not load-bearing.

---

## 1. What the tool is

An interactive design calculator for one electromechanical device: a **rotary variable capacitor that drives a symmetric 4-node Bennet voltage doubler**, with the surrounding mechanical core, central resonator, reluctance spin-up motor, and built-in transfer capacitors all modelled in the same page. It connects layers normally treated separately, so a designer moves from *physical dimensions* to a *predicted electrical pumping ratio* plus mechanical, resonant, motor, transfer-cap, and firing-sequence characterisations in a single view, with a cascade that derives the dependent parameters from a handful of primaries.

It is an **exploration / sizing tool** — **not** a manufacturing release and **not** a hardware-validated simulator. It answers: "for this geometry, gap, dielectric, and a few electrical inputs, does the doubler pump (z > 1), how strongly, with what margin — and is the implied machine physically coherent?"

---

## 2. Architecture and the central safety property

- **Single global `state`** holds every parameter. The 59 numeric inputs are declared once in a `FIELDS` table (`id, default, min, max, step`) and auto-wired to a paired range slider + number box; non-numeric controls (enums, checkboxes) are handled explicitly.
- **Reproducibility:** the complete parameter set serialises into the URL hash on every change ("copy share-url"); opening that URL reproduces the exact state. No server, no database, no storage.
- **Producer / consumer discipline (the load-bearing invariant).** The electrical engine `solveDoubler4(...)` is the **consumer** and is **never edited by feature work**. Every other block is a **producer** that computes geometry/physics and, at most, writes the solver's *input* state at a single call site:

| Block | Role | Touches the solver? |
|---|---|---|
| Host `solveDoubler4` | switched-capacitor network solver → pumping ratio `z` | — (consumer, frozen) |
| **C-I** plate geometry | geometry + gap + dielectric → rotor `Cmin/Cmax` | drives rotor caps (pre-step) |
| **M** mechanical core | quadricone / shaft / void / disc, DIN keys, HV clearances, guards | no — readouts + cross-section |
| **R** central resonator | conical-coil `L ∥ C_R` tank, f₀/Q/ringdown | no — readouts + cross-section |
| **D** distributed-EM motor | 12-C-EM reluctance spin-up, Q/turns/voltage budget | no — readouts + top-view |
| **T** transfer caps | bus-ring Ca/Cb geometry → capacitance | optional `tcDrive` writes `ca`/`cb` at call site |
| **Design-flow + presets** | one-pass cascade of primaries → slaved inputs; JSON preset load/save | only via the documented `tcFromCmax`/`tcDrive` call-site wiring |
| **S** firing sequence | read-only `traceDoubler4` trace → 4 firing/clocking panels | no — pure sink, never writes solver state |
| **Commutator** render | physical realisation of D1–D4: axial companion + front-view overlay | no — render/consumer, reads geometry only |

A reviewer can verify the invariant directly: the five frozen primitives (`solveLinear`, `chargesFromVoltages`, `solvePhase`, `solveDoubler4`, `zSym`) are **byte-identical** across every feature commit (verified by per-function md5). All feature work is upstream of them.

- **Self-test gate.** The page runs a fixed battery of deterministic checks **on load**; the "engine verified" badge turns green only if **all** pass, and an expandable table shows every row (§5).
- **Render layer.** All canvases use a shared 2D idiom (`clearCanvas` → measured `{ctx,w,h}`), so panels reflow to their container. The four Block-S panels and the Block-M cross-section are full-width; the polar clocking map gets its own enlarged full-width canvas. Drawing is read-only and never feeds back into state.

---

## 3. Block-by-block technical summary (with validated anchors)

All anchors below are the values produced by this commit (default cascaded state unless noted), confirmed in the headless run.

### Host — symmetric 4-node Bennet doubler `[OC]`
Cross-coupled regenerative topology (C1:1↔0, C2:4↔0 variable; Ca:1↔2, Cb:3↔4 fixed; Cpar per node; diodes D1 2→0, D2 3→0, D3 1→3, D4 4→2). Each phase brute-searches all 16 diode on/off states, keeps those consistent with the off-diode bias constraints, takes the one maximising |V₁|+|V₄|, iterates two-phase cycles, and returns the median asymptotic per-cycle ratio `z`. **Anchors:** no-swing → z = 1.000; device (160–1000 pF) → z = 1.203; wide (100–2000) → z = 1.438; narrow (400–600) → z = 1.000; C1↔C2 swap symmetric.

### Block C-I — plate geometry → rotor capacitance (v0.2) `[OC] / [IR]`
A sectored disc (alternating kept sectors) + an optional conductive central ring set a finite `Cmin` floor; dielectric is vacuum, **live moist air** (Smith–Weintraub + Buck), or fixed-nominal mica/Kapton; `C = ε₀·εᵣ·A/g`.
**v0.2 active-overlap correction.** The swinging rotor↔stator overlap is **not** the full rotor face: the counter-rotating stator cannot reach the central HV tank (inner void `pvoid`) nor overlap the 6 rim steel cores (outer quad band `pquadfoot + pquadclr`). `plateGeom` now returns **two** areas — `Ametal_full` (full face) and `Ametal_active` (band `[ro+pvoid, plateR−pbus−(pquadfoot+pquadclr)]`). **The pump (C1/C2) uses the squeezed active area; the resonator C_R uses the full face — they are decoupled.** **Anchors (defaults):** `A_active = 0.2211 m²`, `A_full = 0.3839 m²` (squeeze 0.576), active band 95…387 mm; `Cmax = 4.20 nF`, `Cmin = 278 pF` (ring on); dry-air εᵣ(0 °C, 1013 hPa, 0 %) = 1.000576.

### Block M — rotor mechanical core `[OC] / [IR]`
A 45° "quadricone" pair + stub shafts + spherical void + dielectric disc/septum. The hub comes from DIN 6885 key sizing, or from the C-I ring when coupled; spherical-cap/belt/bore volumes; four hard feasibility guards (collar / void-seat / wall / key-fit) + a keyway-collar soft guard; HV clearance/creepage geometry; and a live, dimensioned, scale meridional cross-section. **Anchors:** hubDia(void 50, shaft 35, discH 0) = 197 mm; void partition 2·cap + belt = sphere; `keyLenFor(35)` → DIN 56; default coupled coneR 75 mm, hub ⌀ 150 mm, disc ⌀ 1000 mm. Working unit is **mm** (correction C2).

### Block R — central resonator `[OC]`
A `C_R ∥ L` tank: two conical coils (series, aiding) wound on the quadricones, and the through-mica inter-electrode capacitor. Inductance via an exact conical loop-stack — HF self-inductance + Maxwell mutual over all turn pairs, with complete elliptic integrals by the AGM (no library), decimated to ≤400 nodes for fine wire (flagged). Plus a Medhurst self-capacitance estimate and coil self-resonance; `f₀, f_d, Z₀`, a **copper-only (upper-bound) Q**, ringdown τ, skin δ; RPM-driven PRF and the ringdown-vs-build-up regime. **Anchors:** `ellipKE(0)` → K = E = π/2; capillary `C_R = 1.91 nF`; validated loop-stack `L ≈ 131 µH` (capillary self-test config); default coupled tank `L = 123 µH, f₀ = 326 kHz`; tube OD3/ID1 ≡ rod OD3 at HF; `awgToCond(20)` = 0.812 mm; PRF(N12, 3000 rpm) = 300 Hz. (The brief's `f₀ ≈ 238 kHz` was a cruder cylindrical estimate — see correction C3.)

### Block D — distributed-electromagnet spin-up motor `[OC] / [IR]`
12 stator C-electromagnets in two interleaved groups of 6 (odd → group A on transfer cap C3, even → group B on C4), uniform winding; the N-S-N-S ring pattern is a *consequence* of the two transfer caps swinging antiphase (push-pull). A series resonant DC-block cap blocks the kV bias, passes the low-frequency stepping drive at minimum impedance, and stays a high-Z spectator at f₀. The Q/turns/voltage budget yields the **closed-form, frequency- and turns-independent ampere-turn limit** `N·I = (V_rating − V_bias)·√(C·l_gap/(μ₀·A))`. A top-view projection shows the sectored disc, the 6 rotor poles, and the 12 C-EMs with polarity. **Anchors (worked design point, bias 12 kV / rating 20 kV — the self-test point):** PRF 300 Hz; alt-stroke L = 2.56 H, Z₀ = 2411 Ω, N ≈ 3190, **N·I ≈ 10 585 A-t** — identical at per-stroke drive (300 Hz, N ≈ 1595); energy ½·440 nF·(20 kV)² = 88 J/coil; per-group cap = 6·C = 2.64 µF. With the **default cascade** (`vhvKV = 20`, rating 30, headroom 10 kV) the on-load value is **N·I ≈ 13 230 A-t**.

### Block T — built-in transfer caps Ca/Cb (v0.1) `[OC] / [IR]`
A **solid annular bus ring** (full area, **no keptFrac**) buses the otherwise-unconnected stator sectors *and* serves as the lower Ca/Cb plate; Mylar + an upper electrode complete the cap (Ca on the top face, Cb on the bottom). It consumes C-I's `rActiveInner/rActiveOuter`. Inverse (Ca → width) and forward (width → Ca) modes; inside placement default (inner edge pinned, grows outward, ≤ `rActiveOuter`), outside toggle. Reports band-max Ca, dielectric field, and ½·C·V² energy. The copper–Mylar–copper stack renders on the back of each stator plate in the M cross-section, lifted on a tunable axial bracket. **Anchors (1 mm Mylar, εᵣ 3.2, inside):** Ca 4/7/11 nF → 129/191/258 mm width; band-max 12.3 nF; field 20 kV / 1 mm = 20 kV/mm; energy 7 nF · 20 kV = 1.4 J; round-trip exact. With the default `tcFromCmax` link on, Ca = Cb = 1.5·Cmax ≈ 6.29 nF (width ≈ 178 mm).

### Design-flow inheritance + parameter-set presets `[OC] / [IR]`
Five default-on, overridable couplings cascade the design primaries to the slaved inputs in one acyclic pass (`cascadeState`) before any producer runs: `vhvLink` (HV void = `vhvKV/vhvEkVmm`, Block-T design V, motor bias ← `vhvKV`), `quadLink` (`pquadfoot = 2·demQuadConeRmm`), `demRpmLink` (motor RPM ← master `rrpm`), `demEvLink` (`demEventsPerRev = ⌈pnsec/2⌉`, making the R and D PRF identical by construction), and `tcFromCmax` (`Ca = Cb = tcRatio·Cmax`, driving the solver). Presets are JSON of **primaries + toggles + an `expect` block**; "Load parameter set" reads a self-documenting file (`FileReader`), validates (unknown/out-of-range keys warned and skipped — never applied silently), applies, runs the cascade, **checks each `expect` within tolerance**, updates the hash, and shows a notes panel; "Save current as preset" exports a scaffold. **No magnitude is hard-coded in prose** — `presetExpectGetters` defines the checkable outputs and the preset asserts them. The shipped **R1 baseline** (`presets/R1-baseline.json`) verifies on load: CmaxNF 4.19, CaNF 6.29, prfHz 300, pvoidMm 20, f0kHz 326 — all within tolerance.

### Block S — firing sequence & clocking (read-only sink) `[OC] / [IR] / [RH]`
`traceDoubler4` is a read-only **sibling** of `solveDoubler4` — the identical loop, recording the per-phase node-voltage trace and reusing the frozen `chargesFromVoltages`/`solvePhase`; it carries the running rescale so the consumer reconstructs `Vtrue = V/scale`. A self-test asserts `traceDoubler4.z ≡ solveDoubler4.z` (z = 1.2033 at the device point) within 1e-9. Four full-width canvas panels: `seq-v` (gap voltages with the convex 1/C within-stroke rise, peaks growing ×z/cycle), `seq-logic` (SG3/SG2/SG4/SG1 conduction with stroke bands), `seq-tank` (impulse-kicked damped 5–6 ring whose envelope grows with the pump, plus a resolved-carrier inset), and `seq-clock` (an enlarged polar map: `groups = ⌈Nsec/2⌉`, `pitch = 720/Nsec°`, reacting to geometry `pnsec`). A single timing source `machinePRF() = ⌈pnsec/2⌉·rrpm/60` feeds every panel; a self-test asserts it equals `resonatorCore.prf` and `demMotor.prf`. The tank carrier/decay default to the live Block-R `f₀`/`Q` (`sf0`/`sq0` = 0 ⇒ auto), so no f₀ figure is hard-coded. **[RH]** Caption discipline: only the 5–6 curve is bench-measurable (nodes 1–4 sit on the free counter-rotating stator); the rest is design guidance. The conduction-window/follower-lag angles are display placeholders (open forks F-S1/F-S4).

### Commutator render `[IR]`
A render/consumer visualisation of the frozen switching design in `docs/commutator-design.md` (the physical realisation of diodes `D1–D4` as a rotary, mechanically-timed electrostatic commutator). Two coordinated views: an **axial companion** (new face-on panel — rotor disc + `Nsec` sectors, 6 floating bars at the transfer radius with ball ends, the SG3/SG4 stator sets with the **30° offset drawn**, firing windows + favourable-half shading, a live `kphi` rotor-angle slider) and **front-view overlay** additions in the cross-section (mirrored top/bottom bar sets, stator electrodes across two series spark-gaps per bar, cross-ecliptic sink routing). A `drawLegend` helper encodes **colour = electrical frame** (rotor / stator / **floating bars** / rail) and **hatch = material**; the floating bars get their own colour — the key distinction. Pure `commutatorGeom(state)`: bar count `⌈Nsec/2⌉`, the 30° offset resident in the stator sets with the bar sets axially aligned, transfer-circle radius `ktransrad` (outboard of `rActiveOuter`). Render-only — `k*` inputs have no solver coupling; the spark-transfer `z_spark` model is left open per the design doc §9.

---

## 4. Corrections made openly (reviewer attention)

Per the "correct openly" convention each of these is recorded in `CHANGELOG.md` with its reason. They are the points where the implementation **departs from, or corrects, a brief** and therefore most warrant review.

- **C1 — C-I sectored area.** Original code used the full disc; corrected to the annulus *outside* the ring (the inner disc is the hub/ring, not free sectors), removing a ~2 % overcount. `[review finding]`
- **C2 — Block M working unit.** Briefs specified cm/in; the implementation uses **mm** as the realistic base for these component sizes (void 50, disc 1000). `[IR, recorded]`
- **C3 — Block R inductance / f₀.** The brief quoted `L ≈ 235 µH / f₀ ≈ 238 kHz` from a cruder cylindrical estimate; the validated conical loop-stack (cross-checked against Nagaoka) gives `L ≈ 131 µH` for the capillary self-test config and `f₀ ≈ 326 kHz` at the R1 baseline. The validated values are used and self-tested/asserted; the stale figure was retired entirely by moving the magnitude into the R1 preset's `expect`. `[corrected openly]`
- **C4 — C-I ↔ M coupling.** A user-directed hard link (plate ⌀ → disc ⌀, ring-out ⌀ → hub ⌀) supersedes the briefs' warn-only stance; the DIN key assembly becomes a boundary condition with a new hard guard. `[IR, user-directed]`
- **C5 — C-I v0.2 active-band guard.** The instruction's area formula `max(0, rOut² − rIn²)` is insufficient: once `rActiveOuter` goes **negative** its square exceeds `rActiveInner²` and reports a *spurious* pumping area. Replaced with a band-**width** guard (`rActiveOuter > rActiveInner`). **This bug was caught by the v0.2 collapse self-test** — evidence the battery is doing its job. `[OC correction of instruction]`
- **C6 — Block D top-view.** A user-directed axial top-view projection (sectors + 6 rotor poles + 12 C-EMs in one plane) supersedes the brief's §8 side-view ring. `[IR, user-directed]`
- **C7 — `demCapRatingKV` default 20 → 30 kV.** With the design-flow `vhvLink` on, `demBiasKV ← vhvKV = 20`; leaving the rating at 20 would give zero AC headroom and a spurious "no torque / over-voltage" Block-D warning on first load. Raising the (free) rating default to 30 lands the default cascade coherently (10 kV headroom). `[IR, recorded]`
- **C8 — `tcBracketMm` repurposed (radial → axial); radial pin renamed `tcInnerPinMm`.** The cross-section render brief defines `tcBracketMm` as the **axial** Ca/Cb standoff, but Block-T v0.1 already used that id for the **radial** inner-pin clearance. The radial input was renamed to `tcInnerPinMm` (unchanged 15 mm default/behaviour) to free `tcBracketMm` for the brief's axial meaning, honouring its explicit "do not conflate" instruction. `[IR, recorded]`
- **C9 — Cross-section motor geometry (xsec v0.2.2).** The §5e rotor pole was sized from a free radius and overflowed the rim band ("ate the rotor"); it is now a band-sized square derived from `[rActiveOuter, rRotorOuter]`, the C-EM winding moved to the vertical spine, and the two ±x C-EMs made exact mirrors. Factored into a pure helper (`cemMotorGeom`) so the six new geometry self-tests run without a DOM. `[IR render]`

---

## 5. Verification status

**All 67 deterministic self-tests pass** on commit `7796b72` (engine badge: *verified*). The battery is the regression gate: any change that breaks a modelled relationship flips the badge red on load. The tests are pure functions of the producer code (no DOM), so they reproduce headlessly.

| Group | Count | Coverage |
|---|---|---|
| Host solver | 5 | no-swing, device, narrow, wide, C1↔C2 swap symmetry |
| Block C-I | 8 | dry-air εᵣ, fixed-geom Cmax; v0.2: A_active, A_full, band radii, **C_R invariance under squeeze**, pump ∝ active area, collapse guard |
| Block M | 3 | hubDia, void-partition identity, DIN key length |
| Block R | 6 | AGM elliptic, C_R, validated L, tube ≡ rod HF identity, AWG OD, PRF |
| Block D | 7 | resonance round-trip, Z₀ identity, **N·I invariance**, over-V flag, 88 J energy, N-S-N-S parity, per-group cap |
| Block T | 7 | inverse widths, round-trip, band-max + overrun, Ca = Cb, field, inside > outside, energy |
| Design-flow + presets | 8 | export→load round-trip, partial load, **R1 expect-pass**, corrupt-expect-surfaces-✗, inheritance-overwrite warn, unknown-key warn, bad-JSON safety, flow identities + idempotent cascade |
| Cross-section render | 11 | bracket px→mm, pole-in-band, motor gap from Block D, rim-clamp straddle, legend coverage; **v0.2.2:** C-EM mirror symmetry, no-inboard-overrun, spine-clears-disc, pole-fills-band, two-equal-axial-gaps, coil-on-spine |
| Block S firing sequence | 6 | **tracer ≡ frozen solver**, SG3-peak growth ≈ z, tank kicks monotone, clocking groups/pitch, **PRF single-source ≡ R ≡ D**, **firing pairing ≡ solver** {SG1,SG3}/{SG2,SG4} |
| Commutator render | 4 | SG3↔SG4 offset = sector pitch, bar sets axially aligned, no cross-bridge, transfer radius outboard |

The standout rows are the **invariance / decoupling** guards — they prove a *relationship*, not just a point value: C-I "C_R invariant under squeeze" (the squeeze never reaches the resonator), D "N·I invariance" (the ampere-turn limit is genuinely frequency-independent, not an accident of one operating point), S "tracer ≡ frozen solver" and "PRF single-source ≡ R ≡ D" (the visualiser and the timing sources cannot drift from the engine).

**Verification method.** In-browser self-test on load, plus headless re-runs of `runSelfTest()` and the producer functions under Node with a stubbed DOM (the source of every anchor in this report). **Reviewer to-do:** open the page once to confirm the canvases render without console errors — the numeric engine is independently verified, but the *drawings* (cross-section motor clamp, top-view, the four Block-S panels) are best confirmed visually.

---

## 6. Scope boundaries — what the tool does NOT assert

Deliberately out of scope (deferred; **not** modelled, **not** claimed):

- **Dielectric breakdown / safe-voltage limits** across any gap. HV *geometry* (clearance, creepage, dielectric field) is reported; a pass/fail safe-voltage verdict is not. Block D raises a derated HV-void warning (1 kV/mm) and Block T a field warning (>40 / >100 kV/mm) as **flags, not guarantees**.
- **Conduction / leakage / loss** in the pump; **fringing-field** corrections (a heuristic warning fires when the gap exceeds ~10 % of the smallest in-plane feature, but C is the ideal parallel-plate value).
- **Rotational inertia, mass, balance, bearings, seats** (mechanical detail); **leg-height / bracket structural design** in Block T (only the radial placement, the axial standoff, and the Mylar thickness are real there — the rest is render-schematic).
- **Mica tanδ and spark-gap loss** in Block R (Q is a copper-only *upper bound*; the real loaded Q is far lower).
- **Torque vs. stator drag / inertia** in Block D (ampere-turns feed a future torque estimate once rotor-pole geometry is fixed).
- **The Block-S forks:** SG breakdown clamp / saturation (F-S1), real series-LC tank coupling (F-S2), absolute kV from the operating point (F-S3, the y-axes stay normalised), and conduction-window / follower-lag **angles** from a switch-timing sim (F-S4). The Block-S firing/clocking panels are presentational design guidance, not a timing simulation.

---

## 7. Open questions a reviewer may want to challenge

1. **Drive-frequency mapping (Block D).** Alt-stroke (PRF/2) vs per-stroke (PRF) changes the coil L (hence N) by 4×; the ampere-turn limit is invariant but the *winding* is not. The mapping must be confirmed against the actual stroke→cap pattern before winding.
2. **Transfer-cap scale wiring (Block T → solver).** Block T produces nF-scale Ca/Cb; the host's manual `ca/cb` range was pF-scale (≤ 500). The `tcDrive`/`tcFromCmax` hand-off raises the field max to admit nF values rather than silently clamping. Confirm nF-scale transfer caps are intended for the *physical* (plate-driven, thousands-of-pF) regime, not the abstract demo presets.
3. **Decoupling premise (C-I v0.2).** C_R keeps the full rotor face on the assumption the stator clearances are purely a *stator* concern and the rotor↔rotor through-mica path is unaffected. This is the hinge of the squeeze/decoupling split.
4. **Reluctance-rotor polarity premise (Block D).** The N-S-N-S map and the torque rest on the two transfer caps being genuinely antiphase (push-pull). The tool asserts the parity but cannot prove the antiphase drive — that is a system-level claim.
5. **Resonator alignment premise (Block R).** A real through-mica C_R assumes the rotor electrodes fully align (antiphase supplied by the stator offset). Partial alignment shifts C_R and f₀.
6. **Default operating-point coherence.** The default cascade (vhvKV 20, rating 30, Ca = 1.5·Cmax) was tuned so all guards land green on load; confirm it represents an intended design point, not just a green-light convenience.

---

## 8. How to reproduce / review

1. **Run it:** open `index.html` in any modern browser (offline is fine). Confirm the header badge reads **"engine verified"** and the self-test table (under *Topology & diode schedule*) shows all 67 rows passing.
2. **Inspect the invariant:** confirm the five frozen primitives are unchanged from the validated host engine; all blocks are upstream producers. (`git log -p` on `index.html` filtered to those functions shows no edits.)
3. **Re-run the battery headlessly:** extract the `<script>` body, stub a minimal DOM, call `runSelfTest()`, assert `.ok === true` and `rows + plateRows` count = 67. This is how every anchor in this report was produced.
4. **Load the R1 preset:** "Load parameter set" → `presets/R1-baseline.json`; confirm the five `expect` chips report ✓ within tolerance.
5. **Probe the corrections (§4) and the open questions (§7)** — those are where judgment, not arithmetic, is required.
6. **Share state:** "copy share-url" captures any configuration; the URL hash is the full, reproducible parameter set.

---

## 9. Provenance and reference inputs

- **In-repo briefs (authoritative for their internals):** `docs/brief-blockC1-geometry-to-rotorcap.md`, `…blockM…`, `…blockR…`, `…blockD…`, `…blockS…`, `docs/commutator-design.md` (the frozen switching design — physical realisation of D1–D4), and the system context `docs/doc-circuit-topology-resonances-materials.md`. The Block-T, design-flow, and cross-section briefs were external working documents; their content and every deviation are recorded in `CHANGELOG.md`.
- **Conventions and audit trail:** `CONVENTIONS.md` (tier tags, symbol hygiene, block namespaces, the producer/consumer rule) and `CHANGELOG.md` (every change with its reason).
- **Reference prototypes (committed, not served):** `reference/SectoredDiscCalculator.jsx` (C-I area math) and the Block-S Python mirror/plot prototypes `reference/doubler_core.py`, `reference/sg_sequence_from_solver.py`, `reference/clocking_map.py`.
- **Shipped preset:** `presets/R1-baseline.json` (the worked baseline; the only place its magnitudes live, asserted via `expect`).
- **Companion:** `docs/report-tool-functioning.md` (functional walk-through).

*All physics mainstream; all modelling choices tier-tagged; all corrections logged. The tool is a verified sizing / exploration calculator, not a hardware-validated simulator.*
