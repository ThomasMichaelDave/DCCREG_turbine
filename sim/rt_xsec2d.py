"""sim/rt_xsec2d.py -- design-loop scouting tool (2-D, independent of field_solve). 2-D C1 cross-section at radius r, unrolled over one 60-deg period: Ca_counter | ND1 carrier | C1 stator | air gap |
C1 rotor | A-disc carrier | CR_A. Variants: stator / rotor sector widths, carrier eps, guard strips (cond 3) in the
inter-sector gaps on the stator and/or rotor face plane. Returns per-mm C(1,RA), C(1,G), C(RA,G)."""
import sys, numpy as np, scipy.sparse as sp, scipy.sparse.linalg as spla
EPS0 = 8.8541878128e-15
def solve(r, shift_deg, h=0.25, eps_c=4.7, ws=30.0, wr=30.0, g=7.0, guard_s=0.0, guard_r=0.0, see=True,
          film=0.0, eps_f=5.4, film_full=True):
    P = np.radians(60.0) * r
    nx = int(round(P / h)); hx = P / nx
    t_nd1, t_disc, tf = 18.5, 18.25, 1.0
    z_ca0, z_ca1 = 30.0, 31.0
    z_c1s0 = z_ca1 + t_nd1; z_c1s1 = z_c1s0 + tf
    z_r0 = z_c1s1 + g; z_r1 = z_r0 + tf
    z_cr0 = z_r1 + t_disc; z_cr1 = z_cr0 + tf
    Z = z_cr1 + 30.0
    nz = int(round(Z / h)); hz = Z / nz
    x = (np.arange(nx) + 0.5) * hx; z = (np.arange(nz) + 0.5) * hz
    X, Zg = np.meshgrid(x, z, indexing="ij")
    eps = np.ones((nx, nz))
    eps[(Zg > z_ca1) & (Zg < z_c1s0)] = eps_c
    eps[(Zg > z_r1) & (Zg < z_cr0)] = eps_c
    cond = -np.ones((nx, nz), int)
    xs = X % P
    def band(xx, w):                      # a sector of width w (deg) centred at P/2
        ww = np.radians(w) * r
        return (xx >= 0.5 * P - 0.5 * ww) & (xx < 0.5 * P + 0.5 * ww)
    sh = np.radians(shift_deg) * r
    xr = (X - sh) % P
    if film > 0:                          # dielectric film on both C1 faces inside the gap (air left: g - 2 film)
        fs = (Zg > z_c1s1) & (Zg < z_c1s1 + film); fr = (Zg > z_r0 - film) & (Zg < z_r0)
        if not film_full:                 # film only under the foils (sectored film)
            fs &= band(xs, ws); fr &= band(xr, wr)
        eps[fs | fr] = eps_f
    stator = band(xs, ws); rotor = band(xr, wr)
    if see:
        cond[band(xs, 30.0) & (Zg > z_ca0) & (Zg < z_ca1)] = 0
        cond[rotor & (Zg > z_cr0) & (Zg < z_cr1)] = 2
    cond[stator & (Zg > z_c1s0) & (Zg < z_c1s1)] = 0
    cond[rotor & (Zg > z_r0) & (Zg < z_r1)] = 1
    if guard_s > 0:                       # strip centred in the stator gap (at x = 0 / P), stator face plane
        gw = np.radians(guard_s) * r
        cond[((xs < 0.5 * gw) | (xs >= P - 0.5 * gw)) & (Zg > z_c1s0) & (Zg < z_c1s1)] = 3
    if guard_r > 0:
        gw = np.radians(guard_r) * r
        cond[((xr < 0.5 * gw) | (xr >= P - 0.5 * gw)) & (Zg > z_r0) & (Zg < z_r1)] = 3
    nc = 4
    N = nx * nz; idx = np.arange(N).reshape(nx, nz)
    e = eps * EPS0; isc = cond >= 0
    hxh = np.where(isc, 0.0, 0.5 * hx / (e * hz)); hzh = np.where(isc, 0.0, 0.5 * hz / (e * hx))
    rows, cols, vals = [], [], []; diag = np.zeros(N)
    def add(I, J, G):
        I = I.ravel(); J = J.ravel(); G = G.ravel(); m = np.isfinite(G)
        I, J, G = I[m], J[m], G[m]
        rows.extend([I, J]); cols.extend([J, I]); vals.extend([-G, -G])
        diag[:] += np.bincount(I, G, N) + np.bincount(J, G, N)
    with np.errstate(divide="ignore"):
        add(idx, np.roll(idx, -1, 0), 1.0 / (hxh + np.roll(hxh, -1, 0)))
        add(idx[:, :-1], idx[:, 1:], 1.0 / (hzh[:, :-1] + hzh[:, 1:]))
        diag += np.bincount(idx[:, 0], 1.0 / np.where(hzh[:, 0] > 0, hzh[:, 0], np.inf), N)
        diag += np.bincount(idx[:, -1], 1.0 / np.where(hzh[:, -1] > 0, hzh[:, -1], np.inf), N)
    A = sp.csr_matrix((np.concatenate(vals), (np.concatenate(rows), np.concatenate(cols))), shape=(N, N)) + sp.diags(diag)
    c = cond.ravel(); u = np.nonzero(c < 0)[0]; k = np.nonzero(c >= 0)[0]
    present = sorted(set(c[k]))
    S = sp.csr_matrix((np.ones(k.size), (np.searchsorted(present, c[k]), k)), shape=(len(present), N))
    Auu = A[u][:, u].tocsc(); Auk = A[u][:, k]; Akk = A[k][:, k]
    B = -(Auk @ S[:, k].T).toarray()
    X_ = spla.splu(Auu).solve(B)
    C = (S[:, k] @ Akk @ S[:, k].T).toarray() + S[:, k] @ Auk.T @ X_
    get = lambda a, b: -C[present.index(a), present.index(b)] if a in present and b in present else 0.0
    return get(0, 1) + get(0, 2), get(0, 3), get(1, 3) + get(2, 3)   # C(1, R-A incl n18), C(1,G), C(RA,G)
if __name__ == "__main__":
    r = float(sys.argv[1]) if len(sys.argv) > 1 else 240.0
    P = dict(eps_c=2.1)
    cases = [("G10 30/30 (as built)", dict(eps_c=4.7)), ("PTFE 30/30", P)]
    for ws in (26.0, 22.0, 18.0):
        cases.append((f"PTFE stator {ws:g} / rotor 30", dict(P, ws=ws)))
    for f in (1.0, 2.0, 2.5):
        cases.append((f"PTFE 30/30 mica film {f:g}+{f:g} (sheet)", dict(P, film=f)))
        cases.append((f"PTFE 30/30 mica film {f:g}+{f:g} (sectored)", dict(P, film=f, film_full=False)))
    for ws in (22.0, 18.0):
        for f in (2.0, 2.5):
            cases.append((f"PTFE {ws:g}/30 sectored mica {f:g}+{f:g}", dict(P, ws=ws, film=f, film_full=False)))
            cases.append((f"PTFE {ws:g}/30 sectored mica {f:g}+{f:g}, no see", dict(P, ws=ws, film=f, film_full=False, see=False)))
    for name, kw in cases:
        a = solve(r, 0.0, **kw); b = solve(r, 30.0, **kw)
        print(f"{name:44s} aligned {a[0]*1e15:7.2f}  disaligned {b[0]*1e15:6.2f} fF/mm  kappa {a[0]/b[0]:5.2f}", flush=True)
