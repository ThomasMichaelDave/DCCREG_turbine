# DXF flags — r0.15 EE schematic (for the next drawing rev)

The r0.15 schematic is committed and confirms the deck graph (TOPOLOGY-CONFIRMED). One soft flag remains for cosmetic cleanup (does **not** block the lock):

## FLAG — ND7/ND8 label-position asymmetry (DXF, soft)

- ND7 label @ (1574.389168460322, 1436.72634823195), ND8 label @ (1855.705060494227, 1435.87167619824). Under the A/B mirror about the schematic centre (x=1793), ND8 should sit near x=2012 but is at x=1856 (~157 off). Every other node pair mirrors exactly.
- **Classification:** a label-POSITION asymmetry, not a proven connectivity error. The island ND8's connectivity (Cx4 8-2, SG4a 4-8, SG4b 8-2, BS4 2-8 — the group-B mirror of ND7) is coherent with freeze §5 and the deck. Likely a drafting-layout choice (the island body drawn at its physical position). **Action:** verify the ND8 label/body placement in the next rev for visual symmetry; no deck change needed.

## Method note (not a flag)

The doubler/commutation symbols are drawn as raw primitives (lines/circles/splines), not blocks with named terminals, so an isolated per-symbol terminal trace is not robustly extractable. Those edges are confirmed by node-layout + symmetry + freeze §5 + the spatially-separable traced subset (C_R, SG1, SG2, C2). For a future fully-automated net-for-net diff, drawing the components as blocks with attributed terminals would let the tracer resolve every edge unambiguously.

## GEOM-VALIDATE flags (r0.1)
- **Island face count (decided by axial section):** the drawn Cx3/Cx4 island is **SINGLE-FACE** — one pickup electrode across the ~4 mm gap, nothing on the other face. The model's 648 pF is the optimistic (solid-area + mica-replaces-air) reading; the single-face value is ~471 pF. **TMD design call:** accept single-face (~471 pF, shuttle re-derived, <8% impact) OR add a second pickup face (differential) to realise the 648 pF — a hardware change. Per-face annotation wanted on the next DXF rev either way.
- **A(theta) magnitude (fixed in the engine):** the geom-extract swept A_max was 156872 mm^2 vs the analytic 221080 mm^2 (spin-centre-was-centroid + grid-split bug). The engine now circle-fits the spin axis and merges views by spin-centre; the validated A(theta) is the exact annular-sector analytic. No DXF change needed.

## GEOM-VALIDATE flags (r0.1)
- **Island face count (decided by axial section):** the drawn Cx3/Cx4 island is **SINGLE-FACE** — one pickup electrode across the ~4 mm gap, nothing on the other face. The model's 648 pF is the optimistic (solid-area + mica-replaces-air) reading; the single-face value is ~471 pF. **TMD design call:** accept single-face (~471 pF, shuttle re-derived, <8% impact) OR add a second pickup face (differential) to realise the 648 pF — a hardware change. Per-face annotation wanted on the next DXF rev either way.
- **A(theta) magnitude (fixed in the engine):** the geom-extract swept A_max was 156872 mm^2 vs the analytic 221080 mm^2 (spin-centre-was-centroid + grid-split bug). The engine now circle-fits the spin axis and merges views by spin-centre; the validated A(theta) is the exact annular-sector analytic. No DXF change needed.

## GEOM-VALIDATE flags (r0.1)
- **Island face count (decided by axial section):** the drawn Cx3/Cx4 island is **SINGLE-FACE** — one pickup electrode across the ~4 mm gap, nothing on the other face. The model's 648 pF is the optimistic (solid-area + mica-replaces-air) reading; the single-face value is ~471 pF. **TMD design call:** accept single-face (~471 pF, shuttle re-derived, <8% impact) OR add a second pickup face (differential) to realise the 648 pF — a hardware change. Per-face annotation wanted on the next DXF rev either way.
- **A(theta) magnitude (fixed in the engine):** the geom-extract swept A_max was 156872 mm^2 vs the analytic 221080 mm^2 (spin-centre-was-centroid + grid-split bug). The engine now circle-fits the spin axis and merges views by spin-centre; the validated A(theta) is the exact annular-sector analytic. No DXF change needed.

## GEOM-VALIDATE flags (r0.1)
- **Island face count (decided by axial section):** the drawn Cx3/Cx4 island is **SINGLE-FACE** — one pickup electrode across the ~4 mm gap, nothing on the other face. The model's 648 pF is the optimistic (solid-area + mica-replaces-air) reading; the single-face value is ~471 pF. **TMD design call:** accept single-face (~471 pF, shuttle re-derived, <8% impact) OR add a second pickup face (differential) to realise the 648 pF — a hardware change. Per-face annotation wanted on the next DXF rev either way.
- **A(theta) magnitude (fixed in the engine):** the geom-extract swept A_max was 156872 mm^2 vs the analytic 221080 mm^2 (spin-centre-was-centroid + grid-split bug). The engine now circle-fits the spin axis and merges views by spin-centre; the validated A(theta) is the exact annular-sector analytic. No DXF change needed.
