# Findings — battery energy capacity (rev 3): re-run from the DXF + freeze doc

**Branch** `battery-capacity-dxf` (off `series-resonator` `b62e642`). **Verdict:**
`BINDING-ELEMENT = C1/C2 7 mm air, 21 kV` · `BATTERY-CEILING = 21 kV / 174 mJ` · `DIELECTRIC-NOT-LIMIT`
(garolite 180 kV, 8.6×) · `RAISE-LEVER = widen C1/C2 / creepage ribs / guard-ring the plate edges` ·
**`FLAG`: C_R edge creepage undimensioned in the available DXF — load-bearing, needs r0_10**.

**The source correction is the whole point of this rev.** Rev 2 pulled geometry from `index.html` and called
it authoritative — that was **wrong**: `index.html` is **stale**. Re-deriving from the authoritative
geometry (the DXF + the consolidated freeze doc) **reverses rev 2's two "corrections"** and puts the C1/C2
gap back as the binding element, exactly as the brief anticipated.

> **STANDING CORRECTION (all future work):** the geometric reference is the **DXF + `docs/varcap-design-freeze-v0.10.md`**. `index.html` is a stale calculator and must **not** be used for dimensions (only as a flagged `[STALE]` cross-reference).

**Scope:** small — the insulation-coordination survey, re-sourced. Inherits the series accumulation model +
the 88.8 mJ-at-15 kV anchor (`series_resonator` `b62e642`), C_R = 789 pF. Frozen modules
(`shuttle_core.py`, `reference/doubler_core.py`, `index.html`) **byte-identical** (0 producer edits,
asserted). No DCCREG. HV refs: Kuffel/Zaengl; IEC 60052 (sphere gaps); IEC 60112 (creepage).

---

## 0. Provenance — what is actually in the repo (flagged to TMD)

The brief names "**DXF v0.11**". **There is no v0.11 in the repo.** What exists:
- `docs/varcap-nodeanalysis-template-r0_6_TMD_layout.dxf` — an **r0_6** layout, and a **2-D radial template**:
  it carries the **reference radii** (R387 electrode band, R491 rotor outer, R95/R75/R25 rings, R500 plate
  edge — all confirmed by ezdxf) and the **layer/node structure** (every cap and gap is a named layer:
  `CAP-C1-OVERLAP`, `MECH-DIELECTRIC`, `SG3b-FIRE-GAP`, …), but **not the axial gap spacings** (7 mm air,
  12 mm garolite, 3 mm Cx are axial — absent from a face-on radial view). Its own text even labels the radii
  "R1-baseline (**calculator-derived**)".
- `docs/varcap-design-freeze-v0.10.md` — the **consolidated freeze doc (v0.10)**, whose §3 cap table is the
  dimensional authority for the axial gaps. (Its §8 references a **not-yet-drafted r0_10 DXF**.)

**Method:** radii + element existence read from the DXF (ezdxf); axial gap dimensions from the freeze-doc §3;
the two **cross-checked on r387** (DXF `R387 active band OUTER` ↔ doc `C_R/C1/C2 at r387 electrode` ✓). The
**v0.11 → r0_6+v0.10** version gap and the **missing r0_10 DXF** are flagged as provenance items for TMD;
the substance (the 7 mm / 12 mm-garolite cap set the brief expects) is present and consistent.

## 1. What rev 2 got wrong (reversed by the authoritative source)

| quantity | rev 2 (stale `index.html`) | **rev 3 (DXF + doc v0.10)** |
|---|---|---|
| C1/C2 gap | 0.5 mm air → 1.5 kV, "pump-side, dismissed" | **7.0 mm air → 21 kV** (doc §3; §4: caps the island at ~21 kV) |
| C_R dielectric | 10 mm **mica** → 400 kV | **12 mm garolite** → 180 kV (doc §3/§6: 1.25 kV/mm @ 15 kV) |
| central HV standoff | "void clearN 20 mm / creepage 30 mm" | **no central void** — C_R is **annular at r387**; the standoff is the garolite septum + its edge creepage |

## 2. The survey (axial dims from freeze-doc §3, radii cross-checked vs the DXF)

| element | dim | material | gradient | V_breakdown | holds V_CR? | DXF layer |
|---|---|---|---|---|---|---|
| **C1/C2 varicap gap** | 7.0 mm | air (sphere) | 3 kV/mm | **21 kV** | yes (stator↔rotor, full HV) | CAP-C1-OVERLAP |
| Ca/Cb mica barrier | 4.5 mm | mica | 40 kV/mm | 180 kV | no (internal) | CAP-Ca-GAP |
| Cx3/Cx4 air sub-gap | 3.0 mm | air | 3 kV/mm | 9 kV | no (pickup) | CAP-Cx3-GAP |
| Cx3/Cx4 mica face | 0.3 mm | mica | 40 kV/mm | 12 kV | no (pickup) | CAP-Cx3-GAP |
| **C_R garolite bulk** | 12.0 mm | garolite | 15 kV/mm | **180 kV** | yes | MECH-DIELECTRIC |
| **C_R edge creepage** | **undimensioned** | air-surface | 1–2.5 kV/mm | **12–30 kV (est.)** | yes | MECH-DIELECTRIC |
| fire gap SG3b/SG4b | ~5.5 mm | air (W-Cu sphere) | 3 kV/mm | 16.5 kV | **designed — excluded** | SG3b-FIRE-GAP |

Gradients cited: uniform/sphere-gap air 3 kV/mm (≈30 kV/cm, Kuffel/Zaengl; the doc §5 sphere-gap value);
G-10 bulk 15 kV/mm; mica 40 kV/mm working; surface creepage 1 kV/mm dirty / 2.5 kV/mm clean (IEC 60112). The
sharp-apex derate is applied **only where the geometry is actually sharp** (per the brief) — the C1/C2 gaps
use 12 mm W-Cu **spheres** (doc §5), so the uniform 3 kV/mm holds, not a sharp-tip derate.

## 3. Verdicts

**`BINDING-ELEMENT` = C1/C2 7 mm air gap, V_breakdown = 21 kV** (7 mm × 3 kV/mm). This is the **documented
system ceiling**: freeze-doc §4 states the C1/C2 7 mm gaps *cap the island at ~21 kV*, setting the fire
window **16.6–21 kV (4.4 kV margin)**. rev 2 dismissed this gap on the stale 0.5 mm value; the DXF/doc
restore it as the binding element. Among the *dimensioned* full-V_CR holders it is the minimum (vs garolite
bulk 180 kV).

**`BATTERY-CEILING` = 21 kV → E_max = ½·C_R·V² = 174 mJ** (789 pF). Operating point 15 kV / 88.8 mJ →
**1.40× voltage, 1.96× energy margin** — matching the doc's "comfortable" 16.6–21 kV window.

**`DIELECTRIC-NOT-LIMIT` — confirmed, robust to the source error.** The C_R **garolite** bulk = 180 kV (12 mm
× 15 kV/mm) ≫ the 21 kV ceiling (**8.6×**). The headline survives the index.html→DXF correction exactly as
the brief predicted: it held for the stale 10 mm mica (400 kV) and holds for the real 12 mm garolite
(180 kV). The dielectric *volume* is the strong part; the weak path is air (C1/C2) or surface (creepage).

**⚠ `FLAG` (load-bearing, to TMD): the C_R edge creepage is *undimensioned* in the available r0_6 DXF.** It
is a 2-D radial template; the edge-path length around the garolite septum is an axial/edge geometry that
only the (not-yet-drafted) **r0_10 DXF** would carry. A *bare-edge* estimate (path ≈ the 12 mm septum
thickness) gives **12 kV dirty – 30 kV clean** — **at or below the 15 kV operating point**. A validated
design must have creepage > 15 kV, so the real septum almost certainly has **radial overhang / ribs** that
the radial template doesn't show. **This is the binding unknown** — it is *excluded* from the ceiling here
(rather than letting a guess override the documented 21 kV) but flagged as the load-bearing dimension to
confirm against r0_10. (rev 2's "30 mm" was itself a stale index.html number, not a measurement.)

**`RAISE-LEVER` (geometry, not the dielectric):**
1. **Widen the C1/C2 air gap** — +1 mm buys +3 kV (7 → 9 mm → 27 kV). The doc's 4.4 kV fire-window margin
   already rides on this gap; widening it lifts both the window and the ceiling.
2. **C_R creepage ribs / radial overhang** — the highest-leverage *unknown*: a ribbed edge 2–3× the surface
   path de-binds creepage well above 21 kV. Resolve with the r0_10 DXF first.
3. **Guard-ring / sphere the C1/C2 plate edges** — keep the field uniform (3 kV/mm) rather than incurring a
   sharp-edge derate at the plate rim.
   *Not* thicken the garolite — already 8.6× over, wasted.

## 4. Self-tests (all PASS)

(a) C1/C2 7 mm air = 21 kV (correcting the stale 0.5 mm / 1.5 kV); (b) C_R 12 mm garolite = 180 kV
(correcting the stale 10 mm mica / 400 kV); (c) DXF↔doc cross-check — R387 electrode band present and
labelled in the DXF, agreeing with the doc; (d) Cx air+mica series division — the low-ε air holds 98 % of
the share; (e) the DXF carries the insulation layers (CAP-C1-OVERLAP, MECH-DIELECTRIC, SG3b-FIRE-GAP);
(f) fire gap 5.5 mm × 3 = 16.5 kV, inside the designed 16.6–20 kV window.

## 5. Deliverables

`sim/battery_capacity.py` (DXF-sourced survey via ezdxf + freeze-doc dims + 6 self-tests) ·
`battery-capacity-findings.md` (this) · `battery_capacity.csv` · `battery_breakdown_survey.png` (per-element
breakdown, binding=C1/C2 highlighted, creepage flagged amber, garolite off-scale) ·
`battery_capacity_ceiling.png` (capacity vs the 21 kV ceiling, 15 kV operating point + the flagged creepage
band). Frozen modules byte-identical; **not merged**.
