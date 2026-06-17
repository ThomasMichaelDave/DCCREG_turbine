# Resonator Battery — Hardware Design Considerations

**Status:** [IR] Design intent recorded; not yet a producer. Source: TMD, 2026-06-12 (reading
confirmed), captured from the resonator-accumulation brief (Phase 4) Appendix A. This document is the
hardware layer for the resonator-as-electrostatic-accumulator ("Joule battery") route; it does **not**
change any solver. Mainstream EE + Maxwell-stress energy density only — no DCCREG theory.

## 0. Firewall note (binding)

The rationale *"retain the highest-frequency artifacts to modulate deeper through the Coulomb ledger /
more Fourier terms"* is **parked [RH], explicitly NOT load-bearing** for any design decision in this
repo (TMD concurrence 2026-06-12). The only in-scope high-frequency question is the **HF-damping spec**
(brief §1.4): the minimum damping of the loss spectrum that preserves gap-trigger integrity (zero
backstop false positives, ordering margin) — standard EE, falsifiable, and it bounds HF retention from
*above*. Nothing below depends on the parked rationale, and the capillary winding (A.6) is adopted on
ordinary [OC] grounds (AC-resistance parity, mass/henry, stiffness).

## 1. Waterfall geometry [OC relations; IR layout]

For a chosen rotor radius, component sizing inherits by waterfall. The six steel motor quadricones sit
**angularly between the C_R active sectors, within the electrode sandwich**, with the central battery
quadricone on-axis. The quadricone axial height therefore sets the C_R electrode separation `d`, and

    C_R = ε₀·ε_r·A / d        (ε_r,mica ≈ 5.4)

so every millimetre of quadricone height removed is **capacitance gained, rotor mass removed, and
spin-up inertia reduced** — three objectives on one parameter. Floor on `d`: dielectric strength at the
clamp voltage (20 kV at 1 kV/mm air → 20 mm in air; a solid/mica facing moves the floor substantially
lower) plus the structural section of §3.

## 2. Quadricone hollowing [IR intent; OC constraints]

Optimize for maximum torque at minimum weight via flux-aware voids (spherical/elliptical) that preserve
the flux spine and saturation cross-section. Constraints: the SR torque ceiling = flux-path
cross-section; spin-stress concentration at void equators (factor ≈ 2 under centrifugal load) → a
**Block M FEA gate before any metal is cut**. The six satellite quadricones are hollowed for
weight/torque only — they are **not** resonant-chamber electrodes.

## 3. Electrodes as structure [OC]

Stainless C_R electrode plates may carry rotor structural load (thicker sections permitted).
Constraint: stainless ≈ **40× copper resistivity** → bare stainless plates are ESR in the battery
capacitor and a Q_loaded sink. Rule: **structure in stainless, current in copper** — the active faces
copper-clad/plated. (This is the conductive-structure loss that degrades Q_unloaded → Q_loaded in the
accumulation model.)

## 4. Defined potentials [OC]

Every conductive mass in or adjacent to the C_R field region receives a **defined potential** (bond or
guard) *on the drawing*. Floating steel between HV electrodes is a charge island and a partial-discharge
site.

## 5. Lamination vs solid [OC]

Solid steel in the SR flux path costs eddy/hysteresis loss (motor drag) and, where adjacent to the ring,
Q_loaded. Hollowing and lamination answer different problems; both are evaluated in Block M/D.

## 6. Capillary tube winding — adopted on [OC] grounds only

AC-resistance parity with a solid conductor at battery-grade f₀ (`δ_Cu ≈ 1.5 mm at 2 kHz`, ≥ tube wall,
so current rides the outer surface and tube ≈ solid rod), mass per henry, and the mechanical stiffness
of the wound tube. **Coolant bore: deferred** (out of scope this gate — a future two-in-one feature once
the basis runs). The HF-retention rationale for the bore is parked per §0; the in-scope HF claim is the
§1.4 damping spec, which if anything bounds HF retention from above for gap-trigger integrity.
`[OC/IR/RH as marked]`

## 7. Consequence for the accumulation gate

The waterfall (§1) makes C_R a tunable design variable (via `d`); §3/§5 set the realizable Q_loaded
band; the battery-grade incoherent/coherent routes (resonator-accum findings) need a **kHz-class f₀**
(large L·C) — the capillary loop-stack (§6) is the winding that delivers that L at acceptable mass and
AC resistance. The DC route (the recommended primary) uses C_R directly as the reservoir and L_RES as
the transfer element; its self-discharge is set by mica volume resistivity (§3 materials), not tank Q.
