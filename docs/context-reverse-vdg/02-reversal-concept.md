# The reversal, mapped onto the tube machine

## 1. Running the patent backwards [OC]

An electromagnetic machine is reciprocal:
- **Patent:** shaft torque × speed → coil EMF × current → rectified, summed HV DC.
- **Reversed:** HV DC → one switch per coil, timed to rotor position → coil current *against* the back-EMF →
  torque between the toothed rotor and the magnetised stator cores.

Power per coil is e·i, with e = N·dψ/dt set by the PM flux and the tooth swing. The string draws V_link·I from the
link, and only I²R is lost in the copper.

What this cures [OC, `sim/tube-ledger-findings.md`]:
- Today the C-EMs get µs pulses straight from the spark gaps, and the work is ½·i²·dL/dθ over almost zero travel:
  5.8e-7 N·m.
- A back-EMF machine fed from a smoothed link converts continuously, at the efficiency of an ordinary PM motor.
- The trade is that the motor must *match* the link: the series back-EMF at speed has to be about 20 kV.

## 2. Element map

| patent | reversed role | tube machine part | change from the current build |
|:--|:--|:--|:--|
| toothed rotor 1 | reaction member, passive iron | **toothed ring** at r 130 on the utron hub, one per side | replaces the 3 utrons per side; laminated or SMC; ~60 teeth (pitch 13.6 mm) |
| C-magnets 3, toothed faces 4/5 | torque producers | the **6 C-EM cores per side**, same envelope (r_u 130) | jaw faces toothed (2 teeth per 30 mm jaw); jaw gap 7 → ~1 mm running clearance |
| PM / field excitation | flux bias, makes torque ∝ i | PM in the C-core back, or the patent's *steered-flux* variant | new: magnet pieces in the spine (flux-switching PM) |
| coil 6 | motor winding | the C-EM bobbin (48 × 13 mm window) | rewound: ~6200 turns of 0.20 mm wire (`03-budget.md`) |
| rectifier 7 | **switch 7′ per coil** (commutation) | on each C-EM, at that coil's potential | new: ~1.7 kV device, gate timed by rotor position |
| condenser 8 | **DC link** | a reservoir across the motor string | new: HV capacitor fed from the pump through its load diodes |
| bleeder 9 | safe discharge | across each coil / switch | keep |
| equipotential planes 14 | voltage grading | each C-EM at its own string potential | the stator cage carries the grading |
| series stack (13) | one series string | 12 coils (A 6 + B 6) | A and B coils in one string, or one string per side (fork F3) |
| rotor = acceleration tube | — | the tube shaft / sleeve | unchanged; no beam |
| induction motor 20 | — | **the belt** on the rotor | unchanged |

The phase plan follows the patent:
- 60 teeth make 60° mechanical exactly 10 teeth. Offsetting each C-EM by 1/6 of a tooth pitch (1°) gives six phases
  60° electrical apart, so the torque ripple is small. [IR]
- B is offset half a tooth from A. [IR]

## 3. Counter-rotation [OC]

- The torque acts between the toothed rotor ring (on the belt-driven rotor) and the C-EMs (on the stator). The stator
  is pushed opposite to the rotor; the belt sees the reaction as extra load.
- The relative speed is what makes back-EMF. Because the belt already spins the rotor, the relative speed is 300 rpm at
  stator standstill, so the motor has its full back-EMF from the first moment and needs no start-up mode.
- As the stator spins up, the relative speed rises, and so do the pump power and the back-EMF together.

## 4. Where the DC link comes from [IR, open]

- The v4 pump has no DC output today. It is a growing eigen-state that a limiter holds at the operating peak.
- A link means a load tap, for example rectifying diodes from the transfer nodes into a reservoir, and that tap must be
  in the engine before any motor number is real (gate G-LOAD).
- The link voltage is regulated by the motor switches. They draw only the surplus (voltage-priority control):
  - if the link sags, the switches back off;
  - stall current at 20 kV into the 12 × 0.6 kΩ string is about 2.8 A, which would collapse the pump instantly without that control.

## 5. Isolation [IR]

- The coils sit on the stator, which is already the HV side, so each C-EM floats at its place in the string.
- Each switch needs gate power and position timing at that potential:
  - optical, by fibre;
  - or the clocking decks' tips as position sensors;
  - or a small pick-up coil on the same core.
- Bleeders grade the string at rest.
