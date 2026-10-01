#!/usr/bin/env python3
"""sim/pump_synth_gates.py -- PUMP-SYNTH (brief r0.1) build-time checks and the pre-committed verdict.

Checks (brief §5 + pump-calc §6 as incorporated):
  K      K1-K4 canaries (pump_engine.canaries) + the engine / sizing / synth on-load self-tests
  ENG    the engine file is the pump-calc engine unchanged (git diff vs the pump-calc head): its E0-E6, M1-M3,
         P0, N, F gates carry over from sim/pump-calc-findings.md
  S1     forward law at the freeze geometry under both D-CMIN conventions (279.6 / 295.6 pF)
  S1b    tools/pump-sizing.js = sim/pump_sizing.py to 1e-12 on 200 random plate inputs (Node)
  S2     the ladder at the freeze point: Ca 309 / Cx 471 pF / C_blk 440 nF (+-0.5 %)
  S3     C_blk 440 nF +- 0.5 % at 300 Hz, 0.64 H
  S4     homogeneity: every C (strays included) x k, Lx / k, R_lx / k -> z unchanged to 1e-9 (and the C-only
         deviation reported)
  S5     small-plate probe (rotor 300 mm): the bare core gives z = 1; the drawn-pump minimum plate reported
  H-GEOM C_max at the anchor (= design_synth.Cmax_from_geom) and rotor diameter 983 mm
  H-SYN0 z invariant under r_out / g_v at fixed C_max and kappa_C (1e-9)
  H-SYN1 min_diameter = a >= 15-point scan in C_max (crossing inside the scan bracket, within the tolerance)
  H-SYN2 z monotone in C_max on the searched points
  H-SYN3 every Solve result is re-run exactly and shows z >= 1 + m
  W0     warm-started monodromy = cold start to 1e-9 (the [ME] speed-up changes no number)
  M0     marginal resolution: the z = 1 (neutral) classification and the slow-transient retry agree with the
         plain iteration's long-run growth
  H-UI   no eta_op, "0.50", "0.70", "validated machine", "island sink" in the page source (grep)
  H-STAMP 43 = 43 = 43 (schematic refdes = page REF_MAP = netlist)
  P1     headline evaluation + robustness strip <= 10 s in Pyodide (Node, main + 3 helpers in parallel)
  Z      frozen files: empty diff vs 8cd181e
Verdict: PUMP-SYNTH-{LIVE, SLOW, PARTIAL, ENGINE-DRIFT, SIZING-DRIFT, CANARY-FAIL} (+ SYNTH-SCAN-ONLY).
Usage: python3 sim/pump_synth_gates.py [--only K,S1,...] [--out sim/pump_synth_gates.json]
"""
import json
import math
import os
import random
import re
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path[:0] = [HERE, ROOT, os.path.join(ROOT, "reference")]

import numpy as np                                 # noqa: E402
import pump_engine as PE                            # noqa: E402
import pump_sizing as PS                            # noqa: E402
import pump_synth as SY                             # noqa: E402

FROZEN_BASE = "8cd181e"
ENGINE_BASE = "a5420b7"                             # the pump-calc head (engine + its gate record)
FROZEN = ["shuttle_core.py", "reference", "sim/seq_stat_commutation.py", "sim/design_synth.py",
          "sim/island_asdrawn.py", "sim/island_asdrawn_r01_spice.py", "sim/island_gapbracket.py", "spice",
          "index.html", "tools/charge-pump-synth-live.html", "tools/schematic.svg", "tools/README.md",
          "tools/reference.md"]
OUT = {}


def save(path):
    if path:
        open(path, "w").write(json.dumps(PE._jsonable(OUT), indent=1) + "\n")


def gate_K():
    c = PE.canaries()
    return dict(pass_=bool(c["pass_"] and PE.SELFTEST["pass_"] and PS.SELFTEST_OK and SY.SELFTEST_OK),
                rows=c["rows"], engine_selftest=PE.SELFTEST["pass_"], sizing_selftest=PS.SELFTEST_OK,
                synth_selftest=SY.SELFTEST_OK)


def gate_ENG():
    d = subprocess.run(["git", "diff", "--stat", ENGINE_BASE, "--", "sim/pump_engine.py"], cwd=ROOT,
                       capture_output=True, text=True).stdout.strip()
    return dict(pass_=d == "", base=ENGINE_BASE, diff=d,
                note="engine unchanged since pump-calc: E0-E6 / M1-M3 / P0 / N / F carry over (sim/pump-calc-findings.md)")


def gate_S1():
    vac = dict(PS.PLATE_DEFAULTS, dielectric="vacuum")
    a = PS.rotor_caps(vac, "active_fringe")[0]
    r, rmin, _ = PS.rotor_caps(vac, "ring")
    import design_synth as ds
    ref = ds.Cmax_from_geom(95.0, 387.0, 7.0, 6, 12)
    air = PS.size()["ladder"]["C_max"]["value"]
    _, A_ring = PS.plate_areas(vac)
    return dict(pass_=bool(abs(a - ref) <= 1e-9 * ref and abs(a - 279.6) < 0.05 and abs(r - 295.6) < 0.06
                           and abs(A_ring - 0.01265) < 2e-6),
                active_only_pF=a, design_synth_pF=ref, ring_pF=r, ring_Cmin_pF=rmin, A_ring_m2=A_ring,
                air_default_pF=air, eps_air=PS.eps_air(20.0, 1013.0, 50.0))


def gate_S1b(n=200):
    rng = random.Random(20260930)
    cases = []
    for _ in range(n):
        ri = rng.uniform(20, 200)
        p = dict(r_inMm=ri, r_outMm=ri + rng.uniform(20, 500), g_vMm=rng.uniform(1, 15),
                 dielectric=rng.choice(["air", "vacuum", "kapton", "mica"]), tempC=rng.uniform(-10, 40),
                 p_hPa=rng.uniform(800, 1050), rh=rng.uniform(0, 100), N_sec=rng.choice([8, 12, 16, 24]),
                 ring_on=rng.random() < 0.7, r_ring_inMm=rng.uniform(10, 30), r_ring_outMm=rng.uniform(30, 90))
        p["n_kept"] = p["N_sec"] // 2
        c = dict(cmin_conv=rng.choice(["active_fringe", "ring"]), cpar_mode=rng.choice(["fixed", "scaled"]),
                 ratio_Ca=rng.uniform(0.5, 2), ratio_Cx=rng.uniform(1, 2.5), rpm=rng.uniform(500, 9000),
                 L_coil_H=rng.uniform(0.1, 2))
        if rng.random() < 0.2:
            c["pins"] = {"Ca": rng.uniform(100, 500)}
        cases.append((p, c))
    js = subprocess.run(["node", "-e", "const S=require('./tools/pump-sizing.js');"
                         "const cs=JSON.parse(require('fs').readFileSync(0,'utf8'));"
                         "console.log(JSON.stringify({st:S.selftest().pass,out:cs.map(([p,c])=>S.size(p,c))}))"],
                        cwd=ROOT, input=json.dumps(cases), capture_output=True, text=True)
    J = json.loads(js.stdout)
    worst = [0.0]; mism = []

    def cmp(a, b, path):
        if isinstance(a, dict):
            if set(a) != set(b):
                mism.append(path + " keys"); return
            for k in a:
                cmp(a[k], b[k], path + "." + k)
        elif isinstance(a, (int, float)) and not isinstance(a, bool):
            if b is None:
                mism.append(path); return
            worst[0] = max(worst[0], abs(a - b) / max(1.0, abs(a)))
        elif a != b:
            mism.append(path)
    for (p, c), o in zip(cases, J["out"]):
        cmp(PS.size(p, c), o, "")
    return dict(pass_=bool(J["st"] and worst[0] <= 1e-12 and not mism), n=n, worst_rel=worst[0],
                mismatches=mism[:5], js_selftest=J["st"])


def gate_S2():
    L = PS.size(dict(dielectric="vacuum"))["ladder"]
    rows = dict(Ca=(L["Ca"]["value"], 309.0), cx_max=(L["cx_max"]["value"], 471.0), C_blk_nF=(L["C_blk_nF"]["value"], 440.0))
    dev = {k: (v - r) / r for k, (v, r) in rows.items()}
    return dict(pass_=all(abs(d) <= 5e-3 for d in dev.values()), values={k: v for k, (v, _) in rows.items()},
                rel_dev=dev, note="vacuum, active-only C_max 279.64 pF (the guide §6.1 basis)")


def gate_S3():
    cb, prf = PS.c_blk_nF(3000.0, 0.64, 6)
    return dict(pass_=bool(abs(prf - 300.0) < 1e-12 and abs(cb - 440.0) / 440.0 <= 5e-3), C_blk_nF=cb, PRF=prf)


CAPS = ["C1min", "C1max", "C2min", "C2max", "Ca", "Cb", "Cpar", "cx_max", "cx_min", "pCboss", "gap_stray", "island_stray"]


def gate_S4(ks=(0.37, 3.7)):
    lad, fi = SY.sized({})
    c = SY.engine_cfg(lad, fi)
    z0, _ = SY.z_of(c, warm=False)
    rows = []
    for k in ks:
        c1 = dict(c, **{kk: c[kk] * k for kk in CAPS}); c1["Lx_mH"] /= k; c1["R_lx"] /= k
        z1, cv1 = SY.z_of(PE.make_config({kk: c1[kk] for kk in PE.DEFAULTS}), warm=False)
        c2 = dict(c, **{kk: c[kk] * k for kk in CAPS})
        z2, cv2 = SY.z_of(PE.make_config({kk: c2[kk] for kk in PE.DEFAULTS}), warm=False)
        rows.append(dict(k=k, dz_coscaled=z1 - z0, dz_C_only=z2 - z0, converged=bool(cv1 and cv2)))
    return dict(pass_=all(abs(r["dz_coscaled"]) <= 1e-9 and r["converged"] for r in rows), z0=z0, rows=rows,
                note="C x k with Lx / k and R_lx / k (impedance-consistent) is exact; C-only leaves the island ring "
                     "time as the one non-capacitive scale")


def gate_S5():
    r = 300.0 / 2 / (1 + PS.BUS_MARGIN)
    lad, fi = SY.sized({"r_outMm": r})
    core, _ = SY.run(SY.engine_cfg(lad, fi, {"topology": "core"}), warm=False)
    drawn, _ = SY.run(SY.engine_cfg(lad, fi), warm=False)
    mp = SY.min_plate({})
    return dict(pass_=bool(core["converged"] and abs(core["z"] - 1.0) < 1e-9),
                r_outMm=r, C_max_pF=lad["ladder"]["C_max"]["value"], core_z=core["z"], core_kind=core.get("kind"),
                drawn_z=drawn["z"], drawn_kind=drawn.get("kind"), min_plate=mp)


def gate_HGEOM():
    import design_synth as ds
    vac = dict(PS.PLATE_DEFAULTS, dielectric="vacuum")
    a = PS.rotor_caps(vac, "active_fringe")[0]
    ref = ds.Cmax_from_geom(95.0, 387.0, 7.0, 6, 12)
    dia = PS.size()["rotor_dia_mm"]
    return dict(pass_=bool(abs(a - ref) <= 1e-9 * ref and abs(dia - 983.0) < 0.5), C_max_pF=a, design_synth=ref,
                rotor_dia_mm=dia, design_synth_dia=ds.rotor_dia_mm(dict(r_outMm=387.0)))


def gate_HSYN0():
    base = SY.sized({})[0]["ladder"]["C_max"]["value"]
    # (r_out, g_v) pairs with the same C_max: A_m / g fixed  ->  g' = g (r'^2 - r_in^2) / (r^2 - r_in^2)
    rows = []
    ref = None
    for r in (387.0, 330.0, 450.0):
        g = 7.0 * (r * r - 95.0 ** 2) / (387.0 ** 2 - 95.0 ** 2)
        lad, fi = SY.sized({"r_outMm": r, "g_vMm": g})
        z, cv = SY.z_of(SY.engine_cfg(lad, fi), warm=False)
        ref = z if ref is None else ref
        rows.append(dict(r_outMm=r, g_vMm=g, C_max_pF=lad["ladder"]["C_max"]["value"],
                         kappa=lad["kappa_C"], z=z, dz=z - ref, converged=cv))
    return dict(pass_=all(abs(x["dz"]) <= 1e-9 and abs(x["C_max_pF"] - base) <= 1e-9 * base and x["converged"]
                          for x in rows), rows=rows,
                note="g_v != 7 mm changes eps_r? no -- eps_r(air) does not depend on g; C_max and kappa held")


def gate_HSYN123(n_scan=15):
    t0 = time.time()
    SY._WARM.clear()
    r = SY.min_diameter({}, n_scan=n_scan)
    if not r.get("scan"):
        return dict(pass_=False, error="min_diameter returned no scan", result=r)
    scan = r["scan"]
    tgt = r["target"]
    # the scan's crossing: the first scan point with z >= target and its predecessor
    idx = next(i for i, s in enumerate(scan) if s["converged"] and s["z"] >= tgt)
    a, b = scan[idx - 1], scan[idx]
    lin = a["r_outMm"] + (b["r_outMm"] - a["r_outMm"]) * (tgt - a["z"]) / (b["z"] - a["z"])
    inside = a["r_outMm"] <= r["r_out_z"] <= b["r_outMm"]
    # the linear interpolation error of the coarse scan, from the curvature of the 3 nearest scan points
    c = scan[idx + 1] if idx + 1 < len(scan) else a
    h = b["r_outMm"] - a["r_outMm"]
    curv = abs(c["z"] - 2 * b["z"] + a["z"]) / (h * h)
    slope = (b["z"] - a["z"]) / h
    interp_err = curv * h * h / 8 / max(slope, 1e-12)
    syn1 = inside and abs(r["r_out_z"] - lin) <= 1.0 + interp_err
    syn3 = bool(r["final"] and r["final"]["converged"] and r["final"]["z"] >= tgt - 1e-12)
    out = dict(H_SYN1=dict(pass_=bool(syn1), r_found=r["r_out_z"], r_scan_linear=lin, bracket=[a["r_outMm"], b["r_outMm"]],
                           tol_mm=1.0, interp_err_mm=interp_err, scan=scan),
               H_SYN2=dict(pass_=bool(r["monotone"]), points=r["points"]),
               H_SYN3_min_diameter=dict(pass_=syn3, z=r["z"], target=tgt, feasible=r["final"]["feasible"] if r["final"] else None),
               result={k: r[k] for k in ("found", "r_outMm", "dia_mm", "z", "g_vMm", "binding", "runs", "time_s", "note", "geom")},
               time_s=time.time() - t0)
    mm = SY.max_margin({}, ca_search=True)
    out["H_SYN3_max_margin"] = dict(pass_=bool(mm["final"]["converged"]), z=mm["z"], r_outMm=mm["r_outMm"],
                                    ca=mm["ca"], time_s=mm["time_s"])
    mr = SY.max_rpm({})
    out["H_SYN3_max_rpm"] = dict(pass_=bool(mr["confirm"]["converged"] and mr["feasible"]), rpm=mr["rpm"],
                                 binding=mr["binding"], z=mr["z"], time_s=mr["time_s"])
    return out


def gate_W0():
    rows = []
    for inp in ({}, {"r_outMm": 360.0}, {"r_outMm": 420.0, "gm_load": "valve", "gm_fire": "valve"}):
        lad, fi = SY.sized(inp)
        cfg = SY.engine_cfg(lad, fi)
        zc, cc = SY.z_of(cfg, warm=False)
        zw, cw = SY.z_of(cfg, warm=True)
        rows.append(dict(inp=inp, z_cold=zc, z_warm=zw, dz=zw - zc, converged=bool(cc and cw)))
    return dict(pass_=all(abs(r["dz"]) <= 1e-9 and r["converged"] for r in rows), rows=rows, stats=dict(SY.STATS))


def _plain_growth(cfg, n=160, tail=10):
    net = PE.build_net(cfg); sim = PE.make_sim(net, cfg); PE.seed(sim)
    g = []
    for k in range(n):
        m0 = sim.state_mag(); sim.cycle(k); m1 = sim.state_mag(); g.append(m1 / m0); sim.rescale(1.0 / m1)
    return g[-1], g[-tail:]


def gate_M0():
    rows = []
    for r in (245.0, 250.0):
        lad, fi = SY.sized({"r_outMm": r})
        cfg = SY.engine_cfg(lad, fi)
        m, _ = SY.run(cfg, warm=False)
        g_last, tail = _plain_growth(cfg)
        e = [x - 1.0 for x in tail]
        tr = (e[-1] / e[0]) ** (1.0 / (len(e) - 1)) if e[0] > 0 and e[-1] > 0 else None
        rows.append(dict(r_outMm=r, z=m["z"], converged=m["converged"], kind=m.get("kind"), rate=m.get("rate"),
                         bound=m.get("bound"), plain_growth_160=g_last, tail_ratio=tr))
    # 245 mm: the plain iteration's excess after 160 cycles must match the measured geometric decay (the
    # classification's own rate), within a factor 2, and be small
    ex = rows[0]["plain_growth_160"] - 1.0
    rows[0]["excess_160"] = ex
    ok = (rows[0]["kind"] == "neutral" and 0 <= ex < 1e-4 and rows[0]["tail_ratio"] is not None
          and abs(rows[0]["tail_ratio"] - rows[0]["rate"]) < 2e-3 and
          rows[1]["kind"] is None and abs(rows[1]["z"] - rows[1]["plain_growth_160"]) < 1e-9)
    return dict(pass_=bool(ok), rows=rows,
                note="245 mm: the growth excess decays geometrically onto the neutral mode (z = 1); 250 mm: a slow "
                     "transient, the retried monodromy equals the plain iteration's long-run growth")


BANNED = ["η_op", "eta_op", "0.50", "0.70", "validated machine", "island sink"]


def gate_HUI():
    hits = {}
    for f in ("tools/pump-synth.html", "tools/pump-synth.worker.js", "tools/pump-sizing.js"):
        src = open(os.path.join(ROOT, f), encoding="utf8").read()
        for b in BANNED:
            if b in src:
                hits.setdefault(f, []).append(b)
    return dict(pass_=not hits, banned=BANNED, hits=hits)


_REFDES = re.compile(r"^(C\d|C_AR\d|C__AR\d|C_BR\d|C_R\d|Ca\d|Cb\d|Cx\d|Lx\d|L_A\d|L_B\d|L_R\d|SG\d[a-z]?\d?|BS\d)$")


def gate_HSTAMP():
    svg = open(os.path.join(ROOT, "tools/schematic.svg"), encoding="utf8").read()
    drawn = {t.strip() for t in re.findall(r"<text[^>]*>([^<]*)</text>", svg) if _REFDES.match(t.strip())}
    net = set()
    for l in open(os.path.join(ROOT, "topology_edge_list.csv"), encoding="utf8"):
        c = l.split(",")
        if c[0] and c[0][0] != "#" and c[0] != "component":
            net.add(c[0].strip())
    page = open(os.path.join(ROOT, "tools/pump-synth.html"), encoding="utf8").read()
    blk = page[page.index("const REF_MAP = (() => {"):page.index("return M;\n})();")]
    mapped = set()
    for arr in re.findall(r"add\(\[([^\]]*)\]", blk):
        mapped |= {x.strip().strip('"') for x in arr.split(",") if x.strip()}
    return dict(pass_=bool(len(drawn) == len(mapped) == len(net) == 43 and drawn == mapped == net),
                drawn=len(drawn), mapped=len(mapped), netlist=len(net),
                diff=dict(drawn_not_mapped=sorted(drawn - mapped), mapped_not_drawn=sorted(mapped - drawn),
                          net_not_drawn=sorted(net - drawn)))


P1_BENCH = r"""
import { loadPyodide } from "%(pyo)s/pyodide.mjs";
import fs from "fs";
const R = "%(root)s/";
const files = ["sim/pump_engine.py","sim/pump_sizing.py","sim/pump_synth.py","shuttle_core.py","reference/doubler_core.py",
  "reference/island_resonant_core.py","spice/timing.sub","topology_edge_list.csv","sim/design_synth.py",
  "energy_balance_from_solver.py","sim/island_charging_cosim.py","reference/commutator_real_core.py",
  "reference/doubler_resonant_core.py","presets/G3-geometry-v010.json"];
const [role, model, go1, go2] = process.argv.slice(2);
const t0 = Date.now();
const py = await loadPyodide({ indexURL: "%(pyo)s/" });
await py.loadPackage("numpy");
for (const d of ["/repo/sim","/repo/reference","/repo/spice","/repo/presets"]) py.FS.mkdirTree(d);
for (const f of files) py.FS.writeFile("/repo/"+f, fs.readFileSync(R+f, "utf8"));
await py.runPythonAsync("import sys; sys.path[:0]=['/repo/sim','/repo','/repo/reference']; import pump_synth as P, pump_engine as PE, json, time");
const boot = (Date.now() - t0) / 1000;
const wait = t => new Promise(r => setTimeout(r, Math.max(0, t - Date.now())));
const out = {role, model, boot_s: boot};
for (const [tag, go, inp] of [["cold", +go1, "{}"], ["warm", +go2, "{'r_outMm': 380.0}"]]){
  await wait(go);
  out[tag + "_start"] = Date.now();
  const code = role === "main"
    ? `r = P.evaluate(${inp}, with_strip=False, with_twins=False); json.dumps(dict(z=r['z']))`
    : `lad, fi = P.sized(${inp}); z, c = P.z_of(P.engine_cfg(lad, fi, dict(P.STRIP)['${model}'])); json.dumps(dict(z=z))`;
  out[tag + "_z"] = JSON.parse(await py.runPythonAsync(code)).z;
  out[tag + "_end"] = Date.now();
}
console.log(JSON.stringify(out));
"""


def gate_P1():
    pyo = os.environ.get("PYODIDE_DIR", "/tmp/claude-0/pyo/pyodide")
    if not os.path.isdir(pyo):
        return dict(pass_=False, error=f"no local Pyodide at {pyo}")
    path = "/tmp/claude-0/ps/p1_bench.mjs"
    os.makedirs(os.path.dirname(path), exist_ok=True)
    open(path, "w").write(P1_BENCH % dict(pyo=pyo, root=ROOT))
    lad, fi = SY.sized({})
    cfg = SY.engine_cfg(lad, fi)
    others = [n for n, ov in SY.STRIP if not all(cfg.get(k) == v for k, v in ov.items())]
    go1 = int(time.time() * 1000) + 40000; go2 = go1 + 60000
    procs = [subprocess.Popen(["node", path, "main", "-", str(go1), str(go2)], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)]
    for n in others:
        procs.append(subprocess.Popen(["node", path, "helper", n, str(go1), str(go2)], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True))
    outs = []
    for p in procs:
        so, se = p.communicate(timeout=900)
        try:
            outs.append(json.loads(so.strip().splitlines()[-1]))
        except Exception:
            outs.append(dict(error=(so + se)[-400:]))
    res = dict(cores=os.cpu_count(), workers=len(procs), rows=outs)
    if all("cold_end" in o for o in outs):
        for tag in ("cold", "warm"):
            res[tag + "_wall_s"] = (max(o[tag + "_end"] for o in outs) - min(o[tag + "_start"] for o in outs)) / 1000
            res[tag + "_serial_s"] = sum((o[tag + "_end"] - o[tag + "_start"]) / 1000 for o in outs)
    res["pass_"] = bool(res.get("cold_wall_s", 1e9) <= 10.0 and res.get("warm_wall_s", 1e9) <= 10.0)
    return res


def gate_Z():
    d = subprocess.run(["git", "diff", "--stat", FROZEN_BASE, "--"] + FROZEN, cwd=ROOT, capture_output=True, text=True).stdout.strip()
    return dict(pass_=d == "", base=FROZEN_BASE, diff=d)


GATES = [("K", gate_K), ("ENG", gate_ENG), ("S1", gate_S1), ("S1b", gate_S1b), ("S2", gate_S2), ("S3", gate_S3),
         ("S4", gate_S4), ("HGEOM", gate_HGEOM), ("HSYN0", gate_HSYN0), ("W0", gate_W0), ("M0", gate_M0),
         ("HUI", gate_HUI), ("HSTAMP", gate_HSTAMP), ("Z", gate_Z), ("S5", gate_S5), ("HSYN", gate_HSYN123),
         ("P1", gate_P1)]


def verdict(o):
    g = lambda k: (o.get(k) or {}).get("pass_", False)
    if not g("K"):
        return "PUMP-SYNTH-CANARY-FAIL"
    if not g("ENG"):
        return "PUMP-SYNTH-ENGINE-DRIFT"
    if not all(g(k) for k in ("S1", "S1b", "S2", "S3", "S4", "HGEOM")):
        return "PUMP-SYNTH-SIZING-DRIFT"
    syn = o.get("HSYN") or {}
    core = all(g(k) for k in ("HSYN0", "W0", "M0", "HUI", "HSTAMP", "Z", "S5")) and all(
        (syn.get(k) or {}).get("pass_", False) for k in ("H_SYN1", "H_SYN3_min_diameter", "H_SYN3_max_margin", "H_SYN3_max_rpm"))
    if not core:
        return "PUMP-SYNTH-PARTIAL"
    v = "PUMP-SYNTH-LIVE" if g("P1") else "PUMP-SYNTH-SLOW"
    if not (syn.get("H_SYN2") or {}).get("pass_", False):
        v += " + SYNTH-SCAN-ONLY"
    return v


def main():
    only = None; out = os.path.join(HERE, "pump_synth_gates.json")
    a = sys.argv[1:]
    if "--only" in a:
        only = set(a[a.index("--only") + 1].split(","))
    if "--out" in a:
        out = a[a.index("--out") + 1]
    if os.path.exists(out):
        try:
            OUT.update(json.load(open(out)))
        except Exception:
            pass
    for name, fn in GATES:
        if only and name not in only:
            continue
        t0 = time.time()
        print(f"[{name}] …", flush=True)
        try:
            r = fn()
        except Exception as e:
            import traceback
            r = dict(pass_=False, error=f"{type(e).__name__}: {e}", tb=traceback.format_exc()[-1500:])
        if isinstance(r, dict) and "pass_" not in r:
            r["pass_"] = all(v.get("pass_", False) for v in r.values() if isinstance(v, dict) and "pass_" in v)
        r["gate_time_s"] = time.time() - t0
        OUT[name] = r
        print(f"[{name}] {'PASS' if r.get('pass_') else 'FAIL'} ({r['gate_time_s']:.1f} s)", flush=True)
        save(out)
    OUT["verdict"] = verdict(OUT)
    save(out)
    print("VERDICT", OUT["verdict"])


if __name__ == "__main__":
    main()
