# shuttle-fullsim — findings (rev 0.3): **SHUTTLE-PUMP-CONFIRMED**

**Verdict:** `SHUTTLE-PUMP-CONFIRMED` — the flying-bucket shuttle topology (frozen charge
direction **1→3 / 4→2**) pumps at the ideal-switch tier. The degenerate-limit anchor passes
(z = 1.2033 = `ANCHORS["device"]`), the shuttle grows exponentially with **z_shuttle ≈ 1.19–1.20 > 1**,
island charge ledgers balance to machine precision (no secular drift), the per-branch direction
matches the duty-sign CSV (`Q_D3 > 0` into node 3 every cycle), the bucket budget is feasible across
most of the swept region, and there is a finite `pVbkFire` band with `SG3a < SG3b`. The deliberate
drain-back case degrades the pump as required. Consequence: topology validated at the ideal-switch
tier; the spark-derating pass and the bootstrap gate are next; the event-angle CSV is exported for
the phase-plate DXF.

Branch `shuttle-fullsim` (from `main` `9136624`). `reference/doubler_core.py` **untouched** (empty
diff; mirror self-test still FAITHFUL); `index.html` untouched. Not merged to `main`.

Producer/consumer discipline: `shuttle_core.py` is a **new producer** consuming only the frozen
scalar device-point values, `solve_doubler4`, `ANCHORS`, `run_self_test`. The timing diagram and the
event-angle CSV are pure consumers of `shuttle_core` output. `[OC]`

---

## 1. Anchor test — PASS (authorises the producer; brief §2.3)

Shuttles replaced by ideal galvanic diodes in the **1→3 / 4→2** direction, LR shorted (rail
collapsed). Independent re-implementation of the frozen two-phase doubler at the device point:

| degenerate limit | z | result |
|---|---|---|
| galvanic **1→3 / 4→2** (frozen direction) | **1.2033** | **PASS** (= `ANCHORS["device"]` 1.203 ± 0.03) |
| galvanic 3→1 / 2→4 (reversed) — rev 0.2 | 1.000 | (fails; documented in the rev 0.2 gate report) |

`anchor_test()` is called first in `run_campaign()` and asserted before any campaign step runs. `[OC]`

## 2. Startup & steady state (brief §4.2–4.3)

- **cycles-to-steady = 8** (per-cycle pump ratio converged within 1% over 3 consecutive cycles).
- **z_shuttle ≈ 1.198** (mean over the converged window) / **1.189** (median over 40 post-burn
  cycles) — exponential pump, below the **1.2033** galvanic ceiling as expected for a finite bucket.
- **20 steady cycles captured**: V1…V8, signed branch charges, island potentials Q7/Q8.
- **Per-branch direction = (1→3, 4→2)** every captured cycle — matches the duty-sign CSV. `[OC]`

## 3. Conservation ledgers — all pass (hard-fail; brief §3)

| ledger | check | result |
|---|---|---|
| island charge (per branch, per cycle) | `load_in == fire_out` | max rel-drift **3.9 × 10⁻¹⁴** |
| drain-back island balance | same, extended-window run | drift **6.8 × 10⁻¹⁵** |
| field energy | `field_energy()` exposed; Σ½C·ΔV² tracked across the sweeps | consistent |

`assert_island_ledger()` raises on any branch/cycle exceeding 1 × 10⁻⁶ relative drift. No violations
on any delivered run. `[OC]`

## 4. Bucket budget — feasible region (brief §4.4)

Per-cycle throughput vs the **reused** duty-sign demand (`d3_duty_sign_events.csv`, steady-state
`Q_D3` growth ratio = **1.2033**, sign **+** into node 3 — *not* re-derived). Sweep of `Cx_max` ×
load-station angle (`load_frac`); `*` = feasible (z within 0.05 of the 1.2033 ceiling, forward
transfer):

| Cx_max (pF) | boost | lf 0.0 | 0.2 | 0.4 | 0.6 | 0.8 |
|---:|---:|---|---|---|---|---|
| 200 | 2.9 | 1.142 | 1.136 | 1.128 | 1.118 | 1.105 |
| 400 | 5.9 | **1.167** | **1.161** | 1.153 | 1.141 | 1.122 |
| 800 | 11.8 | **1.183** | **1.179** | **1.173** | **1.163** | 1.144 |
| 1200 | 17.6 | **1.189** | **1.186** | **1.182** | **1.174** | **1.156** |
| 2000 | 29.4 | **1.195** | **1.193** | **1.190** | **1.184** | **1.170** |
| 4000 | 58.8 | **1.199** | **1.198** | **1.196** | **1.193** | **1.184** |
| 8000 | 117.6 | **1.201** | **1.201** | **1.200** | **1.198** | **1.193** |

**26 / 35 cells feasible.** z rises **monotonically toward the galvanic ceiling 1.2033** as the boost
ratio grows (Cx_max/(Cx_min+pCboss+strays)) and falls monotonically as the load station moves later
(smaller bucket). Feasible region: boost ≳ 6 at early load stations; the whole high-boost row is
feasible at every station. `[OC]`

## 5. `pVbkFire` sensitivity & emergent δ (brief §4.5)

Threshold is scale-invariant (`ov > pVbkFire · drive`); an absolute strike level is ill-defined
against the unbounded-growth eigenvector, so `pVbkFire` is a fraction of the per-cycle load drive.
`[IR — normalisation]`

| pVbkFire | z | fired | δ (SG3b − SG1) |
|---:|---|---|---|
| 0.0 – 1.0 | 1.189 | yes | 0.218 |
| 2.0 | 1.189 | yes | 0.308 |
| 5.0 | 1.189 | yes | 0.368 |
| 9.0 | 1.189 | yes | 0.383 |
| 15.0 | 1.189 | yes | 0.390 |
| ≥ 20 | — | **no** | — (strike never reached in-window) |

**Fire band = pVbkFire ∈ [0, ~15]**; inside it δ grows **monotonically** (0.218 → 0.390 sector) and
the dump lands inside the collapse window. **Outside the band** (pVbkFire ≳ 20) the boosted
overvoltage never crosses threshold within the collapse window → **no strike → island charge
accumulates** cycle-on-cycle (the `docs/commutator-design.md` C5 floating-bar accumulation failure;
needs the weak bleed) and no forward transfer occurs. That is the named binding failure outside the
band. `[OC]/[IR]`

## 6. Drain-back validation (deliberate failure; brief §3)

Quench rule: normally `SG3a` opens on the plateau so the island is isolated through the collapse and
the boost raises V7. The validation case (`extend_into_collapse = True`) holds `SG3a` **closed into
the collapse** — charge then drains **back to the source** as Cx shrinks, depleting the bucket before
the forward fire:

| case | z | island ledger |
|---|---|---|
| normal (quench on plateau) | **1.189** | balanced |
| **drain-back** (window into collapse) | **1.087** | balanced (drift 7 × 10⁻¹⁵) |

The pump **degrades demonstrably** (1.189 → 1.087, toward the no-pump floor) while charge is still
conserved — the failure mode is present and reproducible, not absent. `[IR]`

## 7. Timing diagram & event-angle export (brief §5)

`shuttle_timing_from_solver.py` → `shuttle_timing_from_solver.png` (three θ-aligned panels:
C1/C2/Cx3/Cx4 with windows, V1–V4 + islands V7/V8, cumulative per-branch charge ledger). All six
event stations are marked at their **simulated** angles; self-assertions (event count = 6,
SG3a < SG3b, island-ledger balance, per-branch direction sign) pass loudly.

Simulated event angles (one sector = 60° of C1 electrical):

| event | θ (sector) | θ (deg/60) | window | signed Q | direction |
|---|---:|---:|---|---:|---|
| SG1 | 0.050 | 3.0° | 0.050–0.120 | — | 1→3 (return) |
| SG3a | 0.120 | 7.2° | 0.120–0.260 | +47.7 | 1→3 (load) |
| SG3b | 0.268 | 16.1° | 0.260–0.440 | +47.7 | 1→3 (fire) |
| SG2 | 0.550 | 33.0° | 0.550–0.620 | — | 4→2 (return) |
| SG4a | 0.620 | 37.2° | 0.620–0.760 | +52.0 | 4→2 (load) |
| SG4b | 0.768 | 46.1° | 0.760–0.940 | +52.0 | 4→2 (fire) |

**Emergent SG1↔SG3b relation (an output, not asserted):** SG1 **leads** SG3b by Δθ = **0.218**
sector (≈ 13°); SG2 leads SG4b by Δθ = **0.217**. Exported to `shuttle_event_angles.csv` (event, θ,
window, signed charge, branch direction) on this CONFIRMED verdict for the phase-plate DXF
relative-angle check. `[OC]`

## 8. Constraints honoured

- `reference/doubler_core.py` untouched (empty diff); mirror self-test still FAITHFUL (device z =
  1.2033). `index.html` untouched (out of scope).
- `L_RES` = `L1` ≈ **123 µH** cited (symbol + value + section) from `docs/commutator-design.md` §2;
  at PRF it is the near-short on the 5–6 ring, logged but **not** part of the charge-pump verdict.
- Symbol hygiene: rotor phase `θ`, gap `g`, `p`-prefixed new params (`pCboss`, `pVbkFire`); no bare
  `d`. Epistemic tags `[OC]/[IR]` throughout.
- Direction **1→3 / 4→2** per rev 0.3 (anchor evidence + duty-sign CSV); timing anchored at C1/C2
  **max**.
- Branch left for TMD review; **not merged** to `main`.

## 9. What this does and does not establish

- **Establishes [OC]:** at the ideal-switch tier the flying-bucket shuttle reproduces the doubler's
  regenerative 1→3 / 4→2 duty, pumps (z > 1), conserves island charge exactly, and approaches the
  galvanic z = 1.2033 ceiling as the bucket boost grows. The committed escape from
  `XCAP-RATCHET-BLOCKED` is viable.
- **Does not establish (next gates, out of scope here):** spark/strike derating (real `pVbkFire` in
  volts, arc duration, quench margin vs the ~1.7 ms favourable half), the bootstrap two-threshold
  startup loop, loss/leakage and fringing, and HV insulation coordination. The island-accumulation
  failure outside the fire band confirms the C5 weak-bleed requirement is real.
