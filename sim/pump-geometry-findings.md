# PUMP-SYNTH stage 2 — capacitor plate geometry (first cut: Ca / Cb)

**Verdict: `GEOMETRY-STAGE2-PASS`.** All five checks pass (`python3 sim/pump_geometry_gates.py`, record `sim/pump_geometry_gates.json`). Not merged; TMD signs off.

**Scope (TMD, 2026-10-01):**
- The 3-D target is FreeCAD.
- The seed is the r0.15 DXF.
- Ca/Cb are geometrized first.
- Every other electrode is placed as **locked context** from the DXF, so the plate distribution is complete. It is not yet re-sized.

## 1. What was built

| piece | file | role |
|---|---|---|
| stage-1 lock | `tools/pump-synth.html` (🔒 lock → geometry) | Freezes the stage-1 inputs, ladder and exact-engine z into a SHA-256-hashed record kept in the URL (`lock=`, `lockz=`). On every reload the engine re-evaluates the inputs, and the page shows **LOCK DRIFT** unless the hash and z (1e-9) reproduce. Stage-1 controls are frozen while locked. |
| geometrizer | `sim/pump_geometry.py` ↔ `tools/pump-geometry.js` | Locked Ca/Cb → electrode footprints, using the area law `A = C·t/(ε0·εr)` (guide Eq. 20). Solve for r_out (r_in pinned, the default), r_in, the sector width, or nothing (forward mode). An optional manufacturing step can be applied to the solved dimension. |
| round trip | page → worker `z` job | When the realized C differs from the lock (for example after rounding), the exact engine re-runs with Ca/Cb pinned at the realized values and reports z, Δz and pumps / does not pump. |
| plate distribution | page: plan per carrier and assembly overlay; axial half-section; face table | Shows every electrode on every carrier face, coloured by node. |
| checks | `checks()` / `adjacency()` | Ca/Cb inside their counter-electrodes; overlap = electrode area; bore clearance; dielectric margin fits the sector pitch; realized = locked C; alternating layout; **every capacitor's two foils face each other across exactly its own gap**. |
| export | `pump-geometry-<hash>.json` + `tools/pump-geometry.FCMacro` | The macro builds every carrier, foil sector and dielectric slab as solids, grouped and coloured by node, and saves `.FCStd` + `.step` next to the JSON. |
| reference build | `docs/geometry/freeze-v010-CaCb.json` / `.step` | The freeze design point: 95 solids, 1.5 MB STEP, importable into any CAD package. |

## 2. Checks

| check | result | value |
|---|---|---|
| G-SEED | PASS | The model's footprints equal the DXF "stack section (assembly)" plan for all 8 electrode layers (radii and sector start angles). The DXF Ca seed (6 × 30°, r110–175, 4.5 mm mica) gives **309.18 pF**, matching the freeze's 309. |
| G-ADJ | PASS | All 7 capacitors (C1, C2, Ca, Cb, Cx3, Cx4, C_R) face across exactly their own gap. Rotating pairs are judged at alignment. |
| G-JS | PASS | 60 randomized designs: JS = Python to 7e-16, every check string identical. |
| G-CAD | PASS | The macro, run through an OpenCascade stand-in for FreeCAD's `Part`, builds 95 solids (8 carriers, 74 foil sectors, 13 dielectric slabs). Every solid is valid, every volume equals the analytic value (worst 5e-16), there are **no interpenetrations**, and the STEP is written. The JSON exported from the browser builds identically. |
| G-RT | PASS | All three inverse modes realize the locked Ca to 1e-12. Rounding r_out to 1 mm gives r_out 175.0 mm, C = 309.18 pF (+0.45 %), and an exact-engine **z of 1.325175 (Δz −3.0e-4), still pumping**. |

**Browser.** Tested in headless Chromium:
- lock, then 18/18 checks pass;
- the 1 mm rounding round trip takes 6.1 s on a helper worker;
- the ND2 face table is correct;
- the JSON exports;
- reloading from the URL re-verifies the lock;
- no console errors.

## 3. Findings for TMD

1. **The DXF does carry the Ca/Cb areas.**
   - GEOM-EXTRACT reported them as "not extractable", because it looked at `ND1-Ca-ELECTRODE`, which is a schematic glyph only.
   - The real plates are on `ND2-Ca-ELECTRODE` and `ND3-Cb-ELECTRODE`, in the "Ca electrodes", "Cb electrodes" and "stack section (assembly)" frames: **6 × 30° annular sectors, r110–175**.
   - That area (0.029099 m²) on 4.5 mm mica is 309.18 pF, matching the freeze's 309.
   - The drawn `CAP-*-GAP` hatch envelope of 1.0 mm (GEOM-EXTRACT) still disagrees with the 4.5 mm mica. The stage-2 default follows the freeze.
2. **The plate distribution is an angular interleave on shared carriers.**
   - ND2 carries the **Ca electrode (odd sectors, r110–175)** on one face and the **Cx4 pickup (even sectors, r58–350)** on the other.
   - ND3 carries **Cb (even)** and **Cx3 pickup (odd)** the same way.
   - ND1 and ND4 carry the C1/C2 stator sectors (odd / even, r95–387) and are also Ca's and Cb's counter-electrodes.
   - So the stator "plates" must be **insulating carriers with foil electrodes on their faces**. A solid metal plate would couple the full sector area and not realize the drawn capacitances. [IR]
3. **The axial stack order is not in the DXF.** Its "stack section" frame is a plan overlay.
   - The seed is the only order in which every capacitor's electrodes face each other across their own dielectric. Each rotor half is a **clamshell** around its stator pair:
     `flange (island bars) · Cx gap · ND2 · Ca mica · ND1 · 7 mm air · rotor disc · septum · …mirrored`.
   - Total height is 100.2 mm with placeholder thicknesses (foil 1, carrier 3, rotor disc 10, flange 6, septum 12 mm) [IR].
   - Mechanically, the stator pair sits *inside* each rotor half, so it has to be supported through the rotor (bore and rim). That is the first thing to check in CAD.
4. **Rotor phasing as drawn.**
   - C1 is aligned at 0° and C2 is fully out of overlap at 0°: the antiphase doubler.
   - Both islands (Cx3 and Cx4) are at plateau at 0°. This is a drawing observation, not changed here.
5. **The ladder's Ca is 0.45 % below the drawn Ca.**
   - 1.10 × C_max in moist air is 307.80 pF, against 309.18 pF drawn. The locked geometry therefore solves r_out = 174.76 mm instead of 175.
   - Rounding up to the drawn 175 mm costs Δz −3.0e-4, which is consistent with the D-CA finding that a smaller Ca raises z.

## 4. Not in this cut (next stages)

- Geometrizing Cx3/Cx4 (bar fill, mica faces), C_R, and the C_blk "boomerang" stacks (guide §6.7).
- Dielectric breakdown / safe voltage per gap.
- Fringing.
- Supports and fasteners.
- Moving the axial order from [IR] to TMD-confirmed.
