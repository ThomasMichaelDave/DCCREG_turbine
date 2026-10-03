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
