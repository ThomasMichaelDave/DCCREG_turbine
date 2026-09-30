#!/usr/bin/env python3
"""
sim/island_asdrawn.py — ISLAND-ASDRAWN Pass A (brief r0.2): event-driven KCL solver on the drawn sheet
======================================================================================================
Is the series-Lx island sink real on the 43-part sheet of record, at circuit level?

ONE solver for every twin (brief r0.2 §2), so R1 - G1 measures the island, not the tool:
  state  = node charges q (every non-reference node of the drawn netlist) + inductor currents I
  stroke = capacitances follow theta at constant (cluster) charge; conducting gaps are held;
           W_mech = dU at constant charge                                        [OC]
  event  = armed gaps re-solved as a linear complementarity problem (ideal rectifiers: forward
           charge >= 0, blocking voltage <= 0) with inductor currents held constant; loss =
           1/2 v^T C_th v on the closing ports (C_th = Schur complement, from the PRE state) [OC]
  ring   = an event that leaves a voltage across an inductor is integrated EXACTLY (matrix
           exponential, frozen capacitances, complementarity switching located by bisection)
           until the driving inductor's first current zero (quench); int i^2 R by Gauss-Legendre;
           the post-quench residue relaxes to the quasi-static equilibrium (inductor -> short),
           loss = 1/2 v^T C_th v + 1/2 L I^2                                     [OC/ME]
  continuous mode (motor in) additionally integrates the motor L-C-R branches between events.

Read-only consumer of: shuttle_core (profiles/caps_phase/shuttle_cycle/steady_capture/TH_*/Params),
doubler_core.solve_doubler4, island_resonant_core.integrate/closed_form, seq_stat_commutation.
Tiers [OC]/[IR]/[RH]/[ME]. Pure EE firewall. Two ledgers (conservation / peaks) kept separate.
"""
import csv
import math
import os
import re
import sys

import numpy as np
from scipy.linalg import expm

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
SPICE = os.path.join(ROOT, "spice")
for p in (HERE, ROOT, os.path.join(ROOT, "reference")):
    if p not in sys.path:
        sys.path.insert(0, p)

import shuttle_core as sc                      # frozen
import doubler_core as dc                      # frozen
import island_resonant_core as irc             # frozen

GND = -1

# ======================================================================================
# 1. LOCKED INPUTS (brief r0.2 §3) — fixed before any verdict run
# ======================================================================================
RPM = 3000.0
F_CYC = 6 * RPM / 60.0                          # 300 Hz                                   [OC]
T_CYC = 1.0 / F_CYC
DEG = T_CYC / 60.0                              # s per sector-degree
# canary operating point (design_synth.ESTABLISHED = the live tool's canary input)       [OC]
CANARY = dict(C1MIN=16.0, C1MAX=280.0, C2MIN=16.0, C2MAX=280.0, CA=309.0, CB=309.0, CPAR=20.0)
CX_MAX_PF = 471.0                               # live default
CX_MIN_PF = 8.0                                 # island_charging_cosim.CX_MIN (design_synth's shuttle) [OC]
GAP_STRAY_PF = sc.Params().gap_stray            # 2 pF across each gap's own terminals    [IR, shuttle]
PCBOSS_PF = sc.Params().pCboss                  # 6 pF                                     [IR, shuttle]
PCBOSS2_PF = sc.Params().pCboss2                # 0 pF (shuttle default = design_synth BOSS basis) [IR]
STRAY_SET = (0.0, 5.0, 20.0)                    # 7/8/n17/n23 -> reference                 [IR sweep]
STRAY_PRIMARY = 5.0
LX_SET = (0.0, 10e-6, 100e-6, 1e-3)
LX_DRAWN = 1e-3
R_LX = 2.0                                      # integrator design point (Q 729 at S2)    [OC brief]
L_MOTOR, C_MOTOR, R_MOTOR = 0.64, 440e-9, 40.0  # as drawn; R_COIL from s8_unified_coupled [OC]
V_STRIKE = 20e3                                 # R4 only                                   [OC]
BS_FRAC = 0.6


def _parse_dxf():
    txt = open(os.path.join(SPICE, "timing.sub")).read()
    tok = re.search(r"DXF stations \(deg, 60deg sector\):\s*(.*)", txt).group(1).split()
    return {tok[i]: float(tok[i + 1]) for i in range(0, len(tok), 2)}


DXF = _parse_dxf()
# stations: shuttle TH_RET/TH_LOAD (0.05/0.12 x 60 = 3.0/7.2 deg) == DXF SG1/SG3a (asserted);
# the rest from the DXF list. Windows [IR lock]: arm AT the station; the rail return is held to the
# end of its half (shuttle holds `ret` through the phase); the load gap disarms at its fire station
# (island isolated before the fire); fire/backstop armed to the end of the half.
ST = dict(SG1=sc.TH_RET * 60.0, SG3a=sc.TH_LOAD * 60.0, SG3b=DXF["SG3b"], BS3=DXF["BS3"],
          SG2=DXF["SG2"], SG4a=DXF["SG4a"], SG4b=DXF["SG4b"], BS4=DXF["BS4"])
WINDOWS = {"SG1": (ST["SG1"], 30.0), "SG3a1": (ST["SG3a"], ST["SG3b"]),
           "SG3b1": (ST["SG3b"], 30.0), "BS3": (ST["BS3"], 30.0),
           "SG2": (ST["SG2"], 60.0), "SG4a1": (ST["SG4a"], ST["SG4b"]),
           "SG4b1": (ST["SG4b"], 60.0), "BS4": (ST["BS4"], 60.0)}
ISLAND_GAPS = ("SG3b1", "BS3", "SG4b1", "BS4")
LOAD_GAPS = ("SG3a1", "SG4a1")
RAIL_GAPS = ("SG1", "SG2")
MOTOR_PARTS = tuple([f"L_A{i}" for i in range(1, 7)] + [f"C_AR{i}" for i in (1, 2, 3, 5, 6)] +
                    ["C__AR4"] + [f"C_BR{i}" for i in range(1, 7)] + [f"L_B{i}" for i in range(1, 7)])
TANK_PARTS = ("L_R1", "C_R1", "L_R2")


def edge_list():
    out = []
    for r in csv.reader(open(os.path.join(ROOT, "topology_edge_list.csv"))):
        if r and not r[0].startswith("#") and r[0] != "component":
            out.append((r[0], r[1], r[2]))
    return out


# ======================================================================================
# 2. NETWORK
# ======================================================================================
class Net:
    """nodes: names (reference excluded). caps: (name, i, j, C | callable(theta_deg)).
    inds: (name, i, j, L, R, kind) kind 'lx' | 'motor'. gaps: (name, i, j, kind, window, family)
    kind 'rect' (ideal one-way, anode i) | 'arc' (bidirectional, sustained while armed) |
    'rect_latch' (one-way, latched off after its first quench in the window) | 'short' (parity)."""

    def __init__(self):
        self.nodes, self.idx = [], {}
        self.caps, self.inds, self.gaps = [], [], []
        self.meta = {}

    def n(self, name):
        if name in ("0", "R-A", "R-B", "ref"):
            return GND
        if name not in self.idx:
            self.idx[name] = len(self.nodes); self.nodes.append(name)
        return self.idx[name]

    def K(self, th):
        N = len(self.nodes); K = np.zeros((N, N))
        for nm, i, j, C in self.caps:
            c = C(th) if callable(C) else C
            if i >= 0: K[i, i] += c
            if j >= 0: K[j, j] += c
            if i >= 0 and j >= 0:
                K[i, j] -= c; K[j, i] -= c
        return K

    def cap_values(self, th):
        return [(nm, i, j, (C(th) if callable(C) else C)) for nm, i, j, C in self.caps]


def _profile_fns(P):
    """C1, C2, Cx3, Cx4 (F) vs theta (deg) from the FROZEN shuttle_core.profiles at the canary."""
    def f(k):
        return lambda th: 1e-12 * sc.profiles((th / 60.0) % 1.0, P)[k]
    return f(0), f(1), f(2), f(3)


def shuttle_params():
    P = sc.Params(); P.cx_max = CX_MAX_PF; P.cx_min = CX_MIN_PF
    return P


class canary_caps:
    """Context: frozen shuttle_core device scalars rebound to the canary via its public hook."""
    def __enter__(self):
        sc.set_device_caps(**CANARY)

    def __exit__(self, *a):
        sc.reset_device_caps()


def build_drawn(lx=LX_DRAWN, bracket="b", stray=STRAY_PRIMARY, motor=False, cpar=None,
                galvanic=False):
    """The drawn netlist, node-exact from topology_edge_list.csv; tank collapsed (R-A = R-B = ref).
    galvanic=True (G0): the islands are replaced by ideal rectifiers 1->3 and 4->2 (armed over the
    load+fire span of each half) [IR]. Capacitance profiles need canary_caps() active at call time."""
    P = shuttle_params()
    c1, c2, cx3, cx4 = _profile_fns(P)
    cpar = CANARY["CPAR"] * 1e-12 if cpar is None else cpar
    net = Net(); boss = (PCBOSS_PF + PCBOSS2_PF) * 1e-12
    for n in ("1", "2", "3", "4"):
        net.n(n)
    for comp, a, b in edge_list():
        if comp in TANK_PARTS or (comp in MOTOR_PARTS and not motor):
            continue
        if galvanic and comp in ("Cx3", "Cx4", "Lx3", "Lx4", "SG3a1", "SG3b1", "BS3", "SG4a1",
                                 "SG4b1", "BS4"):
            continue
        i, j = net.n(a), net.n(b)
        if comp == "C1":
            net.caps.append(("C1", j, i, c1))            # C1: R-A -> 1
        elif comp == "C2":
            net.caps.append(("C2", j, i, c2))
        elif comp in ("Ca1", "Cb1"):
            net.caps.append((comp, i, j, CANARY["CA"] * 1e-12))
        elif comp == "Cx3":
            net.caps.append((comp, i, j, cx3)); net.caps.append((comp + "_boss", i, j, boss))
        elif comp == "Cx4":
            net.caps.append((comp, i, j, cx4)); net.caps.append((comp + "_boss", i, j, boss))
        elif comp in ("Lx3", "Lx4"):
            net.inds.append((comp, i, j, lx, R_LX, "lx"))
        elif comp.startswith("L_A") or comp.startswith("L_B"):
            net.inds.append((comp, i, j, L_MOTOR, R_MOTOR, "motor"))
        elif comp.startswith("C_AR") or comp.startswith("C__AR") or comp.startswith("C_BR"):
            net.caps.append((comp, i, j, C_MOTOR))
        elif comp in WINDOWS:
            fam = ("rail" if comp in RAIL_GAPS else "load" if comp in LOAD_GAPS else "island")
            kind = "rect"
            if fam == "island":
                kind = "arc" if bracket == "a" else "rect_latch"
            net.gaps.append((comp, i, j, kind, WINDOWS[comp], fam))
            net.caps.append((comp + "_stray", i, j, GAP_STRAY_PF * 1e-12))
        else:
            raise ValueError(comp)
    if galvanic:
        for nm, a, b, w in (("D3", "1", "3", (ST["SG3a"], 30.0)), ("D4", "4", "2", (ST["SG4a"], 60.0))):
            i, j = net.n(a), net.n(b)
            net.gaps.append((nm, i, j, "rect", w, "load"))
            net.caps.append((nm + "_stray", i, j, GAP_STRAY_PF * 1e-12))
    for n in ("1", "2", "3", "4"):
        net.caps.append((f"Cpar{n}", net.n(n), GND, cpar))
    if stray > 0 and not galvanic:
        for n in ("7", "8", "n17", "n23"):
            net.caps.append((f"Cs_{n}", net.n(n), GND, stray * 1e-12))
    net.meta = dict(lx=lx, bracket=bracket, stray=stray, motor=motor, cpar=cpar, galvanic=galvanic)
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


def csolve(K, q, edges):
    """Voltages for node charges q with the closure edges shorted (cluster charge conserved,
    reference cluster at 0). Returns V (N,), new node cap-charges K V."""
    N = len(q); cid, nc = _clusters(N, edges)
    if nc == 0:
        V = np.zeros(N)
    else:
        P = _P(cid, nc); Kc = P.T @ K @ P
        V = P @ np.linalg.solve(Kc, P.T @ q)
    return V, K @ V


def edge_flows(N, edges, dq_net):
    """Charge carried by each closure edge (a -> b), from the net node-charge change dq_net
    (= cap-charge change minus inductor injection). Spanning forest; redundant edges carry 0."""
    adj = {k: [] for k in range(-1, N)}
    tree = []; cid, _ = _clusters(N, [])
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
    lam = np.zeros(len(edges))
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
            lam[e] = sum(dq_net[n] for n in seen if n >= 0)
        else:
            seen_a = {a}; st = [a]
            while st:
                x = st.pop()
                for y, ee in adj[x]:
                    if ee == e or y in seen_a:
                        continue
                    seen_a.add(y); st.append(y)
            lam[e] = -sum(dq_net[n] for n in seen_a if n >= 0)
    return lam


def event_loss(K, q_pre, base_edges, new_edges):
    """1/2 v^T M^-1 v: energy lost shorting `new_edges` from the pre state of the network with
    `base_edges` closed; M = port elastance (B^T Kc^-1 B). Independent of the post state. [OC]"""
    if not new_edges:
        return 0.0
    N = len(q_pre); cid, nc = _clusters(N, base_edges)
    V, _ = csolve(K, q_pre, base_edges)
    v = np.array([(V[a] if a >= 0 else 0.0) - (V[b] if b >= 0 else 0.0) for a, b in new_edges])
    if nc == 0:
        return 0.0
    P = _P(cid, nc); Kc = P.T @ K @ P; Ki = np.linalg.inv(Kc)
    B = np.zeros((nc, len(new_edges)))
    for k, (a, b) in enumerate(new_edges):
        if a >= 0 and cid[a] >= 0: B[cid[a], k] += 1.0
        if b >= 0 and cid[b] >= 0: B[cid[b], k] -= 1.0
    M = B.T @ Ki @ B
    return float(0.5 * v @ np.linalg.lstsq(M, v, rcond=None)[0])


def lcp(K, q, fixed, cands, prev=None, vth=None, tol=1e-9):
    """Ideal-rectifier complementarity: choose S within cands (edges a->b) so that, with fixed+S
    closed: every d in S carries forward charge >= 0 and every d not in S has V_a - V_b <= vth_d
    (0 for ideal; V_strike for R4). Returns (S list of cand indices, V, qnew, lam_S, nvalid)."""
    N = len(q)
    vth = [0.0] * len(cands) if vth is None else vth
    scaleq = max(1e-300, float(np.max(np.abs(q))))

    def test(S):
        edges = list(fixed) + [cands[k] for k in S]
        V, qn = csolve(K, q, edges)
        lam = edge_flows(N, edges, qn - q)[len(fixed):]
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
        return V, qn, lam
    if prev is not None:
        r = test(list(prev))
        if r is not None:
            return list(prev), r[0], r[1], r[2], 1
    import itertools
    found = []
    for m in range(len(cands) + 1):
        for S in itertools.combinations(range(len(cands)), m):
            r = test(list(S))
            if r is not None:
                found.append((list(S), r))
    if not found:
        raise RuntimeError("LCP: no consistent rectifier state")
    S, r = max(found, key=lambda x: abs(x[1][0][0]) + abs(x[1][0][3]) if N > 3 else 0)
    return S, r[0], r[1], r[2], len(found)


# ======================================================================================
# 4. RING ENGINE — exact LTI integration at frozen capacitances
# ======================================================================================
GL_X, GL_W = np.polynomial.legendre.leggauss(6)


class Ring:
    """Linear dynamics of the capacitive network with dynamic inductors `dyn` (list of ind indices)
    and closure edges `edges` (shorts) at frozen K. State x = [q_node (N); I (m)] (node charges are
    kept at node level so partitions are exact; the cluster constraint is applied through csolve)."""

    def __init__(self, net, K, edges, dyn):
        self.net, self.K, self.edges, self.dyn = net, K, list(edges), list(dyn)
        N = len(net.nodes); m = len(dyn)
        cid, nc = _clusters(N, self.edges)
        P = _P(cid, nc); self.P = P; self.cid = cid
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
        # reduced state z = [qc; I]
        A = np.zeros((nc + m, nc + m))
        A[:nc, nc:] = G
        A[nc:, :nc] = -(G.T @ self.Kci) / Ld[:, None]
        A[nc:, nc:] = -np.diag(Rd / Ld)
        self.A = A; self.nc = nc; self.m = m

    def z_of(self, q, I):
        return np.concatenate([self.P.T @ q, I])

    def V_of(self, z):
        return self.P @ (self.Kci @ z[:self.nc]) if self.nc else np.zeros(len(self.cid))

    def step(self, z, h):
        return expm(self.A * h) @ z

    def integrals(self, z0, h):
        """int_0^h of I_k^2 and I_k (per dynamic inductor), Gauss-Legendre (exact to ~1e-12 at
        h << ring period)."""
        i2 = np.zeros(self.m); i1 = np.zeros(self.m)
        for x, w in zip(GL_X, GL_W):
            t = 0.5 * h * (x + 1)
            z = expm(self.A * t) @ z0
            I = z[self.nc:]
            i2 += 0.5 * h * w * I * I; i1 += 0.5 * h * w * I
        return i2, i1


# ======================================================================================
# 5. THE MACHINE SIMULATOR
# ======================================================================================
class Sim:
    """Quasi-static / continuous simulation of one network over a theta schedule.
    mode 'qs' (motor out) or 'cont' (integrates motor branches between events)."""

    def __init__(self, net, mode="qs", dth=0.05, vstrike=None, record_events=False, hold=True):
        self.net, self.mode, self.dth = net, mode, dth
        self.vstrike, self.hold = vstrike, hold
        N = len(net.nodes); self.N = N
        self.q = np.zeros(N); self.I = np.zeros(len(net.inds))
        self.th = 0.0
        self.cond = set()                           # conducting gap names (rect held / arc closed)
        self.latched = set()
        self.ledger = dict(W=0.0, alg=0.0, ring=0.0, relax=0.0, motorR=0.0)
        self.diss_by = {}
        self.rec = record_events; self.events = []
        self.lx_dyn = [k for k, d in enumerate(net.inds) if d[5] == "lx" and d[3] > 0]
        self.lx_short = [k for k, d in enumerate(net.inds) if d[5] == "lx" and d[3] == 0]
        self.motor = [k for k, d in enumerate(net.inds) if d[5] == "motor"]
        self.gap_by = {g[0]: g for g in net.gaps}

    # ---- helpers ----
    def armed(self, name, th):
        a, b = self.gap_by[name][4]
        t = th % 60.0
        return (a <= t < b) if a < b else (t >= a or t < b)

    def ind_edges(self, which):
        return [(self.net.inds[k][1], self.net.inds[k][2]) for k in which]

    def fixed_edges(self, th, quasi=True):
        """Bidirectional closures: Lx->0 shorts always; dynamic Lx as shorts in quasi-static
        strokes; armed arcs / parity shorts that are conducting."""
        e = self.ind_edges(self.lx_short)
        if quasi:
            e += self.ind_edges(self.lx_dyn)
        for nm in sorted(self.cond):
            g = self.gap_by[nm]
            if g[3] in ("arc", "short"):
                e.append((g[1], g[2]))
        return e

    def cands(self, th):
        """Armed one-way gaps (candidates of the complementarity problem)."""
        out = []
        for g in self.net.gaps:
            if g[3] in ("rect", "rect_latch") and self.armed(g[0], th) and g[0] not in self.latched:
                out.append(g)
        return out

    def voltages(self, th=None, K=None, quasi=True):
        K = self.net.K(self.th if th is None else th) if K is None else K
        edges = self.fixed_edges(self.th, quasi) + [(self.gap_by[n][1], self.gap_by[n][2])
                                                    for n in sorted(self.cond)
                                                    if self.gap_by[n][3] in ("rect", "rect_latch")]
        V, _ = csolve(K, self.q, edges)
        return V

    def energy(self, K=None):
        K = self.net.K(self.th) if K is None else K
        V = self.voltages(K=K)
        E = 0.5 * V @ K @ V
        for k, d in enumerate(self.net.inds):
            if d[3] > 0 and d[5] == "motor":
                E += 0.5 * d[3] * self.I[k] ** 2
        # dynamic Lx carry current only inside events (quasi-static current ~0 between events)
        return float(E)

    # ---- stroke: capacitances th0 -> th1 at constant cluster charge, conducting gaps held ----
    def held_rects(self):
        return [n for n in sorted(self.cond) if self.gap_by[n][3] in ("rect", "rect_latch")]

    def stroke(self, th1):
        K0 = self.net.K(self.th); K1 = self.net.K(th1)
        V0 = self.voltages(K=K0); U0 = 0.5 * V0 @ K0 @ V0
        held = self.held_rects()
        fixed = self.fixed_edges(self.th)
        hc = [(self.gap_by[n][1], self.gap_by[n][2]) for n in held]
        # complementarity restricted to the held set: a held rectifier drops out if the stroke
        # would reverse it (then it must block). Newly forward gaps are the event's business.
        S, V1, qn, lam, _ = lcp(K1, self.q, fixed, hc, prev=list(range(len(hc))))
        self.cond = set(n for n in self.cond if self.gap_by[n][3] in ("arc", "short")) | \
            set(held[k] for k in S)
        self.q = qn
        self.ledger["W"] += 0.5 * V1 @ K1 @ V1 - U0
        self.th = th1

    def _edges_now(self, th, quasi):
        return self.fixed_edges(th, quasi) + [(self.gap_by[n][1], self.gap_by[n][2])
                                              for n in self.held_rects()]

    # ---- continuous mode: motor branch dynamics over dt at frozen caps ----
    def motor_step(self, dt):
        if not self.motor or dt <= 0:
            return
        K = self.net.K(self.th)
        for _ in range(8):
            edges = self._edges_now(self.th, quasi=True)
            held = self.held_rects()
            R = Ring(self.net, K, edges, self.motor)
            z0 = R.z_of(self.q, self.I[self.motor])
            i2, i1 = R.integrals(z0, dt)
            z1 = R.step(z0, dt)
            qn = K @ R.V_of(z1)
            lam = edge_flows(self.N, edges, qn - self.q - R.Gn @ i1)[len(edges) - len(held):]
            sc_ = max(1e-300, float(np.max(np.abs(qn))))
            bad = [held[k] for k, l in enumerate(lam) if l < -1e-12 * sc_]
            if not bad:
                break
            self.cond -= set(bad)
        self.q = qn; self.I[self.motor] = z1[R.nc:]
        e = float(np.sum(R.Rd * i2))
        self.ledger["motorR"] += e; self._book("motor_R", e)

    def _book(self, k, e):
        self.diss_by[k] = self.diss_by.get(k, 0.0) + e

    def _vth(self, g):
        if self.vstrike is None or g[0] in self.cond:
            return 0.0
        return self.vstrike * (BS_FRAC if g[0].startswith("BS") else 1.0)

    # ---- event: arming changes / newly forward rectifiers ----
    def event(self, th, strike=False):
        """Complementarity over armed gaps with inductor currents HELD (dynamic Lx open for the
        instant). New closures dump through the Schur-complement loss; if a voltage is then left
        across a dynamic Lx, the ring is integrated and the residue relaxed."""
        K = self.net.K(th)
        for n in list(self.cond):
            if not self.armed(n, th):
                self.cond.discard(n)
        for n in list(self.latched):
            if not self.armed(n, th):
                self.latched.discard(n)
        V = self.voltages(K=K)
        new_arcs = []
        for g in self.net.gaps:
            if g[3] in ("arc", "short") and self.armed(g[0], th) and g[0] not in self.cond:
                v = (V[g[1]] if g[1] >= 0 else 0.0) - (V[g[2]] if g[2] >= 0 else 0.0)
                if abs(v) >= self._vth(g):
                    new_arcs.append(g[0])
        cands = self.cands(th)
        held = [g[0] for g in cands if g[0] in self.cond]
        base_fixed = self.fixed_edges(th, quasi=False)
        fixed = base_fixed + [(self.gap_by[n][1], self.gap_by[n][2]) for n in new_arcs]
        S, Vn, qn, lam, nv = lcp(K, self.q, fixed, [(g[1], g[2]) for g in cands],
                                 prev=[k for k, g in enumerate(cands) if g[0] in self.cond],
                                 vth=[self._vth(g) for g in cands])
        Snames = [cands[k][0] for k in S]
        new_closed = [n for n in Snames if n not in self.cond] + new_arcs
        if not new_closed:
            self.cond = set(n for n in self.cond if self.gap_by[n][3] in ("arc", "short")) | set(Snames)
            self.q = qn
            return None
        return self.fire(th, K, new_closed, Snames, held, base_fixed, new_arcs, qn)

    def fire(self, th, K, new_closed, Snames, held, base_fixed, new_arcs, qn):
        base_edges = base_fixed + [(self.gap_by[n][1], self.gap_by[n][2]) for n in held if n in Snames]
        new_edges = [(self.gap_by[n][1], self.gap_by[n][2]) for n in new_closed]
        q_pre = self.q.copy()
        e_alg = event_loss(K, q_pre, base_edges, new_edges)
        self.cond = set(n for n in self.cond if self.gap_by[n][3] in ("arc", "short")) | \
            set(new_arcs) | set(Snames)
        self.q = qn
        self.ledger["alg"] += e_alg
        for n in new_closed:
            self._book(n, e_alg / len(new_closed))
        ev = dict(th=th, gaps=list(new_closed), e_alg=e_alg, q_pre=q_pre, I_pre=self.I.copy(),
                  cond_pre=sorted(set(held) & set(Snames)), K=K) if self.rec else None
        if self.lx_dyn:
            ev = self.ring(th, K, ev)
        if self.rec and ev is not None:
            ev["q_post"] = self.q.copy(); self.events.append(ev)
        return ev

    def _mon(self, R, K, edges, nheld, z):
        """State at z: V, dynamic I, node cap-charges, instantaneous current through each held
        rectifier (exact: forest flow of K dV/dt - injection)."""
        V = R.V_of(z); I = z[R.nc:]
        dV = R.P @ (R.Kci @ (R.G @ I)) if R.nc else np.zeros(self.N)
        rate = edge_flows(self.N, edges, K @ dV - R.Gn @ I)
        return V, I, K @ V, rate[len(edges) - nheld:]

    def ring(self, th, K, ev, tmax=200e-6):
        """Exact LTI ring at frozen K: stops at the driving Lx current's first zero. Held
        rectifiers open when their current reverses (latching gaps latch); armed open rectifiers
        close when their voltage turns forward. Then the residue relaxes."""
        dyn = self.lx_dyn + self.motor
        edges = self._edges_now(th, quasi=False)
        V = csolve(K, self.q, edges)[0]
        vL = np.array([(V[self.net.inds[k][1]] if self.net.inds[k][1] >= 0 else 0) -
                       (V[self.net.inds[k][2]] if self.net.inds[k][2] >= 0 else 0) for k in self.lx_dyn])
        if np.max(np.abs(vL)) <= 1e-13 * max(1e-300, float(np.max(np.abs(V)))):
            self._relax(th, K, ev); return ev
        drv = self.lx_dyn[int(np.argmax(np.abs(vL)))]
        jd = dyn.index(drv)
        t = 0.0; started = False; peak = 0.0; t_q = {}
        i2tot = np.zeros(len(self.net.inds)); i1tot = np.zeros(len(self.net.inds)); trace = [(0.0, 0.0)]
        h_try = None
        while t < tmax:
            edges = self._edges_now(th, quasi=False)
            held = self.held_rects()
            cands = [g for g in self.cands(th) if g[0] not in self.cond]
            R = Ring(self.net, K, edges, dyn)
            z = R.z_of(self.q, self.I[dyn])
            if R.A.size:
                lam_, Vec = np.linalg.eig(R.A)
                amp = np.abs(np.linalg.solve(Vec, z.astype(complex))) * np.linalg.norm(Vec, axis=0)
            else:
                lam_, amp = np.array([1.0]), np.array([1.0])
            mag = np.abs(lam_); nz = mag[mag > 1e-9 * mag.max()]
            # only oscillatory modes still carrying amplitude limit the step (a decayed parasitic
            # mode must not pin h for the rest of an overdamped ring) [ME]
            osc = [abs(l.imag) for l, a in zip(lam_, amp) if abs(l.imag) > 1e-9 * mag.max()
                   and abs(l.real) < 3 * abs(l.imag) and a > 1e-9 * max(amp.max(), 1e-300)]
            h_max = (2 * math.pi / max(osc) / 48.0) if osc else 0.25 / nz.min()
            if h_try is None:
                h_try = min(h_max, 0.05 / nz.max()) if not osc else h_max
            h = min(h_try, h_max, tmax - t)
            Vs, Is, qs, rs = self._mon(R, K, edges, len(held), z)
            Iscale = max(peak, abs(Is[jd]), 1e-300)
            s_drv = np.sign(Is[jd]) if started else 0.0

            def trig(zz):
                Vz, Iz, qz, rz = self._mon(R, K, edges, len(held), zz)
                rev = [held[k] for k in range(len(held)) if rz[k] < -1e-9 * Iscale]
                vsc = 1e-9 * max(1e-300, float(np.max(np.abs(Vz))))
                fwd = [g[0] for g in cands if ((Vz[g[1]] if g[1] >= 0 else 0) -
                                               (Vz[g[2]] if g[2] >= 0 else 0)) > self._vth(g) + vsc]
                zero = started and (np.sign(Iz[jd]) != s_drv)
                return rev, fwd, zero, Vz, Iz, qz
            z1 = R.step(z, h)
            rev, fwd, zero, V1, I1, q1 = trig(z1)
            if rev or fwd or zero:
                lo, hi = 0.0, h
                for _ in range(64):
                    mid = 0.5 * (lo + hi)
                    r_, f_, z_, *_ = trig(R.step(z, mid))
                    if r_ or f_ or z_:
                        hi = mid
                    else:
                        lo = mid
                h = hi; z1 = R.step(z, h)
                rev, fwd, zero, V1, I1, q1 = trig(z1)
            i2, i1 = R.integrals(z, h)
            for kk, k in enumerate(dyn):
                i2tot[k] += i2[kk]; i1tot[k] += i1[kk]
            self.q = q1; self.I[dyn] = I1; t += h
            peak = max(peak, abs(I1[jd])); started = started or abs(I1[jd]) > 0
            trace.append((t, float(I1[jd])))
            for n in rev:
                self.cond.discard(n); t_q.setdefault(n, t)
                if self.gap_by[n][3] == "rect_latch":
                    self.latched.add(n)
            for n in fwd:
                self.cond.add(n)
            if zero:
                break
            if rev or fwd:
                h_try = None                          # re-derive the step for the new topology
            else:
                h_try = 2.0 * h
                # overdamped: the driving current decays without a zero -> ring over
                # (the residue is then relaxed EXACTLY, so this is a physics cut, not a ledger one)
                if started and abs(I1[jd]) < 1e-3 * peak:
                    break
        e_ring = 0.0
        for k in self.lx_dyn:
            e = self.net.inds[k][4] * i2tot[k]; e_ring += e; self._book(self.net.inds[k][0] + "_R", e)
        e_m = sum(self.net.inds[k][4] * i2tot[k] for k in self.motor)
        self.ledger["ring"] += e_ring; self.ledger["motorR"] += e_m; self._book("motor_R", e_m)
        if ev is not None:
            ev.update(t_ring=t, t_quench=t_q, i_pk=peak, drv=self.net.inds[drv][0], e_ring=e_ring,
                      q_ring_end=self.q.copy(), I_ring_end=self.I.copy(), qL=i1tot.copy(),
                      cond_ring_end=sorted(self.cond), trace=trace)
        self._relax(th, K, ev)
        return ev

    def _relax(self, th, K, ev):
        """Residue -> quasi-static equilibrium: dynamic Lx become shorts, their current -> 0.
        Loss = 1/2 v^T C_th v on the Lx ports (+ newly conducting rectifiers) + 1/2 L I^2. [ME]"""
        e_ind = 0.0
        for k in self.lx_dyn:
            e_ind += 0.5 * self.net.inds[k][3] * self.I[k] ** 2
            self.I[k] = 0.0
        cands = self.cands(th)
        held = [g[0] for g in cands if g[0] in self.cond]
        S, V, qn, lam, nv = lcp(K, self.q, self.fixed_edges(th, quasi=True),
                                [(g[1], g[2]) for g in cands],
                                prev=[k for k, g in enumerate(cands) if g[0] in self.cond])
        Snames = [cands[k][0] for k in S]
        newS = [n for n in Snames if n not in self.cond]
        base = self.fixed_edges(th, quasi=False) + [(self.gap_by[n][1], self.gap_by[n][2])
                                                    for n in held if n in Snames]
        new_edges = self.ind_edges(self.lx_dyn) + [(self.gap_by[n][1], self.gap_by[n][2]) for n in newS]
        e_cap = event_loss(K, self.q, base, new_edges)
        self.cond = set(n for n in self.cond if self.gap_by[n][3] in ("arc", "short")) | set(Snames)
        self.q = qn
        self.ledger["relax"] += e_cap + e_ind
        self._book("relax", e_cap + e_ind)
        if ev is not None:
            ev["e_relax"] = e_cap + e_ind

    # ---- one cycle on the DXF schedule ----
    def grid(self, th0):
        pts = set(np.round(np.arange(0.0, 60.0 + 1e-9, self.dth), 9))
        for a, b in WINDOWS.values():
            pts.add(round(a, 9)); pts.add(round(b % 60.0, 9))
        pts = sorted(p for p in pts if p < 60.0 - 1e-12)
        return [th0 + p for p in pts] + [th0 + 60.0]

    def cycle(self, k, zth=None, cut=0.0):
        th0 = 60.0 * k + cut
        g = [x + cut for x in self.grid(60.0 * k)]
        g = sorted(set([th0] + [x for x in g if th0 < x < th0 + 60.0] +
                       [x + 60.0 for x in self.grid(60.0 * k) if x + 60.0 < th0 + 60.0 + 1e-12 and x + 60.0 > th0]
                       + [th0 + 60.0]))
        g = sorted(set(self.grid(60.0 * k) + self.grid(60.0 * (k + 1))))
        g = [x for x in g if th0 - 1e-12 <= x <= th0 + 60.0 + 1e-12]
        if abs(g[0] - th0) > 1e-9:
            g = [th0] + g
        if abs(g[-1] - (th0 + 60.0)) > 1e-9:
            g = g + [th0 + 60.0]
        if zth is not None:
            g = sorted(set(g) | {th0 + zth})
        mag = None
        for th in g[1:]:
            if self.mode == "cont":
                self.motor_step((th - self.th) * DEG)
            self.stroke(th)
            self.event(th, strike=self.vstrike is not None)
            if zth is not None and abs(th - (60.0 * k + zth)) < 1e-9:
                mag = self.state_mag()
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


def seed(sim, v=-1.0):
    """V1 = V4 = v, others 0 (the solve_doubler4/shuttle seed), as node charges at theta."""
    K = sim.net.K(sim.th); V = np.zeros(sim.N)
    V[sim.net.idx["1"]] = v; V[sim.net.idx["4"]] = v
    sim.q = K @ V


def run_machine(net, mode="qs", ncyc=40, burn=20, dth=0.05, vstrike=None, seed_v=-1.0,
                normalize=True, record_from=None, zth=None, cut=0.0):
    """Run ncyc cycles; per-cycle ledger rows after burn. z = |V1|+|V4| ratio at cycle boundaries."""
    sim = Sim(net, mode=mode, dth=dth, vstrike=vstrike)
    sim.th = cut
    seed(sim, seed_v)
    rows = []; mags = []
    for k in range(ncyc):
        sim.rec = record_from is not None and k >= record_from
        E0 = sim.energy(); L0 = dict(sim.ledger); D0 = dict(sim.diss_by)
        m0 = sim.state_mag()
        mz = sim.cycle(k, zth, cut)
        E1 = sim.energy(); m1 = sim.state_mag()
        dL = {kk: sim.ledger[kk] - L0.get(kk, 0.0) for kk in sim.ledger}
        dD = {kk: sim.diss_by[kk] - D0.get(kk, 0.0) for kk in sim.diss_by}
        W = dL["W"]; Ed = dL["alg"] + dL["ring"] + dL["relax"] + dL["motorR"]
        rows.append(dict(cycle=k, z=m1 / m0 if m0 > 0 else float("nan"), mz=mz, W=W, dE=E1 - E0, E_diss=Ed,
                         eta=(E1 - E0) / W if W else float("nan"),
                         resid=abs(W - (E1 - E0) - Ed) / max(abs(W), 1e-300), parts=dL, by=dD))
        rows[-1]["norm"] = 1.0
        if normalize and m1 > 0:
            sim.rescale(1.0 / m1); rows[-1]["norm"] = m1
    st = rows[burn:]
    if zth is not None:                      # z at a fixed in-cycle phase (Floquet ratio)
        zs = [st[i + 1]["mz"] / (st[i]["mz"] / st[i]["norm"]) for i in range(len(st) - 1)]
    else:
        zs = [r["z"] for r in st]
    out = dict(z=float(np.median(zs)), z_all=zs, eta=float(np.mean([r["eta"] for r in st])),
               eta_spread=float(np.ptp([r["eta"] for r in st])),
               resid_max=float(max(r["resid"] for r in st)), rows=rows, sim=sim)
    return out


# ======================================================================================
# 6. HARNESS GATES
# ======================================================================================
S2_PUB = {2.0: (2.22155, 998.89051), 20.0: (2.22155, 989.01498), 100.0: (2.22289, 947.40603)}


def s2_net(R):
    net = Net()
    s, x, b = net.n("src"), net.n("x"), net.n("bnk")
    net.caps += [("Csrc", s, GND, 1e-9), ("Cx", x, GND, 1e-15), ("Cbank", b, GND, 1e-9)]
    net.inds.append(("Lx", s, x, 1e-3, R, "lx"))
    net.gaps.append(("D", x, b, "rect", (0.0, 60.0), "load"))
    return net


def h1_ring():
    """H1: the solver's ring path on the S2 case vs island_resonant_core.integrate AND the
    published S2 numbers (t1/2 within 0.01 %, V_bank within 0.61 %)."""
    rows = []
    for R, (th_pub, vb_pub) in S2_PUB.items():
        net = s2_net(R); sim = Sim(net, record_events=True)
        K = net.K(0.0); V = np.array([1000.0, 1000.0, 0.0])   # quasi-static: Lx short -> x = src
        sim.q = K @ V
        ev = sim.event(0.0)
        vb = csolve(K, sim.q, sim.fixed_edges(0.0))[0][2]
        t_h = ev["t_quench"].get("D", ev["t_ring"]) * 1e6
        it = irc.integrate(1e-9, 1e-9, 1000.0, 1e-3, R)
        rows.append(dict(R=R, t_half_us=t_h, t_pub=th_pub, dt_pct=abs(t_h - th_pub) / th_pub * 100,
                         t_irc_us=it["t_half"] * 1e6, V_bank=vb, V_pub=vb_pub,
                         dv_pct=abs(vb - vb_pub) / vb_pub * 100, V_irc=it["V_bank_final"],
                         E_loss=ev["e_ring"] + ev["e_alg"], E_irc=it["E_loss"]))
    ok = all(r["dt_pct"] <= 0.01 and r["dv_pct"] <= 0.61 for r in rows)
    return ok, rows


def doubler_net(cpar_pF=20.0, station=False):
    """H3 galvanic anchor: the 4-node doubler with ideal rectifiers D1 2->ref, D2 3->ref,
    D3 1->3, D4 4->2 and solve_doubler4's two-phase caps (A = C1max/C2min on [0,30))."""
    c = CANARY; net = Net()
    n1, n2, n3, n4 = (net.n(x) for x in "1234")
    A = lambda th: (th % 60.0) < 30.0
    net.caps += [("C1", n1, GND, lambda th: 1e-12 * (c["C1MAX"] if A(th) else c["C1MIN"])),
                 ("C2", n4, GND, lambda th: 1e-12 * (c["C2MIN"] if A(th) else c["C2MAX"])),
                 ("Ca1", n1, n2, c["CA"] * 1e-12), ("Cb1", n3, n4, c["CB"] * 1e-12)]
    for n in (n1, n2, n3, n4):
        net.caps.append((f"Cpar{n}", n, GND, cpar_pF * 1e-12))
    al = (0.0, 60.0)
    w = dict(D1=(ST["SG1"], 30.0), D3=(ST["SG3a"], 30.0), D2=(ST["SG2"], 60.0), D4=(ST["SG4a"], 60.0))
    for nm, a, b in (("D1", n2, GND), ("D2", n3, GND), ("D3", n1, n3), ("D4", n4, n2)):
        net.gaps.append((nm, a, b, "rect", w[nm] if station else al, "load"))
    return net


def h3_galvanic():
    """H3: always-armed and station-armed galvanic doubler vs solve_doubler4 at the same caps,
    Cpar 20 and 10 pF, to <= 1e-6 relative."""
    c = CANARY; rows = []
    for cp in (20.0, 10.0):
        zref = dc.solve_doubler4(c["C1MIN"], c["C1MAX"], c["C2MIN"], c["C2MAX"], c["CA"], c["CB"], cp)
        for station in (False, True):
            r = run_machine(doubler_net(cp, station), ncyc=40, burn=20, dth=1.0, zth=29.0)
            rows.append(dict(cpar=cp, station=station, z=r["z"], z_ref=zref,
                             rel=abs(r["z"] - zref) / zref, resid=r["resid_max"], eta=r["eta"]))
    return all(x["rel"] <= 1e-6 for x in rows), rows


def _shuttle_net(P, lx=0.0, eps_stray=0.0):
    """The shuttle's own topology (sc.caps_phase: Cx on (7,3) with boss; Cpar on 1-4) with the
    drawn island split Cx3 (7,n17) + Lx3 (n17,3) and Cx4 (n23,8) + Lx4 (2,n23). Caps are read
    from the mutable dict net.cur, set by the parity schedule from sc.caps_phase."""
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
    net.inds += [("Lx3", ix["n17"], ix["3"], lx, R_LX, "lx"), ("Lx4", ix["2"], ix["n23"], lx, R_LX, "lx")]
    return net, mp


def shuttle_parity(P, lx=0.0, oneway=False, iterations=120, burn=60, eps_stray=0.0):
    """H4/H4b: shuttle_core.shuttle_cycle's schedule (caps_phase strokes, SG1/SG2 returns held,
    load short, 24-step collapse with emergent fire at ov>0) executed with THIS solver's strokes,
    Schur-complement events and (lx>0) ring path. oneway: load/fire as rectifiers (quench)."""
    net, mp = _shuttle_net(P, lx, eps_stray)
    ix = net.idx
    kind = "rect" if oneway else "short"
    al = (0.0, 60.0)
    for nm, a, b, kd in (("RET_A", "2", "0", "short"), ("RET_B", "3", "0", "short"),
                         ("LOAD_A", "1", "7", kind), ("LOAD_B", "4", "8", kind),
                         ("FIRE_A", "7", "3", kind), ("FIRE_B", "8", "2", kind)):
        net.gaps.append((nm, net.n(a), net.n(b), kd, al, "load"))
    sim = Sim(net)
    sim.cands = lambda th: [sim.gap_by[n] for n in sorted(sim.enabled)
                            if sim.gap_by[n][3] == "rect" and n not in sim.latched]
    sim.enabled = set()
    sim.armed = lambda name, th: name in sim.enabled

    def setcaps(caps):
        for a, b, C in caps:
            net.cur[(a, b)] = C * 1e-12

    def closeto(names):
        """Close exactly `names` (shorts/rects enabled) at current caps; event + ring if Lx."""
        sim.enabled = set(names)
        for n in list(sim.cond):
            if n not in names:
                sim.cond.discard(n)
        sim.event(sim.th)

    setcaps(sc.caps_phase("B", P)); sim.th = 0.0
    K = net.K(0.0); V = np.zeros(sim.N); V[ix["1"]] = -1.0; V[ix["4"]] = -1.0; sim.q = K @ V
    ratios = []; pm = 2.0; led = []
    for cyc in range(iterations):
        W0 = sim.ledger["W"]
        for which, ret, src, isl, snk, ld, fr in (("A", "RET_A", 1, "7", "3", "LOAD_A", "FIRE_A"),
                                                  ("B", "RET_B", 4, "8", "2", "LOAD_B", "FIRE_B")):
            sim.enabled = set(); sim.cond = set()
            capsP = sc.caps_phase(which, P); setcaps(capsP); sim.stroke(sim.th)      # all open
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


def h4_shuttle(tol=1e-6):
    """H4: this solver on the shuttle's schedule & topology (Lx shorted) vs shuttle_core."""
    with canary_caps():
        P = shuttle_params()
        z_ref = sc.shuttle_run(P)[0]
        rows_sc = sc.steady_capture(P, ncyc=20)
        z_mine, _ = shuttle_parity(P, lx=0.0)
    return abs(z_mine - z_ref) / z_ref <= tol, dict(z=z_mine, z_shuttle_run=z_ref,
                                                    rel=abs(z_mine - z_ref) / z_ref)


def h2_seqstat():
    """H2 (ngspice, frozen arbiter imported unchanged; asd_-prefixed decks)."""
    import seq_stat_commutation as ssc
    zd, cd = ssc.run_z(ssc.deck("diode", name="asd_h2_direct"), "asd_h2_direct.cir")
    zr, cr = ssc.run_z(ssc.deck("reson", lxfwd=1e-5, name="asd_h2_reson"), "asd_h2_reson.cir")
    return abs(zd - 1.39) <= 0.03 and abs(zr - 1.39) <= 0.03, dict(z_direct=zd, z_reson_10uH=zr,
                                                                     clean=(cd, cr))


def r0_arbiter():
    """R0: deck('reson', lxfwd=1e-3) — the galvanic limit at the drawn Lx (ngspice)."""
    import seq_stat_commutation as ssc
    z, c = ssc.run_z(ssc.deck("reson", lxfwd=1e-3, name="asd_r0"), "asd_r0.cir")
    return dict(z=z, clean=c, observable=z is not None)


def frozen_diff(base="f9c9efa", head_spice="HEAD"):
    """Empty-diff: reference/, shuttle_core.py, sim/seq_stat_commutation.py and the Pass-A set vs
    the branch base; every committed spice/ file vs HEAD (incl. the r0.1 ia_* decks)."""
    import subprocess
    fa = ["shuttle_core.py", "reference/", "sim/seq_stat_commutation.py", "sim/design_synth.py",
          "tools/", "index.html", "docs/kicad/", "topology_edge_list.csv"]
    r1 = subprocess.run(["git", "diff", "--stat", base, "--"] + fa, cwd=ROOT, capture_output=True, text=True)
    r2 = subprocess.run(["git", "diff", "--stat", head_spice, "--", "spice/"], cwd=ROOT,
                        capture_output=True, text=True)
    r3 = subprocess.run(["git", "status", "--porcelain", "--"] + fa, cwd=ROOT, capture_output=True, text=True)
    out = r1.stdout + r2.stdout + r3.stdout
    return out.strip() == "", out


def gates(h4b=True):
    out = {}
    out["H1"] = h1_ring()
    out["H2"] = h2_seqstat()
    out["H3"] = h3_galvanic()
    out["H4"] = h4_shuttle()
    if h4b:
        with canary_caps():
            P = shuttle_params()
            z0, _ = shuttle_parity(P, lx=0.0, iterations=50, burn=25, eps_stray=1e-13)
            res = {}
            for lx in (1e-10, 1e-11):
                for ow in (False, True):
                    z, _ = shuttle_parity(P, lx=lx, oneway=ow, iterations=50, burn=25, eps_stray=1e-13)
                    res[f"{'oneway' if ow else 'short'}_{lx:g}"] = dict(z=z, rel=abs(z - z0) / z0)
        # the gate is stated for the OVERDAMPED limit: at 0.1 nH / 2 ohm the load loop is still
        # under-damped (one-way quench keeps the overshoot, +1.7 %), so it is evaluated at 0.01 nH
        # and the 0.1 nH rows are recorded.
        ok = res["short_1e-10"]["rel"] <= 1e-3 and res["oneway_1e-11"]["rel"] <= 1e-3
        out["H4b"] = (ok, dict(z_alg=z0, **res))
    return out


# ======================================================================================
# 7. ON-LOAD SELF-TESTS (fast)
# ======================================================================================
def _selftest():
    ok = len(edge_list()) == 43
    ok &= abs(ST["SG1"] - DXF["SG1"]) < 1e-9 and abs(ST["SG3a"] - DXF["SG3a"]) < 1e-9
    # two-capacitor paradox: 1 nF @ 1 V shorted to 1 nF @ 0 -> loss 1/4 nJ, independent formula
    K = np.array([[1e-9, 0.0], [0.0, 1e-9]]); q = K @ np.array([1.0, 0.0])
    ok &= abs(event_loss(K, q, [], [(0, 1)]) - 0.25e-9) < 1e-21
    V, qn = csolve(K, q, [(0, 1)]); ok &= abs(V[0] - 0.5) < 1e-12 and abs(V[1] - 0.5) < 1e-12
    lam = edge_flows(2, [(0, 1)], qn - q); ok &= abs(lam[0] - 0.5e-9) < 1e-21
    # rectifier blocks reverse
    S, V, qn, lam, n = lcp(K, K @ np.array([0.0, 1.0]), [], [(0, 1)]); ok &= S == [] and n == 1
    if not ok:
        raise AssertionError("island_asdrawn on-load self-test FAILED")
    return ok


SELFTEST_OK = _selftest()


if __name__ == "__main__":
    import json
    print(json.dumps({k: (v[0], v[1]) for k, v in gates().items()}, indent=1, default=str))
