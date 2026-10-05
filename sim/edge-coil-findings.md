# Edge-driven coil — findings (BRIEF_EDGE_DRIVEN_COIL)

2026-10-05, Brussels time (CEST). Model `sim/edge_coil.py`; results `sim/edge_coil_results.json`; raw per-turn
currents and node voltages for every run in `sim/edge_coil_raw/*.npz`. Pre-registration
`sim/edge-coil-predictions.md`: commit 9b64a58 (04:11:59) and its addendum, commit 80401e2 (04:18:58). The
addendum's own text says "04:40"; that is a typo, and the git time is authoritative. The registered run is commit
3f46ef7 (04:26:43). Disclosure: before writing the addendum's readout definitions I had seen one smoke-test
waveform of the μ = 1 coil (a machinery check). The definitions were not tuned to it; §3 shows they in fact fail
on it.

Everything rests on assumed values for O-1…O-4 (predictions §A):
- an anti-Helmholtz pair on Ø20 × 70 mm MnZn rods, 20 mm gap;
- 40 turns of Ø0.5 mm Cu per coil, pitch 1.5 mm, on a 1 mm PTFE former;
- a grounded can at r = 40 mm;
- MnZn: ρ 5 Ω·m, Debye μ (μi 2300, f_r 1.5 MHz);
- t_r = 2 ns.

TMD's numbers go into `GEOM`, and the same commands re-run everything.

## 1. The model (brief §4) and its gates

- One ladder section per turn. Inductance:
  - self-L μ₀a[ln(8a/r) − 2];
  - every mutual from Maxwell's elliptic form, both coils, with the winding sense as a sign;
  - the wire's internal impedance as a 16-section Foster R–L network (NNLS, positive);
  - the MnZn core as ΔL(ω) from an axisymmetric magnetostatic FV solve with complex μ. This is fitted per
    eigen-mode with positive residues (passive) on 22 real poles.
- Capacitance: the full Maxwell matrix of turns, rod segments and can from an axisymmetric FV electrostatic solve.
  MnZn is a resistive conductor here: 5 mm segments joined by R ∥ C.
- The field in the working volume: closed-form loop fields plus the core's increment from the same magnetostatic
  solve.
- Solver: MNA, trapezoidal rule.

| gate | result | pass |
|:--|:--|:--|
| G-ES coax C′ vs 2πε₀/ln(R/a) | +0.03 % | ✔ |
| G-ES-MESH h 0.05 → 0.035 mm (C_g, C_tt, C_turn-rod) | +0.06 %, +1.1 %, −0.5 % | ✔ (≤ 3 %) |
| G-MS FD mutual vs Maxwell (d = 1.5 / 5 / 20 mm) | +0.07 / −0.02 / +0.10 %; axis field ≤ 0.05 % | ✔ |
| G-PD inductance matrix positive definite | every run | ✔ |
| G-SKIN Foster vs Bessel Z_int, 1 kHz–3 GHz | 0.28 % | ✔ |
| G-CORE ΔL(ω) fit, 1 kHz–3 GHz | 4.0–4.2 % (3.0–3.3 % of it is the dropped modal cross terms); field transfer 0.15–0.24 % | ✔ (≤ 5 %) |
| G-SPICE the same ladder in ngspice (end-lumped C) | 0.086 % of peak terminal current | ✔ |
| G-DT halving the step (Z₀, τ, B, gradient) | −0.27 %, 0, +0.001 %, −0.007 % | ✔ |
| G-NULL static (DC) centre field, junction / odd / end feeds | 1e-14 of one coil's own (1.7 % with a 1-turn mismatch) | ✔ |

The extraction's grounded-rod limit reproduces brief §3 almost exactly (§4 below). The machinery is sound; the
surprises that follow are physics, or the readouts.

## 2. The headline physics: a floating conductive core is a second input

MnZn is a conductor at these time scales. A floating rod is capacitively tied to every turn: about 1.4 pF per turn
to the rod, against 0.5 pF turn-to-turn. Within the edge it jumps to about half the applied voltage. The grounded
far end then sees a step of the opposite sign at t = 0. Two fronts are launched, one from each end, and they meet
mid-coil (raw: `single_N40_mu1.npz`, node voltages and turn currents against time).

Consequences, each in the data:
- the terminal current shows a plateau of V/Z₀ (≈ 890 Ω), then a dip toward zero at about 15 ns, not the ×3 step
  of a shorted line;
- the largest turn-to-turn voltage sits where the fronts collide (section 22 of 40), not at the input;
- in the series pair the far end of coil B is an input too, so coil B carries current long before the wave has
  filled coil A.

Strapping the rod to the can at its far end (1 Ω, post-hoc control) removes the second front. The winding then
behaves as the textbook line of brief §3.

## 3. Verdicts — registered readouts as pre-registered, then post-hoc

The registered readouts assumed a single-ended line: 2τ is where the terminal current first exceeds 2·I_plateau,
and for TDR where the voltage drops below half. On this winding they misfire:
- the dip-and-recovery waveform trips the 2·I test on humps, giving τ(μ = 64) = 7 ns < τ(μ = 1) = 10 ns;
- the 50 Ω TDR voltage is ill-conditioned for a Z₀ of about 1.8 kΩ, since the far-end short moves it by only
  about 5 %.

The registered verdicts are reported as computed, with that flag. Next to them is a **post-hoc** readout: the
input-launched front is tracked turn by turn (straight-line fit over turns 2–10; R² ≥ 0.993 in every case used, 0.973 for MnZn at 1 ns), τ_front = N × its
slope, and Z₀ = V/I over (2t_r, 4t_r). It never replaces a registered verdict.

| | registered verdict (readout) | post-hoc, MnZn floating | post-hoc control: rod strapped | post-hoc control: dielectric (NiZn-like) rod | my prediction |
|:--|:--|:--|:--|:--|:--|
| **P-EDGE-1** line not lump | **PASS**, i(1.6τ)/i(0.4τ) 0.17 (τ misread at 10.2 ns) | INCONCLUSIVE 2.57 (τ 18.4 ns) | **PASS** 0.98 | **KILL** 4.16 | PASS |
| Z₀ against §3 | ladder 944 Ω; ideal 1841 (rod floating) / 473 (rod grounded) | 890 Ω | **466 Ω vs ideal 473 Ω** | 1908 vs 1809 | 20–50 % below ideal: ✔ against the floating ideal |
| **P-EDGE-2** β (B ∝ n^β) | **PASS** −0.18 | PASS −0.13 | PASS −0.17 | PASS +0.26 | PASS, 0.1–0.25 ✔ |
| **P-EDGE-3** γ (B ∝ μ^γ) | **INCONCLUSIVE** −0.32 (readout invalid) | INCONCLUSIVE 0.18 | INCONCLUSIVE 0.17 | INCONCLUSIVE 0.16 | inconclusive 0.2–0.35 ✔ (slightly below) |
| γ against the ladder's DC μ_eff | −0.40 | 0.35 | 0.32 | 0.31 | 0.4–0.6 ✘ |
| **P-EDGE-4** stress in first tenth | **KILL**: section 22/40, 5.2 × V₀/N; α 68 | KILL 22/40 | KILL 8/40, 7.1 × V₀/N | KILL 39/40, 3.8 × V₀/N; α 15 | PASS, α 15–40 ✘ |
| **P-EDGE-5** end-fed: coil B < 10 % over (0, τ₁) | **KILL**: B/A 0.96 | KILL 0.86 | KILL 0.42 | KILL 0.28 | narrow PASS ✘ |
| P-EDGE-5 symmetric (junction) feed < 10 % | PASS 2e-7 (by symmetry) | PASS 2e-7 | — | — | trivial PASS ✔ |
| odd-mode feed / junction with a 1-turn mismatch | 3e-7 / **0.053** | 0.053 | — | — | mismatch breaks it ✘ |
| **P-EDGE-7** (ladder) rod raises C_seen more than L_seen | KILL (readout invalid: L ×1.5e11, C ×5e-11) | **PASS**: C ×3.11, L ×2.43 | — | — | PASS, C ×3–10 ✔, L ≤ ×1.5 ✘ |

**P-EDGE-5 overall: KILL.** The end-fed series pair has no null during the flank, in every rod variant, so the
brief's §8.2 conclusion stands, and more strongly than it argued. Coil B is reached early: by mutual induction and
the inter-coil capacitance, and with a floating rod also by the second front from its own grounded end. The junction
and odd-mode feeds hold the null to the matching: 1 missing turn of 40 leaves 5.3 % during the flank and 1.7 % static.

What the post-hoc numbers say about §3 (brief) on this winding:
- **Turn density cancels:** |β| ≤ 0.26 in every variant. ✔
- **Field per volt:** with the rod strapped, the fill-time field is 1.72 µT/V against §3's
  B = V√(μ₀C′/A) = 1.77 µT/V. ✔ (3 %)
- **The core counts much less than √μ_eff(DC):** B(μ = 64)/B(μ = 1) = 2.1 against √9.0 = 3.0. The front is short on
  the rod's scale, so it sees a smaller, locally demagnetised μ_eff.
- **τ barely grows with μ** (τ ∝ μ^0.07–0.10), while Z₀ ∝ μ^0.17–0.35.
- **The input-turn stress of §1 needs t_r ≲ τ_turn.** At 2 ns (t_r/τ_turn ≈ 4) the initial distribution is already
  washed out. At t_r = 0.5 ns (MnZn floating) the maximum moves to section 2 of 40, at 14.5 × V₀/N (363 V per kV).
  P-EDGE-4's kill stands as registered.

## 4. Regime ratios (brief §5)

| case | t_r | τ (front) | t_r/τ | t_r/τ_turn | regime |
|:--|:--|:--|:--|:--|:--|
| MnZn floating | 1 ns | 25.2 ns | 0.040 | 1.6 | ladder |
| MnZn floating | 2 ns | 25.6 ns | 0.078 | 3.1 | ladder |
| MnZn floating | 5 ns | 37.7 ns | 0.13 | 5.3 | ladder |
| MnZn floating | 0.5 ns | (front fit invalid, R² 0.23) | — | ~1–2 | ladder; full-wave check advised |
| μ = 1 | 0.5 / 1 / 2 / 5 ns | 15.4 / 15.7 / 18.4 / 23.3 ns | 0.03–0.21 | 1.3 / 2.6 / 4.4 / 8.6 | ladder |

Lumped would need t_r ≥ 10 τ, about 250–380 ns for this winding. Every run's ratios (registered τ) are in the
results file under `regime.per_run`. The line is itself dispersive: τ_front rises with t_r even at μ = 1, because
the inter-turn capacitance carries a fast precursor. The MnZn Debye core adds a factor of 1.4–1.6: μ″ of about 340 at 10 MHz and
70 at 50 MHz acts as series impedance.

## 5. P-EDGE-6 — ladder values registered for the bench (per volt of source)

The registered 50 Ω TDR readout returned Z₀ = 1e14 Ω (the ill-conditioning above). The values registered here for
the bench use the post-hoc front readout, stated as such, before any bench data:

| quantity | ladder value |
|:--|:--|
| TDR (50 Ω) on one coil with its MnZn rod: Z₀ / τ | **1786 Ω / 26.1 ns** (read through the current) |
| same coil without its rod: Z₀ / τ | 2057 Ω / 9.3 ns |
| ideal step: Z₀ / τ | 1810 Ω / 25.6 ns |
| peak B_z at the coil centre: Z_s = 0, fill (0, 1.5τ) / whole record | 3.50 / 9.92 µT per V |
| same, Z_s = 50 Ω | 3.40 / 6.61 µT per V (coil accepts 94 % of the source energy over the fill) |
| peak gradient at the pair centre, junction feed: Z_s = 0, fill / record | 27.3 / 160 µT/m per V |
| same, Z_s = 50 Ω | 25.2 / 150 µT/m per V |
| objective (§3/§7), junction feed: gradient per √J over the fill | 5.85 T/m per √J (odd 5.15, end-fed 4.61) |

At a 10 kV edge, then: about 0.27 T/m at the centre during the fill, and 1.6 T/m in the ring that follows (O-3
decides which window counts).

## 6. Design consequences (for O-1…O-4)

1. **Feed (O-2):** junction feed or odd-mode drive; never the end-fed series pair. The coils need the same
   handedness for junction feed and mirror handedness for odd-mode; the static check confirms both.
2. **The rod:**
   - A floating MnZn rod turns the grounded end into a second input and puts the stress peak mid-coil.
   - Strapping each rod to the return (or to the coil's grounded end) restores a clean line.
   - The strap also roughly halves Z₀ (≈ 466 Ω), which matters for matching to the driver's Z_s.
   - The strap removes the far-end launch but raises the peak section stress (7.1 × V₀/N at 2 ns).
3. **Insulation (O-4):** across one turn's insulation, the peak during the fill is 130–180 V per kV at 2 ns and
   about 360 V per kV at 0.5 ns. At a 10 kV edge that is 1.3–3.6 kV turn to turn. The winding insulation rating has
   to be set against these numbers; an enamelled Ø0.5 mm wire will not hold them.
4. **NiZn (dielectric) rod:** no second front, but the return is then the can at 40 mm. The coil behaves more like a
   lump (P-EDGE-1 kill, flat 4.2), with the stress at the far end.

## 7. Not done / open

- **§7 compact terminal model (vector fit) for the DCCREG/RAPT netlists:** waits on a chosen design (O-1…O-4). The
  ladder stays the design tool, and `Ladder.spice_deck` already exports the full ladder to ngspice.
- **Full-wave (openEMS) check:** advised only if t_r falls to about τ_turn (≈ 0.2–0.6 ns here). openEMS is not
  installed in this environment.
- **Assumptions to replace:**
  - MnZn: ρ, bulk ε and the Debye μ(f), to be swapped for the datasheet's μ′/μ″;
  - the can's magnetic transparency;
  - the half-to-each-end mapping of a turn's charge (the end-lumped variant is in G-SPICE).
- **P-EDGE-6/7 bench verdicts:** TMD's.
