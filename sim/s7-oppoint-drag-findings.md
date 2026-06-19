# Findings — S7: expanded-circuit operating point (FIRST) + drag budget & spin-up balance

**Branch** `s7-expanded-oppoint` (off `main`). **Verdict:** **`OPPOINT-HOLDS`** (Phase 1, gating — passes) **+
`BALANCE-FAILS`** (Phase 2, estimate). The expanded circuit still builds/holds 15 kV with the motor as an
explicit load, no node over-volts 21 kV, and the pump→motor power is extracted (**~4–14 W**, replacing the
stale ~14 W surplus) — **but** that power is at/below the estimated **stator drag (~18 W)**, which the **15 W
Cem core loss dominates**, so the contra-rotation does not close on the estimated numbers. The fix is drag
reduction (cut the core loss), not a circuit change.

**Method (hybrid, forced by the SPICE block):** the prior xsim work found the nonlinear flying-bucket shuttle
is **ngspice-blocked**, but the galvanic pump core recovers z and the *linear* expanded elements are
ngspice's strength. So: **ngspice** for the galvanic regression (Phase 1A) + the new linear physics
(split-resonator f₀, Cem-branch impedance); the **frozen `resonator_sim`** for the unchanged nonlinear reach
(valid because the Cems are high-Z f₀ spectators, shown below); the **energy budget + coil-topology** for the
node transients and pump→motor power; coarse `ρω³R⁵`-class models for Phase-2 drag, **every figure tagged
ESTIMATE**. Frozen empty-diff asserted (`doubler_core` / `shuttle_core` / `resonator_sim` / `reference/`).

---

## §3 named checks

| # | check | result |
|---|---|---|
| 1 | frozen empty-diff; 4-node regression recovers z=1.2033 **before** new elements | **z = 1.2042** (ngspice galvanic, Δ < 0.03) ✓ |
| 2 | f₀ / L_total preserved under the split coil | L_total **79.0 µH**, f₀ **632 kHz** ✓ |
| 3 | worst per-node fire transient vs 21 kV | **17.5 kV** (split halves the 35 kV asymmetric) — no breach ✓ |
| 4 | reach with Cem load: 15 kV held? | **yes**, v_peak 14.95 kV, crowbar idle ✓ |
| 5 | pump→motor power extracted | **4–14 W** `[IR/EST]` (the Phase-2 input) |
| 6 | drag estimate: per-source split + total | windage 0.06–5.6 W, bearing 0.5 W, core 15 W → **15.6–21.1 W** `[EST]` |
| 7 | balance: motor power vs stator drag; spin-up | margin **−4.3 W** (deficit); spin-up **does not close** `[EST]` |

## PHASE 1 — operating point on the expanded circuit (gating) → `OPPOINT-HOLDS`

**1A regression (must pass first).** The runnable galvanic deck (the existing `xsim_x0_galvanic.net`,
behavioural charge-defined varicap pump + near-ideal one-way diodes) recovers **z = 1.2042** in ngspice vs the
frozen reference **1.2033** (Δ = +0.0009, within the 0.03 witness tolerance) — **the deck core reproduces the
frozen 4-node pump before any new element is enabled.**

**1B split resonator.** Replacing the single L_R with **two L_R/2 halves (k = 0.3 aiding)** sized to preserve
the total: **L_total = 79.0 µH, f₀ = 632 kHz** (within 5 % of 637 kHz). The open >21 kV flag from the split is
**resolved**: the split shares the ~20 kV L_R fire swing into two ~10 kV drops, halving the node-to-ground
peak **35 → 17.5 kV** — **no node over-volts the 21 kV island ceiling** (this is the coil-topology Part-A win,
now confirmed on the expanded circuit). No `OVERVOLT-SPLIT`.

**1C Cems as load (the new physics).** Enabling the 12 Cem branches (series **L_coil + C_block 440 nF**) across
Ca/Cb:
- **Block-D premise confirmed.** Each branch is resonant **at PRF** (L_coil 0.64 H + C_block 440 nF →
  f_res = 300 Hz = PRF), giving a **low-Z 40 Ω torque-carrier** there; at f₀ = 637 kHz it is **|Z| = 2.56 MΩ
  = 8106 × Z₀ → a high-Z spectator**. So the Cems carry resonant torque current at PRF but are invisible to
  the f₀ reach ring.
- **Reach holds under load.** Because the Cems are 8000× Z₀ at f₀, they **do not detune or load the f₀ ring** —
  the frozen `resonator_sim` reach is unchanged: **v_peak 14.95 kV, crowbar idle, 15 kV holds.** No
  `REACH-DEGRADED`.
- **Pump→motor power = 4–14 W `[IR/ESTIMATE]`.** The Cems are **pump-limited**: driving them to their
  N·I = 1650 A-t ampere-turn ceiling would need **~290 W** (E_mag 0.77 J/coil × 6 active, replenished at PRF/Q),
  but the doubler nets only **useful_per_fire = 6.15 mJ/fire**. So the available motor power is the doubler net
  routed to the Cems (**3.7 W**, lower) up to the routed governor over-delivery (**14 W**, upper) — far below
  the Cem capacity. This is the number Phase 2 needs; it **replaces the stale ~14 W S5 surplus** with a
  load-aware, pump-limited range.

**Phase-1 verdict `OPPOINT-HOLDS`:** the expanded circuit reaches/holds 15 kV with the Cem load, no node
> 21 kV, pump→motor power extracted. **Phase 2 proceeds on these numbers.**

## PHASE 2 — drag budget (ESTIMATE) + balance → `BALANCE-FAILS`

**2A drag envelope** (coarse; the goal is the envelope, not a point value):

| source | value | model |
|---|---|---|
| windage | 0.06 W (1 Pa) … 5.6 W (100 Pa) | ½·C_M·ρ·ω³·R⁵ swept over cavity pressure `[EST]` |
| bearing | 0.5 W | μ·F·r·ω `[EST]` |
| **core loss** | **15 W** | steel mass × specific loss at PRF `[EST]` — **dominant** |
| **steady total** | **15.6 … 21.1 W** | |

**2B balance.** The belt covers the rotor drag directly; the Cems (via the pump) must cover the **stator drag
+ stator spin-up**. The stator drag (Cem iron core loss + a windage share + bearing) ≈ **18 W**, against the
**4–14 W** pump→motor power → **margin −4.3 W (deficit).** The motor is **both pump-limited and
core-loss-limited**: the 15 W Cem core loss alone exceeds the available motor power, so there is no headroom
left for net contra-rotation torque.

**2C spin-up.** With a net torque ≤ 0 at the design speed, the stator **never reaches speed** on the estimated
numbers — the contra-rotation does not close.

**Phase-2 verdict `BALANCE-FAILS` `[ESTIMATE]`.** The deficit is modest (−4 W) and every figure is an estimate,
so this is a *flag, not a death sentence* — the dominant lever is clear: **cut the Cem core loss** (better
lamination, less steel, lower flux density) below the pump→motor power, and/or **route more of the governor
over-delivery** to the motor (the S6 path — though S6 found that surplus small). A modest core-loss reduction
(15 → ~8 W) plus the upper-route 14 W would flip this to `BALANCE-TIGHT`/`CLOSES`. The architecture and the
electrical operating point are sound (Phase 1); the open question is purely the mechanical/iron loss budget.

## Verdict + roadmap

- **`OPPOINT-HOLDS`** (Phase 1, gating) — expanded circuit holds 15 kV with the Cem load, no node > 21 kV,
  pump→motor power 4–14 W extracted. The reach is robust to the motor load (f₀-spectator Cems).
- **`BALANCE-FAILS`** (Phase 2, estimate) — pump→motor power < stator drag (core-loss-dominated); spin-up does
  not close. Lever: cut the Cem core loss / route more surplus.
- Out of scope (informed by this envelope): final bearing selection, supercritical rotordynamics, detailed
  thermal of the per-coil loss, CFD windage. The next step is a real core-loss/lamination budget for the Cem
  iron, then a combined-drive transient (stepping + the routed surplus into one coil).

## Deliverables

`sim/s7_expanded_oppoint.py` (hybrid: ngspice galvanic regression + linear AC, frozen `resonator_sim` reach,
energy-budget + flagged estimates) · this findings doc · `s7_oppoint_drag.csv` · `s7_phase1_oppoint.png`
(node transient vs 21 kV; Cem impedance vs PRF/f₀) · `s7_drag_balance.png` (drag vs pressure with pump→motor
overlaid). Frozen empty-diff asserted. **Not merged.**
