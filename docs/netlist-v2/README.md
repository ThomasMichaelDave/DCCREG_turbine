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
