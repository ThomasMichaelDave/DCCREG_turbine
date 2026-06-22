# Reference — every value → the schematic and the cross-section

This is the **single source** for the tool's reference drawer (the "ⓘ reference" button renders this
file; there is no second copy). Every free variable and readout is mapped to **where it lives on the
schematic** (the netlist of record `topology_edge_list.csv` → `schematic.svg`) and **where it lives on
the cross-section** (the authoritative DXF → `cross-section.svg`). The two artifacts are generated from
their SSOTs by `tools/gen_artifacts.py`, so they cannot silently drift from the design. *(The schematic
SSOT is `topology_edge_list.csv`, the DXF-sourced r0.15 netlist of record; `varcap.cir` is not on this
branch. TMD is the design authority on the final schematic aesthetic; this draft derives from the
netlist — connectivity-checked: **42 components, 22/22 nodes, MATCH**.)*

## Free-variable glossary (verified against the netlist + the DXF)

| free var (UI) | physical referent · units | schematic (netlist) | cross-section (DXF) | sets |
|---|---|---|---|---|
| **`r_out`** active band | varicap plate outer radius · mm | — (geometry) | **R387** active-band outer | plate area → C_max → rotor dia |
| **`g_v`** varicap gap | axial rotor↔stator plate gap · mm | C1/C2 (nodes 1‑5, 4‑6) | the **ND1↔ND9** axial gap | C_max (with the area) |
| **geometric `C_min`** | dis-aligned varicap minimum · pF | C1/C2 nodes | min plate overlap | the modulation floor (geometric) |
| **`Ca`** transfer cap | bucket-brigade transfer cap · pF | **Ca 1‑2 / Cb 3‑4** (309 pF) | the Ca electrode hatch | the transfer match Ca/C_max → z |
| **`C_par`** parasitic floor | unavoidable stray · pF | (not drawn) | — | the real C_min floor (I6) |
| **`C_x,max`** island | flying-bucket max cap · pF | **Cx3 7‑3 / Cx4 8‑2** (island net) | **ND7 / ND8** bars (~R350) | Q_isl, W_coll, E_fire (the shuttle) |
| **`C_R`** tank | resonator capacitance · pF | **C_R, nodes 9‑10** | the **12 mm septum** (centre) | f₀ (with L_R), the tank store |
| **`rpm`** drive | shaft speed · rev/min | — | — | PRF, rim speed (R491) |
| **objective** | the search target | — | — | which design `synthesize()` returns |

*All mappings above were checked against `topology_edge_list.csv` node names and the DXF
layers/ref-radii; no corrections were needed (the netlist names C1/C2/Ca/Cb/Cx3/Cx4/C_R exactly, and
the DXF carries R95/R387/R491/R500 + the ND1/ND9/ND7/ND8 layers and the MECH-DIELECTRIC septum).*

## Readouts → where they live

| readout | meaning · units | schematic | cross-section | from |
|---|---|---|---|---|
| **rotor diameter** | the spinning body diameter · mm | — | **R491** rotor outer (active band R387 **+ 0.27 bus**) | geometry |
| **z** | doubler per-cycle pump gain | the 4-node core (1‑2‑3‑4) | — | **frozen `doubler_core`** |
| **η** | net-electrical fraction (1 − C‑C tax) | the 4-node core | — | **frozen `doubler_core`** decomposition |
| **C_max** | varicap max cap · pF | C1/C2 | the 6 plate wedges (R95–R387) | ε₀·area/gap (geometry) |
| **W_coll** | island collapse work · mJ | Cx3/Cx4 island net | ND7/ND8 bars | **frozen `shuttle_core`** |
| **E_fire / C_fire** | fire energy / cap · mJ / pF | island → tank | bars → septum | frozen `shuttle_core` |
| **rim** | rim speed at the body · m/s | — | at **R491** | rpm × R491 |

## The invariant battery — bound + the (uniform) slack reference

Slack is the **signed fractional headroom to that invariant's bound, normalized by the bound**
(`0` = at the wall/binding, `<0` = violated, `0.10` = 10 % headroom). For the two-sided z band (I3) the
headroom is to the **nearer edge**, normalized by that edge (not the band width) — so it is
apples-to-apples with the one-sided limits.

| invariant | bound · reference | anchor value → slack | role |
|---|---|---|---|
| **I1** conservation | structural ±1 | ledger resid ~1e‑16, +5 % trip **fires** → +1 | a consistency-check-that-trips (**not** "BALANCED"); torque-sim character |
| **I2** solver authority | structural ±1 | z/η/W_coll valid (frozen) → +1 | the frozen solver is the sole z/η/W_coll authority |
| **I3** scale-free z | band **[1.20, 1.45]**, nearer edge | z 1.334 → **0.080** | shrinking/efficiency limiter (modulation collapse) |
| **I4** insulate-first | V_bd > **V_target 15 kV** | 39.6/15 kV → 1.64 | gap holds the hold; septum holds; split-coil antinode out |
| **I5** tax managed | η ≥ **η_min 0.15** | 0.386/0.15 → 1.58 | stage N if the tax dominates |
| **I6** parasitic floor | C_par ≥ **20 pF** (mod-margin) | (C_max−C_par)/C_par → **~13** | reads **large = loose by design**; teeth are indirect (→ I3) |
| **I7** motor matched | output ≤ **pump_net** | 3.7/6.2 mJ → 0.40 | f_res = PRF; high-Z spectator at f₀ |
| **I8** DC-trapped tank | structural ±1 | held DC → +1 | dielectric duty-limited; not the voltage lever |
| **I9** mechanical | rim < **200 m/s** (soft 150) | 154/200 → 0.23 | supercritical; vacuum ≤ 10 Pa |
| **I10** shuttle integrity | strike < **ceiling 21 kV** | 20/21 kV → **0.048** | **the anchor's binding rule** — island strike margin |

**Binding = the least slack** (now apples-to-apples). At the established anchor the ranking is
**I10 (0.048) < I3 (0.080) < I9 (0.23) < I7 (0.40) < …** → the machine is **shuttle-strike-bound**.

## The two artifacts

- **`cross-section.svg`** — generated from the DXF ref-radii (R25/R95/R387/R491/R500) with the named
  features: the 6 varicap plate wedges (ND1/ND9, R95–R387), the island bars (ND7/ND8, ~R350), the C_R
  septum (12 mm, centre), and the 12 Cem cores (~R440).
- **`schematic.svg`** — generated from `topology_edge_list.csv`: the 4-node doubler core (1‑2‑3‑4), the
  rail (5‑6), the islands (7/8), the tank (9‑10), and the two Cem banks (11‑16 / 17‑22), with the
  connectivity check stamped (42 components, 22/22 nodes, MATCH).

Regenerate both with `python3 tools/gen_artifacts.py` whenever the DXF or the netlist updates.
