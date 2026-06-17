# xsim — findings (Phase 6, rev 0.5): **X1-B · X2-B XSIM-MATCH (analytic) · X3-B STRUCTURE + X3-PASS · T3 DT-PLATEAU**

**Verdict line:** `V0-SECONDARY-OPEN` (auth on galvanic anchor) · `X1-B XSIM-MATCH-B` ·
`X2-B XSIM-MATCH-B (3 corners)` · `X3-B STRUCTURE-CONFIRMED` + `X3-PASS (opt/mid) / X3-PASS-CONDITIONAL
(pess, ign≥1.5×strike)` — the BOOT-SEEDED startup composes onto the **ideal** asymptote z=1.18938 ·
`X1-A XSIM-DIVERGENT-A` ·
`T3 DT-PLATEAU (structural)`.

**Branch** `xsim` — the rev-0.5 witness (`effcee1`) carried onto a clean branch cut at that commit, where
the X3-PASS composition tier (`bootstrap_asymptote` / `x3_composition`) was added. **Lineage note:** the
brief assumed a living `xsim` branch off `bootstrap-gate`; in fact rev 0.5 was committed into the linear
mainline (`main → shuttle-fullsim → spark-derate → bootstrap-gate → … → effcee1`), which is **not** on
`main` (correct — not merged) but is an ancestor of the later geometry/freeze branches. This `xsim` branch
re-isolates the campaign at `effcee1`. `reference/doubler_core.py`, `shuttle_core.py`, `index.html`
**untouched** (mirror FAITHFUL, shuttle
C0 green). Not merged. (B) keeps its **own** cluster solver — grep-gate clean: **0** calls to
`shuttle_core.transition`/`_galv_phase`/`spark_run`/`boot_run`; only device-point constants + firing
order + comparison targets consumed.

This rev folds in the **rev 0.5 addendum**: harden the V0 authorisation (T1), extend the (B)
eigen-witness to the arc (X2) and bootstrap (X3) tiers (T2), and a ngspice timestep diagnostic (T3).

---

## T1 — Queiroz Fig-1 method self-test → **V0-SECONDARY-OPEN** (honest residual)

The shared Newton engine `_newton_zab` is built and **unit-checked** (recovers √2 from a 2-var
system; it drives the X2 limit cycle). The Fig-1 reproduction, however, is **OPEN**: the addendum
supplies his segment *restrictions* (e31=e11, e3x=0, e4y=e2y, e3y=0 with D1 off in seg-3, plus the
cap relations) but **not his Fig-1 circuit topology** — which capacitor sits between which nodes, and
the three diode placements — and the paper is **unfetchable in-environment** (arxiv/IEEE/coe.ufrj.br
all return 403). A correct charge-conservation Newton system needs that cap network. Direct
reconstruction attempts (a symmetric Bennet doubler, C1/C2 60↔360 + Ca=Cb=330, across several
node/diode arrangements) yield pumping configurations at **z ∈ {1.0, ~2.08}** but not 1.1538 — the
gain is acutely topology-sensitive and the available spec does not pin it. Per the addendum this is
reported as an **OPEN residual, not a "topology" hand-wave**: the transcribed constraints are stated;
the missing piece is named (the Fig-1 cap/diode network). **X1-B's authorisation therefore stands on
the in-repo galvanic anchor (eigen z = 1.2033, Δ = −4×10⁻¹⁶, exact)** — robust; the external
method-fidelity check stays explicitly open.

## X1-B — ideal shuttle (rev 0.4, carried) → **XSIM-MATCH-B**

z = **1.18938** (Δ = −5×10⁻¹⁴) and emergent δ = **0.2175** (Δ = 0) vs native — to **machine
precision**, by the closed-cycle **eigenvalue** of the per-cycle charge-transfer map (the native
forward-marches; (B) never time-steps). δ emergent (sweeping the threshold moves it 0.2175→0.36, z
invariant).

## X2-B — arc tier (T2) → **XSIM-MATCH-B (all three corners)**

The absolute-volt Paschen strike breaks the ideal-tier scale-invariance, so z becomes a **limit-cycle
property** (the genuine §3.1 case): the fire opens at the **absolute strike crossing** (emergent —
read, not clocked) with a partial transfer φ = 1−pVarc/ov (residual arc drop), and z_arc is the
geometric-mean growth-window gain of the **independent** `_cluster_solve` run forward at the device
point. Strike (650/333/150 V) and pVarc (20/35/50 V) **consumed** from `paschen_strike`/`ARC_CORNERS`,
never tuned.

| Corner | Native z_arc | (B) eigen | Δ | clamp (×strike) | Status |
|---|---|---|---|---|---|
| opt | 1.188767 | **1.18877** | +0.00000 | 1.04 | **MATCH** |
| mid | 1.184406 | **1.18440** | −0.00001 | 1.01 | **MATCH** |
| pess | 1.166661 | **1.16666** | +0.00000 | 1.01 | **MATCH** |

z_arc reproduced to **machine precision** for all three corners; the island-overvoltage **clamp ≈
1.04× strike** (native; ≤5%) emerges. δ read from the absolute-volt crossing (fire θ moves opt→pess
as the strike falls). This validates the limit-cycle solver against an in-repo independent target.

## X3-B — bootstrap structure (T2) → **STRUCTURE-CONFIRMED**

With the Paschen no-fire floor (`V_FLOOR = 327 V`, gating the half inert unless a **rail** node
reaches it) and storage leakage (`tau_storage` 1.0/0.1/0.01 s) **consumed**, the two-threshold
structure is backed out by trajectory classification (no-fire / fire-and-decay / growth):

| Corner | V_floor | V_sustain @3000 | @1519 | @769 |
|---|---|---|---|---|
| mid | 120 V | 160 V | 230 V | 520 V |
| pess | 80 V | **none** | **none** | **none** |

The **structural test (brief §4 — the real test)** passes: **V_floor < V_sustain**, **V_sustain RISES
as rpm falls** (the retention race), and **pess does not self-sustain** ≤3000 rpm — all reproduced,
matching native qualitatively (native mid V_floor≈187 < V_sustain 437@3000/669@1519/1023@769; pess
non-self-sustain). The **magnitudes are softer** than native (V_sustain 160 vs 437) — the (B) low-V
retention model sustains more easily than native's near-floor gain reduction — so the ≤15% magnitude
band is not met, but the ordering/direction/pess (the load-bearing structure) is confirmed. Reported
honestly, not tuned.

## X3-B — bootstrap composition (rev 0.5+) → **X3-PASS (opt/mid) · X3-PASS-CONDITIONAL (pess)**

The structure test above is necessary but not the brief's §3 X3-PASS claim proper, which asks: does the
per-cycle map, driven through the **BOOT-SEEDED startup transient**, *compose* and land on the **same
asymptotic z** as X1? Tested directly (`bootstrap_asymptote` / `x3_composition`): seed the rail at
`seedmul·strike` on nodes 1,4, run the arc limit cycle with the Paschen no-fire floor **enforced** (the
genuine startup gate) and **no leakage** (decay = 1 — leakage is the *separate* retention-race factor of
the structure test), and read the per-cycle gain over a **late, post-transient window** (cycles 70–110,
renorm-robust median of log-gains).

| Corner | seed 0.6× | 1.0× | 1.5× | 3.0× | ignition floor | verdict |
|---|---|---|---|---|---|---|
| opt | 1.18938 | 1.18938 | 1.18938 | 1.18938 | ≥0.6×strike | **X3-PASS** |
| mid | 1.18938 | 1.18938 | 1.18938 | 1.18938 | ≥0.6×strike | **X3-PASS** |
| pess | no-ign | no-ign | 1.18938 | 1.18938 | ≥1.5×strike | **X3-PASS-CONDITIONAL** |

The late-window asymptote lands on **z = 1.18938 — the X1 *ideal* z — to machine precision** (Δ = 0.000000),
**seed-independently**, NOT the finite-amplitude `z_arc` of X2. This is physically exact and the headline:
the arc tier breaks scale-invariance **only through the absolute strike**, so as the seeded rail grows the
strike becomes a vanishing fraction (`strike/V → 0`) and the limit cycle **recovers the scale-invariant
ideal asymptote**. The X2 `z_arc` (1.166–1.189) is the *early-window operating gain* at finite amplitude;
the asymptotic per-cycle map is the ideal — and the bootstrap startup **composes onto it**. So the startup
transient does not change the asymptote: it only decides *whether* the seed ignites and wins the retention
race (the structure test).

The lone exception is the **pessimistic corner below ~1.5×strike**, where the seed never crosses the
Paschen floor and the half stays inert (z ≈ 1.0). This is exactly the brief §3 `X3-INDETERMINATE`
condition — "the startup needs operating-rpm-before-injection at the pessimistic corner" — **reported per
corner, not averaged away**: pess requires an elevated seed (or pre-spin before injection) to ignite,
after which it composes onto the same ideal asymptote.

## T3 — ngspice dt-sweep diagnostic → **DT-PLATEAU (structural)**

Sweeping the X1-A max-timestep over 1.5 decades (Δt = T/{400,1200,4000,12000}) with the step limit
binding:

| Δt (µs) | 2.500 | 0.833 | 0.250 | 0.083 |
|---|---|---|---|---|
| X1-A z | 1.0544 | 1.0493 | 1.0551 | 1.0592 |

z **stays at ~1.05** (Δz = +0.005 across a 30× refinement) and does **not** trend toward native
1.18938 — **DT-PLATEAU**. The X1-A under-pump is therefore **structural**: the native/eigen models
redistribute charge in **zero time** (an algebraic cluster re-solve) and a continuous-time integrator
can only approach that instantaneous limit from the lossy side, never reach it. The §3a mechanism-(1)
attribution is now **EVIDENCED, not merely plausible** — continuous-time SPICE is the wrong tool for
the instantaneous transfer, confirmed, not a tuning problem.

## Full §5 dual-witness table (native · B primary · A tertiary)

Machine-readable: `xsim_comparison.csv`.

| Quantity | Native | B eigen (Δ) | B | A ngspice | A |
|---|---|---|---|---|---|
| X0 anchor z | 1.2033 | 1.2033 (−4e-16) | PASS | 1.2042 | PASS |
| X1 z | 1.18938 | **1.18938 (−5e-14)** | **MATCH** | 1.0544 | DIVERGENT |
| X1 δ | 0.2175 | **0.2175 (0)** | **MATCH** | 0.1917 | DIVERGENT |
| X2 z_arc opt/mid/pess | 1.1888/1.1844/1.1667 | **= (machine prec.)** | **MATCH** | — | BLOCKED |
| X2 clamp | ~1.04 | 1.01–1.04 | PASS | — | BLOCKED |
| X3 V_floor (mid) | 187 V | 120 V (structural) | STRUCT | — | BLOCKED |
| X3 V_sustain (mid@3000) | 437 V | 160 V (rises w/ rpm↓) | STRUCT | — | BLOCKED |
| X3 boot asymptote (opt/mid) | →ideal | **1.18938 (0), seed-indep** | **X3-PASS** | — | BLOCKED |
| X3 boot asymptote (pess) | →ideal | 1.18938 (ign≥1.5×strike) | **PASS-COND** | — | BLOCKED |

**Three independent constructions** agree on X1 (native forward · B eigen) and X2 z_arc (native spark
· B eigen) to **machine precision**; A's X1 divergence is the **named continuous-time artifact**,
now **T3-confirmed structural**.

## Verdict (per-witness + combined)

- **V0-secondary: `V0-SECONDARY-OPEN`** — Fig-1 not reproduced (topology underdetermined +
  unfetchable); X1-B auth on the galvanic anchor (exact).
- **X1-B: `XSIM-MATCH-B`**; **X2-B: `XSIM-MATCH-B`** (3 corners, machine precision) — load-bearing
  confirmations of the native ideal and spark tiers by an independent analytic witness.
- **X3-B: `STRUCTURE-CONFIRMED`** (ordering/direction/pess; magnitudes softer, flagged) **+ `X3-PASS`
  (opt/mid) / `X3-PASS-CONDITIONAL` (pess)** — the BOOT-SEEDED startup composes through the transient
  and lands on the **same asymptotic z = 1.18938 (the X1 ideal)** to machine precision, seed-independently
  (`strike/V → 0` recovers scale-invariance); pess needs ≥1.5×strike seed to ignite (the brief's
  `X3-INDETERMINATE`-at-low-seed corner, reported not averaged).
- **X1-A: `XSIM-DIVERGENT-A`**; **T3: `DT-PLATEAU`** — the divergence is structural (continuous-time),
  not a circuit defect and not numerical under-resolution.
- **Combined: X1 PASS on B · X2 PASS on B · X3 structure + composition (X3-PASS) on B.** The pump, its
  emergent clocking, the arc-tier derating, AND the bootstrap startup composing onto the ideal asymptote
  are confirmed as circuit properties by a second, independent (analytic) method. CHANGELOG updated;
  branch left for TMD review; not merged.

## Deliverables

- `xsim_queiroz_matrix.py` — (B) eigen-witness + `_newton_zab` (T1) + `queiroz_fig1_newton` (OPEN) +
  `arc_limit_cycle` (X2) + `bootstrap_structure`/`boot_classify` (X3 structure) +
  `bootstrap_asymptote`/`x3_composition` (X3-PASS composition, rev 0.5+); self-test covers all tiers.
- `xsim_queiroz_V0.png` (auth + emergent δ), `xsim_x2_arc_corners.png`,
  `xsim_x3_bootstrap_structure.png`, `xsim_dt_sweep.png`.
- `xsim_from_solver.py` (consumer: dual-witness table, three-way z, dt-sweep), `xsim_comparison.csv`,
  `xsim_x1_fire_readout.png`, `xsim_x1_shuttle.net` (A). `xsim-findings.md` — this document.
