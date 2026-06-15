# resonator-sim — findings (r0.1): **TANK-UNDERDRIVEN**

**Verdict:** `TANK-UNDERDRIVEN` — driven by the pump's physically-available per-kick energy (~18 mJ from
the 88 pF island), the live 5–6 tank reaches only **~5 kV**, not 20 kV. Reaching 20 kV on the **C_R =
1477 pF** tank needs **~295 mJ per kick** (~17× the anchor), i.e. the 88 pF island would have to sit at
**~82 kV** — physically implausible against a 20 kV rail. With τ ≈ 0.5 ms and kicks 1.67 ms apart (both
branches, 600 Hz), the tank **decays between kicks** (accumulation ×1.0–1.01) — it is **kick-and-decay,
not a resonant accumulator**. This is a design-direction deliverable, not a failure: it names the lever
(grow Cx toward C_R, raise PRF so spacing < τ, or add resonant synchronisation). **Separately, the
two-tier clamp architecture is validated** at a hypothetical adequate drive (R4 holds ≤ 20 kV with the
glow governing and the crowbar idle, all Q) — so the architecture is sound *if* the drive lever is
fixed.

Branch `resonator-sim` (off `geom-shuttle-gate`). **Standalone** time-domain RLC + clamp model;
imports **neither** `shuttle_core.py`, `reference/doubler_core.py`, nor `index.html` (every prior run
shorted this tank, so the frozen quasi-static solver cannot simulate it). numpy + matplotlib only
(hand-rolled RK4; scipy absent, system non-stiff with the crowbar as a discrete latch). Not merged.
Tiers: `[OC]` physics/derived-from-spec · `[IR]` modelling/reporting · `[RH]` open.

---

## Inputs (brief §2 — tank from geometry + materials)

| Quantity | Value | Note |
|---|---|---|
| L_R | 169 µH | 36-turn copper solenoid (Wheeler); supersedes the code's `L_RES=123 µH` (commutator-design.md §2) |
| C_R | 1477 pF | rotor–rotor across 12 mm mica (DXF r0.6) |
| f₀ | **318.56 kHz** | 1/(2π√(LC)) — brief's ≈319 kHz |
| Q | 320 / 500 / 900 | swept; R_loss = ω₀L_R/Q (0.68 Ω @ Q=500), Z₀=√(L/C)≈338 Ω |
| τ | 2Q/ω₀ ≈ 0.50 ms @ Q=500 | ring decay |
| **Drive** | E_kick swept {5,20,50,100,300} mJ | `shuttle_core` shorts 5–6 → no tank-side delivery; anchor ½·88 pF·(20 kV)² ≈ **17.6 mJ** |
| Kick rate | 600 Hz | two branches at f_cycle=rpm/10=300 Hz, offset ½ branch-cycle |

## R0 — free ringdown vs analytic → **PASS (model authorised)** `[OC]`

| steps/period | f₀ (zero-cross) | f₀ (FFT) | τ |
|---|---|---|---|
| 32 | 318.553 kHz | 318.569 kHz | 0.500 ms |
| 64 | 318.556 kHz | 318.574 kHz | 0.500 ms |

f₀ error **0.00 %** (≤1 %), τ error **0.01 %** (≤3 %) vs analytic (f₀=318.557 kHz, τ=2Q/ω₀=0.500 ms).
The model reproduces the linear RLC to machine-level accuracy and is converged in dt. A global
**energy-conservation gate** (E_injected = E_lossR + E_glow + E_crowbar + E_stored) holds to **< 0.1 %**
across every R-stage.

## R1 — driven, NO clamp → **kick-and-decay; reach NO** `[OC]`

| E_kick | envelope (Q=500) | 1 cold kick | accumulation |
|---|---|---|---|
| 5 mJ | 2.60 kV | 2.60 kV | ×1.00 |
| **20 mJ** (≈anchor) | **5.19 kV** | 5.20 kV | ×1.00 |
| 50 mJ | 8.21 kV | 8.23 kV | ×1.00 |
| 100 mJ | 11.61 kV | 11.64 kV | ×1.00 |
| 300 mJ | 20.10 kV | 20.16 kV | ×1.00 |

- **Mechanism = kick-and-decay.** Combined kick spacing / τ = **3.34** at Q=500 (residual 3.6 %) and
  **1.85** at Q=900 (residual 15.7 %) — the tank is essentially dead before the next kick, so the
  steady envelope equals a *single* cold-kick height (accumulation ×1.00–1.01). It is **not** a
  resonant accumulator.
- **Reach.** At the physical ~18 mJ the tank reaches **~5 kV**. 20 kV needs **295 mJ single-kick**
  (½·C_R·V²) — **~17× the anchor**; to source 295 mJ the 88 pF island would need **~82 kV** (vs the
  20 kV rail). Accumulation-adjusted at Q=900 it is still ~289 mJ. **Reach: NO** at any plausible drive.

## R2 — soft glow governor only (sweep V_glow, both placements) `[OC]`

Drive = a hypothetical **500 mJ** (overshoots ~26 kV un-clamped) so the governor has work; the physical
drive is underdriven (R1).

| V_glow | **void**: sustained / peak / Q-spoil | **island**: sustained / peak |
|---|---|---|
| 14 kV | 22.5 / 24.4 kV / 2.22 | **13.96 / 14.0 kV** |
| 18 kV | 23.4 / 24.9 kV / 0.96 | **17.95 / 18.0 kV** |
| 22 kV | 24.4 / 25.4 kV / 0.33 | **21.94 / 21.9 kV** |

**Placement is decisive.** The **void** shunt bleeds large energy (Q-spoil E_glow/E_R up to 2.2,
shaving 414 mJ/event) but **cannot prevent the per-kick voltage spike** — the impulsive ~10 ns spark
slams the tank past V_glow before a µs-scale shunt can respond, so the peak stays ~24–25 kV. The
**island/upstream** placement caps the per-kick *energy* before injection and holds the peak **exactly
at V_glow**. This favours upstream placement, matching design-intent-lock **§6.3** ("soft governor best
placed upstream so the tank never climbs to the crowbar threshold").

## R3 — hard crowbar only (sweep V_crowbar; sink sizing) `[OC]`

- **Nominal (~18 mJ) drive:** crowbar fires **0** at all Q (envelope ~5 kV ≪ 22 kV) — idle, as a
  last-resort backstop should be.
- **Over-drive (500 mJ) drive:** fires every kick, dumping **~491 mJ/event** (cumulative 2946 mJ over
  the run), ~**49 MW** in a 10 ns dump. **Threshold-independent** (20/22/24 kV identical): the
  impulsive spark spikes past every tank-side setpoint instantly, so the crowbar dumps the full
  excursion ≈ ½·C_R·V_peak². **Sink sizing:** ~0.5 J/event at MW-peak — the "MW-class, far larger than
  the island dump" the lock **§6.2** anticipates. (Full per-event/cumulative table in
  `resonator_sink_energy.csv`.)

## R4 — two-tier combined → **holds ≤ 20 kV, crowbar idle** `[OC]`

| Q | envelope | crowbar fires | held |
|---|---|---|---|
| 320 | 19.73 kV | 0 | ✔ |
| 500 | 19.77 kV | 0 | ✔ |
| 900 | 20.03 kV | 0 | ✔ |

At a design drive that just reaches 20 kV (300 mJ), the glow governor (void, 18 kV) holds the sustained
envelope ≤ 20 kV and the crowbar (22 kV) stays **idle** at all Q. **The two-tier architecture works** —
the open question is the *drive*, not the clamp.

## Q-sensitivity → **conclusion survives** `[OC]`

The reach conclusion is invariant across Q = 320 / 500 / 900: accumulation is ×1.00 / ×1.00 / ×1.01 —
even tripling Q (τ 0.32→0.90 ms) leaves spacing/τ = 5.2 / 3.3 / 1.9, never < 1, so the tank never
crosses into resonant accumulation. Higher Q **cannot** close the 17× reach gap.

---

## Verdict set + levers

- **`TANK-UNDERDRIVEN`** (headline): physical drive reaches ~5 kV; 20 kV needs ~17× the per-kick
  energy. **Levers, in order of leverage:** (1) **grow Cx toward C_R (≈1477 pF)** so the island matches
  the tank — then ½·C_R·(20 kV)² is delivered per kick; (2) **raise PRF so kick-spacing < τ** for
  resonant build (needs ~11× the 600 Hz, i.e. ~6.5 kHz, at fixed Q) ; (3) a **resonant-sync** pump→tank
  coupling. Accumulation/Q alone cannot close the gap.
- **Clamp architecture: validated** (secondary, positive) — at an adequate drive the two-tier clamp
  holds ≤ 20 kV with the crowbar idle; **upstream/island glow placement** is the one that caps the peak
  (a tank-side shunt or crowbar cannot stop the impulsive spike). Recommend the soft governor live
  upstream (lock §6.3), with the void clamp/crowbar as the hard backstop sized for the **~0.5 J / MW**
  full-tank dump (lock §6.2, deferred structural sizing).

A negative headline is the deliverable; nothing was retuned to force a positive.

## Reproduce
```
python3 resonator_sim.py     # R0 self-test -> R1-R4 -> verdict; writes resonator_traces.png + _sink_energy.csv
```
