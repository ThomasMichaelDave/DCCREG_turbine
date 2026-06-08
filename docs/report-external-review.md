# External Review Report — Rotary-Varicap Bennet-Doubler Design Calculator

**Artifact under review:** `index.html` — a single, self-contained web page (no build, no server, no dependencies, no network, no `localStorage`).
**Build stamp:** `C-I v0.2 · T v0.1 · flow+presets v0.2 · xsec v0.2.2 · S v0.1` (shown in the page header).
**Companion document:** `docs/report-tool-functioning.md` (deeper functional walk-through of the host solver + Blocks C-I/M; this report supersedes its block coverage and adds Blocks R, D, T and the C-I v0.2 correction).
**Purpose of this document:** give an external reviewer everything needed to judge the tool's correctness, scope, and honesty — what it claims, how those claims are validated, what was deliberately corrected, and what is explicitly out of scope.

---

## 0. Provenance firewall (read first)

The **working methodology** — epistemic tier tags, a `CHANGELOG.md` audit trail, symbol-hygiene rules, and producer/consumer discipline — is adapted from the "DCCREG programme conventions."

**The physics and mathematics are entirely mainstream.** Specifically: parallel-plate capacitance, a rotary variable capacitor, the cross-coupled Bennet charge doubler, standard solid-mechanics geometry, the Smith–Weintraub air-refractivity relation, the Buck (1981) saturation-vapour-pressure correlation, DIN 6885 parallel-key sizing, circular-loop self/mutual inductance via complete elliptic integrals (AGM), skin effect, LC resonance, series-resonant DC-block coupling, and the salient-pole reluctance-torque relation `T = ½ i² dL/dθ`. **No proprietary or unconventional theory is used or required.** Every substantive claim in code and docs carries a tier tag so a reader can separate standard results from modelling choices:

- **[OC] Operational Core** — standard derivable physics/math; true independent of this project.
- **[IR] Interpretive Reading** — a modelling/engineering choice; internally consistent, chosen.
- **[RH] Resonance/Heuristic** — suggestive framing, not load-bearing.

---

## 1. What the tool is

An interactive design calculator for one electromechanical device: a **rotary variable capacitor that drives a symmetric 4-node Bennet voltage doubler**, with the surrounding mechanical core, central resonator, spin-up motor, and built-in transfer capacitors all modelled in the same page. It connects layers normally treated separately, so a designer goes from *physical dimensions* to a *predicted electrical pumping ratio* plus mechanical, resonant, motor, and transfer-cap characterisations in one view.

It is an **exploration / sizing tool**, not a manufacturing release and **not a hardware-validated simulator**. It answers: "for this geometry, gap, dielectric, and a few electrical inputs, does the doubler pump (z > 1), how strongly, with what margin — and is the implied machine physically coherent?"

---

## 2. Architecture and the central safety property

- **Single global `state`** holds every parameter. Numeric inputs are declared once in a `FIELDS` table (`id, default, min, max, step`) and auto-wired to a slider + number box; non-numeric controls (enums, checkboxes) are handled explicitly.
- **Reproducibility:** the complete parameter set serialises into the URL hash on every change ("copy share-url"). Opening that URL reproduces the exact state. No server, no database.
- **Producer / consumer discipline (the load-bearing invariant).** The electrical engine `solveDoubler4(...)` is the **consumer** and is **never edited by feature work**. Every other block is a **producer** that computes geometry/physics and, at most, writes the solver's *input* state at the call site:

| Block | Role | Touches the solver? |
|---|---|---|
| Host `solveDoubler4` | switched-capacitor network solver → pumping ratio `z` | — (consumer, frozen) |
| **C-I** plate geometry | geometry+gap+dielectric → rotor `Cmin/Cmax` | drives rotor caps (pre-step) |
| **M** mechanical core | quadricone/shaft/void/disc, DIN keys, HV clearances, guards | no — readouts + cross-section only |
| **R** central resonator | conical-coil `L ∥ C_R` tank, f₀/Q/ringdown | no — readouts + cross-section only |
| **D** distributed EM motor | 12-C-EM reluctance spin-up, Q/turns/voltage budget | no — readouts + top-view only |
| **T** transfer caps | bus-ring Ca/Cb geometry → capacitance | optional `tcDrive` toggle writes `ca`/`cb` at call site |
| **Design flow + presets** | one-pass cascade of primaries → slaved inputs; JSON preset load/save | only via the documented `tcFromCmax`/`tcDrive` call-site wiring |
| **S** firing sequence | read-only `traceDoubler4` trace → 4 firing/clocking panels | no — pure sink, never writes solver state |

A reviewer can verify the invariant by confirming `solveDoubler4` and `solvePhase` are byte-identical to the validated host engine; all feature work is upstream of them.

- **Self-test gate.** The page runs a fixed battery of deterministic checks **on load**; an "engine verified" badge turns green only if **all** pass, and an expandable table shows every row. See §5.

---

## 3. Block-by-block technical summary (with validated anchors)

### Host — symmetric 4-node Bennet doubler `[OC]`
Cross-coupled regenerative topology (C1:1↔0, C2:4↔0 variable; Ca:1↔2, Cb:3↔4 fixed; Cpar per node; diodes D1 2→0, D2 3→0, D3 1→3, D4 4→2). The solver brute-searches all 16 diode on/off states per phase, keeps those consistent with off-diode bias constraints, takes the one maximising |V₁|+|V₄|, iterates two-phase cycles, and returns the median asymptotic per-cycle ratio `z`. **Anchors:** no-swing → z = 1.000; device (160–1000 pF) → z ≈ 1.20; wide (100–2000) → z ≈ 1.44; C1↔C2 swap symmetric.

### Block C-I — plate geometry → rotor capacitance (v0.2) `[OC] / [IR]`
Sectored disc (alternating kept sectors) + optional conductive central ring set a finite Cmin floor. Dielectric is vacuum, **live moist air** (Smith–Weintraub + Buck), or fixed-nominal mica/Kapton. `C = ε₀εᵣA/g`.
**v0.2 correction (the active-overlap squeeze):** the swinging rotor↔stator overlap is **not** the full rotor face — the counter-rotating stator cannot reach the central HV tank (inner void) nor overlap the 6 rim steel cores (outer quad band). `plateGeom` now returns **two** areas: `Ametal_full` (full face) and `Ametal_active` (band `[ro+pvoid, plateR−pbus−(pquadfoot+pquadclr)]`). **The pump (C1/C2) uses the squeezed area; the resonator C_R uses the full face** — they are decoupled. **Anchors (defaults):** `A_active ≈ 0.2211 m²`, `A_full ≈ 0.3839 m²` (squeeze ≈ 0.576), active band 95…387 mm; dry-air εᵣ(0 °C, 1013 hPa, 0%) ≈ 1.000576.

### Block M — rotor mechanical core `[OC] / [IR]`
45° "quadricone" pair + stub shafts + spherical void + dielectric disc/septum. Hub from DIN 6885 key sizing (or from the C-I ring when coupled), spherical-cap/belt/bore volumes, four hard feasibility guards (collar / void-seat / wall / key-fit) + a keyway-collar soft guard, HV clearance/creepage geometry, and a live, dimensioned, scale cross-section. **Anchors:** hubDia(void 50, shaft 35, discH 0) = 197 mm; void partition 2·cap+belt = sphere; `keyLenFor(35)` → DIN 56. Working unit is **mm** (see correction C2).

### Block R — central resonator `[OC]`
`C_R ∥ L` tank: two conical coils (series, aiding) wound on the quadricones, and the through-mica inter-electrode capacitor. Inductance via an exact conical loop-stack (HF self + Maxwell mutual over all turn pairs, elliptic integrals by AGM, decimation flagged); Medhurst self-capacitance and coil self-resonance; f₀, f_d, Z₀, copper-limited Q (upper bound), ringdown τ, skin δ; RPM-driven PRF and the ringdown-vs-build-up regime. **Anchors:** `ellipKE(0)` → K=E=π/2; capillary `C_R ≈ 1.91 nF`, `L ≈ 131 µH`; tube OD3/ID1 ≡ rod OD3 at HF; `awgToCond(20)` ≈ 0.812 mm; PRF(N12, 3000 rpm) = 300 Hz.

### Block D — distributed-electromagnet spin-up motor `[OC] / [IR]`
12 stator C-electromagnets in two interleaved groups of 6 (odd→A on cap C3, even→B on C4), uniform winding; the N-S-N-S ring is a *consequence* of the two transfer caps swinging antiphase (push-pull). Series resonant DC-block cap. The Q/turns/voltage budget yields the **closed-form, frequency- and turns-independent ampere-turn limit** `N·I = (V_rating − V_bias)·√(C·l_gap/(μ₀·A))`. A top-view projection shows the sectored disc, 6 rotor poles, and 12 C-EMs with polarity. **Anchors (worked design point):** PRF 300 Hz; alt-stroke L ≈ 2.56 H, Z₀ ≈ 2411 Ω, N ≈ 3190, **N·I ≈ 10 585 A-t** — identical at per-stroke (300 Hz, N ≈ 1595); energy ½·440 nF·(20 kV)² = 88 J/coil; per-group cap = 6·C = 2.64 µF.

### Block T — built-in transfer caps Ca/Cb (v0.1) `[OC] / [IR]`
A **solid annular bus ring** (full area, no keptFrac) buses the otherwise-unconnected stator sectors *and* is the lower Ca/Cb plate; Mylar + upper electrode complete the cap (Ca top face, Cb bottom). Consumes C-I's `rActiveInner/rActiveOuter`. Inverse (Ca→width) and forward (width→Ca); inside placement default (grows outward), outside toggle. Reports band-max Ca, dielectric field, energy. The copper–Mylar–copper stack renders on the back of each stator plate in the M cross-section. **Anchors (1 mm Mylar, εᵣ 3.2, inside):** Ca 4/7/11 nF → 129/191/258 mm; band-max ≈ 12.3 nF; field 20 kV/1 mm = 20 kV/mm; energy 7 nF·20 kV ≈ 1.4 J; round-trip exact.

---

## 4. Corrections made openly (reviewer attention)

Per the "correct openly" convention, each of these is recorded in `CHANGELOG.md` with its reason. They are the points where the implementation **departs from, or corrects, a brief** and therefore most warrant review:

- **C1 — C-I sectored area.** Original code used the full disc; corrected to the annulus *outside* the ring (the inner disc is the hub/ring, not free sectors), removing a ~2 % overcount. `[review finding]`
- **C2 — Block M working unit.** Briefs specified cm/in; implementation uses **mm** as the realistic base for these component sizes (void 50, disc 1000). `[IR, recorded]`
- **C3 — Block R inductance.** The brief quoted `L ≈ 235 µH / f₀ ≈ 238 kHz` from a cruder cylindrical estimate; the validated conical loop-stack (cross-checked against Nagaoka) gives `L ≈ 131 µH / f₀ ≈ 316 kHz`. The validated value is used and self-tested. `[corrected openly]`
- **C4 — C-I↔M coupling.** User-directed hard link (plate ⌀→disc ⌀, ring-out ⌀→hub ⌀) supersedes the briefs' warn-only stance; the DIN key assembly becomes a boundary condition with a new hard guard. `[IR, user-directed]`
- **C5 — C-I v0.2 active-band guard.** The instruction's area formula `max(0, rOut² − rIn²)` is insufficient: once `rActiveOuter` goes **negative** its square exceeds `rActiveInner²` and reports a *spurious* pumping area. Replaced with a band-**width** guard (`rActiveOuter > rActiveInner`). **This bug was caught by the v0.2 collapse self-test**, which is itself the evidence the test battery is doing its job. `[OC correction of instruction]`
- **C6 — Block D top-view.** A user-directed axial top-view projection (sectors + 6 rotor poles + 12 C-EMs in one plane) supersedes the brief's §8 side-view ring. `[IR, user-directed]`
- **C7 — `demCapRatingKV` default 20 → 30 kV.** With the design-flow `vhvLink` on, `demBiasKV ← vhvKV = 20`; leaving the rating at 20 would give zero AC headroom and a spurious "no torque / over-voltage" Block-D warning on first load. Raising the (free) rating default to 30 lands the default cascade coherently. `[IR, recorded]`
- **C8 — `tcBracketMm` repurposed (radial → axial); radial pin renamed `tcInnerPinMm`.** The cross-section render brief defines `tcBracketMm` as the **axial** Ca/Cb standoff, but Block-T v0.1 already used that id for the **radial** inner-pin clearance. The radial input was renamed to `tcInnerPinMm` (unchanged 15 mm default/behaviour) to free `tcBracketMm` for the brief's axial meaning, honouring its explicit "do not conflate" instruction. `[IR, recorded]`

---

## 5. Verification status

**All 62 deterministic self-tests pass** (engine badge: *verified*). The battery is the regression gate: any change that breaks a modelled relationship flips the badge red on load. The tests are pure functions of the producer code (no DOM), so they are reproducible headlessly.

| Group | Count | Coverage |
|---|---|---|
| Host solver | 5 | no-swing, device, narrow, wide, C1↔C2 swap symmetry |
| Block C-I | 2 + 6 | dry-air εᵣ, fixed-geom Cmax; v0.2: A_active, A_full, band radii, **C_R invariance under squeeze**, pump ∝ active area, collapse guard |
| Block M | 3 | hubDia, void partition identity, DIN key length |
| Block R | 6 | AGM elliptic, C_R, validated L, tube≡rod HF identity, AWG OD, PRF |
| Block D | 7 | resonance round-trip, Z₀ identity, **N·I invariance**, over-V flag, 88 J energy, N-S-N-S parity, per-group cap |
| Block T | 7 | inverse widths, round-trip, band-max+overrun, Ca=Cb, field, inside>outside, energy |
| Design flow + presets | 8 | export→load round-trip, partial load, **R1 expect-pass**, corrupt-expect-surfaces-✗, inheritance-overwrite warn, unknown-key warn, bad-JSON safety, flow identities + idempotent cascade |
| Cross-section render | 11 | bracket px→mm, pole-in-band + band width, motor gap from Block D, rim-clamp straddle, legend coverage; **v0.2.2 motor:** C-EM mirror symmetry, no-inboard-overrun, spine-clears-disc, pole-fills-band, two-equal-axial-gaps, coil-on-spine |
| Block S firing sequence | 5 | tracer≡frozen solver, SG3-peak growth≈z, tank kicks monotone, clocking groups/pitch, PRF single-source≡R≡D |

The standout tests are the **decoupling/invariance** ones — C-I "C_R invariant under squeeze" proves the squeeze never reaches the resonator, and D "N·I invariance" proves the ampere-turn limit is genuinely frequency-independent (not an algebraic accident of one operating point).

**Verification method used during development:** in-browser self-test on load, plus headless re-runs of `runSelfTest()` under Node with a stubbed DOM. **Not yet done:** a live visual confirmation of the canvas renders in a browser (no headless browser was available in the build environment); a reviewer should open the page once to confirm the cross-section and top-view drawings render without console errors — the numeric engine is independently verified.

---

## 6. Scope boundaries — what the tool does NOT assert

Deliberately out of scope (deferred; **not** modelled, **not** claimed):

- **Dielectric breakdown / safe-voltage limits** across any gap. HV *geometry* (clearance, creepage, dielectric field) is reported; a pass/fail safe-voltage verdict is not. Block D raises a derated HV-void warning (1 kV/mm) and Block T a field warning (>40/>100 kV/mm) as **flags, not guarantees**.
- **Conduction / leakage / loss** in the pump; **fringing-field** corrections (a heuristic warning fires when the gap exceeds ~10 % of the smallest in-plane feature, but C is the ideal parallel-plate value).
- **Rotational inertia, mass, balance, bearings, seats** (mechanical detail); **leg-height / bracket structural design** in Block T (only radial placement and Mylar thickness are real there).
- **Mica tanδ and spark-gap loss** in Block R (Q is a copper-only *upper bound*).
- **Torque vs. stator drag/inertia** in Block D (ampere-turns feed a future torque estimate once rotor-pole geometry is fixed).
- **Coil self-resonance margin, core loss, and the stroke→cap drive-frequency mapping** (PRF vs PRF/2) for Block D — flagged as open forks to confirm in the system simulation before winding.

---

## 7. Open questions a reviewer may want to challenge

1. **Drive-frequency mapping (Block D §4.4).** alt-stroke (PRF/2) vs per-stroke (PRF) changes the coil L (hence N) by 4×; the ampere-turn limit is invariant but the *winding* is not. The mapping must be confirmed against the actual stroke→cap pattern.
2. **Transfer-cap scale wiring (Block T → solver).** Block T produces nF-scale Ca/Cb; the host's manual `ca/cb` range was pF-scale (≤500). The `tcDrive` hand-off raises the field max to admit nF values rather than silently clamping. Reviewers should confirm nF-scale transfer caps are intended for the *physical* (plate-driven, thousands-of-pF) operating regime, not the abstract demo presets.
3. **Decoupling premise (C-I v0.2).** C_R keeps the full rotor face on the assumption the stator clearances are purely a *stator* concern and the rotor↔rotor through-mica path is unaffected. This is the hinge of the squeeze/decoupling split — worth an independent sanity check.
4. **Reluctance-rotor polarity premise (Block D §2).** The entire N-S-N-S map and torque rest on the two transfer caps being genuinely antiphase (push-pull). If the topology ever made them in-phase the pattern collapses; the tool asserts the parity but cannot prove the antiphase drive — that is a system-level claim.
5. **Resonator alignment premise (Block R).** A real through-mica C_R assumes the rotor electrodes fully align (antiphase supplied by stator offset). If alignment is partial, C_R and f₀ shift.

---

## 8. How to reproduce / review

1. **Run it:** open `index.html` in any modern browser (offline is fine). Confirm the header badge reads **"engine verified"** and the self-test table (under *Topology & diode schedule*) shows all rows passing.
2. **Inspect the invariant:** confirm `solveDoubler4` / `solvePhase` are unchanged from the validated host engine; all blocks are upstream producers.
3. **Re-run the battery headlessly** (optional): extract the `<script>` body, stub a minimal DOM, call `runSelfTest()`, assert `.ok === true`. (This is how the 62/62 result in §5 was produced.)
4. **Probe the corrections (§4)** and the **open questions (§7)** — those are where judgment, not arithmetic, is required.
5. **Share state:** use "copy share-url" to capture any configuration; the URL hash is the full, reproducible parameter set.

---

## 9. Provenance and reference inputs

- Companion functional report: `docs/report-tool-functioning.md`.
- Block briefs: `docs/brief-blockC1-geometry-to-rotorcap.md`, `…blockM…`, `…blockR…`, `…blockD…`; system context `docs/doc-circuit-topology-resonances-materials.md`; Block T brief and the C-I active-overlap instruction (attached working documents).
- Conventions and audit trail: `CONVENTIONS.md` (symbol hygiene, block namespaces, producer/consumer rule), `CHANGELOG.md` (every change with its reason).
- Reference port: `reference/SectoredDiscCalculator.jsx` (the C-I area math source).

*All physics mainstream; all modelling choices tier-tagged; all corrections logged. The tool is a verified sizing/exploration calculator, not a hardware-validated simulator.*
