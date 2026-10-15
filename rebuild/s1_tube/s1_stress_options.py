"""rebuild/s1_tube/s1_stress_options.py -- Stage 1: how to move the voltage stress off the discrete parts.

The designer (2026-10-14): "how can we move the voltage stress away from the discrete components? Minimizing by
adding a multiplier stack is also ok, check what options there are. We have dealt with spark gaps for this reason but
that adds serious complexity."

The metric: the largest voltage any DISCRETE part sees (a diode's reverse voltage, a fixed capacitor's voltage) over
one cycle of the growing mode, divided by
  (i) the varicap nodes' peak (the HV the vane gaps carry), and
  (ii) the system's highest node voltage (the HV the machine makes).
Under linear growth every voltage scales alike, so the ratios are the design's stress fractions [OC].

The topologies (each ideal diodes, the tube's air values of S1, both varicaps in antiphase as S0):
  T0  the S0 core (de Queiroz Fig. 1);
  T1  the S0 core with each diode a string of n sticks: the reference "do nothing" option (ratios / n per stick);
  T2  the two-phase Dickson generalisation of Fig. 1 [IR: this script's construction; Fig. 1 is its N = 1 member,
      in the spirit of the paper's "family using two-phase voltage multipliers", its ref. 26]: each varicap node is
      fed from REF by a chain of 2N diodes whose intermediate nodes are coupled alternately to the other varicap and
      to its own; the HV stays on the varicaps, the chain divides it among the diodes;
  T3  the S0 core plus a Cockcroft-Walton (Villard cascade) of M stages on each varicap node: the HV moves onto the
      ladder's top (e.g. the rings), the core runs at a fraction of it;
  T4  spark gaps: not run (the designer's complexity objection; the record's disc machine, efficiency-resolution).

The solver: quasi-static charge conservation with ideal diodes, the LCP solved as non-negative least squares
(P = B^T K^-1 B = A^T A with A = L^T B, K^-1 = L L^T; the KKT conditions of min ||A q + L^T Q|| over q >= 0 are
exactly the LCP) [OC]. It reproduces sim/queiroz_matrix.py on T0 (checked below).

Writes rebuild/s1_tube/s1_stress_options_results.json.
Usage: python3 rebuild/s1_tube/s1_stress_options.py
"""
import json
import os

import numpy as np
from scipy.optimize import nnls

HERE = os.path.dirname(os.path.abspath(__file__))
CMIN, CMAX, CA = 128.4, 450.6, 495.0           # pF, S1's air values (s1-bare-findings.md inputs)
AL, BE = CMAX / CMIN, CA / CMIN
N_HALF, CYCLES = 1500, 28


class Circuit:
    """nodes 1..n (0 = REF); caps (a, b, value or callable of s); diodes (anode, cathode); varicap nodes."""

    def __init__(self, name, n, caps, diodes, var_nodes):
        self.name, self.n, self.caps, self.diodes, self.var_nodes = name, n, caps, diodes, var_nodes
        self.B = np.zeros((n, len(diodes)))
        for k, (a, c) in enumerate(diodes):
            if c:
                self.B[c - 1, k] += 1
            if a:
                self.B[a - 1, k] -= 1

    def K(self, s):
        K = np.zeros((self.n, self.n))
        for a, b, c in self.caps:
            c = c(s) if callable(c) else c
            for i, j, sg in ((a, a, 1), (b, b, 1), (a, b, -1), (b, a, -1)):
                if i and j:
                    K[i - 1, j - 1] += sg * c
        return K

    def step(self, Kn, Q):
        Ki = np.linalg.inv(Kn)
        L = np.linalg.cholesky(Ki)
        A = L.T @ self.B
        q, _ = nnls(A, -(L.T @ Q), maxiter=50 * self.B.shape[1])
        return Ki @ (Q + self.B @ q)


def c1(s):
    return CMIN * (AL - (AL - 1) * s)


def c2(s):
    return CMIN * (1 + (AL - 1) * s)


def t2_dickson(N, cc=CA):
    """T2: varicaps on nodes P = 1 and Q = 2; chain to P: REF -> a1 -> ... -> a_{2N-1} -> P, a_k coupled to Q (k odd)
    or P (k even); the mirror chain to Q: b_k coupled to P (k odd) or Q (k even). N = 1 is Fig. 1."""
    P, Qn = 1, 2
    m = 2 * N - 1
    a = list(range(3, 3 + m))
    b = list(range(3 + m, 3 + 2 * m))
    caps = [(P, 0, c1), (Qn, 0, c2)]
    diodes = []
    for chain, top, other in ((a, P, Qn), (b, Qn, P)):
        prev = 0
        for k, x in enumerate(chain, start=1):
            caps.append((x, other if k % 2 else top, cc))
            diodes.append((prev, x))
            prev = x
        diodes.append((prev, top))
    return Circuit(f"T2 Dickson N={N}", 2 + 2 * m, caps, diodes, (P, Qn))


def t3_cw(M, cc=CA):
    """T3: the Fig. 1 core (nodes 1-4) plus a Villard/Cockcroft-Walton ladder of M stages on node 1 and on node 4:
    oscillating column node1 - o1 - o2 ..., smoothing column REF - s1 - s2 ...; diodes REF->o1, o1->s1, s1->o2, ..."""
    caps = [(1, 0, c1), (4, 0, c2), (1, 2, CA), (3, 4, CA)]
    diodes = [(0, 2), (0, 3), (3, 1), (2, 4)]
    nxt = 5
    tops = []
    for drive in (1, 4):
        o = list(range(nxt, nxt + M)); nxt += M
        sm = list(range(nxt, nxt + M)); nxt += M
        prev_o, prev_s = drive, 0
        for i in range(M):
            caps.append((prev_o, o[i], cc)); caps.append((prev_s, sm[i], cc))
            diodes.append((prev_s, o[i])); diodes.append((o[i], sm[i]))
            prev_o, prev_s = o[i], sm[i]
        tops.append(sm[-1])
    c = Circuit(f"T3 core + CW M={M}", nxt - 1, caps, diodes, (1, 4))
    c.tops = tops
    return c


def run(c, seed=None):
    """power iteration over whole cycles; then one traced cycle for the stress ratios."""
    v = np.zeros(c.n)
    for p in c.var_nodes:
        v[p - 1] = 1.0
    if seed is not None:
        v = seed
    v = c.step(c.K(0.0), c.K(0.0) @ v)
    zs = []
    for _ in range(CYCLES):
        v = v / np.abs(v).max()
        v0 = v.copy()
        for s0, s1 in zip(np.r_[np.linspace(0, 1, N_HALF + 1)[:-1], np.linspace(1, 0, N_HALF + 1)[:-1]],
                          np.r_[np.linspace(0, 1, N_HALF + 1)[1:], np.linspace(1, 0, N_HALF + 1)[1:]]):
            v = c.step(c.K(s1), c.K(s0) @ v)
        zs.append(float(np.abs(v).max() / np.abs(v0).max()))
    # trace one more cycle
    R = []
    for s0, s1 in zip(np.r_[np.linspace(0, 1, N_HALF + 1)[:-1], np.linspace(1, 0, N_HALF + 1)[:-1]],
                      np.r_[np.linspace(0, 1, N_HALF + 1)[1:], np.linspace(1, 0, N_HALF + 1)[1:]]):
        v = c.step(c.K(s1), c.K(s0) @ v)
        R.append(v.copy())
    R = np.array(R)
    R = R / zs[-1] ** np.linspace(0, 1, len(R))[:, None]       # undo the growth within the cycle [OC]

    def nv(x):
        return np.zeros(len(R)) if x == 0 else R[:, x - 1]
    v_var = max(np.abs(nv(p)).max() for p in c.var_nodes)
    v_sys = np.abs(R).max()
    d_rev = [float((nv(cth) - nv(a)).max()) for a, cth in c.diodes]
    c_fix = [float(np.abs(nv(a) - nv(b)).max()) for a, b, cv in c.caps if not callable(cv)]
    swing = [float((np.abs(nv(p)).max() - np.abs(nv(p)).min()) / np.abs(nv(p)).max()) for p in c.var_nodes]
    out = dict(name=c.name, nodes=c.n, n_diodes=len(c.diodes), n_fixed_caps=len(c_fix), z_cycle=zs[-1],
               z_converged=abs(zs[-1] / zs[-2] - 1) < 1e-4, varicap_peak=float(v_var), system_peak=float(v_sys),
               system_over_varicap=float(v_sys / v_var), varicap_swing_pp_over_peak=swing,
               diode_max_over_varicap=max(d_rev) / v_var, diode_max_over_system=max(d_rev) / v_sys,
               cap_max_over_varicap=max(c_fix) / v_var, cap_max_over_system=max(c_fix) / v_sys,
               diode_rev_over_varicap=[x / v_var for x in d_rev], cap_over_varicap=[x / v_var for x in c_fix])
    if hasattr(c, "tops"):
        out["ladder_top_over_varicap"] = float(max(np.abs(nv(t)).max() for t in c.tops) / v_var)
    return out


def main():
    res = dict(inputs=dict(Cmin_pF=CMIN, Cmax_pF=CMAX, Ca_pF=CA, N_half=N_HALF, cycles=CYCLES,
                           source="rebuild/s1_tube/s1-bare-findings.md (air, 3-D values)"), rows=[])

    def show(r):
        print(f"{r['name']:24s} z {r['z_cycle']:.5f}{'' if r['z_converged'] else ' (not converged)'}  "
              f"diodes {r['n_diodes']:2d} caps {r['n_fixed_caps']:2d}  sys/var {r['system_over_varicap']:.3f}  "
              f"max diode {r['diode_max_over_varicap']:.3f} var / {r['diode_max_over_system']:.3f} sys  "
              f"max cap {r['cap_max_over_varicap']:.3f} var / {r['cap_max_over_system']:.3f} sys")
        res["rows"].append(r)

    for N in (1, 2, 3, 4):
        show(run(t2_dickson(N)))
    for f in (0.5, 2.0, 4.0):                                   # the coupling capacitors' size, N = 2 and 3
        for N in (2, 3):
            r = run(t2_dickson(N, cc=f * CMAX)); r["name"] += f" Cc={f:g}Cmax"; show(r)
    for M in (1, 2, 4):
        show(run(t3_cw(M)))
    res["T1_series_strings"] = "each diode a string of n sticks: every ratio of T0 divided by n per stick [OC]"
    json.dump(res, open(os.path.join(HERE, "s1_stress_options_results.json"), "w"), indent=1)


if __name__ == "__main__":
    main()
