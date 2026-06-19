# Findings — S5: self-consistent operating point + dissipation

**Branch** `s5-operating-point` (off `main`, which carries the validated 789 pF tank + clamp + spark
verdicts). **Verdict:** **`OPERATING-POINT-STABLE`** — the pump↔tank↔clamp loop settles at a parked 15 kV
with **+12 % … +22 % margin** at the 6.0–6.5 mm fire gap, **V_fire 18.7–20.3 kV < 21 kV** (C1/C2 ceiling),
crowbar idle, across Q = 320/500/900. **+ `DIELECTRIC-Q-FLAG`** (garolite tanδ caps the AC ring Q, but the
v0.11 series-DC-hold topology is robust to it). The reach is now **pinned, not anchored**.

**What S5 retires:** the last *assumed* drive-side quantity — the absolute island fire voltage. S2 anchored
it at the 20 kV HV rail; S3 at a 17.2 kV real-gap strike and flagged "15.5 kV cold is tight." S5 lets the
**gap** set V_fire and solves the loop: V_fire is gap-set (18.7–20.3 kV at 6.0–6.5 mm), V_tank is clamp-set
(15 kV), and the tightness caveat is resolved by the recommended wider gap. With no consumer (TMD), this is
the **terminal drive-side characterization** — the metrics are hold power and cold-build efficiency, not a
delivered-power η.

**Scope / discipline:** consumer-only. The pump scale + island ledger come from the frozen `shuttle_core`
spark machinery (regression anchor z = 1.2033); the tank + two-tier clamp are the **unmodified**
`sim/resonator_sim.py`. S5 wraps a fixed-point solver around them. **Frozen empty-diff asserted**
(`shuttle_core.py` / `reference/` / `index.html` / `resonator_sim.py`). No DCCREG.

---

## §8 named checks (all PASS)

| # | check | result |
|---|---|---|
| 1 | f₀/Z₀ ring (guards 123 µH / 960 pF leaks) | f₀ = 635.5 kHz, Z₀ = 315 Ω ✓ |
| 2 | frozen empty-diff | clean (asserted at end) ✓ |
| 3 | regression `assert_ideal_identity` + anchor | z = 1.2033 ✓ |
| 4 | fixed-point convergence (held, reproducible) | v_peak = 15 kV, crowbar idle ✓ |
| 5 | ceiling guard V_fire < 21 kV | 18.7–20.3 kV ✓ |
| 6 | energy balance with losses < 0.1 % | E_inj = lossR + stored + crow + glow, rel 2.5e-4 ✓ |
| 7 | margin ≥ ~5 % at 6.0–6.5 mm | +12.2 % / +21.5 % ✓ |

## A1 — loop closure (V_fire set by the gap; tank settles at the clamp)

| gap | V_fire | E_M2 | V_cold | margin | <21 kV | v_peak | crowbar | held |
|---|---|---|---|---|---|---|---|---|
| 5.5 mm | 17.2 kV | 94 mJ | 15.4 kV | **+2.8 %** (tight) | yes | 14.95 kV | 0 | yes |
| **6.0 mm** | **18.7 kV** | 112 mJ | 16.8 kV | **+12.2 %** | yes | 14.95 kV | 0 | yes |
| **6.5 mm** | **20.3 kV** | 132 mJ | 18.2 kV | **+21.5 %** | yes | 14.95 kV | 0 | yes |

V_fire = 1.04 × (3 kV/mm × gap); E_M2 = η·½·Cx·V_fire² (η = 0.990); V_cold = √(2·E_M2/C_R) is the cold
single-kick tank peak the governor caps to 15 kV. **The fixed point is real:** the scale-invariant pump
boosts the island until the gap strikes (gap-set V_fire), and the governor parks the tank at 15 kV shedding
the surplus — no anchor needed. **The S3 "15.5 kV tight" caveat (5.5 mm, +2.8 %) is resolved by the 6.0–6.5 mm
gap (+12 … +22 %), with V_fire staying below the 21 kV C1/C2 ceiling at all gaps.**

## A2 — dissipation budget (settled point, 6.0 mm, Q = 500) — the new piece

| channel | power | note |
|---|---|---|
| **garolite dielectric** | **53.6 W** | tanδ ≈ 0.02 → Q_diel ≈ 50; **96 % of the ring loss** `[IR]` |
| copper R_ac | 2.2 W | Q_copper ≈ 1200 (coil-topology skin) `[IR]` |
| governor sink | 14.4 W | parked-hold shed (E_upstream / t_run) `[OC]` |
| arc (per fire × PRF) | 0.048 W | 0.08 mJ/fire × 600 Hz `[OC]` |
| windage | ≈ 0 | vacuum cavity — payoff of the vacuum design `[IR]` |
| glow/void | ≈ 0 | vacuum below Paschen minimum (S4-deferred) `[IR]` |
| bearing / mech | ~O(1 W) | order-of-magnitude only `[RH]` |

**`DIELECTRIC-Q-FLAG`.** Adding the dissipation budget (which every prior loss-free run lacked) surfaces a
real sensitivity: **garolite tanδ ≈ 0.02 → Q_diel ≈ 50**, so the dielectric is **96 %** of any AC ring loss
and would cap the working Q far below the swept 320–900 — a `DISSIPATION-LIMITED` result *for a parallel-ring
tank*. **But the v0.11 series-DC-hold topology (coil-topology / series-resonator, on `main`) is robust to it:**
the reach is a single impulsive kick (V_peak is Q-**independent** — set by energy, not Q), and at the DC hold
there is no AC voltage across C_R, so the dielectric AC loss → 0. The garolite dielectric therefore **does not
bind the operating point**; it only matters if the design relied on a high AC ring-Q. (Sweep tanδ if a high
ring-Q is ever needed; recommend a lower-loss septum — mica/ceramic — in that case.)

## A3 — operating point + efficiency

At 6.0 mm: V_fire = 18.7 kV (< 21 kV ✓), E_M2 = 112 mJ, **η_build = 0.795** (the 89 mJ that fills the tank to
15 kV ÷ the 112 mJ cold kick; the governor sheds the 23 mJ surplus). Across **Q = 320/500/900** the tank holds
v_peak ≈ 15 kV with the crowbar idle (the reach is Q-independent; only the ring loss scales). η_build is the
tank-charging step only; the whole-machine mechanical→tank efficiency is ≈ 0.45 (island-charging /
machine-energy-balance blocks, on `main`).

## A4 — build + hold dynamics

- **Cold build (M2 frame):** E_M2 = 112 mJ ≥ 89 mJ → **single-kick reach** (1 fire → 15 kV, 1.67 ms @ 600 Hz).
- **Cross-check (the multi-fire reality):** the series-DC-hold accumulation (coil-topology / series-resonator)
  builds in **~6 fires (≈ 10 ms)** — the M2-PARTIAL regime the island-charging co-sim pinned. S5's M2 frame is
  the optimistic single-kick bound; the realistic sourced delivery (~14 mJ/fire) gives the 6-fire build. Both
  reach 15 kV; the difference is the per-fire delivery model (full M2 dump vs rail-limited mid-collapse fire).
- **Parked hold:** the governor sheds the pump's over-delivery indefinitely; the crowbar stays idle (A1/A3
  held = yes at every gap and Q). **Hold power ≈ 14 W (series-DC-hold)** vs ≈ 70 W if the parallel ring had to
  be re-established each cycle — the series topology is the one that makes the hold cheap.

## Verdict + roadmap

**`OPERATING-POINT-STABLE`** — the reach is pinned: V_fire gap-set (18.7–20.3 kV, < 21 kV), V_tank clamp-set
(15 kV), margin +12 … +22 % at the recommended 6.0–6.5 mm gap, crowbar idle, energy balanced. The "15.5 kV
tight" caveat is retired. **`+ DIELECTRIC-Q-FLAG`** noted (non-binding for the series-DC-hold design; would
bind a parallel-ring tank). Remaining (TMD-gated, not S5 prerequisites): **S4** vacuum-gap glow / hemisphere
edge-flashover (geometry now in hand), then **thermal** (temperature rise from this dissipation budget). S5's
settled operating point is the locked anchor for both.

## Deliverables

`sim/s5_operating_point.py` (consumer-only fixed-point wrapper + A0–A4 + §8 checks) · this findings doc ·
`s5_operating_point.csv` · `s5_operating_margin.png` (margin vs gap) · `s5_dissipation_budget.png`
(per-channel power). Frozen empty-diff asserted. **Not merged.**
