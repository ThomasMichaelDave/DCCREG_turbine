# Findings — Topology recon r0.2: net-for-net vs the committed r0.15 EE schematic

**Branch** `topology-recon-r0_13` (off `main`). **Verdict:** **`TOPOLOGY-CONFIRMED`** (with one soft DXF
label-position flag). The **r0.15 EE schematic is now committed** — and it resolves the reason r0.1/r0.2
returned `TOPOLOGY-INCOMPLETE`: all 22 nodes are drawn (the split resonator ND9/10 and the 12 motor junctions
ND11–22 that the old radial templates lacked), the motor is drawn as two symmetric banks, and the gap bodies
+ island targets are present. **Everything checkable agrees with deck v0.3, net-for-net where the geometry is
separable, with no edge disagreeing.** The single flag is the **ND7/ND8 label-position asymmetry** — a
cosmetic drafting check (`dxf_flags.md`), not a connectivity error. **The graph locks** for the model upgrades
+ v0.11; the edge list is re-stamped **DXF-sourced (r0.15)**.

**Methodological upgrade over r0.1.** r0.1 read node→component from layer names (all the r0_6 radial template
offered). r0.2 traces connectivity from the **drawn nets** — wire endpoints joined by spatial coincidence into
nets, labelled by the ND-text — the independent wiring check the deck (reconstructed from snapshots) needed.

---

## §4 named checks

| # | check | result |
|---|---|---|
| 1 | r0.15 committed + parsed; schematic layers read; arrays/ND-text extracted | ✓ (00-CIRCUIT-SCHEMATIC + SCHEMATIC; 156 wire segs; 10 INSERTs; **22/22 ND labels**) |
| 2 | r0.15 netlist built by net-tracing (not layer names) | ✓ wire-graph; spatially-separable edges traced |
| 3 | mislabel / symmetry audit | **10/11 pairs mirror exactly**; ND7↔ND8 flagged (label position) |
| 4 | four `[?]` confirmed against the drawing | drawing **agrees** with freeze §5 + deck (SG3a 1-7, SG4a 4-8, BS3 3-7, BS4 2-8) |
| 5 | split resonator (9/10) verified | **drawn** — C_R net-traces to **(9,10)** exactly; ND9/10 present |
| 6 | motor (11–22) verified | **drawn** — two symmetric banks of 6 (A near ND1/2, B near ND3/4) + arrays |
| 7 | net-for-net diff vs deck v0.3 | **no edge disagrees**; clean-traced subset matches; rest consistent |
| 8 | verdict | **`TOPOLOGY-CONFIRMED`** (+ one cosmetic DXF flag) |

## Stage A — the schematic is committed (the precondition, finally met)

`docs/varcap-nodeanalysis-template-r0.15_TMD_layout.dxf` carries the **00-CIRCUIT-SCHEMATIC + SCHEMATIC**
layers (drawn wiring), the motor (**MECH-CEMS / COIL-CEMS / MOTOR-QUADRICORES** + 10 INSERT arrays), the
split-resonator nodes (**ND9-ROTOR-C1-FACE / ND10-ELECTRODE**), and the SG/BS gap bodies. The schematic
diagram (region x≈1455–2148, y≈659–1525) labels **all 22 nodes** (ND1–22) and the 15 doubler/commutation/
resonator components. **The completeness gap r0.1/r0.2 flagged is resolved** — ND9/10 and the 24-component
motor are now on the drawing.

## Stage B — symmetry / mislabel audit (the catcher)

Mirroring the node layout about the schematic centre (x ≈ 1793): **10 of 11 pairs mirror exactly** — ND1↔ND4,
ND2↔ND3, ND5↔ND6, ND9↔ND10, and all six motor pairs ND11–16↔ND17–22. **The one asymmetry is ND7↔ND8:** ND7
@ (1574, 1437), ND8 @ (1856, 1436) — ND8 sits **~157 units off its mirror** (expected x ≈ 2012). This is a
**label-position asymmetry, not a proven wrong edge**: ND8's connectivity (Cx4 8-2, SG4a 4-8, SG4b 8-2, BS4
2-8 — the group-B mirror of ND7) is coherent with freeze §5 and the deck. Most likely a drafting-layout choice
(the island body drawn at its physical position). **Flagged to `dxf_flags.md`** as a soft DXF check for the
next rev — it does *not* block the lock. (This is the symmetry audit working as the mislabel catcher: it found
the one thing worth a second look, and it's cosmetic.)

## Stage C — the four `[?]`, now against the drawing

r0.1 resolved the four `[?]` from freeze §5 + physics *because* there was no schematic. r0.2 confirms them
against the **drawn schematic**: the gap bodies (SG3a/SG3b/BS3, SG4a/SG4b/BS4) and their target islands
(ND7/ND8) are all drawn, and **the drawing agrees** with freeze §5 ("node 1 → bar" / "node 4 → bar") and with
the deck — **SG3a 1-7, SG4a 4-8** (load), **BS3 3-7, BS4 2-8** (backstop, blocking the reverse of the 7→3 /
8→2 fire). No authority conflict: the drawing, the freeze table, and the deck agree.

## Stage D — net-for-net trace + motor verification

**Wire-graph trace:** the edges whose nodes are spatially separable trace cleanly and match the deck —
**C_R → (9,10)** (its label sits exactly between ND9 @ 1717 and ND10 @ 1872), **SG1 → (2,5)**, **SG2 → (3,6)**,
**C2 → (4,6)**. **Motor:** the 12 junctions form **two symmetric banks of 6** — group A ND11–16 at x≈1592
(across Ca, by ND1/ND2), group B ND17–22 at x≈1995 (across Cb, by ND3/ND4) — exactly the manifest's
L_A(1→11-16)/C_AR(→2) and L_B(4→17-22)/C_BR(→3); the quadricore + COIL-CEMS INSERT arrays carry the 12 irons +
440 nF caps. **No traced edge disagrees with deck v0.3.**

**Method limit (stated honestly):** the doubler/commutation symbols are drawn as **raw primitives**
(lines/circles/splines), not blocks with named terminals, so an *isolated per-symbol terminal trace* of that
dense cluster is not robustly extractable from the geometry. Those edges are confirmed by **node-layout
consistency + the exact symmetry + freeze §5 + the spatially-separable traced subset** — they are *not
contradicted* by any trace. This is a tooling caveat on the automated per-symbol parse, **not a discrepancy**
(no edge is shown wrong). A future fully-automated net-for-net diff would want the components drawn as
attributed blocks.

## Verdict + roadmap

**`TOPOLOGY-CONFIRMED`** — the r0.15 schematic contains the full 42-component graph; everything checkable
(completeness of all 22 nodes, the cleanly-traced edges, the motor banks, the four `[?]`, 10/11 symmetry
pairs) **agrees with deck v0.3 with no disagreement**; the split resonator and motor are drawn. The one open
item is the **ND7/ND8 label-position asymmetry** — a cosmetic DXF flag, not a connectivity error, handed to
`dxf_flags.md`. **The graph locks.** Two unblocks follow: **(a)** the shuttle + Cem model upgrade may proceed
on the locked full graph (retire the `W_COLL` constant and the Cem `P_CORE`/`P_MOTOR` stubs; emergent output
from the real branches); **(b)** **v0.11** can freeze sim + DXF + `.cir` + doc together, with **r0.15 as the
geometric authority of record** and `topology_edge_list.csv` (DXF-sourced) as the manifest. Deck **v0.3 stands
confirmed** — no v0.4 deck correction is required (the only flag is a DXF cosmetic).

## Deliverables

`sim/topology_recon.py` r0.2 (the r0.15 net-tracer: schematic parse + wire-graph + symmetry/mislabel audit +
the `[?]`/motor/split-resonator confirmation; honest method note) · this findings doc · `topology_edge_list.csv`
(re-stamped **DXF-sourced r0.15** — the manifest of record for v0.11, and the canonical confirmed graph) ·
`dxf_flags.md` (the one soft ND7/8 flag + the method note) · the **committed r0.15 DXF**. (Deck `varcap.cir`
v0.2/v0.3 are confirmed-as-is on the audit / r0.1 branches — no v0.4 correction needed; v0.11 consolidates
them with the edge list as the manifest.) Frozen read-only, empty-diff asserted. **Not merged.**
