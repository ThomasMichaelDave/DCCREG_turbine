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
