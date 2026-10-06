# Goldie (US 3,013,201) floating-rotor generator on the tube's capacitances: diodes vs spark gaps

Source: `sim/goldie_tube.py` → `sim/goldie_tube_results.json`. Exact engine (`pump_engine` Sim + monodromy).
Setup per section:
- induction plate –C/2– floating rotor –C/2– collector;
- C(θ) = 1114 / 71.2 pF (the tube varicap per side, cosine schedule);
- collector stray 28 pF, load cap 2 nF;
- A and B cross-fed (k 1), 300 rpm, scaled to 20 kV.

## Results

| switching | best z per cycle | belt per cycle | lost | surplus at 20 kV | η |
|:--|:--|:--|:--|:--|:--|
| ideal diodes (the patent), k 1 | 1.0882 | 113 mJ | 0.0003 mJ | 3.39 W | 1.000 |
| diodes, rotor stray 50 pF | 1.0825 | 106 mJ | ~0 | 3.18 W | 1.000 |
| diodes, k 0.5 | 1.0069 | 65 mJ | ~0 | 1.95 W | 1.000 |
| diodes, k 0.15 | 0.9996 | — | — | does not self-excite (threshold ~0.18) | — |
| timed spark gaps, best windows (charge −24° → 0.5°, dump 16° → 30.5°) | 1.0880 | 116 mJ | 3.3 mJ | 3.39 W | 0.97 |
| timed spark gaps, charge opened 3° earlier (−27°) | 1.0880 | 126 mJ | 12.6 mJ | 3.35 W | 0.90 |
| timed spark gaps, charge opened at −30° (overlaps the dump at C_min) | 0 | — | — | output shorted to ground | — |
| timed spark gaps, the first narrow windows | 0.96–1.08 | 7–25 mJ | 1–15 mJ | −0.8 to 0.5 W | 0.3–0.9 |

Ledger closure is ≤ 5e-11 J on every converged row. For comparison, the spark-gap Bennet tube (v4) gives 1.31 W of
surplus at η 0.53 (`tube-ledger-findings.md`).

## Reading

1. **With spark gaps it is feasible in the engine's gap model, and nearly as good as diodes:** η 0.97 at the best
   windows. The cost is timing:
   - the windows must be wide (24° charge, 14.5° dump), each ending at its capacitance extreme;
   - their opening angles are tight: 3° early on the charge gap loses 7 points of η, and 6° early shorts the output
     through the charge gap.
   - This is the floating-rotor equivalent of the clocking-deck timing budget.
2. **The engine's gap is optimistic for this circuit.** It strikes at zero voltage and stays lit as long as it is armed.
   In the Goldie circuit both switches carry a slow, continuous current while C ramps (µC over milliseconds, i.e. mA).
   A real spark cannot hold a mA arc, so the gap relaxes, re-striking at its breakdown V_b. Each packet loses
   ½·ΔQ·V_b, so a gap passing charge Q loses about Q·V_b / 2 [OC]. For the 4.3 µC per section per cycle through four
   gaps:
   - V_b 1 kV costs about 8.6 mJ per cycle (η ≈ 0.90);
   - V_b 3 kV costs about 26 mJ per cycle (η ≈ 0.75) [RH].

   Small strike voltages favour short gaps near the Paschen minimum, or a gas.
3. **Timing needs a moving electrode.** Outside its window each gap must hold off the full output:
   - the dump gap sees V_L at C_max;
   - the charge gap sees V_L at C_min.

   A fixed stationary gap cannot both strike at ~1 kV and block 20 kV. The gap distance must change with rotor angle:
   floating bridge tips on the rotor passing stator sphere pairs, i.e. two series gaps per closure, which doubles V_b.
   That fits the floating rotor (the bridges float too), and the clocking decks carry over.
4. **Diodes remain the simplest.** They switch at the exact angle by themselves, η ≈ 1, and need no timing. 25–30 kV HV
   rectifier stacks are commodity parts. Their capacitance (in the 28 pF stray) and leakage are the costs.
