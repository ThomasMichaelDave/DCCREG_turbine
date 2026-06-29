# Figure brief — one image per formula

> Companion to `varcap-machine-design-guide.md`. For every numbered equation (1)–(39) this proposes a clarifying image: **what it shows**, **why it helps** (the theory point), the **labels** it must carry, and — where the physics is subtle — a **sync** note stating my understanding so we can confirm we agree before you draw it.

## How to use this

- One entry per equation, tagged `[E1]…[E39]`, in document order.
- **Merge tags** (`⇒ merge with En`) flag where a single composite figure naturally serves several equations — drawing the cluster once is better pedagogy and less work. If you want strict 1:1, ignore them.
- Figure-**type** shorthand: `geom` = annotated geometry/CAD view · `schematic` = circuit · `plot` = quantitative graph · `panel` = multi-part · `diagram` = conceptual/flow.
- My suggested **consolidated set is ~16 figures** covering all 39 equations (the merges below). I've marked which are the *high-value* teaching figures with ★.

### Quick map (equation → figure)

| Eq | Figure | Type | One-line |
|---|---|---|---|
| 1 | E1 ★ | diagram | Scale-free: same z at any absolute size |
| 2 | E2 ★ | geom | Parallel-plate base law (field, area, gap) |
| 3,5,6,7 | E3 ★ | panel | Sector overlap waveform + aligned/dis-aligned states + swing |
| 4 | E4 | geom | Area decomposition: modulated sectors + constant ring |
| 8,9 | E8 | geom | Annulus sector/ring geometry (r_in,r_out,N_sec,kept) |
| 10 | E10 ★ | diagram | Insulate-first: gap sized by breakdown, not by C |
| 11,12,13 | E11 ★ | diagram | Inverse-design flow (target C,κ,V → g → A_m → ring → r_out) |
| 14,15 | E14 | plot | Air ε_r vs humidity/temperature (how close to 1) |
| 16,17,18 | E16 ★ | plot | Two thickness regimes; max envelope; which part binds |
| 19 | E19 ★ | geom | Tank C_R across the septum, full face vs active band |
| 20,21 | E20 ★ | panel | The two ladders: capacitance vs steel-area |
| 22,23,24 | E22 ★ | plot | Dielectric FOM = ε_r·E_bd; plate area per dielectric |
| 25 | E25 | plot | Linear family scaling at fixed (g,ε_r) |
| 26,27,28,29 | E26 | geom | Boomerang plan+section (annotate the existing PNG) |
| 30,31 | E30 ★ | panel | LC tank: schematic + ring waveform + response |
| 32 | E32 ★ | plot | ½CV² energy triangle (reach = 89 mJ) |
| 33 | E33 ★ | panel | Two-cap LC transfer; η_M2 vs C_x/C_R peaking at match |
| 34,35,36 | E34 ★ | plot | Paschen curve with air & vacuum operating regimes |
| 37 | E37 | plot | Recovery 1−e^(−t/τ) vs inter-pulse window |
| 38 | E38 | diagram | Firing wheel → pulse train → PRF |
| 39 | E39 | plot | Rim speed vs rpm with 150/200 m/s limits |

---

## §1 — Scale-free anchor

### [E1] Eq. (1) — z = z(κ_C, C_a/C_max, C_par/C_min), scale-free ★
- **Image (diagram):** Two side-by-side renders of the *same* doubler-cap network — one "1×", one "10× linear size" — each annotated with its capacitances, both arriving at the **same z = 1.334**. Beneath, a second mini-panel: a single capacitor scaled up alone, with a big red ✗ and "z collapses."
- **Clarifies:** z is a function of *ratios only*; uniform scaling is free, scaling one family breaks the pump. This is the spine of the whole design philosophy.
- **Labels:** the three governing ratios; "×λ on all C → z unchanged"; "×λ on one C → z changes."
- **Sync:** My understanding — the doubler's node charge-conservation equations are homogeneous of degree zero in the capacitances, so a common factor cancels (App. A.0). The *value* of z is the frozen solver's; the figure should illustrate *invariance*, not claim to derive the number.

---

## §2 — Geometry → capacitance (forward)

### [E2] Eq. (2) — C = ε₀ε_r A_ov / g ★
- **Image (geom):** Classic two-plate capacitor in perspective: facing area A_ov shaded, separation g dimensioned, uniform field lines between the plates, slight fringing curl at the edges, +Q/−Q on the plates, dielectric ε_r filling the gap.
- **Clarifies:** the base law every later capacitor inherits; C ∝ area, ∝ 1/gap, ∝ ε_r.
- **Labels:** A_ov, g, ε_r, ±Q, E field; a dashed "fringing neglected here (see §2.3)" callout.
- **Sync:** uniform-field, fringing-neglected idealization — valid for g ≪ in-plane feature size.

### [E3] Eqs. (3),(5),(6),(7) — overlap fraction, the two extremes, swing ratio ★
- **Image (panel, 3 parts):**
  - (a) Top-view of the sectored disc pair at three rotor angles: θ=0 (sectors fully overlapping → aligned), θ=½s_θ (partial), θ=s_θ (sectors over gaps → only ring overlaps).
  - (b) Plot of f_ov(θ): triangle wave, amplitude 0→1, period 2s_θ, with the three states from (a) marked.
  - (c) A small bar pair C_max vs C_min with the ratio κ_C = C_max/C_min called out (≈17.5).
- **Clarifies:** how rotation linearly modulates facing area into a triangle; why only the two extremes feed the solver; that κ_C is a pure *area* ratio (ε₀,ε_r,g cancel).
- **Labels:** s_θ=360°/N_sec, period 2s_θ, f_ov∈[0,1], C_max (f=1), C_min (f=0, ring only), κ_C.
- **Sync:** the triangle is exact only for *radial* sector edges; the ring contributes a constant floor that is *rotation-independent* and is what sets C_min. Confirm the disc actually has radial edges (not skewed/curved), else the apexes round off.

### [E4] Eq. (4) — A_ov(θ) = A_m·f_ov + χ·A_ring
- **Image (geom):** Exploded/transparent rotor face showing two colour-coded regions — the outer *modulated* sector band (A_m, with the kept sectors highlighted) and the central *constant* ring (A_ring). An arrow shows the band's contribution sweeping with θ while the ring stays put.
- **Clarifies:** total facing area = modulated metal + constant ring; the two add because they're electrically parallel.
- **Labels:** A_m (modulated), A_ring (constant), χ∈{0,1} ring on/off.
- **Sync:** ⇒ can share art with E3(a); ring is the deliberate "C_min knob."

### [E8] Eqs. (8),(9) — sector metal area & ring area
- **Image (geom):** Flat annulus dimensioned with r_in, r_out, cut into N_sec=12 sectors, the 6 kept ones shaded in alternation; the central ring annulus dimensioned r_ring,in, r_ring,out separately.
- **Clarifies:** A_m is the kept fraction n_kept/N_sec of the annulus area; the ½ for the 6-of-12 build; ring is a plain annulus.
- **Labels:** r_in, r_out, N_sec, n_kept, the ½ factor; r_ring,in/out.
- **Sync:** kept sectors *alternate* (every other), n_kept = ⌈N_sec/2⌉ = 6.

---

## §3 — Capacitance → geometry (inverse)

### [E10] Eq. (10) — g = V_work·SF / E_bd  (insulate-first) ★
- **Image (diagram):** A gap with the working voltage across it; a vertical "voltage bar" showing V_work, then V_work·SF (margin), then the breakdown ceiling V_bd = E_bd·g sitting *above* it. A label: "gap chosen by breakdown FIRST, area second."
- **Clarifies:** the gap is a *high-voltage* decision independent of the capacitance target — the design-ordering principle.
- **Labels:** V_work, SF, E_bd (≈3 kV/mm air), resulting g (≈7 mm).
- **Sync:** insulate-first means g is solved *before* A_m; the C target then lives in the area, not the gap.

### [E11] Eqs. (11),(12),(13) — inverse design flow ★
- **Image (diagram, flowchart):** Boxes left→right: **Targets** (C_max, κ_C, V_work) → **g** [Eq.10] → **A_m** [Eq.11] → **A_ring** [Eq.12] → **r_out** [Eq.13] → **Checks** (rim §11, breakdown §4, fringing §2.3). Arrows carry the variable that propagates. r_in shown as the one free mechanical input feeding the r_out box.
- **Clarifies:** the fixed solving order and what each step consumes/produces; that κ_C only touches the ring; that r_in trades against r_out.
- **Labels:** each arrow with its symbol; mark "free choice: r_in."
- **Sync:** this is the §3.2 dependency paragraph as a picture — confirm the ordering matches how you actually design (gap → area → ring → radius).

---

## §4 — Dielectric & breakdown thickness

### [E14] Eqs. (14),(15) — moist-air permittivity & refractivity
- **Image (plot):** ε_r,air vs relative humidity (0–100%) at two or three temperatures, y-axis zoomed to ~1.0000–1.0008 so the variation is visible; mark the reference point (dry, 0 °C, 1013 hPa → 1.000576) and a "vacuum = 1 exactly" baseline.
- **Clarifies:** air genuinely varies but only at the 4th decimal; the water-vapour term is what moves it.
- **Labels:** the two Smith–Weintraub terms (dry vs vapour), the reference value, Buck p_sat source.
- **Sync:** the effect is <0.1% — the figure's job is to show it's *small but honest*, not large.

### [E16] Eqs. (16),(17),(18) — two thickness regimes & the max ★
- **Image (plot):** x-axis = plate area A (or capacitance target); two curves — t_breakdown (flat, voltage-set) and t_capacitance (rising with A for fixed C) — with the **max envelope** drawn bold. Mark operating points: **C_R** in the capacitance-driven regime, **C1/C2** in the breakdown-driven regime, **Ca/Cb** near the crossover ("check both").
- **Clarifies:** which constraint binds for which part, and why t = max(...).
- **Labels:** t_breakdown, t_capacitance, "binding = upper curve"; the three part operating points.
- **Sync:** my read — C_R is thick because of the *capacitance* target (12 mm garolite, field only 1.25 kV/mm), the air gaps are thick because of *breakdown*. Confirm Ca/Cb really sits near the crossover for you.

---

## §5 — Tank capacitor

### [E19] Eq. (19) — C_R = ε₀ε_r,garolite·A_full / t_septum ★
- **Image (geom, cross-section):** Axial section through the two rotor halves with the garolite septum between them; C_R formed across the *full* half-annulus face A_full. Beside it, a plan view contrasting the **full face** (used for C_R, f₀) with the **squeezed active band R95–R387** (used by the pump caps), shaded differently.
- **Clarifies:** C_R uses the whole face, not the pump band — the two areas are not interchangeable.
- **Labels:** A_full = ½π·r387², t_septum (12 mm), ε_r garolite; "active band ≠ full face."
- **Sync:** important non-obvious point — the squeeze shrinks *only* the pump; the tank sees the full disc.

---

## §6 — Design ratios & the steel budget

### [E20] Eqs. (20),(21) — area law & the two ladders ★
- **Image (panel):** Two vertical "ladders" side by side. Left: the **capacitance ladder** (C_min, C_rot, Ca, C_x, C_R, C_blk) on a log scale, all within ~3× except C_blk towering 1500× up. Right: the **steel-area ladder** for the same parts, where mica compresses Ca/Cb and the DC-block caps dominate (~22 m² for twelve). Connect each rung with a thin line showing the dielectric/gap "conversion."
- **Clarifies:** capacitance ratio ≠ area ratio; the dielectric+gap is the conversion factor (Eq.21); the magnet caps are the real material budget.
- **Labels:** each rung's value and ÷C_rot / ÷rotor-plate; "conversion = (g_i/g_j)(ε_rj/ε_ri)."
- **Sync:** ⇒ this is the §6.1/§6.4 tables as one picture; the punchline is "DC-block caps ≈ 50× the whole pump-cap set in steel."

### [E22] Eqs. (22),(23),(24) — voltage-limited area & dielectric FOM ★
- **Image (plot, grouped bars):** For Mica / Kapton / PP film: bars for (a) FOM = ε_r·E_bd and (b) resulting plate area per 440 nF/20 kV cap. Show PP winning area *despite* lowest ε_r, because E_bd dominates. Optional inset: u = ½ε₀ε_r E_bd² energy density.
- **Clarifies:** at fixed C,V the area ∝ 1/(ε_r·E_bd); high ε_r alone doesn't win — the *product* (the FOM) does.
- **Labels:** ε_r, E_bd, FOM, t_min, area each; "PP best (1100)."
- **Sync:** E_bd/FOM numbers are external dielectric-literature values, not repo-computed — figure should cite that.

### [E25] Eq. (25) — linear family scaling at fixed (g, ε_r)
- **Image (plot):** Straight lines through the origin: each capacitor's steel area vs the anchor C_rot, all scaling linearly; a slider/arrow "pick any C_rot, the family follows." A second annotation shows the *other* axis (trade gap) is breakdown-floored, so it can only grow.
- **Clarifies:** two scaling axes — scale C_rot (ratios preserved) vs trade gap (floored by insulate-first).
- **Labels:** A ∝ C; "gap floor (Eq.10) → voltage grows all areas."
- **Sync:** ⇒ conceptually pairs with E1 (scale-free) but here in *steel*, not in z.

### [E26] Eqs. (26),(27),(28),(29) — boomerang sizing
- **Image (geom):** **Annotate the existing `boomerang-cap.png`** — plan view: one sector plate dimensioned r_i, r_o, arc φ (A_boom); section view: the foil/film stack with N layers and total height H called out; a tag linking A_total (Eq.26, = the §6.5 template area) → divided over A_boom → N → H.
- **Clarifies:** the fixed voltage-set area spread over large-radius plates → thin stack; the four equations are just "total ÷ per-plate = layers → height."
- **Labels:** r_i, r_o, φ, A_boom, N, H, t_film, t_foil.
- **Sync:** the existing figure already exists; this is mainly *adding equation-linked dimension labels* to it. Confirm the 300–700 mm / 28° / 56-layer / 20 mm row is the canonical one to annotate.

---

## §8 — Resonator

### [E30] Eqs. (30),(31) — f₀ and Z₀ ★
- **Image (panel):** (a) the split-coil + C_R tank schematic (two half-coils k≈0.30, C_R at centre tap); (b) time-domain ring V(t),I(t) showing Z₀ = V̂/Î; (c) frequency response with a peak at f₀ and width set by Q.
- **Clarifies:** f₀ from √(LC); Z₀ as the voltage/current ratio of the ring; Q as sharpness.
- **Labels:** L_R=79 µH, C_R=789 pF, f₀≈637 kHz, Z₀≈316 Ω, Q∈{320,500,900}.
- **Sync:** note the split coil is *fields-aiding*; the 79 µH is the **aided total** (naïve 2×39.5 µH at k=0.30 would be ~102.7 µH — flag that as the §8 caveat).

### [E32] Eq. (32) — reach = ½ C_R V² ★
- **Image (plot):** The energy triangle — V vs q line of slope 1/C_R, area under it = ½CV² shaded; annotate the 15 kV / 789 pF → **89 mJ** target. Optional: stack of ~6–7 small "fire" increments summing to the triangle (the multi-fire reach).
- **Clarifies:** stored energy is the triangle area; the tank target is an *energy*, reached over several fires.
- **Labels:** ½C_R V², 89 mJ, "~6–7 fires × ~14 mJ (M2-PARTIAL)."
- **Sync:** reach is multi-fire, *not* a single resonant build-up (τ_tank < inter-kick) — the increments matter for honesty.

### [E33] Eq. (33) — island→tank transfer efficiency η_M2 ★
- **Image (panel):** (a) schematic: C_x (pre-charged) — L — C_R (empty), the spark gap as the switch; (b) time-domain V_x falling and V_R rising as charge sloshes, marking peak transfer at q_max=2q_eq where current returns to zero; (c) plot of η_M2 vs C_x/C_R, a curve peaking at **1.0 when C_x=C_R**, with the 471/789 → 0.94 point marked.
- **Clarifies:** lossless two-cap LC swap; efficiency is maximised at the match; the design sizes C_x near C_R for this reason.
- **Labels:** q_eq, q_max=2q_eq, η_M2, match point, 0.94 (single-face) / ~0.99 (second pickup face).
- **Sync:** ★ key derivation (App. A.18) — confirm you agree the relevant instant is *peak tank charge* (current zero), which is where the gap re-opens. This is the heart of the reach model.

---

## §9 — Spark gaps

### [E34] Eqs. (34),(35),(36) — breakdown laws & Paschen ★
- **Image (plot):** The Paschen curve V_bd vs p·d (log x) with its minimum (~0.7 kPa·mm) marked. Overlay: the **air** linear regime V_bd≈E_bd·g (right branch, tangent) and the **vacuum** sub-linear V_bd≈K·g^0.6 (left, below-minimum) regime; shade "air operating side" and "vacuum cavity side."
- **Clarifies:** one parent law, two deliberately-chosen operating regimes; why vacuum margin grows slowly (g^0.6) and air is roughly linear.
- **Labels:** Paschen min, E_bd≈3 kV/mm (air), K_vac≈60, exponent 0.6.
- **Sync:** the machine runs the cavity *below* the Paschen minimum (glow suppressed); air gaps run on the right branch. Confirm that split is current.

### [E37] Eq. (37) — hold-off recovery = 1 − e^(−t/τ_rec)
- **Image (plot):** Recovered-strength fraction vs time, three exponential curves for τ_rec ∈ {10 µs, 100 µs, 1 ms}; a vertical line at the inter-pulse window **333 µs (3000 rpm)**; shade "back-conduction risk" where the window falls left of adequate recovery. Mark the ~4000 rpm failure onset at the 1 ms corner.
- **Clarifies:** recovery (thermal channel deionisation), not fast recombination, is the binding rate limit.
- **Labels:** τ_rec bracket, t_cycle=333 µs, T_strike≈0.1 µs (for scale).
- **Sync:** recovery is the rate ceiling; quench is helped by motion + airflow / vacuum.

---

## §10–§11 — Commutation & envelope

### [E38] Eq. (38) — PRF = ⌈N_sec/2⌉·rpm/60
- **Image (diagram):** A "firing wheel" — the rotor with the 6 kept sectors, each marked as a fire event per revolution; a timeline below converting 6 events/rev × (3000/60) rev/s → **300 Hz/branch**. Optionally overlay the firing-station angles (SG1 3°, SG2 33°, …) from the §10 table.
- **Clarifies:** timing is inherited from sector geometry — no separate clock; PRF is just events-per-rev × rev-rate.
- **Labels:** N_sec=12, n_kept=6, rpm, 300 Hz/branch.
- **Sync:** ⇒ can fold in the §10 station map; "radius governs angle, not time."

### [E39] Eq. (39) — rim speed v = 2π·r_out·rpm/60
- **Image (plot + inset):** v vs rpm line for r_out=0.49 m, with horizontal limit lines at 150 (soft) and 200 m/s; operating point at 3000 rpm → **154 m/s** marked. Small inset: the disc with a tangential velocity vector at the rim.
- **Clarifies:** the mechanical ceiling that caps r_out·rpm; where the design sits against it.
- **Labels:** r_out, 150/200 m/s, 154 m/s operating point.
- **Sync:** the rim limit is what bounds r_out from above while the C target pushes it from below.

---

## Optional — key *unnumbered* relations worth a figure

These aren't tagged equations but carry real theory:

- **Quench window (§9.7)** — *diagram:* one rotation cycle with the ~30° favourable half shaded and the arc-extinction interval (µs–sub-ms) drawn inside it; red zone = "polarity reverses while still conducting → charge dumped." This is the single hardest timing constraint; arguably deserves a figure even though it's prose.
- **Design-limit battery (§12)** — *plot:* a margin bar chart across all limits, with **shuttle integrity (20/21 kV, margin 0.048)** shown as the shortest bar (the binding constraint). Great single-glance "where are we tight" figure.
- **Worked design point (§13)** — *diagram:* the full C → geometry → voltage → resonance chain as a single annotated flow, each step tagged with its equation number. A natural "capstone" figure.

---

## Production notes

- **Style:** match the doc's dark-theme/engineering idiom if these go on-screen; for print (the A4 docx/PDF) prefer high-contrast line art on white.
- **Consistency:** reuse the same colour for a given capacitor across E20/E22/E26, and the same symbol set as §1.1 (g not d, θ for angle, κ_C for swing).
- **Captions:** end each caption with the equation number it illustrates (e.g. "… — Eq. (33)") so figures and text cross-reference both ways.
- **Placement:** put each figure immediately after the equation it supports; the §6.7 boomerang already shows the pattern.
