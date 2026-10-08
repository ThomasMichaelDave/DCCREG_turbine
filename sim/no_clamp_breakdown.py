"""sim/no_clamp_breakdown.py -- the electrostatic diode doubler WITHOUT the 20 kV clamps: the voltage grows until the
vane gap breaks down. What does each breakdown do, and does the pump recover? Writes sim/no_clamp_breakdown_results.json.

The circuit is sim/bicone_drive.py's (diodes only) with Z1 / Z4 removed, at 1200 rpm relative (120 Hz), and:
- the reference split in two: the counter-rotor's rail (D1, D2 and the counter-rotor nodes' strays) and the shaft (the
  cones, the rotor vanes' strays), joined by a 0 V source = the reference link (a brush, or for now an inner bearing),
  so its current is measured;
- a 0 V source in series with each of D1-D4 (their currents);
- a breakdown across each vane stack (C1: node 1 to R-A, C2: node 4 to R-B): a switch that closes when the node reaches
  V_BD and stays closed while its current exceeds the chopping current I_CHOP (a latch on ngspice SW's hysteresis), in
  series with the arc loop's inductance L_ARC and resistance R_ARC [IR/RH: the arc conducts both ways while it lasts;
  restrikes follow from the same trigger; the arc voltage is modelled as R_ARC only].
Two breakdown voltages: the vacuum design value of the 3 mm gap (sim/stack_sizing.gap_breakdown_kV, 10 kV/mm) and its
air value at 1 atm (uniform field; the vane edges lower it in practice) -- the first tests run in air.
Usage: python3 sim/no_clamp_breakdown.py
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
sys.path.insert(0, HERE)
import bicone_drive as BD          # noqa: E402
import stack_sizing as SS          # noqa: E402

F, N_CYC, STEPS = 120.0, 30, 20000
T_OFF, I_CHOP = 1e-6, 2.0           # the arc goes out ~1 us after its current falls below I_CHOP [RH]
L_ARC, R_ARC = 200e-9, 1.0
R_VANE = 5.0                       # the vane stack's own series resistance and leads [RH]: it also damps the stack's
                                   # self-discharge into the arc
GAP_MM = 3.0
SOLVER_OPTS = "itl4=500 reltol=2e-3"   # the strikes are stiff; this setting runs both cases through [ME]
CASES = {"vacuum": SS.gap_breakdown_kV(GAP_MM, "vacuum") * 1e3, "air": SS.gap_breakdown_kV(GAP_MM, "air") * 1e3}


def deck(v_bd):
    w = 2 * math.pi * F
    s1, s2 = f"(0.5*(1+cos({w:.8e}*time)))", f"(0.5*(1-cos({w:.8e}*time)))"
    cmin, cmax, ca, cp = BD.CMIN, BD.CMAX, BD.CA, BD.CPAR
    t = ["* diode doubler without clamps: breakdown across the vane stacks",
         f"C1v 1 c1x Q='({cmin:.6e}+{cmax - cmin:.6e}*{s1})*V(1,c1x)'", f"Rv1 c1x ra {R_VANE:g}",
         f"C2v 4 c2x Q='({cmin:.6e}+{cmax - cmin:.6e}*{s2})*V(4,c2x)'", f"Rv4 c2x rb {R_VANE:g}",
         f"Lca ra ca {BD.L_CONE:.6e}", f"Rca ca ca2 {BD.R_CONE}", "Vma ca2 0 0",
         f"Lcb rb cb {BD.L_CONE:.6e}", f"Rcb cb cb2 {BD.R_CONE}", "Vmb cb2 0 0",
         f"Kc Lca Lcb {BD.M_CONE / BD.L_CONE:.4f}",
         f"Ca 1 2 {ca:.6e}", f"Cb 3 4 {ca:.6e}",
         "Vlink rl 0 0"]                                   # counter-rotor rail -> shaft
    t += [f"Cp{n} {n} rl {cp:.3e}" for n in ("1", "2", "3", "4")] + [f"Cp{n} {n} 0 {cp:.3e}" for n in ("ra", "rb")]
    t += [".model ND D(is=1e-9 n=0.005 rs=1e-3 cjo=0)",
          "Dd1 2 n1 ND", "Vd1 n1 rl 0", "Dd2 3 n2 ND", "Vd2 n2 rl 0",
          "Dd3 1 n3 ND", "Vd3 n3 3 0", "Dd4 4 n4 ND", "Vd4 n4 2 0"]
    t += [".model ARC SW(vt=0.5 vh=0.2 ron=%g roff=1e13)" % R_ARC]
    for n, r in (("1", "ra"), ("4", "rb")):
        # latch: the gap voltage reaching V_BD (a 5 V-wide trigger, so nothing leaks below it), or the arc carrying
        # more than I_CHOP, holds h at 1 V; once both are gone h decays with T_OFF and the switch's hysteresis opens the
        # arc below 0.3 V
        trig = (f"0.5*(1+tanh((abs(V({n},{r}))-{v_bd:.1f})/5))"
                f"+0.5*(1+tanh((abs(i(Varc{n}))-{I_CHOP:g})/{0.1 * I_CHOP:g}))")
        t += [f"Bt{n} 0 h{n} I='({trig})*0.5*(1+tanh((1-V(h{n}))/0.02))'",
              f"Ch{n} h{n} 0 1e-9", f"Rh{n} h{n} 0 {T_OFF / 1e-9:.4g}",
              f"S{n} {n} s{n} h{n} 0 ARC OFF", f"La{n} s{n} s{n}b {L_ARC:.3e}", f"Varc{n} s{n}b {r} 0"]
    P = {"belt": f"{(cmax - cmin) * 0.5 * w:.6e}*sin({w:.8e}*time)*0.5*(V(1,c1x)*V(1,c1x)-V(4,c2x)*V(4,c2x))",
         "cone": f"{BD.R_CONE}*(i(Vma)*i(Vma)+i(Vmb)*i(Vmb))",
         "arc": f"{R_ARC}*(i(Varc1)*i(Varc1)+i(Varc4)*i(Varc4))"}
    for nd, ex in P.items():
        t += [f"Bp_{nd} 0 e_{nd} I='{ex}'", f"Cp_{nd} e_{nd} 0 1", f"Rp_{nd} e_{nd} 0 1e18"]
    ics = {"1": -1000.0, "4": -1000.0, "2": 0.0, "3": 0.0, "ra": 0.0, "rb": 0.0}
    ics.update({f"e_{nd}": 0.0 for nd in P})
    ics.update(h1=0.0, h4=0.0)
    vecs = ["v(1)", "v(4)", "i(Varc1)", "i(Varc4)", "i(Vd1)", "i(Vd2)", "i(Vd3)", "i(Vd4)", "i(Vma)", "i(Vmb)",
            "i(Vlink)"] + [f"v(e_{nd})" for nd in P]
    ms = 1.0 / F / STEPS
    t += [".ic" + "".join(f" v({n})={v:g}" for n, v in ics.items()), ".control",
          f"tran {ms:.4e} {N_CYC / F:.6e} uic", "wrdata out.dat " + " ".join(vecs), ".endc",
          f".options {SOLVER_OPTS} abstol=1e-12 vntol=1e-6 gmin=1e-15 maxstep={ms:.4e} method=gear", ".end"]
    return "\n".join(t) + "\n", vecs, list(P)


def run(case):
    v_bd = CASES[case]
    txt, vecs, pk = deck(v_bd)
    with tempfile.TemporaryDirectory() as d:
        open(os.path.join(d, "x.cir"), "w").write(txt)
        r = subprocess.run(["ngspice", "-b", "x.cir"], capture_output=True, text=True, timeout=7200, cwd=d)
        try:
            raw = np.loadtxt(os.path.join(d, "out.dat"))
        except (OSError, ValueError):
            return dict(case=case, error=(r.stdout + r.stderr)[-400:])
    t = raw[:, 0]
    c = {v: raw[:, 2 * j + 1] for j, v in enumerate(vecs)}
    T = 1 / F
    out = dict(case=case, V_bd_kV=v_bd / 1e3, t_end=float(t[-1]), done=bool(t[-1] >= 0.99 * N_CYC * T))
    # first strike: the growth time from the 1 kV seed
    ia = np.abs(c["i(Varc1)"])
    on = ia > 0.5
    first = t[np.argmax(on)] if on.any() else None
    out["first_strike_ms"] = None if first is None else float(first * 1e3)
    t0 = None if first is None else first + 1.5 * T     # past the first strike's recovery
    if t0 is None or t[-1] - t0 < 4 * T:                 # too little of the strike regime to read
        return out
    out["analysed_ms"] = [float(t0 * 1e3), float(t[-1] * 1e3)]
    s = t >= t0
    ts, dur = t[s], t[-1] - t0
    for nd in pk:
        y = c[f"v(e_{nd})"]
        out[f"P_{nd}_W"] = float((np.interp(t[-1], t, y) - np.interp(t0, t, y)) / dur)
    out["P_diodes_W"] = out["P_belt_W"] - out["P_cone_W"] - out["P_arc_W"]

    def strikes(i):
        """strike starts: the arc current exceeding 0.5 A after more than 0.2 ms quiet."""
        idx = np.where(np.abs(i) > 0.5)[0]
        st, last = [], -1e9
        for k in idx:
            if ts[k] - last > 2e-4:
                st.append(ts[k])
            last = ts[k]
        return st
    st1, st4 = strikes(c["i(Varc1)"][s]), strikes(c["i(Varc4)"][s])
    out["strikes_per_s_side1"] = len(st1) / dur
    out["strikes_per_s_side4"] = len(st4) / dur
    out["E_per_strike_mJ"] = out["P_belt_W"] / max(1e-9, (len(st1) + len(st4)) / dur) * 1e3
    # the node just after each strike (residual) and just before (the strike voltage)
    v1 = c["v(1)"][s]
    ia1, lk = c["i(Varc1)"][s], c["i(Vlink)"][s]
    dur_, q_, res = [], [], []
    for x in st1:
        w = (ts >= x) & (ts <= x + 2e-3)
        tw, iw = ts[w], np.abs(ia1[w])
        hot = tw[iw > I_CHOP]
        end = hot[-1] if len(hot) else x
        dur_.append(end - x)
        ww = (ts >= x) & (ts <= end + 2e-6)
        q_.append(float(np.trapezoid(np.abs(lk[ww]), ts[ww])))
        res.append(float(np.abs(np.interp(end + 50e-6, ts, v1))))
    out["arc_duration_us"] = float(np.median(dur_) * 1e6) if dur_ else None
    out["link_charge_per_strike_mC"] = float(np.median(q_) * 1e3) if q_ else None
    out["V1_after_strike_kV"] = float(np.median(res) / 1e3) if res else None
    out["V1_peak_kV"] = float(np.abs(v1).max() / 1e3)
    pk_i = {k: float(np.abs(c[f"i({v})"][s]).max()) for k, v in
            (("arc", "Varc1"), ("D1", "Vd1"), ("D2", "Vd2"), ("D3", "Vd3"), ("D4", "Vd4"), ("cone A", "Vma"),
             ("cone B", "Vmb"), ("link", "Vlink"))}
    out["I_peak_A"] = pk_i
    out["cone_AT_pk"] = BD.N_CONE * max(pk_i["cone A"], pk_i["cone B"])
    lk = c["i(Vlink)"][s]
    out["link_rms_mA"] = float(np.sqrt(np.mean(lk ** 2)) * 1e3)
    # the pump between strikes: does it regrow? growth per cycle from the strike-to-strike record of |V1| peaks
    cyc = np.floor((ts - t0) / T).astype(int)
    pks = [float(np.abs(v1[cyc == n]).max()) for n in range(int(cyc.max()) + 1) if np.any(cyc == n)]
    out["V1_cycle_peaks_kV"] = [p / 1e3 for p in pks]
    return out


def main():
    with Pool(2) as pool:
        rows = pool.map(run, list(CASES))
    json.dump(dict(F_Hz=F, gap_mm=GAP_MM, L_arc_H=L_ARC, R_arc_ohm=R_ARC, R_vane_ohm=R_VANE, I_chop_A=I_CHOP,
                   T_off_s=T_OFF, rows=rows),
              open(os.path.join(HERE, "no_clamp_breakdown_results.json"), "w"), indent=1, default=float)
    for r in rows:
        print(json.dumps({k: v for k, v in r.items() if k != "V1_cycle_peaks_kV"}, default=float))
        print("   |V1| per cycle (kV):", " ".join(f"{x:.1f}" for x in r.get("V1_cycle_peaks_kV", [])))


if __name__ == "__main__":
    main()
