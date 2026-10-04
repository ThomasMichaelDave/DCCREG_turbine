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


MEM_BUDGET = 12.5e9          # bytes for all workers together (the session's cgroup kills near 15 GB) [ME]
BYTES_PER_CELL = 1100.0      # peak RSS per solve (3.7 GB at 3.5 M cells, OOM record): matrix, RS-AMG hierarchy, warm-start potentials [ME]


def _procs_for(design, thetas, level, enclosure, procs):
    """as many processes as the memory budget allows for the largest grid of the sweep."""
    prims = FS.dedupe(FS.primitives(design["parts"]))
    g, _ = FS.build_grid(prims, enclosure=enclosure, res=RES[level], theta_breaks=[0.0, 7.5, 15.0, 22.5])
    est = BYTES_PER_CELL * float(np.prod(g.shape)) * 1.2          # the other angles snap more rotor edges in phi
    return max(1, min(procs, len(thetas), int(MEM_BUDGET // est)))


def sweep(design_path, thetas, level="c", enclosure=50.0, procs=4, log=None):
    """Maxwell matrices at every relative angle: up to `procs` processes (fewer if the memory budget says
    so), each a contiguous run of angles warm-started from its previous angle. A killed worker raises
    (BrokenProcessPool), never hangs."""
    import multiprocessing as mp
    from concurrent.futures import ProcessPoolExecutor, as_completed
    design = json.load(open(design_path)) if isinstance(design_path, str) else design_path
    out = {}
    part = f"{design_path}.{level}.partial.json" if isinstance(design_path, str) else None
    if part and os.path.exists(part):                       # angles a killed run already solved
        out = {float(k): v for k, v in json.load(open(part)).items()}
    thetas_all, thetas = list(thetas), [t for t in thetas if t not in out]
    if not thetas:
        return [out[t] for t in thetas_all]
    procs = _procs_for(design, thetas, level, enclosure, procs)
    n = len(thetas)
    nch = procs if procs > 1 else n                               # one process: one angle per chunk, saved as it lands
    chunks = [list(thetas[k * n // nch:(k + 1) * n // nch]) for k in range(nch)]
    chunks = [c for c in chunks if c]
    if log:
        log(f"sweep: {n} angles, {procs} processes, {len(chunks)} chunks")
    with ProcessPoolExecutor(procs, mp_context=mp.get_context("fork")) as ex:
        futs = [ex.submit(_worker, (design_path, c, level, enclosure)) for c in chunks]
        for f in as_completed(futs):
            for th, r in f.result():
                out[th] = r
                if log:
                    log(f"theta {th:g}: {r['info']['cells']} cells, {r['info']['t_solve']:.0f} s, its {sum(r['info']['iterations'])}")
            if part:
                json.dump({str(k): v for k, v in out.items()}, open(part, "w"))
    if part and os.path.exists(part):
        os.remove(part)
    return [out[t] for t in thetas_all]


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


# ---------------------------------------------------------------------------------------------------
# one design through the whole round trip
# ---------------------------------------------------------------------------------------------------
RT_GEOM = dict(sg_tip_deg=15.0)        # timing-consistent rotor tips (C1 aligned at engine theta 15) [IR]


def design_for(plates=None, geom=None):
    """stage-1 ladder for the plates -> lock -> the pump-geometry build (RT_GEOM + geom)."""
    import pump_geometry as PG
    import pump_sizing as PS
    lad = PS.size(dict(plates or {}))
    lock = PG.lock_record(lad, {}, 0.0, False, "round_trip")
    g = dict(RT_GEOM)
    # D-SCALING [IR, TMD-gated]: voltage-set features fixed; the outer class tracks r_out -- the return band
    # keeps its 23 mm beyond the plates (r410 at r_out 387), the axial bar band its r375 / 387 ratio; the bars,
    # pickups and carrier edge already scale with r_out in the builder
    ro = lad["plates"]["r_outMm"]
    g.update(sg_rrail=ro + 23.0, sg_rbar=ro * 375.0 / 387.0)
    g.update(geom or {})
    return PG.build(lock, g), lad


def integrity(design):
    import circuit_integrity as CI
    rep = CI.analyze(CI.parts_from_design(design), CI.load_netlist(), "round-trip candidate")
    return dict(verdict=rep["verdict"], counts=rep["counts"], nets=len(rep["nets"]),
                fails=[f["text"] for f in rep["findings"] if f["level"] == "FAIL"][:5])


def evaluate_design(tag, plates=None, geom=None, level="c", n_theta=12, enclosure=50.0, procs=4, outdir=None,
                    log=None, firing=None):
    """geometry -> integrity -> field sweep -> reduction -> engine. Cached by tag in outdir."""
    import pump_synth as SY
    import rt_engine as RT
    outdir = outdir or os.path.join(ROOT, "docs", "geometry", "rt")
    os.makedirs(outdir, exist_ok=True)
    design, lad = design_for(plates, geom)
    # a "(tank, shown only)" check is information (brief §5: the tank's reach is a core matter) [IR]
    geo_fail = [k for k, v in design["checks"].items() if not v["pass_"] and "shown only" not in k]
    geo_info = [k for k, v in design["checks"].items() if not v["pass_"] and "shown only" in k]
    integ = integrity(design)
    res = dict(tag=tag, plates=dict(plates or {}), geom=dict(RT_GEOM, **(geom or {})), level=level, n_theta=n_theta,
               enclosure=enclosure, geometry_fails=geo_fail, geometry_info=geo_info, integrity=integ, r_edge=design["r_edge"],
               D_mm=2.0 * design["r_edge"], z_total=design["z_total"], ladder_Ca=lad["ladder"]["Ca"]["value"])
    epath = os.path.join(outdir, f"{tag}.eval.json")
    if geo_fail or integ["verdict"] != "PASS":
        res["excluded"] = "INTEGRITY-FAIL" if integ["verdict"] != "PASS" else "GEOMETRY-CHECK-FAIL"
        json.dump(res, open(epath, "w"), indent=1)
        return res
    dpath = os.path.join(outdir, f"{tag}.design.json")
    json.dump(design, open(dpath, "w"))
    spath = os.path.join(outdir, f"{tag}.{level}{n_theta}.sweep.json")
    thetas = [PERIOD * k / n_theta for k in range(n_theta)]
    if os.path.exists(spath):
        thetas, sols = load(spath)
    else:
        sols = sweep(dpath, thetas, level=level, enclosure=enclosure, procs=procs, log=log)
        save(spath, thetas, sols)
    prof, nets = reduce(sols)
    res["field"] = field_values(prof)
    cfg = SY.engine_cfg(*SY.sized(dict(plates or {}, **(firing or {}))))
    cm = CModel(thetas, prof, tip_deg=res["geom"]["sg_tip_deg"])
    t0 = time.time()
    m = RT.run(RT.build_net(cfg, cmodel=cm), cfg)
    res.update(z=m["z"], converged=m["converged"], t_engine=time.time() - t0)
    json.dump(res, open(epath, "w"), indent=1)
    return res


# ---------------------------------------------------------------------------------------------------
# the floor: the radius surrogate (FS8) and the search (D1, D2)
# ---------------------------------------------------------------------------------------------------
def profiles_of(tag, level="c", n_theta=12, outdir=None):
    outdir = outdir or os.path.join(ROOT, "docs", "geometry", "rt")
    thetas, sols = load(os.path.join(outdir, f"{tag}.{level}{n_theta}.sweep.json"))
    prof, nets = reduce(sols)
    return thetas, prof


class Surrogate:
    """every coupling at every sampled angle as a + b r + c r^2 in r_out, fitted to >= 4 solved radii
    (area-type couplings ~ r^2, edge-type ~ r, fixed ones constant) [ME, brief §3]."""

    def __init__(self, radii, profs, deg=2):
        self.radii = np.asarray(radii, float)
        keys = set(profs[0])
        for p in profs[1:]:
            keys &= set(p)
        self.keys = sorted(keys)
        X = np.vander(self.radii, deg + 1, increasing=True)
        self.coef, self.resid = {}, {}
        for k in self.keys:
            Y = np.array([p[k] for p in profs])                      # (n_r, n_theta)
            c, *_ = np.linalg.lstsq(X, Y, rcond=None)
            self.coef[k] = c
            fit = X @ c
            scale = max(np.max(np.abs(Y)), 1e-9)
            self.resid[k] = float(np.max(np.abs(fit - Y)) / scale)
        self.deg = deg

    def prof(self, r):
        x = np.vander(np.array([float(r)]), self.deg + 1, increasing=True)[0]
        return {k: x @ c for k, c in self.coef.items()}

    def worst_resid(self, min_pF=1.0):
        big = [(self.resid[k], k) for k in self.keys if np.max(np.abs(self.coef[k][0])) > 0 or True]
        return max(big)


def z_cmodel(thetas, prof, plates, tip_deg, firing=None, C_R1_pF=None):
    import pump_synth as SY
    import rt_engine as RT
    cfg = SY.engine_cfg(*SY.sized(dict(plates or {}, **(firing or {}))))
    p = dict(prof)
    if C_R1_pF is not None:
        p[("R-A", "R-B")] = np.full_like(np.asarray(p[("R-A", "R-B")], float), C_R1_pF)
    cm = CModel(thetas, p, tip_deg=tip_deg)
    m = RT.run(RT.build_net(cfg, cmodel=cm), cfg)
    return m["z"], m["converged"]


def floor_search(name, radii, plates=None, geom=None, margin=0.20, level="c", n_theta=12, log=None, confirm=True,
                 r_scan=None, firing=None):
    """D_floor for one lever setting: solve the round trip at `radii` (r_out, mm), fit the surrogate,
    scan z(r_out), find z = 1 + m, confirm exactly there (D2), monotonicity on the bracket (D1)."""
    plates = dict(plates or {})
    tip = dict(RT_GEOM, **(geom or {}))["sg_tip_deg"]
    runs, profs, thetas = [], [], None
    for r in radii:
        tag = f"{name}-r{r:g}"
        res = evaluate_design(tag, dict(plates, r_outMm=r), geom, level=level, n_theta=n_theta, log=log, firing=firing)
        runs.append(res)
        if res.get("excluded"):
            continue
        th, pr = profiles_of(tag, level, n_theta)
        thetas = th
        profs.append((r, pr))
    out = dict(name=name, radii=list(radii), runs=[{k: v for k, v in r.items() if k not in ("geom",)} for r in runs])
    if len(profs) < 4:
        out["verdict"] = "SURROGATE-NEEDS-4-RADII"
        return out
    sur = Surrogate([r for r, _ in profs], [p for _, p in profs])
    out["surrogate_resid"] = sur.worst_resid()
    lo_r, hi_r = min(r for r, _ in profs), max(r for r, _ in profs)
    grid = list(r_scan or np.linspace(lo_r, hi_r, 9))
    zs = []
    for r in grid:
        z, conv = z_cmodel(thetas, sur.prof(r), dict(plates, r_outMm=r), tip, firing)
        zs.append((float(r), z, conv))
    out["scan"] = zs
    target = 1.0 + margin
    mono = all(zs[i + 1][1] >= zs[i][1] - 1e-9 for i in range(len(zs) - 1)) or \
        all(zs[i + 1][1] <= zs[i][1] + 1e-9 for i in range(len(zs) - 1))
    out["D1_monotone"] = bool(mono)
    above = [r for r, z, c in zs if z >= target]
    if not above:
        out["verdict"] = "NO-FLOOR-IN-RANGE"
        out["z_max"] = max(z for r, z, c in zs)
        return out
    # the smallest r with z >= target: bisection on the surrogate between the last below and the first above
    i = next(k for k, (r, z, c) in enumerate(zs) if z >= target)
    if i == 0:
        out["verdict"] = "FLOOR-BELOW-BRACKET"
        out["r_floor"] = zs[0][0]
        return out
    a, b = zs[i - 1][0], zs[i][0]
    for _ in range(12):
        m_ = 0.5 * (a + b)
        z, _c = z_cmodel(thetas, sur.prof(m_), dict(plates, r_outMm=m_), tip, firing)
        a, b = (m_, b) if z < target else (a, m_)
    r_star = b
    z_sur, _ = z_cmodel(thetas, sur.prof(r_star), dict(plates, r_outMm=r_star), tip, firing)
    out.update(r_floor=r_star, z_surrogate=z_sur)
    if confirm:
        tag = f"{name}-floor"
        ex = evaluate_design(tag, dict(plates, r_outMm=round(r_star, 2)), geom, level=level, n_theta=n_theta, log=log, firing=firing)
        out["exact"] = {k: v for k, v in ex.items() if k not in ("geom",)}
        out["D2_dz"] = abs(ex.get("z", float("nan")) - z_sur)
        out["D2"] = bool(out["D2_dz"] < 1e-3)
    out["verdict"] = "FLOOR-SET"
    return out


# ---------------------------------------------------------------------------------------------------
# certification runs (records in sim/round_trip_runs.json; rt_gates reads them)
# ---------------------------------------------------------------------------------------------------
RUNS = os.path.join(HERE, "round_trip_runs.json")


def _record(key, val):
    d = json.load(open(RUNS)) if os.path.exists(RUNS) else {}
    if isinstance(val, dict) and isinstance(d.get(key), dict) and key == "floor":
        d[key].update(val)
    else:
        d[key] = val
    json.dump(d, open(RUNS, "w"), indent=1, default=float)


def sweep_n(tag, n_theta, level="c", procs=4, log=None, outdir=None, enclosure=50.0):
    """the tag's sweep at n_theta angles, reusing every cached sweep whose angles are a subset."""
    outdir = outdir or os.path.join(ROOT, "docs", "geometry", "rt")
    spath = os.path.join(outdir, f"{tag}.{level}{n_theta}.sweep.json")
    if os.path.exists(spath):
        return load(spath)
    thetas = [PERIOD * k / n_theta for k in range(n_theta)]
    have = {}
    for f in os.listdir(outdir):
        if f.startswith(f"{tag}.{level}") and f.endswith(".sweep.json"):
            th, so = load(os.path.join(outdir, f))
            have.update({round(t, 9): s for t, s in zip(th, so)})
    todo = [t for t in thetas if round(t, 9) not in have]
    if todo:
        new = sweep(os.path.join(outdir, f"{tag}.design.json"), todo, level=level, enclosure=enclosure, procs=procs, log=log)
        have.update({round(t, 9): s for t, s in zip(todo, new)})
    sols = [have[round(t, 9)] for t in thetas]
    save(spath, thetas, sols)
    return thetas, sols


def run_rt2(tag="freeze-t15", log=print):
    import pump_synth as SY
    import rt_engine as RT
    cfg = SY.engine_cfg(*SY.sized({}))
    th48, s48 = sweep_n(tag, 48, log=log)
    z = {}
    for n in (12, 24, 48):
        step = 48 // n
        th, so = th48[::step], s48[::step]
        prof, _ = reduce(so)
        m = RT.run(RT.build_net(cfg, cmodel=CModel(th, prof, tip_deg=RT_GEOM["sg_tip_deg"])), cfg)
        z[n] = m["z"]
        log(f"RT2 N_theta {n}: z {m['z']:.7f} conv {m['converged']}")
    _record("rt2", dict(tag=tag, z=z))
    return z


def run_fs5(tag="freeze-t15", levels=("c", "m", "f"), thetas=(0.0, 30.0), log=print):
    """per-refinement change of every reduced coupling at the aligned (0) and disaligned (30) geometric
    angle; the sweep level's offset from the finest level reported for the ladder couplings."""
    design = json.load(open(os.path.join(ROOT, "docs", "geometry", "rt", f"{tag}.design.json")))
    cache = os.path.join(ROOT, "docs", "geometry", "rt", f"{tag}.fs5.json")
    sols = json.load(open(cache)) if os.path.exists(cache) else {}
    for L in levels:
        for t in thetas:
            k = f"{L}@{t:g}"
            if k not in sols:
                t0 = time.time()
                sols[k] = solve_theta(design, t, L)
                log(f"FS5 {k}: {sols[k]['info']['cells']} cells, {time.time() - t0:.0f} s")
                json.dump(sols, open(cache, "w"))
    steps = []
    for a, b in zip(levels[:-1], levels[1:]):
        worst_rel, worst_abs, rows = 0.0, 0.0, []
        for t in thetas:
            pa, _ = reduce([sols[f"{a}@{t:g}"]])
            pb, _ = reduce([sols[f"{b}@{t:g}"]])
            for key in pb:
                va, vb = float(pa[key][0]), float(pb[key][0])
                if abs(vb) >= 1.0:
                    rel = abs(va / vb - 1)
                    worst_rel = max(worst_rel, rel)
                    rows.append(dict(key="|".join(key), theta=t, coarse=va, fine=vb, rel=rel))
                else:
                    worst_abs = max(worst_abs, abs(va - vb))
        rows.sort(key=lambda r: -r["rel"])
        steps.append(dict(step=f"{a}->{b}", worst_rel=worst_rel, worst_abs_small_pF=worst_abs,
                          pass_=bool(worst_rel < 5e-3 and worst_abs < 0.1), rows=rows[:12]))
        log(f"FS5 {a}->{b}: worst rel {worst_rel:.4f}, small-coupling abs {worst_abs:.3f} pF")
    off = {}
    for t in thetas:
        pc, _ = reduce([sols[f"{levels[0]}@{t:g}"]])
        pf, _ = reduce([sols[f"{levels[-1]}@{t:g}"]])
        for nm, ab in VARICAP_KEYS.items():
            k = _key(*ab)
            off[f"{nm}@{t:g}"] = float(pc[k][0] / pf[k][0] - 1)
    rec = dict(tag=tag, levels=list(levels), thetas=list(thetas), steps=steps, offset=off)
    _record("fs5", rec)
    return rec


def export_cad(design, prefix, label, outdir=None):
    """docs/geometry/<prefix>-<hash>.{json,step,-parts.csv} through the existing FreeCAD builder (the OCC
    stand-in G-CAD uses), and <prefix>-<hash>-integrity.txt read back from the STEP. hash = the parts."""
    import hashlib
    import circuit_integrity as CI
    import pump_geometry_gates as PGG
    outdir = outdir or os.path.join(ROOT, "docs", "geometry")
    h = hashlib.sha1(json.dumps(design["parts"], sort_keys=True).encode()).hexdigest()[:8]
    base = os.path.join(outdir, f"{prefix}-{h}")
    open(base + ".json", "w").write(json.dumps(design, indent=1) + "\n")
    PGG._install_occ_freecad()
    os.environ["PUMP_GEOMETRY_JSON"] = base + ".json"
    src = open(os.path.join(ROOT, "tools", "pump-geometry.FCMacro"), encoding="utf8").read()
    ns = {"__name__": "__macro__"}
    exec(compile(src, "pump-geometry.FCMacro", "exec"), ns)
    rep = CI.analyze(CI.parts_from_step(base + ".step"), CI.load_netlist(), os.path.basename(base) + ".step")
    open(base + "-integrity.txt", "w").write(f"# {label}\n" + CI.render(rep) + "\n")
    return dict(hash=h, base=os.path.relpath(base, ROOT), solids=len(ns["RESULT"]), integrity=rep["verdict"],
                counts=rep["counts"])


if __name__ == "__main__":
    if "--rt2" in sys.argv:
        run_rt2()
    if "--fs5" in sys.argv:
        lv = sys.argv[sys.argv.index("--fs5") + 1].split(",") if len(sys.argv) > sys.argv.index("--fs5") + 1 else "cmf"
        run_fs5(levels=tuple(lv))
