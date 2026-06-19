# Findings — S8 r0.2: unified coupled model, EMERGENT doubler

**Branch** `s8-unified-coupled-ledger` rev **r0.2** (off `main`; supersedes r0.1). **Verdict:**
**`SYNERGY-GENERIC` — now *earned*, not structural.** Plus the load-bearing **sub-result: the emergent
spark-gap `DOUBLER_ETA` = 0.385**, which **resolves the audit residual *above* its 0.368 floor** — with the
breakdown threshold *in the solve* the arc loss is ~0.1 %, not the 1.8 % the audit got by over-counting the
commutation charge. The foundation holds even closer to the ideal 0.386 than the audit suggested.

**Why r0.1 was retracted as the synergy test (a code read found the verdict was assumed):** (1) the dominant
losses were hard-coded scalars independent of every DOF → flat by construction; (2) output was pinned at 0
(`P_MOTOR < P_CORE` hard-coded) → `diss_frac ≡ 1` by identity; (3) the guard checked only the fire-ring
sub-ODE — the machine ledger was tautological (`E_in := E_diss + E_out`). **r0.2 removes all three:** the
doubler is **unfrozen into the dynamics** (a real spark-gap transfer — hold off to V_bk, fire through V_arc,
quench at current-zero) so the **C-C tax emerges and responds to V_bk**; **output is emergent**; and the
guard is **machine-level against an independent belt input**. (The dielectric debunk 53 W → 0.033 W and the
fire-ring ODE are kept from r0.1 — the parts that were right.)

**The guard earned its keep, again.** The first r0.2 build double-counted the fire-gap arc (it's *inside* the
C_R chain that `E_belt_in` already tallies) — the machine guard caught it (`diss_frac = 1.0004 > 1`, residual
3.6×10⁻⁴), and the fix closed the ledger to **0.0**. A non-closing ledger is a bug, not a discovery.

**Consumes the audited foundation:** z-anchor **1.334**, W_mech/W_coll/Q_isl HOLD, C_R 789 pF; `DOUBLER_ETA`
**recomputed in-model**, not inherited. Frozen solvers byte-identical (empty-diff asserted). No new energy.

---

## §4 named checks

| # | check | result |
|---|---|---|
| 1 | frozen byte-identical empty-diff | ✓ clean |
| 2 | **Gate 0** — emergent doubler (ideal limit) reproduces z=**1.334** + η=**0.386** + 15 kV | ✓ (tax frac 0.614) |
| 3 | emergent spark-gap `DOUBLER_ETA(V_bk)` vs 0.386 and the audit's 0.368 | **0.385** @ design gap — *above* the floor |
| 4 | machine-level guard `\|E_belt_in − (E_diss+E_out+ΔS)\|/E_belt_in` < 0.1 % (independent) | **0.0** at every point |
| 5 | four-destination partition, **output as a result** | output **~0 W** (S7 core-limited motor — measured) |
| 6 | synergy sweep with the emergent C-C tax | `diss_frac` flat at the floor — now **earned** |
| 7 | parametric probe `[RH]` | dormant (300 Hz vs 2·f₀ 1.27 MHz) |
| 8 | verdict + emergent-`DOUBLER_ETA` resolution | `SYNERGY-GENERIC` (earned); η = 0.385 |

## Stage A — emergent doubler Gate 0

The dynamic spark-gap doubler, in the **ideal-diode limit** (V_bk → 0, V_arc → 0, continuous conduction),
reproduces the frozen boxes **on the current geometry**: emergent **z = 1.3340** (the re-anchored value, not
the stale 1.2033) and emergent **DOUBLER_ETA = 0.3860** (tax fraction 0.6140) — both to four digits. The
energy partition (W_mech the constant-Q stroke, E_tax the gap equalization) falls out of the integration. **Gate
0 PASS** — the model earns trust before any spark-gap or coupling number is believed.

## Stage B — emergent spark-gap `DOUBLER_ETA(V_bk)` — the audit residual closed

| V_bk | η (V_arc 20) | η (35) | η (50) |
|---|---|---|---|
| 0–8 kV | 0.3854 | **0.3851** | 0.3847 |
| 12 kV | 0.4180 | 0.4176 | 0.4172 |

**At the design gap (V_bk = 6 kV, V_arc = 35 V): emergent `DOUBLER_ETA` = 0.385, arc fraction 0.1 %.** This
**resolves the audit residual** — and *corrects* it: the audit bolted `E_arc = V_arc·Q_cyc` onto the ideal
charge flow and got 0.368, but it **over-counted the commutation charge by ~18×** (8.23 µC vs the
self-consistent ~0.46 µC). With the threshold *in the solve*, the arc loss is only ~0.1 % of W_mech, so
**`DOUBLER_ETA` effectively holds at ~0.385**, very close to the ideal 0.386. The threshold does *not* add tax
(it can only reduce it: at high V_bk the gaps hold off, transfer less, and η *rises* to 0.42 — a different
regime). **v0.11 should consume 0.385, not the audit's 0.368.**

## Stage C — machine-level conservation guard

`E_belt_in` is computed **independently** = the belt's mechanical work (varicap reaction W_mech + island
collapse + rotor drag + Cem-drive mechanical). The four destinations: storage **88.76 mJ**, circulation
**1980 mJ** (the fire-transient reactive slosh), **output ~0 W**, dissipation **138.1 W**. The machine ledger
closes to **residual 0.0** (< 0.1 %). **Output ~0 is a *result*** — the S7 pump-/core-limited motor (the Cems
draw 14 W but their 15 W core loss alone exceeds it, so no net contra-rotation) — **not** the r0.1 hard-coded
0.

## Stage D — synergy sweep (now a real test)

`diss_frac` is flat (≈ 1.000) across every DOF — V_bk, septum, k, fire-phase, cap-scale — **but this is now
earned, not structural:** the emergent C-C tax genuinely *responds* (η_doubler varies **0.385 → 0.418** over
V_bk), yet the **dissipation fraction stays at the floor** because the output is ~0. In a no-consumer machine
the belt input becomes essentially all heat regardless of how the tax is tuned — so a flat `diss_frac` is the
correct, measured answer. The U-tube/local-wrong probe is negative: no coupling drops the global fraction
below the floor.

## Stage E — parametric probe `[RH]`

Rotor modulation (~300 Hz) is 2.4×10⁻⁴ of 2·f₀ (1.27 MHz) — **dormant** by ~3.5 decades. No parametric gain at
the design point (would need a redesign to a faster modulation lock; the guard applies — any gain must trace
to belt work).

## Verdict + roadmap

**`SYNERGY-GENERIC` (earned).** With the dominant C-C tax now emergent and able to respond to V_bk, the
dissipation fraction is still flat at the floor — the nest is the sum of its parts, the belt supplies the full
dissipation, and **this time it is measured, not assumed**. No coupling carries a synergy. **Sub-result
(independent of the synergy verdict): emergent `DOUBLER_ETA` = 0.385** — it *resolves the audit residual above
its 0.368 floor* (the audit over-counted the arc charge), so the foundation holds even closer to 0.386 than the
audit indicated. **v0.11 consumes 0.385**, the z-anchor 1.334, and the unchanged W_mech/W_coll/Q_isl; the
hold-power floor is re-stated on 0.385 (a ~0.3 W-class change vs the 0.368 assumption), and S5–S8's qualitative
verdicts stand. This is the last analysis in the arc → **v0.11 (the reconvergence freeze)** next, then Phase 6
full-deck SPICE on the current topology, then the mechanical budgets.

## Deliverables

`sim/s8_unified_coupled.py` **r0.2** (multi-rate integrator: emergent spark-gap doubler, kept fire-ring ODE,
emergent Cem output, four-destination ledger, **machine-level** guard, sweep, `[RH]` probe; Gate-0 on 1.334) ·
this findings doc (r0.2) · `s8_energy_partition.csv` (with the machine-level residual) ·
`s8_doubler_eta_vs_vbk.csv` (the emergent η(V_bk), the audit residual closed) · `s8r02_eta_and_sweep.png`.
Frozen empty-diff asserted. **Not merged.**
