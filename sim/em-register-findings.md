# Electromagnet register — findings (BRIEF_ELECTROMAGNET_REGISTER r0.3)

2026-10-05, Brussels time (CEST). Pre-registration: `sim/em-register-predictions.md`, commit f771c59 (07:08), before
any run.

| what | where |
|:--|:--|
| data | `presets/electromagnets-RA.json`, `presets/electromagnets-V15.json` (every value with its status word and source) |
| code | `sim/em_register.py` (identity, stations, loop sums, PRF, fit, P1-PUMP), `sim/em_ladder.py` (the generalised edge driver), `sim/em_ra.py` (the RA comparison), `sim/em_solids.py` (solids and clearance/HV gates) |
| results | `sim/em_register_results.json` |
| raw per-turn currents and voltages | `sim/em_raw/*.npz` |
| solids (stage-2 part schema) | `docs/geometry/em-register-{RA-a,RA-b,RA-c,V15,motor-drawn-w35}.json` |

Frozen cores: empty diff vs b33baa2. No change inside `pump_engine`, `shuttle_core`, `doubler_core` or
`island_resonant_core`; RA enters as a documented edit of the NR net built by `rt_engine`.

## Verdicts

- **Phase 1 (RA tank): `REGISTER-COLLISION`, on G-CLR-HUB.**
  - The RA hub cannot sit in the current CAD stack.
  - P1-PUMP passes: RA does not break the pump.
  - G-AH-SAT also fails for all three AH windings.
- **Phase 2 (motor, layout open): `REGISTER-COLLISION`, on G-CLR-ROT and G-CLR-SG at the drawn layout, and
  G-HV-MOTOR.**
  - The sweep finds a collision-free outboard layout (r_pole ≥ 519 mm), whose binding gate is the stator frame
    radius.

## 1. Pre-registered numbers

| ID | registered | result | verdict |
|:--|:--|:--|:--|
| P-REG-1 | V15 33.8 / 8.3 / 84.1 µH | 33.80 / 8.26 / 84.13 µH | **PASS** |
| P-REG-2 | RA 98.9 / 34.7 µH | 98.91 / 34.65 µH (k 0.350) | **PASS**: finding 1 stands; 139/93 µH is not reproducible from the drawn turns |
| P-REG-3 | 1.20 MHz ± 5 % | 1.203 MHz (1.89 × f₀) | **PASS** |
| P-REG-4 | 299.9 Hz; 1206 / 201 Ω; Q 30.2, within 0.1 % | 299.92 Hz, 1206.0 / 201.0 Ω, Q **30.15** | **PASS at the registered precision only.** The registered 30.2 is the rounding of 30.15; strictly, Q is 0.17 % from it |
| P-REG-5 | AH pair same way during the flank: centre field > 10 % of one coil's own | ratio 0.71–1.06 over the flank in all six cases; 0.22–0.97 over (0, t_r); 0.47–0.82 over (0, 10 ns) | **PASS** in every case and every window |
| P-REG-6 | \|Δz\| ≤ 1e-3 at Q ≤ 30 | Δz = −2.6e-6 (L 0.5–1 mH; and with the computed L_tot) | **PASS**; P1-PUMP passes |
| P-REG-7 | margins (a) 1.3, (b) 2.1, (c) 0.5; radial (b) 0.45, (a)/(c) 2.0 | 1.30 / 2.10 / 0.50; radial 2.05 / 0.45 / 2.05 | **PASS** (bare winding) |
| P-REG-8 | (a),(c) ≈ V_AH; (b) ≈ ⅔ V_AH, ±25 % | inductive 0.988 / 0.656 / 0.973; ladder late-time 0.981 / 0.661 / 1.124 | **PASS** |
| P-REG-9 | N·I(c) < N·I(a) | 810 vs 1022 A·turns (0.79); L_tot(a)/L_tot(c) = 1.21 | **PASS** |

Notes on P-REG-5 and P-REG-6:
- **P-REG-5 window:** both front-τ readouts of the AH coil were invalid (§4). The flank window therefore fell back
  to 2 t_r + 15 ns, a default not in the pre-registration. The pre-registered fixed windows, (0, t_r) and (0, 10 ns),
  give the same verdict.
- **P-REG-6 z(Q):** z(Q) is flat up to Q = 100 (z 1.3254719–1.3254720). This is partly built into the frozen engine:
  a ring still alive after 50 µs is taken to its ring-down limit (T_RING_MAX). So the engine cannot show a ring
  that survives into the next event, and z above Q ≈ 50 is not evidence either way.
- **The P1-PUMP anchor:** my first attempt used `make_config()` defaults and printed an anchor of 1.625. The judged
  run uses the RT0 configuration (`pump_synth.engine_cfg`) and reproduces 1.3254745317 exactly.

## 2. The D-11 comparison: three AH windings, side by side (no recommendation)

Everything outside the AH winding is identical across the three. Values are at C_R = 789 pF, a 15 kV ring, and rod
μ′(f₀) from a Debye 77 model (μi 2000, f_r 2.5 MHz) [RH until the datasheet is read in].

| | (a) 2 × 25, rod in former | (b) 3 × 17 | (c) 2 × 18 |
|:--|:--|:--|:--|
| L_AH, one coil (with rod) | 98.5 µH | 121.0 µH | 60.7 µH |
| L_TA–L_BA (AH pair, opposing) | −1.25 µH | −1.68 µH | −0.79 µH |
| L_TC–L_TA (top, aiding) / L_BA–L_BC (bottom, opposing) | +22.7 / −22.7 µH | +23.8 / −23.8 µH | +16.6 / −16.6 µH |
| L_TC–L_BA / L_TA–L_BC | −4.6 / +4.6 µH | −5.2 / +5.2 µH | −3.6 / +3.6 µH |
| L_TC = L_BC (32 turns kept) / cone–cone M | 89.5 / +25.8 µH | same | same |
| **L_tot (every mutual, signed)** | **425 µH** | **469 µH** | **351 µH** |
| f₀ (789 pF) / with the ×4 trim | 275 / 137 kHz | 262 / 131 kHz | 303 / 151 kHz |
| Z₀ (789 pF) / ×4 | 734 / 367 Ω | 771 / 386 Ω | 667 / 333 Ω |
| peak chain current at 15 kV | 20.4 A | 19.4 A | 22.5 A |
| AH ampere-turns | 1022 | 992 | 810 |
| centre gradient dB_z/dz (all four windings) | 0.388 T/m | 0.464 T/m | 0.366 T/m |
| \|B\| at the sphere poles (A / B, \|z\| 26) | 55.5 / 24.1 mT | 63.3 / 33.4 mT | 56.2 / 21.6 mT |
| \|B\| at the equatorial wall (r 26) | 6.6 mT | 6.5 mT | 7.1 mT |
| B_z at the centre (all four) | −7.1 mT | −6.8 mT | −7.8 mT |
| T-NULL: AH pair alone, B_z(0) per one coil's own | 2.8e-14 | 2.8e-14 | 2.7e-15 |
| T-NULL: null offset with all four windings | **+14.5 mm** (toward B) | +12.2 mm | +15.9 mm |
| **G-AH-SAT: peak rod B (limit 0.30 T)** | **0.51 T: FAIL** | **0.54 T: FAIL** | **0.48 T: FAIL** |
| core loss at f₀: Steinmetz [RH] / from μ″ | 299 / 44 W | 287 / 40 W | 248 / 40 W |
| steady adjacent-layer voltage (P-REG-8) | 0.99 V_AH | 0.66 V_AH | 0.97 V_AH |
| bench edge: largest physical-neighbour voltage per V of edge, t_r 2 ns / 0.5 ns | 1.01 / 1.14 (layer, apex end) | 1.02 / 1.04 (layer, mid) | 1.06 / 1.31 (layer) |
| in the RA chain (SG1 edge), AH layer-neighbour voltage per V | 0.08 | 0.06 | 0.09 |
| G-CLR-AH: axial / radial / at the return lead | 1.30 / 2.05 / **0.45 mm** | 2.10 / 0.45 / 0.45 mm | 0.50 / 2.05 / **0.45 mm** |
| PEEK sleeve (Ø12.3 + 2 × 0.5 = Ø13.3) in the Ø13 bore | n/a (rod in its former) | **does not fit** | **does not fit** |
| G-CLR-AH | PASS | **FAIL** (sleeve) | **FAIL** (sleeve) |
| mechanical note | shaft engagement ≈ 28 mm; tip at \|z\| 72 + 1 mm PEEK cap | rod 12 mm in the bore | rod 12 mm in the bore |

What the comparison shows (the tool reports and does not choose):

1. **L_tot is half the record:** 351–469 µH against 856 µH, so f₀ is 262–303 kHz, not 194 kHz.
   - The AH coil on the 77 rod gives 98.5 µH for (a), against the record's 197 µH. Its apparent rod μ is about 5–6,
     not 11.
   - The cones lose about 10 µH of the drawn 98.9 µH because turns k = 0–1 sit inside the septum and electrode and
     are dropped from the chain.
   - The record's L_tot also omitted the mutuals: −4 to −6 µH net on the AH side, and the cone–cone +51.7 µH.
   - The corrected L_tot and f₀ above replace 856 µH / 194 kHz wherever they feed the tank (F-10 extended).
2. **The 77 rod saturates at a 15 kV ring in every option** (0.48–0.54 T in a linear model, against 0.30 T). The
   linear model cannot show what saturation then does to L and f₀. The ring amplitude that keeps the rod at 0.30 T is 8.4–9.4 kV (linear scaling).
   The Steinmetz loss at that flux (≈ 250–300 W at a continuous ring) is an extrapolation past saturation and an
   upper bound; the burst duty lowers it.
3. **The null moves 12–16 mm toward side B with all four windings.** Two causes:
   - The aiding cone pair puts a uniform B_z of about 7 mT at the centre.
   - The top L_R↔AH mutual aids while the bottom one opposes.
   - The AH pair alone nulls exactly (1e-14).
   - The 08-06 figure was about 5 mm.
4. **The return lead of the two-layer options takes 1.6 mm of their radial margin**, leaving 0.45 mm at the lead,
   the same as (b) everywhere. A 0.5 mm PEEK sleeve does not fit the decided Ø13 bore in (b) or (c).

## 3. P-REG-5: how the edge enters the RA chain (SG1 fire, R-A driven against the stator)

| case | ratio over the flank | over (0, t_r) | over (0, 10 ns) | centre field per kV | V_R-B / V_R-A (minimum in the flank) | C_R extracted |
|:--|:--|:--|:--|:--|:--|:--|
| (a) with stator | 1.06 | 0.52 | 0.82 | 12.1 µT | **0.40** | 856 pF |
| (a) no stator | 0.74 | 0.22 | 0.47 | 0.6 µT | 0.97 | 812 pF |
| (b) with stator | 0.88 | 0.37 | 0.77 | 11.4 µT | 0.41 | 856 pF |
| (b) no stator | 0.95 | 0.97 | 0.67 | 0.4 µT | 0.97 | 812 pF |
| (c) with stator | 0.71 | 0.41 | 0.74 | 12.0 µT | 0.41 | 856 pF |
| (c) no stator | 0.76 | 0.39 | 0.53 | 0.9 µT | 0.97 | 812 pF |

- **The AH pair circulates the same way during the flank in every case**, confirming the brief's even-mode
  expectation.
- **The new number is R-B.** With the stator foils present (bracket (i), full annuli, an upper bound on that
  coupling), R-B reaches only 40 % of R-A during the flank. C_R does not hold the halves together against R-B's own
  capacitance to the stator side.
  - So the chain sees a large differential drive as well as the common mode.
  - The centre field during the flank is about 12 µT per kV of edge, against under 1 µT/kV without the stator.
- **AH stress in the chain is small** (≤ 0.09 V per V of edge between layers): the AH coils sit deep in the chain.
- **The L_TC cone takes the edge first.** Its front-τ readout was invalid as well. Its §3 idealisation gives
  τ ≈ 138 ns with τ_turn ≈ 4.3 ns, so a 2 ns edge is shorter than one turn's travel time (§4).

## 4. P-EDGE-1…7 on the bench AH coil, and E-REGIME

**Every front-τ readout on the AH bench coils is invalid.**
- The pre-registered one has R² 0.003–0.85 across variants and edges of 0.5–5 ns.
- The post-hoc per-turn-normalised one has R² ≤ 0.29.

The waterfall (`sim/em_raw/bench_a_*`) shows why. Two fronts start at t = 0:
- one at the input turn;
- one at the last turn of layer 2, which lies radially against the input turn (≈ 8.6 pF per touching pair).

They meet mid-winding at about 8 ns. The folded multi-layer coil has no single travelling front, so the line
quantities τ and Z₀ of the edge brief's §3 are not defined for it by front tracking.

| | verdict |
|:--|:--|
| P-EDGE-1 (plateau) | **READOUT INVALID** (registered and post-hoc) |
| P-EDGE-2 (β) | **READOUT INVALID** |
| P-EDGE-3 (γ) | **READOUT INVALID** |
| P-EDGE-4 (stress in the first tenth, section voltages in winding order) | **KILL**: section 48/50 for (a) at 2 ns. Physical-neighbour voltage: **1.0–1.3 V per V of edge** between the input turn and its radial neighbour at the apex end, with up to 14 % overshoot at 0.5 ns. My expectation was 0.9–1.0, exceeded for (c) at 0.5 ns |
| P-EDGE-6 | **REGISTERED with an invalid readout.** Ladder TDR (50 Ω, rod): Z₀ ≈ 265 Ω and centre B ≈ 11.3 µT per V over the fill; the τ value (47.9 ns, R² 0.18) is not usable |
| P-EDGE-7 | **READOUT INVALID** |

An earlier pass of this file's code labelled the post-hoc P-EDGE-1 "PASS" without checking that readout's own fit
quality. That was fixed in the code and in the results before this write-up.

**E-REGIME** (`e_regime_idealised` in the results), from §3's idealisation τ = √(L·C_g) with the ladder's own L and
C_g, and stated as such:

| family | τ (idealised) | t_r/τ at 2 ns | t_r/τ_turn at 2 ns | regime |
|:--|:--|:--|:--|:--|
| AH (a) / (b) / (c), μ 1 → μ_i | 16→39 / 17→37 / 12→26 ns | 0.05–0.17 | 2.6–8.7 | ladder |
| L_TC cone (32 turns) | 138 ns | 0.014 | **0.46** | **t_r < τ_turn: the full-wave check of edge brief §5 applies to the cone** |
| C-EM (1340–1730 turns) [RH] | 1.7–2.2 µs | ≈ 1e-3 | ≈ 1.6 | ladder, once D-5/D-6 fix the geometry |

## 5. Stator / motor gates (Phase 2)

| gate | result | |
|:--|:--|:--|
| G-EM-ID | 12 C-EMs ↔ 12 coils ↔ 12 caps (2 in per-branch); labels by index; nodes = NR | **PASS** |
| G-EM-STATION | DXF: A at 30° + 60k, B at 0° + 60k, numbering clockwise; poles at 15° + 60k on r 424.32 (plan circles) | **PASS**. Block D / S6 deltas: group A +30° (F-2) |
| G-EM-SENSE | with one winding sense against the rail lead (`start_node` 1 for A, 4 for B), N-S alternation around the ring needs opposite signs of the A and B branch currents (i_A+ i_B− or i_A− i_B+); same signs give pairs | reported |
| T-MOTOR-PRF | per coil 299.92 Hz, 1206 Ω, Q 30.15; per branch (12 coils on mA/mB, 2 × 2.64 µF) 299.92 Hz, 201 Ω | see P-REG-4 |
| T-MIRROR | all hands flipped: every scalar identical (rel 0), B_z and ∇B reversed exactly. Under θ → −θ the C-EM station sets map to themselves and the poles go from 15° to 45° + 60k | **PASS** |
| G-CLR-ROT (drawn, r_pole 424.3) | 17 rotor parts collide with the C-cores: both disc carriers, the septum, and **all 12 rotor spark-gap tip stems** (they sweep through the jaws) | **FAIL** |
| G-CLR-SG (drawn) | the stator SG1/SG2 items sit 6.0 mm from the C-EMs (need 11); **the rotor tips (R-A/R-B, θ_r 15° + 60k) sit inside the poles (−8.5 mm)**, because the CAD tips and the drawn poles share 15° + 60k | **FAIL** as drawn; re-clock feasible for δ ∈ [−29°, −7°] ∪ [+5°, +23°] (1° steps, both gaps, w_t 35) |
| G-HV-MOTOR | 2 mm jaw–pole air holds 6–8 kV against a 20 kV-class stator-to-rotor difference; jaw–pole ≈ 3.0 pF at alignment | **FAIL** unless D-6 bonds the core so that the difference stays below about 6 kV |
| G-HV-POLE | 2 × 20 mm creepage against the 15 kV ring at 2.5 mm/kV [RH] = 37.5 mm | PASS (thin margin) |
| G-MOTOR-SWEEP | r_pole 424 → 450–500: collisions 17 → 2 (the outer disc carriers). **r_pole ≥ 519.3: no rotor collision**, but the spine reaches r 599–620 against R_frame 560, and the discs must be extended to host the poles. Rising window 4.1–6.4° (S6/TORQUE-SIM assumed 30°); L(θ) depth ≈ 7.6–9.7 (estimate) | binding: G-CLR-ROT below 519 mm, the frame above |

## 6. Phase 1 geometry gates

| gate | result |
|:--|:--|
| G-CLR-HUB, RA (a/b/c) | **FAIL.** 12 counter-rotating collisions: the hub shell against the ND1/ND4 PTFE carriers (r 50–402 from \|z\| 50.25). 435–439 same-body interferences with the CAD rotor stack (CR foils, A/B disc carriers, rotor C1/C2 foils, buses) inside the cone. L_TC k = 0–1 inside the septum and electrode. No conductor-to-conductor approach under 11 mm once those collisions are resolved |
| G-CLR-HUB, V15 | no counter-rotating collision; 22 same-body interferences (the A/B discs occupy the first turns, F-12); no conductor approach under 11 mm in the latest build |
| G-CLR-AH | (a) PASS; (b), (c) FAIL (the PEEK sleeve) |
| G-CI-EM | couplings quantified and **not yet wired into the circuit-integrity tool**: jaw–pole ≈ 3.0 pF; C_R incl. fringe 856 pF with the stator stack (812 without), against 789 pF; per-turn coil-to-carrier and coil-to-shaft partials are in the ladder's capacitance matrices |

## 7. My expectations against the outcomes

Confirmed:
- P-REG-1…9;
- P-EDGE-4 KILL;
- G-CLR-HUB fail;
- the Phase 1 verdict REGISTER-COLLISION, with P1-PUMP passing;
- (c) having the lower L;
- the null offset going toward B.

Wrong:
- **L_tot**: 351–469 µH, not 0.55–0.75 mH.
- **f₀**: 262–303 kHz, not 210–240 kHz.
- **G-AH-SAT**: a clear fail at 0.48–0.54 T for every option, not marginal.
- **The null offset**: 12–16 mm, not several mm.
- **The P-EDGE bench readouts**: invalid. I expected P-EDGE-1/2/7 PASS and P-EDGE-3 inconclusive.
- **Neighbour stress**: up to 1.3 V/V, not ≤ 1.0.
- **R-B lagging to 0.40** with the stator: not anticipated.

## 8. Open, not done

- **The pump-synth stage-2 page (JS mirror):** the solids are emitted in the stage-2 schema and checked against the
  CAD build in Python, but they are not yet added to `tools/pump-geometry.js` / `pump-synth.html`, and the G-JS
  parity gate is not extended.
- **The circuit-integrity hookup** of the new couplings (G-CI-EM).
- **The C-EM edge ladder** (waits on D-5/D-6), and the compact terminal models for the netlists.
- **Datasheet inputs to replace:**
  - the 77 material's μ′/μ″ and Bsat;
  - Steinmetz parameters;
  - garolite/G-10/enamel εr;
  - the vessel material;
  - the wire grade (pitch 1.60 mm).
- **Decisions still with TMD:** D-3, D-4, D-5, D-6, D-7, D-8, D-9, D-10. The RA stack has to replace the CAD stack
  inside the hub before G-CLR-HUB can pass (F-12). Re-clocking the spark-gap tips needs a builder change
  (`sg_tip_deg`) that is TMD's to approve.
