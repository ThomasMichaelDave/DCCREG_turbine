# DCCREG turbine — design ledger and fact sheet

**The design lock of 2026-10-09.** A temporary documentation ledger and the current fact sheet of the exercise.

| | |
|:--|:--|
| status | **LOCKED for now** — the designer, 2026-10-09: "Let's lock the design for now." |
| design state | commit `09243c7` on branch `claude/new-session-0az7f9`; nothing in the design changed after it |
| what the lock means | the design of record below is the baseline; later changes are recorded against it. The lock does not settle what is still PROPOSED or OPEN (§5): those keep their status |
| this ledger | `docs/ledger/DCCREG-design-ledger.md` (the source) and `.pdf` (its print form) |
| the drawings | `docs/ledger/DCCREG-drawings-bundle.pdf`: 44 sheets behind a two-page register (§7) |
| how it is built | `python3 docs/ledger/make_ledger.py` (needs markdown-it-py, mdit-py-plugins, pypdf and playwright with Chromium) |

**Abstract.** As locked, the DCCREG turbine is a belt-driven tube machine. Its rotor and counter-rotor turn at 600 rpm
in opposite directions through a 1 : −1 reversing gear.
- **Two pumps on each shaft half,** both run by the relative rotation at 120 Hz:
  - **the magnetic pump:** three wound utrons pass six iron bridges, wired as the planar dual of a diode charge
    doubler, and drive the anti-Helmholtz (AH) coil pair;
  - **the electrostatic pump:** an air vane stack in a de Queiroz diode doubler drives two copper rings on the
    outside of a 50 mm glass vacuum sphere, through two mirrored Cockcroft-Walton chains.
- **Two static fields at the sphere's centre:**
  - the AH's steady magnetic cusp (300 ampere-turns per coil), with its null at the centre;
  - a DC electric field of 7.10 kV/cm (2.23 Pa), pointing from ring B to ring A and steady to 0.19 %.
- **Where the power goes:** all the belt's power, about 21 W, ends as heat in the clamps, the copper and the iron.
  The products are the fields.
- **What is still open:** the physics is mainstream throughout [OC]. The ratings, the leakage and several parts are
  placeholders that the bench test must qualify.

**Reading notes.**
- **Tags** (`CONVENTIONS.md` §1):
  - [OC] standard, derivable physics;
  - [IR] a modelling or engineering choice, including datasheet-class values;
  - [RH] a heuristic or placeholder, not load-bearing until qualified.
- **Status words** (as the presets use them):
  - DECIDED: by the designer;
  - PROPOSED: worked out here and used, not yet accepted;
  - REGISTER: carried over from an earlier register;
  - DESIGN: the current sizing;
  - OPEN;
  - ESTIMATE.
- **"The record"** is the design of record.
- **Sources:** every number cites the file that holds it; the paths are from the repository root.

## 1. The machine at a glance

![Figure 1. The locked machine: what drives what. The drive turns the two bodies in opposite directions; on each shaft half a magnetic pump and an electrostatic pump run from the relative rotation; both hold a static field at the hub's centre. Source: docs/ledger/figures/architecture.svg (docs/ledger/make_ledger_figures.py).](figures/architecture.png)

**The bodies.**
- **The rotor** carries:
  - the split shaft, which is the electrical reference (REF);
  - the hub;
  - the rotor vanes of the electrostatic stacks;
  - the wound utrons;
  - every circuit part of both pumps.
- **The counter-rotor** carries:
  - the stator cage;
  - the stator vanes, which are REF for the varicaps;
  - the passive iron bridges.
  It holds no wires, and it reaches the shaft through one inner bearing, the reference link.
- **The frame** holds the two end bearings, the reversing gear and the drive. Every reaction torque goes into the gear.
- **The axis** is vertical: side A below, side B above, mirror images about the hub's equator.

**The two pumps** run at 1200 rpm relative, 120 Hz.
- **The magnetic pump:**
  - each side's three utrons form one group, A or B, whose inductance swings 9.4 ↔ 81 mH per coil as the bridges
    pass;
  - groups A and B run in antiphase, in a circuit that is the exact dual of a diode charge doubler;
  - the saturating NiFe neck in each utron is the clamp;
  - one AH coil sits in each group's branch, and a 22 mF bypass across it holds a steady 300 ampere-turns.
- **The electrostatic pump:**
  - the varicaps C1 / C2 swing 55 ↔ 410 pF in antiphase;
  - the de Queiroz diode doubler multiplies its charge each cycle until the clamps Z1 / Z4 hold the nodes at their
    13.1 kV operating peak;
  - the pump's nodes 1 and 4 then feed two mirrored Cockcroft-Walton chains standing on the shaft, which pump ring A
    to −15.0 kV and ring B to +15.0 kV.

**The hub** is a 50 mm borosilicate vacuum sphere with a 1.5 mm wall.
- The two MnZn AH cores sit on its axis.
- The two copper-foil rings lie on the glass, under 0.5 mm of silicone gel in a PEEK retainer, with a G10 coupler
  outside.
- At its centre the AH's null and the rings' field coincide.

**The design in numbers**

| quantity | value | source |
|:--|:--|:--|
| speed | 600 rpm each way, 1200 rpm relative; both pumps at 120 Hz | `sim/pole-design-findings.md` §6; `sim/core_field.py` |
| tube | 916 mm with the air stack of record and the 120 mm placeholder hub; the locked hub adds about 24 mm | `sim/air-stack-sizing-findings.md` §6.5; `sim/hub-locked-findings.md` §4 |
| diameters | vanes Ø300 mm; bridge ring Ø313 mm; stator cage Ø332 mm | `sim/pole-design-findings.md` §8 |
| magnetic pump, per side | 3 wound utrons (200 turns, 2.23 kg each) and 6 SiFe bridges, gap 0.5 mm | `sim/pole-design-findings.md` §8 |
| AH | 160-turn coils on Fair-Rite 77 MnZn rods; 22 mF bypass each; 290–308 A-turns (300 mean, ±3 %) | `sim/ah-steady-cusp-findings.md` |
| electrostatic pump, per side | 6 + 6 Al vanes 3 mm, full rounds R1.5, 6 mm air gaps; C1 / C2 55–410 pF; Ca / Cb 451 pF | `sim/air-stack-sizing-findings.md` §6.5 |
| operating peak | 13.1 kV at the clamps (the 6 mm gap's breakdown over 1.5) | `sim/air_stack_sizing_results.json` |
| rings | Cu foil 0.10 mm, 26.25–55.71° from the axis; beads Ø3 / Ø2 mm; 29.9 mm apart along the glass | `docs/rings-design.md` §2 |
| rings' supply | symmetric: −14.96 / +14.96 kV on 2 + 2 Cockcroft-Walton stages from the shaft | `sim/hub_rings_build_results.json` record |
| field at the null | 7.10 kV/cm from B to A, 2.23 Pa; ripple 0.014 kV/cm p-p (0.19 %); no sign change in a revolution | `sim/hub_revolution_results.json` |
| power from the belt | magnetic 18.1 W + 1.25 W iron; electrostatic 2.14 W | `sim/ah-steady-cusp-findings.md`; `sim/core_field_results.json` |
| cost (placeholders) | the stack of record's build 6,417 EUR; the cheapest qualifying build 6,001 EUR | `docs/cost/README.md` |

## 2. How the design got here

### 2.1 What the machine is for, as the record states it
- **The brief now,** in the designer's words (`sim/core-null-field-findings.md`): the centre of the vacuum core,
  where the AH null sits, should carry the strongest electrostatic field (pressure).
- **The AH pair** should hold a steady cusp (`sim/ah-steady-cusp-findings.md`).
- **Both pumps** are the supplies, driven from one belt through the 1 : −1 gear (`sim/hub-drive-findings.md`).
- **What the field at a magnetic null is to be used for is not documented.** This ledger records the brief as given
  and does not supply a purpose.

### 2.2 The path, in ten steps

Each step asked a question, found an answer in mainstream physics and left a decision behind. The dates are the
commits' dates.

| # | step (dates) | the question | what was found | what it left |
|:--|:--|:--|:--|:--|
| 1 | the browser tool (to 06-09) | a sectored-disc varicap driving a symmetric Bennet doubler | blocks C-I, M, R, D, T, S in `index.html`; anchor z 1.203 | the tool, now retired and frozen |
| 2 | the disc spark-gap machine (06-11 → 06-29) | can a doubler with spark-gap commutation, a resonant tank and islands deliver energy | the doubler's equalisation *is* the pump; only a downstream sink recovers energy; η ≈ 0.70 is forbidden, η ≈ 0.45–0.50 (`docs/efficiency-resolution.md`) | the freeze v0.10 (C_R 789 pF); the efficiency principle |
| 3 | the drawn pump re-checked (09-29 → 10-02) | does the designer's drawn pump pump, exactly | exact engines and gates (PUMP-CALC, PUMP-SYNTH, GEOM stage 2, the integrity tool); z 1.325 on the drawing | the tools, frozen |
| 4 | the round trip and the design loop (10-03 → 10-05) | do the solids keep the gain | the field-solved floors and strays (about 1 nF) take z to 0.83–0.89 (NO-FLOOR-IN-RANGE); interleaved stacks recover 1.24; with the motor in, z = 1.000 | interleaved stacks of vanes are the way to C; the motor cannot sit across Ca |
| 5 | the register and the motor (10-05) | can the C-EMs turn the counter-rotor | they are about five orders short, and the pump's own reaction torque (78 mN·m) needs an outside drive | the belt and the reversing gear |
| 6 | the tube (10-05 → 10-07) | an elongated machine with vane stacks along the shaft | C1 1.11 nF, κ 15.7 in vacuum; diodes beat spark gaps (η 1.00, 3.0 W against 1.3 W at η 0.53) | the de Queiroz diode core is the electrostatic pump |
| 7 | the pivot: two geared pumps (10-07 → 10-08) | drive the AH from the belt too | the planar dual of the doubler works (z 1.528 against 1.512); wound utrons and passive bridges; the mean-turn fix moves the pick to 2.34 kg, 200 turns, 18.8 W | the magnetic pump of record |
| 8 | the air build (10-08) | the first tests run in air | air takes about a third of the vacuum field; 6 mm gaps, full-round vanes, the 6 + 6 cap: 2.14 W; the AH bypass for a steady cusp; the vane matrix and the cost sheet | the electrostatic stack of record |
| 9 | the field at the core (10-08) | the strongest field at the AH null | HV side onto the rotor (unchanged pump); cones steady or swinging (≈1.4 kV/cm); a DC pair inside the vacuum (65.7 kV/cm, but feedthroughs) | the hub locked; the field needs electrodes |
| 10 | the rings (10-09) | rings outside the glass | the beads, not the separation, set the stages; asymmetric 6.93 kV/cm → symmetric 7.10 kV/cm; steady, no swing | the rings and supply of record (`docs/rings-design.md`) |

### 2.3 The designer's decisions

| date | decision | where recorded |
|:--|:--|:--|
| 06-16 | the freeze v0.10 of the disc machine (12 mm septum, C_R 789 pF) | `docs/varcap-design-freeze-v0.10.md` |
| 10-03 → 10-05 | the design loop's rulings: the machine floats; septum ≤ 1000 mm; N = 2; garolite, not PTFE | `sim/rt-design-predictions.md` |
| 2026-10 (pivot) | rotor and counter-rotor geared 1 : −1; the AH on a magnetic pump; both pumps on the belt | `sim/hub-drive-findings.md` |
| 10-08 | "the first tests run in air"; vanes with full-round edges; the 6 + 6 cap | `sim/air-stack-sizing-findings.md` |
| 10-08 | "the AH pair should hold a steady cusp" | `sim/ah-steady-cusp-findings.md` |
| 10-08 | the reference link through an inner bearing "for now", a brush later | `sim/rotor-parts-duty-findings.md` §4 |
| 10-08 | the HV side on the rotor | `sim/core-field-findings.md` (decision 1) |
| 10-08 | the hub locked: layer order, the 50 mm borosilicate sphere, symmetric pumps | `presets/hub-locked.json` |
| 10-09 | the rings outside the glass; a 1.5 mm wall; the AH flanges outside the vessel | `presets/hub-locked.json`; `sim/hub-locked-findings.md` |
| 10-09 | copper foil with rounded edges for the prototype, a fired-on coating later | `sim/hub-rings-build-findings.md` (brief) |
| 10-09 | "go multistage as long as the rings' separation can hold it" | `sim/hub-rings-build-findings.md` (brief) |
| 10-09 | the symmetric supply: "if it pumps against the core centre, yes!" | `docs/rings-design.md` |
| 10-09 | **"Let's lock the design for now."** | this ledger |

### 2.4 What was learned, and what it superseded
- **Charge pumps pay their equalisation tax inside the core** [OC].
  - A doubler with lossy transfers cannot recover what it spends, and only a downstream sink recovers energy. The
    disc machine's claimed η ≈ 0.70 is forbidden (`docs/efficiency-resolution.md`).
  - With smoothly varying capacitance and diodes the transfer itself is lossless (η 1.00), and that is the pump kept
    (`sim/diode-stack-findings.md`).
  - Spark gaps, islands, shuttles and the resonant tank are superseded.
- **Strays and floors set the gain, not size** [OC].
  - The disc's field-solved floors and strays scaled with the build (`sim/round-trip-findings.md` §5).
  - Interleaved vane stacks along the shaft give the capacitance without the carriers' penalty, hence the tube.
  - In air the fixed 20 pF node stray is what pulls the capped stack's z from 1.38 to 1.31
    (`sim/air-stack-sizing-findings.md` §6.5).
- **A pump's reaction torque must go somewhere** [OC]. The C-EMs could not counter-rotate the stator, so the drive
  is an outside belt with a 1 : −1 gear, and every reaction torque goes into the frame (`sim/spinup-findings.md`).
- **The dual circuit works.** Inductors for capacitors, currents for voltages and flux for charge give a magnetic
  pump with its own gain. A saturating neck is its clamp, which makes it the natural driver for the AH coils
  (`sim/magnetic_doubler.py`, `sim/pole-design-findings.md`).
- **Air sets the voltage, the rims the vanes and the cap the power** (`sim/air-stack-sizing-findings.md`):
  - 6 mm gaps for a 13.1 kV peak;
  - 3 mm full-round vanes for the corona margin;
  - 6 + 6 vanes for 2.14 W.
- **The field at a null needs electrodes; outside the glass they need edges** (`sim/hub-rings-build-findings.md`).
  - The vacuum pair inside reached 65.7 kV/cm but needed two HV feedthroughs.
  - The rings need none. Their beads facing the AH coil ends, not their separation, set how many stages they hold.
- **Only the difference between the rings makes field at the null** [OC].
  - The pump's nodes are twins, so identical circuits give none.
  - The record's mirror chains put the null at the shaft's potential and each ring 15 kV from it, and the field is DC
    (`sim/hub_revolution.py`).

## 3. The components and how they work

### 3.1 Bodies, drive, bearings and the reference

![Figure 2. The machine as modelled in 3-D: the section through the shaft (side A below). The reluctance sections are the record; the electrostatic stack drawn is the old vacuum 8 + 8, Ca / Cb sit on the counter-rotor and the hub is the 120 mm placeholder (stale in part, §6). Source: docs/geometry/tube/tube-r150-n8-wound-g0p5-6br-section.png (sim/tube_geometry.py --rel wound).](../geometry/tube/tube-r150-n8-wound-g0p5-6br-section.png)

- **The rotor** turns at +600 rpm and carries all of both pumps' circuits, so no wire crosses between the bodies
  (`sim/core-field-findings.md` §1, §7). It is the split shaft (two halves, each ending in a flange at the hub) with:
  - the G10 sleeve;
  - the rotor vanes (nodes 1 / 4);
  - Ca / Cb, D1–D4 and Z1 / Z4;
  - the utrons on two 12 mm G10 carrier discs per side;
  - La / Lb and D1*–D4*;
  - the hub.
- **The counter-rotor** turns at −600 rpm and carries no HV (`sim/tube_geometry.py`; `sim/pole-design-findings.md`
  §8). It carries:
  - the G10 stator cage (r 162–166 mm), one tube across the hub;
  - the stator vanes (REF);
  - the four inner bearing spiders;
  - six M235-35A bridges per side in a G10 ring, with side B's offset 30°.
- **The frame** holds the two end bearings and their housings, the 1 : −1 reversing gear, the drive motor and the
  belt. The gear and belt are not designed or drawn (placeholders in the cost sheet) [RH].
- **The bearings:** six 6205-class deep-groove bearings (25 / 52 / 15 mm), each on an 8 mm G10 spider.
  - The four inner ones join rotor and counter-rotor at the relative speed; only the two end bearings face the frame
    (`sim/tube-shaft-findings.md` §5).
  - Why six: on the earlier 1263 mm build, two end bearings fail at any shaft diameter, and four need d 34–40 mm. Six
    give d 25 with f1 239 Hz and 5 µm deflection (`sim/tube-shaft-findings.md` §3).
  - That check has not been re-run on the current build.
- **The shaft:**
  - it is d 25 in the tube model and d 30 in the hub's register, which is OPEN (§6);
  - a non-magnetic shaft is recommended [IR];
  - it is split at the hub, each half bolted at its flange (r 32 × 8 mm at ±72–80 mm in the locked hub).
- **The reference link.** The counter-rotor's stator vanes are REF for C1 / C2. They reach the shaft through one inner
  bearing:
  - the path is rail → lead → outer ring → balls → inner ring → shaft;
  - it carries the varicaps' displacement current, 0.41 mA rms of pure AC with no DC (`sim/core_field_results.json`).
  - A floating counter-rotor would need about 10 nF to the shaft, and at 100 pF the pump stops, so the bearing link
    stays. It is not acceptable with a spark dump or without clamps, where the surges need a brush
    (`sim/rotor-parts-duty-findings.md` §4).

### 3.2 The magnetic pump: utrons, bridges and the dual doubler

**How a bridge makes an inductance that swings** [OC].
- A utron is a U-core electromagnet on the rotor. Its two radial tips face the counter-rotor at r 130 mm.
- When a passive SiFe bridge spans both tips, the flux closes across two 0.5 mm gaps and the coil's inductance is
  high: 81.0 mH. Between bridges the nearest iron is 9.74 mm away and it falls to 9.4 mH (κ 8.6).
- Six bridges on a 60° pitch at 1200 rpm relative swing it at 120 Hz. Each bridge sees the three utrons pass, so it
  carries unipolar flux at 60 Hz (`sim/pole-design-findings.md` §8).

**The dual doubler** (`sim/magnetic_doubler.py`).
- The electrostatic diode doubler's circuit graph has a planar dual: capacitors become inductors, voltages currents,
  charge flux.
- In it, the two varicaps become the two utron groups L1(θ) / L2(θ), three utrons in series each (0.243 H). Ca / Cb
  become the chokes La / Lb (0.146 H), and the diodes become D1*–D4*.
- The bridges of side B sit half a pitch on from side A's, so the groups are in antiphase.
- When a group's inductance falls while its flux is held, its current rises: it generates, and the belt does the work
  against the bridges' pull. When the inductance rises the group motors. The groups swap every half cycle.
- Per cycle the stored flux grows by a fixed factor: z 1.21 in the design screen's linear model, against a selection
  rule of ≥ 1.20. The loaded transient run reads 1.139 early on, and 1.147 with the AH bypass
  (`sim/pole_design_variants_op.json`; `sim/ah-steady-cusp-findings.md`).
- Its duality check against the electrostatic doubler gave z 1.528 against 1.512 (`sim/hub-drive-findings.md`).

![Figure 3. The wound utron against a bridge: the 200-turn coil on the split U-core, the 3.0 mm NiFe neck, the bonded slot cover, the studs; the solved 2-D flux. Source: docs/figures/utron-core-detail.png (docs/make_utron_drawing.py). The half-core's manufacturing drawing is DCCREG-UTR-101 (bundle sheet 4).](../figures/utron-core-detail.png)

**The clamp, the start and the parts.**
- **The clamp.** The dual of the avalanche clamps is the iron's saturation. A 3.0 mm 80 % NiFe strip under each
  utron's back iron saturates at Ψs 0.134 Wb-turns per group, and the current then stops growing. The law
  i = Ψ/L·(1 + (Ψ/Ψs)⁶) is a fit [IR]. The neck is sized to the AH's need and no larger, because heat goes as Ψs²
  (`sim/pole-design-findings.md` §3, §8).
- **The start.** With silicon diodes (0.55 V) a small seed does not grow, because the winding voltage while growing
  is only a few volts. A one-time kick of about 20 % (of Ψs) starts it. The kick source is OPEN, and so is its
  polarity if the bypass electrolytics are polarised.
- **The parts:**
  - the utrons: M235-35A 0.35 mm laminations, stack 100 mm, 200 turns of Ø1.55 mm Cu, 0.58 Ω, 2.23 kg each as built;
  - La / Lb: 0.146 H DC chokes, 0.87–1.15 A, ≤ 110 V; first cut a gapped EI, "not designed" [RH];
  - D1*–D4*: silicon, 2.8 A peak, reverse 112 / 101 / 43 / 45 V; parts not chosen;
  - snubbers: an RC at each of the eight nodes (21 nF + 243 Ω) [IR];
  - the wiring stray Lp2 / Lp3: 4.4 mH [IR];
  - the coils run at 46 °C in air (63 °C in vacuum).
- **The power:** 17.6 W on the belt without the bypass (utron copper 12.9, AH 2.00, La / Lb 0.66, diodes 2.01), plus
  1.25 W of iron. With the bypass the belt reads 18.1 W (`docs/schematic-rotor-circuits.png`;
  `sim/ah-steady-cusp-findings.md`).

![Figure 4. The rotor's two circuits as built: (a) the magnetic dual doubler driving the AH pair; (b) the electrostatic de Queiroz doubler with the HV side on the rotor and the rings' two mirrored chains. The 22 mF bypass across each AH coil is not drawn (§6). Source: docs/schematic-rotor-circuits.svg (docs/make_schematic_rotor.py).](../schematic-rotor-circuits.png)

### 3.3 The AH pair and the steady cusp
- **The pair:** two coils on the shaft's axis, one in each group's branch:
  - 160 turns each, 1.01 mH, 0.27 Ω [RH];
  - wound on G-10 formers around Fair-Rite 4077484611 rods of 77 MnZn ferrite, Ø12.3 mm, at ±30.7–72 mm;
  - seated in PEEK 5.7 mm from the vessel (`presets/hub-locked.json` AH, AH_seat).
- **Anti-Helmholtz:** they are wound to oppose, so their fields cancel at the centre (the null) and rise linearly
  away from it, the cusp [OC]. Which coil sits in which branch, and the winding sense that makes the pair oppose, are
  not documented (§6).
- **The steady cusp.**
  - Without a bypass, each coil carries its branch's unipolar 139–449 A-turns at 120 Hz. Top and bottom peak in
    turn, so the null moves along the axis every cycle.
  - A 22 mF capacitor across each coil (34 Hz with the coil, far below 120 Hz) carries the ripple. Each coil then
    holds 290–308 A-turns (300 mean, ±3 %), and top and bottom stay within 17 A-turns (`sim/ah-steady-cusp-findings.md`).
  - 2.2 mF would resonate near 107 Hz and make the ripple worse. The capacitor's duty is light: 0.65 A rms, about
    0.5 V, 8 mW for the pair.
- **The cost of steadiness:** the steady field is the mean, 300 A-turns, against the 449 A-turn peak the AH was
  sized to. A steady 450 needs 240 turns or a larger pump, which is not re-sized. The rod limit is about
  600 A-turns.

### 3.4 The electrostatic pump: the vane stack and the diode doubler

![Figure 5. The air vane stack of record: the stator vane (REF), the rotor vane (node 1 / 4), both at minimum capacitance, side A's half-section, the vane cell and the rim field against Peek's onset. Panel (d) still draws the placeholder hub. Source: docs/figures/air-vane-stack-6mm.png (docs/make_air_vane_drawing.py).](../figures/air-vane-stack-6mm.png)

**The varicaps C1 / C2** (`sim/air-stack-sizing-findings.md` §6.5).
- On each side, 6 stator vanes (REF, counter-rotor) interleave with 6 rotor vanes (node 1 on side A, node 4 on side B)
  across 11 gaps of 6 mm in air.
- The vanes are aluminium, 3 mm thick, every exposed edge a full round R1.5. Each has six 22° sectors on a 60° pitch,
  r 50–150 mm.
- With the sectors aligned the stack is 410 pF. With the rotor's sectors centred between the stator's it is 55 pF
  (κ 7.47).
- C1 and C2 sit half a pitch apart, so they swing in antiphase six times a relative revolution: 120 Hz.

**The doubler** [OC] (`sim/core_field.py`; de Queiroz's symmetrical generator, its Fig. 1 with every diode reversed:
the same circuit at negative polarity).
- **The circuit:**
  - C1 from node 1 and C2 from node 4 to REF;
  - transfer capacitors Ca (1–2) and Cb (3–4) of 451 pF;
  - four diodes: D1 2→0, D2 3→0, D3 1→3, D4 4→2.
- **One half cycle, step by step:**
  1. The capacitor that is shrinking keeps its charge, because its diode is blocked, so its voltage rises as Q/C. The
     rotation does work against the vanes' attraction.
  2. Through Ca or Cb that lift pulls the next node until a diode conducts.
  3. The charge then pours onto the other varicap while it is large, so it accepts the charge at low voltage.
- **The gain.** Charge is collected while a capacitor is large and lifted while it is small, so it grows each cycle
  by a fixed factor: z 1.31 bare (1.3095 in ngspice). With the rings' chains attached, z is 1.191 at start-up.
- **Self-excitation.** Between diode events the circuit is linear and scale-free, so any seed in the growing mode (a
  contact potential, a triboelectric charge) multiplies by z every cycle [OC].

**The clamps and the operating point.**
- z > 1 at every amplitude, so something must stop the growth. The clamps Z1 (node 1) and Z4 (node 4) are avalanche
  strings, first cut 66 × 200 V. They break down at the operating peak V_op 13.13 kV, conduct once a cycle near the
  peak and turn the whole surplus into heat: 1.07 W each, 0.95 mA peak (`sim/core_field_results.json`).
- **V_op** is the 6 mm air gap's breakdown, 19.7 kV, over a 1.5 margin [RH].
- **The rims' field** at 13.1 kV is 44.4 kV/cm, 0.80 of Peek's onset (55.7 kV/cm). Corona starts at 16.5 kV on a
  smooth surface and 14.0 kV on a handled one, margins of ×1.26 and ×1.07 (`sim/air_stack_sizing_results.json`).
- **The nodes:**
  - nodes 1 and 4 swing −13.2 ↔ −5.7 kV, half a cycle apart (mean −8.6 kV);
  - nodes 2 and 3 swing 0 ↔ −6.1 kV.
  - D1–D4 see reverse peaks of 6.1 / 6.1 / 13.2 / 13.2 kV (parts not chosen; the guidance is ×2 rated HV sticks with
    a surge resistor).
- **The power:** the belt pays 2.14 W, all of it into the clamps.
- **Without clamps** the pump runs as a relaxation oscillator: it arcs at the stack, sends 25–47 A surges through the
  diodes and 38 A through the bearing link, so the clamps stay (`sim/electrostatic-no-clamp-findings.md`).
- **Ca / Cb:** 1.1 C_max, six full-annulus aluminium plates per side with 5 gaps of 6 mm, on the rotor. Their mounts
  need 5.7–7.5 kV of creepage and are not drawn.
- **Strays:** 20 pF per node [RH]. Each pF costs about 0.003 of z (`sim/core-field-findings.md` §4).

### 3.5 The hub

Source: `presets/hub-locked.json` (locked 2026-10-08; the decisions of 2026-10-09).

| layer, inside out | what | status |
|:--|:--|:--|
| the vessel | borosilicate sphere, OD 50.0 mm, wall 1.5 mm (R_in 23.5 mm), ε 4.6, vacuum inside; about 0.8 MPa shell stress | DECIDED |
| the rings | two copper-foil bands on the outer surface (§3.6) | DECIDED / DESIGN |
| the AH | the MnZn rods with their 160-turn coils on the axis, PEEK seats at ±25–30.7 mm (§3.3) | DECIDED (placement) / REGISTER (dimensions) |
| the retainer | unfilled PEEK, ε 3.2, r ≤ 30 mm, ±72 mm; a 0.5 mm pocket over the glass with grooves for the beads | DECIDED (role) / PROPOSED (material) / OPEN (dimensions) |
| the interface filler | two-part silicone gel, degassed and vacuum-cast into the pocket, ε 2.9, 0.5 mm | PROPOSED |
| the shaft coupler | G10 outside the PEEK, r 30–33 mm, ε 4.7 | DECIDED (role) / PROPOSED (G10) / OPEN (shape) |
| the shaft | split, flanges r 32 × 8 mm at ±72–80 mm; non-magnetic | DECIDED (layout) / REGISTER (d 30) |
| the pumps | each shaft half carries its side's electrostatic stack and utron group, symmetric top and bottom | DECIDED |

- **Why PEEK and gel:**
  - the glass–retainer interface is what holds the DC between the rings, and a dry machined fit leaves air gaps; the
    gel fills them, beds the beads and takes up the PEEK–glass expansion mismatch;
  - PEEK is non-magnetic and non-conducting, machines well and barely moves the field (−1.5 % to +0.7 % from alumina
    to PTFE);
  - it is the ten-times-less-conductive PEEK, against the glass and gel, that sets the drift (§3.7)
    (`sim/hub-rings-build-findings.md` §1).
- **The vessel's resistivity,** 1e13 Ω·m at 25 °C [IR], falls steeply with temperature (OPEN).

### 3.6 The rings and their symmetric supply

**The rings** (`docs/rings-design.md`; drawing DCCREG-HUB-201, Figure 6).
- **The bands.** Two bands of annealed Cu-ETP foil, 0.10 mm, lie on the vessel's outer surface from 26.25° to
  55.71° from the axis. Ring B is the upper one, ring A its mirror.
  - Each band is 12.85 mm along the glass and 13.1 cm², and the equatorial gap is 29.9 mm along the glass.
  - Each band is cut as 12 gores, 5.79 → 10.81 mm wide, overlapped 1 mm and soldered, and burnished on. There is no
    adhesive film: the gel bonds it.
- **The edges are beaded.** A bare foil edge concentrates the field, so each edge carries a soldered copper wire ring:
  - Ø3 mm at the polar edge, 73.6 mm of wire;
  - Ø2 mm at the equatorial edge, 135.0 mm of wire;
  - each bedded in a groove of the PEEK, 3.5 / 2.5 mm deep.
- **Why these angles.**
  - The polar bead faces the AH coil's end across 5.4 mm of PEEK. A bigger bead comes closer to it, so the polar
    edge does not ease with size, and a ring at 15 kV needs its polar edge at 26° or more.
  - The gap across the equator holds the DC at 1 kV/mm along the glass.
  - Both beads hold 5 kV/mm in the gel [RH]: 4.85 / 4.36 kV/mm on the record.
  - The rings' separation is not the limit; the beads are (`sim/hub-rings-build-findings.md` §2, §4).
- **Later:** a fired-on coating needs the same beads, or a resistive grading toward the pole.

![Figure 6. DCCREG-HUB-201, the rings' manufacturing drawing: the half-section at 2:1, the beads in their grooves at 5:1, one gore flat at 4:1, the feature table and the build notes. Source: docs/drawings/DCCREG-HUB-201.pdf (docs/make_rings_drawing.py).](../drawings/DCCREG-HUB-201.png)

![Figure 7. The rings' DC supply of record: ring B on two positive Cockcroft-Walton stages from node 4, ring A on the mirror image from node 1; both chains stand on the shaft; each capacitor's DC and each diode's reverse peak. Source: docs/schematic-rings-supply.svg (docs/make_rings_supply_schematic.py).](../schematic-rings-supply.png)

**The supply: two mirrored Cockcroft-Walton chains** [OC] (Figure 7; `sim/core_field.py` dc,
`n_cw = n_cw_a = 2`, `a_ref = "shaft"`).
- **Ring B's chain:**
  - node 4 → Co1 → m1 → Co2 → m2;
  - clamp diodes Dc1 (shaft → m1) and Dc2 (b1 → m2), peak diodes Dp1 (m1 → b1) and Dp2 (m2 → ring B);
  - smoothing capacitors Cs1 (shaft–b1) and Cs2 (b1–ring B).
  - Each stage lifts the smoothing column by node 4's swing, 7.5 kV.
- **Ring A's chain** is the same ladder on node 1 with every diode reversed (Coa, Dca, Dpa, Csa). It lowers its
  column by 7.5 kV a stage.
- **How it pumps against the core centre.**
  - Both chains stand on the shaft (0 V). The hub is mirror-symmetric and ring A is ring B's negative, so the null —
    and the whole equatorial plane — sits at the shaft's potential with nothing connected to it [OC].
  - Each ring stands 15 kV from it, as far as its polar bead allows.
- **The parts and levels:**
  - 8 HV diode stacks, all at 7.5 kV reverse;
  - 8 capacitors of 100 pF / 30 kV, each holding a stage's 7.5 kV DC, except Co1 at 13.2 kV and Coa1 at 5.7 kV
    (nodes 4 and 1 sit at −8.6 kV mean);
  - the levels: b1 +7.49 kV, ring B +14.96 kV, a1 −7.49 kV, ring A −14.96 kV; about 27 mJ stored;
  - no Dk and no C_A (`sim/hub_rings_build_results.json` record_supply).
- **Why 100 pF:** it keeps the pump's start-up gain at 1.191 (1.03 at 1 nF), and still smooths the ripple to tens of
  volts.
- **The strays:** 5.1 pF from each ring to REF and 1.1 pF between the rings, behind diodes.

### 3.7 The field at the null, in space and in time

**How the field is computed** [IR] (`sim/core_rings.py`, `sim/hub_locked.py`, `sim/hub_rings_build.py`).
- An axisymmetric finite-volume solve of div(ε grad V) = 0 on the half hub, with 0.25 mm cells.
- REF is the AH envelope, the flanges, the shaft and the box.
- Each geometry is solved in two modes:
  - anti: the rings at ±1, which gives the field at the null per volt across;
  - sym: both at +1, which gives the strays.
- Any supply is their superposition, exact for this linear problem [OC]: E_null = k (V_B − V_A), with
  k = 0.2373 (kV/cm)/kV for the record's bands.
- The beads come from local solves with 0.025 mm cells, bounded by the hub's solution.

![Figure 8. The rings' field: |E| in the section with equipotentials and field lines from B to A; the field and the pressure along the axis and across the equator; ring B's beads from local solves. Source: docs/figures/hub-rings-field.png (docs/make_rings_field_figure.py).](../figures/hub-rings-field.png)

**In space:**
- **At the null:** 7.10 kV/cm along −z (from B to A) and a pressure ε0E²/2 of 2.23 Pa.
- **Within ±5 mm** it varies 4.6 % along the axis and 2.0 % across the equator.
- **Further out:** across the equator it rises to about 7.7 kV/cm at r 14 mm. Along the axis it falls to zero at
  |z| ≈ 17 mm and then turns toward the AH cores, because each band sits between the null and an AH core, both at
  0 V.
- **In the insulation:**
  - 1.00 kV/mm along the glass between the rings;
  - 4.85 / 4.36 kV/mm in the gel at the beads;
  - 1.41 / 2.97 kV/mm in the glass under them;
  - each ring averages 1.81 kV/mm to the AH cores.
- **The retainer's ε** moves the field at the null by less than 2 %; the AH cores take about 13 % of it.

![Figure 9. One revolution of the rotor: the pump goes through its phases twelve times (C1 / C2, nodes 1 / 4, the chains' oscillating nodes), while the rings hold and the field at the null stays 7.093–7.107 kV/cm from B to A. Source: docs/figures/hub-rings-revolution.png (sim/hub_revolution.py).](../figures/hub-rings-revolution.png)

**In time** (the bench test's predictions are Figure 10, §5.3):
- **Start-up** from the pump's seed: 50 % at 0.12 s, 95 % at 0.24 s, 99 % at 0.33 s.
- **The ripple:**
  - ring A carries 34 V p-p and ring B 29 V p-p at 120 Hz;
  - ring A tops up as node 1 bottoms; ring B tops up 1.03 ms later, as node 4 peaks;
  - so the two mostly add: 57 V p-p across the gap, 0.014 kV/cm p-p (0.19 %) at the null.
- **No swing.** Over a whole revolution (12 pump cycles in 0.1 s) the field never changes sign.
  - Each chain's diodes pass charge one way only, and the storage capacitors hold the rings between cycles.
  - The hub turns with the rotor and the rings are symmetric about the shaft, so the rotation changes nothing at the
    null either.
  - A field swinging from A to B would need AC on the rings, through coupling capacitors. That gives about
    ±1.8 kV/cm, with the pressure peaking near 0.14 Pa [IR estimate, not simulated with the rings].
- **The drift.** With the rings held at their DC, the insulators' leakage moves the potential from the electrostatic
  toward the conduction-settled state [OC]. The conductivities are datasheet-class [IR].
  - PEEK with gel at 25 °C: 7.10 → 7.41 (10 min) → 7.78 (1 h) → 7.82 kV/cm (6 h), +10 %, half-way at 13 min.
  - PEI gives +16 %, G10 +1 % (its σ/ε matches the glass's), and the glass at 40 °C +14 % in a quarter of the time.
- **The leakage:** the ledger of paths gives 158 GΩ per ring, against a 100 GΩ estimate. The chains' diodes and
  capacitors dominate; the rings' own insulation is about 200 TΩ (`sim/hub-rings-build-findings.md` §3).

### 3.8 The cost

Source: `docs/cost/README.md`. Every price is a placeholder for a one-off prototype, in EUR [RH].

**The sheet** (`docs/cost/dccreg-air-build-cost-sheet.xlsx`) costs all 2700 vane-matrix stacks with live formulas.

**The placeholder targets:**
- 6.5 kV/cm at the null, which needs 27.4 kV across the rings on the symmetric supply;
- at least 2 W, with z ≥ 1.3;
- at most 6 + 6 vanes;
- corona-safe rims;
- 300 steady A-turns.

81 designs meet them.

| build | design | power | total |
|:--|:--|--:|--:|
| cheapest that qualifies | 6 mm gaps, 2.5 mm vanes, r 175 mm, 22°, 4 + 4 | 2.01 W | 6,001 |
| the stack of record | 6 mm gaps, 3 mm vanes, r 150 mm, 22°, 6 + 6 | 2.14 W | 6,417 |
| lowest cost per watt | 8 mm gaps, 4 mm vanes, r 300 mm, 26°, 6 + 6 | 16.4 W | 8,308 (506 per W) |

**The fixed parts** are 3,702 before the 15 % contingency, about 70 % of the cheapest build:
- magnetic pump 1,552;
- mechanics 1,222, including the gear 250, the drive 250 and the frame 300;
- hub 626;
- electrostatic 180;
- AH 122.

**The stacks' cost** is per-part work, not metal (metal is about 8 %). Aluminium is the choice.

**The symmetric supply** costs 50 more than the asymmetric one: three more diodes and three more capacitors.

**Not costed:** re-sizing the AH or the pumps, the shaft for larger radii, design, test equipment, the vacuum system
and tooling.

## 4. Fact sheet: the numbers of record, with their sources

**Operating point and machine**

| item | value | source |
|:--|:--|:--|
| speed | 600 rpm each way, 1200 rpm relative | `sim/pole-design-findings.md` §6 |
| pump frequency | 120 Hz (6 sectors and 6 bridges per relative revolution) | `sim/core_field.py`; `sim/pole_design_variants_op.json` |
| tube length | 802 mm as modelled (vacuum stack, 120 mm hub); 916 mm with the air stack of record; about +24 mm for the locked hub | `sim/tube_geometry_wound_results.json`; `sim/air-stack-sizing-findings.md` §6.5; `sim/hub-locked-findings.md` §4 |
| bearings | 6 × 6205-class (25 / 52 / 15 mm) on 8 mm G10 spiders; 4 inner, 2 end | `sim/stack_sizing.py`; `sim/tube-shaft-findings.md` |
| shaft | d 25 (tube model) or d 30 (hub register), OPEN; non-magnetic recommended [IR] | `sim/stack_sizing.py`; `presets/hub-locked.json` |
| reference link | one inner bearing; 0.41 mA rms AC, no DC | `sim/core_field_results.json` |

**Magnetic pump** (per side unless stated; `sim/pole-design-findings.md` §7–§8, `sim/pole_design_variants_op.json`)

| item | value |
|:--|:--|
| utrons | 3 at 0 / 120 / 240° on two 12 mm G10 carrier discs; r 57–130 mm; tips 14 mm; slot 30 × 30 mm; stack 100 mm of M235-35A 0.35 mm |
| coil | 200 turns of 1.89 mm² (Ø1.55 mm), 50 % fill, mean turn 319 mm; R 0.58 Ω; L 81.0 / 9.4 mH (κ 8.6); τ 0.140 s |
| neck (clamp) | 80 % NiFe, 3.0 × 100 mm; Ψs 0.134 Wb-turns per group |
| bridges | 6 M235-35A sectors, r 130.5–144.5 mm, 25.5° face, 0.65 kg each, in a G10 ring r 131.5–156.5 mm; side B offset 30° |
| gap | 0.500 mm aligned, 9.74 mm unaligned; 0 clashes in 457 pairs |
| group | 3 utrons in series: 0.243 H; 0.87–2.81 A per branch; 101 V peak |
| La / Lb | 0.146 H DC chokes, 0.29 Ω, 0.87–1.15 A, ≤ 110 V (not designed) |
| D1*–D4* | Si, 0.55 V at 1 A, 2.8 A peak; reverse 112 / 101 / 43 / 45 V |
| gain | z 1.21 (screen, linear); 1.139 loaded early, 1.147 with the bypass |
| kick | about 20 % of Ψs, once, at start-up |
| mass | 2.23 kg per utron as built (SiFe 0.89, NiFe 0.15, Cu 1.07, G10 0.12) |
| power | belt 17.6 W (18.1 W with the bypass) + iron 1.25 W; coils 46 °C in air |

**AH pair** (`presets/hub-locked.json`; `sim/ah-steady-cusp-findings.md`)

| item | value |
|:--|:--|
| cores | Fair-Rite 4077484611, 77 MnZn, Ø12.3 × 41.3 mm at ±30.7–72 mm; G-10 formers ID 13.5 / OD 16.5 mm |
| coils | 160 turns, r 8.25–11.45 mm, ±31.35–71.35 mm; 1.01 mH, 0.27 Ω each [RH] |
| bypass | 22 mF per coil, ESR 10 mΩ [RH]; LC 34 Hz; 0.65 A rms, about 0.5 V, 8 mW for the pair |
| field | 290–308 A-turns per coil (300 mean, ±3 %); top and bottom within 17 A-turns; rod limit about 600 A-turns |

**Electrostatic pump** (per side unless stated; `sim/air-stack-sizing-findings.md` §6.5, `sim/air_stack_sizing_results.json`,
`sim/core_field_results.json`)

| item | value |
|:--|:--|
| vanes | 6 stator (REF) + 6 rotor (node 1 / 4), Al 3 mm, full rounds R1.5; 11 gaps of 6 mm air |
| sectors | 6 on a 60° pitch, 22° stator / 22° rotor; r 50–150 mm; 8° clearance each side at minimum C |
| rings of the vanes | stator ring r 150–162 mm into the G10 cage (r 162–166); rotor ring r 20.5–50 mm on the G10 sleeve (r 12.5–20.5) |
| C1 = C2 | 54.9–409.9 pF, κ 7.47 (4.81–37.3 pF per gap) |
| Ca = Cb | 450.9 pF = 1.1 C_max: 6 full-annulus plates, 5 gaps of 6 mm, on the rotor |
| stack length | 102 mm of C1 + 6 mm + 48 mm of Ca = 156 mm |
| operating peak | 13.13 kV (19.7 kV breakdown / 1.5 [RH]); face field 21.9 kV/cm; rim 44.4 kV/cm (0.80 of onset) |
| gain | z 1.31 bare (1.3095 ngspice); 1.191 at start-up with the rings' chains |
| nodes | 1 / 4: −13.2 ↔ −5.7 kV (mean −8.6); 2 / 3: 0 ↔ −6.1 kV |
| clamps | Z1 / Z4 avalanche strings, BV 13.1 kV (66 × 200 V); 1.07 W, 0.95 mA peak each |
| D1–D4 | reverse peaks 6.1 / 6.1 / 13.2 / 13.2 kV (parts not chosen) |
| power | belt 2.14 W, all into the clamps |
| aluminium (both sides) | rotor vanes 2.9 kg + Ca / Cb plates 6.1 kg; stator vanes 3.4 kg |

**Rings, supply and field** (`docs/rings-design.md`; `sim/hub_rings_build_results.json`; `sim/hub_drift_results.json`;
`sim/hub_revolution_results.json`)

| item | value |
|:--|:--|
| bands | 26.25–55.71°; 12.85 mm along the glass, 13.1 cm² each; gap 29.92 mm; Cu-ETP 0.10 mm, 12 gores per band |
| beads | Ø3 mm polar (contact r 11.06, z ±22.42 mm), Ø2 mm equatorial (contact r 20.65, z ±14.08 mm) |
| ratings used | 1 kV/mm along the glass; 5 kV/mm in the gel at a bead [RH]; 2 / 8 to qualify |
| supply | 2 + 2 CW stages from the shaft; ring A −14.96 kV, ring B +14.96 kV; 8 diodes at 7.5 kV; 8 × 100 pF / 30 kV |
| k | 0.2373 (kV/cm)/kV |
| at the null | 7.10 kV/cm, 2.23 Pa; ±5 mm uniformity 4.6 % (axis) / 2.0 % (equator) |
| fields in the insulation | glass along the gap 1.00 kV/mm; gel at the beads 4.85 / 4.36 kV/mm; glass at the beads 1.41 / 2.97 kV/mm; to the AH 1.81 kV/mm |
| strays | 5.1 pF to REF each, 1.1 pF between |
| time | 95 % in 0.24 s; ripple 0.014 kV/cm p-p; one revolution 7.093–7.107 kV/cm; drift to 7.82 kV/cm in 6 h (PEEK, gel, 25 °C) |
| leakage | 100 GΩ per ring used (ledger 158 GΩ); 4.5 mW |

**What more stages would give** (if the bench qualifies higher ratings; `sim/hub_rings_build_results.json` best_by_family)

| ratings (interface / gel) | stages a side | across | at the null |
|:--|:--|--:|--:|
| **1 / 5 kV/mm (the record)** | **2** | **29.9 kV** | **7.10 kV/cm** |
| 1 / 8 | 3 | 44.3 kV | 7.80 kV/cm |
| 2 / 5 | 2 (wider bands) | 29.9 kV | 8.35 kV/cm |
| 2 / 8 | 4 | 57.9 kV | 13.38 kV/cm |

## 5. Status: decided, proposed, open

### 5.1 The record's parts by status

| part | status | note |
|:--|:--|:--|
| the 1 : −1 gear, the belt, two pumps per side | DECIDED | not designed or drawn |
| air for the first tests; full-round vanes; the 6 + 6 cap | DECIDED | |
| 6 mm gaps, V_op = breakdown / 1.5; 22° / 22°; r 150; Ca = 1.1 C_max | PROPOSED | the cost optimum differs (§3.8) |
| the clamps Z1 / Z4 | PROPOSED | the designer questioned them; keep them, or go to surge resistors and a brush |
| the HV side on the rotor; the link through one inner bearing | DECIDED | "for now"; a brush later |
| the magnetic pick (g 0.5, 6 bridges, 1200 rpm, 200 turns) | PROPOSED | the basis of DCCREG-UTR-101 (Rev A draft) |
| the steady cusp (22 mF bypass) | PROPOSED | answers the designer's "steady cusp"; not drawn on the schematic |
| La / Lb, D1*–D4*, D1–D4, the clamp strings, the kick source | OPEN | parts not chosen or not designed |
| the hub: layer order, sphere, wall, AH placement, symmetric pumps | DECIDED | |
| the rings outside the glass, copper foil, the symmetric supply | DECIDED | |
| the bands and beads | DESIGN | from the [RH] ratings |
| the PEEK retainer, the gel, the G10 coupler | PROPOSED | |
| the ratings, the leakage | OPEN / ESTIMATE | the bench qualifies them |

### 5.2 Open items
- **The bench** (`docs/bench-test-rings.md`):
  - the hold-off ratings (phase 1), which set the stages;
  - each ring's leakage (phase 2);
  - the conductivities (phase 3);
  - the field on the pump's own supply (phase 4).
- **The hub:**
  - the retainer's and coupler's dimensions, the equatorial split (proposed: the plane is at 0 V) and the leads' path;
  - the AH ends facing the polar beads, to be rounded or capped;
  - the AH seat's length;
  - the vessel's resistivity;
  - the magnetic null's position in the locked hub, not computed.
- **The machine:**
  - put the locked hub and the air stack into the layout and the 3-D model, with Ca / Cb on the rotor; rerun the shaft
    and bearing checks;
  - settle the shaft (d 25 or 30, non-magnetic);
  - design the gear and belt;
  - hold ≤ 0.05 mm runout on the four inner bearings for the 0.5 mm utron gap;
  - work out the rotating loads (40–60 g at r 100–150; 0.86 kN per utron; banding);
  - estimate windage.
- **The parts:**
  - La / Lb cores; D1*–D4*; D1–D4 and the chain diodes; the clamp strings; the kick source and its polarity;
  - the capacitor mounts' creepage;
  - potting and balancing;
  - the 77 MnZn datasheet.
- **The models:**
  - a 3-D check of the utrons' κ (the end corrections are [RH]);
  - a nonlinear check of the neck;
  - real-diode start-up;
  - the beads in the settled DC state;
  - the bead–glass contact wedge;
  - the tube's strays, by a field solve.
- **The fields' purpose:** what the field at the null is for is not documented (§2.1).

### 5.3 The bench test

Source: `docs/bench-test-rings.md`.

- **The test hub:** the sphere with a Ø8 mm pumping tube at one pole (≤ 1e-3 Pa) and aluminium AH dummies at REF.
- **The instruments:**
  - a BGO electro-optic probe on a fibre along the axis;
  - ±30 kV supplies through 100 MΩ;
  - electrometers;
  - a DC partial-discharge detector at 10 pC.
- **The phases:**
  1. **Hold-off on coupons and the sphere:** ±15.0 kV for 1 h, then ±18.7 kV for 1 h, under 10 pC. This sets the
     ratings and the stages.
  2. **Leakage:** at least 100 GΩ expected.
  3. **DC drift on lab supplies for 6 h:** 7.10 → 7.82 kV/cm expected, with the return after grounding and a 40 °C
     repeat.
  4. **The pump's own supply at 1200 rpm relative:** 95 % in 0.24 s and 0.014 kV/cm ripple expected; then the AH
     powered, with the Faraday offset measured first.

![Figure 10. What the bench test should see: the start-up, the 120 Hz ripple (the pump's nodes, the rings, the field), the 6 h drift by material, and the test's phases. Source: docs/figures/hub-bench-predictions.png (docs/make_hub_bench_figure.py).](../figures/hub-bench-predictions.png)

## 6. Known inconsistencies and stale records

The lock records them; it does not fix them. Each is a to-do against the baseline.

| # | where | what | effect |
|:--|:--|:--|:--|
| 1 | the 3-D model and layout (`sim/tube_geometry.py`, `sim/stack_sizing.py`, `docs/geometry/tube/…-wound-…`) | the electrostatic stack is the old vacuum 8 + 8 (3 mm gaps), Ca / Cb sit on the counter-rotor, the stator vanes are labelled node 1 / 4, and the hub is the 120 mm placeholder (Ø90 sphere, bicone); 802 mm | the reluctance sections are current, the rest is not; no STEP of the air stack exists |
| 2 | the shaft | d 25 in the tube, d 30 in the hub register | OPEN |
| 3 | `docs/figures/hub-locked.png`, `sim/hub-locked-findings.md` banner | the lock-down's 3-stage, 20–53° rings shown or named as the record | superseded by DCCREG-HUB-201 |
| 4 | `sim/core-field-findings.md` decisions 5 and 7, `sim/core-null-field-findings.md` | call the pair inside, or the 7.8 kV/cm bands, "the design of record" | superseded by the rings of record |
| 5 | `docs/schematic-rotor-circuits` panel (a) | no 22 mF bypass drawn; it quotes the unbypassed 139–449 A-turns; its generator's docstring still mentions Dk | the bypass is in the cost sheet and the bench plan |
| 6 | the cost sheet's BOM | the bypass is 2 × 10 mF = 20 mF per coil against the 22 mF modelled; the utron SiFe is 1.26 kg (the screen) against 0.89 kg as built; it has 4 spiders against 6 in the model | small cost effects |
| 7 | the kick | `sim/pole_design.py` seeds a current of frac × Ψs / L but reports ½ L (frac × I_pk)²: 38 mJ against about 1.5–3.5 mJ seeded; the labels differ ("of Ψs" or "of I_pk") | the kick source is OPEN anyway |
| 8 | A / B naming | A is the top side in the pivot's documents and the bottom in the tube build; which AH coil sits in which branch, and the winding sense that makes the pair anti-Helmholtz, are not documented | to settle before winding |
| 9 | the magnetic gain | quoted on two bases: 1.21 (screen, linear) and 1.139 (loaded, early) | name the basis when quoting |
| 10 | `sim/hub_rings_build_results.json` record_supply | its E_pk_kV_cm 5.99 is V/d over 50 mm (an old convention), not the null's field (7.10 = k·V) | do not read it as the field |
| 11 | the stack of record against the cost optimum | the studies use 6 mm / 3 mm / r 150 / 6 + 6 (6,417); the sheet's cheapest is 2.5 mm / r 175 / 4 + 4 (6,001) | no designer choice between them is recorded |
| 12 | efficiency | the η ≈ 0.45–0.50 of `README.md` and `CONVENTIONS.md` belongs to the disc spark-gap machine; the current machine has no efficiency of record (its products are static fields) | read the README as history |
| 13 | `README.md`, `CLAUDE.md` | still frame the repository as the Bennet-doubler browser tool, with Block C-I as the task | stale frame |
| 14 | `CONVENTIONS.md` "switch naming" | "the solver's ground is the resonator rail" | the reference is now the shaft |
| 15 | `index.html` (frozen) | its banner still reads η ≈ 0.70 | frozen: flagged, not edited |
| 16 | `docs/commutator-design.md`, `docs/kicad/gap-topology-of-record.md` | read as current; both are the spark-gap machine | superseded by the diode core |
| 17 | `CHANGELOG.md` | one block, `[Unreleased]`, not dated; no entries for the design loop or netlists v2–v4 | the git history holds the dates |
| 18 | tags | some hub documents tagged solver choices [OC] and datasheet values [IR] under a redefinition; corrected at this lock in `docs/rings-design.md` and `sim/hub-rings-build-findings.md` to `CONVENTIONS.md`'s meanings | other early hub files may carry the old reading |

## 7. Drawing register

The bundle, `docs/ledger/DCCREG-drawings-bundle.pdf`, carries every sheet below on A3, in this order. It opens with a
two-page register and has bookmarks by part. The drawings stay in the repository at these paths, with the scripts that
redraw them (`docs/ledger/register.py`).

**Part A — the design of record (locked)**

| sheet | title | file |
|:--|:--|:--|
| 1 | The locked machine: what drives what | `docs/ledger/figures/architecture.png` |
| 2 | Rotor circuits: reluctance pump and electrostatic pump | `docs/schematic-rotor-circuits.svg` |
| 3 | The rings' DC supply, the symmetric pair | `docs/schematic-rings-supply.svg` |
| 4 | DCCREG-UTR-101: the wound utron's SiFe half-core | `docs/drawings/DCCREG-UTR-101.pdf` |
| 5 | The wound utron against a bridge | `docs/figures/utron-core-detail.png` |
| 6 | The air vane stack, 6 mm gaps, 6 + 6 vanes | `docs/figures/air-vane-stack-6mm.png` |
| 7 | DCCREG-HUB-201: rings A and B, copper, beaded | `docs/drawings/DCCREG-HUB-201.pdf` |
| 8 | The rings' field at the null | `docs/figures/hub-rings-field.png` |
| 9 | Reluctance sections A and B, plan cuts | `docs/geometry/tube/tube-r150-n8-wound-g0p5-6br-reluctance-plan.png` |
| 10 | Utron A1 with bridge A1, exploded | `…-wound-g0p5-6br-3d-exploded.png` |
| 11 | Reluctance section A, quarter cut | `…-wound-g0p5-6br-3d-reluctance.png` |
| 12 | Reluctance section A, plan at mid-stack | `…-wound-g0p5-6br-3d-plan.png` |

**Part B — supporting drawings and figures of the record (stale content flagged on the sheets)**

| sheet | title | file |
|:--|:--|:--|
| 13 | The machine as modelled: section (stale in part) | `…-wound-g0p5-6br-section.png` |
| 14 | The machine as modelled: quarter cutaway (stale in part) | `…-wound-g0p5-6br-3d-cutaway.png` |
| 15 | The machine as modelled: half section (stale in part) | `…-wound-g0p5-6br-3d-half.png` |
| 16 | The locked hub's stack-up (its rings stale) | `docs/figures/hub-locked.png` |
| 17 | The rings as built: retainer, edges, stages | `docs/figures/hub-rings-build.png` |
| 18 | What the bench test should see | `docs/figures/hub-bench-predictions.png` |
| 19 | One revolution of the rotor | `docs/figures/hub-rings-revolution.png` |
| 20 | Utron size against gain: the pick | `docs/figures/utron-size-vs-gain.png` |
| 21 | The vane matrix: what the radius buys | `docs/figures/vane-matrix-radius.png` |
| 22 | The vane matrix: rim corona margins | `docs/figures/vane-matrix-corona.png` |

**Part C — earlier phases, superseded, kept for the record**

| sheets | what | files |
|:--|:--|:--|
| 23 | the first two-pump hub drive | `docs/schematic-hub-drive.svg` |
| 24–25 | the first pole pick's flux | `docs/figures/pole-pair-flux-g0p5.png`, `-g1p0.png` |
| 26–28 | the core-field studies: the pair inside, AC-coupled rings, floating cones | `docs/figures/core-null-field.png`, `core-rings.png`, `core-swing-waveforms.png` |
| 29–31 | the earlier spark-gap tube build | `docs/geometry/tube/tube-r150-n8-{section,reluctance-plan,clocking-plan}.png` |
| 32–35 | the C-EM and diode-core schematics | `docs/schematic-diode-core-{switchless,dcbus}.svg`, `docs/schematic-cem-{in-discharge-path,motor-placement}.svg` |
| 36–37 | the disc machine's KiCad schematic and its simplification | `docs/kicad/DCCREG_Turbine_circuit.svg`, `schematic_simplification.png` |
| 38–40 | the disc machine's cross-section, boomerang cap, placed motor | `tools/cross-section.svg`, `docs/boomerang-cap.png`, `docs/geometry/motor/motor-il2f-6563b90d-rc40.png` |
| 41–44 | the disc machine's field cuts | `docs/geometry/rt/slices/*.png` |

**CAD and DXF files** (not on sheets; `tools/step-viewer/` renders the STEP files):
- **of the record:**
  - `docs/drawings/DCCREG-UTR-101_half-core_A.step` and `_lamination.dxf`;
  - the machine as modelled, stale in part: `docs/geometry/tube/tube-r150-n8-wound-g0p5-6br.step`, with its `.glb`
    and `.parts.json`.
- **earlier phases:**
  - the spark-gap tube `tube-r150-n8.step`;
  - the disc builds `freeze-v010-CaCb`, `floor-56b6cb83`, `opt-c9ac780b`, `il2-ce1a9380`, `il2f-6563b90d` (with its
    pump + motor);
  - the designer's C-EM source, the two disc DXF layouts (r0.15, r0.6) and the KiCad source.
- **Not drawn anywhere:**
  - the bridge, the bridge ring, the carrier discs and cheeks, the NiFe strip and the coil as parts;
  - La / Lb;
  - the AH coil and core;
  - the kick source;
  - the gear;
  - the retainer and the coupler.

## 8. Files, tools and how to regenerate

**The records:**
- `presets/hub-locked.json` (the hub's spec);
- `sim/hub_rings_build_results.json` (record, record_supply, best_by_family);
- `sim/pole_design_variants_op.json` (the magnetic pick);
- `sim/air_stack_sizing_results.json` and `sim/core_field_results.json` (the electrostatic pump);
- `sim/ah_steady_cusp_results.json`, `sim/hub_drift_results.json` and `sim/hub_revolution_results.json`.

**The findings,** one per study:
- `sim/pole-design-findings.md`, `sim/ah-steady-cusp-findings.md`, `sim/rotor-parts-duty-findings.md`;
- `sim/air-stack-sizing-findings.md`, `sim/vane-matrix-findings.md`, `sim/core-field-findings.md`;
- `sim/hub-locked-findings.md`, `sim/hub-rings-build-findings.md`;
- the design and test documents `docs/rings-design.md` and `docs/bench-test-rings.md`;
- the cost guide `docs/cost/README.md`.

**Regenerate, in order:**
- **the studies:**
  - `sim/hub_rings_build.py --procs 4` (the rings);
  - `sim/hub_drift.py --procs 4`;
  - `sim/hub_revolution.py`.
- **the drawings and figures:**
  - `docs/make_rings_drawing.py`;
  - `docs/make_rings_field_figure.py`;
  - `docs/make_rings_supply_schematic.py`;
  - `docs/make_schematic_rotor.py`;
  - `docs/make_hub_rings_build_figure.py`, `docs/make_hub_bench_figure.py` and `docs/make_hub_revolution_figure.py`;
  - `docs/make_core_drawing.py` and `docs/make_utron_drawing.py`;
  - `docs/make_air_vane_drawing.py`.
- **the cost:** `docs/make_cost_sheet.py`, then recalculate the workbook.
- **this ledger:** `docs/ledger/make_ledger_figures.py`, then `docs/ledger/make_ledger.py`.

**Frozen, unchanged at the lock:**
- `shuttle_core.py`, `reference/`, `sim/pump_engine.py`, `sim/pump_sizing.py`, `sim/pump_synth.py`, `spice/`,
  `index.html`, `tools/pump-calc*`, `tools/pump-synth*` and `charge-pump-synth-live.html`;
- the diff against `b33baa2` is empty.

## Appendix A. Names and symbols

| name | meaning |
|:--|:--|
| REF, node 0 | the shaft, the rotor's electrical reference; the counter-rotor's stator vanes join it through one inner bearing |
| nodes 1 / 4 | the rotor vanes of side A / B: the electrostatic pump's pumping nodes, −13.2 ↔ −5.7 kV |
| nodes 2 / 3 | the transfer nodes between Ca / Cb and the diodes |
| C1(θ), C2(θ) | the varicaps, vanes of side A / B against REF; 55–410 pF |
| Ca, Cb | the transfer capacitors (1–2, 3–4), 451 pF |
| D1–D4 | the electrostatic doubler's diodes: D1 2→0, D2 3→0, D3 1→3, D4 4→2 |
| Z1, Z4 | the clamps on nodes 1 / 4, avalanche strings at 13.1 kV |
| A1–A3, B1–B3 | the wound utrons of side A / B; the groups L1(θ) / L2(θ) |
| La, Lb; D1*–D4*; Lp2, Lp3 | the magnetic doubler's chokes, diodes and wiring strays |
| AH | the anti-Helmholtz coil pair on the axis; the null, its centre; the cusp, its field |
| ring A, ring B | the copper bands on the vessel, A below (−15.0 kV), B above (+15.0 kV) |
| Co / Cs, Dc / Dp; Coa / Csa, Dca / Dpa | ring B's and ring A's Cockcroft-Walton parts |
| m1, m2, b1; n1, n2, a1 | the chains' oscillating and smoothing nodes |
| z | gain per pump cycle (the growth of the stored charge or flux) |
| κ | the swing ratio C_max / C_min or L_max / L_min |
| V_op | the electrostatic pump's operating peak, set by the clamps |
| k | the field at the null per kV across the rings, (kV/cm)/kV |
| g | a gap (never `d`, `CONVENTIONS.md` §2) |
| θ | the rotor angle (`rotor` in code; never φ, the potential) |
