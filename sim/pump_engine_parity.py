#!/usr/bin/env python3
"""
sim/pump_engine_parity.py — gate N: the pump engine under numpy 1.26.4 (Pyodide 0.26.2) and 2.x
================================================================================================
Runs the engine's on-load self-test, the K1-K4 canaries and two reference evaluations, and prints
a JSON line of the numbers. Run it under BOTH interpreters; sim/pump_engine_gates.py (gate N)
compares the two outputs:

  .pyodide-parity/bin/python sim/pump_engine_parity.py      # numpy 1.26.4 (the Pyodide proxy)
  python3 sim/pump_engine_parity.py                         # CLI numpy 2.x

The browser itself is checked by the same calls through Pyodide (tools/pump-calc.worker.js).
Version-agnostic numpy only. [numpy-pyodide-compat pattern] [ME]
"""
import json
import os
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
for p in (HERE, os.path.dirname(HERE), os.path.join(os.path.dirname(HERE), "reference")):
    if p not in sys.path:
        sys.path.insert(0, p)

import numpy as np


def main():
    out = dict(numpy=np.__version__, python=sys.version.split()[0])
    t = time.time()
    import pump_engine as pe
    out["import_s"] = time.time() - t
    out["selftest"] = bool(pe.SELFTEST["pass_"])
    t = time.time()
    c = pe.canaries()
    out["canaries_s"] = time.time() - t
    out["canaries"] = {r["id"]: dict(pass_=r["pass"], got=r["got"]) for r in c["rows"]}
    out["canaries_pass"] = bool(c["pass_"])
    for name, cfg in (("G1", dict(Lx_mH=0.0)), ("R1_valve", {})):
        t = time.time()
        r = pe.evaluate(cfg, twins=False)
        out[name] = dict(z=r["z"], eta_at_cut=r["ledger"]["eta_at_cut"], resid=r["ledger"]["resid"],
                         time_s=time.time() - t)
    ok = out["selftest"] and out["canaries_pass"]
    print(json.dumps(out))
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
