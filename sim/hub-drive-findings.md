# Hub drive: two pumps for the central cavity — findings

**Design pivot (designer's decision, 2026-10).**
- **Coupling:** rotor and stator are geared 1 : −1, the same speed in opposite directions. The gear, and through it the
  frame, is the reference body for every reaction torque. The belt pays for everything.
- **Bicone:** driven by the **electrostatic** diode doubler (diodes only; a spark-gap dump tested as an option).
- **AH pair:** driven by a **magnetic** pump built from the C-EMs and utrons, pulsed. The utrons are split 2 × 3 (A
  top, B bottom), like the C-EMs (2 × 6).
  > **Naming (2026-10-09):** this study puts side A on top. The record (the tube build, the hub, the rings) puts side
  > A below and side B above. Either way each branch carries its own side's AH coil (`sim/ah_winding.py`).
- Operating point: 300 rpm each way, so 600 rpm relative and 60 pump cycles per second (6 per rev).
  > **The pivot's first operating point.** The record runs 600 rpm each way, 1200 rpm relative and 120 Hz, and its
  > pumps take 21.5 W (`sim/pole-design-findings.md` §6, `docs/drive-gear-belt.md` §1).

**Tools:**
- `sim/magnetic_doubler.py` → `sim/magnetic_doubler_results.json`
- `sim/bicone_drive.py` → `sim/bicone_drive_results.json`
- schematic: `docs/schematic-hub-drive.svg` (generator `docs/make_schematic_hub.py`)

Both are ngspice. Every power term is integrated by the solver.

## 1. The magnetic pump is the exact dual of the Bennet doubler

The de Queiroz core's graph is planar: a wheel with the reference at the hub and the ring 1–2–4–3. Its dual swaps the
elements one for one [OC]:
- C → L, V → I, Q → Ψ;
- each ideal diode stays an ideal diode, with its anode on the face to the right of the original edge.

| electrostatic | magnetic (this machine) |
|:--|:--|
| C1(θ), C2(θ) (antiphase plates) | **A and B utron groups** L1(θ), L2(θ): 3 wound utrons each, against the stator's toothed C-EM iron, A and B offset by half a tooth pitch |
| Ca, Cb | fixed coupling inductors La, Lb (1.1 × L_max, air-gapped) |
| Cpar | small series inductors Lp2, Lp3 |
| D1–D4 | D1*–D4* (see the schematic) |
| breakdown limit | **iron saturation** |
| clamp / HV load | **AH top in series with A, AH bottom in series with B** |

- **The A-dynamo / B-motor picture is exactly how it works.**
  - While A's inductance falls at held flux, its current rises: A generates and the belt does the work.
  - At the same time B's inductance rises, and B motors, giving some work back.
  - Every half cycle they swap. The diodes pass the current from one group to the other.
- **Duality check.** With near-zero copper loss (τ 100 s) and the electrostatic ratio 15.66, the magnetic circuit gives
  z **1.528** per cycle. The electrostatic machine gives 1.512 in ngspice and 1.515 in the engine. The 1 % difference
  comes from the node snubbers and the softer diodes.

## 2. When it grows

**Gain per cycle z** (it must exceed 1):

| L ratio κ_L | lossless | τ 0.05 s | τ 0.118 s | τ 0.25 s | τ 0.5 s | τ 1 s |
|:--|--:|--:|--:|--:|--:|--:|
| 3 | 1.12 | | | | | |
| 5 | 1.28 | | | | | |
| 6 | 1.33 | dies | 1.06 | 1.20 | 1.26 | 1.30 |
| 8 | 1.40 | dies | 1.12 | 1.26 | 1.33 | 1.36 |
| 10 | 1.45 | dies | 1.15 | 1.30 | 1.37 | 1.41 |

- **κ_L = L_aligned / L_unaligned.**
  - Today's C-EM/utron pairs give about 1.15, which is dead.
  - A toothed pole pair like a switched-reluctance motor's gives 6–10 [RH].
- **τ = L/R of each coil.** It depends on the core and copper size, not on the turns.
  - The example coil (20 × 20 mm core, 1 mm aligned gap, 0.67 mm wire, 50 % fill) gives τ ≈ 0.12 s [RH].
- **Threshold at 60 Hz:** κ_L ≳ 3 and τ ≳ 0.08 s.
- **Start-up seed:** iron remanence or a small PM bias. The run used a 10 mA seed.

## 3. Steady state: saturation sets the level

| case | utron current | AH ampere-turns | core B | belt | utron Cu | fixed Cu | AH Cu |
|:--|:--|:--|--:|--:|--:|--:|--:|
| **κ_L 8, τ 0.118 s, AH 160 t (design point)** | 1.0–2.7 A | **157–425** | 1.35 T | 144 W | 100 W | 42 W | 1.6 W |
| κ_L 8, τ 0.118 s, AH 600 t | 0.85–2.2 A | 508–1336 | 1.24 T | 118 W | 70 W | 32 W | 16 W |
| κ_L 8, τ 0.25 s, AH 160 t | 1.7–4.6 A | 271–729 | 1.59 T | 205 W | 144 W | 56 W | 4.8 W |
| κ_L 6, τ 0.25 s, AH 160 t | — to 3.65 A | 229–582 | 1.49 T | 140 W | 96 W | 40 W | 3.3 W |
| κ_L 8, τ 0.25 s, AH (a) 50 t | 1.7–4.6 A | 86–231 | 1.60 T | 206 W | 148 W | 58 W | 0.5 W |

- **The AH current is pulsed and unipolar.** The A and B currents are in antiphase (schematic inset), so the top and
  bottom AH coils take turns being the stronger one. The cusp null moves axially once per cycle.
  - For true AC, couple the AH through a transformer, which removes the DC part.
  - **For a steady cusp**, put a bypass capacitor across each AH coil. At the pick, 22 mF per coil holds both coils at
    300 A-turns ±3 % with the pump unchanged (`sim/ah-steady-cusp-findings.md`). With the utrons in 3-D
    (2026-10-09, `sim/utron-3d-findings.md`) it holds them at 221–245 A-turns; 249–272 with the neck's field map as
    well (`sim/neck-nonlinear-findings.md` §6).
- **AH rod limit.** The MnZn rod's 0.30 T limit corresponds to about 600 ampere-turns (with the register's cone
  windings in series; for the AH alone 743, `sim/ah-null-findings.md` §4).
  - The 160-turn rewind fits at the design point.
  - The 600-turn rewind saturates the rod.
- **The power is set by the iron.** Growth stops where the cores saturate.
  - Currents scale with the core's saturation flux Ψ_s; all powers scale with Ψ_s².
  - A smaller core cuts the 140 W of rotor copper heat quadratically, and the AH ampere-turns linearly.
  - **About 17 W per utron coil and 21 W per fixed inductor at the design point need cooling.**
- **Power to the frame.** 144 W at 600 rpm relative is 2.3 N·m. The magnetic pump is about 15× the electrostatic one
  (9 W), because magnetic machines are that much more power-dense.

## 4. The bicone on the electrostatic pump

- **Placement.** Each 32-turn cone sits in series with its varicap on the **rotor** side: R-A → cone A → shaft, and
  R-B → cone B → shaft.
  - The hub and the rotor vanes turn together, so no rotating contact is needed.
  - The pump's nodes 1–4 and the diodes stay on the stator vanes.
  - **Superseded:** the HV side has moved onto the rotor (`sim/core-field-findings.md`). The core's field now comes
    from two electrodes in the vacuum on the AH null (`sim/core-null-field-findings.md`); the cones are non-metallic
    shaft couplers.
  - D1/D2 still need the stator-to-shaft reference brush.

| limiter | belt (600 rpm rel.) | cone current | ampere-turns |
|:--|--:|:--|--:|
| diodes only (avalanche clamp 20 kV) | 9.1 W | 1.7 mA rms, 3.8 mA peak | **0.12** |
| spark gap 20 kV + quench diode (dump) | 6.8–7.4 W | **19–21 A peak** (analytic 20.2 A) | **610–680** |

- **Diodes only: the bicone is decorative.** The cones see only C1/C2's own current.
- **With the dump** each node discharges through its cone about once per pump cycle (60–67 per second per side):
  - about 54 mJ per dump;
  - ringing at about 1.8 MHz (cone with C1 near its minimum);
  - the gap itself is the voltage limiter, so it also replaces the avalanche clamp.
- Accuracy: the energy books close to ±5 % in the dump runs, because the solver tolerance had to be loosened to get
  through the strike; to 5e-5 W in the diodes-only run.

## Caveats and open items
- **Assumed values [RH]:** κ_L, τ, Ψ_s (1.5 T over 20 × 20 mm) and the AH rewind values. The toothed C-EM/utron geometry
  still has to be designed and field-solved (it replaces gate G-SWING).
- **Modelling choices [IR]:**
  - the node snubbers (10 nF + 1 kΩ at each dual node; 0.08 W);
  - the soft saturation law i = Ψ/L·(1 + (Ψ/Ψ_s)⁶);
  - the cosine L(θ) and C(θ).
- **Not modelled:**
  - the mutual coupling between the bicone and the AH (cone–AH mutuals exist in the RA register);
  - eddy and iron losses at 60 Hz plus harmonics;
  - real gap ringing (the quench diode stops the gap at its first current zero) and the 1–3 kV strike offset.
- **The dual diodes D1*–D4*** sit at node potentials of a few hundred volts, set by L di/dt in the dual. They are
  low-voltage, high-current parts, unlike the 20 kV stack. Their peak voltage has not been checked yet.
- **The electrostatic and magnetic pumps share the rotor and stator** but are electrically separate. Each one's
  reaction torque goes into the gear.
