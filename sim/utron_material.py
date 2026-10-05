#!/usr/bin/env python3
"""sim/utron_material.py -- what the utron core (and the C-EM core) can be made of for a 15 us half-sine pulse.

The circuit is gap-dominated (1-D reluctance, fringing ignored):                                      [RH]
  aligned:   jaw-to-jaw 60 mm = utron 46 mm (along z, the flux) + 14 mm of air  ->  X = g + l/mu_eff
  unaligned: 60 mm of air                                                        ->  X = 60
  L ~ 1/X.

mu_eff is complex. For a conducting sheet or block of thickness t across the flux it is the classic
lamination result,
  mu_eff = mu * tanh(k t/2) / (k t/2),   k = (1 + j)/delta,   delta = sqrt(2 rho / (omega mu)).
For powders, mu' and tan(delta) are taken as given.                                                  [RH]

What it reports:
  * L'/L_ideal: the aligned inductance reached, against an ideal (infinite-mu) utron;
  * swing: (L'_al - L_un)/L'_al, the reluctance-torque lever (F = 1/2 i^2 dL/dx);
  * tan_L = Im X / Re X: about pi*tan_L of the peak stored energy is lost per half-sine pulse.
Usage: python3 sim/utron_material.py -> sim/utron_material_results.json
"""
import cmath
import json
import math
import os

HERE = os.path.dirname(os.path.abspath(__file__))
MU0 = 4e-7 * math.pi
F_EQ = 1.0 / (2 * 15e-6)                                 # a 15 us half-sine ~ 33 kHz [RH]
G_AIR, L_U, G_UN = 14.0, 46.0, 60.0                      # mm, from the STEP (jaw gap 7.0 mm each side)
L_CORE = 300.0                                           # C-EM core mean path, mm [RH: from the section]

# name, mu_r (pulse, mid-B), rho (Ohm m), sheet / block thickness t (m, None for powder), tan(delta) for
# powders, B_sat (T), sourcing [RH]
MATERIALS = [
    ("solid low-carbon steel (block, t = 46 mm)", 1000, 1.4e-7, 46e-3, None, 2.0, "any steel stock"),
    ("soft steel, hollow (bore along z: a closed shorted turn)", None, None, None, None, 2.0, "-"),
    ("soft steel, 3 mm slotted fins (comb)", 1000, 1.4e-7, 3e-3, None, 2.0, "steel bar, wire-EDM slots"),
    ("soft steel, 1 mm fins / sheet stack", 1000, 1.4e-7, 1e-3, None, 2.0, "1 mm DC01 sheet, laser-cut, varnished"),
    ("soft steel, 0.5 mm sheet stack", 1000, 1.4e-7, 0.5e-3, None, 2.0, "0.5 mm DC01 sheet, laser-cut, varnished"),
    ("electrical steel M235-35A, 0.35 mm", 2000, 5.9e-7, 0.35e-3, None, 1.9, "transformer / motor laminations, laser-cut"),
    ("electrical steel NO20 / 0.2 mm", 2000, 5.2e-7, 0.2e-3, None, 1.9, "thin-gauge NO steel (EV motor grade)"),
    ("electrical steel 0.1 mm (10JNEX900 / Arnon 5)", 2000, 5.2e-7, 0.1e-3, None, 1.8, "specialist thin gauge"),
    ("amorphous ribbon 2605SA1, 25 um (cut core)", 3000, 1.3e-6, 25e-6, None, 1.56, "Metglas AMCC cut cores"),
    ("SMC (Somaloy-class), machined blank", 400, None, None, 0.15, 1.6, "SMC prototype blanks, machinable"),
    ("iron powder (carbonyl / mix -26, mu 75)", 75, None, None, 0.02, 1.2, "powder cores / bars"),
    ("MnZn ferrite (reference)", 2000, None, None, 0.01, 0.45, "hard to source at this size"),
]


def mu_lam(mu_r, rho, t):
    w = 2 * math.pi * F_EQ
    delta = math.sqrt(2 * rho / (w * mu_r * MU0))
    k = (1 + 1j) / delta
    x = k * t / 2
    return mu_r * cmath.tanh(x) / x, delta


def evaluate(row, path_mm=L_U, gap_mm=G_AIR, un_mm=G_UN):
    name, mu_r, rho, t, tan, bsat, src = row
    if mu_r is None:                                     # closed conducting tube around the flux: excludes it
        return dict(material=name, mu_eff=[0.0, 0.0], delta_mm=None, L_rel=0.0, swing="negative (repulsion)",
                    tan_L=None, B_sat_T=bsat, sourcing=src)
    if t is not None:
        mu, delta = mu_lam(mu_r, rho, t)
    else:
        mu, delta = mu_r * (1 - 1j * tan), None
    X = gap_mm + path_mm / mu
    L = 1 / X
    L_rel = (1 / X).real * gap_mm
    swing = 1 - (1 / un_mm) / L.real
    return dict(material=name, mu_eff=[mu.real, -mu.imag], delta_mm=delta * 1e3 if delta else None,
                L_rel=L_rel, swing=swing, tan_L=X.imag / X.real, B_sat_T=bsat, sourcing=src)


if __name__ == "__main__":
    ideal = 1 - G_AIR / G_UN
    out = dict(f_eq_Hz=F_EQ, gap_mm=G_AIR, utron_mm=L_U, unaligned_mm=G_UN, swing_ideal=ideal,
               utron=[evaluate(m) for m in MATERIALS],
               cem_core=[evaluate(m, path_mm=L_CORE, gap_mm=G_AIR, un_mm=G_UN) for m in MATERIALS if m[1]])
    json.dump(out, open(os.path.join(HERE, "utron_material_results.json"), "w"), indent=1)
    print(f"f_eq {F_EQ/1e3:.1f} kHz; ideal swing {ideal:.3f}")
    for tag in ("utron", "cem_core"):
        print(f"\n{tag}: material | mu_eff' / mu_eff'' | delta mm | L'/L_ideal | swing | tan_L | B_sat")
        for r in out[tag]:
            sw = r["swing"] if isinstance(r["swing"], str) else f"{r['swing']:.3f}"
            print(f"  {r['material'][:52]:52s} | {r['mu_eff'][0]:8.1f} / {r['mu_eff'][1]:7.1f} | "
                  f"{r['delta_mm'] if r['delta_mm'] is None else round(r['delta_mm'], 3)} | {r['L_rel']:.3f} | {sw} | "
                  f"{r['tan_L'] if r['tan_L'] is None else round(r['tan_L'], 3)} | {r['B_sat_T']}")
