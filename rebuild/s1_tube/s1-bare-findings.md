# Stage 1 — the bare core at the tube's values: findings

**Source:** `rebuild/s1_tube/s1_bare.py` → `s1_bare_results.json` (air), and `--case vacuum` →
`s1_bare_vacuum_results.json`. Every number below is from the results file.

**Status:** evidence for the designer. It adds nothing to the circuit: the frozen S0 core (`42747f4`) is run with the
tube's values.

**The inputs** are provisional until the S2 models re-solve them [IR]:
- C1 / C2: 128.4–450.6 pF (3-D, `sim/tube-strays-findings.md` §4);
- Ca = Cb: 495 pF (the sixth gap, DECIDED);
- 120 Hz;
- the 6 mm gap's breakdown: 19.70 kV (`sim/air_stack_sizing_results.json`, 1.5 × V_op);
- one HV stick per diode position: 20 kV V_RRM, avalanche at 24 kV (`sim/diodes_real.py`).

**No strays are modelled.** S2's field solves bring them in as nodes.

## Headline

**The bare core has no voltage limit of its own below the air's.**
- With ideal diodes it grows without bound [OC: the map is linear in amplitude].
- With real sticks it stops only when D3 / D4 avalanche. Nodes 1 / 4 then sit at **29.7 kV, 1.51 × the varicap gap's
  19.70 kV breakdown**, and the run passes that breakdown at cycle 17, 0.14 s from a 1 kV seed.
- **So the first limit the bare core meets is a flashover of the varicap gap.** The evidence shows that *a* voltage
  limit below the gap's breakdown is necessary. It does not show which kind; that is in the options below. [IR: the
  model has no air breakdown; the gap's figure is the record's]

## Findings

1. **The gain at the tube's values (bare, no strays):**

   | record | z per cycle |
   |:--|:--|
   | ideal diodes (LCP) | 1.18702 |
   | ngspice, near-ideal ND | 1.18714 |
   | ngspice, real sticks, early cycles | 1.1806 |

   - The sticks' drop and capacitance cost 0.006 of z [IR].
   - The record's "1.31 bare" was the 2-D cell's κ 7.47. On the 3-D κ 3.51 the bare core gives 1.187.
2. **The stress map** [OC: under linear growth every voltage scales alike; the growth inside the traced cycle is
   divided out, so the two halves are symmetric]:

   | part | peak / varicap-node peak |
   |:--|:--|
   | nodes 1, 4 (the varicap gaps) | 1.000 |
   | D3, D4 reverse | 0.956 |
   | Ca, Cb | 0.528 |
   | nodes 2, 3 = D1, D2 reverse | 0.472 |

   - The varicap gaps and the cross diodes D3 / D4 carry the stress. The return diodes and the transfer capacitors see
     about half of it.
3. **The run-up and the ceiling** (real sticks, typical leakage, from 1 kV on nodes 1 and 4):
   - V1 goes 1.29 → 4.86 → 18.74 kV at cycles 0 / 8 / 16, then holds at 29.68 kV from cycle ≈ 28. Nodes 2 / 3 hold
     at 15.97 kV.
   - At the ceiling, D3 and D4 each pass 1689 nC a cycle forward and 1689 nC a cycle in avalanche. **The pump's
     surplus circulates through them.** That is the equalization principle: the pump's power ends as heat in what
     limits it [OC].
   - That is about 1.69 µC × 24 kV × 120 Hz ≈ **4.9 W in each of D3 and D4** [IR: priced at BV, a lower bound]. A
     stick of this class is not specified for that continuously [RH], so the ceiling may fail the sticks as well as the
     air.
4. **Self-start depends on the leakage class** [IR: the stick model's leakage element; 24 cycles decide]:

   | leakage per stick | the smallest seed on nodes 1 / 4 that grows |
   |:--|:--|
   | typical, 25 nA | ≤ 1 V |
   | datasheet maximum at 25 °C, 2 µA | 81–82 V |
   | hot, 5 µA | 375–381 V |

   - With typical parts, the bare core starts from about a volt, which is the level of charge left by handling or the
     air. That agrees with the designer's experiment (unaided starts; a rubbed PVC tube if slow).
   - Hot or worst-case parts need tens to hundreds of volts.
   - The earlier record's "the model needs a seed" (ledger items 46 / 65) came from the full machine with its clamps'
     and chains' leakage. The bare core does not show it with typical parts.
5. **Ca:**
   - z peaks at Ca ≈ 0.7 C_max (1.1978). The DECIDED 1.1 C_max gives 1.1870, and 0.5–0.9 C_max all give ≥ 1.194
     [OC: the ideal solver].
   - Strays will move the optimum, so this is a note for S2, not a proposal to undo the decision.

## Air against the tube drawn for vacuum (the designer, 2026-10-14: "in parallel compare with the tube vacuum drawn")

**The vacuum inputs:** the tube as first drawn for vacuum (ledger §2, phase 6: 8 + 8 plates):
- C1 / C2: 71.1–1113.4 pF;
- Ca = Cb: 1224.7 pF (1.1 C_max);
- breakdown: 30 kV (`sim/air_stack_sizing_results.json` base_vacuum).

**Caveat** [IR]: those capacitances come from the 2-D cell and were never re-solved in 3-D. In air, the 3-D rims took
κ from 7.47 to 3.51, so the vacuum κ 15.66 is an upper bound and its z is optimistic.

| | air (3-D, as built) | vacuum (2-D, as drawn) |
|:--|:--|:--|
| κ = C_max / C_min | 3.51 | 15.66 (upper bound) |
| z ideal / ngspice ND / real sticks | 1.18702 / 1.18714 / 1.1806 | 1.57040 / 1.57053 / 1.5694 |
| D3 / D4 reverse ÷ varicap node | 0.956 | 0.880 |
| Ca / Cb ÷ varicap node | 0.528 | 0.543 |
| D1 / D2 reverse ÷ varicap node | 0.472 | 0.457 |
| the gap's breakdown | 19.70 kV | 30 kV |
| the bare core's ceiling (one stick, D3 / D4 avalanche) | 29.7 kV, 1.51 × the breakdown | 38.3 kV, 1.28 × the breakdown |
| cycles from 1 kV to the breakdown | 17 | 7 |
| avalanche charge in D3 / D4 at the ceiling | 1.69 µC a cycle, ≈ 4.9 W each | 10.84 µC a cycle, ≈ 31 W each [IR: at BV] |
| self-start seed, leakage typ / max / hot | ≤ 1 V / 81 V / 375 V | ≤ 1 V / 9 V / 14 V |

- **The conclusion is the same in vacuum.** The bare core overshoots the gap's limit there too, and faster: the
  limit is necessary in both media.
- **Vacuum's larger swing:**
  - it lowers D3 / D4's share a little (0.88 against 0.956);
  - it makes the start far easier against leakage;
  - it makes the surplus at the ceiling about six times larger. The surplus is what a limiter has to burn.

## The options for the limit (PROPOSED, the designer decides)

The evidence asks for a limit under 19.70 kV on nodes 1 / 4, with margin. Whatever does the limiting takes the
pump's whole surplus as heat (finding 3). The options:
- **(a) A limiter on nodes 1 / 4,** e.g. avalanche strings. This is the earlier design's choice. It now enters only
  as one candidate.
- **(b) D3 / D4's own avalanche as the limit:**
  - no added part; the cross diodes are chosen by avalanche voltage and avalanche energy rating;
  - the run's ratio (29.68 kV node / 24 kV BV) suggests a BV near 0.8 × the node target [RH: to be run];
  - the cost is that the cross diodes then carry the full surplus.
- **(c) A load that takes the surplus.** A linear load only lowers z and does not set a ceiling [OC], so a load limits
  only if it draws more than linearly with voltage.
- **(d) A wider gap.** It raises the air's limit but leaves the core without a controlled one.

## Next

- **S1b:** run whichever options the designer picks, with the same solver, ngspice and stick records. Each run
  reports the node ceiling, the margin to 19.70 kV, the heat per part, and the self-start threshold.
- **S2:** the 3-D models of the vane stacks (antiphase, per S0) and Ca / Cb, to give C1 / C2 and the strays as nodes.
  S1's numbers are then re-run on them.
