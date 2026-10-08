"""sim/ah_steady_cusp.py -- a steady cusp from the magnetic pump. Today each AH coil carries its utron branch's current,
139-449 A-turns at the pick, top and bottom peaking in turn, so the cusp's null moves along the axis every cycle. A
bypass capacitor across each AH coil (with its ESR) carries the branch's 120 Hz ripple and leaves the coil the branch's
DC: equal in the two branches, so the pair holds a steady cusp.
The pick (g 0.5 / 6 bridges / 1200 rpm relative), exactly as sim/rotor_parts_duty.py runs it (sim/magnetic_doubler.py
deck), with C_byp + ESR across AHt (x1-d) and AHb (x2-b). Per C: each coil's ampere-turns over the last 4 cycles (min,
mean, max, ripple), the largest top-bottom difference (the dipole that moves the null), the bypass current and its ESR
loss, and the pump's growth z and power ledger (magnetic_doubler.analyse). Writes sim/ah_steady_cusp_results.json.
[OC] the circuit; [IR] the capacitor as C + ESR; [RH] the ESR value.
Usage: python3 sim/ah_steady_cusp.py
"""
import json
import os
import subprocess
import sys
import tempfile
from multiprocessing import Pool

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import magnetic_doubler as M       # noqa: E402
import rotor_parts_duty as RP      # noqa: E402

C_BYP_MF = (0.0, 2.2, 4.7, 10.0, 22.0, 47.0)      # mF across each AH coil (0: today's circuit)
ESR = 0.01                                        # ohm, a low-ESR electrolytic bank [RH]


def run(c_mf):
    kw = RP._kw(RP.TAU_FIXED)
    txt, vecs, info = M.deck(**kw)
    if c_mf:
        byp = [f"R_bypA x1 xb1 {ESR:g}", f"C_bypA xb1 d {c_mf * 1e-3:g}",
               f"R_bypB x2 xb2 {ESR:g}", f"C_bypB xb2 b {c_mf * 1e-3:g}"]
        txt = txt.replace("D1s f2 b ND", "\n".join(byp) + "\nD1s f2 b ND")
    ex = ["v(ps_AHt)", "v(ps_AHb)"]
    txt = txt.replace("wrdata out.dat " + " ".join(vecs), "wrdata out.dat " + " ".join(vecs + ex))
    with tempfile.TemporaryDirectory() as d:
        open(os.path.join(d, "x.cir"), "w").write(txt)
        subprocess.run(["ngspice", "-b", "x.cir"], capture_output=True, text=True, timeout=3600, cwd=d)
        raw = np.loadtxt(os.path.join(d, "out.dat"))
    t = raw[:, 0]
    c = {v: raw[:, 2 * j + 1] for j, v in enumerate(vecs + ex)}
    m = M.analyse(t, c, info, kw)
    h = kw["ah_custom"]
    T = 1.0 / kw["F"]
    s = t >= (kw["n_cyc"] - 4) * T
    iA, iB = c["v(ps_AHt)"] / h["L"], c["v(ps_AHb)"] / h["L"]
    i1 = c["v(ps_L1)"] / M._L(t, 1, kw) * (1 + (c["v(ps_L1)"] / kw["psi_s"]) ** 6)
    out = dict(C_byp_mF=c_mf, ESR_ohm=ESR if c_mf else None, z_early=m.get("z_early"), P_belt_W=m.get("P_belt_W"),
               P_cu_utron_W=m.get("P_cu_utron_W"), P_cu_fixed_W=m.get("P_cu_fixed_W"), P_AH_W=m.get("P_AH_W"),
               branch_AT_min=h["N"] * float(np.abs(i1[s]).min()), branch_AT_max=h["N"] * float(np.abs(i1[s]).max()))
    for nm, i in (("top", iA), ("bottom", iB)):
        a = np.abs(i[s]) * h["N"]
        out[nm] = dict(AT_min=float(a.min()), AT_mean=float(a.mean()), AT_max=float(a.max()),
                       ripple_pp_frac=float((a.max() - a.min()) / a.mean()))
    out["dAT_max"] = float(np.max(np.abs(np.abs(iA[s]) - np.abs(iB[s]))) * h["N"])
    out["dAT_frac"] = out["dAT_max"] / (0.5 * (out["top"]["AT_mean"] + out["bottom"]["AT_mean"]))
    if c_mf:
        ic = i1[s] - iA[s]
        out["I_byp_rms_A"] = float(np.sqrt(np.mean(ic * ic)))
        out["P_esr_W"] = 2 * ESR * out["I_byp_rms_A"] ** 2
        out["V_byp_pk_V"] = float(np.max(np.abs(h["R"] * iA[s] + np.gradient(c["v(ps_AHt)"][s], t[s]))))
    print(f"C {c_mf:5.1f} mF: top {out['top']['AT_min']:.0f}-{out['top']['AT_max']:.0f} A-t (mean {out['top']['AT_mean']:.0f},"
          f" ripple {100 * out['top']['ripple_pp_frac']:.1f} % p-p), top-bottom up to {out['dAT_max']:.0f} A-t; z "
          f"{out['z_early']}, belt {out['P_belt_W']:.2f} W", flush=True)
    return out


def main():
    with Pool(2) as pool:
        rows = pool.map(run, C_BYP_MF, chunksize=1)
    json.dump(dict(pick=RP.PICK, esr_ohm=ESR, ah=M.AH["r160"], rows=rows),
              open(os.path.join(HERE, "ah_steady_cusp_results.json"), "w"), indent=1, default=float)


if __name__ == "__main__":
    main()
