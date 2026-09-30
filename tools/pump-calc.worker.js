/* tools/pump-calc.worker.js — the PUMP-CALC engine worker (Pyodide).
 *
 * Runs sim/pump_engine.py (the exact engine) in a Web Worker so the page never blocks.
 * Boot path copied, with attribution, from tools/charge-pump-synth-live.html @ 8cd181e:
 * Pyodide 0.26.2 from the jsdelivr CDN, loadPackage("numpy"), and the REAL repo files fetched
 * into the virtual FS (no vendored copies, so no drift is possible). Fail-closed: the K1-K4
 * canaries run here BEFORE any number is sent to the page; a failure is reported as CANARY-FAIL
 * and the worker refuses to evaluate.
 *
 * Messages in:  {type:"init", pyodide?}  {type:"evaluate", id, config, twins}
 *               {type:"sweep", id, config, key, values}
 * Messages out: {type:"boot", msg}  {type:"canaries", ok, result}  {type:"down", error}
 *               {type:"progress", id, msg}  {type:"result", id, result}  {type:"error", id, error}
 */
"use strict";
const PYODIDE_CDN = "https://cdn.jsdelivr.net/pyodide/v0.26.2/full/";
// repo files, relative to this worker (tools/) -> the virtual FS under /repo
const REPO_FILES = {
  "/repo/sim/pump_engine.py":                 "../sim/pump_engine.py",
  "/repo/shuttle_core.py":                    "../shuttle_core.py",
  "/repo/reference/doubler_core.py":          "../reference/doubler_core.py",
  "/repo/reference/island_resonant_core.py":  "../reference/island_resonant_core.py",
  "/repo/spice/timing.sub":                   "../spice/timing.sub",
  "/repo/topology_edge_list.csv":             "../topology_edge_list.csv",
  // design_synth (lamps I3/I6/I11/I12 + Cmax_from_geom) and what it imports
  "/repo/sim/design_synth.py":                "../sim/design_synth.py",
  "/repo/energy_balance_from_solver.py":      "../energy_balance_from_solver.py",
  "/repo/sim/island_charging_cosim.py":       "../sim/island_charging_cosim.py",
  "/repo/reference/commutator_real_core.py":  "../reference/commutator_real_core.py",
  "/repo/reference/doubler_resonant_core.py": "../reference/doubler_resonant_core.py",
  "/repo/presets/G3-geometry-v010.json":      "../presets/G3-geometry-v010.json",
};
let py = null, ready = false, canaryOK = false;

function post(o){ self.postMessage(o); }

async function init(cdn){
  try {
    const base = cdn || PYODIDE_CDN;
    post({type:"boot", msg:"booting Pyodide…"});
    importScripts(base + "pyodide.js");
    py = await loadPyodide({ indexURL: base });
    post({type:"boot", msg:"loading numpy…"});
    await py.loadPackage("numpy");
    post({type:"boot", msg:"fetching the repo files…"});
    for (const d of ["/repo/sim", "/repo/reference", "/repo/spice", "/repo/presets"]) py.FS.mkdirTree(d);
    for (const [dst, src] of Object.entries(REPO_FILES)){
      const r = await fetch(new URL(src, self.location.href));
      if (!r.ok) throw new Error("fetch " + src + " → " + r.status + " (serve from the repo root over http)");
      py.FS.writeFile(dst, await r.text());
    }
    post({type:"boot", msg:"importing pump_engine (on-load self-test)…"});
    await py.runPythonAsync(`
import sys, json
sys.path[:0] = ['/repo/sim', '/repo', '/repo/reference']
import pump_engine as _pe
import js as _js
def _call(fn, payload, rid):
    a = json.loads(payload)
    def log(m):
        _js.postMessage(_js.JSON.parse(json.dumps(dict(type="progress", id=rid, msg=m))))
    if fn == "evaluate":
        return json.dumps(_pe.evaluate(a.get("config"), twins=a.get("twins", True), log=log))
    if fn == "sweep":
        out = []
        vals = a["values"]
        for i, v in enumerate(vals):
            log(f"sweep {a['key']} = {v} ({i + 1}/{len(vals)})")
            c = dict(a.get("config") or {}); c[a["key"]] = v
            r = _pe.evaluate(c, twins=False)
            out.append(dict(v=v, z=r["z"], converged=r["converged"]))
        zs = [o["z"] for o in out]
        cross = []
        for i in range(len(vals) - 1):
            x, y = zs[i] - 1.0, zs[i + 1] - 1.0
            if x == 0: cross.append(vals[i])
            elif x * y < 0: cross.append(vals[i] + (vals[i + 1] - vals[i]) * x / (x - y))
        return json.dumps(dict(key=a["key"], points=out, crossings=cross))
    return _pe.api(fn, payload)
`);
    post({type:"boot", msg:"running the K1–K4 canaries…"});
    const can = JSON.parse(await py.runPythonAsync(`json.dumps(dict(canaries=_pe.canaries(), selftest=_pe._jsonable(_pe.SELFTEST), defaults=_pe._jsonable(_pe.DEFAULTS), version=_pe.ENGINE_VERSION))`));
    canaryOK = !!(can.canaries.pass_ && can.selftest.pass_);
    ready = true;
    post({type:"canaries", ok: canaryOK, result: can});
  } catch (e){
    post({type:"down", error: String(e && e.message || e)});
  }
}

async function call(msg, fn){
  if (!ready){ post({type:"error", id: msg.id, error:"engine not ready"}); return; }
  if (!canaryOK){ post({type:"error", id: msg.id, error:"CANARY-FAIL: the engine refuses to evaluate"}); return; }
  try {
    const t0 = performance.now();
    py.globals.set("_payload", JSON.stringify(msg));
    py.globals.set("_rid", msg.id);
    py.globals.set("_fn", fn);
    const out = await py.runPythonAsync(`_call(_fn, _payload, _rid)`);
    const res = JSON.parse(out);
    res.wall_s = (performance.now() - t0) / 1000;
    post({type:"result", id: msg.id, kind: fn, result: res});
  } catch (e){
    post({type:"error", id: msg.id, error: String(e && e.message || e)});
  }
}

let queue = Promise.resolve();
self.onmessage = (ev) => {
  const m = ev.data || {};
  if (m.type === "init") { queue = queue.then(() => init(m.pyodide)); return; }
  if (m.type === "evaluate") { queue = queue.then(() => call(m, "evaluate")); return; }
  if (m.type === "sweep") { queue = queue.then(() => call(m, "sweep")); return; }
};
