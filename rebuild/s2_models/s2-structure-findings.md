# S2a, step 3 — the structure filled in, and its integrity: findings

**Sources:**
- `rebuild/s2_models/s2_geometry.py` → `s2_geometry_results.json`, with the model in `geometry/`: 339 solids, 852 mm (with step 5's thicker end plates);
- `rebuild/s2_models/s2_structure.py` → `s2_structure_results.json`.

**Status:** PROPOSED (2026-10-16), the designer's review.

**The designer (2026-10-16):** "shall we fill in the missing structural components and check the structural and
electrostatic integrity?" The choices behind this pass:

| choice | the designer's answer |
|:--|:--|
| the creepage rules' pollution degree | PD2, as the record |
| the sleeve's creepage | a stock cover and sheds |
| the counter-rotor's two halves | one G10 cage tube across the hub |
| the drive | not yet (an interface) |
| the internal Al-tube combs in the column | keep, as PROPOSED |
| the outer retainer | holds the frame bearings; 40 × 40 B-type T-slot; the frame earthed, REF floating |

- **A correction:** "The structural beams out of extruded parts are meant for the structural retainer that forms the
  most outer cage retainer". I had first read the "column" as the Ca / Cb column. The retainer is the extruded part;
  the column's combs are kept as PROPOSED.

**Steps 4 and 5 (`s2-modes-findings.md`, `s2-thickness-findings.md`) revise this pass:** the driven end plates are
thickened (Ca_06 / Ca_01 4.0, the first rotor vane 4.0, the last stator vane 4.5 mm; decided by delegation, 10-17),
the rest stay 3 mm. The figures below are re-run with them; the all-3 mm figures are given in brackets where they
differ.

## What was added [IR, a first cut]

| part | what | why |
|:--|:--|:--|
| the column's combs | per net, three Al 6063 round tubes 10 × 1.5 (EN 755-8) at r 30, 120° apart, through tabs on that net's plates, with Al spacer tubes 12 × 1. The N1 comb runs on through the rotor vanes; the N2 comb stands on three catalogue glazed-steatite standoffs on the first rotor vane | the column's support and its net ties (OPEN until now); each tube is 14 mm from the other net's plates (12.9 needed) |
| the column's place | moved out to h 97 (from 91) | the N1 comb reaches in to r 23.5, inside the flange's corner, so its hub end must clear the flange by the full 26.1 mm |
| the riser and the tap | straight up from the deck's junctions: the riser through a clearance hole in the first plate (N2) to the first N1 plate, the tap to the first plate | the deck-to-column connections (OPEN until now) |
| the midpoint ring | moved to r 45, inside the sticks' lane | it passed 2.8 mm from the riser |
| the stator | lugs on the stator vanes out to r 190; six steel M5 tie rods with Al spacer tubes at r 182 (27 mm off the rotor vanes' tips); the rods end in the spiders | the stator's REF bus and support (OPEN until now) |
| the cage | one G10 tube, r 192–196, spider to spider across the hub; the spiders run in to its bore | the designer's choice |
| the sleeve | an extruded PTFE tube over the G10 sleeve; two 10 mm PTFE sheds at the bearing end | the designer's fix for G-CREEP |
| the outer retainer | per end: the REF shaft's insulating G10 coupling (a solid 27 mm plug, a PTFE cover, two sheds), an earthed steel stub, the frame bearing (6205 class) in a 150 × 150 × 15 Al plate on two 40 × 40 cross beams, a square of 40 × 40 perimeter beams; four 40 × 40 corner posts, the frame 390 × 390 mm | the designer's retainer; the frame earthed, REF floating |

- **REF against earth is 13.8 kV DC: DECIDED** (the designer, 2026-10-16: "the ref floaths at the 13.8kV"). That is the machine's highest node peak,
  since a floating REF has no other bound. The other nets against earth are taken as their peak against REF plus that.
  A bleeder from REF to earth would cap it and shrink the couplings and the frame.

## The electrostatic gates (the model)

| gate | result |
|:--|:--|
| G-CLASH | 882 pairs, no clash |
| G-SWEEP | no counter-rotor solid in a rotor solid's swept volume |
| G-AIR (case A at 1.5 × the peak; earth included) | every pair clear |
| G-POT (in the potting, 2 kV/mm) | every pair clear |
| G-CREEP, the sleeve (PTFE cover, PD2) | 72 / 67 mm against 60 mm needed: passes |
| G-CREEP, the couplings (REF–earth) | 99 mm against 86 mm: passes |
| the nets | every net reaches its conductors, earth included |

- **Field-judged, not by case A** [IR]: the N1 comb inside the vane stack's bore, between the N1 rotor rings, and the
  riser and tap against the column's plates beyond the one they land on. These are the cells' own field regions, for
  the field solve (S2b).

## The structural study (`s2_structure.py`)

1. **The masses:**
   - the rotor 15.9 kg (15.0 at 3 mm);
   - the counter-rotor 23.9 kg (23.6; the spiders and the stator vanes' lugs weigh most);
   - the retainer 37.0 kg as drawn [RH: the T-slot drawn as a solid bar overstates it; a real 40 × 40 B-type is
     about 1.5 kg/m].
2. **The spin stresses at 750 rpm (1.25 × overspeed) are small everywhere** [OC: the rotating annulus, the radial
   bar]:

   | part | stress | safety |
   |:--|:--|:--|
   | Ca plate (Al annulus) | 0.32 MPa | × 500 |
   | rotor vane sector root | 0.50 MPa | × 320 |
   | stator vane ring with lugs | 0.56 MPa | × 284 |
   | G10 cage | 0.44 MPa | × 684 |
   | Al spider | 0.51 MPa | × 312 |
   | a tie rod's shear under a lug | 0.25 MPa | × 474 |

3. **The bearings:**
   - the lower frame bearing carries the rotating masses' weight, 394 N axial (382 at 3 mm; the axis vertical);
   - the REF-link bearings carry the counter-rotor, 234 N (231);
   - the out-of-balance force at G2.5 is 6.3 N (6);
   - a 6205's C0 is 7.8 kN.
4. **The rotor's bending modes:** 35.6, 97.3 and 195.0 Hz (36.7 / 99.1 / 198 at 3 mm) [IR: the beam model, pinned at
   the frame bearings on the cross beams' stiffness].
   - The first is 3.6 × the shaft's 10 Hz: clear.
   - ~~The second is 17 % under the pump's 120 Hz.~~ **Corrected in step 4:** the pump doesn't excite the bending
     [OC: the six sectors' pulls are axial and their lateral parts cancel]; only the 1× out-of-balance does.
   - The weak links are the couplings' G10 plugs (Ø25, E 18 GPa). A larger plug or coupling diameter would stiffen
     the shaft, if it is ever needed.
5. **The electrostatic pull:** 23 Pa at the varicap's peak, 1.5 N per plate, at 120 Hz. Small, but resonant if a
   plate's mode is near 120 Hz:
   - ~~The hand estimates: the rotor sectors about 141 Hz, the stator sectors about 424 Hz, the Ca plates under
     251 Hz.~~ **Superseded by the modal FE (step 4):** at 3 mm the pull-excited modes were 131, 115 and 129 Hz, and
     600 rpm was not clear. With the end plates thickened, the driven modes sit at 174, 168 and 170 Hz, and 600 rpm is clear
     (`s2-modes-findings.md`, `s2-thickness-findings.md`).

## OPEN, for the designer

- ~~REF against earth~~: DECIDED, 13.8 kV, no bleeder.
- ~~Two dynamic margins near 120 Hz~~: settled by step 4's modal FE and the thicker plates (PROPOSED; the
  designer's). Torsion through the drive stays OPEN (`s2-modes-findings.md`).
- **Still not drawn:** the drive (an interface, by decision), the screws and clamps, and the deck plate's fixing on
  the coupler.

## Next

- **S2b, the field solve:** every conductor's net from `.parts.json`, for C1(θ), C2(θ), Ca, Cb, C_k, the strays and
  the field at the edges and in the bore.
