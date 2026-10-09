# Rotor parts: what La / Lb, the clamps and the reference link must carry — findings

**Source:** `sim/rotor_parts_duty.py` → `sim/rotor_parts_duty_results.json`.

**What it runs:** both netlists of record, at the pick (g 0.5 / 6 bridges / 1200 rpm relative):
- the magnetic dual doubler (`sim/magnetic_doubler.py`), exactly as `sim/pole_design.size_op` runs it;
- the electrostatic diode doubler (`sim/bicone_drive.py`, diodes only), at 600 and 1200 rpm relative.

**Cross-checks:**
- The magnetic run reproduces the pick: AH 449 A-turns, belt 17.58 W, La + Lb copper 0.66 W.
- The 600 rpm electrostatic run reproduces `sim/bicone_drive_results.json`: belt 9.13 W.

**Schematic:** `docs/schematic-rotor-circuits.svg` now carries these values and the bearing path of §4.

## 1. La and Lb are two DC chokes

**What they are.** La and Lb are the fixed coupling inductors of the magnetic doubler, the duals of Ca / Cb:
- La runs from REF to node a; Lb runs from node c to REF.
- Both sit on the rotor.
- They are not designed yet. The model gives each 0.146 H (0.6 × the group's aligned L) and τ = L/R 0.5 s, i.e.
  0.29 Ω [RH].

**What they carry, each, at the pick:**

| | La | Lb |
|:--|--:|--:|
| current | 0.87–1.15 A | 0.87–1.15 A |
| mean / rms | 1.05 / 1.05 A | 1.04 / 1.05 A |
| peak voltage across it | 110 V | 101 V |
| peak stored energy | 96 mJ | 96 mJ |
| copper loss (0.29 Ω) | 0.32 W | 0.32 W |

- **The current is almost pure DC**, with a ripple of ±13 % at the pump frequency.
- **So the core has to hold a DC bias.** That means a gapped core, like a filter choke.
- **The AC flux swing is small,** so laminated SiFe is fine.
  - **Corrected 2026-10-09** (`sim/parts-first-cut-findings.md` §1): the iron loss is small, not negligible: about
    0.12–0.21 W per choke [RH], against 0.33 W of copper.

**How much the 0.5 s matters.** The runs below keep the pick's Ψ_s; the operating point is not re-solved.

| τ of La / Lb | z (early) | AH peak | La + Lb copper |
|:--|--:|--:|--:|
| **0.5 s (the model)** | **1.139** | **449 A-turns** | 0.66 W |
| 0.2 s | 1.123 | 427 A-turns | 1.47 W |
| 0.1 s | 1.092 | 394 A-turns | 2.46 W |
| 0.05 s | 1.026 | 334 A-turns | 3.40 W |

- **0.2 s costs 5 % of the AH field.** A slightly larger neck would win it back.
- **Below about 0.1 s the gain margin goes.**

**A first cut of the choke [RH].** Assumptions:
- a scrapless EI core of M235-35A with a square centre leg and the gap in the centre leg;
- 1.2 T at the peak current;
- fill 0.5;
- copper at 20 °C, as for the utrons' τ.

| τ | centre leg | turns | wire | gap | iron | copper |
|:--|--:|--:|--:|--:|--:|--:|
| 0.5 s | 28 mm | 179 | 1.64 mm² (Ø 1.44) | 0.21 mm | 1.00 kg | 0.41 kg |
| 0.2 s | 23 mm | 258 | 0.79 mm² (Ø 1.00) | 0.31 mm | 0.58 kg | 0.23 kg |

- **The gap is small,** so the iron and the lamination joints add about 20 % to its reluctance. A real design trims
  the turns or the gap to land on 0.146 H.
- **Mass:** the 0.5 s pair (2.8 kg) is about a fifth of the six utrons' 13.4 kg. Both chokes ride on the rotor, so
  mount them close to the axis.

## 2. D1*–D4*

| diode | D1* | D2* | D3* | D4* |
|:--|--:|--:|--:|--:|
| peak reverse voltage | 112 V | 101 V | 43 V | 45 V |

The branch current peaks at 2.8 A. This closes the open item on the schematic and in `sim/hub-drive-findings.md`
(there for the older design point).

## 3. Z1 / Z4, the 20 kV clamps

**What they are.** Passive avalanche-diode strings, one from node 1 and one from node 4 to the counter-rotor's
reference rail.
- **They set the operating voltage of the electrostatic pump.** The doubler gains more than 1 per cycle, so without
  them the nodes grow until something breaks down. The no-clamp rows of `sim/switchless-cem-findings.md` reach
  hundreds of kV.
- **They conduct once per cycle, near the voltage peak,** and turn the whole surplus into heat.
- **Model:** BV 20 kV at 1 µA, a soft knee and 100 kΩ of string resistance [RH] (`sim/bicone_drive.py`,
  `sim/switchless_cem.py`).

**Duty per clamp:**

| | 600 rpm relative (60 Hz) | **1200 rpm relative (120 Hz, the pick)** |
|:--|--:|--:|
| power | 4.57 W | **9.25 W** |
| current: peak / mean / rms | 2.30 / 0.23 / 0.62 mA | 4.42 / 0.45 / 1.24 mA |
| conduction | 16 % of each cycle | 16 % of each cycle |
| energy per cycle | 76 mJ | 77 mJ |
| node peak | 20.23 kV | 20.44 kV |

- **Together the two clamps take the pump's whole output** (18.5 W at the pick).
- The cones carry 2.7 mA rms, so with diodes only the bicone is still decorative.

**As a part [RH].** A series string of avalanche (Zener) diodes, for example 100 × 200 V.
- **Load per diode:** 0.09 W at 1200 rpm, a few per cent of a 5 W axial part's rating.
- **Polarity:** the nodes run negative, so the string's anode end goes to the node and its cathode end to the rail.
- **Voltage:** the string's breakdown voltage *is* the operating voltage.
  - Part tolerance (±5 % is common) and the positive temperature coefficient of high-voltage Zeners (around
    +0.1 %/K) move the operating voltage.
  - Select or trim the string by whole parts: each 200 V part is a 1 % step.
- **Insulation:** the string holds 20 kV end to end, so it needs the creepage of an HV assembly (potted, or in oil).
- **Place:** on the counter-rotor next to nodes 1 / 4, at 1 atm and outside the vacuum, like the D1–D4 stacks
  (`sim/diode-stack-findings.md`). With the HV side on the rotor (`sim/core-field-findings.md`), the clamps and D1–D4
  ride on the rotor instead.
- **Cooling:** about 9 W per string.

## 4. The reference link runs through the bearings for now (designer's decision)

**What crosses between the bodies.** The counter-rotor-to-shaft current is the sum of the two cone currents, i.e. the
displacement current of C1 and C2.
- At 1200 rpm it is **2.25 mA rms and 4.4 mA peak, pure AC, with no DC** (1.12 mA rms at 600 rpm).
- The DC through the clamps and D1 / D2 circulates on the counter-rotor and never crosses. With the HV side on the
  rotor it circulates on the rotor; the link still carries only C1 and C2's AC (`sim/core-field-findings.md` §1).

**The path.** The rail connects through a lead to the outer ring of one inner bearing, then through the balls and the
inner ring to the steel shaft.
- The spiders and the cage are G10, so the bearings' outer rings are insulated unless wired.
- Wire one inner bearing (or two) on purpose and leave the others insulated, so the path is known.

**Diodes only: probably fine [RH].**
- Milliamp currents are far below the current densities associated with electrical erosion of rolling bearings.
- The lubricant film will make the contact intermittent, so the rail may sit a few volts off the shaft. That is
  negligible beside 20 kV.
- A conductive grease makes the contact steadier; a PFPE vacuum grease insulates.

**Not with the dump.** The spark-gap dump's 21 A pulses (54 mJ each, 60 per second per side in the 600 rpm run) close
through this link, so they would pit the bearing's races. Trying the dump needs a real brush or slip ring first.

**The magnetic circuit is not affected:** it is entirely on the rotor.

## Caveats
- **[RH]:** the choke sizing, the clamp-string construction and the bearing judgement are first cuts.
- **[IR]:** the clamp model (soft knee, 100 kΩ) and the La / Lb τ.
- **Not re-solved:** the τ sweep holds Ψ_s at the pick's value.
- **Not covered:** the electrostatic dump was not re-run at 1200 rpm.
