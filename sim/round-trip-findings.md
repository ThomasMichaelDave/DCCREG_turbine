# ROUND-TRIP — findings (brief round-trip-floor r0.1)

**Run verdict: `FIELD-SOLVE-FAIL`.** FS8 (surrogate vs exact, 1.4e-3 against 1e-3) and FS5 (mesh convergence, @@FS5SHORT@@) miss their tolerances. RT2 misses by 2e-5 (|Δz| 1.21e-4 against 1e-4). Every other gate passes: FS1–FS4, FS6, FS7, RT0, RT1, RT3, RT4, CR1, MC1–MC3, FROZEN and FIREWALL. Under the pre-committed set, one FS gate failing decides the verdict.

**Floor verdict: `NO-FLOOR-IN-RANGE`.** This holds at m = 0.20 and also at m = 0. The round-tripped pump (motor off, all gaps in symmetric ring-down) has **no growing mode** anywhere in r_out 300–580 mm (D 775–1499 mm). Its non-neutral eigenvalue rises from 0.811 to 0.854, against the 1.20 the floor needs. The points fit z ≈ 0.900 − 26.8 / r_out [mm] to ±0.002. So under D-SCALING, **no size** reaches z = 1 in the drawn topology. The failed gates are errors of order 1e-3 in z, and the shortfall is ≥ 0.35, so they cannot change this verdict (§2.3).

**What kills the pump: two independent floors, each fatal on its own** (§3):
1. **The disaligned C1/C2 floor.** It is 191 pF, against 16 pF assumed (P2 refuted, ×12). Alone it takes the realized-C ladder from z 1.438 to 0.897.
2. **The ~1 nF of extracted strays.** Alone they take it to 0.953. Island and rail to enclosure are the largest; the rail↔island cross-couplings follow.

No lever tested in the build, alone or combined, restores z > 1 (§4).

- **Motor:** `MOTOR-CERTIFIED`. The integrator passes MC1–MC3. G1m is **confirmed**: with the motor branches in, even the ladder freeze has no growing mode (z = 0.999997, neutral).
- **Branch** `claude/new-session-0az7f9`. Not merged: TMD signs off.
- **Frozen diff:** empty vs b33baa2 (gate FROZEN).
- **Records:**
  - gate record `sim/rt_gates.json` (`python3 sim/rt_gates.py`);
  - run record `sim/round_trip_runs.json` (`python3 sim/round_trip.py --rt2 / --fs5`, `round_trip.floor_search`);
  - per-candidate designs and evaluations in `docs/geometry/rt/` (the field-solve caches are git-ignored and regenerated on demand).

## 1. Gates

| gate | result | value |
|---|---|---|
| FS1 guarded plates vs εA/g | PASS | 0.03 % (2 mm gap), 0.05 % (4 mm) |
| FS2 thin disc vs 8ε0a | PASS | 0.22 % (free space, Robin boundary at 25× the size) |
| FS3 two spheres vs image series | PASS | c11 −0.01 %, c12 −0.09 % |
| FS4 dielectric slab + air gap | PASS | 0.02 % |
| FS5 mesh convergence | **@@FS5RES@@** | @@FS5VAL@@ |
| FS6 reciprocity + sign rules | PASS | \|C_ij − C_ji\|/max 3.8e-9 (reference build, θ 7.5°, tol 1e-9); diagonal > 0, off-diagonal ≤ 0, row sums ≥ 0 |
| FS7 cross-tool (field vs overlap) | reported | C1 max +16 %, Cx max +12 %, Ca +45 %, C_R1 +5.5 % fringe (§2.1) |
| FS8 surrogate vs exact | **FAIL** | worst \|Δz\| 1.39e-3 at r 387 (0.78e-3 at 300, 0.93e-3 at 480, 0.21e-3 at 580); worst coupling residual 2.2 % (couplings ≥ 20 pF). No floor exists, so no final design needs confirming |
| RT0 headline | PASS | z 1.3254745317 (Δ −4e-11), K1–K4 pass |
| RT1 series tank | PASS | 785.203 pF → **1.3113581**; Δz·C_R1 ≈ −11.7 pF (1e6–1e8 pF) |
| RT2 N_θ 24 vs 48 | **FAIL (by 2e-5)** | z₁₂ 0.8304755, z₂₄ 0.8302417, z₄₈ 0.8301207: \|Δ\| 1.21e-4. First-order rate (Δ halves per doubling), extrapolated z∞ 0.83000 |
| RT3 integrity | PASS | every evaluated candidate: integrity PASS (0 FAIL) and all builder checks |
| RT4 G-* on the freeze reference | @@RT4RES@@ | @@RT4VAL@@ |
| CR1 counter-rotation | PASS | split 0 → max_rpm 3885 (I9 rotor) |
| MC1 single branch vs analytic | PASS | 7e-14 (V), 2e-13 (I) |
| MC2 conservation | PASS | 6e-10 |
| MC3 step halving / tolerance | PASS | \|Δz\| 1.1e-6 (dθ 0.05 → 0.025: 101 → 118 located events; loc_it 30 → 40) |
| D1 monotone | PASS | z(r_out) monotone on the scan |
| D2 exact at floor | n/a | no floor |
| FROZEN | PASS | empty diff vs b33baa2 |
| FIREWALL | PASS | field_solve: numpy/scipy/pyamg only; rt_engine: pump_engine + design_synth; no subprocess, git or file writes on their import path |

**Pre-committed predictions.**

| | prediction | outcome |
|---|---|---|
| P1 | series tank lowers z by 0.014 ± 0.002 | **confirmed**: Δz −0.01412 |
| P2 | disaligned C_min within ×2 of 16 pF | **refuted**: 191 pF field-solved (×12; 156 pF to R-A + 35 pF to the merged n18 septum face) |
| P3 | the 1–8 / 4–7 parasitic lowers z | **confirmed in sign, negligible in size**: removing it raises z by 0.0023 (L5 basis), almost all from its angle dependence |
| P4 | D_floor within ±15 % of Ø 841 mm | **refuted**: no floor |
| P5 | Ca toward 0.63 × C_max lowers D_floor | **refuted in direction**: in the field model a *larger* Ca raises z (Ca×2: +0.046 engine-only); smaller lowers it (×0.5: −0.039) |

## 2. The field solve

### 2.1 Solver and validation

- **Method.** Finite volumes on a cylindrical (r, φ, z) tensor grid snapped to every sector edge (stator as is, rotor turned by θ), with exact log/area conductances; conductors are fixed-potential cells.
- **Maxwell matrix.** From the variational Schur complement (error quadratic in the potential error). RS-AMG + CG, tol 1e-5, warm-started between angles.
- **Symmetry.** The build was verified 60°-periodic at every θ, so one 60° wedge with periodic faces is solved and the result ×6.
- **Axis.** The axis region r < 25 mm holds no conductor and is cut (zero-flux face) [ME].
- **D-ENCLOSURE.** Default: a grounded can 50 mm beyond the outermost conductor. Sensitivity in §2.4.
- **Levels.** Coarse "c" is used for sweeps: 1.3–3.5 M cells, 110–740 s per angle.

**Field vs overlap (FS7, reference build, nets as drawn).**

| coupling | overlap (pF) | field (pF) | fringe |
|---|---|---|---|
| C1 / C2 max | 279.8 | 325.1 / 324.4 | +16 % |
| Cx3 / Cx4 max | 522.8 | 584.0 / 585.8 | +12 % |
| Ca1 / Cb1 | 307.8 | 445.0 / 444.6 | +45 % |
| C_R1 (n18–n00) | 785.2 | 828.7 | +5.5 % |
| C1 / C2 min | 0.74 | 156.3 / 156.9 | — |
| Cx3 / Cx4 min | 1.41 | 214.0 / 179.7 | — |

An independent 2-D cross-section solver, written separately, also gives C1 disaligned ≈ 120 pF per machine (65 pF with no dielectric). The floor is real, not a 3-D artefact.

### 2.2 Where the C1 floor comes from

Reference build, θ_geom 30° (disaligned). The C1 face and the Ca counter are split into separate conductors.

| coupling | pF |
|---|---|
| rotor C1 face ↔ stator C1 face: fringe across the 7 mm gap at coincident sector edges | 78.8 |
| n18 septum face ↔ node 1: merged into R-A at the pump frequency | 34.8 |
| rotor C1 face ↔ Ca counter plate (node 1), seen through the stator's inter-sector gaps | 28.4 |
| rotor tip sphere, leads and bus (R-A) ↔ stator C1 face | 28.1 |
| rotor C1 face ↔ node-1 bus, leads and sphere | 15.4 |
| rest | 5.5 |
| **C1 min (R-A ≡ n18)** | **191.1** |

Only the first row responds to sector width, which is why the swing lever fails (§4).

### 2.3 Accuracy against the verdict

- **Mesh (FS5).** @@FS5PROSE@@
- **Uniform C error.** A uniform relative error in every C changes z by nothing: z depends on ratios only (S4 homogeneity).
- **Biggest single changes.** In the knock-out table (§3), removing an entire coupling class moves z by at most 0.53 (the C1 floor).

Non-uniform errors are measured directly. Eight draws, each coupling scaled independently by U(−3 %, +3 %), move z by at most 0.0029 (0.8276–0.8322). That is against a shortfall of ≥ 0.35 to z = 1.2. The surrogate (FS8, 1.4e-3) and N_θ (RT2, 1.2e-4) errors are smaller still.

### 2.4 Enclosure sensitivity (D-ENCLOSURE)

@@ENCTABLE@@

## 3. The round-trip ledger (reference build, rotor tips at 15° [IR])

One change at a time, starting from pump-synth's headline. "conv" is the monodromy's convergence flag. **From L3 on, no step converges.** The engine alternates between two gap-firing patterns, with leading non-neutral eigenvalues of 0.680 and 0.830, and plain iteration decays onto the neutral (charge-conserving) state, growth exactly 1.00000. The quoted z is therefore an **upper bound on the decay rate of the active mode: there is no growing mode.** The ladder freeze, by contrast, converges to 1.32547 in five cycles.

| step | z | conv | change |
|---|---|---|---|
| L0 pump-synth headline | 1.325475 | yes | ladder, parallel tank (collapsed) |
| L1 series tank | 1.311358 | yes | C_R1 785.2 pF realized, R-A the reference |
| L2 realized C's (overlap) | 1.437696 | yes | integrity-tool overlap values in the ladder's profile shapes |
| L3 fringe (field) C's | 0.943321 | no | C1 191.1–344.4, Cx 196.8–584.9, Ca 445.0, C_R1 914.2 pF |
| L4 extracted strays + Cpar | 0.839839 | no | 48 other couplings at their mean replace the ladder floors |
| L5 parasitic varicaps | 0.818529 | no | the other couplings as functions of the angle |
| L6 drawn varicap profiles | 0.841214 | no | C1 / C2 / Cx / Ca / C_R1 as the build realizes them over the turn |
| L7 enclosure reference | **0.830475** | no | both rotor halves float; every coupling to the grounded can — the fully round-tripped z |

**Add one field item to L2 (1.4377), or knock one back out of L3 / L4.**

| item | L2 + item | L3 − item | L4 − item |
|---|---|---|---|
| C1/C2 min (fringe floor) | **0.8966** | **1.4761** | 0.9513 |
| C1/C2 max | 1.5164 | 0.9060 | 0.8106 |
| Cx min | 1.4368 | 0.9439 | 0.8433 |
| Cx max | 1.4438 | 0.9442 | 0.8429 |
| Ca / Cb | 1.3911 | 0.9347 | 0.8260 |
| C_R1 | 1.4394 | — | — |
| strays (48, at their mean) | **0.9525** | — | — |

**Strays.** Knocking out one coupling at a time from L2 + strays (0.9525), the most costly are:

| coupling | mean pF | z without it |
|---|---|---|
| 8 ↔ enc (island) | 66.4 | 0.9860 |
| 7 ↔ enc (island) | 59.0 | 0.9854 |
| 1 ↔ 4 | 15.0 | 0.9808 |
| 1 ↔ enc | 35.9 | 0.9744 |
| 4 ↔ enc | 35.6 | 0.9687 |

Some strays *help*: 1 ↔ n23 (82 pF) → 0.9419, 2 ↔ 8 (33 pF) → 0.9407. No single stray decides it. Scaling every cross-stray (not the enclosure ones) by 0.05 *and* removing 150 pF of C1 floor and 170 pF of Cx floor still gives only 0.958 on the full model.

## 4. The floor and the levers

### 4.1 Floor table (D-SCALING default, motor off, all ring-down, m = 0.20)

Outer-class features track r_out: the return band at r_out + 23 and the axial bar band at r_out·375/387. Voltage-set features stay fixed: septum 12 mm, gaps, spheres.

| r_out (mm) | D (mm) | C1 max (pF) | C1 min, fringe (pF) | κ_C | Cx max / min (pF) | Ca (pF) | C_R1 (pF) | z | integrity |
|---|---|---|---|---|---|---|---|---|---|
| 300 | 775 | 213.6 | 138.0 | 1.548 | 362.2 / 161.2 | 281.7 | 562.6 | 0.8106 | PASS |
| 387 | 1000 | 344.4 | 191.1 | 1.802 | 584.0 / 214.0 | 445.0 | 914.2 | 0.8305 | PASS |
| 480 | 1240 | 520.3 | 254.1 | 2.047 | 878.4 / 269.2 | 640.9 | 1383.0 | 0.8420 | PASS |
| 580 | 1499 | 745.0 | 317.5 | 2.347 | 1261.8 / 328.6 | 900.2 | 1991.2 | 0.8538 | PASS |

The surrogate scan (9 points, 300–580) is monotone (D1): 0.811 → 0.854. z = 1.2 is not reached; the fitted asymptote is z∞ ≈ 0.90.

**The floor verdict is NO-FLOOR-IN-RANGE**, so there is no binding item. The slack of every other constraint, at the bottom of the range:

| constraint | slack |
|---|---|
| I11 cross-fire (the first non-pump constraint) | binds at r_out 254.4 mm (D 657 mm) |
| I9 rim speed | 3885 rpm (split 0), unchanged by r_out at fixed rim radius |
| HV clearances | all pass (integrity 0 FAIL) |

- **C_R1,min:** none exists. z stays below 1.2 even at C_R1 → ∞ (0.840 at the reference size).
- **Septum thickness:** with no C_R1,min there is no target thickness. The septum C is reported only:

| r_out | 300 | 387 | 480 | 580 |
|---|---|---|---|---|
| septum C (pF, 12 mm garolite) | 563 | 914 | 1383 | 1991 |

  The builder's "septum C = 2.82 × C_max (tank, shown only)" check fails off the reference size because the septum thickness is voltage-set. It is recorded as information, as brief §5 treats the tank.

### 4.2 Levers (one at a time against the freeze-lever baseline, reference size)

There is no floor anywhere, so ΔD_floor is undefined for every lever. Ranking is by Δz at fixed size, from field-solved candidates where marked (F), otherwise from the engine on the reference field model (E).

| # | lever | setting | z | Δz | basis | constraints touched |
|---|---|---|---|---|---|---|
| 1 | Ca (D-CA) | ca_cal 2.0 | @@CA2Z@@ | @@CA2DZ@@ | F | Ca/Cb band (fits, integrity PASS) |
| 1 | Ca (D-CA) | ×2.0 / ×1.6 / ×1.3 / ×0.7 / ×0.5 | 0.877 / 0.862 / 0.848 / 0.808 / 0.791 | +0.046 … −0.039 | E | — |
| 4 | series C_R1 | ∞ / 3000 / 1500 pF | 0.840 / 0.834 / 0.832 | +0.009 … +0.002 | E | thinner septum: insulation / tank flags |
| 7 | drop Lx | Lx shorted | 0.8309 | +0.0004 | E | removes 2 parts |
| 3 | 1–8 / 4–7 parasitic | removed | +0.0023 (L5 basis) | +0.002 | E | guard / parity / spacing |
| 6 | island Cx | Cx floor −170 pF (to ~30 pF) | 0.874 with C1 −150 (0.838 without) | +0.036 | E | — |
| 5 | stray floors | every cross-stray ×0.05 | 0.896 | +0.066 | E | routing, enclosure |
| 2 | swing: narrower sectors | c_w 20° | 0.8187 | −0.012 | F | κ 1.80 → 1.93 |
| 2 | swing: narrower sectors | c_w 15° | 0.8129 | −0.018 | F | κ 1.85 |
| 2 | swing: + larger r_in | c_w 20°, r_in 200 | 0.7870 | −0.044 | F | κ 1.85, C_max −33 % |
| 8 | station angles | — | not evaluated | — | — | no pump to tune (§5) |
| 9 | counter-rotation split | see §4.3 | — | 0 (motor off) | — | power lever only |

The combination of the positive levers (Ca×2, Lx dropped, C_R1 up) and the largest size is the opt candidate:

@@OPTROW@@

## 4.3 Counter-rotation (D-SPLIT, default 0.5 [IR])

- Rotor rim radius 491.49 mm; stator lead frame 561.5 mm.
- I9 rim limit 200 m/s on each body; I12 is not binding (142 048 rpm).
- With the motor off, z does not depend on rpm.

| split rpm_stator / rpm_rel | max rpm_rel | rotor rpm | stator rpm | rim rotor (m/s) | rim stator (m/s) | PRF (Hz) | binding |
|---|---|---|---|---|---|---|---|
| 0 (CR1) | 3885.9 | 3885.9 | 0 | 200.0 | 0 | 388.6 | I9 rotor |
| 0.25 | 5181.1 | 3885.9 | 1295.3 | 200.0 | 76.2 | 518.1 | I9 rotor |
| **0.5 (default)** | **6802.7** | 3401.4 | 3401.4 | 175.1 | 200.0 | 680.3 | I9 stator |
| 0.75 | 4535.1 | 1133.8 | 3401.4 | 58.4 | 200.0 | 453.5 | I9 stator |
| 1.0 | 3401.4 | 0 | 3401.4 | 0 | 200.0 | 340.1 | I9 stator |

The optimum split is r_rotor / (r_rotor + r_stator) = 0.467, which gives 7287 rpm with both rims at 200 m/s. Of the tabled splits, the default 0.5 gives the highest max rpm.

## 4.4 Motor certification

`MOTOR-CERTIFIED`. MotorSim integrates the motor branches in continuous time between gap events. It uses Strang splitting and locates each event inside its step by bisection.

| gate | result |
|---|---|
| MC1 | one branch vs the analytic series-RLC discharge, 7e-14 |
| MC2 | per-cycle energy residual 6e-10 |
| MC3 | dθ 0.05 / 0.025 and loc_it 30 / 40: z 0.9999966 / 0.9999977 / 0.9999966, \|Δz\| 1.1e-6 |

**G1m confirmed.** With the motor branches, the ladder freeze itself has no growing mode: z within 1e-5 of 1, which is the neutral mode. pump_engine's split-step gave 1.0000022, which was not converged.

The motor-on floor is not reported: there is no motor-off floor, and the motor-on pump does not pump even on the ladder.

## 5. What it means (for TMD)

The geometry → field → engine loop is closed and the result is negative. As drawn, the build does not pump at any size under D-SCALING.

The ladder's assumptions that fail are:
- **C_min ≈ 16 pF.** The coincident-edge sector layout, the see-through to the Ca counter plate, and the tip / septum hardware put 190 pF on C1 at disalignment.
- **Cpar 20 pF / island 5 pF.** The extracted strays total about 1 nF, dominated by island and rail capacitance to the enclosure.

Both scale with the build, so size does not escape them. The sector-geometry levers in the brief cannot fix the floor, because 60 % of it is not sector fringe.

Remedies that would have to be designed (not in this brief; all [IR], TMD-gated):
- an earthed or guarded screen between the C1 face and the Ca counter plate, closing the see-through;
- tip and septum hardware moved off the C1 face's view;
- disaligned sector edges offset in angle (non-coincident) or recessed;
- a reduced island-to-enclosure view (D-ENCLOSURE, §2.4).

The engine-side what-ifs show how much must be achieved together. Even with the C1 floor cut to ~40 pF, the Cx floor to ~30 pF and every cross-stray to 5 %, z is only 0.958 (§3). The enclosure couplings of the rails and islands must fall as well.

## 6. Exports

- **`docs/geometry/floor-56b6cb83.{json,step,csv}`** + `…-integrity.txt`. There is no floor, so this is the **top of the searched range** (r_out 580, D 1499 mm, z 0.854): the geometry TMD checks for overall size.
- **`docs/geometry/opt-@@OPTHASH@@.*`.** The best lever combination (§4.2).
- **Peak fields** (optional): not produced.

## 7. TMD-gated decisions (defaults used; alternatives shown)

| decision | default used | alternative shown |
|---|---|---|
| D-SCALING | outer class tracks r_out, voltage-set fixed | — |
| D-ENCLOSURE | 50 mm | 100 mm and free space (§2.4) |
| D-SPLIT | 0.5 | split table (§4.3) |
| D-MARGIN | m = 0.20 | m = 0: also no floor |
| D-GAPDEFAULT | all ring-down | — |
| D-MOTORDEFAULT | motor off | motor on: no growing mode |
| D-TANK | drawn series tank at 300 Hz | — |
| D-CA | the ladder's area law | Ca × 2 (§4.2) |
| D-CX | as drawn | — |
| D-ISLAND | as drawn | — |
| D-MEDIUM | air gaps, I4 provisional | — |
