# The Varcap Machine — Design Guide (Formulas & Parameter Dependencies)

> Markdown synthesis of `varcap-machine-design-guide.docx` / `.pdf`, for Claude Code.
> Formulas are LaTeX (`$$…$$`). Figure: `boomerang-cap.svg`.

**Scope.** A formula-first, objective design guide: every subsystem as governing equations, the inverse (target → geometry/thickness), and an explicit map of which parameter sets which.

**Sources & status.** Geometry from DXF `r0.15`; topology from the netlist of record; capacitance and dielectric model from the Block C-I brief; switching from the commutator-design brief; resonator/efficiency/operating point from design-freeze `v0.10` + the S-series. **Current architecture only** — co-rotating rotor halves, split 79 µH coil, 789 pF tank, z 1.334. Superseded choices are not carried. *(Repo-audited against branch `kicad-overlay`: island 648→471 pF single-face primary; reach is multi-fire, M2-PARTIAL; fire window 16.6–21 kV; SG1/SG2 fire the banks into the tank.)*

**Tiers.** `[OC]` standard physics, derivable · `[IR]` engineering choice · `[RH]` heuristic.

**Domain note.** Conventional electrostatic / high-voltage engineering throughout — Bennet doubling, parallel-plate capacitance, Townsend/Paschen breakdown, LC resonance, charge conservation. No substrate/cosmology content enters any formula or choice here.

---

## 1. Symbols and the parameter dependency map

### 1.1 Symbols (load-bearing names)

Plate separation is `g` (never `d`); rotor angle is `θ`; the swing ratio is `κ_C`. Geometry inputs carry no second UI name.

| Symbol | Quantity | Units |
|---|---|---|
| `ε₀` | vacuum permittivity = 8.8541878128×10⁻¹² | F/m |
| `ε_r` | relative permittivity of the gap medium | — |
| `A_ov(θ)` | facing (overlap) area at rotor angle θ | m² |
| `A_m / A_ring` | kept-sector metal area / central ring area | m² |
| `g` | plate separation (air gap) or solid-dielectric thickness t | m |
| `N_sec / n_kept` | sectors / kept sectors (alternating, n_kept = ⌈N_sec/2⌉) | — |
| `C_max / C_min` | aligned / dis-aligned variable-cap extremes | F |
| `κ_C` | swing ratio C_max/C_min (= solver r₁) | — |
| `z` | doubler per-cycle pump gain (scale-free) | — |
| `η` | net-electrical fraction (1 − equalization tax) | — |
| `f₀ / Z₀ / Q` | tank resonance / characteristic impedance / quality | Hz / Ω / — |
| `E_bd / V_bd` | dielectric strength / breakdown voltage | V/m, V |
| `SF` | safety factor on insulation (design margin) | — |

### 1.2 What sets what

The machine is scale-free in the capacitances: z depends only on capacitance ratios, so absolute size is free and is fixed instead by voltage (breakdown), throughput, and mechanics.

| Parameter | Set by (lever) | Propagates into |
|---|---|---|
| `g_v` (varicap gap) | breakdown, insulate-first: g ≥ V_work·SF / E_bd | C scale, fire voltage |
| `r_out` (R387) | C_max target (inverse, §3) + rim limit | C_max, rotor diameter, rim speed |
| `A_ring` | swing target: A_ring = A_m / (κ_C − 1) | C_min, κ_C |
| `C_max, C_min` | geometry (forward, §2) | z, throughput |
| `Ca, Cb` | match to C_max (z-band) | z, transfer tax |
| `t_diel` (solid caps) | max(capacitance-driven, breakdown-driven) (§4) | C, voltage hold |
| `C_R` | full rotor face / septum thickness | f₀, Z₀, reach |
| `L_R` | coil geometry (Nagaoka), sized for L_total | f₀, Z₀, node stress |
| `g_SG` (gap) | target fire voltage / breakdown law (§9) | V_fire, recovery time |
| ball radius | cross-fire margin + electrode life (≤17.5 mm @R387) | erosion interval |
| `rpm` | PRF target, bounded by rim + recovery | PRF, rim speed, quench window |

$$z = z\!\left(\kappa_C,\ \ C_a/C_{\max},\ \ C_{\mathrm{par}}/C_{\min}\right)\qquad[\text{scale-free}]$$

*Scale-free corollary: grow the battery by uniformly scaling the whole capacitance family; scaling one family alone collapses z.* `[OC]`

---

## 2. Variable capacitor: geometry → capacitance (forward)

The sectored-disc varicap is the pump's drive. Two plates on the shaft, the rotor group offset by one sector pitch, give the antiphase pair C1/C2. The capacitance follows the parallel-plate law over the rotation-dependent overlap, with a central ring providing a constant floor.

### 2.1 Base law and overlap

$$C = \varepsilon_0\,\varepsilon_r\,\frac{A_{\mathrm{ov}}}{g}$$

$$f_{\mathrm{ov}}(\theta) = \left|\,1 - \frac{\theta \bmod 2 s_\theta}{s_\theta}\,\right|,\qquad s_\theta = \frac{360^\circ}{N_{\mathrm{sec}}}$$

Radial sector edges → overlap area linear in angle → triangular fraction f_ov ∈ [0,1], period 2s_θ. θ=0 full overlap; θ=s_θ sectors over gaps. `[OC]`

$$A_{\mathrm{ov}}(\theta) = A_m\,f_{\mathrm{ov}}(\theta) + \chi_{\mathrm{ring}}\,A_{\mathrm{ring}},\qquad \chi_{\mathrm{ring}}\in\{0,1\}$$

### 2.2 The two extremes the doubler consumes

Only the two phase extremes feed the solver. The ring is azimuthally symmetric, so it is rotation-independent and sets C_min:

$$C_{\max} = \varepsilon_0\varepsilon_r\frac{A_m+\chi A_{\mathrm{ring}}}{g}\qquad C_{\min} = \varepsilon_0\varepsilon_r\frac{\chi A_{\mathrm{ring}}}{g}\qquad \kappa_C = \frac{C_{\max}}{C_{\min}}$$

With the ring off, C_min → 0 and κ_C → ∞ (z blows up); the ring is the **C_min-setting knob** that keeps the swing ratio finite and tunable. `[IR]`

### 2.3 Sector area

For an annulus between r_in and r_out cut into N_sec equal sectors with n_kept kept in alternation:

$$A_m = \frac{n_{\mathrm{kept}}}{N_{\mathrm{sec}}}\,\pi\!\left(r_{\mathrm{out}}^2 - r_{\mathrm{in}}^2\right)\ \ \xrightarrow{\,N_{\mathrm{sec}}=12,\ n_{\mathrm{kept}}=6\,}\ \ A_m = \tfrac{1}{2}\pi\!\left(r_{\mathrm{out}}^2 - r_{\mathrm{in}}^2\right)$$

$$A_{\mathrm{ring}} = \pi\!\left(r_{\mathrm{ring,out}}^2 - r_{\mathrm{ring,in}}^2\right)$$

**Fringing caveat.** The law neglects fringing — valid while g ≪ the smallest in-plane feature. Warn if g ≳ 10 % of the smaller of {smallest metal-sector arc width, ring radial width}; otherwise apply a Kirchhoff/Palmer effective-area correction. `[IR]`

---

## 3. Variable capacitor: capacitance → geometry and thickness (inverse)

This is the design direction: given a target C_max, a target swing κ_C, and the working voltage, recover the gap, the metal area, the band radius, and the ring. The ordering is fixed by insulate-first — the gap is a breakdown decision and is solved before the area.

### 3.1 Procedure

1. **Gap from voltage (insulate-first).** The gap must hold the working voltage with margin, independent of the capacitance target:

$$g = \frac{V_{\mathrm{work}}\cdot \mathrm{SF}}{E_{\mathrm{bd}}}\qquad\left(\text{air: }E_{\mathrm{bd}}\approx 3.0\ \mathrm{kV/mm}\right)$$

2. **Metal area from the capacitance target.** Invert the C_max law for the kept area:

$$A_m = \frac{C_{\max}\,g}{\varepsilon_0\varepsilon_r} - \chi A_{\mathrm{ring}}$$

3. **Ring from the swing target.** The ring sets C_min and hence κ_C:

$$A_{\mathrm{ring}} = \frac{A_m}{\chi\,(\kappa_C - 1)}$$

4. **Band radius from the metal area.** Choose an inner radius r_in (mechanical/ring clearance) and solve the outer:

$$r_{\mathrm{out}} = \sqrt{\,r_{\mathrm{in}}^2 + \frac{A_m\,N_{\mathrm{sec}}}{n_{\mathrm{kept}}\,\pi}\,}\ \ \Longrightarrow\ \ \tfrac{1}{2}\text{-kept}:\ \ r_{\mathrm{out}} = \sqrt{\,r_{\mathrm{in}}^2 + \frac{2A_m}{\pi}\,}$$

5. **Check against the limits.** rim speed (§11) caps r_out; the gap and ε_r feed the breakdown/voltage check (§4); fringing (§2.3) caps how small g may be relative to the sector arc.

### 3.2 Closed-form summary

$$\begin{aligned} g &= \frac{V_{\mathrm{work}}\,\mathrm{SF}}{E_{\mathrm{bd}}} & \qquad A_m &= \frac{C_{\max}\,g}{\varepsilon_0\varepsilon_r} - \chi A_{\mathrm{ring}} \\[4pt] A_{\mathrm{ring}} &= \frac{A_m}{\kappa_C - 1} & \qquad r_{\mathrm{out}} &= \sqrt{\,r_{\mathrm{in}}^2 + \tfrac{2A_m}{\pi}\,} \end{aligned}$$

**Dependency.** C_max and the working voltage together fix g and A_m; κ_C alone fixes the ring; r_in is the only free mechanical choice, and it trades against r_out. The swing κ_C is purely an area ratio — independent of g and ε_r, so it survives any later gap or dielectric change.

---

## 4. Dielectric selection and breakdown-limited thickness

### 4.1 Permittivity presets

| Medium | ε_r (nominal) | Model | Note |
|---|---|---|---|
| Vacuum | 1 (exact) | constant | humidity-independent; reference |
| Air | ≈1.0006 | live (T, P, RH) | the only one that genuinely varies |
| Kapton | 3.4 (band 3.0–3.5) | constant | fixed-gap only |
| Mica (muscovite) | 5.4 (band 5.0–7.0) | constant | low-loss precision staple |
| Garolite (G-10/FR4) | ≈4.5–5.0 | constant | structural septum (C_R) |

**Moist-air model.** `ε_r,air = 1 + 2·N_air·10⁻⁶`, with `N_air = 77.6·P/T + 3.73×10⁵·p_v/T²` (Smith–Weintraub; T in K, pressures in hPa), `p_v = (RH/100)·p_sat` and `p_sat` from Buck (1981). Dry, 1013 hPa, 273.15 K → ε_r ≈ 1.000576. Air vs vacuum differs <0.1 %, but it is the honest value. `[OC]`

**Rotary realisability.** A rotary varicap moves one plate through the gap medium, so its dielectric is in practice air or vacuum; a solid film cannot be rotated against while bonded to both plates. Solids belong to fixed or sliding-with-film geometries (Ca/Cb/C_R), not the rotating varicap. `[IR]`

### 4.2 Thickness from voltage — and the two regimes

For a solid-dielectric fixed capacitor the gap is the dielectric thickness t. Two independent constraints set it; take the larger.

$$t_{\mathrm{breakdown}} = \frac{V_{\mathrm{work}}\cdot\mathrm{SF}}{E_{\mathrm{diel}}}\qquad t_{\mathrm{capacitance}} = \frac{\varepsilon_0\varepsilon_r A}{C_{\mathrm{target}}}$$

$$t = \max\!\left(t_{\mathrm{breakdown}},\ t_{\mathrm{capacitance}}\right)$$

Which regime binds depends on the part:

- **C_R (tank) is capacitance-driven.** The full rotor face is large, so hitting 789 pF needs a thick septum: 12 mm garolite. The resulting field is 15 kV / 12 mm = 1.25 kV/mm — far under the ~5 kV/mm derated strength. Breakdown is not the lever here; the capacitance target is.
- **Air-gap varicaps (C1/C2) are breakdown-driven.** The 7 mm air gap is set to hold ~21 kV at 3 kV/mm; the area is then solved for the C target (§3).
- **Ca/Cb (transfer) — check both.** 4.5 mm mica for 309 pF; verify it also clears V_work·SF/E_mica.

**Void-in-solid caution.** A solid dielectric in series with an unavoidable air gap concentrates field in the air (the air sees the larger field because its ε_r is lower), which can lower the assembly breakdown below either material alone. Solid dielectric is therefore not a max-voltage lever; the levers are gap geometry, creepage ribs, and moving toward gas or vacuum insulation. `[OC]`

---

## 5. Fixed capacitors — transfer (Ca/Cb) and tank (C_R)

**Transfer caps Ca/Cb** are sized by the doubler match, not by geometry first: z peaks when the transfer cap is comparable to C_max. The Block C-I area law (§2.1) then gives the electrode area for the chosen mica thickness. Locked value: 309 pF, 4.5 mm mica. `[IR]`

**Tank C_R** is the rotor-to-rotor capacitance across the central septum, on the full r387 face (not the squeezed active band). It is sized for the resonance target with L_R (§8), and its thickness is capacitance-driven (§4.2). Locked value: 789 pF, 12 mm garolite. `[OC]`

$$C_R = \varepsilon_0\,\varepsilon_{r,\mathrm{garolite}}\,\frac{A_{\mathrm{full}}}{t_{\mathrm{septum}}},\qquad A_{\mathrm{full}} = \tfrac{1}{2}\pi\,r_{387}^{\,2}\ \ \text{(half-annulus face)}$$

**Active vs full face — keep them separate.** The pump caps use the squeezed active band (R95–R387); C_R and f₀ use the full face. The two areas are not interchangeable: the squeeze shrinks only the pump.

---

## 6. Design ratios — the capacitance ladder and the electrode-area ladder

The machine is scale-free in the capacitances (§7): only ratios set the pump, so the design is naturally expressed as a ladder anchored to one capacitor. The natural anchor is the rotor's own variable capacitance — **C_rot = C_max**, the aligned value of C1/C2. Every other capacitor is then a multiple of it. But a ratio is dimensionless and the build is not: each capacitor becomes a physical, steel-electrode plate whose area is fixed by its capacitance **and** its dielectric and separation.

### 6.1 The capacitance ladder (anchored to the rotor cap)

| Capacitor | Value | Dielectric · gap | ÷ C_rot |
|---|---|---|---|
| `C_min` (C1/C2 dis-aligned) | 16 pF | 7.0 mm air | 0.06 |
| **`C_rot = C_max`** (C1/C2 aligned) | **280 pF** | **7.0 mm air** | **1.00 (anchor)** |
| `Ca / Cb` (transfer) | 309 pF | 4.5 mm mica | 1.10 |
| `Cx,max` (flying bucket) | 471 pF | 3.0 mm air + 0.3 mm mica | 1.68 |
| `C_R` (tank) | 789 pF | 12 mm garolite | 2.82 |
| **`C_blk`** (C-magnet DC-block) | **440 nF** | **film / mica, 20 kV** | **1571** |
| per-group bank (6 × C_blk) | 2.64 µF | — | 9429 |

**The ladder spans pF to µF.** The pump caps cluster within ~3× of the rotor cap; the C-magnet DC-block caps stand three orders of magnitude above everything else. That single fact dominates the material budget (§6.4–6.5). Cx,max is the validated single-face **471 pF**; the 648 pF dual-face reading needs a second pickup electrode — a deferred TMD hardware call (dxf_flags.md). `[OC]`

### 6.2 Why each ratio is what it is

- **κ_C = C_max/C_min ≈ 17.5 — the swing.** Set by the central ring area (§2.2); fixes the pump's modulation depth and must keep z inside [1.20, 1.45].
- **Ca/C_rot ≈ 1.10 — the transfer match.** z peaks when the transfer cap is comparable to C_max; this near-unity ratio is a z-band choice, not free.
- **Cx,max/C_R ≈ 0.60 — the dump match.** The flying-bucket cap is sized close to the tank so the island dump η_M2 = 4·Cx·C_R/(Cx+C_R)² ≈ 0.94 (§8.1). Cx,max/C_rot ≈ 1.68 follows from that match, not from the pump.
- **C_R/C_rot ≈ 2.8 — the tank.** Fixed by the resonance target with L_R and by the full-face geometry (§5); sets the reach ½·C_R·V², independent of the pump gain.
- **C_blk/C_rot ≈ 1571 — the motor DC-block.** Sized by the motor branch, not the pump: it must pass the low-frequency stepping drive at minimum impedance while blocking the kV bias and staying a high-Z spectator at f₀. That forces nF, hence the 1500× jump. `[IR]`

### 6.3 Capacitance → steel: the area law

A ratio becomes a plate area only through the dielectric and the gap. For each capacitor the steel electrode area is:

$$A = \frac{C\,g}{\varepsilon_0\,\varepsilon_r}$$

So the area ratio between any two capacitors is the capacitance ratio scaled by their gap and dielectric:

$$\frac{A_i}{A_j} = \frac{C_i}{C_j}\cdot\frac{g_i}{g_j}\cdot\frac{\varepsilon_{r,j}}{\varepsilon_{r,i}}$$

This is why the capacitance ladder and the steel ladder are not the same ladder: a high-ε_r, thin dielectric (mica) buys a large capacitance on a small plate, while an air gap spends plate area. The dielectric and separation are the conversion factors. `[OC]`

### 6.4 The electrode-area ladder (what actually dominates)

Applying the area law at each capacitor's own dielectric and gap, normalised to the rotor plate (½π(R387²−R95²) = 0.221 m²):

| Capacitor | Value | g/ε_r (mm) | Steel area (m²) | ÷ rotor plate |
|---|---|---|---|---|
| **`C_rot` (C_max)** | **280 pF** | **7.0** | **0.221** | **1.00** |
| `Ca / Cb` | 309 pF | 0.83 | 0.029 | 0.13 |
| `Cx,max` | 471 pF | 3.11 | 0.165 | 0.75 |
| `C_R` | 789 pF | 2.55 | 0.228 | 1.03 |
| **`C_blk`** (each, PP-film) | **440 nF** | **0.036** | **1.81** | **8.2** |
| **`C_blk` × 12** | **5.3 µF** | **—** | **21.7** | **98** |

**Mica compacts the transfer caps** (1.10× the capacitance, 0.13× the plate); the air-dielectric pump and bucket caps and the garolite tank all sit near one rotor-plate of steel each (~0.22 m²). The C-magnet DC-block caps are the outlier: even on the most compact feasible film, **one is ~8× the rotor plate and the twelve together are ~22 m² — roughly 50× the entire pump-cap set combined.** The steel (electrode) budget of the machine is, to first order, the DC-block caps. `[OC]`

### 6.5 The magnet caps dominate — and the dielectric is the lever

Because the DC-block caps run at 20 kV, their dielectric cannot be made arbitrarily thin: the thickness is breakdown-limited (§4.2). Substituting the voltage-set thickness into the area law gives the plate area directly in terms of the dielectric:

$$A = \frac{C\,V_{\mathrm{work}}\,\mathrm{SF}}{\varepsilon_0\,\varepsilon_r\,E_{\mathrm{bd}}}\qquad\left(\text{voltage-limited: } t = V_{\mathrm{work}}\mathrm{SF}/E_{\mathrm{bd}}\right)$$

So at fixed capacitance and voltage the area scales inversely with the product ε_r·E_bd — the dielectric figure of merit. High permittivity alone does not win; mica's high ε_r is offset by its lower breakdown field, and a high-field film beats it:

$$u = \tfrac{1}{2}\varepsilon_0\varepsilon_r E_{\mathrm{bd}}^{\,2}\,,\qquad A \propto \frac{1}{\varepsilon_r\,E_{\mathrm{bd}}}\qquad\Rightarrow\qquad \mathrm{FOM} = \varepsilon_r\,E_{\mathrm{bd}}$$

| Dielectric | ε_r | E_bd (kV/mm) | t_min @20 kV (SF 2) | Area each (m²) | FOM ε_r·E_bd |
|---|---|---|---|---|---|
| Mica | 5.4 | 118 | 0.34 mm | 3.12 | 637 |
| Kapton film | 3.4 | 236 | 0.17 mm | 2.48 | 802 |
| **PP film** | **2.2** | **500** | **0.08 mm** | **1.81** | **1100 (best)** |

The polypropylene film wins on area despite the lowest ε_r, because its breakdown field lets it run thinnest. This is also why a 440 nF / 20 kV part is realistically a wound-film capacitor, not a disc-integrated plate: at these areas it is a discrete component, and it is the dominant capacitor mass in the build. (The E_bd and FOM figures here are external dielectric-literature values, not repo-computed.) `[IR]`

### 6.6 Scaling the whole family

Because the pump is scale-free, the ratio ladder is invariant — choose any absolute rotor capacitance and the rest follow. At a fixed dielectric and gap the areas scale linearly with it:

$$\text{fixed }(g,\varepsilon_r):\quad A \propto C\quad\Longrightarrow\quad \{C_a,\,C_x,\,C_R,\,C_{\mathrm{blk}}\}\ \text{scale linearly with } C_{\mathrm{rot}}$$

**Two scaling axes.** Either hold the gaps and dielectrics and scale the rotor cap (the whole steel ladder scales ∝ C_rot, preserving every ratio), or hold the areas and trade the gap — but the gap is breakdown-floored (insulate-first, §3.1), so it can only grow, not shrink, at a given voltage. Raising the operating voltage therefore grows every steel area through the thickness floor, fastest on the DC-block caps. The rotor cap sets the family; the voltage sets the floor; the dielectric sets how much steel each ratio costs. `[OC]`

### 6.7 C-magnet block cap — boomerang realization and practical design

The 440 nF / 20 kV DC-block cap (§6.1) is realized as an axially-stacked **boomerang** — flat annular-sector plates (Al foil) interleaved with Mylar film, one cap centred on each C-EM in the outer annulus, the stack building along the shaft axis in the C-EM-plus-frame depth. Because the plate area grows with r², reaching out toward the rim makes the stack thin: the fixed template area (set by energy, §6.5) is spread over large plates, so only a few tens of layers are needed.

![Boomerang block cap — plan (twelve sector caps, alternating group rails) and section (axial foil/Mylar stack over the C-EM).](boomerang-cap.png)

Sizing follows directly from the voltage-limited template area (§6.5) divided over the sector plates:

$$A_{\mathrm{total}} = \frac{C\,V_{\mathrm{work}}\,\mathrm{SF}}{\varepsilon_0\,\varepsilon_r\,E_{\mathrm{bd}}}$$

$$A_{\mathrm{boom}} = \tfrac{1}{2}\varphi\,(r_o^{2} - r_i^{2})\,,\qquad N = \frac{A_{\mathrm{total}}}{A_{\mathrm{boom}}}\,,\qquad H = N\,(t_{\mathrm{film}} + t_{\mathrm{foil}})$$

| Boomerang (r_i–r_o, arc) | Mylar | A_boom | layers N | stack H |
|---|---|---|---|---|
| 400–700 mm, 28° (clear of pump band) | 0.35 mm (57 kV/mm) | 0.081 m² | 68 | 25 mm |
| **300–700 mm, 28°** | **0.35 mm** | **0.098 m²** | **56** | **20 mm** |
| 300–700 mm, 28°, impregnated | 0.25 mm (80 kV/mm) | 0.098 m² | 40 | 11 mm |

Twelve 28° boomerangs leave ~2° gaps ≈ 24 mm of clearance between adjacent stacks — enough to insulate neighbours, which sit on antiphase group rails (full Δ-voltage to each other). Material is unchanged from §6.4 (~5.4 m² per cap); the boomerang only packages it flat and curved. (The boomerang packaging is a proposed mechanical realization, not part of the repo deck.) `[IR]`

**Practical design rules** — these are material/electrical, not geometric, so none appear in the DXF; the first three change the design, the rest are bench-verified:

- **Edge field grading (corona).** A bare foil edge concentrates field and starts corona that erodes the Mylar. Round or anti-corona-border the edges, and grade the stack (outer plates slightly smaller than inner) so the field steps down toward the rim. The triple point — foil/dielectric/impregnant junction — must be buried in solid or oil, never at an air boundary. `[OC]`
- **Impregnation and voids.** A many-layer stack traps air; any void partial-discharges at 20 kV and ladders the PET out. Vacuum-dry then oil- or resin-impregnate, with a defined fill/vent path (an annular sector traps bubbles at the outer arc unless filled from there). This decides sealed-oil-can vs potted-block construction. `[OC]`
- **Series-string voltage sharing.** Treated here as one parallel cap with every layer at the full 20 kV. If instead built as series sub-stacks to ease the per-layer field, stray capacitance to frame skews the sharing and one section hogs the field and fails first — needing grading elements, and any resistor across the block partly defeats the DC-block. Decide parallel-vs-series before the plate count is fixed. `[IR]`
- **Self-resonance / ESL.** The block must be low-impedance at the ~150 Hz drive, but it also sees the f₀ ≈ 637 kHz tank ring and sub-µs spark-gap fire transients. A wide flat stack has real inductance; place the foil tabs so the self-resonant frequency sits clear of f₀, or it stops being a clean block at the one frequency it must isolate. `[OC]`
- **dV/dt and ripple heating.** Fast commutation steps drive AC current through the film every cycle; dielectric loss (tanδ × V_AC × PRF) is real wattage, and PET's tanδ rises with temperature — check against thermal runaway in the sealed stack. Polypropylene is markedly better here (another nudge toward PP if margin is thin). `[OC]`
- **Mechanical.** Stator-mounted is simplest; if any of it rides the rotor it sees centrifugal load — clamp so plates cannot fan out or shift (which changes C and opens voids), and account for differential thermal expansion between foil, film, and frame. `[IR]`
- **Effective area.** Foil tabs and the creepage inset subtract from the geometric sector, so the effective A_boom is smaller and the real layer count runs a few above the clean calc — size with a ~10 mm dead border. `[OC]`
- **Failure mode.** Foil/PET is not self-healing: one defect is a dead short, and a shorted DC-block dumps the coil onto the pump node. Either accept periodic replacement, or use self-clearing metallized-PP segments and re-sum the area at that construction's stress. `[IR]`

---

## 7. The doubler — gain z and efficiency η

The 4-node symmetric Bennet doubler is the engine. Its per-cycle gain z is scale-free — a function only of capacitance ratios — so it is the same at any absolute size. The frozen solver is the authority for z and η; the relations below are the dependency structure, not a re-derivation.

$$z = z\!\left(\kappa_C,\ \ C_a/C_{\max},\ \ C_{\mathrm{par}}/C_{\min}\right)\qquad[\text{scale-free}]$$

$$z = 1.334\ \ (\text{galvanic ceiling})\qquad z \approx 1.307\ \ (\text{648 pF island})$$

**Efficiency.** η is the useful output over useful + the charge–charge equalization tax. The doubler core converts at η = 0.386. The downstream island transfer is a true sink and recovers its share of the tax, lifting the machine to η ≈ 0.50 (0.518 design-point transfer-chain η; the self-consistent machine η including the multi-fire reach is ≈ 0.48, island-charging). The doubler-core/Ca–Cb share of the tax is the pumping action itself and is not recoverable. `[OC]`

$$\eta_{\mathrm{core}} = 0.386\qquad \eta_{\mathrm{machine}} \approx 0.50\ \ (\text{direct + island sink})$$

**Band constraint.** Keep z in the validated band [1.20, 1.45]; below it the modulation collapses (κ_C → 1) and the pump dies, which is what the C_min/ring knob (§2.2) and C_par floor guard against.

---

## 8. Resonator — tank, reach, and the island dump

The tank is the rotor-to-rotor C_R rung by a split conical coil (two sized half-coils, fields-aiding k ≈ 0.30, on the two hubs, with C_R at the centre tap). The split shares the fire transient as two smaller drops so each rotor node sees ~17.5 kV rather than ~35 kV. The coil sits ~1000× below the tank in frequency at the pump rate, so pump and ring do not interfere.

$$f_0 = \frac{1}{2\pi\sqrt{L_R C_R}}\qquad Z_0 = \sqrt{\frac{L_R}{C_R}}$$

$$\begin{gathered} L_R = 79\ \mu\mathrm{H},\qquad C_R = 789\ \mathrm{pF} \\[3pt] \Longrightarrow\quad f_0 \approx 637\ \mathrm{kHz},\qquad Z_0 \approx 316\ \Omega,\qquad Q \in \{320,\,500,\,900\} \end{gathered}$$

**Coil sizing.** Two naïve 39.5 µH halves aided at k=0.30 give ~102.7 µH (f₀ ≈ 559 kHz), not 79 µH; the halves are sized down so the aided total lands at L_total = 79 µH. Size the per-half inductance from the Nagaoka form for the conical winding, then verify the aided total. `[IR]`

### 8.1 Reach and the island transfer

$$\text{reach (tank target)} = \tfrac{1}{2}\,C_R\,V^2 \;\approx\; 89\ \mathrm{mJ}\ \ (\text{15 kV},\ 789\ \mathrm{pF})$$

$$\eta_{M2} = \frac{4\,C_x\,C_R}{(C_x + C_R)^2} \;\approx\; 0.94\ \ (\text{471/789 pF})$$

**Multi-fire, not single-kick.** With τ_tank ≈ 0.5 ms against ~1.67 ms between kicks the tank does not build resonantly (accumulation ×1.0–1.01), so it stays Q-robust and f₀-independent. But the island-charging co-sim (verdict **M2-PARTIAL**) shows the gap fires mid-collapse at ~70 pF delivering **~14 mJ/fire**, so the 89 mJ tank is reached over **~6–7 fires** (`ISLAND-FIRE-ENERGY = 14 mJ`, `kick-count ≈ 6.5`) — multi-fire, not a single kick. Match C_x to C_R to keep each dump near 0.94 (single-face; ~0.99 with a second pickup face). `[OC]`

---

## 9. Spark gaps — design choices

The gaps physically realise the solver's ideal diodes. Direction comes from timing, not from a diode or a trigger: rotor alignment gates a self-break.

### 9.1 Switching principle

**Hybrid: alignment-gated self-break.** Alignment (the minimum-gap instant) sets when breakdown is possible — pure rotor geometry, drift-free and measurable. The self-break sets the firing voltage. Because the firing angle is the intersection of two rotor-deterministic curves (rising source V vs falling gap length), voltage scatter perturbs the level, not the timing, so jitter stays low. `[OC]`

**Rejected alternatives** `[IR]`: a triggered trigatron (too many drifting, unmeasurable variables; temperature drift corrupts a timed instant); diodes / solid-state switches (reverse back-pressure needs exotic parts; gate drive on a slip-ring-free spinning frame).

### 9.2 Gap medium — air vs vacuum

The breakdown law differs by regime; pick the operating side of the Paschen curve deliberately.

$$\text{air (above Paschen min):}\quad V_{\mathrm{bd}} \approx E_{\mathrm{bd}}\,g,\qquad E_{\mathrm{bd}} \approx 3.0\ \mathrm{kV/mm}$$

$$\text{vacuum (field emission):}\quad V_{\mathrm{bd}} \approx K_{\mathrm{vac}}\,g^{0.6}\ \mathrm{kV},\qquad K_{\mathrm{vac}} \approx 60$$

$$\text{Paschen:}\quad V_{\mathrm{bd}} = f(p\,d),\qquad \text{minimum near } p\,d \approx 0.7\ \mathrm{kPa\cdot mm}\ (\text{air})$$

- **Air.** Simple, self-healing, but needs active quench (the channel must deionise between pulses) and erodes electrodes; field roughly linear in gap.
- **Vacuum.** Windage ≈ 0 (good for the spin-up budget) and the cavity sits below the Paschen minimum so glow is suppressed; breakdown is sub-linear in gap (g^0.6), so margin grows slowly with gap. Used for the cavity in the current design.

### 9.3 Electrodes — geometry and material

- **Geometry: spheres / hemispheres.** A uniform-field sphere gap gives a repeatable self-break and is corona-free; sharp tips produce soft, leaky, poorly-timed corona and are rejected for the switching gaps. Smooth large-radius electrodes are used where a soft glow is wanted (governor, backstop).
- **Sizing.** Ball radius is grown with the firing radius for cross-fire margin and electrode life, bounded by the station spacing. At R387 the maximum ball is 17.5 mm (from the radius/overlap trade).
- **Material: tungsten / W-Cu.** Erosion resistance for repetitive duty. Erosion widens the gap over life, so the operating voltage creeps up — but the timing is geometric and unaffected; this sets a maintenance interval, not a failure. `[IR]`

### 9.4 Single vs series (double) gaps

**SG1, SG2** fire the AR/BR transfer banks into the resonator tank (floating/differential — no ground return). **Cross-couples (SG3, SG4)** bridge two stator electrodes over a floating rotor bar — a series double gap with a floating midpoint. The double gap has a less predictable strike (two Paschen curves in series plus the floating-midpoint stray capacitance), which is tolerable precisely because the timing is geometric and the firing level is non-critical. `[IR]`

### 9.5 Self-break statistics and recovery

$$T_{\mathrm{strike}} \approx 0.10\ \mu\mathrm{s}\qquad\text{hold-off recovery} = 1 - e^{-t_{\mathrm{cycle}}/\tau_{\mathrm{rec}}}$$

$$\tau_{\mathrm{rec}} \in \{\,10\ \mu\mathrm{s},\ \ 100\ \mu\mathrm{s},\ \ 1\ \mathrm{ms}\,\}$$

**Recovery is the binding rate constraint.** At repetition the inter-pulse window must exceed the channel-recovery time, or the gap back-conducts. At 3000 rpm the window is ~333 µs; recovery-failure onset is near ~4000 rpm at the pessimistic (1 ms) corner. The thermal recovery of the spark channel — not fast charge recombination — limits repetition rate. Quench by motion (larger firing radius → faster sweep, ionisation spread over more area) plus forced airflow run with the disc's centrifugal pumping; in the vacuum cavity, motion and the low pressure do the work. `[OC]`

### 9.6 The backstop gap

**A second, smaller gap per island** at a later station and a lower threshold (≈0.6× the main strike) catches any misfire the load-return did not clear, bounding the island charge to ≤1.05× one bucket. It is a gap, not a resistor — no galvanic element may span the island — and it adds a small fixed stray (~6 pF) to the C_min sum, which must be carried in the swing budget. `[IR]`

### 9.7 Quench window — the make-or-break

$$\text{arc must extinguish before the varicap polarity reverses}$$

If the channel is still conducting when the source polarity reverses, it back-conducts and dumps the pumped charge. The favourable half is ~30° of rotation; the arc blow-out (µs to sub-ms) must complete inside it. This is the single hardest timing constraint and is verified both in model and on the bench. `[OC]`

---

## 10. Commutation timing and firing stations

Timing is inherited from the varicap sector geometry — there is no separate clock. The C1/C2 antiphase offset, the stroke offset, and the SG3/SG4 firing offset are all one sector pitch (30°).

$$\mathrm{PRF} = \left\lceil N_{\mathrm{sec}}/2\right\rceil \frac{\mathrm{rpm}}{60}\quad(\text{per branch});\qquad 6\ \text{cycles/rev at } N_{\mathrm{sec}}=12$$

Stations (DXF r0.15), conduction pairs {SG1,SG3} and {SG2,SG4}, firing return-leads-then-cross-couple:

| Gap | Role | Station | Path |
|---|---|---|---|
| `SG1` | bank→tank | 3.00° | node 2 → resonator (R-A) |
| `SG2` | bank→tank | 33.00° | node 3 → resonator (R-B) |
| `SG3a` | load | 7.20° | node 1 → island |
| `SG3b` | fire | 16.05° | island → node 3 |
| `SG4a` | load | 37.20° | node 4 → island |
| `SG4b` | fire | 46.05° | island → node 2 |
| `BS3` | backstop | 19.00° | island misfire catch |
| `BS4` | backstop | 49.00° | island misfire catch |

**Radius governs angle, not time.** Pushing the gaps outboard (R387) buys cross-fire margin in angle and a larger usable ball (life), bounded by the island radius (~R350). It does not change the resonant timing. Trade at R387: 2.95° station spacing, 2.07° overlap at a 12 mm ball, 0.88° cross-fire margin, ~115 µs overlap at 3000 rpm. `[OC]`

---

## 11. Mechanical and operating envelope

$$v = \frac{2\pi\,r_{\mathrm{out}}\,\mathrm{rpm}}{60}\,,\qquad v < 200\ \mathrm{m/s}\ \ (\text{soft }150)$$

**Dependencies.** r_out and rpm trade against the rim limit; the rotor runs supercritical (above its first bending critical) so the operating speed is held away from criticals. The cavity is vacuum ≤ 10 Pa: windage ≈ 0 (spin-up budget) and glow suppressed (below Paschen minimum). Parked operating voltage 15 kV; with the v0.10 freeze the fire window is 16.6–21 kV (4.4 kV margin): fire ≥ 16.6 kV delivers 89 mJ at η 99 %, capped near 21 kV by the C1/C2 7 mm air gaps. `[OC]`

---

## 12. Design limits (the binding battery)

A candidate is feasible only inside every limit; the binding constraint is the one with least margin. At the current anchor the machine is **shuttle-strike-bound**.

| Limit | Bound / constant | Anchor margin |
|---|---|---|
| Scale-free z | z ∈ [1.20, 1.45] | z 1.334 → 0.080 |
| Insulate-first | V_bd > V_target 15 kV; garolite 5 kV/mm derated; vacuum V_bd=60·g^0.6 | 39.6/15 kV → 1.64 |
| Tax managed | η ≥ 0.15 | 0.386/0.15 → 1.58 |
| Parasitic floor | C_par ≥ 20 pF | (C_max−C_par)/C_par ≈ 13 |
| Motor matched | output ≤ pump_net; f_res = PRF; f₀ spectator | 3.7/6.2 mJ → 0.40 |
| Mechanical | rim < 200 (soft 150) m/s; vacuum ≤ 10 Pa | 154/200 → 0.23 |
| **Shuttle integrity (binding)** | **island strike < 21 kV ceiling** | **20/21 kV → 0.048** |
| Cross-fire / timing | overlap clears SG3b–BS3; fire window vs spacing | geometry |

---

## 13. Worked design point (R1 / freeze, traced)

A pass through the formulas at the reference point, so the chain C → geometry → voltage → resonance is visible end to end.

1. **Varicap gap (insulate-first).** `g = 21 kV / 3 kV/mm ≈ 7 mm` air → holds the fire transient.
2. **Metal area for C_max ≈ 280 pF** (vacuum-ε, ring floor χA_ring for C_min ≈ 16 pF): `A_m = C_max·g/ε₀ − χA_ring`.
3. **Band radius.** `r_out = √(r_in² + 2A_m/π) → R387` with the R95 inner band (½-kept, 12 sectors).
4. **Swing.** `κ_C = 280/16 ≈ 17.5`; the ring area sets this floor independently of g and ε_r.
5. **Transfer / gain.** Ca = Cb = 309 pF matched to C_max → `z = 1.334` (η_core 0.386; machine ≈ 0.50 with the island sink).
6. **Tank.** `C_R = ε₀ε_r A_full / 12 mm = 789 pF`; with L_R = 79 µH → `f₀ ≈ 637 kHz, Z₀ ≈ 316 Ω`.
7. **Reach.** `½ C_R V² = ½ · 789 pF · (15 kV)² ≈ 89 mJ` reached over ~6–7 island fires (~14 mJ each; M2-PARTIAL); island dump 4·471·789/(471+789)² ≈ 0.94.
8. **Commutation.** `PRF = 6 · 3000/60 = 300 Hz`/branch; stations per §10; recovery window ~333 µs > τ_rec; rim 2π·0.49·3000/60 ≈ 154 m/s < 200.

---

*End of guide. Formulas are the design relations; the frozen solver remains the authority for z and η, and the bench is the final court on the breakdown and quench assumptions. Where the synthesizer's default preset and the validated operating point differ (the 326 vs 637 kHz tank, the 39.5 µH placeholder), this guide states the operating value and flags the gap.*
