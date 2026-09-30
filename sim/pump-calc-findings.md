# Findings — PUMP-CALC (brief r0.1): the in-browser pump-action calculator for the drawn pump

**Branch** `claude/new-session-0az7f9`, built on 8cd181e (the r0.2 exact engine). **Not merged**: TMD
signs off.

## BUILD VERDICT: `PUMP-CALC-PARTIAL`

The motor-out calculator is **correct and fast**:

- The canaries K1–K4 pass (with K1 checked on two engines).
- All correctness gates pass: E0–E4, M1, P0, N, F, Z.
- P1 passes at 9.4 s in Pyodide.

The **motor-in machine fails M3 and M2**:

- **M3:** z moves by 0.022 between dθ and dθ/2, and the switching pattern never repeats.
- **M2:** the G1m residual misses 1e-9.

So the motor toggle ships as the brief's PARTIAL rule requires. When the motor is in, the page
re-runs the machine at dθ/2. It shows **"not converged"**, and never a number, unless both runs
converge and agree to 1e-3. P2 is also missed (101 s in Pyodide), for the same non-convergence.

E5 and E6 are reported, not graded. They carry four findings for TMD (§4).

| gate | result | status |
|---|---|---|
| **K1** always-armed galvanic z (engine and JS `solveDoubler4`) | engine 1.3340016137, JS 1.3340016137, solve_doubler4 1.3340016137 | **PASS** (1e-6) |
| **K2** station-armed galvanic z | 1.5225272176 | **PASS** (1e-6) |
| **K3** direct island on the shuttle schedule = shuttle_core | 1.2983502589216 | **PASS** (1e-9) |
| **K4** S2 ring, R = 2 Ω | t½ 2.2214426 µs, V_bank 998.890013 V | **PASS** (0.01 %) |
| **E0** regression vs `island_asdrawn.py` @ 8cd181e ('r02' arming) | H1 (3 × t½, 3 × V_bank), H3 (4 arms), H4, G1 and R1b at the §1 settings: max rel **9.5e-14** (R1b against a live r0.2 run). The §1 anchors: G1 **1.2559910201** (brief 1.255991), R1b **1.3542609005** (brief 1.354261) | **PASS** (1e-9) |
| **E1** numpy expm vs scipy | 4000 ring matrices from 6 gate configurations (motor in/out, Pass A config, S2), 1-norm up to 1.3e6: max rel **7.9e-16** | **PASS** (1e-12) |
| **E2** gap-model limits | (a) M-SR with holdoff off and I_hold 1.5 against M-OW: rel **2.6e-15**. (b) M-RD(→0) with every gap in ring-down: \|z_R − z_G\| = **4e-13**. The per-class table is in §4.3 | **PASS** |
| **E3** no chop | 11 configurations, every extinction at \|i\| ≤ **6.0e-5** of the event's i_pk1 | **PASS** (1e-3) |
| **E4** conservation, 3 terms | per-cycle residual ≤ **2.9e-13** of W on all 11. +5 % on E_diss moves it by exactly −0.05 E_diss/W (≤ 1e-12) and trips the guard | **PASS** (1e-9) |
| **M1** motor branch (0.64 H, 440 nF, 40 Ω) vs analytic | current **2.9e-15**, energy **6.7e-15** | **PASS** (1e-6) |
| **M2** motor-in conservation | R1m per-branch **1.4e-10**, per-coil **7.2e-10**. G1m: **0.18** on the recorded cycle, which is not converged (see below); the plain iteration gives 1.0–1.3e-9 | **FAIL** (G1m) |
| **M3** motor-in convergence | R1m z 2.00224 (dθ) against 1.98011 (dθ/2): Δ **0.022**. Ring step 48 against 96: Δ 3.6e-10. The pattern never repeats (not converged). G1m: \|λ\|max = 1 ± 2e-7 (near-neutral DC-block modes; no pump mode) | **FAIL** → "not converged" |
| **P0** z_monodromy = z_iterated | core station/always, G1, G0, R1 valve, R1 M-RD 0.5, R1 M-SR limit: max rel **4.1e-14** (38–60 iterated cycles) | **PASS** (1e-9) |
| **P1** standard evaluation, twins included | **Pyodide 9.38 s** (Node 22, the local Pyodide 0.26.2 + numpy 1.26.4, peak RSS 256 MB); CPython 4.2 s; headless Chromium page ≈ 9–10 s | **PASS** (≤ 10 s) |
| **P2** motor-in | Pyodide **101 s**, CPython 43 s (the main machine; not converged) | **MISSED** |
| **N** numpy 1.26.4 vs 2.4.6 | self-test and canaries pass under both; z / canary values agree to **≤ 1.1e-14** | **PASS** |
| **F** firewall | pure EE: numpy + the frozen EE cores (design_synth lazily, for the lamps); no subprocess, git or file writes on the import path | **PASS** |
| **Z** frozen empty-diff vs 8cd181e | the brief-§0 list (`shuttle_core.py`, `reference/`, the Pass A/A′ record, every committed `spice/` file, `index.html`, `tools/charge-pump-synth-live.html`, `tools/schematic.svg`, …) plus the working tree: **empty** | **PASS** |

**On M2 for G1m.** The motor-in G1m machine has no growing mode: its largest non-invariant \|λ\| is
1 ± 2e-7, from the motor DC-block charge modes. Its monodromy therefore never converges. The
recorded display cycle then starts from an eigenvector estimate that is inconsistent with the held
switch set, which is where the 0.18 comes from. The plain iteration of the same machine closes at
1.0–1.3e-9. That is the conditioning floor of ½VᵀKV with 2.64 µF block caps beside 5 pF strays
(cond ≈ 5×10⁵; every single operation is within 5e-11). Either way the page shows no number.

## 1. The engine (`sim/pump_engine.py`)

The engine is the r0.2 exact event-driven KCL solver, re-derived under E0. The changes, each gated:

- **numpy only.**
  - Padé(13) scaling-and-squaring expm, on a **power-of-two balanced** matrix. Unbalanced, the
    ring matrices (cluster charges ~1e-9 C beside currents ~1 A) lose 2e-8. Balanced, they agree
    with scipy and a 50-digit reference to 1e-16 (E1).
  - Van Loan block exponentials give the exact ∫i² and ∫i of a continuous-mode motor step (M1).
- **Speed, with the same algebra and decisions.**
  - K is cached per phase, cluster/flow/solve matrices per edge set.
  - The ring is advanced in chunks from one expm per topology.
  - Switching instants are root-found (Illinois on each triggered margin) and confirmed on the
    exact state.
  - Relative to r0.2, R1b goes from ~6 s to ~0.7 s per cycle.
- **Gap models per class (rail / load / fire / backstop)** [IR], with the Pass A′ semantics:
  - **M-OW (valve):** optionally latched. Fire and backstop latch by default, as in r0.2 bracket b.
  - **Sustained arc.**
  - **M-RD:** a lit gap extinguishes at the current zero ending the first half-cycle whose peak is
    below I_hold × i_pk1, where i_pk1 excludes the first 50 ns. After that it is a forward rectifier.
  - **M-SR:** as M-RD, plus a 10 µs holdoff with re-ignition in either direction while
    \|V\| > ρ(t)\|V_f\|.
  - An arc lit by an earlier event behaves as r0.2's arc. A lit gap still ringing at 50 µs of
    frozen-C ring goes to its exact ring-down limit [IR].
- **No chop** [IR, the Pass A′ H2 lesson]. In robust mode a ring ends at the drive zero only once
  every held valve is at its own zero; before that it coasts. Otherwise r0.2's relaxation would open
  valves carrying up to 2e-3 of the transfer peak (E3 would fail). The effect on z is 3e-11.
- **Robust (phase-exact) arming is the default** (§4.1). `arming='r02'` reproduces r0.2 bit for bit
  for E0.
- **z by monodromy** [ME]:
  1. Tape the cycle's linear map.
  2. Jump to the dominant eigenvector, excluding exact invariants (|λ − 1| < 1e-9, e.g. motor
     DC-block charge).
  3. Re-tape until the switching pattern repeats and |Δz| ≤ 1e-12.

  The final taped cycle starts on the eigen-state, so it is also the steady waveform. η at every
  cut comes from it: η(cut) = (z² − 1) E(cut) / [W(cut → 60) + z² W(0 → cut)].
- **TRV** comes from an open-circuit probe at the gap's current zero [ME]: 3 µs of free evolution
  with every other switch frozen, reverse peak ÷ V_f.

## 2. Canary values (the page's fail-closed set)

K1 1.3340016136696 · K2 1.5225272175521 · K3 1.2983502589216 · K4 2.2214426 µs / 998.8900132 V,
plus K1 on the JS side (`solveDoubler4`, copied from `index.html`) 1.3340016136696.

## 3. Measured times

| step | CPython 3.11 / numpy 2.4.6 | Pyodide 0.26.2 / numpy 1.26.4 (Node 22) |
|---|---|---|
| boot (Pyodide + numpy + files) | — | 2.2–5.1 s |
| canaries K1–K4 | 0.7 s | 1.4–1.6 s |
| standard evaluation (R1 valve + G + G0) | 4.2 s | **9.4 s** |
| G1 alone / G0 alone | 0.6 / 0.5 s | ~1.2 s each |
| motor-in main (not converged, 12 taped cycles) | 43 s | 101 s |
| full gate suite | ~40 min | — |

The page itself was exercised in headless Chromium (Playwright, Pyodide served locally). It showed:

- the badge `ENGINE: live · canaries K1–K4 pass`;
- R1 z = 1.6251534218 (PUMPS), with the result in ≈ 9–10 s;
- presets that load and pass their `expect` blocks (K2, K3, G1);
- a sweep that runs;
- the schematic stamp **MATCH (43 drawn = 43 mapped = 43 netlist)**;
- **no console errors**.

## 4. Findings for TMD

### 4.1 The §1 anchors were measured with C1/C2 at shuttle_core's defaults, not the canary

`build_drawn`'s C1/C2 profiles read shuttle_core's module scalars and need `canary_caps()` active,
as its docstring says. The brief's §1 runs did not activate it. So the anchors G1 = **1.255991** and
R1b = **1.354261** are the drawn pump with **C1/C2 160–1000 pF** alongside Ca 309 / Cpar 20 pF
(reproduced to 1e-13). At the canary caps (C1/C2 16–280 pF) the same machines give:

| machine | z at canary caps |
|---|---|
| G1 | 1.3451286534 (r0.2 arming); 1.3451489341 (robust) |
| R1b | 1.6251534218 (robust; not run under r0.2 arming) |

The core anchor (1.5225272) is unaffected. The brief's "islands cost 0.27 in z against the bare
core" rests on the mixed configuration. At the canary caps, G1 costs 0.177 and **R1b (valve) gains
+0.103** over the bare core.

### 4.2 r0.2's arming test is cycle-dependent

`a <= θ % 60 < b` is evaluated on θ = 60k + p. In floating point, SG3a1 / SG4a1 / SG3b1 / SG4b1
therefore arm **one grid step (0.05°) late** in most cycles after the first few (for example,
76.05 % 60 = 16.049999999999997). The core's C1/C2 step at 30° has the same fragility. The engine's
robust mode tests the phase exactly:

| machine | r0.2 (late arming) | robust | Δ |
|---|---|---|---|
| G1 at the §1 caps | 1.2559910 | 1.2560019 | +1.1e-5 |
| R1b at the §1 caps | 1.3542609 | 1.3543107 | +5e-5 |

The robust values are the calculator's.

### 4.3 The linear-circuit ring-down theorem needs every gap in ring-down

With every gap class in M-RD(→0), z_R = z_G to 4e-13 (E2b). With the load gap alone in M-RD(→0),
the other classes' valves rectify the ring:

| load M-RD(→0), others | z_R − z_G |
|---|---|
| rail valve, fire valve (latched) | **+0.0754** |
| rail arc, fire valve | +0.0049 |
| rail valve, fire M-RD(→0) | −0.0004 |
| all M-RD(→0) | 0.0000 |

The gain needs the one-way fire valve *and* the one-way rail valve.

### 4.4 R1 is first-order in dθ; motor-in is not converged

z(R1 valve) runs 1.624461 / 1.625153 / 1.625497 / 1.625668 at dθ 0.1 / 0.05 / 0.025 / 0.0125°.
That is first order: the error at the locked 0.05° is about 7e-4. The cause is the quasi-static load
current being quantised into grid-step micro-rings (about 190 per cycle). G1 does not depend on dθ
(1e-13).

The motor branches resonate at the 300 Hz pump frequency. That leaves near-neutral DC-block modes
(\|λ\| within 2e-7 of 1) and dθ-dependent switching:

- R1m is 2.002 at dθ and 1.980 at dθ/2;
- G1m has no pump mode above them.

**Neither is certifiable**, which is the G1m lesson again. A continuous-time motor integration
(events located inside the motor step), rather than frozen-C steps, is the likely cure. That is out
of this build.

### 4.5 E5 — engine reconciliation at the Pass A ngspice configuration (report-only)

The Pass A configuration: tanh C1/C2 (k 12), cx_min 60, pCboss2 6, R_LX 20 Ω, windows to 27°.

| machine | exact engine z / η(cut 0) | ngspice z / η | Δz |
|---|---|---|---|
| G1a (Lx → 0, bracket a) | 1.3614 / 0.409 | 1.4098 / 0.400 | −0.048 |
| R1a (Lx 1 mH, bracket a) | 2.0020 / 0.590 | 1.9501 / 0.569 | +0.052 |
| R1b (Lx 1 mH, bracket b) | 2.2258 / 0.729 | 2.1598 / 0.701 | +0.066 |
| R1 M-RD(→0), bracket a | 1.3666 / 0.407 | 1.4141 / 0.398 | −0.048 |
| G1 M-RD(→0), bracket a | 1.3604 / 0.409 | 1.4098 / 0.400 | −0.049 |

Attribution, changing one ingredient at a time from the Pass A config (R1b, bracket b):

| change | z |
|---|---|
| none (Pass A config) | 2.2258 |
| shuttle raised-cosine profile | **1.4221** |
| cx_min 8 / pCboss2 0 | 2.5119 |
| R_LX 2 Ω | 2.2360 |
| windows to 30° | 2.2258 |
| dθ/2 | 2.2258 |
| the r0.2 settings | 1.6252 |

The differences are **material**:

- **An offset common to all twins.** All five machines are off by about ±0.05. The G twins sit
  −0.048 below ngspice, so the offset is common to the twins and comes from the tier. The ngspice
  harness has gap RON 2 Ω and 0.5 µs PWL arming edges, i.e. continuous-time conduction (the xsim T3
  effect). The exact engine closes instantaneously.
- **The C1/C2 schedule dominates the level.** The tanh schedule against the shuttle raised-cosine
  moves R1b from 2.23 to 1.42.

So **yes, the Pass A′ grade needs the exact-engine replay** (E6), and the schedule is a design input
that must be fixed first.

### 4.6 E6 — the Pass A′ ladder on the exact engine (report-only)

δ_z = δ_η = 0.005 (the dθ-twin rule, with the floor binding). f_rec,model is 0.996 (2 Ω) / 0.958 (20 Ω).

| model | default config: z_R / z_G, class | Pass A config: z_R / z_G, class | Pass A′ class |
|---|---|---|---|
| M-OW | 1.6252 / 1.3451, SINK-PARTIAL | 2.2258 / 1.3614, SINK-PARTIAL | SINK-PARTIAL ✓ |
| M-RD I_hold → 0, 0.1 | 1.4110 / 1.3356, SINK-PARTIAL | 1.4081 / 1.3604, SINK-PARTIAL | SINK-IS-PUMP ✗ |
| M-RD I_hold 0.3, 0.5 | 1.4110 / 1.3356, SINK-PARTIAL | 1.4081 / 1.3604, SINK-PARTIAL | SINK-PARTIAL ✓ |
| M-RD I_hold 0.7 | 1.4110 / 1.3356, SINK-PARTIAL | **1.9236** / 1.3604, SINK-PARTIAL | SINK-PARTIAL ✓ |
| M-SR t_rec 0, 0.1 µs (I_hold 0.3–0.7) | 1.4110, SINK-PARTIAL | 1.4081; 1.9236 at t_rec 0 with I_hold 0.7; SINK-PARTIAL | SINK-PARTIAL ✓ |
| M-SR t_rec 1 µs | 1.4110, SINK-PARTIAL | 1.4081, SINK-PARTIAL | PUMP-BREAKS ✗ |

**Reading.** On the exact engine the lit load arc is a high-Q ring. At R_LX 2 Ω its half-cycle
peaks fall only about 0.1 % per half-cycle, so it **never meets any I_hold < 0.95 within the ring**.
Every M-RD and M-SR point then collapses onto the M-RD(→0) machine. That machine still gains over its
G twin (SINK-PARTIAL) through the fire-valve + rail-valve rectification of §4.3.

Only at 20 Ω with I_hold 0.7 does the arc go out, and then M-SR with t_rec 1 µs re-ignites it (1.924
→ 1.408): the Pass A′ recovery mechanism, reproduced. So:

- the `CONDITIONAL-ON-RECOVERY` structure holds only where the arc actually extinguishes;
- the ladder's gain at small I_hold comes from the one-way fire and rail models, not the load gap.

**That class disagreement is for TMD (D-GAPDEFAULT).** It is not a harness failure.

## 5. Reuse ledger (all copied into new files with attribution; nothing edited in place)

| from (@ 8cd181e) | what | into | how |
|---|---|---|---|
| `sim/island_asdrawn.py` | Net, `_clusters`/`_P`/`csolve`/`edge_flows`/`event_loss`/`lcp`, Ring, Sim (stroke/event/fire/ring/relax/motor_step), run_machine, doubler_net, s2_net, `_shuttle_net`/shuttle_parity | `sim/pump_engine.py` | derived under E0 (compat arming reproduces it to ≤ 1e-13) |
| `sim/island_gapbracket.py` | M-RD / M-SR rule logic (derive_event, resolve_chain), constants H_TO_ZERO, T_SPIKE, HOLDOFF; `classify` | `pump_engine.py`, `pump_engine_gates.py` (E6) | ported into the event engine; ngspice parts dropped |
| `xsim_queiroz_matrix.py` | `_cycle_map`/`_dominant` (the closed-cycle eigenvalue) | `pump_engine.monodromy` | pattern |
| `index.html` | `solveLinear`, `chargesFromVoltages`, `solvePhase`, `solveDoubler4` | `tools/pump-calc.html` (between `BEGIN/END solveDoubler4`) | copied unmodified; K1's JS side and the instant preview |
| `index.html` | VERIFY/runSelfTest/renderSelfTest; FIELDS/state/bindField/loadFromHash/writeHash/clampField/syncFieldInputs; scheduleRecompute; clearCanvas/drawAxes/niceBar/fmt; findCriticalCa; applyParamPresetTo/evalExpect | `tools/pump-calc.html` | pattern / adapted |
| `index.html` | Block S (drawSeqV/Logic/Clock), drawCommutatorAxial | `tools/pump-calc.html` (timeline, station clock) | adapted to the 8 drawn gaps and the DXF station table |
| `tools/charge-pump-synth-live.html` | Pyodide boot (CDN v0.26.2, numpy, real repo files into the FS), badge states, REF_MAP / sv_ slots / consistency stamp | `tools/pump-calc.worker.js`, `tools/pump-calc.html` | copied / adapted; tank greyed "collapsed", motor greyed when off |
| `sim/pyodide_parity.py`, `run_pyodide_parity.sh` | the two-numpy parity pattern | `sim/pump_engine_parity.py`, gate N | pattern |
| `sim/design_synth.py` | `Cmax_from_geom`, `overlap_deg`, `Z_BAND`, `CPAR_FLOOR_pF`, `T_STRIKE_S`, `T_COND_S` | `pump_engine.lamps`, `make_config` | imported, not copied |
| **dropped** | plate engine, transferCaps, resonatorCore / tank, torque-motor and mechanics panels | — | out of scope (brief §2) |

## 6. TMD-gated (not picked)

- **D-CUT:** the page shows the η(cut) band only.
- **D-GAPDEFAULT:** the page loads with M-OW (valve) and the TRV flag visible. The suggested
  M-RD(→0) load+fire default is one preset away (`default-drawn-R1-ringdown`, z 1.32557 / G 1.32592).
- **D-SCALE:** the default is load-gap V_f = V_strike (20 kV).
- **D-GOVERNOR, D-CANARY.**

## Deliverables

- `sim/pump_engine.py`, `sim/pump_engine_gates.py`, `sim/pump_engine_parity.py`
- `tools/pump-calc.html`, `tools/pump-calc.worker.js`, `tools/pump-calc-README.md`
- `presets/pump/*.json` (7, each with `expect`)
- this document
- the changelog entry
