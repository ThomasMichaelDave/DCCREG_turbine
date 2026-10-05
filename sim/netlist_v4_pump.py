"""Pump check for KiCad netlist v4 (DCCREG_Turbine_circuit_v4).

v4 wiring (from the PDF, the .net export carries no spark-gap pins):
  2 -> L_Ak -> mA_k -> SG1-k -> R-A   (k = 1..6)
  3 -> L_Bk -> mB_k -> SG2-k -> R-B
  C_R1 across R-A / R-B, chain L_R1-L_AH1-L_AH2-L_R2 across it (parallel tank).

Each C-EM gets its own gap and mid node: the RT0 rail gap SG1/SG2 is split into six
identical gaps [IR] (all six fire at the same station angle -- six rotor electrodes
at 60 deg pitch [OC]). Coil L is held constant; the L(theta) torque model is not in. [OC]
Probe convention: R-A = ground (rt_engine).
"""
import sys, math, json
sys.path[:0] = ['sim', 'reference']
import pump_engine as PE, rt_engine as RT, pump_synth as SY

GND = PE.GND
lad, fi = SY.sized({}); cfg = SY.engine_cfg(lad, fi)
L1, R1 = 0.64, 40.0                     # one C-EM coil (register value) [RH]
L_tank, C_R = 425e-6, 789.0             # RA tank, Q 30 [RH]
R_tank = 2*math.pi/(2*math.pi*math.sqrt(L_tank*C_R*1e-12))*L_tank/30


def build(C_node_pF, C_across_pF=0.0, lumped=False):
    net = RT.build_net(cfg, tank="series", C_R1_pF=C_R)
    net.inds.append(("L_tank_chain", net.n("R-B"), GND, L_tank, R_tank, "lx"))
    for gname, node, side in (("SG1", "2", "A"), ("SG2", "3", "B")):
        k = [i for i, g in enumerate(net.gaps) if g[0] == gname][0]
        g0 = list(net.gaps.pop(k)); ni = net.n(node)
        j = 1 if g0[1] == ni else 2
        assert g0[j] == ni, (gname, g0[:3])
        n_coils, L, R = (1, L1/6, R1/6) if lumped else (6, L1, R1)
        for c in range(1, n_coils + 1):
            nm = net.n(f"m{side}{c}")
            g = list(g0); g[0] = f"{gname}-{c}"; g[j] = nm
            net.gaps.append(tuple(g))
            net.inds.append((f"L_{side}{c}", ni, nm, L, R, "lx"))
            Cn = C_node_pF * (6 if lumped else 1)
            if Cn: net.caps.append((f"Cg_{side}{c}", nm, GND, Cn*1e-12))
            if C_across_pF: net.caps.append((f"Cw_{side}{c}", nm, ni, C_across_pF*1e-12))
    return net


if __name__ == "__main__":
    z0 = RT.run(RT.build_net(cfg), cfg)['z']
    out = {"RT0_anchor": z0, "cases": []}
    print("RT0 anchor", round(z0, 7))
    cases = [dict(C_node_pF=c) for c in (0.5, 1, 2, 3.3, 5, 10)] + \
            [dict(C_node_pF=1, C_across_pF=50), dict(C_node_pF=1, lumped=True)]
    for kw in cases:
        m = RT.run(build(**kw), cfg)
        row = dict(kw, z=m['z'], converged=bool(m['converged']))
        out["cases"].append(row); print(row, flush=True)
    json.dump(out, open("sim/netlist_v4_pump_results.json", "w"), indent=1)
