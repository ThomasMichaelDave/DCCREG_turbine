# Tube machine — energy ledger with a belt drive, and the C-EM motor (findings)

Source: `sim/tube_ledger.py` → `sim/tube_ledger_results.json`. Tube defaults (300 mm vanes, 3 mm air, 8 + 8 vanes),
v4 topology, 300 rpm relative, eigen-state scaled to a 20 kV cycle peak, 6 cycles per revolution.

## 1. Ledger: closes

Belt work per cycle = growth of stored energy + every dissipation (gaps, tank/Lx rings, relaxation, coils):

| strays | z | belt / cycle | growth | losses | closure | belt at 300 rpm | losses | available to a load |
|:--|:--|:--|:--|:--|:--|:--|:--|:--|
| fixed | 1.614 | 82.1 mJ | 43.8 mJ | 38.3 mJ | 1e-14 J | 2.46 W | 1.15 W | 1.31 W |
| scaled | 1.315 | 82.3 mJ | 58.7 mJ | 23.5 mJ | 1e-13 J | 2.47 W | 0.71 W | 1.76 W |

Every joule is accounted for; the pump is a belt-to-HV converter and returns at most what the belt puts in. The
"available" column is the growth term, which a load or limiter takes at a 20 kV steady state [IR]. Not yet in the
losses: core eddy loss, corona and leakage, and the mechanical drag below (that is paid by the belt as well).

## 2. Motor: cannot counter-rotate the stator

- **Direct (pulse only):** 5.8e-7 N·m, 1.8e-5 W. The pulse lasts tens of µs and the utron barely moves during it.
- **Freewheel ceiling** (the coil current kept flowing across the stroke, every joule stored in the coils converted):
  1.2 mN·m, 0.04 W. At the real swing (dL/L_aligned 12.8 % at r_u 130) about 0.15 mN·m.
- **Stator drag needed** at 150 rpm counter (symmetric split) [RH, estimates]:
  - air shear between the 84 rotor-vane faces and the stator vanes: 5–12 mN·m;
  - bearings carrying the 52 kg stator (μ 0.0015): 15 mN·m;
  - windage of the 12 C-EMs at r 235 in open air: about 200 mN·m (goes away in a shell or under vacuum).
  - **Total: 19 mN·m (no windage) to 225 mN·m (open air), 0.3–3.5 W.**

Verdict: the direct drive is about 5 orders short. Even the freewheel ceiling is 15–190× short. The whole pump surplus
(1.3–1.8 W) only matches the no-windage drag at 100 % conversion, and a 13 % swing reluctance motor gets nowhere near
that. Same conclusion as the disc design (`sim/motor-geometry-findings.md`).

## 3. What works

The pump only needs the **relative** speed. Options, all on the belt:
1. Stationary stator, belt on the rotor: simplest; nothing else changes.
2. Counter-rotation from the same belt drive through a reversing gear or a second pulley on the stator: halves each
   body's speed. The belt pays the drag either way.

The C-EMs and utrons then carry no drive duty. They can stay as built (the pump holds z with them in the circuit) or come
out to save 19 kg of core on the stator.
