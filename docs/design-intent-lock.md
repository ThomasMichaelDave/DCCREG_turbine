# Design-intent lock — prototype geometry iteration

| Field | Value |
|---|---|
| Path | `docs/design-intent-lock.md` |
| Status | **r0.1 — locked design intent for the current geometry iteration** |
| Scope | varcap-machine only. Topology + regime decisions. **Structural/material sizing explicitly deferred.** Firewall: no DCCREG content. |
| Tier tags | `[OC]` operational core / physics · `[IR]` interpretive design choice · `[OPEN]` decision still required · `[DEFER]` parked to structural-sizing iteration |
| Source | Locked across the design conversation preceding this lock. This file is the single written record; before it, these decisions lived only in chat. |

## Revision history

| Rev | Date | Change |
|---|---|---|
| r0.1 | 2026-06-14 | First lock: geometry-iteration scope + four checks; HV/pulse regime (spark 10 ns, sub-20 kV, local-loop mandate); hybrid spark/glow electrode-form rules + literature basis; two-tier clamp architecture; 5–6 inter-shaft void as native glow clamp via static-sealed rotating vacuum chamber (no rotating seal); deferred-to-sizing list; layer-scheme additions. |

---

## 1. This iteration's scope and the four checks

**Scope `[IR]`:** architect the electro-active parts — their dimensional positions and
relationships — as **topological/structural projections only**. Engineering the structural sizing
(wall thickness, balance, fastening, material stress) is a **later** iteration. The geometry produced
here must answer four checks and nothing more:

1. **Can we pump?** `[OC]` — extract geometry-derived Cmin/Cmax for **all four** varicaps (C1, C2,
   and the cross-path Cx3/Cx4) from node-layer overlaps, feed the **6-node** `shuttle_core` (not the
   4-node `solveDoubler4`), confirm z > 1 at the real caps. This is the headline check; the
   campaign's z = 1.189 used **placeholder** Cx = 1200/60 pF, so if buildable pickup geometry can't
   produce a comparable Cx swing, z moves — a real finding.
2. **Counter-rotation `[OPEN]`** — shafts A/B are **confirmed co-rotating locked** through the
   quadricone hubs (see §7). The original check asked "does the topology allow mechanical
   counter-rotation"; with co-rotation locked, **clarify what counter-rotation refers to** (rotor↔stator
   relative motion, which the topology obviously allows? a counter-rotating outer member? a
   reconsideration?). Do not silently resolve — flag for TMD.
3. **Does everything connect during operation?** `[OC]` — kinematic sweep: do the intended electrodes
   overlap at the right θ, in the right order (return leads, cross-couple follows; load before fire;
   bar arc-width < 30° with guard band to prevent cross-bridging)?
4. **Are the galvanic separations OK?** `[IR]/[DEFER]` — geometry confirms separations are
   **topologically present and correctly placed** (islands 7/8 isolated except through their gaps;
   doubler-node ↔ rotor/island firewall; no unintended adjacency). It does **not** confirm they
   **hold voltage** — creepage/clearance vs the 20 kV rail is `[DEFER]` to sizing. Report as
   "separations located, voltage-holding deferred."

**Loop:** node overlaps → geometry-derived caps → 6-node `shuttle_core` (check 1) → kinematic sweep
(checks 2,3) → adjacency/isolation audit (check 4, topological half). Each gets a named pass/fail.

## 2. HV / pulse regime `[OC]`

- **Power pulse = spark/arc, ~10 ns, sub-20 kV.** At 10 ns the power pulse is a fully-collapsed spark
  channel; glow cannot form or deliver power on that timescale. Glow is **pre-conduction /
  threshold-gating only** for the power gaps, never the power regime.
- **Energy / peak power.** Pulse energy is fixed upstream by E = ½C V² (local store, not the big
  plates). For ~100–1000 pF at ~20 kV ⇒ ~20–200 mJ ⇒ **~2–20 MW peak** in the 10 ns spike.
  Shortening τ raises *peak power* for fixed energy; it does **not** create energy.
- **10 ns mandates a LOCAL low-inductance discharge.** A machine-scale loop (R≈0.25 m) is ~1.25 µH;
  rung against 1 nF that gives a ~50 ns quarter-period — the full machine loop **cannot** produce a
  10 ns edge. To hit 10 ns: local store ~100–200 pF **and** loop inductance ≤ ~200–400 nH, i.e.
  energy stored **at the gap** with a tight, small-area return. The **Cx pickup collapse is inherently
  a local store at the fire gap** — the architecture is on-side — but **the tight return loop at each
  fire gap becomes a first-order drafting requirement, not an afterthought.** Long thin leads
  inductance-limit back to tens of ns regardless of gap speed.
- **Gap hold-off vs 20 kV `[OPEN]`.** 20 kV across the current 0.5 mm gap is ~40 kV/mm, far above air
  breakdown — that gap fires well below 20 kV in air. Resolve while drafting: the gap that *holds*
  20 kV must be sized/pressurised/staged so it holds off until the intended fire, then breaks. Decide
  gap size, medium, or staged-voltage — the electrode spacing drawn must be Paschen-consistent.

## 3. Hybrid spark/glow electrode-form rules `[OC]` physics, `[IR]` split

The regime is set by **field enhancement at the electrode** — the master switch:

- **Spark gaps (SG1, SG2, SG3a/b, SG4a/b)** — power + commutation. **High field enhancement:**
  ball/hemispherical, small radius, tungsten or W-Cu for high-rep-rate. Drives fast full breakdown
  and the sharp 10 ns edge.
- **Glow backstops (BS3, BS4)** — the bleeder. **Low field enhancement:** large, smooth surfaces with
  room for the glow to **spread at constant voltage** (normal-glow self-regulation = the soft bleeder
  behaviour). Distinct geometry from the spark balls; if drafted as balls, no trim recovers clean
  glow.
- **Glow needs active current/power limiting `[OC]`** — a series element or pressure regulation,
  **not geometry alone**. Geometry only *permits* glow; holding it in-window is operating-point trim
  (`[DEFER]`).
- **Nanosecond glow window is narrow and multi-parameter** (gap, tip radius, voltage, pulse width,
  pressure) — `[DEFER]` bench trim, not a topology quantity.

**Electrode-form literature basis** (for the drafting record):

- A. Anders, "Glows, arcs, ohmic discharges: an electrode-centered review…," *Appl. Phys. Rev.*
  **11**, 031310 (2024) — the electrode-centered map; field enhancement at micro-protrusions/cracks
  governs the emission mode.
- Y.P. Raizer, *Gas Discharge Physics* (Springer, 1991) — the canonical Townsend→glow→abnormal→arc
  I–V characteristic (Fig. 8.4). Primary reference. Also Fridman, *Plasma Chemistry* (CUP 2008);
  Smirnov, *Physics of Ionized Gases* (Wiley 2001).
- Nanosecond-pulsed glow domain (the 10–30 ns regime, air): US10283327 / US9378933 — glow "domain of
  existence" trapezoids in V–gap, glow→spark boundary V = E_bd·d + V_CF with E_bd ≈ 30 kV/cm (air),
  cathode-fall V_CF ≈ 2 kV, plus minimum-gap and minimum-voltage bounds.
- Smooth/distributed-surface and current-limiting design rules: US4574380 (protrusion 4–10 mm
  disperses glow to side walls), US8129904 (series R/C limits current to hold glow, prevent
  constriction), US5068002 (pressure regulation to stay in glow band).
- **Consensus that transfers** `[OC]`: form sets regime via field enhancement; glow self-regulates by
  spreading over area; stable glow needs active current/pressure limiting. **Consensus that does NOT
  transfer** `[OPEN/DEFER]`: every cited source is a *static* gap; **the motion-quenched rotary glow
  case is unmapped** — the forced-air + reduced-pressure regime behaviour is bench work.

## 4. Resonator voltage limiting = two-tier shunt regulator `[IR]`

Not a passive "clamp diode." A live resonator's voltage is energy mid-conversion; a clamp **removes
energy from the oscillation**, so it is a *load* with a *sink*, in two tiers:

- **Soft glow governor** — everyday amplitude shaving, low erosion, little energy per event; holds the
  tank near a target. **Regulator.**
- **Hard spark crowbar** — last-resort ceiling; fires only on runaway toward a damaging voltage; large
  energy dump. **Fires ~never in normal operation** (every-cycle firing would spoil Q and change pump
  dynamics). **Circuit breaker, not regulator.**

The two stack in severity: soft governor everyday, hard crowbar behind it.

## 5. What already exists vs what is aspirational `[OC]`

- **The soft-glow-clamp ARCHETYPE is proven and in-repo:** the backstop (BS3/BS4) is a glow gap ("a
  GAP, not a resistor") that catches trapped island charge above a lower threshold; it has a
  **defined dump path** (`_dump_island_into_sink`) and the code already models the soft→hard failure
  (`I > pIconstrict` ⇒ glow→arc constriction). Validated **BACKSTOP-CLEAN** (spark-derate).
- **But it clamps the ISLANDS (7/8), not the resonator (5/6)** — drain-back, not tank amplitude.
- **Therefore:** resonator clamping is an **extension of proven in-house tech**, not new physics —
  **but it is not in the circuit yet**, and the **hard-crowbar tier does not exist anywhere**. Do not
  let the backstop stand in for an unbuilt resonator clamp.

## 6. The hard ceiling goes across nodes 5–6 — consequences `[IR]/[OC]`

A hard tank clamp must sit across the resonator differential, i.e. **nodes 5–6** (shaft A / shaft B
bodies). Placing it there forces three things:

1. **Symmetric, bidirectional gap** `[OC]` — 5–6 is a ringing differential pair; the clamp sees
   polarity reversal each half-ring and must hold off **both** directions until threshold. Not the
   one-way commutation geometry.
2. **Full-tank-dump energy sink** `[DEFER]` — a hard fire dumps ½C_R V² at ~20 kV through near-zero
   impedance: the MW-peak regime, far larger than the island dump. Sink sizing + erosion landing on
   structural parts is deferred sizing work. The backstop's `_dump_island_into_sink` is the
   *template*, a size class smaller.
3. **Implies a soft governor elsewhere** `[IR]` — a *hard-only* 5–6 clamp either never fires (useless)
   or every cycle (Q-killer). The soft governor is best placed **upstream** (island / pickup, glow,
   every cycle) so the tank never climbs to the crowbar threshold — regulate before the peak, not at
   it.

## 7. The 5–6 inter-shaft void as the native clamp `[IR]` — the locked resolution

Rather than bolt on a clamp, **the central void between shaft bodies 5 and 6 IS a gap across the
resonator differential.** Locked design:

- **Native clamp, no added component.** The void is central, **large-surface, low-field-enhancement**
  → naturally **glow-favouring**. The machine **self-sorts**: outboard/sharp = spark, inboard/smooth =
  glow.
- **Glow enabled by setting pd via a sealable vacuum/fill nipple** `[OC]`. At atmospheric large-gap pd
  the void would *spark*, not glow; evacuating (or controlled-fill) moves pd into the glow band. So
  glow-in-the-void is **a pumping spec, not a physics gamble.**
- **NO ROTATING SEAL — the key enabler** `[OC]`. Shafts A/B co-rotate **locked** through the
  quadricone hubs, so the void walls move **together**: the chamber rotates **as a rigid body** and
  the seal is a **static** seal between parts with no relative motion. No dynamic/rotating vacuum seal
  exists. This is what makes a glow clamp practical on a supercritical rotor — the co-rotation-locked
  architecture (chosen for the shaft train) pays this dividend.
- **Nipple = re-sealable valve** `[IR]` — for re-pumping to re-establish the glow operating point as
  internal surfaces outgas over time.

## 8. Open decisions and deferred items

**`[OPEN]` (need TMD before/while drafting):**

- Counter-rotation meaning (§1 check 2).
- Gap hold-off geometry vs 20 kV — size / medium / staged voltage (§2).
- **Void fallback behaviour:** if glow won't establish (pd too high, pump-down insufficient), the void
  falls back to a **hard spark across the inner void** — an arc between shaft bodies on the axis.
  Decide: is hard-spark fallback **acceptable** (it's still a clamp, just hard) or **must-never-spark**
  (much harder constraint on the void)? This decides whether the void is "soft clamp, hard-clamp
  fallback" or "soft clamp that must stay soft."
- Soft-governor location: in the void (5–6 directly) vs upstream (island/pickup). §6.3 favours
  upstream; confirm.

**`[DEFER]` (structural-sizing iteration):**

- Vacuum-chamber wall stress under combined pressure-differential + centrifugal load (evacuating the
  void adds an inward atmospheric load on top of rotation).
- Outgassing / internal-surface prep for glow operating-point stability.
- Full-tank-dump energy-sink sizing (§6.2) and erosion management.
- Glow operating-point trim (the narrow nanosecond window, §3).
- Creepage/clearance voltage-holding of all galvanic separations vs 20 kV (§1 check 4).

## 9. Layer-scheme additions (apply to the node-analysis template → r0.2)

The clamp/void decisions add parts the r0.1 layer scheme does not represent. Add:

- `CLAMP-VOID-GLOW-5-6` — the inter-shaft void glow-clamp electrode surfaces (soft governor), across
  nodes 5–6, smooth/low-enhancement.
- `CLAMP-CROWBAR-HARD-5-6` — hard spark crowbar electrodes across 5–6 (if distinct from the void
  fallback), symmetric/bidirectional.
- `MECH-VACUUM-CHAMBER` — the sealed inter-shaft chamber envelope (static seal line).
- `MECH-VACUUM-NIPPLE` — the re-sealable evacuation/fill valve.
- (confirm) whether the soft governor also wants island/pickup-side clamp electrodes if §6.3 upstream
  placement is chosen → a `CLAMP-SOFT-UPSTREAM` layer.

Bump `varcap-nodeanalysis-layers-r0.x.md` and regenerate the DXF template accordingly, keeping the
construction/reference and node-map conventions intact.

> **Application status (r0.1):** the layer-scheme additions above are **specified but not yet
> applied** — the base `varcap-nodeanalysis-layers-r0.1.md` and its DXF-template generator are **not
> present in this repository** (no copy in the working tree or git history; no DXF tooling). The r0.2
> bump + DXF regeneration are therefore **pending the base artifacts** and tracked as an open action
> for TMD (see CHANGELOG). The new-layer names are frozen here so the bump is mechanical once the base
> file is located.

## 10. One-line summary

Spark power pulse (~10 ns, sub-20 kV, MW-peak, local low-inductance loop mandatory) with a hybrid glow
backstop, plus a two-tier resonator clamp whose **hard ceiling lives across nodes 5–6 as the central
inter-shaft void run in glow regime** — made buildable by a **static-sealed, rigid-body rotating
vacuum chamber with no rotating seal**, evacuated via a re-sealable nipple. Geometry this iteration is
topological/structural projection only; everything in §8 `[DEFER]` waits on the structural-sizing
iteration.
