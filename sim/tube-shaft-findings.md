# Tube machine — shaft, bearing hubs and reluctance radius (findings)

Scope: §0 the design of record; §1–§5 the earlier tube machine (r 50–150 vanes, 3 mm gaps, 8 + 8 vanes per side, its
stator on the frame). Sources: `sim/shaft_bearings.py` →
`sim/shaft_bearings_results.json`, `sim/tube_magnetic.py` → `sim/tube_magnetic_results.json`, `sim/tube_geometry.py` →
`docs/geometry/tube/tube-r150-n8.step`.

## 0. The design of record (2026-10-09): two bodies on the shaft
**Sources:** `sim/tube_geometry.py --record` → `docs/geometry/tube/tube-r150-n6-air6-wound-g0p5-6br-hub50.*` (STEP, GLB,
parts, section, hub, plan, 3-D stills) and `sim/tube_geometry_record_results.json`; `sim/shaft_bearings.py --record` →
`sim/shaft_bearings_record_results.json`.

**The model of record.** The solids now carry:
- the air stack of record: 6 + 6 vanes of 3 mm, 6 mm air gaps, 22° / 22°, r 50–150;
- the HV side on the rotor: the stator vanes are REF, the rotor vanes nodes 1 / 4, and Ca / Cb (6 plates per side) ride
  on the rotor;
- the locked hub: the 50 mm vessel, rings A / B with their beads, the gel, the PEEK retainer, the G10 coupler, and the
  AH cores, formers and coils;
- the wound utrons and bridges as before.

It is **940 mm** long: 916 with the 120 mm placeholder hub, plus the 24 mm the locked hub adds. It has 153 solids. The
checks: 490 pairs with no clash, no sweep hit, the utron gap exact (0.5 mm aligned, 9.74 unaligned), and the STEP reads
back. Not drawn [IR]: the vanes' full rounds, the Ca / Cb mounts, the HV parts, La / Lb, the gear.

**The bearings in the record carry two bodies** [OC law / IR inputs].
- The counter-rotor rides on the shaft through the four inner bearings, and only the two end bearings face the frame.
  The section below (§3) checked the earlier tube, whose stator stood on the frame at every bearing.
- The model: the shaft and the counter-rotor as two Euler–Bernoulli beams on one z grid. The four inner bearings join
  them, and the two end bearings tie the shaft to the frame (each 2e8 N/m [RH]).
- The masses: every solid's mass and rotary inertia at its centroid (datasheet-class densities [IR]; windings half
  Cu). That gives a rotor of 33.4 kg (d 25) and a counter-rotor of 33.1 kg. Their heaviest parts are the two G10 bridge
  rings (6.4 kg each, plus 3.9 kg of bridges), which overhang the inner bearings toward the ends.
- The hub span bends as the G10 coupler plus the PEEK retainer at the equator (EI 6.4 kN·m², rigid joints [IR]),
  against the shaft's 4.0 (d 25) or 8.4 kN·m² (d 30). A hinge there is the lower bound.
- The utrons' magnetic pull is a negative stiffness between the bodies at each reluctance plane. Taken at 2e5 N/m per
  plane [IR], it is negligible: the neck clamps the flux, and about 0.16 T crosses the tips.
- The criteria [IR]: f1 ≥ 3 × the bearings' relative speed (60 Hz), and the change of the utron gap under a 1 g lateral
  load ≤ 0.05 mm. The axis is vertical, so 1 g lateral is a stiffness yardstick, not an operating load.

| bearings | shaft | f1 / f2 (Hz) | utron gap change under 1 g lateral | meets |
|:--|:--|--:|--:|:--|
| 6, as laid out | d 25 | 29 / 46 (hinge 28) | 123 µm | no |
| 6, as laid out | d 30 | 40 / 64 | 64 µm | no |
| 6, as laid out | d 35 | 53 / 84 | 39 µm | no |
| 6, as laid out | d 40 | 65 / 105 | 25 µm | yes |
| **8: + one at each bridge ring's outer end** | **d 25** | **165 / 247** | **3 µm** | **yes** |
| 8: + one at each bridge ring's outer end | d 30 | 176 / 296 | 1 µm | yes |

- **The first two modes** are the whole assembly rocking and bouncing on the shaft's two end spans (188 mm each, between
  an end bearing and the Ca|reluctance bearing). The bridge rings hang on those spans.
- **The shaft's diameter alone buys little:** d 40 just reaches 60 Hz.
- **A bearing between the shaft and each bridge ring's outer end**, beside the end bearing, closes the overhang. f1
  rises sixfold and the gap barely moves, even at d 25.
- **The decision is the designer's** (the ledger's open items): the eighth bearing pair with d 25 (one 6205 class
  throughout), or six bearings with d 40.
- **The bridge rings could be lighter:** 25 mm of solid G10 against 6 × 0.65 kg of bridges.

## 1. Reluctance radius: the C-EMs move outward

At the original utron radius (r_u 52) the 65 mm tangential utron arc was wider than the 60° C-EM pitch, so the rotor saw
the same permeance aligned and between C-EMs: **no reluctance swing**. Sweep of the magnetic design shifted radially
(2-D magnetostatic, ideal iron, linear MMF on the spine plates):

| r_u (mm) | 52 | 70 | 100 | **130** | 160 |
|:--|:--|:--|:--|:--|:--|
| swing (aligned − between) / aligned | 0.0 % | 0.9 % | 10.0 % | **14.7 %** | 16.1 % |

Chosen: **r_u 130 mm** (`rel_shift_mm = 82.1`), reluctance envelope ⌀ 529 mm, C-EM to C-EM 96.5 mm, utron inner edge
r 107. Going to 160 gains only 1.4 points for a ⌀ ~590 envelope. [OC]

## 2. Shaft close to the reluctance steel

A steel shaft (floating iron tube, r 5.5–12.5) adds 2–3 % leakage permeance and does not change the swing (0.85 % vs
0.87 % at r_u 70). At r_u 130 the jaws sit ~95 mm off the shaft, so the effect is smaller still. Recommendation: a
non-magnetic shaft (austenitic stainless or Ti) anyway, to keep eddy currents and stray flux out of the bearings. [IR]

## 3. Bearing hubs and shaft diameter

Euler–Bernoulli FE, consistent mass, bearings as 2e8 N/m springs; the hub joint both rigid and as a hinge (worst case).
Criteria: f1 ≥ 150 Hz (3 × 3000 rpm) and ≤ 0.05 mm deflection under 1 g lateral. Rotor parts 22.2 kg, shaft 1263 mm.

- Two end bearings fail at any diameter (the hinge case is a mechanism).
- **As built: six symmetric hubs** — both ends, both Ca | clocking boundaries, both hub faces (z 10 / 304 / 554 / 710 /
  959 / 1253 mm). d_min 20 mm; **chosen d 25 mm**: f1 239 Hz (rigid) / 230 Hz (hinge), 1 g deflection 5 µm,
  loads 28–75 N, shaft 4.9 kg. 6205-class deep-groove bearings (25 / 52 / 15).
- Four hubs need d 34–40 mm (ends + hub faces) and 3–4 × the bearing load.

## 4. Coupling to the bicone hub

The shaft is split at the hub: each half ends in a flange (r 32, 8 mm) bolted to a bicone apex. With bearings on both
hub faces the bicone carries almost no bending — the hinge and rigid cases differ by only 4 %. The real RA hub geometry
still has to adopt the r 32 flange interface. [OC]

## 5. Counter-rotation

The stator counter-rotates, so the intermediate hubs (Ca | clocking, hub faces) are rotor-to-stator bearings running at
the **relative** speed; only the end hubs face the frame. Outer rolling guides from the stator to a shell are future
design, as are vacuum and gas fill (deferred by the designer). [RH]

## Checks on the rebuilt STEP

307 placed solids from 30 prototypes; G-TUBE-CLASH 0 in 348 pairs, G-TUBE-SWEEP 0 hits, G-TUBE-GAP exact, read-back
307 / 307.
