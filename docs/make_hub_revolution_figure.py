"""docs/make_hub_revolution_figure.py -- writes docs/figures/hub-rings-revolution.png: the rings' supply of record over one
revolution of the rotor (sim/hub_revolution.py -> sim/hub_revolution_results.json). The question: does the field at the
null swing as the pump goes through its phases?
  (a) the pump's phases: C1(theta) and C2(theta), half a cycle apart, twelve times a revolution;
  (b) the pump's nodes 1 and 4, which drive ring A's and ring B's chains;
  (c) the chains: the oscillating nodes swing a stage each, while the smoothing nodes and the rings hold;
  (d) the field at the null on its full scale, both directions: it never leaves B to A;
  (e) the same field magnified: the ripple.
Usage: python3 docs/make_hub_revolution_figure.py
"""
import json
import os

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt                                   # noqa: E402
import numpy as np                                                # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
SIM = os.path.join(HERE, "..", "sim")
SURF, INK, INK2, MUTED, GRID, AXIS = "#fcfcfb", "#0b0b0b", "#52514e", "#898781", "#e1e0d9", "#c3c2b7"
C_A, C_B = "#c0392b", "#1f6fb2"                                  # ring A / node 1's side, ring B / node 4's side
# (validated as a pair: scripts/validate_palette.js; the chains' nodes differ by weight, dash and label, not shade)
OUT = os.path.join(HERE, "figures", "hub-rings-revolution.png")


def kvs(v, f="{:+.1f}"):
    v = 0.0 if abs(v) < 0.5 * 10 ** -int(f.split(".")[1][0]) else v     # no "−0.0"
    return f.format(v).replace("-", "−").replace("+0.0", "0.0")


def style(ax, title, ylabel, xlabel=None):
    ax.set_facecolor(SURF)
    if title:
        ax.set_title(title, fontsize=9.6, loc="left", color=INK)
    ax.set_ylabel(ylabel, fontsize=8.3, color=INK2)
    if xlabel:
        ax.set_xlabel(xlabel, fontsize=8.3, color=INK2)
    ax.grid(True, color=GRID, lw=0.6)
    ax.set_axisbelow(True)
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)
    for s in ("left", "bottom"):
        ax.spines[s].set_color(AXIS)
    ax.tick_params(colors=INK2, labelsize=7.8)


def main():
    D = json.load(open(os.path.join(SIM, "hub_revolution_results.json")))
    S = D["summary"]
    x = np.array(D["rotor_deg"])
    V = {k: np.array(v) for k, v in D["V_kV"].items()}
    e = np.array(D["E_kV_cm"])
    fig = plt.figure(figsize=(14.0, 13.6), facecolor="white")
    gs = fig.add_gridspec(5, 1, height_ratios=(0.8, 0.8, 1.7, 1.0, 0.8), hspace=0.42, left=0.065, right=0.80,
                          top=0.905, bottom=0.05)
    fig.suptitle(f"One revolution of the rotor: the pump goes through its phases {D['n_cycles']} times, and the field "
                 f"at the null stays {S['E_kV_cm']['mean']:.2f} kV/cm from B to A", fontsize=12.2, x=0.01, ha="left",
                 color=INK)
    fig.text(0.01, 0.925, f"sim/hub_revolution.py: the supply of record in ngspice (the symmetric pair, "
             f"{D['record']['n_a']} + {D['record']['n_cw']} stages, 100 pF, 100 GΩ per ring), settled over "
             f"{D['n_settle']} cycles, then one revolution at {D['rpm_each']:.0f} rpm each way "
             f"({D['n_cycles']} × {D['F_Hz']:.0f} Hz cycles, {1e3 * D['n_cycles'] / D['F_Hz']:.0f} ms).\nThe field at the "
             f"null: k (V_B − V_A), k = {D['k_kV_cm_per_kV']:.4f} (kV/cm)/kV; the hub's insulators relax over minutes, "
             "so at 120 Hz the field follows the rings.", fontsize=8.4, color=INK2, linespacing=1.4)
    xlab = "the rotor's angle over one revolution (deg); the six vanes pass twelve times, every 30°"
    axes = [fig.add_subplot(gs[i]) for i in range(5)]
    for ax in axes[1:]:
        ax.sharex(axes[0])

    # (a) the pump's phases
    ax = axes[0]
    ax.plot(x, D["C1_pF"], color=C_A, lw=1.6, label="C1(θ), on node 1")
    ax.plot(x, D["C2_pF"], color=C_B, lw=1.6, label="C2(θ), on node 4")
    style(ax, "(a) the pump's phases: the varicaps C1 and C2, half a cycle apart", "pF")
    ax.legend(fontsize=7.4, frameon=False, loc="upper left", bbox_to_anchor=(1.005, 1.0))

    # (b) the pump's nodes
    ax = axes[1]
    ax.plot(x, V["1"], color=C_A, lw=1.6, label="node 1 → ring A's chain")
    ax.plot(x, V["4"], color=C_B, lw=1.6, label="node 4 → ring B's chain")
    style(ax, f"(b) the pump's nodes swing {kvs(S['V1_kV']['min'], '{:.1f}')} ↔ {kvs(S['V1_kV']['max'], '{:.1f}')} kV, "
              "half a cycle apart", "kV")
    ax.set_ylim(-15, 0)
    ax.legend(fontsize=7.4, frameon=False, loc="upper left", bbox_to_anchor=(1.005, 1.0))

    # (c) the chains: oscillating nodes swing a stage each; smoothing nodes and the rings hold
    ax = axes[2]
    rows = (("eb", C_B, 2.8, "-", "ring B"), ("m2", C_B, 0.9, "-", "m2, oscillating"),
            ("b1", C_B, 1.8, (0, (6, 2)), "b1, smoothing"), ("m1", C_B, 0.9, (0, (1.5, 1.5)), "m1, oscillating"),
            ("n1", C_A, 0.9, (0, (1.5, 1.5)), "n1, oscillating"), ("a1", C_A, 1.8, (0, (6, 2)), "a1, smoothing"),
            ("n2", C_A, 0.9, "-", "n2, oscillating"), ("ea", C_A, 2.8, "-", "ring A"))
    for nd, col, lw, ls, lab in rows:
        if nd in V:
            f_ = "{:+.2f}" if nd in ("ea", "eb") else "{:+.1f}"
            ax.plot(x, V[nd], color=col, lw=lw, ls=ls, label=f"{lab}: {kvs(V[nd].min(), f_)} … {kvs(V[nd].max(), f_)}")
    ax.axhline(0, color=INK, lw=1.0)
    ax.text(x[-1] * 0.995, 0.6, "the shaft, 0 V: both chains stand on it", fontsize=7.4, color=INK, ha="right")
    for nd, txt in (("eb", f"ring B {kvs(S['V_B_kV']['mean'], '{:+.2f}')} kV, {1e3 * S['V_B_kV']['pp']:.0f} V p-p"),
                    ("ea", f"ring A {kvs(S['V_A_kV']['mean'], '{:+.2f}')} kV, {1e3 * S['V_A_kV']['pp']:.0f} V p-p")):
        ax.text(x[0] + 2, V[nd].mean() + (0.7 if nd == "eb" else -1.6), txt, fontsize=7.6, color=INK, weight="bold")
    style(ax, "(c) the chains: each oscillating node swings one stage (7.5 kV) with the pump; the smoothing nodes "
              "and the rings hold", "kV")
    ax.set_ylim(-17.5, 17.5)
    ax.legend(fontsize=7.2, frameon=False, loc="upper left", bbox_to_anchor=(1.005, 1.0))

    # (d) the field at the null on its full scale, both directions
    ax = axes[3]
    lim = 1.15 * float(np.abs(e).max())
    ax.axhspan(-lim, 0, color="#f3f1ec", zorder=0)
    ax.axhline(0, color=INK, lw=1.0)
    ax.plot(x, e, color="#0d366b", lw=2.0)
    ax.text(x[0] + 2, -0.5 * lim, "A to B: never reached", fontsize=7.8, color=INK2, va="center")
    ax.text(x[0] + 2, e.mean() - 0.17 * lim, f"B to A: {S['E_kV_cm']['min']:.3f} … {S['E_kV_cm']['max']:.3f} kV/cm, "
            f"{S['E_sign_changes']} sign changes", fontsize=7.8, color=INK, va="center")
    style(ax, "(d) the field at the null, on its full scale in both directions", "kV/cm")
    ax.set_ylim(-lim, lim)

    # (e) magnified: the ripple
    ax = axes[4]
    ax.plot(x, e, color="#0d366b", lw=1.5)
    style(ax, f"(e) the same field magnified: {S['E_kV_cm']['pp']:.4f} kV/cm p-p "
              f"({100 * S['E_kV_cm']['pp'] / S['E_kV_cm']['mean']:.2f} %), ring A then ring B topping up each cycle",
          "kV/cm", xlab)
    pad = 0.35 * S["E_kV_cm"]["pp"]
    ax.set_ylim(S["E_kV_cm"]["min"] - pad, S["E_kV_cm"]["max"] + pad)
    for ax in axes[:-1]:
        plt.setp(ax.get_xticklabels(), visible=False)
    axes[-1].set_xlim(x[0], x[-1] + (x[1] - x[0]))
    axes[-1].set_xticks(np.arange(0, 361, 30))
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    fig.savefig(OUT, dpi=130, facecolor="white")
    plt.close(fig)
    print(OUT)


if __name__ == "__main__":
    main()
