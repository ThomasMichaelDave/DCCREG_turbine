# Parked: a diode-commutated, floating-rotor tube after US 3,013,201 (Goldie, HVEC, 1961)

Source: `reference/US3013201.pdf` (*Self-excited variable capacitance electrostatic generator*, C. H. Goldie, High Voltage
Engineering Corp., filed 31 May 1960, granted 12 Dec 1961, 4 claims) and `reference/US3013201-figs.png`.

## What the patent does (Figs. 3–4)

Each section (lower and upper) has:
- **a floating rotor 11**, a fan with no connection at all;
- **two stationary sectors in the same plane**: the charging (induction) electrode 13 (S1) and the stator / collector 12
  (S2). The rotor bridges both at once, so it is only a *capacitive link* between them, with no brush or slip ring.

**Two circuits on the one stator electrode, alternating automatically:**
- **Charge.** As the rotor covers 13 and 12, the link capacitance rises. Charge of the opposite sign to 13 is drawn from
  ground into 12 through rectifier 16 (D1).
- **Dump.** As the rotor uncovers them, the capacitance falls and the stator's potential rises. Rectifier 16 blocks, and
  the charge goes to the load through rectifier 17 (D2).

No timing is involved: the diodes switch on voltage alone.

**Two sections, opposite polarity, cross-fed.** A fraction of each section's load voltage (potentiometers 19 / 20) drives
the *other* section's induction plate:
- the loop regenerates, the same principle as the Bennet / Kelvin cross-coupling;
- it starts from a contact potential or a small battery 21;
- the feedback ratio sets voltage and power;
- corona tubes 22 limit the voltage;
- the two outputs add in series across the load (±V).

## Mapping onto the tube [IR]

| patent | tube machine |
|:--|:--|
| induction electrode 13 + collector 12, same plane | split each **stator** vane into interleaved induction and collector sectors (two stator nets per varicap) |
| floating rotor 11 | the **rotor vanes float**: no rotor rails R-A / R-B, no rotor wiring |
| rectifiers 16 / 17 | HV diode stacks (≥ 25 kV) on the stator, replacing SG1–SG4 and BS3 / BS4 |
| potentiometers 19 / 20 | the cross-feed divider (capacitive, to avoid resistive loss) |
| sections A / B | the existing A / B halves of the tube, in opposite polarity |
| corona tubes 22 | the voltage cap: breakdown control by the feedback ratio |

**What it removes:**
- the rotor-to-stator contacts SG1 / SG2;
- the clocking decks (142 mm per side) and the ±2° timing budget;
- the rotor rails, the shaft sleeve's conductors, and the hub's circuit role. The rotor carries no circuit, so the
  quadricone hub and resonator have no job in this variant: a real departure.

**What it costs:**
- the link is two gaps in series (C/4 per varicap);
- HV diodes, whose capacitance adds to C_min and whose leakage adds loss;
- the output leaves the stator, so the stator should be frame-fixed (belt on the rotor only) or carry HV slip rings.

## First-pass budget (ideal diodes; tube C1 1114 / 71 pF per side, stray 28 pF, 20 kV, 300 rpm = 30 cycles/s) [RH]

Charge to the load per cycle per section: Q = (C_link,max − C_link,min)·k·V − (C_link,min + C_s)·V.

| rotor stray | C_link max / min | self-excites for | k 0.5 | k 1.0 |
|:--|:--|:--|:--|:--|
| 0 | 278 / 17.8 pF | k > 0.18 | 1.0 W per section | 2.6 W per section |
| 50 pF | 267 / 10.5 pF | k > 0.15 | 1.1 W | 2.6 W |

Two sections at k 1 give about 5.2 W into the load at 20 kV, against the Bennet tube's 1.3 W surplus (2.5 W belt, 1.15 W
lost in gaps, rings and relaxation). The reasons:
- an ideal diode switches at zero voltage across it, so there is no spark or ring loss;
- each section is a full two-stroke pump.

That is an upper bound. Real HV diode leakage, the divider, corona and the series-link strays all come off it.

## First gates

1. **G-GOLDIE-NET.** A section net in `rt_engine`:
   - induction, rotor and collector nodes, with C(θ) from the tube cell;
   - the diodes as `rect` gaps (the engine's valve model);
   - a capacitive cross-feed divider.

   Check z > 1 and that the ledger closes.
2. **G-GOLDIE-LOAD.** Output power at the 20 kV cap, swept over the feedback ratio k, with diode leakage.
3. **G-GOLDIE-GEOM.** Interleaved induction and collector stator sectors in the vane cell (2-D solve), and their mutual
   stray.
