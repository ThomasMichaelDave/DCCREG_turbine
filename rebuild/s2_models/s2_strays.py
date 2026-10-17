"""rebuild/s2_models/s2_strays.py -- S2b: the field solve on the S2a model (rebuild/s2_models/s2b-plan.md).

The record's finite-volume solver, imported from sim/tube_strays.py (not edited): node-based finite volumes on a
cylindrical tensor grid, Shortley-Weller boundaries, CG with smoothed-aggregation AMG (pyamg), the Maxwell matrix from
the conductors' charges [OC: the method]. The S2a model's parts come from rebuild/s2_models/s2_fv.py (S2b-1).

Steps (each its own flag; every solve kept in s2_strays_results.json by its key, --resume reuses them):
  --cell   S2b-2: one gap of the infinite periodic stack, a 30 deg mirror wedge, at the spacings 1.0 / 0.5 / 0.25 mm,
           without rims (the vanes' sectors only, Neumann at r 50 / 150) and with them (the record's radial build):
           - G-CELL: the record's 3 mm cell (sim/tube_strays_results.json "cell") reproduced within 0.2 %;
           - the gaps of S2a's stack: 3 | 3, and the end vanes' 4 | 3 (the first rotor vane) and 3 | 4.5 (the last
             stator vane) [IR: a periodic cell of those two thicknesses].
  (the stack W, the hub H, the axisymmetric A, the whole F, the profile and the fields follow, s2b-plan.md §4)
Writes rebuild/s2_models/s2_strays_results.json.
Tags: [OC] derivable; [IR] a modelling choice; [RH] a heuristic (CONVENTIONS.md §1). g is a gap, never d.
Usage: python3 rebuild/s2_models/s2_strays.py --cell [--procs 6] [--resume]
"""
import os
os.environ.setdefault("OPENBLAS_NUM_THREADS", "1")
os.environ.setdefault("OMP_NUM_THREADS", "1")
import argparse        # noqa: E402
import json            # noqa: E402
import math            # noqa: E402
import sys             # noqa: E402
import time            # noqa: E402
from multiprocessing import Pool    # noqa: E402

import numpy as np     # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, os.path.join(ROOT, "sim"))
sys.path.insert(0, HERE)
import tube_strays as TS   # noqa: E402
import stack_sizing as SS  # noqa: E402
import s2_fv as F          # noqa: E402

RESULTS = os.path.join(HERE, "s2_strays_results.json")
CELL_H = TS.CELL_H                     # 1.0, 0.5, 0.25 mm: the record's cell spacings
CELL_CASES = [(3.0, 3.0), (4.0, 3.0), (3.0, 4.5)]     # (rotor vane, stator vane) mm: S2a's gaps (s2_geometry.py)


# ============================================================================================== S2b-2: the cell
def build_cell(h=0.5, unaligned=False, rims=True, t_rot=3.0, t_sta=3.0, log=print):
    """sim/tube_strays.build_cell with the two vanes' thicknesses their own: mirrors at the stator vane's and the next
    rotor vane's mid-planes (z 0 and t_sta / 2 + g + t_rot / 2), the 30 deg mirror wedge; each vane's exposed edges a
    full round of half its own thickness [IR, the record's]. rims: the record's radial build (shaft, G10 sleeve, the
    rotor ring on the sleeve, the stator ring, the G10 cage, the REF wall at r 400); else Neumann at r 50 / 150."""
    I = TS.inputs()
    rec = I["rec"]
    g, half = rec["gap_mm"], 0.5 * rec["wr_deg"]
    zs, zr = 0.0, 0.5 * t_sta + g + 0.5 * t_rot
    z = TS.axis(zs, zr, [0.5 * t_sta, zr - 0.5 * t_rot], [(zs, zr, h)])
    ctr = 30.0 if unaligned else 0.0
    edges = [half] + ([ctr - half] if unaligned else [])
    th = TS.axis(0, 30.0, [0, 30] + edges, [(e - 2.5, e + 2.5, 0.4 * h) for e in edges] + [(0, 30, 1.2 * h)],
                 h_far=1.2 * h, grow=1.2)
    ri, ro = SS.TUBE_DEFAULTS["r_inMm"], SS.TUBE_DEFAULTS["r_outMm"]
    if rims:
        rf = [3.0, SS.SHAFT_R, SS.SLEEVE_R, ro + 12, ro + 16, TS.R_BOX] + [x + s * 0.5 * t for x in (ri, ro)
                                                                          for t in (t_rot, t_sta) for s in (-1, 0, 1)]
        r = TS.axis(3.0, TS.R_BOX, rf, [(ri - 5, ri + 5, h), (ro - 5, ro + 5, h), (12.5, 45, 2 * h), (155, 170, 2 * h),
                                        (55, 145, 4 * h), (3, 12.5, 3.0)], h_far=30.0, grow=1.18)
    else:
        r = TS.axis(ri, ro, [], [(ri, ro, 5.0)])
    P = TS.Problem(r, np.radians(th), z, eps_bg=I["eps_air"])
    T0, T1 = -1.0, 2.0
    if rims:
        st = TS.Vane("stator", zs - 0.5 * t_sta, zs + 0.5 * t_sta, ctr, half, ri, ro, ro, ro + 12.0)
        rt = TS.Vane("rotor", zr - 0.5 * t_rot, zr + 0.5 * t_rot, 0.0, half, ri, ro, SS.SLEEVE_R, ro + 12.0)
        g10 = I["hub"]["shaft_coupler"]["value"]["eps_r"]
        P.add_dielectric(g10, TS.ann_c(SS.SHAFT_R, SS.SLEEVE_R, -1, zr + 1), (SS.SHAFT_R, SS.SLEEVE_R, T0, T1, -1, zr + 1))
        P.add_dielectric(g10, TS.ann_c(ro + 12, ro + 16, -1, zr + 1), (ro + 12, ro + 16, T0, T1, -1, zr + 1))
        P.add_conductor(TS.SID["SHAFT"], "SHAFT", lambda R, T, Z: R <= SS.SHAFT_R + TS.TOL, (0, SS.SHAFT_R, T0, T1, -1, zr + 1))
        P.cid[-1, :, :] = TS.SID["W"]; P.names[TS.SID["W"]] = "W"
    else:
        st = TS.Vane("stator", zs - 0.5 * t_sta, zs + 0.5 * t_sta, ctr, half, 0.0, 1000.0)
        rt = TS.Vane("rotor", zr - 0.5 * t_rot, zr + 0.5 * t_rot, 0.0, half, 0.0, 1000.0, 0.0)
    P.add_conductor(TS.SID["N1v"], "N1v", rt.inside, (0, 1e4, T0, T1, zr - t_rot, zr + t_rot))
    P.add_conductor(TS.SID["SA"], "SA", st.inside, (0, 1e4, T0, T1, zs - t_sta, zs + t_sta))
    return P


def _cell_job(job):
    t0 = time.time()
    kw = job["kw"]
    P = build_cell(log=lambda s: None, **kw)
    P.assemble(log=lambda s: None)
    C, its = P.maxwell([TS.SID["N1v"]], log=lambda s: None)
    n1, sa = TS.SID["N1v"], TS.SID["SA"]
    out = dict(key=job["key"], kw=kw, per_gap_pF=-12.0 * C[sa, n1], nodes=int(P.cid.size), run_s=time.time() - t0)
    if kw["rims"]:
        out["rotor_vane_shaft_pF"] = -12.0 * C[TS.SID["SHAFT"], n1]
        out["rotor_vane_wall_pF"] = -12.0 * C[TS.SID["W"], n1]
    print(f"[{job['key']}] {out['per_gap_pF']:.4f} pF per gap ({out['run_s']:.0f} s)", flush=True)
    return out


def cell_jobs():
    out = []
    for (tr, ts) in CELL_CASES:
        for rims in (False, True):
            for h in CELL_H:
                for un in (False, True):
                    kw = dict(h=h, unaligned=un, rims=rims, t_rot=tr, t_sta=ts)
                    out.append(dict(key="cell:" + ",".join(f"{k}={v}" for k, v in sorted(kw.items())), kw=kw))
    return out


def cell_analyse(rows):
    """per case and spacing: the aligned / unaligned per-gap C, kappa per gap; Richardson over the three spacings;
    G-CELL at 3 | 3 against the record's cell."""
    rec = json.load(open(os.path.join(ROOT, "sim", "tube_strays_results.json")))["cell"]
    by = {r["key"]: r for r in rows}
    out, gate = {}, []
    for (tr, ts) in CELL_CASES:
        case = {}
        for rims in (False, True):
            lv = []
            for h in CELL_H:
                g = lambda un: by["cell:" + ",".join(f"{k}={v}" for k, v in sorted(dict(h=h, unaligned=un, rims=rims,  # noqa
                                                                                          t_rot=tr, t_sta=ts).items()))]
                a, u = g(False), g(True)
                lv.append(dict(h_mm=h, aligned=a["per_gap_pF"], unaligned=u["per_gap_pF"],
                               kappa_gap=a["per_gap_pF"] / u["per_gap_pF"]))
            ex = {k: TS.richardson([q[k] for q in lv], list(CELL_H))[0] for k in ("aligned", "unaligned")}
            case["with_rims" if rims else "no_rims"] = dict(levels=lv, extrapolated=ex,
                                                             kappa_gap=ex["aligned"] / ex["unaligned"])
            if (tr, ts) == (3.0, 3.0):
                ref = rec["with_rims" if rims else "no_rims"]
                for q, rq in zip(lv, ref):
                    for k in ("aligned", "unaligned"):
                        dev = q[k] / rq[k] - 1
                        gate.append(dict(rims=rims, h_mm=q["h_mm"], which=k, here=q[k], record=rq[k], dev=dev))
        out[f"{tr:g}|{ts:g}"] = case
    worst = max(abs(x["dev"]) for x in gate)
    return out, dict(rows=gate, worst_dev=worst, tol=0.002, pass_=worst <= 0.002)


# ============================================================================================== the models' core
class PProblem(TS.Problem):
    """sim/tube_strays.Problem with an optional periodic theta: the grid's last theta node is its first turned by the
    period, and the two are merged into one unknown after assembly (A' = P^T A P, B' = B P), so their two half-cells
    become one cell across the seam [OC: the finite-volume sum is the same]. Without period, the record's mirrors."""

    def __init__(self, r, th, z, eps_bg=1.0, periodic=False):
        super().__init__(r, th, z, eps_bg)
        self.periodic = periodic

    def assemble(self, log=print):
        if self.periodic:
            self.cid[:, -1, :] = self.cid[:, 0, :]
        super().assemble(log=log)
        if not self.periodic:
            return
        import scipy.sparse as sp
        free = self.cid < 0
        fidx = np.full(self.shape, -1, dtype=np.int64)
        fidx[free] = np.arange(self.nf)
        seam_hi, seam_lo = fidx[:, -1, :][free[:, -1, :]], fidx[:, 0, :][free[:, 0, :]]
        keep = np.ones(self.nf, dtype=bool)
        keep[seam_hi] = False
        red = np.full(self.nf, -1, dtype=np.int64)
        red[keep] = np.arange(int(keep.sum()))
        red[seam_hi] = red[seam_lo]
        Pm = sp.csr_matrix((np.ones(self.nf), (np.arange(self.nf), red)), shape=(self.nf, int(keep.sum())))
        self.A = (Pm.T @ self.A @ Pm).tocsr()
        self.B = (self.B @ Pm).tocsr()
        self.nf = int(keep.sum())
        log(f"    periodic theta: {len(seam_hi)} seam nodes merged, {self.nf / 1e6:.2f} M unknowns")


def _cyl(sh):
    return lambda R, T, Z: sh.inside(R * np.cos(T), R * np.sin(T), Z)


def _cbox(sh, T0, T1):
    """a Cartesian box as (r0, r1, theta0, theta1, z0, z1): r from the box's nearest and farthest xy points."""
    lo, hi = sh.lo, sh.hi
    nx = min(max(0.0, lo[0]), hi[0]) if not (lo[0] <= 0 <= hi[0]) else 0.0
    ny = min(max(0.0, lo[1]), hi[1]) if not (lo[1] <= 0 <= hi[1]) else 0.0
    r0 = math.hypot(nx, ny)
    r1 = max(math.hypot(x, y) for x in (lo[0], hi[0]) for y in (lo[1], hi[1]))
    return (r0, r1, T0, T1, lo[2], hi[2])


def _overlaps_wedge(sh, t0_deg, t1_deg, n=24):
    """does the part's xy box reach into the wedge (with a margin)? sampled on the box's outline and centre [IR]."""
    lo, hi = sh.lo, sh.hi
    if lo[0] <= 0 <= hi[0] and lo[1] <= 0 <= hi[1]:
        return True
    xs, ys = np.linspace(lo[0], hi[0], n), np.linspace(lo[1], hi[1], n)
    X, Y = np.meshgrid(xs, ys)
    a = np.mod(np.degrees(np.arctan2(Y, X)) - (t0_deg - 5.0), 360.0)
    return bool((a <= (t1_deg - t0_deg) + 10.0).any())


def graded_slices(row, n):
    """a graded part cut into n slices along its axis or arc: (slice Sh, its position s at the slice's middle)."""
    sh = row["sh"]
    out = []
    if row.get("axis"):
        p0, p1 = (np.asarray(q, float) for q in row["axis"])
        u = (p1 - p0) / np.linalg.norm(p1 - p0)
        L = float(np.linalg.norm(p1 - p0))
        sfun = lambda X, Y, Z: ((X - p0[0]) * u[0] + (Y - p0[1]) * u[1] + (Z - p0[2]) * u[2]) / L      # noqa: E731
    else:
        a0, a1 = row["arc"]["th"][0], row["arc"]["th"][1]
        w = (a1 - a0 + 180.0) % 360.0 - 180.0
        sfun = lambda X, Y, Z: ((np.degrees(np.arctan2(Y, X)) - a0 + 180.0) % 360.0 - 180.0) / w     # noqa: E731
    for k in range(n):
        lo_, hi_ = k / n, (k + 1) / n
        f = (lambda X, Y, Z, lo_=lo_, hi_=hi_, first=(k == 0), last=(k == n - 1):
             sh.inside(X, Y, Z) & ((sfun(X, Y, Z) >= lo_) | first) & ((sfun(X, Y, Z) < hi_) | last))
        out.append((F.Sh(f, sh.lo, sh.hi, "slice"), 0.5 * (lo_ + hi_)))
    return out


def category(row):
    """a conductor's itemised name: net : what [IR: the grouping for the findings]."""
    n, nm = row.get("net"), row["name"]
    side = nm[0] if nm[:2] in ("A_", "B_") else ""
    for key, what in (("_Ca_", "Ca"), ("_Cb_", "Ca"), ("_C1_r", "vanes"), ("_C2_r", "vanes"), ("_C1_s", "stator"),
                      ("_C2_s", "stator"), ("_comb", "comb"), ("_tie", "tie"), ("spider", "spider"), ("ref_bearing", "bearing"),
                      ("_riser", "riser"), ("_tap", "tap"), ("hub_ring", "ring"), ("hub_bead", "ring"), ("shaft", "shaft"),
                      ("flange", "shaft"), ("ref_term", "shaft"), ("_J_", "deck"), ("_lead", "deck"), ("_joint", "deck"),
                      ("ring_m", "midring"), ("strap", "deck"), ("cross", "cross"), ("frame", "frame"), ("_fb_", "frame"),
                      ("stub", "frame"), ("_post", "frame")):
        if key in nm:
            return f"{n}:{side}{what}"
    return f"{n}:{side}other"


def add_parts(P, rows, T0, T1, pick, rotate_rotor=0.0, wedge=None, min_r=None, log=print):
    """the chosen parts into P: dielectrics first (in the model's order), then conductors by their itemised names;
    graded parts as slices; the HV wires' cores at no less than min_r [IR: the grid's resolution]; the rotor's parts
    turned by rotate_rotor deg. Returns the conductor names in id order."""
    names = []
    cid = {}

    def turned(row):
        sh = row["sh"]
        return F.placed(sh, dict(dx=0.0, dz=0.0, rot=rotate_rotor)) if (rotate_rotor and row.get("body") == "rotor") else sh
    use = [r for r in rows if pick(r) and (wedge is None or _overlaps_wedge(turned(r), *wedge))]
    for r in use:
        if r["kind"] == "diel":
            sh = turned(r)
            P.add_dielectric(r["eps"], _cyl(sh), _cbox(sh, T0, T1))
    for r in use:
        if r["kind"] == "cond":
            sh = turned(r)
            if r.get("path") is not None and min_r and r["core_r"] < min_r:
                sh = F.wire(r["path"], min_r)
                sh = F.placed(sh, dict(dx=0.0, dz=0.0, rot=rotate_rotor)) if (rotate_rotor and r.get("body") == "rotor") else sh
            nm = category(r)
            if nm not in cid:
                cid[nm] = len(names); names.append(nm)
            P.add_conductor(cid[nm], nm, _cyl(sh), _cbox(sh, T0, T1))
        elif r["kind"] == "graded":
            for k, (sl, s) in enumerate(graded_slices(dict(r, sh=turned(r)), F.GRADED_SLICES)):
                nm = f"g:{r['name']}:{k}:{r['nets'][0]}>{r['nets'][1]}@{s:.3f}"
                cid[nm] = len(names); names.append(nm)
                P.add_conductor(cid[nm], nm, _cyl(sl), _cbox(sl, T0, T1))
    return names, use


def hub_rings_thick(rows, m):
    """the rings' 0.1 mm foils thickened through the gel's 0.5 mm, as the record does for its grid [IR]."""
    H = F._H
    Ro = 0.5 * H["vessel"]["value"]["od_mm"]
    Rg = Ro + H["interface_filler"]["value"]["t_mm"]
    zc = m.zc
    out = []
    for r in rows:
        if r["name"].startswith("hub_ring_"):
            lo, hi = r["sh"].lo, r["sh"].hi
            f = (lambda X, Y, Z, z0=lo[2], z1=hi[2]: (X * X + Y * Y + (Z - zc) ** 2 >= Ro * Ro)
                 & (X * X + Y * Y + (Z - zc) ** 2 <= Rg * Rg) & (Z >= z0) & (Z <= z1))
            r = dict(r, sh=F.Sh(f, (-Rg, -Rg, lo[2]), (Rg, Rg, hi[2]), "ring thick"))
        out.append(r)
    return out


_MODEL = {}


def model():
    if not _MODEL:
        m = F.shadow_core()
        _MODEL.update(m=m, rows=hub_rings_thick(F.roles(m), m))
    return _MODEL["m"], _MODEL["rows"]


# W: the stack, side A, a 60 deg mirror wedge (s2b-plan.md §3)
W_LEVELS = TS.LEVELS


def build_W(level=1, unaligned=False, log=print):
    """side A from the deck's outer face (h 78, a mirror [IR]) to past the frame bearing: the column, its combs, the
    vanes, the stator's lugs, ties and spider, the REF bearing and shaft, the coupling, the earthed stub and frame
    bearing (the frame's beams and posts are left to F); the room a REF-less wall at r 400 and below the stub (FAR).
    Aligned: the wedge 30-90 deg; half a pitch on: the rotor turned 30 deg, the wedge 0-60 deg [OC: s2b-plan.md §3]."""
    import s2_geometry as G
    m, rows = model()
    Lv = W_LEVELS[level]
    zc = m.zc
    z_top = zc - 78.0
    z_lo = -20.0
    t0, t1 = (0.0, 60.0) if unaligned else (30.0, 90.0)
    rot = 30.0 if unaligned else 0.0
    half = 0.5 * G.VANE["wr"]
    # rotor sectors centred at k * 60 + rot, stator at k * 60: their edges in the wedge
    edges = sorted({c + s * half for c in np.arange(-60, 181, 60.0) for s in (-1, 1)} |
                   {c + rot + s * half for c in np.arange(-60, 181, 60.0) for s in (-1, 1)})
    edges = [e for e in edges if t0 - 1e-9 <= e <= t1 + 1e-9]
    tf = [t0, t1] + edges
    th = TS.axis(t0, t1, tf, [(e - 2.0, e + 2.0, Lv["htf"]) for e in edges] + [(t0, t1, Lv["ht"])], h_far=Lv["ht"], grow=1.2)
    # z: every plate face on a node
    zf = [z_lo, z_top]
    for h0, tk in list(m.ca_h) + list(m.vane_h):
        zf += [zc - h0, zc - h0 - tk]
    for r in rows:
        if r["kind"] in ("cond", "diel") and r["sh"].hi[2] <= z_top + 1 and r["sh"].lo[2] >= z_lo - 1 and r["name"][:2] != "B_":
            if r["group"] not in ("deck-A", "wiring"):
                zf += [float(r["sh"].lo[2]), float(r["sh"].hi[2])]
    zs0, zs1 = zc - (m.vane_h[-1][0] + m.vane_h[-1][1]) - 5.0, z_top
    z = TS.axis(z_lo, z_top, zf, [(zs0, zs1, Lv["hz"]), (zs0 - 30, zs0, 1.5 * Lv["hz"])], h_far=6.0, grow=1.15)
    ri, ro = G.VANE["r_in"], G.VANE["r_out"]
    rf = [3.0, G.SHAFT_R, G.SLEEVE_R, G.SLEEVE_OUT, G.FL_R, 25.0, 35.0, 24.0, 36.0, 17.0, 18.0, 26.0,
          ri, ro, G.STATOR_RING[1], G.LUG["r1"], G.CAGE[0], G.CAGE[1], G.TIE["r"] - 5, G.TIE["r"] + 5, TS.R_BOX]
    for tk in {t for _, t in list(m.ca_h) + list(m.vane_h)}:
        rf += [ri + 0.5 * tk, ro - 0.5 * tk]
    r = TS.axis(3.0, TS.R_BOX, rf, [(ri - 5, ri + 5, Lv["hrf"]), (ro - 5, ro + 5, Lv["hrf"]), (12.5, ri - 5, Lv["hr"]),
                                    (ro + 5, 200, Lv["hr"]), (ri + 5, ro - 5, 2 * Lv["hr"]), (3, 12.5, 3.0)], h_far=30.0, grow=1.18)
    P = PProblem(r, np.radians(th), z, eps_bg=TS.inputs()["eps_air"])
    T0, T1 = math.radians(t0) - 0.1, math.radians(t1) + 0.1
    excl = ("frame_post", "frame_beam", "frame_cross", "fb_plate")

    def pick(rw):
        if rw["name"].startswith("B_") or rw["group"] in ("deck-A", "deck-B", "wiring", "hub") or rw["name"].startswith("xbracket"):
            return False
        if any(e in rw["name"] for e in excl) or rw["name"] == "cage" and False:
            return False
        return rw["sh"].lo[2] < z_top - 1e-6 and rw["sh"].hi[2] > z_lo
    names, use = add_parts(P, rows, T0, T1, pick, rotate_rotor=rot, wedge=(t0, t1), log=log)
    # the cage spans both sides: clipped by the domain; the room: a wall at r 400 and a plane below the stub
    far = len(names); names.append("FAR")
    P.cid[-1, :, :] = np.where(P.cid[-1, :, :] < 0, far, P.cid[-1, :, :])
    P.cid[:, :, 0] = np.where(P.cid[:, :, 0] < 0, far, P.cid[:, :, 0])
    P.names[far] = "FAR"
    log(f"    W level {level}, {'half a pitch on' if unaligned else 'aligned'}: r {len(r)} x theta {len(th)} x z {len(z)} "
        f"= {P.cid.size / 1e6:.2f} M nodes, {len(names)} conductors, {len(use)} parts")
    return P, names


# H: the hub and the decks, full 360 deg (s2b-plan.md §3)
H_LEVELS = {0: dict(hz=2.0, ht=2.0, hr=2.0, hhub=0.5), 1: dict(hz=1.5, ht=1.5, hr=1.5, hhub=0.35)}   # [IR: the cost]
SPLIT = {"H": {0: 1, 1: 3}, "F": {0: 3}}     # a solve's driven conductors shared out over this many processes


def build_H(level=0, unaligned=False, log=print):
    """both sides between Ca_04's mid-planes (mirrors [IR]): the decks, the clamp halves and m1 / m4, bracket B, the
    cross wires, the riser and tap, Ca_06-Ca_04 and their combs, the hub with its rings, the flanges, the sleeve, the
    frame's posts in reach; the room a wall at r 400 (FAR). The full turn, periodic. unaligned: the rotor turned 30 deg."""
    import s2_geometry as G
    m, rows = model()
    Lv = H_LEVELS[level]
    zc = m.zc
    hcut = m.ca_h[2][0] + 0.5 * m.ca_h[2][1]
    z0, z1 = zc - hcut, zc + hcut
    rot = 30.0 if unaligned else 0.0
    nth = int(round(360.0 / Lv["ht"]))
    th = np.linspace(0.0, 360.0, nth + 1)
    zf = [z0, z1, zc]
    for h0, tk in m.ca_h[:3]:
        for sg in (-1, 1):
            zf += [zc + sg * h0, zc + sg * (h0 + tk)]
    z = TS.axis(z0, z1, zf, [(zc - 30, zc + 30, Lv["hhub"] * 2), (zc - 80, zc + 80, Lv["hz"])], h_far=Lv["hz"], grow=1.15)
    H = F._H
    Ro = 0.5 * H["vessel"]["value"]["od_mm"]
    Ri = Ro - H["vessel_wall"]["value"]["t_mm"]
    Rg = Ro + H["interface_filler"]["value"]["t_mm"]
    rf = [1.0, Ri, Ro, Rg, H["retainer"]["value"]["r_max_mm"], G.CPL_R1, G.FL_R, G.SHAFT_R, G.SLEEVE_R, G.SLEEVE_OUT,
          G.VANE["r_in"], G.VANE["r_out"], 195.0, 155.0, TS.R_BOX]
    r = TS.axis(1.0, TS.R_BOX, rf, [(Ri - 3, Rg + 3, Lv["hhub"]), (3, 34, 2 * Lv["hhub"]), (34, 130, Lv["hr"]),
                                    (130, 200, 2 * Lv["hr"])], h_far=25.0, grow=1.15)
    P = PProblem(r, np.radians(th), z, eps_bg=TS.inputs()["eps_air"], periodic=True)
    T0, T1 = -0.1, 2 * math.pi + 0.1

    def pick(rw):
        return rw["sh"].lo[2] < z1 and rw["sh"].hi[2] > z0 and not rw["name"].startswith(("A_C1", "B_C2"))
    names, use = add_parts(P, rows, T0, T1, pick, rotate_rotor=rot, min_r=0.6 * Lv["hr"], log=log)
    far = len(names); names.append("FAR")
    P.cid[-1, :, :] = np.where(P.cid[-1, :, :] < 0, far, P.cid[-1, :, :])
    P.names[far] = "FAR"
    log(f"    H level {level}, {'half a pitch on' if unaligned else 'aligned'}: r {len(r)} x theta {len(th)} x z {len(z)} "
        f"= {P.cid.size / 1e6:.2f} M nodes, {len(names)} conductors, {len(use)} parts")
    return P, names


# F: the whole machine, coarse (s2b-plan.md §3)
F_LEVELS = {0: dict(hz=3.0, ht=3.0, hr=3.0, hhub=0.75)}


def build_F(level=0, unaligned=False, log=print):
    """everything, the square frame as drawn, the room a wall at r 400 and planes 40 mm past the stubs (FAR); the full
    turn, periodic; coarse: the earth pairs and the split's check (G-SPLIT)."""
    import s2_geometry as G
    m, rows = model()
    Lv = F_LEVELS[level]
    zc = m.zc
    z0, z1 = -40.0, 2 * zc + 40.0
    rot = 30.0 if unaligned else 0.0
    nth = int(round(360.0 / Lv["ht"]))
    th = np.linspace(0.0, 360.0, nth + 1)
    zf = [z0, z1, zc]
    z = TS.axis(z0, z1, zf, [(zc - 40, zc + 40, Lv["hhub"] * 2), (zc - 330, zc + 330, Lv["hz"])], h_far=Lv["hz"] * 2, grow=1.15)
    H = F._H
    Ro = 0.5 * H["vessel"]["value"]["od_mm"]
    rf = [1.0, Ro - 2.0, Ro, Ro + 0.5, G.SHAFT_R, G.VANE["r_in"], G.VANE["r_out"], 155.0, 195.0, TS.R_BOX]
    r = TS.axis(1.0, TS.R_BOX, rf, [(Ro - 4, Ro + 2, Lv["hhub"]), (3, 200, Lv["hr"]), (200, 280, 2 * Lv["hr"])],
                h_far=25.0, grow=1.15)
    P = PProblem(r, np.radians(th), z, eps_bg=TS.inputs()["eps_air"], periodic=True)
    T0, T1 = -0.1, 2 * math.pi + 0.1
    names, use = add_parts(P, rows, T0, T1, lambda rw: True, rotate_rotor=rot, min_r=0.6 * Lv["hr"], log=log)
    far = len(names); names.append("FAR")
    for sl in ((-1, slice(None), slice(None)), (slice(None), slice(None), 0), (slice(None), slice(None), -1)):
        P.cid[sl] = np.where(P.cid[sl] < 0, far, P.cid[sl])
    P.names[far] = "FAR"
    log(f"    F level {level}: r {len(r)} x theta {len(th)} x z {len(z)} = {P.cid.size / 1e6:.2f} M nodes, "
        f"{len(names)} conductors, {len(use)} parts")
    return P, names


BUILD = dict(W=build_W, H=build_H, F=build_F)


def _model_job(job):
    """one model solve: build, assemble, drive every conductor but FAR; the Maxwell matrix (pF, as modelled)."""
    t0 = time.time()
    lines = []
    log = lambda s: (lines.append(s), print(f"[{job['key']}] {s}", flush=True))       # noqa: E731
    kw = {k: v for k, v in job["kw"].items() if k != "part"}
    P, names = BUILD[job["model"]](log=log, **kw)
    P.assemble(log=log)
    shorts = cross_net_contacts(P, names)
    if shorts:
        log(f"    G-SHORT: {len(shorts)} cross-net contacts: {shorts[:5]}")
    present = [c for c in range(len(names)) if (P.cid == c).any()]
    drive = [c for c in present if names[c] != "FAR"]
    if "part" in job["kw"]:
        k, n = job["kw"]["part"]
        drive = drive[k::n]
    C, its = P.maxwell(drive, log=log)
    return dict(key=job["key"], model=job["model"], kw=job["kw"], names=names, present=[names[c] for c in present],
                driven=[names[c] for c in drive], C=[[None if np.isnan(x) else float(x) for x in row] for row in C],
                shape=list(P.shape), nodes=int(P.cid.size), free=int(P.nf), iterations=its,
                adjacent_pF=float(P.direct.sum() * 1e12), G_SHORT=dict(contacts=shorts, pass_=not shorts),
                run_s=time.time() - t0, log=lines)


def _nets_of(name):
    """a conductor's nets: its own, or a graded slice's two ends."""
    if name.startswith("g:"):
        return set(name.split(":")[3].split("@")[0].split(">"))
    return {name.split(":")[0]}


def cross_net_contacts(P, names):
    """G-SHORT: conductor nodes of two different nets next to each other on the grid (a short in the model); a graded
    slice may touch its own end nets and its own part's slices [OC: the nets]."""
    D = P.direct
    out = []
    for i in range(len(names)):
        for j in range(i + 1, len(names)):
            if D[i, j] > 0 and not (_nets_of(names[i]) & _nets_of(names[j])):
                same_part = names[i].startswith("g:") and names[j].startswith("g:") and                     names[i].split(":")[1] == names[j].split(":")[1]
                if not same_part:
                    out.append((names[i], names[j], float(D[i, j] * 1e12)))
    return out


def model_jobs(which, levels):
    out = []
    for mdl in which:
        for lev in levels.get(mdl, ()):
            for un in ((False,) if mdl == "F" else (False, True)):
                n = SPLIT.get(mdl, {}).get(lev, 1)
                for k in range(n):
                    kw = dict(level=lev, unaligned=un, **({"part": [k, n]} if n > 1 else {}))
                    out.append(dict(model=mdl, kw=kw, key=f"{mdl}:level={lev},unaligned={un}" + (f",part={k}/{n}" if n > 1 else "")))
    out.sort(key=lambda j: -COST.get((j["model"], j["kw"]["level"]), 0))      # the longest first
    return out


COST = {("H", 1): 8, ("W", 2): 7, ("F", 0): 5, ("W", 1): 3, ("H", 0): 3, ("W", 0): 1}


def merged(res, base):
    """one solve's record from its parts (the same grid, each part driving its share of the conductors)."""
    if base in res["solves"]:
        return res["solves"][base]
    parts = [v for k, v in res["solves"].items() if k.startswith(base + ",part=")]
    if not parts:
        return None
    n = int(next(iter(parts))["kw"]["part"][1])
    if len(parts) < n:
        return None
    C = np.array([[np.nan if x is None else x for x in row] for row in parts[0]["C"]])
    for q in parts[1:]:
        Cq = np.array([[np.nan if x is None else x for x in row] for row in q["C"]])
        C = np.where(np.isnan(C), Cq, C)
    out = dict(parts[0], key=base, driven=sorted({d for q in parts for d in q["driven"]}),
               C=[[None if np.isnan(x) else float(x) for x in row] for row in C],
               run_s=sum(q["run_s"] for q in parts))
    out["kw"] = {k: v for k, v in out["kw"].items() if k != "part"}
    return out


# ============================================================================================== the analysis
def pairs(s, scale=1.0):
    """a solve's mutual capacitances between its conductors (pF, -C[a, b] x scale), the undriven columns filled
    from their symmetric rows [OC: C is symmetric]."""
    C, names = TS.matrix(s)
    out = {}
    for i, a in enumerate(names):
        for j, b in enumerate(names):
            if j > i and a in s["present"] and b in s["present"] and not np.isnan(C[i, j]):
                out[(a, b)] = -scale * C[i, j]
    return out


def w_values(s):
    """W's quantities (pF, the full turn: x 6 for the 60 deg wedge): the varicap's own (rotor vanes - stator vanes),
    Ca's own (Ca's N1 plates - its N2 plates), and node 1's and node 2's other couplings itemised."""
    pr = pairs(s, scale=6.0)
    g = lambda a, b: pr.get((a, b), pr.get((b, a), 0.0))       # noqa: E731
    n1 = [x for x in s["present"] if x.startswith("1:")]
    n2 = [x for x in s["present"] if x.startswith("2:")]
    ref = [x for x in s["present"] if x.startswith("REF:")]
    oth = [x for x in s["present"] if x.startswith(("e:", "FAR"))]
    out = dict(varicap=g("1:Avanes", "REF:Astator"), ca=g("1:ACa", "2:ACa"))
    out["n1_ref_items"] = {f"{a}~{b}": g(a, b) for a in n1 for b in ref if (a, b) != ("1:Avanes", "REF:Astator")}
    out["n2_ref_items"] = {f"{a}~{b}": g(a, b) for a in n2 for b in ref}
    out["n1_n2_items"] = {f"{a}~{b}": g(a, b) for a in n1 for b in n2 if (a, b) != ("1:ACa", "2:ACa")}
    out["to_earth_items"] = {f"{a}~{b}": g(a, b) for a in n1 + n2 + ref for b in oth}
    out["n1_ref_stray"] = sum(out["n1_ref_items"].values())
    out["n2_ref_stray"] = sum(out["n2_ref_items"].values())
    out["n1_n2_stray"] = sum(out["n1_n2_items"].values())
    return out


def analyse_W(res):
    """per angle: W's values at each level, extrapolated (Richardson over the levels' z spacing); G-CONV."""
    out, conv = {}, []
    for un in (False, True):
        lv = sorted(int(k.split("level=")[1].split(",")[0]) for k in res["solves"]
                    if k.startswith("W:") and k.endswith(f"unaligned={un}"))
        if not lv:
            continue
        vals = [w_values(res["solves"][f"W:level={x},unaligned={un}"]) for x in lv]
        hs = [W_LEVELS[x]["hz"] for x in lv]
        row = dict(levels=lv, by_level=vals)
        ext = {}
        for k in ("varicap", "ca", "n1_ref_stray", "n2_ref_stray", "n1_n2_stray"):
            xs = [v[k] for v in vals]
            ext[k], p = TS.richardson(xs, hs)
            if len(xs) >= 2:
                conv.append(dict(angle="half pitch" if un else "aligned", what=k, last_two=xs[-2:],
                                 change=xs[-1] / xs[-2] - 1 if xs[-2] else 0.0, order=p))
        row["extrapolated"] = ext
        out["half_pitch" if un else "aligned"] = row
    if "aligned" in out and "half_pitch" in out:
        a, u = out["aligned"]["extrapolated"], out["half_pitch"]["extrapolated"]
        out["C1"] = dict(C_max_pF=a["varicap"], C_min_pF=u["varicap"], kappa=a["varicap"] / u["varicap"],
                         Ca_pF=0.5 * (a["ca"] + u["ca"]))
    lim = dict(varicap=0.02, ca=0.02)
    gate = [dict(c, tol=lim.get(c["what"], 0.10), ok=abs(c["change"]) <= lim.get(c["what"], 0.10)) for c in conv]
    out["G_CONV"] = dict(rows=gate, pass_=bool(gate) and all(g["ok"] for g in gate))
    return out


# ============================================================================================== the orchestration
def load():
    return json.load(open(RESULTS)) if os.path.exists(RESULTS) else dict(solves={})


def save(res):
    json.dump(res, open(RESULTS, "w"), indent=1, default=float)


def run(jobs, fn, procs, res, resume):
    todo = [j for j in jobs if not (resume and j["key"] in res["solves"])]
    print(f"{len(jobs)} solves, {len(todo)} to run on {procs} processes", flush=True)
    if todo:
        with Pool(procs) as pool:
            for r in pool.imap_unordered(fn, todo):
                res["solves"][r["key"]] = r
                save(res)
    return [res["solves"][j["key"]] for j in jobs]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--cell", action="store_true")
    ap.add_argument("--models", nargs="*", default=[], help="W H F")
    ap.add_argument("--levels", nargs="*", type=int, default=None)
    ap.add_argument("--dry", action="store_true", help="build and count the grids only")
    ap.add_argument("--procs", type=int, default=6)
    ap.add_argument("--resume", action="store_true")
    a = ap.parse_args()
    res = load()
    res["note"] = "S2b: the field solve on the S2a model (rebuild/s2_models/s2b-plan.md)"
    if a.models:
        lv = {k: (a.levels if a.levels is not None else {"W": [0, 1, 2], "H": [0, 1], "F": [0]}[k]) for k in a.models}
        jobs = model_jobs(a.models, lv)
        if a.dry:
            for j in jobs:
                t0 = time.time()
                P, names = BUILD[j["model"]](log=print, **j["kw"])
                print(f"  built in {time.time() - t0:.0f} s; conductors: {names}", flush=True)
            return
        run(jobs, _model_job, a.procs, res, a.resume)
        if "W" in a.models:
            res["W"] = analyse_W(res)
            save(res)
            w = res["W"]
            for ang in ("aligned", "half_pitch"):
                if ang in w:
                    for lv_, v in zip(w[ang]["levels"], w[ang]["by_level"]):
                        print(f"W {ang} level {lv_}: varicap {v['varicap']:.2f} pF, Ca {v['ca']:.2f}, N1-REF stray "
                              f"{v['n1_ref_stray']:.2f}, N2-REF {v['n2_ref_stray']:.2f}, N1-N2 {v['n1_n2_stray']:.2f}")
            if "C1" in w:
                print("W, C1:", {k: round(x, 3) for k, x in w["C1"].items()}, "G-CONV", w["G_CONV"]["pass_"])
    if a.cell:
        rows = run(cell_jobs(), _cell_job, a.procs, res, a.resume)
        res["cell"], res["G_CELL"] = cell_analyse(rows)
        save(res)
        g = res["G_CELL"]
        print(f"G-CELL: worst {g['worst_dev']:+.3%} against the record's cell ({'pass' if g['pass_'] else 'FAIL'})")
        for k, c in res["cell"].items():
            print(f"  {k}: no rims kappa {c['no_rims']['kappa_gap']:.3f}, with rims {c['with_rims']['kappa_gap']:.3f} "
                  f"(per gap {c['with_rims']['extrapolated']['aligned']:.3f} / {c['with_rims']['extrapolated']['unaligned']:.3f} pF)")


if __name__ == "__main__":
    main()
