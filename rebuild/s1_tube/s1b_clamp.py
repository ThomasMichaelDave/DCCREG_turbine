"""rebuild/s1_tube/s1b_clamp.py -- Stage S1b: the zener (avalanche) clamp on the S1 core.

The designer (2026-10-16): "For now we are going to deside the zener voltage clamp. Not using it on the physical bench
is just matter of disconnecting it." Then: the clamp level 13.13 kV (the record's V_op = the 6 mm gap's 19.70 kV
breakdown / 1.5), one string per node (Z1 on N1, Z4 on N4, each to REF).

The circuit is S1's (the S0 core at the tube's air values, C_k across N1-N4 and the core electrodes' strays to REF;
rebuild/s1_tube/s1_pulsed_core.py, rebuild/kicad sheet S1 tube) plus the two strings. TOPOLOGY below is its single
source: the deck written here and the KiCad sheet S1b (rebuild/kicad/make_kicad.py) are both checked against it.

The parts, from the record [IR: their classes, not bought parts]:
  - the HV sticks D1-D4: sim/diodes_real.py STICK (as rebuild/s1_tube/s1_bare.py), one per position, leakage classes
    typ 25 nA / max 2 uA / hot 5 uA;
  - each clamp string: 66 avalanche parts of the 200 V class in series (1.5KE200A class), sim/diodes_real.py CLAMP:
    per part a dynamic impedance of 2.5 V / I, 10 ohm bulk, 60 pF at 0 V; BV of the string = 66 x 200 V = 13.2 kV at
    1 mA; leakage typ 10 nA / max 0.5 uA / hot 5 uA [RH, sim/diodes-real-findings.md]; tolerance +-5 % per part and
    +0.1 %/K (sim/parts_first_cut.py Z_TOL, Z_TC).

Runs (ngspice, the stick and clamp models; the varicaps' C(t) cosine in antiphase as S1):
  A  run-up from a 1 kV seed to the clamped steady state, nominal strings, typical leakage: the node peaks, the margin
     to 19.70 kV, each string's current, charge, power (and per part), the sticks' reverse peaks, the core's
     reversing difference V1 - V4;
  B  the strings' spread: both at -5 % / +5 %, mismatched (Z1 +5 %, Z4 -5 %), hot (+25 K: +2.5 %);
  C  the self-start threshold with the strings' leakage in the circuit (the record's flagged side effect), by
     leakage class of the sticks and the strings;
  D  the ideal reference: the clamp as an ideal limit at 13.13 kV is s1_multiplier_tap.py's case B0 (cited).

Writes rebuild/s1_tube/s1b_clamp_results.json and the representative deck s1b_clamp.cir.
Usage: python3 rebuild/s1_tube/s1b_clamp.py [--procs 4]
"""
import json
import math
import os
import subprocess
import sys
import tempfile
from multiprocessing import Pool

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "rebuild", "s0_base"))
sys.path.insert(0, HERE)
from s0_base import TOPOLOGY as S0  # noqa: E402  the frozen S0 topology
import s1_bare as sb  # noqa: E402  the stick model, the leakage classes, the air values (--case air)

V = sb.CASES["air"]["V"]
V_BD = sb.CASES["air"]["V_BD"]                  # 19.70 kV, the 6 mm gap's breakdown
V_CLAMP = V_BD / 1.5                            # 13.13 kV, the designer's level
C_K, C_RREF = 1.1e-12, 5.1e-12                  # F, the record's ring strays (sim/hub-rings-build-findings.md)
Z = dict(n=66, v_dev=200.0, nbv_vt_dev=2.5, rs_dev=10.0, cj0_dev=60e-12, m=0.4, vj_dev=0.7,
         leak=dict(typ=10e-9, max=0.5e-6, hot=5e-6), tol=0.05, tc=0.001)
STEPS = 2000
VT = sb.VT

TOPOLOGY = dict(
    name="S1b: the S1 core with the zener clamp, one string per node",
    capacitors={**{k: dict(v) for k, v in S0["capacitors"].items()},
                "Ck": dict(nodes=("1", "4"), kind="fixed", role="the core's electrode pair (N1 top, N4 bottom)"),
                "Cr1": dict(nodes=("1", "0"), kind="fixed", role="the top core electrode's stray to REF"),
                "Cr4": dict(nodes=("4", "0"), kind="fixed", role="the bottom core electrode's stray to REF")},
    diodes=dict(S0["diodes"]),                                      # (anode, cathode)
    clamps={"Z1": ("0", "1"), "Z4": ("0", "4")},                   # (anode, cathode): avalanche when the node rises
)
VALUES = dict(V, Ck=C_K, Cr1=C_RREF, Cr4=C_RREF)


def clamp_model(name, scale=1.0):
    """the string as one diode [IR, sim/diodes_real.py clamp_params]: BV at 1 mA, NBV from 2.5 V / I per part."""
    n = Z["n"]
    bv = n * Z["v_dev"] * scale
    nbv = n * Z["nbv_vt_dev"] / VT
    c0 = Z["cj0_dev"] / n
    c_ref = c0 / (1 + 1000.0 / (n * Z["vj_dev"])) ** Z["m"]
    cjo = c_ref * (1 + 1000.0 / 0.7) ** Z["m"]
    return (f".model {name} D(is=1e-12 n={n} rs=0 cjo={cjo:.6g} m={Z['m']:g} vj=0.7 bv={bv:.8g} ibv=1e-3 "
            f"nbv={nbv:.8g})"), n * Z["rs_dev"], bv


def deck(seed, n_cyc, leak_stick="typ", leak_clamp="typ", zscale=(1.0, 1.0)):
    w = 2 * math.pi * V["F"]
    sw = {"C1": f"(0.5*(1+cos({w:.8e}*time)))", "C2": f"(0.5*(1-cos({w:.8e}*time)))"}
    t = [f"* {TOPOLOGY['name']} -- rebuild/s1_tube/s1b_clamp.py (generated from TOPOLOGY)"]
    for k, c in TOPOLOGY["capacitors"].items():
        a, b = c["nodes"]
        if c["kind"] == "variable":
            t.append(f"{k}v {a} {b} Q='({V['Cmin']:.4e}+{V['Cmax'] - V['Cmin']:.4e}*{sw[k]})*V({a})'")
        else:
            t.append(f"{k} {a} {b} {VALUES[k]:.4e}")
    ic = {"1": seed, "4": seed, "2": 0.0, "3": 0.0}
    probes = []
    mline, rs = sb.stick_model("DS")
    t += [mline, f".model DL D(is={sb.LEAK[leak_stick]:.6g} n={sb.V_LEAK / VT:.8g} rs=0 cjo=0)",
          f".model ZL D(is={Z['leak'][leak_clamp]:.6g} n={sb.V_LEAK / VT:.8g} rs=0 cjo=0)"]
    for k, (a, cth) in TOPOLOGY["diodes"].items():
        j = f"{k.lower()}j"
        t += [f"Vam{k} {a} {k.lower()}a 0", f"R{k} {k.lower()}a {j} {rs:.6g}", f"{k} {j} {cth} DS",
              f"{k}L {k.lower()}a {cth} DL"]
        ic[j] = ic[f"{k.lower()}a"] = ic.get(a, 0.0)
        probes.append(f"i(Vam{k})")
    for (k, (a, cth)), sc in zip(TOPOLOGY["clamps"].items(), zscale):
        zl, zr, _ = clamp_model(f"MZ{k}", sc)
        j = f"{k.lower()}j"
        # SPICE reads a "Z" element as a MESFET: the strings' diodes are named D<ref> [OC: SPICE element letters]
        t += [zl, f"Vam{k} {a} {k.lower()}a 0", f"R{k} {k.lower()}a {j} {zr:.6g}", f"D{k} {j} {cth} MZ{k}",
              f"D{k}L {k.lower()}a {cth} ZL"]
        ic[j] = ic[f"{k.lower()}a"] = 0.0
        probes.append(f"i(Vam{k})")
    ms = 1.0 / V["F"] / STEPS
    t += [".ic " + " ".join(f"v({n})={x:.6g}" for n, x in ic.items() if n != "0"), ".control",
          f"tran {ms:.4e} {n_cyc / V['F']:.6e} uic",
          "wrdata out.dat v(1) v(2) v(3) v(4) " + " ".join(probes), ".endc",
          f".options reltol=1e-5 abstol=1e-14 vntol=1e-6 maxstep={ms:.4e} method=gear itl4=200", ".end"]
    return "\n".join(t) + "\n"


def simulate(job):
    tag, kw, n_cyc = job
    txt = deck(n_cyc=n_cyc, **kw)
    with tempfile.TemporaryDirectory() as d:
        open(os.path.join(d, "x.cir"), "w").write(txt)
        r = subprocess.run(["ngspice", "-b", "x.cir"], capture_output=True, text=True, timeout=3600, cwd=d)
        f = os.path.join(d, "out.dat")
        if not os.path.exists(f):
            return tag, dict(error=(r.stdout + r.stderr).strip().splitlines()[-4:])
        raw = np.loadtxt(f)
    tt = raw[:, 0]
    cols = raw[:, 1::2]
    Vn, I = cols[:, :4], cols[:, 4:]                     # I: D1-D4, then Z1, Z4 (ammeter at the anode, + = forward)
    cyc = np.floor(tt * V["F"] + 1e-9).astype(int)
    rows = []
    for k in range(n_cyc):
        m = cyc == k
        if m.sum() < 10:
            continue
        dt = np.gradient(tt[m])
        v1, v2, v3, v4 = Vn[m].T
        nodes = {"0": np.zeros(m.sum()), "1": v1, "2": v2, "3": v3, "4": v4}
        rev = {kk: float((nodes[c] - nodes[a]).max()) for kk, (a, c) in TOPOLOGY["diodes"].items()}
        row = dict(k=k, V1=float(v1.max()), V4=float(v4.max()), V2=float(v2.max()), V3=float(v3.max()),
                   Vmin=float(Vn[m].min()), diff_max=float((v1 - v4).max()), diff_min=float((v1 - v4).min()),
                   stick_rev_kV={kk: x / 1e3 for kk, x in rev.items()})
        for j, (kk, (a, c)) in enumerate(TOPOLOGY["clamps"].items()):
            iz = -I[m, 4 + j]                                    # avalanche current (cathode -> anode), A
            vz = nodes[c] - nodes[a]
            row[kk] = dict(Q_nC=float((np.maximum(iz, 0) * dt).sum() * 1e9),
                           E_mJ=float((np.maximum(iz, 0) * vz * dt).sum() * 1e3), I_pk_mA=float(iz.max() * 1e3))
        rows.append(row)
    return tag, dict(rows=rows)


def steady(res, last=8):
    """the clamped steady state: the mean over the last cycles [IR: settled when the peaks stop moving]."""
    R = res["rows"][-last:]
    mean = lambda f: float(np.mean([f(r) for r in R]))          # noqa: E731
    out = dict(V1_kV=mean(lambda r: r["V1"]) / 1e3, V4_kV=mean(lambda r: r["V4"]) / 1e3,
               V2_kV=mean(lambda r: r["V2"]) / 1e3, V3_kV=mean(lambda r: r["V3"]) / 1e3,
               settled=abs(R[-1]["V1"] / R[0]["V1"] - 1) < 2e-3,
               diff_kV=[mean(lambda r: r["diff_min"]) / 1e3, mean(lambda r: r["diff_max"]) / 1e3],
               stick_rev_kV={k: mean(lambda r, k=k: r["stick_rev_kV"][k]) for k in TOPOLOGY["diodes"]})
    out["margin_to_breakdown"] = V_BD / 1e3 / max(out["V1_kV"], out["V4_kV"])
    for k in TOPOLOGY["clamps"]:
        e = mean(lambda r, k=k: r[k]["E_mJ"])
        out[k] = dict(Q_nC=mean(lambda r, k=k: r[k]["Q_nC"]), E_mJ_per_cycle=e, P_W=e * 1e-3 * V["F"],
                      P_per_part_W=e * 1e-3 * V["F"] / Z["n"], I_pk_mA=mean(lambda r, k=k: r[k]["I_pk_mA"]))
    out["P_total_W"] = sum(out[k]["P_W"] for k in TOPOLOGY["clamps"])
    return out


def grows(res):
    pk = [r["V1"] for r in res["rows"]]
    return pk[-1] > 1.5 * pk[1]


def threshold(pool, ls, lc, lo=1.0, hi=3e3, iters=8, n_cyc=24):
    """the smallest seed on N1 / N4 that grows [IR: 24 cycles decide; 3 kV is under the clamp]."""
    run = lambda s: pool.apply(simulate, ((s, dict(seed=s, leak_stick=ls, leak_clamp=lc), n_cyc),))[1]  # noqa: E731
    if not grows(run(hi)):
        return dict(threshold_V=None, note=f"no growth even from {hi:g} V")
    if grows(run(lo)):
        return dict(threshold_V=f"<= {lo:g}")
    for _ in range(iters):
        mid = math.sqrt(lo * hi)
        lo, hi = (lo, mid) if grows(run(mid)) else (mid, hi)
    return dict(threshold_V=[lo, hi])


def main():
    procs = int(sys.argv[sys.argv.index("--procs") + 1]) if "--procs" in sys.argv else 4
    open(os.path.join(HERE, "s1b_clamp.cir"), "w", newline="\n").write(deck(1000.0, 60))
    out = dict(inputs=dict(values=VALUES, V_breakdown_V=V_BD, V_clamp_target_V=V_CLAMP, clamp=Z,
                           clamp_BV_nominal_V=clamp_model("x")[2], stick=sb.STICK, stick_leak_A=sb.LEAK,
                           topology=TOPOLOGY, steps_per_cycle=STEPS,
                           sources=dict(values="rebuild/s1_tube/s1_bare.py (air); C_k / strays "
                                               "sim/hub-rings-build-findings.md", stick="sim/diodes_real.py STICK, LEAK",
                                        clamp="sim/diodes_real.py CLAMP; sim/parts_first_cut.py Z_TOL, Z_TC; leakage "
                                              "sim/diodes-real-findings.md",
                                        level="the designer, 2026-10-16: 13.13 kV, one string per node")))
    N = 60
    jobs = [("A_nominal", dict(seed=1000.0), N),
            ("B_low_-5pc", dict(seed=3000.0, zscale=(0.95, 0.95)), N),
            ("B_high_+5pc", dict(seed=3000.0, zscale=(1.05, 1.05)), N),
            ("B_mismatch_Z1+5_Z4-5", dict(seed=3000.0, zscale=(1.05, 0.95)), N),
            ("B_hot_+25K", dict(seed=3000.0, zscale=(1.025, 1.025)), N)]
    with Pool(procs) as pool:
        res = dict(pool.map(simulate, jobs))
        for tag, r in res.items():
            if "error" in r:
                print(tag, "ERROR", r["error"]); out[tag] = r; continue
            s = steady(r)
            out[tag] = dict(steady=s, history_V1_kV=[x["V1"] / 1e3 for x in r["rows"]])
            print(f"{tag:22s} V1 {s['V1_kV']:.3f} V4 {s['V4_kV']:.3f} kV (settled {s['settled']}), margin "
                  f"x{s['margin_to_breakdown']:.3f}; Z1 {s['Z1']['P_W']:.3f} W ({s['Z1']['P_per_part_W']*1e3:.1f} mW/part, "
                  f"{s['Z1']['I_pk_mA']:.2f} mA pk), Z4 {s['Z4']['P_W']:.3f} W; diff {s['diff_kV'][0]:+.2f}..{s['diff_kV'][1]:+.2f} kV; "
                  f"sticks rev {', '.join(f'{k} {x:.2f}' for k, x in s['stick_rev_kV'].items())} kV")
        out["C_self_start"] = {}
        for ls, lc in (("typ", "typ"), ("typ", "max"), ("typ", "hot"), ("max", "max"), ("hot", "hot")):
            key = f"sticks_{ls}_clamps_{lc}"
            out["C_self_start"][key] = threshold(pool, ls, lc)
            print("C", key, out["C_self_start"][key])
    tap = json.load(open(os.path.join(HERE, "s1_multiplier_tap_results.json")))
    b0 = [r for r in tap["rows"] if r["name"].startswith("B0")][0]
    out["D_ideal_reference"] = dict(source="rebuild/s1_tube/s1_multiplier_tap_results.json B0 (ideal limit, no C_k)",
                                    P_W_at_13p13kV=b0["at_varicap_13p13kV"]["P_buf_W"])
    print("D ideal limit at 13.13 kV (B0):", out["D_ideal_reference"]["P_W_at_13p13kV"], "W")
    json.dump(out, open(os.path.join(HERE, "s1b_clamp_results.json"), "w"), indent=1, default=float)


if __name__ == "__main__":
    main()
