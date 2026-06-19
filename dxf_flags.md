# DXF punch-list — what the EE-schematic DXF (the brief's r0_13/r0_15) must contain

**Status:** the recon is BLOCKED on a schematic DXF that has never been committed. Two briefs (r0_15, then r0_13) assumed it exists; an exhaustive scan of all git history finds only radial-layout templates. To unblock `TOPOLOGY-CONFIRMED` and v0.11, an EE-schematic DXF must be committed with:

1. **Drawn nets** (wires/polylines + symbol terminals), not just layer-named bodies — so
   connectivity can be traced by spatial junction (the methodological point of r0.2).
2. **The split resonator** — nodes ND9/ND10 with L_R1(5-9) + C_R(9-10) + L_R2(10-6).
   (Absent from every committed DXF; the radial templates draw a single hub coil.)
3. **The 24 motor components** — L_A1-6/C_AR1-6 (nodes 11-16, across Ca: coil-outer ND1,
   cap-inner ND2) and L_B1-6/C_BR1-6 (nodes 17-22, across Cb: ND4/ND3). The 12 quadricore
   irons + 440 nF caps. (Undrafted in every committed DXF.)
4. **The four [?] gaps as drawn nets** — SG3a 1-7, SG4a 4-8 (load), BS3 3-7, BS4 2-8
   (backstop, blocking the reverse of the 7->3 / 8->2 fire) — to confirm the freeze-§5 +
   physics resolution against the actual drawing.

**Latest committed DXF:** `varcap-nodeanalysis-template-r0.2.dxf` (49 layers, radial layout, no ND9/10, no motor, 0 INSERTs). It is a geometry template (node->component via layer names), not a wired schematic — sufficient for r0.1's layer-name recon, not for r0.2's net-for-net diff.

Once committed, re-run `python3 sim/topology_recon.py` — the gate auto-detects the schematic (ND9/10 + motor) and proceeds to the net-trace.
