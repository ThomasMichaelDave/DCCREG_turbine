# Brief: S2 — pump↔tank coupling (does the real pump deliver the assumed kick?)

**Verdict target:** replace the parameterised `E_kick` in `resonator_sim` with the **real per-cycle
energy `shuttle_core` delivers to the 5–6 tank at the revised geometry**, and decide whether that
delivery clears the 15 kV reach floor. This is the make-or-break coupling step the r2 verdict was
explicitly conditional on.

**Tiers:** `[OC]` derived/standard charge accounting · `[IR]` modelling/coupling choice · `[RH]` open/raw.

---

## 0. Repository & session setup (fresh Claude Code session)

- Branch **`s2-pump-tank-coupling`** off **`resonator-sim-r2`** (where `sim/resonator_sim.py` lives,
  validated `TANK-HOLDS-15kV`). Do **not** branch off `main`.
- `shuttle_core.py`, `reference/doubler_core.py`, `index.html` are **frozen** — empty diff required at
  the end (assert it). All coupling code is new and lives under `sim/`.
- Owns all git. Not merged. Changelog every step. On-load self-tests in every new module.

## Revision history

- r0.1 (this brief) — first coupling brief. Spine = the two un-propagated geometry corrections (§1).

---

## 1. Why this run

The r2 resonator result is `TANK-HOLDS-15kV` **given an assumed drive**. `resonator_sim.apply_kick`
injects `E_kick` straight onto C_R as a voltage jump; the island→tank transfer efficiency and the
island fire voltage are **not** in that model. Two revisions that the reach case depends on were applied
on the tank side only and **never run through the producer**:

| revision | tank side (applied) | producer side (still stale) |
|---|---|---|
| island `cx_max` 88 → **648 pF** | `E_kick` 115–171 mJ assumes 648 pF | `shuttle_core` pump **confirmed at 88 pF** (preset G1, Cx 4/88) |
| 5–6 coil 169 (cyl) → **79 µH (conical)** | `resonator_sim` L_R = 79 µH (R0-confirmed) | `L_RES_UH = 123 µH` in `shuttle_core` + `commutator-design.md §2` |

The structural problem: **the geometry that was pump-confirmed and the geometry the tank reach assumes
are different geometries.** The confirmed `z ≈ 1.189` and the balanced island ledger characterise the
*88 pF* bucket; the reach budget needs the *648 pF* bucket. Growing the bucket 7.4× changes the absolute
charge per trip and the collapse/boost dynamics (`boost_ratio = cx_max/(cx_min+strays)` jumps ≈ 5.5 → ≈
32). None of that has been simulated. S2 simulates it and asks one question: **at the real grown
geometry and the real 15 kV operating scale, what energy lands on the 5–6 tank per kick, and does it
clear the 108 mJ reach floor?**

## 2. Locked corrected inputs (lock BEFORE any run)

### 2.1 The 5–6 ring inductance — `L_R = 79 µH (conical)` `[OC]`

- The tank ring in S2 uses **L_R = 79 µH** (conical bicone loop-sum), the value r2 R0 confirmed against
  analytic f₀ (577.92 kHz, 0.00 %). **Never** 123 µH (`L_RES_UH`, stale pre-conical annotation) and
  **never** 169 µH (cylindrical, falsified).
- **Self-test (hard-fail):** `assert abs(f0(L_R=79e-6, C_R=960e-12) − 579e3) < 5e3` and
  `assert abs(Z0 − 287) < 5` Ω. If a 123 or 169 leaks in, f₀ comes out 463/318 kHz and Z₀ 358 Ω — the
  test catches it.
- **Note for the pump premise (no action, just logged):** the "5–6 collapses to common reference at PRF"
  argument that lets `shuttle_core` short the rail survives the correction — X_L@600 Hz is 0.30 Ω at
  79 µH vs 0.46 Ω at 123 µH, both ≪ Z₀ 287 Ω. So `SHUTTLE-PUMP-CONFIRMED` is unaffected by the stale L.
  The 79-vs-123 difference bites **only** in the ring, which is S2's job.
- **TMD-gated reconciliation (recommended, optional, annotation-only):** update `L_RES_UH` 123 → 79 in
  `shuttle_core.py` and `commutator-design.md §2` so the producer stops advertising 123. `L_RES_UH` is
  used in **no computation** (grep-confirmed: definition + docstring only), so this is a zero-result-impact
  doc fix — but it touches a frozen file, so it is **TMD's call**, not Claude Code's. S2 proceeds with
  L_R = 79 in the ring regardless of whether this fix is taken.

### 2.2 The grown island — new preset `G2-geometry-r2.json` `[OC]/[IR]`

- Create a new preset `presets/G2-geometry-r2.json`, cloned from `G1-geometry-r06.json` with the r2
  revisions applied. Do **not** mutate G1 (it is the record of the pre-revision buildable geometry).
- Changes from G1: `cx3max/cx4max` 88 → **648**, `cx3min/cx4min` 4 → **8** (grown island: r_out 232→350,
  gap 7.6→3 mm, +0.3 mm mica barriers); `cR` 1477 → **960** (record-only — the pump shorts 5–6, so C_R
  does not feed z); carry `L_R` 79 µH as a provenance field. C1/C2 (16/280) and Ca/Cb (309) unchanged.
- Same schema discipline as G1: `expect` block with `tol: 0`, on-load self-test `loaded == expect`.
- The grown Cx loads into the pump via `Params.cx_min/cx_max` (the existing supported path in
  `geom_shuttle_run`); C1/C2/Ca/Cb/Cpar via `set_device_caps`. **No new hook, no frozen edit.**

## 3. Interface contract — read-only consumer of the frozen pump `[OC]`

S2 reads the pump through existing public surface; it never reaches into solver internals.

- `steady_capture(P, ncyc=N)` → per-cycle rows: node V (V1–V8), signed branch charges
  (`A_load`/`A_fire`, `B_load`/`B_fire`), island potentials Q7/Q8. **`fire_out` is the per-branch
  charge the bucket sheds per cycle** — the raw delivery quantity.
- `assert_island_ledger(leds)` → must still pass at the grown Cx (load_in == fire_out, drift < 1e-6).
  If the grown bucket breaks the ledger, that is a finding, not a pass.
- `node_charges(V, caps)`, `field_energy(V, caps)` → for absolute charge/energy bookkeeping.
- End-of-run assertion: `git diff` on `shuttle_core.py` / `reference/` / `index.html` is **empty**.

## 4. Coupling topology — **TMD-gated decision** (blocks §5–§7) `[IR]`

`shuttle_core` is rail-collapsed: it gives the doubler-node charge ledger (`fire_out` at nodes 3/2 via
islands 7/8), **not** a 5–6 tank voltage. How the per-cycle doubler charge becomes a 5–6 tank kick is a
**topology choice that TMD owns** — it determines the entire extraction. Candidate maps:

- **M1 — rail-increment kick.** The 5–6 tank is across the doubler output rails; per cycle the rails gain
  ΔQ and the kick is the energy delivered across the 5–6 coil as that increment rings. `E_kick` ≈ work to
  move ΔQ at the rail voltage. (Continuous-pump → discrete-ring picture.)
- **M2 — island-dump kick.** Each island fire dumps its bucket (`fire_out` charge at `v_isl` fire
  voltage, post-collapse boost) directly into the 5–6 ring through L_R. `E_kick` = the resonant transfer
  of ½·Cx·V_fire² across the 648/960 cap ratio (the ~96 %-of-island-energy peak transfer).

**Do not pick for TMD.** Pause here, present M1/M2 (and any third reading TMD has), take the choice, then
proceed. The migration doc's "extract the real per-cycle charge to nodes 5–6" is most naturally M2, but
the rail-collapse in the producer makes M1 defensible — this is exactly the seam TMD flagged as routing
to them.

## 5. Absolute scale fixing `[OC]`

`shuttle_core` runs **scale-invariant** (normalised; `use_abs_volts = False`, z is a growth ratio). It
emits no absolute joules. Fix the scale by the operating point the clamp enforces:

- Rail / island fire voltage anchored so the steady tank sits at the clamped **15 kV** (the r2 operating
  point). Solve for the absolute `v_scale` that makes the chosen coupling (§4) deliver to a 15 kV-parked
  tank, then read absolute per-cycle charge and energy at that scale.
- Report `E_deliver_per_kick` in **mJ**, both branches, at the 15 kV scale, with the boost/collapse
  contribution itemised (load energy vs. collapse-work gain).

## 6. Model `[OC]/[IR]`

1. Load `G2-geometry-r2.json`; run §7 G0/P-anchor on the pump at the grown Cx.
2. Extract `E_deliver_per_kick` (mJ) per §4 map + §5 scale.
3. Drive the **unmodified** `sim/resonator_sim.py` tank+clamp (L_R = 79 µH, C_R = 960 pF, two-tier
   upstream-governor + crowbar clamp, Q sweep 320/500/900) with the extracted `E_kick` instead of the
   parameter. `resonator_sim` is consumed, not edited — if the real delivery is a *train* (per-cycle
   varying, ramp-up) rather than a fixed kick, drive it as the real sequence and report whether the
   single-kick assumption still holds.

## 7. Campaign (strict order)

- **G0 — re-anchor at G2.** Degenerate-limit anchor (Ca/Cb→large, C_R shorted, shuttles→ideal diodes)
  recovers z = 1.2033 ± 0.03 at the G2 caps. Authorises the grown-geometry pump. `[OC]`
- **P1 — pump at grown Cx.** z_shuttle, island ledger (drift < 1e-6), bucket budget, boost_ratio at
  cx_max=648. Report z vs the G1 88 pF z=1.189 — does growing the bucket help, hurt, or hold the pump? `[OC]`
- **X1 — extract delivery.** `E_deliver_per_kick` (mJ) at 15 kV scale, both branches, itemised (§5). `[OC]`
- **C1 — drive the tank.** Feed X1 delivery into `resonator_sim`; report tank peak, sustained, clamp
  behaviour (crowbar idle?), governor sink, across Q. `[OC]`

## 8. Named checks (report each pass/fail)

1. `f0/Z0` self-test (§2.1) — guards against 123/169 leaking into the ring.
2. G2 preset on-load self-test (loaded == expect, tol 0).
3. G0 anchor 1.2033 ± 0.03 at G2.
4. Island ledger balanced at grown Cx (drift < 1e-6).
5. `shuttle_core`/`reference`/`index.html` empty diff.
6. **Reach gate (the point of S2):** `E_deliver_per_kick` vs the **108 mJ** reach floor
   (½·C_R·V_target²) and vs the two assumed budgets — **eased 115 mJ (6 % energy margin)** and **full
   171 mJ (37 % margin)**. State which, if any, the real pump clears.
7. Energy conservation across the coupled chain (pump-delivered == tank-stored + dissipated + clamp-shed),
   < 0.1 %.

## 9. Verdict set (pre-committed; a named negative is a deliverable, not a failure)

- **`PUMP-DELIVERS-FULL`** — E_deliver ≥ 171 mJ; full drive real, +25 % headroom confirmed end-to-end.
- **`PUMP-DELIVERS-EASED-ONLY`** — 115 ≤ E_deliver < 171 mJ; eased reach real but the 6 % margin is the
  true ceiling; full-drive headroom was paper.
- **`PUMP-MARGINAL`** — 108 ≤ E_deliver < 115 mJ; clears 15 kV but inside eased's margin — no robustness;
  triggers an island re-grow or a multi-kick accumulation study.
- **`PUMP-UNDERDELIVERS`** — E_deliver < 108 mJ; single-kick reach fails. The r2 `TANK-HOLDS-15kV`
  becomes conditional-unmet; escalate to TMD (re-grow Cx further, raise fire voltage, or accept an
  accumulating-tank regime — which would also break the upstream-governor "cold-tank cap" guarantee, see
  r2 findings caveat).
- **`LEDGER-BREAK`** — grown bucket violates island charge conservation; the 648 pF island is not a clean
  shuttle and the geometry needs rework before any reach claim.

## 10. Deliverables

- `sim/s2_coupling.py` (new; consumer-only), `presets/G2-geometry-r2.json`, `sim/s2-coupling-findings.md`
  (verdict + the §8 check table + E_deliver itemisation), coupled traces PNG, `E_deliver` CSV.
- A one-line update to the r2 findings' conditionality (now resolved or escalated), routed through TMD.

## 11. Out of scope (this run)

- Real spark-gap geometry / strike-arc-quench at the gaps (that is **S3** — gated on the gap hardware
  being drafted into the DXF first).
- Glow/void V_glow physics from Paschen (**S4**). Full-system dissipation/thermal (**S5**).
- Any edit to `shuttle_core`, `doubler_core`, `index.html`, or `resonator_sim` beyond consuming them.
- Rotor RPM/material choice (separate open decision; affects PRF, not single-kick reach).

## 12. Roadmap after S2

S3 spark tier at real gaps → S4 glow/void → S5 full integration + dissipation. S2's `E_deliver` becomes
the locked drive for all of them, retiring the last parameterised input on the drive side.
