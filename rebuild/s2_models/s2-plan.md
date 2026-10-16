# Stage S2 — the 3-D models: plan

> **Corrected 2026-10-16:**
> - **From scratch:** the designer: "we explicitely agreed to build from scratch". S2a is built from the S1b circuit
>   up, not from the redesign's machine, by the rule of addition.
> - **The designer's choices:** bare-minimum mechanics; no can; the decks beside the hub; the hub without the AH.
> - **Read with this:** the table "What changes from the redesign layout" below holds for the deck, the rings, the
>   antiphase and the wall. Its last row ("kept as drawn": the can, the reluctance sections, the bearings, the
>   drive) is withdrawn.
> - See `s2-geometry-findings.md`.

**The designer (2026-10-16):** "commit this, then start S2". The four choices made at the start of S2:

| choice | the designer's answer |
|:--|:--|
| the starting layout | **the 10-11 redesign layout** (`sim/multiplier-layout-3d-findings.md`, PROPOSED), stripped back to the S1b circuit |
| which side node 1 is on | **the record's:** N1 on side A, below the hub; N4 on side B, above. Each core electrode is wired to its own side's varicap node |
| the rims | **yes, as an S2 variant:** win back the κ the rims cost. 2-D cell 7.47, 3.51 as built (ledger §3.4) |
| the field solver | **the repo's finite-volume method** (`sim/tube_strays.py`). FreeCAD holds the model for the designer; an Elmer cross-check may come later |

**What S2 has to deliver** (`rebuild/README.md`, the stages):
- the solids of the tube as the S1b circuit needs them;
- C1(θ), C2(θ), Ca, Cb, the core's C_k and every stray as nodes, from field solves;
- S1 / S1b re-run on them until z closes;
- the gate: S1 ↔ S2 converged, no clash, and the clearances meet the air law.

## What changes from the redesign layout

The redesign layout (552 solids, 1014 mm) carries the 10-10 multiplier circuit. The rebuild's circuit is S1b's (the
KiCad sheet *S1b clamp*). So, per side:

| redesign layout | S2 | why |
|:--|:--|:--|
| C2 **in phase** with C1 (no half-pitch offset) | **C2 half a pitch on: antiphase** | S0 needs 180°; in phase z = 1.000 (`rebuild/s1_tube/s1-pulsed-core-findings.md`) |
| the deck: six diodes, C3–C8, Csa / Csb, the clamp string, surge resistors, ten junctions | **the deck: the S1b parts only**. Side A: D1 (REF → N2), D3 (N3 → N1), Z1 (N1 → REF). Side B: D2, D4, Z4. The cross nets N3 → D3 and N2 → D4 run between the decks, as l1 / r1 did | the multiplier (C3–C8, D5–D8) is not in the rebuild's circuit |
| the rings fed from Csa / Csb through the ladders | **ring A wired straight to N1, ring B straight to N4** (the core's electrode pair, C_k) | the pulsed core, DECIDED 2026-10-15 |
| the hub at the 1.5 mm wall | **the 2 mm wall** (R_in 23.0), from `presets/hub-locked.json` | DECIDED 2026-10-15 |
| the surge resistors R1–R4 | **left out**, as in S1b | not in the rebuild's circuit; added only if a stage shows the need (the rule of addition) |
| the grounded can round the hub, the reluctance sections, the bearings, the drive | **kept as drawn** | outside the electrostatic circuit; in the field solve they are REF or floating conductors |

## The deck (2026-10-16)

- **The designer:** "option 2 ... A bigger deck then required would insert an unnecessary compromise for no reason";
  then "Also clear the can in air (r 50–125)"; and the cross wires need a bracket.
- **The deck of record:** the S1b parts only, every HV part clear of the can in air as well. It runs r 50–125,
  balances itself to 9 g. The column stands at |z| 107 on 20 mm steatite standoffs, bound by the can's end disc
  (each side 10 mm shorter, 994 mm; `s2-deck-findings.md` finding 4).
- **The split strings:** each clamp string is split into two balanced series halves.
- **The bracket:** a PTFE bracket at the midplane holds the two cross wires.
- See `s2-deck-findings.md`.

## The sub-stages

| | what | script → outputs | gate |
|:--|:--|:--|:--|
| **S2a** | **the geometry:** the redesign layout with the changes above. The STEP and parts list carry each solid's net (N1–N4, REF, floating) and material; a FreeCAD document is built from the STEP by script for the designer | `rebuild/s2_models/s2_geometry.py` → `.step`, `.parts.json`, `.FCStd`, the section render | no clash, no sweep; the decks' parts with their clearances; the nets as S1b's TOPOLOGY |
| **S2b** | **the field solve:** the finite-volume method of `sim/tube_strays.py`, generalised to read S2a's parts list: the Maxwell matrix at the aligned and half-pitch angles, levels 0–2 | `rebuild/s2_models/s2_strays.py` → results, findings | levels converge; C1 / C2 / Ca against the record's 3-D values on the unchanged parts |
| **S2c** | **back into the circuit:** S1 / S1b re-run with S2b's C1(θ), C2(θ), Ca, Cb, C_k and strays; the KiCad sheet *S2* carries the solved values | `rebuild/s1_tube/` runs on S2 values | z, the clamp level, the margins and self-start closed against S1b |
| **S2d** | **the rim variant:** the vanes' and rings' edges reshaped so the rims no longer sit edge to edge across the 6 mm gap; κ and z against S2b | `rebuild/s2_models/s2_rims.py` | κ, z, the clearances; no clash |
| | **the clearances against the air law** at S1b's voltage map (13.13 kV on N1 / N4) | in S2a / S2b | every HV gap and surface under the record's field limits |

## The tools

- **The geometry:** OpenCascade through OCP (installed), reusing `sim/tube_geometry.py`'s `LayoutMachine`, read
  only, subclassed in `rebuild/`. Nothing in `sim/` is edited.
- **FreeCAD 1.1.4** (installed 2026-10-16, per user: `%LOCALAPPDATA%\Programs\FreeCAD 1.1\bin\freecad.exe`; its
  interpreter `freecadcmd.exe -c "..."`, OCC 7.8.1) opens the STEP for the designer. Its document is generated by script
  through FreeCAD's own Python, never edited by hand into the record.
- **The field solve:** `sim/tube_strays.py`'s method (node-based finite volumes on a cylindrical grid, Shortley–Weller
  boundaries, CG with smoothed-aggregation AMG through pyamg). A full level-2 solve takes hours on 4 cores.

## Order

S2a first: the designer looks at the model in FreeCAD before any solve. Then S2b → S2c, and S2d once S2b has a
baseline.
