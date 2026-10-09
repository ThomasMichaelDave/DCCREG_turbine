"""sim/magnetic_doubler.py -- the MAGNETIC dual of the de Queiroz diode doubler: the A / B wound utron groups as variable
inductors, steered by diodes, driving the AH pair (top coil in the A branch, bottom coil in the B branch). ngspice.

Duality [OC] (planar dual of solveDoubler4's graph, a wheel: ref at the hub, ring 1-2-4-3): C -> L, V -> I, Q -> Psi,
an ideal diode -> an ideal diode (anode = the face on the right of the original edge). Mapping, with L = r^2 C:

    electrostatic (solveDoubler4)            magnetic dual (this file; dual nodes a b c d f2 f3, ref 0)
    C1(t)+Cpar  1-ref                        L1(t)+Lpar  a -> d     A utron group (+ AH top)
    C2(t)+Cpar  4-ref                        L2(t)+Lpar  c -> b     B utron group (+ AH bottom)
    Ca          1-2                          La          0 -> a     fixed coupling inductor
    Cb          3-4                          Lb          c -> 0     fixed coupling inductor
    Cpar        2-ref / 3-ref                Lp2 f2 -> a,  Lp3 d -> f3   (stray, in series with D1* / D2*)
    D1 2->ref,  D2 3->ref                    D1* f2 -> b,  D2* c -> f3
    D3 1->3,    D4 4->2                      D3* 0 -> d,   D4* 0 -> b

The seed V1 = V4 = -1 maps to i(L1) = i(L2) = i(La) = -1, i(Lb) = +1 (consistent: D3*, D4* conduct at t = 0).

Physics: L falls at fixed flux -> current rises (the belt does work: dynamo); L rises -> motoring. A and B are in antiphase,
so one group generates while the other motors, swapping every half cycle (the user's A-dynamo / B-motor picture).
Mechanical input per variable inductor = (Psi^2/2 + Psi^8/(8 Psi_s^6)) d(1/L)/dt, from W(Psi, theta) of the saturating law
i = Psi/L(theta) (1 + (Psi/Psi_s)^6) [IR]. Copper: R = L / tau per coil. Every power term is integrated by ngspice.

Defaults (tube, geared 1 : -1 at 300 rpm each -> 600 rpm relative, 6 L-cycles per rev -> 60 Hz) [IR/RH]:
- utron group = 3 wound utrons in series: L_max 2 H (1150 turns per coil, 20 x 20 mm core, 1 mm total aligned gap),
  B_sat 1.5 T -> Psi_s = 3 x 1150 x 1.5 x 4e-4 = 2.07 Wb; tau = L/R 0.118 s (0.67 mm wire, 50 % fill) [RH];
- L ratio kappa_L (aligned / unaligned) of a toothed, switched-reluctance-style pole pair [RH: 6-10 is typical];
- La = Lb = 1.1 L_max (Ca / C1max), Lpar = 0.018 L_max (Cpar / C1max), as in the electrostatic core;
- AH: variant (a) 50 turns (98.5 uH with rod, 0.026 ohm) or a 600-turn rewind in the same former (14.2 mH, 3.8 ohm) [RH].
The stator C-EMs are passive toothed iron (the varying reluctance); their coils are not used.

Usage: python3 sim/magnetic_doubler.py   (writes sim/magnetic_doubler_results.json)
"""
import json
import math
import os
import subprocess
import sys
import tempfile

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
F = 60.0                                  # L-cycles per second (6 per rev at 600 rpm relative)
W_REL = 2 * math.pi * 600.0 / 60.0
L_MAX = 2.0
PSI_S = 2.07
TAU = 0.118
R_CA, R_PAR = 1224.694 / 1113.358, 20.0 / 1113.358
AH = {"a50": dict(L=98.5e-6, R=0.026, N=50), "r160": dict(L=1.01e-3, R=0.27, N=160), "r600": dict(L=14.2e-3, R=3.8, N=600)}
# r160 / r600: rewinds of variant (a)'s former; L ~ N^2, R ~ N^2 in the same window [RH]
AT_ROD_LIMIT = 1022 * 0.30 / 0.51         # A-turns that put the AH rod at 0.30 T (G-AH-SAT scaling from 0.51 T @ 1022)
# (conservative: that run had the cone windings in series; for the AH alone 0.30 T is 743 A-turns, sim/ah_null.py)
SEED = 0.01                               # A
CSNUB, RSNUB = 10e-9, 1e3                 # RC at each dual node [IR]


def _coeffs(kw):
    """L(theta)/L_max as a cosine series a_k cos(k w t) (aligned at t = 0); default: the plain cosine of ratio kappa."""
    if kw.get("prof") is not None:
        return list(kw["prof"])
    k = kw.get("kappa", 6.0)
    return [(1 + 1 / k) / 2, (1 - 1 / k) / 2]


def _shape_expr(a, w, phase_k):
    """ngspice text for sum a_k cos(k w t + k phase) and its time derivative."""
    f = "+".join(f"({ak:.8e})*cos({k * w:.8e}*time+{k * phase_k:.8f})" for k, ak in enumerate(a))
    df = "+".join(f"({-k * w * ak:.8e})*sin({k * w:.8e}*time+{k * phase_k:.8f})" for k, ak in enumerate(a) if k > 0)
    return f"({f})", f"({df})"


def deck(kappa=6.0, tau=TAU, tau_fixed=None, sat=True, ah=None, n_cyc=60, steps=2000, seed=SEED, nd=0.05,
         F=F, prof=None, L_max=L_MAX, psi_s=PSI_S, la_ratio=R_CA, ah_custom=None, snub="fixed", snub_k=1.0):
    tau_fixed = tau if tau_fixed is None else tau_fixed
    w = 2 * math.pi * F
    a = _coeffs(dict(kappa=kappa, prof=prof))
    lmin = L_max * sum(ak * (-1) ** k for k, ak in enumerate(a))      # at t = T/2
    lp = R_PAR * L_max
    la = la_ratio * L_max
    sh1, dsh1 = _shape_expr(a, w, 0.0)
    sh2, dsh2 = _shape_expr(a, w, math.pi)
    L1 = f"({L_max:.6e}*{sh1}+{lp:.6e})"
    L2 = f"({L_max:.6e}*{sh2}+{lp:.6e})"
    dinv1 = f"(-{L_max:.6e}*{dsh1}/({L1}*{L1}))"                       # d(1/L1)/dt
    dinv2 = f"(-{L_max:.6e}*{dsh2}/({L2}*{L2}))"
    PSI_S_ = psi_s
    R1 = L_max / tau                       # copper of the utron group (from its aligned L)
    t = ["* magnetic dual doubler", ".model ND D(is=1e-9 n=%g rs=1e-3 cjo=0)" % nd]
    P = {}
    ic = {}

    def ind(name, p, q, Lexpr, R, psi0, var=None, dinv=None):
        """flux-defined inductor p -> q with series R: v = dPsi/dt, i = Psi/L g(Psi)."""
        m = f"m_{name}"
        t.append(f"R_{name} {p} {m} {R:.6e}")
        t.append(f"Bv_{name} 0 ps_{name} I='V({m},{q})'")
        t.append(f"Cv_{name} ps_{name} 0 1")
        t.append(f"Rv_{name} ps_{name} 0 1e15")
        g = f"(1+pwr(abs(V(ps_{name}))/{PSI_S_:.6e},6))" if (var and sat) else "1"      # ngspice pwr keeps the sign
        t.append(f"Bi_{name} {m} {q} I='V(ps_{name})/{Lexpr}*{g}'")
        ic[f"ps_{name}"] = psi0
        P[f"cu_{name}"] = f"{R:.6e}*(V(ps_{name})/{Lexpr}*{g})*(V(ps_{name})/{Lexpr}*{g})"
        if var:
            G = f"(0.5*V(ps_{name})*V(ps_{name})" + (f"+pwr(abs(V(ps_{name})),8)/(8*pwr({PSI_S_:.6e},6))" if sat else "") + ")"
            P[f"mech_{name}"] = f"{G}*{dinv}"

    i0 = seed
    l1_0 = L_max * sum(a) + lp            # at t = 0: L1 at max, L2 at min
    l2_0 = lmin + lp
    # A branch a -> d (with AH top in series), B branch c -> b (with AH bottom). AHt / AHb are named from the pivot,
    # when side A was on top; in the record side A is below, so AHt is side A's coil (below) and AHb side B's (above):
    # each branch carries its own side's coil. Both carry a unipolar current of the same sign in this orientation
    # (x1 -> d, x2 -> b), so the pair is anti-Helmholtz when wound alike and mounted end over end (sim/ah_winding.py)
    if ah:
        h = ah_custom if ah == "custom" else AH[ah]
        ind("L1", "a", "x1", L1, R1, -i0 * l1_0, var=True, dinv=dinv1)
        ind("AHt", "x1", "d", f"{h['L']:.6e}", h["R"], -i0 * h["L"])
        ind("L2", "c", "x2", L2, R1, -i0 * l2_0, var=True, dinv=dinv2)
        ind("AHb", "x2", "b", f"{h['L']:.6e}", h["R"], -i0 * h["L"])
    else:
        ind("L1", "a", "d", L1, R1, -i0 * l1_0, var=True, dinv=dinv1)
        ind("L2", "c", "b", L2, R1, -i0 * l2_0, var=True, dinv=dinv2)
    ind("La", "0", "a", f"{la:.6e}", la / tau_fixed, -i0 * la)
    ind("Lb", "c", "0", f"{la:.6e}", la / tau_fixed, +i0 * la)
    ind("Lp2", "f2", "a", f"{lp:.6e}", lp / tau_fixed, 0.0)
    ind("Lp3", "d", "f3", f"{lp:.6e}", lp / tau_fixed, 0.0)
    t += ["D1s f2 b ND", "D2s c f3 ND", "D3s 0 d ND", "D4s 0 b ND"]
    # winding / stray capacitance with a damping resistor at every dual node: a cut-set of inductors and a diode has
    # nothing to hold its voltage when the diode opens [IR]
    nodes = ["a", "b", "c", "d", "f2", "f3"] + (["x1", "x2"] if ah else [])
    if snub == "scaled":
        # keep the snubber the same small perturbation it was at 60 Hz with L_max 2 H: L C F^2 and R / sqrt(L/C) fixed
        csn = CSNUB * (L_MAX / L_max) * (60.0 / F) ** 2 * snub_k
        rsn = RSNUB * (L_max / L_MAX) * (F / 60.0) / math.sqrt(snub_k)
    else:
        csn, rsn = CSNUB, RSNUB
    for n in nodes:
        t += [f"Cs_{n} {n} sn_{n} {csn:g}", f"Rs_{n} sn_{n} 0 {rsn:g}"]
    P["snub"] = "+".join(f"V(sn_{n})*V(sn_{n})/{rsn:g}" for n in nodes)
    for nd_, ex in P.items():
        t += [f"Bp_{nd_} 0 e_{nd_} I='{ex}'", f"Cp_{nd_} e_{nd_} 0 1", f"Rp_{nd_} e_{nd_} 0 1e18"]
        ic[f"e_{nd_}"] = 0.0
    ms = 1.0 / F / steps
    vecs = ["v(ps_L1)", "v(ps_L2)"] + [f"v(e_{k})" for k in P]
    t += [".ic" + "".join(f" v({k})={v:.6e}" for k, v in ic.items()), ".control",
          f"tran {ms:.4e} {n_cyc / F:.6e} uic", "wrdata out.dat " + " ".join(vecs), ".endc",
          f".options reltol=1e-5 abstol=1e-15 vntol=1e-9 gmin=1e-15 maxstep={ms:.4e} method=gear", ".end"]
    return "\n".join(t) + "\n", vecs, dict(lmin=lmin, lp=lp, la=la, R1=R1)


def run(**kw):
    txt, vecs, info = deck(**kw)
    with tempfile.TemporaryDirectory() as d:
        open(os.path.join(d, "x.cir"), "w").write(txt)
        r = subprocess.run(["ngspice", "-b", "x.cir"], capture_output=True, text=True, timeout=3600, cwd=d)
        try:
            raw = np.loadtxt(os.path.join(d, "out.dat"))
        except (OSError, ValueError):
            return dict(kw, error=(r.stdout + r.stderr)[-300:])
    t = raw[:, 0]
    c = {v: raw[:, 2 * j + 1] for j, v in enumerate(vecs)}
    return analyse(t, c, info, kw)


def _L(t, which, kw):
    a = _coeffs(kw)
    w = 2 * math.pi * kw.get("F", F)
    ph = 0.0 if which == 1 else math.pi
    Lm = kw.get("L_max", L_MAX)
    return Lm * sum(ak * np.cos(k * (w * t + ph)) for k, ak in enumerate(a)) + R_PAR * Lm


def analyse(t, c, info, kw):
    sat = kw.get("sat", True)
    n_cyc = kw.get("n_cyc", 60)
    T = 1.0 / kw.get("F", F)
    psi_s = kw.get("psi_s", PSI_S)

    def cur(which):
        psi = c[f"v(ps_L{which})"]
        i = psi / _L(t, which, kw)
        return i * (1 + (psi / psi_s) ** 6) if sat else i
    i1, i2 = cur(1), cur(2)
    cyc = np.floor(t / T).astype(int)
    pk = [float(np.abs(np.r_[i1[cyc == n], i2[cyc == n]]).max()) for n in range(n_cyc) if np.any(cyc == n)]
    z = [pk[k + 1] / pk[k] for k in range(len(pk) - 1) if pk[k] > 0]
    done = t[-1] >= 0.99 * n_cyc * T
    out = dict(kw, done=bool(done), t_end=float(t[-1]), z_early=float(np.median(z[2:8])) if len(z) > 8 else None,
               z_late=float(np.median(z[-5:])) if len(z) > 5 else None, I_peak_last_A=pk[-1] if pk else None)
    if not done or len(pk) < 8:
        return out
    t0, t1 = (n_cyc - 4) * T, t[-1]
    sel = t >= t0

    def mean(k):
        y = c[f"v(e_{k})"]
        return float((np.interp(t1, t, y) - np.interp(t0, t, y)) / (t1 - t0))
    keys = [k[4:-1] for k in c if k.startswith("v(e_")]
    P = {k: mean(k) for k in keys}
    mech = sum(v for k, v in P.items() if k.startswith("mech_"))
    cu = sum(v for k, v in P.items() if k.startswith("cu_L"))
    ah = sum(v for k, v in P.items() if k.startswith("cu_AH"))
    psi_pk = float(max(np.abs(c["v(ps_L1)"][sel]).max(), np.abs(c["v(ps_L2)"][sel]).max()))
    out.update(P_snub_W=P.get("snub", 0.0))
    out.update(P_belt_W=mech, P_cu_utron_W=P.get("cu_L1", 0) + P.get("cu_L2", 0),
               P_cu_fixed_W=cu - P.get("cu_L1", 0) - P.get("cu_L2", 0), P_AH_W=ah,
               I1_pk=float(np.abs(i1[sel]).max()), I1_min=float(np.abs(i1[sel]).min()),
               I2_pk=float(np.abs(i2[sel]).max()), I1_rms=float(np.sqrt(np.mean(i1[sel] ** 2))),
               B_core_pk_T=psi_pk / psi_s * 1.5, psi_pk=psi_pk, T_belt_mNm=mech / W_REL * 1e3)
    if kw.get("ah"):
        N = (kw["ah_custom"] if kw["ah"] == "custom" else AH[kw["ah"]])["N"]
        out.update(AH_AT_pk=N * out["I1_pk"], AH_AT_min=N * out["I1_min"], AH_rod_limit_AT=AT_ROD_LIMIT)
    # the A / B waveforms over the last cycle, for the plot
    s = t >= (n_cyc - 1) * T
    k = max(1, int(s.sum() // 200))
    out["wave"] = dict(t_ms=list((t[s][::k] - t[s][0]) * 1e3), iA=list(i1[s][::k]), iB=list(i2[s][::k]))
    return out


def main(only=None):
    path = os.path.join(HERE, "magnetic_doubler_results.json")
    rows = []

    def rec(tag, **kw):
        r = run(**kw)
        r["case"] = tag
        rows.append(r)
        if "error" in r:
            print(f"{tag:50s} ERROR {r['error']}", flush=True); return r
        s = f"{tag:50s} z early {r['z_early'] if r['z_early'] is None else round(r['z_early'], 4)} late " \
            f"{r['z_late'] if r['z_late'] is None else round(r['z_late'], 4)} | I_pk {r['I_peak_last_A']:.3g} A"
        if "P_belt_W" in r:
            s += (f" | belt {r['P_belt_W']:.3f} W, Cu utron {r['P_cu_utron_W']:.3f} fixed {r['P_cu_fixed_W']:.3f} AH "
                  f"{r['P_AH_W']:.4f} W | B {r['B_core_pk_T']:.2f} T")
            if "AH_AT_pk" in r:
                s += f" | AH {r['AH_AT_min']:.0f}-{r['AH_AT_pk']:.0f} A-t"
        print(s, flush=True)
        return r

    # 1. duality check: lossless, linear, the electrostatic ratio -> z must be the electrostatic 1.512 (cosine, ngspice)
    rec("CHECK near-lossless (tau 100 s) kappa 15.66", kappa=15.66, tau=100.0, sat=False, n_cyc=12)
    # 2. lossless z vs kappa_L
    for kap in (3.0, 5.0, 6.0, 8.0, 10.0):
        rec(f"near-lossless kappa {kap:g}", kappa=kap, tau=100.0, sat=False, n_cyc=16)
    # 3. with copper: z vs kappa_L, tau
    for kap in (6.0, 8.0, 10.0):
        for tau in (0.05, 0.118, 0.25, 0.5, 1.0):
            rec(f"copper kappa {kap:g} tau {tau:g} s", kappa=kap, tau=tau, sat=False, n_cyc=16)
    # 4. saturation-limited steady state with the AH pair in series (top in A, bottom in B)
    for kap, tau, ah, n in ((8.0, 0.25, "r160", 50), (8.0, 0.25, "r600", 50), (8.0, 0.25, "a50", 50),
                            (8.0, 0.118, "r160", 90), (8.0, 0.118, "r600", 90), (6.0, 0.25, "r160", 70)):
        rec(f"SAT kappa {kap:g} tau {tau:g} s, AH {ah}", kappa=kap, tau=tau, sat=True, ah=ah, n_cyc=n)
    json.dump(dict(F=F, L_max=L_MAX, Psi_s=PSI_S, rows=rows), open(path, "w"), indent=1, default=float)


if __name__ == "__main__":
    if len(sys.argv) > 2 and sys.argv[1] == "one":
        r = run(**json.loads(sys.argv[2])); r.pop("wave", None)
        print(json.dumps(r, default=float)[:1500])
    else:
        main()
