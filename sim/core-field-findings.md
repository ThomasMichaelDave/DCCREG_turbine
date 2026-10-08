# The electrostatic circuit's HV side on the rotor, and a field on the core — findings

**Source:**
- `sim/core_field.py` → `sim/core_field_results.json` (ngspice);
- the schematic's panel (b), `docs/schematic-rotor-circuits.svg` / `.png` (`docs/make_schematic_rotor.py`);
- the stack drawing's labels, `docs/figures/air-vane-stack-6mm.png`;
- the cost sheet, `docs/cost/` (`docs/make_cost_sheet.py`).

**Designer's decision.** Move the electrostatic circuit's high-voltage side onto the rotor, so the core can get an
electric field with the AH's steady cusp at its centre.

**The design.** The air build's capped stack (`sim/air_stack_sizing.py` stage 4c): 3 mm full-round vanes, 6 + 6 per
varicap per side, 6 × 22° / 22°, 6 mm gaps, r 150. That gives C 55–410 pF, Ca = Cb 451 pF and V_op 13.1 kV, at 1200 rpm
relative (120 Hz).

## 1. The move

**What changes:**

| part | before | now |
|:--|:--|:--|
| rotor vanes R-A / R-B | near the shaft, through the cones | **nodes 1 / 4** (HV) |
| stator vanes | nodes 1 / 4 (HV) | **REF of C1 / C2**, on the counter-rotor |
| Ca / Cb, D1–D4, Z1 / Z4 | counter-rotor | **rotor**, with the hub |
| cones | coils in series, at the shaft's potential | **the core's electrodes** (§2) |
| reference link | one inner bearing | the same bearing: it joins the stator vanes to the shaft |

**The pump does not change.** The circuit is the same; only the bodies under its parts move.
- The gain z is 1.3095 per cycle, against the stack's eigen-cycle 1.3090.
- The clamped power is 2.1423 W, against 2.1423 W before the move (within 0.002 %).

**The node waveforms (steady state, clamped):**
- node 1 swings from −5.7 to −13.2 kV; node 2 from 0 to −6.1 kV;
- V_Ca = V(1) − V(2) runs from −5.7 to −7.5 kV;
- V(1) − V(4) swings ±7.4 kV at 120 Hz.

**The reference link stays.**
- It carries 0.41 mA rms (0.92 mA peak) of pure AC, C1 and C2's displacement current. The DC through the diodes and
  clamps stays on the rotor.
- **A floating counter-rotor stops the pump [IR]:**
  - with 100 pF from the counter-rotor to the shaft, z is 1.000;
  - with 1 nF, z is 1.18.
  - The counter-rotor must stay tied to the shaft.

## 2. Putting a field on the core

Three ways to wire the cones [IR]. Strays [RH]: 20 pF per cone to the shaft side, 10 pF from cone to cone. E is quoted
over the cost sheet's placeholder 50 mm.

| option | what the core sees | E over 50 mm | z per cycle | clamped power | extra parts |
|:--|:--|--:|--:|--:|:--|
| none (no field) | — | — | 1.310 | 2.14 W | — |
| **series:** the cones stay coils, now between node 1 / 4 and the rotor vanes | V(1) − V(4): ±7.3 kV at 120 Hz, no DC | ±1.5 kV/cm AC | 1.233 | 1.76 W | none |
| **ca:** cone A on node 1, cone B on node 2 | −6.7 kV mean, 1.7 kV p-p (26 %); both cones also swing 6.5 kV p-p against the shaft | 1.3 kV/cm | 1.266 | 1.95 W | none |
| **peak:** cone A charged from node 1 through diode Dk and held by C_core 1 nF; cone B on the shaft | **−13.2 kV DC, 11 V p-p (0.1 %)** | **2.6 kV/cm** | 1.087 while charging, then 1.31 | **2.14 W** | Dk, C_core |

**For a steady field, take the peak option.**
- It gives the full operating peak, almost without ripple, and leaves the pump's power as it is.
- It meets the cost sheet's placeholder target of 10 kV (2 kV/cm over 50 mm).
- The other two cost gain: the cones' strays sit on the pumping nodes.
- The series option keeps the cones as coils, but with diodes only they carry 0.46 mA rms (0.05 A-turns): still
  decorative.

## 3. The peak option

**The core's leakage sets the load.** With C_core at 1 nF:

| core leakage R_leak [RH] | z while charging | cone A | p-p | leakage power | clamps |
|--:|--:|--:|--:|--:|--:|
| 10 GΩ | 1.087 | −13.2 kV | 11 V | 0.017 W | 2.12 W |
| 1 GΩ | 1.082 | −13.2 kV | 102 V | 0.17 W | 1.97 W |
| 0.1 GΩ | 1.035 | **−11.1 kV** | 0.72 kV | 1.23 W | 0.61 W, Z4 only |
| 0.05 GΩ | **0.987** | the pump does not start | | | |
| 0.03 GΩ | 0.958 | the pump does not start | | | |

- **Keep the core above about 1 GΩ.** Below about 0.06 GΩ the gain falls under 1, and the pump cannot start.
- **The ripple** follows V / (R_leak · C · f) within 5 %. A 0.1 nF C_core at 10 GΩ gives 83 V p-p and charges faster
  (z 1.225).
- **Start-up:** from −1 kV, cone A reaches 95 % in 32 cycles (0.27 s) with 1 nF.

**The parts:**
- **Dk:** reverse peak 7.5 kV, because node 1 never rises above −5.7 kV. It goes in the HV parts as a fifth diode stack.
- **C_core:** 1 nF, rated ≥ 20 kV (e.g. a ceramic doorknob), from cone A to the shaft.
- **The other diodes:** D1 / D2 see 6.1 kV reverse and D3 / D4 13.2 kV.
- **The clamps** take 1.07 W each, 0.96 mA peak.

**The field's direction.** The pump runs negative, so E points from cone B (on the shaft) down to cone A (−13.2 kV). On
the axis it is parallel to the cusp's B. To reverse it, run the core positive: flip every diode, the clamps and Dk
included, as de Queiroz's Fig. 1 draws it.

## 4. What the HV on the rotor asks of the build

**The G10 sleeve now holds node 1 off the shaft.**
- The rotor vanes' rings sit on the 8 mm sleeve over the d 25 shaft. At 13.2 kV the field is 2.1 kV/mm at the shaft and
  1.3 kV/mm at the sleeve's surface, which G10 holds in bulk.
- **An air film at the bore** sees about 4.7× the G10's field (εr), so 10 kV/mm. A 50 µm film then carries 0.50 kV
  against Paschen's 0.55 kV, and it would discharge on every cycle [OC].
- **Bond the sleeve to the shaft, or make its bore conductive** [RH]. The same applies, at a lower field, under the
  rings.

**The Ca / Cb stacks ride on the rotor.**
- **Mass:** their 6.1 kg moves to the rotor. That adds 0.076 kg m² to the rotor vanes' 0.029, i.e. 151 J against 57 J
  at 600 rpm per body.
- **Mounts:** the alternate plates (nodes 1 / 2, and 4 / 3) differ by V_Ca, 5.7–7.5 kV. The mounts between them need
  that much creepage. The mounts are not drawn.
- **Not re-run:** the shaft check (`sim/shaft_bearings.py`) and the solids (`sim/tube_geometry.py`) still put Ca / Cb
  on the counter-rotor. So does `sim/stack_sizing.layout`, which labels the stator vanes node 1 / 4.

**The hub.**
- Cone A at −13.2 kV DC sits next to the flange at its apex, the AH coils and cone B, all near the shaft's potential.
- The G10 shells meet at the equator.
- The electrode's extent on the shell sets the clearances and the creepage. It is not chosen.

**The counter-rotor carries no HV:** the stator vanes, the cage and the bridges are at REF.

**The parts on the rotor:**
- at 600 rpm they see 40 g at r 100 mm and 60 g at r 150 mm, so pot them and balance the rotor with them;
- the clamps' 2.1 W is shed on the rotor.

## 5. What was updated
- **The schematic's panel (b):** the new bodies, Dk, C_core, R_leak, the bicone as electrodes, and this stack's numbers
  (it showed the vacuum stack before).
- **The stack drawing's labels:**
  - stator vane = REF, rotor vane = node 1 / 4;
  - Ca plates on the rotor;
  - the aluminium per body;
  - a row for the HV side.
- **The cost sheet:**
  - **BOM fixed:** the HV-feed placeholder (120) becomes C_core (25), cone A's lead and clearance (60) and the rotor's
    HV insulation (80). The bicone becomes electrodes. The total is 3,461.
  - **HV parts** count five diode stacks (D1–D4, Dk).
  - **The cheapest design is unchanged** (5 mm gaps, 2 mm vanes, r 200, 18°, 4 + 4) at 5,637.

## Caveats
- **[RH]:**
  - the strays (20 pF per node and per cone, 10 pF cone to cone);
  - R_leak and C_core;
  - the bearing's contact (1 Ω);
  - the 50 mm spacing and the 2 kV/cm target.
- **[IR]:**
  - the three wirings;
  - the cosine C(θ);
  - the clamp model (soft knee, 100 kΩ);
  - E taken as V / d.
- **Not modelled:**
  - the field in the core: it needs the electrode geometry and a field solve;
  - corona at cone A's edges;
  - the bicone–AH coupling.
- **Not re-run with the HV on the rotor:**
  - the vacuum stack (`sim/bicone_drive.py`, `sim/rotor_parts_duty.py`) and its spark-gap dump. Its topology is the
    same, so its pump numbers carry over;
  - the solids and the shaft check (§4).
