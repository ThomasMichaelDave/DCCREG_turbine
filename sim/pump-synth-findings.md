# PUMP-SYNTH — findings (brief r0.1, with pump-calc r0.2 incorporated)

**Verdict: `PUMP-SYNTH-LIVE`.** Every check passes, and P1 is met with the parallel strip. SYNTH-SCAN-ONLY does not apply, because H-SYN2 is monotone.

- Branch `claude/new-session-0az7f9`. Not merged: TMD signs off.
- Frozen files show an empty diff vs 8cd181e (gate Z).
- The engine `sim/pump_engine.py` is byte-identical to the pump-calc head a5420b7 (gate ENG). Its E0–E6, M1–M3, P0, N and F results therefore carry over from `sim/pump-calc-findings.md`.
- The gate record is `sim/pump_synth_gates.json`, produced by `python3 sim/pump_synth_gates.py`.

**Brief discrepancy.** The hybrid brief says "pump-calc is not yet built on any branch, verified at 8cd181e". On this branch it *is* built (`PUMP-CALC-PARTIAL`, commits 7ca54f0…a5420b7). PUMP-SYNTH is built on top of it rather than from scratch, so the "new" engine modules listed in brief §0 are the pump-calc ones, reused unchanged.

## 1. Check table

| check | result | value |
|---|---|---|
| K (K1–K4 + on-load self-tests) | PASS | K1 1.334001614, K2 1.522527218, K3 1.2983502589, K4 2.22144 µs / 998.890 V; engine, sizing, synth and JS self-tests all pass |
| ENG (engine unchanged since pump-calc) | PASS | `git diff a5420b7 -- sim/pump_engine.py` is empty |
| S1 forward law | PASS | active-only 279.6407 pF (= `design_synth.Cmax_from_geom`); with the ring 295.640 pF (A_ring 0.012651 m², R25–R68.2, C_min 16.00 pF); default 7 mm moist air (20 °C, 1013 hPa, 50 % RH) 279.819 pF |
| S1b JS = Python | PASS | 200 random plate inputs, worst relative difference **0** (rule strings identical) |
| S2 ladder vs guide §6.1 | PASS | Ca 307.6 pF (−0.45 %), Cx 469.8 pF (−0.26 %), C_blk 439.76 nF (−0.05 %), all within ±0.5 % |
| S3 C_blk | PASS | 439.76 nF at 300 Hz, 0.64 H |
| S4 homogeneity | PASS | every C × k with Lx / k and R_lx / k: \|Δz\| ≤ 1.6e-13 (k = 0.37, 3.7). **C-only: 1.8e-9 / 4.3e-9** — see §5.1 |
| S5 small plate | PASS | ⌀ 300 mm (C_max 9.8 pF): bare core **silent, z = 1**; drawn pump z = 1 (neutral). Drawn-pump minimum plate: **r_out 245.4 mm, ⌀ 623 mm** (C_max 101.8 pF), bracket [244.8, 245.4] mm |
| H-GEOM | PASS | C_max = `Cmax_from_geom` to 1e-9; rotor ⌀ 982.98 mm |
| H-SYN0 size invariance | PASS | (r_out, g_v) = (387, 7.000), (330, 4.967), (450, 9.623) at the same C_max: \|Δz\| ≤ 1.1e-13 |
| H-SYN1 search vs scan | PASS | found r_out 331.10 mm; the 15-point scan crossing (linear) 330.98 mm, inside the scan bracket [325.4, 362.1]; difference 0.12 mm ≤ 1 mm + 0.51 mm interpolation bound |
| H-SYN2 monotone | PASS | z non-decreasing in C_max on every searched point |
| H-SYN3 Solve re-run | PASS | min_diameter re-run z 1.20092 ≥ 1.20 and feasible; max_margin and max_rpm confirming runs converged |
| W0 warm = cold | PASS | \|Δz\| ≤ 9e-15 on 3 machines |
| M0 marginal resolution | PASS | 245 mm: neutral, decay 0.96552 per cycle (plain iteration 0.96557); 250 mm: retried monodromy 1.0104172794 = plain iteration to 3e-14 |
| H-UI | PASS | none of η_op, "0.50", "0.70", "validated machine" or "island sink" in the page, worker or JS sizing source |
| H-STAMP | PASS | 43 drawn = 43 mapped = 43 netlist |
| P1 headline + strip ≤ 10 s (Pyodide) | PASS | 4 Pyodide instances in parallel (Node, 4 cores): **8.2 s cold, 4.2 s warm** (31.3 s and 15.0 s serial). Headless Chromium on the page: 8.2–8.8 s with 3 helpers |
| Z frozen | PASS | empty diff vs 8cd181e |

The slow gates and P1 ran on c782941. After that, b30ab16 only restricted warm starts to pumping orbits, which does not change a pumping run. The fast gates, W0, M0, S5 and H-SYN were re-run on the final code.

**Browser smoke test** (headless Chromium, local Pyodide 0.26.2):
- badge live in 5–6 s;
- PUMPS: YES at z 1.3255;
- strip M-OW 1.6235 / M-RD(→0) 1.3255 / M-SR(0.1 µs) 1.3255 / M-SR(1 µs) 1.3255;
- stamp MATCH;
- no console errors.

## 2. The freeze settings, and min_diameter

These are the shipped defaults: R95–R387, 7 mm air, 12/6, D-CMIN active + 16 pF, Ca 1.10, Cx 1.68, fixed floors, load + fire M-RD(→0), motor off.

- **z = 1.3254745317, PUMPS: YES.** Every evaluated invariant holds, and I3 sits in its band.
- **Named blocker:** I4 insulate-first, by least slack. The rotor gap of 7.00 mm sits exactly at V_ceil / E_bd = 21 kV / 3 kV/mm. **I4 is provisional (D-MEDIUM)**, and the 3 kV/mm air figure is [RH].
- **Twins:** G (Lx shorted) 1.325827, Δz −0.00035. G0 (station valves) 1.439607, Δz −0.114.
- **Strip:** M-OW 1.6235. Both M-SR rows collapse onto M-RD(→0), as in pump-calc E6: at 2 Ω the lit arc never falls to 0.3 i_pk1 before its ring ends.

**min_diameter (m = 0.20).** The answer is **r_out 331.1 mm → rotor ⌀ 841 mm**:
- z 1.20092 on the exact re-run;
- g_v 7.00 mm from the insulation law;
- **binding item:** the z margin itself (z ≥ 1 + m). At that size I4 is at zero slack (g_v at the law value by construction), I9 has rim 132 m/s against 200 (slack 0.34), and I11 has overlap 2.42° against 2.95° (slack 0.18).
- The search used 6 exact runs.

**H-SYN1 scan** (15 points; r_out mm → C_max pF → z):

| r_out | 105.0 | 141.7 | 178.5 | 215.2 | 251.9 | 288.6 | 325.4 | 362.1 | 398.8 | 435.6 | 472.3 | 509.0 | 545.7 | 582.5 | 619.2 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| C_max | 4.0 | 22.0 | 45.4 | 74.1 | 108.2 | 147.7 | 192.5 | 242.7 | 298.3 | 359.2 | 425.5 | 497.2 | 574.2 | 656.6 | 744.3 |
| z | 1 | 1 | 1 | 1 | 1.01468 | 1.09165 | 1.18689 | 1.27272 | 1.34904 | 1.41640 | 1.47559 | 1.52752 | 1.57307 | 1.61307 | 1.64827 |

z = 1 at and below r_out 215 mm means no growing mode (§5.2). The pump starts pumping at r_out ≈ 245 mm.

**Other objectives:**
- **max_margin at ⌀ ≤ 983 mm:** r_out 387.0 mm, z 1.32549.
- **max_margin with the Ca golden-section search:** the engine's **z-optimal Ca is 0.63 × C_max (z 1.3450)**, against the ladder's 1.10 × C_max (z 1.3255). This is a D-CA input for TMD; the tool reports it and does not change the default.
- **max_rpm:** **3885 rpm, bound by I9.** The rim reaches 200 m/s at R491. I12 would allow about 142 000 rpm, with ring t½ 0.33 µs against a 115 µs overlap. The confirming exact run gives z 1.32547.

## 3. Measured times

| task | CPython (this container) | Pyodide 0.26.2 (Node, 1 instance) |
|---|---|---|
| headline evaluation (full observables) | 3.0 s cold, 1.7 s warm | 6.7 s cold, 3.5 s warm |
| headline + strip | 9.6 s serial | 23.6 s serial; **8.2 s / 4.2 s parallel** (4 instances) |
| twins (G, G0) | ≈ 1 s | ≈ 2 s |
| min_diameter | 39 s (6 runs) | 92 s (6 runs) |
| max_margin / with Ca search | 4 s / 24 s | 5.4 s / 48 s |
| max_rpm | 4 s | 8.7 s |
| min_plate (smallest pumping rotor) | 250 s in the gate (11 runs, 4 of them below threshold) | **509 s** (11 runs) — on-demand button only |
| one non-pumping point (z = 1 resolution) | 25–50 s | ≈ 2× |

The non-pumping points are the slow ones. The engine's own monodromy is tried first (12 cycles). Then the plain iteration must show the growth excess decaying geometrically to 0, which takes 40–140 cycles near threshold (§5.2). Searches that only cross the pumping side (min_diameter at m = 0.20, max_rpm, max_margin) are fast. min_plate, and critical values on the non-pumping side, are slow but exact.

## 4. Reuse ledger

| from | at | what | how |
|---|---|---|---|
| `tools/charge-pump-synth-live.html` | 8cd181e | CSS tokens and dark theme; slider rows (label + live value + range); SOLVER badge states (booting / live / CANARY-FAIL / down); objective select + Solve; lamp rows with the binding highlight and named-blocker line; reference drawer (overlay, schematic slot, stamp, legend, cross-section, lightbox, `mdToHtml`); the `REF_MAP` → `sv_<REF>` pattern and consistency stamp; `drawRotor`; reset to anchor | copied, then adapted: wedges from N_sec/n_kept, the ring, the gap radius, `REF_MAP` re-bound to the ladder |
| `tools/pump-calc.html` | a5420b7 (this branch) | `solveDoubler4` block (itself `index.html` @ 8cd181e, unmodified); chart helpers (`clearCanvas` / `drawAxes` / `niceBar` / `fmt` / `lines`); boot (`file://` detection, Blob worker, watchdog); `request`/`onWorker`; the canary table; waveform / timeline / η(cut) / event-table renderers; sweep; preset + `expect` pattern; the 43-ref `REF_MAP` grouping (tank collapsed, motor greyed) | `solveDoubler4` and the chart helpers are spliced verbatim; the rest is adapted |
| `tools/pump-calc.worker.js` | a5420b7 | Pyodide boot path, `REPO_FILES` fetch-into-FS | copied, then extended: `pump_sizing`/`pump_synth`, the main and helper roles, H-GEOM |
| `index.html` | 8cd181e | Block C-I plate engine (plateGeom / plateCaps / epsAir / epsRof); `cascadeState` (Ca = ratio·C_max); `FIELDS`/`state`/`bindField`/`scheduleRecompute`/URL-hash idiom; the `findCriticalCa` pattern | ported (`sim/pump_sizing.py` ↔ `tools/pump-sizing.js`); pattern reused |
| `sim/design_synth.py` | 8cd181e (frozen) | `Cmax_from_geom`, `BUS_MARGIN`, `Z_BAND`, `CPAR_FLOOR_pF`, `RIM_HARD`, `K_VAC`, `E_DIEL_DERATED`, `overlap_deg`, `T_STRIKE_S`, `T_COND_S`, the SG3b–BS3 spacing, the `_BLOCKER_PRIORITY` order and the `binding` least-slack fallback | imported unchanged |
| `sim/pump_engine.py` | a5420b7 | the exact engine, `canaries`, `lamps` (I11/I12/TRV), `summarize`, `scale_readouts` | imported unchanged |

**Dropped (D-LEDGER):**
- the shell parent's operating-efficiency card and its canary rung;
- the forbidden-path diagnostic and its FE-leakage slider;
- the default-pass invariants;
- `max_energy_density`.

`max_eta` (D-CUT) and `min_belt_power` (D-GOVERNOR) are shown disabled, with the reason.

## 5. Findings for TMD

1. **S4: the island ring time is the one non-capacitive scale.**
   - z is exactly homogeneous (1.6e-13) when Lx and R_lx are co-scaled with the capacitances (L/k, R/k).
   - With the C's alone scaled it moves by 4.3e-9, just outside the brief's 1e-9.
   - The gate is held on the impedance-consistent form, and the C-only number is reported. The statement "z depends only on capacitance ratios" is therefore true to about 5e-9 at Lx 1 mH, and exact for Lx → 0.
2. **Below threshold there is no z < 1, only "no growing mode".**
   - Under r_out ≈ 245 mm (default settings) the drawn pump does not decay. Its state converges onto the cycle map's **neutral mode** (λ = 1: charge trapped where no gap can dump it), or the gaps fall silent, as for the bare core at ⌀ 300 mm.
   - `pump_engine.dominant` excludes neutral modes by design (trapped DC on the motor DC-block caps). Below threshold its jump therefore lands on a decaying mode, and its monodromy never converges ("not converged" in pump-calc).
   - `sim/pump_synth.py` resolves this with exact plain cycles from the engine's standard seed:
     - (a) the growth excess decays geometrically to 0 (rate and Aitken bound reported): **z = 1, does not pump**;
     - (b) it settles above 1: a slow transient near threshold, and the engine's monodromy is retried from the settled state and converges (exact z);
     - (c) silent: z = 1.
   - Gate M0 checks both cases against the plain iteration.
   - **The threshold sits at r_out 245.4 mm (⌀ 623 mm, C_max 101.8 pF).** It is sharp: 1.00014 at 245.4 mm, 1.0104 at 250 mm.
3. **Multistability.** Below and near threshold, a machine started from a *different* state can stay on a non-pumping orbit where the standard seed pumps. Only pumping eigen-states seed warm starts, and a warm run is accepted only when it converges with z > 1. Otherwise the run is redone cold, so the standard seed defines z. This was found when a gate sequence reused a sub-threshold eigen-state.
4. **D-CA.** The engine's z-optimal Ca on the drawn pump is about 0.63 × C_max (z 1.345), not the ladder's 1.10 (z 1.3255). Under M-RD(→0), Ca has no z = 1 crossing within ×1/32…×32. **Cpar does: the critical Cpar is about 98–99 pF** (bracket 97.2–99.3 pF, run cap 14), so the 20 pF floor has about ×5 headroom.
5. **D-CPAR drives min_diameter, as the brief predicted.** Under *fixed* floors, the minimum pumping rotor is ⌀ 623 mm and the m = 0.20 rotor is ⌀ 841 mm. Under *scaled* strays, z becomes nearly size-independent (the fringe floor C_min stays at 16 pF under D-CMIN = active + fringe). The tool shows this when that mode is selected.
6. **I4 binds the freeze point by least slack.** That follows from the provisional air law (g_v = 21 kV / 3 kV/mm = 7.0 mm), not from the pump, and stays provisional until D-MEDIUM. Under the hard-vacuum law the insulation g_v is about 0.17 mm, and min_diameter would size against a different gap.
7. **The ring.** S1's "295.6 pF with the ring" needs A_ring 0.01265 m², which is R25–R**68.2** rather than R68 (0.012563 m², 295.5 pF). The default ring is set to R68.2.

## 6. Deliverables

- `tools/pump-synth.html`, `tools/pump-synth.worker.js`, `tools/pump-sizing.js` (the S1b JS mirror), `tools/pump-synth-reference.md`, `tools/pump-synth-README.md`
- `sim/pump_sizing.py`, `sim/pump_synth.py`, `sim/pump_synth_gates.py`, `sim/pump_synth_gates.json`
- `presets/pump/freeze-v010-plates.json`, `presets/pump/small-plate-probe.json`
- this file; `CHANGELOG.md`
