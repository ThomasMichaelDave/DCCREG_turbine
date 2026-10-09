# Real diodes in both pumps of record — findings

**Source:** `sim/diodes_real.py` → `sim/diodes_real_results.json`; figure `docs/figures/diodes-real.png` (the same
script). Every number below is from the results file unless another file is named.

**Status:** the ledger's model check 32, "real diodes at start-up" (`docs/ledger/DCCREG-design-ledger.md` §5.2, §6).
The device models are datasheet-class [IR]; no part is chosen here (the parts are `sim/parts-first-cut-findings.md`'s,
PROPOSED); the 22 mF bypass is PROPOSED.

**What it runs:** both netlists of record, built by their own functions with the diode models replaced in a copy of the
text:
- the magnetic dual doubler at the pick (`sim/magnetic_doubler.py`, exactly as `sim/rotor_parts_duty.py` `_kw` and
  `sim/ah_steady_cusp.py` run it), without and with the bypass;
- the electrostatic doubler with the rings' symmetric supply (`sim/core_field.py` dc, the settings of
  `sim/hub_rings_build_results.json` record_supply: 2 + 2 stages, 100 pF, 100 GΩ, 280 cycles from −1 kV);
- the same deck on the tube-strays study's as-built capacitances (`sim/tube_strays_results.json`; §6, the results'
  key `electrostatic_as_built`).

## Headline

**The magnetic pump starts and runs with real rectifiers, but the record's 20 % kick starts it only with Schottky
parts.** [IR: the classes]
- The smallest kick that passes the record's start criterion, in % of Ψs (without / with the bypass):
  the record's ND 16.4 / 15.5; the first-cut Schottky set (200 V on D1* / D2*, 100 V on D3* / D4*) 17.2 / 16.4;
  a 200 V Schottky in all four 20.8 / 19.9; the 1N54xx class 25.1 / 24.2; a fast-recovery class 27.8 / 26.9.
- **So the record's 20 % kick fails with silicon PN rectifiers** of either class, at both settings of the bypass. It
  starts the first-cut Schottky set with 16–22 % in hand.
- The threshold follows the diodes' drop at the seed's current: about 0.35 × V_F(0.1 A) in volts, within 4 % for the
  four single-class models [IR: a fit to these runs].
- Running, the drop costs gain and field. With the bypass: z_early 1.147 (ND) → 1.141 (Schottky set) → 1.089
  (1N54xx); each AH coil 300 → 295 → 283 A-turns; the diodes 2.05 → 2.42 → 3.11 W.
- **Reverse recovery is negligible at 120 Hz** [OC: soft commutation]: at most 15 nC and 11 mA per turn-off for the
  1N54xx class, ≤ 0.23 mW per diode as a bound. Removing Tt changes the belt by 4.5 mW of 17.5 W.

**The electrostatic pump runs from the record's −1 kV seed with real HV sticks, but it no longer self-excites, and the
sticks' capacitance and leakage cost the rings.** [IR: the stick and clamp classes]
- **Start-up:** the gain stays above 1 all the way from −1 kV to the clamp (at least 1.152 per cycle with typical
  sticks). 95 % comes in 27 cycles (0.225 s), the same as the record's ND from a consistent seed.
- **No self-excitation:** with real sticks the free pump decays from the record's free-run seed of −10 V (z 0.994
  typical, 0.940 at the datasheet's maximum leakage, 0.859 hot). It grows only from about 17 V (typical leakage),
  64 V (maximum, 25 °C) or 260 V (hot, 100 °C) on nodes 1 and 4. A contact potential or a stray charge of a few volts
  does not start it.
- **The rings,** against the record's −14.96 / +14.96 kV:

  | sticks | ring A / ring B | across | at the null (as built) | 120 Hz ripple across |
  |:--|--:|--:|--:|--:|
  | the record's ND | −14.960 / +14.963 kV | 29.92 kV | 7.62 kV/cm | 57 V p-p |
  | forward law only | −15.02 / +15.03 kV | 30.05 kV | 7.65 kV/cm | 57 V p-p |
  | + junction capacitance (0.2–0.4 pF) | −14.66 / +14.69 kV | 29.35 kV | 7.47 kV/cm | 186 V p-p |
  | + typical leakage (25 nA) | −14.65 / +14.67 kV | 29.32 kV | 7.47 kV/cm | 193 V p-p |
  | maximum leakage (2 µA, 25 °C) | −13.62 / +13.70 kV | 27.32 kV | 6.96 kV/cm | 766 V p-p |
  | hot leakage (5 µA, 100 °C) | −12.06 / +12.28 kV | 24.34 kV | 6.20 kV/cm | 1697 V p-p |
  | typical + 1 pF body capacitance [RH] | −13.63 / +13.72 kV | 27.35 kV | 6.96 kV/cm | 643 V p-p |

  The field is k (V_B − V_A) with the record's as-built k, 0.2546 (kV/cm)/kV (`sim/hub_rings_build_results.json`
  record) [OC: linear].
- **The clamps** take 1.06 W each with typical sticks (1.07 W in the record), 16 mW per 200 V device. The sticks take
  9 mW in all; at the maximum leakage 96 mW, at the hot leakage 213 mW.

**As built (on the tube-strays study's solved capacitances) the real sticks leave the electrostatic pump almost no
start margin, and hot it does not start from the deck's −1 kV at all.** [OC: the circuit; IR: the stick and clamp
classes]
- **The set** is `sim/tube_strays_results.json`'s "as built" (`sim/tube-strays-findings.md` §5). With the record's ND
  it reproduces that study exactly: z 1.0579 bare and 1.0310 with the rings' chains, ±13.86 kV (§6.2).
- **The machine (the clamped deck, the clamps' leakage in it) starts from** any seed with ND; from 122 V with typical
  sticks; from 1.0 kV at the datasheet maximum (it fails from 0.95 kV); and from 3.65 kV hot (it fails from 3.40 kV).
  On the record's capacitances the same sticks grew from 17.5 / 64 / 259 V (§4.1).
- **From the deck's −1 kV:**
  - with typical sticks it starts: 95 % at 0.575 s;
  - at the maximum leakage only just: 95 % at 1.49 s;
  - **hot, not at all: it decays to nothing.**
  - From −1.5 kV / −5 kV the maximum / hot cases reach 95 % in 0.69 / 0.30 s.
- **The rings as built,** against ND's −13.86 / +13.86 kV, 7.06 kV/cm at the null and 55 V p-p across:

  | sticks | ring A / ring B | at the null | 120 Hz ripple across | the two clamps | the 12 sticks |
  |:--|--:|--:|--:|--:|--:|
  | typical leakage | −13.38 / +13.40 kV | 6.82 kV/cm | 182 V p-p | 0.64 W | 3.5 mW |
  | maximum leakage (2 µA, 25 °C) | −12.35 / +12.42 kV | 6.31 kV/cm | 764 V p-p | 0.56 W | 87 mW |
  | hot leakage (5 µA, 100 °C) | −10.72 / +10.89 kV | 5.50 kV/cm | 1722 V p-p | 0.42 W | 198 mW |

## 1. The models

### 1.1 D1*–D4*: rectifier classes [IR datasheet-class]

Each class is a level-1 diode. Is, N and Rs go through three typical forward points at 25 °C (three linear equations
[OC]); C_J at 4 V with M and Vj gives Cjo; Tt follows the class's trr (SPICE's storage time is about 0.4 Tt in the
0.5 A / 1 A / 0.25 A test); BV sits above the rating (`sim/diodes_real.py` MAG_CLASSES).

| class | V_F at 0.1 / 1 / 3 A | Is, N, Rs | C_J at 4 V (Cjo, M, Vj) | Tt | BV |
|:--|:--|:--|:--|:--|:--|
| the record's ND (n 1) | 0.48 / 0.54 / 0.57 V | 1 nA, 1, 1 mΩ | none | none | none |
| **GP**, 1N54xx class, 3 A / 200 V, standard recovery | 0.72 / 0.85 / 0.95 V | 23.5 nA, 1.82, 24 mΩ | 30 pF (72.7 pF, 0.45, 0.65 V) | 5 µs (trr ≈ 2 µs) | 260 V |
| **FR**, 3 A / 200 V fast recovery | 0.78 / 0.95 / 1.10 V | 114 nA, 2.19, 44 mΩ | 30 pF | 0.5 µs (trr 150–250 ns) | 260 V |
| **SB**, 3 A / 200 V Schottky | 0.60 / 0.71 / 0.84 V | 84 pA, 1.10, 49 mΩ | 150 pF (450 pF, 0.5, 0.5 V) | none | 230 V |
| SB100, 3 A / 100 V Schottky | 0.45 / 0.55 / 0.66 V | 11.6 nA, 1.08, 40 mΩ | 250 pF (750 pF) | none | 120 V |

- **The models run:** ND; GP, FR and SB in all four positions; **SBM**, SB on D1* / D2* (they block 113 / 104 V) and
  SB100 on D3* / D4* (58 / 60 V with the start-up). SBM stands for `sim/parts-first-cut-findings.md`'s first cut
  (200 / 150 V Schottky); its 150 V part on D3* / D4* lies between the SB and SB100 classes [IR].
- The record's ND drops 0.54 V at 1 A: a 100 V Schottky's drop, 0.17 V below the 200 V Schottky class that D1* / D2*
  need and 0.31 V below the 1N54xx class.
- **Leakage is left out** [OC estimate]: a Si part's datasheet maximum, 5 µA at 113 V, is 0.6 mW. The Schottky's fitted
  Is understates its real leakage (µA cold, mA hot), which is milliwatts at these voltages [RH].

### 1.2 D1–D4 and the chains' diodes as HV sticks; Z1 / Z4 as avalanche strings [IR datasheet-class]

**The stick** (the 20 kV / 5 mA avalanche class of `sim/diode-stack-findings.md`; `sim/diodes_real.py` STICK):
- **20 junctions of the 1 kV class in series,** carried as one level-1 diode:
  - forward: N = 20 × 1.8; 17 V at 1 mA and 20 V at 5 mA, which gives Is 17.6 pA and Rs 375 Ω [OC: two points, N
    fixed]. At start-up currents it still drops volts: 3.8 V at 1 nA, 10.2 V at 1 µA;
  - junction capacitance: 30 pF a junction at 0 V, M 0.33: 1.5 pF the stick at 0 V, 0.37 pF at 1 kV, 0.19 pF at
    7.5 kV;
  - recovery: Tt 100 ns (the fast class); a slow stick, Tt 3 µs, as a variant;
  - avalanche: BV 24 kV (1.2 × V_RRM).
- **Per position,** by the record's ×2-rated guidance (`docs/ledger/DCCREG-design-ledger.md` §3.4), as
  `sim/parts-first-cut-findings.md` sizes them: one stick for D1, D2 (6.1 kV) and for each chain diode (7.5 kV); two
  in series for D3, D4 (13.2 kV).
- **The leakage, through Is:** a parallel element with Is = I_R and N V_T = 250 V [RH], so the leakage rises about
  linearly to a few hundred volts and saturates by about 0.75 kV.
  - One level-1 Is cannot carry both a µA leakage and the forward law: with Is = 2 µA the two-point forward fit needs a
    negative Rs [IR].
  - Three levels per stick: **typical 25 nA**, the rings' leakage ledger's basis ("tens of nA at a third of its
    rating", `sim/hub_rings_build.py` LEAKAGE); **maximum 2 µA** at 25 °C and **hot 5 µA** at 100 °C, the class's
    datasheet limits (`sim/diode-stack-findings.md`).
- **An ngspice limit, worked around** [IR]: the level-1 depletion capacitance stalls the run ("timestep too small")
  once a junction with Vj ≥ 3 V reaches 1 V forward (checked: Vj 0.7–2 V run, 3–28 V stall). The string's law
  C0 / (1 + V / (20 × 0.7 V))^0.33 is carried as Cjo′ / (1 + V / 0.7 V)^0.33 with Cjo′ matching it at 1 kV:
  within 4 % from 100 V to 13 kV, 30 % high at 10 V, 2.7 × at 0 V (`electrostatic.strings`).
- **Variants:** forward law only; + C_J and Tt; + typical, maximum or hot leakage; V_F × 2; + 1 pF body capacitance
  per stick [RH]; Tt 3 µs; + `sim/parts-first-cut-findings.md`'s 22 kΩ surge resistor on each of D1–D4.

**The clamp strings** (the ledger's first cut, 66 × 200 V; `sim/diodes_real.py` CLAMP):
- 66 avalanche (Zener) diodes of the 200 V / 5 W class: a knee of 2.5 V per e-fold per device (2.5 kΩ at 1 mA,
  500 Ω at 5 mA), 10 Ω bulk, 60 pF at 0 V; leakage typical 10 nA, maximum 0.5 µA, hot 5 µA [RH].
- Trimmed by whole parts to stand at the record's node peak, 13.227 kV, at the record's clamp peak current, 0.95 mA:
  200.5 V a device at 1 mA [IR]. The record's DZ is one diode with a hard knee and 100 kΩ.

**The varicaps, split** [the defect OC, checked; the cure IR]:
- Under `uic` ngspice starts a charge-defined capacitor uncharged: a lone Q = C·V capacitor with `.ic` −1000 V reads
  0 V at the first step, a linear one −1000 V (`electrostatic.uic_check`).
- The deck's C1v / C2v are charge-defined, so the record's −1 kV seed is redistributed in the first nanoseconds:
  within 1 µs node 1 stands at −582 V and node 4 at −905 V. The ideal ND rides that jump; real sticks would conduct
  through it, an artefact.
- So every real-diode deck splits each varicap into a linear capacitor at its t = 0 value, which takes the `.ic`, and
  a charge-defined part (C(t) − C(0))·V, zero at t = 0. C(t) is unchanged [OC]. The record's ND runs both ways.

### 1.3 The runs
- **Magnetic** (the pick: 200 turns, Ψs 0.1336 Wb-turns, 120 Hz):
  - **The kick** is the record's seed, a current frac · Ψs / L_max in L1, L2, the AH pair, La and Lb
    (`sim/pole_design.py` kick_seed). The record's is 20 %: 0.110 A, 3.48 mJ (`sim/pole_design_variants_op.json`).
  - **The criterion is the record's** (`sim/pole_design.py` size_op): 225 A-turns (N_AH × the branch peak over the
    last 4 of 40 cycles). **The threshold** is bisected from 12–40 % to 1 % of Ψs. Every failing trial decays to
    nothing within 40 cycles, so none is a late start.
  - **The start-up:** 60 cycles from the record's 20 % kick.
  - **The steady state:** 60 cycles from the record's operating seed, 30 % (`sim/rotor_parts_duty.py` SEED_FRAC), or
    1.25 × the threshold where that is more (GP 31 / 30 %, FR 35 / 34 %), as `sim/magnetic_doubler.py` analyse.
  - **Each diode** is measured by ngspice's own terminal current and power (@D[id], @D[p], equal to a 0 V ammeter's to
    1e-6 A on a run where both work). An ammeter in series with a diode that stores charge stalls ngspice here [IR].
  - **Recovery:** each turn-off's negative current lobe, its charge Q_rr and peak I_rr; Q_rr·V_R per turn-off as the
    loss bound. Level-1 charges are functions of the junction voltage, so they are lossless round a cycle [OC]; what
    recovery costs the circuit is measured against the same diode with Tt = 0.
  - **The solver:** the deck's reltol 1e-5 with ngspice's default abstol 1e-12 / vntol 1e-6. The deck's 1e-15 / 1e-9
    stall at the first turn-off of a diode with stored charge; one GP run needed reltol 3e-5 [IR].
- **Electrostatic:**
  - **the clamped run** is the record's (280 cycles, 10 000 steps a cycle, −1 kV on nodes 1 and 4), the rings over the
    last 8 cycles, 95 % as `sim/core_field.py` run computes it;
  - **the free runs** give z as the record fits it (cycles 3–11 of 12), from −10 V and from −1 kV;
  - **the threshold:** free runs of 40 cycles; "grows" when the last cycle's node-1 peak exceeds cycle 5's;
    bisection in log |V| to 10 % [IR];
  - every stick's terminal power through a 0 V ammeter; the output interpolated to 1000 points a cycle at the deck's
    maximum step [IR] (ND-ic checks it changes nothing).

## 2. Gates

| gate | result | pass |
|:--|:--|:--|
| G-MAG: the record's ND, the deck's own options, 22 mF, against `sim/ah_steady_cusp_results.json` | z_early 1.14656, belt 18.1262 W, AHt / AHb 299.82 / 300.18 A-turns (sample means, the record's statistic): within 7e-6 | ✔ |
| G-MAG: the same without the bypass, + the diodes' reverse peaks of `sim/rotor_parts_duty_results.json` | z_early 1.13942, belt 17.5764 W, 112 / 101 / 43 / 45 V: exact | ✔ |
| G-MAG: both again with the new runs' options | within 8e-5 (the coils' sample means, D4*'s peak), 5e-7 (z_early, belt) | ✔ |
| G-ES: the deck as is, against `sim/hub_rings_build_results.json` record_supply / record_supply_free | rings −14.9603 / +14.9635 kV, belt 2.1438 W, Z1 1.0698 W, 29 cycles to 95 %, z 1.19065: exact | ✔ |
| G-ES: ND run as the new runs are (the deck's maximum step, interpolated output) | the same within 6e-5; 29 cycles; z to 3e-7 | ✔ |
| G-ES: ND with the split varicaps | rings and clamps within 6e-5; 95 % in 27 cycles (not 29) and z 1.1878 (not 1.1907): the consistent seed, reported, not gated | ✔ |
| G-ENERGY: every new steady run, the belt against every dissipation and dW/dt | magnetic ≤ 1.0e-5 of the belt (10 runs); electrostatic ≤ 4.2e-7 (10 runs) | ✔ |
| G-STEP magnetic: GP, 22 mF, 2000 → 4000 steps a cycle | belt +4e-5, diodes +1e-5, coil +7e-5; z_early −0.2 % (the early cycles) | ✔ |
| G-STEP electrostatic: typical sticks, 10 000 → 20 000 steps a cycle | rings, belt, clamps, sticks within 1e-6; 27 cycles both | ✔ |
| G-UIC: a lone linear / charge-defined capacitor with `.ic` −1000 V | −1000.0 / 0.0 V at the first step | (the defect) |

## 3. The magnetic pump

### 3.1 The start kick

| D1*–D4* | V_F at 0.1 A | fails / starts, no bypass | fails / starts, 22 mF | seeded at the threshold (no bypass / 22 mF) |
|:--|--:|:--|:--|:--|
| the record's ND | 0.48 V | 15.5 / 16.4 % | 14.6 / 15.5 % | 2.33 / 2.09 mJ |
| SBM (Schottky 200 / 100 V) | 0.60 / 0.45 V | 16.4 / 17.2 % | 15.5 / 16.4 % | 2.59 / 2.33 mJ |
| SB (Schottky 200 V in all four) | 0.60 V | 19.9 / 20.8 % | 19.0 / 19.9 % | 3.74 / 3.43 mJ |
| GP (1N54xx class) | 0.72 V | 24.2 / 25.1 % | 23.4 / 24.2 % | 5.49 / 5.11 mJ |
| FR (fast recovery) | 0.78 V | 26.9 / 27.8 % | 26.0 / 26.9 % | 6.70 / 6.28 mJ |

- **The record's 20 % kick starts** ND, SBM, and SB with the bypass (narrowly: 95 % only after 0.33 s). **It does
  not start** SB without the bypass, GP or FR.
- **Why** [OC]: while the seed grows, the windings' voltage is a few volts and each conduction loses about V_F. The
  seed must therefore exceed a level proportional to the drop at its own current: 0.343 / 0.346 / 0.349 / 0.356
  × V_F(0.1 A) for ND / SB / GP / FR [IR: the fit].
- **The bypass lowers the threshold by about 1 % of Ψs** in every model.
- **Cross-check** (`sim/parts-first-cut-findings.md` §3, cjo 0, no Tt): the record's diodes 14 / 16 %, its 1N540x
  class 20 / 25 %, its Schottky set 16 %. These runs, with C_J, Tt and BV, agree to their grid. Its "Schottky in all
  four" (16 %) is a 100 V part, which D1* / D2* cannot use; a 200 V one in all four needs 20.8 % here.

### 3.2 From the record's 20 % kick

| | without the bypass | with 22 mF |
|:--|:--|:--|
| the record's ND | 95 % of the branch peak at 0.217 s, within 2 % from 0.242 s | 0.208 / 0.233 s |
| SBM | 0.225 / 0.258 s | 0.217 / 0.242 s (the coil's mean: 0.225 / 0.250 s) |
| SB | does not start | 0.325 / 0.350 s |
| GP, FR | do not start (the branch falls below 0.01 A-turns within 0.1 s) | do not start |

### 3.3 The steady state (from 30 %, GP and FR from 1.25 × their thresholds)

| D1*–D4* | z_early, none / 22 mF | branch peak, no bypass | each AH coil with 22 mF: min–max (mean) | belt, none / 22 mF | diodes, none / 22 mF |
|:--|:--|--:|:--|:--|:--|
| the record's ND | 1.139 / 1.147 | 449 A-t | 290–308 (300) A-t | 17.58 / 18.13 W | 2.01 / 2.05 W |
| SBM | 1.135 / 1.141 | 442 A-t | 286–303 (295) A-t | 17.47 / 18.01 W | 2.36 / 2.42 W |
| SB | 1.113 / 1.122 | 434 A-t | 280–298 (290) A-t | 17.21 / 17.75 W | 2.65 / 2.72 W |
| GP | 1.087 / 1.089 | 424 A-t | 274–291 (283) A-t | 16.94 / 17.47 W | 3.04 / 3.11 W |
| FR | 1.085 / 1.088 | 415 A-t | 268–285 (277) A-t | 16.70 / 17.23 W | 3.35 / 3.44 W |

- The bypass still holds each coil within ±3 % and the two coils within 16–17 A-turns, whatever the diodes.
- The belt falls with the field: the utron copper falls more than the diodes' heat rises.
- The coil means are time means; the record's sample means differ by < 0.3 A-turns.

### 3.4 Each diode's heat, and the recovery (with the bypass)

| D1*–D4* | D1* / D2* / D3* / D4* | turn-off: Q_rr, I_rr | Q_rr·V_R·f, per diode | Tt's cost to the circuit |
|:--|:--|:--|:--|:--|
| the record's ND | 0.44 / 0.44 / 0.59 / 0.59 W | none | none | — |
| SBM | 0.57 / 0.57 / 0.64 / 0.64 W | 5–7 nC, ≤ 0.4 mA (capacitive) | ≤ 0.09 mW | none (no Tt) |
| SB | 0.56 / 0.56 / 0.80 / 0.79 W | 4–7 nC, ≤ 0.4 mA (capacitive) | ≤ 0.09 mW | none (no Tt) |
| GP | 0.65 / 0.65 / 0.90 / 0.90 W | 9–15 nC, 5.6–11 mA, 6–11 µs | 0.15–0.23 mW | belt +4.5 mW (17.472 against 17.468 W) |
| FR | 0.72 / 0.71 / 1.00 / 1.00 W | 0.9–1.5 nC, ≤ 0.5 mA | ≤ 0.02 mW | < 0.1 mW |

- **The heat is the conduction** (the terminal power over the cycle) [OC: level-1 charges are lossless round a
  cycle]. In the stored-charge phase a GP diode even returns 4–7 nJ per turn-off.
- **Why recovery is so small** [OC]: the current commutates at about I_pk·ω ≈ 2 kA/s, so the charge left at the zero
  crossing is about (di/dt)·Tt² ≈ 50 nC at most, and the 21 nF snubbers absorb it. D3* / D4* turn off up to 4 times a
  cycle (the counts are in the results).
- **The reverse peaks** with the start-up: 112–115 / 102–105 / 57–59 / 58–60 V, as `sim/parts-first-cut-findings.md`
  finds; no diode approaches its BV.

## 4. The electrostatic pump and the rings

### 4.1 The gain against the seed

| sticks | z from −10 V | z from −1 kV | grows from (fails at) | least z, −1 kV to the clamp |
|:--|--:|--:|:--|--:|
| the record's ND, the deck as is | 1.1907 | (scale-free) | any seed | 1.183 |
| the record's ND, split | 1.1878 | 1.1886 | any seed | 1.162 |
| forward law only | 0.9995 | 1.187 | — | 1.157 |
| + C_J, Tt | 0.996 | 1.184 | — | 1.153 |
| typical leakage | 0.994 | 1.184 | 17.5 V (16.5 V) | 1.152 |
| maximum leakage | 0.940 | 1.170 | 64 V (60 V) | 1.124 |
| hot leakage | 0.859 | 1.142 | 259 V (246 V) | 1.024 |
| typical, V_F × 2 | 0.995 | 1.179 | — | 1.141 |

- **The record's z, 1.191 "at start-up", is a large-signal gain** [OC]. With real sticks it holds from about 1 kV up;
  at tens of volts the sticks' drop (4–10 V each at nA–µA), their capacitance and their leakage take it below 1
  (Figure (c)).
- **What starts the pump** is therefore a seed of at least tens of volts, a few hundred hot, on the varicaps. The
  record's −1 kV is enough at every leakage level.

### 4.2 The start-up from −1 kV

| | cycles to 95 % | time |
|:--|--:|--:|
| the record's ND, the deck as is (the record) | 29 | 0.242 s |
| the record's ND, split (a consistent −1 kV) | 27 | 0.225 s |
| sticks: forward only, + C_J, typical, V_F × 2, Tt 3 µs, 22 kΩ | 27 | 0.225 s |
| + 1 pF body capacitance | 26 | 0.217 s |
| maximum leakage | 28 | 0.233 s |
| hot leakage | 36 | 0.300 s |

The record's 29 cycles carry the deck's `uic` artefact: its effective seed is −0.58 / −0.90 kV, not −1 kV (§1.2).

### 4.3 The rings and the sticks' leakage
- **The forward law alone changes nothing material:** the drops raise node 1's swing from 7.53 to 7.58 kV, so the
  rings stand 60 V higher (headline table).
- **The sticks' own capacitance is what costs** [OC: a capacitive path across each chain diode]. 0.2–0.4 pF across
  each diode takes 0.70 kV off the gap (0.57 kV below the record) and triples the 120 Hz ripple, 57 → 186 V p-p
  (0.014 → 0.047 kV/cm at the null). A 1 pF body capacitance [RH] takes a further 2.0 kV (27.35 kV across) and gives
  643 V p-p.
- **Typical leakage (25 nA) costs 26 V more.** Each chain diode then leaks 19–22 nA; the rings' own 100 GΩ load each
  with 0.15 µA.
- **At the datasheet maximum (2 µA)** each chain diode leaks 1.4–1.7 µA, ten times the rings' load: the gap is
  27.32 kV, 2.6 kV (8.7 %) below the record's, 6.96 kV/cm, with 766 V p-p. **Hot (5 µA)** it is 24.34 kV, 5.6 kV
  (18.7 %) below, 6.20 kV/cm.
- So the chain diodes need the selection `sim/parts-first-cut-findings.md` proposes (I_R ≤ 25 nA at 7.5 kV,
  25 °C) [IR], and cool: silicon leakage roughly doubles every 10 K [RH].
- **Recovery is irrelevant:** a 3 µs stick changes the rings by 1 V and the belt by 0.1 mW.

### 4.4 The clamps' and the sticks' heat

| sticks | each clamp (per device) | clamp peak current / node peak | D1, D2 / D3, D4, each | the 8 chain diodes, each | all 12 |
|:--|:--|:--|:--|:--|--:|
| the record's ND and DZ | 1.070 W (16.2 mW) | 0.95 mA / 13.23 kV | — | — | (5e-5 W, the remainder) |
| typical | 1.058 W (16.0 mW) | 0.85 mA / 13.21 kV | 1.4 / 2.8 mW | 0.07–0.12 mW | 9.1 mW (1.2 mW leakage) |
| maximum leakage | 1.019 W (15.4 mW) | 0.83 mA / 13.20 kV | 5.5 / 15.3 mW | 4.8–9.0 mW | 96 mW (88 mW) |
| hot leakage | 0.950 W (14.4 mW) | 0.78 mA / 13.19 kV | 11.8 / 34.1 mW | 10–21 mW | 213 mW (205 mW) |
| typical + 22 kΩ on D1–D4 | 1.058 W | 0.85 mA | 2.3 / 4.2 mW | as typical | 13.7 mW |

- The real string's soft knee conducts longer at a lower peak (0.85 mA against 0.95 mA) [IR: the knee].
- The leakage's power comes out of the clamps' share: the belt stays 2.06–2.15 W.
- Against `sim/parts-first-cut-findings.md`: its bound for D1–D4 at the maximum leakage, about 80 mW, holds (42 mW
  here); its chain duty, 0.15 µA average, matches (0.14–0.15 µA).

## 5. What this contradicts in the record

1. `docs/ledger/DCCREG-design-ledger.md`:371–372, self-excitation: "any seed in the growing mode (a contact potential,
   a triboelectric charge) multiplies by z every cycle [OC]". True for ideal diodes only: with real sticks the free
   pump decays below about 17 V (typical leakage), 64 V (maximum) or 260 V (hot) (§4.1).
2. `docs/ledger/DCCREG-design-ledger.md`:370 and :657, "z is 1.191 at start-up": with real sticks z is 0.86–0.99 at
   the record's free-run seed (−10 V); 1.14–1.19 from −1 kV (§4.1).
3. `docs/ledger/DCCREG-design-ledger.md`:537, :678, :772; `sim/hub-rings-build-findings.md`:305;
   `docs/rings-design.md`:198; `docs/bench-test-rings.md`:157, "95 % at 0.24 s (29 cycles)": the 29 cycles carry the
   deck's `uic` artefact. From a consistent −1 kV, 27 cycles (0.225 s), with ND and with typical sticks alike; 0.30 s
   hot (§4.2).
4. `docs/ledger/DCCREG-design-ledger.md`:101, :503, :676 (±14.96 kV), :102 and :541 (57 V p-p, 0.014 kV/cm p-p);
   `sim/hub-rings-build-findings.md`:274, :306, :317; `docs/rings-design.md`:45, :202;
   `docs/bench-test-rings.md`:158: with real sticks −14.65 / +14.67 kV, 7.47 kV/cm at switch-on and 193 V p-p,
   0.049 kV/cm p-p (×3.4), from the sticks' capacitance; at the maximum leakage 6.96 kV/cm and 0.195 kV/cm p-p
   (§4.3).
5. `sim/diode-stack-findings.md`:44–45, "Their ~1 pF and µA leakage are small next to the 1 nF-class capacitors": the
   record's chains are 100 pF, and there 1 pF of body capacitance or 2 µA of leakage each cost about 2.6 kV across the
   gap.
6. `sim/hub_rings_build.py`:253 (LEAKAGE), "a 20 kV stack leaks tens of nA at a third of its rating": that is a
   typical or selected part. The class's datasheet maximum, 2 µA (`sim/diode-stack-findings.md`), is 80 × more; the
   ledger's 3e11 Ω a stage holds only with selected parts.
7. `docs/ledger/DCCREG-design-ledger.md`:284, :626, :837, "0.54 V … a Schottky-class drop": it is a 100 V Schottky's;
   the 200 V Schottky class that D1* / D2* need drops 0.71 V, and needs a 20.8 % kick in all four positions.
8. `docs/ledger/DCCREG-design-ledger.md`:285 and :628, "the threshold is 16 %": that is the deck's ND (16.4 %). With
   the first-cut Schottky set it is 17.2 % (16.4 % with the bypass); with silicon PN rectifiers 25–28 %, above the
   record's 20 % kick (§3.1).
9. `sim/pole-design-findings.md`:95 and :98–99 ("silicon diodes (≈ 0.55 V)"; "once kicked to ≥ 8–10 % of Ψ_s … the
   diode drop then costs only about 2 W") and `sim/pole_design.py`:291 (the label "Si (0.55 V @ 1 A)"): a real silicon
   rectifier drops 0.85 V at 1 A; the pick then needs a 25 % kick and its diodes take 3.0–3.1 W.

## 6. As built: the tube-strays study's capacitances

### 6.1 The set and the runs
- **The set** [OC: that study's 3-D field solve; IR: its cosine C(θ) between the two solved angles] is
  `sim/tube_strays_results.json` decks.sets["as built"], read by the script as that study's deck takes it:
  - C1v = C2v 133.0 ↔ 446.0 pF: node 1's solved total to REF, unaligned / aligned (199.2 / 512.2 pF,
    `sim/tube-strays-findings.md`:206), less its 66.2 pF fixed stray. So the first Ca plate's swing is in it; the
    vanes alone are 128.4 / 450.6 pF (:25);
  - Ca = Cb 481.6 pF: 480.5 pF as laid out (`sim/tube-strays-findings.md`:27) plus the 1.1 pF from node 1 to node 2;
  - the node strays 66.2 pF (nodes 1, 4) and 24.5 pF (nodes 2, 3); across the hub 0.048 pF (nodes 1–4) and less;
  - the rings 5.87 pF each to REF and 1.50 pF between them; 0.015 / 0.007 pF from node 1 (4) to ring A (B) / B (A).
- **Applied as that study applies it:** `sim/tube_strays.py` deck_strays replaces the node strays and adds the
  couplings. The script replicates it (`apply_strays`) rather than importing it, because that module rebinds
  `sim/core_field.py`'s deck at import [IR].
- **The cases:** (a) the record's ND, the varicaps split (§1.2); (b) typical, (c) maximum and (d) hot leakage, with the
  sticks and clamps of §1.2.
- **The free runs:** 12 cycles at 20 000 steps a cycle, z as the record fits it (cycles 3–11), with the rings' chains,
  from −10 V and −1 kV. For the gate, also bare (no rings) from −1 kV, as that study runs it.
- **The start trials** [IR]:
  - the clamped deck itself (the machine, the clamps and their leakage in it) from a seed v0 on nodes 1 and 4;
  - 120 cycles, doubled while undecided, up to 960; bisection in log |v0| to 10 %, up to 10 kV;
  - a trial grows once it reaches the clamp, or while its gain over the last five cycles is above 1 and not falling
    (against the five cycles 20 earlier);
  - it fails once it has decayed 100×, or while that gain is below 1 and not rising.
- **Why not §1.3's rule** (free runs of 40 cycles, the last peak above cycle 5's) [OC: the runs]:
  - as built the pump's surplus is small, and the rings' chains take tens of cycles to charge;
  - while they charge, the chains' reverse voltage rises, and their sticks' leakage with it;
  - so a seed near the threshold grows for 20–40 cycles and then decays. With typical sticks §1.3's rule reads
    "grows" at 67 V, where the gain over cycles 30–39 is 0.9997; the machine from 75 V decays (0.9991 over its last
    five of 120 cycles).
  - §1.3's rule is still run as built (the results' thresholds_40), for comparison with §4.1.
- **The clamped runs** [IR]:
  - from the deck's −1 kV, and from 1.25 × the threshold (rounded up to 0.5 kV) where the threshold is above 0.5 kV;
  - each as long as `sim/tube_strays.py` _cycles gives from its seed at its 12-cycle free gain,
    280 + 1.3 ln(13.227 kV / |v0|) / ln z cycles;
  - each doubled until the rings settle (the last ten cycles within 0.3 %);
  - ND runs that study's own 390 cycles.

### 6.2 Gates

| gate | result | pass |
|:--|:--|:--|
| G-AB: the as-built set with the deck as is, against `sim/tube_strays_results.json` decks.table["as built"] | z 1.0578642 bare and 1.0309849 with the rings' chains (to 2e-10); rings −13.8599 / +13.8625 kV, 7.0575 kV/cm, 95 % at 0.625 s: exact; belt 0.64665 W (−1.6e-6) | ✔ |
| G-AB: the same with the split varicaps | rings, field and belt within 3e-5; the late gain (cycles 30–39 of 40) 1.05771 bare and 1.03870 with the chains, against the deck's 1.05771 / 1.03838 (1e-6 / 3e-4). z over cycles 3–11 (1.0544 / 1.0285) and 95 % at 0.525 s carry the consistent seed's start: reported, not gated (§1.2) | ✔ |
| G-ENERGY: the four clamped runs with sticks that start | ≤ 9e-8 of the belt | ✔ |
| G-STEP: each threshold's two bracketing trials at 20 000 steps a cycle | the same verdicts; the last five cycles' gain within 2e-6 | ✔ |

### 6.3 The gain, and the seed it needs

| sticks | z from −10 V | z from −1 kV | the machine starts from (fails at) | §1.3's rule, as built | on the record's capacitances (§4.1) |
|:--|--:|--:|:--|--:|--:|
| (a) the record's ND, split | 1.0285 | 1.0298 | any seed (1 V) | any seed | any seed |
| (b) typical leakage | 0.9966 | 1.0244 | 122 V (115 V) | 67 V | 17.5 V |
| (c) maximum leakage (25 °C) | 0.9518 | 1.0038 | 1.00 kV (0.95 kV) | 0.81 kV | 64 V |
| (d) hot leakage (100 °C) | 0.8808 | 0.9672 | 3.65 kV (3.40 kV) | 2.21 kV | 259 V |

- **The seed rises 7–16× against the record's capacitances** [OC]. The sticks' drop and leakage take a share of
  each cycle's charge that falls with the amplitude. The seed must be large enough for that share to fall below the
  pump's surplus, and as built the surplus with the chains is 0.031 a cycle, against the record's 0.191
  (`sim/tube_strays_results.json` decks.table: z_rings_start 1.0310 / 1.1907).
- **The clamps' own leakage counts** [OC: the same deck less the clamps; the results' free_vs_machine]. The gain
  over cycles 30–39 from the same seed, free (no clamps) against the machine:
  - at the maximum leakage from 0.81 kV, 1.0018 against 0.983: the free pump grows, the machine decays;
  - hot from 3.16 kV, 1.021 against 0.974;
  - with typical sticks from 75 V, 0.9998 against 0.9994.
  - Each clamp string's leakage (0.5 µA at the maximum, 5 µA hot [RH]) drains nodes 1 and 4 directly.
- **So the deck's −1 kV seed is 8× the typical sticks' threshold, on the maximum's, and 0.27× the hot one**
  (Figure (e), where ▼ marks each threshold).

### 6.4 The start-up

| sticks | from | it starts | 95 % at |
|:--|--:|:--|--:|
| the record's ND, the deck as is (the tube-strays study's run) | −1 kV | yes | 0.625 s (75 cycles) |
| (a) the record's ND, split | −1 kV | yes | 0.525 s (63) |
| (b) typical leakage | −1 kV | yes | 0.575 s (69) |
| (c) maximum leakage | −1 kV | yes, on its threshold | 1.49 s (179) |
| (c) maximum leakage | −1.5 kV | yes | 0.69 s (83) |
| (d) hot leakage | −1 kV | **no:** it decays to nothing (node 1's peak 1.85 kV in the first cycle, 1e-17 kV by cycle 280) | — |
| (d) hot leakage | −5 kV | yes | 0.30 s (36) |

- **At the maximum leakage, from −1 kV,** node 1's peak takes 0.46 s to reach 2 kV and 0.90 s to reach 3 kV. It then
  reaches the clamp at 1.43 s (Figure (f)). The least gain on the way is 0.996, at cycle 11; the gain is 1.0025 by
  cycle 40 and 1.0074 by cycle 80 [OC: the chains charging while the amplitude grows].
- **The steady state does not depend on the seed** [OC]: the maximum-leakage runs from −1 kV and −1.5 kV agree to
  1e-8 kV on the rings and 5e-6 on the belt.

### 6.5 The rings, the field at the null, the ripple and the heat

| sticks | ring A / ring B | across | at the null | 120 Hz ripple across | the belt | each clamp (per device) | clamp peak current / node peak | the 12 sticks (their leakage) |
|:--|--:|--:|--:|--:|--:|--:|--:|--:|
| (a) the record's ND, split | −13.859 / +13.862 kV | 27.72 kV | 7.06 kV/cm | 55 V p-p (0.014 kV/cm) | 0.647 W | 0.322 W (4.9 mW) | 0.47 mA / 13.18 kV | — |
| (b) typical | −13.385 / +13.402 kV | 26.79 kV | 6.82 kV/cm | 182 V (0.046 kV/cm) | 0.649 W | 0.321 W (4.9 mW) | 0.30 mA / 13.04 kV | 3.5 mW (1.1 mW) |
| (c) maximum | −12.347 / +12.421 kV | 24.77 kV | 6.31 kV/cm | 764 V (0.194 kV/cm) | 0.651 W | 0.280 W (4.2 mW) | 0.26 mA / 13.01 kV | 87 mW (85 mW) |
| (d) hot (from −5 kV) | −10.720 / +10.886 kV | 21.61 kV | 5.50 kV/cm | 1722 V (0.438 kV/cm) | 0.616 W | 0.210 W (3.2 mW) | 0.17 mA / 12.94 kV | 198 mW (195 mW) |

- **The field at the null** is k (V_B − V_A), k = 0.2546 (kV/cm)/kV (`sim/hub_rings_build_results.json` record), and
  its ripple is k × the gap's peak-to-peak [OC: linear].
- **The sticks cost a little more of the gap as built than on the record's capacitances** [OC]: 0.93 kV typical
  (0.60 kV, §4.3), 2.95 kV at the maximum (2.60 kV) and 6.12 kV hot (5.58 kV). That is 3.4 / 10.7 / 22.1 % of ND's
  27.72 kV.
- **The field at the null with typical sticks, 6.82 kV/cm,** is 10.5 % below the record's 7.62 kV/cm
  (`docs/ledger/DCCREG-design-ledger.md`:102) and 3.4 % below the as-built ND's 7.06 kV/cm.
- **The ripple** comes from the sticks' capacitance and leakage, as in §4.3: 55 → 182 V p-p across with typical sticks
  (98 / 96 V on ring A / B).
- **The clamps carry less of the same belt** (0.62–0.65 W). The sticks' leakage takes 85 mW of it at the maximum and
  195 mW hot. Each chain diode leaks 19–22 nA typical, 1.4–1.7 µA at the maximum and 3.4–4.3 µA hot.

### 6.6 What this adds against the record
1. `docs/ledger/DCCREG-design-ledger.md`:443, "The pump barely self-excites" (as built): with real sticks it does not
   self-excite. From −10 V it decays (z 0.997 typical, 0.952 at the maximum, 0.881 hot), and the machine starts only
   from 122 V, 1.0 kV or 3.65 kV (§6.3).
2. `docs/ledger/DCCREG-design-ledger.md`:443, :590 and :797; `sim/tube-strays-findings.md`:254, "±13.86 kV,
   7.06 kV/cm, 95 % in 0.63 s" as built: that is the record's ND on the deck's own start.
   - With typical sticks: −13.38 / +13.40 kV, 6.82 kV/cm, 182 V p-p, and 95 % at 0.575 s from a consistent −1 kV.
   - At the maximum leakage: 6.31 kV/cm, and 95 % at 1.49 s from −1 kV.
   - Hot: no start from −1 kV (§6.4, §6.5).
3. On the record's capacitances only:
   - `docs/ledger/DCCREG-design-ledger.md`:715, the gain: "with real HV sticks below 1 under about 17 V (260 V hot),
     so a seed is needed";
   - :102, "With real HV sticks 7.47 kV/cm at switch-on";
   - this file's §4.1 (:269–270), "The record's −1 kV is enough at every leakage level".
   - As built, the seed is 122 V to 3.65 kV, −1 kV does not start the hot pump, and the field with typical sticks is
     6.82 kV/cm.
4. **For the designer** (not a contradiction): `docs/ledger/DCCREG-design-ledger.md`:797 offers "Accept it, or win the
   margin back". With real sticks, accepting it as built means one of two things:
   - the selected, cool parts of `sim/parts-first-cut-findings.md` (I_R ≤ 25 nA at 7.5 kV) and a seed of at least
     about 1 kV;
   - or a seed of at least 3.65 kV, for hot leakage.
   - The sticks' and the clamps' leakage are the bench's to settle (`docs/bench-test-rings.md`), OPEN until it measures
     them.

## Caveats
- **[IR] datasheet-class models:** typical curves at 25 °C; the stick as one level-1 string; the leakage element's
  shape (N V_T 250 V [RH]); the stick capacitance carried with Vj 0.7 V; the clamp's knee; the split varicaps. No
  vendor part is modelled.
- **[RH]:** the body capacitance (1 pF), the hot leakage of the clamps, the leakage's temperature law. The clamps' hot
  leakage (5 µA a string) is load-bearing for §6's hot threshold (3.65 kV).
- **Not modelled:** temperature (V_F falls about 2 mV/K a junction hot, the leakage rises); the HV parts' stray
  capacitance to their surroundings (§3–§5 keep the deck's 20 pF a node; §6 takes the solved node strays, but not the
  sticks' own strays); corona; a physical kick source (the K4 dump of `sim/parts-first-cut-findings.md`); speeds below
  1200 rpm relative.
- **The start criterion is the record's** (40 cycles); every failing trial decayed, so the bracketing is sharp.
- **§6's start trials are a rule of this study** [IR]. Every bracketing trial is decided within 240 cycles. Two trials
  far below the typical sticks' threshold (1 V and 32 V) are still undecided at 960 cycles, with gains of 0.9989; they
  count as failing.
