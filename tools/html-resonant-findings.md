# Findings — HTML-RESONANT: the design assistant rewired onto the resonant machine

**Branch** `html-resonant` (off `solver-consolidation`). **Verdict:** **`HTML-RESONANT-LIVE`.** The
Pyodide assistant (`tools/charge-pump-synth-live.html`) is off the old direct machine (η 0.386) and
onto the **consolidated resonant machine (η_real ≈ 0.70, real spark-gap commutator, firing geometry)**.
`evaluate_design` now returns the **dual anchor** (resonant operating + frozen direct regression); the
expanded decision space (Lx, V_strike, r, d_ball, FE) drives new readouts and lamps; the page asserts a
**dual canary** on load with **no silent fallback**. The frozen computational anchors stay
byte-identical.

## §-checks (brief §5)

| # | check | result |
|---|---|---|
| 1 | frozen empty-diff; live solver loads **cores only** (no offline sweeps); git-diff out of live path | ✓ anchors+cores byte-identical; REPO_FILES = cores + design_synth (no firing_geometry/commutator_real **drivers**); the `subprocess git diff` is in `main()` only, never in `evaluate_design` |
| 2 | **dual canary** in-browser: resonant η ≈ 0.70 **and** z(α→0) = 1.334, matching the CLI | ✓ contract verified (table below) |
| 3 | new free vars move the readouts | ✓ V_strike→α_max/η_real; r/d_ball→cross-fire; FE→budget→η_real (table below) |
| 4 | new lamps fire | ✓ I11 cross-fire amber/fail as r↓/ball↑; I13 FE-budget tracks the bleed |
| 5 | conservation closes + trips at the operating point | ✓ the resonant cores' independent i²R-vs-bookkeeping guard (9.4e-12 / trips +5%); I1 ledger closes+trips |
| 6 | anti-staleness link stated | ✓ the offline sweeps are the validation suite (named, **not** loaded in-browser) |
| 7 | `index.html` retired/labelled | ✓ loud RETIRED banner → points to the live tool; dropped from the frozen-anchor check |

## 1. The integrated `evaluate_design` (the live solver)

`sim/design_synth.py` gains `operating_point(d)` — composing the **live cores + firing closed forms**:
- **`commutator_real_core`** → the V_strike spark-gap holdoff: `α_max`, `z_resonant`, `η_gross`, and the
  **FE/arc budget** (`fe_arc_budget`, dwell = the electrode-overlap time) → **η_real ≈ 0.70**.
- **`island_resonant_core`** → the island ring t½ (from Lx) for the timing guard.
- **firing-geometry closed forms** (distilled, not the sweep): `overlap_deg = (d_ball+2·g_lat)/r`,
  cross-fire margin vs the SG3b–BS3 2.95° spacing, overlap-time vs t½.

**Dual return:** `evaluate_design` returns `operating` (the resonant machine the HTML shows) **and**
`regression` (`z_direct` = `doubler_core` at α→0 = 1.334 — the canary). **Glue refactor:** the
`subprocess git diff` frozen-check stays in `main()` (offline); `evaluate_design`/`synthesize` are
I/O-free and Pyodide-safe (verified: JSON round-trips cleanly, no numpy types leak).

## 2. Expanded decision space + invariants

New free vars (defaulting to the established resonant anchor): `Lx_mH=1.0`, `V_strikeV=20 kV`,
`r_gapMm=387`, `d_ballMm=12`, `FE_uA=30`. New invariants, added to the I1–I10 battery (now **13**):
- **I11 cross-fire** — `overlap < ` SG3b–BS3 spacing (firing-geometry A2).
- **I12 resonant-timing** — `t_overlap ≥ t_strike+t½+t_cond` (the A1 guard; never binds).
- **I13 FE-budget** — `η_real > η_direct` after the FE bleed + arc.

## 3. The dual canary — in-browser vs CLI (brief §4)

The in-browser solver runs the **same unmodified `design_synth.py`** under Pyodide, so the numbers
match the CLI **by construction**. CLI reference (what the in-browser canary asserts):

| rung | quantity | value | canary test |
|---|---|---|---|
| **operating** | η_real | **0.7034** | \|η_real − 0.70\| < 0.03 → ✓ |
| operating | α_max | 0.8067 | (readout) |
| operating | z_resonant | 2.478 | (readout) |
| **regression** | z(α→0) | **1.3336** | \|z − 1.334\| < 5e-3 → ✓ |
| regression | η_direct | 0.3863 | \|η − 0.386\| < 3e-3 → ✓ |
| both | rotor / invariants | 983 mm / **13/13** | dia ∈ [960,1010], all pass, feasible → ✓ |

**Badge:** `SOLVER: live` only if **both** rungs reproduce; `SOLVER: CANARY-FAIL` if either drifts;
`SOLVER: down` (no hard-coded substitute) if Pyodide/a core fails to load. *Note: this sandbox has no
in-browser CDN, so the end-to-end Pyodide load is confirmed at the data-contract level (the canary reads
exactly the fields the CLI emits, which reproduce); the final live load is a serve-from-repo-root step in
TMD's environment — and on failure the page says `SOLVER: down`, never falls back.*

## 4. Readouts & lamps move with the inputs (checks 3, 4)

| input change | effect (verified live) |
|---|---|
| V_strike 20→30 kV | α_max 0.81→1.0, **η_real 0.70→0.96** |
| V_strike 20→15 kV | α_max 0.81→0.70, η_real 0.70→0.60 |
| r_gap 387→250 mm | cross-fire margin +0.88°→**−0.26° (I11 FAIL/amber)** |
| d_ball 12→18 mm | cross-fire margin +0.88°→−0.01° (I11 trips) |
| FE 30→300 µA | FE+arc budget 0.18→1.43 mJ, η_real 0.70→0.66 (I13 tracks) |

The cross-fire readout is colour-coded (green > 0.3° · amber < 0.3° · red < 0). The direct-z readout is
amber when the regression doesn't reproduce.

## 5. HTML interface delta (brief §3)

- **New "Commutation / firing" input tier:** Lx, V_strike (kV slider → V_strikeV), gap radius r, ball
  d_ball, FE leakage — grouped, established defaults, host idiom (`FREE_KEYS`/`liveEval`/`readFree`).
- **New readouts:** the **resonant machine panel** (η_real headline, α_max, z_resonant), the **firing
  geometry panel** (cross-fire °, overlap/t½ µs, FE+arc mJ), and the **direct regression panel**
  (z(α→0), η_direct) — the operating machine is the headline; the frozen baseline is the regression line.
- **New lamps:** I11 cross-fire, I12 resonant-timing, I13 FE-budget — rendered automatically by the
  battery loop (now numeric-ordered I1…I13), the binding one flagged.
- **Entry points unchanged:** `evaluate_design`/`synthesize`/`established_anchor` — new internals,
  minimal shell change (added the 3 resonant cores to the fetched file list).
- **Footer rewritten** to the honest character: two anchors / one canary; the resonant cores' genuinely
  independent guard distinguished from I1's consistency-check-that-trips; the anti-staleness link stated.

## 6. `index.html` retired (check 7)

A loud **RETIRED** banner now tops `index.html`, marking it the static direct-machine (η 0.386)
fallback and linking to the live resonant assistant. It is dropped from `design_synth`'s frozen-anchor
git-diff (it is no longer a computational anchor — the frozen set is `doubler_core`/`shuttle_core`/
`resonator_sim`). (Full deletion is TMD's call; the labelled banner avoids a second *trusted* source.)

## Deliverables

`tools/charge-pump-synth-live.html` (rewired: firing tier, resonant + regression readouts, I11–I13
lamps, dual canary, honest footer) · `sim/design_synth.py` (the integrated dual-return `evaluate_design`
+ `operating_point` + I11–I13 + the glue refactor) · this findings doc · `index.html` (retired banner).
Frozen computational anchors (`doubler_core`/`shuttle_core`/`resonator_sim`) byte-identical; the resonant
cores reused unmodified. **Not merged** (goes live on TMD's nod; the ngspice cross-validation is the
separate Phase-6 capstone).
