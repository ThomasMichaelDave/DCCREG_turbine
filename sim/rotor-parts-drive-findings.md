# The AH-drive parts on the rotor and the drive re-cut onto the layout — findings

**Source:** `sim/rotor_parts_drive.py` → `sim/rotor_parts_drive_results.json` and `docs/figures/rotor-parts-drive.png`
(about two minutes; OCP). The full model comes from `python3 sim/tube_geometry.py --layout --full`, which builds the
parts from this study: `docs/geometry/tube/tube-r150-n6-air6-wound-g0p5-6br-hub50-layout-full.{step,glb,parts.json}`,
its section `…-layout-full-section.png`, and its gates in `sim/tube_geometry_layout_full_results.json`. The layout
without them (`--layout`, the drawing set's basis) is unchanged.

**What it is:** the designer asked for "the AH parts locations proposed and positioned in an updated model and the
bevel reverse too". So this study does two things:
- it proposes places on the rotor for the magnetic pump's parts that drive the AH: La / Lb, D1*–D4*, the eight node
  snubbers, the two AH bypass capacitors and the K4 kick;
- it re-cuts the 1 : −1 bevel reverser and its belt drive onto the layout's side A end (the ledger's §6, item 71).

**Status:** PROPOSED. The places, the cradles, the ballast and the re-cut are the designer's to accept or set
otherwise. No study of record changed.

**Tags:**
- [OC] the balance arithmetic, the loads, the clearances' bounds, the two-body modes;
- [IR] the places, the cradles, the orientations, the routes, the re-cut's choices;
- [RH] the bought parts' masses, the bolts, the cross leads' insulation and their field estimate.

## Headline
- **Every part has a place, and the model closes.**
  - The full model: 663 solids, the 113 new ones among them.
  - No part overlaps another: 1939 pairs tested in the layout's gate, 499 new pairs in the study.
  - No rotor solid sweeps a counter-rotor solid (`sim/tube_geometry_layout_full_results.json` G-TUBE-SWEEP).
  - The STEP reads back with all 663 instances.
- **The parts sit in the reluctance bays' three free wedges**, between the utrons (at 0, 120 and 240°), so at 60,
  180 and 300°. Each wedge holds a G10 cradle between the bay's two carrier discs (z 61–181 on side A) [IR]:

  | wedge | side A | side B (turned over) |
  |:--|:--|:--|
  | S1, 60° | La | Lb |
  | S2, 180° | D1*, D3*; the snubbers at a, d, x1, f2; bypass A; ballast | D2*, D4*; the snubbers at b, c, x2, f3; bypass B; ballast |
  | S3, 300° | the K4 kick; ballast | ballast |

- **Each side balances on its own.** The brass ballast in S2 and S3 gives every wedge the choke wedge's m·r (138.0
  kg·mm) and m·r·z [OC]. Three equal moments 120° apart sum to zero, and their equal axial lever leaves no couple.
  - The ballast: 1.09 kg (23.2 mm) in S2, 1.02 kg in S3 A, 1.16 kg in S3 B.
  - The solver's residual is 0.013 / 0.002 g·mm, against the 1732 g·mm that G2.5 allows.
- **The price is mass: +9.74 kg on the rotor, 4.88 kg a side.**
  - That is the choke's 1.665 kg, the three cradles, the small parts, and 3.27 kg of ballast a side.
  - It is +29 % on the layout's 33.8 kg rotor (the ledger's item 70).
- **The shafts: f1 holds, f2 falls toward 120 Hz** (d 25, the coupler joint; this study's reading of the solids):

  | | f1 | f2 | f3 | rotor |
  |:--|:--|:--|:--|:--|
  | the layout as drawn, stiff seats (k_b 2 × 10⁸) | 83.9 | 155.8 | 195.3 Hz | 38.2 kg |
  | with the parts and the drive | 83.9 | 116.8 | 164.7 Hz | 50.4 kg |
  | the layout as drawn, G10 spiders (k_b 0.86 × 10⁸) | 79.8 | 136.2 | 185.9 Hz | 38.2 kg |
  | with the parts and the drive | 79.3 | 107.9 | 149.1 Hz | 50.4 kg |

  f1 is the central span's mode and does not move. f2 is the reluctance bays' mode. It drops to 3–10 % under the
  pumps' 120 Hz (OPEN, §4).
- **The drive re-cut** [IR]:
  - the first cut moves up 30.5 mm, which puts its gear-end bearing on the layout's bridge-ring bearing A
    (z 22.5–37.5);
  - that bearing and its cartridge take the place of the gear-end bearing, the counter-rotor's hub and its end disc
    (DRV-108 and DRV-109 drop out);
  - the counter-rotor's side gear bolts by its Ø80 back flange (6 × M4 on PCD 70) under the cartridge, and closes the
    bearing's seat from below;
  - the case loses its lip: it is cut at z 22.5, 3.5 mm under the bridge-ring spider;
  - the layout's frame end bearing A and its spider go. The locating bearing in the case floor (z −63.5 to −48.5)
    is the frame bearing now;
  - the reluctance sleeve A starts at z 47.5, on the collar;
  - the shaft runs on to z −102.5, the rotor gear's keyway in it.
- **The machine:** z −105.5 (the bell's foot) to 1014. The frame bearings are 1060 mm apart, where they were 994.
- **Everything that turns against something else keeps clear** (168 pairs; at least 1.0 mm).
  - The least are the first cut's own: 1.0 mm axially, the rotor gear's hub to the locating bearing's retaining ring;
    1.25 mm radially, the CR gear's bore to spacer A.
  - The re-cut's own: 2.75 mm from the CR gear to the shaft; 2.95 mm from the cartridge to the collar; 3.5 mm
    axially from the spider to the case top.

## 1. The wedges and their cradles
- **The free space** [OC: the layout's solids]. In each bay, between the utrons' bands, there are three wedges about
  80° wide at r 21–120 and z 61–181. The bridges (counter-rotor) start at r 130.5, the bridge ring at r 131.5.
- **The cradle** (each wedge; G10) [IR; RH the bolts]:
  - two 6 mm end plates on the carrier discs' inboard faces. Each is a 120° sector r 22.5–122, flat at the
    backplate and cut 3 mm clear of both neighbouring utrons' bands (their cheeks, |y| ≤ 29 from x 43);
  - a 6 mm backplate across the wedge's outer end (u 110–116, 64 wide, z 67–175), its corners at r 120.3. It takes the
    parts' centrifugal load in bearing, and the end plates take it to the discs;
  - eight M5 a wedge [RH].
- **S1: La / Lb** (EI-84 × 35, 1.665 kg; `sim/parts_first_cut_results.json` la_lb.chosen) [IR]:
  - the E's outer legs flat on the backplate, so x (84) is radial, u 26–110;
  - the stack (35, the winding 61 over all) tangential; the legs (70) axial, z 86–156;
  - its leads go to the harness (not drawn).
- **S2 and S3:**
  - the brass ballast (CuZn39Pb3, non-magnetic) on the backplate, 54 × 102 mm;
  - a 3 mm G10 board on the ballast, drilled for the parts' leads;
  - the parts on the board: the bypass capacitor standing, its pins cut to the board; the DO-201AD rectifiers and the
    snubbers' OX resistors lying flat, their leads bent through the board; the R76 capacitors standing; the K4
    module's base on the board, axial;
  - S3 B carries the ballast alone.
- **The harness** [IR]: from the LV cable's radial exit (r 24, z 201) round the sleeve at r 30, above the outer
  carrier disc, out along each wedge's bisector to r 62, then down outside the disc to the cradle's end plate (its
  grommet not drawn).

## 2. The balance and the loads
- **The solve** (`balanced()`) [OC]: S1's moments are set by the choke. The ballast's thickness, its tangential
  offset and its axial centre in S2 / S3 are solved so that m·u, m·v and m·u·z equal S1's (converged in four
  iterations; 0.48 mm and 0.36 mm of tangential offset).

  | wedge | mass | r of its centroid | load at 600 rpm | at 750 rpm |
  |:--|:--|:--|:--|:--|
  | S1 (La / Lb + cradle) | 1.955 kg | 70.6 mm | 545 N | 852 N |
  | S2 | 1.458 kg | 94.7 mm | 545 N | 852 N |
  | S3 A / S3 B | 1.465 / 1.450 kg | 94.2 / 95.2 mm | 545 N | 852 N |

- **The cradle is lightly loaded** [RH: the bolts]. At 750 rpm, through eight M5 a wedge: 7.5 MPa of shear in the
  bolts, 3.6 MPa of bearing in the G10, 1.8 MPa of in-plane tension in an end plate. G10's strengths are 100 MPa and
  more.
- **The bought parts' masses are [RH]**, from the makers' class: the cell 36 g, the snap-in capacitor 32 g, a
  rectifier 1.1 g. They are 4 % of a wedge, and the ballast is solved to them.

## 3. The cross-hub leads
- **Two LV leads must cross the hub:**
  - b (AH_B's finish) to bay A, for D1* and D4*;
  - d (AH_A's finish) to bay B, for D2*.
- **Their route** [IR]:
  - from the bore, in a 3 × 3 groove in each flange's inboard face;
  - through a Ø3.2 hole in the coupler's wall;
  - axially along the coupler at r 39, in the can (the coupler r 33, the can r 46), at −10° and −30°, far from the
    rings' leads at 150–175°;
  - then into the other flange the same way.
  - The flanges and the coupler carry the grooves and holes in the full model.
- **Their field** [RH: a coax estimate]:
  - the rings (±14.9 kV, r 25) inside the grounded can would put r 39 at 4.0 kV;
  - a lead there at about 0 V has 1.34 kV/mm at its insulation's surface;
  - Peek's onset at that radius is 5.55 kV/mm (`sim/rotor_parts_drive_results.json` cross_leads).
  - A field solve of the hub with the leads is OPEN; so is what the leads do to the rings' field on the coupler.

## 4. What it leaves open
- **f2 near 120 Hz** (OPEN). With the parts, the reluctance bays' mode falls to 108–117 Hz, 3–10 % under the pumps'
  120 Hz. The utrons' pulls are three-fold symmetric, so they put no net side load on the shaft in the ideal; what an
  asymmetry would excite there is to be checked. The levers are fewer kilograms (below), stiffer seats, or d 30.
- **The ballast, 3.3 kg a side** [IR]. It exists only to balance one 1.7 kg choke. The alternatives are the
  designer's:
  - the first cut's compact choke, EI-66 × 44 at 1.19 kg (`sim/parts_first_cut_results.json` la_lb.compact), cuts
    it about a third;
  - a denser ballast (tungsten alloy) cuts its volume, not its m·r;
  - or split each choke's iron over the three wedges (a different part).
- **The chokes beside the utrons.** 1.2 kg of SiFe sits in the bay between two utrons' windings. Its coupling to their
  field, and theirs to it, is not modelled (OPEN).
- **The carrier discs' new duty.** They now carry 545 N a wedge at 600 rpm, against `sim/rotor-mechanics-findings.md`'s
  sizing for the utrons alone (OPEN).
- **The bypass capacitors in the bays.** They put the bore's cable and the harness (some 0.3 m each way [RH]) in series with the bypass,
  which `sim/ah-steady-cusp-findings.md` treats as across the coil (OPEN: the leads' resistance and inductance).
- **The K4's reed** needs a magnet past it at full speed. The rotor's bay is shielded by the counter-rotor's bridges
  and ring, so where the magnet goes is OPEN.
- **The re-cut's details** [IR]:
  - the case top is 3.5 mm under the counter-rotor's spider, with no labyrinth;
  - the collar's Ø40 face spans the bearing's shield (the first cut's choice). A relieved face, or a Ø32 collar, clears
    it;
  - the motor is drawn at +x, 245 mm out; the frame that holds it, the case and the B end is not drawn.
- **The records it makes stale:**
  - the drawing set's DRV sheets (drawn on the record's stack-up), SHF-305 (the sleeve), BRG-811 and P-001 (the frame
    end bearing A);
  - the viewer's model (the layout without these parts).
