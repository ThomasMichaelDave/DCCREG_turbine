"""sim/utron_3d.py -- a 3-D check of the utrons' inductance swing (ledger §6 item 34, the open model check of §5.2):
L_aligned, L_unaligned, kappa = L_al / L_un and L_max of the pick (g 0.5 / 6 bridges / 1200 rpm relative), against
the record's 2-D field solve (sim/pole_fd2d.py) and its end corrections (K_END_A 0.03, K_END_U 0.30 [RH]); then the
pump's gain with the 3-D values, by the pick's own deck (sim/magnetic_doubler.py, run as sim/rotor_parts_duty.py and
sim/ah_steady_cusp.py run it). Writes sim/utron_3d_results.json and docs/figures/utron-3d.png.

Model:
- linear magnetostatics in the reduced form H = T - grad(Omega), div(mu H) = 0 [OC]. T is the winding's current
  vector potential (curl T = J): along the winding's axis v, N I / (2 cv) inside the hole, falling linearly through
  the build to 0 outside, i.e. a uniform current density over the real section and round the end turns (rounded
  rectangles, R 1 inside and R 28 outside, sim/utron_profile.coil_ring) [OC];
- node-based finite volumes on graded tensor grids, one unknown per node; T enters through its exact edge integrals,
  so in the iron (inside the hole, carrying no current) T is an exact discrete gradient and the reduced potential has
  no cancellation error, only the solver's round-off [OC]. L / N^2 = sum_e w_e H_e^2 (twice the energy per
  ampere-turn squared); the scheme minimises the co-energy and converges from above, the record's A_z solve
  (sim/pole_fd2d.py) from below [OC: complementary formulations; gate G-2D]. Smoothed-aggregation AMG (pyamg,
  evolution strength) preconditions CG to a 1e-11 residual [IR];
- iron linear: mu_r 3000 as the record (sim/pole_fd2d.MUR_FE), 4000, and 1e5 for the mu -> infinity limit [IR];
- two frames [IR]:
  (a) the record's unrolled frame (sim/pole_fd2d.Design: y = u - r_g, x = the arc at r_g, the 120 deg period, the
      record's section with flux-tight walls 40 mm below the coil and above the bridges), extruded over the 100 mm
      stack, with free space beyond the stack's ends;
  (b) the machine's cylinder (r, theta, z) with the as-built shapes of sim/utron_profile.spec: parallel-sided tips with
      their faces on the gap arc, the flat back iron (both staircased on the polar grid; a cell carrying winding
      current is air), the 0.5 mm gap and the bridges' annular sectors conformal; r 12.5 mm (the non-magnetic shaft)
      to 260 mm, flux-tight [IR];
- the three coils of a group are in series. Identical copies circulate the same way round the machine axis, so their
  holes see 3 N I in total (Ampere) and a circumferential (toroidal) flux links all three [OC]. Mirrors give the two
  limits: Omega = 0 half way to the next utron is the periodic set of identical coils ('free'); a flux-tight plane
  there is the alternating set, with no net circumferential MMF ('alt'). In 2-D the alternating set reproduces the
  record's A = 0 walls to 0.1 % (gate G-2D), so 'alt' is the record's convention in 3-D; the cylinder's half model
  (0-180 deg, one coil excited) gives the self and mutual inductances for any winding sense [OC: linearity];
- symmetry: the stack's mid-plane, and (aligned, unaligned) the utron's centre line [OC]. Neighbouring utrons and the
  six bridges are in every model (the 120 deg period, or the half machine).
Gates: G-SOL (the long solenoid), G-AIR (the air-cored winding against an independent Neumann integral), G-2D (the
section against sim/pole_fd2d.py, bracketed), G-CCORE (the record's own gapped-core self-check), G-MESH (three
refinements), G-LONG (long stacks reproduce the 2-D per-length L), G-DECK (the record's deck reproduces the pick).
Usage: python3 sim/utron_3d.py   (about 20-40 min on 4 cores: 44 3-D solves of 0.1-0.5 M nodes, 14 ngspice runs)
"""
import json
import math
import os
import sys
import time
from multiprocessing import Pool

import numpy as np
import scipy.sparse as sp

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
import pole_fd2d as P2D           # noqa: E402  the record's 2-D solve (read, never edited)
import utron_profile as UP        # noqa: E402  every dimension of the pick
import pole_design as PD          # noqa: E402  fit_cos, _z_at (the screen's z_lin)
import rotor_parts_duty as RP     # noqa: E402  how the pick's deck is run
import ah_steady_cusp as ACS      # noqa: E402  the bypass (PROPOSED)

MU0 = 4e-7 * math.pi
MM = 1e-3
MU_REC = P2D.MUR_FE                      # 3000, the record's iron [RH there]
MU_SET = (4000.0, 1e5)                   # the brief's 'large mu_r', and the mu -> infinity limit [IR]
H_MESH = (2.0, 1.4, 1.0)                 # mesh scales (mm) of the gate G-MESH; the finest is the production mesh
H_AUX = 2.0                              # the comparisons that are quoted as ratios to the same-mesh reference [IR]
H_CYL = 1.4                              # the cylinder's finer mesh (it runs at H_AUX and H_CYL)
H_AIR = (2.0, 1.4)                       # meshes of the air-cored winding (G-AIR)
A_NEU = (1.0, 0.7)                       # pixel sizes of the Neumann integral (G-AIR), mm
THETA_MID = (2.5, 5.0, 7.5, 10.0, 15.0, 20.0)   # intermediate rotor angles, deg (the record's grid is 0:2.5:30)
L_LONG = (300.0, 600.0)                  # stack lengths of the gate G-LONG, mm
FD_REFINE = ((1090, 0.05),)              # sim/pole_fd2d.solve refined: X / 1090 cells in x (its own X / 545 lands the
                                         # aligned tips and bridges on cell faces; this keeps them there), fine 0.05
H_2D_FINE = (0.5, 0.35)                  # finer 2-D scalar sections for the bracket of G-2D
C_BYP = (0.0, 22.0)                      # mF across each AH coil (sim/ah_steady_cusp.py; 22 mF is PROPOSED)
STRENGTH = ("evolution", {})
NPROC = min(4, os.cpu_count() or 1)
OUT_DIR = os.environ.get("UTRON3D_OUT")                 # testing only: write the results and the figure elsewhere
if os.environ.get("UTRON3D_QUICK"):                     # testing only: coarse meshes
    H_MESH, H_AUX, H_CYL, THETA_MID, FD_REFINE, H_2D_FINE = (4.0, 3.0, 2.0), 4.0, 3.0, (5.0,), ((1090, 0.05),), (1.5,)
    H_AIR, A_NEU = (4.0, 3.0), (2.0, 1.0)


# ================================================================================================= the record's inputs
def record():
    """the pick as recorded: sim/pole_design_variants_op.json (design, operating point), sim/pole_design_variants.json
    (its characterised row), sim/utron_profile.spec (the built dimensions)."""
    op = json.load(open(os.path.join(HERE, "pole_design_variants_op.json")))["designs"][RP.PICK]
    rows = json.load(open(os.path.join(HERE, "pole_design_variants.json")))["rows"]
    row = [r for r in rows if r["design"] == op["design"]][0]
    s = UP.spec(op["design"], op["best"], row)
    spec = {k: s[k] for k in ("r_g", "g", "w_p", "s", "d", "b", "L", "clr", "n_br", "t_b", "W_u", "l_b", "cv", "u_y0",
                              "u_y1", "u_p0", "u_p1", "u_m0", "u_m1", "h_c", "over", "N_u", "br_deg")}
    return dict(op=op, row=row, spec=spec, best=op["best"])


# ================================================================================================= finite volumes
def graded(breaks, lo, hi, coarse, grow=1.3):
    """nodes lo..hi: every break (x, h) is a node with cells <= h beside it, growing geometrically, capped at coarse."""
    br = {}
    for x, h in list(breaks) + [(lo, coarse), (hi, coarse)]:
        if lo - 1e-12 <= x <= hi + 1e-12:
            k = round(min(max(x, lo), hi), 12)
            br[k] = min(h, br.get(k, coarse))
    xb = np.array(sorted(br))
    hb = np.array([br[k] for k in sorted(br)])

    def hfun(x):
        return np.minimum(coarse, np.min(hb[None, :] + (grow - 1.0) * np.abs(x[:, None] - xb[None, :]), axis=1))
    nodes = [xb[0]]
    for a, b in zip(xb[:-1], xb[1:]):
        xs = np.linspace(a, b, 4001)
        s = np.concatenate([[0.0], np.cumsum(np.diff(xs) / hfun(0.5 * (xs[1:] + xs[:-1])))])
        n = max(1, int(math.ceil(s[-1] - 1e-6)))
        nodes += list(np.interp(np.linspace(0.0, s[-1], n + 1)[1:], s, xs))
        nodes[-1] = b
    return np.array(nodes)


class Grid:
    """orthogonal tensor grid: Cartesian, or cylindrical (r, theta, z) with cyl=True. xs: node coordinates (m, rad);
    bcs per axis: (lo, hi) each 'nat' (B_n = 0) or 'dir' (Omega fixed: an odd mirror, H_t = 0), or 'per'."""

    def __init__(self, xs, bcs, cyl=False):
        self.cyl, self.bc = cyl, bcs
        self.x = [np.asarray(x, float) for x in xs]
        self.per = [b == "per" for b in bcs]
        self.h = [np.diff(x) for x in self.x]
        self.nc = [len(h) for h in self.h]
        self.nn = [n if p else n + 1 for n, p in zip(self.nc, self.per)]
        self.xn = [x[:-1] if p else x for x, p in zip(self.x, self.per)]
        self.xc = [0.5 * (x[1:] + x[:-1]) for x in self.x]
        self.eshape = [tuple(self.nc[b] if b == a else self.nn[b] for b in range(3)) for a in range(3)]
        self.eoff = np.cumsum([0] + [int(np.prod(s)) for s in self.eshape])
        self.ne, self.N = int(self.eoff[-1]), int(np.prod(self.nn))

    def eidx(self, a):
        return np.indices(self.eshape[a]).reshape(3, -1)

    def grad(self):
        """edges x nodes: Omega(head) - Omega(tail)."""
        rows, cols, vals = [], [], []
        for a in range(3):
            I = self.eidx(a)
            e = self.eoff[a] + np.arange(I.shape[1])
            J = I.copy()
            J[a] = (I[a] + 1) % self.nn[a] if self.per[a] else I[a] + 1
            rows += [e, e]
            cols += [np.ravel_multi_index(tuple(J), tuple(self.nn)), np.ravel_multi_index(tuple(I), tuple(self.nn))]
            vals += [np.ones(e.size), -np.ones(e.size)]
        return sp.csr_matrix((np.concatenate(vals), (np.concatenate(rows), np.concatenate(cols))), shape=(self.ne, self.N))

    def _half(self, ax, node, side, rweight):
        """the half cell next to a node on `side` (-1 below, 0 above) along ax: its measure (int r dr on the r axis of a
        cylinder when rweight), whether it exists, the cell index."""
        ic = node + side
        if self.per[ax]:
            ok, ic = np.ones(ic.shape, bool), ic % self.nc[ax]
        else:
            ok = (ic >= 0) & (ic < self.nc[ax])
            ic = np.clip(ic, 0, self.nc[ax] - 1)
        hh = 0.5 * self.h[ax][ic]
        if self.cyl and ax == 0 and rweight:
            r0 = self.xn[0][np.clip(node, 0, self.nn[0] - 1)]
            m = 0.5 * np.abs(r0 ** 2 - (r0 - hh if side == -1 else r0 + hh) ** 2)
        else:
            m = hh
        return np.where(ok, m, 0.0), ok, ic

    def edge_weight(self, mu_cell):
        """w_e = mu_e A*_e / l_e: the dual face of each edge over its (up to) four cells, in the grid's metric [OC]."""
        out = []
        for a in range(3):
            b, c = (a + 1) % 3, (a + 2) % 3
            I = self.eidx(a)
            acc = np.zeros(I.shape[1])
            for db in (-1, 0):
                for dc in (-1, 0):
                    J = [I[0].copy(), I[1].copy(), I[2].copy()]
                    mb, okb, ib = self._half(b, I[b], db, rweight=(a == 2))
                    mc, okc, icc = self._half(c, I[c], dc, rweight=(a == 2))
                    J[b], J[c] = ib, icc
                    area = mb * mc
                    if self.cyl and a == 0:
                        area = area * 0.5 * (self.x[0][I[0]] + self.x[0][I[0] + 1])
                    acc += np.where(okb & okc, mu_cell[tuple(J)] * area, 0.0)
            l = self.xn[0][I[0]] * self.h[1][I[1]] if (self.cyl and a == 1) else self.h[a][I[a]]
            out.append(acc / l)
        return np.concatenate(out)


def fv_solve(G, mu_cell, taus, dirich, fixed=None, tol=1e-11, maxiter=800):
    """K Omega = G^T W tau for each tau; Omega fixed on the node mask dirich (values from fixed[q], else 0)."""
    import pyamg
    t0 = time.time()
    Gm = G.grad()
    w = G.edge_weight(mu_cell)
    K = (Gm.T @ sp.diags(w) @ Gm).tocsr()
    free = ~dirich
    Kf = K[free][:, free].tocsr()
    ml = pyamg.smoothed_aggregation_solver(Kf, symmetry="symmetric", max_coarse=500, strength=STRENGTH)
    t1 = time.time()
    outs, its = [], []
    for q, tau in enumerate(taus):
        Om = np.zeros(G.N)
        if fixed is not None and fixed[q] is not None:
            Om[dirich] = fixed[q][dirich]
        rhs = Gm.T @ (w * tau) - K @ Om
        res = []
        Om[free] = ml.solve(rhs[free], tol=tol, accel="cg", maxiter=maxiter, residuals=res)
        its.append([len(res), float(res[-1] / max(res[0], 1e-300))])
        outs.append(tau - Gm @ Om)
    return outs, w, dict(nodes=int(G.N), setup_s=t1 - t0, solve_s=time.time() - t1, cg=its)


# ================================================================================================= the winding's T
GL_X, GL_W = np.polynomial.legendre.leggauss(4)


def coil(sp_, theta_c=0.0, s=1.0, x_c=0.0, period=None, L=None):
    """the winding (sim/utron_profile.coil_ring): its hole's core is the back iron's (u, w) section u_y0..u_y1 x 0..L;
    inner offset clr (R 1), outer offset clr + h_c (R 28); width 2 cv along v."""
    return dict(u0=sp_["u_y0"], u1=sp_["u_y1"], z0=0.0, z1=sp_["L"] if L is None else L, Ri=sp_["clr"],
                Ro=sp_["clr"] + sp_["h_c"], cv=sp_["cv"], theta_c=theta_c, s=s, x_c=x_c, period=period, r_g=sp_["r_g"])


def gfun(u, z, c):
    """1 in the hole, linear through the build, 0 outside [OC: a uniform current density across the build]."""
    du = np.maximum(np.maximum(c["u0"] - u, u - c["u1"]), 0.0)
    dz = np.maximum(np.maximum(c["z0"] - z, z - c["z1"]), 0.0)
    return np.clip((c["Ro"] - np.hypot(du, dz)) / (c["Ro"] - c["Ri"]), 0.0, 1.0)


def _gauss(a, b, f, brk):
    pts = np.sort(np.concatenate([a[:, None], np.clip(brk, a[:, None], b[:, None]), b[:, None]], axis=1), axis=1)
    lo, hi = pts[:, :-1], pts[:, 1:]
    mid, half = 0.5 * (lo + hi), 0.5 * (hi - lo)
    tot = np.zeros(a.size)
    for xg, wg in zip(GL_X, GL_W):
        tot += np.sum(wg * half * f(mid + half * xg), axis=1)
    return tot


def _u_breaks(c, z):
    dz = np.maximum(np.maximum(c["z0"] - z, z - c["z1"]), 0.0)
    out = [np.full(z.shape, c["u0"]), np.full(z.shape, c["u1"])]
    for R in (c["Ri"], c["Ro"]):
        d = np.sqrt(np.maximum(R * R - dz * dz, 0.0))
        out += [np.where(R > dz, c["u0"] - d, c["u0"]), np.where(R > dz, c["u1"] + d, c["u1"])]
    return np.stack(out, axis=1)


def tau_cyl(G, coils):
    """edge integrals of T on a cylindrical grid: 4-point Gauss between the kinks of g and the step of the width,
    exact for the iron's constant-direction T [OC]."""
    tau = np.zeros(G.ne)
    rN, zN, tN = G.xn[0] / MM, G.xn[2] / MM, G.xn[1]
    for c in coils:
        npr, reach = c["s"] / (2 * c["cv"]), c["Ro"] + 2.0
        I = G.eidx(0)                                            # r-edges
        phi = (tN[I[1]] - c["theta_c"] + math.pi) % (2 * math.pi) - math.pi
        z = zN[I[2]]
        ra, rb = G.x[0][I[0]] / MM, G.x[0][I[0] + 1] / MM
        sn, cs = np.sin(phi), np.cos(phi)
        sel = (np.minimum(np.abs(ra * sn), np.abs(rb * sn)) <= c["cv"] + 1e-9) & (cs > 0) & \
              (rb * cs >= c["u0"] - reach) & (ra * cs <= c["u1"] + reach) & (z <= c["z1"] + reach) & \
              (z >= c["z0"] - reach) & (np.abs(sn) > 1e-15)
        if sel.any():
            p, q, zz, s_, c_ = ra[sel], rb[sel], z[sel], sn[sel], cs[sel]
            brk = np.concatenate([_u_breaks(c, zz) / c_[:, None], (c["cv"] / np.abs(s_))[:, None]], axis=1)
            f = lambda r: gfun(r * c_[:, None], zz[:, None], c) * (np.abs(r * s_[:, None]) <= c["cv"])
            tau[G.eoff[0] + np.where(sel)[0]] += npr * s_ * _gauss(p, q, f, brk)
        I = G.eidx(1)                                            # theta-edges
        r, z = rN[I[0]], zN[I[2]]
        ta = (G.x[1][I[1]] - c["theta_c"] + math.pi) % (2 * math.pi) - math.pi
        tb = ta + G.h[1][I[1]]
        ps = np.arcsin(np.clip(c["cv"] / np.maximum(r, 1e-9), 0.0, 1.0))
        sel = (ta < ps) & (tb > -ps) & (np.abs(ta) < 1.5) & (r >= c["u0"] - reach) & \
              (r <= math.hypot(c["u1"] + reach, c["cv"] + reach)) & (z <= c["z1"] + reach) & (z >= c["z0"] - reach)
        if sel.any():
            rr, zz, p, q = r[sel], z[sel], ta[sel], tb[sel]
            ang = np.arccos(np.clip(_u_breaks(c, zz) / rr[:, None], -1.0, 1.0))
            pss = np.arcsin(np.clip(c["cv"] / rr, 0.0, 1.0))
            brk = np.concatenate([ang, -ang, pss[:, None], -pss[:, None]], axis=1)
            f = lambda t: gfun(rr[:, None] * np.cos(t), zz[:, None], c) * \
                (np.abs(rr[:, None] * np.sin(t)) <= c["cv"]) * rr[:, None] * np.cos(t)
            tau[G.eoff[1] + np.where(sel)[0]] += npr * _gauss(p, q, f, brk)
    return tau


def tau_cart(G, coils):
    """unrolled frame (y = u - r_g, x, z): T along x, exact on x-edges (g is constant along them) [OC]."""
    tau = np.zeros(G.ne)
    yN, zN = G.xn[0] / MM, G.xn[2] / MM
    xa, xb = G.x[1][:-1] / MM, G.x[1][1:] / MM
    I = G.eidx(1)
    for c in coils:
        g = gfun(yN[I[0]] + c["r_g"], zN[I[2]], c)
        ov = np.zeros(I.shape[1])
        for sh in ((0.0,) if not c["period"] else (-c["period"], 0.0, c["period"])):
            ov += np.clip(np.minimum(xb[I[1]], c["x_c"] + sh + c["cv"]) - np.maximum(xa[I[1]], c["x_c"] + sh - c["cv"]),
                          0.0, None)
        tau[G.eoff[1]:G.eoff[2]] += c["s"] / (2 * c["cv"]) * g * ov
    return tau


def current_cells(G, tau, rel=1e-12):
    """cells with a face that carries winding current (the discrete curl of tau) [OC: Stokes]."""
    t0, t1, t2 = (tau[G.eoff[a]:G.eoff[a + 1]].reshape(G.eshape[a]) for a in range(3))
    nxt = lambda A, ax: np.roll(A, -1, axis=ax) if G.per[ax] else np.take(A, range(1, A.shape[ax]), axis=ax)
    cur = lambda A, ax: A if G.per[ax] else np.take(A, range(0, A.shape[ax] - 1), axis=ax)
    c2 = cur(t0, 1) - nxt(t0, 1) + nxt(t1, 0) - cur(t1, 0)
    c1 = cur(t2, 0) - nxt(t2, 0) + nxt(t0, 2) - cur(t0, 2)
    c0 = cur(t1, 2) - nxt(t1, 2) + nxt(t2, 1) - cur(t2, 1)
    eps = rel * max(np.abs(c0).max(), np.abs(c1).max(), np.abs(c2).max(), 1e-300)
    hot = np.zeros(tuple(G.nc), bool)
    for A, ax in ((c2, 2), (c1, 1), (c0, 0)):
        a = np.abs(A) > eps
        hot |= cur(a, ax) | nxt(a, ax)
    return hot


# ================================================================================================= the utron models
def mesh_par(h):
    """mesh scale h (mm) -> the gap cells, the tip / bridge edges, the stack end, the coarse cap [IR]."""
    return dict(hg=min(0.1, 0.2 * h), hx=0.5 * h, hz=min(0.25, 0.25 * h), h=h, hc=6.0 * h, grow=1.3)


def build_cart(sp_, theta, h, mu_r, mode="quarter", two_d=False, L=None, zfar=None, ywall=0.0, far_z="nat",
               far_x="dir", xmax=None, far_y="nat", iron=True):
    """(a) the record's frame: its section (sim/pole_fd2d.Design: tips y -d..0, back iron -d-b..-d, bridges g..g+t_b,
    walls 40 mm beyond) over the stack. mode 'quarter': x 0..X/2 (mirrors at the utron's centre and half way to the
    next, aligned / unaligned); 'half': x -X/2..X/2, periodic ('free') or flux-tight at both ends ('alt')."""
    m = mesh_par(h)
    L = sp_["L"] if L is None else L
    X = 2 * math.pi * sp_["r_g"] / 3.0
    pitch = 2 * math.pi * sp_["r_g"] / sp_["n_br"]
    xu = sp_["r_g"] * math.radians(theta)
    d, b, g, rg = sp_["d"], sp_["b"], sp_["g"], sp_["r_g"]
    ylo, yhi = (sp_["u_m0"] - rg) - 40.0 - ywall, g + sp_["t_b"] + 40.0 + ywall
    ybr = [(0.0, m["hg"]), (g, m["hg"]), (-d, h), (-d - b, h), (g + sp_["t_b"], h), (sp_["u_p0"] - rg, h),
           (sp_["u_p1"] - rg, h), (sp_["u_m1"] - rg, h), (sp_["u_m0"] - rg, h)]
    y = graded(ybr, ylo, yhi, m["hc"], m["grow"])
    bridges = [(j * pitch - xu) for j in range(-2, 4)]
    xbr = [(v, m["hx"]) for v in (sp_["s"] / 2, sp_["s"] / 2 + sp_["w_p"], -sp_["s"] / 2, -sp_["s"] / 2 - sp_["w_p"])]
    xbr += [(sp_["cv"], h), (-sp_["cv"], h)] + [(xb + sgn * sp_["l_b"] / 2, m["hx"]) for xb in bridges for sgn in (-1, 1)]
    if mode == "quarter":
        xm = X / 2 if xmax is None else xmax
        x = graded([q for q in xbr if -1e-9 <= q[0] <= xm], 0.0, xm, m["hc"], m["grow"])
        bcx = ("dir", far_x)
    else:
        x = graded(xbr, -X / 2, X / 2, m["hc"], m["grow"])
        bcx = "per" if far_x == "per" else (far_x, far_x)
    if two_d:
        z, bcz = np.array([0.0, 10.0]), "per"
    else:
        zfar = (L + sp_["clr"] + sp_["h_c"] + 200.0) if zfar is None else zfar
        z = graded([(L, m["hz"]), (L + sp_["clr"], h), (L + sp_["clr"] + sp_["h_c"], h)], L / 2, zfar,
                   max(m["hc"], 4 * h), m["grow"])
        bcz = ("nat", far_z)
    G = Grid([y * MM, x * MM, z * MM], [(far_y, far_y), bcx, bcz])
    yc, xc, zc = (G.xc[0] / MM, G.xc[1] / MM, G.xc[2] / MM)
    mu = np.full(tuple(G.nc), MU0)
    if iron:
        inz = np.ones_like(zc, bool) if two_d else (zc < L)
        boxes = [(-d, 0.0, sp_["s"] / 2, sp_["s"] / 2 + sp_["w_p"]), (-d, 0.0, -sp_["s"] / 2 - sp_["w_p"], -sp_["s"] / 2),
                 (-d - b, -d, -sp_["W_u"] / 2, sp_["W_u"] / 2)] + \
                [(g, g + sp_["t_b"], xb - sp_["l_b"] / 2, xb + sp_["l_b"] / 2) for xb in bridges]
        for (y0, y1, x0, x1) in boxes:
            my = (yc >= y0) & (yc < y1)
            mx = np.zeros_like(xc, bool)
            for sh in ((0.0,) if mode == "quarter" else (-X, 0.0, X)):
                mx |= (xc >= x0 + sh) & (xc < x1 + sh)
            mu[my[:, None, None] & mx[None, :, None] & inz[None, None, :]] = MU0 * mu_r
    c = coil(sp_, period=None if mode == "quarter" else X, L=L)
    if two_d:
        c["z0"], c["z1"] = -1e9, 1e9
    tau = tau_cart(G, [c])
    hot = current_cells(G, tau)
    G.n_hot_iron = int(np.sum(hot & (mu > 10 * MU0)))
    mu[hot] = MU0
    sym = (2.0 if mode == "quarter" else 1.0) * (1.0 if two_d else 2.0)
    return G, mu, tau, sym, L


def build_cyl(sp_, theta, h, mu_r, sector="mirror60", L=None, zfar=None, r_min=12.5, r_max=260.0, excite=(1, 1, 1),
              far_t="dir", far_z="nat"):
    """(b) the machine's cylinder. sector 'mirror60': theta 0..60 deg (mirrors at utron 1's centre and half way to
    utron 2; far_t 'dir' = identical coils, 'nat' = alternating); 'half': 0..180 deg (mirrors at 0 and 180 deg; any
    excitation symmetric about utron 1). The rotor angle theta: utron 1 at 0, the bridges at 60 k - theta deg."""
    m = mesh_par(h)
    L = sp_["L"] if L is None else L
    rg, g = sp_["r_g"], sp_["g"]
    rb0, rb1 = rg + g, rg + g + sp_["t_b"]
    half_b = math.radians(sp_["br_deg"]) / 2                     # sim/utron_profile: br_deg = l_b / (r_g + g)
    rbr = [(rg, m["hg"]), (rb0, m["hg"]), (rb1, h)] + [(sp_[k], h) for k in ("u_y1", "u_y0", "u_p0", "u_p1", "u_m1", "u_m0")]
    r = graded(rbr, r_min, r_max, m["hc"], m["grow"])
    t0, t1 = 0.0, (math.pi / 3 if sector == "mirror60" else math.pi)
    bct = ("dir", far_t) if sector == "mirror60" else ("dir", "dir")
    uth = [0.0, 2 * math.pi / 3, -2 * math.pi / 3]
    bth = [math.radians(60.0 * k - theta) for k in range(-6, 7)]
    hx = m["hx"] / rg
    tbr = []
    for tu in uth:
        for v in (sp_["s"] / 2, sp_["s"] / 2 + sp_["w_p"]):
            for sgn in (-1, 1):
                tbr += [(tu + sgn * math.asin(v / rg), hx), (tu + sgn * math.atan2(v, sp_["u_y1"]), 2 * hx)]
        for sgn in (-1, 1):
            tbr += [(tu + sgn * math.atan2(sp_["W_u"] / 2, sp_["u_y0"]), 2 * hx)]
    tbr += [(tb + sgn * half_b, hx) for tb in bth for sgn in (-1, 1)]
    th = graded([q for q in tbr if t0 - 1e-12 <= q[0] <= t1 + 1e-12], t0, t1, m["hc"] / rg, m["grow"])
    zfar = (L + sp_["clr"] + sp_["h_c"] + 200.0) if zfar is None else zfar
    z = graded([(L, m["hz"]), (L + sp_["clr"], h), (L + sp_["clr"] + sp_["h_c"], h)], L / 2, zfar, max(m["hc"], 4 * h),
               m["grow"])
    G = Grid([r * MM, th, z * MM], [("nat", "nat"), bct, ("nat", far_z)], cyl=True)
    R, T = np.meshgrid(G.xc[0] / MM, G.xc[1], indexing="ij")
    iron2 = np.zeros(R.shape, bool)
    for tu in uth:                                               # the U-cores in each utron's own frame (u, v)
        ph = (T - tu + math.pi) % (2 * math.pi) - math.pi
        u, v = R * np.cos(ph), R * np.sin(ph)
        iron2 |= (np.abs(v) >= sp_["s"] / 2) & (np.abs(v) <= sp_["s"] / 2 + sp_["w_p"]) & (u >= sp_["u_y1"]) & (R <= rg)
        iron2 |= (u >= sp_["u_y0"]) & (u <= sp_["u_y1"]) & (np.abs(v) <= sp_["W_u"] / 2)
    for tb in bth:
        ph = (T - tb + math.pi) % (2 * math.pi) - math.pi
        iron2 |= (R >= rb0) & (R <= rb1) & (np.abs(ph) <= half_b)
    mu = np.full(tuple(G.nc), MU0)
    mu[iron2[:, :, None] & (G.xc[2] / MM < L)[None, None, :]] = MU0 * mu_r
    coils = [coil(sp_, theta_c=tu, s=float(excite[k]), L=L) for k, tu in enumerate(uth) if excite[k]]
    tau = tau_cyl(G, coils)
    hot = current_cells(G, tau)
    G.n_hot_iron = int(np.sum(hot & (mu > 10 * MU0)))
    mu[hot] = MU0                                                # a cell carrying winding current is air [IR]
    extra = tau_cyl(G, [coil(sp_, theta_c=uth[1], s=1.0, L=L)]) if sector == "half" else None
    return G, mu, tau, 4.0, L, extra


def solve_case(G, mu, tau, sym, L, record_conv=False, extra=None):
    """L / N^2 = sym x sum w H^2 [OC: 2 W per (A-turn)^2], and its split: the stack (z < L) and the end turns."""
    nn = tuple(G.nn)
    I = np.indices(nn).reshape(3, -1)
    dirich = np.zeros(G.N, bool)
    for ax in range(3):
        if not G.per[ax]:
            for end, pos in ((0, 0), (1, nn[ax] - 1)):
                if G.bc[ax][end] == "dir":
                    dirich |= I[ax] == pos
    if not dirich.any():
        dirich[0] = True                                         # the potential's constant
    taus, fixed = [tau], [None]
    if record_conv:                                              # Omega = c on the far x-plane, zero net flux through it
        unit = np.zeros(G.N); unit[I[1] == nn[1] - 1] = 1.0
        taus.append(np.zeros_like(tau)); fixed.append(unit)
    outs, w, info = fv_solve(G, mu, taus, dirich, fixed)
    H = outs[0]
    if record_conv:
        E = G.eidx(1)
        last = G.eoff[1] + np.where(E[1] == G.nc[1] - 1)[0]
        c = -np.sum(w[last] * H[last]) / np.sum(w[last] * outs[-1][last])
        H = H + c * outs[-1]
    W2 = float(np.sum(w * H * H))
    zedge = np.zeros(G.ne)
    for a in (0, 1):
        zedge[G.eoff[a]:G.eoff[a + 1]] = G.xn[2][G.eidx(a)[2]] / MM
    q = w * H * tau
    in_stack = np.where(zedge < L - 1e-6, 1.0, np.where(zedge > L + 1e-6, 0.0, 0.5))
    out = dict(L=sym * W2, lam_stack=sym * float(np.sum(q * in_stack)), lam_end=sym * float(np.sum(q * (1 - in_stack))),
               check=float(np.sum(q)) / W2 - 1.0, info=info, n_hot_iron=G.n_hot_iron, cells=[int(n) for n in G.nc])
    if extra is not None:
        out["M12"] = 2.0 * float(np.sum(w * H * extra))          # utron 2's coil lies wholly inside the half model
    return out


def case(c):
    """one solve (a worker): c holds the frame, angle, mesh, mu, conventions."""
    t0 = time.time()
    sp_ = c["spec"]
    try:
        if c["kind"] == "cart":
            kw = {k: c[k] for k in ("mode", "two_d", "L", "zfar", "ywall", "far_z", "far_x", "xmax", "far_y", "iron")
                  if k in c}
            G, mu, tau, sym, L = build_cart(sp_, c["theta"], c["h"], c.get("mu_r", MU_REC), **kw)
            r = solve_case(G, mu, tau, sym, L, record_conv=c.get("record_conv", False))
            if c.get("two_d"):
                per_len = r["L"] / (G.x[2][-1] - G.x[2][0])
                r.update(L=per_len * sp_["L"] * MM, L_per_m=per_len)
        elif c["kind"] == "cyl":
            kw = {k: c[k] for k in ("sector", "L", "zfar", "r_max", "excite", "far_t", "far_z") if k in c}
            G, mu, tau, sym, L, extra = build_cyl(sp_, c["theta"], c["h"], c.get("mu_r", MU_REC), **kw)
            r = solve_case(G, mu, tau, sym, L, extra=extra)
        elif c["kind"] == "neumann":
            r = dict(L=neumann(sp_, c["a"]))
        elif c["kind"] == "fd2d":
            D = P2D.Design(**c["design"])
            r = dict(L=P2D.solve(D, c["theta"], hx=c.get("hx", 0.5), fine=c.get("fine"))["L2d"])
        elif c["kind"] == "sol":
            r = solenoid(sp_, c["h"])
        else:
            raise ValueError(c["kind"])
    except Exception as e:                                       # report, do not hide
        r = dict(error=repr(e))
    r["s"] = time.time() - t0
    r["name"] = c["name"]
    return r


# ================================================================================================= independent checks
def neumann(sp_, a):
    """the winding alone in free space by the Neumann integral L = mu0 / 4 pi int int J.J' / R dV dV' [OC]: uniform
    along v (width D = 2 cv), the v and v' integrals in closed form F(rho) = 2 (D asinh(D / rho) - sqrt(D^2 + rho^2)
    + rho); the (u, w) section in pixels of side a (coverage sub-sampled 4 x 4), the midpoint rule between pixels and
    each pixel's geometric mean distance 0.44705 a with itself [OC: Maxwell's GMD]."""
    c = coil(sp_)
    u = np.arange(sp_["u_m0"] + a / 2, sp_["u_p1"], a)
    w = np.arange(-sp_["over"] + a / 2, sp_["L"] + sp_["over"], a)
    U, W = (v.ravel() for v in np.meshgrid(u, w, indexing="ij"))

    def off(uu, ww):
        nu, nw = np.clip(uu, c["u0"], c["u1"]), np.clip(ww, c["z0"], c["z1"])
        return uu - nu, ww - nw
    cov = np.zeros(U.size)
    sub = (np.arange(4) + 0.5) / 4 - 0.5
    for du in sub:
        for dw in sub:
            ou, ow = off(U + du * a, W + dw * a)
            rho = np.hypot(ou, ow)
            cov += (rho >= c["Ri"]) & (rho <= c["Ro"])
    keep = cov > 0
    U, W, A = U[keep], W[keep], cov[keep] / 16 * a * a
    ou, ow = off(U, W)
    n = np.hypot(ou, ow)
    ju, jw = -ow / n, ou / n                                     # the turns circulate in the (u, w) plane
    D = 2 * c["cv"]
    J = 1.0 / (D * sp_["h_c"])
    tot = 0.0
    for i0 in range(0, U.size, 2000):
        i1 = min(U.size, i0 + 2000)
        rho = np.hypot(U[i0:i1, None] - U[None, :], W[i0:i1, None] - W[None, :])
        rho = np.where(rho < 1e-9, 0.44705 * a, rho)
        F = 2.0 * (D * np.arcsinh(D / rho) - np.sqrt(D * D + rho * rho) + rho)
        tot += np.sum((ju[i0:i1, None] * ju[None, :] + jw[i0:i1, None] * jw[None, :]) * A[i0:i1, None] * A[None, :] * F)
    return MU0 / (4 * math.pi) * J * J * tot * MM


def solenoid(sp_, h):
    """the long solenoid [OC]: the winding's section, uniform along x (periodic), no iron: B = mu0 n I inside the hole,
    falling through the build, zero outside; L' = mu0 n^2 int g^2 dA. Returns the FV value per metre, the discrete
    closed form (the same g at the nodes) and the continuous integral."""
    m = mesh_par(h)
    rg = sp_["r_g"]
    ybr = [(sp_[k] - rg, h) for k in ("u_m0", "u_m1", "u_y0", "u_y1", "u_p0", "u_p1")]
    zbr = [(v, h) for v in (-sp_["over"], -sp_["clr"], 0.0, sp_["L"], sp_["L"] + sp_["clr"], sp_["L"] + sp_["over"])]
    y = graded(ybr, sp_["u_m0"] - rg - 40.0, 40.0, 4 * h, m["grow"])
    z = graded(zbr, -80.0, sp_["L"] + 80.0, 4 * h, m["grow"])
    x = np.linspace(0.0, 10.0, 3)
    G = Grid([y * MM, x * MM, z * MM], [("nat", "nat"), "per", ("nat", "nat")])
    c = coil(sp_)
    n_per_m = 1.0                                                # turns per metre, 1 A
    I = G.eidx(1)
    g = gfun(G.xn[0][I[0]] / MM + rg, G.xn[2][I[2]] / MM, c)
    tau = np.zeros(G.ne)
    tau[G.eoff[1]:G.eoff[2]] = n_per_m * g * G.h[1][I[1]]
    mu = np.full(tuple(G.nc), MU0)
    dirich = np.zeros(G.N, bool); dirich[0] = True
    (H,), w, info = fv_solve(G, mu, [tau], dirich)
    Xlen = G.x[1][-1] - G.x[1][0]
    fv = float(np.sum(w * H * H)) / Xlen
    disc = float(np.sum(w * tau * tau)) / Xlen
    yq = np.linspace(y[0], y[-1], 4001); zq = np.linspace(z[0], z[-1], 6001)
    gq = gfun(0.5 * (yq[1:] + yq[:-1])[:, None] + rg, 0.5 * (zq[1:] + zq[:-1])[None, :], c)
    cont = MU0 * n_per_m ** 2 * float(np.sum(gq ** 2 * np.diff(yq)[:, None] * np.diff(zq)[None, :])) * MM * MM
    return dict(L_per_m=fv, discrete=disc, continuous=cont, nodes=G.N, cg=info["cg"])


# ================================================================================================= the deck
def _deck_one(job):
    """the pick's deck with a utron set's (prof, tau, L_max), exactly as sim/ah_steady_cusp.run runs it (its own
    sim/rotor_parts_duty._kw, with the three utron inputs replaced); C_byp in mF. 'zlin': the screen's linear gain
    (sim/pole_design._z_at at 1200 rpm)."""
    name, var, cmf = job
    if cmf == "zlin":
        q = PD._z_at((dict(prof=var["prof"], tau=var["tau"], cyc_per_rev=6), 1200.0))
        return dict(name=name, kind="zlin", z_lin=q["z"])
    base = RP._kw
    if var.get("replace"):
        def kw_override(tf, _v=var):
            kw = base(tf)
            kw.update(prof=_v["prof"], tau=_v["tau"], L_max=_v["L_max"], seed=RP.SEED_FRAC * kw["psi_s"] / _v["L_max"])
            if _v.get("la_ratio") is not None:
                kw["la_ratio"] = _v["la_ratio"]
            return kw
        RP._kw = kw_override
    try:
        r = ACS.run(cmf)
    finally:
        RP._kw = base
    r.update(name=name, kind="deck")
    return r


# ================================================================================================= main
def jobs_for(rec):
    """every solve of the study (names are the cache keys)."""
    spc = rec["spec"]
    design = rec["op"]["design"]
    jobs = []

    def add(name, **kw):
        jobs.append(dict(name=name, spec=spc, **kw))
    # G-SOL, G-AIR, G-2D, G-CCORE
    for h in (2.0, 1.0, 0.5):
        add(f"sol h{h}", kind="sol", h=h)
    for a in A_NEU:
        add(f"neumann a{a}", kind="neumann", a=a)
    for h in H_AIR:
        for bc in ("nat", "dir"):
            add(f"air h{h} {bc}", kind="cart", theta=0.0, h=h, iron=False, xmax=1000.0, ywall=900.0, zfar=1100.0,
                far_x=bc, far_y=bc, far_z=bc)
    th13 = [float(t) for t in np.linspace(0.0, 30.0, 13)]
    for t in th13:
        add(f"fd2d {t}", kind="fd2d", design=design, theta=t)
    Xp = 2 * math.pi * spc["r_g"] / 3.0
    for t in (0.0, 30.0):
        for nx, fine in FD_REFINE:
            add(f"fd2d {t} nx{nx}", kind="fd2d", design=design, theta=t, hx=Xp / nx, fine=fine)
        for h in H_2D_FINE:
            add(f"alt2d h{h} t{t}", kind="cart", theta=t, h=h, two_d=True, far_x="nat")
    sc = dict(kind="S", g=1.0, w_p=20.0, s=30.0, d=50.0, L_stk=100.0)            # sim/pole_fd2d._selfcheck
    add("ccore fd2d", kind="fd2d", design=sc, theta=0.0)
    sc_spec = dict(spc, g=1.0, w_p=20.0, s=30.0, d=50.0, b=20.0, W_u=70.0, l_b=70.0, t_b=20.0, cv=14.0)
    sc_spec.update(u_y1=sc_spec["r_g"] - 50.0, u_y0=sc_spec["r_g"] - 70.0, u_p0=sc_spec["r_g"] - 49.0,
                   u_p1=sc_spec["r_g"] - 2.0, h_c=47.0, over=48.0)
    sc_spec.update(u_m1=sc_spec["u_y0"] - 1.0, u_m0=sc_spec["u_y0"] - 48.0)
    for h in (1.0, 0.5):
        jobs.append(dict(name=f"ccore 2d h{h}", spec=sc_spec, kind="cart", theta=0.0, h=h, two_d=True, far_x="nat"))
    # G-MESH: the record's frame, alternating (the record's convention), 2-D and 3-D
    for h in H_MESH:
        for t in (0.0, 30.0):
            add(f"alt2d h{h} t{t}", kind="cart", theta=t, h=h, two_d=True, far_x="nat")
            add(f"alt3d h{h} t{t}", kind="cart", theta=t, h=h, far_x="nat")
    for t in (0.0, 30.0):
        add(f"rec2d t{t}", kind="cart", theta=t, h=H_AUX, two_d=True, record_conv=True)
        add(f"rec3d t{t}", kind="cart", theta=t, h=H_AUX, record_conv=True)
        add(f"free2d t{t}", kind="cart", theta=t, h=H_AUX, two_d=True)
        add(f"free3d t{t}", kind="cart", theta=t, h=H_AUX)
        for mu in MU_SET:
            add(f"alt2d mu{mu:g} t{t}", kind="cart", theta=t, h=H_AUX, two_d=True, far_x="nat", mu_r=mu)
            add(f"alt3d mu{mu:g} t{t}", kind="cart", theta=t, h=H_AUX, far_x="nat", mu_r=mu)
        add(f"alt3d zdir t{t}", kind="cart", theta=t, h=H_AUX, far_x="nat", far_z="dir")
        add(f"alt2d wall t{t}", kind="cart", theta=t, h=H_AUX, two_d=True, far_x="nat", ywall=40.0)
        add(f"alt3d wall t{t}", kind="cart", theta=t, h=H_AUX, far_x="nat", ywall=40.0)
        for Ls in L_LONG:
            add(f"alt3d L{Ls:g} t{t}", kind="cart", theta=t, h=H_AUX, far_x="nat", L=Ls)
        for h in (H_AUX, H_CYL):
            add(f"cyl free h{h} t{t}", kind="cyl", theta=t, h=h)
            add(f"cyl alt h{h} t{t}", kind="cyl", theta=t, h=h, far_t="nat")
        add(f"cyl one t{t}", kind="cyl", theta=t, h=H_AUX, sector="half", excite=(1, 0, 0))
    for t in THETA_MID:
        add(f"alt2d mid t{t}", kind="cart", theta=t, h=H_AUX, two_d=True, mode="half", far_x="nat")
        add(f"alt3d mid t{t}", kind="cart", theta=t, h=H_AUX, mode="half", far_x="nat")
    for t in (0.0, 30.0):                                        # the 'half' frame at the end angles (consistency)
        add(f"alt2d mid t{t}", kind="cart", theta=t, h=H_AUX, two_d=True, mode="half", far_x="nat")
        add(f"alt3d mid t{t}", kind="cart", theta=t, h=H_AUX, mode="half", far_x="nat")
    return jobs


def main():
    T0 = time.time()
    rec = record()
    jobs = jobs_for(rec)
    th13 = [float(t) for t in np.linspace(0.0, 30.0, 13)]

    def cost(j):
        if j["kind"] not in ("cart", "cyl"):
            return 0.5
        c = (2.0 / j["h"]) ** 3 * (3.0 if j.get("sector") == "half" else 1.0) * (2.0 if j.get("mode") == "half" else 1.0)
        c *= (j.get("L", 100.0) / 100.0) ** 0.3 * (0.01 if j.get("two_d") else 1.0) * (2.0 if j.get("record_conv") else 1.0)
        return c
    order = sorted(jobs, key=lambda j: -cost(j))                 # the biggest first
    print(f"utron_3d: {len(order)} solves on {NPROC} processes", flush=True)
    cache = os.environ.get("UTRON3D_CACHE")                      # testing only: keep / reuse the solves
    R = json.load(open(cache)) if cache and os.path.exists(cache) else {}
    todo = [j for j in order if j["name"] not in R or "error" in R[j["name"]]]
    with Pool(NPROC) as pool:
        for r in pool.imap_unordered(case, todo):
            R[r["name"]] = r
            msg = r.get("error") or f"L {r.get('L', r.get('L_per_m', 0)) * 1e6:.5f} uH"
            print(f"  {r['name']:28s} {msg} ({r['s']:.0f} s)", flush=True)
            if cache:
                json.dump(R, open(cache, "w"), default=float)
    bad = [k for k, v in R.items() if "error" in v]
    if bad:
        raise SystemExit(f"failed: {bad}")
    out = analyse(rec, R, th13)
    out["deck"] = decks(rec, out)
    finish(rec, out)
    out["run_time_s"] = time.time() - T0
    json.dump(out, open(os.path.join(OUT_DIR or HERE, "utron_3d_results.json"), "w"), indent=1, default=float)
    figure(out)
    print(f"done in {out['run_time_s'] / 60:.1f} min", flush=True)


def analyse(rec, R, th13):
    spc, row = rec["spec"], rec["row"]
    uH = 1e6
    out = dict(pick=RP.PICK, inputs=dict(
        spec=spc, N_u=rec["best"]["N_u"], psi_s=rec["best"]["psi_s"], R_per_n2=row["R_per_n2"], mu_r_record=MU_REC,
        K_END_A=P2D.K_END_A, K_END_U=P2D.K_END_U, record_L_al=row["L_al"], record_L_un=row["L_un"],
        record_kappa=row["kappa"], record_L2d_ratio=row["L2d_ratio"], record_tau=row["tau"], record_prof=row["prof"],
        record_z_lin=row["z_rpm"]["1200"], sources=dict(
            pick="sim/pole_design_variants_op.json", row="sim/pole_design_variants.json",
            dimensions="sim/utron_profile.spec", section="sim/pole_fd2d.Design", deck="sim/rotor_parts_duty._kw",
            bypass="sim/ah_steady_cusp.run")))
    g = {}
    # ---- G-SOL
    g["G-SOL"] = [dict(h=h, L_per_m=R[f"sol h{h}"]["L_per_m"], discrete=R[f"sol h{h}"]["discrete"],
                       continuous=R[f"sol h{h}"]["continuous"],
                       err_discrete=R[f"sol h{h}"]["L_per_m"] / R[f"sol h{h}"]["discrete"] - 1,
                       err_continuous=R[f"sol h{h}"]["L_per_m"] / R[f"sol h{h}"]["continuous"] - 1) for h in (2.0, 1.0, 0.5)]
    # ---- G-AIR
    neu = {a: R[f"neumann a{a}"]["L"] for a in A_NEU}
    air = {(h, bc): R[f"air h{h} {bc}"]["L"] for h in H_AIR for bc in ("nat", "dir")}
    Ln, ha = neu[A_NEU[-1]], H_AIR[-1]
    fv_mid = 0.5 * (air[(ha, "nat")] + air[(ha, "dir")])
    g["G-AIR"] = dict(neumann_uH={str(a): v * uH for a, v in neu.items()},
                      fv_uH={f"h{h} {bc}": v * uH for (h, bc), v in air.items()},
                      fv_bracket_finest_uH=[air[(ha, "nat")] * uH, air[(ha, "dir")] * uH], err=fv_mid / Ln - 1,
                      inside=bool(air[(ha, "nat")] <= Ln * 1.005 and Ln <= air[(ha, "dir")] * 1.005))
    # ---- G-2D: the record's section, bracketed
    fd = {t: R[f"fd2d {t}"]["L"] for t in th13}
    fdr = {(t, nx): R[f"fd2d {t} nx{nx}"]["L"] for t in (0.0, 30.0) for nx, _ in FD_REFINE}
    a2 = {(h, t): R[f"alt2d h{h} t{t}"]["L"] for h in H_MESH + H_2D_FINE for t in (0.0, 30.0)}
    rec2 = {t: R[f"rec2d t{t}"]["L"] for t in (0.0, 30.0)}
    g["G-2D"] = dict(
        pole_fd2d_uH={t: fd[t] * uH for t in (0.0, 30.0)},
        pole_fd2d_refined_uH={f"{t} nx{nx}": v * uH for (t, nx), v in fdr.items()},
        scalar_alt_uH={f"{t} h{h}": a2[(h, t)] * uH for h in H_MESH + H_2D_FINE for t in (0.0, 30.0)},
        scalar_record_conv_uH={t: rec2[t] * uH for t in (0.0, 30.0)},
        alt_over_record_conv={t: R[f"alt2d h{H_AUX} t{t}"]["L"] / rec2[t] for t in (0.0, 30.0)},
        bracket={t: [fdr[(t, FD_REFINE[-1][0])] * uH, a2[(H_2D_FINE[-1], t)] * uH] for t in (0.0, 30.0)},
        err_vs_pole_fd2d={t: a2[(H_MESH[-1], t)] / fd[t] - 1 for t in (0.0, 30.0)},
        record_rows_reproduced=float(max(abs(fd[t] * (1 + P2D.K_END_A + (P2D.K_END_U - P2D.K_END_A) *
                                                     (1 - (fd[t] - fd[30.0]) / (fd[0.0] - fd[30.0])))
                                             / row["L_per_n2"][k] - 1) for k, t in enumerate(th13))))
    # ---- G-CCORE: the record's self-check geometry against mu0 w_p L_stk / (2 g)
    an = MU0 * 20e-3 * 0.1 / (2 * 1e-3)
    g["G-CCORE"] = dict(analytic_uH=an * uH, pole_fd2d_ratio=R["ccore fd2d"]["L"] / an,
                        scalar_ratio={f"h{h}": R[f"ccore 2d h{h}"]["L"] / an for h in (1.0, 0.5)})
    # ---- G-MESH
    a3 = {(h, t): R[f"alt3d h{h} t{t}"] for h in H_MESH for t in (0.0, 30.0)}
    mesh = []
    for h in H_MESH:
        La, Lu = a3[(h, 0.0)]["L"], a3[(h, 30.0)]["L"]
        mesh.append(dict(h=h, nodes=[a3[(h, t)]["info"]["nodes"] for t in (0.0, 30.0)], L_al_uH=La * uH, L_un_uH=Lu * uH,
                         kappa=La / Lu, k_al=La / a2[(h, 0.0)], k_un=Lu / a2[(h, 30.0)]))
    g["G-MESH"] = mesh
    # ---- G-LONG: the slope of L over the stack length against the 2-D per-length L
    longr = {}
    for t in (0.0, 30.0):
        Ls = [spc["L"]] + list(L_LONG)
        Lv = [R[f"alt3d h{H_AUX} t{t}"]["L"]] + [R[f"alt3d L{x:g} t{t}"]["L"] for x in L_LONG]
        slope = (Lv[2] - Lv[1]) / ((Ls[2] - Ls[1]) * MM)
        per2d = R[f"alt2d h{H_AUX} t{t}"]["L_per_m"]
        longr[t] = dict(stacks_mm=Ls, L_uH=[v * uH for v in Lv], slope_uH_per_m=slope * uH, two_d_per_m_uH=per2d * uH,
                        err=slope / per2d - 1, intercept_uH=(Lv[2] - slope * Ls[2] * MM) * uH,
                        pole_fd2d_per_m_uH=fd[t] / (spc["L"] * MM) * uH, err_vs_pole_fd2d=slope / (fd[t] / (spc["L"] * MM)) - 1)
    g["G-LONG"] = longr
    out["gates"] = g
    # ---- the 3-D result in the record's frame (the alternating set = the record's convention), finest mesh
    hp = H_MESH[-1]
    res = {}
    for t, tag in ((0.0, "al"), (30.0, "un")):
        r3, L2 = a3[(hp, t)], a2[(hp, t)]
        res[tag] = dict(L3d=r3["L"], L2d=L2, k=r3["L"] / L2, lam_stack=r3["lam_stack"], lam_end=r3["lam_end"],
                        fringe_share=(r3["lam_stack"] - L2) / r3["L"], end_share=r3["lam_end"] / r3["L"],
                        section_share=L2 / r3["L"], K_3d=r3["L"] / L2 - 1)
    out["frame_a"] = res
    # ---- sensitivity, at H_AUX, as ratios to the same-mesh reference
    ref = {t: R[f"alt3d h{H_AUX} t{t}"]["L"] for t in (0.0, 30.0)}
    sens = {}
    for t in (0.0, 30.0):
        s = {}
        for mu in MU_SET:
            s[f"mu{mu:g}_3d"] = R[f"alt3d mu{mu:g} t{t}"]["L"] / ref[t]
            s[f"mu{mu:g}_2d"] = R[f"alt2d mu{mu:g} t{t}"]["L"] / R[f"alt2d h{H_AUX} t{t}"]["L"]
        s["far_z_dir"] = R[f"alt3d zdir t{t}"]["L"] / ref[t]
        s["walls_plus40_3d"] = R[f"alt3d wall t{t}"]["L"] / ref[t]
        s["walls_plus40_2d"] = R[f"alt2d wall t{t}"]["L"] / R[f"alt2d h{H_AUX} t{t}"]["L"]
        s["record_conv_3d"] = R[f"rec3d t{t}"]["L"] / ref[t]
        s["free_3d"] = R[f"free3d t{t}"]["L"] / ref[t]
        s["free_2d"] = R[f"free2d t{t}"]["L"] / R[f"alt2d h{H_AUX} t{t}"]["L"]
        s["half_frame_3d"] = R[f"alt3d mid t{t}"]["L"] / ref[t]
        sens[t] = s
    out["sensitivity"] = sens
    # ---- the cylinder
    cyl = {}
    for t in (0.0, 30.0):
        cf = {h: R[f"cyl free h{h} t{t}"]["L"] for h in (H_AUX, H_CYL)}
        ca = {h: R[f"cyl alt h{h} t{t}"]["L"] for h in (H_AUX, H_CYL)}
        one = R[f"cyl one t{t}"]
        a_, b_ = one["L"], one["M12"]
        cyl[t] = dict(free_uH={str(h): v * uH for h, v in cf.items()}, alt_uH={str(h): v * uH for h, v in ca.items()},
                      free_over_alt={str(h): cf[h] / ca[h] for h in cf}, alt_over_frame_a={str(h): ca[h] / (
                          R[f"alt3d h{h} t{t}"]["L"]) for h in cf},
                      self_uH=a_ * uH, mutual_uH=b_ * uH, aiding_uH=(a_ + 2 * b_) * uH, one_reversed_uH=(a_ - 2 * b_ / 3) * uH,
                      aiding_check=(a_ + 2 * b_) / cf[H_AUX] - 1, n_hot_iron=R[f"cyl free h{H_AUX} t{t}"]["n_hot_iron"])
    out["cylinder"] = cyl
    # ---- the profile: the 3-D / 2-D ratio at the computed angles, on the record's 13-angle grid
    kmid = {t: R[f"alt3d mid t{t}"]["L"] / R[f"alt2d mid t{t}"]["L"] for t in list(THETA_MID) + [0.0, 30.0]}
    out["k_theta"] = {str(t): kmid[t] for t in sorted(kmid)}
    out["L2d_record_13"] = [fd[t] for t in th13]
    return out


def variant(name, L13, th13, rec, note):
    """a utron set from L(theta) on the record's grid: L_al, L_un, kappa, L_max, prof (sim/pole_design.fit_cos), tau."""
    row, N_u = rec["row"], rec["best"]["N_u"]
    prof, err = PD.fit_cos(th13, L13, 60.0)
    return dict(name=name, note=note, L13=list(L13), L_al=L13[0], L_un=L13[-1], kappa=L13[0] / L13[-1],
                L_max=3 * N_u ** 2 * L13[0], prof=prof, fit_err=err, tau=L13[0] / row["R_per_n2"], replace=True)


def finish(rec, out):
    """nothing heavy: the summary numbers the findings quote."""
    v = out["variants"]
    r0 = v["record"]
    out["summary"] = {k: dict(L_al_uH=x["L_al"] * 1e6, L_un_uH=x["L_un"] * 1e6, kappa=x["kappa"], L_max_H=x["L_max"],
                              L_max_vs_record=x["L_max"] / r0["L_max"] - 1, kappa_vs_record=x["kappa"] / r0["kappa"] - 1,
                              tau_s=x["tau"]) for k, x in v.items()}


def decks(rec, out):
    """the variants' L(theta) and the deck runs (ngspice)."""
    th13 = [float(t) for t in np.linspace(0.0, 30.0, 13)]
    fd = np.array(out["L2d_record_13"])
    row = rec["row"]
    kt = {float(k): v for k, v in out["k_theta"].items()}
    tk = np.array(sorted(kt)); kk = np.array([kt[t] for t in tk])
    k13 = np.interp(th13, tk, kk)                               # [IR] piecewise linear in theta between the solves
    L_e = fd * k13
    # scale to the finest mesh's end values (the ratios k at 0 and 30 deg from H_MESH[-1]) [IR]
    fa = out["frame_a"]
    sc = np.interp(th13, [0.0, 30.0], [fa["al"]["k"] / kt[0.0], fa["un"]["k"] / kt[30.0]])
    L_e = L_e * sc
    s13 = (fd - fd[-1]) / (fd[0] - fd[-1])                       # the normalised 2-D swing, 1 aligned .. 0 unaligned

    def by_s(r_al, r_un):
        return r_un + (r_al - r_un) * s13                        # [IR] a factor interpolated in the 2-D swing
    cyl = out["cylinder"]
    f_aid = by_s(cyl[0.0]["free_over_alt"][str(H_CYL)] * cyl[0.0]["alt_over_frame_a"][str(H_CYL)],
                 cyl[30.0]["free_over_alt"][str(H_CYL)] * cyl[30.0]["alt_over_frame_a"][str(H_CYL)])
    f_rev = by_s(cyl[0.0]["one_reversed_uH"] / cyl[0.0]["aiding_uH"] * cyl[0.0]["free_over_alt"][str(H_CYL)] *
                 cyl[0.0]["alt_over_frame_a"][str(H_CYL)],
                 cyl[30.0]["one_reversed_uH"] / cyl[30.0]["aiding_uH"] * cyl[30.0]["free_over_alt"][str(H_CYL)] *
                 cyl[30.0]["alt_over_frame_a"][str(H_CYL)])
    rec_var = dict(name="record", note="sim/pole_design_variants.json row: 2-D x (1 + K_END)", L13=row["L_per_n2"],
                   L_al=row["L_al"], L_un=row["L_un"], kappa=row["kappa"], L_max=3 * rec["best"]["N_u"] ** 2 * row["L_al"],
                   prof=row["prof"], fit_err=row["fit_err"], tau=row["tau"], replace=False)
    V = dict(record=rec_var,
             frame_a=variant("3-D, record's frame", L_e, th13, rec,
                             "the record's section in 3-D, alternating set (no net circumferential MMF)"),
             cyl_aiding=variant("3-D, cylinder, coils aiding", L_e * f_aid, th13, rec,
                                "the machine's cylinder, three identical coils in series (aiding round the axis)"),
             cyl_one_reversed=variant("3-D, cylinder, one coil reversed", L_e * f_rev, th13, rec,
                                      "the cylinder, one of the three coils connected the other way"))
    out["variants"] = V
    jobs = []
    for k, v in V.items():
        jobs.append((k, v, "zlin"))
        for c in C_BYP:
            jobs.append((k, v, c))
    # La / Lb held at the record's 0.146 H (la_ratio rescaled): a sensitivity on the best estimate
    held = dict(V["cyl_aiding"], la_ratio=RP.LA_RATIO * V["record"]["L_max"] / V["cyl_aiding"]["L_max"])
    for c in C_BYP:
        jobs.append(("cyl_aiding_La_held", held, c))
    with Pool(NPROC) as pool:
        rs = pool.map(_deck_one, jobs, chunksize=1)
    D = {}
    for (k, v, c), r in zip(jobs, rs):
        d = D.setdefault(k, {})
        if c == "zlin":
            d["z_lin"] = r["z_lin"]
        else:
            d[f"{c:g}mF"] = {q: r.get(q) for q in ("z_early", "P_belt_W", "P_cu_utron_W", "P_cu_fixed_W", "P_AH_W",
                                                     "branch_AT_min", "branch_AT_max", "top", "bottom", "dAT_max")}
    return D


# ================================================================================================= the figure
def figure(out):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import matplotlib.ticker  # noqa: F401
    INK, INK2, MUTED, GRID, BASE, SURF = "#0b0b0b", "#52514e", "#898781", "#e1e0d9", "#c3c2b7", "#fcfcfb"
    S1, S2, S3, S4 = "#2a78d6", "#eb6834", "#1baf7a", "#eda100"
    plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 9, "axes.edgecolor": BASE, "axes.labelcolor": INK2,
                         "xtick.color": MUTED, "ytick.color": MUTED, "axes.facecolor": SURF, "figure.facecolor": SURF})
    th13 = np.linspace(0.0, 30.0, 13)
    V = out["variants"]
    fig, ax = plt.subplots(1, 3, figsize=(15.5, 4.9), gridspec_kw=dict(width_ratios=[1.25, 1.0, 1.0]))
    a = ax[0]
    for key, col in (("record", MUTED), ("frame_a", S1), ("cyl_aiding", S2), ("cyl_one_reversed", S3)):
        v = V[key]
        lab = "record: 2-D x (1 + K_END)" if key == "record" else v["name"]
        a.plot(th13, np.array(v["L13"]) * 1e6, color=col, lw=2.0, solid_capstyle="round",
               label=f"{lab}, \u03ba {v['kappa']:.2f}")
        a.plot([0, 30], [v["L_al"] * 1e6, v["L_un"] * 1e6], "o", ms=6, color=col, mec=SURF, mew=2)
    a.set_yscale("log")
    a.set_yticks([0.2, 0.3, 0.5, 1.0, 2.0], ["0.2", "0.3", "0.5", "1", "2"])
    a.yaxis.set_minor_formatter(matplotlib.ticker.NullFormatter())
    a.set_xlim(-1, 31)
    a.set_xticks([0, 5, 10, 15, 20, 25, 30])
    a.set_xlabel("rotor angle from alignment \u03b8 (deg)")
    a.set_ylabel("L / N\u00b2 per utron (\u00b5H, log scale)")
    a.grid(True, color=GRID, lw=0.8)
    a.set_axisbelow(True)
    for s_ in ("top", "right"):
        a.spines[s_].set_visible(False)
    a.legend(loc="upper right", fontsize=7.6, frameon=False, labelcolor=INK2)
    a.set_title("(a) L(\u03b8) over the half cycle: the record against 3-D", loc="left", fontsize=10, color=INK)
    # (b) the 3-D L in the record's frame: the 2-D section, the stack-end fringing, the end turns (shares)
    b = ax[1]
    fa, cyl = out["frame_a"], out["cylinder"]
    for i, (tag, t) in enumerate((("al", 0.0), ("un", 30.0))):
        x = fa[tag]
        parts = [x["L2d"], x["lam_stack"] - x["L2d"], x["lam_end"]]
        tot = sum(parts)
        left = 0.0
        for p, col, lab in zip(parts, (S1, S2, S3), ("2-D section (x stack)", "stack-end fringing", "end turns")):
            frac = p / tot
            b.barh(i, max(frac - 0.004, 0.0), left=left, height=0.3, color=col, label=lab if i == 0 else None)
            if frac > 0.12:
                b.text(left + frac / 2, i, f"{100 * frac:.0f} %", ha="center", va="center", fontsize=8,
                       color="white" if col in (S1, S2) else INK)
            left += frac
        aid = cyl[t]["free_over_alt"][str(H_CYL)] * cyl[t]["alt_over_frame_a"][str(H_CYL)] - 1
        b.text(1.03, i - 0.07, f"{tot * 1e6:.3f} \u00b5H", va="center", fontsize=8.5, color=INK)
        b.text(1.03, i + 0.12, f"cylinder, coils aiding: {100 * aid:+.0f} %", va="center", fontsize=7.6, color=INK2)
    b.set_yticks([0, 1], ["aligned", "unaligned"])
    b.set_xlim(0, 1.45)
    b.set_xticks([0, 0.25, 0.5, 0.75, 1.0], ["0", "25", "50", "75", "100 %"])
    b.invert_yaxis()
    for s_ in ("top", "right", "left"):
        b.spines[s_].set_visible(False)
    b.tick_params(axis="y", length=0, colors=INK2)
    b.legend(loc="lower center", bbox_to_anchor=(0.36, -0.36), ncol=3, fontsize=7.6, frameon=False, labelcolor=INK2)
    b.set_title("(b) the 3-D L / N\u00b2 in the record's frame, by where it is linked", loc="left", fontsize=10, color=INK)
    # (c) the pump: z_early without / with the 22 mF bypass
    c = ax[2]
    D = out["deck"]
    keys = [("record", MUTED), ("frame_a", S1), ("cyl_aiding", S2), ("cyl_one_reversed", S3)]
    for j, (k, col) in enumerate(keys):
        z0 = D[k]["0mF"]["z_early"]; z22 = D[k]["22mF"]["z_early"]
        c.plot([z0, z22], [j, j], color=GRID, lw=2.0, zorder=1)
        c.plot([z0], [j], "o", ms=7, color=col, mec=SURF, mew=2, zorder=3)
        c.plot([z22], [j], "s", ms=7, color=col, mec=SURF, mew=2, zorder=3)
        c.text(max(z0, z22) + 0.004, j, f"{z0:.3f} / {z22:.3f}", va="center", fontsize=8, color=INK2)
    c.axvline(1.0, color=BASE, lw=1.0)
    c.set_yticks(range(len(keys)), ["record", "3-D, record's frame", "3-D, cylinder,\ncoils aiding",
                                    "3-D, cylinder,\none coil reversed"])
    c.invert_yaxis()
    zs = [D[k][q]["z_early"] for k, _ in keys for q in ("0mF", "22mF")]
    c.set_xlim(min(zs + [1.0]) - 0.01, max(zs) + 0.05)
    c.set_xlabel("z_early per cycle, the loaded deck (● no bypass, ■ 22 mF)")
    c.grid(True, axis="x", color=GRID, lw=0.8)
    c.set_axisbelow(True)
    for s_ in ("top", "right", "left"):
        c.spines[s_].set_visible(False)
    c.tick_params(axis="y", length=0, colors=INK2)
    c.set_title("(c) the pump's gain with each utron set", loc="left", fontsize=10, color=INK)
    fig.suptitle("The pick's utron in 3-D (sim/utron_3d.py): kappa, where the flux goes, and the pump", x=0.01, ha="left",
                 fontsize=11, color=INK)
    fig.tight_layout(rect=(0, 0.02, 1, 0.95))
    path = os.path.join(OUT_DIR, "utron-3d.png") if OUT_DIR else os.path.join(ROOT, "docs", "figures", "utron-3d.png")
    fig.savefig(path, dpi=150)
    plt.close(fig)
    out["figure"] = "docs/figures/utron-3d.png"


if __name__ == "__main__":
    main()
