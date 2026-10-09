# The bench test of the rings

**What it is for:** the rings' design rests on four things no model settles:
1. **the hold-off ratings:** the interface along the glass between the rings (1 kV/mm), and the silicone gel at the
   copper beads (5 kV/mm). Both are [RH], and between them they set the number of multiplier stages;
2. **each ring's leakage** (100 GΩ estimate), which sets the multiplier's sag;
3. **the conductivities of the glass, gel, retainer and coupler**, which make the DC field at the null drift after
   switch-on;
4. **the field with the pump's own supply:** its start-up and its 120 Hz ripple.

The test measures them in that order. The ratings come first because they decide the build.

**Sources of the predictions:**
- `sim/hub_drift.py` → `sim/hub_drift_results.json` (the drift, the swing, the start-up);
- `sim/hub_rings_build.py` → `sim/hub_rings_build_results.json` (the record and the alternatives);
- the figures: `docs/figures/hub-bench-predictions.png` and the record's field, `docs/figures/hub-rings-field.png`;
- the design and the drawing: `docs/rings-design.md`, `docs/drawings/DCCREG-HUB-201`;
- the findings: `sim/hub-rings-build-findings.md`.

**The record under test** (`presets/hub-locked.json` rings):
- **the bands:** 0.1 mm copper foil on the glass, 26.25–55.71° from the axis, 29.9 mm apart along the glass;
- **the beads:** Ø3 mm at the polar edges, Ø2 mm at the equatorial edges;
- **the retainer:** unfilled PEEK with a 0.5 mm gel-filled pocket, and the G10 coupler outside;
- **the supply, symmetric:** ring A at −15.0 kV on its own two-stage Cockcroft-Walton chain from the shaft on node
  1, ring B at +15.0 kV on the mirror chain on node 4; 29.9 kV across, the null at the shaft's potential;
- **at the null:** 7.62 kV/cm and 2.57 Pa as connected, DC from B to A, with the beads in their grooves as drawn (the
  bands alone 7.10); settling to 8.20 kV/cm as the insulators leak (`sim/hub-beads-settled-findings.md`).

## 1. The test hub
- **The vessel:**
  - as built: a 50 mm borosilicate sphere with a 1.5 mm wall;
  - plus a pumping tube (borosilicate, Ø8 mm) at one pole, on a turbo pump to 1e-3 Pa or better.
  - The vacuum must be real. Air inside would carry its own ions (its relaxation time ε0/σ is about 7 min) and screen
    the DC in minutes.
- **The rings:** as built:
  - the foil cut as gores and soldered;
  - the beads soldered copper wire rings;
  - the pocket vacuum-cast with degassed gel;
  - the PEEK retainer and the G10 coupler.
  - The leads leave through the coupler as PTFE-insulated HV wire, potted where they exit.
- **The AH:** a dummy at REF at each pole, an aluminium cylinder on the AH's envelope (Ø22.9 mm from |z| 30.7 mm
  out to the flange).
  - The pumping side's dummy is bored for the pumping tube and the probe's fibre.
  - The other pole may carry the real core and coil, unpowered and tied to REF, until phase 4b.
- **The flanges and shaft stubs:** aluminium, at REF. REF goes to ground through the electrometer (phase 2) or
  directly.

## 2. The instruments
- **Two DC supplies:**
  - −30 kV and +30 kV, current-limited to 50 µA or less, ripple 0.1 % or less;
  - each output through a 100 MΩ series resistor, which limits a flashover's energy and costs 0.1 % against 100 GΩ.
- **Electrometers** (pA to µA): one in REF's return to ground, one in the other ring's (phase 2).
- **The field probe at the null:**
  - **the sensor:** an electro-optic (Pockels) BGO (Bi₄Ge₃O₁₂) crystal, longitudinal (light and field both along z),
    about 3 × 3 × 10 mm, on a fibre through the pumping tube along the axis;
  - **why the axis:** a thin dielectric along the field barely disturbs the axial field it measures;
  - **why BGO:** it is all-dielectric (no metal near the null), not pyroelectric, and resistive enough to hold a DC
    reading for hours [IR]. Its bandwidth is far above 120 Hz.
  - **Calibrate it** before and after in a parallel-plate cell, with DC steps of 1–10 kV/cm and a 6 h hold. The hold
    measures the crystal's own drift, which must stay well under the 9 % that phase 3 looks for.
- **Non-contact electrostatic voltmeters** facing a test patch on each lead (phase 4). A resistive divider would load
  the multiplier: 1 GΩ against the rings' 100 GΩ.
- **A DC partial-discharge detector** (coupling capacitor and PD instrument, 10 pC threshold), for phase 1.
- **Temperature:** thermocouples on the glass at the equator and on the retainer; an enclosure held at 25 °C and
  40 °C.

## 3. The phases
### Phase 1: the hold-off (it sets the stages)
- **(a) Interface coupons:**
  - **the coupon:** a 1.5 mm borosilicate plate (curved to R 25 if available, flat otherwise) with two foil electrodes
    beaded as built (Ø2 mm), 10 mm apart, under 0.5 mm of gel and a PEEK cover, cast like the hub. Each electrode is
    two gores lapped as built, the lap running into the bead, and each bead carries a closing joint
    (`sim/hub-joints-findings.md` §5);
  - **the test:** ten coupons, the DC ramped at 0.5 kV/s to flashover; record the voltage and the track;
  - **the interface rating:** half the lowest flashover's average field, provided 1.5× that holds for 1 h without
    partial discharge [RH].
- **(b) Bead coupons:**
  - **the coupon:** a Ø2 or Ø3 mm copper bead in gel, facing a REF plate across 5 mm of gel and PEEK. That is the polar
    bead facing the AH coil's end, the record's tightest spot. Make the beads as the rings will be: the Ø3 mm seamless,
    the Ø2 mm with its dressed joint facing the plate.
  - **the test:** ramp to breakdown;
  - **the gel's rating at a bead:** half the lowest [RH].
- **(c) The sphere:**
  - Hold the record's DC (−15.0 / +15.0 kV) for 1 h, then 1.25× it (−18.7 / +18.7 kV) for 1 h.
  - A vane flashover at node 4 lifts ring B to 19.0 kV, 2 % past 1.25× (`sim/parts-first-cut-findings.md` §2.7).
    Whether to qualify to ±20 kV (1.33×) instead is the designer's (OPEN).
  - Partial discharge must stay below the 10 pC threshold through both holds: the DC settles 90 % of the way in 39 min
    (phase 3), and a void at an equatorial bead's contact discharges only once it has (`sim/hub-joints-findings.md`
    §4). Keep the detector on through phase 3 as well.
  - On a sacrificial build, optionally ramp to flashover.
- **What it decides** (`sim/hub_rings_build_results.json` best_by_family; the symmetric supply, the designer's
  family, with the asymmetric family's best for comparison):

| ratings qualified (interface / gel at a bead) | stages a side | across the rings | bands | beads (polar / eq.) | at the null (the bands alone) | asymmetric best |
|:--|:--|--:|:--|:--|--:|--:|
| **1 / 5 kV/mm (the record)** | **2 + 2** | **29.9 kV** | **26.25–55.7°** | **Ø3 / Ø2 mm** | **7.10 kV/cm (7.62 with the beads)** | 6.93 |
| 1 / 8 | 3 + 3 | 44.3 kV | 24.0–39.2° | Ø3 / Ø2 mm | 7.80 kV/cm | 7.97 |
| 2 / 5 | 2 + 2 | 29.9 kV | 25.5–72.9° | Ø3 / Ø4 mm | 8.35 kV/cm | 7.91 |
| 2 / 8 | 4 + 4 | 57.9 kV | 30.75–56.8° | Ø3 / Ø3 mm | 13.38 kV/cm | 13.25 |

- **Then:** set the measured ratings in `presets/hub-locked.json` (ratings) and re-run `sim/hub_rings_build.py`. The
  table above is that run at the four pairs.

### Phase 2: the leakage (it sets the multiplier's sag)
- **The rings:** each ring alone at its record potential from its lab supply. The other ring and REF go to ground
  through the electrometers.
  - Read the current into REF and into the other ring after 1 h. Record the whole decay first: the absorption current
    of the PEEK, gel and glass is a second check of phase 3's time constants.
- **The multiplier's parts** at their stage voltage, 7.5 kV: each HV diode in reverse, each 100 pF capacitor's
  insulation, and the potted assembly's surface.
- **Expect** (the ledger, `sim/hub_rings_build.py` LEAKAGE):
  - **the rings' own insulation:** about 200 TΩ, under 0.1 nA at 15 kV;
  - **the parts:** about 3e11 Ω per stage in the diodes and 5e11 Ω in the capacitors;
  - **in all:** 158 GΩ per ring, and at least the 100 GΩ estimate.
- **If less:** the chains sag. At 10 GΩ two stages give about ±14.2 kV instead of ±15.0 (ring B's chain), and more
  stages stop helping above four.
  - Set the measured value in `presets/hub-locked.json` (rings_leakage) and re-run.

### Phase 3: the DC drift on lab supplies
- **The run:**
  - switch both rings on together (within a second) to −15.0 / +15.0 kV;
  - record the field at the null for 6 h at 25 °C;
  - ground both rings and record the return;
  - repeat at 40 °C.
- **Expect** (sim/hub_drift.py; PEEK retainer, gel, 25 °C):
  - **the rise:** 7.62 kV/cm at switch-on, 7.95 at 10 min, 8.18 at 1 h, 8.20 at 6 h (+7.6 %);
  - **the times:** half-way at 7.6 min and 90 % at 39 min; two exponentials fit it, τ ≈ 6 and 24 min;
  - **the return:** grounding the settled rings leaves the field at the null at +0.58 kV/cm (the settled minus the
    connected field), decaying with the same times. This checks that the drift is linear charging of the insulators.
  - **At 40 °C** (the glass five times as conductive): 8.27 kV/cm, half-way at 2.8 min.
  - **The ratio of the glass's conductivity to the gel's,** which E∞ / E(0) and the τᵢ measure, decides the equatorial
    beads once settled: their gel holds 5 kV/mm while the glass conducts at most about 4 times the gel
    (`sim/hub-beads-settled-findings.md` §7). In service the hub runs at about 2.4 (`sim/hub-thermal-findings.md`).
    Measure it at 25 °C and at 40 °C, and the gel's own conductivity on a coupon at both.
- **The other cases bracket the materials:**

| case | switch-on | 10 min | 1 h | 6 h | half-way |
|:--|--:|--:|--:|--:|--:|
| **PEEK retainer, gel, 25 °C (the design)** | **7.62** | **7.95** | **8.18** | **8.20 kV/cm** | **7.6 min** |
| PEI retainer, gel, 25 °C | 7.62 | 7.98 | 8.33 | 8.42 | 12 min |
| G10 retainer, gel, 25 °C | 7.62 | 7.74 | 7.77 | 7.77 | 4.5 min |
| PEEK retainer, gel, 40 °C glass | 7.62 | 8.18 | 8.27 | 8.27 | 2.8 min |
| PEEK retainer, no gel (air in the pocket and the grooves), 25 °C | 7.35 | 7.68 | 7.97 | 8.00 | 9.8 min |

- **Analysis:** fit E(t) = E∞ − Σ aᵢ exp(−t/τᵢ) with one or two terms, then compare:
  - **E(0)** checks the electrostatics (k = 0.2546 (kV/cm)/kV with the beads; 0.2373 for the bands alone) and the
    probe's calibration;
  - **E∞ / E(0)** checks the ratios of the conductivities;
  - **the τᵢ** check the conductivities themselves.
  - Then set the measured conductivities in `sim/hub_drift.py` SIG.
- **G10 barely drifts, and why:** its σ/ε matches the glass's and the gel's, so no charge collects at their
  interfaces. PEEK leaks ten times less, so its interfaces charge and the field at the null rises.

### Phase 4: with the pump's supply
- **(a) The rings on the rotor's own supply:** ring A on its two-stage chain at node 1, ring B on the mirror chain at
  node 4, the pump at 1200 rpm relative (120 Hz). Expect:
  - **the start-up from the seed:** 50 % at 0.12 s, 95 % at 0.24 s (29 cycles), 99 % at 0.33 s;
  - **the 120 Hz ripple on the field at the null:** 0.014 kV/cm p-p on 7.62 (0.19 %). The field stays DC from B to A;
    it does not swing from A to B. The probe needs a resolution of about 5e-4.
  - **the rings' ripple** (non-contact voltmeters): about 29 V p-p on ring B and 34 V on ring A. Ring A tops up as
    node 1 bottoms, 1.03 ms before ring B tops up as node 4 peaks, so the ripples mostly add across the gap (57 V
    p-p);
  - **then the drift of phase 3 again.** The multiplier's sag adds nothing at 100 GΩ.
- **(b) The AH powered:** its ampere-turns ripple 5.9 % p-p with 22 mF across each coil
  (`sim/ah-steady-cusp-findings.md`).
  - First run the AH with the rings grounded. The fibre passes through the AH's bore, where its field can rotate the
    light (the Faraday effect), so measure that offset before reading the rings' field.

## 4. Safety
- **High voltage:** up to ±19 kV on the sphere in phase 1(c), and to flashover on the coupons (40 kV class supplies).
  - Use an interlocked, grounded enclosure and ground sticks; each supply's output goes through its 100 MΩ.
- **Stored energy:** a 100 pF capacitor holds 2.8 mJ at a stage's 7.5 kV, and Co1 holds 8.7 mJ at its 13.2 kV. That
  makes about 27 mJ in the record's eight capacitors. Ground them through 10 MΩ before touching.
- **The vacuum sphere:** small, but borosilicate under vacuum can implode. Keep a polycarbonate shield around it.
- **The spinning pump (phase 4):** its own guards.
- **X-rays:** none are expected, since the electrodes are outside the vacuum and below 30 kV. Check with a survey meter
  at the first full voltage.

## 5. What the results change
- **The ratings** → presets ratings → `sim/hub_rings_build.py` → the stage count and the bands.
- **The leakage** → presets rings_leakage → the multiplier's sag and the stage count.
- **The drift** → the field to expect in operation (connected → settled) and the conductivities (`sim/hub_drift.py`).
