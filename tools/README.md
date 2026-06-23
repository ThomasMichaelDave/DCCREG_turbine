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

### numpy parity — the live cores must run on Pyodide's numpy *and* the CLI's

The cores are validated on the **CLI numpy (2.x)** but **run in-browser on Pyodide 0.26.2's numpy
(1.26.4)**. The numpy-2.0 rename means a name can work on one side and crash the other (e.g. `np.trapezoid`
exists only on 2.x, `np.trapz` only on 1.x — they share **no** single name). A 2.0-only name sails the CLI
and then hard-fails the browser load with `SOLVER: down`. The guard against that whole class:

```bash
make pyodide-parity        # runs every live core + the dual canary under BOTH numpy 1.26 and 2.x
```

This builds a `.pyodide-parity/` venv pinned to **numpy 1.26.4** (the Pyodide 0.26.2 bundle — the local
proxy for the in-browser numpy), runs `sim/pyodide_parity.py` under it **and** under the CLI numpy, and
writes `numpy_parity.txt` (the two-version pass table). Green on both ⇒ the in-browser load is guaranteed
numpy-wise. Renamed-function calls use the version-agnostic shim
`_trapz = getattr(np, "trapezoid", getattr(np, "trapz", None))`, never a bare `np.trapezoid`/`np.trapz`.

## Using it

- **Free-variable sliders** (left) roam the dimension space; each change calls `evaluate_design` live
  (debounced, with a spinner). z/η/W_coll track the ratios — they are not pinned.
- **"Solve"** (with an objective) calls `synthesize` — the full constrained search (a few seconds the
  first time, then cached); it pushes the optimal dimensions back onto the sliders.
- **Invariant lamps** (right): green = pass, amber = the **binding** constraint, red = fail. Slack is the
  uniform "fraction of headroom to the bound."
- **"ⓘ reference"** opens the drawer (closed by default): the **schematic container** (hosts the KiCad
  `varcap.svg`, click-to-enlarge), the **legend + live-value table** (label-matched to the schematic),
  the **consistency stamp** (KiCad netlist ↔ design topology), the cross-section, and the glossary.

## The schematic is KiCad's (TMD authors; the tool hosts + checks)

The container hosts the KiCad SVG and verifies its netlist against the design topology — it does **not**
draw a schematic. TMD re-exports on a design change:

```bash
kicad-cli sch export svg     --output tools/            varcap.kicad_sch   # -> tools/varcap.svg
kicad-cli sch export netlist --format spice --output tools/schematic.cir   varcap.kicad_sch
git add tools/varcap.svg tools/schematic.cir && git commit
```

The container is a **drop-in**: once `tools/varcap.svg` is committed it appears in the slot with no code
change (until then the slot shows the labelled interim stand-in `tools/schematic.svg`). The stamp reads
**MATCH** (KiCad netlist = the 42-component / 22-node design graph), **⚠ MISMATCH** (re-export needed),
or **AWAITING-KICAD** (no `tools/schematic.cir` committed yet).

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
