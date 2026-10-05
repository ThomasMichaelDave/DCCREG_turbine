# Electromagnet register — pre-registration (BRIEF_ELECTROMAGNET_REGISTER r0.3)

Committed before any register run. The git commit time is authoritative. The brief's own P-REG-1…9 stand as
registered by the brief, verbatim. This file adds my expectations, the readout definitions and the modelling
choices. Nothing here is edited after a run; outcomes go in `sim/em-register-findings.md`.

Data: `presets/electromagnets-RA.json` (integrated first, D-1) and `presets/electromagnets-V15.json` (regression).
Tags: [OC] / [IR] / [RH] / [ME].

## A. Modelling choices for the RA hub ladder (axisymmetric about the spin axis) [IR]

- **Side A** (top) at z < 0, as in the CAD frame.
- **Windings, as listed in the preset:**
  - L_TC/L_BC: 34-turn conical stacks.
  - AH: 2 × 25 (a), 3 × 17 (b) or 2 × 18 (c). Layer-j centre radius 8.25 + 0.8 + 1.6 j mm; pitch 1.60 mm; layer 1
    enters at the apex end.
  - Circulation = hand × axial direction of layer 1's traversal, and constant through the layers.
  - Even layer counts get a straight axial return lead beside the outer layer: segmented L, capacitance to the
    turns it passes, zero mutual with the coaxial turns [OC].
- **Leads:**
  - L_TC top turn → AH apex end: a 20 mm lead.
  - The join: a 70 mm lead routed around the vessel.
- **Rods:** conductors (5 mm segments, R ∥ C), tied to the join node through 1 Ω. Magnetically, Debye μ (μi 2000,
  f_r 2.5 MHz) [RH].
- **Returns and dielectrics (no can):**
  - C_R electrodes on the septum faces (|z| 6–7). The annulus inner radius is 30 mm and the outer radius is sized to
    789 pF across 12 mm garolite (εr 4.8).
  - Septum, hub shell (5 mm garolite), G-10 former, Ø27 bore tube.
  - Shafts (R-A/R-B, Ø30 from the tip), with the shaft tip and a PEEK sleeve in the rod bore.
  - Vessel: glass sphere, εr 4.6 [RH].
  - Sphere seat: PEEK, |z| 26–30.7.
- **Stator side, bracketed:**
  - (i) node-1/node-4 foils at the il2f positions as full annuli, r ≥ 95, with the rotor C1/C2 faces (R-A/R-B) at
    |z| 27.25–28.25, r ≥ 95. The il2f r_in of 75 collides with L_TC; that is reported in G-CLR-HUB.
  - (ii) no stator foils.
  - Both inside the stator frame as a far grounded boundary (r 560, |z| 200).
  - Full annuli overstate the 22°/30° sector couplings by about 2–3×.
- **Turns that collide with the septum or electrode** (L_TC k = 0, 1: |z| 4.0 and 6.4 with r_cond 1.5) are dropped
  from the ladder chain, and the electrode is the chain's start. The loop sum (P-REG-2) uses all 34 as drawn.
- **Capacitance:**
  - Electrostatic FV with h 0.15 mm in the hub band. AH conductors are represented at radius 0.5 mm in the field
    solve.
  - The partials between touching neighbours are replaced by the Massarini–Kazimierczuk enamelled-wire formula
    (adjacent same-layer turns, and radially facing adjacent-layer turns).
  - Bare capillaries: the two-wire formula (π ε₀/acosh(d/2a) per metre). The capacitance to everything else is
    kept.
  - Gate G-ENAMEL: a fine planar FD of two touching enamelled wires against the formula, ≤ 15 %.
- **Edge (SG1 fire):** R-A is driven by an ideal step (Z_s = 0) against the stator conductors (ground); t_r = 2 ns,
  swept 0.5–5 ns (D-10). R-B follows through C_R and the chain.

## B. Readouts (fixed now)

- **τ (front):** I_early = median terminal current over (2 t_r, 4 t_r); a turn's arrival = the first time its
  current exceeds 0.5 I_early; τ = N × slope of a straight-line fit over the first quarter of the turns in winding
  order. Z₀ = V/I_early.
- **Bench coil** (P-EDGE-1…4, 6, 7): one AH coil (variant a unless stated) on its rod and former, far (base) end
  grounded, the rod tied to the far end, inside a grounded fixture can of r 40 mm.
  - P-EDGE-1: plateau PASS if i(1.6 τ)/i(0.4 τ) ≤ 1.5; KILL if ≥ 3.
  - P-EDGE-2: 2 layers × {10, 13, 18, 25} turns over 40 mm, μ = 1.
  - P-EDGE-3: μ ∈ {1, 4, 16, 64}. Peak |B_z| at the coil centre on the axis over (0, 1.5 τ).
  - P-EDGE-4: the section voltage |v_k − v_k+1| in winding order, max over (0, τ); first tenth = sections ≤ N/10.
    Physical-neighbour voltages (same layer and adjacent layer) are reported beside it.
  - P-EDGE-6/7: a 50 Ω TDR read through the current; P-EDGE-7 compares with the rod against without it.
- **P-REG-5:**
  - Window: flank = (0, 2 t_r + τ_AH), with τ_AH the bench-coil front τ of the same variant.
  - Ratio = max|B_TA + B_BA| / max(max|B_TA|, max|B_BA|) at the centre over the window, with all four windings
    present (contributions split by winding).
  - Prediction true (the AH pair does not null) if the ratio > 0.10. Also reported: (0, t_r), (0, 10 ns), and the
    centre field per kV including L_TC/L_BC.
- **P-REG-8:** the inductive (late-time) distribution with one uniform current through the AH coil: v_k = Σ_j L_kj i,
  turn potentials cumulative. Largest |V_i − V_j| over radially facing adjacent-layer pairs, ÷ V_AH. The ladder's
  late-time value is reported beside it.
- **P-REG-9:** N·I at equal tank voltage, I = V_ring √(C_R/L_tot), with L_tot = Re L at f₀ (all mutuals, rod μ′(f₀)).
- **G-AH-SAT:** max |B| over the rod cells at the peak ring current (15 kV on 789 pF), μ′(f₀); limit 0.30 T.
- **Core loss:** Steinmetz, 250 kW/m³ at 100 kHz/100 mT, f^1.5 B^2.6 [RH until datasheet], integrated over the rod
  at f₀.
- **T-NULL:**
  - Static AH pair alone: |B_z(0)| ≤ 1e-9 of one coil's own.
  - With all four windings: the axial offset of the B_z = 0 point nearest the centre.
- **T-MIRROR:** every hand flipped, geometry kept (for axisymmetric parts this is also the θ → −θ mirror): scalars
  equal to 1e-12, B reversed. The C-EM station set and pole map under θ → −θ are reported.
- **E-REGIME:**
  - t_r ∈ {0.5, 1, 2, 5} ns.
  - Families: AH (a, b, c) and L_TC from the ladder.
  - C-EM: §3 idealisation only. Its ladder waits on D-5/D-6.

## C. My expectations (written before the runs)

| ID | brief's prediction | I expect |
|:--|:--|:--|
| P-REG-1 | 33.8 / 8.3 / 84.1 µH | PASS (same method) |
| P-REG-2 | 98.9 / 34.7 µH | PASS: finding 1 stands |
| P-REG-3 | 1.20 MHz ± 5 % | PASS |
| P-REG-4 | 299.9 Hz; 1206 / 201 Ω; Q 30.2 | PASS |
| P-REG-5 | AH pair same way during the flank, ratio > 10 % | PASS strongly (ratio 1.3–2): C_R holds R-A/R-B together, so the drive is almost pure common mode |
| P-REG-6 | \|Δz\| ≤ 1e-3 at Q ≤ 30 | PASS; z(Q) drifts above Q ≈ 50 |
| P-REG-7 | margins (a) 1.3, (b) 2.1, (c) 0.5; radial (b) 0.45, (a)/(c) 2.0 | the bare-winding margins PASS. New: the return lead of (a)/(c) eats 1.6 mm of radial margin (≈ 0.45 mm left at the lead), and a 0.5 mm PEEK sleeve on a Ø12.3 rod (Ø13.3) does not fit the Ø13 bore |
| P-REG-8 | (a),(c) ≈ V_AH; (b) ≈ ⅔ V_AH | PASS within 25 % (end mutuals pull the values 5–15 % below) |
| P-REG-9 | N·I(c) < N·I(a) | PASS |
| L_tot / f₀ | — | (a) 0.55–0.75 mH, f₀ 210–240 kHz; (c) lower L |
| G-AH-SAT | ≤ 0.30 T | marginal: 0.25–0.4 T for (a); (c) lower |
| T-NULL | AH alone 1e-9; displaced with all four | PASS; offset several mm toward side B (the bottom L_R↔AH mutual opposes) |
| P-EDGE-1 bench (rod tied) | plateau | PASS |
| P-EDGE-2 | \|β\| < 0.3 | PASS |
| P-EDGE-3 | 0.35 < γ < 0.65 | INCONCLUSIVE (γ 0.15–0.25, the short rod's demagnetisation) |
| P-EDGE-4 | stress in the first tenth | KILL at 2 ns (t_r/τ_turn ≫ 1). Physical-neighbour voltage at the apex end ≈ 0.9–1.0 V₀ in all three variants during the flank (input turn beside a turn the wave reaches last) |
| P-EDGE-7 | C_seen raised more than L_seen | PASS |
| G-CLR-HUB | — | FAIL: the CAD stack's A/B discs and C1/C2 rotor foils sit inside the RA cone, and L_TC k = 0–1 sit in the septum/electrode |
| Phase verdicts | — | Phase 1: REGISTER-COLLISION (G-CLR-HUB), with P1-PUMP passing. Phase 2: REGISTER-COLLISION or SOURCE-CONFLICT (G-CLR-ROT/SG, F-4/F-6) |
