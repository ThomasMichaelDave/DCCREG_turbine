#!/usr/bin/env python3
"""
sim/pump_sizing.py — PUMP-SYNTH / PUMP-CALC r0.2 sizing: rotor plates -> C1/C2 -> the capacitance ladder
=======================================================================================================
A pure, JSON-safe function `size(plates, choices) -> ladder`. It is mirrored 1:1 in JS in
tools/pump-synth.html (gate S1b holds the two to 1e-12).

  1. Rotor plates -> C_max, C_min, kappa_C by the design guide's forward law (docs/varcap-machine-
     design-guide.md Eqs. (5)-(9), A.10). The formulas are ported from index.html's Block C-I plate engine
     (plateGeom / plateCaps / epsAir / epsRof @ 8cd181e), with the freeze/DXF defaults instead of the stale ones.
  2. The ladder (guide §6.1-6.2) sizes every other pump capacitor from C_rot = C_max. The cascade pattern
     follows index.html cascadeState ("Ca = ratio * Cmax"), extended to Cx, Cpar, Lx and C_blk.

TMD-gated choices, shipped at the flagged default with the alternative selectable:
  D-CMIN  'active_fringe' (default: active area only + a fixed 16 pF fringe floor, the design_synth /
          geom-extract basis, which matches the locked 280/16) | 'ring' (guide Eqs. 5-7: the ring adds to C_max
          and sets C_min)
  D-CA    Ca/C_max = 1.10 (the guide's transfer match)
  D-CX    Cx,max/C_max = 1.68 (inherited from the tank dump match, guide §6.2)
  D-CPAR  'fixed' (default: 20 pF floor and fixed strays) | 'scaled' (strays scale with C_max relative to the
          freeze point)
Pins: any ladder value can be overridden (pins={key: value}); a pinned value is reported as such.
Tiers [OC]/[IR]/[RH]/[ME]. Pure EE. No file I/O or subprocess on the import path.
"""
import json
import math

EPS0 = 8.8541878128e-12                       # F/m, CODATA 2018 [OC] (= index.html eps0, design_synth EPS0)
SW_K1, SW_K2 = 77.6, 3.73e5                   # Smith-Weintraub [OC] (index.html)
BUCK_A, BUCK_B, BUCK_C, BUCK_D = 6.1121, 18.678, 234.5, 257.14   # Buck (1981) [OC] (index.html)
DIELECTRICS = {"vacuum": 1.0, "air": None, "kapton": 3.4, "mica": 5.4}   # index.html DIELECTRICS (nominal) [OC/IR]
BUS_MARGIN = 0.27                             # rotor outer = active-band outer x (1 + 0.27): design_synth [OC]
C_FREEZE_PF = 279.6                           # the freeze-point C_max, active area, vacuum (S1) [OC]

PLATE_DEFAULTS = dict(
    r_inMm=95.0, r_outMm=387.0,               # active band R95-R387 (freeze / DXF)
    g_vMm=7.0, dielectric="air",              # rotor gap and its medium
    tempC=20.0, p_hPa=1013.0, rh=50.0,        # moist-air state (A.10)
    N_sec=12, n_kept=6,                       # sectors / kept
    ring_on=True, r_ring_inMm=25.0, r_ring_outMm=68.2,   # central ring R25..R68.2: A_ring 0.01265 m^2 -> C_min 16.0 pF at 7 mm vacuum (brief S1)
)
CHOICE_DEFAULTS = dict(
    cmin_conv="active_fringe", C_fringe_pF=16.0,          # D-CMIN
    ratio_Ca=1.10, ratio_Cx=1.68, ratio_CR=2.82,          # D-CA, D-CX; C_R shown only (tank collapsed)
    cpar_mode="fixed", Cpar_pF=20.0,                      # D-CPAR
    cx_min_pF=8.0, gap_stray_pF=2.0, pCboss_pF=6.0, island_stray_pF=5.0,
    Lx_mH=1.0, R_lx=2.0,
    rpm=3000.0, L_coil_H=0.64, R_coil=40.0,               # motor branch: C_blk from the resonance rule
    pins={},
)
LADDER_KEYS = ("C_max", "C_min", "Ca", "Cb", "cx_max", "cx_min", "Cpar", "gap_stray", "pCboss",
               "island_stray", "Lx_mH", "R_lx", "C_blk_nF")


def eps_air(tempC, p_hPa, rh):
    """Moist-air relative permittivity, Eqs. (14)-(15): eps_r = 1 + 2 N 1e-6 (index.html epsAir). [OC]"""
    tK = tempC + 273.15
    p_sat = BUCK_A * math.exp((BUCK_B - tempC / BUCK_C) * (tempC / (BUCK_D + tempC)))
    p_vap = (rh / 100.0) * p_sat
    N = SW_K1 * p_hPa / tK + SW_K2 * p_vap / (tK * tK)
    return 1.0 + 2.0 * N * 1e-6


def eps_r(p):
    if p["dielectric"] == "air":
        return eps_air(p["tempC"], p["p_hPa"], p["rh"])
    return DIELECTRICS[p["dielectric"]]


def plate_areas(p):
    """Kept-sector metal area, Eq. (8), and ring area, Eq. (9) (m^2). [OC]"""
    kept = p["n_kept"] / p["N_sec"]
    ri, ro = p["r_inMm"] * 1e-3, p["r_outMm"] * 1e-3
    A_m = kept * math.pi * (ro * ro - ri * ri) if ro > ri else 0.0
    rri, rro = p["r_ring_inMm"] * 1e-3, p["r_ring_outMm"] * 1e-3
    A_ring = math.pi * (rro * rro - rri * rri) if (p["ring_on"] and rro > rri) else 0.0
    return A_m, A_ring


def rotor_caps(p, conv="active_fringe", C_fringe_pF=16.0):
    """C_max, C_min (pF) and kappa_C under the D-CMIN convention.
    'ring' (guide Eqs. 5-7): C_max = e0 er (A_m + chi A_ring)/g, C_min = e0 er chi A_ring/g.
    'active_fringe': C_max = e0 er A_m/g, C_min = the fixed fringe floor. [OC law; IR convention]"""
    A_m, A_ring = plate_areas(p)
    g = p["g_vMm"] * 1e-3
    k = EPS0 * eps_r(p) / g * 1e12
    if conv == "ring":
        cmax = k * (A_m + A_ring); cmin = k * A_ring
    elif conv == "active_fringe":
        cmax = k * A_m; cmin = C_fringe_pF
    else:
        raise ValueError(conv)
    return cmax, cmin, (cmax / cmin if cmin > 0 else float("inf"))


def c_blk_nF(rpm, L_coil_H, groups):
    """Motor DC-block cap resonant at the branch PRF, C = 1/((2 pi PRF_branch)^2 L). PRF_branch =
    ceil(N_sec/2) rpm/60 (index.html machinePRF; 300 Hz at 3000 rpm and 12 sectors). [OC]"""
    prf = groups * rpm / 60.0
    return 1e9 / ((2.0 * math.pi * prf) ** 2 * L_coil_H), prf


def size(plates=None, choices=None):
    """Rotor plates + choices -> the ladder (JSON-safe). Every entry: value, ratio to C_rot = C_max, rule,
    tag, pinned flag. Also the geometry readouts (rotor diameter, rim speed, both D-CMIN conventions)."""
    p = dict(PLATE_DEFAULTS); p.update(plates or {})
    c = dict(CHOICE_DEFAULTS); c.update(choices or {})
    pins = dict(c.get("pins") or {})
    for k in pins:
        if k not in LADDER_KEYS:
            raise KeyError(f"cannot pin {k!r}")
    cmax, cmin, kap = rotor_caps(p, c["cmin_conv"], c["C_fringe_pF"])
    cmax_r, cmin_r, _ = rotor_caps(p, "ring")
    cmax_a, _, _ = rotor_caps(p, "active_fringe", c["C_fringe_pF"])
    groups = int(math.ceil(p["N_sec"] / 2))
    cblk, prf = c_blk_nF(c["rpm"], c["L_coil_H"], groups)
    scale = (cmax / C_FREEZE_PF) if c["cpar_mode"] == "scaled" else 1.0
    raw = dict(
        C_max=(cmax, "forward law Eq. (5)", "[OC] law; D-CMIN convention"),
        C_min=(cmin, "Eq. (6)" if c["cmin_conv"] == "ring" else "fixed fringe floor", "[IR] D-CMIN"),
        Ca=(c["ratio_Ca"] * cmax, f"{c['ratio_Ca']:g} x C_max (index.html cascadeState)", "[IR] D-CA"),
        Cb=(c["ratio_Ca"] * cmax, "= Ca", "[IR] D-CA"),
        cx_max=(c["ratio_Cx"] * cmax, f"{c['ratio_Cx']:g} x C_max (tank dump match)", "[IR] D-CX"),
        cx_min=(c["cx_min_pF"] * scale, "island collapsed value (island_charging_cosim.CX_MIN)", "[IR]"),
        Cpar=(c["Cpar_pF"] * scale, "fixed floor on nodes 1-4 (I6)" if scale == 1.0 else
              "floor scaled with C_max", "[IR] D-CPAR"),
        gap_stray=(c["gap_stray_pF"] * scale, "per-gap stray (shuttle default)", "[IR] D-CPAR"),
        pCboss=(c["pCboss_pF"] * scale, "boss stray in parallel with Cx", "[IR] D-CPAR"),
        island_stray=(c["island_stray_pF"] * scale, "7/8/n17/n23 -> reference (r0.2 lock)", "[IR] D-CPAR"),
        Lx_mH=(c["Lx_mH"], "series island inductor (0 = direct island)", "[IR]"),
        R_lx=(c["R_lx"], "Lx ESR (integrator design point)", "[IR]"),
        C_blk_nF=(cblk, f"1/((2 pi {prf:.0f} Hz)^2 x {c['L_coil_H']:g} H)", "[OC] law"),
    )
    lad = {}
    for k, (v, rule, tag) in raw.items():
        pv = pins.get(k)
        val = float(pv) if pv is not None else float(v)
        unit = "mH" if k == "Lx_mH" else "ohm" if k == "R_lx" else "nF" if k == "C_blk_nF" else "pF"
        ratio = (val / cmax) if (unit == "pF" and cmax > 0) else ((val * 1e3 / cmax) if unit == "nF" and cmax > 0 else None)
        lad[k] = dict(value=val, unit=unit, ratio=ratio, rule=rule, tag=tag, pinned=pv is not None,
                      ladder_value=float(v))
    r_rot = p["r_outMm"] * (1.0 + BUS_MARGIN)
    rim = 2.0 * math.pi * c["rpm"] / 60.0 * r_rot * 1e-3
    A_m, A_ring = plate_areas(p)
    return dict(plates=p, choices={k: v for k, v in c.items() if k != "pins"}, pins=pins, ladder=lad,
                kappa_C=(lad["C_max"]["value"] / lad["C_min"]["value"]) if lad["C_min"]["value"] > 0 else None,
                conventions=dict(active_fringe=dict(C_max=cmax_a, C_min=c["C_fringe_pF"]),
                                 ring=dict(C_max=cmax_r, C_min=cmin_r)),
                eps_r=eps_r(p), A_m=A_m, A_ring=A_ring, PRF_branch=prf, groups=groups,
                C_R_pF=c["ratio_CR"] * cmax, rotor_dia_mm=2.0 * r_rot, rotor_outMm=r_rot, rim_mps=rim)


def engine_config(lad, extra=None):
    """The ladder -> sim/pump_engine config keys (C_blk is the per-coil cap of the drawn per-coil topology)."""
    L = lad["ladder"]
    cfg = dict(C1min=L["C_min"]["value"], C1max=L["C_max"]["value"], C2min=L["C_min"]["value"],
               C2max=L["C_max"]["value"], Ca=L["Ca"]["value"], Cb=L["Cb"]["value"], Cpar=L["Cpar"]["value"],
               cx_max=L["cx_max"]["value"], cx_min=L["cx_min"]["value"], pCboss=L["pCboss"]["value"],
               gap_stray=L["gap_stray"]["value"], island_stray=L["island_stray"]["value"],
               Lx_mH=L["Lx_mH"]["value"], R_lx=L["R_lx"]["value"], C_motor_nF=L["C_blk_nF"]["value"],
               L_motor=lad["choices"]["L_coil_H"], R_motor=lad["choices"]["R_coil"], rpm=lad["choices"]["rpm"])
    cfg.update(extra or {})
    return cfg


def electrode_areas(lad):
    """Optional electrode-area ladder, guide §6.3-6.4 area law A = C (sum g_i/eps_i)/eps0 (m^2) for the
    locked dielectrics: Ca/Cb 4.5 mm mica; Cx 3.0 mm air + 0.3 mm mica in series. [OC law, IR stack]"""
    L = lad["ladder"]

    def area(C_pF, layers):
        return C_pF * 1e-12 * sum(t * 1e-3 / er for t, er in layers) / EPS0
    return dict(Ca=area(L["Ca"]["value"], [(4.5, 5.4)]), cx_max=area(L["cx_max"]["value"], [(3.0, 1.0006), (0.3, 5.4)]),
                rotor_active=lad["A_m"])


def _selftest():
    ok = True
    # S1 at the freeze geometry, vacuum: active-only 279.6 pF (= design_synth.Cmax_from_geom), ring 295.6 pF
    p = dict(PLATE_DEFAULTS, dielectric="vacuum")
    a, _, _ = rotor_caps(p, "active_fringe")
    r, rmin, _ = rotor_caps(p, "ring")
    A_m, A_ring = plate_areas(p)
    ok &= abs(a - 279.6) < 0.05 and abs(r - 295.6) < 0.06 and abs(r - a - rmin) < 1e-9
    ok &= abs(A_ring - 0.01265) < 2e-6 and abs(rmin - 16.0) < 0.02
    # dry air at 0 C, 1013 hPa: eps_r = 1.000576 (guide A.10 numeric check)
    ok &= abs(eps_air(0.0, 1013.0, 0.0) - 1.000576) < 2e-6
    # S3: C_blk 440 nF (+-0.5 %) at 300 Hz, 0.64 H
    cb, prf = c_blk_nF(3000.0, 0.64, 6)
    ok &= abs(prf - 300.0) < 1e-12 and abs(cb - 440.0) / 440.0 < 5e-3
    # H-GEOM: rotor diameter 983 mm at r_out 387
    ok &= abs(size()["rotor_dia_mm"] - 982.98) < 0.01
    if not ok:
        raise AssertionError("pump_sizing on-load self-test FAILED")
    return True


SELFTEST_OK = _selftest()

if __name__ == "__main__":
    print(json.dumps(size(), indent=1))
