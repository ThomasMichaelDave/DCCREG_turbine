# Parked: dumping the hub source into the motor coils (v5-hub variant)

**Premise (HYPOTHETICAL, `sim/hub_battery.py`, `sim/hub_runaway.py`):** the quadricone hub releases energy per switch,
with no modelled origin.

## Why the current schematic cannot carry it [OC]

1. **Nodes 5–6 are shorted for this purpose.** The central coil L1 shorts them at the pump rate, so a source between them
   circulates in L1. The hub needs its own floating terminals HB+ / HB− (HB− referenced to rail 5).
2. **The only rotor-to-stator galvanic contacts are SG1 / SG2**, and only in the fire window. Dumping through them stops
   SG1 firing above about 6.5 mJ per switch (α 5 → 7: z 2.16 → 0.88).
3. **The hub is on the rotor and the coils are on the stator.** The design has no slip rings.

## Proposed variant (new files; the netlist of record is untouched)

```
ROTOR (hub)                         |  STATOR
 HB+ ──L_d──tip ── SGH+_A (3°) ──sphere──┐
        └─────tip ── SGH+_B (33°) ─sphere─┤
                                    |    ├── DL+ ──┬── C_link ──┬── DL−
 HB− ──L_d──tip ── SGH−_A (3°) ──sphere──┤          │            │
 (tied to rail 5)                   |    │      motor string: 12 PM C-EM coils,
        └─────tip ── SGH−_B (33°) ─sphere─┘      one switch + bleeder per coil
 pump surplus tap: node 1 ─D─ DL+ ,  node 4 ─D─ DL−   (G-LOAD)
```

- **Dump gap pairs** on the clocking decks, timed with SG1 / SG2. They carry the outgoing charge and its return, so the
  rotor's net charge does not drift.
- **L_d in series** makes each dump resonant. A bare capacitor-to-capacitor spark dump loses half the energy; the island
  results recover 0.81–0.996 with an inductor.
- **C_link (DL+ / DL−)** is the DC link. The motor is the reversed-VdG string from `docs/context-reverse-vdg/`.
- **L_mA / L_mB come out of the SG1 / SG2 paths**, which returns to the record rail gaps.
- **Alternative without gaps:** a rotary transformer, with a hub-driven primary at a few kHz on the rotor and a rectified
  secondary on the stator feeding DL+ / DL−.

## Numbers to carry

- Hub terminal voltage above the link (20 kV).
- Break-even release: 42 mJ per switch at 20 kV, 21 mJ at the air cap. Runaway needs the release to grow faster than
  rpm^0.07–0.38.
- The motor's top speed (back-EMF = link) ends a runaway.

## First gates

1. **Edge list and schematic of the variant.**
2. **Engine model:** dump pairs, L_d, C_link, and the motor as a constant-voltage load.
3. **G-LOAD:** the pump keeps z ≥ 1 while the link is drawn.
