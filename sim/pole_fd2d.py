"""sim/pole_fd2d.py -- 2-D magnetostatics of the new reluctance pole pair: a WOUND utron (rotor U-core, two pole tips
facing outward) against passive stator iron (discrete bridges = the C-EMs without coils, or a toothed ring),
across a RADIAL air gap. Gives L(theta) per turn^2, the inductance ratio, the coil time constant L/R, flux densities.

Model [OC/IR]:
- plane of rotation (x tangential = arc length at the gap radius r_g, y radial, gap at 0 < y < g), unrolled [IR: the
  pole pair is < 1/2 of r_g; curvature neglected]; periodic in x over 120 deg (one utron, its share of stator iron);
- vector potential A_z: -div(nu grad A) = J, finite-volume 5-point stencil on a non-uniform grid (fine in the gap),
  A = 0 far above and below; linear iron mu_r 3000 (laminated SiFe, unsaturated) [RH];
- coil around the utron's back iron: + side in the slot, - side under the back iron, 1 ampere-turn;
- L/N^2 = L_stk (<A>_+ - <A>_-) (2-D, per axial stack length), then an end correction [RH]: unaligned x (1 + K_END_U),
  aligned x (1 + K_END_A) for the end-turn / axial fringe flux the 2-D section does not see;
- R/N^2 = rho l_turn / (fill A_slot), tau = L_aligned / R (independent of the turns).
Usage: python3 sim/pole_fd2d.py   (self-check against the analytic aligned permeance)
"""
import math

import numpy as np
import scipy.sparse as sp
import scipy.sparse.linalg as spla

MU0 = 4e-7 * math.pi
MUR_FE = 3000.0
RHO_CU = 1.72e-8
FILL = 0.50
K_END_U, K_END_A = 0.30, 0.03          # end / axial-fringe corrections to the 2-D permeance [RH: SRM practice]
R_G = 130.0                             # gap radius (mm), the tube's utron radius
DOMAIN_DEG = 120.0


def grid_axis(breaks, lo, hi, fine, coarse, grow=1.25):
    """non-uniform axis: cells <= fine near every break, growing geometrically to coarse."""
    pts = sorted(set([lo, hi] + [b for b in breaks if lo <= b <= hi]))
    out = [pts[0]]
    for a, b in zip(pts[:-1], pts[1:]):
        L = b - a
        if L <= 2 * fine:
            n = max(1, int(math.ceil(L / fine)))
            out += list(a + L * np.arange(1, n + 1) / n); continue
        # grow from both ends to the middle
        left, h = [], fine
        while sum(left) + h < L / 2:
            left.append(h); h = min(h * grow, coarse)
        rest = L - 2 * sum(left)
        nmid = max(1, int(math.ceil(rest / coarse)))
        steps = left + [rest / nmid] * nmid + left[::-1]
        x = a
        for s in steps:
            x += s; out.append(x)
        out[-1] = b
    return np.array(sorted(set(np.round(out, 9))))


class Design:
    """all lengths in mm. kind 'S': discrete stator bridges (n_br per rev); 'T': toothed stator ring (N_s teeth per rev).
    The utron: two tips of width w_p (each with n_t teeth in kind T), slot s between them (coil window), slot depth d,
    back iron b; coil fill in the slot (+) and a matching block under the back iron (-)."""

    def __init__(self, kind="S", g=0.5, w_p=16.0, s=30.0, d=50.0, b=None, L_stk=100.0, n_br=6, t_b=None, l_b=None,
                 N_s=24, n_t=2, tooth_ratio=0.42, tooth_depth=None, t_ring=None, clr=1.0, r_g=R_G):
        self.kind, self.g, self.w_p, self.s, self.d = kind, g, w_p, s, d
        self.b = w_p if b is None else b
        self.L_stk, self.n_br, self.N_s, self.n_t = L_stk, n_br, N_s, n_t
        self.t_b = w_p if t_b is None else t_b
        self.W_u = 2 * w_p + s
        self.l_b = self.W_u if l_b is None else l_b
        self.tooth_ratio = tooth_ratio
        self.tooth_depth = max(5 * g, 3.0) if tooth_depth is None else tooth_depth
        self.t_ring = w_p if t_ring is None else t_ring
        self.clr = clr
        self.r_g = r_g
        self.X = 2 * math.pi * r_g * DOMAIN_DEG / 360.0
        self.cyc_per_rev = n_br if kind == "S" else N_s
        self.p_t = 2 * math.pi * r_g / N_s if kind == "T" else None

    def coil_rects(self):
        c = self.clr
        x0, x1 = -self.s / 2 + c, self.s / 2 - c
        y1 = -2.0                                   # the coil stays 2 mm below the tip face
        y0 = -self.d + c
        h = y1 - y0
        plus = (x0, x1, y0, y1)
        yb = -self.d - self.b
        minus = (x0, x1, yb - c - h, yb - c)
        return plus, minus, (x1 - x0) * h

    def utron_rects(self, xc):
        g = []
        w, s, d, b = self.w_p, self.s, self.d, self.b
        for side in (-1, 1):
            xa = xc + (s / 2 if side > 0 else -s / 2 - w)
            if self.kind == "T" and self.n_t > 0:
                # n_t teeth on the tip face; the tip body under them
                td = self.tooth_depth
                g.append((xa, xa + w, -d, -td))
                tw = self.tooth_ratio * self.p_t
                for k in range(self.n_t):
                    cx = xa + w / 2 + (k - (self.n_t - 1) / 2) * self.p_t
                    g.append((cx - tw / 2, cx + tw / 2, -td, 0.0))
            else:
                g.append((xa, xa + w, -d, 0.0))
        g.append((xc - s / 2 - w, xc + s / 2 + w, -d - b, -d))
        return g

    def stator_rects(self):
        out, gp = [], self.g
        if self.kind == "S":
            pitch = 2 * math.pi * self.r_g / self.n_br
            k = int(round(self.X / pitch))
            for j in range(k):
                xb = j * pitch
                out.append((xb - self.l_b / 2, xb + self.l_b / 2, gp, gp + self.t_b))
        else:
            td = self.tooth_depth
            out.append((-self.X, 2 * self.X, gp + td, gp + td + self.t_ring))      # the ring back
            tw = self.tooth_ratio * self.p_t
            n = int(round(self.X / self.p_t))
            for j in range(-1, n + 1):
                xt = j * self.p_t
                out.append((xt - tw / 2, xt + tw / 2, gp, gp + td))
        return out

    def radial_depth(self):
        """utron depth below the gap face: slot + back iron + coil return + clearances (mm)."""
        plus, minus, _ = self.coil_rects()
        return -minus[2] + 1.0

    def fits(self, sleeve_r=20.5, clear=3.0):
        return self.r_g - self.radial_depth() >= sleeve_r + clear

    def tip_centres_ok(self):
        """kind T: both tips must align together -> tip centre distance a multiple of the tooth pitch."""
        if self.kind != "T":
            return True
        dist = self.s + self.w_p
        return abs(dist / self.p_t - round(dist / self.p_t)) < 1e-6


def _wrap(r, X):
    """split a rectangle that crosses the periodic boundary into pieces inside [0, X)."""
    x0, x1, y0, y1 = r
    out = []
    for sh in (-X, 0.0, X):
        a, b = max(x0 + sh, 0.0), min(x1 + sh, X)
        if b > a:
            out.append((a, b, y0, y1))
    return out


def solve(design, theta_deg, hx=0.5, fine=None, return_field=False):
    D = design
    X = D.X
    fine = min(0.1, D.g / 5) if fine is None else fine
    xu = (D.r_g * math.radians(theta_deg)) % X          # the utron centre; stator bridge / tooth at x = 0
    ur = [p for r in D.utron_rects(xu) for p in _wrap(r, X)]
    st = [p for r in D.stator_rects() for p in _wrap(r, X)]
    plus, minus, a_coil = D.coil_rects()
    cp = _wrap((plus[0] + xu, plus[1] + xu, plus[2], plus[3]), X)
    cm = _wrap((minus[0] + xu, minus[1] + xu, minus[2], minus[3]), X)
    ylo = min(r[2] for r in ur + cm) - 40.0
    yhi = max(r[3] for r in st) + 40.0
    ybr = [0.0, D.g] + [r[2] for r in ur + st + cp + cm] + [r[3] for r in ur + st + cp + cm]
    y = grid_axis(ybr, ylo, yhi, fine, 2.0)
    nx = int(round(X / hx))
    x = np.arange(nx) * (X / nx)
    hxa = X / nx
    ny = len(y)
    dy = np.diff(y)
    xc = x + hxa / 2                                     # cell centres (periodic)
    yc = 0.5 * (y[:-1] + y[1:])
    nu = np.full((nx, ny - 1), 1.0 / MU0)
    J = np.zeros((nx, ny - 1))
    XX, YY = np.meshgrid(xc, yc, indexing="ij")

    def paint(arr, rects, val):
        for (a, b, c0, c1) in rects:
            m = (XX >= a) & (XX < b) & (YY >= c0) & (YY < c1)
            arr[m] = val
    paint(nu, ur + st, 1.0 / (MU0 * MUR_FE))
    a_p = sum((r[1] - r[0]) * (r[3] - r[2]) for r in cp)
    a_m = sum((r[1] - r[0]) * (r[3] - r[2]) for r in cm)
    paint(J, cp, 1.0 / (a_p * 1e-6))
    paint(J, cm, -1.0 / (a_m * 1e-6))
    # unknowns: nodes i (0..nx-1, periodic), j (1..ny-2); A = 0 at j = 0, ny-1
    hx_m, dy_m = hxa * 1e-3, dy * 1e-3
    idx = -np.ones((nx, ny), int)
    inner = np.arange(1, ny - 1)
    idx[:, 1:-1] = np.arange(nx * (ny - 2)).reshape(nx, ny - 2)
    rows, cols, vals = [], [], []
    rhs = np.zeros(nx * (ny - 2))
    ip = (np.arange(nx) + 1) % nx
    im = (np.arange(nx) - 1) % nx
    for j in inner:
        # horizontal faces between node (i,j) and (i+1,j): half-cells (i, j-1) [height dy_{j-1}] and (i, j) [dy_j]
        ce = (nu[:, j - 1] * dy_m[j - 1] / 2 + nu[:, j] * dy_m[j] / 2) / hx_m
        cw = (nu[im, j - 1] * dy_m[j - 1] / 2 + nu[im, j] * dy_m[j] / 2) / hx_m
        cn = (nu[im, j] * hx_m / 2 + nu[:, j] * hx_m / 2) / dy_m[j]
        cs = (nu[im, j - 1] * hx_m / 2 + nu[:, j - 1] * hx_m / 2) / dy_m[j - 1]
        me = idx[:, j]
        rows += [me, me, me, me, me]
        cols += [me, idx[ip, j], idx[im, j], idx[:, j + 1], idx[:, j - 1]]
        vals += [ce + cw + cn + cs, -ce, -cw, -cn, -cs]
        src = (J[:, j - 1] * dy_m[j - 1] / 2 * hx_m / 2 + J[im, j - 1] * dy_m[j - 1] / 2 * hx_m / 2 +
               J[:, j] * dy_m[j] / 2 * hx_m / 2 + J[im, j] * dy_m[j] / 2 * hx_m / 2)
        rhs[me] = src
    rows, cols, vals = np.concatenate(rows), np.concatenate(cols), np.concatenate(vals)
    keep = cols >= 0
    K = sp.csr_matrix((vals[keep], (rows[keep], cols[keep])), shape=(nx * (ny - 2),) * 2)
    A = np.zeros((nx, ny))
    A[:, 1:-1] = spla.spsolve(K.tocsc(), rhs).reshape(nx, ny - 2)
    Ac = 0.25 * (A[:, :-1] + A[ip, :-1] + A[:, 1:] + A[ip, 1:])          # cell-centre A
    w = np.outer(np.full(nx, hx_m), dy_m)
    mp, mm = J > 0, J < 0
    dA = (Ac[mp] * w[mp]).sum() / w[mp].sum() - (Ac[mm] * w[mm]).sum() / w[mm].sum()
    L2d = D.L_stk * 1e-3 * dA                                            # H per turn^2
    out = dict(theta=theta_deg, L2d=L2d)
    if return_field:
        Bx = (A[:, 1:] - A[:, :-1]) / dy_m[None, :]
        out.update(x=x, y=y, A=A, Bx=Bx, nu=nu)
    return out


def mean_turn_mm(D):
    """mean turn of the yoke coil: a rounded rectangle around the back iron (b radial x L_stk axial) at the coil's
    mid-build, 2 (L_stk + b) + 2 pi (clr + h_c / 2) [OC: geometry]. (Before 2026-10 the four corners were counted as
    pi (h_c / 2 + clr) + 4 clr, ~15 % short: R, tau and the copper mass in the p1 .. recheck JSONs carry that.)"""
    plus, _, _ = D.coil_rects()
    h_c = plus[3] - plus[2]
    return 2 * (D.L_stk + D.b) + 2 * math.pi * (D.clr + h_c / 2)


def characterise(D, n_theta=9, hx=0.5):
    """L(theta) over one half cycle (aligned -> unaligned), the ratio, tau, and the field in the tip at alignment."""
    period = 360.0 / D.cyc_per_rev
    th = np.linspace(0.0, period / 2, n_theta)
    L = np.array([solve(D, t, hx=hx)["L2d"] for t in th])
    La, Lu = L[0] * (1 + K_END_A), L[-1] * (1 + K_END_U)
    plus, minus, a_coil = D.coil_rects()
    l_turn = mean_turn_mm(D)
    r_per_n2 = RHO_CU * l_turn * 1e-3 / (FILL * a_coil * 1e-6)
    tau = La / r_per_n2
    Lcorr = L * (1 + K_END_A + (K_END_U - K_END_A) * (1 - (L - L[-1]) / max(L[0] - L[-1], 1e-30)))
    return dict(theta=list(th), L_per_n2=list(Lcorr), L_al=La, L_un=Lu, kappa=La / Lu, L2d_ratio=L[0] / L[-1],
                tau=tau, R_per_n2=r_per_n2, l_turn_mm=l_turn, a_coil_mm2=a_coil, cyc_per_rev=D.cyc_per_rev,
                f_Hz=D.cyc_per_rev * 600.0 / 60.0, W_u=D.W_u, radial_depth_mm=D.radial_depth(), fits=D.fits(), r_g=D.r_g)


def _selfcheck():
    """aligned, deep tips and a wide bridge: the 2-D L must approach the two-gap analytic mu0 w_p L_stk / (2 g)
    (plus fringe / leakage, so the solver may only exceed it modestly)."""
    D = Design(kind="S", g=1.0, w_p=20.0, s=30.0, d=50.0, L_stk=100.0)
    L = solve(D, 0.0)["L2d"]
    Lan = MU0 * D.w_p * 1e-3 * D.L_stk * 1e-3 / (2 * D.g * 1e-3)
    return L, Lan


if __name__ == "__main__":
    L, Lan = _selfcheck()
    print(f"selfcheck aligned g 1 mm: L/N^2 2-D {L * 1e6:.3f} uH, two-gap analytic {Lan * 1e6:.3f} uH, ratio {L / Lan:.3f}")
