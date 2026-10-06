"""sim/spinup_equilibrium.py -- can the stator counter-rotate, and does it run away with rpm?

Torques on the free stator (belt holds the rotor at w_r; stator counter-rotates at w_s; w_rel = w_r + w_s):
  + T_m    motor torque from the link: eta * E_s * cycles_per_rev / (2 pi), E_s = pump surplus per cycle (+ hub share)
  - T_p    the PUMP'S OWN reaction torque: the belt work per cycle W is taken from the rotor-stator relative motion, so
           the stator is dragged along by T_p = W * cycles_per_rev / (2 pi) [OC]
  - T_bear rotor-stator bearings (constant) [RH]
  - k w_rel  vane air shear (laminar Couette) [RH]
  - c w_s^2  C-EM windage on the stator (0 in a shell or vacuum) [RH]
Every energy here is PER CYCLE and does not depend on speed (quasi-static engine) [IR], so T_m and T_p do not grow with
rpm: power does, torque does not. Without a hub source E_s < W, hence T_m < T_p always: the stator is dragged WITH the
rotor whatever the motor.

The hub (hypothetical, sim/hub_battery.py) adds E_ext per cycle. Break-even E_ext: eta (W + E_ext - L) - W = drag per cycle
(E_s = W + E_ext - L, L = losses), solved for E_ext at each relative speed. Voltage caps: per-cycle energies ~ V^2.

Usage: python3 sim/spinup_equilibrium.py   (writes sim/spinup_equilibrium_results.json)
"""
import json
import math
import os

HERE = os.path.dirname(os.path.abspath(__file__))
TL = json.load(open(os.path.join(HERE, "tube_ledger_results.json")))
HB = json.load(open(os.path.join(HERE, "hub_battery_results.json")))
CYC_PER_REV, V_REF = 6, 20e3
D_CM = 0.3
V_AIR = (24.4 * D_CM + 6.53 * math.sqrt(D_CM)) * 1e3          # uniform-field air breakdown at 3 mm, 1 atm [OC]: ~10.9 kV
V_CAPS = {"air 3 mm": V_AIR, "20 kV": 20e3, "SF6-class ~30 kV": 30e3}
ETA = (0.5, 0.8)
RPM_REL = (300.0, 600.0, 1200.0, 2400.0)


def main():
    d = TL["drag"]; L0 = TL["ledger"][0]
    w_ref = d["omega_rel"]; f_ref = L0["f_cycles"]
    T_b = d["T_bearing_Nm"]
    k_sh = d["T_shear_Nm"][0] / w_ref                                # sector-covered (low) shear
    c_w = d["T_windage_CEM_Nm"] / d["omega_stator"] ** 2
    g = CYC_PER_REV / (2 * math.pi)                                  # cycles per radian
    out = dict(V_air_3mm=V_AIR, T_bear_Nm=T_b, k_shear_Nms=k_sh, c_wind_Nms2=c_w, net=[], breakeven=[])
    # 1. net stator torque at standstill of the stator (w_s = 0, w_rel = w_r = 300 rpm), with the hub rows
    for r in HB["rows"]:
        W20, L20, S20 = r["P_belt_W"] / f_ref, r["P_loss_W"] / f_ref, r["P_surplus_W"] / f_ref
        for tag, V in V_CAPS.items():
            s = (V / V_REF) ** 2
            for eta in ETA:
                Tm, Tp = eta * S20 * s * g, W20 * s * g
                net = Tm - Tp - T_b - k_sh * w_ref
                out["net"].append(dict(alpha=r["alpha"], cap=tag, eta=eta, T_motor_mNm=Tm * 1e3, T_pump_mNm=Tp * 1e3,
                                       T_net_mNm=net * 1e3, P_ext_W=r["P_ext_W"] * s))
    # 2. break-even hub energy per cycle (per A+B switch pair) vs relative speed, symmetric split w_s = w_rel / 2
    W20, L20 = L0["W_J"], L0["diss_J"]
    for tag, V in V_CAPS.items():
        s = (V / V_REF) ** 2
        for eta in ETA:
            for enc, cw in (("shell/vacuum", 0.0), ("open air", c_w)):
                for rpm in RPM_REL:
                    w = 2 * math.pi * rpm / 60; ws = w / 2
                    drag_cyc = (T_b + k_sh * w + cw * ws ** 2) / g          # J per cycle
                    Ex = ((1 - eta) * W20 * s + drag_cyc) / eta + L20 * s
                    out["breakeven"].append(dict(cap=tag, eta=eta, enclosure=enc, rpm_rel=rpm, E_ext_per_cycle_J=Ex,
                                                 E_ext_per_switch_J=Ex / 2, P_ext_W=Ex * rpm / 60 * CYC_PER_REV,
                                                 drag_per_cycle_J=drag_cyc, W_per_cycle_J=W20 * s))
    json.dump(out, open(os.path.join(HERE, "spinup_equilibrium_results.json"), "w"), indent=1, default=float)
    print(f"air breakdown at 3 mm: {V_AIR / 1e3:.1f} kV")
    print("net torque on a standing stator at 300 rpm relative (+ = counter-rotates):")
    for n in out["net"]:
        if n["alpha"] in (0.0, 3.0):
            print(f"  alpha {n['alpha']:<3g} {n['cap']:16s} eta {n['eta']}: motor {n['T_motor_mNm']:5.1f} - pump {n['T_pump_mNm']:5.1f} "
                  f"- drag = {n['T_net_mNm']:6.1f} mN m  (hub {n['P_ext_W']:.2f} W)")
    print("break-even hub energy (symmetric split):")
    for b in out["breakeven"]:
        if b["eta"] == 0.8:
            print(f"  {b['cap']:16s} {b['enclosure']:12s} rel {b['rpm_rel']:5.0f} rpm: {b['E_ext_per_switch_J'] * 1e3:7.1f} mJ per switch, "
                  f"{b['P_ext_W']:7.2f} W  (pump work {b['W_per_cycle_J'] * 1e3:.0f} mJ/cycle, drag {b['drag_per_cycle_J'] * 1e3:.0f} mJ/cycle)")


if __name__ == "__main__":
    main()
