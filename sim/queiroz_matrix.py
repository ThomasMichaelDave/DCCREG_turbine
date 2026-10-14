"""sim/queiroz_matrix.py -- de Queiroz's segment-matrix solver, checked against the paper and against an independent
ideal-diode solver, and generalised as a basis for future solvers.

Source [OC]: A. C. M. de Queiroz, "Analysis of Electronic Electrostatic Generators", the author's manuscript,
docs/reference/deQueiroz-2019-analysis-electronic-electrostatic-generators.pdf (provenance: docs/reference/README.md).

What it checks:
  A. The paper's closed forms, transcribed from the PDF:
     - Fig. 3 (Wilson / symmetrical bipolar): the half-cycle matrix M (eq. 11), its eigenvalues (eqs. 12-13) and the
       eigenvector ratio (eq. 14);
     - Fig. 1 (symmetrical unipolar, the repo's doubler): the segment solutions (eqs. 19-21) and the Newton-Raphson
       solve of the generalised eigenproblem (eqs. 22-23).
  B. An independent solver that needs no segment order: quasi-static charge conservation with ideal diodes, stepped in
     the capacitance. At each step the node charges carried from the last step are conserved (C_new v = Q + B q) and
     the diodes solve a linear complementarity problem (q >= 0, B^T v >= 0, q . B^T v = 0) [OC]. On top of it:
     - power iteration over whole cycles (the startup mode, z per cycle);
     - the paper's eq. 22 with a numerical half-cycle map F and a finite-difference Jacobian (the generalised
       eigenproblem for any topology).
  C. The paper's two numbers that the repo had misread (see the findings): the notation of z, and the source of 1.1538.

Units: the method is scale-invariant in C and in V [OC: ideal diodes, linear capacitors], so C is in units of C_min
and V is normalised.

Writes sim/queiroz_matrix_results.json.
Usage: python3 sim/queiroz_matrix.py
"""
import itertools
import json
import math
import os

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
PDF = "docs/reference/deQueiroz-2019-analysis-electronic-electrostatic-generators.pdf"
NN = 4                                      # nodes 1..4; 0 is the reference

# The paper's printed values [OC: the PDF, eqs. 13, 14 and after 23]
PAPER = dict(
    fig3=dict(alpha=6.0, beta=5.5, sqrt_z=(0.808875, -1.15155), e41_over_e11=-1.38254),
    fig1=dict(alpha=6.0, beta=5.5, sqrt_z=1.17138, a=0.159674, b=2.24117, newton_start=(1.0, 2.0, 3.0)),
    fig6=dict(z_predicted=1.1538, z_measured_approx=1.08, probe_pF=82.0),
)


# ---------------------------------------------------------------------------------------------------------------------
# Circuits. s in [0, 1] runs phase 1 -> phase 2 (the first half cycle); the second half runs s back 1 -> 0.
# A diode is (anode, cathode). [OC: the PDF, Figs. 1 and 3, and the restrictions under eqs. 6-8, 16-18]
# ---------------------------------------------------------------------------------------------------------------------
def fig1(alpha, beta, polarity=+1):
    """The symmetrical unipolar generator: C1 (1-0) and C2 (4-0) variable, Ca (1-2) = Cb (3-4) = beta, fixed.
    Phase 1: C1 = alpha, C2 = 1. Paper diodes D1 0->2, D2 0->3, D3 3->1, D4 2->4; polarity -1 reverses all four
    (the repo's D1 2->0, D2 3->0, D3 1->3, D4 4->2: the same circuit at negative polarity)."""
    def caps(s):
        return [(1, 0, alpha - (alpha - 1) * s), (4, 0, 1 + (alpha - 1) * s), (1, 2, beta), (3, 4, beta)]
    d = [(0, 2), (0, 3), (3, 1), (2, 4)]
    return dict(name="fig1", caps=caps, diodes=d if polarity > 0 else [(c, a) for a, c in d])


def fig3(alpha, beta):
    """The symmetrical bipolar (Wilson) generator: Ca (1-2) and Cb (3-4) variable, C1 (1-0) = C2 (4-0) = beta.
    Phase 1: Ca = alpha, Cb = 1. Diodes D1 2->0, D2 0->3, D3 3->1, D4 4->2 [IR: read from the drawing; the run's
    agreement with eqs. 13-14 confirms the reading]."""
    def caps(s):
        return [(1, 0, beta), (4, 0, beta), (1, 2, alpha - (alpha - 1) * s), (3, 4, 1 + (alpha - 1) * s)]
    return dict(name="fig3", caps=caps, diodes=[(2, 0), (0, 3), (3, 1), (4, 2)])


def kmat(caps):
    """The nodal capacitance matrix (nodes 1..NN; node 0 dropped) [OC]."""
    K = np.zeros((NN, NN))
    for a, b, c in caps:
        for i, j, sg in ((a, a, 1), (b, b, 1), (a, b, -1), (b, a, -1)):
            if i and j:
                K[i - 1, j - 1] += sg * c
    return K


def bmat(diodes):
    """Diode incidence: forward charge q_k moves from the anode to the cathode; B^T v = v_cathode - v_anode >= 0
    is reverse bias [OC]."""
    B = np.zeros((NN, len(diodes)))
    for k, (a, c) in enumerate(diodes):
        if c:
            B[c - 1, k] += 1
        if a:
            B[a - 1, k] -= 1
    return B


# ---------------------------------------------------------------------------------------------------------------------
# B. The independent solver: charge conservation + ideal diodes as an LCP
# ---------------------------------------------------------------------------------------------------------------------
_SUBSETS = [S for r in range(5) for S in itertools.combinations(range(4), r)]


def lcp_step(K, Q, B, guess=()):
    """Solve K v = Q + B q with q >= 0, w = B^T v >= 0, q.w = 0 [OC: ideal diodes; the LCP w = r + P q with
    P = B^T K^-1 B positive semidefinite, so w and v are unique]. Tries the last active set first, then all 16."""
    Ki = np.linalg.inv(K)
    r = B.T @ Ki @ Q
    P = B.T @ Ki @ B
    scale = max(1e-300, float(np.abs(Ki @ Q).max()))
    for S in [tuple(guess)] + _SUBSETS:
        q = np.zeros(B.shape[1])
        if S:
            idx = list(S)
            q[idx] = np.linalg.solve(P[np.ix_(idx, idx)], -r[idx])
        w = r + P @ q
        if q.min() >= -1e-12 * scale * np.abs(P).max() and w.min() >= -1e-11 * scale:
            return Ki @ (Q + B @ q), tuple(i for i in S if q[i] > 0)
    raise RuntimeError("LCP: no consistent diode state")


def half_cycle(circ, v, n, forward=True, trace=None):
    """March s over one half cycle in n steps from the node voltages v (already consistent at the start)."""
    B = bmat(circ["diodes"])
    s_grid = np.linspace(0, 1, n + 1) if forward else np.linspace(1, 0, n + 1)
    act = ()
    for s0, s1 in zip(s_grid[:-1], s_grid[1:]):
        Q = kmat(circ["caps"](s0)) @ v                  # the node charges just before the step [OC]
        v, act = lcp_step(kmat(circ["caps"](s1)), Q, B, act)
        if trace is not None:
            trace.append((float(s1), act))
    return v


def settle(circ, v, s):
    """Make an arbitrary seed consistent with the diodes at s (charge-conserving)."""
    K = kmat(circ["caps"](s))
    return lcp_step(K, K @ v, bmat(circ["diodes"]))[0]


def power_iteration(circ, n, cycles=40, seed=(1.0, 0.0, 0.0, 1.0)):
    """Whole cycles from a seed on C1 / C2's nodes (as sim/queiroz_fig1_check.py seeds ngspice), normalised each
    cycle; returns z per cycle and the phase-1 eigenvector [OC: the dominant growing mode of a positively
    homogeneous map]."""
    v = settle(circ, np.array(seed, float), 0.0)
    zs = []
    for _ in range(cycles):
        v0 = v / np.abs(v).max()
        vh = half_cycle(circ, v0, n, True)
        v1 = half_cycle(circ, vh, n, False)
        zs.append(float(np.abs(v1).max() / np.abs(v0).max()))
        v = v1
    v0 = v / v[0]
    vh = half_cycle(circ, v0.copy(), n, True)
    return dict(z_cycle=zs[-1], z_history=zs[-6:], e_phase1=v0.tolist(), e_phase2=vh.tolist())


def half_cycle_map_fig1(e, n):
    """F of the paper's eq. 22 for Fig. 1, numerically: (e11, e21, e41) -> (e22, e32, e12) [OC: eq. 15]; phase 1
    has e31 = e11 (D3 conducting)."""
    c = fig1(PAPER["fig1"]["alpha"], PAPER["fig1"]["beta"])
    e11, e21, e41 = e
    v = half_cycle(c, np.array([e11, e21, e11, e41]), n)
    return np.array([v[1], v[2], v[0]])


def newton_generalised_eig(F, x0, h=1e-7, tol=1e-12, itmax=30):
    """Solve G(x) = F([1, a, b]) - r [1, a, b] = 0 for x = [r, a, b] (r = sqrt z) by Newton-Raphson with a
    finite-difference Jacobian [OC: the paper's eqs. 22-23]."""
    def G(x):
        r, a, b = x
        u = np.array([1.0, a, b])
        return F(u) - r * u
    x = np.array(x0, float)
    hist = []
    for _ in range(itmax):
        g = G(x)
        J = np.column_stack([(G(x + h * np.eye(3)[k]) - g) / h for k in range(3)])
        dx = np.linalg.solve(J, -g)
        x = x + dx
        hist.append(float(np.abs(dx).max()))
        if hist[-1] < tol:
            break
    return x, hist


# ---------------------------------------------------------------------------------------------------------------------
# A. The paper's closed forms, transcribed from the PDF
# ---------------------------------------------------------------------------------------------------------------------
def fig3_M(al, be):
    """Eq. 11: [e12, e22] = M [e41, e11]."""
    return np.array([[be + 1, al ** 2 + 2 * al * be + be ** 2 + be - 1],
                     [(be + 1) ** 2, -(al * be + 1)]]) / (al * (be + 1) + be * (be + 2))


def fig3_sqrtz(al, be):
    """Eq. 12."""
    rt = math.sqrt(al ** 2 * (5 * be ** 2 + 8 * be + 4) + 2 * al * be * (4 * be ** 2 + 9 * be + 6)
                   + be ** 2 * (4 * be ** 2 + 12 * be + 9))
    den = 2 * (al * (be + 1) + be * (be + 2))
    return ((-be * (al - 1) + rt) / den, (-be * (al - 1) - rt) / den)


def fig3_ratio(al, be):
    """Eq. 14 (the PDF prints only the + root)."""
    rt = math.sqrt(al ** 2 * (5 * be ** 2 + 8 * be + 4) + 2 * al * be * (4 * be ** 2 + 9 * be + 6)
                   + be ** 2 * (4 * be ** 2 + 12 * be + 9))
    return (-al * be - be - 2 + rt) / (2 * (be + 1) ** 2), (-al * be - be - 2 - rt) / (2 * (be + 1) ** 2)


def fig1_eq21(e, al, be):
    """Eq. 21: (e11, e21, e41) -> (e22, e32, e12), with gamma = beta + 1, lambda = alpha + beta + 1 and the root of
    eq. 20."""
    e11, e21, e41 = e
    g, la = be + 1, al + be + 1
    R = math.sqrt(e11 ** 2 * (1 - 4 * al * be) + 2 * e11 * (e41 * g * (2 * al + 1) - e21 * la)
                  + e21 ** 2 * (al ** 2 + 2 * al * g + g ** 2) - 2 * e21 * e41 * la * g + e41 ** 2 * g ** 2)
    den = 2 * la * (al * g + be)
    e12 = -(-e11 * (2 * al ** 3 + 2 * al ** 2 * (3 * be + 1) + 2 * al * be * (be + 2) - be ** 2)
            + be * (e21 * (2 * al ** 2 + al * (3 * be + 2) + be * g) - e41 * g * (2 * al + be + 2))
            + be ** 2 * R) / den
    e22 = -(-e11 * be * (2 * al ** 2 - 2 * al - 3 * g) + e21 * be * la * (be - 1) - e41 * g ** 2 * (2 * al + be + 2)
            + be * g * R) / den
    e32 = -(-e11 * (2 * al ** 2 * be + al * (2 * be ** 2 + be + 1) - be * (be + 2))
            + e21 * (al ** 2 * g + al * (2 * be ** 2 + 2 * be + 1) + be ** 2 * g)
            - e41 * g * (al * g + be ** 2 + 2 * be + 2)
            + (al * g + be * (be + 2)) * R) / den
    return np.array([e22, e32, e12])


def fig1_eq19(e, al):
    """Eq. 19, the first segment (phase 1 -> x): returns C2x (in C_min), e1x, e2x, e4x."""
    e11, e21, e41 = e
    return dict(C2x=e41 / (e41 - e11), e1x=e11 * al * (e11 - e41) / (e11 * (al + 1) - e41 * al),
                e2x=(e11 ** 2 + e11 * e21 * (al + 1) + e21 * e41 * al) / (e41 * al - e11 * (al + 1)), e4x=e41 - e11)


# ---------------------------------------------------------------------------------------------------------------------
def main():
    al, be = PAPER["fig1"]["alpha"], PAPER["fig1"]["beta"]
    out = dict(source=PDF, paper=PAPER, units="C in C_min; V normalised (the ideal method is scale-invariant) [OC]")

    # --- Fig. 3: closed form vs eigen-decomposition vs the independent solver
    M = fig3_M(al, be)
    lam, vec = np.linalg.eig(M)
    cf = fig3_sqrtz(al, be)
    ratio_cf = fig3_ratio(al, be)
    pi3 = {n: power_iteration(fig3(al, be), n) for n in (500, 2000)}
    p3 = pi3[2000]
    out["fig3"] = dict(
        eq12_sqrt_z=list(cf), eig_of_eq11_M=sorted(lam.real.tolist()),
        eq14_ratio_roots=list(ratio_cf),
        eig_vector_ratio={"%.6f" % lam[k].real: float((vec[0, k] / vec[1, k]).real) for k in range(2)},
        solver=dict(n_per_half={n: r["z_cycle"] for n, r in pi3.items()},
                    z_cycle=p3["z_cycle"], sqrt_z=math.sqrt(p3["z_cycle"]),
                    e41_over_e11=p3["e_phase1"][3] / p3["e_phase1"][0],
                    e21_phase1=p3["e_phase1"][1], e31_over_e11=p3["e_phase1"][2] / p3["e_phase1"][0],
                    e_phase1=p3["e_phase1"], e_phase2=p3["e_phase2"]))

    # --- Fig. 1: eq. 21 + Newton (the paper's route) vs the independent solver (power iteration and numerical Newton)
    x_cf, hist_cf = newton_generalised_eig(lambda u: fig1_eq21(u, al, be), PAPER["fig1"]["newton_start"])
    pi1 = {n: power_iteration(fig1(al, be), n) for n in (500, 2000, 8000)}
    p1 = pi1[8000]
    e1 = np.array(p1["e_phase1"])
    x_num, hist_num = newton_generalised_eig(lambda u: half_cycle_map_fig1(u, 4000),
                                             [math.sqrt(p1["z_cycle"]), e1[1], e1[3]], h=1e-6, tol=1e-10)
    neg = power_iteration(fig1(al, be, polarity=-1), 2000, seed=(-1.0, 0.0, 0.0, -1.0))
    # eq. 21 vs the stepped half cycle at the eigenvector and at an arbitrary point
    probe = np.array([1.0, 0.3, 2.0])
    trace = []
    half_cycle(fig1(al, be), np.array([x_cf[0] * 0 + 1.0, x_cf[1], 1.0, x_cf[2]]), 8000, trace=trace)
    seq, last = [], None
    for s, act in trace:
        if act != last:
            seq.append(dict(s=round(s, 4), conducting=["D%d" % (k + 1) for k in act]))
            last = act
    out["fig1"] = dict(
        eq21_newton=dict(sqrt_z=x_cf[0], a=x_cf[1], b=x_cf[2], z_cycle=x_cf[0] ** 2, steps=hist_cf),
        eq19_at_eigvec=fig1_eq19((1.0, x_cf[1], x_cf[2]), al),
        eq21_vs_stepped_at_probe=dict(probe=probe.tolist(), eq21=fig1_eq21(probe, al, be).tolist(),
                                      stepped=half_cycle_map_fig1(probe, 8000).tolist()),
        solver_power=dict(n_per_half={n: r["z_cycle"] for n, r in pi1.items()}, z_cycle=p1["z_cycle"],
                          sqrt_z=math.sqrt(p1["z_cycle"]), a=e1[1], b=e1[3], e_phase1=p1["e_phase1"],
                          e_phase2=p1["e_phase2"], half_cycle_check=[p1["e_phase2"][1], p1["e_phase2"][2],
                                                                     p1["e_phase2"][0]]),
        solver_newton=dict(sqrt_z=x_num[0], a=x_num[1], b=x_num[2], steps=hist_num),
        repo_negative_polarity=dict(z_cycle=neg["z_cycle"], e_phase1=neg["e_phase1"]),
        diode_sequence_half_cycle=seq,
        ngspice_record=dict(file="sim/queiroz_fig1_check_results.json", **{
            k: v["z_late"] for k, v in json.load(open(os.path.join(HERE, "queiroz_fig1_check_results.json")))
            ["rows"].items() if "z_late" in v}))

    # --- Fig. 6: which reading gives the printed 1.1538? [RH: the paper states only "C_min is then ~60+82 pF"]
    reads = {}
    for name, (cmin, cmax, ca) in {"probe on C1, C2: 142-442, Ca 330": (142, 442, 330),
                                   "probe on C_min only: 142-360, Ca 330": (142, 360, 330)}.items():
        a6, b6 = cmax / cmin, ca / cmin
        x6, _ = newton_generalised_eig(lambda u: fig1_eq21(u, a6, b6), [1.1, x_cf[1], x_cf[2]])
        reads[name] = dict(alpha=a6, beta=b6, sqrt_z=x6[0], z_cycle=x6[0] ** 2)
    out["fig6"] = reads

    json.dump(out, open(os.path.join(HERE, "queiroz_matrix_results.json"), "w"), indent=1, default=float)

    f3, f1 = out["fig3"], out["fig1"]
    print("Fig. 3  eq.12 sqrt z", ["%.6f" % v for v in f3["eq12_sqrt_z"]], " eig(M eq.11)",
          ["%.6f" % v for v in f3["eig_of_eq11_M"]])
    print("        eq.14 ratio roots", ["%.5f" % v for v in f3["eq14_ratio_roots"]],
          " solver z %.6f sqrt %.6f e41/e11 %.5f" % (f3["solver"]["z_cycle"], f3["solver"]["sqrt_z"],
                                                    f3["solver"]["e41_over_e11"]))
    print("Fig. 1  eq.21+Newton sqrt z %.6f a %.6f b %.5f" % (x_cf[0], x_cf[1], x_cf[2]))
    print("        solver power  sqrt z %.6f a %.6f b %.5f  (z/cycle by n: %s)" % (
        f1["solver_power"]["sqrt_z"], f1["solver_power"]["a"], f1["solver_power"]["b"],
        {n: round(v, 6) for n, v in f1["solver_power"]["n_per_half"].items()}))
    print("        solver Newton sqrt z %.6f a %.6f b %.5f" % tuple(x_num))
    print("        repo polarity z %.6f" % neg["z_cycle"], " ngspice", f1["ngspice_record"])
    print("        eq21 vs stepped at probe", f1["eq21_vs_stepped_at_probe"])
    print("        diode sequence", seq)
    for k, v in reads.items():
        print("Fig. 6 ", k, " sqrt z %.5f  z %.5f" % (v["sqrt_z"], v["z_cycle"]))


if __name__ == "__main__":
    main()
