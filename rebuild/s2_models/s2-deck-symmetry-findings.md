# The decks' symmetry along the axis: findings

**Source:** `rebuild/s2_models/s2_deck_symmetry.py` → `s2_deck_symmetry_results.json`, figure `s2-deck-symmetry.png`.
The rules are those of the deck of record (`s2_deck.py --bare-can --no-can`).

**The designer (2026-10-16):** "check if there is a way of creating more symmetry along the axis with regards to the
component placement on the decks, Either the A vs the B deck needs to be balanced/mirrored or every deck should be
perfectly balanced. We are dealing with 2 times two parts per deck so it's worth iterating an investigation, take your
time."

**What balance means here** [OC]:
- **Static imbalance:** each deck's mass moment S = Σ m r.
- **The couple:** the two decks sit 108 mm apart along the axis, at |z| 48–54, so their moments also make a couple
  C = Σ m z r. It rocks the rotor even when S_A + S_B = 0.
- **Both vanish only if each deck's own S is zero.**

**The scale:** the S2a rotor is 13.9 kg (the model's solids). ISO 1940 G2.5 at 600 rpm allows 552 g·mm in all, about
276 g·mm per correction plane [IR: the grade chosen for a reference].

## Headline

**Every deck can be balanced by its own symmetry, wiring included (V1b).** Each deck's residual falls from 268 g·mm to
41 g·mm, the couple from 18,100 to 5,000 g·mm². Every clearance rule still passes, at the same outer radius.

The way to get there:
- **Within a deck:** each pair diametrically opposite, so the deck is two-fold symmetric about the axis.
- **Between the decks:** deck B is deck A turned 180°, not mirrored.
- **The wiring follows the same symmetry:** the two clamp halves sit right against the stick ends they join, and
  their midpoints are joined by a closed ring.

| | V0, the deck of record | V1, a cross | **V1b, a cross with its wiring** |
|:--|:--|:--|:--|
| the parts | the sticks side by side, the halves placed to cancel them | the sticks opposite, the halves opposite | the same, each half against the stick end it joins |
| deck B | A mirrored about a plane through the axis | A turned 180° | A turned 180° |
| every rule (potting, coupler in air, junctions, cross nets) | passes | passes | passes |
| the parts' outer radius | r 101.6 | r 102.0 | r 102.0 |
| static, per deck | 268 g·mm (97 % of a G2.5 plane) | 235 g·mm | **41 g·mm (15 %)** |
| static, both decks | 424 g·mm | 0 | 0 |
| couple | 18,100 g·mm² | 38,700 g·mm² | **5,000 g·mm²** |
| the clamp's N1 lead | 19 mm | 134 mm | 7 mm |
| the midpoint lead | 128 mm, one way | 159 mm, one way | 484 mm, a closed ring |
| the cross wires | 26 mm apart, at ±9° | opposite, 142 mm apart | opposite, 142 mm apart |

1. **V2, deck B the mirror of deck A about the midplane at the same angles, cannot work.** With the cross nets
   straight across, the part over A's D1 would be D2, whose end is N3, not N2 [OC]. Turning B by 180° is what keeps
   the cross nets straight: the rotation maps D3's N3 end onto D1's N2 end.
2. **Symmetric parts alone are not enough (V1).**
   - The leads break the symmetry: the clamp's N1 lead runs 134 mm across, and the midpoint lead runs one way round.
   - Turning B cancels the two decks' moments statically but doubles the couple.
3. **V1b makes the wiring symmetric too:**
   - **The short joints:** Z1a's N1 end lies against D3's N1 end, and Z1b's REF end against D1's REF end. These two
     joints are each other's 180° rotation.
   - **The midpoint ring:** the halves' midpoint ends then sit exactly opposite, joined by a closed ring at the
     midpoint's potential, both ways round. A ring's mass centre is on the axis [OC]. A closed loop does no harm here,
     since no magnetic field links the deck [IR].
   - **What is left:** the one REF strap, which has no twin, gives the residual 41 g·mm.
4. **The cross wires move to opposite sides of the hub,** 142 mm apart:
   - the wire-to-wire creepage path (P1) disappears;
   - each bracket arm carries one wire, so the twin is no longer dead weight;
   - only the arms' wire-to-coupler barriers remain (bracket B's three across each arm; `s2-bracket-findings.md`).
5. **The cost:**
   - about 0.36 m more lead wire for the midpoint ring, about 7.5 g per deck, included in the balance;
   - the ring runs over every part in the potting, at the midpoint's 6.9 kV. Its separation from the N1 parts under
     the potting rule (3.5 mm) is ample at |z| 76.5 [IR: the deck study does not check leads; to be confirmed in the
     3-D model].

## The designer's decision (2026-10-16)

"Implement v1b": V1b is the deck of record. It is in the S2a model (`s2-geometry-findings.md`).

## For the designer (PROPOSED, before the decision)

- **Take V1b as the deck of record.** In the S2a model this means:
  - each deck rebuilt as a cross;
  - deck B turned 180°;
  - the midpoint ring;
  - bracket B as two arms, one wire each, with only the barriers across the arms.
- **Or keep V0** and correct the imbalance with balance masses at the balancing stage.
