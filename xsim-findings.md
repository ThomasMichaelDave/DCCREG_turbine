# xsim — findings (Phase 6, rev 0.1): **XSIM-PARTIAL — X0 RECOVERED · shuttle tiers XSIM-BLOCKED**

**Verdict line:** `X0-ANCHOR-RECOVERED` · `XSIM-BLOCKED (X1/X2/X3 shuttle tiers — named)`.

**Branch** `claude/feasibility-approval-planning-5gkcam`, fast-forwarded onto `bootstrap-gate`
head (so it carries the canonical producer chain: `shuttle_core.py` + spark/bootstrap consumers +
frozen `reference/doubler_core.py`). `reference/doubler_core.py`, `shuttle_core.py` and `index.html`
**untouched** — the gate adds only a netlist generator, the `.net` file, and a comparison consumer
(brief §2.1). Not merged.

ngspice is the **witness**, never the judge; the galvanic anchor (z = 1.2033,
`reference/doubler_core.py`) is the tiebreaker (brief §1).

---

## 1. Engine probe (brief X-1) — **PASS**

`ngspice-42` installed in-environment (egress permitted the system package). It runs a headless
batch (`ngspice -b`) and emits a parseable binary `.raw` (verified). The X-1 gate is cleared — this
is **not** an `XSIM-BLOCKED-ENVIRONMENT` outcome.

Two netlist primitives were verified against ngspice-42 before any campaign step:

- **Time-varying capacitor** — the charge-defined form `Cxxx n+ n- Q='C(θ(t))·V'`. A decisive
  isolated-node test confirmed the **parametric V·dC/dt pump term is present** (an isolated charged
  node's voltage swings inversely with C, charge conserved). This is the brief §3 charge-based
  technique, realised natively (ngspice's `ddt()` B-source was tried first and is unreliable — it
  threw `inf` range errors; the `Q=` capacitor is the correct primitive).
- **Spark gap / diode** — voltage-controlled switch `Sxxx` + `.model SW`, and near-ideal `.model D`.

---

## 2. X0 — degenerate galvanic anchor — **RECOVERED (PASS)**

Shuttles → near-ideal galvanic diodes (frozen direction 2→0, 3→0, 1→3, 4→2), LR shorted, islands/Cx
dropped. C1/C2 swing (tanh square, anti-phase) between the frozen extremes; the unloaded lossless
pump grows the rail |V1|+|V4| ~ z per mechanical cycle; z read from the post-burn per-cycle ratio.

| Quantity | Native (`galvanic_z`) | ngspice | Δ | Tolerance | Result |
|---|---|---|---|---|---|
| **X0 anchor z** | **1.2033** | **1.2042** | **+0.0009** | ≤ 0.03 (stretch ≤ 0.002) | **PASS** |

Δz = +0.0009 sits inside even the stretch tolerance, and is **insensitive to diode ideality** (n
swept 0.001–0.02 → z stable at ~1.204), confirming the residual forward drop is negligible. The
anchor authorises the engine + the charge-defined-cap method. Overlay: `xsim_x0_anchor.png`.

### 2.1 Named modelling note (deviates from brief §3 "near-ideal switches") — **[IR]**

The brief proposed near-ideal **switches** at X0. Empirically a ngspice voltage-controlled switch
(`Sxxx`/`.model SW`) conducts **bidirectionally** while closed, so it cannot **rectify** — the
parametric pump never ratchets and the rail just sloshes (measured z = **1.0**, no growth). The
faithful one-way element is a near-ideal `.model D` diode with the forward drop driven to ~0. The
brief's stated concern — a diode drop pulling z *under* 1.2033 — **does not materialise** at this
device point (measured z = 1.204, slightly *above* the anchor). Surfaced, not engineered around.

---

## 3. X1 / X2 / X3 — shuttle tiers — **XSIM-BLOCKED (named)**

Per brief §4 the ideal tier (X1) must pass before the arc tier (X2) is admitted. X1 is the flying-
bucket **shuttle**: the galvanic cross-diodes are replaced by flying-capacitor islands (Cx3 on
7–3, Cx4 on 8–2) with rotor-clocked spark gaps — a *return* (SG1/SG2), a *load* (SG3a/SG4a), and an
emergent *fire* (SG3b/SG4b) that strikes during the Cx collapse. The genuine independent witnesses
are z, the **emergent δ = θ(SG3b) − θ(SG1)**, and the island ledger (the absolute event angles are
clock-imposed datum — only δ counts, brief §5 carve-out).

**Blocker (named, brief §6 `XSIM-BLOCKED`):** the quasi-static discrete-event shuttle does not map
onto ngspice continuous-time integration within this gate. Across ~8 principled netlist variants
(tanh-square vs raised-cosine drive; switch vs one-way-diode gaps; bidirectional→one-way conversion
of *every* gap; soft/stiff switch models; series-R damping; Gear integration; gmin/maxstep
sweeps), the witness reached one of two named failure modes:

1. **Timestep collapse at the load station** — `Timestep too small … trouble with sld1`: the load
   gap connects two **charge-defined behavioral caps** (node 1's C1v and the island's Cx) through a
   gap, forming a stiff cap↔gap loop the trapezoidal/Gear stepper cannot resolve (the behavioral-Q
   cap carries an internal node that trips at the discontinuity). This is the dominant failure once
   all gaps are made one-way (the physically correct choice from §2.1).
2. **No ratchet when it runs** — in the variant that integrates to completion, the rail **decays**
   (z ≈ 0.985): the continuous witness does not reproduce the native's quasi-static charge-
   redistribution (the native loads the island at the plateau, *isolates* it, lets Cx collapse to
   boost V, then fires — an instantaneous-equilibrium cluster-solve with an emergent strike-state
   selection that has no direct continuous-time analogue without bespoke event scheduling).

The galvanic limit (X0) pumps cleanly because its commutation is memoryless (direct diodes); the
shuttle's **isolated-island-boost-then-emergent-fire** is the element ngspice cannot faithfully
represent here. The generator + harness are emitted for a refined-netlist / TMD-side continuation
(e.g. XSPICE event-driven gaps, or fixed-C islands with scheduled charge injection).

---

## 4. Full §5 comparison table (brief §7 — the full table, not just the failures)

All **native** values are consumed live from `shuttle_core` (or cited from its published findings);
the **SPICE** column is filled where the witness is authorised and `BLOCKED` (with §3's named
reason) for the shuttle tiers. Machine-readable: `xsim_comparison.csv`.

| Quantity | Native | SPICE | Δ | Tolerance | Status |
|---|---|---|---|---|---|
| X0 anchor z (galvanic) | 1.2033 | **1.2042** | +0.0009 | ≤ 0.03 | **PASS** |
| X1 z (ideal shuttle) | 1.18938 | — | — | ≤ 0.005 | BLOCKED |
| X1 emergent δ (SG1→SG3b) | 0.2175 | — | — | ≤ 0.010 | BLOCKED |
| X1 event angles SG1/SG3a/SG3b | 0.0500/0.1200/0.2675 | — | — | ≤ 0.010 | BLOCKED |
| X1 event angles SG2/SG4a/SG4b | 0.5500/0.6200/0.7675 | — | — | ≤ 0.010 | BLOCKED |
| X1 island ledger drift | ~4.6e-14 | — | — | ≤ 1e-6 (hard) | BLOCKED |
| X2 z_arc (mid corner) | 1.18441 | — | — | ≤ 0.010 | BLOCKED |
| X2 clamp (× strike) | ~1.04 | — | — | ≤ 5% | BLOCKED |
| X3 V_floor (mid) | 187 V | — | — | ≤ 15% | BLOCKED |
| X3 V_sustain (mid@3000) | 437 V | — | — | ≤ 15% | BLOCKED |

**Benign carve-outs (declared, brief §5):** a rigid phase offset on all event angles equally is a
datum convention (only relative/δ drift would count); arc-tier z within its 0.010 band and the
clamp-knee shape are expected modelling differences — none of these is the blocker.

---

## 5. Anchor-chain arbitration & verdict

The anchor (galvanic z = 1.2033) is **recovered** by the independent engine, so ngspice and the
native producer **agree at the degenerate limit** — the engine, the charge-defined-cap method, and
the diode-doubler topology are confirmed as a faithful independent witness. No divergence is
claimed (this is not `XSIM-DIVERGENT`): the shuttle-tier quantities are **BLOCKED**, not
mismatched — the witness could not be brought to bear on them, so the native values stand as
*unwitnessed targets*, not as disagreements.

**Net:** `X0-ANCHOR-RECOVERED` (engine + method confirmed) · `XSIM-BLOCKED` on the X1/X2/X3 shuttle
quantities (named numerical/representational obstacle, §3). A blocked result is a deliverable, not
a failure (brief §6). CHANGELOG updated; branch left for TMD review; not merged.

## 6. Deliverables

- `xsim_netgen.py` — netlist generator (reads device point from `shuttle_core` + `presets/R1-baseline.json`).
- `xsim_x0_galvanic.net` — the X0 anchor netlist (recovers z = 1.2042).
- `xsim_from_solver.py` — pure comparison consumer (runs ngspice, parses `.raw`, pulls native from `shuttle_core`).
- `xsim_x0_anchor.png` — X0 rail-growth + per-cycle-ratio overlay vs the native anchor.
- `xsim_comparison.csv` — the full §5 table, machine-readable.
- `xsim-findings.md` — this document.
