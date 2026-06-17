# Simulation campaign — provenance map

> **Consumer-only.** This document asserts nothing new — it lines the campaign up against the **actual
> git state** (branch names + commit hashes fetched, not reconstructed from prose). Where git reality and
> the findings prose disagree, **git wins** and the discrepancy is flagged. No simulation was run and no
> frozen module (`reference/doubler_core.py`, `shuttle_core.py`, `index.html`) was touched to produce it.
> Mainstream circuit theory / linear algebra / charge conservation only — no DCCREG content.

Generated against the `xsim` branch (head `5e259c3`, rev 0.8). Hashes are short; resolve with `git show`.

---

## 1. Lineage (real git topology)

The eigen-witness phases sit on the **linear mainline** as a strict ancestor chain; the geometry /
resonator / reach / freeze track **branches off `effcee1`** (the xsim rev-0.5 commit). Verified by
`git merge-base --is-ancestor`:

```
main (9136624)                 ← effcee1 is NOT on main (confirmed)
   │  …index.html Block work (C-I, M, D, R, T)…
   ▼
shuttle-fullsim (b91b5fd)      Phase 2   ─┐
   ▼  ⊂                                    │ strict ancestor chain
spark-derate   (ca18018)       Phase 3    │  (each ⊂ the next, all ⊂ effcee1)
   ▼  ⊂                                    │
bootstrap-gate (486bf71)       Phase 5    │
   ▼  ⊂                                    │
effcee1  ── xsim rev 0.5 ──────────────────┘   ◀── campaign hinge / common ancestor
   │                                            │
   │ xsim branch RE-ISOLATES here, then         ├──► resonator-sim-r2 (bd46fb0)  TANK-HOLDS-15kV
   │ rev 0.5+/0.6/0.7/0.8 on top:               ├──► s2-pump-tank-coupling (9d06ff8)  PUMP-DELIVERS
   ▼                                            ├──► s2recheck-s3-spark (c1754da)  REACH/STRIKE @789
xsim (5e259c3)  Phase 6 + V0 CLOSED-LOADED      └──► freeze-v0.10 (42797ff)  design freeze + fire-gap note
```

**Lineage-note check (findings vs git):** the `xsim-findings.md` note says effcee1 "is *not* on `main`
but *is* an ancestor of the later geometry/freeze branches." **Git confirms both** — `effcee1` is not an
ancestor of `origin/main`, and it *is* an ancestor of `freeze-v0.10`, `s2recheck-s3-spark`,
`resonator-sim-r2` (and `geom-shuttle-gate`, `design-intent-lock`, the feasibility branch). No discrepancy.

---

## 2. Provenance table (claim → artifact → commit)

| Phase | Branch | Head | Verdict(s) | Headline | Deliverables |
|---|---|---|---|---|---|
| **2 — shuttle full-sim** | `shuttle-fullsim` | `b91b5fd` | `SHUTTLE-PUMP-CONFIRMED` | z ≈ 1.19–1.20; anchor 1.2033; ledgers ~1e-14 | `shuttle-fullsim-findings.md`, `shuttle_event_angles.csv`, `shuttle_timing_from_solver.png` |
| **3 — spark derate** | `spark-derate` | `ca18018` | `LOADRETURN-CONDITIONAL` · `BACKSTOP-CLEAN` · `SPARK-INDETERMINATE` · `GLOW-INDETERMINATE` | spark tier sized; backstop ≤1.05× bucket | `spark-derate-findings.md`, `spark_backstop_table.csv`, `spark_audit_table.csv`, `spark_derate_*.png` |
| **5 — bootstrap gate** | `bootstrap-gate` | `486bf71` | `BOOT-SEEDED` | V_floor 187 < V_sustain 437; two-threshold startup | `bootstrap-findings.md`, `bootstrap_seeder_spec.csv`, `bootstrap_*.png` |
| **6 — xsim eigen-witness** | `xsim` | `5e259c3` | `X0-RECOVERED` · `X1-B XSIM-MATCH` · `X2-B XSIM-MATCH` (3 corners) · `X3-B STRUCTURE-CONFIRMED` + `X3-PASS` (opt/mid) / `X3-PASS-CONDITIONAL` (pess) · `T3 DT-PLATEAU` · **`V0-SECONDARY-CLOSED-LOADED`** | z 1.18938 / δ 0.2175 to machine prec.; arc 3 corners; bootstrap composes to ideal; ngspice divergence T3-structural; **de Queiroz reproduced ideal (1.17138) + loaded (1.1538)** | `xsim-findings.md`, `xsim_comparison.csv`, `xsim_*.png` (`x0`,`x1`,`x2`,`x3`,`queiroz_V0`,`dt_sweep`) |
| **R — resonator tank** | `resonator-sim-r2` | `bd46fb0` | `TANK-HOLDS-15kV` | revised geometry closes the reach gap; clamp holds ≤15 kV | `sim/resonator-r2-findings.md`, `sim/resonator_r2_*.csv/png` |
| **S2 — pump↔tank coupling** | `s2-pump-tank-coupling` | `9d06ff8` | `PUMP-DELIVERS-EASED-ONLY` (M2) / `PUMP-UNDERDELIVERS` (M1) | eased reach real; ~6 % margin the true ceiling | `sim/s2-coupling-findings.md`, `sim/s2_E_deliver.csv`, `sim/s2_coupled_traces.png` |
| **S3 — reach re-confirm @789 + spark tier** | `s2recheck-s3-spark` | `c1754da` | `REACH-CONFIRMED-789` · `STRIKE-CONFIRMED` · `QUENCH-OK` · `BACKSTOP-CLEAN` · `INTEGRATED-REACH-OK` | 789 pF tank holds; strike 15.5 kV cold (flagged tight) | `sim/s2recheck-s3-findings.md`, `sim/s3_spark.csv`, `sim/s3_spark_traces.png` |
| **Freeze v0.10** | `freeze-v0.10` | `42797ff` | (snapshot) | C_R 960→789 pF (12 mm disc); 6 gaps placed; fire-gap mount note | `docs/varcap-design-freeze-v0.10.md`, `docs/design-note-SG3b-SG4b-firegap-mount.md` |

*Cross-branch note:* Phases 2/3/5/6 artifacts are all present on `xsim` (it descends from that ancestor
chain). The R/S2/S3 artifacts live on their **sibling** branches off `effcee1` — `xsim` does **not** carry
them; resolve via the branch named in each row.

---

## 3. Anchor chain & validation logic (what validates what)

**Anchor chain** (each tier grounded in the one before, ending back at the ideal):
```
X0  galvanic anchor  z = 1.2033 (exact, reference/doubler_core.py — the tiebreaker)
 └► X1  ideal shuttle z = 1.18938 / δ = 0.2175           (machine precision)
     └► X2  arc tier   z_arc opt/mid/pess 1.1888/1.1844/1.1667   (absolute-volt limit cycle)
         └► X3  bootstrap startup COMPOSES back onto the X1 ideal asymptote 1.18938
                (seed-independent; strike/V→0 recovers scale-invariance)
```

**Multi-witness structure** (three independent constructions agree where it counts):
- **native** — `shuttle_core` marches forward in θ, reads z as the iterated asymptotic ratio.
- **(B) eigen-witness** — `xsim_queiroz_matrix.py` composes segment-boundary charge-conservation matrices
  into one per-cycle map and takes z as its **dominant eigenvalue**; never time-steps. Ships its **own**
  cluster solver — **grep-gate: 0 calls** into `shuttle_core.transition` / `_galv_phase`.
- **(A) ngspice** — `xsim_from_solver.py` runs the netlists. Agrees on X0 but **diverges on X1**
  (z = 1.054); `T3 DT-PLATEAU` proves this is a **continuous-time integrator artifact** (zero-time cluster
  re-solve vs finite-rate integration), not a circuit defect. **X2/X3 are `BLOCKED` on ngspice** by the
  campaign rule (X1 must pass first) — they are validated only by (B) vs native.

native · (B) agree on **X1 and X2 to machine precision**; (A)'s divergence is the named, T3-confirmed
artifact.

**External anchor — de Queiroz** (*Analysis of Electronic Electrostatic Generators*): his **method** *is*
the (B) eigenvalue-of-M construction; his Fig-1 **topology** *is* our galvanic doubler; the witness
reproduces his **ideal** Newton result (√z = 1.17138) **and** his Fig-6 **loaded** prediction (z = 1.1538,
with the 82 pF measurement divider) → `V0-SECONDARY-CLOSED-LOADED`. The residual chased through rev 0.7
was measurement loading, not an equation slip.

---

## 4. Scoreboard (current state of every gate)

`X0 PASS · X1 PASS · X2 PASS (3 corners) · X3 PASS (opt/mid) + CONDITIONAL (pess, ign ≥ 1.5×strike) ·`
`T3 structural (ngspice continuous-time artifact) · V0 CLOSED-LOADED (ideal 1.17138 + loaded 1.1538) ·`
`SHUTTLE-PUMP-CONFIRMED · spark LOADRETURN-CONDITIONAL/BACKSTOP-CLEAN/SPARK+GLOW-INDETERMINATE ·`
`BOOT-SEEDED · TANK-HOLDS-15kV · PUMP-DELIVERS-EASED-ONLY · REACH-CONFIRMED-789 · STRIKE-CONFIRMED ·`
`QUENCH-OK · INTEGRATED-REACH-OK`

**Caveats preserved (not averaged away):**
- **X3 pess** ignites only at seed **≥ 1.5×strike** (the `X3-INDETERMINATE`-at-low-seed corner — needs
  operating-rpm-before-injection); below that it never crosses the Paschen floor.
- **X3 magnitudes** are softer than native (V_floor 120 vs 187, V_sustain 160 vs 437) — the **ordering /
  direction** is the load-bearing test; the ≤15 % magnitude band is not met.
- **STRIKE** clears 15 kV by only ~0.5 kV cold → fire-gap spacing reclassified to bench-tuned/governed
  (freeze §5; `docs/design-note-SG3b-SG4b-firegap-mount.md`).
- **S2** reach is real only on the **M2/eased** map (~6 % margin); M1 under-delivers.

---

## 5. Open items & next sims

| Item | Owning track | Type |
|---|---|---|
| X3 **pess** conditional (needs ≥1.5×strike seed / pre-spin) | xsim Phase 6 | simulator |
| Deferred **fire-gap + tank coupled sim** (current-zero quench / S3 local-loop ring) | S3 / reach track | simulator |
| **SG1↔SG3a overlap-benign** check (unblocks return-gap placement) | DXF / freeze | DXF |
| **BS3/BS4** backstop DXF markers + the r0_10 DXF | freeze v0.10 | DXF |
| ngspice **X2/X3** (currently BLOCKED) — needs the X1-A continuous-time artifact resolved first (T3 says structural) | xsim (A) witness | simulator |

---

## 6. Artifact index (by branch)

- **`xsim` (`5e259c3`)** — `xsim_queiroz_matrix.py` (B witness + Queiroz Fig-1), `xsim_from_solver.py`
  (A ngspice consumer + §5 table + T3 dt-sweep), `xsim_netgen.py`, `xsim-findings.md`, `xsim_comparison.csv`,
  `xsim_x0/x1/x2/x3_*.png`, `xsim_queiroz_V0.png`, `xsim_dt_sweep.png`; plus the ancestor-phase findings
  (`shuttle-fullsim-findings.md`, `spark-derate-findings.md`, `bootstrap-findings.md`) and their CSV/PNG.
- **`resonator-sim-r2` (`bd46fb0`)** — `sim/resonator_sim.py`, `sim/resonator-r2-findings.md`, traces/sink.
- **`s2-pump-tank-coupling` (`9d06ff8`)** — `sim/s2_coupling.py`, `sim/s2-coupling-findings.md`, `presets/G2-geometry-r2.json`.
- **`s2recheck-s3-spark` (`c1754da`)** — `sim/s2recheck_s3_spark.py`, `sim/s2recheck-s3-findings.md`, `sim/s3_spark.csv/png`, `presets/G3-geometry-v010.json`.
- **`freeze-v0.10` (`42797ff`)** — `docs/varcap-design-freeze-v0.10.md`, `docs/design-note-SG3b-SG4b-firegap-mount.md`.

*Provenance-complete:* every scoreboard gate above resolves to a row in §2 with a branch, a commit, and a
deliverable. No claim without a witness.
