"""docs/make_air_vane_drawing.py -- writes docs/figures/air-vane-stack-6mm.png: the electrostatic vane stack for AIR
(sim/air_stack_sizing.py, stages 4b / 4c): 6 mm gaps, Al vanes and Ca / Cb plates with every exposed edge a full round
(R = t / 2), on the sector widths searched for the full-round vanes.
  (a) a stator vane, (b) a rotor vane, (c) both at minimum C, with today's 30 deg stator dashed;
  (d) the half-section of side A from stack_sizing.layout (the elements that are built), with detail B: the rims;
  (e) the vane cell at minimum C at r 100 (sim/vane_cell): the 1.5 mm square-cut 24 / 22 deg stack against this one;
  (f) the rim's field: a vane edge between its neighbours' faces at the operating peak, against Peek's onset;
  (g) the data, from sim/air_stack_sizing_results.json.
Usage: python3 docs/make_air_vane_drawing.py [--t 3 --n 6]   (the vane thickness and count, from stage 4c's
       thick_compare rows or stage 4b's 'chosen'; default the designer's capped stack, 3 mm and 6 + 6)
"""
import json
import math
import os
import sys

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt                                   # noqa: E402
from matplotlib.patches import Polygon, Rectangle, Arc, Circle    # noqa: E402
import numpy as np                                                # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
SIM = os.path.join(HERE, "..", "sim")
sys.path.insert(0, SIM)
import stack_sizing as SS                                         # noqa: E402
import vane_cell as VC                                            # noqa: E402
import air_stack_sizing as AS                                     # noqa: E402

INK, INK2, DIM = "#1d1d1f", "#52514e", "#3a4a66"
AL_S, AL_R, AL_C, AL_C2, G10, STEEL, OLD = "#b4bac4", "#7f93ad", "#cfc6a8", "#a89f84", "#b9c2ab", "#8a8f99", "#c0392b"
EDGE = dict(ec=INK, lw=0.6)
R_IN, R_OUT, RING, SLEEVE, SHAFT = SS.TUBE_DEFAULTS["r_inMm"], SS.TUBE_DEFAULTS["r_outMm"], 12.0, SS.SLEEVE_R, SS.SHAFT_R
CAGE = (R_OUT + RING, R_OUT + RING + 4.0)                          # sim/tube_geometry.py: the G10 stator cage
OUT = os.path.join(HERE, "figures", "air-vane-stack-6mm.png")


# ------------------------------------------------------------------------------------------------------------ helpers
def dim(ax, a, b, text, off=(0.0, 0.0), fs=7.2, tx=(0.0, 0.0), rot=0, ext=True, ha="center", color=DIM):
    (x0, y0), (x1, y1) = a, b
    A, B = (x0 + off[0], y0 + off[1]), (x1 + off[0], y1 + off[1])
    if ext and (off[0] or off[1]):
        for p, q in ((a, A), (b, B)):
            ax.plot([p[0], q[0] + 0.6 * np.sign(off[0])], [p[1], q[1] + 0.6 * np.sign(off[1])], color=color, lw=0.35)
    ax.annotate("", A, B, arrowprops=dict(arrowstyle="<|-|>", lw=0.5, color=color, mutation_scale=5, shrinkA=0, shrinkB=0))
    ax.text(0.5 * (A[0] + B[0]) + tx[0], 0.5 * (A[1] + B[1]) + tx[1], text, fontsize=fs, color=color, ha=ha, va="center",
            rotation=rot, rotation_mode="anchor", bbox=dict(fc="white", ec="none", pad=0.25, alpha=0.9), zorder=8)


def note(ax, xy, xytext, text, fs=7.2, ha="left", color=INK2, va="center"):
    ax.annotate(text, xy, xytext, fontsize=fs, color=color, ha=ha, va=va, zorder=9,
                arrowprops=dict(arrowstyle="-", lw=0.45, color=color, shrinkA=1, shrinkB=0))


def pol(r, a_deg):
    """(x, y) at radius r and angle a (deg, clockwise from +y)."""
    t = math.radians(a_deg)
    return r * math.sin(t), r * math.cos(t)


def sector(r0, r1, a0, a1, n=60):
    a = np.linspace(a0, a1, n)
    return [pol(r1, t) for t in a] + [pol(r0, t) for t in a[::-1]]


def annulus(ax, r0, r1, fc, z=2, alpha=1.0):
    t = np.linspace(0, 2 * np.pi, 361)
    xo, yo, xi, yi = r1 * np.sin(t), r1 * np.cos(t), r0 * np.sin(t[::-1]), r0 * np.cos(t[::-1])
    ax.add_patch(Polygon(np.c_[np.r_[xo, xi], np.r_[yo, yi]], closed=True, fc=fc, ec=INK, lw=0.6, zorder=z, alpha=alpha))


def arc_dim(ax, r, a0, a1, text, fs=7.2, out=8.0, color=DIM):
    """an angular dimension on the arc of radius r between a0 and a1 (deg, clockwise from +y)."""
    ax.add_patch(Arc((0, 0), 2 * r, 2 * r, theta1=90 - a1, theta2=90 - a0, color=color, lw=0.6, zorder=6))
    for a in (a0, a1):
        (x0, y0), (x1, y1) = pol(r - 4, a), pol(r + 4, a)
        ax.plot([x0, x1], [y0, y1], color=color, lw=0.5, zorder=6)
    x, y = pol(r + out, 0.5 * (a0 + a1))
    ax.text(x, y, text, fontsize=fs, color=color, ha="center", va="center", zorder=7,
            bbox=dict(fc="white", ec="none", pad=0.2, alpha=0.9))


def arc_line(ax, r, a0, a1, color=INK2, lw=0.35):
    ax.plot(*zip(*[pol(r, t) for t in np.linspace(a0, a1, 40)]), color=color, lw=lw, zorder=4)


def round_lines(ax, a0, a1, R, r_lo, r_hi, inner, outer):
    """the tangent lines of a full round R along a sector's exposed edges: its two sides (offset R into the sector) and
    its inner (r_lo) or outer (r_hi) arc."""
    ra, rb = r_lo + (R if inner else 0.0), r_hi - (R if outer else 0.0)
    for a, sgn in ((a0, 1.0), (a1, -1.0)):
        ax.plot(*zip(*[pol(r, a + sgn * math.degrees(R / r)) for r in np.linspace(ra, rb, 20)]), color=INK2, lw=0.35,
                zorder=4)
    if inner:
        arc_line(ax, r_lo + R, a0 + math.degrees(R / (r_lo + R)), a1 - math.degrees(R / (r_lo + R)))
    if outer:
        arc_line(ax, r_hi - R, a0 + math.degrees(R / (r_hi - R)), a1 - math.degrees(R / (r_hi - R)))


def vane_stator(ax, ns, ws, R, fc=AL_S, z=2):
    per = 360.0 / ns
    for k in range(ns):
        c = per * k
        ax.add_patch(Polygon(sector(R_IN, R_OUT, c - 0.5 * ws, c + 0.5 * ws), closed=True, fc=fc, zorder=z, **EDGE))
        if R:
            round_lines(ax, c - 0.5 * ws, c + 0.5 * ws, R, R_IN, R_OUT, inner=True, outer=False)
            arc_line(ax, R_OUT + R, c + 0.5 * ws, c + per - 0.5 * ws)          # the ring's inner edge between sectors
    annulus(ax, R_OUT, R_OUT + RING, fc, z)


def vane_rotor(ax, ns, wr, R, shift=0.0, fc=AL_R, z=3, alpha=1.0):
    per = 360.0 / ns
    for k in range(ns):
        c = per * k + shift
        ax.add_patch(Polygon(sector(R_IN - 0.01, R_OUT, c - 0.5 * wr, c + 0.5 * wr), closed=True, fc=fc, zorder=z,
                             alpha=alpha, **EDGE))
        if R:
            round_lines(ax, c - 0.5 * wr, c + 0.5 * wr, R, R_IN, R_OUT, inner=False, outer=True)
            arc_line(ax, R_IN - R, c + 0.5 * wr, c + per - 0.5 * wr)           # the ring's outer edge between sectors
    annulus(ax, SLEEVE, R_IN, fc, z, alpha)


def plan_axes(ax, title):
    ax.set_aspect("equal"); ax.set_xlim(-185, 185); ax.set_ylim(-196, 190); ax.axis("off")
    ax.set_title(title, fontsize=10.5, loc="left", color=INK)
    ax.add_patch(Circle((0, 0), SHAFT, fc=STEEL, ec=INK, lw=0.5, zorder=1))


def slab(ax, z0, z1, r0, r1, fc, round_lo=False, round_hi=False, z=3, lw=0.5):
    """a vane / plate in the (z, r) half-section: z0..z1 thick, r0..r1, a full round on the r0 and / or r1 end."""
    R, zm = 0.5 * (z1 - z0), 0.5 * (z0 + z1)
    th = np.linspace(0.0, np.pi, 25)
    pts = [(zm - R * math.cos(t), r0 + R - R * math.sin(t)) for t in th] if round_lo else [(z0, r0), (z1, r0)]
    pts += [(zm + R * math.cos(t), r1 - R + R * math.sin(t)) for t in th] if round_hi else [(z1, r1), (z0, r1)]
    ax.add_patch(Polygon(pts, closed=True, fc=fc, ec=INK, lw=lw, zorder=z))


def rect(ax, z0, z1, r0, r1, fc, z=2, hatch=None, lw=0.5):
    ax.add_patch(Rectangle((z0, r0), z1 - z0, r1 - r0, fc=fc, ec=INK, lw=lw, zorder=z, hatch=hatch))


# ----------------------------------------------------------------------------------------- the panels from the solvers
def cell_panel(ax, p, title, cpg_min, r=100.0):
    """the vane cell at minimum C at radius r, half a sector period (rotor centre to stator centre: the cell is symmetric
    about both), equipotentials every 0.1 of the gap voltage, the vanes drawn true to shape over the grid's solution."""
    per = 360.0 / (p["N_sec"] / 2.0)
    s = VC.solve(r, p, 0.5 * per)
    if p.get("edge", "square") == "square":
        assert abs(s["C"] / SS._cell(r, p, 0.5 * per)[0] - 1) < 1e-12, "the cell differs from stack_sizing._cell"
    x, z, V, nt, ng, hz = s["x"], s["z"], s["V"], s["nt"], s["ng"], s["hz"]
    nz = len(z)
    V2 = np.concatenate([V, V], axis=1)
    z2 = (np.arange(2 * nz) + 0.5) * hz
    keep = z2 <= z2[0] + (nz + nt) * hz                             # stator | gap | rotor | gap | stator
    P2 = 0.5 * math.radians(per) * r
    kx = x <= P2 + 1e-9
    X, Z = np.meshgrid(x[kx], z2[keep], indexing="ij")
    W = V2[np.ix_(kx, keep)]
    ax.contourf(X, Z, W, levels=np.linspace(0, 1, 21), cmap="coolwarm", alpha=0.55, zorder=1)
    ax.contour(X, Z, W, levels=np.linspace(0.1, 0.9, 9), colors=INK2, linewidths=0.45, zorder=2)
    # the vanes: conductor rows k0 .. k0 + nt - 1, the faces through the outermost rows (the cell's convention)
    t_n = (nt - 1) * hz
    R = 0.5 * t_n if p.get("edge", "square") == "round" else 0.0
    zs0, zr0, zs1 = z2[0], z2[nt + ng], z2[2 * (nt + ng)]
    xr = r * math.radians(0.5 * p["wr_deg"])                        # the rotor's edge (its centre line is x = 0)
    xs = P2 - r * math.radians(0.5 * p["ws_deg"])                   # the stator's edge (its centre line is x = P2)
    th = np.linspace(-0.5 * np.pi, 0.5 * np.pi, 25)

    def vane(xa, xb, z0, at_right, fc):
        if not R:
            ax.add_patch(Rectangle((xa, z0), xb - xa, t_n, fc=fc, ec=INK, lw=0.5, zorder=3)); return
        if at_right:
            pts = [(xa, z0), (xb - R, z0)] + [(xb - R + R * math.cos(u), z0 + R + R * math.sin(u)) for u in th] + \
                  [(xb - R, z0 + t_n), (xa, z0 + t_n)]
        else:
            pts = [(xb, z0 + t_n), (xa + R, z0 + t_n)] + [(xa + R - R * math.cos(u), z0 + R - R * math.sin(u)) for u in th] + \
                  [(xa + R, z0), (xb, z0)]
        ax.add_patch(Polygon(pts, closed=True, fc=fc, ec=INK, lw=0.5, zorder=3))
    for z0 in (zs0, zs1):
        vane(xs, P2, z0, False, AL_S)
    vane(0.0, xr, zr0, True, AL_R)
    zm = zr0 + 0.5 * t_n
    dim(ax, (xr, zm), (xs, zm), f"{xs - xr:.1f}", fs=7.0)
    ax.set_aspect("equal")
    ax.set_xlim(0.0, P2); ax.set_ylim(zs0 + 0.5 * t_n, zs1 + 0.5 * t_n)
    ax.tick_params(labelsize=6.5)
    ax.set_title(title + f"\nC_min per gap {cpg_min:.2f} pF", fontsize=8.3, loc="left", color=INK)


def rim_panel(axm, axp, t_new, g, v_op_kV, peaks):
    """the rim: a vane's edge between its neighbours' faces (g each side). Left: the field of the new rim. Right: the
    surface field around both full rounds at the operating peak, against Peek's onset for each radius."""
    e = VC.edge_field(t_new, g, "round", field=True)
    V, xs, zs = e["V"], e["xs"], e["zs"]
    k = (xs >= -14.0) & (xs <= 12.0)
    Xh, Zh = np.meshgrid(xs[k], zs, indexing="ij")
    X, Z = np.concatenate([Xh[:, ::-1], Xh], axis=1), np.concatenate([-Zh[:, ::-1], Zh], axis=1)
    VV = np.concatenate([V[k][:, ::-1], V[k]], axis=1)
    axm.contourf(X, Z, VV, levels=np.linspace(0, 1, 21), cmap="coolwarm", alpha=0.55, zorder=1)
    axm.contour(X, Z, VV, levels=np.linspace(0.1, 0.9, 9), colors=INK2, linewidths=0.45, zorder=2)
    R, H = 0.5 * t_new, 0.5 * t_new + g
    th = np.linspace(-0.5 * np.pi, 0.5 * np.pi, 40)
    axm.add_patch(Polygon([(-14, -R), (-R, -R)] + [(-R + R * math.cos(u), R * math.sin(u)) for u in th] + [(-R, R), (-14, R)],
                          closed=True, fc=AL_S, ec=INK, lw=0.6, zorder=3))
    for zz in (H, -H - 1.2):
        axm.add_patch(Rectangle((-14, zz), 26, 1.2, fc=AL_R, ec=INK, lw=0.5, zorder=3))
    a = math.radians(e["angle_deg"])
    for sgn in (1, -1):
        axm.plot(-R + R * math.cos(a), sgn * R * math.sin(a), "o", ms=3.5, color=OLD, zorder=5)
    axm.set_aspect("equal"); axm.set_xlim(-14, 12); axm.set_ylim(-H - 1.4, H + 1.4)
    axm.tick_params(labelsize=6.5)
    axm.set_xlabel("mm, from the rim's tip", fontsize=7.5)
    for t, col in ((1.5, INK2), (t_new, OLD)):
        ef = VC.edge_field(t, g, "round")
        ang, val = np.array(ef["profile"][0]), np.array(ef["profile"][1]) * v_op_kV * 10.0
        m = (ang >= 0) & (ang <= 90)                                   # the half domain; the other half is its mirror
        axp.plot(np.r_[-ang[m][::-1], ang[m]], np.r_[val[m][::-1], val[m]], color=col, lw=1.2, label=f"{t:g} mm, R{0.5 * t:g}")
        on = VC.peek_kV_per_cm(0.5 * t)
        axp.axhline(on, color=col, ls=(0, (4, 2)), lw=0.8)
        axp.text(88, on + 0.8, f"Peek onset {on:.0f}", fontsize=6.8, color=col, ha="right", va="bottom")
    f = v_op_kV / g * 10.0
    axp.axhline(f, color=DIM, lw=0.6, ls=":")
    axp.text(-88, f + 0.8, f"faces {f:.0f}", fontsize=6.8, color=DIM, va="bottom")
    axp.set_xlim(-90, 90); axp.set_ylim(0, 80); axp.set_xticks([-90, -45, 0, 45, 90])
    axp.tick_params(labelsize=6.5)
    axp.set_xlabel("on the round (deg; 0 the tip, ±90 the faces)", fontsize=7.5)
    axp.set_ylabel(f"surface field at {v_op_kV:.1f} kV (kV/cm)", fontsize=7.5)
    axp.legend(fontsize=7, loc="lower center", frameon=False)
    axp.set_title(f"peak {peaks[1]['E_peak_kV_cm']:.0f} kV/cm = {peaks[1]['ratio_to_onset']:.2f} × its onset\n"
                  f"(1.5 mm: {peaks[0]['E_peak_kV_cm']:.0f} kV/cm = {peaks[0]['ratio_to_onset']:.2f} ×)", fontsize=8.3,
                  loc="left", color=INK)


def section_extent(lad, g):
    """the half-section's data limits (z', r): from the hub to just past the Ca|reluctance bearing."""
    el = lad["tube_geometry"]["elements"]
    zf = [e for e in el if e["kind"] == "hub"][0]["z0"]
    carel = [e for e in el if e["side"] == "A" and e["kind"] == "bearing" and e["where"] not in ("hub face", "end")][0]
    return (-40.0, zf - carel["z0"] + g + 24.0 + 70.0), (-72.0, 262.0)


def section_panel(ax, axd, lad, q, g):
    """(d) side A from stack_sizing.layout, z' from the hub's face outward; the vanes as sim/tube_geometry builds them
    (stator: sector + outer ring into the cage; rotor: inner ring from the sleeve + sector), full rounds on the rims."""
    el = lad["tube_geometry"]["elements"]
    hub = [e for e in el if e["kind"] == "hub"][0]
    zf = hub["z0"]
    zz = lambda e: (zf - e["z1"], zf - e["z0"])
    A = [e for e in el if e["side"] == "A"]
    vanes = sorted([e for e in A if e["kind"] == "C1 vane"], key=lambda e: -e["z0"])
    plates = sorted([e for e in A if e["kind"] == "Ca plate"], key=lambda e: -e["z0"])
    hubface = [e for e in A if e["kind"] == "bearing" and e["where"] == "hub face"][0]
    carel = [e for e in A if e["kind"] == "bearing" and e["where"] not in ("hub face", "end")][0]
    B, t = SS.BEARING, q["t_vaneMm"]
    z_end = zz(carel)[1] + g + 24.0
    rect(ax, -36, 0, 0, R_OUT, "#ececec", z=1, hatch="////", lw=0.4)
    ax.text(-18, 0.5 * R_OUT, "hub\n(bicone,\nAH)", fontsize=6.8, color=INK2, ha="center", va="center", zorder=5,
            bbox=dict(fc="white", ec="none", pad=0.4, alpha=0.85))
    fl = [e for e in A if e["kind"] == "flange"][0]
    rect(ax, *zz(fl), 0, fl["r1"], STEEL, z=2)
    rect(ax, zz(fl)[1], z_end, 0, SHAFT, STEEL, z=1)
    rect(ax, zz(hubface)[1], zz(carel)[0], SHAFT, SLEEVE, G10, z=2)
    rect(ax, zz(carel)[1], z_end, SHAFT, SLEEVE, G10, z=2)
    cz0, cz1 = zz(hubface)[0], zz(carel)[1]
    rect(ax, cz0, z_end, *CAGE, G10, z=2)
    for b in (hubface, carel):
        z0, z1 = zz(b); zc = 0.5 * (z0 + z1)
        rect(ax, zc - 0.5 * B["width"], zc + 0.5 * B["width"], SHAFT, 0.5 * B["od"], STEEL, z=3)
        rect(ax, zc - 0.5 * B["spider_t"], zc + 0.5 * B["spider_t"], 0.5 * B["od"], CAGE[0], G10, z=3)
    for e in vanes:
        z0, z1 = zz(e)
        if e["body"] == "stator":
            slab(ax, z0, z1, R_IN, R_OUT + RING, AL_S, round_lo=True)
        else:
            slab(ax, z0, z1, SLEEVE, R_OUT, AL_R, round_hi=True)
    for i, e in enumerate(plates):
        slab(ax, *zz(e), R_IN, R_OUT, AL_C if i % 2 == 0 else AL_C2, round_lo=True, round_hi=True)
    zb = z_end - 9.0
    ax.plot([zb - 3, zb + 3, zb - 3, zb + 3, zb - 3], [-4, 40, 85, 130, 172], color=INK2, lw=0.6, zorder=6)
    ax.text(z_end + 4, 100, "reluctance section\n(wound utrons,\nbridges), then\nthe end bearing", fontsize=6.6, color=INK2,
            va="center", ha="left")
    v0, v1 = zz(vanes[0])[0], zz(vanes[-1])[1]
    p0, p1 = zz(plates[0])[0], zz(plates[-1])[1]
    n, nca = q["n_plates"], len(plates)
    dim(ax, (v0, CAGE[1]), (v1, CAGE[1]), f"C1: {n} + {n} vanes, {2 * n - 1} gaps  →  {v1 - v0:.0f}", off=(0, 12))
    dim(ax, (p0, CAGE[1]), (p1, CAGE[1]), f"Ca: {nca} plates  →  {p1 - p0:.0f}", off=(0, 27))
    dim(ax, (v1, 120), (p0, 120), f"{p0 - v1:g}", fs=6.5, tx=(0, 6), ext=False)
    dim(ax, (v0, -12), (p1, -12), f"electrostatic stacks, side A: {p1 - v0:.0f}  (first vane to last plate)", ext=False)
    dim(ax, (0, -28), (zz(carel)[1], -28), f"hub face to the Ca|reluctance bearing: {zz(carel)[1]:.0f}", ext=False)
    note(ax, (0.5 * sum(zz(hubface)), 120), (-36, 236), "hub-face bearing + G10 spider", ha="left", va="bottom")
    note(ax, (0.5 * sum(zz(carel)), 120), (0.5 * sum(zz(carel)) - 4, 236), "Ca|reluctance bearing + G10 spider",
         ha="center", va="bottom")
    s0 = [e for e in vanes if e["body"] == "stator"][min(3, n - 1)]
    r0 = [e for e in vanes if e["body"] == "rotor"][min(5, n - 1)]
    note(ax, (0.5 * sum(zz(s0)), 156), (v0 + 40, 212), f"stator vane, node 1: r {R_IN:g}–{R_OUT:g} + ring to "
         f"{R_OUT + RING:g}", ha="left", va="bottom")
    note(ax, (0.5 * sum(zz(r0)), 36), (-36, -46), f"rotor vane, R-A: ring from r {SLEEVE:g}, sector to {R_OUT:g}",
         ha="left")
    note(ax, (0.5 * sum(zz(plates[min(4, nca - 1)])), 100), (p0, -62), "Ca plates: full annuli, nodes 1 / 2 alternating",
         ha="left")
    note(ax, (z_end - 20, CAGE[1]), (z_end + 4, 186), f"G10 stator cage\nr {CAGE[0]:g}–{CAGE[1]:g}", ha="left")
    note(ax, (z_end - 30, 0.5 * (SHAFT + SLEEVE)), (z_end + 4, 26), f"G10 sleeve r {SHAFT:g}–{SLEEVE:g}\non the d {2 * SHAFT:g} "
         "shaft", ha="left")
    zs = [zz(e) for e in vanes[:6]]
    zbc = 0.5 * (zs[0][0] + zs[4][1])
    ax.add_patch(Circle((zbc, R_IN), 26, fill=False, ec=OLD, lw=0.8, zorder=7))
    ax.text(zbc + 22, R_IN - 26, "B", fontsize=9, color=OLD, weight="bold", zorder=7)
    (xa, xb), (ya, yb) = section_extent(lad, g)
    ax.set_aspect("equal"); ax.set_xlim(xa, xb); ax.set_ylim(ya, yb)
    ax.set_xlabel("z′ (mm), from the hub face outward (side B is the mirror image: C2, Cb)", fontsize=8)
    ax.set_ylabel("r (mm)", fontsize=8)
    ax.tick_params(labelsize=7)
    ax.spines[["top", "right"]].set_visible(False)
    # detail B: the stator rims at r 50 between the rotor vanes, which run on inward as their rings
    for e in vanes[:6]:
        z0, z1 = zz(e)
        if e["body"] == "stator":
            slab(axd, z0, z1, R_IN, R_IN + 40, AL_S, round_lo=True, lw=0.7)
        else:
            slab(axd, z0, z1, R_IN - 40, R_IN + 40, AL_R, lw=0.7)
    axd.set_xlim(zs[0][0] - 3, zs[4][1] + 3); axd.set_ylim(R_IN - 9, R_IN + 15)
    axd.set_aspect("equal")
    dim(axd, (zs[2][0], R_IN + 11), (zs[2][1], R_IN + 11), f"{t:g}", fs=6.8, tx=(0, 1.8), ext=False)
    dim(axd, (zs[2][1], R_IN + 11), (zs[3][0], R_IN + 11), f"{g:g}", fs=6.8, tx=(0, 1.8), ext=False)
    dim(axd, (zs[1][0], R_IN - 6), (zs[3][0], R_IN - 6), f"{zs[3][0] - zs[1][0]:g}, rotor to rotor", fs=6.5,
        tx=(0, -1.9), ext=False)
    zc = 0.5 * (zs[2][0] + zs[2][1])
    pt = (zc - 0.5 * t * math.cos(math.radians(50)), R_IN + 0.5 * t - 0.5 * t * math.sin(math.radians(50)))
    note(axd, pt, (zc - 3.5, R_IN - 2.5), f"R{0.5 * t:g}", fs=6.8, ha="right")
    axd.plot([zs[0][0] - 3, zs[4][1] + 3], [R_IN, R_IN], color=DIM, lw=0.4, ls=(0, (6, 2, 1, 2)), zorder=4)
    axd.text(zs[4][1] + 2.5, R_IN + 0.5, f"r {R_IN:g}", fontsize=6.5, color=DIM, ha="right", va="bottom", zorder=5)
    axd.tick_params(labelsize=6)
    axd.set_title(f"detail B, enlarged: the stator rims at r {R_IN:g},\nfull round R{0.5 * t:g}, over the rotor vanes' rings",
                  fontsize=8.0, loc="left", color=OLD)
    for sp in axd.spines.values():
        sp.set_color(OLD)


# ------------------------------------------------------------------------------------------------------------ the sheet
def pick(tv, t, n):
    """the drawn design: a stage 4c row (t, n), or stage 4b's chosen stack."""
    rows = [q for q in tv.get("compare", []) if q["t_vaneMm"] == t and q["n_plates"] == n]
    if rows:
        return rows[0]
    c = tv["chosen"]
    assert (c["t_vaneMm"], c["n_plates"]) == (t, n), f"no results for {t} mm, {n} + {n}: run air_stack_sizing --thick-compare"
    return c


def main(t_sel=3.0, n_sel=6):
    res = json.load(open(os.path.join(SIM, "air_stack_sizing_results.json")))
    tv = res["thick_vanes"]
    q = pick(tv, t_sel, n_sel)
    rule = [r for r in tv.get("compare", []) + [tv["chosen"]] if r["t_vaneMm"] == q["t_vaneMm"] and r.get("n_rule", True)
            and r["n_plates"] >= q["n_plates"]]
    qr = rule[0] if rule and rule[0]["n_plates"] != q["n_plates"] else None      # the same vanes at the C_max rule
    old = tv["rows"][0]                                          # the stage 2 stack: 1.5 mm square-cut, 24 / 22 deg
    built = res["gap_sweep"][0]                                  # today's stack in air (3 mm gaps, 8 + 8 x 1.5 mm)
    vac = res["base_vacuum"]
    assert (old["t_vaneMm"], old["edge"], built["gap_mm"]) == (1.5, "square", 3.0)
    ns, ws, wr, g, n, t = q["sectors"], q["ws_deg"], q["wr_deg"], q["gap_mm"], q["n_plates"], q["t_vaneMm"]
    R, per = 0.5 * t, 360.0 / ns
    ws_today = SS.TUBE_DEFAULTS["ws_deg"]
    clr, clr_old, clr_today = 0.5 * (per - ws - wr), 0.5 * (60.0 - old["ws_deg"] - old["wr_deg"]), 0.5 * (60.0 - ws_today - 22.0)
    geo = dict(N_sec=2 * ns, ws_deg=ws, wr_deg=wr, t_vaneMm=t, edge="round", pitch_fixed_mm=g + t)
    lad = SS.size_stack("tube", AS.plates(g, n, "air", geo), dict(rpm=AS.RPM))
    assert abs(lad["tube_caps"]["C_max"] / q["C_max_pF"] - 1) < 1e-9
    assert abs(AS.es_lengths(lad["tube_geometry"])[0] - q["L_es_side_mm"]) < 1e-9
    v_op = q["V_op_kV"]
    rims = {e["t_mm"]: e for e in tv["rim_field"]}
    onset = lambda e, m=1.0: m * v_op * e["peek_kV_cm"] / e["E_peak_kV_cm"]     # the peak at which the rim reaches onset
    rim, rim15 = rims[t], rims[1.5]

    fig = plt.figure(figsize=(22, 16.6), facecolor="white")
    gs = fig.add_gridspec(3, 3, height_ratios=(1.0, 0.74, 0.56), width_ratios=(1, 1, 1.0), hspace=0.24, wspace=0.10,
                          top=0.945, bottom=0.04, left=0.03, right=0.985)
    fig.suptitle(f"Electrostatic vane stack for AIR: {g:g} mm gaps, {ns} sectors of {ws:g}° (stator) / {wr:g}° (rotor), "
                 f"{n} + {n} vanes per varicap per side; vanes and Ca / Cb plates Al {t:g} mm with full-round edges R{R:g}"
                 f"  (dimensions in mm)", fontsize=13.0, x=0.01, ha="left")

    # (a) stator vane
    ax = fig.add_subplot(gs[0, 0])
    plan_axes(ax, f"(a) stator vane (counter-rotor, node 1 / node 4): {ns} × {ws:g}° on a {per:g}° pitch")
    vane_stator(ax, ns, ws, R)
    arc_dim(ax, 120, -0.5 * ws, 0.5 * ws, f"{ws:g}°", out=-14)
    arc_dim(ax, 128, 0.0, per, f"{per:g}° pitch", out=11)
    dim(ax, (0, 0), (0, R_IN), f"r {R_IN:g}", off=(-14, 0), rot=90, tx=(-5, 0))
    dim(ax, (0, 0), pol(R_OUT, 180 + 0.5 * per), f"r {R_OUT:g}", tx=(10, 6))
    note(ax, pol(R_OUT + 6, 180 - 0.5 * per - 10), (128, -190), f"outer ring r {R_OUT:g}–{R_OUT + RING:g},\ninto the G10 cage",
         ha="center", va="bottom")
    ax.text(-182, -194, f"Al {t:g} mm. Every exposed edge a full round R{R:g}:\nthe sectors' sides and inner arc, and the ring's\n"
            "inner edge (thin lines: where the rounds begin)", fontsize=7.4, color=INK2, va="bottom")

    # (b) rotor vane
    ax = fig.add_subplot(gs[0, 1])
    plan_axes(ax, f"(b) rotor vane (rotor, R-A / R-B): {ns} × {wr:g}° on a {per:g}° pitch")
    vane_rotor(ax, ns, wr, R)
    arc_dim(ax, 120, -0.5 * wr, 0.5 * wr, f"{wr:g}°", out=-14)
    dim(ax, (0, 0), pol(R_OUT, 180 + per), f"r {R_OUT:g}", tx=(-12, 4))
    note(ax, pol(0.5 * (SLEEVE + R_IN), 0.5 * per), (112, 172), f"inner ring r {SLEEVE:g}–{R_IN:g} on the G10 rotor sleeve",
         ha="center")
    ax.text(-182, -194, f"Al {t:g} mm. Every exposed edge a full round R{R:g}:\nthe sectors' sides and outer arc, and the ring's\n"
            "outer edge", fontsize=7.4, color=INK2, va="bottom")

    # (c) both at minimum C, today's stator dashed
    ax = fig.add_subplot(gs[0, 2])
    plan_axes(ax, "(c) at minimum C: the rotor sectors centred between the stator sectors")
    vane_stator(ax, ns, ws, 0.0)
    vane_rotor(ax, ns, wr, 0.0, shift=0.5 * per, z=3, alpha=0.9)
    if ns == 6:
        for k in range(6):
            for a in (60.0 * k - 0.5 * ws_today, 60.0 * k + 0.5 * ws_today):
                ax.plot(*zip(pol(R_IN, a), pol(R_OUT, a)), color=OLD, lw=1.0, ls=(0, (4, 2)), zorder=5)
    arc_dim(ax, 100, 0.5 * ws, 0.5 * ws + clr, f"{clr:g}°", out=12)
    arc_dim(ax, 100, 0.5 * per + 0.5 * wr, 0.5 * per + 0.5 * wr + clr, f"{clr:g}°", out=12)
    ax.text(0, -178, f"clearance {clr:g}° each side = {100 * math.radians(clr):.1f} mm at r 100 "
                     f"({R_IN * math.radians(clr):.1f} at r {R_IN:g}, {R_OUT * math.radians(clr):.1f} at r {R_OUT:g})",
            fontsize=8.2, color=INK, ha="center")
    ax.text(0, -192, f"the 1.5 mm stack (24° / 22°): {clr_old:.0f}°, {100 * math.radians(clr_old):.1f} mm; today's "
                     f"{ws_today:g}° stator (red, dashed): {clr_today:g}°, {100 * math.radians(clr_today):.1f} mm",
            fontsize=8.0, color=OLD, ha="center")

    # (d) the half-section of side A, sized to its content, with detail B beside it
    FW, FH = fig.get_size_inches()
    bb = gs[1, 0:2].get_position(fig)
    (xa, xb), (ya, yb) = section_extent(lad, g)
    h_in = bb.height * FH
    w_in = min(h_in * (xb - xa) / (yb - ya), bb.width * FW - 4.2)
    h_in = w_in * (yb - ya) / (xb - xa)
    ax = fig.add_axes([bb.x0 + 0.35 / FW, bb.y1 - h_in / FH, w_in / FW, h_in / FH])
    w_d = min(4.6, bb.width * FW - w_in - 1.3)
    axd = fig.add_axes([bb.x0 + (0.35 + w_in + 0.8) / FW, bb.y0 + 0.16 * bb.height, w_d / FW, 0.62 * bb.height])
    section_panel(ax, axd, lad, q, g)
    ax.set_title("(d) side A, half-section in the plane of a sector at alignment (stack_sizing.layout):\nhub-face bearing, "
                 "C1, Ca, Ca|reluctance bearing", fontsize=10.5, loc="left", color=INK)

    # (e) the vane cell at minimum C: the 1.5 mm stack against this one
    pe = gs[2, 0].subgridspec(1, 2, wspace=0.28)
    p_old = dict(SS.TUBE_DEFAULTS, g_vMm=g, dielectric="air", N_sec=12, ws_deg=old["ws_deg"], wr_deg=old["wr_deg"],
                 t_vaneMm=old["t_vaneMm"], edge="square")
    p_new = dict(SS.TUBE_DEFAULTS, g_vMm=g, dielectric="air", N_sec=2 * ns, ws_deg=ws, wr_deg=wr, t_vaneMm=t, edge="round")
    ax1, ax2 = fig.add_subplot(pe[0, 0]), fig.add_subplot(pe[0, 1])
    cell_panel(ax1, p_old, f"(e) minimum C at r 100, half a period:\n1.5 mm square-cut, {old['ws_deg']:g}° / "
               f"{old['wr_deg']:.0f}°", old["per_gap_min_pF"])
    cell_panel(ax2, p_new, f"\n{t:g} mm full round, {ws:g}° / {wr:g}°", q["per_gap_min_pF"])
    for a_ in (ax1, ax2):
        a_.set_xlabel("along the arc (mm)", fontsize=7.5)
    ax1.set_ylabel("axial (mm)", fontsize=7.5)

    # (f) the rim
    pf = gs[2, 1].subgridspec(1, 2, width_ratios=(1.0, 1.3), wspace=0.34)
    axm, axp = fig.add_subplot(pf[0, 0]), fig.add_subplot(pf[0, 1])
    rim_panel(axm, axp, t, g, v_op, (rim15, rim))
    axm.set_title(f"(f) a rim at {v_op:.1f} kV, {g:g} mm to the\nfaces; equipotentials every 0.1, ● the peak",
                  fontsize=8.3, loc="left", color=INK)

    # (g) the data
    axt = fig.add_subplot(gs[1:, 2]); axt.axis("off")
    L_var, L_ca = q["L_varicap_mm"], q["L_es_side_mm"] - q["L_varicap_mm"] - g
    P_old = res["best_per_gap"][0]["P_clamped_W"]
    nr = qr["n_plates"] if qr else None
    ref = (lambda key, f="{:.2f}": f"{nr} + {nr}: " + f.format(qr[key]) + "; ") if qr else (lambda key, f="": "")
    rows = [
        ("air, 1 atm", f"gap {g:g} mm: breakdown {res['gap_sweep'][2]['V_bd_kV']:.1f} kV (uniform field), operating "
                       f"{v_op:.1f} kV (÷ {res['margin']:.1f})"),
        ("vanes", f"{n} stator + {n} rotor per varicap per side, Al {t:g} mm, full-round edges R{R:g}; {2 * n - 1} gaps"),
        ("sectors", f"{ns} on a {per:g}° pitch: stator {ws:g}°, rotor {wr:g}° (searched for 4 mm at the C_max rule)"),
        ("clearance at min C", f"{clr:g}° each side, {100 * math.radians(clr):.1f} mm at r 100 (1.5 mm stack: {clr_old:.0f}°, "
                               f"{100 * math.radians(clr_old):.1f} mm)"),
        ("C per gap", f"{q['per_gap_min_pF']:.2f} – {q['per_gap_max_pF']:.1f} pF (1.5 mm stack: {old['per_gap_min_pF']:.2f} – "
                      f"{old['per_gap_max_pF']:.1f})"),
        ("C1 = C2", f"{q['C_min_pF']:.0f} – {q['C_max_pF']:.0f} pF, κ {q['kappa']:.2f} ({ref('kappa')}1.5 mm stack "
                    f"{old['kappa']:.2f}; vacuum {vac['kappa']:.1f})"),
        ("Ca = Cb", f"{q['Ca_pF']:.0f} pF: {q['n_gap_ca'] + 1} full-annulus plates, Al {t:g} mm, rims R{R:g}; "
                    f"{q['n_gap_ca']} gaps of {g:g}"),
        ("gain z", f"{q['z']:.3f} per cycle ({ref('z', '{:.3f}')}1.5 mm stack {old['z']:.3f}; vacuum {vac['z']:.3f})"),
        ("pump", f"{q['P_clamped_W']:.2f} W clamped at {v_op:.1f} kV, {res['rpm']:.0f} rpm relative "
                 f"({q['cycles_per_rev'] * res['rpm'] / 60:.0f} Hz)"),
        ("", f"({ref('P_clamped_W')}1.5 mm stack {P_old:.2f} W; today's stack in air {built['P_clamped_W']:.2f} W at "
             f"{built['V_op_kV']:.1f} kV)"),
        ("stacks, side A", f"{L_var:g} C1 + {g:g} + {L_ca:g} Ca = {q['L_es_side_mm']:.0f} mm, first vane to last plate"),
        ("", f"({ref('L_es_side_mm', '{:.0f}')}1.5 mm stack {old['L_es_side_mm']:.0f}; today's {built['L_es_side_mm']:.0f})"),
        ("tube", f"{q['L_tube_mm']:.0f} mm (stack_sizing.layout; {ref('L_tube_mm', '{:.0f}')}the wound build "
                 f"{vac['L_tube_mm']:.0f})"),
        ("aluminium", f"rotor vanes {q['rotor_vanes_kg']:.1f} kg; counter-rotor: stator vanes {q['stator_vanes_kg']:.1f} + "
                      f"Ca / Cb plates {q['ca_plates_kg']:.1f} kg"),
        ("rims at the peak", f"{rim['E_peak_kV_cm']:.1f} kV/cm (× {rim['enhancement']:.2f} the faces' "
                             f"{rim['E_face_kV_cm']:.1f}); onset at {onset(rim):.1f} kV smooth, {onset(rim, 0.85):.1f} kV "
                             f"handled (m 0.85)"),
        ("", "(smooth / handled, kV: " + ", ".join(f"{e['t_mm']:g} mm {onset(e):.1f} / {onset(e, 0.85):.1f}"
                                                    for e in tv["rim_field"] if e["t_mm"] != t) + ")"),
    ]
    axt.set_title("(g) data (sim/air_stack_sizing_results.json: thick_vanes)", fontsize=10.5, loc="left", color=INK)
    y = 0.985
    for k, v in rows:
        axt.text(0.0, y, k, fontsize=8.4, weight="bold", color=INK, transform=axt.transAxes, va="top")
        axt.text(0.235, y, v, fontsize=8.4, color=INK, transform=axt.transAxes, va="top")
        y -= 0.0415
    kap = "; ".join(f"{r['t_vaneMm']:g} mm {r['kappa']:.2f}" for r in sorted(
        [r for r in tv.get("compare", []) + [tv["chosen"]] if r.get("n_rule", True)], key=lambda r: r["t_vaneMm"]))
    paras = []
    if qr:
        paras.append(
            f"The cap: {n} + {n} vanes give {2 * n - 1} working gaps per side and C_max {q['C_max_pF']:.0f} pF against the "
            f"{vac['C_max_pF']:.0f} pF the ladder was sized for (Ca = Cb = 1.1 C_max scale with it). Power falls to "
            f"{q['P_clamped_W'] / qr['P_clamped_W']:.2f} of the {nr} + {nr} stack's, the stacks to {q['L_es_side_mm']:.0f} mm "
            f"per side and the tube to {q['L_tube_mm']:.0f} mm. z falls {qr['z']:.3f} → {q['z']:.3f}, mostly because the "
            "fixed 20 pF stray weighs about 3× more against the smaller stack; with 4 mm vanes it drops below 1.3.")
    paras += [
        f"The thickness: thicker edges fringe more at minimum C (κ at the C_max rule on {ws:g}° / {wr:g}°: {kap}) but "
        f"hold more voltage at the rims; against the {v_op:.1f} kV peak, {t:g} mm reaches Peek's onset at "
        f"{onset(rim):.1f} kV smooth and {onset(rim, 0.85):.1f} kV handled, 1.5 mm at {onset(rim15):.1f} / "
        f"{onset(rim15, 0.85):.1f} kV.",
        f"Against today's stack in air (3 mm gaps, 8 + 8 × 1.5 mm, clamped near {built['V_op_kV']:.0f} kV): "
        f"{built['P_clamped_W']:.2f} W from {built['L_es_side_mm']:.0f} mm per side; this one gives "
        f"{q['P_clamped_W']:.2f} W at {v_op:.0f} kV from {q['L_es_side_mm']:.0f} mm.",
        "[OC] the Laplace solves (vane cell, rim), the core's z; Peek's law (empirical). [IR] the full round on the grid, "
        "the 2-D cell with its 2 pF rim floor and 0.25 mm grid (finer grids raise C_min by up to 7 %), the cosine C(θ), "
        "the sector widths (searched for 4 mm at the C_max rule, not for this count). [RH] the 1.5 margin on breakdown, "
        "the rim field read as a corona margin and the surface factor, the air's humidity and temperature.",
    ]
    import textwrap
    notes = "\n\n".join(textwrap.fill(x, 118) for x in paras)
    axt.text(0.0, y - 0.01, notes, fontsize=7.9, color=INK2, transform=axt.transAxes, va="top")

    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    fig.savefig(OUT, dpi=120)
    plt.close(fig)
    print(OUT)


if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--t", type=float, default=3.0, help="vane thickness, mm")
    ap.add_argument("--n", type=int, default=6, help="vanes per varicap per side (stator = rotor)")
    a = ap.parse_args()
    main(a.t, a.n)
