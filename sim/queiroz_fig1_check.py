"""sim/queiroz_fig1_check.py -- the diode directions of the electrostatic core against the original paper:
A. C. M. de Queiroz, "Analysis of Electronic Electrostatic Generators", Fig. 1 (the symmetrical unipolar generator):
C1 (node 1) and C2 (node 4) variable to ground, Ca 1-2, Cb 3-4; D1 ground -> 2, D2 ground -> 3, D3 3 -> 1, D4 2 -> 4
(anode -> cathode); all voltages positive. Its example: C1, C2 complementary 60-360 pF, Ca = Cb = 330 pF, 20 Hz,
startup gain z = 1.17138 [OC: the paper's eq. after (23)], per HALF cycle (its eq. (15) maps phase 1 to phase 2 with
the nodes swapped), i.e. 1.17138^2 = 1.37213 per full cycle.
The repo's core (solveDoubler4, sim/bicone_drive.py, sim/magnetic_doubler.py): D1 2 -> ref, D2 3 -> ref, D3 1 -> 3,
D4 4 -> 2, seeded negative: every diode reversed, i.e. the same circuit at negative polarity.
Runs the paper's example in ngspice four ways (paper / repo directions, each diode-set with its own seed polarity, and
one single-diode flip) and reports z per cycle. (Flipping D3 or D4 alone forward-biases it at the seed, which the
near-ideal diode model cannot start from, so the flip shown is D1's.) Writes sim/queiroz_fig1_check_results.json.
Usage: python3 sim/queiroz_fig1_check.py
"""
import json
import math
import os
import subprocess
import tempfile

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
CMIN, CMAX, CA, F, N_CYC = 60e-12, 360e-12, 330e-12, 20.0, 14
PAPER = dict(D1=("0", "2"), D2=("0", "3"), D3=("3", "1"), D4=("2", "4"))       # anode, cathode
REPO = dict(D1=("2", "0"), D2=("3", "0"), D3=("1", "3"), D4=("4", "2"))
CASES = {
    "paper directions, positive seed": (PAPER, +1.0),
    "repo directions, negative seed": (REPO, -1.0),
    "repo, D1 alone flipped": (dict(REPO, D1=("0", "2")), -1.0),
}


def run(diodes, seed, n=0.005):
    w = 2 * math.pi * F
    s1, s2 = f"(0.5*(1+cos({w:.8e}*time)))", f"(0.5*(1-cos({w:.8e}*time)))"
    t = ["* de Queiroz Fig. 1",
         f"C1v 1 0 Q='({CMIN:.4e}+{CMAX - CMIN:.4e}*{s1})*V(1)'",
         f"C2v 4 0 Q='({CMIN:.4e}+{CMAX - CMIN:.4e}*{s2})*V(4)'",
         f"Ca 1 2 {CA:.4e}", f"Cb 3 4 {CA:.4e}",
         f".model ND D(is=1e-12 n={n:g} rs=1e-3 cjo=0)"]
    t += [f"{k} {a} {c} ND" for k, (a, c) in diodes.items()]
    ms = 1.0 / F / 4000
    # the seed on the variable capacitors only (nodes 2, 3 at 0): it excites the growing mode. (Seeding all four nodes
    # alike excites a decaying one, z 0.806: the paper's "complicated operation during startup".)
    t += [f".ic v(1)={seed} v(4)={seed} v(2)=0 v(3)=0", ".control", f"tran {ms:.4e} {N_CYC / F:.6e} uic",
          "wrdata out.dat v(1) v(2) v(3) v(4)", ".endc",
          f".options reltol=1e-6 abstol=1e-15 vntol=1e-9 maxstep={ms:.4e} method=gear", ".end"]
    with tempfile.TemporaryDirectory() as d:
        open(os.path.join(d, "x.cir"), "w").write("\n".join(t) + "\n")
        r = subprocess.run(["ngspice", "-b", "x.cir"], capture_output=True, text=True, timeout=600, cwd=d)
        if not os.path.exists(os.path.join(d, "out.dat")):
            return dict(error=(r.stdout + r.stderr).strip().splitlines()[-3:])
        raw = np.loadtxt(os.path.join(d, "out.dat"))
    tt = raw[:, 0]
    V = {n: raw[:, 2 * j + 1] for j, n in enumerate(("1", "2", "3", "4"))}
    cyc = np.floor(tt * F).astype(int)
    pk = [float(np.abs(V["1"][cyc == k]).max()) for k in range(N_CYC) if np.any(cyc == k)]
    z = [pk[k + 1] / pk[k] for k in range(len(pk) - 1) if pk[k] > 0]
    sign = {n: ("+" if V[n].max() > -V[n].min() else "-") for n in V}
    return dict(z_late=float(np.median(z[-5:])), V1_peaks=pk, polarity=sign,
                grows=bool(pk[-1] > 10 * abs(seed)))


def main():
    rows = {}
    for name, (dio, seed) in CASES.items():
        r = run(dio, seed)
        if "error" in r:                                  # the near-ideal diodes can stall ngspice: retry softer
            r = dict(run(dio, seed, n=0.05), diode_n=0.05)
        rows[name] = dict(diodes={k: f"{a}->{c}" for k, (a, c) in dio.items()}, seed_V=seed, **r)
        if "error" in r:
            print(f"{name:34s} ngspice: {r['error']}")
        else:
            print(f"{name:34s} z {r['z_late']:.5f}  grows {r['grows']}  polarity {r['polarity']}  "
                  f"|V1| last {r['V1_peaks'][-1]:.3g} V")
    json.dump(dict(source="de Queiroz, Analysis of Electronic Electrostatic Generators, Fig. 1",
                   z_paper_half_cycle=1.17138, z_paper_full_cycle=1.17138 ** 2, Cmin=CMIN, Cmax=CMAX, Ca=CA, F=F,
                   rows=rows),
              open(os.path.join(HERE, "queiroz_fig1_check_results.json"), "w"), indent=1)


if __name__ == "__main__":
    main()
