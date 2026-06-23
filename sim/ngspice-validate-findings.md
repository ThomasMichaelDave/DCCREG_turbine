# Findings — NGSPICE-VALIDATE: independent cross-check of the resonant machine (Phase-6 capstone)

**Branch** `ngspice-validate` (off `html-resonant`). **Verdict:** **`MODEL-INCOMPLETE`** — with a
**strong partial validation**. An independent engine (ngspice-42) on the same circuit confirms the
linear setup (S0) **and the novel resonant-transfer physics (S2) to < 0.6 %** across a Q sweep — the
part the brief calls "most worth an independent check." The **time-varying varicap (S1, and therefore
the full-machine S3) is the anticipated SPICE limitation**: the faithful work-term formulation does not
converge in the pumping network, so z 1.334 / η_real 0.70 are **not** independently re-confirmed by
ngspice. The gap is named precisely (the varicap) and the path forward stated.

The Python cores are the **anchors under test** (read-only, byte-identical); the ngspice behavioral
models are built **from the governing laws, not the Python numbers** (independence is the whole value).

## §-checks (brief §4)

| # | check | result |
|---|---|---|
| 1 | behavioral models from physics (governing law each); varicap method flagged | ✓ §1 below; varicap = `i = d(C(θ)·V)/dt` (ddt), flagged fragile |
| 2 | Python cores unedited; KiCad SPICE netlist is the source | ✓ cores byte-identical; netlist via `sch_to_netlist` (pin-exact 86/86) from the schematic (kicad-cli unavailable — same source) |
| 3 | S0–S3 each run; per-stage table vs the Python anchors with tolerances | ✓ S0 ✓, S2 ✓, S1 fails (varicap), S3 gated on S1 (table below) |
| 4 | any discrepancy localized to a stage + likely cause | ✓ localized to **S1 — the time-varying varicap** (SPICE model limitation, not a Python bug) |
| 5 | honest-scope statement | ✓ below (validates implementation, not the physics assumptions) |

## 1. The behavioral models (from the physics) `[OC]/[IR]`

Each `spice/*.sub` derives from its **governing law**, never from a Python output:
- **`varicap.sub`** — `i = d/dt[C(θ)·V]` (charge-defined, via ngspice `ddt()`), `C(θ)=C_mid+C_amp·cos(ωt)`
  from the plate geometry. The second term `V·dC/dt` is the electromechanical work. **Method flag:**
  ngspice's behavioral `C='f(time)'` and `Q='f(time)'` forms **drop the `V·dC/dt` work term** (verified:
  V stays constant when C ramps at constant charge). `ddt(C·V)` is **exact in isolation** (verified: a
  ramped-C ddt-cap; and `ddt(1n·v)` returns C·dV/dt to machine precision) — but see §3 S1.
- **`sparkgap.sub`** — a voltage-armed switch (strike at `V_strike`, Paschen) feeding a diode (the
  one-way **current-zero self-quench**) + an arc-drop source (`V_arc`).
- **`fe_backstop.sub`** — a B-source `I = A·V²·exp(−B/V)` (Fowler-Nordheim), the soft bleed; `A,B` from
  the FN law + a designed leakage (an `[IR]` coefficient).
- **`timing.sub`** — rotary arming from the DXF station angles (rotor angle = time).

## 2. The staged comparison (`ngspice_vs_python.csv`)

| stage | quantity | Python | ngspice | Δ | verdict |
|---|---|---|---|---|---|
| **S0** | tank f₀ (kHz) | 179.18 | 179.21 | **0.02 %** | ✓ |
| **S2** | t½ R=2 Ω (µs) | 2.2216 | 2.2214 | 0.00 % | ✓ |
| **S2** | i_pk R=2 Ω (A) | 0.7063 | 0.7063 | 0.00 % | ✓ |
| **S2** | V_bank R=2 Ω (V) | 998.9 | 997.0 | 0.19 % | ✓ |
| **S2** | t½ R=20 Ω (µs) | 2.2216 | 2.2218 | 0.01 % | ✓ |
| **S2** | i_pk R=20 Ω (A) | 0.6993 | 0.6993 | 0.00 % | ✓ |
| **S2** | V_bank R=20 Ω (V) | 989.0 | 983.0 | 0.61 % | ✓ |
| **S2** | t½ R=100 Ω (µs) | 2.2229 | 2.2228 | 0.00 % | ✓ |
| **S2** | i_pk R=100 Ω (A) | 0.6697 | 0.6697 | 0.00 % | ✓ |
| **S2** | V_bank R=100 Ω (V) | 947.4 | 946.7 | 0.07 % | ✓ |
| **S1** | varicap const-Q ratio (ideal 2.0) | 2.000 | **1.650** | **17.5 %** | ✗ |

(`ngspice_s2_waveforms.png`: V_src → 0 / V_bank → 999 V — the full over-transfer (lossless swap) settling
exactly on the Python prediction; i(Lx) peaks at the Python i_pk and self-quenches at the Python t½.)

## 3. Stage-by-stage (the localizer) `[ME]`

- **S0 — linear sanity ✓.** The LC tank rings at f₀ to **0.02 %** — the netlist/integrator setup is right.
- **S2 — resonant transfer ✓ (the novel physics).** An independent LC ring with a current-zero-quenching
  diode reproduces **t½ and i_pk exactly** and the over-transfer V_bank to **0.07–0.61 %** across the
  Q sweep (R = 2 / 20 / 100 Ω). This is the genuinely new physics — the over-transfer/self-quench the
  resonant machine is built on — and **two independent engines converge on it.** `island_resonant_core`
  is independently validated.
- **S1 — direct doubler ✗ (the varicap, MODEL-INCOMPLETE).** The pump needs the time-varying varicap's
  `V·dC/dt` electromechanical work. Two synthesis routes, both fall short of *faithful + convergent*:
  - **`ddt(C(t)·V)`** — the faithful form (exact in isolation) **does not converge** in the pumping
    network (a current-source-only node + the work term diverges / stalls).
  - **`C(t)` + a `V·dC/dt` B-source** — converges, but a single constant-Q stroke is **17.5 % off** the
    ideal (V should double; ngspice gives ×1.65), and that error **compounds over the many cycles** z
    requires.
  So ngspice cannot faithfully reproduce z 1.334 / η 0.386 here. **This is a SPICE-model limitation, not
  a Python bug** — localized cleanly to the varicap layer by the staging. **S3 (full machine) is gated on
  S1** and is therefore not run.

## 4. Honest scope (brief §5) `[ME]`

- **What this proves:** the Python *code and numerics* of the **linear tank and the resonant transfer**
  are right — two independent implementations of the same idealized physics converging to < 0.6 %. A
  self-consistent-but-wrong resonant core would have been caught here; the conservation guard cannot
  catch that class of error. This is real, independent confidence in the **novel** part of the machine.
- **What it does NOT prove:** (a) the **physics assumptions** (both engines idealize the gap as
  switch+arc, the varicap as C(θ), the FE as Fowler-Nordheim) — that is a **hardware** question; ngspice
  is one rung below the bench; (b) the **doubler pump** (z/η) — not because it is wrong, but because the
  varicap can't be built faithfully in ngspice. Note `doubler_core` is **already** an independently
  cross-checked mirror of the frozen JS `solveDoubler4` (4 anchors: no-swing 1.000, device 1.203, narrow
  1.000, wide 1.438) — so the pump is validated against a second implementation, just not *ngspice*.

## 5. The verdict + the named gap

**`MODEL-INCOMPLETE`** — the resonant transfer (S2) and the linear setup (S0) are independently
confirmed; the time-varying varicap (S1/S3) is not faithfully buildable in ngspice. **The recommended
follow-up** to close S1/S3: (a) **LTspice** (its behavioral capacitor handles time-varying C with the
work term more robustly), or (b) a **switched-network constant-Q model** (the doubler as discrete
charge-conserving strokes — faithful to how `doubler_core` itself operates), or (c) a **Python↔ngspice
co-sim** (Python drives the varicap charge, ngspice the linear+gap network). Until then: the resonant
machine carries **two-engine confidence on its novel core (the LC over-transfer)** and **two-implementation
confidence on its pump (Python mirror of the JS solver)** — the doubler↔ngspice rung is the one named gap.

## Deliverables

`spice/` (the behavioral subcircuits `varicap.sub`/`sparkgap.sub`/`fe_backstop.sub`/`timing.sub`; the
stage decks `s0_tank.cir`/`s1_varicap_attempt.cir`/`s2_R*.cir`; `run_stages.sh`) ·
`ngspice_vs_python.csv` (the per-stage comparison) · `ngspice_s2_waveforms.png` (the S2 over-transfer,
two engines) · `sim/ngspice_validate.py` (the harness + verdict) · this findings doc. Python cores frozen
empty-diff. **Not merged** (a validation gate; the result is the confidence statement).
