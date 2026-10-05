#!/usr/bin/env python3
"""sim/em_ra.py -- the RA tank on the register (BRIEF_ELECTROMAGNET_REGISTER §5.2-5.4, Phase 1): the D-11 comparison of
the three AH windings (a), (b), (c) with every mutual of the four windings, f0/Z0, the null (T-NULL), T-MIRROR, rod
saturation (G-AH-SAT) and loss, P-REG-5/8/9, the bench P-EDGE runs on the AH coil and E-REGIME. Readouts as fixed in
sim/em-register-predictions.md §B.                                                                     [OC/IR/ME]
Usage: python3 sim/em_ra.py [magnetics|edge|bench|all] -> sim/em_register_results.json ['ra'], sim/em_raw/*.npz
"""
import json
import math
import os
import sys
import time

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path[:0] = [HERE]
import edge_coil as EC                                   # noqa: E402
import em_ladder as L                                    # noqa: E402
import em_register as R                                  # noqa: E402

RAW = os.path.join(HERE, "em_raw")
VARS = ("a", "b", "c")
TR = 2e-9


def debye(A, f):
    return 1 + (A.mu["mu_i"] - 1) / (1 + 1j * f / A.mu["f_r"])


def chain_vectors(A, lad):
    """per winding: the branch-space selection (for currents in the chain direction)."""
    out = {}
    for w, m in lad.wmask.items():
        out[w] = m.astype(float)
    out["leads"] = (~lad.isturn).astype(float)
    return out


def magnetics(var, log=print, flip=False, ms_cache={}):
    p = L.preset()
    A = L.ra_assembly(var, True, p, flip_hands=flip)
    key = (var,)
    if key not in ms_cache:
        ms_cache[key] = L.MS(A)
    ms = ms_cache[key]
    es_dummy = dict(C=np.zeros((0, 0)), names=[], kinds=[], rod_segs=[])
    lad = L.Ladder(A, es_dummy)                      # inductive part only (no capacitance needed here)
    Lb_air = lad.L_air
    S = lad.S
    M1, T1 = ms.solve(1.0)
    C_R = R.val(R.preset("RA"), "rotor", "C_R_pF") * 1e-12
    f0 = 200e3
    for it in range(4):
        mu = complex(debye(A, f0))
        Mm, Tm = ms.solve(mu, keep_psi=True)
        dL = Mm - M1
        Lb = Lb_air + S @ dL @ S.T
        ones = np.ones(lad.nb)
        Lc = ones @ Lb @ ones
        f0 = 1 / (2 * math.pi * math.sqrt(Lc.real * C_R))
    psi_mu = ms.last_psi
    sel = chain_vectors(A, lad)
    names = ["L_TC", "L_TA", "L_BA", "L_BC", "leads"]
    tab = {a: {b: float((sel[a] @ Lb @ sel[b]).real * 1e6) for b in names} for a in names}
    L_tot = float(Lc.real)
    R_core = float(-2 * math.pi * f0 * Lc.imag)
    Z0 = math.sqrt(L_tot / C_R)
    f0x4 = 1 / (2 * math.pi * math.sqrt(L_tot * 4 * C_R))
    V = R.val(R.preset("RA"), "rotor", "ring_amplitude_kV") * 1e3
    I_pk = V * math.sqrt(C_R / L_tot)
    # fields (all four windings, ring current in the chain direction), mu'(f0)
    Tair = L.air_T(A)
    Ttot = Tair + (Tm - T1).real
    i_turn = S.T @ (np.ones(lad.nb) * I_pk)            # loop currents per turn (signed)
    nt = len(A.targets)
    Bz = (Ttot[:nt] @ i_turn)
    Br = (Ttot[nt:] @ i_turn)
    tg = {nm: k for k, (nm, _, _) in enumerate(A.targets)}
    grad = (Bz[tg["ax+1"]] - Bz[tg["ax-1"]]) / 2e-3
    absB = lambda nm: float(math.hypot(Bz[tg[nm]], Br[tg[nm]]))
    # AH alone
    m_ah = np.zeros(len(A.turns))
    for w in ("L_TA", "L_BA"):
        m_ah[A.windings[w]] = 1
    Bz_ah = Ttot[:nt] @ (i_turn * m_ah)
    one = np.zeros(len(A.turns))
    one[A.windings["L_TA"]] = 1
    Bz_one = Ttot[:nt] @ (i_turn * one)
    # axis profile for the null
    zs = np.linspace(-20, 20, 801)
    rt = np.array([t["r"] for t in A.turns]) * 1e-3
    ztn = np.array([t["z"] for t in A.turns]) * 1e-3
    prof_all, prof_ah = [], []
    M1b, _ = ms.solve(1.0, keep_psi=True)
    psi1 = ms.last_psi
    for zq in zs:
        _, bz_air = L.loop_B(rt, 0.0, zq * 1e-3 - ztn)
        bz_core = (ms.B_at(psi_mu, 0.0, zq, "z") - ms.B_at(psi1, 0.0, zq, "z")).real
        bz = bz_air + bz_core
        prof_all.append(bz @ i_turn)
        prof_ah.append(bz @ (i_turn * m_ah))
    prof_all, prof_ah = np.array(prof_all), np.array(prof_ah)

    def null(prof):
        s = np.where(np.sign(prof[:-1]) != np.sign(prof[1:]))[0]
        if not len(s):
            return None
        k = s[np.argmin(np.abs(zs[s]))]
        return float(zs[k] - prof[k] * (zs[k + 1] - zs[k]) / (prof[k + 1] - prof[k]))

    # rod saturation and loss, mu'(f0) real
    Mr, Tr = ms.solve(float(debye(A, f0).real), keep_psi=True)
    psi_r = ms.last_psi @ i_turn
    Bm, vol = ms.rod_B(psi_r)
    Pv = 250e3 * (f0 / 100e3) ** 1.5 * (Bm / 0.1) ** 2.6
    P_st = float(np.sum(Pv * vol))
    N_AH = len(A.windings["L_TA"])
    out = dict(var=var, flipped=flip, L_table_uH=tab, L_tot_uH=L_tot * 1e6, f0_kHz=f0 / 1e3, f0_x4_kHz=f0x4 / 1e3, Z0_ohm=Z0,
               Z0_x4_ohm=math.sqrt(L_tot / (4 * C_R)), mu_f0=[mu.real, mu.imag], R_core_ohm=R_core,
               I_pk_A=I_pk, ring_kV=V / 1e3, Bz_centre_T=float(Bz[tg["centre"]]), grad_centre_T_per_m=float(grad),
               B_pole_A_T=absB("pole_A"), B_pole_B_T=absB("pole_B"), B_eq_wall_T=absB("eq_wall"),
               null_AH_alone_rel=float(abs(Bz_ah[tg["centre"]]) / abs(Bz_one[tg["centre"]])),
               null_offset_all_mm=null(prof_all), null_offset_AH_mm=null(prof_ah),
               rod_B_max_T=float(Bm.max()), rod_B_p99_T=float(np.percentile(Bm, 99)), G_AH_SAT_pass=bool(Bm.max() <= 0.30),
               core_loss_steinmetz_W=P_st, core_loss_mu2_W=0.5 * I_pk ** 2 * R_core,
               N_AH=N_AH, NI_AH=N_AH * I_pk, L_pd=lad.L_pd,
               C_R_record_pF=C_R * 1e12, axis_profile=dict(z_mm=zs[::20].tolist(), Bz_all_T=prof_all[::20].tolist()))
    # P-REG-8: inductive distribution with one uniform chain current
    vb = Lb.real @ np.ones(lad.nb)                     # per-branch drop per unit di/dt
    vnode = {}
    order = list(range(lad.nb))
    pot = np.zeros(lad.nn)
    # walk the chain from R-A
    cur = 0.0
    nodev = {lad.br[0]["a"]: 0.0}
    for k in order:
        b = lad.br[k]
        nodev[b["b"]] = nodev[b["a"]] - vb[k]
    tp = {}
    for k in order:
        b = lad.br[k]
        if b["turn"] is not None:
            tp[b["turn"]] = 0.5 * (nodev[b["a"]] + nodev[b["b"]])
    ta = A.windings["L_TA"]
    br_ta = [k for k in order if lad.br[k]["turn"] in set(ta) or (lad.br[k]["lead"] == "ret_A")]
    V_AH = abs(sum(vb[k] for k in br_ta))
    pairs = []
    for i in ta:
        for j in ta:
            ti, tj = A.turns[i], A.turns[j]
            if tj["layer"] == ti["layer"] + 1 and abs(ti["z"] - tj["z"]) < 0.2:
                pairs.append((abs(tp[i] - tp[j]), i, j))
    pairs.sort()
    vmax, i_, j_ = pairs[-1]
    out["P-REG-8"] = dict(ratio=vmax / V_AH, at_turns=(int(i_), int(j_)), at_absz_mm=abs(A.turns[i_]["z"]),
                          registered=(1.0 if var in "ac" else 2 / 3),
                          rel=(vmax / V_AH) / (1.0 if var in "ac" else 2 / 3) - 1)
    out["P-REG-8"]["pass_"] = abs(out["P-REG-8"]["rel"]) <= 0.25
    log(f"  RA ({var}){' hands flipped' if flip else ''}: L_tot {L_tot * 1e6:.1f} uH, f0 {f0 / 1e3:.1f} kHz (x4 {f0x4 / 1e3:.1f}),"
        f" Z0 {Z0:.0f} Ohm, I_pk {I_pk:.2f} A, N.I {N_AH * I_pk:.0f} At; grad {grad:.3f} T/m, |B| pole {absB('pole_B') * 1e3:.2f} mT,"
        f" wall {absB('eq_wall') * 1e3:.2f} mT; null AH-alone {out['null_AH_alone_rel']:.1e}, offset all {out['null_offset_all_mm']} mm;"
        f" rod B max {Bm.max():.3f} T; P-REG-8 {vmax / V_AH:.3f}")
    return out, A, ms


def p_reg_9(mag):
    a, c = mag["a"]["NI_AH"], mag["c"]["NI_AH"]
    return dict(NI_a=a, NI_c=c, ratio_c_over_a=c / a, Ltot_ratio_a_over_c=mag["a"]["L_tot_uH"] / mag["c"]["L_tot_uH"],
                verdict="PASS" if c < a else "KILL")


def t_mirror(var, base, log=print):
    fl, _, _ = magnetics(var, log=log, flip=True)
    scal = ("L_tot_uH", "f0_kHz", "Z0_ohm", "I_pk_A", "B_pole_A_T", "B_pole_B_T", "B_eq_wall_T", "rod_B_max_T",
            "core_loss_steinmetz_W", "null_offset_all_mm")
    rel = {k: (abs(fl[k] - base[k]) / max(abs(base[k]), 1e-30)) if base[k] is not None else None for k in scal}
    tab_rel = max(abs(fl["L_table_uH"][a][b] - base["L_table_uH"][a][b]) / max(abs(base["L_table_uH"][a][b]), 1e-30)
                  for a in base["L_table_uH"] for b in base["L_table_uH"][a] if abs(base["L_table_uH"][a][b]) > 1e-9)
    Bflip = (fl["Bz_centre_T"] + base["Bz_centre_T"]) / max(abs(base["Bz_centre_T"]), 1e-30)
    gflip = (fl["grad_centre_T_per_m"] + base["grad_centre_T_per_m"]) / max(abs(base["grad_centre_T_per_m"]), 1e-30)
    ok = all(v is None or v <= 1e-12 for v in rel.values()) and tab_rel <= 1e-12 and abs(Bflip) <= 1e-12 and abs(gflip) <= 1e-12
    log(f"  T-MIRROR ({var}): max scalar rel {max(v for v in rel.values() if v is not None):.1e}, L table {tab_rel:.1e},"
        f" B_z sum {Bflip:.1e}, gradient sum {gflip:.1e} -> {'PASS' if ok else 'FAIL'}")
    return dict(scalar_rel=rel, L_table_rel=tab_rel, Bz_sum_rel=Bflip, grad_sum_rel=gflip, pass_=ok,
                note="for axisymmetric parts the theta -> -theta mirror and the all-hands flip are the same operation")


# ---------------------------------------------------------------------------------------------------------
# edge runs
# ---------------------------------------------------------------------------------------------------------
def front(r, lad, branches, t50, tr, frac=0.5):
    t = r["t"]
    it = r["i_s"][:, 0]
    w = (t > t50 + 2 * tr) & (t < t50 + 4 * tr)
    I = float(np.median(it[w]))
    arr = []
    for k in branches:
        hit = np.where(r["i"][:, k] * np.sign(I) > frac * abs(I))[0]
        arr.append(t[hit[0]] - t50 if len(hit) else np.nan)
    arr = np.array(arr)
    N = len(branches)
    ks = np.arange(1, max(3, N // 4))
    ok = np.isfinite(arr[ks])
    if ok.sum() < 2:
        return dict(tau=float("nan"), Z0=1.0 / I if I else float("nan"), I_early=I, r2=float("nan"))
    sl, ic = np.polyfit(ks[ok], arr[ks][ok], 1)
    pred = sl * ks[ok] + ic
    r2 = 1 - np.sum((arr[ks][ok] - pred) ** 2) / max(np.sum((arr[ks][ok] - arr[ks][ok].mean()) ** 2), 1e-40)
    return dict(tau=float(sl * N), Z0=1.0 / I, I_early=I, r2=float(r2))


def front_posthoc(r, lad, branches, t50, t_win=30e-9, frac=0.5):
    """POST-HOC (not pre-registered): arrival at turn k = first time |i_k| reaches frac of its own max over
    (0, t_win); tau = N x slope over turns 2 .. N/4. Normalising per turn follows a front that attenuates and works
    when a second front starts at the far end."""
    t = r["t"]
    w = (t >= t50) & (t <= t50 + t_win)
    arr = []
    for k in branches:
        x = np.abs(r["i"][w, k])
        hit = np.where(x >= frac * x.max())[0]
        arr.append(t[w][hit[0]] - t50 if len(hit) else np.nan)
    arr = np.array(arr)
    N = len(branches)
    ks = np.arange(1, max(3, N // 4))
    ok = np.isfinite(arr[ks])
    if ok.sum() < 2:
        return dict(tau=float("nan"), r2=float("nan"), arrival_ns=(arr * 1e9).tolist())
    sl, ic = np.polyfit(ks[ok], arr[ks][ok], 1)
    pred = sl * ks[ok] + ic
    r2 = 1 - np.sum((arr[ks][ok] - pred) ** 2) / max(np.sum((arr[ks][ok] - arr[ks][ok].mean()) ** 2), 1e-40)
    return dict(tau=float(sl * N), r2=float(r2), arrival_ns=(arr * 1e9).tolist())


def stress(A, lad, r, t50, t_hi, which):
    """section voltages (winding order) and physical-neighbour voltages for the turns of `which`, max over (0, t_hi)."""
    t = r["t"]
    w = (t >= t50) & (t <= t50 + t_hi)
    v = r["v"]
    tp = lad.turn_potential(v)
    secs = [k for k, b in enumerate(lad.br) if b["turn"] in set(which)]
    sv = []
    for k in secs:
        b = lad.br[k]
        va = v[:, b["a"]] if b["a"] >= 0 else 0 * t
        vb = v[:, b["b"]] if b["b"] >= 0 else 0 * t
        sv.append(float(np.abs(va - vb)[w].max()))
    sv = np.array(sv)
    pairs = []
    ws = list(which)
    for x in range(len(ws)):
        for y in range(x + 1, len(ws)):
            ti, tj = A.turns[ws[x]], A.turns[ws[y]]
            d = math.hypot(ti["r"] - tj["r"], ti["z"] - tj["z"])
            if d < 1.25 * 2 * max(ti["rc"], 0.8) + 0.3:
                kind = "layer" if ti["layer"] != tj["layer"] else "turn"
                pairs.append((float(np.abs(tp[w, ws[x]] - tp[w, ws[y]]).max()), kind, ws[x], ws[y]))
    best = {}
    for val, kind, i, j in pairs:
        if kind not in best or val > best[kind][0]:
            best[kind] = (val, i, j)
    N = len(secs)
    kmax = int(sv.argmax())
    return dict(section_max_per_V=float(sv.max()), section=kmax + 1, N=N, first_tenth=bool(kmax + 1 <= max(1, N // 10)),
                neighbour={k: dict(V_per_V=v_[0], turns=(int(v_[1]), int(v_[2])), rz_mm=[(A.turns[v_[1]]["r"], A.turns[v_[1]]["z"]),
                                                                                       (A.turns[v_[2]]["r"], A.turns[v_[2]]["z"])])
                           for k, v_ in best.items()})


def run_edge(A, es, core, tr, t_end, h, name, Rs=0.0, log=print):
    lad = L.Ladder(A, es, core=core, Rs=Rs)
    vs, t50 = EC.edge(tr)
    t0 = time.time()
    r = lad.transient(vs, t_end, h)
    os.makedirs(RAW, exist_ok=True)
    lad.save(os.path.join(RAW, name + ".npz"), r, dict(name=name, tr=tr, h=h, t50=t50, Rs=Rs, assembly=A.name, meta=A.meta,
                                                       L_pd=lad.L_pd))
    log(f"  edge {name}: {len(r['t'])} steps, h {h * 1e12:.0f} ps, {time.time() - t0:.0f} s, L_pd {lad.L_pd}")
    return lad, r, t50


def bench(var="a", n_per_layer=None, layers=None, rod=True, mu=None, tr=TR, Rs=0.0, name=None, log=print, span=None,
          t_mult=4.0, cache={}):
    B = L.bench_assembly(var, n_per_layer, layers, rod, mu, span_mm=span)
    key = B.name
    if key not in cache:
        es = L.es_extract(B, log=log)
        ms = L.MS(B) if rod else None
        cache[key] = (es, ms, {})
    es, ms, cores = cache[key]
    core = None
    if rod:
        mk = "debye" if mu is None else float(mu)
        if mk not in cores:
            if mu is None:
                g = dict(mu_i=B.mu["mu_i"], f_r=B.mu["f_r"])
                cores[mk] = EC.core_fit(ms, g, log=log)
            elif float(mu) != 1.0:
                cores[mk] = dict(static=L.core_increment(B, ms, float(mu)))
            else:
                cores[mk] = None
        core = cores[mk]
    N = B.meta["N"]
    tau_g = 20e-9 * (N / 50) * (2.0 if (mu or 1) > 1 else 1.0)
    h = min(tr / 50, 2.5e-11)
    name = name or f"bench_{var}_{n_per_layer}_{layers}_{'rod' if rod else 'norod'}_{mu}_{tr:.1e}_{Rs:g}"
    lad, r, t50 = run_edge(B, es, core, tr, t50_end(tr) + t_mult * max(tau_g, 4 * tr), h, name, Rs=Rs, log=log)
    chain = [k for k, b in enumerate(lad.br) if b["turn"] is not None]
    return B, lad, r, t50, chain


def t50_end(tr):
    return EC.edge(tr)[1]


def bench_readouts(B, lad, r, t50, chain, tr):
    fr = front(r, lad, chain, t50, tr)
    tau = fr["tau"]
    t = r["t"]
    it = r["i_s"][:, 0]
    w = (t >= t50) & (t <= t50 + 1.5 * tau)
    Bc = r["B"][:, 0, :].sum(axis=1)
    flat = float(np.interp(t50 + 1.6 * tau, t, it) / np.interp(t50 + 0.4 * tau, t, it))
    out = dict(tau=tau, Z0=fr["Z0"], r2=fr["r2"], valid=bool(fr["r2"] >= 0.9), flat=flat,
               B_peak_fill=float(np.abs(Bc[w]).max()) if w.any() else float("nan"),
               tr_over_tau=tr / tau, tr_over_tau_turn=tr / (tau / len(chain)), t_end_over_tau=(t[-1] - t50) / tau)
    ph = front_posthoc(r, lad, chain, t50)
    tp = ph["tau"]
    nan = float("nan")
    if not (tp > 0):
        out["posthoc"] = dict(tau=tp, r2=ph["r2"], valid=False, flat=nan, B_peak_fill=nan, tr_over_tau=nan, tr_over_tau_turn=nan,
                              t_end_over_tau=nan)
        return out
    wp = (t >= t50) & (t <= t50 + 1.5 * tp)
    out["posthoc"] = dict(tau=tp, r2=ph["r2"], valid=bool(ph["r2"] >= 0.9),
                          flat=float(np.interp(t50 + 1.6 * tp, t, it) / np.interp(t50 + 0.4 * tp, t, it)),
                          B_peak_fill=float(np.abs(Bc[wp]).max()) if wp.any() else nan, tr_over_tau=tr / tp,
                          tr_over_tau_turn=tr / (tp / len(chain)), t_end_over_tau=(t[-1] - t50) / tp)
    return out


def _tau_use(rd):
    if rd["valid"] and rd["tau"] > 0:
        return rd["tau"]
    if rd["posthoc"].get("valid") and rd["posthoc"]["tau"] > 0:
        return rd["posthoc"]["tau"]
    return 15e-9


def fit_pow(x, y):
    x, y = np.asarray(x, float), np.asarray(y, float)
    if not np.all(np.isfinite(y)) or np.any(y <= 0):
        return float("nan")
    return float(np.polyfit(np.log(x), np.log(y), 1)[0])


def bench_all(log=print):
    out = {}
    # P-EDGE-1, 4 (real rod) and E-REGIME per variant / edge
    reg = []
    for var in VARS:
        for tr in (0.5e-9, 1e-9, 2e-9, 5e-9):
            B, lad, r, t50, chain = bench(var, tr=tr, log=log)
            rd = bench_readouts(B, lad, r, t50, chain, tr)
            if tr == TR:
                st = stress(B, lad, r, t50, _tau_use(rd), B.windings["AH"])
                out[f"bench_{var}"] = dict(readout=rd, stress=st, N=B.meta["N"])
                if var == "a":
                    v1 = ("PASS" if rd["flat"] <= 1.5 else ("KILL" if rd["flat"] >= 3 else "INCONCLUSIVE")) if rd["valid"] else "READOUT INVALID (front fit r2 < 0.9)"
                    pf = rd["posthoc"]["flat"]
                    out["P-EDGE-1"] = dict(**rd, verdict=v1, verdict_posthoc="PASS" if pf <= 1.5 else ("KILL" if pf >= 3 else "INCONCLUSIVE"))
                    out["P-EDGE-4"] = dict(**st, verdict="PASS" if st["first_tenth"] else "KILL")
            if tr == 0.5e-9:
                st05 = stress(B, lad, r, t50, _tau_use(rd), B.windings["AH"])
                out[f"bench_{var}_tr0p5"] = dict(readout=rd, stress=st05)
            reg.append(dict(family=f"AH ({var})", t_r=tr, tau=rd["tau"], r2=rd["r2"], valid=rd["valid"], tr_over_tau=rd["tr_over_tau"],
                            tr_over_tau_turn=rd["tr_over_tau_turn"], posthoc=rd["posthoc"]))
            log(f"  bench ({var}) t_r {tr * 1e9:g} ns: tau {rd['tau'] * 1e9:.2f} ns (r2 {rd['r2']:.3f}), Z0 {rd['Z0']:.0f}, flat {rd['flat']:.2f};"
                f" post-hoc tau {rd['posthoc']['tau'] * 1e9:.2f} ns (r2 {rd['posthoc']['r2']:.3f}), flat {rd['posthoc']['flat']:.2f}")
    out["E-REGIME_AH"] = reg
    # P-EDGE-2: 2 layers x {10, 13, 18, 25} over 40 mm, mu = 1
    rows = []
    for n in (10, 13, 18, 25):
        B, lad, r, t50, chain = bench("a", n_per_layer=n, layers=2, mu=1.0, span=40.0, log=log)
        rd = bench_readouts(B, lad, r, t50, chain, TR)
        rows.append(dict(n_per_layer=n, n_per_m=n / 0.04, **rd))
    beta = fit_pow([x["n_per_m"] for x in rows], [x["B_peak_fill"] for x in rows])
    bp = fit_pow([x["n_per_m"] for x in rows], [x["posthoc"]["B_peak_fill"] for x in rows])
    vb = ("PASS" if abs(beta) < 0.3 else ("KILL" if beta > 0.7 else "INCONCLUSIVE")) if all(x["valid"] for x in rows) else "READOUT INVALID"
    out["P-EDGE-2"] = dict(beta=beta, beta_posthoc=bp, rows=rows, verdict=vb,
                           verdict_posthoc="PASS" if abs(bp) < 0.3 else ("KILL" if bp > 0.7 else "INCONCLUSIVE"))
    log(f"P-EDGE-2 {out['P-EDGE-2']['verdict']}: beta {beta:+.3f}; post-hoc {bp:+.3f} {out['P-EDGE-2']['verdict_posthoc']}")
    rows = []
    for mu in (1.0, 4.0, 16.0, 64.0):
        B, lad, r, t50, chain = bench("a", mu=mu, log=log)
        rd = bench_readouts(B, lad, r, t50, chain, TR)
        rows.append(dict(mu=mu, **rd))
    gam = fit_pow([x["mu"] for x in rows], [x["B_peak_fill"] for x in rows])
    gp = fit_pow([x["mu"] for x in rows], [x["posthoc"]["B_peak_fill"] for x in rows])
    vg = ("PASS" if 0.35 < gam < 0.65 else ("KILL" if gam > 0.85 else "INCONCLUSIVE")) if all(x["valid"] for x in rows) else "READOUT INVALID"
    out["P-EDGE-3"] = dict(gamma=gam, gamma_posthoc=gp, rows=rows, verdict=vg,
                           verdict_posthoc="PASS" if 0.35 < gp < 0.65 else ("KILL" if gp > 0.85 else "INCONCLUSIVE"))
    log(f"P-EDGE-3 {out['P-EDGE-3']['verdict']}: gamma {gam:.3f}; post-hoc {gp:.3f} {out['P-EDGE-3']['verdict_posthoc']}")
    # P-EDGE-6/7: 50 Ohm TDR read through the current, with and without the rod
    res67 = {}
    for rod in (True, False):
        B, lad, r, t50, chain = bench("a", rod=rod, mu=None if rod else 1.0, Rs=50.0, log=log)
        t = r["t"]
        vt = r["v"][:, lad.src[0]["term"]]
        vsrc = r["v"][:, lad.src[0]["node"]]
        it = (vsrc - vt) / 50.0
        rr = dict(r, i_s=it[:, None])
        fr = front(rr, lad, chain, t50, TR)
        w = (t > t50 + 2 * TR) & (t < t50 + 4 * TR)
        Z0 = float(np.median(vt[w]) / np.median(it[w]))
        Bc = r["B"][:, 0, :].sum(1)
        wf = (t >= t50) & (t <= t50 + 1.5 * fr["tau"])
        fp = front_posthoc(rr, lad, chain, t50)
        res67["rod" if rod else "norod"] = dict(Z0=Z0, tau=fr["tau"], r2=fr["r2"], tau_posthoc=fp["tau"], r2_posthoc=fp["r2"],
                                                L_seen_posthoc=Z0 * fp["tau"], C_seen_posthoc=fp["tau"] / Z0,
                                                L_seen=Z0 * fr["tau"], C_seen=fr["tau"] / Z0,
                                                B_centre_fill_per_V=float(np.abs(Bc[wf]).max()), B_centre_record_per_V=float(np.abs(Bc).max()))
    kL = res67["rod"]["L_seen"] / res67["norod"]["L_seen"]
    kC = res67["rod"]["C_seen"] / res67["norod"]["C_seen"]
    out["P-EDGE-6"] = dict(registered_ladder_values=res67["rod"], verdict="REGISTERED (bench data pending)")
    kLp = res67["rod"]["L_seen_posthoc"] / res67["norod"]["L_seen_posthoc"]
    kCp = res67["rod"]["C_seen_posthoc"] / res67["norod"]["C_seen_posthoc"]
    valid7 = res67["rod"]["r2"] >= 0.9 and res67["norod"]["r2"] >= 0.9
    out["P-EDGE-7"] = dict(L_ratio=kL, C_ratio=kC, L_ratio_posthoc=kLp, C_ratio_posthoc=kCp, rod=res67["rod"], norod=res67["norod"],
                           verdict=("PASS (ladder)" if kC > kL else "KILL (ladder)") if valid7 else "READOUT INVALID",
                           verdict_posthoc="PASS (ladder)" if kCp > kLp else "KILL (ladder)")
    log(f"P-EDGE-6 registered: Z0 {res67['rod']['Z0']:.0f} Ohm, tau {res67['rod']['tau'] * 1e9:.2f} ns; P-EDGE-7: C x{kC:.2f}, L x{kL:.2f}")
    return out


_CORE = {}


def edge_all(mag, bench_out, log=print):
    out = {}
    for var in VARS:
        rd_ = bench_out[f"bench_{var}"]["readout"]
        tauAH = _tau_use(rd_)
        for stator in (True, False):
            A = L.ra_assembly(var, stator)
            es = L.es_extract(A, log=log)
            if var not in _CORE:
                ms = L.MS(A)
                _CORE[var] = EC.core_fit(ms, dict(mu_i=A.mu["mu_i"], f_r=A.mu["f_r"]), log=log)
            core = _CORE[var]
            flank = 2 * TR + tauAH
            t_end = EC.edge(TR)[1] + max(3 * flank, 40e-9)
            name = f"ra_{var}_{'stator' if stator else 'nostator'}"
            lad, r, t50 = run_edge(A, es, core, TR, t_end, 2.5e-11, name, log=log)
            t = r["t"]
            wins = r["windings"]
            ix = {w: k for k, w in enumerate(wins)}
            c = 0                                                   # target 'centre'
            BTA, BBA = r["B"][:, c, ix["L_TA"]], r["B"][:, c, ix["L_BA"]]
            Ball = r["B"][:, c, :].sum(1)

            def ratio(t_hi):
                w = (t >= t50) & (t <= t50 + t_hi)
                return float(np.abs((BTA + BBA)[w]).max() / max(np.abs(BTA[w]).max(), np.abs(BBA[w]).max()))

            rows = dict(flank_s=flank, tau_AH_source=("registered front" if rd_["valid"] else ("post-hoc front (registered readout invalid)"
                        if rd_["posthoc"].get("valid") else "15 ns default (both front readouts invalid)")),
                        ratio_flank=ratio(flank), ratio_tr=ratio(TR), ratio_10ns=ratio(10e-9),
                        Bz_centre_all_peak_per_kV=float(np.abs(Ball[(t >= t50) & (t <= t50 + flank)]).max() * 1e3),
                        Bz_centre_AH_peak_per_kV=float(np.abs((BTA + BBA)[(t >= t50) & (t <= t50 + flank)]).max() * 1e3),
                        C_R_extracted_pF=float(-es["C"][es["names"].index("R-A"), es["names"].index("R-B")] * 1e12),
                        core_fit_err=core["errL"], override=es["override"], L_pd=lad.L_pd)
            rows["P-REG-5_true"] = rows["ratio_flank"] > 0.10
            # stress: AH top (driven side) and TC
            rows["stress_TA"] = stress(A, lad, r, t50, flank, A.windings["L_TA"])
            rows["stress_TC"] = stress(A, lad, r, t50, flank, A.windings["L_TC"])
            tcb = [k for k, b in enumerate(lad.br) if b["turn"] in set(A.windings["L_TC"])]
            rows["front_TC"] = front(r, lad, tcb, t50, TR)
            rows["front_TC_posthoc"] = {k: v for k, v in front_posthoc(r, lad, tcb, t50).items() if k != "arrival_ns"}
            vR = r["v"][:, lad.nodes["R-B"]]
            rows["V_RB_over_V_RA_flank_min"] = float(vR[(t >= t50 + TR) & (t <= t50 + flank)].min())
            out[name] = rows
            log(f"  {name}: P-REG-5 ratio |B_TA+B_BA|/max {rows['ratio_flank']:.3f} (t_r {rows['ratio_tr']:.3f}, 10 ns"
                f" {rows['ratio_10ns']:.3f}); centre {rows['Bz_centre_all_peak_per_kV'] * 1e6:.2f} uT/kV; AH stress: section"
                f" {rows['stress_TA']['section_max_per_V']:.3f} V/V, neighbour {json.dumps({k: round(v['V_per_V'], 3) for k, v in rows['stress_TA']['neighbour'].items()})};"
                f" C_R {rows['C_R_extracted_pF']:.0f} pF; V_RB/V_RA min {rows['V_RB_over_V_RA_flank_min']:.3f}")
    ok = all(v["P-REG-5_true"] for v in out.values())
    out["P-REG-5"] = dict(verdict="PASS" if ok else ("KILL" if not any(v["P-REG-5_true"] for v in out.values() if isinstance(v, dict) and "P-REG-5_true" in v) else "MIXED"))
    return out


def late_layer_voltage(var, log=print):
    """the ladder's late-time adjacent-layer voltage (P-REG-8 cross-check): R-A driven against R-B (grounded), 100 ns
    edge, read at 400-500 ns (inductive regime: well below a quarter period at f0)."""
    A = L.ra_assembly(var, False)
    A.sources = [("R-A", 1.0)]
    A.cond = [c if c["node"] != "R-B" else dict(c, node="gnd") for c in A.cond]
    es = L.es_extract(A, log=log)
    ms = L.MS(A)
    dL, dT = L.core_increment(A, ms, 2000.0)
    lad = L.Ladder(A, es, core=dict(static=(dL, dT)))
    vs, t50 = EC.edge(100e-9)
    r = lad.transient(vs, 500e-9, 2e-10)
    t = r["t"]
    w = (t >= 400e-9)
    tp = lad.turn_potential(r["v"])[w].mean(0)
    ta = A.windings["L_TA"]
    brs = [k for k, b in enumerate(lad.br) if b["turn"] in set(ta) or b["lead"] == "ret_A"]
    v = r["v"][w].mean(0)
    VAH = abs(sum((v[lad.br[k]["a"]] if lad.br[k]["a"] >= 0 else 0) - (v[lad.br[k]["b"]] if lad.br[k]["b"] >= 0 else 0) for k in brs))
    best = 0
    for i in ta:
        for j in ta:
            if A.turns[j]["layer"] == A.turns[i]["layer"] + 1 and abs(A.turns[i]["z"] - A.turns[j]["z"]) < 0.2:
                best = max(best, abs(tp[i] - tp[j]))
    log(f"  late-time ({var}): adjacent-layer {best / VAH:.3f} V_AH")
    return dict(ratio=best / VAH)


if __name__ == "__main__":
    what = sys.argv[1] if len(sys.argv) > 1 else "all"
    res = json.load(open(R.RESULTS)).get("ra", {}) if os.path.exists(R.RESULTS) else {}
    if what in ("magnetics", "all"):
        mag = {}
        for var in VARS:
            mag[var], A, ms = magnetics(var)
        res["magnetics"] = mag
        res["P-REG-9"] = p_reg_9(mag)
        res["T-MIRROR"] = t_mirror("a", mag["a"])
        res["late_layer"] = {v: late_layer_voltage(v) for v in VARS}
        R.save(dict(ra=res, ra_magnetics={v: dict(L_tot_uH=mag[v]["L_tot_uH"]) for v in VARS}))
    if what in ("bench", "all"):
        res["bench"] = bench_all()
        R.save(dict(ra=res))
    if what in ("edge", "all"):
        res["edge"] = edge_all(res.get("magnetics"), res["bench"])
        R.save(dict(ra=res))
    print("->", R.RESULTS)
