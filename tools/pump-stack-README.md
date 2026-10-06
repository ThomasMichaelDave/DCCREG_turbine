# tools/pump-stack: disc or tube; record, v4 or the de Queiroz diode doubler

`pump-stack.html` sizes the pump for either machine shape and runs the exact engine on it.

**Geometry**
- **Disc** is the PUMP-SYNTH sizing, verbatim (`sim/pump_sizing.py`): one rotor/stator plate pair per variable capacitor,
  R95–R387, 7 mm gap.
- **Tube** is the elongated-z machine:
  - per side, an interleaved stack of self-supporting metal vanes in air, n rotor and n stator vanes per variable capacitor;
  - stator sectors 30°, rotor vanes narrower (22°) so there is a zero-overlap position;
  - the A and B sides sit around the central hub, with a clocking deck and a reluctance section outboard on each side.

**Topology**
- **Netlist of record:** the calculator's path (`pump_synth.engine_cfg` + `z_of`).
- **v4:** `DCCREG_Turbine_circuit_v4`. The C-EMs are in series with SG1 / SG2 (six per side, lumped), with the coil–gap node
  stray and the screened lead across each coil, and the parallel tank.
- **de Queiroz diodes:** the bare electronic Bennet doubler (A. C. M. de Queiroz, IEEE 2018):
  - the `solveDoubler4` topology, with 4 nodes and ideal diodes D1 2 → ref, D2 3 → ref, D3 1 → 3, D4 4 → 2;
  - continuous varicaps (the engine profile) in place of `solveDoubler4`'s two-state steps;
  - no islands and no spark gaps (`stack_sizing.core_net`).

  With continuous capacitance the ideal diodes switch at zero voltage across them, so η ≈ 1
  (`sim/diode-stack-findings.md`).

**Power and breakdown cards**
- **Belt · surplus:** the eigen-state ledger scaled so the highest node peaks at 20 kV (`stack_sizing.V_OP`), times the
  cycle rate (N_sec / 2 × rpm / 60).
- **Highest node · lost:** which node sets that 20 kV, and the power lost in gaps, rings and relaxation.
- **Gap air breakdown:** the uniform-field air breakdown of the vane gap, 24.4 d + 6.53 √d kV with d in cm, and its margin
  at 20 kV. Vane edges and humidity lower it, so a margin under ×1.2 is thin.
- **Gap breakdown by medium** (`stack_sizing.gap_breakdown_kV`):
  - **air:** the formula above. A 3 mm gap breaks down near 10.9 kV, so air needs about 8 mm for 20 kV.
  - **vacuum** (≤ 1e-4 mbar, below the Paschen region): a conservative large-area design field of 10 kV/mm [RH].
- **Tube default: 3 mm gap in vacuum, de Queiroz diode core.**
  - 30 kV design breakdown (×1.5 at 20 kV); 1114 / 71 pF, κ 15.7; 3.0 W surplus at 300 rpm.
  - Air at 8 mm gives only 0.78 W, because κ falls to 4.3 and C to 460 pF.
  - The spark-gap topologies (record, v4) need a gas for their gaps to strike, so with the vacuum default they are a
    comparison only.

## Run it

Serve the repo root over http (as for pump-synth):

```bash
python3 -m http.server 8000      # http://localhost:8000/tools/pump-stack.html
```

Pyodide 0.26.2 and numpy load from the jsdelivr CDN. Without CDN access, serve a local Pyodide 0.26.2 folder (with the numpy
wheel) from the same origin and add `?pyodide=<its-url>/`.

The worker (`pump-stack.worker.js`) is fail-closed. Nothing is shown unless all of these pass:
- the K1–K4 canaries;
- the engine, sizing, synth and stack self-tests;
- the **anchor gate**: the default disc under the record topology must give RT0's z 1.3254745.

## How the tube C(θ) is computed (`sim/stack_sizing.py`)

- **2-D cell:** one sector period wide (60° of arc at radius r) and one vane pitch tall (stator vane, gap, rotor vane, gap),
  periodic both ways. It is solved for the potential (CG, 0.25 mm grid), with C = 2W/V².
- **Positions:** aligned (C_max) and opposed (C_min, rotor vane centred in the stator gap), at 5 radii, integrated over r and
  multiplied by the six periods and the 2n − 1 working gaps.
- **Edge floor:** inner and outer edge fringing is not in the 2-D cell; a fixed floor (2 pF) is added to C_min.
- **Checks:**
  - wide, fully overlapped vanes match the parallel-plate value to 0.3 % at a 1 mm gap and 0.8 % at 3 mm (self-test);
  - halving the grid moves C_max by 0.5 % and C_min by 8 %.
- **Rest of the ladder:** the PUMP-SYNTH ratios (Ca = Cb = 1.10 C_max, Cx = 1.68 C_max).
- **Strays:** either the disc design's absolute values ("fixed") or grown with C_max ("scaled"). The real tube sits between the
  two until its strays are field-solved.

## Reading the section

The section is a vertical cut through the shaft, drawn at the same scale in r and z.
- **Shaft:** the dashed centre line.
- **Vanes and plates:** each horizontal stroke is one vane or plate seen edge-on, so its full width is the plate diameter.
  - **Rotor vanes** (blue) hang on the shaft sleeve; **stator vanes** (violet) hang on the outer posts.
  - The fixed **Ca / Cb plates** (green) are stator only, with two nodes alternating.
- **Order along the shaft:** bottom is the A side, top is the B side, and the bicone hub (C_R, AH coils, vacuum sphere) is in
  the middle. Outward from the hub on each side: C1/C2 variable capacitor, Cx, Ca/Cb, clocking deck, reluctance section.
- **Close-up (right):** the hub with both C1/C2 stacks enlarged.

The vane z positions come from `stack_sizing.layout()`, the same list that sets the reported length.

## Reference results (`sim/stack_sizing_results.json`)

Tube with r 50–150 (300 mm plates), a 3 mm air gap, 1.5 mm vanes and 30° / 22° sectors. Lengths include the derived clocking (4 decks) and reluctance sections (utron ring at r_u 130 mm, ⌀ 529 mm envelope), the split shaft flanges and six bearing hubs:

| vanes per varicap per side | C1/C2 max | κ | length | z, strays fixed (record / v4) | z, strays scaled (record / v4) |
|:--|:--|:--|:--|:--|:--|
| 6 + 6 | 817 pF | 15.5 | 1146 mm | 1.525 / 1.549 | 1.312 / 1.307 |
| **8 + 8** | **1114 pF** | **15.7** | **1263 mm** | **1.567 / 1.614** | **1.313 / 1.315** |
| 10 + 10 | 1411 pF | 15.7 | 1371 mm | 1.593 / 1.658 | 1.313 / 1.321 |

The default disc gives 1.3255 (record) and 1.3030 (v4).

## Tube solids and STEP (`sim/tube_geometry.py`)

`python3 sim/tube_geometry.py [--n-plates 8] [--r-out 150]` builds every element of `stack_sizing.layout()` as an
OpenCascade solid.
- **Vanes:** 6 sectors fused to a ring.
- **Clocking:** a rotor disc and tips, a stator ring and spheres.
- **Reluctance:** the designer's squared C-EM / utron STEP pieces, 6 C-EMs and 3 utrons per side.
- **Structure:** split shaft (⌀ 25, flanges bolted to the bicone apexes at r 32), six 6205-class bearing hubs (ends, Ca | clocking, both hub faces), rotor sleeve segments, insulating stator cages, and a hub placeholder (vacuum sphere + bicone).

It writes:
- `docs/geometry/tube/<tag>.step`: instanced, named, coloured (each repeated part stored once);
- `<tag>.parts.json`: the placed parts;
- three exact-cut renders: the section through the shaft, the reluctance plan, and the clocking plan per deck.

Checks (`sim/tube_geometry_results.json`):
- **G-TUBE-CLASH:** no two solids share volume, except intended joins;
- **G-TUBE-SWEEP:** no stator solid in the volume any rotor solid sweeps;
- **G-TUBE-GAP:** tip to sphere at alignment equals the set gap;
- **G-TUBE-REL:** C-EM to C-EM distance, utron to sleeve, reluctance envelope;
- **read-back:** the STEP reloads with every placed instance.
