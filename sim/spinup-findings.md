# Stator counter-rotation: the balance with the pump's own reaction torque, breakdown caps and rpm feedback

Source: `sim/spinup_equilibrium.py` → `sim/spinup_equilibrium_results.json`. Inputs: `tube_ledger_results.json` (drag) and
`hub_battery_results.json` (the HYPOTHETICAL hub source). Tube v4, reversed-VdG motor at η 0.5–0.8.

## Correction to the earlier balances [OC]

The pump's work per cycle W comes out of the rotor–stator relative motion, so its electrostatic drag acts on the stator
too:

T_pump = W · 6 / 2π = **78 mN·m at 20 kV**.

The earlier stator balances (`tube-ledger-findings.md` §2, `docs/context-reverse-vdg/03-budget.md`) compared the motor
against bearing, shear and windage drag only. With T_pump included:
- The motor runs on the pump's surplus E_s, and E_s < W. So T_motor = η·E_s·6/2π is **always smaller than T_pump**.
- Without an outside source the stator is pulled along *with* the rotor, whatever the motor.
- This does not depend on the motor technology. It is the same relative motion paying for both.

## Net torque on a standing stator (300 rpm relative; + would counter-rotate)

| cap | hub α | motor | pump reaction | net |
|:--|:--|:--|:--|:--|
| air, 3 mm (10.9 kV) | 0 | 6–10 mN·m | 23 mN·m | −33 to −36 mN·m |
| 20 kV | 0 | 21–33 mN·m | 78 mN·m | −64 to −77 mN·m |
| SF6-class 30 kV | 0 | 47–75 mN·m | 176 mN·m | −120 to −149 mN·m |
| 20 kV | 3 (0.30 W hub) | 24–38 mN·m | 77 mN·m | −58 to −72 mN·m |

## The breakdown cap is already at 10.9 kV in air

The C1 vane gap (R-A to node 1) carries the full 20 kV peak; C2 carries 15.7 kV. A uniform 3 mm air gap breaks down at
about **10.9 kV**, and vane edges lower that. So the tube's 20 kV operating point needs one of:
- a gas fill (SF6-class, about 30 kV at 3 mm, 1 atm);
- vacuum below 1e-4 mbar;
- a wider gap.

In plain air it caps near 10.9 kV, and every per-cycle energy scales by (10.9 / 20)² = 0.30.

## rpm feedback: power rises, torque does not

Every energy in the ledger is per cycle and does not depend on speed:
- pump work, surplus and losses;
- the hub release, at the cap.

So motor torque and pump reaction are both constant in rpm, while shear (∝ ω) and windage (∝ ω²) rise. The feedback
loop has a **stable** fixed point, not a runaway:
- with a hub above break-even, the stator settles where the extra drag catches up;
- below break-even it is dragged along.

Break-even hub release (η 0.8, symmetric split):

| cap | enclosure | 300 rpm rel | 600 | 1200 | 2400 |
|:--|:--|:--|:--|:--|:--|
| air 10.9 kV | shell / vacuum | 21 mJ/switch (1.3 W) | 24 (2.9 W) | 30 (7.3 W) | 42 (20 W) |
| 20 kV | shell / vacuum | 42 mJ/switch (2.5 W) | 45 (5.4 W) | 51 (12 W) | 63 (30 W) |
| 20 kV | open air | 171 mJ/switch (10 W) | 562 (67 W) | 2120 (509 W) | 8340 (4.0 kW) |

The hub as specified (release ∝ the pump's voltage, so fixed per switch at the cap) gives 1.5 mJ per switch at the air
cap and 5 mJ at 20 kV with α 3. That is 8–14× short of break-even in a shell.

**A runaway (true positive feedback) would need a hub release per switch that rises with rpm faster than the
break-even column.** In a shell that column is gentle (21 → 42 mJ from 300 to 2400 rpm), so a release growing even
∝ √rpm would cross it. In open air the ω² windage makes it steep. This is the one premise that decides the
what-if. [RH]
