#!/usr/bin/env python3
"""docs/make_drawing_set.py -- the drawing set of the machine as the layout proposes it: a drawing with a small 3-D
view for every part, a source-control sheet for every bought part, and the sub-assemblies with their parts lists and
balloons. The design's own parts are the record's; the layout, the bridge-ring bearings and the capacitors' mounts
are PROPOSED.

Every sheet is drawn from the solids of sim/tube_geometry.py LayoutMachine (with the bridge-ring bearings and the
capacitors' mounts, sim/doubler_caps.py): the views are hidden-line projections and exact sections of the part's own
B-rep (OCP HLR, as docs/make_core_drawing.py), the diameters, lengths and hole patterns are read off its faces, and the
masses and quantities are counted from the model. The numbers in the notes cite the study that holds them.
  * a made part: its views (a section, an end or plan view, a detail where a feature is small), its dimensions,
    material, mass, quantity, finish and notes, and a small shaded 3-D view (three.js in headless Chromium,
    tools/step-viewer/part.html);
  * a bought part: its envelope as the model draws it, the specification it must meet, a candidate part number with
    its source, and the notes to verify before ordering;
  * a sub-assembly: an exact section of its parts as placed, balloons, a parts list, assembly notes, its 3-D view;
    deck A's sheet carries its wiring list (each lead, strap and wire with its net);
  * the general arrangement, and the index of the set.
DCCREG-UTR-101 (the half-core) and DCCREG-HUB-201 (the rings) are drawn by their own scripts and go into the set as
they are.
Writes docs/drawings/set/<DWG>.pdf, a PDF per sheet, and docs/drawings/set-index.json, the set in order; the ledger's
drawings bundle carries the set as its Part D (docs/ledger/register.py reads the index). With --merge OUT, the whole
set as one PDF with a bookmark per sheet (needs pypdf); with --preview DIR, a PNG of every sheet in DIR.
Usage: python3 docs/make_drawing_set.py [--only DWG ...] [--preview DIR] [--no-3d] [--merge OUT]   (about four
minutes; OCP, Chromium and tools/step-viewer's node_modules for the 3-D views)
"""
import argparse
import collections
import functools
import http.server
import json
import math
import os
import socketserver
import sys
import tempfile
import textwrap
import threading
import time

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt                                              # noqa: E402
from matplotlib.patches import Rectangle, Circle, PathPatch, Arc             # noqa: E402
from matplotlib.path import Path                                             # noqa: E402
import numpy as np                                                           # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path[:0] = [HERE, os.path.join(ROOT, "sim")]
import make_core_drawing as D                                               # noqa: E402  (the A3 sheet, its primitives, HLR)

DATE = "2026-10-11"
OUT_DIR = os.path.join(HERE, "drawings")
INDEX_JSON = os.path.join(OUT_DIR, "set-index.json")
INK, DIMC, TXT = D.INK, D.DIMC, D.TXT
LW_VIS, LW_THIN = D.LW_VIS, D.LW_THIN
STATUS_COL = {"LOCKED": "#1f3d66", "PROPOSED": "#9a3412", "BOUGHT": "#365314", "RECORD": "#1f3d66"}
SCALES = (10.0, 5.0, 2.0, 1.0, 0.5, 0.2, 0.1, 0.05)
plt.rcParams["hatch.linewidth"] = 0.35
plt.rcParams["hatch.color"] = "#444444"


def scale_txt(s):
    return f"{s:g}:1" if s >= 1 else f"1:{1 / s:g}"


def fit_scale(w, h, box_w, box_h):
    for s in SCALES:
        if w * s <= box_w and h * s <= box_h:
            return s
    return SCALES[-1]


# ---------------------------------------------------------------------------------------------------------
# the model, shapes and their features
# ---------------------------------------------------------------------------------------------------------
class Model:
    """the layout's solids (sim/tube_geometry.py LayoutMachine, mounts and bridge-ring bearings in)."""

    def __init__(self):
        import tube_geometry as TG
        self.TG = TG
        self.m = TG.LayoutMachine().build()
        self.by_name = {p["name"]: p for p in self.m.parts}
        self.count = collections.Counter(p["proto"] for p in self.m.parts)
        self._placed = {}

    def proto(self, key):
        return self.m.protos[key][0]

    def colour(self, key):
        return self.m.protos[key][1]

    def material(self, key):
        return self.m.protos[key][2]

    def placed(self, name):
        if name not in self._placed:
            self._placed[name] = self.m.placed(self.by_name[name])
        return self._placed[name]

    def names(self, pred):
        return [p["name"] for p in self.m.parts if pred(p)]


class SubModel(Model):
    """a sub-assembly outside the layout (sim/unmodelled_parts.py Sub: the drive, the choke, the kick) behind the
    layout Model's interface; its assembly views draw the gears with their teeth."""

    def __init__(self, sub):
        self.m = sub
        self.by_name = {p["name"]: p for p in sub.parts}
        self.count = collections.Counter(p["proto"] for p in sub.parts)
        self._placed = {}

    def placed(self, name):
        if name not in self._placed:
            self._placed[name] = self.m.placed(self.by_name[name], True)
        return self._placed[name]


_SUBS = {}


def sub(key):
    """the unmodelled parts' sub-assemblies (sim/unmodelled_parts.py), built once."""
    import unmodelled_parts as U
    if key not in _SUBS:
        _SUBS[key] = dict(reverser=U.reverser_sub, belt=U.belt_sub, choke=U.choke_sub, kick=U.kick_sub)[key]()
    return _SUBS[key]


def bbox(shape):
    from OCP.Bnd import Bnd_Box
    from OCP.BRepBndLib import BRepBndLib
    b = Bnd_Box(); BRepBndLib.Add_s(shape, b)
    p, q = b.CornerMin(), b.CornerMax()
    return np.array([p.X(), p.Y(), p.Z()]), np.array([q.X(), q.Y(), q.Z()])


def tight_bbox(shape):
    """the bounding box from a fine mesh (OCC's box carries a tolerance gap)."""
    import motor_geometry as MG
    P = MG.mesh_points(shape, 0.05)
    return P.min(axis=0), P.max(axis=0)


def moved(shape, dx=0.0, dy=0.0, dz=0.0):
    from OCP.gp import gp_Trsf, gp_Vec
    from OCP.BRepBuilderAPI import BRepBuilderAPI_Transform
    t = gp_Trsf(); t.SetTranslation(gp_Vec(dx, dy, dz))
    return BRepBuilderAPI_Transform(shape, t, True).Shape()


def rotated(shape, axis, deg, centre=(0.0, 0.0, 0.0)):
    from OCP.gp import gp_Trsf, gp_Ax1, gp_Pnt, gp_Dir
    from OCP.BRepBuilderAPI import BRepBuilderAPI_Transform
    t = gp_Trsf(); t.SetRotation(gp_Ax1(gp_Pnt(*centre), gp_Dir(*axis)), math.radians(deg))
    return BRepBuilderAPI_Transform(shape, t, True).Shape()


def compound(shapes):
    from OCP.BRep import BRep_Builder
    from OCP.TopoDS import TopoDS_Compound
    b, c = BRep_Builder(), TopoDS_Compound()
    b.MakeCompound(c)
    for s in shapes:
        b.Add(c, s)
    return c


def volume(shape):
    from OCP.BRepGProp import BRepGProp
    from OCP.GProp import GProp_GProps
    g = GProp_GProps(); BRepGProp.VolumeProperties_s(shape, g)
    return g.Mass()


def density(mat):
    import bridge_ring_bearings as BRB
    import shaft_bearings as SB
    for k, v in BRB.RHO_LAYOUT:
        if k in mat:
            return v
    try:
        return SB._density(mat)
    except KeyError:
        return None


def features(shape):
    """the faces a drawing dimensions: coaxial cylinders (the machine axis z through the origin), axial holes and
    bosses off the axis, radial holes, cones (countersinks), planes normal to z. Each cylinder knows whether the
    material lies outside it (a bore or hole) or inside (a surface or boss) from its outward normal."""
    from OCP.TopExp import TopExp_Explorer
    from OCP.TopAbs import TopAbs_FACE
    from OCP.TopoDS import TopoDS
    from OCP.BRepAdaptor import BRepAdaptor_Surface
    from OCP.GeomAbs import GeomAbs_Cylinder, GeomAbs_Cone, GeomAbs_Plane
    from OCP.BRepGProp import BRepGProp_Face
    from OCP.gp import gp_Pnt, gp_Vec
    out = dict(coax=[], axial=[], radial=[], cones=[], zplanes=[])
    e = TopExp_Explorer(shape, TopAbs_FACE)
    while e.More():
        f = TopoDS.Face(e.Current())
        s = BRepAdaptor_Surface(f)
        t = s.GetType()
        lo, hi = bbox(f)
        u, v = 0.5 * (s.FirstUParameter() + s.LastUParameter()), 0.5 * (s.FirstVParameter() + s.LastVParameter())
        p, n = gp_Pnt(), gp_Vec()
        BRepGProp_Face(f).Normal(u, v, p, n)
        P, N = np.array([p.X(), p.Y(), p.Z()]), np.array([n.X(), n.Y(), n.Z()])
        if np.linalg.norm(N) > 0:
            N = N / np.linalg.norm(N)
        if t == GeomAbs_Cylinder:
            c = s.Cylinder()
            ax, loc = c.Axis().Direction(), c.Axis().Location()
            d = np.array([ax.X(), ax.Y(), ax.Z()]); L = np.array([loc.X(), loc.Y(), loc.Z()])
            radial = (P - L) - np.dot(P - L, d) * d
            hole = bool(np.dot(radial, N) < 0)                     # the outward normal points at the axis: a bore
            q = dict(r=c.Radius(), d=d, loc=L, lo=lo, hi=hi, hole=hole)
            if abs(abs(d[2]) - 1.0) < 1e-6:
                q["c"] = (float(L[0]), float(L[1]))
                if math.hypot(*q["c"]) < 1e-4:
                    out["coax"].append(q)
                else:
                    out["axial"].append(q)
            elif abs(d[2]) < 1e-6:
                out["radial"].append(q)
        elif t == GeomAbs_Cone:
            c = s.Cone()
            ax, loc = c.Axis().Direction(), c.Axis().Location()
            out["cones"].append(dict(d=np.array([ax.X(), ax.Y(), ax.Z()]), c=(loc.X(), loc.Y()), lo=lo, hi=hi,
                                     r_max=max(math.hypot(lo[0] - loc.X(), 0), 0)))
        elif t == GeomAbs_Plane:
            if abs(abs(N[2]) - 1.0) < 1e-6:
                out["zplanes"].append(dict(z=float(P[2]), lo=lo, hi=hi, up=bool(N[2] > 0)))
        e.Next()
    return out


def coax_groups(F, tol=0.02):
    """the coaxial cylinders merged by radius and kind: [(r, hole, z0, z1)], radius ascending."""
    g = {}
    for q in F["coax"]:
        k = (round(q["r"] / tol), q["hole"])
        z0, z1 = q["lo"][2], q["hi"][2]
        if k in g:
            r_, a, b = g[k]
            g[k] = (r_, min(a, z0), max(b, z1))
        else:
            g[k] = (float(q["r"]), z0, z1)
    return sorted([(r_, h, a, b) for (_, h), (r_, a, b) in g.items()], key=lambda x: (x[0], x[1]))


def hole_groups(F, tol=0.02):
    """the axial holes (and bosses) off the axis, grouped by diameter, pitch circle and depth: [dict(d, pcd, n,
    angles, z0, z1, hole)], pitch circle ascending."""
    g, val = {}, {}
    for q in F["axial"]:
        r_p = math.hypot(*q["c"])
        k = (round(2 * q["r"] / tol), round(2 * r_p / 0.05), q["hole"], round(q["lo"][2], 2), round(q["hi"][2], 2))
        a = math.degrees(math.atan2(q["c"][1], q["c"][0]))
        g.setdefault(k, set()).add(round(a, 2))
        val.setdefault(k, (2.0 * float(q["r"]), 2.0 * r_p, float(q["lo"][2]), float(q["hi"][2])))
    out = [dict(d=val[k][0], pcd=val[k][1], n=len(angs), angles=sorted(angs), z0=val[k][2], z1=val[k][3], hole=k[2])
           for k, angs in g.items()]
    return sorted(out, key=lambda h: (h["pcd"], h["d"]))


def cones_at(F, holes):
    """mark each hole group countersunk when a cone sits on its axis; returns {index: (D_top, face z)}."""
    marks = {}
    for i, h in enumerate(holes):
        for c in F["cones"]:
            r_p = math.hypot(*c["c"])
            a = math.degrees(math.atan2(c["c"][1], c["c"][0]))
            on_axis = r_p < 1e-3 or any(abs((a - b + 180.0) % 360.0 - 180.0) < 0.5 for b in h["angles"])
            if abs(r_p * 2 - h["pcd"]) < 0.2 and on_axis:
                D_top = 2 * max(abs(c["hi"][0] - c["c"][0]), abs(c["lo"][0] - c["c"][0]),
                                abs(c["hi"][1] - c["c"][1]), abs(c["lo"][1] - c["c"][1]))
                face = c["hi"][2] if c["hi"][2] > h["z1"] - 1e-3 else c["lo"][2]     # the cone's wide end
                marks.setdefault(i, (round(min(D_top, 2 * (c["hi"][0] - c["lo"][0])), 2), face))
    return marks


# ---------------------------------------------------------------------------------------------------------
# views
# ---------------------------------------------------------------------------------------------------------
VIEW_DIR = {"top": ((0, 0, 1), (1, 0, 0)), "front": ((0, -1, 0), (1, 0, 0)), "side": ((1, 0, 0), (0, 1, 0)),
            "bottom": ((0, 0, -1), (1, 0, 0)), "back": ((0, 1, 0), (-1, 0, 0))}


def hlr(shape, view):
    d, xd = VIEW_DIR[view]
    return D.hlr(shape, d, xd)


def edges_box(E, keys=("vis",)):
    P = [p for k in keys for p in E[k]]
    if not P:
        return np.zeros(2), np.zeros(2)
    A = np.vstack(P)
    return A.min(axis=0), A.max(axis=0)


def section_y0(shape):
    """the exact section through y = 0 (a plane through the axis): the cut's triangles and outline in (x, z), and
    the visible edges of the half behind the plane (y >= 0, seen from -y)."""
    import tube_geometry as TG
    from OCP.BRepAlgoAPI import BRepAlgoAPI_Common
    lo, hi = bbox(shape)
    big = 10.0 + float(np.max(hi - lo))
    half_box = TG.box(lo[0] - big, hi[0] + big, 0.0, hi[1] + big, lo[2] - big, hi[2] + big)
    half = BRepAlgoAPI_Common(shape, half_box).Shape()
    tris = TG.section_faces(shape, ("y", 0.0))
    outline = TG.cut_polylines(shape, ("y", 0.0))
    E = D.hlr(half, (0, -1, 0), (1, 0, 0)) if tris else dict(vis=[], hid=[])
    return dict(tris=tris, outline=outline, edges=E)


def tri_path(tris, tr):
    v, c = [], []
    for t in tris:
        P = [tr(np.asarray(p, float)) for p in t]
        v += [P[0], P[1], P[2], P[0]]
        c += [Path.MOVETO, Path.LINETO, Path.LINETO, Path.CLOSEPOLY]
    return Path(v, c) if v else None


class Sheet(D.Sheet):
    """the A3 sheet of docs/make_core_drawing.py with the drawing set's furniture and helpers."""

    def map(self, origin, scale, rot=None):
        o = np.asarray(origin, float)
        R = None if rot is None else np.asarray(rot, float)

        def tr(P):
            P = np.asarray(P, float)
            if R is not None:
                P = P @ R.T
            return o + scale * P
        return tr

    def edges(self, E, tr, hidden=True, lw=LW_VIS, color=INK, clip=None):
        for P in E["vis"]:
            Q = tr(P)
            ln, = self.ax.plot(Q[:, 0], Q[:, 1], color=color, lw=lw, solid_capstyle="round", zorder=3)
            if clip is not None:
                ln.set_clip_path(clip)
        if hidden:
            for P in E["hid"]:
                Q = tr(P)
                ln, = self.ax.plot(Q[:, 0], Q[:, 1], color=color, lw=D.LW_HID * 0.75, ls=(0, (3.0, 1.6)), zorder=3)
                if clip is not None:
                    ln.set_clip_path(clip)

    def hatch(self, tris, tr, fc="#f4f3ef", hatch="////", clip=None, z=2):
        p = tri_path(tris, tr)
        if p is None:
            return
        patch = PathPatch(p, fc=fc, ec="none", hatch=hatch, lw=0, zorder=z)
        self.ax.add_patch(patch)
        if clip is not None:
            patch.set_clip_path(clip)

    def lines(self, polys, tr, lw=LW_VIS, color=INK, clip=None, z=4):
        for P in polys:
            Q = tr(P)
            ln, = self.ax.plot(Q[:, 0], Q[:, 1], color=color, lw=lw, solid_capstyle="round", zorder=z)
            if clip is not None:
                ln.set_clip_path(clip)

    def hdim(self, x1, x2, y_line, y1, y2, text, color=DIMC, txt_side=1):
        """a horizontal dimension: extension lines from (x1, y1) and (x2, y2) to the line at y_line."""
        for x, y in ((x1, y1), (x2, y2)):
            if abs(y_line - y) > 0.8:
                s = 1 if y_line > y else -1
                self.line([(x, y + s * 0.8), (x, y_line + s * 1.6)], lw=LW_THIN * 0.8, color=color)
        small = abs(x2 - x1) < 9.0
        if small:
            a, b = min(x1, x2), max(x1, x2)
            self.line([(a - 7, y_line), (b + 7, y_line)], lw=LW_THIN * 0.8, color=color)
            self.arrow((a, y_line), (a - 1, y_line)); self.arrow((b, y_line), (b + 1, y_line))
        else:
            self.line([(x1, y_line), (x2, y_line)], lw=LW_THIN * 0.8, color=color)
            self.arrow((x1, y_line), (x2, y_line)); self.arrow((x2, y_line), (x1, y_line))
        xm = 0.5 * (x1 + x2) + (0.0 if not small else 0.0)
        self.text(xm, y_line + (1.0 if txt_side > 0 else -3.6), text, ha="center", color=color, size=TXT * 0.95)

    def vdim(self, y1, y2, x_line, x1, x2, text, color=DIMC):
        """a vertical dimension: extension lines from (x1, y1), (x2, y2) to the line at x_line; text along it."""
        for x, y in ((x1, y1), (x2, y2)):
            if abs(x_line - x) > 0.8:
                s = 1 if x_line > x else -1
                self.line([(x + s * 0.8, y), (x_line + s * 1.6, y)], lw=LW_THIN * 0.8, color=color)
        small = abs(y2 - y1) < 9.0
        a, b = min(y1, y2), max(y1, y2)
        if small:
            self.line([(x_line, a - 7), (x_line, b + 7)], lw=LW_THIN * 0.8, color=color)
            self.arrow((x_line, a), (x_line, a - 1)); self.arrow((x_line, b), (x_line, b + 1))
        else:
            self.line([(x_line, a), (x_line, b)], lw=LW_THIN * 0.8, color=color)
            self.arrow((x_line, a), (x_line, b)); self.arrow((x_line, b), (x_line, a))
        self.ax.text(x_line - 1.0, 0.5 * (a + b), text, fontsize=TXT * 0.95, ha="center", va="bottom", rotation=90,
                     color=color, zorder=5, family="DejaVu Sans", rotation_mode="anchor")

    def callout(self, tip, text, toward, color=DIMC):
        """a leader from tip outward along the direction toward (unit), then a shoulder and the text."""
        tip = np.asarray(tip, float); d = np.asarray(toward, float)
        d = d / (np.linalg.norm(d) or 1.0)
        knee = tip + d * 9.0
        ha = "left" if d[0] >= 0 else "right"
        self.leader(tip, knee, text, color=color, ha=ha)

    def adim(self, c, r, a0, a1, text, color=DIMC):
        """an angular dimension: an arc of radius r (sheet mm) about c from a0 to a1 (deg), arrows at both ends."""
        c = np.asarray(c, float)
        self.ax.add_patch(Arc(c, 2 * r, 2 * r, theta1=min(a0, a1), theta2=max(a0, a1), ec=color, lw=LW_THIN * 0.8, zorder=4))
        for a, s in ((a0, 1), (a1, -1)):
            t = math.radians(a)
            p = c + r * np.array([math.cos(t), math.sin(t)])
            tang = np.array([-math.sin(t), math.cos(t)]) * (s if a1 > a0 else -s)
            self.arrow(p, p + tang)
        am = math.radians(0.5 * (a0 + a1))
        q = c + (r + 2.2) * np.array([math.cos(am), math.sin(am)])
        self.text(q[0], q[1], text, ha="center", va="center", color=color, size=TXT * 0.9)

    def centre_mark(self, c, size=3.0):
        c = np.asarray(c, float)
        self.chain(c - [size, 0], c + [size, 0]); self.chain(c - [0, size], c + [0, size])

    def title(self, x, y, s):
        self.text(x, y, s, size=9.0, weight="bold")


def wrap(s, width):
    out = []
    for para in s.split("\n"):
        out += textwrap.wrap(para, width, subsequent_indent="    ") or [""]
    return out


def furniture(S, e, mass_kg, qty, scale_s, sheet_no, n_sheets):
    """the frame, the title block, the revision table."""
    ax = S.ax
    ax.add_patch(Rectangle((20, 10), 390, 277, fill=False, ec=INK, lw=1.6, zorder=2))
    ax.add_patch(Rectangle((5, 5), 410, 287, fill=False, ec=INK, lw=0.4, zorder=2))
    # revision table
    rx, ry = 300.0, 268.0
    ax.add_patch(Rectangle((rx, ry), 110, 19, fill=False, ec=INK, lw=LW_THIN, zorder=2))
    S.line([(rx, ry + 12.5), (rx + 110, ry + 12.5)], lw=0.5); S.line([(rx, ry + 6.3), (rx + 110, ry + 6.3)], lw=0.5)
    S.line([(rx + 12, ry), (rx + 12, ry + 12.5)], lw=0.5); S.line([(rx + 34, ry), (rx + 34, ry + 12.5)], lw=0.5)
    S.text(rx + 2, ry + 14.4, "REVISIONS", size=TXT, weight="bold")
    S.text(rx + 2, ry + 8.2, "Rev", size=TXT); S.text(rx + 14, ry + 8.2, "Date", size=TXT); S.text(rx + 36, ry + 8.2, "Description", size=TXT)
    S.text(rx + 2, ry + 2.0, "A", size=TXT); S.text(rx + 14, ry + 2.0, DATE, size=TXT)
    S.text(rx + 36, ry + 2.0, e.get("rev_text", "First issue, draft for quotation"), size=TXT * 0.92)
    # title block
    x0, y0, w, h = 230.0, 10.0, 180.0, 58.0
    ax.add_patch(Rectangle((x0, y0), w, h, fill=False, ec=INK, lw=1.2, zorder=2))
    for yy in (y0 + 46, y0 + 36, y0 + 26, y0 + 16, y0 + 8):
        S.line([(x0, yy), (x0 + w, yy)], lw=0.6)
    S.line([(x0 + 120, y0), (x0 + 120, y0 + 46)], lw=0.6)
    S.line([(x0 + 60, y0), (x0 + 60, y0 + 26)], lw=0.6)
    S.text(x0 + 3, y0 + 50.5, f"DCCREG turbine   ·   {e['system']}", size=8.0)
    title = e["title"]
    S.text(x0 + 3, y0 + 39.0, title, size=10.5 if len(title) <= 44 else (9.0 if len(title) <= 54 else 7.8), weight="bold")
    mat = e.get("material_text") or e.get("material") or ""
    S.text(x0 + 3, y0 + 29.0, ("Material: " + mat)[:84], size=TXT if len(mat) < 70 else 6.4)
    S.text(x0 + 3, y0 + 19.0, f"Mass: {mass_kg:.3g} kg" if mass_kg else "Mass: —", size=TXT)
    S.text(x0 + 63, y0 + 19.0, f"Qty per machine: {qty}" if qty else "Qty per machine: —", size=TXT)
    S.text(x0 + 3, y0 + 10.6, f"Scale: {scale_s}", size=TXT)
    S.text(x0 + 63, y0 + 10.6, e.get("tol", "Tolerances: ISO 2768-mK"), size=TXT * 0.95)
    S.text(x0 + 3, y0 + 2.6, "Drawn: generated by docs/make_drawing_set.py", size=6.4)
    S.text(x0 + 63, y0 + 2.6, "Checked: —      Approved: —", size=6.6)
    S.text(x0 + 123, y0 + 39.0, "Drawing no.", size=6.6)
    S.text(x0 + 123, y0 + 29.4, e["dwg"], size=11.0 if len(e["dwg"]) <= 14 else 9.5, weight="bold")
    S.text(x0 + 123, y0 + 19.0, f"Rev A   Sheet {sheet_no} of {n_sheets}   A3", size=TXT)
    S.text(x0 + 123, y0 + 10.6, f"Date: {DATE}", size=TXT)
    st = e.get("status", "LOCKED")
    lab = {"LOCKED": "LOCKED DESIGN · DRAFT", "PROPOSED": "PROPOSED · DRAFT", "BOUGHT": "BOUGHT · SOURCE CONTROL",
           "RECORD": "THE RECORD · DRAFT"}.get(st, st)
    S.text(x0 + 123, y0 + 2.6, lab, size=7.4, weight="bold", color=STATUS_COL.get(st, INK))


def notes_block(S, notes, x=24.0, y_top=108.0, width_mm=202.0, size=TXT * 0.95, max_lines=22, bottom=14.0):
    """the notes, numbered and wrapped to the block's width; returns the lines it could not place."""
    cw = 0.62 * size * 0.3528                                           # mm per character, DejaVu Sans, mean
    width = int(width_mm / cw)
    lines = ["NOTES"]
    for i, n in enumerate(notes):
        w = wrap(n, width - 4)
        lines.append(f"{i + 1:<3d}" + w[0])
        lines += ["    " + x_.strip() for x_ in w[1:]]
    dy = size * 0.3528 * 1.62
    n_fit = int((y_top - bottom) / dy)
    for i, ln in enumerate(lines[:n_fit]):
        S.text(x, y_top - 3.0 - i * dy, ln, size=size, weight="bold" if i == 0 else "normal")
    return lines[n_fit:]


def table(S, x, y_top, cols, rows, row_h=5.2, size=6.6, head=True, wrap_cols=None):
    """a ruled table from its top-left corner; cols [(title, width mm)]; rows of strings. Long cells wrap (2 lines
    max) where wrap_cols allows. Returns the bottom y."""
    cw = 0.62 * size * 0.3528
    y = y_top
    allrows = ([tuple(c for c, _ in cols)] if head else []) + [tuple(r) for r in rows]
    for i, r in enumerate(allrows):
        cells = []
        n_l = 1
        for (c, wc), val in zip(cols, r):
            n_ch = max(4, int((wc - 2.0) / cw))
            s_ = str(val)
            parts_ = textwrap.wrap(s_, n_ch) or [""]
            if len(parts_) > 1 and (wrap_cols is None or c in wrap_cols):
                parts_ = parts_[:3]
            else:
                parts_ = [s_[:n_ch]]
            cells.append(parts_)
            n_l = max(n_l, len(parts_))
        hh = row_h + (n_l - 1) * size * 0.3528 * 1.3
        xx = x
        for (c, wc), parts_ in zip(cols, cells):
            S.ax.add_patch(Rectangle((xx, y - hh), wc, hh, fill=(head and i == 0), fc="#eceae3", ec=INK, lw=0.4, zorder=5))
            cap = 0.72 * size * 0.3528
            for k, t in enumerate(parts_):
                S.text(xx + 1.2, y - 0.5 * (row_h + cap) - k * size * 0.3528 * 1.3, t, size=size,
                       weight="bold" if (head and i == 0) else "normal")
            xx += wc
        y -= hh
    return y


def image_box(S, png, box, caption):
    bx = box
    S.ax.add_patch(Rectangle(bx[:2], bx[2], bx[3], fill=False, ec=INK, lw=LW_THIN, zorder=2))
    if png and os.path.exists(png):
        img = plt.imread(png)
        h_img, w_img = img.shape[:2]
        k = min((bx[2] - 3) / w_img, (bx[3] - 8) / h_img)
        w_, h_ = w_img * k, h_img * k
        x_, y_ = bx[0] + (bx[2] - w_) / 2, bx[1] + 6 + (bx[3] - 8 - h_) / 2
        S.ax.imshow(img, extent=(x_, x_ + w_, y_, y_ + h_), zorder=1, interpolation="lanczos")
    S.text(bx[0] + 2, bx[1] + 2.2, caption, size=6.3)


# ---------------------------------------------------------------------------------------------------------
# the 3-D views: one Chromium for the whole set
# ---------------------------------------------------------------------------------------------------------
class Renderer:
    def __init__(self, enabled=True):
        self.ok = enabled and os.path.isdir(os.path.join(ROOT, "tools", "step-viewer", "node_modules", "three"))
        if not self.ok:
            return
        self.tmp = tempfile.mkdtemp(prefix="_dset_", dir=OUT_DIR)

        class Quiet(http.server.SimpleHTTPRequestHandler):
            def log_message(self, *a):
                pass
        self.srv = socketserver.TCPServer(("127.0.0.1", 0), functools.partial(Quiet, directory=ROOT))
        threading.Thread(target=self.srv.serve_forever, daemon=True).start()
        from playwright.sync_api import sync_playwright
        self.pw = sync_playwright().start()
        self.b = self.pw.chromium.launch(executable_path=os.environ.get("CHROMIUM", "/opt/pw-browsers/chromium"),
                                         args=["--use-angle=swiftshader", "--enable-unsafe-swiftshader", "--ignore-gpu-blocklist"])
        self.pg = self.b.new_page(viewport={"width": 900, "height": 600}, device_scale_factor=1)
        self.n = 0

    def png(self, shapes, out, view=(1.0, -1.4, 0.9), up=(0, 0, 1), colour=None, size=(900, 600)):
        """shapes: [(shape, rgb)]; colour: one colour (hex) for a single part, None to keep each shape's."""
        if not self.ok:
            return None
        import step_to_glb as G
        meshes, nodes = [], []
        lo = np.min([bbox(s)[0] for s, _ in shapes], axis=0); hi = np.max([bbox(s)[1] for s, _ in shapes], axis=0)
        defl = max(0.02, 0.0015 * float(np.linalg.norm(hi - lo)))
        for i, (s, c) in enumerate(shapes):
            P, N, I = G.tessellate(s, defl, 0.3)
            if len(I) == 0:
                continue
            meshes.append((f"m{i}", tuple(c), 0.4, P, N, I))
            nodes.append((len(meshes) - 1, np.eye(4), f"m{i}", {}))
        self.n += 1
        glb = os.path.join(self.tmp, f"p{self.n}.glb")
        G.write_glb(glb, meshes, nodes, title="part")
        self.pg.set_viewport_size({"width": size[0], "height": size[1]})
        rel = os.path.relpath(glb, ROOT)
        url = (f"http://127.0.0.1:{self.srv.server_address[1]}/tools/step-viewer/part.html?model=/{rel}"
               f"&dir={','.join(f'{x:g}' for x in view)}&up={','.join(f'{x:g}' for x in up)}" + (f"&color={colour}" if colour else ""))
        self.pg.goto(url)
        self.pg.wait_for_function("window.ready === true", timeout=180000)
        self.pg.screenshot(path=out)
        os.remove(glb)
        return out

    def close(self):
        if not self.ok:
            return
        self.b.close(); self.pw.stop(); self.srv.shutdown()
        try:
            os.rmdir(self.tmp)
        except OSError:
            pass


def hexcol(rgb, lift=0.15):
    r, g, b = [min(1.0, c + lift * (1 - c)) for c in rgb]
    return f"{int(r * 255):02x}{int(g * 255):02x}{int(b * 255):02x}"


# ---------------------------------------------------------------------------------------------------------
# the sheets
# ---------------------------------------------------------------------------------------------------------
BOX3D = (300.0, 72.0, 110.0, 76.0)


def equal_spaced(angles, tol=0.2):
    n = len(angles)
    if n < 2:
        return False
    a = sorted(angles)
    d = [(a[(i + 1) % n] - a[i]) % 360.0 for i in range(n)]
    return all(abs(x - 360.0 / n) < tol for x in d)


def hole_text(h, mark=None, tapped=None):
    """a hole group's callout; tapped {drill Ø: 'M6'} names a tapped hole by its thread."""
    thr = next((v for k, v in (tapped or {}).items() if abs(k - h["d"]) < 0.05), None)
    t = (f"{h['n']}× " if h["n"] > 1 else "") + (thr or f"Ø{h['d']:.4g}")
    t += " THRU" if h.get("thru") else f" ↧ {h['z1'] - h['z0']:.3g}"
    if mark:
        t += f", CSK Ø{mark[0]:.3g} × 90°"
    if h["n"] > 1:
        t += (" EQ SP" if equal_spaced(h["angles"]) else "") + f" on PCD Ø{h['pcd']:.4g}"
    elif h["pcd"] > 0:
        t += f" at r {0.5 * h['pcd']:.4g}, {h['angles'][0]:.1f}°"
    return t


def x_at(outline, z, side=-1, tol=0.06):
    """the outline's outermost x (side -1: most negative) at height z."""
    xs = [p[0] for P in outline for p in P if abs(p[1] - z) < tol]
    if not xs:
        return None
    return min(xs) if side < 0 else max(xs)


def z_levels(F, zmin, zmax, tol=0.3):
    """the faces' heights for the chain of lengths, a level within tol of the one below it merged; the chain ends on
    the part's top face."""
    zs = sorted({round(q["z"], 3) for q in F["zplanes"]} | {round(zmin, 3), round(zmax, 3)})
    out = []
    for z in zs:
        if not out or z - out[-1] > tol:
            out.append(z)
    if out[-1] != round(zmax, 3):
        out[-1] = round(zmax, 3)
    return out


def draw_section(S, sec, tr, hatch="////", clip=None):
    S.hatch(sec["tris"], tr, hatch=hatch, clip=clip)
    S.edges(sec["edges"], tr, hidden=False, clip=clip)
    S.lines(sec["outline"], tr, clip=clip)


def cutting_line(S, a, b, label):
    """the section's cutting plane in a view: a chain line with thick ends and the view arrows."""
    a, b = np.asarray(a, float), np.asarray(b, float)
    S.chain(a, b)
    u = (b - a) / (np.linalg.norm(b - a) or 1.0)
    n = np.array([-u[1], u[0]])
    for p, s in ((a, 1), (b, -1)):
        S.line([p, p + s * u * 5.0], lw=LW_VIS * 1.2)
        tip = p + s * u * 2.5
        S.line([tip + n * 7.0, tip + n * 1.0], lw=0.8)
        S.arrow(tip + n * 0.8, tip + n * 7.0, size=3.0, color=INK)
        S.text(*(tip + n * 9.5 + np.array([0, -1.6])), label, size=9, weight="bold", ha="center")


def begin(e, ctx):
    S = Sheet()
    return S


def finish(S, e, ctx, mass_kg, scale_s, png3d, notes, data_rows, caption3d=None, notes_box=None):
    furniture(S, e, mass_kg, e.get("qty"), scale_s, ctx["sheet_no"][e["dwg"]], ctx["n_sheets"])
    if not e.get("no_3d"):
        image_box(S, png3d, BOX3D, caption3d or "3-D view (axonometric, not to scale)")
    rows = [("status", e.get("status_text") or e.get("status", "")), ("qty per machine", str(e.get("qty") or "—")),
            ("used in", e.get("used_in", "—")), ("source", e.get("source", "—"))] + list(data_rows)
    table(S, 300.0, 262.0, [("", 30.0), ("", 80.0)], rows, head=False, size=6.2, row_h=4.6, wrap_cols=("",))
    nb = notes_box or dict(x=24.0, y_top=108.0, width_mm=202.0)
    rest = notes_block(S, notes, **nb)
    if rest:
        print(f"  {e['dwg']}: {len(rest)} note lines did not fit", flush=True)
    out = ctx["out_pdf"](e["dwg"])
    S.fig.savefig(out)
    if ctx.get("preview"):
        S.fig.savefig(os.path.join(ctx["preview"], f"{e['dwg']}.png"), dpi=ctx.get("dpi", 110))
    plt.close(S.fig)
    return out


MATCOL = [("steatite", (0.95, 0.94, 0.89)), ("silicone", (0.78, 0.86, 0.90)), ("PTFE", (0.96, 0.96, 0.93)),
          ("G10", (0.84, 0.76, 0.52)), ("G-10", (0.84, 0.76, 0.52)), ("glass-epoxy", (0.80, 0.74, 0.55)),
          ("PEEK", (0.88, 0.80, 0.62)), ("borosilicate", (0.80, 0.91, 0.96)), ("MnZn", (0.33, 0.33, 0.35)),
          ("NiFe", (0.70, 0.70, 0.64)), ("M235", (0.55, 0.57, 0.62)), ("magnet wire", (0.86, 0.53, 0.32)),
          ("Cu", (0.86, 0.53, 0.32)), ("brass", (0.86, 0.72, 0.38)), ("1.4404", (0.74, 0.76, 0.79)),
          ("stainless", (0.74, 0.76, 0.79)), ("bearing", (0.70, 0.72, 0.76)), ("Al", (0.83, 0.85, 0.89)),
          ("ceramic", (0.56, 0.67, 0.82)), ("rectifier", (0.25, 0.25, 0.28)), ("resistor", (0.36, 0.55, 0.42)),
          ("POM", (0.94, 0.93, 0.88)), ("M400", (0.50, 0.52, 0.57)), ("PET", (0.88, 0.80, 0.45))]


def matcol(text, default=None):
    for k, c in MATCOL:
        if k in (text or ""):
            return c
    return default or (0.80, 0.81, 0.84)


def render_part(e, ctx, shape):
    """the part's shaded 3-D view: its solid (or its 3-D solid, e.g. a gear's teeth), in its material's colour; a
    module of several parts (parts3d) in each part's colour."""
    if not ctx["renderer"].ok:
        return None
    out = os.path.join(ctx["tmp"], f"{e['dwg']}_3d.png")
    v = e.get("view3d", {})
    if e.get("parts3d"):
        return ctx["renderer"].png(e["parts3d"], out, view=v.get("dir", (1.0, -1.4, 0.9)), up=v.get("up", (0, 0, 1)),
                                   size=(900, 620))
    shape = e["shape3d"] if e.get("shape3d") is not None else shape
    col = e.get("colour3d") or matcol(e.get("material", "") + " " + e.get("model_material", ""), e.get("colour"))
    lo, hi = bbox(shape)
    if not v and (hi[2] - lo[2]) > 3.0 * max(hi[0] - lo[0], hi[1] - lo[1]):
        shape = rotated(shape, (0, 1, 0), 90.0)                    # a long part lies along x
        v = dict(dir=(0.55, -1.4, 0.75))
    return ctx["renderer"].png([(shape, col)], out, view=v.get("dir", (1.0, -1.4, 0.9)), up=v.get("up", (0, 0, 1)),
                               colour=hexcol(col, 0.0), size=(900, 620))


def part_mass(e, shape):
    if "mass_kg" in e:                                             # a part of several materials: its entry's sum
        return e["mass_kg"]
    rho = e.get("rho") or density(e.get("model_material", "") or e.get("material", ""))
    return volume(e["shape3d"] if e.get("shape3d") is not None else shape) * 1e-9 * rho if rho else None


def sheet_turned(e, ctx):
    """a part of revolution about z (holes and features off the axis allowed): SECTION A-A through the axis and the
    end view; a detail when the section is thin; the diameters, lengths and hole patterns from its faces."""
    shape = e["shape"]
    F = features(shape)
    G = coax_groups(F)
    H = hole_groups(F)
    lo, hi = tight_bbox(shape)
    zmin, zmax = float(lo[2]), float(hi[2])
    R = float(max(-lo[0], hi[0], -lo[1], hi[1]))
    L = zmax - zmin
    marks = cones_at(F, H)
    for i, (D_, zf) in marks.items():                             # a countersunk hole runs to its face
        if abs(zf - zmax) < 0.06:
            H[i]["z1"] = zmax
        elif abs(zf - zmin) < 0.06:
            H[i]["z0"] = zmin
    for h in H:
        h["thru"] = abs(h["z0"] - zmin) < 0.06 and abs(h["z1"] - zmax) < 0.06
    sec = section_y0(shape)
    S = begin(e, ctx)
    long_ = e.get("long", L >= 1.2 * R)
    zl = z_levels(F, zmin, zmax, e.get("level_tol", 0.3))
    scales = []
    if long_:
        bxA, bxB, bxD = (28.0, 160.0, 264.0, 112.0), (28.0, 112.0, 70.0, 44.0), (104.0, 112.0, 188.0, 44.0)
        sA = e.get("scale") or fit_scale(L, 2 * R, bxA[2] - 44, bxA[3] - 46)
        cA = np.array([bxA[0] + bxA[2] * 0.47, bxA[1] + bxA[3] * 0.58])
        tr = S.map(cA - sA * np.array([0.5 * (zmin + zmax), 0.0]), sA, [[0.0, 1.0], [1.0, 0.0]])
        draw_section(S, sec, tr)
        S.chain(tr([0.0, zmin - 5.0 / sA]), tr([0.0, zmax + 5.0 / sA]))
        S.title(bxA[0], bxA[1] + bxA[3] + 2, f"SECTION A–A   {scale_txt(sA)}")
        scales.append(sA)
        # diameters: the outer ones at the end they reach, the bores inside
        right = [g for g in G if not g[1] and abs(g[3] - zmax) < 0.06]
        left = [g for g in G if not g[1] and abs(g[2] - zmin) < 0.06 and g not in right]
        k_r = k_l = 0
        for r, hole, z0, z1 in sorted(right, key=lambda g: g[0]):
            x_line = tr([0.0, zmax])[0] + 7.0 + 8.0 * k_r
            S.vdim(tr([-r, 0])[1], tr([r, 0])[1], x_line, tr([0, z1])[0], tr([0, z1])[0], f"Ø{2 * r:.4g}")
            k_r += 1
        for r, hole, z0, z1 in sorted(left, key=lambda g: g[0]):
            x_line = tr([0.0, zmin])[0] - 7.0 - 8.0 * k_l
            S.vdim(tr([-r, 0])[1], tr([r, 0])[1], x_line, tr([0, z0])[0], tr([0, z0])[0], f"Ø{2 * r:.4g}")
            k_l += 1
        mids = [g for g in G if not g[1] and g not in right and g not in left]
        for i, (r, hole, z0, z1) in enumerate(mids):
            S.callout(tr([r, 0.5 * (z0 + z1)]), f"Ø{2 * r:.4g}", (0.5 + 0.2 * i, 1.0))
        bt = e.get("bore_text", {})
        n_bt = 0
        top_s = tr([R, 0.0])[1]
        outer_r = [g[0] for g in G if not g[1]]
        for r, hole, z0, z1 in [g for g in G if g[1] and not any(abs(g[0] - ro) < 0.05 for ro in outer_r)]:
            txt = next((t for k, t in bt.items() if abs(k - 2 * r) < 0.05), None)
            if txt:
                tip = tr([r, z0 + 0.5 * min(z1 - z0, 0.5 * L)])
                S.leader(tip, (tip[0] + 9.0, top_s + 8.0 + 5.0 * n_bt), txt)
                n_bt += 1
            elif (z1 - z0) * sA >= 16 and 2 * r * sA >= 8:
                zc = z0 + 0.3 * (z1 - z0)
                S.vdim(tr([-r, 0])[1], tr([r, 0])[1], tr([0, zc])[0], tr([0, zc])[0], tr([0, zc])[0], f"Ø{2 * r:.4g}")
            else:
                S.callout(tr([r, 0.5 * (z0 + z1)]), f"bore Ø{2 * r:.4g}", (-0.6, 1.0))
        for r, z0, z1 in e.get("threads", ()):                      # ISO 6410: the thread's major diameter, thin
            for sg in (-1, 1):
                S.line([tr([sg * r, z0]), tr([sg * r, z1])], lw=LW_THIN * 0.9, color=INK)
        # lengths below: the chain of the faces' heights and the overall
        yb = tr([-R, 0])[1]
        if 2 < len(zl) <= 9:
            for a, b in zip(zl[:-1], zl[1:]):
                xa, xb = x_at(sec["outline"], a) or -R, x_at(sec["outline"], b) or -R
                S.hdim(tr([0, a])[0], tr([0, b])[0], yb - 9.0, tr([xa, a])[1], tr([xb, b])[1], f"{b - a:.4g}", txt_side=1)
        S.hdim(tr([0, zmin])[0], tr([0, zmax])[0], yb - (18.0 if 2 < len(zl) <= 9 else 9.0), tr([-R, zmin])[1],
               tr([-R, zmax])[1], f"{L:.4g}")
        seen = set()
        for q in F["radial"]:
            key = (round(q["r"], 2), round(q["loc"][2], 1))
            if key in seen or not q["hole"]:
                continue
            seen.add(key)
            S.callout(tr([0.0, q["loc"][2]]) + np.array([0, 2.0]), f"Ø{2 * q['r']:.3g} radial, at {q['loc'][2] - zmin:.4g}",
                      (0.4, 1.0))
        for v, P, text, d in e.get("callouts", ()):
            if v == "section":
                S.callout(tr(P), text, d)
        extra_lines(S, e, "section", tr)
        # the end view, small
        sB = e.get("scale_b") or fit_scale(2 * R, 2 * R, bxB[2] - 26, bxB[3] - 10)
        cB = np.array([bxB[0] + bxB[2] * 0.55, bxB[1] + bxB[3] * 0.5])
        trB = S.map(cB, sB)
        S.edges(hlr(shape, "top"), trB)
        S.centre_mark(cB, size=R * sB + 2.5)
        for r, z0, z1 in e.get("threads", ())[:1]:
            S.ax.add_patch(Arc(tuple(cB), 2 * r * sB, 2 * r * sB, theta1=0.0, theta2=270.0, ec=INK, lw=LW_THIN * 0.9, zorder=4))
        S.title(bxB[0], bxB[1] + bxB[3] + 1, f"VIEW B   {scale_txt(sB)}")
        scales.append(sB)
        hole_callouts(S, H, marks, trB, R * sB, cB, compact=True, tapped=e.get("tapped"))
        # detail D: a part of the section, large
        dz = e.get("detail_z")
        if dz:
            dx = e.get("detail_x") or (-R, R)
            sD = e.get("scale_d") or fit_scale(dz[1] - dz[0], dx[1] - dx[0], bxD[2] - 30, bxD[3] - 10)
            cD = np.array([bxD[0] + bxD[2] * 0.5, bxD[1] + bxD[3] * 0.5])
            trD = S.map(cD - sD * np.array([0.5 * (dz[0] + dz[1]), 0.5 * (dx[0] + dx[1])]), sD, [[0.0, 1.0], [1.0, 0.0]])
            a_, b_ = trD([dx[0], dz[0]]), trD([dx[1], dz[1]])
            clip = Rectangle((min(a_[0], b_[0]), min(a_[1], b_[1])), abs(b_[0] - a_[0]), abs(b_[1] - a_[1]),
                             transform=S.ax.transData)
            draw_section(S, sec, trD, clip=clip)
            S.ax.add_patch(Rectangle(clip.get_xy(), clip.get_width(), clip.get_height(), fill=False, ec=INK, lw=0.4,
                                     ls=(0, (4, 2)), zorder=1))
            S.title(bxD[0], bxD[1] + bxD[3] + 1, f"DETAIL D   {scale_txt(sD)}   (A–A, z {dz[0]:.4g} to {dz[1]:.4g})")
            scales.append(sD)
            for v, P, text, d in e.get("callouts", ()):
                if v == "detail":
                    S.callout(trD(P), text, d)
    else:
        sA = e.get("scale") or fit_scale(2 * R, 2 * R, 174.0, 150.0)
        w_plan = max(124.0, min(207.0, 2 * R * sA + 62.0))
        bxA = (28.0, 116.0, w_plan, 164.0)
        bxC = (bxA[0] + w_plan + 4.0, 116.0, 294.0 - (bxA[0] + w_plan + 4.0), 164.0)
        cA = np.array([bxA[0] + max(46.0 + R * sA, 0.5 * w_plan), bxA[1] + bxA[3] * 0.50])
        trA = S.map(cA, sA)
        E = hlr(shape, "top")
        S.edges(E, trA)
        S.centre_mark(cA, size=min(8.0, 0.3 * R * sA) + 2.0)
        cutting_line(S, cA - [R * sA + 6, 0], cA + [R * sA + 6, 0], "A")
        S.title(bxA[0], bxA[1] + bxA[3] + 1, f"PLAN   {scale_txt(sA)}")
        scales.append(sA)
        diameter_fan(S, G, trA, cA, R * sA)
        hole_callouts(S, H, marks, trA, R * sA, cA, tapped=e.get("tapped"))
        for (ra, a0, a1, text) in e.get("angles", ()):
            S.adim(cA, ra * sA, a0, a1, text)
        for v, P, text, d in e.get("callouts", ()):
            if v == "plan":
                S.callout(trA(P), text, d)
        # the section A-A, its part between r x0 and x1, enlarged: z across and r up (a plate), or r across and z up
        # (a ring), whichever draws it larger
        dw = e.get("detail") or (max(0.0, R - min(R, 40.0)), R)
        x0, x1 = dw
        bw, bh = bxC[2] - 30, bxC[3] - 40
        sH, sV = fit_scale(L, x1 - x0, bw, bh), fit_scale(x1 - x0, L, bw, bh)
        vert = e.get("section_vertical", sV > sH)
        sC = e.get("scale_c") or (sV if vert else sH)
        cC = np.array([bxC[0] + bxC[2] * 0.40, bxC[1] + bxC[3] * 0.48])
        pad = 3.0
        xs_in = [p[0] for P in sec["outline"] for p in P if x0 - 1e-6 <= p[0] <= x1 + 1e-6]
        rs = sorted({round(g[0], 3) for g in G if x0 - 1e-6 <= g[0] <= x1 + 1e-6})
        if not vert:
            trC = S.map(cC - sC * np.array([0.5 * (zmin + zmax), 0.5 * (x0 + x1)]), sC, [[0.0, 1.0], [1.0, 0.0]])
            y_a, y_b = trC([x0, 0])[1], trC([x1, 0])[1]
            z_a, z_b = trC([0, zmin])[0], trC([0, zmax])[0]
            clip_rect = Rectangle((z_a - pad - 4, min(y_a, y_b)), (z_b - z_a) + 2 * pad + 8, abs(y_b - y_a),
                                  transform=S.ax.transData)
            draw_section(S, sec, trC, clip=clip_rect)
            for yy in (min(y_a, y_b), max(y_a, y_b)):                 # break lines where the cut part ends
                S.line([(z_a - pad - 4, yy), (z_b + pad + 4, yy)], lw=0.4, color=INK, ls=(0, (2, 1.5)))
            top = trC([max(xs_in), 0])[1] if xs_in else max(y_a, y_b)
            if len(zl) <= 6:
                for a, b in zip(zl[:-1], zl[1:]):
                    S.hdim(trC([0, a])[0], trC([0, b])[0], top + 7.0, top, top, f"{b - a:.4g}")
            if len(zl) > 2:
                S.hdim(trC([0, zmin])[0], trC([0, zmax])[0], top + 15.0, top, top, f"{L:.4g}")
            for k, r in enumerate(rs[:5]):
                S.line([(z_b + 1.0, trC([r, 0])[1]), (z_b + 6.0, trC([r, 0])[1])], lw=LW_THIN * 0.8, color=DIMC)
                S.text(z_b + 7.0, trC([r, 0])[1] - 1.0, f"r {r:.4g}", size=6.6, color=DIMC)
        else:
            trC = S.map(cC - sC * np.array([0.5 * (x0 + x1), 0.5 * (zmin + zmax)]), sC)
            x_a, x_b = trC([x0, 0])[0], trC([x1, 0])[0]
            z_a, z_b = trC([0, zmin])[1], trC([0, zmax])[1]
            clip_rect = Rectangle((min(x_a, x_b), z_a - pad - 4), abs(x_b - x_a), (z_b - z_a) + 2 * pad + 8,
                                  transform=S.ax.transData)
            draw_section(S, sec, trC, clip=clip_rect)
            for xx in (min(x_a, x_b), max(x_a, x_b)):
                S.line([(xx, z_a - pad - 4), (xx, z_b + pad + 4)], lw=0.4, color=INK, ls=(0, (2, 1.5)))
            right = trC([max(xs_in), 0])[0] if xs_in else max(x_a, x_b)
            if len(zl) <= 6:
                for a, b in zip(zl[:-1], zl[1:]):
                    S.vdim(trC([0, a])[1], trC([0, b])[1], right + 7.0, right, right, f"{b - a:.4g}")
            if len(zl) > 2:
                S.vdim(trC([0, zmin])[1], trC([0, zmax])[1], right + 15.0, right, right, f"{L:.4g}")
            for k, r in enumerate(rs[:5]):
                xr = trC([r, 0])[0]
                S.line([(xr, z_a - 1.0), (xr, z_a - 6.0)], lw=LW_THIN * 0.8, color=DIMC)
                S.ax.text(xr, z_a - 7.0, f"r {r:.4g}", fontsize=6.6, ha="center", va="top", rotation=90, color=DIMC,
                          zorder=5, family="DejaVu Sans")
        extra_lines(S, e, "detail", trC, clip=clip_rect)
        S.title(bxC[0], bxC[1] + bxC[3] + 1, f"SECTION A–A   {scale_txt(sC)}")
        S.text(bxC[0], bxC[1] + bxC[3] - 3.0, f"(its part from r {x0:.4g} to {x1:.4g})", size=6.4, color=DIMC)
        scales.append(sC)
        for v, P, text, d in e.get("callouts", ()):
            if v == "detail":
                S.callout(trC(P), text, d)
    sc = ", ".join(dict.fromkeys(scale_txt(s) for s in scales))
    mass = part_mass(e, shape)
    png = render_part(e, ctx, shape)
    data = list(e.get("data", ())) + [("mass each", f"{mass:.3g} kg" if mass else "—")]
    return finish(S, e, ctx, mass, sc, png, e.get("notes", []), data)


def extra_lines(S, e, view, tr, clip=None):
    """the entry's own lines in a view: [(view, [(x, z), ...], 'chain' | 'thin')], e.g. a gear's pitch cone."""
    for v, P, style in e.get("lines", ()):
        if v != view:
            continue
        Q = np.array([tr(np.asarray(p, float)) for p in P])
        if style == "chain":
            ln, = S.ax.plot(Q[:, 0], Q[:, 1], color=INK, lw=LW_THIN * 0.8, ls=(0, (9, 2, 1.5, 2)), zorder=4)
        else:
            ln, = S.ax.plot(Q[:, 0], Q[:, 1], color=INK, lw=LW_THIN * 0.9, zorder=4)
        if clip is not None:
            ln.set_clip_path(clip)


def diameter_fan(S, G, tr, c, R_s):
    """each coaxial diameter by a leader from its circle, fanned over the upper half of the view."""
    rs = []
    for r, hole, z0, z1 in G:
        if not rs or abs(r - rs[-1][0]) > 0.05:
            rs.append((r, hole))
    n = len(rs)
    if n == 0:
        return
    angs = [150.0] if n == 1 else list(np.linspace(152.0, 100.0, n))
    for k, ((r, hole), a) in enumerate(zip(rs, angs)):
        t = math.radians(a)
        tip = np.asarray(c) + r * (tr([1.0, 0.0])[0] - tr([0.0, 0.0])[0]) * np.array([math.cos(t), math.sin(t)])
        knee = np.asarray(c) + (R_s + 7.0 + 2.5 * k) * np.array([math.cos(t), math.sin(t)])
        S.line([tip, knee], lw=LW_THIN * 0.8, color=DIMC)
        S.arrow(tip, knee, color=DIMC)
        end = knee + np.array([-5.0, 0.0])
        S.line([knee, end], lw=LW_THIN * 0.8, color=DIMC)
        S.text(end[0] - 0.8, end[1] - 0.9, f"Ø{2 * r:.4g}", ha="right", color=DIMC)


def hole_callouts(S, H, marks, tr, R_s, c, compact=False, tapped=None):
    """one leader per hole group from the hole nearest the leader's way (down-left on a plan, down-right on a small end
    view), the groups stacked along it; the pitch circles chained."""
    c = np.asarray(c, float)
    way = 315.0 if compact else 225.0
    u = np.array([math.cos(math.radians(way)), math.sin(math.radians(way))])
    k = 0
    for i, h in enumerate(H):
        if not h["hole"]:
            continue
        if h["n"] > 1 and h["pcd"] > 0:
            r_p = 0.5 * h["pcd"]
            S.ax.add_patch(Circle(tuple(tr([0.0, 0.0])), r_p * (tr([1.0, 0.0])[0] - tr([0.0, 0.0])[0]), fill=False, ec=INK,
                                  lw=LW_THIN * 0.8, ls=(0, (9, 2, 1.5, 2)), zorder=3))
        a = math.radians(min(h["angles"], key=lambda b: abs((b - way + 180.0) % 360.0 - 180.0)))
        r_p = 0.5 * h["pcd"]
        P = np.array([r_p * math.cos(a), r_p * math.sin(a)])
        tip = tr(P + 0.5 * h["d"] * np.array([math.cos(a), math.sin(a)]) * (1 if r_p > 0 else 0))
        knee = c + (R_s + 6.0 + 8.0 * k) * u
        txt = hole_text(h, marks.get(i), tapped)
        ha = "left" if u[0] >= 0 else "right"
        S.line([tip, knee], lw=LW_THIN * 0.8, color=DIMC)
        S.arrow(tip, knee, color=DIMC)
        end = knee + np.array([5.0 if ha == "left" else -5.0, 0.0])
        S.line([knee, end], lw=LW_THIN * 0.8, color=DIMC)
        for j, part in enumerate(wrap(txt, 30)):
            S.text(end[0] + (0.8 if ha == "left" else -0.8), end[1] - 0.9 - 3.0 * j, part.strip(), ha=ha, color=DIMC,
                   size=TXT * 0.9)
        k += 1


def three_views(S, shape, box, hidden=True, views=("front", "top", "side"), scale=None):
    """third-angle projection: the front view (x, z) low left, the top view (x, y) above it, the right view (y, z)
    beside it; returns (scale, {view: (transform, (lo, hi))})."""
    E = {v: hlr(shape, v) for v in views}
    ext = {v: edges_box(E[v], ("vis", "hid")) for v in views}
    w = lambda v: (ext[v][1] - ext[v][0]) if v in ext else np.zeros(2)
    W = w("front")[0] + (w("side")[0] if "side" in views else 0.0) + 40.0
    Hh = w("front")[1] + (w("top")[1] if "top" in views else 0.0) + 40.0
    s = scale or fit_scale(W, Hh, box[2], box[3])
    gap = 22.0
    tot_w = s * (w("front")[0] + (w("side")[0] if "side" in views else 0)) + (gap if "side" in views else 0)
    tot_h = s * (w("front")[1] + (w("top")[1] if "top" in views else 0)) + (gap if "top" in views else 0)
    x0 = box[0] + 0.5 * (box[2] - tot_w)
    y0 = box[1] + 0.5 * (box[3] - tot_h)
    out = {}
    org = lambda v, X, Y: np.array([X, Y]) - s * ext[v][0]
    out["front"] = S.map(org("front", x0, y0), s)
    if "top" in views:
        out["top"] = S.map(org("top", x0, y0 + s * w("front")[1] + gap), s)
    if "side" in views:
        out["side"] = S.map(org("side", x0 + s * w("front")[0] + gap, y0), s)
    for v in views:
        S.edges(E[v], out[v], hidden=hidden)
    return s, {v: (out[v], ext[v]) for v in views}


def overall_dims(S, V):
    """the overall extents on a three-view layout."""
    if "front" in V:
        tr, (lo, hi) = V["front"]
        a, b = tr(lo), tr(hi)
        S.hdim(a[0], b[0], a[1] - 9.0, a[1], a[1], f"{round(hi[0] - lo[0], 1):g}")
        S.vdim(a[1], b[1], a[0] - 9.0, a[0], a[0], f"{round(hi[1] - lo[1], 1):g}")
    if "top" in V:
        tr, (lo, hi) = V["top"]
        a, b = tr(lo), tr(hi)
        S.vdim(a[1], b[1], a[0] - 9.0, a[0], a[0], f"{round(hi[1] - lo[1], 1):g}")


def sheet_block(e, ctx):
    """a prismatic part: three views by hidden-line removal, the overall extents, the entry's own dimensions."""
    shape = e["shape"]
    S = begin(e, ctx)
    box = (34.0, 118.0, 258.0, 156.0)
    s, V = three_views(S, shape, box, views=e.get("views", ("front", "top", "side")), scale=e.get("scale"))
    overall_dims(S, V)
    for v, p1, p2, off, text in e.get("dims", ()):
        tr = V[v][0]
        S.dim(tr(p1), tr(p2), off, text)
    for v, tip, text, d in e.get("callouts", ()):
        S.callout(V[v][0](tip), text, d)
    for v in V:
        tr, (lo, hi) = V[v]
        S.text(tr(lo)[0], tr(hi)[1] + 3.0, {"front": "FRONT", "top": "TOP", "side": "RIGHT"}[v], size=7.2, weight="bold")
    mass = part_mass(e, shape)
    png = render_part(e, ctx, shape)
    data = list(e.get("data", ())) + [("mass each", f"{mass:.3g} kg" if mass else "—")]
    return finish(S, e, ctx, mass, scale_txt(s), png, e.get("notes", []), data)


def sheet_bought(e, ctx):
    """a bought part: its envelope as the model draws it, the specification, the candidate, the notes."""
    shape = e["shape"]
    S = begin(e, ctx)
    box = e.get("env_box", (34.0, 196.0, 258.0, 82.0))
    s, V = three_views(S, shape, box, views=e.get("views", ("front", "top")), scale=e.get("scale"))
    overall_dims(S, V)
    for v, tip, text, d in e.get("callouts", ()):
        S.callout(V[v][0](tip), text, d)
    S.title(28.0, 280.0, e.get("env_title", "ENVELOPE (as the model draws it)") + "   " + scale_txt(s))
    y = table(S, 28.0, box[1] - 6.0, [("specification", 70.0), ("value", 196.0)], e.get("spec", []), size=6.6,
              row_h=5.0, wrap_cols=("value",))
    mass = e.get("mass_kg")
    png = render_part(e, ctx, shape)
    return finish(S, e, ctx, mass, scale_txt(s), png, e.get("notes", []), e.get("data", ()),
                  notes_box=dict(x=24.0, y_top=min(108.0, y - 2.0), width_mm=202.0))


def sheet_list(e, ctx, png=None):
    """a list sheet (the fasteners and stock, a wiring list): a table, no views."""
    S = begin(e, ctx)
    S.title(28.0, 280.0, e.get("heading", ""))
    y = table(S, 28.0, 276.0, e["cols"], e["rows"], size=6.5, row_h=5.0, wrap_cols=tuple(c for c, _ in e["cols"]))
    return finish(S, e, ctx, None, "—", png, e.get("notes", []), e.get("data", ()), caption3d=e.get("caption3d"),
                  notes_box=dict(x=24.0, y_top=min(108.0, y - 2.0), width_mm=202.0))


# ---------------------------------------------------------------------------------------------------------
# sub-assemblies
# ---------------------------------------------------------------------------------------------------------
HATCHES = ("////", "\\\\\\\\", "xxxx", "....", "////", "\\\\\\\\")


def lighten(rgb, k=0.55):
    return tuple(min(1.0, c + k * (1 - c)) for c in rgb)


def assembly_section(S, M, items, box, planes, window, horizontal=False, label="SECTION A–A"):
    """an exact section of the placed parts. planes: [(theta_deg, 'right' | 'left' | 'full')], each the plane through
    the axis at theta turned onto y = 0 and drawn on its half of the view, or [('z', z_cut, 'plan')], a plan cut.
    window: (x0, x1, z0, z1) in the cut's own frame ((x, y) for a plan). Returns the anchors per item (sheet points
    inside its cut) and the scale."""
    import tube_geometry as TG
    x0w, x1w, z0, z1 = window
    W, H = (z1 - z0, x1w - x0w) if horizontal else (x1w - x0w, z1 - z0)
    s = fit_scale(W, H, box[2] - 34, box[3] - 22)
    c = np.array([box[0] + box[2] / 2, box[1] + box[3] / 2 - 2])
    xm, zm = 0.5 * (x0w + x1w), 0.5 * (z0 + z1)
    if horizontal:
        tr = S.map(c - s * np.array([zm, xm]), s, [[0.0, 1.0], [1.0, 0.0]])
    else:
        tr = S.map(c - s * np.array([xm, zm]), s)
    a_, b_ = tr([x0w, z0]), tr([x1w, z1])
    vx0, vx1 = min(a_[0], b_[0]) - 2, max(a_[0], b_[0]) + 2
    vy0, vy1 = min(a_[1], b_[1]) - 2, max(a_[1], b_[1]) + 2
    ax0 = tr([0.0, 0.0])                                        # the axis on the sheet
    anchors = {}
    for pl in planes:
        plan = pl[0] == "z"
        theta, half = (0.0, "full") if plan else pl
        if half == "full":
            clip_xy = (vx0, vy0, vx1 - vx0, vy1 - vy0)
        elif not horizontal:
            clip_xy = (ax0[0], vy0, vx1 - ax0[0], vy1 - vy0) if half == "right" else (vx0, vy0, ax0[0] - vx0, vy1 - vy0)
        else:
            clip_xy = (vx0, ax0[1], vx1 - vx0, vy1 - ax0[1]) if half == "right" else (vx0, vy0, vx1 - vx0, ax0[1] - vy0)
        clip = Rectangle(clip_xy[:2], clip_xy[2], clip_xy[3], transform=S.ax.transData)
        for k, it in enumerate(items):
            for nm in it["names"]:
                shp = M.placed(nm)
                lo, hi = bbox(shp)
                if plan:
                    if hi[2] < pl[1] or lo[2] > pl[1]:
                        continue
                elif hi[2] < z0 - 1 or lo[2] > z1 + 1:
                    continue
                turn = (180.0 - theta) if half == "left" else -theta    # the plane's ray onto its half of the view
                if abs(turn) > 1e-9:
                    shp = rotated(shp, (0, 0, 1), turn)
                cut = ("z", pl[1]) if plan else ("y", 0.0)
                tris = TG.section_faces(shp, cut)
                if not tris:
                    continue
                polys = TG.cut_polylines(shp, cut)
                ref = it.get("ref")
                fc = (0.93, 0.93, 0.93) if ref else lighten(it["colour"])
                p = tri_path(tris, tr)
                patch = PathPatch(p, fc=fc, ec="none", hatch=None if ref else HATCHES[it["no"] % len(HATCHES)], lw=0,
                                  zorder=1.5 if ref else 2)
                S.ax.add_patch(patch); patch.set_clip_path(clip)
                for P in polys:
                    Q = tr(P)
                    ln, = S.ax.plot(Q[:, 0], Q[:, 1], color="#8a8a8a" if ref else INK, lw=0.35 if ref else 0.45, zorder=3)
                    ln.set_clip_path(clip)
                # an anchor: the centroid of the largest triangle that lies inside this half
                best, area = None, 0.0
                inside = lambda m: (clip_xy[0] + 1.0 <= m[0] <= clip_xy[0] + clip_xy[2] - 1.0 and
                                    clip_xy[1] + 1.0 <= m[1] <= clip_xy[1] + clip_xy[3] - 1.0)
                for t in tris:
                    Q = np.array([tr(np.asarray(q, float)) for q in t])
                    u_, v_ = Q[1] - Q[0], Q[2] - Q[0]
                    a = 0.5 * abs(u_[0] * v_[1] - u_[1] * v_[0])
                    ins = [Q[0] + b0 * u_ + b1 * v_ for b0, b1 in BARY if inside(Q[0] + b0 * u_ + b1 * v_)]
                    if ins and a * len(ins) / len(BARY) > area:
                        best, area = np.mean(ins, axis=0), a * len(ins) / len(BARY)
                if best is not None and (it["no"] not in anchors or area > anchors[it["no"]][1]):
                    anchors[it["no"]] = (best, area)
    if not any(pl[0] == "z" for pl in planes) and x0w <= 0.0 <= x1w:
        if horizontal:
            S.chain(tr([0.0, z0]) - [4, 0], tr([0.0, z1]) + [4, 0])
        else:
            S.chain(tr([0.0, z0]) - [0, 4], tr([0.0, z1]) + [0, 4])
    S.title(box[0], box[1] + box[3] + 1.0, f"{label}   {scale_txt(s)}")
    return {k: v[0] for k, v in anchors.items()}, s


BARY = [(1.0 / 3.0, 1.0 / 3.0)] + [(i / 7.0, j / 7.0) for i in range(1, 7) for j in range(1, 7 - i)]


def balloons(S, anchors, box, r=3.2):
    """a balloon per item, in a column beside the view on its anchor's side, spaced so that none overlap."""
    cx = box[0] + box[2] / 2
    for side in (-1, 1):
        pts = sorted([(no, p) for no, p in anchors.items() if (p[0] >= cx) == (side > 0)], key=lambda q: -q[1][1])
        if not pts:
            continue
        x = box[0] + 4.5 if side < 0 else box[0] + box[2] - 4.5
        sp = 2 * r + 1.4
        top, bot = box[1] + box[3] - 5.0, box[1] + 5.0
        ys = []
        for no, p in pts:                                           # each at its anchor's height, pushed down to clear
            ys.append(min(p[1], top) if not ys else min(p[1], ys[-1] - sp))
        if ys and ys[-1] < bot:                                     # and pushed back up from the foot where it ran out
            ys[-1] = bot
            for i in range(len(ys) - 2, -1, -1):
                ys[i] = max(ys[i], ys[i + 1] + sp)
        for (no, p), y in zip(pts, ys):
            S.line([p, (x - side * r, y)], lw=0.5, color=INK)
            S.ax.add_patch(Circle(tuple(p), 0.6, fc=INK, ec=INK, zorder=6))
            S.ax.add_patch(Circle((x, y), r, fc="white", ec=INK, lw=0.7, zorder=6))
            S.text(x, y - 1.15, str(no), ha="center", size=7.0, weight="bold", z=7)


def module_unit(n):
    """a deck module's parts (body, potting, leads, studs) as one unit: A_D1_body -> A_D1, A_J_0_pot -> A_J_0."""
    t = n.split("_")
    return "_".join(t[:3] if len(t) > 2 and t[1] == "J" else t[:2])


def items_of(M, groups):
    """the parts list: groups [(label, dwg, material, predicate on a part's name and proto[, qty])] in order; each takes
    the parts no earlier group took. qty: a number or text, or a function naming each part's unit (the units are
    counted); by default the solids are counted. A label '(for reference)' or '(ref.)' marks a part drawn for its
    place only: unhatched in the section, left out of the 3-D view."""
    taken, out = set(), []
    for k, g in enumerate(groups):
        label, dwg, mat, pred = g[:4]
        names = [p["name"] for p in M.m.parts if p["name"] not in taken and pred(p["name"], p["proto"])]
        taken.update(names)
        if not names:
            continue
        ref = "for reference" in label or "(ref.)" in label
        qty = len(names)
        if len(g) > 4:
            qty = len({g[4](n) for n in names}) if callable(g[4]) else g[4]
        col = M.colour(M.by_name[names[0]]["proto"])
        out.append(dict(no=len(out) + 1, label=label, dwg=dwg, material=mat, names=names, qty="ref." if ref else qty,
                        colour=col, ref=ref))
    return out


def part_colour(M, name):
    k = M.by_name[name]["proto"]
    return matcol(M.material(k), M.colour(k))


AS_LAYOUTS = {
    # the view's box, the parts list's top-left corner, the 3-D box, the notes (x, top, width, bottom or None: from the
    # parts list's foot)
    "std": dict(view=(24.0, 66.0, 202.0, 214.0), plist=(231.0, 264.0), box3d=(230.0, 72.0, 180.0, 70.0),
                notes=(24.0, 62.0, 202.0, 12.0)),
    "tall": dict(view=(24.0, 14.0, 202.0, 266.0), plist=(231.0, 264.0), box3d=(230.0, 72.0, 180.0, 70.0),
                 notes=(231.0, None, 178.0, 146.0)),
    "wide": dict(view=(24.0, 172.0, 386.0, 94.0), plist=(24.0, 162.0), box3d=(230.0, 72.0, 180.0, 94.0),
                 notes=(24.0, None, 200.0, 12.0)),
    "std_notes": dict(view=(24.0, 90.0, 202.0, 190.0), plist=(231.0, 264.0), box3d=(230.0, 72.0, 180.0, 70.0),
                      notes=(24.0, 86.0, 202.0, 12.0)),
    # a broad view over two thirds of the sheet, the parts list in a narrow column beside it (the belt drive)
    "broad": dict(view=(24.0, 116.0, 272.0, 164.0), plist=(300.0, 264.0), box3d=(300.0, 72.0, 110.0, 76.0),
                  notes=(24.0, 112.0, 202.0, 12.0),
                  cols=[("item", 7.0), ("drawing", 20.0), ("description", 47.0), ("material", 24.0), ("qty", 12.0)]),
}


def sheet_assembly(e, ctx):
    M = ctx["submodel"](e["sub"]) if e.get("sub") else ctx["model"]
    items = items_of(M, e["groups"](M))
    S = begin(e, ctx)
    lay = AS_LAYOUTS[e.get("layout", "std")]
    box = e.get("box", lay["view"])
    anchors, s = assembly_section(S, M, items, box, e.get("planes", [(0.0, "full")]), e["window"],
                                  horizontal=e.get("horizontal", False), label=e.get("label", "SECTION A–A"))
    balloons(S, anchors, box)
    # the parts list
    cols = lay.get("cols", [("item", 9.0), ("drawing", 31.0), ("description", 80.0), ("material", 44.0), ("qty", 12.0)])
    rows = [(it["no"], it["dwg"], it["label"], it["material"], it["qty"]) for it in items]
    size = (6.3 if len(rows) <= 16 else 5.6) if "cols" not in lay else 5.4
    px, py = lay["plist"]
    y = table(S, px, py, cols, rows, size=size, row_h=4.6 if len(rows) <= 16 else 4.0, wrap_cols=("description", "material"))
    S.text(px, py + 1.6, "PARTS LIST", size=7.4, weight="bold")
    # 3-D: the parts by their materials, a quarter cut away, the reference parts left out
    png = None
    if ctx["renderer"].ok:
        shapes = [(M.placed(nm), part_colour(M, nm)) for it in items if not it["ref"] or e.get("ref3d")
                  for nm in it["names"] if nm not in e.get("omit3d", ())]
        if e.get("cut3d", True):
            shapes = cut_quarter(shapes, True)
        v = dict(dir=(1.0, -1.4, 0.7), up=(0, 0, 1))
        v.update(e.get("view3d", {}))
        if v.get("lay"):                                           # a tall assembly lies along x (side A to the right)
            shapes = [(rotated(sh, (0, 1, 0), -90.0), c) for sh, c in shapes]
        b3 = lay["box3d"]
        png = ctx["renderer"].png(shapes, os.path.join(ctx["tmp"], f"{e['dwg']}_3d.png"), view=v["dir"], up=v["up"],
                                  size=(int(b3[2] * 6.2), int((b3[3] - 8) * 6.2)))
    furniture(S, e, None, e.get("qty"), scale_txt(s), ctx["sheet_no"][e["dwg"]], ctx["n_sheets"])
    image_box(S, png, lay["box3d"], e.get("caption3d", "3-D view, a quarter cut away; the reference parts left out "
                                                    "(axonometric, not to scale)"))
    nx, ny, nw, nb = lay["notes"]
    rest = notes_block(S, e.get("notes", []), x=nx, y_top=(y - 3.0) if ny is None else ny, width_mm=nw, size=TXT * 0.9,
                       bottom=nb)
    if rest:
        print(f"  {e['dwg']}: {len(rest)} note lines did not fit", flush=True)
    out = ctx["out_pdf"](e["dwg"])
    S.fig.savefig(out)
    if ctx.get("preview"):
        S.fig.savefig(os.path.join(ctx["preview"], f"{e['dwg']}.png"), dpi=ctx.get("dpi", 110))
    plt.close(S.fig)
    e["_items"] = [dict(no=it["no"], label=it["label"], dwg=it["dwg"], qty=it["qty"]) for it in items]
    return out


def cut_quarter(shapes, spec=True):
    """the quarter toward the viewer cut away (x > 0, y < 0 by default)."""
    from OCP.BRepAlgoAPI import BRepAlgoAPI_Cut
    import tube_geometry as TG
    lo = np.min([bbox(s)[0] for s, _ in shapes], axis=0); hi = np.max([bbox(s)[1] for s, _ in shapes], axis=0)
    big = float(np.max(hi - lo)) + 10.0
    q = TG.box(0.0, hi[0] + big, lo[1] - big, 0.0, lo[2] - big, hi[2] + big)
    out = []
    for s, c in shapes:
        lo_, hi_ = bbox(s)
        if hi_[0] <= 0.0 or lo_[1] >= 0.0:
            out.append((s, c))
            continue
        try:
            r = BRepAlgoAPI_Cut(s, q).Shape()
        except Exception:
            out.append((s, c))
            continue
        try:
            bbox(r)                                                # a part wholly inside the quarter is gone
        except Exception:
            continue
        out.append((r, c))
    return out


def sheet_wiring(e, ctx):
    """deck A's wiring: every lead, strap and wire the model routes, with its net and its length."""
    M = ctx["model"]
    rows = []
    for p in M.m.parts:
        n = M.m.nets.get(p["name"])
        if not n or "path" not in n or not e["pred"](p):
            continue
        P = np.asarray(n["path"], float)
        Lw = float(np.sum(np.linalg.norm(P[1:] - P[:-1], axis=1)))
        mat = M.material(p["proto"])
        kind = "PTFE HV wire" if "PTFE HV wire" in mat else ("Cu strap" if "strap" in mat else
                                                              ("tinned Cu lead" if "tinned" in mat else mat[:20]))
        desc = p["label"].split(" - ", 1)[-1].split(" [")[0]
        rows.append((p["name"], n.get("net", "/".join(n.get("nets", []))), kind, f"{Lw:.0f}", desc))
    e["rows"] = rows
    e["cols"] = [("wire", 30.0), ("net", 12.0), ("kind", 26.0), ("mm", 11.0), ("from - to", 189.0)]
    e["heading"] = e.get("heading", "WIRING LIST")
    png = None
    if ctx["renderer"].ok:                                         # the wires in colour over the deck's parts in grey
        wires = {r[0] for r in rows}
        kind_col = {"PTFE HV wire": (0.93, 0.45, 0.10), "Cu strap": (0.80, 0.45, 0.25), "tinned Cu lead": (0.35, 0.35, 0.38)}
        shapes = []
        for p in M.m.parts:
            nm = p["name"]
            if nm in wires:
                shapes.append((M.placed(nm), kind_col.get(next(r[2] for r in rows if r[0] == nm), (0.2, 0.4, 0.8))))
            elif nm == "A_deck_plate" or (p.get("group") == "deck-A" and nm.startswith("A_")):
                shapes.append((M.placed(nm), (0.86, 0.86, 0.84) if "pot" not in p["proto"] else (0.90, 0.92, 0.93)))
        png = ctx["renderer"].png(shapes, os.path.join(ctx["tmp"], f"{e['dwg']}_3d.png"), view=(0.8, -1.2, -1.3),
                                  up=(0, 0, -1), size=(900, 620))
        e.setdefault("caption3d", "deck A from its parts' side: PTFE HV wire orange, straps copper, leads dark")
    return sheet_list(e, ctx, png)


def sheet_index(e, ctx, entries):
    S = begin(e, ctx)
    S.title(28.0, 280.0, "THE DRAWING SET: every sheet, in order")
    cols = [("no", 7.0), ("drawing", 21.0), ("title", 77.0), ("status", 16.0), ("qty", 13.0)]
    rows = [(ctx["sheet_no"][x["dwg"]], x["dwg"].replace("DCCREG-", ""), x["title"], x.get("status", ""),
             x.get("qty_index", x.get("qty")) or "") for x in entries]
    half = (len(rows) + 1) // 2
    sz, rh = (5.6, 3.95) if half <= 40 else (5.0, 3.3)                # a longer set in smaller rows
    y1 = table(S, 24.0, 274.0, cols, rows[:half], size=sz, row_h=rh, wrap_cols=())
    y2 = table(S, 162.0, 274.0, cols, rows[half:], size=sz, row_h=rh, wrap_cols=())
    png = e.get("still")
    return finish(S, e, ctx, None, "—", os.path.join(ROOT, png) if png else None, e.get("notes", []), e.get("data", ()),
                  caption3d=e.get("caption3d"), notes_box=dict(x=24.0, y_top=min(108.0, min(y1, y2) - 2.0), width_mm=202.0))


# ---------------------------------------------------------------------------------------------------------
# the registry: every sheet of the set
# ---------------------------------------------------------------------------------------------------------
AL = "Al EN AW-6082-T6 (the record: Al; the grade proposed [IR])"
G10 = "G10 glass-epoxy laminate, EP GC 201 (IEC 60893-3-2)"
PTFE = "PTFE, virgin (unfilled)"
SS = "austenitic stainless 1.4404 (316L), non-magnetic (μr ≤ 1.05)"
SIL = "silicone, two-part addition cure, vacuum-degassed; ≥ 20 kV/mm [IR]"
HV_RIMS = ("Every rim a full round R1.5 (t / 2), burr-free, Ra ≤ 0.8 µm: the record's rims are full rounds on a handled "
           "surface (Peek m 0.85, sim/vane-matrix-findings.md §2). Clean with IPA after the last operation; handle with "
           "gloves.")
FLAT = "Flatness 0.10 over the whole plate; parallelism of the faces 0.05: the 6 mm working gaps (sim/stack_sizing.py)."
GEN = "General tolerances ISO 2768-mK; dimensions in mm; do not scale. Views by hidden-line removal of the model's solids."
G10_MACH = ("G10 machined across the laminate where the drawing shows faces normal to z; seal every cut edge with "
            "low-viscosity epoxy (tracking along exposed fibres, presets/hub-locked.json shaft_coupler).")


def _nz(shape):
    lo, hi = tight_bbox(shape)
    return moved(shape, 0.0, 0.0, -lo[2])


def _nc(shape):
    lo, hi = tight_bbox(shape)
    c = 0.5 * (lo + hi)
    return moved(shape, -c[0], -c[1], -c[2])


def _axis_to_z(shape):
    """a part on a radial axis (the bushings) turned onto z, centred."""
    F = features(shape)
    q = max(F["radial"], key=lambda q: q["r"])
    th = math.degrees(math.atan2(q["d"][1], q["d"][0]))
    s = rotated(shape, (0, 0, 1), -th)
    s = rotated(s, (0, 1, 0), -90.0)
    lo, hi = tight_bbox(s)
    c = 0.5 * (lo + hi)
    return moved(s, -c[0], -c[1], -lo[2])


def proto(key, norm=_nz):
    return lambda M: norm(M.proto(key))


def drilled(key, holes):
    """the part's drawing solid with the holes the model leaves out (tapped holes, inserts' bores): holes
    [(r, z0, z1)] on the axis, in the part's own z from its lower face."""
    def make(M):
        import tube_geometry as TG
        from OCP.BRepAlgoAPI import BRepAlgoAPI_Cut
        s = _nz(M.proto(key))
        for r, z0, z1 in holes:
            s = BRepAlgoAPI_Cut(s, TG.cyl_z(0.0, 0.0, r, z0, z1)).Shape()
        return s
    return make


def module(keys_dz, turn=False):
    """a potted module: its body, potting and leads / studs as the model draws them (each (proto, dz)), on x."""
    def make(M):
        s = compound([moved(M.proto(k), 0.0, 0.0, dz) for k, dz in keys_dz])
        if turn:
            s = rotated(s, (0, 0, 1), -90.0)
        return _nc(s)
    return make


def entries(M):
    import doubler_caps as DC
    import bridge_ring_bearings as BRB
    import multiplier_layout as ML
    import stack_sizing as S
    p = M.m.p
    rel = p["rel"]
    pl = M.m.mounts
    q = lambda *keys: sum(M.count.get(k, 0) for k in keys)
    col = lambda k: M.colour(k)
    mat = lambda k: M.material(k)
    E = []

    def add(dwg, title, system, kind, make=None, key=None, material="", status="PROPOSED", notes=(), data=(), used_in="",
            source="", qty=None, **kw):
        e = dict(dwg=f"DCCREG-{dwg}", title=title, system=system, kind=kind, make=make, material=material, status=status,
                 notes=list(notes) + ([GEN] if kind in ("turned", "block") else []), data=list(data),
                 used_in=used_in, source=source, qty=qty, **kw)
        if key:
            e.setdefault("model_material", mat(key))
            e.setdefault("colour", col(key))
        E.append(e)
        return e

    add("DS-000", "Index of the drawing set", "the drawing set", "index", status="PROPOSED",
        still="docs/geometry/tube/tube-r150-n6-air6-wound-g0p5-6br-hub50-layout-3d-cutaway.png",
        caption3d="the machine as the set draws it (the layout, quarter cut)",
        notes=["The set draws the machine as sim/tube_geometry.py LayoutMachine builds it (1014 mm; 552 solids from 168 "
               "prototypes): the record's locked design, the multiplier's layout (PROPOSED, sim/multiplier-layout-findings.md), "
               "the bridge-ring bearings (PROPOSED, sim/bridge-ring-bearings-findings.md) and the capacitors' mounts "
               "(PROPOSED, sim/doubler-caps-findings.md).",
               "Status per sheet: LOCKED, the record's locked design (docs/ledger/DCCREG-design-ledger.md); PROPOSED, a "
               "proposal for the designer to accept; BOUGHT, a source-control sheet for a bought part.",
               "Every sheet is Rev A, a draft for quotation: the drawings are generated from the solids and are to be "
               "checked and approved before release. Side B's parts are side A's mirror or the same part, as each sheet "
               "states.",
               "The proposed parts the layout's model does not carry are drawn from their first cuts (sim/unmodelled_parts.py): "
               "the magnetic pump's chokes, kick and electronics (REL-720 to REL-730, P-016 to P-019; their places on the "
               "rotor OPEN) and the drive (DRV-100 to DRV-190, P-012 to P-015; on the record's 940 mm stack-up, to be re-cut "
               "on the layout: ledger §6, item 71).",
               "Not drawn: the screws, studs and inserts (sheets P-011 and DRV-190 list them), the gel, the potting moulds, "
               "the frame (the base plate, the columns, the top plate: placeholders in docs/drive-gear-belt.md §9)."],
        data=[("sheets", "the index and every drawing below"), ("model", "docs/geometry/tube/…-layout.step"),
              ("generator", "docs/make_drawing_set.py")])
    add("GA-001", "General arrangement", "the whole machine", "assembly", status="PROPOSED", qty=1, layout="tall",
        view3d=dict(lay=True, dir=(0.3, -1.4, 0.9)),
        window=(-190.0, 190.0, -5.0, 1019.0), planes=[(0.0, "full")], label="SECTION A–A, the machine through the shaft",
        groups=lambda M: GA_GROUPS, source="sim/tube_geometry.py LayoutMachine",
        notes=["The machine stands on its axis, side B above. z from side A's end; the hub's centre at z 507; 1014 mm "
               "(sim/bridge_ring_bearings.py placement).",
               "Two bodies: the rotor (the shaft, the hub, the decks, Ca / Cb, the rotor vanes, the utrons) and the "
               "counter-rotor (the cage, the stator vanes, the spiders, the bridges and bridge rings), geared 1 : -1.",
               "The balloons name the sub-assemblies; each has its own sheet. The drive (DRV-100, DRV-120) is not placed "
               "here: its first cut stands on the record's 940 mm stack-up (ledger §6, item 71)."])
    E[-1]["groups"] = None                                           # filled once GA_GROUPS is known (below)

    # ---------------- the hub
    add("HUB-200", "Hub, locked, in its coupler", "the hub", "assembly", status="LOCKED", qty=1,
        window=(-60.0, 60.0, 507.0 - 88.0, 507.0 + 88.0), planes=[(0.0, "full")],
        groups=lambda M: [("vessel, borosilicate", "HUB-202", "borosilicate 3.3", lambda n, k: k == "hub_vessel"),
                          ("ring A / ring B, Cu foil bands", "HUB-201", "Cu-ETP 0.1 mm", lambda n, k: k.startswith("hub_ring")),
                          ("beads, Cu wire rings", "HUB-201", "Cu-ETP", lambda n, k: k.startswith("hub_bead")),
                          ("interface gel, 0.5 mm", "—", "silicone gel", lambda n, k: k == "hub_gel"),
                          ("retainer", "HUB-203", "PEEK", lambda n, k: k == "hub_retainer"),
                          ("shaft coupler", "HUB-204", "G10", lambda n, k: k == "hub_coupler"),
                          ("AH core", "P-007", "77 MnZn", lambda n, k: k.startswith("ah_core")),
                          ("AH former", "HUB-205", "G-10", lambda n, k: k.startswith("ah_former")),
                          ("AH coil", "HUB-206", "Cu", lambda n, k: k.startswith("ah_coil")),
                          ("shaft-half flange", "SHF-303", "1.4404", lambda n, k: k == "flange_lv")],
        source="presets/hub-locked.json; docs/rings-design.md §2",
        notes=["Build order: the rings and beads on the vessel (HUB-201); the vessel in the retainer's pocket, the gel "
               "vacuum-cast 0.5 mm into it (presets/hub-locked.json interface_filler); the AH cores and coils in their "
               "seats; the coupler bonded over the retainer and both flanges.",
               "The flanges are turned to Ø60 to sit in the coupler's bore (docs/rings-design.md §2); bonded and pinned.",
               "The rings' leads leave through the coupler's channels to the can's bushings (CAN-400)."])
    add("HUB-202", "Vessel, borosilicate, Ø50 × 1.5", "the hub", "turned", proto("hub_vessel"), "hub_vessel",
        material="borosilicate glass 3.3 (DIN ISO 3585), annealed", status="LOCKED", qty=q("hub_vessel"),
        used_in="HUB-200", source="presets/hub-locked.json vessel, vessel_wall", long=True,
        callouts=[("section", (17.68, 42.68), "SØ50 ±0.1", (0.6, 1.0)),
                  ("section", (0.0, 0.75), "wall 1.5 ±0.1", (-1.0, 0.6))],
        notes=["A sphere, OD 50 ±0.1, wall 1.5 ±0.1, evacuated and sealed: the seal-off tip ground flush at a pole "
               "(the designer's, to agree with the glassblower).",
               "Inside: vacuum ≤ 1e-4 mbar. The shell's stress under vacuum is about 0.8 MPa (presets/hub-locked.json).",
               "The outer surface carries rings A and B (HUB-201): keep it clean and free of scratches."])
    add("HUB-203", "Retainer, PEEK", "the hub", "turned", proto("hub_retainer"), "hub_retainer",
        material="PEEK, unfilled (natural, Victrex 450G class), machined from annealed stock", status="PROPOSED",
        qty=q("hub_retainer"), used_in="HUB-200", source="presets/hub-locked.json retainer; docs/rings-design.md §2", long=True,
        notes=["Its role and material are DECIDED (the designer, 2026-10-09); its grooves and dimensions are the first cut "
               "of docs/rings-design.md §2 (PROPOSED).",
               "The pocket holds the vessel with 0.5 mm all round for the gel, with the beads' grooves; the AH seats at "
               "|z| 25-30.7; the rings' lead channels as drawn.",
               "Anneal after rough machining; finish-machine the pocket and the seats; keep HV surface paths off it (its "
               "CTI is 150, group IIIb: sim/parts-first-cut-findings.md §4)."])
    add("HUB-204", "Shaft coupler, G10 tube 60 / 66", "the hub", "turned", proto("hub_coupler"), "hub_coupler",
        material=G10 + ", tube", status="PROPOSED", qty=q("hub_coupler"), used_in="HUB-200",
        source="presets/hub-locked.json shaft_coupler; docs/rings-design.md §2", long=True,
        notes=["A straight tube, Ø60 / Ø66, |z| ≤ 80: bonded over the PEEK retainer and over both shaft flanges "
               "(PROPOSED first cut, presets/hub-locked.json).",
               "Outside the retainer only: never against the glass or the rings (DECIDED).", G10_MACH])
    add("HUB-205", "AH former, G-10", "the hub", "turned", proto("ah_former_A"), "ah_former_A", material=G10 + ", tube",
        status="LOCKED", qty=q("ah_former_A", "ah_former_B"), used_in="HUB-200",
        source="presets/hub-locked.json AH (presets/electromagnets-RA.json AH_former)", long=True,
        notes=["ID 13.5, OD 16.5 over the core (Fair-Rite 4077484611, Ø12.3, P-007); side A's and side B's are the same "
               "part.", G10_MACH])
    add("HUB-206", "AH coil, 160 turns", "the hub", "turned", proto("ah_coil_A"), "ah_coil_A",
        material="Cu magnet wire, grade 2 (IEC 60317), impregnated", status="LOCKED", qty=q("ah_coil_A", "ah_coil_B"),
        used_in="HUB-200", source="presets/hub-locked.json AH; sim/ah_winding.py", long=True,
        notes=["160 turns on the former HUB-205, as sim/ah_winding.py winds it; the leads to the shaft's LV bore (the LV "
               "cable, P-010).", "Impregnate (VPI, class F) after winding; the envelope as drawn is the winding's."])

    # ---------------- the shaft halves
    def shaft_groups(s_):
        return lambda M: [(f"shaft half {s_}", "SHF-301" if s_ == "A" else "SHF-302", "1.4404", lambda n, k: n == f"shaft_{s_}"),
                          ("shaft-half flange", "SHF-303", "1.4404", lambda n, k: n == f"{s_}_flange"),
                          ("rotor sleeve, vane bay", "SHF-304", "G10", lambda n, k: n == f"{s_}_rotor_sleeve_vanes"),
                          ("rotor sleeve, reluctance bay", "SHF-305", "G10", lambda n, k: n == f"{s_}_rotor_sleeve_rel"),
                          ("PTFE cover", "SHF-306", "PTFE", lambda n, k: n == f"{s_}_sleeve_cover"),
                          ("PTFE shed", "SHF-307", "PTFE", lambda n, k: n.startswith(f"{s_}_shed")),
                          ("LV cable", "P-010", "—", lambda n, k: n == f"{s_}_lv_cable")]
    add("SHF-300", "Shaft half A with its flange, sleeves and sheds", "the shaft", "assembly", status="PROPOSED", qty=1,
        layout="wide", view3d=dict(lay=True, dir=(0.3, -1.4, 0.9)),
        window=(-40.0, 40.0, -2.0, 430.0), planes=[(0.0, "full")], horizontal=True, groups=shaft_groups("A"),
        label="SECTION A–A (z to the right)", source="sim/tube_geometry.py LayoutMachine; sim/multiplier-layout-findings.md §7",
        notes=["Side B's is the mirror (SHF-302 and side B's sleeves). The sleeves are bonded on the shaft; the cover and "
               "sheds bonded on the vane bay's sleeve.",
               "The LV cable runs in the 8 mm bore from the flange's face to the radial exit at |z| 306 from the hub "
               "(sim/multiplier-layout-findings.md §7)."])
    for s_, dwg in (("A", "SHF-301"), ("B", "SHF-302")):
        add(dwg, f"Shaft half {s_}, Ø25, its LV bore", "the shaft", "turned", proto(f"shaft_{s_}"), f"shaft_{s_}", material=SS,
            status="PROPOSED", qty=q(f"shaft_{s_}"), used_in="SHF-300", long=True,
            source="sim/stack_sizing.py SHAFT_R; sim/tube_geometry.py LayoutMachine (LV_BORE, LV_EXIT)",
            notes=["Ø25 as the model draws it (sim/stack_sizing.py SHAFT_R 12.5); presets/hub-locked.json registers d 30. "
                   "The shafts' study passes at d 25 (f1 81-86 Hz, sim/doubler-caps-findings.md §6): the designer's to settle.",
                   "Bearing seats Ø25 k5 at the three bearings' places (the Ca|reluctance, the bridge-ring and the end "
                   "bearing, SKF 6205-2Z, P-001); the rest Ø25 h9.",
                   "The LV bore Ø8 from the flange's end to the radial exit Ø8; deburr both, no sharp edge for the cable.",
                   "Non-magnetic: check μr ≤ 1.05 after machining (the utrons' field)."])
    add("SHF-303", "Shaft-half flange, Ø60 × 8", "the shaft", "turned", proto("flange_lv"), "flange_lv", material=SS,
        status="PROPOSED", qty=q("flange_lv"), used_in="SHF-300, HUB-200",
        source="presets/hub-locked.json shaft (flange_absz 72-80); docs/rings-design.md §2",
        notes=["Turned to Ø60 to sit in the coupler's bore; butt-welded to its shaft half's end and turned true after "
               "welding [IR]; the LV bore Ø8 through both."])
    add("SHF-304", "Rotor sleeve, the vane bay, G10", "the shaft", "turned", proto("sleeve_vanes"), "sleeve_vanes",
        material=G10 + ", tube", status="PROPOSED", qty=q("sleeve_vanes"), used_in="SHF-300, CAP-600", long=True,
        source="sim/stack_sizing.py SLEEVE_R; sim/multiplier_layout.py stack (h 87-281.5)",
        notes=["Ø25 H7 bore on the shaft, Ø41 g6 for the rotor vanes and their spacer rings (CAP-600).",
               "8 mm of G10 between node 1's vane rings and the shaft: 0.53 pF per mm (sim/tube-strays-findings.md §3).",
               G10_MACH])
    add("SHF-305", "Rotor sleeve, the reluctance bay, G10 (A; B mirror)", "the shaft", "turned", proto("sleeve_rel_A"),
        "sleeve_rel_A", material=G10 + ", tube", status="PROPOSED", qty=q("sleeve_rel_A", "sleeve_rel_B"),
        used_in="SHF-300, REL-710", long=True, source="sim/tube_geometry.py LayoutMachine (LV_EXIT)",
        notes=["The LV cable's radial exit Ø8 as drawn; side B's is the mirror.", G10_MACH])
    add("SHF-306", "PTFE cover over the sleeve", "the shaft", "turned", proto("sleeve_cover"), "sleeve_cover", material=PTFE,
        status="PROPOSED", qty=q("sleeve_cover"), used_in="SHF-300", long=True,
        source="sim/multiplier-layout-findings.md §4; sim/doubler-caps-findings.md §2",
        notes=["84 mm of PTFE creepage from the can's disc to the first rotor vane (61.7 mm needed at 9.87 kV rms, "
               "PD2 group I × 1.25).", "Bonded on the sleeve (etched PTFE, epoxy); no node-1 metal may touch it."])
    add("SHF-307", "PTFE shed, Ø65 × 2", "the shaft", "turned", proto("shed"), "shed", material=PTFE, status="PROPOSED",
        qty=q("shed"), used_in="SHF-300", source="sim/multiplier-layout-findings.md §4",
        notes=["Two on each sleeve's outer end give 65.5 mm of creepage from the last rotor vane to the Ca|reluctance "
               "bearing.", "Bonded on the sleeve (etched PTFE)."])

    # ---------------- the can
    thA, thB = (math.degrees(math.atan2(*(0.5 * (bbox(M.placed(n))[0] + bbox(M.placed(n))[1]))[1::-1]))
                for n in ("A_bushing", "B_bushing"))
    add("CAN-400", "Can over the hub, with its end discs and bushings", "the can", "assembly", status="PROPOSED", qty=1,
        window=(-62.0, 62.0, 507.0 - 92.0, 507.0 + 92.0), planes=[(thA, "right"), (thB, "left")],
        label=f"SECTION A–A: right through ring A's bushing ({thA:.0f}°), left through ring B's ({thB:.0f}°)",
        groups=lambda M: [("can", "CAN-401", "Al", lambda n, k: k == "can"),
                          ("end disc", "CAN-402", "Al", lambda n, k: k == "can_disc_m"),
                          ("PTFE bushing", "CAN-403", "PTFE", lambda n, k: k.startswith("bushing")),
                          ("the hub (for reference)", "HUB-200", "—", lambda n, k: k.startswith(("hub_", "ah_"))),
                          ("shaft halves (for reference)", "SHF-301/-302", "—", lambda n, k: k.startswith("shaft_"))],
        source="sim/multiplier-layout-findings.md §5", notes=[
            "The can is REF: Al r 46-48, |z| ≤ 85, its end discs on the shaft; it is the hub's REF boundary "
            "(sim/multiplier-layout-findings.md §5).",
            "Each ring's lead leaves through its PTFE bushing toward its deck's Csa / Csb."])
    add("CAN-401", "Can, Al, Ø96 × 2 × 170", "the can", "turned", proto("can"), "can", material=AL + ", tube",
        status="PROPOSED", qty=q("can"), used_in="CAN-400", long=True, source="sim/multiplier_layout.py CAN_R, CAN_T, CAN_Z",
        notes=["The two radial holes take the rings' lead bushings (CAN-403) at |z| 57, toward each deck's Csa / Csb.",
               "Inside and outside edges rounded R1; the surface clean (REF, the hub's boundary)."])
    add("CAN-402", "Can end disc, three M4 holes", "the can", "turned", proto("can_disc_m"), "can_disc_m", material=AL,
        status="PROPOSED", qty=q("can_disc_m"), used_in="CAN-400, CAP-610", source="sim/doubler_caps.py placement (the standoffs)",
        notes=["On the shaft (Ø25 H7), bonded to the can. The three M4 holes take node 2's steatite standoffs (CAP-617) "
               "with button-head screws from inside the can.",
               "Side B's is the same part, turned to its side's angles."])
    add("CAN-403", "PTFE bushing, the ring's lead", "the can", "turned", lambda M: _axis_to_z(M.proto("bushing_A")), "bushing_A",
        material=PTFE, status="PROPOSED", qty=q("bushing_A", "bushing_B"), used_in="CAN-400",
        source="sim/tube_geometry.py BUSH", long=True,
        notes=["Pressed into the can's hole; the lead's PTFE insulation runs through it unbroken (≥ 30 kV DC, "
               "docs/rings-design.md §3)."])
    deck_entries(add, M, q, col, mat)
    cap_entries(add, M, q, col, mat, pl, p)
    rel_entries(add, M, q, col, mat, rel)
    pump_parts_entries(add)
    brg_entries(add, M, q, col, mat)
    drive_entries(add)
    bought_entries(add, M, q, col, mat)
    bought_extra_entries(add)
    for e in E:
        if e["dwg"] == "DCCREG-GA-001":
            e["groups"] = lambda M: GA_GROUPS
    return E


def deck_entries(add, M, q, col, mat):
    import multiplier_layout as ML
    P = ML.PART
    deck = lambda n, k: n.startswith("A_") and M.by_name[n]["group"] == "deck-A"
    U = module_unit
    add("DCK-500", "Deck A, its parts potted on the G10 plate", "deck A (deck B the mirror)", "assembly", status="PROPOSED",
        qty=2, window=(-162.0, 162.0, -162.0, 162.0), planes=[("z", 507.0 - 48.0, "plan")],
        view3d=dict(dir=(0.8, -1.2, -1.1), up=(0, 0, -1)),
        label="PLAN, the cut at |z| 48 (the sticks' axis), seen from +z",
        groups=lambda M: [("deck plate", "DCK-502", "G10", lambda n, k: n == "A_deck_plate"),
                          ("rectifier stick module (D1 D3 D5 D8 D11 D12)", "DCK-504", "2CL77 + silicone",
                           lambda n, k: deck(n, k) and k.startswith("stick"), U),
                          ("surge resistor module (R1 R3)", "DCK-505", "22 kΩ + silicone",
                           lambda n, k: deck(n, k) and k.startswith("rsurge"), U),
                          ("capacitor module C3 / C6", "DCK-506", "190 pF + silicone", lambda n, k: deck(n, k) and k.startswith("c180"), U),
                          ("capacitor module C8", "DCK-507", "100 pF + silicone", lambda n, k: deck(n, k) and k.startswith("c100_"), U),
                          ("capacitor module Csa", "DCK-508", "100 pF + silicone", lambda n, k: deck(n, k) and k.startswith("c100h"), U),
                          ("screw terminals of the capacitors", "P-003 / P-004", "brass", lambda n, k: deck(n, k) and k == "stud"),
                          ("clamp string module Z1", "DCK-509", "66 × 1.5KE200A + silicone",
                           lambda n, k: deck(n, k) and k.startswith("clamp"), U),
                          ("junction terminal and block", "DCK-503", "brass + silicone", lambda n, k: deck(n, k) and k.startswith("j_"), U),
                          ("leads, straps and wires", "DCK-501", "Cu / PTFE HV wire", lambda n, k: deck(n, k)),
                          ("the can (for reference)", "CAN-401", "—", lambda n, k: n == "can")],
        source="sim/multiplier_layout_results.json decks.A (the plan); sim/multiplier-layout-findings.md §3",
        notes=["Each part sits in the study's plan: the sticks along the outer lane r 132, the others as placed; every "
               "part potted, 8 mm of silicone over it (sim/parts-first-cut-findings.md §5).",
               "Deck B is the mirror about -21.3° (sim/multiplier_layout.py MIRROR, PART_MIRROR): D2 for D1 and so on.",
               "The plate is bonded on the can's outside, |z| 30-36 (sim/multiplier_layout.py DECK_Z0, DECK_T); its two "
               "6 mm holes pass the cross nets l1 / r1 to deck B.",
               "Pot the deck as one: the junctions' blocks, the leads over the parts and the straps to the can inside "
               "the same pour; no void (vacuum-cast, then pressure-cure)."])
    add("DCK-501", "Deck A wiring list", "deck A (deck B the mirror)", "wiring", status="PROPOSED", qty=2,
        pred=lambda p: p["name"].startswith("A_") and (p["group"] in ("deck-A",) or p["name"] in ("A_riser", "A_tap",
                                                       "A_ring_lead", "A_cross_l1", "A_cross_r1")) or p["name"] in ("cross_l1", "cross_r1"),
        used_in="DCK-500", source="sim/tube_geometry.py LayoutMachine.decks (sim/multiplier_layout.py LEADS_A, STRAPS_A)",
        heading="WIRING LIST: every lead, strap and wire of deck A as the model routes it (net; length along its path)",
        notes=["Tinned Cu leads (1.2 mm) inside the potting; PTFE HV wire (UL3239 class, ≥ 20 kV DC, P-009) for the leads "
               "over the parts, the riser, the tap and the cross nets; ≥ 30 kV DC for the ring's lead (docs/rings-design.md §3).",
               "Two leads on one junction land 2.5 mm either side of its centre, along the lane.",
               "Deck B's list is the mirror: nets 1 → 4, 2 → 3, l1 ↔ r1, l2 ↔ r2, xa → xb, ea → eb."])
    add("DCK-502", "Deck plate, G10, r 50-150 × 6", "deck A / deck B", "turned", proto("deck_plate"), "deck_plate",
        material=G10 + ", plate 6 mm", status="PROPOSED", qty=q("deck_plate"), used_in="DCK-500",
        source="sim/multiplier_layout.py DECK_R0, DECK_R1, DECK_T", detail=(46.0, 66.0),
        notes=["The two Ø6 holes pass the cross nets l1 and r1 (deck A's junctions; deck B's sit over them).",
               "Bonded on the can; the parts' face is the outer (+|z|) face.", G10_MACH])
    add("DCK-503", "Junction terminal in its potted block", "deck A / deck B", "turned",
        lambda M: _nz(compound([M.proto("j_cond"), M.proto("j_pot")])), "j_pot", material="brass CuZn39Pb3 terminal; " + SIL,
        status="PROPOSED", qty=q("j_cond"), used_in="DCK-500", source="sim/tube_geometry.py J_COND, J_POT [RH]", long=True,
        mass_kg=1e-9 * (volume(M.proto("j_cond")) * density("brass") + volume(M.proto("j_pot")) * density("silicone potting")),
        model_material="brass", notes=["The terminal Ø10 × 12 (brass) in a potted block Ø20 × 24; its outer face takes the "
                                       "leads over the parts [RH: the envelope]."])
    for dwg, title, keys, kind, turn, label, src in (
            ("DCK-504", "Module: HV rectifier stick, potted", [("stick_body", 0), ("stick_pot", 0), ("stick_lead_neg", 0),
                                                               ("stick_lead_pos", 0)], "stick", True, "D1-D12", "P-002"),
            ("DCK-505", "Module: surge resistor, potted", [("rsurge_body", 0), ("rsurge_pot", 0), ("rsurge_lead_neg", 0),
                                                           ("rsurge_lead_pos", 0)], "rsurge", True, "R1-R4", "P-005"),
            ("DCK-506", "Module: capacitor C3-C6, potted", [("c180_body", 0), ("c180_pot", 0), ("stud", 15.0), ("stud", -15.0)],
             "c180", False, "C3-C6", "P-003"),
            ("DCK-507", "Module: capacitor C7 / C8, potted", [("c100_body", 0), ("c100_pot", 0), ("stud", 14.0), ("stud", -14.0)],
             "c100", False, "C7, C8", "P-004"),
            ("DCK-508", "Module: capacitor Csa / Csb, potted", [("c100h_body", 0), ("c100h_pot", 0), ("stud", 16.0),
                                                                ("stud", -16.0)], "c100h", False, "Csa, Csb", "P-004"),
            ("DCK-509", "Module: clamp string Z1 / Z4, potted", [("clamp_body", 0), ("clamp_pot", 0), ("clamp_lead_0", 0),
                                                                 ("clamp_lead_1", 0)], "clamp", False, "Z1, Z4", "P-006")):
        body = keys[0][0]
        d = P[kind]
        sil = volume(M.proto(keys[1][0])) * 1e-9 * density("silicone potting")
        add(dwg, title, "deck A / deck B", "block", module(keys, turn), body, material=f"{label}: the part ({src}) in " + SIL,
            status="PROPOSED", qty=q(body), used_in="DCK-500", model_material="silicone potting", rho=None,
            source="sim/multiplier_layout.py PART, POT (the envelopes [RH]); sim/parts-first-cut-findings.md §5",
            notes=[f"The part: {d['what']}.",
                   "8 mm of void-free silicone over the part all round (13.2 kV class, sim/parts-first-cut-findings.md §5): "
                   "vacuum-cast in a mould to the envelope drawn, then pressure-cured.",
                   "The envelope is the layout's [RH]; take the real part's from its source-control sheet and keep the "
                   "8 mm.",
                   "The leads leave the potting where drawn; their insulation (or the potting) unbroken to the deck's pour."],
            mass_kg=None,
            data=[("parts", label), ("body", f"Ø{d.get('body_d', d.get('body_w', 0)):g} × {d.get('body_l', 0):g}" if kind != "clamp"
                                     else f"{d['body_w']:g} × {d['body_l']:g} × {d['body_h']:g}"),
                  ("silicone each", f"{sil:.3g} kg: the pour as drawn at {density('silicone potting') / 1e3:g} g/cm³ "
                                    "(sim/bridge_ring_bearings.py RHO_LAYOUT); the part's own mass on its sheet")])


def cap_entries(add, M, q, col, mat, pl, p):
    import doubler_caps as DC
    n_sec = int(p["N_sec"] / 2)
    sA = pl["sides"]["A"]
    zc = M.m.zc
    hA = lambda h: zc - h
    rotor = lambda n, k: k in ("rotor_vane_m",) or k.startswith("rotor_vane_end")
    add("CAP-600", "C1 / C2 varicap stack, side A", "the doubler: C1 / C2", "assembly", status="PROPOSED", qty=2,
        window=(-190.0, 190.0, hA(302.0), hA(162.0)), planes=[(0.0, "right"), (210.0, "left")], horizontal=True,
        label="SECTION A–A (z across): above at 0° (the blades), below at 210° (a tie rod, a dowel)",
        groups=lambda M: [("rotor vane, first (r01)", "CAP-602", "Al", lambda n, k: n == "A_C1_r01"),
                          ("rotor vane (r03-r11)", "CAP-601", "Al", lambda n, k: n.startswith("A_C1_r")),
                          ("stator vane (s02-s12)", "CAP-603", "Al", lambda n, k: n.startswith("A_C1_s")),
                          ("rotor-vane spacer ring", "CAP-604", "G10", lambda n, k: n.startswith("A_vane_spacer")),
                          ("dowel", "CAP-605", "G10", lambda n, k: n.startswith("A_dowel")),
                          ("stator spacer tube", "CAP-606", "G10", lambda n, k: n.startswith("A_stator_spacer")),
                          ("tie rod M8", "P-008", "glass-epoxy", lambda n, k: n.startswith("A_tie_rod")),
                          ("nut M8", "P-008", "glass-epoxy", lambda n, k: n.startswith("A_rod_nut")),
                          ("end ring", "CAP-607", "G10", lambda n, k: n == "A_end_ring"),
                          ("Ca|reluctance spider", "BRG-810", "G10", lambda n, k: n == "A_spider_Ca-reluctance"),
                          ("Ca|reluctance bearing", "P-001", "—", lambda n, k: n == "A_bearing_Ca-reluctance"),
                          ("rotor sleeve, sheds (for reference)", "SHF-304/-307", "—",
                           lambda n, k: n in ("A_rotor_sleeve_vanes", "A_shed_1", "A_shed_2")),
                          ("cage (for reference)", "CGE-901", "—", lambda n, k: n == "stator_cage"),
                          ("shaft (for reference)", "SHF-301", "—", lambda n, k: n == "shaft_A")],
        source="sim/doubler_caps.py placement; sim/doubler-caps-findings.md §1",
        notes=["Rotor: the six rotor vanes and five G10 spacer rings bonded on the sleeve, aligned by three G10 dowels "
               "(90°, 210°, 330°); r01 carries the node-1 comb's posts (CAP-610).",
               "Counter-rotor: the six stator vanes on six glass-epoxy tie rods M8 at r 173 with G10 spacer tubes, from the "
               "end ring (bonded in the cage's bore) to the Ca|reluctance spider; nuts finger-tight + 1/4 turn [IR].",
               "The gaps: 6 mm between every rotor and stator vane (gauge them at the six blades); the rims 12 mm or more "
               "from any G10 (sim/doubler-caps-findings.md §2).",
               "Side B (C2) is the mirror, its stator vanes in phase with C1's."])
    blades = [(140.0, -11.0, 11.0, f"{p['wr_deg']:g}°"), (118.0, 0.0, 60.0, "60°")]
    add("CAP-601", "Rotor vane, C1 / C2 (r03-r11)", "the doubler: C1 / C2", "turned", proto("rotor_vane_m"), "rotor_vane_m",
        material=AL + ", plate 3.0", status="PROPOSED", qty=q("rotor_vane_m"), used_in="CAP-600", angles=blades,
        detail=(14.0, 58.0), source="sim/stack_sizing.py (the record's vane); sim/doubler_caps.py (the dowels)",
        notes=[f"{n_sec} blades of {p['wr_deg']:g}° on a 60° pitch, r 50-150, on the hub ring r 20.5-50 (node 1 / 4).",
               "Three dowel holes Ø5 H7 at r 26.25 (90°, 210°, 330°) for the stack's alignment.", HV_RIMS, FLAT,
               "Laser- or waterjet-cut, then the rims rounded (CNC or tumble and hand-finish)."],
        data=[("node", "1 (C1) / 4 (C2)"), ("holds", "13.2 kV pk to the stator vanes")])
    add("CAP-602", "Rotor vane, the first (r01), hands A / B", "the doubler: C1 / C2", "turned", proto("rotor_vane_end_A"),
        "rotor_vane_end_A", material=AL + ", plate 3.0", status="PROPOSED", qty=q("rotor_vane_end_A", "rotor_vane_end_B"),
        used_in="CAP-600, CAP-610", angles=blades, detail=(14.0, 58.0),
        source="sim/doubler_caps.py placement (the node-1 comb's posts)",
        notes=["As CAP-601, with the node-1 comb's three posts: M4 countersunk (ISO 10642, 90°) from the outer face, at r 35.",
               f"Hand A (drawn): the posts at {sA['theta_n1_deg'][0]:.1f}°, {sA['theta_n1_deg'][1]:.1f}°, "
               f"{sA['theta_n1_deg'][2]:.1f}° (the blades at 0° + 60° k). Hand B: at "
               + ", ".join(f"{a:.1f}°" for a in pl["sides"]["B"]["theta_n1_deg"]) + " (side B's riser at -88.9°).",
               HV_RIMS, FLAT])
    add("CAP-603", "Stator vane with its six lugs, C1 / C2", "the doubler: C1 / C2", "turned", proto("stator_vane_m"),
        "stator_vane_m", material=AL + ", plate 3.0", status="PROPOSED", qty=q("stator_vane_m"), used_in="CAP-600",
        angles=[(140.0, -11.0, 11.0, f"{p['ws_deg']:g}°"), (176.0, 0.0, 30.0, "30°")], detail=(136.0, 166.0),
        callouts=[("plan", (0.0, 182.0), "6× lug R9, outer arc Ø364 (the cage's bore)", (0.55, 1.0))],
        source="sim/stack_sizing.py (the record's vane, its ring r 150-162); sim/doubler_caps.py (the lugs)",
        notes=[f"{n_sec} blades of {p['ws_deg']:g}° on a 60° pitch, r 50-150, on the ring r 150-162 (REF, the counter-rotor).",
               "Six lugs at 30° + 60° k to r 182 (the cage's bore), each with a Ø8.5 hole at r 173 for a tie rod.",
               "The lugs' outer arcs fit the cage's bore Ø364 H9: they locate the vane.", HV_RIMS, FLAT],
        data=[("node", "REF (the counter-rotor)")])
    add("CAP-604", "Rotor-vane spacer ring, G10", "the doubler: C1 / C2", "turned", proto("vane_spacer"), "vane_spacer",
        material=G10, status="PROPOSED", qty=q("vane_spacer"), used_in="CAP-600", detail=(18.0, 34.0),
        source="sim/doubler_caps.py VSP_R1, DOWEL",
        notes=["Between two rotor vanes' hub rings (both node 1): 15.00 ±0.02 long sets their 18 mm pitch.",
               "Its OD stays 18 mm inside the stator blades' inner ends (r 50).", "Bonded to the vanes and the sleeve.", G10_MACH])
    add("CAP-605", "Dowel, G10, Ø5 × 93", "the doubler: C1 / C2", "turned", proto("dowel"), "dowel", material=G10 + ", rod",
        status="PROPOSED", qty=q("dowel"), used_in="CAP-600", long=True, source="sim/doubler_caps.py DOWEL",
        notes=["Ø5 h6 ground; chamfer both ends 0.5 × 45°."])
    add("CAP-606", "Stator spacer tube, G10, Ø16 / 8.5 (-01 × 15, -02 × 12)", "the doubler: C1 / C2", "turned",
        proto("stator_spacer_15"), "stator_spacer_15", material=G10 + ", tube", status="PROPOSED",
        qty=q("stator_spacer_15", "stator_spacer_12"), used_in="CAP-600", long=True, source="sim/doubler_caps.py SSP_D",
        notes=["-01: length 15.00 ±0.02 between two stator vanes (60 per machine); -02: length 12.00 ±0.02 from the last "
               "vane to the spider (12 per machine). The view draws -01.", "Faces square to the bore within 0.02.", G10_MACH])
    add("CAP-607", "End ring, G10, in the cage's bore", "the doubler: C1 / C2", "turned", proto("end_ring"), "end_ring",
        material=G10, status="PROPOSED", qty=q("end_ring"), used_in="CAP-600, CGE-900", detail=(160.0, 186.0),
        source="sim/doubler_caps.py END_RING",
        notes=["Bonded in the cage's bore, its upper face 0.00 / -0.05 from the first stator vane's seat.",
               "Six Ø8.5 holes at r 173 for the tie rods; the nuts below it.", G10_MACH])
    # the column
    add("CAP-610", "Ca / Cb column, side A: the two combs on their posts", "the doubler: Ca / Cb", "assembly",
        status="PROPOSED", qty=2, window=(-165.0, 165.0, hA(182.0), hA(80.0)),
        planes=[(sA["theta_n1_deg"][0], "right"), (sA["theta_n2_deg"][0], "left")],
        label=f"SECTION A–A: right at {sA['theta_n1_deg'][0]:.1f}° (a node-1 post), left at "
              f"{sA['theta_n2_deg'][0]:.1f}° (a node-2 post)",
        groups=lambda M: [("Ca plate, node-2 base (Ca_06)", "CAP-615", "Al", lambda n, k: n == "A_Ca_06"),
                          ("Ca plate, node-1 end (Ca_05)", "CAP-612", "Al", lambda n, k: n == "A_Ca_05"),
                          ("Ca plate, node-2 (Ca_04)", "CAP-613", "Al", lambda n, k: n == "A_Ca_04"),
                          ("Ca plate, node-1 (Ca_03, Ca_01)", "CAP-611", "Al", lambda n, k: n in ("A_Ca_03", "A_Ca_01")),
                          ("Ca plate, node-2 end (Ca_02)", "CAP-614", "Al", lambda n, k: n == "A_Ca_02"),
                          ("post spacer Ø8 (node 1)", "CAP-616", "Al", lambda n, k: n.startswith("A_post1")),
                          ("post spacer Ø8 (node 2)", "CAP-616", "Al", lambda n, k: n.startswith("A_post2")),
                          ("steatite standoff", "CAP-617", "steatite C 221", lambda n, k: n.startswith("A_standoff")),
                          ("can end disc", "CAN-402", "Al", lambda n, k: n == "A_can_disc"),
                          ("rotor vane r01 (the comb's top)", "CAP-602", "Al", lambda n, k: n == "A_C1_r01"),
                          ("the riser, its boot", "DCK-501", "PTFE HV wire, silicone", lambda n, k: n in ("A_riser", "A_riser_boot")),
                          ("the tap, its boot", "DCK-501", "PTFE HV wire, silicone", lambda n, k: n in ("A_tap", "A_tap_boot")),
                          ("rotor sleeve, PTFE cover (ref.)", "SHF-304/-306", "—", lambda n, k: n in ("A_rotor_sleeve_vanes",
                                                                                                         "A_sleeve_cover")),
                          ("the can, shaft (for reference)", "CAN-401", "—", lambda n, k: n in ("can", "shaft_A"))],
        source="sim/doubler_caps.py placement; sim/doubler-caps-findings.md §1-§3",
        notes=["The node-1 comb (Ca_05, Ca_03, Ca_01) hangs from r01 on three posts of Al spacers Ø8 joined by M4 A4 "
               "studs through the tabs; flush M4 countersunk screws where a face meets a working gap.",
               "The node-2 comb (Ca_06, Ca_04, Ca_02) stands on three steatite standoffs on the can's disc, M4 button heads "
               "from inside the can.",
               "No support touches two adjacent plates: each post passes the other comb's plates 11 mm off their bore "
               "(the corona margin 1.05, as the C1 rims: sim/doubler-caps-findings.md §3). Gauge the 6 mm gaps at the "
               "three posts and the rim.",
               "The riser's ring lug under post 1's button head and the tap's on Ca_06, each in a silicone boot."])
    tabs = [(31.0, -60.0, 60.0, "120°")]
    for dwg, key, title, nodes, extra in (
            ("CAP-611", "ca_n1", "Ca plate, node-1 comb (Ca_03, Ca_01)", "1 / 4", "Three tabs with M4 clearance holes for the "
             "studs."),
            ("CAP-612", "ca_n1_end_A", "Ca plate, node-1 comb's end (Ca_05)", "1 / 4", "Posts 2 and 3 countersunk M4 (90°) on "
             "the face toward the deck; post 1 plain (the riser's lug under its button head). Side B's is the same part, "
             "turned over."),
            ("CAP-613", "ca_n2", "Ca plate, node-2 comb (Ca_04)", "2 / 3", "Three tabs with M4 clearance holes for the studs."),
            ("CAP-614", "ca_n2_end_A", "Ca plate, node-2 comb's end (Ca_02)", "2 / 3", "Its three holes countersunk M4 (90°) "
             "on the face away from the deck (toward Ca_01). Side B's is the same part, turned over."),
            ("CAP-615", "ca_n2_base_A", "Ca plate, node-2 comb's base (Ca_06), hands A / B", "2 / 3",
             "Three holes for the standoffs' studs; the tap's hole at r 132 countersunk M4 on the face toward Ca_05 "
             "(hand A drawn; hand B the mirror).")):
        keys = [key, key.replace("_A", "_B")] if key.endswith("_A") else [key]
        add(dwg, title, "the doubler: Ca / Cb", "turned", proto(key), key, material=AL + ", plate 3.0", status="PROPOSED",
            qty=q(*keys), used_in="CAP-610", angles=tabs, detail=(24.0, 58.0),
            source="sim/doubler_caps.py tab_outline, placement; sim/multiplier_layout.py (the record's plates r 50-150)",
            notes=["A full annulus r 50-150 (the record's), 3.0 thick, with three tabs into the bore to r 27 at 120°: each "
                   "the hull of a lobe R8 round its post at r 35 and a 24 mm chord on the bore.", extra, HV_RIMS, FLAT],
            data=[("node", nodes), ("holds", "13.2 kV DC to its neighbours (Ca, 6 mm)")])
    add("CAP-616", "Post spacer, Al, Ø8, M4 (-01 × 15, -02 × 6)", "the doubler: Ca / Cb", "turned",
        drilled("post_15", [(1.65, -1.0, 16.0)]), "post_15", material=AL + ", round bar", status="PROPOSED",
        qty=q("post_15", "post_6"), used_in="CAP-610", long=True, threads=[(2.0, 0.0, 15.0)],
        bore_text={3.3: "M4 THRU (tap drill Ø3.3)"}, source="sim/doubler_caps.py POST_D (M4 female)", notes=[
            f"-01: 15.00 ±0.02 long ({q('post_15')} per machine); -02: 6.00 ±0.02 long ({q('post_6')} per machine); "
            "both M4 tapped through, 6H (a female-female spacer). The view draws -01.",
            "Ends square to the thread within 0.02; all edges rounded R1 (an HV conductor 11 mm from the other comb).",
            "The model's solid is plain; the tapped bore is the drawing's."])
    add("CAP-617", "Standoff, glazed steatite, Ø16 × 30, M4", "the doubler: Ca / Cb", "turned",
        drilled("standoff", [(3.5, -1.0, 9.0), (3.5, 21.0, 31.0)]), "standoff",
        material="steatite C 221 (IEC 60672-3), glazed all over but the end faces; M4 brass inserts, cemented",
        status="PROPOSED", qty=q("standoff"), used_in="CAP-610", long=True, model_material="steatite",
        bore_text={7.0: "Ø7 +0.1 ↧ 9 both ends, for the inserts [IR]"},
        source="sim/doubler_caps.py STANDOFF; sim/doubler-caps-findings.md (no catalogue part at this size)",
        notes=["A custom part for a technical-ceramics maker: no catalogue standoff of Ø16 × 30 with M4 threads was found "
               "(Abbatron's glazed standoffs run 1/2-5/8 in with 6-32 / 8-32 threads).",
               "Node 2 (≤ 4.5 kV) to REF: 30 mm of glazed steatite against 6.5 mm needed (inorganic, creepage = clearance).",
               "Inserts: brass M4, Ø7 × 9, thread 8 deep [IR], cemented in the bores flush ±0.05 and square to the axis "
              "within 0.05; the end faces lapped flat. 12 mm of solid steatite stays between the inserts.",
               "Alternate: virgin PTFE, the same envelope, brass inserts pressed in (it creeps; check after a month)."])


def rel_entries(add, M, q, col, mat, rel):
    zc = M.m.zc
    a1 = M.by_name["A_U1_core_pos"]["place"]["rot"]
    b1 = M.by_name["A_bridge_1"]["place"]["rot"] if "A_bridge_1" in M.by_name else 0.0
    zs = [bbox(M.placed(n))[k][2] for n in M.names(lambda p: p["name"].startswith("A_U1_")) for k in (0, 1)]
    z_mid = 0.5 * (min(zs) + max(zs))
    add("REL-700", "Utron, wound: half-cores, neck strip, coil", "the reluctance pump", "assembly", status="LOCKED",
        qty=q("wu_winding"), window=(40.0, 150.0, -40.0, 40.0), planes=[("z", z_mid, "plan")],
        label=f"SECTION A–A: utron A1 cut at its mid-height (z {z_mid:.0f}), seen from +z",
        groups=lambda M: [("half-core, M235-35A (hand A / B)", "UTR-101", "M235-35A", lambda n, k: n.startswith("A_U1_core")),
                          ("neck strip, 80 % NiFe", "REL-702", "80 % NiFe", lambda n, k: n == "A_U1_strip"),
                          ("air-break spacer", "REL-703", "G10", lambda n, k: n == "A_U1_spacer"),
                          ("slot cover", "REL-704", "G10", lambda n, k: n == "A_U1_wedge"),
                          ("cheek (+v / -v)", "REL-705", "G10", lambda n, k: n.startswith("A_U1_cheek")),
                          ("yoke coil, 200 turns", "REL-706", "Cu", lambda n, k: n == "A_U1_winding")],
        source="sim/utron_profile.py spec; sim/utron-3d-findings.md; docs/figures/utron-core-detail.png",
        notes=[f"The record's wound utron: {rel['N_u']} turns of Ø{rel['wire_d_mm']:.2f} on the split U-core, the 3.0 mm NiFe "
               "neck, the bonded slot cover, the studs (docs/make_utron_drawing.py).",
               "The half-cores (UTR-101) bolt through the cheeks and the carrier discs (REL-711) on studs Ø6.4.",
               f"Six per machine, three a side; the air gap to the bridges {rel['g']:g} mm at the aligned position."])
    for dwg, key, title, material, notes in (
            ("REL-702", "wu_strip", "Neck strip, 80 % NiFe", "80 % NiFe, laminations 0.1 mm, bonded (the record)",
             ["30 laminations of 0.1 mm, 3.0 thick (sim/utron_profile.py t_n, n_nife); lapped onto the half-cores' face A."]),
            ("REL-703", "wu_spacer", "Air-break spacer, G10", G10, ["Between the half-cores' break faces (datum B of UTR-101)."]),
            ("REL-704", "wu_wedge", "Slot cover, G10, bonded", G10, ["Bonded over the coil in the slot; 0.83 thick at the tip "
                                                                    "(sim/utron_profile.py t_wedge)."]),
            ("REL-705", "wu_cheek_pos", "Cheek, G10 (-01 +v drawn; -02 -v the mirror)", G10,
             ["Both ends of each half-core stack; the studs through."]),
            ("REL-706", "wu_winding", "Yoke coil, 200 turns", "Cu magnet wire, grade 2 (IEC 60317), Ø1.55, impregnated",
             [f"{rel['N_u']} turns of Ø{rel['wire_d_mm']:.2f} (grade 2), R20 {rel['R_coil_ohm']:.3f} Ω; VPI class F after "
              "winding on a former; the envelope as drawn."])):
        keys = [key] + ([key.replace("pos", "neg")] if "pos" in key else [])
        add(dwg, title, "the reluctance pump", "block", proto(key, _nc), key, material=material, status="LOCKED",
            qty=q(*keys), used_in="REL-700", source="sim/utron_profile.py spec (the record's utron)", notes=notes,
            **(dict(views=("front", "top"), scale=1.0) if key == "wu_wedge" else {}))
    add("REL-710", "Reluctance section A: utrons, carrier discs, bridges, bridge ring", "the reluctance pump", "assembly",
        status="LOCKED", qty=2, window=(-165.0, 165.0, 15.0, 225.0), planes=[(a1, "right"), (b1 + 180.0, "left")],
        label="SECTION A–A: right through a utron, left through a bridge",
        groups=lambda M: [("utron (REL-700)", "REL-700", "—", lambda n, k: n.startswith("A_U"), module_unit),
                          ("carrier disc", "REL-711", "G10", lambda n, k: n.startswith("A_carrier_disc")),
                          ("bridge", "REL-712", "M235-35A", lambda n, k: n.startswith("A_bridge_") and k == "w_bridge"),
                          ("bridge ring", "REL-713", "G10", lambda n, k: n == "A_bridge_ring"),
                          ("rotor sleeve, reluctance bay (ref.)", "SHF-305", "—", lambda n, k: n == "A_rotor_sleeve_rel"),
                          ("shaft (for reference)", "SHF-301", "—", lambda n, k: n == "shaft_A")],
        source="sim/tube_geometry.py wound_element (the record's section, moved by the layout)",
        notes=["The record's section, as the layout moves it: three utrons on two carrier discs (the rotor); six bridges "
               "in the bridge ring (the counter-rotor).", "Side B: the same, its bridges offset 30°."])
    add("REL-711", "Utron carrier disc, G10", "the reluctance pump", "turned", proto("w_disc_57.0"), "w_disc_57.0",
        material=G10 + ", plate 12", status="LOCKED", qty=q("w_disc_57.0"), used_in="REL-710", detail=(16.0, 60.0),
        source="sim/utron_profile.py r_disc, t_disc", notes=["On the sleeve; the utrons' studs through it.", G10_MACH])
    add("REL-712", "Bridge, M235-35A stack", "the reluctance pump", "block", proto("w_bridge", _nc), "w_bridge",
        material="M235-35A (EN 10106), 0.35 mm laminations, bonded stack", status="LOCKED", qty=q("w_bridge"),
        used_in="REL-710", source="sim/utron_profile.py r_br0, r_br1, br_deg",
        notes=[f"r {rel['r_br0']:g}-{rel['r_br1']:g}, {rel['br_deg']:.2f}° wide, 100 long; its inner face at r 130.5 "
               "faces the utrons' tips across the 0.5 mm gap: finish it as UTR-101's tip face."])
    add("REL-713", "Bridge ring, G10 (A; B the mirror)", "the reluctance pump", "turned", proto("w_ring_A"), "w_ring_A",
        material=G10 + ", tube", status="LOCKED", qty=q("w_ring_A", "w_ring_B"), used_in="REL-710", detail=(126.0, 160.0),
        source="sim/utron_profile.py r_ring0, r_ring1", notes=["Its pockets hold the six bridges, bonded.", G10_MACH])


def brg_entries(add, M, q, col, mat):
    zc = M.m.zc
    add("BRG-800", "Bearing hub, Ca|reluctance, side A", "the bearings", "assembly", status="PROPOSED", qty=2,
        window=(-40.0, 190.0, 200.0, 236.0), planes=[(30.0, "full")], layout="wide",
        groups=lambda M: [("bearing SKF 6205-2Z", "P-001", "—", lambda n, k: n == "A_bearing_Ca-reluctance"),
                          ("spider", "BRG-810", "G10", lambda n, k: n == "A_spider_Ca-reluctance"),
                          ("tie rods, nuts, tubes (ref.)", "P-008 / CAP-606", "—",
                           lambda n, k: n.startswith(("A_tie_rod", "A_rod_nut", "A_stator_spacer"))),
                          ("cage (for reference)", "CGE-901", "—", lambda n, k: n == "stator_cage"),
                          ("sleeves, shaft (for reference)", "SHF-301/-304/-305", "—",
                           lambda n, k: n in ("A_rotor_sleeve_vanes", "A_rotor_sleeve_rel", "shaft_A"))],
        source="sim/multiplier_layout.py stack (h 289); sim/doubler_caps.py (the spider grown)",
        notes=["The REF link between the bodies: its inner ring on the shaft (Ø25 k5), its outer in the spider (Ø52 H7).",
               "The spider is bonded in the cage's bore and takes the stator vanes' tie rods."])
    add("BRG-801", "Bearing hub, end (frame), side A", "the bearings", "assembly", status="PROPOSED", qty=2,
        window=(-40.0, 170.0, -3.0, 24.0), planes=[(0.0, "full")], layout="wide",
        groups=lambda M: [("bearing SKF 6205-2Z", "P-001", "—", lambda n, k: n == "A_bearing_end"),
                          ("end spider (frame)", "BRG-811", "G10", lambda n, k: n == "A_spider_end"),
                          ("shaft (for reference)", "SHF-301", "—", lambda n, k: n == "shaft_A")],
        source="sim/bridge_ring_bearings.py placement (one slot out)",
        notes=["The end bearing ties the shaft to the frame; the bottom one locates both bodies (sim/bridge-ring-bearings-"
               "findings.md §4)."])
    add("BRG-802", "Bearing hub, the bridge ring's, side A", "the bearings", "assembly", status="PROPOSED", qty=2,
        window=(-40.0, 162.0, 18.0, 52.0), planes=[(0.0, "full")], layout="wide",
        groups=lambda M: [("bearing SKF 6205-2Z", "P-001", "—", lambda n, k: n == "A_bearing_bridge-ring"),
                          ("cartridge", "BRG-814", "1.4404", lambda n, k: n == "A_cartridge_bridge-ring"),
                          ("bridge-ring spider", "BRG-812", "G10", lambda n, k: n == "A_spider_bridge-ring"),
                          ("ring adapter", "BRG-813", "G10", lambda n, k: n == "A_ring_adapter"),
                          ("bridge ring (for reference)", "REL-713", "—", lambda n, k: n == "A_bridge_ring"),
                          ("shaft (for reference)", "SHF-301", "—", lambda n, k: n == "shaft_A")],
        source="sim/bridge_ring_bearings.py placement, PART",
        notes=["The bearing in its stainless cartridge (a flange on the spider's outboard face, a lip over the outer ring), "
               "the 8 mm spider centred in its slot, the 6 mm ring to the bridge ring's outer face.",
               "Side A's locates the counter-rotor; side B's floats on its spring preload (100 N)."])
    for dwg, key, title, extra, det in (
            ("BRG-810", "spider_rel", "Spider, Ca|reluctance, G10, Ø364", "Bore Ø52 H7 for the 6205; six Ø8.5 holes at r 173 for "
             "the tie rods; bonded in the cage's bore.", (20.0, 60.0)),
            ("BRG-811", "spider", "Spider, end (frame), G10, Ø324", "Bore Ø52 H7 for the 6205; its rim to the frame.", (20.0, 60.0)),
            ("BRG-812", "ring_spider", "Spider, the bridge ring's bearing, G10", "Bore Ø60 H7 for the cartridge's barrel.",
             (24.0, 64.0)),
            ("BRG-813", "ring_adapter", "Ring adapter, G10, spider to bridge ring", "Bonded between the spider's rim and the "
             "bridge ring's outer face.", (120.0, 160.0))):
        add(dwg, title, "the bearings", "turned", proto(key), key, material=G10, status="PROPOSED", qty=q(key),
            used_in="BRG-800/-801/-802", detail=det, source="sim/stack_sizing.py BEARING; sim/bridge_ring_bearings.py",
            notes=[extra, G10_MACH])
    add("BRG-814", "Cartridge, the bridge-ring bearing's (-01 A; -02 B the mirror)", "the bearings", "turned",
        proto("ring_cartridge_A"), "ring_cartridge_A", material=SS, status="PROPOSED",
        qty=q("ring_cartridge_A", "ring_cartridge_B"), used_in="BRG-802", long=False, detail=(20.0, 40.0),
        source="sim/bridge_ring_bearings.py CART_R1, CART_FLANGE_R1, CART_LIP_R0", notes=[
            "Bore Ø52 H7 for the 6205's outer ring; the lip Ø46.4 over it (its housing abutment); the flange on the "
            "spider's outboard face, three M5 to the spider [IR].", "Non-magnetic: μr ≤ 1.05 after machining."])
    add("CGE-900", "Counter-rotor: the cage, the stator stacks, the spiders, the bridges", "the counter-rotor", "assembly",
        status="PROPOSED", qty=1, window=(-192.0, 192.0, -5.0, 1019.0), planes=[(30.0, "full")], layout="tall",
        view3d=dict(lay=True, dir=(0.3, -1.4, 0.9)),
        label="SECTION A–A at 30° (the lugs and tie rods)",
        groups=lambda M: [("cage tube", "CGE-901", "G10", lambda n, k: n == "stator_cage"),
                          ("stator vanes", "CAP-603", "Al", lambda n, k: k == "stator_vane_m"),
                          ("tie rods, nuts", "P-008", "glass-epoxy", lambda n, k: k in ("tie_rod", "rod_nut")),
                          ("stator spacer tubes", "CAP-606", "G10", lambda n, k: k.startswith("stator_spacer")),
                          ("end rings", "CAP-607", "G10", lambda n, k: k == "end_ring"),
                          ("Ca|reluctance spiders", "BRG-810", "G10", lambda n, k: k == "spider_rel"),
                          ("bridges", "REL-712", "M235-35A", lambda n, k: k == "w_bridge"),
                          ("bridge rings", "REL-713", "G10", lambda n, k: k.startswith("w_ring")),
                          ("bridge-ring spiders, adapters", "BRG-812/-813", "G10", lambda n, k: k in ("ring_spider", "ring_adapter")),
                          ("cartridges", "BRG-814", "1.4404", lambda n, k: k.startswith("ring_cartridge"))],
        source="sim/tube_geometry.py LayoutMachine (the stator bodies)",
        notes=["One body geared 1 : -1 against the rotor: the cage from spider to spider joins side A's stator stack and "
               "bridges to side B's (docs/drive-gear-belt.md).",
               "It rides on the shaft at the two Ca|reluctance bearings and the two bridge-ring bearings."])
    add("CGE-901", "Cage tube, G10, Ø364 / 372", "the counter-rotor", "turned", proto("cage"), "cage", material=G10 + ", tube",
        status="PROPOSED", qty=q("cage"), used_in="CGE-900", long=True, source="sim/doubler_caps.py CAGE_R0, CAGE_R1",
        detail_z=(0.0, 40.0), detail_x=(176.0, 192.0),
        notes=["Bore Ø364 H9: the stator vanes' lugs, the end rings and the Ca|reluctance spiders locate in it (bonded).",
               "598 long, spider to spider; 32 mm from the decks' outermost housings (sim/doubler-caps-findings.md §2).",
               G10_MACH])


def bought_entries(add, M, q, col, mat):
    import tube_geometry as TG
    import bridge_ring_bearings as BRB
    part = BRB.PART
    n_brg = q("bearing", "ring_bearing")
    add("P-001", f"Bearing, {part['maker']} {part['designation']}", "bought parts", "bought", proto("ring_bearing"),
        "ring_bearing", material="deep groove ball bearing, 25 / 52 / 15, shielded both sides", status="BOUGHT",
        qty=n_brg, used_in="BRG-800/-801/-802", source="sim/bridge_ring_bearings.py PART (catalogue data, 2026-10-11)",
        mass_kg=part["kg"],
        spec=[("designation", f"{part['maker']} {part['designation']}: {part['what']}"),
              ("bore / OD / width", f"{part['d_mm']:g} / {part['D_mm']:g} / {part['B_mm']:g} mm"),
              ("ratings", f"C {part['C_N'] / 1e3:g} kN, C0 {part['C0_N'] / 1e3:g} kN, Pu {part['Pu_N'] / 1e3:g} kN"),
              ("speeds", f"reference {part['n_ref_rpm']:g} r/min, limiting {part['n_lim_rpm']:g} r/min (2Z)"),
              ("accuracy", f"running {part['running_accuracy']}; dimensions {part['dimensional_accuracy']}"),
              ("abutments", f"da min {part['da_min_mm']:g}, Da max {part['Da_max_mm']:g} mm"),
              ("alternates", "; ".join(f"{a['maker']} {a['designation']}" for a in BRB.ALTERNATES)),
              ("where", "the Ca|reluctance pair, the end pair (frame) and the bridge-ring pair: six per machine")],
        notes=["Catalogue data as a web search rendered the distributors' listings and SKF's brochure (2026-10-11): re-read "
               "the maker's current page before ordering (sim/bridge-ring-bearings-findings.md §1).",
               "Fits: shaft Ø25 k5, housings Ø52 H7; the axial spring preload 100 N on the floating bearings.",
               "Sources: " + "; ".join(f"{k}: {v}" for k, v in list(part["sources"].items())[:3])])
    import multiplier_layout as ML
    add("P-002", "HV rectifier stick, 20 kV, 5 mA (XCH 2CL77)", "bought parts", "bought",
        lambda M: _nc(rotated(compound([M.proto("stick_body"), M.proto("stick_lead_neg"), M.proto("stick_lead_pos")]),
                              (0, 0, 1), -90.0)), "stick_body", material="avalanche HV silicon rectifier stick, epoxy body",
        status="BOUGHT", qty=q("stick_body"), used_in="DCK-504", source="sim/diode-stack-findings.md; LCSC C2982866",
        spec=[("rating", "VRRM 20 kV; IF(AV) 5 mA; IFSM 0.5 A (half-cycle, 50 Hz)"),
              ("characteristics", "VF ≤ 62.5 V at 10 mA; IR ≤ 2 µA at 25 °C, ≤ 5 µA at 100 °C; Cj ≤ 1 pF; trr ≤ 0.1 µs"),
              ("candidate", "XCH 2CL77, LCSC part C2982866 (datasheet: wmsc.lcsc.com …/2204201445_XCH-2CL77_C2982866.pdf)"),
              ("alternates", "Anshan Leadsun 2CL77 (Cj 2 pF, Tj 150 °C); HVGT 2CL77 (100 ns)"),
              ("envelope", f"the layout's: Ø{ML.PART['stick']['body_d']:g} × {ML.PART['stick']['body_l']:g} body [RH]; "
                           "confirm on the sheet received"),
              ("where", "D1-D12, one stick each (sim/multiplier-layout-findings.md §2)")],
        notes=["The record's recommended stick (sim/diode-stack-findings.md: 'stock at LCSC; the recommended stick').",
               "Datasheets disagree on VF max (62.5 / 75 V) and Tj (130 / 150 °C): design to the sheet of the lot bought.",
               "Lot-match the twelve on IR at 15 kV, 25 °C (the clamps and the rings' leakage)."])
    add("P-003", "HV capacitor, 190 pF / 30 kV, N4700 (Vishay 715C30KTT19)", "bought parts", "bought",
        module([("c180_body", 0), ("stud", 15.0), ("stud", -15.0)]), "c180_body",
        material="class 1 ceramic disc (N4700), screw terminals", status="BOUGHT", qty=q("c180_body"), used_in="DCK-506",
        colour3d=(0.56, 0.67, 0.82),
        source="sim/integrated_multiplier_results.json pick (C3-C6 180 pF); Vishay 715C series",
        spec=[("value", "the pick 180 pF (sim/integrated_multiplier_results.json); the nearest catalogue part 190 pF ±20 %"),
              ("rating", "30 kV DC; class 1, N4700; DF 0.2 %; -30 to +85 °C"),
              ("candidate", "Vishay 715C30KTT19 (190 pF, 30 kV DC, N4700, screw terminals), Ø21 × 28 mm (RS listing)"),
              ("status", "the RS listing marks it as being discontinued: confirm stock, or the 715C series' successor"),
              ("envelope", "the layout's Ø30 × 22 [RH]; the candidate is Ø21 × 28: standing, its module is 44 tall, "
                           "inside the deck's 42 mm zone only laid down — the deck's plan to re-check"),
              ("where", "C3-C6 (four per machine)")],
        notes=["Datasheet: wwwlegacy.vishay.com/docs/22210/715c-kt.pdf; listings: farnell.com 715C30KTT19 (2192257).",
               "190 pF against the pick's 180: within the part's ±20 %; the pick's z is flat in C3-C6 (sim/multiplier-"
               "layout-findings.md §6: 1.0157-1.0164 over 150-180 pF)."])
    add("P-004", "HV capacitor, 100 pF / 40 kV, N4700 (Vishay 715C40KTT10)", "bought parts", "bought",
        module([("c100h_body", 0), ("stud", 16.0), ("stud", -16.0)]), "c100h_body",
        material="class 1 ceramic disc (N4700), screw terminals", status="BOUGHT", qty=q("c100h_body", "c100_body"),
        colour3d=(0.56, 0.67, 0.82),
        used_in="DCK-507, DCK-508", source="Vishay 715C series (RS listings 2101583 / 2101584)",
        spec=[("value", "100 pF ±20 %"), ("rating", "40 kV DC; class 1, N4700; -30 to +85 °C"),
              ("candidate", "Vishay 715C40KTT10, Ø21 × 31 mm (RS listing)"),
              ("where", "C7 / C8 (30 kV duty) and Csa / Csb (40 kV): one part for all four"),
              ("envelope", "the layout's Ø30 × 24 (Csa) and Ø25 × 20 (C7 / C8) [RH]; the candidate's 31 mm height makes "
                           "a 47 mm module standing, 5 mm over the deck's zone: lay it along its lane")],
        notes=["No 100 pF / 30 kV 715C was found; the 40 kV part covers C7 / C8 too.",
               "Confirm the terminals' thread and the stock before ordering."])
    add("P-005", "Surge resistor, 22 kΩ, ≥ 15 kV, ≥ 1 W", "bought parts", "bought",
        lambda M: _nc(rotated(compound([M.proto("rsurge_body"), M.proto("rsurge_lead_neg"), M.proto("rsurge_lead_pos")]),
                              (0, 0, 1), -90.0)), "rsurge_body", material="HV thick-film resistor, axial", status="BOUGHT",
        qty=q("rsurge_body"), used_in="DCK-505", source="sim/parts-first-cut-findings.md (the surge resistors); Vishay Techno FHV",
        spec=[("value", "22 kΩ ±10 %; ≥ 1 W; standing ≥ 15 kV DC across its body; pulse-rated (a flashover's surge)"),
              ("candidate", "Vishay Techno FHV axial series (thick film, 100 Ω-10 GΩ, up to 15 kV, pulse-optimised): "
                            "the 22 kΩ ordering code to be read off its datasheet"),
              ("alternate", "two 11 kΩ / 10 kV parts in series in the same potting (Welwyn VRW class)"),
              ("envelope", "the layout's Ø8 × 40 body [RH]"), ("where", "R1-R4 (four per machine)")],
        notes=["No catalogue listing of exactly 22 kΩ at ≥ 15 kV was found in this session's search: the FHV series' range "
               "covers it; confirm the code, the voltage and the pulse rating on its datasheet."])
    add("P-006", "TVS diode 1.5KE200A (the clamp strings)", "bought parts", "bought",
        lambda M: _nc(compound([TG.cyl_z(0.0, 0.0, 2.65, -4.75, 4.75), TG.cyl_z(0.0, 0.0, 0.5, -16.0, -4.75),
                                TG.cyl_z(0.0, 0.0, 0.5, 4.75, 16.0)])), None, material="unidirectional TVS, 1500 W, DO-201",
        status="BOUGHT", qty=66 * q("clamp_body"), used_in="DCK-509", colour=(0.25, 0.25, 0.28),
        source="sim/parts-first-cut-findings.md §2 (Z1, Z4: 66 × 1.5KE200A)",
        spec=[("rating", "VBR 190-210 V at IT 1 mA (the clamp's own current); 1500 W peak pulse"),
              ("candidates", "Littelfuse 1.5KE200A; Vishay 1.5KE200A (the same JEDEC part)"),
              ("lot", "one lot, sorted on VBR at 1 mA, trimmed to the string's V_op (sim/multiplier-layout-findings.md §6: "
                      "60 parts hold the rings at ±14.77 kV)"),
              ("envelope", "DO-201: Ø5.3 × 9.5 body, Ø1.0 leads (drawn here; the module's meander in DCK-509)"),
              ("where", "Z1 and Z4: 66 a string, two strings")],
        notes=["16 mW per part against a ≥ 1.5 W rating, ×90 (sim/parts-first-cut-findings.md §2)."])
    add("P-007", "MnZn ferrite rod, Fair-Rite 4077484611 (77)", "bought parts", "bought", proto("ah_core_A"), "ah_core_A",
        material="77 MnZn ferrite rod", status="BOUGHT", qty=q("ah_core_A", "ah_core_B"), used_in="HUB-200",
        source="presets/hub-locked.json AH; docs/ledger/DCCREG-design-ledger.md §3",
        spec=[("part", "Fair-Rite 4077484611, material 77"), ("size", "Ø12.3 × 41.3 mm (as the record registers it)"),
              ("where", "the AH cores, at |z| 30.7-72 on the axis, one a side")],
        notes=["The record's part (presets/hub-locked.json AH core, REGISTER); its material data from Fair-Rite's 77 "
               "material sheet as the preset cites it."])
    add("P-008", "Threaded rod M8 and nuts, glass-epoxy", "bought parts", "bought",
        lambda M: _nc(compound([M.proto("tie_rod"), moved(M.proto("rod_nut"), 0.0, 0.0, -8.0)])), "tie_rod",
        material="glass-fibre epoxy (G10 / GFRP) threaded rod and nuts", status="BOUGHT",
        qty=f"{q('tie_rod')} rods, {q('rod_nut')} nuts", qty_index=f"{q('tie_rod')} + {q('rod_nut')}",
        used_in="CAP-600, CGE-900", source="sim/doubler_caps.py ROD_D, NUT",
        spec=[("size", "M8, 136 mm per rod (cut from stock); nuts M8, AF 13 × 6.5"),
              ("material", "glass-fibre reinforced epoxy (electrically insulating, non-magnetic)"),
              ("candidates", "M.M. srl (Italy) glass-fibre epoxy threaded rods, nuts and washers, metric, 2.2 m stock; "
                             "Reichelt Chemietechnik GFRP threaded rod; Strongwell FIBREBOLT (3/8-16, the imperial "
                             "alternate)"),
              ("load", "the stator stack's clamp only (tens of N); never a path between two nets (it touches REF metal "
                       "and G10 only)")],
        notes=["Confirm M8 stock and the nuts' match with the maker; seal the cut ends with epoxy."])
    add("P-009", "HV wire, FEP, 20 kV, 18 AWG (UL3239)", "bought parts", "bought",
        lambda M: compound([TG.cyl_z(0.0, 0.0, 1.5, 0.0, 30.0)]), None, material="UL3239 high-voltage lead wire, FEP",
        status="BOUGHT", qty="per DCK-501", qty_index="—", used_in="DCK-501", colour=(0.93, 0.93, 0.90),
        source="sim/multiplier_layout.py bore_wire (1 mm in 3 mm PTFE); docs/rings-design.md §3",
        spec=[("rating", "≥ 20 kV DC for the pump's nodes; ≥ 30 kV DC for the rings' leads (docs/rings-design.md §3)"),
              ("candidate", "FDH Aero UL3239-18-20KV-Z726 (tinned Cu 7/26, modified FEP, 20 kV, 200 °C)"),
              ("rings' leads", "a 30 kV UL3239 (listed by makers; part number to confirm) or a ≥ 40 kV DC silicone lead"),
              ("model", "drawn as Ø3 over a 1 mm conductor (the layout's)")],
        notes=["UL3239's ratings are AC (a 15 kV rms spark test, 40 kV withstand): confirm the DC rating with the maker."])
    add("P-010", "LV cable, the magnetic pump's leads", "bought parts", "bought",
        lambda M: compound([TG.cyl_z(0.0, 0.0, 2.5, 0.0, 40.0)]), None, material="multi-core LV cable, PTFE / FEP insulated",
        status="BOUGHT", qty=2, used_in="SHF-300", colour=COL_LV,
        source="sim/multiplier-layout-findings.md §7; sim/tube_geometry.py LV_R",
        spec=[("conductors", "the AH coils to La / Lb, D1*-D4* and the utrons: 8 cores ≥ 0.5 mm² (≤ 3 A rms, the utrons' "
                             "1.9 A rms) [IR]"),
              ("envelope", "≤ Ø5 over all, to run in the shaft's 8 mm bore"), ("insulation", "PTFE or FEP, 200 °C, ≤ 300 V"),
              ("candidate", "any 8-core PTFE-insulated control cable of ≤ Ø5 (to be chosen)")],
        notes=["The cable's own choice is open; the bore fixes its diameter."])
    add("P-011", "Fasteners, inserts and stock", "bought parts", "list", status="BOUGHT", used_in="all", no_3d=True,
        heading="FASTENERS, INSERTS, ADHESIVES AND STOCK (per machine)",
        cols=[("item", 62.0), ("specification", 150.0), ("qty", 20.0), ("used in", 36.0)],
        rows=[("M4 stud (set screw) A4-70", "ISO 4026, M4 × 12, A4-70: the Ca combs' posts through the tabs", 24, "CAP-610"),
              ("M4 countersunk screw A4-70", "ISO 10642, M4 × 8: r01's outer face (6), Ca_05 posts 2-3 (4), Ca_02 (6)", 16, "CAP-610"),
              ("M4 button-head screw A4-70", "ISO 7380, M4 × 8: the standoffs from inside the can (6), post 1 under Ca_05 (2)", 8,
               "CAP-610"),
              ("M4 nut, brass", "the tap's lug under Ca_06 (in its boot)", 2, "CAP-610"),
              ("M4 ring lug, tinned Cu", "the riser's and the tap's terminations", 4, "CAP-610"),
              ("M5 screw A4-70", "ISO 4762, M5 × 10: the cartridges to their spiders [IR]", 6, "BRG-802"),
              ("structural epoxy", "two-part, e.g. 3M DP490 class: the vane stack, the rings, the spiders, the cage", "—", "all"),
              ("silicone, RTV-2", SIL + ": the deck's pour, the modules, the boots", "≈ 2.5 kg", "DCK-500"),
              ("silicone gel", "two-part, degassed, vacuum-cast: the hub's 0.5 mm interface", "—", "HUB-200"),
              ("G10 stock", "plate 6 / 8 / 10 / 12 / 15; tube Ø16 / 8.5, Ø41 / 64, Ø60 / 66, Ø364 / 372; rod Ø5", "—", "all"),
              ("Al stock", "EN AW-6082-T6 plate 3.0 (vanes, plates), 2.0 (can discs), tube Ø96 / 92, bar Ø8", "—", "all"),
              ("PTFE stock", "virgin: tube Ø45 / 41, sheet 2.0, rod Ø12", "—", "SHF-300, CAN-400")],
        notes=["Quantities from sim/doubler_caps.py placement and the model's counts; side A and side B together.",
               "A4 stainless throughout (non-magnetic enough for the electrostatic stacks; keep it out of the utrons' "
               "gaps)."])


# ---------------------------------------------------------------------------------------------------------
# the proposed parts the layout's model does not carry (sim/unmodelled_parts.py): the magnetic pump's chokes and
# kick, its bought electronics, and the drive (the reverser, the belt, the motor)
# ---------------------------------------------------------------------------------------------------------
DRIVE_FLAG = ("Status: the first cut of docs/drive-gear-belt.md on the record's 940 mm stack-up (z from the record's "
              "bottom end-bearing slot); the ledger asks for the drive to be re-cut on the layout (§6, item 71). PROPOSED.")
DRIVE_STATUS = "PROPOSED · the first cut, on the record's 940 mm stack-up: to re-cut on the layout (ledger §6, item 71)"
PUMP_STATUS = "PROPOSED · the first cut (sim/parts-first-cut-findings.md); its place on the rotor OPEN"
TEETH = ("The teeth as the 3-D view and the model draw them: the heel's involute profile on the back cone (Tredgold), "
         "the flanks straight to the apex, each tooth thinned 0.064 mm for the backlash (sim/unmodelled_parts.py); "
         "the section and the plan draw the blank, as a gear drawing does.")
SS305 = "austenitic stainless 1.4305 (303), non-magnetic, as the shaft"
AL6 = "Al EN AW-6082-T6"
_PAIRS = {}


def subpart(skey, pkey, turn=0.0, norm="z"):
    """a sub-assembly's prototype for its own sheet: (make, make3d), the drawing's solid (a gear's blank) and the 3-D
    view's (its teeth), turned about z by `turn` and moved alike, to start at z 0 (norm 'z') or centred ('c')."""
    def both():
        k = (skey, pkey, turn, norm)
        if k not in _PAIRS:
            bl, _, _, t3 = sub(skey).protos[pkey]
            t3 = bl if t3 is None else t3
            if turn:
                bl, t3 = rotated(bl, (0, 0, 1), turn), rotated(t3, (0, 0, 1), turn)
            lo, hi = tight_bbox(bl)
            d = -0.5 * (lo + hi) if norm == "c" else np.array([0.0, 0.0, -lo[2]])
            _PAIRS[k] = (moved(bl, *d), moved(t3, *d))
        return _PAIRS[k]
    return (lambda M: both()[0]), (lambda M: both()[1])


def placed_parts(skey, names=None):
    """a sub-assembly's parts as placed, each in its colour (a module's 3-D view)."""
    S = sub(skey)
    return [(S.placed(p, True), S.protos[p["proto"]][1]) for p in S.parts if names is None or p["name"] in names]


def gear_rows(g, mates):
    """a bevel gear's data block (sim/unmodelled_parts.py bevel_gear's data; docs/drive-gear-belt.md §5)."""
    return [("gear", "straight bevel, 90° shaft angle; the teeth's proportions at the heel (h_a = m, h_f = 1.25 m)"),
            ("teeth, module", f"z {g['z']}, m {g['m']:g} at the heel; pressure angle {g['alpha_deg']:g}°"),
            ("pitch angle δ", f"{g['delta_deg']:.2f}°; face {g['face_angle_deg']:.2f}°, root {g['root_angle_deg']:.2f}°"),
            ("pitch Ø / tip Ø", f"{g['d_pitch']:.2f} / {g['d_tip_heel']:.2f} at the heel"),
            ("cone distance, face", f"R_e {g['R_e']:.2f}; b {g['b']:g}"),
            ("mounting distance", f"{g['mounting_distance']:.2f} ± 0.05, the cone's apex to the back face"),
            ("mates with", mates), ("backlash", "j_n 0.10-0.15, set at assembly (docs/drive-gear-belt.md §5)"),
            ("accuracy", "ISO 17485 grade 8 class (AGMA Q 8, as sized) [IR]")]


def gear_marks(g):
    """a bevel gear blank's pitch cone (a chain line) and its callouts in the section, in its drawing's frame (z from
    the toe's tip, as subpart moves it)."""
    z0 = g["z_min"]
    (rh, zh), (rt, zt) = g["pitch_heel"], g["pitch_toe"]
    u = np.array([rh - rt, zh - zt]) / math.hypot(rh - rt, zh - zt)
    a, b = np.array([rt, zt - z0]) - 4.0 * u, np.array([rh, zh - z0]) + 4.0 * u
    Ht = (g["Ht"][0], g["Ht"][1] - z0)
    mid = (0.5 * (g["Ht"][0] + g["Tt"][0]), 0.5 * (g["Ht"][1] + g["Tt"][1]) - z0)
    lines = [("detail", [tuple(a), tuple(b)], "chain")]
    calls = [("detail", Ht, f"tip Ø{g['d_tip_heel']:.2f} at the heel", (1.0, 0.25)),
             ("detail", mid, f"face cone {g['face_angle_deg']:.2f}°", (1.0, -0.6)),
             ("detail", tuple(b), f"pitch cone {g['delta_deg']:.2f}°", (0.6, 1.0))]
    return lines, calls


def pump_parts_entries(add):
    """REL-720 the La / Lb choke, REL-721 its winding, REL-730 the K4 kick module (sim/parts-first-cut-findings.md)."""
    import unmodelled_parts as U
    ch = U.CH
    add("REL-720", "La / Lb choke, EI-84 × 35, 150 turns", "the magnetic pump: La / Lb", "assembly", status="PROPOSED",
        status_text=PUMP_STATUS, qty=2, sub="choke", window=(-6.0, 90.0, -4.0, 74.0), planes=[("z", 0.5 * U.CH_S, "plan")],
        label="SECTION A–A: the cut through the stack's middle (seen from +z, the legs up)",
        view3d=dict(dir=(0.9, -1.0, 1.6), up=(0, 1, 0)), cut3d=False,
        groups=lambda M: [("E laminations, a bonded stack", "P-019", "M400-50A 0.5", lambda n, k: n == "E_stack"),
                          ("I laminations, a bonded stack", "P-019", "M400-50A 0.5", lambda n, k: n == "I_stack"),
                          ("gap spacer, 0.063 mm", "P-019", "PET film", lambda n, k: n == "gap_spacer"),
                          ("bobbin", "P-019", "PA66-GF", lambda n, k: n == "bobbin"),
                          ("winding, 150 turns", "REL-721", "Cu, grade 2", lambda n, k: n == "winding"),
                          ("leads, sleeved", "REL-721", "Cu", lambda n, k: n.startswith("lead_"), 2)],
        source="sim/parts-first-cut-findings.md §1; sim/parts_first_cut_results.json la_lb.chosen",
        notes=["La and Lb are one part, two per machine: EI-84 scrapless (84 × 70, centre leg 28, outer legs 14, window "
               "14 × 42), a 35 mm stack of M400-50A 0.5 mm laminations (M235-35A roughly halves the iron loss).",
               f"{ch['turns']} turns of Ø{ch['wire_mm']:.2f} grade 2 in {ch['layers']} layers of {ch['per_layer']}: R20 "
               f"{ch['R20_ohm']:.3f} Ω; 0.146 H, trimmed on test by the spacer (0.063 mm in all three legs, E and I butted).",
               "Bond the stack and the spacer: the gap pulls 531 N at the peak, 226 N pulsating at 120 Hz. Impregnate "
               "(VPI, class F).",
               "On the rotor at r 80 it sees 32 g (490 N at 600 rpm; 760 N in the 750 rpm spin test): La and Lb 180° "
               "apart in one plane; no bracket may encircle a leg (a shorted turn). Its place on the rotor is OPEN.",
               f"{ch['m_with_bobbin_kg']:.2f} kg each: {ch['m_fe_kg']:.2f} kg of iron, {ch['m_cu_kg']:.2f} kg of copper, the "
               "bobbin and the varnish. The flanges reach 1 mm past the build: 84 × 70 × 61 over all."])
    mk, mk3 = subpart("choke", "ch_winding", norm="c")
    add("REL-721", "La / Lb winding, 150 turns of Ø1.40", "the magnetic pump: La / Lb", "block", mk, None,
        material="Cu magnet wire, grade 2 (IEC 60317), Ø1.40, impregnated", status="PROPOSED", status_text=PUMP_STATUS,
        qty=2, used_in="REL-720", source="sim/parts_first_cut_results.json la_lb.chosen (choke(), winding())",
        mass_kg=ch["m_cu_kg"], colour3d=(0.86, 0.53, 0.32), view3d=dict(dir=(0.9, -1.0, 1.6), up=(0, 1, 0)),
        data=[("turns, wire", f"{ch['turns']} × Ø{ch['wire_mm']:.2f} (OD {ch['wire_od_mm']:.3f})"),
              ("layers", f"{ch['layers']} of {ch['per_layer']}; build {ch['build_mm']:.2f}"),
              ("mean turn, length", f"{ch['mlt_mm']:.0f} mm; {ch['length_m']:.1f} m"),
              ("R20, copper", f"{ch['R20_ohm']:.3f} Ω; {ch['m_cu_kg']:.3f} kg")],
        notes=[f"{ch['turns']} turns of Ø{ch['wire_mm']:.2f} grade 2, {ch['layers']} layers of {ch['per_layer']} at a 1.55 mm "
               "pitch on the bobbin, polyester tape 0.05 mm between the layers.",
               "The leads (start and finish) sleeved and led out at the stack's +z face; turn to turn about 0.7 V, layer to "
               "layer about 40 V, which grade 2 holds with a wide margin (sim/parts-first-cut-findings.md §1).",
               "The envelope as drawn: the build round the leg's 28 × 35 section from 1.25 to 12.04 mm, its corners R1.25 "
               "inside and R12.0 outside; 37.2 long between the flanges."])
    add("REL-730", "Start kick K4, module", "the magnetic pump: the start", "bought", lambda M: compound(
        [s for s, _ in placed_parts("kick")]), None, material="a G10 base, the cell in its holder, the board potted in "
        "silicone, the reed sensor", status="PROPOSED", status_text=PUMP_STATUS, qty=1, used_in="the rotor (place OPEN)",
        source="sim/parts-first-cut-findings.md §3 (K4); sim/parts_first_cut_results.json kick",
        make_parts3d=lambda M: placed_parts("kick"), views=("top", "front"), env_box=(34.0, 150.0, 258.0, 128.0), scale=1.0,
        env_title="THE MODULE (its layout a placeholder [RH])", view3d=dict(dir=(1.0, -1.4, 1.2)),
        mass_kg=None,
        spec=[("cell", "9 V lithium (LiMnO2, 1.2 Ah): Ultralife U9VL-J-P, 48.5 × 26.5 × 17.5, in a 9 V holder "
                       "(Keystone 1294 class)"),
              ("C kick", "470 µF 25 V bipolar electrolytic, Ø16 × 25: Nichicon UES1E471MHM; it swings to −2.4 V after "
                         "the dump, so it must be bipolar (or film)"),
              ("R1", "10 kΩ, 0.25 W: the cell charges C in τ 4.7 s"),
              ("SCR", "≥ 400 V, ≥ 1 A, sensitive gate: Littelfuse TCR22-8 (600 V, 1.5 A, TO-92); it sees −101 … +119 V"),
              ("snubber, gate", "100 Ω + 10 nF across the SCR (dV/dt); R3 1 kΩ gate to cathode; the reed through 0.1 µF + "
                                "R2 100 Ω into the gate"),
              ("reed, magnet", "normally open, flange mount on M3: Littelfuse 59140; the magnet a Littelfuse 57140-000 "
                               "actuator, brought from outside the frame"),
              ("link", "the arming link, a 2-pin header and jumper on the potting"),
              ("energy", "19.0 mJ at 9 V; the seed needs 2.2 mJ (16 % of Ψs), a fast dump about 8 mJ: × 2.4")],
        notes=["The K4 kick (PROPOSED): the cell charges C through R1; at full speed the magnet closes the reed once a "
               "revolution, the reed pulses the SCR, and the SCR dumps C across La, + to node a and − to REF: 0.60 A peak "
               "over 17 ms. The SCR stops when its dump ends, so each charge kicks once.",
               "Procedure: arm at standstill (the link in); spin up to 600 rpm each way, never below 500; bring the magnet "
               "to the reed's track; the AH comes up within about 25 cycles (0.2 s); withdraw the magnet. After a slow-down "
               "below about 750 rpm relative, re-kick at full speed (C recharges in about 25 s).",
               "The module's layout and envelope are placeholders [RH]; its place on the rotor is OPEN: where the cage carries "
               "no vanes, away from the bridges and utrons, the reed's blades radial and potted so 20-63 g cannot close it.",
               "It starts the pump at all four rotor phases tried with every diode set (sim/parts-first-cut-findings.md §3)."])


def drive_entries(add):
    """the reverser (DRV-100 to -109), the belt drive (DRV-120, -121) and their small parts (DRV-190)."""
    import unmodelled_parts as U
    res = json.load(open(os.path.join(ROOT, "sim", "unmodelled_parts_results.json")))
    clr, bclr = res["reverser"]["clearance_mm"], res["belt"]["clearance_mm"]
    mesh_clr = min(res["reverser"]["mesh_clearance_mm"].values())
    R = sub("reverser")
    gr, gc, gp = R.data["g_rotor"], R.data["g_cr"], R.data["g_pinion"]
    pb = U.pinion_bearings()
    rotor_ = lambda n: n in ("gear_rotor", "key", "collar", "spacer_A", "spacer_B", "spacer_C")
    add("DRV-100", "The 1 : −1 bevel reverser, side A", "the drive", "assembly", status="PROPOSED", status_text=DRIVE_STATUS,
        qty=1, sub="reverser", window=(-80.0, 80.0, -139.0, 24.0), planes=[(U.PHI_P[0], "right"), (U.PHI_P[0] + 180.0, "left")],
        label=f"SECTION A–A: right through a pinion's axis ({U.PHI_P[0]:.0f}°), left at {U.PHI_P[0] + 180.0:.0f}°",
        view3d=dict(dir=(1.0, -1.4, 0.7)), layout="std_notes", omit3d=("end_disc",),
        caption3d="3-D view, a quarter cut away; the end disc and the shaft left out (axonometric, not to scale)",
        groups=lambda M: [("side gear, the rotor's", "DRV-101", "1.4305", lambda n, k: n == "gear_rotor"),
                          ("side gear, the counter-rotor's", "DRV-102", "1.4305", lambda n, k: n == "gear_cr"),
                          ("pinion z 20", "DRV-103", "POM-C", lambda n, k: n.startswith("pinion_")),
                          ("stub shaft", "DRV-104", "1.4305", lambda n, k: n.startswith("stub_")),
                          ("cartridge sleeve", "DRV-105", "Al 6082", lambda n, k: n.startswith("cartridge_")),
                          ("bearing SKF 6000-2Z", "P-012", "—", lambda n, k: n.startswith("b6000_")),
                          ("gear case", "DRV-106", "Al 6082", lambda n, k: n == "case"),
                          ("bell", "DRV-107", "Al 6082", lambda n, k: n == "bell"),
                          ("counter-rotor hub", "DRV-108", "Al 6082", lambda n, k: n == "hub"),
                          ("end disc", "DRV-109", "G10", lambda n, k: n == "end_disc"),
                          ("bearing SKF 6205-2Z (of P-001's)", "P-001", "—", lambda n, k: n.startswith("bearing_")),
                          ("collar, spacers, key, ring, nut", "DRV-190", "1.4305",
                           lambda n, k: rotor_(n) or n.startswith("spacer_") or n in ("retaining_ring", "nut")),
                          ("pulley 80T with its bush", "P-014", "—", lambda n, k: n in ("pulley_80T", "bush"), "1 + 1"),
                          ("shaft, its drive end (for reference)", "SHF-301", "—", lambda n, k: n == "shaft")],
        source="docs/drive-gear-belt.md §5, §8; sim/unmodelled_parts.py reverser_sub",
        notes=[DRIVE_FLAG,
               "Three POM pinions at 30° / 150° / 270° between two equal stainless side gears; the case is the carrier, held "
               "by the frame: the counter-rotor turns at −600 rpm when the rotor turns at +600 (§5). The teeth clear by "
               f"{mesh_clr:.3f} mm at the closest point (sim/unmodelled_parts_results.json).",
               "On the shaft, clamped by the lock nut against the collar: the gear-end bearing's inner ring, spacer A, the "
               "rotor gear (keyed), spacer B, the locating bearing's inner ring, spacer C, the pulley's bush. Both bodies' "
               "weight (689 N) reaches the case floor's lip through the locating bearing (§7).",
               "Departures from the first cut to make it buildable [IR]: the hub's lip above its bearing (so it carries the "
               "counter-rotor's 350 N); the counter-rotor's gear bolted by a flange outside the bearing; the pinions' "
               f"bearings {pb['spacing_l_mm']:.0f} mm apart, the mesh {pb['overhang_a_mm']:.0f} mm outboard (the case's arithmetic; "
               f"the statics' 16 / 12 do not fit it): {pb['limit']['R_inner_N']:.0f} N at the limit, static safety "
               f"{pb['limit']['static_safety']:.0f}; the bell Ø144 / Ø164, a C open to the motor, clear of the belt.",
               "Backlash j_n 0.10-0.15 by shims under the cartridges' flanges and the rotor gear's spacer; POM-compatible "
               "grease in the closed case (§5)."])
    turned = dict(kind="turned", status="PROPOSED", status_text=DRIVE_STATUS, used_in="DRV-100")
    lines, calls = gear_marks(gr)
    mk, mk3 = subpart("reverser", "g_rotor")
    add("DRV-101", "Side gear, the rotor's, z 30 m 2, keyed", "the drive: the reverser", make=mk, make3d=mk3,
        material=SS305, qty=1, rho=7900.0, colour3d=(0.74, 0.76, 0.79), lines=lines, scale=1.0, section_vertical=True,
        detail=(10.0, 33.0), source="docs/drive-gear-belt.md §5; sim/drive_sizing_results.json gear",
        bore_text={25.0: "Ø25 H7", 40.0: "hub Ø40"},
        data=gear_rows(gr, "DRV-103 pinion z 20, × 3") + [("keyway", "8 P9 × 3.3 in the hub only (DIN 6885 A 8 × 7)")],
        notes=["The first cut's side gear (§5): z 30, m 2, b 12, 1.4305 (non-magnetic, as the shaft); the wheel of a "
               "1.5 : 1 set, re-machined to this drawing, or cut from bar.",
               "Keyed on the shaft's Ø25 journal in its own hub Ø40 × 12, not under the teeth: the small-end root is "
               f"Ø{gr['d_root_toe']:.1f} (§5). Keyway 8 P9 × 3.3 in the hub only.",
               "The mounting distance sets the mesh: shim the spacer under the hub (DRV-190) for the backlash.",
               TEETH, DRIVE_FLAG], **turned)
    lines, calls = gear_marks(gc)
    mk, mk3 = subpart("reverser", "g_cr")
    add("DRV-102", "Side gear, the counter-rotor's, z 30 m 2, flanged", "the drive: the reverser", make=mk, make3d=mk3,
        material=SS305, qty=1, rho=7900.0, colour3d=(0.74, 0.76, 0.79), lines=lines, scale=1.0, section_vertical=True,
        detail=(13.0, 42.0), level_tol=0.6, source="docs/drive-gear-belt.md §5; sim/unmodelled_parts.py side_gear",
        bore_text={31.0: "Ø31", 40.0: "relief Ø40 × 0.5"},
        data=gear_rows(gc, "DRV-103 pinion z 20, × 3") + [("flange", "Ø80 × 3, 6 × Ø4.5 on PCD Ø70")],
        notes=["The same teeth as DRV-101 (§5: two identical side gears), with a back flange Ø80 × 3 [IR]: bolted under "
               "the counter-rotor's hub (DRV-108) by six M4 (ISO 4762, A4) on PCD Ø70 at 0° / 60° …, between the pinions.",
               "Its back face holds the gear-end 6205-2Z's outer ring in the hub's seat; the relief Ø40 × 0.5 keeps it off "
               "the inner ring. Bore Ø31: 1.5 mm round the shaft's spacer tube (Ø28), which turns at 1200 rpm against it.",
               TEETH, DRIVE_FLAG], **turned)
    lines, calls = gear_marks(gp)
    mk, mk3 = subpart("reverser", "g_pinion")
    add("DRV-103", "Pinion, POM-C, z 20 m 2", "the drive: the reverser", make=mk, make3d=mk3,
        material="POM-C (acetal copolymer), natural, from annealed stock", qty=3, rho=1410.0, colour3d=(0.94, 0.93, 0.88),
        lines=lines, scale=1.0, section_vertical=True, detail=(3.0, 23.0), source="docs/drive-gear-belt.md §5",
        bore_text={10.0: "Ø10 H7 (pressed)", 14.0: "hub Ø14"},
        data=gear_rows(gp, "DRV-101 and DRV-102, side gears z 30"),
        notes=["POM-C, z 20, m 2, b 12: an idler, its two meshes balance, so it carries no torque on its shaft; pressed "
               "on its stainless stub shaft (DRV-104).",
               "Its Ø14 hub bears on the inner 6000-2Z's inner ring; mounting distance 38.00 from the apex (§8).",
               "Teeth cut (hob or shaper) or moulded; POM-C ≤ 60 °C (the VDI 2736-class limits of §5): bending 12 MPa, "
               "contact 30 MPa at the driver's limit (S 3.6 / 2.0).", TEETH, DRIVE_FLAG], **turned)
    mk, mk3 = subpart("reverser", "stub")
    add("DRV-104", "Stub shaft, Ø10, the pinion's", "the drive: the reverser", make=mk, material=SS305, qty=3,
        rho=7900.0, colour3d=(0.74, 0.76, 0.79), long=True, source="docs/drive-gear-belt.md §5 (Ø10, 2 × 6000-2Z)",
        notes=["Ø10 h6 over the pinion's seat (pressed) and the two 6000-2Z; the circlip's groove DIN 471 for 10 × 1 "
               "(Ø9.6 × 1.1) at the outer end [IR].",
               f"Bending at the driver's limit {pb['limit']['axle_sigma_MPa']:.0f} MPa, the mesh {pb['overhang_a_mm']:.0f} mm "
               "outboard of the inner bearing (sim/unmodelled_parts_results.json pinion_bearings).", DRIVE_FLAG], **turned)
    mk, mk3 = subpart("reverser", "cart")
    add("DRV-105", "Cartridge sleeve, the pinion's two 6000-2Z", "the drive: the reverser", make=mk, material=AL6, qty=3,
        rho=2700.0, colour3d=(0.83, 0.85, 0.89), long=True, source="docs/drive-gear-belt.md §5, §8 (the case's arithmetic)",
        bore_text={26.0: "Ø26 H7", 22.0: "land Ø22", 26.5: "Ø26.5"},
        notes=["The two 6000-2Z in Ø26 H7 seats either side of the 4 mm land; the inner one pressed from the inner end, "
               "the outer one from outside; Ø32 g6 in the case's bore Ø32 H7.",
               "The flange on the case's boss face (r 76): three M4 (ISO 4762, A4) on PCD Ø40; shims under it set the "
               "backlash j_n 0.10-0.15 (§5).",
               f"The bearings {pb['spacing_l_mm']:.0f} mm apart (the case's arithmetic, §8): the inner one takes "
               f"{pb['steady']['R_inner_N']:.0f} N steady, {pb['limit']['R_inner_N']:.0f} N at the driver's limit, a static "
               f"safety of {pb['limit']['static_safety']:.0f} (the first cut's statics: 16 mm, 141 N, 14).", DRIVE_FLAG],
        **turned)
    mk, mk3 = subpart("reverser", "case", turn=-U.PHI_P[0])
    add("DRV-106", "Gear case, the carrier and end-bearing housing", "the drive: the reverser", make=mk, material=AL6,
        qty=1, rho=2700.0, colour3d=(0.83, 0.85, 0.89), detail=(0.0, 83.0), scale=0.5,
        source="docs/drive-gear-belt.md §5, §7, §8; sim/unmodelled_parts.py gear_case",
        bore_text={52.0: "Ø52 H7 (6205)", 40.0: "lip Ø40", 88.0: "Ø88", 128.0: "Ø128"},
        tapped={2.5: "M3", 5.0: "M6"},
        data=[("bosses", "3 × Ø56 at the pinions' axes (30° / 150° / 270°; drawn at 0° / 120° / 240°), faces at r 76, 60 "
                         "above the floor's underside; bores Ø32 H7; three M4 × 10 on PCD Ø40 each"),
              ("floor", "17 thick: the seat Ø52 H7 × 15 from the top, the lip Ø40 × 2 under it"),
              ("flange", "Ø168 × 8 at the floor; three M6 from below on PCD Ø154 at 120° / 180° / 240°")],
        notes=["The carrier of the reverser and the frame's bottom end-bearing housing (§5, §8): it takes the gear's "
               "1.0 N·m steady, 5.2 N·m at the driver's limit, into the base plate.",
               "The locating 6205-2Z in the floor: the seat Ø52 H7 × 15 from the top on a lip Ø40, which takes both bodies' "
               "weight (689 N, §7); the retaining ring (DRV-190) over it on three M3 at PCD Ø58.",
               "The bosses at the pinions' axes (30° / 150° / 270°, 60 above the floor's underside) carry the cartridges "
               "(DRV-105); three M6 come up from under the base plate, through the bell, into the floor's flange Ø168 [IR: "
               "the first cut's case is the Ø144 barrel; the bosses and the flange are this drawing's].",
               "The top lip's bore Ø88 is the labyrinth over the hub; grease POM-compatible, the case closed.", DRIVE_FLAG],
        **turned)
    mk, mk3 = subpart("reverser", "bell", turn=210.0)
    add("DRV-107", "Bell, a C under the case floor", "the drive: the reverser", make=mk, material=AL6, qty=1, rho=2700.0,
        colour3d=(0.83, 0.85, 0.89), detail=(66.0, 86.0), source="docs/drive-gear-belt.md §8; sim/unmodelled_parts.py bell",
        notes=["Ø164 / Ø144 × 40 over 170°, open toward the motor so the belt passes and can be fitted without lifting the "
               "machine [IR]. The first cut's bell (r 64-72) would cut the belt's land (r 63.1-64.8).",
               "Clamped between the base plate and the case's flange by three M6 × 60 (ISO 4762, A4) from below through "
               "Ø6.6 at 120° / 180° / 240° (drawn turned 210°, so the section misses a hole).",
               f"It clears the 80T pulley by {clr['pulley_80T | bell']:.1f} mm and the belt by {bclr['belt | bell']:.1f} mm "
               "(sim/unmodelled_parts_results.json).", DRIVE_FLAG],
        **turned)
    mk, mk3 = subpart("reverser", "hub")
    add("DRV-108", "Counter-rotor hub, the gear-end bearing's", "the drive: the reverser", make=mk, material=AL6, qty=1,
        rho=2700.0, colour3d=(0.83, 0.85, 0.89), detail=(0.0, 41.0),
        source="docs/drive-gear-belt.md §5, §8; sim/unmodelled_parts.py cr_hub", tapped={4.2: "M5", 3.3: "M4"},
        notes=["z −8 to 10 (§8): the gear-end 6205-2Z in a seat Ø52 H7 × 15 open below, under a lip Ø44 that rests on its "
               "outer ring, so the counter-rotor's 350 N goes through it into the shaft (§5) [IR: the first cut drew the lip "
               "below, which would not carry the weight].",
               "Six M5 × 10 deep from the top on PCD Ø70 (30° / 90° …) for the end disc (DRV-109); six M4 × 8 deep from below "
               "on PCD Ø70 (0° / 60° …) for the side gear's flange (DRV-102).",
               "A metal island at the shaft's potential: the G10 disc insulates it from the counter-rotor's REF parts (§5).",
               DRIVE_FLAG], **turned)
    mk, mk3 = subpart("reverser", "disc", turn=-30.0)
    add("DRV-109", "End disc, G10, the counter-rotor's", "the drive: the reverser", make=mk, material=G10 + ", plate 10",
        qty=1, rho=1850.0, colour3d=(0.84, 0.76, 0.52), detail=(25.0, 45.0), scale=0.5,
        source="docs/drive-gear-belt.md §5 (the bottom spider re-purposed)",
        notes=["G10, 10 mm, r 30-156.5 (§5: the record's bottom frame spider re-purposed): it closes bridge ring A's end and "
               "carries the hub [IR: the bolting].",
               "Twelve M5 countersunk from below on PCD Ø288 into threaded inserts in bridge ring A's end face; six M5 "
               "countersunk from the top on PCD Ø70 into the hub (drawn turned 30°: a hub screw at 0°).", G10_MACH,
               DRIVE_FLAG], **turned)
    add("DRV-120", "The belt drive: pulleys, belt, motor on its plate", "the drive", "assembly", status="PROPOSED",
        status_text=DRIVE_STATUS, qty=1, sub="belt", layout="broad", window=(-86.0, 292.0, -138.0, 28.0),
        planes=[(0.0, "full")], label="SECTION A–A through the shaft's and the motor's axes",
        view3d=dict(dir=(0.6, -1.0, 1.1)), cut3d=False,
        groups=lambda M: [("belt Gates 750-5M-15", "P-013", "—", lambda n, k: n == "belt"),
                          ("pulley 80T and taper bush", "P-014", "—", lambda n, k: n in ("pulley_80T", "bush"), "1 + 1"),
                          ("pulley 20T", "P-014", "—", lambda n, k: n == "pulley_20T"),
                          ("motor, 200 W", "P-015", "—", lambda n, k: n == "motor"),
                          ("motor plate", "DRV-121", "Al 6082", lambda n, k: n == "motor_plate"),
                          ("the reverser (for reference)", "DRV-100", "—", lambda n, k: True)],
        source="docs/drive-gear-belt.md §6; sim/drive_sizing_results.json belt",
        notes=[DRIVE_FLAG,
               "HTD 5M, 15 wide, 750 long (150 teeth); 20T → 80T, 4 : 1: the motor at 2400 rpm for 600 rpm; centres 245.4 "
               "mm, the wrap on the 20T 158° (8 teeth in mesh), the belt at 4.0 m/s (§6).",
               "Tension 46 N static per strand by the motor plate's slots; the hub load 90 N (153 N at the limit) into the "
               "locating bearing (§6, §7). The pitch length at these centres 750.02 mm (sim/unmodelled_parts_results.json).",
               "The motor stands on its plate above the 20T pulley; the plate on a bracket of the frame (the frame is not "
               "drawn: placeholders, §9)."])
    mk, mk3 = subpart("belt", "plate", norm="c")
    add("DRV-121", "Motor plate, tensioning slots", "the drive: the belt", "block", mk, None, material=AL6 + ", plate 10",
        status="PROPOSED", status_text=DRIVE_STATUS, qty=1, used_in="DRV-120", rho=2700.0, colour3d=(0.83, 0.85, 0.89),
        source="docs/drive-gear-belt.md §6, §9 (the motor plate with tensioning slots)",
        views=("top", "front"),
        callouts=[("top", (25.0 * math.cos(math.radians(150)), 25.0 * math.sin(math.radians(150))), "Ø50 H8 THRU", (-0.8, 1.0)),
                  ("top", (24.75, -24.75), "4× M5 THRU on PCD Ø70, at 45°", (1.0, -0.45)),
                  ("top", (55.0, 38.0), "4 slots 6.6 × 26 at x ±45, y ±38", (0.6, 1.0))],
        notes=["120 × 100 × 10: the motor's spigot in Ø50 H8, its flange on four M5 at PCD Ø70 (45°) [IR: the 60 mm "
               "frame's class; confirm on the motor's drawing, P-015].",
               "Four slots 6.6 × 26 for M6 to the frame's bracket: 20 mm of travel along the belt's line for the tension.",
               DRIVE_FLAG])
    add("DRV-190", "The drive's spacers, rings, keys and fasteners", "the drive", "list", status="PROPOSED",
        status_text=DRIVE_STATUS, used_in="DRV-100, DRV-120", no_3d=True,
        heading="THE DRIVE'S SMALL PARTS (per machine)", source="sim/unmodelled_parts.py reverser_sub, belt_sub",
        cols=[("item", 52.0), ("specification", 160.0), ("qty", 20.0), ("used in", 36.0)],
        rows=[("spacer A", f"Ø25 / Ø28 × {-8.0 - (U.Z_APEX - U.TOE_SIDE):.1f}, 1.4305: the rotor gear's toe to the gear-end "
                           "bearing's inner ring (through the counter-rotor's gear)", 1, "DRV-100"),
              ("spacer B", "Ø25 / Ø32 × 3, 1.4305: the rotor gear's hub to the locating bearing's inner ring; shim it to "
                           "set the gear's mounting distance", 1, "DRV-100"),
              ("spacer C", f"Ø25 / Ø32 × {-94.0 - (U.Z_BELT - 0.5 * U.P80['S'] + 25.4):.1f}, 1.4305: the locating bearing to the "
                           "pulley's bush", 1, "DRV-100"),
              ("pinion spacer", "Ø10 / Ø14 × 4, 1.4305: between the two 6000-2Z's inner rings", 3, "DRV-100"),
              ("retaining ring", "Ø44 / Ø66 × 2, 1.4305, three Ø3.4 countersunk on PCD Ø58: over the locating bearing's "
                                 "outer ring, three M3 × 6 (ISO 10642, A4)", 1, "DRV-100"),
              ("shaft collar", "two-piece clamp collar Ø25, ≤ Ø40 × 10, stainless: over the gear-end bearing's inner ring, "
                               "it carries the rotor's weight into the stack [IR]", 1, "DRV-100"),
              ("key", "DIN 6885 A 8 × 7 × 12, stainless: the rotor gear in its hub", 1, "DRV-100"),
              ("lock nut", "SKF KM 5 (M25 × 1.5) with its tab washer MB 5: clamps the shaft's stack", 1, "DRV-100"),
              ("circlip", "DIN 471, 10 × 1, stainless: the stub shafts' outer ends", 3, "DRV-100"),
              ("shims", "Ø48 / Ø32, 0.05 / 0.1 / 0.2, stainless: under the cartridges' flanges (the backlash)", "3 sets",
               "DRV-100"),
              ("screws", "M4 × 10 ISO 4762 A4: 6 (the gear's flange to the hub), 9 (the cartridges); M5 × 12 ISO 10642 A4: "
                         "6 (the disc to the hub); M5 × 16 ISO 10642 A4 + 12 inserts M5: 12 (the disc to bridge ring A)",
               "33 + 12", "DRV-100"),
              ("bolts", "M6 × 60 ISO 4762 A4: 3 (from under the base plate through the bell into the case's flange); M5 × 16 "
                        "ISO 4762: 4 (the motor's flange); M6 × 20 + washers: 4 (the motor plate to its bracket)", 11,
               "DRV-100, DRV-120"),
              ("grease", "POM-compatible, synthetic (PTFE-thickened class): the meshes and the closed case [IR]", "—",
               "DRV-100")],
        notes=["Quantities from sim/unmodelled_parts.py reverser_sub and belt_sub; the drive is one per machine.",
               DRIVE_FLAG])


def bought_extra_entries(add):
    """the bought parts of the drive and of the magnetic pump's electronics (candidates from this session's search,
    2026-10-11: confirm each on the maker's current sheet before ordering)."""
    import unmodelled_parts as U
    st = lambda txt: dict(status="BOUGHT", status_text=txt)
    add("P-012", "Bearing, SKF 6000-2Z", "bought parts", "bought", lambda M: _nz(U.bearing(10.0, 26.0, 8.0)), None,
        material="deep groove ball bearing, 10 / 26 / 8, shielded both sides", qty=6, used_in="DRV-105, DRV-100",
        colour3d=(0.70, 0.72, 0.76), mass_kg=0.019, source="docs/drive-gear-belt.md §5 (2 × 6000-2Z a pinion)",
        **st("BOUGHT · for the drive's first cut (PROPOSED)"),
        spec=[("designation", "SKF 6000-2Z: deep groove ball bearing, shields both sides, greased for life"),
              ("bore / OD / width", "10 / 26 / 8 mm"),
              ("ratings", "C 4.75 kN, C0 1.96 kN (the first cut sized on 4.55 kN)"),
              ("speeds", "reference 67 000 r/min, limiting 34 000 r/min (2Z); here 900 rpm"),
              ("load", "the inner one 40 N steady, 195 N at the driver's limit (sim/unmodelled_parts_results.json)"),
              ("alternates", "FAG 6000-2Z, NSK 6000ZZ, NTN 6000ZZ (the same ISO 15 boundary)"),
              ("where", "two in each pinion's cartridge (DRV-105): six per machine")],
        notes=["Catalogue data as distributors' listings render it (2026-10-11): simplybearings.co.uk 6000-2Z-SKF; "
               "rgbautomatyka.pl 6000-2Z SKF. Re-read SKF's current page before ordering.",
               "Fits: the stub shaft Ø10 k5, the cartridge's seats Ø26 H7."])
    add("P-013", "Timing belt, Gates 750-5M-15 (HTD 5M)", "bought parts", "bought", lambda M: _nc(sub("belt").placed(
        [p for p in sub("belt").parts if p["name"] == "belt"][0])), None, material="HTD 5M timing belt, neoprene / glass "
        "cord", qty=1, used_in="DRV-120", colour3d=(0.18, 0.18, 0.19), views=("top", "front"), mass_kg=None,
        env_box=(34.0, 150.0, 258.0, 128.0), scale=0.5,
        source="docs/drive-gear-belt.md §6; sim/drive_sizing_results.json belt", **st("BOUGHT · for the drive's first cut (PROPOSED)"),
        spec=[("designation", "Gates 750-5M-15 PowerGrip HTD: HTD 5M, 750 mm pitch length, 150 teeth, 15 mm wide"),
              ("listing", "acorn-ind.co.uk, Gates metric timing belts (750-5M-15, EAN 5412571282061)"),
              ("duty", "steady pull 15 N; 60 N at the driver's limit: the 15 mm width needed (§6)"),
              ("tension", "46 N static per strand; the tight side ≤ 76 N against 375 N allowable (§6) [IR]"),
              ("drawn", "its land only, 1.74 mm from the pulleys' tips; the teeth sit in the grooves")],
        notes=["Any HTD 5M 750 × 15 of the same pitch length fits (Optibelt, ContiTech, Megadyne): to choose with the "
               "pulleys' maker."])
    add("P-014", "Pulleys HTD 5M: 80T taper-bush, 20T flanged", "bought parts", "bought", lambda M: compound([
        moved(_nz(compound([sub("belt").placed(p) for p in sub("belt").parts if p["name"] in ("pulley_80T", "bush")])), 0, 0, 0),
        moved(_nz(sub("belt").placed([p for p in sub("belt").parts if p["name"] == "pulley_20T"][0])), 105.0 - U.BELT["centre_mm"],
              0, 0)]), None, material="cast iron / Al pulleys, HTD 5M", qty="1 + 1", qty_index="1 + 1", used_in="DRV-120",
        colour3d=(0.83, 0.85, 0.89), views=("front", "top"), mass_kg=None, source="docs/drive-gear-belt.md §6",
        env_box=(34.0, 150.0, 258.0, 128.0), scale=0.5,
        make3d=lambda M: compound([
            _nz(compound([sub("belt").placed(p, True) for p in sub("belt").parts if p["name"] in ("pulley_80T", "bush")])),
            moved(_nz(sub("belt").placed([p for p in sub("belt").parts if p["name"] == "pulley_20T"][0], True)),
                  105.0 - U.BELT["centre_mm"], 0, 0)]),
        **st("BOUGHT · for the drive's first cut (PROPOSED)"),
        spec=[("80T", "TL80-5M-15: HTD 5M, 80 teeth, pitch Ø127.32, tip Ø126.18, hub Ø92, F 22, S 25, no flanges, for a "
                      "taper bush 1610 (beltingonline.com 80-5M-15)"),
              ("bush", "taper bush 1610, bore Ø25 with an 8 mm keyway, on the shaft's drive end"),
              ("20T", "P20-5M-15F: HTD 5M, 20 teeth, pitch Ø31.83, tip Ø30.69, flanges Ø36, hub Ø23, face 20.5, overall 26, "
                      "pilot bore 6 (ondrives.com); bored Ø14 H7, keyway 5 JS9, an M5 set screw [IR: the motor's shaft]"),
              ("drawn", "the 80T at left with its bush, the 20T at right, its hub up")],
        notes=["The first cut said '24 mm over the flanges' for the 80T: the catalogue's TL80-5M-15 has no flanges and is 25 "
               "through; the flanges are on the 20T (§6 to correct).",
               "Confirm the bush's bore and the 20T's bore with the shaft and the motor's drawing before ordering."])
    add("P-015", "Motor, BLDC 200 W 48 V (APBA60M048030-E), with driver", "bought parts", "bought",
        lambda M: _nc(U.motor_shape()), None, material="brushless DC motor, 60 mm flange, encoder", qty=1, used_in="DRV-120",
        colour3d=(0.20, 0.20, 0.22), views=("front", "top"), mass_kg=1.0, source="docs/drive-gear-belt.md §6",
        **st("BOUGHT · for the drive's first cut (PROPOSED)"),
        spec=[("motor", "Nanotec / SMD APBA60M048030-E: 200 W, 48 V, 3000 rpm, 0.64 N·m rated, 1.92 N·m peak, 6 A, IP65, "
                        "2500 CPR encoder, 60 mm flange (NEMA 24), body 110 mm, about 1 kg (smd.ee; nanotec.com)"),
              ("duty", "0.94 N·m at the belt, 61 W at its shaft (38 % of rated at 2400 rpm), 76 W electrical; run-up 32 s "
                       "at its rated torque (§4)"),
              ("driver", "a 48 V BLDC driver with a speed loop, ramps and a current limit at 1.5 × rated (the design's torque "
                         "fuse, §4.3): Nanotec's matching driver (to choose)"),
              ("supply", "48 V DC, 300 W"),
              ("alternates", "Oriental Motor BLV series 200 W (48 V DC driver); Nanotec DB80S048030 (283 W); a 0.25 kW "
                             "4-pole induction motor on a VFD, 24T / 56T (the economy line, §6)"),
              ("envelope", "the flange's PCD Ø70, the spigot Ø50 and the shaft Ø14 × 30 keyed are the 60 mm frame's class "
                           "[IR]: confirm on the maker's drawing")],
        notes=["The motor's flange stands on the motor plate (DRV-121), its shaft down into the 20T pulley.",
               "Datasheets: smd.ee/products/dc-brushless-motors/apba60m048030-e; nanotec.com 2881-apba60m048030-e."])
    add("P-016", "Schottky rectifiers D1*–D4*, DO-201AD", "bought parts", "bought", lambda M: U.diode_shape(), None,
        material="Schottky rectifier, axial DO-201AD", qty="2 + 2", qty_index="2 + 2", used_in="the rotor (place OPEN)",
        colour3d=(0.20, 0.20, 0.22), views=("front", "side"), mass_kg=0.0012,
        source="sim/parts-first-cut-findings.md §2.1, §4", **st("BOUGHT · for the first cut (PROPOSED)"),
        spec=[("D1*, D2*", "200 V Schottky, ≥ 3 A (5 A preferred): SMC Diode Solutions SB5200 (200 V, 5 A, VF 0.85 V typ. at "
                           "5 A, IFSM 120 A); alternates PANJIT MBR5200 (LCSC C268577), MCC SR5200-TP"),
              ("their duty", "VR 113 / 104 V; IF 0.81 A average, 1.00 A rms, 1.90 A peak: VR × 1.8"),
              ("D3*, D4*", "150 V Schottky (100 V at least), ≥ 3 A: SR5150 (150 V, 5 A, 0.92 V at 5 A, IFSM 150 A; DIYI, LCSC "
                           "C129840); alternate ST STPS3150RL (150 V, 3 A, LCSC C262964)"),
              ("their duty", "VR 58 / 60 V; IF 1.07 A average, 1.45 A rms, 2.27 A peak: VR × 2.5"),
              ("package", "DO-201AD: body Ø5.3 × 9.5 max., leads Ø1.3; the cathode band"),
              ("heat", "0.44-0.59 W a diode: on copper pads or a small heatsink")],
        notes=["With Schottky parts the pump runs as modelled (z 1.142, AH 444 A-turns, a 16 % kick threshold); 1N540x-class "
               "silicon costs 6 % of the AH (sim/parts-first-cut-findings.md §2.1).",
               "Listings: digikey SB5200 (6022615); lcsc.com C268577, C129840, C262964. Confirm on the maker's sheet."])
    cap, res = U.snubber_shapes()
    add("P-017", "Node snubbers: 22 nF PP film + 240 Ω (8 of each)", "bought parts", "bought",
        lambda M: compound(list(U.snubber_shapes())), None, material="PP film capacitor; ceramic composition resistor",
        qty="8 + 8", qty_index="8 + 8", used_in="the rotor (place OPEN)", colour3d=(0.25, 0.35, 0.65), views=("front", "top"),
        mass_kg=None, source="sim/parts-first-cut-findings.md §2.5, §4", **st("BOUGHT · for the first cut (PROPOSED)"),
        spec=[("C", "22 nF ±10 %, polypropylene film, ≥ 250 V DC, pulse-rated: KEMET R76 22 nF ±5 % 400 V DC, 10 mm pitch, "
                    "13 × 9 × 14 (RS 1353468); alternate Panasonic ECW-F series 250 V"),
              ("its duty", "≤ 113 V, ≤ 1.7 V/µs: × 2.2 at 250 V"),
              ("R", "240 Ω (E24), 0.5 W, pulse-rated, non-inductive: Ohmite OX221KE (220 Ω ±10 %, 1 W, ceramic composition, "
                    "pulse-withstanding, 300 V, Ø5.5 × 16.5); alternate OY221KE (2 W)"),
              ("its duty", "≤ 4.2 mW average, ≤ 0.30 W peak: × 118"),
              ("drawn", "the capacitor (leads down) and the resistor (axial) side by side")],
        notes=["The deck's frequency-scaled damping (sim/magnetic_doubler.py snub 'scaled'): tune R and C on the bench to the "
               "real winding capacitance and the diodes' recovery (§2.5). 220 Ω is the OX series' nearest stock value.",
               "Listings: uk.rs-online.com 1353468; digikey.ch OX221KE (823917)."])
    add("P-018", "AH bypass capacitor, 22 mF 10 V, snap-in", "bought parts", "bought", lambda M: U.snapin_shape(), None,
        material="aluminium electrolytic, snap-in", qty=2, used_in="the rotor, beside the hub (place OPEN)",
        colour3d=(0.20, 0.30, 0.55),
        views=("front", "top"), mass_kg=None, source="sim/parts-first-cut-findings.md §2.6, §4; sim/ah-steady-cusp-findings.md",
        **st("BOUGHT · for the first cut (PROPOSED)"),
        spec=[("rating", "22 mF, 6.3-10 V, 105 °C, ≥ 2 A rms at 120 Hz, ESR ≤ 20 mΩ, polarised: + to nodes d / b"),
              ("candidate", "Rubycon 10MXG22000MEFCSN30X30: 22 000 µF, 10 V, 105 °C, Ø30 × 30 snap-in, 10 mm pitch, 2.5 A rms "
                            "at 120 Hz, 3000 h at 105 °C (a retailer's listing; its ESR not found: confirm ≤ 20 mΩ)"),
              ("alternate", "Nichicon LGU1E223MELC: 22 mF, 25 V, 3.96 A, Ø35 × 35 (RS 846-6928)"),
              ("duty", "−0.54 … −0.44 V (nodes d / b positive), 0.63 A rms at 120 Hz, ≤ 1.3 mV the wrong way: × 12 on V, × 3.2 "
                       "on ripple"),
              ("mounting", "beside the hub, clamped against 20-40 g [RH]; the clamp not drawn (its place OPEN)")],
        notes=["The bypass is PROPOSED (sim/ah-steady-cusp-findings.md): it lifts the belt power to 18.13 W.",
               "Snap-in pins on a board or soldered tags; keep the leads short (0.63 A rms at 120 Hz)."])
    add("P-019", "Choke parts: EI-84 laminations, bobbin, wire, spacer", "bought parts", "bought",
        lambda M: U.laminations_shape(), None, material="M400-50A laminations; PA66-GF bobbin; Cu wire; PET film",
        make3d=lambda M: U.laminations_shape(5.0),
        qty="for 2 chokes", qty_index="2 sets", used_in="REL-720", colour3d=(0.66, 0.68, 0.73), views=("front", "top"),
        view3d=dict(dir=(0.5, -1.5, 0.45)),
        mass_kg=None, source="sim/parts-first-cut-findings.md §1; sim/parts_first_cut_results.json la_lb.chosen",
        **st("BOUGHT · for the first cut (PROPOSED)"),
        spec=[("laminations", "EI-84 scrapless (84 × 70, centre leg 28, outer legs 14, window 14 × 42), non-oriented SiFe "
                              "0.5 mm, M400-50A class (M235-35A halves the iron loss): about 67 E + 67 I a choke (35 mm at a "
                              "0.95 stacking factor)"),
              ("bobbin", "EI-84 for a 35 mm stack: 1.0 mm wall, 1.5 mm flanges, glass-filled PA66, UL 94 V-0"),
              ("wire", "Ø1.40 enamelled copper, grade 2 (IEC 60317), class 180 or better: 24.6 m a choke"),
              ("spacer", "PET film 0.063 mm, the E / I joint (all three legs); trim L to 0.146 H on test"),
              ("varnish, tape", "class F impregnating varnish (VPI); polyester tape 0.05 mm between the layers"),
              ("candidate", "no maker's EI-84 lamination or bobbin listing was found in this session's search: to the "
                            "specification")],
        notes=["Drawn: one E and one I lamination as delivered (0.5 mm), the E's legs up; the 3-D view shows ten of each, "
               "stacked.",
               "Any standard EI-84 bobbin for a 35 mm stack fits the winding as sized (sim/parts_first_cut.py winding())."])


COL_LV = (0.87, 0.55, 0.08)

# the general arrangement's sub-assemblies, by the parts' names and prototypes
GA_GROUPS = [
    ("the hub, locked", "HUB-200", "—", lambda n, k: k.startswith(("hub_", "ah_")), 1),
    ("the can, its discs and bushings", "CAN-400", "Al", lambda n, k: k in ("can", "can_disc_m") or k.startswith("bushing"), 1),
    ("decks A and B", "DCK-500", "—", lambda n, k: n.startswith(("A_", "B_")) and k not in ("deck_plate",) and
     any(n.startswith(f"{s}_{x}") for s in "AB" for x in ("D", "R", "C3", "C4", "C5", "C6", "C7", "C8", "Cs", "Z", "J_",
                                                          "lead_", "strap_", "cross_", "ring_lead_deck", "riser_deck",
                                                          "tap_deck")), 2),
    ("deck plates", "DCK-502", "G10", lambda n, k: k == "deck_plate"),
    ("Ca / Cb columns", "CAP-610", "Al", lambda n, k: k.startswith(("ca_n", "post_", "standoff", "boot")), 2),
    ("C1 / C2 varicap stacks", "CAP-600", "Al", lambda n, k: k.startswith(("rotor_vane", "stator_vane", "vane_spacer",
                                                                          "dowel", "stator_spacer", "tie_rod", "rod_nut",
                                                                          "end_ring")), 2),
    ("shaft halves, flanges, sleeves", "SHF-300", "—", lambda n, k: k.startswith(("shaft_", "flange", "sleeve", "shed")) or
     "lv_cable" in n, 2),
    ("bearing hubs: Ca|reluctance, end, bridge ring", "BRG-800/-801/-802", "—",
     lambda n, k: k in ("bearing", "spider", "spider_rel", "ring_bearing", "ring_spider", "ring_adapter") or
     k.startswith("ring_cartridge"), 6),
    ("reluctance sections A and B", "REL-710", "—", lambda n, k: k.startswith(("wu_", "w_")), 2),
    ("cage", "CGE-901", "G10", lambda n, k: k == "cage"),
    ("wiring: risers, taps, cross nets, ring leads", "DCK-501", "—", lambda n, k: True, "1 set"),
]


# ---------------------------------------------------------------------------------------------------------
# main
# ---------------------------------------------------------------------------------------------------------
BUILDERS = dict(turned=sheet_turned, block=sheet_block, bought=sheet_bought, list=sheet_list, assembly=sheet_assembly,
                wiring=sheet_wiring)
EXISTING = {"DCCREG-HUB-201": ("docs/drawings/DCCREG-HUB-201.pdf", "Rings A and B, Cu foil, beaded", "the hub", "HUB-200",
                               "docs/make_rings_drawing.py"),
            "DCCREG-UTR-101": ("docs/drawings/DCCREG-UTR-101.pdf", "Half-core, laminated (hand A; hand B mirror)",
                               "the reluctance pump", "REL-700", "docs/make_core_drawing.py")}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--only", nargs="*", default=None)
    ap.add_argument("--preview", default=None)
    ap.add_argument("--no-3d", action="store_true")
    ap.add_argument("--dpi", type=int, default=110)
    ap.add_argument("--merge", default=None, help="write the set as one PDF, a bookmark per sheet (pypdf)")
    a = ap.parse_args()
    t0 = time.time()
    set_dir = os.path.join(OUT_DIR, "set")
    os.makedirs(set_dir, exist_ok=True)
    if a.preview:
        os.makedirs(a.preview, exist_ok=True)
    M = Model()
    E = entries(M)
    # the existing drawings, each after its sub-assembly
    for dwg, (f, title, system, after, gen) in EXISTING.items():
        k = [i for i, e in enumerate(E) if e["dwg"] == f"DCCREG-{after}"][0]
        E.insert(k + 1, dict(dwg=dwg, title=title, system=system, kind="existing", file=f, status="LOCKED",
                             used_in=after, qty=None, gen=gen))
    sheet_no = {e["dwg"]: i + 1 for i, e in enumerate(E)}
    tmp = tempfile.mkdtemp(prefix="dset_")
    subs = {}

    def submodel(key):
        if key not in subs:
            subs[key] = SubModel(sub(key))
        return subs[key]
    ctx = dict(model=M, renderer=Renderer(not a.no_3d), tmp=tmp, sheet_no=sheet_no, n_sheets=len(E), preview=a.preview,
               dpi=a.dpi, out_pdf=lambda dwg: os.path.join(set_dir, f"{dwg}.pdf"), submodel=submodel)
    index = []
    try:
        for e in E:
            if e["kind"] == "existing":
                e["qty"] = {"DCCREG-HUB-201": "1 set", "DCCREG-UTR-101": f"{M.count['wu_core_pos']} + {M.count['wu_core_neg']}"}[e["dwg"]]
            elif e.get("qty") is None and e.get("make") is not None:
                e["qty"] = ""
            index.append(dict(sheet=sheet_no[e["dwg"]], dwg=e["dwg"], title=e["title"], system=e["system"], kind=e["kind"],
                              status=e.get("status", ""), qty=e.get("qty"), used_in=e.get("used_in", ""),
                              file=(e["file"] if e["kind"] == "existing" else os.path.relpath(ctx["out_pdf"](e["dwg"]), ROOT)),
                              gen=e.get("gen", "docs/make_drawing_set.py")))
            if a.only and e["dwg"] not in a.only and e["dwg"].replace("DCCREG-", "") not in a.only:
                continue
            t1 = time.time()
            if e["kind"] == "existing":
                continue
            if e["kind"] == "index":
                sheet_index(e, ctx, E)
            else:
                if e.get("make"):
                    e["shape"] = e["make"](M)
                if e.get("make3d"):
                    e["shape3d"] = e["make3d"](M)
                if e.get("make_parts3d"):
                    e["parts3d"] = e["make_parts3d"](M)
                BUILDERS[e["kind"]](e, ctx)
            print(f"{e['dwg']:18s} {e['kind']:9s} {time.time() - t1:5.1f} s  {e['title']}", flush=True)
    finally:
        ctx["renderer"].close()
    if not a.only:
        json.dump(dict(note="the drawing set (docs/make_drawing_set.py): every sheet in order", built=DATE,
                       model="docs/geometry/tube/tube-r150-n6-air6-wound-g0p5-6br-hub50-layout.step", sheets=index),
                  open(INDEX_JSON, "w"), indent=1, default=str)
    print(f"{len(E)} sheets; {time.time() - t0:.0f} s")
    if a.merge:
        merge(a.merge)


def merge(out):
    """the set as one PDF from docs/drawings/set-index.json, in its order, a bookmark per sheet."""
    from pypdf import PdfReader, PdfWriter
    idx = json.load(open(INDEX_JSON))
    w = PdfWriter()
    for s_ in idx["sheets"]:
        start = len(w.pages)
        for pg in PdfReader(os.path.join(ROOT, s_["file"])).pages:
            w.add_page(pg)
        w.add_outline_item(f"{s_['sheet']}. {s_['dwg']}: {s_['title']}", start)
    w.add_metadata({"/Title": "DCCREG turbine - the drawing set (Rev A drafts for quotation)",
                    "/Subject": f"built {idx['built']} from {idx['model']} by docs/make_drawing_set.py"})
    with open(out, "wb") as f:
        w.write(f)
    print(f"wrote {out}: {len(w.pages)} pages")


if __name__ == "__main__":
    main()
