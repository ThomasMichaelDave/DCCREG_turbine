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
