# Stage 1 — moving the voltage stress off the discrete parts: options

**Source:** `rebuild/s1_tube/s1_stress_options.py` → `s1_stress_options_results.json`, using S1's air values. The
general solver (ideal diodes; the LCP as non-negative least squares) reproduces the S0 / S1 core exactly: T2 with
N = 1 gives z 1.18702.

**The designer's question (2026-10-14):** "how can we move the voltage stress away from the discrete components?
Minimizing by adding a multiplier stack is also ok, check what options there are. We have dealt with spark gaps for
this reason but that adds serious complexity."

**The metric:** the largest voltage any discrete part sees over a cycle (a diode's reverse voltage, a fixed
capacitor's voltage), divided by the varicap nodes' peak. Every option here keeps the system's highest voltage on the
varicaps, except T3 with M = 4 [OC: ratios of the growing mode].

## Headline

**Where the stress sits is set by the topology, and the core's own cross diodes D3 / D4 always see ≈ 0.96 of the
varicap voltage.** Three levers reduce what a single part sees:
- **Lower the voltage itself by making the gaps finer** (lever L1). This is the only lever that cuts the stress
  everywhere, the vanes included, and it adds no parts.
- **Divide the diodes' share with a two-phase Dickson chain** (T2). It keeps the HV on the vanes, but it costs gain and
  moves stress onto the coupling capacitors.
- **Divide it physically with series sticks,** graded along the vane column (T1). This is the simplest.

A Cockcroft-Walton ladder on the core (T3) does **not** relieve D3 / D4: it adds HV beyond the core. Spark gaps (T4)
are not run.

## The options

| option | z per cycle | diodes / fixed caps | max diode ÷ varicap | max fixed cap ÷ varicap |
|:--|:--|:--|:--|:--|
| T0 = T2 N 1: the S0 core | 1.18702 | 4 / 2 | 0.956 (D3, D4) | 0.528 |
| T2 Dickson N 2 (Cc = Ca) | 1.07961 | 8 / 6 | 0.502 | 0.716 |
| T2 Dickson N 3 | 1.04180 | 12 / 10 | 0.358 | 0.788 |
| T2 Dickson N 4 | 1.02582 | 16 / 14 | 0.292 | 0.829 |
| T2 N 2, Cc 0.5 / 2 / 4 C_max | 1.1107 / 1.0548 / 1.0321 | 8 / 6 | 0.541 / 0.482 / 0.468 | 0.736 / 0.703 / 0.695 |
| T2 N 3, Cc 0.5 / 2 / 4 C_max | 1.0658 / 1.0267 / 1.0148 | 12 / 10 | 0.383 / 0.344 / 0.331 | 0.787 / 0.787 / 0.785 |
| T3 core + CW M 1 / 2 / 4 | 1.0860 / 1.0641 / 1.0563 (M 4 not converged) | 8 / 6 … 20 / 18 | 0.985 / 0.993 / 0.994 | 0.53 |

1. **T1, series sticks** [OC]:
   - n sticks per position divide every diode ratio by n. Nothing else changes, z included.
   - Physically, the string can run along the vane column so the column's own field grades it, which moves the
     stress into the geometry.
   - It costs parts and leakage: the self-start seed scales with the string's leakage (`s1-bare-findings.md`
     finding 4).
2. **T2, the two-phase Dickson** [IR: this script's construction, with Fig. 1 as its N = 1 member]:
   - Each varicap node is fed from REF through 2N diodes. Their intermediate nodes couple alternately to the two
     varicaps.
   - **The diodes' share falls roughly as 1 / N:** 0.956 → 0.50 → 0.36 → 0.29.
   - **The costs:**
     - z falls (1.187 → 1.080 → 1.042), because the chain's capacitance loads the varicaps;
     - the coupling capacitors' share rises (0.53 → 0.72 → 0.83). The stress moves from the diodes onto the
       capacitors.
   - **The capacitors need not be bought parts.** Ca / Cb are already plate stacks on the rotor
     ("six full-annulus aluminium plates", ledger §3), and the coupling capacitors can be the same: geometry sized for
     the field like the vanes. Then the stress does move off discrete parts, onto air-gap structures [IR].
   - Larger coupling capacitors (Cc) lower the diode share a little but cost z; smaller ones help z.
3. **T3, core + Cockcroft-Walton:**
   - The ladder's diodes see ≈ 0.5 of the varicap voltage, but D3 / D4 still see 0.99. The ladder does not divide
     the core's stress; it builds voltage beyond the core (the earlier design's rings supply).
   - It helps only if the HV is wanted *off* the vanes, on a ladder top (e.g. the rings). The core can then run at a
     fraction of it, and every part, D3 / D4 included, sees that fraction.
   - Its gain and output depend on the limited steady state, which this growth-mode metric does not show. It is to
     be run with a limiter if chosen.
4. **T4, spark gaps:** not run, given the designer's complexity objection. They are the disc machine's route
   (`docs/efficiency-resolution.md`).

## L1: lower the voltage, not just divide it

[OC: parallel plates; the rims and the plate thickness are neglected first]
- Take a stack of fixed length and run it at the same field E.
- The gap g sets the voltage: V = E g.
- The capacitance swing scales as 1 / g² (C ∝ 1/g per gap, and the number of gaps ∝ 1/g).
- So the energy per cycle, ∝ C V², does not change.
- **At the same pumped power, a finer gap lowers every part's voltage in proportion:** 6 mm → 3 mm halves the
  stress on D3 / D4, Ca / Cb and the vanes.
- The air also holds a higher field at smaller gaps, which adds margin.

**The costs** [IR]:
- **Plate thickness:** the stack's active fraction is g / (g + t). With the 3 mm vanes, 6 → 3 mm takes the energy at
  fixed length to 0.75. Thinner vanes or a longer stack buy it back.
- **Tolerance:** runout, flatness and gap control get tighter, a concern for the mechanics in S2 / S3.
- **The rims:** their share of the strays grows as the gap shrinks, which lowers κ. That needs the S2 field solve.

## What this means for the build (PROPOSED, the designer decides)

- **To keep the HV on the vanes and off the diodes,** combine L1 (choose the gap for the voltage the parts should
  see) with T1 (graded series sticks). T2 is the topology option if the parts count must fall further and the lower
  z is acceptable.
- **The limit is still needed** in every option (`s1-bare-findings.md`). Whatever limits the voltage takes the
  surplus as heat. With L1 the surplus is the same power at a lower voltage.

## Next

- **T2 and T3 under a limiter:** the steady state, the surplus (power) and each part's stress at the limit, run with
  the S1 records (ideal, ngspice, real sticks).
- **L1 in S2:** the vane stack re-solved in 3-D at two or three gaps, to find κ, the strays and the power at a fixed
  length.
