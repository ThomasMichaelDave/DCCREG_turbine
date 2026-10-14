# The rebuild — the doubler from its base schematic up

**Started:** 2026-10-14 on branch `claude/synthesis-phase1`.

**The designer's direction (2026-10-14):** "this paper's fig. 1 schematic is the new first schematic to create the
doubler from. We then develop the actual 3d models according to the known tube layout. Design it through, scrutinize
it, create it and test it. Basics first, with our lessons learned and context in the other repo's."

**The evidence:**
- the locked design (`09243c7`, `docs/ledger/DCCREG-design-ledger.md`);
- the Phase 1 synthesis (`synthesis/`);
- the repo's other branches (the designer, 2026-10-14: "I meant branches"), e.g. `claude/new-session-0az7f9`,
  `efficiency-resolution`, `commutator-real`.

The evidence is read, never edited. The rebuild writes only under `rebuild/`, and the frozen files stay
byte-identical (`CLAUDE.md`).

## The rule of addition

The designer (2026-10-14): "I will not even decide if the clamps are necessary. We will evaluate this instead of
injecting prior work before evidence exists to prove its necessity."

**So no part of the earlier design enters the rebuild by default.** That includes the clamps, the rings' supply, the
strays budget and the mounts. Each one enters only when a stage's evidence shows the bare circuit needs it, and the
designer then decides. The lessons below say where to look; they do not license an addition.

**Decisions so far** (the designer, 2026-10-14):
- the base schematic is de Queiroz Fig. 1 ("Schematic ok");
- the polarity is positive ("Positive is ok");
- the sixth Ca gap stands from earlier ("sixth Gap ok");
- ideal and real-diode records are both kept;
- there is no HV seed source.

## Stages

Each stage ships as script + results + findings and passes its gate before the next starts. What is DECIDED, PROPOSED
or OPEN at each gate is the designer's call.

| stage | what | gate | state |
|:--|:--|:--|:--|
| **S0** | **The base schematic:** de Queiroz Fig. 1, positive polarity, its topology, its ideal and ngspice records (`s0_base/`) | the ideal solver, ngspice and the paper agree | **frozen** |
| S1 | **The bare core at the tube's values:** C1 / C2 from the vane stacks, Ca / Cb; ideal and real-diode records. **The question it answers: what limits the bare core's voltage** (leakage, the diodes' reverse ratings, breakdown, a load), and so whether anything must be added. Strays enter as nodes when the S2 solves give them | z, the voltages and the charge balance close against S0's solver and ngspice; every addition proposed with its evidence | next |
| S2 | **The 3-D models to the known tube layout:** the vane stacks, the transfer capacitors, the sticks, the mounts; their field solves feed C(θ) and the strays back to S1 until z closes | S1 ↔ S2 converged; no clash; the clearances meet the air law | |
| S3 | **Scrutiny:** electrical integrity, conservation, mechanics, cost (the synthesis and scrutiny agents) | the conservation gate CLEAN or its concerns decided | |
| S4 | **Create:** the drawings, the parts list, the build sequence, all redrawn by script | the drawings match the models | |
| S5 | **Test:** the bench, starting with the designer's self-start experiment recorded as data | measured against S1's records | |

## Freeze

**S0 is frozen** (the designer, 2026-10-14: "Schematic ok"). The freeze commit is recorded below, and this check must
print 0:

`git diff 42747f4 -- rebuild/s0_base/ | wc -l`

- S0_FREEZE: `42747f4` (2026-10-14)

## Lessons learned the stages must carry

| # | lesson | where it bites | evidence |
|:--|:--|:--|:--|
| L1 | Strays set the as-built gain: z falls from 1.31 (bare) to 1.058 / 1.031 as built. The requirement is the node-total ratio (≥ ≈ 2.4 for z ≥ 1). Take strays from the models' field solves, as nodes, not as an assumed budget | S1, S2 | `synthesis/core-engine-spec.md` §2.2, §2.5 (N1) |
| L2 | κ differs between the 3-D solve (3.51) and the 2-D deck (7.47). Size from 3-D field solves only | S2 | `synthesis/tube-spec.md` |
| L3 | The ideal gain is not the efficiency. The diode doubler's transfers are lossless; the pump's power ends as heat in the clamps (the equalization principle, locked). The disc machine's η 0.386 / ≈ 0.50 does not apply | S1, S3 | `CONVENTIONS.md` working rule; `synthesis/synthesis-plan.md` |
| L4 | Self-start: the model needs a seed; the designer's four-diode build starts unaided, dry or humid, or with a rubbed PVC tube. Record the experiment as data; the bench arbitrates | S1, S5 | `synthesis/core-engine-spec.md` rec. 5 (N11) |
| L5 | A seed that excites only the decaying mode does not start in the ideal model | S1 | `sim/queiroz-matrix-findings.md` |
| L6 | Measurement loads the circuit: the paper's 82 pF probes dropped the predicted z from 1.372 to 1.154. The bench's dividers must be in the S1 model | S5 | `sim/queiroz-matrix-findings.md` finding 2 |
| L7 | The sixth Ca gap (495 pF, 1.1 C_max) is DECIDED; node 1 at both column ends | S1, S2 | `synthesis/tube-spec.md` A.8 (N2) |
| L8 | Ten electrical margins sit under 1.25, among them creepage, film, corona and the hot gel | S2, S3 | `synthesis/electrical-integrity-audit.md` (N3) |
| L9 | Mechanics: f2 (108–117 Hz) and a bearing frequency (108.3 Hz) sit under the pumps' 120 Hz; the frame was never checked (≈ 13 Hz) | S2, S3 | `synthesis/retainer-spec.md` (N6, N7) |
| L10 | Heat: the inner air runs +4.8–5.1 K against a +5 K limit | S3 | `synthesis/conservation-audit.md` |
| L11 | Every number needs a script; the synthesis left hand figures without one | all | `synthesis/synthesis-report.md` (N12) |
| L12 | The Phase 2 commutator needs a wiring interface stated from the start | S1 | `synthesis/synthesis-report.md` (N9) |
