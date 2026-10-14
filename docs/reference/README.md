# Reference evidence

Source documents the design's theory rests on. Each is kept byte-identical as received; its checksum is below.

## `deQueiroz-2019-analysis-electronic-electrostatic-generators.pdf`

- **What:** A. C. M. de Queiroz, "Analysis of Electronic Electrostatic Generators". This is the author's manuscript
  (Word → PDF, 5 pages, "Manuscript received …"). It was published as IEEE Trans. Circuits Syst. II 66(4):632–636,
  2019. The journal citation is not printed in the file; it comes from the repo's earlier records.
- **Provenance:** the designer supplied it on 2026-10-14 from the "Electrostatic Turbine Theory" project
  (`analysis.pdf`).
- **SHA-256:** `bdd03ca67868d3fefefc1e22df1501b60ed5664383ce45225c541e997d2b9322`
- **Copyright:** © IEEE / the author. It is kept here as evidence for the design's analysis.
- **What the repo uses from it** [OC: the PDF, pages 2–4]:
  - §II.A: the segment method. For each diode-state segment, C_i e_i = C_{i+1} e_{i+1} (eq. 1). The segments compose
    into a per-period map e_{k+1} = M e_k (eq. 2), and the startup gain is the eigenvalue of M above 1 (eq. 3).
  - §II.B: steady state. The converter's charge vector Q is added to eq. 1, the operation is closed with
    e_{k+1} = e_k, and the energy is E = ½ v_lim² C_eq (eq. 4).
  - **Fig. 3, Wilson / symmetrical bipolar:**
    - C_a, C_b run complementarily from 60 to 360 pF, C1 = C2 = 330 pF (α = 6, β = 5.5);
    - the map is linear (eq. 11), with √z = 0.808875 or −1.15155 (eq. 13) and e41/e11 = −1.38254 (eq. 14).
  - **Fig. 1, symmetrical unipolar** (the repo's de Queiroz doubler):
    - C1, C2 run complementarily from 60 to 360 pF, C_a = C_b = 330 pF;
    - D1 does not conduct in the third segment, so the half-cycle map is nonlinear (eqs. 18–21);
    - the generalised eigenproblem (eq. 22) is solved by Newton–Raphson (eq. 23), giving √z = 1.17138,
      e21/e11 = 0.159674 and e41/e11 = 2.24117.
  - **Fig. 6:** the experiment, with C_min ≈ 60 + 82 pF from the probe dividers. The prediction is 1.1538 and the
    measurement ≈ 1.08.
- **Notation** [OC]: the paper's z is the per-period factor, and √z maps phase 1 to phase 2 with the nodes swapped
  (eqs. 5 and 15).
  - Fig. 1: √z = 1.17138 per half cycle, so z = 1.37213 per cycle.
  - Fig. 3: |√z| = 1.15155, so z = 1.32607.
