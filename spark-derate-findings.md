# spark-derate — findings (rev 0.2): four verdict slots

**Header verdict line:**
`LOADRETURN-CONDITIONAL` · `BACKSTOP-CLEAN` · `SPARK-INDETERMINATE` · `GLOW-INDETERMINATE`.

The ideal-tier shuttle (rev-0.3 SHUTTLE-PUMP-CONFIRMED) is reproduced **exactly** (C0 regression
gate); the spark tier then adds absolute-volt Paschen strike, arc/glow conduction, the **backstop
second boss** (a gap, *not* a resistor), and fault injection. Branch `spark-derate` from
`shuttle-fullsim` head. `reference/doubler_core.py` untouched (mirror still FAITHFUL). Not merged.

Producer/consumer: `shuttle_core.py` is **extended** under regression discipline — every new
parameter defaults to the ideal value, `mode='ideal'` takes the rev-0.3 code path byte-for-byte
(`assert_ideal_identity()`), and a tripwire `_is_ideal()` guards it. `spark_derate_from_solver.py`
is a pure consumer (figures + tables). All rev-0.3 conservation assertions remain hard-fail.

**Absolute scale (cited verbatim):** gap `g`=0.5 mm (`presets/R1-baseline.json` `pgap`), V_HV=20 kV
(`vhvKV`), air field 1 kV/mm (`vhvEkVmm`), favourable-half 30°≈1.7 ms (`commutator-design.md` §6),
tank f₀=326 kHz (`f0kHz`; the old 238 kHz is *resolved/superseded*, not a contradiction), L_RES=123 µH
(`commutator-design.md` §2), C_R=1.91 nF, Q≈1000 **copper-only upper bound** (`report-tool-functioning.md`;
real Q lower → τ_tank swept). Strike/arc/glow voltages are not grounded → swept with three corners
(Kuffel et al.; J.C. Martin). Paschen strike at g=0.5 mm air with boss enhancement: opt 650 V,
mid 333 V, pess 150 V.

---

## C0 — regression gate (rev-0.3 reproduced exactly)

| ID | test | criterion | result |
|---|---|---|---|
| T0a | anchor | z = 1.2033 ± 0.03 | **PASS** z=1.2033 |
| T0b | ideal tier | z_shuttle = 1.1894 ± 0.001 + 6 angles within 1e-3 | **PASS** z=1.18938, angles ✓ |
| T0c | ledger | island ledger < 1e-6 every cycle | **PASS** drift=4.6e-14 |

`assert_ideal_identity()` passes: default `Params()` is on the ideal path and reproduces the rev-0.3
z and the six event angles. Any shift would be a defect; none occurred. `[OC]`

## Slot 1 — LOADRETURN → **LOADRETURN-CONDITIONAL** (runs first; conditions C2)

Induce one missed main fire; advance to the next load alignment; read the sign of the next `load_in`.
The load gap is bidirectional (`transition` equalises whichever way the potentials dictate).

| corner | strike (V) | outcome | T1 deterministic (≥10 seeds) |
|---|---:|---|---|
| opt | 650 | PERSISTS | ✓ (single-valued) |
| mid | 333 | PERSISTS | ✓ |
| pess | 150 | CLEARS | ✓ |

**Verdict: LOADRETURN-CONDITIONAL** — trapped charge returns to source (CLEARS) only at the
pessimistic (lowest-strike) corner; at opt/mid it persists. T1 holds: the mechanism is deterministic
(jitter varies only timing), all seeds give the same outcome. **Consequence:** single-fault
accumulation is *not* self-limiting at the realistic (opt/mid) corners → the backstop must catch
uncleared misses (drives C2's T2b/T2c). `[OC mechanism; IR corner spread]`

## Slot 2 — BACKSTOP → **BACKSTOP-CLEAN**

The backstop is a **second smaller spark-gap boss** per island: later station, lower threshold
(`pVbkBackstop` = 0.6·strike), stray `pCboss2`=6 pF permanently in the C_min sum. Effective boost =
C_max/(C_min + pCboss + pCboss2 + strays) asserted every run.

| ID | test | criterion | result |
|---|---|---|---|
| T2a | false positives | 0 unjustified backstop fires over ≥500 healthy cyc × ≥10 seeds × 3 corners | **PASS** (0; every fire follows a real miss) |
| T2b | catch | fires on every induced miss load-return doesn't clear | **PASS** (single + double faults caught) |
| T2c | accumulation bound | peak island ≤ 1.05× single-bucket with backstop; unbounded without | **PASS** (all corners bounded) |
| T2d | boost tax | pCboss2 ≥ 6 (rev-0.3 budget floor) | **PASS** (boost 17.65 → 16.22, still feasible) |
| T2e | threshold ordering | P(backstop before main boss in a healthy cycle) = 0 | **PASS** (margin 0.0 — robust to coincidence) |

**Verdict: BACKSTOP-CLEAN** — the second gap contains accumulation (every uncleared miss caught,
island bounded at ~1 bucket) with zero false positives and an acceptable boost tax. The earlier
*resistive* island→target bleed is **excluded by construction** (no galvanic element may span
structures in relative motion); the gap honours that rule. `[OC/IR]`

## Slot 3 — SPARK-BAND → **SPARK-INDETERMINATE**

Arc-mode commutation: per-conduction drop `pVarc` (20/35/50 V), hold-off recovery
`1−exp(−t_cycle/τ_rec,eff)` (τ_rec 10 µs/100 µs/1 ms, constant rotary-sweep aid), jitter.
z_spark is the clean geometric-mean per-cycle gain; the **misfire rate** is the high-rpm band edge.

| ID | test | criterion | result |
|---|---|---|---|
| T3a | arc recovery | misfire < 1% below the band edge | **PASS** (≤0.4% up to the pess edge ~4 k rpm) |
| T3b | energy ledger | mech-in = fieldΔ + itemised arc/glow/backstop losses < 1e-6 | **PASS** (itemised, finite) |
| clamp | provenance | island overvoltage clamp set by the gap, not misfire/backstop | **PASS** (≈1.04× strike, invariant rel<2%) |

- z_spark(rpm) ≈ **1.189 / 1.185 / 1.169** (opt/mid/pess), flat in rpm (clean conduction gain ≈ ideal;
  arc drop is negligible against the boosted gap voltage).
- Misfire roll-off (pess): 0% to ~4 k rpm, then 1% → 9% → 28% → 54% by 30 k rpm — the arc cannot
  deionise within the shortening cycle (recovery-failure onset, the high-rpm edge).
- **Self-excitation:** `ln(z)·f_cycle − 1/τ_tank`. At the realistic copper-upper-bound **Q≤1000**
  (1/τ≈1024 s⁻¹) the modest per-cycle gain (ln z≈0.17) needs rpm > ~62 k to self-excite the 326 kHz
  ring — outside the rpm≤30 k envelope. A band opens only at **optimistic Q≥2500** (Q=5000 →
  rpm≳15.5 k). Per the brief, optimistic-only bands are reported as such, never confirmed.

**Verdict: SPARK-INDETERMINATE** — z_spark>1 and the gap clamps are clean, but no self-exciting band
exists at the realistic Q within rpm≤30 k; the band appears only at optimistic (unconfirmable) Q.
**Binding sub-cause:** the 326 kHz tank rings down faster than the pump self-excites at Q≤1000 —
consistent with the repo's "L1-is-a-near-short, the 5–6 ring is a kicked ringdown" framing. `[OC]`

## Slot 4 — GLOW-BAND → **GLOW-INDETERMINATE**

Glow-mode: ignition at low overvoltage, conduction clamped at `pVsus` (200/300/400 V) riding the
collapse to max boost, constriction when the (scale-free) current exceeds `pIconstrict` (onset rpm
= pIconstrict·3000 → opt 15 k / mid 6 k / pess 3 k), degrading glow→arc (named event).

| ID | test | criterion | result |
|---|---|---|---|
| T4a | transfer completion | ≥99% bucket delivered before extinction, in-band | **FAIL at pess** (compl 0.998/0.994/**0.985**) |
| T4b | constriction margin | I_peak ≤ pIconstrict/2 in the claimed band | **PASS** (in-band; onset corner-ordered, counted) |
| T4c | ignition robustness | ignites across jitter at the trimmed overvoltage | **PASS** (floor reported) |

- Glow completion is high (≈99%) at opt/mid but **0.985 at pess** (pVsus=400 V is a large fraction of
  the available overvoltage), failing the 99% bar.
- Constriction onset is corner-ordered (pess constricts from ~3 k rpm) and every constriction is a
  named, counted event (glow→arc).
- Self-excitation band: same as SPARK — empty at realistic Q, optimistic-only.

**Verdict: GLOW-INDETERMINATE** — glow ignites and largely transfers, but (i) the self-excitation band
is optimistic-only and (ii) pess completion falls below 99% with constriction onset inside the band.
Not EMPTY (a band and high completion exist at opt/mid), not CONFIRMED (T4a fails at pess; band
optimistic-only). **Binding sub-causes:** completion floor at pess + the same Q-limited band. `[OC/IR]`

---

## Mode ownership (C5 band map)

Within the swept envelope (rpm ≤ 30 k, Q ≤ 1000) **neither mode self-excites the tank**; both bands
open only at optimistic Q. Where they open (optimistic Q), arc owns the high-rpm end (clean gain, no
constriction) and glow is constriction-limited at pess from ~3 k rpm. No realistic-Q dead-zone
arbitration is needed because no realistic-Q band exists. The pump itself (z_spark>1, island clamps
gap-set, accumulation backstop-contained) is sound; the open question is the **tank Q** (deferred:
mica tanδ + gap loss), which the next gate must pin.

## Constraints honoured / scope

- `reference/doubler_core.py` untouched (empty diff; mirror FAITHFUL, device z=1.2033). `index.html`
  untouched. Rev-0.3 ideal tier reproduced exactly (C0). Not merged.
- `L_RES`=123 µH cited (5–6 ring); f₀=326 kHz, Q≤1000, g=0.5 mm, V_HV=20 kV cited verbatim with source.
- Misfires, constrictions, backstop conductions are named events (`rc.events`) and counted in the audit
  tables (`spark_audit_table.csv`, `spark_backstop_table.csv`). Symbol hygiene + `[OC]/[IR]` throughout.
- **Out of scope (next gates):** the bootstrap two-threshold loop (inherits a third threshold if glow is
  adopted: spark-startup below the Paschen floor → glow near clamp), electrode erosion/lifetime
  (per-shot charge/energy logged), gas-handling/enclosure (consumes the constriction + misfire audits),
  HV insulation coordination, the contingent same-assembly island→rail resistor (only if BACKSTOP were
  HARMFUL — it is CLEAN, so not built).
