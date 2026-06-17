# Findings — battery energy capacity (rev 2): the real flashover ceiling

**Branch** `battery-capacity` (off `series-resonator` `b62e642`). **Verdict:**
`BINDING-ELEMENT = central HV void / creepage cluster` (clearN 20 mm air → 20 kV, creepage 30 mm → 30 kV) ·
`BATTERY-CEILING = 20–30 kV / 158–355 mJ` · `GAROLITE-NOT-LIMIT` (actually **mica**, 400 kV, 13–20× over) ·
`RAISE-LEVER = guard ring (2×) / widen void / creepage ribs — not the dielectric`.

**The headline: the dielectric is the strong part; the limit is air.** Surveying every voltage-holding
element from the *actual* `index.html` geometry, the battery ceiling is set by the **central HV insulation
(void air gap + edge creepage), ~20–30 kV**, not by the C_R dielectric volume (>100 kV). At the 15 kV
operating point the machine has a **1.33× voltage / 1.78× energy margin** to the binding void.

**Two corrections to the brief (rev 2's own demand: compute from geometry, don't assume).** The brief's
*suspected* dimensions are not in `index.html`:
1. **There is no "7 mm C1/C2 air gap."** The varicap gap is `pgap = 0.5 mm` (index.html:206; R1 preset:1865)
   → 1.5 kV — and it is a *pump-side* element behind the open fire gap, so it never holds V_CR at all.
2. **C_R is not "12 mm garolite."** It is a **10 mm mica disc** (`mdisch = 10`, ε_r 5.4; index.html:322,
   1448, 1495) — an even *stronger* dielectric (400 kV bulk vs 180 kV for 12 mm G-10).

So the survey names the real binding element rather than inheriting either rev's assumed number.

**Scope:** small. Inherits the series accumulation model + the 88.8 mJ-at-15 kV anchor (`series_resonator.csv`
@ `b62e642`), C_R = 789 pF, and the machine geometry from `index.html` (surveyed, authoritative). The new
piece is the per-element breakdown computation + V_CR-stress mapping + binding minimisation. Frozen modules
byte-identical (0 producer edits, asserted). No DCCREG. HV refs: Kuffel/Zaengl; IEC 60052 (sphere gaps);
IEC 60112 (creepage).

---

## 1. The insulation-coordination survey (actual geometry)

| element | dim | material | gradient | V_breakdown | holds V_CR? | source |
|---|---|---|---|---|---|---|
| C1/C2 varicap gap | 0.5 mm | air | 3 kV/mm | **1.5 kV** | no (pump-side) | index.html:206 `pgap` |
| Ca/Cb transfer film | 1.0 mm | Mylar | 40 kV/mm | 40 kV | no (transfer) | index.html:666 `tcMylarThkMm` |
| **C_R mica bulk** | 10 mm | mica | 40 kV/mm | **400 kV** | yes | index.html:322 `mdisch` |
| **C_R edge creepage** | 30 mm | air-surface | 1 kV/mm | **30 kV** | yes | index.html:1351 `edgeEE` |
| **HV void clearN (e→n)** | 20 mm | air | 1 kV/mm | **20 kV** | yes | index.html:1349 `voidR` |
| HV void clearEE (e→e) | 40 mm | air | 1 kV/mm | 40 kV | yes | index.html:1350 `2·voidR` |
| fire gap SG3b/SG4b | ~6 mm | air (W-Cu sphere) | — | ~20 kV (V_bd) | **designed — excluded** | inherited fire breakdown |
| commutator kbargap | 2 mm | air | 3 kV/mm | 6 kV | no (display-only) | index.html:406 `kbargap` |

**Gradients (cited).** Uniform-field air 3 kV/mm (≈ 30 kV/cm at STP, Kuffel/Zaengl); `index.html`'s own
design deratings 1 kV/mm sharp-tip (no guard, :2663-2666) and 2 kV/mm with a guard ring (:2834); mica
40 kV/mm working (intrinsic ~118, derated); surface creepage 1 kV/mm dirty / 2.5 kV/mm clean (IEC 60112);
G-10 bulk 15 kV/mm (reference). Sphere-gap uniformity rolls off for s/D ≳ 0.5 (IEC 60052) — the central
electrodes are cone apexes (sharp), so the 1 kV/mm sharp-tip derate is the right floor.

## 2. The binding element + ceiling

Only the **central HV elements hold the full V_CR** (the void air, the edge creepage, the mica bulk); the
pump-side gaps (C1/C2, kbargap) see topological fractions far below V_CR, and the fire gap is a *designed*
breakdown (excluded). Among the V_CR-holders the smallest breakdown binds:

**`BINDING-ELEMENT` = the central HV void / creepage cluster, ~20–30 kV.** At `index.html`'s conservative
1 kV/mm sharp-tip derating the **void air gap clearN (20 mm) → 20 kV** is the floor, with the **edge creepage
(30 mm) → 30 kV** just above and clearEE (40 mm) → 40 kV next. *Robustness note:* whether `clearN` holds the
full V_CR or V_CR/2 depends on the rotor↔rotor electrode-potential split (one side grounded vs symmetric
about a grounded neutral); in the symmetric case the creepage (30 kV) binds instead. **Either way the ceiling
sits in the 20–30 kV central-HV band** — the conclusion is insensitive to that detail.

**`BATTERY-CEILING` = 20–30 kV → E_max = ½·C_R·V² = 158–355 mJ** (789 pF). At the intrinsic 3 kV/mm air the
void would hold 60 kV, but honouring `index.html`'s own 1 kV/mm sharp-tip design value gives the conservative
20 kV floor. **Operating point: 15 kV / 88.8 mJ → 1.33× voltage, 1.78× energy margin** to the binding void.

**The "21 kV" coincidence, explained.** Rev 1's 21 kV was mis-attributed to the garolite, then to a 7 mm
C1/C2 gap. The real number is the **central HV void**: `index.html` sizes the void at 20 mm = 20 kV ÷
1 kV/mm, i.e. the void air gap is coordinated to *equal the design HV*. So the ceiling genuinely is ~20 kV —
but it is the central standoff at the sharp-tip derating, not the dielectric and not C1/C2.

## 3. `GAROLITE-NOT-LIMIT` — confirmed, and stronger than thought

The C_R dielectric **bulk = 400 kV** (10 mm mica) — **20× over the 20 kV ceiling**. The rev-1 garolite
reference (12 mm G-10 → 180 kV) is also far above. The dielectric *volume* is the strong part of the
structure, exactly as rev 2 asserted; the weak path is the air/surface around it. Thickening the dielectric
buys nothing.

## 4. `RAISE-LEVER` — lift the ceiling by geometry, not dielectric

| lever | mechanism | gain |
|---|---|---|
| **Guard ring** on the central electrode | round the cone apex: 1 → 2 kV/mm | ceiling **20 → 40 kV (2×)** — biggest single lever |
| **Widen the void** clearN | +1 mm buys +1 kV at 1 kV/mm | 20 → 30 mm → **30 kV** |
| **Creepage ribs / skirts** | 2–3× the surface path in the same axial space | 30 → 75 mm → **75 kV** (de-binds creepage) |
| ~~thicken the mica~~ | already 20× over | **wasted** |

*Interpretation (brief §note, validated):* the ceiling moves with the **binding gap geometry, decoupled from
C_R entirely**. "How much can the battery hold" is really "how much standoff does the weakest central gap
give" — capacity (½C_R·V²) and standoff (the binding air gap) are **separate knobs**, tunable by gap width
and creepage ribs rather than by the dielectric. The guard ring is the highest-leverage move: it doubles the
ceiling to 40 kV (→ 631 mJ) for the cost of rounding one electrode.

## 5. Self-tests (all PASS)

(a) actual C1/C2 = 0.5 mm air → 1.5 kV (correcting the suspected 7 mm/21 kV); (b) C_R mica 10 mm bulk →
400 kV > 100 kV (the headroom — a model returning ~20 kV would be wrong); (c) air+mica series division — the
low-ε air holds 98 % of the share (sets that element's limit, were such a stack present); (d) creepage uses
the 30 mm edge path, not the 10 mm thickness; (e) hand-calc cross-check — void clearN 20 mm × 1 kV/mm =
20 kV; (f) dielectric bulk margin (mica 400 kV, garolite 180 kV) ≫ any ~20–30 kV ceiling.

## 6. Deliverables

`sim/battery_capacity.py` (insulation survey + V_CR mapping + 6 self-tests) · `battery-capacity-findings.md`
(this) · `battery_capacity.csv` · `battery_breakdown_survey.png` (per-element breakdown vs operating stress,
binding highlighted, dielectric off-scale-high) · `battery_capacity_ceiling.png` (capacity vs the
binding-element ceiling, 15 kV operating point + margin marked). Frozen modules byte-identical; **not merged**.
