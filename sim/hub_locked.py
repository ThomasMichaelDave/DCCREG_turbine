"""sim/hub_locked.py -- the hub as the designer locked it (presets/hub-locked.json), and the field at the AH null from
two electrode rings around its vessel, against the two Rogowski electrodes inside it (sim/core_null_field.py).

The hub, inside out (designer, 2026-10-08):
  vessel    a borosilicate sphere, 50 mm OD, vacuum inside (wall 1.5 mm [RH]);
  rings     two electrode rings around the vessel, one on each hemisphere;
  AH        the cores with their coils on the z axis, top and bottom: the register's MnZn rods and the 160-turn coil in
            variant (a)'s window (one REF envelope here: r <= 11.45 mm, |z| 30.7-72);
  retainer  holds the vessel, the rings and the AH; the shaft coupler encapsulates it (both eps 4.7 [RH], r <= 33 mm,
            |z| <= 72 here);
  shaft     the same shaft top and bottom (REF): a flange r 32 at |z| 72-80 [RH: moved out to clear the coil], the
            shaft r 15 beyond; each half carries its side's electrostatic and magnetic pump.
The rings, three ways [OC]:
  DC, as connected   electrostatics with the dielectrics (sim/core_rings.py's finite volumes on this hub), at the null
                     supply's 20.6 kV across (dc1: A -13.2, B +7.4 kV);
  DC, settled        after a few eps / sigma of the glass (minutes, vessel_resistivity), if the glass alone conducts:
                     the caps beyond each ring follow the ring, the band between grades as ln tan(theta / 2) (a thin
                     resistive shell), and the vacuum sees that potential on its wall (Legendre: E0 = a1 / R_in);
  swing              the float wiring's 120 Hz swing, which the glass does not see as DC; the rings' strays on the pump
                     (ngspice, sim/core_field.py float).
Against: the two Rogowski electrodes inside the vacuum at the dc1 design gap, with this hub's REF parts (boundary
elements, stemless: the axis is the AH's, so the stems would enter from the side).
Usage: python3 sim/hub_locked.py [--h 0.25] [--procs 4]   (writes sim/hub_locked_results.json)
"""
import argparse
import json
import math
import os
import sys
import time
from multiprocessing import Pool

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import core_null_field as NF        # noqa: E402
import core_rings as CR             # noqa: E402

SPEC = json.load(open(os.path.join(HERE, "..", "presets", "hub-locked.json")))


def V(key):
    return SPEC[key]["value"]


_ves, _ah, _ret, _cpl, _sh = V("vessel"), V("AH"), V("retainer"), V("shaft_coupler"), V("shaft")
HUB = dict(R_v=0.5 * _ves["od_mm"], R_in=0.5 * _ves["od_mm"] - V("vessel_wall")["t_mm"], eps_glass=_ves["eps_r"],
           eps_ret=_ret["eps_r"], ret_r=_ret["r_max_mm"] + _cpl["wall_mm"], ret_z=_ret["absz_max_mm"],
           ah_r=_ah["coil"]["r_mm"][1], ah_z=tuple(_ah["core"]["absz_mm"]), fl_r=_sh["flange_r_mm"],
           fl_z=tuple(_sh["flange_absz_mm"]), sh_r=0.5 * _sh["d_mm"], R_box=162.0, Z_box=110.0)
RINGS = {"wire 1.5 mm": dict(kind="wire", d=1.5), "band 4 mm": dict(kind="band", w=4.0, t=0.5),
         "band 8 mm": dict(kind="band", w=8.0, t=0.5)}
THETAS = (20.0, 30.0, 40.0, 50.0, 60.0, 70.0, 80.0)
RHO_GLASS = V("vessel_resistivity")["rho_ohm_m"]


def maps(ring, theta, coils, h, hub=HUB):
    """eps and conductor maps (0 free, 1 REF, 2 ring) of the locked hub's half z >= 0; coils False drops the AH."""
    nr, nz = int(round(hub["R_box"] / h)), int(round(hub["Z_box"] / h))
    r = (np.arange(nr) + 0.5) * h
    z = (np.arange(nz) + 0.5) * h
    R, Z = np.meshgrid(r, z, indexing="ij")
    rho = np.hypot(R, Z)
    eps = np.ones((nr, nz))
    eps[(R <= hub["ret_r"]) & (Z <= hub["ret_z"]) & (rho >= hub["R_v"])] = hub["eps_ret"]   # retainer + coupler
    eps[(rho >= hub["R_in"]) & (rho < hub["R_v"])] = hub["eps_glass"]
    cond = np.zeros((nr, nz), dtype=np.int8)
    if coils:                                                          # the AH core and its coil: one REF envelope
        cond[(R <= hub["ah_r"]) & (Z >= hub["ah_z"][0]) & (Z <= hub["ah_z"][1])] = 1
    cond[(R <= hub["fl_r"]) & (Z >= hub["fl_z"][0]) & (Z <= hub["fl_z"][1])] = 1
    cond[(R <= hub["sh_r"]) & (Z >= hub["fl_z"][1])] = 1
    th = math.radians(theta)
    if ring["kind"] == "wire":
        rc = hub["R_v"] + 0.5 * ring["d"]
        m = np.hypot(R - rc * math.sin(th), Z - rc * math.cos(th)) <= 0.5 * ring["d"]
    else:
        pol = np.arctan2(R, Z)
        m = (rho >= hub["R_v"]) & (rho <= hub["R_v"] + ring["t"]) & (np.abs(pol - th) <= 0.5 * ring["w"] / hub["R_v"])
    cond[m] = 2
    return r, z, eps, cond


def edge_deg(ring, theta, hub=HUB):
    """the ring's edge toward the equator, as a polar angle on the vessel (deg)."""
    half = 0.5 * ring["d"] if ring["kind"] == "wire" else 0.5 * ring["w"]
    return theta + math.degrees(half / hub["R_v"])


def settled(theta1_deg, hub=HUB, n=20001):
    """the settled DC field at the null per volt across the rings, if the glass alone conducts: a thin resistive shell
    with the upper cap at +1/2 (polar angle < theta1), the lower at -1/2, and ln tan(theta / 2) between; the vacuum
    sees that potential at R_in. Returns E0 (V/m per V) and a1 (V per V)."""
    t1 = math.radians(theta1_deg)
    th = np.linspace(0.0, math.pi, n)
    v = np.where(th <= t1, 0.5, np.where(th >= math.pi - t1, -0.5, 0.0))
    band = (th > t1) & (th < math.pi - t1)
    v[band] = 0.5 * np.log(np.tan(th[band] / 2)) / math.log(math.tan(t1 / 2))
    y = v * np.cos(th) * np.sin(th)
    a1 = 1.5 * float(np.sum(0.5 * (y[1:] + y[:-1]) * np.diff(th)))
    return a1 / (hub["R_in"] * 1e-3), a1


def _solve_case(args):
    name, theta, coils, h = args
    t0 = time.time()
    q = CR.solve(RINGS[name], theta, coils, h, hub=HUB, maps_fn=maps)
    q["ring_name"] = name
    q["solve_s"] = time.time() - t0
    for k in ("r_mm", "z_mm", "Ez_axis_kV_cm_per_kV", "Ez_mid_kV_cm_per_kV"):
        q.pop(k)
    return q


def _pump_case(args):
    c_ref, c_rr, name = args
    return name, CR.pump(c_ref, c_rr, name)


def discs_inside(design):
    """the null's Rogowski pair (sim/core_null_field.py, the dc1 design) in this hub: stemless electrodes, the AH
    envelopes, the flanges and the shaft halves as REF (boundary elements; the dielectrics left out)."""
    g, shape = design["g_min_mm"], dict(design["shape"])
    h = NF.h_rule(g)

    def rect(r0, r1, z0, z1, side, f=1.0):
        pts = [np.array([[0.0, z0], [r1 - f, z0]]), NF.arc((r1 - f, z0 + f), f, -0.5 * math.pi, 0.0, 30),
               np.array([[r1, z0 + f], [r1, z1 - f]]), NF.arc((r1 - f, z1 - f), f, 0.0, 0.5 * math.pi, 30),
               np.array([[r1 - f, z1], [0.0, z1]])]
        p = np.vstack(pts)
        p[:, 1] *= side
        return p
    bodies = [("electrode A", "A", NF.cut(NF.rogowski(g, side=-1, rs=None, **shape), h)),
              ("electrode B", "B", NF.cut(NF.rogowski(g, side=+1, rs=None, **shape), h))]
    for side in (+1, -1):
        bodies += [(f"AH {side:+d}", "REF", NF.cut(rect(0, HUB["ah_r"], HUB["ah_z"][0], HUB["ah_z"][1], side), lambda p: 0.6)),
                   (f"flange {side:+d}", "REF", NF.cut(rect(0, HUB["fl_r"], HUB["fl_z"][0], HUB["fl_z"][1], side), lambda p: 0.8)),
                   (f"shaft {side:+d}", "REF", NF.cut(rect(0, HUB["sh_r"], HUB["fl_z"][1], 160.0, side), lambda p: 1.0))]
    m = NF.Model(bodies)
    sup = {"dc1": (design["V_A_kV"] * 1e3, design["V_B_kV"] * 1e3)}
    q = NF.analyse(m, g, "the null's Rogowski pair in the locked hub", dict(shape="rogowski", rs=None, **shape), sup)
    for k in ("Ez_axis_rel", "z_axis_mm", "Ez_mid_rel", "r_mid_mm"):
        q.pop(k)
    q["fits"] = dict(R_max_mm=float(m.p0[m.owner == 0][:, 0].max() * 1e3), R_in_mm=HUB["R_in"],
                     corner_to_wall_mm=None)
    pts = np.vstack([m.p0[m.owner == k] for k in (0, 1)]) * 1e3
    q["fits"]["corner_to_wall_mm"] = float(HUB["R_in"] - np.hypot(pts[:, 0], pts[:, 1]).max())
    return q


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--h", type=float, default=0.25)
    ap.add_argument("--procs", type=int, default=4)
    a = ap.parse_args()
    t0 = time.time()
    nf = json.load(open(os.path.join(HERE, "core_null_field_results.json")))
    d1 = nf["design"]["dc1"]
    v_dc = d1["V_gap_kV"]                                              # the null supply's DC across the pair
    # 1. the rings: field and strays over the polar angle and the form, the AH in (and out, for one form)
    cases = [(nm, th, True, a.h) for nm in RINGS for th in THETAS] + [("band 8 mm", th, False, a.h) for th in THETAS]
    with Pool(a.procs) as pool:
        rings = list(pool.imap(_solve_case, cases))
    for q in rings:
        e1, _ = settled(edge_deg(RINGS[q["ring_name"]], q["theta_deg"]))
        q["E_dc_kV_cm"] = q["E_centre_kV_cm_per_kV"] * v_dc
        q["edge_deg"] = edge_deg(RINGS[q["ring_name"]], q["theta_deg"])
        q["E_settled_kV_cm"] = e1 * 1e-5 * v_dc * 1e3
        print(f"{q['ring_name']:12s} {q['theta_deg']:4.0f} AH {q['coils']!s:5s}: C_ref {q['C_ring_ref_pF']:6.2f} pF "
              f"C_rr {q['C_ring_ring_pF']:5.2f} pF  E0 {q['E_centre_kV_cm_per_kV']:.4f} (kV/cm)/kV -> DC {q['E_dc_kV_cm']:.2f}, "
              f"settled {q['E_settled_kV_cm']:.2f} kV/cm  ({q['solve_s']:.0f} s)", flush=True)
    conv = CR.solve(RINGS["band 8 mm"], 50.0, True, 0.5 * a.h, hub=HUB, maps_fn=maps)
    for k in ("r_mm", "z_mm", "Ez_axis_kV_cm_per_kV", "Ez_mid_kV_cm_per_kV"):
        conv.pop(k)
    print("convergence (band 8 mm, 50 deg, h/2):", conv["E_centre_kV_cm_per_kV"], conv["C_ring_ref_pF"], conv["C_ring_ring_pF"])
    # 2. the swing on the rings: the pump with each case's strays (AH in)
    pc = [(q["C_ring_ref_pF"], q["C_ring_ring_pF"], f"locked {q['ring_name']} {q['theta_deg']:g}") for q in rings if q["coils"]]
    with Pool(a.procs) as pool:
        pumped = dict(pool.imap(_pump_case, pc))
    for q in rings:
        if q["coils"]:
            p = pumped[f"locked {q['ring_name']} {q['theta_deg']:g}"]
            q["pump"] = p
            q["E_swing_kV_cm"] = q["E_centre_kV_cm_per_kV"] * (p["swing_pk_kV"] or 0.0)
    # 3. the discs inside, in this hub
    disc = discs_inside(d1)
    print("discs inside:", {k: v for k, v in disc.items() if k not in ("supplies", "shape")}, disc["supplies"]["dc1"])
    # 4. the settled field's limits: rings at the equator (hemispheres at +-1/2) and the glass's time constant
    e_hemi, _ = settled(89.999)
    tau = 8.8541878128e-12 * HUB["eps_glass"] * RHO_GLASS
    out = dict(note="see the module docstring", spec="presets/hub-locked.json", hub=HUB, rings_def=RINGS, h_mm=a.h,
               V_dc_kV=v_dc, rings=rings, convergence_h2=conv, discs_inside=disc, design_dc1=d1,
               settled_hemispheres_kV_cm=e_hemi * 1e-5 * v_dc * 1e3, glass_tau_s=tau, run_s=time.time() - t0)
    json.dump(out, open(os.path.join(HERE, "hub_locked_results.json"), "w"), indent=1, default=float)
    for q in rings:
        if q["coils"]:
            p = q["pump"]
            print(f"{q['ring_name']:12s} {q['theta_deg']:4.0f}: z {p['z']:.3f} swing {p['swing_pk_kV']:.2f} kV -> "
                  f"{q['E_swing_kV_cm']:.2f} kV/cm peak; P {p['P_belt_W']:.2f} W")
    print(f"tau_glass {tau:.0f} s; hemispheres settled {out['settled_hemispheres_kV_cm']:.2f} kV/cm; done in "
          f"{time.time() - t0:.0f} s")


if __name__ == "__main__":
    main()
