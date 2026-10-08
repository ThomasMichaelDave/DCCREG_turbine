"""sim/vane_cell.py -- the 2-D vane cell of sim/stack_sizing (one sector period at radius r: stator vane | gap | rotor
vane | gap, periodic both ways) with the vanes' edge profile as a choice, and the field at a vane's rim.
  edge "square": stack_sizing._cell exactly (the self-test checks it);
  edge "round":  a full round on the sectors' radial edges, radius half the vane thickness [IR].
cell() gives C per gap per mm of radius; solve() also returns the potential and the conductor map (for the drawings);
tube_caps() integrates C_max / C_min over r_in .. r_out as stack_sizing.tube_caps does (the inner / outer rims stay its
fixed C_edge floor). edge_field() is the peak surface field at the edge of a plate between two planes, g from its
faces: a stator vane's inner rim over the rotor vane's ring, a rotor vane's outer rim under the stator vane's ring.
[OC] the Laplace solves; [IR] the 2-D cell, the full round on the grid; [RH] the edge field as a corona estimate.
Usage: python3 sim/vane_cell.py      (self-tests)
"""
import math
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import stack_sizing as SS          # noqa: E402


def grid(r, p):
    """stack_sizing._cell's grid: conductor nodes fixed at their centres, so the electrical gap is exactly g and the
    vane is nt rows (geometric thickness (nt + 1) hz ~ t)."""
    period_deg = 360.0 / (p["N_sec"] / 2.0)
    P = math.radians(period_deg) * r
    h = p["h_mm"]
    nx = max(16, int(round(P / h)))
    t, g = p["t_vaneMm"], p["g_vMm"]
    ng = max(4, int(round(g / h)))
    hz = g / (ng + 1)
    nt = max(1, int(round(t / hz)) - 1)
    return dict(period_deg=period_deg, nx=nx, hx=P / nx, ng=ng, hz=hz, nt=nt, nz=2 * (nt + ng),
                x=(np.arange(nx) + 0.5) * (P / nx), z=(np.arange(2 * (nt + ng)) + 0.5) * hz)


def vane(G, r, c_deg, w_deg, k0, edge):
    """(nx, nz) map of one vane: the sector w_deg wide centred on c_deg, conductor rows k0 .. k0 + nt - 1. A full round
    keeps the sector's width at its mid-plane and runs through the outermost conductor rows."""
    per = G["period_deg"]
    d_deg = (np.degrees(G["x"] / r) - c_deg + 0.5 * per) % per - 0.5 * per
    band = np.abs(d_deg) < 0.5 * w_deg
    rows = np.arange(k0, k0 + G["nt"])
    m = np.zeros((G["nx"], G["nz"]), dtype=bool)
    if edge == "square":
        m[np.ix_(band, rows)] = True
        return m
    R = 0.5 * (G["nt"] - 1) * G["hz"]
    d = np.abs(r * np.radians(d_deg))[band]                    # mm along the arc from the sector's centre line
    flat = r * math.radians(0.5 * w_deg) - R                   # the faces end here and the round begins
    dz = G["z"][rows] - (G["z"][k0] + R)
    m[np.ix_(band, rows)] = (d[:, None] <= flat) | ((d[:, None] - flat) ** 2 + dz[None, :] ** 2 <= R * R * (1 + 1e-9))
    return m


def solve(r, p, shift_deg, edge=None):
    """the cell at radius r with the rotor vanes turned by shift_deg from aligned: C per gap per mm of radius (F/mm),
    the potential (stator 1 V, rotor 0 V), the conductor map (1 stator, 0 rotor, -1 free) and the grid."""
    edge = edge or p.get("edge", "square")
    G = grid(r, p)
    per, nt, ng = G["period_deg"], G["nt"], G["ng"]
    cond = np.full((G["nx"], G["nz"]), -1, dtype=np.int8)
    cond[vane(G, r, 0.5 * per, p["ws_deg"], 0, edge)] = 1                       # stator vane at 1 V
    cond[vane(G, r, 0.5 * per + shift_deg, p["wr_deg"], nt + ng, edge)] = 0     # rotor vane at 0 V
    # from here on stack_sizing._cell, operation for operation
    hx, hz = G["hx"], G["hz"]
    fixed = cond >= 0
    V = np.where(cond == 1, 1.0, 0.0)
    free = ~fixed
    ax, az = 1.0 / hx ** 2, 1.0 / hz ** 2
    diag = 2 * ax + 2 * az

    def lap(U):
        return (ax * (np.roll(U, 1, 0) + np.roll(U, -1, 0)) + az * (np.roll(U, 1, 1) + np.roll(U, -1, 1)) - diag * U)
    Vb = np.where(fixed, V, 0.0)
    b = lap(Vb) * free

    def A(u):
        U = np.where(free, u, 0.0)
        return -lap(U) * free
    u = np.zeros_like(V); res = b - A(u); pdir = res * (1.0 / diag); z = pdir.copy()
    rz = float(np.sum(res * z))
    b2 = float(np.sum(b * b)) or 1.0
    for it in range(20000):
        Ap = A(pdir)
        alpha = rz / float(np.sum(pdir * Ap))
        u += alpha * pdir; res -= alpha * Ap
        if float(np.sum(res * res)) < 1e-20 * b2:
            break
        z = res * (1.0 / diag)
        rz_new = float(np.sum(res * z))
        pdir = z + (rz_new / rz) * pdir; rz = rz_new
    Vt = np.where(free, u, Vb)
    ex = np.roll(Vt, -1, 0) - Vt; ez = np.roll(Vt, -1, 1) - Vt
    W2 = np.sum(ex * ex) * (hz / hx) + np.sum(ez * ez) * (hx / hz)
    C = SS.EPS0_MM * SS.PS.eps_r(p) * W2 / 2.0
    return dict(G, C=C, it=it, V=Vt, cond=cond, edge=edge)


def cell(r, p, shift_deg):
    """stack_sizing._cell's signature: (C per gap per mm of radius, CG iterations)."""
    s = solve(r, p, shift_deg)
    return s["C"], s["it"]


def tube_caps(p):
    """stack_sizing.tube_caps with this cell (and so with p['edge'])."""
    n_gap = 2 * int(p["n_plates"]) - 1
    rs = np.linspace(p["r_inMm"], p["r_outMm"], int(p["n_r"]))
    period_deg = 360.0 / (p["N_sec"] / 2.0)
    cmx = [cell(r, p, 0.0)[0] for r in rs]
    cmn = [cell(r, p, 0.5 * period_deg)[0] for r in rs]
    n_per = p["N_sec"] / 2.0
    integ = lambda y: n_per * float(np.sum(0.5 * (np.array(y[1:]) + np.array(y[:-1])) * np.diff(rs))) * 1e12
    gmax, gmin = integ(cmx), integ(cmn)
    return dict(n_gap=n_gap, per_gap_max_pF=gmax, per_gap_min_pF=gmin, C_max=n_gap * gmax,
                C_min=n_gap * gmin + p["C_edge_pF"], radii=list(map(float, rs)),
                c_max_pF_per_mm=[c * 1e12 for c in cmx], c_min_pF_per_mm=[c * 1e12 for c in cmn])


# ------------------------------------------------------------------------------------- the field at a plate's edge
def _laplace(inside, V_in, top=0.0, right=0.0, exact=None, xs=None, zs=None):
    """5-point Laplace on a uniform (nx, nz) grid: V_in on the conductor nodes. Without `exact`: mirror (Neumann) on
    the left column and the bottom row (z = 0, the plate's mid-plane), `top` one row above the last, `right` one column
    after the last. With `exact(x, z)`: that potential on every node just outside the grid (xs, zs: node positions)."""
    import scipy.sparse as sp
    import scipy.sparse.linalg as spl
    nx, nz = inside.shape
    fr = ~inside
    idx = -np.ones((nx, nz), dtype=np.int64)
    idx[fr] = np.arange(int(fr.sum()))
    I, K = np.nonzero(fr)
    me = idx[I, K]
    rows, cols, vals = [me], [me], [np.full(len(me), 4.0)]
    rhs = np.zeros(len(me))
    for di, dk in ((1, 0), (-1, 0), (0, 1), (0, -1)):
        i2, k2 = I + di, K + dk
        if exact is None:
            i2, k2 = np.where(i2 < 0, 1, i2), np.where(k2 < 0, 1, k2)
            out_r, out_t = i2 >= nx, k2 >= nz
            rhs[out_r] += right
            rhs[out_t & ~out_r] += top
            outside = out_r | out_t
        else:
            outside = (i2 < 0) | (i2 >= nx) | (k2 < 0) | (k2 >= nz)
            h = xs[1] - xs[0]
            rhs[outside] += exact(xs[0] + i2[outside] * h, zs[0] + k2[outside] * h)
        i2c, k2c = np.clip(i2, 0, nx - 1), np.clip(k2, 0, nz - 1)
        cnd = ~outside & inside[i2c, k2c]
        rhs[cnd] += V_in
        nb = ~outside & ~inside[i2c, k2c]
        rows.append(me[nb]); cols.append(idx[i2c[nb], k2c[nb]]); vals.append(-np.ones(int(nb.sum())))
    A = sp.csr_matrix((np.concatenate(vals), (np.concatenate(rows), np.concatenate(cols))), shape=(len(me), len(me)))
    V = np.full((nx, nz), float(V_in))
    V[fr] = spl.spsolve(A.tocsc(), rhs)
    return V


def _round_field(V, X, Z, xc, zc, R, h, V0, front, lo=3.0, hi=12.0, bin_deg=2.0):
    """the surface field on a round of radius R centred at (xc, zc). Per 2 deg of angle, the potential lo..hi cells off
    the true circle is fitted with a cylinder's log law, V = c0 - E R ln(rho / R): c0 takes up the staircase's shift
    of the effective surface (which a one-parameter read magnifies), E is the field at rho = R. front(X, Z) picks the
    face to read. Returns the angles (deg, atan2 about the centre) and the field (per volt of V0)."""
    rho = np.hypot(X - xc, Z - zc)
    shell = (rho > R + lo * h) & (rho < R + hi * h) & front(X, Z)
    L, Vs = np.log(rho[shell] / R), V[shell] / V0
    phi = np.degrees(np.arctan2(Z[shell] - zc, X[shell] - xc))
    bins = np.arange(-180.0, 180.0 + bin_deg, bin_deg)
    k = np.digitize(phi, bins)
    ang, val = [], []
    for j in range(1, len(bins)):
        m = k == j
        if m.sum() >= 4:
            c = np.linalg.lstsq(np.c_[np.ones(int(m.sum())), -L[m]], Vs[m], rcond=None)[0]
            ang.append(0.5 * (bins[j - 1] + bins[j])); val.append(float(c[1]) / R)
    return np.array(ang), np.array(val)


def edge_field(t, g, edge="round", h=0.05, span=None, field=False):
    """peak surface field (per volt, 1/mm) at the edge of a plate t thick at 1 V between two grounded planes g from
    its faces: half domain, the plate's mid-plane a mirror. "round": a full round, radius t/2; "square": the field one
    cell diagonally off the corner, which grows without bound as h -> 0 (for the trend only).
    Returns dict(E_peak_per_V, E_face_per_V = 1 / g, enhancement, angle_deg[, profile][, V, xs, zs if field])."""
    H = 0.5 * t + g
    nz = int(round(H / h)); h = H / nz                       # nodes z = 0 .. H - h; the plane is the row z = H
    span = span or (3.0 * H, 3.0 * H)
    nx = int(round((span[0] + span[1]) / h))
    xs, zs = -span[0] + h * np.arange(nx), h * np.arange(nz)
    X, Z = np.meshgrid(xs, zs, indexing="ij")
    R = 0.5 * t
    if edge == "round":
        inside = ((X <= -R) & (Z <= R + 1e-9)) | ((X + R) ** 2 + Z ** 2 <= R * R * (1 + 1e-9))
    else:
        inside = (X <= 1e-9) & (Z <= R + 1e-9)
    V = _laplace(inside, 1.0)
    out = dict(E_face_per_V=1.0 / g)
    if edge == "round":
        ang, val = _round_field(V, X, Z, -R, 0.0, R, h, 1.0, lambda x, z: x >= -R)
        j = int(np.argmax(val))
        out.update(E_peak_per_V=float(val[j]), angle_deg=float(ang[j]), profile=(ang.tolist(), val.tolist()))
    else:
        i0, k0 = int(np.argmin(np.abs(xs))), int(np.argmin(np.abs(zs - R)))
        out.update(E_peak_per_V=float((1.0 - V[i0 + 1, k0 + 1]) / (math.sqrt(2.0) * h)), angle_deg=45.0)
    out["enhancement"] = out["E_peak_per_V"] / out["E_face_per_V"]
    if field:
        out.update(V=V, xs=xs, zs=zs)
    return out


def peek_kV_per_cm(r_mm, delta=1.0, m=1.0):
    """Peek's corona onset at the surface of a cylinder of radius r in air (kV/cm, peak) [OC: empirical]."""
    r = 0.1 * r_mm
    return 31.0 * delta * m * (1.0 + 0.308 / math.sqrt(delta * r))


def _cylinder_plane_check(R=2.0, d=6.0, h=0.05):
    """the edge-field reader against the exact cylinder over a plane: radius R, its surface d above the plane, at 1 V.
    The grid's boundary carries the exact potential (line charges at +-a), so only the reader and the staircase are
    tested. Returns (field read at the point facing the plane, exact)."""
    hc = d + R
    a = math.sqrt(hc * hc - R * R)
    lam = 1.0 / math.log((hc + a) / R)
    exact = lambda x, z: lam * 0.5 * np.log((x * x + (z + a) ** 2) / (x * x + (z - a) ** 2))
    xs = -3.0 * hc + h * np.arange(int(round(6.0 * hc / h)))
    zs = 0.5 * h + h * np.arange(int(round(3.0 * hc / h)))
    X, Z = np.meshgrid(xs, zs, indexing="ij")
    V = _laplace(X ** 2 + (Z - hc) ** 2 <= R * R, 1.0, exact=exact, xs=xs, zs=zs)
    ang, val = _round_field(V, X, Z, 0.0, hc, R, h, 1.0, lambda x, z: z <= hc)
    near = np.abs(ang + 90.0) <= 2.0                          # -90 deg: straight down, toward the plane
    return float(np.mean(val[near])), a / (d * R * math.log((hc + a) / R))


def self_test(log=print):
    ok = True
    # 1. square edges reproduce stack_sizing._cell
    p = dict(SS.TUBE_DEFAULTS, g_vMm=6.0, dielectric="air", ws_deg=24.0, wr_deg=22.0)
    for r, sh in ((50.0, 0.0), (100.0, 30.0), (150.0, 30.0)):
        a, b = cell(r, dict(p, edge="square"), sh)[0], SS._cell(r, p, sh)[0]
        ok &= abs(a / b - 1) < 1e-12
        log(f"  square cell r {r:.0f} shift {sh:.0f}: {a * 1e12:.6f} pF/mm against stack_sizing {b * 1e12:.6f}")
    # 2. a full round lowers both C, most where the edges dominate (minimum C)
    q = dict(p, t_vaneMm=4.0)
    sq = [cell(100.0, dict(q, edge="square"), s)[0] for s in (0.0, 30.0)]
    rd = [cell(100.0, dict(q, edge="round"), s)[0] for s in (0.0, 30.0)]
    ok &= rd[0] < sq[0] and rd[1] < sq[1] and rd[1] / sq[1] < rd[0] / sq[0]
    log(f"  4 mm at r 100: aligned {sq[0] * 1e12:.4f} -> {rd[0] * 1e12:.4f} pF/mm, minimum {sq[1] * 1e12:.4f} -> "
        f"{rd[1] * 1e12:.4f} pF/mm (square -> round)")
    # 3. wide plates: the aligned C tends to the parallel plate (one sector of overlap, per gap)
    w = dict(q, ws_deg=58.0, wr_deg=58.0, edge="round")
    c = cell(100.0, w, 0.0)[0]
    pp = SS.EPS0_MM * SS.PS.eps_r(w) * (100.0 * math.radians(58.0)) / 6.0
    ok &= 0.97 < c / pp < 1.10
    log(f"  58 deg plates, 4 mm round, r 100: {c / pp:.4f} x the parallel plate")
    # 4. the edge-field reader against the exact cylinder over a plane
    e_fd, e_ex = _cylinder_plane_check()
    ok &= abs(e_fd / e_ex - 1) < 0.015
    log(f"  cylinder r 2 over a plane at 6: field reader {e_fd:.5f} against exact {e_ex:.5f} /mm ({e_fd / e_ex - 1:+.2%})")
    # 5. a full round's peak field converges with the grid; a square corner's does not
    e1, e2 = edge_field(4.0, 6.0, "round", h=0.1)["E_peak_per_V"], edge_field(4.0, 6.0, "round", h=0.05)["E_peak_per_V"]
    s1, s2 = edge_field(4.0, 6.0, "square", h=0.1)["E_peak_per_V"], edge_field(4.0, 6.0, "square", h=0.05)["E_peak_per_V"]
    ok &= abs(e2 / e1 - 1) < 0.01 and s2 / s1 > 1.1
    log(f"  4 mm plate, 6 mm gaps: round {e1:.5f} -> {e2:.5f} /mm (h 0.1 -> 0.05), square corner {s1:.4f} -> {s2:.4f}")
    log(f"vane_cell self-tests: {'PASS' if ok else 'FAIL'}")
    return ok


if __name__ == "__main__":
    sys.exit(0 if self_test() else 1)
