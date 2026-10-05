#!/usr/bin/env python3
"""sim/em_ladder.py -- the edge driver generalised for the electromagnet register (BRIEF_ELECTROMAGNET_REGISTER §5.3):
explicit per-turn (r, z) lists, multi-layer windings with their return leads, several windings in one solve with
signed series connection and handedness, the machine's own conductors as returns (no can), and a conducting core per
rod. Built on sim/edge_coil.py's primitives (FV operators, elliptic mutuals, Foster skin, modal core fit); the
single-coil model there is unchanged.                                                                   [OC/IR/ME]

Assemblies (from presets/electromagnets-RA.json; every geometric choice listed in sim/em-register-predictions.md §A):
  ra_assembly(var, stator)  the RA hub: L_TC, L_TA (AH top), join, L_BA, L_BC between R-A and R-B, C_R electrodes,
                            septum, hub shell, formers, rods tied to the join, shafts, vessel, seat; stator foils (i)
                            or none (ii); the stator frame (r 560, |z| 200) as the far grounded boundary
  bench_assembly(...)       one AH coil on its rod in a grounded fixture can (P-EDGE bench)
"""
import json
import math
import os
import sys
import time

import numpy as np
import scipy.linalg as sla
import scipy.sparse as sp
import scipy.sparse.linalg as spla
from scipy.special import ellipe, ellipk

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path[:0] = [HERE]
import edge_coil as EC                                   # noqa: E402
from edge_coil import EPS0, MU0, RHO_CU, axis, fv_laplacian, lap_from_edges, mutual, skin_fit  # noqa: E402


def preset():
    return json.load(open(os.path.join(ROOT, "presets", "electromagnets-RA.json")))


def V(p, k):
    return p["rotor"][k]["value"]


# ======================================================================================================
# 0. closed forms                                                                                     [OC]
# ======================================================================================================
def loop_B(a, r, dz):
    """field (B_r, B_z) per ampere of a circular loop of radius a at (r, dz); SI."""
    r = np.asarray(r, float)
    dz = np.asarray(dz, float)
    q = (a + r) ** 2 + dz ** 2
    m = 4 * a * r / q
    K, E = ellipk(m), ellipe(m)
    d2 = (a - r) ** 2 + dz ** 2
    Bz = MU0 / (2 * math.pi * np.sqrt(q)) * (K + (a * a - r * r - dz * dz) / d2 * E)
    with np.errstate(divide="ignore", invalid="ignore"):
        Br = np.where(r > 1e-12, MU0 * dz / (2 * math.pi * r * np.sqrt(q)) * (-K + (a * a + r * r + dz * dz) / d2 * E), 0.0)
    return Br, Bz


def mk_cap_per_m(Dc, Do, er):
    """Massarini-Kazimierczuk turn-to-turn capacitance per metre of touching enamelled round wires."""
    lnr = math.log(Do / Dc)
    th = math.acos(1 - lnr / er)
    return EPS0 * (er * th / lnr + 1 / math.tan(th / 2) - 1 / math.tan(math.pi / 12))


def twowire_cap_per_m(d, a):
    return math.pi * EPS0 / math.acosh(d / (2 * a))


def straight_L(length, rw):
    return 2e-7 * length * (math.log(2 * length / rw) - 0.75)


# ======================================================================================================
# 1. assemblies                                                                                       [IR]
# ======================================================================================================
class Assembly:
    def __init__(self, name):
        self.name = name
        self.turns = []          # dict(w, r, z, rc, rfd, ins, layer, circ)
        self.leads = {}          # name -> dict(L, R, segs, cross)
        self.cond = []           # dict(name, node, mask)   mask(R, Z) in mm; node 'gnd' or a circuit node
        self.diel = []           # (mask, eps)
        self.rods = []           # dict(z0, z1, r, seg, rho, eps_bulk, tie)
        self.path = []           # chain items
        self.sources = []        # (node, amp)
        self.targets = []        # (name, r_mm, z_mm)
        self.domain = None       # dict(r_max, z_lo, z_hi, fine_r=[(a,b,h)], fine_z=[...], hmax, ms_fine_r, ms_fine_z)
        self.mu = dict(mu_i=2000.0, f_r=2.5e6)
        self.meta = {}

    def add_winding(self, name, rz, rc, rfd, ins, layer, circ):
        ix = []
        for (r, z), L in zip(rz, layer):
            ix.append(len(self.turns))
            self.turns.append(dict(w=name, r=r, z=z, rc=rc, rfd=rfd, ins=ins, layer=L, circ=circ))
        return ix


def ah_turns(var, side, p, n_per_layer=None, layers=None, span_mm=None):
    """AH winding turn list in winding order from the apex end (layer 1 apex -> base, layer 2 back, ...).
    side -1 = top (A, z < 0), +1 = bottom (B). Returns rz (mm), layer index, and the apex/base |z|."""
    w = V(p, "AH_wire")
    fo = V(p, "AH_former")
    var_ = V(p, "AH_variants")[var]
    rod = V(p, "AH_rod")
    nl = layers or var_["layers"]
    npl = n_per_layer or var_["turns_per_layer"]
    pitch = w["overall_mm"]
    z0 = rod["absz_mm"][0] + (0.65 if var == "a" else 0.3)      # (a) 31.35 .. 71.35; (b), (c) from |z| ~31
    if span_mm is not None:                                     # bench sweep: npl turns spread over span
        pitch = span_mm / npl
    zc = z0 + pitch / 2 + pitch * np.arange(npl)               # base -> apex
    rz, lay = [], []
    for L in range(nl):
        rL = fo["od_mm"] / 2 + w["overall_mm"] / 2 + w["overall_mm"] * L
        seq = zc[::-1] if L % 2 == 0 else zc                    # layer 1 from the apex end
        for zz in seq:
            rz.append((rL, side * zz))
            lay.append(L)
    return rz, lay, z0, z0 + npl * pitch, pitch


def ra_assembly(var="a", stator=True, p=None, flip_hands=False):
    p = p or preset()
    A = Assembly(f"RA-{var}-{'stator' if stator else 'nostator'}")
    sep = V(p, "septum")
    hub = V(p, "hub_shell")
    sh = V(p, "shaft")
    ves = V(p, "vessel")
    rod = V(p, "AH_rod")
    fo = V(p, "AH_former")
    w = V(p, "AH_wire")
    var_ = V(p, "AH_variants")[var]
    cone = V(p, "L_TC_L_BC")
    hands = V(p, "AH_hand")
    H = {"RH": +1, "LH": -1}
    fh = -1 if flip_hands else +1
    # C_R electrodes sized to C_R across the septum (parallel plate, full annulus from r 30)
    C_R = V(p, "C_R_pF") * 1e-12
    t_sep = 2 * sep["half_thickness_mm"] * 1e-3
    area = C_R * t_sep / (EPS0 * sep["eps_r"])
    r_e_in = 30.0
    r_e = math.sqrt(area / math.pi + (r_e_in * 1e-3) ** 2) * 1e3
    A.meta.update(r_electrode_mm=r_e, var=var, stator=stator)
    zs = sep["half_thickness_mm"]
    tip = var_["shaft_tip_absz_mm"]
    for s, node in ((-1, "R-A"), (+1, "R-B")):
        A.cond.append(dict(name=f"electrode_{node}", node=node,
                           mask=lambda R, Z, s=s: (R >= r_e_in) & (R <= r_e) & (s * Z >= zs) & (s * Z <= zs + 1.0)))
        if tip >= rod["absz_mm"][1]:                              # (a): shaft out to |z| ~72, PEEK cap 1 mm
            A.cond.append(dict(name=f"shaft_{node}", node=node,
                               mask=lambda R, Z, s=s: (R <= sh["d_mm"] / 2) & (s * Z >= tip + 1.0)))
        else:                                                     # feathered tip with the rod bore
            rb = sh["bore_d_mm"] / 2
            A.cond.append(dict(name=f"shaft_{node}", node=node, mask=lambda R, Z, s=s, rb=rb: (
                ((R <= sh["d_mm"] / 2) & (s * Z >= sh["full_from_absz_mm"]) & ((R > rb) | (s * Z > rod["absz_mm"][1]))) |
                ((R > rb) & (R <= 10.0) & (s * Z >= tip) & (s * Z < sh["full_from_absz_mm"])))))
            A.diel.append((lambda R, Z, s=s, rb=rb: (R > rod["d_mm"] / 2) & (R <= rb) & (s * Z >= tip) &
                           (s * Z <= rod["absz_mm"][1]), 3.2))     # PEEK in the bore gap
        if stator:
            A.cond.append(dict(name=f"rotor_face_{node}", node=node,
                               mask=lambda R, Z, s=s: (R >= 95.0) & (R <= 387.0) & (s * Z >= 27.25) & (s * Z <= 28.25)))
    if stator:                                                    # node 1 / node 4 foils near the hub (il2f), full annuli
        for zz in ((31.25, 32.25), (36.25, 37.25), (49.25, 50.25), (70.75, 71.75)):
            A.cond.append(dict(name=f"stator_{zz[0]}", node="gnd",
                               mask=lambda R, Z, zz=zz: (R >= 95.0) & (R <= 387.0) & (np.abs(Z) >= zz[0]) & (np.abs(Z) <= zz[1])))
    # dielectrics
    A.diel.append((lambda R, Z: (np.abs(Z) <= zs) & (R <= 500.0) & (np.hypot(R, Z) > ves["od_mm"] / 2), sep["eps_r"]))
    A.diel.append((lambda R, Z: np.hypot(R, Z) <= ves["od_mm"] / 2, ves["eps_r"]))
    rpz_o = hub["outer_r_plus_absz_mm"]
    rpz_i = rpz_o - hub["thickness_mm"] * math.sqrt(2)
    A.diel.append((lambda R, Z: (R + np.abs(Z) >= rpz_i) & (R + np.abs(Z) <= rpz_o) & (np.abs(Z) >= zs), 4.8))
    A.diel.append((lambda R, Z: (R >= 13.5) & (R <= 15.0) & (np.abs(Z) >= 26.0) & (np.abs(Z) <= 60.0), 4.8))
    A.diel.append((lambda R, Z: (R >= fo["id_mm"] / 2) & (R <= fo["od_mm"] / 2) & (np.abs(Z) >= rod["absz_mm"][0]) &
                   (np.abs(Z) <= rod["absz_mm"][1]), fo["eps_r"]))
    A.diel.append((lambda R, Z: (R <= fo["od_mm"] / 2) & (np.abs(Z) >= ves["pole_absz_mm"]) & (np.abs(Z) < rod["absz_mm"][0]), 3.2))
    # rods: conductors tied to the join
    for s in (-1, +1):
        A.rods.append(dict(z0=s * rod["absz_mm"][0], z1=s * rod["absz_mm"][1], r=rod["d_mm"] / 2, seg=5.0, rho=rod["rho_ohm_m"],
                           eps_bulk=rod["eps_bulk"], tie="join", tie_end=s * rod["absz_mm"][0]))
    A.mu = dict(mu_i=rod["mu_i"], f_r=rod["f_r_MHz"] * 1e6)
    # windings in chain order
    k = np.arange(cone["n"])
    rc_cone = cone["od_mm"] / 2
    keep = [kk for kk in k if cone["z0_mm"] + cone["dz_mm"] * kk - rc_cone >= zs + 1.0]     # clear septum + electrode
    A.meta["TC_dropped"] = [int(kk) for kk in k if kk not in keep]
    rz_tc = [(cone["r0_mm"] + cone["dr_mm"] * kk, -(cone["z0_mm"] + cone["dz_mm"] * kk)) for kk in keep]  # base -> apex
    circ_TC = fh * H[cone["hand_top"]] * (-1)                     # traversal -z on side A
    tc = A.add_winding("L_TC", rz_tc, rc_cone, rc_cone, "bare", [0] * len(rz_tc), circ_TC)
    rzA, layA, zbA, zaA, pitch = ah_turns(var, -1, p)
    circ_TA = fh * H[hands["top"]] * (+1)                         # layer 1 apex (-71) -> base (-31): +z
    ta = A.add_winding("L_TA", rzA, w["d_mm"] / 2, 0.5, "enamel", layA, circ_TA)
    rzB, layB, zbB, zaB, _ = ah_turns(var, +1, p)
    circ_BA_wound = fh * H[hands["bottom"]] * (-1)                # as wound: layer 1 apex (+71) -> base (+31): -z
    ba_w = A.add_winding("L_BA", rzB, w["d_mm"] / 2, 0.5, "enamel", layB, -circ_BA_wound)   # traversed in reverse
    rz_bc = [(cone["r0_mm"] + cone["dr_mm"] * kk, +(cone["z0_mm"] + cone["dz_mm"] * kk)) for kk in keep][::-1]  # apex -> base
    circ_BC = fh * H[cone["hand_bottom"]] * (-1)                  # traversal -z on side B
    bc = A.add_winding("L_BC", rz_bc, rc_cone, rc_cone, "bare", [0] * len(rz_bc), circ_BC)
    rw = w["d_mm"] / 2 * 1e-3
    nl = var_["layers"]
    # leads
    A.leads["apex_A"] = dict(L=straight_L(0.020, rc_cone * 1e-3), R=RHO_CU * 0.020 / (math.pi * (rc_cone * 1e-3) ** 2), segs=1, cross=[])
    A.leads["apex_B"] = dict(A.leads["apex_A"])
    for hn in ("A", "B"):
        A.leads[f"join_{hn}"] = dict(L=straight_L(0.035, rw), R=RHO_CU * 0.035 / (math.pi * rw ** 2), segs=1, cross=[])
    path = [("node", "R-A"), ("turns", tc), ("lead", "apex_A"), ("turns", ta)]
    if nl % 2 == 0:                                               # return lead along the outer layer, apex -> base
        outer = [i for i in ta if A.turns[i]["layer"] == nl - 1]
        outer = sorted(outer, key=lambda i: -abs(A.turns[i]["z"]))
        A.leads["ret_A"] = dict(L=straight_L((zaA - zbA) * 1e-3, rw), R=RHO_CU * (zaA - zbA) * 1e-3 / (math.pi * rw ** 2),
                                segs=len(outer), cross=outer)
        path.append(("lead", "ret_A"))
    path += [("lead", "join_A"), ("node", "join"), ("lead", "join_B")]
    ba = ba_w[::-1]                                               # chain order: from the base end
    if nl % 2 == 0:
        outerB = [i for i in ba_w if A.turns[i]["layer"] == nl - 1]
        outerB = sorted(outerB, key=lambda i: abs(A.turns[i]["z"]))   # base -> apex along the lead
        A.leads["ret_B"] = dict(L=A.leads["ret_A"]["L"], R=A.leads["ret_A"]["R"], segs=len(outerB), cross=outerB)
        path.append(("lead", "ret_B"))
    path += [("turns", ba), ("lead", "apex_B"), ("turns", bc), ("node", "R-B")]
    A.path = path
    A.sources = [("R-A", 1.0)]
    A.windings = dict(L_TC=tc, L_TA=ta, L_BA=ba_w, L_BC=bc)
    A.targets = [("centre", 0.0, 0.0), ("ax-1", 0.0, -1.0), ("ax+1", 0.0, 1.0), ("pole_A", 0.0, -ves["pole_absz_mm"]),
                 ("pole_B", 0.0, ves["pole_absz_mm"]), ("eq_wall", ves["od_mm"] / 2, 0.0)]
    A.domain = dict(r_max=560.0, z_lo=-200.0, z_hi=200.0, fine_r=[(5.0, 106.0, 0.2)], fine_z=[(-90.0, 90.0, 0.2)],
                    hmax=8.0, ms_fine_r=[(0.0, 14.0, 0.25), (14.0, 106.0, 1.0)], ms_fine_z=[(-90.0, 90.0, 0.25)])
    A.meta.update(N_AH=len(ta), N_TC=len(tc), layers=nl, pitch=pitch)
    return A


def bench_assembly(var="a", n_per_layer=None, layers=None, rod=True, mu=None, p=None, span_mm=None):
    """one AH coil (side B frame, z > 0) on its rod and former in a grounded fixture can r 40 mm, |z| 10..110;
    input at the apex end, far (base) end grounded, the rod tied to the far end."""
    p = p or preset()
    B = Assembly(f"bench-{var}-{n_per_layer}-{layers}-{'rod' if rod else 'norod'}")
    rodp = V(p, "AH_rod")
    fo = V(p, "AH_former")
    w = V(p, "AH_wire")
    rz, lay, zb, za, pitch = ah_turns(var, +1, p, n_per_layer, layers, span_mm)
    nl = layers or V(p, "AH_variants")[var]["layers"]
    t = B.add_winding("AH", rz, w["d_mm"] / 2, 0.5, "enamel", lay, +1)
    B.diel.append((lambda R, Z: (R >= fo["id_mm"] / 2) & (R <= fo["od_mm"] / 2) & (Z >= rodp["absz_mm"][0]) & (Z <= rodp["absz_mm"][1]), fo["eps_r"]))
    if rod:
        B.rods.append(dict(z0=rodp["absz_mm"][0], z1=rodp["absz_mm"][1], r=rodp["d_mm"] / 2, seg=5.0, rho=rodp["rho_ohm_m"],
                           eps_bulk=rodp["eps_bulk"], tie="gnd", tie_end=rodp["absz_mm"][0]))
    B.mu = dict(mu_i=rodp["mu_i"], f_r=rodp["f_r_MHz"] * 1e6) if mu is None else dict(static=float(mu))
    rw = w["d_mm"] / 2 * 1e-3
    path = [("node", "in"), ("turns", t)]
    if nl % 2 == 0:
        outer = sorted([i for i in t if B.turns[i]["layer"] == nl - 1], key=lambda i: -B.turns[i]["z"])
        B.leads["ret"] = dict(L=straight_L((za - zb) * 1e-3, rw), R=RHO_CU * (za - zb) * 1e-3 / (math.pi * rw ** 2),
                              segs=len(outer), cross=outer)
        path.append(("lead", "ret"))
    path.append(("node", "gnd"))
    B.path = path
    B.sources = [("in", 1.0)]
    B.windings = dict(AH=t)
    zc = 0.5 * (zb + za)
    B.targets = [("centre", 0.0, zc)]
    B.domain = dict(r_max=40.0, z_lo=10.0, z_hi=110.0, fine_r=[(5.0, 14.5, 0.1)], fine_z=[(25.0, 77.0, 0.1)], hmax=2.0,
                    ms_fine_r=[(0.0, 14.0, 0.25)], ms_fine_z=[(25.0, 77.0, 0.25)], ms_far=True)
    B.meta.update(N=len(t), layers=nl, pitch=pitch, zc=zc, rod=rod)
    return B


# ======================================================================================================
# 2. electrostatics with near-neighbour override                                                     [OC/IR]
# ======================================================================================================
def es_extract(A, log=print, h_scale=1.0):
    d = A.domain
    fr = [(a, b, h * h_scale) for a, b, h in d["fine_r"]]
    fz = [(a, b, h * h_scale) for a, b, h in d["fine_z"]]
    r = axis(0.0, d["r_max"], fr, d["hmax"]) * 1e-3
    z = axis(d["z_lo"], d["z_hi"], fz, d["hmax"]) * 1e-3
    nr, nz = len(r), len(z)
    RC, ZC = np.meshgrid(0.5 * (r[:-1] + r[1:]) * 1e3, 0.5 * (z[:-1] + z[1:]) * 1e3, indexing="ij")
    eps = np.ones((nr - 1, nz - 1))
    for m, e in A.diel:
        eps[m(RC, ZC)] = e
    rows, cols, vals, idx = fv_laplacian(r, z, eps * EPS0, "es")
    R, Z = np.meshgrid(r * 1e3, z * 1e3, indexing="ij")
    cid = -np.ones((nr, nz), int)
    cid[-1, :] = 0
    cid[:, 0] = 0
    cid[:, -1] = 0
    names, kinds = [], []
    for c in A.cond:
        m = c["mask"](R, Z) & (cid != 0)
        if c["node"] == "gnd":
            cid[m] = 0
        else:
            if c["node"] not in names:
                names.append(c["node"])
                kinds.append("fixed")
            cid[m] = names.index(c["node"]) + 1
    seg_of = []
    for ir, rd in enumerate(A.rods):
        z0, z1 = sorted((rd["z0"], rd["z1"]))
        ns = max(1, int(round((z1 - z0) / rd["seg"])))
        ed = z0 + (z1 - z0) * np.arange(ns + 1) / ns
        for s in range(ns):
            names.append(f"rod{ir}.{s}")
            kinds.append("rod")
            m = (R <= rd["r"] + 1e-9) & (Z >= ed[s] - 1e-9) & (Z <= ed[s + 1] + 1e-9) & (cid != 0)
            cid[m] = len(names)
            seg_of.append(dict(rod=ir, s=s, z0=ed[s], z1=ed[s + 1]))
    tix0 = len(names)
    for i, t in enumerate(A.turns):
        names.append(f"t{i}")
        kinds.append("turn")
        m = (R - t["r"]) ** 2 + (Z - t["z"]) ** 2 <= (t["rfd"] * 1.0001) ** 2
        if m.sum() < 3:
            raise ValueError(f"turn {i} under-resolved")
        if np.any(cid[m] > 0):
            raise ValueError(f"turn {i} ({t['w']}) overlaps conductor {names[cid[m].max() - 1]}")
        cid[m] = len(names)
    flat = cid.ravel()
    isrod = np.zeros(len(names) + 2, bool)
    for k, kd in enumerate(kinds):
        isrod[k + 2] = kd == "rod"
    keep = ~(isrod[flat[rows] + 1] & isrod[flat[cols] + 1] & (flat[rows] != flat[cols]))
    L = lap_from_edges(nr * nz, rows[keep], cols[keep], vals[keep])
    free = np.where(flat < 0)[0]
    K = len(names)
    t0 = time.time()
    lu = spla.splu(L[free][:, free].tocsc(), permc_spec="COLAMD")
    cond_nodes = np.where(flat > 0)[0]
    cond_id = flat[cond_nodes] - 1
    LC = L[:, cond_nodes].tocsc()
    Cm = np.zeros((K, K))
    # charge of conductor i = sum over its nodes of (L V); sum via a sparse indicator
    Ind = sp.csr_matrix((np.ones(len(cond_nodes)), (cond_id, cond_nodes)), shape=(K, nr * nz))
    for c0 in range(0, K, 32):
        cs = list(range(c0, min(K, c0 + 32)))
        E = sp.csr_matrix((np.ones(np.isin(cond_id, cs).sum()), (np.where(np.isin(cond_id, cs))[0],
                           np.searchsorted(cs, cond_id[np.isin(cond_id, cs)]))), shape=(len(cond_nodes), len(cs)))
        rhs = -(LC[free] @ E).toarray()
        VF = lu.solve(rhs)
        Vv = np.zeros((nr * nz, len(cs)))
        Vv[free] = VF
        Vv[cond_nodes] = E.toarray()
        Cm[:, cs] = Ind @ (L @ Vv)
    Cm = 0.5 * (Cm + Cm.T)
    log(f"  ES {A.name}: {nr} x {nz} = {nr * nz / 1e3:.0f} k nodes, {K} conductors, {time.time() - t0:.0f} s")
    es = dict(C_fd=Cm.copy(), names=names, kinds=kinds, rod_segs=seg_of, tix0=tix0, grid=(nr, nz))
    es["C"], es["override"] = neighbour_override(A, Cm, tix0)
    return es


def neighbour_override(A, Cm, tix0, er_enamel=3.5):
    """replace the FD partials between touching neighbours: enamelled -> Massarini-Kazimierczuk, bare -> two-wire;
    the capacitance to everything else (row sums) is kept."""
    C = Cm.copy()
    n = len(A.turns)
    P = np.array([(t["r"], t["z"]) for t in A.turns])
    log = []
    for i in range(n):
        ti = A.turns[i]
        for j in range(i + 1, n):
            tj = A.turns[j]
            if ti["w"] != tj["w"]:
                continue
            d = math.hypot(P[i, 0] - P[j, 0], P[i, 1] - P[j, 1])
            lt = 2 * math.pi * 0.5 * (ti["r"] + tj["r"]) * 1e-3
            if ti["ins"] == "enamel":
                Do = 1.60
                if d > 1.25 * Do:
                    continue
                cnew = mk_cap_per_m(2 * ti["rc"], Do, er_enamel) * lt
            else:
                if d > 2.5 * ti["rc"]:
                    continue
                cnew = twowire_cap_per_m(d * 1e-3, ti["rc"] * 1e-3) * lt
            a, b = tix0 + i, tix0 + j
            cold = -C[a, b]
            C[a, b] = C[b, a] = -cnew
            C[a, a] += cnew - cold
            C[b, b] += cnew - cold
            log.append((i, j, cold, cnew))
    return C, dict(n_pairs=len(log), mean_fd_pF=float(np.mean([x[2] for x in log]) * 1e12) if log else 0.0,
                   mean_new_pF=float(np.mean([x[3] for x in log]) * 1e12) if log else 0.0)


# ======================================================================================================
# 3. magnetostatics: core increment + field at the targets + field map                                [OC]
# ======================================================================================================
class MS:
    def __init__(self, A):
        d = A.domain
        far = 400.0 if d.get("ms_far") else 1000.0
        self.r = axis(0.0, far, d["ms_fine_r"], 40.0) * 1e-3
        self.z = axis(min(-far, d["z_lo"] - far), max(far, d["z_hi"] + far), d["ms_fine_z"], 40.0) * 1e-3
        nr, nz = len(self.r), len(self.z)
        self.n = nr * nz
        rc = 0.5 * (self.r[:-1] + self.r[1:]) * 1e3
        zc = 0.5 * (self.z[:-1] + self.z[1:]) * 1e3
        self.RC, self.ZC = np.meshgrid(rc, zc, indexing="ij")
        self.inrod = np.zeros((nr - 1, nz - 1), bool)
        for rd in A.rods:
            z0, z1 = sorted((rd["z0"], rd["z1"]))
            self.inrod |= (self.RC <= rd["r"]) & (self.ZC >= z0) & (self.ZC <= z1)
        self.idx = np.arange(self.n).reshape(nr, nz)
        R, Z = np.meshgrid(self.r, self.z, indexing="ij")
        bnd = (R == 0) | (R == self.r[-1]) | (Z == self.z[0]) | (Z == self.z[-1])
        self.free = np.where(~bnd.ravel())[0]
        self.A = A
        self.S = self._interp([(t["r"] * 1e-3, t["z"] * 1e-3) for t in A.turns])
        self.targets = A.targets
        self.has_core = bool(A.rods)
        self.last_psi = None

    _interp = EC.MS._interp

    def solve(self, mu_r, keep_psi=False):
        """M (turns x turns) and T (2 x targets, rows [Bz..., Br...]) with rod permeability mu_r."""
        cplx = np.iscomplexobj(mu_r)
        nu = np.where(self.inrod, 1.0 / (MU0 * mu_r), 1.0 / MU0).astype(complex if cplx else float)
        rows, cols, vals, _ = fv_laplacian(self.r, self.z, nu, "ms")
        L = lap_from_edges(self.n, rows, cols, vals)
        f = self.free
        lu = spla.splu(L[f][:, f].tocsc(), permc_spec="COLAMD")
        rhs = self.S[:, f].T.toarray().astype(L.dtype)
        psi = np.zeros((self.n, rhs.shape[1]), dtype=L.dtype)
        psi[f] = lu.solve(rhs)
        M = 2 * math.pi * (self.S @ psi)
        M = 0.5 * (M + M.T)
        T = self.field_rows(psi)
        if keep_psi:
            self.last_psi = psi
        return M, T

    def field_rows(self, psi):
        """B_z then B_r at each target, per unit current of each turn (FD; differences only are used)."""
        out = []
        for comp in ("z", "r"):
            for nm, rt, zt in self.targets:
                out.append(self.B_at(psi, rt, zt, comp))
        return np.array(out)

    def B_at(self, psi, rt, zt, comp):
        r, z, idx = self.r, self.z, self.idx
        zt_m, rt_m = zt * 1e-3, rt * 1e-3
        j = np.searchsorted(z, zt_m) - 1
        fz = (zt_m - z[j]) / (z[j + 1] - z[j])
        if rt_m < 1e-9:
            if comp == "r":
                return np.zeros(psi.shape[1], dtype=psi.dtype)
            r1, r2 = r[1], r[2]
            p1 = (1 - fz) * psi[idx[1, j]] + fz * psi[idx[1, j + 1]]
            p2 = (1 - fz) * psi[idx[2, j]] + fz * psi[idx[2, j + 1]]
            c4 = (p2 / r2 ** 2 - p1 / r1 ** 2) / (r2 ** 2 - r1 ** 2)
            return 2 * (p1 / r1 ** 2 - c4 * r1 ** 2)
        i = np.searchsorted(r, rt_m) - 1
        fr = (rt_m - r[i]) / (r[i + 1] - r[i])
        P = lambda a, b: psi[idx[a, b]]
        if comp == "z":                                       # (1/r) dpsi/dr
            dpr = ((1 - fz) * (P(i + 1, j) - P(i, j)) + fz * (P(i + 1, j + 1) - P(i, j + 1))) / (r[i + 1] - r[i])
            return dpr / rt_m
        dpz = ((1 - fr) * (P(i, j + 1) - P(i, j)) + fr * (P(i + 1, j + 1) - P(i + 1, j))) / (z[j + 1] - z[j])
        return -dpz / rt_m

    def rod_B(self, psi_vec):
        """|B| per rod cell for one current pattern (psi_vec: node values), and the cell volumes (m^3)."""
        r, z, idx = self.r, self.z, self.idx
        P = psi_vec.reshape(len(r), len(z))
        dr = np.diff(r)[:, None]
        dz = np.diff(z)[None, :]
        rc = 0.5 * (r[:-1] + r[1:])[:, None]
        dpr = 0.5 * ((P[1:, :-1] - P[:-1, :-1]) + (P[1:, 1:] - P[:-1, 1:])) / dr
        dpz = 0.5 * ((P[:-1, 1:] - P[:-1, :-1]) + (P[1:, 1:] - P[1:, :-1])) / dz
        Bz = dpr / rc
        Br = -dpz / rc
        Bm = np.hypot(np.abs(Bz), np.abs(Br))
        vol = 2 * math.pi * rc * dr * dz
        return Bm[self.inrod], np.broadcast_to(vol, Bm.shape)[self.inrod]


def air_T(A):
    """closed-form loop fields at the targets (rows Bz..., Br...) per unit current of each turn."""
    rt = np.array([t["r"] for t in A.turns]) * 1e-3
    zt = np.array([t["z"] for t in A.turns]) * 1e-3
    rowsz, rowsr = [], []
    for nm, r0, z0 in A.targets:
        Br, Bz = loop_B(rt, r0 * 1e-3, z0 * 1e-3 - zt)
        rowsz.append(Bz)
        rowsr.append(Br)
    return np.array(rowsz + rowsr)


def air_L(A):
    rt = np.array([t["r"] for t in A.turns]) * 1e-3
    zt = np.array([t["z"] for t in A.turns]) * 1e-3
    rc = np.array([t["rc"] for t in A.turns]) * 1e-3
    R1, R2 = np.meshgrid(rt, rt, indexing="ij")
    Z1, Z2 = np.meshgrid(zt, zt, indexing="ij")
    with np.errstate(divide="ignore", invalid="ignore"):
        M = mutual(R1, R2, Z1 - Z2)
    np.fill_diagonal(M, MU0 * rt * (np.log(8 * rt / rc) - 2.0))
    return M


def core_increment(A, ms, mu):
    """static (real or complex) rod permeability: dL and dT relative to mu = 1."""
    M1, T1 = ms.solve(1.0)
    Mm, Tm = ms.solve(mu)
    return Mm - M1, Tm - T1


# ======================================================================================================
# 4. the ladder (general netlist), MNA trapezoidal transient                                           [OC]
# ======================================================================================================
class Ladder:
    def __init__(self, A, es, core=None, Rs=0.0, flip_hands=False):
        """core: None | dict(static=(dL, dT)) | edge_coil.core_fit dict."""
        self.A = A
        nodes = {}

        def node(nm):
            if nm == "gnd":
                return -1
            if nm not in nodes:
                nodes[nm] = len(nodes)
            return nodes[nm]

        br = []        # dict(a, b, turn or None, sign, L, R, lead, seg)
        cur = None
        auto = [0]

        def newnode():
            auto[0] += 1
            return node(f"_n{auto[0]}")

        items = A.path
        for k, it in enumerate(items):
            if it[0] == "node":
                nn = node(it[1])
                if cur is not None and cur != nn:
                    raise ValueError("path: node follows node")
                cur = nn
                continue
            nxt_is_node = k + 1 < len(items) and items[k + 1][0] == "node"
            if it[0] == "turns":
                for q, ti in enumerate(it[1]):
                    last = q == len(it[1]) - 1
                    b = node(items[k + 1][1]) if (last and nxt_is_node) else newnode()
                    br.append(dict(a=cur, b=b, turn=ti, sign=A.turns[ti]["circ"], lead=None))
                    cur = b
            elif it[0] == "lead":
                ld = A.leads[it[1]]
                ns = ld["segs"]
                for q in range(ns):
                    last = q == ns - 1
                    b = node(items[k + 1][1]) if (last and nxt_is_node) else newnode()
                    br.append(dict(a=cur, b=b, turn=None, sign=0, lead=it[1], seg=q, L=ld["L"] / ns, R=ld["R"] / ns))
                    cur = b
        self.br, self.nodes = br, nodes
        # rods
        self.rod_nodes = [node(f"rod{sg['rod']}.{sg['s']}") for sg in es["rod_segs"]]
        # sources
        self.src = []
        for nm, amp in A.sources:
            nt = node(nm)
            if Rs > 0:
                self.src.append(dict(node=node("src:" + nm), term=nt, amp=amp))
            else:
                self.src.append(dict(node=nt, term=nt, amp=amp))
        nn, nb = len(nodes), len(br)
        self.nn, self.nb, self.ns = nn, nb, len(self.src)
        self.n = nn + nb + self.ns
        tix = np.array([b["turn"] if b["turn"] is not None else -1 for b in br])
        isturn = tix >= 0
        self.tix, self.isturn = tix, isturn
        sgn = np.array([float(b["sign"]) for b in br])
        self.sgn = sgn
        bi = np.where(isturn)[0]
        ti = tix[isturn]
        S = np.zeros((nb, len(A.turns)))
        S[bi, ti] = sgn[bi]
        self.S = S
        Mt = air_L(A)
        Lb = S @ Mt @ S.T
        R0b = np.zeros(nb)
        self.relax = []
        # skin: one Foster network per turn (poles common to all turns of one conductor radius)
        relax = {}
        for k in bi:
            t = A.turns[tix[k]]
            R0, pk, Rk, err = skin_fit(t["rc"] * 1e-3, 2 * math.pi * t["r"] * 1e-3)
            R0b[k] = R0
            for q, (p_, r_) in enumerate(zip(pk, Rk)):
                if r_ > 0:
                    relax.setdefault((round(t["rc"], 4), q), (p_, np.zeros(nb)))[1][k] = r_
        for key, (p_, vec) in relax.items():
            self.relax.append((p_, vec, None))
        for k, b in enumerate(br):
            if b["turn"] is None:
                Lb[k, k] += b["L"]
                R0b[k] = b["R"]
        self.L_air = Lb.copy()
        Tair = air_T(A) @ S.T
        self.T_static = Tair
        if core is not None and "static" in core:
            dL, dT = core["static"]
            Lb = Lb + (S @ np.real(dL) @ S.T)
            self.T_static = self.T_static + np.real(dT) @ S.T
        elif core is not None:
            Lb = Lb + S @ core["L_inf"] @ S.T
            self.T_static = self.T_static + core["T_inf"].real @ S.T
            for q in range(len(core["p"])):
                self.relax.append((core["p"][q], S @ core["K"][q] @ S.T, core["d"][q].real @ S.T))
        self.Lb, self.R0b = Lb, R0b
        ev = np.linalg.eigvalsh(0.5 * (Lb + Lb.T))
        self.L_pd = bool(ev.min() > 0)
        self.L_min_eig = float(ev.min())
        # capacitance: conductor potentials P @ v
        Cm = es["C"]
        K = Cm.shape[0]
        P = np.zeros((K, nn))
        name_ix = {nm: k for k, nm in enumerate(es["names"])}
        for k, b in enumerate(br):
            if b["turn"] is None or not name_ix:
                continue
            c = name_ix[f"t{b['turn']}"]
            for x in (b["a"], b["b"]):
                if x >= 0:
                    P[c, x] += 0.5
        for s, sg in enumerate(es["rod_segs"]):
            P[name_ix[f"rod{sg['rod']}.{sg['s']}"], self.rod_nodes[s]] = 1.0
        for k, kd in enumerate(es["kinds"]):
            if kd == "fixed":
                nm = es["names"][k]
                if nm in nodes:
                    P[k, nodes[nm]] = 1.0
        self.P = P
        Cn = P.T @ Cm @ P
        Gn = np.zeros((nn, nn))
        # lead crossing capacitances (each lead segment's downstream node to the turn it passes)
        mkc = mk_cap_per_m(1.5, 1.6, 3.5)
        for k, b in enumerate(br):
            if b["lead"] is None or not name_ix:
                continue
            ld = A.leads[b["lead"]]
            if not ld["cross"]:
                continue
            ti_ = ld["cross"][b["seg"]]
            Cx = mkc * 2 * A.turns[ti_]["rc"] * 1e-3 * 2.0          # crossing over ~ two wire widths [IR]
            c = name_ix[f"t{ti_}"]
            vvec = P[c].copy()
            if b["b"] >= 0:
                vvec[b["b"]] -= 1.0
            Cn += Cx * np.outer(vvec, vvec)
        # rods: R || C between segments, tie to its node
        for s in range(len(es["rod_segs"]) - 1):
            s0, s1 = es["rod_segs"][s], es["rod_segs"][s + 1]
            if s0["rod"] != s1["rod"]:
                continue
            rr = A.rods[s0["rod"]]["r"] * 1e-3
            dzs = 0.5 * ((s0["z1"] - s0["z0"]) + (s1["z1"] - s1["z0"])) * 1e-3
            Gs = math.pi * rr ** 2 / (A.rods[s0["rod"]]["rho"] * dzs)
            Cs = EPS0 * A.rods[s0["rod"]]["eps_bulk"] * math.pi * rr ** 2 / dzs
            u, v = self.rod_nodes[s], self.rod_nodes[s + 1]
            for (x, y, val) in ((u, u, 1), (v, v, 1), (u, v, -1), (v, u, -1)):
                Gn[x, y] += val * Gs
                Cn[x, y] += val * Cs
        for ir, rd in enumerate(A.rods):
            segs = [s for s, sg in enumerate(es["rod_segs"]) if sg["rod"] == ir]
            if not segs:
                continue
            s_t = min(segs, key=lambda s: abs(0.5 * (es["rod_segs"][s]["z0"] + es["rod_segs"][s]["z1"]) - rd["tie_end"]))
            u = self.rod_nodes[s_t]
            v = -1 if rd["tie"] == "gnd" else nodes[rd["tie"]]
            G = 1.0
            Gn[u, u] += G
            if v >= 0:
                Gn[v, v] += G
                Gn[u, v] -= G
                Gn[v, u] -= G
        for sd in self.src:
            if sd["node"] != sd["term"]:
                G = 1.0 / Rs
                for (x, y, val) in ((sd["node"], sd["node"], 1), (sd["term"], sd["term"], 1),
                                    (sd["node"], sd["term"], -1), (sd["term"], sd["node"], -1)):
                    Gn[x, y] += val * G
        self.Cn, self.Gn = Cn, Gn
        Bi = np.zeros((nn, nb))
        for k, b in enumerate(br):
            if b["a"] >= 0:
                Bi[b["a"], k] += 1
            if b["b"] >= 0:
                Bi[b["b"], k] -= 1
        self.Bi = Bi
        srcn = {sd["node"] for sd in self.src}
        kind = []
        for x in range(nn):
            if not np.any(Cn[x]):
                kind.append("alg")
            elif x in srcn:
                kind.append("be")
            else:
                kind.append("trap")
        self.kind = np.array(kind + ["trap"] * nb + ["alg"] * self.ns)
        self.wmask = {w: np.isin(tix, ix) & isturn for w, ix in A.windings.items()}

    _AE = EC.Ladder._AE

    def transient(self, vs, t_end, h):
        nn, nb = self.nn, self.nb
        E, A = self._AE()
        th = np.where(self.kind == "trap", 0.5, 1.0)
        ee = np.where(self.kind == "alg", 0.0, 1.0)
        phi = np.where(self.kind == "trap", 0.5, 0.0)
        alpha = np.array([(1 - h * p / 2) / (1 + h * p / 2) for p, _, _ in self.relax])
        beta = np.array([(h * p / 2) / (1 + h * p / 2) for p, _, _ in self.relax])
        Kbar = np.zeros((nb, nb))
        for q, (p, K, d) in enumerate(self.relax):
            Kbar += (1 - beta[q]) * (np.diag(K) if K.ndim == 1 else K)
        M = ee[:, None] * E / h - th[:, None] * A
        M[nn:nn + nb, nn:nn + nb] += 0.5 * Kbar
        lu = sla.lu_factor(M)
        amp = np.array([sd["amp"] for sd in self.src])
        x = np.zeros(self.n)
        W = [np.zeros(nb) for _ in self.relax]
        nsteps = int(math.ceil(t_end / h))
        ntg = self.T_static.shape[0]
        nw = len(self.wmask)
        rec_x = np.zeros((nsteps + 1, self.n))
        rec_B = np.zeros((nsteps + 1, ntg, nw))
        wl = list(self.wmask.items())

        def field(xv, Wl):
            i = xv[nn:nn + nb]
            out = np.zeros((ntg, nw))
            for c, (w, m) in enumerate(wl):
                b = self.T_static[:, m] @ i[m]
                for q, (p, K, d) in enumerate(self.relax):
                    if d is not None:
                        b = b + d[:, m] @ Wl[q][m]
                out[:, c] = b
            return out

        rec_B[0] = field(x, W)
        b0 = np.concatenate([np.zeros(nn + nb), -amp * vs(0.0)])
        for st in range(1, nsteps + 1):
            t1 = st * h
            b1 = np.concatenate([np.zeros(nn + nb), -amp * vs(t1)])
            i0 = x[nn:nn + nb]
            f0 = A @ x + b0
            rt = np.zeros(nb)
            rk = np.zeros(nb)
            for q, (p, K, d) in enumerate(self.relax):
                diff = i0 - W[q]
                u = alpha[q] * W[q] + beta[q] * i0
                if K.ndim == 1:
                    rt += K * diff
                    rk += K * u
                else:
                    rt += K @ diff
                    rk += K @ u
            f0[nn:nn + nb] -= rt
            rhs = ee * (E @ x) / h + th * b1 + phi * f0
            rhs[nn:nn + nb] += 0.5 * rk
            x1 = sla.lu_solve(lu, rhs)
            i1 = x1[nn:nn + nb]
            W = [alpha[q] * W[q] + beta[q] * (i0 + i1) for q in range(len(self.relax))]
            x, b0 = x1, b1
            rec_x[st] = x
            rec_B[st] = field(x, W)
        t = np.arange(nsteps + 1) * h
        return dict(t=t, v=rec_x[:, :nn], i=rec_x[:, nn:nn + nb], i_s=rec_x[:, nn + nb:], B=rec_B,
                    windings=[w for w, _ in wl])

    def turn_potential(self, v):
        """potential of each turn (mean of its two nodes), [time, turn index]."""
        out = np.zeros((v.shape[0], len(self.A.turns)))
        for k, b in enumerate(self.br):
            if b["turn"] is None:
                continue
            va = v[:, b["a"]] if b["a"] >= 0 else 0.0
            vb = v[:, b["b"]] if b["b"] >= 0 else 0.0
            out[:, b["turn"]] = 0.5 * (va + vb)
        return out

    def save(self, path, r, meta):
        inv = {v: k for k, v in self.nodes.items()}
        np.savez_compressed(path, t=r["t"], v_node=r["v"].astype(np.float32), i_branch=r["i"].astype(np.float32),
                            i_source=r["i_s"], B=r["B"], windings=np.array(r["windings"]),
                            node_names=np.array([inv[k] for k in range(self.nn)]),
                            branch_turn=np.array([b["turn"] if b["turn"] is not None else -1 for b in self.br]),
                            branch_lead=np.array([b["lead"] or "" for b in self.br]),
                            branch_from=np.array([b["a"] for b in self.br]), branch_to=np.array([b["b"] for b in self.br]),
                            branch_sign=self.sgn, turn_rz_mm=np.array([(t["r"], t["z"]) for t in self.A.turns]),
                            turn_winding=np.array([t["w"] for t in self.A.turns]),
                            turn_layer=np.array([t["layer"] for t in self.A.turns]),
                            targets=np.array([f"{a}@({b},{c})" for a, b, c in self.A.targets]), meta=json.dumps(meta))
