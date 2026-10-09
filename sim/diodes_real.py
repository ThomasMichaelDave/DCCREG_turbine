"""sim/diodes_real.py -- real-diode start-up: both pumps of record with datasheet-class rectifiers in place of the
near-ideal ND of every circuit study of record (docs/ledger/DCCREG-design-ledger.md §5.2, the models: "real-diode
start-up"). ngspice. Writes sim/diodes_real_results.json and docs/figures/diodes-real.png; the findings are
sim/diodes-real-findings.md.

1. The magnetic pump: sim/magnetic_doubler.py's deck at the pick, exactly as sim/rotor_parts_duty.py (_kw) and
   sim/ah_steady_cusp.py (the 22 mF bypass, PROPOSED) run it, with D1*-D4* as datasheet-class rectifiers [IR]:
     GP  a 3 A / 200 V general-purpose silicon rectifier of the 1N54xx class (standard recovery),
     FR  a 3 A / 200 V fast-recovery silicon rectifier class,
     SB  a 3 A / 200 V Schottky barrier rectifier class in all four,
     SBM the same on D1* / D2* and a 3 A / 100 V Schottky class on D3* / D4* (they block 43-45 V),
   each as a level-1 diode (Is, N, Rs fitted to three typical forward points; Cjo, M, Vj; Tt; BV, IBV), against the
   record's ND (n 1). Without and with the bypass, per model:
   - the smallest start kick (a fraction of Psi_s seeded as sim/pole_design.py run_real seeds it) that passes the
     record's start criterion (sim/pole_design.py size_op: N_AH x the branch peak over the last 4 of 40 cycles above
     half of AT_TARGET), by bisection; the largest failing kick re-run for 120 cycles;
   - the start-up from the record's 20 % kick (sim/pole_design_variants_op.json kick_frac), 80 cycles: does it start,
     the time to 95 % and to within 2 % of the steady branch peak (and of the coil's mean with the bypass);
   - the steady state from the record's operating seed (sim/rotor_parts_duty.py SEED_FRAC 0.3; 1.25 x the threshold
     where that is larger), 60 cycles: A-turns per coil, z_early, the belt and its ledger, each diode's terminal power
     (its conduction loss; the level-1 charges are lossless round a cycle [OC]) and its reverse recovery: the charge
     it returns at each turn-off (Q_rr), Q_rr x V_R as the loss bound, and the circuit's cost of Tt measured against
     the same diode with Tt = 0.
2. The electrostatic pump and the rings' supply: sim/core_field.py dc as sim/hub_rings_build.py runs record_supply
   (the settings read from sim/hub_rings_build_results.json), with D1-D4 and the 8 chain diodes as HV rectifier
   sticks of the 20 kV / 5 mA avalanche class (sim/diode-stack-findings.md) and Z1 / Z4 as strings of 66 avalanche
   diodes of the 200 V class (the ledger's first cut, §3.4) [IR]. Each stick is a series string of 20 junctions
   carried as one level-1 diode (N x the junction's forward law, Rs, the string's junction capacitance, Tt, BV) with
   its reverse leakage set by the Is of a parallel leakage element; the D3 / D4 positions take two sticks (the
   record's x2-rated guidance). Variants: forward only; no leakage; typical / maximum / hot leakage; V_F x 2; a 1 pF
   body capacitance; a slow (Tt 3 us) stick. Per variant: the gain z from the record's two seeds (-10 V free,
   -1 kV clamped), the smallest seed that grows (bisection), the start-up (95 %), the rings' steady voltages and
   ripple, the stacks' leakage and what it costs the rings, the clamps' and the stacks' dissipation.
   The record's deck starts its two charge-defined varicaps uncharged under uic (ngspice ignores the .ic of nodes 1 /
   4 for them: the -1 kV seed relaxes in the first step) [OC, checked here]. The real-diode runs need a consistent
   start, so each varicap is split into a linear capacitor at its t = 0 value (it takes the .ic) and a charge-defined
   part (C(t) - C(0)) V that is zero at t = 0 [IR]; the record's ND is run both ways.
3. Gates: the wrapped decks with the record's ND reproduce the record (magnetic: sim/ah_steady_cusp_results.json and
   sim/rotor_parts_duty_results.json; electrostatic: sim/hub_rings_build_results.json record_supply and
   record_supply_free); the energy balance of every new steady run (the belt against every dissipation and the change
   in stored energy); a step-size check of one new run per pump.
Tags (CONVENTIONS.md §1): [OC] derivable physics; [IR] a modelling or engineering choice, datasheet-class device
parameters included; [RH] heuristic, not load-bearing. Never a bare d: g for a gap, "diameter" spelled out.
Usage: python3 sim/diodes_real.py [--procs 4] [--only mag|es] [--figure-only]   (needs ngspice; about an hour with 4
       processes)
"""
import argparse
import json
import math
import os
import re
import subprocess
import sys
import tempfile
import time
from multiprocessing import Pool

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
import ah_steady_cusp as AS        # noqa: E402  (the AH bypass: C + ESR across each coil)
import core_field as CF            # noqa: E402  (the electrostatic deck of record)
import magnetic_doubler as M       # noqa: E402  (the magnetic dual doubler's deck)
import pole_design as PD           # noqa: E402  (AT_TARGET, kick_seed)
import rotor_parts_duty as RP      # noqa: E402  (the pick's settings, exactly as the duty study runs it)

OUT_JSON = os.path.join(HERE, "diodes_real_results.json")
OUT_FIG = os.path.join(ROOT, "docs", "figures", "diodes-real.png")
SRC = {
    "pick": "sim/rotor_parts_duty.py (_kw, TAU_FIXED, SEED_FRAC, N_CYC); sim/pole_design_variants_op.json",
    "kick": "sim/pole_design_variants_op.json (best: kick_frac, kick_I_A, kick_mJ); sim/pole_design.py kick_seed",
    "criterion": "sim/pole_design.py size_op (40 cycles, AH_AT_pk > 0.5 AT_TARGET)",
    "bypass": "sim/ah_steady_cusp.py (C_byp + ESR across AHt and AHb); sim/ah_steady_cusp_results.json",
    "duty": "sim/rotor_parts_duty_results.json (la_lb.diode_VR_pk_V)",
    "es_record": "sim/hub_rings_build_results.json (record_supply, record_supply_free)",
    "es_deck": "sim/core_field.py deck (dc, n_cw, n_cw_a, a_ref 'shaft')",
    "sticks": "sim/diode-stack-findings.md (20 kV / 5 mA avalanche stick class: I_R 2 uA at 25 C, 5 uA at 100 C); "
              "sim/hub_rings_build.py LEAKAGE (tens of nA at a third of the rating)",
    "clamps": "docs/ledger/DCCREG-design-ledger.md §3.4 (66 x 200 V); sim/core_field.py DZ",
}
VT = 8.617333262e-5 * 300.15       # kT/q at ngspice's 27 C (TNOM = TEMP) [OC]
RETRY_RELTOL = (3e-5, 1e-4)        # a run that stops early ("timestep too small") is redone looser [IR]


# ======================================================================================================== ngspice
def read_raw(path):
    """an ngspice binary rawfile (real, transient) -> {name: array}, names in lower case."""
    b = open(path, "rb").read()
    k = b.index(b"Binary:\n")
    head = b[:k].decode()
    nv = int(re.search(r"No. Variables:\s*(\d+)", head).group(1))
    names = re.findall(r"^\s*\d+\s+(\S+)\s+\S+\s*$", head.split("\nVariables:\n")[1], flags=re.M)
    d = np.frombuffer(b[k + 8:], dtype="<f8")
    d = d[: (d.size // nv) * nv].reshape(-1, nv)
    return {n.lower(): d[:, j].copy() for j, n in enumerate(names)}


def spice(txt, timeout=10800):
    """runs a deck whose .control block writes out.raw; returns (vectors or None, the log's error lines)."""
    with tempfile.TemporaryDirectory() as dd:
        open(os.path.join(dd, "x.cir"), "w").write(txt)
        r = subprocess.run(["ngspice", "-b", "x.cir"], capture_output=True, text=True, timeout=timeout, cwd=dd)
        err = [ln for ln in (r.stdout + r.stderr).splitlines() if "too small" in ln or "rror" in ln][:3]
        try:
            c = read_raw(os.path.join(dd, "out.raw"))
        except (OSError, ValueError, IndexError, AttributeError):
            c = None
    return c, err


def spice_retry(txt, t_end):
    """spice(); if the run stops before t_end, again with a looser reltol (RETRY_RELTOL) [IR]."""
    c, err = spice(txt)
    used = re.search(r"reltol=(\S+)", txt).group(1)
    for rt in RETRY_RELTOL:
        if c is not None and c["time"][-1] >= t_end * (1 - 1e-6):
            break
        txt = re.sub(r"reltol=\S+", f"reltol={rt:g}", txt)
        c, err = spice(txt)
        used = f"{rt:g}"
    done = c is not None and c["time"][-1] >= t_end * (1 - 1e-6)
    return c, err, float(used), done


def set_output(txt, vecs, extra_ctl=""):
    """the deck's 'wrdata out.dat ...' -> a binary rawfile of vecs."""
    return re.sub(r"^wrdata out\.dat .*$", extra_ctl + "set filetype=binary\nwrite out.raw " + " ".join(vecs), txt,
                  flags=re.M)


def add_lines(txt, lines):
    """element lines before the .ic line."""
    return txt.replace("\n.ic ", "\n" + "\n".join(lines) + "\n.ic ", 1)


def ic_of(txt):
    m = re.search(r"^\.ic (.*)$", txt, flags=re.M)
    return {k.lower(): float(v) for k, v in re.findall(r"v\((\w+)\)=(\S+)", m.group(1))}


def add_ic(txt, extra):
    return re.sub(r"^(\.ic .*)$", lambda m: m.group(1) + "".join(f" v({a})={b:.10g}" for a, b in extra.items()), txt,
                  count=1, flags=re.M)


def integrator(name, expr):
    """the decks' power integrator: a B source charging 1 F, so V(e_name) is the energy [IR, as the decks]."""
    return [f"Bp_{name} 0 e_{name} I='{expr}'", f"Cp_{name} e_{name} 0 1", f"Rp_{name} e_{name} 0 1e18"]


def window_power(c, name, t0, t1):
    y, t = c[f"v(e_{name.lower()})"], c["time"]
    return float((np.interp(t1, t, y) - np.interp(t0, t, y)) / (t1 - t0))


def tavg(t, y, s):
    """the time average of y over the samples s (trapezoid; the samples need not be uniform) [OC]."""
    ts, ys = t[s], y[s]
    return float(np.sum(0.5 * (ys[1:] + ys[:-1]) * np.diff(ts)) / (ts[-1] - ts[0]))


def fit_forward(points):
    """Is, N, Rs of the level-1 law V = N V_T ln(I / Is) + I Rs through three (I, V) points [OC: three linear
    equations in N V_T, -N V_T ln Is and Rs]."""
    A = np.array([[math.log(i), 1.0, i] for i, _ in points])
    a, c, r = np.linalg.solve(A, np.array([v for _, v in points]))
    return dict(Is=float(math.exp(-c / a)), N=float(a / VT), Rs=float(r))


def vf_of(p, i):
    return p["N"] * VT * math.log(i / p["Is"]) + i * p["Rs"]


# =================================================================================================== 1. magnetic
PICK = RP.PICK
_OP = json.load(open(os.path.join(HERE, "pole_design_variants_op.json")))["designs"][PICK]["best"]
KICK_REC = _OP["kick_frac"]                       # 0.2: the record's kick (sim/pole_design_variants_op.json)
SEED_OP = RP.SEED_FRAC                            # 0.3: the record's operating runs' seed (sim/rotor_parts_duty.py)
N_START, N_RUN, N_KICK = 40, RP.N_CYC, 80
START_AT = 0.5 * PD.AT_TARGET                     # 225 A-turns: the record's start criterion (sim/pole_design.py)
C_BYP = 22.0                                      # mF per coil, PROPOSED (sim/ah-steady-cusp-findings.md)
ESR = AS.ESR                                      # ohm [RH] (sim/ah_steady_cusp.py)
MAG_DIODES = (("D1s", "f2", "b"), ("D2s", "c", "f3"), ("D3s", "0", "d"), ("D4s", "0", "b"))   # name, anode, cathode
MAG_NODES = ("a", "b", "c", "d", "f2", "f3", "x1", "x2")
OPTS_MAG = ".options reltol=1e-5 abstol=1e-12 vntol=1e-6 gmin=1e-15 maxstep={ms:.4e} method=gear"
# the deck's own abstol 1e-15 / vntol 1e-9 stall ngspice at the first turn-off of a diode with stored charge (Tt);
# ngspice's default abstol / vntol run through, and the gate shows they leave the record's ND unchanged [IR]

# the device classes [IR datasheet-class, typical at 25 C]: three forward points (A, V) -> Is, N, Rs; C_J at 4 V with
# M and Vj -> Cjo; Tt from the class's trr (SPICE's storage time is about Tt ln(1 + I_F / I_R) = 0.4 Tt for the
# 0.5 A / 1 A / 0.25 A test); BV above the rating, IBV the class's maximum leakage
MAG_CLASSES = {
    "GP": dict(label="1N54xx class: 3 A / 200 V general-purpose Si, standard recovery",
               vf=((0.1, 0.72), (1.0, 0.85), (3.0, 0.95)), cj4=30e-12, m=0.45, vj=0.65, tt=5e-6, bv=260.0, ibv=5e-6,
               basis="V_F 0.72 / 0.85 / 0.95 V typical at 0.1 / 1 / 3 A (1.2 V max at 3 A); C_J 30 pF at 4 V; trr about "
                     "2 us (not specified for standard recovery); I_R <= 5 uA at V_RRM; BV taken 1.3 V_RRM"),
    "FR": dict(label="3 A / 200 V fast-recovery Si class",
               vf=((0.1, 0.78), (1.0, 0.95), (3.0, 1.10)), cj4=30e-12, m=0.45, vj=0.65, tt=0.5e-6, bv=260.0,
               ibv=5e-6, basis="V_F 0.78 / 0.95 / 1.10 V typical (1.3 V max at 3 A); C_J 30 pF at 4 V; trr 150-250 ns; "
                               "I_R <= 5 uA at V_RRM"),
    "SB": dict(label="3 A / 200 V Schottky class",
               vf=((0.1, 0.60), (1.0, 0.71), (3.0, 0.84)), cj4=150e-12, m=0.5, vj=0.5, tt=0.0, bv=230.0, ibv=50e-6,
               basis="V_F 0.60 / 0.71 / 0.84 V typical (about 0.9 V max at 3 A); C_J 150 pF at 4 V; no stored charge "
                     "(majority carriers); I_R tens of uA at V_RRM"),
    "SB100": dict(label="3 A / 100 V Schottky class (D3* / D4* of SBM only)",
                  vf=((0.1, 0.45), (1.0, 0.55), (3.0, 0.66)), cj4=250e-12, m=0.5, vj=0.5, tt=0.0, bv=120.0, ibv=100e-6,
                  basis="V_F 0.45 / 0.55 / 0.66 V typical; C_J 250 pF at 4 V; no stored charge"),
}
# which class sits in D1*, D2*, D3*, D4* per model; ND is the deck's own model
MAG_MODELS = {
    "ND": dict(label="the record's ND (n 1, Is 1 nA, Rs 1 mOhm; no C_J, no Tt, no BV)", sets=("ND",) * 4),
    "GP": dict(label=MAG_CLASSES["GP"]["label"], sets=("GP",) * 4),
    "FR": dict(label=MAG_CLASSES["FR"]["label"], sets=("FR",) * 4),
    "SB": dict(label=MAG_CLASSES["SB"]["label"] + " in all four", sets=("SB",) * 4),
    "SBM": dict(label="200 V Schottky D1* / D2*, 100 V Schottky D3* / D4*", sets=("SB", "SB", "SB100", "SB100")),
}


def mag_params(cls, tt=None):
    q = MAG_CLASSES[cls]
    p = fit_forward(q["vf"])
    p.update(Cjo=q["cj4"] * (1 + 4.0 / q["vj"]) ** q["m"], M=q["m"], Vj=q["vj"], Tt=q["tt"] if tt is None else tt,
             BV=q["bv"], IBV=q["ibv"])
    return p


def mag_model_line(name, p):
    return (f".model {name} D(is={p['Is']:.6e} n={p['N']:.6g} rs={p['Rs']:.6g} cjo={p['Cjo']:.6g} m={p['M']:g} "
            f"vj={p['Vj']:g} tt={p['Tt']:.6g} bv={p['BV']:g} ibv={p['IBV']:g})")


def mag_deck(model, seed_frac, n_cyc, byp_mF, steps=2000, tt0=False, deck_options=False, light=False):
    """the pick's deck (sim/rotor_parts_duty.py _kw) with the seed, the bypass (sim/ah_steady_cusp.py), D1*-D4* of
    the model, a power integrator for the ESR, each diode's terminal current, power and charge current saved (@D[id]
    is the terminal current, charge current included: checked against a 0 V ammeter to 1e-6 A; an ammeter in series
    with a diode that stores charge stalls ngspice here, so none is used), and a binary rawfile."""
    kw = RP._kw(RP.TAU_FIXED)
    kw.update(seed=seed_frac * kw["psi_s"] / kw["L_max"], n_cyc=n_cyc, steps=steps)
    txt, vecs, info = M.deck(**kw)
    lines = []
    if byp_mF:                                                       # exactly sim/ah_steady_cusp.py's bypass
        c = byp_mF * 1e-3
        lines += [f"R_bypA x1 xb1 {ESR:g}", f"C_bypA xb1 d {c:g}", f"R_bypB x2 xb2 {ESR:g}", f"C_bypB xb2 b {c:g}"]
        lines += integrator("esr", f"(V(x1,xb1)*V(x1,xb1)+V(x2,xb2)*V(x2,xb2))/{ESR:g}")
    sets = MAG_MODELS[model]["sets"]
    models = {}
    for (nm, a, k), cls in zip(MAG_DIODES, sets):
        mname = "ND" if cls == "ND" else f"DM_{cls}"
        if cls != "ND":
            models[mname] = mag_model_line(mname, mag_params(cls, tt=0.0 if tt0 else None))
        line = f"{nm} {a} {k} ND"
        assert line in txt, line
        txt = txt.replace(line, f"{nm} {a} {k} {mname}")
    txt = add_lines(txt, list(models.values()) + lines)
    if byp_mF:
        txt = add_ic(txt, {"e_esr": 0.0})
    if not deck_options:
        ms = 1.0 / kw["F"] / steps
        txt = re.sub(r"^\.options .*$", OPTS_MAG.format(ms=ms), txt, flags=re.M)
    out = ["v(ps_L1)", "v(ps_L2)", "v(ps_AHt)", "v(ps_AHb)"]
    if not light:
        out += ["v(ps_La)", "v(ps_Lb)", "v(ps_Lp2)", "v(ps_Lp3)"] + [f"v({n})" for n in MAG_NODES]
        out += [f"v(sn_{n})" for n in MAG_NODES] + (["v(xb1)", "v(xb2)"] if byp_mF else [])
        out += [v for v in vecs if v.startswith("v(e_")] + (["v(e_esr)"] if byp_mF else [])
    dev = [f"@{nm.lower()}[{q}]" for nm, _, _ in MAG_DIODES for q in ("id", "p", "capcur")]
    txt = set_output(txt, out + ([] if light else dev), extra_ctl="" if light else "")
    if not light:
        txt = txt.replace(".control\n", ".control\nsave all " + " ".join(dev) + "\n", 1)
    return txt, kw, info


def _cur(c, t, which, kw):
    psi = c[f"v(ps_l{which})"]
    return psi / M._L(t, which, kw) * (1 + (psi / kw["psi_s"]) ** 6)       # the deck's saturating law [IR]


def settle(y, F, frac=0.95, band=0.02):
    """per-cycle values y: the final value (mean of the last 4), the time to reach frac of it and the time after
    which every cycle stays within +-band of it (the end of that cycle) [IR: the definitions]."""
    y = np.asarray(y, float)
    fin = float(np.mean(y[-4:]))
    hit = np.nonzero(y >= frac * fin)[0]
    t_hit = float((hit[0] + 1) / F) if len(hit) else None
    out = np.nonzero(np.abs(y / fin - 1) > band)[0]
    k_in = int(out[-1] + 1) if len(out) else 0
    t_in = float((k_in + 1) / F) if k_in < len(y) - 4 else None
    return dict(final=fin, t95_s=t_hit, t_settle_s=t_in, cycles95=None if t_hit is None else int(round(t_hit * F)),
                cycles_settle=None if t_in is None else int(round(t_in * F)))


def recovery(t, i, v, s, i_floor=1e-4):
    """each turn-off of a diode in the window s: the negative current lobe that follows the zero crossing (until the
    current is back within 2 % of its reverse peak, or turns positive). Q_rr (its charge), I_rr, its duration, the
    energy the diode itself takes in it, and the count [OC: integrals of the run's own current]."""
    ts, is_, vs = t[s], i[s], v[s]
    ev = []
    k = 1
    while k < len(is_):
        if is_[k - 1] > 0 >= is_[k]:
            j, jm = k, k
            while j < len(is_) and is_[j] <= 0:
                if is_[j] < is_[jm]:
                    jm = j
                if j > jm and is_[j] > 0.02 * is_[jm]:
                    break
                j += 1
            j = min(j, len(is_) - 1)
            seg = slice(k - 1, j + 1)
            q = -float(np.sum(0.5 * (is_[seg][1:] + is_[seg][:-1]) * np.diff(ts[seg])))
            e = float(np.sum(0.5 * ((vs * is_)[seg][1:] + (vs * is_)[seg][:-1]) * np.diff(ts[seg])))
            if -is_[jm] > i_floor:
                ev.append(dict(t=float(ts[k]), Q_C=q, I_rr_A=float(-is_[jm]), dur_s=float(ts[j] - ts[k - 1]), E_J=e))
            k = j + 1
        else:
            k += 1
    if not ev:
        return dict(n=0, Q_rr_C=0.0, I_rr_A=0.0, dur_s=0.0, E_in_diode_J=0.0)
    return dict(n=len(ev), Q_rr_C=float(np.mean([e["Q_C"] for e in ev])), I_rr_A=float(max(e["I_rr_A"] for e in ev)),
                dur_s=float(np.mean([e["dur_s"] for e in ev])), E_in_diode_J=float(np.mean([e["E_J"] for e in ev])))


def mag_stored(c, kw, info, byp_mF, tk):
    """the energy stored at time tk: the six coils' and the two strays' (L1, L2 by the saturating law at their own
    angle), the snubbers' and the bypass capacitors' [OC]."""
    g = lambda name: float(np.interp(tk, c["time"], c[name]))
    psi_s = kw["psi_s"]
    w = 0.0
    for which in (1, 2):
        p = g(f"v(ps_l{which})")
        L = float(M._L(np.array([tk]), which, kw)[0])
        w += p * p / (2 * L) + p ** 8 / (8 * L * psi_s ** 6)
    h = kw["ah_custom"]
    for nm, L in (("aht", h["L"]), ("ahb", h["L"]), ("la", info["la"]), ("lb", info["la"]), ("lp2", info["lp"]),
                  ("lp3", info["lp"])):
        w += g(f"v(ps_{nm})") ** 2 / (2 * L)
    csn = M.CSNUB * (M.L_MAX / kw["L_max"]) * (60.0 / kw["F"]) ** 2
    for n in MAG_NODES:
        w += 0.5 * csn * (g(f"v({n})") - g(f"v(sn_{n})")) ** 2
    if byp_mF:
        w += 0.5 * byp_mF * 1e-3 * ((g("v(xb1)") - g("v(d)")) ** 2 + (g("v(xb2)") - g("v(b)")) ** 2)
    return w


def mag_job(job):
    """one run of the pick: job = dict(model, seed, n_cyc, byp, steps, tt0, deck_options, light)."""
    t_start = time.time()
    model, seed, n, byp = job["model"], job["seed"], job["n_cyc"], job["byp"]
    txt, kw, info = mag_deck(model, seed, n, byp, steps=job.get("steps", 2000), tt0=job.get("tt0", False),
                             deck_options=job.get("deck_options", False), light=job.get("light", False))
    F = kw["F"]
    T = 1.0 / F
    c, err, rt, done = spice_retry(txt, n * T)
    out = dict(job=job, reltol=rt, done=done, err=err, run_s=None)
    if c is None or not done:
        out["run_s"] = time.time() - t_start
        return out
    t = c["time"]
    h = kw["ah_custom"]
    i1, i2 = _cur(c, t, 1, kw), _cur(c, t, 2, kw)
    cyc = np.floor(t / T).astype(int)
    pk = [float(max(np.abs(i1[cyc == k]).max(), np.abs(i2[cyc == k]).max())) for k in range(n)]
    pk1 = [float(np.abs(i1[cyc == k]).max()) for k in range(n)]
    z = [pk[k + 1] / pk[k] for k in range(n - 1) if pk[k] > 0]
    sel = t >= (n - 4) * T
    at_pk = h["N"] * float(np.abs(i1[sel]).max())
    iA, iB = c["v(ps_aht)"] / h["L"], c["v(ps_ahb)"] / h["L"]
    coil_mean = [h["N"] * tavg(t, np.abs(iA), cyc == k) for k in range(n)]
    out.update(z_early=float(np.median(z[2:8])) if len(z) > 8 else None,
               z_late=float(np.median(z[-5:])) if len(z) > 5 else None,
               AH_AT_pk=at_pk, starts=bool(at_pk > START_AT), branch_AT_per_cycle=[h["N"] * x for x in pk1],
               coil_AT_mean_per_cycle=coil_mean, seed_A=kw["seed"])
    if job.get("light"):
        out["run_s"] = time.time() - t_start
        return out
    out["settle_branch"] = settle([h["N"] * x for x in pk1], F)
    out["settle_coil"] = settle(coil_mean, F)
    t0, t1 = (n - 4) * T, float(t[-1])
    keys = sorted({k[4:-1] for k in c if k.startswith("v(e_")})
    P = {k: window_power(c, k, t0, t1) for k in keys}
    mech = sum(v for k, v in P.items() if k.startswith("mech_"))
    cu_ut = P["cu_l1"] + P["cu_l2"]
    cu_fx = sum(v for k, v in P.items() if k.startswith("cu_l")) - cu_ut
    p_ah = P["cu_aht"] + P["cu_ahb"]
    p_d = {nm: tavg(t, c[f"@{nm.lower()}[p]"], sel) for nm, _, _ in MAG_DIODES}    # terminal power, trapezoid
    p_esr = P.get("esr", 0.0)
    dW = (mag_stored(c, kw, info, byp, t1) - mag_stored(c, kw, info, byp, t0)) / (t1 - t0)
    diss = cu_ut + cu_fx + p_ah + P["snub"] + sum(p_d.values()) + p_esr
    out.update(P_belt_W=mech, P_cu_utron_W=cu_ut, P_cu_fixed_W=cu_fx, P_AH_W=p_ah, P_snub_W=P["snub"],
               P_diodes_W=sum(p_d.values()), P_esr_W=p_esr, dW_stored_W=dW,
               balance=dict(residual_W=mech - diss - dW, residual_frac=(mech - diss - dW) / mech,
                            note="belt - (copper + AH + snubbers + diodes + ESR) - dW/dt over the last 4 cycles"))
    for nm, i in (("top", iA), ("bottom", iB)):                        # AHt / AHb (sim/ah-steady-cusp-findings.md)
        a = np.abs(i[sel]) * h["N"]
        out[nm] = dict(AT_min=float(a.min()), AT_max=float(a.max()), AT_mean_samples=float(a.mean()),
                       AT_mean=tavg(t, np.abs(i) * h["N"], sel), ripple_pp_frac=float((a.max() - a.min()) / a.mean()))
    out["dAT_max"] = float(np.max(np.abs(np.abs(iA[sel]) - np.abs(iB[sel]))) * h["N"])
    out["I1_pk_A"] = float(np.abs(i1[sel]).max())
    dio = {}
    for nm, a, k in MAG_DIODES:
        i = c[f"i(@{nm.lower()}[id])"]
        v = (0.0 if a == "0" else c[f"v({a})"]) - c[f"v({k})"]
        rec = recovery(t, i, v, sel)
        ev_per_s = rec["n"] / (t1 - t0)
        vr = float((-v[sel]).max())
        dio[nm.replace("s", "*")] = dict(
            P_W=p_d[nm], I_avg_A=tavg(t, i, sel), I_rms_A=math.sqrt(tavg(t, i * i, sel)), I_pk_A=float(i[sel].max()),
            VR_pk_V=vr, VR_pk_whole_run_V=float((-v).max()), I_rev_min_A=float(i[sel].min()),
            turn_offs_per_s=ev_per_s, Q_rr_C=rec["Q_rr_C"], I_rr_A=rec["I_rr_A"], t_rr_s=rec["dur_s"],
            E_rr_in_diode_J=rec["E_in_diode_J"], P_rr_bound_W=rec["Q_rr_C"] * vr * ev_per_s,
            Q_charges_per_cycle_C=0.5 * tavg(t, np.abs(c[f"@{nm.lower()}[capcur]"]), sel) / F)   # in and out, halved
    out["diodes"] = dio
    out["run_s"] = time.time() - t_start
    return out


def mag_threshold(args):
    """the smallest kick (fraction of Psi_s) that passes the record's criterion, by bisection to 0.005; each trial
    keeps the ratio of its last four cycles' branch peak to its first four's (below 1: it decays, not a slow start)."""
    model, byp = args
    trials = {}

    def starts(f):
        f = round(f, 5)
        if f not in trials:
            r = mag_job(dict(model=model, seed=f, n_cyc=N_START, byp=byp, light=True))
            y = r.get("branch_AT_per_cycle") or [float("nan")] * 4
            trials[f] = dict(frac=f, starts=r.get("starts"), AH_AT_pk=r.get("AH_AT_pk"), z_early=r.get("z_early"),
                             growth_last_over_first=float(np.mean(y[-4:]) / np.mean(y[1:5])), done=r.get("done"),
                             reltol=r.get("reltol"))
        return bool(trials[f]["starts"])
    lo, hi = 0.10, 0.42
    while not starts(hi) and hi < 1.5:
        lo, hi = hi, hi * 1.5
    while starts(lo) and lo > 0.005:
        hi, lo = lo, lo / 2
    while hi - lo > 0.005:
        mid = round(0.5 * (lo + hi), 5)
        if starts(mid):
            hi = mid
        else:
            lo = mid
    r, b, f, Lmax = RP.pick()
    return dict(model=model, byp_mF=byp, frac_starts=hi, frac_fails=lo,
                kick_at_threshold=PD.kick_seed(r, b["N_u"], RP.LA_RATIO, b["psi_s"], hi),
                trials=[trials[f] for f in sorted(trials)])


# ============================================================================================== 2. electrostatic
_HRB = json.load(open(os.path.join(HERE, "hub_rings_build_results.json")))
REC_SUP, REC_FREE = _HRB["record_supply"], _HRB["record_supply_free"]
ES_KW = {k: REC_SUP[k] for k in ("opt", "n_cw", "n_cw_a", "c_core", "c_cw", "r_leak", "a_ref")}
ES_NCYC, ES_STEPS = REC_SUP["n_cyc"], REC_SUP["steps"]           # 280 cycles, 10000 steps a cycle
ES_FREE = dict(clamp=False, n_cyc=REC_FREE["n_cyc"], v0=REC_FREE["v0"])   # 12 cycles from -10 V
V0_CLAMPED = -1000.0                                             # sim/core_field.py deck's default seed (nodes 1, 4)
OUT_PER_CYCLE = 1000                                             # interpolated output points a cycle [IR]
STICK_KV = 20.0                                                  # one stick's V_RRM (the class)
STICK = dict(label="HV rectifier stick, 20 kV / 5 mA avalanche class, fast recovery",
             n_j=20, n_per_j=1.8, vf=((1e-3, 17.0), (5e-3, 20.0)), cj0_j=30e-12, m=0.33, vj_j=0.7, tt=100e-9,
             bv=24e3, ibv=10e-6, nbv_j=1.0,
             basis="20 junctions of the 1 kV class in series [IR]; V_F 17 V at 1 mA and 20 V at 5 mA (about 1 V a "
                   "junction at rated current) with N 1.8 a junction; 30 pF a junction at 0 V (1.5 pF the stick) "
                   "graded M 0.33; trr <= 100 ns (fast class); avalanche BV 1.2 V_RRM; leakage typ 25 nA at 7.5 kV "
                   "(the ledger's basis), max 2 uA at 25 C / 5 uA at 100 C (sim/diode-stack-findings.md)")
LEAK = dict(typ=25e-9, max=2e-6, hot=5e-6)                       # A per stick (string) at its working reverse voltage
ZLEAK = dict(typ=10e-9, max=0.5e-6, hot=5e-6)                    # A per clamp string [IR; hot: RH]
V_LEAK = 250.0                                                   # V: the leakage element's N V_T (saturates by ~0.75 kV) [RH]
CLAMP = dict(label="66 avalanche (Zener) diodes of the 200 V / 5 W class in series", n=66, nbv_vt_dev=2.5, rs_dev=10.0,
             cj0_dev=60e-12, m=0.4, vj_dev=0.7,
             basis="per device: dynamic impedance 2.5 V / I (2.5 kOhm at 1 mA, 500 Ohm at 5 mA), 10 Ohm bulk, 60 pF at "
                   "0 V; I_R <= 0.5 uA at 0.76 V_Z (typ 10 nA); the string trimmed by whole parts so its voltage at the "
                   "record's clamp peak current is the record's node peak")
C_BODY = 1e-12                                                   # F per stick, the body / lead capacitance [RH]
TT_SLOW = 3e-6                                                   # s, a standard-recovery stick [IR]
ES_MODELS = {
    "ND-deck": dict(label="the record's deck as is: ND (n 0.005) and DZ", real=False, split=False, exact=True),
    "ND-ic": dict(label="the record's ND, varicaps as the deck, run as the new runs are (the deck's maximum step, "
                        "the output interpolated)", real=False, split=False),
    "ND": dict(label="the record's ND, varicaps split (a consistent -1 kV seed)", real=False, split=True),
    "HV-fwd": dict(label="sticks: the forward law only (no C_J, Tt, leakage); clamps: the avalanche law only",
                   real=True, cj=False, tt=0.0, leak=None),
    "HV-noleak": dict(label="sticks with C_J and Tt 100 ns, no leakage", real=True, cj=True, tt=STICK["tt"], leak=None),
    "HV-typ": dict(label="sticks and clamps with typical leakage (25 nA / 10 nA)", real=True, cj=True, tt=STICK["tt"],
                   leak="typ"),
    "HV-max": dict(label="the datasheet maximum leakage at 25 C (2 uA / 0.5 uA)", real=True, cj=True, tt=STICK["tt"],
                   leak="max"),
    "HV-hot": dict(label="hot leakage, 100 C (5 uA / 5 uA)", real=True, cj=True, tt=STICK["tt"], leak="hot"),
    "HV-VF2": dict(label="typical leakage, V_F x 2 (40 V at 5 mA a stick)", real=True, cj=True, tt=STICK["tt"],
                   leak="typ", vf_k=2.0),
    "HV-body": dict(label="typical leakage + 1 pF body capacitance a stick", real=True, cj=True, tt=STICK["tt"],
                    leak="typ", c_body=C_BODY),
    "HV-slow": dict(label="typical leakage, a slow stick (Tt 3 us)", real=True, cj=True, tt=TT_SLOW, leak="typ"),
}


def stick_params(ns, vf_k=1.0):
    """a string of ns sticks as one level-1 diode [IR]: N = ns n_j n, Is and Rs fitted to the stick's two forward
    points (x ns, x vf_k); BV and NBV x ns. ngspice's level-1 capacitance stalls once Vj passes about 2 V (checked
    here: 'timestep too small' when the junction reaches 1 V forward for Vj >= 3 V), so the string's junction law
    C0 / (1 + V / (N_j 0.7 V))^M is carried as Cjo' / (1 + V / 0.7 V)^M with Cjo' matching it at 1 kV reverse."""
    S = STICK
    nn = S["n_j"] * S["n_per_j"] * ns * vf_k
    a = nn * VT
    (i1, v1), (i2, v2) = S["vf"]
    v1, v2 = v1 * ns * vf_k, v2 * ns * vf_k
    rs = (v2 - v1 - a * math.log(i2 / i1)) / (i2 - i1)             # two points, N fixed [OC]
    is_ = i1 / math.exp((v1 - i1 * rs) / a)
    nj = S["n_j"] * ns
    c0 = S["cj0_j"] / nj
    vref = 1000.0
    c_ref = c0 / (1 + vref / (nj * S["vj_j"])) ** S["m"]
    cjo = c_ref * (1 + vref / 0.7) ** S["m"]
    return dict(Is=is_, N=nn, Rs=rs, Cjo=cjo, M=S["m"], Vj=0.7, Tt=S["tt"], BV=S["bv"] * ns, IBV=S["ibv"],
                NBV=S["nbv_j"] * nj, C_true_0V=c0, C_at_1kV=c_ref, C_at_7p5kV=c0 / (1 + 7500.0 / (nj * 0.7)) ** S["m"])


def clamp_params(v_target, i_target):
    """the clamp string [IR]: BV (at IBV 1 mA) set so that V(i_target) = v_target; NBV = 66 x 2.5 V / V_T."""
    C = CLAMP
    nbv = C["n"] * C["nbv_vt_dev"] / VT
    rs = C["n"] * C["rs_dev"]
    ibv = 1e-3
    bv = v_target - nbv * VT * math.log(i_target / ibv) - rs * i_target
    c0 = C["cj0_dev"] / C["n"]
    c_ref = c0 / (1 + 1000.0 / (C["n"] * C["vj_dev"])) ** C["m"]
    return dict(Is=1e-12, N=float(C["n"]), Rs=rs, BV=bv, IBV=ibv, NBV=nbv, Cjo=c_ref * (1 + 1000.0 / 0.7) ** C["m"],
                M=C["m"], Vj=0.7, V_Z_dev=bv / C["n"])


CLAMP_P = clamp_params(-REC_SUP["V"]["1"]["min"] * 1e3, REC_SUP["Z1"]["I_pk_mA"] * 1e-3)   # the record's 13.227 kV


def _vr_rec():
    """the record's reverse peaks per position (kV): sticks per position by the x2-rated guidance [IR]."""
    vr = REC_SUP["VR_pk_kV"]
    return {k: vr[k] for k in vr}


def split_varicaps(txt):
    """each varicap = a linear capacitor at its t = 0 value (it takes the .ic under uic) + a charge-defined part
    (C(t) - C(0)) V, zero at t = 0 [IR]; the same C(t) [OC]."""
    for k in ("1", "2"):
        mm = re.search(rf"^C{k}v (\w+) s Q='\((.*)\)\*V\((\w+),s\)'$", txt, flags=re.M)
        node, cexpr = mm.group(1), mm.group(2)
        c0 = eval(cexpr.replace("cos(", "math.cos(").replace("time", "0.0"), {"math": math})
        txt = txt.replace(mm.group(0), f"C{k}v0 {node} s {c0:.10e}\nC{k}v {node} s Q='(({cexpr})-{c0:.10e})*V({node},s)'")
    return txt


def diode_line(name, p):
    return (f".model {name} D(is={p['Is']:.6e} n={p['N']:.6g} rs=0 cjo={p.get('Cjo', 0.0):.6g} m={p.get('M', 0.5):g} "
            f"vj={p.get('Vj', 0.7):g} tt={p.get('Tt', 0.0):.6g} bv={p['BV']:.8g} ibv={p['IBV']:g} nbv={p['NBV']:.8g})")


def es_deck(model, kw_over, steps=ES_STEPS):
    """the record's dc deck (sim/core_field.py, the record_supply settings) for one variant."""
    spec = ES_MODELS[model]
    kw = dict(ES_KW, **kw_over)
    kw.setdefault("steps", steps)
    txt, vecs, pk = CF.deck(**kw)
    n, F = kw["n_cyc"], CF.F
    T = 1.0 / F
    clamp = kw.get("clamp", True)
    if spec.get("exact"):                                            # the gate: the deck as the record runs it
        out = ["v(1)", "v(4)", "v(ea)", "v(eb)"] + [f"v(e_{k})" for k in pk] + (["i(Vz1)", "i(Vz4)"] if clamp else [])
        return set_output(txt, out), kw, pk, []
    if spec.get("split"):
        txt = split_varicaps(txt)
    ic = ic_of(txt)
    icv = lambda node: 0.0 if node == "0" else ic.get(node.lower(), 0.0)
    dio = re.findall(r"^(D\w+) (\w+) (\w+) ND$", txt, flags=re.M)
    vr = _vr_rec()
    lines, models, new_ic = [], {}, {}
    real = spec["real"]
    leak = spec.get("leak")
    vf_k = spec.get("vf_k", 1.0)
    for nm, a, k in dio:
        key = "D" + nm[2:] if nm.startswith("Dd") else nm
        ns = 1 if 2 * vr[key] <= STICK_KV else 2                      # the record's x2-rated guidance [IR]
        if not real:              # the record's ND as the deck has it: an ammeter in series with ND stalls ngspice, and
            continue              # ND's own @D[id] / @D[p] are spurious (spikes of amperes); the ND diodes' loss is the
            #                       energy balance's remainder, as the record's P_other
        # a stick string: 0 V ammeter, its series resistance (an explicit node, so it takes an .ic), the junction
        # string with ic = its t = 0 voltage, the leakage element across both, a body capacitance if asked [IR]
        rep = [f"Vam_{nm} {a} {nm}_a 0"]
        vd0 = icv(a) - icv(k)
        p = stick_params(ns, vf_k)
        if not spec["cj"]:
            p["Cjo"] = 0.0
        p["Tt"] = spec["tt"]
        mname = f"DS{ns}"
        models[mname] = diode_line(mname, p)
        rep += [f"R_{nm} {nm}_a {nm}_j {p['Rs']:.6g}", f"{nm} {nm}_j {k} {mname} ic={vd0:.10g}"]
        new_ic[f"{nm}_j"] = icv(a)
        if leak:
            models[f"DL{ns}"] = f".model DL{ns} D(is={LEAK[leak]:.6g} n={V_LEAK / VT:.8g} rs=0 cjo=0)"
            rep.append(f"{nm}L {nm}_a {k} DL{ns} ic={vd0:.10g}")
        if spec.get("c_body"):
            rep.append(f"Cbody_{nm} {nm}_a {k} {spec['c_body'] / ns:.6g}")
        new_ic[f"{nm}_a"] = icv(a)
        txt = txt.replace(f"{nm} {a} {k} ND", "\n".join(rep))
        va = "0" if a == "0" else f"V({a})"
        vk = "0" if k == "0" else f"V({k})"
        lines += integrator(f"pd_{nm}", f"({va}-{vk})*i(Vam_{nm})")
        new_ic[f"e_pd_{nm}"] = 0.0
    if real and clamp:
        p = dict(CLAMP_P)
        if not spec["cj"]:
            p["Cjo"] = 0.0
        txt = re.sub(r"^\.model DZ D\(.*\)$", diode_line("DZS", p), txt, flags=re.M)
        if leak:
            models["DZL"] = f".model DZL D(is={ZLEAK[leak]:.6g} n={V_LEAK / VT:.8g} rs=0 cjo=0)"
        for z, node in (("z1", "1"), ("z4", "4")):
            rep = [f"D{z} {node} j{z} DZS ic={icv(node):.10g}", f"R{z} j{z} {z} {p['Rs']:.6g}"]
            if leak:
                rep.append(f"D{z}L {node} {z} DZL ic={icv(node):.10g}")
            txt = txt.replace(f"D{z} {node} {z} DZ", "\n".join(rep))
            new_ic[f"j{z}"] = 0.0
    lines += integrator("link", f"V(s)*V(s)/{CF.R_LINK:g}")
    new_ic["e_link"] = 0.0
    txt = add_lines(txt, list(models.values()) + lines)
    txt = add_ic(txt, new_ic)
    nodes = ["1", "2", "3", "4", "s", "ea", "eb", "m1", "m2", "b1", "n1", "n2", "a1"]
    out = [f"v({x})" for x in nodes] + (["i(Vz1)", "i(Vz4)"] if clamp else []) + [f"v(e_{k})" for k in pk] + ["v(e_link)"]
    out += ([f"i(Vam_{nm})" for nm, _, _ in dio] + [f"v(e_pd_{nm})" for nm, _, _ in dio]) if real else []
    # the same maximum step as the deck (T / steps), the output interpolated to OUT_PER_CYCLE points a cycle [IR]
    ms = T / kw["steps"]
    txt = re.sub(r"^tran \S+ (\S+) uic$", lambda m_: f"tran {T / OUT_PER_CYCLE:.6e} {m_.group(1)} 0 {ms:.6e} uic", txt,
                 flags=re.M)
    txt = re.sub(r"^(\.options .*)$", r"\1 interp", txt, flags=re.M)
    return set_output(txt, out), kw, pk, dio


def es_caps(txt):
    """the deck's linear capacitors (name, a, b, C) for the stored-energy check."""
    return [(m[0], m[1], m[2], float(m[3])) for m in re.findall(r"^(C\w+) (\w+) (\w+) ([0-9.eE+-]+)$", txt, flags=re.M)
            if not m[0].startswith("Cp_")]


def es_stored(c, txt, tk, alias=None):
    """the energy stored at time tk in the deck's capacitors and the two varicaps (C(t) at tk) [OC]; alias maps an
    ammeter's node to the node it follows (the 0 V source)."""
    alias = alias or {}

    def g(node):
        node = alias.get(node.lower(), node.lower())
        return 0.0 if node == "0" else float(np.interp(tk, c["time"], c[f"v({node})"]))
    w = sum(0.5 * C * (g(a) - g(b)) ** 2 for nm, a, b, C in es_caps(txt) if not nm.startswith(("C1v0", "C2v0")))
    w_ = 2 * math.pi * CF.F
    c1 = CF.CMIN + (CF.CMAX - CF.CMIN) * 0.5 * (1 + math.cos(w_ * tk))
    c2 = CF.CMIN + (CF.CMAX - CF.CMIN) * 0.5 * (1 - math.cos(w_ * tk))
    return w + 0.5 * c1 * (g("1") - g("s")) ** 2 + 0.5 * c2 * (g("4") - g("s")) ** 2


def es_job(job):
    """one electrostatic run: job = dict(model, case: 'clamped' | 'free', v0, steps)."""
    t_start = time.time()
    model = job["model"]
    over = dict(ES_FREE) if job["case"] == "free" else dict(n_cyc=ES_NCYC)
    over["v0"] = job.get("v0", over.get("v0", V0_CLAMPED))
    txt, kw, pk, dio = es_deck(model, over, steps=job.get("steps", 20000 if job["case"] == "free" else ES_STEPS))
    n, F = kw["n_cyc"], CF.F
    T = 1.0 / F
    c, err, rt, done = spice_retry(txt, n * T)
    out = dict(job=job, reltol=rt, done=done, err=err)
    if c is None or not done:
        out["run_s"] = time.time() - t_start
        return out
    t = c["time"]
    cyc = [(t >= k * T) & (t < (k + 1) * T) for k in range(n)]
    pk1 = [float(np.abs(c["v(1)"][m]).max()) for m in cyc]
    out["V1_peak_per_cycle_kV"] = [p / 1e3 for p in pk1]
    vk = [float(-(c["v(eb)"][m] - c["v(ea)"][m]).max() / 1e3) for m in cyc]   # as sim/core_field.py run
    out["Vk_per_cycle_kV"] = vk
    out["z_per_cycle"] = [pk1[k + 1] / pk1[k] for k in range(n - 1)]
    if job["case"] == "free":                                       # the gain per cycle, as sim/core_field.py run
        k = np.arange(3, n)
        out["z"] = float(math.exp(np.polyfit(k, np.log(np.array(pk1[3:n])), 1)[0]))
        out["grows"] = bool(out["z"] > 1.0)
        out["run_s"] = time.time() - t_start
        return out
    vka = np.array(vk)
    fin = vka[-3:].mean()
    hit = np.nonzero(vka <= 0.95 * fin)[0]
    out.update(Vk_final_kV=float(fin), cycles_to_95pc=int(hit[0]) + 1 if len(hit) else None,
               t_to_95pc_s=(int(hit[0]) + 1) / F if len(hit) else None)
    clamp_on = next((k for k in range(n) if pk1[k] >= 0.99 * max(pk1)), None)
    out["z_min_before_clamp"] = float(min(out["z_per_cycle"][1:max(2, clamp_on - 1)])) if clamp_on else None
    s = t >= (n - 8) * T
    t0, t1 = (n - 8) * T, float(t[-1])
    exact = ES_MODELS[model].get("exact", False)
    P = {k: window_power(c, k, t0, t1) for k in list(pk) + ([] if exact else ["link"])}
    st = lambda y: dict(mean=tavg(t, y, s), min=float(y[s].min()), max=float(y[s].max()), pp=float(y[s].max() - y[s].min()))
    out["V_ea_kV"], out["V_eb_kV"] = st(c["v(ea)"] / 1e3), st(c["v(eb)"] / 1e3)
    out["V_ea_mean_samples_kV"] = float(np.mean(c["v(ea)"][s]) / 1e3)      # the record's statistic (sample mean)
    out["V_eb_mean_samples_kV"] = float(np.mean(c["v(eb)"][s]) / 1e3)
    out["V_gap_kV"] = st((c["v(eb)"] - c["v(ea)"]) / 1e3)
    out["ripple_A_V"], out["ripple_B_V"] = out["V_ea_kV"]["pp"] * 1e3, out["V_eb_kV"]["pp"] * 1e3
    out.update(P_belt_W=P["belt"], P_clamps_W=P["limit"], P_ring_leak_W=P["leak"])
    for z_, node in (("Z1", "1"), ("Z4", "4")):
        i = c[f"i(vz{z_[1]})"]
        p = tavg(t, -c[f"v({node})"] * i, s)
        out[z_] = dict(I_avg_mA=tavg(t, i, s) * 1e3, I_pk_mA=float(i[s].max() * 1e3), P_W=p,
                       P_per_device_W=p / CLAMP["n"], V_node_pk_kV=float(-c[f"v({node})"][s].min() / 1e3))
    if exact:
        out["run_s"] = time.time() - t_start
        return out
    real = ES_MODELS[model]["real"]
    p_st = {nm: window_power(c, f"pd_{nm}", t0, t1) for nm, _, _ in dio} if real else {}
    alias = {f"{nm}_a".lower(): a for nm, a, _ in dio} if real else {}
    dW = (es_stored(c, txt, t1, alias) - es_stored(c, txt, t0, alias)) / (t1 - t0)
    other = P["belt"] - P["limit"] - P["leak"] - P["link"] - dW
    out.update(P_link_W=P["link"], dW_stored_W=dW, P_other_W=other)
    if real:                                                        # every dissipation integrated: a closed balance
        res = other - sum(p_st.values())
        out.update(P_stacks_W=sum(p_st.values()),
                   balance=dict(residual_W=res, residual_frac=res / P["belt"],
                                note="belt - clamps - rings' leakage - link - stacks - dW/dt over the last 8 cycles"))
    out["V_kV"] = {x: st(c[f"v({x})"] / 1e3) for x in ("1", "2", "3", "4")}
    spec = ES_MODELS[model]
    stacks = {}
    for nm, a, kk in dio:
        va = 0.0 if a == "0" else c[f"v({a})"]
        vkk = 0.0 if kk == "0" else c[f"v({kk})"]
        v = va - vkk
        key = "D" + nm[2:] if nm.startswith("Dd") else nm
        q = dict(VR_pk_kV=float((-v[s]).max() / 1e3), VR_mean_kV=tavg(t, -v, s) / 1e3)
        if real:
            i = c[f"i(vam_{nm.lower()})"]
            q.update(P_W=p_st[nm], I_avg_uA=tavg(t, i, s) * 1e6, I_pk_mA=float(i[s].max() * 1e3))
        if spec.get("leak"):                                        # the leakage element's own law [OC]
            il = LEAK[spec["leak"]] * (np.exp(v / V_LEAK) - 1.0)
            q.update(I_leak_avg_nA=-tavg(t, il, s) * 1e9, P_leak_W=tavg(t, v * il, s))
        stacks[key] = q
    out["stacks"] = stacks
    out["run_s"] = time.time() - t_start
    return out


def es_threshold(model):
    """the smallest seed |v0| (nodes 1 and 4) from which the free run grows (z > 1, the record's fit), by bisection
    in log |v0| between 1 V and 1 kV to 3 %."""
    trials = []

    def grows(v):
        r = es_job(dict(model=model, case="free", v0=-v))
        trials.append(dict(v0_V=-v, z=r.get("z"), grows=r.get("grows"), done=r.get("done"), reltol=r.get("reltol"),
                           V1_peak_per_cycle_kV=r.get("V1_peak_per_cycle_kV")))
        return bool(r.get("grows"))
    lo, hi = 1.0, 1000.0
    if grows(lo):
        return dict(model=model, v_grows_V=lo, v_fails_V=None, trials=trials)
    if not grows(hi):
        return dict(model=model, v_grows_V=None, v_fails_V=hi, trials=trials)
    while hi / lo > 1.03:
        mid = math.sqrt(lo * hi)
        if grows(mid):
            hi = mid
        else:
            lo = mid
    return dict(model=model, v_grows_V=hi, v_fails_V=lo, trials=sorted(trials, key=lambda q: -q["v0_V"]))


# ===================================================================================================== the jobs
def _dispatch(job):
    kind = job[0]
    if kind == "mag":
        return job, mag_job(job[1])
    if kind == "mag_thr":
        return job, mag_threshold(job[1])
    if kind == "es":
        return job, es_job(job[1])
    if kind == "es_thr":
        return job, es_threshold(job[1])
    raise ValueError(kind)


def mag_jobs_first():
    jobs = []
    for byp in (0.0, C_BYP):
        for dec in (True, False):                                   # the gate: the deck's options, and ours
            jobs.append(("mag", dict(model="ND", seed=SEED_OP, n_cyc=N_RUN, byp=byp, deck_options=dec, tag="gate")))
        for m in MAG_MODELS:
            jobs.append(("mag_thr", (m, byp)))
            jobs.append(("mag", dict(model=m, seed=KICK_REC, n_cyc=N_KICK, byp=byp, tag="kick")))
        for m in ("GP", "FR"):                                       # the cost of Tt: the same diodes without it
            if m in MAG_MODELS:
                jobs.append(("mag", dict(model=m, seed=SEED_OP, n_cyc=N_RUN, byp=byp, tt0=True, tag="tt0")))
    jobs.append(("mag", dict(model="GP", seed=SEED_OP, n_cyc=N_RUN, byp=C_BYP, steps=4000, tag="steps")))
    return jobs


def es_jobs():
    jobs = [("es", dict(model="ND-deck", case="clamped")), ("es", dict(model="ND-deck", case="free")),
            ("es", dict(model="ND-ic", case="clamped")), ("es", dict(model="ND-ic", case="free"))]
    for m in ES_MODELS:
        if m in ("ND-deck", "ND-ic"):
            continue
        jobs.append(("es", dict(model=m, case="clamped")))
        jobs.append(("es", dict(model=m, case="free", v0=ES_FREE["v0"])))
        jobs.append(("es", dict(model=m, case="free", v0=V0_CLAMPED)))
        if m in ("HV-fwd", "HV-typ", "HV-max", "HV-hot", "HV-VF2"):
            jobs.append(("es_thr", m))
    jobs.append(("es", dict(model="HV-typ", case="clamped", steps=2 * ES_STEPS, tag="steps")))
    return jobs


def _cost(job):
    """a rough run-time order, the longest first."""
    kind, j = job
    if kind == "mag_thr":
        return 8 * N_START * 2.5
    if kind == "es_thr":
        return 700
    if kind == "es":
        return (2 if j.get("model", "").startswith("HV") else 1) * (ES_NCYC if j["case"] == "clamped" else 12) * \
            j.get("steps", ES_STEPS) / ES_STEPS
    return j["n_cyc"] * j.get("steps", 2000) / 2000 * (1 if j["model"] == "ND" else 2.5)


def run_all(procs, only=None):
    jobs = []
    if only in (None, "mag"):
        jobs += mag_jobs_first()
    if only in (None, "es"):
        jobs += es_jobs()
    jobs.sort(key=lambda j: -_cost(j))
    res = []
    with Pool(procs) as pool:
        for job, r in pool.imap_unordered(_dispatch, jobs):
            res.append((job, r))
            tag = job[1]
            brief = {k: r.get(k) for k in ("done", "starts", "z_early", "AH_AT_pk", "z", "t_to_95pc_s", "frac_starts",
                                            "frac_fails", "v_grows_V", "v_fails_V", "P_belt_W", "run_s") if k in r}
            print(job[0], tag, json.dumps(brief, default=float)[:400], flush=True)
    # the steady states need the thresholds: seed max(SEED_OP, 1.25 x threshold)
    if only in (None, "mag"):
        thr = {(r["model"], r["byp_mF"]): r for job, r in res if job[0] == "mag_thr"}
        steady = []
        for (m, byp), q in thr.items():
            seed = max(SEED_OP, round(1.25 * q["frac_starts"], 3))
            steady.append(("mag", dict(model=m, seed=seed, n_cyc=N_RUN, byp=byp, tag="steady")))
        with Pool(procs) as pool:
            for job, r in pool.imap_unordered(_dispatch, steady):
                res.append((job, r))
                print(job[0], job[1], json.dumps({k: r.get(k) for k in ("done", "z_early", "AH_AT_pk", "P_belt_W")},
                                                 default=float), flush=True)
    return res


# ================================================================================================== the summary
def summarise(res, old=None):
    out = old or {}
    out.update(note="sim/diodes_real.py: both pumps of record with datasheet-class rectifiers (the ledger's §5.2 "
                    "'real-diode start-up'). Powers in W over the steady window; A-turns per AH coil (160 turns).",
               sources=SRC, tags="CONVENTIONS.md §1: [OC] derivable, [IR] modelling / datasheet-class choice, [RH] "
                                 "heuristic", V_T_V=VT)
    if any(j[0].startswith("mag") for j, _ in res):
        r0, b0, f0, Lmax0 = RP.pick()
        mg = dict(pick=PICK, F_Hz=f0, L_group_H=Lmax0, psi_s=b0["psi_s"], N_u=b0["N_u"], la_ratio=RP.LA_RATIO,
                  tau_fixed_s=RP.TAU_FIXED, kick_record_frac=KICK_REC, seed_operating_frac=SEED_OP,
                  kick_record=PD.kick_seed(r0, b0["N_u"], RP.LA_RATIO, b0["psi_s"], KICK_REC),
                  start_criterion=f"N_AH x the branch peak over the last 4 of {N_START} cycles > {START_AT:.0f} A-turns "
                                  "(sim/pole_design.py size_op)",
                  bypass=dict(C_mF=C_BYP, ESR_ohm=ESR, status="PROPOSED"), options=OPTS_MAG,
                  classes={k: dict(MAG_CLASSES[k], params=mag_params(k),
                                   VF_fit_V={str(i): vf_of(mag_params(k), i) for i in (0.1, 1.0, 3.0)})
                           for k in MAG_CLASSES},
                  models={k: dict(label=v["label"], D1s_D4s=v["sets"]) for k, v in MAG_MODELS.items()},
                  ND_VF_V={str(i): 1.0 * VT * math.log(i / 1e-9) + i * 1e-3 for i in (0.1, 1.0, 3.0)})
        thr, kick, steady, tt0, gate, steps = {}, {}, {}, {}, {}, None
        for job, r in res:
            if job[0] == "mag_thr":
                thr.setdefault(r["model"], {})["none" if not r["byp_mF"] else "22mF"] = r
            elif job[0] == "mag":
                j = job[1]
                key = "none" if not j["byp"] else "22mF"
                r = {k: v for k, v in r.items()}
                if j["tag"] == "kick":
                    kick.setdefault(j["model"], {})[key] = r
                elif j["tag"] == "steady":
                    steady.setdefault(j["model"], {})[key] = r
                elif j["tag"] == "tt0":
                    tt0.setdefault(j["model"], {})[key] = r
                elif j["tag"] == "gate":
                    gate.setdefault("deck_options" if j.get("deck_options") else "ours", {})[key] = r
                elif j["tag"] == "steps":
                    steps = r
        mg.update(thresholds=thr, kick=kick, steady=steady, tt0=tt0, gate_runs=gate, steps_run=steps)
        out["magnetic"] = mg
    if any(j[0].startswith("es") for j, _ in res):
        es = dict(record_kw=dict(ES_KW, n_cyc=ES_NCYC, steps=ES_STEPS), free_kw=ES_FREE, v0_clamped_V=V0_CLAMPED,
                  output_points_per_cycle=OUT_PER_CYCLE, stick=STICK, stick_V_RRM_kV=STICK_KV,
                  strings={str(ns): stick_params(ns) for ns in (1, 2)},
                  strings_vf2={str(ns): stick_params(ns, 2.0) for ns in (1, 2)},
                  leakage_per_stick_A=LEAK, leakage_per_clamp_A=ZLEAK, V_leak_V=V_LEAK, clamp=CLAMP, clamp_params=CLAMP_P,
                  sticks_per_position={k: (1 if 2 * v <= STICK_KV else 2) for k, v in _vr_rec().items()},
                  models={k: v["label"] for k, v in ES_MODELS.items()}, runs={}, thresholds={})
        for job, r in res:
            if job[0] == "es":
                j = job[1]
                name = j["case"] + ("" if j["case"] == "clamped" else f" {abs(j.get('v0', ES_FREE['v0'])):g} V")
                if j.get("tag") == "steps":
                    name = "clamped steps x2"
                es["runs"].setdefault(j["model"], {})[name] = r
            elif job[0] == "es_thr":
                es["thresholds"][r["model"]] = r
        out["electrostatic"] = es
    out["gates"] = gates(out)
    return out


def gates(out):
    g = []
    cusp = {r["C_byp_mF"]: r for r in json.load(open(os.path.join(HERE, "ah_steady_cusp_results.json")))["rows"]}
    duty = json.load(open(os.path.join(HERE, "rotor_parts_duty_results.json")))["la_lb"]["diode_VR_pk_V"]
    mg = out.get("magnetic")
    if mg and mg.get("gate_runs"):
        for basis, rows in mg["gate_runs"].items():
            for key, r in rows.items():
                rec = cusp[0.0 if key == "none" else C_BYP]
                if not r.get("done"):
                    g.append(dict(gate=f"G-MAG {basis} {key}", ok=False, note="the run did not finish"))
                    continue
                pairs = [("z_early", r["z_early"], rec["z_early"], 2e-3), ("P_belt_W", r["P_belt_W"], rec["P_belt_W"], 2e-3),
                         ("top AT_mean (samples)", r["top"]["AT_mean_samples"], rec["top"]["AT_mean"], 2e-3),
                         ("bottom AT_mean (samples)", r["bottom"]["AT_mean_samples"], rec["bottom"]["AT_mean"], 2e-3),
                         ("top AT_max", r["top"]["AT_max"], rec["top"]["AT_max"], 2e-3),
                         ("AH_AT_pk (branch)", r["AH_AT_pk"], rec["branch_AT_max"], 2e-3)]
                if key == "none":
                    pairs += [(f"VR {k}", r["diodes"][k]["VR_pk_V"], duty[k], 5e-3) for k in duty]
                rows_ = [dict(q=q, run=a, record=b, rel=(a - b) / b, ok=abs((a - b) / b) <= tol) for q, a, b, tol in pairs]
                g.append(dict(gate=f"G-MAG {basis} options, bypass {key}", ok=all(x["ok"] for x in rows_), rows=rows_,
                              record="sim/ah_steady_cusp_results.json" + (", sim/rotor_parts_duty_results.json" if key == "none" else "")))
        for m, rows in mg.get("steady", {}).items():
            for key, r in rows.items():
                if r.get("done"):
                    b = r["balance"]
                    g.append(dict(gate=f"G-ENERGY magnetic {m} {key}", ok=abs(b["residual_frac"]) < 5e-3,
                                  residual_W=b["residual_W"], residual_frac=b["residual_frac"], P_belt_W=r["P_belt_W"]))
        st = mg.get("steps_run")
        base = mg.get("steady", {}).get("GP", {}).get("22mF")
        if st and base and st.get("done") and base.get("done"):
            rows_ = [dict(q=q, steps4000=st[q] if not isinstance(st[q], dict) else st[q]["AT_mean"],
                          steps2000=base[q] if not isinstance(base[q], dict) else base[q]["AT_mean"]) for q in
                     ("z_early", "P_belt_W", "P_diodes_W", "top")]
            for x in rows_:
                x["rel"] = (x["steps4000"] - x["steps2000"]) / x["steps2000"]
            g.append(dict(gate="G-STEP magnetic GP 22 mF: steps 2000 -> 4000 a cycle",
                          ok=all(abs(x["rel"]) < 5e-3 for x in rows_), rows=rows_,
                          note=f"the seed differs if the steady seed is not {SEED_OP}" if base["job"]["seed"] != SEED_OP else ""))
    es = out.get("electrostatic")
    if es and es.get("runs"):
        R = es["runs"]
        for m in ("ND-deck", "ND-ic", "ND"):
            cl, fr = R.get(m, {}).get("clamped"), R.get(m, {}).get(f"free {abs(ES_FREE['v0']):g} V") or R.get(m, {}).get("free")
            if not (cl and cl.get("done")):
                continue
            pairs = [("ring A mean kV", cl["V_ea_kV"]["mean"], REC_SUP["V_ea_kV"]["mean"], 1e-3),
                     ("ring B mean kV", cl["V_eb_kV"]["mean"], REC_SUP["V_eb_kV"]["mean"], 1e-3),
                     ("cycles to 95 %", cl["cycles_to_95pc"], int(round(REC_SUP_T95 * CF.F)), 0.0)] if m != "ND-deck" else \
                [("ring A mean kV (samples)", cl["V_ea_mean_samples_kV"], REC_SUP["V_ea_kV"]["mean"], 1e-4),
                 ("ring B mean kV (samples)", cl["V_eb_mean_samples_kV"], REC_SUP["V_eb_kV"]["mean"], 1e-4),
                 ("cycles to 95 %", cl["cycles_to_95pc"], int(round(REC_SUP_T95 * CF.F)), 0.0),
                 ("P_belt_W", cl["P_belt_W"], REC_SUP["P_belt_W"], 1e-3)]
            if fr and fr.get("done"):
                pairs.append(("z (free, 10 V)", fr["z"], REC_FREE["z"], 2e-3 if m != "ND-deck" else 1e-5))
            rows_ = [dict(q=q, run=a, record=b, rel=(a - b) / b if b else None,
                          ok=(abs((a - b) / b) <= tol) if tol else (a == b)) for q, a, b, tol in pairs]
            g.append(dict(gate=f"G-ES {m}", ok=all(x["ok"] for x in rows_), rows=rows_,
                          record="sim/hub_rings_build_results.json record_supply / record_supply_free"))
        for m, rows in R.items():
            for name, r in rows.items():
                if name.startswith("clamped") and r.get("done") and "balance" in r:
                    b = r["balance"]
                    g.append(dict(gate=f"G-ENERGY electrostatic {m} {name}", ok=abs(b["residual_frac"]) < 5e-3,
                                  residual_W=b["residual_W"], residual_frac=b["residual_frac"], P_belt_W=r["P_belt_W"]))
        a, b = R.get("HV-typ", {}).get("clamped steps x2"), R.get("HV-typ", {}).get("clamped")
        if a and b and a.get("done") and b.get("done"):
            rows_ = [dict(q=q, steps20000=fa(a), steps10000=fa(b)) for q, fa in
                     (("ring A mean kV", lambda r: r["V_ea_kV"]["mean"]), ("ring B mean kV", lambda r: r["V_eb_kV"]["mean"]),
                      ("P_belt_W", lambda r: r["P_belt_W"]), ("P_clamps_W", lambda r: r["P_clamps_W"]),
                      ("P_stacks_W", lambda r: r["P_stacks_W"]), ("cycles to 95 %", lambda r: r["cycles_to_95pc"]))]
            for x in rows_:
                x["rel"] = (x["steps20000"] - x["steps10000"]) / x["steps10000"]
            g.append(dict(gate="G-STEP electrostatic HV-typ: steps 10000 -> 20000 a cycle",
                          ok=all(abs(x["rel"]) < 2e-3 for x in rows_), rows=rows_))
    return g


_vk = np.array(REC_SUP["Vk_per_cycle_kV"])        # the record's 95 % (29 cycles, 0.24 s), from its own per-cycle levels
_hit = np.nonzero(_vk <= 0.95 * _vk[-3:].mean())[0]
REC_SUP_T95 = (int(_hit[0]) + 1) / CF.F


# =================================================================================================== the figure
SURF, INK, INK2, GRID, AXIS = "#fcfcfb", "#0b0b0b", "#52514e", "#e1e0d9", "#c3c2b7"   # as sim/ah_null.py
SERIES = ("#2a78d6", "#eb6834", "#1baf7a", "#eda100")        # categorical slots 1-4, validated (light, adjacent)
BASE = "#8a8f99"                                             # the record's ND: a neutral reference


def figure(out, path):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    def style(ax, title, ylabel, xlabel):
        ax.set_facecolor(SURF)
        ax.set_title(title, fontsize=9.6, loc="left", color=INK)
        ax.set_ylabel(ylabel, fontsize=8.3, color=INK2)
        ax.set_xlabel(xlabel, fontsize=8.3, color=INK2)
        ax.grid(True, color=GRID, lw=0.6)
        ax.set_axisbelow(True)
        for s_ in ("top", "right"):
            ax.spines[s_].set_visible(False)
        for s_ in ("left", "bottom"):
            ax.spines[s_].set_color(AXIS)
        ax.tick_params(colors=INK2, labelsize=7.8)

    mg, es = out["magnetic"], out["electrostatic"]
    fig, axs = plt.subplots(2, 2, figsize=(13.0, 9.0), facecolor=SURF)
    fig.subplots_adjust(left=0.065, right=0.975, top=0.9, bottom=0.075, wspace=0.22, hspace=0.38)
    fig.suptitle("Real diodes in both pumps of record: the magnetic pump's start kick and start-up, the electrostatic "
                 "pump's start-up gain and the rings' rise (sim/diodes_real.py)", fontsize=11.0, color=INK, x=0.065,
                 ha="left")
    cols = {"ND": BASE, "GP": SERIES[0], "FR": SERIES[1], "SB": SERIES[2], "SBM": SERIES[3]}
    names = {"ND": "the record's ND", "GP": "1N54xx class", "FR": "fast recovery", "SB": "Schottky 200 V",
             "SBM": "Schottky 200 / 100 V"}

    # (a) the threshold kick per model, without / with the bypass
    ax = axs[0, 0]
    ms = [m for m in MAG_MODELS if m in mg["thresholds"]]
    x = np.arange(len(ms))
    wbar = 0.34
    for j, (key, lab, hatch) in enumerate((("none", "no bypass", None), ("22mF", "22 mF bypass (PROPOSED)", "////"))):
        vals = [100 * mg["thresholds"][m][key]["frac_starts"] for m in ms]
        bars = ax.bar(x + (j - 0.5) * (wbar + 0.03), vals, width=wbar, color=[cols[m] for m in ms], hatch=hatch,
                      edgecolor=SURF, linewidth=0.0, label=lab)
        for xi, v in zip(x + (j - 0.5) * (wbar + 0.03), vals):
            ax.text(xi, v + 0.6, f"{v:.1f}", ha="center", va="bottom", fontsize=7.2, color=INK)
    ax.axhline(100 * KICK_REC, color=INK2, lw=0.9, ls="--")
    ax.text(len(ms) - 0.5, 100 * KICK_REC + 0.6, f"the record's kick, {100 * KICK_REC:.0f} %", ha="right", va="bottom",
            fontsize=7.4, color=INK2)
    ax.set_xticks(x, [names[m] for m in ms], fontsize=7.8, color=INK2)
    style(ax, "(a) The smallest start kick (% of Ψs) by the record's criterion", "kick, % of Ψs", "")
    from matplotlib.patches import Patch
    ax.legend(handles=[Patch(facecolor=AXIS, label="no bypass"), Patch(facecolor=AXIS, hatch="////", edgecolor=SURF,
                                                                         label="22 mF bypass")],
              fontsize=7.2, frameon=False, labelcolor=INK, loc="upper left")

    # (b) the start-up from the record's 20 % kick, with the bypass: the branch peak per cycle
    ax = axs[0, 1]
    F = mg["F_Hz"]
    for m in ms:
        r = mg["kick"].get(m, {}).get("22mF")
        if not r or not r.get("done"):
            continue
        y = np.array(r["branch_AT_per_cycle"])
        tt = (np.arange(len(y)) + 1) / F
        ax.semilogy(tt, y, color=cols[m], lw=2.0 if m != "ND" else 1.6, ls="-" if m != "ND" else "--",
                    label=names[m] + ("" if r.get("starts") else ": does not start"))
    ax.axhline(START_AT, color=INK2, lw=0.8, ls=":")
    ax.text(0.01, START_AT * 1.07, f"the record's start criterion, {START_AT:.0f} A-turns", fontsize=7.2, color=INK2)
    style(ax, f"(b) Start-up from the record's {100 * KICK_REC:.0f} % kick, 22 mF bypass: the branch peak per cycle",
          "N_AH × peak branch current, A-turns", "time, s")
    ax.legend(fontsize=7.2, frameon=False, labelcolor=INK, loc="lower right")

    # (c) the electrostatic gain per cycle against the seed (free runs)
    ax = axs[1, 0]
    ecols = {"ND": BASE, "HV-typ": SERIES[0], "HV-max": SERIES[1], "HV-hot": SERIES[2], "HV-VF2": SERIES[3]}
    enames = {"ND": "the record's ND", "HV-typ": "sticks, typical leakage", "HV-max": "max leakage (25 °C)",
              "HV-hot": "hot leakage (100 °C)", "HV-VF2": "typical, V_F × 2"}
    for m in ecols:
        pts = []
        for name, r in es["runs"].get(m, {}).items():
            if name.startswith("free") and r.get("done"):
                pts.append((abs(r["job"].get("v0", ES_FREE["v0"])), r["z"]))
        for q in es["thresholds"].get(m, {}).get("trials", []):
            if q.get("z") is not None:
                pts.append((abs(q["v0_V"]), q["z"]))
        if not pts:
            continue
        pts = sorted(set(pts))
        ax.semilogx([p[0] for p in pts], [p[1] for p in pts], color=ecols[m], lw=2.0 if m != "ND" else 1.6,
                    ls="-" if m != "ND" else "--", marker="o", ms=4, mec=SURF, mew=1.0, label=enames[m])
    ax.axhline(1.0, color=INK2, lw=0.8, ls=":")
    for v, lab in ((abs(ES_FREE["v0"]), "the record's free-run seed"), (abs(V0_CLAMPED), "the clamped run's seed")):
        ax.axvline(v, color=AXIS, lw=0.8)
        ax.text(v * 1.05, 0.955, lab, fontsize=7.0, color=INK2, rotation=90, va="bottom")
    style(ax, "(c) The electrostatic pump's gain per cycle against its seed (free runs, 12 cycles)",
          "z per cycle (the record's fit)", "seed on nodes 1 and 4, |V|")
    ax.legend(fontsize=7.2, frameon=False, labelcolor=INK, loc="lower right")

    # (d) the rings' gap per cycle in the record's clamped run
    ax = axs[1, 1]
    for m in ("ND", "HV-typ", "HV-max", "HV-hot", "HV-VF2"):
        r = es["runs"].get(m, {}).get("clamped")
        if not r or not r.get("done"):
            continue
        y = -np.array(r["Vk_per_cycle_kV"])
        tt = (np.arange(len(y)) + 1) / CF.F
        ax.plot(tt, y, color=ecols[m], lw=2.0 if m != "ND" else 1.6, ls="-" if m != "ND" else "--", label=enames[m])
    ax.set_xlim(0, 1.0)
    style(ax, "(d) The rings' DC across the gap, from the clamped run's −1 kV seed", "V_B − V_A (least in the cycle), kV",
          "time, s")
    ax.legend(fontsize=7.2, frameon=False, labelcolor=INK, loc="lower right")
    fig.savefig(path, dpi=150, facecolor=SURF)
    plt.close(fig)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--procs", type=int, default=4)
    ap.add_argument("--only", choices=("mag", "es"), default=None)
    ap.add_argument("--figure-only", action="store_true", help="redraw the figure from the results file")
    a = ap.parse_args()
    if a.figure_only:
        out = json.load(open(OUT_JSON))
        figure(out, OUT_FIG)
        return
    t0 = time.time()
    old = json.load(open(OUT_JSON)) if (a.only and os.path.exists(OUT_JSON)) else None
    res = run_all(a.procs, a.only)
    out = summarise(res, old)
    out["run_s"] = time.time() - t0
    json.dump(out, open(OUT_JSON, "w"), indent=1, default=float)
    if "magnetic" in out and "electrostatic" in out:
        figure(out, OUT_FIG)
    for q in out["gates"]:
        print(q["gate"], "PASS" if q["ok"] else "FAIL", flush=True)
    print(f"done in {time.time() - t0:.0f} s")


if __name__ == "__main__":
    main()
