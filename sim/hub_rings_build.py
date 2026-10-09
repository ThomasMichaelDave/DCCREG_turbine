"""sim/hub_rings_build.py -- building the rings of record (sim/hub_locked.py): the retainer, the rings' edges, the
leakage and the number of multiplier stages the rings' separation can hold.

The designer's brief (2026-10-09):
  1. a current-day machinable retainer that minimally affects both fields;
  2. the prototype's rings are copper foil with rounded edges (a fired-on coating later);
  3. the rings' leakage (the designer cannot judge it);
  4. a bench test; and: multiplier stages may be added as long as the rings' separation holds them.
What is solved here [OC unless tagged]:
  retainer   the field at the null and the rings' strays against the retainer's permittivity, with a 0.5 mm interface
             filler (silicone gel, eps 2.9 [IR]) between the glass and the retainer and a G10 coupler (eps 4.7) outside;
  edges      the peak field at a copper foil's rounded edge (a bead of radius rho_e on a 0.1 mm foil), by a fine local
             finite-volume solve (0.025 mm cells) bounded by the hub's solution: both edges of ring B, the record's
             DC; extrapolated to the surface from 2 and 4 cells out;
  leakage    a ledger of each ring's leakage paths from the parts [IR datasheet-class / RH];
  stages     ring B on 1-6 Cockcroft-Walton stages (ngspice, 100 pF, the leakage estimate) and, for each, the bands
             sized so the gap along the glass holds the DC at the interface rating (1 and 2 kV/mm) and ring B clears
             the AH (5 kV/mm average); the field at the null for each;
  the edges  set the bands (phase 5): every supply -- ring B's chain alone, or both rings' chains (ring A on 1-2
             negative stages, sim/core_field.py n_cw_a) -- at each pair of ratings (the interface along the glass;
             the gel at a bead: 1 / 5 the design, 2 / 8 to qualify): the equatorial edge where the gap holds the DC,
             the polar edge the nearest the pole where its bead holds against the AH coil's end, the smallest
             equatorial bead that holds; from tables of the field at the null and of both edges, solved per mode and
             superposed per supply; the best of each pair solved again directly. The record: the best at 1 / 5;
             its beads' local solve checked with the cell halved and the box enlarged; its supply run in full.
Inputs from presets/hub-locked.json: the retainer system, the foil, the ratings, the leakage estimate.
Usage: python3 sim/hub_rings_build.py [--procs 4] [--resume]   (writes sim/hub_rings_build_results.json; --resume keeps
       phases 1-4 from it)
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
import core_field as CF            # noqa: E402
import core_rings as CR            # noqa: E402
import hub_locked as HL            # noqa: E402

EPS0 = 8.8541878128e-12
# the retainer system proposed [IR datasheet-class] (presets/hub-locked.json retainer, interface_filler, shaft_coupler):
# unfilled PEEK machined with a 0.5 mm pocket over the glass, the pocket filled void-free with silicone gel; G10 outside
SYSTEM = dict(eps_ret=HL.V("retainer")["eps_r"], cpl_t=HL.V("shaft_coupler")["wall_mm"],
              eps_cpl=HL.V("shaft_coupler")["eps_r"], fill_t=HL.V("interface_filler")["t_mm"],
              eps_fill=HL.V("interface_filler")["eps_r"])
EPS_SWEEP = (1.0, 2.1, 2.6, 3.0, 3.2, 3.6, 4.7, 6.0, 9.8)
FOIL_T = HL.V("rings")["foil_t_mm"]           # mm, the prototype's copper foil [RH]
EDGE_R = (0.25, 0.5, 1.0, 1.5)                 # mm, the rounded edges' radius
_RAT = HL.V("ratings")
E_FILL_DESIGN = _RAT["gel_at_bead_kV_mm"]      # kV/mm, a void-free silicone gel's DC design field at a bead [RH]
R_LEAK_EST = HL.V("rings_leakage")["R_ohm_per_ring"]   # ohm per ring, the leakage estimate (the ledger below) [RH]
STAGES = (1, 2, 3, 4, 5, 6)
E_T = (_RAT["interface_kV_mm"], _RAT["to_qualify"]["interface_kV_mm"])   # kV/mm along the glass: design, to qualify


def hub_system():
    return dict(HL.HUB, **SYSTEM)


# ----------------------------------------------------------------------------------- 1. the retainer's permittivity
def _eps_case(args):
    eps_ret, rec = args
    hub = dict(hub_system(), eps_ret=eps_ret)
    q = CR.solve(HL.band(rec["theta_p"], rec["theta_e"]), 0.5 * (rec["theta_p"] + rec["theta_e"]), True, 0.25, hub=hub,
                 maps_fn=HL.maps)
    return dict(eps_ret=eps_ret, k_kV_cm_per_kV=q["E_centre_kV_cm_per_kV"], C_ring_ref_pF=q["C_ring_ref_pF"],
                C_ring_ring_pF=q["C_ring_ring_pF"])


# ----------------------------------------------------------------------------------- 2. the edges: a local solve
def local_fv(eps, cond, vfix, h, r0, z0, vbc):
    """axisymmetric finite volumes on a box of cells (nr, nz) from (r0, z0), cell h (mm): eps at the cells, cond the
    conductor cells (held at vfix), vbc(r, z) the potential on the box's edges (Dirichlet half a cell out). V (V)."""
    nr, nz = eps.shape
    hm = h * 1e-3
    rc = (r0 + (np.arange(nr) + 0.5) * h) * 1e-3
    zc = (z0 + (np.arange(nz) + 0.5) * h) * 1e-3
    free = ~cond
    idx = -np.ones((nr, nz), dtype=np.int64)
    idx[free] = np.arange(int(free.sum()))
    n = int(free.sum())
    diag, rhs = np.zeros(n), np.zeros(n)
    rows, cols, vals = [], [], []
    Vfix = np.where(cond, vfix, 0.0)

    def couple(ia, ja, ib, jb, G):
        fa, fb = free[ia, ja], free[ib, jb]
        a, b = idx[ia, ja], idx[ib, jb]
        both = fa & fb
        np.add.at(diag, a[fa], G[fa]); np.add.at(diag, b[fb], G[fb])
        rows.append(a[both]); cols.append(b[both]); vals.append(-G[both])
        rows.append(b[both]); cols.append(a[both]); vals.append(-G[both])
        m1, m2 = fa & ~fb, fb & ~fa
        np.add.at(rhs, a[m1], G[m1] * Vfix[ib, jb][m1]); np.add.at(rhs, b[m2], G[m2] * Vfix[ia, ja][m2])
    ef = 2 * eps[:-1, :] * eps[1:, :] / (eps[:-1, :] + eps[1:, :])
    rf = (r0 + np.arange(1, nr) * h) * 1e-3
    I, J = np.meshgrid(np.arange(nr - 1), np.arange(nz), indexing="ij")
    couple(I, J, I + 1, J, 2 * math.pi * EPS0 * ef * rf[:, None])
    ef = 2 * eps[:, :-1] * eps[:, 1:] / (eps[:, :-1] + eps[:, 1:])
    I, J = np.meshgrid(np.arange(nr), np.arange(nz - 1), indexing="ij")
    couple(I, J, I, J + 1, 2 * math.pi * EPS0 * ef * rc[:, None])
    # the box's four edges, Dirichlet from the hub's solution
    for side, (ii, jj, G, rr, zz) in {
            "in": (0, slice(None), 2 * math.pi * EPS0 * eps[0, :] * (r0 * 1e-3) * 2, r0, z0 + (np.arange(nz) + 0.5) * h),
            "out": (nr - 1, slice(None), 2 * math.pi * EPS0 * eps[-1, :] * ((r0 + nr * h) * 1e-3) * 2, r0 + nr * h,
                    z0 + (np.arange(nz) + 0.5) * h),
            "bot": (slice(None), 0, 2 * math.pi * EPS0 * eps[:, 0] * rc * 2, r0 + (np.arange(nr) + 0.5) * h, z0),
            "top": (slice(None), nz - 1, 2 * math.pi * EPS0 * eps[:, -1] * rc * 2, r0 + (np.arange(nr) + 0.5) * h,
                    z0 + nz * h)}.items():
        f = free[ii, jj]
        vb = vbc(np.broadcast_to(rr, np.shape(G)), np.broadcast_to(zz, np.shape(G)))
        np.add.at(diag, idx[ii, jj][f], G[f])
        np.add.at(rhs, idx[ii, jj][f], (G * vb)[f])
    A = sp.csr_matrix((np.concatenate(vals + [diag]), (np.concatenate(rows + [np.arange(n)]),
                                                       np.concatenate(cols + [np.arange(n)]))), shape=(n, n))
    V = Vfix.copy()
    V[free] = spla.spsolve(A.tocsc(), rhs)
    return V


def hub_potential(res, va, vb):
    """the hub's potential (V) on its half-domain grid for ring A at va (lower) and ring B at vb (upper), and an
    interpolator in (r, z) mm, z >= 0."""
    cm, dm = 0.5 * (vb + va), 0.5 * (vb - va)
    V = cm * res["V_sym"] + dm * res["V_anti"]
    h = res["h_mm"]
    nr, nz = V.shape

    def at(r, z):
        x = np.clip(np.asarray(r) / h - 0.5, 0, nr - 1.001)
        y = np.clip(np.asarray(z) / h - 0.5, 0, nz - 1.001)
        i, j = np.floor(x).astype(int), np.floor(y).astype(int)
        u, w = x - i, y - j
        return ((1 - u) * (1 - w) * V[i, j] + u * (1 - w) * V[i + 1, j] + (1 - u) * w * V[i, j + 1] + u * w * V[i + 1, j + 1])
    return V, at


def hub_beads(tp, te, rho_e):
    """the hub's solution (both modes) with a bead of radius rho_e at each band edge (coarse): the local boxes' edges."""
    return CR.solve(HL.band(tp, te), 0.5 * (tp + te), True, 0.25, hub=hub_system(), keep=True,
                    maps_fn=lambda ring, theta, coils, h, hub_: maps_beads(ring, theta, coils, h, hub_, rho_e))


def _edge_box(tp, te, rho_e, which, h_loc, half):
    """the local box around ring B's bead ('eq' or 'pol'): its cells' eps, the conductor (foil and bead) and the
    normals out of the bead, each with its two sample points (2 and 4 cells out) and its material."""
    hub = hub_system()
    th = math.radians(te if which == "eq" else tp)
    cx, cz = (hub["R_v"] + rho_e) * math.sin(th), (hub["R_v"] + rho_e) * math.cos(th)    # the bead's centre
    r0, z0 = cx - half, cz - half
    n = int(round(2 * half / h_loc))
    r = r0 + (np.arange(n) + 0.5) * h_loc
    z = z0 + (np.arange(n) + 0.5) * h_loc
    R, Z = np.meshgrid(r, z, indexing="ij")
    rho = np.hypot(R, Z)
    pol = np.degrees(np.arctan2(R, Z))
    eps = np.full((n, n), hub["eps_ret"])
    eps[(rho >= hub["R_v"]) & (rho < hub["R_v"] + max(hub["fill_t"], 2 * rho_e + 0.5))] = hub["eps_fill"]
    eps[(rho >= hub["R_in"]) & (rho < hub["R_v"])] = hub["eps_glass"]
    eps[rho < hub["R_in"]] = 1.0
    cond = (rho >= hub["R_v"]) & (rho <= hub["R_v"] + FOIL_T) & (pol >= tp) & (pol <= te)
    cond |= np.hypot(R - cx, Z - cz) <= rho_e
    normals = []
    for a in np.linspace(0, 2 * math.pi, 721)[:-1]:
        nx, nzv = math.sin(a), math.cos(a)
        sx, sz = cx + rho_e * nx, cz + rho_e * nzv                        # on the bead's surface
        p2 = (sx + 2 * h_loc * nx, sz + 2 * h_loc * nzv)
        p4 = (sx + 4 * h_loc * nx, sz + 4 * h_loc * nzv)
        if min(np.hypot(p2[0] - cx, p2[1] - cz), np.hypot(p4[0] - cx, p4[1] - cz)) <= rho_e:
            continue
        # skip normals that run into the foil or out of the box
        if not (r0 + 6 * h_loc < p4[0] < r0 + 2 * half - 6 * h_loc and z0 + 6 * h_loc < p4[1] < z0 + 2 * half - 6 * h_loc):
            continue
        rho4 = math.hypot(*p4)
        pol4 = math.degrees(math.atan2(*p4))
        if hub["R_v"] <= rho4 <= hub["R_v"] + FOIL_T + 2 * h_loc and tp <= pol4 <= te:
            continue
        rho2 = math.hypot(*p2)
        if rho2 >= hub["R_v"] and rho4 >= hub["R_v"]:
            where = "filler"
        elif rho2 < hub["R_v"] and rho4 < hub["R_v"]:
            where = "glass"
        else:                                                           # straddles the glass: the contact wedge
            continue
        normals.append((a, sx, sz, p2, p4, where))
    return dict(r0=r0, z0=z0, n=n, eps=eps, cond=cond, normals=normals)


def _bilin(F, x, y, r0, z0, h):
    """F (cells of a box from (r0, z0), cell h) at the point (x, y), bilinear."""
    u, w = (x - r0) / h - 0.5, (y - z0) / h - 0.5
    i, j = int(u), int(w)
    u, w = u - i, w - j
    return (1 - u) * (1 - w) * F[i, j] + u * (1 - w) * F[i + 1, j] + (1 - u) * w * F[i, j + 1] + u * w * F[i + 1, j + 1]


def edge_peak(rec, rho_e, which, h_loc=0.025, half=4.0):
    """the peak field (kV/mm) at ring B's rounded edge ('eq' toward the equator, 'pol' toward the pole), in the filler
    and in the glass, for the record's DC; the foil FOIL_T thick, the edge a bead of radius rho_e on the glass."""
    tp, te = rec["theta_p"], rec["theta_e"]
    # the hub's solution with the bead in it (coarse), for the box's edges
    res = hub_beads(tp, te, rho_e)
    _, vbc = hub_potential(res, rec["V_A_kV"] * 1e3, rec["V_B_kV"] * 1e3)
    bx = _edge_box(tp, te, rho_e, which, h_loc, half)
    r0, z0 = bx["r0"], bx["z0"]
    V = local_fv(bx["eps"], bx["cond"], rec["V_B_kV"] * 1e3, h_loc, r0, z0, vbc)
    # the field at the cells, then sampled along normals out of the bead at 2 and 4 cells, extrapolated to its surface
    Er = np.gradient(V, h_loc * 1e-3, axis=0)
    Ez = np.gradient(V, h_loc * 1e-3, axis=1)
    Em = np.hypot(Er, Ez) / 1e6                                         # kV/mm
    out = {"filler": (0.0, None), "glass": (0.0, None)}
    for a, sx, sz, p2, p4, where in bx["normals"]:
        e0 = 2 * _bilin(Em, *p2, r0, z0, h_loc) - _bilin(Em, *p4, r0, z0, h_loc)
        if e0 > out[where][0]:
            out[where] = (float(e0), dict(r_mm=float(sx), z_mm=float(sz), normal_deg=float(math.degrees(a))))
    return dict(edge=which, rho_e_mm=rho_e, E_filler_kV_mm=out["filler"][0], at_filler=out["filler"][1],
                E_glass_kV_mm=out["glass"][0], at_glass=out["glass"][1], h_loc_mm=h_loc, box_half_mm=half)


def maps_beads(ring, theta, coils, h, hub, rho_e):
    """the hub's maps with a bead of radius rho_e at both edges of each band (for the local solves' boundaries)."""
    r, z, eps, cond = HL.maps(ring, theta, coils, h, hub)
    R, Z = np.meshgrid(r, z, indexing="ij")
    for t in (ring["p"], ring["e"]):
        cx, cz = (hub["R_v"] + rho_e) * math.sin(math.radians(t)), (hub["R_v"] + rho_e) * math.cos(math.radians(t))
        cond[(np.hypot(R - cx, Z - cz) <= max(rho_e, 0.5 * h)) & (cond == 0)] = 2
    return r, z, eps, cond


def _edge_case(args):
    rec, rho_e, which = args
    return edge_peak(rec, rho_e, which)


# ----------------------------------------------------------------------------------- 3. the leakage ledger
LEAKAGE = [  # (path, resistance per ring [ohm], basis) at the record's DC
    ("through the PEEK retainer and seat to the AH core", 5e14,
     "rho about 1e14 ohm m [IR], 7 mm over about 14 cm2 of band"),
    ("along the glass to the other ring", 1.6e15, "borosilicate 1e13 ohm m [IR], the 1.5 mm shell across the 32 mm gap"),
    ("through the silicone gel along the interface", 1e15, "rho about 1e13 ohm m [IR], 0.5 mm x 32 mm across the band"),
    ("the lead: PTFE-insulated wire to the rotor's pump, about 0.3 m", 1e15, "insulation resistance [IR]"),
    ("the multiplier's diodes in reverse (2 per stage, about 7 kV each)", 3e11,
     "a 20 kV stack leaks tens of nA at a third of its rating [IR datasheet-class]; per stage, as a load on ring B"),
    ("the multiplier's 100 pF ceramic capacitors' insulation", 5e11, "IR above 1e11 ohm each [IR]; per stage"),
    ("surface leakage of the rotor's HV assembly (potted)", 1e12, "potted, dry [RH]; humid unpotted surfaces 1e10 or less"),
]


def leak_total():
    g = sum(1.0 / r for _, r, _ in LEAKAGE)
    return 1.0 / g


# ----------------------------------------------------------------------------------- 4. the stages
def _stage_run(args):
    n, r_leak = args[:2]
    n_a = args[2] if len(args) > 2 else 0                               # ring A's negative stages (the balanced supply)
    a_ref = args[3] if len(args) > 3 else "dk"                          # "shaft": ring A's chain from the shaft (mirror)
    t0 = time.time()
    nm = (f"A{n_a}{'s' if a_ref == 'shaft' else ''} " if n_a else "")
    kw = dict(opt="dc", n_cw=n, n_cw_a=n_a, c_core=0.1e-9, c_cw=0.1e-9, r_leak=r_leak,
              **({"a_ref": a_ref} if a_ref != "dk" else {}))
    r = CF.run((f"rings {nm}B{n} {r_leak:.0e}", dict(kw, n_cyc=120 + 80 * max(n, n_a), steps=5000)))
    fr = CF.run((f"free rings {nm}B{n} {r_leak:.0e}", dict(kw, clamp=False, n_cyc=12, v0=-10.0)))
    return dict(n_a=n_a, n_cw=n, r_leak=r_leak, **({"a_ref": a_ref} if a_ref != "dk" else {}),
                V_A_kV=r["V_ea_kV"]["mean"], V_B_kV=r["V_eb_kV"]["mean"],
                ripple_B_V=r["V_eb_kV"]["pp"] * 1e3, ripple_A_V=r["V_ea_kV"]["pp"] * 1e3, z_start=fr.get("z"),
                P_belt_W=r["P_belt_W"], P_leak_W=r["P_leak_W"], VR_pk_kV=r["VR_pk_kV"],
                settled=bool(abs(r["Vk_per_cycle_kV"][-1] - r["Vk_per_cycle_kV"][-10]) < 0.003 * abs(r["Vk_per_cycle_kV"][-1])),
                run_s=time.time() - t0)


def size_bands(v_a, v_b, e_t, hub=None, e_bulk=HL.E_BULK, h=0.25):
    """the widest bands the DC allows: the equatorial edge where the gap holds V at e_t along the glass, the polar edge
    where the higher ring clears the AH at e_bulk (never below 20 deg); the field at the null."""
    hub = hub or hub_system()
    vg = (v_b - v_a) / 1e3
    te = 90.0 - math.degrees(vg / e_t / (2 * hub["R_v"]))
    vmax = max(abs(v_a), abs(v_b)) / 1e3
    tp = 20.0
    while HL.ah_clearance_mm(tp) * e_bulk < vmax and tp < te - 5:
        tp += 0.5
    if te - tp < 5.0:
        return dict(theta_p=tp, theta_e=te, feasible=False, V_gap_kV=vg)
    q = CR.solve(HL.band(tp, te), 0.5 * (tp + te), True, h, hub=hub, maps_fn=HL.maps)
    k = q["E_centre_kV_cm_per_kV"]
    return dict(theta_p=tp, theta_e=te, feasible=True, V_gap_kV=vg, k_kV_cm_per_kV=k, E_null_kV_cm=k * vg,
                p_null_Pa=0.5 * EPS0 * (k * vg * 1e5) ** 2, gap_mm=2 * hub["R_v"] * math.radians(90 - te),
                E_ah_kV_mm=vmax / HL.ah_clearance_mm(tp), C_ring_ref_pF=q["C_ring_ref_pF"],
                C_ring_ring_pF=q["C_ring_ring_pF"])


def _size_case(args):
    st, e_t = args
    return dict(st, E_t_kV_mm=e_t, **size_bands(st["V_A_kV"] * 1e3, st["V_B_kV"] * 1e3, e_t))


# ----------------------------------------------------------------------------------- 5. the edges set the bands
# Each edge's field is linear in the hub's two modes. With the hub's solution split as V = cm V_sym + dm V_anti (the
# rings at cm +- dm), the box around ring B's bead is solved once per mode (the bead at 1 V, the box's edges from that
# mode); a supply superposes the two, and ring A's edge is the mirror (cm, -dm) [OC]. The bands' edges then follow from
# three limits: the gap along the glass at the interface rating, and both beads at the gel's rating.
SUPPLIES_AB = [(1, n) for n in range(1, 7)] + [(2, n) for n in range(2, 7)]   # (A's negative stages, B's stages)
TAB_TP = (20.0, 25.0, 30.0, 35.0, 40.0, 45.0)
TAB_TE = (35.0, 40.0, 45.0, 50.0, 55.0, 60.0, 65.0, 70.0, 75.0, 80.0)
POL_TE = (40.0, 50.0, 60.0, 70.0, 80.0)      # the polar edges' table: TAB_TP x these
EQ_TP = (25.0, 40.0)                         # the equatorial edges' table: these x TAB_TE
RHO_POL = (1.0, 1.5)                         # mm, the beads tried at the polar edge
RHO_EQ = (1.0, 1.5, 2.0)                     # mm, at the equatorial edge
E_GEL = (E_FILL_DESIGN, _RAT["to_qualify"]["gel_at_bead_kV_mm"])   # kV/mm in the gel at a bead: design, to qualify


def edge_basis(args):
    """ring B's edge ('eq' / 'pol') of the bands (tp, te) with beads of rho_e: the field along each normal out of the
    bead at its two sample points, per volt of each of the hub's two modes (V/m); edge_eval evaluates a supply."""
    tp, te, rho_e, which = args
    h_loc, half = 0.025, 4.0
    res = hub_beads(tp, te, rho_e)
    bx = _edge_box(tp, te, rho_e, which, h_loc, half)
    r0, z0 = bx["r0"], bx["z0"]
    F = {}
    for mode, (va, vb) in (("sym", (1.0, 1.0)), ("anti", (-1.0, 1.0))):
        _, vbc = hub_potential(res, va, vb)
        V = local_fv(bx["eps"], bx["cond"], 1.0, h_loc, r0, z0, vbc)
        Er = np.gradient(V, h_loc * 1e-3, axis=0)
        Ez = np.gradient(V, h_loc * 1e-3, axis=1)
        F[mode] = np.array([[[_bilin(Er, *pt, r0, z0, h_loc), _bilin(Ez, *pt, r0, z0, h_loc)] for pt in (p2, p4)]
                            for _, _, _, p2, p4, _ in bx["normals"]])           # (normals, 2 points, 2 components)
    return dict(theta_p=tp, theta_e=te, rho_e_mm=rho_e, edge=which, sym=F["sym"], anti=F["anti"],
                gel=np.array([w == "filler" for *_, w in bx["normals"]]),
                at=np.array([(sx, sz, math.degrees(a)) for a, sx, sz, *_ in bx["normals"]]))


def edge_eval(b, v_a, v_b):
    """the peak field (kV/mm) in the gel and in the glass at an edge basis b, for ring A at v_a and ring B at v_b (kV):
    ring B direct, ring A by the mirror; extrapolated to the bead's surface from the two sample points."""
    cm, dm = 0.5 * (v_b + v_a) * 1e3, 0.5 * (v_b - v_a) * 1e3
    rings = {}
    for ring, d in (("B", dm), ("A", -dm)):
        E = cm * b["sym"] + d * b["anti"]
        m = np.hypot(E[..., 0], E[..., 1]) / 1e6
        e0 = 2 * m[:, 0] - m[:, 1]
        ig, il = int(np.argmax(np.where(b["gel"], e0, -1))), int(np.argmax(np.where(b["gel"], -1, e0)))
        rings[ring] = dict(gel=float(e0[ig]), glass=float(e0[il]), at_gel=b["at"][ig].tolist())
    return dict(gel=max(rings["A"]["gel"], rings["B"]["gel"]), glass=max(rings["A"]["glass"], rings["B"]["glass"]),
                rings=rings)


def _k_case(args):
    tp, te = args
    q = CR.solve(HL.band(tp, te), 0.5 * (tp + te), True, 0.25, hub=hub_system(), maps_fn=HL.maps)
    return dict(theta_p=tp, theta_e=te, k_kV_cm_per_kV=q["E_centre_kV_cm_per_kV"], C_ring_ref_pF=q["C_ring_ref_pF"],
                C_ring_ring_pF=q["C_ring_ring_pF"])


def _interp2(xs, ys, f, x, y):
    """f(i, j) on the grid xs x ys, bilinear at (x, y), held at the grid's edges."""
    x, y = min(max(x, xs[0]), xs[-1]), min(max(y, ys[0]), ys[-1])
    i = min(int(np.searchsorted(xs, x, side="right")) - 1, len(xs) - 2)
    j = min(int(np.searchsorted(ys, y, side="right")) - 1, len(ys) - 2)
    u, w = (x - xs[i]) / (xs[i + 1] - xs[i]), (y - ys[j]) / (ys[j + 1] - ys[j])
    return (1 - u) * (1 - w) * f(i, j) + u * (1 - w) * f(i + 1, j) + (1 - u) * w * f(i, j + 1) + u * w * f(i + 1, j + 1)


def design(st, e_t, e_gel, K, POL, EQ):
    """the bands for a supply st at the interface rating e_t and the gel's rating e_gel (kV/mm): the equatorial edge
    where the gap holds the DC at e_t; the polar edge the nearest the pole where its bead (RHO_POL) holds e_gel against
    the AH; the smallest equatorial bead (RHO_EQ) that holds e_gel; the field at the null (all from the tables)."""
    R_v = hub_system()["R_v"]
    v_a, v_b = st["V_A_kV"], st["V_B_kV"]
    vg = v_b - v_a
    te = 90.0 - math.degrees(vg / e_t / (2 * R_v))
    out = dict(n_a=st["n_a"], n_cw=st["n_cw"], **({"a_ref": st["a_ref"]} if st.get("a_ref", "dk") != "dk" else {}),
               V_A_kV=v_a, V_B_kV=v_b, V_gap_kV=vg, E_t_kV_mm=e_t, E_gel_kV_mm=e_gel, theta_e=te,
               gap_mm=2 * R_v * math.radians(90.0 - te), feasible=False)
    if te < TAB_TE[0]:
        return dict(out, why="the gap leaves no band")
    tp_best = rho_p = None
    for rho in RHO_POL:
        for tp in np.arange(TAB_TP[0], TAB_TP[-1] + 1e-9, 0.25):
            pk = _interp2(TAB_TP, POL_TE, lambda i, j: edge_eval(POL[(TAB_TP[i], POL_TE[j], rho)], v_a, v_b)["gel"],
                          tp, te)
            if pk <= e_gel:
                if tp_best is None or tp < tp_best:
                    tp_best, rho_p = float(tp), rho
                break
    if tp_best is None:
        return dict(out, why="the polar bead does not hold")
    out.update(theta_p=tp_best, rho_pol_mm=rho_p)
    if te - tp_best < 5.0:
        return dict(out, why="no room for the band")
    for rho in RHO_EQ:
        pk = _interp2(EQ_TP, TAB_TE, lambda i, j: edge_eval(EQ[(EQ_TP[i], TAB_TE[j], rho)], v_a, v_b)["gel"],
                      tp_best, te)
        if pk <= e_gel:
            k = _interp2(TAB_TP, TAB_TE, lambda i, j: K[(TAB_TP[i], TAB_TE[j])]["k_kV_cm_per_kV"], tp_best, te)
            return dict(out, feasible=True, rho_eq_mm=rho, k_kV_cm_per_kV=k, E_null_kV_cm=k * vg,
                        p_null_Pa=0.5 * EPS0 * (k * vg * 1e5) ** 2)
    return dict(out, why="the equatorial bead does not hold")


def _verify(args):
    """a design solved directly: both beads at their edges, the null field at its bands; the polar edge stepped out
    0.5 deg, or the equatorial bead up a size, until the direct solve holds too."""
    d, e_gel = args
    d = dict(d)
    for _ in range(20):
        pol = edge_eval(edge_basis((d["theta_p"], d["theta_e"], d["rho_pol_mm"], "pol")), d["V_A_kV"], d["V_B_kV"])
        if pol["gel"] <= e_gel or d["theta_e"] - d["theta_p"] < 5.5:
            break
        d["theta_p"] += 0.5
    for _ in range(4):
        eq = edge_eval(edge_basis((d["theta_p"], d["theta_e"], d["rho_eq_mm"], "eq")), d["V_A_kV"], d["V_B_kV"])
        if eq["gel"] <= e_gel or d["rho_eq_mm"] >= RHO_EQ[-1] + 0.5:
            break
        d["rho_eq_mm"] += 0.5
    k = _k_case((d["theta_p"], d["theta_e"]))
    vg = d["V_gap_kV"]
    e = k["k_kV_cm_per_kV"] * vg
    hold = bool(pol["gel"] <= e_gel and eq["gel"] <= e_gel)
    return dict(d, verified=hold, E_pol=pol, E_eq=eq, k_kV_cm_per_kV=k["k_kV_cm_per_kV"], E_null_kV_cm=e,
                p_null_Pa=0.5 * EPS0 * (e * 1e5) ** 2, C_ring_ref_pF=k["C_ring_ref_pF"], C_ring_ring_pF=k["C_ring_ring_pF"],
                E_ah_kV_mm=max(abs(d["V_A_kV"]), abs(d["V_B_kV"])) / HL.ah_clearance_mm(d["theta_p"]))


def _conv_case(args):
    d, rho_e, which, h_loc, half = args
    q = edge_peak(d, rho_e, which, h_loc=h_loc, half=half)
    return dict(edge=which, rho_e_mm=rho_e, h_loc_mm=h_loc, box_half_mm=half, E_gel_kV_mm=q["E_filler_kV_mm"],
                E_glass_kV_mm=q["E_glass_kV_mm"])


def phase5(stages, procs, rec):
    """the tables, every supply's design at each pair of ratings, and the best of each pair solved directly."""
    t0 = time.time()
    est = [dict(q, n_a=q.get("n_a", 0)) for q in stages if q["r_leak"] == R_LEAK_EST]
    kjobs = [(tp, te) for tp in TAB_TP for te in TAB_TE]
    pjobs = [(tp, te, r, "pol") for tp in TAB_TP for te in POL_TE for r in RHO_POL]
    ejobs = [(tp, te, r, "eq") for tp in EQ_TP for te in TAB_TE for r in RHO_EQ]
    with Pool(procs) as pool:
        K = {(q["theta_p"], q["theta_e"]): q for q in pool.imap(_k_case, kjobs)}
        POL = {(b["theta_p"], b["theta_e"], b["rho_e_mm"]): b for b in pool.imap(edge_basis, pjobs)}
        EQ = {(b["theta_p"], b["theta_e"], b["rho_e_mm"]): b for b in pool.imap(edge_basis, ejobs)}
    print(f"tables: {len(K)} fields, {len(POL)} polar and {len(EQ)} equatorial edges ({time.time() - t0:.0f} s)", flush=True)
    designs = [design(st, e_t, e_g, K, POL, EQ) for e_t in E_T for e_g in E_GEL for st in est]
    best = {}
    for e_t in E_T:
        for e_g in E_GEL:
            ok = [q for q in designs if q["E_t_kV_mm"] == e_t and q["E_gel_kV_mm"] == e_g and q["feasible"]]
            if ok:
                best[f"{e_t:g}/{e_g:g}"] = max(ok, key=lambda q: q["E_null_kV_cm"])
    with Pool(procs) as pool:
        ver = list(pool.imap(_verify, [(b, b["E_gel_kV_mm"]) for b in best.values()]))
    best_v = dict(zip(best, ver))
    tables = dict(k=list(K.values()),
                  polar_at_record=[dict(theta_p=k_[0], theta_e=k_[1], rho_e_mm=k_[2],
                                        **edge_eval(b, rec["V_A_kV"], rec["V_B_kV"])) for k_, b in POL.items()])
    return designs, best_v, tables, time.time() - t0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--procs", type=int, default=4)
    ap.add_argument("--resume", action="store_true", help="keep phases 1-4 from the results file")
    a = ap.parse_args()
    t0 = time.time()
    rec = json.load(open(os.path.join(HERE, "hub_locked_results.json")))["record"]
    path = os.path.join(HERE, "hub_rings_build_results.json")
    if a.resume:
        out = json.load(open(path))
        out.pop("edge_convergence", None)                              # superseded by the record's convergence below
    else:
        with Pool(a.procs) as pool:
            eps = list(pool.imap(_eps_case, [(e, rec) for e in EPS_SWEEP]))
            edges = list(pool.imap(_edge_case, [(rec, r_e, w) for w in ("eq", "pol") for r_e in EDGE_R]))
        for q in eps:
            print(f"eps_ret {q['eps_ret']:4.1f}: k {q['k_kV_cm_per_kV']:.4f} (kV/cm)/kV, C_ref {q['C_ring_ref_pF']:.2f}, "
                  f"C_rr {q['C_ring_ring_pF']:.2f} pF", flush=True)
        for q in edges:
            print(f"edge {q['edge']:3s} rho {q['rho_e_mm']:.2f} mm: filler {q['E_filler_kV_mm']:.2f}, glass "
                  f"{q['E_glass_kV_mm']:.2f} kV/mm", flush=True)
        r_est = leak_total()
        print(f"leakage per ring, from the ledger: {r_est:.2e} ohm", flush=True)
        runs = [(n, rl) for rl in (10e9, R_LEAK_EST, 1e12) for n in STAGES]
        with Pool(a.procs) as pool:
            stages = list(pool.imap(_stage_run, sorted(runs, key=lambda x: -x[0])))
        stages.sort(key=lambda x: (x["r_leak"], x["n_cw"]))
        for q in stages:
            print(f"B on {q['n_cw']} stages, {q['r_leak']:.0e} ohm: A {q['V_A_kV']:.2f}, B {q['V_B_kV']:.2f} kV, ripple B "
                  f"{q['ripple_B_V']:.0f} V, z {q['z_start']:.3f}, settled {q['settled']}", flush=True)
        est = [q for q in stages if q["r_leak"] == R_LEAK_EST]
        with Pool(a.procs) as pool:
            sized = list(pool.imap(_size_case, [(q, e_t) for e_t in E_T for q in est]))
        for q in sized:
            print(f"E_t {q['E_t_kV_mm']:g}: B{q['n_cw']} {q['V_gap_kV']:.1f} kV -> bands {q['theta_p']:.1f}-"
                  f"{q['theta_e']:.1f}: " + (f"{q['E_null_kV_cm']:.2f} kV/cm, AH {q['E_ah_kV_mm']:.2f} kV/mm"
                                             if q["feasible"] else "no room"), flush=True)
        best = {f"{e_t:g}": max([q for q in sized if q["E_t_kV_mm"] == e_t and q["feasible"]],
                                key=lambda q: q["E_null_kV_cm"]) for e_t in E_T}
        # the edges of the sized designs: ring B's equatorial and polar edges at 1.0 and 1.5 mm, at each design's DC
        jobs = []
        for q in sized:
            if q["feasible"]:
                d = dict(theta_p=q["theta_p"], theta_e=q["theta_e"], V_A_kV=q["V_A_kV"], V_B_kV=q["V_B_kV"])
                jobs += [(d, r_e, w) for r_e in (1.0, 1.5) for w in ("eq", "pol")]
        with Pool(a.procs) as pool:
            sized_edges = list(pool.imap(_edge_case, jobs))
        for (d, r_e, w), q in zip(jobs, sized_edges):
            q.update(theta_p=d["theta_p"], theta_e=d["theta_e"], V_A_kV=d["V_A_kV"], V_B_kV=d["V_B_kV"])
        out = dict(note="see the module docstring", system=SYSTEM, foil_t_mm=FOIL_T, E_fill_design_kV_mm=E_FILL_DESIGN,
                   record_in=rec, eps_sweep=eps, edges=edges,
                   leakage_ledger=[dict(path=p, R_ohm=r, basis=b) for p, r, b in LEAKAGE], leakage_total_ohm=r_est,
                   R_leak_est=R_LEAK_EST, stages=stages, sized=sized, best=best, sized_edges=sized_edges)
        for k, b in best.items():
            print(f"best at {k} kV/mm (the AH average only): B on {b['n_cw']} stages, {b['V_gap_kV']:.1f} kV, bands "
                  f"{b['theta_p']:.1f}-{b['theta_e']:.1f}: {b['E_null_kV_cm']:.2f} kV/cm ({b['p_null_Pa']:.1f} Pa)")
    # the balanced supplies: ring A on negative stages too
    with Pool(a.procs) as pool:
        ab = list(pool.imap(_stage_run, sorted([(n, R_LEAK_EST, n_a) for n_a, n in SUPPLIES_AB], key=lambda x: -x[0])))
    ab.sort(key=lambda x: (x["n_a"], x["n_cw"]))
    for q in ab:
        print(f"A on {q['n_a']}, B on {q['n_cw']} stages: A {q['V_A_kV']:.2f}, B {q['V_B_kV']:.2f} kV, z {q['z_start']:.3f}, "
              f"settled {q['settled']}", flush=True)
    designs, best_v, tables, t5 = phase5(out["stages"] + ab, a.procs, rec)
    for k, b in best_v.items():
        print(f"best at {k} kV/mm: A{b['n_a']} B{b['n_cw']}, {b['V_gap_kV']:.1f} kV, bands {b['theta_p']:.2f}-"
              f"{b['theta_e']:.2f}, beads {b['rho_pol_mm']:.1f} / {b['rho_eq_mm']:.1f} mm: {b['E_null_kV_cm']:.2f} kV/cm "
              f"({b['p_null_Pa']:.2f} Pa); direct: polar {b['E_pol']['gel']:.2f}, eq {b['E_eq']['gel']:.2f} kV/mm, "
              f"verified {b['verified']}", flush=True)
    # the local solve's convergence at the record's beads (ring B, the higher): the cell halved; the box 1.5x
    rb, conv = best_v.get("1/5"), []
    if rb:
        jobs = [(rb, rb["rho_pol_mm"] if w == "pol" else rb["rho_eq_mm"], w, h_, hf) for w in ("pol", "eq")
                for h_, hf in ((0.025, 4.0), (0.0125, 4.0), (0.025, 6.0))]
        with Pool(a.procs) as pool:
            conv = list(pool.imap(_conv_case, jobs))
        for q in conv:
            print(f"convergence, the record's {q['edge']} bead: cell {q['h_loc_mm']} mm, box +-{q['box_half_mm']:g} mm: "
                  f"gel {q['E_gel_kV_mm']:.3f}, glass {q['E_glass_kV_mm']:.3f} kV/mm", flush=True)
    # the record's supply in full (the clamps, the link, the diodes), as sim/core_field.py's cases run
    sup = fr = None
    if rb:
        kw = dict(opt="dc", n_cw=rb["n_cw"], n_cw_a=rb["n_a"], c_core=0.1e-9, c_cw=0.1e-9, r_leak=R_LEAK_EST)
        nm = (f"A{rb['n_a']} " if rb["n_a"] else "") + f"B{rb['n_cw']} {R_LEAK_EST:.0e}"
        with Pool(2) as pool:
            sup, fr = pool.map(CF.run, [(f"record {nm}", dict(kw, n_cyc=120 + 80 * max(rb["n_cw"], rb["n_a"]),
                                                              steps=10000)),
                                        (f"free record {nm}", dict(kw, clamp=False, n_cyc=12, v0=-10.0))])
        print(f"the record's supply: A {sup['V_ea_kV']['mean']:.2f}, B {sup['V_eb_kV']['mean']:.2f} kV, belt "
              f"{sup['P_belt_W']:.3f} W (waves {sup['P_belt_wave_W']:.3f}), z {fr['z']:.3f}", flush=True)
    out.update(stages_ab=ab, supplies_ab=SUPPLIES_AB, E_gel_kV_mm=E_GEL, tables=tables, designs=designs,
               best_edges=best_v, record=best_v.get("1/5"), record_supply=sup, record_supply_free=fr, convergence=conv,
               phase5_s=t5, run_s=time.time() - t0)
    json.dump(out, open(path, "w"), indent=1, default=float)
    print(f"done in {time.time() - t0:.0f} s")


if __name__ == "__main__":
    main()
