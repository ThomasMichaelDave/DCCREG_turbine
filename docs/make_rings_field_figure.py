"""docs/make_rings_field_figure.py -- writes docs/figures/hub-rings-field.png: the field drawings of the rings of record
(sim/hub_rings_build_results.json record: the symmetric supply, each ring on its own chain from the shaft).
  (a) the hub's section: the field's magnitude, the equipotentials and the field lines from ring B to ring A;
  (b) the field along the axis and across the equator inside the vacuum;
  (c) the electrostatic pressure eps0 E^2 / 2 along the same lines;
  (d), (e) ring B's polar and equatorial beads: the field in the gel and the glass around them (local solves);
  below, the numbers.
The DC as connected (the electrostatic solution); the leakage later moves it (sim/hub_drift.py).
Usage: python3 docs/make_rings_field_figure.py
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
from matplotlib.colors import LinearSegmentedColormap              # noqa: E402
from matplotlib.patches import Circle, Polygon, Rectangle, Wedge  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
SIM = os.path.join(HERE, "..", "sim")
sys.path.insert(0, SIM)
import core_rings as CR                                           # noqa: E402
import hub_locked as HL                                           # noqa: E402
import hub_rings_build as B                                       # noqa: E402

SURF, INK, INK2, MUTED, GRID, AXIS = "#fcfcfb", "#0b0b0b", "#52514e", "#898781", "#e1e0d9", "#c3c2b7"
C_A, C_B = "#c0392b", "#1f6fb2"
SEQ = LinearSegmentedColormap.from_list("seq_blue", ["#f4f8fd", "#cde2fb", "#9ec5f4", "#6da7ec", "#3987e5", "#256abf",
                                                     "#184f95", "#0d366b"])
LINE1, LINE2 = "#2a78d6", "#eb6834"                               # categorical slots 1 and 2: the axis, the equator
OUT = os.path.join(HERE, "figures", "hub-rings-field.png")
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


def hub_field(rec):
    """the hub's DC as connected on its finite volumes, both halves: r, z (mm), V (V), |E| (kV/cm), Er, Ez, cond."""
    hub = B.hub_system()
    tp, te = rec["theta_p"], rec["theta_e"]
    res = CR.solve(HL.band(tp, te), 0.5 * (tp + te), True, 0.25, hub=hub, keep=True, maps_fn=HL.maps)
    va, vb = rec["V_A_kV"] * 1e3, rec["V_B_kV"] * 1e3
    cm, dm = 0.5 * (vb + va), 0.5 * (vb - va)
    Va, Vs, cond = res["V_anti"], res["V_sym"], res["cond"]
    h = res["h_mm"]
    nr, nz = Va.shape
    r = (np.arange(nr) + 0.5) * h
    z = (np.arange(nz) + 0.5) * h
    V = np.concatenate([(cm * Vs - dm * Va)[:, ::-1], cm * Vs + dm * Va], axis=1)
    cf = np.concatenate([cond[:, ::-1], cond], axis=1)
    zf = np.concatenate([-z[::-1], z])
    Er = -np.gradient(V, h * 1e-3, axis=0)
    Ez = -np.gradient(V, h * 1e-3, axis=1)
    Em = np.hypot(Er, Ez) * 1e-5                                    # kV/cm
    return dict(r=r, z=zf, V=V, E=Em, Er=Er, Ez=Ez, cond=cf, h=h, hub=hub)


def bead_map(rec, which):
    """the local solve around ring B's bead ('pol' / 'eq') at the record's DC: the box's cells and |E| (kV/mm)."""
    tp, te = rec["theta_p"], rec["theta_e"]
    rho = rec["rho_pol_mm"] if which == "pol" else rec["rho_eq_mm"]
    h_loc, half = 0.025, 4.0
    res = B.hub_beads(tp, te, rho)
    _, vbc = B.hub_potential(res, rec["V_A_kV"] * 1e3, rec["V_B_kV"] * 1e3)
    bx = B._edge_box(tp, te, rho, which, h_loc, half)
    V = B.local_fv(bx["eps"], bx["cond"], rec["V_B_kV"] * 1e3, h_loc, bx["r0"], bx["z0"], vbc)
    Em = np.hypot(np.gradient(V, h_loc * 1e-3, axis=0), np.gradient(V, h_loc * 1e-3, axis=1)) / 1e6
    n = bx["n"]
    r = bx["r0"] + (np.arange(n) + 0.5) * h_loc
    z = bx["z0"] + (np.arange(n) + 0.5) * h_loc
    return dict(r=r, z=z, E=np.ma.masked_where(bx["cond"], Em), V=V, cond=bx["cond"], rho=rho, which=which)


def materials(ax, hub, both=True, lw=0.6):
    """the boundaries: glass, gel, PEEK retainer, G10 coupler; the AH envelopes (REF)."""
    th = np.linspace(-math.pi / 2, math.pi / 2, 400) if both else np.linspace(0, math.pi / 2, 200)
    for rad, col in ((hub["R_in"], "#6f8ea6"), (hub["R_v"], "#6f8ea6"), (hub["R_v"] + hub["fill_t"], "#b9ad8a")):
        ax.plot(rad * np.cos(th), rad * np.sin(th), color=col, lw=lw, zorder=4)
    ax.plot([hub["ret_r"] - hub["cpl_t"]] * 2, [-hub["ret_z"], hub["ret_z"]], color="#b9ad8a", lw=lw, zorder=4)
    ax.plot([hub["ret_r"]] * 2, [-hub["ret_z"], hub["ret_z"]], color="#b9ad8a", lw=lw, zorder=4)
    for s in ((1, -1) if both else (1,)):
        a, b = sorted((s * hub["ah_z"][0], s * hub["ah_z"][1]))
        ax.add_patch(Rectangle((0, a), hub["ah_r"], b - a, fc="#8a8f99", ec="#5d6670", lw=0.6, zorder=5))


def rings(ax, rec, hub):
    tp, te = math.radians(rec["theta_p"]), math.radians(rec["theta_e"])
    ph = np.linspace(tp, te, 60)
    for s, col in ((1, C_B), (-1, C_A)):
        outer = [((hub["R_v"] + 0.45) * math.sin(p), s * (hub["R_v"] + 0.45) * math.cos(p)) for p in ph]
        inner = [(hub["R_v"] * math.sin(p), s * hub["R_v"] * math.cos(p)) for p in ph[::-1]]
        ax.add_patch(Polygon(outer + inner, closed=True, fc=col, ec="white", lw=0.5, zorder=7))
        for t, rho in ((tp, rec["rho_pol_mm"]), (te, rec["rho_eq_mm"])):
            ax.add_patch(Circle(((hub["R_v"] + rho) * math.sin(t), s * (hub["R_v"] + rho) * math.cos(t)), rho, fc=col,
                                ec="white", lw=0.5, zorder=7))


def main():
    R = json.load(open(os.path.join(SIM, "hub_rings_build_results.json")))
    rec = R["record"]
    sw = json.load(open(os.path.join(SIM, "hub_drift_results.json")))["swing"]
    F = hub_field(rec)
    hub = F["hub"]
    fig = plt.figure(figsize=(16.5, 12.4), facecolor="white")
    outer = fig.add_gridspec(1, 2, width_ratios=(1.0, 1.95), wspace=0.16, left=0.045, right=0.968, top=0.89, bottom=0.115)
    right = outer[0, 1].subgridspec(3, 2, height_ratios=(1, 1, 1.25), hspace=0.42, wspace=0.32)
    fig.suptitle(f"The rings' field, as connected: {kv(rec['V_A_kV'])} / {kv(rec['V_B_kV'], '+{:.1f}')} kV on the "
                 f"symmetric supply, {rec['E_null_kV_cm']:.2f} kV/cm and {rec['p_null_Pa']:.2f} Pa at the null, steady",
                 fontsize=12.5, x=0.01, ha="left", color=INK)
    fig.text(0.01, 0.935, "Ring A on its own negative chain from the shaft (node 1), ring B on the positive one (node 4), "
             "two stages each; the bands on the glass from the polar to the equatorial bead. Finite volumes, 0.25 mm "
             "cells; the beads by local solves, 0.025 mm cells.", fontsize=8.6, color=INK2)

    # (a) the section: |E|, equipotentials, field lines
    ax = fig.add_subplot(outer[0, 0])
    keep = F["r"] <= 36.0
    zk = np.abs(F["z"]) <= 40.0
    r, z = F["r"][keep], F["z"][zk]
    E = F["E"][np.ix_(keep, zk)]
    cond = F["cond"][np.ix_(keep, zk)]
    Em = np.ma.masked_where(cond != 0, E)
    Rg, Zg = np.meshgrid(r, z, indexing="ij")
    pc = ax.pcolormesh(Rg, Zg, np.clip(Em, 0, 15.0), cmap=SEQ, vmin=0, vmax=15.0, shading="auto", zorder=1,
                       rasterized=True)
    V = F["V"][np.ix_(keep, zk)]
    ax.contour(Rg, Zg, np.ma.masked_where(cond != 0, V), levels=np.arange(-14e3, 14.01e3, 2e3), colors=INK2,
               linewidths=0.35, zorder=3, negative_linestyles="solid")
    # the field lines in the vacuum: streamlines of E in the meridional plane, seeded across the equator and near the
    # poles (where the field turns toward the AH cores)
    vac = np.hypot(Rg, Zg) < hub["R_in"] - 0.3
    Er = np.where(vac, F["Er"][np.ix_(keep, zk)], np.nan)
    Ez = np.where(vac, F["Ez"][np.ix_(keep, zk)], np.nan)
    seeds = np.array([[x, 0.0] for x in np.arange(1.0, 22.6, 2.4)] + [[x, s_ * 21.0] for x in (1.2, 3.4) for s_ in (1, -1)])
    ax.streamplot(r, z, Er.T, Ez.T, color=INK, linewidth=0.6, arrowsize=0.8, start_points=seeds,
                  integration_direction="both", broken_streamlines=False, zorder=4)
    materials(ax, hub)
    rings(ax, rec, hub)
    lab = dict(fontsize=7.4, color=INK, bbox=dict(fc="white", ec="none", pad=0.6, alpha=0.92), zorder=9)
    arr = dict(arrowstyle="-", color=INK, lw=0.7)
    tm = math.radians(0.5 * (rec["theta_p"] + rec["theta_e"]))
    for s_, nm, v_ in ((1, "B", rec["V_B_kV"]), (-1, "A", rec["V_A_kV"])):
        ax.annotate(f"ring {nm} {kv(v_, '+{:.1f}' if v_ > 0 else '{:.1f}')} kV", ((hub["R_v"] + 0.5) * math.sin(tm),
                    s_ * (hub["R_v"] + 0.5) * math.cos(tm)), (21.5, s_ * 33.0), arrowprops=arr, **lab)
    ax.annotate("gel 0.5", (25.25 * math.sin(math.radians(68)), 25.25 * math.cos(math.radians(68))), (27.0, 3.0),
                arrowprops=arr, **lab)
    ax.annotate("glass 1.5", (24.25 * math.sin(math.radians(77)), 24.25 * math.cos(math.radians(77))), (26.2, -3.5),
                arrowprops=arr, **lab)
    ax.text(0.8, 1.3, f"{rec['E_null_kV_cm']:.2f} kV/cm\nat the null", **lab)
    ax.text(2.2, 37.5, "AH core (REF)", **lab)
    ax.text(2.2, -38.5, "AH core (REF)", **lab)
    ax.text(5.0, -9.0, "vacuum", **lab)
    ax.text(25.5, 25.0, "PEEK", **lab)
    ax.text(30.35, 15.0, "G10", **lab)
    ax.set_aspect("equal")
    ax.set_xlim(0, 36); ax.set_ylim(-40, 40)
    ax.set_xlabel("r (mm)", fontsize=8.6, color=INK2)
    ax.set_ylabel("z (mm), the shaft's axis", fontsize=8.6, color=INK2)
    ax.tick_params(colors=INK2, labelsize=7.8)
    for s_ in ax.spines.values():
        s_.set_color(AXIS)
    cb = fig.colorbar(pc, ax=ax, fraction=0.05, pad=0.02, extend="max", shrink=0.8)
    cb.set_label("field magnitude (kV/cm; 15 and above saturate)", fontsize=8.0, color=INK2)
    cb.ax.tick_params(labelsize=7.4, colors=INK2)
    cb.outline.set_edgecolor(AXIS)
    ax.set_title("(a) the section: field magnitude, equipotentials every 2 kV,\nfield lines in the vacuum (B to A)",
                 fontsize=9.8, loc="left", color=INK)

    # (b) the field along the axis and across the equator, inside the vacuum (the field is axial on both lines)
    i0 = int(np.argmin(np.abs(F["z"])))
    lim = hub["R_in"] - 0.5                                            # one cell off the glass
    jr = F["r"] < lim
    zv = np.abs(F["z"]) < lim
    ez_axis = -F["Ez"][0, zv] * 1e-5                                   # kV/cm, B (top) to A (bottom): positive down
    ez_eq = -0.5 * (F["Ez"][jr, i0] + F["Ez"][jr, i0 - 1]) * 1e-5
    x_eq = np.concatenate([-F["r"][jr][::-1], F["r"][jr]])
    e_eq = np.concatenate([ez_eq[::-1], ez_eq])
    axB = fig.add_subplot(right[0, :])
    axB.axhline(0, color=AXIS, lw=0.8)
    axB.plot(F["z"][zv], ez_axis, color=LINE1, lw=2.0, label="along the axis (z)")
    axB.plot(x_eq, e_eq, color=LINE2, lw=2.0, label="across the equatorial plane (r)")
    axB.set_xlim(-24, 24)
    style(axB, "(b) the field inside the vacuum, its component from B to A (the whole field on both lines)", "kV/cm",
          "position from the null (mm): z along the axis, r across the equatorial plane")
    axB.legend(fontsize=7.6, frameon=False, loc="lower center", bbox_to_anchor=(0.64, 0.02))
    axB.annotate("axis: the field turns toward the AH cores near the poles", (-19.0, float(np.interp(-19.0, F["z"][zv],
                 ez_axis))), (-17.0, -6.0), fontsize=7.4, color=INK2, arrowprops=dict(arrowstyle="-", color=INK2, lw=0.6))
    c5 = (np.abs(F["z"][zv]) <= 5.0)
    u_axis = 100 * (ez_axis[c5].max() - ez_axis[c5].min()) / rec["E_null_kV_cm"]
    r5 = F["r"][jr] <= 5.0
    u_eq = 100 * (ez_eq[r5].max() - ez_eq[r5].min()) / rec["E_null_kV_cm"]

    # (c) the pressure along the same lines
    axC = fig.add_subplot(right[1, :])
    axC.plot(F["z"][zv], 0.5 * EPS0 * (ez_axis * 1e5) ** 2, color=LINE1, lw=2.0, label="along the axis (z)")
    axC.plot(x_eq, 0.5 * EPS0 * (e_eq * 1e5) ** 2, color=LINE2, lw=2.0, label="across the equatorial plane (r)")
    axC.set_xlim(-24, 24)
    style(axC, f"(c) the electrostatic pressure ε0 E² / 2: steady, {sw['E_pp_kV_cm'] / sw['E_mean_kV_cm'] * 200:.1f} % "
               "p-p at 120 Hz (the supply's ripple)", "Pa", "position from the null (mm)")
    axC.legend(fontsize=7.6, frameon=False, loc="upper center")

    # (d), (e) the beads
    for k, which in enumerate(("pol", "eq")):
        M = bead_map(rec, which)
        axE = fig.add_subplot(right[2, k])
        Rb, Zb = np.meshgrid(M["r"], M["z"], indexing="ij")
        pm = axE.pcolormesh(Rb, Zb, M["E"], cmap=SEQ, vmin=0, vmax=6.0, shading="auto", rasterized=True)
        axE.contour(Rb, Zb, np.ma.masked_where(M["cond"], M["V"]), levels=12, colors=INK2, linewidths=0.3)
        th = np.linspace(0, math.pi / 2, 400)
        for rad, col in ((hub["R_in"], "#6f8ea6"), (hub["R_v"], "#6f8ea6"), (hub["R_v"] + hub["fill_t"], "#b9ad8a")):
            axE.plot(rad * np.sin(th), rad * np.cos(th), color=col, lw=0.8)
        q = rec["E_pol"] if which == "pol" else rec["E_eq"]
        at = q["rings"]["B"]["at_gel"]
        axE.plot([at[0]], [at[1]], marker="o", ms=7, mfc="none", mec=INK, mew=1.3)
        axE.annotate(f"peak {q['rings']['B']['gel']:.2f} kV/mm\nin the gel (design 5)", (at[0], at[1]), (0.04, 0.90),
                     textcoords="axes fraction", va="top", fontsize=7.4, color=INK,
                     bbox=dict(fc="white", ec="none", pad=0.6, alpha=0.92), arrowprops=dict(arrowstyle="-", color=INK,
                                                                                          lw=0.7))
        axE.set_aspect("equal")
        axE.set_xlim(M["r"][0], M["r"][-1]); axE.set_ylim(M["z"][0], M["z"][-1])
        nm = "polar" if which == "pol" else "equatorial"
        style(axE, f"({'d' if k == 0 else 'e'}) ring B's {nm} bead, Ø{2 * M['rho']:g} mm", "z (mm)", "r (mm)")
        axE.grid(False)
        cb = fig.colorbar(pm, ax=axE, fraction=0.046, pad=0.03, extend="max")
        cb.set_label("kV/mm (6+ saturate)", fontsize=7.6, color=INK2)
        cb.ax.tick_params(labelsize=7.2, colors=INK2)
        cb.outline.set_edgecolor(AXIS)

    # the numbers
    txt = (f"Ring A {kv(rec['V_A_kV'])} kV, ring B {kv(rec['V_B_kV'], '+{:.1f}')} kV: {rec['V_gap_kV']:.1f} kV across, the "
           f"null at the shaft's potential (0 V) by symmetry. Bands {rec['theta_p']:.2f}–{rec['theta_e']:.2f}° from the "
           f"axis, {rec['gap_mm']:.1f} mm apart along the glass ({rec['V_gap_kV'] / rec['gap_mm']:.2f} kV/mm). At the "
           f"null {rec['E_null_kV_cm']:.2f} kV/cm, {rec['p_null_Pa']:.2f} Pa; within ±5 mm it varies {u_axis:.1f} % along "
           f"the axis and {u_eq:.1f} % across the equator. The supply's ripple moves it {sw['E_pp_kV_cm']:.3f} kV/cm p-p "
           f"(sim/hub_drift.py swing): the field does not swing. Beads in the gel: polar {rec['E_pol']['gel']:.2f}, "
           f"equatorial {rec['E_eq']['gel']:.2f} kV/mm (design 5); in the glass {rec['E_pol']['glass']:.2f} / "
           f"{rec['E_eq']['glass']:.2f}. Each ring to the AH cores: {rec['E_ah_kV_mm']:.2f} kV/mm on average.")
    fig.text(0.01, 0.012, "\n".join(textwrap.wrap(txt, 245)), fontsize=8.0, color=INK2, va="bottom")
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    fig.savefig(OUT, dpi=130, facecolor="white")
    plt.close(fig)
    print(OUT, json.dumps(dict(uniformity_axis_pc=u_axis, uniformity_eq_pc=u_eq)))


if __name__ == "__main__":
    main()
