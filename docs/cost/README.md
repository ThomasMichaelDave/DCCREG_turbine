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

## The sweet spot at the placeholder prices

**Targets:** the placeholders on Inputs.
- 2 kV/cm over 50 mm on the core, i.e. 10 kV;
- at least 2 W from the electrostatic pump, z ≥ 1.3;
- at most 6 + 6 vanes, corona-safe rims;
- 300 steady A-turns at the AH.

**177 designs meet them.**

| objective | design | operating peak | power | stack per side | stack cost | total |
|:--|:--|--:|--:|--:|--:|--:|
| lowest total cost | 5 mm gaps, 2 mm vanes, r 200 mm, 18°, 4 + 4 | 11.2 kV | 2.35 W | 79 mm | 1,441 | 5,637 |
| lowest cost per watt | 8 mm gaps, 4 mm vanes, r 300 mm, 26°, 6 + 6 | 16.9 kV | 16.4 W | 220 mm | 3,488 | 7,991 (487 per W) |
| (within 0.1 %) | 6 mm gaps, 2.5 mm vanes, r 300 mm, 26°, 6 + 6 | 13.1 kV | 15.2 W | 156 mm | 2,969 | 7,394 (487 per W) |

- **Material: aluminium.**
  - Metal is about 8 % of the stack's cost.
  - Stainless or copper would add 140–460 on the cheapest design and three times the mass, for no electrostatic gain.
  - Al 5083 or 6082 take a polished full round. Al 1050 is a little cheaper but soft.
- **What drives the stack's cost is per-part work:** assembly 22 %, the full rounds 19 %, polishing 13 %, G10 and the
  shaft 12 % each. So the cheapest stack has the fewest, largest vanes.
- **The fixed parts (3,461) are about 70 % of the cheapest build,** so extra watts are cheap at the margin. At 300 mm,
  6 + 6 vanes give 6.5× the power for 31 % more (6 mm gaps), or 7× for 42 % more (8 mm).
- **The AH's steady cusp is met:** 300 A-turns per coil with the 22 mF bypass. Above that, the AH or the pump must be
  re-sized, which is not costed.

## The field on the core
The electrostatic circuit's HV side is on the rotor (`sim/core-field-findings.md`):
- a core diode charges cone A to the node's peak (about the operating peak), and a 1 nF capacitor holds it;
- cone B sits on the shaft;
- BOM fixed carries the capacitor, cone A's lead and the rotor's HV insulation; the HV parts on Designs count the core
  diode as a fifth stack.

## Open
- **The electrode geometry and spacing:** 2 kV/cm over 50 mm on Inputs are placeholders.
- **The core's leakage** must stay above about 1 GΩ (0.17 W at 13 kV). Below about 0.06 GΩ the pump does not start.
