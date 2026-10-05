# Motor geometry: the C-EM / utron from the designer's STEP, placed outside the spark-gap zone (2026-10-05)

**Code and outputs**
- Code: `sim/motor_geometry.py`. Results: `sim/motor_geometry_results.json`. Picture: `docs/geometry/motor/motor-il2f-6563b90d-rc40.png`.
- Source: `docs/geometry/motor/C-em_and_motor_coil_export.step`, from Fusion 360. It holds one C-EM and one utron, spaced as
  the designer drew them.
- Outputs:
  - `docs/geometry/il2f-6563b90d-rc40-motor.step`: the CAD build plus the motor. Each piece is stored once and placed 12×
    (C-EM) or 6× (utron).
  - `docs/geometry/motor/motor-il2f-6563b90d-rc40.step`: the motor only.
  - `docs/geometry/motor/src/*.step`: each source solid in its local frame.
  - `docs/geometry/motor/il2f-6563b90d-rc40+motor.json`: the build plus the motor in the `pump-geometry/1` schema, for
    `tools/pump-geometry.FCMacro` and the Fusion add-in. Both now accept `shape: "import"`.

## Frame and placement

The frame is read from the solids [IR]:
- x is radial; the C opens toward the axis;
- y is tangential, the utron's direction of travel;
- z is axial;
- the local origin is the utron centre (292, 0, 0).

The source places the utron centred between the jaws (aligned). Of the source products, only `trunion pair` is not used: it
has no geometry, and the designer will add the trunnions later.

| item | value |
|:--|:--|
| outermost stator object of the build | SG4a1 stem, r 563.0 (stems and lead frame at r 560; the spark-gap spheres reach only r 427) |
| clearance used (`--r-clear`) | 40 mm |
| utron centre | r 627.4 mm, z 0 (the septum plane) [OC] |
| motor radial extent | utron coil r 603.9 (innermost) … C-EM spool r 764.3; machine Ø grows from 1.12 m to 1.53 m |
| C-EMs | 12, at the register stations (A 30 + 60k, B 0 + 60k), stator |
| utrons | 6, at 15 + 60k (rotor angle 0), rotor |
| air gap jaw – utron | 7.0 mm (core), 5.5 mm (coil), each side |

Copies are made by translation and rotation only. The tips are asymmetric in y (chamfered), so the sense of rotation matters. If
the chamfer should lead the other way, the C-EM needs mirroring in y. **[OPEN]**

## Checks (`sim/motor_geometry_results.json`)

| check | result |
|:--|:--|
| **G-MOT-ZONE**: every motor piece beyond r 563 + 40 | PASS (min r 603.9) |
| **G-MOT-SWEEP**: the rotor's utron ring vs every stator solid (build + C-EM, exact); the C-EM ring vs every rotor solid | PASS: no overlap |
| **G-MOT-MACRO**: the FCMacro (through the OpenCascade stand-in) vs the instanced STEP, all 66 solids | PASS: volume 1e-12, centroid 3e-11 mm |
| **G-MOT-TRUNNION**: band r 500 … 604, z ±25 must be free of stator parts (a rotor spoke sweeps it at every angle) | **FAIL**: the 12 frame leads SG3a1_lead_ka / SG4a1_lead_ka run axially at r 560 from z −116 to +67 |
| **G-MOT-LEAD**: lead SG-k → C-EM coil (the mid node mA_k / mB_k) vs the 3.3 pF per-node budget (v4 pump check) | **FAIL bare**: ≥ 568 mm (26.8° of arc to the nearest SG sphere), ≈ 7.9 pF bare |
| jaw – utron capacitance at alignment | 1.5 pF parallel-plate (604 mm² per jaw overlap, 7.0 mm), about 3 pF with fringing [RH] |

What follows from the two FAILs:
1. **Trunnion band.** The rotor reaching the utrons at z = 0 needs those 12 leads rerouted so they do not cross |z| < 25 between
   r 500 and 604. They are generator routes (node 1 / node 4 to their carriers), so this is a generator change, not a physical
   constraint. The alternative is a rotor drum carried from the outer flanges, but then the stator has to reach the C-EMs around
   it.
2. **The mid-node lead.** It cannot be made short: the gap sits at the rotor-tip radius (r ≈ 410) and the coil at r ≈ 730.
   - Use a **screened lead**: inner conductor = mA_k, screen = the coil's rail end (node 2 / 3), with the core bonded to the screen.
   - The lead capacitance then sits across the coil. About 100 pF/m × 0.57 m ≈ 57 pF there costs Δz ≈ −0.024 (v4: 50 pF across
     each coil → z 1.303 at 1 pF/node). That replaces the −0.07 to −0.17 that 8 pF of bare node stray would cost.
   - The cable must hold the full gap voltage between core and screen (kV class).
   - Moving the C-EM stations radially over their gaps (A at 3 + 60k, B at 33 + 60k) removes the arc (route ≈ 380 mm) but not
     the need for a screen. The torque phase is set by the utron angle relative to the C-EM at firing, so the pole angles move
     with the stations.

The floating utron passes A cores (node 2) and B cores (node 3) alternately, every 15°. That makes it a small charge carrier
between nodes 2 and 3, of about 3 pF. It is not yet in the pump model. **[next: rt_engine check]**

## The utron coil: open or shorted? (classic theory)

**Coupling.** Both halves of the utron winding have the same area vector: about 49,800 mm² per half, pointing along (−x −z)/√2.
So the winding links the jaw-to-jaw (z) flux with an effective N·A ≈ 70,500 mm². It is not decoupled.

**The force.** The energy method gives F = ½ i² dL/dx for the C-EM coil, with L its inductance as seen at the terminals.

- **Open coil (or no coil).** The utron acts as iron in the gap. L rises as it enters the jaws, so the force attracts it toward
  alignment. This is a switched-reluctance drive: fire while the utron approaches (the planned re-clock). The open winding does
  nothing for the force, but at its ends it sees e = N·A·dB/dt. For example, 0.1 T rising in 7.5 µs gives ≈ 0.94 kV. An open
  winding therefore needs kV insulation, or it should be left off. It could be kept as a pickup coil for firing timing.
- **Shorted coil.** For a shorted winding the time constant is τ = L₂/R₂. With 4.6 m of wire per half (about 0.1 Ω at 1 mm Cu),
  τ is far longer than the 15 µs pulse. So the shorted winding keeps the flux out of the utron, and L_eff = L₁(1 − k²) *falls*
  as the utron enters. The force repels: an induction / Thomson-repulsion drive. It must fire *after* alignment, and the
  winding's I²R loss takes a share of every pulse comparable to the work it does.
- **Which is stronger.** Jaw-to-jaw is 60 mm and the utron is 46 mm, which leaves 14 mm of air. A permeable utron changes the gap
  reluctance over its footprint by about 4× (ΔL/L up to about 0.7). Shorted, the swing is k² of the linked flux (about 0.3–0.5).
  [RH]
- **Advice: leave the coil open (or omit it) and make the utron magnetically fast.** Reluctance gives the larger swing with no
  secondary loss, and it keeps the clocking already worked out. Go shorted only if you choose the repulsion drive. The utron then
  need not be iron at all: a Cu / Al block works.

**The material governs either way (classic skin effect).**
- A 15 µs half-sine is about 33 kHz. Skin depth δ = √(2ρ/ωμ):
  - solid low-carbon iron: δ ≈ 0.03 mm;
  - Si-steel: δ ≈ 0.06 mm.
- A **solid iron utron is itself a shorted turn**: the eddy currents exclude the flux. The intended reluctance utron would behave
  as a lossy repulsion block.
- The register's C-EM core (Si-steel, **0.35 mm** laminations) carries the pulse flux in a skin of about 0.06 mm. Its effective
  permeability collapses.
- **Both cores need ferrite (MnZn), or tape of 0.05 mm or less (amorphous / nanocrystalline).**
- The 0.64 H / 40 Ω per C-EM used so far is an engine default, not derived from this geometry. It should be recomputed from this
  core and winding. **[next]**
