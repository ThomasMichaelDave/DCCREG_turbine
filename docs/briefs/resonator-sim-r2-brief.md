# Brief: resonator re-run at revised geometry — confirm 15 kV + clamp hold

> **For Claude Code.** Branch `resonator-sim-r2` off current head. Re-run of the standalone
> resonator model (`resonator_sim.py` from `resonator-sim`) at the **revised geometry** that closed
> the reach gap. Do **not** edit `shuttle_core.py`, `reference/doubler_core.py`, or `index.html`.
> Add a `CHANGELOG.md` entry. Branch left for TMD review; **not merged**.

| Field | Value |
|---|---|
| Branch | `resonator-sim-r2` |
| Status | r0.1 — second resonator run; geometry revised to close the 17× reach gap from `resonator-sim` r0.1 |
| Scope | varcap-machine only. Linear RLC transient + nonlinear clamp shunts. No DCCREG content (firewall). |
| Role | Claude Code re-parameterises and re-runs the tank+clamp model; owns git. Standalone module; reads pump drive as a parameter. |
| Predecessor | `resonator-sim` r0.1 returned **TANK-UNDERDRIVEN** (reached ~5 kV vs 20 kV, 17× short, no accumulation, island 88 pF ≪ tank 1477 pF). This run tests the geometry fix. |

## 0. Repository & session setup (fresh Claude Code session)

- **Repo:** `DCCREG_turbine` (the varcap-machine EE repo). Clone/pull before starting.
- **Branch point — important:** the predecessor model `resonator_sim.py` lives on the **`resonator-sim`
  branch, which was NOT merged to main.** Therefore: **branch `resonator-sim-r2` off `resonator-sim`**
  (to inherit `resonator_sim.py`), *not* off `main`. If `resonator-sim` is unavailable, recreate the
  2-state RLC+clamp ODE per §5 from scratch.
- **Frozen — never edit:** `reference/doubler_core.py`, `shuttle_core.py`, `index.html`, and existing
  presets. This run only adds/parameterises the standalone resonator module.
- **File locations:** simulation code under `sim/` (matching `sim/checks/`); findings markdown +
  CSV + PNG at the branch root or `sim/`; save **this brief** under `docs/briefs/` for the record.
- **Git:** Claude Code owns all git operations. Commit to `resonator-sim-r2`; **do not merge**;
  leave for TMD review. Add a `CHANGELOG.md` entry.
- **Firewall:** varcap-machine engineering only. No DCCREG theory content anywhere in code or docs.

## Revision history

| Rev | Date | Change |
|---|---|---|
| r0.1 | 2026-06-15 | Re-run at revised geometry: Cx grown 88→648 pF, C_R cut 1477→960 pF (8 mm garolite disc), conical tank L=79 µH (was mis-modelled as 169 µH cylindrical), target softened 20→15 kV. Question flips from "can it reach" to "confirm it settles at 15 kV and the clamp holds." |

## 1. Why this re-run

`resonator-sim` r0.1 proved the clamp architecture works but found the tank **underdriven** — a
capacitance mismatch (island ≪ tank) meant each kick reached only ~5 kV with no accumulation. Three
coordinated geometry changes were derived to close it; this run confirms they do, at a **softened
15 kV** target chosen for headroom. The single-kick energy balance predicts ~18.9 kV capability
(26% headroom over 15 kV), robust down to Q≈3 and Cx 37% below design — **this run verifies that
prediction in the full time-domain model and confirms the clamp holds 15 kV with the crowbar idle.**

## 2. Locked input — revised cap set

| Cap | r0.1 (old) | **r0.2 (this run)** | change |
|---|---|---|---|
| C1 / C2 | 16 / 280 pF | 16 / 280 pF | unchanged |
| **Cx3 / Cx4** | 4 / 88 pF | **8 / 648 pF** | r_out 232→350, gap 7.6→3 mm, +0.3 mm mica barrier per face |
| Ca / Cb | 309 pF | 309 pF | unchanged |
| **C_R** | 1477 pF | **960 pF** | 8 mm garolite 700 mm disc, rotor trimmed to r350 |

## 3. Locked input — the tank (corrected for the conical hub)

| Quantity | Value | Note |
|---|---|---|
| **L_R** | **79 µH** | 36-turn copper 3/1 mm capillary on the **bicone hub surface** (coil radius **28→76 mm**, widest at center, 108 mm axial / ~149 mm slant, ~12 m tube). **NB: the earlier 169 µH was a cylindrical mis-model** — the conical loop-sum (self + mutual at true per-turn radius) gives 79 µH. |
| **C_R** | 960 pF | revised (above) |
| **f₀** | **~579 kHz** | up from the mis-modelled 395 kHz; accepted (more ring cycles per commutation window) |
| **Q** | working ≈ 500; **sweep 320 / 500 / 900** | copper skin+proximity; pitch-dependent |
| **R_loss** | ωL/Q | series-equivalent |

## 4. Locked input — drive, target, clamp

- **Pump drive:** per-cycle energy to nodes 5–6. **Extract from the `geom-shuttle-gate` output** if
  available; else parameterise/sweep E_kick. Two modes to run:
  - **Full drive:** island delivers ~171 mJ/kick (boosted fire ~23 kV) → tank capability ~18.9 kV.
  - **Eased drive (recommended):** island ~115 mJ → tank ~15.5 kV (clamp barely works).
- **Fire timing:** G3 stations, PRF ≈ 300 Hz/branch at 3000 rpm (≈600 Hz combined kick rate). Kicks
  are short pulses that ring the tank (not DC steps).
- **Target:** **15 kV** (softened from 20). Energy to reach at C_R 960 pF = **108 mJ**.
- **Clamp:** two-tier — soft glow governor (threshold V_glow, **swept**) + hard crowbar
  (threshold ~15 kV, last-resort). On the 5–6 void. Track per-event + cumulative sink energy.

## 5. Model

Re-use the `resonator-sim` r0.1 ODE (2-state RLC + nonlinear clamp shunts), re-parameterised:

```
dV/dt   = ( I_inject(t) − I_L − I_clamp(V) ) / C_R       # C_R = 960 pF
dI_L/dt = ( V − R_loss·I_L ) / L_R                        # L_R = 79 uH
I_clamp(V) = I_glow(V; V_glow) + I_crowbar(V; ~15 kV)
```

- Max step ≤ ~100 ns (f₀ ~579 kHz → ~17 steps/period); run ≥ several PRF periods for steady state.
- **R0 self-test:** free ringdown matches analytic — f₀ = 579 kHz ± 1%, τ = 2Q/ω₀. Not trusted
  until R0 passes. (This also re-validates the corrected 79 µH against the analytic f₀.)

## 6. Campaign (strict order)

| step | run | gate |
|---|---|---|
| **R0** | free ringdown vs analytic (f₀ 579 kHz, τ) | authorises model + confirms conical L |
| **R1** | driven, **no clamp**, both drive modes, Q-sweep — confirm **peak reach ~18.9 kV (full) / ~15.5 kV (eased)**, single-kick (no accumulation expected at 600 Hz) | verifies the energy-balance prediction |
| **R2** | **glow governor only** — sweep V_glow near 15 kV; holds envelope? energy shaved/event? | governor at the new target |
| **R3** | **crowbar only** — threshold ~15 kV; fires ~never under nominal drive? per-event + cumulative dump | crowbar + sink sizing |
| **R4** | **two-tier combined**, both drive modes — **confirm tank settles ≤ 15 kV, governor does the work, crowbar idle**; report sink load (expect ~38 W full-drive, ~few W eased) | the integrated verdict |

## 7. Named checks (report each, pass/fail)

- **R0:** f₀ = 579 kHz and τ match analytic → model + conical L confirmed.
- **R1 reach:** does the tank reach ~18.9 kV (full) / ~15.5 kV (eased)? Confirm single-kick
  (no accumulation). **Q-sweep:** reach stays >15 kV at Q = 320/500/900 (and note how low Q can go).
- **R2 governor:** V_glow that cleanly holds 15 kV; energy shaved/event; Q impact.
- **R3 crowbar:** per-event + cumulative dump energy → sink size; confirm idle under nominal drive.
- **R4 integrated:** settles ≤ 15 kV, crowbar idle, **sink load quantified** for both drive modes.
- **Headroom check:** confirm the ~26% margin (18.9 vs 15) survives the full model, not just the
  single-kick estimate.

## 8. Verdict set

- **TANK-HOLDS-15kV** *(expected)* — tank reaches ≥15 kV capability AND the two-tier clamp holds it
  at 15 kV with the crowbar idle. The revised resonator + clamp is validated. State the sink load
  for both drive modes and recommend eased-drive if the full-drive sink is impractical.
- **TANK-STILL-UNDERDRIVEN** — if even the revised caps fall short (would contradict the energy
  balance — investigate the pump→tank coupling / charge-sharing efficiency, the prime suspect).
- **CLAMP-INSUFFICIENT** — reaches 15 kV but governor can't hold / crowbar fires every cycle.
- **SINK-OVERSIZED** — holds, but full-drive sink (~38 W) exceeds what the void/structure carries →
  mandate eased-drive, quantify the eased-drive sink.

A negative verdict is a deliverable. Pre-committed: do not retune to force TANK-HOLDS-15kV.

## 9. Deliverables

- `resonator_sim.py` re-parameterised (or a config) for the r0.2 geometry; R0 self-test green.
- `resonator-r2-findings.md` — R0–R4 results, the energy-balance confirmation, governor/crowbar
  behaviour, **sink load (both drive modes)**, Q-sensitivity, headroom check.
- `resonator_r2_traces.png` — V(t) for undamped reach, governed, crowbar, R4 (both drive modes).
- `resonator_r2_sink.csv` — per-event + cumulative clamp energy vs V_glow/V_crowbar.
- CHANGELOG entry. Branch not merged.

## 10. Simulation roadmap — next steps after this run

This run closes the **tank-reach** question. The remaining path to a simulation-validated, buildable
design (each a future brief, in dependency order):

- **S2 — pump↔tank coupling.** Today the pump (`shuttle_core`) and the tank (`resonator_sim`) are
  **decoupled**: the tank drive is a parameterised E_kick. Next, extract the *real* per-cycle charge
  delivered to nodes 5–6 from `shuttle_core` and drive the tank with it dynamically — validating the
  **charge-sharing efficiency** island→tank (does the pump actually deliver the ~115–171 mJ/kick the
  energy balance assumes?). Depends on this run; needs `shuttle_core` to expose tank-side delivery.
- **S3 — spark tier at real gap geometry.** Place the gap electrodes (10–12 mm tungsten spheres at
  4.5–5 mm, 3–4° wide, 0.3 mm mica barriers, 20–30 mm smooth glow backstops) at the G3 stations,
  then run the existing spark-derate machinery at the *real* geometry → strike voltage, arc, quench-
  before-reversal, the 10 ns local loop. Gates the commutation. **Needs the gap hardware drafted
  first (DXF work).**
- **S4 — glow / void-clamp physics.** Model the void glow I–V from Paschen/pd to **bracket V_glow**
  (reduce the sweep to a predicted window). Partly bench-dependent (pressure trim). Largely
  independent of S2/S3.
- **S5 — full-system integration + dissipation.** Couple pump + tank + clamp + gaps in one run with
  **thermal/dissipation accounting** — clamp sink load, coil Q-heating, electrode erosion (the
  "power-machine" dissipation side; see the philosophy doc). The closing validation toward a build.

Dependency sketch:
```
this run (tank reach) ✓gate
      ├─► S2 pump↔tank coupling ─┐
      ├─► S3 spark tier ─────────┤ (S3 needs gaps drafted)
      ├─► S4 glow physics ───────┤ (mostly independent)
      └────────────────────────► S5 integration + dissipation
```

## 11. Out of scope (this run)

Pump internal dynamics (drive is a parameter here — see S2); real spark/glow electrode geometry and
the 10 ns local loop (S3); the vacuum glow operating point bench trim (V_glow swept — S4);
structural sizing of the sink/vacuum chamber and the rotor (the RPM/tip-speed constraint stays a
noted item, not a sim input); creepage/clearance; any change to the frozen solvers or `index.html`.

## 12. Material note (carried)

C_R dielectric = 8 mm garolite disc (700 mm stock). Cx barriers = 0.3 mm mica per face (flashover
protection at the narrowed 3 mm gap + ~20% C bonus). Hub core = Garolite (non-magnetic → L holds),
**but Garolite outgasses in vacuum — vacuum-void-facing surfaces should be Macor or coated**, else
V_glow drifts. Internal hollow sphere = electrode, smooth (glow-favouring). Coil = copper 3/1 mm;
**if the 1 mm bore carries coolant it must be dielectric** at 15 kV. RPM envelope (15k/10k/5k) is
**provisional** — a 1 m rotor exceeds metal tip-speed limits above ~3–4k rpm (CFRP only); carried
for the structural iteration, not this sim.
