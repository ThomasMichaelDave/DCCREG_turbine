# System Documentation — Circuit Topology, Multiple Resonances & Materials

**Scope:** the machine as a whole — the full circuit topology, the three coexisting frequency regimes and the resonant circuits living in them, how those resonances relate to each other and to RPM, the start-up and equilibrium behaviour, and the materials and their effects. This is the integrating document that the per-block briefs (C-I, M, R, D) plug into.

**Companion docs:** `brief-blockM-rotor-mechanical-core.md` (mechanical core), `brief-blockR-central-resonator.md` (central LC tank), `brief-blockD-distributed-electromagnets.md` (spin-up motor). Cross-references below use those block letters.

---

## Revision history

| Version | Date | Summary |
|---|---|---|
| v0.1 | 2026-06-05 | Initial system doc. 6-node topology + two-spinning-unit architecture; three-frequency map; the central f0 tank and the per-coil C-EM resonance and their RPM relationship; impedance hierarchy; start-up bootstrap and the two thresholds; materials section (iron rotor, laminated cores, copper, mica, HV caps). |

---

## Tier legend

- **[OC]** Operational Core — standard physics/EE.
- **[IR]** Interpretive Reading — a design choice within this machine.
- **[RH]** Rhetorical/Heuristic — framing, not load-bearing.

---

## 1. Circuit topology

### 1.1 Two self-contained spinning units, coupled only by capacitance

The machine is two independently rotating assemblies:

- **Rotor unit** — belt-driven (the prime mover). Carries the rotor electrode halves (nodes **5–6**), the central resonator coil, and the solid-iron quadricone poles. Self-contained: its internal wiring closes on itself.
- **Stator unit** — free-spinning, counter-rotating. Carries the stator electrode halves and pump nodes **1–4**, and the 12 C-EM coils. Also self-contained.

They share **no galvanic connection**. All energy crosses the gap **capacitively, through the variable capacitors** (the varicaps). Because the coupling is capacitive, **neither unit needs slip rings** — this is the architectural keystone. The commutation that a brushed/slip-ring machine would need is instead **integrated into the charge pump**: the varicaps reach C_max/C_min at rotor-angle-defined instants, which is what times the charge transfers. [IR]

### 1.2 The 6-node netlist

```
 Ca : 1–2     fixed transfer cap        (= "C3" in the C-EM brief)
 Cb : 3–4     fixed transfer cap        (= "C4" in the C-EM brief)
 C1 : 1–5     variable cap (varicap)    rotor-coupling
 C2 : 4–6     variable cap (varicap)    rotor-coupling
 D3 : 1–3     cross-couple diode (or SG3)
 D4 : 4–2     cross-couple diode (or SG4)
 D1 : 2–5     diode (or SG1)
 D2 : 3–6     diode (or SG2)
 L1 : 5–6     central resonator coil, with C_R (through-mica inter-electrode cap) implicit
 C-EMs        : 6 across Ca, 6 across Cb (Block D), each via its resonant DC-block cap
```

- Nodes **1, 4** are the outer varicap plates — the large HV swing, `|V1|+|V4|`. [OC]
- Nodes **5, 6** are the rotor electrodes — the resonator terminals. [OC]
- **Diode vs spark-gap:** build the **diode** version first (deterministic, self-starts from ambient seed). The spark-gap version (SG1–4, threshold-fired) is deferred — it needs a timing-diagram switch simulation. [IR]

### 1.3 The pump-rate short that keeps the doubler math valid

At the pump rate (~hundreds of Hz) the central coil L1 is a fraction of an ohm — effectively a short across 5–6, merging them into the common rail the original `solveDoubler4` gain analysis assumes. **The doubler gain math therefore stays valid as written;** the resonator is a high-frequency layer riding *on top* at f0 (§2). This is why the central coil is deliberately the **low-L** element of the machine. [OC/IR]

---

## 2. Three frequency regimes — the map

Every impedance statement in this machine is meaningless without naming its frequency, because the same coil looks utterly different at each. There are three regimes, separated by ~1000× each step:

| Regime | Typical value | Origin | What lives here |
|---|---|---|---|
| **Mechanical / PRF** | ~150–450 Hz | rotation: `PRF = 6·RPM/60` | charge pumping; C-EM motor torque |
| **C-EM resonance** | = drive freq (PRF or PRF/2) | `L_coil` + `C_block` series | motor torque tuning + DC block |
| **Central f0 tank** | ~238 kHz | `L1` ∥ `C_R` | the HV "ring" |

The mechanical/PRF regime and the f0 regime are ~1000× apart. The pump kicks the tank a few hundred times per second; between kicks the tank rings at ~238 kHz and decays. They do not interfere precisely because of that separation. [OC]

> **f0 note.** With the motor coils properly isolated (high-L, real spectators at f0), they do **not** load the central tank, so f0 stays at the central-coil-alone value **≈ 238 kHz** (L1 ≈ 235 µH with C_R ≈ 1.9 nF). The earlier "≈ 290 kHz" figure assumed the EM coils sat *inside* the tank (~430 µH parallel) — that loaded case is **superseded**, because steel-cored coils carrying 238 kHz current would be skin-dead and lossy and would wreck the tank Q (§5). Isolation is the deliberate choice; 238 kHz is the resulting f0. [OC/IR]

---

## 3. The multiple resonant circuits and how they relate

### 3.1 Resonance A — the central tank (the "ring"), RPM-independent

```
f0 = 1 / (2π·√(L1·C_R)) ≈ 238 kHz
L1 = central resonator coil (Block R), ~235 µH  (LOW-L element)
C_R = through-mica inter-electrode capacitance, ~1.9 nF
```

`f0` is set purely by L and C — **it does not move with RPM.** What RPM changes is the *amplitude* of the ring (more PRF kicks/sec at higher HV → bigger ring), not its frequency. Tunable only by the coil (turns/wire/cone size) and the disc cap (area, mica εr, thickness). [OC]

### 3.2 Resonance B — the C-EM coupling LC (torque tuning), RPM-tracking

```
f_res(C-EM) = 1 / (2π·√(L_coil·C_block))
            = the coil drive fundamental (PRF or PRF/2 — Block D §4.4)
```

This one is **designed to track the drive**, i.e. to sit at the operating PRF (or PRF/2). Since `PRF = 6·RPM/60`, the *match* between this LC and its drive only lands at the **design RPM**. The cap (user target 440 nF/20 kV) forces `L_coil ≈ 0.64 H` at 300 Hz (or 2.56 H at 150 Hz) — the "many windings" coil. [OC/IR]

### 3.3 How A and B stay out of each other's way — the impedance hierarchy

The two resonances coexist on the same nodes without fighting because of how each coil's impedance lands in each regime:

| Element | Z @ PRF (~300 Hz) | Z @ f0 (~238 kHz) | Role |
|---|---|---|---|
| Central coil L1 (~235 µH) | ~0.44 Ω — near-short | ~350 Ω — tank reactance | the resonator inductor; PRF short keeps doubler math valid |
| C-EM coil (~0.64 H) + C_block | ~R_coil at resonance — carries torque current | ~kΩ–10s kΩ — spectator | motor; resonant at PRF, invisible at f0 |
| C-EM block cap (440 nF) | resonates with coil | inductive branch above resonance → high-Z | DC block + torque tuning + f0 isolation in one part |

The separation is structural: the motor coils are sized for a useful Z at the **PRF** (torque), which — because f0 is ~1000× higher — automatically makes them ~1000× higher-Z at f0, i.e. spectators that neither shift f0 nor drain the ring. Conversely the central coil is the low-L element: a short at PRF (good for the pump), the reactance at f0 (good for the ring). [OC]

### 3.4 The voltage-magnification coupling (the one real cross-talk)

The C-EM resonance is series-resonant, so it magnifies the **cap** voltage by Q:

```
V_cap,peak = V_bias + Q·V_ripple ≤ V_rating   (Block D §4)
I_circ     = Q·I_input                         (current gain — the point of resonance)
```

This couples the **doubler output voltage** (which sets `V_bias` across the block cap) to the **motor cap rating**: the higher the doubler runs, the less AC headroom the 20 kV cap has, and the smaller the allowable ripple and torque. The torque-limiting ampere-turns reduce to a clean closed form (Block D §4.3):

```
N·I_circ,max = (V_rating − V_bias)·√(C_block·l_gap/(μ0·A_gap))
```

— independent of frequency and turns. So the real system trade is **doubler voltage vs spin-up torque**, mediated by the motor cap rating. Run the doubler well below the cap rating, or rate the caps above the doubler voltage. [OC/IR]

---

## 4. RPM dependence and the operating regimes

### 4.1 What scales with RPM and what doesn't

- **PRF = 6·RPM/60** — scales linearly. Sets the pump throughput, the motor commutation rate, and the C-EM drive frequency. [OC]
- **f0 (central tank)** — fixed by LC, **independent of RPM**. RPM changes ring *amplitude*, not frequency. [OC]
- **C-EM resonance match** — lands only at the design RPM (its LC is fixed, its drive tracks RPM), so **torque peaks at the design RPM and falls off either side.** This is a *feature*: it makes the machine tend to self-lock at the design speed, but it means weaker torque during low-RPM spin-up, which the belt must carry through. [OC/IR]

### 4.2 Start-up bootstrap (the chain)

1. Belt spins the rotor; stator starts at rest → relative speed = rotor speed.
2. Climb to **rpm_min** — the speed at which pump gain per stroke beats leakage/loss per stroke (set by leakage τ vs modulation period). Below it, charge bleeds off faster than it's pumped and nothing builds. [OC]
3. **Seed the pump.** A spark-gap doubler cannot self-start from zero (with Q=0, voltage never reaches any gap threshold). Inject a seed charge at the **C_max** rotor position, so the following rotation toward C_min drives `V = Q/C` up into the first gap's threshold on the first stroke. The **diode** version self-starts from ambient seed (contact potential / triboelectric) + modulation gain — a real start-up advantage. [OC]
4. HV builds → nodes 1–4 swing → C-EMs driven → stator counter-rotates → relative speed and PRF climb → bigger kicks into the f0 tank.
5. **rpm_crit** is *not* where the tank "starts" to ring (it rings at f0 whenever kicked, at any RPM) — it is where the C-EM resonance match, the ring amplitude, and the counter-rotation torque all reach the level that balances stator drag. That balance point is the equilibrium. [IR]

### 4.3 Equilibrium and energy flow

At equilibrium the chain is: belt → rotor (mechanical) → reacts through the C-EM/iron coupling to counter-rotate the stator → raises relative speed → raises PRF → pumps the f0 tank harder. The "optimal transfer" knob is matching the motor's PRF-regime branch impedance to the stator's mechanical load line, so torque peaks near rpm_crit and then backs off to merely trimming drag. That impedance/load match (motor `L_coil`, `Q`, and the ampere-turn limit vs stator inertia + drag) is the next quantitative piece to derive, and it couples to the deferred flywheel/inertia block. [IR]

---

## 5. Materials and their effects

Material choice is dominated by **which frequency each part sees**, because eddy-current and skin effects scale steeply with frequency.

### 5.1 Rotor quadricones — solid iron is acceptable

The rotor poles only ever see the **mechanical/PRF** field variation (hundreds of Hz) and act as a **passive reluctance** rotor (no windings, no f0 current). Eddy loss and skin effect at a few hundred Hz are modest, so **solid iron is acceptable** — a major simplification (easy to machine, structurally strong, doubles as the shaft-coupling hub mass). If start-up torque ripple or rotor heating turns out significant, axial lamination is the fallback, but it is not required by the frequency alone. Use a high-permeability, high-saturation soft magnetic iron (e.g. low-carbon steel) so the reluctance contrast (salient pole vs gap) is large → steeper `dL/dθ` → more torque. [OC]

### 5.2 C-EM cores — must be laminated (or ferrite)

The C-EM cores carry the **motor commutation** flux at the PRF and, critically, must **not** carry f0. Two effects:

- **Eddy loss ∝ f²** in a conductive core → at the PRF (hundreds of Hz) a **laminated silicon-steel** core keeps loss acceptable; solid steel would already be lossy and would dissipate the motor drive. [OC]
- **Skin/penetration at f0:** at ~238 kHz the skin depth in steel is ~tens of µm, so the core is **skin-dead** — it cannot carry the field through its bulk and is purely lossy at f0. This is *why* the motor coils must be isolated from the f0 tank (high-L, §3.3): you never want 238 kHz flux in a steel core. [OC]

Use **laminated silicon steel** for the working PRF flux (thin laminations, grain-oriented if the flux path allows). If the commutation frequency is ever pushed high, **ferrite** (an insulator, negligible eddy loss) becomes the better core, at the cost of lower saturation. The coil's own high inductance also **self-filters**: it is high-Z at f0, so even residual f0 coupling drives little current into the core. [OC]

> **Open-core caveat.** A C-magnet with a working air gap is demagnetisation-limited: the effective permeability seen by the coil is set by the **gap**, not the iron's μ_r (apparent μ of order a few for an open path). Inductance is therefore **gap-dominated** — `L ≈ μ0·N²·A_gap/l_gap` — which is exactly the relation used in the Block-D turns budget. The iron mainly provides the low-reluctance return and the saturation ceiling, not the bulk of L. [OC]

### 5.3 Copper windings — skin depth and the many-turns/low-current choice

- At the PRF the copper skin depth is large (mm-scale), so solid fine wire is fully utilised — no need for litz at the drive frequency. [OC]
- The **central resonator coil** is the exception: it runs at f0 (~238 kHz), where the copper skin depth is ~134 µm. There the earlier finding holds — a **capillary tube behaves like a solid rod** at f0 (current rides the outer ~skin-depth shell either way), giving the same L/C/f0/Q with ~11 % less copper. [OC]
- The C-EM windings follow the **many-turns / low-current** strategy: the available pump current is small, so torque (∝ ampere-turns) is recovered by raising N rather than I. High N also delivers the high `L_coil` needed for f0 isolation. The cost is winding resistance (sets Q and copper loss) and a self-resonant frequency that must stay well above f0 (Block D §9). [OC/IR]

### 5.4 Mica dielectric (the C_R cap and the structural septum)

The central disc is mica: it is the **structural septum** carrying the aligned electrode on each face **and** the dielectric of the inter-electrode cap `C_R = ε0·εr·A_align/discThk`. Mica is chosen for high dielectric strength, low loss (high tank Q), thermal stability, and mechanical rigidity (it is also a load-bearing rotor part). `εr ≈ 5.4`; thickness and aligned area are the two `C_R` tuning knobs feeding f0. Low dielectric loss is what lets the f0 ring keep a high Q. [OC]

### 5.5 HV blocking / resonant caps — film, energy, safety

The Block-D series caps (440 nF / 20 kV target) should be **HV film** (low loss, stable, self-healing types preferred). Two material-driven realities:

- **Voltage rating must cover the resonant magnification, not just the bias:** `V_cap,peak = V_bias + Q·V_ripple` (Block D §4). The 20 kV rating exists to absorb the Q-magnified AC on top of the blocked DC bias.
- **Stored energy is large and lethal:** `½·C·V² = 88 J` per cap at 20 kV; twelve of them ≈ **1.06 kJ** on the spinning stator. This drives the per-coil-vs-per-group decision and mandates an interlock/bleed/safety regime (a dedicated HV-safety block is an open deliverable). [OC]

### 5.6 Material → frequency summary

| Part | Frequency seen | Material | Why |
|---|---|---|---|
| Rotor quadricones | PRF (mechanical) | solid soft iron | low loss at hundreds of Hz; reluctance contrast; structural |
| C-EM cores | PRF; must reject f0 | laminated Si-steel (ferrite if HF) | eddy ∝ f²; skin-dead at f0 → isolate |
| C-EM windings | PRF | solid fine Cu, many turns | large skin depth at PRF; many-turns/low-current |
| Central coil | f0 (~238 kHz) | Cu — tube ≈ solid rod | skin depth 134 µm; save copper |
| Disc / C_R | f0 + structural | mica | dielectric strength, low loss (Q), rigidity |
| Block / resonant caps | PRF, HV | HV film | low loss; rated for V_bias + Q·V_ripple |

---

## 6. Open system-level questions

1. **Drive-frequency mapping** (PRF vs PRF/2) — pins L_coil and N (Block D §4.4).
2. **Doubler-voltage vs spin-up-torque** trade via the motor cap rating (§3.4) — choose the operating bias.
3. **Motor-impedance ↔ stator-load match** at rpm_crit (§4.3) — couples to the flywheel/inertia block.
4. **Real tank Q** — dielectric + spark-gap + core residual losses, vs the copper-only optimistic Q from Block R.
5. **HV safety block** — interlock, bleed, energy containment for ~1 kJ of HV storage on a rotating assembly.
6. **Spark-gap timing simulation** — for the deferred SG version of the pump and seed injection.

---

*Status: integrating system documentation, v0.1. The per-block briefs (C-I, M, R, D) remain authoritative for their own internals; this document is authoritative for how they couple in topology, frequency, and material.*
