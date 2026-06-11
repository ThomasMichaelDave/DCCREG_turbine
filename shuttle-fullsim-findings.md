# shuttle-fullsim — pre-build gate report (T0 HALT + export BLOCKER)

**Status:** [IR] **HALTED / BLOCKED before build.** The brief places two hard gates *before any `shuttle_core.py` code may exist* (T0 conduction-angle check, §2.2; export sufficiency, constraint #1). Read-only verification against the frozen `reference/doubler_core.py` shows **both gates trip**, so no simulator, campaign, or timing diagram was built. This report returns the two decisions to TMD.

Branch: `shuttle-fullsim`, fresh from `main` (`9136624`). `reference/doubler_core.py` untouched (empty diff); `index.html` untouched (out of scope). Tiers: **[OC]** solver-derived / standard · **[IR]** interpretive.

---

## Gate 1 — T0 conduction-angle anchor → **HALT**

The brief's station map assumes **SG1 conducts at C1 *minimum*** (the "parallel-dump" reading, inferred from the confirmed {SG1, SG3} pairing). T0 requires checking this against the frozen solver before building. It is **false**: SG1 conducts at C1 **maximum**.

**Phase definitions (verbatim, `doubler_core.solve_doubler4`):**
- phase **B** — `C1 -> min, C2 -> max` → `solve_phase(Q, C1min, C2max, …)`
- phase **A** — `C1 -> max, C2 -> min` → `solve_phase(Q, C1max, C2min, …)`

**Conduction (inferred read-only from ideal-diode V-equality — a conducting diode shorts its endpoints; `DIODES = [(2,0),(3,0),(1,3),(4,2)]` = D1..D4):**

| phase | C1cur | C2cur | v2 | conducting |
|---|---|---|---|---|
| B | **160 (MIN)** | 1000 | −2.19e5 (≠0 ⇒ D1 off) | **D2, D4** (SG2, SG4) |
| A | **1000 (MAX)** | 160 | **0.000** (⇒ D1 on) | **D1, D3** (SG1, SG3) |

`D1 = (2→0)` conducts ⟺ `v2 = 0`; `v2 = 0.000` occurs **only in the phase where C1 = 1000 = C1max**.

> **T0 verdict: SG1 conducts at C1 MAXIMUM.** This trips the brief's HALT condition (§2.2): *"If SG1 conducts at C1 maximum instead, HALT and report — the station map shifts half a sector and TMD decides before any build."* `[OC]`

**Consequence.** The hypothesized six-event station map — `SG3a (load, C1 mid-boost) → SG1 (C1 = min, parallel-dump) → SG3b (fire) → [mirror] SG4a → SG2 → SG4b` — is anchored on SG1-at-C1-min. With SG1 at C1-max it shifts **half a sector**, so the entire load/dump/fire ordering and the closure property ("SG4b bucket series-recharges Ca→C1 while C1 is at C_max") must be **re-derived** before any build. This is a TMD decision, per the brief.

---

## Gate 2 — Export sufficiency (constraint #1) → **BLOCKER**

`shuttle_core.py` must *consume* the frozen solver's exports for **(a)** continuous `C1(θ)/C2(θ)` profiles and **(b)** `LR` (resonator inductor L1, nodes 5–6) parameters. `reference/doubler_core.py` exports **neither**.

**What `doubler_core.py` exports (verbatim):** `DIODES`; `charges_from_voltages(V, C1, C2, Ca, Cb, Cpar)`; `solve_linear(A, b)`; `solve_phase(Q, C1, C2, Ca, Cb, Cpar, eps=1e-9)` → `bestV` only; `solve_doubler4(C1min, C1max, C2min, C2max, Ca, Cb, Cpar, iterations=120, burn=60, trace=False)` → `z` or `(z, rec)`; `ANCHORS`; `run_self_test()`.

**Missing — verbatim BLOCKER list:**

```
MISSING from reference/doubler_core.py:
  1. Continuous C1(θ) / C2(θ) capacitance-vs-rotor-angle profiles.
     doubler_core takes only the discrete scalars C1min, C1max, C2min, C2max and
     switches between two phases; there is NO rotor angle θ/rotor and NO C(θ) function.
  2. LR / L1 resonator inductor and nodes 5–6.
     doubler_core is a purely-capacitive 4-node network (nodes 0–4):
       DIODES = [(2,0),(3,0),(1,3),(4,2)]; K-matrix = addK(1..4) with Ca/Cb bridges only.
     No inductor is modelled. The resonator inductance L is computed in resonatorCore()
     in index.html, NOT in this frozen mirror.
```

**Available:** the baseline `z = 1.203` (via `solve_doubler4`; `ANCHORS` "device" = 1.203 ± 0.03). `[OC]`

> **Gate-2 verdict.** Per constraint #1 (*"if needed quantities are not exported, STOP and report a BLOCKER listing them verbatim"*), the build is blocked: the two quantities the brief says to *consume from the frozen solver* are not there. The frozen 4-node mirror, by design (the L1-short / rail-collapsed-to-ground argument in `docs/commutator-design.md §2`), has no continuous angle profile and no inductor.

---

## Decisions returned to TMD

1. **T0 (station map).** SG1 fires at C1 **max**. Re-derive the six-event station map (and the Ca→C1 closure property) for the half-sector-shifted anchor, then re-issue; or revisit whether the shuttle's load/dump/fire ordering survives the shift. No build until this is fixed.
2. **Exports (source of `C(θ)` and `LR`).** Decide the authorised source, since the frozen solver cannot supply them:
   - **(a)** parameterise `C1(θ)/C2(θ)` and `LR` **fresh inside the new `shuttle_core.py`** (consuming only the *scalar* device-point cap values + `z` from `doubler_core`, plus an explicit θ-swing shape and an LR value); or
   - **(b)** **consume `resonatorCore` (and the C-I plate-geometry C(θ) basis) from `index.html`** as a second producer — a larger coupling that needs sign-off; or
   - **(c)** treat as a genuine blocker and defer LR/`C(θ)` to a model-scope revision.

No pre-committed **SHUTTLE-{PUMP-CONFIRMED | PUMP-BLOCKED | INDETERMINATE}** branch is declared: the simulation was gated out before T0's downstream campaign could run. A negative/halted result is a deliverable, not a failure.

---

## Constraints honoured

- `reference/doubler_core.py` untouched (empty diff); no private symbols imported; no frozen-internal copy-paste; no workaround built.
- `index.html` untouched (out of scope).
- Symbol names cited verbatim; `θ`/`rotor`, `Nsec`, gap `g` hygiene respected (and noted absent from the frozen mirror); epistemic tags applied.
- Branch left for TMD review; **not merged** to `main`.

## Reproduce (read-only)

```
python3 - <<'PY'
import sys; sys.path.insert(0, "reference"); import doubler_core as dc
z, rec = dc.solve_doubler4(160,1000,160,1000,100,100,20, iterations=70, burn=35, trace=True)
by = {(c,p):(c1,c2,V) for c,p,c1,c2,V in rec}; c = max(k[0] for k in by) - 1
for ph in ("B","A"):
    c1,c2,V = by[(c,ph)]
    d1_on = abs(V[1]) <= 1e-6*max(abs(x) for x in V)   # D1=(2->0) on iff v2==0
    print(f"phase {ph}: C1={c1} -> D1/SG1 {'ON' if d1_on else 'off'}")
# -> phase B: C1=160 -> D1/SG1 off ; phase A: C1=1000 -> D1/SG1 ON  => SG1 at C1 MAX
PY
```
