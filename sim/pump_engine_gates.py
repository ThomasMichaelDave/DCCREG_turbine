#!/usr/bin/env python3
"""
sim/pump_engine_gates.py — PUMP-CALC build-time gates (brief pump-calc r0.1 §6)
================================================================================
K1-K4 load-time canaries (also run in the browser worker), E0 engine regression vs
sim/island_asdrawn.py @ 8cd181e, E1 expm parity vs scipy, E2 gap-model limits, E3 no chop,
E4 conservation (+5 % trip), E5 engine reconciliation vs the Pass A ngspice harness (report),
E6 Pass A' replay on the exact engine (report), M1-M3 motor branch / conservation / convergence,
P0 monodromy exactness, P1/P2 speed (CPython here; Pyodide via Node if available), N numpy parity,
F firewall, Z frozen empty-diff.

  python3 sim/pump_engine_gates.py [--quick] [--only E0,E1,...] [--out results.json]

Build-time only: imports scipy (E1) and the frozen r0.2 record (E0); runs git (Z), node and the
numpy-1.26 parity venv (P1/P2/N). Never imported by the calculator. [ME]
"""
import argparse
import collections
import json
import math
import os
import re
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
for p in (HERE, ROOT, os.path.join(ROOT, "reference")):
    if p not in sys.path:
        sys.path.insert(0, p)

import numpy as np
import pump_engine as pe
import shuttle_core as sc
import island_resonant_core as irc

BASE = "8cd181e"
# the brief's §1 anchors (measured by the chat layer on 8cd181e) and this session's live r0.2 values
ANCHOR = dict(core_station=1.5225272, G1=1.255991, R1b=1.354261)
R02_R1B_LIVE = 1.3542609005307074      # island_asdrawn.run_machine, 30/15, this session (1054 s)
NOCANARY = dict(C1min=160.0, C1max=1000.0, C2min=160.0, C2max=1000.0)   # the §1 runs' C1/C2 [finding]
PASS_A = dict(profile="tanh", tanh_k=12.0, cx_min=60.0, pCboss2=6.0, R_lx=20.0, win_end=27.0)
PASS_A_SPICE = dict(G1a=(1.4098, 0.4001), R1a=(1.9501, 0.5689), R1b=(2.1598, 0.7007),
                    D1_G1=(1.4098, 0.4000), D1_R1=(1.4138, 0.3978), RD0_R1=(1.4141, 0.3978))


def mono(over, record=False, events=False, sim_hook=None):
    cfg = pe.make_config(over)
    net = pe.build_net(cfg)
    sim = pe.make_sim(net, cfg); pe.seed(sim)
    if sim_hook:
        sim_hook(sim)
    return pe.monodromy(net, cfg, sim=sim, record=record, events=events), sim


def ev(over, twins=False):
    return pe.evaluate(over, twins=twins)


# ======================================================================================
def gate_K():
    c = pe.canaries()
    js = js_solveDoubler4()
    k1 = [r for r in c["rows"] if r["id"] == "K1"][0]
    if js is not None:
        k1["extra"]["js_solveDoubler4"] = js
        k1["pass"] = bool(k1["pass"] and abs(js - pe.K1_Z) / pe.K1_Z <= 1e-6)
    return dict(pass_=all(r["pass"] for r in c["rows"]), rows=c["rows"])


def js_solveDoubler4():
    """K1's JS twin: the solveDoubler4 block copied into tools/pump-calc.html, run under Node."""
    html = os.path.join(ROOT, "tools", "pump-calc.html")
    if not os.path.exists(html):
        return None
    src = open(html).read()
    m = re.search(r"// BEGIN solveDoubler4.*?\n(.*?)// END solveDoubler4", src, re.S)
    if not m:
        return None
    c = pe.CANARY
    code = m.group(1) + (f"\nconsole.log(solveDoubler4({c['C1MIN']},{c['C1MAX']},{c['C2MIN']},"
                         f"{c['C2MAX']},{c['CA']},{c['CB']},{c['CPAR']}));\n")
    try:
        r = subprocess.run(["node", "-e", code], capture_output=True, text=True, timeout=60)
        return float(r.stdout.strip())
    except Exception:
        return None


# ======================================================================================
def gate_E0(quick=False):
    """pump_engine ('r02' arming) reproduces island_asdrawn.py @ 8cd181e to <= 1e-9 (relative)."""
    import island_asdrawn as ia
    rows = []

    def add(name, mine, ref, tol=1e-9):
        rel = abs(mine - ref) / max(abs(ref), 1e-300)
        rows.append(dict(check=name, pump_engine=mine, r02=ref, rel=rel, pass_=bool(rel <= tol)))
    ok, h1 = ia.h1_ring()
    for r in h1:
        m = pe.s2_ring(r["R"], arming="r02")
        add(f"H1 S2 t1/2 R={r['R']:g}", m["t_half_us"], r["t_half_us"])
        add(f"H1 S2 V_bank R={r['R']:g}", m["V_bank"], r["V_bank"])
    for cp in (20.0, 10.0):
        for station in (False, True):
            ref = ia.run_machine(ia.doubler_net(cp, station), ncyc=40, burn=20, dth=1.0, zth=29.0)["z"]
            cfg = pe.make_config(dict(topology="core", Cpar=cp, simultaneous=not station, arming="r02",
                                      dth=1.0))
            mine = pe.run_machine(pe.core_net(cfg), ncyc=40, burn=20, dth=1.0, zth=29.0, arming="r02")["z"]
            add(f"H3 galvanic {'station' if station else 'always'}-armed Cpar {cp:g}", mine, ref)
    with ia.canary_caps():
        P = ia.shuttle_params()
        ref = ia.shuttle_parity(P, lx=0.0)[0]
        mine = pe.shuttle_parity(P, lx=0.0)[0]
    add("H4 shuttle parity (Lx shorted)", mine, ref)
    # the §1 anchors: G1 and R1b, run_machine 30/15 at the §1 settings (C1/C2 160-1000, see finding)
    cfg = pe.make_config(dict(NOCANARY, Lx_mH=0.0, arming="r02"))
    g1 = pe.run_machine(pe.build_net(cfg), ncyc=30, burn=15, arming="r02")["z"]
    g1_ref = ia.run_machine(ia.build_drawn(lx=0.0, stray=5.0), ncyc=30, burn=15)["z"]
    add("G1 (Lx shorted), 30/15, section-1 settings", g1, g1_ref)
    cfg = pe.make_config(dict(NOCANARY, arming="r02"))
    r1b = pe.run_machine(pe.build_net(cfg), ncyc=30, burn=15, arming="r02")["z"]
    if quick:
        r1b_ref = R02_R1B_LIVE
    else:
        r1b_ref = ia.run_machine(ia.build_drawn(lx=1e-3, bracket="b", stray=5.0), ncyc=30, burn=15)["z"]
    add("R1b (Lx 1 mH, one-way), 30/15, section-1 settings" + (" [r0.2 value cached]" if quick else ""),
        r1b, r1b_ref)
    anchors = dict(G1=(g1, ANCHOR["G1"]), R1b=(r1b, ANCHOR["R1b"]))
    anc_ok = all(abs(a - b) <= 5e-7 for a, b in anchors.values())
    return dict(pass_=all(r["pass_"] for r in rows) and anc_ok, rows=rows,
                anchors={k: dict(pump_engine=a, brief=b, ok=abs(a - b) <= 5e-7) for k, (a, b) in anchors.items()})


# ======================================================================================
def gate_E1(samples=4000):
    """numpy expm (balanced Pade 13) vs scipy.linalg.expm on every ring matrix the gate
    configurations produce (sampled), <= 1e-12 relative (Frobenius)."""
    from scipy.linalg import expm as sexpm
    recs = []
    orig = pe.Ring.E

    def E(self, h):
        out = orig(self, h)
        if len(recs) < samples:
            recs.append((self.A * h, out))
        return out
    pe.Ring.E = E
    try:
        for over in ({}, dict(gm_load="ringdown", ih_load=0.5), dict(gm_load="recover", ih_load=0.7),
                     dict(PASS_A)):
            mono(over)
        pe.s2_ring(2.0)
        cfg = pe.make_config(dict(motor=True, motor_topology="per_branch"))
        sim = pe.make_sim(pe.build_net(cfg), cfg); pe.seed(sim); sim.cycle(0)
    finally:
        pe.Ring.E = orig
    worst = 0.0; worst_g = 0.0; nrm = []
    for Ah, out in recs:
        ref = sexpm(Ah)
        d = np.linalg.norm(out - ref) / max(np.linalg.norm(ref), 1e-300)
        worst = max(worst, d)
        g = pe.expm(Ah)
        worst_g = max(worst_g, np.linalg.norm(g - ref) / max(np.linalg.norm(ref), 1e-300))
        nrm.append(float(np.linalg.norm(Ah, 1)))
    return dict(pass_=bool(worst <= 1e-12 and worst_g <= 1e-12), n=len(recs), max_rel_ring=worst,
                max_rel_expm=worst_g, norm1_range=[min(nrm), max(nrm)] if nrm else None)


# ======================================================================================
def gate_E2():
    """(a) M-SR with holdoff off and I_hold > 1 == M-OW (<= 1e-9). (b) M-RD(->0): |z_R - z_G| <=
    0.005 — the linear-circuit theorem, evaluated where its premise holds (every gap ring-down, so
    no rectifier switches inside a ring); the per-class table is reported."""
    a_ow = mono({})[0]["z"]
    a_sr = mono(dict(gm_load="recover", ih_load=1.5, holdoff_us=0.0))[0]["z"]
    rel_a = abs(a_sr - a_ow) / a_ow
    table = []
    for name, over in (("all classes M-RD(->0) [theorem premise]",
                        dict(gm_load="ringdown", gm_rail="ringdown", gm_fire="ringdown", gm_backstop="ringdown")),
                       ("load M-RD(->0); rail valve", dict(gm_load="ringdown")),
                       ("load M-RD(->0); rail arc", dict(gm_load="ringdown", gm_rail="arc")),
                       ("load + fire M-RD(->0); rail valve", dict(gm_load="ringdown", gm_fire="ringdown"))):
        zR = mono(over)[0]["z"]; zG = mono(dict(over, Lx_mH=0.0))[0]["z"]
        table.append(dict(case=name, z_R=zR, z_G=zG, dz=zR - zG))
    ok_b = abs(table[0]["dz"]) <= 0.005
    return dict(pass_=bool(rel_a <= 1e-9 and ok_b), a=dict(z_valve=a_ow, z_sr_limit=a_sr, rel=rel_a),
                b=table)


# ======================================================================================
GATE_CONFIGS = [("R1 valve", {}), ("R1 M-RD 0.5", dict(gm_load="ringdown", ih_load=0.5)),
                ("R1 M-RD(->0)", dict(gm_load="ringdown")),
                ("R1 M-SR t_rec 0, I_hold 0.7", dict(gm_load="recover", ih_load=0.7)),
                ("R1 M-SR t_rec 1 us, I_hold 0.5", dict(gm_load="recover", ih_load=0.5, trec_load=1.0)),
                ("R1 M-SR limit", dict(gm_load="recover", ih_load=1.5, holdoff_us=0.0)),
                ("R1 arc", dict(gm_load="arc")),
                ("G1", dict(Lx_mH=0.0)), ("G0", dict(galvanic=True)),
                ("R1 valve, section-1 caps", dict(NOCANARY)),
                ("R1 valve, Pass A config", dict(PASS_A))]


def gate_E3_E4():
    """E3: every extinction |i| < 1e-3 of that event's i_pk1 (rings), over the gate configurations.
    E4: per-cycle residual < 1e-9 of W from W (stroke dU), dE (boundary states), E_diss (Schur
    dumps + ring + relaxation + motor), on the eigen-cycle; +5 % on E_diss moves the residual by
    the predicted -0.05 E_diss/W and fails the guard."""
    e3 = []; e4 = []
    for name, over in GATE_CONFIGS:
        def hook(sim):
            sim.chop_log = []
        m, sim = mono(over, record=True, events=True, sim_hook=hook)
        mx = collections.defaultdict(float); cnt = collections.Counter()
        for k, n, r in sim.chop_log:
            mx[(k, n)] = max(mx[(k, n)], r); cnt[(k, n)] += 1
        worst = max(mx.values()) if mx else 0.0
        wk = max(mx, key=mx.get) if mx else None
        e3.append(dict(config=name, n_extinctions=sum(cnt.values()), max_ratio=worst,
                       worst=f"{wk[0]} {wk[1]}" if wk else None, pass_=bool(worst < 1e-3)))
        rec = m["rec"]; led = rec["ledger"]
        W = led["W"]; Ed = led["alg"] + led["ring"] + led["relax"] + led["motorR"]; dE = rec["E1"] - rec["E0"]
        res = (W - dE - Ed) / W
        res5 = (W - dE - 1.05 * Ed) / W
        pred = res - 0.05 * Ed / W
        e4.append(dict(config=name, resid=res, trip_resid=res5, trip_pred=pred,
                       trip_ok=bool(abs(res5 - pred) <= 1e-12 and abs(res5) > 1e-9),
                       pass_=bool(abs(res) < 1e-9 and abs(res5 - pred) <= 1e-12 and abs(res5) > 1e-9)))
    return (dict(pass_=all(r["pass_"] for r in e3), rows=e3),
            dict(pass_=all(r["pass_"] for r in e4), rows=e4))


# ======================================================================================
def gate_E5():
    """Engine reconciliation (report-only): pump_engine at the Pass A ngspice configuration vs the
    ngspice G1a / R1a / R1b / M-RD(->0) numbers; attribution rows swap one ingredient back."""
    rows = []

    def row(name, over, spice=None):
        r = ev(over)
        rows.append(dict(case=name, z=r["z"], eta_cut0=r["ledger"]["eta_at_cut"],
                         eta_band=[r["eta_cut"]["min"], r["eta_cut"]["max"]], converged=r["converged"],
                         spice=spice, dz=(r["z"] - spice[0]) if spice else None))
    A = dict(PASS_A)
    arcs = dict(gm_fire="arc", gm_backstop="arc")
    row("G1a (Lx->0, bracket a) — Pass A config", dict(A, Lx_mH=0.0, **arcs), PASS_A_SPICE["G1a"])
    row("R1a (Lx 1 mH, bracket a)", dict(A, **arcs), PASS_A_SPICE["R1a"])
    row("R1b (Lx 1 mH, bracket b)", dict(A), PASS_A_SPICE["R1b"])
    row("R1 M-RD(->0) load (bracket a)", dict(A, gm_load="ringdown", **arcs), PASS_A_SPICE["RD0_R1"])
    row("G1 M-RD(->0) load (bracket a)", dict(A, Lx_mH=0.0, gm_load="ringdown", **arcs), PASS_A_SPICE["D1_G1"])
    # attribution: schedule/profile ingredients one at a time (from the Pass A config back to r0.2)
    row("R1b, shuttle C1/C2 profile (not tanh)", dict(A, profile="shuttle"))
    row("R1b, cx_min 8 pF, pCboss2 0", dict(A, cx_min=8.0, pCboss2=0.0))
    row("R1b, R_LX 2 ohm", dict(A, R_lx=2.0))
    row("R1b, windows to 30 deg", dict(A, win_end=30.0))
    row("R1b, r0.2 settings (default config)", dict())
    row("R1b, Pass A config, dth 0.025", dict(A, dth=0.025))
    return dict(rows=rows)


# ======================================================================================
def classify(R, G, G0, dz, de, f_rec_model):
    """Pass A' r0.2 classes (sim/island_gapbracket.classify), on the exact engine's ledgers."""
    T_load = G["T_load"]
    f_rec = (R["eta"] - G["eta"]) / T_load if T_load > 0 else float("nan")
    Dz, De = R["z"] - G["z"], R["eta"] - G["eta"]
    if R["z"] < G["z"] - dz or R["z"] <= 1:
        v = "PUMP-BREAKS"
    elif f_rec >= 0.95 * f_rec_model and R["z"] > G["z"] + dz:
        v = "SINK-REALIZED"
    elif R["eta"] > G0["eta"] + de:
        v = "SINK-PARTIAL"
    elif G["eta"] + de < R["eta"] <= G0["eta"] + de:
        v = "SINK-SUBTHRESHOLD"
    elif abs(De) <= de and abs(Dz) <= dz:
        v = "SINK-IS-PUMP"
    else:
        v = "OUT-OF-SET"
    return dict(cls=v, dz=Dz, deta=De, f_rec=f_rec)


def gate_E6(quick=False):
    """Pass A' replay on the exact engine (report-only): the M-OW / M-RD / M-SR ladder at the
    default and at the Pass A configuration, classes vs sim/island-gapbracket-findings.md."""
    ref = {}
    try:
        G = json.load(open(os.path.join(HERE, ".ia2_grade.json")))
        ref["OW"] = G["OW"]["verdict"]
        for k, v in G["RD"].items():
            ref[("RD", float(k))] = v["verdict"]
        for k, v in G["SR"].items():
            tr = float(k.split("|")[0].split("=")[1]); h = float(k.split("|")[1].split("=")[1])
            ref[("SR", tr, h)] = v["cls"]
    except Exception:
        # the classes as published in sim/island-gapbracket-findings.md
        ref["OW"] = "SINK-PARTIAL"
        for h, c in ((0.0, "SINK-IS-PUMP"), (0.1, "SINK-IS-PUMP"), (0.3, "SINK-PARTIAL"),
                     (0.5, "SINK-PARTIAL"), (0.7, "SINK-PARTIAL")):
            ref[("RD", h)] = c
    out = {}
    cfgs = (("default", {}), ("Pass A config", dict(PASS_A)))
    for cname, base in cfgs:
        def led(over):
            r = ev(dict(base, **over))
            by = r["ledger"]["by_frac"]
            return dict(z=r["z"], eta=r["ledger"]["eta_at_cut"], T_load=by.get("SG3a1", 0.0) + by.get("SG4a1", 0.0),
                        converged=r["converged"])
        R_lx = base.get("R_lx", 2.0)
        f_rec_model = irc.integrate(pe.DEFAULTS["cx_max"] * 1e-12, 2640e-9, 5e3, 1e-3, R_lx)["f_rec"]
        # delta_z / delta_eta = max(0.005, 3 x the dth-twin change of R1 valve) (Pass A' rule, dth
        # plays the role of the ngspice reltol twin here)
        a = led({}); b = led(dict(dth=0.025))
        dz = max(0.005, 3 * abs(a["z"] - b["z"])); de = max(0.005, 3 * abs(a["eta"] - b["eta"]))
        G0 = led(dict(galvanic=True))
        ladder = [("OW", dict(), "OW")]
        for h in ((0.0, 0.5) if quick else (0.0, 0.1, 0.3, 0.5, 0.7)):
            ladder.append((f"RD I_hold {h:g}", dict(gm_load="ringdown", ih_load=h), ("RD", h)))
        trs = (0.0, 1e-6) if quick else (0.0, 1e-7, 1e-6)
        hs = (0.5,) if quick else (0.3, 0.5, 0.7)
        for tr in trs:
            for h in hs:
                ladder.append((f"SR t_rec {tr * 1e6:g} us I_hold {h:g}",
                               dict(gm_load="recover", ih_load=h, trec_load=tr * 1e6), ("SR", tr, h)))
        rows = []
        for name, over, key in ladder:
            R = led(over); Gt = led(dict(over, Lx_mH=0.0))
            c = classify(R, Gt, G0, dz, de, f_rec_model)
            pa = ref.get(key if key != "OW" else "OW")
            rows.append(dict(model=name, z_R=R["z"], z_G=Gt["z"], eta_R=R["eta"], eta_G=Gt["eta"],
                             eta_G0=G0["eta"], cls=c["cls"], dz=c["dz"], deta=c["deta"], f_rec=c["f_rec"],
                             pass_a_prime=pa, agree=(pa == c["cls"]) if pa else None,
                             converged=R["converged"] and Gt["converged"]))
        out[cname] = dict(dz=dz, de=de, f_rec_model=f_rec_model, G0=G0, rows=rows)
    return out


# ======================================================================================
def gate_M1():
    """One series R-L-C branch (the motor branch: 0.64 H, 440 nF, 40 ohm) discharging a 1 nF source
    through the engine's continuous-mode path vs the analytic response, <= 1e-6."""
    L, C, R, Cs = 0.64, 440e-9, 40.0, 1e-9
    net = pe.Net()
    a, b = net.n("a"), net.n("b")
    net.caps += [("Cs", a, pe.GND, Cs), ("Cm", b, pe.GND, C)]
    net.inds.append(("Lm", a, b, L, R, "motor"))
    sim = pe.Sim(net, mode="cont")
    K = net.K(0.0); sim.q = K @ np.array([1.0, 0.0])
    Ce = Cs * C / (Cs + C)
    alpha = R / (2 * L); w0 = 1 / math.sqrt(L * Ce); wd = math.sqrt(w0 * w0 - alpha * alpha)
    worst = 0.0; t = 0.0; Eloss = 0.0
    E0 = 0.5 * Cs * 1.0
    for k in range(40):
        dt = 3e-6 * (1 + k % 3)
        sim.motor_step(dt); t += dt
        I = sim.I[0]
        Ia = (1.0 / (wd * L)) * math.exp(-alpha * t) * math.sin(wd * t)
        worst = max(worst, abs(I - Ia) / (1.0 / (wd * L)))
    Vn = np.linalg.solve(K, sim.q)
    E1 = 0.5 * (Cs * Vn[0] ** 2 + C * Vn[1] ** 2) + 0.5 * L * sim.I[0] ** 2
    cons = abs(E0 - E1 - sim.ledger["motorR"]) / E0
    return dict(pass_=bool(worst <= 1e-6 and cons <= 1e-9), max_rel_current=worst, conservation=cons,
                t_us=t * 1e6)


def gate_M2_M3(quick=False):
    """M2: motor-in conservation < 1e-9 on the eigen-cycle. M3: |dz| < 1e-3 between dth and dth/2,
    and between ring_frac 48 and 96 (the ring-step tolerance); else 'not converged'."""
    m2 = []; m3 = []
    cases = [("R1m per-branch", dict(motor=True, motor_topology="per_branch")),
             ("G1m per-branch", dict(motor=True, motor_topology="per_branch", Lx_mH=0.0))]
    if not quick:
        cases.append(("R1m per-coil", dict(motor=True)))
    for name, over in cases:
        t0 = time.time()
        m, sim = mono(over, record=True)
        t_main = time.time() - t0
        rec = m["rec"]; led = rec["ledger"]
        W = led["W"]; Ed = led["alg"] + led["ring"] + led["relax"] + led["motorR"]; dE = rec["E1"] - rec["E0"]
        res = (W - dE - Ed) / W
        m2.append(dict(config=name, resid=res, motor_frac=led["motorR"] / W, pass_=bool(abs(res) < 1e-9)))
        z_h = mono(dict(over, dth=over.get("dth", 0.05) / 2))[0]
        z_f = mono(over, sim_hook=lambda s: setattr(s, "ring_frac", 96.0))[0]
        d1 = abs(m["z"] - z_h["z"]); d2 = abs(m["z"] - z_f["z"])
        conv = m["converged"] and z_h["converged"] and z_f["converged"]
        m3.append(dict(config=name, z=m["z"], z_dth2=z_h["z"], z_ring96=z_f["z"], dz_dth=d1, dz_ring=d2,
                       converged=[m["converged"], z_h["converged"], z_f["converged"]],
                       pass_=bool(conv and d1 < 1e-3 and d2 < 1e-3), time_s=t_main))
    return (dict(pass_=all(r["pass_"] for r in m2), rows=m2),
            dict(pass_=all(r["pass_"] for r in m3), rows=m3))


# ======================================================================================
def z_iterated(over, max_cyc=120, tol=1e-13):
    """The plain power iteration (r0.2 run_machine, robust arming): cycle-boundary |V1|+|V4|
    ratio after it has stopped moving (|dz| < tol for 3 cycles)."""
    cfg = pe.make_config(over); net = pe.build_net(cfg)
    sim = pe.make_sim(net, cfg); pe.seed(sim)
    zs = []; m0 = sim.state_mag(); still = 0
    for k in range(max_cyc):
        sim.cycle(k); m1 = sim.state_mag(); zs.append(m1 / m0); sim.rescale(1.0 / m1); m0 = 1.0
        if len(zs) > 3 and abs(zs[-1] - zs[-2]) < tol:
            still += 1
            if still >= 3:
                break
        else:
            still = 0
    return zs[-1], len(zs)


def gate_P0(quick=False):
    rows = []
    cases = [("core station-armed", dict(topology="core", dth=1.0)),
             ("core always-armed", dict(topology="core", dth=1.0, simultaneous=True)),
             ("G1", dict(Lx_mH=0.0)), ("G0", dict(galvanic=True)), ("R1 valve", {}),
             ("R1 M-RD 0.5", dict(gm_load="ringdown", ih_load=0.5)),
             ("R1 M-SR limit", dict(gm_load="recover", ih_load=1.5, holdoff_us=0.0))]
    if quick:
        cases = cases[:5]
    for name, over in cases:
        zm = mono(over)[0]
        zi, n = z_iterated(over)
        rel = abs(zm["z"] - zi) / zi
        rows.append(dict(config=name, z_monodromy=zm["z"], z_iterated=zi, cycles=n, rel=rel,
                         converged=zm["converged"], pass_=bool(rel <= 1e-9 and zm["converged"])))
    return dict(pass_=all(r["pass_"] for r in rows), rows=rows)


# ======================================================================================
def gate_P(quick=False):
    """P1 standard evaluation (motor out, one gap model, twins) <= 10 s in Pyodide; P2 motor-in
    (the page's path: the main machine, then its d-theta/2 check only if it converged) <= 60 s.
    CPython measured here; Pyodide 0.26.2 via Node (PYODIDE_DIR, default the local copy), with an
    RSS watchdog (3 GB) so a runaway wasm heap cannot take the host down."""
    out = {}
    t = time.time(); pe.evaluate({}); out["P1_cpython_s"] = time.time() - t
    t = time.time(); r = pe.evaluate(dict(motor=True, motor_topology="per_branch"), twins=False)
    out["P2_cpython_s"] = time.time() - t; out["P2_converged"] = r["converged"]
    pyo = os.environ.get("PYODIDE_DIR", "/tmp/claude-0/pyo/pyodide")
    out["pyodide"] = None
    if os.path.isdir(pyo):
        script = f"""
import {{ loadPyodide }} from "{pyo}/pyodide.mjs";
import fs from "fs";
const R = "{ROOT}/";
const files = ["sim/pump_engine.py","shuttle_core.py","reference/doubler_core.py","reference/island_resonant_core.py",
  "spice/timing.sub","topology_edge_list.csv"];
const t0 = Date.now();
const py = await loadPyodide({{ indexURL: "{pyo}/" }});
await py.loadPackage("numpy");
for (const d of ["/repo/sim","/repo/reference","/repo/spice"]) py.FS.mkdirTree(d);
for (const f of files) py.FS.writeFile("/repo/"+f, fs.readFileSync(R+f, "utf8"));
const boot = (Date.now() - t0) / 1000;
const r = await py.runPythonAsync(`
import sys, time, json
sys.path[:0] = ['/repo/sim','/repo','/repo/reference']
import pump_engine as pe
out = {{}}
t=time.time(); c=pe.canaries(); out['canaries_s']=time.time()-t; out['canaries_pass']=c['pass_']
t=time.time(); r=pe.evaluate({{}}); out['P1_s']=time.time()-t; out['z']=r['z']
t=time.time(); r=pe.evaluate({{'motor': True, 'motor_topology': 'per_branch'}}, twins=False); out['P2_s']=time.time()-t; out['motor_converged']=r['converged']
json.dumps(out)
`);
console.log(JSON.stringify(Object.assign({{boot_s: boot}}, JSON.parse(r))));
"""
        path = "/tmp/claude-0/pc/pump_bench.mjs"
        os.makedirs(os.path.dirname(path), exist_ok=True)
        open(path, "w").write(script)
        proc = subprocess.Popen(["node", path], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        peak = 0; t0 = time.time(); killed = False
        while proc.poll() is None:
            try:
                rss = int(open(f"/proc/{proc.pid}/status").read().split("VmRSS:")[1].split()[0])
                peak = max(peak, rss)
                if rss > 3_000_000 or time.time() - t0 > 1500:
                    proc.kill(); killed = True
            except Exception:
                pass
            time.sleep(1)
        so = proc.stdout.read()
        try:
            out["pyodide"] = json.loads(so.strip().splitlines()[-1])
        except Exception:
            out["pyodide"] = dict(error="killed by watchdog" if killed else so[-300:])
        out["pyodide_peak_rss_MB"] = peak / 1024
    py_ = out.get("pyodide") or {}
    p1 = py_.get("P1_s"); p2 = py_.get("P2_s")
    out["P1_pass"] = bool(p1 is not None and p1 <= 10.0)
    out["P2_pass"] = bool(p2 is not None and p2 <= 60.0)
    return out


def gate_N():
    """numpy parity: the engine's self-test, canaries and two evaluations under numpy 1.26.4 (the
    Pyodide proxy venv) and the CLI numpy 2.x agree (<= 1e-9)."""
    res = {}
    for tag, exe in (("numpy_1.26", os.path.join(ROOT, ".pyodide-parity", "bin", "python")),
                     ("numpy_cli", sys.executable)):
        if not os.path.exists(exe):
            res[tag] = dict(error=f"{exe} missing (python3 -m venv .pyodide-parity && "
                                  f".pyodide-parity/bin/pip install numpy==1.26.4)")
            continue
        r = subprocess.run([exe, os.path.join(HERE, "pump_engine_parity.py")], capture_output=True, text=True,
                           timeout=1800, cwd=ROOT)
        try:
            res[tag] = json.loads(r.stdout.strip().splitlines()[-1])
        except Exception:
            res[tag] = dict(error=r.stderr[-400:])
    a, b = res.get("numpy_1.26", {}), res.get("numpy_cli", {})
    ok = bool(a.get("selftest") and b.get("selftest") and a.get("canaries_pass") and b.get("canaries_pass"))
    diffs = {}
    if ok:
        for k in ("G1", "R1_valve"):
            diffs[k] = abs(a[k]["z"] - b[k]["z"]) / b[k]["z"]
        for k in a["canaries"]:
            ga, gb = a["canaries"][k]["got"], b["canaries"][k]["got"]
            ga = ga if isinstance(ga, list) else [ga]; gb = gb if isinstance(gb, list) else [gb]
            diffs["canary_" + k] = max(abs(x - y) / abs(y) for x, y in zip(ga, gb))
        ok = ok and max(diffs.values()) <= 1e-9
    return dict(pass_=ok, runs=res, rel=diffs)


def gate_F():
    """Firewall: pure EE — the engine imports only numpy and the frozen EE cores (design_synth for
    the advisory lamps, lazily); no subprocess / git / file writes on the import path."""
    src = open(os.path.join(HERE, "pump_engine.py")).read()
    imports = sorted(set(re.findall(r"^\s*import (\w+)|^\s*from (\w+) import", src, re.M)))
    names = sorted(set(a or b for a, b in imports))
    allowed = {"csv", "itertools", "json", "math", "os", "re", "sys", "numpy", "shuttle_core",
               "doubler_core", "island_resonant_core", "design_synth", "time"}
    bad = [n for n in names if n not in allowed]
    writes = re.findall(r"open\([^)]*['\"]w", src)
    sub = bool(re.search(r"^\s*(import|from)\s+subprocess", src, re.M))
    return dict(pass_=bool(not bad and not writes and not sub), imports=names, disallowed=bad,
                file_writes=len(writes), subprocess=sub)


def gate_Z():
    """Frozen empty-diff (brief §0) vs 8cd181e, plus the working tree."""
    paths = ["shuttle_core.py", "reference/", "sim/seq_stat_commutation.py", "sim/design_synth.py",
             "sim/island_asdrawn.py", "sim/island_asdrawn_r01_spice.py", "sim/island_gapbracket.py",
             "island_asdrawn_r01_ledger.csv", "island_asdrawn_r01_peaks.csv", "island_asdrawn_r01_runs.csv",
             "island_asdrawn_r01_t1.csv", "island_asdrawn_r01_traces.png", "island_gapbracket.png",
             "island_gapbracket_runs.csv", "island_gapbracket_trv.csv", "sim/island-asdrawn-findings.md",
             "sim/island-asdrawn-r01-spice-findings.md", "sim/island-gapbracket-findings.md",
             "spice/", "index.html", "tools/charge-pump-synth-live.html", "tools/schematic.svg"]
    r1 = subprocess.run(["git", "diff", "--stat", BASE, "--"] + paths, cwd=ROOT, capture_output=True, text=True)
    r2 = subprocess.run(["git", "status", "--porcelain", "--"] + paths, cwd=ROOT, capture_output=True, text=True)
    out = (r1.stdout + r2.stdout).strip()
    return dict(pass_=out == "", base=BASE, diff=out)


# ======================================================================================
def verdict(G):
    K = G["K"]["pass_"]
    E01 = G["E0"]["pass_"] and G["E1"]["pass_"]
    corr = all(G[k]["pass_"] for k in ("E2", "E3", "E4", "M1", "P0", "N", "F", "Z"))
    m3 = G["M3"]["pass_"] and G["M2"]["pass_"]      # the motor-in machine's gates (M2, M3)
    speed = G["P"]["P1_pass"] and G["P"]["P2_pass"]
    if not K:
        return "CANARY-FAIL"
    if not E01:
        return "ENGINE-DRIFT"
    if not corr:
        return "FAIL (a correctness gate)"
    if not m3:
        return ("PUMP-CALC-PARTIAL (motor-in: " + ", ".join(k for k in ("M2", "M3") if not G[k]["pass_"])
                + " fail -> 'not converged')" + ("" if speed else " (+ P1/P2 missed: SLOW)"))
    return "PUMP-CALC-LIVE" if speed else "PUMP-CALC-SLOW"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--quick", action="store_true")
    ap.add_argument("--only", default="")
    ap.add_argument("--out", default="")
    a = ap.parse_args()
    only = set(x.strip() for x in a.only.split(",") if x.strip())
    G = {}
    t00 = time.time()

    def save():
        if a.out:
            G["total_s"] = time.time() - t00
            open(a.out, "w").write(json.dumps(pe._jsonable(G), indent=1, default=str))

    def run(name, fn):
        if only and name not in only:
            return
        t = time.time()
        print(f"== {name} ...", file=sys.stderr, flush=True)
        G[name] = fn()
        if isinstance(G[name], dict):
            G[name]["gate_s"] = time.time() - t
        print(f"   {name}: {G[name].get('pass_', 'report') if isinstance(G[name], dict) else G[name]}"
              f" ({time.time() - t:.0f} s)", file=sys.stderr, flush=True)
        save()
    run("K", gate_K)
    run("E0", lambda: gate_E0(a.quick))
    run("E1", gate_E1)
    run("E2", gate_E2)
    if not only or "E3" in only or "E4" in only:
        t = time.time(); e3, e4 = gate_E3_E4(); G["E3"], G["E4"] = e3, e4
        print(f"   E3: {e3['pass_']}  E4: {e4['pass_']} ({time.time() - t:.0f} s)", file=sys.stderr); save()
    run("E5", gate_E5)
    run("E6", lambda: gate_E6(a.quick))
    run("M1", gate_M1)
    if not only or "M2" in only or "M3" in only:
        t = time.time(); m2, m3 = gate_M2_M3(a.quick); G["M2"], G["M3"] = m2, m3
        print(f"   M2: {m2['pass_']}  M3: {m3['pass_']} ({time.time() - t:.0f} s)", file=sys.stderr); save()
    run("P0", lambda: gate_P0(a.quick))
    run("P", lambda: gate_P(a.quick))
    run("N", gate_N)
    run("F", gate_F)
    run("Z", gate_Z)
    if not only:
        G["verdict"] = verdict(G)
    G["total_s"] = time.time() - t00
    js = json.dumps(pe._jsonable(G), indent=1, default=str)
    if a.out:
        open(a.out, "w").write(js)
    print(js)


if __name__ == "__main__":
    main()
