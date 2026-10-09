"""docs/ledger/register.py -- the drawing register of the design lock (2026-10-09): every technical drawing bundled into
docs/ledger/DCCREG-drawings-bundle.pdf, in sheet order.
Parts: "A" the design of record (locked); "B" supporting drawings of the record; "C" earlier phases, kept for the record.
Each entry: sheet, title, file (from the repository root), what it shows, generator (the script that redraws it), part.
"""

_R = [
    # part A: the design of record
    ("A", "Rotor circuits: reluctance pump and electrostatic pump (as built)", "docs/schematic-rotor-circuits.svg",
     "(a) the magnetic dual doubler driving the AH pair; (b) the de Queiroz diode doubler, the clamps and the rings' "
     "two mirrored chains; parts and operating point", "docs/make_schematic_rotor.py"),
    ("A", "The rings' DC supply, the symmetric pair", "docs/schematic-rings-supply.svg",
     "both Cockcroft-Walton chains stage by stage, each capacitor's DC and each diode's reverse peak; the hub",
     "docs/make_rings_supply_schematic.py"),
    ("A", "DCCREG-UTR-101: the wound utron's SiFe half-core", "docs/drawings/DCCREG-UTR-101.pdf",
     "manufacturing drawing of the half-core (2-D views, lamination, 3-D view)", "docs/make_core_drawing.py"),
    ("A", "DCCREG-HUB-201: rings A and B, copper, beaded", "docs/drawings/DCCREG-HUB-201.pdf",
     "manufacturing drawing of the rings on the vessel: half-section, the beads in their grooves, the gore",
     "docs/make_rings_drawing.py"),
    ("A", "The air vane stack, 6 mm", "docs/figures/air-vane-stack-6mm.png",
     "the electrostatic varicaps C1 / C2: stator and rotor vanes, gaps, full rounds, the stack along the shaft",
     "docs/make_air_vane_drawing.py"),
    ("A", "The wound utron, core detail", "docs/figures/utron-core-detail.png",
     "the utron's core and winding, dimensioned", "docs/make_utron_drawing.py"),
    ("A", "The rings' field on the null", "docs/figures/hub-rings-field.png",
     "field drawings: the section with |E|, equipotentials and field lines; axis and equator; the beads",
     "docs/make_rings_field_figure.py"),
]
REGISTER = [dict(sheet=i + 1, part=p, title=t, file=f, what=w, gen=g) for i, (p, t, f, w, g) in enumerate(_R)]
