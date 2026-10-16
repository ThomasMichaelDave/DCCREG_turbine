# Stage S1b — the zener clamp on the S1 core: findings

**Source:** `rebuild/s1_tube/s1b_clamp.py` → `s1b_clamp_results.json`, and the representative deck `s1b_clamp.cir`.
The script's TOPOLOGY is the single source of the circuit: the deck is written from it, and the KiCad sheet *S1b
clamp* (`rebuild/kicad/dccreg_rebuild/s1b_clamp.kicad_sch`, parts 3xx) is checked against it node for node.

**The designer's decisions (2026-10-16):**
- "For now we are going to deside the zener voltage clamp. Not using it on the physical bench is just matter of
  disconnecting it."
- The clamp level is 13.13 kV, the record's V_op: the 6 mm gap's 19.70 kV breakdown divided by 1.5.
- One string per node: Z1 on N1 and Z4 on N4, each to REF.

**The circuit:** S1's (the S0 core at the tube's air values, C_k 1.1 pF across N1–N4, 5.1 pF strays to REF), plus
the two strings.

**The parts are the record's classes** [IR]:
- **The HV sticks:** `sim/diodes_real.py` STICK, one per position.
- **Each clamp string:** 66 avalanche parts of the 200 V class in series (1.5KE200A class), from `sim/diodes_real.py`
  CLAMP:
  - 2.5 V / I dynamic impedance and 10 Ω bulk per part;
  - BV 13.2 kV at 1 mA for the string;
  - ±5 % per part and +0.1 %/K (`sim/parts_first_cut.py` Z_TOL, Z_TC);
  - leakage 10 nA typical, 0.5 µA maximum, 5 µA hot [RH] (`sim/diodes-real-findings.md`).

## Headline

**The clamp does its job. It holds both nodes at 13.13 kV, 1.50 × under the gap's breakdown.**
- **Heat:** 0.79 W per string, 12 mW per part, 0.64 mA peak. Together the strings take 1.57 W, close to the ideal
  limit's 1.63 W (`s1_multiplier_tap_results.json` B0) [OC: the pump's surplus ends in what limits it].
- **The pulsed core keeps reversing:** V1 − V4 swings ±7.04 kV.
- **The sticks:** D3 / D4 see 13.09 kV reverse against their 20 kV V_RRM; D1 / D2 see 6.26 kV.
- **The cost is self-start when the parts run hot:**
  - With typical leakage the machine still starts from ≤ 1 V.
  - With hot strings it needs about 0.7 kV, and about 1.3 kV with hot sticks and hot strings.

## Findings

1. **The clamped steady state** (A: real sticks, typical leakage, from a 1 kV seed; settled):

   | quantity | value |
   |:--|:--|
   | N1 / N4 peak | 13.127 / 13.127 kV |
   | margin to the gap's 19.70 kV | × 1.501 |
   | each string: power, per part, peak current | 0.787 W, 11.9 mW, 0.64 mA |
   | both strings together | 1.57 W (the ideal limit: 1.63 W) |
   | the core's V1 − V4 | −7.04 to +7.04 kV |
   | stick reverse peaks: D1 / D2, D3 / D4 | 6.26, 13.09 kV |

   - **Each part:** 12 mW against a 5 W steady rating for the class [IR] is light duty.
   - **The record's comparison:** it gives 1.07 W and 0.95 mA per string (ledger §4) on a different stack. S2's
     values will move these.
2. **The strings' spread** (B):

   | case | N1 / N4 peak | margin | power Z1 / Z4 |
   |:--|:--|:--|:--|
   | both −5 % | 12.46 / 12.46 kV | × 1.581 | 0.71 / 0.71 W |
   | both +5 % | 13.80 / 13.80 kV | × 1.428 | 0.87 / 0.87 W |
   | mismatched: Z1 +5 %, Z4 −5 % | 13.73 / 12.51 kV | × 1.435 | 0.47 / 1.11 W |
   | hot, +25 K (+2.5 %) | 13.46 / 13.46 kV | × 1.463 | 0.83 / 0.83 W |

   - **The margin:** the worst case keeps × 1.43 under the gap.
   - **Each node follows its own string** [OC: one string per node]. A mismatch makes the field across the core
     asymmetric (−6.12 / +7.79 kV), and the lower string takes 70 % of the heat.
   - **Matching the two strings** (a measured BV within a few volts) evens this out. It is a bench step: one part
     moves a string by 1.5 %.
3. **Self-start with the strings in the circuit** (C: the smallest seed on N1 / N4 that grows; 24 cycles decide):

   | sticks / strings leakage | seed needed |
   |:--|:--|
   | typ / typ | ≤ 1 V |
   | typ / max (0.5 µA) | 55–57 V |
   | typ / hot (5 µA) | 669–690 V |
   | max / max | 140–144 V |
   | hot / hot | 1.25–1.29 kV |

   - **Cold, with typical parts,** the clamp does not change the bare core's start (≤ 1 V, `s1-bare-findings.md`).
   - **Restarting hot** needs a seed of about 1.3 kV in the worst case.
   - **This is the record's flagged side effect, now with numbers.** The decision "an HV seed only if it's not
     starting" (2026-10-15) covers it, and the designer's rubbed PVC tube is the seed class for it [RH: its
     voltage is not measured].
   - **Low-leakage parts** (a selected batch) keep the start easy.

## What this means for the build (PROPOSED, the designer decides)

- **The strings:** 66 × 200 V per node, as the record has it. Fit each string with a disconnect, so the bench can run
  without it (the designer's point).
- **Match Z1 and Z4 on the bench:** measure each string's BV at 1 mA and trim by whole parts. That keeps the core's
  field symmetric and shares the heat.
- **Select the parts for low leakage:** the self-start threshold follows the strings' leakage, above all when hot.
- **The values move with S2:** C1 / C2 and the strays come from the field solve. Re-run S1b on them; the clamp level
  stays 13.13 kV by decision.

## Next

- **S2:** the 3-D models (the vane stacks in antiphase, the core electrodes at the 2 mm wall, Ca / Cb). Then S1b
  re-runs on S2's values.
