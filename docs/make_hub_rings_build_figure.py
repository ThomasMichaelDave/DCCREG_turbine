"""docs/make_hub_rings_build_figure.py -- writes docs/figures/hub-rings-build.png: the rings as built (sim/hub_rings_build.py
-> sim/hub_rings_build_results.json): the PEEK retainer with its gel-filled pocket, the copper bands with beaded edges,
and the stages the rings' hold-off allows.
  (a) the record's rings to scale: the bands and their beads under the gel and the retainer, DC equipotentials;
  (b) the field at the null against the DC across the rings, each supply at its edge-limited bands, for the four pairs
      of ratings (the interface along the glass; the gel at the beads);
  (c) the polar bead against the AH: its peak field per kV of the ring, and the ring potential it holds;
  (d) the retainer's permittivity: the field at the null barely moves, the strays do;
  (e) the best design of each pair of ratings, solved directly.
Usage: python3 docs/make_hub_rings_build_figure.py
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
from matplotlib.patches import Circle, Polygon, Rectangle, Wedge  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
SIM = os.path.join(HERE, "..", "sim")
sys.path.insert(0, SIM)
import core_rings as CR                                           # noqa: E402
import hub_locked as HL                                           # noqa: E402
import hub_rings_build as B                                       # noqa: E402

SURF, INK, INK2, MUTED, GRID, AXIS = "#fcfcfb", "#0b0b0b", "#52514e", "#898781", "#e1e0d9", "#c3c2b7"
RAMP4 = ("#0d366b", "#1c5cab", "#3987e5", "#86b6ef")             # ordinal blue: the ratings pairs, design first
C_A, C_B = "#c0392b", "#1f6fb2"
STEEL, GLASS, PEEK, GEL, G10 = "#8a8f99", "#cfe3ee", "#efe6cf", "#f6f1a8", "#d9cfa6"
OUT = os.path.join(HERE, "figures", "hub-rings-build.png")
PAIRS = ("1/5", "1/8", "2/5", "2/8")


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


def supply_name(d):
    return (f"A on {d['n_a']} + B on {d['n_cw']}" if d["n_a"] else f"B on {d['n_cw']}") + " stages"


def section(ax, rec, R):
    hub = B.hub_system()
    Rv, Rin = hub["R_v"], hub["R_in"]
    tp, te = rec["theta_p"], rec["theta_e"]
    rp, rq = rec["rho_pol_mm"], rec["rho_eq_mm"]
    # the retainer (PEEK) and the coupler (G10), the gel pocket with its bead grooves, the glass, the vacuum
    ax.add_patch(Rectangle((0, -hub["ret_z"]), hub["ret_r"], 2 * hub["ret_z"], fc=G10, ec="none", zorder=1))
    ax.add_patch(Rectangle((0, -hub["ret_z"]), hub["ret_r"] - hub["cpl_t"], 2 * hub["ret_z"], fc=PEEK, ec="none", zorder=1))
    ax.add_patch(Wedge((0, 0), Rv + hub["fill_t"], -90, 90, width=hub["fill_t"], fc=GEL, ec="none", zorder=2))
    for s in (1, -1):
        for th, rho in ((tp, rp), (te, rq)):
            t = math.radians(th)
            c = ((Rv + rho) * math.sin(t), s * (Rv + rho) * math.cos(t))
            ax.add_patch(Circle(c, rho + 0.5, fc=GEL, ec="none", zorder=2))
    ax.add_patch(Wedge((0, 0), Rv, -90, 90, width=Rv - Rin, fc=GLASS, ec="#6f8ea6", lw=0.6, zorder=3))
    ax.add_patch(Wedge((0, 0), Rin, -90, 90, fc="white", ec="none", zorder=3))
    for s in (1, -1):                                              # the AH: core (MnZn), former (G-10), coil; REF
        a, b = sorted((s * hub["ah_z"][0], s * 46.0))
        ax.add_patch(Rectangle((0, a), hub["ah_r"], b - a, fc=STEEL, ec="#5d6670", lw=0.6, zorder=3))
    # the DC: the record's bands (plain) on the hub's finite volumes
    res = CR.solve(HL.band(tp, te), 0.5 * (tp + te), True, 0.25, hub=hub, keep=True, maps_fn=HL.maps)
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
    keep = r <= 36.0
    Rg, Zg = np.meshgrid(r[keep], zf, indexing="ij")
    step = 2e3
    lv = np.arange(math.floor(va / step) * step, vb + 1, step)
    ax.contour(Rg, Zg, np.ma.masked_where(cf[keep] != 0, Vf[keep]), levels=lv, colors=INK2, linewidths=0.4, zorder=4,
               negative_linestyles="solid")
    ph = np.linspace(math.radians(tp), math.radians(te), 60)
    for s, col in ((1, C_B), (-1, C_A)):
        outer = [((Rv + 0.45) * math.sin(p), s * (Rv + 0.45) * math.cos(p)) for p in ph]
        inner = [(Rv * math.sin(p), s * Rv * math.cos(p)) for p in ph[::-1]]
        ax.add_patch(Polygon(outer + inner, closed=True, fc=col, ec=col, lw=0.6, zorder=6))
        for th, rho in ((tp, rp), (te, rq)):
            t = math.radians(th)
            ax.add_patch(Circle(((Rv + rho) * math.sin(t), s * (Rv + rho) * math.cos(t)), rho, fc=col, ec=col, zorder=6))
    ax.set_aspect("equal")
    ax.set_xlim(0, 36); ax.set_ylim(-40, 40)
    ax.set_xlabel("r (mm)", fontsize=8.3, color=INK2)
    ax.set_ylabel("z (mm), the shaft's axis", fontsize=8.3, color=INK2)
    ax.tick_params(colors=INK2, labelsize=7.8)
    for s_ in ax.spines.values():
        s_.set_color(AXIS)
    lab = dict(fontsize=6.9, color=INK, bbox=dict(fc="white", ec="none", pad=0.5, alpha=0.92), zorder=8)
    arr = dict(arrowstyle="-", lw=0.5, color=INK2)
    t_p, t_e = math.radians(tp), math.radians(te)
    pb = ((Rv + 2 * rp) * math.sin(t_p), (Rv + 2 * rp) * math.cos(t_p))
    qb = ((Rv + rq) * math.sin(t_e) + rq * math.cos(t_e), (Rv + rq) * math.cos(t_e) - rq * math.sin(t_e))
    ax.annotate(f"ring B, {kv(rec['V_B_kV'], '+{:.1f}')} kV: Cu foil {B.FOIL_T:g} mm,\n{tp:.1f}–{te:.1f}°; polar bead "
                f"Ø{2 * rp:g} mm:\n{rec['E_pol']['gel']:.1f} kV/mm in the gel", pb, (12.6, 39.3), arrowprops=arr, va="top",
                **lab)
    ax.annotate(f"equatorial bead Ø{2 * rq:g} mm:\n{rec['E_eq']['gel']:.1f} kV/mm in the gel", qb, (24.5, 27.0),
                arrowprops=arr, **lab)
    ax.annotate(f"ring A, {kv(rec['V_A_kV'])} kV", (Rv * math.sin(0.5 * (t_p + t_e)), -Rv * math.cos(0.5 * (t_p + t_e))),
                (2.0, -37.0), arrowprops=arr, **lab)
    ax.annotate(f"{rec['gap_mm']:.1f} mm along the glass:\n{rec['E_t_kV_mm']:g} kV/mm [RH]", (Rv + 0.3, 0.0), (27.2, -6.0),
                arrowprops=arr, **lab)
    ax.annotate("silicone gel, 0.5 mm\n(ε 2.9), void-free", (Rv * math.sin(1.25) + 0.3, Rv * math.cos(1.25)),
                (26.0, 11.0), arrowprops=arr, **lab)
    ax.annotate("PEEK retainer\n(ε 3.2)", (24.0, 31.0), (24.0, 31.0), arrowprops=None, **lab)
    ax.annotate("G10\ncoupler", (31.5, -24.0), (30.8, -28.5), arrowprops=None, **lab)
    ax.annotate("AH coil end (REF)", (hub["ah_r"] - 1.0, hub["ah_z"][0]), (12.6, 33.4), arrowprops=arr, **lab)
    ax.annotate("glass 1.5 mm", (Rin * math.sin(1.0), -Rin * math.cos(1.0)), (6.0, -16.0), arrowprops=arr, **lab)
    ax.text(0.6, 0.0, f"{rec['E_null_kV_cm']:.1f} kV/cm\nat the null", fontsize=7.4, color="#0d366b", ha="left",
            va="center", zorder=8, bbox=dict(fc="white", ec="none", pad=0.6, alpha=0.85))
    ax.set_title(f"(a) the rings as built, to scale (ring {supply_name(rec)});\nDC equipotentials every 2 kV",
                 fontsize=9.6, loc="left", color=INK)


def main():
    R = json.load(open(os.path.join(SIM, "hub_rings_build_results.json")))
    rec = R["record"]
    fig = plt.figure(figsize=(16.5, 10.6), facecolor="white")
    gs = fig.add_gridspec(2, 3, width_ratios=(0.72, 1, 1), height_ratios=(1, 1), hspace=0.38, wspace=0.3, left=0.045,
                          right=0.96, top=0.875, bottom=0.06)
    fig.suptitle(f"The rings as built: the edges set the stages — ring {supply_name(rec)}, {rec['V_gap_kV']:.1f} kV across, "
                 f"{rec['E_null_kV_cm']:.1f} kV/cm at the null", fontsize=11.8, x=0.01, ha="left", color=INK)
    fig.text(0.01, 0.92, "The retainer: unfilled PEEK with a 0.5 mm pocket over the glass, filled void-free with silicone "
             "gel; G10 coupler outside. The rings: 0.1 mm copper foil, beaded edges. Leakage 100 GΩ per ring (estimate). "
             "Limits: the gap along the glass, and both beads in the gel.", fontsize=8.3, color=INK2)
    section(fig.add_subplot(gs[:, 0]), rec, R)

    # (b) the field at the null against the DC across the rings, each supply at its edge-limited bands
    axB = fig.add_subplot(gs[0, 1])
    for col, key in zip(RAMP4, PAIRS):
        e_t, e_g = (float(x) for x in key.split("/"))
        for fam, mk in ((0, "o"), (1, "s")):
            q = sorted([d for d in R["designs"] if d["E_t_kV_mm"] == e_t and d["E_gel_kV_mm"] == e_g and d["feasible"]
                        and (d["n_a"] > 0) == bool(fam)], key=lambda d: d["V_gap_kV"])
            if q:
                axB.plot([d["V_gap_kV"] for d in q], [d["E_null_kV_cm"] for d in q], color=col, lw=1.5 if fam else 1.1,
                         ls="-" if fam else (0, (3, 2)), marker=mk, ms=4, mec=SURF)
        axB.plot([], [], color=col, lw=1.5, label=f"interface {e_t:g}, gel {e_g:g} kV/mm" + (" (design)" if key == "1/5"
                                                                                           else ""))
        bv = R["best_edges"].get(key)
        if bv:
            axB.plot([bv["V_gap_kV"]], [bv["E_null_kV_cm"]], "o", ms=9, mfc="none", mec=col, mew=1.4, zorder=6)
    axB.plot([rec["V_gap_kV"]], [rec["E_null_kV_cm"]], "o", ms=12, mfc="none", mec=INK, mew=1.4, zorder=7)
    axB.annotate(f"the record: {rec['E_null_kV_cm']:.1f} kV/cm", (rec["V_gap_kV"], rec["E_null_kV_cm"]), (6, -58),
                 textcoords="offset points", fontsize=7.4, color=INK, ha="center",
                 arrowprops=dict(arrowstyle="-", lw=0.5, color=INK2))
    lock = R["record_in"]
    axB.plot([lock["V_gap_kV"]], [lock["E_dc_kV_cm"]], "x", ms=7, color=MUTED, mew=1.4, zorder=6)
    axB.annotate("the lock-down's record\n(edges not checked)", (lock["V_gap_kV"], lock["E_dc_kV_cm"]), (60, -62),
                 textcoords="offset points", fontsize=7.0, color=MUTED, ha="left",
                 arrowprops=dict(arrowstyle="-", lw=0.5, color=MUTED))
    style(axB, "(b) the field at the null against the DC across the rings, each supply at\nits edge-limited bands "
               "(dashed: ring B's chain only; solid: both rings' chains)", "kV/cm", "DC across the rings (kV)")
    axB.legend(fontsize=7.0, frameon=True, facecolor="white", edgecolor="none", framealpha=0.92, loc="upper left")
    axB.set_ylim(0, None)

    # (c) the polar bead against the AH: per kV of the ring, and the ring potential it holds
    axC = fig.add_subplot(gs[0, 2])
    vb = lock["V_B_kV"]
    for col, rho in zip((RAMP4[0], RAMP4[2]), B.RHO_POL):
        q = sorted([t for t in R["tables"]["polar_at_record"] if t["rho_e_mm"] == rho and t["theta_e"] == 50.0],
                   key=lambda t: t["theta_p"])
        c = [t["rings"]["B"]["gel"] / vb for t in q]
        axC.plot([t["theta_p"] for t in q], [10 * x for x in c], color=col, lw=1.8, marker="o", ms=4, mec=SURF,
                 label=f"bead Ø{2 * rho:g} mm")
    axC.set_xlim(19, 46)
    style(axC, "(c) the polar bead faces the AH coil's end: its peak field in the gel per\n10 kV on the ring "
               "(bands to 50°; the other ring adds little)", "kV/mm per 10 kV", "the bands' polar edge (deg from the axis)")
    axC.legend(fontsize=7.0, frameon=False, loc="upper right")
    ax2 = axC.twinx()
    lo, hi = axC.get_ylim()
    ax2.set_ylim(lo, hi)
    vs = [v for v in range(10, 31, 2) if lo < 50.0 / v < hi]
    ax2.set_yticks([50.0 / v for v in vs])
    ax2.set_yticklabels([f"{v}" for v in vs], fontsize=7.6, color=INK2)
    ax2.set_ylabel("the ring potential it holds at 5 kV/mm (kV)", fontsize=8.0, color=INK2)
    for s in ("top",):
        ax2.spines[s].set_visible(False)
    ax2.spines["right"].set_color(AXIS)
    ax2.tick_params(colors=INK2)

    # (d) the retainer's permittivity
    axD = fig.add_subplot(gs[1, 1])
    ep = sorted(R["eps_sweep"], key=lambda q: q["eps_ret"])
    x = [q["eps_ret"] for q in ep]
    k0 = next(q["k_kV_cm_per_kV"] for q in ep if q["eps_ret"] == 3.2)
    axD.plot(x, [100 * (q["k_kV_cm_per_kV"] / k0 - 1) for q in ep], color=RAMP4[0], lw=1.8, marker="o", ms=4, mec=SURF,
             label="the field at the null (vs PEEK)")
    c0 = next(q["C_ring_ref_pF"] for q in ep if q["eps_ret"] == 3.2)
    axD.plot(x, [100 * (q["C_ring_ref_pF"] / c0 - 1) for q in ep], color=RAMP4[2], lw=1.8, marker="s", ms=4, mec=SURF,
             label="each ring's stray to REF (vs PEEK)")
    for e, nm, dx in ((2.1, "PTFE", 0.08), (3.15, "PEI", -0.3), (3.2, "PEEK", 0.08), (4.7, "G10", 0.08),
                      (6.0, "Macor", 0.08), (9.8, "alumina", -0.3)):
        axD.axvline(e, color=GRID, lw=0.9, zorder=0)
        axD.text(e + dx, 0.97, nm, rotation=90, fontsize=7.0, color=INK2, va="top", transform=axD.get_xaxis_transform())
    for q in (ep[0], ep[-1]):
        axD.annotate(f"{100 * (q['k_kV_cm_per_kV'] / k0 - 1):+.1f} %", (q["eps_ret"], 100 * (q["k_kV_cm_per_kV"] / k0 - 1)),
                     (0, 7), textcoords="offset points", fontsize=7.2, color=RAMP4[0], ha="center")
    style(axD, "(d) the retainer's permittivity: the field at the null barely moves; the\nrings' strays (on the pump) "
               "follow ε (0.5 mm gel pocket, G10 coupler)", "change from PEEK (%)", "the retainer's ε_r")
    axD.legend(fontsize=7.0, frameon=True, facecolor="white", edgecolor="none", framealpha=0.92, loc="center right")

    # (e) the best design of each pair of ratings, solved directly
    axT = fig.add_subplot(gs[1, 2]); axT.axis("off")
    axT.set_title("(e) the best design at each pair of ratings, solved directly", fontsize=9.6, loc="left", color=INK)
    xs = (0.0, 0.17, 0.39, 0.55, 0.69, 0.83)
    for x_, h_ in zip(xs, ("ratings\n(kV/mm)", "stages", "bands,\nbeads", "gel, polar /\neq. bead", "at the\nnull",
                           "rings A / B")):
        axT.text(x_, 0.97, h_, fontsize=7.6, color=INK, weight="bold", va="top", transform=axT.transAxes)
    y = 0.83
    for i, key in enumerate(PAIRS):
        b = R["best_edges"].get(key)
        if not b:
            continue
        e_t, e_g = key.split("/")
        stages = f"A {b['n_a']} + B {b['n_cw']}" if b["n_a"] else f"B {b['n_cw']}"
        row = (f"glass {e_t}\ngel {e_g}", stages,
               f"{b['theta_p']:.1f}–{b['theta_e']:.1f}°\nØ{2 * b['rho_pol_mm']:g} / Ø{2 * b['rho_eq_mm']:g} mm",
               f"{b['E_pol']['gel']:.1f} / {b['E_eq']['gel']:.1f}",
               f"{b['E_null_kV_cm']:.1f} kV/cm\n{b['p_null_Pa']:.1f} Pa",
               f"{kv(b['V_A_kV'])} /\n{kv(b['V_B_kV'], '+{:.1f}')} kV")
        for x_, c in zip(xs, row):
            axT.text(x_, y, c, fontsize=7.4, color=INK if i == 0 else INK2, weight="bold" if i == 0 else "normal",
                     va="top", transform=axT.transAxes, linespacing=1.25)
        y -= 0.135
    notes = [
        "The rings' separation is not the only limit: each ring's polar bead faces the AH coil's end (REF) across the "
        "PEEK seat, and holds 5 kV/mm in the gel only away from the pole; the equatorial bead's field grows with the DC even "
        "at a fixed field along the glass. Chains on both rings (A negative, B positive) share the DC, so neither ring "
        "carries most of it.",
        "Bold: the design ratings (1 kV/mm along the glass [RH]; 5 kV/mm in the gel at a bead [RH]). The others need the "
        "bench test's qualification (docs/bench-test-rings.md).",
    ]
    axT.text(0.0, y - 0.01, "\n".join(textwrap.fill(s_, 82) for s_ in notes), fontsize=7.1, color=INK2, va="top",
             transform=axT.transAxes, linespacing=1.35)
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    fig.savefig(OUT, dpi=130, facecolor="white")
    plt.close(fig)
    print(OUT)


if __name__ == "__main__":
    main()
