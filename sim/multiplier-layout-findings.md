# The multiplier stacked into the doubler, laid out in the machine — findings

**Source:** `sim/multiplier_layout.py` → `sim/multiplier_layout_results.json` (24 ngspice runs, the record's hub
solver twice, the record's shaft model 19 times; about 5 minutes on 4 processes). The drawing is
`docs/figures/multiplier-layout.png`, drawn by `docs/make_multiplier_layout.py`.

**The brief** (the designer, 2026-10-11): "This unipolar setup will do for now, lay out the doubler capacitors in the
multiplier top and bottom of the machine stack. Propose placement of the diodes. A mechanical layout."
- **Read here as:**
  - the setup is the proposal of `sim/integrated-multiplier-findings.md`: each chain one polarity, ring A's side
    negative and ring B's positive, as drawn in `docs/schematic-integrated-multiplier.svg`;
  - its capacitors go in the stack, side B's on top and side A's below.
- **If "unipolar" meant one polarity for the whole circuit:** the capacitors' places below stay. Only the diodes'
  directions change, together with the ring stages and the vanes' clocking.

**Status:**
- **DECIDED for now** (the designer, 2026-10-11): the circuit, as above.
- **PROPOSED** here: the whole layout. That covers:
  - the order of the stack;
  - the decks and their plans;
  - the grounded can;
  - the hub-face bearings removed;
  - the trim of the clamp strings.
- **Tags:**
  - [OC]: the circuit's deck, the record's hub solver and shaft model, and the geometry's arithmetic;
  - [IR]: the record's clearance and creepage method (`sim/parts_first_cut.py`), the potting's rule, the plan;
  - [RH]: the parts' envelopes (datasheet-class shapes, to be taken from the parts chosen) and the layout's strays,
    from line, cylinder and plate formulas; no field solve.

## Headline
- **The stack, per side, from the hub outward** (side A below, side B its mirror; |z| from the hub's centre):

| |z| (mm) | what | body |
|:--|:--|:--|
| 0–72 / 72–80 | the hub as locked (PEEK retainer, G10 coupler to r 33), the shaft half's flange | rotor |
| 0–85, r 46–48 | **a grounded can** over the hub: Al, on the shaft, REF; an end disc at 85–87 | rotor |
| 30–36 / 36–78 | **the deck**: a G10 ring plate, r 50–150, carrying every diode, C3–C8, Csa / Csb and the clamp string, each part potted | rotor |
| 117–165 | **the column**: Ca (Cb), the record's six plates (481.6 pF), node 2 (3) toward the deck, node 1 (4) outward | rotor |
| 171–273 | **the vane stack**: the record's 6 + 6 with its ends swapped, a rotor vane (node 1 / 4) at its hub end, a stator vane (REF) outward | rotor / counter-rotor |
| 289 | the Ca\|reluctance bearing on its spider (the record's 272) | — |
| 299–487 | the reluctance section and the end bearing, as the record | rotor / counter-rotor |

  - **The length:** 974 mm against the record's 940, +17 mm a side.
  - **No hub-face bearings.** The counter-rotor rides on the two Ca|reluctance bearings.
- **Why no hub-face bearing** [OC: the bodies]:
  - a spider is counter-rotor: it turns at 1200 rpm against the rotor, so no rotor wire can cross its plane except
    inside the shaft;
  - nodes 1 / 4 cannot run in the shaft. A PTFE HV wire in an 8 mm bore takes 37 pF/m: 3.0 pF on the 80 mm path
    under a bearing, which costs 0.008 of z at the record's price of a pF on nodes 1 and 4 together
    (`sim/tube-strays-findings.md` §5). The proposal starts at z 1.014;
  - the record has the same flaw: its D3 / D4, chains and rings need the vane bays and the hub bay joined, and its
    hub-face spiders separate them.
- **The diodes' placement:**
  - each side's deck holds the six diodes that touch its own nodes: deck A has D1, D3, D5, D8, D11, D12 and deck B
    has D2, D4, D6, D7, D9, D10;
  - the multiplier's capacitors go to the deck of the nodes they join. Deck A holds C3 (2–l1), C6 (r1–r2), C8
    (r2–xa) and Csa; deck B holds C4, C5, C7 and Csb;
  - **so only l1 and r1 cross between the halves** [OC]. That is the fewest any placement allows: two odd cycles of
    the ladder each force one crossing net (§2). The two are mirror nets (r1 = −l1), at −6.4…+6.4 kV.
- **Every clearance holds as if unpotted:**
  - all 78 part pairs per deck, and every part to the can, clear the record's bare clearance (1.5 × the peak);
  - the potting adds at least 16 mm of silicone on every pair, against a solid rule of at most 10.7 mm (§3);
  - the column sits 39 mm off the deck: node 2 against ring A's lead peaks at 19.5 kV.
- **The hub's field is kept:** with the can as the hub's REF boundary, the record's solver gives the field at the
  null × 0.9973 (§5). The can also screens the hub from the decks' 120 Hz swing.
- **The circuit with the layout's strays** (estimated [RH]; §6):
  - **the strays:** nodes 2 / 3 lose 10.8 pF (no plate faces the utrons now), nodes 1 / 4 gain 4.6 pF, and each new
    node carries 1.1–3.3 pF against the study's assumed 24.5;
  - **the gain:** z 1.0164 at start-up, against the study's 1.0142;
  - **the rings rise to ±16.25 kV** at the record's V_op. C3–C6 cannot bring them down (±16.08 kV even at 100 pF),
    and neither can C7 / C8 (±16.19 kV at 47 pF);
  - **trim the clamp strings to 60 parts** (V_op 11.94 kV). The rings then hold ±14.77 kV, the most within the
    record's ±14.96; a smaller part at the REF end sets the last 1 % (`sim/parts-first-cut-findings.md` §2.4).
- **The shafts need the bridge-ring bearings** (§7; the record's model, its solids moved):

  | d 25 | f1 | the utron gap under 1 g lateral |
  |:--|--:|--:|
  | the record, with the hub-face bearings | 29 Hz | −129 µm |
  | without them | **14 Hz** | **−499 µm** |
  | without them, with the record's bridge-ring bearings | 89 Hz (85 on realistic seats) | +1 µm |

  - Without the hub-face bearings, d 40 alone reaches only 26 Hz; the criterion is 60 Hz.
  - The bridge-ring bearings were one of the record's two ways out (ledger §3.1); here they become necessary.
  - Unlike the record's 131–165 Hz, 85–89 Hz sits well below the pumps' 120 Hz.

## 1. The working voltages
The pick's steady state as built (`sim/integrated_multiplier.py`'s deck, ideal diodes, C3–C6 180 pF, the record's
V_op), re-run with every node kept [OC]:
- **The gate:** the rings at ±14.934 kV, as the pick's own run.
- **The nodes** (kV, over the last eight cycles):

| node | min … max | rms |
|:--|:--|--:|
| 1 / 4 | −13.18 … −7.03 / mirror | 9.87 |
| 2 / 3 | 0 … +4.52 / mirror | 3.14 |
| l1 / r1 | −6.41 … −3.67 / mirror | 5.25 |
| r2 / l2 | −8.61 … −5.91 / mirror | 7.02 |
| xa / xb | −14.94 … −12.77 / mirror | 13.64 |
| ea / eb (the rings) | −14.94 / +14.94 | 14.93 |

- **The pairs that set the layout:**
  - ea–eb: 29.9 kV, across the equator between the decks;
  - ea–r1: 21.3 kV, on deck A;
  - 2–ea: 19.5 kV, the column's node-2 plate against the deck;
  - 1–2: 13.2 kV (rms 12.3), Ca's own gap;
  - l1–r1: 12.8 kV, the cross pair.
- **These are the record's V_op.** The trim of §6 lowers every node by 9 % and every interface gains margin, so the
  tables here are the envelope.

## 2. The diodes' placement: where each part sits and what crosses
- **The nets bound to a side** [OC]:
  - side A holds nodes 1 and 2, with the vanes and Ca, and ring A's ea;
  - side B holds nodes 4, 3 and eb;
  - xa and xb follow their rings' stages (D11 / D12, D9 / D10).
- **The rest are free:** l1, l2, r1 and r2.
- **The ladder's graph holds two odd cycles:**
  - 2–r1–r2–l1 (D3, C6, D5, C3) with node 2's surge resistor in series;
  - r2–1–xa (D8, D11, C8).
  So any placement has at least two crossing nets [OC].
- **The placement here crosses only l1 and r1:**
  - r2 and xa go to side A, l2 and xb to side B;
  - each part sits with the nets it joins. C3 (2–l1) and C6 (r1–r2) go to deck A, C4 and C5 to deck B.
- **The other placement** keeps each ladder in one column (C3, C5 on side A; C4, C6 on side B):
  - it crosses four nets: 2, 3, l2, r2;
  - and node 1 would have to pass l2's plates, 19.6 kV apart at the peak.
- **C3–C8 are discrete** [IR]:
  - each is a 180 or 100 pF class-1 HV ceramic or PP / PTFE film part, the record's chain parts' class;
  - as plates, C3 / C4 would add a third node to each column, and the record's mounting rule (no support touching two
    adjacent plates) would then cost a rod set and its notches per node, about 10 % of the plate area each;
  - C5 / C6 cannot join their column at all without an l1–r1 plate pair.
- **Ca / Cb stay plates:**
  - the record's six full annuli, 481.6 pF, unchanged, only reversed in order;
  - **their DC is now 11.6–13.2 kV**, against the record's 6.9;
  - the 6 mm gap holds it at 1.49 to breakdown, as the vanes hold V_op;
  - their mounts' creepage doubles: 77 mm on PTFE or 153 mm on G10 between adjacent plates' supports
    (`sim/parts-first-cut-findings.md` §4's method).

## 3. The decks
- **The plan** (deck A; deck B is its mirror about the bisector of A's l1 and r1 junctions, its nets mirrored, so the
  cross pair runs straight across):
  - **the outer lane, r 132:** the eight sticks lie along it as one chain, REF – R1 – 0′ – D1 – 2 – R3 – 2′ – D3 – r1 |
    l1 – D5 – r2 – D8 – 1 – D11 – xa – D12 – ea, each junction a potted block between two housings' ends;
  - **the inner lane, r 85–102:** C3, C6 and C8 stand; C8 sits under r2's junction. The clamp string Z1 is an arc
    module (66 × 1.5KE200A in a meander, its HV and REF ends at opposite ends), its HV end beyond D11 and its REF end
    under the open sector;
  - **Csa** stands beyond the chain's end (r 126);
  - **the open sector:** 44° parts ring A's ea from R1's REF end;
  - **REF:** straps to the can from R1's end, Z1's REF end and Csa's foot. The rest is joined by PTFE HV wire over the
    parts.
- **The parts' envelopes** [RH]:
  - a stick or a surge resistor: body Ø8 × 40 mm, housing Ø24 × 66 mm;
  - C3–C6 at 180 pF / 30 kV: body Ø30 × 22, housing Ø46;
  - C7 / C8 at 100 pF / 30 kV: body Ø25 × 20, housing Ø41;
  - Csa / Csb at 100 pF / 40 kV: body Ø30 × 24, housing Ø46;
  - the clamp module: body 34 × 134 × 20, housing 50 × 150 × 36;
  - every housing is 8 mm of silicone over its part (`sim/parts-first-cut-findings.md` §5).
- **The check** [IR]:
  - a lying part grades linearly from one net to the other, and the clamp string from node 1 to REF;
  - between any two pieces, the peak is bounded by the pair peaks weighted by the pieces' mixes [OC: the triangle
    inequality];
  - the bodies' distance is set against the bare clearance (1.5 × the peak, IEC 60664-1 F.2 case A as the record
    applies it) and against the potting's solid rule (the peak / 2 kV/mm).
- **Deck A** (B identical by the mirror):
  - all 78 pairs and every part to the can clear bare;
  - **the least bare margin:** D12–Z1, 0.8 mm (21.7 mm against 21.0, at 11.4 kV);
  - **the least housing gap:** D5–C8, 1.9 mm;
  - **to the cage:** the outer lane keeps 16 mm and Csa 13 mm, against the record's 12;
  - **the clamp's HV end to the can:** 25 mm against 24.7.
- **The mass and balance** [RH]:
  - each deck weighs 1.85 kg: 1.16 kg of parts and silicone and 0.70 kg of plate;
  - its centroid sits 13.3 mm off the axis, 24.6 kg·mm, equivalent to 176 g at r 140;
  - the two decks' static sums nearly cancel by the mirror, but they leave a couple. Balance them with the rotor to
    G2.5 (the record's rule), with masses on the can.

## 4. The interfaces
The record's method (`sim/parts_first_cut.py`): clearance from IEC 60664-1 F.2 case A at 1.5 × the peak; creepage
from the rms at pollution degree 2 × 1.25; group I is PTFE and silicone, IIIa is G10.

| interface | peak / rms kV | clearance | creepage PTFE / G10 | the layout gives |
|:--|--:|--:|--:|:--|
| Ca's plates, node 1 ↔ 2 (6 mm of air) | 13.2 / 12.3 | — | 77 / 153 | 1.49 to breakdown, as the vanes |
| the column's node-2 plate ↔ the can's disc | 4.5 / 3.1 | 6.5 | 20 / 39 | 30 mm |
| the column's node-2 plate ↔ the deck's parts | 19.5 / 17.7 | 38.9 | 110 / 221 | 39 mm (sets the column) |
| node 1's riser ↔ the node-2 plates' bores | 13.2 / 12.3 | 24.7 | — | PTFE HV wire ≥ 20 kV DC, 13 mm off |
| the decks ↔ the cage (G10, not REF) | 14.9 | — | — | 13 mm (the record keeps 12) |
| deck A ↔ deck B, across the equator | 29.9 / 29.9 | 67.2 | 187 / 373 | 72 mm |
| the cross nets ↔ the can | 6.4 / 5.2 | 10.4 | 33 / 66 | 82 mm |
| a ring's lead ↔ the can's wall | 14.9 | 28.8 | — | a PTFE bushing; the lead's insulation continuous |
| the sleeve under the column: the first rotor vane ↔ the can's disc | 13.2 / 9.9 | — | 62 / 123 | 84 mm: **PTFE over the sleeve** |
| the sleeve's outer end: the last rotor vane ↔ the Ca\|reluctance bearing | 13.2 / 9.9 | — | 62 / 123 | 17.5 mm: **two 12 mm PTFE sheds** (65.5 mm) |

- **The sleeve's two rows** are the record's own open point, "the G10 sleeve's ends"
  (`sim/parts-first-cut-findings.md` §4).
  - The record's hub-end rotor vane sat 11.5 mm of sleeve from its hub-face bearing.
  - Here the hub side has 84 mm, so a PTFE cover suffices. The outer end has 17.5 mm and needs the sheds.
- **Not drawn here:**
  - **Ca / Cb's mounts:** the record's rods and notches, now at 25 mm of clearance (13.2 kV) where the record had
    13 mm;
  - **the riser's standoffs:** PTFE, from the column's own structure, not the sleeve;
  - **the decks' plate to the can:** PTFE ribbed standoffs;
  - **the potting's PD test:** < 10 pC at 1.25 × the working voltage, the record's acceptance.

## 5. The grounded can and the hub's field
- **The solve:** the record's hub solve (`sim/hub_beads_settled.py` hub_solve, each band edge its own bead in its
  groove, h 0.25 mm), with the can as the hub's REF boundary (r 46, |z| 85) in place of the record's box (the cage at
  r 162, a vane at |z| 110) [OC]:
  - **the field at the null per kV:** 0.25458 → 0.25390 (× 0.99735). At the trimmed rings, ±14.77 kV, that is
    7.50 kV/cm, against the record's 7.62 at ±14.96;
  - **each ring's capacitance to REF:** 6.05 → 7.21 pF, and ring to ring 1.44 → 0.99 pF. Both sit behind diodes and
    beside Csa's 100 pF.
- **The can's size against the field at the null** (the same solve):
  - × 0.99925 for a can at r 58, × 0.99991 at r 88, × 0.99999 at r 160;
  - the can's length does not matter: |z| 85 or 100 gives the same;
  - the AH cores and the flanges hold most of the hub's REF.
- **The can is what keeps the hub "untouched"** [IR]:
  - the decks' nodes swing ±3 kV at 120 Hz within 50–150 mm of the null;
  - the record's model has nothing there but REF;
  - the closed can restores that boundary.
- **The rings' leads:**
  - each leaves its equatorial bead along the normal through the PEEK and the coupler, as `docs/rings-design.md` §2
    has it;
  - it runs along the coupler to |z| about 50, then out through the can's wall in a PTFE bushing to Csa on its own
    deck;
  - ring A's lead and ring B's never share a surface.

## 6. The strays, and the circuit with them
- **Per node, against the as-built set** (`sim/tube_strays_results.json`) [RH: the parts as cylinders near the can;
  the riser as a wire in the bore over the shaft's G10 sleeve; no field solve]:

| node | what changes | pF |
|:--|:--|--:|
| 1 / 4 | the riser (bore 1.34, to the deck 0.88), the clamp string (a third of its body, by its gradient: 1.45), D8 / D11 halves, the junction | +4.6 |
| 2 / 3 | the record's utrons and bearings no longer seen (−14.08), the deck's parts, the tap, the can's disc's fringe (1.0) | −10.8 |
| l1 / r1 | the parts on both decks, the junctions, the cross wire (0.70) | 3.3 each |
| r2 / l2, xa / xb | the parts and the junctions | 1.5, 1.1 |

- **The circuit** (`sim/integrated_multiplier.py`'s deck as built, ideal diodes) [OC: the deck; RH: its inputs]:

| | C3–C6 | the rings at the record's V_op | z at start-up |
|:--|--:|--:|--:|
| the study's strays (24.5 pF on each new node) | 180 pF | ±14.93 kV | 1.0142 |
| the layout's strays | 180 pF | ±16.25 kV | 1.0164 |
| | 150 / 120 / 100 pF | ±16.26 / 16.16 / 16.08 kV | 1.0157 / 1.0147 / 1.0137 |
| the layout's, C7 / C8 at 68 / 47 pF | 180 pF | ±16.22 / 16.19 kV | 1.0163 / 1.0162 |
| **the layout's, the clamps of 60 parts (V_op 11.94 kV)** | 180 pF | **±14.77 kV** | 1.0164 |
| the clamps of 59 / 61 / 62 parts | 180 pF | ±14.52 / 15.02 / 15.26 kV | 1.0164 |

- **What sets the rings' level** [OC: the runs]:
  - the clamps' V_op does, almost wholly: each 200 V part moves the rings 1.6 %;
  - the strays on the new nodes move it too, since the study's 24.5 pF held them down;
  - C3–C6 and C7 / C8 barely move it.
- **The trim:**
  - **60 parts** hold the rings at ±14.77 kV, 1.3 % under the record's level;
  - a lower-voltage part at the REF end takes them the rest of the way, as the record trims (bench, warm);
  - the study's C3–C6 rule (the largest that keeps the rings at the record's level) finds no value with these strays;
  - **C3–C6 stay at 180 pF,** where z is highest.
- **The real sticks:** the start-up gain rises from 1.0142 to 1.0164, so the study's real-stick start-ups (typical,
  maximum and hot leakage) can only improve with the layout. They were not re-run.

## 7. The shafts without the hub-face bearings
- **The model:** `sim/shaft_bearings.py`'s two-body model of record [IR], with its solids moved to this layout:
  - side A's reluctance section and bearings stay; side B's move out 34 mm;
  - the vanes and the Ca / Cb plates go to their new places, the hub moves 17 mm;
  - the hub-face bearings and their spiders are out;
  - one cage tube spans the two Ca|reluctance spiders;
  - the sleeve, the can and the decks (1.85 kg each) come in.
- **The masses:**
  - the rotor goes from 33.4 to 36.8 kg;
  - the counter-rotor goes from 33.1 to 30.8 kg.
- **The gate:** the record's own solids give d 25 at 28.57 Hz, as the record's row.

| shaft | bearings | f1 / f2 / f3 (Hz) | the utron gap, 1 g lateral | the record's f1 |
|:--|:--|:--|--:|--:|
| d 25 | Ca\|reluctance only | 14 / 37 / 112 | −499 µm | 29 |
| d 30 | Ca\|reluctance only | 19 / 54 / 145 | −270 µm | 40 |
| d 40 | Ca\|reluctance only | 26 / 92 / 213 | −141 µm | 65 |
| d 25 | + bridge-ring bearings, stiff seats | 89 / 179 / 210 | +1 µm | 165 |
| d 25 | + bridge-ring bearings, realistic seats (0.86e8 N/m) | 85 / 154 / 201 | +0 µm | 136 |
| d 30 | + bridge-ring bearings, stiff / realistic | 107 / 98 | 0 / −1 µm | 176 / 142 |
| d 40 | + bridge-ring bearings, stiff / realistic | 127 / 107 | −1 / −1 µm | 182 / 146 |

- **Without the hub-face bearings the central span is unsupported.**
  - The counter-rotor's weight goes to the shaft only at the Ca|reluctance bearings, and the hub's and the decks' at
    the flanges.
  - The utron gaps (0.5 mm) would close under 1 g.
- **The bridge-ring bearings** (a bearing between the shaft and each bridge ring's outer end, the record's §3.1 way
  out) take that load to the frame's end of each section.
  - With them, d 25 meets the criterion (3 × the bodies' 20 Hz relative speed).
  - Its first mode sits 29 % under the pumps' 120 Hz, where the record's was 9 % over.
  - The layout grows 10–20 mm a side for them (ledger §3.1); not counted in the 974 mm.
- **The REF link:** now through a Ca|reluctance bearing. The proposal draws 0.02 µA through it, so the counter-rotor
  could float (`sim/integrated-multiplier-findings.md` §6).
- **The magnetic pump's low-voltage leads** (the AH coils to La / Lb, D1*–D4* and the utrons):
  - they cross the Ca|reluctance spiders in an 8 mm bore in each shaft half: from the flange's face, under the
    bearing, out radially in the reluctance bay;
  - low voltage, so the bore's strays do not matter, and the bore costs 1.0 % of the shaft's stiffness ((8 / 25)⁴);
  - the record leaves these leads unrouted.

## Gates
| gate | result | pass |
|:--|:--|:--|
| the working voltages: the pick's steady run reproduced | rings ±14.934 kV, as `sim/integrated_multiplier_results.json` pick.steady | ✔ |
| the shaft model: the record's solids at d 25 | 28.57 Hz, as `sim/shaft_bearings_record_results.json` | ✔ |
| the hub solve: the record's box | k 0.25458, as `sim/hub_rings_build_results.json` record | ✔ |
| the decks' plan: every pair, potted and bare | 78 / 78 per deck | ✔ |

## Caveats
- **The strays are estimates** [RH]. The rings' level rests on them, which is why the clamps are trimmed on the
  bench. A field solve of this stack (`sim/tube_strays.py` on the new elements) would settle them.
- **The parts' envelopes are datasheet-class shapes** [RH]. Take the decks' plan again from the parts chosen.
- **Not run:**
  - a vane flashover with the ring stages;
  - the decks' own field (the parts' rims inside the potting);
  - the varicaps' torque at the gear.
- **The vanes' and Ca's strays:** taken as the record's solve (66.2 pF on node 1) in the stack's mirrored order.
- **The can at r 48 is a compromise** [IR]:
  - at r 58 the field at the null would move −0.075 % instead of −0.27 %;
  - but the inner lane would then sit 10 mm closer to the can, and the clamp string's HV end would rest on its
    potting alone.
- **The record's §3.1 numbers for the bridge-ring bearings** (131–165 Hz) are the record's stack; this stack gives
  85–89 Hz.

## What contradicts or updates the records
- **The ledger §3.1** ("the four inner ones join rotor and counter-rotor"): here there are two inner bearings, the
  Ca|reluctance ones, plus the bridge-ring bearings.
- **The ledger §3.1** names d 40 or the bridge-ring bearings as the ways out of the shaft's low mode. Without the
  hub-face bearings, d 40 no longer suffices.
- **The rings' level:** `sim/integrated-multiplier-findings.md` assumed 24.5 pF on each new node. Laid out compactly
  they carry 1–3 pF, and the clamps must be trimmed from 66 to about 60 parts.
- **The record's layout** never routed its rotor wiring across the hub-face spiders, nor the magnetic pump's leads
  across the Ca|reluctance ones. This layout routes both.
- **`sim/shaft_bearings.py`:** its density table lacked the shaft's renamed material ("austenitic stainless"), so
  `--record` no longer ran. The key is added at the record's steel figure, so the record's results stand
  (CHANGELOG).
