# A steady cusp from the magnetic pump — findings

**Source:** `sim/ah_steady_cusp.py` → `sim/ah_steady_cusp_results.json`.

**Designer's input.** The AH pair should hold a steady cusp.

**The problem.** Each AH coil sits in series with its utron group, so it carries that branch's current.
- **At the pick** (g 0.5 / 6 bridges / 1200 rpm relative) that is 139–449 ampere-turns, 107 % peak to peak, at 120 Hz.
- **Top and bottom peak in turn.** They differ by up to 184 A-turns, so the cusp's null moves along the axis every cycle.

**The fix.** Put a bypass capacitor across each AH coil.
- **It carries the ripple:** the branch's 120 Hz ripple goes through the capacitor, and the coil keeps the branch's DC.
- **It matches the pair:** the A and B branches carry the same DC by symmetry, so the two coils match.
- **The run:** the pick, exactly as `sim/rotor_parts_duty.py` runs it, with C + ESR (10 mΩ [RH]) across AHt and AHb.

| bypass per coil | LC resonance | AH top: min–max (mean) | ripple, p-p | top − bottom, max | z | belt |
|:--|--:|--:|--:|--:|--:|--:|
| none (today) | | 139–449 (290) A-t | 107 % | 184 A-t | 1.139 | 17.6 W |
| 2.2 mF | 107 Hz | 77–487 (299) A-t | 137 % | 409 A-t | 1.144 | 18.5 W |
| 4.7 mF | 73 Hz | 240–351 (300) A-t | 37 % | 110 A-t | 1.145 | 18.3 W |
| 10 mF | 50 Hz | 277–319 (300) A-t | 14 % | 41 A-t | 1.146 | 18.2 W |
| **22 mF** | **34 Hz** | **290–308 (300) A-t** | **5.9 %** | **17 A-t** | **1.147** | **18.1 W** |
| 47 mF | 23 Hz | 295–303 (300) A-t | 2.8 % | 8 A-t | 1.148 | 18.1 W |

- **Size it well below resonance.** The AH coil's 1.0 mH and the capacitor resonate at 1/(2π√(LC)).
  - At 2.2 mF that is 107 Hz, close to the 120 Hz pump frequency, and the ripple gets worse.
  - From 10 mF (50 Hz) the pair filters. 22 mF (34 Hz) holds the coil within ±3 %.
- **The capacitor's duty at 22 mF:** 0.65 A rms ripple, about 0.5 V across it, 8 mW of ESR loss for the pair.
  - A low-voltage electrolytic bank does it, e.g. 2 × 10 mF at 6.3 V per coil, on the rotor beside the AH.
  - Polarised parts need the start kick's polarity fixed. Otherwise use bipolar (non-polarised) electrolytics.
- **The pump doesn't mind:** z goes 1.139 → 1.147 and the belt 17.6 → 18.1 W. The utron copper rises 12.9 → 13.5 W.
- **The cost: the steady field is the mean.** That is 300 A-turns per coil, against the 449 A-turn peak the AH was
  sized to.
  - A steady 450 needs more AH turns (240 instead of 160, with R and L × 2.25) or a larger pump. That is not re-sized
    here.
  - The rod limit (≈ 600 A-turns) now meets a steady field instead of peaks.

## Caveats
- **[RH]:** the 10 mΩ ESR. Electrolytics also age and run warm.
- **Not studied:** the start-up transient with the capacitors fitted (the kick charges them through the coil).
- **Not modelled:** the AH–bicone mutual coupling.
- **Operating point:** the mean A-turns depend on it. This is the pick only.
