# US 2,945,141 — digest

R. J. Van de Graaff and J. G. Trump, assigned to High Voltage Engineering Corp. Filed 31 Dec 1956, granted 12 Jul 1960.
17 claims. Source: `reference/US2945141.pdf` (3 drawing sheets, 6 text pages).

## The generator unit (Fig. 1)

| element | what it is | note |
|:--|:--|:--|
| 1 | rotor: an iron ring with many teeth 2 on its rim | "as many as 100 poles"; no windings, so it can run fast |
| 3 | six C-shaped stator magnets around the rotor | permanent magnets or field-excited; laminated if PM |
| 4, 5 | the magnets' pole faces, toothed like the rotor | the only air gaps are pole face to rotor |
| 6 | a coil on each magnet's back | AC EMF from the reluctance swing |
| 7 | one rectifier per coil | "in the limit, each turn could have its own rectifier"; acts like a commutator |
| 8 | smoothing capacitor per coil | the structure's own capacitance may suffice |
| 9 | bleeder resistor per coil | brings the stack to zero at stop |

- **The mechanism.** Teeth aligned give a small gap and high flux; teeth facing slots give a large gap and low flux. Rotation
  swings the flux in each C-core, and the coil sees an EMF ∝ N·dΦ/dt. More teeth and more speed give a higher frequency,
  so more volts per turn.
- **Phasing.** The six magnets are spaced so adjacent coils differ by 60° electrical. The rectified outputs add in series
  with low ripple. Units in a stack are phased against each other too.
- **Fig. 1 rating:** 18 kV per coil, 54 + 54 kV per three-coil half, 108 kV per unit.

## The stack (Figs. 2–3)

- Units stack along a **tubular** rotor of alternating iron rotors 1 and insulators 10, with stator magnets on insulating
  blocks 11. Each unit's low-voltage coil connects to the next unit's high-voltage coil (leads 13). The coils are
  staggered so the voltage path is much longer than the column.
- Each unit sits on an **equipotential plane** 14. The rotor may be split into insulated sectors that take the adjacent
  magnet's potential, so no Faraday cages are needed.

## The accelerator (Figs. 4–6)

- The rotor tube *is* the acceleration tube, turned by an induction motor 20 through a coupling 21. It runs in SF₆ at
  about 100 psi, which keeps the glass in compression.
- Example: 28 equipotential assemblies × 6 units = 168 units at 18 kV and 300 W each, which is 3 MV at 50 kW.
- The patent's own remarks:
  - horizontal mounting, supported at both ends, against vibration from the pulsating electromagnetic torque;
  - intermediate bearings "if needed";
  - **an alternative**: a solid PM whose flux is *steered* between two branches of the magnetic circuit, so the magnet
    flux is steady and only the branches see AC. That is a flux-switching PM machine in modern terms.

## Claims in one line each

1. Coils, open magnetised C-cores, a reluctance-varying iron rotor, and rectification.
2. As 1, rectified per coil and summed in series.
3. Alternating units and insulating sections forming a rotor assembly.
4. Outputs phased to reduce ripple.
5. The rotor assembly as an acceleration tube.

Claims 6 and later cover the column in compression, the hollow shaft and the terminal.

## What carries over to our machine

- **The C-core is the same shape as our C-EM.** Our C-EM and utron is a one-tooth, unbiased, pulse-fed version of
  Fig. 1. [OC]
- **Six cores at 60° per unit, two units (A, B) along a tube.** That is our layout, and it is how they phase the
  outputs. [IR]
- **One rectifier per coil** is the key topological idea. Reversed, it becomes one switch per coil: an inverter split
  into small, low-voltage pieces along the HV stack. [IR]
- **The magnetised C-core** (PM bias) is what makes the machine linear in current. Without it a reluctance machine is
  ∝ i² and needs high current, which the pump cannot give. [OC]
