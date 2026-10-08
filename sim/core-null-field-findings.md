# The strongest steady field at the AH null — findings

**Source:**
- the electrodes: `sim/core_null_field.py` → `sim/core_null_field_results.json` (axisymmetric boundary elements);
- the supply: `sim/core_field.py`, the `dc` runs → `sim/core_field_results.json` (ngspice);
- the figure: `docs/figures/core-null-field.png` (`docs/make_core_null_figure.py`).

**Designer's brief.**
- The AH coils, top and bottom of the sphere, stay independent of the electrostatic field.
- The centre of the vacuum core, where the AH null sits, should carry the maximum electrostatic pressure or field.
- How is left open; the bicone geometry may go.
- The electrostatic and magnetic pumps are the supplies for both field generators.

**The answer.**
- **Two Rogowski electrodes inside the vacuum**, on the shaft's axis, the gap centred on the null.
- **The electrostatic pump feeds them DC:**
  - electrode A from node 1's negative peak through one diode, −13.2 kV;
  - electrode B from one Cockcroft-Walton (CW) stage on node 4's swing, +7.4 kV;
  - 20.6 kV across a 3.14 mm gap.
- **At the null:** 65.7 kV/cm and 191 Pa, uniform within 1 % out to r = 4.7 mm. The electrodes' surface sits at the
  repo's vacuum rule.
- **The magnetic pump keeps driving the AH pair as it is:** 300 A-turns steady with the 22 mF bypasses
  (`sim/ah-steady-cusp-findings.md`).
  - The electrodes are non-magnetic and sit where B is zero, so neither field generator sees the other.

## 1. Why this geometry: the electrodes' surface is the ceiling
- **Nothing beats a uniform gap.** In charge-free vacuum each component of E is harmonic, so its largest value lies on
  the boundary.
  - The field at the null therefore cannot exceed the largest field on the electrodes.
  - The best any geometry can do is a gap whose surface field equals the field at its centre.
- **The rule then sets the field.** The repo's vacuum rule allows 6.67 kV/mm on any electrode surface:
  - 10 kV/mm design field (`sim/stack_sizing.py`) over the vacuum design's 1.5 margin (`sim/air_stack_sizing.py`);
  - so the null can carry 6.67 kV/mm divided by the electrode's peak-to-centre ratio.
- **The profile decides that ratio.** At a 3.1 mm gap, 1 V across, each electrode on a 2.5 mm stem:

| electrode | surface peak / field at the null | field at the null × g / V | within 1 % to r | C across |
|:--|--:|--:|--:|--:|
| bare stem, hemispherical tip r 2.5 mm | 1.768 | 0.820 | 0.3 mm | 0.19 pF |
| sphere r 5 mm | 1.346 | 0.904 | 0.5 mm | 0.30 pF |
| sphere r 10 mm | 1.164 | 0.950 | 0.6 mm | 0.62 pF |
| flat face r 3.1 mm, full-round edge r 3.1 mm | 1.149 | 0.999 | 2.3 mm | 0.50 pF |
| flat face r 6.2 mm, full-round edge r 6.2 mm | 1.066 | 1.000 | 5.7 mm | 1.33 pF |
| Rogowski, profile started at slope e⁻³ (a 2.9° kink) | 1.064 | 1.000 | 2.6 mm | 0.59 pF |
| **Rogowski, flat r 3.1 mm, smooth join (the design)** | **1.009** | **1.000** | **4.7 mm** | **1.06 pF** |
| Rogowski, flat r 6.2 mm | 1.006 | 1.000 | 7.8 mm | 1.72 pF |

- **Sharp electrodes lose twice.** A point or a sphere puts more field on its own surface and less at the null: the bare
  tip runs its surface 1.77× above a null field that is only 0.82 V/g.
- **Why the Rogowski profile works:**
  - on the 90° Rogowski profile the field falls steadily from the uniform value;
  - the face's flat must join it smoothly: started at slope e⁻³, the 2.9° kink alone adds 6 %;
  - started at e⁻⁶ the join is smooth, and the peak sits 0.9 % above the null.
- **Outside the vessel it is 26× weaker.** The best ring of the previous study (`sim/core_rings.py`) gives
  0.124 (kV/cm) per kV: 2.6 kV/cm at the same 20.6 kV, and 0.29 Pa against 191.

## 2. The supply: the electrostatic pump's DC
- **The circuit, per side:**
  - A: diode Dk from node 1 (its anode on A), with C_A from A to the shaft;
  - B: per CW stage, Co from node 4 to m, Dc from the shaft to m, Dp from m to B, and Cs from B to the shaft;
  - all storage 100 pF; the clamp at 13.1 kV; 1200 rpm relative.

| option | A | B | across | gap at the rule | field at the null | pressure | z at start | ripple A / B, p-p | time to 95 % | parts beyond the pump |
|:--|--:|--:|--:|--:|--:|--:|--:|--:|--:|:--|
| dc0 | −13.2 kV | 0 (shaft) | 13.2 kV | 2.04 mm | 64.5 kV/cm | 184 Pa | 1.237 | 103 V / — | 0.10 s | Dk, C_A |
| **dc1** | **−13.2 kV** | **+7.4 kV** | **20.6 kV** | **3.14 mm** | **65.7 kV/cm** | **191 Pa** | **1.184** | **103 / 45 V** | **0.13 s** | **+ Dc, Dp, Co, Cs** |
| dc2 | −13.2 kV | +14.1 kV | 27.3 kV | 4.14 mm | 66.1 kV/cm | 193 Pa | 1.179 | 103 / 265 V | 0.22 s | + 4 diodes, 4 capacitors |
| dc3 | −13.2 kV | +19.0 kV | 32.2 kV | 4.90 mm | 65.8 kV/cm | 191 Pa | 1.178 | 103 / 703 V | 0.34 s | + 6 diodes, 6 capacitors |
| swing (float), for reference | ±3.5 kV | ∓3.5 kV | ±7.1 kV | 1.06 mm | ±66.3 kV/cm | 0–195 Pa | 1.231 | AC, 120 Hz | | 2 × 1 nF |

- **Every option reaches the same field.** Each is held to the same surface field. More stages buy room at the null,
  not field:
  - the gap grows 2.0 → 4.9 mm;
  - the radius within 1 % grows 3.1 → 7.3 mm.
- **The default is dc1.** It gives one and a half times dc0's gap for two diodes and two capacitors.
- **DC beats the swing for pressure.** The swing's pressure pulses between 0 and its peak at 240 Hz and averages half
  of it; DC holds the peak.
- **The pump barely notices in steady state:**
  - belt 2.14 W, clamps 2.12 W;
  - the electrodes take only their leakage, 23 mW at the 10 GΩ placeholder;
  - every diode sees at most 7.5 kV reverse, apart from D3 / D4 at 13.2 kV.
- **100 pF storage, not 1 nF:**
  - the storage loads the pump while it grows: with 1 nF, z falls to 1.088 / 1.035 / 1.025 (dc0 / dc1 / dc2);
  - with 100 pF it is 1.237 / 1.184 / 1.179 (the bare pump 1.310);
  - the price is 0.5 % ripple at the placeholder leakage.
- **Beyond two stages the CW sags.** At 100 pF each stage adds less: +7.4, +6.7, +4.9 kV. The field doesn't need more
  stages; a wider gap would.

## 3. The electrodes (dc1)
- **The shape [RH]:**
  - flat face r 3.14 mm (= g);
  - the Rogowski profile from slope e⁻⁶ to e¹ (7.0 mm wide, 2.7 mm rise);
  - a closing arc r 1.57 mm (g / 2);
  - each electrode 20.4 mm across and 4.8 mm thick, its face 1.57 mm from the null.
- **The field:**
  - 65.7 kV/cm at the null;
  - the surface peaks 1.5 % above that, on the profile at r ≈ 7 mm;
  - 0.9 % of the 1.5 % is the shape; the rest is the common mode (A −13.2, B +7.4 kV against the shaft).
- **Capacitance:** 1.07 pF across, 1.23 pF from each to REF. Behind the diodes, so none of it sits on the pump's swing.
- **Material [RH]:** non-magnetic and resistive, so neither the AH field nor its 6 % ripple sees the electrodes:
  - titanium or molybdenum, polished and conditioned;
  - not ferritic or cold-worked stainless;
  - no Kovar in the feedthroughs, since it is magnetic: tungsten-in-borosilicate or molybdenum-in-aluminosilicate seals.
- **Field emission [IR]:** at 6.6 kV/mm on polished electrodes, well below the tens of kV/mm where emission usually starts.

## 4. What changes in the hub
- **The vessel gets two HV feedthroughs.** In the model the stems leave along the axis through the poles.
  - The stems' field at the inner wall (vacuum side), on 2.5 mm stems: A 2.05 kV/mm, B 1.21 kV/mm.
  - These are triple junctions (metal, glass, vacuum). They need a recessed seal under a grading shield; not modelled.
- **If the AH sits on axial rods, the stems come in from the side.** The electromagnet register
  (`presets/electromagnets-RA.json`) and the cost sheet's BOM wind the AH coils on MnZn rods on the axis, |z| 30.7–72 mm,
  just outside a 52 mm vessel's poles.
  - The stems then cannot leave along the axis. They enter from the side and turn onto the axis behind each electrode.
  - **Checked:** that hub (each AH winding on its rod as a REF cylinder, r 13 mm) with stemless electrodes. The field at
    the null is unchanged, and the surface peak moves 0.1 % (1.0162 against 1.0150).
  - The side entry itself is 3-D and not modelled.
- **Outside the vessel** the leads run in the hub's insulation, not in vacuum. A at −13.2 kV needs its clearance to the
  AH and the shaft there.
- **The cones** carry no field any more; they stay non-metallic shaft couplers.
- **The null must stay inside the uniform region**, which is 3.1 mm tall and 4.7 mm in radius.
  - Anything that unbalances the AH pair moves the null along the axis. The register measured +14.5 mm with the cone
    coils in its chain.
  - The steady cusp's bypasses leave 17 A-turns between the coils.
  - Check the null's position for the final AH layout.

## 5. Raising it further: the rule is the lever
- **The field at the null scales with the surface field the electrodes are rated for**, and the pressure with its square.
  - At the rule's 6.67 kV/mm: about 197 Pa.
  - At 10 kV/mm (the rule without its margin): about 443 Pa.
- **Small conditioned gaps hold much more.** The repo's law for the vacuum spark gap is 60 kV × g^0.6
  (`sim/design_synth.py`, [IR]).
  - With the same 1.5 margin it would let 20.6 kV sit across 0.33 mm: 62 kV/mm and about 17 kPa.
  - That law describes a spark gap's breakdown, not a gap held for hours. It is an upper bound to test against, not a
    design value.

## Caveats
- **[RH]:**
  - the vacuum rule, made for large-area vanes, applied to small electrodes (conservative);
  - the 10 GΩ leakage and the 100 pF storage;
  - the hub's dimensions (the tube placeholder; the register's hub checked);
  - the coils' REF potential and their position;
  - the electrode material.
- **[OC]:** the boundary elements. Self-tests on an isolated and a concentric sphere hold to 1e-4. The design's surface
  peak moves 0.06 % with the panels halved.
- **Not modelled:**
  - the dielectrics (glass, composite) and the feedthroughs' triple junctions;
  - the leads outside the vessel;
  - the 3-D side entry;
  - the electrodes' mounting;
  - conditioning;
  - the kick and the start with the real strays.

## Open questions for the designer
1. **How much free gap do you need at the null?** The field is the rule's whatever the supply; the gap picks the supply:
   - up to 2.0 mm: dc0;
   - up to 3.1 mm: dc1;
   - up to 4.1 mm: dc2;
   - up to 4.9 mm: dc3;
   - a wider gap lowers the field as V / g (dc1 at 10 mm: 20.6 kV/cm).
2. **Which AH layout is current?** Coils on axial MnZn rods at the poles (the register, the BOM), or loops around the
   vessel (the tube placeholder)? It decides how the stems leave the vessel.
3. **Keep the repo's 6.67 kV/mm for these electrodes, or rate them after a test?** The field at the null follows that
   number one for one.
