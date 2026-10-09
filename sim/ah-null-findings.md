# The AH's magnetic null in the locked hub — findings

**Source:** `sim/ah_null.py` → `sim/ah_null_results.json`; figure `docs/figures/ah-null.png` (the same script).

**Status:** [OC] the magnetostatics, [IR] the linear ferrite and the finite volumes; the 22 mF bypass used here is PROPOSED, not accepted (`sim/ah-steady-cusp-findings.md`).

**Naming:** "top" is the coil above (z > 0), side B's, the deck's AHb; "bottom" is the coil below, side A's, AHt
(`README.md`:24; `sim/ah-steady-cusp-findings.md`:9–10). Which way B_z points follows the winding sense
(`sim/ah-steady-cusp-findings.md`, the winding sense); the magnitudes and positions here do not depend on it [OC].

## Headline numbers
At the pick's 300 A-turns per coil, rods μ_r 2000, the shaft non-magnetic as recorded, unless stated. With the 3-D
utrons (2026-10-09, `sim/utron-3d-findings.md`) the coils carry 221–245 A-turns, so the gradient is 0.083–0.092 T/m
(0.377 mT/m per A-turn); the positions scale with the imbalance, which stays within 12–14 A-turns.

| what | value | where |
|:--|:--|:--|
| the null, balanced pair | at the geometric centre (5e-14 mm) | G-SYM |
| the null with the 22 mF bypass (PROPOSED), over the 120 Hz cycle | −0.43 to +0.44 mm on the axis (0.87 mm p-p); ≤ 50 µT at the centre | §3 |
| the null without the bypass (today's circuit) | −6.36 to +6.32 mm (12.7 mm p-p), more than 3 mm off centre 92 % of the time; up to 0.53 mT at the centre | §3 |
| the gradient at the null, dB_z/dz | **0.113 T/m** (11.3 G/cm): 0.377 mT/m per A-turn on both coils; ×4.8 the same coils without rods | §2 |
| the radial gradient, dB_r/dr | −0.0565 T/m (−½ the axial) | §2 |
| \|B\| in the equatorial plane, r 5 / 10 / 20 mm | 0.27 / 0.50 / 0.70 mT | §2 |
| \|B\| on the axis, \|z\| 5 / 10 / 20 mm | 0.59 / 1.36 / 5.02 mT | §2 |
| the rod's peak | 0.121 T (0.181 at 449 A-turns, 0.242 at 600) | §4 |
| the rod's limits (linear) | 0.30 T (the register's) at 743 A-turns; B_sat 0.38 T (100 °C) at 941; 0.49 T (25 °C) at 1214 | §4 |
| mild-steel shaft halves, touching the rods | gradient +83–85 %, but the rods at 0.35–0.37 T, and the null moved 5.8 mm if one half is steel, 2.8 / 0.6 mm for a 1 / 0.1 mm difference in seating | §5 |

- **The null sits where the coils' imbalance puts it** [OC, first order]: z_null ≈ −15.2 mm × (top − bottom) /
  (top + bottom), toward the weaker coil. At 300 A-turns mean that is 25 µm per A-turn of difference.
- **The bypass is what holds it.** With it the null stays within ±0.44 mm; without it it swings ±6.4 mm, beyond the
  ±5 mm within which the rings' DC field holds 4.4 % (`docs/rings-design.md` §5) [OC].
- **The record's rod limit is conservative.** "About 600 A-turns" scales a run that had the RA chain's cone windings in
  series with the AH. For the AH alone the 0.30 T point is 743 A-turns (§4).
- **The non-magnetic shaft stands** [IR], now with numbers: steel halves would nearly double the gradient only by
  running the rods into saturation and tying the null to how each half seats (§5).
- **Not in the brief, the same solver:** a uniform axial field moves the null 0.10 mm per 10 µT (the rods concentrate
  it ×1.18 at the centre). The earth's vertical component, about 35–50 µT at mid-latitudes [IR], is worth 0.35–0.5 mm
  on the vertical axis, as much as the bypassed imbalance (§6).

## 1. The model and its gates
- **The geometry** (`presets/hub-locked.json` AH, AH_seat, vessel, vessel_wall, shaft) [IR]:
  - the rods: 12.3 mm across (r 6.15 mm), |z| 30.7–72.0 mm;
  - the coils: 160 turns as a uniform current density over r 8.25–11.45 mm, |z| 31.35–71.35 mm;
  - μ_r 1 everywhere else: the G-10 formers, the PEEK seats (|z| 25.0–30.7), the vessel, the retainer, and the
    shaft as recorded ("magnetic": false) [OC: non-magnetic materials].
- **The ferrite:** linear, μ_r 2000 (`presets/electromagnets-RA.json` AH_rod mu_i, datasheet-class) [IR].
- **The field:** axisymmetric magnetostatics in ψ = r A_φ, −∇·((ν/r)∇ψ) = J_φ [OC], with the finite-volume operator of
  `sim/edge_coil.py` (its gate G-MS, `sim/edge-coil-findings.md` §1) [IR].
  - Every material edge sits on a node. The cells are 0.25 mm inside r ≤ 34 mm, |z| ≤ 82 mm, graded to a ψ = 0
    boundary at 2 m: 219 k nodes, about 3 s a solve.
- **The readouts** [OC]: B_z on the axis from ψ = (B_z/2) r² + c r⁴ at the first two radial nodes; the null by Newton
  on a spline of B_z(z) inside the vessel; B_r by central differences; |B| per cell in the ferrite and steel.
- **Linearity:** every field is NI_top × (the top coil's field per A-turn) − NI_bottom × (the bottom's) [OC, linear
  μ]. At 120 Hz the problem is quasi-static: MnZn's skin depth is about 2 m (ρ 5 Ω·m, the register) [OC].
- **The currents:** `sim/ah_steady_cusp_results.json` keeps only their statistics. The script reruns the pick exactly
  as `sim/ah_steady_cusp.py` does (ngspice), without and with the 22 mF bypass, and reads AHt / AHb over the last four
  cycles (G-WAVE).

| gate | result | pass |
|:--|:--|:--|
| G-AIR: an air-cored coil's B_z on the axis against the thick-solenoid closed form, \|z\| ≤ 80 mm | max 0.064 %; +0.036 % at the centre; the air-cored pair's gradient 0.02340 against 0.02339 T/m | ✔ (≤ 1 %) |
| G-MESH: h 0.5 → 0.25 → 0.125 mm, the gradient at the null | 0.11291 → 0.11306 → 0.11315 T/m: +0.13 %, +0.08 % | ✔ (< 2 %) |
| G-MESH, the same steps: the null's lever / the rod's peak / the null shift of a 0.5 mm misplacement | +0.02 / +0.20 / +0.12 %, then +0.004 / +0.11 / +0.02 % | — |
| G-SYM: balanced pair, the null and the centre field | −5e-14 mm; 7e-15 of one coil's own | ✔ |
| G-DIV: dB_r/dr ÷ dB_z/dz at the centre (∇·B = 0 gives −½) | −0.50001 | ✔ |
| G-FAR: the far boundary at 1 m against 2 m, the gradient | −2e-7 | ✔ |
| G-WAVE: regenerated AHt / AHb min, mean, max and largest difference against `sim/ah_steady_cusp_results.json`, 0 and 22 mF | within 4e-14 A-turns; both coils unipolar | ✔ |

**Cross-checks** (not gates):
- **One coil's inductance:** 0.998 mH with its rod, against the record's 1.01 mH (`sim/magnetic_doubler.py` AH r160,
  −1.2 %). Without the rod 0.177 mH, so the rod's apparent μ is 5.6, as in `sim/em-register-findings.md`:88 ("about
  5–6").
- **The gradient per A-turn** against the register's RA run (`sim/em_register_results.json`: 0.388 T/m at 1022
  A-turns with all four windings): 0.3769 against 0.3795 mT/m (−0.7 %). The aiding cone pair adds no gradient at the
  centre by symmetry [OC].
- **The uniform-field boundary:** air-cored, ψ = B r²/2 on the far boundary returns 1.000000 B at the centre.

## 2. The pair as built
At 300 A-turns per coil, balanced (`docs/figures/ah-null.png` (a)–(c)):
- **On the axis:** B_z rises from the null through the seats into the rods. It peaks at 118 mT in each rod's middle
  (|z| 51) and falls to 17.5 mT at the rods' end faces (|z| 30.7, 72.0): the flux leaves through the rods' sides near
  their ends [OC].
- **The gradient at the null:** 0.1131 T/m; each coil contributes 0.188 mT/m per A-turn. The rods raise it ×4.83 over
  the same coils alone (0.0234 T/m).
- **Radially:** dB_r/dr = −0.0565 T/m, −½ the axial [OC]. B_z is zero over the whole equatorial plane (symmetry) [OC].
- **The field in the vessel:**

| point | \|B\| | against the linear cusp |
|:--|--:|--:|
| equatorial plane, r 5 mm | 0.273 mT | −3 % of ½G·r |
| r 10 mm | 0.497 mT | −12 % |
| r 20 mm | 0.702 mT | −38 % |
| r 23.5 mm (the inner wall) | 0.705 mT | |
| axis, \|z\| 5 mm | 0.591 mT | +5 % of G·z |
| \|z\| 10 mm | 1.358 mT | +20 % |
| \|z\| 20 mm | 5.018 mT | ×2.2 |
| \|z\| 23.5 mm (the poles' inner wall) | 8.26 mT | |

- **So the cusp is linear only within a few millimetres** [OC]:
  - along the axis it steepens toward the rods' faces, 5.7 mm beyond the glass;
  - across the equator it flattens: 0.69–0.71 mT from r 18 mm to the wall.

## 3. The null against the imbalance
- **First order** [OC]: z_null ≈ −ℓ (NI_top − NI_bottom) / (NI_top + NI_bottom), with ℓ = B_z(0) / B_z′(0) of one
  coil = 15.23 mm. At 300 A-turns mean: 25.4 µm and 2.87 µT at the centre per A-turn of difference.

| top − bottom (300 mean) | z_null | B at the centre | gradient at the null |
|--:|--:|--:|--:|
| 0 | 0 | 0 | 0.1131 T/m |
| 5 A-turns | −0.127 mm | 14.3 µT | 0.1131 |
| 10 | −0.254 | 28.7 | 0.1131 |
| 17 | −0.432 | 48.8 | 0.1130 |
| 17.4 (the bypass's largest) | −0.441 | 49.9 | 0.1130 |
| 34 | −0.864 | 97.6 | 0.1130 |

- **With the 22 mF bypass (PROPOSED),** over the regenerated 120 Hz cycle:
  - the null moves −0.43 to +0.44 mm (0.87 mm p-p);
  - the centre field peaks at 49.9 µT (33 µT rms);
  - the gradient stays at 0.1123–0.1135 T/m (±0.5 %).
- **Without it** (today's circuit), each coil carries its branch's 139–449 A-turns, top and bottom peaking in turn:
  - the null swings −6.36 to +6.32 mm (12.7 mm p-p) once per cycle. It is more than 3 mm off centre 92 % of the time,
    and more than 5 mm off 53 % (figure (e));
  - at the largest difference (top 324, bottom 140 A-turns) it sits 6.35 mm toward the bottom coil, where the
    gradient is 0.085 T/m;
  - the centre field reaches 0.53 mT (0.47 mT rms); the gradient runs 0.084–0.139 T/m (mean 0.105).
- **Against the electric field:** the rings' DC field varies 4.4 % within ±5 mm of the centre along the axis
  (`docs/rings-design.md` §5). Bypassed, the null stays within ±0.44 mm; unbypassed, it leaves that ±5 mm every
  cycle [OC].

## 4. The rods
| A-turns per coil (both) | peak in the rod | centre, on the axis | end face, on the axis | 99th percentile |
|--:|--:|--:|--:|--:|
| 300 | 0.121 T | 0.118 T | 0.018 T | 0.120 T |
| 449 | 0.181 | 0.177 | 0.026 | 0.180 |
| 600 | 0.242 | 0.236 | 0.035 | 0.241 |

- **Where the peak sits:** at the rod's surface at mid-length (r 6.0, |z| 51.5 mm). Across the middle the field is
  nearly uniform, 0.118 T on the axis to 0.121 T at the surface [OC].
- **The end corners:** a sharp corner in a linear medium concentrates the field without limit as the cells shrink, over
  a vanishing volume. At 0.125 mm cells the outer corner reads 0.125 T (+2.9 % on the last halving). The peak above is
  the rod's bulk, 1 mm off each end, which converges (+0.2 %, then +0.1 %) [IR].
- **Where the rod reaches its limits** (linear, both coils at the same A-turns):
  - 0.30 T, the register's G-AH-SAT limit (`sim/em-register-predictions.md`:74; no basis recorded) [RH]: 743 A-turns;
  - 0.38 T, B_sat at 100 °C (`presets/electromagnets-RA.json` AH_rod): 941;
  - 0.49 T, B_sat at 25 °C (Fair-Rite 77, datasheet-class) [IR]: 1214;
  - the rod's centre on the axis lags by 2.6 % (762 / 966 / 1245).
- **The record's "about 600 A-turns"** is `sim/magnetic_doubler.py`:51, AT_ROD_LIMIT = 1022 × 0.30 / 0.51.
  - It scales the register's RA run: 0.51 T at 1022 A-turns (`sim/em_register_results.json` ra.magnetics.a).
  - That run carried the cone windings L_TC / L_BC in the same chain as the AH, and their flux adds in the rods
    (`sim/em_ra.py` sums every turn). Per A-turn of the AH it gives 0.501 mT, against the AH alone's 0.404 (×1.24).
  - For the locked hub's AH alone, the 0.30 T point is 743 A-turns: the record's 600 is about 19 % conservative [OC
    model, RH limit].
- **The margin:** with the bypass the rods sit steadily at 0.121–0.124 T, 2.4× under 0.30 T. Without it they peak at
  0.182 T at the 449 A-turn peaks, 1.6× under.
- **Shape, not μ, sets the rod's field:** μ_r 1000 / 3000 move it −0.6 / +0.2 %. A rod 3.4 diameters long is
  demagnetisation-limited [OC]. The linear numbers therefore hold up to the B–H knee. Near B_sat μ falls, so the
  A-turns above are where saturation starts, not a margin to run at [IR].

## 5. The shaft
The record: non-magnetic (`presets/hub-locked.json` shaft, "magnetic": false; "a non-magnetic shaft is recommended
[IR]", `docs/ledger/DCCREG-design-ledger.md`:205). Against mild-steel halves [IR]: μ_r 300–1000, solid r 15 mm from
|z| 72 to 300 mm with the flanges r 32 × 8 mm at |z| 72–80, touching the rods' outer faces unless a gap is stated.

| shaft halves (top / bottom) | gradient | null, balanced | null, 17 A-turns apart | rod: peak / centre | steel peak |
|:--|--:|--:|--:|--:|--:|
| non-magnetic (the record) | 0.113 T/m | 0 | −0.44 mm | 0.121 / 0.118 T | — |
| μ 300 / μ 300 | 0.207 (+83 %) | 0 | −0.51 | 0.371 / 0.236 | 0.77 T |
| μ 1000 / μ 1000 | 0.209 (+85 %) | 0 | −0.52 | 0.353 / 0.239 | 0.69 |
| μ 1000 / μ 1000, a 1 mm gap at each rod | 0.156 (+38 %) | 0 | −0.49 | 0.178 / 0.170 | 0.10 |
| μ 1000 / non-magnetic | 0.166 (+47 %) | −5.81 mm | −6.27 | 0.360 / 0.244 | 0.70 |
| μ 1000 / μ 300 | 0.208 (+84 %) | −0.13 | −0.65 | 0.353 / 0.239 | 0.77 |
| μ 1000, seated / a 1 mm gap | 0.183 (+62 %) | −2.79 | −3.29 | 0.357 / 0.242 | 0.69 |
| μ 1000, seated / a 0.1 mm gap | 0.203 (+79 %) | −0.61 | −1.12 | 0.354 / 0.240 | 0.69 |
| austenitic μ 1.05 / non-magnetic | 0.113 (+0.3 %) | −0.06 | −0.50 | 0.122 / 0.119 | 0.07 |
| cold-worked austenitic μ 2 / non-magnetic | 0.119 (+5 %) | −0.88 | −1.32 | 0.136 / 0.133 | 0.13 |

- **Symmetric halves cannot move the balanced null** (mirror symmetry) [OC]. They nearly double the gradient by giving
  each rod's outer face a low-reluctance return; behind a 1 mm gap the gain is 38 %.
  - The null's lever grows from 15.2 to 17.8 mm, so the same 17 A-turns move it 0.52 mm instead of 0.44.
- **The rods pay for it:** their flux doubles.
  - At 300 A-turns the rod's centre runs at 0.24 T and its end near the steel at 0.35–0.37 T. That is past the 0.30 T
    limit, which the rod then reaches at 255 A-turns, and at B_sat(100 °C) from about 320.
  - At 0.125 mm cells the rod's peak and 99th percentile move −1 % and +0.1 % (μ 1000); the contact corner grows
    (0.60 → 0.76 T), a corner effect as in §4.
  - The linear gain is an upper bound: the contact would saturate [IR].
  - The steel itself peaks at 0.7–0.8 T at the contact (a mesh-dependent corner), far below mild steel's
    saturation [IR].
- **Any difference between the halves moves the null:** 5.8 mm if one half is steel; 2.8 mm for a 1 mm difference in
  how the halves seat against their rods, 0.6 mm for 0.1 mm; 0.13 mm for μ 1000 against 300.
  - These are build tolerances of a steel shaft, and all but the last exceed the bypassed imbalance's 0.44 mm.
  - The asymmetric shifts move under 0.5 % at 0.125 mm cells (`shaft[].z_null_balanced_0p125_mm`).
- **"Non-magnetic" needs a number:**
  - one half at μ_r 1.05 moves the null 0.06 mm, an eighth of the bypassed imbalance;
  - at μ_r 2 (heavily cold-worked austenitic [RH]), 0.9 mm;
  - so annealed austenitic stainless or titanium, μ_r ≲ 1.05 [IR].
- **At 120 Hz:** a steel shaft's skin depth is 0.6–1.0 mm (μ_r 1000–300, ρ ≈ 1.5e-7 Ω·m [IR]). The unbypassed ripple
  would meet an eddy-current shield, not the DC permeability, so these rows describe the steady, bypassed field [OC].
- **Verdict:** the non-magnetic shaft stands [IR].
  - It keeps the null independent of the halves' seating and permeability.
  - It keeps the rods 2.4× under 0.30 T.
  - It leaves the gradient to the AH alone.
  - The record's own reason (stray flux and eddy currents in the bearings, `sim/tube-shaft-findings.md` §2) adds to
    these.

## 6. Sensitivity
- **The ferrite's permeability** (both rods μ_r 1000 / 2000 / 3000):
  - the gradient 0.1125 / 0.1131 / 0.1133 T/m (−0.5 / 0 / +0.2 %);
  - the lever 15.22–15.23 mm; the rod's peak 0.120–0.121 T.
- **Two rods that differ:** μ_r 2400 / 1600 (±20 %) moves the null 0.016 mm; 3000 / 1000 moves it 0.052 mm, toward the
  lower μ.
- **A misplaced coil** (the top side, 0.5 mm outward):
  - the winding alone, on its rod: the null moves 0.081 mm toward it, the gradient −0.7 %;
  - the whole AH, rod and winding: 0.250 mm, half the shift, since the null sits midway between identical sources
    [OC]; the gradient −2.2 %.
- **A uniform external field** (not in the brief; the same solver, ψ = B r²/2 on the far boundary):
  - axially the rods concentrate it ×1.18 at the centre, so 10 µT moves the null 0.104 mm;
  - transversely, 10 µT moves it about 0.18 mm off the axis (2B/G from the radial gradient; the rods' transverse
    effect not computed) [RH];
  - on the vertical axis the earth's vertical component (about 35–50 µT at mid-latitudes [IR]) moves the null
    0.35–0.5 mm, and its horizontal component (15–25 µT) about 0.25–0.45 mm sideways. That is as much as the bypassed
    imbalance; the site and the coils' polarity set the signs.

## Caveats
- **[IR] the linear ferrite:** μ_r 2000 (the register's mu_i, itself [RH] there until the 77 datasheet is read in), no
  B–H curve, hysteresis or temperature. The rod's field barely depends on μ (§6), so the linear numbers hold to the
  knee; the saturation A-turns are onsets.
- **[IR] B_sat 0.49 T at 25 °C** is datasheet-class and not in the repository; 0.38 T at 100 °C is the register's.
- **[RH] the 0.30 T limit:** `sim/em-register-predictions.md`:74 sets it without a basis.
- **[IR] the winding as a uniform current density.**
  - The 160 turns' layout was not recorded when this ran: `presets/hub-locked.json` gave the window as "variant (a)'s:
    2 layers of 1.6 mm pitch", which holds 50 turns of the 1.6 mm wire. Since settled (`sim/hub-thermal-findings.md`
    §1): 160 turns of 0.80 mm wire in 4 layers fill the same window, 0.333 Ω. The field here depends only on the
    A-turns and the window.
  - The wound coil's higher resistance drives 294 A-turns instead of 300 with the bypass, so the gradient is 0.111 T/m
    rather than 0.113 (−2 %) [OC: linear].
  - The discrete turns, the helix and the leads are not modelled; each breaks the axisymmetry slightly.
- **[IR] axisymmetry:** only bodies of revolution are modelled. Not modelled: the pumps' iron on the shaft halves
  (utrons, bridges), the bearings, and anything magnetic in the frame.
- **[IR] the steel shaft:** linear, solid (no bore), out to |z| 300 mm; the shaft beyond and its 120 Hz eddy currents
  are not modelled.
- **[OC] quasi-static:** the ferrite's skin depth at 120 Hz is about 2 m, so the field follows the currents.
- **The currents are the pick's only** (g 0.5 / 6 bridges / 1200 rpm relative), regenerated from the record's deck.
  Another operating point changes the A-turns and so the null.
