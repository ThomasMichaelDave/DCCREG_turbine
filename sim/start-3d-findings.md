# The magnetic pump's start with the utrons in 3-D — findings

**Source:** `sim/start_3d.py` → `sim/start_3d_results.json` (107 ngspice runs, 19 min on 2 processes).

**Status:**
- [OC] the circuit: the record's deck;
- [IR] the 3-D utron sets (`sim/utron_3d.py`), La / Lb held at the parts' 0.146 H, the start criterion;
- the K4 kick and the 22 mF bypass are PROPOSED (`sim/parts-first-cut-findings.md`, `sim/ah-steady-cusp-findings.md`).
- It closes the open line of `sim/utron-3d-findings.md`: "the kick threshold and the speeds of
  `sim/parts-first-cut-findings.md` §3 were found with the record's utrons … Not re-run here."

**What runs:** `sim/parts_first_cut.py`'s own `mag_job`, unchanged, at the pick (120 Hz, the 22 mF bypass throughout).
The deck's three utron inputs (prof, tau, L_max) are replaced as `sim/utron_3d.py` replaces them, with each 3-D set from
`sim/utron_3d_results.json` variants:
- the record's frame: κ 6.70;
- the machine's cylinder with one coil of each group reversed: κ 6.44;
- the cylinder with the coils aiding: κ 5.96.
- La / Lb stay at the record's 0.146 H [IR]: the parts' first cut is trimmed to it (`sim/parts-first-cut-findings.md`
  §1), so the deck's la_ratio is rescaled to 0.579–0.584.

**What "it starts" means** [IR]: the AH coil reaches half its own set's steady peak within 40 cycles (113–154
A-turns). The parts study's 225 A-turns is half of the 450 the pick was sized to; a 3-D set's steady peak is 226–251.
Below full speed "it runs" is the parts study's own: more than 50 A-turns over the last 4 of 80 cycles.

## Headline
- **The K4 kick still starts the pump at full speed, at every rotor phase, with every 3-D set** [IR]. That is the
  470 µF / 9 V dump across La of `sim/parts-first-cut-findings.md` §3 (19 mJ), at 1200 rpm relative and the four
  phases the parts study ran.
- **The margins shrink:**

| utron set | κ | steady AH peak | the seed kick starts from | K4 at full speed | K4 at every phase from | a running pump holds from |
|:--|--:|--:|:--|:--|--:|--:|
| the record | 8.59 | 307.9 A-t | 16 % (not 14 %) | 4 of 4 phases | 1000 rpm rel. | 800 rpm rel. (stops at 700) |
| 3-D, the record's frame | 6.70 | 250.6 A-t | 20 % (not 18 %) | 4 of 4 | 1050 | 850 (stops at 800) |
| 3-D, one coil reversed | 6.44 | 241.9 A-t | 25 % (not 20 %) | 4 of 4 | 1100 | 850 (stops at 800) |
| 3-D, coils aiding | 5.96 | 226.2 A-t | 25 % (not 20 %) | 4 of 4 | 1100 | 850 (stops at 800) |

- **What it changes:**
  - **the record's seed kick** (20 % of Ψs, `sim/pole_design_variants_op.json` kick_frac, the start the pole study
    sized) starts the record's frame only just, and not the coupled sets. K4, the first cut, seeds far more and starts
    them all;
  - **the speed window:** K4 must fire above 1050–1100 rpm relative (525–550 rpm each way), not 1000. The operating
    point is 1200, so "fire at full speed, never below 500 each way" (`docs/ledger/DCCREG-design-ledger.md` §3.2)
    becomes "never below 550 each way";
  - **a running pump** stops below 850 rpm relative (425 each way), not about 750.
- **The gate passes exactly:** the record's set reproduces `sim/parts_first_cut_results.json` run for run: the
  threshold pair (14 % dies, 16 % reaches 304.70 A-turns), K4 at two phases (307.88 / 307.85), the speed rows at 950
  and 1000 rpm relative (one phase of two at 950) and the hold at 700 / 800.

## 1. The runs
| set | runs | every no-start |
|:--|:--|:--|
| the record (the gate) | steady; seeds 14 / 16 %; K4 at phases 1 and 1.5; K4 at 950 / 1000 rpm relative; hold at 700 / 800 | dies to about 0 |
| each 3-D set | steady; seeds 10–50 % (11); K4 at phases 1 / 1.25 / 1.5 / 1.75; K4 at 950–1150 rpm relative, phases 1 and 1.5; hold at 750–1000 | dies to about 0, except one |

- **The exception** [from the run]: one coil reversed, seeded at 20 %, still grows at 40 cycles. Its coil reads 68–97
  A-turns over the last 4 cycles against the 121 of the criterion (the branch 142 A-turns, z_early 0.997). It is a slow
  start, so 20 % is that set's edge, and it is not counted.
- **The speed runs** are the parts study's [OC: the same parts on a stretched cycle]: K4 fired at phase 1 or 1.5 of the
  slower cycle. At 1050 rpm relative K4 starts the record's frame at both phases, one coil reversed at one of two and
  the coils aiding at neither.
- **The hold** is the parts study's proxy for a running pump slowing down: a 60 % seed in every coil, 80 cycles at the
  lower speed [IR].

## 2. The numbers by set
**The steady state with the bypass** (60 cycles from the record's 30 % seed; `sets.*.steady`):

| set | AH peak | AH mean current | z_early | belt |
|:--|--:|--:|--:|--:|
| the record | 307.9 A-t | 1.874 A | 1.147 | 18.13 W |
| the record's frame | 250.6 A-t | 1.526 A | 1.088 | 12.27 W |
| one coil reversed | 241.9 A-t | 1.473 A | 1.081 | 11.50 W |
| coils aiding | 226.2 A-t | 1.377 A | 1.070 | 10.13 W |

- These hold La / Lb at 0.146 H. `sim/utron_3d.py` lets them follow 0.6 L_max (+3 %); its "coils aiding, La held" row
  agrees with this one to 0.3 A-turns (226.2 here against its 226 maximum).

**K4 below full speed** (the coil's peak A-turns over the last 4 of 80 cycles; 0 means the pump died):

| rpm relative | the record's frame, phase 1 / 1.5 | one reversed | coils aiding |
|--:|:--|:--|:--|
| 950 | 0 / 0 | 0 / 0 | 0 / 0 |
| 1000 | 0 / 0 | 0 / 0 | 0 / 0 |
| 1050 | 224.4 / 224.4 | 217.2 / 0 | 0 / 0 |
| 1100 | 233.4 / 233.3 | 225.9 / 225.9 | 211.2 / 211.2 |
| 1150 | 242.0 / 242.0 | 234.0 / 234.0 | 218.9 / 218.9 |

**The hold** (a 60 % seed, 80 cycles; A-turns at the end):

| rpm relative | 750 | 800 | 850 | 900 | 950 | 1000 |
|:--|--:|--:|--:|--:|--:|--:|
| the record's frame | 0 | 0 | 171.4 | 189.3 | 202.8 | 214.5 |
| one reversed | 0 | 0 | 163.1 | 181.5 | 195.3 | 207.2 |
| coils aiding | 0 | 0 | 139.7 | 166.3 | 180.5 | 192.4 |

## Caveats
- **[IR]:** the 3-D utron sets (`sim/utron-3d-findings.md`, its own caveats: the iron linear, the record's grid); La /
  Lb held at 0.146 H; the start criterion; the K4 circuit as the parts study models it (an SCR as a ramped
  conductance, R_KICK 0.1 Ω).
- **The deck's diodes** (ND, 0.54 V at 1 A). With the first-cut Schottky set the seed threshold rises by about 1 % of
  Ψs (`sim/diodes-real-findings.md` §3.1); K4's margin covers it at full speed, not re-run here.
- **Not modelled:** the neck's nonlinear field (the record's saturation law; the ledger's model check 31), the drive's
  speed ramp (each run holds one speed).
