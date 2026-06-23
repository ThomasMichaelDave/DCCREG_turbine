# Findings — NGSPICE-S3: the end-to-end composition (make-or-break)

**Branch** `ngspice-s3` (off `ngspice-validate`). **Verdict:** **`DISCREPANCY-S3`** — the deck composes
and **runs stably** (the varicap tripwire holds, z = 1.334), but the resonant gain does **not**
reproduce end-to-end: z stays at the **direct/clamped value (~1.3–1.4)**, not the Python **z_res =
2.478 / η_real = 0.70**. The composition surfaces a real **emergent interaction the component checks
(S0/S1/S2) could not**: in a literal circuit the **over-transfer and the equalization are the same
physical gap**, and you cannot have both — confirming, in a second engine, the doubler-resonant
"resonating the core alters z" caveat, and flagging that the η 0.70 headline needs re-examination.

The Python cores are read-only (the anchors under test); the ngspice models are from physics, never
tuned to η. **This is the valuable kind of break the brief pre-committed** — not a faked pass.

## §-checks (brief §4)

| # | check | result |
|---|---|---|
| 1 | stabilization stated; **S1 tripwire re-passed (z=1.334) with the stabilized varicap** (work term intact) | ✓ z = **1.3908** (tanh tier, <5%); the de Queiroz `Q='C(θ)·V'` charge-defined varicap (charge is the state — nothing differentiates a stiff product; the V·dC/dt work term is native, **proven by the tripwire**) |
| 2 | full deck composes the real elements; firing matches the DXF stations | ✓ varicap doubler + Lx resonant rings + V_strike self-break gaps (the firing geometry from FIRING-GEOMETRY); the **bare SW switch is bidirectional → no rectification → no pump** (a documented trap, avoided with switch+diode) |
| 3 | steady state reached | ✓ both composition decks converge (Gear + bounded step) and run to t_end |
| 4 | end-to-end z_res/η_real vs the Python anchor | ✗ **z stays ~1.3–1.4, not z_res 2.478** (table below) |
| 5 | models from physics, not tuned to η; cores empty-diff | ✓ |

## The end-to-end comparison (`ngspice_s3.csv`)

| stage | quantity | Python | ngspice | Δ | verdict |
|---|---|---|---|---|---|
| **tripwire** | doubler z (varicap intact) | 1.334 | **1.391** | 4.3 % | ✓ (work term intact) |
| **S3-A** | z_res — Lx + clamping diodes | 2.478 | **1.392** | 43.8 % | ✗ |
| **S3-B** | z_res — Lx + V_strike holdoff gaps | 2.478 | **1.009** | 59.3 % | ✗ |

Both composition decks **converge** (conv=True, run to t_end) — this is not a numerical failure; the
varicap is stable (tripwire intact). The resonant gain simply **isn't there**: S3-A sits at the direct
z (the diodes clamp → no over-transfer); S3-B collapses to z≈1 (the V_strike holdoff breaks the pump).

## The localized cause — the emergent interaction `[OC]`

The Python `commutator_real_core` produces η_real 0.70 / z_res 2.478 by **over-transferring the doubler
equalization** with a **V_strike holdoff** (the brigade tax reflected past the equalization mean to
α_max 0.807). Its α-reflection model computes `V_direct` (the *diode* equalization) and **then** reflects
it to α_max (the *V_strike* allowance) — treating the equalization and the over-transfer as **separable**.

The literal circuit shows they are **the same physical gap**, with a hard either/or:

- **S3-A — Lx + clamping diodes (the gap clamps at 0).** The diodes still equalize at ~0, so the pump
  ratchets (z stays at the direct ~1.3–1.4) — but the inner nodes are **clamped at 0**, so there is **no
  over-transfer**. (Exactly the doubler-resonant diode clamp: α_max 0.28, z 1.573 *ceiling* — and the
  circuit sits below it.)
- **S3-B — Lx + V_strike holdoff gaps (the gap holds off to V_strike).** Now the inner nodes *could*
  over-swing — but holding the rail-return off to V_strike means it **no longer conducts at 0 each
  cycle**, which is **the conduction that ratchets the Bennet pump**. So the pump **breaks** (z → ~1,
  no growth).

**You cannot simultaneously clamp at 0 (to ratchet the pump) and hold off to V_strike (to over-transfer)
— it is one gap.** `commutator_real_core` got η 0.70 by assuming you can do both; the second engine says
you cannot. This **independently confirms the DOUBLER-RESONANT load-bearing caveat** ("resonating the
doubler's core pump transfers may alter z — the equalization IS the pump") — now demonstrated in a
circuit, not just argued.

## The implication (stated honestly)

- **The component validations stand:** S0 (linear), S1 (doubler z — Queiroz eigen-matrix + ngspice), S2
  (the resonant transfer, <0.6 %). These are unaffected.
- **The η 0.70 headline (commutator-real, over-transferring the core) is NOT circuit-realizable** as
  modeled. The validated efficiency recovery is the **DOWNSTREAM island** (RESONANT-ISLAND, ~31 %
  combined-tax drop — a true sink, **independently confirmed by S2's resonant-transfer match**), not the
  core over-transfer. The realistic η is **direct 0.386 + the island recovery (~0.45–0.5)**, not 0.70.
- **This is an independent-engine flag, not a unilateral overturn.** It says: **investigate
  `commutator_real_core`'s separability assumption before trusting η 0.70 end-to-end.** The Python
  `doubler_resonant_core` already carried this caveat (z may not survive); S3 shows the circuit makes it
  bite. TMD/Python re-examination is the right next step — and the real schematic's architecture (core
  pump diodes + *downstream* island/bank resonant transfers, not core over-transfer) is the likely
  faithful picture.

## Scope (brief §7)

S3 closes the four-stage capstone with a **decisive, honest break**, not a faked pass. It validates the
**composition** — the one thing S1/S2 couldn't — and the composition reveals a genuine model tension:
not a varicap instability (the tripwire holds), not a numerical failure (the deck converges), but an
**emergent physical interaction** (equalization ↔ over-transfer are one gap) that the lumped α-reflection
model elided. `VARICAP-UNSTABLE` is ruled out (the varicap is stable and work-term-preserving);
`NGSPICE-CONFIRMS-S3` is **not** earned (z_res/η_real do not reproduce). **`DISCREPANCY-S3`** is the
result — and it points at a real model assumption to fix.

## Deliverables

`spice/s3_tripwire.cir` / `s3_A.cir` / `s3_B.cir` (the composed decks) · `spice/run_s3.sh` ·
`ngspice_s3.csv` (the end-to-end comparison) · `sim/ngspice_s3.py` (the harness + the make-or-break
verdict) · this findings doc. Python cores frozen empty-diff. **Not merged** (the result is the
confidence statement — here, a flagged model tension to resolve before the η 0.70 build claim).
