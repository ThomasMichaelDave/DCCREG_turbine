# Switchless C-EMs on the diode core — findings

**Question.** The schematic `docs/schematic-diode-core-dcbus.svg` fed the C-EMs from the DC bus through a switched drive:
per-coil SiC switches, a rotor-position sensor and a controller. That violates "diodes only". Can the C-EMs be driven
with **no switches at all**, and what do they deliver? Two placements were modelled side by side (designer's choice):

- **(a) LEG:** a 6-coil string in series with each varicap (A with C1, B with C2).
- **(b) BUS:** a 6-coil string in series with D5 / D6 into C_bus (the dcbus schematic with the switched drive removed).

**Tool.** `sim/switchless_cem.py` → `sim/switchless_cem_results.json`. Circuit-level ngspice, tube defaults at 300 rpm:
- **Core:** C 71.1 / 1113 pF cosine, Ca = Cb 1225 pF, Cpar 20 pF; near-ideal core diodes. Bus diodes D5/D6 use a
  normal-knee model.
- **Coils:** PM utrons with 0.27 mWb swing [RH, G-SWING open]. Turns N = k × 1846 in the same window, so L ∝ k² and
  R ∝ k².
- **Operating point:** a passive avalanche clamp holds 20 kV at nodes 1 and 4. It is a diode string, not a switch.
- **Why not the engine:** it is scale-free and cannot hold a fixed-amplitude back-EMF [IR].

Every power term is integrated by ngspice itself (B source into 1 F). Belt = Σ −½V²dC/dt. The ledger closes to
≤ 1e-4 W on every row.

## Cross-check
- **Bare core:** z 1.512 per cycle in ngspice against 1.515 in the engine (`diode_machine`).
- **With the 20 kV clamp:** belt 4.54 W = clamp 4.54 W. The clamped waveform takes more than the engine's 3.0 W
  eigen-cycle figure, because the flattened top holds the node at 20 kV longer.

## Results

### (a) LEG: it works without switches, but only with PM utrons and a heavy rewind

Each row is the best of 8 back-EMF phases.

| rewind k (turns/coil) | string EMF pk | to shaft | belt | clamp | copper | T_motor | belt → shaft |
|:--|--:|--:|--:|--:|--:|--:|--:|
| 1 (1 846) | 282 V | 0.21 W | 4.75 W | 4.54 W | 0.0003 W | 6.6 mN·m | 4 % |
| 5 (9 230) | 1.4 kV | 1.01 W | 5.70 W | 4.68 W | 0.007 W | 32 mN·m | 18 % |
| 10 (18 460) | 2.8 kV | 2.09 W | 7.27 W | 5.13 W | 0.04 W | 67 mN·m | 29 % |
| **20 (36 920)** | **5.6 kV** | **4.31 W** | 11.4 W | 6.81 W | 0.29 W | **137 mN·m** | 38 % |
| 40 (73 840) | 11.3 kV | 4.53 W | 17.3 W | 11.3 W | 1.45 W | 144 mN·m | 26 % |

- **Timing comes from the plates alone.** C1's own displacement current d(C1·V)/dt is AC and locked to rotor angle.
  - Best phase: the utron's flux extreme falls at, or up to 7.5° of rotation before, plate alignment (C1 max), i.e.
    phase 315–0°.
  - About 90° electrical (15° of rotation) away from that, power falls to zero.
  - At 135–180° the coils **generate**: the PM C-EMs feed the pump, which is US2945141's forward function. At k 40,
    φ 180 the belt even receives power.
- **The utron count must match.** A coil must see 6 flux periods per rev, one per pump cycle (N_sec 12).
  - The present 3 utrons per side give −2.3 mN·m, i.e. nothing, at any phase.
  - So the tube needs **6 PM utrons per side**.
- **The useful range is about k 10–20.** Copper loss and the extra load on the pump take over by k 40. k 20 means
  ≈ 37 000 turns per coil, wire ≈ 0.09 mm in the same window [RH].
- **The coils add load: the belt rises from 4.5 to 11.4 W at k 20.** The clamp still dumps 6.8 W.
  - The clamp can't be dropped. Coil power grows ∝ V and pump surplus ∝ V², so without it the pump runs away at every
    k (the "no clamp" rows reach hundreds of kV).
- **The stator is still dragged along.** Net torque = T_motor − T_pump − drag.
  - T_motor / T_pump = shaft power / belt power < 1 in every row.
  - Best net: −142 mN·m (k 10, 315°).
  - This repeats the earlier result: a pump-fed motor cannot counter-rotate the stator.

### (b) BUS: no usable torque

| case | coil I_rms | T_motor | note |
|:--|--:|--:|:--|
| no coils | — | — | bus settles at −20.1 kV; D5/D6 carry only the 2 µA bleed (0.04 W) |
| k 1, all phases | 0.02 mA | −0.25 mN·m | the EMF circulates in the snubber |
| k 20, φ 0 / 180 | 0.39 mA | −99 mN·m | **a brake**: the 5.6 kV PM EMF drives 3.1 W through the snubber |
| k 20, φ 90 / 270 | 0.39 mA | −99 mN·m | the pump collapses (node 1 → 0 kV, bus left at −5.5 kV) |

- **No coil current at steady state.** Once C_bus is charged, nothing flows through D5/D6 except the bleed, so the
  coils carry almost no current.
  - A DC bus can only turn coils through commutation, i.e. switches. A constant current gives zero average torque
    with periodic flux [OC].
- **The inductive kick is real.** D5/D6 cut the coil current every cycle, so each string needs a snubber (10 MΩ here
  [RH]). That snubber is where the PM EMF's power goes.
- **The bus loads the pump.** z drops from 1.51 to ≈ 1.03 per cycle while C_bus charges, so the bus takes many cycles
  to reach V_op.

## Verdict
- **LEG is the only switchless placement that drives the C-EMs.**
- It needs PM utrons, 6 per side, phased within about 7.5° of plate alignment, and strings rewound to k 10–20.
  - That gives 2–4 W and 67–137 mN·m to the shaft at 20 kV and 300 rpm.
  - It still needs the avalanche clamp.
- The DC bus, C_bus, R_bleed, R_s and D5/D6 serve no purpose without switches. The new schematic drops them from (a).

## Caveats and open items
- PM flux swing 0.27 mWb per coil and a sinusoidal flux are [RH] (gate G-SWING).
- The winding at k 20 (≈ 37 k turns, ≈ 0.09 mm) is not yet checked against the window, heating or interturn voltage.
- **Insulation:** each string floats at its node potential, up to 20 kV, so coil-to-core and coil-to-frame insulation
  must take ≥ 20 kV (gate G-HV).
- Clamp: an avalanche-diode string, BV 20 kV, string resistance ~100 kΩ [RH]. It dissipates 4–7 W.
- **Phase:** sampled every 45°; the optimum lies between 315° and 0°.
- Varicap profile: cosine.
- The disc was not run.
- **Calculator:** `tools/pump-diode.html`'s "DC tap" column assumes a switched drive. Its "series" column is the D1/D2
  rail placement, not this leg placement.
