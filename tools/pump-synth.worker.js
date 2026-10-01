/* tools/pump-synth.worker.js — the PUMP-SYNTH engine worker (Pyodide). One file, two roles.
 *
 *   role "main"   : boots Pyodide, fetches the REAL repo files, imports sim/pump_synth.py (which imports
 *                   pump_sizing + pump_engine, both with on-load self-tests), runs the K1–K4 canaries and the
 *                   H-GEOM rung BEFORE any number reaches the page (fail-closed), then serves
 *                   evaluate / twins / solve / critical / min_plate / sweep.
 *   role "helper" : the same boot and import (same files, same self-tests) but no canaries; it serves only
 *                   "z" jobs (one exact run: the robustness strip in parallel). The page sends it work only
 *                   after the main worker's canaries passed.
 *
 * Boot path copied from tools/pump-calc.worker.js (this branch), itself from
 * tools/charge-pump-synth-live.html @ 8cd181e: Pyodide 0.26.2 from the jsdelivr CDN, loadPackage("numpy"),
 * repo files fetched into the virtual FS, never vendored.
 *
 * In : {type:"init", role, base, pyodide?}  {type:"call", id, fn, args}
 * Out: {type:"boot", msg}  {type:"ready", role, result}  {type:"down", error}
 *      {type:"progress", id, msg}  {type:"result", id, result}  {type:"error", id, error}
 */
"use strict";
const PYODIDE_CDN = "https://cdn.jsdelivr.net/pyodide/v0.26.2/full/";
const REPO_FILES = {
  "/repo/sim/pump_engine.py":                 "../sim/pump_engine.py",
  "/repo/sim/pump_sizing.py":                 "../sim/pump_sizing.py",
  "/repo/sim/pump_synth.py":                  "../sim/pump_synth.py",
  "/repo/shuttle_core.py":                    "../shuttle_core.py",
  "/repo/reference/doubler_core.py":          "../reference/doubler_core.py",
  "/repo/reference/island_resonant_core.py":  "../reference/island_resonant_core.py",
  "/repo/spice/timing.sub":                   "../spice/timing.sub",
  "/repo/topology_edge_list.csv":             "../topology_edge_list.csv",
  // design_synth (I3/I4/I6/I9/I11/I12 rules + Cmax_from_geom) and what it imports
  "/repo/sim/design_synth.py":                "../sim/design_synth.py",
  "/repo/energy_balance_from_solver.py":      "../energy_balance_from_solver.py",
  "/repo/sim/island_charging_cosim.py":       "../sim/island_charging_cosim.py",
  "/repo/reference/commutator_real_core.py":  "../reference/commutator_real_core.py",
  "/repo/reference/doubler_resonant_core.py": "../reference/doubler_resonant_core.py",
  "/repo/presets/G3-geometry-v010.json":      "../presets/G3-geometry-v010.json",
};
let py = null, ready = false, canaryOK = false, ROLE = "main", BASE = self.location.href;

function post(o){ self.postMessage(o); }

const BRIDGE = `
import sys, json, time
sys.path[:0] = ['/repo/sim', '/repo', '/repo/reference']
import pump_engine as _pe
import pump_sizing as _ps
import pump_synth as _syn
import js as _js
_CANARY_OK = False
def _call(fn, payload, rid):
    a = json.loads(payload)
    def log(m):
        _js.postMessage(_js.JSON.parse(json.dumps(dict(type="progress", id=rid, msg=m))))
    inp = a.get("inp") or {}
    if fn == "z":                                   # one exact run (helpers: the robustness strip)
        lad, fi = _syn.sized(inp)
        cfg = _syn.engine_cfg(lad, fi, a.get("over") or {})
        t = time.time(); z, c = _syn.z_of(cfg)
        return json.dumps(dict(z=z, converged=c, time_s=time.time() - t, model=a.get("model")))
    if not _CANARY_OK:
        raise RuntimeError("CANARY-FAIL: the engine refuses to evaluate")
    if fn == "evaluate":
        return json.dumps(_syn.evaluate(inp, with_strip=a.get("strip", False), with_twins=a.get("twins", False),
                                        canary_ok=_CANARY_OK, log=log))
    if fn == "twins":
        return json.dumps(_syn.add_twins(log=log))
    if fn == "solve":
        return json.dumps(_syn.solve(a["objective"], inp, log=log, **(a.get("kw") or {})))
    if fn == "critical":
        return json.dumps(_syn.critical(inp, a["key"], log=log))
    if fn == "min_plate":
        return json.dumps(_syn.min_plate(inp, log=log))
    if fn == "sweep":                               # z against one input key (plate or choice), exact runs
        out = []
        for i, v in enumerate(a["values"]):
            log(f"sweep {a['key']} = {v} ({i + 1}/{len(a['values'])})")
            d = dict(inp); d[a["key"]] = v
            lad, fi = _syn.sized(d)
            z, c = _syn.z_of(_syn.engine_cfg(lad, fi))
            out.append(dict(v=v, z=z, converged=c, C_max=lad["ladder"]["C_max"]["value"]))
        zs = [o["z"] for o in out]; vals = a["values"]; cross = []
        for i in range(len(vals) - 1):
            x, y = zs[i] - 1.0, zs[i + 1] - 1.0
            if x == 0: cross.append(vals[i])
            elif x * y < 0: cross.append(vals[i] + (vals[i + 1] - vals[i]) * x / (x - y))
        return json.dumps(dict(key=a["key"], points=out, crossings=cross))
    raise KeyError(fn)

def _boot_main():
    global _CANARY_OK
    can = _pe.canaries()
    lad = _ps.size()
    vac = _ps.rotor_caps(dict(_ps.PLATE_DEFAULTS, dielectric="vacuum"), "active_fringe")[0]
    vring = _ps.rotor_caps(dict(_ps.PLATE_DEFAULTS, dielectric="vacuum"), "ring")[0]
    import design_synth as _ds
    ds_c = _ds.Cmax_from_geom(95.0, 387.0, 7.0, 6, 12)
    hgeom = [dict(id="H-GEOM", check="C_max at R95-R387, 7 mm, vacuum, active-only (D-CMIN default) = design_synth.Cmax_from_geom",
                  expected=ds_c, got=vac, tol="1e-9 rel", pass_=abs(vac - ds_c) <= 1e-9 * ds_c),
             dict(id="H-GEOM", check="C_max with the ring term (the other D-CMIN convention)", expected=295.6, got=vring,
                  tol="0.06 pF", pass_=abs(vring - 295.6) < 0.06),
             dict(id="H-GEOM", check="rotor diameter at r_out 387 (BUS_MARGIN 0.27), mm", expected=983.0,
                  got=lad["rotor_dia_mm"], tol="0.5 mm", pass_=abs(lad["rotor_dia_mm"] - 983.0) < 0.5)]
    ok = bool(can["pass_"] and _pe.SELFTEST["pass_"] and _ps.SELFTEST_OK and _syn.SELFTEST_OK and all(r["pass_"] for r in hgeom))
    _CANARY_OK = ok
    return json.dumps(dict(canaries=can, selftest=_pe._jsonable(_pe.SELFTEST), hgeom=_pe._jsonable(hgeom),
                           sizing_selftest=bool(_ps.SELFTEST_OK), synth_selftest=bool(_syn.SELFTEST_OK), ok=ok,
                           defaults=_pe._jsonable(_syn.defaults()), strip=[n for n, _ in _syn.STRIP],
                           strip_over=dict(_syn.STRIP), disabled=_syn.DISABLED_OBJECTIVES,
                           engine_version=_pe.ENGINE_VERSION, synth_version=_syn.SYNTH_VERSION))
`;

async function init(m){
  try {
    ROLE = m.role || "main";
    const base = m.pyodide || PYODIDE_CDN;
    post({type:"boot", msg:`[${ROLE}] booting Pyodide…`});
    importScripts(base + "pyodide.js");
    py = await loadPyodide({ indexURL: base });
    post({type:"boot", msg:`[${ROLE}] loading numpy…`});
    await py.loadPackage("numpy");
    post({type:"boot", msg:`[${ROLE}] fetching the repo files…`});
    for (const d of ["/repo/sim", "/repo/reference", "/repo/spice", "/repo/presets"]) py.FS.mkdirTree(d);
    for (const [dst, src] of Object.entries(REPO_FILES)){
      const r = await fetch(new URL(src, BASE));
      if (!r.ok) throw new Error("fetch " + src + " → " + r.status + " (serve from the repo root over http)");
      py.FS.writeFile(dst, await r.text());
    }
    post({type:"boot", msg:`[${ROLE}] importing pump_synth (on-load self-tests)…`});
    await py.runPythonAsync(BRIDGE);
    let result = {};
    if (ROLE === "main"){
      post({type:"boot", msg:"running the K1–K4 canaries and the H-GEOM rung…"});
      result = JSON.parse(await py.runPythonAsync(`_boot_main()`));
      canaryOK = !!result.ok;
    } else {
      result = JSON.parse(await py.runPythonAsync(`json.dumps(dict(ok=bool(_pe.SELFTEST["pass_"] and _ps.SELFTEST_OK and _syn.SELFTEST_OK)))`));
      canaryOK = !!result.ok;
    }
    ready = true;
    post({type:"ready", role: ROLE, result});
  } catch (e){
    post({type:"down", role: ROLE, error: String(e && e.message || e)});
  }
}

async function call(msg){
  if (!ready){ post({type:"error", id: msg.id, error:"engine not ready"}); return; }
  if (!canaryOK){ post({type:"error", id: msg.id, error:"CANARY-FAIL: the engine refuses to evaluate"}); return; }
  try {
    const t0 = performance.now();
    py.globals.set("_payload", JSON.stringify(msg.args || {}));
    py.globals.set("_rid", msg.id);
    py.globals.set("_fn", msg.fn);
    const res = JSON.parse(await py.runPythonAsync(`_call(_fn, _payload, _rid)`));
    res.wall_s = (performance.now() - t0) / 1000;
    post({type:"result", id: msg.id, fn: msg.fn, result: res});
  } catch (e){
    post({type:"error", id: msg.id, error: String(e && e.message || e)});
  }
}

let queue = Promise.resolve();
self.onmessage = (ev) => {
  const m = ev.data || {};
  if (m.type === "init"){ if (m.base) BASE = m.base; queue = queue.then(() => init(m)); return; }
  if (m.type === "call"){ queue = queue.then(() => call(m)); return; }
};
