"""sim/tube_ledger.py -- the tube machine's energy ledger with a belt on the shaft, and whether the C-EM / utron
reluctance motor can counter-rotate the stator.

Usage: python3 sim/tube_ledger.py   (writes sim/tube_ledger_results.json)

1. Ledger: the v4 tube pump (stack_sizing defaults, strays fixed and scaled) in rt_engine with record=True, the
   eigen-state scaled to a 20 kV cycle peak. Belt work per cycle W = growth of stored energy + every dissipation;
   the closure is checked to round-off. 6 cycles per revolution (N_sec 12).
2. Motor: torque F = 1/2 i^2 dL/dtheta from the engine's int i^2 dt in the lumped C-EM groups, with dL/dtheta from the
   tube_magnetic.py swing at r_u 130; plus the freewheel ceiling (every joule stored in the coils converted).
3. Stator drag: vane air shear, bearings, C-EM windage. Every drag figure is an estimate [RH].
"""
import json
import math
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path[:0] = [HERE, os.path.dirname(HERE), os.path.join(os.path.dirname(HERE), "reference")]
import stack_sizing as S                                 # noqa: E402
import pump_synth as SY                                  # noqa: E402
import rt_engine as RT                                   # noqa: E402
import pump_engine as PE                                 # noqa: E402

RPM_REL, V_PEAK, CYC_PER_REV = 300.0, 20e3, 6
MU0_MM = 4e-7 * math.pi * 1e-3                           # H per (turn^2 mm)
N_TURNS = 1846                                           # 0.40 mm winding (cem_inductance.py) -> ~1.9 H at r_u 130
STATOR_KG = 52.0       # from the STEP solids: Al vanes/plates 11.8, C-EM cores 19.4, G10 cage/spiders/rings 17.7, W-Cu 2.0, rest 1.1
MU_AIR, RHO_AIR = 1.8e-5, 1.2


def ledger(cpar_mode):
    lad = S.size_stack("tube", {}, {} if cpar_mode is None else dict(cpar_mode=cpar_mode))
    fi = dict(SY.FIRING_DEFAULTS) if hasattr(SY, "FIRING_DEFAULTS") else SY.split({})[2]
    cfg = SY.engine_cfg(lad, fi)
    q = dict(S.V4_DEFAULTS)
    net = RT.build_net(cfg, tank="series", C_R1_pF=q["C_tank_pF"])
    Lt = q["L_tank_uH"] * 1e-6
    Rt = (1 / math.sqrt(Lt * q["C_tank_pF"] * 1e-12)) * Lt / q["Q_tank"]
    net.inds.append(("L_tank_chain", net.n("R-B"), PE.GND, Lt, Rt, "lx"))
    n = q["n_coils"]
    for gname, node, mid in (("SG1", "2", "mA"), ("SG2", "3", "mB")):
        k = [i for i, g in enumerate(net.gaps) if g[0] == gname][0]
        g = list(net.gaps[k]); ni, nm = net.n(node), net.n(mid)
        g[1 if g[1] == ni else 2] = nm; net.gaps[k] = tuple(g)
        net.inds.append((f"L_{mid}", ni, nm, q["L_coil_H"] / n, q["R_coil"] / n, "lx"))
        net.caps.append((f"Cmid_{mid}", nm, PE.GND, n * q["C_mid_pF"] * 1e-12))
        net.caps.append((f"Cscreen_{mid}", nm, ni, n * q["C_screen_pF"] * 1e-12))
    m = RT.run(net, cfg, record=True)
    rec = m["rec"]
    s2 = (V_PEAK / np.abs(np.array([p["V"] for p in rec["points"]])).max()) ** 2
    by = {k: v * s2 for k, v in rec["by"].items()}
    W, dE, diss = rec["ledger"]["W"] * s2, (rec["E1"] - rec["E0"]) * s2, sum(by.values())
    f = CYC_PER_REV * RPM_REL / 60.0
    I2 = {mid: by[f"L_{mid}_R"] / (q["R_coil"] / n) for mid in ("mA", "mB")}
    return dict(cpar_mode=cpar_mode or "fixed", z=m["z"], converged=bool(m["converged"]), W_J=W, dE_J=dE, diss_J=diss,
                closure_J=W - dE - diss, diss_by_J=by, P_belt_W=W * f, P_loss_W=diss * f, P_surplus_W=dE * f,
                int_I2_A2s=I2, L_group_H=q["L_coil_H"] / n, f_cycles=f)


def motor(led):
    mag = {(r["r_u"], r["shaft"]): r for r in json.load(open(os.path.join(HERE, "tube_magnetic_results.json")))}
    r = mag[(130.0, "none / non-magnetic")]
    dP = r["aligned"] - r["between"]                               # mm, over 30 deg (aligned -> between)
    dPdth = 2.0 * dP / math.radians(30.0)                          # peak ~ 2x the mean slope [RH]
    dL = N_TURNS ** 2 * MU0_MM * dPdth                             # H/rad per coil
    om = 2 * math.pi * RPM_REL / 60.0
    I2 = sum(led["int_I2_A2s"].values())
    T = 0.5 * (dL / 6) * I2 * led["f_cycles"]                      # lumped group of 6 (cem_inductance.py convention)
    T_pulse = math.pi * math.sqrt(led["L_group_H"] * 1.1e-9)      # half-sine with ~C_max transfer [RH]
    E_coil = sum(0.5 * led["L_group_H"] * 2 * i2 / T_pulse for i2 in led["int_I2_A2s"].values())   # J per cycle, both sides
    ceil = E_coil * led["f_cycles"]
    return dict(swing=dP / r["aligned"], dL_dtheta_H_per_rad=dL, torque_direct_Nm=T, P_direct_W=T * om,
                pulse_us=T_pulse * 1e6, E_coil_per_cycle_J=E_coil, P_ceiling_W=ceil, T_ceiling_Nm=ceil / om,
                P_realistic_W=ceil * dP / r["aligned"], T_realistic_Nm=ceil * dP / r["aligned"] / om)


def drag():
    om_rel = 2 * math.pi * RPM_REL / 60.0
    om_s = 0.5 * om_rel                                            # symmetric split: stator at -150 rpm [OC]
    p = S.TUBE_DEFAULTS
    el = S.size_stack("tube")["tube_geometry"]["elements"]
    n_faces = 2 * sum(1 for e in el if e["kind"].endswith("vane") and e["body"] == "rotor")
    ri, ro, g = p["r_inMm"] * 1e-3, p["r_outMm"] * 1e-3, p["g_vMm"] * 1e-3
    T_face = 2 * math.pi * MU_AIR * om_rel / g * (ro ** 4 - ri ** 4) / 4     # laminar Couette, full annulus
    cover = (p["N_sec"] / 2) * p["wr_deg"] / 360.0
    T_shear = (n_faces * T_face * cover, n_faces * T_face)
    W_st = STATOR_KG * 9.81
    T_bear = 0.0015 * W_st * 0.5 * (S.BEARING["bore"] + S.BEARING["od"]) * 1e-3 / 2   # stator weight on rotor-stator bearings
    r_c, A, Cd = 0.235, 0.119 * 0.060, 1.2                         # C-EM centroid radius, frontal area, bluff body [RH]
    T_wind = 12 * 0.5 * RHO_AIR * (om_s * r_c) ** 2 * Cd * A * r_c
    lo = T_shear[0] + T_bear
    hi = T_shear[1] + T_bear + T_wind
    return dict(omega_rel=om_rel, omega_stator=om_s, rotor_vane_faces=n_faces, T_shear_Nm=T_shear, T_bearing_Nm=T_bear,
                T_windage_CEM_Nm=T_wind, T_need_vacuum_or_shell_Nm=lo, T_need_open_air_Nm=hi,
                P_need_W=(lo * om_s, hi * om_s), stator_kg=STATOR_KG)


def main():
    leds = [ledger(None), ledger("scaled")]
    mot = motor(leds[0]); dr = drag()
    for L in leds:
        print(f"strays {L['cpar_mode']:6s}: z {L['z']:.4f}; per cycle belt {L['W_J'] * 1e3:.1f} mJ = growth {L['dE_J'] * 1e3:.1f} "
              f"+ losses {L['diss_J'] * 1e3:.1f} (closure {L['closure_J']:.1e} J); at 300 rpm: belt {L['P_belt_W']:.2f} W, "
              f"losses {L['P_loss_W']:.2f} W, available {L['P_surplus_W']:.2f} W")
    print(f"motor: swing {mot['swing']:.3f}, direct {mot['torque_direct_Nm']:.1e} N m ({mot['P_direct_W']:.1e} W); freewheel "
          f"ceiling {mot['T_ceiling_Nm'] * 1e3:.1f} mN m ({mot['P_ceiling_W']:.3f} W); realistic {mot['T_realistic_Nm'] * 1e3:.2f} mN m")
    print(f"stator drag: shear {dr['T_shear_Nm'][0] * 1e3:.1f}-{dr['T_shear_Nm'][1] * 1e3:.1f}, bearings {dr['T_bearing_Nm'] * 1e3:.1f}, "
          f"C-EM windage {dr['T_windage_CEM_Nm'] * 1e3:.0f} mN m -> need {dr['T_need_vacuum_or_shell_Nm'] * 1e3:.0f} (no windage) "
          f"to {dr['T_need_open_air_Nm'] * 1e3:.0f} mN m (open air)")
    json.dump(dict(ledger=leds, motor=mot, drag=dr, rpm_rel=RPM_REL, v_peak=V_PEAK),
              open(os.path.join(HERE, "tube_ledger_results.json"), "w"), indent=1, default=float)


if __name__ == "__main__":
    main()
