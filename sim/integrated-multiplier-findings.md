# The multiplier stacked into the doubler — findings

**Source:** `sim/integrated_multiplier.py` → `sim/integrated_multiplier_results.json` (about 610 ngspice runs, 20
min on 4 processes). The schematic is `docs/schematic-integrated-multiplier.svg`, drawn by
`docs/make_integrated_multiplier_schematic.py`.

**Status:**
- **DECIDED** (the designer, 2026-10-10):
  - the charge-pump multipliers are stacked into the doubler, not built as a separate circuit tapping nodes 1 and 4.
    The designer's sketch, read back and confirmed: C3–C6 and D5–D8 are the new parts, and D3 / D4 are rerouted onto
    the ladder;
  - the clamps Z1 / Z4 stay on nodes 1 / 4;
  - the polarity is free; the rings' supply and C3–C6 are worked out here;
  - the doubler, the rings and the magnetic pump's Schottky circuit stay on one revolving body (the rotor, as the
    record: `docs/ledger/DCCREG-design-ledger.md` §3.1);
  - the stack of the whole turbine will change; the magnetic pump, the sphere, its AH and the field interface stay
    as they are for now.
- **PROPOSED** here: bipolar operation (chain 2 reversed), C1 / C2 in phase, one ring stage per chain, C3–C6 at
  180 pF, and the ring stages' and the rings' 100 pF capacitors.
- **Tags:**
  - [OC]: the circuit laws and the topological findings;
  - [IR]: the as-built capacitance set (`sim/tube_strays_results.json` decks.sets['as built']), the real parts' models
    (`sim/diodes_real.py`), the 100 pF parts (the record's chain value), the start rule;
  - [RH]: the new nodes' strays, 24.5 pF each, as nodes 2 / 3 as built. No stack is drawn.

**The circuit as sketched** (positive, every diode pointing away from the shaft; l1 / l2 / r1 / r2 name the sketch's
unlabelled dots):
- **as in the record:** the varicaps C1 (node 1) and C2 (node 4), Ca (1–2), Cb (3–4), and D1 / D2 from the shaft to
  nodes 2 / 3;
- **two capacitor columns:** C3 (2–l1) and C5 (l1–l2) on node 2; C4 (3–r1) and C6 (r1–r2) on node 3;
- **two chains, each to the far varicap:**
  - 0 → D1 → 2 → D3 → r1 → D6 → l2 → D7 → 4, in place of the record's D4;
  - 0 → D2 → 3 → D4 → l1 → D5 → r2 → D8 → 1, in place of its D3.

## Headline
- **As sketched, the circuit pumps but cannot feed the rings** [OC]. Two reasons:
  - **One polarity.** A diode chain charges its end with its own sign, and as drawn both chains point away from the
    shaft, so every node sits on the same side of it. The rings need ring A below the shaft and ring B above it, so
    that the null sits at the shaft's potential (ledger §3.6). One polarity also halves the field at the same bead
    stress.
  - **Nothing above nodes 1 / 4.** The clamps hold those at V_op, 13.1 kV, and the ladder's top reaches only 7.3–7.7
    kV (§1). The rings need 14.96 kV.
- **How it works** (PROPOSED; the schematic):
  1. **Reverse chain 2** (D2, D4, D5, D8). Side A then runs negative and side B positive, symmetric about the shaft.
  2. **Swing C1 and C2 in phase,** C2's rotor sectors aligned with C1's rather than half a pitch apart. The bipolar
     pump needs it: as built, in antiphase it does not pump (z 1.0000).
  3. **Continue each chain one stage past its varicap node to its ring.**
     - Ring B: C7 from l2, with D9 (4 → xb) and D10 (xb → ring B).
     - Ring A: the mirror image, C8 from r2 with D11 and D12.
     - Each ring sits on a 100 pF smoothing capacitor to the shaft.
  4. **C3–C6 at 180 pF.** As built, at the record's V_op, the rings settle at ±14.93 kV with ideal diodes. The
     record's level is ±14.96 kV; 200 pF would give ±14.98 kV, over it.
- **As built, against the record's supply** (the solved strays; ideal diodes unless stated):

| | the record: separate chains | the proposal |
|:--|--:|--:|
| gain z at start-up, ideal diodes | 1.0322 | 1.0142 |
| the rings, ideal diodes | ±13.86 kV | ±14.93 kV |
| the field at the null | 7.06 kV/cm | 7.60 kV/cm |
| 95 % of the rings, from a consistent 1 kV | 0.53 s | 1.45 s |
| typical sticks: z from 1 kV, smallest seed, rings, field | 1.0244, 122 V, ±13.39 kV, 6.82 kV/cm | 1.0129, 51 V, ±14.67 kV, 7.47 kV/cm |
| maximum leakage | 1.0038, 1.0 kV, ±12.38 kV, 6.31 kV/cm | 1.0039, 947 V, ±14.40 kV, 7.33 kV/cm |
| hot | 0.9672, 3.65 kV, ±10.80 kV, 5.50 kV/cm | 0.9870, 4.87 kV, ±13.95 kV, 7.10 kV/cm |
| HV sticks | 14: D3 / D4 at 13.2 kV take two each | 12, one each, all ≤ 6.8 kV |
| Ca / Cb's DC | 6.9 kV | 13.2 kV |
| the reference link | 0.165 mA rms | 0.02 µA rms; the counter-rotor can float |
| the varicaps' 120 Hz torque | 63 mN·m p-p | 191 mN·m p-p |
| the clamps | 0.64 W | 0.63 W |

- **What it gives:**
  - the record's ring level as built: ±14.93 kV with ideal diodes and ±14.67 kV with typical sticks, where the record
    reaches ±13.86 / ±13.39 kV. So the field at the null is 7.60 / 7.47 kV/cm, not 7.06 / 6.82;
  - with real sticks it holds better than the record at every leakage. Their margins at 1 kV meet at the datasheet's
    maximum (1.004 both), the proposal is ahead hot, and its typical seed is 51 V, not 122 V;
  - 12 single sticks instead of 14, with no position above 6.8 kV;
  - no current through the bearing link: Q1 = −Q2, so the counter-rotor pumps the same floating on 100 pF to the shaft
    (z 1.0142), where the record stops (1.0001).
- **What it costs:**
  - **the ideal gain:** 1.014 against 1.032. A bipolar pump's clamp diodes give back to each varicap part of what its
    cross diodes delivered (§2). Real sticks narrow the gap, as above;
  - **Ca / Cb at 13.2 kV DC** (the record's 6.9 kV). Their mounts' creepage roughly doubles: the ledger's 40 mm on
    PTFE is for 7.5 kV between plates (§3.4);
  - **the rings' level rests on the new nodes' strays:** ±16.3 kV with none, ±14.5 kV at 40 pF (24.5 pF is assumed).
    Set the clamp strings on the bench before the hub sees the rings: each 200 V part moves V_op 1.5 %. Or fix C3–C6
    once a stack is drawn;
  - **the torque ripple:** in phase, the two stacks' pulls add, and the varicaps' 120 Hz ripple triples;
  - **the start-up:** 95 % in 1.45 s, not 0.53 s.

## 1. The sketch as drawn (the record's 2-D set)
**The gate:** the record's doubler gives z 1.3087 here (`sim/core_field_results.json` 'free none': 1.3095).

**The free gain over C3–C6** (16 cycles; the new nodes without strays; 40 cycles agree to 0.002):

| C3–C6 | 1 pF | 10 pF | 47 pF | 100 pF | 220 pF | 451 pF | 2 nF | 10 nF |
|:--|--:|--:|--:|--:|--:|--:|--:|--:|
| z | 1.3085 | 1.2950 | 1.2403 | 1.1699 | 1.0958 | 1.0998 | 1.0699 | 1.0024 |

- As C3–C6 shrink, each chain becomes a plain string of diodes and the circuit becomes the record's doubler. Large
  ladder capacitors take the gain toward 1 [OC]. Between 220 and 451 pF the trend reverses by 0.004.

**Clamped at the record's V_op** (the clamps at +V_op, as the circuit is positive):

| | the record | the sketch, 100 pF | the sketch, 451 pF |
|:--|:--|:--|:--|
| nodes 1 / 4 | −13.23 … −5.70 kV | +5.47 … +13.21 | +6.59 … +13.22 |
| nodes 2 / 3 | −6.12 … 0 | 0 … +5.71 | 0 … +3.93 |
| l1 / r1 | — | +2.55 … +6.18 | +1.81 … +5.47 |
| l2 / r2 | — | +4.14 … +7.73 | +3.62 … +7.30 |
| worst reverse peak | 13.18 kV (D3 / D4) | 5.96 (D3 / D4) | 7.01 (D7 / D8) |
| the clamps | 2.14 W | 1.21 W | 1.41 W |

- Every node sits on one side of the shaft, and none rises above nodes 1 / 4.
- The ladder splits the record's 13.2 kV cross diodes into 4–7 kV steps.

## 2. Polarity: why bipolar, and why in phase
- **The rings need both polarities** [OC].
  - The field at the null is k (V_B − V_A), and each ring stands no more than about 15 kV from the AH: its polar bead
    sets that (ledger §3.6).
  - ±14.96 kV gives twice the field of one polarity at the same bead stress.
- **One polarity per chain** [OC]. Reversing chain 2 makes side A negative and side B positive.
- **In phase** [OC]. With opposite charges on C1 and C2, their nodes swing against each other only when the
  capacitances swing together. The cross transfers need that swing.
- **The bipolar doubler** (four diodes, 2-D), against C2's lag behind C1:

| lag | 0° | 30° | 60° | 90° | 120° | 150° | 180° (the record) |
|:--|--:|--:|--:|--:|--:|--:|--:|
| z | 1.0977 | 1.0957 | 1.0896 | 1.0798 | 1.0664 | 1.0493 | 1.0444 |

- **Every mirror-symmetric diode set on the four-node doubler** (mirror and negate; 228 sets, both phasings, 456
  runs):
  - 21 of them pump bipolar;
  - the best gives 1.0977 in phase and 1.0444 in antiphase, the same as the bipolar doubler. No four-diode
    arrangement does better.
- **Why bipolar costs gain** [OC]. In the record's unipolar pump every diode event adds charge of the varicap's own
  sign. In the bipolar one, D1 recharges Ca at each lift by bringing positive charge from the shaft into node 1, so
  part of what Ca delivered at the last collection comes back. Its z of 1.10 against 1.31 (2-D) is that structural
  penalty.
- **The bipolar ladder** (100 pF, 2-D): z 1.0456 in phase, 1.0111 in antiphase.

## 3. The rings: one stage past each varicap node
- **Why a stage** [OC]. Nothing rises above nodes 1 / 4 (§1). A stage coupled to a node that swings against node 4
  lifts ring B by that node's swing.
- **The coupling node** (C3–C6 200 pF):
  - the column tops (l2 / r2, the pick) give ±14.98 kV, the record's level at the record's V_op;
  - l1 / r1 give ±15.34 kV;
  - nodes 2 / 3 give ±16.61 kV, with a worst reverse peak of 9.5 kV.
- **Without the ladder** (the bipolar doubler, its ring stages on nodes 2 / 3):
  - the rings reach ±18.21 kV, D3 / D4 see 13.2 kV and take two sticks each, and z is 1.0095;
  - so the designer's ladder is what brings the rings to the record's level at the record's V_op, and what splits the
    cross diodes' stress.
- **The ring stage's capacitor:** 47 / 100 / 220 pF give ±14.67 / 14.98 / 15.17 kV.
- **The smoothing capacitor:** 47 / 100 / 330 pF leave the rings at ±14.97 / 14.98 / 14.98 kV, with a ripple at the
  null of 0.012 / 0.006 / 0.002 kV/cm p-p.

## 4. Sizing C3–C6 (as built, ideal diodes, the record's V_op)
Each clamped run starts from a consistent 1 kV and runs until the rings settle.

| C3–C6 | z (free) | the rings | the field at the null | each clamp | worst reverse peak |
|:--|--:|--:|--:|--:|--:|
| 47 pF | 1.0098 | ±14.09 kV | 7.17 kV/cm | 13.6 µA | 6.98 kV |
| 100 pF | 1.0126 | ±14.62 | 7.45 | 19.2 | 6.72 |
| 150 pF | 1.0138 | ±14.85 | 7.56 | 22.4 | 6.67 |
| **180 pF** | **1.0142** | **±14.93** | **7.60** | **23.9** | **6.77** |
| 200 pF | 1.0144 | ±14.98 | 7.63 | 24.7 | 6.83 |
| 220 pF | 1.0144 | ±15.01 | 7.64 | 25.4 | 6.88 |
| 330 pF | 1.0133 | ±15.14 | 7.71 | 28.3 | 7.10 |

- **The pick** [IR]: the largest C3–C6 whose rings stay at or below the record's ±14.96 kV with ideal diodes, because
  the polar bead sits 0.4 % under its rating there. That is 180 pF.
  - The gain is flat from 150 to 220 pF, and every position takes one stick.
- **The pick's steady state** (`pick.steady`):
  - **nodes:** 1 at −13.18 … −7.03 kV, 4 at +7.03 … +13.18; 2 at 0 … +4.52, 3 at −4.52 … 0; l1 at −6.41 … −3.67, r1
    at +3.67 … +6.41; l2 at +5.91 … +8.61, r2 at −8.61 … −5.91; xa at −14.94 … −12.77, xb at +12.77 … +14.94; the
    rings at ∓14.93 kV, 13 V p-p ripple each;
  - **reverse peaks:** D1 / D2 4.52 kV; D3 / D4 6.41; D5 / D6 4.95; D7 / D8 6.77; D9 / D11 6.64; D10 / D12 2.16;
  - **each capacitor's DC:** Ca / Cb 11.6–13.2 kV; C3 / C4 6.4–9.0; C5 / C6 11.6–12.8; C7 / C8 6.3–6.9; Csa / Csb
    14.9;
  - **power:** the clamps take 23.9 µA each (0.52 mA peak), 0.63 W in all, from the belt's 0.634 W;
  - **start-up:** from a consistent 1 kV the rings rise without overshoot, 95 % in 174 cycles (1.45 s).
- **The new nodes' strays** [RH] (C3–C6 200 pF):

| each new node's stray | 0 pF | 5 pF | 24.5 pF (assumed) | 40 pF |
|:--|--:|--:|--:|--:|
| z | 1.0165 | 1.0161 | 1.0144 | 1.0131 |
| the rings | ±16.33 kV | ±15.94 kV | ±14.98 kV | ±14.54 kV |

- The rings' level rests on these strays. Plate capacitors built like Ca / Cb would sit near 25 pF and discrete HV
  capacitors near 5 pF [RH]; the latter would put the rings about 7 % over the bead's level until V_op is trimmed
  down.

## 5. Real parts (as built)
**The models:** `sim/diodes_real.py`'s 20 kV stick and its 66-part clamp string. Each position takes one stick, by
twice its reverse peak against the stick's rating, as the record's guidance sizes them.

**The gate:** the record's supply with typical sticks gives z 1.024416 from 1 kV here, and 1.024416 there
(`sim/diodes_real_results.json` electrostatic_as_built).

| leakage | | z from 10 V | z from 1 kV | smallest seed that starts it | the rings | the field at the null | ripple, A / B | 95 % |
|:--|:--|--:|--:|--:|--:|--:|--:|--:|
| typical | the proposal | 0.9980 | 1.0129 | 51 V | ±14.67 kV | 7.47 kV/cm | 20 V | 1.53 s from 1 kV |
| | the record | 0.9966 | 1.0244 | 122 V | −13.38 / +13.40 kV | 6.82 | 98 / 96 V | 0.58 s |
| maximum | the proposal | 0.9843 | 1.0039 | 947 V | ±14.40 | 7.33 | 148 V | 2.73 s from 1.2 kV |
| | the record | 0.9518 | 1.0038 | 1.0 kV | −12.35 / +12.42 | 6.31 | 421 / 357 V | 0.69 s from 1.5 kV |
| hot | the proposal | 0.9760 | 0.9870 | 4.87 kV | ±13.95 | 7.10 | 328 V | 0.90 s from 6.1 kV |
| | the record | 0.8808 | 0.9672 | 3.65 kV | −10.72 / +10.89 | 5.50 | 963 / 826 V | 0.30 s from 5 kV |

- **The seed** is found by `sim/diodes_real.py`'s rule and bisection: the clamped deck, the clamps' leakage in it, and
  trials of 120 cycles, doubled while undecided.
- **With real parts the two pumps' margins meet.** The proposal has fewer sticks (12 against 14) and none doubled, and
  its rings hang on their own stages. At the datasheet's maximum both have 1.004 from 1 kV; at 10 V and hot the
  proposal is ahead.
- **Its rings sag less as the leakage rises:** against ideal diodes, −3.5 % at the maximum and −6.6 % hot; the
  record's sag −10.7 % and −22 %.

## 6. The in-phase stack's side effects
- **The reference link** [OC]:
  - with Q1 = −Q2 the stator vanes carry no net charge, and the link carries 0.02 µA rms, against the record's 165 µA;
  - floating on 100 pF to the shaft, the proposal pumps the same (z 1.0142), and on 10 nF too. The record stops on
    100 pF (1.0001) and needs 10 nF (1.0474), the ledger's finding (§3.1). So the inner bearing need not carry the
    reference.
- **The torque:**
  - the varicaps' pull between the bodies averages 5.0 mN·m (the record 5.1), but swings 191 mN·m p-p at 120 Hz
    against the record's 63: in phase, the two stacks' pulls add;
  - how much of it reaches the gear was not run (`docs/drive-gear-belt.md`).

## Gates
- **The deck against the record:**
  - the 2-D doubler: z 1.3087 against 1.3095;
  - as built, bare: z 1.0576 against 1.0579;
  - the record's supply as built: z 1.0322 against 1.0310 from −10 V. Clamped, the rings sit at −13.860 / +13.862 kV
    against −13.860 / +13.862, and the field at 7.057 kV/cm against 7.057;
  - with typical sticks: z 1.024416 from 1 kV against 1.024416.
- **The energy balance:**
  - every ideal-diode steady run closes the belt against the clamps and the rings' leakage within 0.1 mW of 0.63 W;
  - with real parts the remainder is the sticks' and strings' leakage loss, 4 / 60 / 142 mW, not integrated on its
    own.
- **The step size:** the pick at 8000 steps a cycle gives the same rings (±14.934 kV) and start-up as at 4000.
- **The settled rule:** the gap must hold within 0.1 % over 50 cycles. The 0.3 % over ten cycles of
  `sim/tube_strays.py` passes while a ring still drains through its 100 GΩ at about 0.04 % a cycle; started near
  the steady state, the rings overshoot and then drain for about 270 cycles. So every clamped run starts from 1 kV.

## Caveats
- **[RH] the new nodes' strays:** 24.5 pF each; they set the rings' level (§4).
- **[IR] the as-built set:**
  - the record's stack and Ca / Cb, with C2 run in phase; the in-phase vanes and the new parts are not solved;
  - the redesign's own stack will move κ and the strays.
- **[IR] the 100 pF parts** (C7 / C8, Csa / Csb) take the record's chain value. Their DC: C5 / C6 12.8 kV and Csa /
  Csb 14.9 kV.
- **Not run:**
  - a vane flashover with the ring stages (the record's case lifts ring B to 19 kV, ledger §3.4);
  - the torque's share at the gear;
  - the mounts' creepage with Ca / Cb at 13.2 kV;
  - the redesigned stack.
- **[IR] the cosine C(θ)** between the two solved values, as the record runs it.
