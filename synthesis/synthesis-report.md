# Synthesis Report — Phase 1 (the tube without spark gaps)

**Date:** 2026-10-14
**Baseline evidence:** design state `09243c7` (locked 2026-10-09), branch `claude/new-session-0az7f9` — read-only; no
evidence or frozen file was edited.
**Agent:** synthesis-director
**Target engine:** the §3.9 redesign (circuit DECIDED "for now" 10-11, ledger §5.1; its layout, mounts, bridge-ring
bearings and AH-drive parts PROPOSED), with the record's supply as evidence.

## 1. Phase 1 verdict: CONCERNS

The specs close on energy and charge, and the equalization principle holds in all of them [OC]
(`conservation-audit.md` §2.1–§2.3). No gate failed. The synthesis does not pass clean, for four reasons:
- the specs' power sums disagree by up to 5 W;
- the inner-air limit is met only at nominal heat;
- ten electrical margins are under 1.25;
- the designer's sixth Ca gap leaves every layout result that was computed on five gaps waiting for a re-run.

Each item below is the designer's to settle.

## 2. The specs produced

| file | one line | gate |
|:--|:--|:--|
| `synthesis-plan.md` | scope, sequence, gates; the framing condition that the disc machine's η is not the tube's | — |
| `core-engine-spec.md` | the diode doubler as the tube's engine: z 1.3095 bare → 1.058 / 1.031 as built → 1.0142–1.01589 redesigned; z 1.334 / η 0.386 / ≈ 0.50 kept as labelled anchors of the disc machine; the node-total ratio (≥ ≈ 2.4) as the varicap requirement | 1 PASS |
| `tube-spec.md` | the §3.9 tube part by part, with every ideal / real-diode pair; κ 3.51 as the performance basis; clamps at 60 parts; 12 sticks + R1–R4 (+ 8 PROPOSED on D5–D12); the sixth gap (7 plates a side, ≈ 1032 mm); the charge-injection point (A.3a); the envelope (C.1) and the shaft interface (C.3) | 2 PASS; gate-3 corrections in |
| `electrical-integrity-audit.md` | every gap, creepage path and film against the measured air law and Paschen; 10 failures under 1.25, the hot and altitude limits, the flashover cases | 3 PASS with concerns |
| `retainer-spec.md` | the frame bearings, the drive as re-cut, the earthed guard (Ø440), the thermal path, the interlocked port, the tap-test plan; the frame found unchecked | 3 PASS with concerns |
| `conservation-audit.md` | shaft 36.3–38.6 W nominal (64.0 W top) → heat, the rings 4.5 mW the only product; charge closes to 0.01 %; 13 bookkeeping discrepancies, none creating energy; inner air +4.8–5.1 K against +5 K | 4 CONCERNS |

## 3. The conservation verdict

**CONCERNS** (`conservation-audit.md` §3) [OC]:
- **Energy:** the budget closes in the decks (5e-7 electrostatic record, ≤ 9e-8 real sticks, ≤ 1e-5 magnetic).
- **Charge:** every electrostatic node balances to ≤ 0.011 %.
- **Efficiency:** η is about 1.2e-4 for the machine and 0.0075 for the electrostatic pump, as a clamped pump with no
  recovering sink must give.
- **What it found wrong, all bookkeeping:**
  - **D1, the bearings:** the retainer counts the hub-face pair, which the layout no longer has, so 1.7 W is counted
    twice.
  - **D2, real-part leakage:** it is added on top of the clamps, but it comes out of their share.
  - **D4, the "bound 59 W":** that is the drive's sizing case, not a bound; the top-end sum is 64–68 W, still within the
    200 W motor.
  - **D5 / D6:** utron iron and the guard's drag are missing from the retainer's nominal.
  - **D7:** the drive is still sized on the old 2.14 W electrostatic belt; it is 0.6 W.
- **The ring stage reads 4.7 % more charge than its leakage takes.** The audit attributes this to a diode-current
  reading artefact and names the dV/dt test that would settle it.

## 4. Cross-spec findings (the director's Phase 3)

**Electrical ↔ mechanical**

| check | finding | tag | verdict |
|:--|:--|:--|:--|
| tube heat vs retainer cooling | inner air +4.8–5.1 K nominal, +5.5 K on the 2-D magnetic deck, +8.2 K at the top, against the audit's +5 K limit. The cage wall alone takes 5.0 K, so the fan does not cure the top case. The hub glass at ≤ 37 °C binds (a room of ≤ ≈ 29 °C), not the sticks (`conservation-audit.md` §2.6; `electrical-integrity-audit.md` §2.6) | `[IR]` | CONCERN |
| f1 vs excitation | f1 79–85 Hz at d 25 sits between the 60 Hz criterion and the pumps' 120 Hz (`tube-spec.md` C.3) | `[OC]` | PASS |
| f2 vs 120 Hz | 107.9–116.8 Hz, 3–10 % under the pumps (item 77). **New:** the inner bearings' inner-race pass (108.3 Hz) and the frame bearings' 2 × inner both fall inside it (`retainer-spec.md` §2), and the in-phase varicaps' 191 mN·m p-p at 120 Hz (`tube-spec.md` A.1) drives near it. Seats alone lift f2 only to 116.8 Hz; the levers are the parts' mass (EI-66 choke) or d 30 | `[OC]` kinematics / `[IR]` model | CONCERN |
| the frame | never checked. The drive study's three 45 × 45 Al columns give about 2e5 N/m at the top bearing against the 2e8 the shaft studies assume, so the machine rocks at ≈ 13 Hz, between the bodies' 10 Hz and the relative 20 Hz orders. The run-up's harmonics sweep through it (`retainer-spec.md` §5, a hand estimate) | `[RH]` derived | CONCERN, the largest mechanical one |
| guard vs HV | no opening in any HV part; decks 70 mm from the guard; the guard adds 2–3 pF a deck node, so the clamps are trimmed with it fitted (`tube-spec.md` A.2) | `[IR]` | PASS |
| port vs HV safety | the injection / grounding hatch opens only at standstill, behind a guard-locking dual-channel interlock; the audit wants it treated as an operating feature, since a hot machine with real sticks may not restart after a flashover | `[IR]` | PASS |

**Specification ↔ evidence**

| check | finding | verdict |
|:--|:--|:--|
| operating voltage | V_op 11.94 kV (60 parts), the rings ±14.77 kV ideal, as `sim/multiplier-waveforms-findings.md`; the record's 13.13 kV kept as the envelope. Real sticks on the laid-out deck: not run | consistent; OPEN (real) |
| bearing class | SKF 6205-2Z, P5, as `sim/bridge-ring-bearings-findings.md` | consistent |
| parts missed | none in the ES and motor circuits. Two evidence records disagree with the specs: the drawing set orders 132 clamp parts (P-006) against 2 × 60, and specifies ≥ 30 kV DC ring leads where the first draft carried 20 kV (now corrected). The motor nodes a–d have no published charge balance | gaps noted |

**Interfaces**
- **Tube → retainer:** stated in full (`tube-spec.md` C.1, C.3).
  - The open points: the shaft (d 25 drawn against d 30 in the register), ≈ 1032 mm with the sixth gap (not laid
    out), the rotor 36.9 kg + 9.74 kg of AH-drive parts, and the counter-rotor 36.40 kg.
  - The locating bearing carries 814–872 N axially (L10 ≈ 39 000 h, scaled).
- **Tube → rings:** ±14.77 kV ideal, 11.8 V ripple, 1.27 nC a cycle into each ring (`tube-spec.md` A.5).
  - The real-stick pair exists only as built (20 / 148 / 328 V of ripple).
  - The ring leads are ≥ 30 kV DC; the rings are to be qualified to ±20 kV, not ±18.7 kV
    (`electrical-integrity-audit.md`).
- **Tube → commutator (Phase 2): not stated as a wiring interface. New item N9.**
  - `tube-spec.md` says only that none exists.
  - `core-engine-spec.md` §2.7 gives the electrical condition: a reinstated spark-gap stage re-anchors on the
    station-armed z 1.5225 and must fix a cycle cut for η.
  - The record's aliasing is SG1–SG4 ↔ D1–D4 (`CONVENTIONS.md` §2). In the redesign the cross diodes are three-diode
    chains (D3 → r1 → D6 → l2 → D7 …), so that one-to-one mapping no longer holds.

## 5. Known §6 items resolved by this synthesis

| item | how |
|:--|:--|
| 12 | the η attribution enforced at every gate: no spec applies 0.386 / 0.50 / 0.70 to the tube |
| 46 / 65 | the seed: DECIDED by the designer (2026-10-14). No HV seed source; the designer's experiment (the four-diode de Queiroz self-starts, dry or humid; a rubbed PVC tube if slow) stands beside the model's thresholds, and the bench arbitrates. Whether the redesign self-starts the same way stays OPEN |
| 55 | the Ca gap count: DECIDED by the designer (2026-10-14), the sixth gap, 495 pF (1.1 C_max) |
| 60 | insulating mounts for the node-1 plates adopted in `tube-spec.md` |
| 58 | C1 / C2 in phase, as the redesign's circuit requires (DECIDED for now) |

## 6. Known §6 items carried forward

| item | state after the synthesis |
|:--|:--|
| 2 / 30 | the shaft's diameter: OPEN; d 30 is also the lever for f2 |
| 29 | the bearing count: the layout has six, but the specs' power sums disagree (D1) |
| 41 | vane flashover: OPEN, now sharper. The redesign's case was never run (planning ≈ 18.8 kV on ring B); D5–D12 have no surge resistors (PROPOSED: 8 more of R1–R4's part) |
| 69 | the clamp trim: 60 parts carried as the starting length. To be re-run for the sixth gap and the guard |
| 71 / 74 | the drive re-cut: carried, now stale for the sixth gap (+9 mm a side), and sized on the old electrostatic belt (D7) |
| 72 | the deck capacitors' envelopes: OPEN |
| 75, 67 | the chokes' outline and the LV bore: carried as proposed |
| 77 | f2 under 120 Hz: OPEN, compounded by the bearing frequencies (§4) |

## 7. New items found by the synthesis

| # | item | source | tag |
|:--|:--|:--|:--|
| N1 | the varicap requirement is the node-total ratio (≥ ≈ 2.4 for z ≥ 1 bare); as built it is 2.57. The stray price as built is 0.0008 of z per pF, not the record's 0.003 | `core-engine-spec.md` §2.2, §2.5 | `[IR]` derived |
| N2 | with the sixth gap, seven identical plates give ≈ 577 pF, so 495 pF needs less overlap; node 1 at both column ends is required (node 2 at the vane end has margin 1.21) | `tube-spec.md` A.8; `electrical-integrity-audit.md` | `[IR]` |
| N3 | the electrical failures under 1.25, besides the column ends in N2 and the flashover cases in items 41 / 77: the sleeve's outer-end creepage counted as G10 (0.92–1.01); an unbonded sleeve film > ≈ 60 µm; corona on handled surfaces (1.16–1.17, ≈ 1.0 at 1500 m); the record's ÷ 1.5 rule failing at 850 hPa; one clamp string lost; the hot hub gel (0.99) | `electrical-integrity-audit.md` | `[OC]` / `[IR]` |
| N4 | the brief's Paschen constants overstate 6 mm by 16 %; the measured air law governs gaps ≥ 1 mm | `electrical-integrity-audit.md` | `[OC]` |
| N5 | site limits: a room of 15–29 °C, rotor air ≤ room + 5 K, a site ≤ 600 m | `electrical-integrity-audit.md`; `retainer-spec.md` | `[IR]` |
| N6 | the frame, unchecked, rocks at ≈ 13 Hz; it needs ≥ 5e6 N/m at the top bearing | `retainer-spec.md` §5 | `[RH]` derived |
| N7 | the inner bearings' inner-race pass, 108.3 Hz, lies inside f2 | `retainer-spec.md` §2 | `[OC]` |
| N8 | 100 N of preload is not skid-prone by SKF's minimum-load formula; 150 N in opposed pairs is proposed | `retainer-spec.md` §2 | `[IR]` |
| N9 | the Phase 2 commutator has no wiring interface on the redesign's chains | this report §4 | `[IR]` |
| N10 | the specs' power bookkeeping (D1–D13); the ring stage's 4.7 % over-read | `conservation-audit.md` §2.3–§2.4 | `[OC]` |
| N11 | **the model contradicts the designer's experiment on self-starting.** The likely points where they part are the sticks' leakage and the clamps' hot 5 µA [RH] | `core-engine-spec.md` rec. 5 | `[IR]` |
| N12 | **reproducibility:** the audit's Paschen / film figures and the retainer's numbers are hand or one-off node arithmetic, with no committed script (CLAUDE.md guardrail 4). Python is not on this machine's path | `electrical-integrity-audit.md` rec. 9; `retainer-spec.md` | — |

## 8. Items deferred to Phase 2
- The spark-gap commutator and its wiring interface (N9).
- The rings as the stator, beyond the interface of §4.
- Control electronics beyond K4.
- The hub's structure (the interface only).

## 9. Items deferred to the bench

**The rings and the field (phases 1–4 of `docs/bench-test-rings.md`):**
- the hold-off, qualified to ±20 kV rather than ±18.7 kV;
- the leakage;
- the conductivities at 25 / 40 °C;
- the field on the pump's own supply.

**The pump:**
- whether the redesign self-starts and how humidity affects it (N11);
- the sticks' leakage measured warm;
- the clamps' final count, set warm with the guard fitted;
- partial discharge and corona onset on handled surfaces;
- a deliberate flashover on side B.

**The mechanics and heat:**
- a tap test with the parts mounted (f2), plus a waterfall at 71.7 / 108.3 / 120 / 240 Hz;
- a hammer test of the frame;
- a coast-down for the windage and the bearings;
- thermocouples on the inner air and the glass.

## 10. Recommendations for the designer (all PROPOSED)

1. Re-run the layout for the sixth gap with node 1 at both column ends and the guard as a REF plane. That one run
   updates z, the rings, the strays, the clamp trim, the mounts' corona margin, the length and f1 / f2 together
   (`sim/multiplier_layout.py`, `sim/doubler_caps.py`, `sim/shaft_bearings.py`).
2. Settle f2 with mass or diameter, not seats: the compact EI-66 choke or d 30. In the same decision, set the shaft
   (items 2 / 30).
3. Check the frame before anything is built on it. Run the shaft model with a finite top support, then the hammer
   test.
4. Run the redesign's vane flashover with D5–D12's surge resistors in and out. That decides the 8 resistors and
   ring B's peak (item 41).
5. Treat the +5 K inner-air budget as unmet until the bench measures it. Size the guard's ventilation or the room
   limit on the high case, not the nominal.
6. Have the specs restate their power sums per the conservation audit's recommendations 1–2 and 6. Publish the motor
   nodes' charge balance (rec. 3). Settle the ring-stage reading with a dV/dt fit (rec. 4).
7. Commit scripts for the hand-computed figures (N12), so every number has its script, results and findings.
8. Record the self-start experiment in the repository as data (the conditions, the humidity, the configuration), so
   it can stand beside the model as decision 1 asks.
9. Choose: the preload (150 N proposed), the REF-to-earth bond, the slip hub, the K4 reed magnet's position, the
   grease (`retainer-spec.md`).
10. Before Phase 2, state which nodes of the redesign's chains a commutator would replace (N9).
