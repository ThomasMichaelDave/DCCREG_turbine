"""sim/neck_nonlinear.py -- the neck's nonlinear field check: the pick's wound utron against its bridge in 2-D (the plane
of rotation, scaled by the stack length) with the back iron as built (the 3.0 mm 80 % NiFe strip under a 12 mm G10
air break, the two lap joints onto it, the stud holes) and datasheet-class B-H curves; then the saturation law that
this map gives, fed into the pick's deck. Writes sim/neck_nonlinear_results.json and docs/figures/neck-nonlinear.png.

The field model:
- geometry: sim/pole_fd2d.py's section of the pick (sim/pole_design_variants_op.json), unrolled at r_g, periodic over
  120 deg (one utron, two bridges), A = 0 40 mm beyond the iron [IR: as pole_fd2d]; the built back iron from
  sim/utron_profile.spec (strip u 86-89, half-cores from u 89, the break |v| < 6, studs) [OC: the drawn utron];
- A_z on a tensor mesh with a line at every material edge, pole_fd2d's 5-point finite-volume operator (cell-wise
  reluctivity), written as the minimiser of the magnetic energy and solved by Newton with a backtracking line search on
  it [OC]; the linked flux per turn is L_stk f.A / NI (= pole_fd2d's L_stk (<A>+ - <A>-)) [OC];
- materials [IR]: M235-35A isotropic in the plane, B = SF B_iron (stacking factor SF_SIFE); the neck strip as a
  homogenised stack of 0.1 mm NiFe foils lying in the v-w plane (stacked radially, as utron_profile rounds its
  thickness to whole foils): along the foils B = SF B_iron, across them H = SF H_iron + (1 - SF) B / mu0 [OC: the
  laminate's parallel / series limits]; a contact gap G_J at each lap joint [RH]; air, G10, copper and the A4 studs
  at mu0 [OC].
The deck: sim/rotor_parts_duty._kw (the pick as sim/pole_design.size_op runs it), sim/magnetic_doubler.deck, and the
22 mF bypass inserted as sim/ah_steady_cusp.run does; the utron groups' law replaced (text substitution, the files are
not edited) by the FE's: i = Psi / L(theta) + i_neck(Psi), the neck in series with the rest of the path [IR, checked
against the FE map along the deck's own trajectory].
Usage: python3 sim/neck_nonlinear.py [D | Dstart]   (D: case D, Dstart: its start runs, both on the written
results; NECK_PROCS worker processes, default 2; about 30 minutes with 2 on an idle machine)
"""
import json
import math
import os
import subprocess
import sys
import tempfile
import time
from multiprocessing import Pool

import numpy as np
import scipy.sparse as sps
import scipy.sparse.linalg as spla
from scipy.interpolate import PchipInterpolator
from scipy.optimize import brentq

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
import pole_fd2d as P              # noqa: E402
import pole_design as PD           # noqa: E402
import utron_profile as U          # noqa: E402
import magnetic_doubler as M       # noqa: E402
import rotor_parts_duty as RP      # noqa: E402
import ah_steady_cusp as S         # noqa: E402

MU0 = 4e-7 * math.pi
NU0 = 1.0 / MU0
OUT_JSON = os.path.join(HERE, "neck_nonlinear_results.json")
OUT_FIG = os.path.join(ROOT, "docs", "figures", "neck-nonlinear.png")

# ------------------------------------------------------------------------------------------------ materials [IR]
# M235-35A: typical 50 Hz normal magnetisation curve of a fully processed 0.35 mm non-oriented grade (EN 10106 class;
# mill data sheets of the class: Cogent / Surahammars, voestalpine isovac 235-35 A, thyssenkrupp powercore M 235-35 A).
# J at 2500 / 5000 / 10000 A/m: 1.54 / 1.63 / 1.73 T against the standard's minima 1.49 / 1.60 / 1.70 T; mu_r peaks at
# about 10 000 near 0.8 T; J_s 2.03 T [IR].
H_SIFE = (0, 10, 20, 30, 40, 50, 60, 70, 80, 100, 125, 150, 200, 300, 500, 1000, 2500, 5000, 10000, 20000, 50000,
          100000, 200000)
J_SIFE = (0, 0.025, 0.085, 0.22, 0.42, 0.62, 0.78, 0.90, 0.99, 1.10, 1.18, 1.24, 1.31, 1.38, 1.44, 1.49, 1.54, 1.63,
          1.73, 1.83, 1.95, 2.01, 2.03)
# 80 % NiFe-Mo, annealed (Permalloy-80 class: VAC Mumetall, Carpenter HyMu 80, ASTM A753 alloy 4), DC normal curve at
# 20 C: mu_i ~ 5e4, mu_max ~ 1e5, J 0.786 T at 100 A/m, J_s 0.80 T [IR]; the class spans J_s ~ 0.75-0.87 T.
H_NIFE = (0, 0.5, 1, 1.5, 2, 3, 4, 5, 7, 10, 15, 20, 30, 50, 100, 200, 500, 1000, 2000, 5000)
J_NIFE = (0, 0.030, 0.075, 0.14, 0.22, 0.38, 0.49, 0.56, 0.635, 0.685, 0.722, 0.740, 0.758, 0.772, 0.786, 0.793, 0.798,
          0.7995, 0.800, 0.800)
KJ_60C = 0.975            # J_s at ~60 C (the record's temperature for B_NIFE, sim/utron_profile.py) / at 20 C [RH]
SF_SIFE = 0.95            # M235-35A stack (docs/make_core_drawing.py SF: "a stacking factor >= 0.95") [IR]
SF_NIFE = 0.90            # 0.1 mm NiFe foils with their coating [RH: typical for 0.1 mm laminations]
G_J = 0.02                # mm, contact gap at each lap joint (half-core on strip; datum A flat to 0.02) [RH]
MU_KNEE = 100.0           # an iron counts as saturated where its differential mu_r falls below this [IR]
PROCS = int(os.environ.get("NECK_PROCS", "2"))   # worker processes

# ------------------------------------------------------------------------------------------------ the field solver


class Iron:
    """H(B) of an iron's own flux density: monotone PCHIP through (B = J + mu0 H, H), odd-extended; beyond the table
    B = J_s + mu0 H. W(B) = int H dB."""

    def __init__(self, H, J, kJ=1.0):
        H, J = np.asarray(H, float), np.asarray(J, float) * kJ
        B = J + MU0 * H
        self.B_tab, self.H_tab = B, H
        self.f = PchipInterpolator(np.r_[-B[:0:-1], B], np.r_[-H[:0:-1], H])
        self.df = self.f.derivative()
        self.F = self.f.antiderivative()
        self.Bm, self.Hm = float(B[-1]), float(H[-1])
        self.Wm = float(self.F(self.Bm) - self.F(0.0))
        self.nu0 = float(self.df(0.0))
        self.J_s = float(J[-1])
        # where the differential mu_r falls to MU_KNEE
        bb = np.linspace(0.05 * self.Bm, self.Bm, 20001)
        mud = 1.0 / (self.df(bb) * MU0)
        k = np.where(mud < MU_KNEE)[0]
        self.B_knee = float(bb[k[0]]) if len(k) else self.Bm

    def H(self, B):
        return np.where(B <= self.Bm, self.f(np.minimum(B, self.Bm)), self.Hm + (B - self.Bm) * NU0)

    def dH(self, B):
        return np.where(B <= self.Bm, self.df(np.minimum(B, self.Bm)), NU0)

    def W(self, B):
        e = B - self.Bm
        return np.where(B <= self.Bm, self.F(np.minimum(B, self.Bm)) - self.F(0.0), self.Wm + self.Hm * e + 0.5 * NU0 * e * e)

    def nu(self, B):
        Bf = np.maximum(B, 1e-9)
        return np.where(B > 1e-9, self.H(Bf) / Bf, self.nu0), self.dH(Bf)


SIFE = Iron(H_SIFE, J_SIFE)


def nife(kJ=KJ_60C):
    return Iron(H_NIFE, J_NIFE, kJ)


class Mesh:
    """tensor mesh, x periodic over X (mm), y nodes (mm); cell (i, j) spans x_i..x_i+1, y_j..y_j+1."""

    def __init__(self, x, X, y):
        self.x, self.X, self.y = np.asarray(x, float), float(X), np.asarray(y, float)
        nx, ny = len(self.x), len(self.y)
        self.nx, self.ny = nx, ny
        hx, hy = np.diff(np.r_[self.x, X]), np.diff(self.y)
        I, Jc = np.meshgrid(np.arange(nx), np.arange(ny - 1), indexing="ij")
        ip = (I + 1) % nx
        self.nodes = np.stack([(I * ny + Jc).ravel(), (ip * ny + Jc).ravel(), (I * ny + Jc + 1).ravel(),
                               (ip * ny + Jc + 1).ravel()], axis=1)
        self.HX = (hx[I] * 1e-3).ravel()
        self.HY = (hy[Jc] * 1e-3).ravel()
        self.area = self.HX * self.HY
        self.XC = (self.x[I] + hx[I] / 2).ravel()
        self.YC = (0.5 * (self.y[Jc] + self.y[Jc + 1])).ravel()
        self.ncell, self.nnode = nx * (ny - 1), nx * ny
        jn = np.tile(np.arange(ny), nx)
        self.free = np.where((jn > 0) & (jn < ny - 1))[0]
        # element-matrix scatter restricted to the free nodes (A = 0 on the y boundaries)
        pos = -np.ones(self.nnode, int)
        pos[self.free] = np.arange(len(self.free))
        r = np.repeat(self.nodes, 4, axis=1).ravel()
        c = np.tile(self.nodes, (1, 4)).ravel()
        keep = (pos[r] >= 0) & (pos[c] >= 0)
        self.keep, self.rk, self.ck = keep, pos[r[keep]], pos[c[keep]]

    def b(self, A):
        """the four edge components of each cell (T): B_x on the left / right edges, B_y (sign dropped) bottom / top."""
        a1, a2, a3, a4 = (A[self.nodes[:, k]] for k in range(4))
        return np.stack([(a3 - a1) / self.HY, (a4 - a2) / self.HY, (a2 - a1) / self.HX, (a4 - a3) / self.HX], axis=1)


class Problem:
    """energy W(A) = sum_cells area w(b) - f.A, w the material's energy density of the cell's mean B^2 per component
    (pole_fd2d's stencil for a linear w); materials: {id: dict(kind='lin', mu_r) | dict(kind='iso', iron, SF) |
    dict(kind='lam', iron, SF, normal='x'|'y')}; id 0 is air."""

    def __init__(self, mesh, mat, J, materials, L_stk_mm):
        self.m, self.mat, self.J, self.materials, self.L_stk = mesh, mat, J, materials, L_stk_mm
        m = mesh
        z = np.zeros(m.ncell)
        ihx, ihy = 1 / m.HX, 1 / m.HY
        self.D = np.stack([np.stack([-ihy, z, ihy, z], 1), np.stack([z, -ihy, z, ihy], 1),
                           np.stack([-ihx, ihx, z, z], 1), np.stack([z, z, -ihx, ihx], 1)], axis=1)
        self.f = np.bincount(m.nodes.ravel(), weights=np.repeat(J * m.area / 4.0, 4), minlength=m.nnode)
        self.sel = {k: np.where(mat == k)[0] for k in materials}

    def laws(self, bb):
        n = len(bb)
        ax, ay = np.full(n, 0.5 * NU0), np.full(n, 0.5 * NU0)
        gam, v = np.zeros(n), np.zeros((n, 4))
        w = 0.25 * NU0 * (bb ** 2).sum(1)
        for k, md in self.materials.items():
            s = self.sel[k]
            if not len(s):
                continue
            b = bb[s]
            if md["kind"] == "lin":
                nu = NU0 / md["mu_r"]
                ax[s] = ay[s] = 0.5 * nu
                w[s] = 0.25 * nu * (b ** 2).sum(1)
                continue
            iron, SF = md["iron"], md["SF"]
            if md["kind"] == "iso":
                Sv, air = np.full(4, 1.0 / SF), np.zeros(4)
            elif md["normal"] == "y":
                Sv, air = np.array([1 / SF, 1 / SF, 1.0, 1.0]), np.array([0.0, 0.0, 1.0, 1.0])
            else:
                Sv, air = np.array([1.0, 1.0, 1 / SF, 1 / SF]), np.array([1.0, 1.0, 0.0, 0.0])
            c = b * Sv
            c2 = (c ** 2).sum(1)
            beta = np.sqrt(0.5 * c2)                       # the iron's own |B|
            nui, nud = iron.nu(beta)
            ax[s] = 0.5 * SF * nui * Sv[0] ** 2 + 0.5 * (1 - SF) * NU0 * air[0]
            ay[s] = 0.5 * SF * nui * Sv[2] ** 2 + 0.5 * (1 - SF) * NU0 * air[2]
            gam[s] = np.where(c2 > 0, 0.5 * SF * (nud - nui) / np.maximum(c2, 1e-300), 0.0)
            v[s] = c * Sv
            w[s] = SF * iron.W(beta) + 0.25 * (1 - SF) * NU0 * ((b * air) ** 2).sum(1)
        return ax, ay, gam, v, w

    def assemble(self, A, need_K=True):
        m = self.m
        bb = m.b(A)
        ax, ay, gam, v, w = self.laws(bb)
        dg = np.stack([ax, ax, ay, ay], 1)
        rc = np.einsum("nki,nk->ni", self.D, dg * bb) * m.area[:, None]
        R = np.bincount(m.nodes.ravel(), weights=rc.ravel(), minlength=m.nnode) - self.f
        E = float((w * m.area).sum() - self.f @ A)
        if not need_K:
            return R, E, None
        Ke = np.einsum("nki,nk,nkj->nij", self.D, dg, self.D)
        dv = np.einsum("nki,nk->ni", self.D, v)
        Ke = (Ke + gam[:, None, None] * dv[:, :, None] * dv[:, None, :]) * m.area[:, None, None]
        nf = len(m.free)
        K = sps.csc_matrix((Ke.ravel()[m.keep], (m.rk, m.ck)), shape=(nf, nf))
        return R, E, K

    def solve(self, A0=None, tol=1e-8, maxit=50):
        """Newton on the energy [OC: convex for monotone H(B)]; returns A, iterations, converged."""
        m = self.m
        A = np.zeros(m.nnode) if A0 is None else A0.copy()
        fr = m.free
        for it in range(1, maxit + 1):
            R, E, K = self.assemble(A)
            lu = spla.splu(K, permc_spec="MMD_AT_PLUS_A", options=dict(SymmetricMode=True))
            self.lu = lu
            dA = np.zeros(m.nnode)
            dA[fr] = lu.solve(-R[fr])
            dec = -float(R[fr] @ dA[fr])
            t = 1.0
            if dec > 1e-11 * max(abs(E), 1e-30):
                for _ in range(30):
                    _, En, _ = self.assemble(A + t * dA, need_K=False)
                    if En <= E - 1e-4 * t * dec:
                        break
                    t *= 0.5
            A = A + t * dA
            rel = t * np.abs(dA).max() / max(np.abs(A).max(), 1e-30)
            if rel < tol and t == 1.0:
                return A, it, True
        return A, maxit, False

    def flux(self, A, NI):
        """linked flux per turn (Wb) of a coil carrying NI ampere-turns [OC]."""
        return self.L_stk * 1e-3 * float(self.f @ A) / NI


# ------------------------------------------------------------------------------------------------ the record
def record():
    """the pick (sim/rotor_parts_duty.pick: the variant row and its operating point) and its built utron."""
    r, b, f, Lmax = RP.pick()
    op = json.load(open(os.path.join(HERE, "pole_design_variants_op.json")))["designs"][RP.PICK]
    sp = U.spec(op["design"], op["best"], r)
    return dict(row=r, best=b, f=f, L_max=Lmax, design=op["design"], sp=sp, D=P.Design(**op["design"]))


REC = record()

# the variants: geometry 'fd2d' (pole_fd2d's: solid back iron) or 'built' (the strip, the break, the joints, the holes)
BASE = dict(geom="built", sife="nl", sf_sife=SF_SIFE, nife="lam", sf_nife=SF_NIFE, kJ=KJ_60C, gj=G_J, holes=True)
LINEAR = dict(geom="fd2d", sife="lin", mu_r=P.MUR_FE)


def variant(**kw):
    return dict(BASE, **kw)


def geometry(theta, var, scale=1.0):
    """mesh, material ids, coil masks and region labels of the section at rotor angle theta (deg from alignment)."""
    D, sp = REC["D"], REC["sp"]
    X = D.X
    xu = (D.r_g * math.radians(theta)) % X
    w, s2, dep, bk = D.w_p, D.s / 2, D.d, D.b
    rel = []                                            # (x0, x1, y0, y1, mat) relative to the utron centre; in order
    if var["geom"] == "fd2d":
        rel += [(s2, s2 + w, -dep, 0.0, 1), (-s2 - w, -s2, -dep, 0.0, 1), (-s2 - w, s2 + w, -dep - bk, -dep, 1)]
    else:
        ys = sp["u_n1"] - D.r_g                         # strip top (u 89)
        y0 = sp["u_y0"] - D.r_g                         # strip bottom (u 86)
        hb, gj = sp["brk"] / 2, var["gj"]
        rel += [(s2, s2 + w, -dep, 0.0, 1), (-s2 - w, -s2, -dep, 0.0, 1),
                (hb, s2 + w, ys + gj, -dep, 1), (-s2 - w, -hb, ys + gj, -dep, 1),
                (-s2 - w, s2 + w, y0, ys, 2)]
        if var["holes"]:                                # the Ø6.4 stud holes as squares of equal area [IR]
            h = math.sqrt(math.pi) * sp["stud_d"] / 4
            for (u, vv) in sp["studs"]:
                for sg in (1, -1):
                    rel.append((sg * vv - h, sg * vv + h, u - D.r_g - h, u - D.r_g + h, 0))
    rects = []
    for (a, b_, c, e, k) in rel:
        rects += [(p[0], p[1], p[2], p[3], k) for p in P._wrap((a + xu, b_ + xu, c, e), X)]
    for r in D.stator_rects():
        rects += [(p[0], p[1], p[2], p[3], 3) for p in P._wrap(r, X)]
    plus, minus, a_coil = D.coil_rects()
    cp = P._wrap((plus[0] + xu, plus[1] + xu, plus[2], plus[3]), X)
    cm = P._wrap((minus[0] + xu, minus[1] + xu, minus[2], minus[3]), X)
    allr = [q[:4] for q in rects] + cp + cm
    ylo, yhi = min(q[2] for q in allr) - 40.0, max(q[3] for q in allr) + 40.0
    y = P.grid_axis([0.0, D.g] + [q[2] for q in allr] + [q[3] for q in allr], ylo, yhi, 0.1 * scale, 2.0 * scale)
    x = P.grid_axis([q[0] for q in allr] + [q[1] for q in allr], 0.0, X, 0.2 * scale, 2.0 * scale)
    if abs(x[-1] - X) < 1e-9:
        x = x[:-1]
    m = Mesh(x, X, y)
    mat = np.zeros(m.ncell, int)
    for (a, b_, c, e, k) in rects:
        mat[(m.XC > a) & (m.XC < b_) & (m.YC > c) & (m.YC < e)] = k
    inside = lambda rs: np.any([(m.XC > a) & (m.XC < b_) & (m.YC > c) & (m.YC < e) for (a, b_, c, e) in rs], axis=0)
    cpm, cmm = inside(cp), inside(cm)
    xr = (m.XC - xu + X / 2) % X - X / 2                # tangential position from the utron centre
    reg = np.zeros(m.ncell, int)                        # 0 air, 1 strip under the break, 2 strip under the half-cores,
    reg[(mat == 2) & (np.abs(xr) < sp["brk"] / 2)] = 1  # 3 half-core back iron, 4 tip, 5 tip face (top 1 mm), 6 bridge
    reg[(mat == 2) & (np.abs(xr) >= sp["brk"] / 2)] = 2
    reg[(mat == 1) & (m.YC < -dep)] = 3
    reg[(mat == 1) & (m.YC >= -dep) & (m.YC < -1.0)] = 4
    reg[(mat == 1) & (m.YC >= -1.0)] = 5
    reg[mat == 3] = 6
    return m, mat, cpm, cmm, reg, a_coil


def materials(var):
    if var["sife"] == "lin":
        lin = dict(kind="lin", mu_r=var["mu_r"])
        return {1: lin, 2: lin, 3: lin}
    si = dict(kind="iso", iron=SIFE, SF=var["sf_sife"])
    ni_iron = nife(var["kJ"])
    ni = dict(kind="lam", iron=ni_iron, SF=var["sf_nife"], normal="y") if var["nife"] == "lam" else \
        dict(kind="iso", iron=ni_iron, SF=var["sf_nife"])
    return {1: si, 2: ni, 3: si}


REGIONS = ("strip under the break", "strip under the half-cores", "half-core back iron", "tips", "tip faces (1 mm)",
           "bridges")


def region_stats(prob, A, reg, var):
    """per region: the largest iron B (T) and the area share above the material's knee (mu_diff < MU_KNEE)."""
    m, mats = prob.m, prob.materials
    bb = m.b(A)
    out = []
    for k in range(1, 7):
        s = np.where(reg == k)[0]
        if not len(s):
            out.append((0.0, 0.0))
            continue
        md = mats[prob.mat[s[0]]]
        if md["kind"] == "lin":
            Bi = np.sqrt(0.5 * (bb[s] ** 2).sum(1))
            knee = 1e9
        else:
            Sv = np.full(4, 1 / md["SF"]) if md["kind"] == "iso" else np.array([1 / md["SF"], 1 / md["SF"], 1, 1])
            Bi = np.sqrt(0.5 * ((bb[s] * Sv) ** 2).sum(1))
            knee = md["iron"].B_knee
        out.append((float(Bi.max()), float(m.area[s][Bi > knee].sum() / m.area[s].sum())))
    return out


def characterise(job):
    """one (variant, angle): NI swept adaptively in the linked flux (or a fixed NI list), Newton continued from a
    secant prediction. Returns NI, flux per turn (Wb), iterations, region statistics."""
    key, var, theta, mode, scale = job
    t0 = time.time()
    m, mat, cpm, cmm, reg, a_coil = geometry(theta, var, scale)
    J1 = np.zeros(m.ncell)
    J1[cpm] = 1.0 / m.area[cpm].sum()
    J1[cmm] = -1.0 / m.area[cmm].sum()
    mats = materials(var)
    L_stk = REC["D"].L_stk
    res = dict(key=key, theta=theta, var=var, nodes=m.nnode, NI=[], phi=[], its=[], ok=[], regions=[])
    hist = []

    def step(NI):
        A0 = None
        if hist:                                        # the tangent dA/dNI of the last point (its factorisation)
            n1, a1, tg = hist[-1]
            A0 = a1 + (NI - n1) * tg
        pr = Problem(m, mat, J1 * NI, mats, L_stk)
        A, it, ok = pr.solve(A0)
        tg = np.zeros(m.nnode)
        tg[m.free] = pr.lu.solve(pr.f[m.free] / NI)
        hist[:] = [(NI, A, tg)]
        res["NI"].append(NI)
        res["phi"].append(pr.flux(A, NI))
        res["its"].append(it)
        res["ok"].append(bool(ok))
        res["regions"].append(region_stats(pr, A, reg, var))
        return res["phi"][-1]

    if isinstance(mode, list):                          # a fixed NI list
        for NI in mode:
            step(float(NI))
    else:                                               # adaptive: flux steps, fine around the expected knee
        phi_stop, ni_max = mode
        NI, phi = 5.0, step(5.0)
        while phi < phi_stop and NI < ni_max:
            Linc = phi / NI if len(res["NI"]) < 2 else max((res["phi"][-1] - res["phi"][-2]) /
                                                           (res["NI"][-1] - res["NI"][-2]), 1e-9)
            dphi = 7e-6 if 0.165e-3 < phi < 0.25e-3 else 30e-6
            NI = NI + min(max(dphi / Linc, 0.5), 0.6 * NI + 50.0)
            phi = step(NI)
    res["t_s"] = time.time() - t0
    return res


def field_at(var, theta, NIs):
    """the converged field at the last of NIs (continuation through them), for the figure."""
    m, mat, cpm, cmm, reg, a_coil = geometry(theta, var)
    J1 = np.zeros(m.ncell)
    J1[cpm] = 1.0 / m.area[cpm].sum()
    J1[cmm] = -1.0 / m.area[cmm].sum()
    A = None
    for NI in NIs:
        pr = Problem(m, mat, J1 * NI, materials(var), REC["D"].L_stk)
        A, it, ok = pr.solve(None if A is None else A * NI / prev)
        prev = NI
    return m, mat, reg, pr, A


# ------------------------------------------------------------------------------------------------ gates
def gate_slab():
    """G-SLAB [OC]: an iron slab between two opposite current sheets, the return through mu_r 1e7 iron: B in the slab
    follows H = K exactly (1-D), here solved by the 2-D code; the three material laws, linear to deep saturation."""
    MUR = 1e7
    ts, ti, to = 1.0, 10.0, 20.0
    y = np.r_[np.linspace(0, to, 21), to + ts, np.linspace(to + ts, to + ts + ti, 41)[1:], to + 2 * ts + ti,
              np.linspace(to + 2 * ts + ti, 2 * to + 2 * ts + ti, 21)[1:]]
    m = Mesh(np.linspace(0, 4.0, 5)[:-1], 4.0, y)
    lo, hi = to + ts, to + ts + ti
    jb, jt = int(np.argmin(abs(y - lo))), int(np.argmin(abs(y - hi)))
    ni = nife()
    cases = (("M235-35A, SF 0.95", dict(kind="iso", iron=SIFE, SF=0.95), lambda B: SIFE.H(np.array([B / 0.95]))[0]),
             ("NiFe foils, along them, SF 0.9", dict(kind="lam", iron=ni, SF=0.9, normal="y"),
              lambda B: ni.H(np.array([B / 0.9]))[0]),
             ("NiFe foils, across them, SF 0.9", dict(kind="lam", iron=ni, SF=0.9, normal="x"),
              lambda B: 0.9 * ni.H(np.array([B]))[0] + 0.1 * B / MU0))
    rows = []
    for name, md, Hof in cases:
        for K in (2.0, 20.0, 200.0, 2000.0, 20000.0, 200000.0):
            mat = np.full(m.ncell, 2)
            mat[((m.YC > to) & (m.YC < to + ts)) | ((m.YC > hi) & (m.YC < hi + ts))] = 0
            mat[(m.YC > lo) & (m.YC < hi)] = 1
            J = np.where((m.YC > to) & (m.YC < to + ts), K / (ts * 1e-3), 0.0) - \
                np.where((m.YC > hi) & (m.YC < hi + ts), K / (ts * 1e-3), 0.0)
            pr = Problem(m, mat, J, {1: md, 2: dict(kind="lin", mu_r=MUR)}, 1000.0)
            A, it, ok = pr.solve(tol=1e-12, maxit=60)
            Ay = A.reshape(m.nx, m.ny)[0]
            phi = abs(Ay[jt] - Ay[jb])
            # exact: H_in - H_out = K; flux balance B ti + mu0 (H_in + H_out) ts + mu0 MUR H_out 2 to = 0; B(H_in)

            def Bof(Hin):
                return brentq(lambda B: Hof(B) - Hin, 0.0, 10.0) if Hin > 0 else 0.0
            Hin = brentq(lambda h: Bof(h) * ti + MU0 * (2 * h - K) * ts + MU0 * MUR * (h - K) * 2 * to, 0.0, K)
            ex = Bof(Hin) * ti * 1e-3
            rows.append(dict(law=name, K_A_per_m=K, B_T=ex / (ti * 1e-3), rel_err=phi / ex - 1, newton_its=it))
    err = max(abs(q["rel_err"]) for q in rows)
    return dict(rows=rows, max_rel_err=err, passed=bool(err < 1e-6))


def gate_linear(lin_res):
    """G-LIN: constant mu (pole_fd2d's geometry and mu_r 3000) on this mesh against sim/pole_fd2d.solve."""
    D = REC["D"]
    out = []
    for th in (0.0, 30.0):
        ref = P.solve(D, th)["L2d"]
        mine = [q for q in lin_res if q["theta"] == th][0]
        L = mine["phi"][0] / mine["NI"][0]
        out.append(dict(theta=th, L2d_pole_fd2d_H=ref, L2d_this_H=L, ratio=L / ref))
    worst = max(abs(q["ratio"] - 1) for q in out)
    return dict(rows=out, worst=worst, passed=bool(worst < 0.02))


# ------------------------------------------------------------------------------------------------ analysis of a sweep
PHI_REF = 0.10e-3        # Wb per turn: the working-flux secant that stands for 'below the knee' [IR]


def l_ref(res):
    """the secant inductance per turn^2 at PHI_REF (the first point's if the sweep stops short of it)."""
    return PHI_REF / interp_NI(res, PHI_REF) if res["phi"][-1] >= PHI_REF else res["phi"][0] / res["NI"][0]


def knee(res, tail=0.06e-3):
    """the line below the knee (the secant at PHI_REF), the post-knee asymptote (a line through the sweep's last
    0.06 mWb, if the sweep has passed a knee) and their intersection (the knee flux) [IR: the definitions]."""
    NI, phi = np.array(res["NI"]), np.array(res["phi"])
    L0 = l_ref(res)
    out = dict(L_low_H=float(L0), L_NI5_H=float(phi[0] / NI[0]))
    hi = phi >= phi[-1] - tail
    if hi.sum() >= 2 and (phi[-1] - phi[-2]) / (NI[-1] - NI[-2]) < 0.8 * L0:
        c = np.polyfit(NI[hi], phi[hi], 1)
        out.update(L_inc_H=float(c[0]), phi0_Wb=float(c[1]))
        NIk = c[1] / (L0 - c[0])
        out.update(NI_knee=float(NIk), phi_knee_Wb=float(L0 * NIk), L_inc_frac=float(c[0] / L0))
    return out


def interp_NI(res, phi):
    """NI at the flux phi on a sweep (monotone), linear in between, the asymptote beyond."""
    NI, ph = np.array(res["NI"]), np.array(res["phi"])
    NI, ph = np.r_[0.0, NI], np.r_[0.0, ph]
    if phi <= ph[-1]:
        return float(np.interp(phi, ph, NI))
    s = (NI[-1] - NI[-2]) / (ph[-1] - ph[-2])
    return float(NI[-1] + s * (phi - ph[-1]))


def end_k(L, L_al, L_un):
    """sim/pole_fd2d.characterise's end / axial-fringe factor, interpolated by the L level [RH there]."""
    return P.K_END_A + (P.K_END_U - P.K_END_A) * (1 - (L - L_un) / max(L_al - L_un, 1e-30))


# ------------------------------------------------------------------------------------------------ the deck
def _kw():
    return RP._kw(RP.TAU_FIXED)


def deck_text(law, c_mf):
    """the pick's deck (sim/rotor_parts_duty._kw -> sim/magnetic_doubler.deck), the utron groups' law replaced if law
    is not 'record', the bypass inserted as sim/ah_steady_cusp.run does, the AH fluxes exported."""
    kw = _kw()
    if law.get("n_cyc"):                                # the same deck run longer, to its steady state
        kw = dict(kw, n_cyc=law["n_cyc"])
    if law.get("psi_s") is not None:                    # the record's law at another Psi_s (seed unchanged)
        seed = kw["seed"]
        kw = dict(kw, psi_s=law["psi_s"])
        kw["seed"] = seed
    txt, vecs, info = M.deck(**kw)
    if law["kind"] == "fe":
        txt = replace_law(txt, kw, info, law)
    if c_mf:
        byp = [f"R_bypA x1 xb1 {S.ESR:g}", f"C_bypA xb1 d {c_mf * 1e-3:g}",
               f"R_bypB x2 xb2 {S.ESR:g}", f"C_bypB xb2 b {c_mf * 1e-3:g}"]
        txt = txt.replace("D1s f2 b ND", "\n".join(byp) + "\nD1s f2 b ND")
    ex = ["v(ps_AHt)", "v(ps_AHb)"]
    txt = txt.replace("wrdata out.dat " + " ".join(vecs), "wrdata out.dat " + " ".join(vecs + ex))
    if law.get("method"):                               # case D's bypass runs: trapezoidal integration [IR: numerical]
        txt = txt.replace("method=gear", "method=" + law["method"])
    return txt, vecs + ex, info, kw


def shape_L(law, kw, which):
    """ngspice expressions of L(t) of group 1 / 2 (with the stray, as the deck) and of d(1/L)/dt."""
    w = 2 * math.pi * kw["F"]
    a = law["prof"]
    Lg = law["L_max"]
    lp = M.R_PAR * kw["L_max"]                          # the deck's stray, unchanged
    sh, dsh = M._shape_expr(a, w, 0.0 if which == 1 else math.pi)
    L = f"({Lg:.8e}*{sh}+{lp:.8e})"
    dinv = f"(-{Lg:.8e}*{dsh}/({L}*{L}))"
    return L, dinv


def neck_expr(law, node):
    pts = ",".join(f"{p:.8e},{i:.8e}" for p, i in zip(law["pwl_psi"], law["pwl_i"]))
    return f"(sgn(V({node}))*pwl(abs(V({node})),{pts}))"


def replace_law(txt, kw, info, law):
    """i = Psi / L(t) + i_neck(Psi); copper R1 i^2; mechanical (Psi^2 / 2) d(1/L)/dt [OC for this law]."""
    lines = txt.splitlines()
    R1 = info["R1"]
    out = []
    for ln in lines:
        tag = ln.split(" ", 1)[0]
        for which in (1, 2):
            nm = f"L{which}"
            L, dinv = shape_L(law, kw, which)
            cur = f"(V(ps_{nm})/{L}+{neck_expr(law, 'ps_' + nm)})"
            if tag == f"Bi_{nm}":
                p = ln.split()
                ln = f"{p[0]} {p[1]} {p[2]} I='{cur}'"
            elif tag == f"Bp_cu_{nm}":
                ln = f"Bp_cu_{nm} 0 e_cu_{nm} I='{R1:.6e}*{cur}*{cur}'"
            elif tag == f"Bp_mech_{nm}":
                ln = f"Bp_mech_{nm} 0 e_mech_{nm} I='(0.5*V(ps_{nm})*V(ps_{nm}))*{dinv}'"
        if ln.startswith(".ic"):
            # the same seed current as the record's deck, on this law's L at t = 0 (L1 aligned, L2 unaligned)
            i0 = kw["seed"]
            lp = M.R_PAR * kw["L_max"]
            a = law["prof"]
            l1 = law["L_max"] * sum(a) + lp
            l2 = law["L_max"] * sum(ak * (-1) ** k for k, ak in enumerate(a)) + lp
            parts = ln.split()
            for j, q in enumerate(parts):
                if q.startswith("v(ps_L1)="):
                    parts[j] = f"v(ps_L1)={-i0 * l1:.6e}"
                elif q.startswith("v(ps_L2)="):
                    parts[j] = f"v(ps_L2)={-i0 * l2:.6e}"
            ln = " ".join(parts)
        out.append(ln)
    return "\n".join(out) + "\n"


def law_from_L3(fe_al, L3, thetas, name, dense=0, n_cyc=None):
    """the series-neck law on a given L(theta) per turn^2 (13-angle grid, ends included): its cosine series, the group's
    L_max, the aligned sweep's neck excess over its PHI_REF secant on the utrons' share of the group flux [IR]."""
    N = REC["best"]["N_u"]
    kw = _kw()
    NI, phi = np.array(fe_al["NI"]), np.array(fe_al["phi"])
    L0 = l_ref(fe_al)
    Fn = NI - phi / L0
    L3 = np.asarray(L3)
    prof, err = PD.fit_cos(np.asarray(thetas), L3, 60.0)
    L_max = 3 * N ** 2 * L3[0]
    lp = M.R_PAR * kw["L_max"]
    lg0 = L_max * sum(prof)
    r0 = lg0 / (lg0 + lp)
    xp, yp = np.r_[0.0, 3 * N * phi / r0], np.r_[0.0, Fn / N]
    if dense:                                           # the same table resampled by a monotone cubic [IR: numerical,
        xd = np.unique(np.r_[xp, np.interp(np.arange(dense * (len(xp) - 1) + 1) / dense,  # for ngspice's step control]
                                           np.arange(len(xp)), xp)])
        xp, yp = xd, PchipInterpolator(np.r_[0.0, 3 * N * phi / r0], np.r_[0.0, Fn / N])(xd)
    out = dict(kind="fe", name=name, L_max=L_max, prof=list(prof), fit_err=float(err), pwl_psi=list(xp), pwl_i=list(yp),
               L3d_theta=list(L3), r0=r0, tau=L_max / (kw["L_max"] / kw["tau"]))
    if n_cyc:
        out["n_cyc"] = n_cyc
    return out


D_SETS = ("frame_a", "cyl_one_reversed", "cyl_aiding")
D_DENSE, D_CYC = 4, 150        # case D's runs: the neck table resampled x4, 150 cycles [IR: numerical]


def case_D(out):
    """case D: C's neck law with the 3-D utron sets of sim/utron_3d_results.json 'variants'. Their L(theta) enters as the
    set's 3-D / 2-D ratio at each angle (L13 / L2d_record_13, pole_fd2d's 2-D solve) on this study's 0.1 mWb secant, in
    place of C's end factors; i_neck unchanged (the neck sits within the stack) [IR]. Fed C's own factor the same path
    must reproduce C (the gate). The bracket 'frame_a, series': the 3-D solid section in series with this study's neck
    reluctance, 1/L = 1/L13 + (1/L_FE - 1/L_linear) [IR]."""
    r3 = json.load(open(os.path.join(HERE, "utron_3d_results.json")))
    fd = np.array(r3["L2d_record_13"])
    lf = out["lowfield"]
    L2, L3c, Llin = (np.array(lf[k]) for k in ("L2d_fe_H", "L3d_fe_H", "L2d_linear_H"))
    q = out["fe_sweeps"]["base | 0.0"]
    fe_al = dict(NI=q["NI"], phi=q["phi_Wb"])
    ratios = {"2-D (C's end factors)": L3c / L2}
    for k in D_SETS:
        ratios[k] = np.array(r3["variants"][k]["L13"]) / fd
    L13s = 1 / (1 / np.array(r3["variants"]["frame_a"]["L13"]) + 1 / L2 - 1 / Llin)
    laws = {"gate, 2-D, as C": law_from_L3(fe_al, L2 * ratios["2-D (C's end factors)"], THETAS, "D, gate")}
    for k, r in ratios.items():                         # 150 cycles and the dense table: settled runs
        laws[k] = law_from_L3(fe_al, L2 * r, THETAS, "D, " + k, dense=D_DENSE, n_cyc=D_CYC)
    laws["frame_a, series"] = law_from_L3(fe_al, L13s, THETAS, "D, frame_a, series", dense=D_DENSE, n_cyc=D_CYC)
    jobs = []
    for k, law in laws.items():
        jobs.append(("D, " + k, law, 0.0))
        # with the bypass, gear stops where the slowly growing flux first meets the sharp knee; the 3-D sets run on
        # trapezoidal integration, and the 2-D set on both, which measures the integrator's effect
        jobs.append(("D, " + k, dict(law, method="trap") if k not in ("gate, 2-D, as C",) else law, 22.0))
        if k == "2-D (C's end factors)":
            jobs.append(("D, " + k + ", gear", law, 22.0))
    with Pool(PROCS) as pool:
        runs = pool.map(run_deck, jobs, chunksize=1)
    N, ps0 = REC["best"]["N_u"], REC["best"]["psi_s"]
    res = {}
    for (name, law, c), r in zip(jobs, runs):
        key = name[3:]
        if "error" in r:
            res.setdefault(key, {})["bypass_22mF" if c else "no_bypass"] = dict(error=r["error"])
            continue
        phi_u = r["psi1_max_Wb"] * law["r0"] / (3 * N)
        res.setdefault(key, {})["bypass_22mF" if c else "no_bypass"] = dict(
            z_early=r["z_early"], z_late=r["z_late"], n_cyc=law.get("n_cyc", RP.N_CYC), P_belt_W=r["P_belt_W"], P_cu_utron_W=r["P_cu_utron_W"], P_AH_W=r["P_AH_W"],
            P_cu_fixed_W=r["P_cu_fixed_W"], P_diode_W=r["P_diode_W"], AH_AT_top=r["top"], AH_AT_bottom=r["bottom"],
            branch_AT_min=r["branch_AT_min"], branch_AT_max=r["branch_AT_max"], I1_pk_A=r["I1_pk"],
            psi1_max_Wb=r["psi1_max_Wb"], psi1_max_over_psi_s_record=r["psi1_max_Wb"] / ps0, phi_utron_max_Wb=phi_u,
            pull_N_per_utron=28.2 * (phi_u / 0.223e-3) ** 2)
    sets = {k: dict(ratio_0=float(ratios[k][0]) if k in ratios else None,
                    ratio_30=float(ratios[k][-1]) if k in ratios else None, L_al_coil_mH=N ** 2 * law["L3d_theta"][0] * 1e3,
                    L_un_coil_mH=N ** 2 * law["L3d_theta"][-1] * 1e3,
                    kappa=law["L3d_theta"][0] / law["L3d_theta"][-1], L_max_H=law["L_max"], fit_err=law["fit_err"])
            for k, law in laws.items()}
    lc, ld = out["laws"]["C"], laws["gate, 2-D, as C"]
    gate_law = max(max(abs(a - b) / max(abs(b), 1e-30) for a, b in zip(ld[f], lc[f])) for f in ("prof", "pwl_psi", "pwl_i"))
    gd = []
    for key in ("no_bypass", "bypass_22mF"):
        a, b = res["gate, 2-D, as C"][key], out["operating_point"][f"C | {key}"]
        gd.append(max(abs(a[f] / b[f] - 1) for f in ("z_early", "P_belt_W", "P_cu_utron_W")) if "error" not in a else 1.0)
        gd.append(abs(a["AH_AT_top"]["AT_mean"] / b["AH_AT_top"]["AT_mean"] - 1) if "error" not in a else 1.0)
    return dict(combination="L_D(theta) = L_FE,0.1mWb(theta) x L13_set(theta) / L2d_record_13(theta) [IR]; i_neck as C",
                source="sim/utron_3d_results.json variants (L13), L2d_record_13", sets=sets,
                gate=dict(law_rel_diff=gate_law, deck_rel_diff=max(gd), passed=bool(gate_law < 1e-9 and max(gd) < 1e-9)),
                runs=res, pull_basis="28.2 N per utron at 0.223 mWb (sim/rotor-mechanics-findings.md:183-184), x phi^2 [OC]")


START_SETS = ("frame_a", "cyl_aiding")                 # the bracket of the 3-D sets
START_SEEDS = (0.20, 0.25, 0.30, 0.40)
START_PHASES = (1.0, 1.25, 1.5, 1.75)
START_SPEEDS = ((110.0, (1.0, 1.5)), (115.0, (1.0, 1.5)))   # Hz: 1100, 1150 rpm relative


def _start_job(args):
    """one start run: sim/start_3d._job unchanged (sim/parts_first_cut.mag_job with the 3-D set's RP._kw override,
    La / Lb at 0.146 H), with sim/magnetic_doubler.deck wrapped so that the text it returns carries the case D law (and
    trapezoidal integration); law None runs the record's law (the gate). mag_job's own i1 / i2 (its z_early) use the
    record's law; the verdict uses the AH coil's A-turns, which do not."""
    import start_3d as S3
    name, set_name, law, job = args
    var = S3.utron_sets()[set_name]
    orig = M.deck
    if law is not None:
        def deck_case_d(**kw):
            txt, vecs, info = orig(**kw)
            txt = replace_law(txt, kw, info, law)
            if law.get("method"):
                txt = txt.replace("method=gear", "method=" + law["method"])
            return txt, vecs, info
        M.deck = deck_case_d
    try:
        r = S3._job((name, var, dict(job)))
    finally:
        M.deck = orig
    return r


def case_D_start(out):
    """the start in case D (sim/start_3d.py's runs, the 22 mF bypass, 150 cycles): K4 at the four full-speed phases,
    seeds of 20-40 % of Psi_s, K4 at 1100 / 1150 rpm relative at phases 1 and 1.5; frame_a and cyl_aiding. A run starts
    if the AH coil reaches half the set's own case-D steady peak (the 30 % seed's run) by the end [IR: as start_3d]."""
    import parts_first_cut as PF
    import start_3d as S3
    r3 = json.load(open(os.path.join(HERE, "utron_3d_results.json")))
    fd = np.array(r3["L2d_record_13"])
    L2 = np.array(out["lowfield"]["L2d_fe_H"])
    q = out["fe_sweeps"]["base | 0.0"]
    fe_al = dict(NI=q["NI"], phi=q["phi_Wb"])
    la_rec = RP.LA_RATIO * REC["best"]["L_group_H"]
    K4 = S3.K4
    kd = lambda ph: dict(kind="cap", V0=K4[3], pol=1, phase=ph, into="a", label=None, C_mF=K4[2] * 1e-3,
                         t_on=PF.t_on_cap(K4[2], la_rec))
    byp, n = PF.C_BYP_MF, D_CYC
    jobs = [("gate|record|K4|1", "record", None, dict(seed_frac=0.0, n_cyc=40, bypass_mF=byp, kick=kd(1.0)))]
    for sn in START_SETS:
        law = dict(law_from_L3(fe_al, L2 * np.array(r3["variants"][sn]["L13"]) / fd, THETAS, "D, " + sn,
                               dense=D_DENSE), method="trap")
        for f in START_SEEDS:
            jobs.append((f"{sn}|seed|{f:.2f}", sn, law, dict(seed_frac=f, n_cyc=n, bypass_mF=byp)))
        for ph in START_PHASES:
            jobs.append((f"{sn}|K4|{ph:g}", sn, law, dict(seed_frac=0.0, n_cyc=n, bypass_mF=byp, kick=kd(ph))))
        for F, phs in START_SPEEDS:
            for ph in phs:
                jobs.append((f"{sn}|K4|{F * 10:.0f} rpm|{ph:g}", sn, law,
                             dict(seed_frac=0.0, n_cyc=n, bypass_mF=byp, kick=kd(ph), F_Hz=F)))
    with Pool(PROCS) as pool:
        runs = pool.map(_start_job, jobs, chunksize=1)
    R = {j[0]: r for j, r in zip(jobs, runs)}
    ref = json.load(open(os.path.join(HERE, "start_3d_results.json")))["raw"]["record|K4|1"]["AHt_AT_max"]
    g = R["gate|record|K4|1"]
    gate = dict(here_AT=g.get("AHt_AT_max"), record_AT=ref, passed=bool(g.get("AHt_AT_max") is not None and
                                                                        abs(g["AHt_AT_max"] / ref - 1) < 1e-3))
    sets = {}
    for sn in START_SETS:
        st = R[f"{sn}|seed|0.30"]
        half = 0.5 * st["AHt_AT_max"] if "AHt_AT_max" in st else None
        rows = {}
        for k, r in R.items():
            if not k.startswith(sn + "|"):
                continue
            rows[k[len(sn) + 1:]] = dict(error=r["error"]) if "error" in r else dict(
                AH_AT_final=r["AHt_AT_max"], starts=bool(half and r["AHt_AT_max"] > half), retried=r.get("retried"),
                kick_E_out_mJ=(r.get("kick") or {}).get("E_out_mJ"))
        sets[sn] = dict(steady_AT=st.get("AHt_AT_max"), half_AT=half, case_D_steady_peak_AT=None, rows=rows)
        cd = (out.get("case_D") or {}).get("runs", {}).get(sn, {}).get("bypass_22mF")
        if cd:
            sets[sn]["case_D_steady_peak_AT"] = cd["AH_AT_top"]["AT_max"]
    return dict(source="sim/start_3d.py _job (sim/parts_first_cut.py mag_job), sim/magnetic_doubler.deck wrapped",
                criterion="the AH coil (top) reaches half the set's own case-D steady peak (the 30 % seed, 150 cycles)",
                numerics="the dense neck table (x4), trapezoidal integration, 150 cycles [IR]; mag_job's z_early uses "
                         "the record's law and is not reported", gate=gate, sets=sets)


def law_current(law, kw, psi, t, which):
    """the group current of a law (numpy), for the analysis."""
    if law["kind"] == "record":
        ps = law.get("psi_s") or kw["psi_s"]
        return psi / M._L(t, which, kw) * (1 + (psi / ps) ** 6)
    w = 2 * math.pi * kw["F"]
    ph = 0.0 if which == 1 else math.pi
    L = law["L_max"] * sum(ak * np.cos(k * (w * t + ph)) for k, ak in enumerate(law["prof"])) + M.R_PAR * kw["L_max"]
    return psi / L + np.sign(psi) * pwl_np(np.abs(psi), law["pwl_psi"], law["pwl_i"])


def pwl_np(x, xs, ys):
    """ngspice's pwl: linear between the points, extrapolated with the end segments' slopes."""
    xs, ys = np.asarray(xs), np.asarray(ys)
    y = np.interp(x, xs, ys)
    hi = x > xs[-1]
    y = np.where(hi, ys[-1] + (x - xs[-1]) * (ys[-1] - ys[-2]) / (xs[-1] - xs[-2]), y)
    return y


def run_deck(args):
    """one ngspice run; the analysis mirrors sim/magnetic_doubler.analyse with the law's current, plus the AH coils."""
    name, law, c_mf = args
    txt, vecs, info, kw = deck_text(law, c_mf)
    t0 = time.time()
    with tempfile.TemporaryDirectory() as tmp:
        open(os.path.join(tmp, "x.cir"), "w").write(txt)
        r = subprocess.run(["ngspice", "-b", "x.cir"], capture_output=True, text=True, timeout=3600, cwd=tmp)
        try:
            raw = np.loadtxt(os.path.join(tmp, "out.dat"))
        except (OSError, ValueError):
            return dict(name=name, c_mf=c_mf, error=(r.stdout + r.stderr)[-400:])
    t = raw[:, 0]
    if raw.ndim != 2 or t[-1] < 0.99 * kw["n_cyc"] / kw["F"]:
        return dict(name=name, c_mf=c_mf, error=f"transient stopped at {t[-1]:.4f} s: " + (r.stdout + r.stderr)[-300:])
    c = {v: raw[:, 2 * j + 1] for j, v in enumerate(vecs)}
    out = dict(name=name, c_mf=c_mf, wall_s=time.time() - t0)
    if law["kind"] == "record" and law.get("psi_s") is None:
        m = M.analyse(t, c, info, kw)
        m.pop("wave", None)
        out["magnetic_doubler_analyse"] = {k: m.get(k) for k in ("z_early", "z_late", "P_belt_W", "P_cu_utron_W",
                                                                 "P_cu_fixed_W", "P_AH_W", "P_snub_W", "I1_pk", "I1_min")}
    out.update(analyse(t, c, kw, law))
    return out


def analyse(t, c, kw, law):
    """sim/magnetic_doubler.analyse's statistics with this law's currents [IR: the same definitions], the AH coils' A-turns
    over the last 4 cycles as sim/ah_steady_cusp.run reads them, and the trajectory of group 1 over the last cycle."""
    n_cyc, T = kw["n_cyc"], 1.0 / kw["F"]
    i1 = law_current(law, kw, c["v(ps_L1)"], t, 1)
    i2 = law_current(law, kw, c["v(ps_L2)"], t, 2)
    cyc = np.floor(t / T).astype(int)
    pk = [float(np.abs(np.r_[i1[cyc == n], i2[cyc == n]]).max()) for n in range(n_cyc) if np.any(cyc == n)]
    z = [pk[k + 1] / pk[k] for k in range(len(pk) - 1) if pk[k] > 0]
    out = dict(z_early=float(np.median(z[2:8])) if len(z) > 8 else None,
               z_late=float(np.median(z[-5:])) if len(z) > 5 else None, done=bool(t[-1] >= 0.99 * n_cyc * T))
    t0, t1 = (n_cyc - 4) * T, t[-1]
    sel = t >= t0

    def mean(k):
        y = c[f"v(e_{k})"]
        return float((np.interp(t1, t, y) - np.interp(t0, t, y)) / (t1 - t0))
    keys = [k[4:-1] for k in c if k.startswith("v(e_")]
    Pw = {k: mean(k) for k in keys}
    out.update(P_belt_W=sum(v for k, v in Pw.items() if k.startswith("mech_")),
               P_cu_utron_W=Pw.get("cu_L1", 0) + Pw.get("cu_L2", 0),
               P_cu_fixed_W=sum(v for k, v in Pw.items() if k.startswith("cu_L") and k not in ("cu_L1", "cu_L2")),
               P_AH_W=Pw.get("cu_AHt", 0) + Pw.get("cu_AHb", 0), P_snub_W=Pw.get("snub", 0.0),
               I1_pk=float(np.abs(i1[sel]).max()), I1_min=float(np.abs(i1[sel]).min()),
               I1_rms=float(np.sqrt(np.mean(i1[sel] ** 2))),
               psi1_max_Wb=float(np.abs(c["v(ps_L1)"][sel]).max()))
    h = kw["ah_custom"]
    out["P_diode_W"] = out["P_belt_W"] - out["P_cu_utron_W"] - out["P_cu_fixed_W"] - out["P_AH_W"] - out["P_snub_W"]
    out["branch_AT_min"], out["branch_AT_max"] = h["N"] * out["I1_min"], h["N"] * out["I1_pk"]
    for nm, v in (("top", "v(ps_AHt)"), ("bottom", "v(ps_AHb)")):
        a = np.abs(c[v][sel] / h["L"]) * h["N"]
        out[nm] = dict(AT_min=float(a.min()), AT_mean=float(a.mean()), AT_max=float(a.max()))
    s1 = t >= (n_cyc - 1) * T
    k = max(1, int(s1.sum() // 240))
    ph = (t[s1][::k] * kw["F"]) % 1.0
    out["traj"] = dict(phase=list(ph), psi=list(c["v(ps_L1)"][s1][::k]), i=list(i1[s1][::k]))
    return out


# ------------------------------------------------------------------------------------------------ laws from the FE
def make_law(fe_al, L2d_theta, thetas, use_fe_L=True, name="fe"):
    """the series-neck law: per utron NI = Phi / P(theta) + F_n(Phi) [IR], F_n from the aligned sweep (NI less the
    low-field line); the 3-D end factor of pole_fd2d on P(theta) (option S: the end flux passes the neck) [IR]; the group
    of 3 x N_u in series; the deck's stray Lp outside the neck at its aligned share [IR]."""
    row, best = REC["row"], REC["best"]
    N = best["N_u"]
    kw = _kw()
    NI, phi = np.array(fe_al["NI"]), np.array(fe_al["phi"])
    L0 = l_ref(fe_al)
    Fn = NI - phi / L0                                               # signed: below PHI_REF the SiFe's rising mu
    th = np.asarray(thetas)
    L2 = np.asarray(L2d_theta)
    L3 = L2 * (1 + end_k(L2, L2[0], L2[-1]))
    if use_fe_L:
        return law_from_L3(fe_al, L3, thetas, name)
    prof, err, L_max = list(row["prof"]), row["fit_err"], kw["L_max"]
    lp = M.R_PAR * kw["L_max"]
    lg0 = L_max * sum(prof)
    r0 = lg0 / (lg0 + lp)                                            # the utrons' share of the group flux, aligned
    psi_tab = np.r_[0.0, 3 * N * phi / r0]
    i_tab = np.r_[0.0, Fn / N]
    return dict(kind="fe", name=name, L_max=L_max, prof=list(prof), fit_err=float(err), pwl_psi=list(psi_tab),
                pwl_i=list(i_tab), L3d_theta=list(L3), r0=r0, tau=L_max / (kw["L_max"] / kw["tau"]))


# ------------------------------------------------------------------------------------------------ main
THETAS = [2.5 * k for k in range(13)]


def jobs_list():
    """the FE runs: the built utron at the 13 angles of sim/pole_design.N_THETA (swept past the knee where the deck's
    trajectory or the knee ratios need it), pole_fd2d's linear section, the build-up from pole_fd2d's section to the
    built one, the sensitivities (aligned sweep, low field to 7.5 deg), and the mesh halving."""
    J = []
    for th in THETAS:
        stop = 0.36e-3 if th in (0.0, 30.0) else (0.29e-3 if th <= 10.0 else 0.21e-3)
        J.append((("base", th), BASE, th, (stop, 4000.0), 1.0))
    for th in THETAS:
        J.append((("linear", th), LINEAR, th, [1.0], 1.0))
    for name, var in ATTRIB.items():
        J.append((("attrib", name), var, 0.0, (0.30e-3, 4000.0), 1.0))
    for name, var in SENS.items():
        J.append((("sens", name, 0.0), var, 0.0, (0.30e-3, 4000.0), 1.0))
        for th in THETAS[1:4]:
            J.append((("sens", name, th), var, th, [5.0], 1.0))
    for sc, tag in ((0.5, "mesh"), (1.0, "mesh1")):
        J.append(((tag, 0.0), BASE, 0.0, list(MESH_NI[0.0]), sc))
        J.append(((tag, 30.0), BASE, 30.0, list(MESH_NI[30.0]), sc))
    cost = {"mesh": 0, "base": 1, "attrib": 2, "sens": 3, "mesh1": 4, "linear": 5}
    return sorted(J, key=lambda j: cost[j[0][0]])


ATTRIB = {"V1 pole_fd2d section, M235-35A": variant(geom="fd2d"),
          "V2 + strip and break, ideal NiFe (in-plane, SF 1)": variant(nife="iso", sf_nife=1.0, gj=0.0, holes=False),
          "V3 + SF 0.90": variant(nife="iso", gj=0.0, holes=False),
          "V4 + foils stacked radially": variant(gj=0.0, holes=False),
          "V5 + lap-joint gaps 0.02 mm": variant(holes=False)}
SENS = {"SF_NiFe 0.95": variant(sf_nife=0.95), "SF_NiFe 1.0": variant(sf_nife=1.0), "lap gap 0": variant(gj=0.0),
        "lap gap 0.05 mm": variant(gj=0.05), "J_s(60 C) 0.75 T": variant(kJ=0.75 / 0.80),
        "foils stacked axially": variant(nife="iso")}
MESH_NI = {0.0: (5.0, 130.0, 170.0, 400.0), 30.0: (5.0, 1150.0, 2400.0)}


def main():
    t_start = time.time()
    print("G-SLAB ...", flush=True)
    slab = gate_slab()
    print(f"  max rel error {slab['max_rel_err']:.2e}", flush=True)
    jobs = jobs_list()
    print(f"FE: {len(jobs)} jobs on {PROCS} processes", flush=True)
    with Pool(PROCS) as pool:
        fe = pool.map(characterise, jobs, chunksize=1)
    print(f"FE done in {time.time() - t_start:.0f} s", flush=True)
    post(fe, slab, t_start)


def half_knee(res):
    """the knee's centre: the flux (Wb) and NI where the incremental L first falls to the mean of the low-field L and the
    post-knee asymptote (half the low-field L if the sweep has no asymptote) [IR: the definition]."""
    NI, phi = np.r_[0.0, res["NI"]], np.r_[0.0, res["phi"]]
    L0 = l_ref(res)
    k_ = knee(res)
    lev = 0.5 * (L0 + k_["L_inc_H"]) if "L_inc_H" in k_ else 0.5 * L0
    inc = np.diff(phi) / np.diff(NI)
    k = np.where(inc < lev)[0]
    if not len(k):
        return None, None
    k = k[0]
    # the crossing inside segment k: the segment's own incremental L is below the level; take its start-to-end mean
    return float(0.5 * (phi[k] + phi[k + 1])), float(0.5 * (NI[k] + NI[k + 1]))


def saturation_order(res):
    """per region: the first NI (and flux) at which any of its iron passes the knee (mu_diff < MU_KNEE)."""
    out = {}
    for j, name in enumerate(REGIONS):
        first = next((n for n, (ni, rg) in enumerate(zip(res["NI"], res["regions"])) if rg[j][1] > 0), None)
        out[name] = dict(NI=res["NI"][first] if first is not None else None,
                         phi_Wb=res["phi"][first] if first is not None else None,
                         B_max_last_T=res["regions"][-1][j][0], share_last=res["regions"][-1][j][1])
    return out


def regions_at(res, phi):
    """the region statistics at the sweep point nearest above the flux phi."""
    k = int(np.searchsorted(np.array(res["phi"]), phi))
    k = min(k, len(res["phi"]) - 1)
    return dict(NI=res["NI"][k], phi_Wb=res["phi"][k],
                **{name: dict(B_max_T=res["regions"][k][j][0], share_saturated=res["regions"][k][j][1])
                   for j, name in enumerate(REGIONS)})


def fe_map_NI(base, L2, L3, theta, phi_u):
    """the FE's ampere-turns per utron at (theta, phi_u), 3-D by option S (the end factor on the external path):
    NI_3D = NI_2D - phi (1/L2 - 1/L3), linear in theta between the solved angles [IR]."""
    th = np.array(THETAS)
    k = int(np.clip(np.searchsorted(th, theta) - 1, 0, len(th) - 2))
    vals = []
    for j in (k, k + 1):
        vals.append(interp_NI(base[THETAS[j]], phi_u) - phi_u * (1 / L2[j] - 1 / L3[j]))
    f = (theta - th[k]) / (th[k + 1] - th[k])
    return float((1 - f) * vals[0] + f * vals[1])


def fidelity(run, law, base, L2, L3):
    """the law's current against the FE map along the run's last cycle (group 1)."""
    if "traj" not in run:
        return None
    N, kw = REC["best"]["N_u"], _kw()
    lp = M.R_PAR * kw["L_max"]
    errs, absd = [], []
    for ph, psi, i in zip(run["traj"]["phase"], run["traj"]["psi"], run["traj"]["i"]):
        th = 60.0 * (ph if ph <= 0.5 else 1.0 - ph)
        phi_u = abs(psi - lp * i) / (3 * N)
        ni_fe = fe_map_NI(base, L2, L3, th, phi_u)
        ni_law = abs(i) * N
        errs.append((ni_law - ni_fe) / ni_fe)
        absd.append(ni_law - ni_fe)
    errs, absd = np.array(errs), np.array(absd)
    k = int(np.argmax(np.abs(errs)))
    return dict(rms_rel=float(np.sqrt(np.mean(errs ** 2))), max_rel=float(errs[k]), max_abs_AT=float(absd[np.argmax(np.abs(absd))]),
                at_phase=float(run["traj"]["phase"][k]))


def zlin_job(args):
    """the screen's linear gain z_lin (sim/pole_design._z_at: ideal diodes, no load, 16 cycles)."""
    name, prof, tau = args
    m = M.run(prof=prof, tau=tau, tau_fixed=RP.TAU_FIXED, sat=False, F=REC["f"], n_cyc=16, snub="scaled")
    return dict(name=name, z_lin=m.get("z_late"), z_early=m.get("z_early"))


def post(fe, slab, t_start):
    by = {tuple(q["key"]): q for q in fe}
    D, sp, row, best = REC["D"], REC["sp"], REC["row"], REC["best"]
    N = best["N_u"]
    base = {th: by[("base", th)] for th in THETAS}
    lin = [by[("linear", th)] for th in THETAS]
    g_lin = gate_linear(lin)
    # -- low-field L(theta): 2-D, with pole_fd2d's end factors, and the record's
    L2 = np.array([l_ref(base[th]) for th in THETAS])
    L5 = np.array([base[th]["phi"][0] / base[th]["NI"][0] for th in THETAS])
    Llin = np.array([q["phi"][0] / q["NI"][0] for q in lin])
    L3 = L2 * (1 + end_k(L2, L2[0], L2[-1]))
    Lrec = np.array(row["L_per_n2"])
    prof_C, err_C = PD.fit_cos(THETAS, L3, 60.0)
    lowfield = dict(theta_deg=THETAS, phi_ref_Wb=PHI_REF, L2d_fe_H=list(L2), L2d_fe_NI5_H=list(L5),
                    L2d_linear_H=list(Llin), L3d_fe_H=list(L3),
                    L3d_record_H=list(Lrec), ratio_fe_record=list(L3 / Lrec),
                    L_al_coil_fe_mH=N ** 2 * L3[0] * 1e3, L_un_coil_fe_mH=N ** 2 * L3[-1] * 1e3,
                    L_al_coil_record_mH=N ** 2 * row["L_al"] * 1e3, L_un_coil_record_mH=N ** 2 * row["L_un"] * 1e3,
                    kappa_fe=float(L3[0] / L3[-1]), kappa_record=row["kappa"], prof_fe=list(prof_C),
                    prof_fe_fit_err=float(err_C))
    # -- the knee, per angle; the incremental L after it (2-D; 3-D by option S and by option P)
    knees = {}
    for j, th in enumerate(THETAS):
        k = knee(base[th])
        k["phi_half_Wb"], k["NI_half"] = half_knee(base[th])
        if "L_inc_H" in k:
            k3 = 1 / (1 / L3[j] + 1 / k["L_inc_H"] - 1 / L2[j])
            k.update(L_inc_3d_S_frac=float(k3 / L3[j]),
                     L_inc_3d_P_frac=float((k["L_inc_H"] + (L3[j] - L2[j])) / L3[j]))
        knees[str(th)] = k
    k0, k30 = knees["0.0"], knees["30.0"]
    phi_strip = nife().J_s * SF_NIFE * sp["t_n"] * sp["L"] * 1e-6
    sat = dict(phi_s_design_Wb=sp["phi_s_Wb"], phi_s_record_built_Wb=sp["phi_s_built_Wb"], B_NIFE_T=U.B_NIFE,
               strip_section_mm2=sp["t_n"] * sp["L"], J_s_60C_T=nife().J_s, SF_NiFe=SF_NIFE,
               phi_strip_saturated_Wb=phi_strip, phi_knee_aligned_Wb=k0.get("phi_knee_Wb"),
               phi_half_aligned_Wb=k0.get("phi_half_Wb"), NI_knee_aligned=k0.get("NI_knee"),
               psi_s_record_group=best["psi_s"],
               psi_s_fe_group=best["psi_s"] * k0["phi_knee_Wb"] / sp["phi_s_Wb"],
               knee_vs_design=k0["phi_knee_Wb"] / sp["phi_s_Wb"] - 1,
               L_inc_aligned_frac_2d=k0.get("L_inc_frac"), L_inc_unaligned_frac_2d=k30.get("L_inc_frac"),
               L_inc_aligned_frac_3d_S=k0.get("L_inc_3d_S_frac"), L_inc_unaligned_frac_3d_S=k30.get("L_inc_3d_S_frac"),
               L_inc_aligned_frac_3d_P=k0.get("L_inc_3d_P_frac"), L_inc_unaligned_frac_3d_P=k30.get("L_inc_3d_P_frac"),
               record_estimate=dict(aligned=0.05, unaligned=0.30, source="sim/utron_profile.py docstring [RH]"),
               record_law_dpsi_di_frac=dict(at_psi_s=1 / 8.0, at_1p21_psi_s=1 / (1 + 7 * 1.21 ** 6)))
    # -- mesh halving
    mrows = []
    for th in (0.0, 30.0):
        a, b = by[("mesh1", th)], by[("mesh", th)]
        for NI, p1, p2 in zip(a["NI"], a["phi"], b["phi"]):
            mrows.append(dict(theta=th, NI=NI, phi_Wb=p1, phi_half_cells_Wb=p2, change=p2 / p1 - 1))
        inc1 = (a["phi"][-1] - a["phi"][-2]) / (a["NI"][-1] - a["NI"][-2])
        inc2 = (b["phi"][-1] - b["phi"][-2]) / (b["NI"][-1] - b["NI"][-2])
        mrows.append(dict(theta=th, NI="incremental L, last two points", phi_Wb=inc1, phi_half_cells_Wb=inc2,
                          change=inc2 / inc1 - 1))
    worst = max(abs(q["change"]) for q in mrows)
    g_mesh = dict(rows=mrows, nodes=[by[("mesh1", 0.0)]["nodes"], by[("mesh", 0.0)]["nodes"]], worst=worst,
                  passed=bool(worst < 0.01))
    # -- the laws and the deck
    law_rec = dict(kind="record")
    law_A = dict(kind="record", psi_s=sat["psi_s_fe_group"])
    law_B = make_law(base[0.0], L2, THETAS, use_fe_L=False, name="B")
    law_C = make_law(base[0.0], L2, THETAS, use_fe_L=True, name="C")
    law_Cp = make_law(base[7.5], L2, THETAS, use_fe_L=True, name="C'")   # the bracket: the 7.5 deg sweep's excess
    laws = {"record": law_rec, "A": law_A, "B": law_B, "C": law_C, "C'": law_Cp}
    series_check = {}
    for name in SENS:
        # the variant's neck in series with the base's external path: 1/L = 1/L_base + its change of neck reluctance,
        # from the aligned sweeps [IR: the series model]; its NI 5 points at 2.5-7.5 deg check it
        dR = 1 / l_ref(by[("sens", name, 0.0)]) - 1 / L2[0]
        L2s = 1 / (1 / L2 + dR)
        laws["C, " + name] = make_law(by[("sens", name, 0.0)], L2s, THETAS, use_fe_L=True, name="C, " + name)
        dR5 = 1 / by[("sens", name, 0.0)]["phi"][0] * by[("sens", name, 0.0)]["NI"][0] - 1 / L5[0]
        series_check[name] = [dict(theta=th, dR_NI5_this_angle=float(by[("sens", name, th)]["NI"][0] /
                                                                     by[("sens", name, th)]["phi"][0] - 1 / L5[j]),
                                   dR_NI5_aligned=float(dR5)) for j, th in enumerate(THETAS[:4]) if j > 0]
    djobs = [(name, law, c) for name, law in laws.items() for c in (0.0, 22.0)]
    zjobs = [("record", list(row["prof"]), row["tau"]), ("C (FE L(theta))", list(prof_C), L3[0] / row["R_per_n2"])]
    print(f"deck: {len(djobs)} ngspice runs", flush=True)
    with Pool(PROCS) as pool:
        zl = pool.map_async(zlin_job, zjobs)
        runs = pool.map(run_deck, djobs, chunksize=1)
        zl = zl.get()
    deck = {}
    for (name, law, c), r in zip(djobs, runs):
        if "error" in r:
            deck.setdefault(name, {})["bypass_22mF" if c else "no_bypass"] = r
            continue
        # the base map is the truth only for the base's laws; a sensitivity variant's map was not solved at every angle
        r["fidelity_vs_FE"] = fidelity(r, law, base, L2, L3) if name in ("record", "A", "B", "C", "C'") else None
        deck.setdefault(name, {})["bypass_22mF" if c else "no_bypass"] = r
    # -- the record's aligned operating point (its own run, with the bypass): the flux and current at alignment
    tr = deck["record"]["bypass_22mF"]["traj"]
    ph = np.array(tr["phase"])
    k_al = int(np.argmin(np.minimum(ph, 1 - ph)))
    lp = M.R_PAR * REC["L_max"]
    psi_a, i_a = abs(tr["psi"][k_al]), abs(tr["i"][k_al])
    ra = dict(phase=float(ph[k_al]), psi_group_Wb=psi_a, i_A=i_a, NI=i_a * N, phi_u_Wb=(psi_a - lp * i_a) / (3 * N),
              psi_over_psi_s=psi_a / best["psi_s"])
    order = dict(aligned=saturation_order(base[0.0]), unaligned=saturation_order(base[30.0]),
                 at_knee_aligned=regions_at(base[0.0], k0["phi_knee_Wb"]),
                 at_record_aligned_flux=regions_at(base[0.0], ra["phi_u_Wb"]))

    # -- the build-up from pole_fd2d's section, and the sensitivities (aligned)
    def summ(res):
        k = knee(res)
        k["phi_half_Wb"], k["NI_half"] = half_knee(res)
        return dict(L_low_H=k["L_low_H"], L_NI5_H=k["L_NI5_H"], phi_knee_Wb=k.get("phi_knee_Wb"),
                    L_inc_frac=k.get("L_inc_frac"),
                    phi0_Wb=k.get("phi0_Wb"), phi_half_Wb=k["phi_half_Wb"],
                    NI_at_record_aligned_flux=interp_NI(res, ra["phi_u_Wb"]))
    attrib = {"V0 pole_fd2d section, linear mu_r 3000": dict(L_low_H=float(Llin[0]), L_NI5_H=float(Llin[0]))}
    for name in ATTRIB:
        attrib[name] = summ(by[("attrib", name)])
    attrib["V6 + stud holes = the built utron"] = summ(base[0.0])
    sens = {"baseline": summ(base[0.0])}
    for name in SENS:
        sens[name] = summ(by[("sens", name, 0.0)])
    # -- G-DECK: the record's pick (sim/ah_steady_cusp_results.json; sim/ah-steady-cusp-findings.md)
    ref = {r_["C_byp_mF"]: r_ for r_ in json.load(open(os.path.join(HERE, "ah_steady_cusp_results.json")))["rows"]}
    gd = []
    for c, key in ((0.0, "no_bypass"), (22.0, "bypass_22mF")):
        r, q = deck["record"][key], ref[c]
        mda = r["magnetic_doubler_analyse"]
        gd.append(dict(bypass_mF=c, z_early=r["z_early"], z_early_record=q["z_early"], P_belt_W=r["P_belt_W"],
                       P_belt_record_W=q["P_belt_W"], top_AT_mean=r["top"]["AT_mean"],
                       top_AT_mean_record=q["top"]["AT_mean"], top_AT_min=r["top"]["AT_min"],
                       top_AT_max=r["top"]["AT_max"], P_cu_utron_W=r["P_cu_utron_W"],
                       P_cu_utron_record_W=q["P_cu_utron_W"],
                       analyse_mirror_err=max(abs(r[k] / mda[k] - 1) for k in ("z_early", "P_belt_W", "P_cu_utron_W", "I1_pk"))))
    dev = max(max(abs(g["z_early"] / g["z_early_record"] - 1), abs(g["P_belt_W"] / g["P_belt_record_W"] - 1),
                  abs(g["top_AT_mean"] / g["top_AT_mean_record"] - 1)) for g in gd)
    g_deck = dict(rows=gd, worst=dev, passed=bool(dev < 1e-3 and abs(gd[1]["top_AT_mean"] - 300) < 1.0
                                                   and abs(gd[1]["z_early"] - 1.147) < 5e-4
                                                   and abs(gd[1]["P_belt_W"] - 18.1) < 0.05))
    # -- the operating point table
    op = {}
    for name, d in deck.items():
        for key, r in d.items():
            if "error" in r:
                op[f"{name} | {key}"] = dict(error=r["error"])
                continue
            op[f"{name} | {key}"] = dict(
                z_early=r["z_early"], P_belt_W=r["P_belt_W"], P_cu_utron_W=r["P_cu_utron_W"], P_AH_W=r["P_AH_W"],
                P_cu_fixed_W=r["P_cu_fixed_W"], P_diode_W=r["P_diode_W"], AH_AT_top=r["top"], AH_AT_bottom=r["bottom"],
                branch_AT_min=r["branch_AT_min"], branch_AT_max=r["branch_AT_max"], I1_pk_A=r["I1_pk"],
                I1_rms_A=r["I1_rms"], psi1_max_over_psi_s_record=r["psi1_max_Wb"] / best["psi_s"],
                fidelity_vs_FE=r["fidelity_vs_FE"])
    out = dict(
        source="sim/neck_nonlinear.py", pick=RP.PICK,
        inputs=dict(design=REC["design"], N_u=N, psi_s_group=best["psi_s"], L_max_H=REC["L_max"], tau_s=row["tau"],
                    L_al_H=row["L_al"], L_un_H=row["L_un"], prof=row["prof"], strip_t_mm=sp["t_n"], break_mm=sp["brk"],
                    stack_mm=sp["L"], studs_uv_mm=sp["studs"], stud_hole_mm=sp["stud_d"], K_END=[P.K_END_A, P.K_END_U],
                    deck=dict(TAU_FIXED=RP.TAU_FIXED, SEED_FRAC=RP.SEED_FRAC, LA_RATIO=RP.LA_RATIO, N_CYC=RP.N_CYC,
                              ND=RP.ND, ESR_ohm=S.ESR, AH=M.AH["r160"])),
        materials=dict(M235_35A=dict(H_A_per_m=H_SIFE, J_T=J_SIFE, SF=SF_SIFE, B_knee_T=SIFE.B_knee,
                                     source_class="EN 10106 M235-35A typical 50 Hz normal curve (mill data sheets) [IR]"),
                       NiFe80=dict(H_A_per_m=H_NIFE, J_20C_T=J_NIFE, kJ_60C=KJ_60C, J_s_60C_T=nife().J_s, SF=SF_NIFE,
                                   B_knee_60C_T=nife().B_knee,
                                   source_class="80 % NiFe-Mo annealed, Permalloy-80 / Mumetall / HyMu 80 class, DC [IR]"),
                       lap_gap_mm=G_J, mu_knee=MU_KNEE),
        gates=dict(G_SLAB=slab, G_LIN=g_lin, G_MESH=g_mesh, G_DECK=g_deck),
        record_aligned=ra, lowfield=lowfield, knees=knees, saturation=sat, saturation_order=order,
        buildup_aligned=attrib,
        sensitivity_aligned=sens, sensitivity_series_check=series_check, laws={k: {kk: vv for kk, vv in v.items()} for k, v in laws.items()},
        z_lin=zl, operating_point=op,
        trajectories={name: deck[name]["bypass_22mF"]["traj"] for name in ("record", "C")},
        fe_sweeps={f"{q['key'][0]} | " + " | ".join(str(x) for x in q["key"][1:]): dict(NI=q["NI"], phi_Wb=q["phi"],
                                                                                       newton_its=q["its"], ok=q["ok"],
                                                                                       nodes=q["nodes"])
                   for q in fe},
        runtime_s=time.time() - t_start)
    json.dump(out, open(OUT_JSON, "w"), indent=1, default=float)
    print(f"wrote {OUT_JSON}", flush=True)
    figure(out, base, L2, L3)
    report(out)
    out["case_D"] = case_D(out)
    json.dump(out, open(OUT_JSON, "w"), indent=1, default=float)
    return out


def report(out):
    g = out["gates"]
    print(f"G-SLAB max rel err {g['G_SLAB']['max_rel_err']:.1e} | G-LIN worst {100 * g['G_LIN']['worst']:.2f} % | "
          f"G-MESH worst {100 * g['G_MESH']['worst']:.2f} % | G-DECK worst {g['G_DECK']['worst']:.1e}")
    s = out["saturation"]
    print(f"knee {s['phi_knee_aligned_Wb'] * 1e3:.4f} mWb/utron ({100 * s['knee_vs_design']:+.1f} % on the design's "
          f"{s['phi_s_design_Wb'] * 1e3:.4f}); strip saturated {s['phi_strip_saturated_Wb'] * 1e3:.4f}; L_inc aligned "
          f"{100 * s['L_inc_aligned_frac_2d']:.1f} %, unaligned {100 * (s['L_inc_unaligned_frac_2d'] or 0):.1f} % (2-D)")
    for k, v in out["operating_point"].items():
        if "error" in v:
            print(k, "ERROR", v["error"][-200:])
            continue
        fv = v["fidelity_vs_FE"] or dict(rms_rel=float("nan"), max_rel=float("nan"))
        print(f"{k:34s} z {v['z_early']:.4f} belt {v['P_belt_W']:.2f} W utron Cu {v['P_cu_utron_W']:.2f} W AH top "
              f"{v['AH_AT_top']['AT_min']:.0f}-{v['AH_AT_top']['AT_max']:.0f} ({v['AH_AT_top']['AT_mean']:.0f}) A-t | "
              f"law vs FE rms {100 * fv['rms_rel']:.1f} % max {100 * fv['max_rel']:+.1f} %")


INK, INK2, MUTED, GRID, BASEL, SURF = "#0b0b0b", "#52514e", "#898781", "#e1e0d9", "#c3c2b7", "#fcfcfb"
SERIES = ("#2a78d6", "#eb6834", "#1baf7a", "#eda100")          # categorical slots 1-4, fixed order


def record_law_group(i, theta, psi_s=None):
    """the record's law inverted: the group flux (total, with the stray) at the current i and angle theta."""
    kw = _kw()
    ps = psi_s or kw["psi_s"]
    t = np.array([(theta / 60.0) / kw["F"]])
    L = float(M._L(t, 1, kw)[0])
    return brentq(lambda q: q / L * (1 + (q / ps) ** 6) - i, 0.0, 10 * ps)


def fe_group(base, L2, L3, j, NI):
    """the FE's group flux (total, with the stray) at NI per utron and angle index j, 3-D by option S."""
    kw = _kw()
    N = REC["best"]["N_u"]
    res = base[THETAS[j]]
    # option S: NI_3D(phi) = NI_2D(phi) - phi (1/L2 - 1/L3); invert on the sweep's points
    ph = np.r_[0.0, res["phi"]]
    ni3 = np.r_[0.0, np.array(res["NI"]) - np.array(res["phi"]) * (1 / L2[j] - 1 / L3[j])]
    phi = np.interp(NI, ni3, ph)
    return 3 * N * phi + M.R_PAR * kw["L_max"] * NI / N


def figure(out, base, L2, L3):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    N = REC["best"]["N_u"]
    kw = _kw()
    psr = kw["psi_s"]
    plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 8.5, "axes.edgecolor": BASEL,
                         "axes.labelcolor": INK2, "xtick.color": INK2, "ytick.color": INK2, "axes.linewidth": 0.8})
    fig, axs = plt.subplots(2, 2, figsize=(13.0, 9.6), facecolor=SURF)
    for ax in axs.ravel():
        ax.set_facecolor(SURF)
        ax.grid(True, color=GRID, lw=0.6)
        ax.set_axisbelow(True)
        for sd in ("top", "right"):
            ax.spines[sd].set_visible(False)
    # (a) the group's flux against its current: FE (option S) and the record's law, four angles
    ax = axs[0, 0]
    sel = (0, 4, 8, 12)
    for c, j in zip(SERIES, sel):
        res = base[THETAS[j]]
        NI = np.linspace(0, max(res["NI"]), 300)
        ax.plot(NI / N, fe_group(base, L2, L3, j, NI), color=c, lw=2.0, solid_capstyle="round",
                label=f"FE, {THETAS[j]:g}°")
        ii = np.linspace(0.0, max(res["NI"]) / N, 120)
        ax.plot(ii, [record_law_group(x, THETAS[j]) for x in ii], color=c, lw=1.2, ls=(0, (4, 2.5)),
                label=f"record's law, {THETAS[j]:g}°")
    ax.axhline(psr, color=MUTED, lw=0.8)
    ax.text(0.2, psr * 1.015, f"record's Ψs {psr:.4f} Wb-t", color=INK2, fontsize=7.8, va="bottom")
    ax.set_xlim(0, 6.0)
    ax.set_ylim(0, 0.24)
    ax.set_xlabel("group current i (A; 3 utrons × 200 turns)")
    ax.set_ylabel("group flux Ψ (Wb-turns, with the deck's stray Lp)")
    ax.set_title("(a) Ψ(i) at four rotor angles: the FE (solid) and the record's ^6 law (dashed)", loc="left",
                 color=INK, fontsize=9.5)
    ax.legend(ncol=2, fontsize=7.4, frameon=False, labelcolor=INK2, loc="lower right")
    # (b) the incremental inductance against the flux, aligned and unaligned
    ax = axs[0, 1]
    lp = M.R_PAR * kw["L_max"]
    for c, j, lab in ((SERIES[0], 0, "aligned"), (SERIES[3], 12, "unaligned")):
        res = base[THETAS[j]]
        ph = np.r_[0.0, res["phi"]]
        ni3 = np.r_[0.0, np.array(res["NI"]) - np.array(res["phi"]) * (1 / L2[j] - 1 / L3[j])]
        q = 3 * N * ph + lp * ni3 / N                     # the sweep's own points, group terms (option S)
        inc = np.diff(q) / np.diff(ni3 / N)
        ax.plot(0.5 * (q[1:] + q[:-1]) / psr, inc / inc[0], color=c, lw=2.0, marker="o", ms=3.5,
                mec=SURF, mew=0.8, label=f"FE, {lab} (between sweep points)")
        ii = np.linspace(0.01, 6.0, 600)
        qq = np.array([record_law_group(x, THETAS[j]) for x in ii])
        ir = np.gradient(qq, ii)
        ax.plot(qq / psr, ir / ir[0], color=c, lw=1.2, ls=(0, (4, 2.5)), label=f"record's law, {lab}")
    for y, txt in ((0.05, "record's estimate, aligned (5 %)"), (0.30, "record's estimate, unaligned (30 %)")):
        ax.axhline(y, color=MUTED, lw=0.8)
        ax.text(0.03, y + 0.012, txt, color=INK2, fontsize=7.6)
    ax.set_xlim(0, 1.6)
    ax.set_ylim(0, 1.08)
    ax.set_xlabel("Ψ / Ψs (record)")
    ax.set_ylabel("dΨ/di ÷ its low-field value")
    ax.set_title("(b) the knee: incremental inductance against the flux", loc="left", color=INK, fontsize=9.5)
    ax.legend(fontsize=7.4, frameon=False, labelcolor=INK2, loc="upper right")
    # (c) the field at alignment at the record's aligned operating current
    ax = axs[1, 0]
    ra = out["record_aligned"]
    m, mat, reg, pr, A = field_at(BASE, 0.0, [20.0, 80.0, 120.0, 150.0, ra["NI"]])
    bb = m.b(A)
    Bn = np.zeros(m.ncell)
    for k, md in pr.materials.items():
        sl = pr.sel[k]
        if md["kind"] == "iso":
            Bi = np.sqrt(0.5 * ((bb[sl] / md["SF"]) ** 2).sum(1))
        else:
            Bi = np.sqrt(0.5 * ((bb[sl] * np.array([1 / md["SF"], 1 / md["SF"], 1, 1])) ** 2).sum(1))
        Bn[sl] = Bi / md["iron"].B_knee
    X = m.X
    sh = m.nx // 2
    xe = np.r_[m.x, X]
    xe = np.where(xe > X / 2, xe - X, xe)
    order = np.argsort(np.where(m.x >= X / 2, m.x - X, m.x))
    xc = np.where(m.x >= X / 2, m.x - X, m.x)[order]
    grid = Bn.reshape(m.nx, m.ny - 1)[order]
    edges = np.r_[xc, xc[-1] + np.diff(np.r_[m.x, X])[order][-1]]
    msk = np.ma.masked_where(mat.reshape(m.nx, m.ny - 1)[order] == 0, grid)
    from matplotlib.colors import LinearSegmentedColormap
    cmap = LinearSegmentedColormap.from_list("blue", ["#cde2fb", "#86b6ef", "#3987e5", "#1c5cab", "#0d366b"])
    pc = ax.pcolormesh(edges, m.y, msk.T, cmap=cmap, vmin=0, vmax=1.2, shading="flat", rasterized=True)
    An = A.reshape(m.nx, m.ny)[order]
    lev = np.linspace(An.min(), An.max(), 24)[1:-1]
    ax.contour(xc, m.y, An.T, levels=lev, colors=INK, linewidths=0.45)
    D = REC["D"]
    plus, minus, _ = D.coil_rects()
    for (a0, a1, b0, b1) in (plus, minus):
        ax.add_patch(matplotlib.patches.Rectangle((a0, b0), a1 - a0, b1 - b0, fill=False, ec="#d58a4e", lw=1.0))
    ax.set_xlim(-48, 48)
    ax.set_ylim(-76, 18)
    ax.set_aspect("equal")
    ax.grid(False)
    cb = fig.colorbar(pc, ax=ax, fraction=0.035, pad=0.02)
    cb.set_label("iron B ÷ its knee (μ_diff = 100): NiFe 0.77 T, SiFe 1.46 T", color=INK2, fontsize=7.6)
    cb.outline.set_edgecolor(BASEL)
    ax.set_xlabel("tangential, from the utron's centre (mm)")
    ax.set_ylabel("radial, from the tip face (mm)")
    ax.set_title(f"(c) aligned, {ra['NI']:.0f} A-t per utron (the record's aligned current):\niron B and flux lines",
                 loc="left", color=INK, fontsize=9.5)
    # (d) the trajectory over one cycle: the record and the corrected law, both with the bypass
    ax = axs[1, 1]
    for c, name, lab in ((SERIES[0], "record", "record's law (the pick)"), (SERIES[1], "C", "FE law (case C)")):
        r = out["trajectories"][name]
        ph = np.array(r["phase"])
        o = np.argsort(ph)
        ax.plot(ph[o], np.abs(np.array(r["psi"]))[o] / psr, color=c, lw=2.0, label=lab)
    kn = out["saturation"]["phi_knee_aligned_Wb"] * 3 * N / out["laws"]["C"]["r0"]
    ax.axhline(kn / psr, color=MUTED, lw=0.8)
    ax.text(0.52, kn / psr + 0.012, "FE knee flux, aligned", color=INK2, fontsize=7.6)
    ax.set_xlim(0, 1)
    ax.set_ylim(0.3, 1.1)
    ax.set_xlabel("rotor phase of group A (0 and 1 aligned, 0.5 unaligned)")
    ax.set_ylabel("|Ψ| / Ψs (record)")
    ax.set_title("(d) group A's flux over one 120 Hz cycle,\nwith the 22 mF bypass", loc="left", color=INK, fontsize=9.5)
    ax.legend(fontsize=7.6, frameon=False, labelcolor=INK2, loc="lower center")
    fig.suptitle("The neck's nonlinear check: the pick's utron with its 3.0 mm NiFe neck (sim/neck_nonlinear.py)",
                 x=0.01, ha="left", color=INK, fontsize=11.5)
    fig.tight_layout(rect=(0, 0, 1, 0.97))
    os.makedirs(os.path.dirname(OUT_FIG), exist_ok=True)
    fig.savefig(OUT_FIG, dpi=130, facecolor=SURF)
    plt.close(fig)
    print(f"wrote {OUT_FIG}", flush=True)


if __name__ == "__main__":
    if sys.argv[1:] == ["Dstart"]:                      # the start in case D, on the written results
        res = json.load(open(OUT_JSON))
        res["case_D_start"] = case_D_start(res)
        json.dump(res, open(OUT_JSON, "w"), indent=1, default=float)
        print(json.dumps(res["case_D_start"], default=float)[:4000])
    elif sys.argv[1:] == ["D"]:                         # case D on the written results, without re-solving the field
        res = json.load(open(OUT_JSON))
        res["case_D"] = case_D(res)
        json.dump(res, open(OUT_JSON, "w"), indent=1, default=float)
        print(json.dumps({k: {kk: (vv.get("AH_AT_top"), vv.get("z_early"), vv.get("P_belt_W")) for kk, vv in v.items()}
                          for k, v in res["case_D"]["runs"].items()}, default=float)[:3000])
    else:
        main()
