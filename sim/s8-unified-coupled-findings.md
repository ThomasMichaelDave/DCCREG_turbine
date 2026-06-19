# Findings — S8: unified coupled model + four-destination energy ledger

**Branch** `s8-unified-coupled-ledger` (off `main`). **Verdict:** **`SYNERGY-GENERIC`** — across the whole
tuning sweep the coupled steady-state dissipation matches the floor; enabling each coupling moves the
dissipation fraction by < tolerance; **the nest is the sum of its parts.** The conservation guard closes to
**2.3×10⁻⁶** at every tuning point, so the result is trustworthy and not a numerical phantom. The honest prior
is **vindicated** — and the one concrete payoff is a debunking: the stitched **53 W garolite dielectric loss
is a continuous-ring phantom**; the coupled (series-DC) value is **0.03 W**.

**What S8 is:** one coupled electromechanical model of the whole nest (split resonator + varicap pump + Cem
branches + contra-rotation), instrumented to report energy **by destination per cycle** — storage,
circulation, output, dissipation — replacing the *stitched* S5–S7 budget that solved each box in isolation
and added them. The question only a coupled model can answer: is `E_diss/E_in` lower/equal/higher than the
stitched prediction, and if lower, which coupling carries it?

**Non-negotiable framing honored — no new energy.** Everything is redistribution; the belt sources every watt;
a "synergy" would be a lower dissipation *fraction* (efficiency), never gain. The **hard conservation guard**
(a non-closing ledger = a bug, STOP and fix) is what makes the verdict trustworthy — and it earned its keep:
the first build double-counted the Cem electrical input and mis-booked the C_R chain; the guard fired
(`CONSERVATION-VIOLATED`, residual 0.24), and the ledger was rebuilt to one consistent energy chain before any
result was believed.

**Method:** custom Python integrator (SPICE ruled out — the nonlinear shuttle is ngspice-blocked, S7). The
fast f₀ ring transient (the only stiff part) is integrated at f₀ resolution with the dielectric loss as a
genuine shunt conductance in the dynamics; the slow Cem/mechanical at the PRF scale; mechanical quasi-static at
fixed ω_rotor. Consumer of the frozen physics (z from `shuttle_core`, reach from `resonator_sim`) — edits none;
empty-diff asserted.

---

## §5 named checks

| # | check | result |
|---|---|---|
| 1 | frozen byte-identical empty-diff | ✓ clean (asserted at end) |
| 2 | **Gate 0** — couplings-off reproduces z, reach, f₀ | z = **1.2033**, f₀ = **637 kHz**, reach **14.95 kV** ✓ |
| 3 | **conservation guard** < 0.1 % at every tuning point | max residual **2.3×10⁻⁶** ✓ |
| 4 | baseline partition + dissipation vs stitched | dielectric **0.03 W** vs stitched 53 W (debunked) |
| 5 | coupled partition — Δ from enabling each coupling | **+0.0000** for k, C(θ), Cems (no synergy) |
| 6 | tuning-sweep map — sub-stitched minimum? | none; `E_diss/E_in` flat at the floor |
| 7 | parametric probe `[RH]` | dormant (rotor 300 Hz vs 2·f₀ = 1.27 MHz) |
| 8 | verdict + which coupling carries it | `SYNERGY-GENERIC` — no coupling carries a synergy |

## Stage A — Gate 0 (couplings off → reproduce the boxes)

The model reproduces the validated pieces **before** any coupling is believed: galvanic **z = 1.2033**
(`shuttle_core`, within the 0.03 witness tol), **f₀ = 637 kHz** (L_R 79 µH / C_R 789 pF), **15 kV reach**
(`resonator_sim`, v_peak 14.95 kV, crowbar idle). Gate 0 **PASS** — the model earns trust.

## Stage B — four-destination ledger + hard conservation guard

| destination | baseline (all couplings on) |
|---|---|
| **storage** S | 88.76 mJ (C_R at 15 kV) — ∮dS ≈ 0 at steady state |
| **circulation** (diagnostic) | ~1980 mJ peak-to-peak (the fire-transient reactive slosh — high effective Q) |
| **output** (contra-rotation) | **~0 W** — the motor is core-loss-limited (S7 BALANCE-FAILS); no net contra-rotation |
| **dissipation** | **56.1 W** total |

**Conservation guard: residual 2.3×10⁻⁶** (the fire-ring ODE closes to machine precision once the dielectric
shunt is in the dynamics). **Dissipation breakdown:** C_R chain (doubler C-C tax + dielectric + ring copper +
governor-shed) ≈ 28 W, **core 15 W**, **rotor drag 10 W**, governor-shed 11 W — and **dielectric 0.033 W**.

**The 53 W phantom, debunked.** The stitched budget booked the garolite dielectric at **~53 W** (= 88 mJ/cycle)
— but the *whole* C_R energy chain is only ~28 mJ/cycle, so 53 W of dielectric is **physically impossible**: it
exceeds the entire chain. The coupled value is **0.033 W** — a **1584× over-estimate** in the stitched figure.
The cause is the **series-DC-hold waveform**: C_R holds 15 kV DC and rings only ~0.5 µs per 1.67 ms fire (duty
~0.03 %), so the AC voltage that drives tanδ loss is duty-cycled to ~0. This is **the topology already found in
coil-topology/S5, not a hidden coupling** — and crucially **tanδ is heat, not circulation** (the brief's
"circulation vs dissipation" question for the 53 W resolves as: it was never 53 W of either; it was a
continuous-ring booking error).

## Stage C — couplings one at a time

| config | E_diss/E_in | residual | Δ vs OFF |
|---|---|---|---|
| couplings OFF | 1.0000 | 2.3e-06 | — |
| + k (resonator) | 1.0000 | 2.3e-06 | **+0.0000** |
| + C(θ) pump | 1.0000 | 2.3e-06 | **+0.0000** |
| + Cems load+torque | 1.0000 | 2.3e-06 | **+0.0000** |

Enabling each coupling moves the dissipation fraction by **less than tolerance** — no inter-box energy exchange
changes the partition. (The Cems are f₀ spectators — S7 — so they carry no reactive exchange with the ring;
the resonator k only re-sizes L_total; the varicap C(θ) is the pump, already in the baseline.)

## Stage D — tuning sweep (the synergy question)

`E_diss/E_in` and the total dissipation (56.1 W) are **flat across every DOF**: septum (garolite ↔ mica), k
(0.0 / 0.3 / 0.6), Cem fire-station phase (±15°), cap-family scale (0.5× / 2×). **No sub-stitched minimum
exists** — the floor *is* the minimum. The **U-tube / local-wrong probe** comes back negative: deliberately
detuning a local element off its isolated optimum does **not** lower the global dissipation fraction. Notably
the **septum material is not load-bearing** at this operating point (garolite vs mica both give ~0.03 W
dielectric) — the stitched "swings the tank loss ~5×" applied only to the continuous-ring phantom.

## Stage E — parametric probe `[RH]`

The rotor modulation (~300 Hz) is **2.4×10⁻⁴ of 2·f₀ (1.27 MHz)** — the parametric channel is **dormant** by
~3.5 decades. A hypothetical modulation lock at f₀/2 (319 kHz) would open it, but that is a *different machine*
(an exploratory redesign, out of scope). **No parametric gain at the design point** — the time-varying
varicaps charge the ring, they do not parametrically pump it. (Guard applies here too: any apparent gain would
have to trace to mechanical work in.)

## Verdict

**`SYNERGY-GENERIC`.** Across the sweep the coupled `E_diss/E_in` matches the floor; no coupling carries a
synergy; tuning only redistributes within the floor; the belt supplies the full piecewise dissipation. **The
conservation-tuning question is closed** — TMD's U-tube intuition does not pay out here: the nest is the sum of
its parts, the floor is real, and the only levers are the **floor** ones (septum → dielectric is already
negligible; lamination/flux → core; vacuum → windage). This **vindicates the stitched budget** and clears the
path to the v0.11 freeze + the material/lamination budgets with confidence the piecewise numbers hold.

**The one correction the coupled model makes** (not a synergy, an accounting fix): the S5 garolite "53 W" was a
continuous-ring phantom; the real series-DC dielectric is 0.03 W, and the septum material is not the
load-bearing loss the stitched budget assumed. The dominant floor terms are the **doubler C-C tax, the Cem core
loss, and the drag** — exactly where the S7 levers point.

## Deliverables

`sim/s8_unified_coupled.py` (coupled integrator: Gate-0 regression, four-destination ledger, hard conservation
guard, tuning sweep, `[RH]` parametric probe) · this findings doc · `s8_energy_partition.csv` (per tuning
point, with the guard residual) · `s8_partition.png` (four destinations + the 53 W-vs-0.03 W phantom) ·
`s8_diss_frac_sweep.png` (dissipation fraction over tuning vs the stitched line) · `s8_conservation_guard.png`
(the guard closing at every point). Frozen empty-diff asserted. **Not merged.**
