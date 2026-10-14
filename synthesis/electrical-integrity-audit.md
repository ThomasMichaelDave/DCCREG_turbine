# Electrical Integrity Audit

**Date:** 2026-10-14
**Baseline evidence:** design state `09243c7` (locked 2026-10-09), branch `claude/new-session-0az7f9`
**Synthesis branch:** `claude/synthesis-phase1`
**Agent:** electrical-integrity

**Status legend.** This audit decides nothing. Verdicts: **PASS** (margin ≥ 2), **CONCERN** (1.25 ≤ margin < 2),
**FAIL** (margin < 1.25, the bench's hold-off factor), **OPEN** (only the bench can settle it). The Status column
carries the designer's status of the *choice* being audited (ledger §5.1–§5.2). "Derived" marks arithmetic done here on
committed numbers. No study was re-run. The Paschen and density figures below come from a one-off evaluation of the
formulas stated in §2.1 (no script is committed). The study that should own them is Recommendation 9.

**The audited target** is the §3.9 redesign as `synthesis/tube-spec.md` specifies it: 60-part clamps, V_op 11.94 kV,
rings ±14.77 kV, ideal diodes. Where a figure exists only at the record's V_op (13.13 kV, 66 parts), it is used as the
envelope, or scaled by 11.94 / 13.13 = 0.909 [IR: linear, as `sim/multiplier-layout-findings.md` §1 states]. The
designer's decisions of 2026-10-14 apply:
1. paired ideal / real-stick records;
2. the sixth Ca gap (7 plates a side);
3. no HV seed source, with an injection point at tube-spec A.3a.

## Purpose

This audit tests `synthesis/tube-spec.md` against breakdown physics. It covers:
- Paschen and empirical air breakdown at every air gap;
- creepage on every insulating surface between nets;
- the field at the hub and its interface;
- insulation coordination of the voltage map;
- the flashover and clamp-loss scenarios;
- hot operation;
- the rings' hold-off.

It does not change the geometry. It takes the operating voltages from `synthesis/core-engine-spec.md` and the
geometry from `synthesis/tube-spec.md` (A.6, A.7, A.8, C.2), checked against `sim/multiplier-layout-findings.md`
§3–§5, `sim/multiplier-layout-3d-findings.md` (gates G-LAYOUT) and `sim/doubler-caps-findings.md` §2–§3. The spark-gap
commutator is excluded (Phase 2). The hub interior is locked and is audited at its interface only.

## Governing constraints

1. **Uniform-field air breakdown** [OC]. The record's 6 mm figure, 19.7 kV, is the empirical uniform-field law
   V_bd = 24.4 δ g + 6.29 √(δ g) kV (g in cm, δ the relative air density). It gives 19.5 kV at δ 1. This is the
   criterion of record (`sim/air-stack-sizing-findings.md` §1; ledger §4).
2. **The Paschen form the brief prescribes** [OC]: V_bd = B p g / (ln(A p g) − ln ln(1 + 1/γ)), with A = 15 cm⁻¹Torr⁻¹,
   B = 365 V cm⁻¹Torr⁻¹ and γ = 0.01. At 6 mm and 760 Torr it gives **22.8 kV, 16 % above the empirical law**. Those
   A / B constants fit only E/p ≈ 100–800 V/(cm·Torr). At 6 mm the breakdown E/p is about 43, outside that range.
   - So, for gaps of mm and more, **this audit uses the empirical law** and keeps Paschen as a non-conservative upper
     bound [OC].
   - For sub-0.2 mm films (pd 0.8–15 Torr·cm, inside the fit), Paschen governs [OC].
3. **Inhomogeneous air gaps** follow IEC 60664-1 Table F.2, case A, at 1.5 × the DC peak. This is the record's method
   (`sim/parts-first-cut-findings.md` §4) [IR: the table as recalled; RH: the 1.5].
   - The margin quoted is the impulse withstand the table gives at the actual distance, divided by the operating peak.
     Table points used [IR]: 15 kV → 18 mm, 20 → 25, 25 → 33, 30 → 40, 40 → 60, 50 → 75 mm.
   - **Table F.2 is dimensioned for 2000 m (≈ 80 kPa)** [IR], so these clearances already cover 850 hPa (1500 m).
     The uniform-field gaps sized "÷ 1.5 at 1 atm" do not.
4. **Creepage** follows IEC 60664-1 Table F.4 at PD2: 5.0 / 7.1 / 10.0 mm per kV rms for groups I / II / III at 1 kV
   [IR], taken proportionally above 1 kV and × 1.25 for DC on a rotor [RH] (`sim/parts-first-cut-findings.md` §4).
   - **Above 10 kV, linear extrapolation is not shown to be conservative for DC** [RH]. Under DC, surface charge
     accumulates on insulators: a field-dependent, time-dependent effect that AC-based tables do not encode, and that
     a dust-attracting rotor aggravates. The basis kept here is the record's extrapolation with its × 1.25.
     Potted, void-free interfaces count as solid insulation, not creepage (IEC 60664-1).
5. **Corona onset** follows Peek's law, m 1 (smooth) or 0.85 (handled) [RH]. The onset field scales as
   δ(1 + 0.301 / √(δ r)) [OC form]. For the R1.5 rims this gives × 0.950 at 40 °C, × 0.873 at 850 hPa and × 0.829 at
   both (derived). Corona is not flashover. It is partial discharge in air, which bleeds charge, makes ozone, erodes
   surfaces and draws dust. It is graded on the same scale because the record treats the rims' onset as a design limit
   (ledger §3.4).
6. **The hub's ratings** are 5 kV/mm in the gel at a bead and 1 kV/mm along the glass [RH]
   (`presets/hub-locked.json` ratings). Each rating is defined as *half* the lowest measured breakdown
   (`docs/bench-test-rings.md` phase 1a–b). So a margin of 1.0 against the rating means about 2 against the
   breakdown the rating anticipates.
7. **The clamps are mandatory** (`sim/electrostatic-no-clamp-findings.md`) [OC]. **Equalization is the pump**: no
   insulation fix may add a recovery path (`CONVENTIONS.md`) [OC].

## Specification

### 2.1 Air-gap breakdown

**Air states** (derived) [OC]:

| state | P_atm | T | δ | 6 mm V_bd, empirical | 6 mm Paschen (brief's constants) |
|:--|--:|--:|--:|--:|--:|
| sea level, 20 °C | 1013 hPa | 20 °C | 1.000 | **19.5 kV** (record 19.7) | 22.8 kV |
| sea level, 40 °C rotor air | 1013 | 40 | 0.936 | 18.4 kV | 21.5 kV |
| 1500 m, 20 °C | 850 | 20 | 0.839 | **16.75 kV** | 19.6 kV |
| 1500 m, 40 °C | 850 | 40 | 0.785 | 15.8 kV | 18.5 kV |

**Uniform-field gaps** (operating peak at 60 parts from tube-spec A.7; record-V_op values in brackets):

| gap | g | V across, peak | criterion | margin SL 20 °C | margin 1500 m 20 °C | margin 1500 m 40 °C | verdict | Tag | Status |
|:--|--:|--:|:--|--:|--:|--:|:--|:--|:--|
| C1 / C2 rotor ↔ stator vane (node 1 / 4 ↔ REF), C_min or C_max alike (the gap is fixed, not C-dependent) | 6 mm | 11.99 kV (13.18) | empirical uniform | **1.64** (1.50) | **1.40** (1.27) | **1.32** (1.20) | CONCERN; record V_op at 1500 m 40 °C: FAIL | `[OC]` law; `[IR]` V | DECIDED (6 mm); PROPOSED (60 parts) |
| Ca / Cb plates, node 1 ↔ 2 (4 ↔ 3), 6 gaps (DECIDED 10-14) | 6 mm | ≈ 12.0 kV (13.18 pk, 12.28 rms) | the same | 1.63 (1.49) | 1.40 (1.27) | 1.32 (1.20) | CONCERN | `[OC]`; `[IR]` 0.909 scaling | DECIDED (gaps) |
| column end, node 2 plate ↔ first rotor vane (if the 7-plate parity puts node 2 at the vane end, tube-spec A.8) | 6 mm | node 2 +4.11 against node 1 −11.99 → ≈ 16.1 kV | the same | **1.21** | **1.04** | 0.98 | **FAIL** (one option of an OPEN parity) | `[IR]` | OPEN (layout) |
| clamp worst-case corner: 60 parts at +5 % lot (12.54 kV) and +25 K untrimmed (+0.30 kV) = 12.84 kV on the vane gap | 6 mm | 12.84 kV | the same | 1.52 | 1.30 | **1.23** | FAIL at 1500 m 40 °C | `[IR]` tolerance (`sim/parts-first-cut-findings.md` §2.4) | PROPOSED (trim warm, sorted) |

- **The column-end parity is the sharpest finding.** With 7 plates both ends carry one node. If the ends are node 2,
  a node-2 plate faces the first rotor vane (node 1) across 6 mm. Then Ca's full DC plus node 2's swing stands across
  an air gap sized for node 1 alone. The swing peaks near +4.1 kV (A.7). Whether the peaks coincide depends on the
  phase of node 2's swing against node 1's minimum. The layout puts V(1) − V(2) at 13.18 kV peak at the record's
  V_op (`sim/multiplier-layout-findings.md` §1), which is the Ca gap itself. So the bound is ≈ 16 kV only if the vane
  sees node 2 at its maximum while node 1 sits at its minimum. **The node-1-at-both-ends parity avoids it entirely.**
  [IR] FAIL as a bound on one option; the designer chooses the parity.
- **The clamp worst case** applies only if the string is trimmed cold or unsorted. Sorted (σ 0.36 %) and trimmed
  warm, the corner drops to ≈ 12.0 kV and the 1500 m / 40 °C margin to 1.32 (CONCERN) [IR].
- **At altitude** the record's own rule (breakdown / 1.5) fails at 1500 m even before temperature. 16.75 / 1.5 =
  11.17 kV, below the 11.94 kV V_op [OC arithmetic]. A machine operated above about 600 m (δ ≈ 0.93) must re-trim
  V_op by δ, i.e. the clamp count, to keep the record's 1.5 [IR].

**Edge fields: corona onset** (`sim/air_stack_sizing_results.json`; `sim/doubler-caps-findings.md` §3; tube-spec A.6):

| edge | V (60 parts) | onset, smooth / handled, SL 20 °C | margin smooth / handled, SL | handled, 1500 m 20 °C | handled, 1500 m 40 °C | verdict |
|:--|--:|:--|:--|--:|--:|:--|
| C1 / C2 rims R1.5 (rotor rim between stator rings) | 11.99 kV | 16.5 / 14.0 kV | 1.38 / **1.17** | **1.02** | **0.97** | **FAIL** (handled) |
| Ca tab ↔ other comb's bore edge, post 11 mm (wall bound) | ≈ 12.0 kV | — / 13.9 kV | — / **1.16** | **1.01** | **0.96** | **FAIL** (handled) |
| the same, the post's hole all round (axisymmetric bound) | ≈ 12.0 kV | — / 15.6 kV | — / 1.30 | 1.13 | 1.08 | CONCERN at SL, FAIL at 1500 m |
| Ca rims ending together | ≈ 12.0 kV | — / 18.9 kV | — / 1.58 | 1.38 | 1.31 | CONCERN |
| post surface Ø8 | ≈ 12.0 kV | — / 53.6 kV | — / 4.5 | 3.9 | 3.7 | PASS |

Tags: `[OC]` solves and Peek's form; `[RH]` m 0.85 and δ scaling of the 2-D rim. The design choice is DECIDED (R1.5,
3 mm vanes); the posts are PROPOSED.

- **Rationale.** On a handled or weathered surface the vane rims and the 360 mm per side of tab crossings start corona
  at 1.16–1.17 × the operating peak at sea level, and at about 1.0 × at 1500 m. Two consequences:
  1. **Corona is a leakage path parallel to the clamps.** At the rims it acts first, so it adds to the real-stick seed
     problem (§2.6) and is not in any deck.
  2. **The tab crossings' margin falls below 1 if a post sits closer than 7 mm** (`sim/doubler-caps-findings.md` §3).
     The 7-plate column has not been re-laid, so this placement margin is unverified.
  The smooth-surface margin (1.38) is the honest best case. Cleaning and handling with gloves is a build rule, not a
  margin.

**Inhomogeneous gaps** (IEC F.2 case A; distances from tube-spec A.6 and the 3-D gates):

| interface | V peak, 60 parts (record) | g, laid out | table withstand at g | margin | verdict | Status |
|:--|--:|--:|--:|--:|:--|:--|
| deck A ↔ deck B, across the equator (ea ↔ eb) | 29.5 kV (29.9) | 72 mm (73.2 solid) | ≈ 48 kV | 1.63 (1.61) | CONCERN | PROPOSED |
| column node-2 plate ↔ deck parts (2 ↔ ea) | 18.9 kV (19.5) | 39 mm | ≈ 29.3 kV | 1.55 (1.50) | CONCERN; **5-gap basis: the 7-plate parity may put node 1 here, re-check** | PROPOSED; re-lay OPEN |
| node-1 post ↔ node-2 post | ≈ 12.0 kV (13.18) | 27 mm | ≈ 21.3 kV | 1.77 (1.61) | CONCERN | PROPOSED |
| node-1 comb lowest metal ↔ can disc | ≈ 12.0 kV (13.18) | 39 mm | ≈ 29.3 kV | 2.4 (2.2) | PASS | PROPOSED |
| node-2 standoff, glazed steatite 30 mm, to the can (inorganic: creepage = clearance) | 4.1 kV (4.52) | 30 mm | ≈ 23 kV | 5.6 | PASS; **if parity puts node 1 on the standoffs: ≈ 12.0 kV → 1.92, CONCERN** | PROPOSED |
| decks ↔ G10 cage (counter-rotor, floating near REF) | 14.77 kV (14.94) | 32 mm | ≈ 24.4 kV | 1.65 | CONCERN | PROPOSED |
| clamp HV end ↔ can | 11.99 kV (13.18) | 25 mm | 20 kV | 1.67 (1.52) | CONCERN; bare distance 1.01 × the 24.7 mm rule at the record's V_op | PROPOSED |
| deck worst pair D12 ↔ Z1, bare | ≈ 10.4 kV (11.4) | 21.7 mm | ≈ 17.6 kV | 1.70 (1.54) | CONCERN bare; potted ≥ 16 mm silicone → solid, PASS if PD-free | PROPOSED |
| cross nets l1 / r1 ↔ can | 5.86 kV (6.4) | 82 mm | > 50 kV | > 8 | PASS | PROPOSED |
| injection terminal (node 1, r 132) ↔ cage bore, rotor stopped | 11.99 kV (charged) / seed only (injection) | ≈ 50 mm | ≈ 37 kV | 3.1 | PASS | PROPOSED (synthesis) |
| C1 rims ↔ new G10 (tubes, end ring) | 11.99 kV | 15–18 mm (12 rule) | ≈ 13.5–15.6 kV | **1.13–1.30** | FAIL–CONCERN on the IEC basis. The 12 mm "rim rule" is not the IEC case A figure (≈ 22.5 mm at 1.5 × 11.99) | PROPOSED |
| rotor-vane spacer ring (G10) ↔ stator blades' inner ends | 11.99 kV | 18 mm | ≈ 15.6 kV | 1.30 | CONCERN | PROPOSED |

Tags: `[IR]` table; `[RH]` the 1.5 factor; `[OC]` distances from the 3-D gates.

- **The "12 mm rim rule"** (`sim/doubler-caps-findings.md` §2; CAP-600 notes) is the record's figure for the rims'
  distance to G10. It does not follow from the IEC method the same studies use elsewhere. Against case A it gives
  1.13–1.30.
  - **What mitigates it** [IR]: the far electrode is an insulator (G10), not a conductor at REF. The real stress is
    surface charging of the G10, not a conductor-to-conductor gap. The G10 itself sits on REF hardware within
    centimetres, though.
  - **What this flags:** the rule is unaudited. Either field-solve the rim-to-G10 geometry with the G10's REF backing,
    or open the distance to ≥ 22.5 mm.

**Sub-millimetre air films** (Paschen governs; `sim/core-field-findings.md` §7) [OC]:

| film | field in the film at 11.99 kV | V across film, 50 / 100 / 200 µm | Paschen, 50 / 100 / 200 µm | margin | verdict |
|:--|--:|:--|:--|:--|:--|
| G10 sleeve bore ↔ shaft (εr 4.7 × 1.9 kV/mm) | ≈ 9.0 kV/mm | 0.45 / 0.90 / 1.79 kV | 0.55 / 0.87 / 1.42 kV | 1.23 / **0.96** / **0.79** | **FAIL** unless the bond is void-free |
| rotor ring (Al, node 1) ↔ sleeve outer surface (εr × 1.2 kV/mm) | ≈ 5.6 kV/mm | 0.28 / 0.56 / 1.11 kV | 0.55 / 0.87 / 1.42 | 1.98 / 1.56 / 1.28 | CONCERN |

- **The drawing set says "the sleeves are bonded on the shaft"** (SHF-300 notes, `docs/make_drawing_set.py`). tube-spec
  C.3 states only "G10 sleeves". **Any unbonded patch ≥ 60 µm thick at the bore discharges every 120 Hz cycle**
  [OC: Paschen against the εr-enhanced film field]. The record's alternative is a conductive bore (bore at REF, so
  the film sees no field) [RH].
  - The film voltage uses the thin-film approximation, which slightly overstates thick films. The verdict holds to
    ≥ 0.2 mm [OC].
- **What only the bench settles:** PD at the sleeve with the rotor assembled, < 10 pC at 1.25 × (OPEN).

---

### 2.2 Surface creepage

| surface | V rms (60 parts) | path, material | needed (PD2 × 1.25) | available | margin | verdict | Tag | Status |
|:--|--:|:--|--:|--:|--:|:--|:--|:--|
| sleeve, first rotor vane ↔ can disc | ≈ 9.0 kV (9.87) | PTFE cover SHF-306 | 56 mm (61.7) | 84 mm | 1.50 (1.36) | CONCERN | `[IR]` table; `[RH]` > 1 kV | PROPOSED |
| **sleeve outer end, last rotor vane ↔ Ca\|reluctance bearing** | ≈ 9.0 kV (9.87) | **17.5 mm of sleeve + two PTFE sheds (2 × 2 × 12 = 48 mm)** | 56 mm all-PTFE (61.7) | 65.5 mm | 1.17 (1.06) as tallied | **FAIL** | `[IR]`; `[RH]` | PROPOSED |
| the same, counting the 17.5 mm at its own material if it is bare G10 (group IIIa, 112 mm needed) | ≈ 9.0 kV | mixed | Σ(lᵢ / needᵢ) ≥ 1 | 17.5 / 112 + 48 / 56 = 1.01 (record 0.92) | **1.01** (0.92) | **FAIL** | `[RH]` mixed-path sum | PROPOSED |
| Ca plates, node 1 ↔ 2 | ≈ 11.2 kV (12.28) | none: no support touches two adjacent plates (combs) | 70 / 140 mm | not bridged | — | PASS by construction; **re-verify on 7 plates** | `[OC]` `rules()` touches | PROPOSED |
| node-2 standoffs ↔ can | 2.9 kV (3.14) | glazed steatite 30 mm | 6.5 mm (= clearance) | 30 mm | 4.6 | PASS | `[IR]` | PROPOSED |
| clamp string end to end, stick ends, junction blocks | ≤ 13.4 kV DC (ea ↔ REF) | inside void-free silicone: **solid, no creepage** | solid ≤ 2 kV/mm → ≥ 7.4 mm | ≥ 8 mm silicone; pairs ≥ 16 mm | 1.08 on the 8 mm cover; ≥ 2 between parts | CONCERN (cover); PASS (pairs) | `[RH]` 2 kV/mm | PROPOSED |
| housing foot ↔ G10 deck plate (silicone / G10 interface) | ≤ 20.6 kV DC (ea ↔ r1, deck A) | an interface; creepage only if it delaminates | bare G10 would need ≈ 258 mm | — | — | **OPEN**: adhesion under 40–60 g and thermal cycling; a delaminated foot is a void-path of creepage | `[RH]` | PROPOSED |
| ring A lead ↔ ring B lead | 29.5 kV | own shaft half, never a shared bare surface; PTFE insulation continuous | 187 mm PTFE if bare | not shared | — | PASS by routing | `[IR]` | PROPOSED |
| ring lead through the can (CAN-403 bushing) | 14.77 kV DC | lead insulation continuous through the bushing | solid | **20 kV wire listed in tube-spec C.2 for "leads"** | 1.35 | **FAIL against the record's own ≥ 30 kV DC rule** (see below) | `[IR]` | PROPOSED |
| stator stack insulators (G10 tubes, glass-epoxy rods, end ring) | 0 | touch REF metal and G10 only | — | — | — | PASS: no net-to-net path | `[OC]` | PROPOSED |
| ring ↔ ring along the glass (hub, locked) | 29.5 kV | glass under gel / PEEK: a solid interface | 1 kV/mm rating `[RH]` | 29.9 mm → 0.99 kV/mm | 1.01 on the rating (≈ 2 on the anticipated breakdown) | OPEN (bench phase 1a) | `[RH]` | DECIDED (hub) |

- **The brief's "vane-to-ring creepage along borosilicate beads" has no object in this tube** [OC: the drawing set].
  The beads are copper (the rings' edges, HUB-201). The borosilicate is the hub vessel. The vane stack's insulators are:
  - on the rotor: G10 spacer rings and dowels on the sleeve, touching node-1 metal only;
  - on the counter-rotor: glass-epoxy rods and G10 tubes, touching REF only.
  The vane-to-REF creepage paths are therefore **the sleeve's two ends**, audited above.
- **The sleeve's outer end FAILS.** The 65.5 mm tally adds 17.5 mm of sleeve surface to the sheds' 48 mm and sets it
  against the PTFE requirement.
  - SHF-306 (the PTFE cover) is the hub-side end. At the outer end the sleeve is G10 (SHF-304) unless the cover
    continues there. Counted at G10's rate, the mixed path is 0.92 of the requirement at the record's V_op and 1.01 at
    60 parts.
  - Even counted as all-PTFE the margin is 1.06–1.17.
  - **Fix space:** a third shed (+24 mm), or a PTFE cover over the 17.5 mm [IR]. The geometry change is tube-synth's.
- **The rings' leads.** tube-spec C.2 lists "FEP 20 kV 18 AWG (UL3239)" for "riser, cross nets l1 / r1, leads". Three
  records conflict with that:
  - the drawing set's DCK-501 asks ≥ 30 kV DC for the ring's lead;
  - CAN-403 asks ≥ 30 kV DC through the bushing;
  - P-009's own note says UL3239's ratings are AC (15 kV rms spark test) and that a DC rating must be confirmed with
    the maker.
  At 14.77 kV a 20 kV-rated lead has 1.35, and in the flashover case (§2.5, ≈ 18.8 kV) 1.06. **FAIL against the
  record's rule.** The ring lead must be called out separately: 30 kV UL3239, or a ≥ 40 kV DC silicone lead
  (`docs/make_drawing_set.py` P-009).
- **The potting's 8 mm cover** is sized at 2 kV/mm against the 13.2 kV record. The highest node on the deck, ea /
  Csa's top at 14.77 kV, gets 14.77 / 8 = 1.85 kV/mm, which leaves 1.08 against the [RH] 2 kV/mm. CONCERN. The
  accepting test is the PD figure, < 10 pC at 1.25 × (OPEN, bench).

---

### 2.3 Field at the hub shell

| quantity | value | criterion | margin | verdict | Tag | Status |
|:--|--:|:--|--:|:--|:--|:--|
| field at the null, ±14.77 kV (can solve) | 7.50 kV/cm | **in vacuum** (1e-3 Pa), not air | vacuum gap hold-off ≫ 10 kV/mm at these gaps [OC, order] | > 10 | PASS (wrong medium for the air criterion) | `[OC]` | DECIDED |
| null, real sticks as built: typ / max / hot | 7.47 / 7.33 / 7.10 kV/cm (record supply 6.82 / 6.31 / 5.50) | the same | — | — | PASS | `[OC]` deck; `[RH]` hot | OPEN |
| null, settled (25 °C → 40 °C glass) | 8.20 → 8.27 kV/cm (record, ±14.96) | the same | — | — | PASS | `[OC]`; `[IR]` σ | DECIDED |
| air outside the coupler | 0.55 kV/mm switch-on (record); ≈ 0.54 at ±14.77 | 3.0 kV/mm (30 kV/cm uniform) | 5.5 | PASS | `[OC]` solve; `[IR]` 30 kV/cm | DECIDED |
| gel at the polar bead, switch-on | 4.98 kV/mm (record) → ≈ 4.92 at ±14.77 (× 0.987) | 5 kV/mm rating `[RH]` | **1.016** on the rating | **FAIL** on the rating's own scale; ≈ 2.0 on the anticipated breakdown → OPEN | `[OC]` solve; `[RH]` rating | DECIDED (hub) |
| gel at the equatorial bead, switch-on | 4.46 → 4.40 kV/mm | 5 kV/mm | 1.14 | FAIL on the rating; OPEN | the same | DECIDED |
| gel at the equatorial bead, settled, glass at 32.5 °C (in service) | ≈ 3.2 kV/mm (σ ratio 2.4, interpolated in `sim/hub-beads-settled-findings.md` §7) | 5 kV/mm | ≈ 1.55 | CONCERN | `[IR]` σ | DECIDED |
| the same, glass at 40 °C (σ ratio 5.4) | 6.15 kV/mm | 5 kV/mm | **0.81** | **FAIL** | `[IR]` σ; `[RH]` rating | OPEN (bench phase 3) |
| PEEK at the drawn groove corners, settled | 7.1 kV/mm (4.1 full-round) | ≈ 7 kV/mm by the gel's rule (a third of 20–23) `[RH]` | 0.99 drawn / 1.7 full-round | FAIL drawn; CONCERN full-round (PROPOSED) | `[OC]`; `[RH]` | PROPOSED (grooves) |
| sealed void at an equatorial contact, settled | 0.99 of Paschen at 0.5 mm; 1.46 at 1 mm (`sim/hub-joints-findings.md` §4) | Paschen | 1.01 / 0.68 | FAIL unless void-free (the record requires it) | `[OC]` | DECIDED (void-free casting) |

- **The brief's 30 kV/cm comparison does not apply at the null.** The null lies inside the evacuated vessel. The
  air-exposed field is outside the coupler (0.55 kV/mm, PASS). The binding stresses are inside the solid insulation:
  the polar bead's gel and, in service, the equatorial bead's gel as the glass warms.
- **Effect of real-diode drop.** Every real-stick record lowers the rings and so every hub stress, linearly [OC]:
  - typical sticks: ±14.67 kV → gel ≈ 4.88 kV/mm (1.02 on the rating);
  - record supply as built, typical: ±13.38 / 13.40 kV → gel ≈ 4.46 kV/mm polar (1.12);
  - hot, record supply: ±10.72 / 10.89 → ≈ 3.6 kV/mm (1.39).
  The real drop *improves* the hub's insulation margin. It costs the product (the null field) and the start margin
  (§2.6), not the hold-off.
- **The polar bead runs on its rating at switch-on** in every ideal-diode record. Any lift of ring B past about +1 %
  exceeds it. This is why §2.5 matters.

---

### 2.4 Insulation coordination across the voltage map

**Voltage map, laid out, 60-part clamps** (side A; side B sign-flipped; `sim/multiplier-waveforms-findings.md` §2 via
tube-spec A.7) `[OC]` deck, `[RH]` strays:

| node | DC mean (≈ mid) | swing p-p | peak \|V\| to REF | worst pair partner on the same deck / across |
|:--|--:|--:|--:|:--|
| 1 | −9.2 kV | 5.54 kV | 11.99 | ea (ring A): the column's 13.4 kV; across the hub node 4: 23.98 (only via the decks' 72 mm) |
| 2 | +2.06 | 4.11 | 4.11 | 1: 13.2 (Ca); ea: 18.9 |
| l1 | −4.43 | 2.87 | 5.86 | r1 (cross pair): 11.7 |
| r1 | +4.43 | 2.87 | 5.86 | ea: 20.6 (deck A's widest) |
| r2 | −7.0 | 3.41 | 8.70 | — |
| xa | −13.1 | 3.37 | 14.77 | r1: 20.6 |
| ring A (ea) | −14.77 | ≈ 0.012 | 14.77 | ring B: 29.5 (deck A ↔ B) |

**Component ratings** (the peak at each part's terminals against its rating):

| part | peak duty (60 parts) | rating | margin | verdict | Source | Tag | Status |
|:--|--:|--:|--:|:--|:--|:--|:--|
| D1 / D2 reverse | 4.11 kV | 20 kV stick | 4.9 | PASS | tube-spec A.3 | `[IR]` class | PROPOSED |
| D7 / D8 (worst stick) | 6.11 kV | 20 kV | 3.3 | PASS | the same | `[IR]` | PROPOSED |
| D9 / D11 | 6.10 kV | 20 kV | 3.3 | PASS | the same | `[IR]` | PROPOSED |
| C5 / C6 | 12.8 kV DC (record V_op) | 30 kV | 2.3 | PASS | tube-spec A.5 | `[IR]` | PROPOSED |
| Csa / Csb | 14.9 kV | 40 kV | 2.7 | PASS | the same | `[IR]` | DECIDED for now |
| C7 / C8 | 6.9 kV | 30–40 kV | ≥ 4.3 | PASS | the same | `[IR]` | DECIDED for now |
| Ca / Cb (air) | ≈ 12.0 kV | 6 mm air, 19.5 kV | 1.63 | CONCERN | §2.1 | `[OC]` | DECIDED |
| surge resistors R1–R4, body | ≤ 6.6 kV step (record flashover) | ≥ 15 kV | 2.3 | PASS (record case) | `sim/parts-first-cut-findings.md` §2.2 | `[IR]` | PROPOSED |
| R1–R4, pulse energy | 10.3 mJ | ≥ 0.1 J | 9.7 | PASS (record case) | the same | `[IR]` | PROPOSED |
| clamp string, per part | 0.10 W peak, 5 mW avg | 1.5 W / 1.5 kW 10/1000 | ≫ 2 | PASS | tube-spec A.4 | `[OC]` | PROPOSED |
| HV wire, riser / cross nets | ≤ 12 kV | 20 kV (AC-based, DC unconfirmed) | 1.67 | CONCERN | P-009 note | `[IR]` | PROPOSED |
| HV wire, ring leads | 14.77 kV (18.8 in flashover) | 20 kV listed (≥ 30 kV required by DCK-501 / CAN-403) | 1.35 (1.06) | **FAIL** | §2.2 | `[IR]` | PROPOSED |
| **chain-input / ring-stage surge resistors** | redesign: **none** (R1–R4 sit on D1 and D3 only) | — | — | **FAIL / OPEN** (below) | tube-spec A.3 rationale, evidence ledger | `[IR]` | OPEN |

- **Commutation transients.** Phase 1 has no spark gaps. Diode commutation at 120 Hz is soft: reverse recovery
  ≤ 15 nC and immaterial to the rings (`sim/diodes-real-findings.md` §4.3) [OC]. **The highest voltages the insulation
  must survive are therefore not commutation but the fault events of §2.5.** These are the flashover lift (+27 % on
  a ring) and loss of a clamp (up to the weakest breakdown, about 16–20 kV on nodes 1 / 4).
- **The surge resistors are adequate for the record's case only.** The record's flashover put 5.7–5.8 kV forward
  across the chains' first diodes, and the record added two chain-input resistors (22 kΩ, 0.26 A) for them
  (`sim/parts-first-cut-findings.md` §2.2).
  - The redesign's corresponding diodes are the ladder and ring-stage sticks D5–D8 and D9 / D11. They have no series
    resistance. A flashover step there is limited only by the arc (1 Ω + 200 nH in the record's model [RH]) and the
    wiring.
  - Dumping a 180 pF ladder capacitor at ≈ 6 kV through a few ohms gives currents of amps against a 5 mA stick
    [OC, order]. **FAIL by analogy; OPEN until the redesign's flashover deck runs.**
  - The proposal is to give D5–D8 and D9–D12 the R1–R4 part. The RC is 22 kΩ × 180 pF ≈ 4 µs, far below the
    8.3 ms cycle, so z is not touched to first order [OC].

---

### 2.5 Flashover scenarios

| scenario | trigger | excursion | insulation | components | recovery | verdict | Tag | Status |
|:--|:--|:--|:--|:--|:--|:--|:--|:--|
| **A. vane flashover, side B, record supply** | node 4 flashes to REF at its lowest point: the 6 mm gap or a corona-started rim (§2.1) | ring B 14.96 → **19.03 kV (+27 %)**; b1 7.49 → 10.26 kV | above the bench's ±18.7 kV (1.02 ×); polar gel ≈ 6.3 kV/mm vs 5 (0.79 on the rating, before the DC settles); settled 2.0 / 3.1 kV/mm; with glass at 40 °C the equatorial bead reaches ≈ 7.4 kV/mm | D2 6.6 kV forward, 0.30 A through 22 kΩ, 10.3 mJ: OK; chain parts ≤ 10.3 kV on 30 kV: OK; chain-input resistors 0.26 A: OK | the excess drains through the leakage in seconds to tens of seconds [RH]; the pump re-grows from residual charge | **FAIL** on the hub's ratings; OPEN (bench) | `[IR]` ideal charge sharing; `[RH]` ratings | OPEN (designer, ledger §6 item 41) |
| **A′. the same in the §3.9 redesign** | the same | **not run.** Planning figure: the record's +27 % on ±14.77 kV → ≈ 18.8 kV, above 1.25 × 14.77 = 18.46 | gel ≈ 6.2 kV/mm at switch-on; ring lead 20 kV wire at 1.06 | D5–D12 have no surge resistors (§2.4) | real sticks: a node pulled to ≈ 0.3 kV re-grows only if residual charge elsewhere exceeds the seed (51 V typ, 947 V max, **4.87 kV hot**); the ladder's and rings' stored charge probably carries it, not modelled | **FAIL** (planning); OPEN | `[RH]` scaling | OPEN |
| **B. loss of one clamp string (open circuit)** | a lead or joint broken under 40–60 g; a cracked module | that side is unclamped: the node grows (z ≈ 1.016 a cycle: ≈ 2.2 s from 0.3 kV to 19.5 kV, derived) until the weakest site breaks. That site is rim corona at 14.0 / 16.5 kV (handled / smooth), then the 6 mm gap at 19.5 kV. The rings follow V_op (1.6 % per 200 V): **≈ ±17.3 kV at a 14 kV corona limit, ≈ ±24 kV at the gap's 19.5 kV** [IR linear] | rings ±17.3 → gel ≈ 5.8 kV/mm (FAIL on rating); ±24 kV → ≈ 8.0 kV/mm, past 1.33 × qualification and near the anticipated gel breakdown (≈ 10) | relaxation oscillator (record, air): 25–47 A in D1–D4 without resistors; with 22 kΩ ≈ 0.3–0.9 A; **38 A peak / 2.1 mC a strike through the reference link** in the record. The redesign's counter-rotor floats on 100 pF, so the arc's return closes through a bearing or charges the counter-rotor (not modelled) | arcs repeat every few seconds; pitting lowers the gap; the machine "runs" but erodes vanes and bearings | **FAIL** | `[OC]` mechanism; `[RH]` arc model, the coupled-side response not run | DECIDED (clamps mandatory) |
| **B′. one clamp part shorted** (the usual TVS failure) | a single part fails short | V_op −200 V (−1.7 %); rings −1.6 % | margins improve | the string's other parts take +1.7 % each | normal | PASS | `[IR]` | — |
| **C. ring lead to can / ring-to-ring flashover** | lead insulation (§2.2), bushing PD, a void at an equatorial contact | discharge of Csa / Csb + ring (≈ 107 pF at 14.77 kV ≈ 12 mJ each, ≈ 23 mJ both) | a hub-interior track ends the hub (glass, gel) | Csa 40 kV: OK; D10 / D12 see the step reversed: ≤ 14.8 kV on 20 kV, 1.35 | the hub may not recover; the sphere is the costliest part | CONCERN (prevent by §2.2's lead fix and void-free casting) | `[OC]` energy; `[IR]` | DECIDED (hub) / PROPOSED (leads) |

- **Why only ring B rises in A** [OC] (`sim/parts-first-cut-findings.md` §2.7). A flashover can only pull a node toward
  REF. Node 4 rising by its peak is an oversized upward step, which ring B's positive chain collects. In the bipolar
  redesign the cross-coupled ladder joins both sides, so which ring is lifted, and by how much, is not settled by
  analogy. That makes the redesign's deck the open item.
- **Arc energy per flashover** (derived) [OC]: ½ × 495 pF × (12 kV)² ≈ 36 mJ in Ca, plus about 9 mJ in C1 at C_min.
  That is ≈ 45 mJ a strike, comparable with the no-clamp air strike (43 mJ). Repeated events pit the vanes and lower
  the 1.64 margin.

---

### 2.6 Hot operation

| item | value | source / basis | Tag | Status |
|:--|:--|:--|:--|:--|
| **Operating range proposed for the tube** | **room 15–29 °C** at ≤ 600 m (δ ≥ 0.93); rotor air ≤ room + 5 K | binding limit: the hub's equatorial gel, glass ≤ 37.3 °C, room ≤ 29.8 °C (`sim/hub-thermal-findings.md`); and §2.1's altitude | `[IR]`; `[RH]` the +5 K | PROPOSED (audit) |
| HV deck parts' temperature | ≈ room + 5–15 K. The decks sit at \|z\| 30–78 beside the hub's 41–43 °C AH coils. The clamp's own rise is ≈ 0.4 K (0.297 W on a 0.029 m² housing at h ≈ 25 W/m²K, derived) | `sim/hub-thermal-findings.md`; tube-spec A.4 | `[RH]` | OPEN (bench) |
| stick leakage at the deck's temperature | typical 25 nA at 25 °C, doubling every 10 K → ≈ 100–200 nA at 45–55 °C; the 5 µA "hot" class is a 100 °C junction, not a credible deck state unless the enclosure fails | `sim/diodes-real-findings.md` §4.3 | `[RH]` | OPEN (bench phase 2, warm) |
| insulation margins at the hot end | voltages fall (rings ±13.95 as built; ±10.72 / 10.89 on the record supply). Air density falls too: the 6 mm gap 18.4 kV at 40 °C → 1.53 at 11.99 kV; rim corona handled × 0.950 → 1.11 (FAIL); the equatorial gel at 40 °C glass 6.15 kV/mm (FAIL) | §2.1, §2.3 | `[OC]` / `[RH]` | — |
| clamp drift if trimmed cold | +11.9 V/K: +25 K → +0.30 kV (vane margin 1.64 → 1.60) | tube-spec A.4 | `[IR]` | PROPOSED (trim warm) |
| seed, hot (model) | **4.87 kV** (redesign as built); 3.65 kV (record supply); hot does not start from 1 kV | tube-spec A.3; `sim/diodes-real-findings.md` §6 | `[OC]` deck; `[RH]` hot leakage | OPEN |
| seed vs decision 3 | no HV seed part (DECIDED 10-14). The A.3a injection (node 1, negative, rubbed PVC, kV-class) covers the model's hot 4.87 kV in order of magnitude. Insulation-wise a 5 kV injection is far below V_op (PASS). It must be done at rest with the rings and nodes grounded first (A.3a) | tube-spec A.3a | `[IR]` | DECIDED (no part) / PROPOSED (point) |
| leakage power, hot | 142 mW sticks + strings (redesign as built), against clamps 0.59 W | tube-spec budget | `[IR]` | — |

- **Does the seed need raising hot?** On the model, yes: 4.87 kV against a 1 kV deck seed. On the designer's
  experiment, no (four-diode doubler; no data file). Under decision 3 no part is added; the bench decides. This audit's
  point: **a hot, real-stick machine that suffers a flashover (§2.5 A′) may not restart by itself.** So the A.3a port
  is an operating feature, not only a commissioning one [IR].
- **Thermal boundary with the retainer.**
  - The binding temperature is the hub's (the glass ≤ 37 °C), not the sticks'.
  - The retainer's cage and ventilation must hold the air between the vane stacks at ≤ room + 5 K. That air carries
    windage ≈ 12 W, the magnetic parts 15–18 W and the AH 2.4 W, all heat (tube-spec budget).
  - It must also keep the room under about 29 °C, or the designer accepts the bench's measured σ ratio as the limit.

---

### 2.7 The rings' hold-off (OPEN by design)

| assumption of the model | value | if it is wrong | Tag | Status |
|:--|:--|:--|:--|:--|
| interface rating along the glass | 1 kV/mm (half the lowest coupon flashover) | the stage count and band angles change (`docs/bench-test-rings.md` phase 1 table) | `[RH]` | OPEN |
| gel rating at a bead | 5 kV/mm | the polar bead is at 1.016 on it, so a lower measured rating forces lower rings (fewer clamp parts) | `[RH]` | OPEN |
| ring leakage | 100 GΩ per ring (1.6e11 Ω estimate; the parts dominate at 3e11 Ω a stage, the rings' own insulation 2e14 Ω) | at 10 GΩ, 2 stages give ±14.2 kV instead of ±15.0 (record chain). In the redesign, lower leakage resistance sags the ring stage (C7 / C8 + D9–D12) against its 0.15 µA. More current also speeds the drain after a flashover lift (A): **lower leakage shortens the over-voltage but lowers the product** | `[RH]` | OPEN |
| qualification level | ±18.7 kV (1.25 ×) for 1 h, < 10 pC | below the flashover lift (19.0 kV record; ≈ 18.8 redesign planning) | `[IR]` | OPEN (designer: ±20 kV, 1.33 ×) |
| σ_glass / σ_gel ≤ 4.1 (4.4 full-round) | equatorial bead within rating, settled | at 40 °C glass 5.4 → 6.15 kV/mm | `[IR]` | OPEN (bench phase 3) |

**What the bench must measure** (`docs/bench-test-rings.md`):
1. coupon flashover and 1 h PD (phase 1a–b);
2. the sphere at ±14.8 kV, then **±20 kV**, not ±18.7, for 1 h each with PD < 10 pC (phase 1c). This audit proposes
   ±20 kV because both the record's and the redesign's flashover lifts exceed 1.25 ×;
3. leakage per ring and per ladder part, **warm** (40–50 °C), at the stage voltage (phase 2);
4. σ ratio at 25 / 40 °C (phase 3);
5. on the pump (phase 4): self-start with no injection, then with PVC at A.3a; the rings' level against clamp count;
   and **a deliberate flashover on side B** (a triggered gap across node 4 → REF) with a fast probe on ring B.

## Evidence ledger

| Item | Current design | Evidence | Issue (if any) |
|:-----|:---------------|:---------|:---------------|
| vane / Ca gap 6 mm | 19.7 kV / 1.5 = 13.13 (record); 11.94 kV (60 parts) | `sim/air-stack-sizing-findings.md` §1; tube-spec A.6 | margin 1.64 at SL, 1.40 at 1500 m; the ÷ 1.5 rule fails above ≈ 600 m |
| Paschen (brief's constants) | 22.8 kV at 6 mm | derived | 16 % non-conservative outside the constants' E/p range; empirical law governs |
| rim corona | handled onset 14.0 kV | `sim/air_stack_sizing_results.json` | × 1.17 at 11.94 kV: below 1.25 |
| tab crossing | 1.052 at 13.18 kV; < 1 under 7 mm | `sim/doubler-caps-findings.md` §3 | 7-plate column not re-laid |
| 7-plate parity | node 1 or node 2 at both ends | tube-spec A.8 | node-2 end against the first rotor vane: ≈ 16 kV on 6 mm (bound) |
| sleeve outer end | 17.5 mm + 2 sheds = 65.5 mm vs 62 | `sim/multiplier-layout-findings.md` §4; SHF-307 | 17.5 mm counted at PTFE's rate; G10 there gives 0.92 |
| sleeve bore film | bonded per SHF-300 notes | `sim/core-field-findings.md` §7 | ≥ 60 µm voids discharge every cycle; tube-spec silent |
| 12 mm rim-to-G10 rule | 15–18 mm laid | `sim/doubler-caps-findings.md` §2 | not the IEC case A figure (≈ 22.5 mm) |
| ring-lead wire | "FEP 20 kV" in tube-spec C.2 | DCK-501, CAN-403, P-009 notes | the record asks ≥ 30 kV DC; UL3239's ratings are AC |
| hub polar gel | 4.98 kV/mm on 5 | `sim/hub-beads-settled-findings.md` | any ring lift exceeds the rating |
| flashover, record | ring B 19.03 kV | `sim/parts-first-cut-findings.md` §2.7 | past 1.25 × |
| flashover, redesign | not run | `sim/multiplier-layout-findings.md` Caveats | no surge resistors on D5–D12 |
| no clamp | relaxation oscillator, 25–47 A, 38 A bearing | `sim/electrostatic-no-clamp-findings.md` | redesign with one clamp lost not run |
| hot | sticks 5 µA, rings ±13.95 (as built) | `sim/integrated-multiplier-findings.md` §5 | hot binding limit is the hub glass, ≤ 37 °C |

## Cross-spec dependencies

| Item | Value | Needed by | Note |
|:-----|:------|:----------|:-----|
| 7-plate column parity | node 1 at both ends (avoids a ≈ 16 kV, 6 mm gap at the vane end) | tube-synth | then re-check the column ↔ deck 39 mm and the steatite standoffs at node 1's 12 kV (1.92) |
| sleeve outer-end creepage | ≥ 56 mm PTFE-equivalent at 60 parts, ≥ 62 at 13.13 kV; add a third shed or extend the PTFE cover | tube-synth | currently 0.92–1.17 |
| sleeve bore and ring seats | bonded void-free (< 50 µm) or a conductive bore at REF | tube-synth | Paschen FAIL otherwise |
| rim ↔ G10 distance | ≥ 22.5 mm (IEC case A at 1.5 × 11.99 kV), or a field solve with the G10's REF backing | tube-synth | 15–18 mm laid |
| ring leads | ≥ 30 kV DC rated, separate line in C.2 | tube-synth | DCK-501 / CAN-403 already say so |
| surge resistors on D5–D12 | 22 kΩ, R1–R4's part | tube-synth | pending the redesign flashover deck |
| V_op vs altitude | V_op ≤ δ × 19.5 / 1.5 kV; ≤ 600 m for 60 parts | tube-synth, retainer-spec | site constraint |
| room ≤ 29 °C; rotor air ≤ room + 5 K | ventilation through the cage | retainer-spec | the hub glass's σ limit binds first |
| injection port | closable G10 port at deck A's station; grounding stick access | retainer-spec | the cage is counter-rotor; the port is turned into line at rest |
| hot leakage loss | 142 mW (redesign as built), from the clamps' share | conservation-auditor | belt unchanged; corona loss not in any deck |
| reference-link fault current | 38 A peak, 2.1 mC a strike (record, no clamp) | retainer-spec | bearings must not be the arc return; a brush if no-clamp testing is ever done |
| **From tube-spec** | every voltage, gap, surface (A.6, A.7, A.8, C.2) | this audit | 5-gap basis for all layout gaps |
| **From core-engine-spec** | V_op 11.94 / 13.13 kV; node ranges; rings; flashover record | this audit | — |

## Items deferred to bench

| Item | Why it is open | What the bench measures | Source |
|:-----|:---------------|:-----------------------|:-------|
| hub ratings (1 / 5 kV/mm) | heuristic, half a measured breakdown | coupon flashover; sphere at ±14.8 then ±20 kV, 1 h, PD < 10 pC | `docs/bench-test-rings.md` phase 1 |
| ring and ladder leakage, warm | 100 GΩ and the stick classes are [RH] | per-ring and per-part leakage at 25 / 45 °C | phase 2 |
| σ_glass / σ_gel | sets the equatorial bead's settled stress | E∞ / E(0) at 25 / 40 °C | phase 3 |
| rim and tab corona onset | Peek m 0.85 [RH]; margins 1.16–1.17 | onset of the assembled column and vane stack at up to 1.45 × V_op, with a UV camera or a PD detector | `sim/doubler-caps-findings.md` caveats |
| potting PD | void-free assumption | < 10 pC at 1.25 × on each module and the deck as potted | `sim/parts-first-cut-findings.md` §5 |
| sleeve PD | bore film | PD of the assembled rotor vane stack at 1.25 × | `sim/core-field-findings.md` §7 |
| redesign flashover | not modelled | triggered node 4 → REF flashover, ring B with a fast electrostatic voltmeter | phase 4 (proposed) |
| self-start, hot | model 4.87 kV vs designer's experiment | start with no injection at 25 / 45 °C; PVC at A.3a | phase 4 |
| 6 mm gap breakdown in situ | rims and humidity move it | slow DC ramp of one stack, clamps out, on a sacrificial set | — |

## Recommendations for the designer

All PROPOSED. The designer decides.

1. **Choose the 7-plate parity with node 1 at both ends.** A node-2 end plate facing the first rotor vane puts up to
   ≈ 16 kV across 6 mm (margin 1.21 at sea level).
2. **Fix the sleeve's outer end:** a third PTFE shed, or the PTFE cover continued over the 17.5 mm. Count creepage by
   material.
3. **State in the tube spec that the G10 sleeve is bonded void-free to the shaft** (or the bore made conductive at
   REF), and the rotor rings bonded to the sleeve.
4. **Call out the rings' leads at ≥ 30 kV DC** (the drawing set's own rule), separately from the 20 kV riser and
   cross-net wire. Confirm the DC rating of UL3239.
5. **Add 22 kΩ surge resistors on D5–D12** (or show them unnecessary), and **run the redesign's vane flashover deck**
   on the sixth-gap layout with both ideal and real-stick records.
6. **Qualify the rings to ±20 kV (1.33 ×)** on the bench, not ±18.7 kV, because both flashover lifts exceed 1.25 ×.
   Or limit the rings, for example with a spark gap set near 17 kV (`sim/parts-first-cut-findings.md` §2.7).
7. **Set a site and climate envelope:** ≤ 600 m altitude and room 15–29 °C for 60 parts. Above it, remove one clamp
   part per ≈ 1.6 % of δ lost, at the cost of the rings' level.
8. **Audit the 12 mm rim-to-G10 rule** by a field solve, or open those distances to ≥ 22.5 mm.
9. **Commit a breakdown study** (script, results JSON, findings) that owns every number in §2.1. These include the
   density-corrected gap, corona and film checks, run on the re-laid 7-plate geometry, so that this audit's derived
   figures are reproducible.
10. **Treat the A.3a injection port as an operating feature.** A hot machine with real sticks may need it after a
    flashover.
