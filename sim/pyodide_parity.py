#!/usr/bin/env python3
"""
sim/pyodide_parity.py — the standing Pyodide-numpy parity guard.
================================================================
The live cores are validated on the CLI numpy (2.x) but RUN in-browser on Pyodide's numpy (1.26).
The numpy-2.0 rename (trapz<->trapezoid, and the removed legacy names) means a name that works on one
side crashes on the other. This script runs EVERY HTML-loaded live core's self-test + the DUAL CANARY
path, so the next version-fragile name is caught HERE (locally) -- not by a user staring at
`SOLVER: down`. Run it under BOTH the CLI numpy AND the numpy-1.26 parity venv; both must be green.

  make pyodide-parity      # runs this under .pyodide-parity (numpy 1.26) AND the CLI numpy

This file itself uses only version-agnostic numpy. [numpy-pyodide-compat] [ME]
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
for p in (ROOT, os.path.join(ROOT, "reference"), HERE):
    sys.path.insert(0, p)

import numpy as np


def main():
    nv = np.__version__
    print(f"PYODIDE-PARITY GUARD  (numpy {nv}; trapz={hasattr(np,'trapezoid') and 'trapezoid' or 'trapz'})")
    print("=" * 72)
    results = []

    def check(name, fn):
        try:
            ok = fn()
            results.append((name, bool(ok)))
            print(f"  [{'PASS' if ok else 'FAIL'}] {name}")
        except Exception as e:
            results.append((name, False))
            print(f"  [FAIL] {name}  -> {type(e).__name__}: {e}")

    # --- 1. every HTML-loaded live core imports + self-tests (catches import-time numpy crashes) ---
    import doubler_core as dc
    check("doubler_core.run_self_test (4 anchors)", lambda: dc.run_self_test())
    import island_resonant_core as irc
    check("island_resonant_core.integrate (the LC ring)",
          lambda: irc.integrate(471e-12, 2640e-9, 5e3, 1e-3, 2.0)["resid"] < 1e-3)
    import doubler_resonant_core as drc
    check("doubler_resonant_core.run_self_test", lambda: drc.run_self_test())
    import commutator_real_core as crc
    check("commutator_real_core.run_self_test (exercises _trapz in fe_arc_budget)",
          lambda: crc.run_self_test())
    # the EXACT trapezoid path that broke the browser load:
    check("commutator_real_core.fe_arc_budget (_trapz live)",
          lambda: crc.fe_arc_budget(0.709, 0.807, 20e3 / 15e3)["E_FE"] >= 0)
    import energy_balance_from_solver as eb
    check("energy_balance_from_solver.selftests", lambda: all(ok for _, ok, _ in eb.selftests()))
    check("energy_balance.tau_profile (_trapz live)",
          lambda: abs(eb.tau_profile(16, 280, 309, 309, 20,
                      [-1.0, 0.0, 0.0, -1.0])["mean"]) >= 0)
    import shuttle_core as sc
    check("shuttle_core import (frozen anchor)", lambda: hasattr(sc, "galvanic_z"))
    import island_charging_cosim as ic
    check("island_charging_cosim import", lambda: True)

    # --- 2. the DUAL CANARY path (what the HTML asserts on load) ---
    import design_synth as ds
    r = ds.evaluate_design(ds.established_anchor())
    op_eta = r["operating"]["eta_real"]
    reg_z = r["regression"]["z_direct"]
    reg_eta = r["regression"]["eta_direct"]
    check(f"dual canary: operating eta {op_eta:.4f} in (0.44, 0.55)",
          lambda: 0.44 < op_eta < 0.55)
    check(f"dual canary: regression z {reg_z:.4f} == 1.334",
          lambda: abs(reg_z - 1.334) < 5e-3)
    check(f"dual canary: regression eta {reg_eta:.4f} == 0.386",
          lambda: abs(reg_eta - 0.386) < 5e-3)
    check(f"dual canary: feasible + all {len(r['invariants'])} invariants pass",
          lambda: r["feasible"] and all(v["pass"] for v in r["invariants"].values()))

    allok = all(ok for _, ok in results)
    print("=" * 72)
    print(f"RESULT under numpy {nv}: {'ALL GREEN' if allok else 'FAILURES PRESENT'} "
          f"({sum(ok for _, ok in results)}/{len(results)})")
    return 0 if allok else 1


if __name__ == "__main__":
    sys.exit(main())
