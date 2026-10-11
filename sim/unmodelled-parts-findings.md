# The proposed parts outside the layout's model, in solids — findings

**Source:** `sim/unmodelled_parts.py` → `sim/unmodelled_parts_results.json` (about four minutes; OCP). The drawing set
draws them: `docs/make_drawing_set.py`, 24 sheets (REL-720 to REL-730, DRV-100 to DRV-190, P-012 to P-019).

**Status:** PROPOSED. These are drawings of first cuts, made so the designer can see them. Their places on the rotor
are OPEN. The drive stands on the record's 940 mm stack-up and is to be re-cut on the layout
(`docs/ledger/DCCREG-design-ledger.md` §6, item 71). No study of record changed.

**What it builds** (every dimension from a first cut, or tagged where this script chooses it):
- **The magnetic pump's parts on the rotor** (`sim/parts-first-cut-findings.md`):
  - La / Lb: EI-84 × 35, 150 turns of Ø1.40 (`sim/parts_first_cut_results.json` la_lb.chosen; the bobbin and the
    window from `sim/parts_first_cut.py` choke(), winding());
  - the K4 start kick as a module [RH: its layout];
  - the bought electronics' envelopes: D1*–D4* (DO-201AD), the node snubbers (KEMET R76, Ohmite OX), the AH bypass
    (Rubycon snap-in 30 × 30).
- **The drive** (`docs/drive-gear-belt.md`; `sim/drive_sizing_results.json` gear, belt, envelope):
  - the 1 : −1 bevel reverser at side A: two stainless side gears z 30, three POM pinions z 20 in cartridges, the gear
    case and its bell, the counter-rotor's hub and end disc;
  - the shaft's parts that set it: the collar, three spacers, the key, the locating bearing and its ring, the pulley,
    the nut;
  - the belt drive: the 80T and 20T pulleys, the belt, the motor on its plate.
- **The gears' teeth** [IR]:
  - straight bevels; the heel's involute profile laid on the back cone (Tredgold's virtual spur gear, z / cos δ teeth);
  - the flanks ruled straight to the cone's apex;
  - each tooth thinned 0.064 mm for the first cut's backlash (j_n 0.10–0.15, §5);
  - the pinions turned half a pitch, so a pinion tooth lies on each contact line, where both side gears have a space
    [OC: the mesh's phase].
- **The drawings draw the gears as blanks**, as a gear drawing does (the tip cone as the outline). The 3-D views and
  the assembly sections draw the teeth.

## Headline

### 1. Everything fits, and the teeth mesh
| check | result | where |
|:--|:--|:--|
| overlaps, every pair of parts (the reverser, the belt drive, the choke, the kick) | none (the gear blanks' tooth zones aside: their teeth are checked as solids) | `overlaps_blank`, `overlaps` |
| the teeth, each pinion against each side gear | no overlap; **0.043 mm** at the closest point, all six meshes | `reverser.mesh_overlap_mm3`, `mesh_clearance_mm` |
| the belt's pitch length at the first cut's centres (245.35 mm) | **750.02 mm**, the catalogue's 750 | `belt.pitch_length_mm` |
| the masses against the first cuts' [IR] blanks | side gears 0.268 / 0.227 kg (0.30), pinion 0.0143 kg (0.035), counter-rotor hub 0.143 kg (0.25): the bodies' inertias change by under 0.1 % | `gears`, `parts` |
| the choke's iron | 1.2044 kg, the first cut's 1.2043 | `choke.iron_kg_model` |

**The clearances between parts that turn against each other** (mm; `reverser.clearance_mm`, `belt.clearance_mm`):

| pair | gap | pair | gap |
|:--|--:|:--|--:|
| the counter-rotor's gear / the shaft's spacer (1200 rpm relative) | 1.5 | the hub / the collar | 2.0 |
| the rotor's gear / the locating bearing's ring | 2.2 | the pinion / its cartridge | 5.5 |
| the pinion / the shaft's spacer | 5.3 | the gears / the cartridges | 7.3 |
| the 80T pulley / the bell | 8.9 | the belt / the bell | 7.2 |
| the 80T pulley / the case floor | 5.0 | the 20T pulley / the motor plate | 9.4 |

### 2. The drive's first cut does not close as drawn: five departures [IR, PROPOSED]
The first cut is a concept with its stack-up (`docs/drive-gear-belt.md` §8). Drawn part by part, five of its choices
cannot be built as they stand:

| # | the first cut | the drawing |
|:--|:--|:--|
| 1 | the counter-rotor's hub holds the gear-end 6205-2Z over a lip below it (the sketch: the bearing at z −5–10 on a lip at −8 to −5) | the lip below cannot carry the counter-rotor's weight (350 N, §5) down into the outer ring. The seat is drawn open below, with a lip Ø44 at the top (z 7–10). The gear's flange closes the seat from below (DRV-108) |
| 2 | the counter-rotor's side gear is "bolted under the hub" | the gear's own body (r ≤ 28.3) cannot reach the hub outside the bearing (r 26). It gets a back flange Ø80 × 3, with six M4 on PCD Ø70 between the pinions (DRV-102) |
| 3 | each pinion's two 6000-2Z sit 16 mm apart, with the mesh 12 mm outboard (the statics, §5) | the first cut's own case cannot hold that spacing: the pinion's back at 38, the bearings, the spacer and the wall (`sim/drive_sizing.py` stackup case_r). Drawn 12 mm apart, the mesh 17 mm outboard: the inner bearing takes **40 N steady and 195 N at the driver's limit**, against 29 / 141 N. Static safety 10 (was 14), L10 3 × 10⁷ h steady, the axle at 14 MPa (`reverser.pinion_bearings`) |
| 4 | the bell is the case wall continued (r 64–72) down to the base plate, with belt windows | it would cut the belt's land (r 63.1–64.8) and enclose the 80T pulley. Drawn Ø164 / Ø144 over 170°, a C open to the motor, so the belt clears it by 7.2 mm and can be fitted without lifting the machine. Three M6 come up from under the base plate, through the bell, into the case floor's flange Ø168 (PCD Ø154, clear of the Ø144 barrel) (DRV-106, DRV-107) |
| 5 | the 80T pulley is "24 mm over the flanges" (§8) | the catalogue's TL80-5M-15 has no flanges and is 25 mm through (F 22). The flanged pulley is the 20T, P20-5M-15F (P-014) |

**Also chosen to close the stack** [IR]. The shaft carries the stack in this order:
- the collar, a two-piece clamp Ø25 / Ø40 × 10, over the gear-end bearing's inner ring;
- the bearing's inner ring;
- spacer A, Ø25 / Ø28 × 43.0, through the counter-rotor's gear;
- the rotor's gear;
- spacer B, Ø25 / Ø32 × 3;
- the locating bearing's inner ring;
- spacer C, Ø25 / Ø32 × 6.6;
- the pulley's taper bush.

The lock nut (SKF KM 5) clamps the stack against the collar. The collar carries the rotor's weight into the stack, so
both bodies' 689 N reach the case floor's lip through the locating bearing (§7). A retaining ring Ø44 / Ø66 × 2 on
three M3 holds the bearing's outer ring down. The parts are listed on DRV-190.

### 3. The choke and the kick
- **La / Lb** as sized (§1 of `sim/parts-first-cut-findings.md`):
  - core: EI-84 × 35;
  - winding: 7 layers of 24 turns, the build 10.79 mm round the leg's 28 × 35 section, corners R1.25 inside and R12.04
    outside, 37.2 mm long between the flanges;
  - bobbin: a 1.0 mm wall and 1.5 mm flanges, the flanges 1 mm past the build [IR]. That makes the choke **84 × 70 × 61**
    over all; the first cut's 59.1 is the build alone (`choke.data.outline_mm`).
- **The K4 kick** is drawn as a placeholder module [RH]:
  - a G10 base 100 × 60;
  - the 9 V cell in a holder;
  - the board under silicone: the 470 µF bipolar can laid down, the SCR and the resistors;
  - the reed sensor on the base;
  - the arming link on the potting.

  The module is 100 × 60 × 33. Its place on the rotor is OPEN (§3 of the first cut).

### 4. The bought parts' candidates (this session's search, 2026-10-11; confirm on the maker's current sheet)
| part | candidate | alternates | listing |
|:--|:--|:--|:--|
| D1*, D2* (200 V, ≥ 3 A) | SMC SB5200 (200 V, 5 A, DO-201AD) | PANJIT MBR5200, MCC SR5200-TP | DigiKey 6022615; LCSC C268577 |
| D3*, D4* (150 V, ≥ 3 A) | SR5150 (150 V, 5 A, DO-201AD) | ST STPS3150RL (3 A) | LCSC C129840, C262964 |
| snubber C (22 nF PP, ≥ 250 V) | KEMET R76 22 nF 400 V, 10 mm pitch, 13 × 9 × 14 | Panasonic ECW-F 250 V | RS 1353468 |
| snubber R (240 Ω, 0.5 W, pulse) | Ohmite OX221KE (220 Ω, 1 W, Ø5.5 × 16.5) | OY221KE (2 W) | DigiKey 823917 |
| AH bypass (22 mF, ≥ 2 A rms) | Rubycon 10MXG22000MEFCSN30X30 (Ø30 × 30, 2.5 A rms; its ESR not found) | Nichicon LGU1E223MELC (Ø35 × 35) | a retailer's listing; RS 846-6928 |
| the kick | Ultralife U9VL-J-P; Nichicon UES1E471MHM; Littelfuse TCR22-8; Littelfuse 59140 + 57140-000 | — | the makers' pages |
| pinion bearings | SKF 6000-2Z (10 / 26 / 8, C 4.75 kN, C0 1.96 kN) | FAG, NSK, NTN 6000 | simplybearings.co.uk |
| belt | Gates 750-5M-15 PowerGrip HTD | any HTD 5M 750 × 15 | acorn-ind.co.uk |
| pulleys | TL80-5M-15 + taper bush 1610; P20-5M-15F | — | beltingonline.com; ondrives.com |
| motor | Nanotec / SMD APBA60M048030-E (200 W, 48 V, 3000 rpm, 0.64 N·m, 60 mm flange, 110 mm) | Oriental Motor BLV 200 W; Nanotec DB80S048030 | smd.ee; nanotec.com |
| EI-84 laminations, bobbin | none found: to the specification | — | — |

## Caveats
- **[IR]:**
  - the tooth form (Tredgold's approximation; a real straight bevel's spherical involute differs by microns at these
    sizes, inside the 0.043 mm the mesh check finds);
  - every dimension the first cuts leave open: the hub's lip, the gear's flange, the cartridge's land, the bosses, the
    bell, the collar and the spacers, the motor plate;
  - the motor's flange (PCD Ø70, spigot Ø50, shaft Ø14 × 30: the 60 mm frame's class, to confirm on its drawing).
- **[RH]:** the kick module's layout and envelope; the reed sensor's height; the belt drawn as its land only.
- **The bearings are solid annuli,** as in the layout's model: no balls or shields.
- **Not designed here:** the frame (the base plate, the columns, the top plate, the motor's bracket), the chokes'
  brackets on the rotor, the electronics' boards and clamps. Their places are OPEN.

## What this updates
- `docs/drive-gear-belt.md`: the five departures above, the pinion bearings' loads at the spacing its own case holds,
  and the 80T pulley's flanges.
- `sim/parts-first-cut-findings.md` §1: the choke is 61 mm deep over its flanges (59.1 over the build).
- The ledger's drawing register (§7, Part D) and its list of what is not drawn.
