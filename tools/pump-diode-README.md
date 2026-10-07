# tools/pump-diode: the de Queiroz diode doubler on the disc or the tube, and the power left for the C-EMs

`pump-diode.html` runs the bare electronic Bennet doubler: four diodes and C1, C2, Ca, Cb. The flying bucket is removed:
- no Cx / Lx islands;
- no spark gaps SG1–SG4, BS3 / BS4;
- no clocking decks.

It assesses the power available to the motor C-EMs against operating voltage. Physics: `sim/diode_machine.py` (with
`sim/stack_sizing.py` and `sim/pump_engine.py`), in Pyodide through `tools/pump-diode.worker.js`.

## Run it

```bash
cd <repo-root>
python3 -m http.server 8000      # http://localhost:8000/tools/pump-diode.html
```

On Windows, use the `.js` MIME one-liner from `tools/pump-stack-README.md`. The badge must read
`SOLVER: live · K1–K4 + anchor z 1.3254745 pass`.

## What it computes

- **Core.** The `solveDoubler4` topology:
  - nodes 1–4;
  - diodes D1 2 → ref, D2 3 → ref, D3 1 → 3, D4 4 → 2;
  - continuous varicaps (the engine profile);
  - run by the exact engine to its eigen-cycle.

  Disc: the PUMP-SYNTH plates. Tube: the vane stack, with the layout drawn without Cx vanes or clocking decks (736 mm
  at 8 + 8 vanes).
- **Medium and gap,** selectable for both: air (uniform-field breakdown) or vacuum (≤ 1e-4 mbar, a 10 kV/mm design
  field [RH]).
- **Operating-voltage sweep** from the "sweep from" value to the gap breakdown. Energies scale as V², currents as V.
- **C-EMs, side by side:**
  - **in series with D1 / D2**, so the 6-coil groups carry the rail-diode conduction current;
  - **on a DC tap** of the surplus, a motor fed by the pump.
- **Utrons:**
  - **iron:** torque = ½ i² dL/dθ; DC-tap η = the swing;
  - **PM:** torque = k_t i with k_t = N ΔΦ n_utron / 2; DC-tap η = the field.
- **Stator balance,** stator standing: net T = motor − the pump's own reaction torque (W × cycles per rev / 2π) −
  bearing − air shear (air only).

## Default results (300 rpm relative)

| build | z | breakdown | surplus at breakdown | best C-EM | stator |
|:--|:--|:--|:--|:--|:--|
| tube, 3 mm vacuum, 8 + 8 vanes, iron utrons | 1.515 | 30 kV | 6.77 W | DC tap 0.87 W (series 9e-6 W) | dragged along, −203 mN·m |
| tube, same, PM utrons | 1.515 | 30 kV | 6.77 W | DC tap 5.41 W (series 0.016 W) | dragged along, −58 mN·m |
| disc, 7 mm vacuum, PM utrons | 1.391 (settled ±0.04 %) | 70 kV | 8.32 W | DC tap 6.66 W (series 0.017 W) | dragged along, −123 mN·m |

Reading:
- **Series C-EMs get almost nothing.** The diode current is 0.02–0.2 mA, spread over about 4.6 ms per cycle.
- **The DC tap gets η × the surplus**, but only through a switched drive (per-coil switches, a position sensor and a
  controller). A DC bus without switches gives zero average torque. The switchless alternative is the coils in series
  with the varicaps (`sim/switchless-cem-findings.md`):
  - tube, PM utrons (6 per side), rewound ×20: 4.3 W and 137 mN·m at 20 kV;
  - this calculator does not model that placement yet.
- **The stator is dragged along in every case.** A pump-fed motor gives at most η × the pump's own reaction torque, so it
  cannot counter-rotate the stator. That needs an outside source or a frame-reacted generator (`sim/spinup-findings.md`).

## Inputs and assumptions

- **C-EM defaults** (per geometry, `diode_machine.CEM_DEFAULTS`): N 1846 turns (0.40 mm), R 44.5 Ω, 6 coils per group,
  dL/dθ, swing and utron count from the earlier C-EM studies.
- **Defaults to be replaced by data** [RH]:
  - ΔΦ 0.27 mWb (PM);
  - bearing drag 14.7 mN·m (tube) / 70 mN·m (disc);
  - air shear 4.6 mN·m (tube).
- **Torque window fraction** (default 0.5): the share of coil current that falls on the torque-producing slope.
- **Not modelled:**
  - coil inductance ringing with the node capacitances at diode turn-on;
  - diode leakage (~0.1 W, `sim/diode-stack-findings.md`);
  - core loss;
  - the loaded-pump gate G-LOAD (the surplus is the eigen-state growth term).
