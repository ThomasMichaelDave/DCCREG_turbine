"""sim/goldie_tube.py -- the Goldie (US 3,013,201) floating-rotor, two-section generator on the tube's capacitances, with
(a) ideal diodes (the patent) and (b) spark gaps, run in the exact engine (pump_engine Sim + monodromy).

Section A (negative output on node "1") and section B (positive output on node "4"):
    induction plate I --C(th)/2-- floating rotor R --C(th)/2-- collector S;  R --Cr-- ground;  S --Cs-- ground
    charge switch S <-> ground (patent rectifier 16), dump switch S <-> load (rectifier 17); load cap C_L to ground.
    Cross-feed: I_A is the B load (k = 1) or a capacitive tap on it (k < 1); I_B likewise on the A load.
C(th) = the tube varicap per side (stack_sizing: 1114 / 71.2 pF) with a cosine schedule, 60 deg period.

Switch models (engine kinds):
- 'rect': ideal one-way valve, closes at zero voltage across it -- the patent's rectifiers [OC];
- 'arc' in an angle window: a timed spark gap with the engine's default zero strike threshold (M-RD -> 0). It conducts
  both ways while armed and closes on whatever voltage is across it, booking the two-capacitor loss [OC]. A real gap
  also needs ~1-3 kV to strike: an extra loss and charge offset, NOT in these numbers [RH].

Usage: python3 sim/goldie_tube.py   (writes sim/goldie_tube_results.json)
"""
import json
import math
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import pump_engine as PE                                  # noqa: E402

CMAX, CMIN = 1114.07e-12, 71.2e-12          # tube C1 per side (stack_sizing defaults)
CS = 28e-12                                 # collector stray + switch capacitance [RH]
CL = 2e-9                                   # load / reservoir cap per section [IR]
RPM = 300.0


def C_of(th, phase=0.0):
    return CMIN + (CMAX - CMIN) * 0.5 * (1 + math.cos(2 * math.pi * (th - phase) / 60.0))


def params():
    return dict(model="valve", I_hold=0.0, t_rec=0.0, holdoff=0.0)


def build(switch="rect", k=1.0, Cr=0.0, phase_B=0.0, w_charge=(-10.0, 10.0), w_dump=(20.0, 40.0)):
    net = PE.Net()
    LA, LB = net.n("1"), net.n("4")
    G = PE.GND
    for sec, L_own, L_other, ph in (("A", LA, LB, 0.0), ("B", LB, LA, phase_B)):
        I, R, S = net.n(f"I{sec}"), net.n(f"R{sec}"), net.n(f"S{sec}")
        half = (lambda p: (lambda th: 0.5 * C_of(th, p)))(ph)
        net.caps += [(f"Cir{sec}", I, R, half), (f"Crs{sec}", R, S, half), (f"Cs{sec}", S, G, CS),
                     (f"CL{sec}", L_own, G, CL)]
        if Cr > 0:
            net.caps.append((f"Cr{sec}", R, G, Cr))
        # cross-feed divider: I tied to the other load through C_top, to ground through C_bot (k = C_top / sum)
        if k >= 1.0:
            net.caps.append((f"Cfb{sec}", I, L_other, 1e-6))          # stiff tie (k = 1)
        else:
            Ct = 20e-9
            net.caps += [(f"Cfb{sec}", I, L_other, Ct), (f"Cfg{sec}", I, G, Ct * (1 - k) / k)]
        # A negative: charge S -> ground (anode S), dump load -> S (anode load). B positive: mirrored.
        if sec == "A":
            chg, dmp = (S, G), (L_own, S)
        else:
            chg, dmp = (G, S), (S, L_own)
        if switch == "rect":
            net.gaps += [(f"D1{sec}", *chg, "rect", (0.0, 60.0), "load", params()),
                         (f"D2{sec}", *dmp, "rect", (0.0, 60.0), "fire", params())]
        else:
            wc = ((w_charge[0] + ph) % 60.0, (w_charge[1] + ph) % 60.0)
            wd = ((w_dump[0] + ph) % 60.0, (w_dump[1] + ph) % 60.0)
            net.gaps += [(f"G1{sec}", *chg, "arc", wc, "load", params()),
                         (f"G2{sec}", *dmp, "arc", wd, "fire", params())]
    net.meta = dict(motor=False, lx=0.0, galvanic=False, topology="goldie")
    return net


def run(net):
    cfg = PE.make_config(dict(rpm=RPM))
    sim = PE.Sim(net, mode="qs", dth=cfg["dth"], record_events=False, arming=cfg["arming"], rpm=RPM)
    PE.seed(sim, -1.0)
    m = PE.monodromy(net, cfg, sim=sim, record=True)
    rec = m["rec"]
    V = np.array([p["V"] for p in rec["points"]])
    s2 = (20e3 / np.abs(V).max()) ** 2
    W, dE, diss = rec["ledger"]["W"] * s2, (rec["E1"] - rec["E0"]) * s2, sum(rec["by"].values()) * s2
    f = 6 * RPM / 60.0
    vA, vB = V[:, net.idx["1"]], V[:, net.idx["4"]]
    return dict(z=m["z"], converged=bool(m["converged"]), W_mJ=W * 1e3, growth_mJ=dE * 1e3, loss_mJ=diss * 1e3,
                closure_J=W - dE - diss, P_belt_W=W * f, P_surplus_W=dE * f, P_loss_W=diss * f,
                eta=dE / W if W > 0 else None, VA_sign=float(np.sign(vA[np.argmax(np.abs(vA))])),
                VB_sign=float(np.sign(vB[np.argmax(np.abs(vB))])))


def main():
    out = dict(rows=[])
    cases = [("diodes, k 1", dict(switch="rect", k=1.0)),
             ("diodes, k 1, rotor stray 50 pF", dict(switch="rect", k=1.0, Cr=50e-12)),
             ("diodes, k 0.5", dict(switch="rect", k=0.5)),
             ("diodes, k 0.15 (below threshold)", dict(switch="rect", k=0.15))]
    for wc in ((-10.0, 10.0), (-5.0, 5.0), (-15.0, 15.0)):
        for wd in ((25.0, 35.0), (20.0, 40.0), (28.0, 32.0), (30.0, 45.0)):
            cases.append((f"spark gaps, k 1, charge {wc}, dump {wd}", dict(switch="arc", k=1.0, w_charge=wc, w_dump=wd)))
    for tag, kw in cases:
        try:
            r = run(build(**kw))
        except Exception as e:                       # noqa: BLE001
            r = dict(error=str(e)[:200])
        r.update(case=tag)
        out["rows"].append(r)
        if "error" in r:
            print(f"{tag:55s}: ERROR {r['error']}", flush=True)
            continue
        print(f"{tag:55s}: z {r['z']:.4f} ({'conv' if r['converged'] else 'NOT conv'}) | per cycle at 20 kV: belt "
              f"{r['W_mJ']:6.2f} mJ, growth {r['growth_mJ']:6.2f}, loss {r['loss_mJ']:6.2f} (closure {r['closure_J']:.0e}) | "
              f"surplus {r['P_surplus_W']:.2f} W, eta {r['eta'] if r['eta'] is None else round(r['eta'], 3)}", flush=True)
    json.dump(out, open(os.path.join(HERE, "goldie_tube_results.json"), "w"), indent=1, default=float)


if __name__ == "__main__":
    main()
