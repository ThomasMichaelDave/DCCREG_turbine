# Design note — SG3b/SG4b fire-gap mount: adjustable + RPM-governed `[IR]`

**Status:** design intent for the freeze doc §5, pending mechanical consolidation/feasibility by TMD.
Mainstream EE/mechanical only — no DCCREG. Tier **`[IR]`** throughout (design choices, not solver-derived);
the few quantitative claims that lean on physics are marked `[OC]`.

---

## 0. Why this note exists

S3 found the fire-gap spacing is the soft spot of the v0.10 design: the drafted 5.5 mm gap clears 15 kV but
only by ~0.5 kV cold, and the strike model is linear `3 kV/mm` exactly where (s/D ≈ 0.5) real sphere gaps
start to roll off. Conclusion from that review: **the fire-gap spacing must become a bench-tuned, adjustable
electrode, not a frozen draft dimension.** This note specifies how to make it adjustable *and* turns the
unavoidable centrifugal load into a passive RPM governor — without degrading reach or quench.

Two facts frame everything below:

1. **The fire gap is the machine's voltage relief valve.** The rotor charges until SG3b/SG4b strikes at
   `V_strike`, then dumps the bucket. So `V_strike` *is* the operating-voltage ceiling — which makes the fire
   gap the natural throttle point.
2. **There is no ground-fixed electrode at this gap.** Both sides sit on counter-rotating bodies (the "rotor"
   and the "stator" each turn at half the relative/commutation rate, opposite signs). Neither is
   centrifugally quiet. The design axis is therefore **rigid mount vs compliant mount**, not rotor vs stator.

---

## 1. Architecture: two functions, two electrodes

The gap gets a fixed reference on one electrode and a governed element on the other:

| Electrode | Role | Mount | Behaviour vs RPM |
|---|---|---|---|
| **Outboard** | set-point (bench datum) | **rigid** stiff arm | stays put (body reacts the load) — RPM-stable |
| **Inboard** | centrifugal governor | **compliant** flexure | walks outward → gap **closes** with RPM |

Centrifugal force drives the inboard electrode *toward* the outboard one, so the gap shrinks as the body
speeds up → `V_strike` falls → the voltage ceiling falls → pumping throttles. Spring *both* sides and they
walk outward together and the gap barely changes; the governing comes from making **exactly one** side
compliant. Orient the gap **radially** (inboard electrode at smaller radius) so centrifugal force acts
straight down the gap normal — no cam or lever.

## 2. Set-point electrode (outboard, rigid) `[IR]`

- W-Cu sphere (12 mm) **wired** to its node, not formed on the capacitor surface. Decoupling the spark
  electrode from the cap plate keeps the cap field uniform (no protrusion → no corona on the *cap*); cost is
  ~1 pF stray self-C added to the node — negligible.
- Mounted on a **stiff garolite arm**. Rigid to its body, so the centrifugal load is reacted by the arm and
  the electrode does **not** move relative to its body — the gap reference is RPM-stable even though the body
  rotates. (Stiffness, not "no load", is what buys stability — see §4 for the load.)
- **Macor (or alumina) collar** over the arc-facing few cm; bare garolite chars and surface-tracks under arc
  UV/heat and would become a creepage path that shunts the gap. Grade the **electrode/arm/wire triple
  junction** so it doesn't corona at the mount.
- **Wire short, loop tight** (coax or close pair, minimal enclosed area) — see the quench constraint in §5.
- **Adjust along the gap normal**, perpendicular to the bar's sweep, so setting the spacing does **not** move
  the firing angle (timing). Threaded W-Cu in the holder + jam-nut, bench-set with feeler gauges and locked.

## 3. Governor electrode (inboard, compliant) `[IR]`

- W-Cu sphere on a **flexure** (preferred over a sliding spring: no stiction, repeatable return, easy to
  fatigue-rate). The flexure preload sets the **knee RPM**; the flexure rate sets the **slope**.
- Set the knee **above the intended operating speed** so the governor is idle in normal running and only
  engages on overspeed.
- The flexure deflects under its body's own centrifugal force → the electrode tracks outward → the gap
  closes. Because the governed quantity is the body's **ground** RPM, the governor senses exactly the speed
  that mechanically stresses that body — it protects against the real overspeed-failure mode.

## 4. Force sizing — corrected for the contra-rotating frame `[OC]`

Centrifugal force is set by **ground RPM = relative/2**, not the relative (commutation) rate. This is a
factor-of-4 correction (force ∝ Ω²): at a 3000 rpm *relative* design point each body turns 1500 rpm ground.

- `F_c = m·ω_ground²·r`. For a 12 mm W-Cu sphere (m ≈ 13 g, ~14.5 g/cm³) at r ≈ 350 mm, 1500 rpm ground
  (ω ≈ 157 rad/s): **F_c ≈ 11–12 kgf** (≈ 112 N). *(Using the relative rate as if it were ground speed would
  have given ~46 kgf — wrong by 4×.)*
- Scales as Ω_ground². Illustrative flexure: preload ≈ 112 N to seat the knee near the operating speed; rate
  ≈ 80–90 N/mm gives ~1 mm of travel over a ~500 rpm-ground overspeed band. Pin these to the actual
  operating/overspeed speeds.
- **The throttle is strong above the knee:** since `F_c ∝ Ω²` and delivered power ∝ `V_strike²·PRF`, power
  falls hard once past the knee rather than holding flat. Ideal for a protective limiter; a flat
  constant-power region would need a progressive-rate flexure and isn't required for the safety role.

## 5. Constraints & watch-items

- **Fail-safe direction** `[IR]` — design so a fatigued/broken flexure sends the gap **wide** (that branch
  stops firing — safe, just asymmetric), never narrow (stuck-closed / continuous low-V firing = runaway).
  The flexure is a fatigue part (every spin cycle + fire impulses); assume eventual failure and make it
  benign.
- **Per-body spring matching** `[IR]` — all governor flexures on a given body must be matched so the
  electrodes move as a symmetric iris and the CG stays centred; a soft one walks out further at speed and
  builds a speed-dependent imbalance (the thing the auto-balancer is fighting). This now applies to **two**
  counter-rotating bodies independently — matching is a rotordynamic spec, not just electrical.
- **Fire-loop inductance vs quench** `[OC]` — reach (η) is set by the Cx/C_R ratio and is unaffected by
  wiring, but loop inductance sustains arc current through its zero-crossings and fights the blow-out. The
  quench margin is already only ~1.67× at the pessimistic recovery corner, so keep the wired loop short and
  tight and design it for a clean current-zero, not merely a fast dump.
- **Garolite back from the arc** `[IR]` — Macor/alumina collar near the tip; garolite is structural-run only.
- **Adjust normal-to-sweep** `[IR]` — spacing and firing angle stay independent only if the adjustment axis
  is the gap normal.
- **Ground-vs-relative RPM labeling** `[IR]` — the spring feels **ground** RPM; the firing rate/PRF is the
  **relative** rate (2×). Label every governor number explicitly; this factor of 2 silently halves or doubles
  designs.
- **Jitter (verify, don't assume)** `[OC]` — the electrode-on-flexure is a ~1 kHz mechanical resonator and
  each fire is a broadband impulse; confirm the fire recoil doesn't ring it between shots and jitter the next
  gap. Likely small — measure it.
- **Quench is preserved/improved** `[OC]` — motion-quench runs on the **relative** sweep (2Ω·r); the
  contra-rotation doubles the separation speed vs a fixed stator, which helps the blow-out. Unaffected by the
  mount change.

## 6. Effect on the freeze doc

- **Reclassify** fire-gap spacing (§5) from a frozen number to an **adjustable, bench-tuned `[IR]`** item
  (set vs IEC 60052, locked).
- **Add** the governor as an `[IR]` mechanical sub-assembly (inboard compliant flexure electrode) with the
  fail-safe / per-body-matching / flexure constraints above.
- **Unchanged:** reach (η, floor), pump z, the cap set, quench verdict. BS3/BS4 DXF markers remain the open
  geometry TODO.

---

## CHANGELOG
- v0.1 — initial note. Adjustable wired set-point (outboard, rigid) + centrifugal flexure governor (inboard,
  compliant). Corrected for the contra-rotating frame: no centrifugally-quiet side; force from ground RPM =
  relative/2 (≈11–12 kgf at design point, 4× lower than a relative-rate estimate); rigid-vs-compliant is the
  design axis. Constraints: fail-safe-wide, per-body matching, flexure-over-spring, tight fire loop for
  quench, Macor collar, normal-to-sweep adjust, ground/relative RPM labeling, jitter check.
