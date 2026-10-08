# The electrostatic stacks in air: vane gap and vane count — findings

**Source:** `sim/air_stack_sizing.py` → `sim/air_stack_sizing_results.json`.

**Designer's question.** The first tests run in air. Space the vanes further apart, which lowers C but raises the
breakdown voltage, and choose the number of vanes N to compensate.

**Method:**
- **Hold-off:** air breakdown at 1 atm, 20 °C, uniform field. The operating peak is that ÷ 1.5, the vacuum design's
  own margin (30 / 20 kV) [RH].
- **Capacitance:** C per gap, aligned and opposed, from `stack_sizing`'s 2-D vane cell in air, so the fringing that
  raises C_min is in κ.
- **Gain:** z from the bare de Queiroz core.
- **Power:** the clamped pump power at 1200 rpm relative, from `sim/bicone_drive.py`'s netlist in ngspice.
- **Fixed:** the tube's radius (r 50–150 mm) and 1.5 mm Al vanes. Ca / Cb get the same gap.
- **Lengths:** per side, varicap + Ca, against today's 100 mm. The tube length is the built 802 mm with these stacks
  swapped in.

## 1. The idea is right, but the gap buys voltage, not power density

**Energy per cycle.** It goes as C·V². For a fixed vane count, a wider gap has C ∝ 1/g while V_op grows roughly ∝ g,
so each vane pumps more. The catch is air's hold-off:

| gap | 3 mm | 5 mm | 6 mm | 8 mm | 10 mm | 12 mm | 15 mm |
|:--|--:|--:|--:|--:|--:|--:|--:|
| breakdown in air | 10.9 kV | 16.8 kV | 19.7 kV | 25.4 kV | 30.9 kV | 36.4 kV | 44.6 kV |
| operating peak (÷ 1.5) | 7.3 kV | 11.2 kV | 13.1 kV | 16.9 kV | 20.6 kV | 24.3 kV | 29.7 kV |
| operating field | 2.4 kV/mm | 2.2 | 2.2 | 2.1 | 2.1 | 2.0 | 2.0 |

- **The vacuum design runs at 6.7 kV/mm.** Air allows about a third of that at any gap, i.e. about a tenth of the
  stored energy per unit of gap volume.
- **Wider gaps don't change that,** and the vanes' own thickness costs relatively less at wide gaps. So the clamped
  power per metre of stack is set by air, not by the gap.

## 2. With today's 6-sector vanes, wide gaps kill κ

Each row adds vanes to keep C_max at the vacuum design's 1113 pF.

| gap | vanes N | κ = C_max/C_min | gain z | clamped power | stacks per side | tube | rotor vanes |
|:--|--:|--:|--:|--:|--:|--:|--:|
| vacuum 3 mm (built) | 8 | 15.7 | 1.515 | **18.5 W** | 100 mm | 802 mm | 1.5 kg |
| air 3 mm (as built) | 8 | 15.7 | 1.515 | 2.44 W | 100 mm | 802 mm | 1.5 kg |
| air 5 mm | 13 | 7.9 | 1.39 | 5.16 W | 242 mm | 1085 mm | 2.4 kg |
| air 6 mm | 15 | 6.2 | 1.33 | 6.29 W | 324 mm | 1249 mm | 2.8 kg |
| air 8 mm | 19 | 4.4 | 1.23 | 8.08 W | 524 mm | 1649 mm | 3.6 kg |
| air 10 mm | 23 | 3.4 | 1.15 | 5.87 W | 784 mm | 2168 mm | 4.3 kg |
| air 12 / 15 mm | 27 / 32 | 2.8 / 2.2 | 1.09 / 1.02 | never reaches its clamp | 1.1 / 1.6 m | | |

**Why κ falls.** At the opposed (minimum-C) position, a rotor vane's edge is only 4° (about 7 mm at mid-radius) from
the next stator sector. Once the axial gap is comparable, the fringe field holds C_min up.

## 3. Reshaping the sectors restores κ

The search covered 3 / 4 / 6 sectors with narrower stator and rotor widths at 6, 8 and 10 mm (54 designs). Below is
the best per gap: z ≥ 1.3, most power per millimetre.

| gap | sectors, stator / rotor width | N | κ | z | clamped power | stacks per side | tube | rotor vanes |
|:--|:--|--:|--:|--:|--:|--:|--:|--:|
| 6 mm | 6, 24° / 22° | 16 | 8.4 | 1.40 | 7.43 W | 346 mm | 1294 mm | 3.0 kg |
| 8 mm | 6, 24° / 18° | 23 | 5.8 | 1.31 | 10.2 W | 610 mm | 1820 mm | 3.5 kg |
| 10 mm | 4, 36° / 33° | 25 | 7.5 | 1.37 | 11.0 W | 830 mm | 2260 mm | 4.7 kg |

- **Fewer sectors give the best κ:** 3 sectors at 6 mm reach κ 26 and z 1.58. They also give fewer pump cycles per
  revolution and so less power. With 4 or 6 sectors, narrowing the stator widens the clearance at the minimum-C
  position.
- **Power per metre of stack, clamped:**

  | design | W per metre |
  |:--|--:|
  | vacuum (built) | 184 |
  | air, today's 3 mm stack | 24 |
  | air 6 mm, reshaped | 21 |
  | air 8 mm, reshaped | 17 |
  | air 10 mm, reshaped | 13 |

  So **in air the densest stack is today's 3 mm one**, and widening the gap only ever costs power per metre.
- **Matching the vacuum design's 18.5 W in air** needs about 0.76–0.95 m of stack per side, i.e. a 2.1–2.5 m tube.
  At 3 mm that is N ≈ 58; at 6 mm (reshaped) N ≈ 40.

## 4. Other effects of the gap in air [RH]

- **Vane-edge corona.** Peek's law, with 1.5 mm vanes and fully rounded edges (r 0.75 mm), puts the onset near
  66 kV/cm. The edge field (a cylinder-to-plane estimate) is:

  | gap and operating peak | edge field |
  |:--|--:|
  | 3 mm at 7.3 kV | 47 kV/cm |
  | 6 mm at 13.1 kV | 63 kV/cm |
  | 8 mm at 16.9 kV | 74 kV/cm |
  | 10 mm at 20.6 kV | 84 kV/cm |

  So 3 mm is clear and 6 mm is at the limit. Wider gaps need rolled vane rims of about 2 mm radius (onset then
  ≈ 52 kV/cm, and the field at 10 mm drops to ≈ 45 kV/cm).
- **Tolerances relax with the gap.** A 6 mm gap takes twice the vane flatness and runout error of a 3 mm one, and
  electrostatic pull-in recedes further.
- **Shaft.** A full-power stack of 0.76–0.95 m per side puts about 5–6 kg of rotor vanes on that span. A 25 mm
  shaft's first bending mode then lands near 40–60 Hz: above the 30 Hz criterion (3 × 600 rpm), but it needs a check
  with `sim/shaft_bearings.py`, a thicker shaft or a mid-stack bearing. The 346 mm option stays near 250 Hz.
- **The reluctance pump is unaffected.** It was sized in air.

## 5. What it means for the air phase

| option | gap / vanes | clamp | power (1200 rpm) | tube |
|:--|:--|:--|--:|--:|
| **A. today's stack** | 3 mm / 8 | ≈ 7 kV | 2.4 W | 0.80 m |
| B. more vanes at 3 mm (the densest) | 3 mm / 16 | ≈ 7 kV | ≈ 5.0 W | ≈ 1.0 m |
| C. reshaped 6 mm | 6 mm / 16, 24° / 22° | ≈ 13 kV | 7.4 W | 1.29 m |
| D. vacuum-equivalent power in air | 3–6 mm / 40–58 | 7–13 kV | 18.5 W | 2.1–2.5 m |

- **What the gap is for.** The choice between gap and vane count turns on what the air phase must show. The gap only
  pays if the test needs the *voltage*: e.g. dump energy ∝ V², or the stress on the 20 kV-class diodes and insulation.
- **If it needs the pump working, or its power,** more vanes at 3 mm is cheaper per watt and has no edge-corona issue.
- **Option B is scaled, not run:** twice the working gaps of A at the same geometry and V_op.

## Caveats
- **[RH]:** the 1.5 margin on uniform-field air breakdown (humidity, temperature and the vane edges all move it).
- **Clamped power:** near-ideal diodes, cosine C(θ).
- **The same-power vane counts** scale the clamped power with the working gaps at fixed geometry and V_op.
- **κ at the inner and outer rims:** these edges are a fixed 2 pF floor, not part of the 2-D cell.
- **12 and 15 mm:** with today's sectors the pump didn't reach the clamp within the 24-cycle run (z 1.09 / 1.02). That
  is too little gain to count on with real losses.
