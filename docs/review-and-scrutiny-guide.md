# DCCREG turbine: a guide for review and for the scrutiny bench

**What this is for:** two jobs.
- **Discussing the current proposal with a partner:** which documents to share, and in what order to read them.
- **Planning a scrutiny bench** that tests the electrical and mechanical understanding of the machine: where every
  study, script, drawing and document lives, and which model values only a measurement can settle.

This guide adds no numbers of its own. Each number below is quoted from the file named beside it, with that file's
tags ([OC] / [IR] / [RH], `CONVENTIONS.md` §1).

**State:**
- the branch `claude/new-session-0az7f9` of the repository, as of 2026-10-12;
- the design is LOCKED as of 2026-10-09 (design state `09243c7`). Its redesign (the ledger's §3.9) is under way:
  the designer took its circuit "for now"; its layout and parts are PROPOSED;
- what is DECIDED, PROPOSED or OPEN is the designer's call (the ledger, §5).

## 1. What to share with your partner

### 1.1 The document to send: the design ledger
**`docs/ledger/DCCREG-design-ledger.pdf`** (53 A4 pages; its source is `docs/ledger/DCCREG-design-ledger.md`). It is the
single current account of the machine: its logic, each component's principle, the numbers with their sources, what is
decided and what is open, and what was found inconsistent and how it was settled.

| pages | section | what it gives your partner |
|:--|:--|:--|
| 1–2 | the summary | the status, the abstract, what the redesign changes |
| 4–5 | §1 The machine at a glance | the machine on one page, Figure 1 (what drives what) |
| 6–9 | §2 How the design got here | its purpose, the path in eleven steps, the designer's decisions, what was superseded |
| 10–28 | §3.1–3.8 The components | the bodies and bearings, the magnetic pump, the AH pair, the electrostatic pump, the hub, the rings, the field at the null, the cost; the schematics are Figures 4 and 7 |
| **29–36** | **§3.9 The redesign** | **the current proposal:** the multiplier stacked into the doubler (Figure 10), its layout (Figure 11), the bridge-ring bearings, the capacitors' mounts, the drawing set |
| 37–38 | §4 Fact sheet | the numbers of record, each with the file it comes from |
| 39–43 | §5 Status | every choice as DECIDED / PROPOSED / OPEN (§5.1); the open items for the designer (§5.2); the rings' bench test (§5.3) |
| 44–48 | §6 Known inconsistencies | 76 items: what was found, and whether it was corrected, proposed or left open |
| 48–53 | §7–§8 | the drawing register; the files and how to regenerate them |

**A reading order for a first discussion:** the summary, §1, §3.9, then §5 and §6. §5 and §6 are where the open and
disputed points sit.

### 1.2 Its companion: the drawings
- **`docs/ledger/DCCREG-drawings-bundle.pdf`:** 161 A3 sheets behind a three-page register.
  - The schematics are sheet 2 (the rotor's two circuits), sheet 3 (the rings' supply) and sheet 30 (the redesign, as
    laid out).
  - The redesign's layout and 3-D views are sheets 31–35.
  - The drawing set is sheets 61–161: a sheet for every part, bought part and sub-assembly, with GA-001, the general
    arrangement, on sheet 62.
- **The drawing set alone:** `docs/drawings/set/*.pdf`, 103 sheets, in the order of `docs/drawings/set-index.json`.

### 1.3 Interactive views
These are private on claude.ai: open them, then share them from their Share menu.
- **The drawing-set gallery:** https://claude.ai/artifact/DKGfD3U8kZACdvtHQc5VGF. Every sheet, filterable by system.
- **The 3-D model with its circuit running ("DCCREG Wound Tube"):** https://claude.ai/artifact/YHDhqMAcovexSrNEDyGReM.
  Its source in the repository is `tools/step-viewer/layout.html`.

### 1.4 For a partner who reads the code
- The repository is `ThomasMichaelDave/DCCREG_turbine`, branch `claude/new-session-0az7f9`. They need read access to
  it.
- **Read in this order:** `README.md`, `CONVENTIONS.md` (the tags and the symbols), the ledger, the findings it cites,
  then `presets/hub-locked.json` (the hub's specification of record).

## 2. Where everything is

### 2.1 The pattern
Every study ships as three files:
- **the script:** `sim/<study>.py`;
- **its numbers:** `sim/<study>_results.json`;
- **its findings:** `sim/<study>-findings.md`.

Every figure and drawing is redrawn by a script: `docs/make_*.py`, or the study itself. The ledger's §8 gives the order
to regenerate them in.

### 2.2 The folders

| folder | what is in it |
|:--|:--|
| `docs/ledger/` | the ledger (`.md`, `.pdf`), the drawings bundle (`.pdf`), their builders (`make_ledger.py`, `make_ledger_figures.py`), the register (`register.py`), the ledger's own figures (`figures/`) |
| `sim/` | the studies: scripts, results (`*_results.json`) and findings (`*-findings.md`); the circuit decks are built in Python and run in ngspice |
| `docs/` (top level) | the design documents (`rings-design.md`, `bench-test-rings.md`, `drive-gear-belt.md`), the schematics (`schematic-*.svg` / `.png`) and the generators (`make_*.py`) |
| `docs/drawings/` | the manufacturing drawings of record (`DCCREG-UTR-101.pdf`, `DCCREG-HUB-201.pdf`, with the utron's STEP and DXF); the drawing set in `set/` and its order in `set-index.json` |
| `docs/figures/` | the studies' figures (the layout, the bearings, the strays, the utrons in 3-D, the bench predictions, the drive's concept) |
| `docs/geometry/tube/` | the machine in solids: the record (`…-hub50.step`, `.glb`, `.parts.json`), the redesign's layout (`…-hub50-layout.step`, `.glb`, `.parts.json`), the full model with the AH-drive parts and the drive (`…-hub50-layout-full.step`, `.glb`, `.parts.json`) and their sections and stills |
| `tools/step-viewer/` | the 3-D viewer: `layout.html` (the circuit running on the layout), `viewer.html`, and the scripts that feed them (`make_layout_data.py`, `shoot.py`) |
| `presets/` | `hub-locked.json`, the hub's specification of record and the redesign's status |
| `docs/cost/` | the cost sheet (placeholders) and its README |
| `spice/`, `reference/`, `index.html`, `tools/pump-*` | earlier phases' decks and tools, frozen: never edited (`README.md` gives the check) |
| the repository's root (`*-findings.md`, CSVs, PNGs) | the earlier disc machine's studies, kept for the record and superseded |
| `docs/future-work/`, `docs/context-reverse-vdg/` | background and ideas for later, not the design |

### 2.3 The studies by subject
The scripts are in `sim/`, each with its `_results.json` beside it.

| subject | scripts | findings |
|:--|:--|:--|
| **the magnetic pump** | `pole_design.py` (the pick: `pole_design_variants_op.json`), `magnetic_doubler.py` (the deck), `rotor_parts_duty.py`, `utron_3d.py`, `neck_nonlinear.py` | `pole-design-findings.md`, `rotor-parts-duty-findings.md`, `utron-3d-findings.md`, `neck-nonlinear-findings.md` |
| its start-up and parts | `start_3d.py`, `diodes_real.py`, `parts_first_cut.py` | `start-3d-findings.md`, `diodes-real-findings.md`, `parts-first-cut-findings.md` |
| the AH pair | `ah_steady_cusp.py`, `ah_null.py`, `ah_winding.py` | `ah-steady-cusp-findings.md`, `ah-null-findings.md` |
| **the electrostatic pump** | `air_stack_sizing.py`, `vane_matrix.py`, `core_field.py` (the deck), `tube_strays.py` | `air-stack-sizing-findings.md`, `vane-matrix-findings.md`, `core-field-findings.md`, `tube-strays-findings.md` |
| the hub and its rings | `hub_rings_build.py`, `hub_drift.py`, `hub_revolution.py`, `hub_beads_settled.py`, `hub_thermal.py`, `hub_joints.py` | `hub-rings-build-findings.md`, `hub-beads-settled-findings.md`, `hub-thermal-findings.md`, `hub-joints-findings.md`; the bench plan `docs/bench-test-rings.md` |
| **the redesign (the proposal)** | `integrated_multiplier.py`, `multiplier_layout.py`, `multiplier_waveforms.py`, `bridge_ring_bearings.py`, `doubler_caps.py` | `integrated-multiplier-findings.md`, `multiplier-layout-findings.md`, `multiplier-layout-3d-findings.md`, `multiplier-waveforms-findings.md`, `bridge-ring-bearings-findings.md`, `doubler-caps-findings.md` |
| **the mechanics** | `rotor_mechanics.py`, `shaft_bearings.py`, `drive_sizing.py`, `unmodelled_parts.py`, `rotor_parts_drive.py` | `rotor-mechanics-findings.md`, `tube-shaft-findings.md`, `docs/drive-gear-belt.md`, `unmodelled-parts-findings.md`, `rotor-parts-drive-findings.md` |
| the machine in solids | `tube_geometry.py` (`--record`, `--layout`), `step_to_glb.py` | `multiplier-layout-3d-findings.md` |

### 2.4 The schematics and drawings, with their generators

| what | file | generator |
|:--|:--|:--|
| the rotor's two circuits (ledger Figure 4; bundle sheet 2) | `docs/schematic-rotor-circuits.svg` / `.png` | `docs/make_schematic_rotor.py` |
| the rings' supply of record (Figure 7; sheet 3) | `docs/schematic-rings-supply.svg` / `.png` | `docs/make_rings_supply_schematic.py` |
| the redesign's circuit as laid out (Figure 10; sheet 30) | `docs/schematic-integrated-multiplier.svg` / `.png` | `docs/make_integrated_multiplier_schematic.py` |
| the redesign's layout (Figure 11; sheet 31) | `docs/figures/multiplier-layout.png` | `docs/make_multiplier_layout.py` |
| the drawing set (103 sheets) | `docs/drawings/set/` | `docs/make_drawing_set.py` |
| the utron's half-core; the rings | `docs/drawings/DCCREG-UTR-101.pdf`; `DCCREG-HUB-201.pdf` | `docs/make_core_drawing.py`; `docs/make_rings_drawing.py` |

## 3. For the scrutiny bench: what the models leave to measurement

The ledger keeps the quantities only a bench can settle OPEN until one measures them: the hold-off ratings, the
rings' leakage and the conductivities (`CLAUDE.md`; the ledger, §5). The plan that exists, `docs/bench-test-rings.md`
(the ledger, §5.3), tests only the rings and the field at the null. It has four phases: the hold-off, the leakage,
the DC drift, and the field on the pump's own supply.

The tables below list the further model values a scrutiny bench could check, electrical and mechanical, each with the
file that holds it. They are candidates; which of them the bench takes up is the designer's choice.

### 3.1 Electrical

| quantity | the model's value | where it is | why it matters |
|:--|:--|:--|:--|
| a utron's inductance, aligned / unaligned | 81.0 / 9.4 mH, κ 8.6 in the 2-D screen (its stack's ends a +30 % allowance [RH]); 83.3 / 12.4 mH, κ 6.70 in 3-D; κ 5.96–6.44 with the group's coils coupled | `sim/utron-3d-findings.md`; the ledger §3.2, §4 | κ sets the magnetic pump's gain: one utron on one bridge, at a few angles, with an LCR meter |
| the neck's saturation flux | Ψs 0.1268 Wb-turns as built, the stacking factor 0.90 [RH] | `sim/neck-nonlinear-findings.md`; the ledger §3.2 | it sets the AH's field and the start-up threshold |
| the AH pair's field | 290–308 A-turns per coil with the bypass (the 2-D record); 249–272 in the best estimate (3-D utrons and the neck's field map) | `sim/ah-steady-cusp-findings.md`; `sim/neck-nonlinear-findings.md` §6–§7 | the record and the best estimate disagree: the bench's first electrical question |
| the start kick | the seed threshold 16 % of Ψs with the deck's diodes, 17.2 % with the first cut's Schottky diodes, 25–30 % in the best estimate; the K4 kick starts it at full speed | the ledger §3.2; `sim/parts-first-cut-findings.md` §3; `sim/start-3d-findings.md` | whether K4 (REL-730) is enough |
| the varicaps C1 / C2 | 128.4–450.6 pF as built (κ 3.51, a 3-D field solve) against 54.9–409.9 pF in the deck (κ 7.47) | `sim/tube-strays-findings.md` §4; the ledger §4 | the electrostatic pump's gain; measurable with an LCR meter on a turned stack |
| the node strays | 66 / 25 pF as built (the record); 1–3 pF on the redesign's new nodes as laid out, against 24.5 pF assumed [RH] in its study | `sim/tube-strays-findings.md`; `sim/multiplier-layout-findings.md` | each pF costs about 0.003 of z (`sim/core-field-findings.md` §4); the strays set the redesign's clamp trim |
| the HV sticks' leakage, and the seed it forces | as built with real sticks: the rings −13.38 / +13.40 kV, 6.82 kV/cm; no self-start, a seed of 122 V (1.0 kV at the maximum leakage, 3.65 kV hot) | `sim/diodes-real-findings.md` §6 | the electrostatic pump's start-up: sticks from one lot, measured hot and cold |
| the clamp strings | BV 13.1 kV from 66 × 1.5KE200A-class TVS; the redesign trims them to 60 parts (V_op 11.94 kV) | `sim/parts-first-cut-findings.md` §2; `sim/multiplier-layout-findings.md` §6 | the rings' level follows the string's BV directly |
| the rings: hold-off, leakage, drift | the existing plan's phases 1–4 (100 GΩ per ring used; 7.62 → 8.20 kV/cm in 6 h) | `docs/bench-test-rings.md`; the ledger §5.3 | the ratings and the stage count rest on them |

### 3.2 Mechanical

| quantity | the model's value | where it is | why it matters |
|:--|:--|:--|:--|
| the shaft's first mode | 27–29 Hz as laid out at d 25 (65 Hz at d 40); with the bridge-ring bearings 83–87 Hz at d 25 | `sim/tube-shaft-findings.md` §0; `sim/rotor-mechanics-findings.md` §4; `sim/bridge-ring-bearings-findings.md` | the 60 Hz criterion and the pumps' 120 Hz; a tap test on the shaft in its seats |
| the seats' stiffness | G10 spiders against stiff seats: 83 against 87 Hz | `sim/bridge-ring-bearings-findings.md` | the model brackets the mode between the two |
| the utron gap under load | 123 µm at the stack's centre under 1 g lateral (d 25); a pull of about 28 N per utron | the ledger §3.1, §3.2; `sim/rotor-mechanics-findings.md` | the 0.5 mm gap is what the magnetic pump runs on |
| the runout budget | ≤ 0.027 mm per inner bearing as laid out (P5, an axial spring preload); 0.05 mm with the eighth pair | `sim/rotor-mechanics-findings.md` §5 | it eats the gap |
| the bearings' preload | the record's 100 N, under SKF's 125–250 N rule for spring preloads at d 25 | the ledger §3.9, §5.2 | the designer's to set |
| windage and bearing losses | about 12 W and 5 W | `sim/rotor-mechanics-findings.md` | the belt's power; a spin-down test measures both |
| the drive | 0.48 / 0.52 N·m on the bodies, 1.00 N·m into the frame; the run-up 32 s; as drawn, the pinions' inner bearing takes 40 N steady and 195 N at the driver's limit | `docs/drive-gear-belt.md`; `sim/unmodelled-parts-findings.md` §2 | the five changes the drawings made to the drive's first cut (the ledger §6 item 74) |
| the balance | G2.5 per body, after potting; the AH-drive parts placed so each side balances, with 3.27 kg of ballast a side | `sim/rotor-mechanics-findings.md` §6; `sim/rotor-parts-drive-findings.md` §2 | the potted decks and the chokes move it |
| the bays' mode with the parts | f2 108–117 Hz, against the pumps' 120 Hz | `sim/rotor-parts-drive-findings.md`; the ledger §6 item 77 | a tap test on the rotor with the parts mounted |

### 3.3 To build the bench from
- the drawings: the drawing set (`docs/drawings/set/`) and the rings' drawing (`docs/drawings/DCCREG-HUB-201.pdf`);
- the bought parts' candidates: `sim/unmodelled-parts-findings.md` §4 and the drawing set's P-sheets. They came from a
  web search: confirm each on the maker's current sheet;
- the predictions to test against: each study's `*_results.json`, and `docs/figures/hub-bench-predictions.png` for the
  rings;
- the safety rules for the HV work: `docs/bench-test-rings.md` §4.
