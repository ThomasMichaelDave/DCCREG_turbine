# The electrostatic stacks in air: vane gap and vane count — findings

**Source:** `sim/air_stack_sizing.py` → `sim/air_stack_sizing_results.json`; the vane edge profile and the rim field in
`sim/vane_cell.py`; the drawing `docs/figures/air-vane-stack-6mm.png` (`docs/make_air_vane_drawing.py`).

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
- **Lengths:** from `stack_sizing.layout`, the layout that is drawn and built. Per side: the first varicap vane to the
  last Ca plate, against today's 105 mm. The tube: the built 802 mm plus the layout's change.

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
| vacuum 3 mm (built) | 8 | 15.7 | 1.515 | **18.5 W** | 105 mm | 802 mm | 1.5 kg |
| air 3 mm (as built) | 8 | 15.7 | 1.515 | 2.44 W | 105 mm | 802 mm | 1.5 kg |
| air 5 mm | 13 | 7.9 | 1.39 | 5.16 W | 249 mm | 1097 mm | 2.4 kg |
| air 6 mm | 15 | 6.2 | 1.33 | 6.29 W | 332 mm | 1267 mm | 2.8 kg |
| air 8 mm | 19 | 4.4 | 1.23 | 8.08 W | 534 mm | 1679 mm | 3.6 kg |
| air 10 mm | 23 | 3.4 | 1.15 | 5.87 W | 795 mm | 2210 mm | 4.3 kg |
| air 12 / 15 mm | 27 / 32 | 2.8 / 2.2 | 1.09 / 1.02 | never reaches its clamp | 1.1 / 1.6 m | | |

**Why κ falls.** At the opposed (minimum-C) position, a rotor vane's edge is only 4° (about 7 mm at mid-radius) from
the next stator sector. Once the axial gap is comparable, the fringe field holds C_min up.

## 3. Reshaping the sectors restores κ

The search covered 3 / 4 / 6 sectors with narrower stator and rotor widths at 6, 8 and 10 mm (54 designs). Below is
the best per gap: z ≥ 1.3, most power per millimetre.

| gap | sectors, stator / rotor width | N | κ | z | clamped power | stacks per side | tube | rotor vanes |
|:--|:--|--:|--:|--:|--:|--:|--:|--:|
| 6 mm | 6, 24° / 22° | 16 | 8.4 | 1.40 | 7.43 W | 354 mm | 1312 mm | 3.0 kg |
| 8 mm | 6, 24° / 18° | 23 | 5.8 | 1.31 | 10.2 W | 619 mm | 1850 mm | 3.5 kg |
| 10 mm | 4, 36° / 33° | 25 | 7.5 | 1.37 | 11.0 W | 841 mm | 2302 mm | 4.7 kg |

- **Fewer sectors give the best κ:** 3 sectors at 6 mm reach κ 26 and z 1.58. They also give fewer pump cycles per
  revolution and so less power. With 4 or 6 sectors, narrowing the stator widens the clearance at the minimum-C
  position.
- **Power per metre of stack, clamped:**

  | design | W per metre |
  |:--|--:|
  | vacuum (built) | 176 |
  | air, today's 3 mm stack | 23 |
  | air 6 mm, reshaped | 21 |
  | air 8 mm, reshaped | 16 |
  | air 10 mm, reshaped | 13 |

  So **in air the densest stack is today's 3 mm one**, and widening the gap only ever costs power per metre.
- **Matching the vacuum design's 18.5 W in air** needs about 0.8–0.9 m of stack per side, i.e. a 2.2–2.4 m tube.
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
- **Shaft.** A full-power stack of 0.8–0.9 m per side puts about 5–6 kg of rotor vanes on that span. A 25 mm
  shaft's first bending mode then lands near 40–60 Hz: above the 30 Hz criterion (3 × 600 rpm), but it needs a check
  with `sim/shaft_bearings.py`, a thicker shaft or a mid-stack bearing. The 354 mm option stays near 250 Hz.
- **The reluctance pump is unaffected.** It was sized in air.

## 5. What it means for the air phase

| option | gap / vanes | clamp | power (1200 rpm) | tube |
|:--|:--|:--|--:|--:|
| **A. today's stack** | 3 mm / 8 | ≈ 7 kV | 2.4 W | 0.80 m |
| B. more vanes at 3 mm (the densest) | 3 mm / 16 | ≈ 7 kV | ≈ 5.0 W | ≈ 1.0 m |
| C. reshaped 6 mm | 6 mm / 16, 24° / 22° | ≈ 13 kV | 7.4 W | 1.31 m |
| C′. reshaped 6 mm, 4 mm full-round vanes (§6) | 6 mm / 16, 22° / 22° | ≈ 13 kV | 6.7 W | 1.53 m |
| D. vacuum-equivalent power in air | 3–6 mm / 40–58 | 7–13 kV | 18.5 W | 2.2–2.4 m |

- **What the gap is for.** The choice between gap and vane count turns on what the air phase must show. The gap only
  pays if the test needs the *voltage*: e.g. dump energy ∝ V², or the stress on the 20 kV-class diodes and insulation.
- **If it needs the pump working, or its power,** more vanes at 3 mm is cheaper per watt and has no edge-corona issue.
- **Option B is scaled, not run:** twice the working gaps of A at the same geometry and V_op.

## 6. The designer's vanes: 4 mm with full-round edges

**Designer's input.** The vanes at least 4 mm thick with a rounded profile, to reduce the edge fields; asked, the
Ca / Cb plates too. Taken as 4 mm with a full round (R 2 mm) on every exposed edge, and the sector widths searched again
for those vanes.

**Method:**
- **The cell:** `sim/vane_cell.py` is `stack_sizing`'s 2-D vane cell with the edge profile as a choice. Square-cut, it
  reproduces `stack_sizing._cell` exactly. The full round keeps each sector's width at its mid-plane [IR].
- **The rim:** a plate's edge between two faces of the other node, 6 mm from its faces. That is a stator vane's inner
  rim over the rotor vanes' rings, a rotor vane's outer rim under the stator vanes' rings, and the Ca / Cb rims. It is
  solved on a 0.05 mm grid. The surface field is read with a log-law fit, which matches the exact cylinder over a plane
  within 0.3 %.
- **Stage 4:** N for C_max ≥ 1113 pF, then κ, z, the eigen and clamped power, the layout's lengths and the masses.
  **Stage 4b** repeats the width search for these vanes (41 designs).

### 6.1 Thickness costs κ; the round wins a little back

On the stage-2 winner (6 × 24° / 22° at 6 mm):

| vanes | N | C per gap, min / max | κ | z | clamped | stacks, side A | tube |
|:--|--:|--:|--:|--:|--:|--:|--:|
| 1.5 mm, square-cut | 16 | 4.51 / 38.4 pF | 8.38 | 1.402 | 7.43 W | 354 mm | 1312 mm |
| 4 mm, square-cut | 15 | 6.23 / 39.8 pF | 6.32 | 1.332 | | 444 mm | 1492 mm |
| 4 mm, full round | 15 | 5.88 / 38.7 pF | 6.51 | 1.339 | 6.30 W | 444 mm | 1492 mm |

- **Why:** at minimum C a rotor vane's capacitance is the fringe field from its edges to the next stator sectors, and a
  4 mm edge carries more of it.
- **The round** takes 6 % off C_min against a square-cut 4 mm edge, and 3 % off the aligned C.

### 6.2 The width search finds a flat optimum

On 6 sectors the eigen-cycle power per metre of stack stays within 9.2–10.4 W/m from 18° to 26°. Narrower sectors raise
κ but need more vanes for the same C_max.

| 6 sectors, stator / rotor | N | κ | z | W/m (eigen) | stacks, side A |
|:--|--:|--:|--:|--:|--:|
| 24° / 24° (the top) | 15 | 6.21 | 1.329 | 10.42 | 444 mm |
| **22° / 22° (chosen)** | **16** | **6.86** | **1.353** | **10.17** | **464 mm** |
| 24° / 22° | 15 | 6.51 | 1.339 | 10.09 | 444 mm |
| 20° / 20° | 17 | 7.33 | 1.368 | 9.69 | 484 mm |
| 18° / 18° | 19 | 7.63 | 1.379 | 9.23 | 524 mm |

- **3 or 4 sectors:** κ 12–24 and z 1.48–1.57, but fewer pump cycles per turn: at best 5.8 and 7.6 W/m.
- **The choice [IR]:** the most z within 3 % of the top, which is 22° / 22° with 16 + 16 vanes. Clamped, it gives
  6.69 W against the top's 6.47 W: its higher z more than pays for the 20 mm of extra stack.

### 6.3 The chosen stack

| | 4 mm, full round, 22° / 22° | the 1.5 mm stack (24° / 22°) |
|:--|:--|:--|
| clearance at minimum C | 8° each side, 14.0 mm at r 100 | 7°, 12.2 mm |
| vanes per varicap per side | 16 + 16, Al 4 mm, every exposed edge R2 | 16 + 16, Al 1.5 mm |
| C1 = C2 | 169–1160 pF, κ 6.86 | 142–1190 pF, κ 8.38 |
| Ca = Cb | 1276 pF: 15 plates, Al 4 mm, rims R2, 14 gaps | 1309 pF: 16 plates, 15 gaps |
| gain z | 1.353 | 1.402 |
| clamped pump at 13.1 kV, 1200 rpm | 6.69 W | 7.43 W |
| stacks, side A | 314 + 6 + 144 = 464 mm | 354 mm |
| tube (`stack_sizing.layout`) | 1532 mm | 1312 mm |
| aluminium, rotor vanes (with rings) | 10.2 kg | 3.8 kg |
| aluminium, counter-rotor | stator vanes 12.0 + Ca / Cb 20.4 kg | 4.8 + 8.1 kg |

### 6.4 What 4 mm buys: the rims clear corona

| rim | peak field at 13.1 kV | × the faces' 21.9 kV/cm | Peek onset | share of onset |
|:--|--:|--:|--:|--:|
| 1.5 mm, full round R0.75 | 63.9 kV/cm | 2.92 | 65.9 kV/cm | 0.97 |
| **4 mm, full round R2** | **38.7 kV/cm** | **1.77** | **52.3 kV/cm** | **0.74** |
| 1.5 mm, square-cut | singular | | | |

- **The worst place:** a rim between two full faces. A sector's side edge faces only part of a face.
- **§4's estimate holds:** the solved 1.5 mm rim agrees with its 63 kV/cm.
- **Stiffness [RH]:** 4 mm vanes are much stiffer, which helps flatness and pull-in at the 6 mm gap.
- **Mass [RH]:** the rotor carries 2.7× the vane mass over a 464 mm stack. Scaling §4's 250 Hz with that mass and the
  longer span (f ∝ √(1 / m L³)) puts the shaft's first bending mode near 100 Hz. That is still above the 30 Hz
  criterion, but it needs a check with `sim/shaft_bearings.py`. The counter-rotor carries 32 kg of aluminium.

## Caveats
- **[RH]:** the 1.5 margin on uniform-field air breakdown (humidity, temperature and the vane edges all move it).
- **Clamped power:** near-ideal diodes, cosine C(θ).
- **The same-power vane counts** scale the clamped power with the working gaps at fixed geometry and V_op.
- **κ at the inner and outer rims:** these edges are a fixed 2 pF floor, not part of the 2-D cell.
- **12 and 15 mm:** with today's sectors the pump didn't reach the clamp within the 24-cycle run (z 1.09 / 1.02). That
  is too little gain to count on with real losses.
- **The cell's grid (h 0.25 mm)** makes each vane two cells thinner than drawn: 0.96 mm for 1.5 mm, 3.6 mm for 4 mm.
  - At r 100, refining to h 0.0625 raises C_min per mm by 7.4 % (1.5 mm, square-cut) and 3.8 % (4 mm, round). C_max
    rises 1.5 % and 0.6 %.
  - So every κ here reads a few % high, and the 4 mm penalty of §6.1 is about 2.5 % smaller than shown.
  - The §6.2 ranking holds: 22° / 22° against 24° / 22° is 7.05 against 6.64 at h 0.0625.
- **The full round on the grid** is a staircase: at h 0.25 mm, R 1.8 mm spans about 7 cells.
- **The rim field** is 2-D, a straight rim. The arcs at r 50 and r 150 curve it slightly [RH]. Peek's law assumes
  1 atm, 20 °C and smooth surfaces [RH].
- **The masses** ignore the rounds (< 1 %).
