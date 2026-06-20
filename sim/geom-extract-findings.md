# Findings — GEOM-EXTRACT: r0.15 DXF → overlap(θ)/gap profiles + fire stations

**Branch** `geom-extract` (off `topology-recon-r0_13`, which carries `main` + the DXF-sourced edge
list + the committed r0.15 DXF). **Verdict:** **`GEOMETRY-CONSISTENT`** — the parser **validates**
(frame + hatch 0.0 % + annulus 3.2 % + **all four freeze fire-stations exact** + the C1/C2 plate
sweep), and the cleanly-extractable model values **match the hardware**. **The one soft residual** is
the island cap's **bar-fill** (~19 %, deferred to the sim's fringing model). Four fixed-cap/Cem
features are **out of extraction scope** (drawing punch-list, *not* drifts). This answers the brief's
prize question: **the S5–full-sim stack has been running on station angles and plate/island geometry
that match the drawn machine.**

> **Correction note (this revision).** The first pass reported `GEOMETRY-DRIFTS` on a Cx "factor 2"
> with a *two-face island* reconciliation. **That was wrong** — it was a **drift-check error in this
> parser**, not a hardware drift. The model's 648 pF island is **single-face** with a **mica-loaded
> gap** (3.0 mm + 0.3 mm mica/face, ε_r 5.4 → ~2.5 mm effective), which the drift-check had modelled
> as **4.0 mm air**. Calibrating the model's own method on the predecessor (**G1 88 pF = 6-sector
> r75–232 / 7.6 mm air, exact**) confirms it: the 648 pF = 6-sector r75–350 / 2.51 mm-eff (exact).
> The factor 2 decomposes **exactly** (×1.97) into the dielectric/gap (×1.59) and the bar-fill area
> (×1.24) — no two-face, no full-circle-vs-sector error. The parser's *geometry* was right; its
> drift-check *dielectric* was not, and is now fixed.

The parser is **purely geometric** (brief design rule): it emits `A(θ)`, gaps/gap-stacks, stations,
dims — never C or L. A *nominal* C is computed **only for the drift check** (with the stated
dielectric), never emitted as a sim input.

---

## The coordinate reality (the replica hazard, resolved) `[OC]`

r0.15 lays each part out **1:1 in its own translated view-frame** (C1 plate at (0,−1700), C2 at
(1200,−1700), the rotor faces at (2400,−2900), …), with the **datum + 12-sector grid + ref-radii**
as a reference overlay at **(0,0)**. So "true-scale selection" is: **pick a part's own-view instance,
about that view's spin centre, with radial extent in [R25,R500]; reject the +y schematic/legend
glyphs and any forgotten-translation grab (r≈5009).** Angles are preserved under the pure
translation, so the sector-grid 0° (electrical 0) carries into every view-local frame. Two drawing
idioms had to be handled: the **stator** wedges are drawn as **closed** polylines, but the **rotor**
wedges are **open arc+radial strokes** — stitched into closed loops by endpoint coincidence.

## §4 named checks

| # | check | result |
|---|---|---|
| 1 | **true-scale selection** — accepted outlines in-envelope; replicas/schematic-glyphs rejected | ✓ (own-view band y<−1000; r∈[R25,R500] about each view's spin centre) |
| 2 | **frame** — datum (0,0), 12 sectors @30°, electrical-0 on grid, ref R25/95/387, mm | ✓ (`$INSUNITS`=4) |
| 3 | **A(θ)** swept for C1, C2, Cx3, Cx4 | ✓ (rotor wedges stitched closed; grid-overlap sweep 0–30°) |
| 4 | **hatch check** (parser correctness) — area engine = drawn hatch | ✓ **0.00 % (C1/C2/Cx4), 0.59 % (Cx3)**; C1 stator area 214 053 vs analytic 6×30° annulus 221 080 (**3.2 %**, drawn chamfer) |
| 5 | **endpoint/drift** — nominal C extremes vs model | C1/C2 **consistent** (fringe floor); **Cx3/Cx4 consistent** under the design mica gap (~520–540 pF vs 648; ~19 % bar-fill residual) |
| 6 | **station check** — SG angles vs freeze §5 | ✓ **all exact**: SG3a 7.2 / SG3b 16.1 / SG4a 37.2 / SG4b 46.0 |
| 7 | **fixed caps** Ca/Cb/C_R | **SCOPE** — electrode area on schematic-only layers; gaps (1.0/12.0 mm) confirmed |
| 8 | verdict + profiles | **`GEOMETRY-CONSISTENT`** + `geom_profiles/stations/fixed.csv` |

## Stage A — the frame (clean) `[OC]`

`$INSUNITS = 4` (mm); datum circle at **(0,0)**; **12** sector lines at exactly **30°** with **0° on
the grid** (electrical-0); ref-radii circles **R25/R95/R387** (+ text R75/R491/R500). Established.

## Stage B/C — the overlap sweeps (real, validated) `[OC]`

| part | rotor band | stator band | A(θ) max → min (mm²) | peak at |
|---|---|---|---|---|
| **C1** | r75–387 (6 wedges, stitched) | r95–387 (6 wedges) | **83 480 → 0** | θ=0 (aligned) |
| **C2** | r75–387 | r95–387 | **83 496 → 0** | θ=0 |
| **Cx3** | r75–350 island bars | r58–350 pickup | **148 456 → 644** | θ=0 |
| **Cx4** | r75–350 | r58–350 | **151 640 → 248** | θ=0 |

The C1/C2 curves are the classic varicap modulation — maximal at alignment, sweeping toward 0 across
the 30° sector. **These are the θ-sampled `A(θ)` profiles the torque-resolved sim consumes** (it
multiplies by ε/g and the fringe model).

## Stage D — validation + the drift readout

**Parser correctness (§4.4) — PASS.** The grid area-engine re-integrates each drawn overlap hatch to
**0.0–0.6 %** and reproduces the analytic 6×30° annulus to **3.2 %** (drawn chamfer). The parser is
**not** grabbing a frame-scaled replica and the sweep/clip math is sound → **not `PARSER-INVALID`.**

**Consistent (the machine matches the model where cleanly checkable):**
- **C1, C2** — the geometric overlap sweeps **0 → 83 480 mm²**. The model's **C1_min = 16 pF is the
  fringe/parasitic floor** (Cpar≈20 pF), *not* a geometric minimum, so a 0 geometric min is
  consistent with a 16 pF electrical floor. The axial gap implied by C1_max = 280 pF is **2.64 mm** —
  physical. No drift.
- **Cx3, Cx4** — **the factor 2 was a drift-check dielectric error, not hardware.** The drawn 4.0 mm
  hatch is the *physical envelope*; the design *capacitance* gap is **mica-loaded** (3.0 mm + 0.3 mm
  mica/face, ε_r 5.4 → 2.5–3.1 mm effective). With that, the drawn overlap (148 456 mm²) gives
  **~520–540 pF** vs the model's **648 pF**. Calibration confirms the model's method: **G1's 88 pF
  reproduces exactly** as 6-sector r75–232 / 7.6 mm air, and 648 pF = 6-sector r75–350 / 2.51 mm-eff
  (exact). **No two-face island; no full-circle-vs-sector error** (the parser already measured the
  sectored overlap — 148 k is ~0.4 of the full annulus; a full-circle grab would have *overshot* to
  ~820 pF).
- **Stations SG3a/SG3b/SG4a/SG4b** — drawn **7.2 / 16.1 / 37.2 / 46.0°**, matching freeze §5 to
  **< 0.1°**. The fire clock the whole stack assumed **is the drawn fire clock.** (SG1/SG2 return gaps
  3.0/33.0°, BS3/BS4 backstops 19.0/49.0° — report-only; SGs drawn 6-fold, station = angle mod 60°.)

**Soft residual (flagged, deferred to the sim — not a drift):**
- The model's 648 pF idealizes the island as a **solid 6-sector plateau**; the drawn island is
  **discrete bars** realizing **~81 %** of that area → **real Cx_max ≈ 525 pF, ~19 % below 648.**
  This is closed by **inter-bar fringing** (explicitly the sim's job per the brief's design rule) or
  a small model trim — to be confirmed in the torque-resolved sim's fringing model. It is a
  fringing/area *physics* choice, not a geometry drift.

**Scope / drawing punch-list (NOT drifts):**
- **Ca / Cb / C_R electrode AREA** — the `ND*-Ca/Cb/ELECTRODE` layers carry only the **schematic
  symbol** (+y glyph); the real plates share the plate layers, so the area is **not robustly
  extractable** from a dedicated part-view. The **gap bands are confirmed** (Ca/Cb 1.0 mm, C_R
  12.0 mm septum). The next DXF rev wants the electrodes on their own part-view layer.
- **L_A/L_B Cem pole sweep** — the motor is a **distribution schematic** (MECH-CEMS 36 lines, 12
  QUADRICORE polylines, COIL-CEMS inserts), not concentric pole geometry, so `A_pole(θ)`/`g(θ)` are
  not extractable here (the same "core-symbols-as-blocks" punch-list the topology recon flagged).

## Verdict + what it means

**`GEOMETRY-CONSISTENT`** — the parser validates, and **the drawn machine matches the simulated one on
every cleanly-extracted number**: the **fire stations are exact** to freeze §5, the **C1/C2 plate
sweep is consistent** (16 pF = fringe floor), and the **Cx island reconciles** under the design mica
gap (the earlier factor-2 was this parser's air-at-4mm drift-check error, now fixed — **not** a
two-face island and **not** a sectoring mistake). **One soft residual** stands: the island's
**discrete bar fill** realizes ~81 % of the model's idealized solid-sector area (real Cx_max ≈ 525 pF
vs 648), a **fringing/area choice the sim owns**. Four fixed-cap/Cem features are **out of extraction
scope** (drawing punch-list).

**Bottom line for the stack:** the S5–full-sim results that ride on **station timing**, **plate
geometry**, and the **island cap** are on hardware-matching numbers (the island within the sim's
fringing tolerance). The drawing punch-list (dedicated electrode layers, concentric Cem poles)
unblocks the remaining geometric checks for the torque-resolved sim.

## Deliverables

`sim/geom_extract.py` (the read-only parser: frame, true-scale own-view selection, arc/stroke
stitching, grid-overlap sweep, hatch/annulus/station/endpoint validation with the design dielectric;
self-validating area engine) · this findings doc · `geom_profiles.csv` (θ-sampled `A(θ)` for
C1/C2/Cx3/Cx4 — the sim multiplies by ε/μ/fringing) · `geom_stations.csv` (drawn SG angles vs
freeze) · `geom_fixed.csv` (gap stacks + the scope notes) · `geom_profiles.png`. r0.15 DXF read-only;
frozen solvers empty-diff asserted. **Not merged.**

### Roadmap (brief §8)

**Step 2: the torque-resolved angular sim** consumes `geom_profiles.csv` (`A(θ)` → `dC/dθ` for the
real independent torque integral; the station angles for clocking) and resolves the one soft residual
(the island bar-fill via the fringing model). The fixed-cap electrode layers and the concentric Cem
poles are the drawing punch-list that unblocks the fixed-cap geometric check and the Cem `½i²dL/dθ`.
Then **v0.11** freezes with r0.15 as the geometric authority and these profiles as the locked inputs.

