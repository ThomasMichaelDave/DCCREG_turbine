# DXF flags — r0.15 EE schematic (for the next drawing rev)

The r0.15 schematic is committed and confirms the deck graph (TOPOLOGY-CONFIRMED). One soft flag remains for cosmetic cleanup (does **not** block the lock):

## FLAG — ND7/ND8 label-position asymmetry (DXF, soft)

- ND7 label @ (1574.389168460322, 1436.72634823195), ND8 label @ (1855.705060494227, 1435.87167619824). Under the A/B mirror about the schematic centre (x=1793), ND8 should sit near x=2012 but is at x=1856 (~157 off). Every other node pair mirrors exactly.
- **Classification:** a label-POSITION asymmetry, not a proven connectivity error. The island ND8's connectivity (Cx4 8-2, SG4a 4-8, SG4b 8-2, BS4 2-8 — the group-B mirror of ND7) is coherent with freeze §5 and the deck. Likely a drafting-layout choice (the island body drawn at its physical position). **Action:** verify the ND8 label/body placement in the next rev for visual symmetry; no deck change needed.

## Method note (not a flag)

The doubler/commutation symbols are drawn as raw primitives (lines/circles/splines), not blocks with named terminals, so an isolated per-symbol terminal trace is not robustly extractable. Those edges are confirmed by node-layout + symmetry + freeze §5 + the spatially-separable traced subset (C_R, SG1, SG2, C2). For a future fully-automated net-for-net diff, drawing the components as blocks with attributed terminals would let the tracer resolve every edge unambiguously.
