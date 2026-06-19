# Findings — S6: reluctance regeneration coupling (L(θ) overlay → sense + best node)

**Branch** `s6-regen-coupling` (off `main`). **Verdict:** **`COUNTER-ROTATING`** (Block D's assertion
verified, not asserted) **+ `REGEN-CLOSES-AT-CORE`** (best tap = the core-direct 9/10 gap that doubles as the
governor) **+ `REGEN-TRIVIAL`** (the surplus is 0.13 % of the Cem per-stroke loss — a negligible trim, not a
sustaining regen).

**What S6 decides:** where the S5 resonator surplus connects into the Block-D C-EMs so it adds counter-
rotation torque instead of braking. Reluctance torque T = ½·i²·dL/dθ is polarity-blind, so **only timing
decides drive vs brake**. S6 overlays the L(θ) reluctance profile on the frozen fire clock, verifies the
rotation sense, scores the candidate tap nodes, and checks the scale. The headline: the regen the no-consumer
machine "reopened" is **geometrically sound but energetically trivial** — the architecture works, the recycle
doesn't pay.

**Scope / discipline:** parallel-producer (like Block D) — reads the Block-D C-EM map + the **frozen**
`shuttle_event_angles.csv` fire clock + the S5 surplus; never feeds `solveDoubler4` / `shuttle_core`. **Frozen
empty-diff asserted** (`shuttle_core.py` / `reference/` / `index.html` / `resonator_sim.py`). Read-only on
the DXF/CSV. No DCCREG.

> **Provenance flag (to TMD):** the DXF r0_6 has **no C-EM/pole layers** — the C-EM stations come from Block
> D §2, and the **as-built pole datum** (the rotor-pole clocking vs the fire clock) needs the next DXF rev to
> verify. S6 confirms the counter-rotating placement is *achievable* and returns the required station.

---

## §8 named checks (all PASS)

| # | check | result |
|---|---|---|
| 1 | L(θ) self-tests (periodicity, max/min, half-pitch offset) | ✓ |
| 2 | frozen empty-diff + read-only DXF/CSV | ✓ |
| 3 | strokes in their rising-L windows (margin > 0) | both, **15° margin** ✓ |
| 4 | rotation sense unambiguous (single sign, not borderline) | 15° margin, both ahead ✓ |
| 5 | surplus-isolation (worst mis-fire drain) | drains **12 mJ of 89 mJ** (recoverable < 1 fire) ✓ |
| 6 | V headroom ≤ 20 kV incl. resonant magnification | 15.0 + 0.27 kV < 20 kV ✓ |

## A1/A2 — L(θ) overlay → rotation sense

The C-EM groups sit at 0° (group A, C3) and 30° (group B, C4) on the 60° super-sector; the rotor pole pitch is
60°, so each group's **rising-L (motoring) window is a 30° arc** approaching alignment, and the two windows are
offset by **exactly half a pitch (30°)** — the Block-D line-51 "no dead spot" invariant (self-test PASS).

The frozen fire clock fires **group A at SG3b = 16.05°** and **group B at SG4b = 46.05°** — **30° apart,
matching the group offset**. With the Block-D-intended pole datum (the one that centres each stroke in its
group's rising-L window):

| group | rising-L window | stroke | in window? | margin |
|---|---|---|---|---|
| A | 1.1°–31.1° | 16.05° | **yes** | 15.0° to each edge |
| B | 31.0°–61.0° | 46.05° | **yes** | 15.0° |

**Both strokes fire ahead of the approaching pole (mid rising-L), with a single consistent sign →
`COUNTER-ROTATING`.** Because the two strokes share the same 16.05° offset from their group's C-EM, the
machine is single-sense — both groups motor or both brake, never split. **Block D's counter-rotation
assertion holds against the geometry — verified, not asserted.** As-built datum tolerance: **±15°** before a
stroke crosses into the falling-L arc and that group brakes.

## A3 — node-tap scoring (priority: phase > isolation > V-match > non-disturbance)

| tap | phase | isolation | V-match | disturb | score | (1)+(2) gate |
|---|---|---|---|---|---|---|
| **core-direct 9/10 (gap = governor)** | 2 | 2 | 2 | 1 | **7** | **OK** |
| transfer-cap C3/C4 (ride stepping) | 2 | 1 | 2 | 1 | 6 | no (isolation) |
| governor re-route (clamp → Cems) | 0 | 2 | 1 | 2 | 5 | no (phase) |

**Best node = the core-direct 9/10 gap that doubles as the governor** (the prior hypothesis, now confirmed by
the score): one element fires on **(core > 15 kV) AND (rotor in rising-L)**, so it sheds the excess *through*
the Cems instead of to a dump. It passes the priority (1)+(2) gate outright (phase-feasible at the rising-L
window centres; native >15 kV excess-only isolation) and scores highest on (3)+(4) — V-matched (15 kV ≪ 20 kV
Cem rating, 5 kV headroom) with only a mild disturbance to the held core (the surplus was *already* being
shed by the governor; rerouting it to torque doesn't perturb the 15 kV hold). The transfer-cap tap is
auto-phased but needs a *separate* >15 kV gate (loses on isolation); the governor re-route is voltage-gated,
not angle-gated, so it fails the phase gate without a buffer (`REGEN-NEEDS-BUFFER` would apply if it were the
only route).

**Regen stations returned: group A 16.05°, group B 46.05°** (the rising-L window centres) — the DXF
instruction for the next rev.

## A4 — scale + stability → `REGEN-TRIVIAL`

| quantity | value |
|---|---|
| surplus (S5 governor sink) | 14 W ÷ 600 Hz = **23.3 mJ/fire** |
| Cem magnetic energy | ½·(μ₀·A_gap/l_gap)·(N·I)² = **14.1 J/coil** (N-independent) |
| Cem per-stroke copper loss | 2π·E_mag/Q × 6 active = **17.7 J/stroke** (Q ≈ 30) |
| **surplus / Cem-loss** | **1.3×10⁻³ = 0.13 %** |

**`REGEN-TRIVIAL`:** the surplus is **0.13 % of the Cem per-stroke loss** — a negligible trim, not a
sustaining regen. Even correctly phased into the best node, routing the 14 W surplus to torque buys ~0.1 % of
the drive. The positive-feedback loop (surplus → torque → speed → pump → surplus) has gain ~ ratio ≪ 1 and is
additionally **bounded** by the 15 kV governor threshold (it only sheds the genuine excess) → **no runaway**.
The no-consumer machine therefore stays a **build-then-hold dissipator**: the architecture works, the loop is
stable, but the recycle doesn't pay.

## Verdict + design output

- **`COUNTER-ROTATING`** — verified achievable; the as-built datum needs the DXF C-EM/pole layers (flagged).
- **`REGEN-CLOSES-AT-CORE`** — core-direct 9/10 gap doubling as the governor; stations 16.05°/46.05°.
- **`+ REGEN-TRIVIAL`** — surplus 0.13 % of the Cem drive → a 0.1 % trim, bounded, doesn't pay.
- **DXF instruction (to TMD):** place the regen gap at **16.05° (group A) / 46.05° (group B)**, core-direct
  9/10, strike threshold > 15 kV. **But A4 says the energy return is a ~0.1 % trim** — so the recommendation
  is to keep the simpler S5 dissipative governor unless a future change makes the surplus material (e.g. a
  much larger over-delivery, or a real external consumer — which TMD has ruled out). The regen station lands
  on the same clocking map as the spark gaps, so it slots into the existing phase-plate / clocking-solver
  family if pursued.

## Deliverables

`sim/s6_regen_coupling.py` (read-only producer; L(θ) + overlay + node scoring + A0–A4 + §8 checks) · this
findings doc · `s6_lqtheta_overlay.png` (rising-L windows vs the fire-clock stations) · `s6_node_tap_scores.csv`.
Frozen empty-diff asserted. **Not merged.**
