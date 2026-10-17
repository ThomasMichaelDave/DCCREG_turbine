# S2a, step 4: the plates' modes against the pump's drive, and the fix (findings)

**Sources:**
- `rebuild/s2_models/s2_modes.py` → `s2_modes_results.json`, `s2-modes-campbell.png` (`--campbell` redraws the
  chart);
- `rebuild/s2_models/s2_geometry.py` → `s2_geometry_results.json` (the model with the fix);
- `rebuild/s2_models/s2_structure.py` → `s2_structure_results.json` (the masses and the rotor's modes with the fix).

**Status:** PROPOSED (2026-10-16). **Revised by step 5 (2026-10-17, `s2-thickness-findings.md`):** only the driven
end plates are thickened (4.0 / 4.0 / 4.5 mm), and every other plate keeps the record's 3 mm. Its κ costs 1.2 %
against 11.9 % for this step's fix on every plate. The tables below stand; §3's choice applies to the end plates
only, and §4's costs are B's (step 5 has C's).

**The designer (2026-10-16):** "the 120 Hz margins, how do we move away from that frequency? extra tabs on Ca and Cb?
hyperaccelerate our way outside of that band?", then "yes, run s2_modes and bring the fixes into the model".

## 1. What drives the plates [OC: the parallel-plate pull; IR: the drive's spectrum]

- The pull on a plate is ½ ε₀ (U/g)² on each face. Its pulse follows the varicap, six times a relative revolution:
  120 Hz at 600 rpm each way. Its harmonics sit at 240 and 360 Hz.
- **A plate between two like gaps feels no net pull.** Only the stack's end plates are driven, each by about 0.4–0.5 N
  (`s2_modes_results.json` `drive`):

  | part | net | net pull |
  |:--|:--|:--|
  | Ca_06, Ca_01 (the Ca column's end plates) | 2 / 1 | 0.42 N |
  | C1_r01 (the first rotor vane), C1_s12 (the last stator vane) | 1 / REF | 0.54 N |

  - Every inner plate is driven only by the gaps' tolerance: ±0.2 mm (`delta_m`) leaves at most 0.07 N.
  - The check is still made for every plate type, since the tolerance residual reaches them all.

## 2. The plates' modes (Gmsh → CalculiX, each part held at its real seats) [IR: the FE]

- A uniform pull excites only the modes with a real effective mass in z (a share ≥ 5 %).
- The pull-excited modes, in Hz, against the plate thickness (`s2_modes_results.json` `fe`):

  | part | 3 mm | 4 mm | 4.5 mm | 5 mm | 6 mm |
  |:--|:--|:--|:--|:--|:--|
  | Ca plate (three tabs) | 128.7 | **170.0** | 193.7 | 214.5 | 256.6 |
  | rotor vane (its hub ring) | 131.4 | **174.1** | 196.5 | 217.8 | 260.5 |
  | stator vane (six lugs) | 114.7 | 150.1 | **167.7** | 184.7 | 217.3 |

  The frequency rises about linearly with the thickness, as a plate's should.
- **The hand estimates in `s2-structure-findings.md` are superseded:**
  - the rotor sectors were estimated at 141 Hz (FE: 131 Hz at 3 mm);
  - the stator sectors at 424 Hz (FE: 115 Hz at 3 mm);
  - the stator vane is held at its six lugs, not round its rim, which the hand estimate assumed.

## 3. The fix: thicker plates, not a faster machine

- **The rule** [IR]: no pull-excited mode within ±20 % of the 1× drive, or ±10 % of the 2×.
- **Before** (all 3 mm): the clear speeds are 365–455 and 790–900 rpm. **600 rpm is not clear;** the stator vane at
  115 Hz sits 4 % under 120 Hz.
- **The proposed thicknesses:**
  - Ca / Cb plates **4.0 mm**;
  - rotor vanes **4.0 mm**;
  - stator vanes **4.5 mm**.

  Their modes sit at 168–174 Hz: 40–45 % above the 1×, and 27–30 % below the 2× (240 Hz).
- **After:** the clear speeds are 300–375 and **480–670 rpm. 600 rpm is clear,** with 80 rpm to spare below and 70
  above (`campbell.after`).
- **The other options:**
  - **A faster machine** ("hyperaccelerate"): above the band means 790 rpm or more for 3 mm plates (`campbell.before`), and the relative
    speed, the pump frequency and every loss rise with it. It is the designer's speed, not the plates', so it is not
    used.
  - **More tabs on Ca / Cb:** they stiffen the Ca plates only. The stator vane is the lowest mode, and the rotor vane is
    held round its hub, so more tabs alone would not clear 600 rpm.
- **The non-uniform modes** (nodal diameters) are not excited by a uniform pull, only by the tolerance residual:
  - the Ca plate at 4 mm has a pair at 140 / 142 Hz, 17–18 % above 120 Hz;
  - at that residual pull (≤ 0.07 N) this is a margin to watch, not a failure [IR].

## 4. What the fix costs

- **The mass:** the rotor 15.0 → 18.2 kg, the counter-rotor 23.6 → 25.8 kg (`s2_structure_results.json`
  `masses_kg`). G2.5 at 600 rpm then allows about 725 g·mm on the rotor (552 before), so V1b's 41 g·mm per deck stays
  far inside.
- **The bearings:** 435 N axial on the lower frame bearing (382 before), 7 N out of balance; a 6205's C0 is 7.8 kN.
- **The spin stresses** don't depend on the thickness: still safety × 284 or more.
- **The model:** 884 mm long (848 before). The column sits at h 97, the vanes at h 157–274, the REF link at h 290.
  Every gate passes (G-CLASH, G-SWEEP, G-AIR, G-POT, the net check):
  - the sleeve's G-CREEP: 77 / 66.5 mm against 60 mm;
  - the couplings' G-CREEP: 99 against 86 mm.
- **The electrostatics:** the vanes' 3 mm, with full rounds R1.5, is a record value (ledger §3, "the stack of
  record"). Thicker vanes with fuller rounds lower the rims' field. They also shift C1 / C2 and the stack's κ. **S2b's
  field solve settles C1(θ), C2(θ) and Ca on the thicker plates;** until then S1b's values are from the 3 mm stack.

## 5. The rotor's bending: not excited by the pump

- With step 5's end plates, the beam model gives **35.6, 97.3 and 195.0 Hz** (`s2_structure_results.json` `rotor_modes`; 36.7 /
  99.1 / 198 before).
- **The pump doesn't excite them** [OC]: the six sectors' pulls are axial, and their lateral parts cancel round the
  axis. Only the 1× out-of-balance at 10 Hz drives the bending, 3.6 × under the first mode.
- **This corrects** `s2-structure-findings.md`'s flag "the second, 99 Hz, is 17 % under the pump's 120 Hz": no change
  is needed for it.
- A wider coupling would stiffen the shaft (99 → 108 Hz from od 34 to 60 mm, before the fix; `rotor_vs_coupling_od`),
  but it isn't needed.

## OPEN

- **The thicknesses, 4.0 / 4.0 / 4.5 mm:** the designer's decision, and S2b's field solve on them.
- **Torsion:** the pump's torque pulses at 120 Hz, and the torsional modes run through the 1 : −1 drive. That is not
  modelled until the drive is drawn.
- **The Ca plates' nodal-diameter pair at 140 Hz:** to watch, and to re-check with the plates' real tolerance.
