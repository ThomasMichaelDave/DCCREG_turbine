# The hub's temperature, the AH coils as wound, and the vessel's resistivity — findings

**Source:** `sim/hub_thermal.py` → `sim/hub_thermal_results.json` (about a minute: four ngspice runs of the pump's
deck, then the conduction cases).

**Status:**
- [OC] the conduction, the copper's resistance and its temperature coefficient;
- [IR] the materials' conductivities, the winding's layout and the Arrhenius fit through the record's two points;
- [RH] the convection off the hub (about 20 W/m² K) and the air between the vane stacks (5 K over the room).
- The ledger's open item "the vessel's resistivity" gets an estimate here; the bench measures it.

## Headline
- **The AH coils as wound:** 160 turns of 0.80 mm grade-1 enamelled wire (0.869 mm over the enamel), orthocyclic in 4
  layers of up to 46 turns.
  - That builds 3.13 mm in the 3.2 mm window, with 9.7 m of wire: **R 0.333 Ω at 20 °C**, 0.36 Ω at the coil's
    41 °C.
  - It is the largest standard wire that fits. The deck's 0.27 Ω (`sim/magnetic_doubler.py` AH r160) scaled
    variant (a)'s 50 turns of 1.6 mm wire as N² "in the same window", which is a window full of bare copper.
  - With 0.333 Ω the pick drives **294 A-turns per coil** with the 22 mF bypass (300 at 0.27 Ω), and 285 / 271 without
    it. The bypass stays PROPOSED.
- **Each coil dissipates 1.22 W** with the bypass and 1.28 W without, at the coil's temperature. Nothing else in the hub
  heats it noticeably [RH]:
  - the MnZn rods sit at 0.12 T DC with a small ripple;
  - the rings leak picoamperes.
- **The temperatures**, with a 25 °C room, the air between the vane stacks 5 K above it [RH] and h 20 W/m² K [RH]:

| part | with the bypass | without |
|:--|--:|--:|
| the coil, mean / hottest | 41.1 / 43.2 °C | 41.7 / 43.9 °C |
| the rod's tip at the seat | 41.5 °C | 42.1 °C |
| the glass at the poles / at the equator | 37.2 / 32.2 °C | 37.6 / 32.4 °C |
| **the glass between the rings** (55.7–90°) | **32.5 °C** | 32.7 °C |
| the coupler's surface, the flange | 32.7, 32.6 °C | 32.9, 32.7 °C |

- **The vessel's resistivity in service** [IR]:
  - the record's 1e13 Ω·m holds at 25 °C. Through its 25 / 40 °C points (`sim/hub_drift.py` SIG) borosilicate falls
    with an activation energy of 0.90 eV;
  - at 32.5 °C, between the rings, that gives **4.2e12 Ω·m (σ 2.4e-13 S/m), 2.4 × its 25 °C conductivity**;
  - at the poles' 37 °C it is 2.5e12 Ω·m.
- **Against the equatorial beads' limit:** σ_glass ≤ 4.06 σ_gel with the drawn grooves and ≤ 4.37 with the
  recommended full-round ones (`sim/hub-beads-settled-findings.md` §7). The gel is held at its 25 °C 1e-13 S/m.
  - In service the ratio is 2.4, between 2.2 and 3.0 over the cases below. The beads hold.
  - The margin in temperature: the glass between the rings may reach 37.3 °C (drawn) or 38.0 °C (full-round). That
    is **a room up to 29.8 °C, or 30.5 °C**, with the air 5 K above it.
  - The margin is thin, so the bench must measure both conductivities at temperature (phase 3 and its 40 °C repeat).
    A gel whose conductivity also rises with temperature widens it; most do [RH].
- **The settled field at the null** in service lies between the 25 °C and 40 °C cases: about 8.26 kV/cm at
  σ_glass / σ_gel 2.4 (`sim/hub-beads-settled-findings.md` §7; 7.62 at switch-on).

## 1. The winding
- **The window** (`presets/hub-locked.json` AH): r 8.25–11.45 mm, |z| 31.35–71.35 mm, so 3.2 mm by 40 mm, on the G10
  former (Ø13.5 / 16.5 mm) over the 77 MnZn rod (Ø12.3 mm).
- **The wire** [IR datasheet-class]: IEC 60317-0-1 grade 1 maximum overall diameters, wound orthocyclic. Each layer
  sits d_o·√3/2 over the one below [OC].

| bare / over the enamel | per layer | layers for 160 | build | fits 3.2 mm |
|:--|--:|--:|--:|:--|
| 0.75 / 0.817 mm | 48 | 4 | 2.94 mm | yes |
| **0.80 / 0.869 mm** | **46** | **4** | **3.13 mm** | **yes: the largest** |
| 0.85 / 0.922 mm | 43 | 4 | 3.32 mm | no |

- **The resistance** [OC]:
  - the layers' mean radius, weighted by their turns (46, 46, 46, 22), is 9.64 mm, so 160 turns take 9.70 m;
  - R20 = 1.724e-8 Ω·m × 9.70 m / 0.503 mm² = **0.333 Ω**. At 41 °C it is 0.36 Ω (+0.393 %/K).
- **The deck's 0.27 Ω** (`sim/magnetic_doubler.py`:50, "R ~ N² in the same window" [RH]): variant (a)'s 50 turns of
  1.6 mm wire fill the window at π/4, which is bare copper, square-packed. Real enamel and orthocyclic layers give
  0.333 Ω (+23 %).
- **The pump with the wound coil** (the pick, `sim/rotor_parts_duty.py`'s settings, re-run in ngspice):

| coil R | bypass | coil A: mean (rms) | coil B: mean (rms) | A-turns, mean |
|:--|:--|:--|:--|:--|
| 0.27 Ω (the deck's) | none | 1.812 (1.924) A | 1.728 (1.924) A | 290 / 276 |
| 0.27 Ω | 22 mF | 1.874 (1.874) A | 1.876 (1.872) A | 300 / 300 |
| **0.333 Ω (as wound)** | none | 1.779 (1.885) A | 1.694 (1.885) A | 285 / 271 |
| **0.333 Ω** | **22 mF** | **1.837 (1.837) A** | **1.840 (1.836) A** | **294 / 294** |

- **So the steady cusp is 2 % weaker as wound:** 0.111 T/m at the null instead of 0.113 (`sim/ah-null-findings.md`:
  0.377 mT/m per A-turn on both coils) [OC]. At the coil's 41 °C (0.36 Ω) about 1 % more goes.
- **The deck keeps 0.27 Ω** [IR]: every pump study of record runs on it. The difference is recorded here, not
  carried through them.

## 2. The model
- **The conduction** [OC]: steady, axisymmetric finite volumes on the hub's half z ≥ 0, 0.25 mm cells. The midplane
  is adiabatic, since the two coils are alike.
- **The parts** (`presets/hub-locked.json` hub entries), W/m K [IR datasheet-class]:

| part | k |
|:--|--:|
| borosilicate vessel | 1.15 |
| the vacuum inside: radiation, 4σT³D / (2/ε − 1), ε 0.9 [RH] | 0.22 |
| silicone gel (the pocket) | 0.20 |
| PEEK retainer | 0.25 |
| G10 coupler and formers | 0.30 |
| 77 MnZn rod | 4.0 |
| the coil, impregnated (sensitivity 0.5–2) | 1.0 |
| potting: rod to former, the coil's ends | 0.20 |
| stainless flanges and shaft | 16 |

- **The coupling** [IR]: the AH is bonded into its bore and its rod seats on the flange.
- **The boundaries** [RH]:
  - convection off the coupler, the flanges and the shaft at h, against the air between the vane stacks;
  - h for a cylinder of 33 mm radius turning at 600 rpm: 2.1 m/s at its surface, Re about 8,500, so about
    20 W/m² K. The cases also run 10 and 40;
  - the shaft beyond |z| 110 mm is an infinite fin, √(h P k A) = 0.15 W/K at h 20.
- **The heat** [OC]: I_rms² R per coil, R at the coil's mean temperature (iterated).
- **The mesh:** at 0.125 mm cells the hottest coil's rise moves +0.4 %, the band's −0.1 % and the poles' −1.1 %
  (✔ ≤ 2 %).

## 3. The cases
Above the room (25 °C) and the air (30 °C); with the bypass unless stated:

| case | P per coil | coil, hottest | glass: poles / between the rings | σ_glass / σ_gel between the rings |
|:--|--:|--:|:--|--:|
| h 10 W/m² K | 1.224 W | 45.2 °C | 39.1 / 34.3 °C | 2.92 |
| **h 20 (the base)** | **1.216 W** | **43.2 °C** | **37.2 / 32.5 °C** | **2.38** |
| h 40 | 1.211 W | 42.1 °C | 36.1 / 31.7 °C | 2.16 |
| h 20, the coil's k 0.5 | 1.218 W | 44.0 °C | 37.3 / 32.6 °C | 2.39 |
| h 20, the coil's k 2 | 1.213 W | 42.3 °C | 36.9 / 32.5 °C | 2.36 |
| without the bypass, h 20 | 1.283 W | 43.9 °C | 37.6 / 32.7 °C | 2.42 |
| without the bypass, h 10 | 1.293 W | 46.0 °C | 39.6 / 34.6 °C | 3.00 |

- **Most of the hub's rise is the air's:** of the gap band's 7.5 K over the room, 5 K is the air between the vane
  stacks [RH] and 2.5 K the hub's own. The air's figure matters most; the drive's heat (`docs/drive-gear-belt.md`,
  about 60 W at the belt) warms it.
- **The coils are cool:** 43 °C against a class-B (130 °C) or class-F winding.

## 4. The vessel's resistivity
Borosilicate through the record's two points (1e-13 S/m at 25 °C, 5.4e-13 at 40 °C), Arrhenius with 0.90 eV [IR]:

| glass | 25 °C | 30 °C | 32.5 °C (between the rings) | 35 °C | 37.3 °C (the beads' limit) | 40 °C |
|:--|--:|--:|--:|--:|--:|--:|
| ρ | 1.0e13 Ω·m | 5.6e12 | **4.2e12** | 3.2e12 | 2.5e12 | 1.85e12 |

- **For the records:** `presets/hub-locked.json` vessel_resistivity keeps 1e13 Ω·m at 25 °C, now with 0.90 eV and the
  service estimate 4.2e12 Ω·m. It stays OPEN until the bench's phase 3 measures it.
- **The glass's own leakage** between the rings stays negligible against the supply's 100 GΩ per ring, even at 40 °C
  (`sim/hub_rings_build.py` LEAKAGE: the field side about 2e14 Ω at 25 °C) [OC: the ratio of conductivities].

## Caveats
- **[RH] the air between the vane stacks** at 5 K over the room is not computed. Its heat comes from the rotor's
  utrons (13.5 W of copper), La / Lb, the windage and the bearings, against the cage and the frame's cooling.
- **[RH] h** is a correlation's order of magnitude for a rotating cylinder in stirred air, and the cases bracket it.
- **[IR] the gel's conductivity** is held at its 25 °C value. Its temperature dependence is not in the records, and it
  sets the beads' margin with the glass's.
- **[IR] the glass is not uniform:** the bead study varied the glass's conductivity as a whole. The poles run 4.7 K
  warmer than the band between the rings; that does not touch the polar beads, which are insensitive to it.
- **[IR] axisymmetric:** the leads, the coil's own leads and any split in the retainer are not modelled.
