# s2recheck-s3 — findings (v0.10): **REACH-CONFIRMED-789 · STRIKE-CONFIRMED · QUENCH-OK · BACKSTOP-CLEAN · INTEGRATED-REACH-OK**

**Verdict:** the v0.10 freeze (C_R 960→**789 pF**, 12 mm disc) **validates end-to-end**. The S2 coupling
reach **re-confirms on the new 789 pF tank** (entry gate), and the S3 spark tier at the real mm-scale
gaps **strikes inside the fire window, quenches within the favourable half, contains misfires, and the
integrated pump→gap→tank→clamp chain holds 15 kV with the crowbar idle**. The one honest caveat: at the
*real* fire-gap strike (17.2 kV island, not the 20 kV HV anchor) the integrated cold-tank reach is
**15.5 kV — tight**; opening the drafted 5.5 mm gap toward ~6 mm restores comfortable margin while
staying below the 21 kV C1/C2 flashover ceiling.

Branch `s2recheck-s3-spark` (off `freeze-v0.10`). **Consumer only:** reuses the frozen `shuttle_core`
spark machinery and drives the standalone `resonator_sim` tank at C_R=789 pF; `shuttle_core` /
`reference/` / `index.html` **byte-identical** (asserted). **Regression-gated** (C0:
`assert_ideal_identity` + T0a/T0b/T0c). The spark sim is **parametric** (freeze §5 spec); the **BS3/BS4
DXF markers are still TODO** (drafting), flagged in B3. Not merged. Tiers: `[OC]` · `[IR]` · `[RH]`.

---

## Gates (all PASS)

| gate | result |
|---|---|
| ring f₀/Z₀ self-test | **637.5 kHz / 316 Ω** (stale 123 µH→463, 960 pF→578 kHz would fail) |
| G3 preset loaded == expect (tol 0) | PASS (Cx 648, C_R 789, C1/C2 16/280, Ca/Cb 309) |
| C0 regression (`assert_ideal_identity` + T0a/T0b/T0c) | anchor **1.2033**, ideal **1.1894**, ledger drift **4.6e-14** |
| frozen empty-diff (`shuttle_core`/`reference`/`index.html`) | PASS (checked twice) |

## B1 — S2 reach re-confirm @789 pF (entry gate) → **REACH-CONFIRMED-789** `[OC]`

Smaller C_R is *favourable*: η = 4·Cx·C_R/(Cx+C_R)² = **0.990** (was 0.962 @960), floor =
½·C_R·15kV² = **89 mJ** (was 108). Island at the 20 kV HV anchor → E_M2 = **128 mJ** → cold-tank peak
**18.0 kV** → clears 15 kV. Driving the unmodified `resonator_sim` tank (island governor 15 kV +
crowbar 16 kV) holds 15 kV at all Q (Q=500: clamped 14.95 kV, crowbar 0, sink 24.7 W, conservation
+0.03 %). **The 789 pF tank is easier than the 960 pF S2 run** (lower floor, better match). S3 opens.

## B2 — fire-gap strike (12 mm spheres, 3 kV/mm) → **STRIKE-CONFIRMED** `[OC]`

| spacing | strike | island fire (1.04×) | window 16.6–21 kV |
|---|---|---|---|
| 5.3 mm | 15.9 kV | 16.5 kV | **UNDER** (just below) |
| **5.5 mm (drafted)** | 16.5 kV | **17.2 kV** | ✔ in window |
| 5.8 mm | 17.4 kV | 18.1 kV | ✔ |
| 6.0 mm | 18.0 kV | 18.7 kV | ✔ |
| 6.4 mm | 19.2 kV | 20.0 kV | ✔ |

The drafted 5.5 mm SG3b/SG4b gap strikes the island at **17.2 kV**, inside the 16.6–21 kV window — but
near the lower (16.6 kV reach-floor) edge. (Bench-calibrate the 3 kV/mm gradient vs IEC 60052;
`shuttle_core.paschen_strike` is the 0.5 mm small-gap Paschen-min regime and is deliberately not used
for these kV-scale sphere gaps.)

## B3 — arc quench + backstop containment → **QUENCH-OK · BACKSTOP-CLEAN** `[OC]/[IR]`

- **Quench:** the arc recovery τ_rec (opt 10 µs / mid 100 µs / pess 1 ms) is ≪ the **1.67 ms favourable
  half** at every corner → the arc extinguishes inside the favourable half (no back-conduction).
- **Backstop:** the frozen `C2_backstop` returns **BACKSTOP-CLEAN** (T2a no false-positives, T2b catches
  single+double induced misses, island bounded **0.71× single-bucket ≤ 1.05**). The 0.6×-strike ratio
  and the ≤1.05× containment bound are **scale-free**, so the result carries to the v0.10 16.5 kV strike.
- **10 ns local-loop dump:** the fire is an impulse spanning f₀ = 637 kHz (~1.6 µs period) → the gap
  dumps the bucket in ≪ 1 ring period (the real local-loop L is an S3-deferred / out-of-scope item).
- **`[RH]` flag:** the **BS3/BS4 DXF markers (19°/49°, outer ~r350–380) are still TODO** — the sim runs
  on the freeze §5 spec (0.6× strike); the drafting is the remaining gap-geometry task.

## B4 — integrated reach at the REAL strike → **INTEGRATED-REACH-OK** `[OC]`

Coupling pump (z 1.307) → fire gap → tank (789 pF / 79 µH) → clamp, **at the real fire-gap strike**
(island **17.2 kV**, not the 20 kV HV anchor): E_deliver = η·½·Cx·17.2kV² = **94 mJ** → cold-tank peak
**15.5 kV** → clears the 15 kV floor (89 mJ). The two-tier clamp holds 15 kV with the crowbar idle at all
Q (Q=500: clamped 14.95 kV, sink **3.6 W**, conservation +0.03 %).

**Honest margin note `[IR]`:** 15.5 kV cold is **tight** vs 15 kV — the drafted 5.5 mm gap sits at the
low edge of the window. **Recommend opening SG3b/SG4b toward ~6.0–6.5 mm** (island 18–20 kV → 110–130 mJ
→ cold peak 16.8–18.2 kV) for comfortable reach margin, staying below the **21 kV C1/C2 flashover**
ceiling (max spacing ~6.7 mm). The governor sheds the surplus (sink rises modestly), the crowbar stays
idle.

> **S5 update (routed to TMD, `s5-operating-point`):** this "15.5 kV tight" caveat is now **RESOLVED and
> PINNED** — closing the pump↔tank↔clamp loop self-consistently gives `OPERATING-POINT-STABLE` with
> **+12.2 % / +21.5 % margin at the 6.0 / 6.5 mm gap** (V_fire 18.7 / 20.3 kV, both < 21 kV C1/C2), crowbar
> idle, across Q = 320/500/900. The fire voltage is gap-set, not anchored. S5 also flags `DIELECTRIC-Q-FLAG`
> (garolite tanδ caps the AC ring-Q, but the series-DC-hold topology is robust to it).

---

## Verdict set + design output

- **`REACH-CONFIRMED-789`** (entry gate met) · **`STRIKE-CONFIRMED`** · **`QUENCH-OK`** ·
  **`BACKSTOP-CLEAN`** · **integrated chain clears 15 kV** — the v0.10 design is validated in simulation.
- **Design recommendation:** widen the drafted SG3b/SG4b fire gap from 5.5 → ~6.0–6.5 mm for reach
  margin (the 5.5 mm point clears but tight). Draft the **BS3/BS4 backstop markers** into the DXF to
  close the last gap-geometry TODO (the sim already validates them parametrically at 0.6× strike).
- **Closes the S2 fire-gap conditionality at 789 pF:** the real fire gap lands the island at 17.2 kV →
  94 mJ > 89 mJ floor → reach confirmed with margin (the S2 result was conditional on the island fire
  voltage; the drafted gap supplies it).

## Out of scope / next
S4 glow/void V_glow physics; S5 full dissipation/thermal; rotor RPM/material; the real local-loop L
(10 ns dump); the BS3/BS4 DXF drafting.

## Reproduce
```
python3 sim/s2recheck_s3_spark.py   # self-tests + C0 -> B1 (reach) -> B2/B3/B4 (spark) -> verdicts; writes PNG + CSV
```
