# s2-coupling — findings (r0.1): **PUMP-DELIVERS-EASED-ONLY** (M2) / **PUMP-UNDERDELIVERS** (M1)

**Verdict (map-dependent):** the real pump's per-cycle delivery to the 5–6 tank **brackets the 108 mJ
reach floor**, so the coupling-map choice flips the reach. Under **M2 (island-dump**, the migration-doc
reading) the pump delivers **124.7 mJ → `PUMP-DELIVERS-EASED-ONLY`** (tank reaches 16.1 kV, the two-tier
clamp holds 15 kV, crowbar idle). Under **M1 (rail-increment**, conservative) it delivers **90.2 mJ →
`PUMP-UNDERDELIVERS`** (tank reaches only 13.7 kV). **Working conclusion: `PUMP-DELIVERS-EASED-ONLY`** —
the eased reach is real, the ~6 % margin is the true ceiling, and the full-drive +25 % headroom was
**paper**. The result is map- *and* scale-sensitive (the ideal pump is scale-invariant; the absolute
island fire voltage is the swing variable).

Branch `s2-pump-tank-coupling` (off `resonator-sim-r2`). **Read-only consumer** of the frozen pump
(`sim/s2_coupling.py`); `shuttle_core.py` / `reference/` / `index.html` **byte-identical** (asserted).
Drives the **unmodified** `sim/resonator_sim.py` tank. Not merged. Tiers: `[OC]` derived/standard
charge accounting · `[IR]` coupling/scale choice · `[RH]` open.

---

## §8 named checks (all PASS)

| # | check | result |
|---|---|---|
| 1 | ring f₀/Z₀ (guards stale 123/169 µH) | **577.9 kHz / 287 Ω** PASS |
| 2 | G2 preset loaded == expect (tol 0) | PASS |
| 3 | G0 anchor 1.2033 ± 0.03 at G2 | **inj 1.20327** PASS |
| 4 | island ledger balanced at grown Cx | **drift 1.2e-13** PASS (no LEDGER-BREAK) |
| 5 | `shuttle_core`/`reference`/`index.html` empty diff | PASS |
| 6 | **reach gate** (E_deliver vs 108/115/171 mJ) | **map-dependent — see below** |
| 7 | energy conservation across the coupled chain | **< 0.05 %** PASS |

## Spine: two un-propagated corrections, now run through the producer (brief §1)

The r2 `TANK-HOLDS-15kV` was proven on the *tank* side at the grown geometry; the *pump* was still
confirmed only at the old 88 pF bucket. New `presets/G2-geometry-r2.json` propagates the corrections
(island Cx 4/88→**8/648 pF**, C_R 1477→**960 pF** record-only, L_R **79 µH** provenance; C1/C2 + Ca/Cb
unchanged; G1 not mutated). The ring uses L_R = 79 µH (conical); the §2.1 f₀/Z₀ self-test catches any
123/169 µH leak.

## G0 — re-anchor at G2 → **authorised** `[OC]`

Injection VERIFIED (reset→galvanic **1.20327** = Z_BASELINE); G2 galvanic ceiling **1.334** — *unchanged
from G1*, because `galvanic_z` depends only on C1/C2/Ca/Cb/Cpar (the grown Cx and revised C_R do not
enter the degenerate anchor). The brief-literal Ca/Cb→large→1.000 (transfer caps short the pump), the
same placeholder-ceiling subtlety logged in geom-shuttle G0.

## P1 — pump at the grown 648 pF bucket → **pumps HARDER, clean ledger** `[OC]`

| | G1 (88 pF) | **G2 (648 pF)** |
|---|---|---|
| z_shuttle | 1.2077 | **1.3072** |
| above unity | — | **+48 % vs G1** |
| island ledger drift | — | **1.2e-13** (< 1e-6) |
| boost_ratio | 7.3 | 40.5 |

Growing the bucket **helps** the pump (z 1.208→1.307, still below the 1.334 ceiling) and the 648 pF
island is a **clean shuttle** (no `LEDGER-BREAK`). So the grown geometry is sound on the pump side.

## X1 — extract real delivery (BOTH maps, brief §4/§5) `[OC]/[IR]`

**Scale-fix `[IR]`:** the ideal pump is **scale-invariant** (the eigenvector grows by z each cycle with
no absolute volts), so the absolute delivery is set by the operating-point anchor, *not* by the pump.
Anchor: the firing island potential = the design rail **V_HV = 20 kV** (shuttle_core's locked HV).

| map | formula | E_deliver | cold-tank peak | class |
|---|---|---|---|---|
| **M2 island-dump** | η·½·Cx·V_isl², η = 4·Cx·C_R/(Cx+C_R)² = **0.962** | **124.7 mJ** | 16.1 kV | **EASED-ONLY** |
| **M1 rail-increment** | (1−1/z)·C_R·V_rail², (1−1/z) = 0.235 | **90.2 mJ** | 13.7 kV | **UNDERDELIVERS** |

The maps **bracket the 108 mJ floor** — the coupling choice flips reach. M2's η = 96 % is the
geometry-confirmed peak LC transfer of the 648/960 cap pair (the r2 "equal-vessel" claim, validated).
**Boost sensitivity (M2):** island fire 18 / 20 / 23 kV → **101 / 125 / 165 mJ** — the absolute island
fire voltage is the swing variable (below ~18.6 kV M2 also under-delivers; at 23 kV it nears full).

## C1 — drive the unmodified tank with the real delivery → `[OC]`

| map | E_deliver | tank (no clamp) | clamped peak | crowbar | governor sink | result |
|---|---|---|---|---|---|---|
| M2 | 124.7 mJ | 16.1 kV (reaches) | 14.95 kV | 0 | **10.5 W** | **HOLDS 15 kV** |
| M1 | 90.2 mJ | 13.7 kV (short) | 13.67 kV | 0 | 0 W | **under-reaches** |

Held across Q = 320/500/900 for M2; energy conservation across the coupled chain < 0.05 %. The M2
governor sink (10.5 W) is well below the r2 full-drive 39 W — consistent with "eased-only".

---

## Verdict + routing to TMD

- **Working verdict: `PUMP-DELIVERS-EASED-ONLY`** (M2, island-dump). Eased reach is real (124.7 mJ >
  115 mJ), the ~6 % margin is the ceiling, full-drive headroom was paper. **M1 (rail-increment) is the
  conservative bound** — `PUMP-UNDERDELIVERS` (90 mJ). The honest headline is that reach is **map- and
  scale-sensitive**, not a clean pass.
- **For TMD:** (1) confirm **M2 vs M1** as the physical coupling (the migration doc and the hydraulic
  pump-stroke picture favour M2; the rail-collapse in the producer makes M1 defensible). (2) The
  **absolute island fire voltage** (here anchored at the 20 kV HV) is the dominant remaining
  uncertainty — the scale-invariant pump cannot self-fix it; pinning it needs the **self-consistent
  pump↔tank↔clamp operating point (S5 co-sim)**. (3) Recommend the **eased drive** (already the r2
  recommendation; ~10 W sink under M2).
- **Resolves the r2 conditionality:** `TANK-HOLDS-15kV` **stands** under M2 / eased drive, and is
  **conditional (unmet)** under M1. Not a clean confirmation of the full-drive headroom.

## Out of scope / next

S3 spark tier at real gaps (gated on DXF gap hardware), S4 glow/void V_glow physics, **S5 full
integration + dissipation** — which is also where the absolute-scale operating point gets pinned
self-consistently, resolving the M1/M2 + scale sensitivity this run surfaces.

## Reproduce
```
python3 sim/s2_coupling.py    # self-tests -> G0 -> P1 -> X1 (both maps) -> C1 -> verdict; writes PNG + CSV
```
