#!/usr/bin/env python3
"""sim/ah_null.py -- where the AH's magnetic null sits in the locked hub, its gradient, and the checks around it.

The pair as locked (presets/hub-locked.json AH, AH_seat, shaft, vessel): two 160-turn coils in variant (a)'s window,
r 8.25-11.45 mm, |z| 31.35-71.35 mm, wound to oppose, each on a Fair-Rite 4077484611 rod of 77 MnZn (12.3 mm across,
|z| 30.7-72.0) inside a G-10 former; PEEK seats to the 50 mm vessel; the split shaft's flanges r 32 x 8 mm at
|z| 72-80, non-magnetic as recorded. The currents are the magnetic pump's at the pick
(sim/ah-steady-cusp-findings.md): with the 22 mF bypass (PROPOSED) 290-308 A-turns per coil, the two within 17;
without it each coil carries its branch's 139-449 A-turns at 120 Hz. sim/ah_steady_cusp_results.json keeps only
their statistics, so the waveforms are regenerated here exactly as sim/ah_steady_cusp.py runs them (ngspice) and
checked against those statistics (gate G-WAVE).

Naming: "top" is the coil above (z > 0), "bottom" the coil below. The record puts side A below and side B above
(README.md, docs/ledger/DCCREG-design-ledger.md §2), and the deck's AHt is side A's coil, AHb side B's
(sim/ah-steady-cusp-findings.md, naming note): so top = AHb, bottom = AHt.

Model:
  field      axisymmetric magnetostatics in psi = r A_phi: -div((nu/r) grad psi) = J_phi, psi = 0 on the axis and on
             a far boundary at 2 m [OC]; sim/edge_coil.py's finite-volume operator (fv_laplacian 'ms', exact radial
             weights) on a graded grid with every material edge on a node                                    [IR]
  sources    each coil a uniform current density over its window (the turns' layout is not modelled), loaded as
             the exact integrals of the nodal hat functions                                                   [IR]
  ferrite    linear, mu_r 2000 (presets/electromagnets-RA.json AH_rod mu_i, datasheet-class), no saturation; the
             former, seats, vessel, retainer and a non-magnetic shaft are mu_r 1                         [IR] / [OC]
  steel      the shaft halves as mild steel when asked: linear mu_r 300-1000, r 15 mm from |z| 72 to 300 mm with
             the flanges r 32 x 8 mm at |z| 72-80                                                             [IR]
  readouts   B_z on the axis from psi = (B_z/2) r^2 + c r^4 at the first two radial nodes; B_r = -(1/r) dpsi/dz
             by central differences; |B| per cell in the ferrite and steel; the null by Newton on a cubic spline
             of B_z(z) inside the vessel                                                                      [OC]
  linearity  every field is NI_top x (the top coil's unit field) - NI_bottom x (the bottom's): the coils oppose;
             the 120 Hz cycle is quasi-static (the MnZn skin depth at 120 Hz is about 2 m)                    [OC]
Sign: positive NI_top circulates so that B_z > 0 inside the top coil, the bottom coil the other way; the record's
winding sense (sim/ah-steady-cusp-findings.md, the winding sense) sets the actual polarity, not the magnitudes.
Gates: G-AIR (air-cored coil against the closed form, <= 1 %), G-MESH (h 0.5 / 0.25 / 0.125 mm, < 2 % each step),
G-SYM (the balanced null at z = 0), G-DIV (radial gradient = -G/2), G-FAR (boundary at 1 m against 2 m), G-WAVE (the
regenerated waveforms against the recorded statistics).
Usage: python3 sim/ah_null.py [--h 0.25] [--no-figure]  -> sim/ah_null_results.json, docs/figures/ah-null.png
"""
import argparse
import json
import math
import os
import subprocess
import sys
import tempfile
import time
from multiprocessing import Pool

sys.dont_write_bytecode = True                        # leave sim/__pycache__ as it is

import numpy as np                                    # noqa: E402
import scipy.sparse.linalg as spla                    # noqa: E402
from scipy.interpolate import CubicSpline             # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
from edge_coil import MU0, fv_laplacian, lap_from_edges   # noqa: E402  the repo's axisymmetric FV operator [OC]
import ah_steady_cusp as AS                               # noqa: E402  the bypass's ESR, as recorded
import magnetic_doubler as MD                             # noqa: E402  the pump's deck; AH r160; AT_ROD_LIMIT
import rotor_parts_duty as RP                             # noqa: E402  the pick, as sim/ah_steady_cusp.py runs it

RESULTS = os.path.join(HERE, "ah_null_results.json")
FIGURE = os.path.join(ROOT, "docs", "figures", "ah-null.png")


def _load(path):
    with open(path) as fh:
        return json.load(fh)


# ======================================================================================================
# 0. inputs, every one from its file
# ======================================================================================================
SRC_HUB = "presets/hub-locked.json"
SRC_REG = "presets/electromagnets-RA.json"
SRC_CUSP = "sim/ah_steady_cusp_results.json"
HUB = _load(os.path.join(ROOT, SRC_HUB))
REG = _load(os.path.join(ROOT, SRC_REG))
CUSP = _load(os.path.join(ROOT, SRC_CUSP))
EMREG = _load(os.path.join(HERE, "em_register_results.json"))

_ah, _seat, _sh = HUB["AH"]["value"], HUB["AH_seat"]["value"], HUB["shaft"]["value"]
_ves, _wall = HUB["vessel"]["value"], HUB["vessel_wall"]["value"]
_rod = REG["rotor"]["AH_rod"]["value"]

GEO = dict(                                           # mm                                                  [IR]
    rod_r=0.5 * _ah["core"]["d_mm"],                  # 6.15: the rod, 12.3 mm across (AH.core)
    rod_z=tuple(_ah["core"]["absz_mm"]),              # |z| 30.7-72.0 (AH.core)
    coil_r=tuple(_ah["coil"]["r_mm"]),                # 8.25-11.45 (AH.coil)
    coil_z=tuple(_ah["coil"]["absz_mm"]),             # |z| 31.35-71.35 (AH.coil)
    former_r=(0.5 * _ah["former"]["id_mm"], 0.5 * _ah["former"]["od_mm"]),   # G-10: mu_r 1, not a part here
    seat_z=tuple(_seat["absz_mm"]),                   # PEEK |z| 25.0-30.7: mu_r 1
    ves_r=0.5 * _ves["od_mm"],                        # 25.0
    ves_r_in=0.5 * _ves["od_mm"] - _wall["t_mm"],     # 23.5
    shaft_r=0.5 * _sh["d_mm"],                        # 15.0 (the shaft, 30 mm across)
    flange_r=_sh["flange_r_mm"],                      # 32.0
    flange_z=tuple(_sh["flange_absz_mm"]),            # |z| 72-80
)
TURNS = int(_ah["coil"]["turns"])                     # 160
SHAFT_MAGNETIC = bool(_sh["magnetic"])                # False: the record
MU_ROD = float(_rod["mu_i"])                          # 2000 (the register tags it [RH] until the datasheet is read)
BSAT_100C = float(_rod["Bsat_100C_T"])                # 0.38 T at 100 C (register)
BSAT_25C = 0.49                                       # T at 25 C: not in the repo; Fair-Rite 77 datasheet-class [IR]
B_LIMIT_REG = 0.30                                    # T: G-AH-SAT's limit (sim/em-register-predictions.md:74)
AT_ROD_LIMIT_REC = float(MD.AT_ROD_LIMIT)             # 601 A-turns (sim/magnetic_doubler.py:51: 1022 x 0.30 / 0.51)
L_AH_REC = float(MD.AH["r160"]["L"])                  # 1.01 mH (sim/magnetic_doubler.py AH r160, [RH] N^2 scaling)
STEEL_MU = (300.0, 1000.0)                            # mild steel, linear [IR]
Z_STEEL_END = 300.0                                   # mm: the steel shaft halves modelled out to |z| 300 [IR]
GAP_STEEL = 1.0                                       # mm: a non-magnetic spacer at the rod's outer end, as the
                                                      # register's 1 mm PEEK cap (sim/em-register-findings.md §2) [IR]
GAP_SMALL = 0.1                                       # mm: a small contact-gap difference [IR]
MU_AUSTENITIC = (1.05, 2.0)                           # "non-magnetic" stainless: annealed / heavily cold-worked
                                                      # austenitic class [RH]
ROD_END_BAND = 1.0                                    # mm: the rod's bulk leaves out 1 mm at each end, where the
                                                      # linear model's corner peak grows as the cells shrink [IR]
SHIFT = 0.5                                           # mm: the axial misplacement studied [IR]
IMBALANCE = (0.0, 5.0, 10.0, 17.0, 34.0)              # A-turns, top minus bottom (the brief's list)
DECK_SIDE = {"AHt": "bottom", "AHb": "top"}           # side A (AHt) below, side B (AHb) above (see the docstring)


def _cusp_row(c_mf):
    return [x for x in CUSP["rows"] if abs(x["C_byp_mF"] - c_mf) < 1e-9][0]


ROW0, ROW22 = _cusp_row(0.0), _cusp_row(22.0)
NI_MEAN = float(round(0.5 * (ROW22["top"]["AT_mean"] + ROW22["bottom"]["AT_mean"])))   # 300 A-turns (22 mF row)
DNI_BYP = ROW22["dAT_max"]                                                               # 17.4 A-turns
NI_PEAK = ROW0["top"]["AT_max"]                                                          # 449 A-turns (no bypass)

# grid: uniform near region, graded beyond                                                             [IR]
H_PROD = 0.25                         # mm, the production cell (G-MESH)
FAR = 2000.0                          # mm, the far boundary, psi = 0 (G-FAR)
R_NEAR, Z_NEAR = 34.0, 82.0           # mm: uniform cells out to here
H_MID, GROW, H_FAR = 2.0, 1.15, 40.0  # graded to 2 mm cells out to |z| 300, then to 40 mm


# ======================================================================================================
# 1. the grid [IR] and the solve [OC]
# ======================================================================================================
def _uniform(a, b, h):
    cells = max(1, int(math.ceil((b - a) / h - 1e-9)))
    return a + (b - a) * np.arange(1, cells + 1) / cells


def _graded(a, b, h0, cap):
    steps, x, hk = [], a, h0
    while x < b - 1e-12:
        hk = min(hk * GROW, cap)
        steps.append(hk)
        x += hk
    steps = np.array(steps) * (b - a) / sum(steps)
    return a + np.cumsum(steps)


def _axis(breaks, h, tail):
    """nodes (mm): uniform cells of at most h between the breakpoints, then graded segments (end, cap)."""
    pts = [np.array([breaks[0]])] + [_uniform(a, b, h) for a, b in zip(breaks[:-1], breaks[1:])]
    x, hk = breaks[-1], h
    for b, cap in tail:
        seg = _graded(x, b, hk, cap)
        pts.append(seg)
        hk, x = seg[-1] - seg[-2], b
    return np.concatenate(pts)


def case(**kw):
    """a configuration; defaults are the record: both rods mu 2000, non-magnetic shaft, nothing misplaced."""
    cs = dict(mu_top=MU_ROD, mu_bot=MU_ROD, steel_top=None, steel_bot=None, gap_top=0.0, gap_bot=0.0,
              coil_shift=0.0, rod_shift=0.0, air=False)
    cs.update(kw)
    return cs


def parts(cs):
    """the magnetic parts [(name, r_max, z_lo, z_hi, mu)] and the two windows (r1, r2, z1, z2), mm."""
    (z0, z1), r0 = GEO["rod_z"], GEO["rod_r"]
    (a1, a2), (b1, b2) = GEO["coil_r"], GEO["coil_z"]
    s_rod, s_coil = cs["rod_shift"], cs["rod_shift"] + cs["coil_shift"]          # the top side, outward (+z)
    mag = [] if cs["air"] else [("rod_top", r0, z0 + s_rod, z1 + s_rod, cs["mu_top"]),
                                ("rod_bot", r0, -z1, -z0, cs["mu_bot"])]
    fz0, fz1 = GEO["flange_z"]
    for side, mu, gap in ((+1, cs["steel_top"], cs["gap_top"]), (-1, cs["steel_bot"], cs["gap_bot"])):
        if mu:
            tag = "top" if side > 0 else "bot"
            for nm, rr, za, zb in (("flange", GEO["flange_r"], fz0 + gap, fz1),
                                   ("shaft", GEO["shaft_r"], fz0 + gap, Z_STEEL_END)):
                lo, hi = sorted((side * za, side * zb))
                mag.append((f"{nm}_{tag}", rr, lo, hi, float(mu)))
    return mag, (a1, a2, b1 + s_coil, b2 + s_coil), (a1, a2, -b2, -b1)


def _breaks():
    """one breakpoint set for every case (each side mirrored), so every comparison shares one grid."""
    (z0, z1), (b1, b2), (fz0, fz1) = GEO["rod_z"], GEO["coil_z"], GEO["flange_z"]
    rb = {0.0, 5.0, 10.0, 20.0, GEO["ves_r_in"], GEO["ves_r"], GEO["rod_r"], *GEO["coil_r"], GEO["shaft_r"],
          GEO["flange_r"], R_NEAR}
    zb = {0.0, 5.0, 10.0, 20.0, GEO["ves_r_in"], GEO["seat_z"][0], z0, z1, b1, b2, z0 + SHIFT, z1 + SHIFT,
          b1 + SHIFT, b2 + SHIFT, fz0, fz0 + GAP_SMALL, fz0 + GAP_STEEL, fz1, Z_NEAR}
    return sorted(x for x in rb if x <= R_NEAR), sorted(x for x in zb if x <= Z_NEAR)


def _hat(x, lo, hi):
    """the integral over [lo, hi] of every node's hat function on the nodes x."""
    w = np.zeros(len(x))
    for k in np.where((x[1:] > lo) & (x[:-1] < hi))[0]:
        a, b, span = max(lo, x[k]), min(hi, x[k + 1]), x[k + 1] - x[k]
        w[k] += ((x[k + 1] - a) ** 2 - (x[k + 1] - b) ** 2) / (2 * span)
        w[k + 1] += ((b - x[k]) ** 2 - (a - x[k]) ** 2) / (2 * span)
    return w


class Sol:
    """psi (Wb, nodes x nodes) per ampere-turn of each coil, both circulating +phi; the grid in mm."""

    def __init__(self, cs, h=H_PROD, far=FAR):
        t0 = time.time()
        self.cs, self.h, self.far = cs, h, far
        rb, zb = _breaks()
        self.r = _axis(rb, h, [(far, H_FAR)])
        zp = _axis(zb, h, [(Z_STEEL_END, H_MID), (far, H_FAR)])
        self.z = np.concatenate([-zp[::-1], zp[1:]])
        self.j0 = len(zp) - 1                                                  # the node at z = 0
        self.mag, self.win_t, self.win_b = parts(cs)
        rc, zc = 0.5 * (self.r[:-1] + self.r[1:]), 0.5 * (self.z[:-1] + self.z[1:])
        self.RC, self.ZC = np.meshgrid(rc, zc, indexing="ij")
        self.mu = np.ones(self.RC.shape)
        self.masks = {}
        for nm, rr, za, zb_, mu in self.mag:
            m = (self.RC <= rr) & (self.ZC >= za) & (self.ZC <= zb_)
            self.mu[m] = mu
            self.masks[nm] = m
        rows, cols, vals, _ = fv_laplacian(self.r * 1e-3, self.z * 1e-3, 1.0 / (MU0 * self.mu), "ms")
        nr, nz = len(self.r), len(self.z)
        lap = lap_from_edges(nr * nz, rows, cols, vals)
        R, Z = np.meshgrid(self.r, self.z, indexing="ij")
        free = np.where(~((R == 0) | (R == self.r[-1]) | (Z == self.z[0]) | (Z == self.z[-1])).ravel())[0]
        lu = spla.splu(lap[free][:, free].tocsc(), permc_spec="MMD_AT_PLUS_A")
        self.load, self.psi = {}, {}
        for nm, (a1, a2, b1, b2) in (("top", self.win_t), ("bot", self.win_b)):
            jd = 1.0 / ((a2 - a1) * (b2 - b1) * 1e-6)                          # A/m^2 per ampere-turn
            f = jd * np.outer(_hat(self.r * 1e-3, a1 * 1e-3, a2 * 1e-3), _hat(self.z * 1e-3, b1 * 1e-3, b2 * 1e-3))
            p = np.zeros(nr * nz)
            p[free] = lu.solve(f.ravel()[free])
            self.load[nm], self.psi[nm] = f, p.reshape(nr, nz)
        # a uniform 1 T axial field from far away: psi = B r^2 / 2 on the far boundary, no sources            [OC]
        bnd = np.setdiff1d(np.arange(nr * nz), free)
        pb = 0.5 * (R.ravel()[bnd] * 1e-3) ** 2
        p = np.zeros(nr * nz)
        p[bnd], p[free] = pb, lu.solve(-(lap[free][:, bnd] @ pb))
        self.psi["ext"] = p.reshape(nr, nz)
        self.nodes, self.secs = nr * nz, time.time() - t0

    # ---------------- readouts [OC] ----------------
    def combo(self, ni_top, ni_bot):
        """psi of the pair: the bottom coil runs the other way (anti-Helmholtz)."""
        return ni_top * self.psi["top"] - ni_bot * self.psi["bot"]

    def axis_bz(self, psi):
        """B_z on the axis (T) at every z node, from psi = (B_z/2) r^2 + c r^4 near the axis."""
        r1, r2 = self.r[1] * 1e-3, self.r[2] * 1e-3
        p1, p2 = psi[1], psi[2]
        c4 = (p2 / r2 ** 2 - p1 / r1 ** 2) / (r2 ** 2 - r1 ** 2)
        return 2 * (p1 / r1 ** 2 - c4 * r1 ** 2)

    def mid_plane(self, psi):
        """(B_r, B_z) on the z = 0 plane at the r nodes (T)."""
        j, rr, zz = self.j0, self.r * 1e-3, self.z * 1e-3
        dpz = (psi[:, j + 1] - psi[:, j - 1]) / (zz[j + 1] - zz[j - 1])
        dpr = np.gradient(psi[:, j], rr)
        br, bz = np.zeros(len(rr)), np.zeros(len(rr))
        br[1:], bz[1:] = -dpz[1:] / rr[1:], dpr[1:] / rr[1:]
        bz[0] = self.axis_bz(psi)[j]
        return br, bz

    def cells(self, psi):
        """cell-centred (B_r, B_z) (T): B_z exact for a uniform B_z across the cell, dpsi/dz interpolated in r^2."""
        rr, zz = self.r * 1e-3, self.z * 1e-3
        d2 = (rr[1:] ** 2 - rr[:-1] ** 2)[:, None]
        bz_edge = 2 * (psi[1:, :] - psi[:-1, :]) / d2
        bz = 0.5 * (bz_edge[:, :-1] + bz_edge[:, 1:])
        gz = (psi[:, 1:] - psi[:, :-1]) / np.diff(zz)[None, :]
        rcm = 0.5 * (rr[:-1] + rr[1:])[:, None]
        wgt = (rcm ** 2 - rr[:-1, None] ** 2) / d2
        br = -(gz[:-1] + (gz[1:] - gz[:-1]) * wgt) / rcm
        return br, bz

    def inductance(self):
        """one coil's self-inductance (H) for TURNS turns: N^2 2 pi <psi, load> per ampere-turn."""
        return TURNS ** 2 * 2 * math.pi * float(np.sum(self.psi["top"] * self.load["top"]))

    def bulk(self, name):
        """a rod's cells less ROD_END_BAND at each end."""
        _, _, lo, hi, _ = [p for p in self.mag if p[0] == name][0]
        return self.masks[name] & (self.ZC >= lo + ROD_END_BAND) & (self.ZC <= hi - ROD_END_BAND)


# ======================================================================================================
# 2. the null [OC]
# ======================================================================================================
class Axis:
    """unit on-axis fields inside the vessel (|z| <= 25 mm: no material edge), as splines in mm."""

    def __init__(self, sol):
        sel = np.abs(sol.z) <= GEO["seat_z"][0] + 1e-9
        self.zs = sol.z[sel]
        self.bt, self.bb = sol.axis_bz(sol.psi["top"])[sel], sol.axis_bz(sol.psi["bot"])[sel]
        self.St, self.Sb = CubicSpline(self.zs, self.bt), CubicSpline(self.zs, self.bb)
        self.Se = CubicSpline(self.zs, sol.axis_bz(sol.psi["ext"])[sel])        # per tesla of uniform axial field
        self.dSt, self.dSb, self.dSe = self.St.derivative(), self.Sb.derivative(), self.Se.derivative()

    def null(self, ni_top, ni_bot, b_ext=0.0):
        """the null nearest the centre (mm), the gradient there (T/m) and the field at z = 0 (T), with an optional
        uniform axial field b_ext (T) from far away; arrays welcome."""
        nt, nb, be = np.asarray(ni_top, float), np.asarray(ni_bot, float), np.asarray(b_ext, float)
        zn = np.zeros(np.broadcast(nt, nb, be).shape)

        def f(zq):
            return nt * self.St(zq) - nb * self.Sb(zq) + be * self.Se(zq)

        def fp(zq):
            return nt * self.dSt(zq) - nb * self.dSb(zq) + be * self.dSe(zq)
        for _ in range(40):
            step = f(zn) / fp(zn)
            zn = zn - step
            if np.max(np.abs(step)) < 1e-11:
                break
        resid = np.max(np.abs(f(zn)))
        assert resid < 1e-12, f"null not converged: {resid}"
        return zn, fp(zn) * 1e3, f(0.0)

    def lever(self):
        """the null's lever (mm): B_z(0) over dB_z/dz(0) of one coil; z_null ~ -lever x (top - bottom) / sum."""
        return float(self.St(0.0) / self.dSt(0.0))


def rod_stats(sol, br, bz, name):
    """|B| in a rod: the bulk's peak (ROD_END_BAND off each end), the 99th percentile over the whole rod, and the end
    corners' peak, which the linear model concentrates without limit as the cells shrink (reported, not used)."""
    m, bk = sol.masks[name], sol.bulk(name)
    bm = np.hypot(br, bz)
    i, j = np.unravel_index(int(np.argmax(np.where(bk, bm, -1.0))), bm.shape)
    return dict(B_bulk_max_T=float(bm[i, j]), at_r_mm=float(sol.RC[i, j]), at_z_mm=float(sol.ZC[i, j]),
                B_p99_T=float(np.percentile(bm[m], 99)), B_corner_max_T=float(bm[m].max()))


def rod_axis(sol, psi, name):
    """on-axis |B| at the rod's mid-length and at its inner and outer end faces (T)."""
    _, _, lo, hi, _ = [p for p in sol.mag if p[0] == name][0]
    ax = np.abs(sol.axis_bz(psi))
    inner, outer = (lo, hi) if lo > 0 else (hi, lo)
    return dict(B_centre_T=float(np.interp(0.5 * (lo + hi), sol.z, ax)), B_inner_tip_T=float(np.interp(inner, sol.z, ax)),
                B_outer_end_T=float(np.interp(outer, sol.z, ax)))


def readout(sol, ni_top=NI_MEAN, ni_bot=NI_MEAN, ax=None, full=False):
    """the pair's numbers at (ni_top, ni_bot)."""
    ax = ax or Axis(sol)
    zn, grad, b0 = ax.null(ni_top, ni_bot)
    psi = sol.combo(ni_top, ni_bot)
    br, bz = sol.cells(psi)
    out = dict(z_null_mm=float(zn), G_T_per_m=float(grad), B_centre_uT=float(b0 * 1e6), lever_mm=ax.lever())
    for nm in ("rod_top", "rod_bot"):
        if nm in sol.masks:
            out[nm] = dict(**rod_stats(sol, br, bz, nm), **rod_axis(sol, psi, nm))
    steel = [nm for nm in sol.masks if nm.startswith(("flange", "shaft"))]
    if steel:
        m = np.zeros(sol.RC.shape, bool)
        for nm in steel:
            m |= sol.masks[nm]
        out["steel_B_max_T"] = float(np.hypot(br, bz)[m].max())
    if full:
        bza = sol.axis_bz(psi)
        mbr, mbz = sol.mid_plane(psi)
        rr = sol.r[sol.r <= GEO["ves_r"] + 1e-9]
        fit = (rr > 0) & (rr <= 3.0 + 1e-9)
        coef = np.linalg.lstsq(np.column_stack([rr[fit] * 1e-3, (rr[fit] * 1e-3) ** 3]),
                               mbr[:len(rr)][fit], rcond=None)[0]
        za = np.arange(-80.0, 80.0 + 1e-9, 1.0)
        req = np.arange(0.0, GEO["ves_r"] + 1e-9, 0.5)
        mabs = np.hypot(mbr, mbz)
        pts = {}
        for rq in (5.0, 10.0, 20.0, GEO["ves_r_in"]):
            i = int(np.argmin(np.abs(sol.r - rq)))
            pts[f"r{rq:g}_z0"] = dict(B_r_mT=float(mbr[i] * 1e3), B_z_mT=float(mbz[i] * 1e3), absB_mT=float(mabs[i] * 1e3))
        for zq in (-GEO["ves_r_in"], -20.0, -10.0, -5.0, 5.0, 10.0, 20.0, GEO["ves_r_in"]):
            j = int(np.argmin(np.abs(sol.z - zq)))
            pts[f"r0_z{zq:+g}"] = dict(B_z_mT=float(bza[j] * 1e3), absB_mT=float(abs(bza[j]) * 1e3))
        out.update(radial_gradient_T_per_m=float(coef[0]), radial_over_axial=float(coef[0] / grad), points=pts,
                   axis_profile=dict(z_mm=za.tolist(), Bz_mT=(np.interp(za, sol.z, bza) * 1e3).tolist()),
                   equator_profile=dict(r_mm=req.tolist(), Br_mT=(np.interp(req, sol.r, mbr) * 1e3).tolist(),
                                        absB_mT=(np.interp(req, sol.r, mabs) * 1e3).tolist()))
    return out


# ======================================================================================================
# 3. the currents: the pick's waveforms, regenerated as sim/ah_steady_cusp.py runs them               [OC]
# ======================================================================================================
def pump_waves(c_mf):
    """the deck's AHt / AHb ampere-turns over the last 4 cycles of the pick, with C_byp + ESR across each (0: none)."""
    kw = RP._kw(RP.TAU_FIXED)
    txt, vecs, info = MD.deck(**kw)
    if c_mf:
        byp = [f"R_bypA x1 xb1 {AS.ESR:g}", f"C_bypA xb1 d {c_mf * 1e-3:g}",
               f"R_bypB x2 xb2 {AS.ESR:g}", f"C_bypB xb2 b {c_mf * 1e-3:g}"]
        txt = txt.replace("D1s f2 b ND", "\n".join(byp) + "\nD1s f2 b ND")
    ex = ["v(ps_AHt)", "v(ps_AHb)"]
    txt = txt.replace("wrdata out.dat " + " ".join(vecs), "wrdata out.dat " + " ".join(vecs + ex))
    with tempfile.TemporaryDirectory() as tmp:
        with open(os.path.join(tmp, "x.cir"), "w") as fh:
            fh.write(txt)
        subprocess.run(["ngspice", "-b", "x.cir"], capture_output=True, text=True, timeout=3600, cwd=tmp)
        raw = np.loadtxt(os.path.join(tmp, "out.dat"))
    ts = raw[:, 0]
    col = {v: raw[:, 2 * j + 1] for j, v in enumerate(vecs + ex)}
    ah, period = kw["ah_custom"], 1.0 / kw["F"]
    keep = ts >= (kw["n_cyc"] - 4) * period
    cur = {nm: col[f"v(ps_{nm})"][keep] / ah["L"] for nm in ("AHt", "AHb")}
    return dict(C_byp_mF=c_mf, F_Hz=float(kw["F"]), N=int(ah["N"]), t_s=ts[keep] - ts[keep][0],
                NI={nm: np.abs(i) * ah["N"] for nm, i in cur.items()},
                sign={nm: [float(np.sign(i).min()), float(np.sign(i).max())] for nm, i in cur.items()})


def gate_wave(w, row):
    """the regenerated AHt / AHb against the recorded 'top' / 'bottom' (the deck's names) of the same row."""
    st = {}
    for nm in ("AHt", "AHb"):
        a = w["NI"][nm]
        st[nm] = dict(AT_min=float(a.min()), AT_mean=float(a.mean()), AT_max=float(a.max()))
    st["dAT_max"] = float(np.max(np.abs(w["NI"]["AHt"] - w["NI"]["AHb"])))
    diffs = [abs(st[nm][k] - row[key][k]) for nm, key in (("AHt", "top"), ("AHb", "bottom"))
             for k in ("AT_min", "AT_mean", "AT_max")] + [abs(st["dAT_max"] - row["dAT_max"])]
    unipolar = all(v[0] == v[1] for v in w["sign"].values())
    return dict(regenerated=st, max_abs_diff_AT=float(max(diffs)), unipolar=unipolar,
                pass_=bool(max(diffs) <= 0.5 and unipolar))


def cycle(ax, sol, w, cells_unit):
    """the null, the gradient and the centre field over the 4 recorded cycles; the rods' peak |B| over them."""
    ni_top, ni_bot = w["NI"]["AHb"], w["NI"]["AHt"]                              # DECK_SIDE
    zn, grad, b0 = ax.null(ni_top, ni_bot)
    period = 1.0 / w["F_Hz"]
    last = w["t_s"] >= w["t_s"][-1] - period
    k = int(np.argmax(np.abs(ni_top - ni_bot)))
    sub = np.unique(np.linspace(0, len(w["t_s"]) - 1, 2000).astype(int))
    peaks = {}
    for nm in ("rod_top", "rod_bot"):
        bk = sol.bulk(nm)
        (tr, tz), (br_, bz_) = ([x[bk] for x in cells_unit[s]] for s in ("top", "bot"))
        nt, nb = ni_top[sub][:, None], ni_bot[sub][:, None]
        bm = np.hypot(nt * tr - nb * br_, nt * tz - nb * bz_).max(axis=1)
        q = int(np.argmax(bm))
        peaks[nm] = dict(B_bulk_max_T=float(bm[q]), at_NI_top=float(ni_top[sub][q]), at_NI_bottom=float(ni_bot[sub][q]))
    return dict(
        z_null_mm=dict(min=float(zn.min()), max=float(zn.max()), pp=float(zn.max() - zn.min()),
                       absmax=float(np.abs(zn).max())),
        B_centre_uT=dict(min=float(b0.min() * 1e6), max=float(b0.max() * 1e6), absmax=float(np.abs(b0).max() * 1e6),
                         rms=float(np.sqrt(np.mean(b0 ** 2)) * 1e6)),
        G_T_per_m=dict(min=float(grad.min()), max=float(grad.max()), mean=float(grad.mean())),
        at_max_difference=dict(NI_top=float(ni_top[k]), NI_bottom=float(ni_bot[k]), z_null_mm=float(zn[k]),
                               B_centre_uT=float(b0[k] * 1e6), G_T_per_m=float(grad[k])),
        rods_bulk_peak_over_cycle=peaks,
        last_cycle=dict(t_ms=((w["t_s"][last] - w["t_s"][last][0]) * 1e3)[::8].tolist(),
                        NI_top=ni_top[last][::8].tolist(), NI_bottom=ni_bot[last][::8].tolist(),
                        z_null_mm=zn[last][::8].tolist(), B_centre_uT=(b0[last][::8] * 1e6).tolist(),
                        G_T_per_m=grad[last][::8].tolist()))


# ======================================================================================================
# 4. gates
# ======================================================================================================
def thick_axis(zf, win, ni=1.0):
    """closed-form B_z on the axis (T) of a uniform-density winding (r1, r2, z1, z2 in mm) at zf (mm)        [OC]"""
    a1, a2, b1, b2 = (x * 1e-3 for x in win)
    jd = ni / ((a2 - a1) * (b2 - b1))
    zf = np.asarray(zf, float) * 1e-3

    def prim(u):
        return u * np.log((a2 + np.sqrt(a2 ** 2 + u ** 2)) / (a1 + np.sqrt(a1 ** 2 + u ** 2)))
    return MU0 * jd / 2 * (prim(b2 - zf) - prim(b1 - zf))


def gate_air(h, log):
    sol = Sol(case(air=True), h=h)
    bz = sol.axis_bz(sol.psi["top"])
    sel = np.abs(sol.z) <= 80.0 + 1e-9
    ref = thick_axis(sol.z[sel], sol.win_t)
    rel = bz[sel] / ref - 1
    step = 1e-3                                                                 # mm
    g_ref = NI_MEAN * ((thick_axis(step, sol.win_t) - thick_axis(-step, sol.win_t)) -
                       (thick_axis(step, sol.win_b) - thick_axis(-step, sol.win_b))) / (2 * step * 1e-3)
    _, g_fv, _ = Axis(sol).null(NI_MEAN, NI_MEAN)
    out = dict(h_mm=h, max_abs_rel_axis=float(np.abs(rel).max()), rel_at_centre=float(rel[np.argmin(np.abs(sol.z[sel]))]),
               B_centre_one_coil_uT_per_AT=float(ref[np.argmin(np.abs(sol.z[sel]))] * 1e6),
               G_air_pair_T_per_m=float(g_fv), G_air_pair_closed_form_T_per_m=float(g_ref),
               G_air_rel=float(g_fv / g_ref - 1), L_air_H=sol.inductance())
    out["pass_"] = bool(out["max_abs_rel_axis"] <= 0.01 and abs(out["G_air_rel"]) <= 0.01)
    log(f"G-AIR: on-axis max |rel| {100 * out['max_abs_rel_axis']:.3f} % (|z| <= 80 mm), centre "
        f"{100 * out['rel_at_centre']:+.4f} %; air pair G {g_fv:.5f} vs {g_ref:.5f} T/m ({100 * out['G_air_rel']:+.3f} %)")
    return out, sol


# ======================================================================================================
# 5. the figure
# ======================================================================================================
SURF, INK, INK2, GRID, AXIS = "#fcfcfb", "#0b0b0b", "#52514e", "#e1e0d9", "#c3c2b7"
RED, BLUE, FERRITE, STEEL = "#c0392b", "#1f6fb2", "#b9b5aa", "#8a8f99"


def figure(res, base_sol, path):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.patches import Circle, Rectangle

    def style(ax, title, ylabel, xlabel):
        ax.set_facecolor(SURF)
        ax.set_title(title, fontsize=9.6, loc="left", color=INK)
        ax.set_ylabel(ylabel, fontsize=8.3, color=INK2)
        ax.set_xlabel(xlabel, fontsize=8.3, color=INK2)
        ax.grid(True, color=GRID, lw=0.6)
        ax.set_axisbelow(True)
        for s in ("top", "right"):
            ax.spines[s].set_visible(False)
        for s in ("left", "bottom"):
            ax.spines[s].set_color(AXIS)
        ax.tick_params(colors=INK2, labelsize=7.8)

    def legend(ax, size=7.2, **kw):
        ax.legend(fontsize=size, frameon=False, labelcolor=INK, **kw)

    pr, im, rd = res["pair"], res["imbalance"], res["rods"]
    (z0, z1), r0 = GEO["rod_z"], GEO["rod_r"]
    (a1, a2), (b1, b2) = GEO["coil_r"], GEO["coil_z"]
    fz0, fz1 = GEO["flange_z"]
    fig, axs = plt.subplots(2, 3, figsize=(15.0, 9.6), facecolor=SURF)
    fig.subplots_adjust(left=0.05, right=0.985, top=0.9, bottom=0.07, wspace=0.27, hspace=0.36)
    fig.suptitle(f"The AH's magnetic null in the locked hub: {NI_MEAN:.0f} A-turns per coil, 77 MnZn rods (μr "
                 f"{MU_ROD:.0f}), non-magnetic shaft. G = {pr['G_T_per_m']:.3f} T/m at the null (sim/ah_null.py)",
                 fontsize=11.2, color=INK, x=0.05, ha="left")

    # (a) the section: flux lines
    ax = axs[0, 0]
    psi = base_sol.combo(NI_MEAN, NI_MEAN)
    sr, sz = base_sol.r <= 40.0, np.abs(base_sol.z) <= 90.0
    RR, ZZ = np.meshgrid(base_sol.r[sr], base_sol.z[sz], indexing="ij")
    pz = psi[np.ix_(sr, sz)]
    lim = np.abs(pz).max()
    ax.contour(RR, ZZ, pz, levels=np.linspace(-lim, lim, 41)[1:-1], colors=INK2, linewidths=0.55, linestyles="solid")
    for s in (+1, -1):
        ax.add_patch(Rectangle((0, min(s * z0, s * z1)), r0, z1 - z0, fc=FERRITE, ec=INK2, lw=0.6, alpha=0.85,
                               label="77 MnZn rod" if s > 0 else None))
        ax.add_patch(Rectangle((a1, min(s * b1, s * b2)), a2 - a1, b2 - b1, fc=RED if s > 0 else BLUE, ec="none",
                               alpha=0.55, label="coil, top (side B)" if s > 0 else "coil, bottom (side A), opposed"))
        ax.add_patch(Rectangle((0, min(s * fz0, s * fz1)), GEO["flange_r"], fz1 - fz0, fc="none", ec=STEEL, lw=0.9,
                               ls="--", label="flange, non-magnetic" if s > 0 else None))
    ax.add_patch(Circle((0, 0), GEO["ves_r"], fc="none", ec=BLUE, lw=0.9, ls=":", label="vessel, 50 mm"))
    ax.plot([0], [0], marker="x", color=RED, ms=7, ls="none", label="the null")
    ax.set_xlim(0, 40)
    ax.set_ylim(-90, 90)
    ax.set_aspect("equal")
    style(ax, "(a) the half-section: flux lines (ψ = const)", "z (mm)", "r (mm)")
    legend(ax, size=7.0, loc="upper left", bbox_to_anchor=(1.06, 1.0))

    # (b) B_z on the axis
    ax = axs[0, 1]
    zp, bzp = np.array(pr["axis_profile"]["z_mm"]), np.array(pr["axis_profile"]["Bz_mT"])
    ax.axvspan(z0, z1, color=FERRITE, alpha=0.35, lw=0, label="the rods")
    ax.axvspan(-z1, -z0, color=FERRITE, alpha=0.35, lw=0)
    ax.plot(zp, bzp, color=RED, lw=1.6, ls="-", label=f"as built (rods μr {MU_ROD:.0f})")
    ax.plot(res["pair_air_axis"]["z_mm"], res["pair_air_axis"]["Bz_mT"], color=BLUE, lw=1.4, ls="--",
            label="the same coils without rods")
    ax.axvline(GEO["ves_r_in"], color=INK2, lw=0.7, ls=":", label="the vessel's inner wall")
    ax.axvline(-GEO["ves_r_in"], color=INK2, lw=0.7, ls=":")
    style(ax, "(b) B_z on the axis", "B_z (mT)", "z (mm)")
    legend(ax, loc="upper left")

    # (c) |B| away from the null, along the axis and across the equator
    ax = axs[0, 2]
    keep = (zp >= 0) & (zp <= GEO["ves_r"])
    req, babs = np.array(pr["equator_profile"]["r_mm"]), np.array(pr["equator_profile"]["absB_mT"])
    gax = pr["G_T_per_m"]
    sgrid = np.linspace(0, GEO["ves_r"], 50)
    ax.plot(zp[keep], np.abs(bzp[keep]), color=RED, lw=1.6, ls="-", label="on the axis: |B| at |z| = s")
    ax.plot(req, babs, color=BLUE, lw=1.6, ls="--", label="in the equatorial plane: |B| at r = s")
    ax.plot(sgrid, gax * sgrid, color=RED, lw=0.8, ls=":", label=f"G·s (G = {gax:.3f} T/m)")
    ax.plot(sgrid, 0.5 * gax * sgrid, color=BLUE, lw=0.8, ls="-.", label="G/2·s")
    ax.axvline(GEO["ves_r_in"], color=INK2, lw=0.7, ls=":")
    style(ax, "(c) |B| inside the vessel, from the null", "|B| (mT)", "distance s from the centre (mm)")
    legend(ax, loc="upper left")

    # (d) the null against the imbalance
    ax = axs[1, 0]
    dd, zz = np.array(im["sweep"]["dNI"]), np.array(im["sweep"]["z_null_mm"])
    ax.axvspan(0, DNI_BYP, color=BLUE, alpha=0.12, lw=0, label=f"with the 22 mF bypass: ≤ {DNI_BYP:.0f} A-turns")
    ax.plot(dd, zz, color=RED, lw=1.6, ls="-", label=f"the null, {NI_MEAN:.0f} A-turns mean")
    ax.plot(dd, -im["lever_mm"] * dd / (2 * NI_MEAN), color=BLUE, lw=1.0, ls="--",
            label=f"first order: −{im['lever_mm']:.1f} mm × (top − bottom) / (top + bottom)")
    tb = im["table"]
    ax.plot([x["dNI"] for x in tb], [x["z_null_mm"] for x in tb], ls="none", marker="o", ms=4, color=RED,
            label="0, 5, 10, 17, 34 A-turns")
    style(ax, "(d) the null against the coils' imbalance", "z_null (mm)", "top − bottom (A-turns)")
    legend(ax, loc="lower left")

    # (e) one 120 Hz cycle
    ax = axs[1, 1]
    for key, col, ls, lab in (("unbypassed", RED, "-", "no bypass: 139–449 A-turns each"),
                              ("bypassed_22mF", BLUE, "--", "22 mF bypass (PROPOSED): 290–308")):
        lc = im[key]["cycle"]["last_cycle"]
        ax.plot(lc["t_ms"], lc["z_null_mm"], color=col, lw=1.5, ls=ls, label=lab)
    ax.axhline(0, color=INK2, lw=0.7)
    ax.set_ylim(-7.6, 10.0)
    style(ax, "(e) the null over one 120 Hz cycle at the pick", "z_null (mm)", "t (ms)")
    legend(ax, loc="upper left")

    # (f) the rod's |B| against the ampere-turns
    ax = axs[1, 2]
    ni = np.linspace(0, 1400, 281)
    for key, col, ls, lab in (("bulk", RED, "-", "rod peak (bulk), non-magnetic shaft"),
                              ("centre", RED, ":", "rod centre on the axis, non-magnetic shaft"),
                              ("steel_1000_bulk", BLUE, "--", "rod peak (bulk), mild-steel shaft μr 1000")):
        y = rd["per_AT_T"][key] * ni
        ok = y <= BSAT_25C + 1e-9
        ax.plot(ni[ok], y[ok], color=col, lw=1.5, ls=ls, label=lab)
    for bl, txt in ((B_LIMIT_REG, "0.30 T: the register's G-AH-SAT limit"), (BSAT_100C, "0.38 T: B_sat at 100 °C"),
                    (BSAT_25C, "0.49 T: B_sat at 25 °C")):
        ax.axhline(bl, color=INK2, lw=0.7, ls="-.")
        ax.text(1395, bl + 0.007, txt, fontsize=6.8, color=INK2, ha="right")
    for xv, txt in ((NI_MEAN, "300"), (NI_PEAK, "449"), (AT_ROD_LIMIT_REC, "601: the record's rod limit")):
        ax.axvline(xv, color=AXIS, lw=0.8)
        ax.text(xv + 8, 0.015, txt, fontsize=6.8, color=INK2)
    ax.set_xlim(0, 1400)
    ax.set_ylim(0, 0.56)
    style(ax, "(f) the ferrite's |B| against the ampere-turns (linear)", "|B| (T)", "A-turns per coil, both coils")
    legend(ax, size=6.8, loc="lower right", bbox_to_anchor=(1.0, 0.1))
    os.makedirs(os.path.dirname(path), exist_ok=True)
    fig.savefig(path, dpi=150, facecolor=SURF)
    plt.close(fig)


# ======================================================================================================
# 6. main
# ======================================================================================================
def _rel(a, b):
    return float(a / b - 1)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--h", type=float, default=H_PROD)
    ap.add_argument("--no-figure", action="store_true")
    args = ap.parse_args()
    h = args.h
    log = lambda s: print(s, flush=True)                                       # noqa: E731
    t_start = time.time()
    with Pool(2) as pool:
        waves_async = pool.map_async(pump_waves, (0.0, 22.0), chunksize=1)     # ngspice, beside the field solves

        res = dict(schema="ah-null/1", generated_by="sim/ah_null.py", h_mm=h, far_mm=FAR)
        res["inputs"] = dict(
            geometry_mm=GEO, turns=TURNS, shaft_magnetic_record=SHAFT_MAGNETIC, mu_rod=MU_ROD,
            Bsat_25C_T=BSAT_25C, Bsat_100C_T=BSAT_100C, B_limit_register_T=B_LIMIT_REG,
            AT_rod_limit_record=AT_ROD_LIMIT_REC, L_AH_record_H=L_AH_REC, NI_mean=NI_MEAN, dNI_bypassed=DNI_BYP,
            NI_peak_unbypassed=NI_PEAK, steel_mu=STEEL_MU, steel_z_end_mm=Z_STEEL_END, steel_gap_mm=GAP_STEEL,
            steel_gap_small_mm=GAP_SMALL, mu_austenitic=MU_AUSTENITIC, rod_end_band_mm=ROD_END_BAND, shift_mm=SHIFT,
            naming="top = the coil above (z > 0) = side B = the deck's AHb; bottom = below = side A = AHt",
            sources={
                "geometry": f"{SRC_HUB} AH (core, former, coil), AH_seat, vessel, vessel_wall, shaft",
                "turns": f"{SRC_HUB} AH.coil.turns",
                "mu_rod, Bsat_100C": f"{SRC_REG} rotor.AH_rod (mu_i, Bsat_100C_T; [RH] there until the 77 datasheet is read in)",
                "Bsat_25C": "not in the repository: Fair-Rite 77 datasheet-class [IR]",
                "B_limit_register": "sim/em-register-predictions.md:74 (G-AH-SAT, limit 0.30 T); sim/em_ra.py:125",
                "AT_rod_limit_record": "sim/magnetic_doubler.py:51 AT_ROD_LIMIT = 1022 x 0.30 / 0.51",
                "L_AH_record": "sim/magnetic_doubler.py AH['r160'] (variant (a)'s former rewound, [RH] N^2 scaling)",
                "currents": f"{SRC_CUSP} rows C_byp 0 and 22 mF; the waveforms regenerated as sim/ah_steady_cusp.py runs them",
                "naming": "README.md:24 and docs/ledger/DCCREG-design-ledger.md:61 (side A below); sim/ah-steady-cusp-findings.md:9-10 (AHt = side A)",
                "RA comparison": "sim/em_register_results.json ra.magnetics.a (all four windings at a 15 kV ring)",
                "steel, gaps, z_end, shift, austenitic mu, end band": "[IR] / [RH] (this study)"})

        # ---- gates (a) air, (b) mesh, (c) symmetry; the far boundary and div B ----
        log(f"solving (h {h} mm) ...")
        g_air, sol_air = gate_air(h, log)
        base = Sol(case(), h=h)
        log(f"  grid {len(base.r)} x {len(base.z)} = {base.nodes} nodes, {base.secs:.1f} s per solve")
        ax0 = Axis(base)
        pair = readout(base, ax=ax0, full=True)
        mesh = {}
        for hh in sorted({0.5, h, 0.125}, reverse=True):
            s_ = base if hh == h else Sol(case(), h=hh)
            r_ = readout(s_, ax=ax0 if s_ is base else None)
            s_sh = Sol(case(rod_shift=SHIFT), h=hh)
            mesh[f"{hh:g}"] = dict(nodes=s_.nodes, G_T_per_m=r_["G_T_per_m"], lever_mm=r_["lever_mm"],
                                   rod_B_bulk_max_T=r_["rod_top"]["B_bulk_max_T"], rod_B_p99_T=r_["rod_top"]["B_p99_T"],
                                   rod_B_centre_T=r_["rod_top"]["B_centre_T"],
                                   rod_B_corner_max_T=r_["rod_top"]["B_corner_max_T"],
                                   null_shift_AH_moved_mm=readout(s_sh)["z_null_mm"] - r_["z_null_mm"])
        hs = sorted(mesh, key=float, reverse=True)
        steps = []
        for a, b in zip(hs[:-1], hs[1:]):
            steps.append({k: _rel(mesh[b][k], mesh[a][k]) for k in ("G_T_per_m", "lever_mm", "rod_B_bulk_max_T",
                                                                     "rod_B_p99_T", "rod_B_centre_T", "rod_B_corner_max_T",
                                                                     "null_shift_AH_moved_mm")})
            steps[-1]["from_to"] = f"{a} -> {b} mm"
        g_mesh = dict(levels=mesh, steps=steps, criterion="G changes < 2 % at each halving",
                      pass_=bool(all(abs(x["G_T_per_m"]) < 0.02 for x in steps)))
        log("G-MESH: G " + " -> ".join(f"{mesh[k]['G_T_per_m']:.5f}" for k in hs) + " T/m; steps " +
            ", ".join(f"{100 * x['G_T_per_m']:+.3f} %" for x in steps))
        one = abs(float(ax0.St(0.0)))
        sym = abs(pair["B_centre_uT"] * 1e-6) / (NI_MEAN * one)
        g_sym = dict(z_null_mm=pair["z_null_mm"], B_centre_over_one_coil=float(sym),
                     pass_=bool(abs(pair["z_null_mm"]) < 1e-9 and sym < 1e-9))
        log(f"G-SYM: balanced null at {pair['z_null_mm']:.2e} mm; B_z(0) / one coil's {sym:.1e}")
        g_div = dict(radial_T_per_m=pair["radial_gradient_T_per_m"], axial_T_per_m=pair["G_T_per_m"],
                     ratio=pair["radial_over_axial"], rel_to_minus_half=float(pair["radial_over_axial"] / -0.5 - 1),
                     pass_=bool(abs(pair["radial_over_axial"] / -0.5 - 1) < 0.01))
        log(f"G-DIV: dB_r/dr {pair['radial_gradient_T_per_m']:.5f} T/m = {pair['radial_over_axial']:.5f} x G")
        g_far = dict(G_far_1m=readout(Sol(case(), h=h, far=1000.0))["G_T_per_m"], G_far_2m=pair["G_T_per_m"])
        g_far["rel"] = _rel(g_far["G_far_1m"], g_far["G_far_2m"])
        g_far["pass_"] = bool(abs(g_far["rel"]) < 1e-3)
        log(f"G-FAR: G at a 1 m boundary {100 * g_far['rel']:+.5f} % against 2 m")

        # ---- the pair as built ----
        L_rod, L_air = base.inductance(), g_air["L_air_H"]
        _, g_air_pair, _ = Axis(sol_air).null(NI_MEAN, NI_MEAN)
        pair.update(L_one_coil_H=L_rod, L_one_coil_air_H=L_air, L_ratio_rod_over_air=L_rod / L_air,
                    B_centre_one_coil_uT_per_AT=float(ax0.St(0.0) * 1e6),
                    G_one_coil_T_per_m_per_AT=float(ax0.dSt(0.0) * 1e3),
                    G_per_AT_T_per_m=pair["G_T_per_m"] / NI_MEAN, G_air_cored_T_per_m=float(g_air_pair),
                    rods_gain_on_G=float(pair["G_T_per_m"] / g_air_pair))
        air_bz = sol_air.axis_bz(sol_air.combo(NI_MEAN, NI_MEAN))
        za = np.arange(-80.0, 80.0 + 1e-9, 1.0)
        res["pair_air_axis"] = dict(z_mm=za.tolist(), Bz_mT=(np.interp(za, sol_air.z, air_bz) * 1e3).tolist())
        ra = EMREG["ra"]["magnetics"]["a"]
        res["cross_checks"] = dict(
            L_vs_record=dict(L_H=L_rod, L_record_H=L_AH_REC, rel=_rel(L_rod, L_AH_REC),
                             note="the record's 1.01 mH is the register's 98.5 uH (variant (a), 50 turns, with rod) x (160/50)^2"),
            G_per_AT_vs_RA=dict(this_T_per_m_per_AT=pair["G_T_per_m"] / NI_MEAN,
                                RA_T_per_m_per_AT=ra["grad_centre_T_per_m"] / ra["NI_AH"],
                                rel=_rel(pair["G_T_per_m"] / NI_MEAN, ra["grad_centre_T_per_m"] / ra["NI_AH"]),
                                note="RA: all four windings at a 15 kV ring; the aiding cone pair adds no gradient at the "
                                     "centre by symmetry, so the AH alone should match per A-turn"))
        b10 = 10e-6
        zx, _, _ = ax0.null(NI_MEAN, NI_MEAN, b10)
        ax_air = Axis(sol_air)
        res["external_field"] = dict(
            enhancement_at_centre=float(ax0.Se(0.0)), air_cored_check=float(ax_air.Se(0.0)),
            z_null_per_10uT_axial_mm=float(zx), bare_estimate_per_10uT_mm=float(-b10 / pair["G_T_per_m"] * 1e3),
            radial_offset_per_10uT_transverse_bare_mm=float(2 * b10 / pair["G_T_per_m"] * 1e3),
            note="axial: computed with the rods (psi = B r^2 / 2 on the far boundary); transverse: the bare estimate "
                 "2 B / G from the radial gradient G/2, the rods' transverse concentration not computed")
        log(f"external axial field: x{ax0.Se(0.0):.3f} at the centre (air-cored {ax_air.Se(0.0):.6f}); "
            f"10 uT moves the null {zx:+.4f} mm")
        log(f"pair: G {pair['G_T_per_m']:.4f} T/m (air-cored {g_air_pair:.4f}); radial {pair['radial_gradient_T_per_m']:.4f}; "
            f"lever {pair['lever_mm']:.2f} mm; L {L_rod * 1e3:.3f} mH (air {L_air * 1e3:.3f}); G/AT vs RA "
            f"{100 * res['cross_checks']['G_per_AT_vs_RA']['rel']:+.2f} %")

        # ---- the imbalance ----
        sweep_d = np.linspace(0.0, 200.0, 201)
        zs_, _, bs_ = ax0.null(NI_MEAN + sweep_d / 2, NI_MEAN - sweep_d / 2)
        table = []
        for dn in sorted(set(IMBALANCE) | {round(DNI_BYP, 2)}):
            zn, gr, b0 = ax0.null(NI_MEAN + dn / 2, NI_MEAN - dn / 2)
            table.append(dict(dNI=dn, NI_top=NI_MEAN + dn / 2, NI_bottom=NI_MEAN - dn / 2, z_null_mm=float(zn),
                              B_centre_uT=float(b0 * 1e6), G_T_per_m=float(gr),
                              first_order_mm=float(-ax0.lever() * dn / (2 * NI_MEAN))))
        imb = dict(lever_mm=ax0.lever(), dz_per_AT_mm=float(-ax0.lever() / (2 * NI_MEAN)),
                   B_centre_per_AT_uT=float(ax0.St(0.0) * 1e6), table=table,
                   sweep=dict(dNI=sweep_d.tolist(), z_null_mm=zs_.tolist(), B_centre_uT=(bs_ * 1e6).tolist()))
        log("imbalance: " + ", ".join(f"{x['dNI']:g} -> {x['z_null_mm']:+.3f} mm ({x['B_centre_uT']:.1f} uT)" for x in table))

        # ---- the rods ----
        cells_unit = dict(top=base.cells(base.psi["top"]), bot=base.cells(base.psi["bot"]))
        rods = dict(at={})
        for ni in (NI_MEAN, NI_PEAK, 600.0):
            r_ = readout(base, ni, ni, ax=ax0)
            rods["at"][f"{ni:.0f}"] = dict(NI=ni, top=r_["rod_top"], bottom=r_["rod_bot"])
        per = rods["at"][f"{NI_MEAN:.0f}"]["top"]
        rods["per_AT_T"] = dict(bulk=per["B_bulk_max_T"] / NI_MEAN, p99=per["B_p99_T"] / NI_MEAN,
                                centre=per["B_centre_T"] / NI_MEAN, inner_tip=per["B_inner_tip_T"] / NI_MEAN)
        rods["NI_to_reach"] = {f"{bl:.2f} T": {k: bl / rods["per_AT_T"][k] for k in ("bulk", "p99", "centre", "inner_tip")}
                               for bl in (B_LIMIT_REG, BSAT_100C, BSAT_25C)}
        rods["record_basis"] = dict(
            AT_ROD_LIMIT=AT_ROD_LIMIT_REC, RA_rod_B_max_T=ra["rod_B_max_T"], RA_NI_AH=ra["NI_AH"],
            RA_per_AT_T=ra["rod_B_max_T"] / ra["NI_AH"], this_bulk_per_AT_T=rods["per_AT_T"]["bulk"],
            ratio=ra["rod_B_max_T"] / ra["NI_AH"] / rods["per_AT_T"]["bulk"],
            note="the RA run's rod field came from all four windings in one chain: the cones L_TC / L_BC "
                 "(32 turns each at the same ring current) as well as the AH (sim/em_ra.py, i_turn over every turn)")
        log(f"rods: bulk {per['B_bulk_max_T']:.4f} T at {NI_MEAN:.0f} A-t (centre {per['B_centre_T']:.4f}, inner tip "
            f"{per['B_inner_tip_T']:.4f}, corner {per['B_corner_max_T']:.4f}); 0.30 T at {B_LIMIT_REG / rods['per_AT_T']['bulk']:.0f}, "
            f"0.38 T at {BSAT_100C / rods['per_AT_T']['bulk']:.0f}, 0.49 T at {BSAT_25C / rods['per_AT_T']['bulk']:.0f} A-t")

        # ---- the shaft ----
        mu_a, mu_b = MU_AUSTENITIC
        shaft_cases = [
            ("non-magnetic (the record)", case()),
            ("mild steel mu 300, touching the rods", case(steel_top=300.0, steel_bot=300.0)),
            ("mild steel mu 1000, touching the rods", case(steel_top=1000.0, steel_bot=1000.0)),
            ("mild steel mu 1000, 1 mm non-magnetic gap", case(steel_top=1000.0, steel_bot=1000.0, gap_top=GAP_STEEL,
                                                               gap_bot=GAP_STEEL)),
            ("top half mu 1000, bottom half non-magnetic", case(steel_top=1000.0)),
            ("top half mu 1000, bottom half mu 300", case(steel_top=1000.0, steel_bot=300.0)),
            ("mu 1000, top touching, bottom 1 mm gap", case(steel_top=1000.0, steel_bot=1000.0, gap_bot=GAP_STEEL)),
            ("mu 1000, top touching, bottom 0.1 mm gap", case(steel_top=1000.0, steel_bot=1000.0, gap_bot=GAP_SMALL)),
            (f"top half mu {mu_a:g} (austenitic, annealed), bottom 1", case(steel_top=mu_a)),
            (f"top half mu {mu_b:g} (austenitic, cold-worked), bottom 1", case(steel_top=mu_b)),
        ]
        shaft = []
        for nm, cs in shaft_cases:
            s_ = base if nm.startswith("non-magnetic") else Sol(cs, h=h)
            a_ = ax0 if s_ is base else Axis(s_)
            r_ = readout(s_, ax=a_)
            r17 = readout(s_, NI_MEAN + DNI_BYP / 2, NI_MEAN - DNI_BYP / 2, ax=a_)
            row = dict(case=nm, G_T_per_m=r_["G_T_per_m"], G_rel=_rel(r_["G_T_per_m"], pair["G_T_per_m"]),
                       z_null_balanced_mm=r_["z_null_mm"], z_null_bypassed_mm=r17["z_null_mm"],
                       lever_mm=r_["lever_mm"], rod_top=r_["rod_top"], rod_bot=r_["rod_bot"],
                       steel_B_max_T=r_.get("steel_B_max_T"))
            if nm.startswith("mild steel mu 1000, touching"):
                for k, key in (("bulk", "B_bulk_max_T"), ("p99", "B_p99_T"), ("centre", "B_centre_T")):
                    rods["per_AT_T"][f"steel_1000_{k}"] = r_["rod_top"][key] / NI_MEAN
                fine = readout(Sol(cs, h=0.125)) if h > 0.125 else r_
                row["mesh_0p125"] = dict(G_T_per_m=fine["G_T_per_m"], rod_B_bulk_max_T=fine["rod_top"]["B_bulk_max_T"],
                                         rod_B_p99_T=fine["rod_top"]["B_p99_T"],
                                         rod_B_corner_max_T=fine["rod_top"]["B_corner_max_T"],
                                         steel_B_max_T=fine.get("steel_B_max_T"))
            if abs(r_["z_null_mm"]) > 1e-6 and h > 0.125:                     # the asymmetric cases' null, finer
                row["z_null_balanced_0p125_mm"] = readout(Sol(cs, h=0.125))["z_null_mm"]
            shaft.append(row)
            log(f"shaft: {nm:52s} G {r_['G_T_per_m']:.4f} T/m ({100 * row['G_rel']:+.1f} %), null {r_['z_null_mm']:+.3f} mm "
                f"(17 A-t: {r17['z_null_mm']:+.3f}), rod bulk {r_['rod_top']['B_bulk_max_T']:.3f} / centre "
                f"{r_['rod_top']['B_centre_T']:.3f} T" + (f", steel {row['steel_B_max_T']:.3f} T" if row["steel_B_max_T"] else ""))
        rods["NI_to_reach_steel_1000"] = {f"{bl:.2f} T": {k: bl / rods["per_AT_T"][f"steel_1000_{k}"]
                                                         for k in ("bulk", "p99", "centre")}
                                          for bl in (B_LIMIT_REG, BSAT_100C, BSAT_25C)}

        # ---- sensitivity ----
        sens = dict(mu=[], mismatch=[], misplacement=[])
        for mu in (1000.0, 2000.0, 3000.0):
            s_ = base if mu == MU_ROD else Sol(case(mu_top=mu, mu_bot=mu), h=h)
            r_ = readout(s_, ax=ax0 if s_ is base else None)
            sens["mu"].append(dict(mu=mu, G_T_per_m=r_["G_T_per_m"], G_rel=_rel(r_["G_T_per_m"], pair["G_T_per_m"]),
                                   lever_mm=r_["lever_mm"], rod_B_bulk_max_T=r_["rod_top"]["B_bulk_max_T"],
                                   rod_B_centre_T=r_["rod_top"]["B_centre_T"]))
        for mt, mb in ((2400.0, 1600.0), (3000.0, 1000.0)):
            r_ = readout(Sol(case(mu_top=mt, mu_bot=mb), h=h))
            sens["mismatch"].append(dict(mu_top=mt, mu_bot=mb, z_null_mm=r_["z_null_mm"], G_T_per_m=r_["G_T_per_m"],
                                         B_centre_uT=r_["B_centre_uT"]))
        for nm, cs in ((f"top winding {SHIFT:g} mm outward on its rod", case(coil_shift=SHIFT)),
                       (f"top AH (rod and winding) {SHIFT:g} mm outward", case(rod_shift=SHIFT))):
            r_ = readout(Sol(cs, h=h))
            sens["misplacement"].append(dict(case=nm, z_null_mm=r_["z_null_mm"], G_T_per_m=r_["G_T_per_m"],
                                             G_rel=_rel(r_["G_T_per_m"], pair["G_T_per_m"]), B_centre_uT=r_["B_centre_uT"]))
        for row in sens["mu"] + sens["mismatch"] + sens["misplacement"]:
            log("sens: " + ", ".join(f"{k} {v:.4g}" if isinstance(v, float) else f"{k} {v}" for k, v in row.items()))

        # ---- the currents over the cycle ----
        waves = dict(zip((0.0, 22.0), waves_async.get()))
    g_wave = {}
    for c_mf, row, key in ((0.0, ROW0, "unbypassed"), (22.0, ROW22, "bypassed_22mF")):
        w = waves[c_mf]
        g_wave[f"C {c_mf:g} mF"] = gate_wave(w, row)
        imb[key] = dict(C_byp_mF=c_mf, F_Hz=w["F_Hz"], stats_by_deck_name=g_wave[f"C {c_mf:g} mF"]["regenerated"],
                        cycle=cycle(ax0, base, w, cells_unit))
        cy = imb[key]["cycle"]
        log(f"{key}: null {cy['z_null_mm']['min']:+.3f} .. {cy['z_null_mm']['max']:+.3f} mm (p-p {cy['z_null_mm']['pp']:.3f}); "
            f"B(0) up to {cy['B_centre_uT']['absmax']:.1f} uT; G {cy['G_T_per_m']['min']:.4f}-{cy['G_T_per_m']['max']:.4f} T/m; "
            f"rod bulk peak {cy['rods_bulk_peak_over_cycle']['rod_top']['B_bulk_max_T']:.4f} T")
    g_wave["pass_"] = bool(all(v["pass_"] for v in g_wave.values()))
    log("G-WAVE: max |regenerated - recorded| " + ", ".join(f"{k} {v['max_abs_diff_AT']:.3g} A-t" for k, v in g_wave.items()
                                                           if isinstance(v, dict)))
    res["gates"] = {"G-AIR": g_air, "G-MESH": g_mesh, "G-SYM": g_sym, "G-DIV": g_div, "G-FAR": g_far, "G-WAVE": g_wave}
    res["pair"], res["imbalance"], res["rods"], res["shaft"], res["sensitivity"] = pair, imb, rods, shaft, sens
    res["runtime_s"] = time.time() - t_start
    with open(RESULTS, "w") as fh:
        json.dump(res, fh, indent=1, default=float)
    log(f"wrote {os.path.relpath(RESULTS, ROOT)}")
    if not args.no_figure:
        figure(res, base, FIGURE)
        log(f"wrote {os.path.relpath(FIGURE, ROOT)}")
    log("gates: " + ", ".join(f"{k} {'PASS' if v['pass_'] else 'FAIL'}" for k, v in res["gates"].items()))


if __name__ == "__main__":
    main()
