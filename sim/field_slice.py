#!/usr/bin/env python3
"""sim/field_slice.py -- meridional cuts of the 3-D electrostatic field (field_solve), as pictures.

One solve at one relative angle keeps the potential of every unit excitation (net k at 1 V, the others at 0).
Any voltage set is then a superposition, V = sum_k v_k V_k. Floating nets (e.g. the utron) take the potential
that leaves them uncharged: C_ff v_f = -C_fd v_d, from the solve's own Maxwell matrix.

Picture, at a fixed angle phi (a meridional r-z plane):
  * colour: |E| in the plane (kV/mm, log scale);
  * thin lines: equipotentials;
  * white lines: E field lines (streamlines of the in-plane E);
  * grey: conductors (labelled by net); hatched: dielectrics.
The azimuthal E component is not drawn (|E| in the plane only).                                      [IR]

Usage:
  python3 sim/field_slice.py solve <design tag> <theta_geom> <phi1,phi2,...> [level]  -> docs/geometry/rt/slices/<tag>@<theta>.npz
  python3 sim/field_slice.py plot <npz> <phi> <spec> [r0,r1,z0,z1] [out.png]
    spec: 'unit:<net>'  or  'net=volts,net=volts,...[;float=net,net]'
"""
import json
import math
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path[:0] = [HERE]
RT_DIR = os.path.join(ROOT, "docs", "geometry", "rt")
SLICE_DIR = os.path.join(RT_DIR, "slices")


def solve(tag, theta, phis, level="c"):
    import field_solve as FS
    import round_trip as RTR
    design = json.load(open(os.path.join(RT_DIR, f"{tag}.design.json")))
    prims = FS.dedupe(FS.primitives(design["parts"]))
    rot = RTR.rotor_names(design)
    th = theta % FS.PERIOD
    rotor_edges = sorted({(q["a0"] + th) % FS.PERIOD for q in prims if q["kind"] == "sector" and q["name"] in rot
                          and q["cond"] is not None and q["w"] < 360 - 1e-9} |
                         {(q["a0"] + q["w"] + th) % FS.PERIOD for q in prims if q["kind"] == "sector" and q["name"] in rot
                          and q["cond"] is not None and q["w"] < 360 - 1e-9})
    stator = [q for q in prims if q["name"] not in rot]
    moved = [dict(q, a0=(q["a0"] + th) % 360.0) if q["kind"] == "sector" and q["w"] < 360 - 1e-9 else q
             for q in prims if q["name"] in rot]
    g, bc = FS.build_grid(stator + moved, enclosure=None, res=RTR.RES[level], theta_breaks=rotor_edges)
    eps, cond, names = FS.rasterize(g, prims, rotor=rot, theta=th)
    C, info = FS.maxwell(g, eps, cond, names, bc, r_cut=25.0, tol=1e-5, return_V=True)
    V = info["V"]
    os.makedirs(SLICE_DIR, exist_ok=True)
    out = dict(rc=g.rc, zc=g.zc, pc=g.pc, names=np.array(names), C=C * 6.0, theta=theta)
    for ph in phis:
        ip = int(np.argmin(np.abs(((g.pc - ph % FS.PERIOD) + 30) % 60 - 30)))
        out[f"V@{ph:g}"] = V[:, ip, :, :]
        out[f"cond@{ph:g}"] = cond[:, ip, :]
        out[f"eps@{ph:g}"] = eps[:, ip, :].astype(np.float32)
        out[f"phi_used@{ph:g}"] = g.pc[ip]
    path = os.path.join(SLICE_DIR, f"{tag}@{theta:g}.npz")
    np.savez_compressed(path, **out)
    return path


def potentials(d, spec):
    """spec -> {net: volts} for every net (floating nets solved from the Maxwell matrix)."""
    names = [str(n) for n in d["names"]]
    if spec.startswith("unit:"):
        k = spec[5:]
        return {n: (1.0 if n == k else 0.0) for n in names}, f"unit excitation: net {k} at 1 V, all others at 0 V"
    fixed_s, _, float_s = spec.partition(";float=")
    fixed = {}
    for kv in filter(None, fixed_s.split(",")):
        n, v = kv.split("="); fixed[n] = float(v)
    flo = [n for n in filter(None, float_s.split(","))]
    v = {n: fixed.get(n, 0.0) for n in names}
    if flo:
        C = np.asarray(d["C"], float)
        fi = [names.index(n) for n in flo]; di = [i for i in range(len(names)) if i not in fi]
        vd = np.array([v[names[i]] for i in di])
        vf = np.linalg.solve(C[np.ix_(fi, fi)], -C[np.ix_(fi, di)] @ vd)
        for i, x in zip(fi, vf):
            v[names[i]] = float(x)
    lab = ", ".join(f"{n} {v[n] / 1e3:+.2f} kV" for n in names if abs(v[n]) > 0 or n in flo)
    return v, "operating set: " + lab + (f" (floating: {', '.join(flo)})" if flo else "")


def plot(npz, phi, spec, window=None, out=None, title=None):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.colors import LogNorm
    from scipy.interpolate import RegularGridInterpolator
    d = dict(np.load(npz, allow_pickle=False))
    names = [str(n) for n in d["names"]]
    rc, zc = d["rc"], d["zc"]
    Vk = d[f"V@{phi:g}"]; cond = d[f"cond@{phi:g}"]; eps = d[f"eps@{phi:g}"]
    v, lab = potentials(d, spec)
    V = np.tensordot(Vk.astype(float), np.array([v[n] for n in names]), axes=([2], [0]))     # (Nr, Nz) volts
    r0, r1, z0, z1 = window or (rc.min(), rc.max(), zc.min(), zc.max())
    # uniform grid for the picture
    h = max((r1 - r0), (z1 - z0)) / 700.0
    R = np.arange(r0, r1, h); Z = np.arange(z0, z1, h)
    RR, ZZ = np.meshgrid(R, Z, indexing="ij")
    P = np.c_[RR.ravel(), ZZ.ravel()]
    iV = RegularGridInterpolator((rc, zc), V, bounds_error=False, fill_value=None)
    Vu = iV(P).reshape(RR.shape)
    ic = RegularGridInterpolator((rc, zc), cond.astype(float), method="nearest", bounds_error=False, fill_value=-1)
    Cu = ic(P).reshape(RR.shape).astype(int)
    ie = RegularGridInterpolator((rc, zc), eps.astype(float), method="nearest", bounds_error=False, fill_value=1.0)
    Eu = ie(P).reshape(RR.shape)
    Er, Ez = np.gradient(-Vu, R, Z)                                            # V/mm
    Emag = np.hypot(Er, Ez) / 1e3                                               # kV/mm (for volts in)
    inside = Cu >= 0
    Emag = np.where(inside, np.nan, Emag)
    unit = spec.startswith("unit:")
    fig, ax = plt.subplots(figsize=(13, 13 * (z1 - z0) / (r1 - r0) * 0.9 + 1.5))
    Eplot = Emag * (1e3 if unit else 1.0)                                       # unit case: V/mm per volt
    lo = np.nanpercentile(Eplot, 2); hi = np.nanmax(Eplot)
    im = ax.pcolormesh(R, Z, Eplot.T, norm=LogNorm(vmin=max(lo, hi * 1e-4), vmax=hi), cmap="inferno", shading="auto")
    cb = fig.colorbar(im, ax=ax, shrink=0.8)
    cb.set_label("|E| in the plane, V/mm per V of excitation" if unit else "|E| in the plane, kV/mm")
    lev = np.linspace(np.nanmin(Vu), np.nanmax(Vu), 25)
    ax.contour(R, Z, np.where(inside, np.nan, Vu).T, levels=lev, colors="#7fb3ff", linewidths=0.5)
    Ers, Ezs = np.where(inside, 0, Er), np.where(inside, 0, Ez)
    ax.streamplot(R, Z, Ers.T, Ezs.T, density=1.6, color="w", linewidth=0.5, arrowsize=0.6)
    diel = (Eu > 1.01) & ~inside
    ax.contourf(R, Z, diel.T.astype(float), levels=[0.5, 1.5], colors="none", hatches=["////"])
    ax.contour(R, Z, diel.T.astype(float), levels=[0.5], colors="#bbbbbb", linewidths=0.4)
    cols = plt.cm.tab20(np.linspace(0, 1, max(len(names), 2)))
    for k, n in enumerate(names):
        m = Cu == k
        if m.any():
            ax.contourf(R, Z, m.T.astype(float), levels=[0.5, 1.5], colors=[cols[k % 20]], alpha=0.95)
            ii = np.argwhere(m); c = ii[len(ii) // 2]
            ax.text(R[c[0]], Z[c[1]], n, fontsize=7, ha="center", va="center", color="k",
                    bbox=dict(boxstyle="round,pad=0.1", fc="w", ec="none", alpha=0.7))
    if not unit:
        ax.contour(R, Z, np.nan_to_num(Emag).T, levels=[3.0], colors="cyan", linewidths=1.2)
    ax.set_aspect("equal"); ax.set_xlim(r0, r1); ax.set_ylim(z0, z1)
    ax.set_xlabel("r [mm]"); ax.set_ylabel("z [mm]")
    ph_used = float(d[f"phi_used@{phi:g}"])
    ax.set_title(title or f"{os.path.basename(npz)}  meridional cut at phi = {ph_used:.2f} deg (rotor at {float(d['theta']):g} deg)\n{lab}"
                 + ("" if unit else "   (cyan: 3 kV/mm)"), fontsize=9)
    out = out or os.path.splitext(npz)[0] + f"-phi{phi:g}-{spec.replace(':', '_').replace(',', '_').replace(';', '_').replace('=', '')[:60]}.png"
    fig.tight_layout(); fig.savefig(out, dpi=90); plt.close(fig)
    return out


if __name__ == "__main__":
    if sys.argv[1] == "solve":
        phis = [float(x) for x in sys.argv[4].split(",")]
        print(solve(sys.argv[2], float(sys.argv[3]), phis, sys.argv[5] if len(sys.argv) > 5 else "c"))
    elif sys.argv[1] == "plot":
        win = [float(x) for x in sys.argv[5].split(",")] if len(sys.argv) > 5 else None
        print(plot(sys.argv[2], float(sys.argv[3]), sys.argv[4], win, sys.argv[6] if len(sys.argv) > 6 else None))
