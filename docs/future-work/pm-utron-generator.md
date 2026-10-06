# Parked: permanent-magnet rotor cores — the C-EMs as the patent's DC generator

**Idea.** Make the utrons (rotor reluctance cores) permanent magnets. Each utron passing a C-EM then swings the flux
through its coil, which is US 2,945,141 run *forwards*. Each coil gets an AC EMF; rectify it per coil and stack the
outputs in series, and the result is an extra DC source.

## First-pass budget [RH]

Inputs:
- NdFeB utron, about 0.6 T across the 2 × 7 mm jaws, a 900 mm² jaw face, about 50 % of the flux captured by the C-core;
- 3 utrons per side, so each C-EM sees 3 passes per revolution;
- the existing bobbin, matched load.

| rpm rel | f per coil | winding | EMF per coil (pk) | 12-coil string (rectified, open) | power (matched) |
|:--|:--|:--|:--|:--|:--|
| 300 | 15 Hz | 1846 t / 44 Ω | 23 V | 282 V | ~19 W |
| 300 | 15 Hz | 6207 t / 0.6 kΩ | 79 V | 948 V | ~16 W |
| 600 | 30 Hz | 1846 t | 47 V | 564 V | ~75 W |
| 1200 | 60 Hz | 1846 t | 94 V | 1.1 kV | ~300 W |

- **Power.** Even untoothed, this is about 7× the electrostatic pump's whole belt draw (2.5 W) at 300 rpm, and it grows
  ∝ rpm² until core loss, saturation or the winding's current limit. It is far more power than the variable capacitors
  give: electromagnetic conversion is the dense route.
- **Voltage.** It is low: hundreds of V at 15 Hz. Reaching 20 kV takes the patent's recipe:
  - a toothed rotor and toothed jaws, raising f about 20×;
  - fine-wire coils;
  - per-coil rectifiers in series.

  With 60 teeth and 0.20 mm wire, the earlier budget gives about 21 kV per 12-coil string at 300 rpm
  (`sim/reverse_vdg_budget.py`).

## The catch: where the reaction torque goes [OC]

The power is taken from the rotor–stator relative motion. If the generator coils sit on the **counter-rotating
stator**, their reaction torque drags the stator along with the rotor, exactly like the pump's own reaction
(`sim/spinup-findings.md`).
- **No generator plus motor pair working between the same two bodies can counter-rotate the stator.** The motor's
  torque is at most η × what the generator took.
- **The way out is to react against the frame.**
  - Put the generator coils on a **frame-fixed ring**: rotor (PM utrons) against the frame, so the belt pays and the frame
    takes the reaction.
  - Put the motor **between the stator and the frame/shell**: the outer guides, which were already future design.
  - That is an electrical reversing gear: belt → PM generator (rotor vs frame) → DC → motor (stator vs shell).
  - Chain efficiency about 0.6–0.8, against about 0.95 for a mechanical gear. Its merit is no mechanical link to the
    stator.

## Side effects to check

- **The pump.** PM utrons near the HV structure: the C-EM cores are bonded to nodes 2 / 3, and the utrons float.
  Magnetised utrons add no charge coupling, but they make eddy-current drag in all nearby conductors: the Al vanes and
  the tips.
- **Cogging.** PM utron to C-EM attraction gives cogging torque at 3 × 6 per revolution, and that loads the shaft
  bearings.
- **Magnets.** Demagnetisation margin under the coil currents, and a temperature limit (NdFeB about 80–120 °C).

## First gates

1. **G-PM-FLUX:** magnetostatic solve (the `tube_magnetic.py` analogy plus a PM source) of the aligned and unaligned flux
   through one C-EM.
2. **G-PM-EMF:** EMF and power against rpm, with core loss.
3. **G-FRAME:** a frame-fixed coil ring at r_u 130 that clears the stator cage, plus the stator-to-shell motor envelope.

## Variant (2026-10-06): belt on the stator, PM utrons + C-EMs as a BLDC motor that drives the rotor backwards

Setup:
- the older (record) schematic, with the C-EMs entirely out of the Bennet circuit;
- the belt drives the stator;
- the C-EMs, in two groups A / B, are energised from an outside supply and commutated by rotor position;
- the PM utrons make the pair a brushless PM motor that turns the rotor the other way.

Record schematic, tube at 20 kV (`RT.build_net(cfg)`):

| strays | z | pump work per cycle | ledger closure | pump reaction torque |
|:--|:--|:--|:--|:--|
| fixed | 1.567 | 82 mJ | 5e-14 J | 78.5 mN·m |
| scaled | 1.313 | 83 mJ | 3e-15 J | 79 mN·m |

- **The pump starts as soon as the stator turns.** Only relative motion counts. Left free, the rotor is dragged along with
  the stator, by the pump reaction (78 mN·m), the bearings (15 mN·m), vane shear and PM cogging, and that kills the
  relative speed. The motor's job is to hold the rotor back or reverse it.
- **Shorted, passive C-EM coils make it worse.** By Lenz, the induced currents couple the rotor to the stator. The coils
  must be driven.
- **Torque the motor must supply.** About 100 mN·m at 20 kV (45 mN·m at the air cap). At a symmetric split (each body at
  150 rpm, 300 relative) that is about 1.6 W from the motor and 1.6 W from the belt. The total, T·ω_rel, equals the pump
  work plus drag, the same as driving one body.
- **The motor itself is easy.** The existing winding (1846 turns) has about 23 V peak back-EMF per coil at 300 rpm
  relative, so the job takes milliamps. It is an ordinary 2-phase BLDC; a 2-phase machine has dead points, so it needs
  an asymmetric gap or start-up logic.
- **Energy must come from outside the rotor–stator pair:** low-voltage slip rings to the stator, or a small alternator
  between the stator and the frame. A motor powered by the pump cannot do it (`sim/spinup-findings.md`).
- **What counter-rotation buys:**
  - each body at half speed;
  - windage per body ×1/8 (total ×1/4 at the same relative speed);
  - centrifugal stress ×1/4;
  - same relative-speed bearing load.
- **Isolation.** The C-EMs sat bonded to nodes 2 / 3 in v4. Out of the circuit, they and their low-voltage supply must be
  insulated from the stator's HV nodes, or placed in a frame-referenced end section.
