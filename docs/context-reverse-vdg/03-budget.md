# Budget — first pass (`sim/reverse_vdg_budget.py` → `sim/reverse_vdg_budget_results.json`)

**Inputs:**
- The tube ledger (`sim/tube_ledger_results.json`): 300 rpm relative and a 20 kV peak.
- The C-EM envelope at r_u 130: spine 750 mm², bobbin window 48 × 13 mm.
- A 1 mm running clearance and a 0.4 T peak-to-peak spine flux swing with PM bias [RH].
- Motor efficiency 0.5–0.8 including the switches [RH].

## 1. Power and current [OC]

| | strays fixed | strays scaled |
|:--|:--|:--|
| belt input | 2.46 W | 2.47 W |
| pump surplus at 20 kV (the most the motor can draw) | 1.31 W | 1.76 W |
| link current at 20 kV | 66 µA | 88 µA |

## 2. Torque available vs needed

| | η 0.5 | η 0.8 |
|:--|:--|:--|
| torque from the whole surplus (T = η·P / ω_rel) | 21–28 mN·m | 33–45 mN·m |

Needed (stator drag estimate, `tube-ledger-findings.md`):
- **19 mN·m** in a shell or vacuum (vane shear plus bearings);
- **225 mN·m** in open air (C-EM windage dominates).

**Verdict:**
- **Shell or vacuum:** closes with 10–140 % margin, using all of the pump's surplus.
- **Open air:** 5–10× short.

Either way, the electrical path costs the belt 1 / (η_pump·η_motor) ≈ 2–4× the drag power. A reversing gear costs about
1.05×. [OC]

## 3. Teeth and frequency [IR]

| tooth pitch at r 130 | teeth | pitch / gap | electrical f at 300 rpm |
|:--|:--|:--|:--|
| 10 mm | 82 | 10 | 410 Hz |
| **13.6 mm** | **60** | **14** | **300 Hz** |
| 20 mm | 41 | 20 | 205 Hz |

- 60 teeth fit the 60° phase plan (`02-reversal-concept.md` §2).
- Pitch / gap ≥ 10 keeps the tooth swing large: that is the patent's point.
- 300 Hz suits 0.1–0.2 mm laminations or SMC.

## 4. Winding [OC with the [RH] flux swing]

EMF per turn = π·f·ΔΦ = **0.28 V** (60 teeth, ΔΦ 0.3 mWb). For 20 kV / 12 coils = 1.67 kV per coil that needs about
**5900 turns**.

| wire | turns in the window | R per coil | string EMF at 300 rpm | copper loss at 88 µA | stall current at 20 kV |
|:--|:--|:--|:--|:--|:--|
| 0.12 mm | 15 890 | 4.3 kΩ | 54 kV | 0.4 mW | 0.39 A |
| 0.16 mm | 9 903 | 1.5 kΩ | 34 kV | 0.14 mW | 1.1 A |
| **0.20 mm** | **6 207** | **0.6 kΩ** | **21 kV** | **0.06 mW** | **2.8 A** |
| 0.25 mm | 4 251 | 0.3 kΩ | 14 kV | 0.02 mW | 6.4 A |

- 0.20 mm matches the link at 300 rpm relative.
- The back-EMF grows as the stator spins up, so the switches must also handle the link sitting *below* the back-EMF.
  Then the switches stop conducting and the motor freewheels.
- Copper loss is negligible. The real losses are core loss at 300 Hz, the switches and windage. [RH]

## 5. What this budget does not yet include

- **The loaded pump.** The surplus is the eigen-state growth term. Whether the pump *sustains* 20 kV while 66–88 µA
  leave is gate G-LOAD.
- **The 0.4 T swing.** It is an assumption. A magnetostatic solve with the toothed jaws and the PM (G-SWING) replaces it.
- **Core loss, PM eddy loss, switch loss**, and the gate-drive power at each coil's potential.
- **Torque ripple**, and the reaction torque on the stator cage (the patent warns about vibration from it).
