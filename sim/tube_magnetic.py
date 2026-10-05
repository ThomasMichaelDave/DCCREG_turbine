#!/usr/bin/env python3
"""sim/tube_magnetic.py -- does the shaft disturb the reluctance drive? C-EM permeance with and without a steel shaft.

Same magnetostatic analogue as sim/cem_inductance.py (ideal iron = magnetic equipotential, linear MMF on the spine,
floating iron bodies eliminated by zero net flux), one C-EM per 60 deg period with a utron at 15 deg [IR: 6 utrons
equivalent], placed at the tube's utron radius r_u. The shaft is a floating iron cylinder (steel, mu >> 1) over the
section height, or absent (= a non-magnetic shaft: austenitic stainless, Ti, composite).
Reported: the permeance (mm) aligned (rotor 15) and between C-EMs (rotor 45), and the swing.
Usage: python3 sim/tube_magnetic.py [r_u ...]
"""
import json, math, os, sys
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE)
sys.path[:0] = [HERE]
import cem_inductance as CI

SHAFT_R = 12.5


def design(r_u, shaft):
    _, d = CI.design()
    ru0 = d["r_utron_centre"]
    for p in d["parts"]:                       # move every piece radially by r_u - ru0 (same local geometry)
        p["r_in"] += r_u - ru0; p["r_out"] += r_u - ru0
        rm = 0.5 * (p["r_in"] + p["r_out"])
        w_mm = math.radians(p["w_deg"]) * (rm - (r_u - ru0))
        c = p["start_deg"] + 0.5 * p["w_deg"]
        p["w_deg"] = math.degrees(w_mm / rm); p["start_deg"] = (c - 0.5 * p["w_deg"]) % 360.0
    if shaft:
        d["parts"].append(dict(name="shaft", shape="sector", r_in=5.5, r_out=SHAFT_R, start_deg=0.0, w_deg=360.0,
                               z0=-80.0, z1=80.0, node="S", body="rotor AB", material=CI.COND + "steel shaft", role="magnetic"))
    return d


def permeance(names, C_pF):
    C = np.asarray(C_pF, float) * 1e-12
    fl = [i for i, n in enumerate(names) if n in ("U", "S")]
    di = [i for i, n in enumerate(names) if n not in ("U", "S")]
    Cr = C[np.ix_(di, di)] - C[np.ix_(di, fl)] @ np.linalg.solve(C[np.ix_(fl, fl)], C[np.ix_(fl, di)])
    v = CI.psi_vector([names[i] for i in di]); x = np.array([v[names[i]] for i in di])
    A = (CI.SPINE_X[1] - CI.SPINE_X[0]) * CI.CORE_W; g = 2 * CI.WIN_HALF / CI.N_PLATE - CI.PLATE_T
    return float(x @ Cr @ x) / CI.EPS0_MM / 6.0 - (CI.N_PLATE - 1) * A / g * (1.0 / CI.N_PLATE) ** 2


def main(rus):
    import round_trip as RTR
    out = []
    for r_u in rus:
        for shaft in (False, True):
            d = design(r_u, shaft)
            row = dict(r_u=r_u, shaft="steel" if shaft else "none / non-magnetic")
            for th, key in ((15.0, "aligned"), (45.0, "between")):
                s = RTR.solve_theta(d, th, "c", enclosure=None, r_cut=5.0)
                row[key] = permeance(s["names"], s["C"])
            row["swing"] = row["aligned"] / row["between"] - 1
            out.append(row)
            print(f"r_u {r_u:6.1f}  shaft {row['shaft']:20s}  P aligned {row['aligned']:7.1f}  between {row['between']:7.1f} mm  swing {row['swing']*100:5.1f} %", flush=True)
    json.dump(out, open(os.path.join(HERE, "tube_magnetic_results.json"), "w"), indent=1)


if __name__ == "__main__":
    main([float(x) for x in sys.argv[1:]] or [47.4, 70.0])
