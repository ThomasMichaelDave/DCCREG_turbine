"""sim/hub_battery.py -- HYPOTHETICAL: the quadricone hub as an energy source (a "battery"), and its downstream
consequences for the tube machine and the stator drive.

THIS IS A WHAT-IF, NOT A PHYSICS CLAIM. The hub here is given an input of energy whose origin is deliberately not
modelled (the designer's premise). The engine stays conservative: the source is booked as its own ledger term "ext",
so belt + ext = growth of stored energy + losses closes to round-off, and every downstream number traces to that one
assumption. [RH: premise]

Model (the designer's spec, 2026-10-06):
- The release fires at each switch: SG1 (A side) and SG2 (B side).
- At a switch the hub releases dq = alpha * C_ii * V_i into the node it feeds (C_ii its self-capacitance, V_i its voltage
  at that instant): the release grows with the pump's voltage and always adds energy. In the engine, rotor half A (node 5) is the
  reference and R-B (node 6) carries the state. A release of +alpha * q_RB moves charge 5 -> 6 or 6 -> 5 depending on
  the sign of q_RB at that switch; the direction per side is reported.
- The release starts only once the pump has reached V_ON (10 kV). The engine is scale-free, so the threshold enters the
  build-up trajectory (cycle by cycle) rather than the eigen-state.

Usage: python3 sim/hub_battery.py [alpha ...]   (writes sim/hub_battery_results.json)
"""
import json
import math
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import tube_ledger as TL                                  # noqa: E402
import pump_engine as PE                                  # noqa: E402

V_ON = 10e3                  # V, the hub starts releasing at this pump voltage [designer]
V_SEED = 100.0               # V, build-up seed (any small value; growth is geometric)
ALPHAS = (0.0, 0.01, 0.03, 0.1, 0.3, 1.0, 3.0)
SWITCH_GAPS = {"SG1": "A", "SG2": "B"}


class HubSim(PE.Sim):
    """pump_engine.Sim with the hypothetical hub release at each SG1 / SG2 switch (tape-consistent, ledger-booked)."""

    def __init__(self, *a, alpha=0.0, variant="series", **k):
        super().__init__(*a, **k)
        self.alpha, self.variant = alpha, variant
        self.ledger["ext"] = 0.0
        self.releases = []

    def fire(self, th, K, new_closed, Snames, held, base_fixed, new_arcs, Mq, vf, lam, S):
        ev = super().fire(th, K, new_closed, Snames, held, base_fixed, new_arcs, Mq, vf, lam, S)
        sides = [SWITCH_GAPS[n] for n in new_closed if n in SWITCH_GAPS]
        if self.alpha > 0 and sides:
            if self.variant == "rail56":                              # literal: between rotor halves 5 and 6
                i = self.net.idx["R-B"]
                into = lambda d: "node 6 (R-B)" if d > 0 else "node 5 (R-A)"
            else:                                                       # in series with the firing switch
                i = self.net.idx["2" if sides[0] == "A" else "3"]
                into = lambda d: (f"node {'2' if sides[0] == 'A' else '3'} from rail {'5' if sides[0] == 'A' else '6'}")
            E0 = self.energy()
            Kth = self.Kof(self.th)
            Vmat, _ = self.alg.solver(self.kkey(self.th), Kth, self._edges_now(self.th, True))
            # dq_i = alpha * C_ii * V_i: grows with the pump's voltage, always adds energy (dE ~ alpha C_ii V_i^2)
            J = np.eye(self.N); J[i, :] += self.alpha * Kth[i, i] * Vmat[i, :]
            dq = float((J @ self.q - self.q)[i])
            self._tq(J)
            dE = self.energy() - E0
            self.ledger["ext"] += dE
            self.releases.append(dict(th=float(self.phase(th)), side=sides[0], dq=float(dq), dE=float(dE),
                                      into=into(dq)))
        return ev


def run(alpha, cpar_mode=None, variant="series"):
    net_q = TL.tube_v4_net(cpar_mode)
    net, cfg, q = net_q
    sim = HubSim(net, mode="qs", dth=cfg["dth"], record_events=True, arming=cfg["arming"], rpm=cfg["rpm"], alpha=alpha,
                 variant=variant)
    PE.seed(sim, -1.0)
    m = PE.monodromy(net, cfg, sim=sim, record=True)
    L = TL.ledger(cpar_mode, m=m, net_q=net_q)
    # releases of the last (eigen-state) cycle, scaled like the ledger (charge by s, energy by s^2)
    rec = m["rec"]
    s = TL.V_PEAK / np.abs(np.array([p["V"] for p in rec["points"]])).max()
    last = sim.releases[-2:] if alpha > 0 else []
    L["releases"] = [dict(r, dq_uC=r["dq"] * s * 1e6, dE_mJ=r["dE"] * s * s * 1e3) for r in last]
    return L


def buildup(z_off, z_on, f_cyc):
    """cycles / seconds from V_SEED to V_ON (pump alone) and V_ON -> 20 kV (pump + hub)."""
    n1 = math.log(V_ON / V_SEED) / math.log(z_off) if z_off > 1 else float("inf")
    n2 = math.log(TL.V_PEAK / V_ON) / math.log(z_on) if z_on > 1 else float("inf")
    return dict(cycles_to_V_on=n1, cycles_V_on_to_20kV=n2, seconds_total=(n1 + n2) / f_cyc,
                seconds_V_on_to_20kV=n2 / f_cyc)


def drives(L, om, T_need):
    """downstream: the as-built pulse C-EMs (direct + freewheel ceiling) and the reversed-VdG motor."""
    mot = TL.motor(L)
    P_av = L["P_surplus_W"]
    rows = dict(T_cem_direct_mNm=mot["torque_direct_Nm"] * 1e3, T_cem_ceiling_mNm=mot["T_ceiling_Nm"] * 1e3,
                T_cem_realistic_mNm=mot["T_realistic_Nm"] * 1e3,
                T_rvdg_mNm=(0.5 * P_av / om * 1e3, 0.8 * P_av / om * 1e3))
    for tag, T in (("shell", T_need[0]), ("open_air", T_need[1])):
        rows[f"cem_closes_{tag}"] = bool(mot["T_ceiling_Nm"] >= T)
        rows[f"rvdg_closes_{tag}"] = bool(0.5 * P_av / om >= T)
    return rows


def main():
    alphas = [float(a) for a in sys.argv[1:]] or list(ALPHAS)
    dr = TL.drag(); om = dr["omega_rel"]
    T_need = (dr["T_need_vacuum_or_shell_Nm"], dr["T_need_open_air_Nm"])
    base = None
    out = dict(premise="HYPOTHETICAL hub source; origin not modelled; booked as ledger term ext", V_on=V_ON,
               T_need_Nm=T_need, rows=[])
    lit = run(0.1, variant="rail56")
    out["literal_rail56_alpha0.1"] = dict(z=lit["z"], P_ext_W=lit["P_ext_W"], closure_J=lit["closure_J"])
    print(f"literal (between rotor halves 5 and 6), alpha 0.1: z {lit['z']:.4f}, hub {lit['P_ext_W']:.4f} W -- shorted by the "
          "central coil at the pump rate", flush=True)
    for a in alphas:
        L = run(a)
        if base is None:
            base = L
        b = buildup(base["z"], L["z"], L["f_cycles"])
        d = drives(L, om, T_need)
        row = dict(alpha=a, z=L["z"], converged=L["converged"], closure_J=L["closure_J"], P_belt_W=L["P_belt_W"],
                   P_ext_W=L["P_ext_W"], P_loss_W=L["P_loss_W"], P_surplus_W=L["P_surplus_W"], int_I2=L["int_I2_A2s"],
                   releases=L["releases"], **b, **d)
        out["rows"].append(row)
        print(f"alpha {a:<6g}: z {L['z']:.4f} ({'conv' if L['converged'] else 'NOT conv'}), closure {L['closure_J']:.1e} J | "
              f"belt {L['P_belt_W']:.2f} W + hub {L['P_ext_W']:.3f} W = losses {L['P_loss_W']:.2f} W + surplus "
              f"{L['P_surplus_W']:.2f} W | 10->20 kV in {b['seconds_V_on_to_20kV']:.2f} s | C-EM ceiling "
              f"{d['T_cem_ceiling_mNm']:.2f} mN m, rVdG {d['T_rvdg_mNm'][0]:.0f}-{d['T_rvdg_mNm'][1]:.0f} mN m "
              f"(need {T_need[0] * 1e3:.0f} / {T_need[1] * 1e3:.0f})", flush=True)
        for r in L["releases"]:
            print(f"      release at {r['side']}: {r['dq_uC']:+.3f} uC into {r['into']}, {r['dE_mJ']:.2f} mJ")
    json.dump(out, open(os.path.join(HERE, "hub_battery_results.json"), "w"), indent=1, default=float)


if __name__ == "__main__":
    main()
