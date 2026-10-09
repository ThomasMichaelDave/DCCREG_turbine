# Rotating mechanics: centrifugal loads, the magnetic pull, the 0.5 mm gap, windage and balancing — findings

**Source:** `sim/rotor_mechanics.py` → `sim/rotor_mechanics_results.json` (`python3 sim/rotor_mechanics.py`, under a
minute; numpy / scipy).

**Scope.** The locked machine (`docs/ledger/DCCREG-design-ledger.md`): rotor +600 rpm, counter-rotor −600 rpm,
1200 rpm relative, the axis vertical, side A below. Loads at 600 rpm and at a 1.25 × overspeed, 750 rpm [IR].

**Inputs** (read from the record; nothing guessed):

| input | value | source |
|:--|:--|:--|
| utron (as built) | 3 per side, r 57–130, tips 14 × 100 mm, slot 30 × 30, 200 turns; SiFe 0.89, NiFe 0.15, Cu 1.07, G10 0.12 kg | `sim/utron_profile.py` `spec` of the pick in `sim/pole_design_variants_op.json` |
| utron fastening | 4 A4 M6 studs in Ø6.4 holes through the half-cores and 10 mm G10 cheeks; cheeks bolted to two 12 mm G10 carrier discs (r 20.5–57) | `sim/utron_profile.py` docstring; `sim/pole-design-findings.md` §8 |
| bridges | 6 per side, M235-35A, r 130.5–144.5, 25.5°, 0.65 kg; G10 ring r 131.5–156.5, z 20–194 (A) | `sim/utron_profile.py`; the layout below |
| gap | 0.500 mm aligned, 9.74 mm unaligned; tip faces ground on the assembled rotor, profile 0.04 | `sim/tube_geometry_wound_results.json`; `sim/pole-design-findings.md` §8 |
| clamp flux | Ψs 0.1336 Wb-turns per group of 3 × 200 turns → 0.223 mWb per utron; 0.159 T over a tip | `sim/pole_design_variants_op.json` (`psi_s`, `N_u`, `B_body_T`) |
| vane stacks | 6 + 6 Al 3 mm, 22° sectors, r 50–150, 11 gaps of 6 mm; Ca / Cb 6 plates, 5 gaps, on the rotor; Al rotor vanes 2.87, Ca / Cb 6.11, stator vanes 3.38 kg | `sim/air_stack_sizing_results.json` (`thick_vanes.compare`); `sim/air_stack_sizing.py` `masses`; `sim/core-field-findings.md` §7 |
| layout | 940 mm: end bearings z 10 / 930 (frame), Ca\|rel 198 / 742, hub faces 380 / 560 (inner); stacks A z 51–151, B 789–889 | `sim/stack_sizing.layout` with the stack above and the hub's flanges at \|z\| 72–80 (`presets/hub-locked.json`) |
| shaft, bearings | Ø25 (tube) or Ø30 (register), OPEN; 6205-class, G10 spiders 8 mm | `sim/stack_sizing.py` lines 60–61; `presets/hub-locked.json` |
| hub | 50 mm borosilicate, 1.5 mm wall; PEEK r ≤ 30, \|z\| ≤ 72; gel 0.5 mm; G10 coupler r 30–33 | `presets/hub-locked.json` |
| coil temperature | 46 °C in air, at the model's 40 °C ambient | `sim/pole_design_variants_op.json` (`T_coil_air_C`); `sim/pole_design.py` line 125 (`T_AMB` 313 K) |
| belt power | magnetic 18.13 + iron 1.25 + electrostatic 2.14 = 21.5 W | `sim/ah_steady_cusp_results.json` (22 mF); `sim/pole_design_variants_op.json`; `sim/core_field_results.json` |

## Headline

1. **No banding is needed** [OC: the stresses; IR: the strengths]. At 750 rpm every part keeps a safety factor of 19 or
   more on datasheet strengths. A band over the utrons' tips would have to sit in the 0.5 mm gap (over the end turns,
   2.7 mm from the ring, it would not hold the stack); the bridge ring holds its bridges from outside. What carries the
   gap instead is **the stack's clamp and the joints' fit**: without the stud preload or the bond, the M6 studs bend
   0.80 mm at 600 rpm. So: preload the studs, fit or dowel the holes, bond in the impregnation, and spin to 750 rpm
   before the OP 50 grind (§2).
2. **Windage ≈ 12 W (8–25 W), and the bearings' friction ≈ 5 W (3–14 W)** at 600 rpm each way in air [IR: the
   correlations; RH: their coefficients]. That is **≈ 17 W of mechanical loss against the pumps' 21.5 W**, so the belt
   delivers about 39 W, not 21 W (§6).
3. **The gap** [OC: the statics; IR: the stack-up, the bearing classes and the seats]:
   - Only the four inner bearings move the utrons against the bridges; the frame bearings do not. The reluctance
     sections overhang the Ca|rel bearings, so a Ca|rel bearing's eccentricity reaches the gap × 2.0 (its hub-face
     bearing's × 1.2).
   - **Minimum running gap** at 750 rpm, hot, with a 100 N belt pull, as laid out (six bearings): **0.33 mm worst case,
     0.40 mm statistical**, with P6 bearings under an axial spring preload and 5 / 10 µm seats. With P0 bearings and
     normal clearance it is 0.26 / 0.36 mm. With the 8-bearing option of `sim/tube-shaft-findings.md` §0 it is
     0.39 / 0.44 mm.
   - **Runout spec, replacing "≤ 0.05 mm on the four inner bearings":** the all-in TIR per inner bearing (the bearing's
     K_ia + K_ea, the journal's and housing's runout to the grind / bore datums, any play) **≤ 0.027 mm as laid out**
     (P5 class + preload), or **≤ 0.05 mm with the 8-bearing option** (P6 + preload is 0.036 mm). Either keeps the
     eccentricity at the gap ≤ 10 % of g, worst case. No rub (gap ≥ 0.25 mm) needs only ≤ 0.08 mm (§5).
4. **Balance grade G2.5** [IR: the grade; OC: ISO 21940-11's definitions] per body, two planes, after assembly:
   U_per 1.31 kg·mm for the rotor (32.9 kg) and 1.33 kg·mm for the counter-rotor (33.4 kg), 0.66 kg·mm per plane, a
   40 µm offset of the mass centre. G6.3 (100 µm) is the in-service limit (§7).
5. **The magnetic pull is small** [OC: Maxwell stress; IR: the clamp law per utron]:
   - 28 N per utron at the clamp, 42 N at the clamp law's peak. Its negative stiffness, 0.05 MN/m per side (≤ 0.17 MN/m
     bound), is 2–7 % of the bodies' relative stiffness at the stack, so it amplifies the eccentricity × 1.02–1.06 (§3).
   - The bridges need bonding: below about 170 rpm with flux on, the pull exceeds their centrifugal force.

## 1. The bodies and what was counted

**Rotor, 32.9 kg** (Ø25 shaft; 34.3 kg at Ø30):
- 6 utrons, 13.37 kg;
- Ca / Cb plates 6.11 kg; rotor vanes 2.87 kg;
- shaft halves 3.04 kg, flanges 0.41 kg; G10 sleeve 1.01 kg; carrier discs 0.79 kg;
- the hub 0.72 kg (vessel 0.025, AH cores 0.048, AH coils 0.085, PEEK 0.40, gel 0.004, coupler 0.16);
- six bearing inner rings 0.27 kg;
- La / Lb first cut 2.82 kg (`sim/rotor-parts-duty-findings.md` §1) [RH]. The bobbin-wound EI-84 × 35 of
  `sim/parts-first-cut-findings.md` §1 is 3.3 kg for the pair (2026-10-09): the rotor 0.5 kg (1.5 %) heavier, which
  moves no result here by more than that;
- 1.5 kg for the clamps, D1–D4, the CW chains, D1*–D4*, the snubbers, the bypass, wiring and potting [RH, not designed].

**Counter-rotor, 33.4 kg:**
- bridge rings 12.79 kg (G10, 25 mm wall, 174 mm long, minus the pockets) — the heaviest item;
- bridges 7.85 kg; cage 4.30 kg (r 162–166, z 188–752); stator vanes 3.38 kg;
- four inner spiders 4.76 kg (full 8 mm plates r 26–162 [IR]); the inner bearings' outer parts 0.33 kg.

**The utron's centre of mass** is at **r 97.9 mm** (SiFe at 106.7, Cu at 93.0, NiFe at 87.5, cheeks at 84.4 mm) [OC].
- Its mass is 2.228 kg against the record's 2.233: the 0.2 % is the cheeks' stud holes.
- The bridge's centre of mass is at r 136.5 mm.

**Polar inertia** [IR: the main parts]: rotor 0.24 kg·m², counter-rotor 0.65 kg·m². That stores 0.47 + 1.28 kJ at
600 rpm and 2.7 kJ at 750.

## 2. Centrifugal loads and banding

### 2.1 The utron's retention

**The load per utron:**

| | 600 rpm | 750 rpm |
|:--|--:|--:|
| acceleration at the tips (r 130) | 52 g | 82 g |
| utron, m ω² r_cm | **861 N** | **1346 N** |
| + magnetic pull at the clamp (§3) | 28 N (42 at the peak) | same |
| on the 4 studs (all but the cheeks) | 834 N, 209 N per stud | 1304 N, 326 N per stud |
| per cheek (4 per utron) | 215 N | 336 N |

The record's 0.86 kN (`sim/pole-design-findings.md` §8) is confirmed.

**The load path:** the coil bears on the strip, the strip on the half-cores, the half-cores on the studs, the studs on
the cheeks, and the cheek roots (r 43–57) on the carrier discs [IR: the record's §8 arrangement].
- **The cheek-to-disc fastening is not in the record.** Assumed: one A4-70 M5 per cheek root, through the 14 mm lap,
  in a reamed hole, preloaded to 3.5 kN [IR].
- **The stud preload is not in the record.** Assumed: 5 kN per M6, 55 % of the A4-70 proof load [IR].

**Two ways the stack can carry its load:**
- **(A) As a bonded, preloaded beam between the cheeks.**
  - Bending normal to the laminations: 1.49 MPa at 600 rpm, 2.33 MPa at 750 (section 581 mm², I 81 500 mm⁴).
  - The two studs of a half-core prestress it to 17.2 MPa, so it never decompresses: × 7.4 at 750 rpm.
  - The studs carry only shear at the stack's end faces (9 MPa at 750 rpm), and friction holds those faces × 6.1.
- **(B) No credit for the bond or the preload: the studs carry the stack as 110 mm beams.**
  - 293 MPa and **0.80 mm** of bow at 600 rpm; 458 MPa (yield, × 1.0) and 1.25 mm at 750.
  - Either deflection is more than the gap [OC: beam theory].
- **So the preload and the bond are load-bearing for the gap,** not just for strength.

**The clearance holes are the other risk.** Ø6.4 holes on M6 studs, and a friction-only cheek root (× 2.1 at 750 rpm,
less as G10 creeps), could let a utron step outward by 0.2–0.4 mm. The budget in §5 excludes that slip, so it has to be
designed out:
- fitted (reamed H7) holes, or one dowel per cheek, at the stack and at the root;
- bond the cheeks and roots in the vacuum impregnation;
- disc springs on steel washer plates under the nuts, to hold the preload through G10 creep;
- spin the rotor at 750 rpm, then grind the tips (OP 50).

### 2.2 The coil

- **The coil carries itself** [OC: beam estimate]. It is a closed loop on the back iron: 394 N at 600 rpm, 0.14 MPa on
  the former, about 0.2 MPa in its end turns.
- **The impregnation is load-bearing.** The slot side bows 0.7 µm as an impregnated bundle, but **0.30 mm as loose
  wires** (0.47 mm at 750 rpm). The clearance to the slot cover is 0.1 mm. The record's "≈ 0.001 mm"
  (`sim/pole-design-findings.md` §8) holds only if the VPI bonds the bundle [RH: the bundle's stiffness].

### 2.3 The carrier discs

Each 12 mm disc carries the three utrons' half-loads at r ≈ 50 [OC: a thin ring under 3 radial loads, Lamé].
- **Ring tension + bending + its own rotation:** 1.8 MPa at 600 rpm, 2.8 MPa at 750 (× 90).
- **The weak spot is the rim:** the root bolt sits 7 mm from the disc's edge. Shear-out is 3.1 MPa at 750 rpm, × 19 on
  60 MPa [IR].
- **A longer lap** (the cheek root down to r 35) would give the root two bolts and edge distances of 3 bolt diameters,
  as composite joints prefer [IR].

### 2.4 The bridges and their ring

- **Each bridge presses on its pocket floor:** 353 N at 600 rpm (551 N at 750), 0.05 MPa.
- **The ring:** a 0.28 MPa hoop (smeared over the 12 × 100 mm band behind the pockets) + 1.97 MPa of bending between the
  six bridges + 0.17 MPa of its own rotation = **2.4 MPa** (3.8 at 750 rpm, × 66) [OC: thin ring, 6 loads].
- **It needs no band.** The bridges push outward into the ring, and the ring's growth opens the gap by 11 µm
  (no credit taken in §5).
- **The magnetic pull pulls each bridge inward,** 28 N (42 N peak). Below **170 rpm** (with flux on) it exceeds the
  bridge's centrifugal force. So bond or key the bridges in their pockets; don't rely on seating.

### 2.5 The vanes, the Ca / Cb plates and the cage

| part | 600 rpm | 750 rpm | × at 750 |
|:--|--:|--:|--:|
| rotor vane sector root (r 50, tension) / inner ring at the bore | 0.23 / 0.23 MPa | 0.36 / 0.35 MPa | 670 |
| stator vane outer ring (r 150–162), 6 sector loads + own | 0.63 MPa | 0.98 MPa | **245** |
| Ca / Cb plate, free annulus, hoop at the bore | 0.20 MPa | 0.32 MPa | 750 |
| G10 cage r 162–166, own + the stator rings' push | 0.33 MPa | 0.51 MPa | 490 |

[OC: Lamé and thin ring; IR: Al 6061-T6 240 MPa, G10 250 MPa.]

- **The Al rings and the cage differ in expansion** (23 against 13 ppm/K): the rings tighten by 0.03 mm in the cage per
  +20 K and loosen as much per −20 K. Key or bond them axially and radially [IR].

### 2.6 The hub

- **Rotation adds almost nothing:** the glass 5.5 kPa, the PEEK 2 kPa, the coupler 7 kPa. The vacuum's 0.8 MPa
  (`presets/hub-locked.json`) dominates the glass by 150 × [OC].
- **The gel keeps the sphere centred** [OC: incompressible layer]. A sphere 0.1 mm off-centre feels 0.01 N, against the
  stiffness of a confined, near-incompressible 0.5 mm layer.
- **The hub's axial load.** With the bottom bearing locating, the hub carries the B half of the rotor (about 160 N): 0.27
  MPa in the G10 coupler. Keep the glass and the retainer out of that path; the flanges bolt to the coupler [IR].

### 2.7 Verdict

**No band, anywhere.** The lowest factors at 750 rpm are:
- the disc rim's shear-out (19) and the M5 root bolt (25), both on the assumed fastening;
- the friction and bond items (2.1–7.4), which §2.1 turns into fitted, bonded, preloaded joints.

The record's "so the coils need banding or a retaining ring" (`sim/pole-design-findings.md` line 195, §6) predates the
§8 stud-and-cheek build, and is superseded.

## 3. The magnetic pull

**The force** [OC: Maxwell stress, fringing ignored — an upper bound].
- At the clamp, 0.223 mWb crosses each 14 × 100 mm tip face, **0.159 T**. That is the record's `B_body_T`.
- So 14.1 N per face, **28.2 N per utron**, pulling the utron outward and the bridge inward.
  - **2026-10-09** (`sim/neck-nonlinear-findings.md`, notes against the record): with the field map's neck law the aligned
    flux reaches about 0.232 mWb, so about 31 N per utron.
- The record's law i = Ψ/L (1 + (Ψ/Ψs)⁶) at the branch's 2.81 A peak gives Ψ = 1.21 Ψs, i.e. 41.5 N. That is a bound:
  aligned, the branch current is near its minimum.

**The unbalanced pull** (per side; all three utrons align at once, A at rotor angle 0, B at 30°):
- Three poles in series at constant current, linear iron: k = 3F/g = **0.17 MN/m** [OC].
- With the clamp law applied per utron, the flux barely follows the gap. k falls by 1 + 6x⁶/(1 + x⁶): **0.05 MN/m** at
  most (0.04 at Ψs) [IR].
- At the peak flux, linear (the extreme): 0.25 MN/m.
- It pulses at the 120 Hz pump frequency, A and B in antiphase.

**What it does** (two-body model, §4):
- The bodies' relative stiffness at the stack is 2.5 MN/m as laid out (Ø25), 4.5 at Ø30, and 45 MN/m with the 8-bearing
  option.
- So k_mag / k_rel is 0.02 / 0.07 / 0.10 (clamp / bound / extreme). The eccentricity is amplified × 1.02 / 1.06 / 1.10.
  f1 drops from 27.3 to 26.3 Hz at the extreme, and every case stays stable.
- At the worst-case eccentricity of §5 (66 µm), the pull is **3–11 N per side**: negligible beside the 100 N bearing
  preload. The record's 2e5 N/m (`sim/tube-shaft-findings.md` §0) sits inside this range.

## 4. The shaft and the counter-rotor as two bodies

**The model** [OC law / IR inputs].
- The shaft (with the hub's G10 coupler, EI 5.3 kN·m²) and the counter-rotor (cage, bridge rings) are Euler–Bernoulli
  beams.
- The counter-rotor **floats on the four inner bearings**, and only the two end bearings meet the frame (rigid).
- The bearings are 6205s under a 100 N axial spring preload, 1.2e8 N/m by Hertz (Palmgren's ball deflection, 9 balls of
  7.94 mm, α 10°). They sit in series with a G10 spider of 3e8 N/m [RH], so 0.86e8 N/m.
- The mesh converges: 10 and 5 mm grids agree to 0.05 %.

| case | f1 / f2 (Hz) | k_rel at the stack | gap change under 1 g lateral: centre / outer end of the stack |
|:--|--:|--:|--:|
| **as laid out, Ø25** | **27 / 46** | 2.5 MN/m | **147 / 251 µm** |
| as laid out, Ø30 | 37 / 63 | 4.5 MN/m | 80 / 133 µm |
| Ø30, the reluctance spans Ø40 | 44 / 75 | 5.6 MN/m | 65 / 100 µm |
| Ø25, Ti-6Al-4V shaft | 21 / 36 | 1.6 MN/m | 236 / 408 µm |
| Ø25, the hub as a hinge | 27 / 46 | 2.4 MN/m | 153 / 262 µm |
| **8 bearings (+ one at each bridge ring's outer end), Ø25** | **131 / 205** | 45 MN/m | 2 / 2 µm |
| 8 bearings, Ø30 | 138 / 228 | 71 MN/m | 0.5 / 2 µm |
| the drive proposal: a gear-end bearing on side A only | 34 / 97 | 31 MN/m (A) | A 15 µm, B 163 / 279 µm |
| cross-check, 6 bearings, the record's 2e8 N/m and 210 GPa steel | 29 / 49 | 2.9 MN/m | 128 / 222 µm |
| cross-check, 8 bearings, the record's 2e8 N/m and 210 GPa steel | 163 / 253 | 59 MN/m | 3 / 3 µm |
| the earlier model on this build (all six bearings to ground) | 329 / 331 | 41 MN/m | 2 / 2 µm |

- **An independent check of `sim/tube-shaft-findings.md` §0.** With that file's parameters this model gives 29 / 49 Hz
  and 128 µm (§0: 29 / 46 Hz, 123 µm), and 163 Hz / 3 µm with 8 bearings (§0: 165 Hz, 3 µm).
- **The earlier grounded model is wrong for this machine.** It gives 329 Hz and 2 µm on the same build, because it
  stands the counter-rotor on the frame.
- **The gap tilts along the stack.** Its outer end moves 1.7 × the centre, so §5 uses the worst point.
- **The axis is vertical,** so 1 g lateral is a stiffness yardstick and a handling case, not an operating load.
  - Plumbed within 0.5°, the gap moves ≈ 2 µm.
  - **Transported or tested horizontally,** the gap loses 0.15–0.25 mm, and shocks close it. Transport vertical, or with
    shims in the gaps [IR].
- **The 8-bearing option's f1 depends on the bearing seats' stiffness.** It is 163 Hz at 2e8 N/m, but 131 Hz with a
  preloaded 6205 in a G10 spider: 9 % above the pumps' 120 Hz. Detune it (stiff metal cartridges in the spiders) and
  check it with a tap test on the build [IR].
  - At z end + 18, where §0 models it, the bearing's spider would cut through the utrons' end turns (z 23–51 on side A).
    The layout needs 10–20 mm more per side for it.
- **The drive proposal's gear-end bearing** (`docs/drive-gear-belt.md`, untracked at the time of writing) straddles
  side A only. Side B keeps the as-laid-out sensitivity until the top bearing of the pair is added.

## 5. The 0.5 mm gap budget

### 5.1 How the bearings' runout reaches the gap

**The influence of a unit eccentricity at each bearing** on the relative displacement at the worse end of the nearer
stack [OC: the beam model's statics]:

| bearing | as laid out (Ø25) | as laid out (Ø30) | 8 bearings (Ø25) |
|:--|--:|--:|--:|
| frame bearings (both) | **0.00** | 0.00 | 0.00 |
| Ca\|rel, this side | **1.99** | 1.91 | 0.86 |
| hub face, this side | 1.20 | 1.02 | 0.10 |
| hub face, far side | 0.22 | 0.12 | 0.01 |
| Ca\|rel, far side | 0.02 | 0.01 | 0.00 |
| ring end, this side | — | — | 0.83 |
| **sum (worst case) / RSS** | **3.43 / 2.34** | 3.06 / 2.17 | 1.79 / 1.19 |

- **The frame bearings only place the assembly in the frame** (two supports: statically determinate). Their runout
  moves both bodies together, so P0 is enough there.
- **The counter-rotor tilts about its hub-face bearing.** The bridges hang 50–150 mm beyond the Ca|rel bearing, so a
  Ca|rel bearing's eccentricity is levered × 2.0 into the gap.

### 5.2 The terms (750 rpm, hot, at the worst utron)

| term | as laid out (Ø25) | 8 bearings (Ø25) | basis |
|:--|--:|--:|:--|
| tip-face profile (0.04 zone after OP 50) | 20 µm | 20 µm | `sim/pole-design-findings.md` §8 |
| bridge-face profile (proposed: bored in place, 0.04 zone) | 20 µm | 20 µm | [IR] |
| centrifugal growth of the tips: cheek 7.1, joints 3.7, disc 0.7 µm (600 rpm: 7.4) | 11.6 µm | 11.6 µm | [OC]; bridge-ring growth +18 µm opening, not credited |
| the magnetic pull on the retention | 0.4 µm | 0.4 µm | [OC] |
| thermal, worst (nominal 10.7; self-heating alone 5.5) | 26.9 µm | 26.9 µm | [IR] below |
| a 100 N belt pull, pulley 50 mm outboard of the frame bearing | 21.6 µm | 2.0 µm | [RH] the drive is not designed |
| unbalance whirl at G2.5 (× the dynamic factor) | 3.4 µm | 0.1 µm | [IR] |
| **subtotal (deterministic)** | **104 µm** | **81 µm** | |
| eccentricity: the sum (or RSS) of the influences × the per-bearing eccentricity × the magnetic amplification | below | below | §5.1, §3 |

**Thermal** [IR: a radial chain model]:
- The tips are ground at 20 °C and run at the record's 40 °C ambient, with the coils at 46 °C (the core +6 K, the cheek
  +4, the disc +2).
- The tip circle grows 47 µm and the bridge faces 36 µm: shaft, bearing, spider and ring on one side; shaft, sleeve,
  disc, cheek and core on the other. The net closing is 10.7 µm.
- **Worst case, 26.9 µm:** G10 in-plane 16 ppm/K on the rotor and 10 on the counter-rotor, and the sleeve +10 ppm/K
  through its thickness.
- **Cut the same G10 grade and lot** for the carrier discs, cheeks, spiders and bridge rings, and the worst case falls
  toward the nominal.

**Per-bearing eccentricity** = (K_ia + K_ea + journal TIR + housing TIR + radial play) / 2.
- ISO 492 values for the 6205 (bore 18–30 mm, outside diameter 50–80 mm) [IR]:

  | class | K_ia | K_ea |
  |:--|--:|--:|
  | P0 | 13 µm | 25 µm |
  | P6 | 8 µm | 13 µm |
  | P5 | 4 µm | 8 µm |
  | P4 | 3 µm | 5 µm |

- Radial internal clearance, CN: 5–20 µm. Seats proposed at 5 µm (journal) and 10 µm (housing) [IR].
- **The vertical axis loads the radial bearings with nothing,** so their play is free play. An axial spring preload
  (≈ 100 N) removes it [OC]; the locating bearings carry the weight (below).

### 5.3 The minimum running gap (750 rpm, hot; worst case / RSS)

| inner bearings | all-in TIR each | as laid out Ø25 | as laid out Ø30 | 8 bearings Ø25 |
|:--|--:|--:|--:|--:|
| P0, CN clearance, no preload | 73 µm | 0.26 / 0.36 mm (ecc. 27 %) | 0.29 / 0.38 | 0.35 / 0.42 |
| P0, axial spring preload | 53 µm | 0.30 / 0.38 (19 %) | 0.32 / 0.40 | 0.37 / 0.43 |
| **P6, axial spring preload** | **36 µm** | **0.33 / 0.40 (13 %)** | 0.35 / 0.42 | **0.39 / 0.44 (6 %)** |
| P5, axial spring preload | 27 µm | 0.35 / 0.41 (10 %) | 0.37 / 0.42 | 0.40 / 0.44 |

- The percentages are the worst-case eccentricity over g.
- At 600 rpm every entry is 4–5 µm larger.
- **No case rubs.** Even P0 bearings with free play keep 0.26 mm, worst case, at the overspeed.
- **The excluded terms are designed out (§2.1):** joint slip in the clearance holes (up to 0.2–0.4 mm) and the loose-coil
  bow (0.3 mm).

### 5.4 The runout allowed per inner bearing

The allowed all-in TIR per inner bearing, all four alike:

| criterion | as laid out Ø25 | as laid out Ø30 | 8 bearings Ø25 |
|:--|--:|--:|--:|
| no rub: g_min ≥ 0.25 mm (half the gap), worst case, 750 rpm [IR] | 80 µm | 100 µm | 188 µm |
| eccentricity ≤ 10 % of g, worst case [RH: a common air-gap rule] | **27 µm** | 31 µm | **56 µm** |
| eccentricity ≤ 10 % of g, RSS | 42 µm | 46 µm | 84 µm |

**The record's provisional "hold ≤ 0.05 mm runout on the four inner bearings"** (ledger line 601;
`sim/pole-design-findings.md` line 397) is right in size but needs a definition and a layout:
- **As laid out**, 0.05 mm all-in TIR is safe from rubbing, but it gives 91 µm of worst-case eccentricity (18 % of g).
  The spec should be **≤ 0.027 mm all-in**: P5 bearings, axial spring preload, journals ≤ 5 µm and housings ≤ 10 µm TIR
  to the datums.
  - The Ca|rel bearings weigh twice the hub faces, so spend the precision there: P5 at Ca|rel and P6 at the hub faces
    gives 56 µm (11 %).
- **With the 8-bearing option**, the record's 0.05 mm holds, and P6 + preload (36 µm) gives 32 µm (6 %).

**How to get there** [IR]:
- Grind the journals and the tip faces in one setup (the tips' datum).
- Bore the bridge faces and the four inner housings of the counter-rotor in one setup (the bridges' datum).
- Use metal bearing cartridges in the G10 spiders.
- Accept on the assembled machine: the relative runout between the tip circle and the bridge bore at each stack, and the
  cold gap at every utron and bridge ≥ 0.45 mm.

**The bearings' loads and lives** (vertical axis; the bottom frame bearing locates both bodies, and the Ca|rel A
bearing the counter-rotor) [IR: ISO 281 form, ratings 14.8 kN dynamic, 7.8 kN static]:
- bottom frame bearing: axial 650 N at 600 rpm, L10 92 000 h;
- Ca|rel A: 328 N at 1200 rpm relative, 210 000 h;
- the floating ones on the 100 N preload: > 3 × 10⁶ h.

**Under 1 g lateral (handling)** the inner bearings take up to 570 N, far inside the 7.8 kN static rating. Let one
inner bearing locate the counter-rotor axially and the others float [OC]: stainless shaft against the G10 cage is 28 µm
of difference per 470 mm and 20 K.

## 6. Windage and bearing friction

**At 600 rpm each way in air (20 °C, 1013 hPa).** The internal shear runs at the relative speed, 1200 rpm.

| component | nominal | range | model [IR correlation / RH coefficient] |
|:--|--:|--:|:--|
| vane stacks, faces (22 counter-rotating gaps of 6 mm) | 1.73 W | 1.7–6.6 | Daily & Nece regime III (Re 1.9e5, G 0.04, c_M 0.0066) at the relative speed; × 0.72 for counter-rotation, × 0.37 metal coverage (full discs: high) |
| vane stacks, the 144 sectors' 3 mm edges | 3.23 W | 0.8–6.5 | form drag, c_D 0.4 (0.1–0.8) on the edge pair at ω r |
| Ca / Cb stacks: the outer plate against the Ca\|rel spider (12 mm), 2 | 0.45 W | 0.45–0.63 | Daily & Nece regime IV |
| Ca / Cb stacks: the rims against the cage (12 mm), 2 | 0.88 W | 0.6–2.0 | Bilgen & Boulos Taylor–Couette (Re_δ 1.5e4); grooves × 1.5 (1–2.5) |
| reluctance sections: 3 salient utrons in the bridge ring, 2 | 3.17 W | 2.4–6.0 | a paddle model: 3 bluff utrons (c_D 2) drive the section's air to 0.71 ω against the ring bore (c_f 0.005) and the end walls. Cross-check: Taylor–Couette at the mean 1.08 mm gap gives 2.4 W smooth |
| the counter-rotor's outside in still air (cage r 166 × 564, rings r 156.5 × 2 × 174) | 2.61 W | 1.8–3.4 | Theodorsen & Regier (Re 1.15e5, c_f 0.0043) |
| bridge-ring ends, hub coupler, carrier discs | 0.08 W | | Daily & Nece; the free cylinder |
| **windage** | **12.1 W** | **7.9–25.1** | |
| bearing friction (4 inner at 1200 rpm relative, 2 frame at 600) | 5.1 W | 3.2–14.2 | Palmgren M0 (f0 1, ν 30 mm²/s; 0.75–2, 15–70) + the load term with the thrust on the locating bearings |
| **mechanical, total** | **17.3 W** | **11–39** | |
| the pumps (magnetic 18.13 + iron 1.25 + electrostatic 2.14) | 21.5 W | | records |

- **The belt therefore delivers ≈ 39 W** (32–61 W), not the ledger's "about 21 W" (line 24). A coast-down from 600 rpm,
  with the pumps unloaded, reads the mechanical loss directly: about 3 rpm/s at the start
  (the loss = (I_r + I_c) ω |dω/dt|) [OC].
- **The vane stacks are the largest item,** and of them the sector edges. Fuller edge profiles would trade against
  C_min [RH].
- **The windage scales with the air density.** It vanishes in vacuum, and rises about as ω^2.8: × 1.9 at 750 rpm.
- **The drive proposal's 25 W allowance** (`docs/drive-gear-belt.md` §4.1, untracked) sits at the top of this range. Its
  10 W of bearing drag (seven 6205-2Z, f0 1, 100 mm²/s) is what this model gives at that grease: 9.6 W for six,
  11.4 W for seven.
- **Unfaired rotor parts add more.** A potted HV block of 20 × 40 mm at r 60 in the hub cavity costs ≈ 0.25 W [RH]. Pot
  the rotor's parts into smooth, axisymmetric carriers, for the windage and the balance alike.
- **Use shields (2Z), not contact seals,** on the bearings [IR].

## 7. Balancing

**ISO 21940-11, rigid bodies** (10 Hz against first modes of 27 Hz and more). The permissible offset of the mass centre
is G / ω, and U_per = that offset × m, split equally between two planes of a symmetric body [OC: the standard's
definitions; IR: the grade].

| body | mass | G6.3: U_per, per plane, offset | **G2.5** | G1 |
|:--|--:|--:|--:|--:|
| rotor | 32.9 kg | 3.30 kg·mm, 1.65, 100 µm | **1.31 kg·mm, 0.66 per plane, 40 µm; 5.2 N at 600 rpm** | 0.52 kg·mm, 16 µm |
| counter-rotor | 33.4 kg | 3.35 kg·mm, 1.68, 100 µm | **1.33 kg·mm, 0.67 per plane, 40 µm; 5.3 N** | 0.53 kg·mm, 16 µm |

**Proposed: G2.5 per body as balanced, G6.3 as the in-service alarm limit** [IR]. ISO puts machines up to 950 rpm at
G6.3, and the gap would accept it: the G6.3 whirl is about 6 µm at the gap as laid out, the G2.5 whirl 2.5 µm. G2.5 is
chosen because:
- the counter-rotor floats on the shaft, so the first modes are low (27 / 46 Hz as laid out). Each body's unbalance is
  amplified × 1.16 and passes through the inner bearings into the other body;
- the unbalance grows in service, from G10 creep, the potting and the coils bedding in, and G2.5 leaves that margin
  inside G6.3;
- the bench measures fields with an electro-optic probe on the axis;
- **both bodies need correction balancing anyway**, so G2.5 costs nothing extra:
  - a single utron 6.7 g heavy (0.30 %) uses a whole plane's budget, but a coil's copper varies ±1–2 %;
  - so does a bridge 4.9 g heavy (0.74 %), or a bridge ring 0.1 mm eccentric (6.4 kg × 0.1 mm = 0.64 kg·mm).

**How:**
- Balance each body after assembly on its own bearing seats, in two planes:
  - the rotor's outer carrier discs, about 13 g at r 50 per plane;
  - the counter-rotor's bridge-ring ends, about 4.4 g at r 150.
- Re-check after the 750 rpm spin-seat.
- **The energy to guard:** 1.8 kJ at 600 rpm, 2.7 kJ at 750. The credible fragment is a loose bridge (24 J at 600 rpm,
  38 J at 750) or utron (42 / 66 J), not a burst. A 2–3 mm steel guard stops either [RH].

## 8. What to do (summary) [IR]

1. **No bands.** Specify instead:
   - the stud preload (5 kN, disc springs on steel plates);
   - fitted holes or dowels at the stack and the cheek roots;
   - bonding in the VPI, the coil included;
   - a 750 rpm spin-seat before OP 50;
   - bonded or keyed bridges.
2. **The shaft:** settle it at Ø30 at least, and preferably Ø40 under the utrons, where no HV sleeve is needed — or adopt
   the 8-bearing option.
   - Ø30 takes the 6206 class or Ø25 journals.
   - Avoid titanium (Young's modulus 114 GPa: 21 Hz).
3. **The 8-bearing option** is the structural cure for the gap: × 0.5 on the bearings' runout, × 0.01 on side loads.
   - Detune its f1 from 120 Hz with stiff seats.
   - The drive proposal's gear-end bearing is the lower one of the pair.
4. **The bearings:**
   - inner: P5 at Ca|rel and P6 at the hub faces (or P6 throughout with the 8-bearing option);
   - the frame bearings: P0;
   - all on an axial spring preload, with shields, a low-viscosity grease and metal cartridges in the spiders.
5. **The runout spec:** the all-in TIR per inner bearing ≤ 0.027 mm as laid out, ≤ 0.05 mm with 8 bearings; acceptance
   by measurement (§5.4).
6. **Put the belt's pull into the locating frame bearing,** not into a shaft span: 100 N overhung costs 22 µm of gap as
   laid out.
7. **Ship and test vertically,** or shim the gaps.
8. **Budget about 17 W of mechanical loss on top of the pumps' 21.5 W** (up to 39 W), and measure it by coast-down.
9. **Balance to G2.5** per body, two planes, after assembly.

## Notes against the record

- `sim/pole-design-findings.md` line 195: *"so the coils need banding or a retaining ring."*
  - No band is needed (§2). The coil is a closed loop on the back iron.
- `docs/ledger/DCCREG-design-ledger.md` line 24: *"all the belt's power, about 21 W, ends as heat in the clamps, the
  copper and the iron."*
  - Windage and bearing friction add about 17 W (11–39 W). The belt delivers about 39 W.
- Ledger line 601 and `sim/pole-design-findings.md` line 397: *"hold ≤ 0.05 mm runout on the four inner bearings"* /
  *"about 0.05 mm or better".*
  - Defined and replaced in §5.4: ≤ 0.027 mm all-in as laid out, 0.05 mm with 8 bearings.
- `sim/pole-design-findings.md` line 200: *"Air windage … is not modelled here."*
  - Now modelled: 12 W.
- Ledger lines 200–202: the earlier check (six bearings, Ø25, f1 239 Hz, 5 µm), noted as not re-run on the current
  build.
  - That is the grounded model. On this build it gives 329 Hz; floating, it is 27 Hz (Ø25). This agrees with
    `sim/tube-shaft-findings.md` §0, committed meanwhile.
- `sim/air-stack-sizing-findings.md` lines 98 and 191: the shaft's first mode *"near 40–60 Hz"* / *"near 100 Hz … above
  the 30 Hz criterion"*.
  - Both scaled the grounded 250 Hz. The current 940 mm build sits at 27 Hz (Ø25), below 3 × 600 rpm.
- `sim/shaft_bearings.py` line 29: `K_BEARING = 2e8` [RH].
  - A vertical shaft's deep-groove bearings carry no radial load, so with clearance and no preload they are free play.
    Under a 100 N axial preload they are 1.2e8 N/m, and 0.86e8 N/m on a G10 spider.
  - At that stiffness the 8-bearing f1 of §0 (165 Hz) is 131 Hz, near the 120 Hz pump.
- `sim/tube-shaft-findings.md` §0: *"utron gap change under 1 g lateral 123 µm"*.
  - That is at the stack's centre. The outer end of the stack moves 1.7 × (222 µm on §0's parameters).
- The coils' *"46 °C in air"* (ledger line 253) is at a 40 °C ambient (`sim/pole_design.py` line 125). The thermal
  budget uses it as such.

## Caveats

- **[OC]:**
  - the rotating-ring, rotating-disc and beam stresses;
  - the beam model's statics and modes (converged);
  - the Maxwell-stress force;
  - ISO 21940's definitions;
  - the influence of the frame bearings (zero, by statics).
- **[IR]:**
  - the datasheet-class strengths and moduli: G10 in-plane 250 MPa, 18 GPa, CTE 13 (10–16) ppm/K; Al 240 MPa;
    PEEK 95 MPa; A4-70 450 / 700 MPa;
  - the assumed fastenings (5 kN stud preload, one M5 per cheek root);
  - ISO 492 runout classes and the proposed seat runouts;
  - the bearings' Hertz stiffness;
  - the windage correlations (Daily & Nece, Bilgen & Boulos, Theodorsen & Regier);
  - Palmgren's friction;
  - the 1.25 × overspeed;
  - the worst-case and RSS stack-ups;
  - the thermal chain.
- **[RH]:**
  - the G10 spiders' stiffness (3e8 N/m) and the frame as rigid;
  - the 10 % eccentricity rule;
  - the bond's 5 MPa;
  - the windage coefficients: the counter-rotation factor 0.72, the edge c_D, the paddle c_D and c_f, the groove factor;
  - the 100 N belt pull;
  - the masses of La / Lb and the electronics, and where they sit;
  - the guard.
- **Not modelled:**
  - gyroscopic effects (small at 10 Hz);
  - the gear's mesh forces (the proposed bevel reverser's three pinions cancel them);
  - torsional modes;
  - the 3-D flow in the sectored stack;
  - creep of G10 over time;
  - the spider's axial and tilt stiffness;
  - the reluctance sections' cooling flow.
- **The windage range is wide** (8–25 W). The coast-down test should settle it before the drive is finalised.
