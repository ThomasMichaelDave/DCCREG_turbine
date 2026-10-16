# S2a, step 2 — the tube as solids for the S1b circuit, from scratch: findings

**Source:** `rebuild/s2_models/s2_geometry.py` → `s2_geometry_results.json`. The model files are in
`rebuild/s2_models/geometry/`, under the name `s2-tube-s1b-from-scratch`:
- `.step`: 138 instances of 59 products, read back whole;
- `.parts.json`: every solid with its net;
- `.FCStd`: written through FreeCAD's GUI program, so its parts display;
- `-view.png`: a still of that document.

**Status:** PROPOSED (2026-10-16), for the designer's review.

**Why from scratch** (the designer, 2026-10-16): "we explicitely agreed to build from scratch, then why am I seeing the
entire build again with reluctance sections and all?"
- **What went wrong first:** the first S2a model subclassed the 10-11 redesign's whole machine. It carried the
  magnetic pump, the AH, the grounded can, the redesign's mounts, its bearings and its frame, none of which a rebuild
  stage has earned.
- **That model is withdrawn.** Its findings rested on those parts: the column bound by the can's disc, and 994 mm.
- **This model follows the rule of addition** (`rebuild/README.md`): what the S1b circuit needs, plus the bare minimum
  of mechanics.

**The designer's choices for it (2026-10-16):**
- bare-minimum mechanics;
- no can round the hub;
- the decks beside the hub;
- the hub without its AH (the magnetic pump is not earned yet).

## Headline

**The S1b circuit's tube is 580 mm long, 142 solids** (with bracket B) (h = |z| from the hub's centre, per side):

| h (mm) | what | net |
|:--|:--|:--|
| 0–80 | the hub as locked, without the AH: the vessel at the 2 mm wall, ring A / B and their beads (the core's electrode pair), the gel, the PEEK retainer, the G10 coupler, the flanges (h 72–80) | N1 / N4 (the rings), REF (the flanges) |
| 30–78 | the deck beside the hub, on the coupler: layout V1b (`s2-deck-symmetry-findings.md`), two-fold symmetric, deck B deck A turned 180°. The sticks opposite each other, the clamp halves opposite each other, each against the stick end it joins, the midpoint ring; on the rules of `s2_deck.py --bare-can --no-can` | N1–N3 / N2–N4, REF |
| 0 | the cross wires' support, bracket B in V1b's form: a split G10 collar on the coupler, two G10 arms on opposite sides with one wire each, four mica barriers across each | — |
| 91–139 | Ca (Cb): the record's six plates, node 2 toward the deck | N2 / N1 (N3 / N4) |
| 145–247 | C1 (C2): the record's 6 + 6 vanes (the stack S1's values come from), side B's rotor vanes half a pitch on | N1 (N4) / REF |
| 265–280 | the REF link: a bearing on the shaft and an Al spider to the stator carrier (the 2026-10-08 decision, a placeholder) | REF |
| 80–290 | the shaft (REF) in its G10 sleeve; the G10 carrier tube for the stator vanes | REF / — |

**The gates:**
- G-CLASH: no two solids share volume (279 pairs tested).
- G-SWEEP: no counter-rotor solid in a rotor solid's swept volume.
- G-AIR: every two conductors of different nets clear their peak's bare clearance. The 6 mm cells and the potting are
  excepted; diode bodies are graded along their axes.
- G-POT: inside the potting, every two conductors of different nets are at least U / 2 kV/mm apart, the midpoint ring
  included.
- Every net reaches its conductors.

**G-CREEP fails:** the rotor sleeve's surface is too short from the rotor vanes to REF at both ends (finding 3). This
is evidence for an addition, the designer's call.

## Findings

1. **Each element's place is set by its own clearance** [OC: the rule, IEC 60664-1 case A at 1.5 × the peak]:
   - **The column's node-2 plate at h 91**, bound by the deck's parts (13 mm off them). The flange allows N2 at h 80
     and N1's first plate at h 87.7.
   - **The REF link's bearing at h 265:** 26 mm of air beyond the outermost rotor vane (N1, 13.8 kV).
   - **The ring leads** leave the coupler below the deck, run out under its plate and come up into the N1 / N4
     junction from below. Up the coupler's face they passed 4.5 mm from the flange (REF) at 13.8 kV.
   - **The decks' REF straps** run low (h 60) and climb only beside the coupler to the brass terminals into the
     flange (h 74.5). At h 76 they passed 22.5 mm from the column's first node-1 plate, against 26.1 mm needed.
2. **What the model leaves OPEN** (each needs design, not a placeholder; the field solve gives every conductor its
   net from the parts list, so it does not need them drawn):
   - the ties between the plates of one net: the column's node-1 and node-2 plates, the rotor vanes to the column,
     and the stator vanes' REF bus;
   - the column's mechanical support;
   - the riser and the tap from the deck to the column;
   - the deck plate's fixing on the coupler;
   - the joint between the counter-rotor's two halves;
   - the drive.
3. **G-CREEP, the rotor sleeve.**
   - The rotor vanes' rings (N1 / N4) sit on the G10 sleeve. Its surface runs to REF at both ends: the coupler's end
     at the flange, and the REF link's bearing.
   - The rule (the redesign's, `sim/doubler_caps.py` rules()) is IEC 60664-1 PD2 × 1.25 DC on the rms, 9.64 kV.

     | path | available | needed on G10 (IIIa) | needed under a PTFE cover (I) |
     |:--|:--|:--|:--|
     | the first rotor vane → the flange | 65 mm | 121 mm | 60 mm |
     | the outermost rotor vane → the bearing | 27 mm | 121 mm | 60 mm |

   - The evidence's answer was a PTFE cover over the sleeve with sheds (`sim/multiplier-layout-findings.md` §4).
   - Here it would be an addition with this evidence behind it. The designer decides.

## The decks and the bracket in V1b (2026-10-16)

The designer: "Implement v1b".
- **The decks:** deck A and deck B as `s2_deck_symmetry_results.json` V1b.
  - Each deck's static residual is 41 g·mm (V0: 268); the couple is 5,000 g·mm² (V0: 18,100).
  - The S2a rotor is 13.9 kg, so ISO 1940 G2.5 at 600 rpm allows 552 g·mm in all.
- **The cross wires** sit on opposite sides of the hub, 142 mm apart, at 28° and −152°.
- **The bracket:** each G10 arm (r 39–81, 19 × 6 mm) carries one wire. The barriers across it are counted for this
  deck's wire radius (r 71): the plain path of 30.6 mm needs four barriers, for 94.6 mm against the 84.2 mm needed.
  The study's three were for the earlier deck's r 84.
- **G-POT:** the potting rule holds for every conductor pair inside it, the midpoint ring included.
- **Every gate passes, except G-CREEP on the rotor sleeve,** which stays OPEN for the designer.

## The structural pass (2026-10-16)

The structure, the outer retainer and the integrity checks are in `s2-structure-findings.md`. The model is now 339
solids and 848 mm long. Every gate passes, the sleeve's G-CREEP included, now with the cover and sheds.

## Next

- **The designer's review in FreeCAD,** and the decision on the sleeve's creepage.
- **S2b, the field solve on this model:** C1(θ), C2(θ), Ca, Cb, C_k and the strays from the parts list, with
  `sim/tube_strays.py`'s finite-volume method.
