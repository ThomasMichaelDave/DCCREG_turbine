# HYPOTHETICAL — the quadricone hub as an energy source ("battery"): downstream consequences

**A what-if, not a physics claim.** The hub is given an energy input whose origin is not modelled (the designer's premise).
The engine stays conservative: the source is its own ledger term, and belt + hub = growth + losses closes to ≤ 1.1e-14 J
on every row. Source: `sim/hub_battery.py` → `sim/hub_battery_results.json`. Tube v4 at 300 rpm relative and 20 kV
(strays fixed). [RH: premise; OC: everything downstream]

## The designer's spec, as modelled

1. **Timing.** The hub releases at each switch: SG1 on side A, SG2 on side B.
2. **Size.** The release grows with the pump: Δq = α·C_ii·V_i into the node it feeds, so it always adds energy
   (ΔE ≈ α·C_ii·V_i²). It starts at 10 kV. The engine is scale-free, so the threshold only enters the build-up timing.
3. **Where.** Into node 5 on A and node 6 on B.

## Finding 1 — between nodes 5 and 6 the release does nothing

- Nodes 5 and 6 are the two rotor halves. The central resonator coil joins them and is a near short at the pump rate
  (the L1-short argument in `CONVENTIONS.md`; the tank rings at 275 kHz against a 30 Hz pump).
- A source between 5 and 6 drives current round the central coil, not the pump. At α 0.1 the hub delivers 0.0000 W and
  z stays 1.6141.
- **For the hub to feed the pump, its release must close through a switch.** In the second variant it sits in series with
  the firing gap: rail 5 → node 2 through SG1 and the A C-EMs, rail 6 → node 3 through SG2 and the B C-EMs. All rows
  below use that variant.

## Finding 2 — a release that grows with the pump stays small at the operating voltage

| α | z | hub | belt | losses | surplus | 10 → 20 kV | C-EM ceiling | reversed-VdG torque |
|:--|:--|:--|:--|:--|:--|:--|:--|:--|
| 0 | 1.614 | 0 | 2.46 W | 1.15 W | 1.31 W | 0.05 s | 1.20 mN·m | 21–33 mN·m |
| 0.01 | 1.617 | 0.002 W | 2.46 W | 1.15 W | 1.31 W | 0.05 s | 1.18 mN·m | 21–33 mN·m |
| 0.1 | 1.643 | 0.016 W | 2.46 W | 1.16 W | 1.31 W | 0.05 s | 1.04 mN·m | 21–33 mN·m |
| 0.3 | 1.694 | 0.046 W | 2.45 W | 1.17 W | 1.32 W | 0.04 s | 0.80 mN·m | 21–34 mN·m |
| 1 | 1.827 | 0.137 W | 2.43 W | 1.20 W | 1.37 W | 0.04 s | 0.42 mN·m | 22–35 mN·m |
| 3 | 2.041 | 0.299 W | 2.41 W | 1.21 W | 1.50 W | 0.03 s | 0.14 mN·m | 24–38 mN·m |

Stator drag to beat: 19 mN·m in a shell or vacuum, 225 mN·m in open air.

- **The growth is real** (z 1.61 → 2.04), but it only shortens the build-up, which already takes 0.05 s. The pump is
  held at 20 kV by its limiter, so faster growth buys nothing in steady state.
- **The release scales as V², so at a fixed 20 kV it is a fixed, small power.** Even α 3, a release three times the
  node's own charge at every switch, gives 0.3 W.
- **Where that energy goes:**
  - 0.19 W reaches the surplus;
  - 0.06 W adds to the losses;
  - the rest displaces belt work (the belt draws 0.05 W less).
- **The as-built pulse C-EMs get worse.** The release refills node 2 / node 3 right after the switch, so less charge
  rings through the coils. The ceiling falls from 1.2 to 0.14 mN·m.
- **Correction:** the stator also carries the pump's reaction torque (78 mN·m at 20 kV), so no row here counter-rotates
  the stator; see `sim/spinup-findings.md`.
- **The reversed-VdG drive gains 3–5 mN·m.** It already closed in a shell without the hub. In open air it needs about
  14 W of surplus, roughly 50× what this release law gives at α 3.

## What would change the outcome (for the next what-if)

1. **A release that does not scale with the pump**, i.e. a fixed energy per switch. The surplus then rises one-for-one
   with the hub's power, less its share of the losses. Open air needs about 14 W of surplus: about 0.2 J per switch.
2. **A higher operating voltage.** The release ∝ V², so 40 kV gives 4×, but the HV clearances grow with it.
3. **A release in series with the coil groups rather than onto the node.** It would drive the C-EM current directly.
   That helps the pulse C-EMs only if the current is also held across the stroke (the freewheel limit stands).
