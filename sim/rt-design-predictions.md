# Round-trip design loop: predictions and outcomes

Each prediction is recorded here **before** its run, then the outcome is filled in with a one-line verdict:

| verdict | meaning |
|---|---|
| ADOPTED | the move is kept |
| DROPPED | the move is abandoned |
| CONFIRMED | the prediction held |
| REFUTED | the prediction failed |
| SURPRISE | the result was not anticipated |

## Ground convention (TMD)

The machine floats completely in practice. Every virtual ground used in a simulation is stated, and a result that depends on one is flagged **[GROUND]**.

| basis | what it means | label |
|---|---|---|
| physical | the machine floating in free space: every node's capacitance goes to infinity, the 25× Robin boundary | "free" |
| historical default | a grounded can 50 mm out | "can50", a virtual ground |

## Step 0: stray budget (engine only, reference build, rotor tips 15°)

**Groups.** Each group is scaled on the field-solved C(θ):

| group | couplings | how it is scaled |
|---|---|---|
| C1 | 1–R-A and 4–R-B | the floor scaled by f, swing kept: C − (1 − f)·min C |
| Cx | 7–n17 and 8–n23 | the floor scaled by f, swing kept |
| X | every other node-to-node coupling | × f |
| E | every node's capacitance to the can or to infinity | × f |
| Ca | Ca and Cb | × f |

**Predictions.**
- **B1.** C1 and E are both binding: no single group scaled alone to f = 0.1 reaches z ≥ 1.2.
- **B2.** C1 alone at f = 0.1 gives the biggest single-group gain, but z < 1.1.
- **B3.** The pair (C1, E) at f = 0.25 reaches z ≥ 1.2 on the free basis.
- **B4 [GROUND].** On the free basis, moving the virtual reference from infinity to R-A changes z by < 0.02.

**Outcomes:** (filled after the run)
