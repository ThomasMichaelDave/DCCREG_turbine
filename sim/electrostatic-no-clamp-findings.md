# The electrostatic core: diode directions, running without the clamps, and testing in air — findings

**Scripts:**
- `sim/queiroz_fig1_check.py` → `sim/queiroz_fig1_check_results.json`;
- `sim/no_clamp_breakdown.py` → `sim/no_clamp_breakdown_results.json`.

**Designer's inputs:**
- The record schematic uses spark gaps, so it can't fix the diode directions. Check them against de Queiroz's Fig. 1.
- The 20 kV Zener clamps might not be needed: without them the voltage rises to breakdown. What is the issue?
- The first tests run in air, not vacuum.

## 1. The diode directions match de Queiroz, at the opposite polarity

**The paper.** A. C. M. de Queiroz, *Analysis of Electronic Electrostatic Generators*, Fig. 1, the "symmetrical
unipolar generator":
- C1 (node 1) and C2 (node 4) are variable, each to ground; Ca joins 1–2 and Cb joins 3–4.
- Diodes, anode → cathode: D1 ground → 2, D2 ground → 3, D3 3 → 1, D4 2 → 4.
- All voltages are positive.

**The repo** (`solveDoubler4`, `sim/bicone_drive.py`, `sim/magnetic_doubler.py` and the schematic): D1 2 → ref,
D2 3 → ref, D3 1 → 3, D4 4 → 2.
- **Every diode is reversed, and consistently so.** This is the same circuit at negative polarity, which is why the
  repo seeds −1 V and its nodes run negative.
- The capacitor placement and the antiphase of C1 / C2 are the same as the paper's.

**Check.** The paper's own example in ngspice: C1 and C2 complementary, 60–360 pF; Ca = Cb = 330 pF; 20 Hz.

| diode set | seed | gain per cycle z | polarity |
|:--|:--|--:|:--|
| the paper's | +1 V | **1.37205** | all nodes + |
| the repo's | −1 V | **1.37200** | all nodes − |
| the repo's with D1 alone flipped | −1 V | 1.065 (3.8× in 14 cycles, against 87×) | mixed |

- **The match:** the paper gives z = 1.17138 per *half* cycle (its eq. (15) maps phase 1 onto phase 2 with the nodes
  swapped). That is 1.17138² = **1.37213 per cycle**, matching both simulations to better than 0.01 %.
- **Mixing directions breaks it:** flip any single diode and it is a different and much weaker machine.
- **Seeding:** the circuit grows from a seed on the variable capacitors (nodes 2 and 3 at 0). Seeding all four nodes
  alike excites a decaying mode (z 0.806). This is the paper's "complicated operation during startup".

**To build it positive like the paper:** reverse all four diodes and the clamp strings together. Nothing else changes.

## 2. Without the clamps the pump becomes a relaxation oscillator

**The model.** `sim/bicone_drive.py`'s diodes-only circuit at 1200 rpm relative (120 Hz), changed as follows:
- the clamps Z1 / Z4 removed;
- an arc across each vane stack (node 1 to R-A, node 4 to R-B) when the gap reaches its breakdown voltage;
- the counter-rotor's reference rail and the shaft joined by a measured link (for now an inner bearing);
- ammeters in D1–D4.

**The arc** [RH] strikes at the breakdown voltage and conducts both ways. It stays alight while its current exceeds
2 A, and has 1 Ω and 200 nH, with 5 Ω for the vane stack's own plates and leads.

| at 1200 rpm relative | **air** (3 mm at 1 atm: 10.9 kV, uniform field) | **vacuum** (30 kV, the 10 kV/mm design field) |
|:--|--:|--:|
| strikes per second per side | 26–31 (one every ~4 cycles) | ≈ 32 |
| energy per strike | 43 mJ | 300 mJ |
| node 1 just after a strike | 0.32 kV | 0.32 kV |
| arc duration (above 2 A) | 220 µs | 310 µs |
| pump power (belt) | 2.5 W | 19.1 W |
| … into the arcs / diodes / cones | 1.7 / 0.7 / 0.08 W | 14.7 / 3.8 / 0.7 W |
| peak current in D1 / D2 / D3 / D4 | 40 / 47 / 28 / 25 A | 104 / 80 / 77 / 71 A |
| peak current in the cones (A-turns) | 28 / 25 A (890) | 77 / 71 A (2460) |
| **reference link (bearing): peak / rms / charge per strike** | **38 A / 1.8 A / 2.1 mC** | **89 A / 5.4 A / 6.2 mC** |
| local spike of the vane stack's self-discharge | 330 A | 730 A |

**It does not collapse.**
- **Electrically:** each strike empties the pump almost completely (node 1 to about 0.3 kV). It rebuilds at about
  ×1.5 per cycle and strikes again about 4 cycles later, so it runs as a relaxation oscillator, not as a stopped
  machine.
- **Mechanically:** a rough estimate [RH] puts the vanes' electrostatic pull-in near 75 kV, well above either
  breakdown voltage. The estimate takes the attraction's negative stiffness, 2ε₀AV²/d³, against a 1.5 mm Al rotor
  sector cantilevered 100 mm.

**What goes wrong instead:**
- **The vanes become the spark gap.**
  - Most of the pump's power goes into arcs at the vane stack: 1.7 W in air, 14.7 W in vacuum.
  - Repeated arcs pit the vanes. Pits raise the local field, which lowers the breakdown voltage. In vacuum the arcs
    also spray metal onto the G10.
  - Tracking on those coated surfaces is the slow road to a machine that no longer builds voltage.
  - Where it breaks down is not controlled: it could equally be the Ca / Cb plates (the same 3 mm), an edge or an
    insulator surface.
- **Surges through the diode stacks.**
  - D1–D4 carry 25–47 A peaks in air and 70–105 A in vacuum, against a rating of a few mA (e.g. 2CL77, 5 mA).
  - They need the 10–47 kΩ series surge resistors of `sim/diode-stack-findings.md` (the model has none). Those
    resistors would also take most of the current out of the cones.
- **Surges through the bearing.** The same discharge closes through the counter-rotor-to-shaft link.
  - Even in air that is 38 A peaks, 2 mC per strike and 1.8 A rms through a 6205's rolling contacts: enough to
    erode it.
  - **So "no clamps" and "the reference through the bearings" do not go together.**
- **Uncontrolled voltage.** Every part has to stand whatever breaks down first, instead of a defined 20 kV.
- **The one upside:** the cones do get real pulses (890 A-turns in air), but at an uncontrolled place and rate.

## 3. Testing in air

**The breakdown limit drops to about 10.9 kV.**
- The 3 mm vane and plate gaps hold about 10.9 kV in air (uniform field; `sim/stack_sizing.gap_breakdown_kV`).
- The vane edges lower that, and corona from the edges can bleed charge from a few kV upward [RH].
- **So in air the 20 kV clamps would never conduct.** The air breaks down first, and the machine runs as in §2's air
  column.

**Options for the air tests:**
- **(a) Clamp below the air breakdown.** About 7 kV, i.e. about 35 × 200 V in the same string.
  - The pump then gives about (7 / 20)² of the vacuum figure: roughly 2.3 W at 1200 rpm, 1.1 W per clamp.
  - Nothing sparks, and the bearing link carries only the AC displacement current (well under 1 mA).
- **(b) Let it spark.** Fit the diodes' surge resistors and use a brush, not the bearing, for the reference link.
- **(c) Add a defined spark gap set below the vane breakdown** (the dump): controlled pulses through the cones. It
  needs the same brush.

**The magnetic circuit is unaffected by air.** It was sized in air and runs cooler there (coil 46 °C against 63 °C in
vacuum).

## Caveats
- **Arc model [RH]:** strike at a fixed voltage, current-sustained above 2 A, 1 Ω + 200 nH, 5 Ω of vane stack.
  Restrike and the real arc voltage shape the tail, not the first peak.
- **Diodes:** near-ideal, with no series resistors and no forward drop of a real HV stick. Both would cut the surge
  peaks and the 220–310 µs freewheel through the cones and the link.
- **Breakdown site:** only the vane gaps were given one.
- **The vacuum run's window:** it covers about 63 ms of strikes (about 2 per side); the air run covers 190 ms.
- **The solver:** the strikes are stiff. `itl4=500 reltol=2e-3` runs both cases; the strike rate agrees within ±10 %
  across the settings tried.
