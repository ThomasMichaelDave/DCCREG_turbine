"""sim/rotor_parts_duty.py -- what the parts of the rotor schematic (docs/schematic-rotor-circuits.svg) must carry at the
pick (g 0.5 / 6 bridges / 1200 rpm relative), from the two netlists of record. Writes sim/rotor_parts_duty_results.json.

1. La / Lb (sim/magnetic_doubler.py, the pick exactly as sim/pole_design.size_op runs it): current, voltage and peak
   stored energy, the D1*-D4* reverse voltages, and how the pump depends on the La / Lb time constant (the 0.5 s of
   TAU_FIXED is [RH]); at the pick's Psi_s, not re-solved.
2. La / Lb as parts: a first-cut gapped choke [RH] -- a scrapless EI core of M235-35A, square centre leg of side a,
   window 0.5a x 1.5a, the gap in the centre leg; B_PK at the peak current, fill K_U, copper at 20 C (as the utrons'
   tau). The size follows from the stored energy and tau: a^5 = rho (L I^2) c_t tau / (B^2 k_u c_w) [OC: gap-dominated
   reluctance; the iron and the joints add ~20 % to so small a gap, which a real design trims with the turns].
3. Z1 / Z4, the 20 kV clamps (sim/bicone_drive.py, diodes only) at 600 and 1200 rpm relative: current, conduction,
   power and energy per cycle, the node peak; and the current that crosses from the counter-rotor to the shaft (cone A +
   cone B), which the reference link (a brush, or for now the inner bearings) carries.
4. The clamp as a part: a string of N_Z avalanche (Zener) diodes of V_Z each [RH].
Usage: python3 sim/rotor_parts_duty.py
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
import magnetic_doubler as M       # noqa: E402

PICK = "g 0.5 / 6 bridges / 1200 rpm"
LA_RATIO, TAU_FIXED, ND, SEED_FRAC, N_CYC = 0.6, 0.5, 1.0, 0.3, 60      # as sim/pole_design.size_op
TAU_SWEEP = (0.05, 0.1, 0.2, 0.5)
B_PK, K_U, RHO_CU, RHO_FE, RHO_CU_KG = 1.2, 0.5, 1.72e-8, 7650.0, 8900.0
C_A, C_W, C_T = 1.0, 0.75, 4 + math.pi / 2             # EI: A_core = a^2, A_window = 0.75 a^2, mean turn 5.57 a
V_CORE, V_CU = 6.0, 0.75 * (4 + math.pi / 2)            # core volume / a^3; copper volume / (k_u a^3)
N_Z, V_Z = 100, 200.0                                   # clamp string [RH]


def pick():
    op = json.load(open(os.path.join(HERE, "pole_design_variants_op.json")))["designs"][PICK]
    rows = json.load(open(os.path.join(HERE, "pole_design_variants.json")))["rows"]
    r = [x for x in rows if x["design"] == op["design"]][0]
    b = op["best"]
    f = r["cyc_per_rev"] * b["rpm"] / 60.0
    Lmax = 3 * b["N_u"] ** 2 * r["L_al"]
    return r, b, f, Lmax


def _kw(tau_fixed):
    r, b, f, Lmax = pick()
    return dict(prof=r["prof"], tau=r["tau"], tau_fixed=tau_fixed, sat=True, F=f, n_cyc=N_CYC, L_max=Lmax,
                psi_s=b["psi_s"], la_ratio=LA_RATIO, ah="custom", ah_custom=M.AH["r160"], seed=SEED_FRAC * b["psi_s"] / Lmax,
                nd=ND, snub="scaled")


def _ngspice(txt):
    with tempfile.TemporaryDirectory() as d:
        open(os.path.join(d, "x.cir"), "w").write(txt)
        subprocess.run(["ngspice", "-b", "x.cir"], capture_output=True, text=True, timeout=3600, cwd=d)
        return np.loadtxt(os.path.join(d, "out.dat"))


def magnetic_duty():
    """La / Lb current and voltage, D1*-D4* reverse voltage over the last 4 cycles of the pick."""
    kw = _kw(TAU_FIXED)
    txt, vecs, info = M.deck(**kw)
    ex = ["v(ps_La)", "v(ps_Lb)"] + [f"v({n})" for n in ("a", "b", "c", "d", "f2", "f3")]
    raw = _ngspice(txt.replace("wrdata out.dat " + " ".join(vecs), "wrdata out.dat " + " ".join(vecs + ex)))
    c = {v: raw[:, 2 * j + 1] for j, v in enumerate(vecs + ex)}
    t = raw[:, 0]
    s = t >= (N_CYC - 4) / kw["F"]
    la = info["la"]
    out = dict(L_H=la, R_ohm=la / TAU_FIXED, tau_s=TAU_FIXED, f_Hz=kw["F"])
    for nm, node in (("La", "a"), ("Lb", "c")):
        i = c[f"v(ps_{nm})"][s] / la
        ia = np.abs(i)
        out[nm] = dict(I_max_A=float(ia.max()), I_min_A=float(ia.min()), I_mean_A=float(ia.mean()),
                       I_rms_A=float(np.sqrt(np.mean(i ** 2))), V_pk_V=float(np.abs(c[f"v({node})"][s]).max()),
                       W_pk_J=float(0.5 * la * ia.max() ** 2), P_cu_W=float(la / TAU_FIXED * np.mean(i ** 2)))
    V = {n: c[f"v({n})"][s] for n in ("a", "b", "c", "d", "f2", "f3")}
    vr = {"D1*": V["b"] - V["f2"], "D2*": V["f3"] - V["c"], "D3*": V["d"], "D4*": V["b"]}   # V(cathode) - V(anode)
    out["diode_VR_pk_V"] = {k: float(v.max()) for k, v in vr.items()}
    return out


def _sweep_one(tf):
    m = M.run(**_kw(tf))
    keep = ("z_early", "AH_AT_pk", "AH_AT_min", "P_belt_W", "P_cu_utron_W", "P_cu_fixed_W", "P_AH_W", "I1_pk")
    return dict(tau_fixed_s=tf, **{k: m.get(k) for k in keep})


def la_core(L, I_pk, I_rms, tau):
    """first-cut gapped EI choke for L at I_pk with time constant tau [RH]."""
    a = (RHO_CU * L * I_pk ** 2 * C_T * tau / (B_PK ** 2 * C_A ** 2 * K_U * C_W)) ** 0.2
    N = L * I_pk / (B_PK * C_A * a ** 2)
    l_gap = 4e-7 * math.pi * N * I_pk / B_PK
    a_wire = K_U * C_W * a ** 2 / N
    R = RHO_CU * N * C_T * a / a_wire
    return dict(tau_s=tau, a_mm=a * 1e3, turns=round(N), gap_mm=l_gap * 1e3, wire_mm2=a_wire * 1e6,
                wire_d_mm=2 * math.sqrt(a_wire / math.pi) * 1e3, R_ohm=R, P_cu_W=R * I_rms ** 2,
                m_core_kg=V_CORE * a ** 3 * RHO_FE, m_cu_kg=V_CU * K_U * a ** 3 * RHO_CU_KG,
                outline_mm=(3 * a * 1e3, 2.5 * a * 1e3, a * 1e3))


def _clamp_one(F):
    BD.F = F
    txt, vecs, pk = BD.deck("diodes")
    ex = ["i(Vz1)", "i(Vz4)"]
    raw = _ngspice(txt.replace("wrdata out.dat " + " ".join(vecs), "wrdata out.dat " + " ".join(vecs + ex)))
    c = {v: raw[:, 2 * j + 1] for j, v in enumerate(vecs + ex)}
    t = raw[:, 0]
    s = t >= (24 - 8) / F
    ts = t[s]
    dt, dur = np.diff(ts), ts[-1] - ts[0]

    def avg(y):
        return float(np.sum(0.5 * (y[1:] + y[:-1]) * dt) / dur)
    out = dict(F_Hz=F, rpm_rel=60 * F / 6)
    for nd in pk:
        y = c[f"v(e_{nd})"]
        out[f"P_{nd}_W"] = float((np.interp(ts[-1], t, y) - np.interp(ts[0], t, y)) / dur)
    for z, node in (("Z1", "v(1)"), ("Z4", "v(4)")):
        i, v = c[f"i(V{z.lower()})"][s], c[node][s]
        on = 0.5 * (i[1:] + i[:-1]) > 0.05 * i.max()
        p = avg(-v * i)
        out[z] = dict(I_pk_mA=float(i.max() * 1e3), I_avg_mA=avg(i) * 1e3, I_rms_mA=math.sqrt(avg(i * i)) * 1e3,
                      conduction=float(np.sum(dt[on]) / dur), P_W=p, E_per_cycle_mJ=p / F * 1e3,
                      V_node_pk_kV=float(np.abs(v).max() / 1e3))
    ia, ib = c["i(Vma)"][s], c["i(Vmb)"][s]
    link = ia + ib                                  # cone A + cone B into the shaft = the counter-rotor-to-shaft current
    out["cone_rms_mA"] = math.sqrt(avg(ia * ia)) * 1e3
    out["link"] = dict(I_pk_mA=float(np.abs(link).max() * 1e3), I_rms_mA=math.sqrt(avg(link * link)) * 1e3,
                       I_avg_mA=avg(link) * 1e3)
    return out


def main():
    with Pool(4) as pool:
        es = pool.map_async(_clamp_one, (60.0, 120.0))
        sweep = pool.map(_sweep_one, TAU_SWEEP)
        mag = magnetic_duty()
        es = es.get()
    La = mag["La"]
    cores = [la_core(mag["L_H"], La["I_max_A"], La["I_rms_A"], tf) for tf in (0.5, 0.2)]
    zc = es[-1]["Z1"]
    string = dict(N=N_Z, V_Z=V_Z, BV_kV=N_Z * V_Z / 1e3, P_per_diode_W=zc["P_W"] / N_Z, I_pk_mA=zc["I_pk_mA"])
    out = dict(pick=PICK, la_lb=mag, tau_sweep=sweep, la_core=cores, clamps=es, clamp_string=string,
               assumptions=dict(B_pk_T=B_PK, k_u=K_U, rho_cu=RHO_CU, core="scrapless EI, square centre leg, gap in it"))
    json.dump(out, open(os.path.join(HERE, "rotor_parts_duty_results.json"), "w"), indent=1, default=float)
    print(f"La: {La['I_min_A']:.2f}-{La['I_max_A']:.2f} A (mean {La['I_mean_A']:.2f}, rms {La['I_rms_A']:.2f}), "
          f"{La['V_pk_V']:.0f} V pk, {La['W_pk_J'] * 1e3:.0f} mJ pk; D* reverse {mag['diode_VR_pk_V']}")
    for q in sweep:
        print(f"  tau_fixed {q['tau_fixed_s']:g} s: z {q['z_early']:.3f}, AH {q['AH_AT_pk']:.0f} A-t, La+Lb {q['P_cu_fixed_W']:.2f} W")
    for q in cores:
        print(f"  choke tau {q['tau_s']:g} s: leg {q['a_mm']:.1f} mm, {q['turns']} t of {q['wire_mm2']:.2f} mm2, gap "
              f"{q['gap_mm']:.2f} mm, {q['m_core_kg']:.2f} kg iron + {q['m_cu_kg']:.2f} kg Cu")
    for q in es:
        z = q["Z1"]
        print(f"  {q['rpm_rel']:.0f} rpm: clamp {z['P_W']:.2f} W, {z['I_pk_mA']:.2f} mA pk / {z['I_avg_mA']:.3f} avg, "
              f"conducting {100 * z['conduction']:.0f} %, node {z['V_node_pk_kV']:.2f} kV; link {q['link']['I_rms_mA']:.2f} mA rms")


if __name__ == "__main__":
    main()
