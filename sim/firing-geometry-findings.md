# Findings — FIRING-GEOMETRY: clock from the DXF stations, then sweep station/radius/ball

**Branch** `firing-geometry` (off `netlist-gaps-rederive`). **Verdict:** **`STATIONS-CONFIRMED +
HINTS`.** Clocking the commutator from the real **DXF 00-FIRING-STATIONS** (not the assumed window)
holds **η_real ≈ 0.70** — the resonant transfer fits the electrode-overlap window with **~111 µs of
margin** (overlap 115 µs ≫ t½ 2.2 µs), so the ⚠ timing flag is **resolved by geometry, not sign-off**.
The sweep's headline design finding: the binding constraint is **not** the window but **cross-fire**
at the tightest station pair (**SG3b→BS3, 2.95°**). The radius is critical for *that*, not for the
resonant fit.

Frozen `doubler_core`/`shuttle_core` read-only (direct-limit anchor α→0 → z 1.334 / η 0.386);
`commutator_real_core` reused. **Not merged** (design-exploration; feeds the gap-placement spec).

## §-checks (brief §6)

| # | check | result |
|---|---|---|
| 1 | frozen empty-diff; clocked from the **DXF stations** | ✓ byte-identical; STATIONS = DXF (SG1 3.0°…BS4 49°) |
| 2 | baseline α_max/η at real timing vs idealized 0.70 | ✓ **η_real 0.703**, α_max 0.807, fit margin **111 µs** → `STATIONS-CONFIRMED` |
| 3 | overlap-window model + **the radius criticism** (µs/°) | ✓ overlap 2.07°/115 µs; A1 margin 111 µs; **A2 cross-fire margin 0.88°** at r=387/12 mm |
| 4 | lookup table; A1–A4 per combination; viable region | ✓ 1260 combos, **798 viable**; failures: A1 **0**, A2 **462** → cross-fire dominates |
| 5 | design hints; radius/ball envelope; cross-fire boundaries | ✓ below |
| 6 | conservation guard at the operating point | ✓ ring closes 9.4e-12 + trips; FE perturbable |

## 1. Baseline — the real timing holds η (brief §1) `[ME]`

Clocking `commutator_real_core` from the DXF stations, the **conduction window = the electrode-overlap
window** `Δθ_overlap = (d_ball + 2·g_lat)/r`. At the established **12 mm W-Cu spheres**, **r = 387 mm**,
**3000 rpm**: overlap = **2.07° = 115 µs**, while the fire needs `t_strike + t½ + t_conduction ≈
4.3 µs` (t½ = the island Lx ring, 2.2 µs). **Fit margin = 111 µs** — the transfer fits trivially, so
η_real = **0.703** (the FE-bleed dwell is the real, *shorter* overlap window → if anything slightly
better than the 278 µs-assumed 0.697). **Not `WINDOW-LIMITED`.**

## 2. The overlap-window model + the radius criticism (brief §2/§4) `[OC]`

The physical spine: a gap fires only while its two balls are within striking range. Two regimes:
- **A1 (window-fits, time):** `t_overlap = Δθ_overlap/ω ≥ t_strike+t½+t_cond`. **Never binds** — even
  at r = 491 mm and **30 000 rpm** the overlap stays above the 4.3 µs need (the `max_rpm_A1` column is
  `>30k` at every radius). The time window is enormous vs the µs-scale resonant transfer.
- **A2 (no-cross-fire, angle):** `Δθ_overlap < ` spacing to the nearest station. The tightest pair is
  **SG3b→BS3 = 2.95°**. This is the **binding** constraint (462 of 462 assertion failures are A2).

**The radius criticism, explicitly:** at the current **r = 387 mm / 12 mm ball / 3000 rpm** the
overlap is **2.07°**, leaving an A2 cross-fire margin of **0.88°** (positive, comfortable) and an A1
time margin of **111 µs** (vast). **The radius is *not* critical for fitting the resonant transfer** —
it is the lever that sets cross-fire: **larger r ⇒ narrower overlap ⇒ more cross-fire margin**
(opposite to the brief's `RADIUS-CRITICAL`-too-narrow worry). The danger is **inner** placement: at
**r = 250 mm the 12 mm ball already cross-fires** (overlap 3.21° > 2.95°, margin **−0.26°**).

## 3. The radius trade (brief §4) `[SOLVER]`

| r (mm) | overlap @12 mm | A2 margin | max ball (no cross-fire) | t_overlap @3000 | max rpm (A1) |
|---|---|---|---|---|---|
| 250 | 3.21° | **−0.26°** (cross-fire) | 10.5 mm | 184 µs | >30 000 |
| 300 | 2.67° | +0.28° | 13.0 mm | 153 µs | >30 000 |
| 350 | 2.29° | +0.66° | 16.0 mm | 131 µs | >30 000 |
| **387** | **2.07°** | **+0.88°** | **17.5 mm** | 115 µs | >30 000 |
| 450 | 1.78° | +1.17° | 21.0 mm | 99 µs | >30 000 |
| 491 | 1.63° | +1.32° | 23.0 mm | 90 µs | >30 000 |

The curve is monotone: **push the BS3/SG3b balls outward** to widen the cross-fire margin and allow a
bigger ball; the time window stays comfortable throughout. A1 (the resonant fit) never sets the limit.

## 4. Design hints (brief §5) `[SOLVER]`

- **Viable region:** 798/1260 combinations pass A1–A4. Within it, **η_real is essentially flat
  (~0.70)** — the geometry doesn't move the efficiency; it moves the *margin*. So **best-η and
  best-margin coincide at large r / small ball** (best η 0.707 @ r=491/4 mm; best cross-fire margin
  4.25° same corner), but η is not the discriminator — **margin is**.
- **Are the DXF stations near-optimal?** Yes on η (no perturbation beats them) and viable on margin.
  No station shift is *needed*; the only lever worth pulling is the **radius/ball** against the 3° pair.
- **Concrete hint:** at the established 12 mm ball, keep **r ≥ ~300 mm** (and prefer the outer band,
  r ~ 387–491, for a 0.9–1.3° cross-fire margin). If a **larger ball** is wanted (lower field stress,
  longer life), r = 491 mm admits up to **~23 mm**; r = 250 mm caps it at **~10.5 mm** (and 12 mm
  already cross-fires there).
- **Cross-fire boundary (a design wall):** **r ≤ 250 mm with a ≥ 11 mm ball cross-fires SG3b↔BS3** at
  the DXF spacing — the gaps cannot be placed in the inner band at the established ball size. The relief
  is larger r, a smaller ball, or widening the SG3b–BS3 spacing (a station move, which the sweep shows
  is otherwise unnecessary).

## 5. The radius verdict

**COMFORTABLE in time, cross-fire-bound in angle.** The current radius (≈387 mm) is comfortable: the
resonant transfer fits with ~111 µs to spare, and the SG3b–BS3 cross-fire margin is +0.88°. The
recommended envelope is **r ∈ [≈350, 491] mm with d_ball ≤ the per-radius cap above** (12 mm fits from
r ≥ 300 mm). The design is **not window-limited** — the earlier idealized-clock η ≈ 0.70 survives the
real DXF timing.

## Deliverables

`sim/firing_geometry.py` (DXF-station bind + overlap-window model + the lookup sweep) ·
`firing_lookup.csv` (every combination, A1–A5) · `firing_radius_trade.csv` (radius vs max-ball /
overlap / max-rpm) · `firing_geometry.png` (cross-fire margin vs ball/radius; overlap-time ≫ t½) ·
this findings doc. Frozen solvers untouched. **Not merged** — informs the gap-placement spec TMD
signs off.

### [IR] parameters (TMD to confirm)

`g_lat = 1 mm` (lateral striking clearance/side), `t_strike = 0.1 µs`, `t_conduction = 2 µs`. The
cross-fire margin is the sensitive one: at the conservative `2·g_lat = g_strike ≈ 5.5 mm` the r=387/12
mm margin tightens from 0.88° toward ~0.1° — so **the SG3b–BS3 pair is the watch-item** and the outer
band is the safe recommendation. A1 (the resonant fit) is insensitive to all of these (111 µs margin).
