# tools/ — the live design synthesizer

`charge-pump-synth-live.html` is the design synthesizer as an interactive instrument, backed by the
**real `sim/design_synth.py` + the frozen solvers** running client-side in **Pyodide**. The HTML is a
thin shell; all z / η / W_coll and the invariant logic are the repo's Python (the frozen solver is the
sole authority and is never re-implemented in JS).

## Run it

**Serve from the repo root** (not `file://` — the page fetches `../reference/*.py`, which `file://`
blocks):

```bash
cd <repo-root>
python3 -m http.server 8000
# then open:
#   http://localhost:8000/tools/charge-pump-synth-live.html
```

- **First load needs internet** — Pyodide + numpy come from the jsdelivr CDN. After the first load the
  browser caches them (local thereafter).
- **Serve from the repo ROOT, not from inside `tools/`** — the page fetches `../reference/doubler_core.py`,
  `../shuttle_core.py`, `../sim/design_synth.py`, `../presets/G3-geometry-v010.json`, etc. Serving from
  inside `tools/` makes those `../` fetches 404.

## The badge IS the acceptance test

| badge | meaning | trust? |
|---|---|---|
| **`SOLVER: live`** (green) | the in-browser solver reproduced the established machine (canary: rotor 983 mm, z 1.3336, η 0.3863) | **yes** — z/η are the live frozen solvers |
| **`SOLVER: CANARY-FAIL`** (red) | the in-browser numbers disagree with the established anchor (a vendoring/Pyodide numeric drift) | **no** — do not trust until it reproduces |
| **`SOLVER: down`** | Pyodide/numpy didn't load | **no** — fix serve-from-root / CDN access |

The page **never** falls back to hard-coded z/η — a synthesizer that quietly stops using the solver is
worse than one that says it's down.

## Using it

- **Free-variable sliders** (left) roam the dimension space; each change calls `evaluate_design` live
  (debounced, with a spinner). z/η/W_coll track the ratios — they are not pinned.
- **"Solve"** (with an objective) calls `synthesize` — the full constrained search (a few seconds the
  first time, then cached); it pushes the optimal dimensions back onto the sliders.
- **Invariant lamps** (right): green = pass, amber = the **binding** constraint, red = fail. Slack is the
  uniform "fraction of headroom to the bound."
- **"ⓘ reference"** opens the drawer (closed by default) mapping every value to the schematic node and the
  cross-section feature, with both SSOT-generated artifacts.

## Troubleshooting

- **fetch 404s** → you served from inside `tools/` instead of the repo root.
- **stuck "booting…"** → offline / a proxy is blocking the Pyodide CDN.
- **port busy** → `python3 -m http.server 8001` (or any free port).
- **reference SVGs missing** → run `python3 tools/gen_artifacts.py` to regenerate `cross-section.svg`
  (from the DXF) and `schematic.svg` (from `topology_edge_list.csv`).

## Files

| file | what | source of truth |
|---|---|---|
| `charge-pump-synth-live.html` | the instrument (single file; fetches the frozen `.py` from `../`) | — |
| `reference.md` | the reference text (rendered into the ⓘ drawer) | this file |
| `cross-section.svg` | the ref-radii + named features | the DXF (via `gen_artifacts.py`) |
| `schematic.svg` | the nodes + components | `topology_edge_list.csv` (via `gen_artifacts.py`) |
| `gen_artifacts.py` | regenerates the two SVGs + the connectivity check | — |

The frozen solvers (`reference/doubler_core.py`, `shuttle_core.py`) are **read-only** and stay
byte-identical; the page loads them unmodified.
