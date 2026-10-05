#!/usr/bin/env python3
"""sim/timing_budget.py -- how much spark-gap timing error the v4 pump tolerates, and what that means in mm at a
given clocking radius.

Network: RT0 ladder (pump_synth sized) + v4: parallel tank (425 uH chain across R-A / R-B), C-EMs in series with
SG1 / SG2 (0.31 H lumped = one 1.85 H coil / 6, 7.3 ohm), mid node 1 pF + 57 pF screen per coil.     [IR]
One station at a time is shifted by d degrees (its arming edge; a load gap's disarm edge moves with its fire
station), the rest held: z(d). Tolerance = the |d| at which z falls to z_min.
Usage: python3 sim/timing_budget.py -> sim/timing_budget_results.json
"""
import json, math, os, sys
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path[:0] = [HERE, os.path.join(os.path.dirname(HERE), "reference")]
import pump_engine as PE, rt_engine as RT, pump_synth as SY

L1, R1 = 1.85, 44.0
STATIONS = ("SG1", "SG3a", "SG3b", "BS3", "SG2", "SG4a", "SG4b", "BS4")
EDGE = {  # station -> [(gap, which end)]
    "SG1": [("SG1", 0)], "SG3a": [("SG3a1", 0)], "SG3b": [("SG3a1", 1), ("SG3b1", 0)], "BS3": [("BS3", 0)],
    "SG2": [("SG2", 0)], "SG4a": [("SG4a1", 0)], "SG4b": [("SG4a1", 1), ("SG4b1", 0)], "BS4": [("BS4", 0)]}


def net_v4(cfg, shift=None):
    net = RT.build_net(cfg, tank="series", C_R1_pF=789.0)
    Rt = (1 / math.sqrt(425e-6 * 789e-12)) * 425e-6 / 30
    net.inds.append(("L_tank_chain", net.n("R-B"), PE.GND, 425e-6, Rt, "lx"))
    for gname, node, mid in (("SG1", "2", "mA"), ("SG2", "3", "mB")):
        k = [i for i, g in enumerate(net.gaps) if g[0] == gname][0]
        g = list(net.gaps[k]); ni, nm = net.n(node), net.n(mid)
        g[1 if g[1] == ni else 2] = nm; net.gaps[k] = tuple(g)
        net.inds.append((f"L_{mid}", ni, nm, L1 / 6, R1 / 6, "lx"))
        net.caps.append((f"Cg_{mid}", nm, PE.GND, 6e-12)); net.caps.append((f"Cw_{mid}", nm, ni, 6 * 57e-12))
    if shift:
        st, d = shift
        for gname, end in EDGE[st]:
            k = [i for i, g in enumerate(net.gaps) if g[0] == gname][0]
            g = list(net.gaps[k]); w = list(g[4]); w[end] += d; g[4] = tuple(w); net.gaps[k] = tuple(g)
    return net


def main(deltas=(-2.0, -1.0, -0.5, 0.5, 1.0, 2.0)):
    lad, fi = SY.sized({}); cfg = SY.engine_cfg(lad, fi)
    z0 = RT.run(net_v4(cfg), cfg)["z"]
    print("v4 ladder z0", round(z0, 4), flush=True)
    out = dict(z0=z0, rows={})
    for st in STATIONS:
        row = {}
        for d in deltas:
            m = RT.run(net_v4(cfg, (st, d)), cfg); row[d] = (m["z"], bool(m["converged"]))
        out["rows"][st] = row
        print(st, " ".join(f"{d:+.1f}:{v[0]:.4f}{'' if v[1] else '*'}" for d, v in row.items()), flush=True)
    json.dump(out, open(os.path.join(HERE, "timing_budget_results.json"), "w"), indent=1)


if __name__ == "__main__":
    main()
