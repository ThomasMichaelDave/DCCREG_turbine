# Rotary Commutator — Switching Design

**Status:** [IR] Geometry frozen; transfer model open. Physical realisation of the
solver's ideal diodes `D1–D4`; `solveDoubler4` is unchanged and remains the ideal-diode
ceiling. Mainstream EE only — no DCCREG theory.

## 1. Purpose

How the doubler's switches (the solver's ideal diodes `D1–D4` in `index.html`) are
physically realised: a **rotary, contactless, mechanically-timed electrostatic
commutator**. Floating rotor bars bridge stator electrodes across a double gap during
geometric alignment — influence-machine lineage (Wimshurst, Bonetti, Kelvin, Van de
Graaff): direction comes from *timing*, not from a diode or a trigger. This document is
the physical layer plus its real-world derating; it does **not** change the engine. **[IR]**

## 2. Switch ↔ diode mapping

The 4-node solver in `index.html` is authoritative. Physical spark-gap aliases:

| Solver diode | Physical switch | Path | Realisation |
|:--|:--|:--|:--|
| `D1` (2→0) | SG1 | 2 → rail | single gap to the resonator rail |
| `D2` (3→0) | SG2 | 3 → rail | single gap to the resonator rail |
| `D3` (1→3) | SG3 | 1 → 3 | double gap over a floating bar |
| `D4` (4→2) | SG4 | 4 → 2 | double gap over a floating bar |

**Ground ≡ resonator rail.** The solver's ground (node 0) is physically the resonator
rail (nodes 5–6, coil `L_RES`/`L1`). At PRF, `L1` is a near-short — the repo's
"L1-is-a-short-at-PRF" argument (learn stage 03) — so the 4-node, ground-referenced model
is valid. The 5–6 resonant swing is the measurable output, treated separately from the
pump model. The cross-couples `D3`/`D4` are node-to-node and map to SG3/SG4 unchanged.
**[OC for the L1-short; IR for the physical layering]**

**Resonator inductance.** `L_RES` (= `L1`, the coil across nodes 5–6) ≈ **123 µH** —
the value Block R's `resonatorCore` computes for the default coupled tank (also recorded
in `docs/report-external-review.md`; the capillary self-test config gives ≈ 131 µH).
TMD-checked and authorised 2026-06-11. **[IR]** This is the value downstream simulations
(e.g. `shuttle_core.py`) must cite for the 5–6 resonator branch; at PRF it is the near-short
above, so it bears on the 5–6 ring dynamics, not the charge-pump verdict.

## 3. Switching regime (frozen)

| Decision | Choice | Consequence |
|:--|:--|:--|
| Trigger regime | Hybrid: alignment gates a self-break | Timing geometric (drift-free); firing voltage = self-break (drift demoted to operating-point) **[IR]** |
| Coupling | Momentary bridge — both gaps fire together when aligned | Bidirectional *within* the window → rectification comes from timing the window to the favourable-polarity half **[IR]** |
| Multiplicity | 6 bars per cross-couple (12 total) | 6× charge **throughput** per couple — not 6× voltage **[IR]** |

Alignment (minimum-gap instant) sets *when* breakdown is possible — pure rotor geometry,
drift-free, measurable. The self-break sets the *voltage*; in a threshold-driven pump that
drift only nudges the operating point. The firing *angle* is the intersection of two
rotor-deterministic curves (rising V vs gap length), so jitter stays low. **[OC]**

## 4. Conduction pairing (solver-verified)

Extracted from `solveDoubler4`'s phase logic at the device point:

- Phase B (C1→min): `D2` + `D4` conduct.
- Phase A (C2→min): `D1` + `D3` conduct.

So the switches group **by transfer-cap branch**: `{D1,D3}` (Ca, sources nodes 1,2) and
`{D2,D4}` (Cb, sources nodes 3,4) — i.e. SG1+SG3 and SG2+SG4. This matches the drawn
timeline (1,3)/(2,4) and the `L_A↔Ca / L_B↔Cb` motor wiring. **The solver is the arbiter;
do not record a different pairing.** **[OC]**

## 5. Physical geometry (frozen)

- **Two mirror bar sets:** one 6-arm set at the top of the rotor, one at the bottom, about
  the central resonator hub — for rotor balance and to match the doubler's C1↔C2 symmetry.
  Top set serves SG3 (1→3); bottom serves SG4 (4→2). **[IR]**
- **In-plane bridging:** each bar bridges two stator electrodes within its own plane. The
  cross-couple sinks — node 3 (SG3) and node 2 (SG4) — are routed **across the ecliptic
  (mid-plane)** on the stator leg frame to reach the opposite plane. 12 in-plane bridges
  total, 6 per cross-couple.
- **Leg frame** (counter-rotating with the stator) carries **both** the 12 motor C-EMs
  **and** the cross-ecliptic HV routing for nodes 2, 3.
- **Floating bars:** one per active sector (6 per set); isolated from node 5; on the rotor;
  each a double (series) gap with a floating midpoint.
- **Returns** SG1/SG2 are single gaps straight to the rail — no floating bar (the rail is
  on the rotor). SG1 rides the C1/Ca disc with SG3; SG2 the C2/Cb disc with SG4.
- **The 30° offset lives only in the stator sector discs** (one sector pitch, 360°/12). The
  top and bottom **bar sets are axially aligned**; the firing offset comes from the stator
  electrode positions. Do not also offset the bar sets, or the offset doubles to 60°.

## 6. Timing (frozen)

- 30° = sector pitch = C1/C2 antiphase pump offset = stroke offset. Commutator timing is
  **inherited from the varicap sector geometry — no separate clock;** favourable-polarity
  phasing is automatic. **[OC]**
- C1's full max→min→max spans 60° → 6 pump cycles per revolution, two strokes 30° apart.
  SG3 fires 6×/rev; SG4 6×/rev, offset 30°.
- **Relative speed governs** alignment, sweep speed, and firing rate: bars on the rotor,
  commutator electrodes on the counter-rotating leg frame → the sum of both rates. The
  `PRF = ⌈Nsec/2⌉·RPM/60` (F6) must use the **relative** RPM. **[OC]**
- Favourable half ≈ 30° (≈ 1.7 ms at the design relative rate); the arc must quench inside it.

## 7. Quench (frozen approach)

The arc **must extinguish before the varicap polarity reverses**, or it back-conducts and
dumps the pumped charge — the make-or-break constraint. **[OC]** Quench by motion (larger
transfer radius → faster sweep, ionisation spread over more area) plus forced air (radial
"Dyson"-type impeller). Run the flow **with** the disc's centrifugal pumping — axial intake
through the clocking stack, exhaust at the rim — not against it. The impeller is a parasitic
windage load on the spin-up motor (stage D torque budget). **[IR]** Margin: ~1.7 ms window
vs µs-to-sub-ms arc blow-out — comfortable. **[OC]**

## 8. Constraints & consequences

| # | Item | Tier | Note |
|:--|:--|:--|:--|
| C1 | Arc quench < favourable half | [OC] | Make-or-break; verify in model and on bench |
| C2 | PRF basis = relative (counter-rotating sum) RPM | [OC] | Check the `PRF`/System inputs use the relative rate |
| C3 | Erosion is real (spark chosen) | [IR] | Distributed by 6 bars + radius + airflow + W/W-Cu. Gaps widen over life → operating voltage creeps; timing unaffected (geometric). Maintenance interval. |
| C4 | Series double-gap strike voltage less predictable | [IR] | Two Paschen curves + floating-midpoint stray C. Tolerable: timing geometric, level non-critical. |
| C5 | Floating-bar DC charge accumulation | [IR] | May need a weak bleed to a reference to stop slow charge-up. |
| C6 | HV insulation coordination | [IR] | Nodes 2,3 carry pumped HV across the leg frame beside lower-voltage C-EM windings — real creepage/clearance margin required. |
| C7 | Parasitic capacitance, asymmetric | [IR] | Cross-ecliptic runs add stray C on 2,3 only → feeds `Cpar`, asymmetrically; slightly tilts the C1↔C2 symmetry the solver assumes. |
| C8 | No accidental cross-bridge | [IR] | SG3/SG4 sets are 30° apart; bar arc-width + electrode-set width must stay under 30° with guard band. |
| C9 | Momentary-bridge transfer is partial | [RH] | Per-event charge is arc-duration-limited; a sweet spot exists between transfer and back-conduction. |

## 9. Modelling status

- **Ceiling [OC]:** ideal-diode per-cycle gain `z = 1.203` at the device point (solver,
  unchanged). The spark commutator gives `z_spark < z`.
- **Startup threshold [RH]:** no firing until |V_source − V_sink| ≥ V_strike; the strike
  penalty fades as V grows (`z_spark → z` for V ≫ V_strike). Implies a minimum seed voltage.
- **Open — spark-transfer model [RH]:** per-event charge as f(strike voltage, arc-duration
  /quench window, node capacitances, 6-bar throughput), run to asymptote against the `z`
  ceiling, locating the arc-duration sweet spot. Inputs fully specified by §§3–7.
- **Producer/consumer:** `solveDoubler4` (ideal diode) is the canonical anchor and is never
  edited by this work. A spark-transfer model, if built, is a separate consumer; if it ever
  graduates into `index.html` it gets its own brief.
- **Design intent [IR]:** HV regime, clamp tiers, and the 5–6 vacuum-glow clamp are locked in
  `design-intent-lock.md`.

## 10. Superseded approaches

- **Triggered trigatron** — rejected: too complex; too many unmeasurable, drifting variables;
  temperature drift corrupts a *timed* instant.
- **Diodes / solid-state controlled switches** — rejected: reverse "back-pressure" needs
  exotic/military-spec parts; controlled switches need isolated gate drive on a free-spinning,
  slip-ring-free frame.
