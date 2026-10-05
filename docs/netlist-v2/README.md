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
