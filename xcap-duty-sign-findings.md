# xcap-duty-sign — D3/D4 duty-sign findings

**Outcome:** **XCAP-RATCHET-BLOCKED** — at the device operating point each cross-couple (D3, D4) conducts the **same sign** of charge every cycle. A two-terminal series ("flying") capacitor in the D3/D4 branch cannot carry this duty: it would charge to one polarity and block steady-state transfer. The current single-gap Cx proposal is **closed** on this necessary-condition screen.

**Scope note (authorised reduction).** The first-pass export screen (§A) found `dV_k` at conduction *onset* not reconstructable from the frozen mirror's exports without re-implementing solver internals (BLOCKER). TMD authorised **option (i): the charge-sign-only screen** — drop the `dV_k` chart/CSV column and the `sign(Q)`↔`sign(dV)` self-assert, and replace it with the **forward-bias fact**: an ideal diode conducts only forward, so `sign(dV_onset) = +` by the conduction condition. The signed transferred charge `Q_k` (the primary duty-sign quantity) **is** reconstructable, so the gate is answered cleanly. `reference/doubler_core.py` is untouched (empty diff); `index.html` untouched (out of scope).

Branch: `xcap-duty-sign`, fresh from `main` (`9136624`). Tiers: **[OC]** solver-derived / standard charge accounting · **[IR]** criterion / display choices.

---

## A. Export screen (why the scope was reduced)

`reference/doubler_core.py` exports (verbatim): `DIODES = [(2,0),(3,0),(1,3),(4,2)]` (D1..D4 anode→cathode); `charges_from_voltages(V, C1, C2, Ca, Cb, Cpar)` → `np.array([q1,q2,q3,q4])` (forward map V→Q); `solve_linear(A, b)`; `solve_phase(Q, C1, C2, Ca, Cb, Cpar, eps=1e-9)` → **`bestV` only** (post-conduction node voltages; the winning diode mask is internal, not returned); `solve_doubler4(C1min, C1max, C2min, C2max, Ca, Cb, Cpar, iterations=120, burn=60, trace=False)` → `z`, or `(z, rec)` with `rec` = `(cycle, phase:"B"|"A", C1cur, C2cur, [v1..v4])` (**post-phase `V`**, two records/cycle); `ANCHORS`; `run_self_test()`. The mirror is the pure electrical solver — **no rotor angle `θ`/`rotor`, no `Nsec`, no gap `g`** (so the brief's `θ_k` is not a solver export).

- **Signed transferred charge `Q_k`** — reconstructable from the trace + `charges_from_voltages` (§B). ✔
- **`dV_k` at conduction onset** — needs the all-off pre-conduction voltages (an inverse charges→voltages solve at the new caps), which no export provides; building it would re-implement `solve_phase`'s internal capacitance-matrix assembly. ✘ → dropped under option (i).

---

## B. Method (charge-sign screen) — `d3_duty_sign_from_solver.py`

Pure consumer of `doubler_core.py` (no core edit, no private symbols). Per cycle, the signed charge through a cross-couple is recovered by **conserved-charge differencing on the event's sink node**, because in the phase that diode conducts its sink node has exactly one delivering diode (the other return is off, verified per event):

- **D3** (phase A, sink **node 3**; D2 off): `Q_D3 = q3(V_A) − q3(V_B)`, where `q3(·)` is the node-3 component of `charges_from_voltages` (= `Cpar·v3 + Cb·(v3−v4)`, independent of C1/C2). `q3(V_B)` is the conserved onset charge entering phase A (mirrors the solver's own `Q = charges_from_voltages(V_B, C1min, C2max, …)`).
- **D4** (phase B, sink **node 2**; D1 off): `Q_D4 = q2(V_B) − q2(V_prevA)`, `q2(·) = Cpar·v2 + Ca·(v2−v1)`.

**Sign convention** (matches brief §2.2 and `DIODES`): `+` = charge **into** the sink = **1→3** for D3, **4→2** for D4 — the diode's forward direction.

**Operating point / window.** Device preset: `C1,C2 = 160–1000 pF`, `Ca = Cb = 100`, `Cpar = 20`; measured `z = 1.2033`. Run `iterations = 60` so `max|V| < 1e6` throughout — the solver's overflow rescale never fires, so all cycles share one scale and per-cycle magnitudes are directly comparable (70 already trips the 1e6 rescale). **Steady-state criterion [IR, adjusted, normalised]:** the diode-ideal pump grows ×z per cycle (no fixed magnitude), so convergence is applied to the per-branch ratio `|Q_k|/|Q_{k−1}|` (which → constant `z`), within 1% relative change for 3 consecutive cycles on both branches; then ≥ 20 further cycles form the analysis window. Here the window is **cycles 9–59 (51 events/branch)**.

**Self-assertions (on load):** event count ≥ 20/branch ✔; every window event forward-signed (`Q_k > 0`) — the forward-bias substitute for the dropped `sign(dV)` check ✔ (0 violations); sink-node not clamped to ground per event ✔ (0 flags).

---

## C. Result (table evidence)

`d3_duty_sign_events.csv` (full, 59 events/branch) + `d3_duty_sign_chart.png` (signed `Q_k` and `|Q_k|/|Q_{k−1}|` per branch). Window excerpt:

| branch | cycle | Q_signed | sign | \|Q_k\|/\|Q_{k−1}\| |
|---|---|---|---|---|
| D3 | 9  | 8.178e+02 | + | 1.20835 |
| D3 | 10 | 9.865e+02 | + | 1.20629 |
| D3 | 58 | 7.131e+06 | + | 1.20327 |
| D3 | 59 | 8.581e+06 | + | 1.20327 |
| D4 | 9  | 7.562e+02 | + | 1.19685 |
| D4 | 10 | 9.070e+02 | + | 1.19941 |
| D4 | 58 | 6.501e+06 | + | 1.20327 |
| D4 | 59 | 7.822e+06 | + | 1.20327 |

- **D3:** 51/51 window events `+` → sign sequence **constant**.
- **D4:** 51/51 window events `+` → sign sequence **constant**.
- Magnitude ratio → `z = 1.20327` on both branches (the pump's per-cycle gain); the per-event *direction* never reverses.

**[OC] corroboration:** this is exactly what the topology forces — D3 `(1→3)` and D4 `(4→2)` are one-way ideal diodes, conducting once per cycle in their forward direction only, so the per-event charge sign is structurally invariant. The screen confirms it on the actual converged cycle (it is not assumed).

---

## D. Declared outcome & consequence

**XCAP-RATCHET-BLOCKED** (`s_k` constant across the window for both D3 and D4). Per the brief's pre-committed consequence:

- A two-terminal series flying cap in the D3/D4 branch **cannot carry the duty** (it integrates a one-signed charge and saturates, blocking steady-state transfer). The single-gap `Cx3`/`Cx4` proposal as drawn is closed on this necessary-condition screen.
- **Viable escapes** (not evaluated here): (a) a **second gap per island** restoring shuttle/reset (bidirectional) behaviour; or (b) **cycle re-derivation** that makes the branch duty AC. Either is a new architecture step.
- **Caveat (necessary, not sufficient):** this screens the *existing galvanic* cycle. Inserting `Cx3`/`Cx4` would itself perturb the cycle; a Phase-2 Cx-topology model (new module, frozen core untouched) would be needed to settle sufficiency. Out of scope here.

---

## E. Reproduce

From repo root, no arguments, deterministic:

```
python3 d3_duty_sign_from_solver.py
# device z = 1.2033 ; events D3=59 D4=59 ; window cycles [9..59] = 51
# D3: signs=+++…+  (constant)
# D4: signs=+++…+  (constant)
# reverse-sign events: 0 ; sink-clamp flags: 0
# OUTCOME: XCAP-RATCHET-BLOCKED
```

Requires `numpy` + `matplotlib` (the same deps `reference/doubler_core.py` and the other reference `.py` already use). Writes `d3_duty_sign_events.csv` and `d3_duty_sign_chart.png` beside the script.

## F. Constraints honoured

- `reference/doubler_core.py` untouched (empty diff); no private symbols imported; no core workaround.
- `index.html` untouched (out of scope).
- All symbol names verified verbatim against the code; epistemic tags applied.
- Branch left for TMD review; **not merged** to `main`.
