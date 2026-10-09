# The rotor's parts, first cut: La / Lb, the ratings, the start kick, creepage and potting — findings

**Source:** `sim/parts_first_cut.py` → `sim/parts_first_cut_results.json` (about 20 minutes with 4 processes on an idle machine; ngspice).

**Status:** first cuts [IR / RH]. Every part here stays PROPOSED until the designer accepts it; the ledger lists them
for the designer to decide (`docs/ledger/DCCREG-design-ledger.md` §5.1–§5.2). No netlist or record of the design was
changed.

**What it runs:**
- **The magnetic dual doubler** at the pick (g 0.5 / 6 bridges / 1200 rpm relative), exactly as
  `sim/rotor_parts_duty.py` runs it: the deck of `sim/magnetic_doubler.py`, with the Ψs and the group of
  `sim/pole_design_variants_op.json`. 152 runs:
  - the duties, without and with the 22 mF AH bypass of `sim/ah_steady_cusp.py` (C + 10 mΩ);
  - the seed of `sim/pole_design.py` (a current frac · Ψs / L_max in every coil): its threshold, and its other sign;
  - seven kick circuits across La, each at four rotor phases, and a sweep of the kick's energy;
  - the diodes' forward drop: the record's, a 1N540x-class silicon rectifier, Schottky parts;
  - the chosen kick below full speed, and whether a running pump holds as it slows (the same parts on a stretched
    cycle);
  - La / Lb at their own τ = L / R.
- **The electrostatic pump** with the rings' symmetric supply, exactly as `sim/hub_rings_build.py` runs
  `record_supply` (`sim/core_field.py` dc, 2 + 2 stages, 100 pF, 100 GΩ, 280 cycles):
  - every diode's and capacitor's duty, by KCL on the nodes [OC];
  - the clamps;
  - a vane flashover, by charge sharing between ideal parts [IR].
- **No circuit:** the chokes' sizing; the creepage and clearance tables.

**Cross-checks.** Both decks reproduce their records.

| quantity | here | the record | file |
|:--|--:|--:|:--|
| magnetic z_early | 1.1394 | 1.1394 | `sim/rotor_parts_duty_results.json` |
| AH peak / belt | 448.9 A-turns / 17.576 W | 448.9 / 17.576 W | 〃 |
| La | 0.869–1.146 A | 0.869–1.146 A | 〃 |
| D1*–D4* reverse, steady state | 112 / 101 / 43 / 45 V | 112 / 101 / 43 / 45 V | 〃 |
| with the bypass: z / belt / A-turns per coil | 1.1466 / 18.126 W / 290–308 | 1.1466 / 18.126 W / 290–308 | `sim/ah_steady_cusp_results.json` |
| electrostatic belt | 2.1438 W | 2.1438 W | `sim/hub_rings_build_results.json` record_supply |
| clamps, each | 1.070 W, 0.951 mA peak | 1.070 W, 0.951 mA | 〃 |
| D1 / D3 reverse | 6.12 / 13.18 kV | 6.12 / 13.18 kV | 〃 |
| the seed at 20 % of Ψs | 0.110 A, 3.48 mJ | 0.110 A, 3.48 mJ | `sim/pole_design_variants_op.json` (kick_I_A, kick_mJ) |

## Headline

### 1. La / Lb: a standard EI-84 with a 35 mm stack meets the modelled 0.29 Ω

| each choke | |
|:--|:--|
| core | scrapless EI-84 laminations: 84 × 70 mm, centre leg 28 mm, outer legs 14 mm, window 14 × 42 mm; stack 35 mm; non-oriented SiFe 0.5 mm, M400-50A class (M235-35A, the utrons' grade, roughly halves the iron loss) [IR] |
| winding | 150 turns of Ø1.40 mm grade-2 enamelled copper, 7 layers of 24 on a bobbin; 39 % of the window is copper [IR] |
| gap | 0.126 mm in all: E and I butted on a 0.063 mm non-magnetic spacer, or a 0.126 mm gap ground in the centre leg; trimmed on test to 0.146 H [IR] |
| inductance | 0.146 H. The iron is 31 % of the reluctance, so μ_r 1500–8000 [RH] moves L over 0.111–0.181 H at a fixed gap: hence the trim |
| peak flux density, with the DC | 1.20 T at the record's 1.147 A; 1.22 T at the 1.167 A of the bypassed pump. The knee (1.45 T [IR]) comes at 1.39 A, ×1.21 |
| ripple assumed | the record's 0.869–1.147 A at 120 Hz (±14 % about the middle, `sim/rotor_parts_duty_results.json`): 0.041 Wb-turns, 0.29 T p-p in this core |
| resistance | **0.276 Ω at 20 °C**, the model's basis (it has 0.292 Ω, τ 0.5 s, copper at 20 °C); 0.30 Ω at 41 °C in service [RH: a 40 °C rotor ambient] |
| losses | copper 0.33 W; iron about 0.2 W [RH] |
| mass, outline | 1.20 kg of iron + 0.34 kg of copper, about 1.66 kg with the bobbin and varnish [RH]; 84 × 70 × 59 mm |
| on the rotor | at r 80 mm: 32 g, 490 N per choke at 600 rpm; 50 g, 760 N in the 750 rpm spin test [OC]. Mount the pair 180° apart in one plane |

- **In the pump at its own τ (0.53 s), the pick is unchanged:** z 1.140, AH 450 A-turns, belt 17.60 W.
- **A compact alternative,** EI-66 with a 44 mm stack: 1.11 kg and 0.54 Ω (τ 0.27 s). Held at the same AH, it costs
  the belt 0.59 W more (18.13 W against 17.54 W) for 0.44 kg less per choke.

### 2. D1*–D4*: use Schottky rectifiers
- **The record's diode is optimistic for silicon.** The deck's model drops 0.54 V at 1 A (`sim/magnetic_doubler.py`
  nd 1); a 1N540x-class silicon rectifier drops about 0.85 V [IR datasheet-class].
- **With 1N540x-class parts in all four,** z falls 1.139 → 1.074 and the AH 449 → 423 A-turns (−6 %). The diodes take
  3.04 W instead of 2.01 W, and the kick must seed 25 % of Ψs instead of 16 %.
- **With Schottky parts** (200 V on D1* / D2*, 100–150 V on D3* / D4*) the pump is as modelled: z 1.142, AH 444,
  2.29 W in the diodes, a 16 % threshold.

### 3. The start kick: a capacitor dumped across La through an SCR, fired contactlessly at speed (PROPOSED)
- **The recommendation [IR]:** a 9 V lithium primary cell charges a 470 µF bipolar electrolytic through 10 kΩ.
  - At speed, an outside magnet closes a reed switch on the rotor, and the reed pulses an SCR's gate.
  - The SCR dumps the capacitor across La, + to node a: 19 mJ, 0.60 A peak, over 17 ms.
  - The SCR stops conducting when its dump ends, so each charge kicks once.
- **The evidence:** it starts the pump at all four rotor phases tried, with the record's diodes, with silicon
  rectifiers and with Schottky parts. The seed needs 2.2 mJ (16 % of Ψs); a fast dump needs about 8 mJ stored.
- **Fire it at full speed** (600 rpm each way), never below 500 [IR]. Below full speed the pump's gain falls:
  - with the record's diodes the kick starts it at every phase tried from 1000 rpm relative (500 each way), at one
    phase of two at 950, and not at 900, 800 or 400 (200 each way, the records' "above about 200 rpm");
  - Schottky parts start from 950; 1N540x-class rectifiers only at full speed (one phase of two at 1150).
  - A running pump holds down to about 800 rpm relative (205 A-turns) and stops by 700. After a slow-down, re-kick at
    full speed.
- **The polarity is the diodes', not the kick's.** A seed of the other sign starts the pump in the deck's own sign.
  The bypass never sees more than 1.3 mV the wrong way in any run, so polarised bypass parts go + to nodes d / b,
  whatever the kick does.
- **The alternative:** a 22 µF polypropylene film capacitor at 50 V (27.5 mJ, a 4.5 ms dump). It also starts at every
  phase with every diode set, but needs a 50 V source: a port at standstill, or a converter.

### 4. The ratings

| part | qty | duty (this study's runs; the worst case) | rating specified [IR] | margin |
|:--|--:|:--|:--|:--|
| La, Lb | 2 | 0.146 H; 0.87–1.15 A (1.05 A rms; 1.17 A peak with the bypass); ≤ 110 V; 96 mJ | EI-84 × 35 mm, 150 t of Ø1.40 mm grade 2, gap 0.126 mm (spacer 0.063 mm), R20 0.276 Ω | B 1.20 T (1.22 T); the knee at 1.39 A, ×1.21 |
| D1*, D2* | 2 | VR 113 / 104 V (start-up included); IF 0.81 A avg, 1.00 A rms, 1.90 A peak | Schottky, 200 V, ≥ 3 A (5 A preferred); or a 1N5404-class Si rectifier (400 V, 3 A, IFSM 200 A) at the cost in gain of §2 | VR ×1.8 (Schottky) / ×3.6; IF ×3.7 |
| D3*, D4* | 2 | VR 58 / 60 V (start-up; 47 / 48 V steady with the bypass); IF 1.07 A avg, 1.45 A rms, 2.27 A peak | Schottky, 150 V (100 V at least), ≥ 3 A (5 A preferred) | VR ×2.5 (×1.7 at 100 V); IF ×2.8 at 3 A |
| node snubbers (RC to REF) | 8 | C at ≤ 113 V, ≤ 1.7 V/µs; R ≤ 4.2 mW average, ≤ 0.30 W peak | 22 nF ±10 % polypropylene film, 250 V DC; 240 Ω, 0.5 W, pulse-rated, non-inductive | ×2.2 on V; ×118 on power |
| AH bypass (if used) | 2 | 22 mF; −0.54 … −0.44 V (nodes d / b positive); 0.63 A rms at 120 Hz; ≤ 1.3 mV the wrong way | 22 mF, 6.3–10 V aluminium electrolytic, 105 °C, ≥ 2 A rms at 120 Hz, ESR ≤ 20 mΩ; polarised, + to nodes d / b | ×12 on V; ×3.2 on ripple |
| start kick | 1 | the seed starts it from 16 % of Ψs (2.2 mJ); 25 % (5.4 mJ) with 1N540x-class diodes; at full speed | the K4 kick of §3 (470 µF bipolar, 25 V; 9 V lithium cell; SCR ≥ 400 V, ≥ 1 A; reed and magnet), fired at 600 rpm each way, never below 500 | ×2.4 on the 8 mJ a fast dump needs; ×1.2 in speed |
| D1, D2 | 2 | VR 6.12 kV; IF 81 µA avg, 0.96 mA peak, 0.21 mA rms | one 20 kV avalanche HV stick, 5 mA class, + a 22 kΩ surge resistor | VR ×3.3 (guidance ×2); IF ×62 |
| D3, D4 | 2 | VR 13.18 kV; IF 81 µA avg, 1.59 mA peak, 0.25 mA rms | two 20 kV sticks in series (or one 30 kV), + a 22 kΩ surge resistor | VR ×3.0 (×2.3); IF ×62 |
| surge resistors (D1–D4) | 4 | 1.4 mW normally; in a vane flashover ≤ 6.6 kV across, 0.30 A peak, 10.3 mJ, τ 10 µs | 22 kΩ ±5 %, ≥ 15 kV across the body, ≥ 1 W, ≥ 0.1 J single pulse | ×2.3 on V; ×10 on energy |
| chain-input resistors (added here) | 2 | in a flashover the chains' first diodes see 5.8 kV forward, otherwise limited only by the arc | the surge resistors' part, in series with Coa1 and with Co1 | 0.26 A peak; RC 2.2 µs |
| Z1, Z4 clamp strings | 2 | BV = V_op 13.13 kV; 1.07 W, 0.95 mA peak, 81 µA avg, 0.24 mA rms; on 14 % of each cycle | 66 × 200 V avalanche diodes: TVS of the 1.5KE200A class (190–210 V at 1 mA) or 5 W Zeners of the 1N5388B class; one lot, sorted, trimmed | 16 mW per part against ≥ 1.5 W, ×90 |
| chain diodes | 8 | VR 7.50 kV each; IF 0.15 µA avg (the rings' leakage), ≤ 0.053 mA peak | one 20 kV stick each, selected for IR ≤ 25 nA at 7.5 kV and 25 °C | VR ×2.7 |
| chain capacitors | 8 | DC 7.47–7.49 kV; Co1 13.22 kV, Coa1 5.71 kV; ≤ 25 V p-p, ≤ 3.4 µA rms | 100 pF ±10 %, 30 kV DC, HV ceramic class 1 (or PP / PTFE film); IR ≥ 1e11 Ω guaranteed; partial-discharge-free at 1.25 × | ×2.3 (Co1); ×4.0; ×5.3 (Coa1) |

### 5. Three findings beyond the brief
- **The seed's sign does not set the pump's** [OC, from the deck]. Seeds of the other sign (20, 25 and 30 % of Ψs)
  start the pump in the deck's own sign, with and without the bypass, and the bypass is never reverse-biased.
  `sim/ah-steady-cusp-findings.md` says the opposite (see the last section).
- **The magnetic pump starts only near full speed, and stops below about 750 rpm relative** [IR] (§3). The records'
  "kick above about 200 rpm" is the gear's bound, not the pump's: there the kick dies within 8 cycles.
- **A vane flashover on side B lifts ring B to 19.0 kV** [IR].
  - It happens when node 4 flashes to REF at its lowest point: 14.96 → 19.03 kV, +27 %, and the excess leaves only
    through the leakage.
  - That is above the bench's 1.25× hold-off (±18.7 kV, `docs/bench-test-rings.md`). Before the hub's DC settles, the
    polar bead's gel would run at about 6.3 kV/mm, against 5 kV/mm [RH]; settled, at about 2 kV/mm.
  - Ring A is discharged by the mirror event, not overcharged.
  - OPEN for the designer (§2.7).

## 1. La and Lb in detail

**The duty** (`sim/rotor_parts_duty_results.json` la_lb):
- 0.1458 H;
- 0.869–1.147 A at 120 Hz, 1.05 A rms;
- 110 V peak across La, 101 V across Lb;
- 96 mJ at the peak.

The bypassed pump (`sim/ah_steady_cusp.py`'s circuit, re-run here) carries 0.885–1.167 A. The whole start-up from the
record's seed never exceeds the steady peak.

**The method** [IR choices; `sim/parts_first_cut.py` choke()]:
- **The sizes:** the standard scrapless EI sizes (EI-66, 76, 84, 96, 105, 120), each at stacks of 1, 1.25, 1.5 and 2 ×
  the centre leg.
- **The turns:** the fewest that keep 1.20 T at the peak current: N = L I_pk / (B A_Fe), with a 0.95 stacking factor
  [OC].
- **The wire:** the largest IEC 60317 size whose grade-2 wire winds N turns in layers on the bobbin, with 5 % of the
  build to spare.
  - The bobbin: a 1.0 mm wall, 1.5 mm flanges and 1 mm to the outer leg.
  - Polyester between the layers; each layer's own mean turn.
- **The gap:** what gives L with McLyman's fringing factor and the iron at μ_r 3000 [RH].
- **R** at 20 °C (1.724e-8 Ω·m) and at the choke's temperature (+0.393 %/K) [OC].
  - The rotor's 40 °C ambient and 25 W/m²K are `sim/pole_design.py`'s T_AMB and H_AIR [RH].
- **The iron loss:** M400-50A's 4.0 W/kg at 1.5 T, 50 Hz, scaled (f / 50)^1.3 (B / 1.5)², × 1.5 for the DC bias and the
  non-sinusoidal ripple [RH].

**The lightest choke for each resistance** (from the table in the results):

| core × stack | turns, wire | R at 20 °C | τ | iron + copper | gap |
|:--|:--|--:|--:|--:|--:|
| EI-66 × 33 | 203 × Ø0.90 | 0.77 Ω | 0.19 s | 0.86 kg | 0.21 mm |
| EI-66 × 44 (compact) | 152 × Ø1.00 | 0.54 Ω | 0.27 s | 1.11 kg | 0.14 mm |
| EI-84 × 28 | 188 × Ø1.25 | 0.40 Ω | 0.37 s | 1.27 kg | 0.18 mm |
| **EI-84 × 35 (chosen)** | **150 × Ø1.40** | **0.276 Ω** | **0.53 s** | **1.54 kg** | **0.126 mm** |
| EI-84 × 42 | 125 × Ø1.60 | 0.19 Ω | 0.75 s | 1.85 kg | 0.095 mm |
| EI-96 × 32 | 144 × Ø1.70 | 0.19 Ω | 0.77 s | 1.94 kg | 0.11 mm |

- **The rule** [IR]: the lightest standard size with R at 20 °C ≤ the model's 0.292 Ω.
  - EI-84 × 35 meets it with 6 % to spare; EI-84 × 42 buys 30 % lower R for 0.31 kg more.
  - R falls roughly as the size⁻⁵, so a smaller core pays steeply in copper loss [OC: scaling at fixed L, I and B].
- **The record's first cut** (`sim/rotor_parts_duty_results.json` la_core: a 28 mm square leg, 179 turns, 0.21 mm gap,
  1.00 + 0.41 kg, 0.292 Ω):
  - it filled half the window with bare copper and had no bobbin;
  - the bobbin-wound EI-84 × 35 is its buildable form: 39 % copper, 0.13 kg heavier.
- **What R does to the pump** (ngspice, the pick):

| τ of La / Lb | Ψs held: z, AH, belt | AH restored to 449 A-turns: Ψs, belt, La + Lb copper |
|:--|:--|:--|
| 0.5 s (the model) | 1.139, 449, 17.58 W | — |
| **0.53 s (EI-84 × 35)** | **1.140, 450, 17.60 W** | **0.1334 Wb-t, 17.54 W, 0.62 W** |
| 0.27 s (EI-66 × 44) | 1.131, 436, 17.18 W | 0.1371 Wb-t, 18.13 W, 1.20 W |

- **The gap:**
  - 0.126 mm in all is small, so the spacer sets L to ±25 % against the iron's spread: trim it on test [IR];
  - butted E and I put the spacer in all three legs (two equal gaps in series);
  - the gap's pull is 531 N at the peak and 305 N at the minimum, a 226 N pulsation at 120 Hz [OC]. Bond the stack and
    the spacer (§5).
- **The iron loss:** about 0.21 W (M400-50A) or 0.12 W (M235-35A), against 0.33 W of copper [RH]. That is small, but
  not negligible as `sim/rotor-parts-duty-findings.md` §1 has it.
- **The heat:** 0.54 W off 270 cm² is under 1 K of rise. The copper sits at the rotor's ambient [RH].
- **On the rotor:**
  - at 600 rpm, a choke at r 50 / 80 / 110 mm sees 20 / 32 / 44 g and pulls 300 / 490 / 670 N [OC];
  - at the 750 rpm of the spin test (`sim/rotor-mechanics-findings.md` §2.1), × 1.56: 50 g and 760 N at r 80 mm;
  - alone at r 80 mm it would be 123 kg·mm of unbalance, so mount La and Lb 180° apart in one plane (statically and
    dynamically balanced) [OC];
  - brackets must not encircle a leg, or they make a shorted turn [OC];
  - the pair is 3.3 kg, about a quarter of the six utrons' 13.4 kg (`sim/pole-design-findings.md` §8), and 0.5 kg
    more than the 2.82 kg the rotor's mass budget carries for them (`sim/rotor-mechanics-findings.md` §1).
- **The winding's voltage:** ≤ 112 V. Turn to turn about 0.7 V and layer to layer about 40 V, which grade-2 enamel takes
  with a wide margin [OC/IR].
- **A C-core alternative** [RH]: grain-oriented cut cores at 1.5 T need 0.8 × the turns. At the same window that is
  0.64 × R, or the same R at about 0.77 × the mass. Not designed here.

## 2. The ratings, part by part

### 2.1 D1*–D4* (magnetic pump)
- **The duties** (the worse of the unbypassed and bypassed runs, start-up included):
  - D1* / D2*: VR 113 / 104 V; IF 0.81 A average, 1.00 A rms, 1.90 A peak;
  - D3* / D4*: VR 58 / 60 V; IF 1.07 A average, 1.45 A rms, 2.27 A peak.
- **Two refinements of the record:**
  - the 2.8 A the record quotes is the branch's peak; each diode's own peak is 1.9 / 2.3 A;
  - D3* / D4* reach 57–60 V during start-up, against the steady 43 / 45 V (47 / 48 V with the bypass).
- **The forward drop decides** (§Headline 2):

| D1*, D2* / D3*, D4* | z_early | AH peak | in the diodes | kick threshold |
|:--|--:|--:|--:|--:|
| the record's 0.54 V / 0.54 V | 1.139 | 449 | 2.01 W | 16 % |
| 1N540x-class Si 0.85 V / Si 0.85 V | 1.074 | 423 | 3.04 W | 25 % |
| Si 0.85 V / Schottky 0.50 V | 1.135 | 440 | 2.49 W | 20 % |
| **Schottky 0.70 V / 0.50 V** | **1.142** | **444** | **2.29 W** | **16 %** |

- **The diode models** [IR datasheet-class fits at 1 A and 3 A, 25 °C]:
  - silicon 0.85 / 0.95 V;
  - a 100 V Schottky 0.50 / 0.65 V;
  - a 200 V Schottky 0.70 / 0.85 V.
  - All are without recovery charge. A standard rectifier's few µs of recovery are small at 120 Hz against the
    inductive commutation that the snubbers damp [RH].
- **The rating [IR]:**
  - D1* / D2*: a 200 V Schottky (×1.8 on VR);
  - D3* / D4*: 150 V (×2.5), or 100 V at least (×1.7);
  - all ≥ 3 A average (5 A preferred, for the heat).
  - A 1N5404-class rectifier (VRRM 400 V, IF(AV) 3 A, IFSM 200 A, VF ≤ 1.2 V at 3 A [IR datasheet-class]) holds every
    duty, but costs the gain shown.
- **Heat:** 0.44–0.59 W per diode. On copper pads or small heatsinks a 5 A part stays well inside its rating [RH].
  Schottky leakage rises with temperature, but at ≤ 113 V it costs milliwatts [RH].

### 2.2 D1–D4 and their surge resistors (electrostatic pump)
- **The duties** (`record_supply` re-run):
  - D1 / D2: VR 6.12 kV, D3 / D4: 13.18 kV;
  - each carries 81 µA on average (the clamps' DC, which circulates through the pump), 0.9–1.6 mA peak and 0.21–0.25 mA
    rms.
- **The rating:** the guidance ×2 rated HV sticks (`docs/ledger/DCCREG-design-ledger.md` §3.4) [IR]:
  - D1 / D2 need ≥ 12.2 kV: one 20 kV stick (×3.3);
  - D3 / D4 need ≥ 26.4 kV: two 20 kV sticks in series (×3.0) or one 30 kV stick (×2.3).
  - The 2CL77 class named in `sim/diode-stack-findings.md` (20 kV, 5 mA, IR 2 µA at 25 °C, avalanche) is what that
    file records [IR datasheet-class].
  - Use avalanche parts from one lot and no grading resistors, as `sim/diode-stack-findings.md` says.
- **Leakage:** at the 2 µA maximum spec the four would take at most about 80 mW (3.6 % of the 2.14 W). At a third of
  the rating it is tens of nA [RH].
- **The surge resistors** (`sim/diode-stack-findings.md`: 10–47 kΩ per position): 22 kΩ [IR].
  - **Normally** they dissipate 1.4 mW (0.25 mA rms), and their RC with Ca is 10 µs against the 8.3 ms cycle.
  - **In a vane flashover** (§2.7) D1 / D2 see a 6.6 kV forward step. The resistor holds it to 0.30 A peak, takes
    10.3 mJ and passes 4.7e-7 A²s, against 25–47 A without it (`sim/electrostatic-no-clamp-findings.md`).
  - **The part:** 22 kΩ ±5 %, ≥ 15 kV across the body, ≥ 1 W, ≥ 0.1 J in one pulse. For example an HV thick-film
    resistor, or six 3.9 kΩ, 0.5 W metal-glaze parts of ≥ 2.5 kV each in series [IR datasheet-class].
- **Two more, at the chains' inputs (added here) [IR]:**
  - the same flashover puts 5.7–5.8 kV forward across Dca1 / Dca2 (side A) or Dp1 / Dp2 (side B), limited only by the
    arc and the wiring;
  - 22 kΩ in series with Coa1 and with Co1 holds them to 0.26 A;
  - the RC with 100 pF is 2.2 µs, so the chains do not see it at 120 Hz.

### 2.3 The chains: 8 diodes and 8 capacitors
- **The diodes:**
  - each holds 7.47–7.50 kV reverse;
  - each carries the ring's leakage, 0.15 µA on average (15 kV / 100 GΩ), in pulses of ≤ 0.053 mA.
  - One 20 kV stick each (×2.7) [IR].
  - **Select for leakage:** IR ≤ 25 nA at 7.5 kV and 25 °C is 3e11 Ω per diode, the leakage ledger's figure per stage
    (`sim/hub-rings-build-findings.md` §3).
  - Silicon leakage roughly doubles every 10 K [RH]. At the hub's 32–43 °C (`sim/hub-thermal-findings.md`) that is
    ×2–3, so the bench's phase 2 should measure it warm.
- **The capacitors:**
  - DC 7.47–7.49 kV, except Co1 at 13.22 kV and Coa1 at 5.71 kV;
  - ripple ≤ 25 V p-p and ≤ 3.4 µA rms, so their losses are nil.
  - 100 pF ±10 % / 30 kV (`docs/rings-design.md` §4): ×2.3 on Co1, ×4.0 on the rest.
  - **Class 1 HV ceramic (N750–N4700) or PP / PTFE film** [IR]. Class 2 ceramics lose some capacitance under DC and are
    piezoelectric on a vibrating rotor: second choice.
  - **Insulation:** ≥ 1e11 Ω guaranteed, and measured ≥ 1e12 Ω at the working voltage. That meets the ledger's 5e11 Ω
    per stage.
  - **Partial discharge:** free at 1.25 × (16.5 kV for Co1) [IR].

### 2.4 The clamp strings Z1 / Z4
- **The duty** (each):
  - it breaks down at V_op 13.13 kV (`sim/core_field_results.json` design);
  - it takes 1.07 W: 0.95 mA peak, 81 µA average, 0.24 mA rms, conducting 14 % of each cycle, 8.9 mJ per cycle.
- **The string:** 66 × 200 V = 13.2 kV nominal (the ledger's first cut).
  - ±5 % parts give 12.54–13.86 kV at worst; a random lot gives ±47 V (σ, 0.36 %) [IR].
  - Sort the parts by VBR at 1 mA and trim the string with whole parts. Each 200 V part is a 1.5 % step; a lower-voltage
    part at the REF end sets the rest.
- **Temperature:** high-voltage avalanche parts drift about +0.1 %/K [IR datasheet-class], so the string moves
  +13 V/K. A 25 K rise lifts V_op 0.33 kV (2.5 %).
  - That takes the 6 mm gap's 1.5 margin to 1.46.
  - It takes the rims' corona margin on a handled surface from ×1.07 to ×1.04 (`sim/air-stack-sizing-findings.md`
    §6.5).
  - So trim the string warm, at its working temperature [IR].
- **The part** [IR datasheet-class]:
  - **preferred:** a TVS of the 1.5KE200A class. VBR 190–210 V is specified at IT 1 mA, the clamp's own current; it
    takes 1.5 kW for a 10/1000 µs pulse and 6.5 W steady at a 75 °C lead;
  - **or** a 5 W Zener of the 1N5388B class: 190–210 V at 5 mA, Zzt 480 Ω.
- **Per part:** 16 mW average and 0.19 W at the peak (×90 under 1.5 W).
  - A series string carries one current, so there is no sharing problem.
  - Below breakdown the avalanche parts take any imbalance without grading [OC/IR].
- **Capacitance:** the string's junctions in series (C_j / 66) add to the node's 20 pF stray. About 1–2 pF costs
  0.003–0.006 of z, at 0.003 per pF (`sim/core-field-findings.md` §4) [RH: the junction capacitance].
- **Build:** a meander in a silicone-potted module, its HV end and its REF end at opposite ends (§4).

### 2.5 The node snubbers (8)
- **The duty:**
  - the capacitors see ≤ 113 V and ≤ 1.7 V/µs;
  - each resistor takes ≤ 4.2 mW on average (1.1–3.9 mW by node) and ≤ 0.30 W at its peak.
- **The rating:**
  - 22 nF ±10 % polypropylene film at 250 V DC (×2.2), pulse-rated;
  - 240 Ω (E24; the model has 243 Ω), 0.5 W, pulse-rated thick-film or carbon composition, non-inductive (×118).
- **What they are:** the deck's frequency-scaled damping (`sim/magnetic_doubler.py` snub "scaled", from 10 nF and
  1 kΩ at 60 Hz) [IR]. On the bench, tune them to the real winding capacitance and the diodes' recovery.

### 2.6 The AH bypass (if used; PROPOSED in `sim/ah-steady-cusp-findings.md`)
- **The duty at 22 mF:**
  - −0.54 … −0.44 V across it, nodes d / b positive;
  - 0.63 A rms at 120 Hz (the record's 0.645 A also counts the snubber's current at x1);
  - 7.9 mW for the pair at the 10 mΩ ESR [RH];
  - at most 1.3 mV the wrong way in any run: start-ups, the reversed seeds and every kick.
- **The rating** [IR datasheet-class]:
  - 22 mF, 6.3–10 V aluminium electrolytic at 105 °C (×12 on voltage);
  - ≥ 2 A rms at 120 Hz (×3.2);
  - ESR ≤ 20 mΩ.
- **Polarised parts are fine,** + to nodes d / b. The diodes set that sign, whatever the kick (§3).
- **Mounting:** beside the hub, clamped against 20–40 g [RH].

### 2.7 A vane flashover
- **The event** [IR]:
  - a pumping node flashes to REF at its lowest point, the worst instant;
  - the arc holds it there while the rest of the network settles through ideal diodes;
  - charge is conserved, and each diode's equalisation dissipates ½ dq V_f [OC].
- **What it does:**

| flashover | the pump's diodes | the chain's first diodes | the rings after |
|:--|:--|:--|:--|
| node 1 to REF | D1: 6.6 kV forward step, 3.1 µC, 10.3 mJ; D3: 0.3 kV | Dca1 / Dca2: 5.7 kV, 0.4 / 0.2 µC | ring A −14.98 → **−13.20 kV**; ring B unchanged |
| node 4 to REF | D2: 6.6 kV, 3.1 µC, 10.3 mJ; D4: 0.3 kV | Dp1 / Dp2: 5.7–5.8 kV, 0.15 µC | **ring B +14.96 → +19.03 kV**; b1 7.49 → 10.26 kV |

- **Why only ring B rises** [OC]:
  - a flashover can only pull a node toward REF;
  - node 4 rising by 13.2 kV is one oversized upward swing, which ring B's positive chain collects;
  - node 1 rising empties ring A's negative chain instead.
- **The excess on ring B stays** until the leakage drains it, seconds to tens of seconds [RH].
  - At 19.0 kV it is 2 % above the bench's ±18.7 kV hold-off (`docs/bench-test-rings.md`).
  - **Before the hub's DC settles** (as at switch-on), the polar bead's gel field scales to about 6.2–6.3 kV/mm, from
    4.85–4.98 kV/mm at 15 kV (`docs/rings-design.md` §2) [IR: linear], against the 5 kV/mm design rating [RH]. The
    polar bead sits 0.4 % under its rating at switch-on (`sim/hub-beads-settled-findings.md`), so any lift exceeds it.
  - **Settled** (25 °C), the gel at the beads is at 0.69 kV/mm (polar) and 1.88 kV/mm (equatorial). The flashover's
    fast 4.1 kV step would add its capacitive share, about 1.35 and 1.2 kV/mm: about 2.0 and 3.1 kV/mm [IR:
    superposition, the step's share scaled from the switch-on field]. With the glass at 40 °C the equatorial bead is
    already at 6.15 kV/mm settled (the record's condition on σ_glass / σ_gel), and the step would take it to about
    7.4.
  - The chain's parts stay within their ratings: ≤ 10.3 kV on a 30 kV capacitor, and the diodes under 20 kV.
- **OPEN for the designer.** Options [RH]:
  - qualify the rings to ±20 kV (1.33×) on the bench;
  - or limit ring B, for example with a spark gap set near 17 kV, which leaks nothing until it fires;
  - or rely on the vanes' 1.5 margin to keep flashovers rare.

## 3. The start kick

**What the record seeds** [OC]:
- `sim/pole_design.py` run_real starts L1, L2, the AH pair, La and Lb at i0 = frac · Ψs / L_max (the deck of
  `sim/magnetic_doubler.py`).
- At the record's 20 % that is 0.110 A in each and 3.48 mJ of co-energy (L1 alone 1.51 mJ;
  `sim/pole_design_variants_op.json` kick_mJ, kick_mJ_L1).
- So "1.5–3.5 mJ seeded" is L1 alone up to all six coils. The old basis, ½ L_group (frac · I_pk)², gave about 38 mJ
  (`docs/ledger/DCCREG-design-ledger.md` §6, #7).

**The threshold, refined** (the start criterion of `sim/pole_design.py` size_op: 225 A-turns within 40 cycles):

| case | does not start | starts | seeded at the threshold |
|:--|--:|--:|--:|
| the record's diodes, without / with the bypass | 14 % | **16 %** | 2.2 mJ |
| 1N540x-class Si in all four | 20 % | 25 % | 5.4 mJ |
| Si D1* / D2*, Schottky D3* / D4* | — | 20 % | 3.5 mJ |
| Schottky in all four | 14 % | 16 % | 2.2 mJ |

- **Which coils need it:**
  - a seed in loop A alone (L1, the A coil of the AH, La) starts it; in loop B alone it does not;
  - in La and Lb alone it does (at 30 %).
  - So a kick into La's loop is enough.
- **It must fire at speed** [OC]. The pump grows only while L(θ) swings. At standstill the loop's current decays with
  L / R ≈ 0.4 H / 2.3 Ω ≈ 0.17 s.
  - A push-button cannot be pressed on a turning rotor, so the trigger must be contactless.
  - "At speed" means at full speed: see below the kicks' table.

**Seven physical kicks** (`KICKS`) [IR]:
- **The circuit:** each kick sits across La, + to node a and − to REF. The SCR is a one-way switch ramped over 20 µs
  that stops at the end of its dump; the cells' switch closes for 20 ms.
- **The conditions:** the 22 mF bypass is fitted, and the kick comes 1, 1.25, 1.5 or 1.75 cycles into a run that
  starts at rest (θ = 0 has L1 aligned).

| kick | stored / delivered | dump | peak current | the capacitor after | starts (4 phases) | with Si / Si + Schottky / Schottky diodes |
|:--|--:|--:|--:|--:|:--|:--|
| K1: 10 µF film at 50 V | 12.5 mJ | 3.4 ms | 0.55 A | −27.7 V | 4 of 4 | — |
| K2: 22 µF film at 50 V | 27.5 mJ | 4.5 ms | 0.82 A | −27.0 V | 4 of 4 | 4 / 4 / 4 of 4 |
| K3: 100 µF at 25 V | 31.3 mJ | 8.5 ms | 0.85 A | −10.5 V | 4 of 4 | — |
| **K4: 470 µF at 9 V** | **19.0 mJ** | **17 ms** | **0.60 A** | **−2.4 V** | **4 of 4** | **4 / 4 / 4 of 4** |
| K5: 4.7 mF at 3.6 V | 30.5 mJ | 52 ms | 0.56 A | +0.16 V | 4 of 4 | **1** / 4 / 4 of 4 |
| K6: 3.6 V cell, 1 Ω, 20 ms | 20 mJ delivered | 20 ms | 0.53 A | — | 4 of 4 | — |
| K7: 9 V cell, 2 Ω, 20 ms | 139 mJ delivered | 20 ms | 1.44 A | — | 4 of 4 | — |

- **How much:**
  - a fast dump (10 µF) starts from 8 mJ at both phases tried, from 4.5 mJ at one of two, and not from 2 mJ;
  - 100 µF needs 11 mJ for both, 5 mJ for one;
  - so the source must store about 2–4 × the seeded 2.2 mJ, because the dump does not all land in the growing mode
    [IR].
- **The sign:**
  - + to node a, the deck's sign, is the one to build;
  - the other sign started K2 at one of its two phases, and then in the deck's sign;
  - into a and c at once (a diode-OR) started at both.
- **The bypass** never saw more than 1.3 mV the wrong way.
- **The kick's own capacitor swings negative** after a fast dump (an LC half-swing before the SCR stops), so it must
  be non-polar: film, or a bipolar electrolytic. Only K5 stays positive.

**Below full speed** (`speed` in the results) [IR]:
- **The runs:** the same parts on a stretched cycle (L(θ) fixed in angle; every L, R and snubber kept), the bypass
  fitted, 80 cycles. "Runs" means more than 50 A-turns in the AH coil over the last 4 cycles; a pump that dies is at
  about 0. The 1200 row is the runs above (40 cycles, 225 A-turns).
- **"Holds"** uses a seed of 60 % of Ψs in every coil, as a proxy for a running pump that slows down.

| rpm relative (each way) | K4, the record's diodes | K4, Schottky | K4, 1N540x Si | the record's 20 % seed | a running pump | AH, steady |
|--:|:--|:--|:--|:--|:--|--:|
| 1200 (600) | 4 of 4 | 4 of 4 | 4 of 4 | starts | runs | 308 A-turns |
| 1150 (575) | | | 1 of 2 | | | |
| 1100 (550) | 2 of 2 | | 0 of 2 | starts | | 288 |
| 1050 (525) | 2 of 2 | | 0 of 2 | | | 277 |
| 1000 (500) | 2 of 2 | 2 of 2 | | does not | | 266 |
| 950 (475) | 1 of 2 | 2 of 2 | | | | 253 |
| 900 (450) | 0 of 2 | | | | holds | 240 |
| 800 (400) | 0 of 2 | | | | holds | 205 |
| 700 (350) | | | | | stops | — |
| 600 (300) | | | | | stops | — |
| 400 (200) | 0 of 2: gone within 8 cycles | | | | | — |

- **Why** [OC]: the copper's loss per cycle grows as the cycle stretches (R T / L), and the diodes' fixed drop weighs
  more as the winding's EMF (∝ speed) falls. The record's own linear gain is 1.081 at 600 rpm relative against 1.208 at
  1200 (`sim/pole_design_variants.json` z_rpm).
- **So the kick is fired at full speed,** where every diode set starts at every phase. The margin is 17 % in speed with
  the record's diodes, 21 % with Schottky parts, and less than 50 rpm (4 %) with 1N540x-class rectifiers: one more
  reason for Schottky parts (§2.1).
- **The AH and the belt fall with speed** (bypassed): 308 A-turns at 1200, 266 and 13.5 W at 1000, 205 and 8.2 W at
  800 rpm relative.
- **A slow-down** below about 750 rpm relative (between 700 and 800) stops the pump; the K4 capacitor recharges in
  about 25 s (5 τ), so a re-kick at full speed is ready by then.

**The options** (no wire crosses to the counter-rotor; everything on the rotor):

| option | what it delivers | polarity | reliability and failure modes | verdict |
|:--|:--|:--|:--|:--|
| 1. capacitor + SCR, a reed and an outside magnet (K1–K5) | 12–31 mJ stored, 0.55–0.85 A peak, 3–52 ms | set by the wiring: + to node a | One shot per charge. A welded reed re-fires each recharge (a kick into the running loop); an open SCR or a flat cell gives no start (benign, visible); a shorted SCR lets the cell feed ≤ 1 mA (negligible) [RH] | **recommended (K4)** |
| 2. a cell with a timer (MOSFET one-shot, K6-like) | ~20 mJ, 0.5 A, 20 ms | set by the wiring | Simple energy, but electronics beside 13 kV on a rotor (upsets by discharges); a stuck-on switch drives amperes from the cell into the loop continuously [RH] | second choice |
| 3. a permanent-magnet bias on a bridge | a seed every passage: about 36 µWb per utron for 16 % of Ψs (a small ferrite block) [RH] | set by the magnet | Untested. It biases the neck's saturation and adds cogging and iron loss at every pass; it needs a nonlinear field study [RH] | not now |
| 4. remanence | ≲ 1–2 % of Ψs aligned, ~0 unaligned (SiFe Hc ~40 A/m over ~1 mm of gap) [RH] | the last run's | An order of magnitude short of the 16 % | no |
| 5. a pulse from the electrostatic side (the clamp's current charging a capacitor at its REF end, a breakover diode) | mJ every second or so, automatic | fixed | No cell, but it couples the pumps, depends on the clamps and on the electrostatic pump running, and keeps firing while running [RH] | not for the first build |
| 6. more utron turns, so it self-starts | — | — | ≥ 1000 turns, 59–94 W (`sim/pole-design-findings.md` §4) | no |

**The recommendation: K4** [IR, PROPOSED]:
- **The circuit:**
  - a 9 V lithium primary cell (LiMnO2 class, about 1.2 Ah);
  - a 10 kΩ charging resistor, so τ is 4.7 s;
  - a 470 µF, 25 V bipolar electrolytic;
  - an SCR of ≥ 400 V and ≥ 1 A from the capacitor's + to node a, and the capacitor's − to REF (La's other end);
  - an RC snubber across the SCR (about 100 Ω + 10 nF) against dV/dt triggering, and 1 kΩ from its gate to its cathode;
  - a short gate pulse (0.1 µF into the gate through 100 Ω) when a reed switch closes.
- **The SCR's voltage:** node a swings about ±110 V, so the SCR sees about −101 … +119 V: ×3.4 at 400 V.
- **The procedure:**
  1. at standstill, arm it: insert the cell or close a link;
  2. spin up to full speed, 600 rpm each way (never below 500);
  3. bring a magnet to the reed's track from outside the frame;
  4. the AH comes up within about 25 cycles (0.2 s), then withdraw the magnet.
- **Why:**
  - it is tested at all four phases with all three diode sets;
  - the voltages are low throughout;
  - it needs no charging port and no converter;
  - it kicks once per charge;
  - its worst failure feeds the loop ~1 mA.
- **The alternative:** K2, if a 50 V source is acceptable: 22 µF polypropylene film at 50 V, 1.4 × the energy and the
  fastest dump. A film capacitor keeps its charge for tens of minutes after a precharge at standstill [IR
  datasheet-class: IR × C ≥ 1e4 s].
- **Layout** [RH]:
  - put the reed where the cage carries no vanes and away from the bridges and utrons, so the magnet magnetises nothing;
  - the reed must not close under the 20–40 g of service at r 50–100 mm, or the 31–63 g of the 750 rpm spin test: mount
    it with its blades radial and pot it.

## 4. Creepage and clearance

**The method** (IEC 60664-1 style):
- **Creepage** comes from the long-term rms of the working voltage; for DC, its value [IR].
  - Pollution degree 2 (a lab machine in air: non-conductive pollution, occasional condensation) [IR].
  - Table F.4's PD2 values: 5.0 / 7.1 / 10.0 mm at 1 kV for material groups I / II / III. In the table they are
    proportional to the voltage from 250 V to 1 kV [IR: the table as recalled; check the edition in use].
  - **Above 1 kV they are taken proportional again** [RH: an extrapolation beyond the table].
  - **× 1.25 design margin** for DC on a rotor, whose field draws dust [RH].
  - Pollution degree 3, as a sensitivity: 12.5 / 14 / 16 mm per kV [IR at 1 kV; RH above].
- **Clearance:** Table F.2, case A (inhomogeneous field), at 1.5 × the DC peak, the record's own air margin
  [IR: the table as recalled; RH: the factor].
- **Solid insulation** in void-free potting: the peak over 2 kV/mm [RH].

**Material groups by CTI** (IEC 60112) [IR datasheet-class]:

| material | CTI | group | here |
|:--|:--|:--|:--|
| PTFE | ≥ 600 | I | standoffs, rods, lead insulation |
| silicone elastomer (a potted module's surface) | ≥ 600, typical | I | module surfaces |
| G10 / FR4 | 175–250, typical | IIIa | carriers, the sleeve, the coupler |
| PEEK, unfilled | 150 (Victrex 450G datasheet) | IIIb | the hub's retainer: the lowest CTI of the materials in use, so keep HV surface paths off it |
| glazed alumina / steatite | does not track | inorganic | creepage need not exceed the clearance (IEC 60664-1) |

**The interfaces** (the working voltages from the `record_supply` run):

| interface | U rms / peak | clearance | creepage, design: PTFE or silicone / G10 or PEEK | ribbed standoff: PTFE / G10 | solid |
|:--|:--|--:|:--|:--|--:|
| the Ca plates, node 1 ↔ node 2 (and Cb, 4 ↔ 3) | 6.41 / 7.45 kV | 13 mm | 40 / 80 mm | 21 mm + 2 ribs of 5 / 37 mm + 4 of 6 | 3.7 mm |
| node 1 / 4 metal ↔ REF (the vanes' rings, the Ca node-1 plates, Z1 / Z4's top, D3 / D4, Coa1 / Co1) | 9.05 / 13.23 kV | 25 mm | 57 / 113 mm | 33 + 3 × 5 / 49 + 6 × 6 mm | 6.6 mm |
| node 2 / 3 metal ↔ REF (the Ca node-2 plates, D1 / D2) | 3.27 / 6.12 kV | 10 mm | 20 / 41 mm | 18 + 1 × 5 / 18 + 2 × 6 mm | 3.1 mm |
| node 1 ↔ node 4 (only where side A meets side B) | 5.55 / 7.45 kV | 13 mm | 35 / 69 mm | 21 + 2 × 5 / 37 + 3 × 6 mm | 3.7 mm |
| a clamp string, end to end | 9.05 / 13.23 kV | 25 mm | 57 / 113 mm | as node 1 / 4 | 6.6 mm |
| one chain stage (its diode or capacitor) | 5.48 / 7.50 kV | 13 mm | 34 / 68 mm | 21 + 2 × 5 / 37 + 3 × 6 mm | 3.8 mm |
| Co1 (13.2 kV DC) | 13.22 / 13.23 kV | 25 mm | 83 / 165 mm | 41 + 5 × 5 / 73 + 8 × 6 mm | 6.6 mm |
| a ring's lead and its chain's top ↔ REF | 14.96 / 14.98 kV | 29 mm | 94 / 187 mm | 45 + 5 × 5 / 85 + 9 × 6 mm | 7.5 mm |
| ring A's lead ↔ ring B's lead | 29.9 / 30.0 kV | 67 mm | 187 / 374 mm | keep them apart | 15 mm |

- **The standard's own value** (without the 1.25) is 0.8 × the design column; at pollution degree 3 it is 2.0 × (group
  I) and 1.3 × (groups IIIa / IIIb) the standard's value.
- **A ribbed standoff's creepage** is its height plus twice the sum of its ribs' depths. Ribs wider than X = 1 mm
  count at PD2 [IR].
- **Inside a void-free potted module** there is no creepage: it is solid insulation. Use ≥ 8 mm of silicone over
  13.2 kV parts and ≥ 5 mm over 7.5 kV parts (the solid column with some margin) [RH].

**The Ca / Cb mounts** (the record: "their mounts need 5.7–7.5 kV of creepage and are not drawn"):
- **The constraint:**
  - adjacent plates differ by V_Ca: −5.70 … −7.45 kV, 6.41 kV rms (`record_supply`);
  - that needs 40 mm of creepage on PTFE or 80 mm on G10 / PEEK (design; 32 / 64 mm standard) and 13 mm of clearance;
  - the plates are 6 mm apart, so **no support may touch two adjacent plates**.
- **A first cut** [RH]:
  - **the node-1 plates** (and node 4's on side B) ride on the rotor vanes' own stack: conductive spacer rings at node 1
    on the G10 sleeve (r 20.5–50 mm), like the rotor vanes;
  - **the node-2 plates** (node 3's) hang on 3–6 insulating tie-rods near their outer rim, PTFE or G10 sleeved in PTFE,
    with node-2 spacers between them;
  - **the node-1 plates are notched** round the rods with ≥ 13 mm of clearance, the notches rounded like the rims;
  - **the rods anchor in an insulating end disc** on the rotor:
    - from a rod's foot to the nearest node-1 metal, ≥ 80 mm along G10 (≥ 40 mm on PTFE or a silicone-coated face). The
      disc's r 50–150 mm span gives about 100 mm, so add ribs only if the layout shortens it;
    - from the rods to REF parts, ≥ 41 mm on G10 (node 2 runs 0 … −6.1 kV).
- **The G10 sleeve's ends:** from node 1's rings to the shaft's REF metal, ≥ 113 mm of G10 surface or ≥ 57 mm of PTFE /
  silicone [RH]. Sheds, or a silicone sleeve over its end, shorten it. This adds to the bore's bonding of
  `sim/core-field-findings.md` §7.
- **The HV leads:**
  - PTFE- or silicone-insulated HV wire, rated ≥ 20 kV DC for the pump's nodes and ≥ 30 kV DC for the rings
    (`docs/rings-design.md` §3);
  - ring A's and ring B's leads each run on their own shaft half and never share a bare surface: 29.9 kV between them
    needs 187 mm even on PTFE.

## 5. Potting and impregnation (specification, first cut)

| item | process and material [IR] | why |
|:--|:--|:--|
| **utron coils** (6) | Vacuum-pressure impregnation (vacuum ≤ 1 mbar, then 3–6 bar) with a solventless class F (155 °C) or class H epoxy or polyesterimide resin. Grade-2 wire of thermal class ≥ 180. Bond the G10 slot cover in the same cycle (DCCREG-UTR-101). | The impregnation is load-bearing: each coil is a closed loop round its back iron (394 N at 600 rpm), and its slot side bows 0.7 µm as a bonded bundle against 0.30 mm as loose wires, with 0.1 mm to the slot cover (`sim/rotor-mechanics-findings.md` §2.2) [RH: the bundle's stiffness]. Bond the cheeks and their roots in the same cycle (§2.1 there). It also stops turn fretting under the 120 Hz forces and gives the heat a path. The coils run at 46 °C in air (63 °C in vacuum), far inside class F. If the section shares a vacuum, use a low-outgassing resin (ASTM E595: TML ≤ 1.0 %, CVCM ≤ 0.10 %) [IR datasheet-class]. |
| **La, Lb** (2) | Dip-and-bake or VPI in the same class F resin. Bond the EI stack and the gap spacer (polyester, Nomex or glass-epoxy film) into one block; clamp it with brackets that do not encircle a leg. | The gap's pull pulsates 305–531 N at 120 Hz (§1): unbonded, it hums, frets and creeps the gap, and L drifts. The winding sees 20–40 g. The voltage is ≤ 112 V, so there is no HV requirement [OC]. |
| **AH coils** (2), beside the glass in the PEEK retainer | Wind on the G10 former; vacuum-impregnate void-free with a low-viscosity class F epoxy; fully cure and post-cure **before** the coil goes into its seat. Finish the end that faces the vessel smooth and round (the AH-end proposal of `docs/rings-design.md` §2: corners ≥ 1.5 mm at REF, a conductive flange coat or an end ring). No metal or carbon fillers. | Each polar bead faces the coil's end across 5.4 mm of PEEK (`docs/rings-design.md` §2), so the coil's outer surface is an electrode in the rings' field: a void there discharges, and the bench's < 10 pC partial-discharge test (`docs/bench-test-rings.md`) would fail. The coils run at 41–43 °C with 1.2 W each (`sim/hub-thermal-findings.md`), so class F is ample. A metal end ring must be split: closed, it is a shorted turn that the AH's 120 Hz ripple drives (up to ~0.3 W without the bypass) [RH estimate]. Platinum-cured silicone gels are inhibited by amines, sulfur and tin, so test the gel's cure on the cured epoxy and the PEEK [IR]. Never pot against the glass: the gel takes up PEEK's 47 ppm/K against the glass's 3.3 (`sim/hub-rings-build-findings.md` §1). |
| **HV parts** (D1–D4, the surge and chain-input resistors, Z1 / Z4, the chains' diodes and capacitors, their leads) | Two-part addition-cure silicone elastomer (Shore A ~30–50), primed, degassed and vacuum-cast (≤ 5 mbar), void-free, in rigid housings (PBT, PPS or PTFE, or walled G10 trays) that take the centrifugal load. Cover ≥ 8 mm over 13.2 kV parts and ≥ 5 mm over 7.5 kV parts. Stress-relief boots where leads leave. Accept on < 10 pC at 1.25 × the working voltage. | Void-free potting is solid insulation, so no creepage inside. The silicone surface is group I (CTI ≥ 600) and hydrophobic. Its low modulus spares the sticks' glass passivation, the ceramic capacitors and the joints in thermal cycling; epoxy is rigid, cracks, and its voids discharge. Its ε of 2.7–3.0 (against epoxy's 3.5–4.5) keeps the node strays down, at 0.003 of z per pF (`sim/core-field-findings.md` §4) [IR datasheet-class]. Dry potted modules are what the leakage ledger assumes: 1e12 Ω against 1e10 humid (`sim/hub-rings-build-findings.md` §3). Make the housings smooth and axisymmetric, for the windage and the balance (`sim/rotor-mechanics-findings.md` §6), and balance the rotor after potting (`sim/core-field-findings.md` §7). |

## Caveats
- **[RH]:**
  - IEC 60664-1's values as recalled, their extrapolation above 1 kV, the ×1.25 for DC and the 1.5 on the clearance;
  - the iron's μ_r and loss in the chokes; the 40 °C rotor ambient and 25 W/m²K;
  - the 2 kV/mm in the potting;
  - the flashover's ideal charge sharing (no arc voltage, no losses, the worst instant);
  - the remanence and permanent-magnet estimates; the failure-mode judgements;
  - the snubbers' real values (the deck's are numerical damping).
- **[IR]:**
  - the datasheet-class values (1N5404, 1N5388B, 1.5KE200A, the 2CL77 class) and the diode models fitted to them;
  - the bobbin's geometry and the layer winding;
  - the diode currents attributed by KCL at nodes with two diodes;
  - the start criterion (225 A-turns within 40 cycles of a 40-cycle run); below full speed, "runs" (more than 50
    A-turns over the last 4 of 80 cycles), and the 60 % seed as a running pump's proxy;
  - the SCR as a 20 µs-ramped one-way switch that stops when its dump ends;
  - a run that stops early is repeated once with reltol 3e-5 and half the maxstep (the verdicts do not depend on it).
- **Not covered:**
  - the layout: no space was checked for the chokes, the HV modules or the kick;
  - the HV modules' heat (the clamps' 1.07 W each);
  - EMI on the kick's trigger;
  - a speed ramp: the deck runs at one speed, so the slow-down is a proxy;
  - the chokes' stray field at the hub;
  - the clamp string's junction capacitance (not in the deck).
- **The model's copper is at 20 °C throughout** (as the record's). In service all copper runs about 8–9 % higher at
  41 °C [OC].
- **`--cache FILE`** keeps the raw ngspice results between runs, to rework the analysis only. A plain run does
  everything.

## What contradicts or updates the records
Line numbers as of 2026-10-09; the ledger was being edited at the time.

- **`sim/ah-steady-cusp-findings.md`:64–65** (the winding sense and the bypass's polarity): "the kick must seed this
  sign, which is the deck's sign. Seeded the other way, the pump runs mirrored and reverse-biases them [OC]."
  - Here, seeds of the other sign at 20, 25 and 30 % of Ψs start the pump in the deck's own sign, with and without the
    bypass. The A coil carries −1.83 A (unbypassed) and −1.87 A (bypassed), as with the deck's seed, and the bypass
    never goes the wrong way by more than 1.3 mV in any run.
  - The diodes set the sign. So the kick's sign does not decide the bypass's parts: the ledger's "The kick source is
    OPEN, and so is its polarity if the bypass electrolytics are polarised" (`docs/ledger/DCCREG-design-ledger.md`
    :278–279, §3.2) and the cost sheet's "Bipolar parts if the kick polarity is free" (`docs/make_cost_sheet.py`
    :374–375) are settled: polarised parts, + to nodes d / b. Wire the kick + to node a all the same; the other sign
    started K2 at only one of its two phases.
- **`docs/ledger/DCCREG-design-ledger.md`:277** (§3.2) and **:590** (§4), and **`docs/drive-gear-belt.md`:223**
  (§4.2): "Kick above about 200 rpm, clear of the drive's 20 Hz gear mode"; "So kick the magnetic pump above about
  200 rpm [IR]."
  - 200 rpm each way (400 relative) clears the gear, but the pump does not start there: the K4 kick's current is gone
    within 8 cycles.
  - With the record's diodes it starts at every phase tried only from 1000 rpm relative (500 each way); with
    1N540x-class rectifiers only at full speed. Kick at full speed, 600 rpm each way (§3).
  - The ledger's 20 % seed itself starts from 1100 rpm relative, not from 1000.
- **`sim/rotor-parts-duty-findings.md`:35** (§1): "iron loss is negligible". It is about 0.12–0.21 W per choke [RH],
  against 0.33 W of copper: small, not negligible.
- **`docs/ledger/DCCREG-design-ledger.md`:283** (§3.2) and **:588** (§4): "D1*–D4*: silicon, 2.8 A peak, reverse
  112 / 101 / 43 / 45 V"; "Si, 0.55 V at 1 A".
  - The 2.8 A is the branch's; the diodes' own peaks are 1.9 A (D1* / D2*) and 2.3 A (D3* / D4*).
  - D3* / D4* reach 57–60 V during start-up; 43 / 45 V is the unbypassed steady state.
  - 0.55 V at 1 A (also :275, "With silicon diodes (0.55 V)") is a Schottky-class drop. A 1N540x-class silicon
    rectifier drops about 0.85 V and costs z 1.139 → 1.074 and the AH 449 → 423 A-turns (§2.1).
- **`sim/pole-design-findings.md`:96** (§4) and **`docs/make_cost_sheet.py`:370:** "a capacitor or battery with a
  push-button"; "Start-kick source (capacitor + push-button)". The kick must fire at speed, so a button on the rotor
  cannot be used; a contactless trigger is needed (§3).
- **`docs/ledger/DCCREG-design-ledger.md`:369–370** (§3.4): "Their mounts need 5.7–7.5 kV of creepage". Creepage is a
  length: that voltage needs 32–64 mm (PD2, the standard) or 40–80 mm (design), so no mount may bridge two adjacent
  plates (§4).
- **`docs/make_cost_sheet.py`:366:** "La / Lb gapped EI chokes (1.0 kg iron, 0.41 kg Cu)", and
  **`sim/rotor-mechanics-findings.md`:64** (§1): "La / Lb first cut 2.82 kg". This study's EI-84 × 35 is 1.20 kg of
  iron and 0.34 kg of copper per choke, 3.3 kg for the pair with bobbins and varnish.
- **New, not in any record:** a node-4 vane flashover lifts ring B to 19.0 kV, past the bench's ±18.7 kV
  (`docs/bench-test-rings.md`:81) (§2.7).
