# Findings — FULL-SIM: the complete coupled machine on the locked r0.15 graph

**Branch** `full-sim-coupled` (off `topology-recon-r0_13`, which carries `main` + the DXF-sourced
`topology_edge_list.csv`). **Verdict:** **`FULL-CLOSES`** — but *thin and vacuum-gated*. The whole
machine pumps, holds 15 kV under the **real** shuttle + **real** 12-branch motor load, and the
**emergent** contra-rotation output (**0.91 W**) clears the stator mechanical drag (**0.53 W** at 1 Pa,
margin **+0.38 W**) — *only* in a clean cavity: the balance holds at ≤ 10 Pa and **fails by 100 Pa**.
The **real floor is 16.7 W**, replacing the 56 W r0.2 stub and the 138 W artifact. The independent
torque-integral guard closes to machine precision (**1.2 × 10⁻¹⁶**).

This is the first model where the **whole** pump (emergent doubler + real flying-bucket shuttle) and the
**whole** motor (12 real L/C branches) emerge together on the verified topology — superseding the
piecewise S5–S8 stack. All three r0.2 defects are fixed (below). **No new energy:** the belt sources
every watt; the guard makes a non-closing ledger a bug, not a discovery.

---

## §0 precondition (topology of record)

The brief's §0 branches off `main` "after the r0.15 recon is merged / the DXF-sourced edge list is the
topology of record." The recon (`TOPOLOGY-CONFIRMED`, `topology_edge_list.csv` DXF-sourced r0.15) is on
`topology-recon-r0_13`, **not yet merged to main**. Rather than merge unasked, this branch is cut **off
`topology-recon-r0_13`** so it consumes the locked edge list directly (and inherits `main`'s S8/energy-
balance content). The 12 Cem branches, the shuttle nodes 7/8, the split resonator 9/10, and the four `[?]`
gaps in the model all match `topology_edge_list.csv` net-for-net. **Flag for v0.11:** merge the recon to
`main` so the edge list is the topology of record there too.

## The three r0.2 defects — fixed (brief §0)

| # | r0.2 defect | fix here |
|---|---|---|
| 1 | **Tautological guard** — `E_belt_in` was assembled from the same terms as `E_diss` (resid ≡ 0) | `E_belt_in` is the **independent mechanical torque integral** `∮T_retard·ω dt = W_mech(½∮V²dC) + W_coll(shuttle collapse) + E_drag`; the destinations are tallied separately from the electrical/loss models. Guard residual **1.2 × 10⁻¹⁶** (a real check, not an identity). |
| 2 | **Output pinned at 0** by hard-coded `P_MOTOR < P_CORE` | output **emerges** = `P_motor − copper(i²R) − core(flux)` on the real branches = **+0.91 W** (sign positive, a result). |
| 3 | **Placeholder circulation** `½·440nF·(3kV)²` | **real** reactive exchange (peak-to-peak storage, ∫\|P_internal\|) = **22.3 mJ** (and it tracks `cap_scale`, 11→45 mJ). |

---

## §4 named checks

| # | check | result |
|---|---|---|
| 1 | frozen empty-diff (doubler/shuttle/resonator read, not edited) | ✓ clean |
| 2 | **Gate 0** — stub limit reproduces S8 r0.2 | ✓ z **1.334**, η **0.3860**, reach **14.95 kV**, dissipation **56.08 W**, storage **88.76 mJ**, output **0** |
| 3 | **emergent W_coll** ≈ 12.449 mJ + island < 21 kV | ✓ **12.4489 mJ** (frozen anchor, MATCH); island fires at **20 kV** < 21 kV ceiling |
| 4 | **Cem branches** — f_res = PRF; reach holds; emergent readout | ✓ f_res **299.9 Hz** (=PRF_branch); \|Z\|@f0 = 2.56 MΩ (**×8112 Z₀ → spectator**, reach holds); I_peak **107 mA**, N·I **114 A-t** « 1650, B **72 mT**, copper **1.40 W**, core(flux) **0.48 W**, output **0.91 W** |
| 5 | **independent guard** < 0.1 % | ✓ **1.2 × 10⁻¹⁶** (torque integral vs destinations) |
| 6 | **four-destination partition** — real floor | ✓ storage 88.76 mJ / circulation 22.3 mJ / **output 0.91 W** / **dissipation 16.7 W** |
| 7 | **BALANCE on real branches** | output **0.91 W** vs stator mech-drag **0.53 W** → margin **+0.38 W** at 1 Pa (vacuum-gated) |
| 8 | sweeps + verdict | ✓ **`FULL-CLOSES`** (thin, vacuum-gated) |

---

## Stage A — Gate 0 (the scaffolding is trustworthy)

In the **stub limit** (shuttle frozen to the `W_COLL` constant, Cems to the S8-r0.2 `P_MOTOR`/`P_CORE`
stub) the full integrator reproduces **S8 r0.2 exactly**: dissipation **56.08 W**, storage **88.76 mJ**,
output **0**, with z = 1.334 and η = 0.3860 re-derived *emergently* from the frozen `doubler_core`
(`solve_doubler4` on the G3 geometry) and the frozen `½∮V²dC` decomposition (the `W_mech = ΔU + E_tax`
identity closes to 1.4 × 10⁻¹⁶). The 56.08 W decomposes as C_R-chain 17.03 + drag 10 + core 15 + Cem
copper 14 + arc 0.05. **Gate 0 PASS** — the new scaffolding is validated before any real subsystem is
believed.

## Stage B — the real flying-bucket shuttle (W_coll emerges)

The flying-bucket transfer is brought *into* the integration: the doubler restores the rail (budget
η·W_mech = 6.15 mJ/fire), the island picks up at the 648 pF plateau (V* = 2.15 kV), the rotor collapses
Cx toward 16 pF boosting V to the 20 kV strike, and the gap fires **mid-collapse** at C_fire = 69.8 pF.
At periodic steady state (E_fire spread 0.0):

- **W_coll EMERGES = 12.4489 mJ** — matching the frozen `shuttle_core` anchor to < 0.05 mJ. The 12.449 mJ
  constant is retired; it is now a per-cycle result and a regression target met.
- E_fire = **13.95 mJ**, Q = 1.395 µC, rail-seed = 1.50 mJ/fire (the doubler's share of the fire).
- the island fires at **20 kV, under the 21 kV ceiling** (no node over-volt).

## Stage C — the 12 real Cem branches (the motor emerges)

The stub is replaced by the 12 driven L_A/C_AR + L_B/C_BR branches (two banks of 6, group A/B alternating
at PRF_branch = 300 Hz). The **Block-D premise is confirmed**: f_res = **299.9 Hz = PRF_branch**, and the
branch is a **high-Z spectator at f₀** (\|Z\|@637 kHz = 2.56 MΩ = ×8112 Z₀), so the f₀ reach is **not
detuned** — 15 kV holds under the load. The branch current is **pump-limited**, and the readout is
**emergent**:

- I_peak = **107 mA** → N·I = **114 A-t**, far below the 1650 A-t ceiling (the pump nets only ~2.8 W to
  the motor; the full N·I would need ~kW). Gap flux **B = 72 mT**.
- copper i²R = **1.40 W** (6 branches at the real current); core from the **flux/Steinmetz model** =
  **0.48 W** — **not** the fixed 15 W stub (at 72 mT the iron loss is small).
- reluctance output (½i²dL/dθ, what's left) = **+0.91 W** contra-rotation — emergent, **sign positive**.

## Stage D — the full operating point + the independent guard

`E_belt_in = ∮T_retard·ω dt = W_mech (9.56) + W_coll (7.47) + E_drag (0.56) = 17.59 W`, computed entirely
on the **mechanical** side. The destinations — C-C tax 5.87, dielectric 6.22, ring-copper 2.03,
fire-transfer loss 0.12, Cem-core 0.48, Cem-copper 1.40, drag 0.56 (heat) + **output 0.91** — are tallied
**independently** from the electrical/loss/flux models. The two routes agree to **1.2 × 10⁻¹⁶**: the guard
now has teeth (a routing bug — e.g. dropping a Cem term, or the arc double-count that this build caught and
removed — breaks it; in r0.2 it could not, because `E_belt_in` *was* the destination sum).

**Four-destination partition @ 1 Pa:** storage **88.76 mJ** · circulation **22.3 mJ** (real) · output
**0.91 W** · dissipation **16.7 W** (diss-fraction 0.948). **The real floor is 16.7 W** — the inflated
fixed-15 W core and fixed-10 W drag of the stub are replaced by the emergent flux-core (0.48 W) and the
vacuum-set drag (0.56 W at 1 Pa).

**BALANCE (the S7 question, now measured on the real branches):** emergent output **0.91 W** vs the
stator's **mechanical** drag **0.53 W** (½ windage 0.028 + bearing 0.5) → **margin +0.38 W**. (The Cem
core 0.48 W + copper 1.40 W are already netted *inside* the 0.91 W output; the belt covers the rotor drag
via `E_drag`.) The S7 estimate (margin −1 W against a 15 W fixed core) is superseded: with the **emergent**
flux-core the motor's own iron is cheap, and the binding constraint is **windage**, i.e. **vacuum**.

## Stage E — sweeps + the floor's sensitivity

| sweep point | output W | dissipation W | margin W | guard resid |
|---|---|---|---|---|
| garolite, **1 Pa** (base) | 0.911 | 16.68 | **+0.383** | 1.2e-16 |
| mica (5× lower tanδ) | 0.911 | 16.68 | +0.383 | 1.2e-16 |
| **10 Pa** | 0.911 | 17.19 | **+0.130** | 1.2e-16 |
| **100 Pa** | 0.911 | 22.25 | **−2.403** | 0.0 |
| **0.1 Pa** (hard vac) | 0.911 | 16.63 | +0.408 | 1.2e-16 |
| cap_scale 0.5 / 2.0 | 0.911 | 16.68 | +0.383 | 1.2e-16 (circ 11 / 45 mJ) |

The balance is **entirely vacuum-gated**: it crosses from + to − between 10 and 100 Pa. The **septum DOF
(garolite→mica) does not move the output** — it is a ring-side loss, not a motor-side lever (it shaves the
6.2 W dielectric but the motor budget is untouched). `cap_scale` only moves the **real circulation**
(11↔45 mJ), confirming the metric is reactive, not dissipative. The guard closes at every point.

## Verdict + honest caveats

**`FULL-CLOSES`** — the machine **pumps** (W_coll emerges 12.449 mJ), **holds 15 kV** (real shuttle + Cem
spectator load, no detune, island < 21 kV), and **contra-rotates** with a **positive emergent output**
that clears the stator drag at ≤ 10 Pa. The real floor is **16.7 W**.

**But the close is thin and conditional, and I am stating that plainly:**

1. **Vacuum-gated.** Margin is **+0.38 W at 1 Pa, +0.13 W at 10 Pa, −2.4 W at 100 Pa.** A clean cavity is a
   **hard requirement**, not headroom. The dominant lever is **windage/vacuum**, exactly as flagged.
2. **Thin & model-dependent.** The +0.38 W rests on the **[IR] reduced resonant-branch model** (Q_CEM = 30,
   the resonant build-up `I_peak ~ √(Q·E_net/L)`). A lower effective Q, higher copper, or a larger
   core-loss coefficient would erase the margin. The output is **pump-throughput-limited** (~2.8 W into the
   motor), so it cannot be grown by driving the branches harder — only by netting more from the doubler.
3. **What's robust** (model-independent): the pump works and the reach holds; W_coll = 12.449 mJ; the Cem
   branches are PRF-resonant f₀-spectators (reach not detuned); the **real floor (16.7 W) is far below the
   stub (56 W) and the artifact (138 W)** because the real flux-core is cheap; and the guard closes at
   10⁻¹⁶. The headline isn't "free spin" — it's that **the motor's iron is not the wall S7 feared; the wall
   is windage**, and a thin contra-rotation balance closes **iff the cavity is pumped down**.

## Deliverables

`sim/full_sim_coupled.py` (the full multi-rate integrator: emergent doubler + real shuttle + fire-ring +
12 real Cem branches + quasi-static mechanical; the independent torque-integral guard; the real
circulation; the emergent output; 7 non-circular self-tests) · this findings doc ·
`full_sim_partition.csv` (per operating point + torque residual) · `full_sim_cem_branches.csv` (per-branch
current/copper/core/output) · `full_sim_partition.png` (four-destination partition + BALANCE-vs-vacuum).
Frozen solvers (`doubler_core.py`, `shuttle_core.py`, `resonator_sim.py`) read-only, empty-diff asserted.
**Not merged.**

### Roadmap (brief §8)

`FULL-CLOSES` (thin, vacuum-gated) is a real result → **v0.11 (reconvergence freeze)** with the full-machine
operating point as the headline: the real floor (16.7 W), the real BALANCE (+0.38 W at 1 Pa, vacuum-gated),
r0.15 as the geometric authority, the DXF-sourced edge list as the manifest, the audited foundation
(z 1.334, η 0.3860). Punch-list (parallel): the ND7/8 label flag; core-symbols-as-blocks for a future
net-trace of the dense core. Then the **dimensioned** mechanical DXF → the angular/clocking/phase-plate sim
family → bearings/rotordynamics/vacuum-gap flashover (the next geometry-gated arc; the *electrical* machine
is fully simulated here).
