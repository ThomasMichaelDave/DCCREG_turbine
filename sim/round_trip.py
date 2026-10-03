#!/usr/bin/env python3
"""
sim/round_trip.py — ROUND-TRIP orchestrator: geometry -> integrity -> field solve -> reduction -> engine
=========================================================================================================
  geometry(params)   pump_geometry.build on a stage-1 lock (D-SCALING: what tracks r_out is in SCALING)
  integrity          circuit_integrity.analyze must report 0 FAIL (RT3); its nets are the reduction's nodes
  field solve        field_solve: the Maxwell matrix at N_theta relative angles over one 60-degree period
  reduction          Maxwell matrix -> two-terminal couplings between the drawn nets and to the enclosure,
                     each a periodic function of the relative angle (Fourier interpolation, CModel)
  engine             rt_engine: series tank, the couplings in place of the ladder and the floors

Angles [IR, the engine frame]: the engine's theta is the relative rotor angle at which a gap arms (its
station). In the build a rotor tip at rotor angle t meets the station sphere at stator angle s when the
rotor has turned by s - t, so theta_geom = theta_engine - t_tip. pump_geometry puts the tips at
t_tip = TIP_DEG (0 in the stage-2 build). Pure EE.
"""
import json
import math
import os
import sys
import time

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
for _p in (HERE, ROOT, os.path.join(ROOT, "reference")):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import field_solve as FS                      # noqa: E402

PERIOD = 60.0
RES = {   # field-solve resolution levels [ME]; FS5 decides which one is good enough
    "c": dict(h_min_z=1.0, h_min_r=1.0, grow=1.6, h_max_z=5.0, h_max_r=6.0, h_max_p=2.5, h_min_arc=1.5),
    "m": dict(h_min_z=0.6, h_min_r=0.6, grow=1.5, h_max_z=4.0, h_max_r=5.0, h_max_p=2.0, h_min_arc=1.0),
    "f": dict(h_min_z=0.5, h_min_r=0.5, grow=1.45, h_max_z=3.0, h_max_r=4.0, h_max_p=1.5, h_min_arc=0.6),
    "x": dict(h_min_z=0.35, h_min_r=0.35, grow=1.35, h_max_z=2.5, h_max_r=3.0, h_max_p=1.0, h_min_arc=0.4),
}


def rotor_names(design):
    return {p["name"] for p in design["parts"] if str(p.get("body", "")).startswith("rotor")}


def solve_theta(design, theta_geom, level="c", enclosure=50.0, r_cut=25.0, tol=1e-5, warm=None):
    """The Maxwell matrix of the whole build at one relative angle (rotor turned by theta_geom degrees).
    Returns dict(names, C (pF, full machine), info). warm: a dict carried between calls (the previous
    potential, re-gridded in phi, starts the solve)."""
    prims = FS.dedupe(FS.primitives(design["parts"]))
    rot = rotor_names(design)
    th = theta_geom % PERIOD
    rotor_edges = sorted({(q["a0"] + th) % PERIOD for q in prims if q["kind"] == "sector" and q["name"] in rot
                          and q["cond"] is not None and q["w"] < 360 - 1e-9} |
                         {(q["a0"] + q["w"] + th) % PERIOD for q in prims if q["kind"] == "sector" and q["name"] in rot
                          and q["cond"] is not None and q["w"] < 360 - 1e-9})
    stator = [q for q in prims if q["name"] not in rot]
    rprims = [q for q in prims if q["name"] in rot]
    # grid: snapped to the stator as is and to the rotor turned by theta
    moved = [dict(q, a0=(q["a0"] + th) % 360.0) if q["kind"] == "sector" and q["w"] < 360 - 1e-9 else q for q in rprims]
    g, bc = FS.build_grid(stator + moved, enclosure=enclosure, res=RES[level], theta_breaks=rotor_edges)
    eps, cond, names = FS.rasterize(g, prims, rotor=rot, theta=th)
    V0 = None
    if warm is not None and warm.get("V") is not None and warm["shape_rz"] == (g.shape[0], g.shape[2]) \
            and warm["names"] == names and np.allclose(warm["r"], g.r) and np.allclose(warm["z"], g.z):
        V0 = FS.regrid_phi(warm["V"], warm["pc"], g.pc)
    C, info = FS.maxwell(g, eps, cond, names, bc, r_cut=r_cut, tol=tol, V0=V0, return_V=warm is not None)
    if warm is not None:
        warm.update(V=info["V"], pc=g.pc.copy(), r=g.r.copy(), z=g.z.copy(), shape_rz=(g.shape[0], g.shape[2]), names=names)
    info = {k: v for k, v in info.items() if k != "V"}
    info["warm"] = V0 is not None
    info.update(shape=list(g.shape), theta_geom=theta_geom, level=level, enclosure=enclosure)
    return dict(names=names, C=(C * 6.0 * 1e12).tolist(), info=info)


def _worker(args):
    os.environ["OMP_NUM_THREADS"] = "1"
    path, chunk, level, enclosure = args
    design = json.load(open(path)) if isinstance(path, str) else path
    warm = {}
    return [(t, solve_theta(design, t, level, enclosure, warm=warm)) for t in chunk]


def sweep(design_path, thetas, level="c", enclosure=50.0, procs=4, log=None):
    """Maxwell matrices at every relative angle: `procs` processes, each a contiguous run of angles
    warm-started from its previous angle."""
    import multiprocessing as mp
    ctx = mp.get_context("fork")
    n = len(thetas)
    chunks = [list(thetas[k * n // procs:(k + 1) * n // procs]) for k in range(procs)]
    chunks = [c for c in chunks if c]
    out = {}
    with ctx.Pool(len(chunks)) as pool:
        for res in pool.imap_unordered(_worker, [(design_path, c, level, enclosure) for c in chunks]):
            for th, r in res:
                out[th] = r
                if log:
                    log(f"theta {th:g}: {r['info']['cells']} cells, {r['info']['t_solve']:.0f} s, its {sum(r['info']['iterations'])}")
    return [out[t] for t in thetas]


# ---------------------------------------------------------------------------------------------------
# reduction: Maxwell matrices -> periodic two-terminal couplings on the drawn nets
# ---------------------------------------------------------------------------------------------------
MERGE = {"n18": "R-A", "n00": "R-B"}          # the tank coils are shorts at the pump frequency [OC]


def reduce(sols, merge=MERGE):
    """[(theta_geom, Maxwell pF)] -> {(a, b): array over theta} of two-terminal pF, b = 'enc' for the
    enclosure; nets in `merge` are joined first (sum of rows and columns)."""
    names = sols[0]["names"]
    nets = []
    for n in names:
        m = merge.get(n, n)
        if m not in nets:
            nets.append(m)
    T = np.zeros((len(nets), len(names)))
    for j, n in enumerate(names):
        T[nets.index(merge.get(n, n)), j] = 1.0
    prof = {}
    for s in sols:
        assert s["names"] == names
        C = T @ np.array(s["C"]) @ T.T
        for i, a in enumerate(nets):
            prof.setdefault((a, "enc"), []).append(float(C[i].sum()))
            for j in range(i + 1, len(nets)):
                key = tuple(sorted((a, nets[j])))
                prof.setdefault(key, []).append(float(-C[i, j]))
    return {k: np.array(v) for k, v in prof.items()}, nets


class CModel:
    """Periodic couplings for the engine: f(theta_engine) in F. Fourier interpolation over the samples
    (uniform in [0, 60) geometric degrees); theta_geom = theta_engine - tip_deg."""

    def __init__(self, thetas, prof, tip_deg=0.0, tag="build", min_pF=0.0, drop=()):
        self.thetas = np.asarray(thetas, float)
        self.tip = tip_deg
        self.tag = tag
        n = len(self.thetas)
        assert np.allclose(np.diff(self.thetas), PERIOD / n) and abs(self.thetas[0]) < 1e-9, "uniform samples from 0"
        self.coef = {}
        for k, v in prof.items():
            if k in drop or np.max(np.abs(v)) < min_pF:
                continue
            self.coef[k] = np.fft.rfft(np.asarray(v, float)) / n
        self.n = n
        self._cache = {}

    def value(self, key, theta_geom):
        c = self.coef[key]
        n = self.n
        x = 2 * math.pi * (theta_geom % PERIOD) / PERIOD
        k = np.arange(c.size)
        w = np.where((k == 0) | ((n % 2 == 0) & (k == n // 2)), 1.0, 2.0)
        return float(np.sum(w * (c.real * np.cos(k * x) - c.imag * np.sin(k * x))))

    def caps(self):
        out = []
        for key in self.coef:
            a, b = key
            if a == "enc":
                a, b = b, a
            f = self._fn(key)
            out.append((f"C[{key[0]}|{key[1]}]", a, b, f))
        return out

    def _fn(self, key):
        def f(th_e, key=key):
            t = round((th_e - self.tip) % PERIOD, 9)
            ck = (key, t)
            v = self._cache.get(ck)
            if v is None:
                v = 1e-12 * self.value(key, t)
                if len(self._cache) > 400000:
                    self._cache.clear()
                self._cache[ck] = v
            return v
        return f


def save(path, thetas, sols):
    json.dump(dict(thetas=list(thetas), sols=sols), open(path, "w"))


def load(path):
    d = json.load(open(path))
    return d["thetas"], d["sols"]


# ---------------------------------------------------------------------------------------------------
# the round-trip ledger at one design point: one change at a time (brief §9)
# ---------------------------------------------------------------------------------------------------
VARICAP_KEYS = {"C1": ("1", "R-A"), "C2": ("4", "R-B"), "Cx3": ("7", "n17"), "Cx4": ("8", "n23"),
                "Ca": ("1", "2"), "Cb": ("3", "4"), "C_R1": ("R-A", "R-B")}


def _key(a, b):
    return tuple(sorted((a, b))) if "enc" not in (a, b) else ((a, b) if b == "enc" else (b, a))


def field_values(prof):
    """the ladder's numbers as the build realizes them (fringe included): extremes of the varicaps, means of
    the fixed ones."""
    v = {k: prof[_key(*ab)] for k, ab in VARICAP_KEYS.items()}
    return dict(C1max=float(v["C1"].max()), C1min=float(v["C1"].min()), C2max=float(v["C2"].max()),
                C2min=float(v["C2"].min()), cx3_max=float(v["Cx3"].max()), cx3_min=float(v["Cx3"].min()),
                cx4_max=float(v["Cx4"].max()), cx4_min=float(v["Cx4"].min()), Ca=float(v["Ca"].mean()),
                Cb=float(v["Cb"].mean()), C_R1=float(v["C_R1"].mean()))


def ledger(cfg, thetas, prof, overlap, tip_deg=15.0, log=None):
    """[(step, z, converged, note)] from pump-synth's headline to the fully round-tripped z.
    overlap: the integrity tool's realized (overlap-only) values {C1max, C1min, cx_max, cx_min, Ca, C_R1}."""
    import rt_engine as RT
    rows = []

    def run(step, note, cfg_, **kw):
        t0 = time.time()
        z, conv = RT.z_of(cfg_, **kw)
        rows.append(dict(step=step, z=z, converged=conv, note=note, time_s=time.time() - t0))
        if log:
            log(f"{step}: z {z:.6f} {'conv' if conv else 'NOT converged'} -- {note}")
    run("L0 pump-synth headline", "ladder, parallel tank (collapsed)", cfg)
    run("L1 series tank", f"C_R1 {overlap['C_R1']:.2f} pF realized, R-A the reference", cfg, tank="series",
        C_R1_pF=overlap["C_R1"])
    c2 = dict(cfg, C1max=overlap["C1max"], C2max=overlap["C1max"], C1min=overlap["C1min"], C2min=overlap["C1min"],
              cx_max=overlap["cx_max"], cx_min=overlap["cx_min"], Ca=overlap["Ca"], Cb=overlap["Ca"])
    run("L2 realized C's (overlap)", "integrity-tool overlap values in the ladder's profile shapes", c2, tank="series",
        C_R1_pF=overlap["C_R1"])
    fv = field_values(prof)
    c3 = dict(cfg, C1max=fv["C1max"], C1min=fv["C1min"], C2max=fv["C2max"], C2min=fv["C2min"],
              cx_max=0.5 * (fv["cx3_max"] + fv["cx4_max"]), cx_min=0.5 * (fv["cx3_min"] + fv["cx4_min"]),
              Ca=fv["Ca"], Cb=fv["Cb"])
    run("L3 fringe (field) C's", f"C1 {fv['C1min']:.1f}-{fv['C1max']:.1f}, Cx {c3['cx_min']:.1f}-{c3['cx_max']:.1f}, "
        f"Ca {fv['Ca']:.1f}, C_R1 {fv['C_R1']:.1f} pF", c3, tank="series", C_R1_pF=fv["C_R1"])
    ladder_keys = {_key(*ab) for ab in VARICAP_KEYS.values()}
    others = {k: v for k, v in prof.items() if k not in ladder_keys}
    const = [(f"S[{k[0]}|{k[1]}]", k[0], k[1], 1e-12 * float(np.mean(v))) for k, v in others.items()]
    keep = ("C1", "C2", "Ca", "Cb", "Cx3", "Cx4")
    run("L4 extracted strays + Cpar", f"{len(others)} other couplings at their mean replace the ladder floors",
        c3, tank="series", C_R1_pF=fv["C_R1"], ladder=keep, extra=const, ref="R-A")
    cm_o = CModel(thetas, others, tip_deg=tip_deg, tag="others")
    run("L5 parasitic varicaps", "the other couplings as functions of the angle", c3, tank="series",
        C_R1_pF=fv["C_R1"], ladder=keep, extra=cm_o.caps(), ref="R-A")
    cm = CModel(thetas, prof, tip_deg=tip_deg, tag="build")
    run("L6 drawn varicap profiles", f"C1 / C2 / Cx / Ca / C_R1 as the build realizes them over the turn (tips at {tip_deg:g} deg)",
        c3, ladder=(), extra=cm.caps(), ref="R-A")
    run("L7 enclosure reference", "both rotor halves float; every coupling to the grounded can", c3, cmodel=cm)
    return rows, fv


def _selftest():
    # the Fourier model reproduces its samples and is 60-degree periodic; reduce() keeps reciprocity
    th = [60.0 * k / 12 for k in range(12)]
    v = np.array([100 + 50 * math.cos(math.radians(6 * t)) + 3 * math.sin(math.radians(12 * t)) for t in th])
    cm = CModel(th, {("1", "R-A"): v})
    ok = all(abs(cm.value(("1", "R-A"), t) - x) < 1e-9 for t, x in zip(th, v))
    ok &= abs(cm.value(("1", "R-A"), 7.0) - cm.value(("1", "R-A"), 67.0)) < 1e-9
    C = np.array([[10.0, -4.0, -1.0], [-4.0, 9.0, -2.0], [-1.0, -2.0, 5.0]])
    prof, nets = reduce([dict(names=["1", "n18", "R-A"], C=C.tolist())])
    ok &= nets == ["1", "R-A"] and abs(prof[("1", "R-A")][0] - 5.0) < 1e-12 and abs(prof[("1", "enc")][0] - 5.0) < 1e-12
    if not ok:
        raise AssertionError("round_trip on-load self-test FAILED")
    return True


SELFTEST_OK = _selftest()
