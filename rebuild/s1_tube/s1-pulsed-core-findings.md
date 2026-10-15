# Stage 1 — a pulsed core field from the S0 doubler: findings

**Source:** `rebuild/s1_tube/s1_pulsed_core.py` → `s1_pulsed_core_results.json`. It uses the frozen S0 core with S1's
air values and ideal diodes, and S1's capacitance profile: linear in the rotor angle each half cycle [IR]. Every
number below comes from the results file. The kilovolt figures scale the varicap peak to the record's 13.13 kV, as a
reference only [RH].

**The designer's question (2026-10-15):** "The core is meant to be pulsed yes, it's meant to go back and forth between
the top and bottom section. Potentially we need to account for it in the schematic. Lets say the centre is the neutral
and top and bottom switch polarities when going through their phases. Then how do we account for it in the doubler.
Is a mere phase shift of the top varicap against the bottom varicap enough?"

## Headline

**S0 already pulses the core, and no extra phase shift is needed.** The S0 doubler runs its two varicaps a half
cycle apart (180°, the decided Fig. 1). In its steady periodic state V1(t) = V4(t + T/2) [OC: the map's half-cycle
symmetry]. As a result:
- **The difference V1 − V4 is a pure alternating wave.** It is what drives a field from a top electrode to a bottom
  electrode through a symmetric centre. Its mean is zero (≤ 3 × 10⁻⁶ of the peak), its second harmonic is ≤ 5 × 10⁻⁶,
  and it is nearly sinusoidal (third harmonic 0.06).
- **With the centre as the neutral, top and bottom swap polarity every half cycle.** Each sits at ±(V1 − V4)/2. This
  is the designer's picture, and the schematic already contains it.
- **What does not alternate is the common mode,** (V1 + V4)/2: 0.57–0.74 of the peak, always positive (S0's DECIDED
  polarity). It sets no field at a symmetric centre [IR: symmetric geometry]. It does set where the varicaps' stator
  side (REF) sits relative to the neutral, −7.5 to −9.7 kV at the 13.13 kV scale.

**The 180° phase is the right one, and the best.** A smaller shift only costs gain:

| phase between C1 and C2 | 0° | 30° | 60° | 90° | 120° | 150° | 165° | 180° (S0) |
|:--|:--|:--|:--|:--|:--|:--|:--|:--|
| z per cycle | 1.00000 | 1.00424 | 1.07469 | 1.12249 | 1.15546 | 1.16875 | 1.17500 | **1.18702** |

In phase (0°), the doubler does not grow at all. This settles the noted conflict: the §3.9 redesign drew C1 / C2 in
phase, and that drawing cannot pump in this topology [OC: this run].

## Findings

1. **The pulsed difference** (÷ the varicap nodes' peak):

   | state | V1 − V4 | fundamental | 3rd harmonic | common mode | varicap minimum |
   |:--|:--|:--|:--|:--|:--|
   | growing (no limit) | ±0.528 | 0.474 | 0.056 | 0.563–0.736 | 0.440 |
   | limited (the B0 buffer) | ±0.540 | 0.498 | 0.063 | 0.574–0.742 | 0.460 |

   - The varicap nodes never fall below 0.44–0.46 of their peak. Each node swings by about half its peak, on top of a
     DC of about two thirds of it. Only the *difference* reverses.
   - **At the 13.13 kV scale (limited):**
     - the difference is ±7.09 kV, 14.18 kV peak to peak;
     - at the record's k_null 0.2546 (kV/cm)/kV (`sim/diodes_real_results.json`), the field at the null is ±1.80 kV/cm
       at 120 Hz, 3.61 kV/cm peak to peak [IR: the record's ring geometry and 1.5 mm wall, with the rings tied
       straight to nodes 1 and 4].
   - That is about a quarter of the record's 7.62 kV/cm DC field. The record got its field from ± ladders standing
     at ±15 kV, and those give DC.
2. **The core in the schematic is a load across nodes 1 and 4.** The schematic records it as a capacitor C_k from
   node 1 to node 4 (the electrode pair across the core), plus each electrode's stray to REF:

   | C_k (1–4) / to REF each | z | difference amplitude (limited) | energy in C_k at peak, 13.13 kV scale |
   |:--|:--|:--|:--|
   | none | 1.18702 | 0.540 | — |
   | 1.1 / 5.1 pF (the record's ring strays) | 1.17590 | 0.538 | 0.027 mJ |
   | 5 / 5.1 pF | 1.16756 | 0.537 | 0.124 mJ |
   | 20 / 5.1 pF | 1.13646 | 0.530 | 0.484 mJ |
   | 50 / 5.1 pF | 1.07825 | 0.517 | 1.15 mJ |
   | 128.4 pF (= C_min) / 5.1 pF | 1.00000 | 0.526 | 3.06 mJ |

   - The load costs gain, not swing: the difference stays at 0.52–0.54 of the peak.
   - A C_k as large as C_min stops the pump. It ties the two varicaps together, so the varicaps no longer carry the
     swing. The record's rings (1.1 pF) cost 0.011 of z.
   - **The energy in C_k is reactive.** It peaks twice a cycle, with the field one way and then the other, and returns
     through zero in between. In the ideal model it flows back into the varicaps and is not lost [OC: linear capacitor,
     no diode in its path]. Only the core's dielectric loss (the glass, the gel) and its leakage turn it into heat [RH:
     not modelled].
3. **The neutral (D):**
   - Ground the centre (a symmetric midpoint of the 1–4 pair), and the top and bottom read ±3.54 kV, swapping each
     half cycle.
   - REF then sits at −7.53 to −9.74 kV against that neutral, a DC offset with a ripple at 2 × 120 Hz.
   - Ground REF instead, as S0 does, and the centre floats at the common mode.
   - It is the same circuit either way. The choice is only where the insulation's zero sits: the stator vanes, or the
     core's midplane.

## What this means for the build (PROPOSED, the designer decides)

- **Keep 180°. No phase-shift part is needed.** Tie the top core electrode to node 1 (C1's swinging side) and the
  bottom one to node 4. The field across the core then reverses every half cycle at the shaft's 120 Hz.
- **Add C_k and the electrodes' strays to the schematic** as S1's first addition (README's rule of addition): a
  capacitor 1–4 and one to REF on each. Its value comes from the S2 field solve of the core electrodes.
- **The amplitude choice:**
  - The direct tie gives ±0.54 of the varicap peak across the core.
  - More would need the ladders to swing rather than stand DC. In S1's multiplier study the ± ladders' tops carry a
    small ripple, not a reversal. So a larger *alternating* field is a new topology question, not a ladder size.
  - The phase-2 commutator is the other route to fast, larger reversals.
- **Where the zero sits:** the stator (REF) or the core's midplane. This decides the insulation map; see D.

## Next

- **The same runs with real sticks (ngspice):** the reversal waveform, and the core's reactive energy against the
  sticks' losses.
- **S2:** the core electrodes' C_k and strays from the field solve. The k_null of the new geometry, with the wall the
  designer confirms (1.5 or 2 mm).
