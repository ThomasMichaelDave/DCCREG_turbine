#!/usr/bin/env python3
"""sim/shaft_bearings.py -- where the bearings go on the vertical tube shaft, and how thick the shaft must be.

Model (classic rotordynamics, small amplitude) [OC law / IR inputs]:
  * Euler-Bernoulli beam FE along z (2 dof / node: w, theta), consistent mass for the shaft, the rotor parts as lumped
    masses at their z (from stack_sizing.layout: rotor vanes, clocking discs + tips, utrons + hub rings, sleeve, hub);
  * bearings: radial springs k_b (rolling bearing, 2e8 N/m) at the chosen z, no moment stiffness;
  * the central hub: the shaft is SPLIT there and the bicone couples the halves [OC: TMD]. Two bounds:
    'rigid' (the bicone flange-to-flange joint transmits moment) and 'hinge' (it does not);
  * criteria: first bending (critical) frequency f1 >= 3 x the top speed (3000 rpm -> 150 Hz); deflection under a
    1 g lateral load (rotor mass + shaft) <= 0.05 mm (the 3 mm vane gap keeps > 98 %); bearing loads reported.
Usage: python3 sim/shaft_bearings.py -> sim/shaft_bearings_results.json
"""
import json
import math
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path[:0] = [HERE]
import stack_sizing as S                                 # noqa: E402

E_STEEL, RHO_STEEL = 210e9, 7850.0
RHO = {"Al vane": 2700.0, "G10": 1850.0, "WCu": 15000.0, "lam": 7650.0, "Cu": 8900.0, "glass": 2500.0}
K_BEARING = 2e8                                          # N/m, radial, deep-groove / angular-contact class [RH]
RPM_MAX = 3000.0
UTRON_CORE_MM3, UTRON_COIL_MM3 = 71917.0, 2 * 3295.0     # sim/motor_geometry pieces


def rotor_masses(lad):
    """[(z_mm, kg, what)] for every rotor part, plus the sleeve as a distributed mass (kg/m)."""
    p, el = lad["tube"], lad["tube_geometry"]["elements"]
    per = []
    ri, ro, t = p["r_inMm"], p["r_outMm"], p["t_vaneMm"]
    frac = (p["N_sec"] / 2) * p["wr_deg"] / 360.0
    A_vane = frac * math.pi * (ro ** 2 - ri ** 2) + math.pi * (ri ** 2 - S.SLEEVE_R ** 2)     # sectors + inner ring, mm^2
    for e in el:
        zc = 0.5 * (e["z0"] + e["z1"])
        if e["body"] != "rotor":
            continue
        k = e["kind"]
        if k.endswith("vane"):
            per.append((zc, A_vane * t * 1e-9 * RHO["Al vane"], k))
        elif k == "clk rotor disc":
            per.append((zc, math.pi * (e["r1"] ** 2 - e["r0"] ** 2) * (e["z1"] - e["z0"]) * 1e-9 * RHO["G10"], k))
        elif k == "clk tip":
            per.append((e["zc"], 6 * (4 / 3) * math.pi * e["R"] ** 3 * 1e-9 * RHO["WCu"], k))
        elif k == "utron":
            per.append((e["zc"], 3 * (UTRON_CORE_MM3 * RHO["lam"] + UTRON_COIL_MM3 * RHO["Cu"]) * 1e-9, k))
        elif k == "utron hub":
            per.append((zc, math.pi * (e["r1"] ** 2 - e["r0"] ** 2) * (e["z1"] - e["z0"]) * 1e-9 * RHO["G10"], k))
    hub = [e for e in el if e["kind"] == "hub"][0]
    hh = 0.5 * (hub["z1"] - hub["z0"])
    rs = min(45.0, hh - 8.0)
    m_hub = (4 / 3) * math.pi * rs ** 3 * 1e-9 * RHO["glass"] * 0.15 + 2.0      # thin-wall vessel + AH coils / C_R (placeholder) [RH]
    per.append((0.5 * (hub["z0"] + hub["z1"]), m_hub, "hub"))
    sleeve = math.pi * (S.SLEEVE_R ** 2 - S.SHAFT_R ** 2) * 1e-6 * RHO["G10"]       # kg/m
    return per, sleeve, (hub["z0"], hub["z1"])


def beam(z_nodes, d_mm, bore_mm, point, q_extra, bearings, hub, joint="rigid"):
    """K, M of the shaft (with a joint at the hub split) -> f1, deflection under 1 g lateral, bearing loads."""
    n = len(z_nodes)
    L = np.diff(z_nodes) * 1e-3
    I = math.pi / 64 * ((d_mm * 1e-3) ** 4 - (bore_mm * 1e-3) ** 4)
    A = math.pi / 4 * ((d_mm * 1e-3) ** 2 - (bore_mm * 1e-3) ** 2)
    mu = RHO_STEEL * A + q_extra                                       # kg/m
    # dof: node i -> (2i, 2i+1); a hinge at the hub split doubles the rotation dof there
    ndof = 2 * n
    zh = 0.5 * (hub[0] + hub[1])
    ih = int(np.argmin(np.abs(z_nodes - zh)))
    rot_r = {ih: ndof} if joint == "hinge" else {}
    if joint == "hinge":
        ndof += 1
    K = np.zeros((ndof, ndof)); M = np.zeros((ndof, ndof))
    for e in range(n - 1):
        l = L[e]
        k = E_STEEL * I / l ** 3 * np.array([[12, 6 * l, -12, 6 * l], [6 * l, 4 * l * l, -6 * l, 2 * l * l],
                                              [-12, -6 * l, 12, -6 * l], [6 * l, 2 * l * l, -6 * l, 4 * l * l]])
        m = mu * l / 420 * np.array([[156, 22 * l, 54, -13 * l], [22 * l, 4 * l * l, 13 * l, -3 * l * l],
                                     [54, 13 * l, 156, -22 * l], [-13 * l, -3 * l * l, -22 * l, 4 * l * l]])
        a, b = e, e + 1
        dofs = [2 * a, 2 * a + 1, 2 * b, rot_r.get(b, 2 * b + 1) if False else 2 * b + 1]
        if a in rot_r:                         # the element right of the hinge uses the second rotation dof
            dofs[1] = rot_r[a]
        for i in range(4):
            for j in range(4):
                K[dofs[i], dofs[j]] += k[i, j]; M[dofs[i], dofs[j]] += m[i, j]
    for zp, mp, _ in point:
        i = int(np.argmin(np.abs(z_nodes - zp))); M[2 * i, 2 * i] += mp
    for zb in bearings:
        i = int(np.argmin(np.abs(z_nodes - zb))); K[2 * i, 2 * i] += K_BEARING
    w2, V = np.linalg.eig(np.linalg.solve(K, M))                      # M v = (1/w^2) K v
    lam = np.real(w2); lam = lam[lam > 0]
    f1 = 1.0 / (2 * math.pi * math.sqrt(lam.max()))
    F = M @ np.tile([9.81, 0.0], ndof // 2 + 1)[:ndof] * 0
    g = np.zeros(ndof); g[0:2 * n:2] = 9.81
    F = M @ g                                                          # 1 g lateral (transport / horizontal test)
    u = np.linalg.solve(K, F)
    w = u[0:2 * n:2]
    loads = [K_BEARING * w[int(np.argmin(np.abs(z_nodes - zb)))] for zb in bearings]
    return dict(f1_Hz=f1, defl_max_mm=float(np.max(np.abs(w)) * 1e3), w_mm=(w * 1e3).tolist(), bearing_loads_N=loads,
                shaft_kg=RHO_STEEL * A * (z_nodes[-1] - z_nodes[0]) * 1e-3)


def layouts(lad):
    """candidate bearing positions (z, mm), symmetric about the hub, at section boundaries (room for a bearing hub)."""
    el = lad["tube_geometry"]["elements"]
    L = lad["tube_geometry"]["L_total_mm"]
    hub = [e for e in el if e["kind"] == "hub"][0]
    zc = 0.5 * (hub["z0"] + hub["z1"])
    clk = {e["side"]: e for e in el if e["kind"] == "clocking"}
    rel = {e["side"]: e for e in el if e["kind"] == "reluctance"}
    ca = [e for e in el if e["kind"] in ("Ca plate",)]
    ca_out = min(e["z0"] for e in ca)
    mirror = lambda z: 2 * zc - z
    end_lo, end_hi = 0.0, L
    hub_lo, hub_hi = hub["z0"], hub["z1"]
    rc_lo = rel["A"]["z1"]                      # between reluctance A and clocking A
    end_lo = min(e["zc"] for e in el if e["kind"] == "bearing" and e.get("where") == "end")
    end_hi = max(e["zc"] for e in el if e["kind"] == "bearing" and e.get("where") == "end")
    ca_lo = clk["A"]["z1"]                      # between clocking A and Ca
    design = sorted(e["zc"] for e in el if e["kind"] == "bearing")
    return {
        "6: AS BUILT (layout bearing hubs)": design,
        "2: ends": [end_lo, end_hi],
        "4: ends + hub faces": [end_lo, hub_lo, hub_hi, end_hi],
        "4: reluctance|clocking + hub faces": [rc_lo, hub_lo, hub_hi, mirror(rc_lo)],
        "6: ends + reluctance|clocking + hub faces": [end_lo, rc_lo, hub_lo, hub_hi, mirror(rc_lo), end_hi],
        "6: ends + clocking|Ca + hub faces": [end_lo, ca_lo, hub_lo, hub_hi, mirror(ca_lo), end_hi],
    }


def main():
    lad = S.size_stack("tube")
    per, sleeve, hub = rotor_masses(lad)
    L = lad["tube_geometry"]["L_total_mm"]
    z = np.linspace(0.0, L, 253)                                      # the end bearing hubs sit at the shaft ends
    out = dict(rotor_parts_kg=sum(m for _, m, _ in per), sleeve_kg_per_m=sleeve, L_shaft_mm=float(z[-1] - z[0]),
               criteria=dict(f1_min_Hz=3 * RPM_MAX / 60.0, defl_max_mm=0.05, k_bearing_N_per_m=K_BEARING), rows=[])
    f_need = 3 * RPM_MAX / 60.0
    print(f"rotor parts {out['rotor_parts_kg']:.1f} kg; shaft {out['L_shaft_mm']:.0f} mm; need f1 >= {f_need:.0f} Hz, "
          f"1 g deflection <= 0.05 mm", flush=True)
    for name, bz in layouts(lad).items():
        for joint in ("rigid", "hinge"):
            best = None
            for d in range(20, 81, 2):
                r = beam(z, float(d), 0.0, per, sleeve, bz, hub, joint)
                ok = r["f1_Hz"] >= f_need and r["defl_max_mm"] <= 0.05
                row = dict(layout=name, joint=joint, d_mm=d, f1_Hz=r["f1_Hz"], defl_max_mm=r["defl_max_mm"],
                           loads_N=r["bearing_loads_N"], shaft_kg=r["shaft_kg"], ok=ok)
                if ok and best is None:
                    best = row
            if best is None:
                best = dict(layout=name, joint=joint, d_mm=None, ok=False, f1_Hz=r["f1_Hz"], defl_max_mm=r["defl_max_mm"])
            best["bearings_z_mm"] = [round(v, 1) for v in bz]
            if name.startswith("6: AS BUILT"):
                r25 = beam(z, 25.0, 0.0, per, sleeve, bz, hub, joint)
                best["at_d25"] = dict(f1_Hz=r25["f1_Hz"], defl_max_mm=r25["defl_max_mm"], loads_N=r25["bearing_loads_N"],
                                      shaft_kg=r25["shaft_kg"])
                print(f"   at d 25 mm ({joint}): f1 {r25['f1_Hz']:.0f} Hz, 1 g deflection {r25['defl_max_mm']*1e3:.1f} um, "
                      f"loads {', '.join(f'{x:.0f}' for x in r25['bearing_loads_N'])} N, shaft {r25['shaft_kg']:.1f} kg", flush=True)
            out["rows"].append(best)
            print(f"{name:46s} {joint:5s}: d_min {best['d_mm']} mm  f1 {best['f1_Hz']:.0f} Hz  1 g defl {best['defl_max_mm']*1e3:.1f} um"
                  + (f"  loads {', '.join(f'{x:.0f}' for x in best.get('loads_N', []))} N" if best.get('loads_N') else ""), flush=True)
    json.dump(out, open(os.path.join(HERE, "shaft_bearings_results.json"), "w"), indent=1, default=float)


if __name__ == "__main__":
    main()
