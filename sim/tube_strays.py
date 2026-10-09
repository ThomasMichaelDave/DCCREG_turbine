"""sim/tube_strays.py -- the tube's strays by a field solve: the electrostatic capacitance matrix of the record's HV parts,
the strays it leaves beside the varicaps' and the transfer capacitors' own, and what they do to the pump.

Writes sim/tube_strays_results.json and docs/figures/tube-strays.png; the findings are sim/tube-strays-findings.md.

The model [IR] (every input read from the record; the files are in SRC):
- the record's solids as laid out (docs/geometry/tube/tube-r150-n6-air6-wound-g0p5-6br-hub50.parts.json, built by
  sim/tube_geometry.py --record from sim/stack_sizing.layout): side A from the hub's equator down to the reluctance
  section's mid-plane (z 100-470 mm of the 940 mm tube); side B is its mirror;
- conductors on nodes (Dirichlet): the 6 rotor vanes (node 1), the 6 stator vanes (REF), the Ca plates (nodes 1 / 2
  alternating, as the netlist), the shaft half, flange and the two bearings in reach (REF), the AH core and coil (REF),
  the three wound utrons (REF, their cores, neck strips and windings), the bridges (floating), ring A with its beads,
  a REF wall at r 400 mm (the room);
- dielectrics per cell: the G10 sleeve, spiders, cage, bridge ring and carrier discs (eps 4.7), the hub's PEEK, gel and
  glass; moist air elsewhere (sim/pump_sizing.eps_air at the record's 20 C, 1013 hPa, 50 %);
- every exposed vane and plate edge a full round of half the thickness (R1.5), as the record states; the rotor ring's
  bore on the sleeve and the stator ring's rim in the cage are not exposed;
- the solve: div(eps grad V) = 0 by node-based finite volumes on a cylindrical tensor grid (r, theta, z) in a 60 deg
  wedge with mirror faces (exact for the record's 6-fold vanes and bridges and its 3 utrons at 0 / 120 / 240 deg); the
  vanes' and plates' faces and every material boundary on grid planes; the conductors' curved and oblique surfaces at
  their sub-cell distance along each edge (Shortley-Weller); CG with smoothed-aggregation AMG (pyamg); the Maxwell
  matrix from the conductors' charges [OC: the method];
- the angles: aligned (C1 at its maximum) and half a pitch on (minimum): the whole rotor (vanes and utrons) against the
  whole counter-rotor (stator vanes and bridges), as the parts list draws them at 0 deg;
- the equator (z 470): a mirror (even mode); one odd-mode solve (the equator at 0 V) gives the couplings across to
  side B [OC]; the hub's rings and the across-hub couplings also from an axisymmetric whole-machine model (vanes as full
  annuli: the bound);
- the periodic cell: one gap of the infinite stack (mirrors at the vanes' mid-planes), without rims (the record's 2-D
  cell in 3-D: the gate) and with them (the interior of the real stack).
Then: floating parts eliminated by their zero charge (Kron) [OC]; the nodes' capacitances; the varicap's own C (rotor
vanes to stator vanes) and Ca's own (Ca's node-1 plates to its node-2 plates) taken out; the rest are the strays.
The pump: sim/core_field.py's deck built by its own function (deck, run), with the 20 pF node strays replaced in this
copy only (and couplings added): the start-up gain z, the clamped power, the rings' symmetric supply as
sim/hub_rings_build.py runs record_supply.
Tags: [OC] derivable physics; [IR] a modelling choice; [RH] a heuristic (CONVENTIONS.md section 1). g is a gap, never d.
Usage: python3 sim/tube_strays.py [--resume] [--procs 2] [--levels 0 1 2]
       (several hours on 4 cores: the level-2 solves are 6-7 M nodes each; --resume reuses the solves already in the
       results file)
"""
import os
os.environ.setdefault("OPENBLAS_NUM_THREADS", "1")      # one BLAS thread per process: the solves run side by side
os.environ.setdefault("OMP_NUM_THREADS", "1")
import argparse        # noqa: E402
import hashlib         # noqa: E402
import json            # noqa: E402
import math            # noqa: E402
import re              # noqa: E402
import sys             # noqa: E402
import time            # noqa: E402
from multiprocessing import Pool    # noqa: E402

import numpy as np     # noqa: E402
import scipy.sparse as sp            # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
import stack_sizing as SS          # noqa: E402  (the layout's constants: shaft, sleeve, bearing, flange, vane band)
import pump_sizing as PS           # noqa: E402  (moist-air eps_r; frozen, imported only)
import core_field as CF            # noqa: E402  (the pump's deck of record)

RESULTS = os.path.join(HERE, "tube_strays_results.json")
FIGURE = os.path.join(ROOT, "docs", "figures", "tube-strays.png")
SRC = {
    "parts": "docs/geometry/tube/tube-r150-n6-air6-wound-g0p5-6br-hub50.parts.json",
    "stack": "sim/air_stack_sizing_results.json",
    "hub": "presets/hub-locked.json",
    "layout": "sim/stack_sizing.py",
    "solids": "sim/tube_geometry.py",
    "utron": "sim/utron_profile.py",
    "op": "sim/pole_design_variants_op.json",
    "deck": "sim/core_field.py",
    "core": "sim/core_field_results.json",
    "rings": "sim/hub_rings_build_results.json",
}
EPS0_MM = 8.8541878128e-15          # F/mm
TOL = 1e-7                          # mm: a node on a face is inside
PICK = "g 0.5 / 6 bridges / 1200 rpm"
WEDGE = 60.0                        # deg, mirror faces
R_BOX = 400.0                       # mm: the REF wall (the room) [IR]
Z_LO = 100.0                        # mm: the domain's lower end, the reluctance section's mid-plane (a mirror) [IR]
LEVELS = {0: dict(hz=1.5, hrf=0.75, hr=2.0, htf=0.6, ht=1.8),
          1: dict(hz=1.0, hrf=0.5, hr=1.5, htf=0.4, ht=1.2),
          2: dict(hz=0.75, hrf=0.375, hr=1.125, htf=0.3, ht=0.9)}
CELL_H = (1.0, 0.5, 0.25)          # mm: the periodic cell's levels


# ======================================================================================== the finite-volume core
def axis(a, b, fixed=(), zones=(), h_far=10.0, grow=1.25):
    """1-D nodes from a to b: every point of `fixed` is a node; the spacing follows the finest zone (x0, x1, h)
    containing x, graded outward at `grow` per cell up to h_far."""
    pts = sorted({float(a), float(b)} | {float(x) for x in fixed if a <= x <= b})

    def h_of(x):
        h = np.full_like(x, h_far, dtype=float)
        for x0, x1, hz in zones:
            dd = np.maximum(0.0, np.maximum(x0 - x, x - x1))
            h = np.minimum(h, hz + (grow - 1.0) * dd)
        return h
    out = [pts[0]]
    for x0, x1 in zip(pts[:-1], pts[1:]):
        xs = np.linspace(x0, x1, 2001)
        inv = 1.0 / h_of(xs)
        cum = np.concatenate([[0.0], np.cumsum(0.5 * (inv[1:] + inv[:-1]) * np.diff(xs))])
        n = max(1, int(math.ceil(cum[-1] - 1e-9)))
        out += list(np.interp(np.linspace(0.0, cum[-1], n + 1)[1:], cum, xs))
        out[-1] = x1
    return np.array(out)


class Problem:
    """conductors on the nodes of a cylindrical tensor grid (ids >= 0; -1 free), a relative permittivity per cell."""

    def __init__(self, r, th, z, eps_bg=1.0):
        self.r, self.th, self.z = np.asarray(r, float), np.asarray(th, float), np.asarray(z, float)
        self.shape = (len(r), len(th), len(z))
        self.cid = np.full(self.shape, -1, dtype=np.int16)
        self.eps = np.full((len(r) - 1, len(th) - 1, len(z) - 1), eps_bg)
        self.solids, self.names = {}, {}

    def _box(self, bb, cells=False):
        sl = []
        for x, lo, hi in ((self.r, bb[0], bb[1]), (self.th, bb[2], bb[3]), (self.z, bb[4], bb[5])):
            i0 = max(0, int(np.searchsorted(x, lo, "left")) - 1)
            i1 = min(len(x) - (1 if cells else 0), int(np.searchsorted(x, hi, "right")) + 1)
            sl.append(slice(i0, max(i0, i1)))
        return tuple(sl)

    def add_conductor(self, cid, name, inside, bb):
        self.solids.setdefault(cid, []).append((inside, bb))
        self.names[cid] = name
        s = self._box(bb)
        R, T, Z = np.meshgrid(self.r[s[0]], self.th[s[1]], self.z[s[2]], indexing="ij")
        sub = self.cid[s]
        sub[inside(R, T, Z)] = cid
        self.cid[s] = sub

    def add_dielectric(self, epsr, inside, bb):
        s = self._box(bb, cells=True)
        c = [0.5 * (x[1:] + x[:-1])[q] for x, q in zip((self.r, self.th, self.z), s)]
        R, T, Z = np.meshgrid(*c, indexing="ij")
        sub = self.eps[s]
        sub[inside(R, T, Z)] = epsr
        self.eps[s] = sub

    def inside_cid(self, cid, R, T, Z):
        m = np.zeros(np.shape(R), dtype=bool)
        for f, bb in self.solids.get(cid, []):
            box = (R >= bb[0] - 1e-9) & (R <= bb[1] + 1e-9) & (T >= bb[2] - 1e-12) & (T <= bb[3] + 1e-12) & \
                  (Z >= bb[4] - 1e-9) & (Z <= bb[5] + 1e-9)
            if box.any():
                m[box] |= f(R[box], T[box], Z[box])
        return m

    def conductances(self):
        """the edge conductances eps0 eps A / L of the dual faces, each split over the four cells that share the edge
        (the radial ones with the exact log law, so a coaxial field is exact) [OC]."""
        r, th, z, E = self.r, self.th, self.z, self.eps
        Nr, Nt, Nz = self.shape
        half = lambda x: 0.5 * (x[1:] + x[:-1])
        lo = lambda x: np.concatenate([[x[0]], half(x)])
        hi = lambda x: np.concatenate([half(x), [x[-1]]])
        wtm, wtp, wzm, wzp = th - lo(th), hi(th) - th, z - lo(z), hi(z) - z
        lrm, lrp = np.log(r / lo(r)), np.log(hi(r) / r)
        arm, arp = 0.5 * (r * r - lo(r) ** 2), 0.5 * (hi(r) ** 2 - r * r)
        P = np.zeros((Nr - 1, Nt + 1, Nz + 1)); P[:, 1:-1, 1:-1] = E
        Gr = (P[:, :-1, :-1] * wtm[None, :, None] * wzm[None, None, :] + P[:, 1:, :-1] * wtp[None, :, None] * wzm[None, None, :]
              + P[:, :-1, 1:] * wtm[None, :, None] * wzp[None, None, :] + P[:, 1:, 1:] * wtp[None, :, None] * wzp[None, None, :])
        Gr *= (EPS0_MM / np.log(r[1:] / r[:-1]))[:, None, None]
        P = np.zeros((Nr + 1, Nt - 1, Nz + 1)); P[1:-1, :, 1:-1] = E
        Gt = (P[:-1, :, :-1] * lrm[:, None, None] * wzm[None, None, :] + P[1:, :, :-1] * lrp[:, None, None] * wzm[None, None, :]
              + P[:-1, :, 1:] * lrm[:, None, None] * wzp[None, None, :] + P[1:, :, 1:] * lrp[:, None, None] * wzp[None, None, :])
        Gt *= (EPS0_MM / np.diff(th))[None, :, None]
        P = np.zeros((Nr + 1, Nt + 1, Nz - 1)); P[1:-1, 1:-1, :] = E
        Gz = (P[:-1, :-1, :] * arm[:, None, None] * wtm[None, :, None] + P[1:, :-1, :] * arp[:, None, None] * wtm[None, :, None]
              + P[:-1, 1:, :] * arm[:, None, None] * wtp[None, :, None] + P[1:, 1:, :] * arp[:, None, None] * wtp[None, :, None])
        Gz *= (EPS0_MM / np.diff(z))[None, None, :]
        return Gr, Gt, Gz

    def _fractions(self, ax, ca, cb, n_bis=12, s_min=0.05):
        """the edges along axis ax with one free and one conductor end: the fraction s of the edge from the free node to
        the conductor's surface, by bisection on that conductor's own inside test (Shortley-Weller) [IR]."""
        idx = np.nonzero((ca < 0) ^ (cb < 0))
        s = np.ones(len(idx[0]))
        if not len(s):
            return idx, s
        i, j, k = idx
        b_ = (i + 1, j, k) if ax == 0 else ((i, j + 1, k) if ax == 1 else (i, j, k + 1))
        fa = ca[idx] < 0
        F = [np.where(fa, a, b) for a, b in zip((i, j, k), b_)]
        Cn = [np.where(fa, b, a) for a, b in zip((i, j, k), b_)]
        cond = np.where(fa, cb[idx], ca[idx])
        RF, TF, ZF = self.r[F[0]], self.th[F[1]], self.z[F[2]]
        RC, TC, ZC = self.r[Cn[0]], self.th[Cn[1]], self.z[Cn[2]]
        for c in np.unique(cond):
            if c not in self.solids:                       # walls and planes marked on nodes: the surface is the node
                continue
            m = cond == c
            l_, h_ = np.zeros(int(m.sum())), np.ones(int(m.sum()))
            for _ in range(n_bis):
                mid = 0.5 * (l_ + h_)
                ins = self.inside_cid(c, RF[m] + mid * (RC[m] - RF[m]), TF[m] + mid * (TC[m] - TF[m]), ZF[m] + mid * (ZC[m] - ZF[m]))
                h_, l_ = np.where(ins, mid, h_), np.where(ins, l_, mid)
            s[m] = np.maximum(s_min, h_)
        return idx, s

    def assemble(self, log=print):
        t0 = time.time()
        cid = self.cid
        free = cid < 0
        nf = int(free.sum())
        fidx = np.full(self.shape, -1, dtype=np.int64)
        fidx[free] = np.arange(nf)
        self.ncond = nc = int(cid.max()) + 1
        rows, cols, vals, B = [], [], [], []
        diag = np.zeros(nf)
        direct = np.zeros((nc, nc))
        for ax, G in enumerate(self.conductances()):
            sa_, sb_ = [slice(None)] * 3, [slice(None)] * 3
            sa_[ax], sb_[ax] = slice(0, self.shape[ax] - 1), slice(1, self.shape[ax])
            ca, cb = cid[tuple(sa_)], cid[tuple(sb_)]
            fa_, fb_ = fidx[tuple(sa_)], fidx[tuple(sb_)]
            both = (ca < 0) & (cb < 0)
            g, a_, b_ = G[both], fa_[both], fb_[both]
            rows += [a_, b_]; cols += [b_, a_]; vals += [-g, -g]
            diag += np.bincount(a_, g, nf) + np.bincount(b_, g, nf)
            idx, s = self._fractions(ax, ca, cb)
            ge = G[idx] / s
            fa = ca[idx] < 0
            fn = np.where(fa, fa_[idx], fb_[idx])
            cn = np.where(fa, cb[idx], ca[idx]).astype(np.int64)
            diag += np.bincount(fn, ge, nf)
            B.append((cn, fn, ge))
            cc = (ca >= 0) & (cb >= 0) & (ca != cb)
            if cc.any():
                np.add.at(direct, (ca[cc], cb[cc]), G[cc]); np.add.at(direct, (cb[cc], ca[cc]), G[cc])
        rows.append(np.arange(nf)); cols.append(np.arange(nf)); vals.append(diag)
        self.A = sp.csr_matrix((np.concatenate(vals), (np.concatenate(rows), np.concatenate(cols))), shape=(nf, nf))
        self.B = sp.csr_matrix((np.concatenate([b[2] for b in B]), (np.concatenate([b[0] for b in B]),
                                np.concatenate([b[1] for b in B]))), shape=(nc, nf))
        self.direct, self.nf = direct, nf
        log(f"    {nf / 1e6:.2f} M free nodes of {free.size / 1e6:.2f} M, {nc} conductors; adjacent across conductors "
            f"{direct.sum() * 1e12:.2f} pF ({time.time() - t0:.0f} s)")

    def maxwell(self, excite, tol=1e-10, log=print):
        """columns of the Maxwell matrix (pF): C[a, b] = the charge on a with b at 1 V and every other conductor at 0;
        the columns not driven are NaN."""
        import pyamg
        t0 = time.time()
        ml = pyamg.smoothed_aggregation_solver(self.A, symmetry="hermitian", strength=("symmetric", {"theta": 0.0}),
                                               max_coarse=1000)
        log(f"    AMG {len(ml.levels)} levels ({time.time() - t0:.0f} s)")
        sig = np.asarray(self.B.sum(axis=1)).ravel()
        n = self.ncond
        C = np.full((n, n), np.nan)
        its = {}
        for c in excite:
            t1 = time.time()
            res = []
            x = ml.solve(np.asarray(self.B[c, :].todense()).ravel(), tol=tol, accel="cg", maxiter=600, residuals=res)
            q = -(self.B @ x)
            q[c] += sig[c] + self.direct[c, :].sum()
            q -= self.direct[:, c]
            C[:, c] = q * 1e12
            its[self.names.get(c, str(c))] = len(res)
            log(f"    {self.names.get(c, c)}: {len(res)} CG iterations, {res[-1] / res[0]:.0e} ({time.time() - t1:.0f} s)")
        return C, its


# ============================================================================================== the geometry
def _sector_dist(X, Y, alpha, rho, R_lim, outer):
    """in-plane distance from (X, Y) to a sector's spine: |angle| <= alpha about the x axis, eroded by rho from its two
    radial sides, bounded by the arc |q| <= R_lim (outer) or |q| >= R_lim. Candidates: the projections onto the eroded
    side and the arc where they land on the spine, and their corner [OC: convex-piece distance]."""
    Y = np.abs(Y)
    sa, ca = math.sin(alpha), math.cos(alpha)
    sL = rho - (X * sa - Y * ca)
    rq = np.hypot(X, Y)
    sA = (rq - R_lim) if outer else (R_lim - rq)
    d = np.full(np.shape(X), np.inf)
    rL = np.hypot(X + sL * sa, Y - sL * ca)
    d = np.where((sL > 0) & ((rL <= R_lim) if outer else (rL >= R_lim)), np.minimum(d, sL), d)
    with np.errstate(invalid="ignore", divide="ignore"):
        ok = (sA > 0) & ((R_lim * X / rq) * sa - (R_lim * Y / rq) * ca >= rho)
    d = np.where(ok, np.minimum(d, sA), d)
    tau = math.sqrt(R_lim * R_lim - rho * rho)
    d = np.minimum(d, np.hypot(X - (rho * sa + tau * ca), Y - (-rho * ca + tau * sa)))
    return np.where((sL <= 0) & (sA <= 0), 0.0, d)


class Vane:
    """a vane or plate with every exposed edge a full round of half its thickness: the solid is every point within
    t / 2 of its spine (the outline eroded by t / 2 at the exposed edges, in the mid-plane) [IR].
    'rotor': 6 sectors r_in..r_out and a ring r_ring_in..r_in (its bore on the sleeve, not rounded);
    'stator': 6 sectors r_in..r_out and a ring r_out..r_ring_out (its rim in the cage, not rounded);
    'plate': a full annulus r_in..r_out (both rims rounded). sectors=False: the axisymmetric bound (full annuli)."""

    def __init__(self, kind, z0, z1, centre_deg=0.0, half_deg=11.0, r_in=50.0, r_out=150.0, r_ring_in=20.5,
                 r_ring_out=162.0, sectors=True, pitch_deg=60.0):
        self.kind, self.z0, self.z1 = kind, z0, z1
        self.zm, self.rho = 0.5 * (z0 + z1), 0.5 * (z1 - z0)
        self.c, self.per, self.al = math.radians(centre_deg), math.radians(pitch_deg), math.radians(half_deg)
        self.ri, self.ro, self.rri, self.rro, self.sectors = r_in, r_out, r_ring_in, r_ring_out, sectors

    def bbox(self, t0=-1.0, t1=2.0):
        return (self.rri if self.kind == "rotor" else self.ri, self.rro if self.kind == "stator" else self.ro, t0, t1,
                self.z0, self.z1)

    def d2(self, R, T):
        rho = self.rho
        if self.kind == "plate":
            return np.maximum(0.0, np.maximum((self.ri + rho) - R, R - (self.ro - rho)))
        if not self.sectors:
            return np.maximum(0.0, R - (self.ro - rho)) if self.kind == "rotor" else np.maximum(0.0, (self.ri + rho) - R)
        dl = np.mod(T - self.c + 0.5 * self.per, self.per) - 0.5 * self.per
        X, Y = R * np.cos(dl), R * np.sin(dl)
        if self.kind == "rotor":
            return np.minimum(_sector_dist(X, Y, self.al, rho, self.ro - rho, True), np.maximum(0.0, R - (self.ri - rho)))
        return np.minimum(_sector_dist(X, Y, self.al, rho, self.ri + rho, False), np.maximum(0.0, (self.ro + rho) - R))

    def inside(self, R, T, Z):
        dz = Z - self.zm
        lim = self.rho * (1 + 1e-9) + TOL
        m = np.abs(dz) <= lim
        out = np.zeros(np.shape(R), dtype=bool)
        if m.any():
            ok = dz[m] ** 2 + self.d2(R[m], T[m]) ** 2 <= lim * lim
            if self.kind == "rotor":
                ok &= R[m] >= self.rri - TOL
            elif self.kind == "stator":
                ok &= R[m] <= self.rro + TOL
            out[m] = ok
        return out


def ann(r0, r1, z0, z1):
    return lambda R, T, Z: (R >= r0 - TOL) & (R <= r1 + TOL) & (Z >= z0 - TOL) & (Z <= z1 + TOL)


def ann_c(r0, r1, z0, z1):
    return lambda R, T, Z: (R > r0) & (R < r1) & (Z > z0) & (Z < z1)


def _rrect(u, w, u0, u1, w0, w1, Rc):
    du = np.maximum(0.0, np.maximum((u0 + Rc) - u, u - (u1 - Rc)))
    dw = np.maximum(0.0, np.maximum((w0 + Rc) - w, w - (w1 - Rc)))
    return (u >= u0 - TOL) & (u <= u1 + TOL) & (w >= w0 - TOL) & (w <= w1 + TOL) & (du * du + dw * dw <= Rc * Rc + TOL)


def utron_inside(sp_, zs0, ang_deg):
    """a wound utron's metal: the two L-shaped half-cores (back iron and tip, the tip faces on the gap arc), the NiFe
    strip and the winding (a rounded-rectangle loop round the back iron), in the utron's frame: u radial, v tangential,
    w axial from the stack's lower end (sim/utron_profile.py spec / rects / coil_ring / half_core) [IR: the studs' holes,
    the G10 spacer, slot cover and cheeks left out]."""
    a, L = math.radians(ang_deg), sp_["L"]
    o = (sp_["u_m0"], sp_["u_p1"], -sp_["over"], L + sp_["over"], sp_["over"])
    i = (sp_["u_m1"] + 1e-6, sp_["u_p0"] - 1e-6, -sp_["clr"] + 1e-6, L + sp_["clr"] - 1e-6, sp_["clr"])
    s2, wp = 0.5 * sp_["s"], sp_["w_p"]

    def f(R, T, Z):
        u, v, w = R * np.cos(T - a), R * np.sin(T - a), Z - zs0
        av = np.abs(v)
        stack = (w >= -TOL) & (w <= L + TOL)
        back = (u >= sp_["u_n1"] - TOL) & (u <= sp_["u_y1"] + TOL) & (av >= 0.5 * sp_["brk"] - TOL) & (av <= s2 + wp + TOL)
        tip = (u >= sp_["u_y1"] - TOL) & (av >= s2 - TOL) & (av <= s2 + wp + TOL) & (R <= sp_["r_g"] + TOL)
        strip = (u >= sp_["u_y0"] - TOL) & (u <= sp_["u_n1"] + TOL) & (av <= 0.5 * sp_["W_u"] + TOL)
        wind = (av <= sp_["cv"] + TOL) & _rrect(u, w, *o) & ~_rrect(u, w, *i)
        return (stack & (back | tip | strip)) | wind
    return f


def sector_inside(r0, r1, z0, z1, centre_deg, half_deg):
    c, h = math.radians(centre_deg), math.radians(half_deg)
    return lambda R, T, Z: (R >= r0 - TOL) & (R <= r1 + TOL) & (Z >= z0 - TOL) & (Z <= z1 + TOL) & (np.abs(T - c) <= h + 1e-9)


_INPUTS = {}


def inputs():
    """the record's inputs (cached per process)."""
    if not _INPUTS:
        rows = json.load(open(os.path.join(ROOT, SRC["stack"])))["thick_vanes"]["compare"]
        rec = [q for q in rows if q["t_vaneMm"] == 3.0 and q["n_plates"] == 6][0]
        lay = json.load(open(os.path.join(ROOT, SRC["parts"])))
        hub = json.load(open(os.path.join(ROOT, SRC["hub"])))
        import utron_profile as U                       # the spec exactly as sim/tube_geometry.py wound_rel builds it
        op = json.load(open(os.path.join(ROOT, SRC["op"])))["designs"][PICK]
        vrows = json.load(open(os.path.join(HERE, "pole_design_variants.json")))["rows"]
        row = [r for r in vrows if r["design"] == op["design"]]
        sp_ = U.spec(op["design"], op["best"], row[0] if row else None)
        eps_air = PS.eps_r(dict(SS.TUBE_DEFAULTS, dielectric="air"))
        _INPUTS.update(rec=rec, lay=lay, hub=hub, sp=sp_, eps_air=eps_air)
    return _INPUTS


# side model conductors: the driven ones first (their columns are solved), then the REF parts (always 0 V)
SIDE = ["N1v", "N1c", "N2", "SA", "BRa", "BRb", "UT", "W", "RA", "SHAFT", "BRG", "MID"]
SID = {n: k for k, n in enumerate(SIDE)}
REF_PARTS = ("SA", "SHAFT", "BRG", "MID", "UT", "W")      # at REF in the record (UT and W: variants float them)


def build_side(level=1, unaligned=False, mid="mirror", spacers=False, log=print):
    """side A of the record, z Z_LO..470, the 60 deg mirror wedge. unaligned: the counter-rotor (stator vanes, bridges)
    turned half a pitch, 30 deg, against the rotor (vanes, utrons) [OC: the record's 6-fold vanes, 6 bridges, 3 utrons
    keep their mirror faces at 0 and 60 deg]. mid 'zero': the equator at 0 V (the odd mode). spacers: a variant [RH], the
    node-1 parts joined by conductive rings on the sleeve (not the record)."""
    I = inputs()
    rec, lay, hub, sp_ = I["rec"], I["lay"], I["hub"], I["sp"]
    Lv = LEVELS[level]
    half = 0.5 * rec["wr_deg"]
    els = lay["elements"]
    A = [e for e in els if e["side"] == "A"]
    hubel = [e for e in els if e["kind"] == "hub"][0]
    zc = 0.5 * (hubel["z0"] + hubel["z1"])
    vanes = [e for e in A if e["kind"] == "C1 vane"]
    plates = [e for e in A if e["kind"] == "Ca plate"]
    brg = [e for e in A if e["kind"] == "bearing"]
    fl = [e for e in A if e["kind"] == "flange"][0]
    wu = [e for e in A if e["kind"] == "w utron"][0]
    wb = [e for e in A if e["kind"] == "w bridge"][0]
    wr = [e for e in A if e["kind"] == "w ring"][0]
    wd = [e for e in A if e["kind"] == "w disc"]
    B = SS.BEARING
    ri, ro = SS.TUBE_DEFAULTS["r_inMm"], SS.TUBE_DEFAULTS["r_outMm"]
    ah = hub["AH"]["value"]
    core, former, coil = ah["core"], ah["former"], ah["coil"]
    # ---- the grid: every face and material boundary on a node
    zf = [Z_LO, zc] + [x for e in vanes + plates for x in (e["z0"], e["z1"])]
    for b in brg:
        zf += [b["zc"] + s * 0.5 * B["width"] for s in (-1, 1)] + [b["zc"] + s * 0.5 * B["spider_t"] for s in (-1, 1)]
        zf += [b["z0"], b["z1"]]
    zf += [fl["z0"], fl["z1"], wu["zs1"], wu["z1"], wb["z1"], wr["z1"], zc - core["absz_mm"][1], zc - core["absz_mm"][0]]
    zf += [x for dsk in wd for x in (dsk["z0"], dsk["z1"])]
    z0s, z1s = min(e["z0"] for e in plates) - 4.0, max(e["z1"] for e in vanes) + 5.0
    z = axis(Z_LO, zc, zf, [(z0s, z1s, Lv["hz"]), (z0s - 24, z0s, 1.5 * Lv["hz"]), (z1s, z1s + 30, 1.5 * Lv["hz"])],
             h_far=6.0, grow=1.15)
    rf = [3.0, 0.5 * core["d_mm"], 0.5 * former["id_mm"], 0.5 * former["od_mm"], coil["r_mm"][1], SS.SHAFT_R, SS.SLEEVE_R,
          0.5 * B["od"], SS.FLANGE_R, 30.0, 33.0, 23.5, 25.0, 25.5, ri - 1.5, ri, ri + 1.5, wu["r0"], sp_["r_g"], wb["r0"],
          wr["r0"], wb["r1"], ro - 1.5, ro, ro + 1.5, wr["r1"], ro + 12.0, ro + 16.0, R_BOX]
    r = axis(3.0, R_BOX, rf, [(45, 55, Lv["hrf"]), (145, 155, Lv["hrf"]), (12.5, 45, Lv["hr"]), (155, 170, Lv["hr"]),
                              (55, 145, 2 * Lv["hr"]), (128, 133, 0.5), (3, 12.5, 3.0)], h_far=30.0, grow=1.18)
    ctr = 30.0 if unaligned else 0.0
    edges = sorted({half, WEDGE - half} | ({ctr - half, ctr + half} if unaligned else set()))
    bh = 0.5 * wb["width_deg"]
    tf = [0.0, WEDGE] + ([ctr - bh, ctr + bh] if unaligned else [bh, WEDGE - bh]) + edges
    th = axis(0.0, WEDGE, tf, [(e - 2.0, e + 2.0, Lv["htf"]) for e in edges] + [(0, WEDGE, Lv["ht"])], h_far=Lv["ht"],
              grow=1.2)
    P = Problem(r, np.radians(th), z, eps_bg=I["eps_air"])
    log(f"    side A, level {level}, {'unaligned' if unaligned else 'aligned'}{', odd mode' if mid == 'zero' else ''}"
        f"{', spacers' if spacers else ''}: r {len(r)} x theta {len(th)} x z {len(z)} = {P.cid.size / 1e6:.2f} M nodes")
    T0, T1 = -1.0, math.radians(WEDGE) + 1.0
    # ---- dielectrics [IR: datasheet-class eps, presets/hub-locked.json]
    g10 = hub["shaft_coupler"]["value"]["eps_r"]
    for b in brg:
        P.add_dielectric(g10, ann_c(0.5 * B["od"], ro + 12, b["zc"] - 0.5 * B["spider_t"], b["zc"] + 0.5 * B["spider_t"]),
                         (0.5 * B["od"], ro + 12, T0, T1, b["zc"] - 5, b["zc"] + 5))
    bz = sorted(brg, key=lambda e: e["z0"])
    for b0, b1 in zip(bz[:-1], bz[1:]):              # the sleeve between neighbouring bearing hubs (sim/tube_geometry.py)
        P.add_dielectric(g10, ann_c(SS.SHAFT_R, SS.SLEEVE_R, b0["z1"], b1["z0"]), (SS.SHAFT_R, SS.SLEEVE_R, T0, T1, b0["z1"], b1["z0"]))
    zc0 = min(b["z0"] for b in brg if b["where"] != "end")
    P.add_dielectric(g10, ann_c(ro + 12, ro + 16, zc0, zc + 1), (ro + 12, ro + 16, T0, T1, zc0, zc + 1))      # the cage
    P.add_dielectric(g10, ann_c(wr["r0"], wr["r1"], Z_LO - 1, wr["z1"]), (wr["r0"], wr["r1"], T0, T1, Z_LO - 1, wr["z1"]))
    for dsk in wd:
        P.add_dielectric(g10, ann_c(dsk["r0"], dsk["r1"], dsk["z0"], dsk["z1"]), (dsk["r0"], dsk["r1"], T0, T1, dsk["z0"], dsk["z1"]))
    ves, wall = hub["vessel"]["value"], hub["vessel_wall"]["value"]["t_mm"]
    Ro = 0.5 * ves["od_mm"]
    gel = hub["interface_filler"]["value"]
    Rg = Ro + gel["t_mm"]
    ret, cpl = hub["retainer"]["value"], hub["shaft_coupler"]["value"]
    zr0 = zc - ret["absz_max_mm"]
    rs = lambda R, Z: np.hypot(R, Z - zc)
    bore = lambda R, Z: (R < coil["r_mm"][1]) & (Z < zc - core["absz_mm"][0])
    P.add_dielectric(ret["eps_r"], lambda R, T, Z: (R < ret["r_max_mm"]) & (Z > zr0) & (rs(R, Z) > Rg) & ~bore(R, Z),
                     (0, ret["r_max_mm"], T0, T1, zr0, zc))
    P.add_dielectric(gel["eps_r"], lambda R, T, Z: (rs(R, Z) > Ro) & (rs(R, Z) < Rg), (0, Rg, T0, T1, zc - Rg, zc))
    P.add_dielectric(ves["eps_r"], lambda R, T, Z: (rs(R, Z) > Ro - wall) & (rs(R, Z) < Ro), (0, Ro, T0, T1, zc - Ro, zc))
    P.add_dielectric(g10, ann_c(0.5 * former["id_mm"], 0.5 * former["od_mm"], zc - core["absz_mm"][1], zc - core["absz_mm"][0]),
                     (0, 9, T0, T1, zr0, zc))
    P.add_dielectric(cpl["eps_r"], ann_c(ret["r_max_mm"], ret["r_max_mm"] + cpl["wall_mm"], zr0, zc + 1),
                     (ret["r_max_mm"], 34, T0, T1, zr0, zc + 1))
    # ---- conductors
    for e in vanes:
        v = Vane(e["body"], e["z0"], e["z1"], 0.0 if e["body"] == "rotor" else ctr, half, ri, ro, SS.SLEEVE_R, ro + 12.0)
        P.add_conductor(SID["N1v" if e["body"] == "rotor" else "SA"], "N1v" if e["body"] == "rotor" else "SA", v.inside, v.bbox(T0, T1))
    for e in plates:
        v = Vane("plate", e["z0"], e["z1"], r_in=ri, r_out=ro)
        nm = "N1c" if e["node"] == "1" else "N2"
        P.add_conductor(SID[nm], nm, v.inside, v.bbox(T0, T1))
        if spacers and e["node"] == "1":             # [RH] the node-1 plates on rings on the sleeve (not the record)
            P.add_conductor(SID[nm], nm, ann(SS.SLEEVE_R, ri, e["z0"], e["z1"]), (SS.SLEEVE_R, ri, T0, T1, e["z0"], e["z1"]))
    if spacers:                                      # [RH] a node-1 spacer tube r 20.5-30 on the sleeve, Ca_05 to r02
        za, zb = min(e["z0"] for e in plates if e["node"] == "1"), max(e["z1"] for e in vanes if e["body"] == "rotor")
        P.add_conductor(SID["N1v"], "N1v", ann(SS.SLEEVE_R, 30.0, za, zb), (SS.SLEEVE_R, 30.0, T0, T1, za, zb))
    P.add_conductor(SID["SHAFT"], "SHAFT", lambda R, T, Z: (R <= SS.SHAFT_R + TOL) & (Z <= fl["z0"] + TOL),
                    (0, SS.SHAFT_R, T0, T1, Z_LO - 1, fl["z0"]))
    P.add_conductor(SID["SHAFT"], "SHAFT", ann(0, SS.FLANGE_R, fl["z0"], fl["z1"]), (0, SS.FLANGE_R, T0, T1, fl["z0"], fl["z1"]))
    for (r0_, r1_), zz in (((0.0, 0.5 * core["d_mm"]), core["absz_mm"]), (tuple(coil["r_mm"]), coil["absz_mm"])):
        P.add_conductor(SID["SHAFT"], "SHAFT", ann(r0_, r1_, zc - zz[1], zc - zz[0]), (r0_, r1_, T0, T1, zc - zz[1], zc - zz[0]))
    for b in brg:
        zb0, zb1 = b["zc"] - 0.5 * B["width"], b["zc"] + 0.5 * B["width"]
        P.add_conductor(SID["BRG"], "BRG", ann(SS.SHAFT_R, 0.5 * B["od"], zb0, zb1), (SS.SHAFT_R, 0.5 * B["od"], T0, T1, zb0, zb1))
    for a in wu["angles"]:
        if a <= WEDGE + 20.0:
            P.add_conductor(SID["UT"], "UT", utron_inside(sp_, wu["zs0"], a), (wu["r0"] - 2, sp_["r_g"] + 3, T0, T1, wu["z0"], wu["z1"]))
    for a, nm in ([(ctr, "BRa")] if unaligned else [(0.0, "BRa"), (WEDGE, "BRb")]):
        P.add_conductor(SID[nm], nm, sector_inside(wb["r0"], wb["r1"], wb["z0"], wb["z1"], a, bh), (wb["r0"], wb["r1"], T0, T1, wb["z0"], wb["z1"]))
    rg = hub["rings"]["value"]
    tp, te = math.radians(rg["polar_edge_deg"]), math.radians(rg["equatorial_edge_deg"])

    def ring_a(R, T, Z):                             # the foil (thickened to the gel's 0.5 mm for the grid) and its beads
        rr, ang = rs(R, Z), np.arctan2(R, zc - Z)
        out = (rr >= Ro - TOL) & (rr <= Rg + TOL) & (ang >= tp - 1e-9) & (ang <= te + 1e-9)
        for th_, d_ in ((tp, rg["bead_d_mm"]["polar"]), (te, rg["bead_d_mm"]["equatorial"])):
            Rc = Ro + 0.5 * d_
            out = out | ((R - Rc * math.sin(th_)) ** 2 + (Z - (zc - Rc * math.cos(th_))) ** 2 <= 0.25 * d_ * d_ + TOL)
        return out
    P.add_conductor(SID["RA"], "RA", ring_a, (0, Rg + 2, T0, T1, zc - Rg - 2, zc))
    P.cid[-1, :, :] = SID["W"]; P.names[SID["W"]] = "W"
    if mid == "zero":
        P.cid[:, :, -1] = np.where(P.cid[:, :, -1] < 0, SID["MID"], P.cid[:, :, -1]); P.names[SID["MID"]] = "MID"
    return P


def build_cell(h=0.5, unaligned=False, rims=True, clear=0.0, log=print):
    """one gap of the infinite periodic stack: mirrors at a stator vane's and the next rotor vane's mid-planes, the
    30 deg mirror wedge. rims=False: the record's 2-D cell in 3-D (Neumann at r 50 / 150, the sectors only, no rims).
    rims=True: the real radial build (shaft, sleeve, the rotor ring, the stator ring, the cage, the REF wall).
    clear > 0 [RH, not the record]: the rotor ring's edge and the rotor sectors' outer rims pulled back by clear, the
    stator sectors' inner rims and the stator ring's edge pushed out by clear (the overlap shrinks to r 50+c..150-c)."""
    I = inputs()
    rec = I["rec"]
    t, g, half = rec["t_vaneMm"], rec["gap_mm"], 0.5 * rec["wr_deg"]
    zs, zr = 0.0, t + g
    z = axis(zs, zr, [0.5 * t, zr - 0.5 * t], [(zs, zr, h)])
    ctr = 30.0 if unaligned else 0.0
    edges = [half] + ([ctr - half] if unaligned else [])
    th = axis(0, 30.0, [0, 30] + edges, [(e - 2.5, e + 2.5, 0.4 * h) for e in edges] + [(0, 30, 1.2 * h)], h_far=1.2 * h, grow=1.2)
    ri, ro = SS.TUBE_DEFAULTS["r_inMm"], SS.TUBE_DEFAULTS["r_outMm"]
    if rims:
        rf = [3.0, SS.SHAFT_R, SS.SLEEVE_R, ro + 12, ro + 16, R_BOX] + [x + s * 1.5 for x in (ri - clear, ri + clear, ro - clear, ro + clear)
                                                                     for s in (-1, 0, 1)]
        r = axis(3.0, R_BOX, rf, [(ri - clear - 5, ri + clear + 5, h), (ro - clear - 5, ro + clear + 5, h), (12.5, 45, 2 * h),
                                  (155, 170, 2 * h), (55, 145, 4 * h), (3, 12.5, 3.0)], h_far=30.0, grow=1.18)
    else:
        r = axis(ri, ro, [], [(ri, ro, 5.0)])
    P = Problem(r, np.radians(th), z, eps_bg=I["eps_air"])
    T0, T1 = -1.0, 2.0
    if rims:
        st = Vane("stator", zs - 0.5 * t, zs + 0.5 * t, ctr, half, ri + clear, ro, ro + clear, ro + 12.0)
        rt = Vane("rotor", zr - 0.5 * t, zr + 0.5 * t, 0.0, half, ri - clear, ro - clear, SS.SLEEVE_R, ro + 12.0)
        g10 = I["hub"]["shaft_coupler"]["value"]["eps_r"]
        P.add_dielectric(g10, ann_c(SS.SHAFT_R, SS.SLEEVE_R, -1, zr + 1), (SS.SHAFT_R, SS.SLEEVE_R, T0, T1, -1, zr + 1))
        P.add_dielectric(g10, ann_c(ro + 12, ro + 16, -1, zr + 1), (ro + 12, ro + 16, T0, T1, -1, zr + 1))
        P.add_conductor(SID["SHAFT"], "SHAFT", lambda R, T, Z: R <= SS.SHAFT_R + TOL, (0, SS.SHAFT_R, T0, T1, -1, zr + 1))
        P.cid[-1, :, :] = SID["W"]; P.names[SID["W"]] = "W"
    else:
        st = Vane("stator", zs - 0.5 * t, zs + 0.5 * t, ctr, half, 0.0, 1000.0)
        rt = Vane("rotor", zr - 0.5 * t, zr + 0.5 * t, 0.0, half, 0.0, 1000.0, 0.0)
    P.add_conductor(SID["N1v"], "N1v", rt.inside, (0, 1e4, T0, T1, zr - t, zr + t))
    P.add_conductor(SID["SA"], "SA", st.inside, (0, 1e4, T0, T1, zs - t, zs + t))
    return P


AXI = ["N1", "N2", "N3", "N4", "STA", "RA", "RB", "REF", "W"]
AID = {n: k for k, n in enumerate(AXI)}


def build_axi(h=0.5, h_hub=0.25, log=print):
    """the whole machine as a body of revolution, both sides and the hub: the vanes as full annuli (the axisymmetric
    bound: the sectors smeared [IR]); the utrons and bridges left out (not bodies of revolution)."""
    I = inputs()
    lay, hub = I["lay"], I["hub"]
    els = lay["elements"]
    hubel = [e for e in els if e["kind"] == "hub"][0]
    zc = 0.5 * (hubel["z0"] + hubel["z1"])
    B = SS.BEARING
    brg = [e for e in els if e["kind"] == "bearing"]
    vanes = [e for e in els if e["kind"] in ("C1 vane", "C2 vane")]
    plates = [e for e in els if e["kind"] in ("Ca plate", "Cb plate")]
    fls = [e for e in els if e["kind"] == "flange"]
    z_lo, z_hi = min(e["z0"] for e in els), max(e["z1"] for e in els)
    ah = hub["AH"]["value"]
    core, former, coil = ah["core"], ah["former"], ah["coil"]
    ret, cpl = hub["retainer"]["value"], hub["shaft_coupler"]["value"]
    zf = [z_lo, z_hi] + [x for e in vanes + plates + fls for x in (e["z0"], e["z1"])]
    for b in brg:
        zf += [b["zc"] + s * 0.5 * B["width"] for s in (-1, 1)] + [b["zc"] + s * 0.5 * B["spider_t"] for s in (-1, 1)] + [b["z0"], b["z1"]]
    for sg in (-1, 1):
        zf += [zc + sg * x for x in list(core["absz_mm"]) + list(coil["absz_mm"]) + [ret["absz_max_mm"]]]
    zA = (min(e["z0"] for e in plates if e["side"] == "A") - 4, max(e["z1"] for e in vanes if e["side"] == "A") + 5)
    zB = (min(e["z0"] for e in vanes if e["side"] == "B") - 5, max(e["z1"] for e in plates if e["side"] == "B") + 4)
    z = axis(z_lo, z_hi, zf, [(zA[0], zA[1], h), (zB[0], zB[1], h), (zc - 40, zc + 40, h_hub), (zc - 90, zc + 90, 2 * h)],
             h_far=8.0, grow=1.12)
    ri, ro = SS.TUBE_DEFAULTS["r_inMm"], SS.TUBE_DEFAULTS["r_outMm"]
    rf = [1.0, 0.5 * core["d_mm"], 0.5 * former["id_mm"], 0.5 * former["od_mm"], coil["r_mm"][0], coil["r_mm"][1], SS.SHAFT_R,
          SS.SLEEVE_R, 0.5 * B["od"], SS.FLANGE_R, ret["r_max_mm"], ret["r_max_mm"] + cpl["wall_mm"], 23.5, 25.0, 25.5,
          ri - 1.5, ri, ri + 1.5, ro - 1.5, ro, ro + 1.5, ro + 12, ro + 16, R_BOX]
    r = axis(1.0, R_BOX, rf, [(5, 34, h_hub), (45, 55, h), (145, 155, h), (12.5, 170, 2 * h)], h_far=25.0, grow=1.12)
    P = Problem(r, np.radians([0.0, 1.0]), z, eps_bg=I["eps_air"])
    T0, T1 = -1.0, 1.0
    g10 = hub["shaft_coupler"]["value"]["eps_r"]
    for b in brg:
        P.add_dielectric(g10, ann_c(0.5 * B["od"], ro + 12, b["zc"] - 4, b["zc"] + 4), (0.5 * B["od"], ro + 12, T0, T1, b["zc"] - 5, b["zc"] + 5))
    bz = sorted(brg, key=lambda e: e["z0"])
    for b0, b1 in zip(bz[:-1], bz[1:]):
        if not (b0["z1"] <= hubel["z0"] <= b1["z0"]):
            P.add_dielectric(g10, ann_c(SS.SHAFT_R, SS.SLEEVE_R, b0["z1"], b1["z0"]), (SS.SHAFT_R, SS.SLEEVE_R, T0, T1, b0["z1"], b1["z0"]))
    zc0, zc1 = min(b["z0"] for b in brg if b["where"] != "end"), max(b["z1"] for b in brg if b["where"] != "end")
    P.add_dielectric(g10, ann_c(ro + 12, ro + 16, zc0, zc1), (ro + 12, ro + 16, T0, T1, zc0, zc1))
    ves, wall = hub["vessel"]["value"], hub["vessel_wall"]["value"]["t_mm"]
    Ro = 0.5 * ves["od_mm"]
    gel = hub["interface_filler"]["value"]
    Rg = Ro + gel["t_mm"]
    rs, az = (lambda R, Z: np.hypot(R, Z - zc)), (lambda Z: np.abs(Z - zc))
    bore = lambda R, Z: (R < coil["r_mm"][1]) & (az(Z) > core["absz_mm"][0])
    P.add_dielectric(ret["eps_r"], lambda R, T, Z: (R < ret["r_max_mm"]) & (az(Z) < ret["absz_max_mm"]) & (rs(R, Z) > Rg) & ~bore(R, Z),
                     (0, ret["r_max_mm"], T0, T1, zc - 73, zc + 73))
    P.add_dielectric(gel["eps_r"], lambda R, T, Z: (rs(R, Z) > Ro) & (rs(R, Z) < Rg), (0, Rg, T0, T1, zc - Rg, zc + Rg))
    P.add_dielectric(ves["eps_r"], lambda R, T, Z: (rs(R, Z) > Ro - wall) & (rs(R, Z) < Ro), (0, Ro, T0, T1, zc - Ro, zc + Ro))
    P.add_dielectric(g10, lambda R, T, Z: (R > 0.5 * former["id_mm"]) & (R < 0.5 * former["od_mm"]) & (az(Z) > core["absz_mm"][0])
                     & (az(Z) < core["absz_mm"][1]), (0, 9, T0, T1, zc - 73, zc + 73))
    P.add_dielectric(cpl["eps_r"], lambda R, T, Z: (R > ret["r_max_mm"]) & (R < ret["r_max_mm"] + cpl["wall_mm"]) & (az(Z) < ret["absz_max_mm"]),
                     (ret["r_max_mm"], 34, T0, T1, zc - 73, zc + 73))
    for e in vanes:
        v = Vane(e["body"], e["z0"], e["z1"], r_in=ri, r_out=ro, r_ring_in=SS.SLEEVE_R, r_ring_out=ro + 12.0, sectors=False)
        nm = {("A", "rotor"): "N1", ("B", "rotor"): "N4"}.get((e["side"], e["body"]), "STA")
        P.add_conductor(AID[nm], nm, v.inside, v.bbox(T0, T1))
    for e in plates:
        v = Vane("plate", e["z0"], e["z1"], r_in=ri, r_out=ro)
        P.add_conductor(AID["N" + e["node"]], "N" + e["node"], v.inside, v.bbox(T0, T1))
    for f_ in fls:
        P.add_conductor(AID["REF"], "REF", ann(0, SS.FLANGE_R, f_["z0"], f_["z1"]), (0, SS.FLANGE_R, T0, T1, f_["z0"], f_["z1"]))
    fa, fb = [f_ for f_ in fls if f_["side"] == "A"][0], [f_ for f_ in fls if f_["side"] == "B"][0]
    P.add_conductor(AID["REF"], "REF", lambda R, T, Z: (R <= SS.SHAFT_R + TOL) & ((Z <= fa["z0"] + TOL) | (Z >= fb["z1"] - TOL)),
                    (0, SS.SHAFT_R, T0, T1, z_lo - 1, z_hi + 1))
    for b in brg:
        zb0, zb1 = b["zc"] - 0.5 * B["width"], b["zc"] + 0.5 * B["width"]
        P.add_conductor(AID["REF"], "REF", ann(SS.SHAFT_R, 0.5 * B["od"], zb0, zb1), (SS.SHAFT_R, 0.5 * B["od"], T0, T1, zb0, zb1))
    for sg in (-1, 1):
        for (r0_, r1_), zz in (((0.0, 0.5 * core["d_mm"]), core["absz_mm"]), (tuple(coil["r_mm"]), coil["absz_mm"])):
            za, zb = sorted((zc + sg * zz[0], zc + sg * zz[1]))
            P.add_conductor(AID["REF"], "REF", ann(r0_, r1_, za, zb), (r0_, r1_, T0, T1, za, zb))
    rg = hub["rings"]["value"]
    tp, te = math.radians(rg["polar_edge_deg"]), math.radians(rg["equatorial_edge_deg"])
    for sg, nm in ((-1, "RA"), (1, "RB")):
        def ring(R, T, Z, sg=sg):
            rr, ang = rs(R, Z), np.arctan2(R, sg * (Z - zc))
            out = (rr >= Ro - TOL) & (rr <= Ro + max(rg["foil_t_mm"], h_hub) + TOL) & (ang >= tp - 1e-9) & (ang <= te + 1e-9)
            for th_, d_ in ((tp, rg["bead_d_mm"]["polar"]), (te, rg["bead_d_mm"]["equatorial"])):
                Rc = Ro + 0.5 * d_
                out = out | ((R - Rc * math.sin(th_)) ** 2 + (Z - (zc + sg * Rc * math.cos(th_))) ** 2 <= 0.25 * d_ * d_ + TOL)
            return out
        P.add_conductor(AID[nm], nm, ring, (0, Rg + 2, T0, T1, zc - Rg - 2, zc + Rg + 2))
    P.cid[-1, :, :] = AID["W"]; P.names[AID["W"]] = "W"
    log(f"    axisymmetric whole machine: r {len(r)} x z {len(z)} = {len(r) * len(z) / 1e6:.2f} M nodes x 2")
    return P


# ================================================================================================ the solves
def _solve(job):
    """one solve: build, assemble, drive the listed conductors; returns the columns of the Maxwell matrix (pF, as the
    model is: the 60 deg wedge, the 30 deg cell, the 1 deg axisymmetric slice)."""
    kind, kw = job["kind"], job["kw"]
    t0 = time.time()
    lines = []
    log = lambda s: (lines.append(s), print(f"[{job['key']}] {s}", flush=True))
    if kind == "side":
        P = build_side(log=log, **kw)
        names = SIDE
    elif kind == "cell":
        P = build_cell(log=log, **kw)
        names = SIDE
    else:
        P = build_axi(log=log, **kw)
        names = AXI
    P.assemble(log=log)
    present = [c for c in range(P.ncond) if (P.cid == c).any()]
    drive = [c for c in present if names[c] in job["drive"]]
    C, its = P.maxwell(drive, log=log)
    n = P.ncond
    return dict(key=job["key"], kind=kind, kw=kw, names=names[:n], present=[names[c] for c in present],
                driven=[names[c] for c in drive], C=[[None if np.isnan(x) else float(x) for x in row] for row in C],
                shape=list(P.shape), nodes=int(P.cid.size), free=int(P.nf), iterations=its,
                adjacent_pF=float(P.direct.sum() * 1e12), run_s=time.time() - t0)


def jobs(levels):
    """every solve: the side model at each level and angle; the odd mode and the variants at level 1; the periodic
    cell without and with rims at three spacings, the rims' clearance; the axisymmetric whole machine."""
    full = ["N1v", "N1c", "N2", "SA", "BRa", "BRb", "UT", "W"]
    out = []
    for lev in levels:
        for un in (False, True):
            out.append(dict(kind="side", kw=dict(level=lev, unaligned=un), drive=full if lev < 2 else full[:6]))
    lv = min(1, max(levels))
    for un in (False, True):
        out.append(dict(kind="side", kw=dict(level=lv, unaligned=un, mid="zero"), drive=["N1v", "N1c", "N2"]))
        out.append(dict(kind="side", kw=dict(level=lv, unaligned=un, spacers=True), drive=["N1v", "N1c", "N2", "BRa", "BRb"]))
    for rims in (False, True):
        for h in CELL_H:
            for un in (False, True):
                out.append(dict(kind="cell", kw=dict(h=h, unaligned=un, rims=rims), drive=["N1v", "SA"]))
    for c in (3.0, 6.0, 12.0):
        for un in (False, True):
            out.append(dict(kind="cell", kw=dict(h=0.5, unaligned=un, rims=True, clear=c), drive=["N1v", "SA"]))
    out.append(dict(kind="axi", kw=dict(h=0.5, h_hub=0.25), drive=["N1", "N2", "N3", "N4", "RA", "RB"]))
    for j in out:
        j["key"] = j["kind"] + ":" + ",".join(f"{k}={v}" for k, v in sorted(j["kw"].items()))
    return out


def signature():
    """the inputs the solves depend on (a change invalidates the cache)."""
    I = inputs()
    blob = json.dumps(dict(rec={k: I["rec"][k] for k in ("gap_mm", "t_vaneMm", "ws_deg", "wr_deg", "n_plates")},
                           el=I["lay"]["elements"], hub={k: I["hub"][k] for k in ("vessel", "vessel_wall", "rings", "AH",
                                                                                   "retainer", "interface_filler", "shaft_coupler")},
                           levels=LEVELS, cell=CELL_H, box=R_BOX, zlo=Z_LO, wedge=WEDGE,
                           code=hashlib.sha1(open(__file__, "rb").read().split(b"# ==== the analysis")[0]).hexdigest()),
                      sort_keys=True, default=float)
    return hashlib.sha1(blob.encode()).hexdigest()[:16]


# ==== the analysis ===============================================================================================
def matrix(s):
    return np.array([[np.nan if x is None else x for x in row] for row in s["C"]]), list(s["names"])


def side_caps(s, floating=("BRa", "BRb"), ref=REF_PARTS, scale=6.0):
    """from a side solve: floating parts eliminated (zero charge), then the deck's capacitances per side (pF):
    the varicap's own (rotor vanes - stator vanes), Ca's own (node-1 plates - node-2 plates), node 1 / node 2 to REF,
    between them, and the strays itemised. Every entry used is a driven column (or its symmetric row) [OC]."""
    C, names = matrix(s)
    n = len(names)
    present = set(s["present"])
    drv = set(s["driven"])
    # symmetric completion of the rows of driven columns
    for a in range(n):
        for b in range(n):
            if np.isnan(C[a, b]) and not np.isnan(C[b, a]):
                C[a, b] = C[b, a]
    fl = [names.index(f) for f in floating if f in present]
    for f in fl:
        assert names[f] in drv, f"floating {names[f]} must be driven"
    keep = [i for i in range(n) if i not in fl and names[i] in present]
    if fl:
        Cff = C[np.ix_(fl, fl)]
        Ckf = C[np.ix_(keep, fl)]
        Cr = C[np.ix_(keep, keep)] - Ckf @ np.linalg.solve(Cff, Ckf.T)
    else:
        Cr = C[np.ix_(keep, keep)]
    nm = [names[i] for i in keep]
    ix = {k: i for i, k in enumerate(nm)}
    m = lambda a, b: -scale * Cr[ix[a], ix[b]] if (a in ix and b in ix and not np.isnan(Cr[ix[a], ix[b]])) else 0.0
    refs = [x for x in ref if x in ix]
    out = dict(varicap=m("N1v", "SA"), ca=m("N1c", "N2"), stray_12=m("N1v", "N2"))
    out["node1_ref"] = sum(m(a, b) for a in ("N1v", "N1c") for b in refs)
    out["node2_ref"] = sum(m("N2", b) for b in refs)
    out["node1_ring"] = sum(m(a, "RA") for a in ("N1v", "N1c"))
    out["node2_ring"] = m("N2", "RA")
    out["stray1"] = out["node1_ref"] - out["varicap"]
    out["stray2"] = out["node2_ref"]
    out["items1"] = {f"{a}-{b}": m(a, b) for a in ("N1v", "N1c") for b in refs + ["RA"] if not (a == "N1v" and b == "SA")}
    out["items2"] = {f"N2-{b}": m("N2", b) for b in refs + ["RA"]}
    out["internal_N1v_N1c"] = m("N1v", "N1c")
    return out


def richardson(xs, hs):
    """the extrapolated value from three levels (the observed order p fitted to them, 0.5 <= p <= 4); with two levels
    or a non-monotone sequence, the finest value. Returns (value, p or None)."""
    xs = [x for x in xs if x is not None]
    if len(xs) < 3:
        return (xs[-1] if xs else None), None
    x0, x1, x2 = xs[-3:]
    h0, h1, h2 = hs[-3:]
    d1, d2 = x1 - x0, x2 - x1
    if d1 == 0 or d2 == 0 or d1 * d2 < 0:
        return x2, None
    f = lambda p: (h0 ** p - h1 ** p) / (h1 ** p - h2 ** p) - d1 / d2
    lo, hi = 0.5, 4.0
    if f(lo) * f(hi) > 0:
        return x2, None
    for _ in range(60):
        mid = 0.5 * (lo + hi)
        lo, hi = (mid, hi) if f(lo) * f(mid) > 0 else (lo, mid)
    p = 0.5 * (lo + hi)
    return x2 + d2 / ((h1 / h2) ** p - 1.0), p


# ================================================================================================ the decks
_DECK = CF.deck


def deck_strays(strays=None, **kw):
    """sim/core_field.py's deck, built by its own function; then, in this copy only, the node strays Cp1-Cp4 set to
    strays['Cp'][node] (F) and the couplings strays['Cx'] {'a b': F} added."""
    txt, vecs, pk = _DECK(**kw)
    if strays:
        lines = txt.split("\n")
        for i, ln in enumerate(lines):
            mt = re.match(r"^Cp([1-4]) ([1-4]) 0 ", ln)
            if mt and mt.group(1) in strays.get("Cp", {}):
                lines[i] = f"Cp{mt.group(1)} {mt.group(2)} 0 {strays['Cp'][mt.group(1)]:.6e}"
        j = [i for i, ln in enumerate(lines) if ln.startswith(".model ND")][0]
        lines[j:j] = [f"Cx{k.replace(' ', '_')} {k} {v:.6e}" for k, v in strays.get("Cx", {}).items() if v > 0]
        txt = "\n".join(lines)
    return txt, vecs, pk


CF.deck = deck_strays          # sim/core_field.py's run looks its deck up by name: in this process and its workers only


def _run(case):
    name, kw = case
    r = CF.run((name, kw))
    keep = ("z", "P_belt_W", "P_limit_W", "P_belt_wave_W", "done", "V", "V_ea_kV", "V_eb_kV", "Z1", "VR_pk_kV", "link")
    return name, {k: r[k] for k in keep if k in r}


def deck_cases(sets, rings_kw):
    """for each stray set: the free run (z), the clamped run (power), the rings' supply (free z, clamped)."""
    out = []
    for nm, s in sets.items():
        base = dict(cmin=s["cmin"], cmax=s["cmax"], ca=s["ca"], strays=dict(Cp=s["Cp"], Cx=s["Cx"]))
        out += [(f"{nm}|free", dict(base, opt="none", clamp=False, n_cyc=12)),
                (f"{nm}|clamped", dict(base, opt="none")),
                (f"{nm}|rings free", dict(base, **{k: v for k, v in rings_kw.items() if k not in ("n_cyc", "steps")},
                                          c_e=s["c_e"], c_gap=s["c_gap"], clamp=False, n_cyc=12, v0=-10.0)),
                (f"{nm}|rings", dict(base, **rings_kw, c_e=s["c_e"], c_gap=s["c_gap"]))]
    return out
