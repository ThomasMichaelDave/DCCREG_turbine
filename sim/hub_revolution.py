"""sim/hub_revolution.py -- the rings' supply of record over one revolution of the rotor: does the field at the null
swing as the pump goes through its phases? (the designer's question, 2026-10-09)

The record's supply (sim/hub_rings_build_results.json record: the symmetric pair, two stages a side, 100 pF storage,
100 GOhm per ring; sim/core_field.py dc with a_ref "shaft") runs in ngspice to its settled state, as the build's stage
runs do (120 + 80 n cycles). It is then recorded over one revolution of the rotor.
- One revolution: the rotor and the counter-rotor turn 600 rpm each way through the 1 : -1 gear (1200 rpm relative),
  so the six vanes pass twelve times in 0.1 s. That is 12 cycles of the pump at 120 Hz, each 30 deg of the rotor.
- The pump's phases: C1(theta) and C2(theta), half a cycle apart; nodes 1 and 4 follow them.
- What is recorded: nodes 1 and 4; ring B's chain (m1, m2 oscillating; b1 and ring B smoothing); ring A's mirror chain
  (n1, n2; a1 and ring A); and the field at the null.
- The field at the null is k (V_B - V_A), as connected, with k the record's bands' field per kV [OC]. That is the hub's
  electrostatic solution. Its insulators relax over minutes (sim/hub_drift.py), so at 120 Hz the field follows the
  rings' potentials; the slow drift is a separate, DC effect.
Usage: python3 sim/hub_revolution.py   (writes sim/hub_revolution_results.json)
"""
import json
import math
import os
import re
import subprocess
import sys
import tempfile
import time

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import core_field as CF            # noqa: E402
import hub_rings_build as B        # noqa: E402

RPM_EACH = 600.0                   # rotor and counter-rotor, each way (1200 rpm relative)
N_REV = 12                         # pump cycles in one revolution of the rotor: 6 vanes x 2 (the 1 : -1 gear)
STEPS = 5000                       # time steps per pump cycle (the build's ripple runs use the same)
N_OUT = 150                        # output points per pump cycle


def main():
    t_run = time.time()
    rec = json.load(open(os.path.join(HERE, "hub_rings_build_results.json")))["record"]
    assert abs(N_REV * RPM_EACH / 60.0 - CF.F) < 1e-9, "12 cycles per revolution at 600 rpm need the pump at 120 Hz"
    n_set = 120 + 80 * max(rec["n_cw"], rec["n_a"])                   # settled, as the build's stage runs
    kw = dict(opt="dc", n_cw=rec["n_cw"], n_cw_a=rec["n_a"], n_cyc=n_set + N_REV, steps=STEPS, c_core=0.1e-9,
              c_cw=0.1e-9, r_leak=B.R_LEAK_EST, **({"a_ref": rec["a_ref"]} if rec.get("a_ref", "dk") != "dk" else {}))
    txt, vecs, _ = CF.deck(**kw)
    T = 1.0 / CF.F
    t0 = n_set * T
    # keep only the revolution's data: ngspice's tran tstart (the settling still runs in full)
    txt, n = re.subn(r"^tran (\S+) (\S+) uic$", lambda m: f"tran {m.group(1)} {m.group(2)} {t0:.6e} uic", txt,
                     flags=re.M)
    assert n == 1
    with tempfile.TemporaryDirectory() as d:
        open(os.path.join(d, "x.cir"), "w").write(txt)
        r = subprocess.run(["ngspice", "-b", "x.cir"], capture_output=True, text=True, cwd=d, timeout=7200)
        raw = np.loadtxt(os.path.join(d, "out.dat"))
    t = raw[:, 0]
    c = {v: raw[:, 2 * j + 1] for j, v in enumerate(vecs)}
    assert t[-1] >= t0 + 0.999 * N_REV * T, (r.stdout + r.stderr)[-400:]
    tu = t0 + np.arange(N_REV * N_OUT) * T / N_OUT
    kv = {v[2:-1]: np.interp(tu, t, c[v]) / 1e3 for v in vecs if v.startswith("v(") and not v.startswith("v(e_")}
    w = 2 * math.pi * CF.F
    dC = CF.CMAX - CF.CMIN
    c1 = (CF.CMIN + dC * 0.5 * (1 + np.cos(w * tu))) * 1e12          # pF, as the deck's C1v / C2v
    c2 = (CF.CMIN + dC * 0.5 * (1 - np.cos(w * tu))) * 1e12
    k = rec["k_kV_cm_per_kV"]
    e = k * (kv["eb"] - kv["ea"])                                      # kV/cm at the null, B to A positive
    ang = (tu - t0) / T * 360.0 / N_REV                                # the rotor's angle over the revolution (deg)

    def st(y):
        return dict(mean=float(y.mean()), min=float(y.min()), max=float(y.max()), pp=float(np.ptp(y)))
    # the top-ups each cycle: ring B's highest and ring A's lowest point
    top = []
    for i in range(N_REV):
        s = slice(i * N_OUT, (i + 1) * N_OUT)
        top.append(dict(cycle=i, B_deg=float(ang[s][np.argmax(kv["eb"][s])]), A_deg=float(ang[s][np.argmin(kv["ea"][s])])))
    out = dict(note="see the module docstring", rpm_each=RPM_EACH, F_Hz=CF.F, n_cycles=N_REV, n_settle=n_set,
               k_kV_cm_per_kV=k, record=dict((q, rec[q]) for q in ("n_a", "n_cw", "a_ref", "theta_p", "theta_e")),
               summary=dict(E_kV_cm=st(e), E_sign_changes=int(np.sum(np.diff(np.sign(e)) != 0)),
                            E_always_B_to_A=bool(e.min() > 0), V_B_kV=st(kv["eb"]), V_A_kV=st(kv["ea"]),
                            V1_kV=st(kv["1"]), V4_kV=st(kv["4"]),
                            chain={nd: st(kv[nd]) for nd in ("m1", "m2", "b1", "n1", "n2", "a1") if nd in kv},
                            C1_pF=st(c1), C2_pF=st(c2)),
               top_ups=top,
               rotor_deg=np.round(ang, 3).tolist(), C1_pF=np.round(c1, 3).tolist(), C2_pF=np.round(c2, 3).tolist(),
               E_kV_cm=np.round(e, 6).tolist(),
               V_kV={nd: np.round(kv[nd], 5).tolist() for nd in ("1", "4", "m1", "m2", "b1", "eb", "n1", "n2", "a1", "ea")
                     if nd in kv},
               run_s=time.time() - t_run)
    json.dump(out, open(os.path.join(HERE, "hub_revolution_results.json"), "w"), indent=1, default=float)
    S = out["summary"]
    print(f"one revolution ({N_REV} pump cycles, {N_REV * T * 1e3:.0f} ms): the field at the null {S['E_kV_cm']['min']:.4f} "
          f"to {S['E_kV_cm']['max']:.4f} kV/cm (mean {S['E_kV_cm']['mean']:.4f}, {S['E_kV_cm']['pp']:.4f} p-p), "
          f"sign changes {S['E_sign_changes']}, always B to A: {S['E_always_B_to_A']}")
    print(f"rings: B {S['V_B_kV']['mean']:+.3f} kV ({1e3 * S['V_B_kV']['pp']:.0f} V p-p), A {S['V_A_kV']['mean']:+.3f} kV "
          f"({1e3 * S['V_A_kV']['pp']:.0f} V p-p); nodes 1 / 4 {S['V1_kV']['min']:.2f} to {S['V1_kV']['max']:.2f} kV")
    for nd, q in S["chain"].items():
        print(f"  {nd}: {q['min']:+.2f} to {q['max']:+.2f} kV ({q['pp']:.2f} p-p)")
    print(f"done in {time.time() - t_run:.0f} s")


if __name__ == "__main__":
    main()
