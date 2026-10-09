# Diode stack vs spark gaps on the tube: the de Queiroz core wins

Source: `sim/diode_stack_compare.py` → `sim/diode_stack_compare_results.json`. Exact engine, tube ladder
(C1 / C2 1114 / 71 pF, Ca = Cb 1225 pF, Cpar 20 pF), 300 rpm. Each run is scaled so that its highest node peaks at
20 kV, which is the breakdown-limited node.

The original electronic Bennet doubler (A. C. M. de Queiroz, *Analysis of Electronic Electrostatic Generators*, IEEE
2018) is in the repo as:
- the frozen `solveDoubler4` (`index.html`);
- its mirror `reference/doubler_core.py`;
- the engine's `core_net` (`topology="core"`).

It has 4 nodes and 4 ideal diodes: D1 2 → ref, D2 3 → ref, D3 1 → 3, D4 4 → 2.

| circuit | z per cycle | highest node | belt | surplus | η |
|:--|:--|:--|:--|:--|:--|
| record schematic, spark gaps (tube default) | 1.567 | node 1 | 2.47 W | 1.30 W | 0.53 |
| record schematic, **every gap a diode** | 2.406 | **island 8 (8× node 1)** | 0.18 W | 0.17 W | 0.96 |
| de Queiroz core, two-state stepped caps (`solveDoubler4`) | 1.712 | node 4 | 0.92 W | 0.48 W | 0.52 |
| **de Queiroz core, smooth caps, diodes** | 1.515 | node 1 | 3.01 W | **3.01 W** | **1.00** |

For comparison, the Goldie two-section machine with diodes (`goldie-tube-findings.md`) gives 3.39 W at η 1.00.

## Reading

1. **The bare de Queiroz diode core, with real (smoothly varying) capacitors, is the best Bennet option.** It gives
   2.3× the spark-gap tube's surplus at η ≈ 1. Ideal diodes start conducting at zero voltage across them, so charge
   moves without a spark or a ring.
2. **The 0.39–0.52 "direct doubler η" is a property of the two-state schedule, not of diodes.** `solveDoubler4`
   switches each capacitance instantly between min and max. Every instant jump with a diode conducting redistributes
   charge at a voltage step, which is a loss. With continuous capacitance the same circuit is lossless. **This
   qualifies `docs/efficiency-resolution.md`:** its η 0.386 rests on the stepped model. That needs a re-check before it
   is quoted for a physical machine [IR].
3. **Do not simply swap diodes into the record schematic.** With diodes the Cx / Lx islands stop being timed dumps and
   become voltage multipliers. Island node 8 rides at 8× node 1, so under a 20 kV cap the main nodes sit near 2.5 kV
   and the output collapses. The islands only make sense with timed spark gaps. A diode stack means **the bare core,
   without the islands**.
4. **Practical layout** [IR]:
   - The rotor halves are the reference (R-A), and R-B is joined to it by the tank coil, so the rotor can be grounded
     through a shaft brush.
   - All four diodes then sit on the stator: D1 / D2 to ground, D3 / D4 between stator nodes.
   - There are no rotor-to-stator gaps and no clocking decks.
   - Ratings: the nodes reach 20 kV, and D3 / D4 see up to about the sum of two node swings, so use stacks rated
     ≥ 40 kV. HV rectifier sticks at 30–100 kV / few mA are stock. Their ~1 pF and µA leakage are small next to the
     1 nF-class capacitors.
     - **Corrected 2026-10-09** (`sim/diodes-real-findings.md` §4.3): not next to the record's 100 pF chains. There
       each stick's junction capacitance (0.2–0.4 pF) takes 0.57 kV off the rings' 29.9 kV, and 1 pF of body
       capacitance or 2 µA of leakage each take about 2.6 kV.

## Diode parts for the stack (default tube: 3 mm vacuum, diode core, highest node 20 kV)

Engine, per diode position:

| position | function | peak reverse | design rating (×2) |
|:--|:--|:--|:--|
| D1 | node 2 → rotor rail | 9.1 kV | ≥ 20 kV |
| D2 | node 3 → rotor rail | 8.6 kV | ≥ 20 kV |
| D3 | node 1 → node 3 | 17.9 kV | ≥ 40 kV |
| D4 | node 4 → node 2 | 15.8 kV | ≥ 40 kV |

Currents are sub-mA (about 0.3 mA average, about 1 mA peak at 300 rpm). The switching rate is 30 Hz, so recovery time is
irrelevant.

| choice | D1 / D2 | D3 / D4 | notes |
|:--|:--|:--|:--|
| **2CL77** (20 kV, 5 mA, I_R 2 µA at 25 °C / 5 µA at 100 °C, avalanche) | 1 | 2 in series | stock at LCSC; the recommended stick |
| **C67X040D20TTS** (CSDC, 40 kV, 20 mA) | — | 1 | one stick per position |
| CL01-12 (microwave, 12 kV, 350 mA, I_R 5 µA) | 2 in series | 3–4 in series | cheap and robust; higher leakage and V_F |

- **Leakage loss.** I_R × V_R ≈ 2 µA × 18 kV ≈ 36 mW per D3 / D4 position at 25 °C, about 0.1 W in total (~3 % of the 3 W).
  It rises ~2.5× hot, so keep the stacks cool and in air, oil or potting at 1 atm, outside the vacuum. Epoxy bodies
  outgas and flash over along their surface in vacuum.
- **Series sharing.** Use avalanche-rated parts from one lot. Do **not** grade with resistors: 200 MΩ across 20 kV
  would burn 2 W, most of the surplus. Avoid large grading capacitors too, since they add stray capacitance across the
  pump nodes.
- **Surge.** A vane flashover dumps the stored charge (~0.24 J at 20 kV) through the stack. A 10–47 kΩ HV resistor per
  position limits the current, for about 10–50 mW of I²R at 1 mA peak.
