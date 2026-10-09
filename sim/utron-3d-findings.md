# The utrons' κ in 3-D, and what it does to the pump — findings

**Source:** `sim/utron_3d.py` → `sim/utron_3d_results.json`; figure `docs/figures/utron-3d.png` (the same script).
The run took 34 min on 4 processes (2028 s), reusing its own cache of solves.

**Status:**
- [OC] magnetostatics, and the series coils' coupling round the axis (Ampère);
- [IR] the finite-volume model, its frames, the iron's linear μ_r and the deck's inputs;
- [RH] nothing new; the record's own [RH] end corrections (K_END) are what this replaces.
- It answers the ledger's model check 34, "the utrons' κ in 3-D" (`docs/ledger/DCCREG-design-ledger.md` §6).

**Naming:**
- κ = L_al / L_un of one utron; L / N² is per turn squared; "per coil" is × 200² (`sim/pole_design_variants_op.json`
  `N_u`).
- L_max = 3 N_u² L_al, the group's aligned inductance as the deck takes it (`sim/rotor_parts_duty.py` `pick`).
- **The record:** the pick's row in `sim/pole_design_variants.json`, i.e. the 2-D solve of `sim/pole_fd2d.py` ×
  (1 + K_END), with K_END_A 0.03 aligned and K_END_U 0.30 unaligned (`sim/pole_fd2d.py` line 26, [RH: SRM practice]).
- **Aiding:** a group's three coils connected so that they circulate the same way round the machine's axis (identical
  copies, connected alike). **One reversed:** one of the three connected the other way.

## Headline
- **The utrons' κ is 6.7 in 3-D, not 8.6** [OC law, IR model].
  - The record's 2-D section with an [RH] end correction (+3 % aligned, +30 % unaligned) under-counts the stack's ends.
  - In 3-D they add +5.85 % aligned and +71.3 % unaligned: each end is worth about 3 mm of extra stack aligned and
    36 mm unaligned.
  - So L_al is 83.3 mH per coil (the record's 81.0) and L_un 12.4 mH (9.43): κ 6.70, −22 %.
- **The three series coils of a group also couple round the machine** [OC], which the record's 2-D walls exclude.
  - Wound as identical copies and connected alike, they put 3 N I round the axis, and the flux that drives links all
    three coils.
  - In the machine's cylinder that makes κ 5.96 with the coils aiding, and 6.44 with one of the three reversed.
  - **The record does not say how the three coils are connected: that is the designer's.** One reversed is the better
    choice; with three coils the coupling cannot be cancelled.
- **The pump is weaker than the record** (the record's own deck with each utron set; the pick's Ψs held):

| utron set | κ | z_lin | z_early, no bypass / 22 mF | AH, no bypass: range (mean) | AH with the bypass: range (mean) | belt, no bypass / 22 mF |
|:--|--:|--:|:--|:--|:--|:--|
| the record | 8.59 | 1.208 | 1.139 / 1.147 | 139–449 (290) | 290–308 (300) | 17.6 / 18.1 W |
| 3-D, the record's frame | 6.70 | 1.171 | 1.084 / 1.091 | 112–353 (238) | 237–251 (245) | 12.0 / 12.3 W |
| 3-D, cylinder, one coil reversed | 6.44 | 1.167 | 1.077 / 1.084 | 108–341 (228) | 229–242 (236) | 11.3 / 11.6 W |
| 3-D, cylinder, coils aiding | 5.96 | 1.158 | 1.066 / 1.072 | 102–318 (212) | 214–227 (221) | 9.9 / 10.2 W |

- **What it changes in the record:**
  - **the pick fails its own selection rule:** z_lin ≥ 1.20 (`sim/pole-design-findings.md`:29; the pick's 1.208).
    In 3-D it is 1.16–1.17;
  - **the AH's steady field falls from 300 to 221–245 A-turns** with the bypass, so the null's gradient falls from
    0.113 to 0.083–0.092 T/m (0.377 mT/m per A-turn, `sim/ah-null-findings.md`);
  - the belt pays 10–12 W instead of 18;
  - the start: the kick threshold and the speeds of `sim/parts-first-cut-findings.md` §3 were found with the record's
    utrons, and a lower z_early starts harder. Not re-run here.
- **What would restore 450 A-turns** at the peak: Ψs × 1.27 (the record's frame), × 1.32 (one reversed) or × 1.42
  (aiding), a neck of about 3.8–4.3 mm of NiFe against 3.0 [IR: Ψs in proportion to the neck]. The utrons' copper loss
  rises as Ψs² (`sim/pole-design-findings.md` §3), so about × 1.6–2.0.
- **Or a longer stack:** the ends' share is fixed per end, so κ recovers with the stack's length: about 7.8 at 150 mm
  and 8.4 at 200 mm in the record's frame (this study's per-length and end values, linear in the stack) [IR]. That is
  a different utron: the designer's.

## 1. The model and its gates
**The solver** [IR]: node-based finite volumes for H = T − ∇Ω, with pyamg and conjugate gradients.
- The coil enters as its current vector potential T (its real section and rounded end turns) through exact edge
  integrals. In the iron T is then an exact discrete gradient, so there is no reduced-potential cancellation [OC].
- This scheme converges from above; the record's A_z solve (`sim/pole_fd2d.py`) converges from below.
- The iron is linear, μ_r 3000 as the record's (4000 and 1e5 as sensitivities).
- **Two frames:**
  - the record's unrolled frame: the `pole_fd2d.Design` section extruded over the 100 mm stack, its walls 40 mm out;
  - the machine's cylinder, r 12.5–260 mm: parallel-sided tips and the flat back iron on the grid, the gap and the
    bridges conformal. All three utrons and six bridges are in every model.

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
| the deck | the pick's Ψs 0.1336 Wb-turns, La / Lb 0.6 L_max, the deck's diodes, 30 % seed, 60 cycles at 120 Hz; AH r160 (160 turns, 1.01 mH, 0.27 Ω); bypass 22 mF + 10 mΩ | `sim/rotor_parts_duty.py` lines 33, 51–55; `sim/magnetic_doubler.py` `AH`; `sim/ah_steady_cusp.py` |

**The gates:**

| gate | the check | result |
|:--|:--|:--|
| G-DECK | the record's deck, run through `sim/ah_steady_cusp.run`, reproduces the record | exact: z_early 1.1394 / 1.1466, 139–449 / 290–308 A-turns, 17.58 / 18.13 W |
| G-SOL | a long solenoid against its discrete and continuous closed forms | discrete exact; continuous +0.63 → +0.13 % at h 2 → 0.5 mm |
| G-AIR | the winding alone in a 0.6 m box against an independent Neumann integral (0.0708 µH) | 0.07177–0.07179 µH, +1.4 % [IR: within 2 %] |
| G-2D | the scalar 2-D at h 0.35 mm (from above) and `pole_fd2d` refined (from below) | they bracket the aligned 2-D value at 1.974–1.992 µH; `pole_fd2d` at its own mesh, 1.9666 µH, sits 0.4 % under the bracket. Unaligned 0.1819–0.1824 µH, `pole_fd2d` 0.1814 |
| G-2D, the walls | the no-coupling ("alternating") model against the record's A = 0 walls | 0.99992 aligned, 0.99919 unaligned |
| G-CCORE | the record's gapped-core self-check against the two-gap analytic value | 1.2165 × (`pole_fd2d` 1.2052 ×; the record quotes 1.21) |
| G-MESH | h 2 / 1.4 / 1.0 mm | the 3-D / 2-D ratios move ≤ 0.06 %: 1.0577 → 1.0583 → 1.0585 aligned, 1.7146 → 1.7139 → 1.7134 unaligned |
| G-LONG | stacks of 100, 300 and 600 mm against the 2-D per-length L | the slope matches to 0.02 % aligned and 0.7 % unaligned; the intercepts (both ends) 0.122 / 0.140 µH |
| the cylinder's split | self + 2 × mutual against the separate aiding solve | closes to −8e-13 / 2e-5 µH |

## 2. The record's frame: the stack's ends
At h 1.0 mm:

| | 3-D | 2-D, the same mesh | 3-D / 2-D | the record's (1 + K_END) |
|:--|--:|--:|--:|--:|
| aligned | 2.12634 µH | 2.00884 µH | 1.0585 | 1.03 |
| unaligned | 0.31252 µH | 0.18240 µH | 1.7134 | 1.30 |

- **The ratio is applied to the record's own 2-D values** (`pole_fd2d`, 1.96665 / 0.181386 µH), so the 2-D
  discretisation cancels:

| | the record | 3-D | change |
|:--|--:|--:|--:|
| L_al per turn² (per coil) | 2.0256 µH (81.0 mH) | 2.0817 µH (83.3 mH) | +2.8 % |
| L_un per turn² (per coil) | 0.2358 µH (9.43 mH) | 0.3108 µH (12.43 mH) | +32 % |
| κ | 8.59 | 6.70 | −22 % |
| L_max (the group) | 0.2431 H | 0.2498 H | +2.8 % |
| τ | 0.1395 s | 0.1434 s | |

- **Where the extra flux is linked:** almost all within the stack's length (beyond it 0.0019 / −0.0018 µH). So the ends
  are one total; a split into end turns and fringing would mean nothing here.
- **Over the cycle** the 3-D / 2-D ratio rises from 1.058 aligned to 1.431 at 10° and 1.740 at 20° (`k_theta`), so the
  whole profile L(θ) flattens toward its unaligned end (Figure (a)).
- **Sensitivities:** μ_r 4000 moves the aligned L +1.4 % in 3-D and in 2-D alike, so the ratio holds; μ → ∞ +5.7 %.
  The far wall moves it ≤ 0.3 %. The record's walls 40 mm further out move the unaligned L +5 % in 3-D (+11 % in 2-D):
  the unaligned flux reaches the walls.

## 3. The coupling round the machine
- **Why** [OC]: the three utrons of a group are in series. As identical coils connected alike, their MMFs add round the
  axis, 3 N I through the ring of the three. The flux this drives circulates round the machine and links all three.
  `pole_fd2d`'s walls (A = 0 above and below) set the net circumferential flux to zero and so exclude it.

| model | aligned, coupled / uncoupled | unaligned, coupled / uncoupled |
|:--|--:|--:|
| 2-D, unrolled | 1.0115 | 1.293 |
| 3-D, unrolled, h 2 mm | 1.007 | 1.112 |
| 3-D, the cylinder, h 1.4 mm | 1.0090 | 1.1128 |

- **The cylinder's split** (h 1.4 mm): self 2.1572 / 0.3347 µH, mutual between two utrons 0.0056 / 0.0108 µH.
  - Aiding, the group sees 3 L_self + 6 M: 2.1685 / 0.3563 µH per utron, κ 5.96.
  - One reversed, 3 L_self − 2 M: 2.1534 / 0.3275 µH, κ 6.44.
- **The cylinder's own geometry** (no coupling) against the unrolled frame: 0.9998 aligned, 1.019 unaligned.

## 4. The pump
- **The deck** (`sim/rotor_parts_duty.py`'s, through `sim/ah_steady_cusp.run`): each utron set's L(θ) is the record's
  2-D L(θ) × the 3-D ratio k(θ), interpolated over the angles solved (0, 2.5, 5, 7.5, 10, 15, 20, 30°) [IR]. Ψs is
  held at the pick's 0.1336 Wb-turns; La / Lb, the wiring stray and the snubbers follow the deck's own scaling with
  L_max.
- **The results** are the headline's table. Holding La / Lb at the record's 0.146 H instead (the coils aiding):
  z_early 1.064 / 1.070, AH 102–317 (212) / 213–226 (220): the same.
- **Why the AH falls more than κ:** the gain per cycle falls with κ, so the pump settles lower on the neck's
  saturation curve [IR: the deck's own law, i = Ψ / L (1 + (Ψ / Ψs)⁶)].

## 5. What contradicts the records
- `sim/pole_fd2d.py`:26, K_END_U 0.30 and K_END_A 0.03 [RH]: 0.713 and 0.0585 in 3-D.
- `sim/pole_fd2d.py`:9, "A = 0 far above and below": it excludes the coils' coupling round the machine.
- κ 8.6 and 81 / 9.4 mH per coil: `sim/pole-design-findings.md`:359 and the ledger §1, §3.2 and §4. In 3-D: κ 6.70
  and 83.3 / 12.4 mH (the record's frame), 5.96 / 6.44 in the cylinder (aiding / one reversed).
- `sim/pole-design-findings.md`:48–49, "mesh converged to 0.5 %": `pole_fd2d` at its own mesh sits 0.4 % under the
  bracketed 2-D aligned value, and its uniform x-grid moves the unaligned L +1.5 % at a non-commensurate hx 0.35 mm.
- `sim/pole-design-findings.md`:423–424, the end corrections' caveat and the 3-D check it calls due: done here; the
  corrections are 2× (aligned) and 2.4× (unaligned) the record's.
- **The pick's selection rule,** z_lin ≥ 1.20 (`sim/pole-design-findings.md`:29; the ledger §3.2): 1.16–1.17 in 3-D.
- **The AH's steady field,** 290–308 A-turns with the bypass (the ledger §3.3, §4; `sim/ah-steady-cusp-findings.md`):
  221–245 in 3-D. The null's gradient follows it.

## Caveats
- **[IR] the record's solid U-core section:** no NiFe neck strip, no 12 mm break, no stud holes (the neck is model check
  31). The iron is linear and the solve magnetostatic: no eddy currents.
- **[IR] free space beyond the reluctance section;** the cylinder flux-tight at r 12.5 and 260 mm. Cells that carry
  winding current are air.
- **[IR] the deck's L(θ)** is the record's 2-D profile scaled by the 3-D ratio, not a 3-D solve at every angle.
- **[IR] Ψs held:** the neck's saturation in the 3-D field is model check 31's (the nonlinear neck).
- **Not re-run:** the start (the kick's threshold and speeds), the utrons' heat at the new operating point, and the
  variant screen of `sim/pole_design.py` with the 3-D corrections.
