# The rings as built: retainer, copper edges, leakage and stages — findings

**Sources:**
- **the build:** `sim/hub_rings_build.py` → `sim/hub_rings_build_results.json`;
- **the supply:** `sim/core_field.py` dc, now with ring A's own negative chain (`n_cw_a`);
- **the bench predictions:** `sim/hub_drift.py` → `sim/hub_drift_results.json`;
- **the figures:** `docs/figures/hub-rings-build.png` and `docs/figures/hub-bench-predictions.png`;
- **the test plan:** `docs/bench-test-rings.md`;
- **the spec:** `presets/hub-locked.json`, now carrying the build's record and materials.

**Designer's brief (2026-10-09):**
1. "the interface rating: suggest a current day machineable retainer that minimally affects the performance of both
   field";
2. "for initial proto a copper foil with rounded edges will be used. Afterwards fir[ed]-on coating can be used";
3. the leakage: "no idea how to judge";
4. "set up the bench test if possible. I expect the field to swing, with the power supplies";
5. and: "the multipliers can be added accordingly. we can go multistage as long as the rings's separation can hold it
   before breaking down onto eachother".

**In short:**
- **The retainer:** unfilled PEEK, with a 0.5 mm pocket over the glass filled void-free with silicone gel, and the G10
  coupler outside it.
- **The copper:** beads at the foil's edges, Ø3 mm at the polar edges and Ø2 mm at the equatorial edges.
- **The leakage:** about 100 GΩ per ring, set by the multiplier's own parts.
- **The stages:** the rings' separation is not what limits them; the beads in the gel are. Each polar bead faces the
  AH coil's end across the PEEK seat. At the design ratings this gives **two stages on ring B: 28.2 kV across, 6.9 kV/cm
  at the null**.
- **More stages:** they pay only if the bench qualifies higher ratings. Six stages (two on ring A, four on ring B)
  reach 13.3 kV/cm at 2 kV/mm along the glass and 8 kV/mm in the gel.
- **A correction:** the lock-down's record (three stages, 20–53°, 7.8 kV/cm) never had its edges checked. Its polar
  beads would run at 7.7 kV/mm in the gel.

## 1. The retainer: unfilled PEEK, with a gel-filled pocket
- **The proposal:**
  - **the material:** unfilled PEEK, natural grade, machined from annealed stock (e.g. Victrex 450G or Ketron 1000
    PEEK);
  - **the pocket:** 0.5 mm over the glass, with grooves for the rings' beads, vacuum-cast with a degassed two-part
    silicone gel (ε 2.9);
  - **the coupler:** G10, outside the PEEK (r 30–33 mm), not against the glass or the rings.
- **Why the gel:** the glass–retainer interface is what holds off the DC between the rings, and a dry machined fit
  leaves air gaps. The gel fills them, beds the beads, and takes up the expansion mismatch (PEEK about 47 ppm/K,
  borosilicate 3.3).
- **Why PEEK (minimal effect on both fields):**
  - **Magnetic:** PEEK is non-magnetic and non-conducting, so it has no effect on the AH field and carries no eddy
    currents.
  - **Electric:** the retainer's permittivity barely moves the field at the null (solved at the lock-down's bands, with
    the gel and the coupler). From PTFE (ε 2.1) to alumina (9.8) it moves +0.7 % to −1.5 % against PEEK; with no
    retainer at all (ε 1), +2.5 %.
  - **The strays follow ε:** each ring's stray to REF is 4.0 / 5.4 / 7.3 / 13.3 pF for PTFE / PEEK / G10 / alumina.
    They sit behind diodes, off the pump's swing.
  - **What matters more:** the interface (the gel), the material's DC conductivity (it sets the drift, §5), its
    moisture uptake, and that it machines and holds size.
- **The materials** [IR, datasheet-class; all non-magnetic]:

| material | ε_r | volume resistivity | strength (short-term) | water, 24 h | Tg / service | machining | here |
|:--|--:|--:|--:|--:|:--|:--|:--|
| **PEEK, unfilled** | **3.2–3.3** | **about 1e14 Ω·m** | **20–23 kV/mm** | **0.1 %** | **143 °C / 250 °C** | **excellent, stable** | **proposed** |
| PEI (Ultem 1000) | 3.15 | about 1e15 Ω·m | 25–33 kV/mm | 0.25 % | 217 °C / 170 °C | good; stress-cracks with some coolants | the alternative |
| PTFE | 2.1 | above 1e16 Ω·m | 20–60 kV/mm (thin) | < 0.01 % | — / 260 °C | creeps; will not hold the glass | no |
| POM-C (acetal) | 3.7–3.8 | about 1e13 Ω·m | 20 kV/mm | 0.2 % | — / about 100 °C | excellent | no: moisture, temperature |
| G10 / FR4 | 4.7–4.8 | about 1e13 Ω·m (dry) | 20 kV/mm | 0.1–0.2 % | about 130 °C | abrasive; fibres | outside only (the coupler) |
| Macor | 6.0 | about 1e14 Ω·m | 40 kV/mm (AC) | 0 | — / 800 °C | carbide tools; brittle | no: ε, cost |

- **Not advised against the glass:**
  - filled grades: carbon fill conducts, and glass fill raises ε and gives the interface a tracking path;
  - G10: its fibres would run along the interface between the rings.
- **PEI:** ten times PEEK's resistivity and a higher strength. It leaks less, so its interfaces charge more and settle
  more slowly: the field drifts +14 % instead of +9 % (§5).

## 2. The rings: copper foil with beaded edges
- **The foil:** 0.1 mm annealed copper [RH: the thickness].
  - The band is a spherical zone, doubly curved, so cut it as gores (12–16), overlap and solder them, and burnish them
    onto the glass.
  - Bond it with the gel itself, not an adhesive film: an adhesive's voids would sit right at the interface.
- **The edges:** a 0.1 mm foil's bare edge concentrates the field. So each edge carries a bead, a copper wire ring
  soldered along it and bedded in the gel (the retainer's grooves).
- **What the edges do,** at the lock-down's record (32.2 kV, ring B +19.0 kV). Peak field in the gel / in the glass,
  from a local solve (0.025 mm cells) bounded by the hub's solution:

| bead radius | equatorial edge | polar edge |
|--:|:--|:--|
| 0.25 mm | 9.0 / 7.2 kV/mm | 9.6 / 6.1 kV/mm |
| 0.5 mm | 6.8 / 5.0 | 8.2 / 4.0 |
| 1.0 mm | 5.1 / 3.2 | 7.75 / 2.1 |
| 1.5 mm | 4.3 / 2.5 | 8.05 / 1.3 |

- **The polar edge does not ease with a bigger bead.** It faces the AH coil's end (REF) across the 5.7 mm PEEK seat,
  and a bigger bead comes closer to it. Its peak sits on the bead's top, toward the AH.
  - At 20° from the axis it runs about 4.1 kV/mm in the gel per 10 kV on the ring (Ø2 mm bead), falling to 2.6 at
    40°.
  - So a ring at 15 kV needs its polar edge at 25.75° or more, with a Ø3 mm bead.
- **The lock-down's record is therefore not buildable** at 5 kV/mm in the gel: its polar beads would run at 7.75 kV/mm.
- **The beads of record:**
  - **Ø3 mm at the polar edges:** 4.99 kV/mm in the gel, at the limit by design;
  - **Ø2 mm at the equatorial edges:** 4.23 kV/mm, about 4.4 converged.
- **The local solve's convergence** (`convergence` in the results):
  - **Ø3 mm beads:** converged (no change at half the cell, −0.6 % with the box 1.5× as large);
  - **Ø2 mm beads:** read about 2.5 % low at the base cell. This affects the record's equatorial bead (13 % under its
    limit) and the qualified designs' Ø2 mm beads.
- **The fired-on coating later:** a fired film's edge is thin too. It needs the same beads (a wire ring soldered or
  fired on), or a resistive grading toward the pole (§ Open).

## 3. The leakage: about 100 GΩ per ring, from the multiplier's parts
- **How to judge it:** the leakage matters through the multiplier, whose stages sag when the rings leak. So list every
  path from each ring at its potential [IR, datasheet-class / RH]:

| path | per ring | basis |
|:--|--:|:--|
| through the PEEK retainer and seat to the AH core | 5e14 Ω | about 1e14 Ω·m, 7 mm over about 14 cm² of band |
| along the glass to the other ring | 1.6e15 Ω | borosilicate 1e13 Ω·m, the 1.5 mm shell across the gap |
| through the gel along the interface | 1e15 Ω | about 1e13 Ω·m, 0.5 mm across the band |
| the lead to the rotor's pump (PTFE-insulated, about 0.3 m) | 1e15 Ω | insulation resistance |
| the multiplier's diodes in reverse (about 7 kV each) | 3e11 Ω | tens of nA at a third of a 20 kV stack's rating; per stage |
| the multiplier's 100 pF capacitors' insulation | 5e11 Ω | above 1e11 Ω each; per stage |
| the rotor's HV assembly's surface, potted and dry | 1e12 Ω | [RH]; humid and unpotted, 1e10 or less |
| **in all** | **1.6e11 Ω** | the estimate used: **1e11 Ω (100 GΩ)** |

- **The rings' own insulation leaks about a thousand times less** (2e14 Ω per ring) than the electronics.
  - **The parts:** choose the diodes and capacitors by their leakage at the stage voltage.
  - **The HV assembly:** pot it and keep it dry.
  - **Then measure it** (bench phase 2).
- **What it does to the multiplier** (ring B's DC on n stages, 100 pF; ring A −13.2 kV):

| ring B on | 10 GΩ (the old placeholder) | 100 GΩ (the estimate) | 1 TΩ |
|:--|--:|--:|--:|
| 1 stage | +7.44 kV | +7.52 kV | +7.53 kV |
| 2 stages | +14.15 | **+14.96** | +15.05 |
| 3 stages | +19.04 | +22.17 | +22.55 |
| 4 stages | +21.39 | +28.92 | +29.99 |
| 5 stages | +21.42 | +34.96 | +37.35 |
| 6 stages | +19.97 | +40.07 | +44.58 |

- **At 10 GΩ** more stages stop helping above four. **At the estimate** each stage adds 5–7.5 kV up to six.
- **The diodes stay at 7.5 kV reverse at most**, and the pump's start-up gain at 1.180.

## 4. How many stages the rings hold
- **The limits** [RH: the ratings, presets ratings]:
  - **the designer's:** the gap along the glass between the rings holds the DC at the interface rating (1 kV/mm);
  - **the polar bead** holds the gel's rating (5 kV/mm) against the AH coil's end;
  - **the equatorial bead** holds it across the gap. Its field grows with the DC even at a fixed field along the
    glass: the gap widens, the bands narrow.
- **The balanced supply:** both rings on chains, so neither carries most of the DC. Ring A on a negative chain stacked
  on node 1's peak (`sim/core_field.py` `n_cw_a`): −20.7 kV on one stage, −28.0 kV on two.
  - The start-up gain stays at 1.169 / 1.166 (against 1.180).
  - The earlier decks are unchanged byte for byte.
- **The search:**
  - **the supplies:** 17 (ring B on 1–6 stages, and ring A on 1–2 negative stages with B on 1–6), at 100 GΩ;
  - **the ratings:** four pairs;
  - **the bands:** each design's bands from tables of the field at the null and of both edges.
  - **The edge tables:** the hub solved per mode and superposed per supply; ring A's edge is ring B's mirror.
  - **The check:** the best of each pair solved again directly, with the polar edge stepped out where needed.
- **At the design ratings** (1 kV/mm along the glass, 5 kV/mm in the gel):

| supply | across | bands | beads (polar / eq.) | at the null |
|:--|--:|:--|:--|--:|
| ring B on 1 | 20.7 kV | 22.5–66.2° | Ø2 / Ø2 mm | 5.6 kV/cm |
| **ring B on 2 (the record)** | **28.2 kV** | **25.75–57.7°** | **Ø3 / Ø2 mm** | **6.9 kV/cm** |
| ring A on 1 + B on 1 | 28.2 kV | 34.0–57.7° | Ø3 / Ø3 mm | 6.3 kV/cm |
| ring B on 3 | 35.4 kV | 39.0–49.4° | Ø3 / Ø3 mm | 6.3 kV/cm |
| ring A on 1 + B on 2 | 35.7 kV | 35.0–49.1° | Ø3 / Ø3 mm | 6.85 kV/cm |
| 42 kV and more | | | | the polar beads do not hold, or the gap leaves no band |

- **More stages lose at the design ratings:** each needs the polar beads further from the pole and a longer gap,
  and the bands left between them shrink faster than the DC grows.
- **The ratings to qualify** (best_edges; solved directly):

| ratings (interface / gel at a bead) | supply | across | bands | beads | at the null |
|:--|:--|--:|:--|:--|--:|
| **1 / 5 kV/mm (the record)** | **ring B on 2** | **28.2 kV** | **25.75–57.7°** | **Ø3 / Ø2 mm** | **6.93 kV/cm, 2.1 Pa** |
| 1 / 8 | ring A on 1 + B on 2 | 35.7 kV | 22.0–49.1° | Ø2 / Ø2 mm | 7.97 kV/cm, 2.8 Pa |
| 2 / 5 | ring B on 2 | 28.2 kV | 25.5–73.9° | Ø3 / Ø4 mm | 7.91 kV/cm, 2.8 Pa |
| 2 / 8 | ring A on 2 + B on 4 | 56.9 kV | 30.75–57.4° | Ø3 / Ø3 mm | 13.25 kV/cm, 7.8 Pa |

- **The answer to "go multistage as long as the separation holds":**
  - **Today:** at the ratings that can be designed to, the rings hold two stages, on ring B. Ring A stays on node 1's
    peak, as before.
  - **Six stages** (13.3 kV/cm, 1.9× the record) need both ratings qualified higher: 2 kV/mm along the glass and
    8 kV/mm in the gel.
  - **One higher rating alone** gains about 15 %.
  - The bench's first phase settles which row is built (`docs/bench-test-rings.md`).
- **The record's checks:**
  - **the AH:** ring B's average field to the AH cores is 1.8 kV/mm;
  - **the diodes:** 7.5 kV reverse at most;
  - **the strays:** 5.3 pF to REF and 1.3 pF between the rings;
  - **the start-up:** z 1.180;
  - **the ripple:** ring B 29 V p-p.

## 5. The bench test, and what the field should do
- **The plan:** `docs/bench-test-rings.md`:
  - (1) the hold-off on coupons and the sphere, which sets the stages;
  - (2) each ring's leakage;
  - (3) the DC drift on lab supplies;
  - (4) the rings on the pump's own supply.
- **The probe:** an electro-optic BGO sensor on a fibre, along the axis through a pumping tube at one pole.
- **What the field at the null should do** (`sim/hub_drift.py`, the record):
  - **the start-up:** 95 % in 0.22 s (27 cycles) from the seed;
  - **the 120 Hz swing:** 0.009 kV/cm p-p on 6.93 (0.13 %). With the DC supply, the multiplier smooths the pump's
    swing almost completely. The AH's ampere-turns swing 5.9 % p-p with 22 mF across each coil.
  - **the drift:** with the rings held at their DC, 6.93 kV/cm at switch-on, 7.54 at 1 h, 7.57 at 6 h (+9 %),
    half-way at 12 min. The leakage moves the potential along the glass and through the gel and the PEEK, from the
    electrostatic toward the conduction-settled state [OC]. The other materials bracket it: PEI +14 %, G10 +1 %
    (its σ/ε matches the glass's), PEEK at 40 °C +12 % in a quarter of the time.
- **"I expect the field to swing, with the power supplies":** the designer meant the ripple on the DC (2026-10-09).
  With the DC on the rings it is 0.13 %: 0.009 kV/cm p-p on 6.93 at 120 Hz. The bench's phase 4 measures it.

## 6. What changes
- **`presets/hub-locked.json`:**
  - **rings:** the record (bands, beads, supply, foil);
  - **new entries:** ratings, rings_leakage, interface_filler;
  - **retainer:** PEEK, PROPOSED; **coupler:** G10 outside;
  - **the open list.**
  - `sim/hub_rings_build.py` reads its materials, ratings and leakage from it.
- **`sim/hub_locked.py`:** keeps the lock-down's placeholder ε 4.7 (`EPS_RET_LOCKDOWN`), so its results stand as the
  lock-down's study.
- **`sim/core_field.py`:** ring A's negative chain (`n_cw_a`); every earlier deck is unchanged.
- **The schematic's panel (b):** ring B on two stages.
- **The cost sheet:**
  - the multiplier's stages and ring A's chain;
  - the sag factors at 100 GΩ;
  - the rings' field per kV;
  - the retainer and the gel in the BOM.

## Caveats
- **[RH]:**
  - the ratings (1 kV/mm along the glass, 5 kV/mm in the gel at a bead; 2 / 8 to qualify);
  - the leakage estimate;
  - the conductivities (datasheet-class, uncertain by an order of magnitude: the drift's size and times follow
    them);
  - the foil's thickness.
- **[OC]:**
  - the finite volumes and the local solves at the beads (§2 convergence);
  - the superposition of the modes (exact for the linear problem);
  - the tables' bilinear interpolation (each pair's best re-solved directly).
- **Not modelled:**
  - **the contact wedge** where a bead touches the glass. It is skipped in the sampling; the void-free gel is what keeps
    it benign, and the coupons test it.
  - **the AH side's edges** (the coil's end turns and former), which face the polar beads. Round or cap them.
  - **the rings' leads** through the retainer and the coupler.
  - **the gores' overlaps and joints.**
  - **the beads' field in the settled DC state.** Conduction then shares the DC by the conductivities, not the
    permittivities. The PEEK, ten times less conductive than the gel, should take more of it, which would ease the
    beads [IR]; not checked.

## Open
- **The ratings:** the bench's phase 1. They set the stages, from the record's two to the qualified six.
- **The AH seat's length (5.7 mm):** it sets how near the pole the bands may start, since the polar beads must clear
  the AH coil's end. A longer seat would let the bands start nearer the pole, but it moves the AH: the designer's call.
- **The fired-on coating's edges:** beaded, or graded by a resistive layer toward the pole.
