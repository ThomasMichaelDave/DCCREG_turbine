# Cost sheet: the air build

**File:** `dccreg-air-build-cost-sheet.xlsx`.
- **Generator:** `docs/make_cost_sheet.py`. Recalculate after rebuilding, e.g. with LibreOffice, so the cached values
  are filled in.
- **What it costs:** every stack of the vane matrix (2700 designs, `sim/vane_matrix_results.json`), with formulas on
  the Inputs sheet.
- **The Optimum sheet** picks the cheapest design that meets the targets (or the lowest cost per watt) and lists the
  next ten. It also checks the AH's steady cusp.
- **BOM fixed** holds the parts that don't depend on the stack: the magnetic pump, the AH and its bypass, the hub and
  the mechanics.

**To use it:**
1. **Inputs:** edit the yellow cells (blue text), the targets first.
2. **BOM fixed:** edit the quantities and unit prices.
3. **Optimum:** read the result.

Every price is a placeholder for a one-off prototype in EUR [RH]; replace each with a quote.

## The core field: DC on the rings (the default), the pair inside, swinging or steady
Pick it on Inputs (core field). The electrostatic circuit's HV side is on the rotor (`sim/core-field-findings.md`).
- **4, DC on the rings (the default, the designer's choice):** two rings outside the hub's glass, as built: copper foil
  bands from 26.25° to 55.71° with beaded edges, under the gel and the PEEK retainer (`docs/rings-design.md`,
  `sim/hub-rings-build-findings.md`).
  - **The supply, by ring A's feed:**
    - **feed 2, the symmetric supply (as built, the default):** ring A on its own N_CW_A-stage Cockcroft-Walton chain
      from the shaft on node 1, the mirror of ring B's, so the null sits at the shaft's potential. No Dk, no C_A. Two
      stages a side as built.
    - **feed 1:** ring A on node 1's peak through Dk, with N_CW_A (0–2) negative stages stacked on it.
    - **ring B:** N_CW Cockcroft-Walton stages on node 4 (two as built).
  - **The core's voltage:** 1.067 × the floating swing's peak (AM) × the chains' outputs, plus V_op on feed 1.
    - **The output** is 1 / 1.989 / 2.948 / 3.846 / 4.649 / 5.328 for one to six stages. On feed 2 it applies to each
      ring; on feed 1, ring A adds 0.993 / 1.960 for one or two stages. The output carries the simulated sag at
      100 GΩ per ring.
    - **On the stack of record** that is 29.7 kV, against 29.9 kV simulated.
  - **The field at the null** is that voltage × 0.2373 (kV/cm)/kV, the rings as built's field per kV.
    - That figure belongs to the record's bands. Other stage counts need their own bands and figure
      (`sim/hub_rings_build_results.json` designs). On the symmetric supply: 0.2892 for 1 + 1, 0.1758 for 3 + 3
      (1 / 8 kV/mm), 0.2791 for 2 + 2 at 2 / 5, and 0.2311 for 4 + 4 (2 / 8).
  - **The pump keeps its clamped gain and power**, since the rings sit behind diodes.
  - **Inputs checks** that ring A's stage count fits its feed; no design qualifies when it does not.
- **3, the pair inside (not chosen):** two Rogowski electrodes in the vacuum on the AH null
  (`sim/core-null-field-findings.md`).
  - **The supply** is the same as 4.
  - **The field is capped** at the vacuum rule's 65.7 kV/cm at the null. Inputs says whether the target is within it.
  - **The spacing is the free gap** wanted at the null.
- **2, swinging:** the cones float, each coupled through 1 nF to node 1 / 4.
  - The core sees an AC field at the pump frequency, about 0.55 of the operating peak.
  - The cones' strays cost gain on small stacks.
  - Designs' AM–AO hold each design's swing, z and power, from ngspice (`sim/core_swing_grid.json`).
- **1, steady:** a core diode charges cone A to the operating peak and a 1 nF capacitor holds it; cone B sits on the
  shaft. The pump keeps its gain.

## The sweet spot at the placeholder prices

**The hub is the locked one** (`presets/hub-locked.json`): the vessel a 50 mm borosilicate sphere, two MnZn AH cores
on the z axis, the PEEK retainer (in every option; 120 + contingency, missing before).

**Targets, with the rings (the default):** the placeholders on Inputs.
- 6.5 kV/cm at the null, i.e. 27.4 kV across the rings, on the symmetric supply with two stages a side;
- at least 2 W from the electrostatic pump, z ≥ 1.3;
- at most 6 + 6 vanes, corona-safe rims;
- 300 steady A-turns at the AH.

**81 designs meet them:**

| objective | design | operating peak | across the rings | power | stack per side | stack cost | total |
|:--|:--|--:|--:|--:|--:|--:|--:|
| lowest total cost | 6 mm gaps, 2.5 mm vanes, r 175 mm, 22°, 4 + 4 | 13.1 kV | 30.0 kV | 2.01 W | 105 mm | 1,516 | 6,001 |
| lowest cost per watt | 8 mm gaps, 4 mm vanes, r 300 mm, 26°, 6 + 6 | 16.9 kV | 39.6 kV | 16.4 W | 220 mm | 3,523 | 8,308 (506 per W) |

- **The stages cost little; the ratings decide them.** The same cheapest stack carries more stages wherever the bench
  qualifies them:

| ratings (interface / gel at a bead) | stages (symmetric supply) | field wanted (k) | across | total |
|:--|:--|:--|--:|--:|
| 1 / 5 kV/mm, below the record | 1 + 1 | 4.3 kV/cm (0.2892) | 15.1 kV | 5,934 |
| **1 / 5 kV/mm (the record)** | **2 + 2** | **6.5 kV/cm (0.2373)** | **30.0 kV** | **6,001** |
| 1 / 8 | 3 + 3 | 7.7 kV/cm (0.1758) | 44.5 kV | 6,067 |
| 2 / 5 | 2 + 2, wider bands | 8.3 kV/cm (0.2791) | 30.0 kV | 6,001 |
| 2 / 8 | 4 + 4 | 13.3 kV/cm (0.2311) | 58.1 kV | 6,134 |
| 1 / 5, the asymmetric record (feed 1) | ring B on 2, ring A on Dk | 6.5 kV/cm (0.2460) | 28.1 kV | 5,951 |

- **The symmetric supply costs 50 more** than the asymmetric record: three more diode stacks and three more 100 pF
  capacitors, for 7.10 kV/cm against 6.93 at the null.
- **The stack of record** (6 mm, 3 mm, r 150, 6 + 6) also qualifies, at 6,417.
- **The fixed parts** with the rings are 3,702:
  - the PEEK retainer (120) and the gel (30);
  - the two ring electrodes (2 × 25);
  - eight 100 pF capacitors.

  There are no feedthroughs.

**With the pair inside** (core field 3, feed 1, one stage, 65 kV/cm over 3.1 mm, i.e. 20.15 kV), 81 designs meet them:

| objective | design | operating peak | across the null | power | stack per side | stack cost | total |
|:--|:--|--:|--:|--:|--:|--:|--:|
| lowest total cost | 6 mm gaps, 2.5 mm vanes, r 175 mm, 22°, 4 + 4 | 13.1 kV | 20.7 kV | 2.01 W | 105 mm | 1,503 | 6,285 |
| lowest cost per watt | 8 mm gaps, 4 mm vanes, r 300 mm, 26°, 6 + 6 | 16.9 kV | 26.9 kV | 16.4 W | 220 mm | 3,498 | 8,579 (523 per W) |

**At the earlier placeholders** (2 kV/cm over 50 mm, i.e. 10 kV), for the cones' modes:

**With the swinging core, no design meets them.**
- **The largest swing** in the matrix is 9.4 kV (8 mm gaps, 4 mm vanes, r 300 mm, 6 + 6). 10 kV would need 10 mm gaps,
  whose rims need more than 4 mm.
- **The stack of record** (6 mm, 3 mm, r 150, 6 + 6) swings ±7.1 kV but falls to z 1.23 and 1.73 W.
- **Either bring the cones closer or lower the target.** 2 kV/cm needs at most 46 mm at 9.2 kV. The cheapest designs per
  swing:

| swing wanted | cheapest design | its swing | z | power | total |
|:--|:--|--:|--:|--:|--:|
| ≥ 6 kV | 5 mm gaps, 2 mm vanes, r 200 mm, 18°, 4 + 4 | 6.2 kV | 1.362 | 2.06 W | 5,835 |
| ≥ 7 kV | 6 mm gaps, 2.5 mm vanes, r 200 mm, 22°, 4 + 4 | 7.2 kV | 1.313 | 2.58 W | 6,031 |
| ≥ 8 or 9 kV | 8 mm gaps, 4 mm vanes, r 250 mm, 22°, 4 + 4 | 9.2 kV | 1.301 | 5.04 W | 6,618 |

The best per watt with a swinging core is 6 mm gaps, 2.5 mm vanes at r 300 mm, 26°, 6 + 6: 7.4 kV, 14.7 W, 515 per W.

**With the steady core, 177 designs meet them:**

| objective | design | operating peak | power | stack per side | stack cost | total |
|:--|:--|--:|--:|--:|--:|--:|
| lowest total cost | 5 mm gaps, 2 mm vanes, r 200 mm, 18°, 4 + 4 | 11.2 kV | 2.35 W | 79 mm | 1,441 | 5,809 |
| lowest cost per watt | 8 mm gaps, 4 mm vanes, r 300 mm, 26°, 6 + 6 | 16.9 kV | 16.4 W | 220 mm | 3,488 | 8,164 (497 per W) |
| (within 0.4 %) | 6 mm gaps, 2.5 mm vanes, r 300 mm, 26°, 6 + 6 | 13.1 kV | 15.2 W | 156 mm | 2,969 | 7,567 (499 per W) |

**Either way:**
- **Material: aluminium.**
  - Metal is about 8 % of the stack's cost.
  - Stainless or copper would add 140–460 on the cheapest design and three times the mass, for no electrostatic gain.
  - Al 5083 or 6082 take a polished full round. Al 1050 is a little cheaper but soft.
- **What drives the stack's cost is per-part work:** assembly 22 %, the full rounds 19 %, polishing 13 %, G10 and the
  shaft 12 % each. So the cheapest stack has the fewest, largest vanes.
- **The fixed parts** (3,702 with the rings on two stages a side, 3,636 swinging, 3,611 steady) are about 70 % of the
  cheapest build, so extra watts are cheap at the margin.
  - The rings: 8 mm gaps at r 300 mm, 6 + 6 give 8× the power for 40 % more.
  - Steady core: at 300 mm, 6 + 6 vanes give 6.5× the power for 31 % more (6 mm gaps), or 7× for 42 % more (8 mm).
  - The pair inside would add its electrodes (2 × 80) and two non-magnetic feedthroughs (2 × 120) instead of the rings
    (placeholders).
- **The AH's steady cusp is met:** 300 A-turns per coil with the 22 mF bypass. Above that, the AH or the pump must be
  re-sized, which is not costed.

## Open
- **The field wanted at the null:** 6.5 kV/cm on Inputs is a placeholder under what the rings as built reach (7.1).
- **The ratings:** the interface along the glass (1 kV/mm) and the gel at the beads (5 kV/mm) [RH] set the bands, the
  stages and the field per kV (0.2373). The bench qualifies them (`docs/bench-test-rings.md`); higher ratings carry
  more stages (the table above).
- **The rings' leakage:** 100 GΩ per ring (an estimate from the parts) sets the multiplier's sag, and with it the stage
  factors.
- **The cones' strays** (20 pF each, 10 pF between them) are guesses. They set the swinging core's gain cost.
- **The core's leakage:**
  - steady core: above about 1 GΩ (0.17 W at 13 kV); below about 0.06 GΩ the pump does not start;
  - swinging core: it only sets the cones' DC.
