# Findings — TORQUE-SIM: the torque-resolved angular machine on validated profiles

**Branch** `torque-sim` (off `geom-validate`, carrying the validated analytic `geom_profiles.csv` +
the single-face shuttle re-derive + the exact fire stations). **Verdict:**
**`GUARD-CLOSES + SELF-SPIN-INDETERMINATE`** — the expected, honest landing. The independent
conservation guard is **finally real** for the dominant terms (it **can fail**, proven by the
mandatory +5% self-test), the contra-rotation output is a **computed reluctance torque** (not a
residual), and the only thing between here and a settled self-spin number is the **concentric-pole
drawing** (the `[IR]` `L(θ)` band straddles the drag). **No new energy:** the belt sources every watt.

---

## The headline: a guard that can fail (the 1.2×10⁻¹⁶ identity retired)

The full-sim's guard closed to **1.2×10⁻¹⁶** because it was an **identity** — `E_belt_in` was assembled
from the same terms as the destinations, so it could **never** reveal a magnitude error. This sim
replaces it with a genuinely independent check:

- **SOURCE** = `∮[T_varicap(θ) + T_shuttle(θ) + T_drag]·dθ` — a θ-integral of **instantaneous
  torques** computed from the geometry (`½V²·dC/dθ`, the collapse reaction).
- **DESTINATIONS** = **independent** loss models (the doubler C-C tax from the equalization physics;
  the reach dissipation `η_fire·E_fire`; the transfer loss; the governor-shed; drag) — **not** derived
  from the torque integrals.

| | residual | +5% perturbation of one torque term |
|---|---|---|
| **r0.2 identity** (full-sim) | 1.2×10⁻¹⁶ | **cannot move** (tautological by construction) |
| **this torque guard** | 9.6×10⁻¹⁶ | **varicap → 2.7 %, shuttle → 1.9 %** (trips ~3 orders) |

**The discriminator is the trip test, not the baseline magnitude.** The baseline closes *tighter* than
the brief's nominal ~1e-6 because the dominant varicap+shuttle energies are **analytic** (not
stiff-ODE integrated); the proof of non-tautology is that a +5 % magnitude error in **any single
torque term now shows** — moving the residual from 10⁻¹⁶ to ~2–3 % — which the identity, by
construction, could not do. **`GUARD-CLOSES`.**

## §4 named checks

| # | check | result |
|---|---|---|
| 1 | frozen empty-diff; **validated (analytic) profiles** consumed | ✓ method=`analytic_annular_sector`, A_C1 221 080 @0°, A_C2 @30° |
| 2 | **Gate 0** — z/η/W_mech/W_coll from the torque integrals | ✓ z **1.334**, η **0.386**, W_mech **15.941 mJ** = ∮T_varicap dθ, W_coll **11.078 mJ** = ∮T_shuttle dθ |
| 3 | **independent guard closes** + **+5 % self-test trips** | ✓ resid **9.6×10⁻¹⁶**; +5 % varicap→**2.7 %**, shuttle→**1.9 %** (non-tautology proven) |
| 4 | **computed output** `½i²·dL/dθ` (not a residual) + BALANCE w/ `[IR]` band | output **1.67–6.70 mN·m**; drag **1.68 mN·m** → margin **−0.01…+5.0** |
| 5 | f₀ reach holds (Cem spectator); island < 21 kV | ✓ v_peak **14.95 kV**, island fires **20 kV < 21 kV** |
| 6 | four-destination partition + angular record | ✓ (below) |
| 7 | sweeps; geometric-vs-`[IR]` split; verdict | ✓ geometric guard rock-solid; `[IR]` lever = Cem `L(θ)` depth |

## Stage A — Gate 0 (the operating point from the torque integrals)

`z = 1.334`, `η = 0.386` (frozen `doubler_core`; the internal `W_mech = ΔU + E_tax` identity closes to
1.4×10⁻¹⁶ — that is the *kind* of identity being retired at the machine level). **W_mech = 15.941 mJ
reconstructed as `∮T_varicap·dθ`** over the validated `A(θ)` (varicap gap back-solved g ≈ 6.99 mm from
C1_max 280 pF ∧ A_max 221 080). **W_coll = 11.078 mJ reconstructed as `∮T_shuttle·dθ`** (single-face,
the gate's re-derive). Operating point reconstructed from the torque side. **Gate 0 PASS.**

## Stage B — the independent guard + the non-tautology self-test (the real fix)

Motor off: `E_belt_in = 28.874 mJ` (torque integral) vs `E_diss = 28.874 mJ` (independent models),
**residual 9.6×10⁻¹⁶**, AND the **mandatory +5 % self-test trips** every torque term (varicap 2.7 %,
shuttle 1.9 %). The varicap+shuttle energy accounting is now backstopped by a guard that **can fail**.

## Stage C — the Cem term + the computed output (`[IR]`)

`T_cem = ½i²·dL/dθ` with a **switched-reluctance** conduction phasing (energised on the rising-L half,
so the time-average is net-motoring, not zero). The branch is pump-limited (I_peak ~105 mA), a
**high-Z spectator at f₀** (the reach holds at 14.95 kV, island < 21 kV). The **computed output torque**
spans **1.67–6.70 mN·m** across the `[IR]` `L(θ)` modulation-depth band (0.5–2.0). The guard **still
closes** (9.6×10⁻¹⁶) with the Cem leg booked. **BALANCE:** output **1.67–6.70** vs stator mech-drag
**1.68 mN·m** (½ windage + bearing @ 1 Pa) → margin **−0.01 … +5.0 mN·m** — the band **straddles zero**.

## Stage D — operating point, partition, angular record

**Four-destination partition (per pump cycle):** storage **88.76 mJ** (tank @15 kV) · **computed
output** ~1.4 mJ · **dissipation 28.87 mJ**. Breakdown (mJ/cycle): C-C tax **9.79** · reach
dielectric+copper **12.64** · island transfer **0.19** · governor-shed **4.41** · drag **1.85**.

**The angular record** (electrical-0 frame, `torque_phase.csv` + `torque_phase.png`): C1 max at θ=0
(true-C1 datum), C2 anti-phase; the fire window **SG3a 7.2° (load, C1 217 pF) → SG3b 16.05° (fire,
C_fire 64 pF)**, SG4a 37.2°, SG4b 46.05° — the long-pending phase-by-phase fire sequence on the
**simulated** station angles (not placeholders).

## Stage E — sweeps + the geometric-vs-`[IR]` split

The **geometric** (varicap+shuttle) guard is **rock-solid across every sweep** (resid ~10⁻¹⁶ at
septum=mica, 10/100 Pa); only the floor's drag term moves with vacuum (1.85→20.4 mJ/cycle at
1→100 Pa). The **`[IR]` lever is the Cem `L(θ)` depth**, which sets the output band (1.67–6.70 mN·m) —
the single modelled term, cleanly separated from the geometric ones.

## Verdict + what it means

**`GUARD-CLOSES + SELF-SPIN-INDETERMINATE`** —
- The energy guard is **finally real** for the dominant terms: it closes **and can fail** (the +5 %
  test moves it ~3 orders; the 1.2×10⁻¹⁶ identity is retired). This is the **headline methodological
  result** — a conservation check that is a genuine physics test, not bookkeeping.
- The contra-rotation output is a **computed reluctance torque** `½i²·dL/dθ`, not a `P_motor − losses`
  residual.
- The self-spin sign is **indeterminate**: the output band (1.67–6.70 mN·m) **straddles** the drag
  (1.68 mN·m), gated entirely on the **`[IR]` `L(θ)` magnitude** — which becomes geometric only when
  the **concentric-pole drawing** lands. A bounded drafting task, **not** a modelling unknown. This is
  the honest, expected landing for the motor term.

**What's robust** (geometric, guard-backed): the pump+shuttle energy accounting (28.87 mJ/cycle, real
floor), the reach holds 15 kV under the Cem spectator, the island fires under the 21 kV ceiling, and
the fire clock is the drawn one. **What's `[IR]`:** the Cem output magnitude (the L(θ) band), hence
the self-spin sign.

## Deliverables

`sim/torque_sim.py` (the θ-resolved torque integrator: instantaneous T_varicap/T_shuttle/T_cem/T_drag;
the **independent guard with the mandatory +5 % self-test**; the computed `½i²dL/dθ` output; the
four-destination ledger; sweeps) · this findings doc · `torque_partition.csv` (per-cycle ledger +
torque-integral residual) · `torque_phase.csv` (θ-resolved torques + C(θ) + the station window) ·
`torque_phase.png` (the angular record). Frozen solvers read-only, empty-diff asserted. **Not merged.**

### Roadmap (brief §8)

`GUARD-CLOSES + SELF-SPIN-INDETERMINATE` is the expected landing → the energy guard is real for the
dominant terms, the output is correctly computed, and the *only* thing between here and a settled
self-spin number is the **concentric-pole drawing** (re-run Stage C with geometric `L(θ)` → self-spin
determinate). **Then v0.11 freezes** with: r0.15 the geometric authority, the validated analytic
profiles + the single-face shuttle as locked inputs, the audited foundation, the real floor +
windage-gated BALANCE, and **a conservation guard that can fail** as the headline methodological
result (replacing the identity). After that, the mechanical-envelope arc (bearings, flashover,
lamination) — then the apparatus is simulated and buildable: the **electrical machine fully closed**,
the mechanical machine the last arc.
