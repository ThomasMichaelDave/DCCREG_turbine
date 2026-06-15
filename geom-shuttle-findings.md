# geom-shuttle — findings (r0.1): **GEOM-PUMP-CONFIRMED**

**Verdict:** `GEOM-PUMP-CONFIRMED` — the first **buildable** geometry (DXF r0.6) pumps on the canonical
solver: ideal-tier `z_geom = 1.2077`, **above** the campaign's placeholder-cap `z = 1.1894` (+9.7 %
relative to unity). Fire margin is healthy and the firing order holds. The one substantive finding is
on **G0**: the geometry caps' galvanic ceiling is **1.334** (which *independently reproduces* the
chat-side port's z≈1.335, rather than refuting it) — `1.2033` was only ever the *placeholder* device
point's ceiling, not a cap-invariant.

Branch `geom-shuttle-gate` (off `main`'s canonical solver line `effcee1`). This is a **consumer** run.
`reference/doubler_core.py` and `index.html` **untouched**; `shuttle_core.py` carries **one additive,
default-preserving** change only — the TMD-authorised `set_device_caps()`/`reset_device_caps()` cap
hook (+40 lines, 0 deletions; the rev-0.3 path is byte-identical — `--rev03` anchor `1.2033`, spark C0
`T0a 1.2033 · T0b 1.1894 · drift 4.6e-14` all green). Caps are **consumed from**
`presets/G1-geometry-r06.json`, never hard-coded in the consumer. Not merged. Tiers: `[OC]`
solver-derived · `[IR]` modelling/reporting.

---

## Inputs — geometry-derived cap set (DXF r0.6, Z-stack true-scale)

| Cap | Placeholder | **Geometry r0.6** | Injection |
|---|---|---|---|
| C1 / C2 (min/max pF) | 160 / 1000 | **16 / 280** | `set_device_caps` |
| Cx3 / Cx4 (min/max pF) | 60 / 1200 | **4 / 88** | `Params.cx_min/cx_max` |
| Ca / Cb (pF) | 100 | **309** | `set_device_caps` |
| Cpar (pF) | 20 | **20** | `set_device_caps` |
| C_R (pF) | — | 1477 | **record only** — 5–6 rail collapsed to ground in the pump (`shuttle_core.py` tier; brief G0 "C_R shorted") |

---

## G0 — anchor recovery at geometry caps → **INJECTION VERIFIED; anchor reinterpreted** `[OC]`

| reading | run | z | meaning |
|---|---|---|---|
| (i) | placeholder reset → `galvanic_z` | **1.20327** | injection mechanism **VERIFIED** (round-trips to `Z_BASELINE` exactly) |
| (ii) | geometry caps, Ca/Cb = 309 | **1.33400** | the **geometry** device point's own galvanic ceiling — **≈ chat-side port z≈1.335** |
| (iii) | geometry C1/C2, Ca/Cb → large | **1.00002** | transfer caps short the pump ⇒ z→1.000 (**not** 1.2033) |

**Finding.** `Z_BASELINE = 1.2033` is `ANCHORS["device"]` — the galvanic z **at the placeholder caps**.
It is **not cap-invariant**, so "recover 1.2033 *at the geometry caps*" tests only that the caps were
injected (reading (i): exact). At the geometry caps the degenerate ceiling is its own value, **1.334**.
Two consequences for the brief's framing:
- The brief's literal G0 — "Ca/Cb → large → 1.2033" — does **not** hold in the canonical solver: with
  Ca/Cb ≫ C1 the transfer caps rigidly couple the pump pairs and z → 1.000 (reading (iii)).
- The chat-side 4-node port's z≈1.335 was **not** a wrong number — reading (ii) shows the canonical
  solver gives **1.334** at the same caps. The port's *self-check* mis-targeted 1.2033 (a placeholder
  value); the underlying figure was right. The canonical run **cross-validates** it.

G1 is therefore authorised on the verified injection (i) + the cross-validated ceiling (ii), with the
anchor value reinterpreted — not on a literal 1.2033 match.

## G1 — 6-node pump → **z_geom = 1.2077 (pumps; more than placeholder)** `[OC]`

| | placeholder | **geometry r0.6** |
|---|---|---|
| ideal-tier `z_shuttle` | 1.18938 | **1.20766** |
| own galvanic ceiling | 1.20327 | 1.33400 |
| pump vs unity | +0.18938 | **+0.20766** (+9.7 % rel.) |

The buildable geometry **pumps, and pumps harder** than the placeholder. Mechanism: the transfer caps
**Ca/Cb = 309 pF** are now *larger* than the swinging C1max = 280 pF (placeholder: 100 vs 1000 — the
reservoir was tiny relative to the swing). The bigger reservoir lifts the per-cycle gain and the
ceiling (1.334), and `z_geom = 1.208` sits comfortably below that ceiling — internally consistent with
the solver's bucket-budget (galvanic z is the shuttle ceiling). The smaller swing (280 vs 1000) and
smaller Cx (88 vs 1200) do **not** stop the pump; they reduce absolute throughput, not the ratio.

## G2 — fire-boost adequacy → **fires with headroom** `[OC]`

| metric | placeholder | **geometry** | note |
|---|---|---|---|
| bare collapse Cx_max/Cx_min | 20× | **22×** | similar (brief §2) |
| **effective** boost cx_max/(cx_min+strays) | 17.65× | **7.33×** | strays (pCboss 6 + gap 2 = 8 pF) dominate cx_min = 4 pF |
| **fire margin** overvoltage / source rail (scale-free) | 0.154 | **1.157** | geometry fires with **more** headroom |
| absolute per-fire charge (∝ Cx_max) | 1200 pF | 88 pF | **~14× smaller** → throughput, not firing |

The lower boost **ratio** is real (the fixed boss/gap strays dominate the small buildable cx_min), but
it does **not** gate firing: the larger Ca/Cb load the island to a higher fraction of the rail, so the
scale-free fire margin (overvoltage normalised by its own source rail) is **1.16 vs 0.15** — the
geometry fires *harder* than the placeholder. The ~14× smaller per-fire charge lowers throughput, but
G1 (`z > 1`) already shows the pump survives it. **No `GEOM-FIRE-MARGINAL`.** *(Absolute-volt strike
confirmation against the real 0.5 mm spark gap remains a spark-tier task once gap electrodes are placed
— deferred, brief §7; the scale-free margin here is the in-scope evidence.)*

## G3 — gap stations + firing order → **order holds at 30°/no-offset** `[OC]`

Event stations (one 60° sector; from `steady_trace` — set by the solver's timing model, the target
angles for the next DXF to *place* the gaps at, since gap electrodes are not yet drawn, §7):

| event | SG1 | SG3a | SG3b | SG2 | SG4a | SG4b |
|---|---|---|---|---|---|---|
| θ (sector) | 0.0500 | 0.1200 | 0.2675 | 0.5500 | 0.6200 | 0.7675 |
| deg of 60° | 3.0 | 7.2 | 16.1 | 33.0 | 37.2 | 46.0 |

- **Intra-branch order** return < load < fire holds on both branches (A: SG1<SG3a<SG3b; B:
  SG2<SG4a<SG4b) ⇒ **SG1/SG2 lead, SG3/SG4 lag — HOLDS**.
- **Inter-branch** A→B spacing = 0.500 sector = exactly the as-drawn **30° stator offset**; the islands
  carry **no** deliberate offset.
- **Recommendation for the next DXF:** the basic lead/lag needs **no island offset** — it is structural
  in the 30° stator offset + the load/collapse/fire windows. If a *different* inter-stage lag is wanted,
  add an island angular offset of `(target_lag − 0.500)` sector; at present that delta is `+0.000`
  (true antiphase). *(The brief flagged G3 as "expected to possibly fail"; it does not — the as-drawn
  geometry already produces the correct firing order.)*

---

## Verdict set

- **`GEOM-PUMP-CONFIRMED`** — G0 injection verified (anchor reinterpreted to the geometry ceiling
  1.334, cross-validating the chat-side 1.335) **and** G1 `z_geom = 1.2077 > 1`, above the placeholder
  1.1894. G2 fires with headroom; G3 firing order holds.
- For TMD / next DXF iteration: (1) the buildable geometry is sound to carry forward; the bigger Ca/Cb
  reservoir is the reason it out-pumps the placeholder. (2) Throughput (not pumping) is the cost of the
  small Cx — if more delivered charge is wanted, grow Cx_max (more pickup area / smaller Cx gap), which
  also lifts the effective boost ratio. (3) No island timing offset is required for the firing order.
  (4) Place the spark-gap electrodes at the G3 stations and re-run the spark tier for the absolute
  strike confirmation (deferred §7). (5) Mirror the Ca-side shrink into the Cb Z-stack cross-section so
  the drawing is self-consistent (§8); this run assumed Ca = Cb = 309 pF.

## Reproduce

```
python geom_shuttle_run.py        # G0–G3, prints the verdict; writes geom_caps_vs_placeholder.csv
python shuttle_core.py --rev03    # regression: anchor 1.2033, ideal tier unchanged (hook inert)
```
