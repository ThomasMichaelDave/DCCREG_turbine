#!/usr/bin/env python3
"""sim/edge_coil.py -- the electromagnet under a fast HV edge: a turn-resolved ladder (BRIEF_EDGE_DRIVEN_COIL).

One ladder section per turn (brief §4), solved by a conventional nodal (MNA) transient, trapezoidal rule [OC method]:
  (a) self-L  mu0 a [ln(8a/r) - 2] (surface current) + the wire's internal impedance as a fitted Foster R-L network
      (exact Bessel Z_int of a round Cu wire, NNLS -> positive elements) per turn                            [OC]
  (b) mutual M between every pair of turns, both coils (Maxwell, complete elliptic K/E at parameter m = k^2);
      winding sense as a sign per turn (circulation = helicity x axial progression of the current)            [OC]
  (c) skin effect: the Foster network of (a)                                                                 [OC]
  (d) capacitance: the full Maxwell matrix (turns, MnZn rod segments, can = ground) from an axisymmetric
      finite-volume electrostatic solve; MnZn is a resistive conductor (brief §8.1): segments joined by R || C   [OC/IR]
  (e) core: dL(w) = M(mu(w)) - M(mu = 1) from an axisymmetric magnetostatic (psi = r A_phi) finite-volume solve
      with the complex mu, fitted with common real poles and PSD residues -> a passive R-L network on the
      shared magnetising path; frequency-independent mu enters as a constant dL                              [OC]
  (f) the field in the working volume: closed-form loop fields + the core's increment from the same FV solve [OC]
No retardation (quasi-static PEEC); every run reports t_r/tau and t_r/tau_turn (brief §5).

Not python/circuit.py (brief §0). Not wired into pump_engine (frozen); the compact terminal model of brief §7 is
for a chosen design (O-1..O-4 open), so the ladder is the design tool here.

Usage:  python3 sim/edge_coil.py gates | runs | all     -> sim/edge_coil_results.json, sim/edge_coil_raw/*.npz
Assumed geometry and materials: GEOM below (every value [IR]; see sim/edge-coil-predictions.md §A).
"""
import json
import math
import os
import subprocess
import sys
import tempfile
import time

import numpy as np
import scipy.linalg as sla
import scipy.sparse as sp
import scipy.sparse.linalg as spla
from scipy.optimize import nnls
from scipy.special import ellipe, ellipk, jve

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
RAW = os.path.join(HERE, "edge_coil_raw")
RESULTS = os.path.join(HERE, "edge_coil_results.json")
MU0 = 4e-7 * math.pi
EPS0 = 8.8541878128e-12
RHO_CU = 1.72e-8                                    # Ohm m, 20 C                                          [OC]

GEOM = dict(                                        # every value an assumption standing in for O-1..O-4    [IR]
    n_turns=40, pitch=1.5, wire_d=0.5,              # mm; single layer per coil
    r_rod=10.0, rod_len=70.0, gap=20.0,             # MnZn rods O20 x 70, facing ends 20 mm apart
    former_t=1.0, former_eps=2.1,                   # PTFE former under the winding
    r_can=40.0, can_margin=20.0,                    # grounded coaxial can (electrostatic return)
    rod_seg=5.0, rod_rho=5.0, rod_eps_bulk=1e4,     # MnZn: Ohm m, bulk eps_r between segments
    mu_i=2300.0, f_r=1.5e6,                         # Debye mu(f) = 1 + (mu_i - 1)/(1 + j f/f_r)
    rod=True, mu=None,                              # mu None -> the Debye MnZn; a number -> frequency-independent
    h_es=0.05, h_ms=0.25,                           # FV cell sizes in the winding band, mm
)


# ======================================================================================================
# 1. closed forms: mutual, self, loop field, wire internal impedance + Foster fit                    [OC]
# ======================================================================================================
def mutual(a, b, d):
    """Maxwell: M = mu0 sqrt(ab) [(2/k - k) K(k) - (2/k) E(k)], k^2 = 4ab/((a+b)^2 + d^2); SI units."""
    m = 4 * a * b / ((a + b) ** 2 + d ** 2)
    k = np.sqrt(m)
    return MU0 * np.sqrt(a * b) * ((2 / k - k) * ellipk(m) - (2 / k) * ellipe(m))


def self_L_ext(a, rw):
    """surface-current self-inductance of a circular turn (brief §4a)."""
    return MU0 * a * (math.log(8 * a / rw) - 2.0)


def loop_Bz_axis(a, dz):
    return MU0 * a ** 2 / (2 * (a ** 2 + dz ** 2) ** 1.5)


def z_int(f, rw, rho=RHO_CU):
    """internal impedance per metre of a round wire: (k rho / 2 pi r) J0(kr)/J1(kr), k = (1 - j)/delta."""
    f = np.asarray(f, float)
    delta = np.sqrt(rho / (math.pi * f * MU0))
    k = (1 - 1j) / delta
    z = k * rw
    return k * rho / (2 * math.pi * rw) * jve(0, z) / jve(1, z)


def skin_fit(rw, length, fband=(1e3, 3e9), npole=24):
    """Z_int(jw) - R0 = sum R_k jw/(jw + p_k), R_k >= 0 (NNLS on relative error); returns R0, p, R, max rel err."""
    f = np.logspace(math.log10(fband[0]), math.log10(fband[1]), 160)
    w = 2 * math.pi * f
    Z = z_int(f, rw) * length
    R0 = RHO_CU * length / (math.pi * rw ** 2)
    p = 2 * math.pi * np.logspace(math.log10(fband[0]) + 1.0, math.log10(fband[1]) + 2.0, npole)
    basis = (1j * w[:, None]) / (1j * w[:, None] + p[None, :])
    wt = 1 / np.abs(Z)
    Am = np.vstack([basis.real * wt[:, None], basis.imag * wt[:, None]])
    y = np.concatenate([(Z.real - R0) * wt, Z.imag * wt])
    R, _ = nnls(Am, y)
    Zf = R0 + basis @ R
    err = float(np.max(np.abs(Zf - Z) / np.abs(Z)))
    return R0, p, R, err


# ======================================================================================================
# 2. geometry: turns, rods, feed                                                                     [IR]
# ======================================================================================================
def coil_layout(g, pair, mismatch=0):
    """turn list (mm): dict(coil, k, r, z) in physical z order per coil, and rods [(z0, z1)].
    single: one rod centred at z = 0; pair: rods at +-(gap/2 .. gap/2 + rod_len), coil B may lose `mismatch` turns
    at its outer end."""
    a = g["r_rod"] + g["former_t"] + g["wire_d"] / 2
    N, p = g["n_turns"], g["pitch"]
    span = N * p
    turns, rods = [], []
    if not pair:
        rods = [(-g["rod_len"] / 2, g["rod_len"] / 2)]
        for k in range(N):
            turns.append(dict(coil=0, k=k, r=a, z=-span / 2 + (k + 0.5) * p))
    else:
        zc = g["gap"] / 2 + g["rod_len"] / 2
        rods = [(-zc - g["rod_len"] / 2, -zc + g["rod_len"] / 2), (zc - g["rod_len"] / 2, zc + g["rod_len"] / 2)]
        for c, sgn in ((0, -1), (1, +1)):
            n_c = N - (mismatch if c == 1 else 0)
            for k in range(n_c):                      # k = 0 at the inner (junction) end
                z_in = sgn * (zc - span / 2 + (k + 0.5) * p) if sgn > 0 else -(zc - span / 2 + (k + 0.5) * p)
                turns.append(dict(coil=c, k=k, r=a, z=z_in))
    return a, turns, rods


# ======================================================================================================
# 3. axisymmetric grids + finite-volume operators                                                    [OC]
# ======================================================================================================
def _graded(x0, x1, h0, h1, hmax, gr=1.18):
    L = x1 - x0
    if L <= 1.5 * max(h0, h1):
        return np.array([])
    sl, sr = [], []
    while sum(sl) + sum(sr) < L:
        nl = min(h0 * gr ** (len(sl) + 1), hmax)
        nr = min(h1 * gr ** (len(sr) + 1), hmax)
        (sl if nl <= nr else sr).append(nl if nl <= nr else nr)
    s = np.array(sl + sr[::-1])
    s *= L / s.sum()
    return x0 + np.cumsum(s)[:-1]


def axis(lo, hi, fine, hmax):
    """nodes lo..hi; uniform spacing h inside each fine (a, b, h) interval, graded elsewhere."""
    fine = sorted((max(a, lo), min(b, hi), h) for a, b, h in fine)
    merged = []
    for a, b, h in fine:
        if merged and a <= merged[-1][1]:
            pa, pb, ph = merged[-1]
            merged[-1] = (pa, max(pb, b), min(ph, h))
        else:
            merged.append((a, b, h))
    pts, x, hprev = [lo], lo, hmax
    for a, b, h in merged:
        n = max(1, int(round((b - a) / h)))
        if a > x:
            pts += list(_graded(x, a, hprev, h, hmax))
            pts.append(a)
        pts += list(a + (b - a) * np.arange(1, n + 1) / n)
        x, hprev = b, (b - a) / n
    if hi > x:
        pts += list(_graded(x, hi, hprev, hmax, hmax))
        pts.append(hi)
    return np.unique(np.round(np.array(pts), 9))


def fv_laplacian(r, z, coef_cell, kind):
    """symmetric FV operator on the node grid r (nr) x z (nz), cell coefficients coef_cell (nr-1, nz-1).
    kind 'es': div(eps grad V) in cylindrical (weights 2 pi r);  kind 'ms': div((nu/r) grad psi) (exact radial)."""
    nr, nz = len(r), len(z)
    dr, dz = np.diff(r), np.diff(z)
    rm = 0.5 * (r[:-1] + r[1:])
    idx = np.arange(nr * nz).reshape(nr, nz)
    C = coef_cell
    pad = np.zeros((nr - 1, nz + 1), dtype=C.dtype)
    pad[:, 1:-1] = C                                   # pad[:, j] = cell j-1
    dzp = np.zeros(nz + 1)
    dzp[1:-1] = dz
    # radial edges (i, j)-(i+1, j): half cells j-1 and j
    hz = 0.5 * (pad[:, :-1] * dzp[None, :-1] + pad[:, 1:] * dzp[None, 1:])          # (nr-1, nz)
    if kind == "es":
        cr = 2 * math.pi * rm[:, None] * hz / dr[:, None]
    else:
        cr = hz * 2.0 / (r[1:] ** 2 - r[:-1] ** 2)[:, None]
    # axial edges (i, j)-(i, j+1): half cells i-1 and i
    padr = np.zeros((nr + 1, nz - 1), dtype=C.dtype)
    padr[1:-1, :] = C
    if kind == "es":
        lo = np.concatenate([[0.0], math.pi * (r[1:] ** 2 - rm ** 2)])             # cell i-1 part, node i
        hi = np.concatenate([math.pi * (rm ** 2 - r[:-1] ** 2), [0.0]])            # cell i part
    else:
        with np.errstate(divide="ignore"):
            lo = np.concatenate([[0.0], np.log(r[1:] / rm)])
            hi = np.concatenate([np.where(r[:-1] > 0, np.log(rm / np.where(r[:-1] > 0, r[:-1], 1)), 0.0), [0.0]])
    cz = (padr[:-1, :] * lo[:, None] + padr[1:, :] * hi[:, None]) / dz[None, :]
    rows = np.concatenate([idx[:-1, :].ravel(), idx[:, :-1].ravel()])
    cols = np.concatenate([idx[1:, :].ravel(), idx[:, 1:].ravel()])
    vals = np.concatenate([cr.ravel(), cz.ravel()])
    return rows, cols, vals, idx


def lap_from_edges(n, rows, cols, vals):
    W = sp.coo_matrix((vals, (rows, cols)), shape=(n, n))
    W = (W + W.T).tocsr()
    d = np.asarray(W.sum(axis=1)).ravel()
    return (sp.diags(d) - W).tocsr()


# ======================================================================================================
# 4. electrostatic extraction: Maxwell capacitance matrix (turns, rod segments; can = ground)         [OC]
# ======================================================================================================
def es_extract(g, turns, rods, log=print):
    h = g["h_es"]
    rw = g["wire_d"] / 2
    a = turns[0]["r"]
    zs = [t["z"] for t in turns]
    z_lo = min(r0 for r0, _ in rods) - g["can_margin"]
    z_hi = max(r1 for _, r1 in rods) + g["can_margin"]
    fine_z = []
    for c in sorted({t["coil"] for t in turns}):
        zc = [t["z"] for t in turns if t["coil"] == c]
        fine_z.append((min(zc) - 2.0, max(zc) + 2.0, h))
    for r0, r1 in rods:
        fine_z += [(r0 - 1, r0 + 1, 0.25), (r1 - 1, r1 + 1, 0.25)]
    z = axis(z_lo, z_hi, fine_z, 2.0) * 1e-3
    r = axis(0.0, g["r_can"], [(g["r_rod"] - 0.5, a + rw + 1.5, h)], 2.0) * 1e-3
    nr, nz = len(r), len(z)
    rc = 0.5 * (r[:-1] + r[1:]) * 1e3
    zc_ = 0.5 * (z[:-1] + z[1:]) * 1e3
    RC, ZC = np.meshgrid(rc, zc_, indexing="ij")
    eps = np.ones((nr - 1, nz - 1))
    for r0, r1 in rods:                                # PTFE former along the rod length
        eps[(RC >= g["r_rod"]) & (RC <= g["r_rod"] + g["former_t"]) & (ZC >= r0) & (ZC <= r1)] = g["former_eps"]
    rows, cols, vals, idx = fv_laplacian(r, z, eps * EPS0, "es")
    R, Z = np.meshgrid(r * 1e3, z * 1e3, indexing="ij")
    cid = -np.ones((nr, nz), int)                     # -1 free; 0 ground; 1.. conductors
    cid[-1, :] = 0
    cid[:, 0] = 0
    cid[:, -1] = 0
    names = []
    for t in turns:
        names.append(f"T{t['coil']}.{t['k']}")
        m = (R - t["r"]) ** 2 + (Z - t["z"]) ** 2 <= (rw * 1.0001) ** 2
        assert m.sum() >= 4, "wire under-resolved"
        cid[m] = len(names)
    seg_of = []
    if g["rod"]:
        for ir, (r0, r1) in enumerate(rods):
            ns = max(1, int(round((r1 - r0) / g["rod_seg"])))
            edges = r0 + (r1 - r0) * np.arange(ns + 1) / ns
            for s in range(ns):
                names.append(f"R{ir}.{s}")
                m = (R <= g["r_rod"] + 1e-9) & (Z >= edges[s] - 1e-9) & (Z <= edges[s + 1] + 1e-9) & (cid != 0)
                cid[m] = len(names)
                seg_of.append(dict(rod=ir, s=s, z0=edges[s], z1=edges[s + 1]))
    flat = cid.ravel()
    rodset = np.zeros(len(names) + 1, bool)
    for k, nm in enumerate(names):
        rodset[k + 1] = nm.startswith("R")
    keep = ~(rodset[flat[rows]] & rodset[flat[cols]] & (flat[rows] != flat[cols]))   # rod segment | segment: R || C
    L = lap_from_edges(nr * nz, rows[keep], cols[keep], vals[keep])
    free = np.where(flat < 0)[0]
    K = len(names)
    t0 = time.time()
    lu = spla.splu(L[free][:, free].tocsc(), permc_spec="COLAMD")
    Cm = np.zeros((K, K))
    LC = L[:, flat > 0].tocsc()
    cond_nodes = np.where(flat > 0)[0]
    cond_id = flat[cond_nodes] - 1
    for c0 in range(0, K, 24):
        cs = list(range(c0, min(K, c0 + 24)))
        E = np.zeros((len(cond_nodes), len(cs)))
        for j, c in enumerate(cs):
            E[cond_id == c, j] = 1.0
        rhs = -(LC[free] @ E)
        VF = lu.solve(np.asarray(rhs))
        V = np.zeros((nr * nz, len(cs)))
        V[free] = VF
        V[cond_nodes] = E
        Qn = L @ V
        for i in range(K):
            Cm[i, cs] = Qn[cond_nodes[cond_id == i]].sum(axis=0)
    Cm = 0.5 * (Cm + Cm.T)
    log(f"  ES: grid {nr} x {nz} = {nr * nz / 1e3:.0f} k nodes, {K} conductors, {time.time() - t0:.1f} s")
    return dict(C=Cm, names=names, rod_segs=seg_of, grid=(nr, nz))


def gate_es(log=print):
    """coaxial cylinder r_a inside a grounded can R, long: 2 pi eps0/ln(R/a) per metre at the mid-plane."""
    ra, Rc, Lz, h = 11.0, 40.0, 600.0, 0.25
    z = axis(-Lz / 2, Lz / 2, [(-5, 5, h)], 4.0) * 1e-3
    r = axis(0, Rc, [(ra - 1, ra + 1, h)], 2.0) * 1e-3
    nr, nz = len(r), len(z)
    rows, cols, vals, idx = fv_laplacian(r, z, np.full((nr - 1, nz - 1), EPS0), "es")
    L = lap_from_edges(nr * nz, rows, cols, vals)
    R, Z = np.meshgrid(r * 1e3, z * 1e3, indexing="ij")
    cid = -np.ones((nr, nz), int)
    cid[-1, :] = 0
    cid[:, 0] = 0
    cid[:, -1] = 0
    cid[(R <= ra + 1e-9) & (cid != 0)] = 1
    flat = cid.ravel()
    free = flat < 0
    V = np.zeros(nr * nz)
    V[flat == 1] = 1
    V[free] = spla.spsolve(L[free][:, free].tocsc(), -(L[free][:, flat == 1] @ V[flat == 1]))
    # charge per metre from the radial flux through r = 20 mm at the mid-plane (|z| < 5 mm, uniform cells)
    i = np.searchsorted(r, 0.020)
    jm = np.where(np.abs(z) < 0.005)[0]
    flux = 2 * math.pi * 0.5 * (r[i] + r[i + 1]) * EPS0 * (V[idx[i, jm]] - V[idx[i + 1, jm]]) / (r[i + 1] - r[i])
    cpm = float(np.mean(flux))
    ref = 2 * math.pi * EPS0 / math.log(Rc / ra)
    err = cpm / ref - 1
    log(f"G-ES coax C' {cpm * 1e12:.3f} pF/m vs {ref * 1e12:.3f} analytic: {err * 100:+.2f} %")
    return dict(C_fd=cpm, C_ref=ref, rel=err, pass_=abs(err) <= 0.02)


# ======================================================================================================
# 5. magnetostatic extraction: core increment dL(mu) and field transfer dT(mu)                         [OC]
# ======================================================================================================
class MS:
    """psi = r A_phi on an (r, z) node grid; -div((nu/r) grad psi) = J; psi = 0 on the axis and far boundary."""

    def __init__(self, g, turns, rods, targets, h=None):
        h = h or g["h_ms"]
        a = turns[0]["r"]
        zt = [t["z"] for t in turns] + list(targets)
        z_lo, z_hi = min(r0 for r0, _ in rods) - 3, max(r1 for _, r1 in rods) + 3
        z_lo, z_hi = min(z_lo, min(zt) - 3), max(z_hi, max(zt) + 3)
        self.z = axis(-600.0, 600.0, [(z_lo, z_hi, h)], 40.0) * 1e-3
        self.r = axis(0.0, 400.0, [(0.0, 1.0, h), (g["r_rod"] - 1.5, a + 2.5, h)], 30.0) * 1e-3
        self.g, self.turns, self.rods, self.targets = g, turns, rods, list(targets)
        nr, nz = len(self.r), len(self.z)
        rc = 0.5 * (self.r[:-1] + self.r[1:]) * 1e3
        zc = 0.5 * (self.z[:-1] + self.z[1:]) * 1e3
        RC, ZC = np.meshgrid(rc, zc, indexing="ij")
        self.inrod = np.zeros((nr - 1, nz - 1), bool)
        for r0, r1 in rods:
            self.inrod |= (RC <= g["r_rod"]) & (ZC >= r0) & (ZC <= r1)
        self.idx = np.arange(nr * nz).reshape(nr, nz)
        R, Z = np.meshgrid(self.r, self.z, indexing="ij")
        bnd = (R == 0) | (R == self.r[-1]) | (Z == self.z[0]) | (Z == self.z[-1])
        self.free = np.where(~bnd.ravel())[0]
        self.n = nr * nz
        self.S = self._interp([(t["r"] * 1e-3, t["z"] * 1e-3) for t in turns])      # turn positions

    def _interp(self, pts):
        """bilinear weights (n_pts x n_nodes): source distribution and evaluation (same stencil, symmetric)."""
        rows, cols, vals = [], [], []
        for k, (rp, zp) in enumerate(pts):
            i = np.searchsorted(self.r, rp) - 1
            j = np.searchsorted(self.z, zp) - 1
            fr = (rp - self.r[i]) / (self.r[i + 1] - self.r[i])
            fz = (zp - self.z[j]) / (self.z[j + 1] - self.z[j])
            for di, dj, w in ((0, 0, (1 - fr) * (1 - fz)), (1, 0, fr * (1 - fz)), (0, 1, (1 - fr) * fz), (1, 1, fr * fz)):
                rows.append(k)
                cols.append(self.idx[i + di, j + dj])
                vals.append(w)
        return sp.csr_matrix((vals, (rows, cols)), shape=(len(pts), self.n))

    def solve(self, mu_r):
        """returns M (n_turns x n_turns, H) and T (n_targets x n_turns, T per A at the axis targets)."""
        nu = np.where(self.inrod, 1.0 / (MU0 * mu_r), 1.0 / MU0).astype(complex if np.iscomplexobj(mu_r) else float)
        rows, cols, vals, _ = fv_laplacian(self.r, self.z, nu, "ms")
        L = lap_from_edges(self.n, rows, cols, vals)
        f = self.free
        lu = spla.splu(L[f][:, f].tocsc(), permc_spec="COLAMD")
        rhs = self.S[:, f].T.toarray().astype(L.dtype)
        psi = np.zeros((self.n, rhs.shape[1]), dtype=L.dtype)
        psi[f] = lu.solve(rhs)
        M = 2 * math.pi * (self.S @ psi)
        M = 0.5 * (M + M.T)
        T = np.zeros((len(self.targets), len(self.turns)), dtype=L.dtype)
        r1, r2 = self.r[1], self.r[2]
        for q, zt in enumerate(self.targets):
            j = np.searchsorted(self.z, zt * 1e-3) - 1
            fz = (zt * 1e-3 - self.z[j]) / (self.z[j + 1] - self.z[j])
            p1 = (1 - fz) * psi[self.idx[1, j]] + fz * psi[self.idx[1, j + 1]]
            p2 = (1 - fz) * psi[self.idx[2, j]] + fz * psi[self.idx[2, j + 1]]
            # psi = (B/2) r^2 + c r^4 near the axis
            c4 = (p2 / r2 ** 2 - p1 / r1 ** 2) / (r2 ** 2 - r1 ** 2)
            T[q] = 2 * (p1 / r1 ** 2 - c4 * r1 ** 2)
        return M, T


def debye_mu(g, f):
    return 1 + (g["mu_i"] - 1) / (1 + 1j * np.asarray(f) / g["f_r"])


def core_fit(ms, g, log=print, nf=34, fband=(1e3, 3e9), npole=14):
    """dL(jw) = L_inf + sum K_q/(jw + p_q), K_q, L_inf PSD; dT(jw) = T_inf + sum d_q p_q/(jw + p_q)."""
    M1, T1 = ms.solve(1.0)
    f = np.logspace(math.log10(fband[0]), math.log10(fband[1]), nf)
    dL, dT = [], []
    t0 = time.time()
    for fk in f:
        Mk, Tk = ms.solve(complex(debye_mu(g, fk)))
        dL.append(Mk - M1)
        dT.append(Tk - T1)
    dL, dT = np.array(dL), np.array(dT)
    w = 2 * math.pi * f
    p = 2 * math.pi * np.logspace(math.log10(fband[0]), math.log10(fband[1]), npole)
    basisL = np.hstack([np.ones((nf, 1)), 1 / (1j * w[:, None] + p[None, :])])
    basisT = np.hstack([np.ones((nf, 1)), p[None, :] / (1j * w[:, None] + p[None, :])])
    sc = 1 / np.linalg.norm(dL.reshape(nf, -1), axis=1)
    N = dL.shape[1]

    def lsq(basis, Y, s):
        A = np.vstack([basis.real * s[:, None], basis.imag * s[:, None]])
        B = np.vstack([Y.real * s[:, None], Y.imag * s[:, None]])
        return np.linalg.lstsq(A, B, rcond=None)[0]

    X = lsq(basisL, dL.reshape(nf, -1), sc).reshape(npole + 1, N, N)
    Xp = []
    for Kq in X:                                       # PSD projection (passivity)
        Kq = 0.5 * (Kq + Kq.T)
        ev, V = np.linalg.eigh(Kq)
        Xp.append((V * np.clip(ev, 0, None)) @ V.T)
    Xp = np.array(Xp)
    fitL = np.einsum("fq,qij->fij", basisL, Xp)
    errL = float(np.max(np.linalg.norm((fitL - dL).reshape(nf, -1), axis=1) * sc))
    scT = 1 / np.maximum(np.linalg.norm(dT.reshape(nf, -1), axis=1), 1e-30)
    D = lsq(basisT, dT.reshape(nf, -1), scT).reshape(npole + 1, *dT.shape[1:])
    fitT = np.einsum("fq,qij->fij", basisT, D)
    errT = float(np.max(np.linalg.norm((fitT - dT).reshape(nf, -1), axis=1) * scT))
    log(f"  core fit: {nf} complex solves {time.time() - t0:.0f} s; dL err {errL * 100:.2f} %, dT err {errT * 100:.2f} %"
        f"; dL(0)/L_air(diag) {np.trace(dL[0].real) / np.trace(M1):.2f}")
    return dict(p=p, L_inf=Xp[0], K=Xp[1:], T_inf=D[0], d=D[1:], errL=errL, errT=errT, f=f,
                dL_diag=np.array([np.trace(x) for x in dL]), M1=M1, T1=T1)


def gate_ms(log=print):
    g = dict(GEOM, rod=False)
    a = 11.25
    out = {}
    for d in (1.5, 5.0, 20.0):
        turns = [dict(coil=0, k=0, r=a, z=-d / 2), dict(coil=0, k=1, r=a, z=d / 2)]
        ms = MS(g, turns, [(-35, 35)], [0.0])
        M, T = ms.solve(1.0)
        ref = mutual(a * 1e-3, a * 1e-3, d * 1e-3)
        Tref = 2 * loop_Bz_axis(a * 1e-3, d / 2 * 1e-3)
        out[d] = dict(M_fd=float(M[0, 1]), M_ref=float(ref), rel=float(M[0, 1] / ref - 1),
                      T_rel=float(T[0].sum() / Tref - 1))
        log(f"G-MS d={d} mm: M_fd {M[0, 1] * 1e9:.3f} nH vs Maxwell {ref * 1e9:.3f}: {out[d]['rel'] * 100:+.2f} %;"
            f" axis field {out[d]['T_rel'] * 100:+.2f} %")
    return dict(cases=out, pass_=all(abs(v["rel"]) <= 0.02 and abs(v["T_rel"]) <= 0.02 for k, v in out.items() if k >= 5))


# ======================================================================================================
# 6. the ladder: netlist, MNA, trapezoidal transient, DC                                              [OC]
# ======================================================================================================
class Ladder:
    """nodes: coil chains + rod segments (+ source nodes); branches: turns (+ leads).
    feed: 'single' | 'end' | 'junction' | 'odd'; far ends grounded ('gnd') or open ('open')."""

    def __init__(self, g, turns, rods, es, core=None, feed="single", far="gnd", Rs=0.0, cap_map="mean",
                 targets=(), ms_T=None, lead_mm=None):
        self.g, self.turns, self.feed, self.Rs = g, turns, feed, Rs
        rw = g["wire_d"] / 2 * 1e-3
        nodes = {}

        def node(nm):
            if nm == "gnd":
                return -1
            if nm not in nodes:
                nodes[nm] = len(nodes)
            return nodes[nm]

        coils = sorted({t["coil"] for t in turns})
        self.coil_turns = {c: [i for i, t in enumerate(turns) if t["coil"] == c] for c in coils}
        br = []                                         # (a, b, turn index or None, sign, L_self, R0)
        sources = []                                    # (node, amplitude)
        hel = {}
        if feed == "single":
            chain = sorted(self.coil_turns[0], key=lambda i: turns[i]["z"])
            for n_, i in enumerate(chain):
                b = "gnd" if (n_ == len(chain) - 1 and far == "gnd") else f"n0.{n_ + 1}"
                br.append((node(f"n0.{n_}"), node(b), i, +1))
            sources.append(("n0.0", 1.0))
        else:
            A = sorted(self.coil_turns[0], key=lambda i: turns[i]["z"])          # left coil, -z ... junction
            B = sorted(self.coil_turns[1], key=lambda i: turns[i]["z"])          # junction ... +z
            if feed in ("end", "odd"):                  # +z progression in both; mirror handedness
                hel = {0: +1, 1: -1}
                for n_, i in enumerate(A):
                    br.append((node(f"a.{n_}"), node(f"a.{n_ + 1}"), i, hel[0] * (+1)))
                lead = (lead_mm if lead_mm is not None else (turns[B[0]]["z"] - turns[A[-1]]["z"])) * 1e-3
                Llead = 2e-7 * lead * (math.log(2 * lead / rw) - 0.75)
                br.append((node(f"a.{len(A)}"), node("b.0"), None, 0, Llead, RHO_CU * lead / (math.pi * rw ** 2)))
                for n_, i in enumerate(B):
                    last = n_ == len(B) - 1
                    b = ("gnd" if far == "gnd" and feed == "end" else f"b.{n_ + 1}") if last else f"b.{n_ + 1}"
                    br.append((node(f"b.{n_}"), node(b), i, hel[1] * (+1)))
                sources.append(("a.0", 1.0))
                if feed == "odd":
                    sources.append((f"b.{len(B)}", -1.0))
            elif feed == "junction":                    # outward from the junction; same handedness
                hel = {0: +1, 1: +1}
                for n_, i in enumerate(A[::-1]):        # progression -z
                    last = n_ == len(A) - 1
                    a_ = "j" if n_ == 0 else f"a.{n_}"
                    b = ("gnd" if far == "gnd" else f"a.{n_ + 1}") if last else f"a.{n_ + 1}"
                    br.append((node(a_), node(b), i, hel[0] * (-1)))
                for n_, i in enumerate(B):
                    last = n_ == len(B) - 1
                    a_ = "j" if n_ == 0 else f"b.{n_}"
                    b = ("gnd" if far == "gnd" else f"b.{n_ + 1}") if last else f"b.{n_ + 1}"
                    br.append((node(a_), node(b), i, hel[1] * (+1)))
                sources.append(("j", 1.0))
        self.hel = hel
        # rod nodes
        self.rod_nodes = []
        nseg = len(es["rod_segs"])
        for s, seg in enumerate(es["rod_segs"]):
            self.rod_nodes.append(node(f"rod{seg['rod']}.{seg['s']}"))
        # source nodes (Rs > 0 -> separate node behind Rs)
        self.src = []
        for nm, amp in sources:
            nt = node(nm)
            if Rs > 0:
                ns = node("src:" + nm)
                self.src.append(dict(node=ns, term=nt, amp=amp))
            else:
                self.src.append(dict(node=nt, term=nt, amp=amp))
        self.nodes = nodes
        nn, nb, ns_ = len(nodes), len(br), len(self.src)
        self.nn, self.nb, self.ns = nn, nb, ns_
        # branch parameters
        a_m = turns[0]["r"] * 1e-3
        R0, pk, Rk, self.skin_err = skin_fit(rw, 2 * math.pi * a_m)
        Ls = self_L_ext(a_m, rw)
        tix = np.array([b[2] if b[2] is not None else -1 for b in br])
        sgn = np.array([b[3] for b in br], float)
        self.tix, self.sgn = tix, sgn
        isturn = tix >= 0
        self.isturn = isturn
        Lb = np.zeros((nb, nb))
        R0b = np.zeros(nb)
        zt = np.array([t["z"] for t in turns]) * 1e-3
        rt = np.array([t["r"] for t in turns]) * 1e-3
        ti = tix[isturn]
        bi = np.where(isturn)[0]
        dz = zt[ti][:, None] - zt[ti][None, :]
        with np.errstate(divide="ignore", invalid="ignore"):
            Mt = mutual(rt[ti][:, None], rt[ti][None, :], dz)
        np.fill_diagonal(Mt, Ls)
        Lb[np.ix_(bi, bi)] = Mt * np.outer(sgn[bi], sgn[bi])
        R0b[bi] = R0
        for k, b in enumerate(br):
            if b[2] is None:
                Lb[k, k] = b[4]
                R0b[k] = b[5]
        self.L_air = Lb.copy()
        self.relax = []                                 # (p, K (nb x nb) or diag vector, d (targets x nb) or None)
        for p_, r_ in zip(pk, Rk):
            if r_ > 0:
                self.relax.append((p_, np.where(isturn, r_, 0.0), None))
        # core
        S = np.zeros((nb, len(turns)))                 # branch <- turn map with sign
        S[bi, ti] = sgn[bi]
        self.S = S
        targets = list(targets)
        Tair = np.zeros((len(targets), len(turns)))
        for q, ztq in enumerate(targets):
            Tair[q] = loop_Bz_axis(rt, zt - ztq * 1e-3)
        self.T_static = Tair @ S.T                      # field per branch current (targets x nb)
        self.core_relax = []
        if core is not None and core.get("static") is not None:
            dL, dT = core["static"]
            Lb += S @ dL @ S.T
            self.T_static = self.T_static + dT @ S.T
        elif core is not None:
            Lb += S @ core["L_inf"] @ S.T
            self.T_static = self.T_static + core["T_inf"].real @ S.T
            for q in range(len(core["p"])):
                self.relax.append((core["p"][q], S @ core["K"][q] @ S.T, core["d"][q].real @ S.T))
        self.Lb, self.R0b = Lb, R0b
        ev = np.linalg.eigvalsh(0.5 * (Lb + Lb.T))
        self.L_min_eig = float(ev.min())
        self.L_pd = bool(ev.min() > 0)
        # capacitance: conductor potentials = P @ node voltages
        Cm = es["C"]
        K = Cm.shape[0]
        P = np.zeros((K, nn))
        name_ix = {nm: k for k, nm in enumerate(es["names"])}
        for k, b in enumerate(br):
            if b[2] is None:
                continue
            t = turns[b[2]]
            c = name_ix[f"T{t['coil']}.{t['k']}"]
            ends = [x for x in (b[0], b[1]) if x >= 0]
            if cap_map == "mean":
                for x in (b[0], b[1]):
                    if x >= 0:
                        P[c, x] += 0.5
            else:                                       # 'end': the downstream end node (ground if grounded)
                if b[1] >= 0:
                    P[c, b[1]] = 1.0
        for s, seg in enumerate(es["rod_segs"]):
            P[name_ix[f"R{seg['rod']}.{seg['s']}"], self.rod_nodes[s]] = 1.0
        self.P = P
        Cn = P.T @ Cm @ P
        Gn = np.zeros((nn, nn))
        rr = g["r_rod"] * 1e-3
        for s in range(nseg - 1):
            s0, s1 = es["rod_segs"][s], es["rod_segs"][s + 1]
            if s0["rod"] != s1["rod"]:
                continue
            dzs = 0.5 * ((s0["z1"] - s0["z0"]) + (s1["z1"] - s1["z0"])) * 1e-3
            Gs = math.pi * rr ** 2 / (g["rod_rho"] * dzs)
            Cs = EPS0 * g["rod_eps_bulk"] * math.pi * rr ** 2 / dzs
            u, v = self.rod_nodes[s], self.rod_nodes[s + 1]
            for (x, y, val) in ((u, u, 1), (v, v, 1), (u, v, -1), (v, u, -1)):
                Gn[x, y] += val * Gs
                Cn[x, y] += val * Cs
        for sd in self.src:
            if sd["node"] != sd["term"]:
                G = 1.0 / Rs
                for (x, y, val) in ((sd["node"], sd["node"], 1), (sd["term"], sd["term"], 1),
                                    (sd["node"], sd["term"], -1), (sd["term"], sd["node"], -1)):
                    Gn[x, y] += val * G
        self.Cn, self.Gn = Cn, Gn
        Bi = np.zeros((nn, nb))                         # +1 where the branch current leaves the node
        for k, b in enumerate(br):
            if b[0] >= 0:
                Bi[b[0], k] += 1
            if b[1] >= 0:
                Bi[b[1], k] -= 1
        self.Bi, self.br = Bi, br
        self.n = nn + nb + ns_
        # row kinds
        kind = []
        srcnodes = {sd["node"] for sd in self.src}
        for x in range(nn):
            if not np.any(Cn[x]):
                kind.append("alg")
            elif x in srcnodes:
                kind.append("be")
            else:
                kind.append("trap")
        kind += ["trap"] * nb + ["alg"] * ns_
        self.kind = np.array(kind)

    # --- assembly ---
    def _AE(self):
        nn, nb, ns_ = self.nn, self.nb, self.ns
        n = self.n
        E = np.zeros((n, n))
        A = np.zeros((n, n))
        E[:nn, :nn] = self.Cn
        A[:nn, :nn] = -self.Gn
        A[:nn, nn:nn + nb] = -self.Bi
        for s, sd in enumerate(self.src):
            A[sd["node"], nn + nb + s] += 1.0           # source current enters its node
            A[nn + nb + s, sd["node"]] = 1.0            # row: v_node - amp Vs(t) = 0
        E[nn:nn + nb, nn:nn + nb] = self.Lb
        A[nn:nn + nb, :nn] = self.Bi.T
        A[nn:nn + nb, nn:nn + nb] = -np.diag(self.R0b)
        return E, A

    def transient(self, vs, t_end, h, rec_every=1):
        """vs(t) -> source waveform (V, multiplied by each source's amplitude). Records v, i, i_s, field."""
        nn, nb, ns_ = self.nn, self.nb, self.ns
        E, A = self._AE()
        th = np.where(self.kind == "trap", 0.5, 1.0)
        ee = np.where(self.kind == "alg", 0.0, 1.0)
        phi = np.where(self.kind == "trap", 0.5, 0.0)
        alpha = np.array([(1 - h * p / 2) / (1 + h * p / 2) for p, _, _ in self.relax])
        beta = np.array([(h * p / 2) / (1 + h * p / 2) for p, _, _ in self.relax])
        Kbar = np.zeros((nb, nb))
        for q, (p, K, d) in enumerate(self.relax):
            Kq = np.diag(K) if K.ndim == 1 else K
            Kbar += (1 - beta[q]) * Kq
        M = ee[:, None] * E / h - th[:, None] * A
        M[nn:nn + nb, nn:nn + nb] += 0.5 * Kbar
        lu = sla.lu_factor(M)
        amp = np.array([sd["amp"] for sd in self.src])
        bvec = lambda t: np.concatenate([np.zeros(nn + nb), -amp * vs(t)])
        x = np.zeros(self.n)
        W = [np.zeros(nb) for _ in self.relax]
        nsteps = int(math.ceil(t_end / h))
        nrec = nsteps // rec_every + 1
        rec_t = np.zeros(nrec)
        rec_x = np.zeros((nrec, self.n), np.float64)
        ntg = self.T_static.shape[0]
        rec_B = np.zeros((nrec, ntg, len(self.coil_turns)))
        coil_mask = {c: np.isin(self.tix, ix) & self.isturn for c, ix in self.coil_turns.items()}

        def field(xv, Wl):
            i = xv[nn:nn + nb]
            out = np.zeros((ntg, len(coil_mask)))
            for c, m in coil_mask.items():
                bsum = self.T_static[:, m] @ i[m]
                for q, (p, K, d) in enumerate(self.relax):
                    if d is not None:
                        bsum = bsum + d[:, m] @ Wl[q][m]
                out[:, c] = bsum
            return out

        def relax_term(i, Wl):
            s = np.zeros(nb)
            for q, (p, K, d) in enumerate(self.relax):
                diff = i - Wl[q]
                s += K * diff if K.ndim == 1 else K @ diff
            return s

        def relax_known(i, Wl):
            s = np.zeros(nb)
            for q, (p, K, d) in enumerate(self.relax):
                u = alpha[q] * Wl[q] + beta[q] * i
                s += K * u if K.ndim == 1 else K @ u
            return s

        k_rec = 0
        rec_t[0] = 0.0
        rec_x[0] = x
        rec_B[0] = field(x, W)
        t = 0.0
        b0 = bvec(0.0)
        for st in range(1, nsteps + 1):
            t1 = st * h
            b1 = bvec(t1)
            i0 = x[nn:nn + nb]
            f0 = A @ x + b0
            f0[nn:nn + nb] -= relax_term(i0, W)
            rhs = ee * (E @ x) / h + th * b1 + phi * f0
            rhs[nn:nn + nb] += 0.5 * relax_known(i0, W)
            x1 = sla.lu_solve(lu, rhs)
            i1 = x1[nn:nn + nb]
            W = [alpha[q] * W[q] + beta[q] * (i0 + i1) for q in range(len(self.relax))]
            x, b0, t = x1, b1, t1
            if st % rec_every == 0:
                k_rec += 1
                rec_t[k_rec] = t
                rec_x[k_rec] = x
                rec_B[k_rec] = field(x, W)
        rec_t, rec_x, rec_B = rec_t[:k_rec + 1], rec_x[:k_rec + 1], rec_B[:k_rec + 1]
        return dict(t=rec_t, v=rec_x[:, :nn], i=rec_x[:, nn:nn + nb], i_s=rec_x[:, nn + nb:], B=rec_B)

    def dc(self, Vdc=1.0, T_dc=None):
        """static solution (w = i, caps open): node voltages, branch currents, field per coil (G-NULL)."""
        nn, nb, ns_ = self.nn, self.nb, self.ns
        E, A = self._AE()
        A = A.copy()
        for x in self.rod_nodes:
            A[x, x] -= 1e-9                              # leak: the floating rods
        amp = np.array([sd["amp"] for sd in self.src])
        b = np.concatenate([np.zeros(nn + nb), -amp * Vdc])
        xv = np.linalg.solve(A, -b)
        i = xv[nn:nn + nb]
        T = self.T_static.copy()
        for p, K, d in self.relax:
            if d is not None:
                T = T + d                               # w = i at DC
        out = {c: T[:, np.isin(self.tix, ix) & self.isturn] @ i[np.isin(self.tix, ix) & self.isturn]
               for c, ix in self.coil_turns.items()}
        return xv, out

    # --- the same ladder as an ngspice deck (for G-SPICE) ---
    def spice_deck(self, tr, t_end, h, path):
        nn, nb = self.nn, self.nb
        inv = {v: k for k, v in self.nodes.items()}
        nm = lambda x: "0" if x < 0 else f"N{x}"
        L = []
        L.append("* edge_coil ladder (G-SPICE)")
        for k, b in enumerate(self.br):
            a_, b_ = nm(b[0]), nm(b[1])
            mids = [f"X{k}_{j}" for j in range(len(self.relax) + 1)]
            L.append(f"L{k} {a_} {mids[0]} {self.Lb[k, k]:.9e}")
            L.append(f"R0_{k} {mids[0]} {mids[1] if self.relax else b_} {max(self.R0b[k], 1e-6):.9e}")
            for q, (p, K, d) in enumerate(self.relax):
                if K.ndim != 1:
                    raise ValueError("G-SPICE deck supports the skin network and static mu only")
                n1 = mids[q + 1]
                n2 = mids[q + 2] if q + 2 < len(mids) else b_
                if q + 1 == len(mids) - 1:
                    n2 = b_
                Rq = K[k]
                if Rq <= 0:
                    L.append(f"Rz{k}_{q} {n1} {n2} 1e-9")
                    continue
                L.append(f"Rf{k}_{q} {n1} {n2} {Rq:.9e}")
                L.append(f"Lf{k}_{q} {n1} {n2} {Rq / p:.9e}")
        kk = 0
        for k1 in range(nb):
            for k2 in range(k1 + 1, nb):
                c = self.Lb[k1, k2] / math.sqrt(self.Lb[k1, k1] * self.Lb[k2, k2])
                if abs(c) > 1e-12:
                    L.append(f"K{kk} L{k1} L{k2} {c:.12f}")
                    kk += 1
        Cn, Gn = self.Cn, self.Gn
        cc = 0
        for x in range(nn):
            rowsum = Cn[x].sum()
            if rowsum > 1e-18:
                L.append(f"Cg{cc} {nm(x)} 0 {rowsum:.9e}")
                cc += 1
            for y in range(x + 1, nn):
                if abs(Cn[x, y]) > 1e-20:
                    L.append(f"Cm{cc} {nm(x)} {nm(y)} {-Cn[x, y]:.9e}")
                    cc += 1
                if Gn[x, y] < 0:
                    L.append(f"Gr{cc} {nm(x)} {nm(y)} {-1 / Gn[x, y]:.9e}")
                    cc += 1
        sd = self.src[0]
        T = tr / 0.5903
        L.append(f"Vs {nm(sd['node'])} 0 PWL(" + " ".join(
            f"{t:.6e} {sd['amp'] * 0.5 * (1 - math.cos(math.pi * min(t, T) / T)):.9f}"
            for t in np.linspace(0, T, 41)) + f" {t_end:.6e} {sd['amp']:.9f})")
        L.append(f".tran {h:.6e} {t_end:.6e} 0 {h:.6e}")
        L.append(".options method=trap reltol=1e-6 abstol=1e-12 vntol=1e-9 chgtol=1e-18")
        L.append(".control\nrun\nwrdata " + path + ".dat i(Vs)\n.endc\n.end")
        open(path + ".cir", "w").write("\n".join(L) + "\n")


# ======================================================================================================
# 7. edge, readouts                                                                                   [OC/IR]
# ======================================================================================================
def edge(tr):
    """raised-cosine edge, 10-90 % = tr; returns vs(t) and its 50 % time."""
    T = tr / 0.5903
    return (lambda t: 0.5 * (1 - math.cos(math.pi * t / T)) if t < T else 1.0), 0.5 * T


def ideal_line(g, es, turns, coil_ix=None, mu_eff=1.0, rod_grounded=False):
    """§3 idealisation: Z0 = n sqrt(mu0 mu A/C'), tau = l n sqrt(mu0 mu A C'), C' from the Maxwell matrix (turns at
    1 V, the rod floating or grounded, can 0)."""
    C = es["C"]
    names = es["names"]
    T = [k for k, nm in enumerate(names) if nm.startswith("T") and (coil_ix is None or nm.startswith(f"T{coil_ix}."))]
    Rr = [k for k, nm in enumerate(names) if nm.startswith("R")]
    if rod_grounded or not Rr:
        Ctot = C[np.ix_(T, T)].sum()
    else:
        # rod floating: Schur complement (rod charge zero)
        Ctt = C[np.ix_(T, T)]
        Ctr = C[np.ix_(T, Rr)]
        Crr = C[np.ix_(Rr, Rr)]
        Ctot = (Ctt - Ctr @ np.linalg.solve(Crr, Ctr.T)).sum()
    N = len(T)
    ell = N * g["pitch"] * 1e-3
    a = turns[0]["r"] * 1e-3
    A = math.pi * a ** 2
    n = N / ell
    Cp = Ctot / ell
    return dict(C_total=float(Ctot), Cp=float(Cp), Z0=float(n * math.sqrt(MU0 * mu_eff * A / Cp)),
                tau=float(ell * n * math.sqrt(MU0 * mu_eff * A * Cp)), L_total=float(MU0 * mu_eff * n ** 2 * A * ell))


def alpha_of(es, coil_ix=0):
    """alpha = sqrt(C_g/C_s): C_g = all turns at 1 V (rod, can 0); C_s = series chain of the adjacent-turn caps."""
    C = es["C"]
    names = es["names"]
    T = [k for k, nm in enumerate(names) if nm.startswith(f"T{coil_ix}.")]
    T = sorted(T, key=lambda k: int(names[k].split(".")[1]))
    Cg = C[np.ix_(T, T)].sum()
    Ctt = np.array([-C[T[j], T[j + 1]] for j in range(len(T) - 1)])
    Cs = 1.0 / np.sum(1.0 / Ctt)
    return dict(C_g=float(Cg), C_s=float(Cs), C_tt_mean=float(Ctt.mean()), alpha=float(math.sqrt(Cg / Cs)))


def tau_from_current(t, i, t50, V=1.0, tau0=None, tr=None):
    """ideal step, far end grounded: plateau I, then ~3I after 2 tau. Returns Z0 = V/I, tau, flatness ratio."""
    tau = tau0
    I = None
    for _ in range(6):
        w = (t > t50 + max(0.4 * tau, 1.5 * (tr or 0))) & (t < t50 + 1.6 * tau)
        if w.sum() < 3:
            w = (t > t50 + 0.4 * tau) & (t < t50 + 1.6 * tau)
        I = float(np.median(i[w]))
        after = np.where((t > t50 + 0.5 * tau) & (i > 2 * I))[0]
        if not len(after):
            break
        tnew = 0.5 * (t[after[0]] - t50)
        if abs(tnew - tau) < 1e-3 * tau:
            tau = tnew
            break
        tau = tnew
    def at(x):
        return float(np.interp(t50 + x * tau, t, i))
    return dict(Z0=V / I, tau=tau, I_plateau=I, flat=at(1.6) / at(0.4), i_04=at(0.4), i_16=at(1.6))


def tdr(t, vt, t50, Rs, Vs=1.0, tau0=None):
    """50 Ohm TDR, far end grounded: Z(t) = Rs (1 + rho)/(1 - rho), rho = (v - Vs/2)/(Vs/2); tau from the drop."""
    Vi = Vs / 2
    rho = (vt - Vi) / Vi
    Z = Rs * (1 + rho) / np.clip(1 - rho, 1e-12, None)
    tau = tau0
    Z0 = None
    for _ in range(6):
        w = (t > t50 + 0.4 * tau) & (t < t50 + 1.6 * tau)
        Z0 = float(np.median(Z[w]))
        vpl = float(np.median(vt[w]))
        after = np.where((t > t50 + 0.5 * tau) & (vt < 0.5 * vpl))[0]
        if not len(after):
            break
        tnew = 0.5 * (t[after[0]] - t50)
        if abs(tnew - tau) < 1e-3 * tau:
            tau = tnew
            break
        tau = tnew
    return dict(Z0=Z0, tau=tau, L_seen=Z0 * tau, C_seen=tau / Z0)
