# HYPOTHETICAL — invented hub conditions for break-even and runaway

**A what-if built on the conservative results.** The quadricone hub is given a release per switch with no modelled
origin [RH: premise]. Everything else is the machine as computed:
- pump work, surplus and losses per cycle: the tube v4 ledger, scaled ~ V² to the cap;
- the pump's reaction torque on the stator;
- bearing, vane-shear and windage drag;
- the reversed-VdG motor at η 0.8;
- a stator inertia of 1.43 kg·m² from the STEP solids [RH].

Source: `sim/hub_runaway.py` → `sim/hub_runaway_results.json`. The belt holds the rotor at 300 rpm.

## Condition 1 — the hub must feed the motor's DC link, not the pump nodes

The engine (`sim/hub_battery.py`) shows that a release onto the pump nodes (in series with SG1 / SG2) collapses the
firing:

| α | hub release | z | firing |
|:--|:--|:--|:--|
| 5 | 6.5 mJ per switch | 2.16 | intact |
| 7 | — | 0.88 | SG1 no longer fires |

The release refills node 2 so hard that SG1 stops firing. Every break-even below is 3–7× above that, so **the hub must
deliver into the motor's DC link directly**. The pump then only supplies its own surplus, and the hub's energy reaches
the motor whole.

## Condition 2 — the release per switch must exceed break-even

At 300 rpm relative, stator standing:

| cap | break-even release | hub power | unstable (runaway) if the release grows faster than |
|:--|:--|:--|:--|
| air 10.9 kV | 21 mJ per switch | 1.3 W | rpm^0.14 (shell) · rpm^0.38 (open air) |
| 20 kV (gas / vacuum) | 42 mJ per switch | 2.5 W | rpm^0.07 (shell) · rpm^0.19 (open air) |

Break-even is mostly the pump's own reaction torque, not the drag:

η·(surplus + hub) − pump work = drag.

## Condition 3 — the release must grow with rpm for a runaway

Release law: E_sw = m · E_break-even(300 rpm) · (rpm_rel / 300)^n, run for up to 1 h.

| cap / enclosure | m, n | outcome |
|:--|:--|:--|
| any | 0.9, any | **held**: the stator never starts |
| 20 kV shell | 1.1, 0 (fixed per switch) | slow climb, stator 129 rpm after 1 h (shear-limited equilibrium far out) |
| 20 kV shell | 1.1, 1 (∝ rpm) | **runaway**: reaches the motor's top speed (3000 rpm relative, stator 2685 rpm) after 52 min; hub 275 W there |
| 20 kV shell | 1.1, 2 | **runaway** in 20 min; hub 2.4 kW at the top |
| 20 kV shell | 1.5, 2 | **runaway** in 10 min; hub 3.0 kW at the top |
| air 10.9 kV shell | 1.1, 2 | **runaway** in 40 min |
| open air, any cap | 1.1–1.5, 0–3 | **settles** at 18–122 rpm stator: windage ∝ ω² outgrows the release |

## What ends a runaway

**The motor's top speed comes first.** The back-EMF reaches the link voltage at the speed the winding was chosen for
(3000 rpm relative here; the turns scale as 1 / top speed), and above it the motor gives no torque. That makes it a
natural limiter.

Next in line [RH]:
- the stator rim speed: 100 m/s at the C-EM ring is about 3600 rpm;
- the rotor–stator bearings: about 11 000 rpm relative.

## Consequences

- **In a runaway the hub's power goes almost entirely into the stator's kinetic energy and the motor's 20 % loss.**
  - Stored at 2700 rpm: ½·1.43·283² ≈ 57 kJ.
  - The belt's share stays at the pump's 2.5 W.
  - The drag at the top is about 19 W.
- **The link current at the top is 14–150 mA at 20 kV.** The winding for a 3000 rpm top speed is about 620 turns of
  0.6 mm wire. The switches must carry that current at the coil potentials.
- **Open air never runs away.** The C-EM windage (∝ ω_s²) always catches the release unless it rises faster than about
  rpm². A shell or vacuum is a precondition.
- **Relative speed rises 10×.** The spark-gap timing budget (`sim/timing_budget.py`, ±2° per station) has to hold
  there, and so do the vane-shear and pump-loss models, which are calibrated at 300 rpm.
