"""sim/core_rings.py -- two electrode rings on the core's vessel, one on each hemisphere, as the conductors that carry the
pump's swing (designer's proposal). Axisymmetric electrostatics (r, z) of the hub, then the pump with the rings' strays.

The hub (dimensions [RH]: the tube's placeholder, sim/tube_geometry.py, in the designer's layer order):
  vessel     glass sphere, r 42-45 mm (eps 4.6), vacuum inside;
  retainer   non-magnetic composite shell, r 45-48 mm (eps 4.7, as G10) -- the rings sit on the vessel, under it;
  rings      ring A on the upper hemisphere at polar angle theta from the axis, ring B its mirror: a round wire on the
             vessel's surface (dia 2 or 6 mm) or a band 10 mm wide along the surface (0.5 mm thick);
  coils      the field (AH) coils, at about the shaft's potential: two loops around the retainer, 6 x 6 mm at r 47-53,
             |z| 18-24 (where they fit inside the placeholder cones; the real coils are not sized) -- or left out;
  cones      the shaft-coupling cones, G10 (eps 4.7), r from 75 at z 0 to 32 at |z| 60, 3 mm wall;
  REF        the flanges (r <= 32, |z| 60-68), the shaft (r <= 12.5) and the hub-face bearing (r <= 26, |z| 70.5-85.5),
             the counter-rotor's cage (r 162) and its first stator vane (|z| 88).
Method [OC]: finite volumes on a uniform (r, z) grid, div(eps grad V) = 0, conductors as fixed-potential cells; half the
hub (z >= 0) with the midplane antisymmetric (rings at +1 / -1) or symmetric (both at +1).
  ring-to-REF capacitance  = the symmetric charge per volt;
  ring-to-ring capacitance = (antisymmetric - symmetric charge) / 2 per volt;
  field at the centre      = -dV/dz at the origin per volt of A - B.
The pump: sim/core_field.py's float wiring (Cca / Ccb 1 nF) with those strays in place of its 20 / 10 pF guesses.
Usage: python3 sim/core_rings.py [--h 0.25] [--procs 4]   (writes sim/core_rings_results.json)
"""
import argparse
import json
import math
import os
import sys
import time
from multiprocessing import Pool

import numpy as np
import scipy.sparse as sp
import scipy.sparse.linalg as spla

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import core_field as CF                 # noqa: E402

EPS0 = 8.8541878128e-12                 # F/m
HUB = dict(R_in=42.0, R_v=45.0, t_ret=3.0, eps_glass=4.6, eps_ret=4.7, eps_cone=4.7,
           cone_r0=75.0, cone_r1=32.0, cone_hh=60.0, cone_wall=3.0,
           flange_r=32.0, flange_z=(60.0, 68.0), shaft_r=12.5, bearing_r=26.0, bearing_z=(70.5, 85.5),
           R_box=162.0, Z_box=88.0, coil=dict(r=(47.0, 53.0), z=(18.0, 24.0)))       # [RH] placeholders, mm
RINGS = {"wire 2 mm": dict(kind="wire", d=2.0), "wire 6 mm": dict(kind="wire", d=6.0),
         "band 10 mm": dict(kind="band", w=10.0, t=0.5)}
THETAS = (20.0, 30.0, 40.0, 50.0, 60.0, 70.0)


def maps(ring, theta, coils, h, hub=HUB):
    """eps and conductor maps (0 free, 1 REF, 2 ring) at the cell centres of the half hub z >= 0."""
    nr, nz = int(round(hub["R_box"] / h)), int(round(hub["Z_box"] / h))
    r = (np.arange(nr) + 0.5) * h
    z = (np.arange(nz) + 0.5) * h
    R, Z = np.meshgrid(r, z, indexing="ij")
    rho = np.hypot(R, Z)
    eps = np.ones((nr, nz))
    eps[(rho >= hub["R_in"]) & (rho < hub["R_v"])] = hub["eps_glass"]
    eps[(rho >= hub["R_v"]) & (rho < hub["R_v"] + hub["t_ret"])] = hub["eps_ret"]
    ro = hub["cone_r0"] - (hub["cone_r0"] - hub["cone_r1"]) * Z / hub["cone_hh"]
    eps[(Z <= hub["cone_hh"]) & (R <= ro) & (R >= ro - hub["cone_wall"])] = hub["eps_cone"]
    cond = np.zeros((nr, nz), dtype=np.int8)
    cond[(R <= hub["flange_r"]) & (Z >= hub["flange_z"][0]) & (Z <= hub["flange_z"][1])] = 1
    cond[(R <= hub["shaft_r"]) & (Z >= hub["flange_z"][1])] = 1
    cond[(R <= hub["bearing_r"]) & (Z >= hub["bearing_z"][0]) & (Z <= hub["bearing_z"][1])] = 1
    if coils:
        c = hub["coil"]
        cond[(R >= c["r"][0]) & (R <= c["r"][1]) & (Z >= c["z"][0]) & (Z <= c["z"][1])] = 1
    th = math.radians(theta)
    if ring["kind"] == "wire":
        rc = hub["R_v"] + 0.5 * ring["d"]
        m = np.hypot(R - rc * math.sin(th), Z - rc * math.cos(th)) <= 0.5 * ring["d"]
    else:
        pol = np.arctan2(R, Z)
        m = (rho >= hub["R_v"]) & (rho <= hub["R_v"] + ring["t"]) & (np.abs(pol - th) <= 0.5 * ring["w"] / hub["R_v"])
    cond[m] = 2
    return r, z, eps, cond


def solve(ring, theta, coils, h=0.25, hub=HUB, keep=False):
    r, z, eps, cond = maps(ring, theta, coils, h, hub)
    nr, nz = eps.shape
    hm = h * 1e-3
    rc, zc = r * 1e-3, z * 1e-3                                         # m
    # face conductances (F): radial faces between i and i+1, axial faces between j and j+1
    ef_r = 2 * eps[:-1, :] * eps[1:, :] / (eps[:-1, :] + eps[1:, :])
    G_r = 2 * math.pi * EPS0 * ef_r * ((np.arange(1, nr) * hm)[:, None])          # x (h / h)
    ef_z = 2 * eps[:, :-1] * eps[:, 1:] / (eps[:, :-1] + eps[:, 1:])
    G_z = 2 * math.pi * EPS0 * ef_z * rc[:, None]
    G_out_r = 2 * math.pi * EPS0 * eps[-1, :] * (nr * hm) * 2.0                    # to the cage at r = R_box (h/2)
    G_top = 2 * math.pi * EPS0 * eps[:, -1] * rc * 2.0                              # to the stator vane at z = Z_box
    G_mid = 2 * math.pi * EPS0 * eps[:, 0] * rc * 2.0                               # to the midplane (antisymmetric)
    free = cond == 0
    idx = -np.ones((nr, nz), dtype=np.int64)
    idx[free] = np.arange(free.sum())
    n = int(free.sum())
    out = {}
    for mode in ("anti", "sym"):
        Vfix = np.where(cond == 2, 1.0, 0.0)
        rows, cols, vals = [], [], []
        diag = np.zeros(n)
        rhs = np.zeros(n)

        def couple(ia, ja, ib, jb, G):
            """faces between cells a and b with conductance G (arrays of equal shape)."""
            fa, fb = free[ia, ja], free[ib, jb]
            a, b = idx[ia, ja], idx[ib, jb]
            both = fa & fb
            np.add.at(diag, a[fa], G[fa])
            np.add.at(diag, b[fb], G[fb])
            rows.append(a[both]); cols.append(b[both]); vals.append(-G[both])
            rows.append(b[both]); cols.append(a[both]); vals.append(-G[both])
            m1 = fa & ~fb
            np.add.at(rhs, a[m1], G[m1] * Vfix[ib, jb][m1])
            m2 = fb & ~fa
            np.add.at(rhs, b[m2], G[m2] * Vfix[ia, ja][m2])
        I, J = np.meshgrid(np.arange(nr - 1), np.arange(nz), indexing="ij")
        couple(I, J, I + 1, J, G_r)
        I, J = np.meshgrid(np.arange(nr), np.arange(nz - 1), indexing="ij")
        couple(I, J, I, J + 1, G_z)
        fo = free[-1, :]
        np.add.at(diag, idx[-1, :][fo], G_out_r[fo])
        ft = free[:, -1]
        np.add.at(diag, idx[:, -1][ft], G_top[ft])
        if mode == "anti":
            fm = free[:, 0]
            np.add.at(diag, idx[:, 0][fm], G_mid[fm])
        A = sp.csr_matrix((np.concatenate(vals + [diag]),
                           (np.concatenate(rows + [np.arange(n)]), np.concatenate(cols + [np.arange(n)]))), shape=(n, n))
        x = spla.spsolve(A.tocsc(), rhs)
        V = Vfix.copy()
        V[free] = x
        # charge on the ring: the flux out of its cells into free cells
        q = 0.0
        for (ia, ja, ib, jb, G) in (
                (slice(None, -1), slice(None), slice(1, None), slice(None), G_r),
                (slice(None), slice(None, -1), slice(None), slice(1, None), G_z)):
            ca, cb = cond[ia, ja], cond[ib, jb]
            va, vb = V[ia, ja], V[ib, jb]
            q += float(np.sum(G[(ca == 2) & (cb == 0)] * (va - vb)[(ca == 2) & (cb == 0)]))
            q += float(np.sum(G[(cb == 2) & (ca == 0)] * (vb - va)[(cb == 2) & (ca == 0)]))
        out[mode] = dict(q=q, V=V if keep else None)
        if mode == "anti":
            out["E_centre_per_Vdiff"] = float(V[0, 0] / (0.5 * hm)) / 2.0           # V/m per volt of A - B
            out["Ez_axis_per_Vdiff"] = (V[0, :] / (zc + 1e-30) / 2.0).tolist()       # mean field from the centre
            out["Ez_mid_per_Vdiff"] = (V[:, 0] / (0.5 * hm) / 2.0).tolist()         # in the midplane, along r
    c_ref = out["sym"]["q"]
    c_rr = 0.5 * (out["anti"]["q"] - out["sym"]["q"])
    res = dict(theta_deg=theta, ring=ring, coils=coils, h_mm=h, C_ring_ref_pF=c_ref * 1e12, C_ring_ring_pF=c_rr * 1e12,
               E_centre_kV_cm_per_kV=out["E_centre_per_Vdiff"] * 1e-2 / 1e3 * 1e3,   # (V/m)/V -> (kV/cm)/kV
               r_mm=r.tolist(), z_mm=z.tolist())
    res["Ez_axis_kV_cm_per_kV"] = [v * 1e-2 for v in out["Ez_axis_per_Vdiff"]]
    res["Ez_mid_kV_cm_per_kV"] = [v * 1e-2 for v in out["Ez_mid_per_Vdiff"]]
    if keep:
        res["V_anti"] = out["anti"]["V"]
        res["cond"] = cond
        res["eps"] = eps
    return res


def _solve_case(args):
    name, theta, coils, h = args
    t0 = time.time()
    q = solve(RINGS[name], theta, coils, h)
    q["ring_name"] = name
    q["solve_s"] = time.time() - t0
    for k in ("r_mm", "z_mm", "Ez_axis_kV_cm_per_kV", "Ez_mid_kV_cm_per_kV"):
        q.pop(k)
    return q


def pump(c_ref_pF, c_rr_pF, name):
    """the stack of record with the float wiring and these strays: the gain (free) and the clamped steady state."""
    CF.C_CONE, CF.C_CC = c_ref_pF * 1e-12, c_rr_pF * 1e-12
    fr = CF.run((f"{name} free", dict(opt="float", clamp=False, n_cyc=12, v0=-10.0)))
    cl = CF.run((name, dict(opt="float", n_cyc=24)))
    return dict(z=fr.get("z"), P_belt_W=cl.get("P_belt_W"), swing_pk_kV=cl.get("swing_pk_kV"),
                cone_swing_kV=cl.get("cone_swing_kV"))


def _pump_case(args):
    c_ref, c_rr, name = args
    return name, c_ref, c_rr, pump(c_ref, c_rr, name)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--h", type=float, default=0.25)
    ap.add_argument("--procs", type=int, default=4)
    a = ap.parse_args()
    # 1. the rings: field and strays over the polar angle, the ring's form, and the coils present or not
    cases = [(nm, th, co, a.h) for nm in RINGS for th in THETAS for co in (True, False)]
    with Pool(a.procs) as pool:
        rings = list(pool.imap(_solve_case, cases))
    for q in rings:
        print(f"{q['ring_name']:10s} theta {q['theta_deg']:4.0f} coils {q['coils']!s:5s}: C_ref {q['C_ring_ref_pF']:6.2f} pF "
              f"C_rr {q['C_ring_ring_pF']:6.2f} pF  E0 {q['E_centre_kV_cm_per_kV']:.4f} (kV/cm)/kV  ({q['solve_s']:.0f} s)",
              flush=True)
    # convergence: the 2 mm wire at 40 deg with coils, at half the grid
    conv = solve(RINGS["wire 2 mm"], 40.0, True, 2 * a.h)
    for k in ("r_mm", "z_mm", "Ez_axis_kV_cm_per_kV", "Ez_mid_kV_cm_per_kV"):
        conv.pop(k)
    # 2. the pump's budget for strays (geometry-free) and 3. the pump with each ring case's strays
    budget = [(cr, cc, f"budget {cr:g} {cc:g}") for cr in (0.0, 2.0, 5.0, 10.0, 20.0) for cc in (0.0, 2.0, 5.0, 10.0)]
    ring_cases = [(q["C_ring_ref_pF"], q["C_ring_ring_pF"], f"ring {q['ring_name']} {q['theta_deg']:g} {q['coils']}")
                  for q in rings]
    with Pool(a.procs) as pool:
        pumped = {nm: dict(C_ref_pF=cr, C_rr_pF=cc, **p) for nm, cr, cc, p in pool.imap(_pump_case, budget + ring_cases)}
    for q in rings:
        q["pump"] = pumped[f"ring {q['ring_name']} {q['theta_deg']:g} {q['coils']}"]
        q["E_centre_kV_cm"] = q["E_centre_kV_cm_per_kV"] * (q["pump"]["swing_pk_kV"] or 0.0)
    out = dict(hub=HUB, rings_def=RINGS, h_mm=a.h, rings=rings, convergence_h2=conv,
               budget=[pumped[nm] for _, _, nm in budget], design=CF.Q["C_min_pF"], note="see the module docstring")
    json.dump(out, open(os.path.join(HERE, "core_rings_results.json"), "w"), indent=1, default=float)
    for q in rings:
        p = q["pump"]
        print(f"{q['ring_name']:10s} {q['theta_deg']:4.0f} coils {q['coils']!s:5s}: z {p['z']:.3f} P {p['P_belt_W']:.2f} W "
              f"swing {p['swing_pk_kV']:.2f} kV -> E0 {q['E_centre_kV_cm']:.2f} kV/cm")


if __name__ == "__main__":
    main()
