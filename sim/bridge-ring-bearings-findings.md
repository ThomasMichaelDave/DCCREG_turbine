# The bridge-ring bearings: their place, the part, the shafts — findings

**Source:** `sim/bridge_ring_bearings.py` → `sim/bridge_ring_bearings_results.json` and
`docs/figures/bridge-ring-bearings.png` (about 40 s). The solids come from `sim/tube_geometry.py --layout`, which imports
this study's placement and writes `docs/geometry/tube/tube-r150-n6-air6-wound-g0p5-6br-hub50-layout.{step,glb,parts.json}`.
Its section `…-layout-section.png` shows them in panel (e), and the still `…-layout-3d-ringA.png` and the viewer's
"Ring bearing A" view (the "DCCREG Wound Tube" artifact) show them in 3-D.

**What it is:** the bridge-ring bearings that the layout needs (`sim/multiplier-layout-findings.md` §7), placed, drawn
and named.
**Status:** PROPOSED: the placement, the seat and the part are the designer's to accept.
**Tags:**
- [OC] the beam statics and modes; the ISO 281 and Palmgren forms;
- [IR] the placement, the seat, the masses, the duty's assumptions; the catalogue data, as a web search rendered it;
- [RH] the cartridge's walls; the seats' stiffness.

## Headline
- **The part: SKF 6205-2Z.**
  - It is a 25 / 52 / 15 mm SKF Explorer deep groove ball bearing, shielded both sides, with normal clearance.
  - Its ratings: C 14.8 kN, C0 7.8 kN, Pu 0.335 kN; reference speed 28 000 r/min, limiting speed 14 000 r/min;
    0.13 kg.
  - Its running accuracy is ISO P5 (SKF Explorer up to 52 mm OD); its dimensions are to P6.
  - It is the record's bearing exactly: its ratings are the ones `sim/rotor_mechanics.py` already uses, and it has
    the shields the record asks for.
  - Alternates: Schaeffler FAG 6205-C-2Z (Cr 15.9 kN) and NSK 6205ZZ (§1).
- **The place** [IR]:
  - each bearing takes the record's end-bearing slot (h 467–487 mm from the hub's centre);
  - the end bearing (frame) moves out one 20 mm slot (h 487–507);
  - **the machine grows 974 → 1014 mm.** The bridge-ring bearings sit at z 30 / 984, the end bearings at
    z 10 / 1004, the Ca|reluctance bearings at z 218 / 796.
- **The seat** [IR]:
  - an austenitic stainless cartridge in an 8 mm G10 spider, centred in its slot as every spider of the record is;
  - a 6 mm G10 ring joins the spider's rim to the bridge ring's outer face;
  - the spider then stays 9 mm clear of the utrons' end turns, where an end disc on the face itself would leave 3 mm.
- **The shafts at d 25** (the record's two-body model, the record's solids moved to the layout; the criterion 60 Hz):
  - **f1 is 87 Hz on stiff seats and 83 Hz on G10 spiders**, where the layout study's placement gave 89 / 85;
  - the utron gap moves at most 1.6 µm under 1 g lateral;
  - the drawn solids agree to 1.2 %.
- **What sets f1 now** [OC]: the shaft's central span.
  - Mode 1 bends the 578 mm of shaft between the Ca|reluctance bearings, which carries the hub, the can, both decks,
    Ca / Cb and the rotor vanes. The counter-rotor stays almost still.
  - The bridge-ring bearings close the counter-rotor's overhang (its 14 Hz mode); after that the shaft's diameter
    moves f1 (d 30: 96–105 Hz) and the seats barely do (2.3 × the stiffness: +5 %).
- **The duty** (the axis vertical) [IR]:
  - the bottom bridge-ring bearing locates the counter-rotor: 331 N at 1200 rpm relative, L10 217 000 h;
  - the top one floats on the 100 N spring preload: L10 3.8 million h;
  - the speed is 8.6 % of the part's limit;
  - the pair adds 2.1 W of friction (6.1 W at the record's high end).
- **Every gate passes:**
  - this file's copy of the layout study's shaft model reproduces its nine rows exactly;
  - the part fits the record's slot and has its ratings;
  - d 25 meets 3 × 20 Hz on both seats;
  - the drawn solids hold the placement and agree on f1;
  - the solids: no clash in 1151 pairs, no sweep hit, every deck pair as the plan.

## 1. The part [IR: catalogue data]
The makers' own sites are outside this session's network policy. The data below come from a web search of the
distributors' listings and SKF's Explorer brochure (2026-10-11); re-read the current product page before ordering.

| | SKF 6205-2Z (proposed) | Schaeffler FAG 6205-C-2Z | NSK 6205ZZ |
|:--|:--|:--|:--|
| d / D / B | 25 / 52 / 15 mm | 25 / 52 / 15 mm | 25 / 52 / 15 mm |
| closures | 2 sheet-steel shields (2Z) | 2 shields | 2 shields (ZZ) |
| C / C0 | 14.8 / 7.8 kN | 15.9 / 7.8 kN | 14.0 / 7.85 kN (distributors) |
| fatigue limit | 0.335 kN | 0.53 kN | — |
| reference / limiting speed | 28 000 / 14 000 r/min | 16 000 / 18 400 r/min | — / 15 000 r/min (grease) |
| mass | 0.13 kg | 0.129 kg | 0.129 kg |
| running accuracy | ISO P5 (Explorer, up to 52 mm OD) | to be confirmed | normal, unless a P6 / P5 suffix is ordered |
| other | kr 0.025, f0 14; abutments da ≥ 30.6, Da ≤ 46.4 mm | f0 13.8; Generation C | — |

**The sources:**
- **SKF 6205-2Z:**
  - [Simply Bearings, 6205-2Z](https://www.simplybearings.co.uk/products/6205-2z-skf);
  - [Simply Bearings, 6205](https://www.simplybearings.co.uk/products/6205-skf);
  - [RS Components 286-8038](https://uk.rs-online.com/web/p/ball-bearings/2868038);
  - the Explorer accuracy: [SKF's brochure 6270 EN](https://www.skf.com/binaries/pub12/Images/SKF%20Explorer%20deep%20groove%20ball%20bearings%20with%20RSL%20and%20RSH%20seals_6270%20EN_tcm_12-179206.pdf)
    and [Machine Design](https://www.machinedesign.com/archive/bearings-products-deep-groove-bearings).
- **FAG 6205-C-2Z:**
  - [Schaeffler medias](https://medias-at.schaeffler.com/de/product/rotary/rolling-and-plain-bearings/ball-bearings/deep-groove-ball-bearings/6205-c-2z-l207>v/p/1695363);
  - [csapagy-bolt.hu](https://csapagy-bolt.hu/catalog/product/57621);
  - [RS Components 137-1663](https://uk.rs-online.com/web/p/ball-bearings/1371663).
- **NSK 6205ZZ:**
  - [RS Components 409-0502](https://uk.rs-online.com/web/p/ball-bearings/4090502);
  - [IMS Supply](https://www.imssupply.com/catalog/nsk/6205zz.html).

**Why this part:**
- **The record's class:** a 6205 (25 / 52 / 15) in the record's 20 mm slot, on the d 25 journal. The ratings that
  `sim/rotor_mechanics.py` `BRG_6205` carries (14.8 / 7.8 kN, f0 14) are this part's, so the record's lives and
  stiffnesses stand.
- **Shields, not seals:** `sim/rotor-mechanics-findings.md` §6 asks for shields (2Z).
- **The runout in a standard part:** the record asks P6 at the inner bearings with the eighth pair, which gives 36 µm
  all-in against 0.05 mm allowed (`sim/rotor-mechanics-findings.md` §5.4). The Explorer 6205's running accuracy is P5
  (K_ia 4, K_ea 8 µm) without a special order.
- **Normal clearance under an axial spring preload,** as the record takes it.
- **The drive's first cut** already names a 6205-2Z for its gear-end bearing (`docs/drive-gear-belt.md` §7).

**To specify at ordering** [IR]:
- **the grease:** the record's friction estimate takes a low-viscosity grease (§6 there); the part comes with the
  maker's standard fill;
- **the material:** steel, like the record's six bearings. The pair is symmetric about the hub, farther from the null
  than the pumps' iron, and the AH null model leaves every bearing out (`sim/ah-null-findings.md`, caveats).

## 2. The place and the seat [IR]
Side A, from its end; side B mirrors it (z' = 1014 − z):

| part | r (mm) | z (mm) | body |
|:--|:--|:--|:--|
| the end bearing (frame), the record's 6205, on its frame spider (r 26–162, z 6–14) | 12.5–26 | 2.5–17.5 | frame |
| **the bridge-ring bearing, SKF 6205-2Z** | 12.5–26 | 22.5–37.5 | between the bodies |
| its cartridge, austenitic stainless: barrel / flange on the spider / lip over the outer ring | 26–30 / 30–38 / 23.2–26 | 22.5–37.5 / 22.5–26 / 37.5–39 | counter-rotor |
| its spider, G10 8 mm | 30–156.5 | 26–34 | counter-rotor |
| the ring, G10 6 mm, from the spider's rim to the bridge ring | 131.5–156.5 | 34–40 | counter-rotor |
| bridge ring A (the record's) | 131.5–156.5 | 40–214 | counter-rotor |
| the rotor's reluctance-bay sleeve; utron A's end turns | 12.5–20.5; 58–128 | 40–208; from 43 | rotor |

- **The clearances:**
  - the spider is 9 mm from the end turns;
  - the frame spider is 8.5 mm from the cartridge;
  - the two bearings' faces are 5 mm apart (a spacer on the shaft between their inner rings, not drawn).
- **Why the end bearing moves out** rather than the bridge-ring bearing taking a new slot inboard: the geometry is the
  same either way. The bridge ring and its bay keep their place relative to the hub, and every slot is the record's
  20 mm.
- **Why a spider and a ring, not an end disc on the ring's face** (the drive's first cut, `docs/drive-gear-belt.md`
  §5): the utrons' end turns stand 3 mm off that face (z 23 against 20 in the record's frame). Centred in its slot,
  the spider clears them by 9 mm.
- **The cartridge** is the record's "metal cartridge in the spider" (`sim/rotor-mechanics-findings.md` §8):
  - its flange is bolted to the spider;
  - at side A its lip carries the counter-rotor's weight onto the outer ring;
  - at side B the outer ring floats on a wave spring under the lip.
  Its walls are [RH].
- **The drive's first cut** makes its gear-end bearing the bottom bridge-ring bearing (`docs/drive-gear-belt.md` §8;
  `sim/rotor-mechanics-findings.md` §8.3). It and this placement agree on the part and on its role (locating the
  counter-rotor), but differ in two ways:
  - the seat: the drive's 10 mm G10 end disc lies on the ring's face, 3 mm from the end turns;
  - the stack-up, cut on the record's 940 mm: there the frame's locating bearing goes into the gear case's floor.
  With the drive, side A's frame bearing and its slot here become the drive's. Its stack-up is to be re-cut on this
  layout.

## 3. The shafts [OC law / IR inputs]
**The model:**
- `sim/shaft_bearings.py` `two_body`: the shaft and the counter-rotor as two Euler–Bernoulli beams;
- the record's solids, moved as `sim/multiplier_layout.py` `shaft()` moves them;
- the end bearings and their frame spiders one slot further out, the shaft 40 mm longer, and the new parts as masses:
  - each spider 1.10 kg, each ring 0.25 kg, each cartridge 0.135 kg, all on the counter-rotor;
  - each bearing 0.13 kg, on the shaft, as the record's convention;
- k_mag 2e5 N/m per reluctance plane, as the layout study;
- the seats at the record's 2e8 N/m ("stiff") or 0.86e8 N/m (a preloaded 6205 in a G10 spider,
  `sim/rotor-mechanics-findings.md` §4).

**The masses** (the shaft's steel counted once, corrected here; see the end of this file):
- the rotor goes from 33.76 to 34.18 kg: the two bearings and 40 mm of shaft;
- the counter-rotor goes from 30.81 to 33.78 kg: the spiders, rings and cartridges.

| shaft | seats | f1 / f2 / f3 (Hz) | the utron gap, 1 g lateral | the layout study's f1 (z 28 / 946, 974 mm) |
|:--|:--|:--|--:|--:|
| **d 25** | **stiff (2e8)** | **87.1 / 164.1 / 203.7** | **+1.6 µm** | 89.2 |
| **d 25** | **G10 spider (0.86e8)** | **83.2 / 142.9 / 193.3** | **+1.1 µm** | 84.7 |
| d 30 | stiff | 105.0 / 190.1 / 276.1 | +0.4 µm | 107.4 |
| d 30 | G10 spider | 96.2 / 165.9 / 214.9 | −0.1 µm | 97.9 |
| d 40 | stiff | 123.6 / 237.9 / 314.1 | −0.4 µm | 127.0 |
| d 40 | G10 spider | 105.5 / 213.3 / 231.8 | −0.9 µm | 107.4 |

- **f1 falls 2 %** against the layout study's placement:
  - the bearing now sits 10 mm outside the ring's face instead of 8 mm inside it;
  - the counter-rotor carries 3 kg more at its ends;
  - the shaft is longer.
- **The drawn solids** (`sim/tube_geometry.py` LayoutMachine, every solid's own mass and inertia; densities as the
  record's, with the potting and the HV parts as `sim/multiplier_layout.py` `deck_mass` [RH]):
  - f1 is 86.1 / 82.2 Hz (−1.2 %), the gap +1.6 / +1.1 µm;
  - the rotor weighs 35.09 kg (the drawn decks, wiring and potting are 0.91 kg over the study's estimate), the
    counter-rotor 33.93 kg.
- **The mode shapes** (Figure (b), d 25 on G10 spiders):
  - mode 1 (83 Hz) bends the central span, the counter-rotor nearly still;
  - mode 2 (143 Hz) bends the shaft's outer spans in phase, against the centre;
  - mode 3 (193 Hz) rocks them in antiphase.
  The bridge-ring bearings have taken the counter-rotor's overhang modes out of the low range.
- **The seats move f1 little** (Figure (a)): from 0.4e8 to 3.5e8 N/m it goes 75 → 88 Hz, and f2 123 → 174 Hz. Stiff
  seats buy more on f2 and f3 than on f1.
- **The margins to the pumps' 120 / 240 Hz** [IR: their force ripple between the bodies is small; the three utrons'
  pulls balance, `sim/rotor-mechanics-findings.md` §3]:

  | shaft, seats | the margins |
  |:--|:--|
  | d 25, G10 spiders | f1 31 % under 120 Hz; f2 19 % over 120; f3 19 % under 240 |
  | d 25, stiff | f3 15 % under 240 Hz |
  | d 30, G10 spiders | f3 10 % under 240 Hz |
  | **d 40, G10 spiders** | **f3 3.4 % under 240 Hz: avoid it, or tap-test** |

  - The run-up sweeps the pumps' 120 Hz through f1 at about 70 % speed, inside its 32 s ramp
    (`docs/drive-gear-belt.md` §6).
- **The 1 g lateral (handling) loads** (d 25, G10 spiders):
  - the bridge-ring bearings 359 N each, the Ca|reluctance bearings 194 N, the end bearings 333 N;
  - the static safety C0 / P0 is 21.7 at the least.

## 4. The duty [IR: ISO 281 basic rating life, Palmgren's friction; the part's ratings]
The axis is vertical, so the bearings' radial loads are the unbalance (≈ 5 N at G2.5, `sim/rotor-mechanics-findings.md`
§7) and their axial loads the weights and the preloads.
- **The bottom bridge-ring bearing locates the counter-rotor axially.** It is the bearing nearest the gear, as the
  drive's first cut has it. The other inner bearings float.
- **The bottom end bearing (frame) locates both bodies,** as in the record.

| bearing | speed | axial load | P | L10 | friction (f0 1, 30 mm²/s; f0 2, 70) | Hertz stiffness / with the G10 spider |
|:--|:--|--:|--:|--:|:--|:--|
| bridge ring A, locating the counter-rotor | 1200 rpm relative | 331 N | 592 N | 217 000 h | 1.27 W; 3.24 W | 1.79e8 / 1.12e8 N/m |
| bridge ring B, floating | 1200 rpm relative | 100 N (the preload) | 229 N | 3.8 × 10⁶ h | 0.86 W; 2.83 W | 1.20e8 / 0.86e8 N/m |
| end A (frame), locating both bodies | 600 rpm | 667 N | 1002 N | 90 000 h | 0.95 W; 1.57 W | 2.25e8 / 1.29e8 N/m |

- **The speed:** 1200 rpm relative is 8.6 % of the 2Z's limiting speed (n·dm 46 200 mm/min).
- **The friction:** the pair adds 2.1 W nominal and 6.1 W at the high end, on top of the record's 5.1 W (3.2–14.2 W,
  `sim/rotor-mechanics-findings.md` §6).
- **The end bearing** carries both bodies, 667 N against the record's 650 N (`sim/rotor-mechanics-findings.md` §5.4):
  L10 90 000 h against 92 000 h. The drive's first cut gave 65 000 h, with its belt load as well.
- **The minimum load and the preload** [IR]:
  - SKF's minimum radial load, kr (ν n / 1000)^(2/3) (dm / 100)², is 40 N at 30 mm²/s and 71 N at 70 mm²/s, far
    above the unbalance. The axial spring preload loads the balls instead, which is the record's reason for it
    (`sim/rotor-mechanics-findings.md` §5.2).
  - SKF's rule for spring preloads in small motors, F = k d with k 0.005–0.01 kN/mm
    ([Design World](https://www.designworldonline.com/what-are-the-best-methods-for-preload-in-a-bearing-system/)),
    gives 125–250 N at d 25, so the record's 100 N sits under it.
  - At 150 N the bearing's stiffness rises 14 % (1.37e8 N/m) and its friction by 0.07 W.
  - The preload is the designer's choice; this study keeps the record's 100 N.
- **The reference link** stays the wired Ca|reluctance bearing (`sim/multiplier-layout-findings.md` §7). The
  bridge-ring bearings' cartridges sit in G10, with no wired path. The nearest HV part is C1's outermost rotor vane,
  0.2 m inboard, beyond the Ca|reluctance bearing.

## Gates
| gate | result | pass |
|:--|:--|:--|
| G1 this file's copy of the layout study's shaft model | its nine rows (d 25 / 30 / 40, with and without the bridge-ring bearings, both seats) to 0 relative | ✔ |
| G2 the part fits the record | 25 / 52 / 15 mm, the record's slot; C, C0, f0 as `sim/rotor_mechanics.py` `BRG_6205` | ✔ |
| G3 d 25 meets 3 × 20 Hz | 87.1 Hz on stiff seats, 83.2 Hz on G10 spiders; the gap +1.6 / +1.1 µm (≤ 50) | ✔ |
| G4 the drawn solids | the bearings' z as placed (30 / 984, 10 / 1004, 218 / 796), 1014 mm; f1 within 1.2 % (5 % allowed) | ✔ |
| the solids (`sim/tube_geometry_layout_results.json`) | 386 solids of 147 prototypes; no clash in 1151 pairs; no sweep hit; G-LAYOUT and G-TUBE-WOUND as before; the STEP reads back 386 / 386 | ✔ |

## Caveats
- **The catalogue data** were not read from the makers' own pages (see §1).
- **The seats' stiffness** is bracketed, not modelled: the record's 2e8 N/m and its 0.86e8 for a G10 spider [RH]. Tap-test
  the build.
- **The runout budget** (`sim/rotor-mechanics-findings.md` §5) is the record's stack, with its hub-face bearings. Its
  influence coefficients for this layout's four inner bearings are not re-run. The part's P5 running accuracy is the
  record's tightest class.
- **The cartridge, its lip and the spacer** are envelopes [RH]: the wave spring, the circlips and the bolts are not drawn.
- **The windage changes by +0.06 W** on the record's correlations (`sim/rotor_mechanics.py` windage):
  - the bridge rings' ends no longer face the frame's spiders: −0.05 W;
  - the new spiders face them across 12 mm: +0.09 W;
  - the outer carrier discs now face a counter-rotating spider: +0.01 W.
- **Not run:** the gear's own masses and its frame bearing in the case (the drive is not drawn).

## What contradicts or updates the records
- **`sim/multiplier-layout-findings.md` §7** ("10–20 mm a side … not counted in the 974 mm"; 89 / 85 Hz): with the
  bearings placed, it is 20 mm a side, 1014 mm, and 87 / 83 Hz as drawn.
- **`sim/multiplier-layout-3d-findings.md`** ("not drawn: the bridge-ring bearings"; 378 solids, 974 mm): they are
  drawn; the layout model is now 386 solids and 1014 mm.
- **The ledger §3.1** (131–165 Hz for the eighth pair): that is the record's stack. The layout gives 83–87 Hz at d 25,
  set by the shaft's central span.
- **`sim/rotor-mechanics-findings.md` §5.4** (the Ca|rel A bearing locates the counter-rotor): with the bridge-ring
  bearings, the bottom one locates it, as the drive's first cut proposes.
- **`docs/drive-gear-belt.md` §8:** its stack-up is cut on the record's 940 mm with an end disc on the ring's face, so
  it is to be re-cut on this layout (§2).
- **The record's two-body rotor mass** (`sim/tube-shaft-findings.md` §0: 33.4 kg at d 25; the layout's 36.8 kg in
  `sim/multiplier-layout-findings.md` §7) counted the shaft halves twice, once as solids and once as the beam's
  distributed steel. The model itself counted them once, so its modes, deflections and loads stand (they move by
  3e-8). Corrected in `sim/shaft_bearings.py` `two_body`, it is 30.4 kg for the record and 33.8 kg for the layout.
  `sim/shaft_bearings_record_results.json` and `sim/multiplier_layout_results.json` are re-run; only the rotor masses
  change, and the record's material names (austenitic stainless) take the place of the stale ones.
- **The tools, none of the record's other outputs changed:**
  - `sim/shaft_bearings.py` `two_body` gains `n_shapes` (the mode shapes; default off);
  - `sim/tube_geometry.py` LayoutMachine gains `ring_bearings` (default on) and draws the parts;
  - the viewer gains the "Ring bearing A" view.
