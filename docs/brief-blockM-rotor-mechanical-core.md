# Brief — Block M: Rotor Mechanical Core (Quadricone + Shaft + Void + Disc)

**For:** Claude Code (implementation agent)
**Host:** `index.html` — Symmetric Bennet Doubler 4-node calculator (vanilla JS, self-contained). **Integrate as a parallel panel.**
**Status:** specified, not yet implemented. `[OC]` for the geometry/math; `[IR]` for device/assembly choices; `[RH]` for the operating-field reading.

> Discipline + symbol hygiene: see `CONVENTIONS.md`. The geometry below is mainstream solid mechanics; **no DCCREG theory is included or required** (README firewall).

---

## 0. Inheritance & relation to Block C-I

- **From C-I (`brief-blockC1-...`):** the rotor plate is a **sectored-disc + ring** capacitor electrode producing `Cmin/Cmax`. Block M supplies the *structural body* that electrode rides on. **Block M is a second, independent producer; it does NOT feed `solveDoubler4`.** **[OC — producer/consumer preserved]**
- **From the host:** match `FIELDS`/`state`/`$()`/`bindField`/`scheduleRecompute`/hash idiom; CSS-variable dark theme; on-load self-tests. **[match it]**

**The rotor (physical picture).** A central dielectric **disc** carries a sectored capacitor **electrode on each face** (C1 top, C2 bottom), mirrored across the disc mid-plane. Each electrode is a sectored annulus: inner edge at `hubDia` (the cone base), outer edge ≈ `plateDia ≈ discDia`. A **45° quadricone half** is bonded to each electrode across that annulus, base-to-electrode; the cone tapers outward to its apex, where a **stub shaft** (one per side — never a through-shaft) couples it to a bearing/drive. A **spherical void** sits at the assembly center; the disc fills its equatorial belt as a dielectric **septum** with a small central bore. Two sectored groups offset by one sector pitch realise the host's antiphase C1/C2. **[IR — assembly realisation]**

---

## 1. Symbols (additions to `CONVENTIONS.md` §2)

`d` remains **forbidden**. Two diameter families — outer (`discDia ≈ plateDia`) and inner (`hubDia = 2·coneR`); explicit `*Dia` names.

| Quantity | Symbol | Code | Notes |
|:--|:--|:--|:--|
| Cone base radius (= hub radius) | $R_c$ | `coneR` | 45° ⇒ cone height = `coneR` |
| Hub diameter (= electrode INNER annulus) | $\varnothing_h$ | `hubDia` | $=2R_c$; set by key sizing (small) |
| Disc diameter (structural, outer) | $\varnothing_D$ | `discDia` | large; carries the electrodes |
| Plate / electrode OUTER diameter | $\varnothing_p$ | `plateDia` | $\lesssim$ `discDia`; C-I owns it |
| Void radius / diameter | $r_v,\varnothing_v$ | `voidR`,`voidDia` | sphere; centred on the disc mid-plane |
| Disc thickness | $H_d$ | `discH` | separates C1/C2; **not** `h` bare |
| Disc central bore diameter | $\varnothing_{dv}$ | `discVoidDia` | dielectric-septum passage; ex. $\approx\varnothing_v/2$ |
| Wall fraction (void budget) | $f_w$ | `wallFrac` | $[0,1]$; **not** `t` (temperature) |
| Shaft diameter / radius | $\varnothing_s$ | `shaftDia`,`shaftR` | stub, one per cone apex |
| Key length / width | $L_k,w_k$ | `keyLen`,`keyW` | DIN 6885 |
| Hub keyway depth | $t_2$ | `keywayHubT` | collar reduction |
| Insertion depth (per stub) | $L_{ins}$ | `insertDepth` | apex → bore bottom |
| Collar (radial, at base) | — | `collar` | $=R_c-\text{shaftR}$ |
| Cone cap depth (void, per cone) | $c$ | `capDepth` | $=r_v-H_d/2$ |
| Electrode↔neutral clearance | — | `clearN` | $\approx r_v$ |

---

## 2. Quadricone geometry (port to vanilla JS)  **[OC]**

45° half-angle ⇒ for each cone, height = `coneR`; one cone solid $=\tfrac13\pi R_c^3$.

```
volQuadricone = (2/3)*PI*coneR^3            // both cones (no disc/void/shaft yet)
```

**Void (spherical) + wall guard.** Sphere radius `voidR`, centred at the disc mid-plane.
```
voidR <= (coneR/sqrt2) * (1 - wallFrac)     // inscribed-sphere wall budget
```

**Disc compensation — caps stay spherical, disc is the septum.** With the disc of thickness `discH`, each cone holds a **spherical cap** truncated at `±discH/2`; the disc carries the equatorial belt as **solid dielectric** with a central bore `discVoidDia` (NOT an open zone).
```
capDepth = voidR - discH/2                  // per cone; valid while discH < voidDia
```
The two cap cavities connect only through the disc bore. The electrode-facing cap surface is exactly spherical; the belt 12.5–25 mm (ex.) is dielectric. **[IR for the septum; OC for the cap]**

---

## 3. Shaft / key / hub sizing  **[OC math; IR for the 1.5·D rule]**

Two **stub** shafts, one per apex (a through-shaft would short C1↔C2). Apex sits at `coneR + discH/2` from centre; void pole at `voidR`, so the disc *adds* `discH/2` of insertion room per side:
```
insertMax = coneR + discH/2 - voidR         // bore must clear the void pole
keyedLen  = insertMax - shaftR              // collar exists only beyond shaftR depth
```
**Key auto-sizing (industry).** Equal-strength length ≈ **1.571·shaftDia**; practical rule **L ≤ ~1.5·shaftDia** for load distribution. Default `keyLen = 1.5*shaftDia`, round to a DIN 6885 standard length. **[OC]**

**Hub sizing (key binds at this scale):**
```
hubDia = voidDia + shaftDia + 2*keyLen - discH        // = 2(coneR)
```
**Guards (hard stop in red; warn in amber):**
```
collar:        shaftDia <= coneR                         // hub OD >= 2*bore  [hard]
void seat:     shaftDia <= 2*(coneR + discH/2 - voidR)   // clean stub seat   [hard]
wall:          voidR <= (coneR/sqrt2)*(1 - wallFrac)     // [hard]
key fit:       keyedLen >= keyLen                        // [hard]
keyway collar: coneR - shaftR - keywayHubT >= shaftR     // [warn]
```

---

## 4. Assembly stack-up & shared parameters (Block M ↔ C-I coupling)  **[IR]**

Two diameter families (outer electrical, inner mechanical) plus the void tie the models together. **Coupling is warn-only** (do NOT hard-link the panels):
```
// TWO diameter families — do NOT collapse them:
discDia  ≈ plateDia          // OUTER (electrical): set by capacitor area / C-I  (ex. 1000 ≈ 998)
hubDia   = 2*coneR           // INNER (mechanical): set by key sizing             (ex. 150)
electrodeInnerDia = hubDia   // sectored electrode = annulus [hubDia, plateDia]
hubDia >> voidDia > discVoidDia   // void + bore are small central features inside the hub
```
- **Warn** if the C-I plate's effective inner radius ≠ `hubR` (the electrode should ring the hub). **[warn]**
- **Warn** if `plateDia > discDia` (electrode overhangs the disc). **[warn]**
- The void/septum live inside `hubR`; the electrode lives outside it — they do not overlap. **[OC]**

**HV separation (geometry only — voltage/breakdown is the deferred HV block).** Void centre = electric neutral by mirror symmetry; each electrode is ≈ `voidR` from it.
```
clearN   = voidR                             // electrode -> central neutral (straight)
clearEE  = 2*voidR (= voidDia)               // electrode -> electrode (through void)
creepEE  = 2*(voidR - discVoidDia/2) + discH // surface path around the septum bore
```
The disc bore `discVoidDia` is the neutral passage; the solid belt is the creep barrier. Report distances; **do not** assert a safe voltage (deferred). **[OC geometry; RH for "field-mediated conduction at working energy"]**

---

## 5. Outputs (new local panel; nothing driven into the solver)

`.kv` readouts: `coneR`, `hubDia`, `capDepth`, `insertMax`, `keyLen` (+ DIN size), `keyedLen`, `collar`, `clearN`, `clearEE`, `creepEE`, void/cap/septum volumes, and a binding-guard line (which constraint set `hubDia`). Mass / inertia / balance are **deferred** (later block). **[OC]**

Plus the **live axial cross-section** (§5.1) — the primary visual feedback for this block.

---

### 5.1 Live axial cross-section (parametric, canvas)  **[OC geometry; IR rendering]**

A canvas slice through the **shaft axis** — the $(x,z)$ half-plane mirrored left/right (about the axis) and top/bottom (about the disc mid-plane) — redrawn live on every `recompute`. It frames the *current* geometry so proportions visibly morph as parameters change. This is the block's main visual readout.

**Projection.** `z` vertical (shaft axis), `x` = signed radius. **Isotropic** scale (equal px/mm both axes) so proportions are true:
```
totalH = discH + 2*(coneR + stubOut)
scale  = min( (W-2*m)/discDia, (H-2*m)/totalH )      // m = margin px
```
Re-fit each redraw (the "parametrically sized" behaviour). Because the disc is wide and flat (ex. 1000 mm) while the cones are small (ex. 150 mm), show a **mm scale bar** + `px/mm` so absolute size stays legible under auto-fit. A `fit | lock-scale` segmented toggle is desirable — **lock** makes changes read as real growth/shrink instead of re-framing. **[IR]**

**Elements (host CSS vars).** Dielectric disc (rect `x∈[±discR]`, `z∈[±discH/2]`, `--panel`/`--line`); sectored electrodes as bands on both faces over `x∈[±hubR,±plateR]` (`--acc`, hatched to denote "sectored"); the two 45° quadricone profiles (triangles, base `±coneR` at `±discH/2`, apex on axis), `--ink`/`--dim`; the spherical **void** caps (arcs radius `voidR`, drawn as cavity), the dielectric **septum belt** (`discVoidR→voidR`) and the central **bore** (`±discVoidR`); the two **shaft stubs** (rects `±shaftR`, bore depth `insertMax` inward, protruding outward) with a **keyway** notch; the central **neutral** marker at the origin; optional dashed **creepage** path and the `clearEE` span.

**Dimension annotations** (leader-lined, toggle-able): `discDia hubDia voidDia discVoidDia discH coneR insertMax`.

**Guard feedback.** Colour a feature `--bad` when its hard guard trips (cap vanishes at `discH ≥ voidDia`; shaft breaches collar; wall/key fail) and echo the binding-guard label. The cross-section thus doubles as the guard visualiser.

---

## 6. Implementation spec

**6.1 Markup.** One `<section class="panel">` titled *"Rotor mechanical core (quadricone + shaft + void + disc)"*, above or beside the C-I plate panel. Numeric `.row`s (range+number+unit) for `mvoid mdiscvoid mdisch mshaft mwall mdiscdia` reusing `bindField`; a `.kv` block for §5; cm/in unit toggle. **Prefix `m`** for mechanical ids (no clash with C-I `p*` or host `c*`).

**6.2 FIELDS + state.** Append `mvoid mdiscvoid mdisch mshaft mwall mdiscdia` with sane `def/min/max/step` (e.g. `mvoid` 5–200 mm; `mwall` 0–0.9 step 0.01; `mdisch` 0–`voidDia`; `mdiscdia` 50–2000 mm). `hubDia` is **derived** (key sizing), not an input. They hash-serialise for free.

**6.3 Functions** (plain JS, named consts with `// [OC] source`):
```
quadriconeCore(s) -> { coneR, hubDia, capDepth, insertMax, keyLen, keyedLen,
                       collar, clearN, clearEE, creepEE, vols, bind, warns }
keyLenFor(shaftDia) -> number        // 1.5*shaftDia, snapped to DIN 6885 ladder
```
`keyLen` auto from `mshaft` unless a manual override is set.

**6.4 No solver wiring.** Block M never writes `state.c1*/c2*` and never calls `solveDoubler4`. It only renders its own panel + warnings.

**6.5 Warnings** (dark-theme classes): the §3 hard guards (red, block the readout); the §4 coupling checks vs the C-I plate (amber); `discH >= voidDia` (caps vanish → sphere fully in disc); `capDepth <= 0`.

**6.6 Self-tests.** Extend `runSelfTest()`: (a) `voidDia=50, shaftDia=35, discH=0, keyLen=56 → hubDia ≈ 197 mm`; (b) void-partition identity: cap×2 + septum-zone = full sphere when the disc bore = 0 (degenerate check); (c) `keyLenFor(35) ≈ 52.5 → DIN 56`. Surface in the existing self-test table.

**6.7 Presets.** Add `rotor-core` to `PRESETS` setting the `m*` ids (the worked 15 cm-class example), leaving `psrc`/electrical fields untouched.

**6.8 Discipline.** `CONVENTIONS.md` names verbatim; `"use strict"`; URL-hash state (no `localStorage`); tag choices `[OC]/[IR]/[RH]`.

---

**6.10 Cross-section.** Add `<canvas id="mxsec" width="600" height="220">` to the Block-M panel. Implement `drawCrossSection(s)` in the host canvas idiom (`clearCanvas`, 2D ctx, no libs); call it from `recompute()` (or extend `drawCharts()`). Pure function of `state` + the derived `quadriconeCore(s)`; isotropic auto-fit per §5.1; scale bar + `px/mm` readout; `fit|lock` segmented toggle (host style); guard-coloured features. No solver interaction. **[OC/IR]**

## 7. Open forks
1. **Plate/electrode inner radius ↔ `voidR`** — warn-only now; promote to a shared field later? **[IR]**
2. **Creepage path definition** (§4) — confirm the surface route vs straight clearance; the "2×voidR" figure is the clearance reading. **[task]**
3. **Mass / rotational inertia / static balance** — the flywheel block. **[OC, deferred]**
4. **HV / dielectric-strength → safe voltage** across `creepEE`/`clearEE` (couples to the C-I dielectric). **[OC, deferred — the genuine next block, shared with C-I §7]**
5. **Stub-shaft bearing/seat detail** beyond the keyed bore. **[deferred]**
6. **Cross-section scale mode** (§5.1): `fit` vs `lock-scale`; later an optional isometric/3D or θ-sweep view — the 2D axial slice is the load-bearing one. **[IR/deferred]**

---

## Appendix — equation summary
```
volQuadricone = (2/3)·π·coneR³,           cone height = coneR (45°)
capDepth      = voidR − discH/2,          valid discH < voidDia = 2·voidR
insertMax     = coneR + discH/2 − voidR,  keyedLen = insertMax − shaftR
keyLen        ≈ 1.571·shaftDia  (use 1.5·shaftDia, snap to DIN 6885)
hubDia        = voidDia + shaftDia + 2·keyLen − discH = 2·coneR
guards: shaftDia≤coneR · shaftDia≤2(coneR+discH/2−voidR) · voidR≤(coneR/√2)(1−wallFrac) · keyedLen≥keyLen
clearEE = 2·voidR,  creepEE = 2(voidR − discVoidDia/2) + discH,  neutral at centre
hierarchy: discDia ≈ plateDia  >>  hubDia = 2·coneR  >  voidDia  >  discVoidDia
electrode = sectored annulus [hubDia → plateDia];  hubDia from key sizing, plateDia from C-I area
```
