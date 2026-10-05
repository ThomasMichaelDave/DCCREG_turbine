# Netlist v2 (KiCad DCCREG_Turbine_circuit_v2, 2026-10-05)

`topology_edge_list_v2.csv` comes from the KiCad export (`.net`), plus the schematic plot for the six spark gaps the
export does not carry. SG1, SG2, SG3b1, SG4b1, BS1 and BS2 have no pins in the export. Node names follow the
netlist of record (1–4, 7, 8, R-A, R-B); renamed parts are given in `nr_name`. The netlist of record,
`topology_edge_list.csv`, is unchanged.

**As drawn, two points stop it being runnable:**
1. **L_A1…6 sit in parallel with SG1 (2 – R-A), and L_B1…6 in parallel with SG2 (3 – R-B).** At low frequency that
   is a 0.107 H short across each rail gap.
   - Series form: 2 → L_A1…6 → m_A → SG1 → R-A, and 3 → L_B1…6 → m_B → SG2 → R-B.
   - Physically, one coil per gap station, on the stator side.
2. **The tank.** The sheet note says C_R is the capacitance between the rotor electrodes (R-A, R-B). The four coils
   sit across it as a parallel tank. The wiring, though, puts C_R mid-chain.
   - Parallel form (the register's RA form): L_R1 – L_AH1 – join – L_AH2 – L_R2 from R-A to R-B, with C_R1
     directly R-A – R-B.

## v3 (2026-10-05 13:36): pump check in rt_engine, RT0 configuration, parallel tank (425 µH ∥ 789 pF, Q 30)

The tank in v3 is parallel: C_R1 across R-A / R-B. The C-EMs are still drawn in parallel with SG1 / SG2.
Each group is modelled as six coils in parallel (0.107 H, 6.7 Ω), with constant L; the torque model is not in yet.

| case | z (RT0 anchor 1.3254745) |
|:--|:--|
| parallel tank only | 1.325472 |
| v3 as drawn: C-EMs in parallel with SG1 / SG2 | **0.554: the pump dies** |
| series form 2 → L_A → m_A → SG1 → R-A (B mirrored), m_A → reference 2 pF | 1.3488 |
| same, 5 / 10 / 20 / 50 / 100 pF | 1.3319 / 1.3077 / 1.2652 / 1.1772 / 1.0435 (not converged) |
| m_A → ref 2 pF, plus 50 / 200 / 1000 pF across the coil | 1.3345 / 1.3181 / 1.3181 |

Design rule from this: keep the capacitance of the coil–gap node to the rest of the machine low (≤ about 20 pF for
z ≥ 1.26). Capacitance across the coil is harmless. For the C-EM core this means bonding it to the coil's rail end
(node 2 / 3), so the winding capacitance sits across the coil rather than to ground (D-6).

## v4 (2026-10-05): C-EMs in series with their own gaps, parallel tank, so this is the series form

From the v4 PDF:
- each C-EM has its own gap: 2 → L_Ak → mA_k → SG1-k → R-A, and 3 → L_Bk → mB_k → SG2-k → R-B, for k = 1…6;
- C_R1 is directly across R-A / R-B, with L_R1 – L_AH1 – L_AH2 – L_R2 across it.

The `.net` export still carries no spark-gap pins: every SG line in the `.cir` is node-less. The gaps in
`topology_edge_list_v4.csv` are therefore taken from the PDF.

**Pump check.** `sim/netlist_v4_pump.py` runs rt_engine with the RT0 configuration and the parallel tank (425 µH ∥ 789 pF,
Q 30). Each side has six coils (0.64 H, 40 Ω), each with its own gap. Every SG1-k / SG2-k copies the RT0 rail gap, so all
six on a side fire at the same angle. L is held constant. Results are in `sim/netlist_v4_pump_results.json`.

| stray per coil–gap node to the machine | z (RT0 anchor 1.3254745) |
|:--|:--|
| 0.5 pF | 1.3437 |
| 1 pF | 1.3266 |
| 2 pF | 1.2990 |
| 3.3 pF | 1.2660 |
| 5 pF | 1.2325 |
| 10 pF | 1.1533 |
| 1 pF, plus 50 pF across each coil | 1.3030 |
| lumped equivalent (one 0.107 H coil, 6 pF node) | 1.3266 (equal to the 1 pF per-coil case) |

The six per-coil node strays add up. The lumped rule of ≤ about 20 pF (z ≥ 1.26) becomes **≤ about 3.3 pF per coil–gap
node**. That covers each mA_k / mB_k node, its SG1-k / SG2-k sphere, and the lead between them.

The v3 note that capacitance across the coil is harmless was too strong. 50 pF across each of the six coils (300 pF
lumped) costs Δz ≈ −0.024. That is still much milder than node stray, so bonding the core to the rail end (D-6) remains the
right choice.

To keep the node small, keep the coil-to-gap lead short and keep the gap sphere small and well away from the rotor body and
the other rail.
