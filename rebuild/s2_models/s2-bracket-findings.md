# The cross wires' support without machined PTFE: findings

**Source:** `rebuild/s2_models/s2_bracket.py` → `s2_bracket_results.json`, figure `s2-bracket-variants.png`.

**The designer (2026-10-16):** "the PTFE bracket is both structural and dielectrically important (for creepage?) I
would like to see it design differently where it doesn't use PTFE machined parts. We could lengthen the creepage paths
by adding more slots with for instance thin mica plates, the structural section ofcourse also needs to be taken into
account, wathever works there. Let's try some things out ..."

**The job:** hold the cross wires N2 and N3 (25.8 mm apart at r 83.8) at the hub's midplane, at 600 rpm, with a twin
for the balance. Two creepage paths:
- **P1, wire to wire:** 6.38 kV peak, 5.06 kV rms.
- **P2, each wire to the coupler's face:** the worst pair N1–N2, 7.38 kV peak, 6.74 kV rms [IR, conservative: the ring
  taken at the coupler's face].

**The rules** [IR] are the deck's:
- creepage: IEC 60664-1 PD2 × 1.25 DC on the rms;
- an inorganic surface does not track, so its creepage need only match the clearance;
- a path that crosses several materials is rated at the worst of them (IEC practice as recalled; to confirm against
  the standard's text);
- clearance: case A at 1.5 × the peak.

**The structure** (all but A): a split collar clamped round the coupler carries the arm and its twin, so the spin loads
the collar in hoop tension rather than a bonded joint in peel.

## Headline

**The loads are tiny:** about 0.04 MPa at the arm's root (the wires pull 0.4 N). So **the creepage, the joint and the
way the part is made decide, not the strength.** Two variants without machined PTFE pass:
- **B: G10 with mica barriers.** It passes with 7 mm of margin on both paths, from sawn G10 and cut mica.
- **D: one moulded glass-bonded-mica piece.** It passes by far the most, but it needs a mould and is brittle.

C fails as sized.

| | build | P1, wire to wire (have / need) | P2, wire to coupler (have / need) | mass (pair + collar) | root stress, safety | how it is made |
|:--|:--|:--|:--|:--|:--|:--|
| A | machined PTFE arm, bonded (the S2a reference) | 42.8 / 31.6 mm, PTFE (I) | 49.3 / 42.1 mm | 84 g | 0.033 MPa, × 303 | machined PTFE; a bonded joint in peel |
| **B** | **G10 collar and arms; 3 mica barriers between the seats, 3 across each arm, each 8 mm proud of both faces** | **70.8 / 63.3 mm**, rated G10 (IIIa) | **91.3 / 84.2 mm** | 97 g | 0.034 MPa, × 8800 | sawn and drilled G10, cut 0.3 mm mica, bonded in slots |
| C | G10 collar and arm; two catalogue glazed-steatite posts Ø16 × 25 | 59.8 / 63.3 mm **short** (the path crosses the G10) | 61.8 / 84.2 mm **short** | 138 g | 0.047 MPa, × 1150 | catalogue posts; sawn G10 |
| D | one moulded glass-bonded-mica collar with both arms | 22.8 / 10.3 mm, inorganic | 43.3 / 12.6 mm | 151 g | 0.042 MPa, × 2160 | moulded in one: a mould to make; brittle |

1. **B is the designer's idea, and it closes:**
   - **The barriers:** three barriers run radially between the seats for P1, and three cross the arm toward the
     collar for P2. Each stands 8 mm proud of both faces and past the edges, so every way round it adds 16 mm.
   - **Why it needs them:** the whole path is rated as G10, because it crosses G10. The G10 rule is twice PTFE's, so
     the barriers carry that factor.
   - **The cost:** the two sets cross, so the mica plates need cross-halving notches where they meet.
2. **C fails because the path from one post's top to the other runs down the posts and across the G10 arm**, so it is
   rated as G10. To close it, the posts would need about 47 mm for P2, or C would need mica barriers as B has.
3. **D needs nothing more for creepage:** glass-bonded mica does not track, so only the clearance applies.
   - It is the heaviest at 151 g.
   - It is a moulded part, so it needs a mould.
   - It is brittle, which matters under the spin and assembly loads.

## The designer's choice (2026-10-16): B, in 3-D

"go with B and model it in 3D".
- **Where it is:** `rebuild/s2_models/s2_geometry.py` bracket(). It replaces the PTFE arm in the S2a model, and the
  close-up still is `geometry/s2-tube-s1b-from-scratch-bracket.png`.
- **The collar:** a split G10 collar, r 33–39 × 12 mm, in two halves with 1 mm splits, clamped round the coupler at the
  midplane. The screws across the splits are not drawn.
- **The arms:** two G10 arms, 6 mm thick and 44.8 mm wide, r 39–93.3; the wire arm has two drilled seats, the twin
  has none.
- **The mica:** on each arm, three radial barriers between the seats and three across the arm, 0.3 mm muscovite in
  0.4 mm sawn slots, cross-halved. They are drawn as one fused part per arm.
- **The 3-D check** [OC, on the solids' extents] confirms that the barriers cut every surface path. Every plate stands
  8.0 mm proud of both faces, the radial ones run from the collar's face to 8.0 mm past the arm's tip, and the cross
  ones 8.0 mm past both edges. So P1 is 70.8 mm (63.3 needed) and P2 91.3 mm (84.2 needed), as the study computed.
- **The model's gates still pass:** no clash, no sweep hit, every air clearance; 142 solids.

## In V1b's form (2026-10-16)

The decks' V1b layout puts the two cross wires on opposite sides of the hub (`s2-deck-symmetry-findings.md`), which
changes the bracket:
- **Two arms, one wire each:** each identical G10 arm, 19 mm wide, carries one wire, and the two arms balance each
  other. There is no dead twin.
- **No wire-to-wire path:** P1 is gone, and so are the radial mica plates.
- **Four barriers across each arm:** the wires now sit at r 71, so the plain path to the collar is 30.6 mm, and four
  barriers give 94.6 mm against the 84.2 mm needed.
- **The 3-D coverage still holds:** every plate stands 8 mm proud of both faces and past both edges.
- **The close-up** is `geometry/s2-tube-s1b-from-scratch-bracket.png`.
