#!/usr/bin/env python3
"""
*** SUPERSEDED by brief r0.2 (sim/island_asdrawn.py, event-driven KCL solver). Kept as the r0.1 record.
*** Do NOT re-run: run() would overwrite the committed (now frozen) spice/ia_*.cir decks. ***
sim/island_asdrawn_r01_spice.py (was sim/island_asdrawn.py) — ISLAND-ASDRAWN Pass A r0.1: is the island sink real on the drawn sheet?
===========================================================================================
Circuit-level (ngspice: KCL + explicit armed gaps) run of the 43-part sheet of record
(`topology_edge_list.csv`, node-exact) to decide whether the series-Lx island transfer raises the
pump's gain over its own Lx->0 twin. Read-only consumer of the frozen cores:

  seq_stat_commutation.deck/run_z/eta_of_z   (the arbiter, H2/R0)
  shuttle_core.profiles/caps_phase/shuttle_run/galvanic_z/Params/set_device_caps   (H4, Cx profile)
  island_resonant_core.integrate/closed_form (model predictions: t1/2, f_rec)
  doubler_core.solve_doubler4                (H5)

Nothing here re-implements a frozen solver; this module only BUILDS decks from the edge list, RUNS
ngspice and does bookkeeping (z = per-cycle peak ratio, the conservation ledger, the peak record).

Tiers: [OC] derivable/standard · [IR] design choice/interpretive reading · [RH] heuristic, never
load-bearing · [ME] method.  Two-ledger discipline: `ledger()` (conservation) and `peaks()` (per-pulse
peak record) are computed from the raw traces independently; no peak quantity enters the ledger.
Firewall: pure EE — KCL, LC, gap switching, varicap work. No substrate physics.
"""
import csv
import math
import os
import re
import subprocess
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
SPICE = os.path.join(ROOT, "spice")
RAW = os.path.join(SPICE, "ia_raw")          # gitignored raw traces
for p in (HERE, ROOT, os.path.join(ROOT, "reference")):
    if p not in sys.path:
        sys.path.insert(0, p)

import shuttle_core as sc                     # frozen; public surface only
import island_resonant_core as irc            # frozen model (predictions)
import doubler_core as dc                     # frozen mirror (H5)
import seq_stat_commutation as ssc            # frozen arbiter (H2/R0)

# ======================================================================================
# 1. LOCKED INPUTS (brief §2) — fixed before any verdict run
# ======================================================================================
RPM = 3000.0                                  # [OC] live default
N_SECTORS = 6                                 # [OC] active sectors / rev
F_CYC = N_SECTORS * RPM / 60.0                # 300 Hz pump cycle (one 60 deg sector)   [OC]
T_CYC = 1.0 / F_CYC
DEG = T_CYC / 60.0                            # seconds per sector-degree

# varicap schedule: the arbiter's tanh re-clocked to real time (brief §2 Values)       [IR lock]
C1MIN_F, C1MAX_F = 16e-12, 280e-12            # 16-280 pF (G3)                            [OC]
TANH_K = 12.0                                 # arbiter steepness (seq_stat_commutation S1)
CA_F = CB_F = 309e-12                         # Ca1 = Cb1                                 [OC]
CPAR_F = 20e-12                               # I6 floor on nodes 1-4 (arbiter deck)      [OC]
# island
CX_MAX_PF = 471.0                             # live default                               [OC]
_P0 = sc.Params()
CX_MIN_PF = _P0.cx_min                        # shuttle cx_min (60 pF)                     [IR, shuttle]
GAP_STRAY_F = _P0.gap_stray * 1e-12           # 2 pF across each gap's own terminals      [IR, shuttle]
BOSS_F = (_P0.pCboss + 6.0) * 1e-12           # pCboss 6 + pCboss2 6 (backstop boss drawn) [IR]
STRAY_REF_PF = (0.0, 5.0, 20.0)               # 7/8/n17/n23 -> reference sweep            [IR]
STRAY_REF_PRIMARY = 5.0                       # primary setting                            [IR]
LX_SET = (0.0, 10e-6, 100e-6, 1e-3)           # 0.0 == Lx->0                               [OC sweep]
LX_DRAWN = 1e-3                               # live default                               [OC]
# motor branches as drawn: 0.64 H series 440 nF, x6 per side                        [OC sheet]
L_MOTOR, C_MOTOR = 0.64, 440e-9
# gaps
GAP_RON = 2.0                                 # conducting gap resistance = S2 design R (Q~729)  [IR]
GAP_ROFF = 1e9
EDGE_S = 0.5e-6                               # arming PWL edge                              [ME]
VE_RECT = 1e-3                                # rectifier softening (V)                       [ME]
R_LX = 20.0                                   # Lx coil ESR = S2/integrator mid-band R (Q~73 at S2).  [IR]
#   The sheet's lossless Lx rings at ~3.6 MHz against the 2 pF load-gap stray for the whole cycle;
#   as drawn (0 ohm) and at 2 ohm the run is not timestep-converged. 20 ohm converges (reltol
#   1e-4 vs 1e-5: dz 0.003, deta 0.001). 0/2 ohm are reported as sensitivities.            [ME]
RELTOL = 1e-4                                 # converged at R_LX=20 (1e-5 twins run in the campaign) [ME]
G0_CX_F = 100e-9                              # >= 100x the largest node cap (~609 pF)       [OC]

# ---- clock: DXF stations, imported from the spice/timing.sub comment line (not re-typed) ----
def dxf_stations():
    txt = open(os.path.join(SPICE, "timing.sub")).read()
    m = re.search(r"DXF stations \(deg, 60deg sector\):\s*(.*)", txt)
    tok = m.group(1).split()
    return {tok[i]: float(tok[i + 1]) for i in range(0, len(tok), 2)}


STATIONS = dxf_stations()
# arming windows [IR lock]: every gap arms AT its DXF station. Rail returns and fire/backstop gaps
# stay armed to the end of their half-sector clearance (WIN_END, after the shuttle collapse end
# 26.4 deg and before the next tanh stroke edge at 30 deg); the load gap disarms at its fire station
# (the island is isolated before the fire -- shuttle "SGxa opens on the plateau", DXF-placed).
WIN_END = 27.0


def windows():
    s = STATIONS
    w = {"SG1": (s["SG1"], WIN_END), "SG3a1": (s["SG3a"], s["SG3b"]),
         "SG3b1": (s["SG3b"], WIN_END), "BS3": (s["BS3"], WIN_END)}
    w.update({"SG2": (s["SG2"], WIN_END + 30.0), "SG4a1": (s["SG4a"], s["SG4b"]),
              "SG4b1": (s["SG4b"], WIN_END + 30.0), "BS4": (s["BS4"], WIN_END + 30.0)})
    return w


WINDOWS = windows()
ISLAND_GAPS = ("SG3b1", "BS3", "SG4b1", "BS4")          # bracketed [IR]
LOAD_GAPS = ("SG3a1", "SG4a1")
RAIL_GAPS = ("SG1", "SG2")

# ---- topology: the sheet, node-exact ------------------------------------------------
MOTOR_PARTS = tuple([f"L_A{i}" for i in range(1, 7)] + [f"C_AR{i}" for i in (1, 2, 3, 5, 6)] +
                    ["C__AR4"] + [f"C_BR{i}" for i in range(1, 7)] + [f"L_B{i}" for i in range(1, 7)])
TANK_PARTS = ("L_R1", "C_R1", "L_R2")


def edge_list():
    rows = []
    for r in csv.reader(open(os.path.join(ROOT, "topology_edge_list.csv"))):
        if not r or r[0].startswith("#") or r[0] == "component":
            continue
        rows.append((r[0], r[1], r[2]))
    return rows


def _n(node, tank):
    """Map sheet nets to SPICE nodes. Collapsed tank: R-A = R-B = reference (0). [IR brief §2]"""
    if node in ("R-A", "R-B"):
        if tank == "collapsed" or node == "R-A":
            return "0"
        return "rb"
    return node.lower().replace("-", "_")


# ======================================================================================
# 2. DECK BUILDER
# ======================================================================================
def s_expr(phase=0.0):
    w = 2 * math.pi * F_CYC
    return f"(0.5*(1+tanh({TANH_K}*sin({w:.9e}*time+{phase:.9f}))))"


def cx_profile_pf(which):
    """(theta_deg grid, Cx pF) one period, sampled from the FROZEN shuttle_core.profiles. [IR]"""
    P = sc.Params(); P.cx_max = CX_MAX_PF
    th = np.round(np.arange(0.0, 60.0 + 1e-9, 0.1), 6)
    k = 2 if which == 3 else 3
    return th, np.array([sc.profiles((t / 60.0) % 1.0, P)[k] for t in th])


def _pwl(th_deg, vals):
    pts = " ".join(f"{t * DEG:.9e} {v:.6g}" for t, v in zip(th_deg, vals))
    return f"PWL({pts}) r=0"


def arm_pwl(on_deg, off_deg):
    t_on, t_off = on_deg * DEG, off_deg * DEG
    pts = [(0.0, 0), (t_on, 0), (t_on + EDGE_S, 1), (t_off, 1), (t_off + EDGE_S, 0), (T_CYC, 0)]
    return "PWL(" + " ".join(f"{t:.9e} {v}" for t, v in pts) + ") r=0"


def write_timing_sub():
    """spice/timing_asdrawn.sub: real arming windows from the DXF (new file; replaces nothing)."""
    L = ["* timing_asdrawn.sub — gap arming from the DXF stations at 3000 rpm (one angle, theta=wt)",
         f"* sector 60 deg = {T_CYC*1e3:.4f} ms (300 Hz). Window rule [IR]: arm AT the DXF station;",
         f"* rail/fire/backstop to {WIN_END} deg (+30 mirror); load gap to its fire station.",
         "* generated by sim/island_asdrawn.py — do not edit by hand.",
         ".subckt timing_asdrawn " + " ".join(f"arm_{g.lower()}" for g in WINDOWS)]
    for g, (a, b) in WINDOWS.items():
        L.append(f"Varm_{g.lower()} arm_{g.lower()} 0 {arm_pwl(a, b)}")
        L.append(f"* {g}: armed {a:.2f}-{b:.2f} deg")
    L.append(".ends timing_asdrawn")
    open(os.path.join(SPICE, "timing_asdrawn.sub"), "w").write("\n".join(L) + "\n")


def write_gap_sub():
    """spice/sparkgap_bidir.sub: bracket (a) sustained bidirectional arc + the one-way armed gap.
    Behavioural conductances (no internal node): ngspice's SW+diode series stalls on the floating
    internal node at every switching event (Timestep too small) -- recorded as a harness finding. [ME]"""
    txt = f"""* sparkgap_bidir.sub — armed gap elements for ISLAND-ASDRAWN (generated by sim/island_asdrawn.py)
* arm = the timing_asdrawn.sub PWL arming node (0 idle / 1 armed, {EDGE_S*1e6:.1f} us edges).
* bracket (a) [IR]: BIDIRECTIONAL, arc SUSTAINED while armed: I = V*(arm/RON + 1/ROFF). A us ring can
*   keep conducting through its current zeros if deionisation is slower than the ring (unmeasured).
* one-way [IR/OC]: armed rectifier I = arm/RON * rect(V) + V/ROFF, rect(V) = (V+sqrt(V^2+VE^2))/2:
*   conducts forward, QUENCHES at current zero (no reverse conduction), re-conducts if forward-biased
*   again while armed. The established rail/load model; bracket (b) for the island gaps (sparkgap.sub
*   behaviour with the strike threshold scaled out). VE = {VE_RECT} V softening << the 100 V seed. [ME]
.subckt sparkgap_bidir a b arm PARAMS: RON={GAP_RON} ROFF={GAP_ROFF:.0e}
  Barc a b I='V(a,b)*(V(arm)/RON + 1/ROFF)'
.ends sparkgap_bidir
.subckt gap_oneway a b arm PARAMS: RON={GAP_RON} ROFF={GAP_ROFF:.0e} VE={VE_RECT}
  Brect a b I='V(arm)/RON*0.5*(V(a,b)+sqrt(V(a,b)*V(a,b)+VE*VE)) + V(a,b)/ROFF'
.ends gap_oneway
"""
    open(os.path.join(SPICE, "sparkgap_bidir.sub"), "w").write(txt)


QSCALE = 1e-9                                 # charge-state scale (F): V(q) = Q / QSCALE        [ME]


def _varicap(nm, a, b, cexpr):
    """Time-varying capacitor as an explicit charge integrator (no ddt Jacobian): the terminal
    current is sensed, integrated on a QSCALE state cap (V(q)=Q/QSCALE), and the terminals see
    V = Q/C(t). i = dQ/dt exactly, so the element is lossless and W_mech = -int 1/2 V^2 dC. [OC/ME]
    (ngspice's `C ... Q=` / B-ddt forms stall at every armed-gap dump: recorded harness finding.)"""
    q, x = f"q_{nm.lower()}", f"x_{nm.lower()}"
    return [f"V_{nm}i {a} {x} 0",
            f"F_{nm}q 0 {q} V_{nm}i 1",
            f"C_{nm}q {q} 0 {QSCALE:.1e}",
            f"B_{nm}v {x} {b} V='V({q})*{QSCALE:.1e}/{cexpr}'"]


class Cfg:
    """One deck. lx: 0.0 => Lx->0. cx: 'profile' (471 pF shuttle profile) | 'big' (G0)."""
    def __init__(self, name, lx=LX_DRAWN, cx="profile", bracket="b", stray_ref=STRAY_REF_PRIMARY,
                 motor=False, tank="collapsed", cpar=CPAR_F, maxstep=1e-6, ncyc=16, gap="ideal",
                 seed=100.0, vstrike=20e3, rlx=None, reltol=None):
        rlx = R_LX if rlx is None else rlx
        reltol = RELTOL if reltol is None else reltol
        self.__dict__.update(dict(name=name, lx=lx, cx=cx, bracket=bracket, stray_ref=stray_ref,
                                  rlx=rlx, reltol=reltol,
                                  motor=motor, tank=tank, cpar=cpar, maxstep=maxstep, ncyc=ncyc,
                                  gap=gap, seed=seed, vstrike=vstrike))


def build(cfg):
    """Return (deck_text, meta). meta lists every energy-bearing element for the ledger."""
    tank = cfg.tank
    caps, varcaps, inds, gaps, lines = [], [], [], [], []
    rows = edge_list()
    used = set()
    for comp, a, b in rows:
        A, B = _n(a, tank), _n(b, tank)
        if comp in MOTOR_PARTS and not cfg.motor:
            continue                                  # R1/G1: 24 motor parts removed (declared)
        if comp in TANK_PARTS and tank == "collapsed":
            continue                                  # tank collapsed (R-A = R-B = ref)
        used.add(comp)
        if comp in ("C1", "C2"):
            ph = 0.0 if comp == "C1" else math.pi
            varcaps.append((comp, B, A, ("tanh", ph)))   # C1: 1 -> R-A ; C2: 4 -> R-B
        elif comp in ("Ca1", "Cb1"):
            caps.append((comp, A, B, CA_F))
        elif comp in ("Cx3", "Cx4"):
            if cfg.cx == "big":
                caps.append((comp, A, B, G0_CX_F))
            else:
                varcaps.append((comp, A, B, ("cx", 3 if comp == "Cx3" else 4)))
            caps.append((comp + "_boss", A, B, BOSS_F))
        elif comp in ("Lx3", "Lx4"):
            inds.append((comp, A, B, cfg.lx))
        elif comp.startswith("L_A") or comp.startswith("L_B"):
            inds.append((comp, A, B, L_MOTOR))
        elif comp.startswith("C_AR") or comp.startswith("C__AR") or comp.startswith("C_BR"):
            caps.append((comp, A, B, C_MOTOR))
        elif comp in ("L_R1", "L_R2"):
            inds.append((comp, A, B, 39.5e-6))           # R3 only: live halves 39.5 uH [OC]
        elif comp == "C_R1":
            caps.append((comp, A, B, 789e-12))
        elif comp in WINDOWS:
            gaps.append((comp, A, B))
            caps.append((comp + "_stray", A, B, GAP_STRAY_F))
        else:
            raise ValueError(f"unmapped sheet part {comp}")
    # declared strays (brief §2)
    for n in ("1", "2", "3", "4"):
        caps.append((f"Cpar{n}", n, "0", cfg.cpar))
    if cfg.stray_ref > 0:
        for n in ("7", "8", "n17", "n23"):
            caps.append((f"Cs_{n}", n, "0", cfg.stray_ref * 1e-12))

    L = [f"* ISLAND-ASDRAWN deck {cfg.name}: lx={cfg.lx} cx={cfg.cx} bracket={cfg.bracket} "
         f"stray_ref={cfg.stray_ref}pF motor={cfg.motor} tank={cfg.tank} gap={cfg.gap}",
         "* generated by sim/island_asdrawn.py from topology_edge_list.csv (node-exact).",
         ".include timing_asdrawn.sub", ".include sparkgap_bidir.sub"]
    if cfg.gap == "spark":
        L += [".include sparkgap.sub", ".include fe_backstop.sub"]
    L.append("Xclk " + " ".join(f"arm_{g.lower()}" for g in WINDOWS) + " timing_asdrawn")
    for nm, a, b, C in caps:
        L.append(f"C_{nm} {a} {b} {C:.6e}")
    for nm, a, b, kind in varcaps:
        vab = f"V({a})" if b == "0" else f"V({a},{b})"
        if kind[0] == "tanh":
            L += _varicap(nm, a, b, f"({C1MIN_F:.4e}+{C1MAX_F - C1MIN_F:.4e}*{s_expr(kind[1])})")
        else:
            th, cx = cx_profile_pf(kind[1])
            L.append(f"V_{nm}c {nm.lower()}c 0 {_pwl(th, cx)}")
            L += _varicap(nm, a, b, f"(1e-12*V({nm.lower()}c))")
    for nm, a, b, Lv in inds:
        if Lv == 0.0:
            L.append(f"V_{nm} {a} {b} 0")             # Lx -> 0 (current sensed)
        elif nm in ("Lx3", "Lx4") and cfg.rlx > 0:
            L.append(f"L_{nm} {a} r_{nm.lower()} {Lv:.6e}")      # coil + its own ESR (same branch)
            L.append(f"R_{nm}esr r_{nm.lower()} {b} {cfg.rlx:.6g}")
        else:
            L.append(f"L_{nm} {a} {b} {Lv:.6e}")
    for g, a, b in gaps:
        sn = f"s_{g.lower()}"
        L.append(f"V_s{g} {a} {sn} 0")                # conduction-current sense
        arm = f"arm_{g.lower()}"
        if cfg.gap == "spark":
            # R4: station arming (behavioural, this module) in series with the FROZEN physics subckts.
            L.append(f"Xarm{g} {sn} m{g.lower()} {arm} sparkgap_bidir")
            if g in ("BS3", "BS4"):
                # FN soft bleed, onset ~0.6*V_strike: exp(-B/V) = e^-10 at 0.6 Vs, 1 mA there [IR]
                bfn = 0.6 * cfg.vstrike * 10.0
                afn = 1e-3 / ((0.6 * cfg.vstrike) ** 2 * math.exp(-10.0))
                L.append(f"X{g} m{g.lower()} {b} fe_backstop PARAMS: AFN={afn:.4e} BFN={bfn:.4e}")
            else:
                L.append(f"X{g} m{g.lower()} {b} sparkgap PARAMS: VSTRIKE={cfg.vstrike:.4e} VARC=30")
        elif g in ISLAND_GAPS and cfg.bracket == "a":
            L.append(f"X{g} {sn} {b} {arm} sparkgap_bidir")
        else:
            L.append(f"X{g} {sn} {b} {arm} gap_oneway")
    nodes = sorted(({x for c in caps + varcaps + inds for x in c[1:3]} |
                    {x for g in gaps for x in g[1:3]}) - {"0"})
    ic = " ".join(f"v({n})={(-cfg.seed if n in ('1', '4') else 0.0)}" for n in nodes)
    for nm, a, b, kind in varcaps:                    # charge state consistent with the seed
        v0 = (-cfg.seed if a in ("1", "4") else 0.0) - (-cfg.seed if b in ("1", "4") else 0.0)
        c0 = float(_c_of_t(kind, np.array([0.0]))[0])
        ic += f" v(q_{nm.lower()})={c0 * v0 / QSCALE:.9g}"
    vecs = ["time"] + [f"v({n})" for n in nodes] + [f"i(v_s{g[0].lower()})" for g in gaps]
    for nm, a, b, Lv in inds:
        vecs.append(f"i(v_{nm.lower()})" if Lv == 0.0 else f"i(l_{nm.lower()})")
    tstop = cfg.ncyc * T_CYC
    L += [f".ic {ic}", ".control", "set filetype=binary",
          f"tran {cfg.maxstep:.2e} {tstop:.6e} uic",
          f"write ia_raw/{cfg.name}.raw " + " ".join(vecs[1:]),
          ".endc",
          f".options reltol={cfg.reltol:.0e} abstol=1e-9 vntol=1e-9 gmin=1e-14 maxstep={cfg.maxstep:.2e} "
          "method=trap itl4=200", ".end"]
    res = [(nm + "esr", nm, cfg.rlx) for nm, a, b, Lv in inds
           if nm in ("Lx3", "Lx4") and Lv > 0 and cfg.rlx > 0]
    meta = dict(caps=caps, varcaps=varcaps, inds=inds, gaps=gaps, nodes=nodes, used=used, res=res)
    return "\n".join(L) + "\n", meta


# ======================================================================================
# 3. RUN + RAW READER
# ======================================================================================
def read_raw(path):
    """ngspice binary raw (single real plot) -> dict name -> array. [ME]"""
    with open(path, "rb") as f:
        data = f.read()
    k = data.index(b"Binary:\n") + len(b"Binary:\n")
    head = data[:k].decode("latin-1").splitlines()
    nv = int([h for h in head if h.startswith("No. Variables")][0].split(":")[1])
    npnt = int([h for h in head if h.startswith("No. Points")][0].split(":")[1])
    i0 = head.index("Variables:")
    names = [head[i0 + 1 + j].split()[1].lower() for j in range(nv)]
    arr = np.frombuffer(data[k:k + 8 * nv * npnt], dtype="<f8").reshape(npnt, nv)
    return {n: arr[:, j].copy() for j, n in enumerate(names)}


def run(cfg, keep_deck=True):
    raise RuntimeError("r0.1 harness is superseded (brief r0.2); re-running would overwrite frozen decks")
    os.makedirs(RAW, exist_ok=True)
    deck, meta = build(cfg)
    cir = f"ia_{cfg.name}.cir"
    open(os.path.join(SPICE, cir), "w").write(deck)
    r = subprocess.run(["ngspice", "-b", cir], capture_output=True, text=True, timeout=3600,
                       cwd=SPICE)
    log = r.stdout + r.stderr
    ok = ("too small" not in log) and ("aborted" not in log.lower())
    rawp = os.path.join(RAW, f"{cfg.name}.raw")
    if not os.path.exists(rawp):
        raise RuntimeError(f"ngspice produced no raw for {cfg.name}:\n{log[-2000:]}")
    return dict(cfg=cfg, meta=meta, d=read_raw(rawp), ok=ok, log=log[-500:])


def run_many(cfgs, procs=4):
    from concurrent.futures import ThreadPoolExecutor
    with ThreadPoolExecutor(procs) as ex:
        return list(ex.map(run, cfgs))


# ======================================================================================
# 4. OBSERVABLES — z, the conservation ledger, the peak record (kept separate)
# ======================================================================================
def z_of(t, v1, v4, T=T_CYC, skip=4):
    """Per-cycle peak of |V1|+|V4|, median of successive ratios — the arbiter's rule (run_z),
    parametrised by the cycle period. Cross-checked against run_z on the arbiter's own trace (H2)."""
    import statistics
    pk = {}
    m = np.abs(v1) + np.abs(v4)
    idx = (t / T).astype(int)
    for c in np.unique(idx):
        pk[int(c)] = float(m[idx == c].max())
    cs = [c for c in sorted(pk) if pk[c] > 1e-12][skip:]
    cs = [c for c in cs if (c + 1) * T <= t[-1] + 1e-12]     # complete cycles only
    if len(cs) < 3:
        return None
    return statistics.median([pk[cs[i + 1]] / pk[cs[i]] for i in range(len(cs) - 1)])


def _v(d, n):
    return np.zeros_like(d["time"]) if n == "0" else d[f"v({n})"]


def _c_of_t(kind, t):
    if kind[0] == "tanh":
        s = 0.5 * (1 + np.tanh(TANH_K * np.sin(2 * math.pi * F_CYC * t + kind[1])))
        return C1MIN_F + (C1MAX_F - C1MIN_F) * s
    th, cx = cx_profile_pf(kind[1])
    return 1e-12 * np.interp(((t % T_CYC) / DEG), th, cx)


def _iL(d, nm, Lv):
    return d[f"i(v_{nm.lower()})"] if Lv == 0.0 else d[f"i(l_{nm.lower()})"]


def _seg(t, t0, t1):
    i0 = int(np.searchsorted(t, t0)); i1 = int(np.searchsorted(t, t1))
    return slice(max(i0, 0), min(i1 + 1, len(t)))


def stored(res, idx=None):
    d, m = res["d"], res["meta"]
    t = d["time"]
    E = np.zeros_like(t)
    for nm, a, b, C in m["caps"]:
        E += 0.5 * C * (_v(d, a) - _v(d, b)) ** 2
    for nm, a, b, kind in m["varcaps"]:
        E += 0.5 * _c_of_t(kind, t) * (_v(d, a) - _v(d, b)) ** 2
    for nm, a, b, Lv in m["inds"]:
        if Lv > 0:
            E += 0.5 * Lv * _iL(d, nm, Lv) ** 2
    return E


def ledger(res, cyc, perturb_gap=0.0):
    """Conservation ledger over steady cycle `cyc` [t_k, t_k+T]:
    W_mech = -sum_varicaps integral 1/2 V^2 dC (constant-charge definition, energy-balance-findings)
    dE_stored = sum 1/2 C V^2 + 1/2 L I^2 over EVERY element;  E_diss = integral v*i over every gap
    (switch + diode, incl. roff leakage). residual = |W - dE - E_diss| / E_diss. [OC]"""
    d, m = res["d"], res["meta"]
    t = d["time"]
    s = _seg(t, cyc * T_CYC, (cyc + 1) * T_CYC)
    tt = t[s]
    W = 0.0; Wpart = {}
    for nm, a, b, kind in m["varcaps"]:
        v = (_v(d, a) - _v(d, b))[s]
        C = _c_of_t(kind, tt)
        w = float(-np.sum(0.25 * (v[1:] ** 2 + v[:-1] ** 2) * np.diff(C)))
        Wpart[nm] = w; W += w
    E = stored(res)[s]
    dE = float(E[-1] - E[0])
    diss = {}
    for g, a, b in m["gaps"]:
        p = (_v(d, a) - _v(d, b))[s] * d[f"i(v_s{g.lower()})"][s]
        diss[g] = float(np.trapezoid(p, tt)) if hasattr(np, "trapezoid") else float(np.trapz(p, tt))
    Eg = sum(diss.values())
    for rn, ln, R in m.get("res", []):
        diss[rn] = _trap(R * d[f"i(l_{ln.lower()})"][s] ** 2, tt)
    Ed = sum(diss.values()) + perturb_gap * Eg          # +5% trip on the GAP term alone
    # residual normalised by the GAP term (<= E_diss, so the closure test is the stricter one; the
    # +5 % gap trip then reads ~5 % whatever share the coil ESR takes). resid_Ediss also reported.
    resid = abs(W - dE - Ed) / max(abs(Eg), 1e-300)
    resid_ed = abs(W - dE - Ed) / max(abs(Ed), 1e-300)
    return dict(W=W, Wpart=Wpart, dE=dE, E_diss=Ed, E_gap=Eg, diss=diss, resid=resid,
                resid_Ediss=resid_ed,
                eta=dE / W if W else float("nan"), E0=float(E[0]))


def _trap(y, x):
    return float(np.trapezoid(y, x)) if hasattr(np, "trapezoid") else float(np.trapz(y, x))


def win_t(cyc, a_deg, b_deg):
    return cyc * T_CYC + a_deg * DEG, cyc * T_CYC + b_deg * DEG


def peaks(res, cyc):
    """Per-pulse PEAK record (separate from the ledger): i_pk, V_pk per gap in cycle `cyc`, and
    the load-stroke t1/2 (SG3a1 conduction start -> first current zero)."""
    d, m = res["d"], res["meta"]
    t = d["time"]
    s = _seg(t, cyc * T_CYC, (cyc + 1) * T_CYC)
    out = {}
    for g, a, b in m["gaps"]:
        i = d[f"i(v_s{g.lower()})"][s]; v = (_v(d, a) - _v(d, b))[s]
        out[g] = dict(i_pk=float(np.max(np.abs(i))), V_pk=float(np.max(np.abs(v))))
    for g in LOAD_GAPS:
        w0, w1 = WINDOWS[g]
        ss = _seg(t, *win_t(cyc, w0, w1))
        tt, i = t[ss], d[f"i(v_s{g.lower()})"][ss]
        ip = np.max(np.abs(i)) if len(i) else 0.0
        th = None
        if ip > 0:
            on = np.where(np.abs(i) > 0.01 * ip)[0]
            if len(on):
                k0 = on[0]; kp = int(np.argmax(np.abs(i)))
                after = np.where(np.abs(i[kp:]) < 1e-3 * ip)[0]
                if len(after):
                    th = float(tt[kp + after[0]] - tt[k0])
        out[g]["t_half"] = th
    return out


# ======================================================================================
# 5. ON-LOAD SELF-TESTS (fast, no ngspice)
# ======================================================================================
def _selftest():
    ok = True
    # stations parsed from timing.sub equal geom_stations.csv freeze intent (DXF)
    g = {r["station"]: r for r in csv.DictReader(open(os.path.join(ROOT, "geom_stations.csv")))}
    for k, v in STATIONS.items():
        ref = g[k]["freeze_intent_deg"] or g[k]["drawn_angle_deg"]
        ok &= abs(float(ref) - v) < 0.06
    # windows ordered, inside their half, load disarms at fire
    for gname, (a, b) in WINDOWS.items():
        ok &= a < b and (b <= 30.0 if a < 30 else b <= 60.0)
    ok &= WINDOWS["SG3a1"][1] == WINDOWS["SG3b1"][0]
    # edge list is the 43-part sheet
    ok &= len(edge_list()) == 43
    # Cx profile reproduces the frozen shuttle profile plateau/collapse extremes
    th, cx = cx_profile_pf(3)
    ok &= abs(cx.max() - CX_MAX_PF) < 1e-9 and abs(cx.min() - CX_MIN_PF) < 1e-9
    # motor branch resonance = 299.9 Hz (brief B2 value)
    ok &= abs(1 / (2 * math.pi * math.sqrt(L_MOTOR * C_MOTOR)) - 299.9) < 0.1
    # z_of on a synthetic geometric series returns the ratio exactly
    tt = np.linspace(0, 10 * T_CYC, 10001)[:-1]
    ok &= abs(z_of(tt, 1.3 ** (tt / T_CYC).astype(int) * 1.0, 0 * tt) - 1.3) < 1e-12
    if not ok:
        raise AssertionError("island_asdrawn on-load self-test FAILED")
    return ok


SELFTEST_OK = _selftest()


# ======================================================================================
# 6. HARNESS GATES H1-H7 (brief §4). Any failure => HARNESS-FAIL, no verdict.
# ======================================================================================
S2_PUB = {2.0: (2.22155, 998.89051), 20.0: (2.22155, 989.01498), 100.0: (2.22289, 947.40603)}
S2_TOL = 0.612          # % — the published max S2 delta (ngspice_vs_python.csv, "0.61 %")    [OC]


def h1_s2():
    """H1: S2 ring C_src 1n -> Lx 1m -> gap (this module's one-way element, R = gap RON) -> C_bank 1n.
    Reproduce the published t1/2 and V_bank(6 us) within 0.612 %."""
    rows = []
    for R, (th_pub, vb_pub) in S2_PUB.items():
        name = f"ia_h1_R{int(R)}"
        deck = f"""* H1 S2 reproduction through the ISLAND-ASDRAWN one-way gap element (R = RON)
.include sparkgap_bidir.sub
Varm arm 0 1
Csrc src 0 1n ic=1000
Cbank bnk 0 1n ic=0
Lx src a 1m
Xg a bnk arm gap_oneway PARAMS: RON={R}
.control
tran 0.5n 8u uic
meas tran thalf WHEN i(Lx)=0 CROSS=1
meas tran vbank FIND v(bnk) AT=6u
.endc
.options reltol=1e-6
.end
"""
        open(os.path.join(SPICE, name + ".cir"), "w").write(deck)
        out = subprocess.run(["ngspice", "-b", name + ".cir"], capture_output=True, text=True,
                             cwd=SPICE).stdout
        th = float(re.search(r"thalf\s*=\s*([-\d.eE+]+)", out).group(1)) * 1e6
        vb = float(re.search(r"vbank\s*=\s*([-\d.eE+]+)", out).group(1))
        cf = irc.closed_form(1e-9, 1e-9, 1000.0, 1e-3, R)
        d_t = abs(th - th_pub) / th_pub * 100; d_v = abs(vb - vb_pub) / vb_pub * 100
        rows.append(dict(R=R, t_half_us=th, t_pub=th_pub, dt_pct=d_t, V_bank=vb, V_pub=vb_pub,
                         dv_pct=d_v, cf_t_half_us=cf["t_half"] * 1e6,
                         ok=d_t <= S2_TOL and d_v <= S2_TOL))
    return all(r["ok"] for r in rows), rows


def h2_arbiter(ms=2e-7):
    """H2: seq_stat_commutation imported unchanged: all-direct z 1.39, forward-resonant z ~1.39 at
    Lx 10 uH. Also cross-checks this module's z_of() against run_z on the arbiter's own trace."""
    zd, cd = ssc.run_z(ssc.deck("diode", name="ia_h2_direct"), "ia_h2_direct.cir")
    zr, cr = ssc.run_z(ssc.deck("reson", lxfwd=1e-5, ms=ms, name="ia_h2_reson"), "ia_h2_reson.cir")
    rows = [[float(x) for x in l.split()] for l in open(os.path.join(SPICE, "ia_h2_direct.dat"))
            if len(l.split()) >= 4]
    a = np.array(rows)
    zmine = z_of(a[:, 0], a[:, 1], a[:, 3], T=1e-3, skip=4)
    ok = abs(zd - 1.39) <= 0.03 and abs(zr - 1.39) <= 0.03 and abs(zmine - zd) < 1e-4   # z_of drops the incomplete last cycle
    return ok, dict(z_direct=zd, z_reson_10uH=zr, z_of_crosscheck=zmine, conv=(cd, cr))


def shuttle_ratio():
    """z_shuttle(471 pF)/z_shuttle(galvanic) from the FROZEN shuttle at the G3 device caps (its
    public set_device_caps hook; reset afterwards). Boss strays as in the drawn deck."""
    sc.set_device_caps(C1MIN=16, C1MAX=280, C2MIN=16, C2MAX=280, CA=309, CB=309, CPAR=20)
    try:
        P = sc.Params(); P.cx_max = CX_MAX_PF; P.pCboss2 = 6.0
        z_sh = sc.shuttle_run(P)[0]; z_g = sc.galvanic_z()
    finally:
        sc.reset_device_caps()
    return z_sh, z_g, z_sh / z_g


def z_energy(res, c0=6):
    """Energy-growth cross-check: sqrt(E(k+1)/E(k)) at cycle boundaries, median. [ME]"""
    d = res["d"]; t = d["time"]; E = stored(res)
    kmax = int(t[-1] / T_CYC)
    Ek = [E[min(np.searchsorted(t, k * T_CYC), len(t) - 1)] for k in range(c0, kmax + 1)]
    r = [math.sqrt(Ek[i + 1] / Ek[i]) for i in range(len(Ek) - 1) if Ek[i] > 0]
    return float(np.median(r)) if r else None


def _dq_cap(d, C, a, b, sl):
    """Charge change on a cap from terminal a's side over window slice sl (indices i0,i1)."""
    va = _v(d, a); vb = _v(d, b)
    return C * ((va[sl[1]] - vb[sl[1]]) - (va[sl[0]] - vb[sl[0]]))


def _win_idx(t, t0, t1):
    return (min(int(np.searchsorted(t, t0)), len(t) - 1),
            min(int(np.searchsorted(t, t1)), len(t) - 1))


def acyc(res, want=9):
    """Analysis cycle: `want`, or the last complete cycle if the run aborted earlier."""
    return min(want, int(res["d"]["time"][-1] / T_CYC + 1e-9) - 1)


def node_partners(res, node, cyc, w0, w1, exclude):
    """Charge INTO each element attached to `node` (from the node's side) over [w0,w1] deg of cycle
    `cyc`, excluding the named elements. Caps via C*dV (exact); gaps/inductors via integral i. [OC]"""
    d, m = res["d"], res["meta"]; t = d["time"]
    i0, i1 = _win_idx(t, *win_t(cyc, w0, w1)); tt = t[i0:i1 + 1]
    out = {}
    for nm, a, b, C in m["caps"]:
        base = nm.replace("_stray", "").replace("_boss", "")
        if node not in (a, b) or base in exclude:
            continue
        other = b if a == node else a
        out[nm] = _dq_cap(d, C, node, other, (i0, i1))
    for nm, a, b, kind in m["varcaps"]:
        if node in (a, b) and nm not in exclude:
            other = b if a == node else a
            C = _c_of_t(kind, t)
            va, vb = _v(d, node), _v(d, other)
            out[nm] = C[i1] * (va[i1] - vb[i1]) - C[i0] * (va[i0] - vb[i0])
    for g, a, b in m["gaps"]:
        if node in (a, b) and g not in exclude:
            i = d[f"i(v_s{g.lower()})"][i0:i1 + 1]
            out[g] = _trap(i, tt) * (1 if a == node else -1)
    for nm, a, b, Lv in m["inds"]:
        if node in (a, b) and nm not in exclude:
            i = _iL(d, nm, Lv)[i0:i1 + 1]
            out[nm] = _trap(i, tt) * (1 if a == node else -1)
    return out


def t1_premise(res, cyc):
    """T1: load-stroke charge ledger at node 3 (share landing on C_BR1-6) + node-4 downstream split
    + load t1/2 vs the integrator closed form (471 pF / 2.64 uF / Lx)."""
    d = res["d"]; t = d["time"]
    w0, w1 = WINDOWS["SG3a1"]
    i0, i1 = _win_idx(t, *win_t(cyc, w0, w1))
    q_lx = _trap(_iL(d, "Lx3", res["cfg"].lx)[i0:i1 + 1], t[i0:i1 + 1])   # into node 3
    p3 = node_partners(res, "3", cyc, w0, w1, exclude={"Lx3"})
    q_cbr = sum(v for k, v in p3.items() if k.startswith("C_BR"))
    groups3 = {"Cb1": p3.get("Cb1", 0.0), "C_BR1-6 (motor bank)": q_cbr,
               "Cpar3": p3.get("Cpar3", 0.0),
               "SG2 (+stray)": p3.get("SG2", 0.0) + p3.get("SG2_stray", 0.0),
               "SG3b1/BS3 (+strays, island gaps)": sum(p3.get(k, 0.0) for k in
                                                        ("SG3b1", "SG3b1_stray", "BS3", "BS3_stray"))}
    p4 = node_partners(res, "4", cyc, w0, w1, exclude={"Cb1"})
    groups4 = {"C2 (-> ref -> C1 chain)": p4.get("C2", 0.0), "Cpar4": p4.get("Cpar4", 0.0),
               "SG4a1 (+stray) -> mirror island/Ca1": p4.get("SG4a1", 0.0) + p4.get("SG4a1_stray", 0.0),
               "L_B1-6 (motor return)": sum(v for k, v in p4.items() if k.startswith("L_B"))}
    kcl3 = abs(q_lx - sum(p3.values())) / max(abs(q_lx), 1e-300)
    # the load STROKE proper: SG3a1 conduction start -> quench (+ one stroke of margin); the window
    # figures above also carry the motor branch's own 300 Hz current over the 490 us window.
    ig = d["i(v_ssg3a1)"][i0:i1 + 1]; tt = t[i0:i1 + 1]
    ip = np.max(np.abs(ig)); on = np.where(np.abs(ig) > 0.01 * ip)[0]
    kp = int(np.argmax(np.abs(ig))); off = np.where(np.abs(ig[kp:]) < 1e-3 * ip)[0]
    ts0 = tt[on[0]]; ts1 = tt[kp + off[0]] if len(off) else tt[-1]
    ts1 = ts1 + (ts1 - ts0)
    a0, a1 = (ts0 - cyc * T_CYC) / DEG, (ts1 - cyc * T_CYC) / DEG
    j0, j1 = _win_idx(t, ts0, ts1)
    q_lx_s = _trap(_iL(d, "Lx3", res["cfg"].lx)[j0:j1 + 1], t[j0:j1 + 1])
    p3s = node_partners(res, "3", cyc, a0, a1, exclude={"Lx3"})
    q_cbr_s = sum(v for k, v in p3s.items() if k.startswith("C_BR"))
    stroke3 = {"Cb1": p3s.get("Cb1", 0.0), "C_BR1-6 (motor bank)": q_cbr_s,
               "Cpar3": p3s.get("Cpar3", 0.0),
               "SG2 (+stray)": p3s.get("SG2", 0.0) + p3s.get("SG2_stray", 0.0),
               "SG3b1/BS3 (+strays)": sum(p3s.get(k, 0.0) for k in
                                          ("SG3b1", "SG3b1_stray", "BS3", "BS3_stray"))}
    p4s = node_partners(res, "4", cyc, a0, a1, exclude={"Cb1"})
    stroke4 = {"C2 (-> ref -> C1 chain)": p4s.get("C2", 0.0), "Cpar4": p4s.get("Cpar4", 0.0),
               "SG4a1 (+stray) -> mirror island/Ca1": p4s.get("SG4a1", 0.0) + p4s.get("SG4a1_stray", 0.0),
               "L_B1-6 (motor return)": sum(v for k, v in p4s.items() if k.startswith("L_B"))}
    pk = peaks(res, cyc)["SG3a1"]
    cf = irc.closed_form(CX_MAX_PF * 1e-12, 6 * C_MOTOR + CB_F, 1.0, max(res["cfg"].lx, 1e-30),
                         max(res["cfg"].rlx, 1e-9))
    share_w = q_cbr / q_lx if q_lx else float("nan")
    share = q_cbr_s / q_lx_s if q_lx_s else float("nan")
    verdict = ("PREMISE-HOLDS" if share >= 0.95 else "PREMISE-FAILS" if share < 0.05
               else "PREMISE-PARTIAL")
    return dict(q_lx_stroke=q_lx_s, share_CBR=share, stroke_deg=(a0, a1), stroke_node3=stroke3,
                stroke_node4=stroke4, q_lx_window=q_lx, share_CBR_window=share_w,
                node3=groups3, node4=groups4, kcl3_resid=kcl3,
                t_half_meas=pk["t_half"], t_half_model=cf["t_half"], premise=verdict)


def h7_kcl_fire(res, cyc):
    """H7: during the SG3b1 fire window, net charge into node 3's OTHER elements (all but Lx3/SG3b1/
    BS3; island-gap strays belong to their gap) must equal the charge change on the strays linking
    S={7,n17} to nodes outside {7,n17,3} (incl. the SG3a1 path), within 1 %."""
    d, m = res["d"], res["meta"]; t = d["time"]
    w0, w1 = WINDOWS["SG3b1"]
    i0, i1 = _win_idx(t, *win_t(cyc, w0, w1)); tt = t[i0:i1 + 1]
    lhs = sum(node_partners(res, "3", cyc, w0, w1, exclude={"Lx3", "SG3b1", "BS3"}).values())
    q_out = 0.0                                               # charge leaving S to the outside
    for nm, a, b, C in m["caps"]:
        ends = {a, b}
        inS = ends & {"7", "n17"}
        if inS and not (ends <= {"7", "n17", "3"}):
            sn = next(iter(inS)); other = b if a == sn else a
            q_out += _dq_cap(d, C, sn, other, (i0, i1))
    q_out -= _trap(d["i(v_ssg3a1)"][i0:i1 + 1], tt)          # SG3a1 current flows 1 -> 7 (into S)
    rhs = -q_out
    q_circ = _trap(np.abs(d["i(v_ssg3b1)"][i0:i1 + 1]) + np.abs(d["i(v_sbs3)"][i0:i1 + 1]), tt)
    err = abs(lhs - rhs) / max(abs(lhs), abs(rhs), 1e-300)
    return dict(lhs_q_node3=lhs, rhs_q_strays=rhs, q_circ_fire=q_circ, rel_err=err,
                ok=err <= 0.01, bypass_ratio=abs(lhs) / max(q_circ, 1e-300),
                loop_bypassed=abs(lhs) / max(q_circ, 1e-300) < 0.05)


# ======================================================================================
# 7. CAMPAIGN (brief §4 strict order) + verdict (brief §6, pre-committed)
# ======================================================================================
LEDGER_CYCLES = (8, 9, 10, 11)
MODEL_ETA = {"G0": 0.386, "G1": 0.302, "R1": 0.50}           # efficiency-resolution / model
F_REC_MODEL = 0.91                                            # integrator claim (brief §6)
PREDICTION = dict(premise="PREMISE-FAILS", fire="LOOP-BYPASSED",
                  arbiter_a="SINK-IS-PUMP", arbiter_b="SINK-IS-PUMP or REVERSAL-ONLY")


def summarize(res):
    d = res["d"]; t = d["time"]; c = res["cfg"]
    ncomp = int(t[-1] / T_CYC + 1e-9)
    cyc = [k for k in LEDGER_CYCLES if k + 1 <= ncomp] or [k for k in range(5, ncomp)][-3:]
    leds = [ledger(res, k) for k in cyc]
    trip = [ledger(res, k, perturb_gap=0.05) for k in cyc]
    eta = float(np.mean([L["eta"] for L in leds]))
    row = dict(name=c.name, lx=c.lx, cx=c.cx, bracket=c.bracket, stray_ref_pF=c.stray_ref,
               motor=c.motor, cpar_pF=c.cpar * 1e12, rlx=c.rlx, reltol=c.reltol, maxstep=c.maxstep,
               completed_cycles=ncomp, ngspice_clean=res["ok"],
               z=z_of(t, d["v(1)"], d["v(4)"]), z_energy=z_energy(res),
               eta=eta, eta_spread=float(np.ptp([L["eta"] for L in leds])),
               resid_max=max(L["resid"] for L in leds), trip_min=min(L["resid"] for L in trip),
               ledger_cycles=cyc)
    L0 = leds[0]
    row["W_mech"] = L0["W"]
    row["T_load_frac"] = float(np.mean([(L["diss"].get("SG3a1", 0) + L["diss"].get("SG4a1", 0)) / L["W"]
                                        for L in leds]))
    row["T_fire_frac"] = float(np.mean([sum(L["diss"].get(g, 0) for g in ISLAND_GAPS) / L["W"]
                                        for L in leds]))
    row["T_rail_frac"] = float(np.mean([sum(L["diss"].get(g, 0) for g in RAIL_GAPS) / L["W"]
                                        for L in leds]))
    row["T_esr_frac"] = float(np.mean([sum(v for k, v in L["diss"].items() if k.endswith("esr")) / L["W"]
                                       for L in leds]))
    res["leds"] = leds
    return row


def base(name, **kw):
    kw.setdefault("ncyc", 13)
    return Cfg(name, **kw)


def plan():
    P = {}
    for br in "ab":
        P[f"G0{br}"] = base(f"G0{br}", lx=0.0, cx="big", bracket=br)
        P[f"G1{br}"] = base(f"G1{br}", lx=0.0, bracket=br)
        P[f"G1{br}_ms05"] = base(f"G1{br}_ms05", lx=0.0, bracket=br, maxstep=0.5e-6)
        P[f"R1{br}"] = base(f"R1{br}", lx=LX_DRAWN, bracket=br)
        P[f"R1{br}_rel5"] = base(f"R1{br}_rel5", lx=LX_DRAWN, bracket=br, reltol=1e-5)
        for lx, tag in ((10e-6, "L10u"), (100e-6, "L100u")):
            P[f"{tag}{br}"] = base(f"{tag}{br}", lx=lx, bracket=br)
        for sr in (0.0, 20.0):
            P[f"G1{br}_s{int(sr)}"] = base(f"G1{br}_s{int(sr)}", lx=0.0, bracket=br, stray_ref=sr)
            P[f"R1{br}_s{int(sr)}"] = base(f"R1{br}_s{int(sr)}", lx=LX_DRAWN, bracket=br, stray_ref=sr)
        P[f"R2{br}"] = base(f"R2{br}", lx=LX_DRAWN, bracket=br, motor=True)
        P[f"G1m{br}"] = base(f"G1m{br}", lx=0.0, bracket=br, motor=True)
        P[f"R1{br}_esr2"] = base(f"R1{br}_esr2", lx=LX_DRAWN, bracket=br, rlx=2.0)
        P[f"R1{br}_esr0"] = base(f"R1{br}_esr0", lx=LX_DRAWN, bracket=br, rlx=0.0)
    P["G0a_cpar10"] = base("G0a_cpar10", lx=0.0, cx="big", bracket="a", cpar=10e-12)
    return P


def verdict(rows, h_ok):
    if not h_ok:
        return "HARNESS-FAIL", {}
    out = {}
    for br in "ab":
        g0, g1, r1 = rows[f"G0{br}"], rows[f"G1{br}"], rows[f"R1{br}"]
        g1b = rows[f"G1{br}_ms05"]
        dz = max(0.03, 3 * abs(g1["z"] - g1b["z"]))
        de = max(0.03, 3 * abs(g1["eta"] - g1b["eta"]))
        f_rec = (r1["eta"] - g1["eta"]) / g1["T_load_frac"] if g1["T_load_frac"] > 0 else float("nan")
        if r1["z"] < g1["z"] - dz or r1["z"] <= 1:
            v = "PUMP-BREAKS"
        elif f_rec >= 0.86 and r1["z"] > g1["z"] + dz:
            v = "SINK-REALIZED"
        elif r1["eta"] > g0["eta"]:
            v = "SINK-PARTIAL"
        elif g1["eta"] + de < r1["eta"] <= g0["eta"]:
            v = "SINK-SUBTHRESHOLD"
        elif abs(r1["eta"] - g1["eta"]) <= de and abs(r1["z"] - g1["z"]) <= dz:
            v = "SINK-IS-PUMP"
        else:
            v = "UNCLASSIFIED"
        out[br] = dict(verdict=v, f_rec_meas=f_rec, dz=dz, deta=de, z_R1=r1["z"], z_G1=g1["z"],
                       z_G0=g0["z"], eta_R1=r1["eta"], eta_G1=g1["eta"], eta_G0=g0["eta"])
    va, vb = out["a"]["verdict"], out["b"]["verdict"]
    gain_a = va in ("SINK-REALIZED", "SINK-PARTIAL", "SINK-SUBTHRESHOLD")
    gain_b = vb in ("SINK-REALIZED", "SINK-PARTIAL", "SINK-SUBTHRESHOLD")
    if gain_b and not gain_a:
        final = "REVERSAL-ONLY"
    elif va == vb:
        final = va
    elif gain_a and gain_b:                        # both gain, different strength: the weaker governs
        order = ["SINK-SUBTHRESHOLD", "SINK-PARTIAL", "SINK-REALIZED"]
        final = min(va, vb, key=order.index)
    else:
        final = f"{va} (a) / {vb} (b)"
    return final, out


FROZEN_A = ["shuttle_core.py", "reference/", "sim/seq_stat_commutation.py", "sim/design_synth.py",
            "tools/", "index.html", "docs/kicad/", "topology_edge_list.csv"]


def frozen_diff(base="f9c9efa"):
    """Empty-diff assertion (brief §0): frozen paths + every EXISTING spice/*.sub|*.cir vs base."""
    old = subprocess.run(["git", "ls-tree", "-r", "--name-only", base, "spice/"], cwd=ROOT,
                         capture_output=True, text=True).stdout.split()
    paths = FROZEN_A + [p for p in old if p.endswith((".sub", ".cir"))]
    r = subprocess.run(["git", "diff", "--stat", base, "--"] + paths, cwd=ROOT,
                       capture_output=True, text=True)
    u = subprocess.run(["git", "status", "--porcelain", "--"] + paths, cwd=ROOT,
                       capture_output=True, text=True)
    return (r.stdout.strip() == "" and u.stdout.strip() == ""), r.stdout + u.stdout


def load(key, cfg):
    return dict(cfg=cfg, meta=build(cfg)[1], d=read_raw(os.path.join(RAW, f"{cfg.name}.raw")), ok=True)


def twin(cfg, reltol=1e-5):
    kw = {k: getattr(cfg, k) for k in ("lx", "cx", "bracket", "stray_ref", "motor", "tank", "cpar",
                                         "maxstep", "ncyc", "rlx")}
    return Cfg(cfg.name + "_rel5", reltol=reltol, **kw)


def report(write=True):
    """Re-derive every observable from the stored raw traces; evaluate H1-H7, the checks and the
    pre-committed verdict; write the CSVs/PNG. Runs are produced by `campaign()`."""
    P = plan()
    for k in ("G0a", "G0b", "G0a_cpar10", "G1a", "G1b", "R2a", "R2b", "G1ma", "G1mb"):
        P[k + "_rel5"] = twin(P[k])
    keep = {"G1a", "R1a", "R1b", "R2a_rel5", "R2b"}
    rows, res = {}, {}
    for k, c in P.items():
        if not os.path.exists(os.path.join(RAW, f"{c.name}.raw")):
            continue
        r = load(k, c); rows[k] = summarize(r)
        if k in keep:
            res[k] = r
        else:
            res[k] = dict(leds=r["leds"])        # ledger rows only; the trace is released
    for k in keep:
        c = acyc(res[k])
        rows[k]["h7"] = h7_kcl_fire(res[k], c)
    # ---- gates
    H = {}
    ok1, h1 = h1_s2(); H["H1"] = (ok1, h1)
    ok2, h2 = h2_arbiter(); H["H2"] = (ok2, h2)
    zarb = h2["z_direct"]
    g0 = {br: rows[f"G0{br}_rel5"] for br in "ab"}
    H["H3"] = (all(abs(g0[br]["z"] - zarb) <= 0.03 for br in "ab"),
               {br: g0[br]["z"] for br in "ab"} | {"z_arbiter": zarb})
    zsh, zg, rsh = shuttle_ratio()
    r41 = {br: rows[f"G1{br}"]["z"] / rows[f"G0{br}"]["z"] for br in "ab"}
    H["H4"] = (all(abs(r41[br] - rsh) <= 0.03 for br in "ab"),
               dict(zG1_over_zG0=r41, z_shuttle471=zsh, z_shuttle_galv=zg, shuttle_ratio=rsh))
    dz_pred = dc.solve_doubler4(16, 280, 16, 280, 309, 309, 10) - dc.solve_doubler4(16, 280, 16, 280, 309, 309, 20)
    dz_meas = rows["G0a_cpar10_rel5"]["z"] - rows["G0a_rel5"]["z"]
    H["H5"] = (abs(dz_meas - dz_pred) <= 0.03, dict(dz_meas=dz_meas, dz_pred=dz_pred))
    h6 = {k: (rows[k]["resid_max"], rows[k]["trip_min"]) for k in
          ("G0a_rel5", "G0b_rel5", "G1a", "G1b", "R1a", "R1b")}
    H["H6"] = (all(v[0] < 0.01 and v[1] > 0.04 for v in h6.values()), h6)
    h7 = {k: rows[k]["h7"] for k in ("R1a", "R1b", "R2a_rel5", "R2b")}
    H["H7"] = (all(v["ok"] for v in h7.values()), h7)
    h_ok = all(v[0] for v in H.values())
    final, per = verdict(rows, h_ok)
    # ---- modifiers
    mot = {}
    for br in "ab":
        r2, g1m = rows[f"R2{br}_rel5"], rows[f"G1m{br}_rel5"]
        mot[br] = dict(z_R2=r2["z"], z_G1m=g1m["z"], eta_R2=r2["eta"], eta_G1m=g1m["eta"],
                       dz_R2_G1m=r2["z"] - g1m["z"], dz_R1_G1=per[br]["z_R1"] - per[br]["z_G1"])
    motor_dep = any(abs(m["dz_R2_G1m"] - m["dz_R1_G1"]) > per[br]["dz"] for br, m in mot.items())
    t1 = {k: t1_premise(res[k], acyc(res[k])) for k in ("R2a_rel5", "R2b", "R1a", "R1b")}
    pk = {k: peaks(res[k], acyc(res[k])) for k in ("G1a", "R1a", "R1b", "R2a_rel5", "R2b")}
    out = dict(rows=rows, H=H, h_ok=h_ok, verdict=final, per=per, motor=mot,
               motor_dependent=motor_dep, t1=t1, peaks=pk, frozen=frozen_diff(), res=res)
    if write:
        _write_outputs(out)
    return out


def _write_outputs(o):
    rows = o["rows"]
    cols = ["name", "lx", "cx", "bracket", "stray_ref_pF", "motor", "cpar_pF", "rlx", "reltol", "maxstep",
            "completed_cycles", "z", "z_energy", "eta", "eta_spread", "resid_max", "trip_min",
            "T_load_frac", "T_fire_frac", "T_rail_frac", "T_esr_frac"]
    with open(os.path.join(ROOT, "island_asdrawn_r01_runs.csv"), "w", newline="") as f:
        w = csv.writer(f); w.writerow(cols)
        for k, r in rows.items():
            w.writerow([r[c] if not isinstance(r[c], float) else f"{r[c]:.6g}" for c in cols])
        f.write(f"#verdict,{o['verdict']}\n")
    with open(os.path.join(ROOT, "island_asdrawn_r01_t1.csv"), "w", newline="") as f:
        w = csv.writer(f); w.writerow(["run", "scope", "node", "partner", "charge_C", "share_of_Lx3"])
        for k, t in o["t1"].items():
            for scope, n3, n4, q in (("stroke", t["stroke_node3"], t["stroke_node4"], t["q_lx_stroke"]),
                                     ("load_window", t["node3"], t["node4"], t["q_lx_window"])):
                w.writerow([k, scope, "3", "Lx3 (in)", f"{q:.6e}", "1"])
                for nm, v in n3.items():
                    w.writerow([k, scope, "3", nm, f"{v:.6e}", f"{v / q:.4f}"])
                for nm, v in n4.items():
                    w.writerow([k, scope, "4", nm, f"{v:.6e}", f"{v / q:.4f}"])
            w.writerow([k, "t_half", "", "measured_us", f"{t['t_half_meas']*1e6:.4f}", ""])
            w.writerow([k, "t_half", "", "model_closed_form_us", f"{t['t_half_model']*1e6:.4f}", ""])
    with open(os.path.join(ROOT, "island_asdrawn_r01_ledger.csv"), "w", newline="") as f:
        w = csv.writer(f); w.writerow(["run", "cycle", "W_mech", "dE_stored", "E_diss", "E_gap",
                                       "resid_gap", "resid_Ediss", "eta"] +
                                      [f"diss_{g}" for g in WINDOWS] + ["diss_Lx3esr", "diss_Lx4esr"])
        for k in ("G0a_rel5", "G1a", "G1b", "R1a", "R1b", "R2a_rel5", "R2b"):
            for L, c in zip(o["res"][k]["leds"], rows[k]["ledger_cycles"]):
                w.writerow([k, c] + [f"{L[x]:.6e}" for x in ("W", "dE", "E_diss", "E_gap")] +
                           [f"{L['resid']:.3e}", f"{L['resid_Ediss']:.3e}", f"{L['eta']:.5f}"] +
                           [f"{L['diss'].get(g, 0):.6e}" for g in WINDOWS] +
                           [f"{L['diss'].get(x, 0):.6e}" for x in ("Lx3esr", "Lx4esr")])
    with open(os.path.join(ROOT, "island_asdrawn_r01_peaks.csv"), "w", newline="") as f:
        w = csv.writer(f); w.writerow(["run", "gap", "i_pk_A", "V_pk_V", "t_half_us", "note"])
        for k, pk in o["peaks"].items():
            for g, v in pk.items():
                th = v.get("t_half")
                w.writerow([k, g, f"{v['i_pk']:.4e}", f"{v['V_pk']:.4e}",
                            "" if th is None else f"{th*1e6:.4f}",
                            "scale-free (100 V seed, cycle 9): ratios only"])
    _plots(o)


def _plots(o):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    rows = o["rows"]
    fig, ax = plt.subplots(2, 2, figsize=(13, 8.5))
    lxs = [0.0, 10e-6, 100e-6, 1e-3]
    keys = {0.0: "G1", 10e-6: "L10u", 100e-6: "L100u", 1e-3: "R1"}
    for br, mk in (("a", "o-"), ("b", "s--")):
        zs = [rows[keys[l] + br]["z"] for l in lxs]; es = [rows[keys[l] + br]["eta"] for l in lxs]
        xl = [1e-7, 1e-5, 1e-4, 1e-3]
        ax[0, 0].semilogx(xl, zs, mk, label=f"bracket ({br})")
        ax[0, 1].semilogx(xl, es, mk, label=f"bracket ({br})")
    ax[0, 0].axhline(rows["G0a_rel5"]["z"], color="k", ls=":", label="G0 (galvanic)")
    ax[0, 1].axhline(rows["G0a_rel5"]["eta"], color="k", ls=":", label="G0")
    ax[0, 1].axhline(0.50, color="#e76f51", ls="-.", label="model eta 0.50")
    ax[0, 1].axhline(0.302, color="#999", ls="-.", label="model eta(G1) 0.302")
    for a, yl in ((ax[0, 0], "z (arbiter rule)"), (ax[0, 1], "eta = dE_stored / W_mech")):
        a.set_xlabel("Lx (H); leftmost point = Lx->0"); a.set_ylabel(yl); a.legend(fontsize=7)
        a.grid(alpha=.3)
    ax[0, 0].set_title("Lx sweep — drawn deck, motor out, stray 5 pF")
    ax[0, 1].set_title(f"verdict: {o['verdict']}")
    # traces: one load stroke, G1 vs R1
    for j, k in enumerate(("G1a", "R1a")):
        d = o["res"][k]["d"]; t = d["time"]; c = 9
        s = (t >= c * T_CYC + 7.15 * DEG) & (t <= c * T_CYC + 7.30 * DEG)
        tt = (t[s] - c * T_CYC - 7.2 * DEG) * 1e6
        a = ax[1, j]
        for n in ("1", "7", "n17", "3", "4"):
            a.plot(tt, d[f"v({n})"][s], lw=1, label=f"V{n}")
        a2 = a.twinx(); a2.plot(tt, d["i(v_ssg3a1)"][s], "k--", lw=.8, label="i SG3a1")
        a.set_xlabel("us after SG3a arming (cycle 9)"); a.set_ylabel("V (scale-free)")
        a2.set_ylabel("A"); a.legend(fontsize=7, loc="upper left"); a2.legend(fontsize=7, loc="upper right")
        a.set_title(f"{k}: load stroke 1->SG3a1->7->Cx3->n17->Lx3->3")
    fig.tight_layout(); fig.savefig(os.path.join(ROOT, "island_asdrawn_r01_traces.png"), dpi=110)
    plt.close(fig)


def campaign():
    """Run every deck of plan() + the tight-tolerance twins (4 in parallel), then report()."""
    write_timing_sub(); write_gap_sub()
    P = plan()
    cf = list(P.values()) + [twin(P[k]) for k in ("G0a", "G0b", "G0a_cpar10", "G1a", "G1b",
                                                  "R2a", "R2b", "G1ma", "G1mb")]
    run_many(cf)
    return report()


if __name__ == "__main__":
    import json
    o = report() if "--report" in sys.argv else campaign()
    print(json.dumps(dict(verdict=o["verdict"], per=o["per"], gates={k: v[0] for k, v in o["H"].items()},
                          motor_dependent=o["motor_dependent"], frozen_empty=o["frozen"][0]),
                     indent=1, default=str))
