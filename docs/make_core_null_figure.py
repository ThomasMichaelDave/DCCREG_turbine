"""docs/make_core_null_figure.py -- writes docs/figures/core-null-field.png: the strongest steady field at the AH null
(sim/core_null_field.py, sim/core_null_field_results.json; the supplies from sim/core_field_results.json).
  (a) the hub's section with the two Rogowski electrodes on the null, dc1 at its design gap, equipotentials every 2 kV;
  (b) the gap, enlarged: equipotentials every 1 kV, the radius over which the field holds within 1 %;
  (c) the field at the null against the gap for each supply, held to the vacuum rule on the electrodes' surface;
  (d) the pressure at the null, 1/2 eps0 E^2;
  (e) why the profile matters: the surface field along the electrode, over the field at the centre;
  (f) the supplies side by side.
Usage: python3 docs/make_core_null_figure.py
"""
import json
import math
import os
import sys

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt                                   # noqa: E402
import numpy as np                                                # noqa: E402
from matplotlib.path import Path                                  # noqa: E402
from matplotlib.patches import PathPatch, Rectangle, Wedge          # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
SIM = os.path.join(HERE, "..", "sim")
sys.path.insert(0, SIM)
import core_null_field as N                                       # noqa: E402

SURF, INK, INK2, MUTED, GRID, AXIS = "#fcfcfb", "#0b0b0b", "#52514e", "#898781", "#e1e0d9", "#c3c2b7"
RAMP4 = ("#86b6ef", "#3987e5", "#1c5cab", "#0d366b")               # ordinal blue: 0 .. 3 multiplier stages
C_A, C_B, F_A, F_B = "#c0392b", "#1f6fb2", "#f6d5d1", "#dbe7f3"    # electrode A (node 1's side) / B, as the old cones
STEEL, GLASS, COMP = "#8a8f99", "#cfe3ee", "#e9e1c9"
OUT = os.path.join(HERE, "figures", "core-null-field.png")
EPS0 = N.EPS0


def kv(v):
    """a voltage in kV with a real minus sign."""
    return f"{v:.1f}".replace("-", "\u2212")


def style(ax, title, ylabel, xlabel=None):
    ax.set_facecolor(SURF)
    ax.set_title(title, fontsize=9.6, loc="left", color=INK)
    ax.set_ylabel(ylabel, fontsize=8.3, color=INK2)
    if xlabel:
        ax.set_xlabel(xlabel, fontsize=8.3, color=INK2)
    ax.grid(True, color=GRID, lw=0.6, which="major")
    ax.set_axisbelow(True)
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)
    for s in ("left", "bottom"):
        ax.spines[s].set_color(AXIS)
    ax.tick_params(colors=INK2, labelsize=7.8, which="both")


def body_paths(m):
    """closed outlines (mm) of each conductor, mirrored about the axis for display: the electrodes' contours run from the
    axis back to the axis, so the mirror closes them."""
    out = []
    for k, (name, key) in enumerate(m.names):
        sel = m.owner == k
        pts = np.vstack([m.p0[sel], m.p1[sel][-1:]]) * 1e3
        if key in ("A", "B"):
            full = np.vstack([pts, (pts * [-1, 1])[::-1]])
        else:
            full = pts
        out.append((name, key, full))
    return out


def field_map(m, sig, r, z, paths):
    R, Z = np.meshgrid(r, z, indexing="xy")
    V = m.potential(sig, np.abs(R.ravel()) * 1e-3, Z.ravel() * 1e-3).reshape(R.shape)
    inside = np.zeros(R.shape, dtype=bool)
    pts = np.column_stack([R.ravel(), Z.ravel()])
    for _, key, p in paths:
        inside |= Path(p).contains_points(pts).reshape(R.shape)
        if key == "REF":                                           # the coil's mirror image
            inside |= Path(p * [-1, 1]).contains_points(pts).reshape(R.shape)
    return R, Z, np.ma.masked_where(inside, V)


def draw_bodies(ax, paths, lw=1.0):
    for name, key, p in paths:
        fc, ec = dict(A=(F_A, C_A), B=(F_B, C_B)).get(key, (STEEL, "#5d6670"))
        for q in ((p,) if key in ("A", "B") else (p, p * [-1, 1])):
            ax.add_patch(PathPatch(Path(q), fc=fc, ec=ec, lw=lw, zorder=4))


def section(ax, m, sig, d1):
    v = N.VESSEL
    ax.add_patch(Wedge((0, 0), v["R_v"] + 3.0, 0, 360, width=3.0, fc=COMP, ec="none", zorder=1))
    ax.add_patch(Wedge((0, 0), v["R_v"], 0, 360, width=v["R_v"] - v["R_in"], fc=GLASS, ec="#6f8ea6", lw=0.6, zorder=1))
    paths = body_paths(m)
    r = np.linspace(-56, 56, 225)
    z = np.linspace(-56, 56, 225)
    R, Z, V = field_map(m, sig, r, z, paths)
    lv = np.arange(-12e3, 7.01e3, 2e3)
    ax.contour(R, Z, V, levels=lv, colors=INK2, linewidths=0.45, zorder=3, negative_linestyles="solid")
    draw_bodies(ax, paths, lw=0.8)
    ax.set_aspect("equal")
    ax.set_xlim(-56, 56); ax.set_ylim(-56, 56)
    ax.set_xlabel("r (mm), mirrored", fontsize=8.3, color=INK2); ax.set_ylabel("z (mm), the shaft's axis", fontsize=8.3,
                                                                              color=INK2)
    ax.tick_params(colors=INK2, labelsize=7.8)
    for s in ax.spines.values():
        s.set_color(AXIS)
    lab = dict(fontsize=7.2, color=INK, bbox=dict(fc="white", ec="none", pad=0.6, alpha=0.88), zorder=6)
    arr = dict(arrowstyle="-", lw=0.5, color=INK2)
    ax.annotate(f"electrode B, +{d1['V_B_kV']:.1f} kV\n(one CW stage on node 4)", (2.6, 30), (9, 47), arrowprops=arr, **lab)
    ax.annotate(f"electrode A, {kv(d1['V_A_kV'])} kV\n(node 1's peak through Dk)", (2.6, -30), (9, -50), arrowprops=arr, **lab)
    ax.annotate("AH coil (REF)\n[RH placeholder]", (50, 21), (30, 6), arrowprops=arr, **lab)
    ax.annotate("vessel (glass)\n+ retainer", (-31, 31), (-54, 45), arrowprops=arr, **lab)
    ax.text(-54, -53, "equipotentials every 2 kV; the shaft and the coils are REF (0 V)", fontsize=6.8, color=INK2,
            zorder=6)
    ax.set_title("(a) the hub's section: two Rogowski electrodes on the AH null,\n"
                 f"dc1 at its design gap {d1['g_min_mm']:.2f} mm", fontsize=9.6, loc="left", color=INK)


def zoom(ax, m, sig, d1):
    paths = body_paths(m)
    g = d1["g_min_mm"]
    r = np.linspace(-15, 15, 241)
    z = np.linspace(-6.5, 6.5, 131)
    R, Z, V = field_map(m, sig, r, z, paths)
    lv = np.arange(-13e3, 7.01e3, 1e3)
    ax.contour(R, Z, V, levels=lv, colors=INK2, linewidths=0.5, zorder=3, negative_linestyles="solid")
    draw_bodies(ax, paths, lw=0.9)
    ru = d1["r_uniform_1pc_mm"]
    ax.add_patch(Rectangle((-ru, -0.5 * g), 2 * ru, g, fc="none", ec="#0d366b", lw=1.1, ls=(0, (3, 2)), zorder=5))
    ax.set_aspect("equal")
    ax.set_xlim(-15, 15); ax.set_ylim(-6.5, 6.5)
    ax.set_xlabel("r (mm)", fontsize=8.3, color=INK2); ax.set_ylabel("z (mm)", fontsize=8.3, color=INK2)
    ax.tick_params(colors=INK2, labelsize=7.8)
    for s in ax.spines.values():
        s.set_color(AXIS)
    lab = dict(fontsize=7.2, color=INK, bbox=dict(fc="white", ec="none", pad=0.6, alpha=0.88), zorder=6)
    ax.annotate(f"within 1 % of the\nnull's field to\nr = {ru:.1f} mm", (ru, 0.0), (10.9, -1.1),
                arrowprops=dict(arrowstyle="-", lw=0.5, color=INK2), **lab)
    ax.text(0, 0, "AH null", fontsize=7.0, color="#0d366b", ha="center", va="center", zorder=6,
            bbox=dict(fc="white", ec="none", pad=0.4, alpha=0.8))
    ax.set_title(f"(b) the gap: {d1['V_gap_kV']:.1f} kV across {g:.2f} mm, {d1['E0_kV_cm']:.1f} kV/cm and "
                 f"{d1['p0_Pa']:.0f} Pa at the null;\nequipotentials every 1 kV; the surface peaks "
                 f"{100 * (d1['k_surf'] - 1):.1f} % above the null, on the profile", fontsize=9.6, loc="left", color=INK)


def main():
    R = json.load(open(os.path.join(SIM, "core_null_field_results.json")))
    rows = {r["name"]: r for r in json.load(open(os.path.join(SIM, "core_field_results.json")))["rows"]}
    rings = json.load(open(os.path.join(SIM, "core_rings_results.json")))["rings"]
    ring_best = max(q["E_centre_kV_cm_per_kV"] for q in rings)
    sup = {k: tuple(v) for k, v in R["supplies_V"].items()}
    d1 = R["design"]["dc1"]
    m = N.build("rogowski", d1["g_min_mm"], **d1["shape"])
    sA, sB = m.solve({"A": 1.0}), m.solve({"B": 1.0})
    sig = d1["V_A_kV"] * 1e3 * sA + d1["V_B_kV"] * 1e3 * sB

    fig = plt.figure(figsize=(16.5, 10.2), facecolor="white")
    gs = fig.add_gridspec(2, 3, width_ratios=(1.12, 1, 1), height_ratios=(1.25, 1), hspace=0.36, wspace=0.27,
                          left=0.045, right=0.985, top=0.872, bottom=0.06)
    fig.suptitle("The strongest steady field at the AH null: two Rogowski electrodes in the vacuum, on the "
                 "electrostatic pump's DC", fontsize=11.8, x=0.01, ha="left", color=INK)
    fig.text(0.01, 0.925, "Stack of record (3 mm, 6 + 6, 6 mm gaps, 13.1 kV clamp), 1200 rpm relative; held to the "
             f"repo's vacuum rule, {N.E_OP_KV_MM:.2f} kV/mm on any electrode surface (10 kV/mm over the 1.5 margin). "
             "Axisymmetric boundary elements (sim/core_null_field.py); the hub is the tube placeholder [RH].",
             fontsize=8.3, color=INK2)
    section(fig.add_subplot(gs[0, 0]), m, sig, d1)
    zoom(fig.add_subplot(gs[1, 0]), m, sig, d1)

    # (c) / (d): the field and the pressure at the null against the gap
    axE, axP = fig.add_subplot(gs[0, 1]), fig.add_subplot(gs[0, 2])
    sw = R["sweep"]
    gs_ = np.array([q["g_mm"] for q in sw])
    for i, nm in enumerate(("dc0", "dc1", "dc2", "dc3")):
        e0 = np.array([q["supplies"][nm]["E0_kV_mm"] for q in sw]) * 10
        es = np.array([q["supplies"][nm]["Esurf_max_kV_mm"] for q in sw])
        ok = es <= N.E_OP_KV_MM * 1.0001
        dd = R["design"][nm]
        lab = f"{nm}: {dd['V_gap_kV']:.1f} kV" + (" (B on the shaft)" if nm == "dc0" else f" ({nm[-1]} CW stage"
                                                   + ("s)" if nm != "dc1" else ")"))
        for ax, y, yd in ((axE, e0, dd["E0_kV_cm"]), (axP, 0.5 * EPS0 * (e0 * 1e5) ** 2, dd["p0_Pa"])):
            # the allowed part solid (from the design gap up), the part the rule forbids dotted
            gg = np.concatenate([[dd["g_min_mm"]], gs_[gs_ > dd["g_min_mm"]]])
            yy = np.concatenate([[yd], y[gs_ > dd["g_min_mm"]]])
            ax.plot(gg, yy, color=RAMP4[i], lw=2.0 if nm == "dc1" else 1.5, label=lab, zorder=4)
            ax.plot(gs_[gs_ <= dd["g_min_mm"] * 1.05], y[gs_ <= dd["g_min_mm"] * 1.05], color=RAMP4[i], lw=1.0,
                    ls=(0, (1, 1.6)), zorder=3)
            ax.plot([dd["g_min_mm"]], [yd], "o", ms=6.5 if nm == "dc1" else 5, color=RAMP4[i], mec=SURF, zorder=5)
    fl = R["design"]["float (peak)"]
    e0f = np.array([q["supplies"]["float (peak)"]["E0_kV_mm"] for q in sw]) * 10
    m_f = gs_ >= fl["g_min_mm"]
    for ax, y, yd in ((axE, e0f, fl["E0_kV_cm"]), (axP, 0.5 * EPS0 * (e0f * 1e5) ** 2, fl["p0_Pa"])):
        ax.plot(np.concatenate([[fl["g_min_mm"]], gs_[m_f]]), np.concatenate([[yd], y[m_f]]), color=MUTED, lw=1.2,
                ls=(0, (5, 2.5)), label=f"the swing, ±{0.5 * fl['V_gap_kV'] * 2:.1f} kV peak (float, 120 Hz)", zorder=2)
    e_rule = N.E_OP_KV_MM * 10
    axE.axhline(e_rule, color=INK2, lw=0.9, ls=(0, (4, 3)))
    axE.text(11.8, e_rule * 1.06, f"the rule: {N.E_OP_KV_MM:.2f} kV/mm on the surface", fontsize=7.2, color=INK2,
             ha="right", va="bottom")
    e_ring = ring_best * d1["V_gap_kV"]
    axE.axhline(e_ring, color=MUTED, lw=0.9, ls=(0, (1, 2)))
    axE.text(11.8, e_ring * 1.07, f"best ring outside the vessel\n({d1['V_gap_kV']:.1f} kV): {e_ring:.1f} kV/cm",
             fontsize=7.2, color=MUTED, ha="right", va="bottom")
    p_rule = 0.5 * EPS0 * (N.E_OP_KV_MM * 1e6) ** 2
    axP.axhline(p_rule, color=INK2, lw=0.9, ls=(0, (4, 3)))
    axP.text(11.8, p_rule * 1.12, f"at the rule's field: {p_rule:.0f} Pa", fontsize=7.2, color=INK2, ha="right",
             va="bottom")
    p_ring = 0.5 * EPS0 * (e_ring * 1e5) ** 2
    axP.axhline(p_ring, color=MUTED, lw=0.9, ls=(0, (1, 2)))
    axP.text(11.8, p_ring * 1.15, f"best ring outside the vessel: {p_ring:.2f} Pa", fontsize=7.2, color=MUTED,
             ha="right", va="bottom")
    for ax in (axE, axP):
        ax.set_xscale("log"); ax.set_yscale("log")
        ax.set_xlim(1.0, 12.0)
        ax.set_xticks([1, 1.5, 2, 3, 4, 5, 6, 8, 10, 12]); ax.set_xticklabels(["1", "1.5", "2", "3", "4", "5", "6", "8",
                                                                                "10", "12"])
    axE.set_ylim(1.5, 220)
    axP.set_ylim(0.15, 1500)
    style(axE, "(c) the field at the null against the gap; dots: the smallest gap the rule allows", "kV/cm",
          "gap g (mm)")
    style(axP, "(d) the electrostatic pressure at the null, ½ ε0 E²", "Pa", "gap g (mm)")
    h, lab = axE.get_legend_handles_labels()
    axE.legend(h, lab, fontsize=7.2, loc="lower left", frameon=True, facecolor="white", edgecolor="none",
               framealpha=0.92)
    axE.text(1.04, 150, "dotted: the surface would exceed the rule", fontsize=7.0, color=INK2,
             bbox=dict(fc=SURF, ec="none", pad=0.5, alpha=0.9), zorder=6)
    for nm in ("dc0", "dc1", "dc2", "dc3"):
        dd = R["design"][nm]
        axP.annotate(f"{dd['g_min_mm']:.2f}", (dd["g_min_mm"], dd["p0_Pa"]), (0, 7 if nm in ("dc0", "dc2") else -12),
                     textcoords="offset points", fontsize=7.0, color=INK2, ha="center")

    # (e) the profile: the surface field along the electrode
    axS = fig.add_subplot(gs[1, 1])
    cols = {"bare stem": MUTED, "sphere r 10": INK2, "pill: flat r 3.1, full": "#b9770e", "pill: flat r 6.2": "#e0a458",
            "Rogowski, profile from": "#86b6ef", "Rogowski, flat r 3.1": "#0d366b"}
    gp = R["profile_gap_mm"]
    for q in R["profile"]:
        key = next((k for k in cols if q["label"].startswith(k)), None)
        if key is None:
            continue
        kw = dict(q["shape"])
        shape = kw.pop("shape")
        mm = N.build(shape, gp, **kw)
        a_, b_ = mm.solve({"A": 1.0}), mm.solve({"B": 1.0})
        sd = 0.5 * (b_ - a_)
        e0 = abs(float(mm.field(sd, np.array([0.0]), np.array([0.0]))[1][0]))
        sel = mm.owner == 0
        s_ = np.cumsum(mm.L[sel]) * 1e3 - 0.5 * mm.L[sel] * 1e3
        es = np.abs(sd[sel]) / EPS0 / e0
        keep = s_ <= 18
        design = key == "Rogowski, flat r 3.1"
        lab = q["label"].replace(" (the design)", "") + f": peak {q['k_surf_diff']:.3f}"
        axS.plot(s_[keep], es[keep], color=cols[key], lw=2.0 if design else 1.2, label=lab, zorder=4 if design else 3)
    axS.axhline(1.0, color=INK2, lw=0.8, ls=(0, (4, 3)))
    axS.set_xlim(0, 18); axS.set_ylim(0, 1.9)
    style(axS, f"(e) the surface field along the electrode, over the null's (g {gp:g} mm, 1 V across)", "E_surface / E_null",
          "distance along the electrode from the face's centre (mm)")
    axS.legend(fontsize=7.0, frameon=False, loc="upper right", ncol=1)

    # (f) the supplies
    axT = fig.add_subplot(gs[1, 2]); axT.axis("off")
    axT.set_title("(f) the supplies: one field; the voltage buys room", fontsize=9.6, loc="left", color=INK)
    head = ("", "A / B", "across", "gap", "E null", "p", "z start", "ripple")
    xs = (0.0, 0.095, 0.31, 0.43, 0.525, 0.635, 0.715, 0.82)
    for x, h_ in zip(xs, head):
        axT.text(x, 0.93, h_, fontsize=7.6, color=INK, weight="bold", transform=axT.transAxes)
    axT.text(0.36, 0.875, "kV", fontsize=6.8, color=INK2, transform=axT.transAxes)
    axT.text(0.095, 0.875, "kV", fontsize=6.8, color=INK2, transform=axT.transAxes)
    for x, u in zip(xs[3:], ("mm", "kV/cm", "Pa", "", "V p-p, A / B")):
        axT.text(x, 0.875, u, fontsize=6.8, color=INK2, transform=axT.transAxes)
    y = 0.80
    for nm in ("dc0", "dc1", "dc2", "dc3"):
        dd, rr, fr = R["design"][nm], rows[N.SUPPLY_ROWS[nm]], rows["free " + N.SUPPLY_ROWS[nm]]
        vb = "0 (shaft)" if nm == "dc0" else f"+{dd['V_B_kV']:.1f}"
        rip = f"{rr['V_ea_kV']['pp'] * 1e3:.0f}" + ("" if nm == "dc0" else f" / {rr['V_eb_kV']['pp'] * 1e3:.0f}")
        cells = (nm + (" ★" if nm == "dc1" else ""), f"{kv(dd['V_A_kV'])} / {vb}", f"{dd['V_gap_kV']:.1f}",
                 f"{dd['g_min_mm']:.2f}", f"{dd['E0_kV_cm']:.1f}", f"{dd['p0_Pa']:.0f}", f"{fr['z']:.3f}", rip)
        for x, c in zip(xs, cells):
            axT.text(x, y, c, fontsize=7.4, color=INK if nm == "dc1" else INK2, weight="bold" if nm == "dc1" else "normal",
                     transform=axT.transAxes)
        y -= 0.075
    fz = rows["free float"]["z"]
    cells = ("swing", f"±{0.5 * fl['V_gap_kV']:.1f}", f"±{fl['V_gap_kV']:.1f}", f"{fl['g_min_mm']:.2f}",
             f"±{fl['E0_kV_cm']:.1f}", f"0–{fl['p0_Pa']:.0f}", f"{fz:.3f}", "AC 120 Hz")
    for x, c in zip(xs, cells):
        axT.text(x, y, c, fontsize=7.4, color=MUTED, transform=axT.transAxes)
    D = R["design"]
    notes = [
        "Each option is held to the same surface field, so each reaches about 65 kV/cm at the null. More multiplier stages "
        f"widen the gap at that field ({D['dc0']['g_min_mm']:.1f} → {D['dc3']['g_min_mm']:.1f} mm) and the radius within "
        f"1 % ({D['dc0']['r_uniform_1pc_mm']:.1f} → {D['dc3']['r_uniform_1pc_mm']:.1f} mm); they do not raise the field.",
        "No geometry beats a uniform gap: in the vacuum each component of E is harmonic, so the field at the null cannot "
        "exceed the field on the electrodes.",
        "Rated higher (polished, conditioned, small area: the electrodes here are "
        f"{2 * D['dc0']['R_max_mm']:.0f}–{2 * D['dc3']['R_max_mm']:.0f} mm across), they would carry more; "
        "the field at the null scales with the rated surface field, the pressure with its square.",
        "z start: the pump's gain at start-up with 100 pF storage (the bare pump 1.310). Ripple at the 10 GΩ placeholder "
        "leakage. ★ the default: one CW stage, Co / Dc / Dp / Cs.",
    ]
    import textwrap
    axT.text(0.0, y - 0.07, "\n".join(textwrap.fill(s_, 84) for s_ in notes), fontsize=7.0, color=INK2, va="top",
             transform=axT.transAxes, linespacing=1.32)
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    fig.savefig(OUT, dpi=130, facecolor="white")
    plt.close(fig)
    print(OUT)


if __name__ == "__main__":
    main()
