# Retainer Specification

**Date:** 2026-10-14
**Baseline evidence:** design state `09243c7` (locked 2026-10-09), branch `claude/new-session-0az7f9`
**Synthesis branch:** `claude/synthesis-phase1`
**Agent:** retainer-spec

**Status legend.** Status is the designer's, as the ledger records it (`docs/ledger/DCCREG-design-ledger.md` §5). This
spec recommends only as **PROPOSED (synthesis)**; it decides nothing. "Derived" = arithmetic done here on committed
numbers; **no study was re-run** (no Python in this session). The drawing PDFs were not opened; sheet numbers come from
`docs/drawings/set-index.json` and the findings.

**Inputs applied.** Tube envelope, masses, shaft interface: `synthesis/tube-spec.md` C.1, C.3 (gated). Designer's
decisions of 2026-10-14 (`synthesis/core-engine-spec.md` Rec. 2, 4, 5): sixth Ca gap (+9 mm a side, not laid out: tube
≈ 1032 mm, frame bearings ≈ 1078 mm apart, rotor ≈ +1.0 kg); no HV seed part; paired ideal/real records. From
`synthesis/electrical-integrity-audit.md`: room 15–29 °C at ≤ 600 m, rotor air ≤ room + 5 K, hub glass ≤ 37.3 °C binds;
decks ≥ 12 mm from the counter-rotor cage (32 mm drawn); the A.3a charge-injection / grounding port is an operating
feature; **ventilation openings must not reduce those clearances.**

**Corrections to the brief, from the record (director to note).**
1. **"Cage" has two meanings.** The record's "cage" is the counter-rotor's rotating G10 tube r 182–186 (CGE-901), a
   tube part. The stationary enclosure specified here is called the **guard** (the "safety cage" of the brief).
2. **"123 µm at d 25"** is the six-bearing layout's gap change (`sim/tube-shaft-findings.md` §0). With the bridge-ring
   bearings placed it is **+1.1 / +1.6 µm** (`sim/bridge-ring-bearings-findings.md` §3).
3. **"3600 RPM"** is no operating speed: shaft and bodies 600 rpm each way, 1200 rpm relative at the inner bearings,
   750 rpm each way at the 1.25 × overspeed (`sim/rotor-mechanics-findings.md`).
4. **Ledger §3.6 is the rings**; the drive and bearings are §3.1, §3.9.
5. **Not used:** `sim/hub-drive-findings.md` (the pivot's first point: 300 rpm each way, 144 W, 2.3 N·m),
   `sim/spinup-findings.md` (20 kV tube v4), `sim/torque-sim-findings.md` (disc machine, z 1.334) and
   `sim/hub-joints-findings.md` (the rings' gores) carry nothing for the retainer. Drive sizing is
   `docs/drive-gear-belt.md`.
6. The drive study's frame (45 × 45 Al columns, "outside the cage's Ø332") predates the cage Ø372 and was never
   dynamically checked (§5).

## Purpose

The retainer is everything outside the tube that holds, spins and encloses it: the two frame bearings, the bevel
reverser and its case, the belt and motor, the base frame, the guard, the ventilation, and the bench-side interfaces
(REF-to-earth bond, K4 magnet station, injection port). It excludes the tube (`synthesis/tube-spec.md`), including the
Ca|reluctance and bridge-ring bearings, their G10 spiders and cartridges (counter-rotor parts), and the hub and rings
(interface only). It needs from the tube: envelope, masses, shaft interface, loads, heat. It gives the tube: the frame
bearings' stiffness and preload, the drive torque path, the thermal boundary, the guard's clearances and strays.

## Governing constraints

1. **Equalization-is-the-pump.** Nothing in the retainer recovers energy from the pump transfers; the belt's power ends
   as heat (`CONVENTIONS.md`; tube-spec Governing 1). `[OC]`
2. **Gap budget.** The 0.5 mm utron gap rules the bearings: all-in runout per inner bearing and the belt's overhung pull
   (`sim/rotor-mechanics-findings.md` §5). `[OC]` statics, `[IR]` budget
3. **Counter-rotor floats on the shaft**; only the two frame bearings face the frame (`sim/tube-shaft-findings.md` §0).
   `[OC]`
4. **Non-magnetic near the AH null.** Shaft and gears austenitic (`sim/ah-null-findings.md` §5, via ledger §3.1); the
   null is moved 0.35–0.5 mm by the earth's field (ledger §3.3), ≈ 0.11 T/m gradient. The guard and the frame within
   ±0.5 m of the hub are aluminium or austenitic. `[IR]`
5. **HV is inside.** ±14.77 kV rings in the grounded can; decks to 14.9 kV; the guard is earthed metal at ≥ 32 mm from
   them, and openings never reduce the deck-to-cage clearances of the electrical-integrity audit. `[IR]`
6. **Site envelope** from the audit: ≤ 600 m, room 15–29 °C, rotor air ≤ room + 5 K. `[IR]`; `[RH]` the +5 K
7. **Frozen files and the designer's items** untouched; every status below is PROPOSED unless the ledger says DECIDED.

## Specification

### 1  Shaft bearings

| Parameter | Value | Source / basis | Tag | Status |
|:----------|:------|:---------------|:----|:-------|
| Part, every seat | **SKF 6205-2Z** (25 / 52 / 15; C 14.8 kN, C0 7.8 kN; shields, CN clearance; P5 Explorer); alternates FAG 6205-C-2Z, NSK 6205ZZ | `sim/bridge-ring-bearings-findings.md` §1; P-001 | `[IR]` catalogue via web search | PROPOSED |
| Retainer's seats (2) | **Bottom, locating:** in the gear-case floor, z −63.5 … −48.5, takes both bodies' weight, the belt pull. **Top, floating:** housing in the top plate, z ≈ 1004 (≈ 1022 with the sixth gap), wave-spring preloaded. Frame bearings 1060 mm apart (≈ 1078) | `sim/rotor-parts-drive-findings.md` Headline; tube-spec C.1 | `[IR]` | PROPOSED |
| Not retainer | Ca\|reluctance (2) and bridge-ring (2) bearings: tube / counter-rotor, on G10 spiders in stainless cartridges (BRG-8xx). Interface: bottom bridge-ring bearing A is the gear-end bearing (counter-rotor's side gear bolts under its cartridge); it locates the counter-rotor (357 N derived from 36.4 kg; 331 N in the study, L10 217 000 h) | `sim/bridge-ring-bearings-findings.md` §2, §4; `docs/drive-gear-belt.md` §5 | `[IR]` | PROPOSED |
| Axial arrangement | Bottom frame bearing locates the whole assembly; every other bearing floats on its spring. Shaft growth (≈ 0.37 mm per 20 K on 1.06 m, derived from 17 ppm/K) goes to the top bearing, away from the mesh | `docs/drive-gear-belt.md` §7 | `[OC]` | PROPOSED |
| Locating bearing load | axial **814 N** (parts sum 45.6 + 1.0 + 36.4 kg) to **872 N** (two-body reading 50.4 + 1.0 + 37.54 kg), derived; radial 96 N (belt 90 + unbalance 5), 160 N at the driver's limit. The drive study's 689 N is stale (70 kg) | tube-spec C.1; `docs/drive-gear-belt.md` §7 | `[OC]` weights | PROPOSED |
| Locating bearing life | P ≈ 1.35 kN (ISO 281 form: X 0.56, Y ≈ 1.5) → **≈ 39 000 h** at 872 N (scaled from the study's 65 000 h at 689 N). Shortest-lived bearing; inspect at 10 000 h | derived from `docs/drive-gear-belt.md` §7 | `[IR]` | PROPOSED |
| Floating bearings | top frame: radial = its share of unbalance (≈ 5 N); life > 10⁶ h on the spring | `sim/bridge-ring-bearings-findings.md` §4 | `[IR]` | PROPOSED |
| Class | frame bearings: P0 acceptable (they place the assembly; influence on the gap 0.00); inner bearings P5 at Ca\|reluctance, P6 acceptable at the bridge-ring pair. The 6205-2Z Explorer is P5 at no extra cost, so order P5 throughout | `sim/rotor-mechanics-findings.md` §5.1, §5.4 | `[IR]` | PROPOSED |
| **Preload** | record 100 N; SKF's small-motor rule F = k·d, k 0.005–0.01 kN/mm → 125–250 N at d 25. **Recommend 150 N** on every floating bearing (4 inner + top frame) | `sim/bridge-ring-bearings-findings.md` §4 | `[IR]` | **PROPOSED (synthesis); OPEN (designer)** |
| Preload arrangement | springs in opposed pairs (top bearings load down, lower floating bearings load up) so the net on the locating bearing is ≤ one preload; wave-spring rate ≤ 60 N/mm so ±0.5 mm of thermal travel moves the load ≤ ±20 % | derived | `[IR]` | PROPOSED |
| Runout budget | all-in TIR per inner bearing **≤ 0.027 mm** (P5 + preload; journals ≤ 5 µm, housings ≤ 10 µm TIR to the grind datums). The record allows 0.05 mm with the eighth pair (P6 + preload = 36 µm), which this layout has; but the influence coefficients are not re-run for the placed pair, so hold 0.027 | `sim/rotor-mechanics-findings.md` §5.4; `sim/bridge-ring-bearings-findings.md` Caveats | `[OC]` statics; `[IR]` | PROPOSED |
| Seat material | stainless liner in the Al case floor and top housing: Al (23 ppm/K) opens a 52 mm seat by ≈ 24 µm per 20 K against 12 µm for the bearing steel; a 17 ppm/K liner opens ≈ 5 µm net | derived | `[OC]` | PROPOSED |
| Seat stiffness | 0.86e8 N/m (preloaded 6205 in a G10 spider) to 2e8 N/m (stiff). Frame seats: aim ≥ 1.2e8 (bearing Hertz at 100 N), the housing adding in series | `sim/rotor-mechanics-findings.md` §4 | `[RH]` | OPEN (tap test) |
| Speed | inner 1200 rpm relative (1500 at 750): 8.6 % (10.7 %) of the 2Z's 14 000 rpm limit; frame 600 (750) rpm; pinion 6000-2Z 900 rpm. Even 3600 rpm would be 26 % of limit | `sim/bridge-ring-bearings-findings.md` §4 | `[OC]` | PROPOSED |
| Lubrication | shielded (2Z), never contact seals (+ as much drag again). Grease for life, **low-viscosity (≈ 18–30 mm²/s base oil, PAO/ester, NLGI 2, −30…+110 °C)**; the standard fill is probably ≈ 70 mm²/s (3.2 W against 1.3 W for bridge-ring A). Verify the datasheet. Replace at every tube rebuild, else at 20 000 h; health check = coast-down (≈ 3 rpm/s at 600 rpm, loss = (I_r + I_c) ω \|dω/dt\|) | `sim/rotor-mechanics-findings.md` §6; `sim/bridge-ring-bearings-findings.md` §4 | `[IR]`; `[RH]` interval | PROPOSED |
| Reference link | a lubricated rolling contact is not a defined conductor at 0.02 µA. tube-spec A.0 lets the counter-rotor float (z 1.0142 on 100 pF); do not rely on a bearing as the link. If kept, a wire or brush. Bearings must not be the arc return in any no-clamp test (38 A, 2.1 mC a strike) | tube-spec A.0; audit; ledger §3.1 | `[IR]` | PROPOSED |

**Preload: the issue.** At 100 N the record sits under SKF's rule. Below it a vertical, lightly loaded 6205 is exposed
to (a) free play (radial clearance 5–20 µm; the record removes it by the axial spring, `sim/rotor-mechanics-findings.md`
§5.2), (b) ball skidding on cold, stiff grease (SKF minimum radial load 40 N at 30 mm²/s, 71 N at 70 mm²/s, against an
unbalance of ≈ 5 N), (c) varying-compliance (ball-pass) vibration, (d) shorter life from smearing. Derived here:
at 100 N and α ≈ 10° each of 9 balls carries ≈ 40–65 N, above the ≈ 35 N a ball sees at the minimum radial load, so
skidding is **not** predicted at 100 N by SKF's own formula; the rule's 125–250 N is a rule of thumb for noise and
stiffness `[RH]`. At 150 N: stiffness +14 %, friction +0.07 W a bearing (`sim/bridge-ring-bearings-findings.md` §4),
L10 of the floating bearings stays > 10⁶ h. At 250 N stiffness ≈ +36 % `[OC]` Hertz (F^1/3). **Recommend 150 N**, the
bench sweeps 100 / 150 / 250 N by coast-down loss and by noise. Preload does **not** cure f2 (§7).

**Ball-pass frequencies** (derived, `[OC]` kinematics; 9 balls of 7.94 mm, pitch 38.5 mm, α 10°, from
`sim/rotor-mechanics-findings.md` §4). Inner bearings at 20 Hz relative: cage 8.0, **outer-race pass 71.7**,
**ball spin 46.5**, **inner-race pass 108.3 Hz**; 2 × outer 143 Hz. Frame bearings at 10 Hz: outer 35.8, inner 54.2,
**2 × inner 108.3 Hz**. The inner-race pass and the frame bearings' second harmonic sit **inside f2 (107.9–116.8 Hz)**;
the outer-race pass is 11–14 % under f1 (79–84 Hz). They excite only through waviness or a defect, so P5, the preload and a
bench waterfall matter; not in the record.

### 2  Motor mount

| Parameter | Value | Source / basis | Tag | Status |
|:----------|:------|:---------------|:----|:-------|
| Motor | BLDC 200 W, 48 V, 3000 rpm, 0.64 N·m rated, 60 mm flange, 110 mm; candidate Nanotec / SMD APBA60M048030-E with speed-loop driver (ramp, 1.5 × current limit); flange PCD Ø70, spigot Ø50, shaft Ø14 × 30 to confirm | `docs/drive-gear-belt.md` §6; `sim/unmodelled-parts-findings.md` §4 | `[IR]` catalogue class | PROPOSED |
| Load | 61 W at its shaft, 76 W electrical, 38 % of rated at 2400 rpm; run-up 32 s; peak 0.64 N·m (161 W); at limit 0.96 N·m | `docs/drive-gear-belt.md` §4.3, §6 | `[IR]` | PROPOSED |
| Overspeed | 750 rpm each way needs 3000 rpm: the motor's rated speed; windage ×1.9 there, belt ≈ 85–100 W. Spin-seat (rotor-mechanics §8) at the top of the motor's range, 400 W family above 100 W | `sim/rotor-mechanics-findings.md` §6; drive §4.1 | `[IR]` | OPEN (designer) |
| Position | **beside the tube** at +x, 245 mm out, motor axis vertical and parallel to the shaft, belt plane below the case (pulley centre ≈ 27 mm below the locating bearing's midplane). Drive compartment under the tube guard | `docs/drive-gear-belt.md` §6, §8; `sim/rotor-parts-drive-findings.md` §4 | `[IR]` | PROPOSED |
| Mount | Al motor plate, ≥ 15 mm, **slotted along the centre line** with a jacking screw (DRV motor plate "tensioning slots"), dowelled to a reference edge on the base plate; bolted to the base plate, not to the bell | `sim/unmodelled-parts-findings.md` §1; drawing set | `[IR]` | PROPOSED |
| Alignment | shafts parallel ≤ 0.25° (≈ 1 mm over 245 mm); pulley faces coplanar ≤ 0.5 mm, checked with a straight edge across the flanged 20T and the 80T; shims under the plate | belt-maker practice | `[RH]` | PROPOSED |
| Isolation | **rigid, no soft mount.** A synchronous belt needs a fixed centre distance, and a soft mount lowers the motor-on-belt mode (309 Hz) toward the 240 Hz pulsation and 300 Hz mesh. The pulsation never reaches the frame (0.12 N·m p-p) | `docs/drive-gear-belt.md` §4.2 | `[IR]` | PROPOSED |
| Motor rotation orders | 40 Hz (1 ×), 80 Hz (2 ×) against f1 79–84 Hz: balance the rotor of the motor and pulley to G2.5 or better; check on the bench waterfall | derived | `[OC]` | PROPOSED |
| Driver and supply | 48 V 300 W supply and driver **outside** the guard's air path; **dynamic-brake chopper and resistor rated ≥ 2.5 kJ a stop** (stored energy 2.2 kJ derived: J_r ≈ 0.37, J_c ≈ 0.75 kg·m² at 600 rpm; braking at limit 19 s) | `docs/drive-gear-belt.md` §4.3; derived | `[RH]` inertias | PROPOSED |
| Heat | motor + driver loss ≈ 15 W (76 − 61): outside the tube compartment (§6) | derived | `[IR]` | PROPOSED |

### 3  Belt drive and rotation changer

| Parameter | Value | Source / basis | Tag | Status |
|:----------|:------|:---------------|:----|:-------|
| Belt | Gates HTD 5M, 15 mm, 750 mm (150 teeth), centres 245.35 mm, 4.0 m/s, wrap 158° on the 20T, 8 teeth in mesh | `docs/drive-gear-belt.md` §6; `sim/unmodelled-parts-findings.md` §1 | `[IR]` | PROPOSED |
| Pulleys, ratio | 20T (Ø31.8, **flanged** P20-5M-15F) on the motor, 80T (Ø127.3, TL80-5M-15, taper bush 1610, **no flanges**) on the shaft: **4 : 1; motor 2400 rpm gives 600 rpm** shaft, rotor +600, counter-rotor −600 | the same; drawing set P-014 | `[IR]` | PROPOSED |
| Width check | 6.1 mm needed steady (15 N), 15.1 mm at the limit (60 N): 15 mm | drive §6 | `[IR]` 0.5 N/mm/tooth | PROPOSED |
| Tension | **46 N static per strand**; tight side ≤ 76 N against 375 N allowable; slack side stays tight at the limit. Set by span pluck: first transverse mode **61 Hz** at 46 N (240 mm span); re-check after 24 h run-in | drive §6 | `[IR]` | PROPOSED |
| Tensioner | none: slotted motor plate and jacking screw (§2), fixed centres thereafter | drawing set | `[IR]` | PROPOSED |
| Bearing load from tension | hub load 90 N static (2T sin 79°), 153 N at the limit, at the pulley, **into the locating bearing** 27 mm above it; journal bending 1.6 MPa (2.6). The gap cost of an overhung 100 N pull is 2.0 µm with the eighth pair (21.6 µm without) | drive §7; `sim/rotor-mechanics-findings.md` §5.2 | `[OC]`; `[RH]` 100 N | PROPOSED |
| Rotation changer | **bevel reverser with a held carrier** (a differential with the carrier fixed): two stainless 1.4305 side gears z 30, m 2, 12 mm face; three POM-C pinions z 20 at 120°, each on a Ø10 stub shaft in two 6000-2Z; the gear case (Al 6082) is the carrier and the frame bottom-bearing housing. Chosen over a star gear, crossed belts, two phase-locked motors, spur layshaft, friction bevel | `docs/drive-gear-belt.md` §2, §5 | `[OC]` kinematics; `[IR]` choice | PROPOSED |
| Torques | gear puts 0.48 (counter-rotor) / 0.52 N·m (rotor) on the bodies, **1.00 N·m into the frame**; belt 0.94 N·m, 59 W; pulsation at the gear 0.061 N·m p-p (gear-path mode 20 Hz, mesh 300 Hz); run-up peak 1.63 N·m, limit 2.52 / 2.78 braking | drive §4 | `[OC]`; `[IR]` | PROPOSED |
| Backlash | j_n 0.10–0.15 mm by shims and a spacer; POM growth eats ≈ 0.05 mm per 30 K | drive §5 | `[IR]` | PROPOSED |
| Run-up | crosses the 20 Hz gear mode at ≈ 100 rpm, so K4 is fired at 600 rpm, never below 500 (550 with the 3-D utrons) | drive §4.2; tube-spec B.5 | `[IR]` | PROPOSED |
| Fuse | the driver's 1.5 × limit is the torque fuse; a **rub at the 0.5 mm gap is not limited by it** (1.89 kJ record; ≈ 2.2 kJ now). The POM pinions yield at ≈ 10 N·m on a side gear (derived: 45 MPa short-term at 12.3 MPa for 2.78 N·m); the optional **slip hub (≈ 6 N·m, 80 EUR)** is OPEN | drive §4.3, §5 | `[IR]` | OPEN (designer) |

**The five changes the drawings made (ledger §6 item 74; `sim/unmodelled-parts-findings.md` §2): all PROPOSED, carried.**

| # | First cut | Drawn |
|:--|:--|:--|
| 1 | counter-rotor hub holds the gear-end 6205 over a lip below | cannot carry 350 N: seat open below, lip Ø44 at its top, the gear's flange closes it (DRV-108) |
| 2 | side gear "bolted under the hub" | body r ≤ 28.3 cannot reach: back flange Ø80 × 3, 6 × M4 on PCD 70 (DRV-102) |
| 3 | pinion bearings 16 mm apart | case cannot hold it: 12 mm apart; inner bearing 40 N steady, 195 N at the limit (29 / 141), static safety 10 |
| 4 | bell continues the case wall | cuts the belt land: bell a C, Ø164 / Ø144 over 170°, belt 7.2 mm clear (DRV-106, -107) |
| 5 | 80T pulley "24 mm over the flanges" | catalogue 80T has none, 25 mm through; flanges on the 20T |

**The re-cut (item 71, 2026-10-12, PROPOSED):** drive moved up 30.5 mm; bridge-ring bearing A and its cartridge become
the gear-end bearing (DRV-108, -109 drop out); case cut at z 22.5, 3.5 mm under the spider, **no labyrinth**; the
frame end bearing A and spider go; locating bearing in the case floor is the frame bearing; shaft to z −102.5 with the
rotor gear's keyway; machine z −105.5 …; least turning clearances 1.0 mm (hub to retaining ring), 1.25 mm, 2.75 mm,
2.95 mm. **Stale:** DRV sheets (drawn on the 940 mm stack-up), SHF-305, BRG-811, P-001. With the sixth gap everything
outward of the columns moves 9 mm a side; the stack-up is re-cut with the tube. Carry the drive; the case's seals,
the bell and the slip hub are not designed (OPEN).

### 4  Safety guard (the safety cage)

No evidence file exists for the guard. Everything here is from first principles: `[IR]` choice, `[RH]` estimate, all
**PROPOSED (synthesis)**; the designer decides.

**Design-basis events** (`sim/rotor-mechanics-findings.md` §7, §2): (E1) a loose utron, 2.23 kg, CoM r 97.9 mm,
**66 J at 750 rpm** (42 J at 600); a loose bridge 38 J; a deck fragment ≲ 25 J; (E2) a bearing seizure or a rub at the
0.5 mm gap with ≈ 2.2 kJ stored; (E3) the touch of rotating parts (cage tube surface 11.7 m/s) and of a pulley or belt;
(E4) HV: decks to 14.9 kV, rings ±14.77 kV in the can, stored ≈ 0.1–0.15 J in the capacitors (derived: Ca / Cb 43 mJ each,
rings 12 mJ each, ladder ≈ 7 mJ each; ring τ ≈ 11 s through the assumed 100 GΩ, Ca / Cb minutes through the sticks).

| Parameter | Value | Source / basis | Tag | Status |
|:----------|:------|:---------------|:----|:-------|
| Form | a stationary **earthed perforated cylinder around the tube**, Ø440 inside, from a partition plate at the gear case's top (z ≈ +10, set at the re-cut) to the top plate; **separate belt cover** over the drive bay. Not structural | this spec | `[IR]` | PROPOSED |
| Material | **perforated 5052-H32 aluminium, 4 mm**, Ø5 holes on 7.5 pitch (≈ 40 % open), edges deburred and rolled, bonded to earth. Containment (blunt 2.2 kg, perimeter-shear punch model, half the ligaments): ≈ 180 J against 66 J, margin ≈ 2.7, before the G10 bridge ring and cage tube take their share | derived | `[RH]` | PROPOSED |
| Trade-offs | **polycarbonate**: clear and impact-tough, but insulating: charges tribo-electrically beside an HV rotor, gives no shield, can be a charged surface the operator touches. **Expanded metal**: cheaper, lighter, rough edges (field spikes), diamond slots pass fingers unless fine. **Perforated steel** (2–3 mm per rotor-mechanics §7): stronger per mm but magnetic near the AH null (the guard at 0.22 m is ≈ (25/220)³ ≈ 10⁻³ of the AH field, negligible, but the earth-field shift of the null is already 0.35–0.5 mm, so keep ferromagnets away [RH]). Aluminium chosen: shield, non-magnetic, light, openable | this spec | `[IR]` | PROPOSED |
| Finger safety | holes ≤ 5 mm (IP2X 12 mm probe blocked); ≥ 25 mm from the guard to any moving surface (EN ISO 13857 Table 4 gives ≈ 10 mm for a 4–6 mm slot, from memory: verify) | this spec | `[RH]` | PROPOSED |
| **Clearance to the tube** | guard inner r 220 against the cage tube r 186 (**34 mm**) and the stator rings r 162 (58 mm). Allowance spent: tube concentricity ≈ 1 mm TIR `[RH]`, thermal growth 0.05 mm, whirl at G2.5 3.4 µm, sway under 1 g ≈ 36 µm (g / (2π f1)², f1 83 Hz, derived; the stale 123 µm is a gap change, not a sway), guard tolerance ± 3 mm: ≈ 5 mm, leaving ≈ 29 mm ≥ 25 | derived; `sim/bridge-ring-bearings-findings.md` §3 | `[OC]`/`[RH]` | PROPOSED |
| **Clearance to HV** | decks (r ≤ 150, HV lane r 132) to the guard: **70 mm** (88 mm from the lane), in air, **beyond the 32 mm drawn deck-to-cage gap**; the audit needs ≥ 12 mm to the cage. IEC 60664 case A at 1.5 × 14.9 kV asks ≈ 29 mm (tube-spec A.6, ring lead) → margin 2.4. Mean field ≈ V / d = 14.9 kV / 88 mm ≈ 1.7 kV/cm, × 2.5 geometry ≈ 4 kV/cm against ≈ 30 kV/cm; hole edges ×3–5 stay below onset | tube-spec A.6; audit §2 | `[RH]` | PROPOSED |
| **Ventilation vs clearance** | **No opening is cut in the counter-rotor cage, the can, or any G10 part**, so the deck-to-cage 32 mm and every tube clearance stay as drawn. All airflow is **outside** the cage tube, between it and the guard (the tube sheds its heat through its wall, §6). The guard's perforations only add a further 70 mm of air | this spec | `[IR]` | PROPOSED |
| Earthing | guard, partition, belt cover, case, frame, all panels on **one PE star point**, ≥ 4 mm² Cu, ≤ 0.1 Ω, doors bonded by straps and proven closed by the interlock. Outside the guard the field is ≈ 0 (a 5 mm hole attenuates as e^(−3.8 z/D): e^(−7.6) at 10 mm) | this spec | `[OC]` | PROPOSED |
| Rings' field at the guard | not significant: the rings sit inside the earthed can r 46–48 (null field × 0.9973); the HV outside the can is the decks and the lead bushings, covered above | tube-spec A.6 | `[OC]` | PROPOSED |
| **REF bond** | the model's "room at REF" (`sim/tube-strays-findings.md` §3; floating room moves strays by −0.3…−1 pF, z +0.001) matches an earthed guard only if REF is at earth. **Propose: shaft top end to PE through a silver-graphite brush and a 1 MΩ, ≥ 5 kV resistor.** 1 MΩ costs ≤ 25 V at the clamps' 25 µA asymmetry and limits a flashover's return. The drive study left "earthed or floating" undecided | `docs/drive-gear-belt.md` Not designed; ledger §3.1 | `[IR]` | **OPEN (designer)** |
| **Guard strays** | a potted deck module (≈ 25 mm equivalent radius) to a plane 88 mm away adds ≈ 2–3 pF (sphere-to-plane), against new-node budgets of 1.1–3.5 pF. Cost (tube-spec A.2): ≈ −80 V of ring level per pF on the low end, i.e. ≈ −0.15…−0.3 kV, about one clamp part. **Trim the clamps with the guard fitted.** The layout is not re-run with a REF plane at r 220 | tube-spec A.2; `sim/integrated-multiplier-findings.md` §4 | `[RH]` | OPEN (tube-synth) |
| **Injection / grounding port** | **a closable port in the guard at deck A's station (hub-centred z −78 … −30), 150 × 100 mm**, hinged, interlocked, bonded; behind it the counter-rotor's own G10 port, turned into line at rest (indexing pin on the frame to stop the counter-rotor with its port at the guard port). Insulating tool only (PVC rod, probe), and a **grounding stick** that reaches node 1 / 4 and both rings. Usable in operation as an operating feature: the **port is opened only at standstill** (the stick and injection are rest acts; injection at speed is induction only, tube-spec A.3a). Port 50 mm of air to the terminal, 3.1 × | tube-spec A.3a; audit | `[IR]` | PROPOSED; geometry OPEN |
| Other panels | (a) **top cap** with top plate: lift-off for craning the tube in (≈ 90 kg, shaft-end eye thread, vertical only: gaps lose 0.15–0.25 mm horizontally, rotor-mechanics §4); (b) **belt cover** (tension, pulleys); (c) **instrument window**: a 120 × 80 mm mesh window at the hub station for strobe / probe; (d) **K4 magnet pocket** in the guard wall at side A, machine z ≈ 121 (wedge S3, r ≈ 94 mm), range through the counter-rotor's M235 bridges **not established** (OPEN, tube-spec B.5); keep any permanent magnet ≥ 0.4 m from the hub (≈ 3–6 µT, null shift ≈ 0.03–0.05 mm, derived) | tube-spec B.5; `sim/rotor-parts-drive-findings.md` §4 | `[RH]` | PROPOSED / OPEN |
| No leads out | the tube has no external wiring; the electrical leads of the brief do not exist. The kick circuit is on the rotor (K4); the only bench wires are the REF bond, the speed sensors and thermocouples | tube-spec B.5, C.2 | `[OC]` | PROPOSED |
| **Interlock** | every panel on a **guard-locking, dual-channel switch** (ISO 14119 / 13849-1 PL d, practice): the drive cannot start with a panel open; a panel unlocks only after **standstill from two independent sensors** (driver Hall and a proximity on the counter-rotor flange, both < 5 rpm) **and** the bench's grounding stick has been used. Open request: controlled stop (stop category 1: brake ≈ 19 s) then STO. Fault: STO and coast (≈ 3 rpm/s initially) with the guard locked | `docs/drive-gear-belt.md` §4.3; `docs/bench-test-rings.md` §4 | `[IR]` | PROPOSED |
| Monitoring | thermocouple in the guard air at the hub station: alarm 33 °C, trip 35 °C (hub glass 37.3 °C at room 29.8 °C + 5 K = 34.8 °C) | `sim/hub-thermal-findings.md`; audit | `[IR]` | PROPOSED |

### 5  Base frame

**The finding the drive study left open.** The studies treat the frame bearings as 2e8 N/m and "the frame as rigid"
(`sim/rotor-mechanics-findings.md` caveats; `docs/drive-gear-belt.md` "Not modelled: the frame's own stiffness"). The
placeholder frame (three 45 × 45 Al T-slot columns, I ≈ 1.4e-7 m⁴ `[RH]`, 1.2 m) gives a top-bearing lateral stiffness
of 3 × 12EI/L³ ≈ **2 × 10⁵ N/m** (guided top) , a thousand times under the assumed value. The machine (≈ 90 kg, I about
the bottom bearing ≈ 35 kg·m², top lever 1.06 m) then **rocks at ≈ 13 Hz** (derived), between the 10 Hz synchronous
and 20 Hz relative orders. Requiring the rocking mode ≥ 3 × 20 Hz (the record's own criterion) gives
**k_top ≥ 4.5 × 10⁶ N/m**. `[RH]`

| Parameter | Value | Source / basis | Tag | Status |
|:----------|:------|:---------------|:----|:-------|
| Requirement | lateral stiffness at the top bearing housing **≥ 5 × 10⁶ N/m** (measured, bench-mounted, machine fitted); frame's lowest mode ≥ 150 Hz or clear of 40 / 80 / 120 / 240 / 300 Hz by 15 %; base torsion capacity ≥ 40 N·m (twice the POM fuse's 20 N·m on the carrier) | derived | `[RH]` | PROPOSED |
| Material | **aluminium** (6082-T6), non-magnetic and one earth; steel only below the hub's ±0.5 m | CONVENTIONS shaft rule; §Governing 4 | `[IR]` | PROPOSED |
| Candidate | base plate 25 mm, 760 × 760 (motor out to x = 300, the 245 mm belt centre); **three RHS columns 150 × 150 × 8** (12.3 kg/m, ≈ 44 kg) on a Ø620 pitch circle at 60°, 180°, 300° (none at the motor's 0°), joined at the top by a triangular beam ring and three 100 × 100 × 6 arms carrying a 25 mm centre housing plate. Estimate ≈ 1 × 10⁷ N/m (columns 2 × 10⁷ guided, arms 2 × 10⁷), twice the requirement; FE and tap test before the first spin | derived | `[RH]` | PROPOSED |
| Height | base underside (z −125.5) to top plate (≈ 1049; ≈ 1067 with the sixth gap): **≈ 1.17 m (≈ 1.19 m)** | `sim/rotor-parts-drive-findings.md`; tube-spec C.1 | `[IR]` | PROPOSED; re-lay OPEN |
| Mass, stability | machine ≈ 90 kg + frame ≈ 130 kg + guard ≈ 15 kg ≈ 235 kg; CG ≈ 0.55 m high on a 0.76 m base: tips at ≈ 32°, belt pull 90 N negligible | derived | `[OC]` | PROPOSED |
| Bench mounting | **bolted**, 4 × M10 on a 500 mm square to a bench or slab of mass ≥ 300 kg (the dynamics want stiffness, not mass); elastomer pads under the bench, not under the frame | derived | `[RH]` | PROPOSED |
| Levelling | four screw feet with locking nuts; axis plumb ≤ 0.2° (the record: 0.5° moves the gap ≈ 2 µm); spirit level on the case top before each run; transport and test **vertical** | `sim/rotor-mechanics-findings.md` §4 | `[IR]` | PROPOSED |
| Reaction torque | steady 1.00 N·m on the case, run-up 3.4, limit 5.2; motor plate 0.24 / 0.64 / 0.96 N·m; weight on the locating bearing 872 N: adequate by 8 × (40 N·m capacity); pulsation 0.12 N·m p-p | `docs/drive-gear-belt.md` §7 | `[IR]` | PROPOSED |
| Case, bell | case Ø144 Al 6082 on the base plate by 3 × M6 through the C bell (Ø164 / 144 over 170°); grease and debris fall away from the stack | drive §8; unmodelled-parts §2 | `[IR]` | PROPOSED |

### 6  Thermal management

| Term | W | Source | Tag |
|:--|--:|:--|:--|
| ES pump (clamps 0.594, rings 0.0045, leakage 0.004–0.14, R 0.006) | 0.6 (≤ 0.74 hot) | tube-spec power table | `[OC]` deck; `[IR]` |
| Magnetic pump, 3-D utrons + neck map (D1*–D4* 2.42, La / Lb Cu 0.66 + Fe 0.24–0.42, AH coils 2.44, snubbers ≤ 0.034, utron Cu and iron) | 12.7–15.0 (deck basis 18.1 + 1.25) | tube-spec power table; ledger §3.2 | `[IR]` |
| Windage (vane stacks 4.96, reluctance sections 3.17, rest 3.9) | **12.1** (7.9–25.1) | `sim/rotor-mechanics-findings.md` §6 | `[IR]`; `[RH]` coefficients |
| Bearing friction, 4 inner + 2 frame | 5.1 (3.2–14.2) | the same | `[IR]` |
| Bridge-ring pair + windage | 2.1 (6.1) + 0.06 | `sim/bridge-ring-bearings-findings.md` §4 | `[IR]` |
| Gear case (meshes, pinion bearings, in the drive bay) | 2.6 | `docs/drive-gear-belt.md` §4.1 | `[IR]` |
| **Shaft power = tube + gear** | **≈ 36 nominal, 42 deck basis; design bound 59** (25 W windage allowance) | drive §4.1 | `[IR]` |
| Motor + driver | ≈ 15 (76 W electrical − 61 W) | drive §6 | `[IR]` |

**Heat into the tube compartment ≈ 34–40 W nominal, ≤ 56 W bound.** Windage, bearings and copper all end as heat in the
air inside the counter-rotor cage, which is closed. The audit's ≤ room + 5 K applies to that inner air.

| Parameter | Value | Source / basis | Tag | Status |
|:----------|:------|:---------------|:----|:-------|
| Operating range | room **15–29 °C**, ≤ 600 m; rotor air ≤ room + 5 K (≤ 34 °C); hub glass ≤ 37.3 °C (drawn grooves), 38.0 (full round); AH coils 41–43 °C; POM ≤ 60 °C; HTD belt, SKF grease ≤ 110 °C: not binding | audit; `sim/hub-thermal-findings.md` §3 | `[IR]`; `[RH]` +5 K | PROPOSED (audit) |
| Heat path | **inner air → the cage tube's G10 wall (4 mm, negligible resistance) → the outside air that the tube's own 11.7 m/s surface stirs → guard → room.** Outer h ≈ 30 W/m²K (Re ≈ 3 × 10⁵), inner ≈ 20, area ≈ 0.9 m² (tube, rings, ends): U ≈ 12, so 40 W is ≈ 3.7 K wall-to-air, plus ≈ 1–3 K of outside-air rise: **≈ 5–7 K** total, matching the +5 K | derived | `[RH]` | PROPOSED |
| Ventilation | outside the cage only (§4). **Natural convection through the guard**: inlet band of perforations at the partition (low) and open perforated top cap; the annulus is 0.043 m². Chimney head ≈ 0.11 Pa for 2.5 K mean over 1.1 m, ≈ 7 L/s (derived), against 9–10 L/s needed to carry 55 W at 5 K. Marginal at the bound, adequate at 36 W (≈ 3.5 K) | derived | `[RH]` | PROPOSED |
| Partition | a plate between the tube and drive compartments so the motor (15 W), the driver and the gear (2.6 W) do not feed hot air to the guard's inlet; the drive bay vents away from the tube. Supply and driver outside the guard (§2) | `sim/hub-thermal-findings.md` §3 ("the drive's heat warms it") | `[IR]` | PROPOSED |
| Forced cooling | **not required at steady state** at room ≤ 25 °C on the evidence. Fit a **provision**: a 120 mm axial fan on the top cap (grounded, 20–30 L/s, ≈ 3 ×) fitted only if the bench shows air > room + 5 K or the room exceeds 25 °C. The room limit is 29 °C regardless: the hub glass binds first | audit; hub-thermal | `[RH]` | PROPOSED; OPEN (bench) |
| Guard drag | a close guard raises the outside windage from 2.6 W (still air) by ≈ 1–2 W (Taylor–Couette, gap 34 mm, c_f ≈ 0.006: ≈ 3.8 W) | derived | `[RH]` | PROPOSED |
| Trim temperature | the clamp strings drift +11.9 V/K: trim at the machine's warm steady state, guard on | tube-spec A.4 | `[IR]` | PROPOSED |
| Vent vs HV | perforations 5 mm in earthed metal 70 mm from 14.9 kV parts: no clearance lost (§4) | §4 | `[IR]` | PROPOSED |

### 7  Bay mode f2 and 120 Hz

**The concern (ledger §6 item 77, OPEN).** With the AH-drive parts (+9.74 kg, 4.88 kg a side) f2 of the reluctance bays
falls to **116.8 Hz** (stiff seats, 2e8 N/m) and **107.9 Hz** (G10 spiders, 0.86e8), 2.7–10 % under the pumps' 120 Hz
(`sim/rotor_parts_drive_results.json` shafts; f1 79.3–83.9; f3 149–165). Without the parts f2 is 136–156 Hz. f2 bends
the shaft's outer spans in phase against the centre (`sim/bridge-ring-bearings-findings.md` §3).

| Parameter | Value | Source / basis | Tag | Status |
|:----------|:------|:---------------|:----|:-------|
| Excitation | the utrons' pulls are three-fold symmetric: no net side load in the ideal; the ES varicaps are six-fold: none. A lateral 120 Hz force needs an asymmetry: F ≈ asymmetry × 3 × 28–42 N: 4–6 N p-p for 5 % (A and B in antiphase). Response needs modal mass and Q from the tap test | `sim/rotor-mechanics-findings.md` §3; ledger item 77 | `[RH]` | OPEN |
| Run-up | 120 Hz crosses f1 at ≈ 67 % speed and f2 at 90–97 % (≈ 2.4 s); the magnetic pump is kicked at 600 rpm, so only the symmetric ES pump runs through both | drive §4.2 | `[IR]` | PROPOSED |
| Retainer levers | (1) **seat stiffness**: 0.86e8 → 2e8 N/m moves f2 only +8.9 Hz (107.9 → 116.8); infinite stiffness stays near 125 Hz (derived from the layout's ratio, 1.12 ×) `[RH]`; the study varies all seats together: the frame bearings' share is **not separated**. (2) **preload** 100 → 250 N: bearing stiffness +36 %, f2 ≈ +1.5 Hz `[RH]`. (3) **frame top stiffness** (§5): unmodelled; a soft top lowers f2. (4) damping: an elastomer-ringed floating top bearing adds damping and loses stiffness | derived | `[RH]` | OPEN |
| What detunes it | mass, not support: f2 scales as 1/√(M_eff); the 4.88 kg a side cut f2 by 25 %, implying M_eff ≈ 6 kg a side `[RH]`. The compact EI-66 choke (saves ≈ 1.6 kg a side) gives ≈ 126 Hz stiff / 110 G10; d 30 (the layout's ratio 1.16) gives ≈ 125–136. Both are tube levers (tube-synth, ledger Rec. 8) | rotor-parts-drive §4; `sim/bridge-ring-bearings-findings.md` §3 | `[RH]` | OPEN (designer) |
| Acceptance rule | no measured mode of the assembled machine within ±10 % of 120 or 240 Hz or of the 300 Hz mesh unless its measured response at the gap is ≤ 10 µm (10 % of g is 50 µm) | `sim/rotor-mechanics-findings.md` §5.4 | `[RH]` | PROPOSED |
| Bench | (a) **tap test** (instrumented hammer, 3-axis accelerometers at the Ca\|reluctance, bridge-ring and frame stations, bay stations) on the **rotor with its parts mounted**, in the frame, at standstill, with the springs at 100, 150, 250 N; (b) the same with the frame bearings locked and free (frame share of f2); (c) the bare frame with a dummy mass; (d) run-up and coast-down waterfall on frame accelerometers over 0–300 Hz, marking 40 / 80 (motor), 71.7 / 108.3 (inner bearings), 120 / 240 (pumps), 300 (mesh) | `sim/rotor-parts-drive-findings.md` §4 | `[IR]` | PROPOSED |

## Evidence ledger

| Item | Current design | Evidence | Issue (if any) |
|:-----|:---------------|:---------|:---------------|
| bearings | 6 × SKF 6205-2Z, P5; 2 frame (retainer), 4 inner (tube) | `sim/bridge-ring-bearings-findings.md` | catalogue data from a web search; re-read before ordering |
| preload | 100 N vs SKF 125–250 N | the same §4 | OPEN (designer); 150 N proposed |
| runout | 0.027 (six) / 0.05 mm (eighth pair) | `sim/rotor-mechanics-findings.md` §5.4 | influence not re-run for the placed pair |
| first mode | 83–87 Hz (d 25), gap +1.1…1.6 µm | `sim/bridge-ring-bearings-findings.md` §3 | 27–29 Hz and 123 µm are the six-bearing layout |
| f2 | 107.9–116.8 Hz | `sim/rotor-parts-drive-findings.md` | near 120 Hz; frame's share unseparated |
| locating bearing | 65 000 h at 689 N | `docs/drive-gear-belt.md` §7 | masses grew: ≈ 39 000 h at 872 N (derived) |
| drive | bevel reverser, HTD 5M 4 : 1, 200 W | `docs/drive-gear-belt.md` | five changes; re-cut on the layout; sheets stale; seals, bell, slip hub open |
| frame | 3 × 45 × 45 Al, never checked | drive §8 | rocking ≈ 13 Hz derived (§5) |
| grease | 30 vs 70 vs 100 mm²/s in different studies | `sim/rotor-mechanics-findings.md` §6; drive §4.1 | no grease chosen; bearing drag 5–11 W |
| windage | 12 W (8–25); allowance 25 W | `sim/rotor-mechanics-findings.md` §6 | coast-down to settle |
| thermal | glass 32.5 °C, room ≤ 29.8 °C, air +5 K | `sim/hub-thermal-findings.md` | air rise `[RH]`, not computed |
| guard | none in the record | — | specified here from first principles |
| REF to earth | undecided | drive §"Not designed" | OPEN |

## Cross-spec dependencies

| Item | Value | Needed by | Note |
|:-----|:------|:----------|:-----|
| Frame-bearing stiffness, preload, top-support stiffness | 1.2–2e8 N/m seats, 150 N, ≥ 5e6 N/m top | tube-synth (shaft dynamics, f1 / f2) | re-run `sim/shaft_bearings.py` with the frame k_b swept separately and a finite top support |
| Locating-bearing seat and weight | 872 N axial, 160 N radial | tube-synth | masses to be re-counted with the sixth gap |
| Guard strays | ≈ 2–3 pF on deck nodes | tube-synth, electrical-integrity | re-run the layout with a REF plane at r 220; trim with the guard on |
| Guard inner r 220; deck-to-cage clearance unchanged | 70 mm to decks; no opening in cage, can or G10 | electrical-integrity | closes "ventilation vs HV" |
| Injection / grounding port, interlocked, standstill-only | guard hatch at deck A's station z −78 … −30; counter-rotor port indexed | tube-synth (A.3a), electrical-integrity | geometry OPEN |
| REF bond | brush + 1 MΩ to PE | electrical-integrity, tube-synth | the designer's |
| K4 magnet station | guard pocket at machine z ≈ 121 side A | tube-synth | reed range through the bridges unproven |
| Thermal | heat 34–40 W (≤ 56 W) into the compartment; air ≤ room + 5 K; room 15–29 °C, ≤ 600 m | electrical-integrity, conservation-auditor | table §6 |
| Stored energy at the driver | ≈ 2.2 kJ; brake chopper ≥ 2.5 kJ | conservation-auditor | |
| **From tube-spec** | envelope 1014 (≈ 1032) mm, frame bearings 1060 (≈ 1078) mm, masses 35.88 + 9.74 (+ 1.0) / 36.40 kg, shaft d 25 (d 30 OPEN), 6 × 6205-2Z, belt interface | this spec | the sixth-gap re-lay moves the drive stack-up |
| **From electrical-integrity** | operating range, field at the guard, port use | this spec | taken from the audit |

## Items deferred to bench

| Item | Why it is open | What the bench measures | Source |
|:-----|:---------------|:-----------------------|:-------|
| Modes, f2, seat share | seats bracketed 0.86–2e8, frame share unseparated | tap tests §7 (a)–(c) | `sim/rotor-parts-drive-findings.md` |
| Preload | 100 / 150 / 250 N | coast-down loss, noise, waterfall at 71.7 and 108.3 Hz | `sim/bridge-ring-bearings-findings.md` §4 |
| Windage, bearing loss | 8–25 W, 3–14 W | coast-down from 600 rpm | `sim/rotor-mechanics-findings.md` §6, §8 |
| Frame stiffness, rocking mode | derived ≈ 13 Hz placeholder | hammer test at the top housing | §5 |
| Belt tension | 46 N | pluck 61 Hz | `docs/drive-gear-belt.md` §6 |
| Air rise | +5 K `[RH]` | thermocouples in the guard air and on the cage tube, at 25 and 29 °C room | `sim/hub-thermal-findings.md` |
| Guard field | hole-edge field, strays | dark-room corona watch, ring level with and without the guard | tube-spec A.2 |
| REF potential | floating vs bonded | electrostatic voltmeter on the shaft, brush in and out | ledger §3.1 |
| Jam behaviour | POM fuse ≈ 10 N·m | not run: analysis only | `docs/drive-gear-belt.md` §5 |

## Recommendations for the designer

All PROPOSED (synthesis). The designer decides.

1. **Preload 150 N** on every floating bearing, springs in opposed pairs; keep P5 and the 0.027 mm runout.
2. **Carry the drive** (bevel reverser, HTD 5M 4 : 1, 200 W) as re-cut; re-cut its stack-up on the sixth-gap tube;
   decide the **slip hub** (≈ 6 N·m) for a rub; re-count the locating bearing (≈ 39 000 h) or go to a 25 mm bore of the
   next series.
3. **Replace the placeholder frame**: aluminium RHS columns with a top ring, k_top ≥ 5 × 10⁶ N/m, then have mech-scrutiny
   re-run the shaft model with that finite top support and with the frame k_b swept alone.
4. **Adopt the guard** (4 mm perforated aluminium, Ø440, earthed, interlocked, standstill unlock) and decide the **REF
   bond** (brush + 1 MΩ).
5. **Settle f2 jointly with tube-synth** (compact EI-66 choke, d 30); seats and preload alone do not clear it.
6. **Set the site envelope** at room 15–29 °C, ≤ 600 m, fit a fan provision, alarm the air at 33 °C.
7. **Place the K4 magnet** (reed range through the bridges) and the injection port index.
8. **Choose a grease** (low viscosity) and pin the bearing drag.
