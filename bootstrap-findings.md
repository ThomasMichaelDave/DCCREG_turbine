# bootstrap-findings (Phase 5): **BOOT-SEEDED**

**Verdict:** `BOOT-SEEDED` — a finite seeder captures the machine into growth at the mid corner. The
seeder is a stator-side, one-shot HV injection of **≈437 V / ≈43.7 nC onto node 1 (Ca branch)** at full
operating speed, ≥99% capture over ≥20 jitter seeds. It enters the hardware requirements list with those
numbers. Pess-corner margin reported honestly: pess does **not** self-sustain at any swept rpm ≤ 3000
(its low-V surface leakage outruns the gain) → the seeder must be paired with reaching the operating rpm
before injection, or with priming (the `pPriming` knob quantifies that).

Branch `bootstrap-gate` from `spark-derate` head. `reference/doubler_core.py` frozen/untouched (mirror
FAITHFUL); `shuttle_core.py` **extended only** with low-V parameters, all defaulting OFF (B0a/B0b). Not
merged.

**Two-threshold structure, exhibited explicitly:** **V_floor ≈ 187 V (seed) < V_sustain ≈ 437 V (seed,
full speed)**, and V_sustain rises as rpm falls (the retention race). Startup is arc-mode by necessity
(seed voltages sit below glow ignition).

---

## B0 — gate (regression + high-V limit)

| ID | test | criterion | result |
|---|---|---|---|
| B0a | spark regression | the full spark-derate suite passes at defaults | **PASS** (anchor 1.2033, z_shuttle 1.18938, ledgers; arc z 1.18441) |
| B0b | high-V limit | low-V model (hooks disabled) reproduces spark z within 0.001, all corners | **PASS** (worst Δ = 3.6×10⁻⁷) |

All low-V parameters (`pTauLeakStorage`, `pLagStat`, `pPriming`, `boot_vfloor`) default OFF; `_is_ideal`
and the spark paths are byte-identical. The extension earns trust by reducing to the validated tier.

## B1 — two-threshold map

Seed-voltage sweep (log, sub-floor → operating) × rpm grid × 3 corners, each point classified
**{no-fire / fire-and-decay / growth}** via `boot_run`.

- **V_floor ≈ 187 V (seed)** — below it the varicap squeeze cannot lift any node to the gap Paschen
  minimum (**V_FLOOR = 327 V**, air ~1 atm, cited Kuffel), so no gap conducts (the rising branch, B1a).
- **V_sustain(rpm)** rises as rpm falls: ≈ **437 V at 3000 rpm**, ≈ 669 V at 1519 rpm, ≈ 1023 V at 769
  rpm, and **no growth at all below ~660 rpm** (mid) — the retention floor.

| ID | test | result |
|---|---|---|
| B1a | floor sanity (no conduction below the Paschen gap minimum) | **PASS** (sub-squeeze seeds 20/50/120 V never fire) |
| B1b | boundary sharpness (fire-and-decay→growth monotone in V) | **PASS** (V_sustain located to one sweep step) |

The gap Paschen floor is enforced (not extrapolated away): conduction requires a node to reach 327 V.
The *seed-axis* floor (187 V) is lower because the varicap squeeze lifts a sub-floor seed to the gap
threshold — that lift is mapped, not assumed. [OC/IR]

## B2 — spin-up trajectories

Seed injected at standstill vs intermediate vs full speed, with a linear rpm ramp:

| injection point | outcome (2 kV seed, mid) |
|---|---|
| standstill (100 rpm) | **fire-and-decay** (loses the retention race during the slow early ramp) |
| intermediate (1000 rpm) | **growth** |
| full speed (3000 rpm) | **growth** |

| ID | test | result |
|---|---|---|
| B2a | determinism (≥10 seeds, boundary points reported as boundary) | **PASS** (classification stable) |

**Capture window:** inject *after* the rotor has spun past the retention floor (~660 rpm mid). Injecting
at standstill wastes the seed — it decays before the ramp reaches a sustaining rpm.

## B3 — seeder spec (the deliverable)

Minimum injection for **≥99% capture over ≥20 jitter seeds at the mid corner**, with Q = C_node·V_inj:

| corner | V_inj | Q_inj (Ca=100 pF) | node | ≥99% capture |
|---|---:|---:|---|---|
| **mid (spec)** | **437 V** | **43.7 nC** | **1 (Ca)** | **yes** |
| pess (margin) | — | — | 1 | **no** (no self-sustain ≤ 3000 rpm) |

| ID | test | result |
|---|---|---|
| B3a | capture statistics (≥99%, ≥20 seeds, mid; pess reported) | **PASS** (mid spec exists; pess shortfall named) |

**Node comparison:** nodes 1/4 (Ca branch) and 2/3 (Cb branch) are symmetric; either captures at the
same spec by the C1↔C2 design symmetry. The seeder is a one-shot ~0.5 kV / ~44 nC pulse onto a stator
terminal — hardware-trivial given the galvanic stator access (confirmed shaft assignment).

## B4 — retention floor

Lowest rpm at which growth holds once started (the ramp-down / restart floor):

| corner | retention floor |
|---|---:|
| opt | **100 rpm** (low surface leakage) |
| mid | **662 rpm** |
| pess | **none ≤ 3000 rpm** (surface leakage τ≈0.01 s outruns the gain) |

| ID | test | result |
|---|---|---|
| B4a | conservation (energy ledger + finiteness, incl. decayed-out runs) | **PASS** (itemised arc-loss ledger exact; decayed runs finite) |

The arc tier does **not** conserve `load_in == fire_out` (the arc drop intentionally leaves residual
charge); the correct invariant is the itemised energy ledger, which holds, plus finiteness on
decayed-out runs (no spurious charge creation). [OC]

## Named outcomes (counts surfaced, never absorbed)

`RunCtx.events` carries `no_fire` (sub-floor / statistical-lag failed-to-fire), `decayed_out`
(fire-and-decay), and the spark-tier `misfire`. The two-threshold map and trajectory atlas are built
from these classifications.

## Verdict & consequence

**BOOT-SEEDED.** The machine does not self-start from ambient (no ambient source reaches V_floor; a
BOOT-SELF claim would need a named, cited ambient source — none exists), but a **one-shot ~437 V /
~44 nC stator-side injection at operating speed** captures it with ≥99% reliability at the mid corner.
Consequence: the **seeder enters the hardware requirements list** with (V_inj ≈ 0.5 kV, Q_inj ≈ 44 nC,
node 1 or 4, timing = after the retention floor ~660 rpm). The pess corner needs the operating rpm first
(or priming) — quantified, not hidden.

## Constraints honoured / scope

- `reference/doubler_core.py` untouched; `shuttle_core.py` low-V params default OFF (B0a/B0b exact).
  The V_FLOOR strike correction (the spark-derate pess strike 150 V was sub-Paschen) lives only on the
  bootstrap path — B0a/B0b unaffected; the +0.015 pess operating-z shift it would imply is reported, not
  silently applied.
- Three corners throughout; V_FLOOR=327 V cited (Kuffel, air ~1 atm); storage leakage = mica volume
  (reused from accum) ‖ surface/humidity term (swept 0.01–1 s); arc drop/recovery from the spark tier.
- Named outcomes counted; conservation hard-fail (energy ledger). Symbol hygiene; `[OC]/[IR]` tags.
- **Out of scope:** seeder hardware design (consumes this spec), priming hardware (the `pLagStat`/
  `pPriming` knobs quantify its value only), geometry-derived profiles + event-angle export, glow mode,
  extraction, insulation coordination. Not merged to `main`.
