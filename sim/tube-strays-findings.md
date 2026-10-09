# The tube's strays by a field solve — findings

**Source:** `sim/tube_strays.py` → `sim/tube_strays_results.json`; figure `docs/figures/tube-strays.png` (the same
script, `--figure-only` redraws it). About 4 CPU-hours of solves (30, cached in the results file), then 18 minutes of
decks on 2 processes (ngspice).

**Status:** [OC] the electrostatics, the solver's method and its gates; [IR] the model: the record's solids as laid out,
the potentials given to parts the record leaves undefined, the room. The strays it replaces were [RH]
(`sim/core_field.py`:59). This is the ledger's open model check 33, "the tube's strays, by a field solve"
(`docs/ledger/DCCREG-design-ledger.md`:812).

**Scope:** the electrostatic pump of record: 6 + 6 Al vanes per side (3 mm, R1.5 full rounds, 6 mm gaps, 22° / 22°,
r 50–150), Ca / Cb 6 full-annulus plates, the HV side on the rotor (`sim/air_stack_sizing_results.json` thick_vanes
compare t 3 / n 6; `docs/geometry/tube/tube-r150-n6-air6-wound-g0p5-6br-hub50.parts.json`). Side A is solved and side B
is its mirror. All values are per side unless stated.

## Headline

| what | solved | the record | where |
|:--|--:|--:|:--|
| stray to REF, node 1 / 4 (beyond the varicap's own electrodes) | **66.2 pF** (61.6 aligned, 70.8 unaligned) | 20 pF [RH] | §3 |
| stray to REF, node 2 / 3 | **24.5 pF** (24.5 / 24.4) | 20 pF [RH] | §3 |
| node 1 – node 2, beyond Ca's own plates | 1.15 pF | — | §3 |
| across the hub: 1 – 4, 2 – 3, 1 – 3 | 0.048, 0.002, 0.005 pF | — | §3 |
| **C1 = C2, the varicap's own (rotor vanes to stator vanes)** | **450.6 / 128.4 pF, κ 3.51** | 409.9 / 54.9 pF, κ 7.47 | §4 |
| node 1 to REF in all (varicap + strays) | 512.2 / 199.2 pF, κ 2.57 | 429.9 / 74.9 pF, κ 5.74 | §4 |
| Ca = Cb as laid out | 480.5 pF | 450.9 pF | §4 |
| the rings: each to REF / between them | 5.87 / 1.50 pF | 3 / 2 pF in the deck; 5.14 / 1.14 pF from the hub's solve | §3 |
| **z, bare:** the record's caps with the solved strays / as built | **1.196 / 1.058** | 1.3095 | §5 |
| **z at start-up with the rings' chains:** the same two | **1.124 / 1.031** | 1.191 | §5 |
| clamped power: the same two | 1.66 / 0.65 W | 2.14 W | §5 |
| the rings' supply: the same two | ±14.66 / ±13.86 kV; 7.47 / 7.06 kV/cm at the null | ±14.96 kV; 7.62 kV/cm | §5 |

Sources of the record's column: `sim/core_field.py`:59; `sim/air_stack_sizing_results.json`;
`sim/core_field_results.json`; `sim/hub_rings_build_results.json` (record, record_supply, record_supply_free).

1. **The node strays are larger than the 20 pF placeholder, and node 1 / 4's is three times it** [OC: the solve; IR:
   the model].
   - **Node 1 / 4: 66.2 pF.**
     - The rotor vanes' rings reach the shaft through the G10 sleeve: 40.2 / 40.5 pF.
     - The first Ca plate (node 1) reaches the stator vanes through the last rotor vane's openings: 14.6 pF aligned,
       23.1 pF unaligned. This term rises as C1 falls.
     - The rest is 7.0 pF: bearings 3.1, the room 1.9, utrons 1.1, the shaft and flange from the Ca plates 0.9.
   - **Node 2 / 3: 24.5 pF.**
     - The bottom Ca plate faces the Ca|reluctance spider and the utrons below it: 11.5 pF to the utrons, the floating
       bridges' share included.
     - The rest: the stator vanes 4.9, the room 3.5, the bearings 2.5, the shaft and flange 2.1.
2. **The bigger change is in the varicap itself** [OC].
   - The record's C1(θ) comes from a 2-D cell that has no inner or outer rim. It puts a 2 pF floor on C_min alone
     (`sim/stack_sizing.py`:37).
   - Solved with its rims, C1 is 450.6 / 128.4 pF (κ 3.51), not 409.9 / 54.9 (κ 7.47).
   - Each stator sector's inner rim sits over the rotor ring's edge at the same radius, and each rotor sector's outer
     rim sits under the stator ring's edge, 6 mm apart. Together they add 3.4 pF per gap aligned and 5.9 pF unaligned.
   - An independent 2-D solve along the rims agrees (§2).
3. **The pump loses most of its margin** [OC: the deck; IR: the lumped strays].
   - With the record's C1 / Ca and the solved strays: z 1.196, 1.124 with the rings' chains, 1.66 W.
   - As built, with every capacitance solved: z 1.058 and 1.031 with the chains. It still self-excites, but it reaches
     95 % in 0.63 s instead of 0.24 s. It gives 0.65 W, and the rings stand at ±13.86 kV: 7.06 kV/cm at the null,
     against 7.62.
4. **The gates pass** (§2):
   - the solver against three closed forms;
   - the record's own 2-D vane cell reproduced within 1 %;
   - convergence over three grids (z moves 0.0004 across them);
   - the deck with 20 pF reproduces the record to 1e-8.

## 1. The model
- **The solids** are the record's, as `sim/stack_sizing.layout` and `sim/tube_geometry.py --record` lay them out
  (`…-hub50.parts.json` elements) [IR].
  - Side A spans z 100–470 mm: the reluctance section's mid-plane to the hub's equator.
  - **Conductors at REF:**
    - the 6 stator vanes (sectors r 50–150 and a ring 150–162 into the cage);
    - the shaft half (r 12.5), its flange (r 32 × 8 mm at z 390–398);
    - the hub-face and Ca|reluctance bearings (steel, r 12.5–26);
    - the AH core and coil (`presets/hub-locked.json` AH);
    - the three wound utrons (half-cores, NiFe strip and winding, `sim/utron_profile.py` spec of the pick);
    - a REF wall at r 400 mm, the room.
  - **The pump's conductors:**
    - the 6 rotor vanes, node 1 (sectors and a ring r 20.5–50 on the sleeve);
    - the Ca plates, full annuli r 50–150: nodes 1 / 2 alternating, as the parts list marks them.
  - **Floating:** the six bridges.
  - **Ring A:** with its two beads, its foil thickened to 0.5 mm for the grid.
- **Dielectrics** [IR: datasheet-class, `presets/hub-locked.json`]:
  - G10 at ε 4.7: the sleeve, the spiders, the cage, the bridge ring, the carrier discs;
  - the hub's PEEK 3.2, gel 2.9 and borosilicate 4.6;
  - moist air elsewhere: ε 1.000638 (`sim/pump_sizing.py` eps_air at `sim/stack_sizing.py`'s 20 °C, 1013 hPa, 50 %).
- **Every exposed edge a full round R1.5** (the record's words). The solid is every point within 1.5 mm of the vane's
  mid-plane outline, eroded at its exposed edges [IR]. The rotor ring's bore (on the sleeve) and the stator ring's rim
  (in the cage) are not exposed.
- **The solve** [OC: the method]:
  - div(ε grad V) = 0 by node-based finite volumes on a cylindrical grid (r, θ, z), in a 60° wedge with mirror faces.
    That is exact for the record's 6-fold vanes, its 6 bridges and its utrons at 0 / 120 / 240°.
  - The radial conductances use the log law. Every face and material boundary lies on a grid plane; curved and
    oblique conductor surfaces enter at their sub-cell distance along each edge (Shortley–Weller).
  - CG with smoothed-aggregation AMG (pyamg), residual 1e-10. The Maxwell matrix comes from the conductors' charges;
    its asymmetry is ≤ 2e-10 of its largest entry.
- **Two angles:**
  - aligned (C1 at maximum), as the parts list draws it;
  - half a pitch on (minimum): the counter-rotor's stator vanes and bridges turned 30° against the rotor's vanes and
    utrons.
- **The equator is a mirror** (the even mode). One odd-mode solve, with the equator at 0 V, gives the couplings across
  to side B [OC].
- **Taken out as intended:**
  - the varicap's own C = rotor vanes ↔ stator vanes;
  - Ca's own = node-1 plates ↔ node-2 plates.
  - Floating parts are eliminated by their zero charge (Kron reduction) [OC]. What remains between a pump node and REF
    is its stray.
- **Two cross-checks:**
  - **the periodic cell:** one gap of the infinite stack (mirrors at the vanes' mid-planes). Without rims it is the
    record's 2-D cell in 3-D; with them, the real radial build;
  - **an axisymmetric whole machine:** both sides and the hub, the vanes as full annuli (the bound), without utrons or
    bridges. It gives the rings' strays.

| grid | spacing in the stacks: z / r at the rims / θ at the sector edges | nodes (aligned / unaligned) |
|:--|:--|--:|
| level 0 | 1.5 / 0.75 mm / 0.6° | 1.30 / 1.64 M |
| level 1 | 1.0 / 0.5 mm / 0.4° | 3.10 / 4.01 M |
| level 2 | 0.75 / 0.375 mm / 0.3° | 6.23 / 8.07 M |

## 2. The gates
| gate | result | pass |
|:--|:--|:--|
| G-COAX: shaft, G10 sleeve and air to an outer conductor, against the closed form | −3.6e-14 | ✔ |
| G-SPHERE: concentric spheres a 20 / b 40 mm, curved surfaces across the grid, h 1 / 0.5 / 0.25 mm | −0.094 / −0.029 / −0.008 % (second order); the plain staircase −5.1 / −2.4 / −1.3 % | ✔ |
| G-STRIP: a thin strip midway between planes (Cohn's stripline, exact), fringing at sharp edges, h 0.5 / 0.25 / 0.125 | +1.42 / +0.70 / +0.35 % (first order, as sharp edges are); extrapolated −0.003 % | ✔ |
| G-VANE: the record's 2-D cell as it discretises the vane (2.4 mm node to node, R1.2, `sim/stack_sizing.py`:83), solved here in 3-D without rims | 37.53 / 4.852 pF per gap against 37.26 / 4.806 (+0.72 / +0.96 %) | ✔ (≤ a few %) |
| the same with the vane as drawn (3.0 mm, R1.5), h 1 / 0.5 / 0.25 | 37.63 / 5.153 pF per gap (+1.0 / +7.2 % on the record), within 0.1 % across h | — |
| G-MESH: levels 0 → 1 → 2, the varicap aligned / unaligned | 448.9 → 450.2 → 450.6 / 127.1 → 128.1 → 128.4 pF (last step +0.09 / +0.23 %; extrapolated 451.0 / 128.7) | ✔ |
| the same: stray, node 1 | 62.9 → 62.1 → 61.6 / 72.1 → 71.3 → 70.8 pF (last step −0.7 %; extrapolated, order 0.75, 59.6 / 68.9) | ✔ (≤ 3 %) |
| the same: stray, node 2; Ca | 24.53 → 24.53 → 24.52 pF; 480.1 → 480.4 → 480.5 pF | ✔ |
| the same, propagated to the pump: z as built | 1.0575 → 1.0576 → 1.0579 | ✔ |
| G-DECK: `sim/core_field.py`'s deck with 20 pF, this script's copy | z 1.30952787 (record 1.30952788); 2.142322 W (2.142320); with the rings z 1.1906518 (1.1906518), 2.143807 W (2.143808), −14.9603 / +14.9635 kV (−14.9603 / +14.9635) | ✔ |
| cross-check: the rims' fringe by an independent 2-D finite-difference solve (scratch, not shipped) | 11.8 pF/m at the inner rim, 11.7 at the outer, per gap: 5.4 pF over the rims' arcs against the 3-D cell's 5.9 (the corners) | — |

- **The values below are the finest grid's (level 2)** [IR]. The extrapolation is the error estimate.
- **Node 1's stray converges slowly** (order 0.75): where the rotor ring meets the sleeve, metal, G10 and air meet at
  one edge.
  - The periodic cell shows the same: 6.66 → 6.47 → 6.38 pF per rotor vane at h 1 / 0.5 / 0.25.
  - So node 1's stray may be about 2 pF (3 %) lower. In z that is about +0.005 at 0.0027 per pF (§5).

## 3. The strays per node, and where they come from
| part reached | node 1 / 4, aligned | unaligned | node 2 / 3, aligned | unaligned |
|:--|--:|--:|--:|--:|
| the shaft, flange, AH | 41.10 | 41.39 | 2.06 | 2.04 |
| the stator vanes (node 1: the Ca node-1 plates only) | 14.62 | 23.07 | 4.88 | 4.92 |
| the bearings | 3.01 | 3.21 | 2.46 | 2.45 |
| the utrons (the floating bridges' share included) | 1.15 | 1.11 | 11.62 | 11.41 |
| the room (REF wall, r 400) | 1.71 | 2.03 | 3.50 | 3.59 |
| **in all** | **61.60** | **70.81** | **24.52** | **24.42** |
| to ring A (and its image, ring B) | 0.11 | 0.23 | 0.005 | 0.005 |

- **Node 1's 40 pF to the shaft is the sleeve** [OC].
  - The six rotor rings sit on 8 mm of G10 (ε 4.7) over the Ø25 shaft. That coax is 0.53 pF per mm of its length.
  - The rings cover 18 mm of the 93 mm stack, and directly under them it is 1.6 pF a ring.
  - Their faces hold the sleeve's surface between them near node 1's potential, so the interior cell gives 6.4 pF per
    vane. The end vanes add the hub-face bearing and the bare sleeve below the stack.
  - The same cell with a PTFE sleeve (ε 2.1): 3.19 pF per vane, ×0.49 [RH: not the record].
- **The first Ca plate sees the stator vanes** [OC].
  - Each stack ends on a rotor vane (r12) 6 mm above Ca_01, both node 1 (`…parts.json` elements).
  - Through r12's openings Ca_01 faces the next stator vane, 15 mm off. Aligned, the openings line up through the stack:
    14.6 pF. Unaligned, the stator sectors sit right over the openings: 23.1 pF.
  - **This stray swings against C1.**
- **Node 2's bottom plate looks down** onto the Ca|reluctance spider, the bearing and the utrons' end turns, 35 mm
  below. The utrons take 11.5 pF of the 24.5.
- **The variants** (level 1, one choice each; the base: utrons at REF, bridges floating, the room at REF):

| variant [IR] | node 1 / 4 | node 2 / 3 | z, bare | z with the rings |
|:--|--:|--:|--:|--:|
| the base (level 2) | 66.2 | 24.5 | 1.058 | 1.031 |
| the base at level 1 (the variants' grid) | 66.7 | 24.5 | 1.058 | — |
| the room floating (no REF enclosure) | 65.9 | 23.5 | 1.059 | 1.032 |
| the utrons floating | 66.0 | 17.4 | 1.066 | 1.037 |
| the bridges at REF | 67.0 | 27.1 | 1.054 | 1.028 |
| node-1 spacer rings on the sleeve, r 20.5–30, z 223–361, and the node-1 plates on rings to r 20.5 [RH] | 104.9 | 23.1 | 1.026 | 1.008 |

- **The spacer variant** is the mounting that `sim/parts-first-cut-findings.md`:531 proposes as a first cut. It is not
  in the record's solids, which draw bare rings and free plates.
  - Every millimetre of node-1 metal on the sleeve adds about 0.5 pF [OC: the coax above].
  - With it the start-up gain falls to 1.008.
- **Across the hub** [OC: even against odd mode, level 1]:
  - 1 – 4 is 0.016 pF aligned and 0.081 unaligned (mean 0.048);
  - 2 – 3 is 0.002; 1 – 3 and 2 – 4 are 0.005.
  - The axisymmetric bound gives 0.002 (full annuli screen more).
- **The rings** (axisymmetric whole machine, h 0.25 mm at the hub):
  - each ring to REF 5.87 pF, ring to ring 1.50 pF;
  - node 1 to ring A 0.015 pF, to ring B 0.007.
  - The hub's own solve gave 5.14 / 1.14 pF in its box (`sim/hub_rings_build_results.json` record). The deck ran
    3 / 2 pF.
  - In the supply this changes nothing: z 1.1237 → 1.1233, ±14.660 → ±14.660 kV.
- **The axisymmetric bound** (full annuli, no utrons, no bridges): node 1's stray 44.9 pF and node 2's 17.1 pF.
  - Both are below the 3-D values, as they should be: full stator annuli shield Ca_01, and the utrons are absent.
  - The bound's own varicap is 1104 pF.

## 4. The varicap and Ca as built
| per gap (the interior of the stack, the periodic cell, h 0.25) | aligned | unaligned |
|:--|--:|--:|
| the record (2-D cell, `sim/air_stack_sizing_results.json`) | 37.26 | 4.806 |
| 3-D, no rims, the vane as drawn | 37.63 | 5.153 |
| 3-D with the rims (rotor ring 20.5–50, stator ring 150–162, sleeve, shaft, cage) | 41.00 | 11.10 |
| **the rims' share** | **+3.36** | **+5.94** |

| the 11-gap stack, per side | C_max | C_min | κ |
|:--|--:|--:|--:|
| the record: 11 × the 2-D cell, + 2 pF on C_min | 409.9 | 54.9 | 7.47 |
| 11 × the 3-D cell with rims | 450.9 | 122.1 | 3.69 |
| **the stack as built (its ends in, level 2)** | **450.6** | **128.4** | **3.51** |
| node 1 to REF in all (the varicap, Ca_01's swing and the fixed strays) | 512.2 | 199.2 | 2.57 |

- **Why the rims matter** [OC].
  - At minimum C the record's cell sees only the sectors' radial edges, 8° apart.
  - But each stator sector's rounded inner rim (r 50) sits right over the rotor ring's rounded edge (r 50), and each
    rotor sector's outer rim (r 150) under the stator ring's inner edge (r 150): edge to edge, 6 mm apart, along
    115 mm and 346 mm of arc per gap.
  - Aligned, the same rims face continuous metal, so they add less.
- **The record knew both gaps.** `sim/air-stack-sizing-findings.md`:245 says the rims are "a fixed 2 pF floor, not part
  of the 2-D cell". Line 248 says the cell's grid "makes each vane two cells thinner than drawn", so "every κ here reads
  a few % high". The 3-D solve puts numbers on both: the rims +37 / +65 pF, the thickness +1.0 / +7.2 % per gap.
- **What a radial clearance would buy** (the periodic cell, h 0.5) [RH: a design option, not the record's; the
  designer's call; on the whole side in the next section]:
  - the rotor ring's edge is pulled in to r 50 − c and the rotor sectors' outer rims to r 150 − c;
  - the stator sectors' inner rims are pushed out to r 50 + c;
  - the stator ring's inner edge stays at r 150. That makes 2c of clearance at the inner rim and c at the outer, and the
    overlap r 50 + c … 150 − c.
  - `build_cell`'s docstring (`sim/tube_strays.py`:531) says the stator ring's edge moves too. The code keeps it at
    r 150, and the table below is the code's.

| clearance c | per gap aligned | unaligned | κ per gap |
|--:|--:|--:|--:|
| 0 (the record) | 40.98 | 11.09 | 3.70 |
| 3 mm | 38.57 | 9.18 | 4.20 |
| 6 mm | 36.24 | 7.94 | 4.57 |
| 12 mm | 31.65 | 6.40 | 4.94 |

- **Ca as laid out** is 480.5 pF, not the deck's 450.9.
  - Five gaps of 6 mm between full annuli r 50–150 give 463.9 pF as parallel plates; their rims add the rest.
  - The layout rounds the gap count up: `sim/stack_sizing.py`:154, `n_ca = ceil(Ca / c_fixed_gap)`.
  - So Ca = 1.17 C_max(record), and 1.07 C_max as solved.

## 5. The pump with them
`sim/core_field.py`'s own deck and run [OC: the circuit; IR: a cosine C(θ) between the two solved angles, as the record
does]. Each set replaces the 20 pF per node and adds the couplings above:
- the record's caps with the solved strays as fixed node capacitors;
- "as built": C1v swings between the solved totals, so Ca_01's swing is in it; Ca as solved; the rings' solved
  strays.

The clamped runs and the rings' supply are lengthened until they reach the clamp and settle: 24–141 and 280–679
cycles.

| set | z, bare | z with the rings' chains | clamped power | the rings | at the null | 95 % at |
|:--|--:|--:|--:|--:|--:|--:|
| the record (20 pF) | 1.3095 | 1.1907 | 2.142 W | ±14.96 kV | 7.62 kV/cm | 0.24 s |
| the record's caps, the solved strays | 1.1958 | 1.1237 | 1.656 W | ±14.66 kV | 7.47 | 0.28 s |
| the same with the rings' solved strays | 1.1958 | 1.1233 | 1.656 W | ±14.66 kV | 7.47 | 0.28 s |
| the varicap as solved, 20 pF elsewhere | 1.1307 | 1.0802 | 1.206 W | ±14.27 kV | 7.27 | 0.36 s |
| **as built (every capacitance solved)** | **1.0579** | **1.0310** | **0.646 W** | **±13.86 kV** | **7.06** | **0.63 s** |

- **With real HV sticks** (2026-10-09, `sim/diodes-real-findings.md` §6): these rows are the record's near-ideal diodes. As built
  with real sticks the pump does not self-excite: it starts from 122 V (typical leakage), 1.0 kV (the datasheet's
  maximum) or 3.65 kV (hot), and holds −13.38 / +13.40 kV, 6.82 kV/cm with typical sticks (95 % at 0.575 s from a
  consistent −1 kV).
- **The field at the null** is k (V_B − V_A), with k = 0.2546 (kV/cm)/kV, the record's bands with their beads
  (`sim/hub_rings_build_results.json` record) [OC: linear].
- **The start-up times** run from the deck's own start (`uic`, −1 kV); on it the record's 0.24 s
  (`docs/ledger/DCCREG-design-ledger.md`:557) is reproduced. The ledger's item 47 (:886) gives 0.225 s from a
  consistent −1 kV start; the times here are all on the deck's own start.
- **The rings fall less than the power** [OC: the circuit].
  - Each Cockcroft-Walton stage lifts by node 4's swing. The clamps still hold the peak at 13.1 kV, but the swing
    shrinks with the solved C ratios.
  - The power falls with the gain's surplus.
- **The deck's own price of a pF** (the record's caps):
  - nodes 1 and 4 together cost 0.0027 of z per pF;
  - nodes 2 and 3 together cost 0.0018.
  - This agrees with the record's "about 0.003" (`sim/core-field-findings.md`:237) for the 1 / 4 pair.

## 6. The remedies, for the designer (not the record)
**[RH]: options, not the record.**
- **Source:** `python3 sim/tube_strays.py --remedies` → `sim/tube_strays_results.json` remedies (its solves under
  remedy_solves).
- **The grid:** the side model at level 1, 3.9–5.1 M nodes, against the record as built at the same level. The remedy
  builder at c 0 reproduces the record's model node for node (G-REMEDY).
- **The clearance c** is the periodic cell's (§4): the rotor ring's edge to r 50 − c, the rotor sectors' outer rims to
  r 150 − c, the stator sectors' inner rims to r 50 + c, the stator ring's edge kept at r 150.
- **The PTFE sleeve:** ε 2.1 in place of G10's 4.7.
- **Everything else as built:** Ca / Cb as laid out (6 plates, 5 gaps, 480.5 pF), the utrons at REF, the bridges
  floating.
- **The pump:** the §5 "as built" deck set, with the record's couplings across the hub and the rings' solved strays.

| case (level 1, per side) | C1 aligned / unaligned | κ | node 1 in all, κ | stray 1 / 4 | stray 2 / 3 | z, bare | z with the rings' chains | clamped power | the rings | at the null | 95 % at |
|:--|--:|--:|--:|--:|--:|--:|--:|--:|--:|--:|--:|
| as built, the record | 450.2 / 128.1 pF | 3.51 | 512.2 / 199.4, 2.57 | 66.7 pF | 24.5 pF | 1.0576 | 1.0308 | 0.643 W | ±13.86 kV | 7.06 kV/cm | 0.63 s |
| c 12 mm | 347.2 / 74.6 | 4.66 | 411.9 / 147.7, 2.79 | 68.9 | 24.6 | 1.0771 | 1.0407 | 0.715 W | ±13.91 | 7.08 | 0.51 s |
| PTFE sleeve | 450.2 / 128.1 | 3.51 | 491.8 / 179.0, 2.75 | 46.3 | 24.3 | 1.0789 | 1.0453 | 0.826 W | ±13.99 | 7.12 | 0.49 s |
| c 12 mm + PTFE sleeve | 347.2 / 74.6 | 4.66 | 391.5 / 127.3, 3.08 | 48.5 | 24.5 | 1.1053 | 1.0587 | 0.906 W | ±14.04 | 7.15 | 0.41 s |
| c 6 mm | 397.6 / 92.4 | 4.30 | 461.0 / 164.9, 2.80 | 67.9 | 24.6 | 1.0821 | 1.0463 | 0.816 W | ±13.99 | 7.12 | 0.48 s |
| (the record: 20 pF, 2-D C1) | 409.9 / 54.9 | 7.47 | 429.9 / 74.9, 5.74 | 20 | 20 | 1.3095 | 1.1907 | 2.142 W | ±14.96 | 7.62 | 0.24 s |

- **None of them brings the pump back to the record's numbers** [OC: the deck]. Both together do best: z 1.105 bare and
  1.059 with the chains, 0.91 W, 0.41 s.
- **The clearance doubles C1's swing ratio but costs C_max.**
  - κ goes 3.51 → 4.30 at 6 mm and 4.66 at 12 mm. C_max falls 450 → 398 → 347 pF, and the fixed strays stay.
  - So node 1's swing in all rises only to 2.80 / 2.79, and 6 mm gives slightly more z and power than 12 mm.
  - With the shorter rotor sectors, Ca_01 reaches the stator vanes a little more: 15.9–17.1 / 24.2–24.8 pF, against
    14.6 / 23.1.
- **The PTFE sleeve halves the rotor vanes' coupling to the shaft** (40.8 → 20.5 pF) and leaves C1 as it is.
  - Node 1 / 4's stray drops to 46.3 pF. Node 2 / 3's does not move (24.3 pF): its strays are the bottom Ca plate's, not
    the sleeve's.
- **Ca under the record's rule** (Ca = 1.1 C_max, gaps = ceil(Ca / 92.8 pF), `sim/stack_sizing.py`:154), with each
  case's solved C_max:
  - **6 gaps (7 plates)** for the record as built and for the PTFE sleeve: 1.1 × 450 = 495 pF. The plates as laid out,
    5 gaps and 480.5 pF, are 1.07 C_max.
  - **5 gaps (6 plates, as laid out)** for c 12 mm and c 6 mm, alone or with PTFE: 382 / 437 pF needed.
  - The deck keeps the 5 gaps throughout, as asked.
- **Not done:** level 2 for these cases (the record's level 1 → 2 step moved z by 0.0003, §2); intermediate clearances;
  other sleeve materials or thicknesses; the stator ring's edge moved as well (at c 12 mm it would vanish into the
  cage). The figure is not extended: these rows are this table.

## Notes against the record
- `sim/stack_sizing.py`:37, `C_edge_pF=2.0` "inner + outer edge fringe floor added to C_min [IR]" (also
  `sim/air-stack-sizing-findings.md`:245).
  - Solved: the rims add 37 pF to C_max and 65 pF to C_min for the 11 gaps, at both angles.
- `sim/air_stack_sizing_results.json` thick_vanes compare (t 3, n 6): C 54.86–409.90 pF, κ 7.47. The ledger repeats
  it at `docs/ledger/DCCREG-design-ledger.md`:75, :342 and :641 ("55 ↔ 410 pF", κ 7.47).
  - Solved: 128.4–450.6 pF, κ 3.51.
- `sim/core_field.py`:59 / `sim/bicone_drive.py`:27, 20 pF per node [RH]; the ledger at :386 ("Strays: 20 pF per node
  [RH]") and :166 ("the fixed 20 pF node stray is what pulls the capped stack's z from 1.38 to 1.31").
  - Solved: 66.2 pF (nodes 1 / 4) and 24.5 pF (nodes 2 / 3). The bare z is 1.196 with the record's caps and 1.058 as
    built.
- The ledger :350 and :642, "Ca = Cb … 451 pF = 1.1 C_max: 6 full-annulus plates, 5 gaps of 6 mm".
  - Those plates give 463.9 pF as parallel plates and 480.5 pF solved.
- `sim/stack_sizing.py`:83 (and `sim/vane_cell.py`:33), `nt = round(t / hz) − 1`: the record's cell holds a 3 mm vane
  as 2.4 mm node to node (R1.2).
  - Per gap: C_min 4.806 against 5.153 for the drawn 3 mm R1.5 (+7.2 %), C_max +1.0 %. That is the direction
    `sim/air-stack-sizing-findings.md`:248 states, now with its size.
- `sim/hub_rings_build_results.json` record_supply ran with the deck's defaults c_e 3 pF and c_gap 2 pF
  (`sim/core_field.py`:80–81; `sim/hub_rings_build.py` passes neither). The same file's record holds the hub solve's
  5.14 / 1.14 pF, and the ledger :491 and :665 quote 5.1 / 1.1 pF as the strays.
  - The whole-machine solve gives 5.87 / 1.50 pF. The difference does not move the supply (§3).
- `sim/tube_geometry.py`:231–235 places every vane at rot 0, so the 3-D model draws C1 and C2 in phase (parts list
  A_C1_r02 … B_C2_r12, all rot 0.0).
  - The deck runs them in antiphase (`sim/core_field.py` s1 / s2), and the ledger :344 says "C1 and C2 sit half a pitch
    apart". The bridges carry their half-pitch offset; the vanes do not.
- `sim/stack_sizing.py`:176, "starting and ending on a stator vane".
  - The layout ends each stack on a rotor vane beside the first Ca plate, and that is the path for Ca_01's 14.6–23.1 pF.

## Caveats
- **[OC]:**
  - the Laplace solve, its sub-cell boundaries and the log-law radial conductances;
  - the Maxwell matrix, the Kron reduction of floating parts, the even / odd split at the equator;
  - the linear field at the null.
- **[IR]:**
  - **the record's solids as drawn.** The rotor vanes' interconnection, the Ca plates' mounts and connections, D1–D4,
    the clamp strings, the chains' parts and every lead are not drawn, and not modelled. Each adds stray, and the
    spacer row of §3 shows how much one mounting can;
  - **the potentials the record leaves open:** the utrons at REF (their circuit sits within about 100 V of the shaft),
    the bridges floating, a REF room at r 400 mm (the variants in §3);
  - the domain's lower mirror at the utrons' mid-plane (z 100);
  - the full round as the eroded outline's 1.5 mm neighbourhood;
  - ring A's foil thickened to the grid;
  - the datasheet-class ε of G10, PEEK, the gel and the glass;
  - the cosine C(θ) between the two solved angles, the record's own shape: the intermediate angles are not solved;
  - the finest grid's values (node 1's stray may be about 3 % lower, §2).
- **[RH]:** the variants not in the record: the spacers, the PTFE sleeve, the rims' clearance.
- **Not modelled:**
  - the rest of the machine below z 100 and the frame;
  - the vanes' runout and their axial play (the gaps are nominal);
  - surface leakage;
  - the AH's and the cage's details beyond `presets/hub-locked.json` and the parts list.
