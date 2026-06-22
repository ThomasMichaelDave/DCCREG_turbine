# Findings — COMMUTATOR-REAL: the real brigade price (spark gaps + field emission, not diodes)

**Branch** `commutator-real` (off `doubler-resonant`). **Verdict:** **`BRIGADE-RECOVERABLE`** — the
`doubler-resonant` η 0.404 was a **diode artifact**. The machine has **no diodes**: the rectifier is
a **spark gap that holds off to V_strike** (not a hard clamp at 0) plus a **Fowler-Nordheim
field-emission backstop** (a soft bleed, not a wall). The gap holdoff lifts the over-transfer ceiling
**α_max 0.28 → 0.81** and the gross η **0.404 → 0.709** at the established V_strike = 20 kV; the real
price is now a small, quantified **FE-bleed + arc budget** (~0.3–0.7 mJ/cycle at a designed backstop),
landing **η_real ≈ 0.70**. **Decision: KEEP the Ca/Cb brigade inductors** — the real anchor η is
~0.70 (commutator-set), **not 0.404 and not 0.999.**

The frozen `doubler_core`/`shuttle_core` stay the **direct-limit anchor** (α→0 reproduces z 1.334 /
η 0.386); the commutator is a **new** model, reusing the `doubler_resonant_core` over-transfer cycle
and the `island_resonant_core` guard. **Not merged** — this resolves the Ca/Cb keep/drop; the
synthesizer/topology follow the verdict (and the KiCad netlist needs the gaps drawn).

## The headline (the Ca/Cb decision, resolved)

| model | rectifier | α_max | z | η | physical? |
|---|---|---|---|---|---|
| direct (frozen anchor) | — | 0 | 1.334 | 0.386 | ✓ |
| `doubler-resonant` (diode) | hard clamp at v≤0 | 0.28 | 1.573 | **0.404** | ✗ **no diodes in the machine** |
| **COMMUTATOR-REAL** (this block) | **spark gap holdoff V_strike + FE bleed** | **0.81** | **2.48** | **0.697** | ✓ real commutator |
| naive (no rectifier) | none | 1.0 | 3.00 | 0.999 | ✗ ceiling |

The diode clamped the inner nodes at 0; the **real gap holds off to 20 kV**, giving the over-transfer
the headroom a junction denies. **That single correction recovers ~31 of the 61 available efficiency
points** the diode model had written off.

## §-checks (brief §7)

| # | check | result |
|---|---|---|
| 1 | frozen `doubler_core`/`shuttle_core`/`index.html` empty-diff; commutator new; `doubler_resonant_core`+`island_resonant_core` reused | ✓ byte-identical vs `doubler-resonant` |
| 2 | direct-limit anchor α→0 → z 1.334 / η 0.386 | ✓ **z 1.3340, η 0.3860** (not `MODEL-FAIL`) |
| 3 | α_max from V_strike + FE vs the diode 0.28; assumed 2×3 arrangement | ✓ **α_max 0.807** @ 20 kV (vs 0.28); arrangement stated below |
| 4 | brigade-η loss budget (recovered − FE − arc) vs 0.404 / 0.999 | ✓ **η_real ≈ 0.70** (central); budget table below |
| 5 | conservation closes + trips with FE + arc included | ✓ ring **9.4e-12 + trips 4.3 %**; FE bleed **perturbable** (+5 % leakage moves E_FE) |
| 6 | verdict + Ca/Cb decision + real anchor η | ✓ `BRIGADE-RECOVERABLE`; **keep Ca/Cb**; anchor η ~0.70 |
| 7 | netlist-completion flag | ✓ list + custom-symbol recommendation below |

## The assumed 2×3 arrangement (⚠ flag for TMD)

Per island (×2), **three gaps** replace the diode rectifier: **two sparking gaps** (SG_a, SG_b — hold
off to V_strike ≈ 20 kV, fire, arc `E_arc = V_arc·Q`, self-quench at current-zero) and **one
field-emission backstop** (BS3/BS4, onset 0.6·V_strike = 12 kV, nodes 3↔7 / 2↔8 — the frozen
`shuttle_core` validated this as `BACKSTOP-CLEAN`; TMD's refinement is that it operates by **field
emission**, a soft FN bleed, not a discrete strike). The doubler-side rail-return rectifier
(D1/D2 in the lumped model) is the **doubler gaps SG1/SG2**. TMD confirms the FE-leg identity and the
two sparking gaps' conduction order.

## 1. The model `[OC]/[IR]`

The rectifier is the **gap holdoff**: replace the diode threshold (gap voltage ≤ 0) with the
spark-gap threshold (gap voltage ≤ **V_strike**). The over-transfer α (from `doubler-resonant`) is
then bounded not by a diode at 0 but by **the swing at which the first gap reaches V_strike** — much
larger headroom. The FE backstop (FN `J ∝ E²·exp(−B/E)`, onset 0.6·V_strike) bleeds charge **softly**
along the swing and the held dwell — a real, accounted loss, not a clamp.

**Direct-limit anchor (the gate):** at α→0 the model reproduces frozen **z 1.3340, η 0.3860**
bit-close. **Diode-limit cross-check:** at V_strike→0 it reproduces the `doubler-resonant` clamp
(z 1.573, η 0.404) — so the only change from that block is the realistic holdoff.

## 2. α_max from the holdoff (brief §3) `[SOLVER]`

| V_strike | α_max | z | η_gross |
|---|---|---|---|
| 0 (diode) | 0.28 | 1.573 | 0.404 |
| 12 kV | 0.63 | 2.09 | 0.542 |
| **20 kV (established)** | **0.81** | **2.48** | **0.709** |
| 30 kV | 1.00 | 3.00 | 0.998 |

α_max climbs smoothly with the holdoff; at the real V_strike it is **0.81**, almost 3× the diode's
0.28. (η_gross here is **before** the FE/arc budget.)

## 3. The real brigade η — a loss budget, not a wall (brief §2/§4) `[SOLVER]`

`recovered_net = recovered_gross − E_FE − E_arc`, per cycle, at V_strike = 20 kV
(`recovered_gross` = 10.3 mJ/cycle):

| FE leakage | dwell | E_FE (mJ) | E_arc (mJ) | net (mJ) | **η_real** | tier |
|---|---|---|---|---|---|---|
| 10 µA | window 278 µs | 0.11 | 0.05 | 10.15 | **0.704** | RECOVERABLE |
| **30 µA** | **window** | **0.33** | **0.05** | **9.92** | **0.697** | **RECOVERABLE** |
| 30 µA | sector 1.67 ms | 2.00 | 0.05 | 8.26 | 0.645 | RECOVERABLE |
| 100 µA | window | 1.11 | 0.05 | 9.15 | 0.673 | RECOVERABLE |
| 100 µA | sector | 6.67 | 0.05 | 3.59 | 0.499 | BOUNDED |
| 300 µA | sector | 20.0 | 0.05 | −9.8 | 0.080 | PRICE-CONFIRMED |

The **arc is negligible** (~0.05 mJ/cycle). The **FE bleed** is the real price, and it stays small for
a **designed backstop** (a controlled, low-leakage clamp — its purpose is safety, not conduction). At
the central estimate (**30 µA, commutating within the SG window**) **η_real = 0.697**. The verdict
only degrades to `BOUNDED`/`PRICE-CONFIRMED` if the FE leg is pushed to ≥100 µA **and** the over-
transfer dwells a full rotor sector (1.67 ms) — i.e. a leaky backstop bleeding tens of watts at
20 kV, which a deliberate design avoids. **Across the plausible design envelope η_real ≈ 0.65–0.70.**

## 4. Conservation (brief §4) `[ME]`

Two independent guards. **(A)** the LC ring (`island_resonant_core`, reused unmodified): closes
**9.4×10⁻¹²**, trips **+5 % R** (→ 0.043). **(B)** the budget is non-tautological: the FE bleed is a
**real, perturbable** loss — **+5 % FE leakage moves E_FE** (0.334 → 0.350 mJ/cycle). No recovery is
free; every recovered mJ is a reduced dissipation, and the FE/arc are charged against it.

## 5. The decision (brief §6)

- **Cx (Lx3/Lx4):** **keep** — already validated (a true sink, no rectifier clamp; RESONANT-ISLAND).
- **Ca/Cb (brigade inductors):** **KEEP.** The diode 0.404 was a stand-in artifact; the real
  commutator recovers to **η ≈ 0.70**. The synthesizer's η and the established anchor should be set
  to the **real commutator value (~0.70)**, not 0.404 and not 0.999 — pending TMD's FE-leg spec
  (leakage × dwell), which sets whether the final number is ~0.65 or ~0.70.

**The honest end-to-end story:** the island resonance is the validated downstream win; the brigade
resonance, **with the real gap+FE commutator**, is **also worth it** — the bucket-brigade tax is
**mostly recoverable** after all, because the deliberate V_strike holdoff (gaps, not silicon) gives
the over-transfer the room a diode denies. The price is a **small FE+arc budget**, not the ratchet's
whole tax.

## 6. Netlist-completion flag (brief §7.7) — for TMD

The KiCad export carries **only `SG3a1`/`SG4a1`** (drawn as `SolderJumper_2_Open` = gaps, since KiCad
has no spark-gap symbol). **Missing for the consistency check to match:**
- **SG3b, SG4b** — the second island sparking gaps;
- **FE legs / BS3, BS4** — the field-emission backstops (0.6·V_strike; nodes 3↔7 / 2↔8);
- **SG1, SG2** — the doubler-side gaps near Ca/Cb (the rail-return rectifier).

**Recommend custom KiCad symbols** — one **sparking-gap**, one **FE/leakage-gap** — with a **naming
convention** (`SG*` sparking, `FE*`/`BS*` field-emission) so the parser/consistency check classifies
gaps vs caps and the schematic is self-documenting. This fixes the root cause (gaps drawn as generic
jumpers) and lets the container check the full 2×3 island arrangement + the doubler gaps.

## Deliverables

`reference/commutator_real_core.py` (new; the V_strike sparking gaps + the Fowler-Nordheim FE leg +
the independent guard; anchored to the frozen doubler) · `commutator_real.csv` (real brigade η vs
V_strike / FE leakage / dwell; the loss budget; the direct-limit anchor row) · `sim/commutator_real.py`
(driver + verdict) · `commutator_real.png` (η vs V_strike; the four-η comparison) · this findings doc.
Frozen `doubler_core`/`shuttle_core`/`index.html` byte-identical. **Not merged.**

### Roadmap

On TMD's confirmation of the gap arrangement + the FE-leg spec and completion of the KiCad schematic:
adopt the **real commutator anchor η ≈ 0.70** in `design_synth` (replacing both the 0.386 direct floor
*for the resonant machine* and the 0.404 diode artifact), keep Cx/Lx **and** Ca/Cb, and let the
container's consistency check run against the completed netlist (all gaps drawn with the new symbols).
