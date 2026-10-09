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
Usage: python3 sim/tube_strays.py [--resume] [--procs 3] [--levels 0 1 2]
       (several hours on 4 cores: the level-2 solves are 6-7 M nodes each; --resume reuses the solves already in the
       results file; --merge FILE reuses another run's; --only KEY runs only those solves; --solves-only stops after
       them)
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


def build_cell(h=0.5, unaligned=False, rims=True, clear=0.0, sleeve_eps=None, log=print):
    """one gap of the infinite periodic stack: mirrors at a stator vane's and the next rotor vane's mid-planes, the
    30 deg mirror wedge. rims=False: the record's 2-D cell in 3-D (Neumann at r 50 / 150, the sectors only, no rims).
    rims=True: the real radial build (shaft, sleeve, the rotor ring, the stator ring, the cage, the REF wall).
    clear > 0 [RH, not the record]: the rotor ring's edge and the rotor sectors' outer rims pulled back by clear, the
    stator sectors' inner rims and the stator ring's edge pushed out by clear (the overlap shrinks to r 50+c..150-c).
    sleeve_eps [RH, not the record]: the sleeve's permittivity in place of G10's."""
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
        P.add_dielectric(sleeve_eps or g10, ann_c(SS.SHAFT_R, SS.SLEEVE_R, -1, zr + 1), (SS.SHAFT_R, SS.SLEEVE_R, T0, T1, -1, zr + 1))
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
    out.append(dict(kind="cell", kw=dict(h=0.5, unaligned=False, rims=True, sleeve_eps=2.1), drive=["N1v", "SA"]))
    out.append(dict(kind="axi", kw=dict(h=0.5, h_hub=0.25), drive=["N1", "N2", "N3", "N4", "RA", "RB"]))
    for j in out:
        j["key"] = j["kind"] + ":" + ",".join(f"{k}={v}" for k, v in sorted(j["kw"].items()))
    return out


def physics_hash():
    """the solver's, the geometry's and the builders' code (from the finite-volume core to the solves)."""
    src = open(__file__, "rb").read()
    a, b = src.index(b"# " + b"=" * 88 + b" the finite-volume core"), src.index(b"# " + b"=" * 96 + b" the solves")
    return hashlib.sha1(src[a:b]).hexdigest()


def signature():
    """the inputs the solves depend on, and the physics code (a change of either invalidates the cache)."""
    I = inputs()
    blob = json.dumps(dict(rec={k: I["rec"][k] for k in ("gap_mm", "t_vaneMm", "ws_deg", "wr_deg", "n_plates")},
                           el=I["lay"]["elements"], hub={k: I["hub"][k] for k in ("vessel", "vessel_wall", "rings", "AH",
                                                                                   "retainer", "interface_filler", "shaft_coupler")},
                           levels=LEVELS, cell=CELL_H, box=R_BOX, zlo=Z_LO, wedge=WEDGE, code=physics_hash()),
                      sort_keys=True, default=float)
    return hashlib.sha1(blob.encode()).hexdigest()[:16]


# ==== the analysis ===============================================================================================
def matrix(s):
    """a solve's Maxwell matrix (pF, as modelled), the entries of undriven columns filled from their symmetric rows
    (C is symmetric [OC]); the entries between two undriven conductors stay NaN."""
    C = np.array([[np.nan if x is None else x for x in row] for row in s["C"]])
    C = np.where(np.isnan(C), C.T, C)
    return C, list(s["names"])


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
    keep = ("z", "P_belt_W", "P_limit_W", "P_belt_wave_W", "done", "V", "V_ea_kV", "V_eb_kV", "Z1", "VR_pk_kV", "link",
            "n_cyc", "Vk_per_cycle_kV", "V1_peak_per_cycle_kV")
    return name, {k: r[k] for k in keep if k in r}


# ================================================================================================ the gates
def gate_analytic(log=print):
    """the solver against closed forms [OC]: a coaxial pair with a G10 layer (exact for the log-law radial edges);
    concentric spheres (curved surfaces across the grid: the sub-cell distances against the plain staircase); a thin
    strip midway between two planes (Cohn's stripline, fringing at sharp edges)."""
    from scipy.special import ellipk
    out = {}
    # coaxial: shaft r 12.5, G10 to 20.5, air to 50, in a 10 deg wedge, 10 mm long
    P = Problem(axis(5.0, 60.0, [12.5, 20.5, 50.0], [(5, 60, 0.7)]), np.radians([0.0, 10.0]), np.array([0.0, 5.0, 10.0]))
    P.add_conductor(0, "in", lambda R, T, Z: R <= 12.5 + 1e-9, (0, 12.5, -1, 1, -1, 11))
    P.add_conductor(1, "out", lambda R, T, Z: R >= 50 - 1e-9, (50, 60, -1, 1, -1, 11))
    P.add_dielectric(4.7, ann_c(12.5, 20.5, -1, 11), (12.5, 20.5, -1, 1, -1, 11))
    P.assemble(log=lambda s: None)
    c = -P.maxwell([0], log=lambda s: None)[0][1, 0]
    ex = 2 * math.pi * EPS0_MM / (math.log(20.5 / 12.5) / 4.7 + math.log(50 / 20.5)) * 10.0 * (10 / 360) * 1e12
    out["coax"] = dict(C_pF=c, exact_pF=ex, rel_err=c / ex - 1)
    rows = []
    for h in (1.0, 0.5, 0.25):
        a, b = 20.0, 40.0
        res = {}
        for sw in (True, False):
            P = Problem(axis(1e-3, 45.0, [], [(0, 45, h)]), np.radians([0.0, 5.0]), axis(-45.0, 45.0, [], [(-45, 45, h)]))
            P.add_conductor(0, "in", lambda R, T, Z: R * R + Z * Z <= a * a, (0, a, -1, 1, -a, a))
            P.add_conductor(1, "out", lambda R, T, Z: R * R + Z * Z >= b * b, (0, 50, -1, 1, -50, 50))
            if not sw:
                P._fractions = lambda ax, ca, cb, **k: (np.nonzero((ca < 0) ^ (cb < 0)), np.ones(int(((ca < 0) ^ (cb < 0)).sum())))
            P.assemble(log=lambda s: None)
            res[sw] = -P.maxwell([0], log=lambda s: None)[0][1, 0]
        ex = 4 * math.pi * EPS0_MM * a * b / (b - a) * (5 / 360) * 1e12
        rows.append(dict(h_mm=h, sub_cell=res[True] / ex - 1, staircase=res[False] / ex - 1))
    out["spheres"] = dict(a_mm=20.0, b_mm=40.0, rows=rows)
    rows = []
    R0, W, bs = 3000.0, 20.0, 12.0
    for h in (0.5, 0.25, 0.125):
        P = Problem(axis(R0 - 60, R0 + 60, [R0 - W / 2, R0 + W / 2], [(R0 - 60, R0 + 60, h)]), np.radians([0.0, 1.0]),
                    axis(0.0, bs / 2, [], [(0, bs, h)]))
        P.add_conductor(0, "strip", lambda R, T, Z: (np.abs(R - R0) <= W / 2 + 1e-9) & (Z <= 1e-9), (R0 - W, R0 + W, -1, 1, -1, 1))
        P.add_conductor(1, "plane", lambda R, T, Z: Z >= bs / 2 - 1e-9, (0, 1e5, -1, 1, bs / 2 - 1, bs))
        P.assemble(log=lambda s: None)
        rows.append(dict(h_mm=h, C_pF=-P.maxwell([0], log=lambda s: None)[0][1, 0]))
    k = 1 / math.cosh(math.pi * W / (2 * bs))
    ex = 0.5 * 4 * EPS0_MM * ellipk(1 - k * k) / ellipk(k * k) * R0 * math.radians(1.0) * 1e12
    for q in rows:
        q["rel_err"] = q["C_pF"] / ex - 1
    rich = 2 * rows[-1]["C_pF"] - rows[-2]["C_pF"]
    out["stripline"] = dict(W_mm=W, b_mm=bs, exact_pF=ex, rows=rows, richardson_pF=rich, richardson_err=rich / ex - 1,
                            note="Cohn: C' = 4 eps0 K(k')/K(k), k = sech(pi W / 2b), zero-thickness strip; first order at the "
                                 "sharp edges, so Richardson with p = 1")
    log(f"  coax {out['coax']['rel_err']:+.1e}; spheres sub-cell " + ", ".join(f"{q['sub_cell']:+.3%}" for q in out["spheres"]["rows"])
        + " (staircase " + ", ".join(f"{q['staircase']:+.2%}" for q in out["spheres"]["rows"]) + "); stripline "
        + ", ".join(f"{q['rel_err']:+.2%}" for q in rows) + f", extrapolated {out['stripline']['richardson_err']:+.3%}")
    return out


def gate_vane_record_like(log=print):
    """the record's 2-D cell as it discretises the vane (sim/stack_sizing._cell / sim/vane_cell.grid at h 0.25: 11 node
    rows at 0.24 mm, so 2.4 mm node to node, a full round of 1.2 mm, the gap 6.0 mm, the z period 16.8 mm), solved
    here in 3-D with no rims: it must return the record's per-gap C_max / C_min (sim/air_stack_sizing_results.json)."""
    I = inputs()
    rec = I["rec"]
    out = []
    for h in (0.5, 0.25):
        row = dict(h_mm=h)
        for un in (False, True):
            t, g, half = 2.4, rec["gap_mm"], 0.5 * rec["wr_deg"]
            zr = t + g
            z = axis(0.0, zr, [0.5 * t, zr - 0.5 * t], [(0, zr, h)])
            edges = [half] + ([30.0 - half] if un else [])
            th = axis(0, 30.0, [0, 30] + edges, [(e - 2.5, e + 2.5, 0.4 * h) for e in edges] + [(0, 30, 1.2 * h)], h_far=1.2 * h, grow=1.2)
            P = Problem(axis(50.0, 150.0, [], [(50, 150, 5.0)]), np.radians(th), z, eps_bg=I["eps_air"])
            st = Vane("stator", -0.5 * t, 0.5 * t, 30.0 if un else 0.0, half, 0.0, 1000.0)
            rt = Vane("rotor", zr - 0.5 * t, zr + 0.5 * t, 0.0, half, 0.0, 1000.0, 0.0)
            P.add_conductor(0, "rotor", rt.inside, (0, 1e4, -1, 2, zr - t, zr + t))
            P.add_conductor(1, "stator", st.inside, (0, 1e4, -1, 2, -t, t))
            P.assemble(log=lambda s: None)
            row["unaligned" if un else "aligned"] = -12 * P.maxwell([0], log=lambda s: None)[0][1, 0]
        row["aligned_vs_record"] = row["aligned"] / rec["per_gap_max_pF"] - 1
        row["unaligned_vs_record"] = row["unaligned"] / rec["per_gap_min_pF"] - 1
        out.append(row)
    log("  the record's cell in 3-D: " + "; ".join(f"h {q['h_mm']}: {q['aligned']:.3f} ({q['aligned_vs_record']:+.2%}) / "
                                                 f"{q['unaligned']:.3f} ({q['unaligned_vs_record']:+.2%}) pF per gap" for q in out))
    return out


# ================================================================================================ the orchestration
def _hs(level):
    return LEVELS[level]["hz"]


def stray_sets(res):
    """the stray sets for the deck, per side (F): the record; the record's caps with the solved strays; the pump as
    built; its variants."""
    rec = inputs()["rec"]
    pF = 1e-12
    R = res["record_deck"]
    best = res["side_best"]
    ac, rings = res["across"], res["rings_axi"]
    m = lambda k: 0.5 * (best["aligned"][k] + best["unaligned"][k])
    cx_pump = {"1 2": m("stray_12") * pF, "3 4": m("stray_12") * pF, "1 4": ac["C14_pF"] * pF, "2 3": ac["C23_pF"] * pF,
               "1 3": ac["C13_pF"] * pF, "2 4": ac["C13_pF"] * pF}
    cx_rings = {"1 ea": rings["C_node1_ringA_pF"] * pF, "4 eb": rings["C_node1_ringA_pF"] * pF,
                "1 eb": rings["C_node1_ringB_pF"] * pF, "4 ea": rings["C_node1_ringB_pF"] * pF}
    base = dict(cmin=rec["C_min_pF"] * pF, cmax=rec["C_max_pF"] * pF, ca=rec["Ca_pF"] * pF)
    sets = {"record": dict(base, Cp={n: R["CPAR_pF"] * pF for n in "1234"}, Cx={}, Cx_rings={}, c_e=R["c_e_pF"] * pF,
                           c_gap=R["c_gap_pF"] * pF)}
    cp = {"1": m("stray1") * pF, "4": m("stray1") * pF, "2": m("stray2") * pF, "3": m("stray2") * pF}
    sets["strays"] = dict(base, Cp=cp, Cx=dict(cx_pump), Cx_rings={}, c_e=R["c_e_pF"] * pF, c_gap=R["c_gap_pF"] * pF)
    sets["strays + rings"] = dict(sets["strays"], Cx_rings=cx_rings, c_e=rings["C_ring_ref_pF"] * pF, c_gap=rings["C_ring_ring_pF"] * pF)

    def built(b, label):
        tot_a, tot_u = b["aligned"]["node1_ref"], b["unaligned"]["node1_ref"]
        cp1 = 0.5 * (b["aligned"]["stray1"] + b["unaligned"]["stray1"])
        ca = 0.5 * (b["aligned"]["ca"] + b["unaligned"]["ca"] + b["aligned"]["stray_12"] + b["unaligned"]["stray_12"])
        cp2 = 0.5 * (b["aligned"]["stray2"] + b["unaligned"]["stray2"])
        cxp = {k: v for k, v in cx_pump.items() if k not in ("1 2", "3 4")}
        return dict(cmin=(tot_u - cp1) * pF, cmax=(tot_a - cp1) * pF, ca=ca * pF,
                    Cp={"1": cp1 * pF, "4": cp1 * pF, "2": cp2 * pF, "3": cp2 * pF}, Cx=cxp, Cx_rings=cx_rings,
                    c_e=rings["C_ring_ref_pF"] * pF, c_gap=rings["C_ring_ring_pF"] * pF, label=label)
    sets["varicap as solved, 20 pF"] = dict(sets["record"], cmin=best["unaligned"]["varicap"] * pF, cmax=best["aligned"]["varicap"] * pF)
    sets["as built"] = built(best, "the best estimate")
    for nm, b in res.get("side_variants", {}).items():
        sets[f"as built, {nm}"] = built(b, nm)
    lv = res.get("side_levels", {})
    for lev, b in lv.items():
        if lev != max(lv):                               # the coarser levels: the mesh's effect on z
            sets[f"as built, level {lev}"] = built(b, f"level {lev}")
    return sets


def _cycles(z, extra, floor):
    """the cycles to grow from the deck's 1 kV start to the clamp at this z (with a margin), plus `extra` to settle and
    measure; never fewer than the record's own `floor`."""
    if not z or z <= 1.0:
        return None
    return max(floor, int(math.ceil(extra + 1.3 * math.log(CF.V_OP / 1e3) / math.log(z))))


def run_decks(sets, rings_kw, procs, log=print):
    """per set: the free runs (z bare; z at start-up with the rings' chains), then the clamped run and the rings'
    supply, each long enough to reach the clamp at its own z (the record's 24 / 280 cycles where they suffice), the
    rings' run doubled until settled (the last ten cycles within 0.3 %, as sim/hub_rings_build.py checks)."""
    v_op = CF.V_OP
    out = {}

    def go(cases):
        with Pool(procs) as pool:
            for name, r in pool.imap_unordered(_run, cases):
                out[name] = r
                log(f"  deck {name}: " + (f"z {r['z']:.4f}" if "z" in r else f"belt {r.get('P_belt_W', float('nan')):.3f} W"
                                           + (f", A {r['V_ea_kV']['mean']:.2f} / B {r['V_eb_kV']['mean']:.2f} kV" if "V_ea_kV" in r else "")))
    base = {}
    for nm, s in sets.items():
        base[nm] = (dict(cmin=s["cmin"], cmax=s["cmax"], ca=s["ca"], strays=dict(Cp=s["Cp"], Cx=s["Cx"])),
                    dict(cmin=s["cmin"], cmax=s["cmax"], ca=s["ca"], strays=dict(Cp=s["Cp"], Cx=dict(s["Cx"], **s["Cx_rings"])),
                         c_e=s["c_e"], c_gap=s["c_gap"]))
    free_kw = {k: v for k, v in rings_kw.items() if k not in ("n_cyc", "steps")}
    cases = []
    for nm in sets:
        cases.append((f"{nm}|free", dict(base[nm][0], opt="none", clamp=False, n_cyc=12)))
        if not nm.startswith("as built, level"):
            cases.append((f"{nm}|rings free", dict(base[nm][1], **free_kw, clamp=False, n_cyc=12, v0=-10.0)))
    go(cases)
    cases = []
    for nm in sets:
        if nm.startswith("as built, level"):
            continue
        rec_ = nm == "record"                            # the gate: the record's own cycles (24 and 280)
        nc = 24 if rec_ else _cycles(out[f"{nm}|free"].get("z"), 12, 24)
        if nc:
            cases.append((f"{nm}|clamped", dict(base[nm][0], opt="none", n_cyc=nc)))
        nr = rings_kw["n_cyc"] if rec_ else _cycles(out[f"{nm}|rings free"].get("z"), rings_kw["n_cyc"], rings_kw["n_cyc"])
        if nr:
            cases.append((f"{nm}|rings", dict(base[nm][1], **dict(rings_kw, n_cyc=nr))))
    go(cases)
    for _ in range(2):                                   # the rings' run again, twice as long, until it settles
        redo = []
        for nm in sets:
            r = out.get(f"{nm}|rings")
            if r and not _settled(r):
                redo.append((f"{nm}|rings", dict(base[nm][1], **dict(rings_kw, n_cyc=2 * r["n_cyc"]))))
        if not redo:
            break
        go(redo)
    table = {}
    k_null = _rings_record()["k_kV_cm_per_kV"]
    for nm in sets:
        t = dict(z=out.get(f"{nm}|free", {}).get("z"))
        c = out.get(f"{nm}|clamped")
        if c:
            pk = c.get("V1_peak_per_cycle_kV") or [None]
            t.update(P_clamped_W=c.get("P_belt_W"), clamped_cycles=c.get("n_cyc"), V1_kV=(c.get("V") or {}).get("1"),
                     V2_kV=(c.get("V") or {}).get("2"), VR_pk_kV=c.get("VR_pk_kV"), link_mA_rms=(c.get("link") or {}).get("I_rms_mA"),
                     reached_clamp=bool(pk[-1] and pk[-1] > 0.97 * v_op / 1e3))
        rf, rr = out.get(f"{nm}|rings free"), out.get(f"{nm}|rings")
        if rf:
            t["z_rings_start"] = rf.get("z")
        if rr:
            va, vb = (rr.get("V_ea_kV") or {}).get("mean"), (rr.get("V_eb_kV") or {}).get("mean")
            t.update(rings_P_belt_W=rr.get("P_belt_W"), V_A_kV=va, V_B_kV=vb, rings_cycles=rr.get("n_cyc"),
                     rings_settled=_settled(rr), E_null_kV_cm=(k_null * (vb - va) if va is not None else None),
                     t_to_95pc_s=_t95(rr))
        table[nm] = t
    return table


def _settled(r):
    vk = r.get("Vk_per_cycle_kV") or []
    return bool(len(vk) > 10 and abs(vk[-1] - vk[-10]) < 0.003 * abs(vk[-1]))


def _t95(r):
    """the rings' start-up: the first cycle at 95 % of the final gap voltage (sim/core_field.py's start rule)."""
    vk = np.array(r.get("Vk_per_cycle_kV") or [])
    if len(vk) < 10:
        return None
    fin = vk[-3:].mean()
    hit = np.nonzero(vk <= 0.95 * fin)[0]
    return float((hit[0] + 1) / CF.F) if len(hit) else None


def analyse(res, levels, log=print):
    """the solves into the record's terms: the periodic cell, the side model per level (and extrapolated), the
    variants, the couplings across the hub, the rings."""
    S = res["solves"]
    rec = inputs()["rec"]
    key = lambda kind, **kw: kind + ":" + ",".join(f"{k}={v}" for k, v in sorted(kw.items()))
    # ---- the periodic cell
    cell = dict(record=dict(per_gap_max_pF=rec["per_gap_max_pF"], per_gap_min_pF=rec["per_gap_min_pF"],
                            C_edge_pF=rec["C_min_pF"] - rec["n_gap"] * rec["per_gap_min_pF"], n_gap=rec["n_gap"]))
    for rims in (False, True):
        rows = []
        for h in CELL_H:
            row = dict(h_mm=h)
            for un in (False, True):
                s = S.get(key("cell", h=h, unaligned=un, rims=rims))
                if not s:
                    continue
                C, nm = matrix(s)
                tag = "unaligned" if un else "aligned"
                row[tag] = -12 * C[nm.index("SA"), nm.index("N1v")]
                if rims:
                    row[f"{tag}_rotor_vane_shaft_pF"] = -24 * C[nm.index("SHAFT"), nm.index("N1v")]
                    row[f"{tag}_rotor_vane_wall_pF"] = -24 * C[nm.index("W"), nm.index("N1v")]
            rows.append(row)
        cell["with_rims" if rims else "no_rims"] = rows
    clr = []
    for c in (0.0, 3.0, 6.0, 12.0):
        row = dict(clear_mm=c)
        for un in (False, True):
            s = S.get(key("cell", h=0.5, unaligned=un, rims=True)) if c == 0 else \
                S.get(key("cell", h=0.5, unaligned=un, rims=True, clear=c))
            if s:
                C, nm = matrix(s)
                row["unaligned" if un else "aligned"] = -12 * C[nm.index("SA"), nm.index("N1v")]
        if "aligned" in row and "unaligned" in row:
            row["kappa_gap"] = row["aligned"] / row["unaligned"]
        clr.append(row)
    cell["clearance"] = clr
    s = S.get(key("cell", h=0.5, unaligned=False, rims=True, sleeve_eps=2.1))
    if s:
        C, nm = matrix(s)
        cell["sleeve_ptfe"] = dict(eps=2.1, rotor_vane_shaft_pF=-24 * C[nm.index("SHAFT"), nm.index("N1v")],
                                   per_gap_aligned_pF=-12 * C[nm.index("SA"), nm.index("N1v")])
    res["cell"] = cell
    # ---- the side model per level, and extrapolated
    lv = {}
    for lev in levels:
        caps = {}
        for un in (False, True):
            s = S.get(key("side", level=lev, unaligned=un))
            if s:
                caps["unaligned" if un else "aligned"] = side_caps(s)
        if len(caps) == 2:
            lv[lev] = caps
    res["side_levels"] = lv
    hs = [_hs(l) for l in sorted(lv)]
    best, ext = {"aligned": {}, "unaligned": {}}, {"aligned": {}, "unaligned": {}}
    for ang in ("aligned", "unaligned"):
        for k in ("varicap", "ca", "stray_12", "node1_ref", "node2_ref", "stray1", "stray2", "internal_N1v_N1c",
                  "node1_ring", "node2_ring"):
            xs = [lv[l][ang][k] for l in sorted(lv)]
            v, p = richardson(xs, hs)
            best[ang][k] = xs[-1]                        # the deck takes the finest level; the extrapolation is the gate
            ext[ang][k] = dict(levels=xs, h_mm=hs, value=v, order=p,
                               last_step=(xs[-1] / xs[-2] - 1) if len(xs) > 1 and xs[-2] else None)
        for grp in ("items1", "items2"):
            best[ang][grp] = dict(lv[max(lv)][ang][grp])
    res["side_best"], res["side_extrapolation"] = best, ext
    # ---- variants, at level 1 (or the finest below it)
    lvv = max([l for l in lv if l <= 1] or [max(lv)])
    var = {}
    s_a, s_u = S.get(key("side", level=lvv, unaligned=False)), S.get(key("side", level=lvv, unaligned=True))
    if s_a and s_u and "UT" in s_a["driven"] and "W" in s_a["driven"]:
        for nm, fl, extra in (("the room floating", ("BRa", "BRb", "W"), ()), ("the utrons floating", ("BRa", "BRb", "UT"), ()),
                              ("the bridges at REF", (), ("BRa", "BRb"))):
            ref = tuple(x for x in REF_PARTS if x not in fl) + extra
            var[nm] = {"aligned": side_caps(s_a, floating=fl, ref=ref), "unaligned": side_caps(s_u, floating=fl, ref=ref)}
    sp_a, sp_u = (S.get(key("side", level=lvv, unaligned=u, spacers=True)) for u in (False, True))
    if sp_a and sp_u:
        var["node-1 spacers on the sleeve [RH]"] = {"aligned": side_caps(sp_a), "unaligned": side_caps(sp_u)}
    res["side_variants"], res["side_variants_level"] = var, lvv
    # ---- across the hub: the odd mode against the even, unreduced (level lvv) [OC]
    ac = dict(level=lvv)
    grp = lambda C, nm, A, B: sum(C[nm.index(a), nm.index(b)] for a in A for b in B)
    n1, n2 = ("N1v", "N1c"), ("N2",)
    for un in (False, True):
        se, so = S.get(key("side", level=lvv, unaligned=un)), S.get(key("side", level=lvv, unaligned=un, mid="zero"))
        if se and so:
            (Ce, ne), (Co, no) = matrix(se), matrix(so)
            ac["unaligned" if un else "aligned"] = dict(
                C14_pF=3.0 * (grp(Co, no, n1, n1) - grp(Ce, ne, n1, n1)), C23_pF=3.0 * (grp(Co, no, n2, n2) - grp(Ce, ne, n2, n2)),
                C13_pF=3.0 * (grp(Co, no, n2, n1) - grp(Ce, ne, n2, n1)))
    for k in ("C14_pF", "C23_pF", "C13_pF"):
        v = [ac[t][k] for t in ("aligned", "unaligned") if t in ac]
        ac[k] = float(np.mean(v)) if v else 0.0
    res["across"] = ac
    # ---- the axisymmetric whole machine: the rings, and the bound
    sa = S.get(key("axi", h=0.5, h_hub=0.25))
    if sa:
        C, nm = matrix(sa)
        g = lambda a, b: -360.0 * C[nm.index(a), nm.index(b)]
        refs = ("STA", "REF", "W")
        rr = _rings_record()
        res["rings_axi"] = dict(C_ring_ref_pF=sum(g("RA", b) for b in refs), C_ring_ring_pF=g("RA", "RB"),
                                C_node1_ringA_pF=g("N1", "RA"), C_node1_ringB_pF=g("N1", "RB"), C_node2_ringA_pF=g("N2", "RA"),
                                C14_axi_pF=g("N1", "N4"), C13_axi_pF=g("N1", "N3"), C23_axi_pF=g("N2", "N3"),
                                node1_ref_axi_pF=sum(g("N1", b) for b in refs), node2_ref_axi_pF=sum(g("N2", b) for b in refs),
                                varicap_axi_pF=g("N1", "STA"), ca_axi_pF=g("N1", "N2"),
                                record_hub_solve=dict(C_ring_ref_pF=rr["C_ring_ref_pF"], C_ring_ring_pF=rr["C_ring_ring_pF"],
                                                      source=SRC["rings"] + " record"))
    return res


def _rings_record():
    return json.load(open(os.path.join(ROOT, SRC["rings"])))["record"]


def record_deck():
    """the record's deck inputs: the node strays (sim/core_field.py CPAR), the rings' strays as record_supply ran them
    (the deck's defaults c_e / c_gap: sim/hub_rings_build.py passes neither), the record_supply case and its results."""
    import inspect
    dflt = {k: v.default for k, v in inspect.signature(_DECK).parameters.items()}
    rb = json.load(open(os.path.join(ROOT, SRC["rings"])))
    rs = rb["record_supply"]
    core = {r["name"]: r for r in json.load(open(os.path.join(ROOT, SRC["core"])))["rows"]}
    return dict(CPAR_pF=CF.CPAR * 1e12, c_e_pF=dflt["c_e"] * 1e12, c_gap_pF=dflt["c_gap"] * 1e12,
                rings_kw={k: rs[k] for k in ("opt", "n_cw", "n_cw_a", "c_core", "c_cw", "r_leak", "a_ref", "n_cyc", "steps")},
                z_free=core["free none"]["z"], P_clamped_W=core["none"]["P_belt_W"], z_rings=rb["record_supply_free"]["z"],
                rings_P_belt_W=rs["P_belt_W"], V_A_kV=rs["V_ea_kV"]["mean"], V_B_kV=rs["V_eb_kV"]["mean"],
                E_null_kV_cm=rs.get("E_null_mean_kV_cm"))


def sensitivity(procs, log=print):
    """the deck's own price of a pF (the record's caps): z against Cp on nodes 1 / 4 and on nodes 2 / 3."""
    pF = 1e-12
    cases = [(f"sens|{c1}|{c2}", dict(opt="none", clamp=False, n_cyc=12,
                                      strays=dict(Cp={"1": c1 * pF, "4": c1 * pF, "2": c2 * pF, "3": c2 * pF}, Cx={})))
             for c1, c2 in ((20, 20), (30, 20), (20, 30))]
    with Pool(procs) as pool:
        r = dict(pool.map(_run, cases))
    z = lambda a, b: r[f"sens|{a}|{b}"]["z"]
    return dict(dz_per_pF_nodes14=(z(30, 20) - z(20, 20)) / 10.0, dz_per_pF_nodes23=(z(20, 30) - z(20, 20)) / 10.0,
                z_at=dict(cp20_20=z(20, 20), cp30_20=z(30, 20), cp20_30=z(20, 30)),
                note="each pair of nodes raised together (1 and 4, or 2 and 3), the record's C1 / C2 / Ca / Cb")


# ================================================================================================ the figure
INK, INK2, MUTED, GRID, BASE, SURF = "#0b0b0b", "#52514e", "#898781", "#e1e0d9", "#c3c2b7", "#fcfcfb"
SERIES = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4", "#008300", "#4a3aa7", "#e34948"]   # fixed order


def figure(res, path=FIGURE, log=print):
    """the model's section, the strays per node against the record's 20 pF, the varicap, and the pump."""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.colors import ListedColormap
    plt.rcParams.update({"font.size": 8.5, "axes.edgecolor": BASE, "axes.labelcolor": INK2, "xtick.color": MUTED,
                         "ytick.color": MUTED, "axes.titlesize": 9.5, "axes.titleweight": "bold", "axes.titlecolor": INK,
                         "font.family": "sans-serif"})
    fig = plt.figure(figsize=(16.5, 10.2), facecolor=SURF)
    gs = fig.add_gridspec(2, 3, width_ratios=[1.05, 1.0, 1.0], wspace=0.28, hspace=0.32, left=0.045, right=0.985, top=0.93, bottom=0.07)
    # (a) the section
    ax = fig.add_subplot(gs[:, 0])
    P = build_side(level=0, unaligned=False, log=lambda s: None)
    j = 0
    col = {"N1v": SERIES[0], "N1c": SERIES[0], "N2": SERIES[1], "SA": "#7d7b74", "SHAFT": "#4d4c48", "BRG": "#4d4c48",
           "UT": "#a8a69e", "BRa": "#d2d0c8", "BRb": "#d2d0c8", "RA": SERIES[2], "W": SURF, "MID": SURF}
    cmap = ListedColormap([col[n] for n in SIDE])
    Cc = P.cid[:, j, :].astype(float)
    Cc[Cc < 0] = np.nan
    E = P.eps[:, j, :]
    ax.pcolormesh(P.r, P.z, np.where(E.T > 1.5, E.T, np.nan), cmap=ListedColormap(["#efe8d0"]), shading="flat", rasterized=True)
    ax.pcolormesh(P.r, P.z, Cc.T, cmap=cmap, vmin=-0.5, vmax=len(SIDE) - 0.5, shading="nearest", rasterized=True)
    ax.set_xlim(0, 200); ax.set_ylim(Z_LO, 470); ax.set_aspect("equal")
    ax.set_xlabel("r (mm)"); ax.set_ylabel("z (mm), side A; the hub's equator at 470")
    ax.set_title("(a) The model: side A at 0°, aligned (60° mirror wedge)", loc="left")
    for txt, xy in (("stator vanes (REF)", (152, 362)), ("rotor vanes (node 1)", (60, 352)), ("Ca node-1 plates", (152, 256)),
                    ("Ca node-2 plates", (152, 216)), ("G10 sleeve on the shaft", (24, 300)), ("hub-face bearing + spider", (30, 392)),
                    ("Ca|reluctance bearing", (30, 210)), ("utron (REF)", (75, 185)), ("bridge (floating)", (133, 160)),
                    ("G10 cage", (168, 330)), ("flange, AH, ring A", (36, 440))):
        ax.annotate(txt, xy, fontsize=7.5, color=INK)
    ax.text(0.0, -0.075, "dielectrics (G10, PEEK, gel, glass) tinted; the REF wall at r 400 mm and the reluctance "
            "section's mid-plane (z 100) close the box", transform=ax.transAxes, fontsize=7, color=INK2)
    best = res["side_best"]
    # (b) the strays per node, by the part they reach (the colours follow the part)
    ax = fig.add_subplot(gs[0, 1])
    cats = [("SHAFT", "the shaft, flange and AH (through the sleeve)"), ("SA", "the stator vanes (node 1's: the Ca node-1 plates')"), ("UT", "the utrons"),
            ("BRG", "the bearings"), ("W", "the room (REF wall, r 400)")]
    rows = []
    for node, grp, srcs in (("node 1 / 4", "items1", ("N1v", "N1c")), ("node 2 / 3", "items2", ("N2",))):
        it = {k: 0.5 * (best["aligned"][grp].get(k, 0) + best["unaligned"][grp].get(k, 0)) for k in best["aligned"][grp]}
        rows.append((node, [sum(it.get(f"{s_}-{c}", 0.0) for s_ in srcs) for c, _ in cats]))
    y = [1.0, 0.0]
    for (node, vals), yy in zip(rows, y):
        x0 = 0.0
        for k, v in enumerate(vals):
            ax.barh(yy, v, left=x0, height=0.42, color=SERIES[k], edgecolor=SURF, linewidth=2,
                    label=cats[k][1] if yy == 1.0 else None)
            if v > 3.0:
                ax.text(x0 + 0.5 * v, yy + 0.27, f"{v:.1f}", ha="center", va="bottom", fontsize=7.5, color=INK)
            x0 += v
        ax.text(x0 + 1, yy, f"{x0:.1f} pF", va="center", fontsize=9, color=INK, fontweight="bold")
    ax.axvline(res["record_deck"]["CPAR_pF"], color=INK2, lw=1)
    ax.text(res["record_deck"]["CPAR_pF"] + 0.6, 1.5, "the record: 20 pF per node [RH]", fontsize=7.5, color=INK2)
    ax.set_yticks(y); ax.set_yticklabels([r[0] for r in rows]); ax.set_ylim(-1.15, 1.7)
    ax.set_xlim(0, 1.22 * max(sum(r[1]) for r in rows))
    ax.set_xlabel("stray to REF per side, pF (mean of the two angles; the varicap's and Ca's own taken out)")
    ax.set_title("(b) The strays per node, by the part they reach", loc="left")
    ax.grid(axis="x", color=GRID, lw=0.8); ax.set_axisbelow(True)
    ax.legend(fontsize=6.8, loc="lower right", ncol=1, frameon=False)
    # (c) the varicap
    ax = fig.add_subplot(gs[0, 2])
    cl = res["cell"]
    n = cl["record"]["n_gap"]
    nr, wr = cl["no_rims"][-1], cl["with_rims"][-1]
    models = [("the record, 2-D cell + 2 pF", res["inputs"]["C_max_pF"], res["inputs"]["C_min_pF"]),
              ("3-D cell, no rims × 11", n * nr["aligned"], n * nr["unaligned"]),
              ("3-D cell, rims × 11", n * wr["aligned"], n * wr["unaligned"]),
              ("the stack, ends in", best["aligned"]["varicap"], best["unaligned"]["varicap"]),
              ("node 1 to REF, all", best["aligned"]["node1_ref"], best["unaligned"]["node1_ref"])]
    xx = np.arange(len(models))
    ax.bar(xx - 0.17, [m[1] for m in models], width=0.3, color=SERIES[0], label="aligned (C_max)", edgecolor=SURF, linewidth=1)
    ax.bar(xx + 0.17, [m[2] for m in models], width=0.3, color=SERIES[1], label="unaligned (C_min)", edgecolor=SURF, linewidth=1)
    for k, m in enumerate(models):
        ax.text(k, max(m[1], m[2]) + 34, f"κ {m[1] / m[2]:.2f}", ha="center", fontsize=8, color=INK, fontweight="bold")
        ax.text(k + 0.17, m[2] + 6, f"{m[2]:.0f}", ha="center", fontsize=7, color=INK2)
        ax.text(k - 0.17, m[1] + 6, f"{m[1]:.0f}", ha="center", fontsize=7, color=INK2)
    ax.set_xticks(xx); ax.set_xticklabels([m[0].replace(", ", ",\n", 1) for m in models], fontsize=7)
    ax.set_ylabel("C1 per side, pF"); ax.set_ylim(0, 640)
    ax.set_title("(c) The varicap C1: the rims' fringe the 2-D cell leaves out", loc="left")
    ax.legend(fontsize=7.5, frameon=False, loc="upper left")
    ax.grid(axis="y", color=GRID, lw=0.8); ax.set_axisbelow(True)
    # (d) the gain, (e) the power
    D = res["decks"]["table"]
    show = [k for k in ("record", "strays", "strays + rings", "varicap as solved, 20 pF", "as built") if k in D]
    names = {"record": "the record\n(20 pF)", "strays": "record caps,\nsolved strays", "strays + rings": "+ the rings'\nsolved strays",
             "varicap as solved, 20 pF": "varicap solved,\n20 pF", "as built": "as built\n(all solved)"}
    ax = fig.add_subplot(gs[1, 1])
    xx = np.arange(len(show))
    zb = [D[k]["z"] for k in show]
    zr = [D[k].get("z_rings_start") for k in show]
    ax.bar(xx - 0.17, zb, width=0.3, color=SERIES[0], label="z, bare (12 free cycles)", edgecolor=SURF, linewidth=1)
    ax.bar(xx + 0.17, [v or 0 for v in zr], width=0.3, color=SERIES[2], label="z at start-up, with the rings' chains", edgecolor=SURF, linewidth=1)
    for k in range(len(show)):
        ax.text(k - 0.17, zb[k] + 0.006, f"{zb[k]:.3f}", ha="center", fontsize=7, color=INK)
        if zr[k]:
            ax.text(k + 0.17, zr[k] + 0.006, f"{zr[k]:.3f}", ha="center", fontsize=7, color=INK)
    ax.axhline(1.0, color=INK2, lw=1, label="z = 1: no self-excitation below")
    ax.set_ylim(0.9, 1.36); ax.set_xticks(xx); ax.set_xticklabels([names[k] for k in show], fontsize=7.5)
    ax.set_ylabel("gain per pump cycle, z")
    ax.set_title("(d) The start-up gain (sim/core_field.py's deck)", loc="left")
    ax.legend(fontsize=7.5, frameon=False, loc="upper right")
    ax.grid(axis="y", color=GRID, lw=0.8); ax.set_axisbelow(True)
    ax = fig.add_subplot(gs[1, 2])
    pw = [D[k].get("P_clamped_W") or 0 for k in show]
    ax.bar(xx, pw, width=0.4, color=SERIES[0], edgecolor=SURF, linewidth=1)
    for k in range(len(show)):
        va, vb = D[show[k]].get("V_A_kV"), D[show[k]].get("V_B_kV")
        ax.text(k, pw[k] + 0.03, f"{pw[k]:.2f} W" + (f"\nrings ±{0.5 * (vb - va):.2f} kV" if va is not None else ""),
                ha="center", va="bottom", fontsize=7.2, color=INK)
    ax.set_ylim(0, 1.2 * max(pw))
    ax.set_xticks(xx); ax.set_xticklabels([names[k] for k in show], fontsize=7.5)
    ax.set_ylabel("clamped power from the belt, W (clamps at 13.13 kV)")
    ax.set_title("(e) The clamped power and the rings' supply", loc="left")
    ax.grid(axis="y", color=GRID, lw=0.8); ax.set_axisbelow(True)
    fig.suptitle("The tube's strays by a field solve: the record's electrostatic stack (6 + 6 vanes, 6 mm gaps, Ca / Cb 6 plates) "
                 "in 3-D — sim/tube_strays.py", x=0.045, ha="left", fontsize=11.5, fontweight="bold", color=INK)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    fig.savefig(path, dpi=130, facecolor=SURF)
    plt.close(fig)
    log(f"  figure: {os.path.relpath(path, ROOT)}")


# ================================================================================================ main
def _cost(j):
    if j["kind"] == "side":
        return {0: 1.3, 1: 3.2, 2: 7.0}[j["kw"]["level"]] * (1.3 if j["kw"].get("unaligned") else 1.0) * len(j["drive"]) / 8.0
    if j["kind"] == "cell":
        return 0.02 if j["kw"]["h"] >= 0.5 else 0.3
    return 0.5


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--resume", action="store_true", help="reuse the solves already in the results file")
    ap.add_argument("--procs", type=int, default=3)
    ap.add_argument("--levels", type=int, nargs="*", default=[0, 1, 2])
    ap.add_argument("--solves-only", action="store_true", help="run the solves and stop")
    ap.add_argument("--results", default=RESULTS, help="the results file (default sim/tube_strays_results.json)")
    ap.add_argument("--merge", nargs="*", default=[], help="other results files whose solves to reuse (same signature)")
    ap.add_argument("--only", nargs="*", default=None, help="run only these solves (their keys)")
    ap.add_argument("--figure-only", action="store_true", help="redraw the figure from the results file")
    a = ap.parse_args()
    if a.figure_only:
        return figure(json.load(open(a.results)))
    t0 = time.time()
    sig = signature()
    old = json.load(open(a.results)) if a.resume and os.path.exists(a.results) else {}
    cache = old.get("solves", {}) if old.get("signature") == sig else {}
    for f_ in a.merge:
        o_ = json.load(open(f_)) if os.path.exists(f_) else {}
        if o_.get("signature") == sig:
            cache.update({k: v for k, v in o_.get("solves", {}).items() if k not in cache})
    I = inputs()
    rec = I["rec"]
    res = dict(note="the tube's strays by a field solve (sim/tube_strays.py; findings sim/tube-strays-findings.md). "
                    "Capacitances in pF per side unless stated; the deck's sets in F.",
               tags="CONVENTIONS.md section 1: [OC] derivable physics; [IR] a modelling choice; [RH] a heuristic",
               sources=SRC, signature=sig, levels=LEVELS, cell_h_mm=list(CELL_H), wedge_deg=WEDGE, r_box_mm=R_BOX, z_lo_mm=Z_LO,
               inputs=dict(C_max_pF=rec["C_max_pF"], C_min_pF=rec["C_min_pF"], Ca_pF=rec["Ca_pF"], kappa=rec["kappa"],
                           per_gap_max_pF=rec["per_gap_max_pF"], per_gap_min_pF=rec["per_gap_min_pF"], n_gap=rec["n_gap"],
                           t_vane_mm=rec["t_vaneMm"], gap_mm=rec["gap_mm"], ws_deg=rec["ws_deg"], wr_deg=rec["wr_deg"],
                           eps_air=I["eps_air"], eps_g10=I["hub"]["shaft_coupler"]["value"]["eps_r"],
                           Ca_parallel_plate_pF=5 * EPS0_MM * I["eps_air"] * math.pi * (150 ** 2 - 50 ** 2) / rec["gap_mm"] * 1e12),
               solves=cache)
    print("the solver's gates", flush=True)
    res["gates"] = dict(analytic=gate_analytic(), vane_record_like=gate_vane_record_like())
    todo = [j for j in jobs(a.levels) if j["key"] not in cache and (a.only is None or j["key"] in a.only)]
    small = sorted([j for j in todo if not (j["kind"] == "side" and j["kw"]["level"] >= 2)], key=_cost, reverse=True)
    big = sorted([j for j in todo if j not in small], key=_cost, reverse=True)
    print(f"{len(todo)} solves to run ({len(cache)} cached)", flush=True)
    for group, procs in ((small, a.procs), (big, max(1, min(a.procs, 2)))):
        if not group:
            continue
        with Pool(procs, maxtasksperchild=1) as pool:
            for s in pool.imap_unordered(_solve, group):
                cache[s["key"]] = s
                json.dump(res, open(a.results, "w"), indent=1, default=float)
                print(f"solved {s['key']} in {s['run_s']:.0f} s", flush=True)
    if a.solves_only:
        return
    analyse(res, sorted(set(a.levels)))
    res["record_deck"] = record_deck()
    sets = stray_sets(res)
    res["decks"] = dict(sets={k: {kk: vv for kk, vv in v.items()} for k, v in sets.items()})
    print("the decks", flush=True)
    res["decks"]["table"] = run_decks(sets, res["record_deck"]["rings_kw"], a.procs)
    res["decks"]["sensitivity"] = sensitivity(a.procs)
    R, T = res["record_deck"], res["decks"]["table"]["record"]
    res["gates"]["deck_record"] = dict(z=[T["z"], R["z_free"]], P_clamped_W=[T.get("P_clamped_W"), R["P_clamped_W"]],
                                       z_rings=[T.get("z_rings_start"), R["z_rings"]], rings_P_belt_W=[T.get("rings_P_belt_W"), R["rings_P_belt_W"]],
                                       V_A_kV=[T.get("V_A_kV"), R["V_A_kV"]], V_B_kV=[T.get("V_B_kV"), R["V_B_kV"]])
    figure(res)
    res["run_s"] = time.time() - t0
    json.dump(res, open(a.results, "w"), indent=1, default=float)
    print(f"done in {res['run_s']:.0f} s", flush=True)


if __name__ == "__main__":
    main()
