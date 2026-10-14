# de Queiroz's segment-matrix solver — checked, and a basis for future solvers

**Source:** `sim/queiroz_matrix.py` → `sim/queiroz_matrix_results.json`. Every number below is from the results file
unless another file is named. The paper is
`docs/reference/deQueiroz-2019-analysis-electronic-electrostatic-generators.pdf`, the author's manuscript; its
provenance is in `docs/reference/README.md`.

**Status:** a theory check. It changes no design value and no frozen file. The circuit is the repo's electrostatic
core, which is the paper's Fig. 1 with every diode reversed (ledger §3, "The doubler").

## Headline

**The paper's method and numbers reproduce to 6 digits, by two independent routes.** [OC]
- The two routes:
  1. the paper's closed forms, transcribed from the PDF;
  2. an ideal-diode charge-conservation solver that needs no segment order.
- **Three corrections to how the paper is read.** One concerns the paper's own print; two concern the repo's reading
  of it.

| | the paper prints | this check | |
|:--|:--|:--|:--|
| Fig. 3, √z (eq. 13) | 0.808875 / −1.15155 | eq. 12: 0.808875 / −1.151555; eig(M of eq. 11): the same; solver: z 1.326078 → √z 1.151555 | ✔ |
| Fig. 3, e41/e11 (text after eq. 13) | −1.38254 | M's eigenvector −1.382539; solver −1.38254 | ✔ (eq. 14 as printed gives **+**1.38254: a sign slip) |
| Fig. 1, √z (after eq. 23) | 1.17138 | eq. 21 + Newton: 1.171396; solver, power iteration: 1.171396; solver, Newton: 1.171394 | ✔ to 1.4 × 10⁻⁵ |
| Fig. 1, a = e21/e11 | 0.159674 | 0.159674 / 0.159672 / 0.159660 | ✔ |
| Fig. 1, b = e41/e11 | 2.24117 | 2.24117 / 2.24118 / 2.24119 | ✔ |
| Fig. 6, predicted z | 1.1538 | z per cycle 1.15378 with C1 and C2 at 142–442 pF (60–360 + 82 pF probe), Ca = Cb = 330 pF | ✔ |

## Findings

1. **The paper's z is per cycle; √z is the half-cycle factor.** [OC: the PDF, eqs. 3, 5 and 15]
   - Fig. 1: √z = 1.171396 per half cycle, so z = **1.372170** per cycle.
   - The paper's 1.17138 is √z. `sim/queiroz_fig1_check.py` has the right numbers but calls the half-cycle factor
     "z".
   - ngspice gives 1.372052 with the paper's diodes and 1.372001 with the repo's (`sim/queiroz_fig1_check_results.json`).
     That is 0.009 % / 0.012 % under the ideal limit: the cost of the near-ideal diode model [IR].
2. **The 1.1538 is the paper's Fig. 6 experiment, not the α = 6, β = 5.5 case.** [OC: the PDF, text under eq. 23;
   this run]
   - The prediction is z per cycle with the 82 pF probe dividers on nodes 1 and 4: C1 and C2 at 142–442 pF,
     α 3.113, β 2.324, z 1.15378.
   - `xsim_queiroz_matrix.py` targeted 1.1538 at α = 6, β = 5.5. That is why it stayed `V0-SECONDARY-OPEN`: no
     correct solver could hit it.
   - The paper measured ≈ 1.08 and attributes the gap to losses and distributed capacitance.
   - [RH] Adding the probe to C_min only (142–360 pF) gives z 1.0801. This is a coincidence of interest, not an
     explanation.
3. **Eq. 14 as printed has an overall sign slip.** [OC]
   - Its "+" root evaluates to +1.38254 and its "−" root to −2.34112. The true eigenvector ratios of eq. 11's M are
     −1.38254 (for √z −1.151555) and +2.34112 (for 0.808875).
   - So the correct form is e41/e11 = (αβ + β + 2 ∓ √D) / (2(β + 1)²). The text's −1.38254 is right; only the
     printed formula is off.
4. **The printed √z 1.17138 sits 1.6 × 10⁻⁵ under the converged value.** [OC]
   - Two independent routes agree at 1.171396, and the same Newton converges to 10⁻¹⁶ from the paper's start
     [1 2 3]ᵀ in 6 steps.
   - a and b agree to all printed digits. The likely cause is a slip in the printed √z; it is immaterial to every
     use in the repo.
5. **Eqs. 19 and 21 are transcribed correctly.** [OC]
   - At an arbitrary probe point (1, 0.3, 2), not on the eigenvector, eq. 21 and the stepped half cycle agree to
     2 × 10⁻⁶. That is the stepper's discretisation, so the closed form holds off the eigenvector too.
   - Eq. 19 at the eigenvector gives C2x = 1.806 C_min, inside [1, α].
6. **The diode sequence matches the paper's segments** [OC: the solver's trace over one half cycle from phase 1, with
   C1 shrinking]:

   | segment | s from | conducting |
   |:--|:--|:--|
   | phase 1 → x | 0 | none |
   | x → y | 0.161 | D2 |
   | y → phase 2 | 0.542 | D4 (D2 hands off within one step) |

   - D1 never conducts in the half cycle. That is the paper's "D1 does not conduct", and the reason the map stays
     nonlinear (eqs. 18–21).
   - Phase 2 mirrors phase 1: e22 / e11 = e32 / e21 = e12 / e41 = 1.17140 (eq. 15).
7. **The repo's polarity is the same machine.** [OC] Reversing all four diodes and the seed gives z 1.372165 at the
   same step count as the paper's polarity.
8. **Fig. 3's map is exactly linear.** The solver's z does not move between 500 and 2000 steps a half cycle
   (1.3260778834). Fig. 1's converges from 1.372119 (500) to 1.372165 (2000) to 1.372169 (8000). Its D2 → D4
   hand-off falls inside a step, so the stepper resolves it only to O(Δ²) [OC].

## The method, for future solvers

**What the paper's method is** [OC: the PDF, §II]:
- Ideal diodes split the cycle into **segments** of fixed conduction state.
- In each segment, the charge of every cluster of diode-tied nodes is conserved: C_i e_i = C_{i+1} e_{i+1} (eq. 1),
  with the segment's ties and annulations as constraints.
- The segments compose into one map per period (or per half period, under the nodes' symmetry).
- If the map is linear (Fig. 3), z is an eigenvalue of M and the eigenvector gives the voltage ratios.
- If a diode stays off at a capacitance extreme (Fig. 1), products of unknown C and e survive. The map is then only
  positively homogeneous, and the generalised eigenproblem F([1 a b]) = √z [1 a b] is solved by Newton (eqs. 22–23).

**Its limits**, as the paper states them:
- The segment order must be known beforehand, from a simulation.
- The closed forms are circuit-specific and grow fast (eq. 21).
- The method "was known to fail" with some parasitic capacitances in Bennet's doubler.
- Diode drops make z depend on amplitude, so the startup analysis assumes ideal diodes.
- The steady-state version (§II.B, eq. 4) is described but "detailed in another publication".

**The generalisation in `sim/queiroz_matrix.py`** [OC: standard complementarity mechanics; IR: the choice of
formulation]:
1. **State:** node voltages v. **Stepping:** move the capacitances from s to s + Δ.
   - Carry the node charges: Q = K(s) v.
   - Solve K(s + Δ) v' = Q + B q, where B is the diode incidence matrix.
2. **Ideal diodes are an LCP:**
   - w = Bᵀ v' ≥ 0 (reverse bias), q ≥ 0 (forward charge), q · w = 0;
   - P = Bᵀ K⁻¹ B is positive semidefinite, so v' is unique.
   - Four diodes means 16 active sets. The solver tries the previous set first, and enumeration is cheap.
3. **Within a segment the step is exact.** The tied cluster's charge depends only on the end capacitances. The only
   error is a diode that turns off inside a step, and it is O(Δ²).
4. **z** comes either from power iteration over whole cycles, which finds the growing mode, or from Newton on the
   numerical half-cycle map (the paper's eq. 22 with F computed, not derived). Both need no segment order and no
   closed form.
5. **What carries over to the tube:**
   - extra nodes and strays are rows in K;
   - the clamps (Z1 / Z4) are diodes with an offset, w = Bᵀ v + V_z ≥ 0;
   - the rings' chains are more diodes and capacitors in the same LCP;
   - a real diode's drop is an offset of the same kind, and makes z amplitude-dependent, as the paper warns;
   - the steady state (§II.B) is a fixed point e_{k+1} = e_k with a charge vector Q added, solved by the same
     Newton.
6. **The caveat on startup modes:** the map has more than one mode. Fig. 3's M has √z 0.808875 besides −1.151555.
   A seed that excites only a decaying mode does not start in the ideal model. ngspice showed this for Fig. 1 when
   every node is seeded alike (z 0.806, `sim/queiroz_fig1_check.py`). Power iteration from a generic seed finds the
   growing mode; a solver should report the seed it used.

## What this does not cover

- **The frozen engine.** `reference/doubler_core.py` and `shuttle_core.py` model the disc spark-gap machine, a
  different circuit. They are not compared here.
- **The tube as built.** This check uses the paper's capacitances, not the tube's (C1 / C2, Ca / Cb 451 pF, strays,
  clamps, chains: `sim/core_field.py`). Applying the generalised solver to the tube's netlist is the next step, if
  the designer wants it.
- **The steady-state analysis (§II.B).** The paper defers it; it is not implemented here.
