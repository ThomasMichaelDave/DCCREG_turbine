# S2a, step 5: the plates' thickness, the best compromise (findings)

**Sources:**
- `rebuild/s2_models/s2_thickness.py` → `s2_thickness_results.json`;
- `rebuild/s2_models/s2_modes_results.json` (the FE modes and the drive per plate, step 4);
- `rebuild/s2_models/s2_geometry.py` → `s2_geometry_results.json` (the model with the choice).

**Status: DECIDED by delegation** (2026-10-17). The designer: "Decide what the overal best compromise is when
considering priority on functional behavior and overall performance." **The choice is option C:** thicken only the
driven end plates. The designer may overrule it.

## 1. The two facts that set the choice

- **Only four plates per side carry a net pull at 120 Hz** [OC: a plate between two gaps of the same voltage is
  pulled alike both ways] (`s2_modes_results.json` `drive`):

  | plate | net pull |
  |:--|:--|
  | the column's end plates, Ca_06 and Ca_01 | 0.42 N |
  | the first rotor vane, C1_r01 | 0.54 N |
  | the last stator vane, C1_s12 | 0.54 N |

  The rest feel only the gaps' tolerance: at most 0.07 N at ±0.2 mm.
- **Thickness costs the pump's gain only in the vanes.**
  - A thicker vane's rounded rims raise C_min, and with it κ falls.
  - The Ca plates are full annuli, so their capacitance doesn't depend on their thickness; they cost only mass and
    length.

## 2. The options [IR: the 2-D cell with full-round edges, `sim/air_stack_sizing.py`; damping 1 % RH]

All figures are against A, the record. κ, z and P are the 2-D cell's, 6 + 6 vanes, 22° sectors, 6 mm air. The 3-D
stack's κ is lower (its rims), so only the differences count.

| | A: record, all 3 mm | B: all thick (step 4) | **C: end plates thick** | D: all thick, stator 4 |
|:--|:--|:--|:--|:--|
| end plates (Ca / rotor / stator), mm | 3 / 3 / 3 | 4 / 4 / 4.5 | **4 / 4 / 4.5** | 4 / 4 / 4 |
| inner plates, mm | 3 / 3 / 3 | 4 / 4 / 4.5 | **3 / 3 / 3** | 4 / 4 / 4 |
| κ (the 2-D cell) | 7.471 | 6.585 (−11.9 %) | **7.380 (−1.2 %)** | 6.715 (−10.1 %) |
| z | 1.3090 | 1.2825 | **1.3066** | 1.2868 |
| the eigen-cycle power | 1.563 W | −3.7 % | **−0.3 %** | −3.1 % |
| the rims' peak field / Peek's onset at 13.13 kV | 0.798 | 0.718–0.738 | **0.798** | 0.738 |
| aluminium, both sides | — | +4.68 kg | **+1.12 kg** | +4.11 kg |
| the stack's metal, per side | — | +21.0 mm | **+4.5 mm** | +18.0 mm |
| the driven plates clear of 120 / 240 Hz | no | yes | **yes** | yes |
| the largest deflection at 120 Hz (1 % damping) | 75.6 µm | 5.4 µm | **10.1 µm** | 8.9 µm |

- **A, the record:** its driven plates sit near 120 Hz.
  - The last stator vane (114.7 Hz, 0.54 N) swings 76 µm, and 369 µm if its mode lands exactly on 120 Hz: 6 % of the
    gap.
  - That modulates C1 / C2 at the pump's own frequency and makes the stack a sounding board.
- **B and D** clear every mode, but pay 10–12 % of κ, 3–4 % of the power, 4–5 kg and 18–21 mm a side for plates that
  carry no drive.
- **C** detunes the four plates that are driven and keeps the record's 3 mm everywhere else.
  - It keeps 99 % of κ and 99.7 % of the power, for 1.1 kg and 4.5 mm a side.
  - The rims stay at the record's 0.80 of Peek's onset, the margin the designer kept on 10-09 (ledger §3.4).

## 3. Option C's inner plates, at 3 mm, near 120 Hz

- The inner plates' modes (115–131 Hz) stay inside the ±20 % band. **Only the tolerance residual reaches them, and it
  moves them by micrometres** (`s2_thickness_results.json` `options.C.response`):

  | inner plate, 3 mm | its mode | at 120 Hz, 1 % damping | exactly on 120 Hz |
  |:--|:--|:--|:--|
  | Ca plate | 128.7 Hz | 3.3 µm | 22 µm |
  | rotor vane | 131.4 Hz | 5.3 µm | 44 µm |
  | stator vane | 114.7 Hz | 10.1 µm | 49 µm |

- **The worst case:**
  - The worst inner plate, exactly on resonance, moves 49 µm: 0.8 % of the 6 mm gap.
  - At ±0.5 mm gaps (0.18 N) it is about 125 µm, 2 % of the gap.
  - The bending stress in a 3 mm sector is about 1.5 MPa [IR: a cantilever 100 mm long, the tip's load], against
    Al 6061-T6's fatigue strength of about 95 MPa at 5 × 10⁸ cycles [RH: a handbook value]. Both are negligible.
- **The condition C rests on:** the vanes' gaps held to ±0.2 mm. That is the drive's basis, and a build tolerance
  for the bench.
- **The end plates, thickened:** 2–5 µm at 120 Hz. Even exactly on resonance it is 54–142 µm, and with the plates at
  1.40–1.45 × 120 Hz that cannot happen at 600 rpm.
- **The electrostatic negative stiffness is negligible** [OC]. At the end plate it is 2 F / g, about 490 N/m,
  against the plate's modal stiffness of 330–780 kN/m (3 to 4 mm).

## 4. In the model

- **Thicknesses:**
  - `T_CA`, `T_ROT`, `T_STA` = 3.0 mm (the inner plates);
  - `T_CA_END`, `T_ROT_END`, `T_STA_END` = 4.0 / 4.0 / 4.5 mm.
- **Each end plate is its own prototype:**
  - `ca_n2_first` (Ca_06) and `ca_n1_end` (Ca_01);
  - `rotor_vane_end` (r01) and `stator_vane_end` (s12).
- **The model:** 339 solids, 852 mm long (848 for the record, 884 for B).
  - The column sits at h 97, the vanes at h 153–258, the REF link at h 274.
  - Every gate passes: G-CLASH, G-SWEEP, G-AIR, G-POT and the nets.
  - The sleeve's G-CREEP is 73 / 67 mm against 60 mm; the couplings' is 99 against 86 mm.

## OPEN

- **S2b's field solve** on the mixed stack: C1(θ), C2(θ), Ca, and the end vanes' share of the strays.
- **Torsion through the drive** (step 4).
- **The bench:** the plates' real modes and damping, by tap test, and the gaps' tolerance as built.
