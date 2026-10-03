#!/usr/bin/env python3
"""
sim/field_solve.py — ROUND-TRIP: the 3-D electrostatic capacitance matrix of a pump-geometry build  [ME]
=======================================================================================================
Every conductor of the bill of solids (foils, bus rings, spheres, stems, leads, links), every insulator
(G10 carriers, the garolite septum, the mica slabs and facings) and a grounded enclosure.

METHOD [ME] -- finite volumes on a cylindrical tensor grid (r, phi, z):
  * the solver sees the equation div(eps grad V) = 0, cell-centred, with the exact 1-D conductances of an
    annular-sector cell (radial: 2 pi-free log form, azimuthal: log form, axial: the sector area);
  * grid lines are SNAPPED to every box-like boundary of the build (foil, carrier, slab and bus-ring
    radii, angles and heights), so those are represented exactly; spheres, stems and leads are
    rasterised (cell centre inside, plus every cell their axis passes through) [ME staircase];
  * conductors are fixed-potential cells whose surface is the cell face; the Maxwell matrix is the
    Schur complement C = S A_cc S^T - B^T A_uu^-1 B (symmetric by construction);
  * the build is 60-degree periodic (6 kept sectors, 6 spokes per gap; checked by periodicity()), so one
    60-degree wedge is solved with periodic faces and every entry is multiplied by 6;
  * boundary: the grounded can (Dirichlet 0) at `enclosure` mm beyond the outermost conductor, or free
    space (Robin, monopole decay dV/dn = -V/rho) [IR, D-ENCLOSURE];
  * linear solves: algebraic multigrid (pyamg, if installed) preconditioning CG; fallback: CG with a
    z-line (tridiagonal) block-Jacobi preconditioner (slow) [ME].
Units: mm, F. Reference = the enclosure (or infinity). Pure EE. No file I/O on import.
Gates FS1-FS6 (analytic cases) run in rt_gates.py; a small on-load self-test runs here.
"""
import math
import time

import numpy as np
import scipy.sparse as sp
import scipy.sparse.linalg as spla

try:
    import pyamg
except Exception:                       # pragma: no cover
    pyamg = None

EPS0 = 8.8541878128e-15                 # F/mm
EPS_R = {"air": 1.0006, "mica": 5.4, "garolite": 4.7, "G10": 4.7}
PERIOD = 60.0


def eps_of_material(mat):
    """relative permittivity of an insulator by its material name (as pump_geometry.DIELECTRICS)."""
    m = (mat or "").lower()
    for k, v in (("mica", 5.4), ("garolite", 4.7), ("g10", 4.7)):
        if k in m:
            return v
    return EPS_R["air"]


CONDUCTOR_KEYS = ("al foil", "cu ", "w-cu", "sphere")


def is_conductor(mat):
    m = (mat or "").lower()
    return any(k in m for k in CONDUCTOR_KEYS)


# ---------------------------------------------------------------------------------------------------
# grid
# ---------------------------------------------------------------------------------------------------
def _merge(v, tol):
    v = np.unique(np.asarray(v, float))
    if v.size == 0:
        return v
    out = [v[0]]
    for x in v[1:]:
        if x - out[-1] > tol:
            out.append(x)
    return np.array(out)


def axis_edges(lo, hi, breaks, fine, h_max, h_min, grow, tol):
    """Cell edges on [lo, hi] containing every break; the size grows geometrically (ratio `grow`) from
    h_min at each `fine` position to at most h_max."""
    b = _merge([lo, hi] + [x for x in breaks if lo < x < hi], tol)
    fine = np.asarray(sorted(fine), float)

    def h_at(x):
        if fine.size == 0:
            return h_max
        d = np.min(np.abs(fine - x))
        return min(h_max, h_min + (grow - 1.0) * d)
    edges = [b[0]]
    for a, c in zip(b[:-1], b[1:]):
        pts = [a]
        x = a
        while True:
            h = min(h_at(x), h_at(min(c, x + h_at(x))))
            if x + h >= c - 0.3 * h:
                break
            x += h
            pts.append(x)
        n = len(pts)
        # rescale so the interval ends exactly on c (keep relative sizes)
        if n > 1:
            s = np.array(pts + [c])
            s = a + (s - a) * (c - a) / (s[-1] - a)
            edges.extend(s[1:].tolist())
        else:
            edges.append(c)
    return np.array(edges)


class Grid:
    def __init__(self, r, p, z):
        self.r, self.p, self.z = np.asarray(r, float), np.asarray(p, float), np.asarray(z, float)
        self.rc = 0.5 * (self.r[1:] + self.r[:-1])
        self.pc = 0.5 * (self.p[1:] + self.p[:-1])
        self.zc = 0.5 * (self.z[1:] + self.z[:-1])
        self.shape = (self.rc.size, self.pc.size, self.zc.size)

    @property
    def n(self):
        return int(np.prod(self.shape))


# ---------------------------------------------------------------------------------------------------
# parts -> primitives (the bill of solids of pump_geometry, or analytic test bodies)
# ---------------------------------------------------------------------------------------------------
def _ang(x, y):
    return math.degrees(math.atan2(y, x)) % 360.0


def primitives(parts, node_of=None):
    """design['parts'] -> list of primitives dict(kind sector|sphere|rod, cond (node or None), eps, ...)."""
    out = []
    for p in parts:
        cond = is_conductor(p.get("material"))
        node = (node_of(p) if node_of else p.get("node")) if cond else None
        q = dict(kind=p["shape"], cond=node, eps=None if cond else eps_of_material(p.get("material")), name=p["name"])
        if p["shape"] == "sector":
            q.update(r_in=p["r_in"], r_out=p["r_out"], a0=p["start_deg"], w=p["w_deg"], z0=p["z0"], z1=p["z1"])
        elif p["shape"] == "sphere":
            q.update(c=list(p["c"]), R=p["r"])
        else:
            q.update(p0=list(p["p0"]), p1=list(p["p1"]), R=p["r"])
        out.append(q)
    return out


def _canon(q, period=PERIOD):
    """a key invariant under rotation by multiples of the period (for de-duplicating periodic copies)."""
    if q["kind"] == "sector":
        a = q["a0"] % period if q["w"] < 360.0 - 1e-9 else 0.0
        return ("s", q["cond"], q["eps"], round(q["r_in"], 4), round(q["r_out"], 4), round(a % period, 4),
                round(min(q["w"], 360.0), 4), round(q["z0"], 4), round(q["z1"], 4))
    pts = [q["c"]] if q["kind"] == "sphere" else [q["p0"], q["p1"]]
    a = _ang(*pts[0][:2])
    rot = -math.radians(period * math.floor(a / period + 1e-9))
    key = [q["kind"], q["cond"], round(q["R"], 4)]
    for x in pts:
        key += [round(x[0] * math.cos(rot) - x[1] * math.sin(rot), 3), round(x[0] * math.sin(rot) + x[1] * math.cos(rot), 3),
                round(x[2], 3)]
    return tuple(key)


def periodicity(prims, period=PERIOD, tol=1e-3):
    """Is the set of primitives invariant under a rotation by `period` degrees? Returns (ok, n_unpaired,
    examples). Every primitive's image must match a primitive of the same kind, node / permittivity and
    radius to `tol` mm (sectors: the start angle + period)."""
    groups = {}
    for q in prims:
        groups.setdefault((q["kind"], q["cond"], q["eps"]), []).append(q)
    arr = {}
    for key, qs in groups.items():
        arr[key] = np.array([_vec(q) for q in qs])
    bad = []
    for q in prims:
        key = (q["kind"], q["cond"], q["eps"])
        v = _vec(_rotated(q, period))
        A = arr[key]
        d = np.max(np.abs(A - v[None, :]), axis=1)
        if q["kind"] == "rod":                       # either orientation of the segment
            vf = np.concatenate([v[:1], v[4:7], v[1:4]])
            d = np.minimum(d, np.max(np.abs(A - vf[None, :]), axis=1))
        if q["kind"] == "sector":                    # angles modulo 360
            da = np.abs(((A[:, 3] - v[3]) + 180.0) % 360.0 - 180.0)
            d = np.maximum(np.max(np.abs(np.delete(A, 3, axis=1) - np.delete(v, 3)[None, :]), axis=1), da)
        if not np.any(d < tol):
            bad.append(q["name"])
    return not bad, len(bad), bad[:5]


def _vec(q):
    if q["kind"] == "sector":
        a = q["a0"] % 360.0 if q["w"] < 360.0 - 1e-9 else 0.0
        return np.array([q["r_in"], q["r_out"], min(q["w"], 360.0), a, q["z0"], q["z1"]])
    if q["kind"] == "sphere":
        return np.array([q["R"]] + list(q["c"]))
    return np.array([q["R"]] + list(q["p0"]) + list(q["p1"]))


def _rotated(q, d):
    q2 = dict(q)
    if q["kind"] == "sector":
        q2["a0"] = (q["a0"] + d) % 360.0 if q["w"] < 360.0 - 1e-9 else q["a0"]
        return q2
    c, s = math.cos(math.radians(d)), math.sin(math.radians(d))
    rot = lambda x: [x[0] * c - x[1] * s, x[0] * s + x[1] * c, x[2]]
    if q["kind"] == "sphere":
        q2["c"] = rot(q["c"])
    else:
        q2["p0"], q2["p1"] = rot(q["p0"]), rot(q["p1"])
    return q2


def dedupe(prims, period=PERIOD):
    seen, out = set(), []
    for q in prims:
        k = _canon(q, period)
        if k not in seen:
            seen.add(k)
            out.append(q)
    return out


# ---------------------------------------------------------------------------------------------------
# grid from primitives
# ---------------------------------------------------------------------------------------------------
DEFAULT_RES = dict(h_max_r=4.0, h_min_r=0.5, h_max_z=3.0, h_min_z=0.5, h_max_p=1.5, h_min_arc=0.6, grow=1.45,
                   r_fine_at=387.0, h_far=12.0)


def build_grid(prims, enclosure=50.0, period=PERIOD, res=None, theta_breaks=(), free_scale=25.0):
    """Tensor grid over one wedge [0, period) x [0, R] x [Z0, Z1]: every SECTOR boundary is a grid line
    (conductor boundaries graded to h_min), constant-height leads add their top / bottom planes and
    axial leads their radii; spheres and the angular extent of leads are rasterised [ME]."""
    R = dict(DEFAULT_RES, **(res or {}))
    rb, zb, pb, rf, zf, pf = [], [], [], [], [], []
    r_max = z_max = 0.0
    z_min = 0.0
    for q in prims:
        if q["kind"] == "sector":
            rb += [q["r_in"], q["r_out"]]; zb += [q["z0"], q["z1"]]
            if q["w"] < 360.0 - 1e-9:
                pb += [q["a0"] % period, (q["a0"] + q["w"]) % period]
                if q["cond"] is not None:
                    pf += [q["a0"] % period, (q["a0"] + q["w"]) % period]
            if q["cond"] is not None:
                rf += [q["r_in"], q["r_out"]]; zf += [q["z0"], q["z1"]]
                r_max = max(r_max, q["r_out"]); z_max = max(z_max, q["z1"]); z_min = min(z_min, q["z0"])
        elif q["kind"] == "sphere":
            c = q["c"]; rr = math.hypot(c[0], c[1])
            if q["cond"] is not None:
                r_max = max(r_max, rr + q["R"]); z_max = max(z_max, c[2] + q["R"]); z_min = min(z_min, c[2] - q["R"])
        else:
            a, b = q["p0"], q["p1"]; ra, rbb = math.hypot(a[0], a[1]), math.hypot(b[0], b[1])
            if abs(a[2] - b[2]) < 1e-9:
                zb += [a[2] - q["R"], a[2] + q["R"]]
            if math.hypot(a[0] - b[0], a[1] - b[1]) < 1e-9:              # axial lead
                rb += [ra - q["R"], ra + q["R"]]
            if q["cond"] is not None:
                r_max = max(r_max, ra + q["R"], rbb + q["R"]); z_max = max(z_max, a[2] + q["R"], b[2] + q["R"])
                z_min = min(z_min, a[2] - q["R"], b[2] - q["R"])
    pb += list(theta_breaks); pf += list(theta_breaks)
    if enclosure is None:                    # free space: a far Robin boundary
        ext = free_scale * max(r_max, z_max - z_min)
        Rr, Z0, Z1 = r_max + ext, z_min - ext, z_max + ext
        h_far = max(R["h_far"], 0.25 * ext)
    else:
        Rr, Z0, Z1 = r_max + enclosure, z_min - enclosure, z_max + enclosure
        h_far = R["h_far"]
    re = axis_edges(0.0, r_max + 1.0, rb, rf, R["h_max_r"], R["h_min_r"], R["grow"], 0.05)
    re = _extend(re, Rr, R["grow"], h_far)
    ze = axis_edges(z_min - 1.0, z_max + 1.0, zb, zf, R["h_max_z"], R["h_min_z"], R["grow"], 0.05)
    ze = _extend(ze, Z1, R["grow"], h_far)
    ze = -_extend(-ze[::-1], -Z0, R["grow"], h_far)[::-1]
    # phi: graded in angle so that the arc at r_fine_at is h_min_arc at a conductor sector edge
    dmin = math.degrees(R["h_min_arc"] / R["r_fine_at"])
    pe = axis_edges(0.0, period, pb, pf, R["h_max_p"], dmin, R["grow"], 0.004)
    return Grid(re, pe, ze), dict(R_enc=Rr, z_enc=(Z0, Z1), free=enclosure is None)


def _extend(e, end, grow, hmax):
    """continue the edges e (increasing) to `end`, growing the cell size geometrically up to hmax."""
    e = list(e)
    h = e[-1] - e[-2]
    x = e[-1]
    while x + h * grow < end - 0.5 * min(hmax, h * grow):
        h = min(hmax, h * grow); x += h; e.append(x)
    e.append(end)
    return np.array(e)


# ---------------------------------------------------------------------------------------------------
# rasterisation
# ---------------------------------------------------------------------------------------------------
def rasterize(g, prims, period=PERIOD, theta=0.0, rotor=None):
    """eps (Nr,Np,Nz) float and cond (Nr,Np,Nz) int (-1 = insulator) + the list of conductor names.
    `rotor`: set of primitive names on the rotor; those are rotated by +theta degrees."""
    Nr, Np, Nz = g.shape
    eps = np.full(g.shape, EPS_R["air"])
    cond = np.full(g.shape, -1, dtype=np.int32)
    names = []
    cid = {}

    def ids(lo_hi, edges_c):
        lo, hi = lo_hi
        return np.nonzero((edges_c >= lo - 1e-9) & (edges_c <= hi + 1e-9))[0]
    order = [q for q in prims if q["cond"] is None] + [q for q in prims if q["cond"] is not None]
    for q in order:
        th = theta if (rotor is not None and q["name"] in rotor) else 0.0
        if q["cond"] is not None and q["cond"] not in cid:
            cid[q["cond"]] = len(names); names.append(q["cond"])
        val_c = cid.get(q["cond"], -1)
        if q["kind"] == "sector":
            I = ids((q["r_in"], q["r_out"]), g.rc); K = ids((q["z0"], q["z1"]), g.zc)
            if I.size == 0 or K.size == 0:
                continue
            if q["w"] >= 360.0 - 1e-9 or q["w"] >= period - 1e-9 and abs((q["w"] % period)) < 1e-9:
                J = np.arange(Np)
            else:
                d = (g.pc - (q["a0"] + th)) % period
                J = np.nonzero(d < q["w"] - 1e-9)[0] if q["w"] < period else np.arange(Np)
            if J.size == 0:
                continue
            sl = np.ix_(I, J, K)
            if q["cond"] is None:
                eps[sl] = q["eps"]
            else:
                cond[sl] = val_c
        else:
            _raster_curved(g, q, th, period, eps, cond, val_c)
    return eps, cond, names


def _cart(rc, pc_deg, zc):
    a = np.radians(pc_deg)
    return rc * np.cos(a), rc * np.sin(a), zc


def _raster_curved(g, q, th, period, eps, cond, val_c):
    c, s = math.cos(math.radians(th)), math.sin(math.radians(th))
    rot = lambda x: [x[0] * c - x[1] * s, x[0] * s + x[1] * c, x[2]]
    if q["kind"] == "sphere":
        P = [rot(q["c"])]
        P0 = P1 = P[0]
    else:
        P0, P1 = rot(q["p0"]), rot(q["p1"])
    R = q["R"]
    # bounding box in r, z; angle range of the axis
    pts = np.array([P0, P1])
    rr = np.hypot(pts[:, 0], pts[:, 1])
    rmin = _seg_rmin(P0, P1) - R; rmax = rr.max() + R
    zmin, zmax = pts[:, 2].min() - R, pts[:, 2].max() + R
    I = np.nonzero((g.r[1:] > rmin) & (g.r[:-1] < rmax))[0]
    K = np.nonzero((g.z[1:] > zmin) & (g.z[:-1] < zmax))[0]
    if I.size == 0 or K.size == 0:
        return
    am = _ang(*(0.5 * (np.array(P0) + np.array(P1)))[:2])
    # every wedge cell, mapped to the periodic image nearest the part
    pc_img = g.pc + period * np.round((am - g.pc) / period)
    half = 0.5 * math.degrees(math.hypot(P1[0] - P0[0], P1[1] - P0[1]) / max(rmin + R, 1.0)) + math.degrees((R + 3.0) / max(rmin + R, 1.0)) + 2.0
    J = np.nonzero(np.abs(pc_img - am) <= half)[0]
    if J.size == 0:
        return
    RR, PP, ZZ = np.meshgrid(g.rc[I], pc_img[J], g.zc[K], indexing="ij")
    X, Y, Z = _cart(RR, PP, ZZ)
    d = _pt_seg_dist(X, Y, Z, P0, P1)
    inside = d <= R + 1e-9
    # plus every cell the axis passes through (thin parts stay connected and present)
    L = math.dist(P0, P1)
    hmin = min(np.min(np.diff(g.r[I[0]:I[-1] + 2])), np.min(np.diff(g.z[K[0]:K[-1] + 2])))
    n = max(2, int(math.ceil(L / (0.25 * hmin))) + 1)
    t = np.linspace(0.0, 1.0, n)
    A = np.array(P0)[None, :] + t[:, None] * (np.array(P1) - np.array(P0))[None, :]
    ar, aa, az = np.hypot(A[:, 0], A[:, 1]), np.degrees(np.arctan2(A[:, 1], A[:, 0])) % 360.0, A[:, 2]
    ii = np.clip(np.searchsorted(g.r, ar) - 1, 0, g.shape[0] - 1)
    jj = np.clip(np.searchsorted(g.p, aa % period) - 1, 0, g.shape[1] - 1)
    kk = np.clip(np.searchsorted(g.z, az) - 1, 0, g.shape[2] - 1)
    sel = (np.ix_(I, J, K))
    if q["cond"] is None:
        sub = eps[sel]; sub[inside] = q["eps"]; eps[sel] = sub
        eps[ii, jj, kk] = q["eps"]
    else:
        sub = cond[sel]; sub[inside] = val_c; cond[sel] = sub
        cond[ii, jj, kk] = val_c


def _seg_rmin(a, b):
    dx, dy = b[0] - a[0], b[1] - a[1]
    L2 = dx * dx + dy * dy
    t = 0.0 if L2 < 1e-18 else min(1.0, max(0.0, -(a[0] * dx + a[1] * dy) / L2))
    return math.hypot(a[0] + t * dx, a[1] + t * dy)


def _pt_seg_dist(X, Y, Z, a, b):
    d = np.array(b, float) - np.array(a, float)
    L2 = float(d @ d)
    if L2 < 1e-18:
        return np.sqrt((X - a[0]) ** 2 + (Y - a[1]) ** 2 + (Z - a[2]) ** 2)
    t = ((X - a[0]) * d[0] + (Y - a[1]) * d[1] + (Z - a[2]) * d[2]) / L2
    t = np.clip(t, 0.0, 1.0)
    return np.sqrt((X - a[0] - t * d[0]) ** 2 + (Y - a[1] - t * d[1]) ** 2 + (Z - a[2] - t * d[2]) ** 2)


# ---------------------------------------------------------------------------------------------------
# operator and Maxwell matrix
# ---------------------------------------------------------------------------------------------------
@np.errstate(divide="ignore", invalid="ignore", over="ignore")
def conductances(g, eps, cond, bc):
    """Face conductances (F) of the FV operator: Gr (Nr+1,Np,Nz), Gp (Nr,Np,Nz) [face j+1/2, periodic],
    Gz (Nr,Np,Nz+1). Conductor cells contribute no half-cell resistance (their surface is the face)."""
    Nr, Np, Nz = g.shape
    r0, r1 = g.r[:-1], g.r[1:]
    rc = g.rc
    dp = np.radians(np.diff(g.p))
    dz = np.diff(g.z)
    e = eps * EPS0
    isc = cond >= 0
    # radial half-cell resistances: inner half (r0 -> rc) and outer half (rc -> r1), per unit (dphi dz)
    with np.errstate(divide="ignore"):
        lin = np.where(r0 > 0, np.log(rc / np.where(r0 > 0, r0, 1.0)), np.inf)
    lout = np.log(r1 / rc)
    W = dp[None, :, None] * dz[None, None, :]                      # dphi * dz
    Rin = np.where(isc, 0.0, lin[:, None, None] / (e * W))
    Rout = np.where(isc, 0.0, lout[:, None, None] / (e * W))
    Gr = np.zeros((Nr + 1, Np, Nz))
    Gr[1:-1] = 1.0 / (Rout[:-1] + Rin[1:])
    # outer boundary r = R_enc
    rbnd = Rout[-1]
    if bc["free"]:
        rho = np.sqrt(g.r[-1] ** 2 + g.zc ** 2)[None, None, :]
        A = g.r[-1] * W[-1][None]                                    # face area
        Gr[-1] = 1.0 / (rbnd + rho / (EPS0 * EPS_R["air"] * A))
    else:
        Gr[-1] = 1.0 / rbnd
    # azimuthal: half-cell conductance eps dz ln(r1/r0) / (dphi/2)
    lnr = np.log(r1 / np.where(r0 > 0, r0, r1 * 1e-12))
    lnr[0] = np.log(r1[0] / max(r1[0] * 1e-6, 1e-9)) if r0[0] == 0 else lnr[0]
    Hp = (0.5 * dp)[None, :, None] / (e * lnr[:, None, None] * dz[None, None, :])
    Hp = np.where(isc, 0.0, Hp)
    Gp = 1.0 / (Hp + np.roll(Hp, -1, axis=1))                      # face between j and j+1 (periodic)
    # axial: area 0.5 dphi (r1^2 - r0^2)
    Az = 0.5 * dp[None, :, None] * (r1 ** 2 - r0 ** 2)[:, None, None]
    Hz = np.where(isc, 0.0, (0.5 * dz)[None, None, :] / (e * Az))
    Gz = np.zeros((Nr, Np, Nz + 1))
    Gz[:, :, 1:-1] = 1.0 / (Hz[:, :, :-1] + Hz[:, :, 1:])
    if bc["free"]:
        rho0 = np.sqrt(g.rc ** 2 + g.z[0] ** 2)[:, None]; rho1 = np.sqrt(g.rc ** 2 + g.z[-1] ** 2)[:, None]
        A2 = Az[:, :, 0]
        Gz[:, :, 0] = 1.0 / (Hz[:, :, 0] + rho0 / (EPS0 * EPS_R["air"] * A2))
        Gz[:, :, -1] = 1.0 / (Hz[:, :, -1] + rho1 / (EPS0 * EPS_R["air"] * A2))
    else:
        Gz[:, :, 0] = 1.0 / Hz[:, :, 0]
        Gz[:, :, -1] = 1.0 / Hz[:, :, -1]
    return Gr, Gp, Gz


def maxwell(g, eps, cond, names, bc, tol=1e-5, log=None, solver="auto", return_V=False, r_cut=25.0, V0=None):
    """The Maxwell capacitance matrix of the conductors (F, for the WEDGE; x period count for the build),
    with the enclosure (or infinity) as reference. Returns (C, info).
    r_cut: the core r < r_cut (no conductor there: asserted) is cut out behind a zero-flux face. In the
    60-degree wedge its azimuthal cells shrink to nothing at the axis, which wrecks the multigrid; the
    field there is negligible (the nearest conductor is 30+ mm out; gate FS-CUT reports the effect) [ME]."""
    t0 = time.time()
    Nr, Np, Nz = g.shape
    N = Nr * Np * Nz
    idx = np.arange(N).reshape(g.shape)
    void = np.zeros(g.shape, bool)
    if r_cut and r_cut > 0:
        void[g.rc < r_cut] = True
        if np.any(cond[void] >= 0):
            raise ValueError(f"a conductor lies inside r_cut = {r_cut} mm")
        eps = np.where(void, 1e-300, eps)
    Gr, Gp, Gz = conductances(g, eps, cond, bc)
    with np.errstate(invalid="ignore"):
        pass
    c = cond.ravel()
    # adjacency of two different conductors on the grid = unresolved gap
    bad = 0
    for (a, b) in ((cond[:-1], cond[1:]),):
        bad += int(np.count_nonzero((a >= 0) & (b >= 0) & (a != b)))
    bad += int(np.count_nonzero((cond >= 0) & (np.roll(cond, -1, 1) >= 0) & (cond != np.roll(cond, -1, 1))))
    bad += int(np.count_nonzero((cond[:, :, :-1] >= 0) & (cond[:, :, 1:] >= 0) & (cond[:, :, :-1] != cond[:, :, 1:])))
    rows, cols, vals = [], [], []
    diag = np.zeros(N)

    def add(I, J, G):
        G = G.ravel(); I = I.ravel(); J = J.ravel()
        m = np.isfinite(G) & (G > 0)
        I, J, G = I[m], J[m], G[m]
        rows.append(I); cols.append(J); vals.append(-G)
        rows.append(J); cols.append(I); vals.append(-G)
        diag[:] += np.bincount(I, G, N) + np.bincount(J, G, N)
    add(idx[:-1], idx[1:], Gr[1:-1])
    add(idx, np.roll(idx, -1, axis=1), Gp)
    add(idx[:, :, :-1], idx[:, :, 1:], Gz[:, :, 1:-1])
    # boundary (to the reference)
    gb = np.zeros(g.shape)
    gb[-1] += np.where(np.isfinite(Gr[-1]), Gr[-1], 0.0)
    gb[:, :, 0] += np.where(np.isfinite(Gz[:, :, 0]), Gz[:, :, 0], 0.0)
    gb[:, :, -1] += np.where(np.isfinite(Gz[:, :, -1]), Gz[:, :, -1], 0.0)
    diag += gb.ravel()
    rows = np.concatenate(rows); cols = np.concatenate(cols); vals = np.concatenate(vals)
    A = sp.csr_matrix((vals, (rows, cols)), shape=(N, N))
    A = A + sp.diags(diag)
    u = np.nonzero((c < 0) & ~void.ravel())[0]
    k = np.nonzero(c >= 0)[0]
    nc = len(names)
    S = sp.csr_matrix((np.ones(k.size), (c[k], k)), shape=(nc, N))      # conductor cells -> nets
    Auu = A[u][:, u].tocsr()
    Auk = A[u][:, k]
    Akk = A[k][:, k]
    B = -(Auk @ S[:, k].T).toarray()                                      # rhs per net (n_u x nc)
    t1 = time.time()
    X, it = _solve(Auu, B, tol, log, solver, None if V0 is None else V0.reshape(N, -1)[u])
    t2 = time.time()
    Ckk = (S[:, k] @ Akk @ S[:, k].T).toarray()
    # variational (energy) form: exact X gives Ckk - B^T X; with an approximate X the error is quadratic
    # in the solution error (2 B^T X - X^T A X is stationary at the exact X) [ME]
    BX = B.T @ X
    XAX = X.T @ (Auu @ X)
    C = Ckk - (BX + BX.T - XAX)
    C_lin = Ckk - BX                                                      # the plain Schur complement
    recip = float(np.max(np.abs(C_lin - C_lin.T)) / max(np.max(np.abs(C_lin)), 1e-300))
    C = 0.5 * (C + C.T)
    info = dict(cells=N, unknowns=int(u.size), conductor_cells=int(k.size), adjacent_conductor_faces=bad,
                t_assemble=t1 - t0, t_solve=t2 - t1, iterations=it, reciprocity=recip)
    if return_V:
        V = np.zeros((N, nc), dtype=np.float32); V[u] = X
        for j in range(nc):
            V[k[c[k] == j], j] = 1.0
        info["V"] = V.reshape(g.shape + (nc,))
    return C, info


def _solve(A, B, tol, log, solver, X0=None):
    """A X = B for SPD A. Symmetric diagonal scaling, then CG preconditioned by a Ruge-Stueben AMG V-cycle
    (pyamg); a direct LU for small systems; Jacobi-CG if pyamg is missing [ME]."""
    nrhs = B.shape[1]
    its = []
    if solver == "direct" or A.shape[0] < 4000:
        lu = spla.splu(A.tocsc())
        return lu.solve(B), [0] * nrhs
    dd = 1.0 / np.sqrt(A.diagonal())
    Ds = sp.diags(dd)
    As = (Ds @ A @ Ds).tocsr()
    if pyamg is not None and solver in ("auto", "amg"):
        ml = pyamg.ruge_stuben_solver(As, max_coarse=500)
        M = ml.aspreconditioner(cycle="V")
    else:
        M = None
    X = np.zeros_like(B)
    for j in range(nrhs):
        b = dd * B[:, j]
        if not np.any(b):
            its.append(0); continue
        n_it = [0]

        def cb(xk):
            n_it[0] += 1
        x0 = None if X0 is None else (X0[:, j].astype(float) / dd)
        x, info = spla.cg(As, b, x0=x0, rtol=tol, maxiter=400 if M is not None else 20000, M=M, callback=cb)
        if info != 0:
            raise RuntimeError(f"field_solve: CG did not converge (rhs {j}, info {info})")
        X[:, j] = dd * x; its.append(n_it[0])
    return X, its


def mutual(C, names):
    """Maxwell matrix -> two-terminal capacitances: {(a, b): C_ab} (a < b) and {a: C_a,ref}."""
    n = len(names)
    pair, ref = {}, {}
    for i in range(n):
        ref[names[i]] = float(C[i].sum())
        for j in range(i + 1, n):
            pair[tuple(sorted((names[i], names[j])))] = float(-C[i, j])
    return pair, ref


# ---------------------------------------------------------------------------------------------------
# self-test: an annular parallel-plate pair with a guard (axisymmetric) vs eps A / g
# ---------------------------------------------------------------------------------------------------
def guarded_plates(r_in=20.0, r_out=60.0, gap=4.0, t=1.0, guard=30.0, slit=0.5, eps_slab=None, slab_t=0.0, res=None,
                   enclosure=40.0):
    """Two annular plates (r_in..r_out) facing across `gap`; the top one is surrounded by a guard ring
    (r_out+slit .. r_out+guard) at the same potential, and a guard disc inside r_in-slit; optional
    dielectric slab of eps_slab and thickness slab_t on the lower plate (series case FS4)."""
    prims = []
    sec = lambda name, node, ri, ro, z0, z1, eps=None: dict(kind="sector", cond=node, eps=eps, name=name, r_in=ri, r_out=ro,
                                                            a0=0.0, w=360.0, z0=z0, z1=z1)
    big = r_out + guard
    prims.append(sec("low", "low", 0.0, big, -t, 0.0))
    prims.append(sec("top", "top", r_in, r_out, gap, gap + t))
    prims.append(sec("guard_o", "guard", r_out + slit, big, gap, gap + t))
    if r_in - slit > 0:
        prims.append(sec("guard_i", "guard", 0.0, r_in - slit, gap, gap + t))
    if eps_slab:
        prims.append(sec("slab", None, 0.0, big, 0.0, slab_t, eps_slab))
    g, bc = build_grid(prims, enclosure=enclosure, res=dict(dict(h_max_r=2.0, h_min_r=0.1, h_max_z=0.5, h_min_z=0.1,
                                                                  h_max_p=60.0, h_min_arc=60.0, grow=1.3), **(res or {})))
    eps, cond, names = rasterize(g, prims)
    C, info = maxwell(g, eps, cond, names, bc, solver="direct", r_cut=0.0)
    pair, ref = mutual(C, names)
    return pair[tuple(sorted(("low", "top")))] * 6.0, info, g


def _selftest():
    # the 'top' plate's charge (guard at its potential) against eps0 A / g on the gap mid-slit area
    Cp, info, g = guarded_plates(r_in=20.0, r_out=60.0, gap=2.0, guard=25.0, slit=0.25, res=dict(h_max_r=1.0, h_max_z=0.25))
    A = math.pi * ((60.125) ** 2 - (19.875) ** 2)               # area to the slit centrelines
    ref = EPS0 * EPS_R["air"] * A / 2.0
    if abs(Cp / ref - 1) > 0.01:
        raise AssertionError(f"field_solve self-test: guarded plates {Cp:.4e} vs {ref:.4e}")
    return True


SELFTEST_OK = _selftest()


def regrid_phi(V, pc_old, pc_new, period=PERIOD):
    """periodic linear interpolation of a field V (Nr, Np, Nz, ...) along phi onto new cell centres (the r
    and z grids must agree) -- a warm start for the next relative angle [ME]."""
    x = np.concatenate([pc_old - period, pc_old, pc_old + period])
    Vx = np.concatenate([V, V, V], axis=1)
    i = np.clip(np.searchsorted(x, pc_new) - 1, 0, x.size - 2)
    t = ((pc_new - x[i]) / (x[i + 1] - x[i]))
    shp = [1, -1] + [1] * (V.ndim - 2)
    return (Vx[:, i] * (1 - t).reshape(shp) + Vx[:, i + 1] * t.reshape(shp)).astype(np.float32)
