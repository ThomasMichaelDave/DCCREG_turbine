# Round-trip design loop: predictions and outcomes

Each prediction is recorded here **before** its run, then the outcome is filled in with a one-line verdict:

| verdict | meaning |
|---|---|
| ADOPTED | the move is kept |
| DROPPED | the move is abandoned |
| CONFIRMED | the prediction held |
| REFUTED | the prediction failed |
| SURPRISE | the result was not anticipated |

## Ground convention (TMD)

The machine floats completely in practice. Every virtual ground used in a simulation is stated, and a result that depends on one is flagged **[GROUND]**.

| basis | what it means | label |
|---|---|---|
| physical | the machine floating in free space: every node's capacitance goes to infinity, the 25× Robin boundary | "free" |
| historical default | a grounded can 50 mm out | "can50", a virtual ground |

## Step 0: stray budget (engine only, reference build, rotor tips 15°)

**Groups.** Each group is scaled on the field-solved C(θ):

| group | couplings | how it is scaled |
|---|---|---|
| C1 | 1–R-A and 4–R-B | the floor scaled by f, swing kept: C − (1 − f)·min C |
| Cx | 7–n17 and 8–n23 | the floor scaled by f, swing kept |
| X | every other node-to-node coupling | × f |
| E | every node's capacitance to the can or to infinity | × f |
| Ca | Ca and Cb | × f |

**Predictions.**
- **B1.** C1 and E are both binding: no single group scaled alone to f = 0.1 reaches z ≥ 1.2.
- **B2.** C1 alone at f = 0.1 gives the biggest single-group gain, but z < 1.1.
- **B3.** The pair (C1, E) at f = 0.25 reaches z ≥ 1.2 on the free basis.
- **B4 [GROUND].** On the free basis, moving the virtual reference from infinity to R-A changes z by < 0.02.

**Outcomes:** (filled after the run)

The run was `python3 sim/rt_budget.py`, recorded in `sim/rt_budget.json`. Step 1's part-ownership solves are in `docs/geometry/rt/freeze-t15-free.attrib.json`.

| | prediction | outcome |
|---|---|---|
| B1 | no single group alone reaches 1.2 | **CONFIRMED.** Best single group on free: X × 0 → 0.967. On can50: Ca × 3 → 0.903 |
| B2 | C1 is the biggest single-group gain | **REFUTED.** X (the cross-strays) is bigger. On free: X × 0.1 → 0.955 against C1 × 0.1 → 0.886 |
| B3 | (C1, E) at 0.25 reaches 1.2 on free | **REFUTED.** 0.886. On the free basis E barely matters: E × 0 → 0.868 from 0.861 |
| B4 [GROUND] | free basis, reference ∞ → R-A changes z by < 0.02 | **CONFIRMED.** 0.8608 → 0.8624 (Δ 0.0016). On can50 the shift is 0.011 |

**SURPRISE.** Cutting the island Cx floor *lowers* z inside the winning combinations: C1 × 0.1, E × 0.1, X × 0.1 gives 1.2034; adding Cx × 0.1 gives 1.1203. The island floor is not a target.

**Budget on the physical (free) basis.**

| C1 floor | X cross-strays | E | z | converged |
|---|---|---|---|---|
| × 0.1 (191 → ~19 pF) | × 0.1 (~620 → ~60 pF) | any | **1.14** | yes |
| × 0.1 | × 0.1 | × 0.1 | **1.20** | yes |
| × 0.25 | × 0.1 | × 1 | 1.06 | yes |
| × 0.1 | × 0.25 | × 1 | 1.05 | yes |

The threshold for a growing mode is C1 ≲ 0.25 together with X ≲ 0.25. **C1 and X must fall together, by roughly an order of magnitude each.** Ca × 3 adds about +0.06 on top.

**Step 1: who owns the strays (free space; cross-strays 585 pF at θ 0, 654 pF at θ 30).**

1. **The Ca/Cb counter foils (rails 1 and 4) facing the rotor's Cx island foils (n23/8 and n17/7).** About 110 pF per island side, about 225 pF in all. This is the single biggest X owner.
2. **The bank bus rings (2, 3) facing the Cx foils.** About 28 pF each side.
3. **The C2/C1 rotor faces facing the opposite Cx foils.** 30 pF.
4. **Lead to lead.** About 45 pF.

**The C1 floor at disalignment** (θ 30):

| source | pF |
|---|---|
| face–face edge fringe | 79 |
| n18 septum C_R foil → stator C1 face | 29 |
| Ca counter → rotor C1 face | 28 |
| rotor leads → stator C1 face | 27 |
| node-1 lead / bus → rotor face | 16 |

**Next moves, retargeted.**
- **M1.** A screen, or a radial or axial separation, between the Ca/Cb band and the rotor Cx island faces. Target: X −200 pF or more.
- **M2.** Offset or recessed C1 sector edges. Target: −79 → about −30 pF.
- **M3.** Screen the septum C_R foil and the Ca counter from the C1 face. Target: −57 pF.
- **M4.** Route the rotor leads out of the stator face's view. Target: −27 pF.

## Size limit (TMD)

The septum disc may be at most **1000 mm in diameter**: r_edge ≤ 500, which is the reference build (r_out 387). The size lever is therefore gone. Every move is judged at the reference size, and z ≥ 1.2 must be reached at D 1000.

## Step 2, move M1: trim the Ca/Cb counter-electrodes to their band (`counter_trim=1`)

The counter foils (rails 1 and 4) spanned the whole stator plate, r95–387, while the Ca/Cb electrodes are a 25 mm ring (r357–382). M1 trims the counters to r352–387, the electrode band plus the dielectric margin. All builder checks pass, integrity PASS, G-JS parity holds.

Predictions, recorded before the run. All on the free basis.

| | prediction |
|---|---|
| M1-a | the rail-counter ↔ island couplings (1–n23, 1–8, 4–n17, 4–7; ~223 pF at θ 30) fall by ≥ 70 %, so X falls by ≥ 150 pF |
| M1-b | "Ca counter → rotor C1 face" (28 pF) falls to ≤ 8 pF, so the C1 floor falls by ~20 pF |
| M1-c | Ca and Cb (field) change by ≤ 10 % |
| M1-d | z rises to 0.88–0.90: a step, not a pump. Per the budget, X must also go ×0.1 and C1 ×0.1 |
