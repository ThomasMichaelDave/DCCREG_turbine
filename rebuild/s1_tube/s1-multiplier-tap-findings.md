# Stage 1 — a two-stage multiplier on the doubler, tapped into a buffer: findings

**Source:** `rebuild/s1_tube/s1_multiplier_tap.py` → `s1_multiplier_tap_results.json`, with S1's air values and
ideal diodes. Voltages are given in units of the buffer voltage V_buf, and as kilovolts when the varicap peak is set
to the record's 13.13 kV, a reference scale only [RH].

**The designer's question (2026-10-14):** "the maximum voltage difference between two nodes of the multiplier
considering we add a two stage on top of the doubler. Where do we tap that difference? The idea is not to dissipate
anything, ideally I want all energy cycling back and forth, with limited losses. Can we do that with a buffer
somewhere for instance?"

## Headline

**Yes, in the ideal model.** A buffer in place of a dissipating limit stores 99.6–99.96 % of the mechanical input,
and the energy balance closes to 10⁻⁵ [OC: ideal diodes and linear capacitors; the transfers are lossless].
- **This is the locked principle's allowed route:** recovery at a downstream sink, not on the pump's own transfers
  (`CONVENTIONS.md`).
- **The store must keep emptying.**
  - With z > 1 and no outlet, energy piles up without bound. A full buffer is just a limit again.
  - "Cycling back and forth" therefore means a loop: store → converter → the drive. The drive's net power then falls
    to the losses: the diodes' drop and leakage, corona, the converter, the bearings and windage.
  - The loop cannot run itself [OC: conservation; every loss is positive].
- **Where to tap:**
  - **Most energy per volt of stress:** straight at the varicap nodes, case B0.
  - **A floating bipolar output:** across a positive ladder on node 1 and a negative ladder on node 4, case BB.
    - The tap reads 0.92 of the varicap peak.
    - The largest voltage between any two nodes is 1.58 × the tap, between node 1 and the negative ladder.
  - **Two positive ladders,** case BP, step the voltage *down* here. Do not use that arrangement.

## The cases

The core is the frozen S0 doubler in every case. The ladders have 2 stages (Villard / Cockcroft-Walton), with
capacitors equal to Ca. The buffer is held at V_buf by an exact rescale each cycle.

| | B0: core → buffer | BP: core + CW2 (+) on 1 and on 4 → buffer to REF | BB: core + CW2 (+) on 1, CW2 (−) on 4 → buffer across the tops |
|:--|:--|:--|:--|
| the tap (V_buf) ÷ varicap peak | 1.00 | 0.41 | 0.92 |
| largest voltage between any two nodes | 1.00 V_buf (node 4 – REF) | 2.41 V_buf (node 4 – REF) | **1.58 V_buf (node 1 – the negative ladder's 2nd oscillating node)** |
| largest diode reverse ÷ varicap peak | 1.00 (D3 / D4 at the limit) | 1.00 | 1.00 (D3 / D4); the ladders' own ≤ 0.31 |
| largest fixed capacitor ÷ varicap peak | 0.54 | 0.70 | 1.00 (the negative ladder's input capacitor, 4 – o1); the positive one's 0.70 |
| stored ÷ mechanical input | 0.9996 | 0.9957 | 0.9988 |
| the varicaps' energy swing ÷ net input, a cycle | 0.49 | 0.48 | 0.52 |
| at a 13.13 kV varicap peak: tap / largest pair / power stored | 13.13 / 13.13 kV / 1.63 W | 5.44 / 13.13 kV / 0.83 W | **12.13 / 19.20 kV / 0.93 W** |

1. **The maximum difference with a two-stage multiplier** is case BB [OC: this run]:
   - 1.58 × the tap, between the core's node 1 (+1.08 V_buf) and the negative ladder (−0.50 V_buf);
   - 19.2 kV at a 13.13 kV varicap peak.
   - That pair's insulation, not any one part, sets the clearance.
2. **Where to tap it:**
   - Across the two ladder tops: + about 0.45 V_buf, − about 0.55 V_buf around REF, 12.1 kV at that scale.
   - The tap floats and is bipolar, which is the form a ± electrode pair (the rings) would want.
   - The ladder parts each see ≤ 0.33 of the varicap peak. Two parts still see the full peak: D3 / D4 in the core,
     and the negative ladder's input capacitor.
3. **The costs of the ladders:**
   - At the same varicap peak, BB stores 0.57 of B0's power (0.93 W against 1.63 W). The ladders carry charge back and
     forth, and the core runs at a lower swing.
   - BP is worse: the core rises to 2.41 × the tap. A positive ladder driven from a node with a large DC level and a
     swing of about half the peak adds less than the DC it starts from.
4. **"Energy cycling back and forth":**
   - Inside the pump, the varicaps' stored energy swings by only about half the net input each cycle. Most of the
     shaft's work is net transfer into the store, not reactive energy.
   - The cycling the designer describes therefore has to be the outer loop, store → drive.

## What a real build has to add (PROPOSED, the designer decides)

- **The store:**
  - A capacitor bank at the tap, emptied by a converter into the drive's supply.
  - This is de Queiroz's §II.B steady-state operation: a DC/DC converter discharges the generator when it reaches
    v_lim, with E = ½ C_eq v_lim² a discharge (eq. 4) [OC: the paper].
  - The converter's trigger is then the limit, with no clamp needed. **The limit and the recovery are the same
    part.**
- **The losses to price:**
  - the sticks' forward drop on every transfer and their leakage (S1's real-diode record);
  - the converter's efficiency at HV;
  - corona.
  These decide how much of the 0.93–1.63 W comes back.

## Next

- **The same cases with real sticks (ngspice):** the stored share and the losses, for B0 and BB.
- **A converter model** (de Queiroz Fig. 2 class) as the store's outlet, to check the trigger-as-limit cycle.
