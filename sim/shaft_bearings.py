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
Usage: python3 sim/shaft_bearings.py -> sim/shaft_bearings_results.json (the spark-gap tube, its stator on the frame)
       python3 sim/shaft_bearings.py --record [k_mag N/m] -> sim/shaft_bearings_record_results.json (the design of
       record: the counter-rotor rides on four inner bearings; record() below)
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


# ---------------------------------------------------------------------------------------------------------
# the design of record: two bodies (sim/tube_geometry.py --record)
# ---------------------------------------------------------------------------------------------------------
DENSITY = [("MnZn", 4800.0), ("NiFe", 8700.0), ("M235", 7650.0), ("borosilicate", 2230.0), ("PEEK", 1300.0),
           ("gel", 1000.0), ("coil", 5050.0), ("foil", 8900.0), ("wire ring", 8900.0), ("Al ", 2700.0), ("G10", 1850.0),
           ("G-10", 1850.0), ("steel", 7850.0), ("bearing", 7850.0)]          # kg/m^3, datasheet-class [IR]; windings:
# half Cu (8900), half impregnant (1200) [IR]
E_G10, E_PEEK = 18e9, 3.6e9                                                   # in-plane G10, unfilled PEEK [IR]
F_REL_HZ = 1200.0 / 60.0                                                       # the bearings' relative speed (20 Hz)


def _density(material):
    for key, rho in DENSITY:
        if key in material:
            return rho
    raise KeyError(material)


def record_parts(pick="g 0.5 / 6 bridges / 1200 rpm"):
    """every solid of the record's model with its body, mass, centroid and inertia about its own centroid (y axis)."""
    import tube_geometry as TG
    from OCP.BRepGProp import BRepGProp
    from OCP.GProp import GProp_GProps
    lad = S.size_stack("tube", TG.record_plates(pick))
    m = TG.Machine(lad).build()
    out = []
    for pt in m.parts:
        mat = m.protos[pt["proto"]][2]
        rho = _density(mat)
        g = GProp_GProps(); BRepGProp.VolumeProperties_s(m.placed(pt), g)
        c, I = g.CentreOfMass(), g.MatrixOfInertia()
        out.append(dict(name=pt["name"], body=pt["body"], material=mat, kg=g.Mass() * 1e-9 * rho,
                        x=c.X(), z=c.Z(), J_yy_kgm2=I.Value(2, 2) * 1e-15 * rho))   # mm^5 -> m^5, x rho
    return lad, out


def two_body(lad, parts, d_mm, hub_joint="coupler", k_b=K_BEARING, k_mag=None, extra_inner=()):
    """the shaft (rotor) and the counter-rotor as Euler-Bernoulli beams on one z grid. The four inner bearings join them
    (radial springs k_b), the two end bearings tie the shaft to the frame. Every solid is a lumped mass and rotary
    inertia at its body's nearest node; the shaft's own steel is distributed. The hub span (between the flanges)
    bends as the G10 coupler + the PEEK retainer at the equator ('coupler', rigid joints) or as a hinge. k_mag: the
    utrons' negative magnetic stiffness per reluctance plane, between the bodies (N/m) [OC law / IR inputs]."""
    el = lad["tube_geometry"]["elements"]
    L = lad["tube_geometry"]["L_total_mm"]
    z = np.linspace(0.0, L, 471)
    n = len(z)
    hub = [e for e in el if e["kind"] == "hub"][0]
    brg = sorted([e for e in el if e["kind"] == "bearing"], key=lambda e: e["zc"])
    ends = [b["zc"] for b in brg if b["where"] == "end"]
    inner = [b["zc"] for b in brg if b["where"] != "end"] + list(extra_inner)
    cr = [p for p in parts if p["body"] == "stator"]
    zc0 = min(e["z0"] for e in el if e["body"] == "stator" and e["kind"] not in ("bearing",))
    zc1 = max(e["z1"] for e in el if e["body"] == "stator" and e["kind"] not in ("bearing",))
    H = json.load(open(os.path.join(os.path.dirname(HERE), "presets", "hub-locked.json")))
    r_ret, w_cpl = H["retainer"]["value"]["r_max_mm"] * 1e-3, H["shaft_coupler"]["value"]["wall_mm"] * 1e-3
    R_gel = (0.5 * H["vessel"]["value"]["od_mm"] + H["interface_filler"]["value"]["t_mm"]) * 1e-3
    EI_hub = (E_G10 * math.pi / 4 * ((r_ret + w_cpl) ** 4 - r_ret ** 4)
              + E_PEEK * math.pi / 4 * (r_ret ** 4 - R_gel ** 4))                       # the equator's section
    I_sh = math.pi / 64 * (d_mm * 1e-3) ** 4
    A_sh = math.pi / 4 * (d_mm * 1e-3) ** 2
    r_c = lad["tube"]["r_outMm"] + 12.0
    EI_cr = E_G10 * math.pi / 4 * (((r_c + 4.0) * 1e-3) ** 4 - (r_c * 1e-3) ** 4)       # the 4 mm cage (the stiffest
    # sections, the bridge rings, are stiffer still) [IR]
    nd = 4 * n                                   # dof: shaft (w, th) at 2i, 2i+1; counter-rotor at 2n + 2i, 2n + 2i + 1
    K = np.zeros((nd, nd)); M = np.zeros((nd, nd))

    def add_beam(off, i, EI, mu):
        l = (z[i + 1] - z[i]) * 1e-3
        k = EI / l ** 3 * np.array([[12, 6 * l, -12, 6 * l], [6 * l, 4 * l * l, -6 * l, 2 * l * l],
                                    [-12, -6 * l, 12, -6 * l], [6 * l, 2 * l * l, -6 * l, 4 * l * l]])
        mm = mu * l / 420 * np.array([[156, 22 * l, 54, -13 * l], [22 * l, 4 * l * l, 13 * l, -3 * l * l],
                                      [54, 13 * l, 156, -22 * l], [-13 * l, -3 * l * l, -22 * l, 4 * l * l]])
        dofs = [off + 2 * i, off + 2 * i + 1, off + 2 * i + 2, off + 2 * i + 3]
        K[np.ix_(dofs, dofs)] += k; M[np.ix_(dofs, dofs)] += mm
    cr_nodes = set()
    for i in range(n - 1):
        zm = 0.5 * (z[i] + z[i + 1])
        in_hub = hub["z0"] < zm < hub["z1"]
        if in_hub and hub_joint == "hinge":
            EI = 1e-3 * EI_hub                   # a hinge, numerically: the span carries shear, not moment
        else:
            EI = EI_hub if in_hub else E_STEEL * I_sh
        add_beam(0, i, EI, 0.0 if in_hub else RHO_STEEL * A_sh)
        if zc0 <= zm <= zc1:
            add_beam(2 * n, i, EI_cr, 0.0)       # the cage's own mass is in the parts list
            cr_nodes.update((i, i + 1))
    cr_idx = np.array(sorted(cr_nodes))
    for p_ in parts:
        if p_["name"].startswith("shaft_"):
            continue                             # the shaft's steel is distributed above
        off = 2 * n if p_["body"] == "stator" else 0
        if p_["body"] == "stator" and "spider" in p_["name"] and "end" in p_["name"]:
            continue                             # the end spiders belong to the frame
        i = int(np.argmin(np.abs(z - p_["z"]))) if off == 0 else int(cr_idx[np.argmin(np.abs(z[cr_idx] - p_["z"]))])
        M[off + 2 * i, off + 2 * i] += p_["kg"]
        M[off + 2 * i + 1, off + 2 * i + 1] += p_["J_yy_kgm2"] + p_["kg"] * (p_["x"] ** 2 + (p_["z"] - z[i]) ** 2) * 1e-6
    for zb in inner:
        i = int(np.argmin(np.abs(z - zb)))
        a_, b_ = 2 * i, 2 * n + 2 * i
        K[a_, a_] += k_b; K[b_, b_] += k_b; K[a_, b_] -= k_b; K[b_, a_] -= k_b
    for zb in ends:
        i = int(np.argmin(np.abs(z - zb))); K[2 * i, 2 * i] += k_b
    planes = [e["zc"] for e in el if e["kind"] == "w utron"]
    if k_mag:
        for zp in planes:                        # negative stiffness between the bodies at each reluctance plane
            i = int(np.argmin(np.abs(z - zp)))
            a_, b_ = 2 * i, 2 * n + 2 * i
            K[a_, a_] -= k_mag; K[b_, b_] -= k_mag; K[a_, b_] += k_mag; K[b_, a_] += k_mag
    # the counter-rotor's dof outside its extent carry nothing: pin them
    free = [j for j in range(nd) if j < 2 * n or (j - 2 * n) // 2 in cr_nodes]
    Kf, Mf = K[np.ix_(free, free)], M[np.ix_(free, free)]
    mu = np.linalg.eigvals(np.linalg.solve(Kf, Mf))                 # M v = (1 / w^2) K v; massless dof give mu = 0
    mu = np.sort(np.real(mu[np.abs(np.imag(mu)) < 1e-9 * np.abs(mu).max()]))[::-1]
    f = [float(1.0 / (2 * math.pi * math.sqrt(x))) for x in mu[:6] if x > 0]
    g = np.zeros(nd); g[0:2 * n:2] = 9.81; g[2 * n::2] = 9.81
    u = np.zeros(nd); u[free] = np.linalg.solve(Kf, (M @ g)[free])
    w_s, w_c = u[0:2 * n:2] * 1e3, u[2 * n::2] * 1e3
    gap = [float(w_s[int(np.argmin(np.abs(z - zp)))] - w_c[int(np.argmin(np.abs(z - zp)))]) for zp in planes]
    loads = {f"{zb:.0f}": float(k_b * (u[2 * int(np.argmin(np.abs(z - zb)))] - u[2 * n + 2 * int(np.argmin(np.abs(z - zb)))]))
             for zb in inner}
    loads.update({f"{zb:.0f} (end)": float(k_b * u[2 * int(np.argmin(np.abs(z - zb)))]) for zb in ends})
    return dict(d_mm=d_mm, hub_joint=hub_joint, k_mag_N_per_m=k_mag, extra_inner_z_mm=list(extra_inner), f_Hz=f,
                f1_Hz=f[0], EI_hub_Nm2=EI_hub,
                EI_shaft_Nm2=E_STEEL * I_sh, EI_counter_rotor_Nm2=EI_cr, defl_shaft_max_um=float(np.abs(w_s).max() * 1e3),
                gap_change_um=[g_ * 1e3 for g_ in gap], bearing_loads_1g_N=loads,
                m_rotor_kg=float(sum(p_["kg"] for p_ in parts if p_["body"] != "stator") + RHO_STEEL * A_sh * (L - (hub["z1"] - hub["z0"])) * 1e-3),
                m_counter_rotor_kg=float(sum(p_["kg"] for p_ in parts if p_["body"] == "stator" and not ("spider" in p_["name"] and "end" in p_["name"]))))


def record(k_mag=None):
    lad, parts = record_parts()
    by = {}
    for p_ in parts:
        key = (p_["body"], p_["material"].split(",")[0])
        by[key] = by.get(key, 0.0) + p_["kg"]
    out = dict(model="two bodies: the shaft and the counter-rotor on four inner bearings, two end bearings to the frame",
               L_mm=lad["tube_geometry"]["L_total_mm"], f_rel_Hz=F_REL_HZ, k_bearing_N_per_m=K_BEARING,
               criteria=dict(f1_min_Hz=3 * F_REL_HZ, f1_old_min_Hz=3 * RPM_MAX / 60.0, gap_change_max_um=50.0),
               masses_kg={f"{b} / {m_}": round(v, 3) for (b, m_), v in sorted(by.items())}, rows=[])
    el = lad["tube_geometry"]["elements"]
    ends = sorted(e["zc"] for e in el if e["kind"] == "bearing" and e["where"] == "end")
    # the stiffening option: a bearing between the shaft and each bridge ring's outer end, beside the end bearing [IR]
    ring_ends = (ends[0] + 18.0, ends[1] - 18.0)
    cases = [(d, j, km, ()) for d in (25.0, 30.0) for j in ("coupler", "hinge") for km in ((None, k_mag) if k_mag else (None,))]
    cases += [(d, "coupler", k_mag, ()) for d in (35.0, 40.0)]
    cases += [(d, "coupler", k_mag, ring_ends) for d in (25.0, 30.0)]
    for d, joint, km, extra in cases:
            if True:
                r = two_body(lad, parts, d, joint, k_mag=km, extra_inner=extra)
                ok = r["f1_Hz"] >= out["criteria"]["f1_min_Hz"] and max(abs(x) for x in r["gap_change_um"]) <= 50.0
                r["ok"] = bool(ok)
                out["rows"].append(r)
                print(f"d {d:.0f} mm, hub {joint:7s}{'' if not km else f', k_mag {km:.2e}'}"
                      f"{', + bridge-ring bearings' if extra else ''}: f {', '.join(f'{x:.0f}' for x in r['f_Hz'][:3])} Hz; "
                      f"1 g: shaft {r['defl_shaft_max_um']:.1f} um, gap change "
                      f"{', '.join(f'{x:+.1f}' for x in r['gap_change_um'])} um; rotor {r['m_rotor_kg']:.1f} kg, "
                      f"counter-rotor {r['m_counter_rotor_kg']:.1f} kg", flush=True)
    json.dump(out, open(os.path.join(HERE, "shaft_bearings_record_results.json"), "w"), indent=1, default=float)
    return out


if __name__ == "__main__":
    if sys.argv[1:2] == ["--record"]:
        record(float(sys.argv[2]) if len(sys.argv) > 2 else None)
    else:
        main()
