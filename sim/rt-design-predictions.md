# Round-trip design loop: predictions and outcomes

Each prediction is recorded here **before** its run, then the outcome is filled in with a one-line verdict:

| verdict | meaning |
|---|---|
| ADOPTED | the move is kept |
| DROPPED | the move is abandoned |
| CONFIRMED | the prediction held |
| REFUTED | the prediction failed |
| SURPRISE | the result was not anticipated |

## Ground convention (TMD)

The machine floats completely in practice. Every virtual ground used in a simulation is stated, and a result that depends on one is flagged **[GROUND]**.

| basis | what it means | label |
|---|---|---|
| physical | the machine floating in free space: every node's capacitance goes to infinity, the 25× Robin boundary | "free" |
| historical default | a grounded can 50 mm out | "can50", a virtual ground |

## Step 0: stray budget (engine only, reference build, rotor tips 15°)

**Groups.** Each group is scaled on the field-solved C(θ):

| group | couplings | how it is scaled |
|---|---|---|
| C1 | 1–R-A and 4–R-B | the floor scaled by f, swing kept: C − (1 − f)·min C |
| Cx | 7–n17 and 8–n23 | the floor scaled by f, swing kept |
| X | every other node-to-node coupling | × f |
| E | every node's capacitance to the can or to infinity | × f |
| Ca | Ca and Cb | × f |

**Predictions.**
- **B1.** C1 and E are both binding: no single group scaled alone to f = 0.1 reaches z ≥ 1.2.
- **B2.** C1 alone at f = 0.1 gives the biggest single-group gain, but z < 1.1.
- **B3.** The pair (C1, E) at f = 0.25 reaches z ≥ 1.2 on the free basis.
- **B4 [GROUND].** On the free basis, moving the virtual reference from infinity to R-A changes z by < 0.02.

**Outcomes:** (filled after the run)

The run was `python3 sim/rt_budget.py`, recorded in `sim/rt_budget.json`. Step 1's part-ownership solves are in `docs/geometry/rt/freeze-t15-free.attrib.json`.

| | prediction | outcome |
|---|---|---|
| B1 | no single group alone reaches 1.2 | **CONFIRMED.** Best single group on free: X × 0 → 0.967. On can50: Ca × 3 → 0.903 |
| B2 | C1 is the biggest single-group gain | **REFUTED.** X (the cross-strays) is bigger. On free: X × 0.1 → 0.955 against C1 × 0.1 → 0.886 |
| B3 | (C1, E) at 0.25 reaches 1.2 on free | **REFUTED.** 0.886. On the free basis E barely matters: E × 0 → 0.868 from 0.861 |
| B4 [GROUND] | free basis, reference ∞ → R-A changes z by < 0.02 | **CONFIRMED.** 0.8608 → 0.8624 (Δ 0.0016). On can50 the shift is 0.011 |

**SURPRISE.** Cutting the island Cx floor *lowers* z inside the winning combinations: C1 × 0.1, E × 0.1, X × 0.1 gives 1.2034; adding Cx × 0.1 gives 1.1203. The island floor is not a target.

**Budget on the physical (free) basis.**

| C1 floor | X cross-strays | E | z | converged |
|---|---|---|---|---|
| × 0.1 (191 → ~19 pF) | × 0.1 (~620 → ~60 pF) | any | **1.14** | yes |
| × 0.1 | × 0.1 | × 0.1 | **1.20** | yes |
| × 0.25 | × 0.1 | × 1 | 1.06 | yes |
| × 0.1 | × 0.25 | × 1 | 1.05 | yes |

The threshold for a growing mode is C1 ≲ 0.25 together with X ≲ 0.25. **C1 and X must fall together, by roughly an order of magnitude each.** Ca × 3 adds about +0.06 on top.

**Step 1: who owns the strays (free space; cross-strays 585 pF at θ 0, 654 pF at θ 30).**

1. **The Ca/Cb counter foils (rails 1 and 4) facing the rotor's Cx island foils (n23/8 and n17/7).** About 110 pF per island side, about 225 pF in all. This is the single biggest X owner.
2. **The bank bus rings (2, 3) facing the Cx foils.** About 28 pF each side.
3. **The C2/C1 rotor faces facing the opposite Cx foils.** 30 pF.
4. **Lead to lead.** About 45 pF.

**The C1 floor at disalignment** (θ 30):

| source | pF |
|---|---|
| face–face edge fringe | 79 |
| n18 septum C_R foil → stator C1 face | 29 |
| Ca counter → rotor C1 face | 28 |
| rotor leads → stator C1 face | 27 |
| node-1 lead / bus → rotor face | 16 |

**Next moves, retargeted.**
- **M1.** A screen, or a radial or axial separation, between the Ca/Cb band and the rotor Cx island faces. Target: X −200 pF or more.
- **M2.** Offset or recessed C1 sector edges. Target: −79 → about −30 pF.
- **M3.** Screen the septum C_R foil and the Ca counter from the C1 face. Target: −57 pF.
- **M4.** Route the rotor leads out of the stator face's view. Target: −27 pF.

## Size limit (TMD)

The septum disc may be at most **1000 mm in diameter**: r_edge ≤ 500, which is the reference build (r_out 387). The size lever is therefore gone. Every move is judged at the reference size, and z ≥ 1.2 must be reached at D 1000.

## Step 2, move M1: trim the Ca/Cb counter-electrodes to their band (`counter_trim=1`)

The counter foils (rails 1 and 4) spanned the whole stator plate, r95–387, while the Ca/Cb electrodes are a 25 mm ring (r357–382). M1 trims the counters to r352–387, the electrode band plus the dielectric margin. All builder checks pass, integrity PASS, G-JS parity holds.

Predictions, recorded before the run. All on the free basis.

| | prediction |
|---|---|
| M1-a | the rail-counter ↔ island couplings (1–n23, 1–8, 4–n17, 4–7; ~223 pF at θ 30) fall by ≥ 70 %, so X falls by ≥ 150 pF |
| M1-b | "Ca counter → rotor C1 face" (28 pF) falls to ≤ 8 pF, so the C1 floor falls by ~20 pF |
| M1-c | Ca and Cb (field) change by ≤ 10 % |
| M1-d | z rises to 0.88–0.90: a step, not a pump. Per the budget, X must also go ×0.1 and C1 ×0.1 |

## Step 0b: the swing requirement (engine only, pump-synth's ideal ladder)

The ideal ladder keeps its small strays (Cpar 20, island 5, gap 2 pF). C1/C2 min is set to C_max/κ, with Ca × {0.5…3} and Cx max × {0.5…3} re-sized for the best converged z:

| κ = C_max/C_min | best z | at Ca, Cx |
|---|---|---|
| 17.5 (pump-synth) | 1.382 | Ca × 0.5, Cx × 3 |
| 8 | 1.246 | Ca × 1, Cx × 3 |
| 4 | 1.084 | Ca × 1, Cx × 3 |
| 3 | no growing mode | — |
| 2 | no growing mode | — |

**Requirement:** z ≥ 1.2 needs **κ ≳ 7 even with ideal strays**. The drawn build has κ = 1.80.

Screening every non-face contribution would leave only the 79 pF face-edge fringe, so κ ≈ 344/79 ≈ 4.4 at the 7 mm gap: still short. Reaching κ ≥ 7 also needs one of these:
- a smaller gap: a voltage-set feature (D-MEDIUM);
- edge treatment that cuts the face fringe itself (offset or recessed edges, field-shaping bars);
- a higher-εr film on the faces, raising C_max more than the fringe.

**Engine what-if (free basis), larger wanted swings against fixed strays:**

| C1, Cx, Ca swings | strays | z |
|---|---|---|
| × 2 | as built | 0.940 |
| × 3 | as built | 0.985 |
| × 3 | X × 0.5 | 0.993 |

Swing alone does not suffice: the strays must fall as well.

**M1 outcome.** Part-ownership solves at θ 0 and 30, free basis, in `docs/geometry/rt/m1-free.attrib.json`.

| | prediction | outcome |
|---|---|---|
| M1-a | X falls by ≥ 150 pF | **REFUTED.** X 585 → 538 (θ 0), 654 → 592 (θ 30): −47 / −62 pF. The rail ↔ island coupling moved from the Ca counter foil to the **C1 stator foil on the same carrier, the same node**. 1–n23 at θ 30: "Ca foil 54.0" became "C1 foil 44.5" |
| M1-b | C1 floor falls by ~20 pF | **REFUTED.** 192.3 → 199.2. Ca counter → rotor face did fall (28.4 → 1.9), but the node-1 bus ring followed the counter's new inner edge outward to r354, so bus → rotor C1 face went from 6 to 26 pF, and the face–face fringe rose 79 → 95 |
| M1-c | Ca within 10 % | CONFIRMED: 454 → 463 |
| M1-d | z 0.88–0.90 | not run. The sweep was stopped, since a 60 pF X cut is worth ≲ +0.02 per the budget |

**Verdict: DROPPED.**

**Lesson for the following predictions.** Conductors of one node shield each other. A node's exposure to another is set by the geometry *between the nodes*, the carrier stack, not by which of its faces carries foil. A move must change the field path between two different nets: distance, an interposed conductor of a third potential, or less facing area of the *node as a whole*.

## Step 2, move M5: low-εr carriers (G10 4.7 → PTFE 2.1), geometry unchanged

Every "G10 …" carrier, stator and rotor, becomes PTFE (εr 2.1). The garolite septum and the mica facings are kept. This is a material move: **[IR] mechanical flag**, since PTFE rotor discs at speed need structural review, and is to be weighed by TMD.

Predictions (free basis), recorded before the run:

| | prediction |
|---|---|
| M5-a | the C1 floor falls from 192 to 110–140 pF. The 2-D check gave 120 → 65 pF with the dielectric removed, so PTFE should land about halfway |
| M5-b | X falls from ~620 to 300–400 pF. The rail ↔ island path runs through the 41 mm ND2/ND3 carrier |
| M5-c | C1 max falls by ≤ 5 %: the C1 gap is air |
| M5-d | z rises to 0.90–0.95. Still no pump: κ ≈ 2.6, against the ≥ 7 that Step 0b requires |

**M5 field results** (part-ownership solves at θ 0 and 30, free basis; `docs/geometry/rt/m5-ptfe-free.attrib.json`).

| | prediction | outcome |
|---|---|---|
| M5-a | C1 floor 110–140 pF | **CONFIRMED.** 192.3 → 138.3 |
| M5-b | X 300–400 pF | **CONFIRMED.** 585 → 357 (θ 0), 654 → 406 (θ 30). Rail ↔ island halved: 1–n23 73 → 36 |
| M5-c | C1 max falls by ≤ 5 % | **REFUTED (narrowly).** 345.5 → 324.5, −6.1 % |
| M5-d | z 0.90–0.95 | **CONFIRMED.** z 0.9020 (free basis, 12 angles; reference free 0.8608, +0.041), not converged: still no growing mode. Field C1 324.5 / 138.3 (κ 2.35), Cx 570 / 137–161, Ca 413, C_R1 874 |

The Cx island floor also fell (225 → 161). The budget says that alone costs z.

## Scouting (2-D, `sim/rt_xsec2d.py`): edge, gap and see-through variants at r 240

| variant | aligned (fF/mm) | disaligned (fF/mm) | κ |
|---|---|---|---|
| base 30/30, G10 | 183.4 | 92.8 | 1.98 |
| 30/30, PTFE | 174.2 | 63.3 | 2.75 |
| PTFE, stator 22° / rotor 30° (offset edges) | 150.1 | 46.4 | 3.23 |
| PTFE, 20/20 | 124.7 | 26.3 | 4.75 |
| PTFE, gap 3.5 mm | 337.4 | 81.0 | 4.17 |
| PTFE, 22/30, gap 3.5 | 278.4 | 52.9 | 5.26 |
| PTFE, stator guard strips | 155.2 | 46.7 | 3.32, adding C(RA, G) 7 → 44 varying |
| PTFE, no see-through (back plates hidden) | 170.6 | 53.3 | 3.20 |
| PTFE, 22/30, no see-through | 138.5 | 28.7 | 4.82 |
| **PTFE, 22/30, gap 3.5, no see-through** | 262.8 | 31.4 | **8.38** |

**Reading.**
- Guard strips trade the C1 floor for a strongly varying C(RA, guard). That is a new rotating stray, so they are rejected.
- At the 7 mm gap the best combination found is κ ≈ 4.8. The **≥ 7 requirement needs the gap reduced to ~3.5 mm**, on top of PTFE, offset edges and hidden back plates.
- 2-D at mid-radius over-estimates the 3-D κ: the 3-D base is 1.80 against 1.98 here, because the inner radii are worse and the hardware adds to the floor.

## TMD rulings (this round)

- **Asymmetry.** Rotor and stator geometry may differ: smaller node-1 / node-4 stator plates, to be simulated.
- **The C1/C2 clearance (g_v, 7 mm) may be lowered.** This is distinct from the septum. Mica-based thin structural dielectrics may be used.
- **Any dielectric facing or film** (mica, PTFE, Mylar, Kapton) and any screening is acceptable if it does not jeopardise the pump.

## 2-D scouting, round 2 (r 240, `sim/rt_xsec2d.py`)

| variant | κ |
|---|---|
| PTFE 30/30 | 2.75 |
| PTFE, stator 26 / 22 / 18 against rotor 30 | 3.14 / 3.23 / 3.15 |
| PTFE 30/30, mica 2.5 + 2.5 as a sheet | 3.64 |
| PTFE 30/30, mica 2.5 + 2.5 **sectored** | 4.90 |
| PTFE 22/30, sectored mica 2.5 + 2.5 | 6.28 |
| PTFE 22/30, sectored mica 2.5 + 2.5, back plates hidden | **9.65** |
| PTFE 18/30, same | **10.56** |

A film helps only when sectored, lying under the foils. As a full sheet it raises the fringe almost as much as it raises C_max.

## Step 2, round 2: combined candidates (3-D, free basis, 12 angles)

**Common settings:**
- carriers PTFE;
- stator C1/C2 plates 22° against rotor faces 30° (`c_ws_deg=22`);
- Ca/Cb counters 22° (`counter_w_deg=22`), hidden behind the stator face;
- C_R plates 22° (`cr_w_deg=22`), hidden behind the rotor face;
- Ca/Cb electrodes 20° wide (`ca_w=20`), so they fit inside the counters.

**Candidates:**

| | g_v | sectored mica per face | air left |
|---|---|---|---|
| **A** | 7 mm | 2.5 mm | 2 mm |
| **B** | 4 mm | 1.0 mm | 2 mm |
| **C** | 3.5 mm | none | 3.5 mm |
| **D** | 3 mm | 0.5 mm | 2 mm |

The ladder re-sizes with g_v (C_max 280 / 490 / 560 / 653 pF). All four build, pass every builder check and pass integrity.

**Predictions** (recorded before the runs; 2-D κ derated by ×0.85 for 3-D, hardware floor ~25 pF kept):

| | prediction |
|---|---|
| A | κ_C 5–7, z 0.98–1.12 |
| B | κ_C 5–7; z within ±0.05 of A (same air, larger C overall, strays relatively smaller) |
| C | κ_C 4–5, z 0.95–1.05 |
| D | κ_C 6–8, the best z; **the first candidate expected to reach ≥ 1.1** |
| R2-X | X falls relative to C_max by ≥ 2× against the reference (PTFE plus the larger C_max) |

**Round-2 outcome, A** (g_v 7, sectored mica 2.5 / face, PTFE, 22/30, hidden counters and C_R plates; free basis; `docs/geometry/rt/r2A.eval.json`).

| | prediction | outcome |
|---|---|---|
| A κ_C | 5–7 | **CONFIRMED: 5.40** (C1 581.6 / 107.8 pF) |
| A z | 0.98–1.12 | **CONFIRMED: z 1.0195, converged.** **The first growing mode** of the round-tripped build |

**Engine-only follow-ups on A's field model (free basis).**
- **Re-sizing does not help.** Ca × 0.8 / 1.5 / 2 / 2.5 → 1.015 / 0.976 / 0.986 / 0.992. Ca × 0.6 → 0.924. Cx swing × 2 → 1.022. Ca is right where it is.
- **The floors remain the levers.**

| change | z | converged |
|---|---|---|
| C1 floor × 0.5 | 1.067 | yes |
| X × 0.5 | 1.093 | yes |
| **both × 0.5** | **1.180** | yes |
| both × 0.7 | 1.094 | yes |
| E × 0.5 | 1.026 | yes |
| Cx floor × 0.5 | 0.958 | no — the island floor must stay |

**Next:** ownership solves on A, to name the parts behind its 108 pF C1 floor and its X.

**Round-2 outcome, D** (g_v 3, sectored mica 0.5 / face, 2 mm air, otherwise as A; free basis; `docs/geometry/rt/r2D.eval.json`).

| | prediction | outcome |
|---|---|---|
| D κ_C | 6–8 | **CONFIRMED: 6.59** (C1 757.3 / 114.9 pF) |
| D is the best z | — | **CONFIRMED: z 1.0576, converged** (A 1.0195) |
| D z ≥ 1.1 | — | **REFUTED** |

**Engine-only follow-ups on D.**
- **Re-sizing is flat.** Ca × 0.5–1.3 with Cx swing × 1–2 spans 1.054–1.065.
- **The floors close it.**

| change | z | converged |
|---|---|---|
| C1 floor × 0.5 | 1.103 | yes |
| X × 0.5 | 1.123 | yes |
| **both × 0.5** | **1.204** | yes, **the target** |
| both × 0.7 | 1.127 | yes |

**Remaining job, on D: halve the C1 floor (115 → ~57 pF) and halve X.**

B and C were not run (stopped for compute). D dominates them on the 2-D and the A/D trend. Next: ownership solves on D.

## The cross-side rule (stray-sensitivity map on D; `sim/rt_stray_map_D.json`, dz per +10 pF, all converged)

The nodes split by side of the septum: side A {1, 2, 8, n23, R-A} and side B {4, 3, 7, n17, R-B}.

| coupling type | effect per +10 pF |
|---|---|
| **same-side** (e.g. rail/bank ↔ island on one side) | **harmless:** −0.0001 to +0.0013 |
| **stator/island cross-side** {1, 2, 8, n23} × {4, 3, 7, n17} | **−0.008 to −0.009 per pair** |
| rotor ↔ opposite-side stator | small per pair; 60 pF in all, worth +0.035 if removed |

**Budget on D, by set:**

| change | z |
|---|---|
| the harmful set (45 pF; largest rail 1 ↔ rail 4, 12.5 pF) → 0 | 1.115 |
| the harmful set × 0.5 | 1.083 |
| the rotor-cross set (60 pF) → 0 | 1.093 |
| all cross-side × 0 + C1 floor × 0.7 | **1.227** |
| all cross-side × 0.5 + C1 floor × 0.5 | 1.172 |
| same-side × 0.5 (297 pF) | only 1.072 |

**Consequence.** Converting a cross-side coupling into C1 floor costs about the same per pF, ~0.008 per 10 pF either way. So a screen tied to any pump node does not help. Cross-side coupling falls only with **distance between the two sides, lower permittivity, or a screen at a neutral potential** (infinity, or a virtual ground, which would be **[GROUND]**-flagged).

**Owners on D, excluding C_R1:**
- the stator plate seeing the *opposite* rotor through the rotor-sector gaps: about 27 pF per side (C2 stator ↔ C1 rotor face 10.9, ↔ n18 8.5, ↔ R-A lead 7.7);
- rail ↔ rail 12.5 pF;
- leads.

**D's C1 floor owners at θ 30 (115 pF):**

| source | pF |
|---|---|
| face–face | 40.5 |
| Ca counter → rotor face | 18.9 |
| rotor leads → stator face | 18.4 |
| stator leads → rotor face | 10.3 |
| C_R (n18) → stator face | 10.0 |
| bus | 6.2 |

## Round 3, candidate E: C1-floor moves on D

Settings relative to D:
- stator plates 18°, outer edge pulled in 12 mm (`c_s_inset=12`), so r95–375;
- counters 16° (`counter_w_deg=16`);
- C_R plates 16° (`cr_w_deg=16`);
- Ca electrodes 14° (`ca_w=14`), r232–382.

Builds, integrity PASS, G-JS parity holds.

**Predictions,** recorded before the run:

| | prediction |
|---|---|
| E-a | C1 floor 115 → 80–95 pF |
| E-b | C1 max 757 → 590–640 pF; the stator area is × 0.77 |
| E-c | κ 6.5–7.5 |
| E-d | z 1.05–1.09, roughly flat against D. The C_max loss offsets the floor gain. **If this holds, the C1 floor is not worth chasing further at fixed gap; the cross-side distance is.** |

## TMD proposal: multi-layer (interleaved) C1/C2 stacks on sides A and B — engine estimate on D

Multiplying C1/C2, with the ladder's Ca/Cb and Cx, by N. Strays fixed. Converged z in every case.

| N | optimistic: only face–face scales (D's non-face floor of 74 pF stays) | pessimistic: the whole C1/C2 floor scales |
|---|---|---|
| 1 | 1.0576 (D) | 1.0576 |
| 2 | 1.160 | 1.113 |
| **3** | **1.212** | 1.131 |
| 4 | 1.241 | 1.137 |

With Cx not scaled: N = 2 → 1.121, N = 3 → 1.137.

**Reading.** Multi-layer reaches z ≥ 1.2 at N ≈ 3, **provided**:
1. the added layers bring only face-to-face fringe. The see-through and hardware floor of 74 pF must not repeat per layer. In an interleaved stack the inner rotor plates sit between same-node stator plates, so this is the expected case;
2. the island Cx scales with C1/C2.

The deeper A and B stacks also keep the two sides further apart. The cross-side rule says that helps.

**Round 4 (to build):** interleaved C1/C2 stacks (N rotor plates between N+1 stator plates per side, sharing the D settings), with Cx scaled to match. **Prediction:** z between the two bounds, nearer the optimistic one.

## Round 4: interleaved stacks (TMD go-ahead), `sim/rt_interleave.py`

**Definition.** N = rotor plates per stack = stator plates per stack, so each stack has 2N − 1 gaps.

**Build.** Derived from D. Each C1/C2 stack and each Cx3/Cx4 stack gets 2(N − 1) double-sided intermediate plates:
- foil | 4 mm PTFE | foil, alternating rotor and stator;
- sectored mica facings in every gap, as D has them;
- rotor plates linked at their inner rim (axial rods through the stator plates' bores);
- stator plates linked at their outer rim, by 4° tabs to an axial rod beyond the rotor plates.

Everything beyond each stack moves axially outward. The rotor spark-gap tips on the disc rim follow their stator partners, so every gap keeps its spacing. Those tips get longer stems: **[IR] mechanical flag**.

| | parts | axial span | integrity | C1 overlap | Cx overlap |
|---|---|---|---|---|---|
| N = 2 (r4N2) | 1027 | ±151.2 mm | PASS, 12 nets | 1976 pF (×3.0) | 1571 (×3.0) |
| N = 3 (r4N3) | 1275 | ±188.4 mm | PASS, 12 nets | 3293 pF (×5.0) | 2618 (×5.0) |

Ca is unchanged (719 pF). The engine on D says that is better: ×3 with Ca × 1 → 1.259 against Ca × 3 → 1.212; ×5 with Ca × 1 → 1.320 against 1.257.

**Screening.** 6 angles per 60°. RT2 showed the angle count moves z by ~1e-3. The winner is extended to 12 angles.

**Predictions,** recorded before the runs:

| | prediction |
|---|---|
| N2 | z 1.15–1.26: between the pessimistic and optimistic engine bounds, κ_C ≥ 9 |
| N3 | z 1.18–1.32. **Expected to be the first ≥ 1.2 field-solved build** |
| IL-x | the cross-side harmful set does not grow by more than 20 %, since the stacks push the sides apart |

**Round-3 outcome, E** (`docs/geometry/rt/r3E.eval.json`).

| | prediction | outcome |
|---|---|---|
| E-a | C1 floor 80–95 pF | **CONFIRMED: 90.6** (D 114.9) |
| E-b | C1 max 590–640 pF | **CONFIRMED: 608.9** |
| E-c | κ 6.5–7.5 | **CONFIRMED: 6.72** (D 6.59) |
| E-d | z 1.05–1.09, about flat | **REFUTED (slightly low): 1.0408**, converged, below D's 1.0576 |

**Verdict: DROPPED.** The conclusion predicted in E-d holds: at fixed gap, cutting the C1 floor by shrinking the stator plate loses as much C_max as it gains in floor. D stays the base for round 4.

**Round-4 outcome, N = 2** (`docs/geometry/rt/r4N2.eval.json`; 6 angles, free basis, coarse level).

| | prediction | outcome |
|---|---|---|
| N2 | z 1.15–1.26 | **EXCEEDED: z 1.2791, converged.** κ_C **13.09** (C1 2186.5 / 167.0 pF); Cx 1679 / 299–323; Ca 818; C_R1 685 |

**The first field-solved build with z ≥ 1 + m (m = 0.20) inside the D 1000 mm limit.**

Open before calling it feasible:
1. the 12-angle confirmation (RT2-type), queued;
2. mesh convergence (FS5) at this point;
3. motor on;
4. the TMD mechanical and HV flags: PTFE plates and discs, the longer tip stems, 2 mm air between mica facings, the axial span ±151 mm.

## Round 5: N = 2 adopted for optimisation (TMD). Buildable variant N2c and its machine-build review

**Wiring, revised for the build.**
- Each intermediate plate's two foils are joined by embedded 1 mm vias through its own carrier.
- The inter-plate links run only between the near foils of adjacent same-type plates.
- The other type's intermediate foils are trimmed to keep the HV rule (11 mm) from each exposed link. The rotor mid-plate foil runs r75 → 380 instead of 387; the island bar plate starts at r80 instead of 75.
- Link rods clear every mica facing.

`docs/geometry/rt/r4N2c.design.json`: integrity PASS, 12 nets.

**CAD export** (FreeCAD builder, OCC): `docs/geometry/il2-ce1a9380.{json,step,-parts.csv,-integrity.txt,-cadcheck.json}`.
- 1051 solids, all valid;
- volumes exact (6e-15);
- **0 solid clashes**; intentional joins are declared by shared chains, as the builder does;
- STEP names complete;
- **integrity read back from the STEP: PASS** (12 nets, 0 FAIL, 11 WARN, as D).

**Machine-build review** (`sim/rt_buildcheck.py`, from the parts list, calibrated: the freeze reference and D both read BUILD-OK):

| check | D | N2c |
|---|---|---|
| counter-rotation collisions (revolved envelopes) | 0 | **0** |
| tightest running clearance | 1.5 mm* | 1.5 mm* |
| HV, exposed conductor vs other body (rule 11 mm) | 13.4 mm, OK | **7.2 mm, 288 pairs below.** All are the stator plate links (node 1/4) against the main rotor face (R-A/R-B) edge |
| axial length | 228 mm | **302 mm** |
| mass, rotor body (both rotor halves + septum) | 119 kg | **142 kg** (PTFE ρ 2.2) |
| mass, stator | 163 kg | 184 kg |
| thinnest wide carrier | 8 mm × 500 (flange) | **4 mm PTFE × 306–319 mm span**, the intermediate plates |
| longest rotor-tip stem | 10.5 mm | **28.5 mm** (⌀4): the tips follow ND1 out by 18 mm |

\* The rod-end artifact of the builder's lead risers, identical in D; accepted by the builder.

**Flags for TMD (build feasibility):**
1. **HV at the stator links:** 7.2 mm against the 11 mm spark-gap rule. The C1/C2 capacitor gaps themselves hold the same voltage across 2 mm air + mica, so the links are ~3× less stressed than the gap. But they are exposed rods: an insulating sleeve (PTFE tube) or a slightly larger rotor-face inset would close it.
2. **4 mm PTFE intermediate plates spanning ~310 mm:** stiffness and flutter at speed. A mica-glass composite plate is the natural substitute; it raises the carrier εr, so it is to be field-checked.
3. **28.5 mm ⌀4 rotor-tip stems:** bending at 3000+ rpm. A ⌀6 stem or a shorter path (tips moved to the outermost rotor plate) should be checked.
4. **Mass +23 kg rotor, axial +74 mm.**

**Field result of N2c:** pending (the 6-angle, then 12-angle sweep is running).
