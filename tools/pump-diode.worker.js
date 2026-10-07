/* tools/pump-diode.worker.js — the PUMP-DIODE engine worker (Pyodide): the bare de Queiroz diode doubler (no flying bucket)
 * on the DISC or the TUBE, and the C-EM power assessment (sim/diode_machine.py). Copied from tools/pump-stack.worker.js.
 *
 * Boot path copied from tools/pump-synth.worker.js (this branch; that file is frozen and is not edited):
 * Pyodide 0.26.2 from the jsdelivr CDN, loadPackage("numpy"), the REAL repo files fetched into the virtual FS.
 * Imports sim/stack_sizing.py (on-load self-test: the 2-D vane cell against the parallel-plate limit, disc mode =
 * pump_sizing), which imports pump_sizing; z comes from pump_synth (record) or rt_engine (v4).
 * Fail-closed: K1–K4 canaries + engine / sizing / synth / stack self-tests + the disc anchor gate (the default disc
 * under the record topology must give RT0's z 1.3254745) BEFORE any number reaches the page.
 *
 * In : {type:"init", base, pyodide?}  {type:"call", id, fn, args}
 * Out: {type:"boot", msg}  {type:"ready", result}  {type:"down", error}
 *      {type:"progress", id, msg}  {type:"result", id, result}  {type:"error", id, error}
 */
"use strict";
const PYODIDE_CDN = "https://cdn.jsdelivr.net/pyodide/v0.26.2/full/";
const REPO_FILES = {
  "/repo/sim/pump_engine.py":                 "../sim/pump_engine.py",
  "/repo/sim/pump_sizing.py":                 "../sim/pump_sizing.py",
  "/repo/sim/pump_synth.py":                  "../sim/pump_synth.py",
  "/repo/sim/rt_engine.py":                   "../sim/rt_engine.py",
  "/repo/sim/stack_sizing.py":                "../sim/stack_sizing.py",
  "/repo/sim/diode_machine.py":               "../sim/diode_machine.py",
  "/repo/shuttle_core.py":                    "../shuttle_core.py",
  "/repo/reference/doubler_core.py":          "../reference/doubler_core.py",
  "/repo/reference/island_resonant_core.py":  "../reference/island_resonant_core.py",
  "/repo/spice/timing.sub":                   "../spice/timing.sub",
  "/repo/topology_edge_list.csv":             "../topology_edge_list.csv",
  "/repo/sim/design_synth.py":                "../sim/design_synth.py",
  "/repo/energy_balance_from_solver.py":      "../energy_balance_from_solver.py",
  "/repo/sim/island_charging_cosim.py":       "../sim/island_charging_cosim.py",
  "/repo/reference/commutator_real_core.py":  "../reference/commutator_real_core.py",
  "/repo/reference/doubler_resonant_core.py": "../reference/doubler_resonant_core.py",
  "/repo/presets/G3-geometry-v010.json":      "../presets/G3-geometry-v010.json",
};
const RT0_Z = 1.3254745;
let py = null, ready = false, okGate = false, BASE = self.location.href;
function post(o){ self.postMessage(o); }

const BRIDGE = `
import sys, json, time
sys.path[:0] = ['/repo/sim', '/repo', '/repo/reference']
import pump_engine as _pe
import pump_sizing as _ps
import pump_synth as _syn
import stack_sizing as _st
import diode_machine as _dm
import js as _js
def _call(fn, payload, rid):
    a = json.loads(payload)
    def log(m):
        _js.postMessage(_js.JSON.parse(json.dumps(dict(type="progress", id=rid, msg=m))))
    if fn == "evaluate":
        t = time.time()
        r = _dm.evaluate(a.get("geometry", "tube"), plates=a.get("plates") or {}, choices=a.get("choices") or {},
                         cem=a.get("cem") or {}, motor=a.get("motor") or {}, log=log)
        r["time_s"] = time.time() - t
        return json.dumps(r, default=float)
    raise KeyError(fn)

def _boot():
    can = _pe.canaries()
    t = time.time()
    anchor = _st.evaluate("disc", topology="record", ledger=False)["result"]
    gate = dict(id="ANCHOR", check="default disc, record topology = RT0 headline", expected=${RT0_Z}, got=anchor["z"],
                tol="1e-6", pass_=bool(anchor["converged"] and abs(anchor["z"] - ${RT0_Z}) < 1e-6), time_s=time.time() - t)
    ok = bool(can["pass_"] and _pe.SELFTEST["pass_"] and _ps.SELFTEST_OK and _syn.SELFTEST_OK and _st.SELFTEST_OK and _dm.SELFTEST_OK and gate["pass_"])
    return json.dumps(dict(canaries=can, gate=gate, ok=ok, stack_selftest=bool(_st.SELFTEST_OK),
                           tube_defaults=_st.TUBE_DEFAULTS, disc_defaults=_ps.PLATE_DEFAULTS,
                           cem_defaults=_dm.CEM_DEFAULTS, motor_defaults=_dm.MOTOR_DEFAULTS,
                           choice_defaults={k: v for k, v in _ps.CHOICE_DEFAULTS.items() if k != "pins"},
                           engine_version=_pe.ENGINE_VERSION), default=float)
`;

async function init(m){
  try {
    const base = m.pyodide || PYODIDE_CDN;
    post({type:"boot", msg:"booting Pyodide…"});
    importScripts(base + "pyodide.js");
    py = await loadPyodide({ indexURL: base });
    post({type:"boot", msg:"loading numpy…"});
    await py.loadPackage("numpy");
    post({type:"boot", msg:"fetching the repo files…"});
    for (const d of ["/repo/sim", "/repo/reference", "/repo/spice", "/repo/presets"]) py.FS.mkdirTree(d);
    for (const [dst, src] of Object.entries(REPO_FILES)){
      const r = await fetch(new URL(src, BASE));
      if (!r.ok) throw new Error("fetch " + src + " → " + r.status + " (serve from the repo root over http)");
      py.FS.writeFile(dst, await r.text());
    }
    post({type:"boot", msg:"importing (on-load self-tests)…"});
    await py.runPythonAsync(BRIDGE);
    post({type:"boot", msg:"running the K1–K4 canaries and the disc anchor gate…"});
    const result = JSON.parse(await py.runPythonAsync(`_boot()`));
    okGate = !!result.ok; ready = true;
    post({type:"ready", result});
  } catch (e){
    post({type:"down", error: String(e && e.message || e)});
  }
}

async function call(msg){
  if (!ready){ post({type:"error", id: msg.id, error:"engine not ready"}); return; }
  if (!okGate){ post({type:"error", id: msg.id, error:"CANARY-FAIL: the engine refuses to evaluate"}); return; }
  try {
    const t0 = performance.now();
    py.globals.set("_payload", JSON.stringify(msg.args || {}));
    py.globals.set("_rid", msg.id); py.globals.set("_fn", msg.fn);
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
