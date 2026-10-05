# tools/pump-stack: disc or tube, record or v4

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

## Reference results (`sim/stack_sizing_results.json`)

Tube with r 50–160, a 3 mm air gap, 1.5 mm vanes and 30° / 22° sectors:

| vanes per varicap per side | C1/C2 max | κ | z, strays fixed (record / v4) | z, strays scaled (record / v4) |
|:--|:--|:--|:--|:--|
| 5 + 5 | 769 pF | 16.4 | 1.527 / 1.548 | 1.318 / 1.313 |
| **7 + 7** | **1111 pF** | **16.7** | **1.579 / 1.628** | **1.320 / 1.324** |
| 9 + 9 | 1453 pF | 16.8 | 1.609 / 1.679 | 1.321 / 1.330 |

The default disc gives 1.3255 (record) and 1.3030 (v4).
