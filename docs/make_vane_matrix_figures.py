"""docs/make_vane_matrix_figures.py -- the figures and summary tables of the air vane-stack matrix
(sim/vane_matrix_results.json, from sim/vane_matrix.py):
  docs/figures/vane-matrix-radius.png  what a larger vane radius buys, at the 6 + 6 cap: the clamped power, the gain z,
                                       the stack length for the 1.5 mm stack's 7.4 W, the aluminium; one line per gap,
                                       each on its thinnest corona-safe thickness;
  docs/figures/vane-matrix-corona.png  the rims' corona margin over gap and thickness (handled surface, m 0.85);
  sim/vane_matrix_summary.json         the tables the findings quote.
Usage: python3 docs/make_vane_matrix_figures.py
"""
import json
import os

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt                                   # noqa: E402
from matplotlib.colors import LinearSegmentedColormap, TwoSlopeNorm   # noqa: E402
import numpy as np                                                # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
SIM = os.path.join(HERE, "..", "sim")
FIG = os.path.join(HERE, "figures")
# chart tokens (the dataviz reference palette, light mode)
SURF, INK, INK2, MUTED, GRID, AXIS = "#fcfcfb", "#0b0b0b", "#52514e", "#898781", "#e1e0d9", "#c3c2b7"
RAMP4 = ("#86b6ef", "#3987e5", "#1c5cab", "#0d366b")             # ordinal blue: 250 / 400 / 550 / 700 (validated)
DIV = LinearSegmentedColormap.from_list("div", ["#e34948", "#f0efec", "#2a78d6"])   # red <- gray -> blue
P_REF = 7.43                                                      # W: the 1.5 mm 16 + 16 stack (air_stack_sizing)


def style(ax, title, ylabel):
    ax.set_facecolor(SURF)
    ax.set_title(title, fontsize=10, loc="left", color=INK)
    ax.set_ylabel(ylabel, fontsize=8.5, color=INK2)
    ax.grid(True, color=GRID, lw=0.6)
    ax.set_axisbelow(True)
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)
    for s in ("left", "bottom"):
        ax.spines[s].set_color(AXIS)
    ax.tick_params(colors=INK2, labelsize=8)


def load():
    m = json.load(open(os.path.join(SIM, "vane_matrix_results.json")))
    return m, m["rows"]


def safe_t(m, g):
    """the thinnest thickness whose rims hold the operating peak on a handled surface (None if none does)."""
    ok = [r["t_mm"] for r in m["rims"] if r["gap_mm"] == g and r["V_onset_handled_kV"] >= next(
        q["V_op_kV"] for q in m["rows"] if q["gap_mm"] == g)]
    return min(ok) if ok else None


def pick(rows, **k):
    return [q for q in rows if all(q[a] == b for a, b in k.items())]


def summary(m, rows):
    """the findings' tables."""
    out = {}
    R = m["axes"]["r_out_mm"]
    ok = [q for q in rows if q["corona_ok"] and q["gain_ok"]]
    out["best_per_m"] = [max([q for q in ok if q["r_outMm"] == ro], key=lambda q: q["P_clamped_est_per_m"]) for ro in R]
    cap = [q for q in ok if q["n_plates"] <= 6]
    out["best_capped"] = [max([q for q in cap if q["r_outMm"] == ro], key=lambda q: q["P_clamped_est_W"]) for ro in R]
    out["ref_series"] = pick(rows, gap_mm=6.0, t_vaneMm=3.0, ws_deg=22.0, n_plates=6)
    out["safe_t"] = {str(g): safe_t(m, g) for g in m["axes"]["gap_mm"]}
    keys = ("gap_mm", "t_vaneMm", "r_outMm", "ws_deg", "n_plates", "V_op_kV", "C_min_pF", "C_max_pF", "kappa", "z",
            "P_clamped_est_W", "P_clamped_est_per_m", "L_es_side_mm", "L_tube_mm", "rotor_vanes_kg", "stator_vanes_kg",
            "ca_plates_kg", "I_rotor_kgm2", "V_onset_handled_kV")
    slim = lambda q: {k: q[k] for k in keys}
    return {k: ([slim(q) for q in v] if isinstance(v, list) else v) for k, v in out.items()}


def fig_radius(m, rows):
    R = m["axes"]["r_out_mm"]
    gaps = [g for g in (3.0, 5.0, 6.0, 8.0) if safe_t(m, g)]      # each on its thinnest corona-safe thickness
    fig, axs = plt.subplots(1, 4, figsize=(17, 4.6), facecolor="white")
    fig.subplots_adjust(left=0.045, right=0.985, top=0.74, bottom=0.14, wspace=0.30)
    fig.suptitle("What a larger vane radius buys: 6 + 6 vanes per varicap per side, 6 × 22° / 22° sectors, full-round "
                 "vanes and plates on each gap's thinnest corona-safe thickness", fontsize=11.5, x=0.01, ha="left",
                 color=INK)
    for col, g in zip(RAMP4, gaps):
        t = safe_t(m, g)
        s = sorted(pick(rows, gap_mm=g, t_vaneMm=t, ws_deg=22.0, n_plates=6), key=lambda q: q["r_outMm"])
        lab = f"gap {g:g} mm, {t:g} mm vanes ({s[0]['V_op_kV']:.0f} kV)"
        x = [q["r_outMm"] for q in s]
        kw = dict(color=col, lw=1.6, marker="o", ms=5, mec=SURF, mew=1.2, label=lab)
        axs[0].plot(x, [q["P_clamped_est_W"] for q in s], **kw)
        axs[1].plot(x, [q["z"] for q in s], **kw)
        # the smallest vane count that reaches the 1.5 mm stack's power, and its stack length
        L = []
        for ro in R:
            c = sorted([q for q in pick(rows, gap_mm=g, t_vaneMm=t, ws_deg=22.0, r_outMm=ro)
                        if q["P_clamped_est_W"] >= P_REF and q["gain_ok"]], key=lambda q: q["n_plates"])
            L.append(c[0]["L_es_side_mm"] if c else np.nan)
        axs[2].plot(R, L, **kw)
        axs[3].plot(x, [q["rotor_vanes_kg"] + q["stator_vanes_kg"] + q["ca_plates_kg"] for q in s], **kw)
        for ax, y in ((axs[0], s[-1]["P_clamped_est_W"]), (axs[1], s[-1]["z"])):
            ax.annotate(f"{g:g} mm", (x[-1], y), (6, 0), textcoords="offset points", fontsize=7.5, color=INK2, va="center")
    style(axs[0], "clamped power at the operating peak", "W (calibrated eigen-cycle)")
    style(axs[1], "gain per cycle z", "z")
    axs[1].axhline(m["z_floor"], color=MUTED, lw=0.9, ls=(0, (4, 3)))
    axs[1].text(R[-1] + 26, m["z_floor"] + 0.004, "floor 1.3", fontsize=7.5, color=MUTED, va="bottom", ha="right")
    style(axs[2], f"stack per side for {P_REF:g} W (fewest vanes)", "mm, first vane to last plate")
    style(axs[3], "aluminium, both bodies (6 + 6)", "kg")
    for ax in axs:
        ax.set_xlabel("vane outer radius r_out (mm)", fontsize=8.5, color=INK2)
        ax.set_xticks(R)
        ax.set_xlim(R[0] - 10, R[-1] + 28)
    h, lab = axs[0].get_legend_handles_labels()
    fig.legend(h, lab, ncol=len(lab), fontsize=8, frameon=False, loc="upper left", bbox_to_anchor=(0.04, 0.905))
    axs[2].text(R[0], axs[2].get_ylim()[0], " none reaches it\n with ≤ 16 + 16", fontsize=7.5, color=MUTED, va="bottom")
    out = os.path.join(FIG, "vane-matrix-radius.png")
    fig.savefig(out, dpi=130, facecolor="white")
    plt.close(fig)
    return out


def fig_corona(m):
    G, T = m["axes"]["gap_mm"], m["axes"]["t_mm"]
    v_op = {g: next(q["V_op_kV"] for q in m["rows"] if q["gap_mm"] == g) for g in G}
    M = np.array([[next(r["V_onset_handled_kV"] for r in m["rims"] if r["gap_mm"] == g and r["t_mm"] == t) / v_op[g]
                   for g in G] for t in T])
    fig, ax = plt.subplots(figsize=(7.6, 4.4), facecolor="white")
    fig.subplots_adjust(left=0.13, right=0.97, top=0.82, bottom=0.15)
    norm = TwoSlopeNorm(vcenter=1.0, vmin=min(0.6, M.min()), vmax=max(1.4, M.max()))
    ax.imshow(M, cmap=DIV, norm=norm, aspect="auto", origin="lower")
    for i, t in enumerate(T):
        for j, g in enumerate(G):
            v = M[i, j]
            ax.text(j, i, f"{v:.2f}", ha="center", va="center", fontsize=8.5, color=INK if 0.75 < v < 1.25 else "white")
    ax.set_xticks(range(len(G)), [f"{g:g} mm\n{v_op[g]:.1f} kV" for g in G], fontsize=8, color=INK2)
    ax.set_yticks(range(len(T)), [f"{t:g} mm (R{t / 2:g})" for t in T], fontsize=8, color=INK2)
    ax.set_xlabel("gap, and its operating peak (air breakdown ÷ 1.5)", fontsize=8.5, color=INK2)
    ax.set_ylabel("vane and plate thickness (full round)", fontsize=8.5, color=INK2)
    fig.suptitle("Rim corona margin: onset peak (Peek, handled surface m 0.85) ÷ operating peak", fontsize=10, x=0.01,
                 ha="left", color=INK)
    ax.set_title("above 1.00 (blue) the rims hold; below (red) they go into corona first", fontsize=8.5, loc="left",
                 color=INK2)
    for s in ax.spines.values():
        s.set_visible(False)
    out = os.path.join(FIG, "vane-matrix-corona.png")
    fig.savefig(out, dpi=130, facecolor="white")
    plt.close(fig)
    return out


def main():
    m, rows = load()
    s = summary(m, rows)
    json.dump(s, open(os.path.join(SIM, "vane_matrix_summary.json"), "w"), indent=1, default=float)
    print(fig_radius(m, rows))
    print(fig_corona(m))


if __name__ == "__main__":
    main()
