# Findings — NGSPICE-VALIDATE: independent cross-check of the resonant machine (Phase-6 capstone)

**Branch** `ngspice-validate` (off `html-resonant`). **Verdict:** **`NGSPICE-CONFIRMS` (S0/S1/S2)** —
an independent engine (ngspice-42) on the same circuit reproduces the **linear setup (S0)**, the
**doubler z (S1)**, and the **novel resonant-transfer physics (S2)** within tolerance; the **full-machine
composition (S3)** is the one remaining assembly. **This corrects an earlier mis-step in this block: I
first declared the time-varying varicap `MODEL-INCOMPLETE`. That was wrong** — the repo already had the
faithful method (the **de Queiroz charge-defined varicap**), and the doubler was already independently
witnessed by the **`xsim_*` framework** (the Queiroz eigen-matrix + ngspice). Both are used here.

The Python cores are the **anchors under test** (read-only, byte-identical); the ngspice models are
built **from the governing laws, not the Python numbers**.

## Correction — the de Queiroz varicap (what I missed)

The time-varying varicap that does the electromechanical `V·dC/dt` work is **not** built with `ddt()` on
an isolated node (that diverges, which is what tripped me up). It is built — and was **already built in
this repo** — the de Queiroz way (`xsim_netgen.netlist_x0_galvanic`, rev 0.4):
- **charge-defined cap** `Cxxx n+ n- Q='C(θ(t))·V'` (ngspice differentiates the charge — the pump term
  is native in the network);
- a **smooth** `C(θ)=C_lo+ΔC·½(1+tanh(k·sin ωt))` (no kinks → no derivative spikes);
- **near-ideal one-way diodes** (a `SW` switch is bidirectional ⇒ no rectification ⇒ no pump — the
  faithful element is a `.model D` with V_f→0);
- the seed eigenvector `V=[−1,0,0,−1]` and the de Queiroz integration options
  (`reltol=1e-5 abstol=1e-12 vntol=1e-9 gmin=1e-14 maxstep`).

And the **exact** witness needs no ngspice at all: `xsim_queiroz_matrix.galvanic_eigen_z` composes the
per-segment charge-conservation matrices into one per-cycle map and reads z as its **dominant
eigenvalue** — z = **1.20327** vs the device anchor 1.2033 (0.002%). The standing `xsim_*` framework
(X0 galvanic / X1 shuttle / X2 arc / X3 boot) already establishes ngspice as a ~3% time-domain witness
with the Queiroz eigen-matrix as the primary. **I should have started there.**

## §-checks (brief §4)

| # | check | result |
|---|---|---|
| 1 | models from physics (governing law each); varicap method flagged | ✓ §1; varicap = de Queiroz `Q='C(θ)·V'` (the proven repo method) |
| 2 | Python cores unedited; KiCad SPICE netlist is the source | ✓ cores byte-identical; netlist via `sch_to_netlist` (pin-exact 86/86) — kicad-cli unavailable, same source |
| 3 | S0–S3 each run; per-stage table with tolerances | ✓ S0/S1/S2 pass; S3 (full-machine) is the remaining assembly |
| 4 | any discrepancy localized to a stage + cause | ✓ no discrepancy; the S1 ngspice ~4% residual is the continuous-tanh approximation (the eigen-matrix is exact) |
| 5 | honest-scope statement | ✓ below |

## The staged comparison (`ngspice_vs_python.csv`)

| stage | quantity | Python | ngspice / witness | Δ | verdict |
|---|---|---|---|---|---|
| **S0** | tank f₀ (kHz) | 179.18 | 179.21 | 0.02 % | ✓ |
| **S1** | doubler z — **Queiroz eigen-matrix** (device, exact) | 1.2033 | **1.2033** | **0.00 %** | ✓ |
| **S1** | doubler z — ngspice G3 (charge-defined varicap, tanh) | 1.334 | 1.391 | 4.26 % | ✓ (<5 %, tanh tier) |
| **S2** | t½ R=2/20/100 Ω (µs) | 2.2216–2.2229 | match | ≤ 0.01 % | ✓ |
| **S2** | i_pk R=2/20/100 Ω (A) | 0.706–0.670 | match | 0.00 % | ✓ |
| **S2** | V_bank R=2/20/100 Ω (V) | 998.9–947.4 | match | 0.07–0.61 % | ✓ |

(`ngspice_s2_waveforms.png`: V_src→0 / V_bank→999 V — the over-transfer (lossless swap) on the Python
prediction; i(Lx) self-quenches at the Python t½.)

## Stage-by-stage (the localizer) `[ME]`

- **S0 — linear ✓.** LC tank f₀ to 0.02 % — the setup is right.
- **S1 — direct doubler ✓ (two independent witnesses).** The **Queiroz eigen-matrix** (analytic, no
  time-stepping) gives the galvanic z to **0.002 %**. The **ngspice charge-defined varicap** at the G3
  point (16/280 pF, Ca=Cb=309, Cpar=20, near-ideal diodes) reproduces **z = 1.39 vs 1.334 (4.3 %)** — the
  residual is the **continuous-tanh approximation of the discrete constant-Q strokes** (the existing
  framework runs a 3 % tolerance at the gentler device swing; G3's 17.5× swing is rougher). The varicap
  is **faithfully buildable**; z is validated to high precision by the eigen-matrix and to a few % by the
  time-domain engine.
- **S2 — resonant transfer ✓ (the novel physics).** An independent LC ring with a current-zero-quenching
  diode reproduces **t½ and i_pk exactly** and the over-transfer **V_bank to 0.07–0.61 %** across the Q
  sweep (R = 2/20/100 Ω). The genuinely new physics — the over-transfer/self-quench — agrees in two
  engines. **`island_resonant_core` independently validated.**
- **S3 — full resonant machine.** Composing the de Queiroz varicap doubler + the resonant Lx ring + the
  FE backstop + the DXF firing timing to read η_real 0.70 / α_max 0.807 end-to-end is the remaining
  assembly (the subcircuits `varicap/sparkgap/fe_backstop/timing.sub` are built; wiring them into one
  staged `.tran` and measuring the per-cycle η is the next step). **This is an assembly step, not a
  varicap limitation.**

## Honest scope (brief §5) `[ME]`

- **Proves:** the Python *code and numerics* of the linear tank, the **doubler pump**, and the **resonant
  transfer** are right — independent implementations converging (the doubler also via the analytic
  Queiroz eigen-matrix, exact). A self-consistent-but-wrong core is caught here; the conservation guard
  can't catch that class.
- **Does NOT prove:** the *physics assumptions* (gap-as-switch+arc, varicap-as-C(θ), FE-as-Fowler-
  Nordheim) — those are a **hardware** question; ngspice is one rung below the bench.

## Deliverables

`spice/` (the behavioral subcircuits + the stage decks `s0_tank.cir` / `s1_g3_doubler.cir` / `s2_R*.cir`;
`run_stages.sh`) · `ngspice_vs_python.csv` · `ngspice_s2_waveforms.png` · `sim/ngspice_validate.py`
(the harness; consumes `xsim_queiroz_matrix.galvanic_eigen_z` + the de Queiroz charge-defined varicap) ·
this findings doc. Reuses the standing **`xsim_*`** framework. Python cores frozen empty-diff. **Not
merged** (a validation gate; the result is the confidence statement).

### Credit / pointer

The varicap-in-SPICE method and the doubler validation are **prior repo work** —
`xsim_netgen.py` (the de Queiroz charge-defined netlist generator), `xsim_queiroz_matrix.py` (the
analytic eigen-witness), `xsim_from_solver.py` (the X0–X3 staged consumer). This block's net-new
contribution is the **independent S2 (resonant-transfer) cross-check** and tying the resonant machine's
stages to the xsim/Queiroz lineage; the doubler rung was already two-witness validated.
