# tools/pump-synth — rotor plates → does the drawn pump pump?

`pump-synth.html` sizes the drawn pump from its rotor plates and decides **PUMPS: YES / NO** with one exact engine.

It combines two parents:
- **The shell** comes from `charge-pump-synth-live.html`: plate sliders with an anchor reset, objective + Solve, result cards, the invariant battery with its named blocker, the reference drawer, and the SOLVER badge.
- **The physics** comes from pump-calc: `sim/pump_engine.py`, called through `sim/pump_synth.py` and `sim/pump_sizing.py`, running in Pyodide Web Workers.

The drawer's reference is `pump-synth-reference.md`.

## Run it

Serve the **repo root** over http. Opening the file directly (`file://`) does not work.

```bash
cd <repo-root>
python3 -m http.server 8000
#   http://localhost:8000/tools/pump-synth.html
```

- The first load fetches Pyodide 0.26.2 and numpy from the jsdelivr CDN. To use a local copy, add `?pyodide=<url-of-a-pyodide-0.26.2-folder>/` (it must be served from the same origin, or with CORS).
- **Workers.** One main worker runs the canaries, the headline, the twins, Solve, the critical values and the sweeps. Up to three helper workers run the robustness strip in parallel.
  - The number of helpers is `navigator.hardwareConcurrency − 1`, capped at 3.
  - Override it with `?helpers=0..3`. With no helpers the strip runs serially, which is slower.
- **Measured timing** (Pyodide in Node and in headless Chromium, 4 cores):
  - boot ≈ 5–6 s;
  - headline + strip ≈ 8 s cold, ≈ 4 s warm;
  - plus the twins ≈ 2 s.
  - `min_diameter` ≈ 6–8 exact runs.

  Below threshold, a non-pumping point needs a longer plain iteration (see `sim/pump-synth-findings.md`).

## The badge (fail-closed)

| badge | meaning |
|---|---|
| `SOLVER: live · K1–K4 + H-GEOM pass` | Every check below passed, so numbers are shown. |
| `SOLVER: CANARY-FAIL` | A canary or H-GEOM disagrees. Engine numbers are not shown and compute is disabled. |
| `SOLVER: down` | Pyodide, numpy or a repo file did not load. The page never falls back to a hard-coded number. |

The checks behind a live badge:
- the K1–K4 canaries, with K1 also run on the JS `solveDoubler4`;
- H-GEOM: C_max at R95–R387 / 7 mm equals `design_synth.Cmax_from_geom`, and the rotor is ⌀ 983 mm;
- the engine, sizing and synth on-load self-tests;
- the JS sizing self-test.

## If it stays on "booting…"

The causes and fixes are the same as for pump-calc (see `tools/pump-calc-README.md`):
- a `file://` open;
- no CDN access;
- a server started inside `tools/`.

## Reading it

- **PUMPS** means z > 1 for the exact drawn pump under the selected gap models. The default is D-GAPDEFAULT: M-RD(→0) for the load and fire gaps.
- **"z = 1, does not pump"** means the machine has no growing mode. Either the gaps fall silent, or the state converges onto the cycle map's neutral mode (charge trapped where no gap can dump it). This is the small-plate behaviour (S5).
- **"Not converged"** shows no number.
- **The ladder** lists every derived capacitor with its rule and tag.
  - Pin a value to override it.
  - Press **z=1?** for the engine's critical value, shown with a headroom meter on a ×32 scale.
- **The battery.** Each row is pass, fail, NOT-EVALUATED (dashed dot), n/a or info. Only evaluated rows decide feasibility and the named blocker.
- **The URL hash** holds every input that differs from the defaults, plus the pins (`pin_<key>`). Nothing is stored in `localStorage`.
- **Presets** (`presets/pump/`): `freeze-v010-plates` and `small-plate-probe`, each with an `expect` block.

## Stage 2 — capacitor plate geometry

Once stage 1 gives a workable design, press **🔒 lock → geometry**. This does the following:
- **Freezes stage 1.** The inputs, ladder and exact-engine z are stored as a hashed record in the URL (`lock=`, `lockz=`).
- **Re-verifies on reload.** The engine re-evaluates the locked inputs, and the badge shows LOCK DRIFT if they no longer reproduce.
- **Opens the geometry stage** (`tools/pump-geometry.js` ↔ `sim/pump_geometry.py`).

In the geometry stage:
- **Ca / Cb are geometrized.** You set the dielectric and its thickness, the sector width, which dimension to solve (r_out, r_in or the width), an optional manufacturing step, and the dielectric margin. If the realized C differs from the lock, the exact engine re-runs with Ca/Cb pinned at the realized values and reports Δz.
- **The plate distribution** shows a plan per carrier (both faces) and an assembly overlay, plus an axial half-section of the stack. Every other electrode is locked context from the r0.15 DXF.
- **Export.** `pump-geometry-<hash>.json` + `pump-geometry.FCMacro`: in FreeCAD, Macro ▸ Macros… ▸ Execute, then pick the JSON. The macro builds every carrier, foil sector and dielectric slab, and saves `.FCStd` and `.step` next to the JSON. The reference build is `docs/geometry/freeze-v010-CaCb.step`.

**Names in the 3-D model.** Every solid carries a descriptive label, which is also its STEP product name. For example:

`ND2 / Ca_el_1 - Ca electrode, node 2, Ca, sector 1 of 6 (30-60 deg), r110-174.76 mm, Al foil 1 mm, septum side, z -35.5..-34.5`

- The solids are grouped into one named sub-assembly per carrier, plus a "Dielectrics" assembly.
- `<json>-parts.csv`, written next to the STEP, is the translation table: one row per solid with its name, label, assembly, role, node, capacitor, material, radii, angles, z range and volume.
- Labels are ASCII-only, so they survive STEP in any package.

**Fusion 360, native.** `tools/fusion360/PumpGeometry/` is a Fusion 360 script.
1. Install it: Utilities ▸ ADD-INS ▸ Scripts and Add-Ins ▸ Scripts ▸ **+**, then pick the folder.
2. Run it, and pick the exported JSON.

It opens a new design containing:
- a top component named with the lock hash;
- one sub-component per carrier, plus Dielectrics;
- one named body per solid.

The names are the same as in the STEP and the parts CSV; Fusion forbids `/`, so it becomes `-`. Lengths are converted to Fusion's internal centimetres, and the design has parametric base features. Colours come from a copied library appearance; if that appearance isn't found, the bodies are left uncoloured.

**Fusion 360, via STEP.** Open or upload the `.step`. The products become named components and the carrier assemblies become a component tree, with colours as appearances. The reference file `docs/geometry/freeze-v010-CaCb.step` needs no FreeCAD at all. For other designs, the FreeCAD macro writes the STEP, and that STEP then opens in Fusion.

**Spark gaps, in the stack.** Rotor and stator counter-rotate, so each rotary gap sits in the axial gap between the rotor face and the stator face it joins, in a ring reserved beyond the capacitor electrodes:
- the **bar band** (r375) in the Cx gap holds the load, fire and backstop gaps, with the island-bar tips on tabs;
- the **rail band** (r410) in the C1/C2 gap holds the returns.

The page shows them in the "gaps A" and "gaps B" plan views and in the axial section, and their parameters are in the "spark gaps" group. Buttons of a foreign node are fed by leads over the rotor rims along the stator frame; SG4a and SG3a are the crossovers. A standing check verifies that no rotor part shares (r, z) with any stator part once both are revolved.

**Z-stretch.** The two foils of a node are joined through their carrier by explicit links, so the carrier's thickness is free along z. With **Z-stretch = auto** (stack group), each carrier grows to hold its seated buttons and embedded leads (recess + seat + lead + cover), and the stack height shows the stretch. **Z-stretch = fixed** keeps the base thicknesses, and the checks show the shortfall. Every gap electrode has a lead embedded in its carrier to a foil of its own node. No capacitance changes.

The stack order and the base carrier/foil thicknesses are [IR] placeholders (the DXF has no axial section). See `sim/pump-geometry-findings.md`.
