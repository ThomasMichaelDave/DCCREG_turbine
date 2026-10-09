# The locked hub, and the field at the AH null — findings

> **Superseded in part by the build (2026-10-09, `sim/hub-rings-build-findings.md`).**
> - **The record:** §1's three stages at 20–53° were sized without the copper edges. Their polar beads would run at
>   7.7 kV/mm in the gel, against 5. The rings as built hold **two stages on ring B, 28.2 kV across, bands 25.75–57.7°
>   with beaded edges: 6.9 kV/cm at the null**. More stages need the bench's higher ratings.
> - **The placeholders:** the retainer (now PEEK with a gel pocket, G10 outside), the leakage (now about 100 GΩ per
>   ring) and the open items on the rings' material and the drift test are answered there.
> - **Still the lock-down's:** the rest of this study stands (its tables use the placeholder ε 4.7, `EPS_RET_LOCKDOWN`).

**Source:**
- the hub: `presets/hub-locked.json` (the designer's stack-up and choices; every value carries its status and source);
- the field: `sim/hub_locked.py` → `sim/hub_locked_results.json`;
- the supply: `sim/core_field.py`, the `dc<n> 0.1nF` runs → `sim/core_field_results.json`;
- the figure: `docs/figures/hub-locked.png` (`docs/make_hub_locked_figure.py`).

**Designer's lock-down (2026-10-08), inside out:**
1. **The vacuum vessel:** a sphere, 50 mm in diameter, borosilicate glass.
2. **The rings sit around it.**
3. **The AH cores with their coils** on its z axis, top and bottom.
4. **A retainer holds all of it**, and the shaft coupler encapsulates the retainer.
5. **The same shaft, top and bottom**, each half with its side's symmetric electrostatic and magnetic pump.

**Designer's choices (2026-10-09):**
- **the rings outside the glass make the field;**
- **the glass wall is 1.5 mm;**
- **the AH flanges sit outside the vessel.** Read here as: the flanges sit outboard of the AH, at |z| 72–80, and the
  160-turn coil is kept.

**Taken from the register** (`presets/electromagnets-RA.json`): the AH core is a MnZn 77 rod, Ø12.3 × 41.3 mm at
|z| 30.7–72, on a G-10 former. The coil is the 160-turn rewind in variant (a)'s window: r 8.25–11.45 mm, |z| 31.35–71.35.

**Placeholders [RH]:**
- the retainer and coupler (ε 4.7, out to r 33 mm, |z| ≤ 72);
- the rating of the glass–retainer interface between the rings (1 kV/mm);
- each ring's leakage (10 GΩ).

## 1. The rings of record
- **Two bands on the glass, under the retainer,** mirror-symmetric about the equator:
  - from 20° (r 8.6 mm, just clear of the AH seat) to 53° (r 20.0 mm, |z| 15.0 mm) from the axis;
  - 0.5 mm thick;
  - 32.2 mm apart along the glass across the equator.
- **The supply: the pump's DC on three multiplier stages.**
  - Ring A takes node 1's negative peak through Dk: −13.2 kV.
  - Ring B sits on three Cockcroft-Walton stages on node 4: +19.0 kV.
  - That is 32.2 kV across, with all storage at 100 pF.
- **At the null:** 7.8 kV/cm and 2.7 Pa as connected, settling toward 8.9 kV/cm (§3).
- **The supply is the limit, not the vacuum.** At 7.8 kV/cm the vacuum is far below its 67 kV/cm rule.
- **What sets the bands:** with more DC the rings need a wider gap between them, so the bands end further from the
  equator. More DC still wins:

| supply | across the rings | bands | gap along the glass | field at the null | pressure | settled | start z |
|:--|--:|:--|--:|--:|--:|--:|--:|
| no stage (ring B on the shaft) | 13.2 kV | 20–75° | 13.2 mm | 3.8 kV/cm | 0.65 Pa | 4.1 kV/cm | 1.237 |
| one stage | 20.6 kV | 20–66° | 20.6 mm | 5.7 kV/cm | 1.45 Pa | 6.2 kV/cm | 1.184 |
| two stages | 27.3 kV | 20–59° | 27.3 mm | 7.1 kV/cm | 2.22 Pa | 7.9 kV/cm | 1.179 |
| **three stages (the record)** | **32.2 kV** | **20–53°** | **32.2 mm** | **7.8 kV/cm** | **2.70 Pa** | **8.9 kV/cm** | **1.178** |

- **A better-rated interface lets the bands reach the equator.** With three stages: 9.2 kV/cm at 2 kV/mm, 9.6 at 5.
  - 5 kV/mm is the repo's derated garolite with a creepage margin (`sim/design_synth.py`).
- **Checks:**
  - **The AH:** each ring's average field to the AH cores is 2.6 kV/mm through the retainer and the seats, against
    5 kV/mm derated garolite [IR].
  - **The diodes:** Dk sees 7.5 kV reverse; the multiplier's diodes at most 7.0 kV.
  - **The multiplier:** at 100 pF it sags. Its third stage adds 4.9 kV, not 7.4, with the 10 GΩ placeholder leakage
    per ring. Ring B ripples 0.7 kV p-p.
  - **The strays:** the rings' strays (7.4 pF each to the shaft side, 1.3 pF between them) sit behind diodes, off the
    pump's swing.
- **Against the other options:**
  - **the pair inside the vacuum:** 8.4× the field (65.7 kV/cm) and 70× the pressure, at the cost of two feedthroughs
    and a side entry;
  - **the 120 Hz swing on the rings:** a fifth of the field (±1.5 kV/cm on 8 mm bands).

## 2. The comparison that decided it
Both readings of "the rings" were solved in the locked hub, at one stage (20.6 kV):

| electrodes | field at the null | pressure | in time | the pump |
|:--|--:|--:|:--|:--|
| the Rogowski pair inside the vacuum (20.6 kV across 3.14 mm) | 65.7 kV/cm | 191 Pa | steady | start z 1.184; 2.14 W |
| two rings outside the glass, DC as connected (8 mm bands at 50°) | 4.2 kV/cm | 0.79 Pa | drifts as the glass leaks | unchanged |
| the same rings, DC settled (the glass alone leaking) | 6.0 kV/cm | 1.6 Pa | after about 30 min | unchanged |
| the same rings, the 120 Hz swing (float wiring) | ±1.5 kV/cm | 0–0.1 Pa | AC | z 1.286; 2.05 W |

- **The pair inside** fits the 50 mm vessel with 12 mm to spare, but its stems would have to enter from the side,
  since the axis is the AH's.
- **The designer chose the rings outside the glass.** §1 then sized them; wide bands on three stages almost double
  this table's 4.2 kV/cm.

## 3. How the rings behave
- **The ring's form, at one stage** (8 mm bands did best of the narrow rings, around 50°):

| ring | DC field per kV across | at 20.6 kV | to the shaft side | ring to ring | the swing's peak | z with the swing |
|:--|--:|--:|--:|--:|--:|--:|
| wire Ø1.5 mm | 0.152 (kV/cm)/kV | 3.1 kV/cm | 4.8 pF | 1.0 pF | ±1.1 kV/cm | 1.291 |
| band 4 mm | 0.172 | 3.5 kV/cm | 5.1 pF | 1.2 pF | ±1.3 kV/cm | 1.289 |
| band 8 mm | 0.205 | 4.2 kV/cm | 5.8 pF | 1.6 pF | ±1.5 kV/cm | 1.286 |
| **bands 20–53° (§1)** | **0.242** | **5.0 kV/cm** | **7.4 pF** | **1.3 pF** | | |

- **Wide bands give more field.** At 32.2 kV the bands from 20° gain from 6.8 kV/cm (ending at 45°) to 9.6 (ending at
  80°). Starting them at 25° or 30° instead of 20° costs 4–11 %.
- **The AH cores take about 13 % of the rings' field.** They sit at the shaft's potential next to the poles; an 8 mm
  band at 50° gives 4.8 kV/cm without them.
- **DC through glass drifts.** Borosilicate leaks: ρ ≈ 1e13 Ωm at 25 °C [IR], τ = ε/σ ≈ 7 min.
  - The glass beyond each ring follows the ring's potential, so the field rises toward the settled value.
  - "Settled" assumes the glass alone leaks. The retainer, the PEEK seats and charge collecting on the vacuum side of
    the wall all shift it, and the last can screen it.
  - The swing does neither, at a fifth of the field.

## 4. What the lock-down changes
- **The vessel** shrinks from the 90 mm placeholder to the 50 mm sphere. The earlier rings study (`sim/core_rings.py`)
  used the placeholder.
- **The AH sits on the axis**, not around the vessel.
- **The hub grows.** The flanges sit outside the vessel, outboard of the 160-turn coil, at |z| 72–80.
  - The tube layout's 120 mm hub put them at |z| 60.
  - So the tube grows by about 24 mm when its layout is refreshed.
- **The schematic's panel (b)** now draws the rings outside the glass, Dk + C_A on node 1, and the multiplier stage × 3 on
  node 4.
- **The cost sheet's core field 4,** DC on the rings, is the default. Its BOM has two ring electrodes and seven 100 pF
  capacitors, with no feedthroughs, and the vessel line is the 50 mm sphere with two MnZn cores.
- **Not yet updated:**
  - the tube layout (`sim/stack_sizing.py` hub_mm 120);
  - its 3-D model (`sim/tube_geometry.py`: the 90 mm placeholder vessel and the bicone; it also still puts Ca / Cb
    on the counter-rotor).

  That is a separate refresh. In the cost sheet the 24 mm adds about 3 to the shaft.

## Caveats
- **[RH]:**
  - the interface rating (it sets the bands);
  - the rings' leakage (it sets the multiplier's sag);
  - the retainer's and coupler's permittivity and extent;
  - the AH as one REF envelope (core, former and coil);
  - the borosilicate resistivity (it falls steeply with temperature).
- **[OC]:** the finite volumes. At half the cell the field moves 1.0 % and the strays 1–3 % (8 mm band, 50°).
- **Not modelled:**
  - the rings' leads through the retainer and coupler to the rotor's pump;
  - the field at the bands' edges inside the retainer (a rounded or graded edge is needed);
  - the settled state with the retainer's leakage;
  - charge on the wall.

## Open
Answered by the build (`sim/hub-rings-build-findings.md`), except the ratings, which the bench qualifies
(`docs/bench-test-rings.md`):
- **The glass–retainer interface's rating**, from the retainer's material and process. 1 kV/mm is the placeholder; the
  bands widen with it.
- **The rings' material** (copper foil or a fired coating), their edges' grading, and their leads.
- **The rings' and leads' leakage.** Less leakage brings the multiplier's stages back toward 7.4 kV each.
- **A test of the DC drift** on the glass: how far and how fast the field moves from as-connected to settled.
