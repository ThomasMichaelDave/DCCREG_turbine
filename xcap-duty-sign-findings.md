# xcap-duty-sign — Export-sufficiency screen & BLOCKER

**Status:** [IR] **BLOCKER.** Per brief §2 (blocker protocol) the first step is to inspect `reference/doubler_core.py`'s exports and report whether they suffice to reconstruct, per D3/D4 conduction event, the **signed transferred charge** and the **node voltages at conduction onset**. They do **not**: the signed charge is reconstructable, but `dV_k` at conduction onset (and the event angle `θ_k`) are not available without re-implementing solver internals — which §2.2 forbids. So I STOP here; the T2 consumer script and the T3 three-way determination (XCAP-AC-CONFIRMED / XCAP-RATCHET-BLOCKED / XCAP-INDETERMINATE) were **not** executed.

Branch: `xcap-duty-sign`, fresh from `main` (`9136624`). `reference/doubler_core.py` untouched (no diff). `index.html` untouched (out of scope).

---

## 1. What was inspected

`reference/doubler_core.py` — the frozen Python mirror of `solveDoubler4` (asserted faithful to the JS anchors by its own `run_self_test()`). Inspected as a pure consumer; no import of private symbols, no edit to the core.

## 2. Exports available (verbatim symbol names)

| Symbol | Signature / return | Notes |
|---|---|---|
| `DIODES` | `[(2, 0), (3, 0), (1, 3), (4, 2)]` | D1..D4 as (anode → cathode) [OC] |
| `charges_from_voltages(V, C1, C2, Ca, Cb, Cpar)` | `np.array([q1, q2, q3, q4])` | per-node **stored charge** from node voltages (forward map V→Q only) |
| `solve_linear(A, b)` | `x` or `None` | generic dense solve |
| `solve_phase(Q, C1, C2, Ca, Cb, Cpar, eps=1e-9)` | returns **`bestV` = `[v1, v2, v3, v4]` only** | the winning **post-conduction** node voltages. The winning diode mask `d = [d1,d2,d3,d4]` is computed internally (loop `for s in range(16)`) but **not returned**. The capacitance-matrix assembly (`kd1..kd4`, `addK`) is internal. |
| `solve_doubler4(C1min, C1max, C2min, C2max, Ca, Cb, Cpar, iterations=120, burn=60, trace=False)` | `z`, or `(z, rec)` when `trace=True` | `rec` = list of per-phase records `(cycle:int, phase:"B"|"A", C1cur:float, C2cur:float, V:[v1,v2,v3,v4])`, two per cycle. **`V` is post-phase** (after `solve_phase`). |
| `ANCHORS`, `run_self_test()` | — | fidelity harness |

**Symbol-hygiene check (per §3):** `doubler_core.py` is the pure *electrical* solver. It contains **no rotor angle** (`θ`/`rotor`), **no sector count** (`Nsec`), **no gap** (`g`). The trace is indexed by `cycle` (int) and `phase` (`"B"`/`"A"`) plus the cap values `C1cur`/`C2cur` — there is no angular coordinate. (Confirmed against the actual code; no assumed names.)

## 3. Sufficiency for the per-event quantities the brief requires (§2.2 / §2.4)

### (a) Signed transferred charge `Q_k` — **RECONSTRUCTABLE** [OC]
In the canonical galvanic cycle each cross-couple's sink node has exactly one delivering diode in the phase it conducts (D2/D1 are off then), so charge into the sink is attributable to D3/D4 alone. Using **only** the exported `charges_from_voltages` and the trace's per-phase recorded caps:

- D3 conducts in phase **A** (`C1max, C2min`); its sink is node 3. The conserved node-3 charge entering phase A equals the node-3 component of `charges_from_voltages(V_B, C1cur_B, C2cur_B, …)` where `(V_B, C1cur_B=C1min, C2cur_B=C2max)` is the **preceding phase-B record** (this mirrors the solver's own `Q = charges_from_voltages(V, C1cur, C2cur, …)`). Then
  `Q_D3,k = charges_from_voltages(V_A, C1max, C2min, …)[2] − charges_from_voltages(V_B, C1min, C2max, …)[2]`.
  Sign convention maps directly: **+ = charge into node 3 = 1 → 3** (the brief's D3 convention). D2-off is verifiable per event (`|v3| ≉ 0`).
- D4 conducts in phase **B**; sink node 2; analogous differencing on index `[1]`. **+ = 4 → 2**. D1-off verifiable (`|v2| ≉ 0`).

This is enough to answer the **primary** ratchet-vs-AC question (the sign sequence `s_k = sign(Q_k)`).

### (b) `dV_k` at conduction **onset** — **NOT RECONSTRUCTABLE** [BLOCKER]
"Onset" is the all-diodes-**off** state at the *new* cap values, given the conserved charges, *before* `solve_phase` clamps the conducting diodes. The trace records only **post**-phase `V` (where D3 has already shorted `v1 = v3`, so `V1 − V3 ≈ 0` — the wrong quantity). Recovering the onset `(V1 − V3)` requires an **inverse** map (charges → voltages) at a given cap config with all diodes off. No export provides it:

- `charges_from_voltages` is **forward only** (V → Q).
- `solve_phase` returns the **winning** (post-conduction) state and offers no way to request the all-off mask; its capacitance matrix (`kd1..kd4`, `addK`) is internal and not exported.

Reconstructing onset voltages would mean **re-implementing `solve_phase`'s internal matrix assembly** in the consumer — reaching into solver internals, which **§2.2 forbids** ("read exported outputs only, never reach into solver internals … Do not work around"). `dV_k` is required by T2.2, charted in T2.4 panel 2, and used in the T2.4 self-assertion (`sign(Q_k)` consistent with `sign(dV_k)` at onset). Without it those tasks cannot be done as specified.

### (c) Event angle `θ_k` — **not a solver export** [missing]
There is no rotor angle in this electrical mirror (§2 above). `θ_k` could only be assigned by a design-layer phase→angle mapping (the 30° stroke offset), which is `[IR]` and lives outside `doubler_core.py`.

### (d) Per-event diode mask — inferable, not exported
`solve_phase` returns `bestV` only. Which diodes conducted is **inferable** from post-`V` equality (`D1: |v2|≈0`, `D2: |v3|≈0`, `D3: |v1−v3|≈0`, `D4: |v4−v2|≈0`), but the explicit winning `d` is not returned.

## 4. BLOCKER declaration

Per brief §2.2, the exports are **sufficient** for the signed transferred charge `Q_k` (the primary duty-sign quantity) but **insufficient** for:

1. **`dV_k` at conduction onset** (T2.2 / T2.4) — needs an all-off onset solve the exports do not provide.
2. **Event angle `θ_k`** (T2.2) — absent from the electrical mirror.

STOP per protocol. No consumer script, no chart/CSV, no XCAP-{AC|RATCHET|INDETERMINATE} determination produced.

## 5. Context for TMD (not a decision taken here)

- **The gate is answerable from `Q_k` signs alone**, which *are* reconstructable. As an `[OC]` structural note on the *existing galvanic* cycle: D3 and D4 are one-way ideal diodes that conduct only forward (D3: 1→3 in phase A; D4: 4→2 in phase B), so per-event charge sign is structurally constant → this is *consistent with* an **XCAP-RATCHET-BLOCKED** outcome. The brief rightly insists on measurement (and notes inserting Cx would perturb the cycle), so this is offered as orientation, not a determination.
- **Unblock options (any one is enough):**
  - **(i) Charge-sign-only screen** — drop the `dV_k` chart and replace the consistency self-assertion with the forward-bias fact (`sign(dV_onset) = +` by the conduction condition). I can then deliver the three-way determination from `Q_k`. *Cleanest discipline; recommended.*
  - **(ii) Authorise a consumer-side all-off onset solve** — re-state the documented circuit topology in the new script and solve it with the exported `solve_linear` to recover `dV_k`. This re-derives the network matrix outside the frozen core and stretches "read exported outputs only," so it needs explicit sign-off.
  - **(iii) Export onset `V` / the winning diode mask from `doubler_core.py`** — disallowed here (the core is frozen).
- `θ_k`, if wanted, is a separate `[IR]` design-layer mapping; not needed for the duty-sign gate.

## 6. Constraints honoured

- `reference/doubler_core.py` untouched (empty diff). No private symbols imported; no workaround built.
- `index.html` untouched (out of scope, §5).
- Epistemic tags applied; symbol names verified verbatim against the code.
