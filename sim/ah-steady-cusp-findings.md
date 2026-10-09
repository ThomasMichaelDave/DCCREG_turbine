# A steady cusp from the magnetic pump — findings

**Source:** `sim/ah_steady_cusp.py` → `sim/ah_steady_cusp_results.json`.

**Designer's input.** The AH pair should hold a steady cusp.

**Status:** the bypass is PROPOSED; the designer has not accepted it (2026-10-09).

**Naming:** "top" and "bottom" below are the deck's AHt / AHb, named when side A was on top. In the record side A
is below, so AHt is side A's coil (below) and AHb side B's (above); each branch carries its own side's coil.

**The problem.** Each AH coil sits in series with its utron group, so it carries that branch's current.
- **At the pick** (g 0.5 / 6 bridges / 1200 rpm relative) that is 139–449 ampere-turns, 107 % peak to peak, at 120 Hz.
- **Top and bottom peak in turn.** They differ by up to 184 A-turns, so the cusp's null moves along the axis every cycle.

**The fix.** Put a bypass capacitor across each AH coil.
- **It carries the ripple:** the branch's 120 Hz ripple goes through the capacitor, and the coil keeps the branch's DC.
- **It matches the pair:** the A and B branches carry the same DC by symmetry, so the two coils match.
- **The run:** the pick, exactly as `sim/rotor_parts_duty.py` runs it, with C + ESR (10 mΩ [RH]) across AHt and AHb.

| bypass per coil | LC resonance | AH top: min–max (mean) | ripple, p-p | top − bottom, max | z_early | belt |
|:--|--:|--:|--:|--:|--:|--:|
| none (today) | | 139–449 (290) A-t | 107 % | 184 A-t | 1.139 | 17.6 W |
| 2.2 mF | 107 Hz | 77–487 (299) A-t | 137 % | 409 A-t | 1.144 | 18.5 W |
| 4.7 mF | 73 Hz | 240–351 (300) A-t | 37 % | 110 A-t | 1.145 | 18.3 W |
| 10 mF | 50 Hz | 277–319 (300) A-t | 14 % | 41 A-t | 1.146 | 18.2 W |
| **22 mF** | **34 Hz** | **290–308 (300) A-t** | **5.9 %** | **17 A-t** | **1.147** | **18.1 W** |
| 47 mF | 23 Hz | 295–303 (300) A-t | 2.8 % | 8 A-t | 1.148 | 18.1 W |

- **With the 3-D utrons** (2026-10-09, `sim/utron-3d-findings.md` §4) the 22 mF row reads 214–251 A-turns (221–245
  mean, by how each group's coils are connected), z_early 1.072–1.091 and 10.2–12.3 W: the bypass still holds the coil
  within ±3 %.
- **Size it well below resonance.** The AH coil's 1.0 mH and the capacitor resonate at 1/(2π√(LC)).
  - At 2.2 mF that is 107 Hz, close to the 120 Hz pump frequency, and the ripple gets worse.
  - From 10 mF (50 Hz) the pair filters. 22 mF (34 Hz) holds the coil within ±3 %.
- **The capacitor's duty at 22 mF:** 0.65 A rms ripple, about 0.5 V across it, 8 mW of ESR loss for the pair.
  - A low-voltage electrolytic does it, e.g. one 22 mF / 6.3 V part per coil, on the rotor beside the AH.
  - Polarised parts need the start kick's polarity fixed (§ the winding sense). Otherwise use bipolar
    (non-polarised) electrolytics.
- **The pump doesn't mind:** z_early (the loaded run's) goes 1.139 → 1.147 and the belt 17.6 → 18.1 W. The utron
  copper rises 12.9 → 13.5 W.
- **The cost: the steady field is the mean.** That is 300 A-turns per coil, against the 449 A-turn peak the AH was
  sized to.
  - A steady 450 needs more AH turns (240 instead of 160, with R and L × 2.25) or a larger pump. That is not re-sized
    here.
  - The rod limit (≈ 600 A-turns; 743 for the AH alone, `sim/ah-null-findings.md` §4) now meets a steady field instead
    of peaks.

## The winding sense, and the bypass's polarity (2026-10-09)
**Source:** `sim/ah_winding.py` → `sim/ah_winding_results.json` (the pick, as above, without and with 22 mF).

- **The coils' currents** [OC]: each is unipolar and of the same sign in its element's orientation, in both branches
  (the dual's twin branches):
  - coil A (AHt, x1 → d): −0.87 to −2.81 A without the bypass, −1.81 to −1.93 A with it;
  - coil B (AHb, x2 → b): the same.
  - So the current flows from the diode side into each coil: d → x1, and b → x2.
- **How to wind and connect them** [OC]:
  - Wind two identical coils: the same hand, the start lead at the same end.
  - Connect each coil's start to its group's utrons (x1 / x2) and its finish to the diode side (d / b).
  - Mount them as rotated copies, each with its start lead toward the vessel. A coil turned end over end circulates
    the other way about +z for the same terminal current, so the two fields oppose: anti-Helmholtz.
- **The wrong way:** a translated copy (both start leads upward), with the same connections, circulates the same way.
  That makes a Helmholtz pair, with the field of both coils added at the null.
- **The check at the bench:** energise the pair from a DC supply through the same terminals. B at the centre must read
  zero within noise, with opposite signs 10 mm above and below.
- **The bypass's polarity:** each coil carries about 0.5 V DC, with d (and b) positive, and a ripple of tens of mV. So
  polarised parts go + to d (b).
  - **Corrected 2026-10-09** (`sim/parts-first-cut-findings.md` §3, §5): this said the kick must seed this sign and
    that a seed of the other sign runs the pump mirrored, reverse-biasing the parts. It does not. Seeds of the other
    sign (20, 25 and 30 % of Ψs) start the pump in the deck's own sign, with and without the bypass, and the bypass
    never sees more than 1.3 mV the wrong way. The diodes set the sign [OC, from the deck]; the kick is wired + to
    node a all the same.

## Caveats
- **[RH]:** the 10 mΩ ESR. Electrolytics also age and run warm.
- **Not studied:** the start-up transient with the capacitors fitted (the kick charges them through the coil).
- **Not modelled:** the AH–bicone mutual coupling.
- **Operating point:** the mean A-turns depend on it. This is the pick only.
