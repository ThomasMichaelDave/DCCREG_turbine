"""sim/ah_winding.py -- which way the AH coils' currents flow, and so how the pair must be wound and connected to be
anti-Helmholtz (ledger §6 item 8).

The pick (g 0.5 / 6 bridges / 1200 rpm relative) runs as sim/ah_steady_cusp.py runs it (sim/magnetic_doubler.py deck,
sim/rotor_parts_duty.py's settings), without and with the 22 mF bypass (PROPOSED). The deck's elements:
  - group A's branch a -> L1 -> x1 -> AHt -> d, and group B's c -> L2 -> x2 -> AHb -> b;
  - AHt / AHb are the names from the pivot, when side A was the upper side. In the record side A is below, so AHt is
    side A's coil (below) and AHb side B's (above): each branch carries its own side's coil, as each shaft half carries
    its side's circuits (presets/hub-locked.json pumps, DECIDED).
Read: the sign of each coil's current in its element's orientation (x1 -> d, x2 -> b) over the last four cycles [OC].
Writes sim/ah_winding_results.json.
Usage: python3 sim/ah_winding.py
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
import ah_steady_cusp as SC        # noqa: E402
import magnetic_doubler as M       # noqa: E402
import rotor_parts_duty as RP      # noqa: E402


def run(c_mf):
    kw = RP._kw(RP.TAU_FIXED)
    txt, vecs, info = M.deck(**kw)
    if c_mf:
        byp = [f"R_bypA x1 xb1 {SC.ESR:g}", f"C_bypA xb1 d {c_mf * 1e-3:g}",
               f"R_bypB x2 xb2 {SC.ESR:g}", f"C_bypB xb2 b {c_mf * 1e-3:g}"]
        txt = txt.replace("D1s f2 b ND", "\n".join(byp) + "\nD1s f2 b ND")
    ex = ["v(ps_AHt)", "v(ps_AHb)"]
    txt = txt.replace("wrdata out.dat " + " ".join(vecs), "wrdata out.dat " + " ".join(vecs + ex))
    with tempfile.TemporaryDirectory() as d:
        open(os.path.join(d, "x.cir"), "w").write(txt)
        subprocess.run(["ngspice", "-b", "x.cir"], capture_output=True, text=True, timeout=3600, cwd=d)
        raw = np.loadtxt(os.path.join(d, "out.dat"))
    t = raw[:, 0]
    c = {v: raw[:, 2 * j + 1] for j, v in enumerate(vecs + ex)}
    h = kw["ah_custom"]
    T = 1.0 / kw["F"]
    s = t >= (kw["n_cyc"] - 4) * T
    out = dict(C_byp_mF=c_mf, seed_A=kw.get("seed"))
    for nm, el in (("A (AHt, x1 -> d)", "AHt"), ("B (AHb, x2 -> b)", "AHb")):
        i = c[f"v(ps_{el})"][s] / h["L"]                  # a linear coil: i = Psi / L
        out[nm] = dict(I_mean_A=float(i.mean()), I_min_A=float(i.min()), I_max_A=float(i.max()),
                       frac_negative=float(np.mean(i < 0)), AT_mean=float(h["N"] * i.mean()))
    a, b = out["A (AHt, x1 -> d)"], out["B (AHb, x2 -> b)"]
    out["same_sign"] = bool(np.sign(a["I_mean_A"]) == np.sign(b["I_mean_A"]) and a["frac_negative"] in (0.0, 1.0)
                            and b["frac_negative"] in (0.0, 1.0))
    print(f"C {c_mf:4.1f} mF: coil A {a['I_min_A']:+.3f} .. {a['I_max_A']:+.3f} A (x1 -> d), coil B {b['I_min_A']:+.3f} .. "
          f"{b['I_max_A']:+.3f} A (x2 -> b); unipolar and the same sign: {out['same_sign']}", flush=True)
    return out


def main():
    with Pool(2) as pool:
        rows = pool.map(run, (0.0, 22.0), chunksize=1)
    rule = dict(
        currents="each coil's current is unipolar and of the same sign in its element's orientation, in both branches "
                 "(the dual's twin branches) [OC]",
        connect="coil A: its start to x1 (group A's utrons), its finish to d; coil B: its start to x2, its finish to b",
        wind="two identical coils (the same hand, the start lead at the same end); mounted as rotated copies, each "
             "with its start lead toward the vessel. A coil rotated end over end reverses its circulation about +z "
             "for the same terminal current, so the pair's fields oppose: anti-Helmholtz [OC]",
        not_this="identical coils with the same terminal connections, both with the start lead upward (a translated "
                 "copy) give the same circulation: Helmholtz, a field of about the pair's sum at the null",
        check="at the bench, energise the pair from a DC supply through the same terminals: B at the centre within "
              "noise of zero, and of opposite sign 10 mm above and below the centre")
    json.dump(dict(pick=RP.PICK, ah=M.AH["r160"], rows=rows, rule=rule),
              open(os.path.join(HERE, "ah_winding_results.json"), "w"), indent=1, default=float)


if __name__ == "__main__":
    main()
