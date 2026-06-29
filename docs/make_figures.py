#!/usr/bin/env python3
"""
Draft figures for the Varcap Machine Design Guide.
One figure per (clusterable) formula, per docs/figure-brief.md.

Output: docs/figures/E*.png  (+ docs/figures/_contact_sheet.pdf)
Print-style line art; values taken from varcap-machine-design-guide.md.
These are FIRST DRAFTS for assessment, not final art.
"""
import os
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Wedge, Annulus, Rectangle, FancyArrowPatch, FancyBboxPatch, Circle
from matplotlib.lines import Line2D

OUT = os.path.join(os.path.dirname(__file__), "figures")
os.makedirs(OUT, exist_ok=True)

plt.rcParams.update({
    "figure.dpi": 160,
    "savefig.dpi": 160,
    "font.size": 10,
    "axes.titlesize": 11,
    "axes.titleweight": "bold",
    "axes.edgecolor": "#333333",
    "axes.linewidth": 0.9,
    "axes.grid": True,
    "grid.color": "#dddddd",
    "grid.linewidth": 0.6,
    "savefig.bbox": "tight",
    "savefig.facecolor": "white",
    "figure.facecolor": "white",
})

# consistent capacitor colours across figures
COL = {
    "Cmin": "#9e9e9e", "Crot": "#1f77b4", "Ca": "#2ca02c",
    "Cx": "#ff7f0e", "CR": "#9467bd", "Cblk": "#d62728",
}
INK = "#222222"
saved = []

def finish(fig, name, title=None):
    if title:
        fig.suptitle(title, fontsize=12, fontweight="bold")
    p = os.path.join(OUT, name)
    fig.savefig(p)
    plt.close(fig)
    saved.append((name, title or ""))
    print("wrote", name)

def disc_sectors(ax, n=12, kept_offset=0, r0=0.55, r1=1.0, color="#1f77b4",
                 alpha=0.6, theta_off=0.0, label=None):
    """Draw the kept (alternating) sectors of an n-sector disc."""
    w = 360.0 / n
    for i in range(n):
        if (i % 2) == kept_offset:
            ax.add_patch(Wedge((0, 0), r1, theta_off + i*w, theta_off + (i+1)*w,
                               width=r1-r0, facecolor=color, edgecolor="white",
                               linewidth=0.5, alpha=alpha))
    if label:
        ax.plot([], [], marker="s", linestyle="", color=color, alpha=alpha, label=label)

# ----------------------------------------------------------------------
# E1 — scale-free invariance
# ----------------------------------------------------------------------
def E1():
    fig, ax = plt.subplots(figsize=(7.2, 3.6))
    ax.axis("off")
    ax.set_xlim(0, 10); ax.set_ylim(0, 6)
    def ladder(cx, cy, s, lab):
        # crude cap-ladder glyph: 4 capacitor plates
        for k in range(4):
            x = cx - 1.2*s + 0.8*s*k
            ax.plot([x, x], [cy-0.5*s, cy+0.5*s], color=INK, lw=2)
            ax.plot([x+0.12*s, x+0.12*s], [cy-0.5*s, cy+0.5*s], color=INK, lw=2)
        ax.plot([cx-1.2*s, cx+1.2*s], [cy+0.5*s, cy+0.5*s], color=INK, lw=1)
        ax.plot([cx-1.2*s, cx+1.2*s], [cy-0.5*s, cy-0.5*s], color=INK, lw=1)
        ax.text(cx, cy+0.9*s, lab, ha="center", fontsize=10, fontweight="bold")
    ladder(2.2, 4.2, 1.0, "build at 1×")
    ladder(7.2, 4.0, 1.7, "build at 10×")
    ax.annotate("", xy=(5.3, 4.1), xytext=(3.7, 4.1),
                arrowprops=dict(arrowstyle="->", lw=1.5, color="#2ca02c"))
    ax.text(4.5, 4.5, r"$\times\lambda$ on ALL $C$", ha="center", color="#2ca02c", fontsize=9)
    ax.text(4.7, 1.9, r"$z = z\left(\kappa_C,\ C_a/C_{max},\ C_{par}/C_{min}\right) = 1.334$",
            ha="center", fontsize=12,
            bbox=dict(boxstyle="round", fc="#eef6ff", ec="#1f77b4"))
    ax.text(4.7, 0.8, "same z at any absolute size  —  scale ONE family alone "
                      r"$\Rightarrow$ z collapses ✗",
            ha="center", fontsize=9, color="#b00")
    finish(fig, "E01_scale_free.png", "E1 — Scale-free pump gain (Eq. 1)")

# ----------------------------------------------------------------------
# E2 — parallel-plate base law
# ----------------------------------------------------------------------
def E2():
    fig, ax = plt.subplots(figsize=(6.2, 4.0))
    ax.axis("off"); ax.set_xlim(0, 10); ax.set_ylim(0, 8)
    ax.add_patch(Rectangle((2, 5.6), 6, 0.35, facecolor="#444", edgecolor="k"))
    ax.add_patch(Rectangle((2, 2.1), 6, 0.35, facecolor="#444", edgecolor="k"))
    ax.fill_between([2, 8], 2.45, 5.6, color="#eef6ff")  # dielectric
    for x in np.linspace(2.6, 7.4, 9):
        ax.annotate("", xy=(x, 2.55), xytext=(x, 5.5),
                    arrowprops=dict(arrowstyle="->", color="#1f77b4", lw=1))
    for x in np.linspace(2.6, 7.4, 6):
        ax.text(x, 5.95, "+", ha="center", color="k", fontsize=11, fontweight="bold")
        ax.text(x, 1.75, "–", ha="center", color="k", fontsize=12, fontweight="bold")
    ax.annotate("", xy=(8.7, 5.6), xytext=(8.7, 2.45),
                arrowprops=dict(arrowstyle="<->", lw=1.3))
    ax.text(8.95, 4.0, r"$g$", fontsize=12)
    ax.text(5.0, 6.5, r"facing area $A_{ov}$", ha="center", fontsize=11)
    ax.text(5.0, 4.0, r"$\varepsilon_r$  (field $E$ uniform)", ha="center", fontsize=10, color="#1f77b4")
    ax.text(5.0, 0.7, r"$C = \varepsilon_0\,\varepsilon_r\,\dfrac{A_{ov}}{g}$",
            ha="center", fontsize=15,
            bbox=dict(boxstyle="round", fc="#fffbe6", ec="#caa"))
    ax.text(8.0, 6.2, "fringing\nneglected", fontsize=7, color="#888", style="italic")
    finish(fig, "E02_parallel_plate.png", "E2 — Parallel-plate base law (Eq. 2)")

# ----------------------------------------------------------------------
# E3 — overlap waveform + extremes + swing
# ----------------------------------------------------------------------
def E3():
    fig = plt.figure(figsize=(10.5, 3.6))
    # (a) three rotor states
    for j, (th, lab) in enumerate([(0, r"$\theta=0$ aligned"),
                                   (15, r"$\theta=\frac{1}{2} s_\theta$"),
                                   (30, r"$\theta=s_\theta$ over gaps")]):
        ax = fig.add_subplot(1, 4, j+1)
        ax.set_aspect("equal"); ax.axis("off")
        ax.set_xlim(-1.1, 1.1); ax.set_ylim(-1.1, 1.1)
        disc_sectors(ax, kept_offset=0, color="#1f77b4", alpha=0.55, theta_off=0)
        disc_sectors(ax, kept_offset=0, color="#ff7f0e", alpha=0.55, theta_off=th)
        ax.add_patch(Circle((0, 0), 0.5, facecolor="#9467bd", alpha=0.5, edgecolor="white"))
        ax.set_title(lab, fontsize=9)
    # (b) waveform
    ax = fig.add_subplot(1, 4, 4)
    th = np.linspace(0, 120, 600)
    s = 30.0
    fov = np.abs(1 - (th % (2*s))/s)
    ax.plot(th, fov, color="#1f77b4", lw=2)
    ax.set_xlabel(r"rotor angle $\theta$ (deg)"); ax.set_ylabel(r"$f_{ov}(\theta)$")
    ax.set_title(r"triangle, period $2s_\theta$", fontsize=9)
    ax.scatter([0, 60, 120], [1, 1, 1], color="#1f77b4", zorder=5)
    ax.scatter([30, 90], [0, 0], color="#ff7f0e", zorder=5)
    ax.annotate(r"$C_{max}$ (f=1)", (0, 1), textcoords="offset points", xytext=(6, -2), fontsize=8)
    ax.annotate(r"$C_{min}$ (ring only)", (30, 0), textcoords="offset points", xytext=(3, 8), fontsize=8)
    ax.set_ylim(-0.1, 1.25)
    fig.text(0.5, 0.005,
             r"$\kappa_C=C_{max}/C_{min}\approx 17.5$  (pure area ratio — $\varepsilon_0,\varepsilon_r,g$ cancel)",
             ha="center", fontsize=9)
    fig.suptitle("E3 — Sector overlap, the two extremes, swing ratio (Eqs. 3, 5, 6, 7)",
                 fontsize=12, fontweight="bold")
    fig.tight_layout(rect=[0, 0.04, 1, 0.94])
    fig.savefig(os.path.join(OUT, "E03_overlap_extremes.png")); plt.close(fig)
    saved.append(("E03_overlap_extremes.png", "E3"))
    print("wrote E03_overlap_extremes.png")

# ----------------------------------------------------------------------
# E4 — area decomposition
# ----------------------------------------------------------------------
def E4():
    fig, ax = plt.subplots(figsize=(5.2, 5.2))
    ax.set_aspect("equal"); ax.axis("off")
    ax.set_xlim(-1.15, 1.15); ax.set_ylim(-1.15, 1.15)
    disc_sectors(ax, kept_offset=0, color="#1f77b4", alpha=0.7, r0=0.55, r1=1.0,
                 label=r"$A_m$ modulated band")
    ax.add_patch(Annulus((0, 0), 0.5, 0.28, facecolor="#9467bd", alpha=0.6,
                         edgecolor="white"))
    ax.plot([], [], marker="s", linestyle="", color="#9467bd", alpha=0.6,
            label=r"$\chi A_{ring}$ constant floor")
    ax.annotate("sweeps with θ", xy=(0.75, 0.45), xytext=(1.0, 1.0),
                fontsize=8, arrowprops=dict(arrowstyle="->", color="#1f77b4"))
    ax.annotate("rotation-independent", xy=(0.0, 0.38), xytext=(-1.1, -1.0),
                fontsize=8, arrowprops=dict(arrowstyle="->", color="#9467bd"))
    ax.legend(loc="upper left", fontsize=8, frameon=True)
    ax.set_title(r"$A_{ov}(\theta)=A_m f_{ov}(\theta)+\chi A_{ring}$" + "\n(parallel areas add)",
                 fontsize=10)
    finish(fig, "E04_area_decomposition.png", "E4 — Area decomposition (Eq. 4)")

# ----------------------------------------------------------------------
# E8 — annulus sector / ring geometry
# ----------------------------------------------------------------------
def E8():
    fig, ax = plt.subplots(figsize=(5.4, 5.4))
    ax.set_aspect("equal"); ax.axis("off")
    ax.set_xlim(-1.2, 1.2); ax.set_ylim(-1.2, 1.2)
    w = 30
    for i in range(12):
        kept = (i % 2 == 0)
        ax.add_patch(Wedge((0, 0), 1.0, i*w, (i+1)*w, width=0.45,
                           facecolor="#1f77b4" if kept else "white",
                           edgecolor="#1f77b4", linewidth=0.8,
                           alpha=0.65 if kept else 1.0))
    ax.add_patch(Annulus((0, 0), 0.45, 0.18, facecolor="#9467bd", alpha=0.5, edgecolor="#9467bd"))
    # dimension arrows
    ax.annotate("", xy=(1.0, 0), xytext=(0, 0), arrowprops=dict(arrowstyle="->", lw=1.2))
    ax.text(0.7, -0.12, r"$r_{out}$", fontsize=11)
    ax.annotate("", xy=(0.55*np.cos(np.radians(75)), 0.55*np.sin(np.radians(75))),
                xytext=(0, 0), arrowprops=dict(arrowstyle="->", lw=1.0, color="#555"))
    ax.text(0.05, 0.4, r"$r_{in}$", fontsize=10, color="#555")
    ax.text(0, 1.12, r"$N_{sec}=12$, $n_{kept}=6$ (alternating)  $\Rightarrow A_m=\frac{1}{2}\pi(r_{out}^2-r_{in}^2)$",
            ha="center", fontsize=9)
    ax.text(0, -1.12, r"ring: $A_{ring}=\pi(r_{ring,out}^2-r_{ring,in}^2)$",
            ha="center", fontsize=9, color="#9467bd")
    finish(fig, "E08_annulus_geometry.png", "E8 — Sector & ring geometry (Eqs. 8, 9)")

# ----------------------------------------------------------------------
# E10 — insulate-first
# ----------------------------------------------------------------------
def E10():
    fig, (axg, axb) = plt.subplots(1, 2, figsize=(8.4, 4.0),
                                   gridspec_kw=dict(width_ratios=[1, 1.1]))
    axg.axis("off"); axg.set_xlim(0, 6); axg.set_ylim(0, 8)
    axg.add_patch(Rectangle((1, 5.4), 4, 0.3, facecolor="#444"))
    axg.add_patch(Rectangle((1, 2.3), 4, 0.3, facecolor="#444"))
    axg.annotate("", xy=(5.4, 5.4), xytext=(5.4, 2.6),
                 arrowprops=dict(arrowstyle="<->"))
    axg.text(5.6, 4.0, r"$g$", fontsize=13)
    axg.text(3, 6.4, "air gap", ha="center", fontsize=9)
    axg.text(3, 4.0, "spark / fire\ntransient", ha="center", fontsize=9, color="#b00")
    axg.set_title("gap = a breakdown decision", fontsize=10)
    # bar
    axb.bar(["V_work", "V_work·SF", "V_bd = E_bd·g"], [15, 30, 39.6],
            color=["#1f77b4", "#ff7f0e", "#2ca02c"])
    axb.set_ylabel("kV"); axb.grid(axis="y")
    axb.set_title(r"$g=\dfrac{V_{work}\,SF}{E_{bd}}$  (insulate first)", fontsize=11)
    axb.text(2, 36, "margin", ha="center", fontsize=8, color="#2ca02c")
    for i, v in enumerate([15, 30, 39.6]):
        axb.text(i, v+0.6, f"{v:g}", ha="center", fontsize=8)
    finish(fig, "E10_insulate_first.png", "E10 — Insulate-first gap (Eq. 10)")

# ----------------------------------------------------------------------
# E11 — inverse design flow
# ----------------------------------------------------------------------
def E11():
    fig, ax = plt.subplots(figsize=(11, 3.4))
    ax.axis("off"); ax.set_xlim(0, 22); ax.set_ylim(0, 6)
    def box(x, w, txt, fc):
        ax.add_patch(FancyBboxPatch((x, 2.2), w, 1.6, boxstyle="round,pad=0.1",
                                    fc=fc, ec="#333"))
        ax.text(x+w/2, 3.0, txt, ha="center", va="center", fontsize=8.5)
    def arrow(x0, x1, lab):
        ax.annotate("", xy=(x1, 3.0), xytext=(x0, 3.0),
                    arrowprops=dict(arrowstyle="->", lw=1.4))
        ax.text((x0+x1)/2, 3.5, lab, ha="center", fontsize=7.5, color="#1f77b4")
    box(0.3, 3.0, "Targets\n$C_{max},\\ \\kappa_C,\\ V_{work}$", "#eef6ff")
    box(4.2, 2.6, "gap $g$\n[Eq.10]", "#fff0e6")
    box(8.0, 3.0, "metal $A_m$\n[Eq.11]", "#eaffea")
    box(12.2, 2.8, "ring $A_{ring}$\n[Eq.12]", "#f3eaff")
    box(16.0, 2.8, "radius $r_{out}$\n[Eq.13]", "#ffeaea")
    box(19.8, 1.9, "Checks\n§4,§11", "#eeeeee")
    arrow(3.3, 4.2, ""); arrow(6.8, 8.0, r"$V,SF$"); arrow(11.0, 12.2, r"$C_{max}$")
    arrow(15.0, 16.0, r"$\kappa_C$"); arrow(18.8, 19.8, r"$A_m$")
    ax.annotate(r"free: $r_{in}$", xy=(17.4, 2.2), xytext=(17.0, 0.7),
                fontsize=8, arrowprops=dict(arrowstyle="->", color="#555"))
    ax.text(11, 5.4, "fixed order — insulate-first: gap before area; "
                     r"$\kappa_C$ touches only the ring", ha="center", fontsize=9)
    finish(fig, "E11_inverse_flow.png", "E11 — Inverse-design flow (Eqs. 11, 12, 13)")

# ----------------------------------------------------------------------
# E14 — moist-air permittivity
# ----------------------------------------------------------------------
def E14():
    def psat_buck(Tc):  # hPa
        return 6.1121*np.exp((18.678 - Tc/234.5)*(Tc/(257.14+Tc)))
    def eps_air(Tc, RH, P=1013.0):
        T = Tc + 273.15
        pv = (RH/100.0)*psat_buck(Tc)
        N = 77.6*P/T + 3.73e5*pv/T**2
        return 1 + 2*N*1e-6
    fig, ax = plt.subplots(figsize=(6.6, 4.2))
    RH = np.linspace(0, 100, 200)
    for Tc, c in [(0, "#1f77b4"), (20, "#ff7f0e"), (40, "#d62728")]:
        ax.plot(RH, eps_air(Tc, RH), color=c, lw=2, label=f"{Tc} °C")
    ax.axhline(1.0, color="#999", ls="--", lw=1)
    ax.text(2, 1.0000, "vacuum = 1 (exact)", fontsize=8, va="bottom", color="#666")
    ax.scatter([0], [eps_air(0, 0)], color="#1f77b4", zorder=5)
    ax.annotate(f"dry, 0 °C, 1013 hPa\n→ {eps_air(0,0):.6f}", (0, eps_air(0, 0)),
                textcoords="offset points", xytext=(20, 10), fontsize=8,
                arrowprops=dict(arrowstyle="->"))
    ax.set_xlabel("relative humidity (%)"); ax.set_ylabel(r"$\varepsilon_{r,air}$")
    ax.legend(title="temperature", fontsize=8)
    ax.set_title(r"$\varepsilon_{r,air}=1+2N\times10^{-6}$  (Smith–Weintraub + Buck) — "
                 "varies only at the 4th decimal", fontsize=9)
    ax.ticklabel_format(axis="y", useOffset=False)
    finish(fig, "E14_air_permittivity.png", "E14 — Moist-air permittivity (Eqs. 14, 15)")

# ----------------------------------------------------------------------
# E16 — two thickness regimes
# ----------------------------------------------------------------------
def E16():
    fig, ax = plt.subplots(figsize=(7.0, 4.4))
    C = np.linspace(50e-12, 1200e-12, 400)
    eps0 = 8.854e-12; epsr = 5.4; A = 0.05  # illustrative fixed plate, mica
    t_cap = eps0*epsr*A/C * 1e3  # mm
    t_bd = (20e3*2/ (118e6)) * 1e3 * np.ones_like(C)  # mica 118 kV/mm, 20kV SF2 -> mm
    Cp = C*1e12
    ax.plot(Cp, t_cap, color="#9467bd", lw=2, label=r"$t_{capacitance}=\varepsilon_0\varepsilon_r A/C$")
    ax.plot(Cp, t_bd, color="#d62728", lw=2, label=r"$t_{breakdown}=V\,SF/E_{diel}$")
    ax.plot(Cp, np.maximum(t_cap, t_bd), color="k", lw=3, alpha=0.35,
            label=r"$t=\max(\cdot)$ binds")
    ax.set_xlabel("capacitance target (pF)  [illustrative, fixed area]")
    ax.set_ylabel("dielectric thickness t (mm)")
    ax.set_ylim(0, t_cap.max()*0.6)
    ax.legend(fontsize=8)
    ax.text(0.30, 0.85, "capacitance-driven\n(thick septum, e.g. $C_R$)",
            transform=ax.transAxes, fontsize=8, color="#9467bd", ha="center")
    ax.text(0.80, 0.18, "breakdown-driven\n(e.g. air gaps $C_1/C_2$)",
            transform=ax.transAxes, fontsize=8, color="#d62728", ha="center")
    ax.set_title("Two independent floors — take the larger (Eq. 18)", fontsize=10)
    finish(fig, "E16_thickness_regimes.png", "E16 — Thickness regimes (Eqs. 16, 17, 18)")

# ----------------------------------------------------------------------
# E19 — tank C_R across septum, full vs active face
# ----------------------------------------------------------------------
def E19():
    fig, (axs, axp) = plt.subplots(1, 2, figsize=(9.2, 4.2))
    # cross-section
    axs.axis("off"); axs.set_xlim(0, 8); axs.set_ylim(0, 8)
    axs.add_patch(Rectangle((1, 4.4), 6, 1.6, facecolor="#bcd", edgecolor="k"))
    axs.add_patch(Rectangle((1, 2.0), 6, 1.6, facecolor="#bcd", edgecolor="k"))
    axs.add_patch(Rectangle((1, 3.6), 6, 0.8, facecolor="#9467bd", alpha=0.5, edgecolor="k"))
    axs.text(4, 5.2, "rotor face A", ha="center", fontsize=9)
    axs.text(4, 2.8, "rotor face B", ha="center", fontsize=9)
    axs.text(4, 4.0, "garolite septum  $t=12$ mm", ha="center", fontsize=8, color="#553")
    axs.annotate("", xy=(7.4, 4.4), xytext=(7.4, 3.6), arrowprops=dict(arrowstyle="<->"))
    axs.text(7.6, 4.0, r"$t_{septum}$", fontsize=9)
    axs.set_title(r"$C_R=\varepsilon_0\varepsilon_{r,garolite}A_{full}/t_{septum}=789$ pF", fontsize=9)
    # plan: full vs active band
    axp.set_aspect("equal"); axp.axis("off"); axp.set_xlim(-1.15, 1.15); axp.set_ylim(-1.15, 1.15)
    axp.add_patch(Wedge((0, 0), 1.0, 0, 180, facecolor="#9467bd", alpha=0.35, edgecolor="#9467bd"))
    axp.add_patch(Wedge((0, 0), 1.0, 0, 180, width=1.0-0.24, facecolor="none", edgecolor="none"))
    axp.add_patch(Wedge((0, 0), 1.0, 0, 180, width=1.0-0.55, facecolor="#1f77b4", alpha=0.5, edgecolor="#1f77b4"))
    axp.text(0, 0.55, "full face\n($C_R$, $f_0$)", ha="center", fontsize=8, color="#553")
    axp.text(0, 0.15, "active band\n(pump R95–R387)", ha="center", fontsize=7.5, color="#1f77b4")
    axp.set_title("full face ≠ squeezed pump band", fontsize=9)
    finish(fig, "E19_tank_septum.png", "E19 — Tank capacitor across the septum (Eq. 19)")

# ----------------------------------------------------------------------
# E20 — the two ladders
# ----------------------------------------------------------------------
def E20():
    fig, (axc, axa) = plt.subplots(1, 2, figsize=(10, 4.6))
    names = ["C_min", "C_rot", "Ca/Cb", "C_x", "C_R", "C_blk"]
    cols = [COL["Cmin"], COL["Crot"], COL["Ca"], COL["Cx"], COL["CR"], COL["Cblk"]]
    cappF = [16, 280, 309, 471, 789, 440000]
    area = [0.01, 0.221, 0.029, 0.165, 0.228, 1.81]
    y = np.arange(len(names))
    axc.barh(y, cappF, color=cols); axc.set_xscale("log")
    axc.set_yticks(y); axc.set_yticklabels(names); axc.invert_yaxis()
    axc.set_xlabel("capacitance (pF, log)"); axc.set_title("capacitance ladder", fontsize=10)
    for i, v in enumerate(cappF):
        axc.text(v*1.2, i, (f"{v/1000:.0f} nF" if v >= 1000 else f"{v} pF"), va="center", fontsize=7.5)
    axa.barh(y, area, color=cols)
    axa.set_yticks(y); axa.set_yticklabels(names); axa.invert_yaxis()
    axa.set_xlabel("steel electrode area (m²)"); axa.set_title("steel-area ladder", fontsize=10)
    for i, v in enumerate(area):
        axa.text(v+0.02, i, f"{v:g}", va="center", fontsize=7.5)
    axa.text(0.62, 0.40, "C_blk ×12 ≈ 22 m²\n(DC-block dominates\nthe steel budget)",
             transform=axa.transAxes, ha="center", fontsize=8.5, color=COL["Cblk"],
             bbox=dict(boxstyle="round", fc="white", ec=COL["Cblk"], alpha=0.9))
    fig.suptitle("E20 — Two ladders: capacitance vs steel area (Eqs. 20, 21)",
                 fontsize=12, fontweight="bold")
    fig.tight_layout(rect=[0, 0, 1, 0.94])
    fig.savefig(os.path.join(OUT, "E20_two_ladders.png")); plt.close(fig)
    saved.append(("E20_two_ladders.png", "E20")); print("wrote E20_two_ladders.png")

# ----------------------------------------------------------------------
# E22 — dielectric FOM
# ----------------------------------------------------------------------
def E22():
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(9, 4.2))
    diel = ["Mica", "Kapton", "PP film"]
    fom = [637, 802, 1100]; area = [3.12, 2.48, 1.81]
    cols = ["#9467bd", "#ff7f0e", "#2ca02c"]
    ax1.bar(diel, fom, color=cols); ax1.set_ylabel(r"FOM $=\varepsilon_r\,E_{bd}$")
    ax1.set_title("figure of merit (higher better)", fontsize=10)
    for i, v in enumerate(fom): ax1.text(i, v+15, str(v), ha="center", fontsize=8)
    ax2.bar(diel, area, color=cols); ax2.set_ylabel("plate area per cap (m²)")
    ax2.set_title("area @ 440 nF/20 kV (lower better)", fontsize=10)
    for i, v in enumerate(area): ax2.text(i, v+0.05, f"{v}", ha="center", fontsize=8)
    ax2.text(2, 1.81/2, "PP wins\ndespite\nlowest $\\varepsilon_r$", ha="center",
             fontsize=8, color="white", fontweight="bold")
    fig.suptitle("E22 — Dielectric FOM and resulting plate area (Eqs. 22, 23, 24)",
                 fontsize=12, fontweight="bold")
    fig.tight_layout(rect=[0, 0, 1, 0.93])
    fig.savefig(os.path.join(OUT, "E22_dielectric_fom.png")); plt.close(fig)
    saved.append(("E22_dielectric_fom.png", "E22")); print("wrote E22_dielectric_fom.png")

# ----------------------------------------------------------------------
# E25 — linear family scaling
# ----------------------------------------------------------------------
def E25():
    fig, ax = plt.subplots(figsize=(6.4, 4.2))
    Crot = np.linspace(0, 400, 100)
    ratios = {"Ca/Cb": (1.10, COL["Ca"]), "C_x": (1.68, COL["Cx"]),
              "C_R": (2.82, COL["CR"])}
    # area slope ∝ ratio * (g/epsr) normalised so C_rot maps to 0.221 m^2
    for lab, (r, c) in ratios.items():
        ax.plot(Crot, Crot/280*0.221*r*0.6, color=c, lw=2, label=lab)
    ax.plot(Crot, Crot/280*0.221, color=COL["Crot"], lw=2.5, label="C_rot (anchor)")
    ax.set_xlabel(r"anchor $C_{rot}$ (pF)"); ax.set_ylabel("steel area (a.u.)")
    ax.set_title(r"fixed $(g,\varepsilon_r)$: $A\propto C$ — pick any anchor, family follows",
                 fontsize=9)
    ax.legend(fontsize=8)
    finish(fig, "E25_family_scaling.png", "E25 — Linear family scaling (Eq. 25)")

# ----------------------------------------------------------------------
# E26 — boomerang plan + section
# ----------------------------------------------------------------------
def E26():
    fig, (axp, axs) = plt.subplots(1, 2, figsize=(9, 4.4))
    axp.set_aspect("equal"); axp.axis("off"); axp.set_xlim(-1.15, 1.15); axp.set_ylim(-0.2, 1.15)
    axp.add_patch(Wedge((0, 0), 1.0, 60, 88, width=0.57, facecolor="#d62728", alpha=0.5, edgecolor="#d62728"))
    axp.annotate("", xy=(np.cos(np.radians(74)), np.sin(np.radians(74))),
                 xytext=(0.43*np.cos(np.radians(74)), 0.43*np.sin(np.radians(74))),
                 arrowprops=dict(arrowstyle="<->", lw=1))
    axp.text(0.15, 0.85, r"$r_o$", fontsize=10); axp.text(0.1, 0.45, r"$r_i$", fontsize=10)
    axp.text(0.55, 1.02, r"arc $\varphi$", fontsize=9)
    axp.set_title(r"plan: one sector plate $A_{boom}=\frac{1}{2}\varphi(r_o^2-r_i^2)$", fontsize=8.5)
    # section: stack
    axs.set_xlim(0, 6); axs.set_ylim(0, 8); axs.axis("off")
    for k in range(14):
        axs.add_patch(Rectangle((1, 1+k*0.42), 3.6, 0.18, facecolor="#888"))
        axs.add_patch(Rectangle((1, 1+k*0.42+0.18), 3.6, 0.16, facecolor="#eef6ff"))
    axs.annotate("", xy=(5.0, 1), xytext=(5.0, 1+14*0.42), arrowprops=dict(arrowstyle="<->"))
    axs.text(5.15, 4, r"$H=N(t_{film}+t_{foil})$", fontsize=9)
    axs.text(2.8, 7.2, "foil / Mylar stack\n$N=A_{total}/A_{boom}$", ha="center", fontsize=8.5)
    axs.set_title("section: axial stack", fontsize=9)
    fig.suptitle("E26 — Boomerang block cap (Eqs. 26–29)  [annotate over real CAD]",
                 fontsize=11, fontweight="bold")
    fig.tight_layout(rect=[0, 0, 1, 0.93])
    fig.savefig(os.path.join(OUT, "E26_boomerang.png")); plt.close(fig)
    saved.append(("E26_boomerang.png", "E26")); print("wrote E26_boomerang.png")

# ----------------------------------------------------------------------
# E30 — LC tank: schematic + ring + response
# ----------------------------------------------------------------------
def E30():
    fig = plt.figure(figsize=(11, 3.6))
    L = 79e-6; C = 789e-12
    f0 = 1/(2*np.pi*np.sqrt(L*C)); Z0 = np.sqrt(L/C); Q = 500
    # schematic
    ax = fig.add_subplot(1, 3, 1); ax.axis("off"); ax.set_xlim(0, 10); ax.set_ylim(0, 8)
    t = np.linspace(0, 1, 200)
    ax.plot(1+1.5*t, 6+0.4*np.sin(2*np.pi*6*t), color=INK)  # coil L1
    ax.plot(6.5+1.5*t, 6+0.4*np.sin(2*np.pi*6*t), color=INK)  # coil L2
    ax.plot([5, 5], [3, 6.4], color=INK); ax.plot([5.5, 5.5], [3, 6.4], color=INK)  # C_R
    ax.text(5.25, 2.5, r"$C_R$", ha="center", color=COL["CR"])
    ax.text(1.7, 7, r"$L_R/2$", fontsize=8); ax.text(7.2, 7, r"$L_R/2$", fontsize=8)
    ax.text(5, 7.6, "split coil, k≈0.30", ha="center", fontsize=8)
    ax.set_title("tank schematic", fontsize=9)
    # ring waveform
    ax = fig.add_subplot(1, 3, 2)
    tt = np.linspace(0, 6/f0, 1000)
    env = np.exp(-tt*np.pi*f0/Q)
    V = np.cos(2*np.pi*f0*tt)*env
    I = -np.sin(2*np.pi*f0*tt)*env
    ax.plot(tt*1e6, V, color=COL["CR"], label=r"$V/\hat V$")
    ax.plot(tt*1e6, I, color="#1f77b4", label=r"$I/\hat I$")
    ax.set_xlabel("t (µs)"); ax.set_title(r"ring: $Z_0=\hat V/\hat I$", fontsize=9)
    ax.legend(fontsize=8)
    # response
    ax = fig.add_subplot(1, 3, 3)
    f = np.linspace(0.3*f0, 2*f0, 600)
    H = 1/np.sqrt(1+Q**2*(f/f0 - f0/f)**2)
    ax.plot(f/1e3, H, color="#2ca02c")
    ax.axvline(f0/1e3, color="#999", ls="--")
    ax.set_xlabel("f (kHz)"); ax.set_title(f"f₀≈{f0/1e3:.0f} kHz, Z₀≈{Z0:.0f} Ω", fontsize=9)
    fig.suptitle("E30 — LC tank: resonance & characteristic impedance (Eqs. 30, 31)",
                 fontsize=12, fontweight="bold")
    fig.tight_layout(rect=[0, 0, 1, 0.92])
    fig.savefig(os.path.join(OUT, "E30_lc_tank.png")); plt.close(fig)
    saved.append(("E30_lc_tank.png", "E30")); print("wrote E30_lc_tank.png")

# ----------------------------------------------------------------------
# E32 — energy triangle
# ----------------------------------------------------------------------
def E32():
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(9, 4.0))
    C = 789e-12; V = 15e3; Q = C*V
    q = np.linspace(0, Q, 100)
    ax1.plot(q*1e6, q/C/1e3, color=COL["CR"], lw=2)
    ax1.fill_between(q*1e6, q/C/1e3, color=COL["CR"], alpha=0.2)
    ax1.set_xlabel("charge q (µC)"); ax1.set_ylabel("voltage (kV)")
    ax1.text(Q*1e6*0.35, V/1e3*0.4, r"$\frac{1}{2} C_R V^2$" + "\n= 89 mJ",
             fontsize=11, color=COL["CR"])
    ax1.set_title("stored tank energy = triangle area", fontsize=10)
    # multi-fire
    fires = np.arange(1, 8)
    ax2.bar(fires, np.minimum(fires*14, 89), color=COL["Cx"])
    ax2.axhline(89, color="#b00", ls="--"); ax2.text(1, 91, "89 mJ target", fontsize=8, color="#b00")
    ax2.set_xlabel("island fire #"); ax2.set_ylabel("cumulative mJ")
    ax2.set_title("reached over ~6–7 fires (~14 mJ each)", fontsize=9)
    fig.suptitle("E32 — Reach: ½ C_R V² and the multi-fire build (Eq. 32)",
                 fontsize=12, fontweight="bold")
    fig.tight_layout(rect=[0, 0, 1, 0.93])
    fig.savefig(os.path.join(OUT, "E32_reach.png")); plt.close(fig)
    saved.append(("E32_reach.png", "E32")); print("wrote E32_reach.png")

# ----------------------------------------------------------------------
# E33 — island->tank transfer efficiency
# ----------------------------------------------------------------------
def E33():
    fig = plt.figure(figsize=(11, 3.6))
    Cx, CR, L, V0 = 471e-12, 789e-12, 79e-6, 15e3
    Cs = Cx*CR/(Cx+CR); w = 1/np.sqrt(L*Cs)
    qeq = V0*Cx*CR/(Cx+CR)
    # schematic
    ax = fig.add_subplot(1, 3, 1); ax.axis("off"); ax.set_xlim(0, 10); ax.set_ylim(0, 8)
    ax.plot([1, 1], [3, 6], color=INK, lw=2); ax.plot([1.5, 1.5], [3, 6], color=INK, lw=2)
    ax.text(1.25, 2.4, r"$C_x$ (charged)", ha="center", color=COL["Cx"], fontsize=8)
    tt = np.linspace(0, 1, 100); ax.plot(3+2*tt, 6+0.3*np.sin(2*np.pi*5*tt), color=INK)
    ax.text(4, 6.7, "L", fontsize=9)
    ax.plot([7, 7], [3, 6], color=INK, lw=2); ax.plot([7.5, 7.5], [3, 6], color=INK, lw=2)
    ax.text(7.25, 2.4, r"$C_R$ (empty)", ha="center", color=COL["CR"], fontsize=8)
    ax.text(5, 0.9, "spark-gap switch", ha="center", fontsize=8, color="#b00")
    ax.set_title("lossless LC swap", fontsize=9)
    # time domain
    ax = fig.add_subplot(1, 3, 2)
    th = np.linspace(0, np.pi, 400); t = th/w
    q = qeq*(1-np.cos(w*t))
    Vx = (V0 - q/Cx)/1e3; VR = (q/CR)/1e3
    ax.plot(t*1e6, Vx, color=COL["Cx"], label=r"$V_x$")
    ax.plot(t*1e6, VR, color=COL["CR"], label=r"$V_R$")
    ax.axvline(np.pi/w*1e6, color="#999", ls="--")
    ax.text(np.pi/w*1e6, 1, " peak transfer\n (I=0, q=2q_eq)", fontsize=7)
    ax.set_xlabel("t (µs)"); ax.set_ylabel("kV"); ax.legend(fontsize=8)
    ax.set_title("charge sloshes across", fontsize=9)
    # efficiency vs ratio
    ax = fig.add_subplot(1, 3, 3)
    r = np.linspace(0.05, 4, 400); eta = 4*r/(1+r)**2
    ax.plot(r, eta, color="#2ca02c", lw=2)
    rr = Cx/CR; ax.scatter([rr], [4*rr/(1+rr)**2], color="#b00", zorder=5)
    ax.annotate(f"471/789\n→ {4*rr/(1+rr)**2:.2f}", (rr, 4*rr/(1+rr)**2),
                textcoords="offset points", xytext=(10, -25), fontsize=8)
    ax.axvline(1, color="#999", ls=":"); ax.text(1.05, 0.2, "match\nη=1", fontsize=8)
    ax.set_xlabel(r"$C_x/C_R$"); ax.set_ylabel(r"$\eta_{M2}$")
    ax.set_title(r"$\eta_{M2}=\dfrac{4C_xC_R}{(C_x+C_R)^2}$", fontsize=10)
    fig.suptitle("E33 — Island→tank transfer efficiency (Eq. 33)",
                 fontsize=12, fontweight="bold")
    fig.tight_layout(rect=[0, 0, 1, 0.92])
    fig.savefig(os.path.join(OUT, "E33_transfer_efficiency.png")); plt.close(fig)
    saved.append(("E33_transfer_efficiency.png", "E33")); print("wrote E33_transfer_efficiency.png")

# ----------------------------------------------------------------------
# E34 — Paschen + air/vacuum regimes
# ----------------------------------------------------------------------
def E34():
    fig, (axp, axg) = plt.subplots(1, 2, figsize=(9.6, 4.2))
    # Paschen for air (Townsend); pd in kPa·mm (= Pa·m exactly).
    # A,B,gamma tuned so the minimum lands at the canonical air point
    # (~327 V @ ~0.76 kPa·mm), consistent with the guide's "~0.7 kPa·mm".
    A, B, gamma = 16.5, 430.0, 0.01
    pd_kpamm = np.logspace(-1.0, 2.0, 500)  # kPa·mm
    denom = np.log(A*pd_kpamm) - np.log(np.log(1+1/gamma))
    Vb = B*pd_kpamm/denom
    Vb[denom <= 0] = np.nan
    axp.plot(pd_kpamm, Vb, color="#1f77b4", lw=2)
    imin = np.nanargmin(Vb)
    axp.scatter([pd_kpamm[imin]], [Vb[imin]], color="#b00", zorder=5)
    axp.annotate(f"min ≈ {Vb[imin]:.0f} V\n@ {pd_kpamm[imin]:.2f} kPa·mm",
                 (pd_kpamm[imin], Vb[imin]), textcoords="offset points",
                 xytext=(10, 20), fontsize=8, arrowprops=dict(arrowstyle="->"))
    axp.set_xscale("log"); axp.set_xlabel("p·d (kPa·mm)"); axp.set_ylabel(r"$V_{bd}$ (V)")
    axp.set_ylim(0, 3000)
    axp.axvspan(pd_kpamm[imin], pd_kpamm[-1], color="#1f77b4", alpha=0.06)
    axp.text(5, 2600, "air: right branch\n(≈ linear in gap)", fontsize=8, color="#1f77b4")
    axp.axvspan(pd_kpamm[0], pd_kpamm[imin], color="#9467bd", alpha=0.06)
    axp.text(0.16, 2600, "below min:\nglow suppressed\n(vacuum cavity)", fontsize=7.5, color="#9467bd")
    axp.set_title("Paschen curve (air) — Eq. 36", fontsize=10)
    # V vs gap: air linear vs vacuum g^0.6
    g = np.linspace(1, 10, 100)
    axg.plot(g, 3.0*g, color="#1f77b4", lw=2, label=r"air $V_{bd}=E_{bd}g$ (3 kV/mm)")
    axg.plot(g, 60*g**0.6, color="#9467bd", lw=2, label=r"vacuum $V_{bd}=60\,g^{0.6}$")
    axg.set_xlabel("gap g (mm)"); axg.set_ylabel(r"$V_{bd}$ (kV)")
    axg.legend(fontsize=8); axg.set_title("air vs vacuum gap law (Eqs. 34, 35)", fontsize=10)
    fig.suptitle("E34 — Breakdown laws & operating regimes (Eqs. 34, 35, 36)",
                 fontsize=12, fontweight="bold")
    fig.tight_layout(rect=[0, 0, 1, 0.92])
    fig.savefig(os.path.join(OUT, "E34_paschen.png")); plt.close(fig)
    saved.append(("E34_paschen.png", "E34")); print("wrote E34_paschen.png")

# ----------------------------------------------------------------------
# E37 — recovery
# ----------------------------------------------------------------------
def E37():
    fig, ax = plt.subplots(figsize=(6.8, 4.2))
    t = np.linspace(0, 2000, 500)  # us
    for tau, c in [(10, "#2ca02c"), (100, "#ff7f0e"), (1000, "#d62728")]:
        ax.plot(t, 1-np.exp(-t/tau), color=c, lw=2, label=f"τ_rec = {tau} µs")
    ax.axvline(333, color="#333", ls="--")
    ax.text(345, 0.2, "333 µs window\n(3000 rpm)", fontsize=8)
    ax.axvspan(0, 333, color="#d62728", alpha=0.05)
    ax.set_xlabel("time since last strike (µs)"); ax.set_ylabel("hold-off recovered fraction")
    ax.legend(fontsize=8, loc="lower right")
    ax.set_title(r"$1-e^{-t/\tau_{rec}}$ — thermal recovery is the rate limit (Eq. 37)",
                 fontsize=10)
    finish(fig, "E37_recovery.png", "E37 — Hold-off recovery (Eq. 37)")

# ----------------------------------------------------------------------
# E38 — firing wheel + pulse train
# ----------------------------------------------------------------------
def E38():
    fig = plt.figure(figsize=(9, 4.0))
    ax = fig.add_subplot(1, 2, 1, projection="polar")
    w = np.radians(30)
    for i in range(12):
        if i % 2 == 0:
            ax.bar(i*w + w/2, 1.0, width=w*0.9, bottom=0.3, color="#1f77b4", alpha=0.6)
    ax.set_yticklabels([]); ax.set_xticklabels([])
    ax.set_title("6 kept sectors fire / rev", fontsize=9)
    ax2 = fig.add_subplot(1, 2, 2)
    T = 1000/300.0  # ms between pulses per branch
    for k in range(6):
        ax2.plot([k*T, k*T], [0, 1], color="#b00", lw=2)
    ax2.set_xlabel("time (ms)"); ax2.set_yticks([])
    ax2.set_title("PRF = 6 × 3000/60 = 300 Hz / branch", fontsize=9)
    fig.suptitle("E38 — Firing rate from sector geometry (Eq. 38)",
                 fontsize=12, fontweight="bold")
    fig.tight_layout(rect=[0, 0, 1, 0.92])
    fig.savefig(os.path.join(OUT, "E38_firing_prf.png")); plt.close(fig)
    saved.append(("E38_firing_prf.png", "E38")); print("wrote E38_firing_prf.png")

# ----------------------------------------------------------------------
# E39 — rim speed
# ----------------------------------------------------------------------
def E39():
    fig, ax = plt.subplots(figsize=(6.6, 4.2))
    rpm = np.linspace(0, 4500, 200); r = 0.49
    v = 2*np.pi*r*rpm/60
    ax.plot(rpm, v, color="#1f77b4", lw=2)
    ax.axhline(200, color="#b00", ls="--"); ax.text(100, 203, "hard 200 m/s", fontsize=8, color="#b00")
    ax.axhline(150, color="#e69500", ls="--"); ax.text(100, 153, "soft 150 m/s", fontsize=8, color="#e69500")
    vp = 2*np.pi*r*3000/60
    ax.scatter([3000], [vp], color="#2ca02c", zorder=5)
    ax.annotate(f"3000 rpm → {vp:.0f} m/s", (3000, vp), textcoords="offset points",
                xytext=(-120, 10), fontsize=9, arrowprops=dict(arrowstyle="->"))
    ax.set_xlabel("rpm"); ax.set_ylabel("rim speed v (m/s)")
    ax.set_title(r"$v=2\pi r_{out}\,$rpm$/60$  ($r_{out}=0.49$ m) — Eq. 39", fontsize=10)
    finish(fig, "E39_rim_speed.png", "E39 — Rim speed envelope (Eq. 39)")

# ----------------------------------------------------------------------
ALL = [E1, E2, E3, E4, E8, E10, E11, E14, E16, E19, E20, E22, E25, E26,
       E30, E32, E33, E34, E37, E38, E39]
for fn in ALL:
    try:
        fn()
    except Exception as e:
        print("FAILED", fn.__name__, "->", repr(e))

# contact sheet
from matplotlib.backends.backend_pdf import PdfPages
import matplotlib.image as mpimg
pngs = sorted(f for f in os.listdir(OUT) if f.endswith(".png"))
with PdfPages(os.path.join(OUT, "_contact_sheet.pdf")) as pdf:
    for f in pngs:
        img = mpimg.imread(os.path.join(OUT, f))
        h, w = img.shape[:2]
        fig = plt.figure(figsize=(8.27, 8.27*h/w*0.96))
        ax = fig.add_axes([0, 0, 1, 0.95]); ax.imshow(img); ax.axis("off")
        fig.text(0.5, 0.975, f, ha="center", fontsize=9, fontweight="bold")
        pdf.savefig(fig); plt.close(fig)
print("\nTOTAL:", len(pngs), "figures + contact sheet")
