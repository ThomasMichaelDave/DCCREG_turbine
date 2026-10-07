"""docs/make_pole_drawing.py -- writes docs/figures/pole-pair-flux.png: the chosen reluctance pole pair in the plane of
rotation (unrolled at the gap radius), wound utron (rotor U-core) under two passive stator bridges, with the 2-D flux
lines (contours of A_z) aligned and unaligned, from sim/pole_fd2d.py.
Usage: python3 docs/make_pole_drawing.py [g_mm]
"""
import json
import os
import sys

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt                           # noqa: E402
from matplotlib.patches import Rectangle                  # noqa: E402
import numpy as np                                        # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "sim"))
import pole_fd2d as P                                     # noqa: E402

INK, MUTED, IRON, CU, FLUX = "#1d1d1f", "#6e6e73", "#9aa0a6", "#c8742a", "#1f6fb2"


def panel(ax, D, theta, title):
    s = P.solve(D, theta, return_field=True)
    x, y, A = s["x"], s["y"], s["A"]
    X = D.X
    xu = (D.r_g * np.radians(theta)) % X
    # show the periodic strip centred on the utron: x' = x - xu wrapped to [-X/2, X/2)
    xs = (x - xu + X / 2) % X - X / 2
    order = np.argsort(xs)
    xs, A = xs[order], A[order, :]

    def shift(r):
        out = []
        for sh in (-X, 0.0, X):
            a, b = r[0] - xu + sh, r[1] - xu + sh
            a, b = max(a, -X / 2), min(b, X / 2)
            if b > a:
                out.append((a, b, r[2], r[3]))
        return out
    sel_y = (y > -D.radial_depth() - 8) & (y < D.g + D.t_b + 12)
    lv = np.linspace(A.min(), A.max(), 26)[1:-1]
    for r in [p for q in D.stator_rects() for p in shift(q)]:
        ax.add_patch(Rectangle((r[0], r[2]), r[1] - r[0], r[3] - r[2], fc=IRON, ec="none", alpha=0.5))
    for r in [p for q in D.utron_rects(xu) for p in shift(q)]:
        ax.add_patch(Rectangle((r[0], r[2]), r[1] - r[0], r[3] - r[2], fc=IRON, ec="none", alpha=0.9))
    plus, minus, _ = D.coil_rects()
    for (a, b, c0, c1), lab in ((plus, "+"), (minus, "−")):
        ax.add_patch(Rectangle((a, c0), b - a, c1 - c0, fc=CU, ec="none", alpha=0.45))
        ax.text(0.5 * (a + b), 0.5 * (c0 + c1), lab, ha="center", va="center", color=INK, fontsize=11)
    ax.contour(xs, y[sel_y], A[:, sel_y].T, levels=lv, colors=FLUX, linewidths=0.8, linestyles="solid")
    ax.set_xlim(-120, 120)
    ax.set_ylim(y[sel_y].min(), y[sel_y].max())
    ax.set_aspect("equal")
    ax.set_title(title, color=INK, fontsize=11, loc="left")
    ax.set_xlabel("tangential, mm from the utron centre (unrolled at r_g)", color=MUTED, fontsize=9)
    ax.set_ylabel("radial, mm (gap face at 0)", color=MUTED, fontsize=9)
    ax.tick_params(colors=MUTED, labelsize=8)
    for sp in ax.spines.values():
        sp.set_color("#d2d2d7")


def main(g=0.5):
    fin = json.load(open(os.path.join(HERE, "..", "sim", "pole_design_final.json")))
    tag = "best g 0.5" if g == 0.5 else "g 0.5 geometry at 1.0 mm"
    d = fin["designs"][tag]["char"]["design"]
    D = P.Design(**d)
    fig, axs = plt.subplots(1, 2, figsize=(13, 5.6), facecolor="white")
    panel(axs[0], D, 0.0, f"aligned (θ 0): gap {D.g} mm")
    panel(axs[1], D, 30.0, "unaligned (θ 30°): utron between two bridges")
    fig.suptitle(f"Wound utron vs passive stator bridges — r_g {D.r_g:.0f} mm, tips {D.w_p:.0f} mm, slot {D.s:.0f} × {D.d:.0f} mm, "
                 f"stack {D.L_stk:.0f} mm, 6 bridges {D.l_b:.0f} × {D.t_b:.0f} mm per side", color=INK, fontsize=12, x=0.01, ha="left")
    fig.text(0.01, 0.01, "grey: laminated iron (utron dark, stator bridges light) · copper: utron coil (+ in the slot, − under the back iron) · "
             "blue: 2-D flux lines (equal flux between lines). Source: sim/pole_fd2d.py", color=MUTED, fontsize=8.5)
    fig.tight_layout(rect=(0, 0.06, 1, 0.94))
    os.makedirs(os.path.join(HERE, "figures"), exist_ok=True)
    out = os.path.join(HERE, "figures", f"pole-pair-flux-g{str(g).replace('.', 'p')}.png")
    fig.savefig(out, dpi=130)
    print(out)


if __name__ == "__main__":
    main(float(sys.argv[1]) if len(sys.argv) > 1 else 0.5)
