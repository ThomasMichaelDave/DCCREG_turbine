# S2a, step 1 — the compact deck for the S1b circuit: findings

> **Superseded in part (2026-10-16):** the designer chose no can round the hub. The deck of record is now
> `s2_deck_bare_nocan_results.json` (`--bare-can --no-can`):
> - the inner edge on the hub's coupler (r 33), checked against the worst of the ring and the flange behind it;
> - lane r 77, plate r 33–111, 4 g residual;
> - cross wires 22.8 mm apart; the bracket r 33–91 on the coupler.
>
> Everything below about the can (r 48), and the stack finding, belongs to the withdrawn model; see
> `s2-geometry-findings.md`.

**Source:** `rebuild/s2_models/s2_deck.py`. It writes two variants:
- relying on the potting: `s2_deck_results.json`, figure `s2-deck-plan.png`;
- also clearing the can in bare air (`--bare-can`): `s2_deck_bare_results.json`, figure `s2-deck-plan_bare.png`.

**The designer (2026-10-16):** "option 2, eventually we will have to redesign the deck but thats for the future. A
bigger deck then required would insert an unnecessary compromise for no reason." So the deck is planned for the S1b
parts only, not cut down from the 10-11 redesign's 13 parts per side.

**The rules and envelopes are the redesign study's,** imported from `sim/multiplier_layout.py` (not edited):
- the parts' potted housings;
- IEC 60664-1 case A clearance at 1.5 × the peak;
- the potting's 2 kV/mm solid rule (`sim/parts_first_cut.py` E_POT);
- the can (r 48) and the cage (r 162, 12 mm kept);
- the deck mass model.

The rules this plan adds [IR]:
- the junction blocks (Ø20 potted around a Ø10 terminal, `sim/tube_geometry.py` J_POT, J_COND);
- the two cross nets, which run straight across between the decks as bare 3 mm PTFE wires, so they need the bare
  clearance of their peak.

**The working voltages are S1b's own** (its ngspice deck), at the strings' +5 % case, the highest of the spread
[IR: design to the worst string]:
- N1 / N4 at 13.80 kV to REF;
- N1–N3 at 13.76 kV;
- N1–N2 at 7.38 kV;
- N2–N3 at 6.38 kV.

## Headline

**The S1b deck fits a ring of r 50–109 mm (redesign: r 50–150) and balances itself to 3 g.** The column moves from
39 mm to 13 mm off the deck; with the can's end disc the column sits at |z| 107 (finding 4), so each side is 10 mm
shorter. This is the variant that relies on the
potting, as the redesign did.

**One decision is the designer's: whether the HV parts must also clear the grounded can in bare air** (as if the
potting had a void). That variant needs r 50–125 and 135 g more plate.

## Findings

1. **Three parts per side:**
   - D1 (REF → N2), D3 (N3 → N1) and Z1, with side B its mirror;
   - four junctions: N1, N2, the cross net N3x, and REF straps to the can.

   The cross-net junctions N2 and N3x sit symmetric about the mirror line. So deck B's N2-from-A and N3-to-A lie
   exactly over them, and each cross wire runs straight across: 23.9 mm apart against the 10.3 mm their 6.38 kV
   needs in air.
2. **The balance decides the arrangement:**
   - The clamp string's arc module weighs 434 g by the redesign's mass model, against 37 g for each stick.
     - That is an overestimate [RH]: the model takes the string's body block at 2.5 g/cm³. Sixty-six 1.5KE parts
       weigh about 75 g; most of the rest is potting.
   - The parts strung in a chain round the lane (sticks, then the string) need a **331 g balance mass**. Raising the
     sticks' radius cannot cancel the string (at r 135 it still needs 148 g).
   - **The fix: each string is split into two series halves of 33 parts** (Z1a: N1 → m1, Z1b: m1 → REF), joined at
     the midpoint m1 by a lead.
     - Electrically it is the same string: the same clamp level, netlist and circuit [OC: series].
     - Mechanically the two halves sit at about 98° and 257°, opposite the sticks, where they cancel the deck's
       moment: **3 g residual** [OC: 2 m R cos φ = S].
3. **The two variants:**

   | | relying on the potting (default) | also bare to the can (`--bare-can`) |
   |:--|:--|:--|
   | the sticks' lane | r 75 mm | r 92 mm |
   | the clamp halves' centres | r 75, at 98° / 257° | r 92, at 102° / 259° |
   | the deck plate | r 50–109, 326 g | r 50–125, 461 g |
   | parts and junctions, per side | 577 g | 577 g |
   | residual imbalance | 3 g at the lane | 9 g at the lane |
   | the worst body-to-can distance (Z1a at 13.8 kV) | 10.0 mm: the potting needs 6.9, bare air 26.1 | 26.6 mm: bare air 26.1 |
   | D3 to the can | 24.2 mm (bare 26.1) | 41.0 mm |
   | every pair of parts, both rules | passes | passes |

   - Both pass the potting rule everywhere.
   - In the default, Z1a and D3 rely on the potting for their clearance to the can, as the redesign's decks did.
4. **The stack** (corrected 2026-10-16 by S2a's geometry, `s2_geometry.py` column()):
   - **The deck alone** lets the column's node-2 plate sit 13 mm off the deck's parts (N2 against N1, 7.38 kV), not
     the redesign's 39 mm.
   - **But the column also stands on the grounded can's end disc** (|z| 87), on steatite standoffs. The redesign's own
     mount rules (`sim/doubler_caps.py` rules()) then bind:
     - N2 against the disc in air: |z| ≥ 97.8;
     - the column's first node-1 plate (Ca_05) against the disc in air, 13.8 kV: |z| ≥ 104.1;
     - the standoffs at a 20 mm catalogue length (the redesign's 30): |z| 107.
   - **So the column sits at |z| 107** (the redesign: 117). **Each side is 10 mm shorter, and the machine is 994 mm**
     (the redesign: 1014).
   - The 26 mm first stated here counted the deck only.

## The designer's decisions (2026-10-16)

- **The deck clears the can in bare air as well:** "Also clear the can in air (r 50–125)". The deck of record is the `--bare-can` variant,
  `s2_deck_bare_results.json`:
  - the sticks' lane at r 92;
  - the clamp halves at r 92, at 102° / 259°;
  - the plate r 50–125;
  - a residual imbalance of 9 g.
- **The cross wires get a support bracket:** "Make sure here the wires have a bracket to support them when crossing. Eventually that bracket will be integrated in later design considerations but for now it requires a support."

## The cross wires' bracket (PROPOSED, for now; to be integrated later)

From `s2_deck.py` bracket(), in `s2_deck_bare_results.json` [IR]:

| | value |
|:--|:--|
| what | a PTFE arm on the can's outer face, at the hub's midplane (z 0), halfway across the 60 mm of air between the deck plates |
| size | r 48–105, 40 mm wide, 8 mm thick; two U-seats for the 3 mm wires, 24.9 mm apart at r 97.7 |
| the wires' creepage across the arm | 41.9 mm (two 5 mm ribs between the seats) against 31.6 mm needed: 5.06 kV rms, PTFE group I, PD2, × 1.25 DC |
| each wire to the can along the arm | 48.2 mm against 22.7 mm needed (3.64 kV rms) |
| each wire to the can in air | 48 mm against 10.7 mm (6.58 kV peak) |
| the load | 39 g at 600 rpm; the wires load the seats with 0.48 N |
| mass, balance | 41 g; an identical arm 180° round balances it [OC] |

- The rule is the same as the deck's: creepage on the rms through `sim/parts_first_cut.py` creepage and DC_MARGIN, and
  clearance on the peak.
- One spare rib is added over the need [IR].

## Next

- **S2a, step 2:** the solids on the chosen deck, the stack moved in, side B's vanes half a pitch on (antiphase), and
  the rings wired to N1 / N4. Then the clash and sweep checks, and the FreeCAD document for the designer's review.
