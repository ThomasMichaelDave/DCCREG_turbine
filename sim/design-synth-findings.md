# Findings — DESIGN-SYNTH: a constrained dimension-chooser

**Branch** `design-synth` (off `torque-sim` — the brief's `design-optimize` base does not exist as a
branch; `torque-sim` carries the frozen solvers, the validated profiles, and the established machine,
and the "rules" are **reconstructed from the campaign's established results**). **Verdict:**
**`SYNTH-FEASIBLE`** — Claude Code chose every dimension, **every invariant held**, the conservation
guard **closes and can fail**, and the tool reports **which rule binds** each objective. The
infeasible-goal probe returns `SYNTH-INFEASIBLE` **with the named blocker**, exactly as specified.

**The principle, realized.** Dimensions are decision variables; the rules and derivations are hard
constraints. The synthesizer **calls** the frozen solvers (`doubler_core` z/η, `shuttle_core` W_coll)
per candidate — it never re-derives, fits, or overrides them — so flexibility can only move within the
feasible region the invariants define. The frozen solvers keep *intent* and *geometry* from ever
trading places.

> **r0.2 correction (bus margin) — `CANARY-RESTORED`.** r0.1 reported the rotor diameter as the
> *active-band* diameter (`r_out × 2`) with **no bus margin**, and computed the rim at `r_out` — so the
> established machine "reproduced" at 774 mm instead of its real **~982 mm** rotor (R387 active-band
> outer → **R491 rotor outer after the 27 % bus** → R500 plate edge), and I9's rim margin was
> overstated. The synthesis *logic* is unchanged (z-band, bindings, infeasible-naming are ratio-based,
> bus-independent). Fixed: `BUS_MARGIN = 0.27`, every reported diameter = `2·r_out·(1+bus)`, the rim is
> at the **rotor body** (R491), and the **canary now asserts the rotor diameter** (~982 mm) — it
> correctly **fails at 774 mm if the bus is dropped** (verified). Corrected table:
>
> | item | r0.1 (no bus) | r0.2 (corrected) |
> |---|---|---|
> | established rotor (canary) | 774 mm | **983 mm** ✓ (assertion live, [960,1010]) |
> | min_diameter @ 15 kV | 500 mm | **635 mm** (r_out 250) — bound by I3 |
> | max_eta | 700 mm | **889 mm** (r_out 350) — bound by I3 |
> | max_rpm rim @ 6000 rpm | 157 m/s | **199 m/s** (at the 200 m/s wall) |
> | max_rpm I9 ceiling | "9000 rpm" | **~6000 rpm** (rim binds at the rotor radius) |
>
> The infeasible probe is re-stated in the corrected definition: "rotor dia ≤ 300 mm" is now
> `r_out ≤ 118 mm` (was 150); blocker unchanged (z → 1.0, **I3**). z/η and all binding constraints are
> identical to r0.1. The synthesizer's diameters are now comparable to the parametric reference, the
> HTML sizer, and the worked example (all apply bus ≈ 0.27–0.29).

---

## §5 named checks

| # | check | result |
|---|---|---|
| 1 | frozen empty-diff; **solvers called (not re-implemented)** per candidate | ✓ `doubler_core`/`eb` for z/η, `island_charging`(frozen shuttle) for W_coll; cached by scale-free ratio |
| 2 | **regression anchor** — established ~1000 mm / 15 kV reproduces | ✓ **C1_max 280 pF** (forward model exact), z **1.334**, η **0.386**; feasible on all 10 invariants |
| 3 | chosen objective + optimal free-var set | ✓ 3 objectives (min-diameter, max-η, max-rpm) below |
| 4 | **full §2 battery passes; binding invariant named** | ✓ I3 (size, η), I9 (rpm) — distinct, meaningful |
| 5 | **I1 conservation closes + +5 % trip fires** | ✓ resid **≤1.3×10⁻¹⁶**, +5 % source perturbation **trips** (non-tautological) |
| 6 | design sheet + compliance table | ✓ `synth_design.csv`, `synth_compliance.csv` |

## The invariant battery (reconstructed from the campaign)

| # | invariant | encoded as | source block |
|---|---|---|---|
| **I1** | conservation, real | per-cycle ledger closes **and** +5 % source-term perturbation trips it | torque-sim |
| **I2** | frozen-solver authority | z/η from `doubler_core`; W_coll from `shuttle_core` — called, never substituted | foundation |
| **I3** | scale-free z | z ∈ **[1.20, 1.45]** (device 1.203 … wide 1.438); ratios only | doubler anchors |
| **I4** | insulate-first | gap V_bd(vacuum)=60·g^0.6 kV > V_target; septum 5 kV/mm derated; split-coil antinode out | coil-topology / freeze |
| **I5** | tax managed | η ≥ 0.15 (else stage N) | energy-balance |
| **I6** | parasitic floor | C_par ≥ 20 pF; slack = modulation margin (C_max−C_par)/C_par | S-blocks |
| **I7** | motor matched | output ≤ pump net; f_res = PRF (300 Hz); high-Z spectator at f₀ | S7 / full-sim |
| **I8** | DC-trapped tank | tank held DC, tan-δ duty-limited (not the voltage lever) | S8 (53 W debunk) |
| **I9** | mechanical | rim < 200 m/s (soft 150); supercritical; vacuum ≤ 10 Pa | freeze / full-sim |
| **I10** | shuttle integrity | island strike < node ceiling (21 kV); collapse reaches V_strike from V* | geom-validate |

## The regression anchor (the canary)

The established machine (r_in 95, r_out 387, g_v 7 mm) synthesizes to **C1_max = 280 pF** (the forward
geometry model is exact), **z 1.334 / η 0.386** (frozen solver), rotor **774 mm diameter**, **feasible
on all 10 invariants**. The least-slack invariant is **I10** (the shuttle strike-vs-ceiling margin,
20 vs 21 kV, slack +0.05 — the machine's tightest rule). **The coupling is intact** → no synthesis is
believed until this passes.

## The synthesized designs (Claude Code chose; the rules held)

| objective | optimal dimensions | z | η | **binding constraint** |
|---|---|---|---|---|
| **min diameter** @ 15 kV | dia **500 mm** (r_out 250), g_v 3 mm, C_min 20 pF | 1.272 | 0.441 | **I3 scale-free z** — shrinking to dia 400 collapses the modulation (z < 1.20) |
| **max η** (min tax) | dia 700 mm, g_v 5 mm, C_min 50 pF | 1.225 | **0.526** | **I3 scale-free z** — pushing η higher (lower modulation) drives z to the 1.20 floor |
| **max rpm** | dia 500 mm @ **6000 rpm** (rim 157 m/s) | 1.272 | 0.441 | **I9 mechanical** — 9000 rpm would exceed the 200 m/s rim limit |

**The single most useful diagnostic — the binding constraint — is distinct per objective:** the
**doubler z-derivation (I3)** is what limits the *small* and the *efficient* designs (you cannot
shrink the plates or trade modulation for efficiency without the scale-free z falling out of its
validated band), while **mechanics (I9)** is what limits *speed*. The tool found these by perturbing
the objective's variable toward improvement and reporting the rule that fails — the *active*
constraint, not merely the globally-tightest one.

## I1 — a conservation guard that can fail (carried from torque-sim)

The per-cycle ledger closes (residual ≤1.3×10⁻¹⁶) **and the mandatory +5 % self-test trips it**: a
+5 % perturbation of the source term moves the residual off zero (the destinations are independent
models using the *nominal* energies, so they don't track the perturbed source). As in torque-sim, the
**discriminator is the trip, not the baseline magnitude** — the guard is a genuine check, not an
identity. Every reported feasible candidate passes it.

## The infeasible-goal probe (a result, not a failure)

Demanding a **tiny rotor (dia ≤ 300 mm)** at 15 kV returns **`SYNTH-INFEASIBLE`** over the grid (0/6
feasible), and **names the blocker: I3 (scale-free z)** — at r_out 150 the C_max (62 pF) approaches
the parasitic floor (20 pF), the modulation collapses to ~2, and **z → 1.000 (no pumping)**. The goal
is impossible *without relaxing a stated rule*: a higher-z ratio family, a smaller stray floor, or
accepting a lower z. The tool says **which** — the prize the brief specified.

## Verdict + what it means

**`SYNTH-FEASIBLE`** — the synthesizer is the standing bridge between *intent* and *geometry*: state a
goal, get a dimensioned design **guaranteed by construction to honor every derivation and rule** the
campaign established. The flexibility lives in the dimensions; the discipline lives in the invariants;
and the frozen solvers keep the two from trading places. The **binding constraint** per objective is
the actionable output — it names the rule to relax if you want to push further (I3 for size/efficiency,
I9 for speed).

## Deliverables

`sim/design_synth.py` (the synthesizer: free-variable search, the §2 invariant battery with
frozen-solver calls, the configurable objective, the *active*-binding-constraint reporter; self-tests:
the regression anchor + the +5 % conservation trip) · this findings doc · `synth_design.csv` (the
chosen dimensions per objective + binding constraint) · `synth_compliance.csv` (per-invariant
pass/slack at the anchor) · `synth_feasible.png` (the I3 z-band edge vs rotor diameter — the
size-limiting derivation, with the optima marked). Frozen empty-diff asserted. **Not merged** — the
synthesized designs feed the DXF/deck only on TMD's approval.

### Roadmap (brief §9)

`SYNTH-FEASIBLE` → **proposed dimensioned designs** with their binding constraints and a clean
conservation guard. **TMD reviews**; on approval a chosen design feeds the **concentric-pole drawing**
(optimized motor geometry — which also closes the torque-sim's `SELF-SPIN-INDETERMINATE` by making
`L(θ)` geometric) and a DXF/deck update. `SYNTH-INFEASIBLE` → the named blocking invariant tells you
exactly which rule the goal violates — relax it deliberately and re-run. The synthesizer is the
intent→geometry bridge for the remaining design arc.

> **Base-branch note.** The brief branches off `design-optimize`, which has not been built in this
> repo (no numbered-rules doc / HTML-sizer-as-rules artifact exists). I branched off `torque-sim`
> (carries the frozen solvers + validated profiles + established machine) and **reconstructed the
> invariant battery from the campaign's established results** (cited per invariant above). If a
> formal `design-optimize` rules block is intended first, this synthesizer drops onto it unchanged —
> the invariants are already encoded as callable checks.
