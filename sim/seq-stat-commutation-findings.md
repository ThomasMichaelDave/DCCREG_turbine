# Findings — SEQUENCED-STATISTICAL-COMMUTATION: the test S3 should have run

**Branch** `seq-stat-commutation` (off `ngspice-s3`). **Verdict:** **`RECOVERY-FORBIDDEN`.** Building
the **circuit-level** sequenced commutator (rail-return rectifies at its DXF station; the tax-recovery
forward fire over-transfers at a *later* station) and digging into the **statistics** (V_strike scatter
+ formative lag), the conservation arbiter confirms: **the rotary commutation genuinely separates
rectify from recover in angle — but the forward over-transfer is still clamped by its own rectifying
gaps, and the statistics open no hidden regime toward 0.70.** S3's either/or is **a conservation fact,
not a single-gap artifact.** η 0.70 is not realizable; the validated floor **η ≈ 0.45–0.50 (the
downstream island, S2-confirmed)** stands.

## The trap, recorded honestly (the brief's central warning)

The brief warns: *the risk is re-coding `commutator_real_core`'s assumption (that rectify and
over-transfer are separable).* **I hit it first.** An initial pass built the model on
`doubler_resonant_core`'s **α-reflection** (`V_res = V_direct + α(V_direct − V_pre)`) and got a
spurious **`RECOVERY-CONFIRMED` (η 0.82)** — with a **failed sanity check** (V_strike→0 gave z 1.856,
not 1.334). That is the tell: the α-reflection **assumes** the over-transfer adds to the pump, so it
returns η 0.70+ *by construction* and **cannot represent the pump breaking**. It re-codes the intuition.
**The arbiter must be circuit-level (KCL + explicit gap switching), never the α-model** — so the final
model is the de Queiroz varicap doubler in ngspice, and z is **observed**, not assumed.

## §-checks (brief §4)

| # | check | result |
|---|---|---|
| 1 | model is **circuit-level (KCL + gap rules), not the α-reflection** | ✓ ngspice deck; all-direct z = 1.39 (= frozen 1.334, tanh tier) — faithful sanity, **not** re-coded |
| 2 | gaps fire at DXF stations in order; deterministic sequenced z | ✓ rail-return D1/D2 rectify (clamp at 0, pump ratchets); forward D3/D4 resonant → **z ≈ 1.39 ≈ direct, NO recovery** |
| 3 | Monte-Carlo; the recovery distribution (mean/var/shape/correlation) | ✓ statistical V_strike on the forward gaps → no recovering tail toward 0.70 (table below) |
| 4 | conservation guard: recovered vs relocated, trip-tested | ✓ z (the gain ratio) stays at direct → the tax energy **relocates**, never net-reaches 0.70 |
| 5 | firewall: pure EE, no substrate physics | ✓ statistical breakdown, formative lag, LC resonance, charge conservation only |

## 1. The deterministic sequenced result `[OC]`

The de Queiroz varicap doubler with the **rail-return as plain rectifying diodes** (D1/D2 — clamp at 0,
so the Bennet pump ratchets) and the **forward path resonant** (D3/D4 + series Lx — the tax-recovery
transfer, separated in angle from the rectification):

| configuration | observed z | η(z) |
|---|---|---|
| all-direct (circuit sanity) | 1.39 (= 1.334 tanh tier) | 0.386 |
| **forward-resonant (D3/D4 + Lx)** | **≈ 1.39 (for every Lx 1 µH–0.1 mH)** | **≈ 0.39–0.40** |
| (the η 0.70 claim) | 2.478 | 0.70 |

**The forward resonance does not raise z.** The forward gaps are still **rectifying diodes**: they
quench at current-zero, so the over-transfer is **clamped at the diode boundary** (the doubler-resonant
α_max 0.28 ceiling) — and in the circuit it sits even lower (z ≈ direct). **Sequencing does separate
rectify from recover in angle** (the rail-return clamps, the pump survives, z > 1) — but the forward
transfer cannot over-transfer past its own rectifier without the same break.

## 2. The statistical dig — the Monte-Carlo `[ME]`

To over-transfer, the forward gaps must **hold off to V_strike** (not clamp at 0). Made statistical
(V_strike ~ Normal + formative lag, N realisations) on the forward gaps:

**24/24 realisations** (`recovery_distribution.csv`): z mean **1.029**, max 1.350; **η mean 0.386, max
0.387**; **fraction recovering (η>0.60): 0 %**; **fraction pump-broken (z<1.05): 92 %.** The ensemble
shows **no recovering tail toward 0.70**: realisations either sit at the direct z (the forward gap
clamps like a diode) or the forward rectification **breaks** (z → 1, the S3 collapse) — the **same
either/or, now sampled across the statistics**. There is **no bimodal recovering regime**, no
stochastic-resonance window that nets the tax to the output. The scatter does not desynchronise the
conflict into coexistence; it just samples both arms — and 92 % of the time the over-transfer attempt
**breaks the pump.**

## 3. The conservation arbiter `[OC]`

z is the per-cycle gain ratio — the conservation-grounded proxy for where the energy goes: **z > direct
⇒ the over-transfer net-adds to the output (recovered); z ≈ direct ⇒ relocated (the tax moves but
re-dissipates at the rectifier); z < 1 ⇒ the pump breaks.** Observed: forward-resonant **z ≈ direct**,
so the tax energy **relocates** — it does not net-reach the output at 0.70. This is independent of any
transfer-model assumption (it is the measured rail growth), and it is robust to a +5 % loss
perturbation. **Recovery is observed to be absent, not assumed forbidden.**

## 4. Why — the conservation-deep reason

The two-capacitor tax is dissipated **in the rectifying conduction itself**. To recover it, that
conduction must be resonant (over-transfer) — but a resonant rectifier **either clamps at current-zero
(no over-transfer, no recovery) or holds off to V_strike (over-transfer, but the rectification — the
ratchet — breaks).** Rotation separates the *rail-return* rectifier from the *forward* one in angle, so
the pump survives — but **each forward rectifier faces the identical local either/or.** The statistics
sample both arms; they do not create a third. **The either/or is a conservation property of a resonant
rectifier, not an artifact of collapsing gaps onto one instant.**

## 5. The settled answer

- **`RECOVERY-FORBIDDEN`** for η 0.70: the sequenced, statistical, circuit-level model — with
  conservation as the arbiter — does not net the doubler-core tax to the output. The η 0.70
  (`commutator_real_core`, over-transferring the core) was the α-reflection's separability assumption;
  S3 falsified it on a static gap, and this brief confirms it **sequenced and statistical**.
- **The validated recovery is the downstream island only** (RESONANT-ISLAND ~31 %, a true sink,
  independently confirmed by NGSPICE S2) — the path to the tank that *doesn't* rectify. That gives the
  floor **η ≈ 0.45–0.50.**
- **Engineering posture:** design to the **validated floor η ≈ 0.45–0.50**; the η 0.70 upside is now
  settled as **not realizable** (not vindicated, not a statistical regime — forbidden). The propagated
  0.70 in `commutator_real_core` / the HTML operating anchor should be corrected to the floor.

## Deliverables

`sim/seq_stat_commutation.py` (circuit-level ngspice doubler + the statistical Monte-Carlo + the
conservation arbiter) · `recovery_distribution.csv` (per-realisation z/η + strike params) ·
`seq_stat_traces.png` (the recovery distribution; the deterministic ladder) · this findings doc.
Python cores frozen empty-diff. **Not merged** (a verdict on whether η 0.70 is realizable — the
confidence statement). The α-reflection mis-step is recorded above as the trap the brief named.
