# Findings — island→tank fire path + whole-machine efficiency

**Branch** `machine-energy-balance` (off `energy-balance` `84fcaaa`, which is off the 789 pF / G3 head
`s2recheck-s3-spark`). **Verdict line:** `FIRE-PATH-RECOVERS` · `S2-ETA-CONFIRMED` · `QUENCH-AT-ZERO-CLEAN`
· **`ENERGY-BALANCE-GAP`** (η_machine > 1 on the literal trace — escalate) · `MACHINE-ETA = 7.3 (mid),
UNPHYSICAL`.

**Two sides, both real:** the fire *path* is excellent (the inductive C-L-C swap bypasses the stator's
C-C tax), **but** the machine-level energy accounting exposes that the reach-bearing M2 island-dump is
**not energetically sourced** by the flying-bucket shuttle trace. The headline machine efficiency cannot be
stated as a clean number — it escalates.

**Scope:** NOT consumer-only. All *state* (pre-fire island, Cx, tank C_R/L_R, V_arc) is consumed from the
frozen `shuttle_core` trace + Block R; the **fire transfer is a new time-domain RK4 ODE** in
`sim/fire_tank_transfer.py` (the frozen quasi-static solver shorts the 5–6 tank and cannot do the
L-coupled dynamics). Frozen modules (`shuttle_core.py`, `reference/doubler_core.py`, `index.html`)
**byte-identical** to base (0 producer edits, asserted). Mainstream circuit dynamics + electromechanics —
no DCCREG.

**Base flagged (per brief):** `energy-balance` `84fcaaa` descends from `s2recheck-s3-spark` (the 789 pF G3
point) — confirmed by `git merge-base`. Stator `W_mech = 15.94 mJ/fire` inherited (cited, not recomputed).

---

## 1. The two transfer regimes (why this is the real efficiency question) `[OC]`

- **Stator core merges (prior block):** pure **C-to-C** zero-time snap → the ½CΔV² two-capacitor tax,
  R-independent → 61 % lost (η = 38.6 %).
- **Island→tank fire (this block):** **C-L-C** — island Cx and tank C_R exchange charge *through* L, so the
  transfer is **oscillatory**, ~lossless at the matched-cap LC swap. The loss here is **not** the capacitive
  paradox; it is **arc drop + loop R + quench timing**. S2's reach assumed η = 0.990 = 4·Cx·C_R/(Cx+C_R)².
  **This block tests whether the dynamic fire achieves that swap.** It does.

## 2. The dynamic fire-transfer ODE `[OC]`

Integrated from the pre-fire state (island Cx = 648 pF at V_island = 20 kV, tank C_R = 789 pF at 0) with a
hand-rolled RK4 (Δt = 0.2 ns), to the **first natural current-zero** (no artificial cutoff):
```
L_eff·dI/dt = V_island − V_tank − V_arc·sgn(I) − I·R_loop ;  dV_island/dt = −I/Cx ;  dV_tank/dt = +I/C_R
```
Parameters (cited): C_R 789 pF, L_R 79 µH, Cx 648 pF (G3); V_arc 20/35/50 V + τ_rec 10 µs/100 µs/1 ms
(`shuttle_core.py:685-687`); V_HV 20 kV anchor (`s2_coupling.py:129`). **Undocumented → `[IR]` estimates,
swept, both sub-dominant:** L_loop ≈ 1 µH (≪ L_R, so L_eff ≈ 80 µH), R_loop ≈ 0.5 Ω (≪ Z₀ ≈ 474 Ω).

## 3. Results — the fire path RECOVERS

| corner | V_arc | **η_fire** | E_tank | E_arc | E_loop | E_resid | τ_quench |
|---|---|---|---|---|---|---|---|
| opt | 20 V | **0.9868** | 127.9 mJ | 0.28 mJ | 0.23 mJ | 1.20 mJ | 0.530 µs |
| mid | 35 V | **0.9853** | 127.7 mJ | 0.50 mJ | 0.23 mJ | 1.18 mJ | 0.530 µs |
| pess | 50 V | **0.9838** | 127.5 mJ | 0.71 mJ | 0.23 mJ | 1.16 mJ | 0.530 µs |

- **`FIRE-PATH-RECOVERS`** — η_fire ≈ **0.985** at all corners (E_island,pre = ½·648 pF·20 kV² = 130 mJ →
  ~128 mJ delivered). The inductive fire bypasses the C-C tax: **98.5 % vs the stator core's 38.6 %.**
- **`S2-ETA-CONFIRMED`** — the dynamic transfer reproduces S2's matched-cap **η = 0.9904** to within ~0.5 %
  (the small shortfall is the arc drop + the ~1 % residual left oscillating on the mismatched 648/789
  island at the first current-zero, **not** a modelling failure). The reach assumption taken on the formula
  alone is validated by the time-domain integration.
- **`QUENCH-AT-ZERO-CLEAN`** — the arc extinguishes at the first current-zero **τ_quench = 0.530 µs**
  (= π·√(L_eff·C_eff), self-test e). The arc recovery τ_rec (10 µs–1 ms) ≫ the ring-back time (2·τ_quench
  = 1.06 µs), so the gap cannot re-conduct before the tank would ring energy back — the U-tube "release at
  the top" holds at every corner. The S3-deferred local-loop question is answered: the quench is clean.

Loss ledger (mid): delivered 127.7 / arc 0.50 / loop-R 0.23 / residual-on-island 1.18 mJ — closes to
E_pre = 130 mJ at the integrator tolerance (6.9×10⁻⁸, self-test c).

## 4. The escalation — `ENERGY-BALANCE-GAP` (η_machine > 1) `[OC]`

`η_machine = E_tank,delivered / (W_mech,stator + W_mech,island)`. Per the **literal-trace** decision,
`W_mech,island` is the flying-bucket ½Q²·Δ(1/C) from the frozen `shuttle_core` trace (G3, z = 1.307, boost
40.5, ledger balanced to 5×10⁻¹⁵), anchored to 20 kV:

```
W_mech,island (literal flying bucket) = 1.58 mJ   (the collapsed 8 pF bucket holds 1.60 mJ at 20 kV)
W_mech,stator (inherited, 84fcaaa)    = 15.94 mJ
E_tank,delivered (fire ODE, mid)      = 127.7 mJ
=> eta_machine = 127.7 / (15.94 + 1.58) = 7.29   >> 1   UNPHYSICAL
```

**This is the finding (escalate), not a clean number.** The efficient fire delivers ~128 mJ *from a 648 pF
island charged to 20 kV (130 mJ)* — but the **literal flying-bucket shuttle trace performs only 17.5 mJ of
mechanical work per fire** (stator 15.9 + island 1.6). An efficiency above 1 is impossible, so the M2
island-dump (the 648 pF/130 mJ reservoir the S2/S3 **89 mJ single-kick reach relies on**) is **not
energetically sourced by the M1 flying-bucket trace** the rest of the campaign runs on. They are different
machines and cannot be mixed.

**What the gap names (the unaccounted ~112 mJ):** a self-consistent machine needs **one** of:
- **(M2 real):** the 648 pF island is genuinely charged to 20 kV (130 mJ) by a real mechanical path — then
  W_mech,island ≈ 130 mJ and η_machine ≈ 128/(15.9+130) ≈ **0.88** (an efficient machine, fire-path-set).
  But that 130 mJ of island-charging mechanical work is **absent from the shuttle trace** — it is the
  unmodelled input this block exposes.
- **(M1 literal):** the flying bucket delivers only ~η_fire·1.6 ≈ 1.6 mJ/fire — then the tank needs **~80
  fires** to reach 89 mJ, i.e. it is **not single-kick**, contradicting the S2/S3 reach regime.

Either way, **the S2/S3 89 mJ single-kick reach rests on an island-charging energy (~130 mJ/fire) that the
flying-bucket shuttle trace does not contain.** The reach margin should be re-examined against a
self-consistent island-charging model (the deferred S5 co-sim the s2-coupling block already flagged). The
fire *path* is not the problem — it is efficient; the *sourcing* of the M2 island is.

## 5. Verdicts (pre-committed)

- **`FIRE-PATH-RECOVERS`** ✓ — η_fire ≈ 0.985; the inductive C-L-C fire bypasses the stator C-C tax.
- **`S2-ETA-CONFIRMED`** ✓ — the dynamic transfer reproduces the 0.990 matched-cap formula (within ~0.5 %,
  arc + first-zero residual).
- **`QUENCH-AT-ZERO-CLEAN`** ✓ — extinguishes at the first current-zero (0.53 µs); τ_rec ≫ ring-back at all
  corners.
- **`ENERGY-BALANCE-GAP`** ⚠ **escalate** — η_machine = 7.3 > 1 (literal trace): the M2 island-dump reach
  is energetically inconsistent with the M1 flying-bucket trace; the ~130 mJ island-charging work is
  unaccounted. `MACHINE-ETA` is **not** a clean number — it is a flag.

## 6. Self-tests (all PASS)

(a) lossless **matched** LC swap (Cx=C_R, V_arc=R=0) → η_fire = 1.000 (integrator + S2-formula sanity);
(b) arc-dominated → η collapses 0.98→0.36 as V_arc 100→8000 V, E_arc grows ×240 (the localizer attributes
loss to the arc); (c) ODE energy closure delivered+arc+loop+residual = E_pre to 6.9×10⁻⁸; (d) ½·C_R·V_peak²
= 88.8 mJ ≈ S3 floor; (e) τ_quench = 0.530 µs = π·√(L_eff·C_eff).

## 7. Deliverables

`sim/fire_tank_transfer.py` (ODE + accounting + 5 self-tests) · `machine-energy-balance-findings.md` (this)
· `machine_energy_balance.csv` · `fire_transfer_trace.png` (I, V_island, V_tank vs t, current-zero marked)
· `fire_loss_ledger.png` (delivered/arc/loop/residual) · `machine_eta_vs_corner.png` (η_fire clean vs
η_machine > 1). Frozen modules byte-identical; **not merged** — left for TMD review (the GAP escalates).
