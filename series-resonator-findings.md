# Findings — series-resonator output stage (L_R in series with C_R, 5–6)

**Branch** `series-resonator` (off `island-charging` `d0ef6f6`). **Verdict:** **`SERIES-HOLDS-DC`** ·
**`REACH-DC-15kV` in 6 fires** · **`OVERSHOOT-SELF-LIMITS`** · **`QUENCH-SERIES-CLEAN`** ·
`DC-AC-SPLIT = {15.0 kV DC, 20.0 kV ripple}` · `MACHINE-ETA = 0.445`.

**The series topology dissolves the accumulation problem.** The prior blocks left the reach as a ~6–7-fire
*pumped swing* that the **parallel** tank (L_R ∥ C_R) could never hold — L_R shorts DC, so every kick rings
down and nothing accumulates. Putting **L_R in series** with C_R (5 — L_R — junction — C_R — 6) makes **C_R
itself the DC battery**: at DC the cap blocks and L_R carries no drop, so the full 5–6 DC sits on C_R, and
with the gap open between fires nothing drains it. The pumped swing now **accumulates to 15 kV DC in 6
fires** — the exact inverse of the parallel-tank ring-down — at the *same* ~0.45 efficiency. No separate
hold cap is needed.

**Scope:** only the **post-fire output stage** is redone. Inherited untouched (cited): the pump eigen-witness
(gaps-open, topology-independent), and the island-charging source — Q_isl = 1.395 µC, E_fire ≈ 14 mJ,
W_coll = 12.45 mJ (`island_charging.csv` @ `d0ef6f6`); W_mech,stator = 15.94 mJ (`energy_balance.csv` @
`84fcaaa`); the fire-ODE form (`fire_tank_transfer.py` @ `05ccf60`). The **series fire ODE + the
accumulation loop are new** (own RK4 integrator). Frozen modules (`shuttle_core.py`,
`reference/doubler_core.py`, `index.html`) **byte-identical** (0 producer edits, asserted). No DCCREG.

---

## 1. The coupling that's easy to miss — the strike rises with V_CR `[OC]`

In the parallel tank the gap fired at V_island ≈ V_breakdown because the tank had rung down to ~0. In the
series topology **C_R holds a standing bias V_CR**, and the gap sits between the island and the C_R-branch
input (node 5 at V_CR), so it breaks down at **V_island − V_CR = V_breakdown (≈ 20 kV)**. The island must
reach **V_CR + V_breakdown** to fire → it **collapses further** (to lower C_fire = Q_isl/(V_CR+V_bd)) as C_R
fills: C_fire runs 70 pF → 42 pF as V_CR climbs 0 → 15 kV. The island has the charge to reach any strike
(Q ≈ 1.40 µC into 8 pF → 175 kV ceiling), so **the 15 kV clamp — not the island — caps V_CR** (self-test d:
the island over-reaches to 15.1 kV unclamped). The strike is modelled as the gap breakdown across the actual
electrodes, not a fixed island voltage.

## 2. The series fire ODE + accumulation `[OC]`

Per fire (inherited ODE form, now charging the DC-holding C_R), RK4 to the first current-zero:
```
L_R·dI/dt = V_island − V_CR − V_arc·sgn(I) − I·R_loop ;  dV_island/dt = −I/C_fire ;  dV_CR/dt = +I/C_R
```
The island starts at the strike (C_fire @ V_CR+V_bd); the series swap charges C_R through L_R; the gap
quenches at the series current-zero (half-period π√(L_eff·C_eff) ≈ 0.17–0.23 µs, self-test a), leaving C_R
charged. **Between fires C_R holds V_CR** (gap open, L_R in series — no drain path; self-test b/f). The clamp
extracts once V_CR hits 15 kV.

**Why it reaches 15 kV in only 6 fires despite a mismatched swap.** The island fires mid-collapse at ~70 pF,
badly mismatched to the 789 pF C_R, so only ~30 % of the island *energy* transfers at the first
current-zero — but the *charge* delivered is large because the small high-voltage island **charge-reverses**
through L_R, dumping ΔQ ≈ 2.56 µC into C_R on the first fire (V_CR: 0 → 3.24 kV). The standing 20 kV
breakdown differential is re-established every fire, so each kick adds a similar large ΔQ:

| fire | V_CR before | V_CR after | ΔQ | C_fire | W_coll (rotor) |
|---|---|---|---|---|---|
| 1 | 0.0 kV | 3.24 kV | 2.56 µC | 70 pF | 12.4 mJ |
| 2 | 3.24 | 6.10 | 2.26 | 60 pF | 14.9 |
| 3 | 6.10 | 8.64 | 2.00 | 54 pF | 16.9 |
| 4 | 8.64 | 10.98 | 1.85 | 49 pF | 18.6 |
| 5 | 10.98 | 13.14 | 1.70 | 45 pF | 20.1 |
| 6 | 13.14 | **15.11 → clamp 15.0** | 1.55 | 42 pF | 21.4 |

## 3. Verdicts (pre-committed, brief §4)

- **`SERIES-HOLDS-DC`** ✓ — C_R blocks DC and holds V_CR between fires (gap open, L_R series, no drain). The
  inverse experiment (force-drain C_R each fire → parallel-tank limit) recovers **no accumulation** (V_CR
  stuck at 3.24 kV, never reaches 15 kV), isolating the series benefit (self-test f).
- **`REACH-DC-15kV` in 6 fires** ✓ — C_R accumulates to 15 kV DC in **6 fires** at ~14 mJ/fire — the inverse
  of the parallel-tank ring-down, and consistent with the island-charging ~6–7-fire pumped swing.
- **`OVERSHOOT-SELF-LIMITS`** ✓ — the island over-reaches (15.1 kV unclamped); the **15 kV clamp binds** (the
  resonant overshoot does *not* run away — the clamp, not the island, caps V_CR).
- **`QUENCH-SERIES-CLEAN`** ✓ — the gap quenches at the series current-zero (≈ 0.17–0.23 µs, half-period),
  C_R left charged; no ring-back through the gap.
- **`DC-AC-SPLIT = {V_DC = 15.0 kV, V_ripple = 20.0 kV}`** — the steady 5–6 waveform is a **flat 15 kV DC
  bias on C_R** with a brief (~0.17 µs) **20 kV AC transient across L_R** at each fire (the breakdown
  differential ringing). The composite is the DC battery the machine wanted, with sparse ring spikes — not a
  rung-down AC tank.
- **`MACHINE-ETA = 0.445`** — mechanical → DC-store efficiency, corner-independent (arc 20/35/50 V all give
  0.445; the swap is breakdown-differential-driven, not arc-limited). The C-C taxes are unchanged from the
  island-charging block (~0.48), **but the energy now stays on C_R instead of ringing away**, so the reach
  *succeeds* at that same efficiency.

## 4. The result

**The series output stage is the right topology.** It converts the multi-fire pumped swing — which the
parallel tank dissipated — into a **sustained 15 kV DC store on C_R**, reached in 6 fires, self-limited by
the clamp, at η ≈ 0.45. The accumulation problem that has shadowed the reach since the single-kick
assumption fell is **dissolved by making C_R the DC battery**: no separate hold cap, L_R doing double duty as
the resonant charging inductor and the current-zero quench. The earlier escalation (reach is multi-fire, not
single-kick) stands — but in the series topology the multi-fire reach **is achievable and holds**.

## 5. Self-tests (all PASS)

(a) series LC half-period quench 0.225 µs = π√(L_eff·C_eff); (b) C_R holds DC, accumulates monotonically;
(c) converges to steady 15 kV; (d) clamp self-limit (island over-reaches to 15.1 kV); (e) per-fire energy
closure dE_CR + E_resid + E_arc + E_loop = island energy at strike (rel 6×10⁻⁸); (f) inverse experiment —
drain between fires → no accumulation (parallel-tank ring-down recovered).

## 6. Deliverables

`sim/series_resonator_output.py` (series fire ODE + accumulation loop + 6 self-tests) ·
`series-resonator-findings.md` (this) · `series_resonator.csv` · `series_vcr_accumulation.png` (V_CR → 15 kV
over 6 fires, clamp self-limit) · `series_5_6_waveform.png` (DC bias + AC ring; one-fire zoom) ·
`series_dc_ac_split.png` (DC/AC decomposition). Frozen modules byte-identical; **not merged**.
