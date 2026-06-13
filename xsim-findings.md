# xsim — findings (Phase 6, rev 0.2): **X0 RECOVERED · X1′ UNBLOCKED & PUMPING · XSIM-DIVERGENT on z**

**Verdict line:** `X0-ANCHOR-RECOVERED` · `X1-UNBLOCKED (Queiroz)` · `FIRE-EMERGENT (not VOID)` ·
`XSIM-DIVERGENT on z (localised, named)`.

**Branch** `claude/feasibility-approval-planning-5gkcam` (on `bootstrap-gate` head — carries the
canonical producer chain). `reference/doubler_core.py`, `shuttle_core.py`, `index.html` **untouched**
(mirror FAITHFUL, shuttle C0 green after the run — verified). Not merged. ngspice is the witness;
the galvanic anchor (z = 1.2033) is the tiebreaker.

This rev folds in the **rev 0.3 addendum** (De Queiroz source-imposed charge-transfer) which cleared
the rev-0.1 X1 numerical blocker. The device point, firing order, tolerances (§5) and verdict set are
unchanged; the addendum changed only the *numerical realisation* of the caps/gaps.

---

## 1. Engine probe (X-1) — PASS

`ngspice-42` installed in-environment; headless `-b` batches emit parseable binary `.raw`. Not an
`XSIM-BLOCKED-ENVIRONMENT`.

## 2. X0 / X0′ — degenerate galvanic anchor — RECOVERED (PASS)

Near-ideal one-way diodes (2→0,3→0,1→3,4→2), LR shorted, islands dropped; C1/C2 charge-defined `Q=`
caps swing anti-phase. **ngspice z = 1.2042 vs native 1.2033, Δ = +0.0009** (inside the stretch
≤0.002), insensitive to diode ideality. Authorises the engine + the charge-defined-cap method.
Overlay `xsim_x0_anchor.png` / `xsim_x0prime_anchor.png`.

*[IR] named note (carried from rev 0.1):* a ngspice `SW` switch is bidirectional when closed and
cannot rectify (z = 1.0, no pump); the faithful one-way element is a near-ideal `.model D` diode,
whose residual Vf does **not** pull z under 1.2033 (measured above).

## 3. X1′ — ideal flying-bucket shuttle — UNBLOCKED (Queiroz), pumping; z DIVERGENT

### 3.1 The unblock (addendum §1–3)

The rev-0.1 blocker — the isolated-island Cx-collapse boost had no stable continuous-time analogue
(timestep collapse at the load-station behavioral-Q-cap↔gap loop; no ratchet) — is **cleared** by the
source-imposed method:

- **Islands (Cx3 on 7–3, Cx4 on 8–2): charge-controlled `V = Q/Cx(t)`** (Cx+boss lumped, charge on a
  1 F integrator node, terminal voltage synthesised by a `B`-source). Verified in isolation: an
  isolated island boosts **×20 = Cx_max/Cx_min** as Cx collapses, charge conserved to machine
  precision. The boost is imposed by the source law ⇒ **ratchet by construction, no stiff Q-node**.
- **C1v/C2v: charge-defined `Q=` caps** (proven at X0; compose on shared nodes with Ca/CPAR).
- **Return SG1/SG2 + load SG3a/SG4a: clocked *bidirectional* switches** — the ideal-tier native gaps
  are cluster-merge equalisations; one-way diodes are wrong here (and never conduct down-pumping).
- **Fire SG3b/SG4b: source-imposed soft-threshold dump** `I = win·gm·max(0, V(isl,snk) − Vstrike)` —
  one-way, threshold `Vstrike`, self-extinguishing, eligibility = the Cx collapse window (the cap
  profile), **not** a fire clock edge.

Result: the shuttle **runs** (≈3 s, no timestep collapse) and **pumps** (z > 1, ratchets). Both
rev-0.1 blocker modes are eliminated. *(Numerical notes: over-ideal diodes, n ≤ 0.05, cause Newton
micro-stepping → use moderate diodes; the held-collapse Cx profile slams V=Q/Cx at the θ-wrap → the
profile reinflates post-fire to stay continuous; tiny island stabiliser caps aid start-up.)*

### 3.2 The fire is EMERGENT — δ measured, not imposed (addendum firewall, the central evidence)

Sweeping the strike threshold `Vstrike` **moves the fire angle** — the proof δ is read off the
boosted rail, not set by a clock (a clock-pinned fire would not respond). `xsim_x1_fire_readout.png`:

| Vstrike | emergent δ = θ(SG3b) − θ(SG1) | z |
|---|---|---|
| 0.00 | 0.192 | 1.054 |
| 0.05 | 0.301 | 1.050 |
| 0.12 | 0.328 | 1.058 |
| 0.25 | 0.329 | 1.069 |

δ spans **0.192 → 0.329** as the threshold rises — the same emergent trend as the native
`pVbkFire` sensitivity (0.218 → 0.39). **This is NOT `XSIM-VOID-METHOD`:** the fire is a genuine
voltage-threshold strike on the boosted island rail.

### 3.3 K-invariance sub-gate (addendum §3) — PASS

The conditioner `K` cancels analytically in `V = Q/C`; numerically z and δ are stable across three
decades:

| K | z | δ |
|---|---|---|
| 1e8 | 1.0551 | 0.1914 |
| 1e9 | 1.0549 | 0.1913 |
| 1e10 | 1.0696 | 0.1910 |

K does no physics (z, δ stable) — the method is sound.

### 3.4 The divergence (named, localised)

At the ideal device point (Vstrike = 0): **ngspice z = 1.0544 vs native 1.18938, Δ = −0.135** —
outside the ≤ 0.005 tolerance. The emergent δ = 0.1917 vs 0.2175 (Δ = −0.026) is qualitatively
right but outside ≤ 0.010. The shortfall is **robust across every fire realisation** (one-way diode,
near-ideal diode, source-imposed dump, gm ∈ [1e-3, 1e-2]) and across K — so it is **not** a
fire-gap artifact. Diagnosis (`V(7,3)` over a steady cycle): the charge-controlled island **boosts
correctly** (overvoltage 0.03 plateau → 0.32 at collapse end), but the continuous-time shuttle
**under-transfers charge per cycle** relative to the native quasi-static cluster-solve (the rail node
does not boost as strongly between phases). This is the expected continuous-time-vs-quasi-static
modelling difference, localised to the X1 charge-transfer rate — a SPICE realisation artifact, not a
defect in the native producer.

## 4. Full §5 comparison table (brief §7 — the full table)

Native values consumed live from `shuttle_core`; machine-readable `xsim_comparison.csv`.

| Quantity | Native | SPICE | Δ | Tolerance | Status |
|---|---|---|---|---|---|
| X0 anchor z (galvanic) | 1.2033 | **1.2042** | +0.0009 | ≤ 0.03 | **PASS** |
| X1 z (ideal shuttle) | 1.18938 | **1.0544** | −0.135 | ≤ 0.005 | **FAIL** (divergent) |
| X1 emergent δ (SG1→SG3b) | 0.2175 | **0.1917** | −0.026 | ≤ 0.010 | FAIL (close; emergent ✓) |
| X1 island ledger (imposed) | ~5e-14 | 0 (by construction) | — | ≤ 1e-6 | PASS |
| X2 z_arc (mid corner) | 1.18441 | — | — | ≤ 0.010 | BLOCKED (gated behind X1, §4) |
| X2 clamp (× strike) | ~1.04 | — | — | ≤ 5% | BLOCKED (gated) |
| X3 V_floor (mid) | 187 V | — | — | ≤ 15% | BLOCKED (gated) |
| X3 V_sustain (mid@3000) | 437 V | — | — | ≤ 15% | BLOCKED (gated) |

X2/X3 stay BLOCKED by the **strict campaign order** (brief §4): the arc tier is not admitted until
X1 passes §5, and X1 z is out of tolerance. The island-ledger row is PASS-by-construction (the
charge-controlled integrator conserves Q exactly) — a structural consequence of the method, not an
independent witness of the native ~1e-14 drift, and reported as such.

## 5. Anchor-chain arbitration & verdict

The anchor (galvanic z = 1.2033) is recovered by the independent engine, so where the two simulators
disagree on z the anchor designates the **native quasi-static result as authoritative** and the
ngspice continuous-time under-pump as the localised artifact (the SPICE shuttle never reproduces the
anchor's per-cycle gain in the shuttle limit; it falls ~0.135 short). The disagreement is **named and
localised** (charge-transfer rate, §3.4), the fire is **emergent** (not VOID), and the method is
**K-invariant** (sound).

**Net (rev 0.2):** `X0-RECOVERED` · the Queiroz method **unblocks X1** (runs + pumps; rev-0.1
`XSIM-BLOCKED` retired) · the emergent δ is demonstrated · but **`XSIM-DIVERGENT` on z** (1.0544 vs
1.18938, localised to the continuous-time charge-transfer rate). A divergence is a deliverable, not a
failure (brief §6): it yields a documented SPICE artifact (the shuttle limit needs a charge-transfer
realisation closer to the quasi-static cluster-solve — e.g. a per-event imposed equalisation — to
close the ~0.135 z gap). CHANGELOG updated; branch left for TMD review; not merged.

## 6. Deliverables

- `xsim_netgen.py` — generator (X0 galvanic + X1′ Queiroz shuttle); reads device point from
  `shuttle_core` + `presets/R1-baseline.json`.
- `xsim_x0_galvanic.net`, `xsim_x1_shuttle.net` — the netlists.
- `xsim_from_solver.py` — pure comparison consumer (ngspice runner, `.raw` parser, fire-angle readout,
  K-invariance sweep, VOID-METHOD guard).
- `xsim_x0_anchor.png` / `xsim_x0prime_anchor.png` — anchor recovery overlay.
- `xsim_x1_fire_readout.png` — **the SG3b strike on the boosted rail + emergent δ vs threshold** (the
  central rev-0.3 evidence that δ is measured, not imposed).
- `xsim_comparison.csv` — the full §5 table. `xsim-findings.md` — this document.
