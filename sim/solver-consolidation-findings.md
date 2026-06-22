# Findings — SOLVER-CONSOLIDATION: the stack audit + the integrated-solver rewrite spec

**Branch** `solver-consolidation` (off `firing-geometry`). **Verdict:** **`CONSOLIDATION-MAPPED`.** The
whole stack is inventoried and classified against **actual code** (`solver_inventory.csv`), every
headline result reproduces live (no `STACK-DISCREPANCY`), and the three resonant **live cores are
import-clean *and* I/O-free** (no `CORE-REFACTOR-NEEDED`). The integrated architecture is specified
end-to-end below, with a concrete rewrite punch-list. **No code changed** (audit/spec only;
frozen-and-everything empty-diff).

The motivating gap is real and named: **`index.html` still runs the OLD DIRECT machine (η 0.386)** while
the validated operating machine is the **resonant one (η ≈ 0.70, real spark-gap commutator, DXF firing
geometry)**. This spec is what the rewrite executes so the HTML can never drift from the validated
physics again.

## Phase 1 — inventory & classification (verified against code)

Full table in `solver_inventory.csv` (36 entries). Tally: **3 FROZEN-ANCHOR · 3 LIVE-CORE · 1
SYNTH-GLUE · 6 OFFLINE-SWEEP · 1 CONSUMER · 3 TOOL · 18 ARCHIVAL · 1 FROZEN(STALE) HTML.**

### The consolidation-relevant stack

| module | class | computes | I/O-clean | verdict |
|---|---|---|---|---|
| `reference/doubler_core.py` | **FROZEN-ANCHOR** | direct Bennet z & node trace | yes (pure) | z 1.334 / η 0.386 |
| `shuttle_core.py` | **FROZEN-ANCHOR** | direct shuttle + the 8-gap arrangement | yes | BACKSTOP-CLEAN |
| `sim/resonator_sim.py` | **FROZEN-ANCHOR** | parallel-RLC tank transient (RK4) | yes (standalone) | TANK settles 15 kV |
| `reference/island_resonant_core.py` | **LIVE-CORE** | LC ring C_eff/Z/t½/i_pk/Q + loss + guard | **yes (I/O-free)** | RESONANT-TRANSFER-MODELED |
| `reference/doubler_resonant_core.py` | **LIVE-CORE** | resonant Bennet cycle, z(α), diode clamp | **yes (I/O-free)** | Z-RETUNED *(superseded)* |
| `reference/commutator_real_core.py` | **LIVE-CORE** | V_strike gap holdoff + FN FE/arc budget | **yes (I/O-free)** | **BRIGADE-RECOVERABLE (η≈0.70)** |
| `sim/design_synth.py` | **SYNTH-GLUE** | I1–I10 battery + search + binding report | import-clean; **git-diff subprocess in the report path** | DESIGN-SYNTH feasible |
| `sim/firing_geometry.py` | **OFFLINE-SWEEP** | overlap-window + cross-fire lookup | yes | STATIONS-CONFIRMED + HINTS |
| `sim/commutator_real.py` | **OFFLINE-SWEEP** | V_strike sweep + FE-budget grid | yes | → α_max(V_strike) |
| `sim/brigade_tax_localize.py` | **OFFLINE-SWEEP** | per-transfer tax (frozen trace) | reads preset JSON | → tax 11.19/8.39 mJ |
| `energy_balance_from_solver.py` | **CONSUMER** | η = dE/W_mech, the tax fraction | reads preset JSON | → W_mech 15.94, η 0.386 |
| `sim/sch_to_netlist.py` · `netlist_gaps.py` · `rederive_from_gaps.py` | **TOOL** | schematic→connectivity; 8-gap check | reads `.kicad_sch` | topology of record |

(18 ARCHIVAL block sims — torque, geom_extract/validate, battery_capacity, fire_tank_transfer,
island_charging, s2–s8, topology_recon, the `xsim_*`/`*_from_solver` helpers — earned their verdicts in
prior blocks and are **not in the live path**; kept as offline/regression record.)

### Code-vs-findings discrepancy audit (the standing verification discipline)

Every headline claim was re-run against the **actual code** — **all reproduce, zero discrepancies:**

| claim (findings) | live code | |
|---|---|---|
| doubler_core direct z 1.334 | **1.3340** | ✓ |
| doubler-resonant diode clamp z 1.573 / η 0.404 | **1.5727 / 0.4040** | ✓ |
| commutator-real α_max 0.807, η_real ≈ 0.70 | **0.807 / 0.697** | ✓ |
| island f_rec ≈ 0.996 (high Q) | **0.996** | ✓ |
| firing overlap 2.07° vs spacing 2.95° | **2.07 / 2.95** | ✓ |

**One supersession to record (not a discrepancy):** `doubler_resonant_core`'s `Z-RETUNED` (η 0.404) was
the **diode stand-in**; COMMUTATOR-REAL showed the diode-at-0 was an artifact and the **real spark-gap
holdoff gives η ≈ 0.70**. So `doubler_resonant_core` stays as a **diagnostic** core (the regression
between direct and commutator), but the **operating model is `commutator_real_core`**.

## Phase 2 — the integrated-solver architecture (the rewrite spec)

### 2.1 Two anchors (both returned by `evaluate_design`)

- **Direct-limit regression anchor** — frozen `doubler_core` at α→0 → **z 1.334 / η 0.386**. The canary
  that catches drift; the resonant model must reproduce it.
- **Operating point** — the **resonant machine**: `commutator_real_core` (real V_strike gap holdoff) →
  **α_max 0.807, z 2.478, η_real ≈ 0.70**, with the island transfer (`island_resonant_core`) recovering
  the downstream ~31 % and the DXF firing geometry (closed forms) gating it.

`evaluate_design(free_vars)` returns **both**: `operating = {eta_real, alpha_max, z_resonant, …}` and
`regression = {z_direct: 1.334, eta_direct: 0.386, reproduces: True}`.

### 2.2 Composition: fast-cores-live + closed-form invariants

```mermaid
flowchart LR
  subgraph LIVE["evaluate_design (per-drag, ms)"]
    FV[free vars: caps, Lx, V_strike, r, d_ball, FE, rpm]
    DC[doubler_core<br/>direct z/eta — REGRESSION] 
    CR[commutator_real_core<br/>alpha_max, eta_gross, FE/arc budget — OPERATING]
    IS[island_resonant_core<br/>f_rec(Q), island recovery]
    RES[resonator closed-form<br/>f0, eta_match]
    FG[firing closed-forms<br/>overlap=(d_ball+2g_lat)/r<br/>cross-fire & A1 margins]
    FV --> DC
    FV --> CR --> IS --> RES
    FV --> FG
    DC -. regression .-> OUT
    CR --> OUT[two-anchor result + lamps]
    IS --> OUT
    RES --> OUT
    FG --> OUT
  end
  subgraph OFFLINE["validation suite (on core change, not per-drag)"]
    SW[firing_geometry · commutator_real · resonant_brigade · doubler_resonant ·<br/>brigade_tax_localize · resonant_island · energy_balance]
    FROZ[frozen self-tests: doubler_core / shuttle_core / resonator_sim]
  end
  SW -. regenerates .-> FG
  SW -. regenerates .-> CR
  FROZ -. asserts .-> DC
```

**Data flow (a candidate design on paper):** free vars (G3 caps + Lx 1 mH + V_strike 20 kV + r 387 mm +
d_ball 12 mm + FE 30 µA + 3000 rpm) → `doubler_core` gives the **regression** z 1.334/η 0.386 →
`commutator_real_core.solve_doubler_commutator(V_strike/V_peak)` gives **α_max 0.807, z 2.478, η_gross
0.709** → `fe_arc_budget(…, t_dwell = overlap_time)` gives **η_real 0.70** → `island_resonant_core`
adds the downstream recovery → resonator closed-form gives **f0/η_match** → `firing_geometry`
closed-forms give **overlap 2.07°, cross-fire margin +0.88°, A1 margin 111 µs** → **lamps + two-anchor
η**.

### 2.3 The closed-form invariants (traced to the sweep that validated each)

| invariant (live check) | closed form | from sweep |
|---|---|---|
| **A2 cross-fire** | `Δθ_overlap = (d_ball+2·g_lat)/r < ` station spacing (2.95° tightest) | `firing_geometry` |
| **A1 resonant-timing** | `t_overlap = Δθ/ω ≥ t_strike+t½+t_cond` (never binds — keep as guard) | `firing_geometry` |
| **α_max(V_strike)** | monotone table/curve (0→0.28 diode … 0.807 @20 kV … 1.0 @30 kV) | `commutator_real` |
| **FE/arc budget** | `commutator_real_core.fe_arc_budget` (already a live func) | `commutator_real` |
| **brigade worth-it** | per-transfer tax (A 11.19 / B 8.39 mJ; C_eff 68.6 pF) recovered > ring loss | `brigade_tax_localize` + `resonant_brigade` |
| **island f_rec(Q)** | `1 − π/Q` (integrated) — live in `island_resonant_core` | `resonant_island` |

The **offline sweeps stay as the validation suite**: re-run on any core change (CI/`make validate`),
**regenerating the closed forms** — the anti-staleness link that keeps the live checks honest.

### 2.4 The expanded decision space & invariant map

**New free variables** (a "commutation / firing" tier): `Lx_mH`, `V_strike_kV`, `r_gap_mm`,
`d_ball_mm`, `FE_leakage_uA`, `rpm` (joining the existing geometry caps C1/C2/Ca/Cb/Cx, C_R/L_R).

**Invariant map** — existing I1–I10 (`design_synth`) kept; **I10 already carries the resonant Lx +
brigade-clocking sub-checks**. New:

| check | test | source |
|---|---|---|
| **I11 cross-fire (A2)** | `Δθ_overlap < ` nearest station spacing | firing_geometry |
| **I12 resonant-timing (A1)** | `t_overlap ≥ t_strike+t½+t_cond` (guard; never binds) | firing_geometry |
| **I13 FE-budget** | `η_real > η_direct` after FE/arc; backstop leakage within design | commutator_real_core |
| **I1′ resonant conservation** | the independent i²R-vs-bookkeeping guard closes ~1e-12 **and** trips +5 % | island/commutator cores |

**Updated anchor numbers:** operating **η₀ → 0.70**, **z_operating → 2.48**; the frozen **η 0.386 / z
1.334** retained **only as the regression**. (I3's [1.20, 1.45] z-band stays a check on the *direct
regression* z, not the operating z — the band validated the direct device; the operating z 2.48 is a
readout.)

### 2.5 The HTML interface delta

- **Entry points (unchanged signatures, new internals):** `evaluate_design(free_vars)` →
  `{operating, regression, lamps}`; `synthesize(goal, objective)`; `established_anchor()` → the
  **resonant** machine (η 0.70) with the frozen regression attached.
- **New inputs** — a **"Commutation / Firing" tier**: `Lx_mH`, `V_strike_kV`, `r_gap_mm`, `d_ball_mm`,
  `FE_leakage_uA`, `rpm` (host idiom: `FIELDS`/`state`/`bindField`/URL-hash; no localStorage).
- **New readouts:** η_real (≈ 0.70), α_max, z_operating, cross-fire margin (°), overlap/t½ margin (µs),
  FE + arc budget (mJ/cyc), island recovery; **z_direct/η_direct as the regression line**.
- **New lamps:** **cross-fire (A2)**, **resonant-timing (A1)**, **FE-budget**, plus the existing I1–I10
  battery.
- **The canary:** opens on the **resonant** established machine (η 0.70) and still asserts the **direct
  regression (α→0 → z 1.334)** under the hood — the engine badge stays green only if both hold.

## Phase 3 — the rewrite punch-list (what the rewrite brief executes)

1. **Cores: no refactor needed.** `island_resonant_core`, `doubler_resonant_core`,
   `commutator_real_core` are import-clean **and** I/O-free → drop straight into Pyodide. *(verified)*
2. **`design_synth` glue refactor:** move the **subprocess `git diff` frozen-check out of the live
   invariant battery** into an offline validation step (Pyodide has no git). The `ESTABLISHED` anchor is
   already inlined (no preset file); the I1–I10 functions are pure and stay live.
3. **Extract the closed forms into a live module:** `overlap_deg`/`nearest_spacing` (pure in
   `firing_geometry` — import directly); `α_max(V_strike)` (compute live via
   `solve_doubler_commutator`, or ship the monotone table); the brigade per-transfer tax + worth-it as
   constants. *(these are the I11–I13 live checks)*
4. **Resonator:** use the **closed-form f0/η_match live**; keep `resonator_sim`'s RK4 transient as
   **offline** validation (it is standalone/frozen).
5. **Inline the G3 preset** caps into the HTML `state` defaults (no JSON file fetch in Pyodide) — they
   are already the `design_synth.ESTABLISHED` + `FIELDS` values.
6. **Stand up the offline validation suite** as the anti-staleness link: `firing_geometry`,
   `commutator_real`, `resonant_brigade`, `doubler_resonant`, `brigade_tax_localize`, `resonant_island`,
   `energy_balance` + the frozen self-tests — run on core change, regenerating §2.3's closed forms.
7. **`index.html` rewrite:** replace the direct-machine compute with `evaluate_design` composing the
   live cores + closed forms; add the commutation/firing input tier + the new readouts/lamps; the canary
   opens resonant and asserts the frozen regression.

## Named checks (brief §)

1. ✓ `solver_inventory.csv` complete (36 modules classified); **no code-vs-findings discrepancies**
   (5/5 headline claims reproduce live); one **supersession** recorded (doubler-resonant → commutator).
2. ✓ Each LIVE CORE confirmed **import-clean + I/O-free** (no refactor); `design_synth`'s subprocess
   git-diff named as the one glue refactor (it is SYNTH-GLUE, not a core).
3. ✓ Composition order + shared params specified end-to-end (§2.2; a candidate design flows through).
4. ✓ Closed-form invariants traced to the validating sweep (§2.3).
5. ✓ Two-anchor scheme stated; both the operating η and the frozen regression in `evaluate_design`
   (§2.1).
6. ✓ HTML interface delta — inputs/readouts/lamps/entry points (§2.5).
7. ✓ The rewrite punch-list (§Phase 3).

## Deliverables

`solver_inventory.csv` · this `sim/solver-consolidation-findings.md` (architecture + rewrite spec +
composition diagram + punch-list). **No code changes; frozen empty-diff asserted. Not merged** (a
planning artifact — the rewrite brief executes against this spec).
