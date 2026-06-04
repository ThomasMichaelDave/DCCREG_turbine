# Functional Report — Variable-Capacitor → Symmetric Bennet Doubler Design Tool

**Artifact:** `index.html` (single self-contained web page; no build, no server, no dependencies)
**Scope of this report:** how the tool works — its purpose, models, data flow, interface, verification, and limitations.
**Status:** working and self-tested. Host doubler + Block C-I (plate capacitance) + Block M (rotor mechanical core), with geometric coupling between the two geometry blocks.

> **Provenance / firewall.** The *working methodology* (epistemic tier tags, a changelog audit trail, symbol-hygiene rules, producer/consumer discipline) is adapted from the "DCCREG programme conventions." **The physics and mathematics in the tool are entirely mainstream** — parallel-plate capacitance, a rotary variable capacitor, the Bennet charge doubler, standard solid-mechanics geometry, the Smith–Weintraub air-refractivity relation, the Buck (1981) vapour-pressure correlation, and DIN 6885 key sizing. **No proprietary or unconventional theory is used or required.** Every substantive claim carries a tier tag (below) so a reader can separate standard results from modelling choices.

---

## 1. Executive summary

The tool is an interactive design calculator for a specific electromechanical device: a **rotary variable capacitor that drives a symmetric 4-node Bennet voltage doubler**. It links three layers that are normally treated separately:

1. **Electrical engine (host).** A switched-capacitor network solver that computes the asymptotic per-cycle voltage-gain ratio **z** of a cross-coupled 4-node Bennet doubler from the capacitor values.
2. **Electrical front end (Block C-I).** A parametric model of the rotor capacitor plate (sectored disc + central ring) that converts *geometry + gap + dielectric* into the rotor capacitance extremes **Cmin / Cmax**. These now **drive the rotor capacitors of the doubler automatically**.
3. **Mechanical core (Block M).** A parametric model of the rotor's structural body (a 45° "quadricone" pair, stub shafts, a central spherical void, and a dielectric disc/septum), with industry key sizing, feasibility guards, high-voltage clearance/creepage geometry, and a live scale cross-section drawing — now showing the fixed stator plates as well.

The two geometry blocks are **coupled**: the capacitor plate diameter sets the structural disc diameter, and the capacitor ring's outer diameter sets the mechanical hub/cone diameter. The single page therefore takes a designer from *physical dimensions* to a *predicted electrical pumping ratio* and a *mechanically-checked, dimensioned cross-section* in one view.

The page **self-tests on load**; an "engine verified" badge and an expandable table report a fixed set of deterministic checks. All checks currently pass.

---

## 2. Purpose and intended use

- **Primary question answered:** "For a given rotor-plate geometry, gap, dielectric, and a few stray/transfer capacitances, does the Bennet doubler pump (z > 1), how strongly, and how much margin is there — and is the implied mechanical core physically realisable?"
- **Audience:** a designer exploring the parameter space of this device. It is an **exploration / sizing tool**, not a manufacturing release or a hardware-validated simulator.
- **Out of scope (by design, see §11):** dielectric breakdown / safe-voltage limits, conduction and leakage losses, fringing-field corrections, rotational inertia / mass / balance, and bearing/seat detail. These are deferred to later work and are explicitly *not* asserted by the tool.

---

## 3. System architecture

- **Single file.** Everything (markup, CSS dark theme, and all JavaScript) lives in one `index.html`. It runs offline in any modern browser. There is **no build step, no network call, and no `localStorage`**.
- **State.** A single global `state` object holds every parameter. Numeric inputs are declared once in a `FIELDS` table (`id, default, min, max, step`) and auto-wired to a paired range slider + number box. Non-numeric controls (dielectric choice, toggles) are handled explicitly.
- **Shareable URL.** The complete parameter set is serialised into the page's URL hash on every change ("copy share-url"). Opening that URL reproduces the exact state — this is the reproducibility mechanism (no server, no database).
- **Producer / consumer discipline.** The electrical solver `solveDoubler4(...)` is the *consumer* and is never edited by feature work. The geometry blocks are *producers*:
  - **Block C-I** produces the four rotor-capacitance values consumed by the solver.
  - **Block M** is an **independent producer** of mechanical readouts and a drawing; it never writes electrical state and never calls the solver.
  This separation keeps the validated electrical engine isolated from front-end changes.
- **Recompute loop.** Any input change schedules a single debounced `recompute()` that (a) runs the Block C-I pre-step (geometry → rotor caps), (b) runs the Block M readouts + cross-section, (c) runs the doubler solver and updates all outputs and charts.

---

## 4. The device (physical picture)

A central **dielectric disc** carries a sectored capacitor **electrode on each face** (the two rotors, "C1" on top and "C2" on the bottom), mirrored across the disc mid-plane. Each electrode is a sectored annulus whose inner edge sits at the hub and whose outer edge is the plate/disc rim. A **fixed stator plate** faces each rotor electrode across a small **gap g** — this electrode↔stator gap is the working capacitor gap. As the rotor turns, the overlap between the sectored rotor electrode and the stator sweeps the capacitance between **Cmin** and **Cmax**.

Structurally, a **45° quadricone half** is bonded to each electrode (base at the hub, tapering outward to an apex), and a **stub shaft** (one per side — never a through-shaft, which would short the two rotors together) couples each apex to a bearing/drive. A **spherical void** at the assembly centre keeps the two electrodes apart; the disc fills the void's equatorial belt as a solid dielectric **septum** with a small central **bore**. Two sectored groups offset by one sector pitch realise the doubler's two **antiphase** rotors: when C1 is at Cmax, C2 is at Cmin.

This is the device the three computational blocks describe.

---

## 5. Electrical engine — symmetric 4-node Bennet doubler (host) **[OC]**

**Topology.** Four nodes above ground:
- Variable rotor capacitors: **C1** (node 1↔gnd) and **C2** (node 4↔gnd).
- Fixed transfer capacitors: **Ca** (1↔2) and **Cb** (3↔4).
- Stray capacitance **Cpar** from each node to ground.
- Four ideal diodes: D1 (2→0), D2 (3→0), D3 (1→3), D4 (4→2). The cross-diodes D3/D4 are the regenerative cross-couple that lets the 4-node device pump without relying on parasitic asymmetry.

**Solver method.** The engine runs the device as a two-phase-per-cycle switched-capacitor network:
1. Each phase conserves the per-node charge from the previous phase.
2. It brute-force searches all 16 diode on/off combinations; a combination is *consistent* if every "off" diode is reverse-biased (V_from ≤ V_to) and on-diodes short their endpoints. Each candidate is solved as a small linear system (Gaussian elimination over the conducting clusters).
3. Among consistent states it keeps the one maximising |V₁| + |V₄|.
4. It iterates 120 cycles, discards a burn-in, and returns the **median asymptotic ratio z = (|V₁|+|V₄|)ₙ / (|V₁|+|V₄|)ₙ₋₁**, rescaling to keep magnitudes bounded.

**Outputs derived from z:** growth ×/cycle, % per cycle, cycles-to-×10 and ×1000, a live C1↔C2 swap-symmetry check, and a **transfer-cap headroom** analysis (it sweeps Ca = Cb to find the z = 1 critical point and reports remaining margin or deficit). Two canvas charts plot z versus the rotor swing ratio and z versus Ca = Cb.

**Interpretation of z:** z > 1 = "PUMPING", z ≈ 1 = "KNIFE-EDGE", z < 1 = "STALLED".

---

## 6. Block C-I — plate geometry → rotor capacitance (electrical front end)

Converts the rotor-plate geometry into the capacitance extremes that drive the solver.

### 6.1 Capacitance model **[OC]**
Parallel-plate law in SI, scaled to picofarads:

```
C = ε0 · εr · A_overlap / g ,     ε0 = 8.8541878128×10⁻¹² F/m
```

The plate is a disc of `Nsec` equal sectors with alternating sectors kept as conductor (kept fraction = ⌈Nsec/2⌉ / Nsec — e.g. **12 sectors → 6 kept / 6 gaps**, 8 → 4/4), plus a central conductive ring (annulus). Rotation makes the sector overlap a triangular function of angle, so:

```
C_max = ε0·εr·(A_metal + χ_ring·A_ring) / g        (full sector overlap)
C_min = ε0·εr·(χ_ring·A_ring) / g                   (sectors over gaps)
swing ratio κ_C = C_max / C_min                      (= the host's r₁/r₂)
```

The ring is azimuthally symmetric, so it contributes a **rotation-independent capacitance floor** — it is the knob that keeps Cmin (and therefore the swing ratio) finite and tunable. Turning the ring off sends Cmin → 0 and κ_C → ∞ (flagged with a warning).

### 6.2 Dielectric model (→ εr)
| Dielectric | εr | Model |
|:--|:--|:--|
| Vacuum | 1 (exact) | constant **[OC]** |
| Air | ≈ 1.0006 | live function of T, pressure, humidity **[OC]** |
| Kapton | 3.4 (band 3.0–3.5) | fixed nominal **[IR]** |
| Mica | 5.4 (band 5.0–7.0) | fixed nominal **[IR]** |

The **moist-air** model is live (shown only when "Air" is selected):

```
εr_air = 1 + 2·N_air×10⁻⁶
N_air  = 77.6·P/T + 3.73×10⁵·p_v/T²          (Smith–Weintraub, N-units)
p_v    = (RH/100)·p_sat
p_sat  = 6.1121·exp[(18.678 − T_C/234.5)·T_C/(257.14 + T_C)]   (Buck 1981), hPa
```

with T in kelvin and pressures in hectopascals. (Honest note: air differs from vacuum by < 0.1 %; the model is included for completeness and correctness, not because the effect is large.)

A practicality note is surfaced when a **solid** dielectric is chosen, because a bonded film cannot in practice be rotated against both plates of a rotary capacitor — mica/Kapton are offered as fixed-gap "what-if" exploration. **[IR]**

### 6.3 Driving the solver (inheritance)
By default the rotor source is **"plate"**: the computed **Cmin/Cmax drive all four rotor fields** (C1 and C2 share the plate geometry — the symmetric design — linked by default). Those four inputs are then **read-only/disabled** and the panel is labelled "inherited from plate geometry." Only **transfer + stray (Ca, Cb, Cpar) remain user inputs**, because they cannot yet be estimated from geometry. A manual-override toggle remains for direct solver exploration. In plate mode the rotor-field maximum is raised to 10000 pF (realistic plate capacitances can exceed the manual 3000 pF range); values beyond that clamp with a visible warning.

---

## 7. Block M — rotor mechanical core

Models the structural body the electrode rides on. **It never feeds the solver** — it produces readouts, feasibility guards, and the cross-section.

### 7.1 Geometry **[OC]**
A 45° half-angle cone has height = base radius, so for cone base radius `R_c`:

```
quadricone volume   = (2/3)·π·R_c³                 (both cones)
cone cap depth      = voidR − discH/2              (spherical cap per cone)
insertion depth     = R_c + discH/2 − voidR        (bore must clear the void pole)
keyed length avail. = insertion depth − shaftR
```

The void is a sphere centred on the disc mid-plane; each cone holds a spherical-cap cavity truncated at ±discH/2, and the disc carries the equatorial belt as solid dielectric with a central bore. Cap, belt, and bore volumes are reported.

### 7.2 Key / hub sizing (DIN 6885) **[OC math; IR for the 1.5·D rule]**
Two stub shafts (one per apex). Key length is auto-sized by the load-distribution rule **L ≈ 1.5·shaft⌀**, snapped *up* to the nearest DIN 6885 standard length; a DIN 6885 cross-section table provides key width and hub keyway depth. In the **standalone** mode the hub diameter is *derived* from the assembly footprint:

```
hubDia (key sizing) = voidDia + shaftDia + 2·keyLen − discH   (= 2·R_c)
```

### 7.3 Feasibility guards
Each guard reports a signed margin; the binding (most-limiting) guard is named. Hard guards (red when violated) / soft guards (amber):

- **collar:** shaft⌀ ≤ R_c
- **void seat:** shaft⌀ ≤ 2·insertion depth
- **wall:** voidR ≤ (R_c/√2)·(1 − wall-fraction)
- **key fit:** keyed length ≥ key length
- **keyway collar** (soft): R_c − shaftR − hub-keyway-depth ≥ shaftR
- **hub fits ring** (coupled mode only — see §8)

Additional warnings cover caps vanishing (disc thickness ≥ void⌀), an over-wide bore, and the coupling checks.

### 7.4 High-voltage geometry (distances only) **[OC geometry]**
By mirror symmetry the void centre is the electrical neutral. The tool reports straight and surface distances but **does not assert a safe voltage** (deferred):

```
clearN  = voidR                          (electrode → central neutral)
clearEE = 2·voidR                        (electrode → electrode, through the void)
creepEE = 2·(voidR − bore/2) + discH     (surface path around the septum bore)
```

### 7.5 Live axial cross-section
A canvas slice through the shaft axis, mirrored left/right and top/bottom, redrawn on every recompute. It is **isotropic** (equal px/mm on both axes) so proportions are true, with a `fit | lock-scale` toggle, a millimetre **scale bar** + px/mm readout (necessary because the disc is wide and flat while the cones are small), and an optional **dimensions** overlay. Features are colour-coded and turn red when their guard trips, so the drawing doubles as the guard visualiser. It renders: the dielectric disc, the sectored electrodes (hatched annular bands), the two quadricone profiles, the spherical-void caps + septum belt + bore, the two shaft stubs with keyway, the central neutral marker, and the **fixed stator plates** above and below the rotor (annular bands at the gap g from each electrode, with stator ⌀ = rotor/plate ⌀, clearing the hub centrally).

---

## 8. Coupling between the geometry blocks **[IR — user-directed]**

The electrical plate (C-I) and the mechanical core (M) are linked by a toggle ("couple to plate", on by default; shareable in the URL). The two diameter families are kept distinct — an *outer* electrical family and an *inner* mechanical family — and tied as:

```
plate ⌀ (C-I)        →  structural disc ⌀ (M)        [outer family]
ring-outer ⌀ (C-I)   →  quadricone / hub ⌀ (M):  hubDia = ring-outer⌀,  R_c = hubDia/2   [inner family]
sectors (C-I)        →  primary structural input, surfaced in M (12 → 6 kept/6 gap, etc.)
```

The key consequence: in coupled mode the hub is **no longer derived from key sizing**; it is set by the capacitor ring. The DIN key/void/shaft sizing then becomes a **boundary condition** checked by a hard guard — *"hub fits ring (key sizing ≤ ring ⌀)"* — which goes red if the chosen void/shaft/key assembly will not fit inside the ring-imposed hub. In coupled mode the structural disc-⌀ input is disabled and tracks the plate, and the electrode is reported explicitly as the annulus [hub⌀, plate⌀] over the chosen sector count.

> The two implementation briefs originally specified this link as *warn-only* ("do not hard-link"). The active coupling was added on explicit instruction and recorded as a deliberate change in the changelog, per the project's "correct openly" convention.

---

## 9. Data flow and what is user-set vs. derived

| Quantity | Source |
|:--|:--|
| Sector count, plate ⌀, ring ⌀ (in/out), gap g, dielectric + (T, P, RH) | **User input** (Block C-I) |
| Rotor caps C1/C2 min & max | **Derived** from C-I capacitance (inherited; inputs disabled) |
| Transfer caps Ca, Cb; stray Cpar | **User input** (cannot be estimated yet) |
| Void ⌀, bore ⌀, disc thickness, shaft ⌀, wall fraction | **User input** (Block M) |
| Disc ⌀ | **Derived** from plate ⌀ when coupled (else user input) |
| Hub ⌀ / cone radius | **Derived** — from ring ⌀ when coupled, else from key sizing |
| Key length + DIN size, keyed length, clearances, creepage, volumes, guard margins | **Derived** (Block M) |
| Doubling ratio z and all electrical outputs | **Derived** (host solver) |

**Worked default device (loads on open):** 12 sectors, 1 m plate/disc, ring-outer ⌀ 150 mm → hub ⌀ 150 mm / cone radius 75 mm, gap 0.5 mm, air; void 40 mm, shaft 20 mm, disc thickness 10 mm. This yields inherited rotor caps **Cmin ≈ 278 pF, Cmax ≈ 7237 pF** (swing ratio 26), all mechanical guards green (binding guard: key fit), HV spans clearEE = 40 mm / creepEE = 30 mm, and with Ca = Cb = 100 pF, Cpar = 20 pF a doubling ratio **z ≈ 1.25** (pumping). *(These defaults were chosen so the coupled mechanical guards land valid; they are a starting point, not a recommended operating point.)*

---

## 10. User interface

Dark, monospaced, single-column-collapsing layout. Three input panels (rotor plate geometry; rotor mechanical core; rotor caps + transfer/stray) and an outputs panel (z display, verdict, growth metrics, headroom meter) plus charts. Every numeric control is a linked slider + number box with explicit units and a min/max range. Presets are provided: electrical (`device`, `wide`, `narrow`, `no swing`), plate-only dielectric exploration (`plate · air`, `plate · mica`), and the coupled `rotor-core` showcase. State is shareable via "copy share-url".

---

## 11. Verification — self-tests

The page runs a deterministic self-test suite on load and shows pass/fail in an expandable table; the engine badge reflects the aggregate. The suite has three groups, **all currently passing**:

**Electrical engine (host):**
- four reference operating points (no-swing → z ≈ 1.000; device → z ≈ 1.203; narrow → z ≈ 1.000; wide → z ≈ 1.438), each within tolerance;
- a C1↔C2 swap-symmetry check (swapping the two rotors must not change z).

**Block C-I (capacitance):**
- dry-air permittivity at 0 °C / 1013 hPa / 0 % RH → εr ≈ **1.000576** (matches the textbook value);
- a fixed-geometry capacitance check (10 cm plate, 12 sectors, ring off, 0.1 mm gap, vacuum) → Cmax ≈ **347.7 pF**, compared against an independently computed closed-form value.

**Block M (mechanical):**
- hub-diameter formula: void⌀ 50, shaft⌀ 35, disc thickness 0 → hub⌀ = **197 mm**;
- void-partition identity: two spherical caps + equatorial belt = full sphere (degenerate bore);
- DIN key sizing: keyLenFor(35 mm) → **DIN 56**.

These checks are deterministic and serve as a clean pass/fail gate for any change.

---

## 12. Assumptions, idealisations, and limitations

- **Ideal switched-capacitor model.** The solver uses ideal diodes (no forward drop, no leakage, no reverse recovery) and lossless capacitors. z is an asymptotic, steady-state ratio, not a transient or efficiency figure.
- **Fringing neglected.** The capacitance uses the ideal parallel-plate law; a warning fires when the gap is no longer small compared with the smallest in-plane feature, but no fringing correction is applied.
- **No breakdown / safe-voltage limit.** HV distances (clearance, creepage) are reported as geometry only. The tool deliberately does **not** convert them into a safe operating voltage; dielectric strength and leakage are a separate, deferred block.
- **Rotary-dielectric caveat.** Solid dielectrics (mica/Kapton) are not physically rotatable against both plates; they are flagged as fixed-gap exploration.
- **No mass / inertia / balance.** Rotational dynamics, mass, and static balance are out of scope (a later "flywheel" block).
- **Coupling is geometric, not enforced as a tolerance stack.** Plate ≈ disc and ring = hub are set as equalities; manufacturing tolerances are not modelled.
- **Defaults are illustrative.** The loaded default device is chosen to be self-consistent (all guards green), not to represent an optimised or recommended design.
- **Validation status.** All verification is internal/analytic (self-tests against closed-form values and reference points). The tool has **not** been validated against physical hardware.

---

## 13. Epistemic discipline (tier tags)

Every substantive statement in the documentation and every modelling choice in the code carries a tag, kept deliberately honest:
- **[OC] Operational Core** — standard, derivable physics/math, true independent of this project.
- **[IR] Interpretive Reading** — an engineering/modelling choice; internally consistent, chosen rather than forced.
- **[RH] Resonance / Heuristic** — suggestive only, not load-bearing.

This lets an external reviewer immediately distinguish textbook results (the capacitance law, the doubler solver, the geometry, DIN sizing, the air model) from design decisions (treating solids as constant, the raise-max field policy, the plate↔core coupling, rendering choices).

---

## 14. Reproducibility, provenance, and change control

- **Reproducible by URL.** Any computed state is fully captured in the page URL hash; sharing the link reproduces the inputs and therefore the outputs exactly.
- **No hidden state.** No `localStorage`, no cookies, no server; the page is deterministic given its inputs.
- **Auditable history.** Source is under version control with a human-readable `CHANGELOG.md`; the implementation briefs (`docs/brief-blockC1-…`, `docs/brief-blockM-…`) and conventions (`CONVENTIONS.md`) are part of the repository.

---

## 15. Symbol glossary (selected)

| Symbol | Code | Meaning |
|:--|:--|:--|
| C1, C2 | `c1*`, `c2*` | the two antiphase rotor capacitors (min/max) |
| Ca, Cb | `ca`, `cb` | fixed transfer capacitors |
| Cpar | `cpar` | per-node stray capacitance to ground |
| z | — | asymptotic per-cycle doubling ratio |
| Nsec | `pnsec` | sector count (12 → 6 kept / 6 gap) |
| g | `pgap` | capacitor gap (electrode ↔ stator) |
| εr | `epsR` | relative permittivity (dielectric) |
| Cmin, Cmax, κ_C | — | rotor capacitance extremes and swing ratio (= host r₁/r₂) |
| R_c, hub⌀ | `coneR`, `hubDia` | cone base radius; hub diameter = 2·R_c |
| voidR, discH | — | spherical-void radius; disc thickness |
| clearN/EE, creepEE | — | HV clearance and creepage distances |

---

## 16. Open items / roadmap

1. **Dielectric strength → safe-voltage bound** across the reported clearance/creepage (the genuine next block; couples C-I dielectric to M geometry).
2. **Conduction / leakage loss** in the doubler (moves z from ideal toward realistic).
3. **Fringing correction** for non-small gaps.
4. **Mass / rotational inertia / static balance** (flywheel block).
5. **θ-sweep visualisation** of C(θ) (the solver only needs the two extremes; this is illustrative).
6. **Estimating the transfer/stray capacitances** from geometry (currently the only required manual electrical inputs).

---

*End of report.*
