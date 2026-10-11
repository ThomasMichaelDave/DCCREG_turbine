# The multiplier as laid out, running — findings

**Source:** `sim/multiplier_waveforms.py` → `sim/multiplier_waveforms_results.json` (three ngspice runs, about a
minute). The 3-D viewer plays it on the parts: `tools/step-viewer/layout.html`, its data built by
`tools/step-viewer/make_layout_data.py` (the "DCCREG Wound Tube" artifact).

**What it runs:** the layout study's own deck (`sim/multiplier_layout.py` run_deck: `sim/integrated_multiplier.py`'s
proposal as built, ideal diodes, C1 / C2 in phase) at the layout's picks (`sim/multiplier_layout_results.json`
strays):
- C3–C6 180 pF, the layout's strays on the new nodes and on nodes 1–4;
- the clamp strings of 60 parts (V_op 11.94 kV);
- from the consistent 1 kV seed, 537 cycles.

Two records come out of it:
- **the start-up:** every node's mean, minimum and maximum, cycle by cycle;
- **the steady cycle:** the last cycle written again at every solver step, every node's voltage, and from them each
  diode's current (§1).

**Status:** the record of the PROPOSED layout's circuit (`sim/multiplier-layout-findings.md`); no decision rides on it.
**Tags:** [OC] the deck's arithmetic and Kirchhoff's law; [IR] the deck's modelling (ideal diodes, as the study);
[RH] its inputs, the layout's strays.

## Headline
- **The rings:**
  - ±14.769 kV, the layout study's run exactly (G1);
  - 11.8 V of ripple a cycle;
  - the field at the null 7.50 kV/cm with the can (× 0.9973, `sim/multiplier_layout_results.json` hub).
- **The start-up** [ideal diodes]: from the 1 kV seed the rings reach 95 % at cycle 146 (1.22 s) and are settled by
  cycle 537 (4.5 s).
- **The charge:**
  - each chain passes 208.5 nC a cycle (25.0 µA);
  - its clamp takes 207.2 nC of that (24.9 µA);
  - its ring stage takes 1.27 nC (0.15 µA), the ring's leakage through its 100 GΩ.
- **The cycle's order** (relative rotation 0–60°; at 0° the vanes are aligned, C1 = C2 = C_max; at 30° C_min). Each
  pair is mirrored, side A's and side B's at the same angles:

| relative rotation | what conducts | what it does |
|:--|:--|:--|
| 10.5–22.8° | D5 / D6 | the ladder's middle diodes: r2 → l1, r1 → l2 |
| 22.7–26.3° | D1 / D2 | the doubler's base: node 2 (3) to the shaft |
| 25.2–30.2° | Z1 / Z4 | the clamps, as nodes 1 / 4 swing to ±11.94 kV near C_min |
| 25.3–26.5° | D9 / D11 | the ring stages' first diodes |
| 39.7–40.0° | D10 / D12 | the ring stages' second diodes, into the rings |
| 39.8–59.7° | D3 / D4 | the ladder's first diodes: 2 → r1, l1 → 3 |
| 41.2–59.8° | D7 / D8 | the ladder's last diodes: l2 → 4, 1 → r2 |

- **The reverse peaks:** 3.37–6.11 kV per diode, each within one 20 kV stick (the record's ×2 rule, as the study).

## 1. How the diodes' currents are read [OC]
- **An ideal diode's own current cannot be read.**
  - The deck's diode (n 0.005) turns on within one solver step, overshooting by about 2.7 mV.
  - Its current at that step reads 1–2 A, while the nodes move a fraction of a volt. In the Gear method a step's
    current is not the charge the step moved.
  - A 0 V source in series to measure it stops the solver at once (D12's branch, 7 ns in).
- **Kirchhoff's law instead:**
  - each chain is one path of diodes from the shaft to its ring: 0 → D1 → 2 → D3 → r1 → D6 → l2 → D7 → 4 → D9 → xb
    → D10 → eb, and its mirror;
  - working in from the ring, each diode passes what the nodes beyond it took up in each 1° bin (C ΔV for every
    capacitor of the netlist, C(t) V for the varicaps, the rings' leakage), plus the clamp at its varicap node;
  - the node voltages are smooth, so the bins' charges are exact sums of C ΔV.
- **The checks it must pass:**
  - no diode conducts backwards: worst 0.75 % of its peak;
  - none conducts while reverse biased by 50 V or more: worst 1.3 %;
  - both worst values come from the small ring stages, where the bins' C ΔV terms nearly cancel.

## 2. The steady cycle
| part | from → to | nC a cycle | µA | peak (1° bins), mA | conducts, deg | reverse peak, kV |
|:--|:--|--:|--:|--:|:--|--:|
| D1 / D2 | 0 → 2 / 3 → 0 | 208.48 | 25.02 | 0.612 | 22.7–26.3 | 4.11 |
| D3 / D4 | 2 → r1 / l1 → 3 | 208.50 | 25.02 | 0.229 | 39.8–59.7 | 5.86 |
| D5 / D6 | r2 → l1 / r1 → l2 | 208.50 | 25.02 | 0.146 | 10.5–22.8 | 5.71 |
| D7 / D8 | l2 → 4 / 1 → r2 | 208.49 | 25.02 | 0.140 | 41.2–59.8 | 6.11 |
| D9 / D11 | 4 → xb / xa → 1 | 1.27 | 0.153 | 0.018 | 25.3–26.5 | 6.10 |
| D10 / D12 | xb → eb / ea → xa | 1.29 | 0.155 | 0.033 | 39.7–40.0 | 3.37 |
| Z1 / Z4 | the clamps | 207.24 | 24.87 | 0.516 | 25.2–30.2 | — |

- **The nodes' swings** (side A; side B the same with the sign flipped, within 0.07 V):

| node | kV, min / max |
|:--|:--|
| 1 | −11.99 / −6.45 |
| 2 | 0.00 / +4.11 |
| l1 | −5.86 / −2.99 |
| r1 | +2.99 / +5.86 |
| r2 | −8.70 / −5.29 |
| xa | −14.77 / −11.40 |
| ea (ring A) | −14.78 / −14.76 |

- **The counter-rotor** (s) stays within 0.1 µV of REF through the reference link.

## 3. The start-up
- From the 1 kV seed, nodes 1 / 4 grow by the free gain (z 1.0164, `sim/multiplier_layout_results.json` strays) until
  the clamps catch them. The rings follow through their stages: 95 % at cycle 146, settled by 537.
- At the run's end the rings still creep up: each ring stage passes 4.5–4.7 % more than its ring's leakage (1.23 nC a
  cycle), the charge its capacitors still take up. That is within the study's settled rule (0.1 % over 50 cycles).

## Gates
| gate | result | pass |
|:--|:--|:--|
| G1 the rings as the layout study's "clamps of 60" run | −14.769 / +14.769 kV, as `sim/multiplier_layout_results.json`; the last cycle alone −14.770 / +14.770 | ✔ |
| G2 the charge balance | chains 1 and 2 to 0.011 %; nodes 1 / 4 (the clamp plus the ring stage) to 0.009 %; the ring stages D9 = D10, D11 = D12 to 1.6 %; no backward conduction (0.75 %), none while reverse biased (1.3 %) | ✔ |
| G3 twice the steps | the rings within 0.3 V; no device's charge moves more than 0.03 % of the chain's | ✔ |

## Caveats
- **Ideal diodes,** as the layout study. The real sticks' start-up is `sim/integrated-multiplier-findings.md`'s, and
  the layout only improves it (z 1.0164 against 1.0142).
- **The strays are estimates** [RH]. The levels rest on them; the bench trims the clamp strings.
- **The viewer's time is slowed:** a cycle lasts 1/120 s; the page shows it over 6 s (720×). The start-up plays each
  node's mean per cycle, not its swing within the cycle.
