"""docs/ledger/register.py -- the drawing register of the design lock (2026-10-09; revised at the settlement the same
day): every technical drawing bundled into docs/ledger/DCCREG-drawings-bundle.pdf, in sheet order, and the CAD files that
cannot go on a sheet.
Parts: "A" the design of record (locked); "B" supporting drawings and figures of the record (stale content flagged);
"C" earlier phases, superseded, kept for the record.
Each entry: part, title, file (from the repository root), what it shows (and what in it is stale), generator.
Analysis plots of the earlier phases (the repository root's *.png, sim/*.png) are data, not drawings: they stay with
their findings and are not bundled.
"""

_TUBE = "docs/geometry/tube/tube-r150-n8-wound-g0p5-6br"         # the model before the record (vacuum stack, placeholder hub)
_REC = "docs/geometry/tube/tube-r150-n6-air6-wound-g0p5-6br-hub50"   # the record in solids (sim/tube_geometry.py --record)
_R = [
    # ------------------------------------------------------------------------------------- A: the design of record
    ("A", "The locked machine: what drives what", "docs/ledger/figures/architecture.png",
     "the drive and the two counter-rotating bodies, both pumps, the hub and its two fields; where the belt's power "
     "goes; the reference", "docs/ledger/make_ledger_figures.py"),
    ("A", "Rotor circuits: reluctance pump and electrostatic pump", "docs/schematic-rotor-circuits.svg",
     "(a) the magnetic dual doubler driving the AH pair (the 22 mF bypass dashed, PROPOSED); (b) the de Queiroz diode "
     "doubler, the clamps and the rings' two mirrored chains; parts and operating point", "docs/make_schematic_rotor.py"),
    ("A", "The rings' DC supply, the symmetric pair", "docs/schematic-rings-supply.svg",
     "both Cockcroft-Walton chains stage by stage, each capacitor's DC and each diode's reverse peak; the hub with its "
     "AH cores at REF", "docs/make_rings_supply_schematic.py"),
    ("A", "DCCREG-UTR-101: the wound utron's SiFe half-core", "docs/drawings/DCCREG-UTR-101.pdf",
     "manufacturing drawing, Rev A draft for quotation: lamination profile 2:1, views B and C, GD&T, hole table, stack "
     "data, 3-D view", "docs/make_core_drawing.py"),
    ("A", "The wound utron against a bridge", "docs/figures/utron-core-detail.png",
     "the 200-turn coil on the split U-core, the 3.0 mm NiFe neck, the bonded slot cover and studs; front view, two "
     "sections, the 2-D flux, the data", "docs/make_utron_drawing.py"),
    ("A", "The air vane stack, 6 mm gaps, 6 + 6 vanes", "docs/figures/air-vane-stack-6mm.png",
     "the electrostatic varicaps C1 / C2: stator vane (REF), rotor vane (node 1 / 4), both at minimum C, side A's "
     "half-section, the vane cell, the rim field (panel d still draws the placeholder hub)",
     "docs/make_air_vane_drawing.py"),
    ("A", "DCCREG-HUB-201: rings A and B, copper, beaded", "docs/drawings/DCCREG-HUB-201.pdf",
     "manufacturing drawing, Rev A draft: the half-section 2:1, the polar and equatorial beads in their grooves 5:1, "
     "one gore flat 4:1, the feature table and build notes", "docs/make_rings_drawing.py"),
    ("A", "The rings' field at the null", "docs/figures/hub-rings-field.png",
     "field drawings: the section's |E|, equipotentials and field lines; the field and the pressure along the axis "
     "and across the equator; ring B's beads", "docs/make_rings_field_figure.py"),
    ("A", "The machine of record: section through the shaft", f"{_REC}-section.png",
     "the record in solids, 940 mm: the air stack of record (6 + 6 vanes, 6 mm gaps) with Ca / Cb on the rotor, the "
     "reluctance sections and the locked hub; side A below", "sim/tube_geometry.py --record"),
    ("A", "The machine of record: quarter cutaway", f"{_REC}-3d-cutaway.png",
     "the same solids in 3-D, cut away", "tools/step-viewer/shoot.py"),
    ("A", "The machine of record: half section", f"{_REC}-3d-half.png",
     "the same solids, half-sectioned", "tools/step-viewer/shoot.py"),
    ("A", "The locked hub in solids", f"{_REC}-hub.png",
     "the vessel, rings A / B with their beads, the gel, the PEEK retainer, the G10 coupler, the AH cores, formers and "
     "coils, the flanges", "sim/tube_geometry.py --record"),
    ("A", "Reluctance sections A and B, plan cuts", f"{_REC}-reluctance-plan.png",
     "the three wound utrons per side on the rotor and the six bridges per side on the counter-rotor (B offset 30°)",
     "sim/tube_geometry.py --record"),
    ("A", "Utron A1 with bridge A1, exploded", f"{_TUBE}-3d-exploded.png",
     "the parts of one wound utron and its bridge", "tools/step-viewer/shoot.py"),
    ("A", "Reluctance section A, quarter cut", f"{_TUBE}-3d-reluctance.png",
     "utrons on their G10 carrier discs inside the bridge ring", "tools/step-viewer/shoot.py"),
    ("A", "Reluctance section A, plan at mid-stack", f"{_TUBE}-3d-plan.png",
     "the 0.5 mm gaps at the aligned position", "tools/step-viewer/shoot.py"),
    # ------------------------------------------------------------------------------------ B: supporting, flagged
    ("B", "The lock-down study of the hub", "docs/figures/hub-locked.png",
     "the hub as locked (50 mm sphere, AH cores, flanges) and the lock-down's pick of rings, its 3-stage 20–53° bands "
     "superseded by DCCREG-HUB-201", "docs/make_hub_locked_figure.py"),
    ("B", "The rings as built: retainer, edges, stages", "docs/figures/hub-rings-build.png",
     "the PEEK retainer with its gel pocket and the beads to scale; the field against the DC by supply family and "
     "rating; the polar bead against the AH; the retainer's permittivity", "docs/make_hub_rings_build_figure.py"),
    ("B", "What the bench test should see", "docs/figures/hub-bench-predictions.png",
     "start-up, the 120 Hz ripple (nodes, rings, field), the 6 h drift by material, the test's phases",
     "docs/make_hub_bench_figure.py"),
    ("B", "One revolution of the rotor", "docs/figures/hub-rings-revolution.png",
     "the pump's phases, its nodes, the chains, and the field at the null: steady from B to A, no sign change",
     "docs/make_hub_revolution_figure.py"),
    ("B", "Utron size against gain: the pick", "docs/figures/utron-size-vs-gain.png",
     "6 / 12 bridges × 600 / 1200 rpm at 0.5 / 1.0 mm, with the corrected mean turn", "docs/make_variants_chart.py"),
    ("B", "The vane matrix: what the radius buys under the 6 + 6 cap", "docs/figures/vane-matrix-radius.png",
     "power, gain, stack length and aluminium against the vanes' outer radius", "docs/make_vane_matrix_figures.py"),
    ("B", "The vane matrix: rim corona margins", "docs/figures/vane-matrix-corona.png",
     "the rim's corona margin against gap and vane thickness", "docs/make_vane_matrix_figures.py"),
    ("B", "The AH's null in the locked hub", "docs/figures/ah-null.png",
     "the cusp's field, the null against the coils' imbalance and over the 120 Hz cycle with and without the bypass, "
     "the rods' flux, the shaft's permeability", "sim/ah_null.py"),
    ("B", "The reversing gear and the belt drive (PROPOSED)", "docs/figures/drive-gear-concept.svg",
     "the first cut: a bevel reverser at side A, its carrier held by the frame, three POM-C pinions; the HTD belt and "
     "the motor", "sim/drive_sizing.py --figure"),
    ("B", "The utrons in 3-D: their ends, their coupling and the pump", "docs/figures/utron-3d.png",
     "κ in 3-D against the record's 2-D section, where the flux goes, the coils' coupling round the machine, and the "
     "pump with each utron set (model check 34)", "sim/utron_3d.py"),
    ("B", "The neck in a nonlinear field solve", "docs/figures/neck-nonlinear.png",
     "Ψ(NI) of the built utron, where the iron saturates, and the pump with the field map's law (model check 31)",
     "sim/neck_nonlinear.py"),
    ("B", "Real diodes in both pumps", "docs/figures/diodes-real.png",
     "the kick's threshold by rectifier class, the electrostatic gain against the seed, and the rings with real HV "
     "sticks (model check 32)", "sim/diodes_real.py"),
    ("B", "The tube's strays by a field solve", "docs/figures/tube-strays.png",
     "the strays per node and where they come from, the varicap with its rims, and the pump as built (model check 33)",
     "sim/tube_strays.py"),
    # ---------------------------------------------------------------------------------------- C: earlier phases
    ("C", "The machine as modelled before the record: section", f"{_TUBE}-section.png",
     "superseded by the record in solids: the old vacuum 8 + 8 stack, Ca / Cb on the counter-rotor, the 120 mm "
     "placeholder hub (802 mm tube); its reluctance sections are the record's", "sim/tube_geometry.py --rel wound"),
    ("C", "The machine as modelled before the record: quarter cutaway", f"{_TUBE}-3d-cutaway.png",
     "as the section", "tools/step-viewer/shoot.py"),
    ("C", "The machine as modelled before the record: half section", f"{_TUBE}-3d-half.png",
     "as the section", "tools/step-viewer/shoot.py"),
    ("C", "Hub drive: the first two-pump schematic (2026-10-07)", "docs/schematic-hub-drive.svg",
     "superseded by the rotor circuits: 300 rpm each way, 3 × 1150-turn toothed C-EM iron, the doubler on the stator "
     "vanes driving the bicone, a brush", "docs/make_schematic_hub.py"),
    ("C", "First pole pick: pole-pair flux at 0.5 mm", "docs/figures/pole-pair-flux-g0p5.png",
     "superseded geometry (r_g 165, slot 50 × 60, stack 70, bridges 90 × 20), before the mean-turn correction",
     "docs/make_pole_drawing.py"),
    ("C", "First pole pick: pole-pair flux at 1.0 mm", "docs/figures/pole-pair-flux-g1p0.png",
     "as the 0.5 mm sheet", "docs/make_pole_drawing.py"),
    ("C", "The DC pair inside the vacuum (not chosen)", "docs/figures/core-null-field.png",
     "Rogowski electrodes on the AH null in the placeholder hub, 65.7 kV/cm; superseded by the rings outside the glass",
     "docs/make_core_null_figure.py"),
    ("C", "Rings on the placeholder vessel, AC-coupled", "docs/figures/core-rings.png",
     "the swinging-rings study through 1 nF: field, strays, gain", "docs/make_core_rings_figure.py"),
    ("C", "The floating cones' swing", "docs/figures/core-swing-waveforms.png",
     "cone electrodes on coupling capacitors swinging −4.4 / +2.7 kV at 120 Hz", "docs/make_core_swing_figure.py"),
    ("C", "Earlier tube build: section", "docs/geometry/tube/tube-r150-n8-section.png",
     "the spark-gap tube with clocking decks, C-EMs and the bicone, 1263 mm", "sim/tube_geometry.py"),
    ("C", "Earlier tube build: C-EM and utron plan", "docs/geometry/tube/tube-r150-n8-reluctance-plan.png",
     "the designer's C-EM / utron sections", "sim/tube_geometry.py"),
    ("C", "Earlier tube build: clocking plan", "docs/geometry/tube/tube-r150-n8-clocking-plan.png",
     "the spark-gap clocking deck", "sim/tube_geometry.py"),
    ("C", "Switchless C-EMs on the diode core", "docs/schematic-diode-core-switchless.svg",
     "leg against bus placement of the C-EMs", "docs/make_schematic_switchless.py"),
    ("C", "Diode core with a DC bus", "docs/schematic-diode-core-dcbus.svg",
     "marked SUPERSEDED in the file: a DC bus with a switched C-EM drive", ""),
    ("C", "C-EMs in the discharge path", "docs/schematic-cem-in-discharge-path.svg",
     "the C-EMs in series with the rail gaps SG1 / SG2", ""),
    ("C", "C-EM motor placement", "docs/schematic-cem-motor-placement.svg",
     "the C-EMs in the netlist of record; a buffer and angle-gated fire proposal", ""),
    ("C", "Disc machine: the KiCad schematic of record", "docs/kicad/DCCREG_Turbine_circuit.svg",
     "the designer's disc machine: 43 parts, 8 spark gaps (the source is the .kicad_sch beside it)",
     "designer export (KiCad)"),
    ("C", "Disc machine: Ca / Cb simplification proposal", "docs/kicad/schematic_simplification.png",
     "43 → 31 parts", "docs/kicad/render_simplification.py"),
    ("C", "Disc machine: reference cross-section", "tools/cross-section.svg",
     "the disc's reference radii and named features from the r0.15 DXF", "tools/gen_artifacts.py"),
    ("C", "Disc machine: the boomerang C-EM block cap", "docs/boomerang-cap.png", "plan and section", ""),
    ("C", "Disc machine: the placed C-EM motor", "docs/geometry/motor/motor-il2f-6563b90d-rc40.png",
     "plan and radial section of the motor on the interleaved N = 2 disc", ""),
    ("C", "Disc machine: field cut at an SG1 station", "docs/geometry/rt/slices/machine-SG1-station-before-firing.png",
     "meridional |E| before firing, v4 topology", "sim/field_slice.py"),
    ("C", "Disc machine: field cut at an SG1 station, zoom", "docs/geometry/rt/slices/machine-SG1-zoom-before-firing.png",
     "as the station cut, magnified", "sim/field_slice.py"),
    ("C", "Disc motor: field cut at ±15 kV", "docs/geometry/rt/slices/motor-A-station-pm15kV.png",
     "the motor model at rotor 15°", "sim/field_slice.py"),
    ("C", "Disc motor: field cut, unit drive", "docs/geometry/rt/slices/motor-A-station-unit-cA.png",
     "the motor model at rotor 15°, unit drive on C_A", "sim/field_slice.py"),
]
REGISTER = [dict(sheet=i + 1, part=p, title=t, file=f, what=w, gen=g) for i, (p, t, f, w, g) in enumerate(_R)]

# CAD and DXF files: not placed on sheets (open them in a CAD viewer; tools/step-viewer/ renders the STEP files)
CAD = [
    ("A", "docs/drawings/DCCREG-UTR-101_half-core_A.step", "the utron half-core stack, hand A (hand B mirrored)"),
    ("A", "docs/drawings/DCCREG-UTR-101_lamination.dxf", "the as-cut lamination profile (R12), tip face R130.20"),
    ("A", f"{_REC}.step", "the record in solids (153 solids, 940 mm)"),
    ("A", f"{_REC}.glb", "the same, for tools/step-viewer/"),
    ("A", f"{_REC}.parts.json", "its parts and layout list"),
    ("C", f"{_TUBE}.step", "the machine as modelled before the record (152 solids)"),
    ("C", f"{_TUBE}.glb", "the same, for tools/step-viewer/"),
    ("C", f"{_TUBE}.parts.json", "its parts and layout list"),
    ("C", "docs/geometry/tube/tube-r150-n8.step", "the earlier spark-gap tube build (307 solids, 1263 mm)"),
    ("C", "docs/geometry/freeze-v010-CaCb.step", "the disc's v0.10 freeze with Ca / Cb"),
    ("C", "docs/geometry/floor-56b6cb83.step", "round-trip floor build (disc)"),
    ("C", "docs/geometry/opt-c9ac780b.step", "round-trip opt build (disc)"),
    ("C", "docs/geometry/il2-ce1a9380.step", "interleaved N = 2 disc build"),
    ("C", "docs/geometry/il2f-6563b90d.step", "final interleaved N = 2 disc build"),
    ("C", "docs/geometry/il2f-6563b90d-rc40-FULL-pump+motor.step", "the disc pump with its C-EM motor"),
    ("C", "docs/geometry/motor/C-em_and_motor_coil_export.step", "the designer's C-EM and utron source (Fusion 360)"),
    ("C", "docs/varcap-nodeanalysis-template-r0.15_TMD_layout.dxf", "the designer's disc layout, r0.15"),
    ("C", "docs/varcap-nodeanalysis-template-r0_6_TMD_layout.dxf", "the designer's disc layout, r0.6"),
    ("C", "docs/kicad/DCCREG_Turbine_circuit.kicad_sch", "the designer's KiCad source of the disc schematic"),
]
