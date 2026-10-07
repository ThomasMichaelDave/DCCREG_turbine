"""sim/pole_design.py -- design / optimisation of the reluctance pole pair for the magnetic doubler (wound utrons on the
rotor, passive stator iron), stage by stage:

P1 screen: 2-D field solve of each candidate (sim/pole_fd2d.py) -> L(theta), ratio kappa_L, tau = L/R, then the doubler's
   gain per cycle z with the REAL L(theta) shape at the candidate's own frequency (sim/magnetic_doubler.py, linear, copper
   in every coil; fixed inductors La / Lb at TAU_FIXED). Families:
     S: 6 discrete stator bridges per side (the C-EMs as passive iron), 60 Hz at 600 rpm relative;
     T: a toothed stator ring (N_s teeth per rev), tips with n_t teeth, 10 N_s Hz.
P2 size: stack length, winding window, the saturable neck (Psi_s), the utron turns vs the AH winding, heat per coil
   in air and in vacuum, iron loss.
P3 the chosen pole pair in the saturating doubler with the AH pair, against the AH target; the 0.5 mm vs 1.0 mm gap.

Usage: python3 sim/pole_design.py p1 | p2 | p3      (writes sim/pole_design_<stage>.json)
"""
import json
import math
import os
import sys
from multiprocessing import Pool

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import pole_fd2d as P                    # noqa: E402
import magnetic_doubler as M             # noqa: E402

TAU_FIXED = 0.5                          # fixed coupling inductors: large gapped cores, not geometry-bound [RH]
N_THETA = 13
K_FIT = 6


def fit_cos(theta, L, period):
    """least-squares cosine series of L/L(0) over a half period (L symmetric about alignment)."""
    th = np.asarray(theta) * 2 * math.pi / period
    y = np.asarray(L) / L[0]
    A = np.stack([np.cos(k * th) for k in range(K_FIT + 1)], axis=1)
    a, *_ = np.linalg.lstsq(A, y, rcond=None)
    return list(a), float(np.abs(A @ a - y).max())


def s_family():
    out = []
    for g in (0.5, 0.75, 1.0):
        for w_p in (12.0, 16.0, 20.0):
            for s in (20.0, 30.0, 40.0):
                if 2 * w_p + s > 72.0:                       # unaligned isolation inside the 60 deg pitch
                    continue
                for d in (40.0, 60.0):
                    out.append(dict(kind="S", g=g, w_p=w_p, s=s, d=d))
    return out


def t_family():
    out = []
    for g in (0.5, 1.0):
        for N_s in (12, 18, 24, 36):
            p = 2 * math.pi * P.R_G / N_s
            for n_t in (1, 2):
                tw = 0.42 * p
                w_p = (n_t - 1) * p + tw + 1.0
                m = 1                                        # tooth centres on stator teeth: m = n_t - 1 (mod 2)
                while m * p - w_p < 20.0 or (m - n_t + 1) % 2:
                    m += 1
                s = m * p - w_p
                if 2 * w_p + s > 0.9 * P.R_G * math.radians(P.DOMAIN_DEG):
                    continue
                if w_p > 50.0:
                    continue
                bfl = round(n_t * tw + 2.0, 3)               # back iron / ring sized for the flux of n_t teeth
                out.append(dict(kind="T", g=g, N_s=N_s, n_t=n_t, w_p=round(w_p, 4), s=round(s, 4), d=50.0, b=bfl,
                                t_ring=bfl))
    return out


def s_refine():
    """P1b: discrete bridges, gap radius free, radial space and unaligned isolation enforced."""
    out = []
    for g in (0.5, 1.0):
        for r_g in (130.0, 165.0):
            pitch = 2 * math.pi * r_g / 6
            for w_p in (14.0, 16.0, 18.0, 20.0, 24.0):
                for s in (30.0, 40.0, 50.0):
                    if 2 * w_p + s > 0.53 * pitch:
                        continue
                    for d in (40.0, 50.0, 60.0):
                        D = P.Design(kind="S", g=g, w_p=w_p, s=s, d=d, r_g=r_g)
                        if D.fits():
                            out.append(dict(kind="S", g=g, w_p=w_p, s=s, d=d, r_g=r_g))
    return out


def p1b():
    cands = s_refine() + [c for c in t_family()]
    print(f"P1b: {len(cands)} candidates x {N_THETA} angles", flush=True)
    with Pool(4) as pool:
        chars = pool.map(_char, cands)
    rows = []
    for r in chars:
        a, err = fit_cos(r["theta"], r["L_per_n2"], 360.0 / r["cyc_per_rev"])
        r["prof"], r["fit_err"] = a, err
        rows.append(r)
    with Pool(4) as pool:
        zs = pool.map(_z, rows)
    for r, z in zip(rows, zs):
        r.update(z)
        d = r["design"]
        print(f"{d['kind']} g {d['g']:4.2f} r_g {r['r_g']:5.0f} w_p {d['w_p']:5.1f} s {d['s']:5.1f} d {d.get('d', 50):4.0f}"
              + (f" N_s {d['N_s']:2d} n_t {d['n_t']}" if d['kind'] == 'T' else "              ")
              + f" | kappa {r['kappa']:6.2f} tau {r['tau']:.3f} s f {r['f_Hz']:4.0f} Hz depth {r['radial_depth_mm']:5.1f}"
              f" fits {r['fits']} | z {r['z'] if r['z'] is None else round(r['z'], 4)}", flush=True)
    json.dump(dict(stage="p1b", tau_fixed=TAU_FIXED, rows=rows), open(os.path.join(HERE, "pole_design_p1b.json"), "w"),
              indent=1, default=float)


# ---------------------------------------------------------------- P2 / P3: sizing and the AH-loaded steady state
AT_TARGET = 450.0                        # AH ampere-turns peak (rod limit ~600 at 0.30 T: 25 % margin) [IR]
B_SAT = 1.5                              # neck flux density at the knee, M235-35A [RH]
RHO_FE = 7650.0
P_FE_50 = 2.35                           # W/kg at 1.5 T, 50 Hz, M235-35A (max spec) [RH]
H_AIR, DT_AIR = 25.0, 100.0              # W/m^2K forced by the rotation, class-F rise [RH]
EPS_RAD, T_COIL, T_AMB = 0.85, 428.0, 313.0
SIGMA = 5.670e-8


def with_stack(r, L_stk):
    """rescale a characterised design to another stack length (2-D L ~ L_stk; R' via the mean turn)."""
    d = r["design"]
    k = L_stk / P.Design(**d).L_stk
    D = P.Design(**dict(d, L_stk=L_stk))
    plus, minus, a_coil = D.coil_rects()
    h_c = plus[3] - plus[2]
    l_turn = 2 * (D.L_stk + D.b) + math.pi * (h_c / 2 + D.clr) + 4 * D.clr
    rp = P.RHO_CU * l_turn * 1e-3 / (P.FILL * a_coil * 1e-6)
    out = dict(r, L_al=r["L_al"] * k, L_un=r["L_un"] * k, R_per_n2=rp, l_turn_mm=l_turn, tau=r["L_al"] * k / rp,
               L_stk=L_stk, h_c=h_c, axial_mm=L_stk + 2 * h_c, design=dict(d, L_stk=L_stk))
    return out


def thermal(r, n_coils_side=3):
    D = P.Design(**r["design"])
    plus, minus, a_coil = D.coil_rects()
    wc, h_c = plus[1] - plus[0], plus[3] - plus[2]
    # exposed coil surface: the slot side's top, the return side's bottom, both end-turn bundles (mm^2)
    A = 2 * wc * D.L_stk + 2 * 2 * (wc + h_c) * h_c + 2 * h_c * D.L_stk * 0.5
    A_m2 = A * 1e-6
    return dict(A_coil_m2=A_m2, P_air_max_W=H_AIR * A_m2 * DT_AIR,
                P_vac_max_W=SIGMA * EPS_RAD * A_m2 * (T_COIL ** 4 - T_AMB ** 4))


def iron_loss(r, f):
    D = P.Design(**r["design"])
    vol_u = (2 * D.w_p * D.d + D.W_u * D.b) * D.L_stk                # mm^3 per utron
    vol_b = D.l_b * D.t_b * D.L_stk                                  # per bridge
    m_u, m_b = vol_u * 1e-9 * RHO_FE, vol_b * 1e-9 * RHO_FE
    pk = P_FE_50 * (f / 50.0) ** 1.3                                 # W/kg at 1.5 T [RH]
    return dict(m_utron_kg=m_u, m_bridge_kg=m_b, P_fe_side_W=pk * (3 * m_u + 6 * m_b * 0.5))   # bridges: unipolar


def p3_eval(r, N_u, ah, la_ratio=M.R_CA, n_cyc=None):
    """saturating doubler with the AH pair, one run at a reference Psi_s, rescaled to the AH target (exact: the model
    scales linearly with Psi_s)."""
    Lmax = 3 * N_u ** 2 * r["L_al"]                                  # 3 utrons per group in series
    h = dict(M.AH[ah])
    prof = r["prof"]
    psi0 = 3 * N_u * B_SAT * (r["design"]["w_p"] * r["design"]["L_stk"] * 1e-6) * 0.6
    z = r.get("z_lin")
    n = n_cyc or int(math.ceil(math.log(1000.0) / math.log(max(z or 1.1, 1.04)))) + 20     # grow x1000, then settle
    kw = dict(prof=prof, tau=r["tau"], tau_fixed=TAU_FIXED, sat=True, F=r["f_Hz"], n_cyc=n, L_max=Lmax, psi_s=psi0,
              la_ratio=la_ratio, ah="custom", ah_custom=h, seed=1e-3 * psi0 / Lmax)
    m = M.run(**kw)
    m.pop("wave", None)
    if "AH_AT_pk" not in m:
        return dict(N_u=N_u, ah=ah, la_ratio=la_ratio, ok=False, z_early=m.get("z_early"), err=m.get("error"))
    k = AT_TARGET / m["AH_AT_pk"]
    psi_s = psi0 * k
    neck_mm = psi_s / (3 * N_u * B_SAT * r["design"]["L_stk"] * 1e-3) * 1e3       # back-iron width that saturates
    out = dict(N_u=N_u, ah=ah, la_ratio=la_ratio, ok=True, z_early=m["z_early"], z_late=m["z_late"],
               psi_s=psi_s, neck_mm=neck_mm, I_pk=m["I1_pk"] * k, I_rms=m["I1_rms"] * k,
               P_cu_utron_W=m["P_cu_utron_W"] * k * k, P_cu_fixed_W=m["P_cu_fixed_W"] * k * k, P_AH_W=m["P_AH_W"] * k * k,
               P_snub_W=m["P_snub_W"] * k * k, P_belt_el_W=m["P_belt_W"] * k * k, AT_pk=AT_TARGET,
               AT_min=m["AH_AT_min"] * k, L_group_H=Lmax, n_cyc=n)
    out["P_per_utron_coil_W"] = out["P_cu_utron_W"] / 6.0
    wire_mm2 = P.FILL * r["a_coil_mm2"] / N_u
    out.update(wire_mm2=wire_mm2, J_A_mm2=out["I_rms"] / wire_mm2,
               V_group_pk_V=2 * math.pi * r["f_Hz"] * psi_s)                # ~ the group's peak winding voltage
    return out


def p3():
    rows = json.load(open(os.path.join(HERE, "pole_design_p1b.json")))["rows"]
    good = [r for r in rows if r["design"]["kind"] == "S" and r["fits"] and r.get("z")]
    pick = {}
    for g in (0.5, 1.0):
        pick[g] = max([r for r in good if r["design"]["g"] == g], key=lambda r: r["z"])
    # the g 0.5 winner's geometry with a 1.0 mm gap (same hardware, wider gap)
    same = dict(pick[0.5]["design"], g=1.0)
    rr = P.characterise(P.Design(**same), n_theta=N_THETA)
    rr["design"] = same
    rr["prof"], rr["fit_err"] = fit_cos(rr["theta"], rr["L_per_n2"], 360.0 / rr["cyc_per_rev"])
    rr.update(_z(rr))
    sets = {"best g 0.5": pick[0.5], "g 0.5 geometry at 1.0 mm": rr}
    if pick[1.0]["design"] != same:
        sets["best g 1.0"] = pick[1.0]
    out = dict(stage="p3", AT_target=AT_TARGET, tau_fixed=TAU_FIXED, designs={})
    for tag, r0 in sets.items():
        print(f"\n== {tag}: {r0['design']}  kappa {r0['kappa']:.2f}, z(L_stk 100) {r0['z']}", flush=True)
        stacks = []
        for L in (70.0, 100.0, 140.0):
            r = with_stack(r0, L)
            z = _z(r)
            r.update(z_lin=z["z"])
            stacks.append(r)
            print(f"  L_stk {L:5.0f}: tau {r['tau']:.3f} s, z {z['z']}, axial {r['axial_mm']:.0f} mm/side", flush=True)
        r = max(stacks, key=lambda q: (q["z_lin"] or 0) - 0.0005 * q["axial_mm"])     # small axial-length penalty
        res = dict(char=r, thermal=thermal(r), iron=iron_loss(r, r["f_Hz"]), stacks=[{k: q[k] for k in ("L_stk", "tau", "z_lin", "axial_mm")} for q in stacks], runs=[])
        print(f"  chosen L_stk {r['L_stk']:.0f}; coil heat limit air {res['thermal']['P_air_max_W']:.1f} W, vacuum "
              f"{res['thermal']['P_vac_max_W']:.1f} W per coil; iron loss {res['iron']['P_fe_side_W']:.1f} W per side", flush=True)
        for ah in ("a50", "r160"):
            for N_u in (100, 200, 400, 800):
                for la in (0.6, M.R_CA, 2.0):
                    q = p3_eval(r, N_u, ah, la)
                    res["runs"].append(q)
                    if not q["ok"]:
                        print(f"    AH {ah} N_u {N_u:4d} La {la:.2f}: no steady state (z {q['z_early']}) {q.get('err') or ''}", flush=True)
                        continue
                    print(f"    AH {ah} N_u {N_u:4d} La {la:.2f}: z {q['z_early']:.3f} | I {q['I_pk']:.2f} A pk, J {q['J_A_mm2']:.1f} A/mm2 "
                          f"| heat utron {q['P_per_utron_coil_W']:.2f} W/coil, fixed {q['P_cu_fixed_W']:.2f}, AH {q['P_AH_W']:.2f} W | belt(el) "
                          f"{q['P_belt_el_W']:.2f} W | neck {q['neck_mm']:.1f} mm (w_p {r['design']['w_p']})", flush=True)
        out["designs"][tag] = res
    json.dump(out, open(os.path.join(HERE, "pole_design_p3.json"), "w"), indent=1, default=float)


NECK_MIN_MM = 6.0                         # narrowest practical lamination bridge [RH]


def valid(q):
    return bool(q.get("ok") and (q.get("z_early") or 0) > 1.02 and q.get("P_belt_el_W", 0) > 0
                and q.get("neck_mm", 1e9) < 1e3)


def iron_real(r, q):
    """iron loss at the real flux densities: the neck at B_SAT, the rest at B_SAT * neck / w_p (M235-35A, ~B^2)."""
    D = P.Design(**r["design"])
    pk = P_FE_50 * (r["f_Hz"] / 50.0) ** 1.3
    b_body = B_SAT * min(1.0, q["neck_mm"] / D.w_p)
    fe = iron_loss(r, r["f_Hz"])
    m_neck = 3 * 10.0 * q["neck_mm"] * D.L_stk * 1e-9 * RHO_FE          # a 10 mm long neck per utron
    return dict(B_body_T=b_body, P_fe_side_W=pk * ((3 * fe["m_utron_kg"] + 3 * fe["m_bridge_kg"]) * (b_body / 1.5) ** 2 + m_neck))


def final():
    p3d = json.load(open(os.path.join(HERE, "pole_design_p3.json")))["designs"]
    out = dict(stage="final", AT_target=AT_TARGET, designs={})
    plan = {"best g 0.5": (300, 400, 500), "g 0.5 geometry at 1.0 mm": (600, 800, 1000)}
    for tag, nus in plan.items():
        r = p3d[tag]["char"]
        runs = []
        for N_u in nus:
            for la in (0.4, 0.6):
                q = p3_eval(r, N_u, "r160", la)
                q["valid"] = valid(q)
                if q["valid"]:
                    q.update(iron_real(r, q))
                runs.append(q)
                print(f"{tag:26s} N_u {N_u:5d} La {la:.1f}: valid {q['valid']} z {q.get('z_early')} "
                      + (f"| utron {q['P_per_utron_coil_W']:.2f} W/coil fixed {q['P_cu_fixed_W']:.2f} AH {q['P_AH_W']:.2f} "
                         f"iron/side {q['P_fe_side_W']:.2f} | belt el {q['P_belt_el_W']:.1f} W | neck {q['neck_mm']:.2f} mm "
                         f"V_pk {q['V_group_pk_V']:.0f} V" if q["valid"] else ""), flush=True)
        ok = [q for q in runs if q["valid"]]
        best = min(ok, key=lambda q: q["P_belt_el_W"] + 2 * q["P_fe_side_W"]) if ok else None
        chk = None
        if best:
            # direct confirmation at the scaled Psi_s: the AH must land on the target
            Lmax = 3 * best["N_u"] ** 2 * r["L_al"]
            m = M.run(prof=r["prof"], tau=r["tau"], tau_fixed=TAU_FIXED, sat=True, F=r["f_Hz"], n_cyc=best["n_cyc"],
                      L_max=Lmax, psi_s=best["psi_s"], la_ratio=best["la_ratio"], ah="custom", ah_custom=M.AH["r160"],
                      seed=1e-3 * best["psi_s"] / Lmax)
            wave = m.pop("wave", None)
            chk = dict(AT_pk=m.get("AH_AT_pk"), AT_min=m.get("AH_AT_min"), P_belt_W=m.get("P_belt_W"), z_late=m.get("z_late"), wave=wave)
            print(f"  -> best {tag}: N_u {best['N_u']} La {best['la_ratio']}; direct check AH {chk['AT_min']:.0f}-{chk['AT_pk']:.0f} A-t "
                  f"(target {AT_TARGET:.0f}), belt {chk['P_belt_W']:.2f} W", flush=True)
        out["designs"][tag] = dict(char={k: v for k, v in r.items() if k not in ("theta",)}, runs=runs, best=best, check=chk,
                                   thermal=thermal(r))
    json.dump(out, open(os.path.join(HERE, "pole_design_final.json"), "w"), indent=1, default=float)


DIODES = {"Si (0.55 V @ 1 A)": 1.0, "Schottky (0.35 V @ 1 A)": 0.65}


def run_real(r, N_u, la, nd, psi_s, seed_frac=0.03, n_cyc=90):
    Lmax = 3 * N_u ** 2 * r["L_al"]
    m = M.run(prof=r["prof"], tau=r["tau"], tau_fixed=TAU_FIXED, sat=True, F=r["f_Hz"], n_cyc=n_cyc, L_max=Lmax,
              psi_s=psi_s, la_ratio=la, ah="custom", ah_custom=M.AH["r160"], seed=seed_frac * psi_s / Lmax, nd=nd)
    m.pop("wave", None)
    return m


def solve_real(r, N_u, la, nd, psi_guess, seed_frac=0.03):
    """two passes: run, rescale Psi_s towards the AH target (near-linear once V >> V_f), confirm."""
    psi = psi_guess
    m = None
    for _ in range(3):
        m = run_real(r, N_u, la, nd, psi, seed_frac)
        at = m.get("AH_AT_pk") or 0.0
        if at < 1.0:
            return dict(N_u=N_u, la_ratio=la, nd=nd, starts=False, z_early=m.get("z_early"), psi_s=psi)
        if abs(at / AT_TARGET - 1) < 0.03:
            break
        psi *= AT_TARGET / at
    out = dict(N_u=N_u, la_ratio=la, nd=nd, starts=True, psi_s=psi, z_early=m["z_early"], AT_pk=m["AH_AT_pk"],
               AT_min=m["AH_AT_min"], P_belt_W=m["P_belt_W"], P_utron_coil_W=m["P_cu_utron_W"] / 6, P_fixed_W=m["P_cu_fixed_W"],
               P_AH_W=m["P_AH_W"], I_pk=m["I1_pk"], V_pk=2 * math.pi * r["f_Hz"] * psi,
               neck_mm=psi / (3 * N_u * B_SAT * r["design"]["L_stk"] * 1e-3) * 1e3)
    out["P_diode_W"] = out["P_belt_W"] - 6 * out["P_utron_coil_W"] - out["P_fixed_W"] - out["P_AH_W"] - m.get("P_snub_W", 0.0)
    q = dict(out); q["neck_mm"] = out["neck_mm"]
    out.update(iron_real(r, q))
    # start-up threshold: the smallest seed (fraction of Psi_s) that still grows
    thr = None
    for f in (0.003, 0.01, 0.03):
        mm = run_real(r, N_u, la, nd, psi, f, n_cyc=40)
        if (mm.get("AH_AT_pk") or 0) > 0.5 * AT_TARGET:
            thr = f; break
    out["seed_min_frac"] = thr
    return out


def real():
    fin = json.load(open(os.path.join(HERE, "pole_design_final.json")))["designs"]
    plan = {"best g 0.5": (600, 800, 1000, 1300), "g 0.5 geometry at 1.0 mm": (800, 1000, 1300, 1600)}
    out = dict(stage="real-diodes", AT_target=AT_TARGET, designs={})
    for tag, nus in plan.items():
        r = fin[tag]["char"]
        ideal = [q for q in fin[tag]["runs"] if q.get("valid")]
        k_psi = sum(q["psi_s"] / q["N_u"] for q in ideal) / len(ideal)          # Psi_s per utron turn (ideal diodes)
        rows = []
        for dname, nd in DIODES.items():
            for N_u in nus:
                q = solve_real(r, N_u, 0.6, nd, k_psi * N_u)
                q["diode"] = dname
                rows.append(q)
                if q["starts"]:
                    print(f"{tag:26s} {dname:24s} N_u {N_u:5d}: z {q['z_early']:.3f} AH {q['AT_min']:.0f}-{q['AT_pk']:.0f} | belt {q['P_belt_W']:.1f} W "
                          f"= utron {q['P_utron_coil_W']:.2f} W/coil x6 + fixed {q['P_fixed_W']:.2f} + AH {q['P_AH_W']:.2f} + diodes {q['P_diode_W']:.2f}"
                          f" | iron {q['P_fe_side_W']:.2f} W/side | V_pk {q['V_pk']:.0f} V neck {q['neck_mm']:.1f} mm seed >= {q['seed_min_frac']}", flush=True)
                else:
                    print(f"{tag:26s} {dname:24s} N_u {N_u:5d}: does not start from a 3 % seed (z {q['z_early']})", flush=True)
        out["designs"][tag] = dict(rows=rows)
    json.dump(out, open(os.path.join(HERE, "pole_design_real.json"), "w"), indent=1, default=float)


def kick():
    """start-up kick: the seed raised to >= 10 % of Psi_s (a start pulse), Si diodes, fewest turns."""
    fin = json.load(open(os.path.join(HERE, "pole_design_final.json")))["designs"]
    plan = {"best g 0.5": (400, 500), "g 0.5 geometry at 1.0 mm": (600, 800)}
    out = dict(stage="kick", AT_target=AT_TARGET, designs={})
    for tag, nus in plan.items():
        r = fin[tag]["char"]
        ideal = [q for q in fin[tag]["runs"] if q.get("valid")]
        k_psi = sum(q["psi_s"] / q["N_u"] for q in ideal) / len(ideal)
        rows = []
        for N_u in nus:
            psi = k_psi * N_u
            m = None
            for _ in range(3):
                m = run_real(r, N_u, 0.6, 1.0, psi, seed_frac=0.3, n_cyc=60)
                at = m.get("AH_AT_pk") or 0.0
                if at < 1:
                    break
                if abs(at / AT_TARGET - 1) < 0.02:
                    break
                psi *= AT_TARGET / at
            if not m.get("AH_AT_pk"):
                rows.append(dict(N_u=N_u, runs=False)); print(f"{tag} N_u {N_u}: no steady state", flush=True); continue
            q = dict(N_u=N_u, runs=True, psi_s=psi, z_early=m["z_early"], AT_pk=m["AH_AT_pk"], AT_min=m["AH_AT_min"],
                     P_belt_W=m["P_belt_W"], P_utron_coil_W=m["P_cu_utron_W"] / 6, P_fixed_W=m["P_cu_fixed_W"],
                     P_AH_W=m["P_AH_W"], I_pk=m["I1_pk"], V_pk=2 * math.pi * r["f_Hz"] * psi,
                     neck_mm=psi / (3 * N_u * B_SAT * r["design"]["L_stk"] * 1e-3) * 1e3)
            q["P_diode_W"] = q["P_belt_W"] - 6 * q["P_utron_coil_W"] - q["P_fixed_W"] - q["P_AH_W"] - m.get("P_snub_W", 0.0)
            q.update(iron_real(r, q))
            thr = None
            for f in (0.03, 0.05, 0.08, 0.1, 0.15, 0.2, 0.3):
                mm = run_real(r, N_u, 0.6, 1.0, psi, f, n_cyc=40)
                if (mm.get("AH_AT_pk") or 0) > 0.5 * AT_TARGET:
                    thr = f; break
            q["seed_min_frac"] = thr
            q["seed_min_flux_mWb_per_utron"] = thr * psi / (3 * N_u) * 1e3 if thr else None
            rows.append(q)
            print(f"{tag:26s} N_u {N_u}: AH {q['AT_min']:.0f}-{q['AT_pk']:.0f} | belt {q['P_belt_W']:.1f} W = utron {q['P_utron_coil_W']:.2f} W/coil x6 "
                  f"+ fixed {q['P_fixed_W']:.2f} + AH {q['P_AH_W']:.2f} + diodes {q['P_diode_W']:.2f} | iron {q['P_fe_side_W']:.2f} W/side | "
                  f"I_pk {q['I_pk']:.2f} A V_pk {q['V_pk']:.0f} V neck {q['neck_mm']:.2f} mm | kick >= {thr} of Psi_s", flush=True)
        out["designs"][tag] = dict(rows=rows)
    json.dump(out, open(os.path.join(HERE, "pole_design_kick.json"), "w"), indent=1, default=float)


def _char(kw):
    D = P.Design(**kw)
    r = P.characterise(D, n_theta=N_THETA)
    r["design"] = kw
    return r


def p1():
    cands = s_family() + t_family()
    print(f"P1: {len(cands)} candidates x {N_THETA} angles", flush=True)
    with Pool(4) as pool:
        chars = pool.map(_char, cands)
    rows = []
    for r in chars:
        period = 360.0 / r["cyc_per_rev"]
        a, err = fit_cos(r["theta"], r["L_per_n2"], period)
        r["prof"], r["fit_err"] = a, err
        rows.append(r)
    with Pool(4) as pool:
        zs = pool.map(_z, rows)
    for r, z in zip(rows, zs):
        r.update(z)
        d = r["design"]
        print(f"{d['kind']} g {d['g']:4.2f} w_p {d['w_p']:5.1f} s {d['s']:5.1f} d {d.get('d', 50):4.0f}"
              + (f" N_s {d['N_s']:2d} n_t {d['n_t']}" if d['kind'] == 'T' else "              ")
              + f" | kappa {r['kappa']:6.2f} (2-D {r['L2d_ratio']:6.2f}) tau {r['tau']:.3f} s f {r['f_Hz']:4.0f} Hz"
              f" fit {r['fit_err']:.1e} | z {r['z'] if r['z'] is None else round(r['z'], 4)}", flush=True)
    json.dump(dict(stage="p1", tau_fixed=TAU_FIXED, rows=rows), open(os.path.join(HERE, "pole_design_p1.json"), "w"),
              indent=1, default=float)


def _z(r):
    kw = dict(prof=r["prof"], tau=r["tau"], tau_fixed=TAU_FIXED, sat=False, F=r["f_Hz"], n_cyc=16)
    m = M.run(**kw)
    return dict(z=m.get("z_late"), z_early=m.get("z_early"), z_error=m.get("error"))


if __name__ == "__main__":
    {"p1": p1, "p1b": p1b, "p3": p3, "final": final, "real": real, "kick": kick}[sys.argv[1]]()
