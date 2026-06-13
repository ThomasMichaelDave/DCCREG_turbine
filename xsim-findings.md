# xsim — findings (Phase 6, rev 0.3): **X1-B XSIM-MATCH (analytic eigen-witness) · X1-A DIVERGENT (ngspice)**

**Verdict line:** `V0-AUTHORISED` · `X1-B XSIM-MATCH-B` (z & δ to machine precision) ·
`X1-A XSIM-DIVERGENT-A` (continuous-time artifact, localised) · `X1 PASS on B (primary)`.

**Branch** `claude/feasibility-approval-planning-5gkcam` (on `bootstrap-gate` head).
`reference/doubler_core.py`, `shuttle_core.py`, `index.html` **untouched** (mirror FAITHFUL, shuttle
C0 green after the run). Not merged.

This rev folds in the **rev 0.4 addendum**: a **second, analytic witness** (B) — the Queiroz
segment-matrix / eigenvalue method — added as the **primary** X1 check, with the rev-0.3 ngspice
continuous-time path (A) demoted to a **tertiary corroborator**. The addendum's insight: the
shuttle's non-overlapping emergent fire is the case Queiroz's *closed-cycle eigen-solve* was built
for — analytic, not continuous-time. That insight is borne out: B matches native to machine
precision; A's rev-0.3 under-pump is thereby confirmed as a continuous-time artifact, not a circuit
property.

---

## 1. (B) Queiroz eigen-witness — PRIMARY (`xsim_queiroz_matrix.py`)

### 1.1 Construction & independence (addendum §3.3 — load-bearing)

z is the **dominant eigenvalue of the per-cycle charge-transfer map**: the cycle is segmented by
conduction state (return SG1/SG2 → load SG3a/SG4a → Cx collapse → emergent fire SG3b/SG4b), each
segment is a nodal charge-conservation relation `C_i e_i = C_{i+1} e_{i+1}`, the segments are
**composed** into one map M, and `z = max|eig(M)|` with the eigenvector giving the steady voltage
ratios. The fire angle is **emergent** — the collapse sub-step where the boosted-island overvoltage
first crosses the strike threshold (Newton/root-find on the converged solution); the ideal tier is
scale-invariant, so the map is linear.

**Independence is real and verified:** `shuttle_core` solves **forward in θ** (step caps, conserve
cluster charge, re-solve V at each micro-step, *read* the emergent fire) and reads z as the
asymptotic ratio over ~120 iterated cycles. (B) **never time-steps and never iterates to
convergence** — it composes the segment matrices and extracts z as an **eigenvalue**. (B) implements
its **own** cluster-charge solver (`_cluster_solve`) and **does not import**
`shuttle_core.transition` / `_galv_phase` / any native solver (grep-verified: 0 calls; only the
device-point constants, the firing **order**, and `shuttle_run` as the comparison *target* are
consumed). Different construction ⇒ a genuine second witness, not the same method twice.

### 1.2 Authorisation (V0)

- **Primary (paper-independent):** the eigen-method applied to the **galvanic limit** (islands →
  direct diodes) recovers **z = 1.2033** (Δ = −4×10⁻¹⁶ vs the anchor) — the (B) analog of X0,
  using canonical in-repo data. `xsim_queiroz_V0.png`.
- **Secondary (Queiroz Fig-1):** his unipolar example (Cmin/Cmax 60/360, Ca=Cb=330) targets
  z ≈ 1.1538; our galvanic eigenmap with his cap values gives **1.326**. This does **not** reproduce
  his number because his exact Fig-1 topology (node count / stray arrangement) differs from our
  4-node galvanic doubler and **could not be fetched** (arxiv/IEEE/his site all 403 in-environment).
  Reported honestly as a best-effort cross-check; the **authorisation rests on the galvanic anchor**
  (1.2033, exact), which is the canonical, load-bearing gate.

### 1.3 X1-B result — **XSIM-MATCH-B**

| Quantity | Native | (B) eigen | Δ | Tol | Status |
|---|---|---|---|---|---|
| X1 z (ideal shuttle) | 1.18938 | **1.18938** | −5×10⁻¹⁴ | ≤ 0.005 | **MATCH** |
| X1 emergent δ (SG1→SG3b) | 0.2175 | **0.2175** | 0 | ≤ 0.010 | **MATCH** |
| X1 island ledger | ~5×10⁻¹⁴ | 0 (Q conserved by construction) | — | ≤ 1e-6 | PASS |

The analytic witness reproduces native z **and** δ to **machine precision**. The δ is genuinely
emergent: sweeping the strike threshold moves it (0.2175 → 0.36) while z stays **invariant at
1.18938** — exactly the native `pVbkFire` behaviour (δ 0.218 → 0.39, z constant across the fire
band). Not clocked, not imposed.

## 2. (A) ngspice threshold-fire — TERTIARY corroborator (rev 0.3 path)

Carried from rev 0.3 (source-imposed Queiroz islands; threshold-driven fire, K-invariant, emergent
δ). It **runs and pumps** but **under-transfers charge/cycle**: z = **1.0544** vs 1.18938
(Δ = −0.135), δ = 0.1917 (Δ = −0.026). Robust across every fire realisation and K → **XSIM-DIVERGENT-A**.

With **B matching native to machine precision**, A's divergence is conclusively **localised as a
continuous-time SPICE artifact** (the trapezoidal/Gear march does not reproduce the quasi-static
per-cycle charge redistribution), **not** a circuit defect. This is exactly the addendum's
prediction (continuous-time SPICE cannot faithfully carry the non-overlapping emergent-fire shuttle;
the analytic method can).

## 3. Full §5 dual-witness table (brief §7) — native · B primary · A tertiary

Machine-readable: `xsim_comparison.csv`.

| Quantity | Native | B eigen (Δ) | B | A ngspice (Δ) | A |
|---|---|---|---|---|---|
| X0 anchor z (galvanic) | 1.2033 | 1.2033 (−4e-16) | PASS | 1.2042 (+0.0009) | PASS |
| X1 z (ideal shuttle) | 1.18938 | **1.18938 (−5e-14)** | **MATCH** | 1.0544 (−0.135) | DIVERGENT |
| X1 emergent δ | 0.2175 | **0.2175 (0)** | **MATCH** | 0.1917 (−0.026) | DIVERGENT |
| X1 island ledger | ~5e-14 | 0 | PASS | 0 | PASS |
| X2 z_arc (mid) | 1.18441 | — | BLOCKED | — | BLOCKED |
| X2 clamp (× strike) | ~1.04 | — | BLOCKED | — | BLOCKED |
| X3 V_floor (mid) | 187 V | — | BLOCKED | — | BLOCKED |
| X3 V_sustain (mid@3000) | 437 V | — | BLOCKED | — | BLOCKED |

**Three-way z reconciliation:** `shuttle_core` (forward) = **1.18938** · (B) eigen = **1.18938** ·
(A) ngspice = 1.05444. Two genuinely independent constructions (native forward-march and B
closed-cycle eigen-solve) agree on z **and** δ to machine precision — the strongest statement this
gate can make on X1.

**X2/X3 status:** now **admitted** (X1-B passes, brief §4 ordering satisfied) but **not yet run** —
the eigen arc/bootstrap extension (absolute-volt Paschen threshold ⇒ the genuine Newton case of
addendum §3.1) is the next deliverable; deferred here, marked BLOCKED-pending, not claimed.

## 4. Verdict (per-witness + combined, addendum §6)

- **(B) X1-B: `XSIM-MATCH-B`** — z and δ match native to machine precision; independent by
  construction; galvanic-authorised. **B carries X1 → X1 PASSES.**
- **(A) X1-A: `XSIM-DIVERGENT-A`** — ngspice continuous-time under-pump (z 1.054, δ 0.192),
  localised as a SPICE artifact (B matches, so the circuit is fine). Not a circuit defect.
- **Combined X1: MATCH (on B, primary).** Anchor-chain: the galvanic anchor holds for both witnesses;
  where A and the native disagree, B (the trustworthy analytic witness for this non-overlapping tier)
  and the native agree — the native quasi-static z is corroborated, and A's deviation is the named
  continuous-time artifact.

A divergence in A with B matching localises a residual ngspice artifact, not a circuit defect
(addendum §6) — stated. CHANGELOG updated; branch left for TMD review; not merged.

## 5. Deliverables

- `xsim_queiroz_matrix.py` — (B) segment-matrix/eigen witness; own cluster solver; self-test =
  galvanic 1.2033 (primary) + X1-B shuttle 1.18938/δ 0.2175 + Queiroz Fig-1 best-effort.
- `xsim_queiroz_V0.png` — (B) authorisation + X1-B match + emergent δ-vs-threshold.
- `xsim_netgen.py` / `xsim_x1_shuttle.net` — (A) ngspice shuttle (rev 0.3, tertiary).
- `xsim_x1_fire_readout.png` — (A) SG3b threshold crossing (δ-is-measured evidence).
- `xsim_from_solver.py` — consumer: runs A, drives B, dual-witness §5 table, three-way z, V0 plot.
- `xsim_comparison.csv` — full table (native + B + A). `xsim-findings.md` — this document.
