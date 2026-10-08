"""docs/make_hub_locked_figure.py -- writes docs/figures/hub-locked.png: the hub as the designer locked it
(presets/hub-locked.json) and the field at the AH null from the two electrode rings around the vessel, against the two
Rogowski electrodes inside it (sim/hub_locked.py -> sim/hub_locked_results.json).
  (a) the hub's section to scale: left, the rings (an 8 mm band at 50 deg) with their DC equipotentials every 2 kV;
      right, the Rogowski pair on the null;
  (b) the field at the null against the rings' polar angle: DC as connected, DC settled, the swing; the pair inside;
  (c) the rings' strays: to the shaft side and between the rings;
  (d) the options side by side.
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
import core_null_field as NF                                      # noqa: E402
import core_rings as CR                                           # noqa: E402
import hub_locked as HL                                           # noqa: E402

SURF, INK, INK2, MUTED, GRID, AXIS = "#fcfcfb", "#0b0b0b", "#52514e", "#898781", "#e1e0d9", "#c3c2b7"
RAMP3 = ("#86b6ef", "#3987e5", "#0d366b")                         # ordinal blue: the ring forms, small to large
C_A, C_B, F_A, F_B = "#c0392b", "#1f6fb2", "#f6d5d1", "#dbe7f3"
STEEL, GLASS, COMP = "#8a8f99", "#cfe3ee", "#e9e1c9"
OUT = os.path.join(HERE, "figures", "hub-locked.png")
DRAWN = ("band 8 mm", 50.0)
EPS0 = 8.8541878128e-12


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


def section(ax, d1, v_a, v_b):
    hub = HL.HUB
    ax.add_patch(Rectangle((-hub["ret_r"], -hub["ret_z"]), 2 * hub["ret_r"], 2 * hub["ret_z"], fc=COMP, ec="#b9ad8a",
                           lw=0.6, zorder=1))
    ax.add_patch(Wedge((0, 0), hub["R_v"], 0, 360, width=hub["R_v"] - hub["R_in"], fc=GLASS, ec="#6f8ea6", lw=0.6, zorder=2))
    ax.add_patch(Wedge((0, 0), hub["R_in"], 0, 360, fc="white", ec="none", zorder=2))
    for s in (1, -1):
        z0, z1 = sorted((s * hub["ah_z"][0], s * hub["ah_z"][1]))
        ax.add_patch(Rectangle((-hub["ah_r"], z0), 2 * hub["ah_r"], z1 - z0, fc=STEEL, ec="#5d6670", lw=0.6, zorder=3))
        z0, z1 = sorted((s * hub["fl_z"][0], s * hub["fl_z"][1]))
        ax.add_patch(Rectangle((-hub["fl_r"], z0), 2 * hub["fl_r"], z1 - z0, fc=STEEL, ec="#5d6670", lw=0.6, zorder=3))
        z0, z1 = sorted((s * hub["fl_z"][1], s * 112.0))
        ax.add_patch(Rectangle((-hub["sh_r"], z0), 2 * hub["sh_r"], z1 - z0, fc=STEEL, ec="#5d6670", lw=0.6, zorder=3))
    # left half: the rings and their DC field (as connected), from the finite volumes
    ring = HL.RINGS[DRAWN[0]]
    res = CR.solve(ring, DRAWN[1], True, 0.25, hub=hub, keep=True, maps_fn=HL.maps)
    cm, dm = 0.5 * (v_b + v_a), 0.5 * (v_b - v_a)                  # B (upper) and A (lower)
    Va, Vs, cond = res["V_anti"], res["V_sym"], res["cond"]
    h = res["h_mm"]
    nr, nz = Va.shape
    r = (np.arange(nr) + 0.5) * h
    z = (np.arange(nz) + 0.5) * h
    up = cm * Vs + dm * Va
    lo = cm * Vs - dm * Va
    Vf = np.concatenate([lo[:, ::-1], up], axis=1)
    cf = np.concatenate([cond[:, ::-1], cond], axis=1)
    zf = np.concatenate([-z[::-1], z])
    keep = r <= 62.0
    Rg, Zg = np.meshgrid(-r[keep], zf, indexing="ij")
    Vm = np.ma.masked_where(cf[keep] != 0, Vf[keep])
    ax.contour(Rg, Zg, Vm, levels=np.arange(-12e3, 6.01e3, 2e3), colors=INK2, linewidths=0.45, zorder=4,
               negative_linestyles="solid")
    th = math.radians(DRAWN[1])
    half = 0.5 * ring["w"] / hub["R_v"]
    for s, fc, ec in ((1, F_B, C_B), (-1, F_A, C_A)):
        ph = np.linspace(th - half, th + half, 30)
        outer = [(-(hub["R_v"] + 0.9) * math.sin(p), s * (hub["R_v"] + 0.9) * math.cos(p)) for p in ph]
        inner = [(-hub["R_v"] * math.sin(p), s * hub["R_v"] * math.cos(p)) for p in ph[::-1]]
        ax.add_patch(Polygon(outer + inner, closed=True, fc=ec, ec=ec, lw=1.0, zorder=6))
    # right half: the Rogowski pair on the null (drawn to scale; their stems would enter from the side)
    g, shape = d1["g_min_mm"], d1["shape"]
    for side, fc, ec in ((1, F_B, C_B), (-1, F_A, C_A)):
        p = NF.rogowski(g, side=side, rs=None, **shape)
        p = np.vstack([p, [[0.0, p[-1, 1]]]])
        ax.add_patch(Polygon(p, closed=True, fc=fc, ec=ec, lw=0.9, zorder=6))
    ax.plot([0, 0], [-112, 112], color=INK2, lw=0.6, ls=(0, (6, 3)), zorder=5)
    ax.set_aspect("equal")
    ax.set_xlim(-62, 62); ax.set_ylim(-112, 112)
    ax.set_xlabel("r (mm): left, the rings; right, the pair inside", fontsize=8.3, color=INK2)
    ax.set_ylabel("z (mm), the shaft's axis", fontsize=8.3, color=INK2)
    ax.tick_params(colors=INK2, labelsize=7.8)
    for s_ in ax.spines.values():
        s_.set_color(AXIS)
    lab = dict(fontsize=7.0, color=INK, bbox=dict(fc="white", ec="none", pad=0.5, alpha=0.88), zorder=8)
    arr = dict(arrowstyle="-", lw=0.5, color=INK2)
    ax.annotate(f"ring B, +{v_b / 1e3:.1f} kV\n(8 mm band at {DRAWN[1]:.0f}°)", (-19.5, 16.5), (-60, 26), arrowprops=arr, **lab)
    ax.annotate(f"ring A, −{-v_a / 1e3:.1f} kV", (-19.5, -16.5), (-60, -24), arrowprops=arr, **lab)
    ax.annotate("vessel: borosilicate,\n50 mm OD, 1.5 mm wall [RH]", (16, -19), (24, -44), arrowprops=arr, **lab)
    ax.annotate("AH core + coil (REF)", (9, 52), (16, 58), arrowprops=arr, **lab)
    ax.annotate("retainer + coupler\n(ε 4.7 [RH])", (27, 32), (34, 40), arrowprops=arr, **lab)
    ax.annotate("flange, shaft half (REF)\nside B: its electrostatic\n+ magnetic pump", (20, 78), (24, 94), arrowprops=arr, **lab)
    ax.annotate("side A: the same, mirrored", (20, -78), (24, -96), arrowprops=arr, **lab)
    ax.annotate(f"the pair inside: {g:.2f} mm gap,\n{d1['E0_kV_cm']:.1f} kV/cm at the null", (5, 4), (24, 10),
                arrowprops=arr, **lab)
    ax.set_title("(a) the locked hub to scale; the rings' DC equipotentials every 2 kV (left),\n"
                 "the Rogowski pair on the null (right; its stems would enter from the side)", fontsize=9.6, loc="left",
                 color=INK)


def main():
    R = json.load(open(os.path.join(SIM, "hub_locked_results.json")))
    d1, disc = R["design_dc1"], R["discs_inside"]
    v_a, v_b = d1["V_A_kV"] * 1e3, d1["V_B_kV"] * 1e3
    rings = R["rings"]
    fig = plt.figure(figsize=(16.5, 10.6), facecolor="white")
    gs = fig.add_gridspec(2, 3, width_ratios=(0.95, 1, 1), height_ratios=(1, 1), hspace=0.36, wspace=0.27, left=0.04,
                          right=0.985, top=0.875, bottom=0.06)
    fig.suptitle("The locked hub: the field at the AH null from two rings around the 50 mm vessel, against the Rogowski "
                 "pair inside it", fontsize=11.8, x=0.01, ha="left", color=INK)
    va_s = f"{v_a / 1e3:.1f}".replace("-", "\u2212")
    fig.text(0.01, 0.92, "Designer's stack-up (presets/hub-locked.json): borosilicate sphere, rings around it, the AH cores "
             "with their coils on the z axis, retainer, shaft coupler, the shaft halves with their pumps. Stack of record, "
             f"1200 rpm relative; DC from the null's supply ({va_s} / +{v_b / 1e3:.1f} kV).", fontsize=8.3, color=INK2)
    section(fig.add_subplot(gs[:, 0]), d1, v_a, v_b)

    # (b) the field at the null against the ring's polar angle
    axE = fig.add_subplot(gs[0, 1])
    for col, nm in zip(RAMP3, HL.RINGS):
        q = sorted([x for x in rings if x["ring_name"] == nm and x["coils"]], key=lambda x: x["theta_deg"])
        th = [x["theta_deg"] for x in q]
        axE.plot(th, [x["E_dc_kV_cm"] for x in q], color=col, lw=1.8, marker="o", ms=4, mec=SURF,
                 label=f"{nm}: DC as connected")
    q8 = sorted([x for x in rings if x["ring_name"] == "band 8 mm" and x["coils"]], key=lambda x: x["theta_deg"])
    q8n = sorted([x for x in rings if x["ring_name"] == "band 8 mm" and not x["coils"]], key=lambda x: x["theta_deg"])
    th = [x["theta_deg"] for x in q8]
    axE.plot(th, [x["E_dc_kV_cm"] for x in q8n], color=RAMP3[2], lw=1.0, ls=(0, (4, 2)),
             label="band 8 mm without the AH cores")
    axE.plot(th, [x["E_settled_kV_cm"] for x in q8], color=MUTED, lw=1.6, ls=(0, (5, 2)),
             label=f"band 8 mm: DC settled, the glass leaking (τ ≈ {R['glass_tau_s'] / 60:.0f} min)")
    axE.plot(th, [x["E_swing_kV_cm"] for x in q8], color=MUTED, lw=1.4, ls=(0, (1, 1.6)),
             label="band 8 mm: the 120 Hz swing, peak (float)")
    e_in = disc["supplies"]["dc1"]["E0_kV_mm"] * 10
    axE.axhline(e_in, color=INK, lw=1.4)
    axE.text(80.5, e_in * 1.08, f"the Rogowski pair inside: {e_in:.1f} kV/cm", fontsize=7.4, color=INK, ha="right",
             va="bottom")
    axE.set_yscale("log"); axE.set_ylim(0.5, 150)
    axE.set_xticks(HL.THETAS)
    style(axE, "(b) the field at the null against the rings' polar angle", "kV/cm",
          "the ring's polar angle from the axis (deg); 90 = the equator")
    axE.legend(fontsize=7.0, frameon=True, facecolor="white", edgecolor="none", framealpha=0.92, loc="upper left",
               bbox_to_anchor=(0.0, 0.81))

    # (c) the strays
    axC = fig.add_subplot(gs[0, 2])
    for col, nm in zip(RAMP3, HL.RINGS):
        q = sorted([x for x in rings if x["ring_name"] == nm and x["coils"]], key=lambda x: x["theta_deg"])
        th = [x["theta_deg"] for x in q]
        axC.plot(th, [x["C_ring_ref_pF"] for x in q], color=col, lw=1.8, marker="o", ms=4, mec=SURF, label=f"{nm}: to REF")
        axC.plot(th, [x["C_ring_ring_pF"] for x in q], color=col, lw=1.1, ls=(0, (1, 1.5)), label=f"{nm}: ring to ring")
    axC.set_ylim(0, 18); axC.set_xticks(HL.THETAS)
    style(axC, "(c) the rings' strays: each to the shaft side (REF), and between them", "pF",
          "the ring's polar angle from the axis (deg)")
    axC.legend(fontsize=7.0, frameon=False, loc="upper left", ncol=2)

    # (d) the options side by side
    axT = fig.add_subplot(gs[1, 1:]); axT.axis("off")
    axT.set_title("(d) the options in the locked hub", fontsize=9.6, loc="left", color=INK)
    b8 = [x for x in q8 if x["theta_deg"] == DRAWN[1]][0]
    best_set = max(q8, key=lambda x: x["E_settled_kV_cm"])
    best_sw = max(q8, key=lambda x: x["E_swing_kV_cm"])

    def p_of(e_kv_cm):
        return 0.5 * EPS0 * (e_kv_cm * 1e5) ** 2
    rows = [("the Rogowski pair inside, DC (dc1)", f"{e_in:.1f}", f"{p_of(e_in):.0f}", "steady",
             "z 1.184 at start, 2.14 W", "two feedthroughs in the glass; the stems enter from the side"),
            (f"rings outside, DC as connected (8 mm band, {DRAWN[1]:.0f}°)", f"{b8['E_dc_kV_cm']:.1f}",
             f"{p_of(b8['E_dc_kV_cm']):.2f}", "drifts as the glass leaks", "unchanged", "the rings under the retainer"),
            (f"rings outside, DC settled (glass alone leaking, {best_set['theta_deg']:.0f}°)",
             f"{best_set['E_settled_kV_cm']:.1f}", f"{p_of(best_set['E_settled_kV_cm']):.2f}",
             f"after ~{5 * R['glass_tau_s'] / 60:.0f} min", "unchanged", "set by glass, retainer and wall charge"),
            (f"rings outside, the swing (8 mm band, {best_sw['theta_deg']:.0f}°)", f"±{best_sw['E_swing_kV_cm']:.1f}",
             f"0–{p_of(best_sw['E_swing_kV_cm']):.2f}", "120 Hz AC", f"z {best_sw['pump']['z']:.3f}, "
             f"{best_sw['pump']['P_belt_W']:.2f} W", "the float wiring, 1 nF each")]
    xs = (0.0, 0.355, 0.415, 0.475, 0.61, 0.75)
    for x, h_ in zip(xs, ("option", "kV/cm", "Pa", "in time", "the pump", "the hub needs")):
        axT.text(x, 0.93, h_, fontsize=7.8, color=INK, weight="bold", transform=axT.transAxes)
    y = 0.84
    for i, rw in enumerate(rows):
        for x, c in zip(xs, rw):
            axT.text(x, y, textwrap.fill(c, {0.61: 16, 0.75: 34, 0.475: 18}.get(x, 60)), fontsize=7.6,
                     color=INK if i == 0 else INK2, weight="bold" if i == 0 else "normal", va="top",
                     transform=axT.transAxes)
        y -= 0.12
    notes = [
        f"Inside the vacuum the pair reaches the rule's field ({disc['supplies']['dc1']['Esurf_max_kV_mm']:.2f} kV/mm on "
        f"its surface): {e_in / b8['E_dc_kV_cm']:.0f}× the rings' DC field as connected, "
        f"{e_in / best_set['E_settled_kV_cm']:.0f}× their settled field. It fits the 50 mm vessel with "
        f"{disc['fits']['corner_to_wall_mm']:.0f} mm to spare.",
        "Outside, the rings reach the vacuum through the glass and the retainer. The AH cores at the shaft's potential, "
        f"next to the poles, take {100 * (1 - b8['E_dc_kV_cm'] / [x for x in q8n if x['theta_deg'] == DRAWN[1]][0]['E_dc_kV_cm']):.0f} % "
        "of the rings' field; nearer the equator the rings couple to each other instead (C ring to ring rises steeply "
        "past 70°).",
        "DC through glass is not steady: borosilicate leaks (ρ ≈ 1e13 Ωm at 25 °C [IR], τ = ε/σ ≈ 7 min), so the caps "
        "beyond each ring drift toward the ring's potential. The settled line assumes the glass alone leaks. The retainer, "
        "the PEEK seats and charge on the vacuum side of the wall all shift it.",
        "The swing keeps the pump near its bare gain (z 1.29 against 1.31), but at the pump's ±7.4 kV it gives the least "
        "field.",
    ]
    axT.text(0.0, y - 0.03, "\n".join(textwrap.fill(s_, 150) for s_ in notes), fontsize=7.2, color=INK2, va="top",
             transform=axT.transAxes, linespacing=1.35)
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    fig.savefig(OUT, dpi=130, facecolor="white")
    plt.close(fig)
    print(OUT)


if __name__ == "__main__":
    main()
