# The electrostatic circuit's HV side on the rotor, and a swinging field on the core — findings

**Source:**
- `sim/core_field.py` → `sim/core_field_results.json` (ngspice), and `--grid` → `sim/core_swing_grid.json`;
- the schematic's panel (b), `docs/schematic-rotor-circuits.svg` / `.png` (`docs/make_schematic_rotor.py`);
- the stack drawing's labels, `docs/figures/air-vane-stack-6mm.png`;
- the cost sheet, `docs/cost/` (`docs/make_cost_sheet.py`);
- the waveforms, `docs/figures/core-swing-waveforms.png` (`docs/make_core_swing_figure.py` →
  `sim/core_swing_waveforms.json`).

**Designer's decisions:**
1. Move the electrostatic circuit's high-voltage side onto the rotor, so the core can get an electric field with the AH's
   steady cusp at its centre.
2. Then: a swinging field instead of one referred to the shaft, on floating cones (§2).
3. **The hub, from the inside out** (designer's description):
   - the core, encapsulated in a non-magnetic composite retainer;
   - the field (AH) coils around it;
   - probably some insulation;
   - and over that the shaft-coupling cones, non-metallic and non-magnetic (probably G10).

   The materials are open; they are to keep the field as high as possible without adding parasitic capacitance. There
   are no electrodes per se.
   - **A dielectric adds no capacitance of its own.** It only scales the capacitance between conductors whose field runs
     through it, by up to its εr: G10 4.7, PTFE 2.1.
     - The 20 pF / 10 pF strays in §2–§3 belong to the conductors that would carry the swing, not to the cones.
     - Where a shell sits between those conductors and the core, a higher εr leaves more of the voltage across the core
       but raises their capacitance.
   - **Open: which conductors carry the pump's swing to the core.**
     - As described, the conductors around the core are the field coils and the shaft flanges at the cones' apexes. All
       of them sit within about 100 V of the shaft.
     - With nothing at the swing, the core sees no field from the pump.
     - The field coils, at the shaft's potential, would also screen the core from a swing applied outside them.
   - Below, "cone A / B" stands for whatever conductor carries that side's swing.
4. **Proposal (designer):** two electrode rings on the vessel, one on each hemisphere, as those conductors (§4).
5. **Brief (designer), after the rings:** the strongest electrostatic field (pressure) at the core's centre, on the AH
   null. The AH coils stay independent; the bicone may go; how is open; both pumps are the supplies.
   - **Now the design of record:** two Rogowski electrodes in the vacuum on the null, on the pump's DC. Electrode A
     takes node 1's peak and electrode B one multiplier stage on node 4: 20.6 kV across 3.14 mm, 65.7 kV/cm and 191 Pa
     at the null.
   - See `sim/core-null-field-findings.md`. §2–§4 below are the cones' and rings' studies that led there.

**The design.** The air build's capped stack (`sim/air_stack_sizing.py` stage 4c): 3 mm full-round vanes, 6 + 6 per
varicap per side, 6 × 22° / 22°, 6 mm gaps, r 150. That gives C 55–410 pF, Ca = Cb 451 pF and V_op 13.1 kV, at 1200 rpm
relative (120 Hz).

## 1. The move

**What changes:**

| part | before | now |
|:--|:--|:--|
| rotor vanes R-A / R-B | near the shaft, through the cones | **nodes 1 / 4** (HV) |
| stator vanes | nodes 1 / 4 (HV) | **REF of C1 / C2**, on the counter-rotor |
| Ca / Cb, D1–D4, Z1 / Z4 | counter-rotor | **rotor**, with the hub |
| cones | 32-turn coils in series, at the shaft's potential | **non-conducting shaft-coupling cones**; the conductors for the core's swing are open (§2) |
| reference link | one inner bearing | the same bearing: it joins the stator vanes to the shaft |

**The pump does not change.** The circuit is the same; only the bodies under its parts move.
- The gain z is 1.3095 per cycle, against the stack's eigen-cycle 1.3090.
- The clamped power is 2.1423 W, against 2.1423 W before the move (within 0.002 %).

**The node waveforms (steady state, clamped):**
- node 1 swings from −5.7 to −13.2 kV; node 2 from 0 to −6.1 kV;
- V_Ca = V(1) − V(2) runs from −5.7 to −7.5 kV;
- V(1) − V(4) swings ±7.4 kV at 120 Hz.

**The reference link stays.**
- It carries 0.41 mA rms (0.92 mA peak) of pure AC, C1 and C2's displacement current. The DC through the diodes and
  clamps stays on the rotor.
- **A floating counter-rotor needs a large capacitance to the shaft instead [IR]:**

  | counter-rotor to shaft | z per cycle |
  |--:|--:|
  | 100 pF | 1.000: the pump stops |
  | 1 nF | 1.18 |
  | 3.3 nF | 1.265 |
  | 10 nF | 1.294; 2.01 W, the counter-rotor 0.3 kV off the shaft |

  10 nF is about 1.1 m² of electrode at a 1 mm air gap between the bodies, so the bearing stays.

## 2. A swinging field on floating cones (the design of record until the null-field brief)

**Superseded** as the design of record by the DC field on the null (decision 5, `sim/core-null-field-findings.md`).

**The wiring.**
- Cca (1 nF) couples node 1 to cone A, and Ccb (1 nF) couples node 4 to cone B.
- Nothing else ties the cones to the shaft. Their leakage (10 GΩ each [RH]) sets their DC, about the shaft's potential,
  after a few R_leak · CC (10 s each).

**What the core sees** (the steady state, the DC set by the leakage):
- **±7.1 kV at 120 Hz** between the cones (14.1 kV p-p). The field reverses every half cycle: ±1.4 kV/cm over the
  placeholder 50 mm.
- **Each cone** swings from −4.4 to +2.7 kV against the shaft, in antiphase with the other. Their common mode moves
  from −1.0 to +1.4 kV.
- **Cca / Ccb** hold up to 8.8 kV: the nodes' DC, plus the swing.

**What it costs.** The cones' strays (20 pF each to the shaft side, 10 pF between them [RH]) now sit on the pumping
nodes.
- z falls from 1.310 to 1.231, and the clamped power from 2.14 to 1.78 W (0.89 W per clamp).
- That is below the cost sheet's placeholders (z ≥ 1.3, ≥ 2 W): **the stack of record no longer meets them** (§3).
- **What the steady option needed and this one doesn't:** the diode. The core's leakage takes only 1.5 mW at 10 GΩ, and
  the link carries 0.34 mA rms.

**Other ways to swing it** [IR]:

| wiring | the core sees | the cones against the shaft | z | clamped power |
|:--|--:|:--|--:|--:|
| **floating, on Cca / Ccb** | ±7.1 kV | −4.4 … +2.7 kV | 1.231 | 1.78 W |
| straight on nodes 1 / 4 | ±7.3 kV | −13.2 … −5.8 kV | 1.231 | 1.76 W |
| straight on nodes 2 / 3 | ±5.6 kV | −5.9 … 0 kV | 1.247 | 1.72 W |

**Floating costs 4 % of the swing**, through the coupling capacitors' divider, and takes the nodes' 8.6 kV DC off the
cones. That 8.6 kV would otherwise stand between the cones and the flanges and the AH.

**Why each cone swings −4.4 / +2.7 kV, while the core sees ±7.1 kV** (`docs/figures/core-swing-waveforms.png`):
- **Node 1 is not a sine.** It rests near its top (−5.8 kV) for most of the cycle and dips to the clamp (−13.2 kV)
  around minimum C1. It spends 60 % of the cycle above its average (−8.6 kV), which sits 0.9 kV above the midpoint of
  its swing (−9.5 kV).
- **The coupling capacitor removes only that average.** Each cone therefore swings +2.8 / −4.6 kV about it (×0.96 for
  the divider: +2.7 / −4.4 kV). In harmonics, node 1 carries 3.84 kV at 120 Hz and 1.19 kV at 240 Hz; the 240 Hz part
  makes the asymmetry.
- **Node 4 is node 1 half a cycle later.** Half a cycle reverses the odd harmonics and keeps the even ones.
  - Across the core (A − B), the even harmonics cancel: 7.39 kV at 120 Hz, 0.19 kV at 360 Hz, and nothing at 240 Hz.
    The field is symmetric.
  - In the common mode, (A + B) / 2, the odd harmonics cancel: both cones move together, 1.17 kV at 240 Hz, against the
    shaft. That moves the core's potential, not its field.
- **What it would take to centre each cone on the shaft** (±3.6 kV): a +0.9 kV bias on its DC. It would not change the
  field across the core, only the peak to the flanges (4.4 → 3.6 kV).

## 3. The swinging core across the matrix

**The grid.** ngspice over C_max 130–12000 pF × κ 3–75 (Ca = 1.1 C_max): the swing's peak, z and the clamped power,
with the floating cones and bare. The cost sheet interpolates it for each of the 2700 designs.

- **The swing is 0.53–0.68 of the operating peak** wherever κ ≥ 5 and C_max ≥ 250 pF, which covers every feasible
  design. It is lower at κ 3. The ratio is higher on big stacks, where the clamp's 100 kΩ lets the nodes overshoot
  [IR].
- **The gain cost shrinks as the stack grows:**

  | C_max (κ 8) | z bare → with the cones | power kept |
  |--:|--:|--:|
  | 450 pF | 1.332 → 1.256 | 85 % |
  | 1500 pF | 1.399 → 1.371 | 96 % |
  | 3000 pF and up | within 0.02 | ≥ 98 % |

  Below about 250 pF the cones take most of the gain: z ≤ 1.10, and a quarter of the power or less.
- **What the matrix can do with a swinging core.** Cost sheet at the default prices, with N ≤ 6, z ≥ 1.3, ≥ 2 W and
  corona-safe rims:

  | swing wanted | cheapest design | its swing | z | power | total |
  |:--|:--|--:|--:|--:|--:|
  | ≥ 6 kV | 5 mm gaps, 2 mm vanes, r 200, 18°, 4 + 4 | 6.2 kV | 1.362 | 2.06 W | 5,663 |
  | ≥ 7 kV | 6 mm gaps, 2.5 mm vanes, r 200, 22°, 4 + 4 | 7.2 kV | 1.313 | 2.58 W | 5,858 |
  | ≥ 8 or 9 kV | 8 mm gaps, 4 mm vanes, r 250, 22°, 4 + 4 | 9.2 kV | 1.301 | 5.04 W | 6,445 |
  | ≥ 10 kV | none | | | | |

  - **The largest swing** is 9.4 kV (8 mm / 4 mm at r 300, 6 + 6), or 9.75 kV uncapped at 16 + 16.
  - **The best per watt** is 6 mm / 2.5 mm at r 300, 26°, 6 + 6: 7.4 kV, 14.8 W, 503 per W.
- **So the placeholder target (2 kV/cm over 50 mm, 10 kV) is out of reach for a swinging field in air.** At 2 kV/cm
  the cones must be at most 46 mm apart (9.2 kV), or 35 mm at the stack of record's 7.1 kV.
- **The 10 mm gaps** would reach it (20.6 kV peak), but need rims thicker than the matrix's 4 mm.

## 4. Electrode rings on the vessel (designer's proposal)

**Source:** `sim/core_rings.py` → `sim/core_rings_results.json`; the figure `docs/figures/core-rings.png`
(`docs/make_core_rings_figure.py`).

**The model.**
- **The hub [RH]:** the tube's placeholder, in the designer's layer order:
  - the glass vessel, r 42–45 mm;
  - the composite retainer, 45–48 mm;
  - the field coils as two loops at the shaft's potential, 6 × 6 mm at r 47–53, |z| 18–24, where they fit inside
    the cones;
  - the G10 cones;
  - the flanges, shaft and bearing, the cage and the first stator vanes as REF.
- **The rings** sit on the vessel under the retainer, A on the upper hemisphere and B its mirror. Each is coupled
  through 1 nF to node 1 / 4.
- **The solve:** axisymmetric field solves give the field at the centre and each ring's strays [OC]. The solver
  reproduces a sphere between planes to 0.6 %, and halving the grid moves the results 2–3 %.
- **The pump:** the float wiring with those strays.

**The rings work.**
- **They sit inside the field coils,** so the coils do not screen them.
- **They add little capacitance** (that is far less than the 20 / 10 pF guessed for electrodes on the cones):
  - at 20–50° from the axis, 3–8 pF each to the shaft side (the coils, the flanges) and at most 1.6 pF between them;
  - nearer the coils, at 60–70°, up to 19 pF and 4.3 pF.
- **The pump keeps z 1.28–1.30 at 20–50°** (1.25 at worst; bare 1.31), 1.9–2.1 W, and a ±7.2–7.4 kV swing between
  the rings.

| ring | polar angle | to the shaft side | ring to ring | field at the centre, peak | z | power |
|:--|--:|--:|--:|--:|--:|--:|
| wire Ø 2 mm | 40° | 5.4 pF | 0.2 pF | 0.68 kV/cm | 1.291 | 2.09 W |
| wire Ø 2 mm | 50° | 6.8 pF | 0.3 pF | 0.71 kV/cm | 1.287 | 2.07 W |
| wire Ø 6 mm | 50° | 8.3 pF | 0.5 pF | 0.80 kV/cm | 1.283 | 2.05 W |
| band 10 mm | 40° | 6.6 pF | 0.3 pF | 0.83 kV/cm | 1.288 | 2.07 W |
| band 10 mm | 50° | 8.4 pF | 0.6 pF | 0.87 kV/cm | 1.282 | 2.05 W |

**The field at the centre is modest:** 0.5–0.9 kV/cm peak, alternating at 120 Hz, axial and fairly uniform inside the
vessel.
- That is about half of the swing over the rings' spacing, because thin rings hold little charge.
- Per kV of swing it is 0.06–0.12 kV/cm, a property of the geometry. A larger swing scales it: the 8 mm-gap stacks'
  9.2 kV would give about 1.1 kV/cm.
- 2 kV/cm at the centre would need about 20 kV of swing with these rings.

**Where to put them:**
- **About 40–50° from the axis** gives the most field.
- **Towards the poles** the rings shrink and feel the flanges.
- **Towards the equator** they couple to each other and, here, to the field coils.
- **A wider ring** (the band) gives more field for more capacitance.
- **The field coils** cost 5–9 % of the field at 20–60° (11–19 % at 70°) and add capacitance as the rings approach
  them. With them left out, the rings' stray to the shaft side stays about 3–5 pF at any angle.

**The pump's budget for strays, for any electrodes** (geometry-free; the stack of record):

| to the shaft side \ ring to ring | 0 pF | 2 pF | 5 pF | 10 pF |
|--:|--:|--:|--:|--:|
| 0 pF | 1.307 | 1.301 | 1.292 | 1.277 |
| 2 pF | 1.301 | 1.295 | 1.286 | 1.272 |
| 5 pF | 1.293 | 1.287 | 1.278 | 1.264 |
| 10 pF | 1.280 | 1.274 | 1.266 | 1.253 |
| 20 pF | 1.256 | 1.251 | 1.243 | 1.231 |

Each pF costs about 0.003 of z either way. z ≥ 1.30 allows about 2 pF each.

**Not covered:**
- the real hub's dimensions;
- the field coils' real size and place (160 turns of Ø 1.5 mm need about 20 × 20 mm, which the placeholder hub cannot
  hold);
- the rings' surface field. Under the retainer it sits in the composite, so voids there would discharge.

## 5. The steady alternatives

**The earlier options** for comparison. These were the recommendation before the designer chose a swinging field.

| option | what the core sees | E over 50 mm | z per cycle | clamped power | extra parts |
|:--|:--|--:|--:|--:|:--|
| none (no field) | — | — | 1.310 | 2.14 W | — |
| **series:** the cones stay coils, now between node 1 / 4 and the rotor vanes | V(1) − V(4): ±7.3 kV at 120 Hz, no DC | ±1.5 kV/cm AC | 1.233 | 1.76 W | none |
| **ca:** cone A on node 1, cone B on node 2 | −6.7 kV mean, 1.7 kV p-p (26 %); both cones also swing 6.5 kV p-p against the shaft | 1.3 kV/cm | 1.266 | 1.95 W | none |
| **peak:** cone A charged from node 1 through diode Dk and held by C_core 1 nF; cone B on the shaft | **−13.2 kV DC, 11 V p-p (0.1 %)** | **2.6 kV/cm** | 1.087 while charging, then 1.31 | **2.14 W** | Dk, C_core |

- **The peak option** gives the full operating peak, almost without ripple, and leaves the pump's power as it is.
- **The others cost gain:** the cones' strays sit on the pumping nodes.
- **The series option** keeps the cones as coils, but with diodes only they carry 0.46 mA rms (0.05 A-turns): still
  decorative.

## 6. The steady (peak) option in detail

**The core's leakage sets the load.** With C_core at 1 nF:

| core leakage R_leak [RH] | z while charging | cone A | p-p | leakage power | clamps |
|--:|--:|--:|--:|--:|--:|
| 10 GΩ | 1.087 | −13.2 kV | 11 V | 0.017 W | 2.12 W |
| 1 GΩ | 1.082 | −13.2 kV | 102 V | 0.17 W | 1.97 W |
| 0.1 GΩ | 1.035 | **−11.1 kV** | 0.72 kV | 1.23 W | 0.61 W, Z4 only |
| 0.05 GΩ | **0.987** | the pump does not start | | | |
| 0.03 GΩ | 0.958 | the pump does not start | | | |

- **Keep the core above about 1 GΩ.** Below about 0.06 GΩ the gain falls under 1, and the pump cannot start.
- **The ripple** follows V / (R_leak · C · f) within 5 %. A 0.1 nF C_core at 10 GΩ gives 83 V p-p and charges faster
  (z 1.225).
- **Start-up:** from −1 kV, cone A reaches 95 % in 32 cycles (0.27 s) with 1 nF.
- **The parts:**
  - Dk sees a 7.5 kV reverse peak, because node 1 never rises above −5.7 kV;
  - C_core is 1 nF, rated ≥ 20 kV;
  - D1 / D2 see 6.1 kV reverse and D3 / D4 13.2 kV;
  - the clamps take 1.07 W each.
- **The field's direction:** from cone B (on the shaft) down to cone A. Running the core positive (every diode flipped)
  reverses it.

## 7. What the HV on the rotor asks of the build

**The G10 sleeve now holds node 1 off the shaft.**
- The rotor vanes' rings sit on the 8 mm sleeve over the d 25 shaft. At 13.2 kV the field is 2.1 kV/mm at the shaft and
  1.3 kV/mm at the sleeve's surface, which G10 holds in bulk.
- **An air film at the bore** sees about 4.7× the G10's field (εr), so 10 kV/mm. A 50 µm film then carries 0.50 kV
  against Paschen's 0.55 kV, and it would discharge on every cycle [OC].
- **Bond the sleeve to the shaft, or make its bore conductive** [RH]. The same applies, at a lower field, under the
  rings.

**The Ca / Cb stacks ride on the rotor.**
- **Mass:** their 6.1 kg moves to the rotor. That adds 0.076 kg m² to the rotor vanes' 0.029, i.e. 151 J against 57 J
  at 600 rpm per body.
- **Mounts:** the alternate plates (nodes 1 / 2, and 4 / 3) differ by V_Ca, 5.7–7.5 kV. The mounts between them need
  that much creepage. The mounts are not drawn.
- **Not re-run:** the shaft check (`sim/shaft_bearings.py`) and the solids (`sim/tube_geometry.py`) still put Ca / Cb
  on the counter-rotor. So does `sim/stack_sizing.layout`, which labels the stator vanes node 1 / 4.

**The hub.**
- Both cones now swing, −4.4 to +2.7 kV each against the flanges and the AH coils (near the shaft's potential), and up
  to 7.1 kV against each other where the G10 shells meet at the equator.
- That is less than the steady option's −13.2 kV DC on cone A. The electrode's extent on the shell sets the clearances
  and the creepage; it is not chosen.

**The counter-rotor carries no HV:** the stator vanes, the cage and the bridges are at REF.

**The parts on the rotor:**
- at 600 rpm they see 40 g at r 100 mm and 60 g at r 150 mm, so pot them and balance the rotor with them;
- the clamps' 1.8 W is shed on the rotor.

## 8. What was updated
- **The schematic's panel (b):** the new bodies, the floating cones on Cca / Ccb with the swinging E, and this stack's
  numbers (it showed the vacuum stack before).
- **The stack drawing's labels:**
  - stator vane = REF, rotor vane = node 1 / 4;
  - Ca plates on the rotor;
  - the aluminium per body;
  - a row for the HV side.
- **The cost sheet:**
  - **Inputs:** the core field, 2 swinging (the default) or 1 steady. The targets are checked against that mode's
    voltage, z and power.
  - **Designs:** the swinging core's swing, z and power per design, from the grid (AM–AO), and the mode's values
    (AP–AR).
  - **BOM fixed:**
    - the core capacitors: two (Cca, Ccb) swinging, one (C_core) steady;
    - the cones' leads and clearances;
    - the rotor's HV insulation.
    - Totals: 3,486 swinging, 3,461 steady.
  - **HV parts:** four diode stacks swinging, five steady (with Dk).
  - **The result:**
    - steady mode reproduces the earlier optimum (5,637);
    - with the swinging default, no design meets the placeholder 10 kV (§3).

## Caveats
- **[RH]:**
  - the strays (20 pF per node and per cone, 10 pF cone to cone). The cones' strays decide the swinging core's gain
    cost;
  - R_leak, CC and C_core;
  - the bearing's contact (1 Ω);
  - the 50 mm spacing and the 2 kV/cm target.
- **[IR]:**
  - the wirings;
  - the cosine C(θ);
  - the clamp model (soft knee, 100 kΩ). The swing's ratio on big stacks leans on it;
  - E taken as V / d;
  - the grid's interpolation, bilinear in log C_max and log κ.
- **Not modelled:**
  - the field in the core: it needs the electrode geometry and a field solve;
  - corona at the cones' edges;
  - the bicone–AH coupling.
- **Not re-run with the HV on the rotor:**
  - the vacuum stack (`sim/bicone_drive.py`, `sim/rotor_parts_duty.py`) and its spark-gap dump. Its topology is the
    same, so its pump numbers carry over;
  - the solids and the shaft check (§7).
