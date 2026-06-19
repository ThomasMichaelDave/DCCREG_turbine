# Findings — GEOM-EXTRACT: r0.15 DXF → overlap(θ)/gap profiles + fire stations

**Branch** `geom-extract` (off `topology-recon-r0_13`, which carries `main` + the DXF-sourced edge
list + the committed r0.15 DXF). **Verdict:** **`GEOMETRY-DRIFTS`** — the parser **validates**
(frame + hatch 0.0 % + annulus 3.2 % + **all four freeze fire-stations exact** + the C1/C2 plate
sweep), and the cleanly-extractable model values **match the hardware**, with **one named reconcile
item**: the **Cx island cap** (drawn single-face 329 pF vs model 648 pF — the model value is the
**two-face** reading; confirm the island is differential). Four features are **out of extraction
scope** (drawing punch-list, *not* drifts). This answers the brief's prize question: **the S5–full-sim
stack has been running on station angles and plate geometry that match the drawn machine; the only
number to reconcile before the next sim is the island cap's one-face-vs-two-face factor of 2.**

The parser is **purely geometric** (brief design rule): it emits `A(θ)`, gaps, stations, dims — never
C or L. A *nominal* C is computed **only for the drift check** (ε₀ + a stated simple model), never
emitted as a sim input.

---

## The coordinate reality (the replica hazard, resolved) `[OC]`

r0.15 lays each part out **1:1 in its own translated view-frame** (C1 plate at (0,−1700), C2 at
(1200,−1700), the rotor faces at (2400,−2900), …), with the **datum + 12-sector grid + ref-radii**
as a reference overlay at **(0,0)**. So "true-scale selection" is not "within R25–500 *about the
datum*" literally (no part sits there) — it is: **pick a part's own-view instance, about that view's
spin centre, with radial extent in [R25,R500]; reject the +y schematic/legend glyphs and any
forgotten-translation grab (r≈5009).** Angles are preserved under the pure translation, so the
sector-grid 0° (electrical 0) carries into every view-local frame. Two drawing idioms had to be
handled: the **stator** wedges are drawn as **closed** polylines, but the **rotor** wedges are
**open arc+radial strokes** — stitched into closed loops by endpoint coincidence (the brief's
"tessellate arc edges… arc+radial outlines").

## §4 named checks

| # | check | result |
|---|---|---|
| 1 | **true-scale selection** — accepted outlines in-envelope; replicas/schematic-glyphs rejected | ✓ (own-view band y<−1000; r∈[R25,R500] about each view's spin centre) |
| 2 | **frame** — datum (0,0), 12 sectors @30°, electrical-0 on grid, ref R25/95/387, mm | ✓ (`$INSUNITS`=4) |
| 3 | **A(θ)** swept for C1, C2, Cx3, Cx4 | ✓ (rotor wedges stitched closed; grid-overlap sweep 0–30°) |
| 4 | **hatch check** (parser correctness) — area engine = drawn hatch | ✓ **0.00 % (C1/C2/Cx4), 0.59 % (Cx3)**; C1 stator area 214 053 vs analytic 6×30° annulus 221 080 (**3.2 %**, drawn chamfer) |
| 5 | **endpoint/drift** — nominal C extremes vs model | C1/C2 **consistent** (fringe floor); **Cx3/Cx4 DRIFT/RECONCILE** (two-face) |
| 6 | **station check** — SG angles vs freeze §5 | ✓ **all exact**: SG3a 7.2 / SG3b 16.1 / SG4a 37.2 / SG4b 46.0 |
| 7 | **fixed caps** Ca/Cb/C_R | **SCOPE** — electrode area on schematic-only layers; gaps (1.0/12.0 mm) confirmed |
| 8 | verdict + profiles | **`GEOMETRY-DRIFTS`** + `geom_profiles/stations/fixed.csv` |

## Stage A — the frame (clean) `[OC]`

`$INSUNITS = 4` (mm); datum circle at **(0,0)** ("DATUM 0,0 spin axis"); **12** sector lines at
exactly **30°** spacing with **0° on the grid** (electrical-0); ref-radii circles **R25/R95/R387**
(+ text R75/R491/R500). Frame established.

## Stage B/C — the overlap sweeps (real, validated) `[OC]`

| part | rotor band | stator band | A(θ) max → min (mm²) | peak at |
|---|---|---|---|---|
| **C1** | r75–387 (6 wedges, stitched) | r95–387 (6 wedges) | **83 480 → 0** | θ=0 (aligned) |
| **C2** | r75–387 | r95–387 | **83 496 → 0** | θ=0 |
| **Cx3** | r75–350 island bars | r58–350 pickup | **148 456 → 644** | θ=0 |
| **Cx4** | r75–350 | r58–350 | **151 640 → 248** | θ=0 |

The C1/C2 curves are the classic varicap modulation — maximal overlap at alignment, sweeping toward
0 as the rotor turns through the 30° sector. **These are the θ-sampled `A(θ)` profiles the
torque-resolved sim consumes** (it multiplies by ε/g and the fringe model).

## Stage D — validation + the drift readout

**Parser correctness (§4.4) — PASS.** The grid area-engine re-integrates each drawn overlap hatch to
**0.0–0.6 %**, and reproduces the analytic 6×30° annulus to **3.2 %** (the residual is the drawn
chamfer on the wedge corners). The parser is **not** grabbing a frame-scaled replica and the
sweep/clip math is sound → **not `PARSER-INVALID`.**

**Consistent (the machine matches the model where cleanly checkable):**
- **C1, C2** — the geometric overlap sweeps **0 → 83 480 mm²**. The model's **C1_min = 16 pF is the
  fringe/parasitic floor** (Cpar≈20 pF), *not* a geometric minimum, so a 0 geometric min is
  consistent with a 16 pF electrical floor. The axial gap (not in the radial drawing) implied by
  C1_max = 280 pF is **2.64 mm** — physical. No drift.
- **Stations SG3a/SG3b/SG4a/SG4b** — drawn **7.2 / 16.1 / 37.2 / 46.0°**, matching freeze §5
  (**7.2 / 16.05 / 37.2 / 46.05**) to **< 0.1°**. The fire clock the whole stack assumed **is the
  drawn fire clock.** (SG1/SG2 return gaps 3.0/33.0°, BS3/BS4 backstops 19.0/49.0° — drawn,
  report-only; the SGs are drawn 6-fold, one marker per active sector pair, so the station angle is
  the marker angle mod 60°.)

**Drift / reconcile (the prize — 2 items):**
- **Cx3, Cx4** — single-face nominal **329/336 pF** (ε₀, 4.0 mm gap, A_max) vs model **648 pF**: a
  **factor ≈ 2.0**. The **two-face differential** nominal (the island bar coupling to a pickup on
  *both* faces) is **657/671 pF — matching the model to 1–4 %.** So the model's 648 pF *is* the
  two-face reading of the drawn geometry. **RECONCILE before the next sim: confirm the island is
  physically two-face (differential bar between two pickups).** If single-face, the 648 pF (and the
  whole 8↔648 shuttle swing the flying-bucket block uses) is a 2× overstatement and the shuttle
  W_coll/E_fire re-derive; if two-face (the likely intent), drawing and model agree and only the
  drawing's per-face annotation needs the note.

**Scope / drawing punch-list (NOT drifts — features this drawing doesn't carry in extractable form):**
- **Ca / Cb / C_R electrode AREA** — the `ND*-Ca/Cb/ELECTRODE` layers carry only the **schematic
  symbol** (a +y glyph); the real transfer/septum plates share the plate layers, so the electrode
  area is **not robustly extractable** from a dedicated part-view. The **gap bands are confirmed**
  (Ca/Cb 1.0 mm, C_R 12.0 mm septum). To check 309/789 pF geometrically, the next DXF rev wants the
  electrodes on their own part-view layer.
- **L_A/L_B Cem pole sweep** — the motor is drawn as a **distribution schematic** (MECH-CEMS 36
  lines, 12 QUADRICORE polylines, COIL-CEMS inserts), **not** concentric pole geometry, so
  `A_pole(θ)`/`g(θ)` are not extractable here. The torque-resolved sim's Cem `½i²dL/dθ` will need
  the motor drawn as concentric poles (the same "core-symbols-as-blocks" punch-list the topology
  recon flagged).

## Verdict + what it means

**`GEOMETRY-DRIFTS`** — the parser validates, and **the drawn machine matches the simulated one
everywhere cleanly checkable**: the **fire stations are exact** to freeze §5 and the **C1/C2 plate
sweep is consistent** (the 16 pF floor is fringe, the implied axial gap is physical). **One named
reconcile item stands:** the **Cx island cap**, where the model's 648 pF is the **two-face** reading
of a drawn single-face 329 pF — *confirm the island is differential* before the next sim trusts the
8↔648 swing. Four fixed-cap/Cem features are **out of extraction scope** (handed to the drawing
punch-list, not drifts).

**Bottom line for the stack:** the S5–full-sim results that ride on **station timing** and **plate
geometry** are on hardware-matching numbers; the **island-cap-dependent** results (shuttle W_coll,
E_fire, the flying-bucket swing) ride on the **two-face assumption**, which is the single thing to
confirm in the drawing before the torque-resolved angular sim (brief §8 step 2) runs on these
profiles.

## Deliverables

`sim/geom_extract.py` (the read-only parser: frame, true-scale own-view selection, arc/stroke
stitching, grid-overlap sweep, hatch/annulus/station/endpoint validation; self-validating area
engine) · this findings doc · `geom_profiles.csv` (θ-sampled `A(θ)` for C1/C2/Cx3/Cx4 — the sim
multiplies by ε/μ/fringing) · `geom_stations.csv` (drawn SG angles vs freeze) · `geom_fixed.csv`
(gaps + the scope notes) · `geom_profiles.png`. r0.15 DXF read-only; frozen solvers empty-diff
asserted. **Not merged.**

### Roadmap (brief §8)

The reconcile (island one-face vs two-face) is settled first — likely a drawing annotation
(two-face), possibly a shuttle re-check if single-face. Then **step 2: the torque-resolved angular
sim** consumes `geom_profiles.csv` (`A(θ)` → `dC/dθ` for the real independent torque integral; the
station angles for clocking), fixing the full-sim's two remaining soft spots on real dimensions. The
fixed-cap electrode layers and the concentric Cem poles are the drawing punch-list that unblocks the
fixed-cap geometric check and the Cem `½i²dL/dθ`. Then **v0.11** freezes with r0.15 as the geometric
authority and these profiles as the locked inputs.
