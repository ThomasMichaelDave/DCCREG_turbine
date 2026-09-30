#!/usr/bin/env python3
"""
sim/pump_engine.py — PUMP-CALC exact engine (brief pump-calc r0.1)
===================================================================
"Does the drawn pump pump, by how much, and where does the energy go?" — one exact engine for any
configuration of the drawn pump (doubler + islands + all eight gaps), tank collapsed.

PROVENANCE (reuse ledger, see sim/pump-calc-findings.md):
  * the event-driven KCL core (Net, closure algebra, lcp, event_loss, Ring, Sim, run_machine,
    doubler_net, s2_net, _shuttle_net/shuttle_parity) is DERIVED from sim/island_asdrawn.py @ 8cd181e
    (the r0.2 record, frozen) and held to it by gate E0 (sim/pump_engine_gates.py);
  * the M-RD / M-SR gap rules are ported from sim/island_gapbracket.py @ 8cd181e (derive_event,
    ChainEngine, resolve_chain) into the event engine; the ngspice parts are dropped;
  * the closed-cycle eigenvalue follows xsim_queiroz_matrix._cycle_map/_dominant (XSIM-MATCH-B).
  Changes vs r0.2 (each gated):
    - numpy only: scipy.linalg.expm -> expm() below, Pade(13) scaling-and-squaring (gate E1)  [ME]
    - arming: 'robust' phase-exact station test (default) or 'r02' (the r0.2 float semantics,
      th = 60k+p, a <= th % 60 < b — cycle-dependent at the 1e-14 level; E0 runs in 'r02')   [ME]
    - caches (K per phase, cluster/flow matrices per edge set) and a vectorised ring loop: same
      algebra, same decisions (E0 <= 1e-9)                                                     [ME]
    - gap models per class (rail / load / fire / backstop): valve (M-OW), arc, ring-down (M-RD),
      symmetric recovering (M-SR); TRV probe; per-event records                               [IR]
    - z by Floquet/monodromy: the cycle's composed linear map, spectral radius (gate P0)       [ME]

Tiers [OC] derivable/standard · [IR] design choice / interpretive · [RH] heuristic · [ME] method.
Pure EE firewall. No git / subprocess / file writes on the import path (browser-safe, Pyodide).
Read-only consumer of: shuttle_core (profiles/Params/caps_phase/TH_*/N_COLLAPSE/set_device_caps),
doubler_core.solve_doubler4, island_resonant_core.integrate, spice/timing.sub (DXF stations),
topology_edge_list.csv (the netlist of record).
"""
import csv
import itertools
import json
import math
import os
import re
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
SPICE = os.path.join(ROOT, "spice")
for _p in (HERE, ROOT, os.path.join(ROOT, "reference")):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import shuttle_core as sc                      # frozen
import doubler_core as dc                      # frozen
import island_resonant_core as irc             # frozen

GND = -1
ENGINE_VERSION = "pump_engine r0.1 (derived from island_asdrawn @ 8cd181e)"


# ======================================================================================
# 0. expm — Pade(13) scaling-and-squaring (Higham 2005), numpy only                   [ME]
# ======================================================================================
_PADE = {3: (120., 60., 12., 1.),
         5: (30240., 15120., 3360., 420., 30., 1.),
         7: (17297280., 8648640., 1995840., 277200., 25200., 1512., 56., 1.),
         9: (17643225600., 8821612800., 2075673600., 302702400., 30270240., 2162160., 110880.,
             3960., 90., 1.)}
_B13 = (64764752532480000., 32382376266240000., 7771770303897600., 1187353796428800.,
        129060195264000., 10559470521600., 670442572800., 33522128640., 1323241920.,
        40840800., 960960., 16380., 182., 1.)
_THETA = {3: 1.495585217958292e-2, 5: 2.539398330063230e-1, 7: 9.504178996162932e-1,
          9: 2.097847961257068e0, 13: 5.371920351148152e0}


def _balance(A, sweeps=40):
    """Power-of-two diagonal similarity B = D^-1 A D equalising off-diagonal row/column norms
    (Parlett-Reinsch; LAPACK gebal without permutation). Exact in floating point (exponent shifts
    only). The ring matrices mix cluster charges (~1e-9 C) and currents (~1 A); unbalanced, the
    Pade approximant loses 2e-8 relative on the S2 ring. Returns (B, d), A = diag(d) B diag(d)^-1.
    Scaling A by h leaves the balance unchanged, so a Ring balances once. [ME]"""
    B = np.array(A, dtype=float); n = B.shape[0]; d = np.ones(n)
    for _ in range(sweeps):
        done = True
        for i in range(n):
            c = float(np.abs(B[:, i]).sum() - abs(B[i, i]))
            r = float(np.abs(B[i, :]).sum() - abs(B[i, i]))
            if c == 0.0 or r == 0.0:
                continue
            g = r / 2.0; f = 1.0; s0 = c + r
            while c < g:
                f *= 2.0; c *= 4.0
            g = r * 2.0
            while c > g:
                f /= 2.0; c /= 4.0
            if (c + r) / f < 0.95 * s0:
                done = False
                B[i, :] /= f; B[:, i] *= f; d[i] *= f
        if done:
            break
    return B, d


def expm_bal(B, d, h=1.0):
    """expm(A h) for A = diag(d) B diag(d)^-1 (a balanced pair from _balance)."""
    E = _expm_pade(B * h)
    return E * d[:, None] / d[None, :]


def expm(A):
    """Matrix exponential, Pade approximant with scaling and squaring (Higham 2005, the
    algorithm scipy.linalg.expm refined), on the balanced matrix. Gate E1 holds it to scipy at
    <= 1e-12 relative."""
    A = np.asarray(A, dtype=float)
    n = A.shape[0]
    if n == 0:
        return np.zeros((0, 0))
    if n > 1:
        B, d = _balance(A)
        return expm_bal(B, d)
    return _expm_pade(A)


def _expm_pade(A):
    n = A.shape[0]
    ident = np.eye(n)
    nrm = float(np.max(np.sum(np.abs(A), axis=0)))
    if nrm == 0.0:
        return ident
    for m in (3, 5, 7, 9):
        if nrm <= _THETA[m]:
            b = _PADE[m]
            A2 = A @ A
            pw = [ident, A2]
            while len(pw) < (m + 1) // 2:
                pw.append(pw[-1] @ A2)
            U = A @ sum(b[2 * j + 1] * pw[j] for j in range(len(pw)))
            V = sum(b[2 * j] * pw[j] for j in range(len(pw)))
            return np.linalg.solve(V - U, V + U)
    s = max(0, int(math.ceil(math.log2(nrm / _THETA[13]))))
    A = A / (2.0 ** s)
    b = _B13
    A2 = A @ A; A4 = A2 @ A2; A6 = A4 @ A2
    U = A @ (A6 @ (b[13] * A6 + b[11] * A4 + b[9] * A2) + b[7] * A6 + b[5] * A4 + b[3] * A2
             + b[1] * ident)
    V = A6 @ (b[12] * A6 + b[10] * A4 + b[8] * A2) + b[6] * A6 + b[4] * A4 + b[2] * A2 + b[0] * ident
    R = np.linalg.solve(V - U, V + U)
    for _ in range(s):
        R = R @ R
    return R


# ======================================================================================
# 1. INPUTS OF RECORD — netlist, DXF stations, defaults
# ======================================================================================
def _read(path):
    with open(path) as f:
        return f.read()


def parse_dxf():
    """DXF station angles (deg, 60-deg sector) from the spice/timing.sub comment line (as r0.2)."""
    txt = _read(os.path.join(SPICE, "timing.sub"))
    tok = re.search(r"DXF stations \(deg, 60deg sector\):\s*(.*)", txt).group(1).split()
    return {tok[i]: float(tok[i + 1]) for i in range(0, len(tok), 2)}


def edge_list():
    out = []
    with open(os.path.join(ROOT, "topology_edge_list.csv")) as f:
        for r in csv.reader(f):
            if r and not r[0].startswith("#") and r[0] != "component":
                out.append((r[0], r[1], r[2]))
    return out


DXF = parse_dxf()
EDGES = edge_list()
MOTOR_PARTS = tuple([f"L_A{i}" for i in range(1, 7)] + [f"C_AR{i}" for i in (1, 2, 3, 5, 6)] +
                    ["C__AR4"] + [f"C_BR{i}" for i in range(1, 7)] + [f"L_B{i}" for i in range(1, 7)])
TANK_PARTS = ("L_R1", "C_R1", "L_R2")
GAP_CLASS = {"SG1": "rail", "SG2": "rail", "SG3a1": "load", "SG4a1": "load",
             "SG3b1": "fire", "SG4b1": "fire", "BS3": "backstop", "BS4": "backstop"}
GAP_NAMES = ("SG1", "SG3a1", "SG3b1", "BS3", "SG2", "SG4a1", "SG4b1", "BS4")
CLASSES = ("rail", "load", "fire", "backstop")
MODELS = ("valve", "arc", "ringdown", "recover")        # M-OW, sustained arc, M-RD, M-SR
MODEL_KIND = {"valve": "rect", "arc": "arc", "ringdown": "rd", "recover": "sr"}
CANARY = dict(C1MIN=16.0, C1MAX=280.0, C2MIN=16.0, C2MAX=280.0, CA=309.0, CB=309.0, CPAR=20.0)

# gap-model constants (sim/island-gapbracket-findings.md semantics)                      [IR]
H_TO_ZERO = 1e-4           # I_hold -> 0 realised as 1e-4 of i_pk1 (as Pass A')
T_SPIKE = 50e-9            # i_pk1 excludes the first 50 ns after an ignition (Pass A')
HOLDOFF = 10e-6            # M-SR holdoff (Pass A')
T_RING_MAX = 50e-6         # a lit arc still ringing after 50 us of frozen-C ring is taken to its
                           # ring-down limit (exact relaxation; gate E2's theorem)       [IR]
T_TRV = 3e-6               # open-circuit TRV probe window after a gap's current zero    [ME]
BS_FRAC = 0.6
BISECT_IT = 44             # switching instants to 2^-44 of the step (r0.2: to machine precision) [ME]
DEBUG_RING = False

DEFAULTS = dict(
    topology="drawn",            # 'drawn' | 'core' (bare 4-node doubler, solve_doubler4 topology)
    C1min=16.0, C1max=280.0, C2min=16.0, C2max=280.0,   # pF (canary = design_synth.ESTABLISHED)
    Ca=309.0, Cb=309.0, Cpar=20.0,                       # pF
    profile="shuttle",           # 'shuttle' (shuttle_core.profiles raised cosine) | 'tanh' (Pass A)
    tanh_k=12.0,
    cx_max=471.0, cx_min=8.0,    # pF (live default / island_charging_cosim.CX_MIN)
    pCboss=6.0, pCboss2=0.0,     # pF (shuttle Params; pCboss2 = design_synth C_min basis)
    gap_stray=2.0,               # pF across each gap's own terminals
    island_stray=5.0,            # pF 7/8/n17/n23 -> reference
    Lx_mH=1.0, R_lx=2.0,         # series island inductor + ESR (r0.2 lock / integrator point)
    motor=False, motor_topology="per_coil",   # 'per_coil' (as drawn, 43) | 'per_branch' [IR, 33]
    L_motor=0.64, C_motor_nF=440.0, R_motor=40.0,
    gm_rail="valve", gm_load="valve", gm_fire="valve", gm_backstop="valve",
    latch_rail=False, latch_load=False, latch_fire=True, latch_backstop=True,
    ih_rail=0.0, ih_load=0.0, ih_fire=0.0, ih_backstop=0.0,        # I_hold / i_pk1
    trec_rail=0.0, trec_load=0.0, trec_fire=0.0, trec_backstop=0.0,  # us
    holdoff_us=10.0,
    st_SG1=DXF["SG1"], st_SG3a=DXF["SG3a"], st_SG3b=DXF["SG3b"], st_BS3=DXF["BS3"],
    st_SG2=DXF["SG2"], st_SG4a=DXF["SG4a"], st_SG4b=DXF["SG4b"], st_BS4=DXF["BS4"],
    win_end=30.0,                # rails / fire / backstop armed to the end of their half (r0.2)
    simultaneous=False,          # all gaps always armed (the solve_doubler4 machine)
    galvanic=False,              # G0: islands replaced by ideal station valves
    arming="robust",             # 'robust' | 'r02'
    rpm=3000.0, dth=0.05,        # deg grid
    V_strike_kV=20.0,            # D-SCALE anchor [IR]
    use_geom=False, r_inMm=95.0, r_outMm=387.0, g_vMm=7.0, n_kept=6, N_sec=12,
    d_ballMm=12.0, r_gapMm=387.0, g_latMm=1.0,
)
_NUMERIC = [k for k, v in DEFAULTS.items() if isinstance(v, float) or (isinstance(v, int)
                                                                       and not isinstance(v, bool))]


def make_config(user=None):
    cfg = dict(DEFAULTS)
    for k, v in (user or {}).items():
        if k not in DEFAULTS:
            raise KeyError(f"unknown config key {k!r}")
        d = DEFAULTS[k]
        if isinstance(d, bool):
            v = bool(v) if not isinstance(v, str) else v.lower() in ("1", "true", "yes", "on")
        elif isinstance(d, (int, float)):
            v = float(v)
        cfg[k] = v
    for c in CLASSES:
        if cfg["gm_" + c] not in MODELS:
            raise ValueError(f"gm_{c}: {cfg['gm_' + c]!r} not in {MODELS}")
    if cfg["use_geom"]:
        import design_synth as ds
        cmax = ds.Cmax_from_geom(cfg["r_inMm"], cfg["r_outMm"], cfg["g_vMm"], int(cfg["n_kept"]),
                                 int(cfg["N_sec"]))
        cfg["C1max"] = cfg["C2max"] = float(cmax)
    return cfg


def stations(cfg, compat=False):
    s = dict(SG1=cfg["st_SG1"], SG3a=cfg["st_SG3a"], SG3b=cfg["st_SG3b"], BS3=cfg["st_BS3"],
             SG2=cfg["st_SG2"], SG4a=cfg["st_SG4a"], SG4b=cfg["st_SG4b"], BS4=cfg["st_BS4"])
    if compat:                               # r0.2: SG1/SG3a from shuttle TH_RET/TH_LOAD (floats)
        if abs(s["SG1"] - sc.TH_RET * 60.0) < 1e-9:
            s["SG1"] = sc.TH_RET * 60.0
        if abs(s["SG3a"] - sc.TH_LOAD * 60.0) < 1e-9:
            s["SG3a"] = sc.TH_LOAD * 60.0
    return s


def windows(cfg, compat=False):
    """Arming windows [IR lock, r0.2]: arm AT the station; rails, fire and backstop to the end of
    their half (win_end); the load gap disarms at its fire station."""
    if cfg["simultaneous"]:
        return {g: (0.0, 60.0) for g in GAP_NAMES}
    s = stations(cfg, compat); W = cfg["win_end"]
    return {"SG1": (s["SG1"], W), "SG3a1": (s["SG3a"], s["SG3b"]),
            "SG3b1": (s["SG3b"], W), "BS3": (s["BS3"], W),
            "SG2": (s["SG2"], W + 30.0), "SG4a1": (s["SG4a"], s["SG4b"]),
            "SG4b1": (s["SG4b"], W + 30.0), "BS4": (s["BS4"], W + 30.0)}


# ======================================================================================
# 2. NETWORK
# ======================================================================================
class Net:
    """nodes (reference excluded); caps (name, i, j, C | callable(theta_deg)); inds (name, i, j, L,
    R, kind 'lx'|'motor'); gaps (name, i, j, kind, window, family, params). Kinds: 'rect' (ideal
    one-way, anode i), 'rect_latch', 'arc', 'rd', 'sr', 'short' (parity)."""

    def __init__(self):
        self.nodes, self.idx = [], {}
        self.caps, self.inds, self.gaps = [], [], []
        self.meta = {}
        self.prof = None                     # callable(theta) -> dict of varicap values (F)

    def n(self, name):
        if name in ("0", "R-A", "R-B", "ref"):
            return GND
        if name not in self.idx:
            self.idx[name] = len(self.nodes); self.nodes.append(name)
        return self.idx[name]

    def K(self, th):
        N = len(self.nodes); K = np.zeros((N, N))
        pv = self.prof(th) if self.prof is not None else None
        for nm, i, j, C in self.caps:
            if isinstance(C, str):
                c = pv[C]
            else:
                c = C(th) if callable(C) else C
            if i >= 0: K[i, i] += c
            if j >= 0: K[j, j] += c
            if i >= 0 and j >= 0:
                K[i, j] -= c; K[j, i] -= c
        return K

    def cap_values(self, th):
        pv = self.prof(th) if self.prof is not None else None
        return [(nm, i, j, (pv[C] if isinstance(C, str) else (C(th) if callable(C) else C)))
                for nm, i, j, C in self.caps]


def shuttle_P(cfg):
    P = sc.Params(); P.cx_max = cfg["cx_max"]; P.cx_min = cfg["cx_min"]
    P.pCboss = cfg["pCboss"]; P.pCboss2 = cfg["pCboss2"]; P.gap_stray = cfg["gap_stray"]
    return P


def make_profile(cfg):
    """C1, C2, Cx3, Cx4 (F) vs theta (deg). 'shuttle': the FROZEN shuttle_core.profiles with the
    device scalars bound through its public hook for the call; 'tanh': the Pass A arbiter schedule
    C = Cmin + (Cmax-Cmin)/2 (1 + tanh(k sin(2 pi theta/60 + phase))) with Cx from shuttle_core."""
    P = shuttle_P(cfg)
    caps = dict(C1MIN=cfg["C1min"], C1MAX=cfg["C1max"], C2MIN=cfg["C2min"], C2MAX=cfg["C2max"])
    kind = cfg["profile"]; k = cfg["tanh_k"]

    def prof(th):
        sc.set_device_caps(**caps)
        try:
            c1, c2, cx3, cx4 = sc.profiles((th / 60.0) % 1.0, P)
        finally:
            sc.reset_device_caps()
        if kind == "tanh":
            w = 2.0 * math.pi * th / 60.0
            c1 = cfg["C1min"] + (cfg["C1max"] - cfg["C1min"]) * 0.5 * (1 + math.tanh(k * math.sin(w)))
            c2 = cfg["C2min"] + (cfg["C2max"] - cfg["C2min"]) * 0.5 * (1 + math.tanh(k * math.sin(w + math.pi)))
        return dict(C1=1e-12 * c1, C2=1e-12 * c2, Cx3=1e-12 * cx3, Cx4=1e-12 * cx4)
    return prof


def build_net(cfg, lx=None, galvanic=None):
    """The drawn netlist, node-exact from topology_edge_list.csv; tank collapsed (R-A = R-B = ref).
    lx (H) overrides Lx (0 = the G twin, Lx shorted); galvanic (G0): islands replaced by ideal
    rectifiers 1->3 and 4->2 armed over the load+fire span of each half [IR, r0.2]."""
    if cfg["topology"] == "core":
        return core_net(cfg)
    lx = cfg["Lx_mH"] * 1e-3 if lx is None else lx
    galvanic = cfg["galvanic"] if galvanic is None else galvanic
    compat = cfg["arming"] == "r02"
    W = windows(cfg, compat)
    net = Net(); net.prof = make_profile(cfg)
    boss = (cfg["pCboss"] + cfg["pCboss2"]) * 1e-12
    gstray = cfg["gap_stray"] * 1e-12
    for n in ("1", "2", "3", "4"):
        net.n(n)
    per_branch = cfg["motor"] and cfg["motor_topology"] == "per_branch"
    for comp, a, b in EDGES:
        if comp in TANK_PARTS or (comp in MOTOR_PARTS and not cfg["motor"]):
            continue
        if galvanic and comp in ("Cx3", "Cx4", "Lx3", "Lx4", "SG3a1", "SG3b1", "BS3", "SG4a1",
                                 "SG4b1", "BS4"):
            continue
        if per_branch and (comp.startswith("C_AR") or comp.startswith("C__AR") or comp.startswith("C_BR")):
            continue
        if per_branch and (comp.startswith("L_A") or comp.startswith("L_B")):
            # one DC-block cap per 6-coil branch [IR, the decided but undrawn 33-part variant]:
            # the coils land on a common branch node, the block cap (6 x C_motor) closes to the bank
            a, b = (a, "mA") if comp.startswith("L_A") else ("mB", b)
        i, j = net.n(a), net.n(b)
        if comp == "C1":
            net.caps.append(("C1", j, i, "C1"))              # C1: R-A -> 1
        elif comp == "C2":
            net.caps.append(("C2", j, i, "C2"))
        elif comp == "Ca1":
            net.caps.append((comp, i, j, cfg["Ca"] * 1e-12))
        elif comp == "Cb1":
            net.caps.append((comp, i, j, cfg["Cb"] * 1e-12))
        elif comp == "Cx3":
            net.caps.append((comp, i, j, "Cx3")); net.caps.append((comp + "_boss", i, j, boss))
        elif comp == "Cx4":
            net.caps.append((comp, i, j, "Cx4")); net.caps.append((comp + "_boss", i, j, boss))
        elif comp in ("Lx3", "Lx4"):
            net.inds.append((comp, i, j, lx, cfg["R_lx"], "lx"))
        elif comp.startswith("L_A") or comp.startswith("L_B"):
            net.inds.append((comp, i, j, cfg["L_motor"], cfg["R_motor"], "motor"))
        elif comp.startswith("C_AR") or comp.startswith("C__AR") or comp.startswith("C_BR"):
            net.caps.append((comp, i, j, cfg["C_motor_nF"] * 1e-9))
        elif comp in GAP_CLASS:
            fam = GAP_CLASS[comp]
            net.gaps.append(gap_tuple(cfg, comp, i, j, W[comp], fam))
            net.caps.append((comp + "_stray", i, j, gstray))
        else:
            raise ValueError(comp)
    if per_branch:
        net.caps.append(("C_Ablock", net.n("mA"), net.n("2"), 6 * cfg["C_motor_nF"] * 1e-9))
        net.caps.append(("C_Bblock", net.n("3"), net.n("mB"), 6 * cfg["C_motor_nF"] * 1e-9))
    if galvanic:
        s = stations(cfg, compat); We = cfg["win_end"]
        wd = ((0.0, 60.0), (0.0, 60.0)) if cfg["simultaneous"] else ((s["SG3a"], We), (s["SG4a"], We + 30.0))
        for (nm, a, b), w in zip((("D3", "1", "3"), ("D4", "4", "2")), wd):
            i, j = net.n(a), net.n(b)
            net.gaps.append((nm, i, j, "rect", w, "load", {}))
            net.caps.append((nm + "_stray", i, j, gstray))
    for n in ("1", "2", "3", "4"):
        net.caps.append((f"Cpar{n}", net.n(n), GND, cfg["Cpar"] * 1e-12))
    if cfg["island_stray"] > 0 and not galvanic:
        for n in ("7", "8", "n17", "n23"):
            net.caps.append((f"Cs_{n}", net.n(n), GND, cfg["island_stray"] * 1e-12))
    net.meta = dict(lx=lx, galvanic=galvanic, motor=cfg["motor"], topology="drawn")
    return net


def gap_tuple(cfg, name, i, j, window, fam):
    model = cfg["gm_" + fam]
    kind = MODEL_KIND[model]
    if kind == "rect" and cfg["latch_" + fam]:
        kind = "rect_latch"
    params = dict(model=model, I_hold=cfg["ih_" + fam], t_rec=cfg["trec_" + fam] * 1e-6,
                  holdoff=cfg["holdoff_us"] * 1e-6)
    return (name, i, j, kind, window, fam, params)


def core_net(cfg):
    """H3/K1/K2: the 4-node doubler with ideal rectifiers D1 2->ref, D2 3->ref, D3 1->3, D4 4->2 and
    solve_doubler4's two-phase caps (A = C1max/C2min on [0,30)); station-armed unless simultaneous
    [r0.2 doubler_net]."""
    net = Net()
    n1, n2, n3, n4 = (net.n(x) for x in "1234")
    A = lambda th: (th % 60.0) < 30.0
    c1lo, c1hi, c2lo, c2hi = cfg["C1min"], cfg["C1max"], cfg["C2min"], cfg["C2max"]
    net.caps += [("C1", n1, GND, lambda th: 1e-12 * (c1hi if A(th) else c1lo)),
                 ("C2", n4, GND, lambda th: 1e-12 * (c2lo if A(th) else c2hi)),
                 ("Ca1", n1, n2, cfg["Ca"] * 1e-12), ("Cb1", n3, n4, cfg["Cb"] * 1e-12)]
    for n in (n1, n2, n3, n4):
        net.caps.append((f"Cpar{n}", n, GND, cfg["Cpar"] * 1e-12))
    s = stations(cfg, cfg["arming"] == "r02")
    al = (0.0, 60.0)
    w = dict(D1=(s["SG1"], 30.0), D3=(s["SG3a"], 30.0), D2=(s["SG2"], 60.0), D4=(s["SG4a"], 60.0))
    for nm, a, b in (("D1", n2, GND), ("D2", n3, GND), ("D3", n1, n3), ("D4", n4, n2)):
        net.gaps.append((nm, a, b, "rect", al if cfg["simultaneous"] else w[nm], "load", {}))
    net.meta = dict(lx=0.0, galvanic=True, motor=False, topology="core")
    return net


# ======================================================================================
# 3. CLOSURE ALGEBRA — clusters, constrained solve, forward charge per closure, event loss
# ======================================================================================
def _clusters(N, edges):
    par = list(range(N + 1))                    # index N = reference

    def f(x):
        while par[x] != x:
            par[x] = par[par[x]]; x = par[x]
        return x
    for a, b in edges:
        ra, rb = f(N if a < 0 else a), f(N if b < 0 else b)
        if ra != rb:
            par[ra] = rb
    g = f(N); cid = -np.ones(N, dtype=int); nc = 0; m = {}
    for n in range(N):
        r = f(n)
        if r == g:
            continue
        if r not in m:
            m[r] = nc; nc += 1
        cid[n] = m[r]
    return cid, nc


def _P(cid, nc):
    P = np.zeros((len(cid), nc))
    for n, c in enumerate(cid):
        if c >= 0:
            P[n, c] = 1.0
    return P


def _flow_matrix(N, edges):
    """Row e: the node set whose net charge change crosses closure edge e (a -> b), as r0.2's
    edge_flows (spanning forest; redundant edges carry 0): lam = F @ dq_net."""
    adj = {k: [] for k in range(-1, N)}
    tree = []
    par = list(range(N + 1))

    def f(x):
        while par[x] != x:
            par[x] = par[par[x]]; x = par[x]
        return x
    for e, (a, b) in enumerate(edges):
        A, B = (N if a < 0 else a), (N if b < 0 else b)
        if f(A) != f(B):
            par[f(A)] = f(B); tree.append(e)
            adj[a].append((b, e)); adj[b].append((a, e))
    F = np.zeros((len(edges), N))
    for e in tree:
        a, b = edges[e]
        seen = {b}; st = [b]; hasg = (b == GND)
        while st:
            x = st.pop()
            for y, ee in adj[x]:
                if ee == e or y in seen:
                    continue
                seen.add(y); st.append(y); hasg |= (y == GND)
        if not hasg:
            for n in seen:
                if n >= 0:
                    F[e, n] = 1.0
        else:
            seen_a = {a}; st = [a]
            while st:
                x = st.pop()
                for y, ee in adj[x]:
                    if ee == e or y in seen_a:
                        continue
                    seen_a.add(y); st.append(y)
            for n in seen_a:
                if n >= 0:
                    F[e, n] = -1.0
    return F


class Alg:
    """Per-network caches of the closure algebra (cluster maps, flow matrices, solve matrices)."""

    def __init__(self, N):
        self.N = N
        self._cl, self._fl, self._sv = {}, {}, {}
        self._bal = {}
        self._sv_key = None

    def clusters(self, edges):
        key = tuple(edges)
        r = self._cl.get(key)
        if r is None:
            cid, nc = _clusters(self.N, edges)
            r = (cid, nc, _P(cid, nc)); self._cl[key] = r
        return r

    def flows(self, edges):
        key = tuple(edges)
        F = self._fl.get(key)
        if F is None:
            F = _flow_matrix(self.N, edges); self._fl[key] = F
        return F

    def solver(self, kkey, K, edges):
        """(Vmat, Mq): V = Vmat @ q and new node cap-charges q' = Mq @ q with `edges` shorted at K.
        Cached per (K key, edge set); the K-key cache is flushed when the key changes."""
        if kkey != self._sv_key:
            self._sv = {}; self._sv_key = kkey
        key = tuple(edges)
        r = self._sv.get(key)
        if r is None:
            cid, nc, P = self.clusters(edges)
            if nc == 0:
                Vmat = np.zeros((self.N, self.N))
            else:
                Kc = P.T @ K @ P
                Vmat = P @ np.linalg.solve(Kc, P.T)
            r = (Vmat, K @ Vmat); self._sv[key] = r
        return r


def event_loss(alg, K, q_pre, base_edges, new_edges, kkey=None):
    """1/2 v^T M^-1 v: energy lost shorting `new_edges` from the pre state of the network with
    `base_edges` closed; M = port elastance (B^T Kc^-1 B). Independent of the post state. [OC]"""
    if not new_edges:
        return 0.0
    cid, nc, P = alg.clusters(base_edges)
    if nc == 0:
        return 0.0
    Vmat, _ = alg.solver(kkey, K, base_edges) if kkey is not None else (None, None)
    Kc = P.T @ K @ P; Ki = np.linalg.inv(Kc)
    V = P @ (Ki @ (P.T @ q_pre)) if Vmat is None else Vmat @ q_pre
    v = np.array([(V[a] if a >= 0 else 0.0) - (V[b] if b >= 0 else 0.0) for a, b in new_edges])
    B = np.zeros((nc, len(new_edges)))
    for k, (a, b) in enumerate(new_edges):
        if a >= 0 and cid[a] >= 0: B[cid[a], k] += 1.0
        if b >= 0 and cid[b] >= 0: B[cid[b], k] -= 1.0
    M = B.T @ Ki @ B
    return float(0.5 * v @ np.linalg.lstsq(M, v, rcond=None)[0])


def lcp(alg, kkey, K, q, fixed, cands, prev=None, vth=None, tol=1e-9):
    """Ideal-rectifier complementarity (r0.2): choose S within cands (edges a->b) so that, with
    fixed+S closed, every d in S carries forward charge >= 0 and every d not in S has
    V_a - V_b <= vth_d. Returns (S, V, qnew, lam_S, nvalid, Mq)."""
    N = len(q)
    vth = [0.0] * len(cands) if vth is None else vth
    scaleq = max(1e-300, float(np.max(np.abs(q)))) if N else 1e-300
    nf = len(fixed)

    def test(S):
        edges = list(fixed) + [cands[k] for k in S]
        Vmat, Mq = alg.solver(kkey, K, edges)
        V = Vmat @ q; qn = Mq @ q
        lam = alg.flows(edges)[nf:] @ (qn - q)
        scalev = max(1e-300, float(np.max(np.abs(V))) if N else 1.0)
        for k, l in zip(S, lam):
            if l < -tol * scaleq:
                return None
        for k in range(len(cands)):
            if k in S:
                continue
            a, b = cands[k]
            va = V[a] if a >= 0 else 0.0; vb = V[b] if b >= 0 else 0.0
            if va - vb > vth[k] + tol * scalev:
                return None
        return V, qn, lam, Mq
    if prev is not None:
        r = test(list(prev))
        if r is not None:
            return list(prev), r[0], r[1], r[2], 1, r[3]
    found = []
    for m in range(len(cands) + 1):
        for S in itertools.combinations(range(len(cands)), m):
            r = test(list(S))
            if r is not None:
                found.append((list(S), r))
    if not found:
        raise RuntimeError("LCP: no consistent rectifier state")
    S, r = max(found, key=lambda x: abs(x[1][0][0]) + abs(x[1][0][3]) if N > 3 else 0)
    return S, r[0], r[1], r[2], len(found), r[3]


# ======================================================================================
# 4. RING ENGINE — exact LTI integration at frozen capacitances
# ======================================================================================
GL_X, GL_W = np.polynomial.legendre.leggauss(6)


class Ring:
    """Linear dynamics of the capacitive network with dynamic inductors `dyn` and closure edges
    `edges` (shorts) at frozen K. Reduced state z = [qc (cluster charges); I (dyn currents)]."""

    def __init__(self, net, alg, K, edges, dyn, cache=True):
        self.net, self.K, self.edges, self.dyn = net, K, list(edges), list(dyn)
        N = len(net.nodes); m = len(dyn)
        cid, nc, P = alg.clusters(self.edges)
        self.P = P; self.cid = cid
        self.Kc = P.T @ K @ P if nc else np.zeros((0, 0))
        self.Kci = np.linalg.inv(self.Kc) if nc else np.zeros((0, 0))
        G = np.zeros((nc, m)); Gn = np.zeros((N, m))
        for k, di in enumerate(dyn):
            nm, a, b, L, R, kind = net.inds[di]
            if a >= 0:
                Gn[a, k] -= 1.0
                if cid[a] >= 0: G[cid[a], k] -= 1.0
            if b >= 0:
                Gn[b, k] += 1.0
                if cid[b] >= 0: G[cid[b], k] += 1.0
        self.G, self.Gn = G, Gn
        Ld = np.array([net.inds[d][3] for d in dyn]); Rd = np.array([net.inds[d][4] for d in dyn])
        self.Ld, self.Rd = Ld, Rd
        A = np.zeros((nc + m, nc + m))
        A[:nc, nc:] = G
        A[nc:, :nc] = -(G.T @ self.Kci) / Ld[:, None]
        A[nc:, nc:] = -np.diag(Rd / Ld)
        self.A = A; self.nc = nc; self.m = m
        bkey = (tuple(self.edges), tuple(self.dyn))
        dc_ = alg._bal.get(bkey) if cache else None
        if A.shape[0] <= 1:
            self._B, self._d = A, np.ones(A.shape[0])
        elif dc_ is not None and dc_.shape[0] == A.shape[0]:
            # the cached exact power-of-two similarity of this topology (any such D is exact),
            # reused unchanged so the arithmetic never depends on evaluation history
            self._B, self._d = A * dc_[None, :] / dc_[:, None], dc_
        else:
            self._B, self._d = _balance(A)
            if cache:
                alg._bal[bkey] = self._d
        self.PKci = P @ self.Kci if nc else np.zeros((N, 0))
        self.KPKci = K @ self.PKci
        # instantaneous edge rates (K dV/dt - injection) are linear in I: rates = Tr @ I  [OC]
        F = alg.flows(self.edges)
        dVdI = self.PKci @ G if nc else np.zeros((N, m))
        self.Tr = F @ (K @ dVdI - Gn)

    def z_of(self, q, I):
        return np.concatenate([self.P.T @ q, I])

    def V_of(self, z):
        return self.PKci @ z[:self.nc] if self.nc else np.zeros(len(self.cid))

    def E(self, h):
        return expm_bal(self._B, self._d, h) if self.A.shape[0] > 1 else expm(self.A * h)

    def step(self, z, h):
        return self.E(h) @ z

    def eigdec(self):
        """(lam, Vd, Vdi) of A when the eigen-decomposition reconstructs A to 1e-12, else None."""
        if not hasattr(self, "_eig"):
            self._eig = None
            if self.A.size:
                try:
                    lam_, Vd = np.linalg.eig(self.A); Vdi = np.linalg.inv(Vd)
                    err = np.max(np.abs((Vd * lam_[None, :]) @ Vdi - self.A)) / max(1e-300, np.max(np.abs(self.A)))
                    if err < 1e-12:
                        self._eig = (lam_, Vd, Vdi)
                except np.linalg.LinAlgError:
                    pass
        return self._eig

    def gl_mats(self, h):
        """expm(A t_i) at the 6 Gauss-Legendre nodes of [0, h] (for int I^2, int I): from the
        eigen-decomposition when well conditioned (quadrature only; the state always advances by
        the Pade expm), else expm. [ME]"""
        ed = self.eigdec()
        if ed is None:
            return [self.E(0.5 * h * (x + 1)) for x in GL_X]
        lam_, Vd, Vdi = ed
        return [np.real((Vd * np.exp(lam_ * (0.5 * h * (x + 1)))[None, :]) @ Vdi) for x in GL_X]

    def integrals(self, z0, h, mats=None):
        mats = self.gl_mats(h) if mats is None else mats
        i2 = np.zeros(self.m); i1 = np.zeros(self.m)
        for Mx, w in zip(mats, GL_W):
            I = (Mx @ z0)[self.nc:]
            i2 += 0.5 * h * w * I * I; i1 += 0.5 * h * w * I
        return i2, i1

    def exact_integrals(self, z0, h):
        """int_0^h I_k^2 and int_0^h I_k EXACTLY (Van Loan block exponentials): the Gram matrix
        X = int e^{As} z0 z0^T e^{A^T s} ds = F22^T F12 of expm([[-A, z0 z0^T], [0, A^T]] h), and
        int e^{As} ds from expm([[A, I], [0, 0]] h). Used where a step spans a large part of a live
        oscillation (continuous-mode motor steps). [OC/ME]"""
        n = self.A.shape[0]
        Mx = np.zeros((2 * n, 2 * n))
        Mx[:n, :n] = -self.A; Mx[:n, n:] = np.outer(z0, z0); Mx[n:, n:] = self.A.T
        F = expm(Mx * h)
        X = F[n:, n:].T @ F[:n, n:]
        My = np.zeros((2 * n, 2 * n)); My[:n, :n] = self.A; My[:n, n:] = np.eye(n)
        S = expm(My * h)[:n, n:]
        i2 = np.array([X[self.nc + k, self.nc + k] for k in range(self.m)])
        i1 = (S @ z0)[self.nc:]
        return i2, i1

    def h_max(self, z):
        """r0.2 step rule: 1/48 of the fastest oscillatory mode still carrying amplitude, else a
        quarter of the slowest decay. Returns (h_max, h_first, osc)."""
        if self.A.size:
            lam_, Vec = np.linalg.eig(self.A)
            amp = np.abs(np.linalg.solve(Vec, z.astype(complex))) * np.linalg.norm(Vec, axis=0)
        else:
            lam_, amp = np.array([1.0]), np.array([1.0])
        mag = np.abs(lam_); nz = mag[mag > 1e-9 * mag.max()]
        osc = [abs(l.imag) for l, a in zip(lam_, amp) if abs(l.imag) > 1e-9 * mag.max()
               and abs(l.real) < 3 * abs(l.imag) and a > 1e-9 * max(amp.max(), 1e-300)]
        hm = (2 * math.pi / max(osc) / 48.0) if osc else 0.25 / nz.min()
        h0 = hm if osc else min(hm, 0.05 / nz.max())
        return hm, h0, bool(osc)


# ======================================================================================
# 5. THE MACHINE SIMULATOR
# ======================================================================================
class Sim:
    """Quasi-static / continuous simulation of one network over a theta schedule (r0.2 Sim, with
    the gap-model state machine, a monodromy tape and per-event records).
    mode 'qs' (motor out) or 'cont' (integrates motor branches between events)."""

    def __init__(self, net, mode="qs", dth=0.05, vstrike=None, record_events=False, arming="robust",
                 rpm=3000.0):
        self.net, self.mode, self.dth = net, mode, dth
        self.vstrike = vstrike
        self.compat = arming == "r02"
        self.T_CYC = 1.0 / (6 * rpm / 60.0); self.DEG = self.T_CYC / 60.0
        N = len(net.nodes); self.N = N; self.M = len(net.inds)
        self.alg = Alg(N)
        self.q = np.zeros(N); self.I = np.zeros(self.M)
        self.th = 0.0
        self.cond = set()                           # conducting gap names (rect held / arc lit)
        self.latched = set()
        self.gs = {}                                # rd / sr runtime state per gap
        self.ledger = dict(W=0.0, alg=0.0, ring=0.0, relax=0.0, motorR=0.0)
        self.diss_by = {}
        self.rec = record_events; self.events = []
        self.lx_dyn = [k for k, d in enumerate(net.inds) if d[5] == "lx" and d[3] > 0]
        self.lx_short = [k for k, d in enumerate(net.inds) if d[5] == "lx" and d[3] == 0]
        self.motor = [k for k, d in enumerate(net.inds) if d[5] == "motor"]
        self.gap_by = {g[0]: g for g in net.gaps}
        self._kc = {}
        self._ph_th, self._ph = None, 0.0
        self.tape = None                            # monodromy tape (n x n) when recording
        self.trace = None                           # per-grid-point record (eigen cycle)
        self.ring_frac = 48.0                       # steps per fastest live oscillation (M3 knob)
        self.chop_log = None                        # gate E3: |i| at every extinction / i_pk
        self.patterns = []

    # ---- phase / K ----
    def phase(self, th):
        if self.compat:
            return th % 60.0
        if th == self._ph_th:
            return self._ph
        p = round(th % 60.0, 9)
        p = 0.0 if p >= 60.0 else p
        self._ph_th, self._ph = th, p
        return p

    def kkey(self, th):
        return th if self.compat else self.phase(th)

    def Kof(self, th):
        k = self.kkey(th)
        K = self._kc.get(k)
        if K is None:
            if len(self._kc) > 4096:
                self._kc = {}
            K = self.net.K(th if self.compat else self.phase(th))
            self._kc[k] = K
        return K

    # ---- tape (monodromy) ----
    def _tq(self, Mq):
        """q <- Mq q (I unchanged), mirrored on the tape."""
        self.q = Mq @ self.q
        if self.tape is not None:
            self.tape[:self.N] = Mq @ self.tape[:self.N]

    def _tzero_I(self, ks):
        for k in ks:
            self.I[k] = 0.0
        if self.tape is not None:
            for k in ks:
                self.tape[self.N + k] = 0.0

    def _tring(self, R, E):
        """(q, I_dyn) <- the ring map z1 = E z (frozen K), mirrored on the tape."""
        z = R.z_of(self.q, self.I[R.dyn]); z1 = E @ z
        self.q = R.KPKci @ z1[:R.nc] if R.nc else np.zeros(self.N)
        self.I[R.dyn] = z1[R.nc:]
        if self.tape is not None:
            Z = np.vstack([R.P.T @ self.tape[:self.N], self.tape[[self.N + d for d in R.dyn]]])
            Z1 = E @ Z
            self.tape[:self.N] = R.KPKci @ Z1[:R.nc] if R.nc else 0.0
            for kk, d in enumerate(R.dyn):
                self.tape[self.N + d] = Z1[R.nc + kk]
        return z1

    # ---- helpers ----
    def armed(self, name, th):
        a, b = self.gap_by[name][4]
        if self.compat:
            t = th % 60.0
            return (a <= t < b) if a < b else (t >= a or t < b)
        t = self.phase(th); e = 1e-9
        if b - a >= 60.0 - 1e-12:
            return True
        a %= 60.0; b %= 60.0
        return (a - e <= t < b - e) if a < b else (t >= a - e or t < b - e)

    def ind_edges(self, which):
        return [(self.net.inds[k][1], self.net.inds[k][2]) for k in which]

    def lit(self, g):
        return g[3] in ("arc", "short") or (g[3] in ("rd", "sr") and self.gs.get(g[0], {}).get("st") == "lit")

    def fixed_edges(self, th, quasi=True):
        """Bidirectional closures: Lx->0 shorts always; dynamic Lx as shorts in quasi-static
        strokes; lit arcs (arc / lit rd, sr) and parity shorts that are conducting."""
        e = self.ind_edges(self.lx_short)
        if quasi:
            e += self.ind_edges(self.lx_dyn)
        for nm in sorted(self.cond):
            g = self.gap_by[nm]
            if self.lit(g):
                e.append((g[1], g[2]))
        return e

    def is_rect(self, g):
        """One-way at this instant: valves, and rd/sr gaps after extinction (forward rectifier)."""
        if g[3] in ("rect", "rect_latch"):
            return True
        return g[3] in ("rd", "sr") and self.gs.get(g[0], {}).get("st") == "rect"

    def cands(self, th):
        out = []
        for g in self.net.gaps:
            if self.is_rect(g) and self.armed(g[0], th) and g[0] not in self.latched:
                out.append(g)
        return out

    def held_rects(self):
        return [n for n in sorted(self.cond) if self.is_rect(self.gap_by[n])]

    def _edges_now(self, th, quasi):
        return self.fixed_edges(th, quasi) + [(self.gap_by[n][1], self.gap_by[n][2])
                                              for n in self.held_rects()]

    def voltages(self, th=None, K=None, quasi=True):
        th = self.th if th is None else th
        K = self.Kof(th) if K is None else K
        edges = self._edges_now(th, quasi)
        Vmat, _ = self.alg.solver(self.kkey(th), K, edges)
        return Vmat @ self.q

    def energy(self, K=None):
        K = self.Kof(self.th) if K is None else K
        V = self.voltages(K=K)
        E = 0.5 * V @ K @ V
        for k, d in enumerate(self.net.inds):
            if d[3] > 0 and d[5] == "motor":
                E += 0.5 * d[3] * self.I[k] ** 2
        return float(E)

    def _book(self, k, e):
        self.diss_by[k] = self.diss_by.get(k, 0.0) + e

    def _vth(self, g):
        if self.vstrike is None or g[0] in self.cond:
            return 0.0
        return self.vstrike * (BS_FRAC if g[0].startswith("BS") else 1.0)

    def _vgap(self, g, V):
        return (V[g[1]] if g[1] >= 0 else 0.0) - (V[g[2]] if g[2] >= 0 else 0.0)

    def _keep_lit(self):
        return set(n for n in self.cond if self.lit(self.gap_by[n]))

    # ---- stroke: capacitances th0 -> th1 at constant (cluster) charge, conducting gaps held ----
    def stroke(self, th1):
        K0 = self.Kof(self.th); K1 = self.Kof(th1)
        V0 = self.voltages(K=K0); U0 = 0.5 * V0 @ K0 @ V0
        held = self.held_rects()
        fixed = self.fixed_edges(self.th)
        hc = [(self.gap_by[n][1], self.gap_by[n][2]) for n in held]
        S, V1, qn, lam, _, Mq = lcp(self.alg, self.kkey(th1), K1, self.q, fixed, hc,
                                    prev=list(range(len(hc))))
        self.cond = self._keep_lit() | set(held[k] for k in S)
        self._tq(Mq)
        if len(S) == len(hc):
            # same closures: dU at constant cluster charge, cancellation-free [OC]:
            # U1 - U0 = -1/2 V1^T (K1 - K0) V0
            self.ledger["W"] += -0.5 * V1 @ (K1 - K0) @ V0
        else:
            self.ledger["W"] += 0.5 * V1 @ K1 @ V1 - U0
        self.th = th1

    # ---- continuous mode: motor branch dynamics over dt at frozen caps ----
    def motor_step(self, dt):
        if not self.motor or dt <= 0:
            return
        K = self.Kof(self.th)
        for _ in range(8):
            edges = self._edges_now(self.th, quasi=True)
            held = self.held_rects()
            R = Ring(self.net, self.alg, K, edges, self.motor)
            z0 = R.z_of(self.q, self.I[self.motor])
            i2, i1 = R.exact_integrals(z0, dt)
            E = R.E(dt)
            z1 = E @ z0
            qn = R.KPKci @ z1[:R.nc] if R.nc else np.zeros(self.N)
            lam = self.alg.flows(edges)[len(edges) - len(held):] @ (qn - self.q - R.Gn @ i1)
            sc_ = max(1e-300, float(np.max(np.abs(qn))))
            bad = [held[k] for k, l in enumerate(lam) if l < -1e-12 * sc_]
            if not bad:
                break
            self.cond -= set(bad)
        self._tring(R, E)
        e = float(np.sum(R.Rd * i2))
        self.ledger["motorR"] += e; self._book("motor_R", e)

    # ---- event: arming changes / newly forward rectifiers / arc strikes ----
    def _disarm(self, th):
        for n in list(self.cond):
            if not self.armed(n, th):
                self.cond.discard(n)
        for n in list(self.latched):
            if not self.armed(n, th):
                self.latched.discard(n)
        for n in list(self.gs):
            if not self.armed(n, th):
                del self.gs[n]

    def event(self, th, strike=False):
        """Complementarity over armed gaps with inductor currents HELD (dynamic Lx open for the
        instant). New closures dump through the Schur-complement loss; if a voltage is then left
        across a dynamic Lx, the ring is integrated and the residue relaxed. [r0.2]"""
        K = self.Kof(th); kk = self.kkey(th)
        self._disarm(th)
        V = self.voltages(K=K)
        new_arcs = []; vf = {}
        for g in self.net.gaps:
            if g[0] in self.cond or not self.armed(g[0], th):
                continue
            if g[3] in ("arc", "short") or (g[3] in ("rd", "sr") and g[0] not in self.gs):
                v = self._vgap(g, V)
                if abs(v) >= self._vth(g):
                    new_arcs.append(g[0]); vf[g[0]] = v
        cands = self.cands(th)
        for g in cands:
            vf[g[0]] = self._vgap(g, V)
        held = [g[0] for g in cands if g[0] in self.cond]
        for n in new_arcs:
            g = self.gap_by[n]
            if g[3] in ("rd", "sr"):
                self.gs[n] = dict(st="lit", Vf=vf[n], nhalf=0, p1=None, pk=0.0, t_ign=0.0,
                                  n_reign=0)
        base_fixed = self.fixed_edges(th, quasi=False)
        fixed = base_fixed + [(self.gap_by[n][1], self.gap_by[n][2]) for n in new_arcs]
        S, Vn, qn, lam, nv, Mq = lcp(self.alg, kk, K, self.q, fixed, [(g[1], g[2]) for g in cands],
                                     prev=[k for k, g in enumerate(cands) if g[0] in self.cond],
                                     vth=[self._vth(g) for g in cands])
        Snames = [cands[k][0] for k in S]
        new_closed = [n for n in Snames if n not in self.cond] + new_arcs
        if not new_closed:
            newcond = self._keep_lit() | set(Snames)
            # nothing switched: the re-projection is the identity up to rounding; in robust mode it
            # is skipped (with 440 nF motor caps beside pF strays each no-op projection costs
            # ~1e-12 of the stored energy) [ME]
            if self.compat or newcond != self.cond:
                self.cond = newcond
                self._tq(Mq)
            return None
        return self.fire(th, K, new_closed, Snames, held, base_fixed, new_arcs, Mq, vf, lam, S)

    def fire(self, th, K, new_closed, Snames, held, base_fixed, new_arcs, Mq, vf, lam, S):
        kk = self.kkey(th)
        self._fired = tuple(new_closed)
        base_edges = base_fixed + [(self.gap_by[n][1], self.gap_by[n][2]) for n in held if n in Snames]
        new_edges = [(self.gap_by[n][1], self.gap_by[n][2]) for n in new_closed]
        q_pre = self.q.copy()
        e_alg = event_loss(self.alg, K, q_pre, base_edges, new_edges, kkey=kk)
        self.cond = self._keep_lit() | set(new_arcs) | set(Snames)
        self._tq(Mq)
        self.ledger["alg"] += e_alg
        for n in new_closed:
            self._book(n, e_alg / len(new_closed))
        ev = None
        if self.rec:
            # charge dumped through each newly closed gap (forest flow of the instantaneous event)
            edges_all = self.fixed_edges(th, quasi=False) + [(self.gap_by[n][1], self.gap_by[n][2])
                                                             for n in self.held_rects()]
            Fl = self.alg.flows(edges_all) @ (self.q - q_pre)
            qd = {}
            for n in new_closed:
                g = self.gap_by[n]
                e_ = (g[1], g[2])
                qd[n] = float(Fl[edges_all.index(e_)]) if e_ in edges_all else 0.0
            ev = dict(th=float(self.phase(th)), gaps=list(new_closed), e_alg=e_alg,
                      Vf={n: float(vf.get(n, 0.0)) for n in new_closed}, q_dump=qd,
                      e_ring=0.0, e_relax=0.0, e_motor=0.0, i_pk=0.0, t_half=None, trv={},
                      q_ring={n: 0.0 for n in new_closed}, n_reign=0, ext={})
        if self.lx_dyn:
            # the ring after an rd / sr IGNITION carries that gap's extinction rule (its i_pk1);
            # an arc lit by an earlier event behaves as r0.2's sustained arc in later rings [IR]
            self._track = set(n for n in new_arcs if self.gap_by[n][3] in ("rd", "sr"))
            ev = self.ring(th, K, ev)
        if self.rec and ev is not None:
            self.events.append(ev)
        return ev

    # ---- the ring (vectorised r0.2 loop + the rd / sr gap state machine) ----
    def ring(self, th, K, ev, tmax=200e-6):
        """Exact LTI ring at frozen K. valve / arc (r0.2): stops at the driving Lx current's first
        zero; held rectifiers open when their current reverses (latching gaps latch); armed open
        rectifiers close when forward. rd / sr (Pass A'): a lit gap extinguishes at the current zero
        that ends the first half-cycle whose peak < I_hold * i_pk1 (i_pk1 excludes the first 50 ns);
        rd then acts as a forward rectifier; sr is off for its holdoff and re-ignites in either
        direction while |V_gap| > rho(t) |V_f|, rho = 1 - exp(-dt/t_rec). A lit gap still ringing at
        T_RING_MAX goes to its ring-down limit (exact relaxation) and stays lit. Then the residue
        relaxes. [r0.2 / IR]
        Implementation [ME]: per topology segment one expm(A h) and the r0.2 Gauss-Legendre
        quadrature folded into matrices; steps advanced in chunks with the r0.2 trigger tests
        evaluated on every step end; the first triggering step is bisected (64 halvings, state by
        eigen-decomposition) and then taken exactly with expm."""
        kk = self.kkey(th)
        dyn = self.lx_dyn + self.motor
        edges = self._edges_now(th, quasi=False)
        V = self.alg.solver(kk, K, edges)[0] @ self.q
        vL = np.array([self._vgap((None, self.net.inds[k][1], self.net.inds[k][2]), V) for k in self.lx_dyn])
        if np.max(np.abs(vL)) <= 1e-13 * max(1e-300, float(np.max(np.abs(V)))):
            self._relax(th, K, ev); return ev
        drv = self.lx_dyn[int(np.argmax(np.abs(vL)))]
        jd = dyn.index(drv)
        track = getattr(self, "_track", set())
        if track:
            tmax = T_RING_MAX
        t = 0.0; started = False; peak = 0.0; t_q = {}
        i2tot = np.zeros(self.M); i1tot = np.zeros(self.M); trace = [(0.0, 0.0)]
        rate_pk = {}; ring_chops = []
        nochop = not self.compat          # [IR, Pass A' H2]: valves open only at their own zero
        past_zero = False
        CH = 48
        done = False
        while t < tmax and not done:
            # ---------------- segment set-up (topology fixed until a switch) ----------------
            edges = self._edges_now(th, quasi=False)
            held = self.held_rects()
            cands = [g for g in self.cands(th) if g[0] not in self.cond]
            litsm = [n for n in sorted(self.cond) if n in track and self.lit(self.gap_by[n])]
            offsm = [n for n, s_ in self.gs.items() if s_["st"] == "off" and n in track]
            R = Ring(self.net, self.alg, K, edges, dyn)
            nc = R.nc; nz = nc + R.m
            z = R.z_of(self.q, self.I[dyn])
            hm, h0, osc = R.h_max(z)
            hmax = hm * 48.0 / self.ring_frac
            h_next = hmax if osc else h0
            nh = len(held)
            hrows = np.arange(len(edges) - nh, len(edges), dtype=int)
            lrows = np.array([edges.index((self.gap_by[n][1], self.gap_by[n][2])) for n in litsm], dtype=int)
            Tv = np.zeros((len(cands), nc)); vthc = np.array([self._vth(g) for g in cands])
            for ci, g in enumerate(cands):
                row = np.zeros(self.N)
                if g[1] >= 0: row[g[1]] += 1.0
                if g[2] >= 0: row[g[2]] -= 1.0
                Tv[ci] = row @ R.PKci if nc else 0.0
            Toff = np.zeros((len(offsm), nc))
            for oi, n in enumerate(offsm):
                g = self.gap_by[n]; row = np.zeros(self.N)
                if g[1] >= 0: row[g[1]] += 1.0
                if g[2] >= 0: row[g[2]] -= 1.0
                Toff[oi] = row @ R.PKci if nc else 0.0
            off_ext = np.array([self.gs[n]["t_ext"] for n in offsm])
            off_vf = np.array([abs(self.gs[n]["Vf"]) for n in offsm])
            off_trec = np.array([self.gap_by[n][6]["t_rec"] for n in offsm])
            off_hold = np.array([self.gap_by[n][6]["holdoff"] for n in offsm])
            zero_on = not litsm and not offsm and not past_zero   # drive-zero ends the ring only
                                                          # when no tracked arc is lit / in holdoff
            TrI = R.Tr                               # rates = TrI @ I
            PKciT = R.PKci.T if nc else np.zeros((0, self.N))
            hcache = {}

            def hmats(h):
                r = hcache.get(h)
                if r is None:
                    E = R.E(h); GL = R.gl_mats(h)
                    Q = np.zeros((R.m, nz, nz)); S1 = np.zeros((R.m, nz))
                    RT = []
                    for Mx, w in zip(GL, GL_W):
                        rows_ = Mx[nc:, :]
                        Q += (0.5 * h * w) * np.einsum("ki,kj->kij", rows_, rows_)
                        S1 += (0.5 * h * w) * rows_
                        if len(lrows):
                            RT.append(TrI[lrows] @ rows_)
                    r = (E, Q, S1, RT); hcache[h] = r
                return r
            eigd = None

            def zat(z0, tau):
                """state at tau from z0 (switch location only): eigen-decomposition, expm fallback"""
                ed = R.eigdec()
                if ed is None:
                    return R.E(tau) @ z0
                lam_, Vd, Vdi = ed
                return np.real(Vd @ (np.exp(lam_ * tau) * (Vdi @ z0)))

            def trig1(zs, ze, t_end, st0, pk0):
                """r0.2 triggers for one step (start zs, end ze); st0/pk0 = started/peak at start."""
                Is = zs[nc + jd]
                Iscale = max(pk0, abs(Is), 1e-300)
                s_drv = np.sign(Is) if st0 else 0.0
                Ie = ze[nc:]
                re_ = TrI @ Ie
                rev = [held[k] for k in range(nh) if re_[hrows[k]] < -1e-9 * Iscale]
                Ve = R.PKci @ ze[:nc] if nc else np.zeros(self.N)
                vsc = 1e-9 * max(1e-300, float(np.max(np.abs(Ve)))) if self.N else 0.0
                fwd = []
                if len(cands):
                    vc = Tv @ ze[:nc]
                    fwd = [g[0] for ci, g in enumerate(cands) if vc[ci] > vthc[ci] + vsc]
                zero = zero_on and st0 and (np.sign(Ie[jd]) != s_drv)
                lz = []
                if len(lrows):
                    rs_ = TrI[lrows] @ zs[nc:]
                    lz = [litsm[i] for i in range(len(lrows))
                          if np.sign(rs_[i]) != 0 and np.sign(re_[lrows[i]]) != np.sign(rs_[i])]
                rig, hend = [], []
                for oi, n in enumerate(offsm):
                    dtx = t_end - off_ext[oi]
                    rho = 1.0 if off_trec[oi] <= 0 else 1.0 - math.exp(-dtx / off_trec[oi])
                    if dtx > 2e-8 and abs(float(Toff[oi] @ ze[:nc])) > rho * off_vf[oi]:
                        rig.append(n)
                    if t_end >= off_ext[oi] + off_hold[oi]:
                        hend.append(n)
                return rev, fwd, zero, lz, rig, hend
            def margins(zs, ze, t_end, st0, pk0):
                """The same tests as trig1, as signed margins: component j is triggered iff
                m_j < 0 (strict[j]) or m_j <= 0 (not strict[j])."""
                Is = zs[nc + jd]
                Iscale = max(pk0, abs(Is), 1e-300)
                s_drv = np.sign(Is) if st0 else 0.0
                Ie = ze[nc:]
                re_ = TrI @ Ie
                m, strict = [], []
                for k in range(nh):
                    m.append(re_[hrows[k]] + 1e-9 * Iscale); strict.append(True)
                if len(cands):
                    Ve = R.PKci @ ze[:nc] if nc else np.zeros(self.N)
                    vsc = 1e-9 * max(1e-300, float(np.max(np.abs(Ve)))) if self.N else 0.0
                    vc = Tv @ ze[:nc]
                    for ci in range(len(cands)):
                        m.append(vthc[ci] + vsc - vc[ci]); strict.append(True)
                if zero_on and st0 and s_drv != 0:
                    m.append(s_drv * Ie[jd]); strict.append(False)
                if len(lrows):
                    rs_ = TrI[lrows] @ zs[nc:]
                    for i in range(len(lrows)):
                        sgn = np.sign(rs_[i])
                        if sgn != 0:
                            m.append(sgn * re_[lrows[i]]); strict.append(False)
                for oi in range(len(offsm)):
                    dtx = t_end - off_ext[oi]
                    rho = 1.0 if off_trec[oi] <= 0 else 1.0 - math.exp(-dtx / off_trec[oi])
                    m.append(rho * off_vf[oi] - abs(float(Toff[oi] @ ze[:nc])) if dtx > 2e-8 else 1.0)
                    strict.append(True)
                    m.append(off_ext[oi] + off_hold[oi] - t_end); strict.append(False)
                return np.array(m), np.array(strict)
            # ---------------- chunked stepping within the segment ----------------
            Etape = np.eye(nz) if self.tape is not None else None
            seg_changed = False
            while t < tmax and not done and not seg_changed:
                hs = []; tt = t; hn = h_next
                while len(hs) < CH and tt < tmax:
                    h = min(hn, hmax, tmax - tt)
                    hs.append(h); tt += h
                    hn = 2.0 * h if not osc else hmax
                C = len(hs)
                Zs = np.empty((C, nz)); zz = z
                for c in range(C):
                    zz = hmats(hs[c])[0] @ zz; Zs[c] = zz
                Zst = np.vstack([z[None, :], Zs[:-1]])
                tend = t + np.cumsum(hs)
                Ie = Zs[:, nc + jd]; Is = Zst[:, nc + jd]
                aIe = np.abs(Ie)
                pkb = np.maximum(peak, np.concatenate([[0.0], np.maximum.accumulate(aIe)[:-1]]))
                pka = np.maximum(pkb, aIe)
                Iscale = np.maximum(np.maximum(pkb, np.abs(Is)), 1e-300)
                stb = np.concatenate([[started], started | (np.cumsum(aIe > 0)[:-1] > 0)])
                sta = stb | (aIe > 0)
                sdrv = np.where(stb, np.sign(Is), 0.0)
                RE = Zs[:, nc:] @ TrI.T if len(edges) else np.zeros((C, 0))
                trg = np.zeros(C, dtype=bool)
                if nh:
                    trg |= np.any(RE[:, hrows] < -1e-9 * Iscale[:, None], axis=1)
                if len(cands):
                    VE = Zs[:, :nc] @ PKciT if nc else np.zeros((C, self.N))
                    vsc = 1e-9 * np.maximum(1e-300, np.max(np.abs(VE), axis=1))
                    trg |= np.any(Zs[:, :nc] @ Tv.T > vthc[None, :] + vsc[:, None], axis=1)
                if zero_on:
                    trg |= stb & (np.sign(Ie) != sdrv)
                if len(lrows):
                    RS = Zst[:, nc:] @ TrI[lrows].T
                    ss = np.sign(RS)
                    trg |= np.any((ss != 0) & (np.sign(RE[:, lrows]) != ss), axis=1)
                if len(offsm):
                    dtx = tend[:, None] - off_ext[None, :]
                    with np.errstate(over="ignore", divide="ignore", invalid="ignore"):
                        rho = np.where(off_trec[None, :] > 0, 1.0 - np.exp(-dtx / np.where(off_trec > 0, off_trec, 1.0)[None, :]), 1.0)
                    VO = np.abs(Zs[:, :nc] @ Toff.T)
                    trg |= np.any((dtx > 2e-8) & (VO > rho * off_vf[None, :]), axis=1)
                    trg |= np.any(tend[:, None] >= (off_ext + off_hold)[None, :], axis=1)
                over = sta & (aIe < 1e-3 * pka) & (not litsm) & (not offsm)
                if nochop:
                    hmax_i = np.max(np.abs(RE[:, hrows]), axis=1) if nh else np.zeros(C)
                    over = over & (hmax_i <= 1e-4 * pka)
                    if past_zero:
                        over = over | (hmax_i <= 1e-6 * pka)
                ci_t = int(np.argmax(trg)) if trg.any() else C
                ci_o = int(np.argmax(over)) if over.any() else C
                nacc = min(ci_t, ci_o + 1 if ci_o < C else C)
                if DEBUG_RING: print("chunk t0=%.4e C=%d ci_t=%d ci_o=%d nacc=%d h=%.4e" % (t, C, ci_t, ci_o, nacc, hs[0]))
                # ---- accept full steps [0, nacc) ----
                if nacc and self.chop_log is not None and nh:
                    pkr = np.max(np.abs(RE[:nacc][:, hrows]), axis=0)
                    for k_, n in enumerate(held):
                        rate_pk[n] = max(rate_pk.get(n, 0.0), float(pkr[k_]))
                if nacc:
                    for h in set(hs[:nacc]):
                        E, Q, S1, RT = hmats(h)
                        sel = [c for c in range(nacc) if hs[c] == h]
                        Zg = Zst[sel]
                        i2 = np.einsum("ci,kij,cj->k", Zg, Q, Zg); i1 = S1 @ Zg.sum(axis=0)
                        for kk_, k in enumerate(dyn):
                            i2tot[k] += i2[kk_]; i1tot[k] += i1[kk_]
                        if ev is not None:
                            qr = TrI @ i1
                            for n in ev["q_ring"]:
                                ge = (self.gap_by[n][1], self.gap_by[n][2]) if n in self.gap_by else None
                                if ge in edges:
                                    ev["q_ring"][n] += float(qr[edges.index(ge)])
                        if len(lrows):
                            okc = np.array(sel)
                            for li, n in enumerate(litsm):
                                s_ = self.gs[n]
                                m_ = (t + np.cumsum(hs)[okc] - hs[0] * 0 - s_["t_ign"]) > T_SPIKE
                                if m_.any():
                                    vals = [np.abs(Zg[m_] @ RTi[li]) for RTi in RT] + [np.abs(RE[okc[m_], lrows[li]])]
                                    s_["pk"] = max(s_["pk"], float(np.max(np.concatenate(vals))))
                    if Etape is not None:
                        for c in range(nacc):
                            Etape = hmats(hs[c])[0] @ Etape
                    z = Zs[nacc - 1]; t = float(tend[nacc - 1])
                    peak = float(pka[nacc - 1]); started = bool(sta[nacc - 1])
                    trace.extend(zip(tend[:nacc].tolist(), Ie[:nacc].tolist()))
                    h_next = hmax if osc else 2.0 * hs[nacc - 1]
                if ci_o < C and ci_o < ci_t:
                    done = True                             # overdamped: the ring is over (r0.2)
                    break
                if ci_t >= C:
                    continue                                # no switch in this chunk
                # ---- the triggering step: bisection, then the exact partial step ----
                zs0 = Zst[ci_t]; st0 = bool(stb[ci_t]); pk0 = float(pkb[ci_t]); h = hs[ci_t]
                h = self._switch_instant(trig1, margins, zat, lambda z0, tau: R.E(tau) @ z0,
                                         zs0, h, t, st0, pk0)
                E = R.E(h); GL = R.gl_mats(h)
                z1 = E @ zs0
                rev, fwd, zero, lz, rig, hend = trig1(zs0, z1, t + h, st0, pk0)
                i2, i1 = R.integrals(zs0, h, GL)
                for kk_, k in enumerate(dyn):
                    i2tot[k] += i2[kk_]; i1tot[k] += i1[kk_]
                if ev is not None:
                    qr = TrI @ i1
                    for n in ev["q_ring"]:
                        ge = (self.gap_by[n][1], self.gap_by[n][2]) if n in self.gap_by else None
                        if ge in edges:
                            ev["q_ring"][n] += float(qr[edges.index(ge)])
                if len(lrows):
                    for li, n in enumerate(litsm):
                        s_ = self.gs[n]
                        if t + h - s_["t_ign"] > T_SPIKE:
                            vals = [abs(float(TrI[lrows[li]] @ (Mx @ zs0)[nc:])) for Mx in GL]
                            vals.append(abs(float(TrI[lrows[li]] @ z1[nc:])))
                            s_["pk"] = max(s_["pk"], max(vals))
                if Etape is not None:
                    Etape = E @ Etape
                z = z1; t += h
                I1 = z1[nc:]
                peak = max(peak, abs(I1[jd])); started = started or abs(I1[jd]) > 0
                trace.append((t, float(I1[jd])))
                # commit the ring state before switching (the tape carries the composite map)
                self._commit_ring(R, z, Etape); Etape = np.eye(nz) if self.tape is not None else None
                if self.chop_log is not None and (rev or lz):
                    re1 = TrI @ z1[nc:]
                    Isc = max(pk0, abs(zs0[nc + jd]), 1e-300)
                    for n in rev:
                        r_ = hrows[held.index(n)]
                        ring_chops.append(("rev", n, abs(float(re1[r_]))))
                    for n in lz:
                        r_ = lrows[litsm.index(n)]
                        ring_chops.append(("zero", n, abs(float(re1[r_]))))
                changed = self._ring_actions(th, K, ev, t, t_q, rev, fwd, lz, rig, hend)
                still = any(self.gs.get(n, {}).get("st") in ("lit", "off") for n in track)
                if zero and not still:
                    if nochop:
                        hv = self.held_rects()
                        re1 = TrI @ z1[nc:]
                        imax = max([abs(float(re1[hrows[held.index(n)]])) for n in hv if n in held] + [0.0])
                        if imax > 1e-6 * max(peak, 1e-300):
                            past_zero = True                 # coast to the valves' own zeros
                            seg_changed = True
                            continue
                    done = True
                    break
                if past_zero and changed:
                    hv = self.held_rects()
                    re1 = TrI @ z1[nc:]
                    rem = [n for n in hv if n in held and abs(float(re1[hrows[held.index(n)]])) > 1e-6 * max(peak, 1e-300)]
                    if not rem:
                        done = True
                        break
                if (lz or hend) and track and not still:
                    if nochop:
                        hv = self.held_rects()
                        re1 = TrI @ z1[nc:]
                        imax = max([abs(float(re1[hrows[held.index(n)]])) for n in hv if n in held] + [0.0])
                        if imax > 1e-6 * max(peak, 1e-300):
                            past_zero = True                 # coast to the valves' own zeros
                            seg_changed = True
                            continue
                    done = True                            # the tracked gap is out: ring over
                    break
                if changed:
                    seg_changed = True
                else:
                    h_next = hmax if osc else 2.0 * h
                    if started and abs(I1[jd]) < 1e-3 * peak and not litsm and not offsm:
                        done = True
                        break
            if not seg_changed:
                self._commit_ring(R, z, Etape)
        e_ring = 0.0
        for k in self.lx_dyn:
            e = self.net.inds[k][4] * i2tot[k]; e_ring += e; self._book(self.net.inds[k][0] + "_R", e)
        e_m = sum(self.net.inds[k][4] * i2tot[k] for k in self.motor)
        self.ledger["ring"] += e_ring; self.ledger["motorR"] += e_m; self._book("motor_R", e_m)
        for n, s_ in self.gs.items():                      # sr still in holdoff at ring end: recovered
            if s_["st"] == "off":
                s_["st"] = "rect"
        self._track = set()
        self._ring_end_i = {}
        if self.chop_log is not None and R is not None:
            # gate E3 [brief 6]: |i| at every extinction over THAT event's i_pk1 (the ring's
            # transfer peak, i.e. the driving current's peak)
            ref = max(peak, 1e-300)
            for kind_, n, i_ in ring_chops:
                self.chop_log.append((kind_, n, i_ / ref))
            re_end = R.Tr @ z[R.nc:]
            for n in self.held_rects():
                e_ = (self.gap_by[n][1], self.gap_by[n][2])
                if e_ in R.edges:
                    self._ring_end_i[n] = abs(float(re_end[R.edges.index(e_)])) / ref
        if ev is not None:
            for n in ev["gaps"]:                          # ring ended on the transfer zero
                if n not in ev["trv"] and n in self.gap_by and n not in self._keep_lit():
                    ev["trv"][n] = self._trv_probe(th, K, n, ev)
                    t_q.setdefault(n, t)
            ev.update(t_ring=t, t_quench=t_q, i_pk=peak, drv=self.net.inds[drv][0], e_ring=e_ring,
                      e_motor=e_m, trace=trace[:: max(1, len(trace) // 400)])
            ev["t_half"] = min([t_q[n] for n in ev["gaps"] if n in t_q], default=None)
        self._relax(th, K, ev)
        return ev

    def _switch_instant(self, trig1, margins, zat, zex, zs0, h, t, st0, pk0):
        """The first instant in (0, h] at which the r0.2 trigger test is true, given it is true at
        h. Each triggered scalar margin is root-found (Illinois regula falsi, state by eigen-
        decomposition); the earliest root is then confirmed on the EXACT (expm) state and nudged
        forward until the trigger holds there, so the committed step always switches. Falls back
        to the r0.2 bisection (exact state). [ME]"""
        def any_trig(r_):
            return any(r_[:2]) or r_[2] or any(r_[3:])

        def trig_ex(tau):
            return any_trig(trig1(zs0, zex(zs0, tau), t + tau, st0, pk0))
        m0, strict = margins(zs0, zs0, t, st0, pk0)
        mh, _ = margins(zs0, zat(zs0, h), t + h, st0, pk0)
        fired = [j for j in range(len(mh)) if (mh[j] < 0 if strict[j] else mh[j] <= 0)
                 and not (m0[j] < 0 if strict[j] else m0[j] <= 0)]
        best = None
        for j in fired:
            def f(tau):
                return margins(zs0, zat(zs0, tau), t + tau, st0, pk0)[0][j]
            a, b = 0.0, h; fa, fb = m0[j], mh[j]
            side = 0
            for _ in range(80):
                if fb == fa:
                    break
                c = (a * fb - b * fa) / (fb - fa)
                if not (a < c < b):
                    c = 0.5 * (a + b)
                fc = f(c)
                if (fc < 0 if strict[j] else fc <= 0):
                    b, fb = c, fc
                    if side == -1:
                        fa *= 0.5
                    side = -1
                else:
                    a, fa = c, fc
                    if side == 1:
                        fb *= 0.5
                    side = 1
                if b - a <= 8e-16 * h:
                    break
            best = b if best is None else min(best, b)
        if best is not None:
            tau = best
            for k in range(48):
                if trig_ex(tau):
                    return tau
                tau = min(h, best + (h - best) * 2.0 ** (k - 46) + h * 2.0 ** (k - 52))
                if tau >= h:
                    break
        lo, hi = 0.0, h                                 # r0.2 bisection fallback (exact state)
        for _ in range(64):
            mid = 0.5 * (lo + hi)
            if mid <= lo or mid >= hi:
                break
            if trig_ex(mid):
                hi = mid
            else:
                lo = mid
        return hi

    def _commit_ring(self, R, z, Etape):
        """Write the ring state z back to (q, I_dyn); the tape takes the composite ring map."""
        self.q = R.KPKci @ z[:R.nc] if R.nc else np.zeros(self.N)
        self.I[R.dyn] = z[R.nc:]
        if self.tape is not None and Etape is not None:
            Z = np.vstack([R.P.T @ self.tape[:self.N], self.tape[[self.N + d for d in R.dyn]]])
            Z1 = Etape @ Z
            self.tape[:self.N] = R.KPKci @ Z1[:R.nc] if R.nc else 0.0
            for kk, d in enumerate(R.dyn):
                self.tape[self.N + d] = Z1[R.nc + kk]

    def _ring_actions(self, th, K, ev, t, t_q, rev, fwd, lz, rig, hend):
        changed = False
        for n in rev:
            self.cond.discard(n); t_q.setdefault(n, t); changed = True
            if self.gap_by[n][3] == "rect_latch":
                self.latched.add(n)
            if ev is not None and n in ev["gaps"] and n not in ev["trv"]:
                ev["trv"][n] = self._trv_probe(th, K, n, ev)
        for n in fwd:
            self.cond.add(n); changed = True
        for n in lz:                                   # a lit rd / sr gap's current zero
            s = self.gs[n]; s["nhalf"] += 1
            if s["p1"] is None:
                s["p1"] = s["pk"]
            h_ = self.gap_by[n][6]["I_hold"]; h_ = H_TO_ZERO if h_ <= 0 else h_
            if s["pk"] < h_ * s["p1"] or (s["nhalf"] == 1 and h_ > 1.0 and s["p1"] > 0):
                self.cond.discard(n); t_q.setdefault(n, t); changed = True
                if ev is not None and n in ev["gaps"]:
                    ev["ext"][n] = dict(t=t, nhalf=s["nhalf"])
                    if n not in ev["trv"]:
                        ev["trv"][n] = self._trv_probe(th, K, n, ev)
                if self.gap_by[n][3] == "sr" and self.gap_by[n][6]["holdoff"] > 0:
                    s.update(st="off", t_ext=t)
                else:
                    s["st"] = "rect"
            s["pk"] = 0.0
        for n in hend:
            if n in self.gs and self.gs[n]["st"] == "off":
                self.gs[n]["st"] = "rect"; changed = True
        for n in rig:                                  # M-SR re-ignition (either direction)
            if n not in self.gs or self.gs[n]["st"] != "off":
                continue
            Vn = self.voltages(th, K, quasi=False)
            vfn = self._vgap(self.gap_by[n], Vn)
            self._reignite(th, K, n, vfn, t, ev)
            changed = True
        return changed

    def _reignite(self, th, K, n, vfn, t, ev):
        """M-SR re-ignition inside a ring: instantaneous closure (Schur loss, inductor currents
        held), the gap lit again with V_f = its voltage at re-ignition."""
        kk = self.kkey(th)
        g = self.gap_by[n]
        base = self._edges_now(th, quasi=False)
        e_alg = event_loss(self.alg, K, self.q, base, [(g[1], g[2])], kkey=kk)
        self.gs[n] = dict(st="lit", Vf=vfn, nhalf=0, p1=None, pk=0.0, t_ign=t,
                          n_reign=self.gs[n].get("n_reign", 0) + 1)
        self.cond.add(n)
        getattr(self, "_track", set()).add(n)
        _, Mq = self.alg.solver(kk, K, self._edges_now(th, quasi=False))
        self._tq(Mq)
        self.ledger["alg"] += e_alg; self._book(n, e_alg)
        if ev is not None:
            ev["e_alg"] += e_alg; ev["n_reign"] += 1

    def _trv_probe(self, th, K, n, ev):
        """Open-circuit TRV probe [ME]: from the state at gap n's current zero, the post-zero network
        (n open, every other switch frozen) evolves freely for T_TRV; returns the reverse peak of
        V_gap(n) over its pre-closure V_f, and when it occurs. Diagnostic only: the state is not
        advanced."""
        g = self.gap_by[n]
        dyn = self.lx_dyn + self.motor
        was = n in self.cond
        self.cond.discard(n)                          # the probed gap is open after its zero
        edges = self._edges_now(th, quasi=False)
        if was:
            self.cond.add(n)
        R = Ring(self.net, self.alg, K, edges, dyn, cache=False)
        z = R.z_of(self.q, self.I[dyn])
        row = np.zeros(self.N)
        if g[1] >= 0: row[g[1]] += 1.0
        if g[2] >= 0: row[g[2]] -= 1.0
        c = row @ R.PKci if R.nc else np.zeros(0)
        nstep = 600
        E = R.E(T_TRV / nstep)
        vmin, tmin = 0.0, 0.0
        zz = z.copy()
        for k in range(1, nstep + 1):
            zz = E @ zz
            v = float(c @ zz[:R.nc]) if R.nc else 0.0
            if v < vmin:
                vmin, tmin = v, k * T_TRV / nstep
        vf = abs(ev["Vf"].get(n, 0.0)) if ev is not None else 0.0
        return dict(ratio=(-vmin / vf) if vf > 0 else float("nan"), t_us=tmin * 1e6,
                    v_rev=-vmin, Vf=vf)

    def _relax(self, th, K, ev):
        """Residue -> quasi-static equilibrium: dynamic Lx become shorts, their current -> 0.
        Loss = 1/2 v^T C_th v on the Lx ports (+ newly conducting rectifiers) + 1/2 L I^2. [ME]"""
        kk = self.kkey(th)
        e_ind = 0.0
        for k in self.lx_dyn:
            e_ind += 0.5 * self.net.inds[k][3] * self.I[k] ** 2
        self._tzero_I(self.lx_dyn)
        cands = self.cands(th)
        held = [g[0] for g in cands if g[0] in self.cond]
        S, V, qn, lam, nv, Mq = lcp(self.alg, kk, K, self.q, self.fixed_edges(th, quasi=True),
                                    [(g[1], g[2]) for g in cands],
                                    prev=[k for k, g in enumerate(cands) if g[0] in self.cond])
        Snames = [cands[k][0] for k in S]
        newS = [n for n in Snames if n not in self.cond]
        if self.chop_log is not None:
            for n in held:                        # a held valve the relaxation opens: its current
                if n not in Snames:               # at the ring's end is the chop (gate E3)
                    self.chop_log.append(("relax-open", n, getattr(self, "_ring_end_i", {}).get(n, 0.0)))
        base = self.fixed_edges(th, quasi=False) + [(self.gap_by[n][1], self.gap_by[n][2])
                                                    for n in held if n in Snames]
        new_edges = self.ind_edges(self.lx_dyn) + [(self.gap_by[n][1], self.gap_by[n][2]) for n in newS]
        e_cap = event_loss(self.alg, K, self.q, base, new_edges, kkey=kk)
        self.cond = self._keep_lit() | set(Snames)
        q0 = self.q.copy()
        self._tq(Mq)
        self.ledger["relax"] += e_cap + e_ind
        self._book("relax", e_cap + e_ind)
        if ev is not None:
            ev["e_relax"] = e_cap + e_ind
            edges_all = self.fixed_edges(th, quasi=True) + [(self.gap_by[n][1], self.gap_by[n][2])
                                                            for n in self.held_rects()]
            Fl = self.alg.flows(edges_all) @ (self.q - q0)
            for n in ev["q_ring"]:
                if n in self.gap_by:
                    ge = (self.gap_by[n][1], self.gap_by[n][2])
                    if ge in edges_all:
                        ev["q_ring"][n] += float(Fl[edges_all.index(ge)])

    # ---- one cycle on the schedule ----
    def grid(self, th0):
        pts = set(np.round(np.arange(0.0, 60.0 + 1e-9, self.dth), 9))
        for g in self.net.gaps:
            a, b = g[4]
            pts.add(round(a % 60.0, 9)); pts.add(round(b % 60.0, 9))
        pts = sorted(p for p in pts if p < 60.0 - 1e-12)
        return [th0 + p for p in pts] + [th0 + 60.0]

    def cycle(self, k, zth=None, cut=0.0, on_point=None):
        th0 = 60.0 * k + cut
        g = sorted(set(self.grid(60.0 * k) + self.grid(60.0 * (k + 1))))
        g = [x for x in g if th0 - 1e-12 <= x <= th0 + 60.0 + 1e-12]
        if abs(g[0] - th0) > 1e-9:
            g = [th0] + g
        if abs(g[-1] - (th0 + 60.0)) > 1e-9:
            g = g + [th0 + 60.0]
        if zth is not None:
            g = sorted(set(g) | {th0 + zth})
        mag = None
        pat = []
        for th in g[1:]:
            if self.mode == "cont":
                self.motor_step((th - self.th) * self.DEG)
            self.stroke(th)
            self._fired = None
            self.event(th, strike=self.vstrike is not None)
            pat.append((tuple(sorted(self.cond)), self._fired))
            if zth is not None and abs(th - (60.0 * k + zth)) < 1e-9:
                mag = self.state_mag()
            if on_point is not None:
                on_point(self, th)
        self.patterns.append(pat)
        return mag

    def state_mag(self):
        V = self.voltages()
        return abs(V[self.net.idx["1"]]) + abs(V[self.net.idx["4"]])

    def rescale(self, s):
        self.q *= s; self.I *= s
        for k in self.ledger:
            self.ledger[k] *= s * s
        for k in self.diss_by:
            self.diss_by[k] *= s * s
        for n, st in self.gs.items():
            st["Vf"] = st.get("Vf", 0.0) * s
            if st.get("p1") is not None:
                st["p1"] *= s
            st["pk"] = st.get("pk", 0.0) * s


def seed(sim, v=-1.0):
    """V1 = V4 = v, others 0 (the solve_doubler4/shuttle seed), as node charges at theta."""
    K = sim.Kof(sim.th); V = np.zeros(sim.N)
    V[sim.net.idx["1"]] = v; V[sim.net.idx["4"]] = v
    sim.q = K @ V


def make_sim(net, cfg, record=False):
    mode = "cont" if (cfg.get("motor") and net.meta.get("motor")) else "qs"
    return Sim(net, mode=mode, dth=cfg["dth"], record_events=record, arming=cfg["arming"],
               rpm=cfg["rpm"])


def run_machine(net, mode="qs", ncyc=40, burn=20, dth=0.05, vstrike=None, seed_v=-1.0,
                normalize=True, record_from=None, zth=None, cut=0.0, arming="robust", rpm=3000.0,
                sim=None):
    """r0.2 run_machine: ncyc cycles; per-cycle ledger rows after burn; z = |V1|+|V4| ratio at cycle
    boundaries (median over the post-burn cycles; zth: at a fixed in-cycle phase)."""
    if sim is None:
        sim = Sim(net, mode=mode, dth=dth, vstrike=vstrike, arming=arming, rpm=rpm)
        sim.th = cut
        seed(sim, seed_v)
    rows = []
    for k in range(ncyc):
        sim.rec = record_from is not None and k >= record_from
        E0 = sim.energy(); L0 = dict(sim.ledger); D0 = dict(sim.diss_by)
        m0 = sim.state_mag()
        mz = sim.cycle(k, zth, cut)
        E1 = sim.energy(); m1 = sim.state_mag()
        dL = {kk: sim.ledger[kk] - L0.get(kk, 0.0) for kk in sim.ledger}
        dD = {kk: sim.diss_by[kk] - D0.get(kk, 0.0) for kk in sim.diss_by}
        W = dL["W"]; Ed = dL["alg"] + dL["ring"] + dL["relax"] + dL["motorR"]
        rows.append(dict(cycle=k, z=m1 / m0 if m0 > 0 else float("nan"), mz=mz, W=W, dE=E1 - E0,
                         E_diss=Ed, eta=(E1 - E0) / W if W else float("nan"),
                         resid=abs(W - (E1 - E0) - Ed) / max(abs(W), 1e-300), parts=dL, by=dD))
        rows[-1]["norm"] = 1.0
        if normalize and m1 > 0:
            sim.rescale(1.0 / m1); rows[-1]["norm"] = m1
    st = rows[burn:]
    if zth is not None:
        zs = [st[i + 1]["mz"] / (st[i]["mz"] / st[i]["norm"]) for i in range(len(st) - 1)]
    else:
        zs = [r["z"] for r in st]
    return dict(z=float(np.median(zs)), z_all=zs, z_last=float(zs[-1]),
                eta=float(np.mean([r["eta"] for r in st])),
                eta_spread=float(np.ptp([r["eta"] for r in st])),
                resid_max=float(max(r["resid"] for r in st)), rows=rows, sim=sim)


# ======================================================================================
# 6. MONODROMY — z as the spectral radius of the composed cycle map                    [ME]
# ======================================================================================
def _statevec(sim):
    return np.concatenate([sim.q, sim.I])


def _setstate(sim, x):
    sim.q = np.array(x[:sim.N], dtype=float); sim.I = np.array(x[sim.N:], dtype=float)


def taped_cycle(sim, k, record=False, events=False):
    """One cycle with the tape on: returns the cycle map Phi (x_end = Phi x_start), the discrete
    switching pattern and (record) the cycle's observables: per-grid-point voltages, conduction,
    stored energy, cumulative work; the per-event records (events); the cycle ledger."""
    n = sim.N + sim.M
    sim.tape = np.eye(n)
    for kk in sim.lx_short:                      # Lx -> 0: a short, not a state (its "current"
        sim.tape[sim.N + kk] = 0.0               # row would be a spurious eigenvalue 1)
    sim.ledger = {kk: 0.0 for kk in sim.ledger}; sim.diss_by = {}; sim.events = []
    sim.rec = bool(events)
    pts = []
    E0 = sim.energy(); m0 = sim.state_mag()
    x0 = _statevec(sim)

    def on_point(s, th):
        V = s.voltages()
        ph = s.phase(th)
        pts.append(dict(th=60.0 if (ph < 1e-9 and th > 60.0 * k + 30.0) else float(ph),
                        V=V.copy(), cond=sorted(s.cond), E=s.energy(), W=s.ledger["W"]))
    sim.cycle(k, on_point=on_point if record else None)
    Phi = sim.tape; sim.tape = None
    sim.rec = False
    rec = None
    if record:
        rec = dict(points=pts, events=list(sim.events), ledger=dict(sim.ledger),
                   by=dict(sim.diss_by), E0=E0, E1=sim.energy(), m0=m0, m1=sim.state_mag(), x0=x0)
    return Phi, sim.patterns[-1], rec


NEUTRAL_TOL = 1e-9          # |lam - 1| below this: an exact invariant of the cycle map [ME]


def dominant(Phi, x_ref):
    """Dominant eigenpair of the cycle map, EXCLUDING exact invariants (lam = 1 to 1e-9: e.g. DC
    charge trapped on the motor DC-block caps, which the cycle neither grows nor drains) — a
    neutral mode is not pumping [ME]. Returns (lam, v, sub-ratio, n_neutral)."""
    w, vecs = np.linalg.eig(Phi)
    neutral = np.abs(w - 1.0) < NEUTRAL_TOL
    cand = np.where(~neutral)[0]
    if not len(cand):
        cand = np.arange(len(w))
    k = int(cand[np.argmax(np.abs(w[cand]))])
    lam = w[k]
    v = np.real(vecs[:, k])
    if float(v @ x_ref) < 0:
        v = -v
    srt = np.sort(np.abs(w[cand]))[::-1]
    sub = float(srt[1] / srt[0]) if len(srt) > 1 and srt[0] > 0 else 0.0
    return lam, v, sub, int(neutral.sum())


def monodromy(net, cfg, settle=None, maxit=None, tol=1e-12, seed_v=-1.0, sim=None, log=None,
              record=False, events=False):
    """z by the closed-cycle eigenvalue. The drawn pump is piecewise-linear and homogeneous with
    scale-invariant switching, so once the switching pattern repeats one cycle IS a linear map
    Phi [OC]. Procedure [ME]: settle, then tape every cycle; once two consecutive cycles share a
    pattern, restart from Phi's dominant eigenvector (a jump); converged when the cycle taped
    from that eigen-state repeats the pattern and |dz| <= tol. A jump that breaks the pattern is
    undone (plain iteration resumes from the pre-jump state). The last taped cycle starts on the
    eigen-state, so its record is the steady waveform. Returns dict (z, v, sim, rec, ...)."""
    cont = sim.mode == "cont" if sim is not None else bool(cfg.get("motor") and net.meta.get("motor"))
    settle = (6 if cont else 2) if settle is None else settle
    maxit = (24 if cont else 10) if maxit is None else maxit
    if sim is None:
        sim = make_sim(net, cfg)
        seed(sim, seed_v)
    k = 0
    for _ in range(settle):
        sim.cycle(k); k += 1
        m = sim.state_mag()
        if m > 0:
            sim.rescale(1.0 / m)
    hist = []
    conv = False; rec = None
    prev = None                      # (pattern, z, jumped) of the previous taped cycle
    backup = None
    jfail = 0                        # consecutive jumps whose next cycle changed the pattern
    for it in range(maxit):
        x0 = _statevec(sim)
        from_eig = prev is not None and prev[2]
        Phi, pat, rec_ = taped_cycle(sim, k, record=record and from_eig, events=events and from_eig)
        k += 1
        if rec_ is not None:
            rec = rec_
        lam, v, sub, nneu = dominant(Phi, x0)
        z = float(abs(lam))
        x1 = _statevec(sim)
        hist.append(dict(it=it, z=z, complex=bool(abs(lam.imag) > 1e-12 * abs(lam)), sub=sub,
                         neutral=nneu, jumped=from_eig))
        if log:
            log(f"monodromy it {it}: z={z:.12f} sub={sub:.3f}{' (from eigen-state)' if from_eig else ''}")
        same = prev is not None and pat == prev[0]
        if from_eig:
            if same and abs(z - prev[1]) <= tol * max(1.0, z):
                conv = True
                break
            jfail = 0 if same else jfail + 1
        if jfail >= 3 and from_eig and not same and backup is not None:
            # cautious mode: a jump that changes the pattern is undone; iterate plainly
            _setstate(sim, backup[0]); sim.gs, sim.cond, sim.latched = backup[1], backup[2], backup[3]
            backup = None
            m = sim.state_mag()
            if m > 0:
                sim.rescale(1.0 / m)
            prev = (pat, z, False)
            continue
        if jfail < 3 or same:
            backup = (x1.copy(), dict(sim.gs), set(sim.cond), set(sim.latched))
            nv = np.linalg.norm(v); _setstate(sim, v / nv * np.linalg.norm(x1))
            m = sim.state_mag()
            if m > 0:
                sim.rescale(1.0 / m)
            prev = (pat, z, True)
            continue
        m = sim.state_mag()
        if m > 0:
            sim.rescale(1.0 / m)
        prev = (pat, z, False)
    if record and (rec is None or not conv):
        # not converged (or no eigen-state cycle recorded): record one more cycle from the last
        # eigen-state estimate so the page can still show the (flagged) waveform
        nv = np.linalg.norm(v); _setstate(sim, v / nv)
        m = sim.state_mag()
        if m > 0:
            sim.rescale(1.0 / m)
        Phi2, pat2, rec = taped_cycle(sim, k, record=True, events=events); k += 1
    xs = rec["x0"] if rec else x0
    align = float(abs(xs @ v) / max(np.linalg.norm(xs) * np.linalg.norm(v), 1e-300))
    return dict(z=z, lam=complex(lam), v=v, Phi=Phi, sim=sim, k=k, converged=conv, hist=hist,
                sub=sub, pattern=pat, rec=rec, align=align)


# ======================================================================================
# 7. OBSERVABLES — eigen-cycle record: ledger, eta(cut), waveforms, events, TRV
# ======================================================================================
def eta_cut_curve(rec, z, ncut=121):
    """eta(cut) = (z^2 - 1) E(cut) / [W(cut -> 60) + z^2 W(0 -> cut)] over the sector, from the
    eigen-cycle (the steady waveform grows by z per cycle) [OC]. W, E at grid points."""
    pts = rec["points"]
    ths = np.array([p["th"] for p in pts]); Es = np.array([p["E"] for p in pts])
    Ws = np.array([p["W"] for p in pts])
    Wtot = Ws[-1]
    E0 = rec["E0"]
    cut_th = [0.0]; cut_eta = [(z * z - 1.0) * E0 / Wtot if Wtot else float("nan")]
    step = max(1, len(pts) // ncut)
    for i in range(0, len(pts) - 1, step):
        Wa = Ws[i]
        denom = (Wtot - Wa) + z * z * Wa
        cut_th.append(float(ths[i])); cut_eta.append(float((z * z - 1.0) * Es[i] / denom) if denom else float("nan"))
    return cut_th, cut_eta


def _jsonable(o):
    if isinstance(o, dict):
        return {str(k): _jsonable(v) for k, v in o.items()}
    if isinstance(o, (list, tuple)):
        return [_jsonable(v) for v in o]
    if isinstance(o, np.ndarray):
        return [_jsonable(v) for v in o.tolist()]
    if isinstance(o, (np.floating,)):
        o = float(o)
    if isinstance(o, (np.integer,)):
        return int(o)
    if isinstance(o, float):
        return o if math.isfinite(o) else None
    if isinstance(o, complex):
        return [o.real, o.imag]
    return o


def _decimate(n, nmax=720):
    return list(range(0, n, max(1, int(math.ceil(n / nmax))))) + ([n - 1] if n > 1 else [])


def summarize(net, cfg, mono, rec):
    """JSON-safe observables of one evaluated machine (the eigen-cycle, cut at 0 deg)."""
    z = mono["z"]; sim = mono["sim"]
    led = rec["ledger"]
    W = led["W"]; Ed = led["alg"] + led["ring"] + led["relax"] + led["motorR"]
    dE = rec["E1"] - rec["E0"]
    # three independently computed terms [OC]: W (sum of stroke dU at constant charge), dE (the
    # boundary states), E_diss (Schur-complement dumps + ring i^2 R + relaxation + motor i^2 R)
    resid = (W - dE - Ed) / max(abs(W), 1e-300)
    cut_th, cut_eta = eta_cut_curve(rec, z)
    names = net.nodes
    pts = rec["points"]
    ix = _decimate(len(pts))
    pts_d = [pts[i] for i in ix]
    gaps = [g for g in net.gaps]
    vmax = max([float(np.max(np.abs(p["V"]))) for p in pts_d] + [1e-300])
    wave = dict(th=[p["th"] for p in pts_d], norm=vmax,
                V={n: [float(p["V"][i]) / vmax for p in pts_d] for i, n in enumerate(names)
                   if n in ("1", "2", "3", "4", "7", "8", "n17", "n23")},
                gapV={g[0]: [float(sim._vgap(g, p["V"])) / vmax for p in pts_d] for g in gaps},
                cond={g[0]: [1 if g[0] in p["cond"] else 0 for p in pts_d] for g in gaps},
                E=[p["E"] for p in pts_d])
    ev_rows = []
    for ev in rec["events"]:
        for n in ev["gaps"]:
            g = sim.gap_by.get(n)
            trv = ev["trv"].get(n)
            model = g[6].get("model", "valve") if g is not None and len(g) > 6 and g[6] else "valve"
            q = ev["q_dump"].get(n, 0.0) + ev["q_ring"].get(n, 0.0)
            ev_rows.append(dict(gap=n, cls=GAP_CLASS.get(n, g[5] if g else ""), model=model,
                                th=ev["th"], Vf=ev["Vf"].get(n, 0.0), q=q,
                                e_gap=ev["e_alg"] / len(ev["gaps"]), e_esr=ev.get("e_ring", 0.0),
                                e_motor=ev.get("e_motor", 0.0), e_relax=ev.get("e_relax", 0.0),
                                t_half_us=(ev["t_half"] * 1e6 if ev.get("t_half") else None),
                                i_pk=ev.get("i_pk", 0.0), trv=(trv or {}).get("ratio"),
                                trv_t_us=(trv or {}).get("t_us"),
                                needs_rect=bool(trv and trv.get("ratio") and trv["ratio"] > 1.0),
                                n_reign=ev.get("n_reign", 0), ext=ev["ext"].get(n),
                                chop=ev.get("chop", {}).get(n)))
    # one row per gap conduction episode: the strike (largest |V_f|) + the quasi-static
    # re-closures that follow it inside the window ("micro-events" of the r0.2 grid)
    episodes = []
    for gname in [g[0] for g in gaps]:
        rows = [e for e in ev_rows if e["gap"] == gname]
        if not rows:
            continue
        main = max(rows, key=lambda e: abs(e["Vf"]))
        episodes.append(dict(gap=gname, cls=main["cls"], model=main["model"], th=rows[0]["th"],
                             th_strike=main["th"], Vf=main["Vf"], n_events=len(rows),
                             q=sum(e["q"] for e in rows), e_gap=sum(e["e_gap"] for e in rows),
                             e_esr=sum(e["e_esr"] for e in rows), e_motor=sum(e["e_motor"] for e in rows),
                             e_relax=sum(e["e_relax"] for e in rows), t_half_us=main["t_half_us"],
                             i_pk=main["i_pk"], trv=main["trv"], trv_t_us=main["trv_t_us"],
                             needs_rect=main["needs_rect"], n_reign=sum(e["n_reign"] for e in rows),
                             ext=main["ext"]))
    episodes.sort(key=lambda e: e["th"])
    by = {k: v / W for k, v in rec["by"].items()} if W else {}
    win = {g[0]: [float(g[4][0]), float(g[4][1])] for g in gaps}
    models = {g[0]: (g[6].get("model") if len(g) > 6 and g[6] else "valve") for g in gaps}
    return dict(z=z, margin=z - 1.0, pumps=bool(z > 1.0), converged=mono["converged"],
                complex=bool(abs(mono["lam"].imag) > 1e-12 * abs(mono["lam"])),
                sub_ratio=mono["sub"], mono_hist=mono["hist"],
                ledger=dict(cut_deg=0.0, W=W, dE=dE, E_diss=Ed, gap=led["alg"], esr=led["ring"],
                            relax=led["relax"], motor=led["motorR"], resid=resid,
                            eta_at_cut=dE / W if W else None, by_frac=by,
                            W_by=_w_by_varicap(sim, rec)),
                eta_cut=dict(th=cut_th, eta=cut_eta, min=float(np.nanmin(cut_eta)),
                             max=float(np.nanmax(cut_eta))),
                wave=wave, events=ev_rows, episodes=episodes, nodes=names, windows=win,
                models=models)


def _w_by_varicap(sim, rec):
    """W_mech by varicap over the recorded cycle: sum over strokes of -1/2 V^2 dC per varicap
    (constant-charge stroke work, first order in the stroke; normalised to the ledger W). [OC]"""
    pts = rec["points"]
    if len(pts) < 2:
        return {}
    net = sim.net
    raw = {}
    prev = None
    for p in pts:
        cv = {nm: (i, j, c) for nm, i, j, c in net.cap_values(p["th"]) if isinstance(
            [C for n2, a2, b2, C in net.caps if n2 == nm][0], str) or callable(
            [C for n2, a2, b2, C in net.caps if n2 == nm][0])}
        if prev is not None:
            V = p["V"]
            for nm, (i, j, c) in cv.items():
                v = (V[i] if i >= 0 else 0.0) - (V[j] if j >= 0 else 0.0)
                dc_ = c - prev[nm][2]
                raw[nm] = raw.get(nm, 0.0) - 0.5 * v * v * dc_
        prev = cv
    tot = sum(raw.values())
    W = rec["ledger"]["W"]
    return {k: (v / tot * W if tot else 0.0) for k, v in raw.items()}


# ======================================================================================
# 8. PUBLIC API — evaluate / sweep / canaries / selftest (JSON in, JSON out)
# ======================================================================================
def _eval_one(cfg, lx=None, galvanic=None, log=None, full=True, events=True):
    net = build_net(cfg, lx=lx, galvanic=galvanic)
    mono = monodromy(net, cfg, log=log, record=full, events=events and full)
    out = dict(z=mono["z"], converged=mono["converged"], align=mono["align"])
    if full:
        out.update(summarize(net, cfg, mono, mono["rec"]))
    return out, net


def scale_readouts(res, cfg):
    """Operating-point scaling (linear, scale-free engine) [OC]: the eigen-mode is scaled so the
    load-gap voltage at its station equals V_strike (D-SCALE default, [IR])."""
    load = [e for e in res.get("episodes", []) if e["cls"] == "load" and abs(e["Vf"]) > 0]
    if not load:
        return None
    s = cfg["V_strike_kV"] * 1e3 / abs(load[0]["Vf"])
    rows = []
    for e in res["episodes"]:
        rows.append(dict(gap=e["gap"], th=e["th_strike"], V_kV=abs(e["Vf"]) * s / 1e3,
                         i_pk_A=e["i_pk"] * s, q_uC=abs(e["q"]) * s * 1e6,
                         E_gap_mJ=e["e_gap"] * s * s * 1e3, E_esr_mJ=e["e_esr"] * s * s * 1e3,
                         E_motor_mJ=e["e_motor"] * s * s * 1e3,
                         trv_kV=(e["trv"] * abs(e["Vf"]) * s / 1e3) if e["trv"] else None))
    led = res["ledger"]
    return dict(scale_V_per_unit=s, anchor=f"|V_f(load)| = {cfg['V_strike_kV']:.1f} kV",
                W_mech_mJ=led["W"] * s * s * 1e3, E_diss_mJ=led["E_diss"] * s * s * 1e3,
                rows=rows)


def evaluate(config=None, twins=True, log=None):
    """The calculator's one call: JSON config in, JSON observables out (the main machine; its G
    twin, Lx shorted; its G0 twin, islands -> ideal station valves)."""
    import time
    cfg = make_config(config)
    t0 = time.time()
    res, net = _eval_one(cfg, log=log)
    res["time_s"] = time.time() - t0
    res["config"] = cfg
    res["scaled"] = scale_readouts(res, cfg)
    if twins and cfg["topology"] == "drawn":
        tw = {}
        for name, kw in (("G", dict(lx=0.0)), ("G0", dict(galvanic=True))):
            t1 = time.time()
            r, _ = _eval_one(cfg, log=log, full=True, events=False, **kw)
            tw[name] = dict(z=r["z"], converged=r["converged"], dz=res["z"] - r["z"],
                            eta_at_cut=r["ledger"]["eta_at_cut"],
                            deta=(res["ledger"]["eta_at_cut"] or 0) - (r["ledger"]["eta_at_cut"] or 0),
                            time_s=time.time() - t1)
        res["twins"] = tw
    res["lamps"] = lamps(cfg, res)
    res["time_total_s"] = time.time() - t0
    return _jsonable(res)


def sweep(config, key, values, twins=False, log=None):
    """z against one numeric input; the z = 1 crossing (linear interpolation between the bracketing
    points, the findCriticalCa pattern) is marked."""
    base = make_config(config)
    if key not in _NUMERIC:
        raise KeyError(f"{key!r} is not a numeric input")
    zs = []
    for v in values:
        c = dict(base); c[key] = float(v)
        r, _ = _eval_one(make_config({kk: c[kk] for kk in c}), log=log, full=False)
        zs.append(r["z"])
    cross = []
    for i in range(len(values) - 1):
        a, b = zs[i] - 1.0, zs[i + 1] - 1.0
        if a == 0:
            cross.append(values[i])
        elif a * b < 0:
            cross.append(values[i] + (values[i + 1] - values[i]) * a / (a - b))
    return _jsonable(dict(key=key, values=list(values), z=zs, crossings=cross))


def lamps(cfg, res):
    """I3 z band, I6 parasitic floor, I11 cross-fire, I12 resonant timing (design_synth's rules and
    closed forms, imported), plus the TRV admissibility. I12 uses this engine's ring t1/2."""
    out = {}
    try:
        import design_synth as ds
    except Exception as e:                         # the lamps are advisory: never block the numbers
        return dict(error=f"design_synth unavailable: {e}")
    z = res["z"]
    lo, hi = ds.Z_BAND
    out["I3_scalefree_z"] = dict(pass_=bool(lo <= z <= hi), detail=f"z={z:.4f} in {ds.Z_BAND}")
    out["I6_parasitic_floor"] = dict(pass_=bool(cfg["Cpar"] >= ds.CPAR_FLOOR_pF and cfg["C1min"] >= 0),
                                     detail=f"Cpar={cfg['Cpar']:.1f} >= {ds.CPAR_FLOOR_pF:.0f} pF")
    ov = ds.overlap_deg(cfg["d_ballMm"], cfg["r_gapMm"], cfg["g_latMm"])
    spacing = cfg["st_BS3"] - cfg["st_SG3b"]
    out["I11_crossfire"] = dict(pass_=bool(spacing - ov > 0),
                                detail=f"overlap {ov:.2f} deg < SG3b-BS3 {spacing:.2f} deg "
                                       f"(margin {spacing - ov:+.2f})")
    omega = cfg["rpm"] * 2 * math.pi / 60.0
    t_ov = math.radians(ov) / omega
    th_us = [e["t_half_us"] for e in res.get("events", []) if e.get("t_half_us")]
    t_half = max(th_us) * 1e-6 if th_us else 0.0
    need = ds.T_STRIKE_S + t_half + ds.T_COND_S
    out["I12_resonant_timing"] = dict(pass_=bool(t_ov - need > 0),
                                      detail=f"overlap {t_ov * 1e6:.0f} us >= strike+t1/2+dwell "
                                             f"{need * 1e6:.1f} us (t1/2 {t_half * 1e6:.2f} us, engine)")
    bad = [e for e in res.get("events", []) if e.get("needs_rect") and e["model"] != "valve"]
    valve_need = [e for e in res.get("events", []) if e.get("needs_rect") and e["model"] == "valve"]
    out["TRV_admissible"] = dict(pass_=not bad,
                                 detail=(f"{len(bad)} symmetric-gap event(s) need a rectifier "
                                         f"(TRV > V_f)" if bad else
                                         f"valve events needing a rectifier: {len(valve_need)} "
                                         f"(the valve model assumes one)"))
    return out


# ---- canaries (run in the worker before any number is displayed) ----
K1_Z, K2_Z, K3_Z = 1.3340016, 1.5225272, 1.2983502589
K4_T, K4_V = 2.22155, 998.891


def s2_net(R):
    net = Net()
    s, x, b = net.n("src"), net.n("x"), net.n("bnk")
    net.caps += [("Csrc", s, GND, 1e-9), ("Cx", x, GND, 1e-15), ("Cbank", b, GND, 1e-9)]
    net.inds.append(("Lx", s, x, 1e-3, R, "lx"))
    net.gaps.append(("D", x, b, "rect", (0.0, 60.0), "load", {}))
    return net


def s2_ring(R=2.0, arming="robust"):
    """K4 / H1: the ring path on the S2 case (1 nF @ 1 kV -> 1 mH -> 1 nF bank through an ideal
    rectifier): t1/2 and V_bank."""
    net = s2_net(R); sim = Sim(net, record_events=True, arming=arming)
    K = net.K(0.0); V = np.array([1000.0, 1000.0, 0.0])
    sim.q = K @ V
    ev = sim.event(0.0)
    vb = (sim.alg.solver(sim.kkey(0.0), K, sim.fixed_edges(0.0))[0] @ sim.q)[2]
    t_h = ev["t_quench"].get("D", ev["t_ring"]) * 1e6
    return dict(t_half_us=float(t_h), V_bank=float(vb), E_loss=float(ev["e_ring"] + ev["e_alg"]))


def core_z(cfg_over, dth=1.0):
    cfg = make_config(dict(dict(topology="core", Ca=309.0, Cb=309.0, dth=dth), **cfg_over))
    net = core_net(cfg)
    m = monodromy(net, cfg, settle=3, maxit=10)
    return m["z"], m


def _shuttle_net(P, lx=0.0, eps_stray=0.0, r_lx=2.0):
    """r0.2: the shuttle's own topology (sc.caps_phase: Cx on (7,3) with boss; Cpar on 1-4) with
    the drawn island split Cx3 (7,n17) + Lx3 (n17,3) and Cx4 (n23,8) + Lx4 (2,n23)."""
    net = Net(); net.cur = {}
    for x in ("1", "2", "3", "4", "7", "8", "n17", "n23"):
        net.n(x)
    ix = net.idx
    mp = {(1, 0): (ix["1"], GND), (4, 0): (ix["4"], GND), (2, 0): (ix["2"], GND), (3, 0): (ix["3"], GND),
          (1, 2): (ix["1"], ix["2"]), (3, 4): (ix["3"], ix["4"]), (7, 3): (ix["7"], ix["n17"]),
          (8, 2): (ix["8"], ix["n23"])}
    for key, (i, j) in mp.items():
        net.caps.append((str(key), i, j, (lambda k: (lambda th: net.cur[k]))(key)))
    if eps_stray:
        for x in ("7", "8", "n17", "n23"):
            net.caps.append(("eps" + x, ix[x], GND, eps_stray))
    net.inds += [("Lx3", ix["n17"], ix["3"], lx, r_lx, "lx"), ("Lx4", ix["2"], ix["n23"], lx, r_lx, "lx")]
    return net, mp


def shuttle_parity(P, lx=0.0, oneway=False, iterations=120, burn=60, eps_stray=0.0):
    """K3 / H4 (r0.2): shuttle_core.shuttle_cycle's schedule executed with THIS engine's strokes,
    Schur-complement events and (lx>0) ring path."""
    net, mp = _shuttle_net(P, lx, eps_stray)
    ix = net.idx
    kind = "rect" if oneway else "short"
    al = (0.0, 60.0)
    for nm, a, b, kd in (("RET_A", "2", "0", "short"), ("RET_B", "3", "0", "short"),
                         ("LOAD_A", "1", "7", kind), ("LOAD_B", "4", "8", kind),
                         ("FIRE_A", "7", "3", kind), ("FIRE_B", "8", "2", kind)):
        net.gaps.append((nm, net.n(a), net.n(b), kd, al, "load", {}))
    sim = Sim(net, arming="r02")
    sim.Kof = lambda th: net.K(th)                  # caps are set imperatively: never cache
    sim.kkey = lambda th, _c=[0]: (_c.__setitem__(0, _c[0] + 1) or _c[0])
    sim.cands = lambda th: [sim.gap_by[n] for n in sorted(sim.enabled)
                            if sim.gap_by[n][3] == "rect" and n not in sim.latched]
    sim.enabled = set()
    sim.armed = lambda name, th: name in sim.enabled

    def setcaps(caps):
        for a, b, C in caps:
            net.cur[(a, b)] = C * 1e-12

    def closeto(names):
        sim.enabled = set(names)
        for n in list(sim.cond):
            if n not in names:
                sim.cond.discard(n)
        sim.event(sim.th)

    setcaps(sc.caps_phase("B", P)); sim.th = 0.0
    K = net.K(0.0); V = np.zeros(sim.N); V[ix["1"]] = -1.0; V[ix["4"]] = -1.0; sim.q = K @ V
    ratios = []; pm = 2.0
    for cyc in range(iterations):
        for which, ret, src, isl, snk, ld, fr in (("A", "RET_A", 1, "7", "3", "LOAD_A", "FIRE_A"),
                                                  ("B", "RET_B", 4, "8", "2", "LOAD_B", "FIRE_B")):
            sim.enabled = set(); sim.cond = set()
            capsP = sc.caps_phase(which, P); setcaps(capsP); sim.stroke(sim.th)
            closeto([ret])
            cx_load = P.cx_max - P.load_frac * (P.cx_max - P.cx_min)
            boss = P.pCboss + P.pCboss2
            key = (7, 3) if which == "A" else (8, 2)
            net.cur[key] = (cx_load + boss) * 1e-12; sim.stroke(sim.th)
            closeto([ret, ld])
            fired = False
            for k in range(1, sc.N_COLLAPSE + 1):
                f = k / sc.N_COLLAPSE
                cxk = cx_load + (P.cx_min - cx_load) * f
                sim.enabled = {ret}; sim.cond = {ret}
                net.cur[key] = (cxk + boss) * 1e-12; sim.stroke(sim.th)
                Vn = sim.voltages()
                ov = Vn[ix[isl]] - Vn[ix[snk]]
                if (not fired) and ov > sc._fire_threshold(P, 1.0) * 0 and ov > 0:
                    fired = True
                    closeto([ret, fr])
            sim.enabled = set()
        m = sim.state_mag()
        if cyc >= burn and pm > 1e-15 and m > 1e-15:
            ratios.append(m / pm)
        pm = m
        if m > 1e6 or 0 < m < 1e-6:
            sim.rescale(1.0 / m); pm = 1.0
    return float(np.median(ratios)), sim


def canaries():
    """K1-K4 (brief §6). Fail-closed: the page shows no numbers unless all pass."""
    rows = []
    c = CANARY
    z_ref = dc.solve_doubler4(c["C1MIN"], c["C1MAX"], c["C2MIN"], c["C2MAX"], c["CA"], c["CB"], c["CPAR"])
    z1, _ = core_z(dict(simultaneous=True))
    rows.append(dict(id="K1", check="always-armed galvanic z (engine; solve_doubler4 = %.7f)" % z_ref,
                     expected=K1_Z, got=z1, tol=1e-6, rel=abs(z1 - K1_Z) / K1_Z,
                     extra=dict(solve_doubler4=z_ref)))
    z2, _ = core_z(dict(simultaneous=False))
    rows.append(dict(id="K2", check="station-armed galvanic z (DXF stations)", expected=K2_Z, got=z2,
                     tol=1e-6, rel=abs(z2 - K2_Z) / K2_Z))
    sc.set_device_caps(**CANARY)
    try:
        P = sc.Params(); P.cx_max = 471.0; P.cx_min = 8.0
        z3, _ = shuttle_parity(P, lx=0.0)
    finally:
        sc.reset_device_caps()
    rows.append(dict(id="K3", check="direct island on the shuttle schedule = shuttle_core steady z",
                     expected=K3_Z, got=z3, tol=1e-9, rel=abs(z3 - K3_Z) / K3_Z))
    s2 = s2_ring(2.0)
    r4 = max(abs(s2["t_half_us"] - K4_T) / K4_T, abs(s2["V_bank"] - K4_V) / K4_V)
    rows.append(dict(id="K4", check="S2 ring t1/2 (us) and V_bank (V) at R 2 ohm",
                     expected=[K4_T, K4_V], got=[s2["t_half_us"], s2["V_bank"]], tol=1e-4, rel=r4))
    for r in rows:
        r["pass"] = bool(r["rel"] <= r["tol"])
    return _jsonable(dict(pass_=all(r["pass"] for r in rows), rows=rows,
                          engine=ENGINE_VERSION))


# ======================================================================================
# 9. ON-LOAD SELF-TESTS (fast)
# ======================================================================================
def selftest():
    ok = True; rows = []

    def chk(name, cond):
        nonlocal ok
        rows.append((name, bool(cond))); ok &= bool(cond)
    chk("netlist of record has 43 parts", len(EDGES) == 43)
    chk("DXF SG1/SG3a = shuttle TH_RET/TH_LOAD", abs(DXF["SG1"] - sc.TH_RET * 60) < 1e-9
        and abs(DXF["SG3a"] - sc.TH_LOAD * 60) < 1e-9)
    alg = Alg(2)
    K = np.array([[1e-9, 0.0], [0.0, 1e-9]]); q = K @ np.array([1.0, 0.0])
    chk("two-capacitor paradox loss = 1/4 nJ", abs(event_loss(alg, K, q, [], [(0, 1)]) - 0.25e-9) < 1e-21)
    Vmat, Mq = alg.solver("t", K, [(0, 1)]); V = Vmat @ q
    chk("shorted pair equalises to 0.5 V", abs(V[0] - 0.5) < 1e-12 and abs(V[1] - 0.5) < 1e-12)
    chk("forest flow 0.5 nC", abs((alg.flows([(0, 1)]) @ (Mq @ q - q))[0] - 0.5e-9) < 1e-21)
    S, V, qn, lam, n, _ = lcp(alg, "t2", K, K @ np.array([0.0, 1.0]), [], [(0, 1)])
    chk("rectifier blocks reverse", S == [] and n == 1)
    A = np.array([[0.0, 1.0], [-4.0, -0.1]])
    E = expm(A * 0.7); w, Vv = np.linalg.eig(A)
    Eref = np.real(Vv @ np.diag(np.exp(w * 0.7)) @ np.linalg.inv(Vv))
    chk("expm = eigen-decomposition (2x2)", np.max(np.abs(E - Eref)) < 1e-13)
    chk("expm(0) = I", np.allclose(expm(np.zeros((3, 3))), np.eye(3)))
    cfg = make_config({})
    net = build_net(cfg)
    chk("drawn pump (motor out): 8 gaps, 2 Lx", len(net.gaps) == 8 and len(net.inds) == 2)
    netm = build_net(make_config(dict(motor=True)))
    chk("drawn pump (motor in, per-coil): 24 motor parts",
        sum(1 for d in netm.inds if d[5] == "motor") == 12 and
        sum(1 for c in netm.caps if c[0].startswith(("C_AR", "C__AR", "C_BR"))) == 12)
    if not ok:
        raise AssertionError("pump_engine on-load self-test FAILED: " +
                             ", ".join(n for n, v in rows if not v))
    return dict(pass_=ok, rows=rows)


SELFTEST = selftest()


def api(fn, js="{}"):
    """Worker bridge: JSON string in, JSON string out."""
    a = json.loads(js) if js else {}
    if fn == "evaluate":
        return json.dumps(evaluate(a.get("config"), twins=a.get("twins", True)))
    if fn == "sweep":
        return json.dumps(sweep(a.get("config"), a["key"], a["values"]))
    if fn == "canaries":
        return json.dumps(canaries())
    if fn == "selftest":
        return json.dumps(_jsonable(SELFTEST))
    if fn == "defaults":
        return json.dumps(_jsonable(DEFAULTS))
    raise KeyError(fn)


if __name__ == "__main__":
    import time
    t = time.time(); print(json.dumps(canaries(), indent=1)); print("canaries", time.time() - t)
    t = time.time(); r = evaluate({}); print("z", r["z"], "twins", r.get("twins"), time.time() - t)
