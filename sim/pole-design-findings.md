# Reluctance pole pair for the magnetic doubler — findings

**Goal.** Design the C-EM / utron poles for a high inductance swing so the magnetic doubler (wound utrons → AH pair,
`sim/hub-drive-findings.md`) grows and holds the AH at its target, then optimise wherever possible.

**Designer's inputs:**
- in air for now, but judge vacuum too;
- try a 0.5 mm gap and give the loss for 1.0 mm;
- the envelope may change if that gives a positive feasibility result.

**Tools:**
- `sim/pole_fd2d.py`: a new 2-D magnetostatic finite-volume solver for A_z in the plane of rotation, unrolled at the
  gap radius, periodic over 120°, with linear iron μ_r 3000 [RH].
- `sim/pole_design.py`: the staged search and sizing.
- `sim/magnetic_doubler.py`: the pump circuit, extended to take a tabulated L(θ) shape, the pump frequency and
  frequency-scaled node snubbers.
- Drawings: `docs/figures/pole-pair-flux-g0p5.png` and `docs/figures/pole-pair-flux-g1p0.png`, from
  `docs/make_pole_drawing.py`.
- Chart: `docs/figures/utron-size-vs-gain.png`, from `docs/make_variants_chart.py` (§6, §7).
- Geometry (§8): `sim/utron_profile.py` (every dimension of the built utron and bridge), the solids in
  `sim/tube_geometry.py --rel wound`, and the detail drawing `docs/figures/utron-core-detail.png` from
  `docs/make_utron_drawing.py`.

Results: `sim/pole_design_{p1,p1b,p3,final,real,kick,recheck,variants,variants_op}.json`. The p1 T-family rows are
superseded by p1b, after a tooth-parity fix.

**Copper correction (§7).** Up to §6 the coil's mean turn was 13–26 % short. The variant screen and its operating
points (`pole_design_variants*.json`) were re-run with the corrected turn, and §7 holds those numbers. The earlier
stages' JSONs (p1 .. recheck) and the copper numbers in §2–§6 still carry the short turn.

## 1. Topology (what changed)

- **Old:** the C-EM was an axial C-core with jaws 60 mm apart, and the utron block left a 7 mm gap on each side.
  Leakage dominated, so the ratio was about 1.15.
- **New:**
  - The **utron is a wound U-core** (two radial tips, the coil around its back iron) on the **rotor**.
  - The **C-EMs become passive laminated bridges**, 6 per side on the stator, with no coils.
  - The air gap is **radial**, so the bearings set it.
- **A/B antiphase:** the B side is offset half a bridge pitch (30°). The 3 utrons per side align together (120° apart).

**Self-check:** aligned L comes out 1.21 × the two-gap analytic value (gap fringing plus slot leakage). The mesh is
converged to 0.5 %.

## 2. Screening and refinement (P1, P1b)

- **104 candidates** at 13 angles each. Every one gets its L(θ) fitted as a cosine series, then the pump circuit gives
  its true gain per cycle z, with copper in every coil and τ_fixed 0.5 s for La/Lb [RH].
- **Discrete bridges (S) beat a toothed ring (T).**
  - The ring's continuous iron caps its ratio at 3.1, even at 0.5 mm with 12–36 teeth.
  - None of the ring designs fit the radial space.
- **The gap radius is the biggest lever.** At 130 mm the coil's return side doesn't fit above the sleeve once the slot
  is deeper than about 45 mm, and the 60° pitch limits the utron width.
  - Moving to **r_g 165 mm** fixes both.
  - The passive bridges reach only r ≈ 186 mm, far inside the old C-EM envelope (r 265 mm).
- **Winner, the same geometry at both gaps:** tips 20 mm, slot 50 × 60 mm, back iron 20 mm, bridges 90 × 20 mm.

| gap | κ_L (2-D, with end corrections) | τ = L/R (stack 70 mm) | gain per cycle z (60 Hz) |
|:--|--:|--:|--:|
| **0.5 mm** | **11.6** | 0.54 s | **1.30** |
| 1.0 mm | 6.7 | 0.31 s | 1.19 |

- **Bridge length:** 70 mm is worse (z 1.20) and 100 mm is equal (1.31), so l_b ≈ utron width (90 mm) is the
  optimum.
- **Stack length:** 70 / 100 / 140 mm give z 1.30 / 1.31 / 1.32. I chose 70 mm, which makes the section about
  184 mm long per side including end turns.

## 3. Sizing the operating point (P3, final)

**AH target:** 450 ampere-turns peak, against the rod limit of about 600, with the AH rewound to 160 turns [RH].

**Three optimisations found:**
1. **Saturation level.** The level is set by a deliberately narrow **neck** in the utron back iron. Heat ∝ Ψ_s², so
   the neck is sized to the AH target and no larger. It comes to 2.2 mm at 0.5 mm gap and 3.6 mm at 1.0 mm.
   - Mechanically that is a 6 mm bridge over 37 % / 60 % of the stack, with the rest punched out of the laminations.
2. **Utron turns.** Copper heat at a fixed AH current grows with N_u², but too few turns lets the AH coil's own
   inductance and resistance stop the pump. The optimum is about 400 turns (0.5 mm) and 600 turns (1.0 mm).
3. **Coupling inductors.** La = Lb = 0.6 × L_max beats the electrostatic pump's 1.1 (+0.03 in z, −35 % fixed copper).

## 4. Real diodes: start-up is the catch

- **With silicon diodes (≈ 0.55 V) and a small seed (3 % of Ψ_s), the low-turn designs do not start.**
  - While growing, their winding voltages are only a few volts, so the diode drop wins.
  - From the same small seed you need ≥ 1000 turns with Si, or ≥ 800 with Schottky. That costs 59–94 W.
- **Once kicked to ≥ 8–10 % of Ψ_s, the low-turn designs run with Si diodes.** The diode drop then costs only about
  2 W. A kick of 0.23 A in the utron group (about 35 mJ) is enough.
- **The kick source is open.** Options: a one-time start pulse (a capacitor or battery with a push-button, the only
  switch and used only at start-up), a small PM bias in the utron back iron (untested), or a pulse from the
  electrostatic side.

## 5. Design points and the 1.0 mm penalty

*Short mean turn (§7): copper loss and mass here are 13–26 % low and τ is high. The corrected 0.5 vs 1.0 mm comparison
is in §7.*

Si diodes, kicked start, AH 450 ampere-turns, 600 rpm relative, stack 70 mm. Turn counts come from the systematic rule
of §6: the utron group's resistance set to m × the AH coil's, with m 4.5 / 6.5 / 9. The table shows the lowest-power
one that holds the target (`sim/pole_design_recheck.json`).

| | **0.5 mm** | 1.0 mm | 1.0 mm, from a small seed (no kick) |
|:--|--:|--:|--:|
| utron turns (3 per group, wire) | 340 (4.0 mm²) | 410 (3.3 mm²) | 1000 Si / 800 Schottky |
| utron group L | 0.65 H | 0.54 H | — |
| utron current / peak winding voltage | 0.9–2.8 A / 80 V | 1.0–2.8 A / 131 V | — / 690 V |
| **total power** (copper + diodes + AH + iron) | **14.5 W** | **20.3 W** | 99 W Si / 65 W Schottky |
| heat per utron coil | 1.4 W | 2.2 W | 13.3 W / 8.6 W |
| fixed inductors / AH / diodes / iron | 1.7 / 1.9 / 1.9 / 0.7 W | 1.7 / 2.1 / 2.0 / 1.1 W | — |
| coil temperature, air / vacuum (radiation only) | 41 / 46 °C | 42 / 50 °C | — |
| minimum start kick | 15 % of Ψ_s (58 mJ) | 15 % (48 mJ) | (small seed) |
| AH share of the power | 12.9 % | 10.1 % | ~2 % |
| linear gain margin z | 1.30 | 1.19 | — |

- **The 1.0 mm penalty: about 1.4× the power for the same AH** (14.5 → 20.3 W), more turns (410 instead of 340), and
  a lower gain margin (1.30 → 1.19).
- **Correction.** An earlier version of this section reported 18.6 W against 38.3 W, i.e. 2.1×. Two things inflated it:
  - its 1.0 mm turn search started at 600 turns;
  - its first screen used a 0.1 % seed, in which even the ideal diodes' few-mV drop stalls growth.

  The systematic rule with a kick finds the real minimum. The 400 / 600-turn points of `pole_design_kick.json` still
  hold; they just aren't the minimum.
- **Fewer turns means a larger kick** (15 % instead of 10 %), because the winding voltage is lower.
- **Without a start kick** both gaps cost about the same (≈ 90 W with Si), because start-up sets the turn count.
- **Air and vacuum both work.** The design points sit far below the cooling limits: about 87 W per coil in air and
  about 40 W per coil at 155 °C in vacuum (radiation only).
- **Masses:** 3.4 kg of copper per utron coil, 2.25 kg of iron per utron, 0.96 kg per bridge (stack 70 mm).
  - The copper is there for τ, not current: J ≈ 0.6 A/mm².
  - Aluminium would save about 2/3 of the winding mass for about 0.6 × τ.

## 6. Smaller utrons: 12 bridges and 1200 rpm

**Question.** How small can the utron get if the pump frequency goes up?
- 12 stator bridges per side instead of 6 (30° pitch; 24 bridges in total);
- or 1200 rpm relative instead of 600 (600 rpm each way through the 1 : −1 gear);
- or both.

**Method** (`python3 sim/pole_design.py variants`, `variants_ext`, `variants_op`):
- **Designs:**
  - L(θ) doesn't depend on speed, so the 92 six-bridge designs of P1b were reused;
  - 84 new 12-bridge designs, and 154 small 6-bridge designs at the 12-bridge utron sizes (tips 8–14 mm, slots
    15–30 mm wide), so both bridge counts were compared on the same utrons;
  - all at a 100 mm stack, at both gaps.
- **Gain:** each design's gain z comes from the pump circuit at its own frequency, f = bridges × rpm / 60.
- **Snubber check.** The node snubbers are scaled with frequency (L·C·f² and R/√(L/C) held at their validated 60 Hz
  values). That keeps z to ±0.002 when their capacitance is halved or quartered. The old fixed 10 nF would have inflated
  z to 1.47 at 240 Hz, with an artificial 213 W in the snubbers.

**Lightest utron (copper + iron, kg) reaching each gain.** *These two tables use the short mean turn and are superseded
by §7.*

| gap | bridges / rpm | f | z ≥ 1.10 | z ≥ 1.15 | **z ≥ 1.20** | z ≥ 1.25 | best z |
|:--|:--|--:|--:|--:|--:|--:|--:|
| 0.5 mm | 6 / 600 (today) | 60 Hz | 2.20 | 3.11 | **3.40** | 4.01 | 1.31 |
| 0.5 mm | 6 / 1200 | 120 Hz | 1.54 | 1.75 | **1.97** | 3.11 | 1.36 |
| 0.5 mm | 12 / 600 | 120 Hz | 1.55 | 2.56 | — | — | 1.16 |
| 0.5 mm | 12 / 1200 | 240 Hz | 1.15 | 1.34 | **1.55** | — | 1.21 |
| 1.0 mm | 6 / 600 | 60 Hz | 4.01 | 4.67 | **7.31** | — | 1.20 |
| 1.0 mm | 6 / 1200 | 120 Hz | 2.83 | 3.40 | **4.03** | 5.01 | 1.26 |
| 1.0 mm | 12 / 600 | 120 Hz | — | — | — | — | 1.01 |
| 1.0 mm | 12 / 1200 | 240 Hz | — | — | — | — | 1.07 |

- **Frequency is the lever.** At a fixed margin, each doubling of the pump frequency cuts the utron mass by about 40 %.
  - At 0.5 mm and z ≥ 1.20: 3.40 → 1.97 → 1.55 kg.
  - At 1.0 mm: 7.31 → 4.03 kg.
  - That matches the earlier scaling estimate of about 0.8 × linear size per doubling.
- **For the same utron, bridges and speed are interchangeable.** 12 bridges lower κ_L by at most 0.5, and at equal
  frequency the gains agree within about 0.02. Example: tip 10, slot 25 × 30 gives z 1.12 with 6 bridges at
  1200 rpm and 1.13 with 12 bridges at 600 rpm, both at 120 Hz.
- **12 bridges cap the utron width** at ≤ 0.53 × the 30° pitch (36 mm at r 130, 46 mm at r 165), so the large,
  high-margin utrons are no longer possible.
  - They pay off only together with 1200 rpm, and only at 0.5 mm.
  - **At 1.0 mm no 12-bridge design even reaches z 1.10.**

**Operating points of the winners.** AH 450 ampere-turns, Si diodes, kicked start, best of the three turn counts:

| | utron (geometry) | turns | total power | heat per coil | coil °C air / vac | iron | kick | V_pk |
|:--|:--|--:|--:|--:|:--|--:|--:|--:|
| 0.5 mm, 6 / 600 | 3.40 kg (r 130, tip 18, slot 30 × 40) | 240 | 18.2 W | 2.0 W | 44 / 57 | 1.0 W | 20 % (68 mJ) | 92 V |
| **0.5 mm, 6 / 1200** | **1.97 kg** (r 165, tip 12, slot 30 × 30) | 220 | 18.8 W | 2.2 W | 46 / 63 | 1.1 W | 20 % (42 mJ) | 101 V |
| **0.5 mm, 12 / 1200** | **1.55 kg** (r 165, tip 10, slot 25 × 30) | 160 | 16.2 W | 1.6 W | 45 / 59 | 2.0 W | 15 % (10 mJ) | 117 V |
| 1.0 mm, 6 / 600 | 7.31 kg (r 165, tip 20, slot 50 × 60) | 310 | 15.7 W | 1.6 W | 41 / 46 | 0.9 W | 20 % (70 mJ) | 104 V |
| **1.0 mm, 6 / 1200** | **4.03 kg** (r 165, tip 18, slot 40 × 40) | 230 | 14.9 W | 1.5 W | 43 / 51 | 1.1 W | 20 % (35 mJ) | 103 V |

- **Shrinking the utron does not cost power.** At the best turn count every winner needs 15–19 W. The heat is set by
  the AH coil's resistance and the current it needs, not by the utron's size.
- **Stator iron per side:** 5.5 kg (6 / 600, 3.40 kg utron), 3.0 kg (6 / 1200), 4.1 kg (12 / 1200: 12 smaller
  bridges).
- **What 1200 rpm relative costs:**
  - **Centrifugal load on the rotor coils:** about 52 g instead of 13 g at r ≈ 130 mm. That is 0.4–0.5 kN per coil,
    so the coils need banding or a retaining ring.
  - **Electrostatic pump:** its power doubles (power ∝ frequency at fixed voltage): about 18 W with diodes only
    instead of 9 W. The bicone dumps rise to about 120–135 per second per side.
  - **Iron at 240 Hz** (12 / 1200): 1.0 W per side. The 0.35 mm laminations are still below the skin depth (about
    0.45 mm), but 0.2 mm is preferred.
  - **Air windage grows with speed cubed.** It is not modelled here.

**Recommendation:**
- **At 0.5 mm, go to 1200 rpm relative.**
  - With 6 bridges per side (keeping today's 12-C-EM count), the utron shrinks from 3.4 to about 2.0 kg at the same
    margin and the same power.
  - With 12 bridges per side, it reaches about 1.55 kg.
- **At 1.0 mm,** 1200 rpm with 6 bridges halves the utron (7.3 → 4.0 kg). 12 bridges don't work there.

**Open items:**
- the turn rule is coarse (m 4.5 / 6.5 / 9);
- the stack is fixed at 100 mm;
- the start kick is 15–20 % of Ψ_s (10–70 mJ);
- everything else carries the caveats below.

## 7. Correction: the coil's mean turn was 13–26 % short

**Found while drawing the coil (§8).**
- The copper model counted the four corners of each turn as π·(clr + h_c/2) + 4·clr.
- A turn at mid-build, around the back iron, has 2π·(clr + h_c/2) in its corners [OC].
- So the mean turn, R, the copper mass and the copper loss were low, and τ = L/R was high:
  - the drawn utron (tip 14, slot 30 × 30, back iron 14): 277.6 → 319.1 mm (+15 %);
  - deeper slots more (slot depth 60: +26 %).
- **Cross-check:** the winding solid's volume divided by its section gives 315.106 mm for the tip-12 / back-iron-12
  coil. That is exactly the corrected formula.

**Fix:**
- One helper, `pole_fd2d.mean_turn_mm`, is used by the characterisation, the stack rescale and the masses.
- L(θ) doesn't depend on the copper. So `python3 sim/pole_design.py turnfix` only redoes R, τ, the copper mass and
  the circuit z, for all 330 variant designs at both speeds. The short-turn values are kept in each row under
  `short_turn`.
- `variants_op` then re-sizes the winners.

**Lightest utron (kg, 100 mm stack) at each gain, corrected:**

| gap | bridges / rpm | f | z ≥ 1.10 | z ≥ 1.15 | **z ≥ 1.20** | z ≥ 1.25 | best z | was (z ≥ 1.20) |
|:--|:--|--:|--:|--:|--:|--:|--:|--:|
| 0.5 mm | 6 / 600 | 60 Hz | 3.09 | 3.37 | **4.08** | 5.12 | 1.30 | 3.40 |
| 0.5 mm | 6 / 1200 | 120 Hz | 1.66 | 2.09 | **2.34** | 3.37 | 1.35 | 1.97 |
| 0.5 mm | 12 / 600 | 120 Hz | 1.66 | — | — | — | 1.14 | — |
| 0.5 mm | 12 / 1200 | 240 Hz | 1.21 | 1.44 | — | — | 1.196 | 1.55 |
| 1.0 mm | 6 / 600 | 60 Hz | 4.72 | 5.47 | — | — | 1.18 | 7.31 |
| 1.0 mm | 6 / 1200 | 120 Hz | 3.37 | 3.97 | **4.72** | — | 1.24 | 4.03 |
| 1.0 mm | 12 / 600, 12 / 1200 | | — | — | — | — | 0.99 / 1.05 | — |

**What the correction changes:**
- **The pick moves.** At 0.5 mm, 6 bridges and 1200 rpm, the lightest utron with z ≥ 1.20 is now 2.34 kg: r_g 130,
  tip 14, slot 30 × 30.
  - §6's pick (r_g 165, tip 12, slot 30 × 30) falls to z 1.187 at 2.11 kg.
- **12 bridges no longer reach the 1.20 margin.** The best is z 1.196, and §6's 1.55 kg pick is at 1.192.
- **At 1.0 mm and 600 rpm, nothing reaches 1.20** (best 1.18).
- **Frequency is still the lever:** at 0.5 mm, 4.08 kg (60 Hz) against 2.34 kg (120 Hz).

**Operating points, corrected** (AH 450 ampere-turns, Si diodes, kicked start, best of the three turn counts;
`sim/pole_design_variants_op.json`):

| | utron (geometry) | turns | total power | heat per coil | coil °C air / vac | iron | kick | V_pk |
|:--|:--|--:|--:|--:|:--|--:|--:|--:|
| 0.5 mm, 6 / 600 | 4.08 kg (r 130, tip 16, slot 40 × 40) | 260 | 18.9 W | 2.1 W | 44 / 55 | 1.0 W | 20 % | 95 V |
| **0.5 mm, 6 / 1200** | **2.34 kg** (r 130, tip 14, slot 30 × 30) | **200** | **18.8 W** | 2.15 W | 46 / 63 | 1.25 W | 20 % (38 mJ) | 101 V |
| 1.0 mm, 6 / 1200 | 4.72 kg (r 165, tip 20, slot 40 × 40) | 210 | 14.5 W | 1.5 W | 42 / 50 | 1.0 W | 20 % | 94 V |

- **Power stays at 15–19 W.** The AH coil's resistance and current still set the heat.
- **1.0 mm vs 0.5 mm at 1200 rpm:** the cost of the wider gap is mass, not power. It needs twice the utron
  (4.72 against 2.34 kg). Its bigger slot carries more copper (τ 0.17 s), so it holds the AH for 14.5 W against
  18.8 W.
  - At 600 rpm the 1.0 mm gap doesn't reach the 1.20 margin at all.
  - §5's "1.4× the power" compared one fixed geometry at 600 rpm with the short turn. It no longer describes the
    choice.

## 8. The setup as built in the solids

**Build:** `python3 sim/tube_geometry.py --rel wound`, for the §7 pick (0.5 mm, 6 bridges, 1200 rpm).
- **Outputs** in `docs/geometry/tube/tube-r150-n8-wound-g0p5-6br.*`:
  - an instanced STEP: 152 solids from 30 prototypes, read back 152 / 152 (each utron's two half-cores are separate
    solids, 12.0 mm apart across the air break);
  - the parts list;
  - an arrangement section with a detail of reluctance A;
  - plan cuts through both reluctance sections;
  - 3-D stills rendered from the STEP itself (`-3d-{cutaway,half,reluctance,plan,exploded}.png`) and a GLB, from
    `sim/step_to_glb.py` and `tools/step-viewer/` (three.js in headless Chromium; the same scene with orbit controls is
    `tools/step-viewer/viewer.html`).
- **Checks:** `sim/tube_geometry_wound_results.json`.
- **Source of the dimensions:** every utron and bridge dimension comes from `sim/utron_profile.py`, the same numbers
  that draw `docs/figures/utron-core-detail.png`.
- **The default build is unchanged:** a re-run of the C-EM tube gives the same layout, the same 307 parts and the
  same clash, sweep, clocking-gap and C-EM fit results. (Its committed C_max is 1.00064 × today's, which is air's
  ε_r: that results file predates the tube's vacuum default.)

**Arrangement** (the diode build: no Cx islands, no clocking decks):
- **Size:** 802 mm long, vane OD 300 mm, cage OD 332 mm.
- **From the bottom (A):**
  1. end bearing (frame);
  2. reluctance A (162 mm);
  3. Ca|reluctance bearing;
  4. 8 Ca plates;
  5. C1 (8 stator + 8 rotor vanes, 3 mm vacuum gaps);
  6. hub-face bearing;
  7. hub (bicone + AH / C_R placeholder, 120 mm);
  8. B, mirrored.
- **Three bodies:**
  - **Rotor:** shaft halves and flanges, bicone, sleeve, rotor vanes, and the utrons on two G10 carrier discs per side.
  - **Counter-rotor, geared 1 : −1:**
    - the stator cage, now one tube across the hub;
    - stator vanes, Ca / Cb plates;
    - the hub-face and Ca|reluctance spiders;
    - the bridges in their G10 rings.
  - **Frame:** the two end bearings.
  - The four inner bearings run at the relative 1200 rpm. The gear or belt is not drawn.
- **Reluctance section, per side:**
  - 3 utrons at 0 / 120 / 240° on the rotor; 6 bridges at a 60° pitch on the counter-rotor.
  - B's bridges are offset 30°, so at rotor angle 0 A is aligned and B is unaligned (the doubler's antiphase).
  - At r_g 130 the whole section (bridge ring OD 313 mm) fits inside the vane cage's diameter.
- **Checks:**
  - 457 solid pairs, 0 clashes; 0 rotor-sweep hits;
  - air gap aligned 0.500 mm on both sides (B after turning 30°), unaligned 9.74 mm;
  - winding to iron 1.000 mm (core and neck strip); to the wedge 0.10, the cheeks 1.0, the carrier discs 2.7 and the
    bridge ring 2.7 mm;
  - tip faces at r 130.000.

**The utron (detail drawing):**
- **Core:** a split U-core. Two L-shaped M235-35A half-cores (tip 14 + half the back iron), stacked 100 mm. The tip
  faces are on the gap arc r 130 (parallel-sided tips, so the slot keeps its 30 mm for the coil).
- **Neck** (sets Ψ_s):
  - an 80 % NiFe strip, 2.97 × 100 mm, under the back iron: 0.223 mWb at 0.75 T [RH], equal to the operating
    point's 1.48 mm of SiFe at 1.5 T;
  - the half-cores sit on the strip, parted by a 12 mm G10-filled air break, so the flux crosses the strip edge-on,
    in the plane of the laminations;
  - it replaces §3's necked laminations over part of the stack: there the flux would cross between laminations,
    normal to the sheets (low permeability, eddy loss) [RH].
- **Coil:**
  - 200 turns of 1.89 mm² (Ø 1.55 bare), 50 % fill, 28 × 27 mm per side, mean turn 319 mm;
  - rounded end turns (R 28 outside, R 1 inside), 156 mm long over them;
  - wound on a 1 mm G10 former. The strip, the spacer and the half-cores slide into it from both sides.
  - R 0.58 Ω, L 81 / 9.4 mH per coil (κ 8.6, τ 0.140 s); group L 0.243 H, 2.81 A peak, 101 V peak.
- **Retention:**
  - a G10 slot wedge (0.81 mm in 1 mm grooves of the tips, arc-topped up to 1.7 mm over the slot);
  - 4 A4 M6 studs per utron through the half-cores and the G10 cheeks;
  - the cheeks bolted to 12 mm G10 carrier discs on the rotor sleeve.
  - The centrifugal load at 600 rpm (each body) is about 0.86 kN per utron.
- **Mass:** 2.24 kg per utron (SiFe 0.90, NiFe 0.15, Cu 1.07, G10 0.12). Bridges 0.65 kg each, 3.9 kg per side.

**Not settled by the drawing:**
- **The neck needs a nonlinear field check.** The knee (saturated incremental L ≈ 5 % of aligned, ≈ 30 % of unaligned
  with the 12 mm break) and the lap joints (≈ 3 % on the aligned reluctance) are estimates [RH]. The 2-D model is
  linear SiFe without the neck.
- **The 0.5 mm gap** needs runout of about 0.05 mm or better between two counter-rotating bodies on four inner
  bearings [RH]. The bearing arrangement for that is not designed.
- **Not in the solids:**
  - the 1 : −1 gear or belt;
  - La / Lb, the diodes, the snubbers, the start-kick source;
  - the AH (the hub is still the placeholder).
- **Vacuum:** if the reluctance sections share the vanes' vacuum, the impregnation and lamination coatings must be
  low-outgassing.

## Caveats
- **2-D model [IR].** Curvature is neglected and the end/axial-fringe corrections (+30 % unaligned, +3 % aligned) are
  [RH], so a 3-D check of κ_L is still due. The iron is linear μ_r 3000, and saturation enters the circuit through the
  neck law.
- Iron loss is from the M235-35A 1.5 T / 50 Hz rating scaled as f^1.3·B² [RH]. τ_fixed of 0.5 s for La/Lb assumes
  large gapped cores (about 2 J stored each) [RH].
- **AH:** the 160-turn rewind (1.0 mH, 0.27 Ω) is [RH], and the AH–bicone mutual coupling is not included.
- **Next:**
  - a 3-D check of the chosen pair;
  - the start-kick source;
  - the La/Lb core design;
  - ~~the tube STEP update~~ (done, §8: r_g 130 mm after the §7 correction, a 162 mm reluctance section);
  - a nonlinear field check of the neck (§8);
  - mechanical concentricity for 0.5 mm with counter-rotating bearings.
