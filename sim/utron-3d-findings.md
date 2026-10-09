# The utrons' κ in 3-D — findings

**Source:** `sim/utron_3d.py` → `sim/utron_3d_results.json`; figure `docs/figures/utron-3d.png` (the same script).

**Status:** in progress — the production run is under way; the results sections below are filled from
`sim/utron_3d_results.json` when it finishes.

**Naming:**
- κ = L_al / L_un of one utron; L / N² is per turn squared; "per coil" is × 200² (`sim/pole_design_variants_op.json`
  `N_u`).
- L_max = 3 N_u² L_al, the group's aligned inductance as the deck takes it (`sim/rotor_parts_duty.py` `pick`).
- **The record:** the pick's row in `sim/pole_design_variants.json`, i.e. the 2-D solve of `sim/pole_fd2d.py` ×
  (1 + K_END), with K_END_A 0.03 aligned and K_END_U 0.30 unaligned (`sim/pole_fd2d.py` line 26, [RH: SRM practice]).
- **Aiding:** a group's three coils connected so that they circulate the same way round the machine's axis (identical
  copies, connected alike). **One reversed:** one of the three connected the other way.

## 1. The model and its gates

**The utron and its neighbours** (`sim/utron_profile.spec` of the pick; the section is `sim/pole_fd2d.Design`'s):

| input | value | source |
|:--|:--|:--|
| gap, gap radius | 0.5 mm at r_g 130 mm | `sim/pole_design_variants_op.json` (design) |
| U-core | tips 14 mm, slot 30 × 30 mm, back iron 14 mm, width 58 mm, stack 100 mm; M235-35A, linear | `sim/utron_profile.spec` (w_p, s, d, b, W_u, L) |
| iron's μ_r | 3000 as the record; 4000 and 1e5 (the μ → ∞ limit) | `sim/pole_fd2d.py` `MUR_FE` |
| bridges | 6 per side at 60°: 58 × 14 mm (25.46° of r 130.5–144.5 mm), over the stack's length | `sim/utron_profile.spec` (l_b, t_b, br_deg); `sim/stack_sizing.py` `_wound_section` |
| winding | 28 × 27 mm per side (± 14 mm across), 1 mm clear of the iron; end turns rounded, R 1 inside and R 28 outside; 200 turns | `sim/utron_profile.coil_ring`, `spec` (cv, h_c, over) |
| neighbours | 3 utrons per side at 0 / 120 / 240°, the 6 bridges | `sim/pole-design-findings.md` §8 |
| everything else | non-magnetic: the shaft (`presets/hub-locked.json` shaft, "magnetic": false), the G10 cheeks, carrier discs, slot cover, bridge ring and cage | `sim/utron_profile.py`; `sim/tube_geometry.py --rel wound` |
| the deck | the pick's Ψs 0.1336 Wb-turns, La / Lb 0.6 L_max, Si diodes, 30 % seed, 60 cycles at 120 Hz; AH r160 (160 turns, 1.01 mH, 0.27 Ω); bypass 22 mF + 10 mΩ | `sim/rotor_parts_duty.py` lines 33, 51–55; `sim/magnetic_doubler.py` `AH`; `sim/ah_steady_cusp.py` |
