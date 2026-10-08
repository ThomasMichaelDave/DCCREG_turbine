# The locked hub, and the field at the AH null — findings

**Source:**
- the hub: `presets/hub-locked.json` (the designer's stack-up; every value carries its status and source);
- the field: `sim/hub_locked.py` → `sim/hub_locked_results.json`;
- the figure: `docs/figures/hub-locked.png` (`docs/make_hub_locked_figure.py`).

**Designer's lock-down (2026-10-08), inside out:**
1. **The vacuum vessel:** a sphere, 50 mm in diameter, borosilicate glass.
2. **The rings sit around it.**
3. **The AH cores with their coils** on its z axis, top and bottom.
4. **A retainer holds all of it**, and the shaft coupler encapsulates the retainer.
5. **The same shaft, top and bottom**, each half with its side's symmetric electrostatic and magnetic pump.

**Taken from the register** (`presets/electromagnets-RA.json`): the AH core is a MnZn 77 rod, Ø12.3 × 41.3 mm at
|z| 30.7–72, on a G-10 former. The coil is the 160-turn rewind in variant (a)'s window: r 8.25–11.45 mm, |z| 31.35–71.35.

**Placeholders [RH]:**
- the glass wall, 1.5 mm;
- the rings' form and angle (studied below);
- the retainer and coupler: ε 4.7, out to r 33 mm, |z| ≤ 72;
- the shaft flanges at |z| 72–80, moved out to clear the coil.

## 1. The field at the null, in this hub
"The rings" can mean two things here, so both are solved.

| electrodes | field at the null | pressure | in time | the pump |
|:--|--:|--:|:--|:--|
| **the Rogowski pair inside the vacuum** (DC, 20.6 kV across 3.14 mm) | **65.7 kV/cm** | **191 Pa** | steady | start z 1.184; 2.14 W |
| two rings outside the glass, DC as connected (8 mm bands at 50°) | 4.2 kV/cm | 0.79 Pa | drifts as the glass leaks | unchanged |
| the same rings, DC settled (the glass alone leaking) | 6.0 kV/cm | 1.6 Pa | after about 30 min | unchanged |
| the same rings, the 120 Hz swing (float wiring) | ±1.5 kV/cm | 0–0.1 Pa | AC | z 1.286; 2.05 W |

- **The pair inside gives 16× the rings' DC field**, and 10–11× their settled field.
- **It fits:** 20.4 mm across in the 47 mm vacuum, with 12 mm to the glass. Its surface peaks 1.6 % above the null's
  field, 0.13 % over the rule at 3.14 mm, so the gap would open by 0.004 mm.
- **But the axis is now the AH's,** so its stems must enter through the glass from the side and turn onto the axis
  behind each electrode. That is 3-D and not modelled. The field at the null does not depend on it.

## 2. The rings outside the glass
- **Where they work best:** around 50° from the axis.

| ring | DC field per kV across | at 20.6 kV | to the shaft side | ring to ring | the swing's peak | z with the swing |
|:--|--:|--:|--:|--:|--:|--:|
| wire Ø1.5 mm | 0.152 (kV/cm)/kV | 3.1 kV/cm | 4.8 pF | 1.0 pF | ±1.1 kV/cm | 1.291 |
| band 4 mm | 0.172 | 3.5 kV/cm | 5.1 pF | 1.2 pF | ±1.3 kV/cm | 1.289 |
| **band 8 mm** | **0.205** | **4.2 kV/cm** | **5.8 pF** | **1.6 pF** | **±1.5 kV/cm** | **1.286** |

- **The AH cores take 13 % of the rings' field.** They sit at the shaft's potential next to the poles.
  - Without them the 8 mm band would give 4.8 kV/cm.
  - They also raise its stray to the shaft side from 3.7 to 5.8 pF.
- **Toward the equator the rings couple to each other instead.** Ring-to-ring C rises from 1.6 pF at 50° to 17 pF at
  80°, and the field falls.
- **The swing keeps the pump near its bare gain** (z 1.29 at 50°, 1.25 at 80°, against 1.31), but at the pump's
  ±7.4 kV it is the weakest option.
- **DC through glass is not steady.** Borosilicate leaks: ρ ≈ 1e13 Ωm at 25 °C [IR], τ = ε/σ ≈ 7 min.
  - The glass beyond each ring drifts toward that ring's potential. That raises the field toward the hemispheres'
    limit of 6.6 kV/cm.
  - The settled line assumes the glass alone leaks. The retainer, the PEEK seats and charge collecting on the vacuum
    side of the wall all shift it, and the last can screen it.
  - Electrodes inside are held by the supply and absorb that charge.

## 3. What the lock-down changes
- **The vessel shrinks from the 90 mm placeholder to 50 mm.** The earlier rings study (`sim/core_rings.py`) used the
  placeholder.
- **The AH sits on the axis, not around the vessel.**
- **The hub gets longer.** The 160-turn coil in variant (a)'s window reaches |z| 71.35, but the tube layout's hub is
  120 mm long with its shaft flanges at |z| 60 (`sim/stack_sizing.py` hub_mm).
  - The spec moves the flanges to |z| 72–80, so the tube grows by about 24 mm.
  - The shorter windows of variants (b) / (c), which put the core 12 mm into the shaft's bore, would keep 120 mm.
- **BOM:** the vessel line is now the 50 mm borosilicate sphere, and the MnZn core quantity is 2, one per coil (it was 1).
- **Not yet updated:**
  - the tube's 3-D model (`sim/tube_geometry.py` still draws the 90 mm placeholder and the bicone);
  - the schematic's core block.

  Both wait on which electrodes, and on the hub's length.

## Caveats
- **[RH]:**
  - the glass wall;
  - the retainer's and coupler's permittivity and extent;
  - the flanges' place;
  - the AH as one REF envelope (core, former and coil);
  - the borosilicate resistivity (it falls steeply with temperature).
- **[OC]:**
  - the finite volumes: at half the cell, the 8 mm band's field moves 1.0 % and its strays 1–3 %;
  - the boundary elements: as `sim/core_null_field.py`.
- **Not modelled:**
  - the pair's side entry and feedthroughs;
  - the rings' leads;
  - the settled state with the retainer's leakage;
  - charge on the wall.

## Open questions for the designer
1. **Which electrodes make the field at the null?**
   - the two rings around the outside of the glass (4–6 kV/cm DC, ±1.5 kV/cm swinging);
   - or the two Rogowski electrodes inside the vacuum (65.7 kV/cm, two feedthroughs, side entry).
2. **The glass wall's thickness**, and whether the sphere has a neck or port. The pair inside needs two seals, and the
   vessel needs a pump-out.
3. **The hub's length:** move the shaft flanges out to clear the 160-turn coil (the tube grows about 24 mm), or wind the
   AH in a shorter window?
