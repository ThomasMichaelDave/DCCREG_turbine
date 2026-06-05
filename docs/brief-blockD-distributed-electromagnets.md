# Brief — Block D: Distributed Electromagnets (Reluctance Spin-Up Motor)

**Target:** `index.html` calculator (new parallel producer block).
**Companion docs:** `brief-blockM-rotor-mechanical-core.md`, `brief-blockR-central-resonator.md`, `doc-circuit-topology-resonances-materials.md` (read that one for the system-level frequency/RPM picture this block plugs into).
**Producer/consumer rule:** Block D is a **parallel producer**. It reads geometry/electrical context but **never** feeds `solveDoubler4`. The validated solver is untouched.

---

## Revision history

| Version | Date | Summary |
|---|---|---|
| v0.1 | 2026-06-05 | Initial brief. Iron-rotor reluctance machine; 12 stator C-EMs in two interleaved groups on the transfer caps; uniform winding; series resonant DC-block/coupling cap; Q/turns/voltage budget with the closed-form ampere-turn limit; calculator I/O, self-tests, cross-section additions. |

---

## Tier legend

- **[OC]** Operational Core — standard physics/EE; true independent of this design.
- **[IR]** Interpretive Reading — a design identification chosen within this machine.
- **[RH]** Rhetorical/Heuristic — suggestive framing, not load-bearing.

---

## 0. Locked decisions (inputs to this block)

These were settled in discussion and are treated as given here:

1. **Solid-iron rotor quadricones — passive reluctance rotor.** No rotor windings, no magnets, no rotor electrical feed. [IR]
2. **Only the stator C-EMs are powered.** The 12 C-shaped electromagnets are the sole active windings. [IR]
3. **Two interleaved groups of 6**, each group bridging one transfer cap (C3 across nodes 1–2, C4 across nodes 3–4). The two transfer caps swing **antiphase** (push-pull doubler). [OC for push-pull; IR for the assignment]
4. **Uniform winding.** All 12 coils wound the same sense; the N-S-N-S spatial pattern falls out of the antiphase grouping, not from per-coil reversal. [OC]
5. **Series resonant DC-block cap** in line with each coil (or each group): user target **440 nF / 20 kV**. [IR]
6. Stator is a self-contained spinning unit (nodes 1–4 + plates + C-EMs); rotor is a separate spinning unit (5–6 + electrodes + central coil). They couple **capacitively only** through the varicaps — **no slip rings either side**. [IR]

---

## 1. The reluctance-motor model

Torque on a salient iron rotor pole from an energized stator coil:

```
T = ½ · i² · dL/dθ        [OC]
```

Consequences that shape this block:

- **Torque ∝ i² → polarity-blind.** N-vs-S does not set torque direction; the iron is pulled toward whichever poles are energized, regardless of field sign. [OC]
- **Polarity sets flux efficiency, not direction.** With adjacent stator poles N-S-N-S, each N pole's flux returns through its two S neighbours *via the rotor iron* — short, low-reluctance loops → steeper `dL/dθ` → more torque per ampere-turn. All-same-polarity forces a long back-iron return and wastes it. So the N-S map is kept for flux geometry. [OC]
- **Stepping comes from the stroke sequence**, not from the polarity flip: stroke charges C3 → group A pulls; next stroke charges C4 → group B pulls one pole-pitch over; repeat. This is textbook 2-phase switched-reluctance commutation. [OC]
- **12 stator / 6 rotor has no dead spot under 2-phase drive:** when one group is aligned with rotor poles (zero torque) the other group is mid-gap (max torque). [OC]
- **Direction (and therefore whether the stator reaction is counter- or co-rotating)** is set by whether each group fires just *ahead of* or *behind* the approaching rotor pole — i.e. by the commutation phase baked into the varcap angular offset. Reverse it by swapping the C3↔C4 group assignment or shifting commutation by one pole. [OC/IR]
- The C-EMs pull on the rotor iron; by reaction the **free stator is pushed the opposite way** → stator counter-rotation, which raises relative speed and PRF. The belt-driven rotor supplies the reaction energy. [OC]

---

## 2. Polarization map (all 12 C-EMs)

Uniform winding sense. Odd positions → Group A (cap C3, nodes 1–2). Even positions → Group B (cap C4, nodes 3–4).

| C-EM | Angle | Group | Cap | Polarity @ C3⁺ | Polarity @ C4⁺ |
|---|---|---|---|---|---|
| E1 | 0° | A | C3 | N | S |
| E2 | 30° | B | C4 | S | N |
| E3 | 60° | A | C3 | N | S |
| E4 | 90° | B | C4 | S | N |
| E5 | 120° | A | C3 | N | S |
| E6 | 150° | B | C4 | S | N |
| E7 | 180° | A | C3 | N | S |
| E8 | 210° | B | C4 | S | N |
| E9 | 240° | A | C3 | N | S |
| E10 | 270° | B | C4 | S | N |
| E11 | 300° | A | C3 | N | S |
| E12 | 330° | B | C4 | S | N |

Instantaneous ring pattern: **N S N S N S N S N S N S** at the C3⁺ stroke; flipped by one pole-pitch a half pump-cycle later (C4⁺).

**The alternation depends entirely on the two transfer caps being antiphase.** Verification chain the calculator/sim must satisfy:

```
adjacent poles opposite
  ⟸ adjacent poles on opposite groups (A,B,A,B)
  ⟸ opposite groups on opposite caps (C3, C4)
  ⟸ C3 and C4 swing ANTIPHASE (push-pull), charged on alternate strokes.
```

If the topology ever made C3, C4 in-phase, the pattern collapses to N-N-N-N (no short flux return, near-zero torque). This is the one assumption the whole map rests on — flag it as a self-test (§6). [OC]

---

## 3. Why the coupling cap is mandatory and must be resonant, not small

**Mandatory:** a coil is a near-short at DC. Across a transfer cap at kV DC it would draw `V_bias / R_coil` continuously — hundreds of amps, cratered HV rail, burned winding. Some DC block is required regardless. [OC]

**Not small:** at the low drive frequency (hundreds of Hz) a *small* cap is high-impedance and would block the AC stepping drive along with the DC. To pass the drive you need a *large* cap. [OC]

**Resonant is the elegant choice:** size the cap so coil + cap series-resonate at the drive frequency. Then the branch is

- **open at DC** (block ✓),
- **minimum impedance = R_coil at the drive frequency** (max torque current ✓),
- **inductive / high-Z at f0** (spectator on the central resonator ✓).

One component does the DC block, the torque tuning, and the f0 isolation. [OC]

**Resonance also amplifies the circulating current** — the payoff for a current-starved pump:

```
I_circ ≈ Q · I_input        (series-resonant current gain)   [OC]
```

so a small input current sustains large ampere-turns. The price is voltage magnification on the cap (§4) — which is exactly what the 20 kV rating is for.

---

## 4. The Q / turns / voltage budget — the core of this block

### 4.1 Definitions

```
f_drive   drive fundamental seen by a coil (see §4.4 — pin this first)
L_coil    coil inductance
C_block   series DC-block / resonant cap (user: 440 nF)
V_rating  cap voltage rating (user: 20 kV)
V_bias    DC bias across the cap = transfer-cap DC voltage
V_ripple  AC drive amplitude on the transfer cap
N         coil turns
R_coil    coil DC resistance
A_gap     pole-face area
l_gap     total air gap in the magnetic circuit (= n_gaps · clearance)
```

### 4.2 The governing relations [OC]

```
Resonance:        L_coil = 1 / ((2π·f_drive)² · C_block)
Char. impedance:  Z0 = √(L_coil / C_block) = 1/(2π·f_drive·C_block)
Quality factor:   Q  = Z0 / R_coil
Turns (gapped):   N  = √( L_coil · l_gap / (μ0 · A_gap) )
Cap voltage:      V_cap,peak = V_bias + Q · V_ripple   ≤  V_rating   ← BINDING
Circulating I:    I_circ,max = (V_rating − V_bias) / Z0
```

### 4.3 The closed-form torque limit [OC] — the key result

Combining the above, the torque-driving **ampere-turns at the rating limit are independent of frequency and turns count:**

```
N · I_circ,max = (V_rating − V_bias) · √( C_block · l_gap / (μ0 · A_gap) )
```

Adding turns raises both `L_coil` and `Z0`, so the current drops to exactly compensate. **What actually buys torque is: bias headroom `(V_rating − V_bias)`, the cap `C_block`, and the core geometry (`l_gap`, `A_gap`).** Frequency and turns are then free to choose for other reasons (matching the real drive frequency; wire practicality; f0 isolation) without changing the limiting ampere-turns. [OC]

Design levers for more torque, in order of leverage: lower the DC bias (more headroom), enlarge `C_block`, shrink the gap `l_gap`, enlarge pole area `A_gap`.

### 4.4 Pin the drive frequency first (4× swing)

The pump fires **6 events/rev** (PRF = 6·RPM/60). The two transfer caps are charged on **alternate** strokes (push-pull), so each cap — and therefore each coil group — sees a fundamental at **PRF/2**, while the *combined* rotor torque pulses at the full PRF. Resonate the coil at the frequency the **coil current** actually runs at:

- If each group is energized every other stroke → `f_drive = PRF/2`.
- If the commutation energizes a group every stroke → `f_drive = PRF`.

This must be confirmed against the actual stroke→cap mapping in the sim **before winding**, because it sets `L_coil` (and hence N) by 4×. Worked example below shows both.

### 4.5 Worked example (stated assumptions; calculator uses real inputs)

Assumptions: `C_block = 440 nF`, `V_rating = 20 kV`, `A_gap = 4 cm²`, clearance 1 mm × 2 gaps → `l_gap = 2 mm`, mean turn length 12 cm, design RPM 3000 (PRF 300 Hz).

**Resonant L, Z₀, turns:**

| f_drive | L_coil | Z₀ = √(L/C) | N (turns) | wire length |
|---|---|---|---|---|
| 150 Hz (PRF/2) | 2.56 H | 2411 Ω | ~3190 | ~383 m |
| 300 Hz (PRF) | 0.64 H | 1206 Ω | ~1595 | ~191 m |

**Coil R and Q by wire gauge** (note Q is the same at both freqs because N·l_turn·ohm and Z₀ both scale as 1/f_drive):

| wire | R @150 Hz | R @300 Hz | Q |
|---|---|---|---|
| 28 AWG | 81 Ω | 41 Ω | 29.6 |
| 30 AWG | 129 Ω | 65 Ω | 18.6 |
| 32 AWG | 206 Ω | 103 Ω | 11.7 |

**The binding voltage limit and the resulting current / ampere-turns:**

| V_bias | headroom | I_circ,max @150 Hz | I_circ,max @300 Hz | N·I (both) |
|---|---|---|---|---|
| 10 kV | 10 kV | 4.15 A | 8.29 A | 13 230 A-t |
| 12 kV | 8 kV | 3.32 A | 6.64 A | 10 590 A-t |
| 15 kV | 5 kV | 2.07 A | 4.15 A | 6 620 A-t |

Note the last column confirms §4.3: **N·I depends only on the bias headroom (and C, geometry), not on frequency.** Also: at high Q the allowable ripple is small — e.g. Q ≈ 29.6 with 8 kV headroom permits only `V_ripple ≤ 8000/29.6 ≈ 270 V` before the resonant swing reaches 20 kV. The cap rating, the bias, the coil R (hence Q), and the allowable ripple are one coupled constraint: budget them together.

**Stored energy / safety:** `½·C·V² = 88 J per cap` at 20 kV; ×12 ≈ **1.06 kJ** of HV storage on the spinning stator. Lethal. Drives the per-coil vs per-group cap decision (§5).

---

## 5. Per-coil vs per-group caps

Same total energy either way:

- **12 per-coil caps:** each 440 nF / 20 kV, resonates with one coil (`L_coil` from §4.5). More parts, smaller each, distributed.
- **2 per-group caps:** 6 coils paralleled → group inductance `L_coil/6`; resonant cap `= 6 × 440 nF ≈ 2.64 µF / 20 kV` each. Fewer, larger.

Calculator should support both via a `demCapTopology` toggle and report the resulting per-component value and energy.

---

## 6. Calculator block — inputs and outputs

**Namespace:** new prefix `dem*` (distributed-electromagnet motor). Document in CONVENTIONS.md (§ additions below). `d` alone remains forbidden; `dem*` is a compliant prefix.

### Inputs

| ID | Meaning | Units | Default |
|---|---|---|---|
| `demRpm` | design/operating RPM | rpm | 3000 |
| `demEventsPerRev` | pump events per rev (sets PRF) | – | 6 |
| `demDriveMode` | `perStroke` (PRF) or `altStroke` (PRF/2) | enum | altStroke |
| `demCapBlockNF` | series cap value | nF | 440 |
| `demCapRatingKV` | cap voltage rating | kV | 20 |
| `demCapTopology` | `perCoil` or `perGroup` | enum | perCoil |
| `demBiasKV` | DC bias = transfer-cap voltage | kV | 12 |
| `demRippleV` | AC ripple amplitude on transfer cap | V | 250 |
| `demPoleAreaCm2` | pole-face area A_gap | cm² | 4 |
| `demClearanceMm` | single-gap clearance | mm | 1 |
| `demNGaps` | gaps in the magnetic circuit | – | 2 |
| `demWireAWG` | winding wire gauge | AWG | 30 |
| `demTurnLenCm` | mean length per turn | cm | 12 |

### Outputs (all derived; show formula on hover)

| ID | Meaning | Formula |
|---|---|---|
| `demPrfHz` | pump PRF | `demEventsPerRev·demRpm/60` |
| `demDriveHz` | coil drive fundamental | PRF or PRF/2 per `demDriveMode` |
| `demLcoilH` | resonant coil inductance | `1/((2π·demDriveHz)²·C)` |
| `demTurns` | required turns | `√(L·l_gap/(μ0·A))` |
| `demZ0Ohm` | characteristic impedance | `√(L/C)` |
| `demRcoilOhm` | coil DC resistance | `N·l_turn·ρ_AWG` |
| `demQ` | quality factor | `Z0/R` |
| `demRippleMaxV` | max ripple before rating | `(V_rating−V_bias)/Q` |
| `demIcircMaxA` | max circulating current | `(V_rating−V_bias)/Z0` |
| `demNI` | ampere-turns at limit | `(V_rating−V_bias)·√(C·l_gap/(μ0·A))` |
| `demVcapPeakKV` | actual peak cap voltage | `V_bias + Q·V_ripple` |
| `demEnergyJ` | energy per cap | `½·C·V_rating²` |
| `demCapPerGroupUF` | per-group cap (if topology) | `6·C` |

**Warnings the block must raise:**
- `demVcapPeakKV > demCapRatingKV` → over-voltage (reduce ripple / bias / Q, or detune).
- `demRippleMaxV < demRippleV` → same condition, stated as the ripple ceiling.
- `demBiasKV ≥ demCapRatingKV` → no AC headroom; motor produces no torque.
- reminder banner: transfer caps **must** be antiphase (push-pull) for the polarization map to hold.

---

## 7. Self-tests (on-load, consistent with existing block tests)

1. **Resonance round-trip:** `1/((2π·demDriveHz)²·C) == demLcoilH` within 1e-6.
2. **Z0 identity:** `√(L/C) == 1/(2π·f·C)` within 1e-6 (both forms agree at resonance).
3. **Ampere-turn invariance:** compute `N·I_circ,max` at f_drive = PRF and at PRF/2 with the same bias; assert equal within 0.1 % (guards §4.3).
4. **Voltage-budget guard:** with defaults, assert `demVcapPeakKV` flagged when `demRippleV` pushed above `demRippleMaxV`.
5. **Energy:** `½·440e-9·20e3² == 88.0 J` within 0.1 %.
6. **Antiphase assertion (symbolic):** assert group A↔C3, group B↔C4, and that the documented polarity table yields N-S-N-S at C3⁺ (parity check on the 12-row map).
7. **Per-group cap:** `demCapPerGroupUF == 6·demCapBlockNF` within 1e-9.

---

## 8. Cross-section / UI additions

- Add the 12 C-EMs to the axial/face view as a stator ring at `demClearanceMm` from the rotor rim; colour by group (A/B) and tag polarity (N/S) per the §2 map at the C3⁺ instant.
- New legend swatches: `--cem-coil` (copper winding) and `--cem-core` (laminated steel — see materials doc), cross-referenced to the existing hatch legend.
- A small budget panel mirroring §6 outputs, with the over-voltage warning inline.

---

## 9. Open forks (carried)

1. **Drive-frequency mapping (§4.4)** — confirm stroke→cap pattern (PRF vs PRF/2) in the sim before winding.
2. **Torque vs stator load** — the spin-up torque must beat stator drag + inertia; couples to the deferred flywheel/inertia block. Ampere-turns from §4.3 feed a torque estimate once gap geometry and rotor pole geometry are fixed.
3. **Core loss at the drive frequency** — lamination spec; see materials doc §5.
4. **Bias source for class-A torque boost** — optional controlled DC bias through a current-limited path (not off the HV rail); deferred.
5. **Coil self-resonance** — at ~3000 turns the inter-winding capacitance gives a self-resonant frequency that must sit well above f0; check during winding spec.

---

## Appendix — CONVENTIONS.md addition

```
## Block D — distributed electromagnet motor (prefix dem*)
demRpm, demEventsPerRev, demDriveMode, demCapBlockNF, demCapRatingKV,
demCapTopology, demBiasKV, demRippleV, demPoleAreaCm2, demClearanceMm,
demNGaps, demWireAWG, demTurnLenCm                         [inputs]
demPrfHz, demDriveHz, demLcoilH, demTurns, demZ0Ohm, demRcoilOhm,
demQ, demRippleMaxV, demIcircMaxA, demNI, demVcapPeakKV,
demEnergyJ, demCapPerGroupUF                                [outputs]
Rule: 'd' alone remains forbidden; 'dem' is the Block-D prefix.
Block D is a parallel producer; it never feeds solveDoubler4.
```

## Appendix — CHANGELOG entry

```
### Block D — distributed electromagnets (brief v0.1)
Added: reluctance spin-up motor spec. Iron-rotor (passive) + 12 stator C-EMs
in two interleaved groups on transfer caps C3/C4, uniform winding, N-S-N-S
from antiphase grouping. Series resonant DC-block cap (440 nF/20 kV target);
Q/turns/voltage budget with closed-form ampere-turn limit
N·I = (Vrating−Vbias)·√(C·l_gap/(μ0·A)). New dem* namespace, inputs/outputs,
7 self-tests, cross-section ring + legend. Parallel producer; solver untouched.
```
