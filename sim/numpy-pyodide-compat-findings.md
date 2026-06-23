# NUMPY-PYODIDE-COMPAT — findings

**Verdict: `NUMPY-COMPAT-CLEAN`.** The version-safe `trapz`/`trapezoid` shim is in; the sweep found and
fixed **every** version-fragile numpy name in the live cores (two `np.trapezoid` calls, not one); a
numpy-1.26 parity venv (the local Pyodide-numpy proxy) runs every HTML-loaded live core + the dual canary
**green under both numpy 1.26.4 and the CLI's 2.4.6**; and the parity check is wired as a standing guard
(`make pyodide-parity`) so the whole class can't regress silently. No frozen-core version-fragile name →
**no `FROZEN-CORE-CONFLICT`**. *Status: [ME]/[OC] — pure tooling, firewall intact, mergeable.*

## What surfaced

The first real in-browser load failed `SOLVER: down`: `commutator_real_core` calls **`np.trapezoid`** (the
numpy-2.0 name), but **Pyodide 0.26.2 ships numpy 1.26.4**, which only has **`np.trapz`**. The CLI never
caught it — the CLI numpy is **2.4.6**, which has `trapezoid` and has *removed* `trapz`. The two
environments sit on **opposite sides of the numpy-2.0 rename and share no single name**, so:

- a bare `np.trapezoid` → crashes the browser (Pyodide 1.26),
- a bare `np.trapz` → would crash the CLI (numpy 2.4),
- **only a version-agnostic shim works on both.**

The canary did its job — it fail-closed (`SOLVER: down`, no hard-coded fallback). This block stops the
failure at the source and adds the guard that catches the whole class locally.

## The five named checks (brief §6)

### 1. The shim is in; computes identically on 2.4 and 1.26
After `import numpy as np`, in each affected module:
```python
_trapz = getattr(np, "trapezoid", getattr(np, "trapz", None))  # 2.x: trapezoid; Pyodide 1.x: trapz
```
Resolves to `trapezoid` on numpy 2.4.6 and `trapz` on 1.26.4 — confirmed by the parity run's banner
(`trapz=trapezoid` vs `trapz=trapz`). Both compute the same integral; the exercised paths
(`commutator_real_core.fe_arc_budget`, `energy_balance.tau_profile`) pass identically under both.

### 2. The sweep — every version-fragile numpy name in the live cores
Swept every `np.<name>` across all HTML-loaded modules (`design_synth` + every `reference/` core it imports
+ `shuttle_core`, `energy_balance_from_solver`, `island_charging_cosim`) against **both** fragile lists:
the 2.0-introduced names absent in 1.26 (`trapezoid`, `concat`, top-level `astype`, `cumulative_sum/prod`,
`unstack`, …) and the 1.x-removed names absent in 2.x (`trapz`, `in1d`, `row_stack`, `product`,
`alltrue/sometrue`, `NaN/Inf`, `float_`, …).

**Full attribute set used by the live cores:**
`array, asarray, empty, exp, gradient, inf, linalg, linspace, logspace, max, mean, median, pi, sin, sqrt,
zeros` — plus `trapezoid`/`trapz` (only inside the `getattr` shim).

**Version-fragile names found = `np.trapezoid` only**, in **two** places (the brief flagged one):

| file:line | was | now |
|---|---|---|
| `reference/commutator_real_core.py:137` | `np.trapezoid(...)` | `_trapz(...)` |
| `energy_balance_from_solver.py:154` | `np.trapezoid(...)` | `_trapz(...)` |

Everything else in the used set exists, unchanged, in both 1.26 and 2.x (`np.inf` is lowercase — fine; the
removed name is `np.Inf`). The hand-rolled "trapezoidal" loops in `island_resonant_core`,
`fire_tank_transfer`, `resonator_sim` are manual sums, **not** `np.trapz` calls — not fragile.

> The enumerated list is not the authority — §3's two-version parity run is. It passes.

### 3. The numpy-1.26 parity venv — green on both
`.pyodide-parity/` pinned to **numpy 1.26.4** (the Pyodide 0.26.2 `pyodide-lock.json` bundle; confirmed
`has trapz: True / has trapezoid: False` — exactly the in-browser numpy). `sim/pyodide_parity.py` runs
every live core's self-test **and** the dual-canary path, exercising the live `_trapz` in both
`commutator_real_core.fe_arc_budget` and `energy_balance.tau_profile`:

| check | numpy 1.26.4 | numpy 2.4.6 |
|---|---|---|
| doubler_core.run_self_test (4 anchors) | PASS | PASS |
| island_resonant_core.integrate (LC ring) | PASS | PASS |
| doubler_resonant_core.run_self_test | PASS | PASS |
| commutator_real_core.run_self_test (_trapz in fe_arc_budget) | PASS | PASS |
| commutator_real_core.fe_arc_budget (_trapz live) | PASS | PASS |
| energy_balance_from_solver.selftests | PASS | PASS |
| energy_balance.tau_profile (_trapz live) | PASS | PASS |
| shuttle_core import (frozen anchor) | PASS | PASS |
| island_charging_cosim import | PASS | PASS |
| dual canary: operating η 0.5180 ∈ (0.44, 0.55) | PASS | PASS |
| dual canary: regression z 1.3336 == 1.334 | PASS | PASS |
| dual canary: regression η 0.3863 == 0.386 | PASS | PASS |
| dual canary: feasible + all 13 invariants | PASS | PASS |
| **RESULT** | **ALL GREEN (13/13)** | **ALL GREEN (13/13)** |

The two-version pass table is written to `numpy_parity.txt`. Under numpy 1.26 this run **passes where a bare
`np.trapezoid` would have crashed** — the regression is now guarded.

### 4. The standing check wired + documented
- **`make pyodide-parity`** (or `bash sim/run_pyodide_parity.sh`) builds the venv if missing, runs
  `sim/pyodide_parity.py` under **both** the 1.26.4 venv and the CLI numpy, and writes `numpy_parity.txt`.
  Non-zero exit on any failure (CI-ready).
- **Pinned parity version: numpy 1.26.4** (recorded in the `Makefile`, `run_pyodide_parity.sh`, and the
  docs).
- Numpy-compat note added to **`tools/README.md`** (next to the `SOLVER: down` row) and **`CONVENTIONS.md`**
  (working conventions): the live cores must run under both numpys; use the shim, never a bare name; the
  parity venv is the guard.
- **`solver_inventory.csv`** gains a `numpy_compat` column — the two shimmed cores marked
  `shim _trapz … parity-green`, the other live-loaded cores `parity-green (1.26 & 2.x)`, offline modules
  `offline (not browser-loaded)`.

### 5. Frozen-core handling — clean, nothing flagged
Frozen cores (`reference/doubler_core.py`, `shuttle_core.py`, `sim/resonator_sim.py`) swept for **2.0-only**
names (the only frozen risk — a 1.x environment can't run a 2.0-new name): **none found, all clean.** No
frozen core touched; their git diff is empty. → **no `FROZEN-CORE-CONFLICT`.** The two shimmed modules
(`commutator_real_core`, `energy_balance_from_solver`) are **live diagnostic/consumer cores, not frozen
anchors**, so the version-agnostic edit is in-policy.

## Deliverables
- `reference/commutator_real_core.py`, `energy_balance_from_solver.py` — the `_trapz` shim (version-safe).
- `sim/pyodide_parity.py` — the parity guard (every live core + dual canary; version-agnostic numpy only).
- `sim/run_pyodide_parity.sh` + `Makefile` (`make pyodide-parity`) — the standing two-version check.
- `.pyodide-parity/` venv (numpy 1.26.4; gitignored — recreate with `make pyodide-parity-venv`).
- `numpy_parity.txt` — the two-version pass table (both ALL GREEN 13/13).
- `tools/README.md` + `CONVENTIONS.md` numpy-compat note (pinned 1.26.4); `solver_inventory.csv`
  `numpy_compat` column.

**Frozen anchors empty-diff. `NUMPY-COMPAT-CLEAN` — mergeable: a real load-blocking bug fix + a regression
guard, not an exploration.**
