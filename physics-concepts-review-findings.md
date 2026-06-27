# Findings — physics-concepts review → **REPO MAINSTREAM · ION-SIPHON HAS ONE LOAD-BEARING CONSERVATION GAP**

**Branch** `claude/physics-concepts-review-wp81n4`.
**Scope:** scrutinise the load-bearing physics against mainstream electromagnetism / thermodynamics.
Two bodies reviewed: (1) the existing repo (Bennet doubler + variable-capacitor front end + energy-balance
findings); (2) the uploaded `ion_siphon_package.zip` (electret-capillary ion siphon).
**Tier tags** as in `CONVENTIONS.md`: **[OC]** standard physics · **[IR]** modelling choice · **[RH]** heuristic.

**Verdict line:** the repo's electrostatic-machine physics is **mainstream and internally honest**; the
ion-siphon derivation is mostly sound **but its "continuous mode" rests on a non-depleting electret driving a
steady closed-loop current — which a conservative field cannot do.** That single move, taken literally, is an
over-unity element. Everything else in the ion-siphon doc is either correct or already flagged as open.

---

## 1. The existing repo — passes mainstream scrutiny

### 1.1 Bennet doubler / variable capacitor [OC]
The host (`index.html`, `solveDoubler4`) is a symmetric Bennet charge doubler driven by a rotary variable
capacitor. This is textbook electrostatics: the voltage gain is paid for by **mechanical work** done moving
the plates apart against electrostatic attraction at (near-)constant charge (`W = ½Q²·Δ(1/C)`). No free
energy is claimed. The Block C-I geometry→capacitance front end (parallel-plate `C = ε₀ε_r A/g`, triangular
overlap `f_ov(θ)`, Smith–Weintraub moist-air `ε_r`, Buck saturation pressure) is standard and correctly
cited. ✔

### 1.2 Energy-balance findings — honest, and a good positive control [OC]
`energy-balance-findings.md` is the right kind of work:
- The per-cycle identity `W_mech = ΔE_stored + E_tax` closes to **1.4×10⁻¹⁶** (machine precision) — i.e. the
  charge-law `z` campaign is confirmed by an independent **energy** conservation law.
- It surfaces the **equalization tax** (61.4 % of shaft work): the two-capacitor paradox `½·C₁C₂/(C₁+C₂)·ΔV²`
  dissipated at every diode merge **even with ideal diodes**. Correctly identified, correctly quantified.
- It explicitly refuses to call `E_tank/W_mech > 1` an efficiency ("a deliberate tell, surfaced not
  smoothed"). That is exactly the discipline a conservation review wants to see.

**Conclusion for the repo:** no over-unity claim. The machine is a shaft-driven electrostatic generator whose
output is bounded by, and accounted against, the mechanical input. Mainstream. ✔

---

## 2. The ion-siphon package — detailed scrutiny

### 2.1 What is correct [OC]
- **Kinetic (inertial) inductance `L = mℓ/(ne²A)`.** Genuine and correctly derived from carrier momentum
  (½·nmAℓ·v² ≡ ½LI², I = neAv). This is real textbook physics (kinetic inductance of a charged carrier
  column). ✔
- **Dose mode is exactly right.** With no leak, the collector charges until its back-EMF cancels the drive
  and the device stops after delivering `Q_max = C_k V_e`. This is just an electret discharging its stored
  field energy into a capacitor — completely mainstream, energy-bounded, and honestly stated. ✔
- **Steady-state algebra is internally consistent.** `I_ss = V_e/(R+R_leak)`, `V_sc,ss = V_e R_leak/(R+R_leak)`,
  and the characteristic equation `L C_k s² + (R C_k + L/R_leak)s + (1 + R/R_leak) = 0` are algebraically
  correct *for the circuit as drawn*. The problem is not the algebra; it is what `V_e` is allowed to be.
- **Honesty notes are present and good:** §3.3 (a solid film can't be rotated against in a rotary varcap),
  §6.2 + the MIGRATION "OPEN" block (axial poling vs central-null coupling is *stated, not solved*). These
  are correctly tiered as unresolved. ✔

### 2.2 LOAD-BEARING PROBLEM — a static electret cannot sustain a steady closed-loop current

The schematic (`ion_siphon.svg`) and §4 make the topology explicit:

```
atmosphere (ref at ∞) ── C_atm ──[ electret V_e + L + R ]── collector ── C_earth ── earth (common return)
                                                                  └────── R_leak ──────┘
```

**Earth is the common return, so the loop is closed**, and the electret `V_e` is the *only* source in it.

An electret is a frozen **electrostatic** polarization. Its field is conservative:
$$\oint \mathbf{E}\cdot d\boldsymbol{\ell} = 0 \quad\text{for any closed loop. [OC]}$$
The net EMF a static electret can contribute around a closed circuit is therefore **exactly zero**. It is not
a battery: a battery has a non-electrostatic charge-separating mechanism that does work `qV` on each carrier
every lap, which is what lets a battery sustain `I²R` dissipation indefinitely. An electret has no such
mechanism. So:

> **Continuous mode (steady `I_ss` flowing "indefinitely, limited only by the electret lifetime") dissipates
> `I_ss²(R+R_leak)` forever from a source that, by construction, "sources essentially no net charge" and "does
> not sag under load." A non-depleting source delivering sustained power is an over-unity element. [OC]**

The doc reaches this position by a specific substitution. In **Stage I** it correctly notes the passive head
`(V_s − V_k)` *bleeds down* as charge transfers — reservoirs deplete, exactly as a real open siphon drains
its upper reservoir. In **Stage II** it *replaces* that depleting head with an electret `V_e` "that no longer
decreases with delivered charge." That replacement is the unsupported step: it converts a correctly-depleting
drive into a perpetual one and never writes the continuous-mode **energy** balance to check it.

**The correct physics (two legitimate readings, neither matching the doc's framing):**
1. **The electret is the energy store ⇒ it depletes.** The energy for sustained `I²R` comes from the
   electret's stored field/polarization energy, which is finite. Then `V_e` is *not* constant, `I_ss` decays,
   and the device is just a slow version of dose mode. "Continuous, limited only by lifetime" is then
   misleading: the lifetime *is* the energy budget, not a separate material-aging footnote. This collapses
   "continuous mode" into "dose mode with a leak that drains the store faster."
2. **The atmosphere–earth potential difference is the real drive ⇒ *it* depletes (or is externally
   replenished).** The global atmospheric electric circuit (~100 V/m fair-weather field, maintained by
   thunderstorms — i.e. ultimately solar) is a genuine, mainstream energy source. A device tapping it is an
   atmospheric-electricity harvester, not perpetual motion — but then the sustained energy comes from `C_atm`/
   `C_earth` reservoirs bleeding down (**Stage I**, which the doc discarded), **not** from the electret. The
   electret would merely bias the geometry, not power the flow.

Either way, the load-bearing claim — *electret as a non-depleting drive sustaining steady current* — is the
one thing that cannot stand. The doc's own dose-mode result (`Q_max = C_k V_e`) and its depolarization caveat
already contain the correct, conservation-respecting physics; the **continuous-mode framing contradicts
them.** [OC]

Supporting real-world check: this is exactly why **electret microphones** work — the electret holds a bias
while drawing **negligible steady current** into a high-impedance gate. Draw sustained current and the
electret simply discharges. That commercial device is the empirical statement of the limit above.

### 2.3 SECONDARY PROBLEM — "uniformly polarized shell ≡ uniform surface charge" is not an identity

§3.2 claims: *"A uniformly polarized spherical shell — equivalently, a uniform surface charge on a sphere —
produces zero electric field everywhere in its interior."* These are **not** equivalent. [OC]
- A **uniform monopole surface charge** `σ = const` on a sphere → zero interior field (shell theorem). ✔
- A **uniform polarization** `P` produces bound surface charge `σ_b = P·n̂ = P cosθ` (a *cosθ*, dipole-like
  distribution), and a uniformly polarized solid sphere has a **uniform, non-zero** interior field
  `E = −P/(3ε₀)`. ✘ for "zero interior."

So the "interior field-null" datum that §3.2/§6.1 lean on does **not** follow from an electret's (polarized)
charge state — it would require an engineered uniform *monopole* surface charge, which an electret is not.
This is the same tension the doc itself flags in §6.2 (axial poling vs central null), so it is not fatal — but
the stated equivalence is a real conceptual conflation and should be corrected, not used as a clean given.

### 2.4 Framing observation [RH]
Both the repo README ("the physics in this repo is entirely mainstream … no DCCREG theory required") and the
ion-siphon MIGRATION §6 ("strict physics only … if a framework-tagged companion is wanted later, it should be
a separate document") position these as the *mainstream-presentable face* of a larger framework. That is fine
as a discipline — but it raises the bar: a doc that advertises "strict physics only" must not contain a
non-depleting source. §2.2 is precisely the kind of claim that the strict-physics framing is supposed to
exclude, and it slipped through.

---

## 3. Recommendations (no code changed; review only)

1. **Ion-siphon §3.1/§5.2/§8 — write the continuous-mode energy balance.** State plainly that sustained
   `I_ss` is paid for either by the electret's finite stored energy (then `V_e` decays and "indefinite" is
   wrong) or by a depleting/replenished atmosphere–earth reservoir (then re-instate the Stage-I bleed-down
   and credit the atmosphere, not the electret). Drop "non-sagging source + steady current indefinitely" as a
   joint claim. [OC]
2. **Ion-siphon §3.2 — fix the polarization/surface-charge equivalence.** Either specify an engineered
   uniform monopole surface charge for the null, or acknowledge the polarized electret gives a uniform
   non-zero interior field and treat the null as an unsolved geometry target (consistent with §6.2). [OC]
3. **Keep** the dose-mode result, `L = mℓ/(ne²A)`, the kinetic-inductance derivation, and all the existing
   honesty/open-problem flags — those are sound. ✔
4. **Repo:** no action needed for conservation; it is mainstream. The natural next block remains the
   dielectric-breakdown / safe-voltage bound already listed as an open fork. ✔

**Bottom line:** the repo is clean. The ion-siphon "continuous mode" is the one place where mainstream physics
is violated — by treating an electrostatic electret as a perpetual EMF. Recast it as energy-bounded (dose
mode / depleting reservoir) and the whole package becomes mainstream-consistent.
