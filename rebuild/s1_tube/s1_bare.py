"""rebuild/s1_tube/s1_bare.py -- Stage 1: the bare S0 core (de Queiroz Fig. 1, positive) at the tube's values.

The question (rebuild/README.md, the rule of addition): what limits the bare core's voltage, and so does anything
have to be added? Nothing from the earlier design is added here; the clamps, the rings' supply and the strays are
absent on purpose.

Inputs, provisional until the S2 models re-solve them [IR: taken from the evidence, not re-derived]:
  - C1, C2: 128.4-450.6 pF, the vane stack of record solved in 3-D with its rims (sim/tube-strays-findings.md §4,
    sim/tube_strays_results.json);
  - Ca = Cb: 495 pF, the sixth gap (DECIDED 2026-10-14; ledger §6 item 55);
  - 120 Hz: the pumps' rate at 1200 rpm relative (ledger §1, sim/pole-design-findings.md §6);
  - the 6 mm gap's breakdown: 1.5 x V_op = 19.70 kV (sim/air_stack_sizing_results.json thick_vanes/chosen; the
    record's V_op = breakdown / 1.5 [RH]).
  - the real diode: the repo's HV stick, 20 kV V_RRM, avalanche at 24 kV, leakage typ 25 nA / max 2 uA / hot 5 uA
    (sim/diodes_real.py STICK, LEAK, stick_params; datasheet-class [IR]). One stick per position: the bare build.

Parts:
  A. ideal diodes (sim/queiroz_matrix.py's LCP solver): z, the eigenvector, every part's peak voltage over a cycle
     per volt of the node-1 peak (the stress map: under linear growth the largest ratio fails first);
  B. a Ca sweep (z against Ca / C_max) at the tube's C1 / C2;
  C. ngspice, near-ideal diodes: z, the cross-check of A;
  D. ngspice, real sticks: (1) the run-up from a seed with typical leakage -- where does growth stop, and which
     element stops it; (2) the smallest seed that still grows, per leakage class (the self-start question).

Writes rebuild/s1_tube/s1_bare_results.json (air) or s1_bare_vacuum_results.json (--case vacuum).
Usage: python3 rebuild/s1_tube/s1_bare.py [--case air|vacuum]
"""
import json
import math
import os
import subprocess
import sys
import tempfile

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "sim"))
sys.path.insert(0, os.path.join(ROOT, "rebuild", "s0_base"))
import queiroz_matrix as qm  # noqa: E402
from s0_base import TOPOLOGY  # noqa: E402  the frozen S0 topology

TS = json.load(open(os.path.join(ROOT, "sim", "tube_strays_results.json")))
AS = json.load(open(os.path.join(ROOT, "sim", "air_stack_sizing_results.json")))

_BV = AS["base_vacuum"]
CASES = {
    # the air build of record, 3-D solved (the default; s1_bare_results.json)
    "air": dict(V=dict(Cmin=128.4e-12, Cmax=450.6e-12, Ca=495e-12, Cb=495e-12, F=120.0),
                V_BD=1.5 * AS["thick_vanes"]["chosen"]["V_op_kV"] * 1e3,
                src=dict(C1C2="sim/tube-strays-findings.md §4 (3-D, as built)",
                         Ca="ledger §6 item 55, DECIDED 2026-10-14",
                         V_bd="sim/air_stack_sizing_results.json thick_vanes/chosen V_op x 1.5 (the 6 mm air gap)"),
                out="s1_bare_results.json"),
    # the tube as drawn for vacuum (ledger §2 phase 6: 8 + 8 plates, 15 gaps; Ca 1.1 C_max), from the 2-D cell, NOT
    # re-solved in 3-D: the air stack's rims took kappa 7.47 -> 3.51, so this kappa 15.66 is an upper bound [IR]
    "vacuum": dict(V=dict(Cmin=_BV["C_min_pF"] * 1e-12, Cmax=_BV["C_max_pF"] * 1e-12, Ca=_BV["Ca_pF"] * 1e-12,
                          Cb=_BV["Ca_pF"] * 1e-12, F=120.0),
                   V_BD=_BV["V_bd_kV"] * 1e3,
                   src=dict(C1C2="sim/air_stack_sizing_results.json base_vacuum (2-D cell)",
                            Ca="sim/air_stack_sizing_results.json base_vacuum Ca_pF (1.1 C_max)",
                            V_bd="sim/air_stack_sizing_results.json base_vacuum V_bd_kV"),
                   out="s1_bare_vacuum_results.json"),
}
CASE = sys.argv[sys.argv.index("--case") + 1] if "--case" in sys.argv else "air"
V, V_BD = CASES[CASE]["V"], CASES[CASE]["V_BD"]
# the stick (sim/diodes_real.py STICK / LEAK / V_LEAK; copied, not imported: that module loads the record's decks)
STICK = dict(n_j=20, n_per_j=1.8, vf=((1e-3, 17.0), (5e-3, 20.0)), cj0_j=30e-12, m=0.33, vj_j=0.7, tt=100e-9,
             bv=24e3, ibv=10e-6, nbv_j=1.0, V_RRM=20e3)
LEAK = dict(typ=25e-9, max=2e-6, hot=5e-6)
V_LEAK = 250.0
VT = 8.617333262e-5 * 300.15


# ---------------------------------------------------------------------------------------------------------------------
def stress_map(al, be, n=8000):
    """A: the growing mode, then one cycle traced; every part's peak voltage / the node-1 peak [OC: linear growth
    scales every voltage alike]."""
    c = qm.fig1(al, be)
    pi = qm.power_iteration(c, n)
    v = np.array(pi["e_phase1"])
    B = qm.bmat(c["diodes"])
    rec = []
    for fwd in (True, False):
        s_grid = np.linspace(0, 1, n + 1) if fwd else np.linspace(1, 0, n + 1)
        act = ()
        for s0, s1 in zip(s_grid[:-1], s_grid[1:]):
            Q = qm.kmat(c["caps"](s0)) @ v
            v, act = qm.lcp_step(qm.kmat(c["caps"](s1)), Q, B, act)
            rec.append(v.copy())
    R = np.array(rec)
    R = R / pi["z_cycle"] ** np.linspace(0, 1, len(R))[:, None]   # undo the growth within the cycle [OC]
    e1, e2, e3, e4 = R.T
    peaks = {"node 1 (C1, the varicap gap)": e1.max(), "node 4 (C2, the varicap gap)": e4.max(),
             "node 2": e2.max(), "node 3": e3.max(),
             "Ca (1-2)": np.abs(e1 - e2).max(), "Cb (3-4)": np.abs(e3 - e4).max()}
    for k, (a, cth) in TOPOLOGY["diodes"].items():          # reverse voltage = v_cathode - v_anode
        va = np.zeros(len(R)) if a == "0" else R[:, int(a) - 1]
        vc = np.zeros(len(R)) if cth == "0" else R[:, int(cth) - 1]
        peaks[f"{k} reverse"] = (vc - va).max()
    ref = max(e1.max(), e4.max())
    return dict(z_cycle=pi["z_cycle"], e_phase1=pi["e_phase1"], per_node1_peak={k: float(x / ref) for k, x in
                                                                                 peaks.items()},
                min_node=float(R.min() / ref))


def ca_sweep(al, ratios=(0.3, 0.5, 0.7, 0.9, 1.0, 1.1, 1.3, 1.6, 2.0, 3.0, 5.0)):
    out = {}
    for r in ratios:
        out[r] = qm.power_iteration(qm.fig1(al, r * al), 2000, cycles=30)["z_cycle"]
    return out


# ---------------------------------------------------------------------------------------------------------------------
def stick_model(name):
    """sim/diodes_real.py stick_params(1) [IR there]: N fixed by the junctions, Is and Rs fitted to the two forward
    points; the junction law carried as Cjo' / (1 + V / 0.7)^M matching it at 1 kV."""
    S = STICK
    nn = S["n_j"] * S["n_per_j"]
    a = nn * VT
    (i1, v1), (i2, v2) = S["vf"]
    rs = (v2 - v1 - a * math.log(i2 / i1)) / (i2 - i1)
    is_ = i1 / math.exp((v1 - i1 * rs) / a)
    nj = S["n_j"]
    c0 = S["cj0_j"] / nj
    c_ref = c0 / (1 + 1000.0 / (nj * S["vj_j"])) ** S["m"]
    cjo = c_ref * (1 + 1000.0 / 0.7) ** S["m"]
    return (f".model {name} D(is={is_:.6e} n={nn:.6g} rs=0 cjo={cjo:.6g} m={S['m']:g} vj=0.7 tt={S['tt']:.6g} "
            f"bv={S['bv']:.8g} ibv={S['ibv']:g} nbv={S['nbv_j'] * nj:.8g})"), rs


def deck(real, seed, n_cyc, leak="typ", steps=2000):
    w = 2 * math.pi * V["F"]
    sw = {"C1": f"(0.5*(1+cos({w:.8e}*time)))", "C2": f"(0.5*(1-cos({w:.8e}*time)))"}
    t = ["* S1 bare core at the tube's values -- rebuild/s1_tube/s1_bare.py"]
    for k, c in TOPOLOGY["capacitors"].items():
        a, b = c["nodes"]
        if c["kind"] == "variable":
            t.append(f"{k}v {a} {b} Q='({V['Cmin']:.4e}+{V['Cmax'] - V['Cmin']:.4e}*{sw[k]})*V({a})'")
        else:
            t.append(f"{k} {a} {b} {V[k]:.4e}")
    ic = {"1": seed, "4": seed, "2": 0.0, "3": 0.0}
    probes = []
    if real:
        mline, rs = stick_model("DS")
        t += [mline, f".model DL D(is={LEAK[leak]:.6g} n={V_LEAK / VT:.8g} rs=0 cjo=0)"]
        for k, (a, cth) in TOPOLOGY["diodes"].items():
            j = f"{k.lower()}j"
            # ammeter, series resistance to an explicit node, the junction string; the leakage element across [IR]
            t += [f"Vam{k} {a} {k.lower()}a 0", f"R{k} {k.lower()}a {j} {rs:.6g}", f"{k} {j} {cth} DS",
                  f"{k}L {k.lower()}a {cth} DL"]
            ic[j] = ic.get(a, 0.0)
            ic[f"{k.lower()}a"] = ic.get(a, 0.0)
            probes.append(f"i(Vam{k})")
    else:
        t.append(".model ND D(is=1e-12 n=0.005 rs=1e-3 cjo=0)")
        t += [f"{k} {a} {c} ND" for k, (a, c) in TOPOLOGY["diodes"].items()]
    ms = 1.0 / V["F"] / steps
    t += [".ic " + " ".join(f"v({n})={x:.6g}" for n, x in ic.items() if n != "0"), ".control",
          f"tran {ms:.4e} {n_cyc / V['F']:.6e} uic",
          "wrdata out.dat v(1) v(2) v(3) v(4) " + " ".join(probes), ".endc",
          f".options reltol=1e-5 abstol=1e-14 vntol=1e-6 maxstep={ms:.4e} method=gear itl4=200", ".end"]
    return "\n".join(t) + "\n"


def run(txt, n_cyc):
    with tempfile.TemporaryDirectory() as d:
        open(os.path.join(d, "x.cir"), "w").write(txt)
        r = subprocess.run(["ngspice", "-b", "x.cir"], capture_output=True, text=True, timeout=1800, cwd=d)
        f = os.path.join(d, "out.dat")
        if not os.path.exists(f):
            return dict(error=(r.stdout + r.stderr).strip().splitlines()[-4:])
        raw = np.loadtxt(f)
    tt = raw[:, 0]
    cols = raw[:, 1::2]
    Vn = cols[:, :4]
    cyc = np.floor(tt * V["F"] + 1e-9).astype(int)
    out = dict(t_end=float(tt[-1]), cycles=[])
    for k in range(n_cyc):
        m = cyc == k
        if not np.any(m):
            continue
        row = dict(k=k, V1=float(Vn[m, 0].max()), V4=float(Vn[m, 3].max()), V2=float(Vn[m, 1].max()),
                   V3=float(Vn[m, 2].max()), Vmin=float(Vn[m].min()))
        if cols.shape[1] > 4:
            I = cols[m, 4:]
            dt = np.gradient(tt[m])
            # reverse charge per cycle in each position (negative ammeter current = reverse) [OC]
            row["Q_rev_nC"] = [float(-(np.minimum(I[:, j], 0) * dt).sum() * 1e9) for j in range(I.shape[1])]
            row["Q_fwd_nC"] = [float((np.maximum(I[:, j], 0) * dt).sum() * 1e9) for j in range(I.shape[1])]
        out["cycles"].append(row)
    pk = [c["V1"] for c in out["cycles"]]
    out["z_history"] = [pk[i + 1] / pk[i] for i in range(len(pk) - 1) if pk[i] > 0]
    return out


def grows(seed, leak, n_cyc=24):
    r = run(deck(True, seed, n_cyc, leak), n_cyc)
    if "error" in r:
        return None, r
    pk = [c["V1"] for c in r["cycles"]]
    return pk[-1] > 1.5 * pk[1], r          # grows vs decays [IR: from a seed well under the ceiling]


def threshold(leak, lo=1.0, hi=3e3, iters=9):
    """the smallest seed on nodes 1 and 4 that grows, by bisection in log [IR: 24 cycles decide; 3 kV is far under
    the ~30 kV ceiling, so a growing run cannot saturate within them]."""
    g_hi, _ = grows(hi, leak)
    if not g_hi:
        return dict(threshold_V=None, note=f"no growth even from {hi:g} V")
    g_lo, _ = grows(lo, leak)
    if g_lo:
        return dict(threshold_V=f"<= {lo:g}")
    for _ in range(iters):
        mid = math.sqrt(lo * hi)
        g, _ = grows(mid, leak)
        if g is None:
            break
        lo, hi = (lo, mid) if g else (mid, hi)
    return dict(threshold_V=[lo, hi])


# ---------------------------------------------------------------------------------------------------------------------
def main():
    al, be = V["Cmax"] / V["Cmin"], V["Ca"] / V["Cmin"]
    out = dict(inputs=dict(values=V, alpha=al, beta=be, V_breakdown_V=V_BD, stick=STICK, leak_A=LEAK,
                           case=CASE, sources=dict(F="ledger §1", **CASES[CASE]["src"]),
                           more_sources=dict(
                                        stick="sim/diodes_real.py STICK, LEAK")))
    A = stress_map(al, be)
    out["A_ideal_stress"] = A
    print(f"A  ideal z {A['z_cycle']:.5f}/cycle; e_phase1 {np.round(A['e_phase1'], 4).tolist()}")
    for k, x in sorted(A["per_node1_peak"].items(), key=lambda kv: -kv[1]):
        print(f"     {k:30s} {x:.4f} x node-1 peak  -> at the gap's {V_BD / 1e3:.2f} kV on node 1: {x * V_BD / 1e3:.2f} kV")
    B = ca_sweep(al)
    out["B_ca_sweep_z"] = {f"{r:g}": z for r, z in B.items()}
    print("B  z vs Ca/Cmax", {f"{r:g}": round(z, 4) for r, z in B.items()})
    n_c = 20
    C = run(deck(False, 100.0, n_c), n_c)
    out["C_ngspice_ND"] = dict(z_late=float(np.median(C["z_history"][-5:])), z_history=C["z_history"])
    print(f"C  ngspice ND z {out['C_ngspice_ND']['z_late']:.5f}")
    n_d = 70
    D1 = run(deck(True, 1000.0, n_d, "typ"), n_d)
    out["D1_runup_typ"] = D1
    if "error" in D1:
        print("D1 error", D1["error"])
    else:
        last = D1["cycles"][-1]
        print(f"D1 run-up from 1 kV, typ leakage: z early {np.median(D1['z_history'][2:7]):.4f}; last cycle "
              f"V1 {last['V1'] / 1e3:.2f} V4 {last['V4'] / 1e3:.2f} V2 {last['V2'] / 1e3:.2f} V3 {last['V3'] / 1e3:.2f} kV; "
              f"Q_rev nC {np.round(last['Q_rev_nC'], 2).tolist()}")
    out["D2_threshold"] = {}
    for leak in ("typ", "max", "hot"):
        out["D2_threshold"][leak] = threshold(leak)
        print(f"D2 self-start threshold, {leak}: {out['D2_threshold'][leak]}")
    json.dump(out, open(os.path.join(HERE, CASES[CASE]["out"]), "w"), indent=1, default=float)


if __name__ == "__main__":
    main()
