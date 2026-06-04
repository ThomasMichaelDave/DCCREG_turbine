# Brief — Block R: Central Resonator (Conical Coil + Inter-Electrode Capacitor)

**For:** Claude Code (implementation agent)
**Host:** `index.html` — Symmetric Bennet Doubler calculator (vanilla JS, self-contained). **Integrate as a parallel panel + a cross-section update.**
**Status:** specified, not yet implemented. `[OC]` for the EM/math; `[IR]` for modelling/rendering choices.

> Discipline + symbol hygiene: `CONVENTIONS.md`. **All mainstream EM** — circular-loop self/mutual inductance, parallel-plate capacitance, LC resonance, skin effect, spark-gap (break-rate) drive. **No DCCREG theory.** (README firewall.)

---

## 0. Inheritance & relation to Blocks C-I / M

- **Consumes** Block M geometry (`coneR`, cone slant `= coneR·√2`, `discH`) and Block C-I (the **aligned** electrode metal area, and `εr` of the disc dielectric — mica). **Independent producer:** never writes `c1*/c2*`, never calls `solveDoubler4` (cf. M, brief §6.4). Produces resonator readouts + adds the coil to the cross-section. **[OC]**
- **Depends on the C-I area fix** (review finding): `C_R` uses the corrected sectored-annulus area `[ring-out → plate]`, not the full-disc overcount. If that fix is unapplied, `C_R` inherits the ~2 % error. **[flag]**
- **Design premise (locked by user):** the two rotor electrodes **fully align**; the doubler's antiphase pumping is provided by **stator** angular offset, not rotor offset. This is what makes a real through-mica `C_R` exist — without it there is no core resonator. **[IR — locked]**

**Topology.** The two cone coils are in series (apex-to-apex, aiding), bridging the two rotor electrodes; the through-mica capacitor `C_R` bridges the same two nodes. `C_R ∥ L` is a parallel tank. The charge pump delivers a HV pulse train (spark-gap/diode firing) that excites the tank; it rings at `f0` and decays with `τ`. **[OC]**

```
electrode C1 ──[coil ↑ cone1]── apex1 ─── apex2 ──[coil ↓ cone2]── electrode C2
     └──────────────────── C_R (through the mica disc) ───────────────────────┘
```

---

## 1. Symbols (additions to `CONVENTIONS.md` §2)

`d` remains **forbidden**; explicit `OD/ID/*Dia`. New ids take an **`r` prefix** (no clash with `c*`/`p*`/`m*`; DOM range/number suffixes `-r`/`-n` still apply).

| Quantity | Symbol | Code | Notes |
|:--|:--|:--|:--|
| Conductor type | — | `rcond` | `wire` \| `tube` |
| Wire gauge (AWG) | — | `rawg` | ⇄ diameter ⇄ cm² (table) |
| Tube outer / inner ⌀ | — | `rtubeOD`,`rtubeID` | mm; capillary option (ex. 3 / 1) |
| Insulation/varnish thickness | — | `rins` | mm; **user input** (local stock) |
| Rotor speed | — | `rrpm` | drives PRF |
| Stray capacitance | — | `rstray` | pF; small knob |
| Conductor outer ⌀ / Cu area | — | `condOD`,`condArea` | derived (wire or tube) |
| Winding pitch | $p$ | `pitch` | `condOD + 2·rins` |
| Turns per cone / total | $N$ | `Nturn` | derived `= ⌊slant/pitch⌋` |
| Inductance (series, both cones) | $L$ | `L` | loop-stack sum |
| Inter-electrode capacitance | $C_R$ | `C_R` | through-mica, aligned area |
| Coil self-capacitance | $C_{self}$ | `Cself` | Medhurst-style estimate **[IR]** |
| Total tank capacitance | $C_\Sigma$ | `Ctot` | `C_R + Cself + rstray` |
| Resonant / damped freq | $f_0,f_d$ | `f0`,`fd` | `f0=1/(2π√(LC))` |
| Characteristic impedance | $Z_0$ | `Z0` | `√(L/C)` |
| Quality factor | $Q$ | `Q` | `ω0L/R_ac` (copper-only) |
| Ringdown time constant | $\tau$ | `tau` | `2L/R_ac` |
| Skin depth @ f0 | $\delta$ | `delta` | `√(ρ/(π f0 μ0))` |
| Pulse repetition freq | $f_{PRF}$ | `prf` | `⌈Nsec/2⌉·rrpm/60` |

---

## 2. Inductance — conical loop-stack [OC]

A single-layer close-wound 45° conical helix is an exact stack of coaxial loops. With pitch `p = condOD + 2·rins` and slant `= coneR·√2`:

```
Nturn = floor(slant / p)                          // per cone (derived, not input)
turn k: radius r_k = coneR − (k+0.5)·p/√2 ,  axial z_k = ±(discH/2 + (k+0.5)·p/√2)
```
Build the full stack: cone1 (`z>0`) + cone2 (`z<0`, mirrored), **all same rotational sense (aiding)**.

```
L = Σ Lself(r_k, a) + ΣΣ_{i<j} 2·M(r_i, r_j, |z_i−z_j|)
Lself = μ0·r·(ln(8r/a) − 2)            // HF (current on surface); a = condOD/2
M     = μ0·√(r1 r2)·[(2/k − k)K(k) − (2/k)E(k)] ,  k² = 4 r1 r2/((r1+r2)² + d²)
```
`K,E` complete elliptic integrals via **AGM** (no library). **Performance:** O((2N)²). For `2N > 800`, decimate the stack to ≤400 nodes (group `g` adjacent turns; scale that node's mutual by `g²`, self by `g` + intra-group term) so recompute stays live; flag the decimation. **[OC]**

---

## 3. Capacitance [OC for C_R; IR for Cself]

```
C_R  = ε0·εr_disc·A_align / discH          // through the mica septum
A_align = Ametal(annulus) + Aring          // electrodes FULLY ALIGNED (locked premise)
Cself ≈ Medhurst(coneR, axial length)      // turn-to-turn; estimate only [IR]
Ctot  = C_R + Cself + rstray
```
`εr_disc`, `A_align` from C-I (corrected area); `discH` from M. With thin mica + large area `C_R` dominates (ex. ≈1.9 nF), so `Cself` (a few pF) is usually negligible — but report both and the coil's own self-resonant frequency so dominance is visible. **[OC/IR]**

---

## 4. Loss & resonant outputs [OC circuit; loss model partial]

```
length = Σ 2π r_k                                   // total conductor length
R_dc   = ρ_cu·length / condArea
δ      = √(ρ_cu/(π f0 μ0)) ;  R_ac = ρ_cu·length/(π·condOD·δ)   // outer-surface
f0 = 1/(2π√(L·Ctot)) ;  Z0 = √(L/Ctot)
Q  = ω0·L / R_ac ;  τ = 2L/R_ac ;  f_d = f0·√(1 − 1/(4Q²))
E_pulse = ½·Ctot·V_pulse²                            // V_pulse from doubler output (input)
```
> **Q is copper-only and OPTIMISTIC.** Real Q is set by mica dielectric loss (tanδ) and the **spark-gap/diode loss**, both far larger. Report copper-limited Q labelled as an upper bound; keep dielectric + gap + radiation loss as a **deferred refinement**, do not assert the figure as the operating Q. **[OC for copper; deferred otherwise]**

**Capillary-tube note (verified).** At `f0 ≈ 238 kHz`, `δ ≈ 134 µm` ≪ the 1 mm wall, so current rides the outer surface only: an **OD3/ID1 tube ≈ a solid 3 mm rod** in L, C, f0, Z0, Q — identical RF behaviour at ~11 % less copper and far less mass (cooling/pressurisation possible). The `wire | tube` toggle lets the user see this directly. **[OC]**

---

## 5. Drive from rotor RPM [OC/IR]

6 kept sectors ⇒ 6 capacitance phases per revolution; the spark gaps (D1,D3,D2,D4…) fire once per phase:

```
prf        = ⌈Nsec/2⌉ · rrpm / 60          // Hz   (ex. 6·rrpm/60)
ringCycles = f0 / prf                       // f0 oscillations per drive pulse
settle     = τ · prf                         // <1: rings decay between pulses (isolated)
                                             // >1: successive rings overlap (build-up)
```
`prf ≪ f0`, so the tank is **not** driven at resonance — each pulse triggers a ringdown. The regime boundary `settle ≈ 1` (ex. ~4500 rpm) is the headline drive output: report `prf`, `ringCycles`, `settle`, and which regime. `Nsec` from C-I; `rrpm` is the new input. **[OC for the kinematics; IR for the regime reading]**

---

## 6. Conductor input (AWG ⇄ cm² ⇄ ⌀; or tube) [OC]

`rcond = wire`: `rawg` (AWG int) → `condOD`, `condArea` via a built-in AWG table; show **both** AWG and cm²/mm². `rcond = tube`: `rtubeOD/rtubeID` → `condOD = rtubeOD`, `condArea = π((OD/2)²−(ID/2)²)`. `rins` adds to pitch (and to `Cself`). A manual `condOD` override is allowed. **[OC]**

---

## 7. Outputs (new local panel; nothing into the solver)

`.kv`: `Nturn`, `condOD`/`condArea` (AWG + cm²), `length`, `L`, `C_R`/`Cself`/`Ctot`, `f0`, `f_d`, `Z0`, `Q` (flagged upper-bound), `τ`, `R_dc`/`R_ac`, `δ`, `prf`(@`rrpm`), `ringCycles`, `settle`+regime, `E_pulse`. Mass/inertia deferred (with M). **[OC]**

---

## 8. Cross-section update + colour-hatch legend (the picture) **[IR rendering]**

Extend the existing `drawCrossSection(s)` (do not add a canvas) to draw the **resonator coil** and to introduce a **colour + hatch legend** keyed across all calculators — the intuitive-UI requirement.

**Coil rendering.** Along each cone's slant, draw the winding as a **copper-coloured diagonal hatch band** hugging the cone profile (band thickness ∝ `condOD` to scale; hatch line spacing ∝ `pitch`, representative — decimate the drawn strokes if `Nturn` is large). Tube vs wire shown by an open (ring) vs filled stroke. The apex-to-apex link is a thin connector. The coil turns red (`--bad`) if a Block-R guard trips (e.g. `pitch > slant` → < 1 turn; `Nturn` non-physical).

**Colour + hatch legend (new `--copper`, `--steel`, `--diel` CSS vars).** A small legend block beside the canvas; **the same swatch appears next to each calculator's matching readouts**, so a number ties visually to a region:

| Feature | Colour | Hatch | Legend label | Readouts carrying the swatch |
|:--|:--|:--|:--|:--|
| Resonator coil | `--copper` | diagonal | "resonator coil (L)" | Block R: `L, f0, Q…` |
| Rotor electrodes | `--acc` | vertical (existing "sectored") | "rotor electrodes C1/C2" | C-I: `Cmin/Cmax`; R: `C_R` |
| Fixed stators | `--dim` | dotted | "fixed stators (gap g)" | C-I: `g` |
| Dielectric disc / septum | `--diel` | cross-hatch | "mica disc / septum" | M: `discH`; R: `C_R` |
| Quadricone hubs | `--ink` | solid | "quadricone hubs" | M: `hubDia, coneR` |
| Spherical void / bore | `--bg` | none (cavity) | "void / bore" | M: `voidDia, clearEE` |
| Shaft stubs | `--steel` | solid | "stub shafts" | M: `shaftDia` |

Legend entries are toggle-able with the existing `dims` overlay. **[IR]**

---

## 9. Implementation spec

**9.1 Markup.** One `<section class="panel">` "Central resonator (conical coil + inter-electrode C)"; numeric `.row`s for `rawg rtubeOD rtubeID rins rrpm rstray` (+ `rcond` segmented `wire|tube`, manual-OD chk); a `.kv` block (§7); the legend block (§8) beside the existing cross-section canvas. **`r`-prefix ids.**

**9.2 FIELDS + state.** Append the `r*` numeric fields (sane def/min/max/step: `rawg` 8–40; `rtubeOD` 0.5–10; `rtubeID` 0–8; `rins` 0–1 step 0.01; `rrpm` 0–30000; `rstray` 0–500). Controls `rcond`, manual-OD → `MECH_CTL_DEFAULTS`-style block. Hash-serialise all (incl. `rcond`).

**9.3 Functions** (plain JS, `// [OC] source` notes):
```
ellipKE(m)->{K,E}            // AGM, no library
Mloop(r1,r2,d), Lself(r,a)   // §2
awgToCond(awg)->{condOD,condArea}     // AWG table
resonatorCore(s)->{ Nturn, condOD, condArea, length, L, C_R, Cself, Ctot,
                    f0, fd, Z0, Q, tau, Rdc, Rac, delta, prf, ringCycles,
                    settle, regime, guards, bind, warns }
```
Consumes `coneR/slant/discH` from `quadriconeCore(s)` and `{A_align, epsR_disc, Nsec}` from the C-I producer. **No solver wiring.**

**9.4 drawCrossSection update + legend** per §8; new CSS vars `--copper/--steel/--diel`; canvas diagonal/cross/dotted hatch helpers; swatch spans injected next to the relevant `.kv` rows in all three producer panels.

**9.5 Self-tests** (extend `runSelfTest`): (a) `ellipKE(0) → K=E=π/2`; (b) capillary default (coneR 75, mica 10, εr 5.4, OD3/ID1) → `f0 ≈ 238 kHz`, `L ≈ 235 µH`, `C_R ≈ 1.9 nF` (tol); (c) **tube OD3/ID1 vs solid rod OD3 → equal f0 & Q** (HF surface identity); (d) `awgToCond(20).condOD ≈ 0.812 mm`; (e) `prf(Nsec 12, 3000 rpm) = 300 Hz`.

**9.6 Presets.** Add `resonator` (the capillary-tube showcase) setting `r*` + a coupled rotor-core base; leave electrical/plate fields intact.

**9.7 Discipline.** `"use strict"`; URL-hash state (no `localStorage`); `[OC]/[IR]/[RH]` tags; small commits + CHANGELOG.

---

## 10. Open forks
1. **Dielectric + spark-gap loss → real Q** (the genuine Q; couples C-I mica tanδ + the gap model). **[deferred]**
2. **Coil self-capacitance** beyond the Medhurst estimate (conical correction). **[IR]**
3. **Resonant build-up dynamics** in the `settle > 1` regime (pulse-train transient, not just single ringdown). **[deferred]**
4. **RPM ↔ mechanical block** (mass/inertia/balance feed the achievable `rrpm`). **[deferred — flywheel block]**
5. **Loop-stack decimation accuracy** bound for very fine wire. **[task]**

---

## Appendix — equation summary
```
pitch = condOD + 2·rins ;  Nturn = ⌊coneR√2 / pitch⌋ (per cone)
L = Σ Lself + ΣΣ 2M  (aiding, both cones) ;  Lself=μ0 r(ln(8r/a)−2) ;  M via K,E(AGM)
C_R = ε0·εr·A_align/discH (aligned electrodes) ;  Ctot = C_R + Cself + rstray
f0 = 1/(2π√(L Ctot)) ;  Z0=√(L/Ctot) ;  Q=ω0L/R_ac (Cu-only, upper bound) ;  τ=2L/R_ac
R_ac = ρ_cu·length/(π condOD·δ) ,  δ=√(ρ_cu/(π f0 μ0))   // tube ≈ solid rod at HF
prf = ⌈Nsec/2⌉·rrpm/60 ;  ringCycles=f0/prf ;  settle=τ·prf  (≈1 ⇒ regime boundary)
```
