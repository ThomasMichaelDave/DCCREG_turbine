# Simulation campaign — provenance map

> **Consumer-only.** This document asserts nothing new — it lines the campaign up against the **actual
> git state** (branch names + commit hashes fetched, not reconstructed from prose). Where git reality and
> the findings prose disagree, **git wins** and the discrepancy is flagged. No simulation was run and no
> frozen module (`reference/doubler_core.py`, `shuttle_core.py`, `index.html`) was touched to produce it.
> Mainstream circuit theory / linear algebra / charge conservation only — no DCCREG content.

Generated against the `xsim` branch (rev 0.8); **all evidence below is now consolidated onto the
`sim-evidence-consolidated` branch** (merge of `xsim` + `freeze-v0.10` + `s2recheck-s3-spark` +
`resonator-accum` + `xcap-duty-sign`, preserving merge history). The originating branch + commit per row
is retained as **historical provenance** — the hashes still resolve in the merged history. Hashes are
short; resolve with `git show`.

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
| **4 — resonator accumulator** | `resonator-accum` | `a505339` | `ACCUM-DC-PREFERRED` | DC store ½C_R·V²≈0.38 J usable now; AC/coherent need a kHz-tank redesign (M≈0.06 today) | `resonator-accum-findings.md`, `resonator_accum_routes.csv/png`, `resonator_accum_Mmap.csv/png`, `docs/resonator-battery-hardware.md` |
| **Screen — d3/d4 duty-sign** | `xcap-duty-sign` | `a8d38eb` | `XCAP-RATCHET-BLOCKED` | same-sign `+` ratchet on D3/D4 ⇒ a 2-terminal series flying cap can't carry it (single-gap Cx closed) | `xcap-duty-sign-findings.md`, `d3_duty_sign_from_solver.py` (+CSV/PNG) |

*Consolidation note:* **all rows above are now carried on the single `sim-evidence-consolidated` branch**
(merge history preserved). The *Branch* + *Head* columns record where each result was **originally**
produced — historical provenance, and the hashes still resolve in the merged graph. The two `shuttle_core.py`
producer-side additions (the `set_device_caps` geometry hook from the sim spine, and `resonator-accum`'s
one-line `jitter_real` / `export_kick_train`) merged as a **non-overlapping union**, both additive and
inert-by-default; the galvanic anchor re-checks at **z = 1.2033** on the merged tree. `index.html` and
`reference/doubler_core.py` remain **byte-identical to `effcee1`**. (`resonator-sim` r1, `TANK-UNDERDRIVEN`,
is intentionally **excluded** — superseded by the r2 row above.)

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
`QUENCH-OK · INTEGRATED-REACH-OK · ACCUM-DC-PREFERRED · XCAP-RATCHET-BLOCKED`

**Caveats preserved (not averaged away):**
- **X3 pess** ignites only at seed **≥ 1.5×strike** (the `X3-INDETERMINATE`-at-low-seed corner — needs
  operating-rpm-before-injection); below that it never crosses the Paschen floor.
- **X3 magnitudes** are softer than native (V_floor 120 vs 187, V_sustain 160 vs 437) — the **ordering /
  direction** is the load-bearing test; the ≤15 % magnitude band is not met.
- **STRIKE** clears 15 kV by only ~0.5 kV cold → fire-gap spacing reclassified to bench-tuned/governed
  (freeze §5; `docs/design-note-SG3b-SG4b-firegap-mount.md`).
- **S2** reach is real only on the **M2/eased** map (~6 % margin); M1 under-delivers.
- **ACCUM** is `DC-PREFERRED` only — the AC/coherent accumulator routes need a kHz-class tank redesign
  (M≈0.06 at the present 326 kHz f0); not a green light for incoherent storage as-built.
- **XCAP** is a **blocking** screen, not a pass — the single-gap Cx proposal is closed on the same-sign
  duty (escapes: a second gap per island, or a cycle re-derivation).

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

## 6. Artifact index (all on `sim-evidence-consolidated`; grouped by originating branch)

- **witness — orig. `xsim`** — `xsim_queiroz_matrix.py` (B witness + Queiroz Fig-1), `xsim_from_solver.py`
  (A ngspice consumer + §5 table + T3 dt-sweep), `xsim_netgen.py`, `xsim-findings.md`, `xsim_comparison.csv`,
  `xsim_x0/x1/x2/x3_*.png`, `xsim_queiroz_V0.png`, `xsim_dt_sweep.png`; plus the ancestor-phase findings
  (`shuttle-fullsim-findings.md`, `spark-derate-findings.md`, `bootstrap-findings.md`) and their CSV/PNG.
- **resonator tank — orig. `resonator-sim-r2`** — `sim/resonator_sim.py`, `sim/resonator-r2-findings.md`, traces/sink.
- **pump↔tank — orig. `s2-pump-tank-coupling`** — `sim/s2_coupling.py`, `sim/s2-coupling-findings.md`, `presets/G2-geometry-r2.json`.
- **reach+spark — orig. `s2recheck-s3-spark`** — `sim/s2recheck_s3_spark.py`, `sim/s2recheck-s3-findings.md`, `sim/s3_spark.csv/png`, `presets/G3-geometry-v010.json`.
- **freeze docs — orig. `freeze-v0.10`** — `docs/varcap-design-freeze-v0.10.md` (128-line, fire-gap-extended), `docs/design-note-SG3b-SG4b-firegap-mount.md`.
- **accumulator — orig. `resonator-accum`** — `resonator_accum.py`, `resonator_accum_from_solver.py`, `resonator-accum-findings.md`, `resonator_accum_routes.csv/png`, `resonator_accum_Mmap.csv/png`, `resonator_accum_damping.png`, `docs/resonator-battery-hardware.md`.
- **duty-sign screen — orig. `xcap-duty-sign`** — `xcap-duty-sign-findings.md`, `d3_duty_sign_from_solver.py` (+CSV/PNG).
- **geometry chain (carried by the sim track)** — `geom_shuttle_run.py`, `geom-shuttle-findings.md`,
  `presets/G1-geometry-r06.json`, the `varcap-nodeanalysis-template-r0_6_TMD_layout.dxf`, and this document.

*Provenance-complete:* every scoreboard gate resolves to a row in §2 with an originating branch, a commit,
and a deliverable now present on the consolidated branch. No claim without a witness.
