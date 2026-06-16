# The resonator as a pressure machine — a hydraulic lens for the varcap tank

> **Status:** engineering intuition / modelling lens. **Firewall:** this is the standard
> electromechanical (hydraulic) analogy used as a design aid for the varcap-machine. It is **not**
> a claim about the nature of electricity, and it is **not** DCCREG substrate ontology — it stays
> on the engineering side of the wall. Tags: **[OC]** standard physics · **[IR]** interpretive lens.

## Why this lens

The varcap resonator behaves in ways that are far more intuitive if read as a **hydraulic pressure
system** than as an abstract LC circuit. The mapping below is the textbook electromechanical
analogy — rigorous enough to be an equivalent-circuit method, intuitive enough to guide design
decisions about the tank, the clamp, and the energy budget. **[IR]**

## The correspondence **[OC]**

| Electrical | Hydraulic | In this machine |
|---|---|---|
| Voltage V | Pressure (head) | tank "pressure" |
| Charge Q | Fluid volume | stored charge |
| Current I | Flow rate | ring current |
| Capacitance C_R | Compliance — a springy accumulator (volume per unit pressure) | the tank chamber |
| Inductance L_R | Inertance — inertia of a moving fluid slug | the coil |
| Resistance R | Pipe friction | tank loss |

## The resonator is a hydraulic pressure oscillator **[OC]**

An LC tank ringing at f₀ maps exactly onto fluid sloshing between a **compliance** (the springy
accumulator C_R, which pushes back as it fills) and an **inertance** (the heavy fluid slug L_R,
which resists changes in flow and overshoots). Fill the accumulator → pressure rises → drives flow
through the inertance → overshoots equilibrium → reverses → oscillates. This is water-hammer
ringing, a sloshing U-tube, a Helmholtz resonator. The machine's f₀ (~579 kHz at the current
geometry) is the slosh frequency.

## Q is the seal quality of the pressure vessel **[OC]**

The clearest single mapping: **Q is how well the vessel holds pressure between disturbances** — the
inverse leak rate. The energy time constant **τ_E = Q/ω₀** is literally the pressure-decay time:

- **High Q** = a well-sealed accumulator that holds charge long (slow leak).
- **Low Q** = a leaky vessel bleeding pressure to friction fast.

The coil's copper resistance is the porosity of the vessel wall. This is why a low-Q tank is one you
*tolerate* (the first-kick reach barely cares — see below) but never *want* (it wastes pump work as
heat and the high voltage doesn't dwell).

## Energy injection = pump strokes; accumulation = charging the vessel **[OC]**

Each spark fire is a **discrete pump stroke**: the island (a small pre-pressurised cylinder) dumps
its charge-volume into the big tank — a water-hammer pulse that raises tank pressure. Whether the
tank *builds up* over many strokes is the **classic pressure-vessel charging problem** — stroke rate
vs leak rate:

- **Strokes slower than the leak** (kick spacing ≫ τ_E): each stroke bleeds away before the next →
  no build-up, the vessel sits at single-stroke pressure. *(This machine at 3000 rpm.)*
- **Strokes faster than the leak** (kick spacing ≲ τ_E): pressure compounds toward a higher steady
  state. *(Approached only at high RPM and/or high Q.)*

Exactly how a compressor charges an air receiver: pressure rises until per-stroke addition equals
inter-stroke leak-down. **Q and PRF together set the equilibrium pressure.**

## Battery vs pressure vessel — and where this machine sits **[IR]**

- A **battery** is a pressure *source* — constant head as volume is withdrawn (mains-pressure
  supply). Draw current, voltage barely sags.
- A **capacitor / tank** is a pressure *store* — pressure *falls* as charge is withdrawn (a sealed
  rigid vessel emptying). ½CV² is the energy in the pressurised vessel.
- **This machine is a pump.** The rotor converts shaft work into electrostatic pressure, charging
  the store: the plates *attract*, and pulling them apart against that attraction is the pumping
  stroke, depositing energy into the tank. The right model is **pump + accumulator**, not battery.
- The **clamp** is what adds battery-like behaviour at the terminal: the glow governor holds the
  tank at a constant 15 kV ceiling by bleeding excess — a **pressure-relief valve / regulator** that
  turns a rising-pressure store into a pressure-*regulated* output.

## The literal core: Maxwell stress is a real pressure **[OC]**

This is where it stops being analogy. The field energy density ½εE² **is** a mechanical stress (the
Maxwell stress). For the tank at 15 kV across the 8 mm garolite C_R gap:

- E = 15 kV / 8 mm ≈ 1.9 MV/m
- field pressure = ½ε₀εr·E² ≈ **73 Pa**, pulling the rotor faces together with ~13 N.

The "pressure" in the tank is a genuine force on the plates. The stored energy is elastic energy in
a stressed field — a compressed spring, not a metaphor.

## The key refinement: density is small, but energy and power are not **[OC]**

"The pressure is small" describes only **energy density** (~73 Pa = 73 J/m³, capped near ~MJ/m³ even
at breakdown — far below hydraulics or chemistry). What a *dissipating element* experiences is
**total energy** and **power**, which decouple from density through two multipliers:

- **Total energy = density × volume.** Small density × large capacitance (big plates, or an added
  reservoir, or accumulation) → real joules. The same field pressure in a 1 µF bank holds ~110 J.
- **Power = energy ÷ time, and electrostatic release is fast.** No fluid dumps its energy in 10 ns;
  a charged field can. Even modest stored energy becomes enormous power on release.

| Dissipator | Energy | Release | Power felt |
|---|---|---|---|
| spark electrode, per pulse | ~20 mJ | 10 ns | **~2 MW** peak |
| tank shorted (fault) | 108 mJ | ~0.6 µs | ~170 kW |
| 100 nF reservoir into a fault | 11 J | ~1 µs | **~11 MW** |
| electrode, time-averaged @ 2 kHz | 108 mJ × 2000 | continuous | ~216 W thermal |

So the honest framing: **energy-sparse but power-dense — a power machine, not a storage machine.**
"Low pressure" means low *force*, not low *consequence*. Capacitive systems are the inverse of a
battery: little energy, but deliverable at megawatt power. That inversion is the whole reason to
build a pulsed machine — accumulate slowly at low pressure, release fast at high power.

## The dam analogy, and why accumulation matters **[IR]**

A dam holds a "modest" head (a few atm) — nobody fears the pressure. But the accumulated volume ×
that modest head = gigajoules, and a fast release (burst, water hammer) is catastrophic. Low
pressure, huge energy, violent release — *because of accumulation and release rate, not pressure*.
Accumulating charge over run-time (a reservoir integrating many pump strokes) grows energy linearly
with time × PRF, reaching the destructive range while the field pressure inside never exceeds the
same "small" 73 Pa.

## Safety corollary **[OC]**

The hazard scales with **stored energy × discharge speed, not voltage.** 15 kV is a shock; 15 kV
with accumulated stored energy is potentially lethal (energy above ~10 J across the heart can stop
it; a charged reservoir reaches that easily). Practical consequences for the build: bleed-down
resistors across every storage element; short-to-ground before touching anything; treat the tank and
any reservoir as charged-and-dangerous after shutdown — a capacitor holds its charge silently. The
same property that makes it a useful power source makes it a serious hazard.

## What the lens tells the designer

- **Tank "pressure rating"** = breakdown voltage (the vessel bursts at 15–20 kV — the 7 mm/Paschen
  hold-off logic).
- **Leak rate** = Q (why low Q is tolerable for reach but wasteful — it heats the coil).
- **Charge-sharing loss** = throttling turbulence when a small high-pressure cylinder dumps into a
  big low-pressure tank → why matching Cx to C_R (equal-size vessels) transfers energy efficiently.
- **The clamp** = a relief valve / regulator — the device a pressure-vessel engineer reaches for.

**One-line model:** a reciprocating electrostatic pump (the rotor) charging a sealed resonant
accumulator (the tank), whose pressure builds per stroke-vs-leak (PRF vs Q), regulated to a constant
terminal pressure by a relief valve (the clamp) — at small absolute pressure but high release power.
Design it as a *power-dynamics* machine, not a *stored-energy* one.
