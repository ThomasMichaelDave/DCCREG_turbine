"""docs/make_core_drawing.py -- the manufacturing drawing of the utron's SiFe half-core, DCCREG-UTR-101 (A3):

  * views from the B-rep by hidden-line removal (OCP HLR): A the lamination profile (2:1), B from above and C from the
    break-face side (1:1), with dimensions, tolerance frames, datums, notes, a stack-data table and the title block;
  * a shaded 3-D view of the stack (three.js in headless Chromium, tools/step-viewer/part.html; skipped without it);
  * DCCREG-UTR-101_lamination.dxf: the as-cut lamination (tip face R130.20, 0.20 mm grinding stock), for laser / EDM;
  * DCCREG-UTR-101_half-core_A.step: the finished stack, hand A.
Every number comes from sim/utron_profile.spec for the chosen operating point, in the part frame: x' from datum B (the
break face, v = brk / 2), y' from datum A (the face on the NiFe strip, u = u_n1), z' along the stack.
Usage: python3 docs/make_core_drawing.py ["g 0.5 / 6 bridges / 1200 rpm"]
"""
import functools
import http.server
import json
import math
import os
import socketserver
import sys
import threading

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt                                    # noqa: E402
from matplotlib.patches import Polygon, Rectangle, Circle, Arc     # noqa: E402
import numpy as np                                                 # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(ROOT, "sim"))
import utron_profile as U                                          # noqa: E402
import tube_geometry as T                                          # noqa: E402

DWG = "DCCREG-UTR-101"
OUT = os.path.join(HERE, "drawings")
STOCK = 0.20                       # grinding stock on the tip face, removed in OP 50 on the assembled rotor
SF = 0.95                          # stacking factor
LW_VIS, LW_THIN, LW_HID = 1.4, 0.6, 0.9      # pt: visible 0.5 mm, thin 0.2 mm, hidden 0.35 mm (ISO 128)
TXT = 7.4                          # pt, ~2.5 mm lettering
INK, DIMC = "#111111", "#1f3d66"


# ---------------------------------------------------------------------------------------------------------
# geometry in the part frame
# ---------------------------------------------------------------------------------------------------------
def frame(sp):
    """part-frame constants: the arc centre (the machine axis) and the profile corners."""
    xb, ya = sp["brk"] / 2, sp["u_n1"]
    s2, wp = sp["s"] / 2, sp["w_p"]
    return dict(cx=-xb, cy=-ya, W=s2 + wp - xb, x_in=s2 - xb, h_y=sp["u_y1"] - ya,
                holes=[(v - xb, u - ya) for u, v in sp["studs"]], d_hole=sp["stud_d"], L=sp["L"], R=sp["r_g"])


def arc_y(f, x, R):
    return math.sqrt(R ** 2 - (x - f["cx"]) ** 2) + f["cy"]


def solid(sp, stock=0.0):
    """the half-core stack, hand A, in the part frame (tip face R + stock)."""
    from OCP.BRepAlgoAPI import BRepAlgoAPI_Common, BRepAlgoAPI_Cut
    f = frame(sp)
    R = f["R"] + stock
    prof = [(0.0, 0.0), (f["W"], 0.0), (f["W"], f["h_y"] + 40.0), (f["x_in"], f["h_y"] + 40.0), (f["x_in"], f["h_y"]),
            (0.0, f["h_y"])]
    s = T.prism(prof, 0.0, f["L"])
    s = BRepAlgoAPI_Common(s, T.cyl_z(f["cx"], f["cy"], R, -1.0, f["L"] + 1.0)).Shape()
    for (x, y) in f["holes"]:
        s = BRepAlgoAPI_Cut(s, T.cyl_z(x, y, f["d_hole"] / 2, -1.0, f["L"] + 1.0)).Shape()
    return s


def hlr(shape, d, xd):
    """visible and hidden edges of a parallel projection (view direction d toward the viewer, x axis xd)."""
    from OCP.HLRBRep import HLRBRep_Algo, HLRBRep_HLRToShape
    from OCP.HLRAlgo import HLRAlgo_Projector
    from OCP.gp import gp_Ax2, gp_Pnt, gp_Dir
    from OCP.TopExp import TopExp_Explorer
    from OCP.TopAbs import TopAbs_EDGE
    from OCP.TopoDS import TopoDS
    from OCP.BRepAdaptor import BRepAdaptor_Curve
    from OCP.GCPnts import GCPnts_QuasiUniformDeflection
    algo = HLRBRep_Algo(); algo.Add(shape)
    algo.Projector(HLRAlgo_Projector(gp_Ax2(gp_Pnt(0, 0, 0), gp_Dir(*d), gp_Dir(*xd))))
    algo.Update(); algo.Hide()
    h = HLRBRep_HLRToShape(algo)
    out = dict(vis=[], hid=[])
    for key, fns in (("vis", (h.VCompound, h.OutLineVCompound)), ("hid", (h.HCompound, h.OutLineHCompound))):
        for fn in fns:
            c = fn()
            if c.IsNull():
                continue
            e = TopExp_Explorer(c, TopAbs_EDGE)
            while e.More():
                cv = BRepAdaptor_Curve(TopoDS.Edge(e.Current()))
                dd = GCPnts_QuasiUniformDeflection(cv, 0.005)
                if dd.IsDone() and dd.NbPoints() > 1:
                    out[key].append(np.array([[dd.Value(i).X(), dd.Value(i).Y()] for i in range(1, dd.NbPoints() + 1)]))
                e.Next()
    return out


def write_step(shape, path, name):
    from OCP.STEPCAFControl import STEPCAFControl_Writer
    from OCP.STEPControl import STEPControl_AsIs
    from OCP.TDocStd import TDocStd_Document
    from OCP.TCollection import TCollection_ExtendedString
    from OCP.XCAFDoc import XCAFDoc_DocumentTool, XCAFDoc_ColorType
    from OCP.TDataStd import TDataStd_Name
    from OCP.Quantity import Quantity_Color, Quantity_TypeOfColor
    from OCP.Interface import Interface_Static
    doc = TDocStd_Document(TCollection_ExtendedString("XmlOcaf"))
    st = XCAFDoc_DocumentTool.ShapeTool_s(doc.Main())
    lab = st.AddShape(shape, False)
    TDataStd_Name.Set_s(lab, TCollection_ExtendedString(name))
    XCAFDoc_DocumentTool.ColorTool_s(doc.Main()).SetColor(lab, Quantity_Color(*T.COL["sife"], Quantity_TypeOfColor.Quantity_TOC_RGB),
                                                         XCAFDoc_ColorType.XCAFDoc_ColorSurf)
    Interface_Static.SetCVal_s("write.step.product.name", name)
    w = STEPCAFControl_Writer(); w.SetNameMode(True); w.SetColorMode(True)
    w.Transfer(doc, STEPControl_AsIs); w.Write(path)
    return path


def write_dxf(path, sp, stock):
    """the as-cut lamination (one part for both hands; hand B = turned over), DXF R12, mm, origin at datum A / B."""
    f = frame(sp)
    R = f["R"] + stock
    y_out, y_in = arc_y(f, f["W"], R), arc_y(f, f["x_in"], R)
    a_out = math.degrees(math.atan2(y_out - f["cy"], f["W"] - f["cx"]))
    a_in = math.degrees(math.atan2(y_in - f["cy"], f["x_in"] - f["cx"]))
    ents = []
    line = lambda a, b: ents.append(("LINE", a, b))
    line((0, 0), (f["W"], 0)); line((f["W"], 0), (f["W"], y_out))
    ents.append(("ARC", (f["cx"], f["cy"]), R, a_out, a_in))
    line((f["x_in"], y_in), (f["x_in"], f["h_y"])); line((f["x_in"], f["h_y"]), (0, f["h_y"])); line((0, f["h_y"]), (0, 0))
    for (x, y) in f["holes"]:
        ents.append(("CIRCLE", (x, y), f["d_hole"] / 2))
    g = ["0", "SECTION", "2", "HEADER", "9", "$ACADVER", "1", "AC1009", "9", "$INSUNITS", "70", "4", "0", "ENDSEC",
         "0", "SECTION", "2", "ENTITIES"]
    for e in ents:
        if e[0] == "LINE":
            (x0, y0), (x1, y1) = e[1], e[2]
            g += ["0", "LINE", "8", "CUT", "10", f"{x0:.4f}", "20", f"{y0:.4f}", "30", "0.0", "11", f"{x1:.4f}", "21", f"{y1:.4f}", "31", "0.0"]
        elif e[0] == "ARC":
            (x, y), r, a0, a1 = e[1], e[2], e[3], e[4]
            g += ["0", "ARC", "8", "CUT", "10", f"{x:.4f}", "20", f"{y:.4f}", "30", "0.0", "40", f"{r:.4f}", "50", f"{a0:.6f}", "51", f"{a1:.6f}"]
        else:
            (x, y), r = e[1], e[2]
            g += ["0", "CIRCLE", "8", "CUT", "10", f"{x:.4f}", "20", f"{y:.4f}", "30", "0.0", "40", f"{r:.4f}"]
    g += ["0", "TEXT", "8", "NOTES", "10", "0.0", "20", "-4.0", "30", "0.0", "40", "1.5", "1",
          f"{DWG} lamination, as cut (tip face R{R:.2f}), M235-35A 0.35 mm; one part for both hands (hand B = turned over)"]
    g += ["0", "ENDSEC", "0", "EOF"]
    open(path, "w").write("\n".join(g) + "\n")
    return dict(y_out=y_out, y_in=y_in)


def render_3d(sp, png):
    """the stack shaded with its edges (tools/step-viewer/part.html), or None without Chromium / three.js."""
    viewer = os.path.join(ROOT, "tools", "step-viewer")
    if not os.path.isdir(os.path.join(viewer, "node_modules", "three")):
        print("3-D view skipped: run `npm install` in tools/step-viewer")
        return None
    import step_to_glb as G
    step = os.path.join(OUT, f"{DWG}_half-core_A.step")
    glb = os.path.join(OUT, f"_{DWG}_part.glb")
    products, inst = G.read_assembly(step)
    meshes, nodes = [], []
    for key, (shape, col, name) in products.items():
        meshes.append((name, col, 0.6, *G.tessellate(shape, 0.02, 0.1)))
    nodes = [(0, M, lab, {}) for k, M, lab in inst]
    G.write_glb(glb, meshes, nodes, title=DWG)
    class Quiet(http.server.SimpleHTTPRequestHandler):
        def log_message(self, *a):
            pass
    srv = socketserver.TCPServer(("127.0.0.1", 0), functools.partial(Quiet, directory=ROOT))
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    try:
        from playwright.sync_api import sync_playwright
        with sync_playwright() as p:
            b = p.chromium.launch(executable_path=os.environ.get("CHROMIUM", "/opt/pw-browsers/chromium"),
                                  args=["--use-angle=swiftshader", "--enable-unsafe-swiftshader", "--ignore-gpu-blocklist"])
            pg = b.new_page(viewport={"width": 1240, "height": 520}, device_scale_factor=2)
            rel = os.path.relpath(glb, ROOT)
            pg.goto(f"http://127.0.0.1:{srv.server_address[1]}/tools/step-viewer/part.html?model=/{rel}"
                    "&dir=1.0,0.62,0.78&up=0,1,0&color=b9bdc5")
            pg.wait_for_function("window.ready === true", timeout=120000)
            pg.screenshot(path=png)
            b.close()
    finally:
        srv.shutdown()
        os.remove(glb)
    return png


# ---------------------------------------------------------------------------------------------------------
# drafting primitives on an A3 sheet (all in sheet mm)
# ---------------------------------------------------------------------------------------------------------
class Sheet:
    def __init__(self):
        self.fig = plt.figure(figsize=(420 / 25.4, 297 / 25.4))
        self.ax = self.fig.add_axes((0, 0, 1, 1))
        self.ax.set_xlim(0, 420); self.ax.set_ylim(0, 297); self.ax.set_aspect("equal"); self.ax.axis("off")

    def line(self, pts, lw=LW_THIN, color=INK, ls="-", z=3):
        pts = np.asarray(pts, float)
        self.ax.plot(pts[:, 0], pts[:, 1], color=color, lw=lw, ls=ls, solid_capstyle="butt", zorder=z)

    def text(self, x, y, s, size=TXT, ha="left", va="baseline", rot=0, color=INK, weight="normal", z=5, **kw):
        self.ax.text(x, y, s, fontsize=size, ha=ha, va=va, rotation=rot, color=color, weight=weight, zorder=z,
                     family="DejaVu Sans", **kw)

    def arrow(self, tip, toward, size=2.6, color=DIMC):
        """a filled 15-degree arrowhead with its tip at `tip`, pointing away from `toward`."""
        t, f = np.asarray(tip, float), np.asarray(toward, float)
        d = (t - f) / (np.linalg.norm(t - f) or 1.0)
        n = np.array([-d[1], d[0]])
        base = t - d * size
        w = size * math.tan(math.radians(9))
        self.ax.add_patch(Polygon([t, base + n * w, base - n * w], closed=True, fc=color, ec=color, lw=0.3, zorder=4))

    def dim(self, p1, p2, off, text, outside=False, txt_off=1.1, color=DIMC, ext=True):
        """aligned linear dimension between feature points p1, p2 (sheet mm); off: offset vector of the dimension line."""
        p1, p2, off = np.asarray(p1, float), np.asarray(p2, float), np.asarray(off, float)
        a, b = p1 + off, p2 + off
        on = off / (np.linalg.norm(off) or 1.0)
        if ext:
            for p, q in ((p1, a), (p2, b)):
                if np.linalg.norm(q - p) > 0.5:
                    self.line([p + on * 0.8, q + on * 1.6], lw=LW_THIN * 0.8, color=color)
        d = (b - a) / np.linalg.norm(b - a)
        if outside:
            self.line([a - d * 6, b + d * 6], lw=LW_THIN * 0.8, color=color)
            self.arrow(a, a - d); self.arrow(b, b + d)
        else:
            self.line([a, b], lw=LW_THIN * 0.8, color=color)
            self.arrow(a, b); self.arrow(b, a)
        ang = math.degrees(math.atan2(d[1], d[0]))
        if ang > 90.1 or ang < -89.9:
            ang += 180
        m = 0.5 * (a + b)
        nrm = np.array([-math.sin(math.radians(ang)), math.cos(math.radians(ang))])
        # anchor mode: centred along the dimension line and sitting on its side, at any angle (the default mode aligns
        # the rotated bounding box, which puts a vertical value above the midpoint)
        self.text(*(m + nrm * txt_off), text, ha="center", va="bottom", rot=ang, color=color, rotation_mode="anchor")

    def leader(self, tip, knee, text, color=DIMC, ha="left", arrow=True):
        tip, knee = np.asarray(tip, float), np.asarray(knee, float)
        end = knee + np.array([6.0 if ha == "left" else -6.0, 0.0])
        self.line([tip, knee, end], lw=LW_THIN * 0.8, color=color)
        if arrow:
            self.arrow(tip, knee, color=color)
        self.text(end[0] + (0.8 if ha == "left" else -0.8), end[1] - 0.9, text, ha=ha, color=color)

    def fcf(self, x, y, cells, h=5.0, color=INK):
        """feature control frame from its lower-left corner; cells: ('flat'|'perp'|'prof'|'pos'|'par'|text, width)."""
        x0 = x
        for c, w in cells:
            self.ax.add_patch(Rectangle((x0, y), w, h, fill=False, ec=color, lw=LW_THIN, zorder=5))
            cx, cy = x0 + w / 2, y + h / 2
            if c == "flat":
                self.line([(cx - 2.0, cy - 1.0), (cx - 0.8, cy + 1.0), (cx + 2.0, cy + 1.0), (cx + 0.8, cy - 1.0), (cx - 2.0, cy - 1.0)], lw=0.8, color=color)
            elif c == "perp":
                self.line([(cx - 1.8, cy - 1.4), (cx + 1.8, cy - 1.4)], lw=0.8, color=color)
                self.line([(cx, cy - 1.4), (cx, cy + 1.6)], lw=0.8, color=color)
            elif c == "par":
                self.line([(cx - 1.6, cy - 1.4), (cx - 0.4, cy + 1.4)], lw=0.8, color=color)
                self.line([(cx + 0.2, cy - 1.4), (cx + 1.4, cy + 1.4)], lw=0.8, color=color)
            elif c == "prof":
                self.ax.add_patch(Arc((cx, cy - 1.2), 4.2, 4.2, theta1=0, theta2=180, ec=color, lw=0.8, zorder=6))
                self.line([(cx - 2.1, cy - 1.2), (cx + 2.1, cy - 1.2)], lw=0.8, color=color)
            elif c == "pos":
                self.ax.add_patch(Circle((cx, cy), 1.3, fill=False, ec=color, lw=0.8, zorder=6))
                self.line([(cx - 2.1, cy), (cx + 2.1, cy)], lw=0.8, color=color)
                self.line([(cx, cy - 2.1), (cx, cy + 2.1)], lw=0.8, color=color)
            else:
                self.text(cx, cy - 1.0, c, ha="center", color=color)
            x0 += w
        return x0

    def datum(self, foot, direction, letter):
        """datum feature symbol: a filled triangle on the feature at `foot`, a stem along `direction`, the letter box."""
        f, d = np.asarray(foot, float), np.asarray(direction, float) / np.linalg.norm(direction)
        n = np.array([-d[1], d[0]])
        self.ax.add_patch(Polygon([f + n * 1.6, f - n * 1.6, f + d * 2.6], closed=True, fc=INK, ec=INK, lw=0.3, zorder=6))
        top = f + d * 7.0
        self.line([f + d * 2.6, top], lw=LW_THIN, color=INK)
        c = top + d * 2.6
        self.ax.add_patch(Rectangle((c[0] - 2.6, c[1] - 2.6), 5.2, 5.2, fill=False, ec=INK, lw=LW_THIN, zorder=6))
        self.text(c[0], c[1] - 1.05, letter, ha="center", weight="bold")

    def basic(self, x, y, s, ha="center", rot=0, color=DIMC):
        """a basic (theoretically exact) dimension value: boxed."""
        self.ax.text(x, y, s, fontsize=TXT, ha=ha, va="bottom", rotation=rot, color=color, zorder=6, family="DejaVu Sans",
                     bbox=dict(boxstyle="square,pad=0.18", fc="white", ec=color, lw=0.5))

    def view(self, edges, origin, scale, rot=None, hidden=True):
        """place HLR edges: sheet = origin + scale * (rotated) view coordinates."""
        def tr(P):
            P = P if rot is None else P @ np.asarray(rot, float).T
            return np.asarray(origin, float) + scale * P
        for P in edges["vis"]:
            self.line(tr(P), lw=LW_VIS)
        if hidden:
            for P in edges["hid"]:
                self.line(tr(P), lw=LW_HID * 0.8, ls=(0, (3.0, 1.6)))
        return tr

    def chain(self, a, b):
        self.line([a, b], lw=LW_THIN * 0.8, color=INK, ls=(0, (9, 2, 1.5, 2)))


# ---------------------------------------------------------------------------------------------------------
# the sheet
# ---------------------------------------------------------------------------------------------------------
def main(pick="g 0.5 / 6 bridges / 1200 rpm"):
    os.makedirs(OUT, exist_ok=True)
    op = json.load(open(os.path.join(ROOT, "sim", "pole_design_variants_op.json")))["designs"][pick]
    sp = U.spec(op["design"], op["best"])
    f = frame(sp)
    fin = solid(sp)
    step = write_step(fin, os.path.join(OUT, f"{DWG}_half-core_A.step"), f"{DWG} half-core, hand A (finished)")
    cut = write_dxf(os.path.join(OUT, f"{DWG}_lamination.dxf"), sp, STOCK)
    png3d = render_3d(sp, os.path.join(OUT, f"_{DWG}_3d.png"))
    W, xi, hy, L, R = f["W"], f["x_in"], f["h_y"], f["L"], f["R"]
    y_in, y_out = arc_y(f, xi, R), arc_y(f, W, R)
    area = (U._area([(x, y) for x, y in [(0, 0), (W, 0), (W, y_out)] + [(xi + (W - xi) * (1 - k / 60),
            arc_y(f, xi + (W - xi) * (1 - k / 60), R)) for k in range(61)] + [(xi, hy), (0, hy)]])
            - len(f["holes"]) * math.pi * (f["d_hole"] / 2) ** 2)
    mass = area * L * SF * 1e-9 * U.RHO_FE
    n_lam = int(round(L * SF / 0.35))

    S = Sheet()
    ax = S.ax
    # frame and zones
    ax.add_patch(Rectangle((20, 10), 390, 277, fill=False, ec=INK, lw=1.6, zorder=2))
    ax.add_patch(Rectangle((5, 5), 410, 287, fill=False, ec=INK, lw=0.4, zorder=2))

    # ---------------- VIEW A: lamination profile, 2:1 ----------------
    sA, oA = 2.0, np.array([84.0, 172.0])
    eA = hlr(fin, (0, 0, 1), (1, 0, 0))
    S.view(eA, oA, sA, hidden=False)
    P = lambda x, y: oA + sA * np.array([x, y])
    S.text(28, 278, "VIEW A   LAMINATION PROFILE   2 : 1", size=9.5, weight="bold")
    for (x, y) in f["holes"]:
        S.chain(P(x - 5.2, y), P(x + 5.2, y)); S.chain(P(x, y - 5.2), P(x, y + 5.2))
    ex = lambda a, b: S.line([a, b], lw=LW_THIN * 0.8, color=DIMC)          # an extension line
    # widths: B to the tip's inner face inside the slot, the overall width below
    ex(P(0, hy) + (0, 0.8), P(0, hy + 13.0))
    S.dim(P(0, hy + 6.5), P(xi, hy + 6.5), (0, 0), f"{xi:.2f} ±0.05", ext=False)
    S.dim(P(0, 0), P(W, 0), (0, -9), f"{W:.2f} ±0.05")
    S.dim(P(0, 0), P(0, hy), (-9, 0), f"{hy:.2f} ±0.05")
    for k, (x, y) in enumerate(f["holes"]):
        S.text(*(P(x, y) + np.array([5.2, 5.0])), f"H{k + 1}", size=TXT, weight="bold")
    # tip heights at its two edges (reference)
    S.dim(P(W, 0), P(W, y_out), (9, 0), f"({y_out:.2f})")
    ex(P(xi, y_in) + (0.8, 0), P(W, y_in) + (19.6, 0))
    S.dim(P(W, 0) + (18, 0), P(W, 0) + (18, sA * y_in), (0, 0), f"({y_in:.2f})", ext=False)
    # datum A on the extension of the bottom face (left), with its flatness; datum B on the extension of the break face
    ex(P(0, 0) + (-0.8, 0), P(0, 0) + (-34, 0))
    S.datum(P(0, 0) + (-26, 0), (0, -1), "A")
    S.fcf(P(0, 0)[0] - 26 - 3.4 - 18, P(0, 0)[1] - 12.2, [("flat", 7), ("0.02", 11)])
    ex(P(0, hy) + (0, 0.8), P(0, hy + 9.0))
    S.datum(P(0, hy + 4.5), (-1, 0), "B")
    S.fcf(P(0, 0)[0] - 13.2 - 24.4, P(0, hy + 4.5)[1] - 2.5, [("perp", 7), ("0.05", 11), ("A", 6)])
    # hole table (basic coordinates from B and A)
    hx0, hy0 = 148.0, 142.0
    cols = [("HOLE", 11), ("X from B", 17), ("Y from A", 17), ("SIZE", 34)]
    rows_h = [(f"H{k + 1}", f"{x:.2f}", f"{y:.2f}", f"Ø{f['d_hole']:.2f} +0.10/0 THRU") for k, (x, y) in enumerate(f["holes"])]
    for r_i, row in enumerate([tuple(c for c, _ in cols)] + rows_h):
        xx = hx0
        for (c, wc), val in zip(cols, row):
            yy = hy0 + 12.0 - 6.0 * r_i
            ax.add_patch(Rectangle((xx, yy), wc, 6.0, fill=False, ec=INK, lw=LW_THIN * 0.8, zorder=5))
            if r_i and c.startswith(("X", "Y")):
                S.basic(xx + wc / 2, yy + 1.5, val)
            else:
                S.text(xx + wc / 2, yy + 1.9, val, ha="center", weight="bold" if r_i == 0 else "normal", size=6.9)
            xx += wc
    S.text(hx0, hy0 + 19.6, "HOLE TABLE (basic positions)", size=TXT, weight="bold")
    # the two holes: callout through the open slot side, with their position tolerance
    hx, hy2 = f["holes"][1]
    tip_h = P(hx, hy2) + sA * f["d_hole"] / 2 * np.array([math.cos(math.radians(150)), math.sin(math.radians(150))])
    knee = P(-6.5, hy2 + 8.0)
    S.leader(tip_h, knee, f"H1, H2: 2× Ø{f['d_hole']:.2f} +0.10/0 THRU", ha="right")
    S.fcf(knee[0] - 6 - 39, knee[1] - 7.6, [("pos", 7), ("Ø0.10", 14), ("A", 6), ("B", 6), ("C", 6)])
    # the tip face: finished radius, as-cut radius, profile tolerance after OP 50
    xm = 0.5 * (xi + W)
    tip = P(xm, arc_y(f, xm, R))
    knee = tip + np.array([12, 16])
    S.leader(tip, knee, f"R{R:.2f} after OP 50  (R{R + STOCK:.2f} as cut)")
    S.fcf(knee[0] + 6, knee[1] + 2.4, [("prof", 7), ("0.04", 11), ("A", 6), ("B", 6)])
    S.text(knee[0] + 6, knee[1] + 9.0, "after OP 50 (note 5)", size=6.6, color=DIMC)
    # view arrows (reference-arrow method)
    for lab, tipp, dd in (("B", P(W - 3.5, y_out + 9), (0, -1)), ("C", P(-3.0, hy + 25.0), (1, 0))):
        tipp = np.asarray(tipp, float); dd = np.asarray(dd, float)
        S.line([tipp - dd * 12, tipp], lw=0.9, color=INK); S.arrow(tipp, tipp - dd, size=3.4, color=INK)
        S.text(*(tipp - dd * 15.5 + np.array([0, -1.7])), lab, size=11, weight="bold", ha="center")

    # ---------------- VIEW C: from the break face (along +x'), 1:1, z' to the right ----------------
    sC, oC = 1.0, np.array([214.0, 222.0])
    eC = hlr(fin, (-1, 0, 0), (0, 0, 1))
    S.view(eC, oC, sC)
    Q = lambda z, y: oC + sC * np.array([z, y])
    S.text(oC[0], 268.0, "VIEW C   1 : 1", size=9.5, weight="bold")
    S.dim(Q(0, 0), Q(L, 0), (0, -8), f"{L:.1f} ±0.1")
    S.datum(Q(0, y_in * 0.5), (-1, 0), "C")
    S.fcf(Q(0, 0)[0] - 30, Q(0, y_in * 0.5)[1] + 4.6, [("perp", 7), ("0.10", 11), ("A", 6)])
    S.leader(Q(L, y_in * 0.78), Q(L, y_in * 0.78) + np.array([14, 7]), "", arrow=True)
    S.fcf(Q(L, 0)[0] + 20, Q(L, y_in * 0.78)[1] + 4.5, [("par", 7), ("0.10", 11), ("C", 6)])
    for (x, y) in f["holes"]:
        S.chain(Q(-4, y), Q(L + 4, y))

    # ---------------- VIEW B: from above (onto the tip face), 1:1, z' to the right, x' up ----------------
    sB, oB = 1.0, np.array([214.0, 166.0])
    eB = hlr(fin, (0, 1, 0), (0, 0, 1))
    S.view(eB, oB, sB)
    B_ = lambda z, x: oB + sB * np.array([z, x])
    S.text(oB[0], 200.0, "VIEW B   1 : 1", size=9.5, weight="bold")
    S.dim(B_(L, 0), B_(L, W), (8, 0), f"({W:.2f})")
    S.dim(B_(L, xi), B_(L, W), (18, 0), f"({W - xi:.2f})")
    S.text(B_(L * 0.5, W)[0], B_(L * 0.5, W)[1] + 1.8, "tip face (R130, view A)", size=6.6, ha="center", color=DIMC)
    S.chain(B_(-4, f["holes"][0][0]), B_(L + 4, f["holes"][0][0]))

    # ---------------- 3-D view ----------------
    bx = (232.0, 72.0, 178.0, 76.0)
    ax.add_patch(Rectangle(bx[:2], bx[2], bx[3], fill=False, ec=INK, lw=LW_THIN, zorder=2))
    if png3d:
        img = plt.imread(png3d)
        h_img, w_img = img.shape[:2]
        k = min((bx[2] - 4) / w_img, (bx[3] - 10) / h_img)
        w_, h_ = w_img * k, h_img * k
        x_, y_ = bx[0] + (bx[2] - w_) / 2, bx[1] + 7 + (bx[3] - 10 - h_) / 2
        ax.imshow(img, extent=(x_, x_ + w_, y_, y_ + h_), zorder=1, interpolation="lanczos")
    S.text(bx[0] + 3, bx[1] + 2.8, "3-D VIEW, hand A: the L-profile end face, the outer face and the tip face (axonometric, not to scale)", size=TXT)

    # ---------------- stack data, under the notes ----------------
    tx, ty, tw = 24.0, 14.0, 200.0
    rows = [("LAMINATION / STACK DATA", ""),
            ("lamination", "one part for both hands (hand B = laminations turned over)"),
            ("thickness, material", "0.35 mm, M235-35A (EN 10106), coated both sides"),
            ("stack", f"{L:.1f} mm, ≈ {n_lam} laminations at a stacking factor ≥ {SF:.2f}"),
            ("section, mass", f"{area / 100:.2f} cm² net, {mass:.2f} kg per stack"),
            ("per machine", "6 stacks hand A + 6 stacks hand B (3 utrons per side, 2 sides)"),
            ("mates with", "NiFe neck strip on A, G10 spacer on B, G10 cheeks on C and its opposite end")]
    for i, (k, v) in enumerate(rows):
        yy = ty + 44 - i * 6.4
        S.text(tx + 2, yy, k, size=TXT, weight="bold" if i == 0 else "normal")
        S.text(tx + 38, yy, v, size=TXT)
        if i:
            S.line([(tx, yy + 4.6), (tx + tw, yy + 4.6)], lw=0.4)
    ax.add_patch(Rectangle((tx, ty + 1.2), tw, 47.5, fill=False, ec=INK, lw=LW_THIN, zorder=2))

    # ---------------- notes ----------------
    notes = [
        "NOTES",
        "1  Material: non-oriented electrical steel M235-35A to EN 10106, 0.35 mm, fully processed. Insulation coating on both sides:",
        "    C-5 (EN 10342) for an epoxy-bonded stack, or the supplier's self-bonding varnish for a varnish-bonded stack.",
        f"2  Laminations: laser or wire-EDM cut to the DXF {DWG}_lamination.dxf (as-cut profile, tip face R{R + STOCK:.2f}). Burr ≤ 0.02 mm,",
        "    all burrs to one side within a stack. No interlocks, rivets or welds: the two Ø6.40 holes are the only through-features.",
        f"3  Stack: {L:.1f} ±0.1 mm at a stacking factor ≥ {SF:.2f}; laminations aligned on datums A and B and the two holes; bonded",
        "    (self-bonding varnish cured to the supplier's cycle, or vacuum epoxy). Hand B is stacked from laminations turned over.",
        "4  Stress-relief anneal after cutting (optional, to agree): 750 °C for 2 h in a non-oxidising atmosphere, before bonding.",
        "    Epoxy route only: a self-bonding varnish does not survive the anneal.",
        f"5  Tip face: supplied as cut to R{R + STOCK:.2f} ({STOCK:.2f} mm stock). OP 50 (by DCCREG, on the assembled rotor) finishes it to",
        f"    R{R:.2f}: wire EDM or a light grind, then deburr and re-varnish the face. The profile tolerance on the tip face applies after OP 50.",
        f"    The centre of R{R:.0f} is the machine axis: basic {-f['cx']:.2f} from B (away from the tip) and {-f['cy']:.2f} below A.",
        "6  Face A seats the NiFe neck strip (a lap joint in the magnetic circuit): keep A flat, clean and free of burrs.",
        "7  Marking: hand (A / B) and stack number on the tip's outer face (x' = 23) by paint or laser; never on A, B, C or the tip face.",
        "8  Inspection: profile and holes on the bonded stack (CMM or optical); stack height; interlaminar insulation by sample",
        "    (Franklin test, IEC 60404-11).",
        "9  General tolerances ISO 2768-mK. Dimensions in mm. Break sharp edges 0.1 max, except the tip-face edges (keep sharp).",
        "10 Views by reference arrows (ISO 128-30). Boxed values are basic dimensions. Do not scale from this drawing.",
    ]
    for i, n in enumerate(notes):
        S.text(24, 141 - i * 4.25, n, size=TXT, weight="bold" if i == 0 else "normal")

    # ---------------- revision table ----------------
    rx, ry = 300.0, 268.0
    ax.add_patch(Rectangle((rx, ry), 110, 19, fill=False, ec=INK, lw=LW_THIN, zorder=2))
    S.line([(rx, ry + 12.5), (rx + 110, ry + 12.5)], lw=0.5); S.line([(rx, ry + 6.3), (rx + 110, ry + 6.3)], lw=0.5)
    S.line([(rx + 12, ry), (rx + 12, ry + 12.5)], lw=0.5); S.line([(rx + 34, ry), (rx + 34, ry + 12.5)], lw=0.5)
    S.text(rx + 2, ry + 14.4, "REVISIONS", size=TXT, weight="bold")
    S.text(rx + 2, ry + 8.2, "Rev", size=TXT); S.text(rx + 14, ry + 8.2, "Date", size=TXT); S.text(rx + 36, ry + 8.2, "Description", size=TXT)
    S.text(rx + 2, ry + 2.0, "A", size=TXT); S.text(rx + 14, ry + 2.0, "2026-10-08", size=TXT)
    S.text(rx + 36, ry + 2.0, "First issue, draft for quotation", size=TXT)

    # ---------------- title block ----------------
    x0, y0, w, h = 230.0, 10.0, 180.0, 58.0
    ax.add_patch(Rectangle((x0, y0), w, h, fill=False, ec=INK, lw=1.2, zorder=2))
    rows_y = [y0 + 46, y0 + 36, y0 + 26, y0 + 16, y0 + 8]
    for yy in rows_y:
        S.line([(x0, yy), (x0 + w, yy)], lw=0.6)
    S.line([(x0 + 120, y0), (x0 + 120, y0 + 46)], lw=0.6)
    S.line([(x0 + 60, y0), (x0 + 60, y0 + 26)], lw=0.6)
    S.text(x0 + 3, y0 + 50.5, "DCCREG turbine   ·   wound utron, magnetic doubler (rotor)", size=8.2)
    S.text(x0 + 3, y0 + 39.0, "HALF-CORE, LAMINATED   (hand A; hand B mirror)", size=10.5, weight="bold")
    S.text(x0 + 3, y0 + 29.0, "Material: M235-35A, 0.35 mm (EN 10106), bonded stack", size=TXT)
    S.text(x0 + 3, y0 + 19.0, f"Mass: {mass:.2f} kg", size=TXT); S.text(x0 + 63, y0 + 19.0, "Units: mm", size=TXT)
    S.text(x0 + 3, y0 + 10.6, "Scale: 2:1 (A), 1:1 (B, C)", size=TXT); S.text(x0 + 63, y0 + 10.6, "Tolerances: ISO 2768-mK", size=TXT)
    S.text(x0 + 3, y0 + 2.6, "Drawn: generated from sim/utron_profile.py", size=6.6)
    S.text(x0 + 63, y0 + 2.6, "Checked: —      Approved: —", size=6.6)
    S.text(x0 + 123, y0 + 39.0, "Drawing no.", size=6.6); S.text(x0 + 123, y0 + 29.4, DWG, size=12, weight="bold")
    S.text(x0 + 123, y0 + 19.0, "Rev A (draft)   Sheet 1 / 1   A3", size=TXT)
    S.text(x0 + 123, y0 + 10.6, "Date: 2026-10-08", size=TXT)
    S.text(x0 + 123, y0 + 2.6, "DRAFT FOR QUOTATION", size=7.6, weight="bold", color="#9a3412")

    pdf = os.path.join(OUT, f"{DWG}.pdf")
    S.fig.savefig(pdf)
    S.fig.savefig(os.path.join(OUT, f"{DWG}.png"), dpi=160)
    plt.close(S.fig)
    if png3d:
        os.replace(png3d, os.path.join(OUT, f"{DWG}_3d.png"))
    print(json.dumps(dict(pdf=os.path.relpath(pdf, ROOT), step=os.path.relpath(step, ROOT), area_cm2=area / 100, mass_kg=mass,
                          laminations=n_lam, as_cut_heights=cut, finished_heights=dict(y_in=y_in, y_out=y_out)), default=float))


if __name__ == "__main__":
    main(*sys.argv[1:2])
