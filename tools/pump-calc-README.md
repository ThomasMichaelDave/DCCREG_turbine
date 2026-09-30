# tools/pump-calc — the pump-action calculator for the drawn pump

`pump-calc.html` answers one question for any configuration of the drawn pump (doubler + islands +
all eight gaps): **does it pump, by how much, and where does the energy go?** It is a thin page over
one exact engine, `sim/pump_engine.py`, which runs in Pyodide inside a Web Worker
(`pump-calc.worker.js`).

## Run it

Serve from the **repo root** (not `file://` and not from inside `tools/`). The worker fetches
`../sim/pump_engine.py`, `../shuttle_core.py`, `../reference/*.py`, `../spice/timing.sub` and
`../topology_edge_list.csv` into the Pyodide filesystem. These are the real files, never vendored copies.

```bash
cd <repo-root>
python3 -m http.server 8000
#   http://localhost:8000/tools/pump-calc.html
```

- **The first load needs internet access.** Pyodide 0.26.2 and numpy 1.26.4 come from the jsdelivr CDN.
- **Offline or behind a proxy:** extract the Pyodide 0.26.2 release somewhere and serve it under
  the same origin, then add `?pyodide=<url-of-that-directory>/` to the page URL.
- **Engine timing (this build, measured):** boot plus canaries takes about 5 s. A standard
  evaluation (motor out, with both twins) takes about 5–8 s. Motor-in evaluations take longer. See
  `sim/pump-calc-findings.md` (P1/P2).

## The badge is the acceptance test (fail-closed)

| badge | meaning |
|---|---|
| `ENGINE: live · canaries K1–K4 pass` | The in-browser engine reproduced all four canaries (below), and the JS `solveDoubler4` agrees with K1. |
| `ENGINE: CANARY-FAIL` | At least one canary disagrees. **No numbers are shown** and compute is disabled. |
| `ENGINE: down` | Pyodide, numpy or a repo file did not load. The page never falls back to hard-coded numbers. |

## What the canaries mean

| id | check | tolerance |
|---|---|---|
| K1 | Always-armed galvanic doubler at the canary caps: z = **1.3340016**. It is computed by the engine *and* by the JS `solveDoubler4` copied from `index.html`, so the check uses two engines. | 1e-6 |
| K2 | The same doubler with its rectifiers armed at the DXF stations: z = **1.5225272**. This is the r0.2 finding: station phasing binds. | 1e-6 |
| K3 | The engine executing `shuttle_core`'s own schedule and topology must equal shuttle_core's steady z, **1.2983502589**. | 1e-9 |
| K4 | S2 ring: t½ **2.22155 µs** and V_bank **998.891 V** at R = 2 Ω. | 0.01 % |

The build-time gates (E0 regression against the r0.2 record, E1 expm parity, E2–E4 gap-model limits
/ no chop / conservation, M1–M3 motor, P0 monodromy = iteration, N numpy parity, F, Z) are in
`sim/pump_engine_gates.py`, and their results are in `sim/pump-calc-findings.md`.

## Reading the outputs

- **z** is the Floquet multiplier: the spectral radius of the composed one-cycle map, which does not
  depend on where the cycle is cut. z > 1 means the pump pumps.
- **"Not converged"** means the switching pattern did not repeat. For the motor-in machine it also
  means the dθ/2 re-run disagreed by 1e-3 or more. In either case **no number is shown**, only the flag.
- **η** is always shown with its **cut** stated. The η(cut) curve over the sector is given with its
  min/max. The η of an unloaded, growing pump with sequential events is cut-dependent, so no single
  headline η is shown until D-CUT.
- **Twin panel.** G is the same machine with Lx shorted. G0 has the islands replaced by ideal
  station valves. Both use the same gap models, and Δη is reported at the stated cut.
- **Gap events** get one row per conduction episode: the strike plus the quasi-static re-closures of
  the r0.2 grid.
  - The **TRV ratio** is the reverse peak divided by V_f, from an open-circuit probe after the gap's
    current zero.
  - **"Needs a rectifier"** flags a gap modelled as symmetric whose TRV ratio is above 1.
- **Scaled readouts** (kV, A, µC, mJ): the engine is linear and scale-free. The eigen-mode is scaled
  so that the load-gap voltage at its station equals V_strike (the D-SCALE default, [IR]).
- **The URL hash** holds every input that differs from the defaults, so a configuration can be
  shared as a link. Nothing is stored in `localStorage`.

## Out of scope (by design)

- **The tank** (L_R1, C_R1, L_R2 are collapsed, so R-A = R-B = the reference). It is greyed on the
  schematic as "collapsed — core effects out of scope".
- **Governor and crowbar** (D-GOVERNOR).
- **Motor torque and mechanics.** The motor enters only as its circuit branches.
- **Geometry and mechanical panels.** The only geometry path is `design_synth.Cmax_from_geom`.
- **Gap physics beyond the selected model** (valve / arc / ring-down / symmetric recovering).

## Presets (`presets/pump/`)

Each preset is a JSON config with an `expect` block. Loading a preset recomputes and checks it:
`canary-core-simultaneous`, `canary-core-station`, `canary-shuttle-parity`, `default-drawn-G1`,
`default-drawn-R1-valve`, `default-drawn-R1-ringdown`, `pass-A-ngspice-config`.
