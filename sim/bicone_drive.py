"""sim/bicone_drive.py -- the bicone (split L_R, one 32-turn cone per side) driven by the electrostatic diode doubler.
ngspice, tube core at 600 rpm relative (rotor and stator geared 1 : -1 at 300 rpm each -> 60 pump cycles per second).

Placement: each cone half in series with its varicap on the ROTOR side: rotor vane set R-A -> cone A -> shaft reference,
R-B -> cone B -> shaft reference. The hub is on the rotor, so no rotating contact is needed [IR].
Cones: L_TC 89.5 uH each (32 turns), cone-cone mutual +25.8 uH (k 0.288, aiding), R 0.05 ohm each [RH].

Two limiters at nodes 1 and 4:
- DIODES ONLY: the avalanche-diode clamp (BV 20 kV) of sim/switchless_cem.py; the cones carry C1 / C2's own current.
- DUMP: a spark gap from node 1 (node 4) to reference, striking at 20 kV, in series with a diode so that it quenches at the
  first current zero [IR]; the dump rings C1 (C2) through its cone. Gap: ngspice SW (on above 20 kV across it, off below
  1 kV), r_on 1 ohm.
Every power term is integrated by ngspice.

Usage: python3 sim/bicone_drive.py   (writes sim/bicone_drive_results.json)
"""
import json
import math
import os
import subprocess
import tempfile

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
F = 60.0
CMIN, CMAX, CA, CPAR = 71.1155e-12, 1113.358e-12, 1224.694e-12, 20e-12
# CPAR 20 pF is [RH]: for the record's air stack the tube's strays solve to 66 pF on nodes 1 / 4 and 25 pF on 2 / 3
# (sim/tube-strays-findings.md §3, 2026-10-09); the decks keep 20 pF as the record's basis
L_CONE, M_CONE, R_CONE, N_CONE = 89.5e-6, 25.8e-6, 0.05, 32
V_OP = 20e3


def deck(mode, n_cyc=24, steps=20000, ron=1.0, reltol=None):
    reltol = (1e-3 if mode == "dump" else 1e-5) if reltol is None else reltol   # the strike stalls the solver at 1e-5
    w = 2 * math.pi * F
    s1 = f"(0.5*(1+cos({w:.8e}*time)))"
    s2 = f"(0.5*(1-cos({w:.8e}*time)))"
    k = M_CONE / L_CONE
    t = [f"* bicone drive: {mode}",
         f"C1v 1 ra Q='({CMIN:.6e}+{CMAX - CMIN:.6e}*{s1})*V(1,ra)'",
         f"C2v 4 rb Q='({CMIN:.6e}+{CMAX - CMIN:.6e}*{s2})*V(4,rb)'",
         f"Lca ra ca {L_CONE:.6e}", f"Rca ca 0 {R_CONE}", f"Lcb rb cb {L_CONE:.6e}", f"Rcb cb 0 {R_CONE}",
         f"Kc Lca Lcb {k:.4f}",
         "Vma ca2 0 0", "Vmb cb2 0 0",
         f"Ca 1 2 {CA:.6e}", f"Cb 3 4 {CA:.6e}"]
    t = [x.replace("Rca ca 0", "Rca ca ca2").replace("Rcb cb 0", "Rcb cb cb2") for x in t]
    t += [f"Cp{n} {n} 0 {CPAR:.3e}" for n in ("1", "2", "3", "4", "ra", "rb")]     # ra / rb: rotor rail stray [RH]
    t += [".model ND D(is=1e-9 n=0.005 rs=1e-3 cjo=0)", "Dd1 2 0 ND", "Dd2 3 0 ND", "Dd3 1 3 ND", "Dd4 4 2 ND"]
    P = {"belt": f"{(CMAX - CMIN) * 0.5 * w:.6e}*sin({w:.8e}*time)*0.5*(V(1,ra)*V(1,ra)-V(4,rb)*V(4,rb))",
         "cone": f"{R_CONE}*(i(Vma)*i(Vma)+i(Vmb)*i(Vmb))"}
    if mode == "diodes":
        t += [f".model DZ D(is=1e-14 n=1 bv={V_OP:.0f} ibv=1e-6 nbv=1 rs=1e5 cjo=0)",
              "Vz1 0 z1 0", "Dz1 1 z1 DZ", "Vz4 0 z4 0", "Dz4 4 z4 DZ"]
        P["limit"] = "-V(1)*i(Vz1)-V(4)*i(Vz4)"
    else:
        vt, vh = (V_OP + 1e3) / 2, (V_OP - 1e3) / 2
        t += [f".model GAP SW(vt={vt:.0f} vh={vh:.0f} ron={ron} roff=1e13)",
              ".model DQ D(is=1e-9 n=0.005 rs=1e-3 cjo=0)",
              # reference -> gap -> quench diode -> node: current flows from ref into the negative node
              "Vg1 0 g1 0", "S1 g1 h1 0 1 GAP OFF", "Dq1 h1 1 DQ",
              "Vg4 0 g4 0", "S4 g4 h4 0 4 GAP OFF", "Dq4 h4 4 DQ"]
        P["limit"] = "-V(1)*i(Vg1)-V(4)*i(Vg4)"
    for nd, ex in P.items():
        t += [f"Bp_{nd} 0 e_{nd} I='{ex}'", f"Cp_{nd} e_{nd} 0 1", f"Rp_{nd} e_{nd} 0 1e18"]
    ics = {"1": -1000.0, "4": -1000.0, "2": 0.0, "3": 0.0, "ra": 0.0, "rb": 0.0}
    ics.update({f"e_{nd}": 0.0 for nd in P})
    if mode == "dump":
        ics.update(h1=-1000.0, h4=-1000.0, g1=0.0, g4=0.0)           # the open gap's inner node sits at the node
    ms = 1.0 / F / steps
    vecs = ["v(1)", "v(4)", "i(Vma)", "i(Vmb)"] + [f"v(e_{nd})" for nd in P]
    t += [".ic" + "".join(f" v({n})={v:g}" for n, v in ics.items()), ".control",
          f"tran {ms:.4e} {n_cyc / F:.6e} uic", "wrdata out.dat " + " ".join(vecs), ".endc",
          f".options reltol={reltol:g} abstol=1e-12 vntol=1e-6 gmin=1e-15 maxstep={ms:.4e} method=gear", ".end"]
    return "\n".join(t) + "\n", vecs, list(P)


def run(mode, **kw):
    txt, vecs, pk = deck(mode, **kw)
    with tempfile.TemporaryDirectory() as d:
        open(os.path.join(d, "x.cir"), "w").write(txt)
        r = subprocess.run(["ngspice", "-b", "x.cir"], capture_output=True, text=True, timeout=3600, cwd=d)
        try:
            raw = np.loadtxt(os.path.join(d, "out.dat"))
        except (OSError, ValueError):
            return dict(mode=mode, error=(r.stdout + r.stderr)[-300:])
    t = raw[:, 0]
    c = {v: raw[:, 2 * j + 1] for j, v in enumerate(vecs)}
    n_cyc = kw.get("n_cyc", 24)
    T = 1 / F
    out = dict(mode=mode, **kw, t_end=float(t[-1]), done=bool(t[-1] >= 0.99 * n_cyc * T))
    if not out["done"]:
        return out
    t0, t1 = (n_cyc - 8) * T, t[-1]
    sel = t >= t0
    for nd in pk:
        y = c[f"v(e_{nd})"]
        out[f"P_{nd}_W"] = float((np.interp(t1, t, y) - np.interp(t0, t, y)) / (t1 - t0))
    ia, ib = c["i(Vma)"][sel], c["i(Vmb)"][sel]
    out.update(V1_peak_kV=float(np.abs(c["v(1)"][sel]).max() / 1e3), I_cone_pk_A=float(max(np.abs(ia).max(), np.abs(ib).max())),
               I_cone_rms_mA=float(np.sqrt(np.mean(ia ** 2)) * 1e3), AT_pk=float(N_CONE * max(np.abs(ia).max(), np.abs(ib).max())))
    if mode == "dump":
        # count dumps: cone A current above 1 A, separated by > 1 ms
        ts = t[sel]; big = np.abs(ia) > 1.0
        starts = [ts[i] for i in range(1, len(ts)) if big[i] and not big[i - 1]]
        ev = [s for k_, s in enumerate(starts) if k_ == 0 or s - starts[k_ - 1] > 1e-3]
        out["dumps_per_s_A"] = len(ev) / (t1 - t0)
        out["E_per_dump_mJ"] = out["P_limit_W"] / max(1e-9, 2 * out["dumps_per_s_A"]) * 1e3
        # ring frequency and the analytic peak at the dump (C1 near its minimum)
        out["f_ring_analytic_MHz"] = 1 / (2 * math.pi * math.sqrt(L_CONE * (CMIN + CPAR))) / 1e6
        out["I_pk_analytic_A"] = V_OP / math.sqrt(L_CONE / (CMIN + CPAR))
    out["P_other_W"] = out["P_belt_W"] - out["P_cone_W"] - out["P_limit_W"]
    return out


def main():
    rows = []
    for mode, kw in (("diodes", {}), ("dump", {}), ("dump", dict(steps=80000)), ("dump", dict(reltol=3e-4))):
        r = run(mode, **kw)
        rows.append(r)
        print(json.dumps(r, default=float)[:900], flush=True)
    json.dump(dict(F=F, rows=rows), open(os.path.join(HERE, "bicone_drive_results.json"), "w"), indent=1, default=float)


if __name__ == "__main__":
    main()
