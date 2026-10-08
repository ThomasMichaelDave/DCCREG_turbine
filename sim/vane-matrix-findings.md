# The air vane stack as a full matrix — findings

**Source:**
- `sim/vane_matrix.py` → `sim/vane_matrix_results.json` and `.csv` (2700 rows);
- the figures `docs/figures/vane-matrix-radius.png` and `vane-matrix-corona.png` (`docs/make_vane_matrix_figures.py`);
- the tables below, in `sim/vane_matrix_summary.json`.

**Designer's input.** Sweep the vane count, the vane thickness, the rotor–stator gap and the vane radius beyond
150 mm. What does a larger radius gain?

**The matrix (2700 designs):**

| axis | values |
|:--|:--|
| gap g | 3, 4, 5, 6, 8, 10 mm. The operating peak is the air breakdown ÷ 1.5: 7.3–20.6 kV |
| thickness t | 1.5, 2, 2.5, 3, 4 mm with full-round edges; the Ca / Cb plates alike |
| outer radius r_out | 150, 175, 200, 250, 300 mm, rotor and stator vanes alike (r_in 50 mm) |
| vanes N | 4, 6, 8, 10, 12, 16 stator + rotor per varicap per side |
| sector width | 18°, 22°, 26°: 6 sectors, stator = rotor |

**Per design** (`sim/air_stack_sizing.stack`, as in stage 4):
- C_max, C_min, κ and Ca from the full-round vane cell (`sim/vane_cell.py`);
- the bare core's z and its eigen-cycle power at the operating peak, at 1200 rpm relative;
- the stacks' and the tube's lengths from `stack_sizing.layout`;
- the aluminium and the rotor vanes' inertia;
- the rims' corona onset.

**Calibration [IR].** 12 designs ran in ngspice for the clamped power. The clamped / eigen-cycle ratio tracks the gain:
1.02 + 1.13 (z − 1). That fits 11 of them within ±4 %, and the largest stack (7.2 nF) within +11 %.

**Feasible** means the rims hold the operating peak on a handled surface (Peek, m 0.85 [RH]) and z ≥ 1.3: 1553 of the
2700 designs.

**The bodies in these tables are the old placement.** The HV side has since moved onto the rotor
(`sim/core-field-findings.md`), which puts the Ca / Cb plates on the rotor. Move their mass from the counter-rotor's
column to the rotor's.

## 1. What a larger radius buys

At the 6 + 6 cap, with 6 mm gaps, 3 mm full-round vanes and 22° sectors:

| r_out | C_max | κ | z | clamped power | per metre | Al: rotor + counter-rotor | rotor vanes' inertia | cage Ø |
|:--|--:|--:|--:|--:|--:|--:|--:|--:|
| 150 mm | 410 pF | 7.5 | 1.309 | 2.1 W | 14 W/m | 2.9 + 9.5 kg | 0.029 kg m² | 332 mm |
| 175 mm | 570 pF | 9.0 | 1.375 | 3.4 W | 22 W/m | 3.8 + 13.1 kg | 0.053 kg m² | 382 mm |
| 200 mm | 755 pF | 10.5 | 1.426 | 4.9 W | 32 W/m | 4.8 + 17.2 kg | 0.090 kg m² | 432 mm |
| 250 mm | 1194 pF | 13.9 | 1.500 | 8.7 W | 56 W/m | 7.4 + 26.9 kg | 0.219 kg m² | 532 mm |
| 300 mm | 1727 pF | 17.7 | 1.552 | 13.5 W | 87 W/m | 10.4 + 38.8 kg | 0.454 kg m² | 632 mm |

The stacks stay 156 mm per side and the tube 916 mm long.

- **Power grows faster than the area.** The overlap grows as r_out² − r_in², so C_max rises 4.2× from 150 to 300 mm,
  and the power 6.4×.
- **The gain margin grows too** (z 1.31 → 1.55, κ 7.5 → 17.7):
  - the fringe at a sector's edges grows only with the radius, while the overlap grows with its square;
  - the fixed 20 pF stray and the 2 pF rim floor weigh less against a bigger stack.
- **Or keep the power and shorten the stack.** Take the 1.5 mm stack's 7.4 W (fig., third panel):
  - at 150 mm no stack of up to 16 + 16 vanes reaches it on these gaps;
  - at 175 mm it takes 205–555 mm of stack per side, at 200 mm 155–350 mm, and at 300 mm 80–150 mm.
- **The costs:**
  - the aluminium grows about with r² (4× at 300 mm), most of it in the Ca / Cb plates on the counter-rotor;
  - the rotor vanes' inertia grows 16×, to 0.45 kg m² (about 0.9 kJ at 600 rpm). The rim speed stays a trivial
    19 m/s;
  - the tube's diameter grows from 332 to 632 mm.

## 2. The rims set a thickness for every gap

The operating peak grows with the gap faster than a rim's corona onset does, so wider gaps need thicker rims
(fig. `vane-matrix-corona.png`, handled surface):

| gap (operating peak) | 3 mm (7.3 kV) | 4 mm (9.3 kV) | 5 mm (11.2 kV) | 6 mm (13.1 kV) | 8 mm (16.9 kV) | 10 mm (20.6 kV) |
|:--|--:|--:|--:|--:|--:|--:|
| thinnest corona-safe full round | 1.5 mm | 1.5 mm | 2 mm | 2.5 mm | 4 mm | over 4 mm |

- **The rule of thumb:** from 5 mm up, the rim wants about 0.4–0.5 × the gap.
- **At 10 mm** even 4 mm rims reach onset below the peak (0.95 of it). That gap needs rims of 5 mm or more, which the
  matrix doesn't cover.

## 3. The best designs

**(a) Power per metre of stack, uncapped.** Every radius picks the same corner: 3 mm gaps, 1.5 mm vanes, 26° sectors
and 16 + 16 vanes. That corner is on the grid's edge in three axes.

| r_out | clamped | per metre | κ | z | operating peak | stacks per side | Al: rotor + counter-rotor |
|:--|--:|--:|--:|--:|--:|--:|--:|
| 150 mm | 6.3 W | 29 W/m | 18.4 | 1.569 | 7.3 kV | 218 mm | 4.4 + 13.7 kg |
| 200 mm | 12.5 W | 57 W/m | 25.9 | 1.625 | 7.3 kV | 218 mm | 7.5 + 24.9 kg |
| 300 mm | 30.5 W | 140 W/m | 43.9 | 1.680 | 7.3 kV | 218 mm | 16.3 + 56.3 kg |

This repeats the air sizing's lesson: in air the densest stack is the narrowest gap, at a low voltage.

**(b) Power under the 6 + 6 cap.** Once the radius grows, the wider gaps win: a fixed stack pumps about C V², and the
wider gap holds more voltage.

| r_out | best: gap, vanes, sectors | operating peak | clamped | κ | z | stacks per side | Al: rotor + counter-rotor |
|:--|:--|--:|--:|--:|--:|--:|--:|
| 150 mm | 5 mm, 2 mm, 26° | 11.2 kV | 2.4 W | 8.2 | 1.354 | 128 mm | 2.2 + 7.3 kg |
| 175 mm | 6 mm, 2.5 mm, 26° | 13.1 kV | 3.7 W | 7.2 | 1.340 | 156 mm | 3.6 + 12.6 kg |
| 200 mm | 6 mm, 2.5 mm, 26° | 13.1 kV | 5.4 W | 8.4 | 1.389 | 156 mm | 4.7 + 16.5 kg |
| 250 mm | 8 mm, 4 mm, 26° | 16.9 kV | 10.1 W | 6.8 | 1.347 | 220 mm | 11.4 + 41.6 kg |
| 300 mm | 8 mm, 4 mm, 26° | 16.9 kV | 16.4 W | 8.4 | 1.412 | 220 mm | 16.3 + 60.0 kg |

- **26° against 22°:** 26° gives 5–15 % more power for 0.04–0.05 less z.
  - So it wins on power, while 22° keeps more gain margin. At 300 mm with 8 mm gaps: 16.4 W at z 1.41 against
    15.2 W at z 1.46.
  - 26° is the grid's edge.

## 4. What it means
- **With the 6 + 6 cap, the radius is the lever.**
  - 200 mm with 6 mm gaps and 2.5–3 mm vanes gives 4.9–5.4 W at 13 kV: 2.3–2.5× the 150 mm stack, from the same
    156 mm per side.
  - 250–300 mm with 8 mm gaps and 4 mm vanes gives 10–16 W at 17 kV.
- **The price is mass and diameter.**
  - The counter-rotor's Ca / Cb plates dominate the mass.
  - They need not share the vanes' radius or thickness: only Ca = 1.1 C_max and their rims are fixed. That freedom was
    not swept.

## Caveats
- **Absolute powers** carry the calibration: 12 points, residuals −4 to +11 %.
- **Grid edges:** the uncapped best sits on three of them (3 mm, 1.5 mm, 16 + 16), and the capped bests at 26°.
- **The 2-D cell** at h 0.25 mm reads κ a few % high, more for thin vanes (`sim/air-stack-sizing-findings.md`
  caveats).
- **Not modelled:**
  - the shaft's bending with the heavier vanes (`sim/shaft_bearings.py`);
  - the bearings and the gear under the heavier counter-rotor;
  - the vanes' stress (trivial at 19 m/s).
- **Held fixed:** the sector count (6) and the inner radius (50 mm).
