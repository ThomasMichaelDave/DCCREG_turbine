# Reluctance pole pair for the magnetic doubler — findings

**Goal.** Design the C-EM / utron poles for a high inductance swing so the magnetic doubler (wound utrons → AH pair,
`sim/hub-drive-findings.md`) grows and holds the AH at its target, then optimise wherever possible.

**Designer's inputs:**
- in air for now, but judge vacuum too;
- try a 0.5 mm gap and give the loss for 1.0 mm;
- the envelope may change if that gives a positive feasibility result.

**Tools:**
- `sim/pole_fd2d.py`: a new 2-D magnetostatic finite-volume solver for A_z in the plane of rotation, unrolled at the
  gap radius, periodic over 120°, with linear iron μ_r 3000 [RH].
- `sim/pole_design.py`: the staged search and sizing.
- `sim/magnetic_doubler.py`: the pump circuit, extended to take a tabulated L(θ) shape and the pump frequency.
- Drawings: `docs/figures/pole-pair-flux-g0p5.png` and `docs/figures/pole-pair-flux-g1p0.png`, from
  `docs/make_pole_drawing.py`.

Results: `sim/pole_design_{p1,p1b,p3,final,real,kick}.json`. The p1 T-family rows are superseded by p1b, after a
tooth-parity fix.

## 1. Topology (what changed)

- **Old:** the C-EM was an axial C-core with jaws 60 mm apart, and the utron block left a 7 mm gap on each side.
  Leakage dominated, so the ratio was about 1.15.
- **New:**
  - The **utron is a wound U-core** (two radial tips, the coil around its back iron) on the **rotor**.
  - The **C-EMs become passive laminated bridges**, 6 per side on the stator, with no coils.
  - The air gap is **radial**, so the bearings set it.
- **A/B antiphase:** the B side is offset half a bridge pitch (30°). The 3 utrons per side align together (120° apart).

**Self-check:** aligned L comes out 1.21 × the two-gap analytic value (gap fringing plus slot leakage). The mesh is
converged to 0.5 %.

## 2. Screening and refinement (P1, P1b)

- **104 candidates** at 13 angles each. Every one gets its L(θ) fitted as a cosine series, then the pump circuit gives
  its true gain per cycle z, with copper in every coil and τ_fixed 0.5 s for La/Lb [RH].
- **Discrete bridges (S) beat a toothed ring (T).**
  - The ring's continuous iron caps its ratio at 3.1, even at 0.5 mm with 12–36 teeth.
  - None of the ring designs fit the radial space.
- **The gap radius is the biggest lever.** At 130 mm the coil's return side doesn't fit above the sleeve once the slot
  is deeper than about 45 mm, and the 60° pitch limits the utron width.
  - Moving to **r_g 165 mm** fixes both.
  - The passive bridges reach only r ≈ 186 mm, far inside the old C-EM envelope (r 265 mm).
- **Winner, the same geometry at both gaps:** tips 20 mm, slot 50 × 60 mm, back iron 20 mm, bridges 90 × 20 mm.

| gap | κ_L (2-D, with end corrections) | τ = L/R (stack 70 mm) | gain per cycle z (60 Hz) |
|:--|--:|--:|--:|
| **0.5 mm** | **11.6** | 0.54 s | **1.30** |
| 1.0 mm | 6.7 | 0.31 s | 1.19 |

- **Bridge length:** 70 mm is worse (z 1.20) and 100 mm is equal (1.31), so l_b ≈ utron width (90 mm) is the
  optimum.
- **Stack length:** 70 / 100 / 140 mm give z 1.30 / 1.31 / 1.32. I chose 70 mm, which makes the section about
  184 mm long per side including end turns.

## 3. Sizing the operating point (P3, final)

**AH target:** 450 ampere-turns peak, against the rod limit of about 600, with the AH rewound to 160 turns [RH].

**Three optimisations found:**
1. **Saturation level.** The level is set by a deliberately narrow **neck** in the utron back iron. Heat ∝ Ψ_s², so
   the neck is sized to the AH target and no larger. It comes to 2.2 mm at 0.5 mm gap and 3.6 mm at 1.0 mm.
   - Mechanically that is a 6 mm bridge over 37 % / 60 % of the stack, with the rest punched out of the laminations.
2. **Utron turns.** Copper heat at a fixed AH current grows with N_u², but too few turns lets the AH coil's own
   inductance and resistance stop the pump. The optimum is about 400 turns (0.5 mm) and 600 turns (1.0 mm).
3. **Coupling inductors.** La = Lb = 0.6 × L_max beats the electrostatic pump's 1.1 (+0.03 in z, −35 % fixed copper).

## 4. Real diodes: start-up is the catch

- **With silicon diodes (≈ 0.55 V) and a small seed (3 % of Ψ_s), the low-turn designs do not start.**
  - While growing, their winding voltages are only a few volts, so the diode drop wins.
  - From the same small seed you need ≥ 1000 turns with Si, or ≥ 800 with Schottky. That costs 59–94 W.
- **Once kicked to ≥ 8–10 % of Ψ_s, the low-turn designs run with Si diodes.** The diode drop then costs only about
  2 W. A kick of 0.23 A in the utron group (about 35 mJ) is enough.
- **The kick source is open.** Options: a one-time start pulse (a capacitor or battery with a push-button, the only
  switch and used only at start-up), a small PM bias in the utron back iron (untested), or a pulse from the
  electrostatic side.

## 5. Design points and the 1.0 mm penalty

Si diodes, kicked start, AH 450 ampere-turns, 600 rpm relative.

| | **0.5 mm** | 1.0 mm | 1.0 mm, from a small seed (no kick) |
|:--|--:|--:|--:|
| utron turns (3 per group, wire) | 400 (3.4 mm²) | 600 (2.3 mm²) | 1000 Si / 800 Schottky |
| utron group L (La = Lb) | 0.90 H (0.54 H) | 1.16 H (0.70 H) | — |
| utron current / peak winding voltage | 0.8–2.8 A / 106 V | 0.8–2.8 A / 259 V | — / 690 V |
| **belt power** (copper + diodes + AH + iron) | **18.6 W** | **38.3 W** | 99 W Si / 65 W Schottky |
| heat per utron coil | 1.9 W | 4.7 W | 13.3 W / 8.6 W |
| fixed inductors / AH / diodes | 2.4 / 1.9 / 1.9 W | 3.6 / 2.0 / 2.0 W | — |
| coil temperature, air / vacuum (radiation only) | 42 / 49 °C | 45 / 61 °C | — |
| minimum start kick | 10 % of Ψ_s | 8 % | (small seed) |
| AH share of the belt | 10.6 % | 5.6 % | ~2 % |
| linear gain margin z | 1.30 | 1.19 | — |

- **The 1.0 mm penalty: about 2.1× the power for the same AH**, efficiency 10.6 % → 5.6 %. The gain margin also
  drops from 1.30 to 1.19.
- Without a start kick, the two gaps cost about the same (≈ 90 W with Si), because start-up sets the turn count.
- **Air and vacuum both work.** The design points sit far below the cooling limits: about 87 W per coil in air and
  about 40 W per coil at 155 °C in vacuum (radiation only).
- **Masses:** 3.4 kg of copper per utron coil, 2.25 kg of iron per utron, 0.96 kg per bridge.
  - The copper is there for τ, not current: J ≈ 0.6 A/mm².
  - Aluminium would save about 2/3 of the winding mass for about 0.6 × τ.

## Caveats
- **2-D model [IR].** Curvature is neglected and the end/axial-fringe corrections (+30 % unaligned, +3 % aligned) are
  [RH], so a 3-D check of κ_L is still due. The iron is linear μ_r 3000, and saturation enters the circuit through the
  neck law.
- Iron loss is from the M235-35A 1.5 T / 50 Hz rating scaled as f^1.3·B² [RH]. τ_fixed of 0.5 s for La/Lb assumes
  large gapped cores (about 2 J stored each) [RH].
- **AH:** the 160-turn rewind (1.0 mH, 0.27 Ω) is [RH], and the AH–bicone mutual coupling is not included.
- **Next:**
  - a 3-D check of the chosen pair;
  - the start-kick source;
  - the La/Lb core design;
  - the tube STEP update (r_g 165 mm, the new utron and bridges, the 184 mm reluctance section);
  - mechanical concentricity for 0.5 mm with counter-rotating bearings.
