#!/usr/bin/env python3
"""tools/step-viewer/make_layout_data.py -- the files of the layout viewer (tools/step-viewer/layout.html), in one folder
ready to publish: index.html (layout.html), scene.js, sim.js, sim.json and model.json.

sim.json is drawn from the records, rounded for the page and never edited by hand:
  * the circuit: sim/multiplier_waveforms_results.json (the steady cycle at 360 points: every node's voltage, every
    diode's and clamp's current as 1-degree bin means; the start-up: every node's mean per cycle; the devices' table,
    the rings, the gates);
  * the parts' nets: docs/geometry/tube/<tag>.parts.json (sim/tube_geometry.py --layout), each conductor's net or the
    two nets and the line or arc it grades along.
model.json is the layout's GLB base64-wrapped (sim/step_to_glb.py --angular 0.4 --json); this script writes it too
when it is missing.
Usage: python3 tools/step-viewer/make_layout_data.py OUT_DIR
"""
import json
import os
import shutil
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
TAG = "tube-r150-n6-air6-wound-g0p5-6br-hub50-layout"
NODES = ("1", "2", "r2", "xa", "ea", "l1", "r1", "4", "3", "l2", "xb", "eb", "s")
DEVICES = ("D1", "D3", "D6", "D7", "D9", "D10", "D2", "D4", "D5", "D8", "D11", "D12", "z1", "z4")


def r(x, nd=1):
    return round(float(x), nd)


def build(out_dir):
    os.makedirs(out_dir, exist_ok=True)
    W = json.load(open(os.path.join(ROOT, "sim", "multiplier_waveforms_results.json")))
    P = json.load(open(os.path.join(ROOT, "docs", "geometry", "tube", f"{TAG}.parts.json")))
    L = json.load(open(os.path.join(ROOT, "sim", "multiplier_layout_results.json")))
    cyc, per = W["cycle"], W["per_cycle"]
    nets = {}
    for name, q in P["nets"].items():
        e = {k: v for k, v in q.items() if k != "path"}
        if "axis" in e:
            e["axis"] = [[r(x, 2) for x in p] for p in e["axis"]]
        if "arc" in e:
            e["arc"] = {k: ([r(x, 3) for x in v] if isinstance(v, list) else r(v, 3)) for k, v in e["arc"].items()}
        nets[name] = e
    dev = {}
    for nm in DEVICES:
        d = W["devices"][nm]
        dev[nm] = dict(anode=d["anode"], cathode=d["cathode"], charge_nC=r(d["charge_nC"], 3), I_avg_uA=r(d["I_avg_uA"], 3),
                       I_peak_mA=r(d["I_peak_bin_mA"], 4), conducts_deg=[[r(a, 1), r(b, 1)] for a, b in d["conducts_deg"]],
                       V_reverse_peak_kV=None if d["V_reverse_peak_kV"] is None else r(d["V_reverse_peak_kV"], 2))
    job, rings = W["job"], W["rings"]
    data = dict(
        source="sim/multiplier_waveforms_results.json; docs/geometry/tube/" + TAG + ".parts.json (sim/tube_geometry.py --layout)",
        status="PROPOSED (the layout, 2026-10-11); the circuit DECIDED for now (2026-10-11)",
        model=dict(tag=TAG, L_mm=P["L_mm"], zc_mm=P["zc_mm"], n_parts=len(P["parts"])),
        circuit=dict(f_Hz=120.0, period_ms=1000.0 / 120.0, cycle_rel_deg=60.0, rpm=600, C3_C6_pF=r(job["cl"] * 1e12, 0),
                     clamp_parts=job["n_z"], V_op_kV=r(job["vop"] / 1e3, 3), n_cycles=job["n_cyc"],
                     note="ideal diodes from a 1 kV seed (sim/integrated_multiplier.py's deck); the layout's strays [RH]"),
        rings=dict(V_A_kV=r(rings["V_A_kV"], 3), V_B_kV=r(rings["V_B_kV"], 3), ripple_V=r(rings["ripple_A_V"], 1),
                   E_null_kV_cm=r(rings["E_null_can_kV_cm"], 3), cycles_to_95pc=rings["cycles_to_95pc"]),
        gates={k: bool(v["ok"]) for k, v in W["gates"].items()},
        cycle=dict(theta=[r(x, 3) for x in cyc["theta_rel_deg"]],
                   V={nd: [r(v, 0) for v in cyc["V"][nd]] for nd in NODES},
                   I={nm: [r(i * 1e6, 3) for i in cyc["I"][nm]] for nm in DEVICES},       # uA
                   C1_pF=[r(c, 2) for c in cyc["C1_pF"]]),
        startup=dict(mean={nd: [r(v, 0) for v in per[nd]["mean"]] for nd in NODES},
                     min={nd: [r(v, 0) for v in per[nd]["min"]] for nd in ("1", "4")},
                     max={nd: [r(v, 0) for v in per[nd]["max"]] for nd in ("1", "4")}),
        devices=dev, nets=nets,
        layout=dict(length_mm=L["stack"]["L_mm"], field_ratio_can=r(L["hub"]["k_ratio"], 5)))
    json.dump(data, open(os.path.join(out_dir, "sim.json"), "w"), separators=(",", ":"))
    shutil.copy(os.path.join(HERE, "layout.html"), os.path.join(out_dir, "index.html"))
    for f in ("scene.js", "sim.js"):
        shutil.copy(os.path.join(HERE, f), os.path.join(out_dir, f))
    mj = os.path.join(out_dir, "model.json")
    if not os.path.exists(mj):
        step = os.path.join(ROOT, "docs", "geometry", "tube", f"{TAG}.step")
        subprocess.run([sys.executable, os.path.join(ROOT, "sim", "step_to_glb.py"), step, os.path.join(out_dir, "model.glb"),
                        "--angular", "0.4", "--json", mj], check=True)
        os.remove(os.path.join(out_dir, "model.glb"))
    sizes = {f: os.path.getsize(os.path.join(out_dir, f)) for f in sorted(os.listdir(out_dir))}
    print(json.dumps(sizes))


if __name__ == "__main__":
    build(sys.argv[1])
