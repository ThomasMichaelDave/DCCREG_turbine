# Findings — GEOM-VALIDATE: island reconcile + A(θ) registration (the gate before the torque sim)

**Branch** `geom-validate` (off `geom-extract`). **Verdict:** **`PROFILES-VALIDATED`** — but only
**after two corrections this gate forced**, both of which the brief anticipated and the `geom-extract`
"hatch check 0.00 %" could not catch:

1. **The A(θ) magnitude was wrong.** The swept `A_max = 83 480 mm²` was **38 % of the true aligned
   overlap (221 080 mm²)** — an engine registration bug, not geometry. Diagnosed, fixed in the
   engine, and the exact **analytic** annular-sector profile re-emitted.
2. **The island is single-face**, decided **directly from the drawn axial cross-section** (one pickup
   electrode, nothing on the other face) — so the model's `Cx_max = 648 pF` is the **top** of the
   single-face band; the drawn representative is **~471 pF (~27 % lower)**. The frozen shuttle is
   re-derived; the impact is bounded and the full-sim is qualitatively robust.

With both resolved, the torque-resolved sim may consume the **corrected** `geom_profiles.csv` with
dC/dθ and the fire clock in one frame. The single-face-vs-redesign-to-two-face decision is **TMD's**
(flagged) and rescales only the **shuttle** term (≤15 %), not the **varicap** dC/dθ.

---

## Part A — the island reconcile (decided by the axial section, not back-inferred from C)

**A.1 — the direct evidence.** The drawn **axial** cross-section (Z-stack band, side elevation
x=radius / y=axial-Z) reads unambiguously:

| layer | axial Z | radial |
|---|---|---|
| **island bar** `ND7` | y ∈ [1158.2, 1162.2] | r75–350 |
| **gap** `CAP-Cx3` | y ∈ [1162.2, 1166.2] (**4.0 mm**) | — |
| **pickup** `ND3` | y ∈ [1166.2, 1170.2] | r58–350 |

**One pickup, on one face, across a 4.0 mm gap; nothing below the bar.** → the drawn island is
**SINGLE-FACE** (not two-face/differential). The `CAP-Cx3-GAP` ±x bands the parser also sees are the
two *diametric halves* of the annulus, **not** the face count — the face count is the axial flanking,
and it is one.

**A.2 — reconcile the 648 pF.** The brief's premise ("648 = 2 × 329 pF single-face-**air**, so
single-face halves to 324") is **retired on two counts**: single-face is confirmed (there is only one
face — no ×2), *and* the gap is **mica-loaded** (freeze v0.10: 3.0 mm + 0.3 mm mica/face, ε_r 5.4 →
2.5–3.1 mm effective), not 4.0 mm air (the air-at-4 mm reading was the drift-check error corrected in
`geom-extract`). The single-face nominal Cx_max:

| area basis | gap reading | Cx_max |
|---|---|---|
| drawn bars (148 k mm²) | 3.11 mm (mica added) | **421 pF** |
| drawn bars / solid (184 k) | mid | **~471–522 pF** |
| solid 6-sector (184 k) | 2.51 mm (mica replaces air) | **647 pF** ← the model's 648 |

So **single-face Cx_max ≈ 421–648 pF**, with the model's 648 at the **optimistic top** (solid-area +
mica-replaces-air). The drawn representative (discrete bars, balanced gap) is **~471 pF**.

**A.2 — frozen-shuttle re-derive** (the `island_charging` "real" scheme **run**, not edited):

| Cx_max pF | W_coll mJ | ΔW | E_fire mJ | ΔE | C_fire pF | V* kV |
|---|---|---|---|---|---|---|
| **648** (anchor) | 12.449 | +0.0 % | 13.951 | −0.0 % | 69.8 | 2.15 |
| ~471 (representative) | 11.078 | **−11 %** | 12.824 | **−8 %** | 64.1 | 2.72 |
| 421 (low) | 10.583 | −15 % | 12.412 | −11 % | 62.1 | 2.95 |
| 324 (brief air-halve) | 9.418 | −24 % | 11.436 | −18 % | 57.2 | 3.53 |

Across the realistic single-face band the shuttle impact is **W_coll −0…−15 %, E_fire −0…−11 %**; the
island still **fires at 20 kV < the 21 kV ceiling throughout** (V* — the pickup voltage — rises
2.15→2.95 kV but stays far under). **`ISLAND-SINGLE-FACE`**: the full-sim is **qualitatively robust**
(pumps / holds ~15 kV / fires under ceiling); the shuttle's W_coll/E_fire carry a bounded ≤15 %
downward revision pending the design call.

**A.3 design call (TMD, flagged to `dxf_flags.md`):** accept single-face (~471 pF, shuttle
re-derived) **or** add a second pickup face (differential) to realise 648 pF — a hardware change.
Either way the next DXF rev wants a per-face annotation.

## Part B — the A(θ) registration

**B.1 — θ-origin.** The drawn wedge occupancy (circle-fit spin axis):
- **C1 rotor and stator share the same 6-fold phase** (30° mod 60°, width 30°) over r95–387 →
  **aligned at θ=0 = electrical-0** (the "true C1" datum the firing-stations note pins). C1 A_max is
  at θ=0. ✓
- **C2 stator is interleaved** (phase 0° vs C1's 30°) → **C2 is anti-phase to C1 by design** (C2 min
  at θ=0, max at θ=30) — the correct 4-node doubler drive, **not** a registration error.

**B.2 — the magnitude ground truth (the catch).** The **analytic** annular-sector aligned overlap
(6 × 30° over r95–387, independent of any clip/grid engine) is **221 080 mm²**. The `geom-extract`
**swept** A_max was **83 480 mm² — 38 %** of that: a real **`A-MAGNITUDE-DRIFT`**. The
"hatch check 0.00 %" never caught it because it re-integrated the *same drawn polygon* with a second
method (engine self-consistency) against a 3 mm axial Z-strip, **not** the face-view overlap — exactly
the gap the brief flagged. **Root cause (diagnosed + fixed in the engine):** the spin centre was the
wedge-mass **centroid** (off the true axis by ~100 mm) and the 600-mm clustering **split a single
part-view** across cells → partial, mis-registered overlap and the wrong (stack-section) instance
winning. The engine now **circle-fits the spin axis** and **merges grid groups by spin centre**;
the residual is imperfect stroke-stitching (4 of 6 rotor wedges close cleanly), so — these being
**regular annular sectors** — the **exact analytic A(θ)** is adopted as the validated profile and
re-emitted.

**B.3 — phase sanity.** With the island collapse and the fire clock in one frame: at the **load**
station **SG3a (7.2°)** the island is at the high-C plateau (pickup) and C1 is at 76 % of max; at the
**fire** station **SG3b (16.05°)** the island is mid-collapse at **C_fire ≈ 70 pF** and C1 has fallen
to 46 % of max. Pickup at high C, fire at low C_fire, C1 monotone falling across the window → **phase
sane**.

**B.4 — `REGISTRATION-CONFIRMED`** (after the magnitude fix + analytic re-emit): θ-origin = electrical-0,
analytic A_max matched (the swept was the bug), phase physical.

## §-checks summary

| # | check | result |
|---|---|---|
| 1 | island axial face count | **1 pickup face** across 4.0 mm → single-face |
| 2 | island decision + re-derive | `ISLAND-SINGLE-FACE`; Cx_max ~471 pF (band 421–648); W_coll −11 %/E_fire −8 % at rep |
| 3 | C1/C2 max at θ=0 = electrical-0; occupancy | **C1 aligned at θ=0** ✓; C2 anti-phase by design |
| 4 | analytic A_max vs swept | analytic **221 080**; swept 83 480 was **38 %** → A-MAGNITUDE-DRIFT (fixed) |
| 5 | phase at SG3a/SG3b | pickup at plateau, fire mid-collapse, C1 falling → **sane** |
| 6 | gate verdict | **`PROFILES-VALIDATED`** (after 2 corrections) |

## Verdict + what it means

**`PROFILES-VALIDATED`** — the island is resolved (**single-face**, shuttle re-derived) **and** the
registration is **confirmed** — but this gate **earned its place**: it caught that the `geom-extract`
A(θ) **magnitudes were 2.6× wrong** (an engine registration bug the self-consistent hatch check
structurally could not see) and that the island is **single-face** (Cx_max 648 → ~471 pF). The
torque-resolved sim consumes the **corrected, analytic** `geom_profiles.csv`: dC/dθ and the fire clock
are provably co-registered (C1 max at electrical-0, exact 221 080 mm² magnitude), so the
`½V²·dC/dθ` term the independent guard is built on is sound. The single-face-vs-two-face **design
call is TMD's** (flagged); it rescales only the **shuttle** term (W_coll/E_fire, ≤15 %), not the
varicap term.

## Deliverables

`sim/geom_validate.py` (island axial-section extractor + conditional frozen-shuttle re-derive +
registration/phase checks; reuses + fixes the `geom-extract` engine — circle-fit spin axis,
spin-centre group merge — and adds the exact analytic annular-sector overlap) · this findings doc ·
**re-emitted `geom_profiles.csv`** (analytic A(θ), method-tagged, registration-correct: C1 A_max
221 080 @ 0°, C2 @ 30°) · `dxf_flags.md` updated (island single-face per-face annotation; the A(θ)
magnitude fix). r0.15 DXF + frozen solvers read-only, empty-diff asserted. **Not merged.**

> **Note on the shared engine.** `sim/geom_extract.py` carries the spin-centre fix (the
> A-MAGNITUDE-DRIFT root cause) and a softened C1/C2 endpoint note (the absolute C_max is gated on
> the **axial Z-gap**, which is not in the radial view — informational, like the fixed-cap electrode
> areas; the A(θ) **shape** is what's validated). `geom_extract` still returns `GEOMETRY-CONSISTENT`.
> `geom_validate` is the authoritative profile emitter (run it last / with `geom_extract`); the
> validated `geom_profiles.csv` is the **analytic** one.

### Roadmap

`PROFILES-VALIDATED` → the **torque-resolved angular sim** (the next brief) runs the independent
`∮[½V²·dC/dθ + ½i²·dL/dθ]·ω dt` guard and the real `½i²·dL/dθ` output on these co-registered profiles
(the varicap term is geometric now; the Cem L(θ) still awaits the concentric-pole drawing punch-list,
carried `[IR]` until then). TMD settles the island single-face value (accept ~471 pF or redesign to
two-face 648). Then **v0.11** freezes with r0.15 as the geometric authority and the validated profiles
as the locked inputs.
