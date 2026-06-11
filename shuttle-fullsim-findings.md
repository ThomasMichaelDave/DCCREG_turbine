# shuttle-fullsim — gate report (rev 0.2): LR resolved; shuttle-direction HALT

**Status:** [IR] **HALTED on the shuttle direction (anchor-test arbiter).** Rev 0.2's two prior gates and the LR value are now resolved, leaving one decisive issue: the corrected shuttle direction in §1 (load from stack nodes 3/2, fire into terminal nodes 1/4 ⇒ charge **3→1 / 2→4**) is the **reverse** of the frozen solver's regenerative cross-couple (D3: 1→3, D4: 4→2). In the mandatory degenerate-limit it gives **z = 1.0 (no pump)**, so it **cannot pass the §2.3 anchor test** (`z = 1.203 ± 0.03`). Per the brief, *"a new producer is authorised only by reducing to the frozen one in this limit"* — so I stop before building the large simulator on a direction that is guaranteed to fail authorisation, and return the direction decision to TMD with evidence.

Branch: `shuttle-fullsim` (from `main` `9136624`). `reference/doubler_core.py` untouched (empty diff); `index.html` untouched.

---

## Resolved this iteration

- **T0 timing** — RESOLVED. SG1/D1 conducts in the phase where **C1 = max** (verified rev 0.1: phase A C1=1000 → {D1,D3}; phase B C1=160 → {D2,D4}). The station map re-anchors SG1/SG2 to C1/C2 **maximum**. `[OC]`
- **Export option (a)** — RESOLVED. `C(θ)`, `Cx(θ)`, `LR` to be parameterised inside `shuttle_core.py`. `[IR, TMD-approved]`
- **LR value** — RESOLVED. `L_RES` (= `L1`) ≈ **123 µH** recorded in `docs/commutator-design.md` §2 (TMD-checked/authorised 2026-06-11; origin: Block R `resonatorCore` default coupled tank, cross-listed in `docs/report-external-review.md`). `[IR]`

---

## New finding — shuttle direction vs the frozen anchor → **HALT**

**Evidence (independent 4-node solver; `doubler_core.py` untouched).** The degenerate limit of each shuttle (LR shorted, `Cx`→galvanic) is a cross-diode in the shuttle's net direction. An independent re-implementation of the frozen switched-cap cycle, run at the device point, gives:

| cross-couple direction | z (device) | pumps? |
|---|---|---|
| **D3: 1→3, D4: 4→2** (frozen / rev-0.1 shuttle) | **1.2033** | ✔ (= the anchor) |
| **D3: 3→1, D4: 2→4** (rev-0.2 "reversed" shuttle) | **1.000** | ✘ |

(The 1→3 case reproduces `ANCHORS["device"] = 1.203 ± 0.03`, validating the re-implementation; the reversed case does not pump — reversing the cross-couple destroys the regenerative feedback `D3 (1→3)`/`D4 (4→2)` that makes the doubler pump, per `index.html`'s own topology note.) `[OC]`

**Why the reversal is over-corrected.** The T0 finding (SG1 at C1 **max**) is about *timing* — which phase the events land in. It does **not** change the cross-couple's *charge direction*, which the frozen solver fixes at **1→3 / 4→2** (measured: the `xcap-duty-sign` CSV shows `Q_D3 > 0` = into node 3 = 1→3 every cycle). The shuttle's stated purpose is to carry that **1→3 ratchet** duty via a flying bucket (the committed escape from `XCAP-RATCHET-BLOCKED`), so the shuttle should move charge **1→3 / 4→2** (rev-0.1's direction), with **only the station *timing*** re-anchored to SG1/SG2-at-C-max. Rev 0.2 reversed both the timing anchor (correct) **and** the charge direction (incorrect). `[OC for the direction; IR for the reading]`

---

## Decision returned to TMD (one confirmation unblocks the full build)

- **Recommended:** keep the shuttle charge direction **frozen/rev-0.1: Branch A node 1 → island 7 → node 3 (1→3); Branch B node 4 → island 8 → node 2 (4→2)**, and apply **only** the T0 *timing* re-anchor (SG1/SG2 fire at C1/C2 **max**). Then the degenerate-limit anchor passes (z=1.203) and `shuttle_core.py` + the campaign + the timing diagram are built on the authorised direction.
- **If TMD insists on the rev-0.2 reversed direction (3→1 / 2→4):** the topology does **not** pump in the galvanic limit (z=1.0) → the result is **SHUTTLE-PUMP-BLOCKED** by the anchor test, and the shuttle returns to TMD with that binding constraint. No useful sim can be built on it.

No `shuttle_core.py` / anchor test / campaign / timing diagram built yet — gated on this one direction confirmation, to avoid investing a large build in a non-authorisable direction.

---

## Constraints honoured

- `reference/doubler_core.py` untouched (empty diff); the diagnostic is a throwaway independent solver (not committed, not imported); no private symbols; no frozen-internal edit.
- `index.html` untouched (out of scope).
- `L_RES` cited verbatim (symbol + value + section) in `docs/commutator-design.md`; symbol hygiene (`θ`/`rotor`, `Nsec`, `g`) respected; epistemic tags applied.
- Branch left for TMD review; **not merged** to `main`.
