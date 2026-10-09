# The neck's nonlinear field check — findings

**Source:** `sim/neck_nonlinear.py` → `sim/neck_nonlinear_results.json`; figure `docs/figures/neck-nonlinear.png` (the
same script). About 30 min with 2 processes on an idle machine (59 field solves, 22 ngspice runs); case D (§6) about
6 min more (`python3 sim/neck_nonlinear.py D`, on the written results); its start runs (§7) about 10 min
(`python3 sim/neck_nonlinear.py Dstart`).

**Status:**
- [OC] the magnetostatics, the laminate's two limits, the circuit;
- [IR] the 2-D section and its end factors (as `sim/pole_fd2d.py`), the datasheet-class B–H curves, the series-neck law
  fed to the deck;
- [RH] the NiFe foils' stacking factor (0.90), the lap joints' contact gap (0.02 mm), J_s at 60 °C (× 0.975).
- It answers the ledger's model check 31 (`docs/ledger/DCCREG-design-ledger.md`:875). The bench settles the [RH]
  inputs: the aligned L(i) of one built utron reads them directly.

**Scope:** the pick (g 0.5 / 6 bridges / 1200 rpm relative), its utron as drawn (`sim/utron_profile.py` `spec`,
DCCREG-UTR-101), its deck as `sim/rotor_parts_duty.py` runs it, with and without the 22 mF bypass
(`sim/ah_steady_cusp.py`; PROPOSED). "Per utron" is per turn of one utron; "the group" is 3 × 200 turns in series.

## Headline

| what | the record | this check | where (`sim/neck_nonlinear_results.json`) |
|:--|--:|--:|:--|
| the neck's saturation flux, per utron | 0.2227 mWb (design); 0.225 at 0.75 T × 3.0 × 100 mm | **0.2113 mWb (−5.1 %)** | `saturation.phi_knee_aligned_Wb`, `knee_vs_design` |
| … as the group's Ψs | 0.1336 Wb-t | 0.1268 Wb-t | `saturation.psi_s_fe_group` |
| aligned L per coil, below the knee (0.1 mWb) | 81.0 mH | **72.8 mH (−10 %)** | `lowfield.L_al_coil_fe_mH` |
| unaligned L per coil | 9.43 mH | 9.36 mH | `lowfield.L_un_coil_fe_mH` |
| κ | 8.59 | 7.78 | `lowfield.kappa_fe` |
| z_lin (the screen's basis; rule ≥ 1.20) | 1.208 | **1.187** | `z_lin` |
| incremental L past the knee, aligned / unaligned | ≈ 5 % / ≈ 30 % [RH] | **12.8 % / 52 %** (2-D) | `saturation.L_inc_*_frac_2d` |
| where it saturates first | the neck (intended) | **the neck**; the SiFe stays ≤ 0.86 T at the knee | `saturation_order` |
| AH A-turns per coil, 22 mF bypass (mean) | 300 | **323** (C), +8 % | `operating_point["C \| bypass_22mF"]` |
| … without the bypass (min–max, mean) | 139–449 (290) | 162–475 (313) | `operating_point["C \| no_bypass"]` |
| z_early, bypass / none | 1.147 / 1.139 | 1.112 / 1.104 | same |
| belt, bypass / none | 18.1 / 17.6 W | **21.0 / 20.5 W** | same |
| utron copper, bypass / none | 13.5 / 12.9 W | 15.6 / 15.1 W | same |
| **with the 3-D utron sets** (case D, 22 mF): AH mean, z_early, belt — frame_a / one reversed / aiding | 245 / 236 / 221 A-t, z 1.091 / 1.084 / 1.072 (the 3-D study, ^6 law) | **272 / 264 / 249 A-t, z 1.051 / 1.043 / 1.028, 15.0 / 14.2 / 12.7 W** | `case_D.runs`; `sim/utron_3d_results.json` `deck` |

1. **The neck sets Ψs about 5 % below the design** [OC model; RH inputs]. The FE knee is 0.2113 mWb per utron. The
   strip's own saturation, J_s × SF × section = 0.78 T × 0.90 × 300 mm², is 0.2106 mWb. The record sized it at
   0.75 T over the full 3.0 mm, i.e. a stacking factor of 1: 30 foils of 0.1 mm do not fit a 3.0 mm envelope with
   their coating. At SF 0.95 the knee is 0.2216 mWb (the design's, −0.5 %); at SF 1.0, 0.2324 (§3).
2. **The knee is sharp, then soft** [OC]. Below it the aligned L falls only gently (1.82 → 1.77 µH per turn² from
   zero to 0.1 mWb); at 0.211 mWb it drops within ≈ 5 % of flux to an incremental 12.8 % of the low-field L (52 %
   unaligned). The record's ^6 law starts adding current far below Ψs (+26 % at 0.8 Ψs) and keeps hardening past it
   (4.4 % at 1.21 Ψs). Along the record's own trajectory that law differs from the FE by 23 % rms, up to +58 % (§2, §5).
3. **The built back iron costs 10 % of the aligned L below the knee, mostly in the laps** [OC model; RH inputs]. The
   strip's 0.1 mm foils are stacked radially (`sim/utron_profile.py` rounds the strip to whole foils), so where the
   half-cores sit on it the flux crosses the foils normal to them: −8.9 % at SF 0.90. The 0.02 mm lap gaps add −2.3 %,
   the stud holes −0.3 % (§3). κ falls 8.59 → 7.78 and z_lin 1.208 → 1.187, under the screen's 1.20.
4. **The pump with the FE's law runs higher and hotter** [OC circuit; IR law]. Case C (the FE neck and the FE L(θ)) drives
   323 A-turns per coil with the bypass (+8 %), for 21.0 W on the belt (+2.8 W) and 15.6 W of utron copper (+2.1 W);
   z_early falls to 1.112. The FE's knee holds the group's flux near the knee for more of the cycle, so more current
   flows away from alignment. The knee flux falls with angle (0.211 mWb aligned, 0.202 at 7.5°), which C's law does not
   follow: the bracket C′ (the 7.5° knee everywhere) gives 295 A-turns mean without the bypass against C's 313 (§5).
5. **The SiFe never saturates** in the swept range [OC]. At the knee the strip under the break is 95 % past its knee;
   the half-cores reach 0.86 T, the tips 0.70 T, the tip faces 0.23 T, the bridges 0.35 T (SiFe knee 1.46 T). The top
   foils at the laps pass their knee first, from 21 A-turns per utron aligned (§4).

## 1. The model and its gates
**The section** [IR: as `sim/pole_fd2d.py`]: the plane of rotation unrolled at r_g 130 mm, periodic over 120° (one
utron, two bridges), flat tip and bridge faces, A = 0 40 mm beyond the iron, scaled by the 100 mm stack.

**The back iron as built** [OC: the drawn utron, `sim/utron_profile.spec`]: the NiFe strip at u 86–89 across the full
58 mm; the two half-cores from u 89 (less the lap gap); the 12 mm break and the slot cover at μ0; the four Ø6.4 stud
holes (A4 studs, μ0) as squares of equal area [IR]; the coil as pole_fd2d's (+ side u 101–128, − side u 58–85).

| part | law | data [IR unless tagged] |
|:--|:--|:--|
| M235-35A half-cores, bridges | isotropic in the plane, B = SF B_iron | typical 50 Hz normal curve of the EN 10106 grade (mill data-sheet class): J 1.54 / 1.63 / 1.73 T at 2.5 / 5 / 10 kA/m (minima 1.49 / 1.60 / 1.70); μ_r ≈ 10⁴ near 0.8 T; SF 0.95 (`docs/make_core_drawing.py` SF) |
| the neck strip | 0.1 mm foils stacked radially: along them B = SF B_iron, across them H = SF H_iron + (1 − SF) B/μ0 [OC: the laminate's limits] | 80 % NiFe-Mo, annealed (Permalloy-80 / Mumetall / HyMu 80 class): μ_i ≈ 5·10⁴, μ_max ≈ 10⁵, J_s 0.80 T at 20 °C, × 0.975 at 60 °C [RH]; SF 0.90 [RH] |
| the lap joints | an air gap between each half-core and the strip | 0.02 mm [RH] (datum A is flat to 0.02, `docs/make_core_drawing.py`) |

The curves are in `materials`. "Saturated" means the iron's differential μ_r is below 100: 1.46 T for the SiFe, 0.77 T
for the NiFe at 60 °C (`materials.*.B_knee*`) [IR].

**The solver** [OC]: A_z on a tensor mesh with a line at every material edge (0.2 × 0.1 mm at the edges, growing to
2 mm; 86–95 k nodes); pole_fd2d's five-point operator written as the minimiser of the magnetic energy; Newton with a
backtracking line search on it. The linked flux per turn is L_stk f·A/NI, which is pole_fd2d's L_stk (⟨A⟩₊ − ⟨A⟩₋).
Each angle is swept in NI up to 0.36 mWb per utron (aligned, unaligned), 0.29 (2.5–10°) or 0.21 (12.5–27.5°).

| gate | result | pass |
|:--|:--|:--|
| G-SLAB: an iron slab between two current sheets (exact 1-D solution), M235-35A, the foils along and across, 2 A/m to 200 kA/m (to 2.17 T) | max error 3.3e-11 | ✔ (≤ 1e-6) |
| G-LIN: μ_r 3000 everywhere, pole_fd2d's solid section, against `sim/pole_fd2d.solve` | aligned +0.53 %, unaligned +0.05 % | ✔ (≤ 2 %) |
| G-MESH: every cell halved (86 k → 191 k nodes), the built utron, aligned (NI 5–400) and unaligned (NI 5–2400) | flux ≤ 0.23 %; post-knee incremental L 0.11 % / 0.07 % | ✔ (≤ 1 %) |
| G-DECK: the record's deck through this wrapper, 0 and 22 mF, against `sim/ah_steady_cusp_results.json` | identical (0.0); 299.8 A-turns, z_early 1.1466, belt 18.13 W with the bypass | ✔ |
| the analysis mirror against `sim/magnetic_doubler.analyse` on the same runs | 0.0 | ✔ |

Results: `gates`. The record's z_lin is reproduced, 1.2079 (`z_lin`).

## 2. Ψ(NI) of the built utron
**Below the knee** (`lowfield`; per turn²; the 3-D column takes pole_fd2d's end factors on the FE's own L [IR]):

| | 2-D, NI → 0 | 2-D, secant at 0.1 mWb | with end factors | the record | per coil |
|:--|--:|--:|--:|--:|--:|
| aligned | 1.823 µH | 1.768 µH | 1.821 µH | 2.026 µH | 72.8 mH (81.0) |
| 10° | 0.324 | 0.322 | 0.411 | 0.422 | |
| unaligned | 0.181 | 0.180 | 0.234 | 0.236 | 9.36 mH (9.43) |

- The secant at 0.1 mWb stands for "below the knee" [IR]: at NI → 0 the SiFe is in its initial-permeability range
  (μ_r ≈ 2000 in the curve), while the pump works at 0.1–0.21 mWb.
- **The neck is in series with the rest of the path below the knee** [OC check]: the excess MMF over each angle's
  secant line is the same at 0°, 2.5°, 5° and 10° (≈ 2.2 A-turns at 0.15 mWb, `fe_sweeps`).

**The knee** (`knees`; 2-D; the asymptote fitted through each sweep's last 0.06 mWb):

| angle | knee flux (tangents) | its centre | incremental L past it, of the low-field L: 2-D / 3-D (end flux through the neck) / 3-D (around it) |
|:--|--:|--:|:--|
| 0° | 0.2113 mWb | 0.2117 | 12.8 % / 12.5 % / 15.3 % |
| 5° | 0.2084 | 0.2100 | 20.3 % / 18.0 % / 31.3 % |
| 7.5° | 0.2017 | 0.2034 | 35.1 % / 30.1 % / 48.3 % |
| 10° | 0.1976 | 0.2009 | 41.3 % / 35.5 % / 54.0 % |
| 30° | 0.1868 | 0.1861 | 52.4 % / 45.8 % / 63.4 % |

- **Past the knee the extra flux crosses the whole air column between the half-cores** [OC]: the break, and the slot
  with the coil in it. The record's ≈ 5 % counted the break alone.
- **The knee flux falls 12 % from aligned to unaligned** [OC]: part of the strip's flux is slot leakage, which links
  the coil only in part; unaligned that share is larger.
- **The record's law** has dΨ/di = L/8 (12.5 %) at Ψs and 4.4 % at 1.21 Ψs, the same fraction at every angle
  (`saturation.record_law_dpsi_di_frac`).

## 3. What sets Ψs and the knee
**The build-up, aligned** (`buildup_aligned`; L is the 0.1 mWb secant, per turn², 2-D):

| step | L | Δ | knee flux | NI at the record's aligned flux (0.2055 mWb) |
|:--|--:|--:|--:|--:|
| V0 pole_fd2d's section, μ_r 3000 | 1.977 µH | | — | |
| V1 the same, M235-35A | 1.977 | 0.0 % | none | 102 A-t |
| V2 + the strip and the break, NiFe ideal (in-plane, SF 1) | 1.992 | +0.8 % | 0.2318 mWb | 102 |
| V3 + SF 0.90 | 1.992 | 0.0 % | 0.2089 | 104 |
| V4 + the foils stacked radially | 1.814 | **−8.9 %** | 0.2102 | 121 |
| V5 + 0.02 mm lap gaps | 1.773 | −2.3 % | 0.2107 | 123 |
| V6 + the stud holes = the built utron | 1.768 | −0.3 % | 0.2113 | 123 |

- **The SiFe's real curve changes nothing at the working flux** [IR]: the record's μ_r 3000 is right for it.
- **The stacking factor sets Ψs; the foils' direction sets the low-field L** [OC model].

**Sensitivities** (`sensitivity_aligned`; each one input moved from the built utron):

| input | L (0.1 mWb) | knee flux |
|:--|--:|--:|
| the built utron (SF 0.90, gap 0.02 mm, J_s 0.78 T, radial foils) | 1.768 µH | 0.2113 mWb |
| SF 0.95 | 1.850 | 0.2216 |
| SF 1.0 (the record's sizing) | 1.934 | 0.2324 |
| lap gap 0 / 0.05 mm | 1.809 / 1.711 | 0.2102 / 0.2115 |
| J_s(60 °C) 0.75 T (the record's B_NIFE as J_s) | 1.762 | 0.2028 |
| foils stacked axially (in the plane of rotation, like the SiFe) | 1.934 | 0.2094 |

- The series check of these variants at 2.5–7.5° (`sensitivity_series_check`) agrees with their aligned change of
  neck reluctance within 7 % at 2.5–5° and up to 19 % at 7.5° (the J_s variant's change is too small to compare).

## 4. Where the iron saturates first
(`saturation_order`; the first sweep point at which any of a region's iron is past its knee, and the state at the
aligned knee, NI 134 per utron)

| region | first past its knee, aligned / unaligned | B max at the knee | share past it |
|:--|:--|--:|--:|
| strip under the break | 21 A-t (39 µWb) / 278 A-t (50 µWb) | 0.80 T | 95 % |
| strip under the half-cores (the laps) | 21 A-t / 278 A-t | 0.79 T | 1.3 % |
| half-core back iron | never (1.28 T at 826 A-t) | 0.86 T | 0 |
| tips | never | 0.70 T | 0 |
| tip faces (top 1 mm) | never | 0.23 T | 0 |
| bridges | never | 0.35 T | 0 |

- **The neck saturates first, as intended** [OC]. Its top foils at the laps go first, at a tenth of the knee flux;
  that is the gentle softening below the knee (figure (b)).
- **The SiFe keeps a margin of 1.7× at the knee** and stays below its knee to 826 A-turns aligned and 3055 unaligned.

## 5. The pump with the corrected law
**The law** [IR]: the neck in series with the rest of the path, i = Ψ/L(θ) + i_neck(Ψ). L(θ) is the 0.1 mWb secant
at each angle with pole_fd2d's end factors, as a cosine series (`sim/pole_design.fit_cos`, error 4.1 %).
i_neck is the aligned sweep's excess MMF over its secant line, a pwl table, applied to the utrons' share of the
group's flux at alignment. The mechanical power is Ψ²/2 · d(1/L)/dt [OC for this law].
- The deck is otherwise the record's: copper, La / Lb, the strays, the snubbers, the seed current, the AH at 0.27 Ω.
- Cases: **A** the record's ^6 law at the FE's Ψs; **B** the FE's neck on the record's L(θ); **C** the FE's neck and
  L(θ); **C′** as C with the 7.5° sweep's excess, a bracket for the knee's fall with angle (`laws`).
- **Fidelity**: the law's current against the FE map along each run's last cycle (`operating_point.*.fidelity_vs_FE`).

| case | bypass | AH A-turns per coil: min–max (mean) | z_early | belt | utron Cu | law vs FE: rms / max |
|:--|:--|--:|--:|--:|--:|--:|
| record (the pick) | none | 139–449 (290) | 1.139 | 17.6 W | 12.9 W | 22 % / +55 % |
| record (the pick) | 22 mF | 290–308 (300) | 1.147 | 18.1 W | 13.5 W | 23 % / +58 % |
| A: ^6 law at Ψs 0.1268 | none / 22 mF | 131–424 (274) / 274–291 (283) | 1.139 / 1.144 | 15.8 / 16.3 W | 11.5 / 12.0 W | 22 % / +55 % |
| B: FE neck, record's L(θ) | none / 22 mF | 164–475 (310) / 315–335 (326) | 1.145 / 1.152 | 20.7 / 21.2 W | 15.3 / 15.8 W | 4.5 % / −14 % |
| **C: FE neck and L(θ)** | none | 162–475 (313) | 1.104 | 20.5 W | 15.1 W | 4.8 % / −12 % |
| **C: FE neck and L(θ)** | 22 mF | **313–333 (323)** | **1.112** | **21.0 W** | **15.6 W** | 4.7 % / −12 % |
| C′: the 7.5° knee | none | 153–449 (295) | 1.105 | 18.4 W | 13.5 W | 12.9 % / +35 % |
| C′: the 7.5° knee | 22 mF | the transient stopped (ngspice: timestep too small at D4*) | | | | |

- **Ψs alone (A) scales the pump down** [OC]: −5.7 % of A-turns and −2 W for −5.1 % of Ψs.
- **The knee's shape (B) more than reverses it** [OC circuit]. The FE adds little current until the knee, so the
  group's flux rises to 1.06 of the record's Ψs at alignment (record 0.95) and stays higher through the cycle
  (figure (d)): +26 A-turns over the record and +3 W on the belt.
- **The lower aligned L (C) costs gain, not field** [OC]: z_early 1.152 → 1.112 with the A-turns unchanged.
- **C's largest error** is near 7° on the approach to alignment, where the true knee is lower. C′ over-corrects near
  alignment (+35 %). So the true operating point lies between them: 295–313 A-turns mean without the bypass [IR].
- **The rest of the ledger moves with it** (C, 22 mF): AH coils 2.21 W (1.90), La + Lb 0.89 W (0.69), diodes 2.23 W
  (2.06); the branch's peak 3.01 A (2.88).

**Sensitivities on C, 22 mF** (`operating_point["C, …"]`; their fidelity is not checked: their maps were solved
aligned only):

| input | AH mean | z_early | belt | utron Cu |
|:--|--:|--:|--:|--:|
| SF 0.95 / 1.0 | 342 / 360 A-t | 1.128 / 1.147 | 23.3 / 25.7 W | 17.5 / 19.4 W |
| lap gap 0 / 0.05 mm | 322 / 323 | 1.122 / 1.097 | 20.9 / 21.0 | 15.6 / 15.7 |
| J_s(60 °C) 0.75 T | 310 | 1.111 | 19.4 | 14.4 |
| foils stacked axially | 322 | **1.147** | 20.8 | 15.5 |

- **Stacking the NiFe like the SiFe** (in the plane of rotation) restores the record's z_early at the same field
  [OC model]. That is a build choice for the designer; the record's drawing has the foils stacked radially.

## 6. Case D: the FE neck with the 3-D utron sets
**The combination** [IR]: each 3-D set's L(θ) enters as its 3-D / 2-D ratio at each angle, L13 / L2d_record_13
(`sim/utron_3d_results.json` `variants`, pole_fd2d's 2-D solve), on this study's 0.1 mWb secant, in place of C's end
factors. i_neck(Ψ) is C's, unchanged: the neck sits within the stack. The deck is C's (La / Lb at the record's
0.146 H, the record's copper, strays, snubbers and seed).
- **The bracket** "series": the 3-D solid section in series with this study's neck reluctance, 1/L = 1/L13 +
  (1/L_FE − 1/L_linear) [IR]. It keeps the neck's reluctance as solved; the scaling also scales it. For frame_a it puts
  the aligned L 1.1 % lower and moves the operating point by ≤ 0.4 % of A-turns (table).
- **The gate:** fed C's own factor, the same path reproduces C exactly (law and deck: 0.0; `case_D.gate`).
- **Numerics** [IR]: the 3-D sets grow only 2–5 % per cycle, so they run 150 cycles; every run settles (z_late
  1.00000). ngspice gets the same neck table resampled ×4 by a monotone cubic. The bypass runs use trapezoidal
  integration: gear stops where the slowly growing flux first meets the sharp knee.
  - On the 2-D set these change the result by ≤ 0.2 % against C, and trap against gear by ≤ 0.03 %.

**The sets with the neck** (`case_D.sets`; per coil, at 0.1 mWb):

| set | 3-D / 2-D ratio, 0° / 30° | L_al / L_un per coil | κ |
|:--|--:|--:|--:|
| 2-D (C's end factors) | 1.030 / 1.300 | 72.8 / 9.36 mH | 7.78 |
| frame_a (the record's frame) | 1.059 / 1.713 | 74.9 / 12.3 mH | 6.07 |
| cyl_one_reversed | 1.060 / 1.786 | 75.0 / 12.9 mH | 5.83 |
| cyl_aiding | 1.068 / 1.943 | 75.5 / 14.0 mH | 5.40 |

**The operating point** (`case_D.runs`; the AH coil above, "top"; the group's flux at its peak, at alignment):

| set | bypass | AH A-turns per coil: min–max (mean) | z_early | belt | utron Cu | group flux | per utron | pull per utron |
|:--|:--|--:|--:|--:|--:|--:|--:|--:|
| 2-D (= C) | 22 mF | 313–333 (323) | 1.112 | 21.0 W | 15.6 W | 1.061 Ψs | 0.232 mWb | 30.4 N |
| frame_a | none | 133–388 (263) | 1.042 | 14.8 W | 10.7 W | 1.020 Ψs | 0.223 mWb | 28.2 N |
| frame_a | 22 mF | 263–279 (272) | 1.051 | 15.0 W | 11.0 W | 1.023 Ψs | 0.223 mWb | 28.3 N |
| frame_a, series | none / 22 mF | 133–388 (263) / 264–281 (273) | 1.034 / 1.044 | 14.8 / 15.1 W | 10.7 / 11.0 W | 1.020 / 1.022 Ψs | 0.223 mWb | 28.1 / 28.3 N |
| cyl_one_reversed | none | 130–377 (253) | 1.034 | 14.0 W | 10.1 W | 1.017 Ψs | 0.222 mWb | 28.0 N |
| cyl_one_reversed | 22 mF | 256–272 (264) | 1.043 | 14.2 W | 10.4 W | 1.020 Ψs | 0.223 mWb | 28.1 N |
| cyl_aiding | none | 124–355 (239) | 1.019 | 12.5 W | 9.0 W | 1.009 Ψs | 0.221 mWb | 27.6 N |
| cyl_aiding | 22 mF | 242–256 (249) | 1.028 | 12.7 W | 9.2 W | 1.012 Ψs | 0.221 mWb | 27.7 N |

Ψs is the record's 0.1336 Wb-t; the pull scales the record's 28.2 N at 0.223 mWb (`sim/rotor-mechanics-findings.md`
:183–184) as Φ² [OC].
- **The neck raises the 3-D sets' field by 11–13 %** [OC circuit]. With the 22 mF bypass that is 272 / 264 / 249
  A-turns against the 3-D study's 245 / 236 / 221 with the record's law (`sim/utron_3d_results.json` `deck`). As in C,
  the sharp knee holds the flux higher through the cycle; the belt rises by 2.5–2.7 W (12.3 / 11.6 / 10.2 W there).
- **It costs gain** [OC]: z_early falls by about 0.04 to 1.051 / 1.043 / 1.028 with the bypass (1.091 / 1.084 / 1.072
  there). Without the bypass the aiding set reads 1.019, the thinnest margin in this note.
- **The flux at the clamp barely moves**: 221–223 µWb per utron, so the pull stays at ≈ 28 N per utron, as recorded.
- **Which set is the machine's** is the 3-D study's call (`sim/utron-3d-findings.md`); the designer decides on the
  neck and the coils' connection.

## 7. Case D: the start
**The runs** [IR]: `sim/start_3d.py` `_job` unchanged (`sim/parts_first_cut.py` `mag_job` with the 3-D set's `RP._kw`
override, La / Lb at 0.146 H), with `sim/magnetic_doubler.deck` wrapped so that its text carries case D's law
(`sim/neck_nonlinear.py` `_start_job`). All with the 22 mF bypass, 150 cycles, the dense table and trapezoidal
integration (`case_D_start`).
- **The gate:** the record's law and set, K4 at phase 1, 40 cycles: 307.88 A-turns, as `sim/start_3d_results.json`.
- **The criterion** (as `sim/start_3d.py`): the AH coil reaches half the set's own case-D steady peak by the end. That
  peak is the 30 % seed's run, 278.7 / 255.4 A-turns (§6's runs: 279.5 / 256.4).
- `mag_job`'s own z_early uses the record's law and is not reported.

| run | frame_a (κ 6.07): final A-turns | cyl_aiding (κ 5.40): final A-turns |
|:--|--:|--:|
| seed 20 % of Ψs | dies (0) | dies (0) |
| seed 25 % | **278.7** (starts) | dies (0) |
| seed 30 % / 40 % | 278.7 / 278.7 | 255.4 / 255.4 |
| K4 at full speed, phases 1 / 1.25 / 1.5 / 1.75 | 278.7 at all four (17.2–18.4 mJ out of K4) | 255.4 at all four (17.0–18.3 mJ) |
| K4 at 1150 rpm relative, phases 1 / 1.5 | 273.5 / 273.5 | 250.6 / **dies** |
| K4 at 1100 rpm relative, phases 1 / 1.5 | 268.3 / **dies** | **dies / dies** |

- **K4 still starts the pump at full speed at every phase**, in both sets [OC circuit; IR law].
- **The seed threshold rises one step** to 25 % (frame_a) and 30 % (aiding). With the record's law it was 20 % and
  25 % (`sim/start_3d_results.json` `sets`).
- **The speed window narrows.**
  - K4 starts every phase from 1150 rpm relative for frame_a, and only at full speed for the aiding set.
  - With the record's law it was from 1050 and 1100 (`sim/start_3d_results.json`
    `K4_every_phase_from_rpm_relative`).
  - So K4 must fire within the last 50 rpm (or at speed) of the 1200 rpm relative run-up.

## Notes against the record
- `sim/utron_profile.py`:13–15 and `sim/pole-design-findings.md`:417–418: the lap joints "add ~3 % to the aligned
  reluctance"; the saturated incremental L is "~5 % of aligned and ~30 % of unaligned".
  - Here: the laps cost 11 % of the aligned L at 0.1 mWb (the radial foils 8.9 %, the gaps 2.3 %); past the knee
    12.8 % aligned and 52 % unaligned (2-D).
- `sim/utron_profile.py`:11 and `sim/pole-design-findings.md`:359: "the flux crosses the strip edge-on, in the plane of
  the laminations".
  - True under the break. At the laps the flux enters radially stacked foils normal to them, and that is the largest
    cost in §3.
- `sim/pole-design-findings.md`:357 and `CHANGELOG.md`:667: "0.225 mWb at 0.75 T, 1.1 % above the operating point's
  0.223 mWb".
  - Here 0.2113 mWb, −5.1 %. The 3.0 mm strip of "30 laminations of 0.1 mm" holds SF × 3.0 mm of NiFe.
- `docs/ledger/DCCREG-design-ledger.md`:287 and :666: the strip "saturates at Ψs 0.134 Wb-turns per group".
  - Here 0.127 Wb-turns.
- `docs/ledger/DCCREG-design-ledger.md`:288: "The law i = Ψ/L·(1 + (Ψ/Ψs)⁶) is a fit [IR]".
  - Against this map it is 23 % rms off in current along the pick's trajectory, up to +58 % near 5°.
- `docs/ledger/DCCREG-design-ledger.md`:665: "L 81.0 / 9.4 mH (κ 8.6, the 2-D screen)".
  - With the built neck, in the same 2-D frame: 72.8 / 9.36 mH, κ 7.78.
- `sim/pole-design-findings.md`:28–29: the variants "are selected on z_lin ≥ 1.20; the pick has 1.208".
  - With the built neck's L(θ), z_lin is 1.187.
- `docs/make_utron_drawing.py`:266 (the detail drawing's data row "at 0.75 T: Φs +1.1 %") carries the same sizing
  basis. Flagged only: the figure is redrawn by its script.
- `sim/rotor-mechanics-findings.md`:183–184: 0.223 mWb across a tip face at the clamp.
  - In case C the aligned flux reaches about 0.232 mWb per utron (1.06 of the record's Ψs), so the pull at the clamp
    is ≈ 30 N per utron rather than 28 N [OC: ∝ Φ²] (`case_D.runs["gate, 2-D, as C"]`).

## Caveats
- **[RH] the three inputs the result leans on.**
  - The foils' stacking factor sets Ψs: ±0.05 moves it ±5 %.
  - The stacking factor and the laps' contact set the low-field L: SF 0.95 recovers 40 % of the −10 %; the gap moves
    it ±3 %.
  - J_s at 60 °C: 0.75 T would put the knee at 0.2028 mWb.
  - One built utron's aligned L(i) on the bench measures all three.
- **[IR] datasheet-class curves.** They are not the supplier's material. The SiFe's curve matters only below 0.05 mWb;
  the NiFe's J_s and the foils' coating are what count.
- **[IR] the homogenised foils.** The saturation front in the strip spans a few foils, which is where a continuum
  model is weakest. The mesh changes the knee by under 0.25 % (G-MESH), but that does not test the homogenisation.
- **[IR] 2-D.** The ends enter through pole_fd2d's [RH] factors, here on the external path (the end flux through the
  neck); through the air around it the post-knee fractions are 15 % / 63 % (§2).
  - The 3-D check (`sim/utron-3d-findings.md`, ledger line 665) puts κ at 6.70 with linear iron and no neck. The two
    are combined in §6 (case D).
- **[IR] magnetostatic.** No eddy currents: the 0.1 mm foils at 120 Hz have a skin depth of about 0.15 mm at μ_r 5·10⁴,
  larger past the knee [RH].
- **[IR] the law.** The series neck holds below the knee (§2). Its knee is the aligned one; the true knee falls with
  angle, which C and C′ bracket. C′ with the bypass did not run in ngspice.
- **Not changed:** the AH at the deck's 0.27 Ω (0.333 Ω as wound, `sim/hub-thermal-findings.md` §1), the seed, La / Lb,
  the bypass (PROPOSED). The designer decides whether the neck is re-sized (e.g. 3.2–3.3 mm of foils at SF 0.90 for
  the design's Ψs) or the foils turned; this note records the check.
