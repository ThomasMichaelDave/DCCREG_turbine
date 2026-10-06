# Context package — the reversed Van de Graaff–Trump generator as the stator drive (tube machine)

**Purpose.** This is a hand-off for a later work block. It takes US 2,945,141 (Van de Graaff & Trump, 1960,
"Unidirectional high-voltage generator") and runs it backwards inside the current tube machine. The patent turns shaft
rotation into HV DC through toothed-reluctance coils, one rectifier per coil, and a series stack. Reversed, the pump's
HV DC drives the same kind of coil stack, and the reaction torque counter-rotates the stator against the belt-driven
rotor.

**Status:** concept and first-pass budget only. Nothing in the pump, the engine or the tube geometry is changed by this
package.

## Read order

1. `01-patent-digest.md`: what the patent actually claims and builds, with element numbers.
2. `02-reversal-concept.md`: the reversal, mapped element by element onto the tube machine.
3. `03-budget.md`: the energy and torque budget, numbers from `sim/reverse_vdg_budget.py`.
4. `04-gates-and-open-forks.md`: what must be proven before any CAD, and the decisions left to the designer.
5. Background in the repo: `sim/tube-ledger-findings.md` (why the pulse-driven C-EMs fail),
   `sim/tube-shaft-findings.md` (r_u 130, bearings), `sim/motor-geometry-findings.md` (C-EM winding, swing).
6. `reference/US2945141.pdf`, `reference/US2945141-fig1.png`.

## The one-paragraph answer

The pulse-driven C-EMs fail because their current flows for tens of µs while the rotor barely moves. Almost none of the
coil energy becomes work. The reversed patent fixes the **conversion**:
- it is a back-EMF machine: a toothed rotor and PM-biased C-cores make each coil's EMF proportional to speed;
- a series string of 12 coils is wound so its summed back-EMF equals the 20 kV link;
- the link then delivers its surplus as V × I at 66–88 µA, with milliwatts of copper loss.

It does **not** change the ledger. The motor can only spend what the belt put into the pump: 1.3–1.8 W at 20 kV and
300 rpm relative. That gives 21–45 mN·m against an estimated 19 mN·m of stator drag in a shell or vacuum, and 225 mN·m
in open air.

> **Correction (2026-10-06, `sim/spinup-findings.md`):** the stator also carries the pump's own reaction torque
> (78 mN·m at 20 kV), which always exceeds the motor's. The drive does **not** close in any enclosure without an
> outside source. The paragraph below is the superseded first pass.

So the drive closes on paper **only** with windage removed, uses the pump's entire surplus, and costs the belt 2–4×
more than a reversing gear would.

## Guardrails for the work block

1. **Producer/consumer, as in Block C-I.** The motor is a *load* on the pump. Model it in `rt_engine` as a load on the
   DC link; do not touch `solveDoubler4`, the frozen cores or the frozen files (the empty-diff list in `CLAUDE.md` /
   the session rules).
2. **The ledger is the referee.** Every motor number traces to `sim/tube_ledger.py` (belt in = growth + losses, closure
   ≤ 1e-12 J). The motor power can never exceed the pump's surplus at the operating voltage.
3. **Fail-closed gates first** (`04-gates-and-open-forks.md`): G-LOAD (the pump holds 20 kV while loaded) before any
   winding or CAD work.
4. **Tags:** `[OC]` standard physics, `[IR]` a design identification for this machine, `[RH]` heuristic or estimate.
5. **Units and names:** mm, kV, mN·m; the existing tube names (`r_u`, `REL_*`, `CEM_PROFILE`, `TUBE_DEFAULTS`).
6. **Commits:** conventional, small; findings go to `sim/*-findings.md`, the changelog gets one entry per step.
