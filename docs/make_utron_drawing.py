"""docs/make_utron_drawing.py -- writes docs/figures/utron-core-detail.png: the wound utron of the chosen operating point
as a dimensioned detail drawing. Front view (the lamination profile in the plane of rotation, the aligned bridge above),
two side sections (v = 0 through the coil, v = tip centre through a half-core), the 2-D field of the solved section and
the data table. Every dimension comes from sim/utron_profile.spec (the same numbers that build the solids in
sim/tube_geometry.py --rel wound).
Usage: python3 docs/make_utron_drawing.py ["g 0.5 / 6 bridges / 1200 rpm"]
"""
import json
import math
import os
import sys

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt                           # noqa: E402
from matplotlib.patches import Polygon, Rectangle, Circle  # noqa: E402
import numpy as np                                        # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
SIM = os.path.join(HERE, "..", "sim")
sys.path.insert(0, SIM)
sys.path.insert(0, HERE)
import utron_profile as U                                 # noqa: E402
import pole_fd2d as P                                     # noqa: E402

INK, INK2, DIM = "#1d1d1f", "#52514e", "#3a4a66"
SIFE, NIFE, CU, G10, AIR = "#7d828f", "#2f9a9a", "#d58a4e", "#b9c2ab", "#ffffff"
EDGE = dict(ec=INK, lw=0.6)


def dim(ax, a, b, text, off=(0.0, 0.0), fs=7.2, tx=(0.0, 0.0), rot=0, ext=True, ha="center"):
    """a dimension between points a and b, drawn offset by off (data units), text at the middle + tx."""
    (x0, y0), (x1, y1) = a, b
    A, B = (x0 + off[0], y0 + off[1]), (x1 + off[0], y1 + off[1])
    if ext and (off[0] or off[1]):
        for p, q in ((a, A), (b, B)):
            ax.plot([p[0], q[0] + 0.6 * np.sign(off[0])], [p[1], q[1] + 0.6 * np.sign(off[1])], color=DIM, lw=0.35)
    ax.annotate("", A, B, arrowprops=dict(arrowstyle="<|-|>", lw=0.5, color=DIM, mutation_scale=5, shrinkA=0, shrinkB=0))
    ax.text(0.5 * (A[0] + B[0]) + tx[0], 0.5 * (A[1] + B[1]) + tx[1], text, fontsize=fs, color=DIM, ha=ha, va="center",
            rotation=rot, bbox=dict(fc="white", ec="none", pad=0.25, alpha=0.9))


def note(ax, xy, xytext, text, fs=7.2, ha="left"):
    ax.annotate(text, xy, xytext, fontsize=fs, color=INK2, ha=ha, va="center",
                arrowprops=dict(arrowstyle="-", lw=0.45, color=INK2, shrinkA=1, shrinkB=0))


def poly(ax, pts, fc, z=2, **kw):
    ax.add_patch(Polygon(pts, closed=True, fc=fc, zorder=z, **(kw or EDGE)))


def rect(ax, x0, x1, y0, y1, fc, z=2, **kw):
    ax.add_patch(Rectangle((x0, y0), x1 - x0, y1 - y0, fc=fc, zorder=z, **(kw or EDGE)))


def sector_pts(r0, r1, a0, a1, n=40):
    """(v, u) outline of an annular sector, angles in degrees from the utron's centre line."""
    a = np.radians(np.linspace(a0, a1, n))
    outer = [(r1 * math.sin(t), r1 * math.cos(t)) for t in a]
    inner = [(r0 * math.sin(t), r0 * math.cos(t)) for t in a[::-1]]
    return outer + inner


def column(ax, items, x, ha, y_lo, y_hi, fs=7.4):
    """leader labels in a column at x, evenly spaced between y_lo and y_hi in the order of their targets' y."""
    items = sorted(items, key=lambda q: -q[0][1])
    ys = np.linspace(y_hi, y_lo, len(items)) if len(items) > 1 else [0.5 * (y_lo + y_hi)]
    for (xy, text), y in zip(items, ys):
        note(ax, xy, (x, y), text, fs=fs, ha=ha)


def front(ax, sp):
    """the plane of rotation: x = v (tangential), y = u (radius)."""
    r_g, s2, wp, W2 = sp["r_g"], sp["s"] / 2, sp["w_p"], sp["W_u"] / 2
    hb = sp["br_deg"] / 2
    ring_a = hb + 9.0
    # counter-rotor: the bridge ring (G10) and the aligned bridge (SiFe), 1 mm proud of the ring's bore
    poly(ax, sector_pts(sp["r_ring0"], sp["r_ring1"], -ring_a, ring_a), G10, z=1)
    poly(ax, sector_pts(sp["r_br0"], sp["r_br1"], -hb, hb), SIFE, z=2)
    # rotor: cheeks behind (dashed), carrier disc rim, the core
    for v0, v1 in ((s2, s2 + wp), (-s2 - wp, -s2)):
        ax.add_patch(Rectangle((v0, sp["u_ch0"]), v1 - v0, sp["u_ch1"] - sp["u_ch0"], fill=False, ls=(0, (4, 2)), lw=0.6,
                               ec=INK2, zorder=1))
    t = np.radians(np.linspace(-26, 26, 60))
    ax.plot(sp["r_disc"] * np.sin(t), sp["r_disc"] * np.cos(t), color=INK2, lw=0.6, ls=(0, (4, 2)), zorder=1)
    for sd in (+1, -1):
        poly(ax, [(v, u) for u, v in U.half_core(sp, sd)], SIFE)
        for (u, v) in sp["studs"]:
            ax.add_patch(Circle((sd * v, u), sp["stud_d"] / 2, fc=AIR, ec=INK, lw=0.5, zorder=3))
    R = U.rects(sp)
    for key, fc in (("strip", NIFE), ("spacer", G10)):
        u0, u1, v0, v1 = R[key]
        rect(ax, v0, v1, u0, u1, fc, z=3)
    poly(ax, [(v, u) for u, v in U.wedge(sp)], G10, z=3)
    for key, mark in (("coil_plus", "×"), ("coil_minus", "•")):
        u0, u1, v0, v1 = R[key]
        rect(ax, v0, v1, u0, u1, CU, z=3)
        ax.text(-0.5 * sp["cv"], 0.5 * (u0 + u1), mark, ha="center", va="center", fontsize=12, color=INK, zorder=4)
    t = np.radians(np.linspace(-hb - 6, hb + 6, 80))
    ax.plot(r_g * np.sin(t), r_g * np.cos(t), color=INK2, lw=0.4, ls=":", zorder=4)
    # chain dimension over the tips and the slot, the bridge above it
    yc = sp["r_ring1"] + 7
    for v in (-s2 - wp, -s2, s2, s2 + wp):
        ax.plot([v, v], [math.sqrt(r_g ** 2 - v ** 2) + 0.4, yc + 1.5], color=DIM, lw=0.3, ls=(0, (2, 2)), zorder=5)
    dim(ax, (-s2 - wp, yc), (-s2, yc), f"{wp:.0f}", ext=False)
    dim(ax, (-s2, yc), (s2, yc), f"slot s {sp['s']:.0f}", ext=False)
    dim(ax, (s2, yc), (s2 + wp, yc), f"tip w_p {wp:.0f}", ext=False, tx=(0, 0))
    a = math.radians(hb)
    dim(ax, (-sp["r_br0"] * math.sin(a), yc + 9), (sp["r_br0"] * math.sin(a), yc + 9), f"bridge l_b {sp['l_b']:.0f} (arc at its face)",
        ext=False)
    for sd in (-1, 1):
        ax.plot([sd * sp["r_br0"] * math.sin(a)] * 2, [sp["r_br0"] * math.cos(a), yc + 10.5], color=DIM, lw=0.3, ls=(0, (2, 2)), zorder=5)
    # the core's own dimensions
    dim(ax, (6.0, sp["u_y1"]), (6.0, r_g), f"d {sp['d']:.0f}", rot=90, ext=False, tx=(0, 0))
    dim(ax, (W2, sp["u_y0"]), (W2, sp["u_y1"]), f"b {sp['b']:.0f}", off=(5.0, 0), rot=90, tx=(2.6, 0))
    dim(ax, (-W2, sp["u_y0"]), (-W2, sp["u_n1"]), f"{sp['t_n']:.2f}", off=(-5.0, 0), rot=90, tx=(-2.4, 0), fs=6.8)
    dim(ax, (-sp["cv"], sp["u_m0"]), (-sp["cv"], sp["u_m1"]), f"h_c {sp['h_c']:.0f}", off=(-2.6, 0), rot=90, tx=(-2.3, 0), ext=False)
    dim(ax, (-sp["cv"], sp["u_m0"]), (sp["cv"], sp["u_m0"]), f"coil {2 * sp['cv']:.0f}", off=(0, -4.0))
    dim(ax, (-W2, sp["u_y0"]), (W2, sp["u_y0"]), f"W_u {sp['W_u']:.0f}", off=(0, sp["u_m0"] - sp["u_y0"] - 12))
    xd = -W2 - 26
    dim(ax, (xd, sp["u_m0"] - sp["clr"]), (xd, r_g), f"utron r {r_g - sp['depth']:.0f} .. {r_g:.0f} (depth {sp['depth']:.0f})",
        rot=90, ext=False, tx=(-2.6, 0))
    for y in (sp["u_m0"] - sp["clr"], r_g):
        ax.plot([xd - 1.5, -2.0 if y < r_g else -s2 - wp], [y, y], color=DIM, lw=0.3, ls=(0, (2, 2)), zorder=5)
    left = [((-s2 - 0.5 * wp, 0.5 * (r_g + sp["r_br0"])), f"gap {sp['g']:g} (r {r_g:g} | {sp['r_br0']:g})"),
            ((-s2 - 0.6 * wp, sp["u_y1"] + 8), "half-core, M235-35A"),
            ((-sp["cv"] + 4, 0.5 * (sp["u_p0"] + sp["u_p1"])), "coil, slot side (×)"),
            ((-3.0, 0.5 * (sp["u_n1"] + sp["u_y1"])), f"air break {sp['brk']:.0f}, G10 spacer"),
            ((-W2 + 6, 0.5 * (sp["u_y0"] + sp["u_n1"])), f"neck strip, 80 % NiFe {sp['t_n']:.2f}"),
            ((-sp["cv"] + 6, 0.5 * (sp["u_m0"] + sp["u_m1"])), "coil, return side (•)")]
    column(ax, left, -W2 - 34, "right", sp["u_m0"] + 2, r_g + 10)
    right = [((W2 * 0.6, sp["r_ring1"] - 2.5), f"bridge ring, G10, r {sp['r_ring0']:g}..{sp['r_ring1']:g}"),
             ((W2 * 0.45, sp["r_br0"] + 7), f"bridge, SiFe, t_b {sp['t_b']:.0f} (r {sp['r_br0']:g}..{sp['r_br1']:g})"),
             ((0.6 * s2, 0.5 * (sp["u_w0"] + r_g - 0.2)), f"slot cover, G10, bonded (no grooves; {sp['t_wedge']:.2f} at the tips)"),
             ((sp["studs"][1][1], sp["studs"][1][0]), f"A4 M6 studs, Ø{sp['stud_d']:.1f} holes, 2 per half-core"),
             ((s2 + wp - 1.5, sp["u_ch0"] + 6), "cheek, G10 (behind; one per tip and stack end)"),
             ((sp["r_disc"] * math.sin(math.radians(20)), sp["r_disc"] * math.cos(math.radians(20))),
              f"carrier disc rim, r {sp['r_disc']:.0f} (behind)")]
    column(ax, right, W2 + 16, "left", sp["u_m0"] - 6, r_g + 22)
    ax.set_xlim(-W2 - 100, W2 + 118)
    ax.set_ylim(sp["u_m0"] - 24, yc + 16)
    ax.set_aspect("equal"); ax.set_anchor("N")
    ax.set_title("A. front view, the plane of rotation (the stack runs into the page); the aligned bridge above",
                 fontsize=10, loc="left", color=INK)
    ax.set_xlabel("v, tangential (mm)", fontsize=8, color=INK2); ax.set_ylabel("u = radius (mm)", fontsize=8, color=INK2)


def side_coil(ax, sp):
    """side section at v = 0: x = w (axial), y = u: the coil with its end turns, the window, the aligned bridge."""
    L, o = sp["L"], sp["over"]
    cr = U.coil_ring(sp)
    (u0, u1, w0, w1, Ro), (i0, i1, j0, j1, Ri) = cr["outer"], cr["inner"]
    rect(ax, -o - sp["sp"], L + o + sp["sp"], sp["r_ring0"], sp["r_ring1"], G10, z=1)
    rect(ax, 0, L, sp["r_br0"], sp["r_br1"], SIFE, z=2)
    for e0, e1 in ((-sp["t_cheek"] - sp["t_disc"], -sp["t_cheek"]), (L + sp["t_cheek"], L + sp["t_cheek"] + sp["t_disc"])):
        rect(ax, e0, e1, U.SLEEVE_R, sp["r_disc"], G10, z=1)
    poly(ax, [(w, u) for u, w in U.rounded_rect(u0, u1, w0, w1, Ro)], CU)
    poly(ax, [(w, u) for u, w in U.rounded_rect(i0, i1, j0, j1, Ri)], AIR, z=3)
    R = U.rects(sp)
    rect(ax, 0, L, R["strip"][0], R["strip"][1], NIFE, z=4)
    rect(ax, 0, L, R["spacer"][0], R["spacer"][1], G10, z=4)
    rect(ax, 0, L, sp["u_w0"], sp["r_g"] - 0.2, G10, z=4)
    yt = sp["r_ring1"] + 6
    for w in (0, L):
        ax.plot([w, w], [sp["r_br1"], yt + 1.5], color=DIM, lw=0.3, ls=(0, (2, 2)))
    for w in (-o, L + o):
        ax.plot([w, w], [sp["r_g"] - 30, yt + 9.5], color=DIM, lw=0.3, ls=(0, (2, 2)))
    dim(ax, (0, yt), (L, yt), f"stack L {L:.0f}", ext=False)
    dim(ax, (-o, yt + 8), (L + o, yt + 8), f"over the end turns {L + 2 * o:.0f}", ext=False)
    dim(ax, (-o, u1 - Ro), (0, u1 - Ro), f"{o:.0f}", off=(0, 0), ext=False, tx=(0, 2.4), fs=6.8)
    dim(ax, (L + 2, i1), (L + 2, u1), f"{sp['h_c']:.0f}", off=(0, 0), ext=False, rot=90, tx=(2.6, 0), fs=6.8)
    note(ax, (L + o - 0.29 * Ro, u1 - 0.29 * Ro), (L + o + 12, u1 + 12), f"end turns R {Ro:.0f} / R {Ri:.0f}")
    note(ax, (-sp["t_cheek"] - 0.5 * sp["t_disc"], sp["r_disc"] - 6), (-o - 34, sp["r_disc"] + 8),
         f"carrier discs, G10 {sp['t_disc']:.0f} mm")
    note(ax, (50, 0.5 * (sp["u_y0"] + sp["u_n1"])), (-o - 34, sp["u_y0"] - 2), "neck strip (NiFe)")
    note(ax, (50, 0.5 * (sp["u_n1"] + sp["u_y1"])), (-o - 34, sp["u_y1"] + 4), "air-break spacer (G10)")
    note(ax, (70, sp["r_ring1"] - 4), (L + o + 12, sp["r_ring1"] + 2), "bridge ring (counter-rotor)")
    note(ax, (80, 0.5 * (sp["r_br0"] + sp["r_br1"])), (L + o + 12, sp["r_br0"] + 1), "bridge (SiFe)")
    note(ax, (30, sp["r_g"] - 0.6), (-o - 34, sp["r_g"] + 2), "slot cover")
    ax.set_xlim(-o - 38, L + o + 62)
    ax.set_ylim(U.SLEEVE_R - 6, sp["r_ring1"] + 20)
    ax.set_aspect("equal"); ax.set_anchor("N")
    ax.set_title("B. side section at v = 0 (the coil's centre): the window holds the neck strip and the break",
                 fontsize=9.5, loc="left", color=INK)
    ax.set_xlabel("w, axial (mm)", fontsize=8, color=INK2); ax.set_ylabel("u (mm)", fontsize=8, color=INK2)


def side_tip(ax, sp):
    """side section through a tip centre (v = s/2 + w_p/2): the half-core, the strip, cheeks, studs, discs."""
    L, vt = sp["L"], sp["s"] / 2 + sp["w_p"] / 2
    r_g = sp["r_g"]
    u_top = math.sqrt(r_g ** 2 - vt ** 2)
    rect(ax, 0, L, sp["u_n1"], u_top, SIFE)
    rect(ax, 0, L, sp["u_y0"], sp["u_n1"], NIFE)
    for e0, e1 in ((-sp["t_cheek"], 0.0), (L, L + sp["t_cheek"])):
        rect(ax, e0, e1, sp["u_ch0"], sp["u_ch1"], G10)
    for e0, e1 in ((-sp["t_cheek"] - sp["t_disc"], -sp["t_cheek"]), (L + sp["t_cheek"], L + sp["t_cheek"] + sp["t_disc"])):
        rect(ax, e0, e1, U.SLEEVE_R, sp["r_disc"], G10)
    ub0, ub1 = math.sqrt(sp["r_br0"] ** 2 - vt ** 2), math.sqrt(sp["r_br1"] ** 2 - vt ** 2)
    rect(ax, 0, L, ub0, ub1, SIFE)
    for (u, v) in sp["studs"]:
        rect(ax, -sp["t_cheek"] - 6, L + sp["t_cheek"] + 6, u - 0.5 * sp["stud_d"], u + 0.5 * sp["stud_d"], "#c9ccd2", z=5,
             ec=INK, lw=0.5)
        for e in (-sp["t_cheek"] - 6, L + sp["t_cheek"]):
            rect(ax, e, e + 6, u - 5, u + 5, "#9ea3ad", z=6, ec=INK, lw=0.5)
    dim(ax, (-sp["t_cheek"], sp["u_ch1"]), (0, sp["u_ch1"]), f"{sp['t_cheek']:.0f}", off=(0, 5), fs=6.8)
    dim(ax, (-sp["t_cheek"] - sp["t_disc"], U.SLEEVE_R), (-sp["t_cheek"], U.SLEEVE_R), f"{sp['t_disc']:.0f}", off=(0, -5), fs=6.8)
    dim(ax, (L + 2, sp["u_ch0"]), (L + 2, sp["r_disc"]), f"lap {sp['r_disc'] - sp['u_ch0']:.0f}", off=(18, 0), rot=90,
        tx=(2.4, 0), fs=6.8)
    note(ax, (50, 0.5 * (sp["u_n1"] + u_top)), (L + 36, u_top - 6), "half-core, M235-35A\n(tip + half back iron)")
    note(ax, (50, 0.5 * (ub0 + ub1)), (L + 36, ub1 + 6), "bridge (counter-rotor)")
    note(ax, (L + 5, sp["u_ch0"] + 8), (L + 36, sp["u_ch0"] + 2), "cheek, G10: bolted to\nthe carrier disc")
    note(ax, (L + sp["t_cheek"] + 3, sp["studs"][0][0]), (L + 36, sp["studs"][0][0] + 2), "A4 M6 stud + nut")
    note(ax, (50, 0.5 * (sp["u_y0"] + sp["u_n1"])), (L + 36, sp["u_y0"] - 12), "neck strip under the half-core")
    ax.set_xlim(-sp["t_cheek"] - sp["t_disc"] - 10, L + 92)
    ax.set_ylim(U.SLEEVE_R - 6, sp["r_br1"] + 10)
    ax.set_aspect("equal"); ax.set_anchor("N")
    ax.set_title(f"C. side section through a tip (v = {vt:g}): core, cheeks, studs, carrier", fontsize=9.5, loc="left",
                 color=INK)
    ax.set_xlabel("w, axial (mm)", fontsize=8, color=INK2); ax.set_ylabel("u (mm)", fontsize=8, color=INK2)


def flux(ax, design):
    """the solved 2-D section (sim/pole_fd2d.py: linear SiFe, no neck), aligned, centred on the utron."""
    D = P.Design(**design)
    s = P.solve(D, 0.0, return_field=True)
    x, y, A, X = s["x"], s["y"], s["A"], D.X
    xs = (x + X / 2) % X - X / 2
    order = np.argsort(xs)
    xs, A = xs[order], A[order, :]

    def shift(r):
        out = []
        for sh in (-X, 0.0, X):
            a, b = max(r[0] + sh, -X / 2), min(r[1] + sh, X / 2)
            if b > a:
                out.append((a, b, r[2], r[3]))
        return out
    sel = (y > -D.radial_depth() - 6) & (y < D.g + D.t_b + 8)
    for r in [p for q in D.stator_rects() for p in shift(q)]:
        ax.add_patch(Rectangle((r[0], r[2]), r[1] - r[0], r[3] - r[2], fc=SIFE, ec="none", alpha=0.45))
    for r in [p for q in D.utron_rects(0.0) for p in shift(q)]:
        ax.add_patch(Rectangle((r[0], r[2]), r[1] - r[0], r[3] - r[2], fc=SIFE, ec="none", alpha=0.85))
    plus, minus, _ = D.coil_rects()
    for (a, b, c0, c1) in (plus, minus):
        ax.add_patch(Rectangle((a, c0), b - a, c1 - c0, fc=CU, ec="none", alpha=0.6))
    ax.contour(xs, y[sel], A[:, sel].T, levels=np.linspace(A.min(), A.max(), 22)[1:-1], colors="#1f5fa8", linewidths=0.6)
    ax.set_xlim(-75, 75); ax.set_ylim(y[sel].min(), y[sel].max()); ax.set_aspect("equal"); ax.set_anchor("N")
    ax.set_title("D. the solved 2-D section, aligned: flux lines (unrolled at r_g;\nlinear iron, the neck is not in this model)",
                 fontsize=9.5, loc="left", color=INK)
    ax.set_xlabel("tangential (mm)", fontsize=8, color=INK2); ax.set_ylabel("radial from the gap face (mm)", fontsize=8, color=INK2)


def table(ax, sp, op, pick):
    b = op["best"]
    f_u = op["best"]["f_utron_Hz"]
    rows = [
        ("operating point", pick),
        ("section (2-D model)", f"r_g {sp['r_g']:g}, tips {sp['w_p']:g}, slot {sp['s']:g} x {sp['d']:g}, back iron {sp['b']:g}, gap {sp['g']:g}"),
        ("stack", f"{sp['L']:g} mm of M235-35A (0.35 mm); over the end turns {sp['axial_mm']:g} mm"),
        ("winding", f"{sp['N_u']} turns, {sp['wire_mm2']:.2f} mm² (Ø{sp['wire_d_mm']:.2f} bare), fill {U.FILL:.0%}, mean turn {sp['l_turn_mm']:.0f} mm"),
        ("per coil", f"R {sp['R_coil_ohm']:.3f} Ω, L {1e3 * sp['L_al_coil_H']:.1f} / {1e3 * sp['L_un_coil_H']:.1f} mH (aligned / unaligned)"),
        ("ratio, time constant", f"κ {sp['kappa']:.1f}, τ = L/R {sp['tau_s']:.3f} s; f {f_u:.0f} Hz, f·τ {f_u * sp['tau_s']:.1f}"),
        ("group (3 in series)", f"L {b['L_group_H']:.3f} H, I {b['I_pk']:.2f} A pk / {b['I_rms']:.2f} A rms, V {b['V_pk']:.0f} V pk"),
        ("saturation", f"Ψs {b['psi_s']:.4f} Wb-t (group) = {1e3 * sp['phi_s_Wb']:.3f} mWb per utron"),
        ("neck", f"NiFe {sp['t_n']:.1f} x {sp['L']:g} mm ({sp['n_nife']} x {U.NIFE_LAM:g}) at {U.B_NIFE:g} T: Φs "
                 f"{100 * (sp['phi_s_built_Wb'] / sp['phi_s_Wb'] - 1):+.1f} % (op: {sp['neck_sife_mm']:.2f} mm SiFe at 1.5 T); body {b['B_body_T']:.2f} T"),
        ("losses", f"Cu {b['P_utron_coil_W']:.2f} W per coil; machine {b['P_total_W']:.1f} W (iron {2 * b['P_fe_side_W']:.2f} W)"),
        ("coil temperature", f"{b['T_coil_air_C']:.0f} °C in air (forced), {b['T_coil_vac_C']:.0f} °C in vacuum (radiation)"),
        ("start", f"kick ≥ {100 * b['kick_frac']:.0f} % of I_pk ({b['kick_mJ']:.0f} mJ) with Si diodes"),
        ("mass per utron", f"{sp['m_utron_kg']:.2f} kg: SiFe {sp['m_sife_kg']:.2f}, NiFe {sp['m_nife_kg']:.2f}, Cu {sp['m_cu_kg']:.2f}, G10 {sp['m_g10_kg']:.2f}"),
        ("counter-rotor, per side", f"{sp['n_br']} bridges x {sp['m_bridge_kg']:.2f} kg (SiFe), G10 ring r {sp['r_ring0']:g}..{sp['r_ring1']:g}"),
        ("rotor, per side", f"3 utrons at 120°, 2 carrier discs ({sp['m_disc_kg']:.2f} kg each); B bridges offset {180 / sp['n_br']:g}°"),
    ]
    ax.axis("off")
    put = lambda x, k, text, **kw: ax.annotate(text, (x, 1.0), xycoords="axes fraction", xytext=(0, -k), textcoords="offset points",
                                               va="top", **kw)
    put(0.0, 0, "E. data (sim/pole_design_variants_op.json, sim/utron_profile.py)", fontsize=9.5, color=INK)
    k = 22
    for key, v in rows:
        put(0.0, k, key, fontsize=7.8, color=INK2)
        put(0.27, k, v, fontsize=7.8, color=INK)
        k += 15.5
    put(0.0, k + 8,
        "Assembly: wind the coil on its 1 mm G10 former; slide the NiFe strip and the G10 spacer through the window;\n"
        "insert the two half-cores from each side (they sit on the strip); lay in the slot cover; studs + cheeks; bolt the\n"
        "cheeks to the carrier discs; vacuum-impregnate. Grind the tip faces to r_g and bore the bridge faces in their\n"
        f"ring after assembly: the {sp['g']:g} mm gap needs the rotor and counter-rotor runout well below it.",
        fontsize=7.4, color=INK2)
    put(0.0, k + 70, "[OC] the section and its L(θ) are the solved 2-D model; [IR] the build details; [RH] the neck (B_sat, lap\n"
        "joints, the break's knee), the slot cover and the stud sizes are first-cut estimates: a nonlinear field check of the\n"
        "neck is the next step.", fontsize=7.4, color=INK2)


def main(pick="g 0.5 / 6 bridges / 1200 rpm"):
    op = json.load(open(os.path.join(SIM, "pole_design_variants_op.json")))["designs"][pick]
    rows = json.load(open(os.path.join(SIM, "pole_design_variants.json")))["rows"]
    row = [r for r in rows if r["design"] == op["design"]][0]
    sp = U.spec(op["design"], op["best"], row)
    fig = plt.figure(figsize=(21, 15.5), facecolor="white")
    gs = fig.add_gridspec(3, 3, width_ratios=(1.2, 1.0, 1.25), height_ratios=(0.36, 0.5, 0.62), wspace=0.1, hspace=0.12,
                          top=0.955, bottom=0.03, left=0.035, right=0.995)
    front(fig.add_subplot(gs[0:2, 0:2]), sp)
    side_coil(fig.add_subplot(gs[0, 2]), sp)
    side_tip(fig.add_subplot(gs[2, 0]), sp)
    flux(fig.add_subplot(gs[2, 1]), op["design"])
    table(fig.add_subplot(gs[1:, 2]), sp, op, pick)
    for ax in fig.axes:
        ax.tick_params(labelsize=7, colors=INK2)
        for s in ax.spines.values():
            s.set_color("#d2d2d7")
    fig.suptitle(f"Wound utron, detail: {sp['N_u']}-turn yoke coil on a split U-core with a NiFe neck, against a passive bridge"
                 f" (all dimensions in mm)", fontsize=12.5, color=INK, x=0.01, ha="left", y=0.995)
    os.makedirs(os.path.join(HERE, "figures"), exist_ok=True)
    out = os.path.join(HERE, "figures", "utron-core-detail.png")
    fig.savefig(out, dpi=115, bbox_inches="tight", facecolor="white")
    print(out)


if __name__ == "__main__":
    main(*sys.argv[1:2])
