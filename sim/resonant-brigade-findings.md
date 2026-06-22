# Findings — RESONANT-BRIGADE: localize the doubler tax, then resonate the dominant transfers

**Branch** `resonant-brigade` (off `resonant-island`). **Verdict:** **`RESONANT-BRIGADE-MODELED`**
— the doubler bucket-brigade tax **localizes** to **2 switched phase transfers** (sum-check passes),
both **resonate** through the validated `island_resonant_core`, the guard **closes + trips** per step
and in aggregate, the two t½ **co-exist** at one rpm, the **arc floor** is named, and the
**recovered-η-vs-N** curve names the smallest worthwhile inductor set against that floor. **But the
headline η is CONDITIONAL:** resonating the brigade equalization — which *is* the Bennet pump
mechanism — can alter `z = 1.334`, and the frozen `doubler_core` was not re-derived this block, so
**the recovered-η curve is an upper bound pending a doubler re-sim.**

The localization, the worth-it floor, the per-step/aggregate guard, the clocking and the arc floor are
**unconditional**. The η number is **not**. This is the honest result: the *lever* is validated and
sized; whether you can pull it without losing the pump is the open question. **Not merged** (a
topology change — merges on TMD's sign-off of the sequence, the inductor set, **and** the z re-sim).

## The assumed transfer sequence (⚠ flag for TMD sign-off — design authority)

The 4-node Bennet doubler switches in **2 phases per cycle**: **phase B** (C1→min, C2→max) and
**phase A** (C1→max, C2→min), each ending in a **diode-conduction equalization** — that equalization
is the C-C tax. The **Phase-1 sum-check** (Σ Etax = 19.58 mJ/cycle, below) is the cross-validation
that this assumed sequence is the real one. **TMD confirms the sequence and the chosen inductor set
before the model is adopted.**

## §-checks (brief §7)

| # | check | result |
|---|---|---|
| 1 | frozen `doubler_core`/`shuttle_core`/`index.html` empty-diff; localization consumer-side; `island_resonant_core` reused unmodified | ✓ byte-identical vs `resonant-island` |
| 2 | Phase-1 sum-check `Σ Etax = 9.79` + assumed sequence stated | ✓ **19.577 mJ/cycle = 2 fires × 9.789 mJ/fire** (units reconciled, below); sequence confirmed |
| 3 | ranked per-transfer table + concentration | ✓ **phase A 57% / phase B 43%**, both C_eff ≈ 68.6 pF — **2 transfers, CONCENTRATED**, not smeared |
| 4 | per resonated step: worth-it (Q floor) + guard closes + trips | ✓ both worth-it at **Q≈1909**; guard resid ~1e-12, **+5% R trips**; aggregate ledger residual **0** |
| 5 | multi-resonant clocking: all t½ co-exist at the design rpm | ✓ both **t½ ≈ 0.82 µs** (shared C_eff) ≪ 278 µs window → co-exist trivially |
| 6 | recovered-η-vs-N + arc floor + realistic η + recommended set | ✓ **0.386 → 0.736 → 0.999** (upper bound); arc ceiling **~0.997**; recommend **N=2** |
| 7 | synthesizer feasible with brigade L_k; clocking sub-check; canary | ✓ I10 brigade clocking sub-check; **canary z 1.3336, η 0.3863, 983 mm, feasible** |

## Phase 1 — the localization (units reconciled) `[ME]`

`sim/brigade_tax_localize.py` reads the **frozen** `doubler_core` trajectory and splits each phase
transition into the mechanical stroke `W_mech` and the diode equalization tax
`Etax = U_int(diodes off, const-Q) − U_post`, anchored at the **15 kV operating point** (the same
anchor `energy_balance.csv` uses).

**Units (stated once).** `energy_balance.csv` reports `W_mech = 15.941 mJ/fire` and tax-fraction
`0.614` → tax = **9.789 mJ/fire**. A cycle has **two fires** (phase A and phase B), so the per-cycle
doubler tax is **19.58 mJ = 2 × 9.789**. The campaign's published "9.79 mJ" is the **per-fire**
figure; the two phase transfers are the two fires. (This block reconciles a loose "/cycle" label in
the island findings — the physics is unchanged.)

**Sum-check (the localization's own guard).** Σ Etax = **19.577 mJ/cycle** vs target
**19.578 = 2 × 9.789** → **PASS**; the same cycle's `W_mech = 31.88 mJ/cycle` → η_core = **0.386**
(matches `energy_balance`), `z = 1.334`. The sum-check passing *also confirms the assumed 2-phase
sequence.*

| transfer | tax (mJ/cycle) | share | dominant ΔV | C_eff |
|---|---|---|---|---|
| **phase A equalization** | **11.189** | **57.2 %** | 18.06 kV | 68.6 pF |
| **phase B equalization** | **8.388** | **42.8 %** | 15.64 kV | 68.6 pF |

**Concentration:** the tax is in **2 switched phase transfers** (both needed for ≥80 %, since the
largest is 57 % < 80 %) — **CONCENTRATED, not smeared** across the twelve C_AR/C_BR. *Note:* the
lumped 4-node `doubler_core` resolves the brigade only to **phase level** (the Ca/Cb coupling branches
are an approximate finer split; the shared Cpar/node terms don't partition cleanly). So "2 dominant
transfers" is the finest *clean* localization the frozen solver supports — which is enough: it rules
out `TAX-SMEARED` and says **resonance is the right lever**.

## Phase 2 — resonating the dominant transfers `[SOLVER]`

`sim/resonant_brigade.py` walks the ranked list and models each dominant transfer as a half-cycle LC
ring with the **unmodified** `island_resonant_core` (the [SOLVER] series-RLC integral + the
independent i²R-vs-bookkeeping guard). The transfer's extracted **C_eff ≈ 68.6 pF** discharges its
**ΔV** into the (≫) rail; the ring's C_eff reproduces the extracted value.

| transfer | tax | Q (R=2Ω) | t½ | i_pk | ring loss | recovered | worth-it | guard |
|---|---|---|---|---|---|---|---|---|
| phase A | 11.19 | 1909 | 0.82 µs | 4.7 A | 0.018 mJ | 11.171 mJ | **YES** | 1e-12 / **trips** |
| phase B | 8.39 | 1909 | 0.82 µs | 4.1 A | 0.014 mJ | 8.374 mJ | **YES** | 8e-13 / **trips** |

- **Worth-it (Q floor).** Both ring losses (~0.02 mJ) are far below the C-C tax they remove — both
  pass with huge margin at Q≈1909. (With only 2 clean transfers there is no small transfer to reject;
  the worth-it floor would bite if the model resolved the individual C_AR/C_BR — it cannot, frozen.)
- **Multi-resonant clocking (timing wall).** Both t½ ≈ **0.82 µs** (they share C_eff, so they are
  near-identical) and ≪ the **5°@3000 rpm = 278 µs** window → they **co-exist at one rpm trivially**.
  Not `TIMING-COUPLED-INFEASIBLE`.
- **Arc floor.** `E_arc = V_arc·Q_transferred` with the `shuttle_core` corners (20/35/50 V) →
  **0.046 / 0.081 / 0.116 mJ/cycle** → the fully-resonated η ceiling is **~0.997 / 0.997 / 0.995**:
  **η does not reach 1.** The arc is tiny here; the real ceiling on the *headline* is the z caveat,
  not the arc.

**Aggregate ledger (independent of the per-step guard):** Σ recovered **19.545** = Σ(direct tax
**19.577** − ring loss **0.032**), residual **0** — and every step's guard **trips under +5 % R**
(Rule 6.1: closes *and* can fail).

## The recovered-η-vs-N curve (the answer to "how many inductors") `[SOLVER]`

| N | transfers resonated | recovered (mJ/cycle) | recovered-η | Δη |
|---|---|---|---|---|
| 0 | (direct baseline) | 0.000 | **0.386** | — |
| 1 | phase A | 11.171 | **0.736** | +0.350 |
| 2 | + phase B | 19.545 | **0.999** | +0.263 |

Robust across the ring-Q band (Lx 1 mH): η = **0.999 (Q 1909) / 0.990 (Q 191) / 0.951 (Q 38)** —
even a lossy ring recovers most of the tax. **Recommended set: both inductors (N=2)** — there is no
diminishing-returns knee within the 2 clean transfers (both are large and both worth it); phase A
alone (N=1) already captures 57 % of the tax if only one inductor is affordable.

## ⚠ The load-bearing caveat — why this η is an UPPER BOUND `[OC]`

The downstream **island** transfer (RESONANT-ISLAND) was a pure **sink dump**: Cx rings into the bank,
the overshoot never feeds back, so resonating it is unconditionally free. **The brigade equalization
is different.** The diode conduction that loses the tax **is the Bennet pump** — it is *how* the
doubler ratchets charge — and the **post-equalization node voltages are the initial condition for the
next stroke**. A loss-free LC ring does **not** leave the caps at the equalized voltage; it leaves
them in an **over-transferred** state. That different initial condition can **change z = 1.334** (and
hence the pump gain and the very W_mech the η is measured against).

Confirming z survives requires **re-deriving the doubler with LC equalization in place** — and
`doubler_core` is **frozen** (read-only) this block. Therefore:

> **The recovered-η curve (0.386 → 0.999) is an upper bound, conditional on a doubler re-sim
> confirming the resonant equalization preserves z.** The localization, worth-it, guard, clocking and
> arc floor stand on their own; the η number waits on that re-sim.

This is the dominant open item — **not** the ring loss (0.03 mJ) or the arc floor (0.05 mJ).

## Integration + the re-opened topology `[OC]`

- `design_synth` **I10** gains a **brigade multi-resonant clocking** sub-check: both brigade t½
  (from `brigadeL_mH`, C_eff a topology constant 68.6 pF) co-exist with the island t½ ≤ the SG window
  at the design rpm. `brigadeL_mH = 1.0` enters `ESTABLISHED`.
- **Canary re-confirmed:** the anchor still reproduces **z 1.3336, η 0.3863, 983 mm, feasible**;
  binding still **I10**. (The brigade inductors are transfer-efficiency levers in the synth's
  feasibility space; the synth does **not** itself re-derive z — consistent with the caveat above.)
- **Topology re-opened:** **2 brigade inductors** added to the decision space, for TMD to draw into
  the KiCad netlist of record (the container's consistency check follows). Flag the delta.

## Deliverables

`sim/brigade_tax_localize.py` (Phase-1 consumer analysis + the sum-check) ·
`brigade_tax_localization.csv` (ranked per-transfer table) · `sim/resonant_brigade.py` (Phase-2,
reuses `island_resonant_core`) · `resonant_brigade.csv` (recovered-η vs N, per-step worth-it, the t½
set, the arc floor) · `resonant_brigade.png` · this findings doc · `sim/design_synth.py` (I10 brigade
clocking sub-check + `brigadeL_mH`). Frozen `shuttle_core`/`doubler_core`/`index.html` byte-identical.
**Not merged.**

### Roadmap

On TMD's sign-off of (a) the transfer sequence and (b) the inductor set, **and** a doubler re-sim
confirming z survives resonant equalization: the brigade inductors are adopted and the η headline
moves from **0.386** toward the **~0.92–0.997** band (arc-floor-limited). Until the re-sim, the honest
statement is: **the 69 % lever is localized and validated; pulling it is conditional on the pump
surviving.**
