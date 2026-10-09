# The rings' beads settled, the contact wedge, the PEEK and the AH's end — findings

**Source:** `sim/hub_beads_settled.py` → `sim/hub_beads_settled_results.json` (about 25 min on four cores).

**Status:**
- [OC] the electrostatics at switch-on and the steady conduction once settled;
- [IR] the grids, the geometry as drawn (`docs/drawings/DCCREG-HUB-201`) and the conductivities (datasheet-class,
  `sim/hub_drift.py` SIG);
- [RH] the ratings: 5 kV/mm in the gel at a bead and 1 kV/mm along the glass (`presets/hub-locked.json` ratings).
- The grooves' full-round tops and the AH end's radius recommended here are **PROPOSED**. The retainer's dimensions
  are OPEN in the record.

## Headline
- **The field at the null as built is 7.62 kV/cm at switch-on, not 7.10** (§2).
  - The record's 7.10 was solved for the bands alone. The beads reach past each band's edge toward the gap.
  - At half the cell it is 7.65 (+0.4 %).
  - It settles to 8.20 kV/cm at 25 °C (`sim/hub_drift.py`, now with the beads; 8.21 by the settled solve here), and to
    8.27 with the glass at 40 °C.
  - The pressure at the null: 2.57 Pa at switch-on, 2.98 Pa settled.
  - `sim/hub_rings_build.py` (its as-built step) and `sim/hub_drift.py` now carry the beads.
- **As drawn, the beads hold their rating at switch-on.** The gel peaks at 4.98 kV/mm at the polar bead and 4.46 at
  the equatorial; the glass under them at 1.46 and 3.01.
  - The record's 4.85 / 4.36 filled the whole local box with gel. The drawing's grooves bring the PEEK (ε 3.2, above
    the gel's 2.9) within 0.5 mm of the bead.
  - **The polar bead sits at its rating,** 0.4 % under it.
- **Settled at 25 °C, the beads relax.** The gel then peaks at 0.69 / 1.88 kV/mm and the glass at 0.20 / 1.19. The
  PEEK, ten times less conductive than the gel, takes the DC instead:
  - beside the drawn grooves' square top corners: 7.1 kV/mm at 0.05 mm off the gel, 4.3 at 0.25 mm. A sharp corner
    in the model grows without limit as the cells shrink;
  - at the AH end's square corner: 7.7 at 0.05 mm, 4.5 at 0.25 mm;
  - across the AH seat, on average: 2.3 kV/mm (1.6 at switch-on).
- **The contact wedge holds in every state solved** (§4).
  - Its field stays finite at the contact: the thin gap ties the glass's surface to the bead [OC].
  - The voltage across the gap is at most 0.51 of air's Paschen breakdown for a void of that gap (the equatorial bead,
    the glass at 40 °C), with the gel in place.
  - **Corrected 2026-10-09** (`sim/hub-joints-findings.md` §4): this said a void at the contact would not discharge.
    That holds at switch-on only. A void in the gel's place carries more; once settled, in service, a sealed void
    reaching 0.5 mm from an equatorial contact is at 0.99 of the breakdown and one reaching 1 mm at 1.46. The polar
    contacts hold (at most 0.33). So the gel must fill the equatorial contacts' wedges void-free.
- **The equatorial beads set a condition on the materials** (§7). Settled, their gel stays within 5 kV/mm only while
  σ_glass ≤ 4.1 σ_gel (the drawn grooves; 4.4 with the recommended).
  - With the glass at 40 °C (5.4 × its 25 °C conductivity, the gel held) the gel reaches 6.15 kV/mm.
  - The polar beads do not care: 0.64–0.70 kV/mm across the whole range.
  - Where the hub's own heat puts the glass, and so the margin: `sim/hub-thermal-findings.md`.
- **The recommendations** [IR, PROPOSED]:
  - **Machine the grooves' tops full-round:** a ball-end cut concentric with the bead, 1.0 mm of gel over it.
    - That is 5 mm wide and 4 mm deep at the polar edge, 4 mm and 3 mm at the equatorial.
    - The gel at switch-on is 4.99 / 4.45 kV/mm. The PEEK beside the grooves, settled, is 4.1 kV/mm at 0.05 mm
      (7.1 drawn).
    - The equatorial beads' limit rises to σ_glass ≤ 4.4 σ_gel.
  - **Round the AH end's outer corner to at least 1.5 mm, at REF.** Either a rounded former flange coated
    conductive and tied to the core, or a REF end ring over the coil's last turns.
    - It gives 4.5 kV/mm settled at 0.05 mm, against 7.9 square and 5.2 at 0.75 mm.
  - **Keep the seat at 5.7 mm.** With the round grooves and the rounded end, its PEEK peaks at 4.5 kV/mm settled.
    That is about a fifth of PEEK's 20–23 kV/mm short-term strength (`sim/hub-rings-build-findings.md` §1); by the gel
    rating's own rule (a third of it) about 7 kV/mm would be allowed [RH].
  - **Measure σ_gel and σ_glass at the hub's temperature on the bench** (phase 3 and its 40 °C repeat). The
    equatorial beads need σ_glass ≤ 4 σ_gel there.

## 1. The model and its gates
- **The geometry, as drawn** (`docs/make_rings_drawing.py`):
  - each edge has its own bead: Cu wire Ø3 mm at the polar edge (26.25°), Ø2 mm at the equatorial (55.71°);
  - each bead sits in a gel-filled groove, with walls ρ + 0.5 mm off the bead's centre-line and a flat top
    2ρ + 0.5 mm over the contact;
  - the 0.5 mm gel pocket over the glass; the PEEK retainer; the G10 coupler r 30–33 mm;
  - the AH as the register's REF envelope (r ≤ 11.45 mm, |z| ≥ 30.7 mm), the flanges and the shaft at REF.
- **Four solves** [IR: the grids]:
  - **the hub:** 0.25 mm cells, both modes, ring A at −14.96 kV and ring B at +14.96 kV. Switch-on uses ε; settled
    uses σ in its place, in `sim/core_rings.py`'s solver. The vacuum carries no current, so a vanishing σ there [IR];
  - **each bead's box:** 0.025 mm cells over ±4 mm, its edges from the hub, sampled along the bead's normals as the
    record's `edge_peak`;
  - **the wedge's box:** 0.0025 mm cells over ±0.5 mm about the contact, its edges from the bead's box;
  - **the AH end's box:** 0.025 mm cells over ±4 mm about the corner, its edges from the hub.
- **The states:** switch-on (ε: glass 4.6, gel 2.9, PEEK 3.2, G10 4.7); settled with glass and gel at 1e-13 S/m, PEEK
  1e-14, G10 1e-13 and air 2e-14 (25 °C); settled with the glass at 5.4e-13 (40 °C, the gel held).

| gate | result | pass |
|:--|:--|:--|
| G-REC: the record's own bead path (`edge_peak`) | gel 4.851 / 4.355, glass 1.415 / 2.976 kV/mm against the record's 4.851 / 4.355 and 1.415 / 2.972 | ✔ (≤ 0.01) |
| G-BANDS: the hub without beads, at switch-on | 7.100 kV/cm against the record's bands-alone 7.100 | ✔ (≤ 0.5 %) |
| G-SET: the hub as drawn, settled, against `sim/hub_drift.py`'s 6 h | 8.205 against 8.199 (25 °C); 8.275 against 8.268 (40 °C glass) | ✔ (≤ 0.5 %) |
| G-MESH: the null as drawn at 0.25 → 0.125 mm | 7.618 → 7.651 kV/cm (+0.43 %) | — |
| G-WEDGE: the gel's field from the interface condition against V / g across a resolved gap (s 0.2–0.45 mm) | within 3–10 %, e.g. 2.94 / 3.07 kV/mm at s 0.2 mm (equatorial, switch-on); 18 % at one point where the field is 0.5 kV/mm | — |

## 2. The field at the null, with the beads
| hub | switch-on | settled, 25 °C | settled, glass 40 °C |
|:--|--:|--:|--:|
| the bands alone (the record's basis until now) | 7.10 kV/cm | 7.83 | 8.08 |
| **as drawn: each edge with its bead in its groove** | **7.62** | **8.21** | **8.27** |
| the grooves full-round, 1.0 mm of gel (recommended) | 7.61 | 8.25 | 8.29 |

- **Why the beads add 7 %:** they are copper at the band's own potential and reach past its edge toward the gap [OC].
  - The equatorial bead (Ø2 mm) brings ring B's edge 0.43 mm nearer the midplane, out to r 22.5 mm (the foil ends at
    r 20.65 mm).
  - The edges carry the densest charge, nearest the null.
  - The interface rating does not change: it is the average along the glass between the contacts, which stays
    29.9 kV over 29.9 mm.
- **The build's own solver agrees:** its `hub_beads` (one bead size at both edges) gives 7.55 kV/cm with Ø2 mm beads
  and 7.75 with Ø3 mm; the drawing's mix gives 7.62.
- **The pressure** ε₀E²/2: 2.57 Pa at switch-on, 2.98 Pa settled (25 °C) [OC].
- **The drift with the beads** (`sim/hub_drift.py`, PEEK and gel at 25 °C): 7.62 → 7.95 (10 min) → 8.18 (1 h) →
  8.20 kV/cm (6 h), +7.6 %. It is half-way at 7.6 min and at 90 % at 39 min; two exponentials fit it with τ 5.7 and
  23.6 min.
  - The bands alone rose 7.10 → 7.82 (+10 %), half-way at 13 min. The gel in the grooves settles faster (ε/σ 4.3 min).

## 3. The beads
ring B's beads (ring A's are their mirror images), kV/mm:

| | gel, polar | glass, polar | gel, equatorial | glass, equatorial |
|:--|--:|--:|--:|--:|
| the record's box (gel throughout) | 4.85 | 1.41 | 4.36 | 2.97 |
| **as drawn, switch-on** | **4.98** | 1.46 | **4.46** | 3.01 |
| as drawn, settled, 25 °C | 0.69 | 0.20 | 1.88 | 1.19 |
| as drawn, settled, glass 40 °C | 0.67 | 0.35 | **6.15** | 4.86 |
| full-round, 1.0 mm of gel: switch-on | 4.99 | 1.46 | 4.45 | 3.02 |
| full-round, 1.0 mm of gel: settled, 25 °C | 0.65 | 0.17 | 1.71 | 1.06 |
| full-round, 1.0 mm of gel: settled, glass 40 °C | 0.64 | 0.32 | 5.87 | 4.65 |

- **Why the polar beads relax but the equatorial ones may not** [OC]:
  - settled, the polar cap of glass and gel beyond the polar bead carries almost no current: its only way out is the
    PEEK seat to the AH, ten times less conductive. So it floats to the ring's potential, and the seat takes the
    15 kV;
  - beyond the equatorial bead the glass carries the leakage current across the gap. Its surface potential falls away
    from the bead by the glass's own conduction. The gel between the bead and that surface must then hold the
    difference, the more so the better the glass conducts relative to the gel (§7).

## 4. The contact wedge
On the bead's bare-glass side (toward the pole for the polar bead, toward the equator for the equatorial), at a
distance s along the glass from the contact. The gap g(s) is about s²/2ρ. The gel's field is taken at the glass from
the interface condition; ΔV is the voltage across the gap.

| | E_gel peak along the wedge | ΔV / Paschen, largest |
|:--|:--|:--|
| polar, switch-on | 1.47 kV/mm at s 0.45 mm (1.21 at 0.05) | 0.21 at s 1.0 mm (0.52 kV across 0.42 mm) |
| polar, settled 25 °C | 0.20 at 0.8 mm | 0.04 |
| polar, settled, glass 40 °C | 0.84 at 0.025 mm | 0.04 |
| equatorial, switch-on | 2.94 at 0.2 mm (2.73 at 0.05) | 0.36 at 0.6 mm (0.54 kV across 0.21 mm) |
| equatorial, settled 25 °C | 1.07 at 0.45 mm | 0.17 |
| equatorial, settled, glass 40 °C | 14.1 at 0.05 mm (7.9 at 0.2) | **0.51** at 0.3 mm (0.27 kV across 48 µm) |

- **The wedge is not singular** [OC].
  - Near the contact the gap is so thin that it ties the glass's surface to the bead, over a length of the bead's own
    size: where the gap's conductance per area (k_gel / g) exceeds the glass's (k_glass / s), at s below about
    2ρ k_gel / k_glass. Here k is ε at switch-on and σ settled.
  - The gel's field at the contact then tends to (k_glass / k_gel) × the glass's normal field there: finite.
  - Where the gap is resolved (s 0.2–0.45 mm), V / g across it agrees within 3–10 %.
- **The 14 kV/mm** with the glass at 40 °C stands across a gap of 1.3 µm at s 0.05 mm: 14 V. Nothing can avalanche
  across that [OC]. The gel's peak on the bead's surface (6.15 kV/mm, §3) is the stress that counts against its
  rating.
- **Paschen** (air at 1 atm; A 15 /(cm·Torr), B 365 V/(cm·Torr), γ 0.01, its 0.31 kV minimum held below the
  minimum's gap) [IR]:
  - at most 0.51 of the breakdown with the gel in place.
  - **Corrected 2026-10-09** (`sim/hub-joints-findings.md` §4): these lines read "so even a void at the contact would
    not discharge" and "the void-free casting matters at the beads' tops, not in the wedge". The ratio above is the
    gel-filled gap's voltage, not a void's. Re-solved with a void in the wedge, the equatorial contact holds at
    switch-on (0.65 for a void reaching 1 mm) but not once settled: 0.99 for a sealed void reaching 0.5 mm in service,
    1.46 for 1 mm. The void-free casting matters at the beads' tops and at the equatorial contacts alike.

## 5. The PEEK and the AH's end
- **At the hub's scale** (0.25 mm cells, two cells and more off any conductor):
  - the seat's mean is 1.64 kV/mm at switch-on and 2.33 settled (2.52 with the glass at 40 °C). The 15 kV moves into
    the seat as the polar cap settles to the ring's potential;
  - its peak: 3.17 at the AH's corner at switch-on; 3.92 settled, beside the drawn polar groove's top corner (3.74 with
    the full-round grooves, then at the AH's corner).
- **The AH end's corner** (its box; the full-round grooves' hub on its edges), kV/mm in the PEEK at 0.05 / 0.1 /
  0.25 mm off the conductor:

| the corner's radius | switch-on | settled, 25 °C | settled, glass 40 °C |
|:--|:--|:--|:--|
| 0 (the register's square envelope) | 6.77 / 5.24 / 3.88 | 7.87 / 6.11 / 4.58 | 7.90 / 6.14 / 4.60 |
| 0.75 mm | 4.42 / 4.11 / 3.55 | 5.22 / 4.84 / 4.20 | 5.24 / 4.86 / 4.22 |
| **1.5 mm** | 3.71 / 3.52 / 3.22 | **4.48** / 4.25 / 3.89 | 4.51 / 4.28 / 3.92 |
| 2.5 mm | 3.28 / 3.13 / 2.93 | 4.03 / 3.85 / 3.61 | 4.08 / 3.89 / 3.65 |

- **The settled state is the AH end's worst** [OC]: the seat then holds the ring's full 15 kV.
- **The cap:** the end of the coil (0.8 mm wire, `sim/hub-thermal-findings.md` §1) has corners of about 0.4 mm, so
  the AH needs a REF surface of its own over its end [IR]. Two ways:
  - the G10 former's end flange (|z| 30.7–31.35 mm) turned to a 1.5 mm outer radius and coated conductive (graphite or
    silver paint), tied to the core and the coil's cold end;
  - or a brass or copper end ring with a 1.5 mm full-round edge over the last turns, at the same potential.
- **The seat's length stays 5.7 mm** [IR]: with the cap, the PEEK holds 4.5 kV/mm settled. A longer seat would ease it
  and weaken the cusp; a shorter one is not needed.
- **Beside the grooves** (the beads' boxes, PEEK at 0.05 / 0.25 mm off the gel, settled 25 °C):

| groove | polar | equatorial | the polar gel at switch-on |
|:--|:--|:--|--:|
| drawn: square top | 7.14 / 4.26 | 6.60 / 3.82 | 4.98 |
| full-round, 0.5 mm of gel | 4.12 / 3.59 | 4.26 / 3.56 | 5.05 |
| full-round, 0.75 mm | 4.09 / 3.61 | 4.07 / 3.43 | 5.01 |
| **full-round, 1.0 mm** | **4.11 / 3.64** | **3.92 / 3.35** | **4.99** |

- **Why 1.0 mm:** the full-round top removes the corner, but it brings the PEEK (ε 3.2) round the bead's top and lifts
  the polar gel at switch-on. More gel over the bead takes it back under the rating [IR].

## 6. The interface and the air
- **Along the glass between the rings:** the average stays 0.99 kV/mm, which is the rating's measure.
  - Its peak at the hub's scale is 2.25 kV/mm at switch-on, at 56.6°, just past the equatorial bead's contact.
  - Settled it is 1.55 at 59.8° (25 °C) and 2.37 at 56.6° (glass at 40 °C).
- **The air outside the coupler** (within 2 mm of the hub, in the hub model's cage at r 162 mm and vanes at |z| 110 mm):
  0.55 kV/mm at switch-on, beside the rings' equatorial edges (r 33.4, z 12.9 mm), and 0.23 settled.
  - The coupler's surface reaches 6.2 kV at switch-on and 2.6 kV settled.
  - That is about a sixth of air's 3 kV/mm [IR], so the coupler's 33 mm radius holds. A REF part nearer than the cage
    would raise it.

## 7. The settled beads against the glass's conductivity
The gel at 1e-13 S/m, the glass at a multiple of it; kV/mm in the gel at the bead, settled:

| σ_glass / σ_gel | 0.3 | 1 | 2 | 3 | 4 | 5.4 | 8 |
|:--|--:|--:|--:|--:|--:|--:|--:|
| equatorial, drawn | 1.47 | 1.88 | 2.76 | 3.94 | 4.95 | 6.15 | 7.92 |
| equatorial, full-round 1.0 mm | 1.34 | 1.71 | 2.53 | 3.69 | 4.68 | 5.87 | 7.66 |
| polar, drawn | 0.70 | 0.69 | 0.68 | 0.68 | 0.67 | 0.67 | 0.67 |
| the null, drawn (kV/cm) | 8.09 | 8.21 | 8.26 | 8.27 | 8.28 | 8.28 | 8.26 |

- **The limit at 5 kV/mm:** σ_glass ≤ 4.06 σ_gel with the drawn grooves, and ≤ 4.37 σ_gel with the full-round ones
  (interpolated).
- **Both conductivities are datasheet-class** and both fall with temperature [IR]. Borosilicate's activation energy
  is about 0.9 eV (the record's two points); a silicone gel's is usually lower [RH]. So a warmer hub raises the ratio.
- **The ways to hold it:**
  - keep the glass cool: `sim/hub-thermal-findings.md`;
  - choose a gel at least a quarter as conductive as the glass at the hub's temperature;
  - or grade the glass beyond the equatorial bead with a resistive layer, the option docs/rings-design.md already keeps
    for the fired-on coating's edges.
  - The bench's phase 3 measures the ratio: E∞ / E(0) and the τᵢ (`docs/bench-test-rings.md`).

## Caveats
- **[IR] axisymmetric:** the gores' overlaps, the solder joints, the lead to each equatorial bead and any split in the
  retainer are not modelled.
- **[IR] the conductivities** are datasheet-class and held at 25 °C except the glass's 40 °C case. Surface
  conduction along the interfaces and space charge in the gel are not modelled; the settled state is ohmic.
- **[IR] the box edges** come from the coarser solve around them. The AH end's peak is read only within 2.5 mm of the
  corner, since nearer the box's edges the hub's square corner, held there, would show.
- **[RH] the ratings:** 5 kV/mm in the gel and, by its rule, about 7 kV/mm in PEEK are heuristics until the bench's
  phase 1 qualifies them.
- **[IR] Paschen's constants** are the textbook's for air; the gel's own voids may hold gas at other pressures.
