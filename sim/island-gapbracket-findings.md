# Findings — ISLAND-ASDRAWN Pass A′: re-grade under physical gap commutation of the load gaps

**Branch** `claude/new-session-0az7f9`. It carries Pass A at 302f9f2 and the r0.2 HARNESS-FAIL at c3920e6.
**Not merged**: TMD signs off.

The Pass A record is re-graded read-only through `sim/island_asdrawn_r01_spice.py`. That is the
r0.1 ngspice harness, renamed from `sim/island_asdrawn.py` by c3920e6. Only the gap elements of its
decks are rewritten. New decks are `spice/ia2_*`.

## FINAL GRADE: `CONDITIONAL-ON-RECOVERY (t_rec ≤ 0.1 µs)` · `MOTOR-NOT-ASSESSED` · not `STRAY-DEPENDENT`

The predicted grade, `REVERSAL-ONLY (load gap)`, is **not** confirmed. The picture has three parts.

1. **Pass A's `SINK-PARTIAL` does not stand as drawn.** Its gain (Δη +0.169, z 1.95 against 1.41)
   exists only under the one-way load gap (M-OW). After the first current zero, that gap blocks a
   reverse transient recovery voltage (TRV) of **1.41 × its own strike voltage within 0.35–0.38 µs**
   (P1 reproduced on every event). No symmetric self-break gap can do that.
2. **The full ring-down limit kills the gain** (P2 reproduced). M-RD with I_hold → 0 gives
   Δη −0.002 and Δz +0.004, which is `SINK-IS-PUMP`. The tax moves into the coil ESR (T_ESR 0.36 of
   W_mech), as in D1.
3. **A narrow physical window keeps part of the gain.** The conditions are a symmetric gap that:
   - holds its arc through the small reverse half-cycle that follows the transfer, extinguishing
     while the ring current is still ≥ 0.3 of the transfer peak (I_hold ≥ 0.3 i_pk1); and
   - then recovers its full strike strength within **t_rec ≤ 0.1 µs**.

   Under those conditions the gain survives the whole ±10 % parity band as `SINK-PARTIAL`, in the
   M-SR model:

   | parity-averaged Δη | I_hold 0.3 | I_hold 0.5 | I_hold 0.7 |
   |---|---|---|---|
   | t_rec 0 | +0.012 | +0.035 | +0.038 |
   | t_rec 0.1 µs | +0.012 | +0.035 | +0.034 |

   The gain is real in the ledger but small. It is **Δη +0.012 to +0.038**, against the one-way
   bound of +0.169 and the model's claim of about +0.20. f_rec,meas is 0.02–0.07, against
   f_rec,model = 0.954 at the harness's own 22 Ω loop.

   The gap does this legitimately, without acting as a rectifier. At I_hold 0.3–0.5 it never holds
   more than 0.76 × its own V_f in either direction. The I_hold 0.7 point overshoots to 1.05 × V_f
   in the ngspice trace and is marginal.
4. **Recovery slower than about 1 µs reverses the sign.** At t_rec = 1 µs and 10 µs the gap
   re-strikes on the post-extinction swing (52–494 re-ignitions per run). That rings the transfer
   back into the coil ESR, and z falls to 1.385, *below* the direct island's 1.410. Every such point
   is `PUMP-BREAKS`.

**So the island's value depends on a measurable gap property: the µs-scale dielectric recovery of
the load gap.** This is the `[MEAS]` rung the verdict set names. It ties to D-MEDIUM. Even under the
most favourable admissible setting, the drawn machine's η is about 0.41–0.44, not about 0.50.

## 1. Re-grade table (Pass A → Pass A′)

| item | Pass A (302f9f2) | Pass A′ |
|---|---|---|
| verdict | `SINK-PARTIAL` (η 0.57 / 0.70) | **`CONDITIONAL-ON-RECOVERY (t_rec ≤ 0.1 µs)`**. The gain is Δη ≤ +0.038 (η ≤ 0.44), only for I_hold ≥ 0.3 and t_rec ≤ 0.1 µs; otherwise none, or `PUMP-BREAKS` |
| the load-gap model | one-way in both brackets (inherited "established") | the one-way bound needs a 1.41 V_f reverse withstand, so it is a rectifier (§1 of the brief, measured) |
| `REVERSAL-ONLY` ruled out? | yes, "the gain survives bracket (a)" | that reasoning was void: bracket (a) never touched the load gap. The re-grade supersedes it |
| motor | `MOTOR-DEPENDENT` (lossless 0.64 H) | **`MOTOR-NOT-ASSESSED`**. With R_COIL 40 Ω, G1m still does not converge across reltol (H6) |
| `PREMISE-FAILS`, `LOOP-BYPASSED`, `LEDGER-MISMATCH` | stand | stand (not re-run: unaffected by the load-gap model) |

## 2. Check table

| check | result | status |
|---|---|---|
| **H0** reproduction (Pass A and every D1 row, ≤ 0.005) | G1a 1.4098 / 0.4001 · R1a 1.9501 / 0.5689 · R1b 2.1598 / 0.7007 · D1 load-bidirectional G1 1.4098 / 0.4000, R1 1.4138 / 0.3978 · D1 all-gaps G1 1.2829 / 0.4273, R1 1.3139 / 0.4152. All match to ≤ 0.0001 | **PASS** |
| **H1** limits | M-SR (holdoff off, I_hold > 1) = 1.9507 / 0.5690 against M-OW 1.9501 / 0.5689. M-RD(→0) = 1.4141 / 0.3978 against D1 1.4138 / 0.3978 | **PASS** |
| **H2** no chop (every extinction, \|i\| < 1e-3 of the event's first half-cycle peak) | model extinctions are event-exact at the natural zero of the rectifier hand-off (0 on every M-RD/M-SR run). Window-end extinctions go out at the next natural zero; max 9.5e-4 (R2 motor M-RD(→0)); every run < 1e-3 over the verdict runs | **PASS** |
| **H3** conservation (< 1 % of E_diss; trip) | max residual 0.66 % of E_diss (gap-normalised max 1.8 %, reported). A +5 % total-dissipation perturbation moves the signed residual by −5.000 % on every run (predicted −5 %, ±0.1 %), and fails the guard | **PASS** |
| **H4** TRV record | M-OW: reverse peak / V_f = −1.409 to −1.413 at +0.35 to +0.38 µs after the zero, all 6 events (P1). M-RD and M-SR records are in `island_gapbracket_trv.csv` | **PASS** |
| **H5** independent engine (Python, frozen C, ≥ 3 load events per model, 1 %) | M-OW, M-RD(0.5), M-SR(0, 0.7), M-SR(1 µs, 0.5): t½, node-3 charge, E_diss and TRV agree to ≤ 0.50 % (worst: t½ 0.50 % on M-OW cycle 8) | **PASS** |
| **H6** motor convergence (z across reltol ≤ 0.01) | R2 M-OW 1.9130 / 1.9137 ✓. **G1m M-OW 1.0348 / 1.1696 ✗** (Δ 0.135). M-RD(→0): R2 1.0890 / 1.0894 ✓ (the reltol-1e-5 schedule fixed point stopped at 10 iterations unconverged, z within 4e-4). **G1m 1.0150 / 1.0332 ✗** (Δ 0.018) | → `MOTOR-NOT-ASSESSED` |
| **H7** firewall | pure EE: KCL, LC, gap switching, varicap work | PASS |
| **H8** frozen empty-diff | `git diff HEAD` is empty on `shuttle_core.py`, `reference/`, `sim/seq_stat_commutation.py`, every committed `spice/` file (the `ia_*` decks and all `.sub` files), `sim/island_asdrawn.py`, `sim/island_asdrawn_r01_spice.py`, `sim/island-asdrawn-r01-spice-findings.md` and `island_asdrawn_*`. `sim/island-asdrawn-findings.md` differs by the pointer line only (+2 lines: the line and a blank). New files are `ia2_`/`island_gapbracket`-named | **PASS** |

δ_z = 0.0105 and δ_η = 0.005, from the reltol 1e-4 / 1e-5 twins (R1 M-OW Δz 0.0035). The G0
M-RD(→0) reltol-1e-5 twin stopped at 7.6 cycles in ngspice. It is recorded as failed and not used.

## 3. Q2 — M-RD (ring-down)

| I_hold / i_pk1 | →0 | 0.1 | 0.3 | 0.5 | 0.7 |
|---|---|---|---|---|---|
| R1 z / η | 1.4141 / 0.3978 | 1.4138 / 0.3979 | 1.4977 / 0.4218 | 1.6080 / 0.4546 | 1.7277 / 0.4925 |
| G1 z / η | 1.4098 / 0.4000 | 1.4098 / 0.4000 | 1.4098 / 0.4000 | 1.4098 / 0.4000 | 1.4098 / 0.4000 |
| class | `SINK-IS-PUMP` | `SINK-IS-PUMP` | `SINK-PARTIAL` | `SINK-PARTIAL` | `SINK-PARTIAL` |

**Why the transfer peak is not the ring.** The first half-cycle is the transfer itself. After it,
the ring *current* is only about 7–10 % of i_pk1 (the rail rectifier SG1 blocks the reverse swing
and changes the loop), while its *voltage* swing is still of order V_f.

I_hold therefore sets how long the arc keeps ringing. From about 0.3 upward it extinguishes at the
end of the first reverse half-cycle, and the post-extinction forward rectifier then blocks
≤ 0.71 V_f in reverse (admissible for a recovered gap).

The first ~10 ns of each event carry a stray-capacitance dump spike of up to 14× the ring peak.
That spike is excluded from i_pk1 (`T_SPIKE` 50 ns `[IR]`). It is kept in the H2 reference.

## 4. Q3 — M-SR (symmetric, recovering; 10 µs holdoff; ρ = 1 − e^{−Δt/t_rec})

Values are parity-averaged Δη (R1 − G1) and the per-point class across ×0.9 / ×1.0 / ×1.1 of I_hold.

| t_rec \ I_hold | 0.1 | 0.3 | 0.5 | 0.7 |
|---|---|---|---|---|
| 0 | −0.002 `SINK-IS-PUMP` | **+0.012 `SINK-PARTIAL` ×3** | **+0.035 `SINK-PARTIAL` ×3** | **+0.038 `SINK-PARTIAL` ×3** (0.77: 26 re-ignitions) |
| 0.1 µs | −0.002 `SINK-IS-PUMP` | **+0.012 ×3** | **+0.035 ×3** | **+0.034 ×3** (0.7 and 0.77 re-ignite) |
| 1 µs | −0.002 `SINK-IS-PUMP` | −0.010 `PUMP-BREAKS` ×3 | −0.010 `PUMP-BREAKS` ×3 | −0.010 `PUMP-BREAKS` ×3 |
| 10 µs | −0.010 `PUMP-BREAKS` ×3 | −0.010 `PUMP-BREAKS` ×3 | −0.010 `PUMP-BREAKS` ×3 | −0.010 `PUMP-BREAKS` ×3 |

No `PARITY-ONLY` point occurs: no sign flips within any band. Every surviving point needs
t_rec ≤ 0.1 µs, which gives **X = 0.1 µs**.

**Admissibility, normalised to each event's own V_f:**

| point | max \|V\| held during holdoff | reverse \|V\| held by the post-holdoff rectifier |
|---|---|---|
| I_hold 0.3 | 0.45 | 0.34 |
| I_hold 0.5 | 0.76 | 0.56 |
| I_hold 0.7 | **1.05** (the ngspice trace overshoots where the engine stayed below 1; marginal) | 0.65 |

## 5. Q4 motor (R_COIL 40 Ω, real time) and Q5 strays

| run | z | η |
|---|---|---|
| R2 M-OW (reltol 1e-4 / 1e-5) | 1.9130 / 1.9137 | 0.4200 / 0.4203 |
| G1m M-OW (reltol 1e-4 / 1e-5) | 1.0348 / **1.1696** | 0.0196 / 0.0986 (**not converged**) |
| R2 M-RD(→0) (reltol 1e-4 / 1e-5) | 1.0890 / 1.0894 | 0.0523 / 0.0527 |
| G1m M-RD(→0) (reltol 1e-4 / 1e-5) | 1.0150 / **1.0332** | 0.0068 / 0.0198 (**not converged**) |

The 300 Hz motor branches drive the direct twin to the edge of pumping. Its ngspice solution then
depends on tolerance, so no motor modifier can be graded (`MOTOR-NOT-ASSESSED`, P4 falsified).

| stray (pF) | M-RD(→0): R1 − G1 Δη | M-SR (t_rec 0, I_hold 0.7): R1 − G1 Δη |
|---|---|---|
| 0 | −0.001 | +0.034 |
| 5 | −0.002 | +0.048 |
| 20 | −0.007 | +0.026 |

The sign is stable across strays, so the grade is not `STRAY-DEPENDENT`.

## 6. Q6 — the rectifier spec (from Q1 / M-OW traces only; no new physics)

This is what a series rectifier per load gap would have to meet to recover the full M-OW bound
(Δη +0.169, z 1.95):

| quantity | value |
|---|---|
| reverse TRV | 1.413 × V_strike → **28.3 kV** at V_strike 20 kV; **35 kV spec** with a 1.25 margin `[IR]` |
| reverse-blocking time | the TRV peaks **0.35–0.38 µs** after the current zero, so blocking must be established ≪ 0.35 µs after it |
| forward current per event (scaled to the 15 kV operating point) | peak **24 A**, 0.66 µC, ∫i²dt 3.8 µA²s per event |
| RMS per load gap | **0.034 A** (300 Hz) |
| note `[IR]` | a vacuum rectifier has no reverse-recovery charge. It blocks from the zero, which makes it the period-true fit for a ~0.4 µs TRV |

## 7. Pre-committed predictions

| prediction | outcome |
|---|---|
| **P1** TRV ≥ 1.4 on every one-way load event | ✓ 1.409–1.413 |
| **P2** ring-down limit → `SINK-IS-PUMP` (reproduces D1) | ✓ |
| **P3** M-SR shows no gain surviving parity | ✗ gains survive at t_rec ≤ 0.1 µs, I_hold ≥ 0.3 |
| **P4** R_COIL 40 Ω makes G1m converge; the motor changes no sign | ✗ G1m does not converge → `MOTOR-NOT-ASSESSED` |
| **Final** `REVERSAL-ONLY (load gap)` | ✗ → `CONDITIONAL-ON-RECOVERY (t_rec ≤ 0.1 µs)` |

## 8. Method `[ME]` and choices `[IR]`

- **Gap as a scheduled element.** Each gap is three parallel conductances (bidirectional, forward
  rectifier, reverse rectifier) behind its sense source, with Pass A's RON 2 Ω, VE 1 mV and ROFF.
  PWL mode sources switch them. A bidirectional→rectifier hand-off inside a half-cycle of the same
  sign is seamless, and the rectifier extinguishes exactly at the natural zero (event-exact, no
  chop). Ignition uses Pass A's 0.5 µs arming edge; internal edges are 10 ns.
- **Station offset.** Station edges are offset by 2 ns. Otherwise they nearly coincide with the
  periodic Cx/clock PWL breakpoints and force a femtosecond step (a harness finding).
- **Fixed points.** M-OW and D1 schedules are static. M-RD and M-SR schedules come from fixed points.
  - For R twins, each load event's whole extinction / holdoff / re-ignition chain is resolved by an
    exact piecewise-LTI engine. It starts from the ngspice pre-state, uses frozen C and
    matrix-exponential steps, bisects every event, and reproduces the 0.5 µs ramp.
  - The machine-level fixed point converges in 2–3 ngspice runs.
  - G twins, which have no ring, use the trace rule.
- **I_hold → 0** is realised as 1e-4 of i_pk1, with the arc otherwise held to the window end.
- **Window end** (the electrodes part): the arc hands over to a rectifier of the current's sign and
  goes out at its next natural zero.
- **i_pk1** excludes the first 50 ns (the stray-dump spike) `[IR]`.
- **ρ_max** = 1 `[IR]`, as the brief specifies.

## 9. Routed to TMD (do not pick)

- **D-PRINCIPLE.** The proposed rectifier wording holds only for the M-OW bound. The measured result
  is more specific. The equalization can be *partly* resonated with a symmetric gap only if the gap:
  - holds the arc through the first reverse half-cycle while the ring current exceeds about 0.3 of
    the transfer peak, and
  - regains its strike strength within about 0.1 µs;

  and even then it gives Δη ≤ +0.04. Otherwise it relocates or loses.
- **D-LEDGER.** Retire the (6.153 + f·4.407)/20.347 composition. Even the best admissible point
  gives f_rec 0.07, against 0.954.
- **D-ISLAND.** There are three options:
  - drop Lx (symmetric gaps with slower recovery lose, `PUMP-BREAKS`);
  - add a Q6 rectifier per load gap (needs its own falsification run);
  - pursue fast recovery (needs the `[MEAS]` rung: the µs recovery of the load gap in the chosen
    medium — D-MEDIUM).
- **Pass B.** B1 wording waits on this grade. Nothing may call η ≈ 0.50 validated.

## Deliverables

- `sim/island_gapbracket.py`: the consumer module, rule engine, chain engine, gates, campaign and
  report, with on-load self-tests. Its decks are `spice/ia2_*.cir`, plus `spice/ia2_gap.sub`.
- Data:
  - `island_gapbracket_runs.csv` (every run);
  - `island_gapbracket_trv.csv` (TRV per event);
  - `island_gapbracket.png` (the Q2 curve, the Q3 map and the TRV bars).
- A pointer line at the top of `sim/island-asdrawn-findings.md`.
- Changelog.
