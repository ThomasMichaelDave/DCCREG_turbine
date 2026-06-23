# Efficiency resolution — the doubler-core tax is not resonantly recoverable

**Status:** settled (three independent confirmations + conservation arbiter). **Supersedes** every η ≈ 0.70
statement in the repo (HTML operating rung, synthesiser anchor, rules-of-thumb). This document is the
authoritative record of *why* the machine's efficiency is **≈ 0.45–0.50**, not 0.70.

---

## 1. Bottom line

| quantity | value | basis |
|---|---|---|
| **direct doubler** η | **0.386** | frozen `doubler_core`; S1-validated two ways (Queiroz eigen-matrix 0.002 %, ngspice transient 4.3 %) |
| **+ island sink recovery** | **η ≈ 0.45–0.50** | downstream island (Cx/Lx) is a true *sink*; S2-validated in ngspice (<0.6 % on t½/i_pk/V_bank) |
| **doubler-core over-transfer** (the path to 0.70) | **forbidden** | three independent roads + conservation arbiter (below) |

The validated machine is the **direct doubler plus the downstream island resonant transfer**. The reach to
η 0.70 required *also* resonantly recovering the doubler's own equalization tax — and that is not
circuit-realizable.

## 2. The principle (first-class finding)

> **A resonant pump's own equalization cannot be resonated for energy recovery, because the equalization *is*
> the pumping mechanism.** Resonating it either **clamps** it (the pump ratchets, the tax stays lost) or
> **breaks the ratchet** (the pump dies). There is no third state. Sequencing the gaps in angle and scattering
> the strike statistically only let the machine *visit* those two arms — they cannot synthesise a recovering
> third. **Only a downstream *sink* transfer recovers freely**, because the sink is not the pump.

This is general to charge-pumps with resonant recovery, not specific to this geometry. The operational
corollary: **resonant tax-recovery is a property of sinks, not of the rectifying transfers themselves.**

## 3. Efficiency decomposition

The combined transfer tax splits into two parts that behave oppositely:
- **Island (≈ 31 % of the combined tax) — recoverable.** The Cx islands are a downstream sink; their LC
  resonant transfer recovers the tax freely. **Real, S2-validated.** This is the 0.386 → ~0.45–0.50 lift.
- **Doubler core / Ca-Cb bucket-brigade (≈ 69 %) — not recoverable.** This tax lives in the equalization
  transfers that *are* the Bennet pumping action. Resonating them is forbidden by §2. **This is the part the
  η 0.70 claim wrongly assumed it could recover.**

## 4. The three independent roads that falsify η 0.70

1. **Doubler-resonant (diode model).** The rectifying diodes clamp the over-transfer at α_max ≈ 0.28 (the
   rail-return re-conducts), so z re-tunes 1.334 → 1.573 and η only → 0.404. The over-transfer is forbidden by
   the same diodes that make the pump rectify.
2. **S3 (static gap, independent engine).** In the literal ngspice circuit the clamping gap and the holding-off
   gap are the **same element**: S3-A (clamp at 0) ratchets the pump but gives **no over-transfer** (z 1.39);
   S3-B (hold off to V_strike) allows the over-swing but **breaks the pump** (z 1.01). One gap, hard either/or.
3. **Sequenced + statistical (conservation arbiter).** With the gaps fired at their real DXF stations
   (rectification separated from recovery *in angle*) **and** the V_strike scatter + formative lag Monte-Carlo'd,
   every realisation lands on z ≈ 1.0 (pump broke) or z ≈ 1.32 (ratchet, no recovery). **No recovering tail, no
   bimodal regime, no stochastic-resonance window.** The conservation guard confirms the tax energy **relocates,
   never net-reaching the output**. The either/or is conservation-deep, robust across the statistics.

Three different models — diode ceiling, static circuit, sequenced-statistical — reach the same verdict. The
agreement is the confidence.

## 5. Methodological record (why this matters for trust)

- **All internal guards passed the wrong model.** `commutator_real_core`'s conservation guard, anchor
  regression, and control twins all passed — because it was *self-consistent*. It was consistently wrong about
  **separability** (assuming rectify and over-transfer are independent). No internal check can catch a
  self-consistent-but-wrong model; **only an independent engine could**, and did. This is the entire case for the
  ngspice cross-validation gate, demonstrated.
- **The tempting positive was caught.** The first sequenced-statistical pass, built on the α-reflection
  (`V_res = V_direct + α(V_direct − V_pre)`), returned a spurious `RECOVERY-CONFIRMED` (**η 0.82**) — because
  the α-reflection *assumes* the over-transfer adds to the pump and so returns 0.70+ **by construction**. It was
  caught by the pre-committed sanity check: **V_strike→0 gave z 1.856, not 1.334.** The η 0.70 family only ever
  existed in models that presuppose it; when z is *observed* circuit-level, it is forbidden.
- **The negative result is the deliverable.** η 0.70 was caught in simulation, before hardware — before a number
  that wasn't real entered a build decision.

## 6. The validated machine (honest spec)

- **z = 1.334** (direct doubler).
- **η ≈ 0.45–0.50** (direct 0.386 + island sink recovery).
- The **island Cx/Lx resonant transfer** is the real, validated recovery mechanism (S2).
- The **doubler-core Ca/Cb resonant recovery is forbidden** (§2–§4).
- The component validations (S0 linear, S1 doubler z, S2 island transfer) **stand**; only the *core
  over-transfer composition* failed.

## 7. Design implications

- **The Ca/Cb brigade inductors do not deliver.** They were kept on the strength of the 0.404 → 0.70 recovery,
  which does not exist. The machine **simplifies to the direct doubler + the island resonant transfer**
  (pending the re-examination — see the wrap-up brief).
- **Keep the island Cx/Lx** — the real recovery.
- **Correct η 0.70 → ~0.45–0.50** everywhere it propagated (HTML operating rung + dual-canary, synthesiser
  established anchor, rules-of-thumb).
- The bench remains the final court on the *physics assumptions* (gap-as-switch, C(θ), FN backstop); this
  document settles the *circuit-realizability* of the core over-transfer, which is a conservation question.

## 8. Provenance (the trail)

`brief-doubler-resonant` (the diode α_max 0.28 ceiling) → `brief-commutator-real` (the V_strike headroom that
*appeared* to lift it to 0.70) → `brief-ngspice-validate` (S0/S1/S2 confirmed) → `brief-ngspice-s3`
(`DISCREPANCY-S3` — the static either/or) → `brief-seq-stat-commutation` (`RECOVERY-FORBIDDEN` — sequenced +
statistical + conservation arbiter, the α-reflection trap caught). Frozen solvers untouched throughout; firewall
held (pure EE: statistical breakdown, LC resonance, charge conservation).

---

## Repo integration note (efficiency-resolution brief)

The **computed** operating η from the validated cores (`design_synth.operating_point`): η_operating =
(useful + island_recovered) / (useful + doubler_tax + island_tax) = (6.153 + f_rec·4.407) / 20.347 →
**≈ 0.48–0.52** over the usable island-Q band (R 2–100 Ω), **0.518 at the design point** (Lx 1 mH, R 2 Ω,
f_rec 0.996). The η ≈ 0.45–0.50 statement above is the honest band; the synth reports the exact value.
`commutator_real_core` is **superseded** (tagged in `solver_inventory.csv`) — kept as the diagnostic that
produced the forbidden 0.70, alongside `doubler_resonant_core`.
