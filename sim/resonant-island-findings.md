# Findings — RESONANT-ISLAND: the series-LC island transfer (the efficiency fix)

**Branch** `resonant-island` (off `design-synth`). **Verdict:** **`RESONANT-TRANSFER-MODELED`** — the
LC island transfer is modelled, conservation **closes and trips**, the η gain is **quantified with the
island-vs-doubler decomposition**, the timing/current/voltage limits hold, and I10 + the topology
baseline are updated to the new 37-component KiCad netlist. **The fix is real and sized — but the
load-bearing caveat is loud: the island inductor removes only the island's ~31 % share of the loss;
the doubler Ca/Cb bucket-brigade (69 %) is untouched, so the next inductors belong on Ca/Cb.**

The frozen solvers stay frozen — `shuttle_core`/`island_charging_cosim` remain the **direct-transfer
baseline**; the resonant transfer is a **new** solver (`reference/island_resonant_core.py`).
**Not merged** (a topology change — merges only on TMD's sign-off of the operating sequence *and* the
gain).

## The assumed operating sequence (⚠ flag for TMD sign-off — design authority)

From the KiCad netlist (`DCCREG_Turbine_circuit.net`, 37 components) the **connectivity** is fixed:
`net21 (C1/Ca1/L_A rail) —SG3a— Cx3 —Lx3— net10 (Cb1/C_BR bank)`, and the mirror
`net23 —SG4a— Cx4 —Lx4— net4 (Ca1/C_AR bank)` (cross-coupled AR↔BR). The **assumed cycle** is: the
rotary load gap SG3a conducts, the rail charges the island Cx3, then Cx3 **rings through the series
Lx3 into the BR transfer bank** in one half-cycle, completing at **current-zero** so SG3a
**self-quenches**; Cx4/Lx4 mirror. The direct baseline is the two-cap dump of this same Cx→bank
transfer (the audited **4.41 mJ/fire** island pickup tax). **TMD confirms the cycle before the model
is trusted.**

## §-checks

| # | check | result |
|---|---|---|
| 1 | frozen `shuttle_core`/`doubler_core` empty-diff; resonant model is a **new** file | ✓ byte-identical; `reference/island_resonant_core.py` is new |
| 2 | assumed operating sequence stated + flagged for TMD | ✓ (above) |
| 3 | core returns t½, i_pk, Q, E_loss, f_rec; closed-form vs integrated tagged | ✓ + **note**: the integrated `[SOLVER]` loss runs **~2× the brief's closed form** — the `(π/2Q)` estimate under-counts the ring dissipation; the integral is authoritative |
| 4 | conservation **closes** + **+5 % R/Lx trip** | ✓ residual **4×10⁻¹³**; +5 % R → **4.9 %** (fires) — recovered tax is redistribution, not invention |
| 5 | η_resonant vs η_direct over Q; the loss **decomposition** | ✓ (below) — island **31 %** / doubler **69 %** of the combined tax |
| 6 | the three Lx constraints; t½ vs the conduction window | ✓ Lx feasible 0.01 mH–1 H; t½ ≪ window → clean self-quench at the first current-zero |
| 7 | I10 updated; synthesizer feasible with Lx; canary re-confirmed | ✓ I10 carries the 3 sub-checks; **anchor still 983 mm, z 1.3336, η 0.3863, feasible** |

## The resonant-transfer model `[OC]` LC, `[SOLVER]` integrated

`reference/island_resonant_core.py`: a source cap `C_src` (island Cx at ΔV above the bank) transfers
through series `Lx`/`R` into `C_bank`. `C_eff = C_src·C_bank/(C_src+C_bank)`,
`Z = √(Lx/C_eff)`, `t½ = π√(Lx·C_eff)` (transfer completes at current-zero), `i_pk = ΔV·√(C_eff/Lx)`,
`Q = Z/R`. The **direct dump loses `½C_eff·ΔV²` irrespective of R** (the two-cap paradox); the
**resonant transfer loses only the ring's resistive dissipation → 0 as Q→∞.** A series-RLC RK4
transient (`integrate`, **`[SOLVER]`, authoritative**) returns the actual q, E_bank, E_loss
(∫i²R dt), t½ (current-zero), i_pk and the conservation residual. *The integrated loss is ~2× the
brief's `(π/2Q)` closed form — the half-cycle ring dissipation is `≈(π/Q)·E_2cap`, not `(π/2Q)`; the
integral governs.*

## Conservation — redistribution, not invention `[ME]`

The guard checks the **independent** i²R loss integral against the **state-energy balance**
(`E_src_lost = E_bank_gained + E_loss + E_resid_L`); at the current-zero the inductor residual → 0.
It **closes to 4×10⁻¹³** and **the +5 % R perturbation (loss integral only) trips it to 4.9 %** — a
genuine check (Rule 6.1), not an identity. The recovered tax = (direct `½C_eff·ΔV²`) − (resonant
`E_loss`) = exactly the reduction in dissipation.

## η + the loss decomposition (the whole point — and the caveat) `[SOLVER]`

| audited loss term | mJ | share of combined |
|---|---|---|
| **island transfer tax** (direct two-cap dump — what Lx removes) | **4.41 / fire** | **31 %** |
| **doubler Ca/Cb bucket-brigade C-C tax** (the 61 %, **untouched by Lx**) | **9.79 / cycle** | **69 %** |

Over the Q sweep (`resonant_island.csv`), the resonant transfer recovers `f_rec = 1 − (loss/E_2cap)`
of the island tax: at a usable **Q ≈ 729 (R = 2 Ω)** it recovers **4.39 mJ/fire** → the combined
(island + doubler) tax drops **31 %**. Even at lossy **Q ≈ 15 (R = 100 Ω)** it recovers ~3.55 mJ (a
25 % combined-tax drop). **This is a real, sized gain.**

**The load-bearing caveat (do not over-headline):** the island transfer is **31 %** of the combined
tax; the **doubler bucket-brigade is 69 % and the Lx does nothing to it.** The realistic total-η win
is the island's share only — the dominant loss is the doubler Ca/Cb C-C tax. **The decomposition says
the next inductors belong on Ca/Cb** (resonant the bucket-brigade), not more on the island.

## The three Lx constraints + the commutation bonus `[OC]`

- **C-timing:** `t½ = π√(Lx·C_eff)` must fit the SG **conduction window** (assumed **5° @ 3000 rpm =
  278 µs**, flag for TMD). At every feasible Lx (0.01 mH–1 H) `t½ = 0.2–68 µs ≪ 278 µs` → fits easily.
- **C-current:** `i_pk = ΔV√(C_eff/Lx)` ≤ rating (100 A) — sets the **lower** Lx bound (1 µH → 108 A,
  over; ≥ 0.01 mH OK).
- **C-voltage:** the ring node sees ΔV·(1 + √(C_src/C_bank)) ≈ ΔV (bank ≫ island → no boost) = 5.1 kV
  < the insulation envelope.
- **Commutation bonus (§5):** the half-cycle ends at current-zero, so SG3a **self-quenches cleanly**.
  The exact match `t½ ≈ window` would need `Lx ≈ 17 H` (impractical); instead `t½ ≪ window` at any
  feasible Lx, so the gap quenches at the **first** current-zero — well inside the window, **no chop /
  no re-strike.** The resonant transfer and the self-break gap reinforce each other.

→ **not `TIMING-INFEASIBLE`** (a wide feasible Lx band), **not `GAIN-MARGINAL`** (31 % is a real
share) → **`RESONANT-TRANSFER-MODELED`**, with the decomposition pointing the next fix at Ca/Cb.

## Integration + the re-opened topology

- `design_synth` **I10** now carries the three resonant-island sub-checks (timing/current/voltage)
  using `island_resonant_core`; `Lx_mH` enters `ESTABLISHED` (1.0 mH). The frozen direct
  `shuttle_core`/`island_charging_cosim` remain the §5 baseline.
- **Topology of record → the 37-component KiCad netlist** (`docs/kicad/DCCREG_Turbine_circuit.net`,
  with Lx3/Lx4); `topology_edge_list.csv` regenerated from it (**37 components, 24 nodes**) so the
  container's consistency check matches the new graph. *This re-opens the r0.15 22-node topology — the
  cost of the efficiency win — and merges only on TMD's sign-off.*
- **Canary re-confirmed:** the anchor *with* the resonant island still reproduces **z 1.3336, η
  0.3863, ~983 mm, feasible** (the Lx is a transfer-efficiency lever; it does not change z/η_doubler).
  Binding still **I10**.

## Deliverables

`reference/island_resonant_core.py` (new; the LC model + the [SOLVER] integral + conservation/trip) ·
`sim/design_synth.py` (uses it; I10 + the 3 sub-checks + `Lx_mH`; frozen empty-diff) · this findings
doc · `resonant_island.csv` (η vs Q sweep + the decomposition) · `resonant_island.png` ·
`docs/kicad/DCCREG_Turbine_circuit.net` + `.dxf` (the new topology of record) · `topology_edge_list.csv`
(regenerated, 37/24). Frozen `shuttle_core`/`doubler_core` byte-identical. **Not merged.**

### Roadmap

On TMD's sign-off of (a) the operating sequence and (b) the gain: the resonant island is adopted, and
the decomposition's clear next step is to **put the same series-inductor resonant transfer on the
doubler Ca/Cb bucket-brigade** — that is where 69 % of the loss is, and the same LC physics recovers
it. The η headline waits for the bucket-brigade fix; the island fix is the first, smaller, validated
step.
