# Motor geometry (C-EM + utron)

**The complete machine, charge pump plus motor, is `../il2f-6563b90d-rc40-FULL-pump+motor.step`.** It has one root,
"DCCREG machine", with two parts under it: "charge pump" (1099 solids) and "motor" (66 solids).

This folder holds only the motor and its inputs:

| file | what it is |
|:--|:--|
| `C-em_and_motor_coil_export.step` | the designer's source: one C-EM and one utron |
| `src/*.step` | each source solid in the local frame, with the C-EM squared to the utron |
| `MOTOR-ONLY-il2f-6563b90d-rc40.step` | the 12 C-EMs and 6 utrons, placed, **without** the charge pump |
| `il2f-6563b90d-rc40+motor.json` | the build plus the motor, for `tools/pump-geometry.FCMacro` / the Fusion add-in |
| `motor-il2f-6563b90d-rc40.json`, `-motor-only.json`, `-parts.csv`, `.png` | the parts list, the motor-only design, the parts table, the picture |

Regenerate with `python3 sim/motor_geometry.py`. The findings are in `sim/motor-geometry-findings.md`.
