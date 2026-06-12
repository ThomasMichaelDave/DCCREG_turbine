# resonator-accum — findings (rev 0.1): **ACCUM-DC-PREFERRED**

**Primary recommendation:** `ACCUM-DC-PREFERRED` — the DC route (charge parked on C_R, transferred
through L_RES) dominates on **stored energy × retention × transfer efficiency at realizable (existing)
hardware**; both AC routes require a kHz-class f₀ redesign to even build energy. Standalone numeric
deliverable: **HF-DAMPING-SPEC ≥ 2× (mid corner)**.

Branch `resonator-accum` from `spark-derate` head. `reference/doubler_core.py` frozen/untouched;
`shuttle_core.py` carries **one additive, regression-gated change** (a kick-train exporter) — the pump
verdicts are untouched (V3). `resonator_accum.py` is a separate consumer-producer modelling the 5–6 ring
as LCR. Not merged.

**Governing quantity [OC]:** for incoherent kicks into an LCR tank, E_ss ≈ ΔE_kick·M with
**M = Q_loaded·PRF/(2π·f₀)** (the q·v(φ) cross-term averages to zero under jitter). At the spark-derate
point (Q_loaded≈400 mid, PRF=300 Hz, f₀=326 kHz): **M ≈ 0.06** (0.15 at the Q≤1000 ceiling) — the tank
holds ~one kick's energy. Sub-battery by ~2 orders of magnitude.

**Loaded-Q discipline:** every M uses **Q_loaded** = Q_unloaded × {opt 0.70, mid 0.40, pess 0.20}.
Q_unloaded ≤ 1000 (copper-only, `report-tool-functioning.md`) is the labelled ceiling only.

**Firewall (§2.6) honoured:** the HF-retention rationale is parked **[RH], not load-bearing**; the only
HF claim here is the §1.4 damping spec, which bounds HF retention from *above*. No result below is
phrased in terms of the parked rationale.

**No BLOCKER.** Tank params are consistent (`L_RES=123 µH`, `C_R=1.91 nF`, `f₀=326 kHz` — the 238 kHz
figure is *resolved/superseded*, not contradictory). DC leakage is deferred in-repo → mica volume
resistivity cited from standard references (ρ_v 10¹³–10¹⁵ Ω·m) and **swept**.

---

## A0 — gate (V1/V2/V3 pass before any route claim)

| ID | test | criterion | result |
|---|---|---|---|
| V1 | single-kick ringdown | decay = τ_E=Q/(2π·f₀) within 1%; integrator energy ledger <1e-6/ring | **PASS** (τ rel 1e-7, ledger 1.8e-8) |
| V2 | incoherent closed form | sim E_ss reproduces ΔE_kick·M within 5% (idealized) *before any other claim* | **PASS** (rel 1.2% at M=20) |
| V3 | regression | spark-derate T0a–c pass on `shuttle_core` defaults after the export change | **PASS** (anchor 1.2033, z 1.18938, ledgers) |

The simulator earns trust by reproducing the closed form (V2) before extending beyond it. The kick-train
export (`export_kick_train`) reads the existing `leds` (`fire_out`=charge, `th_fire`=angle, jitter, mode)
— purely additive, ideal path byte-identical.

## A1 — DC route (V6 ledger) — the recommended primary

C_R charged to the 20 kV clamp by the existing ratchet; self-discharge `τ_leak = ρ_v·ε₀·ε_r`
(geometry-independent); resonant in/out through L_RES at `η = exp(−π/2Q_loaded)`.

| corner | E_store | τ_leak | transfer η |
|---|---:|---:|---:|
| opt | 382 mJ | 13.3 h | 0.998 |
| mid | 382 mJ | 1.33 h | 0.996 |
| pess | 382 mJ | 8.0 min | 0.992 |

Energy ledger conserves < 1e-6 per operation (**V6 PASS**). Stored **0.38 J** retained over minutes–hours
and transferred at **>99%** — a usable accumulator at *existing* hardware (C_R + L_RES already in the design).

## A2 — incoherent AC (M-map)

M over (f₀ via L·C grid × Q_loaded × rpm). At 326 kHz, M≈0.06–0.15 (sub-battery). **M≥10 exists only via
a kHz-class f₀ redesign** (large L_RES):

| f₀ | rpm | M (mid) | implied L_RES |
|---:|---:|---:|---:|
| 10 kHz | 30 000 | 19.1 | 133 mH |
| 2 kHz | 10 000 | 31.8 | 3.3 H |
| 2 kHz | 30 000 | 95.5 | 3.3 H |

6 mid-corner triples reach M≥10, 3 reach M≥50 — all at f₀ ≤ 10 kHz with **L_RES from 133 mH to 3.3 H**
(vs the present 123 µH). Realizable only as a dedicated battery-grade loop-stack (hardware doc §6), and at
the cost of rotor mass/inertia (hardware doc §1). Recorded with its shortfall, **not** the primary.

## A3 — coherent (passive injection-locking, V5/V4)

Gap-threshold modulation by superposed tank voltage as a phase-selection rule with coupling κ. V5: lock
declared only if energy growth ≥ 3× the diffusive baseline (averaged over 10 seeds, V4).

| tank | κ_threshold (3×) | behaviour |
|---|---|---|
| current 326 kHz (M≪1) | **None** | saturates at 2.8× — too lossy for multi-kick buildup |
| battery-grade 2 kHz (M≈95) | **κ ≥ 0.25** | strong lock (58× at κ=0.25) |

**Coherent lock is impossible at the present tank** (same root cause as incoherent: M≪1, kicks decay
before the next), but **viable after the kHz redesign** from a modest κ≥0.25. Per the brief, if this route
were adopted the **coupled pump+tank model is the follow-on gate** — but it is gated behind the same
redesign the incoherent route needs, so it does not change the primary.

## HF-DAMPING-SPEC (standalone numeric deliverable, A4/V7)

The undamped HF ring residue superposes on the gap voltage — a mis-trigger mechanism for the
threshold-fired gaps. Consumer-level approximation of the T2a/T2e re-check (brief §3): require
`residue/damping < min(T2a, T2e)` voltage margins (T2a=0.60, T2e=0.40 of strike, from the spark-derate
backstop geometry `pVbkBackstop_frac=0.6`).

| corner | undamped residue (of strike) | **minimum damping** |
|---|---:|---:|
| opt | 0.30 | **1×** (already below margin) |
| mid | 0.50 | **2×** |
| pess | 0.70 | **2×** |

**HF-DAMPING-SPEC = ≥2× damping of the loss-spectrum HF residue** (mid/pess), re-verified at the spec
(**V7 PASS**: residue below both margins; the producer ordering margin `_backstop_ordering_margin` stays
robust at 0.0). This feeds the L_RES winding design (bounds HF retention from above — firewall-consistent).

## Comparative route table

| route | stored energy | retention | efficiency / viability | hardware |
|---|---|---|---|---|
| **DC (primary)** | 0.38 J on C_R | minutes–13 h (mica ρ_v) | η > 99% transfer; ledger exact | **existing** (C_R + L_RES) |
| incoherent AC | E_ss=ΔE·M; M≈0.06 now | tank-Q limited | M≥10 only at f₀≤10 kHz | kHz redesign, L 133 mH–3.3 H |
| coherent AC | locks at battery grade | tank-Q limited | κ≥0.25 at 2 kHz; none at 326 kHz | kHz redesign + follow-on coupled gate |

## Verdict & consequence

**ACCUM-DC-PREFERRED.** The DC route is the preferred electrostatic battery: it stores ~0.38 J retained
over minutes–hours and transfers at >99% using hardware already in the design, with self-discharge set by
mica leakage (not tank Q). The AC routes (incoherent M≥10, coherent lock κ≥0.25) are **recorded with their
shortfall**: both demand a kHz-class f₀ redesign (L_RES 0.13–3.3 H, large rotor-mass cost) before they
build any energy; coherent then additionally requires the coupled pump+tank follow-on gate. The
**HF-DAMPING-SPEC (≥2×)** is delivered standalone for the L_RES winding. Hardware context recorded in
`docs/resonator-battery-hardware.md`.

## Constraints honoured / scope

- `reference/doubler_core.py` untouched; the `shuttle_core.py` change is the additive kick-train export only
  (V3: T0a–c byte-identical). Pump verdicts untouched.
- Loaded-Q discipline; three corners throughout; tank params cited verbatim; mica ρ_v cited + swept.
- Firewall §2.6 honoured (parked rationale not load-bearing; HF claim is the §1.4 damping spec only).
- **Out of scope (deferred):** coolant bore, Block-M quadricone FEA, HV insulation coordination, the
  bootstrap two-threshold loop, the coupled pump+tank lock model (follow-on, conditional on a kHz redesign),
  electrode erosion, gas handling. Not merged to `main`.
