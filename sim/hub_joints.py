"""sim/hub_joints.py -- the rings' joints and voids: the gores' laps, the bead rings' closing joints, and a void at a
bead's contact or under a lap (ledger §5.2 "the gores' overlaps and joints"; docs/rings-design.md §2;
sim/hub-rings-build-findings.md "not modelled").

The prototype's bands are 0.1 mm annealed copper foil, each cut as 12 gores overlapped 1 mm and soldered, bedded in the
gel; each edge carries a bead, a copper wire ring cut, closed and soldered (docs/rings-design.md §2). The hub's studies
model the bands as smooth zones and the beads as perfect tori. This study takes the features they leave out, each on the
fields the hub and the bead boxes already give (sim/hub_beads_settled.py, as drawn) [OC law, IR grid]: at switch-on
(the permittivities share the DC) and settled (the conductivities), the glass at 1, 2.4 (in service), 4 and 5.4 (40 C)
times the gel's conductivity.
- **1. The faces:** the normal fields on each band's two faces, between the beads (the hub, 0.25 mm cells) and near
  each bead (its box, 0.025 mm cells): in the gel over the foil, from the PEEK's (the hub's band fills the 0.5 mm
  pocket; the foil's 0.4 mm of gel takes the same D, or J once settled) [IR]; and in the glass under it.
- **2. The lap, a local planar solve** across a seam (x along the azimuth, y out of the glass; the seam runs along the
  meridian, so the cut is two-dimensional) [OC law, IR geometry]:
  - the lower gore on the glass, its cut edge at x = 0; the upper gore over it for -w < x < 0, then ramping down to
    the glass over L_t (the foil draped over the lower gore's edge [RH: L_t 0.5 mm, 0.25-1.0]);
  - the outer face: the upper gore's free edge at x = -w, a 0.1 mm step: as cut (its corner rounded r_c 5-50 um), or
    under a solder fillet (a smooth ramp W_f wide);
  - the inner face: the crevice under the ramp, against the lower gore's edge, filled with the gel or a void;
  - unit far fields, held as a fixed flux density (D at switch-on, J settled) at the box's top (in the PEEK) and
    bottom (in the vacuum under the glass), so a void's own series share is kept [IR]; nested boxes to 0.5 um.
  - **The readouts:** the step's peak field in the gel over the far field (beta), the gel's peak in a gel-filled
    crevice over the glass's far field, and a void's voltage against Paschen's breakdown of its gap (the gap the
    shortest path from the glass to the conductor) [IR: Paschen as sim/hub_beads_settled.py].
- **3. The bead ring's closing joint:** a bulge around the wire, locally a ridge on a flat conductor (its height and
  width far below the wire's radius): a cosine ridge of height delta and base width w in a uniform field, beta against
  delta / w. A half-cylinder ridge gives 2 exactly, the check [OC]; a hemispherical boss (a solder ball) gives 3 [OC].
- **3b. The polar bead's margin:** its peak in the gel with the AH ends rounded (0, 1.5, 2.5 mm at REF, the proposal of
  sim/hub_beads_settled.py §6), both grooves: what a closing joint there may take.
- **4. A void at a bead's contact:** the bead's box and its contact's nested box (sim/hub_beads_settled.py's, as drawn)
  re-solved with the wedge between the bead and the bare glass filled with air (eps 1, or air's sigma once settled)
  out to s_v from the contact; the void's voltage at each s against Paschen's breakdown of its gap. The bead study's
  wedge took the gap's voltage from the gel-filled solve, which a void raises [IR].
- **5. The lap's crevice near the beads:** section 2's crevice on section 1's glass field under the foil near each
  bead.
Writes sim/hub_joints_results.json (about 25 min).
Usage: python3 sim/hub_joints.py
"""
import json
import math
import os
import sys
import time

import numpy as np
import scipy.sparse as sp
import scipy.sparse.linalg as spla

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import hub_beads_settled as S      # noqa: E402
import hub_drift as D              # noqa: E402
import hub_rings_build as B        # noqa: E402

EPS0 = S.EPS0
T_FOIL = B.FOIL_T                  # mm, the prototype's copper foil [RH]
W_LAP = 1.0                        # mm, each gore's overlap on its neighbour (docs/rings-design.md §2)
L_T = (0.25, 0.5, 1.0)             # mm, the upper gore's ramp onto the glass [RH]
L_T_BASE = 0.5
R_C = (0.005, 0.01, 0.025, 0.05)   # mm, the upper gore's cut edge, its corner radius [IR: as cut .. dressed round]
W_F = (0.2, 0.4)                   # mm, a solder fillet along the free edge, its width [IR]
RIDGE = (0.01, 0.03, 0.1, 0.3)     # delta / w of a closing joint's bulge, cosine profile [IR]
S_VOID = (0.25, 0.5, 1.0)          # mm from the contact: how far a void at a bead's contact reaches [IR]
S_FACE = (0.1, 0.25, 0.5, 0.75, 1.0, 1.5, 2.0, 2.5, 3.0, 3.5)   # mm from a bead's contact into the band
E_GEL_RATING = B.E_FILL_DESIGN     # kV/mm, the gel's working rating [RH] (sim/hub_rings_build.py)
# switch-on, then settled at sigma_glass / sigma_gel: 1 (25 C), 2.4 (in service, sim/hub-thermal-findings.md), 4 (about
# the equatorial bead's limit, sim/hub-beads-settled-findings.md §7) and 5.4 (the glass at 40 C); the gel at 1e-13 S/m
RATIOS = (1.0, 2.4, 4.0, 5.4)
HUB_STATES = (("switch-on", None),) + tuple((f"settled, ratio {k:g}", k) for k in RATIOS)
H0, H1, H2 = 0.02, 0.0025, 0.0005  # mm, the lap's boxes: coarse, the seam, the corners
VAC, GLASS, GEL, PEEK, G10, AIR = S.VAC, S.GLASS, S.GEL, S.PEEK, S.G10, S.AIR
VOID = 9                           # a sealed void: eps 1; settled, it conducts next to nothing
# a sealed void's own conduction is ionisation-limited: about 10 ion pairs per cm^3 and s, swept out across a 20 um gap,
# give some 3e-17 A/m^2, ten decades under the glass's settled 1e-7 A/m^2 at 1 kV/mm. So settled, a void is bounded by
# open air's sigma (sim/hub_drift.py SIG air, 2e-14 S/m: the optimistic end) and an insulator (1e-17 S/m here, a ten
# thousandth of the gel's; the check at 1e-18 reads the same) [IR]
SIG_VOID = 1e-17


# ------------------------------------------------------------------------------------------------ the planar solver
def fv_planar(p, cond, h, x0, y0, q_top=None, q_bot=None, vbc=None, shape=None):
    """planar finite volumes on cells (nx, ny) from (x0, y0), cell h (mm): p the property at the cells (eps_r, or sigma
    / eps0), cond the conductor cells (held at 0 V). Either q_top / q_bot, a uniform flux density (p E_y, V/mm) through
    the top and bottom edges with the x edges closed, or vbc(x, y), the potential on all four edges (Dirichlet half a
    cell out, for a nested box). shape(x, y), the conductor as a function, places its surface between a free cell and
    a conductor cell where it truly lies (Shortley-Weller): the cell couples to 0 V over that distance, not the
    staircase's [IR: second order at a curved surface]. Returns V (V)."""
    nx, ny = p.shape
    free = ~cond
    idx = -np.ones((nx, ny), dtype=np.int64)
    n = int(free.sum())
    idx[free] = np.arange(n)
    diag, rhs = np.zeros(n), np.zeros(n)
    rows, cols, vals = [], [], []
    xs = x0 + (np.arange(nx) + 0.5) * h
    ys = y0 + (np.arange(ny) + 0.5) * h

    def theta(ia, ja, ib, jb):
        """the fraction of the way from free cells (ia, ja) to their conductor neighbours (ib, jb) at which the
        conductor begins (bisection on shape), at least 0.05."""
        ax, ay, bx, by = xs[ia], ys[ja], xs[ib], ys[jb]
        lo, hi = np.zeros(ax.shape), np.ones(ax.shape)
        for _ in range(30):
            mid = 0.5 * (lo + hi)
            inside = shape(ax + mid * (bx - ax), ay + mid * (by - ay))
            hi = np.where(inside, mid, hi)
            lo = np.where(inside, lo, mid)
        return np.maximum(hi, 0.05)

    def couple(a, b, G, d):
        fa, fb = free[a], free[b]
        ia, ib = idx[a], idx[b]
        both = fa & fb
        rows.extend([ia[both], ib[both]])
        cols.extend([ib[both], ia[both]])
        vals.extend([-G[both], -G[both]])
        np.add.at(diag, ia[both], G[both])
        np.add.at(diag, ib[both], G[both])
        # a free cell against a conductor cell (the conductor at 0 V adds nothing to the right-hand side)
        I, J = np.meshgrid(np.arange(nx), np.arange(ny), indexing="ij")
        Ia, Ja, Ib, Jb = I[a], J[a], I[b], J[b]
        pa, pb = p[a], p[b]
        for fx, fy, iF, jF, iC, jC, pF in ((fa & ~fb, None, Ia, Ja, Ib, Jb, pa), (fb & ~fa, None, Ib, Jb, Ia, Ja, pb)):
            if not fx.any():
                continue
            g = pF[fx] / (theta(iF[fx], jF[fx], iC[fx], jC[fx]) if shape is not None else np.ones(int(fx.sum())))
            if shape is None:
                g = G[fx]
            np.add.at(diag, idx[iF[fx], jF[fx]], g)
    couple((slice(0, -1), slice(None)), (slice(1, None), slice(None)),
           2 * p[:-1, :] * p[1:, :] / (p[:-1, :] + p[1:, :]), 0)
    couple((slice(None), slice(0, -1)), (slice(None), slice(1, None)),
           2 * p[:, :-1] * p[:, 1:] / (p[:, :-1] + p[:, 1:]), 1)
    if vbc is not None:
        for ii, jj, xx, yy in ((0, slice(None), np.full(ny, x0), ys), (nx - 1, slice(None), np.full(ny, x0 + nx * h), ys),
                               (slice(None), 0, xs, np.full(nx, y0)), (slice(None), ny - 1, xs, np.full(nx, y0 + ny * h))):
            G = 2 * p[ii, jj]
            f = free[ii, jj]
            vb = vbc(xx, yy)
            np.add.at(diag, idx[ii, jj][f], G[f])
            np.add.at(rhs, idx[ii, jj][f], (G * vb)[f])
    else:
        # D_y = -p dV/dy: q_top leaves through the top edge, q_bot enters through the bottom (V/mm times the edge h)
        f = free[:, -1]
        np.add.at(rhs, idx[:, -1][f], -q_top * h)
        f = free[:, 0]
        np.add.at(rhs, idx[:, 0][f], q_bot * h)
    A = sp.csr_matrix((np.concatenate([np.concatenate(vals), diag]),
                       (np.concatenate([np.concatenate(rows), np.arange(n)]),
                        np.concatenate([np.concatenate(cols), np.arange(n)]))), shape=(n, n))
    V = np.zeros((nx, ny))
    V[free] = _solve(A, rhs)
    return V


def _solve(A, rhs):
    """a direct solve for small systems; smoothed-aggregation AMG with conjugate gradients for large ones (the matrix
    is symmetric positive definite: the conductor holds it)."""
    if A.shape[0] < 150_000:
        return spla.spsolve(A.tocsc(), rhs)
    import pyamg
    ml = pyamg.smoothed_aggregation_solver(A.tocsr(), symmetry="symmetric")
    res = []
    x = ml.solve(rhs, tol=1e-11, accel="cg", maxiter=400, residuals=res)
    if res[-1] > 1e-9 * res[0]:
        raise RuntimeError(f"AMG did not converge: {res[-1] / res[0]:.2e}")
    return x


def normal_peak(V, x0, y0, h, pts, nrm, ks=range(3, 10)):
    """the field at a conductor's surface (kV/mm, V in volts), from the field along each surface point's outward normal
    at k h (k in ks), central differences of the interpolated potential and a quadratic extrapolated to the surface:
    it steps over the staircase's own spikes next to a curved surface. Returns (the largest, its point)."""
    at = S.interp(V, x0, y0, h)
    ds = np.array(list(ks), dtype=float) * h
    best = (0.0, None)
    for (px, py), (ux, uy) in zip(pts, nrm):
        a = at(px + (ds - 0.5 * h) * ux, py + (ds - 0.5 * h) * uy)
        b = at(px + (ds + 0.5 * h) * ux, py + (ds + 0.5 * h) * uy)
        e = np.abs(a - b) / h / 1e3
        es = float(np.polyval(np.polyfit(ds, e, 2), 0.0))
        if es > best[0]:
            best = (es, (float(px), float(py)))
    return best


def interp2(V, x0, y0, h):
    return S.interp(V, x0, y0, h)


def efield(V, h):
    """|E| (kV/mm) at the cells, V in volts, cells h mm."""
    gx, gy = np.gradient(V, h, axis=0), np.gradient(V, h, axis=1)
    return np.hypot(gx, gy) / 1e3


def cells(x0, y0, nx, ny, h):
    return np.meshgrid(x0 + (np.arange(nx) + 0.5) * h, y0 + (np.arange(ny) + 0.5) * h, indexing="ij")


def far_dist(cond, h):
    return S.dist_from(cond, h)


# ---------------------------------------------------------------------------------------------------------- the lap
def lap_shape(X, Y, edge, l_t=L_T_BASE, t=T_FOIL, w=W_LAP):
    """the lap's conductor (both gores) at points (X, Y): the lower gore on the glass for x <= 0; the upper over it
    from x -w, ramping down onto the glass over l_t; its free edge ("rc", r) a corner rounded r, or ("fillet", W) under
    a solder fillet, a cosine ramp W wide."""
    g1 = (X <= 0) & (Y >= 0) & (Y <= t)
    yb = np.where(X <= 0, t, np.where(X >= l_t, 0.0, t * (1 - X / l_t)))      # the upper gore's underside
    g2 = (X >= -w) & (Y >= yb) & (Y <= yb + t)
    kind, a = edge
    if kind == "rc":
        cx, cy = -w + a, 2 * t - a
        return g1 | (g2 & ~((X < cx) & (Y > cy) & (np.hypot(X - cx, Y - cy) > a)))
    u = np.clip((X + w + a) / a, 0, 1)
    fil = (X >= -w - a) & (X <= -w) & (Y >= t) & (Y <= t + t * 0.5 * (1 - np.cos(math.pi * u)))
    return g1 | g2 | fil


def lap_geometry(X, Y, edge, crevice, l_t=L_T_BASE, t=T_FOIL, w=W_LAP):
    """the conductor and the materials of the lap's cut at cells (X, Y), the crevice GEL or AIR. y = 0 is the glass's
    outer surface; the gel's pocket reaches y 0.5, the PEEK beyond; the glass below, to the box's bottom (its inner
    surface, y -1.5)."""
    yb = np.where(X <= 0, t, np.where(X >= l_t, 0.0, t * (1 - X / l_t)))
    m = np.full(X.shape, PEEK, dtype=np.int8)
    m[Y < 0.5] = GEL
    m[(X > 0) & (X < l_t) & (Y >= 0) & (Y < yb)] = crevice
    m[Y < 0] = GLASS
    return lap_shape(X, Y, edge, l_t, t, w), m


def edge_surface(edge, t=T_FOIL, w=W_LAP, n=90):
    """points on the free edge's convex surface and their outward normals: the rounded corner's arc, or the fillet's
    profile with its shoulder."""
    kind, a = edge
    if kind == "rc":
        cx, cy = -w + a, 2 * t - a
        ph = np.radians(np.linspace(90, 180, n))
        return np.c_[cx + a * np.cos(ph), cy + a * np.sin(ph)], np.c_[np.cos(ph), np.sin(ph)]
    u = np.linspace(0.3, 1.0, n)
    x = -w - a + u * a
    y = t + t * 0.5 * (1 - np.cos(math.pi * u))
    dy = t * 0.5 * math.pi / a * np.sin(math.pi * u)
    nn = np.hypot(dy, 1.0)
    return np.c_[x, y], np.c_[-dy / nn, 1.0 / nn]


def ramp_surface(l_t, t=T_FOIL, n=60):
    """points on the upper gore's top over its ramp (x 0 to l_t) and their outward normals."""
    x = np.linspace(-0.02, l_t + 0.02, n)
    y = np.where(x <= 0, 2 * t, np.where(x >= l_t, t, 2 * t - t * x / l_t))
    sl = np.where((x > 0) & (x < l_t), -t / l_t, 0.0)
    nn = np.hypot(sl, 1.0)
    return np.c_[x, y], np.c_[-sl / nn, 1.0 / nn]


def lap_props(m, state):
    """eps_r (state None: switch-on) or sigma / eps0 (state k: settled, the glass at k times the gel's sigma) [IR]."""
    if state is None:
        hub = B.hub_system()
        tab = {GLASS: hub["eps_glass"], GEL: hub["eps_fill"], PEEK: hub["eps_ret"], AIR: 1.0, VOID: 1.0}
    else:
        tab = {GLASS: state * D.SIG["gel"], GEL: D.SIG["gel"], PEEK: D.SIG["peek"], AIR: D.SIG["air"], VOID: SIG_VOID}
        tab = {k: v / EPS0 for k, v in tab.items()}
    out = np.empty(m.shape)
    for k, v in tab.items():
        out[m == k] = v
    return out


def nested(edge, crevice, state, l_t, parent, box, h):
    """a nested box (x0, y0, width, height) at cell h, its edges from parent (V, x0, y0, h)."""
    nx, ny = int(round(box[2] / h)), int(round(box[3] / h))
    X, Y = cells(box[0], box[1], nx, ny, h)
    c, m = lap_geometry(X, Y, edge, crevice, l_t)
    V = fv_planar(lap_props(m, state), c, h, box[0], box[1], vbc=interp2(*parent),
                  shape=lambda x, y: lap_shape(x, y, edge, l_t))
    return V, X, Y, c, m


def lap_solve(edge, crevice, state, l_t=L_T_BASE, side="both", fine=1.0):
    """the lap in one state (None: switch-on; k: settled, the glass at k times the gel's sigma), unit far fields: 1 kV/mm in the gel over the flat foil, and 1 kV/mm in the glass under
    it, each held as a fixed flux density at the box's top (y 3.5, the PEEK) and bottom (y -1.5, the glass's inner
    surface). Returns the step's beta, the PEEK over it, the bend's, and the crevice's (the gel's peak, or a void's
    voltage per kV/mm of the glass's far field)."""
    h0, h1, h2 = H0, H1 * fine, H2 * fine
    x0, y0, nx, ny = -8.0, -1.5, int(round(16.0 / h0)), int(round(5.0 / h0))
    X, Y = cells(x0, y0, nx, ny, h0)
    cond, m = lap_geometry(X, Y, edge, crevice, l_t)
    p = lap_props(m, state)
    p_gel, p_glass = float(p[m == GEL].max()), float(p[m == GLASS].max())
    V0 = fv_planar(p, cond, h0, x0, y0, q_top=1e3 * p_gel, q_bot=-1e3 * p_glass,     # V/mm: 1 kV/mm each side
                   shape=lambda x, y: lap_shape(x, y, edge, l_t))
    at0 = interp2(V0, x0, y0, h0)
    out = dict(far_gel_check_kV_mm=float(abs(at0(np.array([-6.5]), np.array([0.2])) - at0(np.array([-6.5]),
                                                                                          np.array([0.4])))[0] / 0.2e3),
               far_glass_check_kV_mm=float(abs(at0(np.array([6.5]), np.array([-0.4])) - at0(np.array([6.5]),
                                                                                            np.array([-0.8])))[0] / 0.4e3))
    if side in ("both", "outer"):
        box1 = (-1.3, 0.0, 1.55 + l_t, 0.6)
        V1, X1, Y1, c1, m1 = nested(edge, crevice, state, l_t, (V0, x0, y0, h0), box1, h1)
        E1 = efield(V1, h1)
        dc1 = far_dist(c1, h1)
        p1 = lap_props(m1, state)                       # the PEEK's far field is p_gel / p_peek of the gel's
        e_pk_far = float(p1[m1 == GEL].max() / p1[m1 == PEEK].max())
        out["peek_over_step_beta"] = float(E1[(m1 == PEEK) & (dc1 >= 2 * h1) & (X1 < -0.5)].max()) / e_pk_far
        pts, nrm = ramp_surface(l_t)
        out["bend_beta"] = normal_peak(V1, box1[0], box1[1], h1, pts, nrm)[0]
        # the free edge: a box about it at h2, and for the sharpest corners another at r_c / 25
        if edge[0] == "rc":
            box2 = (-W_LAP - 0.06, 2 * T_FOIL - 0.06, 0.12, 0.12)
        else:
            box2 = (-W_LAP - edge[1] - 0.04, T_FOIL - 0.02, edge[1] + 0.1, 0.14)
        V2 = nested(edge, crevice, state, l_t, (V1, box1[0], box1[1], h1), box2, h2)[0]
        pts, nrm = edge_surface(edge)
        par, hp = (V2, box2[0], box2[1], h2), h2
        if edge[0] == "rc" and edge[1] / 25 * fine < h2:
            h3 = edge[1] / 25 * fine
            box3 = (-W_LAP - 4 * edge[1], 2 * T_FOIL - 5 * edge[1], 9 * edge[1], 9 * edge[1])
            V3 = nested(edge, crevice, state, l_t, par, box3, h3)[0]
            par, hp = (V3, box3[0], box3[1], h3), h3
        out["step_beta"], out["step_at_mm"] = normal_peak(par[0], par[1], par[2], hp, pts, nrm)
        out["step_h_mm"] = hp
    if side in ("both", "inner"):
        box1 = (-0.3, -0.25, l_t + 0.6, 0.5)
        V1, X1, Y1, c1, m1 = nested(edge, crevice, state, l_t, (V0, x0, y0, h0), box1, h1)
        E1 = efield(V1, h1)
        dc1 = far_dist(c1, h1)
        crev = (m1 == crevice) & (X1 > 0) & (X1 < l_t) & (Y1 >= 0)
        if crevice == GEL:
            out["crevice_gel_peak_per_glass"] = float(E1[crev & (dc1 >= 2 * h1)].max())
            # the corner where the lower gore's cut edge meets the glass (straight, grid-aligned faces), fine
            box3 = (-0.03, -0.03, 0.06, 0.06)
            V3, X3, Y3, c3, m3 = nested(edge, crevice, state, l_t, (V1, box1[0], box1[1], h1), box3, h2)
            E3 = efield(V3, h2)
            dc3 = far_dist(c3, h2)
            ec = np.zeros(c3.shape, dtype=bool)
            ec[:4, :] = ec[-4:, :] = ec[:, :4] = ec[:, -4:] = True
            for k_off in (2, 4, 8):
                sel = (m3 == GEL) & ~c3 & ~ec & (dc3 >= k_off * h2 - 1e-12)
                out[f"crevice_corner_per_glass_{k_off}cells"] = float(E3[sel].max())
        else:
            # the void: the glass's surface under it against the conductor (0 V), kV per kV/mm of the glass's field
            at1 = interp2(V1, box1[0], box1[1], h1)
            xs = np.linspace(0.005, l_t - 0.005, 60)
            vs = np.abs(at1(xs, np.full(xs.shape, 0.5 * h1))) / 1e3
            gap = np.minimum(xs, T_FOIL * (1 - xs / l_t) * math.cos(math.atan(T_FOIL / l_t)))
            out["void"] = [dict(x_mm=float(a), gap_mm=float(g), dV_kV_per_kV_mm=float(v)) for a, g, v in zip(xs, gap, vs)]
            vmax = max(out["void"], key=lambda q: q["dV_kV_per_kV_mm"])
            out["void_dV_max_kV_per_kV_mm"] = vmax["dV_kV_per_kV_mm"]
            out["void_dV_at_mm"] = vmax["x_mm"]
            out["void_E_mean_per_glass"] = float(E1[crev & (dc1 >= 2 * h1)].mean())
    return out


def void_ratio(rows, e_glass):
    """the largest dV / Paschen over a void's points, the glass's far field e_glass (kV/mm)."""
    return max(q["dV_kV_per_kV_mm"] * e_glass / S.paschen_kV(q["gap_mm"]) for q in rows)


# --------------------------------------------------------------------------------------------- the closing joint
def ridge_beta(aspect, half_cyl=False, fine=1.0):
    """a ridge on a flat conductor in a uniform field (eps uniform, 1 kV/mm far off): a cosine of height
    delta = aspect * w over its base w (1 mm), or a half-cylinder of radius 0.25 mm; the peak field over the far field
    (2: the half-cylinder's exact value [OC])."""
    w = 1.0
    if half_cyl:
        a = 0.25

        def shape(X, Y):
            return (Y <= 0) | (np.hypot(X, Y) <= a)
        ph = np.radians(np.linspace(10, 170, 81))
        pts, nrm = np.c_[a * np.cos(ph), a * np.sin(ph)], np.c_[np.cos(ph), np.sin(ph)]
        top = a
    else:
        dl = aspect * w

        def shape(X, Y):
            return (Y <= 0) | ((np.abs(X) <= w / 2) & (Y <= dl * 0.5 * (1 + np.cos(2 * math.pi * X / w))))
        x = np.linspace(-0.25 * w, 0.25 * w, 81)
        y = dl * 0.5 * (1 + np.cos(2 * math.pi * x / w))
        dy = -dl * math.pi / w * np.sin(2 * math.pi * x / w)
        nn = np.hypot(dy, 1.0)
        pts, nrm = np.c_[x, y], np.c_[-dy / nn, 1.0 / nn]
        top = dl
    h0 = 0.01
    x0, y0, nx, ny = -4.0, -0.2, int(round(8.0 / h0)), int(round(5.2 / h0))
    X, Y = cells(x0, y0, nx, ny, h0)
    c = shape(X, Y)
    V0 = fv_planar(np.ones(c.shape), c, h0, x0, y0, q_top=1e3, q_bot=0.0, shape=shape)
    at0 = interp2(V0, x0, y0, h0)
    far = float(abs(at0(np.array([-3.5]), np.array([1.0])) - at0(np.array([-3.5]), np.array([2.0])))[0] / 1e3)
    h1 = min(max(top / 20, 0.001), 0.0025) * fine
    hw = 0.65
    bx = (-hw, -0.02, 2 * hw, top + 0.15)
    nx1, ny1 = int(round(bx[2] / h1)), int(round(bx[3] / h1))
    X1, Y1 = cells(bx[0], bx[1], nx1, ny1, h1)
    c1 = shape(X1, Y1)
    V1 = fv_planar(np.ones(c1.shape), c1, h1, bx[0], bx[1], vbc=interp2(V0, x0, y0, h0), shape=shape)
    e, at = normal_peak(V1, bx[0], bx[1], h1, pts, nrm)
    return dict(aspect=aspect if not half_cyl else 1.0, beta=e, at_mm=at, h_mm=h1, far_check_kV_mm=far)


def hub_ah_rounded(rec, sig, rc, groove="rect", h=S.H_HUB):
    """the hub as drawn with each AH end's outer corner rounded to rc (mm; the freed cells PEEK), as
    sim/hub_beads_settled.py's ah_conductor; returns the solution's interpolator and the field at the null."""
    import core_rings as CR
    import hub_locked as HL
    base = S.maps_fn(rec, sig, groove)

    def fn(ring, theta, coils, h_, hub_):
        r, z, p, cond = base(ring, theta, coils, h_, hub_)
        if rc > 0:
            R, Z = np.meshgrid(r, z, indexing="ij")
            ar, az = hub_["ah_r"], hub_["ah_z"][0]
            cut = ((cond == 1) & (R > ar - rc) & (R <= ar) & (Z >= az) & (Z < az + rc)
                   & (np.hypot(R - (ar - rc), Z - (az + rc)) > rc))
            cond = cond.copy()
            cond[cut] = 0
            p = p.copy()
            p[cut] = S.prop(S.materials(R, Z, rec, hub_, groove), hub_, sig)[cut]
        return r, z, p, cond
    res = CR.solve(HL.band(rec["theta_p"], rec["theta_e"]), 0.0, True, h, hub=B.hub_system(), keep=True, maps_fn=fn)
    V, at = B.hub_potential(res, rec["V_A_kV"] * 1e3, rec["V_B_kV"] * 1e3)
    return dict(V=V, at=at, E_null_kV_cm=abs(res["E_centre_kV_cm_per_kV"]) * rec["V_gap_kV"])


def polar_margin(rec):
    """the polar bead's peak in the gel with the AH ends rounded (0, 1.5, 2.5 mm), both grooves, each state: the margin
    to the gel's rating that a closing joint may take."""
    out = {}
    for label, sig in S.STATES:
        out[label] = []
        for rc in (0.0, 1.5, 2.5):
            hq = hub_ah_rounded(rec, sig, rc)
            row = dict(rc_mm=rc, E_null_kV_cm=hq["E_null_kV_cm"])
            for g in ("rect", S.REC_GROOVE):
                q = S.bead_state(rec, "pol", sig, hq, groove=g, wedge=False)
                row[g] = dict(E_gel_kV_mm=q["E_gel_kV_mm"], E_glass_kV_mm=q["E_glass_kV_mm"],
                              margin=E_GEL_RATING / q["E_gel_kV_mm"] - 1)
            out[label].append(row)
    return out


# --------------------------------------------------------------------------------- the faces and the bead's void
def face_fields(rec, hubq, sig):
    """the normal fields on ring B's faces: between the beads (the hub's cells) and near each bead (its box)."""
    hub = B.hub_system()
    at, h = hubq["at"], hubq["h_mm"]
    p_out = (hub["eps_ret"] / hub["eps_fill"]) if sig is None else (D.SIG["peek"] / D.SIG["gel"])   # PEEK's E -> gel's
    rows = []
    for th in np.linspace(rec["theta_p"], rec["theta_e"], 60):
        u = (math.sin(math.radians(th)), math.cos(math.radians(th)))

        def Vr(rho):
            return float(at(np.array([rho * u[0]]), np.array([rho * u[1]]))[0])
        a, b = hub["R_v"] - h, hub["R_v"] - 3 * h
        e_gl = abs(Vr(a) - Vr(b)) / (2 * h) / 1e3
        c, d = hub["R_v"] + 0.5 + h, hub["R_v"] + 0.5 + 3 * h
        e_pk = abs(Vr(c) - Vr(d)) / (2 * h) / 1e3
        rows.append(dict(theta_deg=float(th), E_glass_kV_mm=e_gl, E_peek_kV_mm=e_pk, E_gel_kV_mm=e_pk * p_out))
    out = dict(band=rows)
    # between the grooves (each groove's wall rho + 0.5 off the bead's centre-line), the hub's own reading
    tp = rec["theta_p"] + math.degrees((rec["rho_pol_mm"] + 0.5 + 0.5) / hub["R_v"])
    te = rec["theta_e"] - math.degrees((rec["rho_eq_mm"] + 0.5 + 0.5) / hub["R_v"])
    mid = [q for q in rows if tp <= q["theta_deg"] <= te]
    out["between"] = dict(theta_deg=(tp, te), E_gel_max_kV_mm=max(q["E_gel_kV_mm"] for q in mid),
                          E_glass_max_kV_mm=max(q["E_glass_kV_mm"] for q in mid),
                          E_glass_min_kV_mm=min(q["E_glass_kV_mm"] for q in mid))
    out["near"] = {}
    for which in ("pol", "eq"):
        bead = S.bead_box(rec, which, sig, at)
        V, r0, z0 = bead["V"], bead["bx"]["r0"], bead["bx"]["z0"]
        atb = S.interp(V, r0, z0, S.H_BOX)
        th_c, rb = S.rec_beads(rec)[which]
        sgn = 1.0 if which == "pol" else -1.0                   # into the band
        dep = 2 * S.H_BOX
        near = []
        for s in S_FACE:
            t = math.radians(th_c) + sgn * s / hub["R_v"]
            u = (math.sin(t), math.cos(t))

            def Vb(rho):
                return float(atb(np.array([rho * u[0]]), np.array([rho * u[1]]))[0])
            vB = rec["V_B_kV"] * 1e3
            e_gl = abs((3 * vB - 4 * Vb(hub["R_v"] - dep) + Vb(hub["R_v"] - 2 * dep)) / (2 * dep)) / 1e3
            top = hub["R_v"] + T_FOIL
            e_gel = abs((3 * vB - 4 * Vb(top + dep) + Vb(top + 2 * dep)) / (2 * dep)) / 1e3
            near.append(dict(s_mm=s, E_glass_kV_mm=e_gl, E_gel_kV_mm=e_gel))
        out["near"][which] = near
    return out


def void_mask(R, Z, rec, which, s_v):
    """the cells of the wedge between the bead and the bare glass, within s_v (mm, along the glass) of the contact."""
    hub = B.hub_system()
    th_c, rb = S.rec_beads(rec)[which]
    rho = np.hypot(R, Z)
    pol = np.degrees(np.arctan2(R, Z))
    s = (pol - th_c) * math.pi / 180 * hub["R_v"] * (-1.0 if which == "pol" else 1.0)    # beyond the contact: s > 0
    cx, cz = (hub["R_v"] + rb) * math.sin(math.radians(th_c)), (hub["R_v"] + rb) * math.cos(math.radians(th_c))
    outside = np.hypot(R - cx, Z - cz) > rb
    gaps = np.full(R.shape, -1.0)
    sel = (s > 0) & (s <= s_v) & (rho >= hub["R_v"])
    for k in np.flatnonzero(sel):
        g = S.gap_mm(rec, which, float(s.flat[k]), hub)
        gaps.flat[k] = g if g is not None else -1.0
    return sel & outside & (rho - hub["R_v"] <= gaps)


def void_props(m, vm, hub, sig, kind):
    """the cells' property with the void vm: eps 1 at switch-on; settled, open air's sigma (kind AIR) or an
    insulator's (kind VOID)."""
    p = S.prop(m, hub, sig)
    p[vm] = 1.0 if sig is None else (D.SIG["air"] if kind == AIR else SIG_VOID) / EPS0
    return p


def bead_void(rec, which, sig, hubq, s_v, kind=AIR):
    """the bead's box and its contact's box with a void out to s_v; the void's dV against Paschen at each s."""
    hub = B.hub_system()
    th, rb = S.rec_beads(rec)[which]
    bx = B._edge_box(rec["theta_p"], rec["theta_e"], rb, which, S.H_BOX, S.HALF_BOX)
    R, Z = S.grid(bx["r0"], bx["z0"], bx["n"], S.H_BOX)
    m = S.materials(R, Z, rec, hub, "rect")
    vm = void_mask(R, Z, rec, which, s_v)
    V = B.local_fv(void_props(m, vm, hub, sig, kind), bx["cond"], rec["V_B_kV"] * 1e3, S.H_BOX, bx["r0"], bx["z0"],
                   hubq["at"])
    # the contact's box
    cr, cz = hub["R_v"] * math.sin(math.radians(th)), hub["R_v"] * math.cos(math.radians(th))
    bcx, bcz = (hub["R_v"] + rb) * math.sin(math.radians(th)), (hub["R_v"] + rb) * math.cos(math.radians(th))
    n = int(round(2 * S.HALF_W / S.H_W))
    r0, z0 = cr - S.HALF_W, cz - S.HALF_W
    Rw, Zw = S.grid(r0, z0, n, S.H_W)
    rho = np.hypot(Rw, Zw)
    pol = np.degrees(np.arctan2(Rw, Zw))
    mw = S.materials(Rw, Zw, rec, hub, "rect")
    vmw = void_mask(Rw, Zw, rec, which, s_v)
    cond = (rho >= hub["R_v"]) & (rho <= hub["R_v"] + T_FOIL) & (pol >= rec["theta_p"]) & (pol <= rec["theta_e"])
    cond |= np.hypot(Rw - bcx, Zw - bcz) <= rb
    Vw = B.local_fv(void_props(mw, vmw, hub, sig, kind), cond, rec["V_B_kV"] * 1e3, S.H_W, r0, z0,
                    S.interp(V, bx["r0"], bx["z0"], S.H_BOX))
    ss_w = [s for s in S.S_WEDGE if s <= min(s_v, S.HALF_W - 0.05)]
    ss_b = [s for s in S.S_BOX if s <= s_v] + ([s_v] if s_v > S.HALF_W - 0.05 and s_v not in S.S_BOX else [])
    rows = S.wedge_rows(rec, which, sig, Vw, r0, z0, S.H_W, ss_w)
    rows += S.wedge_rows(rec, which, sig, V, bx["r0"], bx["z0"], S.H_BOX, [s for s in ss_b if s > S.HALF_W - 0.05])
    rows = [dict((k, q[k]) for k in ("s_mm", "gap_mm", "dV_kV", "paschen_kV", "paschen_ratio")) for q in rows]
    best = max((q for q in rows if q["paschen_ratio"] is not None), key=lambda q: q["paschen_ratio"])
    return dict(s_void_mm=s_v, kind="air" if kind == AIR else "insulating", rows=rows, paschen_max=best)


# ----------------------------------------------------------------------------------------------------------- main
def main():
    t0 = time.time()
    rec = json.load(open(os.path.join(HERE, "hub_rings_build_results.json")))["record"]
    out = dict(note="see the module docstring", t_foil_mm=T_FOIL, w_lap_mm=W_LAP, E_gel_rating_kV_mm=E_GEL_RATING,
               paschen=S.PASCHEN, boxes_mm=(H0, H1, H2))
    # 3. the check first: a half-cylinder ridge gives 2
    out["ridge_check"] = ridge_beta(None, half_cyl=True)
    print("ridge check (half-cylinder, exact 2):", json.dumps(out["ridge_check"]), flush=True)
    out["ridge"] = [ridge_beta(a) for a in RIDGE]
    for q in out["ridge"]:
        print(f"  ridge delta/w {q['aspect']:g}: beta {q['beta']:.4f} (cell {q['h_mm'] * 1e3:.2f} um)", flush=True)
    out["ridge_mesh"] = ridge_beta(0.03, fine=0.5)
    print("  ridge mesh (0.03, half the cells):", json.dumps(out["ridge_mesh"]), flush=True)
    out["polar_margin"] = polar_margin(rec)
    for label, rows in out["polar_margin"].items():
        print(f"  the polar bead, {label}: " + "; ".join(
            f"AH end r {q['rc_mm']:g}: gel {q['rect']['E_gel_kV_mm']:.3f} (margin {q['rect']['margin']:+.2%}), full-round "
            f"{q[S.REC_GROOVE]['E_gel_kV_mm']:.3f} ({q[S.REC_GROOVE]['margin']:+.2%})" for q in rows), flush=True)
    # 2. the lap, unit far fields: the outer side at switch-on and settled (it holds the gel and the PEEK only), the
    # crevice in each state
    out["lap"] = {}
    for label, k in HUB_STATES:
        out["lap"][label] = {}
        if label == "switch-on" or k == RATIOS[0]:
            for rc in R_C:
                q = lap_solve(("rc", rc), GEL, k, side="outer")
                out["lap"][label][f"edge r_c {rc:g}"] = q
                print(f"  lap {label}, edge r_c {rc:g} mm: step beta {q['step_beta']:.3f} (cell {q['step_h_mm'] * 1e3:.2f}"
                      f" um), PEEK over it {q['peek_over_step_beta']:.3f}, the bend {q['bend_beta']:.3f}; far gel (check) "
                      f"{q['far_gel_check_kV_mm']:.4f}", flush=True)
            for wf in W_F:
                q = lap_solve(("fillet", wf), GEL, k, side="outer")
                out["lap"][label][f"fillet {wf:g}"] = q
                print(f"  lap {label}, fillet {wf:g} mm: step beta {q['step_beta']:.3f}", flush=True)
        fills = ((GEL, "gel"), (AIR, "void")) if k is None else ((GEL, "gel"), (AIR, "void"), (VOID, "void, insulating"))
        for lt in L_T:
            for crev, name in fills:
                q = lap_solve(("rc", 0.01), crev, k, l_t=lt, side="inner")
                out["lap"][label][f"crevice {name} L_t {lt:g}"] = q
                if crev == GEL:
                    print(f"  lap {label}, crevice gel, L_t {lt:g}: gel peak / glass far "
                          f"{q['crevice_gel_peak_per_glass']:.3f}, at the corner {q['crevice_corner_per_glass_4cells']:.3f}"
                          f" (8 cells {q['crevice_corner_per_glass_8cells']:.3f}); far glass (check) "
                          f"{q['far_glass_check_kV_mm']:.4f}", flush=True)
                else:
                    print(f"  lap {label}, crevice void, L_t {lt:g}: dV max {q['void_dV_max_kV_per_kV_mm']:.4f} kV per "
                          f"kV/mm at x {q['void_dV_at_mm']:.3f}; mean E / glass {q['void_E_mean_per_glass']:.3f}",
                          flush=True)
    out["lap_mesh"] = dict(step=lap_solve(("rc", 0.01), GEL, None, side="outer", fine=0.5),
                           void=lap_solve(("rc", 0.01), AIR, None, side="inner", fine=0.5),
                           gel=lap_solve(("rc", 0.01), GEL, RATIOS[-1], side="inner", fine=0.5))
    global SIG_VOID
    ins = lap_solve(("rc", 0.01), VOID, RATIOS[1], side="inner")["void_dV_max_kV_per_kV_mm"]
    SIG_VOID, keep = SIG_VOID / 10, SIG_VOID
    out["void_sigma_check"] = dict(sigma_S_m=(keep, SIG_VOID), dV_kV_per_kV_mm=(
        ins, lap_solve(("rc", 0.01), VOID, RATIOS[1], side="inner")["void_dV_max_kV_per_kV_mm"]))
    SIG_VOID = keep
    print("  the insulating void at a tenth of its sigma:", json.dumps(out["void_sigma_check"]), flush=True)
    print("  lap mesh (half the cells): step beta %.3f, void dV %.4f, gel crevice (ratio %g) %.3f / %.3f at 8 cells"
          % (out["lap_mesh"]["step"]["step_beta"], out["lap_mesh"]["void"]["void_dV_max_kV_per_kV_mm"], RATIOS[-1],
             out["lap_mesh"]["gel"]["crevice_gel_peak_per_glass"], out["lap_mesh"]["gel"]["crevice_corner_per_glass_8cells"]),
          flush=True)
    # 1. the faces, and 4. the bead's void, in each state
    out["faces"], out["bead_void"] = {}, {}
    for label, k in HUB_STATES:
        sig = None if k is None else k * D.SIG["gel"]
        hq = S.hub_solve(rec, sig)
        out["faces"][label] = face_fields(rec, hq, sig)
        f = out["faces"][label]
        print(f"faces {label}: between the beads gel <= {f['between']['E_gel_max_kV_mm']:.3f}, glass "
              f"{f['between']['E_glass_min_kV_mm']:.3f}-{f['between']['E_glass_max_kV_mm']:.3f} kV/mm; near the beads "
              + "; ".join(f"{w}: " + ", ".join(f"{q['s_mm']:g} mm {q['E_glass_kV_mm']:.2f}/{q['E_gel_kV_mm']:.2f}"
                                                for q in f["near"][w]) for w in ("pol", "eq")), flush=True)
        out["bead_void"][label] = {}
        for which in ("pol", "eq"):
            kinds = (AIR,) if k is None else (AIR, VOID)
            out["bead_void"][label][which] = [bead_void(rec, which, sig, hq, sv, kind) for kind in kinds
                                              for sv in S_VOID]
            for q in out["bead_void"][label][which]:
                pm = q["paschen_max"]
                print(f"  void ({q['kind']}) at the {which} bead, {label}, to {q['s_void_mm']:g} mm: dV/Paschen "
                      f"{pm['paschen_ratio']:.2f} at {pm['s_mm']:g} mm (gap {pm['gap_mm']:.3f} mm, {pm['dV_kV']:.3f} kV)",
                      flush=True)
        del hq
    # 5. the combinations: each state's face fields on the lap's factors (the outer side's settled factors from the
    # first settled state)
    out["combined"] = {}
    for label, k in HUB_STATES:
        lap = out["lap"][label]
        outer = out["lap"]["switch-on" if k is None else HUB_STATES[1][0]]
        f = out["faces"][label]
        e_gel_mid = f["between"]["E_gel_max_kV_mm"]
        e_gl_mid = f["between"]["E_glass_max_kV_mm"]
        near = [q for w in ("pol", "eq") for q in f["near"][w] if q["s_mm"] >= 0.5]
        e_gl_near = max(q["E_glass_kV_mm"] for q in near)
        e_gel_near = max(q["E_gel_kV_mm"] for q in near)
        row = dict(E_gel_face_between_kV_mm=e_gel_mid, E_glass_between_kV_mm=e_gl_mid,
                   E_glass_near_beads_kV_mm=e_gl_near, E_gel_near_beads_kV_mm=e_gel_near, step={}, crevice={})
        for key, q in outer.items():
            if key.startswith("edge") or key.startswith("fillet"):
                row["step"][key] = dict(E_gel_peak_kV_mm=q["step_beta"] * max(e_gel_mid, e_gel_near))
        for key, q in lap.items():
            if key.startswith("crevice gel"):
                row["crevice"][key] = dict(E_gel_between_kV_mm=q["crevice_gel_peak_per_glass"] * e_gl_mid,
                                           E_gel_near_beads_kV_mm=q["crevice_gel_peak_per_glass"] * e_gl_near,
                                           E_gel_corner_near_beads_kV_mm=q["crevice_corner_per_glass_8cells"] * e_gl_near)
            elif key.startswith("crevice void"):        # open air's sigma, or insulating
                row["crevice"][key] = dict(paschen_between=void_ratio(q["void"], e_gl_mid),
                                           paschen_near_beads=void_ratio(q["void"], e_gl_near))
        out["combined"][label] = row
        print(f"combined {label}: " + json.dumps(row), flush=True)
    out["run_s"] = time.time() - t0
    json.dump(out, open(os.path.join(HERE, "hub_joints_results.json"), "w"), indent=1, default=float)


if __name__ == "__main__":
    main()
