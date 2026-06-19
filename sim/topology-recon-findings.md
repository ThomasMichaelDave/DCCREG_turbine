# Findings — Topology recon: `varcap.cir` v0.2 ↔ DXF

**Branch** `topology-recon` (off `main`). **Verdict:** **`TOPOLOGY-INCOMPLETE`** — the recon's two named
authorities are **absent** from the repo (the DXF *r0_15 EE schematic* does not exist — only the r0_6 radial
layout — and the **24 motor (Cem) components are undrafted in any DXF**). The *reconcilable* part **holds**:
the 18 doubler-core / commutation / resonator components map cleanly to the r0_6 layer encoding + the
freeze-doc node map, the **A/B symmetry is exact** (no right-half mislabel), and the **four `[?]` gaps resolve
exactly as the deck assumes** (SG3a 1-7, SG4a 4-8, BS3 3-7, BS4 2-8 — freeze §5 + physics). This is a
**provenance gap + a real DXF omission, not a discrepancy** — no edge disagrees; parts are *missing from the
DXF*, not *wrong in the deck*. `varcap.cir` v0.3 (the `[?]` cleared, the full 42-component graph from the
available authorities, provenance stamped) and `topology_edge_list.csv` (the manifest of record) are emitted;
full `CONFIRMED` waits on drafting the motor + an actual EE-schematic DXF.

**This is a connectivity check, not a model/dimension check** — only *which component connects which node*.
DXF and frozen solvers read-only (empty-diff asserted).

---

## Stage A — the provenance reality (the brief's premises are partly stale)

Parsing the repo with `ezdxf` found that **the artifact the brief names does not exist**:
- **No `r0_15` EE schematic.** Only `docs/varcap-nodeanalysis-template-r0_6_TMD_layout.dxf` — a **radial
  layout template** that encodes node→component via *layer names*, not drawn schematic nets.
- **No polar-array** (INSERT count = 0). **BS3/BS4 are explicit layers** (`SG-BS3-BACKSTOP`,
  `SG-BS4-BACKSTOP`), *not* "hidden in a polar-array block" — so that named hazard is absent.
- **No right-half mislabel.** The r0_6 layers are correctly and symmetrically named (`ND1-C1` / `ND4-C2`,
  `SG3a` / `SG4a`, `BS3` / `BS4`) — the "copy-without-renumber" artifact the brief expected is **not present**.
- **No motor.** Zero `L_A`/`C_AR`/`L_B`/`C_BR`/C-core/440 nF layers — **the 24 Cem components are undrafted in
  any DXF**; they live only in the Block-D doc + the deck.

So the recon proceeds against the **available** authorities: the r0_6 layer encoding (geometry), the freeze
doc node map + spark-gap table (the schematic-level wiring), the Block-D Cem map, and charge-pump physics.

## §4 named checks

| # | check | result |
|---|---|---|
| 1 | DXF parsed; polar-array exploded; node labels extracted | r0_6 parsed; **no array** (0 INSERTs); BS3/BS4 explicit |
| 2 | DXF edge list by terminal-geometry / layer junction | core/comm/resonator node map recovered from layer names |
| 3 | **symmetry audit** | **A/B symmetry exact** (7/7 pairs mirror under 1↔4,2↔3,5↔6,7↔8,9↔10); no mislabel |
| 4 | **the four `[?]` resolved** | SG3a **1-7**, SG4a **4-8**, BS3 **3-7** (blocks 3→7), BS4 **2-8** (blocks 2→8) |
| 5 | **manifest completeness** | 18 core present; **24 motor absent from any DXF** (real omission); no orphans |
| 6 | reconciled v0.3 + edge list emitted | `varcap_v0_3.cir`, `topology_edge_list.csv` |
| 7 | verdict | **`TOPOLOGY-INCOMPLETE`** |

## Stage B — symmetry audit (the mislabel catcher)

The machine is A/B symmetric. Under the node mirror **1↔4, 2↔3, 5↔6, 7↔8, 9↔10**, all seven left/right pairs
are **mirror-consistent**:

| left | nodes | right | nodes | mirror |
|---|---|---|---|---|
| C1 | (1,5) | C2 | (4,6) | ✓ | Ca (1,2)↔Cb (3,4) ✓ | Cx3 (7,3)↔Cx4 (8,2) ✓ |
| SG1 | (2,5) | SG2 | (3,6) | ✓ | SG3a (1,7)↔SG4a (4,8) ✓ | SG3b (7,3)↔SG4b (8,2) ✓ | BS3 (3,7)↔BS4 (2,8) ✓ |

**No asymmetry, hence no right-half mislabel.** (The brief expected the artifact; the r0_6 layers are clean —
a *positive* finding for the geometry, and it means the deck's right-half edges are trustworthy.)

## Stage C — the four `[?]` resolved (the load-bearing unknowns)

| `[?]` | resolved | authority | physics |
|---|---|---|---|
| **SG3a** | **1-7** | freeze §5 "node 1 → bar" | loads the bucket from ND1 onto island-7 |
| **SG4a** | **4-8** | freeze §5 "node 4 → bar" | loads from ND4 onto island-8 (mirror) |
| **BS3** | **3-7** | charge-pump physics | blocks the **reverse** of SG3b's 7→3 fire (i.e. 3→7) |
| **BS4** | **2-8** | charge-pump physics | blocks the **reverse** of SG4b's 8→2 fire (i.e. 2→8) |

All four resolve **exactly as the deck assumes**. The one-way shuttle is coherent: **load (SGxa) → island
pickup (Cx) → fire (SGxb) → backstop (BSx) blocks the reverse**. SG3a/SG4a are pinned by the freeze §5
spark-gap table directly; BS3/BS4 nodes by the manifest and their *blocking sense* by physics (a backstop
that blocked the wrong way would short the fire path — it doesn't). The r0_6 DXF carries the gap *bodies* as
layers but, being a radial template, not the wired nodes — so the **freeze doc + physics are the deciding
authority** here (the r0_15 schematic that would have shown the nets is absent).

## Stage D — manifest completeness

- **18 / 42 present & reconcilable** — the 6 doubler-core + 8 commutation + the resonator C_R (and the 9/10
  hemispheres) map to the r0_6 layer encoding + the freeze node map.
- **Split coil L_R1/L_R2/K1** — the freeze hub geometry is drafted as a *single* hub coil; the **split**
  (coil-topology/S7) is not yet in r0_6 (a representation gap, flagged).
- **24 / 42 absent — the motor.** `L_A1-6`, `C_AR1-6`, `L_B1-6`, `C_BR1-6` are **undrafted in any DXF** — a
  **real omission** (the design exists in Block-D + the deck; the next DXF rev must draft the 12 C-core irons +
  440 nF caps onto nodes 11–22). No orphans in the reconciled graph (every node has ≥ 2 connections).

## Verdict + roadmap

**`TOPOLOGY-INCOMPLETE`** (classification: **provenance gap + real-omission, not a discrepancy**). The graph
*as reconcilable* is correct and the four `[?]` are cleared, so the deck's connectivity is trustworthy where
it can be checked — but the recon cannot return `CONFIRMED` because (1) there is no EE-schematic DXF to diff
the *wiring* against (only a radial layout giving node assignment via layer names), and (2) the motor is
absent from every DXF. **What unblocks `CONFIRMED`:** draft the 24 Cem components (and the split coil) into the
DXF, and produce an actual EE-schematic rev (the brief's "r0_15") — then the wiring can be diffed net-for-net.

**Deliverables for the lock:** `topology_edge_list.csv` is the **manifest of record** (42 components, node_a /
node_b / source / authority / `[?]`-resolved) that v0.11 should freeze against; `varcap_v0_3.cir` is the
reconciled graph with the `[?]` cleared and the provenance honestly stamped. The shuttle/Cem **model upgrades**
(the next brief) **may proceed on the 18-component core + the resolved shuttle path** — that part of the graph
is locked — but should treat the motor branch as deck-only until the DXF catches up.

## Deliverables

`sim/topology_recon.py` (ezdxf parser of the r0_6 layer encoding + symmetry audit + the `[?]` resolution + the
manifest diff; manifest-count self-test = 42) · this findings doc · `topology_edge_list.csv` (the manifest of
record) · `varcap_v0_3.cir` (`[?]` cleared, provenance stamped). DXF read-only; frozen empty-diff asserted.
**Not merged.**
