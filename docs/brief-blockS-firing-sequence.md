# brief-blockS-firing-sequence.md

**Version:** v0.1
**Status:** ready for implementation
**Target:** `index.html` (Rotary Electrostatic Machine calculator)
**Owner role split:** authored in Claude.ai (scrutiny); to be implemented by Claude Code against the live repo.

> Tiers: **[OC]** standard physics/math · **[IR]** design/display choice · **[RH]** framing.
> Firewall: this is EE-only. No substrate/DCCREG concepts enter here.

---

## CHANGELOG
- **v0.1** — initial brief. Adds read-only `traceDoubler4` sibling + presentational **Block S** (four panels: gap voltages, conduction logic, 5–6 tank, polar clocking map). Reference `.py` prototypes attached.

---

## 0. Purpose & one-paragraph summary

Add a new **presentational block** that visualises the spark-gap firing sequence and its mechanical clocking, driven by the *actual* doubler solver rather than hand-set curves. The solver is **not modified**; a read-only sibling `traceDoubler4` reuses the frozen primitives to expose a per-phase voltage trace, and Block S consumes that trace plus the geometry block's `Nsec` to draw four time/angle-aligned panels. The block is a pure sink — it never writes solver state.

---

## 1. HARD CONSTRAINTS — do not touch

- **Frozen, byte-identical:** `solveLinear`, `chargesFromVoltages`, `solvePhase`, `solveDoubler4`, `zSym`, and the existing `VERIFY`/`runSelfTest` rows. The final diff must show these as **unchanged**.
- **Producer/consumer:** Block S reads existing state; it must not mutate `state.*` solver inputs or feed anything back into the solver path.
- **No new dependencies / no build step:** vanilla JS, single file, no network, **no `localStorage`/`sessionStorage`**.
- **Single source of truth for timing:** PRF and `Nsec` are *consumed*, not re-derived privately (see §3).

---

## 2. Solver layer — add `traceDoubler4` (sibling, read-only)

Add **next to** `solveDoubler4` (do not edit `solveDoubler4`). It mirrors the exact loop and records each phase, reusing the frozen `chargesFromVoltages`/`solvePhase`. A self-test (see §6) asserts its `z` equals `solveDoubler4`'s so the two cannot silently diverge.

```js
// Read-only SIBLING of solveDoubler4: identical loop, records the per-phase
// trace. Reuses the frozen primitives; does NOT modify them.            [OC]
function traceDoubler4(C1min, C1max, C2min, C2max, Ca, Cb, Cpar, opts){
  const iterations = opts?.iterations ?? 120;   // match solver for z-equality
  const burn       = opts?.burn       ?? 60;
  let V = [-1, 0, 0, -1];                        // down-pumping seed, |V|=2
  let C1cur = C1max, C2cur = C2min;              // notional end of phase A
  const ratios = [], trace = [];
  let prevMag = Math.abs(V[0]) + Math.abs(V[3]);
  let cumScale = 1;                              // running rescale product
  for (let cyc = 0; cyc < iterations; cyc++){
    // phase B: C1 -> min, C2 -> max
    let Q = chargesFromVoltages(V, C1cur, C2cur, Ca, Cb, Cpar);
    V = solvePhase(Q, C1min, C2max, Ca, Cb, Cpar);
    C1cur = C1min; C2cur = C2max;
    trace.push({cyc, phase:"B", c1:C1cur, c2:C2cur, V:V.slice(), scale:cumScale});
    // phase A: C1 -> max, C2 -> min
    Q = chargesFromVoltages(V, C1cur, C2cur, Ca, Cb, Cpar);
    V = solvePhase(Q, C1max, C2min, Ca, Cb, Cpar);
    C1cur = C1max; C2cur = C2min;
    trace.push({cyc, phase:"A", c1:C1cur, c2:C2cur, V:V.slice(), scale:cumScale});

    const mag = Math.abs(V[0]) + Math.abs(V[3]);
    if (cyc >= burn && prevMag > 1e-15 && mag > 1e-15) ratios.push(mag/prevMag);
    prevMag = mag;
    const maxV = Math.max.apply(null, V.map(Math.abs));
    if (maxV > 1e6 || (maxV < 1e-6 && maxV > 0)){
      const s = 1/maxV; V = V.map(v=>v*s); prevMag *= s; cumScale *= s;
    }
  }
  ratios.sort((a,b)=>a-b);
  const z = ratios.length ? ratios[Math.floor(ratios.length/2)] : 1.0;
  return {z, trace};
}
```

**De-scaled relative magnitude.** Because the loop rescales to avoid overflow, the consumer must reconstruct monotonic growth as `Vtrue_i = record.V[i] / record.scale`. All Block-S magnitudes derive from `Vtrue`, then are normalised per display window. This keeps the z-growth correct regardless of where a rescale lands.

**Trace indexing (fixed):** `V = [v1, v2, v3, v4]` → `V[0..3]`. Phase **B** = C1 at min (stroke 1, SG3). Phase **A** = C2 at min (stroke 2, SG4).

---

## 3. Consumer wiring

- Add `renderSequence()`; call it at the **end** of the existing draw pass in `recompute()` (after the current charts), read-only.
- **Inputs consumed:**
  - solver caps: `c1min, c1max, c2min, c2max, ca, cb, cpar` (from `state`, min/max-normalised as `zNow()` does).
  - **`Nsec`** — from the geometry block. If the geometry block exposes the sector count under a different id, read that; do **not** introduce a private copy.
  - **PRF** — from the rotation/timing computation (`PRF = ⌈Nsec/2⌉ · RPM/60`). The linear panels' time axis and the clocking map's `f_rot = PRF/⌈Nsec/2⌉` must both derive from this **one** value. If PRF is not currently exposed, compute it once in a shared helper, not per-panel.
- **Re-run cost:** `traceDoubler4` is ~120×2 phases of a 16-state search, sub-ms — safe on every debounced `scheduleRecompute`.

---

## 4. New inputs — `s*` namespace

Append to `FIELDS` (numeric ones hash-serialise automatically). `s*` prefix avoids host field-id collisions (same rule as `p*`). **Do not** add `Nsec` or PRF here — they are consumed (§3).

| id | label | default | min | max | step | meaning |
|---|---|---|---|---|---|---|
| `snshow` | display cycles | 6 | 2 | 12 | 1 | asymptotic cycles shown in linear panels |
| `sf0` | tank f₀ (kHz) | 238 | 1 | 2000 | 1 | resonator panel carrier **[IR]** |
| `sq0` | tank Q | 40 | 1 | 500 | 1 | resonator ring decay **[IR]** |
| `svfire` | SG fire fraction | 0.70 | 0.10 | 0.99 | 0.01 | **reserved/inactive** until fork F-S1 (saturation clamp) |
| `sfollow` | show followers | on | — | — | — | toggle SG1/SG2 traces; serialise manually in `writeHash`/`loadFromHash` like `pdiel` |

---

## 5. Panels — port from reference `.py` to canvas 2D

Four `<canvas>` in a new `<section class="panel">` titled **"Firing sequence & clocking (Block S)"**, drawn in the existing 2D-context chart idiom. Reference prototypes (commit to `reference/`, not served): `doubler_core.py`, `sg_sequence_from_solver.py`, `clocking_map.py`.

### 5.1 `seq-v` — gap voltages
- Traces: `|V1−V3|` (SG3) and `|V4−V2|` (SG4) per cycle, using `Vtrue`. SG3 peak = `|V[0]−V[2]|` @ phase B; SG4 peak = `|V[3]−V[1]|` @ phase A.
- Show the last `snshow` cycles; normalise window to its max.
- Between the two solver samples bounding a stroke, interpolate the convex **1/C** rise (anchored to the exact endpoints): `rise01(τ) = (1/C(τ) − 1/Cmax)/(1/Cmin − 1/Cmax)`, `C(τ)=Cmax·(1−(1−1/κ)τ)`, `κ = C1max/C1min`. **[IR]**
- Mark fire instants; annotate measured `z` and that peaks grow ×`z`/cycle.
- **Axis label: normalised / arbitrary** — the solver returns an eigenvector; absolute kV is set by the operating point (fork F-S3), not here. **[RH]**
- Title note: *diode-ideal trajectory; SG firing clamps this at breakdown (fork F-S1).*

### 5.2 `seq-logic` — conduction logic
- Four step traces: SG3, SG1, SG4, SG2 (1 = conducting). SG3+SG1 in stroke 1, SG4+SG2 in stroke 2; follower lag small. Toggle SG1/SG2 via `sfollow`.
- Stroke bands shaded (stroke 1 = SG3 colour, stroke 2 = SG4 colour).

### 5.3 `seq-tank` — resonator across 5–6
- One impulse-kicked damped ring per transfer: kick amplitude ∝ `Vtrue` at that stroke (`|V[0]|` @B for SG3 +sign, `|V[3]|` @A for SG4 −sign), so the envelope **grows as the pump ramps**. Carrier `sf0`, decay from `sq0` (`τ = Q/(π f₀)`). Draw ± envelope + faint carrier; small inset zoom of the carrier (~30 µs).
- **Caption: the only bench-measurable curve** — nodes 1–4 are on the free counter-rotating stator and unprobeable; galvanic access is the two rotor halves via the shaft ends = nodes 5–6. **[RH]**
- Tag the coupling/amplitude as **[IR] placeholder** (fork F-S2).

### 5.4 `seq-clock` — polar clocking map
- Polar canvas. `groups = ⌈Nsec/2⌉` repeats around one revolution; `pitch = 720/Nsec` deg; `stroke_off = pitch/2`; follower `lag` small.
- Four concentric rings (outer→inner: SG3, SG1, SG4, SG2). Within-group angular offsets: SG3 `0`, SG1 `lag`, SG4 `pitch/2`, SG2 `pitch/2 + lag`. Draw a wedge per group per ring (width = conduction-window angle).
- Theta zero at top, direction = rotation sense. Centre summary: `Nsec`, `groups/rev`, `PRF`, `f_rot`, `T_rev`, `pitch`, `stroke_off`.
- **Notes:** absolute angular origin is arbitrary (pinned only by a sector-zero reference); the **relative** clocking (pitch, stroke offset, follower lag) is the deliverable. Wedge **width/lag are display placeholders [IR]** — real angles come from the switch-timing sim via `f_rot` (fork F-S4).
- This panel **reacts to `Nsec`** from geometry — that coupling is its reason to exist.

---

## 6. Self-tests — add Block-S rows to the existing table

1. **tracer ≡ frozen:** `traceDoubler4(160,1000,160,1000,100,100,20,{iterations:120,burn:60}).z` equals `solveDoubler4(160,1000,160,1000,100,100,20)` within `1e-9`.
2. **z-growth wired right:** median of consecutive SG3 peak ratios (from `Vtrue`, device point) within `0.01` of the tracer `z`.
3. **tank monotone:** with `z>1` (device), successive kick amplitudes strictly increasing.
4. **clocking geometry:** `groups === Math.ceil(Nsec/2)` and `pitch === 720/Nsec` for `Nsec ∈ {8,12}`.

---

## 7. CSS theme variables

Add de-collided colours to `:root` (and the dark/light variants if both exist), matching the cross-section legend discipline:
`--sg3:#1f77b4; --sg2:#5fa8d3; --sg4:#d62728; --sg1:#e8857f; --res:#7d3cb5;`
Panels must read these vars, not hard-coded hex.

---

## 8. Hash & presets
- `snshow, sf0, sq0, svfire` round-trip via `FIELDS`/`writeHash`/`loadFromHash`.
- `sfollow` (boolean) serialised manually.
- No new presets required; existing doubler presets must still drive Block S unchanged.

---

## 9. Open forks / dependencies (track, do not implement here)
- **F-S1** — SG `V_fire` clamp (saturation): activate `svfire` so growth saturates into a steady-state ring instead of climbing forever. Until then the linear panel normalises per-window.
- **F-S2** — real series-LC tank coupling driven by transferred charge per stroke; settles the decay-vs-ring-up question. Replaces the `seq-tank` placeholder kick model.
- **F-S3** — absolute kV: tie the operating point to the breakdown ceiling so the y-axis can leave normalised units.
- **F-S4** — conduction-window & follower-lag **angles** from the switch-timing sim (quench/`V_fire`), via `f_rot`. Currently display placeholders.
- **DEP** — PRF/`Nsec` must come from the single timing source (§3); confirm the geometry block's field ids during wiring.

---

## 10. Acceptance criteria
- [ ] Diff shows frozen solver functions **unchanged**; only additions (`traceDoubler4`, Block S, `s*` fields, CSS vars, self-test rows).
- [ ] All existing self-tests still green; four new Block-S rows green.
- [ ] No `localStorage`/`sessionStorage`, no network, on-load self-test runs.
- [ ] `s*` params hash round-trip; `sfollow` toggle persists.
- [ ] Block S is read-only (no solver-state mutation); changing `Nsec` in geometry visibly updates `seq-clock` group count and pitch.
- [ ] Linear panel time axis and clocking map `f_rot` derive from one PRF source.
