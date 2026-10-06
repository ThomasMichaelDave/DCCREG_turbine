# Gates and open forks

## Gates, in order (fail-closed: stop at the first fail)

| id | check | pass criterion | tool |
|:--|:--|:--|:--|
| **G-LEDGER** | baseline ledger reproduces | `sim/tube_ledger.py`: closure ≤ 1e-12 J, belt 2.46–2.47 W, surplus 1.31–1.76 W | existing |
| **G-LOAD** | the pump holds its operating voltage while loaded | add a DC-link tap (load diodes + reservoir) and a constant-power load P_m to the v4 tube net in `rt_engine`; find the largest P_m at which the link holds 20 kV and z ≥ 1 at the limiter | new, `sim/` |
| **G-LEDGER-L** | the ledger still closes with the load | belt = growth + losses + P_m, closure ≤ 1e-12 J | extends `tube_ledger.py` |
| **G-SWING** | the PM-biased toothed C-core gives the assumed flux swing | 2-D/3-D magnetostatic solve (the `tube_magnetic.py` analogy plus a PM source) of one toothed C-EM over one tooth pitch: ΔΦ ≥ 0.3 mWb, no saturation | extends `tube_magnetic.py` |
| **G-EMF** | the string matches the link | 12 coils × N × π·f·ΔΦ = 20 kV ± 10 % at 300 rpm relative | `reverse_vdg_budget.py` with the G-SWING ΔΦ |
| **G-TORQUE** | torque ≥ drag | η·P_m(G-LOAD) / ω_rel ≥ stator drag for the chosen enclosure (19 mN·m shell/vacuum) | budget |
| **G-HV** | each C-EM and switch at its string potential clears its neighbours | the clearance gates already used for the tube STEP (G-TUBE-CLASH/GAP) plus a per-coil ΔV rule | `tube_geometry.py` |
| **G-STEP** | the toothed ring and the toothed jaws build and sweep clean | G-TUBE-CLASH 0, G-TUBE-SWEEP 0, read-back n/n | `tube_geometry.py` |

G-LOAD decides everything. If the loaded pump cannot sustain 20 kV at about 1 W of draw, nothing downstream matters.

## Open forks: the designer's decisions

- **F1 — enclosure.** The drive only closes with windage removed. A shell (still air, no bluff-body drag) or vacuum.
  Vacuum was deferred: avoid 1e-3–10 mbar (Paschen), use ≤ 1e-4 mbar or a gas fill.
- **F2 — bias.**
  - PM in the C-core spine: modern flux-switching PM, torque ∝ i, solid magnet if the flux is steered (the patent's
    alternative).
  - A DC field winding on the same core: no magnets, but it costs link power.
  - Without bias the machine is ∝ i² and fails like today's C-EMs.
- **F3 — string.** One 12-coil string across both sides, or two 6-coil strings (A, B), each at 20 kV with twice the turns.
- **F4 — switch per coil.**
  - A 1.7 kV SiC MOSFET or IGBT with an optical gate.
  - Or a rotor-segment commutator. At 88 µA, arcing is negligible; the patent avoided commutators for current, not
    voltage.
  - Or a thyristor pair, if the coil current can be brought to zero each stroke.
- **F5 — the rotor ring.** Laminated SiFe 0.1–0.2 mm, or SMC, with 60 teeth at r 130. It replaces the 3 utrons per
  side; the utron hub stays as its carrier.
- **F6 — worth it at all?**
  - The electrical path spends the pump's whole surplus, so nothing is left for any other HV load.
  - It costs the belt 2–4× what a reversing gear costs for the same counter-rotation.
  - Its merit is no mechanical link between rotor and stator. Whether that is worth it is the designer's call.

## Out of scope for the block

- The real RA hub.
- The outer stator guides and the shell structure.
- Wiring rails.
- Field-solved tube strays.
- Gas fill and vacuum hardware.
