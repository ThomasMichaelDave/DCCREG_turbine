# Motor geometry: the C-EM / utron from the designer's STEP, placed outside the spark-gap zone (2026-10-05)

**Code and outputs**
- Code: `sim/motor_geometry.py`. Results: `sim/motor_geometry_results.json`. Picture: `docs/geometry/motor/motor-il2f-6563b90d-rc40.png`.
- Source: `docs/geometry/motor/C-em_and_motor_coil_export.step`, from Fusion 360. It holds one C-EM and one utron, spaced as
  the designer drew them.
- Outputs:
  - `docs/geometry/il2f-6563b90d-rc40-FULL-pump+motor.step`: the CAD build plus the motor. Each piece is stored once and placed 12×
    (C-EM) or 6× (utron).
  - `docs/geometry/motor/MOTOR-ONLY-il2f-6563b90d-rc40.step`: the motor only.
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
| motor radial extent | utron coil r 603.9 (innermost) … C-EM spool r 762.4; machine Ø grows from 1.12 m to 1.52 m |
| C-EMs | 12, at the register stations (A 30 + 60k, B 0 + 60k), stator |
| utrons | 6, at 15 + 60k (rotor angle 0), rotor |
| air gap jaw – utron | 7.0 mm (core), 5.5 mm (coil), each side |

**C-EM squared to the utron.** In the source, the C-EM's 30 mm core plate is turned 5.17° about its own z axis, and its mid-plane
sits 8.6 mm off the utron centre. All four C-EM pieces (core, spools, coil) are turned back by −5.17° about the z axis through the
mid-plane, then shifted 8.6 mm tangentially so the mid-plane passes through the utron centre. That shift equals 0.8° of station
angle, which is a clocking variable anyway. `cem_squaring` measures the turn from the core's plate faces and re-checks it to
0.000° after the correction (`placement.cem_squaring`).

Copies are then made by translation and rotation only. The tips are asymmetric in y (chamfered), so the sense of rotation
matters. If the chamfer should lead the other way, the C-EM needs mirroring in y. **[OPEN]**

## Checks (`sim/motor_geometry_results.json`)

| check | result |
|:--|:--|
| **G-MOT-ZONE**: every motor piece beyond r 563 + 40 | PASS (min r 603.9) |
| **G-MOT-SWEEP**: the rotor's utron ring vs every stator solid (build + C-EM, exact); the C-EM ring vs every rotor solid | PASS: no overlap |
| **G-MOT-MACRO**: the FCMacro (through the OpenCascade stand-in) vs the instanced STEP, all 66 solids | PASS: volume 1e-12, centroid 3e-11 mm |
| **G-MOT-TRUNNION**: band r 500 … 604, z ±25 must be free of stator parts (a rotor spoke sweeps it at every angle) | **FAIL**: the 12 frame leads SG3a1_lead_ka / SG4a1_lead_ka run axially at r 560 from z −116 to +67 |
| **G-MOT-LEAD**: lead SG-k → C-EM coil (the mid node mA_k / mB_k) vs the 3.3 pF per-node budget (v4 pump check) | **FAIL bare**: ≥ 567 mm (26.8° of arc to the nearest SG sphere), ≈ 7.9 pF bare |
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

## The utron coil

There is no wire path to the utrons. The utron coils are left open or omitted, and they are **not part of the circuit**. Open,
the winding still picks up e = N·A·dB/dt, about 1 kV at its ends for 0.1 T rising in 7.5 µs (N·A ≈ 70,500 mm² linked to the
jaw flux). It needs kV insulation, or it should be left off. It does nothing for the force: the drive is reluctance, with the
utron pulled toward alignment, so it fires while approaching.

## Utron core material without ferrite (`sim/utron_material.py`, `sim/utron_material_results.json`)

**Model.** The pulse is a 15 µs half-sine, about 33 kHz. The circuit is gap-dominated: aligned, the 60 mm between the jaws is
46 mm of utron plus 14 mm of air; unaligned, it is 60 mm of air. So the utron needs only a modest μ_eff: once μ_eff is above
about 30, its reluctance (46 mm / μ_eff) is small next to the 14 mm of air. What it must not do is shield the flux with eddy
currents. μ_eff follows the classic lamination law μ·tanh(kt/2)/(kt/2) [RH: 1-D, fringing, saturation and hysteresis ignored].

| utron core | μ_eff (′ / ″) | L′ aligned / ideal | torque swing (ideal 0.767) | loss per pulse ≈ π·tan_L | B_sat |
|:--|:--|:--|:--|:--|:--|
| solid soft steel block | 0.7 / 0.7 | 0.20 | **−0.15 (repels)** | 220 % | 2.0 T |
| soft steel, hollow with the bore along z | flux excluded | – | **repels** | – | 2.0 T |
| soft steel, 3 mm fins (comb) | 11 / 11 | 0.85 | 0.73 | 41 % | 2.0 T |
| soft steel, 1 mm sheet stack | 33 / 33 | 0.95 | 0.75 | 15 % | 2.0 T |
| soft steel, 0.5 mm sheet stack | 65 / 65 | 0.98 | 0.76 | 8 % | 2.0 T |
| **electrical steel M235-35A, 0.35 mm** | 271 / 270 | 0.99 | 0.77 | **2 %** | 1.9 T |
| electrical steel 0.2 mm | 437 / 456 | 1.00 | 0.77 | 1.3 % | 1.9 T |
| SMC (Somaloy-class), machined | 400 / 60 | 0.99 | 0.77 | 0.3 % | 1.6 T |
| iron powder (μ 75) | 75 / 1.5 | 0.96 | 0.76 | 0.3 % | 1.2 T |
| MnZn ferrite (reference) | 2000 / 20 | 1.00 | 0.77 | 0.1 % | **0.45 T** |

**Hollowing out soft steel does not work.** The eddy currents run in a 0.03 mm skin on the outside whether the block is solid or
hollow, so the steel keeps the flux out either way:
- with the bore along z, the tube is a closed shorted turn around the flux, which is the worst case;
- with the bore along x or y, the top and bottom plates face the flux and screen it.

Hollow steel only saves mass. **What works with soft steel is splitting it, not hollowing it:**
- the steel must be in thin sheets or fins whose planes contain z (the flux direction);
- they must be insulated from each other, or joined along one edge only (a comb), so that no closed metal loop encircles the z-flux;
- 1 mm sheet already gives 95 % of the ideal swing, at about 15 % loss per pulse; 0.5 mm gives 8 %.
- Mass can then be removed by leaving out middle sheets, as long as the flux path along z stays continuous.

**Best next material: a stack of electrical-steel laminations (M235-35A / M270-35A, 0.35 mm, or 0.2 mm grades).**
- It is easy to source as transformer or motor lamination sheet: laser-cut 46 × 46 mm squares, varnished or bonded, about
  185 sheets for the 65 mm length.
- It gives 99 % of the ideal swing at about 2 % loss per pulse.
- It saturates at 1.9 T, versus about 0.45 T for ferrite. Torque scales as B², so it carries roughly 18× the flux-density²
  that ferrite can. Ferrite would not have been the best choice even if available.
- Stack the sheets along y (the direction of travel), so that each sheet lies in an x–z plane.
- SMC (machinable, isotropic, no stacking) is the alternative where blanks can be had. Iron powder is low-loss but saturates
  early.

**C-EM core (path ≈ 300 mm, same model).** The core needs a higher μ_eff than the utron, because its path is long.
- The register's 0.35 mm Si-steel reaches 0.96 of ideal at about 12 % loss per pulse (π·0.038). That corrects the earlier note:
  it works, but lossy.
- 0.2 mm reaches 0.98 at about 7.5 %; 0.1 mm or amorphous cut cores (Metglas AMCC) about 3 % or less.
- Solid or 1 mm-and-thicker steel is unusable for the C core.
- The 0.64 H / 40 Ω per C-EM is an engine default, not derived from this geometry, and should be recomputed from it. **[next]**

## Pump feasibility with the placed motor: field ledger (`sim/motor_field.py`, `sim/motor_field_results.json`)

**Method.** The whole machine plus the motor would need 14–16 M grid cells, and the solver's memory limit is about 11 M. So
the motor and the v4 wiring enter as two deltas on the full-machine 12-angle capacitance model of r5N2f, which is the CAD build
il2f-6563b90d with record z 1.2400. Both deltas use the coarse level, the free basis and the same 12 rotor angles.

1. **Gap model** (r 380…563, |z| ≤ 90, 3.5–3.8 M cells). The SG1 / SG2 spheres and stems are their own nets, mA / mB. Merging
   them back into 2 / 3 recovers the before-state exactly from the same solve.
2. **Motor model** (the motor and everything beyond r 450, 2.2–2.5 M cells). The motor parts are proxies [IR]:
   - C-EM core: the squared section as five (r, z) boxes, 30 mm tangential, with the coil lumped in;
   - utron: an envelope including its open coil.

   The cores' and utrons' couplings are added. The shielding they give existing pairs is neglected, which is conservative.

v4 wiring in the engine:
- SG1 is re-noded from 2 to mA. The six C-EMs per side are lumped as 0.107 H / 6.7 Ω, the engine default per coil divided by 6.
- The screened lead is 6 × 57 pF across each coil group.
- The parallel tank is the coil chain across R-A / R-B.

| step | z | Δz |
|:--|:--|:--|
| 0. r5N2f as solved (series-tank basis, old netlist) | 1.2400 | (record 1.2400) |
| 1. + v4 parallel tank | 1.3114 | +0.071 |
| 2. + v4 series C-EMs, mid node 0.5 pF only | 1.3722 | +0.061 |
| 3. + field: the SG1 / SG2 spheres + stems are the mid node | 1.3713 | −0.001 |
| 4. + screened lead, 57 pF across each coil | 1.3471 | −0.024 |
| 5. + C-EM cores (bonded to 2 / 3) | 1.3022 | −0.045 |
| 6. + floating utrons | **1.2967** | −0.006 |

**z = 1.297, converged, with everything placed: the pump stays above z ≥ 1.2.** By step:
- **Mid node.** 5.2 pF lumped, about 0.9 pF per coil–gap node: 2.5 to node 1, 1.8 to R-A (the gap's own capacitance), 0.3 to
  R-B and 0.3 to node 4. A further 4.3 pF goes to node 2, across the coil. That is well inside the 3.3 pF per-node budget. The
  sphere and stem were never the problem; the bare lead was, and the screen fixes it.
- **C-EM cores (the largest motor cost).** Each core couples about 2 pF to free space. The six on each rail also couple 5–9 pF
  to the *other* rail's input node (A cores to node 4, B cores to node 1), through the stator lead frame at r 560. Those frame
  leads have to be rerouted anyway (G-MOT-TRUNNION). Moving them away from the cores, or screening the cores toward the frame,
  wins back part of the −0.045.
- **Utrons.** They couple up to 43.9 pF to the aligned cores (about 7 pF per pair), but they float. With zero net charge they
  carry no charge unless they spark or leak, so they cost only −0.006. The jaw gaps hold: in a ±15 kV operating set the utron
  floats at +10.5 kV and the peak field is about 1 kV/mm (`docs/geometry/rt/slices/`).

**Not yet in this number:**
- the C-EM's own L and R from its geometry (0.64 H / 40 Ω is still a placeholder);
- core and utron eddy loss per pulse (`sim/utron_material.py`: about 2 % for laminated M235-35A, 12 % for a 0.35 mm C-EM core);
- the rerouted frame leads;
- mesh refinement (+0.004 on r5N2f).

## C-EM winding, inductance against angle, and torque at 300 rpm (`sim/cem_inductance.py`)

**Inductance model (3-D, classic magnetostatic ↔ electrostatic analogy).**
- The core and utron are ideal iron, so they are magnetic equipotentials:
  - the top half-core is at ψ = 1 and the bottom half at 0;
  - 12 spine plates under the winding carry the winding's linear magnetomotive force;
  - the utron floats, with zero net flux.
- With that mapping the field solver's Maxwell matrix is the permeance matrix, and L = N²·μ₀·P(θ). The 21 angles are at 1.5°
  steps. The plate-gap term (19.1 mm) is subtracted, and it does not depend on angle.
- The core's finite μ_eff enters as a series permeance (μ·A/l, A 750 mm², l ≈ 300 mm) [RH].

| | unaligned | aligned | swing |
|:--|:--|:--|:--|
| external permeance P (ideal iron) | 458.7 mm | 532.0 mm | **+16 %** |
| with a 0.1 mm Si-steel core (μ′ ≈ 1170) | 393 mm | 446 mm | +13.5 % |
| with a 0.35 mm M235-35A core (μ′ ≈ 270) | 273 mm | 297 mm | +9 % |

The swing is small because the C's flux mostly leaks around the jaws: jaw to jaw is 60 mm and the arms are 74 mm apart, about
as large as the core itself. dL/dθ peaks about 3° before alignment (firing point, [OC]) and changes sign after alignment
(`docs/geometry/motor/cem-inductance-vs-angle.png`).

**Winding (bobbin window ≈ 48 × 13 mm on a 29 × 33 mm tube, fill 0.45, mean turn 176 mm):**

| wire Ø | N | R | L at firing (0.1 mm core) | pulse (π√(L/6·213 pF)) | z |
|:--|:--|:--|:--|:--|:--|
| 0.25 mm | 4251 | 262 Ω | 9.8 H | 59 µs | 1.2966 |
| **0.40 mm** | **1846** | **44 Ω** | **1.85 H** | **25 µs** | **1.2966** |
| 0.63 mm | 796 | 8 Ω | 0.34 H | 11 µs | 1.2965 |

The pump does not care which winding is used: z is 1.2966 throughout. The suggested winding is 0.40 mm, giving ~2 H and 44 Ω.
At 20 kV the peak current is a few tens of mA per coil and the gap flux density a few mT, so the core is nowhere near saturation.

**Torque at 300 rpm (relative), eigen-state scaled to a 20 kV cycle peak:**
- **Direct (pulse only): about 2–10 µN·m.** That is 0.06–0.3 mW of mechanical power, against 3.8 W taken from the belt.
  - The reason: a 10–60 µs pulse lasts while the utron moves only 0.006–0.04 mm, against a 4.8 ms jaw transit at 300 rpm.
  - So F = ½ i²·dL/dx acts over almost no distance.
- **Ceiling (every joule stored in the coils converted): 0.22 W, about 7 mN·m.** This would need a freewheel diode across each
  coil (so the current keeps flowing through the coil, decaying with L/R ≈ 40 ms, while the utron crosses), and a perfect
  conversion. With the real swing (~13 %) about 1 mN·m is attainable.
- **Needed:** bearing drag alone on a 189 kg stator is about 0.07 N·m, about 2.2 W at 300 rpm [RH: deep-groove bearing, 50 mm
  bore, μ 0.0015, no windage or seals].

**Verdict: at 300 rpm and 20 kV the C-EMs cannot counter-rotate the stator.**
- The direct drive is about 4 orders short.
- Even the freewheel ceiling is about 10× short.
- It is a power-budget limit, not a winding choice: the pump's whole belt input at 300 rpm / 20 kV is 3.8 W.
- Torque scales with V² and with rpm, but so does the drag at speed, and the C-EM can only ever take a fraction of the transfer
  energy.

**Levers, in order of effect:**
1. **Drive the stator externally.** For example a second belt or a counter-rotating gear from the rotor drive.
2. **If the C-EMs stay: freewheel diodes across each coil, and a much larger swing.** That means jaw gaps of 1–2 mm instead
   of 7 mm and flux-concentrating pole faces. The ceiling then still sets the limit: about 0.2 W × (V / 20 kV)².
3. **Higher operating voltage.** Every 2× in V gives 4× energy, but the HV clearances grow with it.
