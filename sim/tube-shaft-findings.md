# Tube machine — shaft, bearing hubs and reluctance radius (findings)

Scope: the tube machine (r 50–150 vanes, 3 mm air, 8 + 8 vanes per side). Sources: `sim/shaft_bearings.py` →
`sim/shaft_bearings_results.json`, `sim/tube_magnetic.py` → `sim/tube_magnetic_results.json`, `sim/tube_geometry.py` →
`docs/geometry/tube/tube-r150-n8.step`.

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
