# Findings — ISLAND-ASDRAWN Pass A (brief r0.2): event-driven KCL solver on the drawn sheet

**Branch** `claude/new-session-0az7f9`. It is based on `kicad-overlay` f9c9efa, and this session may
only push to that branch. **Not merged**: TMD signs off.

The r0.1 ngspice harness and its `SINK-PARTIAL` result are **withdrawn**. They are kept as
`sim/island-asdrawn-r01-spice-findings.md` and `sim/island_asdrawn_r01_spice.py`, whose runner is
disabled. Its committed `spice/ia_*` decks are now frozen.

## VERDICT: `HARNESS-FAIL` at H3 (station-armed arm). No verdict.

The pre-committed rule (brief §5) is: "Any failure is `HARNESS-FAIL`: stop, no verdict". The
campaign was therefore stopped after the harness gates. R1, R2/G1m, T1 and R4 were **not run**, and
no z or η comparison between the island twins is reported.

The failure is **not a solver defect**. It is a physics finding that the gate did not anticipate:

> **Station phasing binds.** The galvanic doubler with its rectifiers armed at the DXF stations is
> a different machine from `solve_doubler4`, where all four diodes settle simultaneously. The
> stations are: rail return D1 at 3.0°, cross-couple D3 at 7.2°, and the mirror at 33°/37.2°.
>
> | arming | z (Cpar 20 pF) | z (Cpar 10 pF) |
> |---|---|---|
> | all four always armed (simultaneous) | **1.3340016** = solve_doubler4 (Δ 4e-12) | **1.4017931** (Δ 1e-12) |
> | DXF station order (return, then cross-couple) | **1.5225272** (+14.1 %) | **1.6544167** (+18.0 %) |
> | both armed together at 3.0° | 1.3340016 | — |
> | reversed order (cross-couple 3.0°, return 7.2°) | 1.3549236 | — |

Two things establish that this is physics and not the solver:

- **An independent re-computation reproduces it.** The scratch check is a node-level KKT solve with
  Lagrange multipliers, with no cluster reduction and no shared code. It asserted a unique
  complementarity solution at every step, and it gives 1.5225272 (station) and 1.3340016
  (simultaneous). Agreement with this solver is 1e-11.
- **The mechanism is path dependence.** Ideal diodes on a capacitor network are path-dependent.
  Once D1 has clamped node 2 at 3°, it cannot give charge back when D3 closes at 7.2°. The
  simultaneous solve finds a different complementarity point. `solve_doubler4` is therefore the
  anchor only for a machine whose gaps settle together, not for the DXF-phased one.

### Consequence for the brief (routed to TMD)

H3's station-armed arm cannot pass as written. It asserts that "station phasing does not bind",
and it does bind. Two things need a decision before Pass A can reach a verdict:

1. **Re-anchor G0.** Either accept the station-armed galvanic machine (z 1.5225 at the canary) as
   G0, or change the DXF windows. The deck-internal comparison R1 vs G1 vs G0 would be unaffected
   either way, since all three would run on the same station schedule. But the "model reproduction"
   row η(G0) = 0.386 describes a machine the DXF sheet does not run.
2. **Declare a cycle cut for η.** The second finding (§2) shows that per-cycle η is not
   cut-invariant once gaps fire sequentially. The verdict classes compare η(R1), η(G1) and η(G0),
   so the brief must fix the cut, or define η on a loaded steady state, before those classes are
   meaningful.

## 1. Gate table

| gate | result | status |
|---|---|---|
| **H1** ring path vs `island_resonant_core.integrate` and published S2 | t½ 2.221443 / 2.221498 / 2.222832 µs against published 2.22155 / 2.22155 / 2.22289 (Δ ≤ 0.0049 % ≤ 0.01 %). V_bank 998.8900 / 989.0145 / 947.4056 V against 998.8905 / 989.0150 / 947.4060 (Δ ≤ 5e-5 %). E_loss equals the integrator's | **PASS** |
| **H2** seq-stat, imported unchanged (ngspice, `asd_` decks) | all-direct z 1.3907; forward-resonant 10 µH z 1.3905 (the arbiter's own deck logs a convergence note) | **PASS** |
| **H3** galvanic anchor, ≤ 1e-6, at Cpar 20 and 10 pF | always-armed: Δ 3.7e-12 / 1.0e-12; η 0.385956, matching the frozen `energy_balance.csv` 0.385956. **Station-armed: Δ 0.141 / 0.180** | **FAIL** |
| **H4** direct-island anchor: this solver on the shuttle's own schedule and topology (Lx3/Lx4 shorted) vs `shuttle_core` | z 1.2983502589215656 against `shuttle_run` 1.2983502589215656 and `steady_capture` 1.2983502589215647 (Δ 3e-16) | **PASS** |
| **H4b** limit consistency: ring path at Lx → 0 with R 2 Ω, against the algebraic twin (both with a 0.1 pF island stray; without it the floating island is singular while Lx is open) | shorts (shuttle semantics) at 0.1 nH: Δ 2e-14. One-way quench at **0.01 nH** (overdamped): Δ 4e-14. At the literal **0.1 nH** the load loop is *under*-damped at 2 Ω, and one-way quench traps the overshoot: z 1.3198 against 1.2979, **+1.7 %** | **PASS** in the gate's stated (overdamped) regime; the 0.1 nH figure is recorded |
| H4c, H5, H6, H7, R0–R4 | not run: stopped at H3 per §5 | — |
| R0 `deck('reson', lxfwd=1e-3)` (ngspice, `asd_r0`) | **not observable**: the frozen arbiter deck aborts ("Timestep too small"), as it did in r0.1 | finding |

**H5, informally.** Energy conservation closes to machine precision on every run that was made:
residual ≤ 1.3e-14 of W_mech on the galvanic runs. W_mech is ΔU at constant charge per stroke,
ΔE_stored comes from the boundary states, and E_diss is ½vᵀC_th v from the pre-event Schur
complement. These are three independent computations.

## 2. Second finding — η of a growing, unloaded pump is cut-dependent `[OC]`

A pump growing at z per cycle has E(t) = z^{2t/T}·e(t). The per-cycle ratio ΔE/W_mech therefore
depends on where the cycle is cut, unless no event falls between two candidate cuts.

- For the simultaneous doubler, η = 0.38596 at every cut: after phase A, and at 31° and 45° in
  phase B.
- For the station-armed doubler, at the same z = 1.5225272, **η = 0.559 cut at 0° but 0.329 cut at
  29°.**

The frozen ledger's 0.386 is the post-phase-A cut of the simultaneous machine.

## 3. The harness, as built (for the re-run once H3 is resolved)

`sim/island_asdrawn.py` is one event-driven KCL solver for every twin.

- **State.** Node charges and inductor currents on the drawn netlist, node-exact from
  `topology_edge_list.csv` (43 parts, self-test). R-A = R-B = reference.
- **Strokes.** Capacitances follow `shuttle_core.profiles(θ)` at the canary (16–280 pF, Cx
  471 / 8 pF) at constant cluster charge, with conducting gaps held. W_mech = ΔU.
- **Events.** Armed gaps are solved as an exact complementarity problem: ideal rectifiers need
  forward charge ≥ 0 and blocking voltage ≤ 0. Inductor currents are held during the event. Loss =
  ½vᵀC_th v from the pre-state Schur complement.
- **Rings.** An event that leaves voltage across an Lx is integrated exactly by matrix exponential
  at frozen capacitances, with complementarity switching located by bisection. It runs to the
  driving-Lx current zero, i.e. the quench; bracket (b) gaps latch there. The residue then relaxes
  exactly to the quasi-static equilibrium (Lx → short), with loss ½vᵀC_th v + ½LI².
- **Continuous mode** (motor in) also integrates the motor L–C–R branches (0.64 H, 440 nF, 40 Ω)
  between events.
- **Locked `[IR]` choices:**
  - windows: arm at the station; rails to the end of their half; load disarms at the fire station;
    fire/backstop to the end of the half;
  - brackets: (a) sustained arc while armed; (b) one-way, latched after the first quench;
  - pCboss2 = 0, matching design_synth's C_min basis;
  - strays at {0, 5, 20} pF.

**Status of the harness pieces.** The ring and relaxation paths are exercised by H1 and H4b. The
continuous-mode (motor) path is written but has not been exercised on the drawn deck, because the
campaign was stopped at H3.

H4b's 0.1 nH row is already the resonant-quench effect, in miniature and in the exact algebra: an
under-damped series-L transfer through a one-way gap keeps its overshoot and raises z. Whether that
carries through at 1 mH on the drawn deck is exactly what R1 would measure.

## 4. Pre-committed prediction (unchanged, unevaluated)

- premise `PREMISE-FAILS`
- fire `LOOP-BYPASSED`
- arbiter `SINK-IS-PUMP` / `REVERSAL-ONLY`

None was tested; the stop came first.

## 5. Frozen empty-diff

The check covers two comparisons:
- `reference/`, `shuttle_core.py`, `sim/seq_stat_commutation.py`, `sim/design_synth.py`, `tools/`,
  `index.html`, `docs/kicad/` and `topology_edge_list.csv`, against f9c9efa;
- every committed `spice/` file, including the r0.1 `ia_*` decks, against HEAD.

`frozen_diff()` returns **empty**. New `spice/` names are `asd_`-prefixed.

## Deliverables

- `sim/island_asdrawn.py`: the solver, gates H1–H4b and on-load self-tests. Run `python3
  sim/island_asdrawn.py` to reproduce the gate table.
- `spice/asd_h2_*.cir` and `spice/asd_r0.cir`.
- This document.
- The CSV, T1 and trace deliverables are not produced: they belong to the verdict runs, which were
  stopped.
