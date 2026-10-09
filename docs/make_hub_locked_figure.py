"""docs/make_hub_locked_figure.py -- writes docs/figures/hub-locked.png: the locked hub (presets/hub-locked.json) with
the lock-down study's field generator (2026-10-08), two rings outside the glass on the electrostatic pump's DC
(sim/hub_locked.py -> sim/hub_locked_results.json). The hub's stack-up stands; the lock-down's rings (bands 20-53
deg, three stages, ring A through Dk) are superseded by the rings of record (docs/rings-design.md,
docs/drawings/DCCREG-HUB-201.pdf, docs/figures/hub-rings-field.png).
  (a) the hub's section to scale with the lock-down's rings (bands 20-53 deg, three multiplier stages), DC
      equipotentials every 2 kV;
  (b) the field at the null against the bands' equatorial edge at that DC, with the gaps the insulation allows;
  (c) the field at the null against the supply, each at its widest allowed bands, for three interface ratings;
  (d) the lock-down's pick and the alternatives.
Usage: python3 docs/make_hub_locked_figure.py
"""
import json
import math
import os
import sys
import textwrap

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt                                   # noqa: E402
import numpy as np                                                # noqa: E402
from matplotlib.patches import Polygon, Rectangle, Wedge          # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
SIM = os.path.join(HERE, "..", "sim")
sys.path.insert(0, SIM)
import core_rings as CR                                           # noqa: E402
import hub_locked as HL                                           # noqa: E402

SURF, INK, INK2, MUTED, GRID, AXIS = "#fcfcfb", "#0b0b0b", "#52514e", "#898781", "#e1e0d9", "#c3c2b7"
RAMP3 = ("#0d366b", "#3987e5", "#86b6ef")                         # ordinal blue: polar edge 20 / 25 / 30 deg
RAMP_ET = ("#0d366b", "#3987e5", "#86b6ef")                       # interface rating 1 / 2 / 5 kV/mm
C_A, C_B = "#c0392b", "#1f6fb2"
STEEL, GLASS, COMP = "#8a8f99", "#cfe3ee", "#e9e1c9"
OUT = os.path.join(HERE, "figures", "hub-locked.png")
EPS0 = 8.8541878128e-12


def kv(v, f="{:.1f}"):
    return f.format(v).replace("-", "−")


def style(ax, title, ylabel, xlabel=None):
    ax.set_facecolor(SURF)
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


def section(ax, rec):
    hub = HL.HUB
    ax.add_patch(Rectangle((-hub["ret_r"], -hub["ret_z"]), 2 * hub["ret_r"], 2 * hub["ret_z"], fc=COMP, ec="#b9ad8a",
                           lw=0.6, zorder=1))
    ax.add_patch(Wedge((0, 0), hub["R_v"], 0, 360, width=hub["R_v"] - hub["R_in"], fc=GLASS, ec="#6f8ea6", lw=0.6, zorder=2))
    ax.add_patch(Wedge((0, 0), hub["R_in"], 0, 360, fc="white", ec="none", zorder=2))
    for s in (1, -1):
        for (r1, z0, z1) in ((hub["ah_r"], hub["ah_z"][0], hub["ah_z"][1]), (hub["fl_r"], hub["fl_z"][0], hub["fl_z"][1]),
                             (hub["sh_r"], hub["fl_z"][1], 112.0)):
            a, b = sorted((s * z0, s * z1))
            ax.add_patch(Rectangle((-r1, a), 2 * r1, b - a, fc=STEEL, ec="#5d6670", lw=0.6, zorder=3))
    # the rings' DC field: the finite volumes, B (upper) and A (lower), mirrored to both halves of r
    ring = HL.band(rec["theta_p"], rec["theta_e"])
    res = CR.solve(ring, 0.5 * (rec["theta_p"] + rec["theta_e"]), True, 0.25, hub=hub, keep=True, maps_fn=HL.maps)
    va, vb = rec["V_A_kV"] * 1e3, rec["V_B_kV"] * 1e3
    cm, dm = 0.5 * (vb + va), 0.5 * (vb - va)
    Va, Vs, cond = res["V_anti"], res["V_sym"], res["cond"]
    h = res["h_mm"]
    nr, nz = Va.shape
    r = (np.arange(nr) + 0.5) * h
    z = (np.arange(nz) + 0.5) * h
    Vf = np.concatenate([(cm * Vs - dm * Va)[:, ::-1], cm * Vs + dm * Va], axis=1)
    cf = np.concatenate([cond[:, ::-1], cond], axis=1)
    zf = np.concatenate([-z[::-1], z])
    keep = r <= 62.0
    for sgn in (-1, 1):
        Rg, Zg = np.meshgrid(sgn * r[keep], zf, indexing="ij")
        ax.contour(Rg, Zg, np.ma.masked_where(cf[keep] != 0, Vf[keep]), levels=np.arange(-12e3, 18.01e3, 2e3),
                   colors=INK2, linewidths=0.42, zorder=4, negative_linestyles="solid")
    tp, te = math.radians(rec["theta_p"]), math.radians(rec["theta_e"])
    ph = np.linspace(tp, te, 60)
    for sgn_r in (-1, 1):
        for s, col in ((1, C_B), (-1, C_A)):
            outer = [(sgn_r * (hub["R_v"] + 1.0) * math.sin(p), s * (hub["R_v"] + 1.0) * math.cos(p)) for p in ph]
            inner = [(sgn_r * hub["R_v"] * math.sin(p), s * hub["R_v"] * math.cos(p)) for p in ph[::-1]]
            ax.add_patch(Polygon(outer + inner, closed=True, fc=col, ec=col, lw=0.8, zorder=6))
    ax.set_aspect("equal")
    ax.set_xlim(-62, 62); ax.set_ylim(-112, 112)
    ax.set_xlabel("r (mm)", fontsize=8.3, color=INK2)
    ax.set_ylabel("z (mm), the shaft's axis", fontsize=8.3, color=INK2)
    ax.tick_params(colors=INK2, labelsize=7.8)
    for s_ in ax.spines.values():
        s_.set_color(AXIS)
    lab = dict(fontsize=7.0, color=INK, bbox=dict(fc="white", ec="none", pad=0.5, alpha=0.9), zorder=8)
    arr = dict(arrowstyle="-", lw=0.5, color=INK2)
    xe, ze = hub["R_v"] * math.sin(te), hub["R_v"] * math.cos(te)
    ax.annotate(f"ring B, +{rec['V_B_kV']:.1f} kV: a band on the glass,\n{rec['theta_p']:.0f}–{rec['theta_e']:.0f}° "
                "(three CW stages on node 4)", (-15, 20), (-61, 40), arrowprops=arr, **lab)
    ax.annotate(f"ring A, {kv(rec['V_A_kV'])} kV\n(node 1's peak through Dk)", (-15, -20), (-61, -36), arrowprops=arr, **lab)
    ax.annotate(f"{rec['gap_mm']:.1f} mm along the glass\nbetween the rings: "
                f"{rec['E_t_kV_mm']:.0f} kV/mm [RH]", (xe + 0.6, 0), (30, -10), arrowprops=arr, **lab)
    ax.plot([xe, xe], [-ze, ze], color=INK2, lw=0.0)
    ax.text(0, 0, f"{rec['E_dc_kV_cm']:.1f} kV/cm\nat the null", fontsize=7.4, color="#0d366b", ha="center", va="center",
            zorder=8, bbox=dict(fc="white", ec="none", pad=0.6, alpha=0.85))
    ax.annotate("vessel: borosilicate,\n50 mm OD, 1.5 mm wall", (17, 17.5), (28, 22), arrowprops=arr, **lab)
    ax.annotate("AH core + coil (REF)", (9, 52), (16, 58), arrowprops=arr, **lab)
    ax.annotate("retainer + coupler (ε 4.7 [RH])", (27, 40), (22, 46), arrowprops=arr, **lab)
    ax.annotate("flange (REF): outside the vessel,\noutboard of the AH; the shaft half\nwith side B's pumps", (20, 78),
                (14, 96), arrowprops=arr, **lab)
    ax.annotate("side A: the same, mirrored", (20, -78), (18, -96), arrowprops=arr, **lab)
    ax.set_title("(a) the locked hub to scale, with the lock-down's rings (superseded);\nDC equipotentials every 2 kV",
                 fontsize=9.6, loc="left", color=INK)


def main():
    R = json.load(open(os.path.join(SIM, "hub_locked_results.json")))
    rec, exact, bands = R["record"], R["exact"], R["bands"]
    fig = plt.figure(figsize=(16.5, 10.6), facecolor="white")
    gs = fig.add_gridspec(2, 3, width_ratios=(0.95, 1, 1), height_ratios=(1, 1), hspace=0.36, wspace=0.27, left=0.04,
                          right=0.985, top=0.875, bottom=0.06)
    fig.suptitle("The locked hub, as the lock-down study sized its rings (2026-10-08; the rings superseded by the record, "
                 "docs/rings-design.md)",
                 fontsize=11.8, x=0.01, ha="left", color=INK)
    fig.text(0.01, 0.92, "Designer's stack-up and choices (presets/hub-locked.json): 50 mm borosilicate sphere, 1.5 mm "
             "wall; the rings outside it; the AH cores on the z axis, their flanges outside the vessel; retainer, shaft "
             "coupler, shaft halves with their pumps. 1200 rpm relative.",
             fontsize=8.3, color=INK2)
    section(fig.add_subplot(gs[:, 0]), rec)

    # (b) the field at the null against the bands' equatorial edge, at the pick's DC
    axB = fig.add_subplot(gs[0, 1])
    vg = rec["V_gap_kV"]
    for col, tp in zip(RAMP3, HL.BAND_POLAR):
        q = sorted([b for b in bands if b["theta_p"] == tp], key=lambda b: b["theta_e"])
        axB.plot([b["theta_e"] for b in q], [b["E_centre_kV_cm_per_kV"] * vg for b in q], color=col, lw=1.8, marker="o",
                 ms=4, mec=SURF, label=f"bands from {tp:.0f}°, DC as connected")
    te_grid = np.linspace(45, 80, 71)
    axB.plot(te_grid, [HL.settled(t)[0] * 1e-5 * vg * 1e3 for t in te_grid], color=MUTED, lw=1.3, ls=(0, (5, 2)),
             label="settled, the glass alone leaking")
    for e_t, ls in ((1.0, "-"), (2.0, (0, (4, 2))), (5.0, (0, (1, 1.5)))):
        te_lim = 90.0 - math.degrees(vg / e_t / (2 * HL.HUB["R_v"]))
        if te_lim <= 80.5:
            axB.axvline(te_lim, color=INK2, lw=0.9, ls=ls)
            axB.text(te_lim - 0.4, 2.1, f"{e_t:g} kV/mm", rotation=90, fontsize=7.0, color=INK2, ha="right", va="bottom")
    axB.plot([rec["theta_e"]], [rec["E_dc_kV_cm"]], "o", ms=8, mfc="none", mec=INK, mew=1.4, zorder=6)
    axB.annotate(f"the lock-down's pick: {rec['E_dc_kV_cm']:.1f} kV/cm", (rec["theta_e"], rec["E_dc_kV_cm"]), (6, -14),
                 textcoords="offset points", fontsize=7.4, color=INK)
    axB.set_xlim(44, 81); axB.set_ylim(2, 11)
    style(axB, f"(b) the field at the null against the bands' equatorial edge, {vg:.1f} kV\nacross; lines: the edge each "
               "interface rating allows", "kV/cm", "the bands' equatorial edge (deg from the axis)")
    axB.legend(fontsize=7.0, frameon=True, facecolor="white", edgecolor="none", framealpha=0.92, loc="upper left")

    # (c) the field at the null against the supply, each at its widest allowed bands
    axC = fig.add_subplot(gs[0, 2])
    names = ["dc0", "dc1", "dc2", "dc3"]
    xv = [next(x for x in exact if x["supply"] == nm)["V_gap_kV"] for nm in names]
    for col, key in zip(RAMP_ET, ("1", "2", "5")):
        rows = R["rated"][key]
        ys = []
        for nm in names:
            ok = [x for x in rows if x["supply"] == nm and x["ok"]]
            ys.append(max(x["E_dc_kV_cm"] for x in ok) if ok else np.nan)
        if key == "1":                                             # the exact edge, not the grid's
            ys = [next(x for x in exact if x["supply"] == nm)["E_dc_kV_cm"] for nm in names]
        axC.plot(xv, ys, color=col, lw=2.0 if key == "1" else 1.4, marker="o", ms=5, mec=SURF,
                 label=f"interface {key} kV/mm" + (" (the rating used)" if key == "1" else " (grid of edges)"))
    axC.plot(xv, [next(x for x in exact if x["supply"] == nm)["E_settled_kV_cm"] for nm in names], color=MUTED, lw=1.3,
             ls=(0, (5, 2)), label="1 kV/mm, settled (the glass alone leaking)")
    for nm, x in zip(names, xv):
        axC.annotate(nm, (x, 1.0), ha="center", fontsize=7.2, color=INK2)
    axC.set_ylim(0, 12); axC.set_xlim(10, 35)
    style(axC, "(c) the field at the null against the DC across the rings (0–3 CW stages),\neach at its widest allowed bands",
          "kV/cm", "DC across the rings (kV)")
    axC.legend(fontsize=7.0, frameon=False, loc="upper left")

    # (d) the lock-down's pick and the alternatives
    axT = fig.add_subplot(gs[1, 1:]); axT.axis("off")
    axT.set_title("(d) the lock-down's pick and the alternatives (the record now: 2 + 2 stages, ±15.0 kV, "
                  "7.62 kV/cm with its beads)",
                  fontsize=9.6, loc="left", color=INK)
    b8 = [x for x in R["rings"] if x["ring_name"] == "band 8 mm" and x["theta_deg"] == 50.0 and x["coils"]][0]
    disc = R["discs_inside"]["supplies"]["dc1"]

    def p_of(e):
        return 0.5 * EPS0 * (e * 1e5) ** 2
    rows = []
    for nm in ("dc3", "dc2", "dc1", "dc0"):
        x = next(y for y in exact if y["supply"] == nm)
        rows.append((f"{nm}: bands {x['theta_p']:.0f}–{x['theta_e']:.0f}°" + ("  (its pick)" if nm == rec["supply"] else ""),
                     f"{x['V_gap_kV']:.1f} kV", f"{x['gap_mm']:.1f} mm", f"{x['E_dc_kV_cm']:.1f}", f"{p_of(x['E_dc_kV_cm']):.2f}",
                     f"{x['E_settled_kV_cm']:.1f}", f"{x['z_start']:.3f}", f"{x['C_ring_ref_pF']:.1f} / {x['C_ring_ring_pF']:.1f}"))
    rows.append(("the swing: 8 mm bands at 50°", "±7.4 kV", "", f"±{b8['E_swing_kV_cm']:.1f}",
                 f"0–{p_of(b8['E_swing_kV_cm']):.2f}", "AC", f"{b8['pump']['z']:.3f}",
                 f"{b8['C_ring_ref_pF']:.1f} / {b8['C_ring_ring_pF']:.1f}"))
    rows.append(("not chosen: the Rogowski pair inside", "20.6 kV", "3.14 mm", f"{10 * disc['E0_kV_mm']:.1f}",
                 f"{disc['p0_Pa']:.0f}", "steady", "1.184", "1.0 / 0.7"))
    xs = (0.0, 0.30, 0.39, 0.475, 0.56, 0.645, 0.73, 0.82)
    for x, h_ in zip(xs, ("option", "across", "gap", "kV/cm", "Pa", "settled", "start z", "C to REF / across (pF)")):
        axT.text(x, 0.93, h_, fontsize=7.8, color=INK, weight="bold", transform=axT.transAxes)
    y = 0.84
    for i, rw in enumerate(rows):
        for x, c in zip(xs, rw):
            axT.text(x, y, c, fontsize=7.6, color=INK if i == 0 else (MUTED if i >= 4 else INK2),
                     weight="bold" if i == 0 else "normal", va="top", transform=axT.transAxes)
        y -= 0.075
    notes = [
        "The supply limits the rings, not the vacuum: at 7.8 kV/cm the vacuum is far below its rule. More DC widens the gap "
        "the rings need between them (1 kV/mm along the glass under the retainer [RH]), yet still gains: three stages give "
        f"{rec['E_dc_kV_cm']:.1f} kV/cm, 1.4× one stage. A better-rated interface lets the bands reach the equator: 9.2 kV/cm "
        "at 2 kV/mm, 9.6 at 5.",
        f"The multiplier sags at 100 pF: its third stage adds 4.9 kV, not 7.4 (the 10 GΩ placeholder leakage per ring). "
        f"Each ring's average field to the AH cores is {rec['E_ah_kV_mm']:.1f} kV/mm through the retainer and the seats "
        "(5 kV/mm derated garolite [IR]).",
        "DC through glass drifts: borosilicate leaks (τ ≈ 7 min), so the glass beyond each ring follows it and the field "
        "rises toward the settled value; charge on the vacuum side of the wall can screen it. The swing does neither, at a "
        "fifth of the field.",
    ]
    axT.text(0.0, y - 0.03, "\n".join(textwrap.fill(s_, 150) for s_ in notes), fontsize=7.2, color=INK2, va="top",
             transform=axT.transAxes, linespacing=1.35)
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    fig.savefig(OUT, dpi=130, facecolor="white")
    plt.close(fig)
    print(OUT)


if __name__ == "__main__":
    main()
