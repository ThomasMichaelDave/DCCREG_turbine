# Findings — ISLAND-ASDRAWN Pass A: is the island sink real on the drawn sheet, at circuit level?

**Branch** `claude/new-session-0az7f9` (re-based onto `kicad-overlay` f9c9efa, as the brief requires; the
brief's name `island-asdrawn` was not used because this session may only push to its assigned
branch). **Not merged** — TMD signs off.

## VERDICT: `SINK-PARTIAL` · modifier `MOTOR-DEPENDENT` · `PREMISE-FAILS` · `LOOP-BYPASSED`

**The pre-committed arbiter prediction (`SINK-IS-PUMP`) is falsified. The two stroke predictions hold.**

| | bracket (a) sustained arc | bracket (b) one-way quench | model |
|---|---|---|---|
| z_G0 (galvanic anchor) | 1.412 | 1.412 | — |
| z_G1 (direct island, Lx→0) | 1.410 | 1.410 | — |
| **z_R1 (drawn, Lx 1 mH)** | **1.950** | **2.160** | — |
| η(G0) | 0.403 | 0.403 | 0.386 |
| η(G1) | 0.400 | 0.400 | 0.302 → `LEDGER-MISMATCH` |
| **η(R1)** | **0.569** | **0.701** | ≈ 0.50 |
| T_load/W_mech(G1) | 0.498 | 0.498 | 0.217 (4.407/20.347) |
| **f_rec,meas** | **0.34** | **0.60** | ≈ 0.91 |
| δ_z, δ_η | 0.03, 0.03 (the G1 timestep spread is 1e-8 in z and 6e-5 in η) | | |
| class | `SINK-PARTIAL` | `SINK-PARTIAL` | |

The rule is: z_R1 > z_G1 + δ_z and η(R1) > η(G0), but f_rec,meas < 0.86. So the verdict is
`SINK-PARTIAL`, and it is the same in both brackets. It is not `REVERSAL-ONLY`, because the gain is
also present under the sustained-arc bracket (a).

**What this means, read carefully:**

1. **The series-Lx islands do beat the direct machine on the drawn sheet.** I13 passes. The measured
   η is **0.57 under (a) and 0.70 under (b)**. Per §6 this band replaces 0.50. Bracket (a), 0.57, is
   the conservative figure.
2. **The mechanism is not the one the integrator assumes.** T1 finds `PREMISE-FAILS`: 0.6 % of the
   load-stroke charge reaches C_BR1–6. H7 finds `LOOP-BYPASSED`: the fire returns 0.01 % (a) and
   3.8 % (b) of its circulating charge to node 3. The gain comes from the **load stroke itself**
   (1 → SG3a1 → 7 → Cx3 → n17 → Lx3 → 3). With an inductor in series, that stroke becomes a 0.69 µs
   resonant half-cycle into Cb1 / Cpar3 / the C2 chain. There is no two-capacitor dump. The
   load-gap tax falls from 0.498 W_mech (G1) to 0.146 W_mech (R1a). Of the saving, 0.20 W_mech goes
   to the coil ESR and the rest is stored.
3. **This contradicts the banked principle** ("a pump's own equalization cannot be resonated for
   recovery") in this regime. The G1 ledger shows that the island's load gap is the pump's own
   cross-coupling. T_load(G1) = 0.498 is almost exactly G0's own D3/D4-slot tax of 0.542, and
   z_G1/z_G0 = 0.998. So the island does occupy the Dd3/Dd4 slot, as the brief read it. Yet
   resonating that slot raises the gain. The arbiter never saw this: its forward diodes conduct
   *continuously during a 44 µs tanh stroke*, so Lx is never step-excited (R0/H2). The drawn deck's
   gaps are **station-armed** and close on an already-built ΔV, which makes the transfer a
   resonant switched-capacitor transfer (soft charging). That behaviour is standard EE `[OC]`. How
   well it holds depends on the `[IR]` gap model; see the caveats.
4. **f_rec is low, but not because recovery is weak.** f_rec is normalised to T_load, and T_load
   in the drawn deck is 2.3× the model's figure (0.498 vs 0.217). The islands therefore recover
   *more absolute energy* than the model claims (Δη = +0.17 / +0.30 against the model's +0.20). They
   recover a *smaller fraction* of a tax that is larger than the model's.

**Caveats that bound the verdict:**
- Gaps are ideal armed conductances. Strike thresholds are scaled out, and the arming edge is
  0.5 µs.
- Lx carries a 20 Ω ESR `[IR]`. As drawn it is lossless, and the ring against the 2 pF load-gap
  stray does not converge numerically.
- R4 (absolute scale with the frozen `sparkgap.sub`) could not be observed.
- The motor-in twin G1m is not timestep-converged.

None of these reverses the sign of R1 − G1 in any variant run. The table in §3 shows this.

---

## 1. H/R check table

| check | result | status |
|---|---|---|
| **H1** S2 reproduction through this module's one-way gap element | t½ 2.22144 / 2.22150 / 2.22283 µs; V_bank 998.887 / 989.011 / 947.403 V at R = 2/20/100 Ω; worst Δ 0.005 % against the published 0.612 % | ✓ |
| **H2** arbiter `seq_stat_commutation`, imported unchanged | all-direct z = 1.3907; forward-resonant (10 µH) z = 1.3905. This module's `z_of` equals `run_z` to 7e-6: it drops the incomplete last cycle. The arbiter's own reson deck logs a non-convergence note. | ✓ |
| **H3** G0 (Cx 100 nF ≥ 100× node C, Lx→0) | z = 1.4123 (a) / 1.4124 (b) against 1.3907. Δ = 0.022 ≤ 0.03 | ✓ |
| **H4** z_G1/z_G0 against the shuttle z(471)/z(galv) | 0.9982 (a) / 0.9983 (b) against 0.9736 (frozen shuttle at the G3 caps, pCboss2 6 pF). Δ = 0.025 ≤ 0.03 | ✓ (narrow) |
| **H5** Cpar 20 → 10 pF | Δz_G0 = +0.0946 against solve_doubler4's +0.0678. Δ = 0.027 ≤ 0.03 | ✓ (narrow) |
| **H6** conservation < 1 %; +5 % gap-term trip > 4 % | residual (normalised to E_gap) 0.08 / 0.09 / 0.35 / 0.35 / 0.83 / 0.92 % (G0a, G0b, G1a, G1b, R1a, R1b); trip 5.05–5.88 % | ✓ |
| **H7** KCL fire | node-3 side = stray side to 1e-8 relative (R1a, R1b, R2a, R2b) | ✓ |
| R0 `deck('reson', lxfwd=1e-3)` | **not observable.** The frozen arbiter deck aborts at 12 µs ("Timestep too small", `c1v_int1`) at every allowed `ms` (1e-6 … 5e-8). At 0.1 mH, the top of the published sweep, it also aborts; its partial trace gives z = 1.216, not the published ≈ 1.39. | finding |
| R1 | above | `SINK-PARTIAL` |
| R2 / G1m (motor in, real time) | R2: z 1.954 / 2.233, η 0.444 / 0.661 (reltol 1e-4/1e-5/1e-6 agree to 0.002). G1m: **not converged** (z 1.04 → 1.20 → 1.30 at reltol 1e-4/1e-5/1e-6; 1e-7 aborts) | `MOTOR-DEPENDENT` |
| T1 | C_BR share 0.6 % (R2a) / 0.2 % (R2b); t½ 0.687 µs against the model's 2.156 µs | `PREMISE-FAILS` |
| R4 | **not observable.** The frozen `sparkgap.sub` (SW + diode) stalls ngspice at the first armed strike (7.2°) at 15 kV seed, at reltol 1e-3/1e-4/1e-5 and maxstep 1e-6/1e-7 | modifier not assessed |
| R3 (optional) | not run | — |

`MOTOR-DEPENDENT` rests on the converged R2 against R1. With the motor in, η(R2a) = 0.444, which is
0.125 below η(R1a) = 0.569, far outside δ_η. R2 still beats G0 by +0.041 (a) and +0.26 (b). The motor
branches are six lossless 0.64 H + 440 nF series LCs, resonant at 299.9 Hz, the pump frequency. They
nearly kill the *direct* machine: G1m z ≈ 1.2–1.3 and not converged. With Lx, the machine stays at
z ≈ 1.95.

## 2. Model reproduction table

| quantity | ledger (a / b) | model | status |
|---|---|---|---|
| η(G0) | 0.403 / 0.403 | 0.386 | within δ_η (the tanh-tier offset, as z 1.412 vs 1.334) |
| η(G1) | 0.400 / 0.400 | 0.302 | **`LEDGER-MISMATCH`**: the direct island costs almost nothing over G0 on the drawn sheet, because its "tax" *is* the D3/D4 tax |
| η(R1) | 0.569 / 0.701 | ≈ 0.50 | the measured band replaces 0.50 |
| T_load/W(G1) | 0.498 | 0.217 | mismatch; see §VERDICT point 4 |
| load t½ | 0.687–0.690 µs | 2.156 µs (471 pF / 2.64 µF / 1 mH) | the predicted tell: the bank is not in the loop |

## 3. Sweeps (z / η; motor out unless noted)

| deck | (a) z | (a) η | (b) z | (b) η |
|---|---|---|---|---|
| Lx → 0 (G1) | 1.410 | 0.400 | 1.410 | 0.400 |
| Lx 10 µH | 1.841 | 0.534 | 1.982 | 0.615 |
| Lx 100 µH | 1.930 | 0.563 | 2.126 | 0.684 |
| Lx 1 mH (R1) | 1.950 | 0.569 | 2.160 | 0.701 |
| stray 0 pF: G1 / R1 | 1.442 / 2.216 | 0.361 / 0.620 | 1.442 / 2.421 | 0.361 / 0.783 |
| stray 20 pF: G1 / R1 | 1.323 / 1.541 | 0.501 / 0.558 | 1.324 / 1.737 | 0.501 / 0.636 |
| R1, ESR 2 Ω (not converged) | 2.040 | 0.575 | 2.212 | 0.743 |
| R1, ESR 0 = as drawn (not converged; ledger 5.3 % / 1.3 %) | 2.206 | 0.648 | 2.281 | 0.806 |
| R1, reltol 1e-5 twin | 1.947 | 0.568 | 2.156 | 0.699 |

f_rec,meas by stray setting is 0.48 / 0.78 at 0 pF, 0.34 / 0.60 at 5 pF, and 0.15 / 0.34 at 20 pF. In
every setting η(R1) > η(G0). So `SINK-PARTIAL` is stable across the stray sweep and across the ESR
choice.

## 4. T1 — load-stroke partner breakdown (R2a, reltol 1e-5, cycle 9)

The stroke window is SG3a1 conduction start → first current zero, plus one stroke of margin. That is
7.200° → 7.225°, or 1.4 µs. Charge is given as a share of the charge through Lx3 into node 3.

| node | partner | share |
|---|---|---|
| 3 | Cb1 | 0.584 |
| 3 | Cpar3 (→ ref → C1 chain) | 0.346 |
| 3 | SG2 stray | 0.035 |
| 3 | SG3b1/BS3 strays | 0.030 |
| 3 | **C_BR1–6 (the integrator's "bank")** | **0.006** |
| 4 (of what crossed Cb1) | Cpar4 | 0.308 |
| 4 | C2 (→ ref → C1) | 0.246 |
| 4 | SG4a1 stray → mirror island / Ca1 | 0.036 |
| 4 | L_B1–6 return | −0.006 |

Integrated over the whole 490 µs load *window*, C_BR shows 0.79. That figure is the motor branch's
own 300 Hz current, not the stroke (`island_asdrawn_t1.csv` carries both scopes). KCL at node 3
closes to 6e-5.

## 5. Conservation ledger and peak record (kept separate)

The conservation figures are in `island_asdrawn_ledger.csv`. It records, per steady cycle 8–11,
W_mech = −Σ∫½V²dC over C1, C2, Cx3 and Cx4; ΔE_stored = Σ½CV² + Σ½LI² over every element; and E_diss
per gap and per ESR. The residual is normalised to the gap term, which is the stricter choice
(E_gap ≤ E_diss); the E_diss-normalised figure is also given.

R1a partition: load gaps 0.146, coil ESR 0.204, rail gaps 0.068, fire/backstop gaps 0.016, stored
0.569.

G1a partition: load gaps 0.498, fire 0.054, rail 0.049, stored 0.400.

The peak record is in `island_asdrawn_peaks.csv`: i_pk and V_pk per gap, plus the load t½. The decks
are scale-free (100 V seed, growing at z per cycle), so absolute peaks are meaningless and only
ratios are reported. No peak quantity enters the ledger.

## 6. Locked inputs and every deviation (recorded before the verdict runs)

- **Topology.** `topology_edge_list.csv` node-exact, 43 parts; the self-test asserts 43. R-A = R-B =
  reference (collapsed tank). R1/G1 remove the 24 motor parts, as declared; R2/G1m restore them.
- **Strays.** Cpar 20 pF on nodes 1–4. gap_stray 2 pF across all 8 gaps. Boss pCboss 6 + pCboss2
  6 pF ∥ Cx3/Cx4; pCboss2 is on because the backstops are drawn. Nodes 7/8/n17/n23 → ref at
  {0, **5**, 20} pF.
- **Values.** C1/C2 = 16–280 pF on the arbiter's tanh(12·sin) at 300 Hz. **Phase `[IR]`:** C1 is
  high over [0°, 30°), as in shuttle `caps_phase('A')` and the arbiter. The drawn discs
  (`geom_profiles.csv`) actually sweep C1 *linearly* over 0–30°; the brief locks tanh. Ca1 = Cb1 =
  309 pF. Cx3/Cx4 are sampled from frozen `shuttle_core.profiles` at 471 / 60 pF on a 0.1° grid.
  The motor is 0.64 H + 440 nF, lossless as drawn.
- **Clock.** θ = ωt at 3000 rpm, 300 Hz. Stations are parsed from `spice/timing.sub`. **Windows
  `[IR]`:** each gap arms at its DXF station. SG1/SG2, SG3b1/SG4b1 and BS3/BS4 stay armed to 27° /
  57°. SG3a1/SG4a1 disarm at the fire station (16.05° / 46.05°).
- **Reported finding (DXF vs shuttle).** SG3b at 16.05° sits 0.45° into the shuttle collapse
  window (15.6–26.4°), where Cx has collapsed by about 0.4 %. The fire therefore happens at a
  boost of ≈ 1, not the shuttle's emergent mid-collapse angle. BS3 at 19° sits *inside* the
  collapse, whereas the shuttle's backstop station is at 27.5°, after it. The DXF governs.
- **Gaps (behavioural, `spice/sparkgap_bidir.sub`).** One-way: I = arm/RON · ½(V + √(V² + VE²)).
  It quenches at current zero. RON = 2 Ω and VE = 1 mV. Bracket (a): I = V·arm/RON. The arming edge
  is 0.5 µs; ROFF = 1 GΩ.
- **Harness findings `[ME]`.** ngspice's SW + diode series and the `C … Q=` / B-`ddt` varicap forms
  both stall ("Timestep too small") at every armed dump in this network. The varicaps are therefore
  explicit charge integrators, V = Q/C(t). abstol is 1e-9 because currents reach kA as the
  scale-free pump grows about 200×.
- **Lx ESR 20 Ω `[IR]`.** This is the S2/integrator mid-band R (η_op 0.510 there). It is the coil's
  own loss, not a new path. Without it the ~3.6 MHz Lx/stray ring never damps and the runs don't
  converge.
- **Accuracy.** reltol 1e-4 at maxstep 1 µs. The 1e-5 twins agree to 0.004 in z and 0.001 in η.
  G0 gates use its 1e-5 twin, because the 100 nF Cx amplifies V error in the ledger.
- **Honesty note.** Development runs of R1 were seen while debugging the numerics, before R_LX and
  RELTOL were locked. Every alternative is tabulated in §3, and none changes the verdict class.

## 7. Named checks

1. H1–H7: all pass (§1). H4 and H5 pass narrowly.
2. Model reproduction: G0 matches. G1 is `LEDGER-MISMATCH`, and the verdict rests on R1 against G1,
   as §5.2 requires.
3. T1 premise: `PREMISE-FAILS`.
4. Lx sweep: §3.
5. Two-ledger separation: `ledger()` and `peaks()` read the raw traces independently.
6. Firewall: pure EE — KCL, LC, gap switching and varicap work only.
7. Frozen empty-diff: `frozen_diff()` against f9c9efa is **empty**. It covers `shuttle_core.py`,
   `reference/`, `sim/seq_stat_commutation.py`, `sim/design_synth.py`, `tools/`, `index.html`,
   `docs/kicad/`, `topology_edge_list.csv`, and every pre-existing `spice/*.sub`/`*.cir`.

## 8. Routed to TMD

- **D-ISLAND.** The verdict is not `SINK-REALIZED`, so the brief routes the island decision to TMD.
  The measured η 0.57–0.70 already beats the direct machine; "drop Lx" would *lose* it. What is
  missing is a downstream sink, not the gain.
- **Gap physics decides the band.** The (a)/(b) spread, 0.57 against 0.70, is the deionisation
  question. The gain itself needs step-closing gaps. A `[MEAS]` rung on real closure time and
  quench is what firms this up.
- **Motor match.** Six lossless 300 Hz branches cut η(R2a) to 0.44 and nearly stall the direct
  machine. The coils' real Q, and whether I7 intends the motor resonance at the pump frequency,
  need TMD's view.

## Deliverables

- `sim/island_asdrawn.py`: the deck builder, the gates, the campaign and `report()`, with on-load
  self-tests. Run it bare to run the campaign; `--report` re-derives everything from `spice/ia_raw/`.
- `spice/timing_asdrawn.sub`, `spice/sparkgap_bidir.sub`, and the generated decks `spice/ia_*.cir`.
- `island_asdrawn_runs.csv` (z/η per run), `island_asdrawn_t1.csv` (the T1 stroke ledger),
  `island_asdrawn_ledger.csv` (conservation) and `island_asdrawn_peaks.csv` (peaks), all kept
  separate.
- `island_asdrawn_traces.png`.

Pass B is gated on this verdict being committed, and is not started here.
