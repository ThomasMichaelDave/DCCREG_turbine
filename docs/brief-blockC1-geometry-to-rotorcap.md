# Brief — Block C-I: Plate Geometry → Rotor Capacitance

**For:** Claude Code (implementation agent)
**Host:** `index.html` — Symmetric Bennet Doubler 4-node pump-action calculator (vanilla JS, self-contained). **Integrate into it.**
**Reference:** `reference/SectoredDiscCalculator.jsx` — the parametric area engine whose math is ported here.
**Status:** specified, not yet implemented. [OC] for the physics/math; [IR] for device/modelling/integration choices.

> Discipline and symbol hygiene: see `CONVENTIONS.md`. Tags **[OC]/[IR]/[RH]** as defined there. The physics below is mainstream.

---

## 0. Inheritance

### 0.1 From the area engine (`reference/SectoredDiscCalculator.jsx`)
1. A plate = disc of outer diameter, divided into `Nsec` equal sectors, **alternating** sectors kept as conductor; plus a central conductive **ring** (annulus). **[given]**
2. The engine returns full-disc area, kept-sector (metal) area `Ametal`, and ring area `Aring`. **Port this math to plain JS functions** in the host script (§6). **[task]**

### 0.2 From the host (`index.html`) — do not break
1. **Solver:** `solveDoubler4(C1min, C1max, C2min, C2max, Ca, Cb, Cpar, opts?)` → median asymptotic doubling ratio `z`. **Leave untouched.** **[OC — host engine]**
2. **State/UI pattern:** `FIELDS` array (`{id, def, min, max, step}`), global `state`, `$ = id=>getElementById`, `bindField` wiring `#{id}-r` (range) + `#{id}-n` (number), `scheduleRecompute()` (60 ms debounce) → `recompute()`. **[match it]**
3. **Existing rotor fields:** `c1min c1max c2min c2max` (pF, range 1–3000); transfer/stray `ca cb cpar`. Doubler is symmetric (C1 = node 1↔gnd, C2 = node 4↔gnd); the solver schedules rotors **antiphase** (phase A: C1max/C2min; phase B: C1min/C2max). **[OC]**
4. **State sharing:** `loadFromHash`/`writeHash` serialise every `FIELDS` id into the URL hash. New numeric inputs join `FIELDS`; non-numeric ones are hashed manually. **[host feature]**
5. **Self-test culture:** `runSelfTest()` asserts reference points + a swap-symmetry check; the engine badge reflects pass/fail. Add plate self-tests likewise (§6.7). **[host feature]**
6. **Theme:** CSS variables (`--bg --panel --line --ink --dim --acc --good --warn --bad`), `.panel/.row/.kv/.badge`, monospace. New controls reuse these. **[host style]**

**Device mapping.** Two sectored-disc plates on a common shaft, the two rotor groups offset by one sector pitch, realise the host's antiphase rotors C1 and C2: when C1 is at `Cmax`, C2 is at `Cmin`. So one plate geometry feeds **both** rotors (symmetric design), `c1{min,max} = c2{min,max} = ` plate `{Cmin, Cmax}`. **[IR — physical realisation of the host's symmetric topology]**

---

## 1. Symbols

Use the symbol + host-field-id convention in **`CONVENTIONS.md`** verbatim. Load-bearing points: plate separation is `gap` (`g`), **never** `d`; water-vapour pressure is `pVap`, **never** `e`; rotor angle is `rotor` (`θ`), **never** `phi`; plate inputs take a **`p` prefix** (`pnsec pdia prouter prinner pgap ptempc ppatm prh`, plus `pdiel pring psrc plink`). The plate swing ratio `Cratio = Cmax/Cmin` **is** the host's `r₁`/`r₂` — no second UI name.

---

## 2. Capacitance model (port to vanilla JS)

### 2.1 Parallel-plate base law
$$C = \varepsilon_0\,\varepsilon_r\,\frac{A_\text{ov}}{g}, \qquad \varepsilon_0 = 8.8541878128\times10^{-12}\ \mathrm{F/m}.$$
Work in **SI** (metres, m²); scale the result to **pF** (`×1e12`) for the host fields. **[OC]**

*Idealisations:* fringing neglected (valid while `gap` ≪ smallest in-plane feature — warn if `gap` ≳ 10 % of the smaller of {smallest metal-sector arc width, ring radial width}); for a solid dielectric, `gap` = dielectric thickness. **[IR]**

### 2.2 Rotation-dependent overlap
Radial sector edges ⇒ overlap area linear in overlap angle ⇒ triangular fraction, period $2s_\theta$:
$$f_\text{ov}(\theta)=\left|1-\frac{\theta\bmod 2s_\theta}{s_\theta}\right|\in[0,1],\qquad s_\theta=360^\circ/N_\text{sec}.$$
$\theta=0$: full metal overlap ($f_\text{ov}=1$). $\theta=s_\theta$: sectors over gaps ($f_\text{ov}=0$). **[OC]**

### 2.3 Total facing area, ring floor, rotor extremes
$$A_\text{ov}(\theta)=A_m\,f_\text{ov}(\theta)+\chi_\text{ring}A_\text{ring},\qquad \chi_\text{ring}\in\{0,1\}\ (\texttt{pring}).$$
The ring is azimuthally symmetric ⇒ rotation-independent ⇒ a constant capacitance **floor**:
$$C_\text{max}=\varepsilon_0\varepsilon_r\frac{A_m+\chi_\text{ring}A_\text{ring}}{g},\quad C_\text{min}=\varepsilon_0\varepsilon_r\frac{\chi_\text{ring}A_\text{ring}}{g},\quad \kappa_C=\frac{C_\text{max}}{C_\text{min}}.$$
**Only `Cmin, Cmax` feed the doubler** (the two phase extremes). The full $C(\theta)$ curve is physical but unused by `solveDoubler4`; a θ-sweep plot is optional (deferred). If `pring` is off, `Cmin → 0` and `κ_C → ∞` — warn (host `r1/r2`, `z` blow up). The ring is the **`Cmin`-setting knob** keeping the swing ratio finite and tunable. **[IR]**

---

## 3. Dielectric model (→ `epsR`)

- **Vacuum:** $\varepsilon_r\equiv1$ exactly — humidity-independent by definition (no medium). No env inputs. **[OC]**
- **Air:** the one that genuinely varies (water-vapour dipole). Live model, §3.2. **[OC]**
- **Solids (mica, Kapton):** fixed nominal + tolerance band; weak humidity drift not modelled live. **[IR]**

### 3.1 Preset table
| Preset (`pdiel`) | $\varepsilon_r$ nominal | Model | Notes |
|:--|:--|:--|:--|
| Vacuum | 1 (exact) | constant | reference; hide env inputs |
| Air | ≈1.0006 | live §3.2 | $f(T,P_\text{atm},\mathrm{RH})$ |
| Kapton | 3.4 | constant (band 3.0–3.5) | expose band, not live model |
| Mica (muscovite) | 5.4 | constant (band 5.0–7.0) | low-loss precision staple |

### 3.2 Moist-air model
$$\varepsilon_{r,\text{air}}=1+2N_\text{air}\times10^{-6},\qquad N_\text{air}=77.6\frac{P_\text{atm}}{T}+3.73\times10^{5}\frac{p_v}{T^{2}}\ \text{(N-units)},$$
$T$ in K, $P_\text{atm},p_v$ in hPa. First term = dry density; second = water-vapour dipole (humidity term).
$$p_v=\frac{\mathrm{RH}}{100}p_\text{sat},\qquad p_\text{sat}=6.1121\exp\!\left[\left(18.678-\frac{T_C}{234.5}\right)\frac{T_C}{257.14+T_C}\right]\ \text{hPa (Buck 1981)}.$$
**Sanity assertion (self-test):** dry, 1013 hPa, 273.15 K → $N_\text{air}\approx288$ → $\varepsilon_r\approx1.000576$ (textbook ≈1.00059). Air vs vacuum differs <0.1 %; include for completeness, present honestly. Defaults: `ptempc=20`, `ppatm=1013`, `prh=50`. Show env inputs **only when Air is selected.** **[OC; IR for treating solids as constant]**

### 3.3 Rotary-varcap dielectric practicality (honesty note)
A *rotary* variable capacitor moves one plate relative to the other through the gap medium, so the dielectric is in practice **air or vacuum**. A solid film cannot be rotated against while bonded to both plates; it suits **fixed** or **sliding-with-film** geometries. Keep mica/Kapton selectable as what-if / fixed-gap exploration, but surface a one-line UI note when a solid is chosen in the rotary context. **[IR — realisability caveat]**

---

## 4. Outputs

**Driven into the host (plate mode on):** `state.c1min, c1max` (and `c2min, c2max` if linked) ← plate `Cmin, Cmax` (pF). The host's `z`, growth, `r₁/r₂`, headroom, and charts then update through its own `recompute`. **Do not duplicate them.**

**New local panel readouts:** `epsR` (6 dp when Air), `Ametal`, `Aring` (cm²), `Cmin`, `Cmax` (pF), `Cratio` (note "= r₁"). Optional fold: $A_\text{ov}(\theta)$ at current `rotor` and the C-vs-θ triangle. **[OC]**

---

## 5. Context

The host *is* the Bennet doubler engine (cross-coupled 4-node, ideal-diode 16-state search). This block supplies its physical front end (geometry → rotor caps). The plate's `κ_C` and `Cmax` are the host's gain driver (`r₁/r₂`) and throughput; the ring-as-`Cmin`-floor (§2.3) is a doubler tuning knob exposed through geometry. **[IR]**

Out of scope here (later block): dielectric-breakdown limits bounding safe voltage (couples to `gap`, `epsR`), conduction/leakage loss, and reconciling host pF ranges with realistic plate dimensions. **[scope marker]**

---

## 6. Implementation spec

**Rule:** geometry module = **producer** of the four rotor-cap state values; `solveDoubler4` = **consumer**, unchanged. Minimal coupling.

**6.1 Markup.** Add one `<section class="panel">` titled *"Rotor plate — geometry → capacitance"* above the "Rotor caps" panel. In host `.row` grids: numeric rows for `pnsec pdia prouter prinner pgap` (range + number + unit), reusing `bindField`; a `pdiel` `<select>` (Vacuum/Air/Kapton/Mica); `ptempc/ppatm/prh` rows (hidden unless Air); checkboxes `pring` (default **on**) and `plink` (default **on**); a `psrc` toggle (segmented buttons, host style): **manual** | **plate**; a `.kv` block for local readouts (§4) and a cm/in length-unit toggle.

**6.2 FIELDS + state.** Append numeric plate ids to `FIELDS` with sensible `def/min/max/step` (e.g. `pnsec` 2–48 step 1; `pgap` 0.01–10 mm). They hash-serialise for free. Serialise `pdiel/pring/plink/psrc` into the hash manually in `writeHash`/`loadFromHash`.

**6.3 Port the math** as plain functions (mirror the JSX, no JSX):
```
plateGeom(s)  -> { plateR, Ametal, Aring }     // SI; kept fraction = ceil(Nsec/2)/Nsec
epsAir(tempC, pAtm, rh) -> epsR                 // §3.2 (Buck + Smith–Weintraub)
epsR(s)       -> number                         // dispatch on pdiel
plateCaps(s)  -> { Cmin, Cmax, Cratio }         // pF; §2.3, honours pring (χ_ring)
```
Keep `eps0` and the Buck/Smith–Weintraub coefficients as named consts, each with a `// [OC] source` comment.

**6.4 Wire into `recompute` (one pre-step; solver untouched):**
```js
if (state.psrc === "plate") {
  const { Cmin, Cmax } = plateCaps(state);
  state.c1min = clampField("c1min", Cmin);
  state.c1max = clampField("c1max", Cmax);
  if (state.plink) { state.c2min = state.c1min; state.c2max = state.c1max; }
  syncFieldInputs(["c1min","c1max","c2min","c2max"]); // reflect into the (disabled) pF inputs
}
// ... existing recompute body runs as-is ...
```
In plate mode, **disable** the `c1*/c2*` inputs (derived); re-enable in manual mode.

**6.5 Field-range reconciliation.** Realistic plate values can exceed the rotor fields' `max:3000` pF. Either raise `c1*/c2*` `max` (e.g. to 10000) in plate mode, or clamp with a visible warning (`clampField` returns the clamped value and flags out-of-range). State the choice in an `// [IR]` comment. *(Open fork — see §7.)*

**6.6 Warnings** (dark-theme classes): `prinner ≥ prouter`; `prouter > pdia`; `pgap ≤ 0`; fringing (§2.1); `pring` off → `Cmin=0`, κ_C/`z` undefined; plate `Cmax` clamped; solid dielectric + rotary (§3.3).

**6.7 Self-tests.** Extend `runSelfTest()` with plate rows: (a) dry-air ε_r ≈ 1.000576 (§3.2) within tol; (b) a fixed-geometry C check, e.g. `pdia=10 cm, Nsec=12, ring off, gap=0.1 mm, vacuum → Cmax ≈ 348 pF` (compute exact in code) within tol. Surface in the existing self-test table.

**6.8 Presets.** Add 1–2 plate presets to `PRESETS` (e.g. `plate-air`, `plate-mica`) setting the `p*` ids and `psrc:"plate"`. Keep the electrical presets working (they imply `psrc:"manual"`).

**6.9 Discipline.** Reuse `CONVENTIONS.md` names verbatim. Keep `"use strict"`, `$`, `scheduleRecompute`. No `localStorage` (URL hash). Tag modelling choices `[OC]/[IR]/[RH]` in comments.

---

## 7. Open forks
1. **Field-range policy** (§6.5): raise-max vs clamp-and-warn — pick and document. **[IR]**
2. **Hash round-trip** for non-numeric controls (`pdiel/pring/plink/psrc`). **[task]**
3. **Solid-dielectric rotary realisability** (§3.3): gate solids behind a "fixed-gap" sub-mode? **[IR]**
4. **θ-sweep visualisation** (C-vs-θ triangle on a host canvas) — deferred; solver doesn't need it. **[deferred]**
5. **Dielectric strength per preset** → safe-voltage bound; conduction/leakage loss. **[OC, deferred — genuine next block]**
6. **Fringing correction** (Kirchhoff/Palmer effective area) for non-small `gap`. **[OC, deferred]**

---

## Appendix — equation & constant summary
$$C=\varepsilon_0\varepsilon_r A_\text{ov}/g,\quad \varepsilon_0=8.8541878128\times10^{-12}\,\mathrm{F/m}$$
$$f_\text{ov}(\theta)=\left|1-\tfrac{\theta\bmod 2s_\theta}{s_\theta}\right|,\quad s_\theta=360^\circ/N_\text{sec},\quad A_\text{ov}=A_m f_\text{ov}+\chi_\text{ring}A_\text{ring}$$
$$C_\text{max}=\varepsilon_0\varepsilon_r\tfrac{A_m+\chi_\text{ring}A_\text{ring}}{g},\quad C_\text{min}=\varepsilon_0\varepsilon_r\tfrac{\chi_\text{ring}A_\text{ring}}{g},\quad \kappa_C=C_\text{max}/C_\text{min}\ (=\text{host }r_1)$$
$$\varepsilon_{r,\text{air}}=1+2N_\text{air}\times10^{-6},\ N_\text{air}=77.6\tfrac{P_\text{atm}}{T}+3.73\times10^5\tfrac{p_v}{T^2},\ p_v=\tfrac{\mathrm{RH}}{100}p_\text{sat}$$
$$p_\text{sat}=6.1121\exp\!\left[\left(18.678-\tfrac{T_C}{234.5}\right)\tfrac{T_C}{257.14+T_C}\right]\text{hPa};\quad \varepsilon_{r,\text{vac}}=1,\ \varepsilon_{r,\text{Kapton}}\!\approx\!3.4,\ \varepsilon_{r,\text{mica}}\!\approx\!5.4$$
