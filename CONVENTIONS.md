# Conventions

The single source for tier tags, symbol hygiene, and working rules. Both the docs and the implementation must follow this file.

---

## 1. Epistemic tags

- **[OC] Operational Core** — standard derivable physics/math; true independent of this project.
- **[IR] Interpretive Reading** — a modelling / engineering choice; internally consistent, chosen.
- **[RH] Resonance / Heuristic** — suggestive, not load-bearing.

Apply to every substantive claim in docs and to every modelling choice in code comments. Keep the tiers honest.

---

## 2. Symbol hygiene (mandatory)

**One letter, one meaning.** Never reuse a reserved physics symbol for a geometric quantity.

**Reserved — do NOT repurpose:** `C` (capacitance); `ε₀, ε_r` (permittivity); `A` (area); `V, Q, E, e` (voltage, charge, field, elementary charge); `n` (refractive index); `d` (avoided entirely — ambiguous "diameter" vs "plate separation").

### Project variables (symbol · code name)

| Quantity | Symbol | Code | Notes |
|:--|:--|:--|:--|
| Sector count | $N_\text{sec}$ | `Nsec` | integer; **not** `n` |
| Plate outer diameter | $\varnothing_p$ | `plateDia` | |
| Plate radius | $R_p$ | `plateR` | $=\varnothing_p/2$ |
| Ring outer / inner diameter | $\varnothing_{ro},\varnothing_{ri}$ | `ringOuter`,`ringInner` | |
| **Plate separation (gap)** | $g$ | `gap` | **`g`, never `d`** |
| Rotor angle | $\theta$ | `rotor` | **not** $\varphi$ (potential) |
| Sector angular pitch | $s_\theta$ | `pitch` | $=360^\circ/N_\text{sec}$ |
| Overlap fraction | $f_\text{ov}$ | `fOv` | $[0,1]$ |
| Metal (kept) area, one plate | $A_m$ | `Ametal` | |
| Ring area | $A_\text{ring}$ | `Aring` | |
| Facing overlap area | $A_\text{ov}$ | `Aov` | rotation-dependent |
| Relative permittivity | $\varepsilon_r$ | `epsR` | |
| Plate capacitance | $C$ | `cap` | |
| Plate min/max/ratio | $C_\text{min},C_\text{max},\kappa_C$ | `Cmin,Cmax,Cratio` | $\kappa_C$ = host's `r₁`/`r₂` |
| Air refractivity | $N_\text{air}$ | `Nrefr` | distinct from `Nsec` |
| Temperature | $T$ / $T_C$ | `tempK`/`tempC` | |
| Atmospheric pressure | $P_\text{atm}$ | `pAtm` | hPa; **not** bare `P` (power) |
| Water-vapour pressure | $p_v$ | `pVap` | hPa; **not** `e` |
| Saturation vapour pressure | $p_\text{sat}$ | `pSat` | hPa |
| Relative humidity | RH | `rh` | percent |

### Host-field-id mapping (avoid collisions with the existing simulator)

The host `index.html` already owns the input ids `c1min c1max c2min c2max ca cb cpar`. **New plate inputs take a `p` prefix** so nothing collides and the host's `#{id}-r`/`#{id}-n` + URL-hash machinery is reused verbatim:

`pnsec` · `pdia` · `prouter` · `prinner` · `pgap` · `ptempc` · `ppatm` · `prh`

Non-numeric controls (no `-r`/`-n` pair; serialise into the hash manually): `pdiel` (dielectric `<select>`), `pring` (ring-conductive checkbox), `psrc` (rotor source: manual | plate), `plink` (link C2 to C1).

**Naming note.** The plate swing ratio $\kappa_C = C_\text{max}/C_\text{min}$ is *identically* the quantity the host already displays as **r₁/r₂** and sweeps in its "z vs rotor swing ratio r" chart. Do not introduce a second name in the UI.

### Switch naming

`solveDoubler4`'s ideal diodes **`D1–D4`** (`D1:2→0  D2:3→0  D3:1→3  D4:4→2`) are the
**canonical** switch names. The physical spark-gap commutator aliases them as **SG1–SG4**
(SG1↔D1 … SG4↔D4); see `docs/commutator-design.md §2`. Use `D1–D4` in engine/solver
contexts and SG1–4 only when discussing the physical commutator. The solver's ground (0) is
the physical resonator rail (5–6); it is a near-short at PRF (L1-short argument).

---

## 3. Working conventions

- **Derive a coherent frame, then consolidate.** Land changes as small, reviewable commits.
- **Correct openly** when rigor demands; record the correction and its reason in `CHANGELOG.md`.
- **Flat filenames.** Git + `CHANGELOG.md` own history — no `_vNN` filename suffixes, no per-file revision tables. A doc may carry a one-line *Status* note (tier + one-line state), nothing more.
- **Deliverables are markdown;** the app is a single self-contained `index.html` (no build, no bundler, URL-hash state — never `localStorage`).
- **Cross-reference** docs by repo-relative path.
- **Producer/consumer discipline** for the physics: the geometry module produces rotor-cap values; `solveDoubler4` consumes them and is never edited by feature work.

---

## 4. Block namespaces

Each producer block owns a prefix; `d` alone stays forbidden (ambiguous diameter / separation).

### Block C-I — clearance inputs (`p`-prefix, mm)

```
pvoid (inner HV clearance, tank↔stator), pbus (stator outer bus),
pquadfoot (steel-core footprint band), pquadclr (core collision clearance).
```

Two plate areas now exist and **must not be conflated**:

```
Ametal_full   = full rotor face  → C_R  (rotor↔rotor, resonatorCore)
Ametal_active = squeezed overlap → C1/C2 (rotor↔stator, plateCaps)
```

The active band runs `[ro + pvoid, plateR − pbus − (pquadfoot + pquadclr)]`; clearances are mm regardless of `punit`. The squeeze shrinks the **pump** only — `C_R`/`f0` keep the full face.

### Block T — transfer caps (prefix `tc*`, mm/nF)

```
tcMode, tcPlacement, tcCaNF, tcWidthMm, tcMylarEr, tcMylarThkMm,
tcInnerPinMm (radial inner-pin clearance), tcVkV,
tcBracketMm (AXIAL Ca/Cb standoff height, mm — cross-section render)  [inputs]
tcWidthOutMm, tcRingInnerMm, tcRingOuterMm, tcCaOutNF,
tcAreaM2, tcFieldKVmm, tcEnergyJ, tcCaMaxNF                 [outputs]
```

Note: `tcBracketMm` is the **axial** standoff of the Ca/Cb carrier off the stator back (render). The **radial** inner-pin clearance (`rRingInner = rActiveInner + pin`) is `tcInnerPinMm` — the two are distinct and must not be conflated.

- Bus ring = **SOLID annulus** (full area, **no keptFrac**) — it buses the sectors and is the lower Ca/Cb plate.
- Consumes `rActiveInner` / `rActiveOuter` from `plateGeom`. **Producer** — feeds (never edits) `solveDoubler4`; the optional `tcDrive` wiring routes the realised Ca = Cb into the solver's transfer-cap state at the call site only (raises their field max, nF-scale).
- `t` alone stays forbidden; `tc` is the Block-T prefix.

### Design-flow + presets

```
Masters (primaries): pdia, prouter, prinner, pgap, pnsec, pdiel, rrpm, vhvKV,
vhvEkVmm, demQuadConeRmm, tcMylarEr, tcMylarThkMm, tcRatio, demCapRatingKV, mdisch.
Derived (slaved) via five default-on/overridable toggles (cascadeState, one pass):
  vhvLink    : pvoid, tcVkV, demBiasKV  ← vhvKV (pvoid = vhvKV/vhvEkVmm)
  quadLink   : pquadfoot                ← 2·demQuadConeRmm
  demRpmLink : demRpm                   ← rrpm
  demEvLink  : demEventsPerRev          ← ⌈pnsec/2⌉   (makes R≡D PRF)
  tcFromCmax : tcCaNF = tcRatio·Cmax    → drives the solver Ca/Cb
```

- Presets are JSON of **primaries + toggles + an `expect` block**; loaded via "Load parameter set" (`FileReader`), applied to `state`, then the one-pass cascade runs and `expect` is checked within tolerance. "Save current as preset" exports a scaffold. **No magnitude is hard-coded in docs** — the calculator computes it and the preset asserts it (`expect`, with `tol`); checkable outputs are the explicit `presetExpectGetters` set.
- Persistence is **local file I/O only** (`FileReader` / `Blob`+anchor). No network, no `localStorage`. `solveDoubler4` untouched.

### Block S — firing sequence & clocking (prefix `s*`, presentational sink)

```
snshow, sf0 (0=auto Block-R f₀), sq0 (0=auto Block-R Q), svfire (reserved),
sfollow (boolean, manual hash)                              [inputs]
```

- Read-only **sink**: `traceDoubler4` is a byte-frozen-primitive sibling of `solveDoubler4` (a self-test asserts equal `z`); Block S consumes its trace plus geometry `Nsec` (`pnsec`) and the single timing source `machinePRF()` = `⌈pnsec/2⌉·rrpm/60`. It never writes solver state.
- `s` is the Block-S prefix; never feeds the solver path. Tank f₀/Q default to the live Block-R values (`sf0`/`sq0` = 0 ⇒ auto) — no hard-coded magnitudes.

### Block D — distributed electromagnet motor (prefix `dem*`)

```
demRpm, demEventsPerRev, demDriveMode, demCapBlockNF, demCapRatingKV,
demCapTopology, demBiasKV, demRippleV, demPoleAreaCm2, demClearanceMm,
demNGaps, demWireAWG, demTurnLenCm                         [inputs]
demPrfHz, demDriveHz, demLcoilH, demTurns, demZ0Ohm, demRcoilOhm,
demQ, demRippleMaxV, demIcircMaxA, demNI, demVcapPeakKV,
demEnergyJ, demCapPerGroupUF                               [outputs]
```

- **Rule:** `d` alone remains forbidden; `dem` is the Block-D prefix. Reserved symbols keep their meaning — `C` (the resonant DC-block cap), `V` (voltages), `A` (pole-face area), `Q` (quality factor, not charge here — disambiguated by context and the `dem`-prefixed code names), `N`·`I` (ampere-turns).
- **Producer/consumer:** Block D is a **parallel producer** (like Blocks M and R) — it reads electrical/geometry context but **never** writes the rotor caps and **never** calls `solveDoubler4`.
- The 13 logical output names above are computed inside `demMotor()`; the panel surfaces them in grouped readout rows (`#dr-*`) plus the top-view projection.


## Working rule — resonant tax-recovery is a property of sinks (the equalization-is-the-pump principle)

> **A resonant pump's own equalization cannot be resonated for energy recovery — the equalization *is* the
> pump.** Resonating it clamps it (ratchet, tax lost) or breaks the ratchet (pump dies); sequencing and
> statistics only sample those two arms, never a recovering third. **Only a downstream sink transfer recovers
> freely.**

Established by: `doubler-resonant` (diode α_max 0.28 ceiling) + `ngspice-s3` (the static either/or) +
`seq-stat-commutation` (the sequenced-statistical conservation arbiter). The corollary for design: resonant
recovery (Lx) belongs on **sinks** (the island Cx/Lx, validated S2), **not** on the rectifying pump transfers
(Ca/Cb). Authoritative record: `docs/efficiency-resolution.md`. The machine's operating η is **≈ 0.45–0.50**
(direct 0.386 + island sink), **not** 0.70.
