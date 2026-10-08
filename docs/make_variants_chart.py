"""docs/make_variants_chart.py -- writes docs/figures/utron-size-vs-gain.png: the lightest utron (copper + iron, 100 mm
stack) for each gain margin, as Pareto fronts, for {6, 12} stator bridges per side x {600, 1200} rpm relative, at the
0.5 mm and 1.0 mm gaps (sim/pole_design_variants.json, from `python3 sim/pole_design.py variants`).
Encoding: hue = bridges per side (validated pair), line style = speed; direct labels at the line ends + a legend.
Usage: python3 docs/make_variants_chart.py
"""
import json
import os

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt                           # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
ROWS = json.load(open(os.path.join(HERE, "..", "sim", "pole_design_variants.json")))["rows"]
SURFACE, INK, INK2, MUTED, GRID = "#fcfcfb", "#0b0b0b", "#52514e", "#8a8984", "#e6e5e1"
HUE = {6: "#2a78d6", 12: "#eb6834"}                       # validated: CVD dE 24.7, normal 33.6, contrast >= 3:1
STYLE = {"600": "-", "1200": "--"}


def front(g, n_br, rpm):
    rs = sorted([r for r in ROWS if r["design"]["g"] == g and r["n_br"] == n_br and r["z_rpm"].get(rpm)],
                key=lambda r: r["m_utron_kg"])
    xs, ys, best = [], [], -1.0
    for r in rs:
        z = r["z_rpm"][rpm]
        if z > best:
            best = z
            xs.append(r["m_utron_kg"]); ys.append(z)
    return xs, ys


def main():
    fig, axs = plt.subplots(1, 2, figsize=(13, 5.4), facecolor=SURFACE, sharey=True)
    for ax, g in zip(axs, (0.5, 1.0)):
        ax.set_facecolor(SURFACE)
        for zref, lab in ((1.0, "z = 1"), (1.2, "z = 1.20"),):
            ax.axhline(zref, color=MUTED, lw=0.8, ls=":", zorder=1)
            ax.text(0.08, zref + 0.006, lab, color=INK2, fontsize=8.0, va="bottom", ha="left")
        for n_br in (6, 12):
            for rpm in ("600", "1200"):
                xs, ys = front(g, n_br, rpm)
                if not xs:
                    continue
                f = n_br * int(rpm) / 60
                ax.plot(xs, ys, STYLE[rpm], color=HUE[n_br], lw=1.6, marker="o", ms=5.5, mec=SURFACE, mew=1.0,
                        label=f"{n_br} bridges, {rpm} rpm ({f:.0f} Hz)", zorder=3)
                ax.annotate(f"{n_br} br / {rpm}", (xs[-1], ys[-1]), xytext=(6, 0), textcoords="offset points",
                            color=INK2, fontsize=8.5, va="center")
        ax.set_title(f"gap {g} mm", color=INK, fontsize=11, loc="left")
        ax.set_xlabel("utron mass, copper + iron (kg, 100 mm stack)", color=INK2, fontsize=9.5)
        ax.grid(True, color=GRID, lw=0.6, zorder=0)
        ax.tick_params(colors=INK2, labelsize=8.5)
        for sp in ax.spines.values():
            sp.set_color(GRID)
        ax.set_xlim(0, 9.5)
        ax.set_ylim(0.6, 1.42)
    axs[0].set_ylabel("gain per cycle z (linear, copper in every coil)", color=INK2, fontsize=9.5)
    axs[0].legend(loc="lower right", fontsize=8.5, frameon=False, labelcolor=INK2)
    fig.suptitle("Lightest utron for each gain margin — stator bridges per side and relative speed",
                 color=INK, fontsize=12, x=0.01, ha="left")
    fig.text(0.01, 0.035, "Each line is a Pareto front: every point is the lightest screened utron reaching that gain. "
             "Hue = bridges per side, line style = speed (solid 600 rpm, dashed 1200 rpm relative).", color=MUTED, fontsize=8.5)
    fig.text(0.01, 0.008, "Dotted: z = 1 (growth threshold) and z = 1.20 (healthy margin). Designs below z 0.6 are off the axis. Source: sim/pole_design_variants.json "
             "(python3 sim/pole_design.py variants / variants_ext).", color=MUTED, fontsize=8.5)
    fig.tight_layout(rect=(0, 0.07, 1, 0.94))
    out = os.path.join(HERE, "figures", "utron-size-vs-gain.png")
    fig.savefig(out, dpi=130, facecolor=SURFACE)
    print(out)


if __name__ == "__main__":
    main()
