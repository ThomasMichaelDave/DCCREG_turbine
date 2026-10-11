# The doubler's capacitors as built: the mounts of C1 / C2 and Ca / Cb — findings

**Source:** `sim/doubler_caps.py` → `sim/doubler_caps_results.json` and `docs/figures/doubler-caps.png` (about 70 s on
four cores; ngspice, OCP). The solids come from `sim/tube_geometry.py --layout`, which imports this study's placement
(`placement()`). The parts' and the sub-assemblies' drawings are DCCREG-CAP-600 to -607 (C1 / C2) and -610 to -617
(Ca / Cb) in the drawing set (`docs/make_drawing_set.py`).

**What it is:** the mounts the record leaves undrawn ("connection and mounts not drawn", `sim/tube_geometry.py`; the Ca
mounts' first cut in `sim/parts-first-cut-findings.md` §4), designed for the multiplier's layout, where Ca / Cb hold
13.2 kV DC (`sim/multiplier-layout-findings.md` §4). They are checked against the record's HV rules and its rim
criterion, and run through the pump and the shafts.
**Status:** PROPOSED. The arrangement, the sizes and the parts are the designer's to accept.
**Tags:**
- [OC] the 2-D and axisymmetric field solves; the deck; the beam model;
- [IR] the arrangement; the HV rules as `sim/parts_first_cut.py` applies them; the masses;
- [RH] the sizes; the stray formulas; Peek's surface factor 0.85 (the record's); the fringe's width.

## Headline
- **Ca / Cb: two combs, each on its own three posts in the column's bore** (`placement()`):
  - each plate carries three tabs into the bore (r 50 → 27) at its comb's angles. The posts stand on the tabs at
    r 35, the riser's own radius;
  - the **node-1 comb** (Ca_05, Ca_03, Ca_01) hangs from the first rotor vane on Al spacers Ø8. The riser now lands
    under its first post, at Ca_05;
  - the **node-2 comb** (Ca_06, Ca_04, Ca_02) stands on three **glazed steatite standoffs** (Ø16 × 30, M4 inserts) on
    the can's end disc (REF);
  - **no support touches two adjacent plates** (the record's rule), and no plate is notched: the plates stay full
    annuli, so Ca keeps its overlap.
- **C1 / C2, rotor:** G10 spacer rings (r 20.5–32 × 15) between the rotor vanes' hub rings, bonded on the sleeve, three
  G10 dowels Ø5. No node-1 metal touches the sleeve below the first rotor vane, so the PTFE cover keeps its 84 mm.
- **C1 / C2, stator:**
  - each stator vane gets six lugs outside its ring;
  - six glass-epoxy tie rods M8 with G10 spacer tubes stack the vanes, from a G10 end ring under the first vane to
    the Ca|reluctance spider;
  - **the cage tube moves out to r 182–186** (was 162–166). The lugs locate in its bore, so it stays one tube from
    spider to spider, and the spiders grow to r 182.
- **The HV rules hold** at every new interface (§2):
  - post to post, 27 mm of air against the 24.7 mm case-A clearance;
  - the standoff, 30 mm of glazed steatite against 6.5 mm (PTFE would need 19.7);
  - the rims to the new G10, 15–18 mm against the record's 12 mm rule.
- **The field where a tab crosses the other comb's bore edge** (§3) holds a corona margin of **1.052** on a handled
  surface (Peek, m 0.85).
  - That is the record's own C1 rims' class (1.061); the column's aligned rims hold 1.432.
  - The posts themselves hold 4.07. Closer than 7 mm the margin falls below 1.
- **Ca: 480.5 → 482.3 pF** (+1.8 pF of fringe at the 15 crossings), 1.072 C_max against 1.068 as laid out. The
  DECIDED rule asks for 1.1 (`sim/tube-strays-findings.md` §4).
- **The strays** [RH]: node 1 / 4 +3.8 pF (70.8 → 74.6), node 2 / 3 +4.6 pF (13.7 → 18.3).
- **The pump barely moves** (the layout study's deck at the pick, C3–C6 180 pF):
  - the start-up gain goes 1.01636 → 1.01589 (−0.00048);
  - the rings go ±16.248 → ±16.239 kV;
  - the copy of the deck reproduces the layout study's rows exactly.
- **The shafts:**
  - the rotor gains 0.79 kg (35.09 → 35.88) and the counter-rotor 2.47 kg (33.93 → 36.40), from the drawn solids;
  - f1 at d 25 goes 86.1 → 85.1 Hz on stiff seats and 82.2 → 81.1 Hz on G10 spiders, against 60 Hz;
  - the utron gap's change is unchanged (≤ 1.6 µm at 1 g).
- **The solids:** 552 from 168 prototypes (386 / 147 before). No clash in 1447 pairs, no sweep hit, every G-LAYOUT gap
  held; the riser keeps 13.5 mm to the node-2 plates' bores.

## 1. The arrangement [IR; RH the sizes]
| | node-1 comb (node 4 on side B) | node-2 comb (node 3) |
|:--|:--|:--|
| plates | Ca_05, Ca_03, Ca_01 (h 126, 144, 162) | Ca_06, Ca_04, Ca_02 (h 117, 135, 153) |
| held from | the first rotor vane r01 (h 171) | the can's end disc (REF, h 87) |
| posts | 3 at r 35: Al spacers Ø8 × 15, 15, 6, M4 | 3 at r 35: steatite standoff Ø16 × 30, Al spacers Ø8 × 15, 15 |
| angles, side A | 46.3°, 166.3°, −73.7° (the first at the riser) | 106.3°, −133.7°, −13.7° |
| angles, side B | −88.9°, 31.1°, 151.1° | −28.9°, 91.1°, −148.9° |
| passes (11 mm off its bore edge) | Ca_04, Ca_02 | Ca_05, Ca_03 |
| fastened | M4 studs (A4) through the tabs; flush ISO 10642 screws where a face meets a working gap (r01's outer face, Ca_05 under posts 2 and 3) | M4 studs; flush ISO 10642 on Ca_02's outer face; M4 button heads from inside the can into the standoffs |

- **The tabs:** each is the hull of a lobe R8 round its post and a 24 mm chord on the plate's bore, 391 mm² in the bore
  (`tab_outline()`). Their outline has no convex corner where it meets the bore.
- **The riser** (node 1 / 4) now ends under its comb's first post at Ca_05 (h 126), 45 mm shorter than before. Its
  ring lug sits under a button-head screw inside a silicone boot (R9 × 8). The tap (node 2 / 3) lands on Ca_06's
  underside as before. Its lug is clamped by a flush M4 screw from Ca_06's top, inside its own boot. So neither leaves
  bare metal below the plates, and the 39 mm from Ca_06 to the deck's parts stays the bare clearance.
- **C1 / C2, rotor:** G10 rings r 20.5–32 × 15, five per stack; three G10 dowels Ø5 at r 26.25 (90°, 210°, 330° in
  the vanes' frame) through all six vanes and the rings; the stack bonded on the sleeve. r01 carries the node-1
  comb's three posts in flush countersinks on its outer face.
- **C1 / C2, stator:**
  - six lugs at 30° + k·60°, each the hull of R9 round its rod at r 173 and a 28 mm chord on the ring;
  - six glass-epoxy threaded rods M8 at r 173;
  - G10 spacer tubes Ø16 / 8.5: 15 mm between the vanes and 12 mm from the last vane to the spider;
  - a G10 end ring r 166–182 × 10 bonded in the cage's bore under the first stator vane;
  - glass-epoxy nuts M8 at both ends: under the end ring and on the spider's outboard face.
- **The cage:** G10 r 182–186, |h| ≤ 299, as long as before; its bore locates the lugs. The Ca|reluctance spiders grow
  to r 182 and take the rods.

## 2. The HV rules at the new interfaces [IR: `sim/parts_first_cut.py` via `sim/multiplier_layout.py`]
The working voltages are the layout's steady state as built (`sim/multiplier_layout_results.json` volts.pairs).

| interface | pair, kV pk / rms | need | available | |
|:--|:--|--:|--:|:--|
| a node-1 post ↔ the nearest node-2 post, bare air | 1–2, 13.18 / 12.28 | 24.7 mm (case A) | 27.0 mm | ✔ |
| a post ↔ the other comb's bore edges, bare air | 1–2, 13.18 / 12.28 | the field (§3) | 11.0 mm | ✔ §3 |
| a node-2 standoff, along glazed steatite | 2–0, 4.52 / 3.14 | 6.5 mm (inorganic: = clearance) | 30 mm | ✔ |
| the same in PTFE (the alternate) | 2–0 | 19.7 mm (group I × 1.25) | 30 mm | ✔ |
| Ca_06's tabs ↔ the can's disc, air | 2–0 | 6.5 mm | 30 mm | ✔ |
| the node-1 comb's lowest metal (Ca_05) ↔ the can's disc, air | 1–0, 13.18 / 9.87 | 24.7 mm | 39 mm | ✔ |
| the sleeve's PTFE cover (no node-1 metal on it below r01) | 1–0 | 61.7 mm | 84 mm | ✔ unchanged |
| a rotor-vane spacer ring (G10) ↔ the stator blades' inner ends | 1–0 | 12 mm (the rim rule) | 18 mm | ✔ |
| the rotor rims ↔ the stator stack's G10 tubes | 1–0 | 12 mm | 15 mm | ✔ |
| the Ca and r01 rims ↔ the G10 end ring and its nuts | 1–0 | 12 mm | 15.5 mm | ✔ |
| the decks' outermost housings ↔ the cage (now r 182) | ea–0, 14.94 | 12 mm | 32 mm | ✔ (was 13) |

- **No support touches two adjacent plates** [OC: `rules()` touches]. Every node-1 segment touches only node-1 plates
  and passes one node-2 plate, and the same holds for node 2.
- **The posts' gap to the other comb's bore edges (11 mm)** is not a case-A clearance. The column's own plates hold the
  same 13.2 kV across 6 mm, and the record judges its gaps by the field, not by Table F.2. So the field decides it
  (§3).
- **The stator stack's insulators** (G10 tubes, glass-epoxy rods and nuts, the end ring) touch only REF metal (the
  stator vanes) and G10, so no creepage path joins two nets.

## 3. The fields at the new edges [OC: the solves; RH: Peek's surface factor]
The record's rim criterion is Peek's corona onset on a handled surface (m 0.85, `sim/vane_matrix.py`), above the peak
the edge holds (`sim/vane-matrix-findings.md` §2). A full round R1.5 (the 3 mm plates) has its onset at 47.3 kV/cm;
the Ø8 post's surface has its onset at 39.2 kV/cm.

| edge | model | peak field | margin (onset / peak) | onset voltage |
|:--|:--|--:|--:|--:|
| **the C1 rims** (the record's): a rotor rim between the stator rings | `sim/vane_cell.py` edge_field(3, 6) at 1–0 13.18 kV | 44.6 kV/cm | **1.061** | 14.0 kV |
| the column's own rims, ending together | aligned rims, the stack alternating | 33.0 kV/cm | 1.432 | 18.9 kV |
| **a bore edge under the other comb's tab**, its post 11 mm in front (a wall) | edge_field's geometry, the wall at 11 mm | 45.0 kV/cm | **1.052** | 13.9 kV |
| the same edge, the post's hole all round (axisymmetric) | post through a hole | 39.9 kV/cm | 1.184 | 15.6 kV |
| the post's own surface | the same solve | 9.6 kV/cm | 4.07 | 53.6 kV |

- **Where one comb's tab crosses the other's bore edge, that edge runs between two continuing planes.** This is the
  C1 rims' geometry, so the crossing costs the column's edge its aligned margin (1.43) and gives it C1's (1.05–1.06).
  The facing post costs another 0.009 at 11 mm.
- **The real edge lies between the two models.** The bore's curvature (r 50) wraps the edge partly round the post. The
  wall is the bound.
- **The margin against the post's distance** (fig. (d)):

| post's surface to the edge | 5 | 6 | 7 | 8 | 9 | 11 | 13 | 15 | 20 mm |
|:--|--:|--:|--:|--:|--:|--:|--:|--:|--:|
| margin (wall) | 0.886 | 0.951 | 0.993 | 1.019 | 1.035 | **1.052** | 1.060 | 1.063 | 1.065 |

  Below 7 mm the onset falls under the peak, so r 35 with Ø8 posts leaves 4 mm of margin in placement.
- **The crossings are 3 + 3 tabs × 2.5 faces a side** (Ca_06 and Ca_01 have the other comb on one face only). That is
  360 mm of edge at C1's margin per side.

## 4. Ca and the strays
- **Ca** [OC: the overlap; 2-D: the fringe; RH: the width]:
  - each tab lies in the bore, where the other comb has no metal, so the overlap does not change;
  - at a crossing the edge gains 0.00511 pF per mm (both faces, the 2-D charge against the aligned rims). Over 15
    crossings of 24 mm that is +1.84 pF;
  - **Ca = Cb = 482.3 pF, 1.072 C_max** (as laid out 480.5, 1.068). The DECIDED rule's 1.1 C_max (495 pF) still
    needs a sixth gap, as `sim/tube-strays-findings.md` §4 found.
- **The strays** [RH: `sim/multiplier_layout.py`'s formulas; each comb's three columns of posts and tabs as wires of
  the lobe's radius to the shaft under its sleeve, an upper bound since the plates screen them]:

| node | part | pF |
|:--|:--|--:|
| 1 / 4 | the comb's three columns | +4.45 |
| | the riser, 45 mm shorter in the bore | −0.65 |
| | **in all** (70.80 → 74.61) | **+3.81** |
| 2 / 3 | the comb's three columns | +3.86 |
| | the three steatite standoffs (ε 6, between their inserts) | +0.44 |
| | Ca_06's tabs over the can's disc | +0.35 |
| | **in all** (13.66 → 18.30) | **+4.64** |

## 5. The circuit with the mounts [OC: the deck]
`sim/multiplier_layout.py` run_deck at the pick (C3–C6 180 pF), the layout's deck strays, Ca scaled by 482.3 / 480.5:

| | the layout | with the mounts |
|:--|--:|--:|
| start-up gain (40 cycles, clamps out) | 1.01636 | 1.01589 |
| the rings, steady (537 cycles, settled) | ±16.248 kV | ±16.239 kV |
| the null's field | 8.273 kV/cm | 8.268 kV/cm |

- **The gate:** this copy of the deck gives the layout study's own rows to the last digit (z 1.0163615580, rings
  16.24762702 kV).
- **The mounts cost 0.00048 of start-up gain and 9 V on the rings.**
  - This is far below the record's price for its bare doubler (0.0027 of z per pF on nodes 1 and 4 together,
    `sim/tube-strays-findings.md` §5), which would make 3.8 pF cost 0.010.
  - That price belongs to the record's doubler; the proposal's own deck (`sim/multiplier-layout-findings.md` §6) is
    the measure for the layout, and it is what the rows above run.

## 6. The masses and the shafts [IR: the drawn solids; OC: the beam model]
From the drawn solids (`sim/bridge_ring_bearings.py` solids_parts, without and with the mounts), per machine:

| part | body | n | kg |
|:--|:--|--:|--:|
| G10 spacer rings between the rotor vanes | rotor | 10 | 0.510 |
| steatite standoffs | rotor | 6 | 0.101 |
| Al spacers Ø8 × 15 / × 6 | rotor | 24 / 6 | 0.049 / 0.005 |
| G10 dowels Ø5 | rotor | 6 | 0.020 |
| silicone boots | rotor | 4 | 0.009 |
| the tabs (on the 12 Ca plates) | rotor | | +0.105 |
| G10 end rings | counter-rotor | 2 | 0.635 |
| G10 spacer tubes × 15 / × 12 | counter-rotor | 60 / 12 | 0.240 / 0.038 |
| glass-epoxy rods M8 / nuts | counter-rotor | 12 / 24 | 0.152 / 0.028 |
| the lugs (on the 12 stator vanes) | counter-rotor | | +0.192 |
| the spiders grown to r 182 | counter-rotor | 2 | +0.630 |
| the cage at r 182–186 (4.56 → 5.12 kg) | counter-rotor | | +0.556 |

| d, seat | f1, the layout | f1, with the mounts | modes 2, 3 with the mounts | gap change |
|:--|--:|--:|:--|--:|
| 25, stiff (2e8) | 86.1 Hz | 85.1 Hz | 158.7, 200.1 Hz | 1.6 µm |
| 25, G10 spider (0.86e8) | 82.2 Hz | 81.1 Hz | 138.5, 189.3 Hz | 1.1 µm |
| 30, stiff | 103.7 Hz | 102.4 Hz | 183.5, 269.6 Hz | 0.4 µm |
| 30, G10 spider | 95.1 Hz | 93.7 Hz | 160.9, 210.1 Hz | −0.2 µm |

- **Every row passes** (f1 ≥ 3 × 20 Hz, the gap within 50 µm).
- **The two-body model keeps the r 162 cage's bending stiffness** (`sim/shaft_bearings.py`). The tube at r 182 is
  stiffer, so its rows are a bound.

## 7. Gates
| gate | | |
|:--|:--|:--|
| G1 the HV rules and the adjacency rule | every row | ✔ |
| G2 the fields: every new edge's onset above its peak (the record's rim criterion) | 1.052, 1.184, 4.07 | ✔ |
| G3 Ca not below the as-laid-out | 482.3 ≥ 480.5 pF | ✔ |
| G4 the deck's copy reproduces the layout study; the pump starts with the mounts | exact; z 1.01589 | ✔ |
| G5 the shafts | f1 ≥ 81 Hz, every row | ✔ |
| G6 the solids (`sim/tube_geometry.py --layout`) | no clash in 1447 pairs, no sweep hit, G-LAYOUT | ✔ |

## Caveats and what is not done
- **The margin at a crossing is thin: 1.05, as C1's rims are.** The record accepts that class for the vanes, and the
  column now shares it at 360 mm of edge a side. A corona-onset test of the assembled column at 1.45 × V_op is the
  bench's to run (it adds to `docs/bench-test-rings.md`). If the edges need more margin, wider tabs or a larger post
  distance help little (fig. (d): +0.013 at 20 mm). A thicker plate's larger full round raises the onset;
  `sim/vane-matrix-findings.md` §2 tabulates it by thickness.
- **The field models are 2-D and axisymmetric.** The wall bounds the crossing and the hole the post; a 3-D solve of
  one tab is not done.
- **The strays are formulas** [RH], an upper bound for the columns. The record's 3-D solve
  (`sim/tube_strays.py`) is not re-run with the tabs.
- **The steatite standoff is a custom part:** no catalogue part was found at Ø16 × 30 with M4 threads. Abbatron's
  glazed standoffs run 1/2–5/8 in with 6-32 / 8-32 threads. It is drawn as DCCREG-CAP-617 for a technical-ceramics
  maker; PTFE is the alternate (it creeps; the 30 mm hold 19.7 mm of PTFE creepage).
- **The cage moves out to r 186 (Ø372, was Ø332),** and the counter-rotor is 2.47 kg heavier (§6).
- **Bonding:** the rotor-vane stack is bonded on the sleeve and to its rings (structural epoxy), the end ring into the
  cage, the spiders into the cage. The bond's shear area, the vanes' bores and the rings' faces, is far above the
  loads; it is not analysed.
- **Not changed:** the vanes, the plates and the gaps (C1's κ and Ca's overlap stand); the deck; the hub.

## Notes against the record
- `sim/tube_geometry.py`: "connection and mounts not drawn" (the Ca plates). They are drawn now (`LayoutMachine`, with
  mounts).
- `sim/parts-first-cut-findings.md` §4, the Ca mounts' first cut: node-1 plates on the rotor vanes' stack, node-2
  plates on 3–6 rods near the rim, the node-1 plates notched round them.
  - In the layout Ca holds 13.2 kV, against the record's 7.45 kV peak. A notch then needs 24.7 mm of case-A clearance:
    three notches of R 30.7 round Ø12 rods at r 140 cut 6250 mm², about 10 % of every notched plate [OC: the
    circles' area inside r 150].
  - The bore posts here notch nothing. The record's correction (insulating spacers, or the plates clear of the
    sleeve) holds: no node-1 metal touches the sleeve.
- `sim/multiplier_layout.py` interfaces, "the decks' outermost housings <-> the cage": 13 mm becomes 32 mm with the
  cage at r 182.
