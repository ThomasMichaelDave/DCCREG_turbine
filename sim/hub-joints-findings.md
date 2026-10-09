# The rings' joints and voids: the gores' laps, the bead rings' closing joints, a void at a contact — findings

**Source:** `sim/hub_joints.py` → `sim/hub_joints_results.json` (about 25 min on an idle machine).

**Status:**
- [OC] the field laws, the D and J continuity at the interfaces, and the half-cylinder and hemisphere results;
- [IR] the geometry of each joint, the cells, the void's conduction bounds and the conductivities;
- [RH] the gel's 5 kV/mm rating (`sim/hub_rings_build.py` E_FILL_DESIGN), the foil's ramp over a lap, and Paschen's
  constants for a void.
- It answers the ledger's open item "the gores' overlaps and joints" (`docs/ledger/DCCREG-design-ledger.md` §5.2).
- It corrects `sim/hub-beads-settled-findings.md` §4: a void at the equatorial contact is not safe once the DC has
  settled (§4 here).

## Headline
- **A void at the equatorial beads' contact discharges once the DC has settled** (§4).
  - The bead study took the voltage across the wedge's gap from the gel-filled solve, and a void carries more.
  - At switch-on a void holds, at most 0.65 of Paschen's breakdown.
  - Settled, in service (σ_glass / σ_gel 2.4), a sealed void reaching 0.5 mm from the contact is at 0.99, and one
    reaching 1 mm at 1.46. A sealed void conducts next to nothing, so the insulating bound is the one to hold to [IR].
  - **So the gel must fill each equatorial contact's wedge void-free**, as it must the beads' tops.
  - The polar contacts hold in every state (at most 0.33).
- **The gores' laps hold if the cut edges are dressed and the laps are bedded in the gel** (§2).
  - The upper gore's free edge is a 0.1 mm step on the band's outer face. At switch-on the gel over the foil runs at
    1.20 kV/mm, and the step raises it:
    - as cut, with a corner radius of 5–10 µm: 4.4–3.5 kV/mm, 88–70 % of the rating;
    - dressed round to 25–50 µm: 2.7–2.3 kV/mm;
    - **under a solder fillet 0.2–0.4 mm wide: 1.9–1.6 kV/mm.**
  - A burr stands proud of the edge and is worse; deburr every cut edge [OC: a boss multiplies the field].
  - Once settled the gel over the foil carries a tenth of its switch-on field, so the steps fall to 0.4 kV/mm or less.
  - The crevice under each lap, between the upper gore's ramp and the glass, holds gel-filled: at most 2.8 kV/mm next
    to the beads at switch-on, and 2.3 kV/mm in service.
  - A void in that crevice holds at switch-on (0.29 of Paschen) and in service (0.66). With the glass at 40 °C
    (5.4 ×), the beads' own limit is past and a long void (a 1 mm ramp) reaches 1.22. So the laps near the equatorial
    beads must be void-free as well.
- **The bead rings' closing joints** (§3): a joint left proud raises the bead's field by about 1 + 3.7 δ / w (a bulge
  δ high over its width w).
  - **The equatorial rings** run 12 % under the rating and take a joint dressed to δ / w ≤ 0.03: 0.03 mm over 1 mm.
  - **The polar rings** run 0.3–0.4 % under it with the AH ends square, so no joint a file can make is safe there.
    Rounding the AH ends to 1.5 mm at REF (`docs/rings-design.md` §2, proposed) gives them 2.3–2.4 % (δ / w ≤ 0.006),
    and 2.5 mm gives 4.8–5.0 %.
  - So the polar rings are best made seamless: turned from Cu-ETP bar, or brazed and then turned to the round [IR].
  - A solder ball triples the field at its tip [OC]: none may stand on any bead.

## 1. The faces
The normal fields on ring B's two faces (ring A is its mirror image), from the hub's solve as drawn (0.25 mm cells)
between the beads and from each bead's box (0.025 mm cells) near it. The gel over the foil takes the PEEK's D (or J
once settled) [IR]. kV/mm:

| state | gel over the foil, between the beads | glass under it, between | glass under the foil at 0.1 / 0.5 / 1 / 2 mm from the polar contact | from the equatorial contact |
|:--|--:|--:|:--|:--|
| switch-on | 1.20 | 0.13–0.30 | 0.83 / 0.58 / 0.38 / 0.27 | 1.66 / 1.06 / 0.74 / 0.45 |
| settled, σ_glass / σ_gel 1 (25 °C) | 0.12 | ≤ 0.05 | 0.13 / 0.08 / 0.04 / 0.02 | 0.73 / 0.41 / 0.24 / 0.09 |
| **settled, 2.4 (in service)** | **0.12** | **≤ 0.06** | **0.13 / 0.08 / 0.04 / 0.02** | **1.20 / 0.66 / 0.38 / 0.14** |
| settled, 4 (about the equatorial beads' limit) | 0.12 | ≤ 0.08 | 0.14 / 0.08 / 0.04 / 0.02 | 1.76 / 0.96 / 0.54 / 0.20 |
| settled, 5.4 (the glass at 40 °C) | 0.12 | ≤ 0.08 | 0.15 / 0.08 / 0.05 / 0.02 | 2.28 / 1.23 / 0.70 / 0.26 |

- **The glass under the foil is quiet between the beads**, and its field rises toward the equatorial edge, where the
  band faces the gap between the rings.
- **Within about 0.5 mm of a contact the foil runs under its bead and its solder**, so a lap's crevice there is
  buried. The combinations below take the near-bead fields from 0.5 mm on.

## 2. The lap
**The cut** [IR]: across a seam (x along the azimuth, y out of the glass; the seam runs along the meridian, so the cut
is two-dimensional).
- The lower gore lies on the glass, its cut edge at x = 0. The upper gore lies over it for the 1 mm of the overlap,
  then ramps down onto the glass over L_t (0.25, 0.5 or 1 mm, the foil draped over the lower gore's edge [RH]).
- The gel's pocket reaches 0.5 mm over the glass, the PEEK beyond.
- Unit far fields, held as a fixed flux density in the PEEK and at the glass's inner surface, so a void keeps its own
  share of the series stack [IR]. Nested boxes to 0.5 µm (0.2 µm at the sharpest corner).
- **The solver's check:** a half-cylinder ridge gives 1.993 against the exact 2 [OC]. The conductor's surface sits
  where it truly lies between cells (Shortley–Weller), and the surface field is the normal field extrapolated to it
  from 3–9 cells out.

**The step on the outer face** (the upper gore's free edge), the gel's peak over its far field:

| the edge | β at switch-on | β settled | the gel at switch-on, 1.20 kV/mm × β |
|:--|--:|--:|--:|
| as cut, corner r 5 µm | 3.66 | 3.58 | 4.39 kV/mm |
| as cut, r 10 µm | 2.94 | 2.87 | 3.52 |
| dressed, r 25 µm | 2.25 | 2.20 | 2.70 |
| dressed round, r 50 µm (half the foil) | 1.89 | 1.84 | 2.26 |
| **a solder fillet 0.2 mm wide** | **1.61** | **1.57** | **1.93** |
| a solder fillet 0.4 mm wide | 1.32 | 1.28 | 1.58 |

- **The mesh:** at half the cells the r 10 µm step reads 2.954 against 2.935 (+0.6 %).
- **The PEEK** 0.3 mm over the step sees 1.11 × its own far field at switch-on (1.01 settled).
- **The upper gore's bend** where it starts down its ramp, a sharp 11° kink in the model, reads 1.38. A real bend is
  rounded, so this is an upper bound.
- **Settled** the gel over the foil carries 0.12 kV/mm, so every step stays at or under 0.44 kV/mm.

**The crevice under the ramp,** against the lower gore's cut edge, per kV/mm of the glass's field under the flat foil:

| fill | L_t | switch-on | settled 1 | **settled 2.4** | settled 4 | settled 5.4 |
|:--|--:|--:|--:|--:|--:|--:|
| gel: its peak, 5 µm off the conductor | 0.25 mm | 2.07 | 1.56 | **2.58** | 3.44 | 4.13 |
| | 0.5 mm | 2.40 | 1.76 | **3.08** | 4.08 | 5.20 |
| | 1 mm | 2.66 | 1.91 | **3.48** | 4.64 | 5.70 |
| a void, open air's σ: kV across it | 0.5 mm | 0.12 | 0.12 | **0.17** | 0.19 | 0.20 |
| | 1 mm | 0.17 | 0.18 | **0.27** | 0.32 | 0.35 |
| a void, insulating: kV across it | 0.5 mm | (= open air) | 0.24 | **0.24** | 0.24 | 0.24 |
| | 1 mm | | 0.46 | **0.46** | 0.46 | 0.46 |

- **The gel's peak sits at the lower gore's cut-edge corner on the glass**, a corner where the field grows about as
  r^(-1/3) [OC]: at half the cells (2.5 µm off it) the 5.4 case reads 6.2 against 5.2. A cut edge's own radius, 5–10
  µm, bounds it, so the table quotes 5 µm.
- **An insulating void's voltage** does not depend on the conductivities' ratio: the glass alone conducts around it.
  At a tenth of its σ it reads the same (0.23884 against 0.23883 kV per kV/mm).
- **Each void is set against Paschen's breakdown** of its gap, the shortest path from the glass to the conductor.

**Combined** with §1's fields (kV/mm, or the largest voltage over Paschen's breakdown for a void), L_t 0.5 / 1 mm:

| state | gel-filled, between the beads | gel-filled, near the beads | void (open air / insulating), near the beads |
|:--|--:|--:|:--|
| switch-on | 0.72 / 0.80 | 2.54 / 2.81 | 0.22 / 0.29 |
| settled 1 | 0.09 / 0.10 | 0.73 / 0.79 | 0.09 / 0.12; 0.22 / 0.41 |
| **settled 2.4** | **0.20 / 0.22** | **2.03 / 2.30** | **0.22 / 0.32; 0.35 / 0.66** |
| settled 4 | 0.31 / 0.35 | 3.90 / 4.44 | 0.37 / 0.58; 0.50 / 0.95 |
| settled 5.4 | 0.44 / 0.48 | 6.39 / 7.00 | 0.51 / 0.83; 0.65 / 1.22 |

- **In service everything holds:** 2.3 kV/mm gel-filled, and 0.66 of Paschen for an insulating void under a 1 mm ramp.
- **At 5.4** (the glass at 40 °C) a gel-filled crevice next to the equatorial bead exceeds the rating, as that bead
  itself does (6.15 kV/mm, `sim/hub-beads-settled-findings.md` §7). The laps add no new limit on the conductivities.
- **Between the beads** the laps are far from any limit in every state.

## 3. The bead rings' closing joints
- **The joint as a ridge** [IR]: a joint left proud is a collar around the wire. Its height and width are far below
  the wire's radius, so locally it is a ridge on a flat conductor in the bead's own field.
- **The check:** a half-cylinder ridge, 1.993 against the exact 2 [OC]. A hemispherical boss, a solder ball, gives 3
  [OC: the classical result].

| δ / w | 0.01 | 0.03 | 0.1 | 0.3 |
|:--|--:|--:|--:|--:|
| β (a cosine ridge) | 1.037 | 1.113 | 1.390 | 2.230 |

- **So β ≈ 1 + 3.7 δ / w** for a shallow joint. The cell halved moves the 0.03 ridge by 0.05 %.
- **What each bead can take** (switch-on, its peak in the gel, against 5 kV/mm [RH]); the polar bead re-solved with the
  AH ends rounded (the hub and the bead's box with the same grooves; the drawn grooves / the full-round, 1.0 mm of gel):

| bead | its peak | margin | the joint may rise, δ / w |
|:--|--:|--:|--:|
| equatorial, Ø2 | 4.46 / 4.45 kV/mm | 12 % | 0.03 |
| polar, Ø3, the AH ends square (the register) | 4.980 / 4.986 | 0.4 / 0.3 % | 0.001: none |
| polar, the AH ends rounded 1.5 mm (proposed) | 4.884 / 4.890 | 2.4 / 2.3 % | 0.006 |
| polar, the AH ends rounded 2.5 mm | 4.764 / 4.771 | 5.0 / 4.8 % | 0.013 |

- **Once settled** the polar beads run at 0.61–0.69 kV/mm and the joints do not matter.
- **The equatorial joints** also take the settled condition on the conductivities (`sim/hub-beads-settled-findings.md`
  §7), less their own β: a joint at δ / w 0.03 lowers the beads' limit from σ_glass ≤ 4.1 σ_gel to about 3.5 (the
  settled peak rises 1.01 kV/mm per unit of the ratio there, `sim/hub_beads_settled_results.json` sweep) [IR].

## 4. A void at a bead's contact
**The method:** the bead's box and its contact's nested box of `sim/hub_beads_settled.py` (as drawn), re-solved with
the wedge between the bead and the bare glass filled with a void (ε 1 at switch-on; settled, open air's σ or an
insulator) out to s_v from the contact. At each s, the voltage between the bead and the glass's surface is set against
Paschen's breakdown of the gap there [IR].

**The largest voltage over Paschen's breakdown**, for a void reaching 0.25 / 0.5 / 1 mm from the contact:

| state | polar: open air | polar: insulating | equatorial: open air | equatorial: insulating |
|:--|:--|:--|:--|:--|
| switch-on | 0.12 / 0.25 / 0.33 | (= open air) | 0.33 / 0.52 / 0.65 | (= open air) |
| settled 1 (25 °C) | 0.02 / 0.04 / 0.07 | 0.05 / 0.11 / 0.21 | 0.16 / 0.29 / 0.42 | 0.34 / 0.73 / **1.35** |
| **settled 2.4 (in service)** | **0.03 / 0.06 / 0.08** | **0.05 / 0.10 / 0.16** | **0.37 / 0.55 / 0.71** | **0.56 / 0.99 / 1.46** |
| settled 4 | 0.04 / 0.06 / 0.08 | 0.05 / 0.09 / 0.13 | 0.56 / 0.76 / 0.91 | 0.76 / **1.18 / 1.56** |
| settled 5.4 (40 °C) | 0.04 / 0.06 / 0.07 | 0.05 / 0.08 / 0.11 | 0.71 / 0.92 / **1.06** | 0.90 / **1.30 / 1.63** |

- **Where:** the equatorial bead's worst point is 0.2 mm from the contact, a 21 µm gap carrying 0.35 kV in service
  (0.5 mm void, insulating), against Paschen's 0.35 kV there.
- **Why a longer void is worse:** with the gel in place, the gel ties the glass's surface to the bead near the contact.
  A void cuts that tie, and the further it reaches, the further the glass's surface under it floats from the bead.
- **The bounds** [IR]:
  - a sealed void's own conduction is ionisation-limited, about 3e-17 A/m², ten decades under the glass's settled
    current;
  - so open air's σ (2e-14 S/m) is the optimistic bound and the insulator the realistic one.
- **Against the bead study's §4:** with the gel in place its wedge reached 0.51 of Paschen at most (equatorial, 40 °C).
  That was the gel-filled gap's voltage, not a void's. The sentence "A void at the contact would not discharge" holds
  at switch-on only.
- **Partial discharge in DC:** a void that breaks down recharges with the surrounding conduction's time constant
  (ε / σ, minutes), so it discharges at intervals rather than every cycle [OC]. It still erodes the gel and puts pulses
  on the field.

## 5. What to build (the ledger's open item, settled as a first cut)
- **The gores** (docs/drawings/DCCREG-HUB-201, note 2):
  - deburr every cut edge;
  - lay each lap with its upper gore's free edge under a solder fillet 0.2 mm wide or more (or dressed round,
    r ≥ 25 µm);
  - burnish each lap down into the gel film, its ramp within 0.5 mm;
  - no void under a lap, the more so within 3 mm of the equatorial beads.
- **The bead rings** (note 3):
  - the equatorial rings closed by a butt joint dressed to the wire's round, within 0.03 mm over 1 mm;
  - the polar rings seamless (turned from Cu-ETP bar, or brazed and turned to the round), or the AH ends rounded to
    1.5 mm and the joint dressed within 0.006 mm over 1 mm;
  - no solder ball on any bead, and no solder on the bare-glass side of a contact.
- **The casting** (note 5): the gel void-free in each contact's wedge, the equatorial ones above all.
  - The bare-glass side of each contact can be seen through the vessel's wall from inside: inspect it by borescope
    through the pumping tube before the AH is fitted [RH].
- **The bench** (`docs/bench-test-rings.md`):
  - the coupons of phase 1 carry a lap and a closing joint;
  - the partial-discharge criterion holds through the settled hours, not only at switch-on: a contact void reaches
    its settled voltage as the DC settles, 90 % of the way in 39 min (`docs/bench-test-rings.md` phase 3,
    `sim/hub_drift.py`). Phase 1 (c)'s two holds of 1 h reach it, so their PD record counts in full, and the detector
    stays on through phase 3's 6 h and its 40 °C repeat.

## Caveats
- **[IR] the lap as a 2-D cut:** a seam meets each bead at its end. That 3-D corner is under the bead and its solder
  and is not modelled.
- **[IR] the ramp** is straight, its bends sharp; real foil bends round.
- **[IR] a void** fills the crevice or the wedge entirely; a bubble smaller than the gap carries less (the field in a
  spherical bubble is 3ε / (2ε + 1) = 1.28 × the gel's [OC]).
- **[RH] Paschen's constants** are air's at 1 atm. A void cast under vacuum may hold gas at a lower pressure, which
  moves it along the curve: for these gaps, lower pressure lowers the breakdown.
- **[RH] the 5 kV/mm rating** is the bench's to qualify (phase 1), and so is every margin quoted against it.
- **[IR] the closing joint as a ridge** holds for a joint far smaller than the wire. A gross lump is a boss (× 3).
- **Not covered:** the fired-on coating's edges for the later build (beaded the same way, or graded: the designer's
  process).
