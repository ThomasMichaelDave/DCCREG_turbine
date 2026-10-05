# Edge-driven coil — pre-registration (BRIEF_EDGE_DRIVEN_COIL)

Written and committed **before any ladder run** (2026-10-05, 04:10 CEST). Nothing below is edited after a run; the
outcomes go in `sim/edge-coil-findings.md`, red as fully as green.

Tiers: [OC] standard physics / method · [IR] an engineering choice or assumed value · OPEN = TMD's decision (§10).

## A. Assumptions standing in for the OPEN items (O-1 … O-4)

The repository does not dimension this electromagnet anywhere (no anti-Helmholtz pair, no MnZn rod is specified in
the docs, CONVENTIONS or the netlists). Every value below is therefore an assumption, stated so that a run can be
repeated with TMD's numbers by changing one dictionary (`sim/edge_coil.py: GEOM`).

| item | assumed | tier |
|:--|:--|:--|
| O-1 magnet | anti-Helmholtz pair, two coaxial MnZn rods Ø20 × 70 mm, facing ends 20 mm apart (gap centre z = 0 is the working volume) | OPEN → [IR] |
| winding | per coil: single layer, 40 turns, Cu Ø0.5 mm, pitch 1.5 mm (60 mm long, centred on its rod), on a 1 mm PTFE former (εr 2.1); wire centres at r = 11.25 mm | [IR] |
| return / ground | grounded coaxial can, r = 40 mm, closed 20 mm beyond the rods; electrostatic return only (taken as magnetically transparent, e.g. slotted) | [IR] |
| MnZn electrical | resistive conductor (brief §8.1): ρ = 5 Ω·m, bulk εr 1·10⁴ between rod segments (5 mm segments, R ∥ C); not in contact with the winding | [IR] |
| MnZn magnetic | Debye relaxation μ(f) = 1 + (μi − 1)/(1 + j f/f_r), μi = 2300, f_r = 1.5 MHz (power-ferrite class; replace by the datasheet μ′/μ″) | [IR] |
| O-2 feed | both cases run: end-fed series (mirror handedness) and junction feed (same handedness); odd-mode reported too | OPEN → both |
| O-3 edge | t_r (10–90 %) = 2 ns at the terminals, raised-cosine edge; regime ratios also reported for 0.5, 10, 50 ns; window = first fill (0 … 1.5 τ) | OPEN → [IR] |
| O-4 target | gradient dB_z/dz at the gap centre (anti-Helmholtz), B_z at the null; insulation rating not set → peak turn-to-turn voltage reported per kV applied, not judged | OPEN |
| source | P-EDGE-1…5: ideal step, Z_s = 0 (brief §9). TDR (P-EDGE-6/7): 50 Ω source, same edge | [IR] |

## B. Model (what is extracted, and its known approximations)

- one ladder section per turn; a turn's conductor potential is the mean of its two end nodes [OC approximation];
- self-L: μ₀a[ln(8a/r) − 2] (surface current) + the internal part through a fitted Foster R–L network per turn,
  fitted (NNLS, positive elements) to the exact Bessel internal impedance of a round Cu wire, DC … 3 GHz [OC];
- mutual: Maxwell's elliptic form between every pair of turns, both coils; winding sense as a sign per turn [OC];
- capacitance: full Maxwell matrix (turns, rod segments, can = ground) from an axisymmetric finite-volume
  electrostatic solve; the rod segments are conductors (MnZn), the former is PTFE [OC method, IR geometry];
- core: the increment ΔL(ω) = M(μ(ω)) − M(μ = 1) from an axisymmetric magnetostatic (ψ = rA_φ) finite-volume solve
  with the complex μ, fitted with common real poles (positive-semidefinite residues) into the time domain; the field
  transfer to the working volume likewise [OC method];
- no retardation (quasi-static PEEC, brief §4); the regime check of §5 says when that is not enough.

Gates before any prediction run (each must pass or the run is not reported as a verdict):
G-ES coaxial capacitance vs 2πε₀/ln(R/a) (≤ 2 %); G-MS FD mutual vs Maxwell elliptic (≤ 2 %); G-PD the inductance
matrix positive definite; G-SKIN Foster fit ≤ 3 % on |Z_int| over the band; G-CORE fit ≤ 5 % on ΔL(ω); G-SPICE the
same ladder in ngspice matches this solver's terminal current ≤ 1 %; G-DT halving the step changes every reported
number ≤ 1 %; G-NULL the static (DC) solution of each pair feed shows B_z(0) ≈ 0 (≤ 1 % of one coil's own).

## C. Predictions (my expectations, written before the runs)

The brief's predictions and kill criteria are taken verbatim; below each is what I expect and why.

**P-EDGE-1 — the coil as a line.** Brief: plateau near V/Z₀, not a lumped ramp. *I expect:* PASS. The terminal current
shows a capacitive spike at the edge (inter-turn and turn-to-rod charge), then a plateau that tilts upward slightly
(long-range mutual coupling makes the helix dispersive), then a step at 2τ when the far-end reflection returns.
Plateau Z₀ reported against §3's idealised Z₀; I expect the ladder's to come out **lower** by 20–50 %, because the
idealised C′ ignores the inter-turn capacitance and the rod.

**P-EDGE-2 — turn density cancels.** n = 20, 40, 60, 80 turns over the same 60 mm, same wire, μ = 1 (rod present
electrically). *I expect:* PASS, |β| ≈ 0.1–0.25. Not exactly 0: the turn-to-rod capacitance per unit length grows
with n because more wire faces the rod, so C′ grows slowly with n and B ∝ √C′ creeps up.

**P-EDGE-3 — the core as √μ.** Rod material μ = 1, 4, 16, 64, frequency-independent, fit against those test values.
*I expect:* **inconclusive below 0.35**, γ ≈ 0.2–0.35. The rod is Ø20 × 70 mm, so its demagnetisation caps its
apparent permeability at about 10–20, and it fills only (10/11.25)² ≈ 0.79 of the winding's cross-section, so μ_eff
grows much more slowly than the material μ. Reported beside it: γ refitted against the ladder's own μ_eff
(low-frequency L(μ)/L(1)); there I expect 0.4–0.6, i.e. the √μ_eff law itself holds.

**P-EDGE-4 — input-turn stress.** *I expect:* α from the ladder's own C_g and C_s is well above 3 (≈ 15–40, the rod
dominates C_g), and the largest turn-to-turn voltage during the first fill falls in turns 1–4 of 40: PASS. Its size
against V₀/N: several times α·V₀/N is not expected; I expect 0.5–1.5 × α·coth(α)·V₀/N.

**P-EDGE-5 — the pair's null.** *End-fed series:* over (0, τ₁) coil 2 contributes < 10 % of the centre field —
I expect PASS but narrowly (5–10 %): coil 2 is reached early by mutual induction, by the capacitance across the
gap and through the rods' coupling, not by conduction. *Junction feed:* the mirror-matched model is symmetric, so
the centre field stays ≈ 0 by construction (a solver check, PASS trivially); a 1-turn mismatch case is reported,
not judged, and I expect it to break the 10 % bound during the flank. Odd-mode reported only.

**P-EDGE-6 — ladder values registered for the bench** (reported in the findings, frozen at that commit): Z₀ and τ
from a simulated 50 Ω TDR on one coil with its rod, and the peak B_z at the coil centre and the peak gradient at the
pair centre (junction feed), per volt of source, Z_s = 0 and 50 Ω.

**P-EDGE-7 — MnZn under the edge.** Simulated TDR with and without the rod. *I expect:* PASS by a wide margin — the
rod raises the capacitance seen (τ/Z₀) by ≈ 3–10× (it is a conductor 1.25 mm from the wire, against a can at 40 mm),
and the inductance seen (Z₀·τ) by ≤ 1.5× (μ′ of the Debye ferrite at the ~0.1 GHz edge content is ≈ 1.5, and μ″
shows up as loss, not inductance).
