"""docs/make_rings_drawing.py -- the manufacturing drawing of the rings on the vessel, DCCREG-HUB-201 (A3):

  * A, the half-section of the hub at 2:1: the borosilicate vessel, rings A and B (copper foil bands) with their
    beads, the gel pocket and the bead grooves of the PEEK retainer, the AH seats; the bands' edges and the gap;
  * B, C, details at 5:1: the polar and the equatorial bead on the glass, in the gel, under the PEEK;
  * D, the foil gore for one band (flat pattern, 4:1), cut twelve to a band;
  * the feature table (both rings), the notes and the title block.
Every number comes from the record (sim/hub_rings_build_results.json) and the spec (presets/hub-locked.json).
Usage: python3 docs/make_rings_drawing.py   (writes docs/drawings/DCCREG-HUB-201.pdf / .png)
"""
import json
import math
import os
import sys

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt                                    # noqa: E402
import numpy as np                                                 # noqa: E402
from matplotlib.patches import Circle, Polygon, Rectangle, Wedge   # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(ROOT, "sim"))
import make_core_drawing as D                                      # noqa: E402  (the A3 sheet and its primitives)
import hub_rings_build as B                                        # noqa: E402

DWG = "DCCREG-HUB-201"
OUT = os.path.join(HERE, "drawings")
GORES = 12                         # gores per band [RH]: the flat foil conforms to the sphere within a gore
OVERLAP = 1.0                      # mm, each gore's soldered overlap on its neighbour
INK, DIMC = D.INK, D.DIMC
TXT = D.TXT
GLASS, GEL, PEEK, CU = "#e4eff6", "#f3efb8", "#efe6cf", "#b87333"


def geom():
    R = json.load(open(os.path.join(ROOT, "sim", "hub_rings_build_results.json")))
    rec = R["record"]
    hub = B.hub_system()
    g = dict(rec=rec, hub=hub, Rv=hub["R_v"], Rin=hub["R_in"], fill=hub["fill_t"], foil=B.FOIL_T,
             tp=rec["theta_p"], te=rec["theta_e"], rp=rec["rho_pol_mm"], rq=rec["rho_eq_mm"])
    beads = []
    for nm, th, rho in (("polar", g["tp"], g["rp"]), ("equatorial", g["te"], g["rq"])):
        t = math.radians(th)
        beads.append(dict(name=nm, theta=th, rho=rho, r_contact=g["Rv"] * math.sin(t), z_contact=g["Rv"] * math.cos(t),
                          r_c=(g["Rv"] + rho) * math.sin(t), z_c=(g["Rv"] + rho) * math.cos(t),
                          d_ring=2 * (g["Rv"] + rho) * math.sin(t), wire=math.pi * 2 * (g["Rv"] + rho) * math.sin(t),
                          groove=2 * rho + g["fill"]))
    g["beads"] = beads
    g["L_band"] = g["Rv"] * math.radians(g["te"] - g["tp"])
    g["gap"] = g["Rv"] * math.radians(180.0 - 2 * g["te"])
    g["area_cm2"] = 2 * math.pi * g["Rv"] ** 2 * (math.cos(math.radians(g["tp"])) - math.cos(math.radians(g["te"]))) / 100
    return g


def arc_pts(cx, cy, r, a0, a1, n=120):
    """points on a circle about (cx, cy), polar angles a0 -> a1 (deg) measured from +z (up), toward +r (right)."""
    a = np.radians(np.linspace(a0, a1, n))
    return np.column_stack([cx + r * np.sin(a), cy + r * np.cos(a)])


def section(S, g, O, sc):
    """view A: the half-section about the axis (r to the right of O), both hemispheres, at scale sc."""
    Rv, Rin, fill = g["Rv"], g["Rin"], g["fill"]
    ax = S.ax
    tr = lambda r, z: (O[0] + sc * r, O[1] + sc * z)
    # the retainer (PEEK) around the vessel up to r 30, the AH seats and the AH envelopes (REF, phantom)
    hub = g["hub"]
    rr = hub["ret_r"] - hub["cpl_t"]
    zz = 46.0
    ax.add_patch(Polygon([tr(0, -zz), tr(rr, -zz), tr(rr, zz), tr(0, zz)], closed=True, fc=PEEK, ec="none", zorder=1))
    ax.add_patch(Wedge(tr(0, 0), sc * (Rv + fill), -90, 90, width=sc * fill, fc=GEL, ec="none", zorder=2))
    for s in (1, -1):
        for b in g["beads"]:
            t = math.radians(b["theta"])
            ax.add_patch(Circle(tr((Rv + b["rho"]) * math.sin(t), s * (Rv + b["rho"]) * math.cos(t)),
                                sc * (b["rho"] + fill), fc=GEL, ec="none", zorder=2))
    ax.add_patch(Wedge(tr(0, 0), sc * Rv, -90, 90, width=sc * (Rv - Rin), fc=GLASS, ec="none", zorder=3))
    ax.add_patch(Wedge(tr(0, 0), sc * Rin, -90, 90, fc="white", ec="none", zorder=3))
    for rad in (Rv, Rin):
        S.line([tr(*p) for p in arc_pts(0, 0, rad, 0, 180)], lw=D.LW_VIS)
    S.line([tr(*p) for p in arc_pts(0, 0, Rv + fill, 0, 180)], lw=D.LW_THIN)
    S.chain(tr(0, -zz - 4), tr(0, zz + 4))
    S.line([tr(rr, -zz), tr(rr, zz)], lw=D.LW_THIN)
    for s in (1, -1):
        a, b_ = sorted((s * hub["ah_z"][0], s * zz))
        S.line([tr(0, a), tr(hub["ah_r"], a), tr(hub["ah_r"], b_)], lw=D.LW_THIN, ls=(0, (6, 1.5, 1, 1.5)))
    # the bands (the foil, drawn 0.4 mm thick at this scale) and the beads, rings B (top) and A (bottom)
    for s, lab in ((1, "B"), (-1, "A")):
        th = np.linspace(g["tp"], g["te"], 80)
        out = [tr((Rv + 0.4) * math.sin(math.radians(t)), s * (Rv + 0.4) * math.cos(math.radians(t))) for t in th]
        inn = [tr(Rv * math.sin(math.radians(t)), s * Rv * math.cos(math.radians(t))) for t in th[::-1]]
        ax.add_patch(Polygon(out + inn, closed=True, fc=CU, ec=INK, lw=0.6, zorder=6))
        for b in g["beads"]:
            t = math.radians(b["theta"])
            ax.add_patch(Circle(tr((Rv + b["rho"]) * math.sin(t), s * (Rv + b["rho"]) * math.cos(t)), sc * b["rho"],
                                fc=CU, ec=INK, lw=0.8, zorder=6))
        tm = math.radians(0.5 * (g["tp"] + g["te"]))
        S.leader(tr((Rv + 0.3) * math.sin(tm), s * (Rv + 0.3) * math.cos(tm)), tr(Rv + 6.5, s * 36.0),
                 f"RING {lab}")
    return tr


def angle_dim(S, O, sc, r_arc, a0, a1, text, s=1):
    """an angular dimension about O from the axis (polar angle 0) to a1 (deg), on radius r_arc (mm, model)."""
    pts = [(O[0] + sc * r_arc * math.sin(math.radians(a)), O[1] + s * sc * r_arc * math.cos(math.radians(a)))
           for a in np.linspace(a0, a1, 60)]
    S.line(pts, lw=D.LW_THIN * 0.8, color=DIMC)
    S.arrow(pts[-1], pts[-2])
    S.arrow(pts[0], pts[1])
    am = math.radians(0.5 * (a0 + a1))
    S.text(O[0] + sc * (r_arc + 1.6) * math.sin(am), O[1] + s * sc * (r_arc + 1.6) * math.cos(am), text, ha="center",
           color=DIMC)


def detail(S, g, b, O, sc, label):
    """a bead on the glass at scale sc, in its own frame: the glass's outer surface horizontal at O's height, the
    bead's centre above its contact point at O."""
    Rv, fill = g["Rv"], g["fill"]
    rho = b["rho"]
    ax = S.ax
    tr = lambda u, v: (O[0] + sc * u, O[1] + sc * v)
    w = 6.0
    ax.add_patch(Rectangle(tr(-w, -1.5), sc * 2 * w, sc * 1.5, fc=GLASS, ec=INK, lw=D.LW_VIS, zorder=2))
    ax.add_patch(Rectangle(tr(-w, 0), sc * 2 * w, sc * (b["groove"] + 1.2), fc=PEEK, ec="none", zorder=1))
    ax.add_patch(Rectangle(tr(-w, 0), sc * 2 * w, sc * fill, fc=GEL, ec="none", zorder=2))
    ax.add_patch(Rectangle(tr(-rho - fill, 0), sc * 2 * (rho + fill), sc * b["groove"], fc=GEL, ec="none", zorder=2))
    S.line([tr(-w, fill), tr(-rho - fill, fill), tr(-rho - fill, b["groove"]), tr(rho + fill, b["groove"]),
            tr(rho + fill, fill), tr(w, fill)], lw=D.LW_VIS)
    side = -1 if b["name"] == "polar" else 1                         # the foil runs toward the equator from the polar
    x_f0, x_f1 = (0, w) if side < 0 else (-w, 0)                      # bead, toward the pole from the equatorial one
    ax.add_patch(Rectangle(tr(x_f0, 0), sc * (x_f1 - x_f0), sc * g["foil"], fc=CU, ec=INK, lw=0.6, zorder=4))
    ax.add_patch(Circle(tr(0, rho), sc * rho, fc=CU, ec=INK, lw=D.LW_VIS, zorder=5))
    S.dim(tr(-rho, rho), tr(rho, rho), (0, sc * (rho + 1.8)), f"Ø{2 * rho:g} wire")
    S.dim(tr(rho + fill, 0), tr(rho + fill, b["groove"]), (sc * 2.6, 0), f"{b['groove']:.1f}")
    S.dim(tr(-w + 0.6, 0), tr(-w + 0.6, fill), (-sc * 1.2, 0), f"{fill:g}", outside=True)
    S.text(tr(-w, -1.5)[0], tr(0, -1.5)[1] - 4.5, "glass 1.5", color=INK)
    S.text(tr(w, 0)[0], tr(0, -1.5)[1] - 4.5, "foil 0.1, soldered to the bead", ha="right", color=INK)
    S.text(O[0], O[1] + sc * (b["groove"] + 1.2) + 9.0, label, ha="center", weight="bold")


def gore(S, g, O, sc):
    """view D: one gore of a band, flat: its centre line along the meridian (the arc length from the polar to the
    equatorial edge), its width the latitude's circumference over GORES, plus the overlap on one side."""
    Rv = g["Rv"]
    s = np.linspace(0, g["L_band"], 60)
    th = np.radians(g["tp"]) + s / Rv
    w = 2 * math.pi * Rv * np.sin(th) / GORES
    left = [(O[0] - sc * 0.5 * wi, O[1] + sc * si) for si, wi in zip(s, w)]
    right = [(O[0] + sc * (0.5 * wi + OVERLAP), O[1] + sc * si) for si, wi in zip(s, w)]
    S.ax.add_patch(Polygon(left + right[::-1], closed=True, fc="#f5e3d3", ec=INK, lw=D.LW_VIS, zorder=3))
    S.line([(O[0] + sc * 0.5 * wi, O[1] + sc * si) for si, wi in zip(s, w)], lw=D.LW_THIN, ls=(0, (3, 1.5)))
    S.chain((O[0], O[1] - 4), (O[0], O[1] + sc * g["L_band"] + 4))
    S.dim((O[0] - sc * 0.5 * w[0], O[1]), (O[0] + sc * 0.5 * w[0], O[1]), (0, -9), f"{w[0]:.2f}")
    S.dim((O[0] - sc * 0.5 * w[-1], O[1] + sc * g["L_band"]), (O[0] + sc * 0.5 * w[-1], O[1] + sc * g["L_band"]),
          (0, 8), f"{w[-1]:.2f}")
    S.dim((O[0] - sc * 0.5 * w[-1] - 4, O[1]), (O[0] - sc * 0.5 * w[-1] - 4, O[1] + sc * g["L_band"]), (-6, 0),
          f"{g['L_band']:.2f} (arc)")
    j = int(round(0.55 * (len(s) - 1)))                                # the overlap, dimensioned where it is
    ym, x1, x2 = O[1] + sc * s[j], O[0] + sc * 0.5 * w[j], O[0] + sc * (0.5 * w[j] + OVERLAP)
    S.dim((x1, ym), (x2, ym), (0, 0), "", outside=True)
    S.text(x2 + 7.5, ym - 1.0, f"{OVERLAP:g} overlap", color=DIMC)
    S.text(O[0], O[1] - 22, f"D  GORE, FLAT (4:1): {GORES} per band, {2 * GORES} in all", ha="center", weight="bold")
    S.text(O[0], O[1] - 27, "width = 2π·25·sin θ / 12 along the arc; the edge θ at the narrow end", ha="center",
           size=6.6)


def main():
    g = geom()
    rec = g["rec"]
    S = D.Sheet()
    ax = S.ax
    ax.add_patch(Rectangle((10, 10), 400, 277, fill=False, ec=INK, lw=1.4, zorder=2))
    # A: the section, 2:1
    sc = 2.0
    O = (68.0, 150.0)
    section(S, g, O, sc)
    for s, lab in ((1, "B"), (-1, "A")):
        angle_dim(S, O, sc, 38.0, 0.0, g["tp"], f"{g['tp']:.2f}°", s=s)
        angle_dim(S, O, sc, 44.0, 0.0, g["te"], f"{g['te']:.2f}°", s=s)
    # the gap along the glass across the equator, and the bead rings' centre-line diameters
    te = math.radians(g["te"])
    pts = [(O[0] + sc * (g["Rv"] + 3.0) * math.sin(a), O[1] + sc * (g["Rv"] + 3.0) * math.cos(a))
           for a in np.linspace(te, math.pi - te, 40)]
    S.line(pts, lw=D.LW_THIN * 0.8, color=DIMC); S.arrow(pts[0], pts[1]); S.arrow(pts[-1], pts[-2])
    S.text(O[0] + sc * (g["Rv"] + 4.2), O[1] - 1.0, f"{g['gap']:.2f} along the glass", color=DIMC)
    S.text(O[0] + sc * (g["Rv"] + 4.2), O[1] - 6.0, f"({rec['V_gap_kV']:.1f} kV: {rec['V_gap_kV'] / g['gap']:.2f} kV/mm)",
           color=DIMC, size=6.6)
    for b in g["beads"]:
        y = O[1] + sc * b["z_c"]
        S.dim((O[0], y), (O[0] + sc * b["r_c"], y), (0, sc * (2.2 if b["name"] == "polar" else -1.6)),
              f"R{b['r_c']:.2f} (Ø{b['d_ring']:.2f})", txt_off=0.8)
    S.text(O[0] + sc * 3, O[1] + sc * 1.5, "vacuum", color=INK, size=6.6)
    S.text(O[0] + sc * 15.5, O[1] - sc * 43.0, "PEEK retainer", color=INK, size=6.6)
    S.text(O[0] - sc * 21.0, O[1] + sc * 42.0, "AH (REF), phantom", color=INK, size=6.6)
    S.leader((O[0] + sc * 5.0, O[1] + sc * 40.0), (O[0] - sc * 6.0, O[1] + sc * 44.0), "", arrow=True)
    S.text(O[0] - 48, O[1] + sc * 54, "A  HALF-SECTION ON THE AXIS (2:1)", weight="bold")
    S.text(O[0] - 48, O[1] + sc * 54 - 5, "rings A and B mirror the equator; angles from the axis", size=6.6)
    # B, C: the beads at 5:1
    detail(S, g, g["beads"][0], (212.0, 242.0), 5.0, f"B  POLAR BEAD, Ø{2 * g['rp']:g} (5:1)")
    detail(S, g, g["beads"][1], (212.0, 196.0), 5.0, f"C  EQUATORIAL BEAD, Ø{2 * g['rq']:g} (5:1)")
    # D: the gore
    gore(S, g, (345.0, 205.0), 4.0)
    # the feature table
    x0, y0 = 162.0, 166.0
    hdr = ("feature (each ring)", "polar edge", "equatorial edge")
    rows = [("edge angle from the axis", f"{g['tp']:.2f}°", f"{g['te']:.2f}°")]
    for key, fmt in (("r_contact", "r {:.2f} / z ±{:.2f}"),):
        rows.append(("bead's contact on the glass", fmt.format(g["beads"][0]["r_contact"], g["beads"][0]["z_contact"]),
                     fmt.format(g["beads"][1]["r_contact"], g["beads"][1]["z_contact"])))
    rows += [("bead's centre", f"r {g['beads'][0]['r_c']:.2f} / z ±{g['beads'][0]['z_c']:.2f}",
              f"r {g['beads'][1]['r_c']:.2f} / z ±{g['beads'][1]['z_c']:.2f}"),
             ("bead: Cu wire, ring centre-line", f"Ø{2 * g['rp']:g} wire, Ø{g['beads'][0]['d_ring']:.2f}",
              f"Ø{2 * g['rq']:g} wire, Ø{g['beads'][1]['d_ring']:.2f}"),
             ("wire per ring (cut, close, solder)", f"{g['beads'][0]['wire']:.1f}", f"{g['beads'][1]['wire']:.1f}"),
             ("groove in the PEEK (depth)", f"{g['beads'][0]['groove']:.1f}", f"{g['beads'][1]['groove']:.1f}"),
             ("peak field in the gel (record)", f"{rec['E_pol']['gel']:.2f} kV/mm", f"{rec['E_eq']['gel']:.2f} kV/mm")]
    cw = (66.0, 46.0, 46.0)
    S.ax.add_patch(Rectangle((x0, y0 - 6.0 * len(rows) - 3), sum(cw), 6.0 * len(rows) + 9, fill=False, ec=INK,
                             lw=0.8, zorder=2))
    xx = x0
    for c, w_ in zip(hdr, cw):
        S.text(xx + 1.5, y0 + 1.5, c, weight="bold", size=6.8)
        xx += w_
    for i, rw in enumerate(rows):
        xx = x0
        for c, w_ in zip(rw, cw):
            S.text(xx + 1.5, y0 - 6.0 * (i + 1) + 1.5, c, size=6.8)
            xx += w_
    S.text(x0, y0 + 8, f"RINGS A AND B: band {g['L_band']:.2f} along the glass, {g['area_cm2']:.1f} cm² each; the gap "
                       f"{g['gap']:.2f}", weight="bold", size=7.0)
    # notes
    notes = [
        "NOTES",
        "1. Material: foil Cu-ETP (CW004A), annealed, 0.10 thick; bead rings Cu-ETP wire. Glass: the vessel as supplied",
        "   (borosilicate, OD 50, wall 1.5), clean and degreased.",
        f"2. Cut {GORES} gores per band (D); burnish onto the glass from the polar edge, each overlapping its neighbour by",
        f"   {OVERLAP:g}; solder the overlaps flat. No adhesive film under the foil: the gel bonds and fills it.",
        "3. Close each bead ring by a butt solder joint, filed round; solder it along the foil's edge, centred on the edge",
        "   angle (A), touching the glass. Smooth every joint: no point or burr above the bead's radius.",
        "4. The leads: PTFE-insulated HV wire soldered to the equatorial bead, out through the PEEK and the G10 coupler.",
        "5. The PEEK retainer: unfilled, annealed stock; the pocket 0.5 over the glass and the grooves (B, C) machined to",
        "   size; degassed silicone gel vacuum-cast into the pocket and the grooves, void-free.",
        "6. Ring A is ring B mirrored in the equator. Test before potting: continuity; after: hold-off per",
        "   docs/bench-test-rings.md phase 1 (c).",
    ]
    for i, s_ in enumerate(notes):
        S.text(162.0, 114.0 - 3.8 * i, s_, size=6.6, weight="bold" if i == 0 else "normal")
    # the title block
    x0, y0, w, h = 230.0, 10.0, 180.0, 50.0
    S.ax.add_patch(Rectangle((x0, y0), w, h, fill=False, ec=INK, lw=1.2, zorder=2))
    for yy in (y0 + 40, y0 + 30, y0 + 20, y0 + 10):
        S.line([(x0, yy), (x0 + w, yy)], lw=0.6)
    S.line([(x0 + 120, y0), (x0 + 120, y0 + 40)], lw=0.6)
    S.text(x0 + 3, y0 + 43.5, "DCCREG turbine   ·   the hub: the field's rings on the vessel", size=8.2)
    S.text(x0 + 3, y0 + 33.0, "RINGS A AND B, COPPER, BEADED", size=10.5, weight="bold")
    S.text(x0 + 3, y0 + 23.0, "Cu-ETP foil 0.10 + wire; in gel under PEEK", size=TXT)
    S.text(x0 + 3, y0 + 13.0, "Scale: 2:1 (A), 5:1 (B, C), 4:1 (D)   Units: mm", size=TXT)
    S.text(x0 + 3, y0 + 3.0, "Drawn: generated from sim/hub_rings_build.py", size=6.6)
    S.text(x0 + 123, y0 + 33.0, "Drawing no.", size=6.6)
    S.text(x0 + 123, y0 + 23.4, DWG, size=12, weight="bold")
    S.text(x0 + 123, y0 + 13.0, "Rev A (draft)  Sheet 1/1  A3", size=TXT)
    S.text(x0 + 123, y0 + 3.0, "Date: 2026-10-09", size=TXT)
    os.makedirs(OUT, exist_ok=True)
    pdf = os.path.join(OUT, f"{DWG}.pdf")
    S.fig.savefig(pdf)
    S.fig.savefig(os.path.join(OUT, f"{DWG}.png"), dpi=160)
    plt.close(S.fig)
    print(json.dumps(dict(pdf=os.path.relpath(pdf, ROOT), beads=g["beads"], L_band=g["L_band"], gap=g["gap"]),
                     default=float))


if __name__ == "__main__":
    main()
