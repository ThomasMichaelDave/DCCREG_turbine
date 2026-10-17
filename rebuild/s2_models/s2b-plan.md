# Stage S2b — the field solve on the S2a model: plan

**The designer (2026-10-17):** "Commit the findings and start s2b. Make sure to plan in advance. And tell me what you
want to achieve with S2b and the next phase."

**Status:** the plan, PROPOSED. Nothing in it is solved yet.

## 1. What S2b is for

S1b's circuit runs on values the S2a model never produced:
- C1 / C2 128.4–450.6 pF, from the record's 3-D solve of a different stack (`rebuild/s1_tube/s1_bare.py`);
- Ca = Cb 495 pF, and the core's C_k and the rings' strays from the record;
- node strays from the record's budget.

The S2a model has since changed what those values are:
- the thickened end plates;
- the column's Al-tube combs, the riser and the tap;
- the stator's tie rods and lugs;
- V1b's decks, with the clamp halves' midpoints m1 / m4;
- the cross wires in bracket B;
- the 2 mm glass wall;
- an earthed retainer, against which REF floats at 13.8 kV.

**S2b's aims:**
1. **The circuit's values, solved on the model as built:**
   - C1 and C2 at their extremes, and κ;
   - Ca and Cb;
   - the core's C_k (ring A to ring B through the 2 mm glass);
   - every node's stray, itemised by the part that makes it: N1–N4, m1, m4, REF and earth, between nodes and to REF
     and earth;
   - the couplings across the hub;
   - REF to earth.
2. **The fields at the model's hot spots, at S1b's voltage map:** the vanes' and plates' rims, the combs in the bore,
   the riser and tap against the plates they pass, the decks' parts, the cross wires in the bracket, the midpoint
   rings, the couplings. Each is set against Peek's onset in air or the potting rule. This settles the pairs S2a
   could only flag "field-judged, not by case A".
3. **A handoff S2c can run on without judgement:** one reduced capacitance matrix over S1b's nodes, with each entry's
   convergence band.

**Success criteria [IR, the gates below]:**
- C1 / C2 / Ca converged within 2 % across the levels;
- the strays within 10 %, or their band stated;
- the method proved on analytic cases and on the record's own cell;
- every hot spot under its limit or named.

## 2. The method

- **The solver:** the repo's finite-volume solver, reused by import from `sim/tube_strays.py` (nothing in `sim/` is
  edited) [OC: the method].
  - The parts used: `Problem`, `axis`, `Vane`, `maxwell`, `richardson`, `gate_analytic`.
  - The grid: a cylindrical tensor grid. Conductors are fixed nodes; their surfaces sit at sub-cell distance
    (Shortley–Weller).
  - The equations are solved by CG with smoothed-aggregation AMG (pyamg 5.3). Floating parts are taken out by Kron
    reduction.
- **The geometry adapter (new; `rebuild/s2_models/s2_fv.py`).** The record's solver reads analytic shapes; S2a builds
  OpenCascade solids. The adapter shadows the model's primitives (`TG.sector`, `cyl_z`, `cyl_between`, `wire`,
  `box`, `prism`, `sphere`, `fuse`, `_cut`, …):
  - each call builds both the OCC solid and an analytic `inside(x, y, z)`;
  - the placements (dx, dz, rot) are inverted analytically;
  - a part the shadow cannot express falls back to OCC's point classifier, and is listed.
- **The vanes and plates take the record's full-round edges** (R = t / 2: R1.5, R2 and R2.25 at the end plates)
  through `tube_strays.Vane`. The model draws them square [IR: the record states the rounds; the rims set C_min].
- **Graded parts:** the diode sticks (D1–D4) and the clamp halves (Z1a/b, Z4a/b) carry a potential that runs
  linearly from one net to the other.
  - Each is cut into 4 slices along its axis or arc, each slice its own conductor [IR].
  - The reduction maps each slice's potential onto its two end nets, V = (1 − s) V_a + s V_b, so the matrix becomes
    Tᵀ C T [OC: the linear map of potentials].
- **The HV wires:** the conductor is the 1 mm copper core, inside 3 mm of PTFE as a dielectric.
  - The core is finer than the grid (h 0.75–1.5 mm). Where the grid can't resolve it, the core is drawn at r = h,
    and the wire's pairs are corrected by the line's law: C ∝ 1 / ln(D / r) [OC; IR: the correction].
  - Each correction is stated with its size.
- **Materials (ε_r):**
  - G10 4.7; PTFE 2.1; steatite 6.0; mica 6.5; silicone potting 2.8 [RH];
  - the hub's PEEK, gel and glass from `presets/hub-locked.json`;
  - moist air from `sim/pump_sizing.eps_air`, at 20 °C, 1013 hPa, 50 %.

## 3. Splitting the machine into models

The whole machine at the record's resolution would need about 60 M nodes, which is too many. The S2a model has
symmetries, so it is cut into models that each keep one exactly [OC: by inspection of the model's angles]:

| model | what | symmetry | levels | gives |
|:--|:--|:--|:--|:--|
| **W, the stack** | side A from the deck's outer face (\|z\| 78) to the coupling: the column, the combs, the vanes, the stator's lugs, ties and spider, the REF shaft, the bearing, an earthed cylinder for the retainer [IR] | a 60° wedge with mirror faces: at 30° and 90° when aligned (the N2 comb on one face, the N1 comb on the other), at 0° and 60° half a pitch on. Side B is side A turned half a pitch, so C2(θ) = C1(θ + 30°) [OC] | 0, 1, 2 | C1 and C2 at their extremes, κ, Ca, and the stack's strays (N1, N2 to REF and earth) |
| **H, the hub and the decks** | both sides between Ca_04's mid-planes: the decks (V1b, two-fold), the clamp halves and m1 / m4, bracket B, the cross wires, the riser and tap, the column's first plates, the hub with its rings, the flanges, the sleeve | none (the full 360°) | 0, 1 | the decks' strays, m1 / m4, the cross couplings, the riser / tap couplings, C_k and the rings' strays |
| **A, axisymmetric** | the whole machine as a body of revolution: the vanes smeared to annuli, the retainer as an earthed shell of equal area [IR] | revolution | one fine grid | REF–earth, every node to earth, C_k at the hub's resolution (a cross-check of H), the across-hub couplings |
| **F, the whole, coarse** | everything, the square T-slot frame as drawn | none | coarse only | the earth pairs with the real frame, and the consistency check of the split (G-SPLIT) |
| **cell** | one gap of the infinite stack, periodic | a 30° wedge | 3 spacings | the gate against the record's 2-D and 3-D cells, at 3 / 4 / 4.5 mm |

- **Each capacitance pair is taken from one model only** [IR: the split]:
  - the stack's pairs (N1v, N1c, N2, the stack's REF) from W, extrapolated by Richardson;
  - every pair with a part only H holds from H;
  - the earth pairs from A and F.
  - The pairs two models share are compared, and that comparison is H's and F's error band.

## 4. The steps

| step | what | script → outputs | gate |
|:--|:--|:--|:--|
| **S2b-1** | the geometry adapter, the materials, the nets from the parts list | `s2_fv.py` | **G-GEOM:** each part's `inside()` against OCC's classifier on 2000 points in its box, disagreeing only within 0.05 mm of its surface; every net of `.parts.json` present. **G-ANALYTIC:** `tube_strays.gate_analytic` (coax, plates) through the adapter's path |
| **S2b-2** | the periodic cell at 3, 4 and 4.5 mm | `s2_strays.py --cell` | **G-CELL:** at 3 mm, the record's 3-D cell (`sim/tube_strays_results.json` `cell`, with and without rims) reproduced within 0.2 % at each spacing. The 2-D cell is not the reference: it draws the 3 mm vane 2.4 mm thick between nodes, which puts it 1 % / 7 % under on C_max / C_min (`tube_strays` `gate_vane_record_like`). At 4 and 4.5 mm the values are stated |
| **S2b-3** | W at levels 0–2, aligned and half a pitch | `s2_strays.py --stack` | **G-CONV:** C1 / C2 / Ca within 2 % across levels 1–2 and Richardson's order sane (0.5–4); the strays within 10 % |
| **S2b-4** | H at levels 0–1, both angles | `--hub` | the shared pairs (Ca, the first plates' strays) against W within 5 % at level 1 |
| **S2b-5** | A, then F | `--axi`, `--whole` | **G-SPLIT:** the split's matrix against F's on the pairs both hold, within F's band |
| **S2b-6** | C1(θ)'s shape: W at level 1 at 0, 7.5, 15, 22.5 and 30°. This needs a periodic θ boundary, a subclass of `Problem` (the record has mirrors only) | `--profile` | the departure from S1's raised cosine; S2c takes the solved shape if it departs by more than 2 % [IR] |
| **S2b-7** | the fields: the unit solves superposed at S1b's voltage map (`s2_deck` volts), the peak surface field per part | `--fields` | **G-FIELD:** every exposed surface in air under 0.8 × Peek's onset [RH: the record's rims sit at 0.80]; in the potting under 2 kV/mm average; else named, with its margin |
| **S2b-8** | the assembly: the pairs, Richardson, Kron on the floating parts; S1b's nodes N1–N4, m1, m4, REF, earth; the findings and figures | `s2_strays_results.json`, `s2-strays-findings.md`, `s2-strays.png`, `s2-fields.png` | the matrix symmetric and diagonally dominant; the charge balance per solve within 0.1 % |

- **The cost** [RH, from the record's run: 6–7 M nodes per level-2 solve, several hours on 4 cores]:
  - this machine has 20 cores and 34 GB, so 4–5 solves can run side by side at level 2;
  - W's level 2 and H's level 1 dominate;
  - in all, about one overnight run;
  - `--resume` keeps every finished solve in the results file, keyed by a hash of the geometry and the code, so a
    change re-runs only what it touches.
- **The order:**
  - S2b-1 and S2b-2 first; nothing else runs until their gates pass;
  - then W, H and A in parallel;
  - then F, the profile and the fields;
  - then the assembly.

## 5. What S2b does not do

- **It doesn't change the model.** If a gate or a field shows a fault, S2b names it, and the fix is a change to S2a,
  which the designer decides.
- **It doesn't run the circuit.** That is S2c.

## 6. The next phase: S2c, then S2d

- **S2c, back into the circuit.**
  - S1 and S1b are re-run on S2b's matrix: C1(θ), C2(θ), Ca, Cb, C_k and the strays, with m1 / m4 as real nodes.
  - Their outputs:
    - z;
    - the clamp level and its power;
    - the self-start threshold;
    - the margins.
  - The KiCad sheet *S2* carries the solved values.
  - **The gate:** S1 ↔ S2 converged. z must close against S1b; if the strays drop z below what the designer
    accepts, the evidence names the parts responsible, and the designer chooses the remedy.
- **S2d, the rim variant.** The vanes' rims are reshaped so they no longer face each other edge to edge across the
  6 mm gap. The aim is to win back the κ the rims cost: 7.47 in the 2-D cell, 3.51 as built in the record. It is
  judged on κ, z and the clearances, against S2b as the baseline.
- **Then S3, the scrutiny:**
  - electrical integrity on the solved fields;
  - conservation;
  - mechanics: torsion through the drive, the bench's tap test of the plates;
  - cost.
- **Then S4, the drawings and the parts list by script; S5, the bench.**

## 7. Progress

| step | state | result |
|:--|:--|:--|
| S2b-1, the adapter (`s2_fv.py` → `s2_fv_results.json`) | **done, gates pass** | 339 parts: 280 conductors, 8 graded parts, 77 dielectrics; the nets N1–N4, m1, m4, REF and earth all present. **G-GEOM:** 274 prototypes, 2000 points each, **0 disagreements**; the 7 thin parts (the foils, the midpoint rings, a lead) again at 20000 points, 0. **G-PLACE:** 12 rotated or lifted parts, 0 |
| S2b-2, the cell (`s2_strays.py --cell` → `s2_strays_results.json`) | **done, G-CELL passes** | the record's 3 mm cell reproduced to 0.000 % at every spacing, with and without rims. With the rims, per gap: 3 \| 3 mm, κ 3.694 (40.995 / 11.098 pF); the first rotor vane's gap, 4 \| 3 mm, κ 3.584 (41.196 / 11.494); the last stator vane's, 3 \| 4.5 mm, κ 3.534 (41.099 / 11.629). Over the 11 gaps of a side, the two end gaps cost κ 0.7 % (3.694 → 3.669) [IR: the gaps summed, the stack's ends left to W] |
| S2b-3 … 8 | next | the stack W, the hub H, the axisymmetric A, the whole F, the profile, the fields, the assembly |
