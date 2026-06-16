# resonator-sim-r2 — findings (r0.2): **TANK-HOLDS-15kV**

**Verdict:** `TANK-HOLDS-15kV` — the three coordinated geometry changes **close the reach gap** that
made r0.1 `TANK-UNDERDRIVEN`. The revised tank reaches **18.8 kV (full drive) / 15.4 kV (eased)** —
both above the softened **15 kV** target at every Q — and the two-tier clamp **holds the tank at
≤ 15 kV with the crowbar idle**, governor sink **~39 W (full) / ~4.4 W (eased)**. The full time-domain
model confirms the single-kick energy-balance prediction (and its **+25 % headroom**). Recommend the
**eased drive** (~4 W sink) unless the void/structure can carry the full-drive ~39 W.

Branch `resonator-sim-r2` (off `resonator-sim`). **Standalone** RLC + clamp model under `sim/`; imports
**neither** `shuttle_core.py`, `reference/doubler_core.py`, nor `index.html`. numpy + matplotlib only
(hand-rolled RK4; crowbar a discrete event-dump). Pump↔tank coupling is still a **parameterised** drive
(the S2 next step, brief §10). Not merged. Tiers: `[OC]` physics/derived · `[IR]` modelling/reporting.

---

## What changed from r0.1 (brief §2–3)

| Quantity | r0.1 | **r0.2** | effect |
|---|---|---|---|
| Cx island | 88 pF | **648 pF** | now ≈ tank C_R → efficient charge-sharing (hydraulic "equal-vessel" transfer) |
| C_R tank | 1477 pF | **960 pF** | 8 mm garolite disc; lower energy-to-target (108 mJ for 15 kV) |
| L_R | 169 µH (cyl. mis-model) | **79 µH (conical)** | f₀ 318 → **579 kHz**; R0 re-validates the corrected L |
| Target | 20 kV | **15 kV** | softened for headroom |

The r0.1 lever — "grow Cx toward C_R" — is exactly the fix applied. The island and tank are now
comparable vessels, so a kick transfers its energy efficiently instead of throttling into a much larger
tank.

## R0 — free ringdown vs analytic → **PASS (model + conical L confirmed)** `[OC]`

f₀ = **577.92 kHz** (zero-cross) vs analytic 577.92 kHz → **0.00 %**; τ = 0.275 ms → **0.01 %**.
Converged across 32/48/64 steps/period. The corrected **conical 79 µH** is confirmed against the
analytic f₀ (the cylindrical 169 µH would give 318 kHz — falsified). Energy-conservation gate
(E_inj = E_lossR + E_glow + E_crow + E_stored) holds **< 0.03 %** across all stages.

## R1 — driven, NO clamp → **reach confirmed; single-kick** `[OC]`

Energy to reach 15 kV on C_R = 960 pF is ½·C_R·V² = **108 mJ**.

| drive | E_kick | peak (Q=320 / 500 / 900) | predicted | accum |
|---|---|---|---|---|
| full | 171 mJ | 18.78 / 18.82 / 18.84 kV | 18.87 | ×0.99 |
| eased | 115 mJ | 15.40 / 15.43 / 15.45 kV | 15.48 | ×0.99 |

- **Reach: YES** — both drives clear 15 kV at all Q. Matches the energy-balance prediction (full
  ≈ 18.9 kV, eased ≈ 15.5 kV) in the full time-domain model.
- **Single-kick** (accumulation ×0.99 — still kick-and-decay at 600 Hz, spacing/τ = 9.5/6.1/3.4): the
  reach comes from one kick, so it is **Q-independent** and survives arbitrarily low Q (the kick peak
  is set by energy/C, not by ring build-up).
- **Headroom: +25 %** (full 18.8 vs 15 kV). Equivalently, the full drive can fall **37 %** (171 →
  108 mJ) and still hit 15 kV — the brief's "robust to Cx 37 % below design".

## R2 — soft glow governor only (sweep V_glow near 15 kV, both placements) `[OC]`

Full drive (un-clamped peak 18.9 kV) so the governor has work. Q = 500:

| V_glow | **void**: sustained / peak / sink | **island/upstream**: sustained / peak / sink |
|---|---|---|
| 13 kV | 18.0 kV / 18.0 / 52.8 W | 12.9 / **13.0** / 56.2 W |
| 15 kV | 18.2 kV / 18.2 / 35.3 W | 14.9 / **15.0** / 39.4 W |
| 16 kV | 18.4 kV / 18.4 / 25.8 W | 15.9 / **15.9** / 30.1 W |

Confirms the r0.1 finding: a **void** shunt bleeds energy but the **impulsive ~10 ns kick spikes the
peak past V_glow** (peak stays ~18 kV); the **upstream/island** placement caps the per-kick energy and
holds the **peak exactly at V_glow**. **Upstream is the peak-holding placement** (design-intent-lock
§6.3) and is used in R4.

## R3 — hard crowbar only (threshold near 15 kV) → **idle under nominal; sizes the sink** `[OC]`

- **Eased nominal drive (peak 15.5 kV):** crowbar **idle** (0 fires) for V_crowbar ≥ 16 kV; fires at
  15 kV (the 15.5 kV peak just exceeds it). A 16 kV setpoint is the right "just above target" choice.
- **Full-drive runaway:** the crowbar catches every kick, dumping **~168 mJ/event** (½·C_R·V_peak²,
  cumulative 840 mJ over the run), **~17 MW** in a 10 ns dump — the MW-class full-tank dump the lock
  §6.2 anticipates. It shorts the tank to ~0 each fire (a last-resort breaker, not a governor).

## R4 — two-tier combined (upstream governor + crowbar) → **holds ≤ 15 kV, crowbar idle** `[OC]`

Glow governor upstream at V_glow = 15 kV + crowbar at 16 kV:

| drive | peak | sustained | crowbar fires | governor sink | held |
|---|---|---|---|---|---|
| **full** (171 mJ) | 14.95 kV | 14.87 kV | 0 | **39.4 W** | ✔ (all Q) |
| **eased** (115 mJ) | 14.95 kV | 14.87 kV | 0 | **4.4 W** | ✔ (all Q) |

Both drive modes settle at ≤ 15 kV with the **governor doing the work and the crowbar idle**, at every
Q. *Contrast:* with a **void** governor at full drive the impulse peak (~18.9 kV) spikes past V_glow and
the crowbar is forced to fire every kick — confirming upstream placement is required to keep the crowbar
idle. **Sink load matches the brief's prediction** (~38 W full / few W eased).

## Headroom + Q-sensitivity `[OC]`

- **Headroom check:** the +25 % margin (18.9 vs 15 kV) survives the full model, not just the single-kick
  estimate — the governor parks the tank at 15 kV with that margin in hand.
- **Q-sweep (320/500/900):** reach is single-kick and therefore **Q-independent**; the hold (R4) is
  confirmed at all three Q. The conclusion survives the winding-pitch uncertainty.

---

## Verdict + recommendation

- **`TANK-HOLDS-15kV`** — reach ≥ 15 kV at all Q (both drives) **and** the two-tier upstream clamp holds
  ≤ 15 kV with the crowbar idle. The revised resonator + clamp is validated in the full time-domain
  model.
- **Drive recommendation:** **eased** (~4.4 W governor sink) over **full** (~39 W). 39 W into the void
  clamp is a real continuous load — if the void/structure cannot carry it this becomes `SINK-OVERSIZED`
  and mandates eased-drive; that is a **structural-sizing call** (deferred), so this run reports the
  number and recommends eased rather than declaring it.
- **Why it now works (hydraulic lens):** growing Cx 88 → 648 pF to match C_R 960 pF turns a small
  high-pressure cylinder dumping into a big low-pressure tank (throttling/charge-sharing loss) into two
  comparable vessels that transfer efficiently. The clamp is the relief valve regulating the terminal
  to a constant 15 kV.

## Next (brief §10 roadmap)

**S2 — pump↔tank coupling:** this run still takes E_kick as a parameter. The next brief extracts the
*real* per-cycle charge `shuttle_core` delivers to nodes 5–6 and drives the tank dynamically, validating
the **charge-sharing efficiency** (does the pump actually deliver the assumed ~115–171 mJ/kick?). Then
S3 (spark tier at real gap geometry), S4 (glow/void V_glow physics), S5 (full-system + dissipation).

## Reproduce
```
python3 sim/resonator_sim.py    # R0 self-test -> R1-R4 -> verdict; writes resonator_r2_traces.png + _sink.csv
```
