# The field's rings on the vessel: design documentation (DCCREG-HUB-201)

**What this is:** the design of record for the two rings that hold the DC field on the AH null. It covers the
geometry, the materials, the supply, the fields they make, how they behave in time, and how to build them.

**The decision** (the designer, 2026-10-09): "Do I want to symmetric situation? If it "pumps" against the core centre,
yes!"
- Each ring sits on its own Cockcroft-Walton chain from the shaft:
  - ring A on the pump's node 1, negative;
  - ring B on node 4, positive (the mirror image);
  - two stages a side.
- This replaces the asymmetric supply: ring A on node 1's peak through Dk, the stages all on ring B
  (`sim/hub-rings-build-findings.md` §4).

**The documents:**

| what | file |
|:--|:--|
| the supply over one revolution: the pump's phases, the chains, the rings, the field | `docs/figures/hub-rings-revolution.png` |
| the manufacturing drawing (section, beads, gore) | `docs/drawings/DCCREG-HUB-201.pdf` / `.png` |
| the supply in full, every stage | `docs/schematic-rings-supply.svg` / `.png` |
| the rotor's circuits, the supply in context (panel b) | `docs/schematic-rotor-circuits.svg` / `.png` |
| the field drawings: section, axis, equator, pressure, beads | `docs/figures/hub-rings-field.png` |
| the stage study and the retainer | `docs/figures/hub-rings-build.png` |
| what the bench should see | `docs/figures/hub-bench-predictions.png`, `docs/bench-test-rings.md` |
| the findings behind it | `sim/hub-rings-build-findings.md` |
| the spec | `presets/hub-locked.json` (rings, ratings, rings_leakage, retainer, interface_filler, shaft_coupler) |
| the numbers | `sim/hub_rings_build_results.json` (record, record_supply), `sim/hub_drift_results.json` |
| the cost | `docs/cost/README.md` (core field 4, ring A's feed 2) |

Tags (`CONVENTIONS.md` §1): [OC] standard, derivable physics; [IR] a modelling or engineering choice, including the
datasheet-class values taken; [RH] a heuristic or placeholder, not load-bearing until qualified.

## 1. At a glance

| | |
|:--|:--|
| rings | two copper foil bands on the vessel's outer surface, one per hemisphere, mirror images in the equator |
| bands | 26.25° to 55.71° from the axis, on the 50 mm sphere; 12.85 mm along the glass, 13.1 cm² each |
| gap between the rings | 29.9 mm along the glass, across the equator |
| beads | Cu wire rings soldered along the edges: Ø3 mm polar, Ø2 mm equatorial |
| insulation | 0.5 mm of silicone gel over the glass, in a pocket of an unfilled PEEK retainer; G10 coupler outside |
| supply | symmetric: ring A −15.0 kV, ring B +15.0 kV, 2 + 2 Cockcroft-Walton stages from the shaft; 29.9 kV across |
| at the null | **7.62 kV/cm, 2.57 Pa, DC from B to A** as connected, with the beads (the bands alone 7.10); the null at the shaft's potential (0 V) |
| ripple | 0.014 kV/cm p-p at 120 Hz (0.19 %): no swing |
| drift | 7.62 at switch-on → 8.20 kV/cm settled (+7.6 %, half-way at 7.6 min), PEEK and gel at 25 °C [IR] |
| limits used | 1 kV/mm along the glass between the rings; 5 kV/mm in the gel at a bead [RH] |

## 2. Geometry and dimensions (drawing DCCREG-HUB-201)
- **The vessel:** a borosilicate sphere, OD 50 mm, wall 1.5 mm (ε 4.6), as supplied.
- **The bands:** spherical zones on the outer surface, from θ = 26.25° (the polar edge) to 55.71° (the equatorial
  edge), θ measured from the shaft's axis.
  - Ring B is on the upper hemisphere (z > 0) and ring A is its mirror image.
  - Each band is 12.85 mm along the glass, 13.1 cm².
  - Between the equatorial edges there are 29.9 mm along the glass, which holds the 29.9 kV at 1.00 kV/mm.
- **The beads** (per ring; z is ± for B / A):

| feature | polar edge | equatorial edge |
|:--|:--|:--|
| edge angle from the axis | 26.25° | 55.71° |
| bead: Cu wire | Ø3 mm | Ø2 mm |
| bead's contact on the glass | r 11.06, z ±22.42 | r 20.65, z ±14.08 |
| bead's centre | r 11.72, z ±23.77 | r 21.48, z ±14.65 |
| ring centre-line diameter | Ø23.44 | Ø42.96 |
| length per ring, the centre line (polar seamless, proposed) | 73.6 mm | 135.0 mm |
| groove in the PEEK (depth over the glass), as drawn | 3.5 mm | 2.5 mm |
| the groove proposed: full-round top, 1.0 mm of gel (width × depth) | 5 × 4 mm | 4 × 3 mm |
| peak field in the gel, as drawn (the build's box, gel throughout) | 4.98 kV/mm (4.85) | 4.46 kV/mm (4.36) |
| peak field in the glass, as drawn | 1.46 kV/mm | 3.01 kV/mm |
| settled at 25 °C: gel / glass | 0.69 / 0.20 kV/mm | 1.88 / 1.19 kV/mm |

- **The gores:** each band is cut flat as 12 gores (24 in all), each with a 1 mm overlap on its neighbour.
  - Each gore is 12.85 mm long along its centre line (the meridian).
  - Its width is 2π · 25 · sin θ / 12 along the arc: 5.79 mm at the polar end, 10.81 mm at the equatorial end.
  - **The laps** (first cut, PROPOSED; `sim/hub-joints-findings.md` §2): each upper gore's free edge is a 0.1 mm step
    on the band's outer face. As cut (r 5–10 µm) it lifts the gel's 1.20 kV/mm at switch-on to 3.5–4.4 kV/mm; under a
    solder fillet 0.2 mm wide, to 1.9. So deburr every cut edge and fillet each lap's free edge with the solder, then
    burnish the lap into the gel film, its ramp within 0.5 mm. Gel-filled, the crevice under a lap holds (2.3 kV/mm
    beside the beads in service); a void there holds in service (0.66 of Paschen) but not with the glass at 40 °C.
- **The bead rings' closing joints** (first cut, PROPOSED; §3 there): a joint left proud raises the bead's field by
  about 1 + 3.7 δ / w. The equatorial rings (12 % margin) take a joint dressed to the wire's round within 0.03 mm over
  1 mm. The polar rings (0.3–0.4 % margin) take none, so they are best seamless: turned from Cu-ETP bar, or brazed and
  turned to the round. With the AH ends rounded to 1.5 mm their margin is 2.3–2.4 % (a joint within 0.006 mm over
  1 mm). No solder ball on any bead: it triples the field [OC].
- **The retainer:** unfilled PEEK, to r 30 mm and |z| 72 mm. It holds the vessel, the rings and the AH cores and coils.
  - **The pocket:** 0.5 mm over the glass, gel-filled.
  - **The grooves:** as in the bead table. Proposed: their tops full-round, a ball-end cut concentric with the bead,
    with 1.0 mm of gel over it. Once the DC has settled the PEEK takes it, and the drawn grooves' square top corners
    then hold 7 kV/mm in the PEEK; the full-round tops hold 4.1 (`sim/hub-beads-settled-findings.md` §5) [IR].
  - **The AH seats:** each AH core's end is at |z| 30.7 mm. The polar bead's top is at |z| 25.3 mm, so 5.4 mm of
    PEEK lies between them. The seat stays 5.7 mm long.
  - **The AH ends:** proposed, each end's outer corner rounded to 1.5 mm or more at REF: the G10 former's end flange
    turned and coated conductive, tied to the core, or a REF end ring over the last turns. Settled, the PEEK there
    then holds 4.5 kV/mm, against 7.9 at a square corner [IR].
- **The coupler:** G10, r 30 to 33 mm, outside the PEEK, not against the glass or the rings. A first cut [IR,
  PROPOSED]:
  - a straight tube, Ø60 / Ø66 mm, over |z| ≤ 80 mm: it holds the PEEK retainer (Ø60 × 144 mm) and both shaft
    flanges, turned to Ø60 from the register's Ø64, each bonded and pinned radially (3 × Ø4 mm);
  - the hub's torque and bending pass through it. The torque is about 0.5 N·m (`docs/drive-gear-belt.md`). The axis is
    vertical, so the bending is small in service; laid horizontal, the rotor's weight over its span bends the hub by
    about 40 N·m at most: 4 MPa in the G10, about 3 MPa in the bonds [OC estimate];
  - outside it, the air sees at most 0.55 kV/mm at switch-on, about a sixth of its strength; the coupler's surface
    reaches 6.2 kV (`sim/hub-beads-settled-findings.md` §6).
- **The leads** [IR, PROPOSED]: each leaves its equatorial bead along the bead's outward normal, in a Ø3 mm channel
  through the PEEK and the coupler, filled with the gel. It then runs axially over the coupler to its own end and on to
  its chain on its own shaft half. PTFE-insulated HV wire rated above 30 kV DC, potted where it leaves the coupler: it
  passes the flange (REF) with the ring's 15 kV across its insulation.
- **The temperatures** (`sim/hub-thermal-findings.md`): with the AH coils' 1.2 W each, in a 25 °C room, the coils run
  at 43 °C and the glass at 32–37 °C, 32.5 °C between the rings.

## 3. Materials

| part | material | key values | tag |
|:--|:--|:--|:--|
| bands | Cu-ETP (CW004A) foil, annealed, 0.10 mm | soft enough to burnish onto the sphere | [RH] the thickness |
| beads | Cu-ETP wire, Ø3 / Ø2 mm | butt-soldered rings, filed round | |
| vessel | borosilicate, as supplied | ε 4.6; 1e13 Ω·m [IR] | |
| interface filler | two-part silicone gel, degassed, vacuum-cast | ε 2.9; 5 kV/mm design at a bead | [RH] the rating |
| retainer | unfilled PEEK (e.g. Victrex 450G, Ketron 1000), annealed stock | ε 3.2; about 1e14 Ω·m; 0.1 % water | [IR] |
| coupler | G10, outside the PEEK | ε 4.7 | [IR] |
| leads | PTFE-insulated HV wire, potted where they exit | rated above 30 kV DC | |

- **Not against the glass:** filled grades (carbon conducts; glass fill gives a tracking path), and G10, whose fibres
  would run along the interface (`sim/hub-rings-build-findings.md` §1).
- **The alternative retainer:** PEI (Ultem 1000), ε 3.15. It drifts more, +16 % against PEEK's +10 % (§6).

## 4. The supply: two mirrored chains on the shaft (`docs/schematic-rings-supply`)
- **How it pumps against the core centre:** both chains stand on the shaft (REF, 0 V).
  - Ring B's chain collects node 4's swing upward, a stage at a time.
  - Ring A's chain is the same ladder with every diode reversed: it collects node 1's swing downward.
  - Nodes 1 and 4 are the same waveform half a cycle apart, so each chain carries the same 7.5 kV per stage.
  - The hub is mirror-symmetric and ring A is ring B's negative, so the null sits at the shaft's potential with
    nothing connected to it [OC].
  - Each ring stands 15 kV off the AH cores (at REF), which is as far as its polar bead allows.
- **The circuit** (`sim/core_field.py` dc, `n_cw = n_cw_a = 2`, `a_ref = "shaft"`):
  - **ring B:** node 4 → Co1 → m1 → Co2 → m2;
    - Dc1 from the shaft to m1, Dp1 from m1 to b1, Dc2 from b1 to m2, Dp2 from m2 to ring B;
    - Cs1 from the shaft to b1, Cs2 from b1 to ring B.
  - **ring A:** the mirror: node 1 → Coa1 → n1 → Coa2 → n2;
    - Dca1 from n1 to the shaft, Dpa1 from a1 to n1, Dca2 from n2 to a1, Dpa2 from ring A to n2;
    - Csa1 from the shaft to a1, Csa2 from a1 to ring A.
  - **No Dk and no C_A.**
- **The parts** (the record's run at 100 GΩ per ring, `record_supply`):

| part | count | rating | in service | note |
|:--|--:|:--|:--|:--|
| Dc1, Dc2, Dp1, Dp2, Dca1, Dca2, Dpa1, Dpa2 | 8 | HV stacks, one 20 kV stick each | 7.5 kV reverse peak | 2.7× margin; choose by leakage at 7.5 kV |
| Co1 | 1 | 100 pF / 30 kV | 13.2 kV DC | node 4 sits at −8.6 kV mean |
| Coa1 | 1 | 100 pF / 30 kV | 5.7 kV DC | node 1 sits at −8.6 kV mean |
| Co2, Cs1, Cs2, Coa2, Csa1, Csa2 | 6 | 100 pF / 30 kV | 7.5 kV DC each | |
| leads to the rings | 2 | PTFE HV wire | ±15.0 kV DC | through the coupler, potted |

- **The levels:** b1 +7.49 kV and ring B +14.96 kV; a1 −7.49 kV and ring A −14.96 kV.
- **The pump stays as it is:**
  - D1 / D2 at 6.1 kV reverse and D3 / D4 at 13.2 kV;
  - the clamps Z1 / Z4 at 1.07 W each;
  - the belt at 2.14 W, the leakage at 4.5 mW;
  - the start-up gain at z 1.191, against 1.180 on the asymmetric supply.
- **Why 100 pF:** it keeps the start-up gain (z 1.18 against 1.03 at 1 nF). It still smooths the ripple to tens of
  volts.
- **The strays:** each ring has 5.1 pF to REF and 1.1 pF to the other ring. They sit behind diodes, off the pump's
  swing.

## 5. The fields (`docs/figures/hub-rings-field.png`)
- **At the null:** 7.62 kV/cm as connected, from ring B to ring A (−z), with a pressure ε0E²/2 of 2.57 Pa. The field
  per kV across is k = 0.2546 (kV/cm)/kV.
  - **The beads add 7 %:** the bands alone give 7.10 kV/cm (k 0.2373), on which the edges were sized. The beads are at
    the ring's potential and reach past its edges toward the gap (`sim/hub-beads-settled-findings.md` §2). At half the
    cell it is 7.65.
- **Around the null:**
  - within ±5 mm it varies 4.4 % along the axis and 2.0 % across the equatorial plane;
  - across the equator it rises to 8.5 kV/cm at r 16 mm;
  - along the axis it falls to zero at |z| ≈ 18 mm and then turns toward the AH cores near the poles. Each band sits
    between the null and an AH core, both at 0 V, so the potential on the axis peaks between them.
  - On both lines the field is axial (by symmetry), so these are the whole field and the whole pressure.
- **In the insulation:**
  - **along the glass** between the rings: 1.00 kV/mm, the interface rating [RH];
  - **in the gel at the beads,** as drawn: 4.98 kV/mm (polar) and 4.46 kV/mm (equatorial), against 5 kV/mm [RH]. The
    polar peak is on the bead's top, toward the AH coil's end. The build's own box, filled with gel, gave 4.85 / 4.36;
  - **in the glass under the beads:** 1.46 / 3.01 kV/mm;
  - **each ring to the AH cores:** 1.81 kV/mm on average, through the PEEK.
- **The equatorial plane is at 0 V** with the symmetric supply. No voltage runs along it, so a joint in it carries
  only the normal field (§7) [OC].
- **Once the DC has settled** (`sim/hub-beads-settled-findings.md`): conduction shares the DC by the conductivities.
  - The beads relax: 0.69 / 1.88 kV/mm in the gel at 25 °C. The PEEK, ten times less conductive than the gel, takes
    the DC: 2.3 kV/mm across the AH seat on average.
  - **The equatorial beads set a condition:** their gel stays within 5 kV/mm while the glass conducts at most 4.1 times
    the gel (4.4 with the full-round grooves). In service the ratio is about 2.4 (`sim/hub-thermal-findings.md`).
  - **The contact wedge** where each bead touches the glass stays finite, and with the gel in place its voltage is
    at most half of air's Paschen breakdown for a void of its gap. A void there is another matter: once settled a
    sealed void reaching 0.5 mm from an equatorial contact breaks down (0.99 in service), so the gel fills those wedges
    void-free (`sim/hub-joints-findings.md` §4).
- **The solves** [IR]: the hub's finite volumes with 0.25 mm cells; the beads by local solves with 0.025 mm cells,
  bounded by the hub's solution. The convergence is in `sim/hub_rings_build_results.json` convergence; the beads as
  drawn in `sim/hub_beads_settled_results.json`.

## 6. In time: start-up, ripple, drift (`sim/hub_drift.py`)
- **The start-up** from the pump's seed: 50 % at 0.12 s, 95 % at 0.24 s (29 cycles), 99 % at 0.33 s.
- **The ripple at 120 Hz:** ring A 34 V p-p, ring B 29 V p-p.
  - Ring A tops up as node 1 bottoms (at 0.375 of the cycle). Ring B tops up as node 4 peaks, 0.124 of a cycle
    (1.03 ms) later.
  - The two ripples mostly add: 57 V p-p across the gap, 0.014 kV/cm p-p at the null (0.19 %).
- **"The field from A to B swings now ... correct?" No.** The field at the null is DC, steady from B to A at
  7.62 kV/cm, and the pressure holds its maximum, 2.57 Pa, all the time.
  - **Over one revolution of the rotor** (`sim/hub_revolution.py`, `docs/figures/hub-rings-revolution.png`): the pump
    goes through its phases twelve times. Nodes 1 and 4 and the chains' oscillating nodes swing by 7.5 kV each.
    The rings hold to within 29–34 V, and the field stays at 7.611 … 7.625 kV/cm from B to A, with no sign change.
  - **Why:** each chain's diodes pass charge one way only, ring B's up and ring A's down, and the storage capacitors
    hold the rings between cycles.
  - **A field that swings from A to B** would need AC on the rings: rings on coupling capacitors, following nodes 1 and
    4, as the floating cones did (`sim/core-field-findings.md`).
  - On these bands that gives about ±1.8 kV/cm at 120 Hz, with the pressure peaking at about 0.14 Pa twice a cycle and
    zero between. The pump would also lose gain [IR estimate; not simulated with the rings].
- **The drift** with the rings held at their DC: the leakage moves the potential along the glass and through the gel
  and PEEK, from the electrostatic toward the conduction-settled state [OC].
  - PEEK and gel at 25 °C: 7.62 → 7.95 (10 min) → 8.18 (1 h) → 8.20 kV/cm (6 h), half-way at 7.6 min.
  - The other cases bracket it: PEI +10.5 %, G10 +2.0 %, the glass at 40 °C +8.5 % in about a third of the time. The
    conductivities are datasheet-class [IR].
- **The leakage:** the ledger gives 158 GΩ per ring and the design uses 100 GΩ (estimate). The chains' diodes and
  capacitors dominate; the rings' own insulation is about 200 TΩ.

## 7. Building it
- **1. The glass:** clean and degrease the vessel; mark the edge circles (Ø23.44 / Ø42.96 bead centre-lines, the
  contact circles at z ±22.42 / ±14.08) from the poles.
- **2. The foil:**
  - cut 24 gores (12 per band) to view D, and deburr every cut edge;
  - burnish them onto the glass from the polar edge, each overlapping its neighbour by 1 mm, into a film of the gel;
  - solder each lap with a fillet 0.2 mm wide or more along its free edge, and burnish the lap down, its ramp within
    0.5 mm (§2).
  - No adhesive film under the foil: the gel bonds and fills it, and no void may stay under a lap.
- **3. The beads:**
  - the two polar rings (Ø3 mm section, Ø23.44 mm centre line) seamless: turned from Cu-ETP bar, or brazed and turned
    to the round (§2, proposed);
  - cut Ø2 mm wire to 135.0 mm for the two equatorial rings; close each by a butt joint and dress it to the wire's
    round within 0.03 mm over 1 mm;
  - solder each along its foil edge, centred on the edge angle, touching the glass; no solder on the bare-glass side of
    the contact.
  - Smooth every joint: no point, burr or solder ball may stand above the bead's radius.
- **4. The leads:** solder a PTFE-insulated HV wire to each equatorial bead, and route it out along the bead's normal
  through the PEEK and the coupler, then over the coupler to its own end (§2, proposed).
- **5. Check:** continuity bead to bead around each ring; insulation ring to ring and ring to the AH dummies.
- **6. The retainer:**
  - machine the PEEK from annealed stock: the pocket 0.5 mm over the glass, the grooves 3.5 / 2.5 mm deep (proposed:
    full-round tops with 1.0 mm of gel, 4 / 3 mm deep, §2), the AH seats;
  - **split it at the equatorial plane** (proposed) [IR]. With the symmetric supply that plane is at 0 V [OC], so the joint
    sees no voltage along it, only the normal field. A split through the axis would put the full 1 kV/mm along its
    joint.
  - Fill the joint void-free with the gel.
- **7. Cast:** assemble the vessel, the rings and the retainer, then vacuum-cast the degassed gel into the pocket, the
  grooves and the joint, void-free, above all in the equatorial beads' contact wedges (§5). Inspect those through the
  glass from inside, by borescope through the pumping tube [RH]. Cure the gel per its datasheet, then fit the G10
  coupler.
- **8. Test:** the hold-off of `docs/bench-test-rings.md` phase 1 (c):
  - hold −15.0 / +15.0 kV for 1 h, then 1.25× (±18.7 kV) for 1 h;
  - partial discharge must stay below 10 pC.
  - Then phases 2–4: the leakage, the drift on lab supplies, and the rings on the pump's supply.
- **Safety:** the eight capacitors hold about 27 mJ in service. Ground them through 10 MΩ before touching.

## 8. Open
- **The ratings** (1 kV/mm along the glass, 5 kV/mm in the gel at a bead) are [RH]. The bench's phase 1 qualifies
  them, and with them the stages:

| ratings (interface / gel) | stages a side | across | at the null (the bands alone) |
|:--|--:|--:|--:|
| **1 / 5 kV/mm (the record)** | **2** | **29.9 kV** | **7.10 kV/cm (7.62 with the beads)** |
| 1 / 8 | 3 | 44.3 kV | 7.80 kV/cm |
| 2 / 5 | 2 (wider bands) | 29.9 kV | 8.35 kV/cm |
| 2 / 8 | 4 | 57.9 kV | 13.38 kV/cm |

- **Each ring's leakage** (100 GΩ estimate): the bench's phase 2.
- **The conductivities at temperature** (the bench's phase 3 with its 40 °C repeat): settled, the equatorial beads hold
  their rating while the glass conducts at most about 4 times the gel (`sim/hub-beads-settled-findings.md` §7). In a
  25 °C room the hub runs at about 2.4 (`sim/hub-thermal-findings.md`); that holds up to a room of about 30 °C if the
  gel's conductivity does not rise with temperature.
- **Proposed here, the designer's to accept** (§2):
  - the grooves' full-round tops with 1.0 mm of gel;
  - the AH ends rounded to 1.5 mm or more at REF, with the seat kept at 5.7 mm;
  - the coupler as a straight G10 tube over the retainer and both flanges, the flanges turned to Ø60;
  - the leads' path;
  - the retainer split at the equatorial plane (§7).
- **The fired-on coating's edges** for the later build: beaded the same way, or graded by a resistive layer toward the
  pole.

**Settled since the design** (2026-10-09):
- **The beads in the settled DC state and the contact wedge:** `sim/hub-beads-settled-findings.md`. The polar beads
  ease; the equatorial beads set the condition on the conductivities above; the wedge holds.
- **The field at the null with the beads:** 7.62 kV/cm at switch-on, 8.20 settled (§5, §6).
- **The hub's temperature and the vessel's resistivity in service:** `sim/hub-thermal-findings.md`.
- **The tube layout and its 3-D model** carry the locked hub: `sim/tube_geometry.py --record`
  (`docs/geometry/tube/tube-r150-n6-air6-wound-g0p5-6br-hub50.*`).
