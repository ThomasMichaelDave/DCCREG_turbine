# Findings — DOUBLER-RESONANT: does z survive resonant equalization?

**Branch** `doubler-resonant` (off `resonant-brigade`). **Verdict:** **`Z-RETUNED` — carrying the
`Z-COLLAPSES` conclusion: THE PRICE IS REAL.** Re-deriving the Bennet doubler with half-cycle LC +
diode resonant equalization in place: z does **not** survive at 1.334 and does **not** freely enhance
to the naive 3.0 — **diode rectification clamps the over-transfer**, re-tuning z to **1.573** but
recovering only **η 0.386 → 0.404** (+1.8 points), **far below the 0.999 brigade upper bound**. **The
bucket-brigade tax is ~97 % intrinsic to the ratchet:** the rail-return diodes that make the Bennet
pump *pump* are exactly what forbid the over-transfer that would recover the tax. **TMD's "there is a
price" is CONFIRMED** — built as a falsification test, the model falsifies the free-recovery story,
not the price.

The frozen `doubler_core` stays the **direct-limit anchor** (α→0 reproduces z 1.334 / η 0.386
bit-close); the resonant doubler is a **new** solver, regression-locked to it. **Not merged** — this
resolves that the brigade fix is *not* real on the core transfers; the η headline reverts to the
downstream island gain.

## The headline number (the gate, resolved)

| model | z | η | brigade-tax recovered | physical? |
|---|---|---|---|---|
| direct (frozen anchor, α=0) | 1.334 | 0.386 | — (baseline) | ✓ = frozen |
| **naive unconstrained over-transfer** (α→1) | **3.00** | **0.999** | 100 % | ✗ **diode-violating** |
| **diode-limited over-transfer** (α_max≈0.28, *any* Q) | **1.573** | **0.404** | **~3 %** | ✓ rectification intact |

The naive z=3.0 / η=0.999 **was the resonant-brigade upper bound** — and it is **unphysical**: that
state forward-biases the rail-return diodes (100 % of held states violate blocking). The physical,
rectification-honouring answer recovers **~1.8 efficiency points, not 61.**

## §-checks (brief §7)

| # | check | result |
|---|---|---|
| 1 | frozen `doubler_core`/`shuttle_core`/`index.html` empty-diff; `doubler_resonant_core` new; `island_resonant_core` reused unmodified | ✓ byte-identical vs `resonant-brigade` |
| 2 | direct-limit regression α→0 reproduces z 1.334 / η 0.386 | ✓ **z 1.3340, η 0.3860** (bit-close; not `MODEL-FAIL`) |
| 3 | resonant steady z, η, W_mech; per-stage ladder voltages | ✓ diode-limited **z 1.573, η 0.404**; ladder re-settles (v2,v3→0) |
| 4 | mechanism diagnosis; rectification intact | ✓ **rail-return diodes D1/D2 clamp**; one-way preserved; over-transfer leverage capped |
| 5 | conservation closes + trips; over-transfer energy path explicit | ✓ ring guard **9.4e-12 + trips 4.3 %**; feeds back (no free sink) |
| 6 | verdict + (retuned) z/η | ✓ `Z-RETUNED`, z 1.573, η 0.404 |
| 7 | brigade-η headline updated | ✓ **reverts 0.999 → ~0.40** on the core; island gain stands |

## 1. The model `[OC]`/`[SOLVER]`

The frozen `solve_phase` equalizes charge through a conducting diode **to the mean** (the two-cap tax
½C_eff·ΔV²). Done resonantly (source → series L + diode → sink), the inductor current is **maximal at
the mean**, so a lossless disconnect is only available at the next **current-zero**, which leaves the
caps **over-transferred**. Parameterise by α ∈ [0,1]:

> **V_res = V_direct + α·(V_direct − V_pre)**

with `V_pre` = the diodes-off constant-charge state (the over-transfer **source**), `V_direct` = the
frozen equalized state (the **mean**). α = 0 is the direct doubler (the **frozen anchor**); α = 1 is
the full lossless swap. The half-cycle ring leaves the differential at α·ΔV, so the residual tax is
(1−α²)·direct_tax and the recovered fraction is **α² = f_rec = 1 − π/Q** (the island integral) →
**α = √(max(0, 1 − π/Q))**. The brigade ring (Q≈1909) → α≈0.999 (near-full swap).

**Direct-limit regression (the gate, brief §2):** at α=0, `solve_doubler_resonant` reproduces the
frozen **z 1.3340, η 0.3860** bit-close — so the resonant model **is the same doubler**, only the
transfer mechanism changed; any z shift is the resonance, not an artifact.

## 2. The rectification clamp — *why* z moves (brief §3) `[OC]`

A **held** state at current-zero needs **all diodes blocking**. The over-transfer drives the inner
nodes (2, 3) toward **positive**, which **forward-biases the rail-return diodes D1(2→0) / D2(3→0)** —
they re-conduct and clamp v2, v3 → 0. So the achievable over-transfer is

> **α_max = the largest α keeping the state diode-valid ≈ 0.277** — and it is **independent of Q.**

The naive curve runs to z=3.0; the physical curve **plateaus at z=1.573** the instant α exceeds α_max
(see `doubler_resonant.png`). The four §3 questions, answered:

- **Ladder balance.** The ladder **re-settles** to a new stable balance (it does *not* destabilise /
  collapse toward 1). Per-stage steady voltages move from `[−0.41, 0, −0.41, −1]` (direct) to
  `[−0.80, −0.17, 0, −1]` (clamped) — node 3 pinned at 0 by D2.
- **Rectification.** The diode **still blocks reverse** over all 200 steady half-cycles — the ratchet
  stays one-way. **The price is the STATE, not lost rectification** (the distinction the brief asked
  for, confirmed).
- **Over-transfer leverage.** Moving more charge per step **raises** z (1.334 → 1.573) — but the
  clamp caps it **far** below the lossless 3.0, so the *efficiency* lever barely moves
  (0.386 → 0.404).
- **Re-tune headroom.** α_max is **structural** (v2, v3 → 0 is the topology of the rail return, not a
  ratio choice) — the cap ratios / L / phase **cannot tune the clamp away**. The recovery does not
  unlock with re-design.

**This is the operative effect:** the rail-return diode — the element that makes the Bennet pump
ratchet charge to the output — is the same element that re-conducts and forbids the lossless
over-transfer. The equalization dissipation is **what makes the pump pump**; you cannot have the
ratchet without (most of) the tax.

## 3. Conservation — the over-transfer is no free sink (brief §4) `[ME]`

Two independent guards. **(A)** the per-transfer LC ring, via the validated `island_resonant_core`
i²R-integral vs energy-bookkeeping (reused **unmodified**): closes **9.4×10⁻¹²** AND **trips under
+5 % R** (residual → 0.043). **(B)** the non-tautology: the over-transfer state **feeds the next
stroke** (unlike the island's free sink), so a +5 % α **moves** the steady z (unclamped
1.868 → 1.908) — the ledger accounts the fed-back energy, and a perturbation moves it (Rule 6.1).

## 4. The implication (brief §6) `[OC]`

**Retuned → the brigade fix is not real on the core transfers.** The realistic resonant-doubler η
(0.404) is essentially the direct floor (0.386); the 0.999 upper bound is unreachable because
rectification clamps the over-transfer. Therefore:

- **The 2 brigade inductors come OFF** the doubler core pump transfers (the recovery does not pay).
- **The η headline REVERTS** from the brigade's 0.999 upper bound to the **downstream island gain**
  (RESONANT-ISLAND: ~31 % combined-tax drop, validated and unconditional — the island *is* a free
  sink, so that fix stands).
- **`design_synth` z-band / η₀ are unchanged** — the adopted machine stays the **direct doubler**
  (z 1.334, η 0.386); the resonant doubler is *not* adopted, so the anchor does not move. (Had we
  adopted z=1.573 the anchor would shift; we do not.)
- **The deepest result in the arc:** *not all tax is recoverable, because some of it is what makes
  the pump pump.* The machine's doubler-core efficiency floor (~0.386, or at best ~0.40 with a
  diode-bounded resonance) is set by the ratchet mechanism itself. Documented as the floor.

## Deliverables

`reference/doubler_resonant_core.py` (new; the resonant Bennet cycle + the rectification clamp + the
independent guard; regression-locked to the frozen doubler) · `doubler_resonant.csv` (z, η, ladder vs
α/Q; naive vs diode-limited; the direct-limit anchor row) · `sim/doubler_resonant.py` (the driver +
verdict) · `doubler_resonant.png` (z vs α; the ladder re-settle) · this findings doc. Frozen
`doubler_core`/`shuttle_core`/`index.html` byte-identical (empty-diff asserted). **Not merged.**

### Roadmap

The resonant-transfer architecture is validated **only downstream** (the island, a true sink). On the
**doubler core** the brigade tax is intrinsic — the brigade inductors are removed. The efficiency
story is now honest end-to-end: **island resonance is the real, sized win (~31 % combined-tax drop);
the doubler bucket-brigade is the price of the ratchet, not a recoverable loss.** The next levers, if
any, are architectural (more doubler stages / accept the floor), not more inductors on the core.
