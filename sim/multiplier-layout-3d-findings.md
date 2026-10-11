# The multiplier laid out in the machine, in solids — findings

**Source:** `sim/tube_geometry.py --layout` → `sim/tube_geometry_layout_results.json`, with
`docs/geometry/tube/tube-r150-n6-air6-wound-g0p5-6br-hub50-layout.{step,glb,parts.json}` and the exact-section render
`…-layout-section.png` (about a minute). The 3-D stills (`…-layout-3d-{cutaway,bay,deckB}.png`, and the circuit's
potentials in `…-3d-bay-potential.png` and `…-3d-deckB-potential.png`) are by `tools/step-viewer/shoot.py`.
The interactive viewer is `tools/step-viewer/layout.html`, built by `tools/step-viewer/make_layout_data.py`
(published as the "DCCREG Wound Tube" artifact).

**What it is:** the PROPOSED layout of `sim/multiplier-layout-findings.md`, in solids. The source is
`sim/multiplier_layout_results.json` (the stack, both decks' plans) and the study's own constants (its leads, straps
and mirror). The record supplies the rest: its hub, column plates, vanes and reluctance sections, through
`record_plates()`. Nothing is redrawn by hand.
**Status:** PROPOSED, as the layout.
**Tags:** [OC] the solids' geometry; [IR] the routing chosen here; [RH] the parts' envelopes and the junctions.

## Headline
- **378 solids from 142 prototypes; 974 mm, the hub's centre at z 487** (z from side A's end):

| \|z\| from the hub (mm) | per side, as drawn | body |
|:--|:--|:--|
| 0–72 / 72–80 | the hub as locked; the shaft halves' flanges, turned to Ø60 inside the coupler (`docs/rings-design.md` §2) | rotor |
| 0–87 | the can: Al, r 46–48, its end discs, a PTFE bushing for its ring's lead | rotor (REF) |
| 30–36 / 36–78 | the deck: the G10 plate; every part of the study's plan, potted | rotor |
| 117–165 | Ca / Cb: the record's six plates, node 2 / 3 toward the deck | rotor |
| 171–273 | C1 / C2: the record's 6 + 6 vanes, a rotor vane at the hub end, **C2 in phase with C1** (no half-pitch offset) | rotor / counter-rotor |
| 289 | the Ca\|reluctance bearing and its spider; one cage from spider to spider | — / counter-rotor |
| 299–487 | the record's reluctance section and end bearing (side B's moved out 34 mm) | rotor / counter-rotor |

- **The decks, part by part** (from `sim/multiplier_layout_results.json` decks; deck B the mirror):
  - lying sticks and surge resistors: the study's capsule (Ø24, 66 mm) round a Ø8 × 40 body, with its leads;
  - C3–C8 and Csa / Csb: standing housings round their bodies, with M5 studs top and foot;
  - the clamp string: an arc module round its body;
  - the ten junctions: a brass terminal in a potted block;
  - the leads run over the parts at |z| 76.5, the REF straps run to the can on the plate.
- **The wiring, as routed here** [IR]:
  - **node 1's riser (4's):** up from its junction to |z| 101.5, in to r 35, up the column's bore to the first rotor
    vane;
  - **node 2's tap (3's):** straight up to the column's node-2 plate;
  - **the cross nets l1 and r1:** straight across between the decks, through the plates' holes;
  - **each ring's lead:** from its equatorial bead along the normal through channels in the PEEK and the coupler,
    along the coupler at r 36 to |z| 57, out through the can's bushing, to its Cs's top;
  - **the magnetic pump's LV cable:** in an 8 mm bore in each shaft half, from the flange's face out radially at
    |z| 306, between the Ca|reluctance bearing and the inner carrier disc;
  - **the sleeve:** its PTFE cover under the column, and two 12 mm PTFE sheds at its outer end.
- **Every gate passes:**
  - no two solids share volume;
  - no rotor solid sweeps a counter-rotor one;
  - the utrons' gaps are the record's;
  - every deck pair matches the study's plan (G-LAYOUT).

## Gates
| gate | result | pass |
|:--|:--|:--|
| G-TUBE-CLASH: no two solids share volume (except the intended joins) | 1129 pairs tested, 0 clashes | ✔ |
| G-TUBE-SWEEP: no counter-rotor solid in the volume a rotor solid sweeps | 0 hits | ✔ |
| G-TUBE-WOUND: the utrons' air gap and clearances, the record's | 0.5 mm aligned, 9.74 mm unaligned, the winding 1.0 mm off its iron | ✔ |
| G-LAYOUT, decks A and B: every pair's housings and bodies in 3-D against the study's plan | 78 pairs each; the solids never closer than the plan by more than 0.019 mm (the clamp's arc against its 9-point polyline); the least housing gap 1.86 mm, as the study (C8 sits under r2's junction, so D5–C8 and D8–C8 tie) | ✔ |
| G-LAYOUT, the stack | the column's node-2 plate 39.0 mm from the deck's parts (the study's 39); the riser 13.5 mm from the node-2 plates' bores (13 needed); the decks 12.0 mm from the cage (the record's 12); deck A's conductors 73.2 mm from deck B's (72 needed) | ✔ |
| the STEP read back | 378 instances of 142 products | ✔ |
| the record unchanged | `Machine(record)` builds the same 153 parts as `docs/geometry/tube/…-hub50.parts.json` after the refactor (`wound_element`) and the hub's new options | ✔ |

## Changes to the tools (none to the record's outputs)
- **`sim/tube_geometry.py`:**
  - `LayoutMachine` and `--layout` added;
  - the wound reluctance section's branches moved into `Machine.wound_element`, used by both builds;
  - `locked_hub` takes options for the coupler's length and the leads' channels, the record's defaults unchanged;
  - the primitives `cyl_between`, `wire`, `capsule_y` and `arc_capsule` added.
- **`sim/step_to_glb.py`:** `--angular` added, default 0.15 (the record's). The layout's GLB uses 0.4. This keeps the
  3 mm wires and the beads light (3.0 MB, not 8.4); the linear deflection still sets the large parts.
- **`tools/step-viewer/`:**
  - `scene.js`: the potting is translucent, and the layout gets its views (central bay, deck B, deck A), two-plane
    clipping and section labels;
  - `sim.js`: the potential and conduction layer and the charts;
  - `layout.html`: the viewer;
  - `render.html` and `shoot.py`: a still at one instant of the circuit (`view@phase`, `--sim`);
  - `make_layout_data.py`: the viewer's files.

## Not drawn (open, as in the study)
- **The bridge-ring bearings:** the shafts need them (`sim/multiplier-layout-findings.md` §7). They need 10–20 mm a
  side beyond the 974 mm; their place is the designer's.
- **Mounts and standoffs:**
  - Ca / Cb's rods and mounts, and the plates' interconnections (the riser passes the node-1 plates' bores; their tabs
    are not drawn);
  - the decks' standoffs to the can, and the riser's standoffs.
- **Circuits beyond the HV deck:** the magnetic pump's La / Lb and D1*–D4*, and the AH leads inside the hub.
- **Elsewhere:** the gear and the belt; the potting's real shapes (the study's envelopes stand in) [RH].
