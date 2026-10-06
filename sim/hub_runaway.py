"""sim/hub_runaway.py -- HYPOTHETICAL: invented hub-release laws that make the stator break even and run away.

A what-if built on the conservative engine results. The quadricone hub is given a release per switch E_sw(w_rel)
whose origin is NOT modelled [RH: premise]. Everything else is the machine as computed:
- per-cycle pump work W, surplus E_s and losses: sim/tube_ledger_results.json, scaled ~ V^2 to the voltage cap;
- the hub feeds the motor's DC link directly (onto the pump nodes it breaks SG1's firing above ~6.5 mJ per switch,
  sim/hub_battery.py alpha 5 -> 7);
- drag: bearings (constant), vane shear (~ w_rel), C-EM windage (~ w_s^2, 0 in a shell): sim/spinup_equilibrium.py;
- the reversed-VdG motor at eta 0.8.

Release law (invented): E_sw(w) = m * E_be(w0) * (w / w0)^n,  w0 = 300 rpm relative, with E_be the break-even release.
- n = 0: a fixed release per switch (the earlier spec at the cap);
- n > 0: the "quadricone gain" rising with rpm;
- m sets where it starts relative to break-even.

Stator: I_s dw_s/dt = T_net(w_rel), with the belt holding the rotor at 300 rpm. The run stops at the first mechanical
limit [RH]:
- the rotor-stator bearings' limiting speed (relative);
- the stator rim speed at the C-EM ring;
- the motor's top speed: its back-EMF reaches the link voltage (rewinding moves it; N ~ 1 / top speed).

Energy book per second along the run: belt + hub = pump losses + drag + stator kinetic-energy rate (+ motor loss).

Usage: python3 sim/hub_runaway.py   (writes sim/hub_runaway_results.json)
"""
import json
import math
import os

HERE = os.path.dirname(os.path.abspath(__file__))
TL = json.load(open(os.path.join(HERE, "tube_ledger_results.json")))
HB = json.load(open(os.path.join(HERE, "hub_battery_results.json")))

CYC = 6
G = CYC / (2 * math.pi)                         # cycles per radian
ETA = 0.8
RPM_BELT = 300.0
W0 = 2 * math.pi * 300.0 / 60
# stator inertia from the STEP solids [RH: lumped radii]: C-EM cores + coils 20 kg at r ~0.20 m, Al vanes/plates 11.8 kg
# over r 50-150 mm, G10 cage/spiders/rings 17.7 kg at r ~0.16 m, W-Cu spheres 2 kg at r 0.125 m
I_STATOR = 20.0 * 0.20 ** 2 + 11.8 * (0.05 ** 2 + 0.15 ** 2) / 2 + 17.7 * 0.16 ** 2 + 2.0 * 0.125 ** 2
RPM_BEARING_LIM = 11000.0                       # 6205-class sealed, relative speed [RH]
RPM_MOTOR_TOP = 3000.0                          # reversed-VdG winding chosen so back-EMF = link at this relative speed [IR]
E_CAL_MAX = 10.0                                # x the largest calibrated release (alpha 3): beyond it the split is extrapolated
V_RIM_LIM = 100.0                               # m/s at the C-EM ring r 0.265 m (G10 cage, bonded C-EMs) [RH]
R_RIM = 0.265
CAPS = {"air 10.9 kV": 10.9e3, "20 kV (gas / vacuum)": 20e3}


def machine(V):
    s = (V / 20e3) ** 2
    L0 = TL["ledger"][0]; f = L0["f_cycles"]
    W, Es, Lo = L0["W_J"] * s, L0["dE_J"] * s, L0["diss_J"] * s
    a0 = [r for r in HB["rows"] if r["alpha"] == 0.0][0]; a3 = [r for r in HB["rows"] if r["alpha"] == 3.0][0]
    ext = a3["P_ext_W"] / f
    node_split = dict(to_surplus=(a3["P_surplus_W"] - a0["P_surplus_W"]) / f / ext,
                      to_belt=(a3["P_belt_W"] - a0["P_belt_W"]) / f / ext,
                      to_loss=(a3["P_loss_W"] - a0["P_loss_W"]) / f / ext)
    # the hub feeds the motor's DC link directly: all of it reaches the link, none touches the pump's firing.
    # (Feeding it onto the pump nodes, as in hub_battery.py, stops SG1 firing above ~6.5 mJ per switch at 20 kV,
    # alpha 5 -> 7: z 2.16 -> 0.88 -- below every break-even here.)
    split = dict(to_surplus=1.0, to_belt=0.0, to_loss=0.0)
    d = TL["drag"]
    drag = dict(T_b=d["T_bearing_Nm"], k=d["T_shear_Nm"][0] / d["omega_rel"],
                c=d["T_windage_CEM_Nm"] / d["omega_stator"] ** 2)
    return dict(W=W, Es=Es, L=Lo, split=split, node_split=node_split, drag=drag, E_cal_sw=ext * s / 2)


def t_net(M, w_rel, w_s, E_cyc_hub, cw):
    """net torque on the stator (+ = counter-rotating) and its parts."""
    Es = M["Es"] + M["split"]["to_surplus"] * E_cyc_hub
    W = M["W"] + M["split"]["to_belt"] * E_cyc_hub
    Tm, Tp = ETA * Es * G, W * G
    Td = M["drag"]["T_b"] + M["drag"]["k"] * w_rel + cw * w_s ** 2
    return Tm - Tp - Td, dict(T_motor=Tm, T_pump=Tp, T_drag=Td, W=W, Es=Es)


def breakeven(M, w_rel, w_s, cw):
    """hub energy per cycle that zeroes T_net (linear in E_cyc_hub)."""
    t0, _ = t_net(M, w_rel, w_s, 0.0, cw)
    t1, _ = t_net(M, w_rel, w_s, 1.0, cw)
    return -t0 / (t1 - t0)


def run(M, m, n, cw, t_end=3600.0, dt=0.05):
    wr = 2 * math.pi * RPM_BELT / 60
    Ebe0 = breakeven(M, W0, W0 - wr, cw)               # at 300 rpm relative = stator standing (rotor at 300)
    law = lambda w: m * Ebe0 * (w / W0) ** n
    ws, t, rows, stop = 0.0, 0.0, [], "t_end (1 h)"
    E_cal = M["E_cal_sw"] * E_CAL_MAX; t_extrap = None
    while t < t_end:
        w = wr + ws
        Eh = law(w)
        T, parts = t_net(M, w, ws, Eh, cw)
        if ws <= 0 and T <= 0:
            stop = "held: net torque <= 0 at standstill"; break
        if t_extrap is None and Eh / 2 > E_cal:
            t_extrap = t
        if len(rows) == 0 or t - rows[-1]["t"] >= 5.0:
            P_hub = Eh * w * G
            rows.append(dict(t=t, rpm_stator=ws * 60 / (2 * math.pi), rpm_rel=w * 60 / (2 * math.pi), T_net_mNm=T * 1e3,
                             P_hub_W=P_hub, P_belt_W=parts["W"] * G * wr, P_motor_W=parts["T_motor"] * w,
                             P_drag_W=parts["T_drag"] * w, E_sw_mJ=Eh / 2 * 1e3))
        if w * 60 / (2 * math.pi) >= RPM_BEARING_LIM:
            stop = f"bearing limit {RPM_BEARING_LIM:.0f} rpm relative"; break
        if ws * R_RIM >= V_RIM_LIM:
            stop = f"stator rim {V_RIM_LIM:.0f} m/s ({V_RIM_LIM / R_RIM * 60 / (2 * math.pi):.0f} rpm)"; break
        if w * 60 / (2 * math.pi) >= RPM_MOTOR_TOP:
            stop = f"motor top speed {RPM_MOTOR_TOP:.0f} rpm relative (back-EMF = link)"; break
        if len(rows) > 13 and abs(rows[-1]["rpm_stator"] - rows[-13]["rpm_stator"]) < 0.05:
            stop = "settled"; break
        ws = max(0.0, ws + T / I_STATOR * dt); t += dt
    return dict(m=m, n=n, E_be_300_mJ_per_switch=Ebe0 / 2 * 1e3, stop=stop, t_stop=t, rows=rows, t_extrapolated=t_extrap,
                final=rows[-1] if rows else None)


def main():
    out = dict(premise="HYPOTHETICAL hub release per switch E_sw = m E_be(300 rpm) (w/w0)^n; origin not modelled",
               I_stator=I_STATOR, eta=ETA, runs=[])
    print(f"stator inertia {I_STATOR:.2f} kg m^2 [RH]")
    for tag, V in CAPS.items():
        M = machine(V)
        print(f"\n{tag}: pump work {M['W'] * 1e3:.0f} mJ/cycle, surplus {M['Es'] * 1e3:.0f}; hub feeds the DC link directly")
        for enc, cw in (("shell/vacuum", 0.0), ("open air", M["drag"]["c"])):
            # the release exponent n* above which break-even is unstable (runaway): compare d ln E_be / d ln w at 300 rpm
            wr = W0; e1 = breakeven(M, W0, 0.0, cw); e2 = breakeven(M, W0 * 1.01, W0 * 0.01, cw)
            n_star = math.log(e2 / e1) / math.log(1.01)
            print(f"  {enc}: break-even {e1 / 2 * 1e3:.0f} mJ per switch at 300 rpm ({e1 * W0 * G:.2f} W); "
                  f"runaway needs the release to rise faster than rpm^{n_star:.2f} there")
            for m, n in ((0.9, 0.0), (1.1, 0.0), (1.1, 1.0), (1.1, 2.0), (1.5, 2.0), (1.1, 3.0)):
                r = run(M, m, n, cw)
                r.update(cap=tag, enclosure=enc, n_star=n_star)
                out["runs"].append(r)
                f_ = r["final"]
                if f_ is None:
                    print(f"    m {m} n {n}: {r['stop']}")
                    continue
                print(f"    m {m} n {n}: {r['stop']} at t {r['t_stop']:.1f} s -> stator {f_['rpm_stator']:.0f} rpm, rel "
                      f"{f_['rpm_rel']:.0f} rpm, hub {f_['P_hub_W']:.1f} W ({f_['E_sw_mJ']:.0f} mJ/switch), belt {f_['P_belt_W']:.1f} W, "
                      f"drag {f_['P_drag_W']:.1f} W")
    json.dump(out, open(os.path.join(HERE, "hub_runaway_results.json"), "w"), indent=1, default=float)


if __name__ == "__main__":
    main()
