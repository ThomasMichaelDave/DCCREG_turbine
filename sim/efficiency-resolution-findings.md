# Findings — EFFICIENCY-RESOLUTION: bank the finding, correct the propagated η, flag Ca/Cb

**Branch** `efficiency-resolution` (off `seq-stat-commutation`). **Verdict:** **`EFFICIENCY-RESOLVED`.**
`RECOVERY-FORBIDDEN` settled the efficiency question; this brief **integrates the documentation**,
**corrects η 0.70 → the validated value everywhere it propagated**, **banks the conservation
principle**, **marks `commutator_real_core` superseded**, and **flags the Ca/Cb simplification** (gated
on TMD, not executed). The repo now rests on the validated **η ≈ 0.50** computed from the frozen cores.

## §-checks (brief §5)

| # | check | result |
|---|---|---|
| 1 | `docs/efficiency-resolution.md` integrated + cross-referenced | ✓ added; README links it; CONVENTIONS.md banks the principle + points to it |
| 2 | operating model recomposed (direct + island sink); **exact η reported**; commutator tagged superseded | ✓ `design_synth.operating_point` → **η 0.518** (design pt); `solver_inventory.csv` tags `commutator_real_core` (and `doubler_resonant_core`) **SUPERSEDED-DIAGNOSTIC** |
| 3 | η corrected everywhere it propagated; **no surviving operating 0.70 claim** (grep) | ✓ HTML canary + readouts + footer, synth anchor/comments — grep clean (remaining 0.70 are all *forbidden/falsify* context) |
| 4 | conservation principle banked verbatim | ✓ in `docs/efficiency-resolution.md` §2 and `CONVENTIONS.md` |
| 5 | dual canary reproduces **regression** (z 1.334) and the **corrected operating** η | ✓ canary operating rung now asserts `0.44 < η < 0.55` (not `|η−0.70|<0.03`); CLI = in-browser contract holds |
| 6 | Ca/Cb simplification flagged with touch-points; **not executed** | ✓ map below |

## 1. The computed validated η `[OC]`

`operating_point` now composes the **validated cores** (no `commutator_real_core` in the operating
path):

> **η_operating = (useful + island_recovered) / (useful + doubler_tax + island_tax)**
> = (6.153 + f_rec·4.407) / 20.347

with the energy anchors from `energy_balance.csv` / `resonant_island.csv` (mJ/fire) and `f_rec` from
`island_resonant_core` (S2-validated) at the design Lx/R:

| operating point | f_rec | island recovered | **η_operating** |
|---|---|---|---|
| Lx 1 mH, R 2 Ω (Q 729) | 0.996 | 4.39 mJ | **0.518** |
| R 20 Ω (Q 73) | 0.958 | 4.22 mJ | 0.510 |
| R 100 Ω (Q 15) | 0.806 | 3.55 mJ | 0.477 |

→ **η ≈ 0.48–0.52 over the usable island-Q band, 0.518 at the design point** — the doubler-core
conversion η stays **0.386** (the regression). This is the honest "≈ 0.45–0.50" of the resolution doc,
**computed**, not hard-coded. `commutator_real_core`'s α_max/η are retained only in
`operating.forbidden_diag` (the superseded forbidden-path number, 0.70).

## 2. What changed (the corrections)

- **`sim/design_synth.py`** — `operating_point` recomposed (direct + island sink; the firing-geometry
  margins I11/I12 stand); **I13 renamed `I13_fe_budget` → `I13_island_recovery`** (asserts the validated
  η beats the floor); the dual-return docstrings corrected; `commutator_real_core` kept imported only for
  the forbidden-path diagnostic.
- **`tools/charge-pump-synth-live.html`** — the **canary operating rung** asserts the validated band
  (`0.44 < η < 0.55`), not 0.70; the headline readout shows **η operating ≈ 0.50** with the **island
  recovered** mJ; **α_max / η_forbidden / FE+arc are relabelled the "forbidden-path diagnostic"** (not
  the operating efficiency); the tier header and footer rewritten to the validated machine.
- **`solver_inventory.csv`** — `commutator_real_core` **SUPERSEDED-DIAGNOSTIC** ("BRIGADE-RECOVERABLE
  η~0.70 FORBIDDEN"), `doubler_resonant_core` likewise.
- **`docs/efficiency-resolution.md`** — the authoritative record (integrated verbatim + a repo-integration
  note with the computed η).
- **`README.md`** — efficiency line + link. **`CONVENTIONS.md`** — the conservation principle banked.

## 3. The conservation principle (banked) `[OC]`

> **A resonant pump's own equalization cannot be resonated for energy recovery — the equalization *is*
> the pump.** Resonating it clamps it (ratchet, tax lost) or breaks the ratchet (pump dies); sequencing
> and statistics only sample those two arms, never a recovering third. **Only a downstream sink transfer
> recovers freely.**

(In `docs/efficiency-resolution.md` §2 and `CONVENTIONS.md`. Established: doubler-resonant ceiling +
S3 either/or + sequenced-statistical conservation arbiter.)

## 4. The Ca/Cb simplification — flagged, NOT executed (gated on TMD) `[IR]`

The Ca/Cb **brigade inductors** (`L_A1–6`, `L_B1–6` in the schematic) were kept for the **0.404 → 0.70
recovery that does not exist**. Removing them **reverts the doubler core to the frozen direct
equalization** (already validated, z 1.334 / η 0.386); **the island `Cx`/`Lx` stays** (the real, S2-
validated recovery). The machine then **simplifies to the frozen direct doubler + the island resonant
transfer — a fully validated configuration, no new physics.** **The actual topology change is a separate
design brief on TMD's sign-off.** Touch-points this would change:

| touch-point | change if Ca/Cb inductors removed |
|---|---|
| **KiCad schematic** (`DCCREG_Turbine_circuit.kicad_sch`) | delete `L_A1–6` / `L_B1–6` (12 brigade inductors); the rotor→bank coupling reverts to the direct Ca/Cb path; re-export the netlist (43 → 31 components) |
| **DXF** (`docs/kicad/*.dxf`, firing stations) | unchanged (the gaps/stations are not the brigade inductors); the SG3b/SG4b island fires + Lx3/Lx4 stay |
| **`topology_edge_list.csv`** | regenerate from the simplified schematic (drop the 12 L_A/L_B edges) |
| **`design_synth` `ESTABLISHED`** | drop `brigadeL_mH`; the I10 **brigade multi-resonant clocking** sub-check (the L_A/L_B t½ co-existence) is removed (the island Lx clocking stays) |
| **resonator sizing** | unchanged — the tank (`C_R`/`L_R`) and the island transfer are untouched; the bank `C_AR/C_BR` stay (they are the transfer banks, not the inductors) |
| **the operating η** | **unchanged at ≈ 0.50** — the brigade inductors never contributed (their recovery was the forbidden path); removing them is a *simplification*, not an efficiency loss |

**The decision is TMD's**; the implication (revert to direct + island, fully validated, η unchanged) is
mapped so it is informed. This brief only flags it.

## 5. Verdict

**`EFFICIENCY-RESOLVED`** — the documentation is integrated; the operating model is the validated
**direct + island sink** (η **0.518** computed, ~0.50); **no η 0.70 operating claim survives**
(grep-confirmed; the remaining mentions are the forbidden-path diagnostic / the falsification record);
the conservation principle is banked; the Ca/Cb simplification is flagged with touch-points (not
executed). The dual canary still reproduces the regression (z 1.334) and now the corrected operating η.
Frozen `doubler_core` / `shuttle_core` / `island_resonant_core` byte-identical. **Not merged** (the
corrections land on review; the Ca/Cb topology change awaits TMD's separate sign-off).

## Deliverables

`docs/efficiency-resolution.md` · `sim/design_synth.py` (recomposed operating point; the exact η; I13
renamed) · `tools/charge-pump-synth-live.html` (corrected canary + readouts + diagnostic relabel) ·
`solver_inventory.csv` (superseded tags) · `README.md` + `CONVENTIONS.md` (η corrected + the principle) ·
this findings doc. Frozen cores empty-diff. **Not merged.**
