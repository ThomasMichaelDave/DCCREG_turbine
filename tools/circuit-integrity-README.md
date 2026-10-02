# Circuit integrity: the 3-D build against the netlist of record

`sim/circuit_integrity.py` (with a 1:1 JS mirror, `tools/circuit-integrity.js`) checks a 3-D build of the DCCREG machine against `topology_edge_list.csv`. It rebuilds the circuit **from the solids alone**:

| it finds | from | as |
|---|---|---|
| galvanic nets | copper solids that touch (≤ 0.01 mm) | one net per touching group |
| capacitors | foils of two nets facing each other | parallel-plate C through the insulators between them; rotor/stator pairs swept over a full turn |
| spark gaps | a stator sphere and a rotor sphere meeting across a band | the gap's node pair, spacing and sphere sizes |

Then it requires every **name and CAD group** to state the node its copper is actually on.

It does not use the generator's own bookkeeping, so it also checks the generator.

## Run it

```bash
python3 sim/circuit_integrity.py docs/geometry/freeze-v010-CaCb.json     # the exported JSON (bill of solids)
python3 sim/circuit_integrity.py docs/geometry/freeze-v010-CaCb.step     # or the STEP (needs OCP: pip install cadquery-ocp)
python3 sim/circuit_integrity.py model.step --json report.json           # also write the report
```

- **Exit code:** 0 means PASS, 1 means a FAIL.
- **STEP input:** the STEP route re-reads every solid's name and recognizes its shape from its faces: annular sector slab, sphere or cylinder. It accepts the FreeCAD form `node-2 / SG1_sph_6 - …` and the Fusion 360 form, where `/` becomes `-`.
- **Older STEPs:** a STEP from before the node groups also reads. Its nodes, materials and bodies are taken from the old labels.
- **On the page:** stage 2 of `tools/pump-synth.html` runs the same check live, in the "circuit integrity" panel, on every geometry change.

## The rules

| rule | FAIL when | why it matters here |
|---|---|---|
| I1 net purity | one net touches two nodes (SHORT; the bridging parts are named) | a lead or bus crossing another node's copper |
| I2 node continuity | a node is split into several nets (OPEN; its fragments are named) | sectors not bussed, a lead that stops short |
| I3 nodes of record | a drawn node is not in the netlist; old aliases (5 / 6) are named | the geometry must speak the netlist's language |
| I4 rotating joint | a net has copper on the rotor and on the stator | rotor and stator counter-rotate: such a wire would be torn off; they meet only across spark gaps |
| I5 orphans | a net holds no foil electrode | a stray lead, stem or sphere |
| I6 capacitors | a drawn netlist capacitor is missing, or fixed where it must rotate (C1, C2, Cx3, Cx4) or the reverse | the varicaps must be rotor-against-stator |
| I6 strays (WARN) | two nets' foils face each other with no netlist capacitor between them | parasitic capacitance, with its value and the component it shunts |
| I7 spark gaps | a netlist gap has no sphere pair on its nodes; a sphere pair meets on nodes the netlist does not join (PARASITIC GAP); a gap's name does not match its nodes | |
| I8 names | a label, a group or a gap / capacitor name says a different node than the copper; an insulator is labelled with a node; a name is reused | what you see in CAD must be the circuit |
| I9 off-model (INFO) | — | the netlist parts not drawn (inductors, the motor banks), and which drawn nets they join |

**Physics [OC].**
- Capacitances are parallel plate with no fringing, through the insulators in between: series layers, air elsewhere.
- Rotor/stator pairs, and fixed pairs with rotating copper between them, are swept over a full turn in 1° steps.
- A pair is coupled only if at most one partly shielding copper layer lies between the foils. Beyond that the field ends on the copper in between.
- Insulator permittivities come from material names: mica 5.4, garolite / G10 4.7.

## Gate

Gate **G-CI** (in `sim/pump_geometry_gates.py`):
- **Reference build:** the reference build passes, with one net per netlist node, all 7 drawn capacitors and all 8 gaps realized on their nodes.
- **STEP re-read:** re-reading the reference STEP gives the same nets, capacitors, gaps and strays.
- **JS parity:** the JS mirror reports exactly what the Python does, on the reference build and 8 random designs.
- **Seeded faults:** each of these is caught by the rule meant for it:
  - a sphere grouped under the wrong node (I8);
  - a lead shorting two nodes (I1);
  - a C_R plate sector losing its bus riser (I2);
  - a rotor tip on the wrong node (I1, I7);
  - the C_R plate tied to R-A (I2, I6, I8);
  - stator copper touching a rotor foil (I4).

Both modules self-test on load.
