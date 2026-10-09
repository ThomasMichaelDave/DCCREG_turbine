"""sim/hub_drift.py -- what the bench test of the rings should see: the field at the AH null against time, from the
supply's start-up through its 120 Hz swing to the slow drift as the insulators leak (the rings as built:
sim/hub_rings_build.py's record and retainer system).

Three time scales [OC]:
  start-up   the pump charging the rings (sim/core_field.py's dc supply of the record, per cycle): the field follows the
             DC across the rings, as connected (k of the record's bands);
  120 Hz     the supply's ripple on the rings (the same run's last cycles): the field swings with it;
  minutes-   the leakage of the glass, the interface gel, the retainer, the coupler and the air: quasi-static current
  hours      continuity, C dV/dt + G V = b, on the hub's finite volumes (the record's bands at +-1/2, the AH, flanges
             and shaft at REF); implicit Euler from the electrostatic solution at switch-on, PER_DECADE steps a decade.
Conductivities at 25 C [IR datasheet-class]: borosilicate 1e-13 S/m (about 5e-13 at 40 C), silicone gel 1e-13, PEEK
1e-14, PEI 1e-15, G10 1e-13 (dry), air 2e-14 (its natural ions), the vacuum 0.
Usage: python3 sim/hub_drift.py [--procs 4]   (writes sim/hub_drift_results.json)
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

import numpy as np
import scipy.sparse as sp
import scipy.sparse.linalg as spla

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import core_field as CF            # noqa: E402
import hub_locked as HL            # noqa: E402
import hub_rings_build as B        # noqa: E402

EPS0 = 8.8541878128e-12
SIG = dict(glass=1e-13, glass40=5.4e-13, gel=1e-13, peek=1e-14, pei=1e-15, g10=1e-13, air=2e-14)   # S/m [IR]
CASES = {  # name: (retainer, glass, gel present)
    "PEEK retainer, gel, 25 C": ("peek", "glass", True),
    "PEI retainer, gel, 25 C": ("pei", "glass", True),
    "G10 retainer, gel, 25 C": ("g10", "glass", True),
    "PEEK retainer, gel, 40 C glass": ("peek", "glass40", True),
    "PEEK retainer, no gel (air gaps), 25 C": ("peek", "glass", False),
}
T_END = 6 * 3600.0                 # s
PER_DECADE = 60                    # implicit Euler steps per decade of time (one factorisation per decade) [OC]


def maps(rec, ret, glass, gel, h):
    """the hub's eps and sigma maps and its conductors (the record's bands)."""
    hub = B.hub_system()
    if not gel:
        hub = dict(hub, eps_fill=1.0)                                 # the pocket left as air
    r, z, eps, cond = HL.maps(HL.band(rec["theta_p"], rec["theta_e"]), 0.0, True, h, hub)
    R, Z = np.meshgrid(r, z, indexing="ij")
    rho = np.hypot(R, Z)
    sig = np.full(eps.shape, SIG["air"])                              # the air around the hub
    region = (R <= hub["ret_r"]) & (Z <= hub["ret_z"]) & (rho >= hub["R_v"])
    sig[region] = SIG[ret]
    sig[region & (R > hub["ret_r"] - hub["cpl_t"])] = SIG["g10"]      # the coupler
    sig[region & (rho < hub["R_v"] + hub["fill_t"])] = SIG["gel"] if gel else SIG["air"]
    sig[(rho >= hub["R_in"]) & (rho < hub["R_v"])] = SIG[glass]
    sig[rho < hub["R_in"]] = 0.0                                      # the vacuum
    return r, z, eps, sig, cond


def assemble(prop, cond, r, h, vring):
    """the finite-volume matrix of the free cells for a cell property (eps0 eps_r or sigma) and the right-hand side
    from the conductors (rings at vring, REF 0); the cage (r = R_box) and the vane (z = Z_box) at REF, the midplane at
    0 (the antisymmetric half)."""
    nr, nz = prop.shape
    hm = h * 1e-3
    rc = r * 1e-3
    free = cond == 0
    idx = -np.ones((nr, nz), dtype=np.int64)
    idx[free] = np.arange(int(free.sum()))
    n = int(free.sum())
    Vfix = np.where(cond == 2, vring, 0.0)
    diag, rhs = np.zeros(n), np.zeros(n)
    rows, cols, vals = [], [], []

    def hmean(a, b):
        with np.errstate(invalid="ignore", divide="ignore"):
            return np.where((a + b) > 0, 2 * a * b / (a + b), 0.0)

    def couple(ia, ja, ib, jb, G):
        fa, fb = free[ia, ja], free[ib, jb]
        a, b = idx[ia, ja], idx[ib, jb]
        both = fa & fb
        np.add.at(diag, a[fa], G[fa]); np.add.at(diag, b[fb], G[fb])
        rows.append(a[both]); cols.append(b[both]); vals.append(-G[both])
        rows.append(b[both]); cols.append(a[both]); vals.append(-G[both])
        m1, m2 = fa & ~fb, fb & ~fa
        np.add.at(rhs, a[m1], G[m1] * Vfix[ib, jb][m1]); np.add.at(rhs, b[m2], G[m2] * Vfix[ia, ja][m2])
    I, J = np.meshgrid(np.arange(nr - 1), np.arange(nz), indexing="ij")
    couple(I, J, I + 1, J, 2 * math.pi * hmean(prop[:-1, :], prop[1:, :]) * (np.arange(1, nr) * hm)[:, None])
    I, J = np.meshgrid(np.arange(nr), np.arange(nz - 1), indexing="ij")
    couple(I, J, I, J + 1, 2 * math.pi * hmean(prop[:, :-1], prop[:, 1:]) * rc[:, None])
    f = free[-1, :]
    np.add.at(diag, idx[-1, :][f], (2 * math.pi * prop[-1, :] * (nr * hm) * 2)[f])
    f = free[:, -1]
    np.add.at(diag, idx[:, -1][f], (2 * math.pi * prop[:, -1] * rc * 2)[f])
    f = free[:, 0]
    np.add.at(diag, idx[:, 0][f], (2 * math.pi * prop[:, 0] * rc * 2)[f])
    A = sp.csr_matrix((np.concatenate(vals + [diag]), (np.concatenate(rows + [np.arange(n)]),
                                                       np.concatenate(cols + [np.arange(n)]))), shape=(n, n))
    return A, rhs, idx


def drift(args):
    name, rec, h = args
    ret, glass, gel = CASES[name]
    t0 = time.time()
    r, z, eps, sig, cond = maps(rec, ret, glass, gel, h)
    C, bC, idx = assemble(EPS0 * eps, cond, r, h, 0.5)               # rings at +-1/2: 1 V across
    G, bG, _ = assemble(sig, cond, r, h, 0.5)
    i0 = idx[0, 0]

    def e_null(v):
        return float(v[i0] / (0.5 * h * 1e-3))                         # V/m per volt across the rings

    V = spla.spsolve(C.tocsc(), bC)                                    # at switch-on: the electrostatic solution
    ts, E = [0.0], [e_null(V)]
    edges = [0.0] + [10.0 ** k for k in range(0, int(math.ceil(math.log10(T_END))))] + [T_END]
    for t_a, t_b in zip(edges[:-1], edges[1:]):                        # constant steps within each decade
        dt = (t_b - t_a) / PER_DECADE
        lu = spla.splu((C / dt + G).tocsc())
        for k in range(PER_DECADE):
            V = lu.solve(C @ V / dt + bG)
            ts.append(t_a + (k + 1) * dt)
            E.append(e_null(V))
    k_kv = np.array(E) * 1e-5 * 1e3                                    # (kV/cm) per kV across
    return dict(name=name, retainer=ret, glass=glass, gel=gel, h_mm=h, t_s=ts, k_kV_cm_per_kV=k_kv.tolist(),
                E_kV_cm=(k_kv * rec["V_gap_kV"]).tolist(), run_s=time.time() - t0)


def swing(rec, n_cyc=200, steps=5000):
    """the record's supply (its stages, 100 pF) re-run for its waveforms: the last two cycles of ring A and B, and the
    field at the null they give (as connected); and the start-up, cycle by cycle."""
    kw = dict(opt="dc", n_cw=rec["n_cw"], n_cw_a=rec["n_a"], n_cyc=n_cyc, steps=steps, c_core=0.1e-9, c_cw=0.1e-9,
              r_leak=B.R_LEAK_EST)
    txt, vecs, _ = CF.deck(**kw)
    with tempfile.TemporaryDirectory() as d:
        open(os.path.join(d, "x.cir"), "w").write(txt)
        subprocess.run(["ngspice", "-b", "x.cir"], capture_output=True, text=True, cwd=d, timeout=7200)
        raw = np.loadtxt(os.path.join(d, "out.dat"))
    t = raw[:, 0]
    c = {v: raw[:, 2 * j + 1] for j, v in enumerate(vecs)}
    T = 1.0 / CF.F
    tu = (n_cyc - 2) * T + np.arange(2000) * 2 * T / 2000
    va, vb = np.interp(tu, t, c["v(ea)"]), np.interp(tu, t, c["v(eb)"])
    per_cyc = [float(-(c["v(eb)"][(t >= k * T) & (t < (k + 1) * T)] - c["v(ea)"][(t >= k * T) & (t < (k + 1) * T)]).max())
               for k in range(n_cyc)]
    k = rec["k_kV_cm_per_kV"]
    e = k * (vb - va) / 1e3
    return dict(t_ms=((tu - tu[0]) * 1e3).tolist(), V_A_kV=(va / 1e3).tolist(), V_B_kV=(vb / 1e3).tolist(),
                E_kV_cm=e.tolist(), E_mean_kV_cm=float(e.mean()), E_pp_kV_cm=float(np.ptp(e)),
                startup_E_kV_cm=[-k * x / 1e3 for x in per_cyc], startup_t_s=[(i + 0.5) * T for i in range(n_cyc)])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--procs", type=int, default=4)
    ap.add_argument("--h", type=float, default=0.25)
    a = ap.parse_args()
    t0 = time.time()
    rec = json.load(open(os.path.join(HERE, "hub_rings_build_results.json")))["record"]   # the rings as built
    with Pool(a.procs) as pool:
        runs = list(pool.imap(drift, [(nm, rec, a.h) for nm in CASES]))
    for q in runs:
        e = q["E_kV_cm"]
        print(f"{q['name']:40s}: {e[0]:.2f} at switch-on -> {e[np.searchsorted(q['t_s'], 600)]:.2f} at 10 min -> "
              f"{e[np.searchsorted(q['t_s'], 3600)]:.2f} at 1 h -> {e[-1]:.2f} kV/cm at {q['t_s'][-1] / 3600:.0f} h "
              f"({q['run_s']:.0f} s)", flush=True)
    print(f"the record's k {rec['k_kV_cm_per_kV']:.4f}; the drift model at switch-on "
          f"{runs[0]['k_kV_cm_per_kV'][0]:.4f} (kV/cm)/kV", flush=True)
    sw = swing(rec)
    print(f"the 120 Hz swing at the null: {sw['E_mean_kV_cm']:.2f} kV/cm mean, {sw['E_pp_kV_cm']:.3f} kV/cm p-p", flush=True)
    cusp = json.load(open(os.path.join(HERE, "ah_steady_cusp_results.json")))
    ah = [q for q in cusp["rows"] if q["C_byp_mF"] == 22.0][0]
    out = dict(note="see the module docstring", sigma_S_m=SIG, cases={k: list(v) for k, v in CASES.items()}, record=rec,
               leakage_total_ohm=B.leak_total(), R_leak_est=B.R_LEAK_EST,
               drift=runs, swing=sw, ah_ripple=dict(AT_min=ah["top"]["AT_min"], AT_max=ah["top"]["AT_max"],
                                                   AT_mean=ah["top"]["AT_mean"]), run_s=time.time() - t0)
    json.dump(out, open(os.path.join(HERE, "hub_drift_results.json"), "w"), indent=1, default=float)
    print(f"done in {time.time() - t0:.0f} s")


if __name__ == "__main__":
    main()
