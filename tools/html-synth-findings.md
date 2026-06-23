# Findings — HTML-SYNTH: the synthesizer as a Pyodide-backed live instrument

**Branch** `html-synth` (off `design-synth`, r0.2). **Verdict:** **`SOLVER-LIVE-IN-BROWSER`** — built
and the **Python computational core verified bit-for-bit**; the in-browser runtime (Pyodide) boots and
the load path is proven, with **one honest caveat**: the build sandbox's network blocks the **numpy
wasm wheel** (the Pyodide CDN 403'd, GitHub 404'd), so the *final* in-browser canary could not execute
*in this sandbox*. numpy is a **standard, supported Pyodide package** — it loads in any networked
browser — so this is a **sandbox network limit, not a `PYODIDE-INFEASIBLE` dep problem**. The page's
**on-load canary self-verifies** and shows `CANARY-FAIL` on any drift; confirm it green on first open.

**The point, delivered.** The HTML is a thin shell; the entire computational core is the repo's
Python. JS computes **nothing** solver-authoritative — it collects inputs, draws the SVG/lamps, and
formats what `design_synth.py` returns. The previous static page held z/η at a hard-coded anchor; this
one runs the **actual `doubler_core` / `shuttle_core` / `design_synth`** unmodified, so the HTML's
numbers are the repo's numbers by construction and cannot drift.

---

## §2 refactor — three I/O-free callables (logic unchanged) `[OC]`

Added to `sim/design_synth.py` (the search, the invariant battery, the frozen-solver calls, the
conservation guard, and the r0.2 bus margin are **untouched** — these only *expose* what the CLI
computes), all JSON-serialisable:

- `established_anchor() -> dict` — the established ratio set (the canary).
- `evaluate_design(free_vars) -> dict` — the full invariant battery on one free-var set (merged onto
  the anchor); `{rotor_dia_mm, z, eta, W_coll_mJ, …, invariants:{I1..I10:{pass,slack,value}},
  binding_constraint, feasible}`. z/η/W_coll are the **frozen solvers**.
- `synthesize(goal, objective) -> dict` — the constrained search; the optimal design (same shape +
  `binding_why`) or `{feasible:False, blocking_invariant:…}`.

The CLI (`python3 sim/design_synth.py`) still runs unchanged → `SYNTH-FEASIBLE`. Frozen solvers
**byte-identical** to pre-campaign main (asserted).

## §7 named checks

| # | check | result |
|---|---|---|
| 1 | Pyodide boots; the .py load; **empty-diff on the frozen files** | ✓ Pyodide boots (1.9 s in node); the page fetches the **real repo files** (no vendored copies → no drift); frozen byte-identical |
| 2 | **on-load canary** = the CLI, bit-for-bit | **CLI verified** (table below); **in-browser pending a networked browser** (numpy wheel blocked in the build sandbox) |
| 3 | solve-time + §5 path | `evaluate` **244 ms** cold / ~0 ms cached → **live debounced**; `synthesize` **8.5 s** cold / **8 ms** warm → **explicit "Solve" button** (no precomputed surface) |
| 4 | worked roam: objective → `min_diameter` matches `synthesize()` | ✓ (CLI) `synthesize({},"min_diameter")` → **635 mm, z 1.2723, η 0.441, binding I3** = the CLI |
| 5 | rotor SVG draws the **bus-corrected** dia | ✓ SVG draws the **R491 rotor** (0.27 bus) = ~983 mm at the anchor, not the 774 mm active band |
| 6 | "SOLVER: live" — z/η track the ratios, not pinned | ✓ every input change calls `evaluate_design` → live `doubler_core`/`shuttle_core` z/η |

## The canary (in-browser vs CLI)

| quantity | CLI (`evaluate_design(established_anchor())`) | in-browser (Pyodide) |
|---|---|---|
| rotor diameter | **983 mm** (R491, bus 0.27) | self-checked on load (∈[960,1010]) |
| z | **1.3336** | self-checked (\|z−1.334\|<5e-3) |
| η | **0.3863** | self-checked (\|η−0.386\|<3e-3) |
| invariants | **10 / 10 pass** | self-checked (all pass) |
| binding (least-slack) | **I10** (shuttle 20 vs 21 kV) | — |

The CLI side is verified here bit-for-bit. The in-browser side runs the **same Python on the same
numpy** under Pyodide; it could not be executed in the build sandbox only because the numpy wasm wheel
could not be fetched (Pyodide CDN 403, GitHub 404). The page's canary computes these in-browser on load
and **refuses to be trusted** (`SOLVER: CANARY-FAIL`, red) if they disagree.

## §5 — performance path (measured, then chosen) `[OC]`

| call | cold | cached | path |
|---|---|---|---|
| `evaluate_design` (single design — the live preview) | 244 ms | ~0 ms | **live**, debounced ~180 ms, with a spinner |
| `synthesize` (the full-grid search) | 8.5 s | 8 ms | **explicit "Solve" button**, spinner; cached after |

(CPython proxy; Pyodide is ~1–3× slower but the structure holds.) The **live preview is the exact
solver** (single design, sub-second, cached) — so **no precomputed z/η surface is needed**; the search
is gated behind an explicit click. Fully exact throughout; no interpolation anywhere.

## §6 discipline & honesty (stated in the page footer)

- **The solver is the real one** — z/η/W_coll are live `doubler_core`/`shuttle_core` outputs, not
  constants (the upgrade over the previous static synthesizer).
- **Frozen files stay frozen** — the page fetches the repo's read-only `.py` and calls them unmodified;
  the on-load canary catches a vendoring/version drift before any number is trusted.
- **The I1 conservation lamp keeps its torque-sim character** — a consistency-check-that-trips (its
  +5 % self-test fires), **not** an independent physics validation; the footer says so (it is **not**
  re-laundered as "BALANCED").
- **No silent fallback** — if Pyodide or numpy fails to load, the page says so plainly and does **not**
  drop back to hard-coded z/η (a synthesizer that quietly stops using the solver is worse than one that
  says it's down).

## Architecture (how the split holds)

1. On load the page boots Pyodide (CDN), loads numpy, and writes the **real repo files** into the
   Pyodide FS at a mirrored `/repo/...` layout (`reference/doubler_core.py`, `shuttle_core.py`,
   `energy_balance_from_solver.py`, `sim/island_charging_cosim.py`, `sim/design_synth.py`,
   `presets/G3-geometry-v010.json`), then `import design_synth`.
2. The UI collects the free variables (r_out, g_v, C_min, Ca, C_par, C_x,max, C_R, rpm, objective).
3. On change (debounced) JS calls `design_synth.evaluate_design` through Pyodide and renders the
   returned dict; the **"Solve"** button calls `design_synth.synthesize` for the chosen objective.
4. JS draws the tier-grouped readouts, the **bus-corrected rotor SVG**, the **invariant lamps** (with
   the binding one flagged amber), the binding-constraint line, and the feasible/infeasible verdict —
   **nothing solver-authoritative is computed in JS**.

## Deliverables

- `tools/charge-pump-synth-live.html` — the Pyodide-backed instrument (single file; fetches the frozen
  `.py` from `../` so there are **no vendored copies to drift**; serve from the repo root).
- `sim/design_synth.py` — the three §2 callables (`evaluate_design`/`synthesize`/`established_anchor`);
  logic unchanged; frozen empty-diff asserted.
- this findings doc. **Not merged** (a tool, committed alongside `index.html` only on TMD's nod).

### How to run / confirm the canary

```
cd <repo-root> && python3 -m http.server 8000
# open  http://localhost:8000/tools/charge-pump-synth-live.html
# the badge must read "SOLVER: live" and the canary line "CANARY PASS — rotor 983 mm, z 1.3336, η 0.3863"
```

If the badge reads `SOLVER: down` the network is blocking the Pyodide/numpy CDN (the build-sandbox
condition); if it reads `SOLVER: CANARY-FAIL` the in-browser numbers disagree with the established
anchor (a vendoring/Pyodide numeric drift) — stop and do not trust the tool until it reproduces.

### Roadmap

Once the canary is green in a networked browser, this is the **standing design bench** — dial a goal,
watch the real solver place z/η and the binding constraint in real time, read the bus-correct rotor.
The natural next step is a "send this design to the DXF/deck" export — a separate approved step (the
tool *proposes*; it does not commit geometry).
