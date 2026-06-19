# Findings — AUDIT: solver foundation

**Branch** `audit-solver-foundation` (off `main`). **Verdict:** **`FOUNDATION-DRIFTS`** — two foundation
quantities move materially: the **z-gate** re-anchors 1.2033 → **1.334** (it ran on stale device geometry,
F3), and **DOUBLER_ETA** drops 0.386 → **0.368** (the spark-gap arc loss, F6, the predicted outcome). The
other scalars (W_mech, W_coll, Q_isl) hold; F2 is benign (rigorous = heuristic); the topology is a
relabeling. **The foundation is corrected, not invalidated** — S8 r0.2 should consume DOUBLER_ETA = 0.368
and the z-anchor = 1.334; the propagated hold-floor change is small (~0.2 W), so S5–S8's *qualitative*
verdicts stand.

**Discipline.** The frozen solvers (`doubler_core`, `shuttle_core`, `resonator_sim`, `reference/`) were the
**subject, not the oracle** — read, never edited (**empty-diff asserted**). The audit built a *new,
independently validated* solver (rigorous LCP + spark-gap switch) and *compared*. Where the inherited
scalars fail they are **superseded** (re-based here, for S8 r0.2 to consume as a new freeze), not edited in
place — preserving producer/consumer discipline while letting the foundation be corrected. The circular
JS-mirror self-test is replaced by **rigorous-vs-frozen** and **ngspice-vs-solver** cross-checks.

---

## §3 named checks

| # | check | result |
|---|---|---|
| 1 | frozen byte-identical empty-diff | ✓ clean (solvers read, not edited) |
| 2 | `varcap.cir` v0.2 committed as SSOT; node-map built | ✓ committed (was only in /outputs) |
| 3 | topology verdict (F4/F5) | **relabeling** — pump core unchanged; resonator/Cems/island are load-side additions |
| 4 | current-geometry z (F3) | **1.334** (16–280/309) vs the **1.2033** device-anchor gate; gap +0.131; gate re-anchored |
| 5 | rigorous-vs-heuristic z (F2) | **0 state-mismatches** on device/current/wide → heuristic = LCP (benign) |
| 6 | spark-gap DOUBLER_ETA (F6) | 0.386 → **0.368** (mid), −4.7%; +0.17 W on the floor |
| 7 | re-based scalar table | z +10.9%, DOUBLER_ETA −4.7%, USEFUL −4.7%; W_mech/W_coll/Q_isl hold; resonator 960→789 |
| 8 | verdict + which scalar moved | **`FOUNDATION-DRIFTS`** — z-anchor, DOUBLER_ETA, USEFUL |

## Stage A — topology reconciliation (F4/F5)

`varcap.cir` v0.2 is **committed** as the electrical SSOT (it previously lived only in
`/mnt/user-data/outputs`, so the corrected topology had no in-repo reference). Building the node map: the
v0.2 **"returns-to-rail / no-ground"** is a **gauge choice** — the energetics depend only on voltage
*differences*, and `shuttle_core` "collapsed the rail to ground 0", which is the *same* node relabeled. So
the **pump core (ND1–4) is a relabeling of the frozen 4-node** network (C1(1-5), C2(4-6), Ca(1-2), Cb(3-4),
Cpar; gaps D1/D2→rail, D3:1-3, D4:4-2). The split resonator (ND9/10), the 12 Cems (ND11–22), and the island
(ND7/8) are **documented additions on the load side** (Block R / S5–S8) — they do not change the pump graph.
**The inherited pump energetics are on the correct graph.** (Not a genuine change → does not force
`SOLVER-INVALID`.)

## Stage B — geometry re-anchor (F3) — the museum-piece gate

`shuttle_core.galvanic_z()` = **1.2033** runs on the **stale device anchor** (160–1000 pF, Ca=Cb=100). The
machine's **actual galvanic z on the current geometry** (16–280 pF, Ca=Cb=309) is **1.334** — a +0.131 gap,
and it matches the freeze-doc "galvanic ceiling 1.334." So **every S5–S8 "Gate-0 pass" (z = 1.2033)
validated a geometry the machine no longer has.** *Crucially*, the **energetics already use 1.334** —
`energy_balance_from_solver` runs the solver at the current geometry — so the **downstream scalars are not
stale**; only the *gate* was. The Gate-0 anchor **re-bases 1.2033 → 1.334** so every future brief gates the
machine, not a museum piece.

## Stage C — rigorous diode solve (F2) — benign

F2 is real in the code: `solve_phase` checks OFF-diodes reverse-biased (lines 78–81) but **never enforces
ON-diodes carry forward current**, then picks `max(|v1|+|v4|)`. A rigorous LCP (enforce **both** ON-forward
*and* OFF-reverse → unique solution) was built and compared:

| geometry | heuristic z | rigorous LCP z | state-mismatches |
|---|---|---|---|
| device (stale) | 1.2033 | 1.2033 | **0** |
| current | 1.3340 | 1.3340 | **0** (0 multi-pass) |
| wide | 1.4379 | 1.4379 | **0** |

**The heuristic max-pick selects the unique physical branch on every geometry** — zero mismatches, and never
more than one state passes the full LCP. F2 is a theoretical hazard but **benign in practice**; not
`SOLVER-INVALID`. (Independently, the ngspice X0 deck recovers z = 1.2042 — the non-circular cross-check that
replaces the JS mirror.)

## Stage D — spark-gap switch physics (F6) — the load-bearing drift

The dominant **C-C equalization tax (0.614 of W_mech) is switch-independent** (thermodynamic — two caps at
ΔV lose ½·(C1C2/ΣC)·ΔV² however they're connected), and **V_bk only sets the absolute scale** (the S5
pinning), not the per-cycle tax *fraction*. What the spark gap **adds** is the **arc loss** `E_arc = V_arc ×
Q_cyc` (zero in the ideal-diode model). With the per-cycle commutation charge **8.23 µC** (current geometry,
20 kV rail):

| corner | V_arc | E_arc | DOUBLER_ETA | drop |
|---|---|---|---|---|
| opt | 20 V | 0.165 mJ | 0.386 → **0.376** | 2.7 % |
| **mid** | 35 V | 0.288 mJ | 0.386 → **0.368** | **4.7 %** |
| pess | 50 V | 0.411 mJ | 0.386 → **0.360** | 6.7 % |

**DOUBLER_ETA drops 0.386 → 0.368 (mid) — F6's prediction confirmed.** Propagated to the doubler-tax term of
the S8 hold floor: 5.87 → 6.05 W (**+0.17 W**). The scalar moves ~5 %, but the *absolute* floor change is
small (the arc is the only addition; the C-C tax was already correct), so **S5–S8's qualitative verdicts
stand**.

## Stage E — re-based scalar table + resonator drift

| scalar | inherited | recomputed | Δ | provenance |
|---|---|---|---|---|
| z (galvanic anchor) | 1.2033 | **1.3340** | **+10.9 %** | device → current geometry (F3) |
| DOUBLER_ETA | 0.3860 | **0.3679** | **−4.7 %** | ideal diode → spark gap, mid (F6) |
| USEFUL/fire | 6.153 mJ | **5.865 mJ** | **−4.7 %** | = η·W_mech (follows η) |
| W_mech/fire | 15.941 mJ | 15.941 mJ | 0 % | switch-independent (**HOLDS**) |
| W_coll/fire | 12.449 mJ | 12.449 mJ | 0 % | island, geometry-set (**HOLDS**) |
| Q_isl | 1.395 µC | 1.395 µC | 0 % | island pickup (**HOLDS**) |

**Resonator drift closed:** `resonator_sim`'s *default* `C_R = 960 pF (8 mm)` is the one known stale island —
the freeze is **789 pF (12 mm)**. All consumers (S2recheck → S8) already pass `C_R = 789` explicitly, so no
downstream number used 960; only the **default** is stale. Flagged for the new freeze (the frozen file is not
edited here).

## Verdict + roadmap

**`FOUNDATION-DRIFTS`** — three quantities move: the **z-anchor** (1.2033 → 1.334, a gate/validation fix —
the scalars never used the stale value), **DOUBLER_ETA** (0.386 → 0.368, the spark-gap arc loss), and
**USEFUL** (follows η). The foundation is **corrected, not invalidated**: F2 is benign (rigorous = heuristic),
the topology is a relabeling (pump core unchanged), W_mech/W_coll/Q_isl hold, and the propagated floor change
is ~0.2 W so S5–S8's qualitative verdicts (BALANCE-FAILS, SYNERGY-GENERIC, …) stand.

**Per the roadmap →** write **S8 r0.2** directly on the re-based scalars: **DOUBLER_ETA = 0.368** (mid; report
the opt/pess band), the **z-gate re-anchored to 1.334**, the **doubler unfrozen into the dynamics**, and the
resonator default closed to 789 pF. The graphic-novel apparatus numbers (the hold floor, the BALANCE margin)
update by the small spark-gap arc term; the headline verdicts are unchanged. This audit was the
highest-leverage check in the stack, and it found exactly the drift F6 predicted — better here than after
more building on it.

## Deliverables

`varcap.cir` v0.2 (committed SSOT with topology header) · `sim/audit_solver_foundation.py` (rigorous LCP +
spark-gap switch + ngspice/LCP cross-checks + the re-base; non-circular self-tests) · this findings doc ·
`audit_scalar_rebase.csv` (inherited vs recomputed, geometry/topology/switch stamped) · `audit_z_and_eta.png`
(current-geometry z vs the stale anchor; ideal vs spark-gap DOUBLER_ETA). Frozen empty-diff asserted. **Not
merged.**
