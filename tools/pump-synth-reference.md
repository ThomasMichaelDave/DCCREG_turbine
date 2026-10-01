# PUMP-SYNTH reference

This page is the reference drawer of `tools/pump-synth.html`. It replaces `tools/reference.md`, which documents the older tool's ledger composition.

## What the tool answers

*Given these rotor plates, does the drawn pump pump, by how much, and what stops a smaller or faster rotor?*

The chain has one direction only:

1. rotor plates
2. forward law
3. the ladder
4. the exact engine
5. **PUMPS: YES / NO**

| stage | module | what it does | tier |
|---|---|---|---|
| plates → C_max, C_min, κ_C | `sim/pump_sizing.py` (JS mirror `tools/pump-sizing.js`, gate S1b) | ε0·εr·A/g with kept sectors (Eq. 8), the ring (Eq. 9) and moist-air εr (A.10) | [OC] law |
| C_max → every other capacitor | `sim/pump_sizing.py` ladder | Ca = 1.10·C_max, Cx,max = 1.68·C_max, the fixed floors, and C_blk from the branch PRF | [IR] ratios |
| ladder → z | `sim/pump_engine.py` (the pump-calc engine) | monodromy of the drawn pump: doubler + islands + all eight gaps, tank collapsed | [OC] / [ME] |
| z → verdict | `sim/pump_synth.py` | PUMPS = z > 1; the robustness strip; the invariant battery; the objectives | [IR] |

## Why the searches are small

z depends only on capacitance ratios [OC].

- Gate **S4** confirms this. Every C scaled by k leaves z unchanged to 2e-13 once Lx and R_lx are co-scaled (L/k, R/k).
- With the C's alone scaled, z moves by 4e-9. The island ring time is the only non-capacitive scale.

Every capacitor is a ratio of C_max, and the floors stay fixed (Cpar, Cx_min, the gap / boss / island strays). So **z depends on the plates only through C_max and κ_C**, and r_out and g_v enter only through C_max ∝ A_m/g_v. Gate **H-SYN0** checks this to 1e-9.

`min_diameter` is therefore a 1-D bracketed root search in C_max via r_out, at the g_v the insulation law gives.

Under D-CPAR = *scaled*, the strays grow with C_max and z becomes nearly size-independent. The tool says so when that mode is on.

## Panels

**Rotor plates.**
- active band r_in / r_out;
- rotor gap g_v and its dielectric (air: temperature, pressure, RH; or vacuum, kapton, mica);
- N_sec / n_kept;
- the central ring (on/off, inner/outer radius).

Defaults are the freeze / DXF values: R95–R387, 7 mm air, 12/6, ring R25–R68.2.

**Ladder.** Every derived item shows:
- its value and its ratio to C_max;
- its rule and tag;
- a **pin** box that overrides the ladder value;
- the engine's **critical** value, where z = 1 with everything else as sized, and a headroom meter. The critical value is found on demand by a bracket-and-bisect search on the exact engine (the `findCriticalCa` pattern of `index.html`, generalised).

**Commutation / firing.**
- Lx and its ESR;
- V_strike (the D-SCALE anchor) and the ceiling V_ceil;
- the gap radius (as a fraction of r_out) and the sphere-gap ball and lateral gap (I11 cross-fire);
- the gap model per class: valve M-OW, sustained arc, ring-down M-RD(I_hold) and symmetric recovering M-SR(I_hold, t_rec).

**Drive.** rpm, and the motor branches on/off.

## Gap-model robustness strip

The strip gives z of the same machine with the load and fire gaps under four models:
- M-OW (valve);
- M-RD(→0) (ring-down to extinction);
- M-SR(0.1 µs);
- M-SR(1 µs), with I_hold 0.3·i_pk1.

All four are exact runs, executed in parallel helper workers when the machine has the cores. At 2 Ω the lit load arc never falls to 0.3·i_pk1 before its ring ends, so both M-SR rows collapse onto M-RD(→0) (pump-calc E6).

## Invariant battery

Status is one of **pass**, **fail**, **not-evaluated**, **n/a** or **info**. Feasibility and the named blocker use only the evaluated rows (pass/fail).

| id | source in this tool | status |
|---|---|---|
| I1 conservation | engine ledger residual (W = ΔE + E_diss), per evaluation | evaluated |
| I2 solver authority | K1–K4, the engine self-test, the pattern repeat | evaluated |
| I3 z band [1.20, 1.45] | exact z; the band is the robust-margin lamp (PUMPS means z > 1) | evaluated [IR] band |
| I4 insulate-first | `design_synth` spark-gap / septum / coil rule, plus g_v ≥ V_ceil / E_bd(medium) | **provisional** (D-MEDIUM) |
| I5 tax | the η(cut) band | info until D-CUT |
| I6 parasitic floor | Cpar ≥ 20 pF | evaluated |
| I7 motor matched | f_res = 1/(2π√(L·C_blk)) against PRF_branch; the motor-output sub-check is not evaluated | evaluated (motor on) / not-evaluated (motor off) |
| I8 DC tank | — | n/a (tank collapsed) |
| I9 mechanical | rim speed at the rotor body R(r_out·1.27) < 200 m/s; vacuum and supercritical not evaluated | evaluated (partial) |
| I10 shuttle integrity | engine ring t½ inside the 5° window; scaled i_pk ≤ 100 A; V_strike < V_ceil | evaluated |
| I11 cross-fire | `design_synth.overlap_deg` against the SG3b–BS3 spacing | evaluated |
| I12 resonant timing | overlap time ≥ strike + engine t½ + dwell | evaluated |
| I13 island recovery | exact twin (Lx vs shorted) plus TRV admissibility | evaluated |

The **named blocker** is the first failing evaluated invariant, in `design_synth`'s priority order. When nothing fails, it is the least-slack passing one (`design_synth.binding`).

## Objectives

- **min_diameter.** The smallest rotor with z ≥ 1 + m (m = 0.20). It must also pass:
  - I4, at g_v = V_ceil / E_bd: 7.0 mm for 21 kV in air at 3 kV/mm [RH];
  - I9;
  - I11, where the gap radius follows r_out, so the overlap grows as the rotor shrinks;
  - I12.

  Method: an Illinois regula-falsi search in r_out (exact runs). Monotonicity is checked on the search's own points (**H-SYN2**). On a violation the 15-point scan answer is returned instead (SYNTH-SCAN-ONLY).
- **max_margin.** The largest z at the stated maximum rotor diameter. Optionally a golden-section search on the Ca ratio, which shows the engine's z-optimal Ca against the ladder's 1.10 (D-CA).
- **max_rpm.** The highest rpm passing I9 (rim) and I12 (timing). It is analytic, because the ring t½ does not depend on rpm, and is confirmed by one exact run. With the motor on, C_blk is re-sized at the new PRF and I7 is re-checked.
- **max_eta** is disabled: D-CUT (η is cut-dependent for an unloaded, growing pump).
- **min_belt_power** is disabled: D-GOVERNOR (it needs a loaded operating point).

**Every Solve result is re-run exactly (H-SYN3).** No interpolation ever sets a headline.

## What was dropped from the older tool, and why

| older feature | here | reason |
|---|---|---|
| the operating-efficiency card and its canary rung | removed (D-LEDGER) | It was a ledger composition that double-counts the island tax. The exact engine never observed it. |
| the forbidden-path diagnostic and its FE-leakage slider | removed | Out of scope for a pump verdict. The older tool keeps it. |
| the regression card (z 1.334) | canary K1, on the engine **and** on JS `solveDoubler4` | Same anchor, now checked by two engines. |
| free sliders for C1min / Ca / Cpar / Cx / C_R | the ladder plus pins | The capacitors are sized from the plates. |
| the 4-D grid search | the reduced searches above | 512 exact runs would take more than an hour in-browser. |
| the max-energy-density objective | removed | It is a tank quantity, and the tank is out of scope. |

## TMD-gated decisions

Each ships with its flagged default; the alternative is selectable.

| id | default | alternative |
|---|---|---|
| D-LEDGER | the operating-efficiency card is retired | — |
| D-CMIN | active area + 16 pF fringe floor (279.6 pF at the freeze, vacuum) | the ring adds to C_max and sets C_min (295.6 pF) |
| D-CA | Ca = 1.10·C_max | the engine's z-optimal Ca (`max_margin` with the Ca search) |
| D-CX | Cx,max = 1.68·C_max | size Cx for the pump alone |
| D-CPAR | fixed floors | strays scale with C_max |
| D-GAPDEFAULT | M-RD(→0) for load and fire | any model per class |
| D-MOTORDEFAULT | motor off, "not assessed" | motor on (pump-calc M2/M3 fail, so the result is shown as "not converged") |
| D-CUT | no single η (the band is shown) | — |
| D-SCALE | kV/A/µC anchored at \|V_f(load)\| = V_strike | — |
| D-GOVERNOR | not modelled | — |
| D-MEDIUM | I4 provisional: air 3 kV/mm | hard vacuum, the K_VAC·g^0.6 law; ≤ 10 Pa is not evaluated |

## Stage 2 — plate geometry (after the lock)

- **The lock** freezes stage 1 (inputs, ladder, z) under a SHA-256 hash in the URL, and is re-verified against the engine on every reload.
- **Ca/Cb** become electrode footprints by the area law A = C·t/(ε0·εr). The seed is the DXF: 6 × 30° annular sectors, r110–175, 4.5 mm mica, which gives 309.18 pF.
- **Round trip.** Any realized-C deviation (for example from manufacturing rounding) goes back through the exact engine.
- **Context.** The other electrodes are placed from the DXF as locked context: C1/C2 stators r95–387, rotor faces r75–387, Cx pickups r58–350, island bars r75–350, in alternating 30° sector sets.
- **Axial stack** [IR], the one order where every pair faces across its own dielectric:
  `flange · Cx gap · ND2 · Ca mica · ND1 · C1 air · rotor A · septum · rotor B · C2 air · ND4 · Cb mica · ND3 · Cx gap · flange`.
- **Export** is JSON plus `tools/pump-geometry.FCMacro` (FreeCAD), with gates G-SEED, G-ADJ, G-JS, G-CAD and G-RT (`sim/pump_geometry_gates.py`).

## Out of scope

- tank and core dynamics;
- motor torque;
- dielectric thickness from voltage;
- governor / crowbar;
- Pass B;
- any design change;
- any edit to either parent tool.
