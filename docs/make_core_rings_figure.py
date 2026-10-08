"""docs/make_core_rings_figure.py -- writes docs/figures/core-rings.png: two electrode rings on the core's vessel as the
conductors for the pump's swing (sim/core_rings.py, sim/core_rings_results.json).
  (a) the hub's half-section with the equipotentials of A - B, for the case drawn (a 10 mm band at 50 deg, coils in);
  (b) the field at the centre at the pump's swing, over the rings' polar angle, for each ring form, coils in / out;
  (c) the rings' stray capacitance to the shaft side, and between the rings;
  (d) the pump's gain z with those strays.
Usage: python3 docs/make_core_rings_figure.py
"""
import json
import math
import os
import sys

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt                                   # noqa: E402
import numpy as np                                                # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
SIM = os.path.join(HERE, "..", "sim")
sys.path.insert(0, SIM)
import core_rings as CR                                           # noqa: E402

SURF, INK, INK2, MUTED, GRID, AXIS = "#fcfcfb", "#0b0b0b", "#52514e", "#898781", "#e1e0d9", "#c3c2b7"
RAMP3 = ("#86b6ef", "#3987e5", "#0d366b")                         # ordinal blue: the three ring forms, small to large
C_A, C_B, STEEL, GLASS, COMP, G10C = "#c0392b", "#1f6fb2", "#8a8f99", "#cfe3ee", "#e9e1c9", "#d7dccb"
OUT = os.path.join(HERE, "figures", "core-rings.png")
DRAWN = ("band 10 mm", 50.0, True)


def style(ax, title, ylabel):
    ax.set_facecolor(SURF)
    ax.set_title(title, fontsize=9.6, loc="left", color=INK)
    ax.set_ylabel(ylabel, fontsize=8.3, color=INK2)
    ax.grid(True, color=GRID, lw=0.6)
    ax.set_axisbelow(True)
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)
    for s in ("left", "bottom"):
        ax.spines[s].set_color(AXIS)
    ax.tick_params(colors=INK2, labelsize=7.8)


def section(ax, res):
    h = res["h_mm"]
    V, cond, eps = res["V_anti"], res["cond"], res["eps"]
    nr, nz = V.shape
    r = (np.arange(nr) + 0.5) * h
    z = (np.arange(nz) + 0.5) * h
    Vf = np.concatenate([-V[:, ::-1], V], axis=1)                 # the lower half: antisymmetric
    zf = np.concatenate([-z[::-1], z])
    cf = np.concatenate([cond[:, ::-1], cond], axis=1)
    ef = np.concatenate([eps[:, ::-1], eps], axis=1)
    R, Z = np.meshgrid(r, zf, indexing="ij")
    rho = np.hypot(R, Z)
    hub = CR.HUB
    img = np.ones(R.shape + (3,))
    def paint(mask, col):
        img[mask] = matplotlib.colors.to_rgb(col)
    paint((rho >= hub["R_in"]) & (rho < hub["R_v"]), GLASS)
    paint((rho >= hub["R_v"]) & (rho < hub["R_v"] + hub["t_ret"]), COMP)
    paint((ef > 4.0) & (rho > hub["R_v"] + hub["t_ret"]), G10C)
    paint(cf == 1, STEEL)
    paint((cf == 2) & (Z > 0), C_A)
    paint((cf == 2) & (Z < 0), C_B)
    ax.imshow(np.transpose(img, (1, 0, 2)), origin="lower", extent=(0, r[-1] + h / 2, zf[0] - h / 2, zf[-1] + h / 2),
              interpolation="nearest", zorder=1)
    Vm = np.ma.masked_where(cf != 0, Vf)
    ax.contour(R, Z, Vm, levels=np.linspace(-0.9, 0.9, 19), colors=INK2, linewidths=0.45, zorder=3,
               negative_linestyles="solid")
    ax.set_aspect("equal")
    ax.set_xlim(0, 100); ax.set_ylim(-88, 88)
    ax.set_xlabel("r (mm)", fontsize=8.3, color=INK2); ax.set_ylabel("z (mm)", fontsize=8.3, color=INK2)
    ax.tick_params(colors=INK2, labelsize=7.8)
    for s in ax.spines.values():
        s.set_color(AXIS)
    lab = dict(fontsize=7.2, color=INK, bbox=dict(fc="white", ec="none", pad=0.6, alpha=0.85), zorder=6)
    ax.annotate("ring A (on node 1\nthrough Cca)", (36, 30), (60, 62), arrowprops=dict(arrowstyle="-", lw=0.5), **lab)
    ax.annotate("ring B (node 4)", (36, -30), (58, -60), arrowprops=dict(arrowstyle="-", lw=0.5), **lab)
    ax.annotate("field coil (REF)", (50, 21), (70, 30), arrowprops=dict(arrowstyle="-", lw=0.5), **lab)
    ax.annotate("cone (G10)", (63, 12), (78, 6), arrowprops=dict(arrowstyle="-", lw=0.5), **lab)
    ax.annotate("flange, shaft,\nbearing (REF)", (20, 64), (40, 80), arrowprops=dict(arrowstyle="-", lw=0.5), **lab)
    ax.text(3, 3, "vacuum", fontsize=7.2, color=INK2, zorder=6)
    ax.text(30, -3, "vessel + retainer", fontsize=6.8, color=INK2, zorder=6, rotation=-62)
    ax.set_title("(a) the hub's half-section [RH placeholders]: a 10 mm band at 50°,\nequipotentials of A − B every 0.1",
                 fontsize=9.6, loc="left", color=INK)


def main():
    d = json.load(open(os.path.join(SIM, "core_rings_results.json")))
    rings = d["rings"]
    res = CR.solve(CR.RINGS[DRAWN[0]], DRAWN[1], DRAWN[2], d["h_mm"], keep=True)
    fig = plt.figure(figsize=(15.5, 8.6), facecolor="white")
    gs = fig.add_gridspec(2, 3, width_ratios=(1.05, 1, 1), hspace=0.42, wspace=0.28, left=0.05, right=0.985, top=0.86,
                          bottom=0.08)
    fig.suptitle("Two electrode rings on the core's vessel: the field at the centre, the strays they put on the pump, and "
                 "the pump's gain", fontsize=11.5, x=0.01, ha="left", color=INK)
    fig.text(0.01, 0.905, "Stack of record (3 mm, 6 + 6, 6 mm gaps), each ring coupled through 1 nF to node 1 / 4; the "
             "hub's dimensions are the tube's placeholders in the designer's layer order (sim/core_rings.py).",
             fontsize=8.3, color=INK2)
    section(fig.add_subplot(gs[:, 0]), res)
    axE, axC, axZ = fig.add_subplot(gs[0, 1]), fig.add_subplot(gs[0, 2]), fig.add_subplot(gs[1, 1])
    for col, nm in zip(RAMP3, CR.RINGS):
        for coils, ls in ((True, "-"), (False, (0, (4, 2)))):
            q = sorted([x for x in rings if x["ring_name"] == nm and x["coils"] == coils], key=lambda x: x["theta_deg"])
            th = [x["theta_deg"] for x in q]
            lab = f"{nm}" + ("" if coils else ", no coils")
            kw = dict(color=col, lw=1.6, ls=ls, marker="o" if coils else None, ms=4, mec=SURF, label=lab)
            axE.plot(th, [x["E_centre_kV_cm"] for x in q], **kw)
            axC.plot(th, [x["C_ring_ref_pF"] for x in q], **kw)
            axZ.plot(th, [x["pump"]["z"] for x in q], **kw)
            if coils:
                axC.plot(th, [x["C_ring_ring_pF"] for x in q], color=col, lw=1.0, ls=(0, (1, 1.5)))
    style(axE, "(b) the field at the centre, peak, at the pump's swing", "kV/cm (alternating, 120 Hz)")
    style(axC, "(c) each ring's stray to the shaft side; dotted: ring to ring", "pF")
    style(axZ, "(d) the pump's gain with those strays", "z per cycle")
    axZ.axhline(1.3095, color=MUTED, lw=0.9, ls=(0, (4, 3)))
    axZ.text(71, 1.3095 + 0.0008, "bare pump 1.310", fontsize=7.2, color=MUTED, ha="right", va="bottom")
    axZ.axhline(1.231, color=MUTED, lw=0.9, ls=(0, (1, 2)))
    axZ.text(71, 1.231 + 0.0008, "the earlier 20 / 10 pF guess: 1.231", fontsize=7.2, color=MUTED, ha="right", va="bottom")
    for ax in (axE, axC, axZ):
        ax.set_xlabel("ring's polar angle from the axis (deg); 90 = the equator", fontsize=8.3, color=INK2)
        ax.set_xticks(CR.THETAS)
    h, lab = axE.get_legend_handles_labels()
    axE.legend(h, lab, fontsize=7.4, frameon=False, ncol=2, loc="lower center")
    # the budget table: z for any stray, geometry-free
    axT = fig.add_subplot(gs[1, 2]); axT.axis("off")
    axT.set_title("(e) the pump's stray budget: z for any rings", fontsize=9.6, loc="left", color=INK)
    b = d["budget"]
    cc = sorted({q["C_rr_pF"] for q in b}); cr = sorted({q["C_ref_pF"] for q in b})
    axT.text(0.0, 0.88, "to the shaft side ↓  /  ring to ring →", fontsize=7.8, color=INK2, transform=axT.transAxes)
    for j, c in enumerate(cc):
        axT.text(0.42 + 0.15 * j, 0.78, f"{c:g} pF", fontsize=8, color=INK, weight="bold", ha="right", transform=axT.transAxes)
    for i, c in enumerate(cr):
        y = 0.68 - 0.1 * i
        axT.text(0.0, y, f"{c:g} pF", fontsize=8, color=INK, weight="bold", transform=axT.transAxes)
        for j, c2 in enumerate(cc):
            q = [x for x in b if x["C_ref_pF"] == c and x["C_rr_pF"] == c2][0]
            axT.text(0.42 + 0.15 * j, y, f"{q['z']:.3f}", fontsize=8, color=INK if q["z"] >= 1.3 else INK2,
                     weight="bold" if q["z"] >= 1.3 else "normal", ha="right", transform=axT.transAxes)
    axT.text(0.0, 0.1, "Bold: z ≥ 1.30. Each pF to the shaft side costs about 0.003 of z, each pF between the rings "
             "about 0.003 too.", fontsize=7.6, color=INK2, transform=axT.transAxes, wrap=True)
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    fig.savefig(OUT, dpi=130, facecolor="white")
    plt.close(fig)
    print(OUT)


if __name__ == "__main__":
    main()
