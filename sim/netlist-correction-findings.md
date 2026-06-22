# Findings — NETLIST-CORRECTION: the real 8-gap topology + the re-derive

**Branch** `netlist-gaps-rederive` (off `commutator-real`). **Trigger:** COMMUTATOR-REAL flagged that
the KiCad `.net` export was a stale/partial capture (37 components, only 2 of 8 commutation gaps). TMD
supplied the live **`DCCREG_Turbine_circuit.kicad_sch`** (43 components, **all 8 gaps**), which is now
the source of record. **Result:** the real topology is extracted (pin-exact), the 8-gap arrangement is
consistency-checked, and the verdict chain is **re-confirmed on the real topology** — `BRIGADE-RECOVERABLE`
stands (η_real ≈ 0.70, keep Ca/Cb).

## What changed

- **Source of record → the schematic.** The `.net` export (date 15:52) predated the gap work; the
  schematic (43 comps) has `SG1, SG2, SG3a1, SG3b1, SG4a1, SG4b1, BS3, BS4`. The schematic has **no net
  labels** — connectivity is pure wire/junction geometry, so I built a **pin-exact extractor**
  (`sim/sch_to_netlist.py`): every one of the **86/86 pins lands on a wire endpoint**, validating the
  instance transform, and it reproduces the old export's non-gap nets.
- **`topology_edge_list.csv` regenerated** from the schematic (43 components, 24 nets, calibration
  86/86) — supersedes the 37-component version derived from the stale export.

## The real 8-gap topology (read from the schematic)

| ref | kind | nodes | role |
|---|---|---|---|
| SG3a1 | sparking | (1, 7) | branch-A load (A rail → island A) |
| SG3b1 | sparking | (7, 3) | branch-A fire (island A → BR bank) |
| SG4a1 | sparking | (4, 8) | branch-B load |
| SG4b1 | sparking | (8, 2) | branch-B fire (island B → AR bank) |
| BS3 | field-emission | (7, 3) | branch-A FE backstop, **∥ SG3b1** |
| BS4 | field-emission | (8, 2) | branch-B FE backstop, **∥ SG4b1** |
| SG1 | sparking | (2, R-A) | **AR bank → resonator tank** |
| SG2 | sparking | (3, R-B) | **BR bank → resonator tank** |

Consistency check: **8/8 present & consistent** (`sim/netlist_gaps.py`).

## Two corrections vs the earlier (lumped-abstraction) assumption — neither moves a verdict

1. **SG1/SG2 fire into the resonator tank, not to ground.** The machine is floating/differential (no
   ground node). The COMMUTATOR-REAL rectifier modeled the *holdoff on the banks* (nodes 2,3 ≤ V_strike);
   SG1/SG2 + the island-fire gaps provide exactly that holdoff. The fired charge's destination (tank vs
   ground) doesn't change the over-transfer bound → the recovery is unchanged.
2. **BS3/BS4 are in parallel with the island fire gaps** (7↔3, 8↔2), not a separate bank-to-ground leg.
   The FE soft-bleed budget character (small for a designed backstop) is unchanged.

## Re-derive — the verdict chain on the real topology

`sim/rederive_from_gaps.py` confirms the rectifier premise from the real gaps (banks 2,3 are
V_strike-gated by spark gaps; FE backstops parallel to the fire gaps) and re-runs the chain:

| stage | result |
|---|---|
| direct-limit anchor (α→0) | z 1.3340, η 0.3860 (= frozen 1.334/0.386) |
| diode stand-in (doubler-resonant) | z 1.573, η 0.404 — the v≤0 clamp **the real gaps replace** |
| **real gaps (V_strike holdoff)** | α_max **0.807**, z **2.478**, η_gross **0.709** → **η_real ≈ 0.697** (30 µA backstop) |

**`BRIGADE-RECOVERABLE` re-confirmed on the real topology** — the diode-at-0 was the artifact; the real
spark-gap holdoff recovers the brigade tax. `doubler_core`/`shuttle_core` stay frozen; the gaps are
consumed from TMD's schematic of record.

## Deliverables

`sim/sch_to_netlist.py` (pin-exact schematic→connectivity extractor) · `sim/netlist_gaps.py` (8-gap
consistency check + rectifier-role map) · `sim/rederive_from_gaps.py` (edge-list regen + chain re-run) ·
`docs/kicad/DCCREG_Turbine_circuit.kicad_sch` (the source of record, in-repo) ·
`docs/kicad/gap-topology-of-record.md` (the documented real topology) ·
`docs/kicad/symbols/dccreg_gaps.kicad_sym` (optional self-documenting Spark_Gap / FE_Gap symbols) ·
`topology_edge_list.csv` (regenerated, 43 comps). Frozen solvers untouched. **Not merged.**

### Note for TMD

The gaps are drawn as generic `SolderJumper_2_Open`; the parser classifies them by the `SG*`/`BS*`
naming convention, so nothing is blocked. Swapping the jumpers for the custom `Spark_Gap`/`FE_Gap`
symbols is optional (self-documenting only). The official `.net` export can be refreshed from KiCad at
your convenience — the in-repo schematic + the extractor already give the correct 43-component topology.
