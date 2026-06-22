# Gap topology of record — the real 8-gap commutator (from TMD's schematic)

**Status: COMPLETE.** TMD's `DCCREG_Turbine_circuit.kicad_sch` (43 components) now carries **all eight
commutation gaps**. The connectivity below is **read directly from the schematic geometry** (no labels;
pure wire/junction geometry) by `sim/sch_to_netlist.py`, with a **pin-exact transform (86/86 pins land
on wire endpoints)** — so this is the as-drawn topology, not an assumption.

This supersedes the earlier stale `.net` export (37 components, only `SG3a1`/`SG4a1`) **and** corrects
the provisional spec that had assumed (from the lumped `shuttle_core` node-0 abstraction) that SG1/SG2
returned to ground. **They do not** — see the corrections below.

## Node map (schematic net ↔ machine node)

| node | role | signature members |
|---|---|---|
| **1** | A rail | C1.2, Ca1.1, L_A1–6.1, SG3a1.1 |
| **4** | B rail | C2.2, Cb1.2, L_B1–6.2, SG4a1.1 |
| **2** | AR transfer bank | Ca1.2, C_AR1–6.2, Lx4.1, **SG1.1, SG4b1.2, BS4.2** |
| **3** | BR transfer bank | Cb1.1, C_BR1–6.1, Lx3.2, **SG2.1, SG3b1.2, BS3.2** |
| **7** | island A (Cx3) | Cx3.1, SG3a1.2, SG3b1.1, BS3.1 |
| **8** | island B (Cx4) | Cx4.2, SG4a1.2, SG4b1.1, BS4.1 |
| **R-A** | resonator A end | C1.1, L_R1.1, SG1.2 |
| **R-B** | resonator B end | C2.1, L_R2.2, SG2.2 |

## The 8 gaps, as wired

| ref | kind | nodes | role |
|---|---|---|---|
| **SG3a1** | sparking | (1, 7) | branch-A **load** — A rail → island A |
| **SG3b1** | sparking | (7, 3) | branch-A **fire** — island A → BR bank |
| **SG4a1** | sparking | (4, 8) | branch-B **load** — B rail → island B |
| **SG4b1** | sparking | (8, 2) | branch-B **fire** — island B → AR bank |
| **BS3** | field-emission | (7, 3) | branch-A **FE backstop**, in **parallel** with SG3b1 |
| **BS4** | field-emission | (8, 2) | branch-B **FE backstop**, in **parallel** with SG4b1 |
| **SG1** | sparking | (2, R-A) | **AR bank → resonator tank** (bank fire to output) |
| **SG2** | sparking | (3, R-B) | **BR bank → resonator tank** |

## Two corrections vs the earlier provisional spec (neither changes any verdict)

1. **SG1/SG2 do NOT return to ground (node 0).** The real machine is **floating/differential** (no
   ground symbol in the schematic). SG1/SG2 **fire the transfer banks into the resonator tank** (the
   output stage: bank → `C_R1`/`L_R1`/`L_R2`). The COMMUTATOR-REAL rectifier modeled the *holdoff* on
   the banks (nodes 2,3 can't exceed V_strike), and that holdoff is exactly what SG1/SG2 (plus the
   island-fire gaps SG3b/SG4b) provide — the **destination** of the fired charge (tank vs ground)
   doesn't change the over-transfer bound. So `BRIGADE-RECOVERABLE` (η_real ≈ 0.70) stands.
2. **BS3/BS4 sit in parallel with the island fire gaps** (both span island↔bank, 7↔3 / 8↔2), not on a
   separate bank-to-ground leg. The FE soft-bleed is across the same gap the sparking fire gap fires —
   the budget character (small for a designed backstop) is unchanged.

## Rectifier-role map (what the topology-driven re-derive consumes)

- **V_strike-gated transfer banks:** nodes **2 (AR), 3 (BR)** — held off by the bank-fire gaps
  (SG1/SG2) and the island-fire gaps (SG3b/SG4b). This *is* the rectification the brigade over-transfer
  rings against (the COMMUTATOR-REAL premise, now sourced from the real gaps rather than the diode
  stand-in).
- **FE backstops:** BS3 (7↔3), BS4 (8↔2) — the Fowler-Nordheim soft bleed, onset 0.6·V_strike.
- **Island commutation:** SG3a/SG4a load the islands from the rails; SG3b/SG4b fire them into the
  cross-coupled banks (with Lx3/Lx4 the resonant series inductors).

## Optional cleanup (not blocking)

The gaps are drawn as generic `Jumper:SolderJumper_2_Open`. The parser already classifies them by the
**`SG*` / `BS*` naming convention**, so the topology check works as-is. For a self-documenting
schematic, the custom symbols in **`docs/kicad/symbols/dccreg_gaps.kicad_sym`** (`Spark_Gap`, `FE_Gap`)
can replace the jumpers at TMD's convenience — purely cosmetic; the netlist/topology are already
correct.

## Tooling

- `sim/sch_to_netlist.py` — reconstructs connectivity from the schematic geometry (pin-exact).
- `sim/netlist_gaps.py` — the 8-gap consistency check + the rectifier-role map.
- `sim/rederive_from_gaps.py` — regenerates `topology_edge_list.csv` from the schematic and re-runs the
  verdict chain against the real gaps.
- `topology_edge_list.csv` — regenerated from the schematic (43 components, pin-calibration 86/86).
