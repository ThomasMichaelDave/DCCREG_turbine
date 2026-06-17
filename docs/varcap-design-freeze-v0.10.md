# Varcap-machine — design freeze v0.10 (temporary)

**Status:** temporary freeze for github. Geometry + cap set validated; C_R now pinned via the 12 mm disc.
Six spark gaps placed; **backstops (BS3/BS4) the only missing gap geometry**. Mainstream EE only — no
DCCREG theory in this project.

---

## 1. Design concept

A high-voltage **rotary electrostatic generator**: a symmetric **4-node Bennet voltage doubler** (solver
nodes 1–4 stator; nodes 5/6 the two **co-rotating** rotor halves) with **flying-bucket ("shuttle") charge
transfer** via floating island bars (nodes 7/8), and **rotary, alignment-gated self-break spark-gap
commutation** (no diodes, no triggers, no slip rings — direction comes from timing).

The doubler pumps the rotor toward ~20 kV. Per fire event an island bar dumps its charge through a **fire
gap** into a central **C_R ∥ L_R resonator tank** — C_R is the rotor-rotor capacitance across a garolite
septum; L_R is a **conical coil on the bicone hub surface** — which rings at **f₀ ≈ 637 kHz**. An **upstream
two-tier clamp** (soft glow governor + hard crowbar) holds the tank at the **15 kV** operating point.
12 sectors, 6 alternating active, **6 pump cycles per revolution**; spin-up by a switched-reluctance motor
(quadricone steel cores). Reach is **single-kick energy balance** (½·C_R·V²), Q-robust and f₀-independent.

## 2. Node map

| Node | Body |
|---|---|
| 1–4 | stator (C1, C2 stators; Ca, Cb, Cx pickup electrodes) |
| 5 / 6 | shaft A / shaft B rotor halves (co-rotating, locked through the central hub coupler) |
| 7 / 8 | island bar set on B / on A (floating, isolated from node 5) |

## 3. Capacitor set (everything that feeds the simulator)

| Cap | Electrodes (radii, mm) | Gap / dielectric | Sectors | Value | Tier |
|---|---|---|---|---|---|
| C1 | ND1 r387 ↔ ND5 rotor r387 | 7.0 mm air | 6 alt | 16–280 pF | [OC] |
| C2 | ND4 r387 ↔ ND6 rotor r387 | 7.0 mm air | 6 alt | 16–280 pF | [OC] |
| Ca | ND1 ↔ ND2 (r175) | 4.5 mm mica | — | 309 pF | [OC] |
| Cb | ND3 (r110–175) ↔ ND4 | 4.5 mm mica | — | 309 pF | [OC] |
| Cx3 | ND7 bars r75–350 ↔ ND3 pickup r58–350 | 3.0 mm air + 0.3 mm mica/face | 6 alt | 8–648 pF | [OC] |
| Cx4 | ND8 bars r75–350 ↔ ND2 pickup r58–350 | 3.0 mm air + 0.3 mm mica/face | 6 alt | 8–648 pF | [OC] |
| **C_R** | ND5 ↔ ND6 (electrode r387) | **12.0 mm garolite** | half-ann | **789 pF** | [OC] |
| L_R | 36-turn Cu 3/1 mm capillary, conical, bicone hub (coil r28→76, ~108 mm axial) | — | — | 79 µH | [OC] |

Resonator: **C_R = 789 pF, L_R = 79 µH → f₀ ≈ 637 kHz, Z₀ ≈ 316 Ω**, Q sweep 320/500/900.
*(C_R was pinned by choosing the disc thickness: 12 mm garolite at the r387 electrode → 789 pF. This is the
matched/comfortable point — see §4.)*

## 4. Pump / reach

- Pump per-cycle gain **z ≈ 1.307** (grown 648 pF island; **unchanged by C_R** — the pump shorts the 5–6
  rail, so C_R does not feed z). Galvanic ceiling 1.334, island ledger clean.
- Reach floor (½·C_R·V², 15 kV / 789 pF) = **89 mJ**.
- M2 island-dump transfer η = 4·Cx·C_R/(Cx+C_R)² = **99 %** (648/789 nearly matched).
- **Fire window:** single-kick reach requires island fire **≥ 16.6 kV** (delivers 89 mJ at η 99 %); the
  C1/C2 7 mm air gaps cap the island at **~21 kV**. Window **16.6–21 kV (4.4 kV margin)** — comfortable.
- **S2 should be re-confirmed at C_R = 789 pF** (favourable: lower floor, better match than the 960 pF run).

## 5. Spark-gap + clamp spec

Air-breakdown gradient: **3.0 kV/mm** sphere-gap (bench-calibrate vs IEC 60052). Each gap ×6 (every 60°).

| Gap | Path | Station | Radius | Spacing | Electrode | DXF |
|---|---|---|---|---|---|---|
| SG1 | node 2 → rail | 3.00° | C1/Ca disc | ~5–6 mm | 12 mm W-Cu sphere | **placed** |
| SG2 | node 3 → rail | 33.00° | C2/Cb disc | ~5–6 mm | 12 mm sphere | **placed** |
| SG3a | node 1 → bar | 7.20° | ~r340–350 | ~4.5–5 mm | 12 mm sphere | **placed** |
| SG3b | bar → node 3 (FIRE) | 16.05° | outer ~r340–350 | **adj.** ~5.3–6.4 mm* | 12 mm W-Cu sphere, wired + governed | **placed** |
| SG4a | node 4 → bar | 37.20° | ~r340–350 | ~4.5–5 mm | 12 mm sphere | **placed** |
| SG4b | bar → node 2 (FIRE) | 46.05° | outer ~r340–350 | **adj.** ~5.3–6.4 mm* | 12 mm W-Cu sphere, wired + governed | **placed** |
| BS3 | backstop (misfire) | **19.0°** | outer ~r350–380 | 0.6× strike | 20–30 mm smooth | **TODO** |
| BS4 | backstop (misfire) | **49.0°** | outer ~r350–380 | 0.6× strike | 20–30 mm smooth | **TODO** |
| Governor | clamp (upstream/island) | — | island side | — | smooth, 15 kV | [IR] |
| Crowbar | clamp (last resort) | — | 5–6 void | — | smooth hollow sphere, 16 kV | [IR] |

*Fire-gap spacing is **no longer a frozen number** — it is reclassified to an **adjustable, bench-tuned
`[IR]`** electrode (set vs IEC 60052, locked with a jam-nut, adjusted along the gap normal so spacing and
firing angle stay independent). S3 found the 5.5 mm draft clears 15 kV by only ~0.5 kV cold, right where the
linear 3 kV/mm strike model starts to roll off; the spacing must be tuned on the bench, not committed in the
DXF. Strike target ~16.6–20 kV island → ~5.3–6.4 mm. Load/return spacings still need the pump's absolute node
voltages. Radial bands governed by **quench** (push outboard), bounded by the island r350. Timing: 30°
SG3↔SG4 stator offset; 12-sector grid @30°; 6 bars/set.

**Fire-gap mount — adjustable + RPM-governed `[IR]`** (sub-assembly; see
`docs/design-note-SG3b-SG4b-firegap-mount.md`). The fire gap is the machine's voltage relief valve
(`V_strike` *is* the operating ceiling), and both electrodes sit on counter-rotating bodies — there is no
centrifugally-quiet side, so the design axis is **rigid vs compliant mount**, not rotor vs stator. The gap
gets two electrodes: an **outboard set-point** electrode (W-Cu sphere, wired to its node, on a **rigid**
garolite arm with a Macor/alumina arc collar — RPM-stable bench datum), and an **inboard governor** electrode
(W-Cu sphere on a **compliant flexure**) whose centrifugal deflection walks it radially *inward* so the gap
**closes** with overspeed → `V_strike` falls → pumping throttles. Force scales on **ground RPM = relative/2**
(`F_c ≈ 11–12 kgf` for a 12 mm W-Cu sphere at r≈350 mm, 1500 rpm ground — a 4× correction vs treating the
relative/commutation rate as ground speed); since `F_c ∝ Ω²` and power `∝ V_strike²·PRF`, the throttle is
strong above the knee — a passive protective limiter. Set the flexure knee **above** operating speed (idle in
normal running). Constraints `[IR]`: **fail-safe-wide** (a fatigued flexure must open the gap, never stick it
closed → no low-V runaway); **per-body flexure matching** (symmetric iris, CG centred — now a rotordynamic
spec on **two** contra-rotating bodies); flexure preferred over sliding spring (no stiction, fatigue-ratable);
Macor collar near the tip, garolite structural-run only; **tight, short fire loop** — loop inductance fights
the blow-out and the quench margin is only ~1.67× at the pessimistic recovery corner `[OC]`; label every
governor number **ground vs relative** RPM (a silent factor of 2); verify fire-recoil doesn't ring the ~1 kHz
flexure between shots (`[OC]`, measure). Quench is **preserved/improved** — motion-quench runs on the relative
sweep (2Ω·r), and contra-rotation doubles the separation speed vs a fixed stator `[OC]`.

## 6. Materials

Switching electrodes: tungsten / W-Cu spheres. Glow electrodes (backstops, governor): smooth large-radius.
Void-facing surfaces: Macor. C_R septum: **12 mm garolite** (15 kV/12 mm = 1.25 kV/mm holdoff). Ca/Cb/Cx
barriers: mica. Coil: copper 3/1 mm capillary. Quench: radial forced-air impeller with the disc's pumping.

## 7. Freeze status

- **Frozen / validated:** node map, cap geometry & values, **C_R = 789 pF pinned (12 mm disc)**, resonator
  C_R∥L_R, pump z, firing-station angles, 6 spark gaps placed, clamp architecture, materials. Reach (η,
  floor), pump z, the cap set, and the quench verdict are **unchanged** by the fire-gap mount note.
- **Reclassified (§5):** SG3b/SG4b **fire-gap spacing** is now an **adjustable, bench-tuned `[IR]`** electrode
  (set vs IEC 60052, locked), with an added **RPM-governed fire-gap mount** sub-assembly — rigid wired
  set-point (outboard) + centrifugal flexure governor (inboard); see
  `docs/design-note-SG3b-SG4b-firegap-mount.md`. Pending mechanical consolidation/feasibility by TMD.
- **Open before a *permanent* freeze:** (a) BS3/BS4 backstop markers + electrode geometry (§5); (b) one
  combined sim pass — re-confirm S2 reach at C_R = 789 pF (entry gate), then S3 spark tier at the real gaps
  (strike / quench / integrated reach).
- **Producer/consumer:** frozen solvers (`doubler_core`, `shuttle_core`) untouched; this freeze is
  documentation + DXF.

## 8. Artifacts

`varcap-nodeanalysis-template-r0_10_TMD_layout.dxf` · this document ·
`docs/design-note-SG3b-SG4b-firegap-mount.md` (fire-gap mount: adjustable + RPM-governed) · the S2 coupling
findings/code · the gap-hardware spec.
