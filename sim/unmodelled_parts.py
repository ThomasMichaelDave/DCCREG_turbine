#!/usr/bin/env python3
"""sim/unmodelled_parts.py -- solids for the proposed parts the layout's model does not carry, built from their first
cuts so that the drawing set can draw them (docs/make_drawing_set.py):
  * the magnetic pump's parts on the rotor (sim/parts-first-cut-findings.md, PROPOSED): the La / Lb choke (EI-84 x 35,
    150 turns of 1.40 mm), the K4 start kick, the Schottky rectifiers D1*-D4*, the node snubbers and the AH bypass
    capacitors. Their places on the rotor are OPEN, so each is drawn on its own.
  * the drive (docs/drive-gear-belt.md, PROPOSED): the 1 : -1 bevel reverser at side A (two side gears z 30, three POM
    pinions z 20 in cartridges, the gear case, its bell, the counter-rotor's hub and end disc), the HTD 5M belt, its
    pulleys and the 200 W motor on its plate. The first cut stands on the record's 940 mm stack-up (z from the record's
    bottom end-bearing slot); the ledger asks for it to be re-cut on the layout (DCCREG-design-ledger.md §6, item 71),
    so it is drawn in its own frame, not placed in sim/tube_geometry.py LayoutMachine.
Every number the first cuts give is read from their results (sim/parts_first_cut_results.json,
sim/drive_sizing_results.json) or cited where it is set; what they leave open is chosen here and tagged [IR] (a
modelling choice) or [RH] (a placeholder). The checks run here: every sub-assembly's parts do not overlap, the parts
that turn against each other keep their clearances, the gear's teeth mesh without interference at the first cut's
backlash, the belt's pitch length closes at 750 mm, and the masses against the first cuts'.
Writes sim/unmodelled_parts_results.json. Usage: python3 sim/unmodelled_parts.py   (about a minute; OCP)
"""
import functools
import json
import math
import os
import sys
import time

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
import tube_geometry as TG                                                   # noqa: E402  (primitives, colours)

OUT = os.path.join(HERE, "unmodelled_parts_results.json")


def _res(rel):
    with open(os.path.join(ROOT, rel)) as f:
        return json.load(f)


_PF = _res("sim/parts_first_cut_results.json")
_DR = _res("sim/drive_sizing_results.json")
COL = dict(TG.COL, pom=(0.93, 0.92, 0.87), ss=(0.74, 0.76, 0.79), al=(0.80, 0.82, 0.86), fe=(0.48, 0.50, 0.55),
           film=(0.88, 0.80, 0.45), bobbin=(0.20, 0.20, 0.22), belt=(0.18, 0.18, 0.19), cell=(0.20, 0.33, 0.62),
           pcb=(0.15, 0.45, 0.25), black=(0.12, 0.12, 0.13), blue=(0.20, 0.36, 0.66), brown=(0.55, 0.35, 0.20))

# densities (kg/m3) [IR: handbook values]
RHO = dict(ss=7900.0, al=2700.0, pom=1410.0, g10=1850.0, fe=7650.0, cu=8890.0, pa_gf=1450.0, pet=1390.0)

# =====================================================================================================================
# primitives
# =====================================================================================================================
box, cyl_z, sector, fuse, prism = TG.box, TG.cyl_z, TG.sector, TG.fuse, TG.prism


def cut(s, *tools):
    from OCP.BRepAlgoAPI import BRepAlgoAPI_Cut
    for t in tools:
        s = BRepAlgoAPI_Cut(s, t).Shape()
    return s


def common(a, b):
    from OCP.BRepAlgoAPI import BRepAlgoAPI_Common
    return BRepAlgoAPI_Common(a, b).Shape()


def ring(r0, r1, z0, z1):
    return sector(r0, r1, z0, z1)


def frame(xl, yl, zl, o=(0.0, 0.0, 0.0)):
    """the transform taking a part's own axes (x, y, z) onto xl, yl, zl at o."""
    from OCP.gp import gp_Trsf
    t = gp_Trsf()
    X, Y, Z = (np.asarray(v, float) for v in (xl, yl, zl))
    t.SetValues(X[0], Y[0], Z[0], o[0], X[1], Y[1], Z[1], o[1], X[2], Y[2], Z[2], o[2])
    return t


def rot_z(deg, dz=0.0, dx=0.0, dy=0.0):
    """rotate about z by deg, then translate."""
    c, s = math.cos(math.radians(deg)), math.sin(math.radians(deg))
    return frame((c, s, 0), (-s, c, 0), (0, 0, 1), (dx, dy, dz))


def flip_x(deg=0.0, dz=0.0):
    """turned over about x (z -> -z), then rotated about z by deg and lifted by dz."""
    c, s = math.cos(math.radians(deg)), math.sin(math.radians(deg))
    return frame((c, s, 0), (s, -c, 0), (0, 0, -1), (0, 0, dz))


def radial(phi_deg, z0):
    """a part on a radial axis at phi in the plane z0: its own z outward along phi, its own x up the machine's z."""
    c, s = math.cos(math.radians(phi_deg)), math.sin(math.radians(phi_deg))
    return frame((0, 0, 1), (s, -c, 0), (c, s, 0), (0, 0, z0))


def apply(shape, t):
    from OCP.BRepBuilderAPI import BRepBuilderAPI_Transform
    return shape if t is None else BRepBuilderAPI_Transform(shape, t, True).Shape()


def revolve(poly):
    """a closed polygon [(r, z)] (r >= 0) in the xz half plane, revolved about z."""
    from OCP.BRepBuilderAPI import BRepBuilderAPI_MakePolygon, BRepBuilderAPI_MakeFace
    from OCP.BRepPrimAPI import BRepPrimAPI_MakeRevol
    from OCP.gp import gp_Pnt, gp_Ax1, gp_Dir
    mp = BRepBuilderAPI_MakePolygon()
    for r, z in poly:
        mp.Add(gp_Pnt(float(r), 0.0, float(z)))
    mp.Close()
    f = BRepBuilderAPI_MakeFace(mp.Wire()).Face()
    return BRepPrimAPI_MakeRevol(f, gp_Ax1(gp_Pnt(0, 0, 0), gp_Dir(0, 0, 1)), 2 * math.pi).Shape()


def cone_z(r0, r1, z0, z1):
    """a cone frustum on the z axis, radius r0 at z0 and r1 at z1."""
    from OCP.BRepPrimAPI import BRepPrimAPI_MakeCone
    from OCP.gp import gp_Ax2, gp_Pnt, gp_Dir
    lo, hi = (z0, z1) if z1 > z0 else (z1, z0)
    ra, rb = (r0, r1) if z1 > z0 else (r1, r0)
    return BRepPrimAPI_MakeCone(gp_Ax2(gp_Pnt(0, 0, lo), gp_Dir(0, 0, 1)), ra, rb, hi - lo).Shape()


def holes(r_pcd, n, d, z0, z1, a0=0.0, csk=None, angles=None):
    """n axial holes of diameter d on a pitch circle, z0..z1, equally spaced from a0 (or at the angles given); csk =
    (D, z_face, +1 | -1): a 90 deg countersink of diameter D at the face z_face, opening upward (+1) or downward."""
    out = []
    for k in range(n):
        a = math.radians(angles[k] if angles else a0 + 360.0 * k / n)
        x, y = r_pcd * math.cos(a), r_pcd * math.sin(a)
        h = cyl_z(x, y, 0.5 * d, z0, z1)
        if csk:
            D, zf, up = csk
            dep = 0.5 * (D - d)
            cone = cone_z(0.5 * D + 1.0, 0.5 * d, zf + up * 1.0, zf - up * dep)     # 1 mm past the face, so it cuts clean
            h = fuse([h, apply(cone, rot_z(0.0, dx=x, dy=y))])
        out.append(h)
    return out


def stadium(cx0, cx1, y, w, z0, z1):
    """a slot of width w along x from cx0 to cx1 (centres), at y, z0..z1."""
    return fuse([box(cx0, cx1, y - 0.5 * w, y + 0.5 * w, z0, z1), cyl_z(cx0, y, 0.5 * w, z0, z1),
                 cyl_z(cx1, y, 0.5 * w, z0, z1)])


def volume(shape):
    from OCP.BRepGProp import BRepGProp
    from OCP.GProp import GProp_GProps
    g = GProp_GProps(); BRepGProp.VolumeProperties_s(shape, g)
    return g.Mass()


def bbox(shape):
    from OCP.Bnd import Bnd_Box
    from OCP.BRepBndLib import BRepBndLib
    b = Bnd_Box(); BRepBndLib.Add_s(shape, b, True)
    p, q = b.CornerMin(), b.CornerMax()
    return [round(p.X(), 2), round(p.Y(), 2), round(p.Z(), 2)], [round(q.X(), 2), round(q.Y(), 2), round(q.Z(), 2)]


def valid(shape):
    from OCP.BRepCheck import BRepCheck_Analyzer
    return bool(BRepCheck_Analyzer(shape).IsValid())


def distance(a, b):
    from OCP.BRepExtrema import BRepExtrema_DistShapeShape
    d = BRepExtrema_DistShapeShape(a, b)
    d.Perform()
    return float(d.Value()) if d.IsDone() else None


# =====================================================================================================================
# straight bevel gears [OC: geometry; IR: the tooth form]
# =====================================================================================================================
def _inv(a):
    return math.tan(a) - a


def spur_outline(zv, m, alpha, ha, hf, thin, n_teeth, n_fl=8, n_tip=3, n_root=3):
    """the outline of the virtual spur gear (Tredgold: the back cone developed) in polar (rho, psi): n_teeth involute
    teeth of the angular pitch 2 pi / zv, each thinned by `thin` at the pitch circle, a tooth space on psi = 0."""
    rv = m * zv / 2.0
    rb = rv * math.cos(alpha)
    ra, rf = rv + ha, rv - hf
    bp = (math.pi * m / 2.0 - thin) / (2.0 * rv)

    def beta(rho):
        rho = max(rho, rb)                               # a radial flank below the base circle
        return bp + _inv(alpha) - _inv(math.acos(min(1.0, rb / rho)))
    pitch = 2.0 * math.pi / zv
    rhos = [rf + (ra - rf) * k / (n_fl - 1) for k in range(n_fl)]
    pts = []
    for j in range(n_teeth):
        c = (j + 0.5) * pitch
        s0, f, bt = c - 0.5 * pitch, beta(rf), beta(ra)
        pts += [(rf, s0 + (c - f - s0) * k / n_root) for k in range(n_root)]
        pts += [(rho, c - beta(rho)) for rho in rhos]
        pts += [(ra, c - bt + 2.0 * bt * k / n_tip) for k in range(1, n_tip)]
        pts += [(rho, c + beta(rho)) for rho in reversed(rhos)]
        pts += [(rf, c + f + (0.5 * pitch - f) * k / n_root) for k in range(1, n_root)]
    return pts, dict(rv=rv, rb=rb, ra=ra, rf=rf, tip_land_mm=2.0 * ra * beta(ra), root_gap_mm=2.0 * rf * (0.5 * pitch - beta(rf)))


def apex_prism(P3, z_near, z_far):
    """the solid swept by the rays from the origin through a closed outline P3, between the planes z_near and z_far:
    each side face lies in the plane through the origin and two neighbouring points, so it is planar and exact."""
    from OCP.BRepBuilderAPI import (BRepBuilderAPI_MakePolygon, BRepBuilderAPI_MakeFace, BRepBuilderAPI_Sewing,
                                    BRepBuilderAPI_MakeSolid)
    from OCP.TopoDS import TopoDS
    from OCP.TopExp import TopExp_Explorer
    from OCP.TopAbs import TopAbs_SHELL
    from OCP.ShapeFix import ShapeFix_Solid
    from OCP.gp import gp_Pnt
    A = [(q[0] * z_near / q[2], q[1] * z_near / q[2], z_near) for q in P3]
    B = [(q[0] * z_far / q[2], q[1] * z_far / q[2], z_far) for q in P3]

    def face(pts):
        mp = BRepBuilderAPI_MakePolygon()
        for p in pts:
            mp.Add(gp_Pnt(*map(float, p)))
        mp.Close()
        return BRepBuilderAPI_MakeFace(mp.Wire(), True).Face()
    sew = BRepBuilderAPI_Sewing(1e-6)
    sew.Add(face(A)); sew.Add(face(B))
    n = len(P3)
    for i in range(n):
        j = (i + 1) % n
        sew.Add(face([A[i], A[j], B[j], B[i]]))
    sew.Perform()
    shell = TopoDS.Shell(TopExp_Explorer(sew.SewedShape(), TopAbs_SHELL).Current())
    f = ShapeFix_Solid(BRepBuilderAPI_MakeSolid(shell).Solid())
    f.Perform()
    return f.Solid()


def bevel_gear(z, m, delta_deg, b, back, bore_r, alpha_deg=20.0, thin=0.0, toothed=True):
    """a straight bevel gear in its own frame: the cone's apex at the origin, the axis +z toward the gear's back.
    Equal-addendum teeth at the heel (h_a m, h_f 1.25 m), shrinking to the apex; a 0.5 mm crown below the root at the
    heel and the toe [IR]. back: the outline [(r, z)] from the crown at the heel to the bore at the back face.
    Returns (blank, toothed, data): the blank is the gear as a drawing draws it (the tip cone as its outline), the
    toothed solid has the teeth (the heel's profile on the back cone, Tredgold; the flanks ruled through the apex)."""
    d, al = math.radians(delta_deg), math.radians(alpha_deg)
    Re = m * z / (2.0 * math.sin(d))
    Ri = Re - b
    k = Ri / Re
    p, n = np.array([math.sin(d), math.cos(d)]), np.array([math.cos(d), -math.sin(d)])
    ha, hf = m, 1.25 * m
    Ht, Hr, C = Re * p + ha * n, Re * p - hf * n, Re * p - (hf + 0.5) * n
    Tt, Tr, Cp = Ri * p + k * ha * n, Ri * p - k * hf * n, Ri * p - k * (hf + 0.5) * n
    poly = [(bore_r, Cp[1]), tuple(Cp), tuple(Tt), tuple(Ht), tuple(C)] + [tuple(q) for q in back]
    poly = [(float(r), float(zz)) for r, zz in poly]
    blank = revolve(poly)
    data = dict(outline=poly, Ht=tuple(map(float, Ht)), Hr=tuple(map(float, Hr)), Tt=tuple(map(float, Tt)),
                Tr=tuple(map(float, Tr)), z_min=float(min(q[1] for q in poly)),
                z=z, m=m, delta_deg=delta_deg, b=b, alpha_deg=alpha_deg, R_e=Re, R_i=Ri, d_pitch=m * z,
                d_tip_heel=2.0 * Ht[0], apex_to_tip_heel=float(Ht[1]), apex_to_back=float(max(q[1] for q in poly)),
                face_angle_deg=math.degrees(math.atan2(Ht[0], Ht[1])), root_angle_deg=math.degrees(math.atan2(Hr[0], Hr[1])),
                back_cone_deg=90.0 - delta_deg, d_root_toe=2.0 * Tr[0], d_root_heel=2.0 * Hr[0], h_a=ha, h_f=hf,
                pitch_heel=(float(Re * p[0]), float(Re * p[1])), pitch_toe=(float(Ri * p[0]), float(Ri * p[1])),
                thin_mm=thin)
    if not toothed:
        return blank, None, data
    zv = z / math.cos(d)
    out, sp = spur_outline(zv, m, al, ha, hf, thin, z)
    zB = Re / math.cos(d)                                # the back cone's apex on the axis
    P3 = []
    for rho, psi in out:                                 # the developed back cone wrapped onto the cone [OC]
        th, r = psi / math.cos(d), rho * math.cos(d)
        P3.append((r * math.cos(th), r * math.sin(th), zB - rho * math.sin(d)))
    zs = [q[1] for q in poly]
    g = common(apex_prism(P3, min(zs) - 1.0, max(zs) + 1.0), blank)
    data.update(z_v=zv, tip_land_heel_mm=sp["tip_land_mm"], root_gap_heel_mm=sp["root_gap_mm"])
    return blank, g, data


# =====================================================================================================================
# the sub-assemblies, in the shape of tube_geometry's Machine (prototypes + placed parts)
# =====================================================================================================================
class Sub:
    def __init__(self, key, title, note):
        self.key, self.title, self.note = key, title, note
        self.protos = {}          # key -> (blank shape, colour, material, toothed shape or None)
        self.parts = []           # dict(name, proto, T, body, group, label)
        self.data = {}

    def proto(self, key, make, colour, material):
        """make() returns a shape, or (shape for the drawing, shape for the 3-D view)."""
        if key not in self.protos:
            s = make()
            s2 = None
            if isinstance(s, tuple):
                s, s2 = s
            self.protos[key] = (s, colour, material, s2)
        return key

    def add(self, name, proto, T=None, body="", desc=""):
        self.parts.append(dict(name=name, proto=proto, T=T, body=body, group=self.key,
                               label=f"{self.key} / {name} - {desc} [{self.protos[proto][2]}, {body}]"))

    def placed(self, part, three_d=False):
        s, _, _, s3 = self.protos[part["proto"]]
        return apply(s3 if (three_d and s3 is not None) else s, part["T"])


# ------------------------------------------------------------------------------------------------- La / Lb choke
CH = _PF["la_lb"]["chosen"]                           # EI-84 x 35, 150 t of 1.40 mm (sim/parts-first-cut-findings.md §1)
CH_BOB = _PF["la_lb"]["assumptions"]["bobbin_mm"]     # the bobbin's wall, clearances and flanges, as sized
CH_A, CH_S = CH["a_mm"], CH["stack_mm"]               # centre leg 28, stack 35
CH_GAP = CH["spacer_mm"]                              # 0.063 mm: E and I butted on it (two gaps in series)


def choke_sub():
    """La / Lb: the scrapless EI-84 [OC: the proportions, sim/parts_first_cut.py EI] -- centre leg a, outer legs a / 2,
    window a / 2 x 3a / 2, outline 3a x 2.5a -- stacked 35 mm along z; x across the E, y up its legs. The bobbin and
    the winding as sized there (CH_BOB: a 1.0 mm wall at 0.25 mm from the leg, 1.5 mm flanges, the layers' build 10.8
    mm); the flanges 1 mm short of the outer legs and of the build [IR]."""
    a, s, g = CH_A, CH_S, CH_GAP
    w = 0.5 * a                                       # outer leg, window width
    hw = 1.5 * a                                      # window height
    e_poly = [(0, 0), (3 * a, 0), (3 * a, w + hw), (3 * a - w, w + hw), (3 * a - w, w), (2 * a, w), (2 * a, w + hw),
              (a, w + hw), (a, w), (w, w), (w, w + hw), (0, w + hw)]
    yE, yI = w + hw, w + hw + g                       # the E's legs' faces; the I's face on the spacer
    clr, wall, fl = CH_BOB["leg_clearance"], CH_BOB["wall"], CH_BOB["flange"]
    build = CH["build_mm"]                            # 7 layers of (1.492 + 0.05) mm
    off_in, off_out = clr + wall, clr + wall + build  # the winding from the bobbin's wall outward
    x0, x1, z0, z1 = a, 2 * a, 0.0, s                 # the centre leg's section
    yb0, yb1 = w + clr, yE - clr                      # the bobbin along the leg
    f_x0, f_x1 = w + CH_BOB["outer_clearance"], 3 * a - w - CH_BOB["outer_clearance"]               # off the legs
    f_z0, f_z1 = z0 - (off_out + 1.0), z1 + (off_out + 1.0)
    wind_len = CH["per_layer"] * CH["wire_od_mm"] * CH_BOB["pitch_factor"]                          # 24 x 1.552 mm
    yw0 = 0.5 * (yb0 + yb1) - 0.5 * wind_len
    S = Sub("choke", "La / Lb choke, EI-84 x 35", "sim/parts-first-cut-findings.md §1")
    S.proto("ch_E", lambda: prism(e_poly, z0, z1), COL["fe"], "M400-50A 0.5 mm laminations, E, bonded stack")
    S.proto("ch_I", lambda: box(0, 3 * a, yI, yI + w, z0, z1), COL["fe"], "M400-50A 0.5 mm laminations, I, bonded stack")
    S.proto("ch_spacer", lambda: box(0, 3 * a, yE, yI, z0, z1), COL["film"], f"PET film {g:.3f} mm, the gap spacer")

    def bobbin():
        tube = cut(TG.rounded_box_y(x0 - off_in, x1 + off_in, yb0, yb1, z0 - off_in, z1 + off_in, off_in),
                   box(x0 - clr, x1 + clr, yb0 - 1, yb1 + 1, z0 - clr, z1 + clr))    # its corners round as the turns
        fls = [cut(box(f_x0, f_x1, ya, ya + fl, f_z0, f_z1), box(x0 - clr, x1 + clr, ya - 1, ya + fl + 1, z0 - clr, z1 + clr))
               for ya in (yb0, yb1 - fl)]
        return fuse([tube] + fls)
    S.proto("ch_bobbin", bobbin, COL["bobbin"], "bobbin, glass-filled PA66 (UL 94 V-0), 1.0 mm wall, 1.5 mm flanges")

    def winding():
        o = TG.rounded_box_y(x0 - off_out, x1 + off_out, yw0, yw0 + wind_len, z0 - off_out, z1 + off_out, off_out)
        i = TG.rounded_box_y(x0 - off_in, x1 + off_in, yw0 - 1, yw0 + wind_len + 1, z0 - off_in, z1 + off_in, off_in)
        return cut(o, i)
    S.proto("ch_winding", winding, COL["cu"], f"Cu magnet wire, grade 2, {CH['wire_mm']:.2f} mm, {CH['turns']} turns")
    r_w = 0.5 * CH["wire_mm"]
    zl = z1 + off_out                                 # the leads leave the outer layer's face at +z
    S.proto("ch_lead", lambda: cyl_z(0.0, 0.0, r_w, 0.0, 22.0), COL["cu"], f"Cu lead, {CH['wire_mm']:.2f} mm, sleeved")
    for nm, k in (("E_stack", "ch_E"), ("I_stack", "ch_I"), ("gap_spacer", "ch_spacer"), ("bobbin", "ch_bobbin"),
                  ("winding", "ch_winding")):
        S.add(nm, k, None, "rotor", desc=S.protos[k][2])
    for j, xx in enumerate((x0 + 6.0, x1 - 6.0)):
        S.add(f"lead_{j + 1}", "ch_lead", rot_z(0.0, dx=xx, dy=yw0 + wind_len - 2.0 - 4.0 * j, dz=zl), "rotor",
              desc="the winding's start / finish")
    S.data = dict(outline_mm=[3 * a, 2.5 * a + g, round(f_z1 - f_z0, 3)], window=[w, hw], flange_z=[f_z0, f_z1],
                  winding_y=[yw0, yw0 + wind_len], winding_offsets=[off_in, off_out])
    return S


# ------------------------------------------------------------------------------------------------- the K4 kick
KICK = _PF["kick"]
CELL = dict(L=48.5, W=26.5, T=17.5)          # a 9 V (PP3 / 6LR61-size) lithium cell, Ultralife U9VL-J-P [IR datasheet]
REED = dict(L=23.0, W=14.0, H=5.5)           # Littelfuse 59140 flange-mount reed sensor: 23 x 14 [IR datasheet], H [RH]


def kick_sub():
    """the K4 kick as a module [RH: the layout; the parts are the first cut's, sim/parts-first-cut-findings.md §3]: a G10
    base 100 x 60 x 3; the 9 V cell in its holder; the electronics on a small board under silicone (the 470 uF bipolar
    can laid down, the SCR, the resistors and the RC parts); the reed sensor on the base, its blades to lie radial
    when the module is mounted; the arming link on the potting. x along the base, z up from its underside."""
    S = Sub("kick", "Start kick K4", "sim/parts-first-cut-findings.md §3")
    t = 3.0
    hx0, hy0 = 6.0, 6.0                                                   # the cell's holder
    bx0, bx1, by0, by1, bz1 = 64.0, 96.0, 6.0, 54.0, t + 22.0             # the potted block
    zb0, zb1 = t + 1.0, t + 2.6                                           # the board on 1 mm standoffs
    cap = apply(cyl_z(0, 0, 8.0, 0, 25.0), frame((0, 1, 0), (0, 0, 1), (1, 0, 0), (bx0 + 3.5, 30.0, zb1 + 8.2)))
    scr = apply(cut(cyl_z(0, 0, 2.4, 0, 4.8), box(-3, 3, 1.3, 3, -1, 6)), rot_z(0.0, dx=bx0 + 6.0, dy=14.0, dz=zb1))
    res = lambda y: apply(cyl_z(0, 0, 1.25, 0, 6.5), frame((0, 1, 0), (0, 0, 1), (1, 0, 0), (bx0 + 16.0, y, zb1 + 1.3)))
    board = box(bx0 + 1.0, bx1 - 1.0, by0 + 2.0, by1 - 2.0, zb0, zb1)
    inner = [board, cap, scr] + [res(y) for y in (12.0, 46.0, 50.0)]
    S.proto("k_base", lambda: cut(box(0, 100, 0, 60, 0, t), *[cyl_z(x, y, 1.7, -1, t + 1) for x in (5, 95) for y in (5, 55)]),
            COL["g10"], "G10 base, 3 mm, four M3 holes")
    S.proto("k_holder", lambda: cut(box(hx0, hx0 + CELL["L"] + 4, hy0, hy0 + CELL["W"] + 4, t, t + 14.0),
                                    box(hx0 + 2, hx0 + CELL["L"] + 2, hy0 + 2, hy0 + CELL["W"] + 2, t + 1.5, t + 20.0)),
            COL["black"], "9 V cell holder, PCB / chassis mount (Keystone 1294 class)")
    S.proto("k_cell", lambda: box(hx0 + 2, hx0 + 2 + CELL["L"], hy0 + 2, hy0 + 2 + CELL["W"], t + 1.5, t + 1.5 + CELL["T"]),
            COL["cell"], "9 V lithium cell, LiMnO2, 1.2 Ah (Ultralife U9VL-J-P)")
    S.proto("k_pot", lambda: cut(box(bx0, bx1, by0, by1, t, bz1), *inner), COL["silicone"], "silicone potting, RTV-2")
    S.proto("k_pcb", lambda: board, COL["pcb"], "FR-4 board, 1.6 mm")
    S.proto("k_cap", lambda: cap, COL["blue"], "470 uF 25 V bipolar electrolytic, 16 x 25 (Nichicon UES1E471MHM)")
    S.proto("k_scr", lambda: scr, COL["black"], "SCR TO-92, 600 V 1.5 A (Littelfuse TCR22-8)")
    S.proto("k_res", lambda: res(0.0), COL["brown"], "resistor, axial, 0.25-0.5 W")
    S.proto("k_reed", lambda: cut(box(0, REED["L"], 0, REED["W"], 0, REED["H"]), cyl_z(3.0, 7.0, 1.6, -1, 7),
                                  cyl_z(20.0, 7.0, 1.6, -1, 7)),
            COL["black"], "reed sensor, normally open, flange mount (Littelfuse 59140)")
    S.proto("k_link", lambda: box(0, 8.0, 0, 5.0, 0, 8.0), COL["black"], "arming link, 2-pin header and jumper")
    S.add("base", "k_base", None, "rotor", desc="the module's base")
    S.add("cell_holder", "k_holder", None, "rotor", desc="the cell's holder")
    S.add("cell", "k_cell", None, "rotor", desc="the 9 V lithium cell")
    S.add("board", "k_pcb", None, "rotor", desc="the board")
    S.add("C_kick", "k_cap", None, "rotor", desc="the kick capacitor, 470 uF bipolar")
    S.add("SCR", "k_scr", None, "rotor", desc="the SCR")
    for j, (y, what) in enumerate(((12.0, "R1 10 kOhm, the charging resistor"), (46.0, "R2 100 Ohm, the gate's series"),
                                   (50.0, "R3 1 kOhm, gate to cathode"))):
        S.add(f"R{j + 1}", "k_res", rot_z(0.0, dy=y), "rotor", desc=what)
    S.add("potting", "k_pot", None, "rotor", desc="the potting over the board")
    S.add("reed", "k_reed", rot_z(0.0, dx=6.0, dy=40.0, dz=t), "rotor", desc="the reed sensor")
    S.add("link", "k_link", rot_z(0.0, dx=84.0, dy=10.0, dz=bz1), "rotor", desc="the arming link")
    S.data = dict(base=[100.0, 60.0, t], block=[bx1 - bx0, by1 - by0, bz1 - t], height=bz1 + 8.0)
    return S


# ------------------------------------------------------------------------------------------------- bought electronics
DO201AD = dict(D=5.3, L=9.5, d=1.3, lead=25.4)    # JEDEC DO-201AD, the maxima [IR datasheet-class: SB5200, SR5150]
R76 = dict(L=13.0, W=9.0, H=14.0, pitch=10.0, d=0.6, lead=30.0)   # KEMET R76 22 nF 400 V, 10 mm pitch (RS 1353468)
OX = dict(D=5.5, L=16.5, d=0.8, lead=25.0)        # Ohmite OX221KE (DigiKey 823917: 5.50 x 16.50 mm; leads 0.8 mm)
SNAP = dict(D=30.0, H=30.0, pitch=10.0, pin_w=2.0, pin_t=1.0, pin_l=6.3)   # Rubycon 10MXG22000MEFCSN30X30: 30 x 30,
#                                                   snap-in, 10 mm pitch (a retailer's listing); the pins [IR: class]


def diode_shape():
    """an axial DO-201AD part along x, centred (its cathode band is not modelled)."""
    from OCP.BRepPrimAPI import BRepPrimAPI_MakeCylinder
    from OCP.gp import gp_Ax2, gp_Pnt, gp_Dir
    q = DO201AD
    half = 0.5 * q["L"]
    ax = lambda x0, r, L: BRepPrimAPI_MakeCylinder(gp_Ax2(gp_Pnt(x0, 0, 0), gp_Dir(1, 0, 0)), r, L).Shape()
    body = ax(-half, 0.5 * q["D"], q["L"])
    return fuse([body, ax(-half - q["lead"], 0.5 * q["d"], q["lead"]), ax(half, 0.5 * q["d"], q["lead"])])


def snubber_shapes():
    """the snubber's two parts side by side: the R76 box (its leads down) and the OX resistor (axial, along x)."""
    from OCP.BRepPrimAPI import BRepPrimAPI_MakeCylinder
    from OCP.gp import gp_Ax2, gp_Pnt, gp_Dir
    c = R76
    cap = fuse([box(-0.5 * c["L"], 0.5 * c["L"], -0.5 * c["W"], 0.5 * c["W"], 0.0, c["H"])] +
               [cyl_z(sx * 0.5 * c["pitch"], 0.0, 0.5 * c["d"], -c["lead"], 0.0) for sx in (-1, 1)])
    o = OX
    ax = lambda x0, r, L: BRepPrimAPI_MakeCylinder(gp_Ax2(gp_Pnt(x0, 0, 0), gp_Dir(1, 0, 0)), r, L).Shape()
    res = fuse([ax(-0.5 * o["L"], 0.5 * o["D"], o["L"]), ax(-0.5 * o["L"] - o["lead"], 0.5 * o["d"], o["lead"]),
                ax(0.5 * o["L"], 0.5 * o["d"], o["lead"])])
    return cap, apply(res, rot_z(0.0, dx=0.0, dy=26.0, dz=0.5 * c["H"]))


def snapin_shape():
    """the bypass capacitor: the can on its sleeve, the two snap-in pins down."""
    q = SNAP
    can = fuse([cyl_z(0, 0, 0.5 * q["D"], 0.0, q["H"]), cyl_z(0, 0, 0.5 * q["D"] - 1.5, q["H"], q["H"] + 0.6)])
    pins = [box(sx * 0.5 * q["pitch"] - 0.5 * q["pin_w"], sx * 0.5 * q["pitch"] + 0.5 * q["pin_w"], -0.5 * q["pin_t"],
                0.5 * q["pin_t"], -q["pin_l"], 0.0) for sx in (-1, 1)]
    return fuse([can] + pins)


def laminations_shape(t=0.5):
    """one E and one I lamination (0.5 mm; or a stack t thick), as delivered, in the x-z plane (the E's legs up z), the I
    above the E."""
    a, w, hw = CH_A, 0.5 * CH_A, 1.5 * CH_A
    e_poly = [(0, 0), (3 * a, 0), (3 * a, w + hw), (3 * a - w, w + hw), (3 * a - w, w), (2 * a, w), (2 * a, w + hw),
              (a, w + hw), (a, w), (w, w), (w, w + hw), (0, w + hw)]
    to_xz = frame((1, 0, 0), (0, 0, 1), (0, -1, 0))   # the plate's y onto z, its thickness along -y
    E = apply(prism(e_poly, 0.0, t), to_xz)
    I = apply(box(0, 3 * a, 0, w, 0.0, t), frame((1, 0, 0), (0, 0, 1), (0, -1, 0), (0.0, 0.0, w + hw + 8.0)))
    return fuse([E, I])


# =====================================================================================================================
# the drive: the 1 : -1 bevel reverser at side A and the belt (docs/drive-gear-belt.md; sim/drive_sizing_results.json)
# =====================================================================================================================
GS, GG, ENV, BELT = _DR["gear"]["spec"], _DR["gear"]["geometry"], _DR["envelope"], _DR["belt"]
Z_APEX = ENV["z_apex"]                       # -36: the pinions' plane, the cones' common apex on the axis
R_SHAFT = 12.5                               # the shaft's 25 mm journal at the gear end (docs/drive-gear-belt.md §5)
PHI_P = (30.0, 150.0, 270.0)                 # the pinions' axes, 120 deg apart (3 pinions, GS N_p) [IR: the angles]
MOTOR_DIR = 0.0                              # the motor at +x, centres 245.4 mm (BELT centre_mm) [IR: the direction]
BACKLASH = 0.12                              # j_n 0.10-0.15 mm (§5); the model thins each gear's teeth by half [IR]
THIN = 0.5 * BACKLASH / math.cos(math.radians(GS["alpha_deg"]))
BACK = 8.0                                   # each gear's back behind its outer pitch circle (sim/drive_sizing.py
#                                              stackup back 8.0), so the mounting face sits 28 mm from the apex
B6205 = dict(d=25.0, D=52.0, B=15.0, d1=31.8, Da=46.4)    # the layout's bearing (sim/bridge_ring_bearings.py PART)
B6000 = dict(d=10.0, D=26.0, B=8.0, C=4.75e3, C0=1.96e3)  # SKF 6000-2Z (catalogue data via distributors, 2026-10-11)
PIN_BACK = GG["apex_to_pinion_pitch_circle"] + BACK      # 38: the pinion's back face from the apex (stackup)
# the cartridge, along the pinion's axis from the apex: the inner 6000 38-46, a 4 mm land 46-50, the outer 50-58 (the
# case's arithmetic, sim/drive_sizing.py stackup case_r: 38 + 2 x 8 + 4); the sleeve through the case's wall 64-72 to a
# boss face at 76, its flange 76-80 [IR]
CART = dict(b1=(38.0, 46.0), land=(46.0, 50.0), b2=(50.0, 58.0), wall=(64.0, 72.0), boss=76.0, flange=(76.0, 80.0),
            od=32.0, flange_d=48.0, pcd=40.0, boss_d=56.0)
CASE = dict(r_in=64.0, r_out=ENV["case_outer_r"], floor=(-96.0, -79.0), lip_bore=40.0, top=-2.0, lip=(-8.0, -2.0),
            lip_r=44.0, flange_r=84.0, flange_z=(-96.0, -88.0), bolt_pcd=154.0)
BELL = dict(r_in=72.0, r_out=82.0, z=(-136.0, -96.0), a0=95.0, a1=265.0)   # a C open to the motor, under the flange;
#   the three M6 come up through the base plate and the bell into the case's flange, clear of its Ø144 barrel [IR]
P80 = dict(z=80, pd=127.32, od=126.18, hub_d=92.0, F=22.0, S=25.0, bush="1610")   # TL80-5M-15 (beltingonline: Dp
#                                                 127.32, De 126.18, hub 92, F 22, S 25, no flanges)
P20 = dict(z=20, pd=31.83, od=30.69, flange_d=36.0, hub_d=23.0, face=20.5, overall=26.0)   # P20-5M-15F (Ondrives)
MOT = dict(flange=60.0, L=110.0, pcd=70.0, spigot=50.0, shaft_d=14.0, shaft_l=30.0, flange_t=8.0)   # APBA60M048030-E:
#   60 mm flange (NEMA 24), body 110 mm (smd.ee, Nanotec); the PCD, spigot and shaft [IR: the 60 mm class, to confirm]
Z_BELT = -113.5                              # the belt's mid-plane: the 80T's 22 mm face centred in its 25 mm hub [IR]
BOLTS = (120.0, 180.0, 240.0)                # the case-to-bell-to-base bolts, in the bell's C [IR]
PIN_TURN = 180.0 / GS["z_p"]                 # half a pinion pitch: a pinion tooth on each contact line, where both side
#                                              gears have a space [OC: the mesh's phase]


def toe_z(m, z, delta_deg, b):
    """the toe's front face from the apex, as bevel_gear builds it: R_i cos(delta) + (R_i / R_e)(h_f + 0.5) sin(delta)."""
    d = math.radians(delta_deg)
    Re = m * z / (2.0 * math.sin(d))
    Ri = Re - b
    return Ri * math.cos(d) + (Ri / Re) * (1.25 * m + 0.5) * math.sin(d)


TOE_SIDE = toe_z(GS["m"], GS["z_s"], GG["delta_side_deg"], GS["b"])   # 15.0: the rotor gear's toe, below the apex


def zr(z_rel, cr):
    """a z along the gear's own axis to the machine's: the counter-rotor's gear above the apex, the rotor's below."""
    return Z_APEX + z_rel if cr else Z_APEX - z_rel


def side_gear(which):
    """the side gears (z 30, m 2, b 12, 1.4305, sim/drive_sizing_results.json gear): the same teeth. The rotor's keyed
    in its own hub, the Ø40 the first cut names (§5: the key in the hub, not under the teeth), on the Ø25 journal; the
    counter-rotor's with a back flange Ø80 bolted under its hub outside the bearing, its bore clear of the shaft's
    spacer [IR: the flange, the bore]."""
    m, z, d, b = GS["m"], GS["z_s"], GG["delta_side_deg"], GS["b"]
    Re = GG["R_e"]
    dl = math.radians(d)
    C = (Re * math.sin(dl) - 3.0 * math.cos(dl), Re * math.cos(dl) + 3.0 * math.sin(dl))     # the crown (0.5 below the root)
    zb = GG["apex_to_side_pitch_circle"] + BACK                                              # 28
    if which == "rotor":
        back = [(C[0], zb), (20.0, zb), (20.0, zb + 12.0), (R_SHAFT, zb + 12.0)]          # the hub Ø40 x 12 (stackup)
        bl, gt, data = bevel_gear(z, m, d, b, back, R_SHAFT, GS["alpha_deg"], THIN)
        key = box(0.0, R_SHAFT + 3.3, -4.0, 4.0, zb - 0.01, zb + 12.5)                     # DIN 6885 A 8 x 7: t2 3.3
        bl, gt = cut(bl, key), cut(gt, key)
        data.update(bore="Ø25 H7", keyway="8 P9 x 3.3 (DIN 6885 A 8 x 7) in the hub only", hub=(40.0, 12.0))
    else:
        back = [(C[0], zb), (15.5, zb)]
        bl, gt, data = bevel_gear(z, m, d, b, back, 15.5, GS["alpha_deg"], THIN)
        fl = cut(ring(15.5, 40.0, zb - 3.0, zb), ring(15.5, 20.0, zb - 0.5, zb + 1.0),
                 *holes(35.0, 6, 4.5, zb - 4.0, zb + 1.0, a0=-30.0))                      # the flange; the relief Ø40 x 0.5
        bl, gt = fuse([bl, fl]), fuse([gt, fl])
        bl, gt = cut(bl, ring(14.0, 20.0, zb - 0.5, zb + 1.0)), cut(gt, ring(14.0, 20.0, zb - 0.5, zb + 1.0))
        data.update(bore="Ø31", flange=(80.0, 3.0), flange_holes="6 x Ø4.5 on PCD Ø70", relief="Ø40 x 0.5")
    data["mounting_distance"] = zb
    return bl, gt, data


def pinion():
    """the pinion (z 20, m 2, b 12, POM-C): its back face 38 from the apex (stackup pinion_back_r) on a Ø14 hub that
    bears on the inner 6000's inner ring; pressed on its Ø10 stub shaft [IR: the hub]."""
    m, z, d, b = GS["m"], GS["z_p"], GG["delta_pinion_deg"], GS["b"]
    Re = GG["R_e"]
    dl = math.radians(d)
    C = (Re * math.sin(dl) - 3.0 * math.cos(dl), Re * math.cos(dl) + 3.0 * math.sin(dl))
    back = [(C[0], C[1] + 0.85), (7.0, C[1] + 0.85), (7.0, PIN_BACK), (5.0, PIN_BACK)]
    bl, gt, data = bevel_gear(z, m, d, b, back, 5.0, GS["alpha_deg"], THIN)
    data.update(bore="Ø10, pressed on the stub shaft (H7 / p6 class)", hub=(14.0, PIN_BACK - C[1] - 0.85),
                mounting_distance=PIN_BACK)
    return bl, gt, data


def stub_shaft():
    """Ø10 from the pinion's toe (21.5 from the apex) through both 6000s to its circlip (DIN 471 10 x 1) at 58 [IR]."""
    s = ring(0.0, 5.0, 21.5, 60.2)
    groove = cut(ring(4.8, 5.1, 58.0, 59.1), ring(0.0, 4.8, 57.0, 60.0))
    return cut(s, groove)


def cartridge():
    """the pinion's cartridge sleeve (Al 6082): Ø26 H7 seats for the two 6000-2Z either side of a 4 mm land (Ø22), the
    outer one inserted from outside; Ø32 g6 through the case's wall and boss; the flange Ø48 x 4 on the boss's face,
    three M4 on PCD Ø40; shims under it set the backlash (§5) [IR]."""
    c = CART
    body = fuse([ring(0.0, 0.5 * c["od"], c["b1"][0], c["flange"][0]),
                 ring(0.0, 0.5 * c["flange_d"], c["flange"][0], c["flange"][1])])
    body = cut(body, ring(0.0, 13.0, c["b1"][0] - 1, c["b1"][1]), ring(0.0, 11.0, c["land"][0] - 1, c["land"][1] + 1),
               ring(0.0, 13.0, c["b2"][0], c["b2"][1]), ring(0.0, 13.25, c["b2"][1] - 0.01, c["flange"][1] + 1),
               *holes(0.5 * c["pcd"], 3, 4.5, c["flange"][0] - 1, c["flange"][1] + 1, a0=90.0))
    return body


def bearing(d, D, B):
    return ring(0.5 * d, 0.5 * D, 0.0, B)


def gear_case():
    """the gear case = the carrier = the frame's bottom end-bearing housing (Al 6082; §5, §8): Ø144 x 8 wall, the floor
    17 thick with the locating 6205-2Z's seat (Ø52 H7 from the top, a lip Ø40 below it, which takes the bodies'
    weight); the top lip Ø88 (the labyrinth); three bosses at the pinions with the cartridges' bores Ø32 H7; a flange
    Ø168 on the floor, three M6 into it from below [IR: the bosses, the flange; the first cut's case Ø144 is the
    barrel]."""
    c, k = CASE, CART
    barrel = ring(c["r_in"], c["r_out"], c["floor"][0], c["top"])
    floor = ring(0.5 * c["lip_bore"], c["r_in"] + 0.5, c["floor"][0], c["floor"][1])
    lip = ring(c["lip_r"], c["r_out"], c["lip"][0], c["lip"][1])
    flange = ring(c["r_out"] - 0.5, c["flange_r"], c["flange_z"][0], c["flange_z"][1])
    bosses = [apply(ring(0.0, 0.5 * k["boss_d"], c["r_in"] - 6.0, k["boss"]), radial(ph, Z_APEX)) for ph in PHI_P]
    s = fuse([barrel, floor, lip, flange] + bosses)
    s = cut(s, ring(0.0, c["r_in"], c["floor"][1], c["top"] + 1))                 # the cavity (the bosses' insides)
    s = cut(s, ring(0.0, 0.5 * B6205["D"], c["floor"][0] + 2.0, c["floor"][1] + 1))   # the seat, 15 deep from the top
    for ph in PHI_P:
        s = cut(s, apply(ring(0.0, 0.5 * k["od"], c["r_in"] - 7.0, k["boss"] + 1.0), radial(ph, Z_APEX)),
                *[apply(t, radial(ph, Z_APEX)) for t in holes(0.5 * k["pcd"], 3, 3.3, k["boss"] - 10.0, k["boss"] + 1.0, a0=90.0)])
    s = cut(s, *holes(0.5 * c["bolt_pcd"], 3, 5.0, c["flange_z"][0] - 1, c["flange_z"][1], angles=BOLTS))   # M6 from below
    s = cut(s, *holes(29.0, 3, 2.5, c["floor"][1] - 6.0, c["floor"][1] + 1, a0=0.0))   # the retaining ring's M3
    return s


def bell():
    """the bell under the case floor, a C open toward the motor so that the belt passes and can be fitted (Al 6082):
    Ø164 / Ø144 x 40 over 170 deg; three Ø6.6 through for the M6 from the base plate into the case's flange [IR]."""
    b = BELL
    s = sector(b["r_in"], b["r_out"], b["z"][0], b["z"][1], b["a0"], b["a1"] - b["a0"])
    return cut(s, *holes(0.5 * CASE["bolt_pcd"], 3, 6.6, b["z"][0] - 1, b["z"][1] + 1, angles=BOLTS))


def cr_hub():
    """the counter-rotor's hub (Al 6082, z -8..10, §8): the gear-end 6205-2Z in a seat Ø52 H7 open below, under a lip
    Ø44 at the top that rests on its outer ring (the counter-rotor's 350 N, §5); six M5 from the top for the end disc
    and six M4 from below for the side gear's flange, both on PCD Ø70 [IR: the lip above, the bolting]."""
    s = cut(ring(22.0, 40.0, -8.0, 10.0), ring(0.0, 0.5 * B6205["D"], -9.0, 7.0))
    return cut(s, *holes(35.0, 6, 4.2, 0.0, 10.5, a0=30.0), *holes(35.0, 6, 3.3, -8.5, 0.0, a0=0.0))


def end_disc():
    """the counter-rotor's end disc (G10 10 mm, r 30-156.5, z 10..20; §5 'the bottom spider re-purposed'): six M5
    countersunk from the top into the hub, twelve M5 countersunk from below into inserts in bridge ring A [IR]."""
    s = ring(GS["r_disc0"], 156.5, 10.0, 10.0 + GS["t_disc"])
    z0, z1 = 10.0, 10.0 + GS["t_disc"]
    return cut(s, *holes(35.0, 6, 5.5, z0 - 1, z1 + 1, a0=30.0, csk=(10.4, z1, +1)),
               *holes(144.0, 12, 5.5, z0 - 1, z1 + 1, a0=15.0, csk=(10.4, z0, -1)))


def pulley80():
    """the machine's pulley: TL80-5M-15 (HTD 5M, 80 teeth, unflanged; F 22, S 25, hub Ø92; taper bush 1610) on the
    shaft's drive end below the case floor [catalogue: beltingonline]. The 2-D view draws its tip diameter; the 3-D
    view has 80 grooves [IR: the groove's form]."""
    q = P80
    z0, z1 = Z_BELT - 0.5 * q["S"], Z_BELT + 0.5 * q["S"]                # the hub 25 through, on the nut [IR]
    f0, f1 = Z_BELT - 0.5 * q["F"], Z_BELT + 0.5 * q["F"]
    bl = fuse([ring(28.6, 0.5 * q["hub_d"], z0, z1), ring(0.5 * q["hub_d"] - 0.5, 0.5 * q["od"], f0, f1)])
    gro = [cyl_z(0.5 * q["od"] * math.cos(2 * math.pi * j / q["z"]), 0.5 * q["od"] * math.sin(2 * math.pi * j / q["z"]),
                 1.5, f0 - 1, f1 + 1) for j in range(q["z"])]
    return bl, cut(bl, *gro)


def bush1610():
    """the taper bush 1610, bore Ø25 with an 8 mm keyway (its 25.4 mm length; drawn as a cylinder Ø57.2) [IR]."""
    z0 = Z_BELT - 0.5 * P80["S"]
    return cut(ring(R_SHAFT, 28.6, z0, z0 + 25.4), box(R_SHAFT - 1.0, R_SHAFT + 3.3, -4.0, 4.0, z0 - 1, z0 + 27))


def pulley20():
    """the motor's pulley: P20-5M-15F (HTD 5M, 20 teeth, flanged Ø36; face 20.5, overall 26, hub Ø23) bored Ø14 [Ondrives],
    its hub up toward the motor plate [IR]."""
    q = P20
    f0 = Z_BELT - 0.5 * q["face"]
    f1 = f0 + q["face"]
    bl = fuse([ring(7.0, 0.5 * q["flange_d"], f0, f0 + 1.0), ring(7.0, 0.5 * q["od"], f0 + 1.0, f1 - 1.0),
               ring(7.0, 0.5 * q["flange_d"], f1 - 1.0, f1), ring(7.0, 0.5 * q["hub_d"], f1, f0 + q["overall"])])
    gro = [cyl_z(0.5 * q["od"] * math.cos(2 * math.pi * j / q["z"]), 0.5 * q["od"] * math.sin(2 * math.pi * j / q["z"]),
                 1.5, f0 + 1.0, f1 - 1.0) for j in range(q["z"])]
    return bl, cut(bl, *gro)


def belt_shape():
    """the belt (Gates 750-5M-15): its land, 1.74 mm from the pulleys' tip diameters outward, 15 wide, round both
    pulleys at the first cut's centres; its teeth sit in the grooves and are not drawn [IR]."""
    from OCP.gp import gp_Pnt, gp_Circ, gp_Ax2, gp_Dir
    from OCP.GC import GC_MakeArcOfCircle, GC_MakeSegment
    from OCP.BRepBuilderAPI import BRepBuilderAPI_MakeEdge, BRepBuilderAPI_MakeWire, BRepBuilderAPI_MakeFace
    from OCP.BRepPrimAPI import BRepPrimAPI_MakePrism
    from OCP.gp import gp_Vec
    c = BELT["centre_mm"]
    r1, r2 = 0.5 * P80["od"], 0.5 * P20["od"]
    z0 = Z_BELT - 0.5 * BELT["width_mm"]

    def stadium_face(off):
        a, b = r1 + off, r2 + off
        al = math.acos((r1 - r2) / c)
        C1 = gp_Circ(gp_Ax2(gp_Pnt(0, 0, z0), gp_Dir(0, 0, 1)), a)
        C2 = gp_Circ(gp_Ax2(gp_Pnt(c, 0, z0), gp_Dir(0, 0, 1)), b)
        P = lambda cx, r, t: gp_Pnt(cx + r * math.cos(t), r * math.sin(t), z0)
        e1 = BRepBuilderAPI_MakeEdge(GC_MakeArcOfCircle(C1, al, 2 * math.pi - al, True).Value()).Edge()
        e2 = BRepBuilderAPI_MakeEdge(GC_MakeSegment(P(0, a, -al), P(c, b, -al)).Value()).Edge()
        e3 = BRepBuilderAPI_MakeEdge(GC_MakeArcOfCircle(C2, -al, al, True).Value()).Edge()
        e4 = BRepBuilderAPI_MakeEdge(GC_MakeSegment(P(c, b, al), P(0, a, al)).Value()).Edge()
        w = BRepBuilderAPI_MakeWire()
        for e in (e1, e2, e3, e4):
            w.Add(e)
        return BRepBuilderAPI_MakeFace(w.Wire()).Face()
    band = cut(BRepPrimAPI_MakePrism(stadium_face(1.74), gp_Vec(0, 0, BELT["width_mm"])).Shape(),
               BRepPrimAPI_MakePrism(stadium_face(0.0), gp_Vec(0, 0, BELT["width_mm"])).Shape())
    return band


def belt_pitch_length():
    """the open belt's pitch length at the first cut's centres [OC]."""
    c, r1, r2 = BELT["centre_mm"], 0.5 * P80["pd"], 0.5 * P20["pd"]
    be = math.asin((r1 - r2) / c)
    return 2.0 * math.sqrt(c * c - (r1 - r2) ** 2) + r1 * (math.pi + 2 * be) + r2 * (math.pi - 2 * be)


def motor_shape():
    """the motor's envelope (APBA60M048030-E class): the 60 mm square flange 8 thick on the plate, the body to 110 mm,
    the spigot Ø50 x 3 into the plate's bore, the shaft Ø14 x 30 down into the 20T pulley [IR: the 60 mm class]."""
    q = MOT
    h = 0.5 * q["flange"]
    zf = PLATE["z"][1]
    fl = cut(box(-h, h, -h, h, zf, zf + q["flange_t"]), *[cyl_z(sx * 0.5 * q["pcd"] / math.sqrt(2), sy * 0.5 * q["pcd"] / math.sqrt(2),
                                                                2.75, zf - 1, zf + q["flange_t"] + 1) for sx in (-1, 1) for sy in (-1, 1)])
    body = box(-h + 1.0, h - 1.0, -h + 1.0, h - 1.0, zf + q["flange_t"], zf + q["L"])
    spig = cyl_z(0, 0, 0.5 * q["spigot"], zf - 3.0, zf)
    shaft = cyl_z(0, 0, 0.5 * q["shaft_d"], zf - q["shaft_l"], zf - 3.0)
    return fuse([fl, body, spig, shaft])


PLATE = dict(L=120.0, W=100.0, z=(-97.0, -87.0), slot_w=6.6, slot_l=20.0, slot_x=45.0, slot_y=38.0)


def motor_plate():
    """the motor plate (Al 6082, 120 x 100 x 10): the spigot's bore Ø50 H8, four M5 on PCD Ø70 for the flange, four
    slots 6.6 wide for M6 to the frame's bracket, 20 mm of travel along the belt's line for the tension [IR]."""
    q = PLATE
    s = box(-0.5 * q["L"], 0.5 * q["L"], -0.5 * q["W"], 0.5 * q["W"], q["z"][0], q["z"][1])
    s = cut(s, cyl_z(0, 0, 0.5 * MOT["spigot"], q["z"][0] - 1, q["z"][1] + 1),
            *[cyl_z(sx * 0.5 * MOT["pcd"] / math.sqrt(2), sy * 0.5 * MOT["pcd"] / math.sqrt(2), 2.1, q["z"][0] - 1, q["z"][1] + 1)
              for sx in (-1, 1) for sy in (-1, 1)],
            *[stadium(sx * q["slot_x"] - 0.5 * q["slot_l"], sx * q["slot_x"] + 0.5 * q["slot_l"], sy * q["slot_y"],
                      q["slot_w"], q["z"][0] - 1, q["z"][1] + 1) for sx in (-1, 1) for sy in (-1, 1)])
    return s


@functools.lru_cache(maxsize=None)
def reverser_sub():
    """the reverser at side A as the first cut stacks it (§8; z from the record's bottom end-bearing slot), with the
    shaft's parts that set it: the collar, the spacers, the key, the locating bearing and its ring, the pulley. The
    shaft's stack (the collar, the gear-end bearing's inner ring, spacer A, the rotor gear, spacer B, the locating
    bearing's inner ring, spacer C, the bush) is clamped by the lock nut against the collar, which carries the rotor's
    weight into it; the counter-rotor's rests on the gear-end bearing through the hub's lip; both reach the locating
    bearing, whose outer ring sits on the case floor's lip (§7: 689 N) [IR]."""
    S = Sub("reverser", "The 1 : -1 bevel reverser, side A", "docs/drive-gear-belt.md §5, §8")
    zb = GG["apex_to_side_pitch_circle"] + BACK
    gr, gc, gp = side_gear("rotor"), side_gear("cr"), pinion()
    S.data.update(g_rotor=gr[2], g_cr=gc[2], g_pinion=gp[2])
    S.proto("g_rotor", lambda: gr[:2], COL["ss"], "austenitic stainless 1.4305, rotor side gear z 30")
    S.proto("g_cr", lambda: gc[:2], COL["ss"], "austenitic stainless 1.4305, counter-rotor side gear z 30")
    S.proto("g_pinion", lambda: gp[:2], COL["pom"], "POM-C, pinion z 20")
    S.proto("stub", stub_shaft, COL["ss"], "austenitic stainless 1.4305, stub shaft Ø10")
    S.proto("cart", cartridge, COL["al"], "Al 6082-T6, cartridge sleeve")
    S.proto("b6000", lambda: bearing(B6000["d"], B6000["D"], B6000["B"]), COL["steel"], "bearing SKF 6000-2Z")
    S.proto("sp_pin", lambda: ring(5.0, 7.0, 0.0, 4.0), COL["ss"], "spacer Ø10 / Ø14 x 4, between the 6000s' inner rings")
    S.proto("case", gear_case, COL["al"], "Al 6082-T6, gear case")
    S.proto("bell", bell, COL["al"], "Al 6082-T6, bell")
    S.proto("hub", cr_hub, COL["al"], "Al 6082-T6, counter-rotor hub")
    S.proto("disc", end_disc, COL["g10"], "G10, the counter-rotor's end disc")
    S.proto("b6205", lambda: bearing(B6205["d"], B6205["D"], B6205["B"]), COL["steel"], "bearing SKF 6205-2Z")
    S.proto("collar", lambda: ring(R_SHAFT, 20.0, 0.0, 10.0), COL["ss"], "shaft collar, two-piece clamp, Ø25 / Ø40 x 10")
    S.proto("sp_A", lambda: ring(R_SHAFT, 14.0, 0.0, -8.0 - (Z_APEX - TOE_SIDE)), COL["ss"],
            "spacer tube Ø25 / Ø28, stainless")
    S.proto("sp_B", lambda: ring(R_SHAFT, 16.0, 0.0, 3.0), COL["ss"], "spacer Ø25 / Ø32 x 3, stainless")
    zc_top = Z_BELT - 0.5 * P80["S"] + 25.4                                 # the bush's top face
    S.proto("sp_C", lambda: ring(R_SHAFT, 16.0, 0.0, -94.0 - zc_top), COL["ss"], "spacer Ø25 / Ø32, stainless")
    S.proto("ret", lambda: cut(ring(22.0, 33.0, 0.0, 2.0), *holes(29.0, 3, 3.4, -1.0, 3.0, a0=0.0, csk=(6.7, 2.0, +1))),
            COL["ss"], "retaining ring Ø44 / Ø66 x 2, stainless")
    S.proto("key", lambda: box(R_SHAFT - 4.0, R_SHAFT + 3.0, -4.0, 4.0, 0.0, 12.0), COL["steel"], "key DIN 6885 A 8 x 7 x 12")
    S.proto("p80", pulley80, COL["al"], "pulley TL80-5M-15, cast iron / Al, unflanged")
    S.proto("bush", bush1610, COL["steel"], "taper bush 1610, bore Ø25, keyed")
    S.proto("nut", lambda: ring(R_SHAFT, 19.0, 0.0, 7.0), COL["steel"], "lock nut SKF KM 5 (M25 x 1.5) with MB 5")
    S.proto("shaft", lambda: cut(ring(0.0, R_SHAFT, -133.0, 30.0),
                                 apply(box(R_SHAFT - 4.0, R_SHAFT + 1.0, -4.0, 4.0, 0.0, 12.0), flip_x(-PHI_P[0], dz=Z_APEX - zb))),
            COL["steel"], "the shaft, Ø25 at its drive end, its keyway 8 x 4 for the rotor gear")
    za = Z_APEX
    S.add("shaft", "shaft", None, "rotor", desc="the shaft's drive end (for reference)")
    S.add("collar", "collar", rot_z(0.0, dz=7.0), "rotor", desc="the collar over the gear-end bearing's inner ring")
    S.add("bearing_gear_end", "b6205", rot_z(0.0, dz=-8.0), "rotor | counter-rotor",
          desc="the gear-end inner bearing (the bottom bridge-ring bearing's role)")
    S.add("hub", "hub", None, "counter-rotor", desc="the counter-rotor's hub")
    S.add("end_disc", "disc", None, "counter-rotor", desc="the counter-rotor's end disc under bridge ring A")
    S.add("gear_cr", "g_cr", rot_z(PHI_P[0], dz=za), "counter-rotor", desc="the counter-rotor's side gear")
    S.add("spacer_A", "sp_A", rot_z(0.0, dz=za - TOE_SIDE), "rotor", desc="spacer, the rotor gear's toe to the bearing")
    S.add("gear_rotor", "g_rotor", flip_x(-PHI_P[0], dz=za), "rotor", desc="the rotor's side gear, keyed")
    S.add("key", "key", flip_x(-PHI_P[0], dz=za - zb), "rotor", desc="the rotor gear's key")
    for j, ph in enumerate(PHI_P):
        T = radial(ph, za)
        S.add(f"pinion_{j + 1}", "g_pinion", T.Multiplied(rot_z(PIN_TURN)), "pinion", desc=f"pinion {j + 1} at {ph:.0f} deg")
        S.add(f"stub_{j + 1}", "stub", T, "pinion", desc="its stub shaft")
        S.add(f"cartridge_{j + 1}", "cart", T, "frame", desc="its cartridge sleeve")
        S.add(f"b6000_{j + 1}a", "b6000", radial_dz(ph, za, CART["b1"][0]), "pinion | frame", desc="its inner 6000-2Z")
        S.add(f"b6000_{j + 1}b", "b6000", radial_dz(ph, za, CART["b2"][0]), "pinion | frame", desc="its outer 6000-2Z")
        S.add(f"spacer_{j + 1}", "sp_pin", radial_dz(ph, za, CART["land"][0]), "pinion", desc="its inner rings' spacer")
    S.add("case", "case", None, "frame", desc="the gear case")
    S.add("bell", "bell", None, "frame", desc="the bell")
    S.add("spacer_B", "sp_B", rot_z(0.0, dz=-79.0), "rotor", desc="spacer, the gear's hub to the locating bearing")
    S.add("bearing_locating", "b6205", rot_z(0.0, dz=-94.0), "rotor | frame", desc="the locating end bearing (frame)")
    S.add("retaining_ring", "ret", rot_z(0.0, dz=-79.0), "frame", desc="the locating bearing's retaining ring")
    S.add("spacer_C", "sp_C", rot_z(0.0, dz=zc_top), "rotor", desc="spacer, the bearing to the pulley's bush")
    S.add("bush", "bush", None, "rotor", desc="the pulley's taper bush")
    S.add("pulley_80T", "p80", None, "rotor", desc="the machine's pulley")
    S.add("nut", "nut", rot_z(0.0, dz=-133.0), "rotor", desc="the lock nut")
    return S


def radial_dz(phi, z0, dz):
    return radial(phi, z0).Multiplied(rot_z(0.0, dz=dz))


def belt_sub():
    """the belt drive: the machine's pulley, the belt, the motor's pulley, the motor on its plate (§6), with the case,
    the bell and the shaft for reference."""
    S = Sub("belt", "The belt drive", "docs/drive-gear-belt.md §6")
    c = BELT["centre_mm"]
    R = reverser_sub()
    for nm in ("case", "bell", "hub", "gear_cr", "gear_rotor", "bearing_locating", "pulley_80T", "bush", "shaft", "nut"):
        q = [p for p in R.parts if p["name"] == nm][0]
        k = q["proto"]
        if k not in S.protos:
            S.protos[k] = R.protos[k]
        S.parts.append(dict(q, group=S.key))
    S.proto("belt", belt_shape, COL["belt"], "belt Gates 750-5M-15 (HTD 5M, 150 teeth, 15 wide)")
    S.proto("p20", pulley20, COL["al"], "pulley P20-5M-15F, flanged, bored Ø14")
    S.proto("plate", motor_plate, COL["al"], "Al 6082-T6, motor plate")
    S.proto("motor", motor_shape, COL["black"], "brushless DC motor 200 W 48 V (Nanotec / SMD APBA60M048030-E)")
    S.add("belt", "belt", None, "belt", desc="the belt")
    S.add("pulley_20T", "p20", rot_z(0.0, dx=c), "motor", desc="the motor's pulley")
    S.add("motor_plate", "plate", rot_z(0.0, dx=c), "frame", desc="the motor plate")
    S.add("motor", "motor", rot_z(0.0, dx=c), "motor", desc="the motor")
    return S


# =====================================================================================================================
# checks
# =====================================================================================================================
MADE_RHO = dict(g_rotor=RHO["ss"], g_cr=RHO["ss"], g_pinion=RHO["pom"], stub=RHO["ss"], cart=RHO["al"], case=RHO["al"],
                bell=RHO["al"], hub=RHO["al"], disc=RHO["g10"], sp_A=RHO["ss"], sp_B=RHO["ss"], sp_C=RHO["ss"],
                sp_pin=RHO["ss"], ret=RHO["ss"], plate=RHO["al"], ch_E=7700.0 * 0.95, ch_I=7700.0 * 0.95,
                ch_bobbin=RHO["pa_gf"])     # the laminations at sim/parts_first_cut.py's RHO_FE and K_STACK


def overlaps(S, pairs=None, tol=1e-3, three_d=False, exclude=()):
    """the overlap volume of every pair of placed parts (mm3), or of the pairs given; the pairs excluded are left out
    (the gear blanks' tooth zones, which overlap by design: their teeth are checked as solids)."""
    P = [(p["name"], S.placed(p, three_d)) for p in S.parts]
    out = []
    for i in range(len(P)):
        for j in range(i + 1, len(P)):
            a, b = P[i], P[j]
            if pairs is not None and (a[0], b[0]) not in pairs and (b[0], a[0]) not in pairs:
                continue
            if (a[0], b[0]) in exclude or (b[0], a[0]) in exclude:
                continue
            la, ha = bbox(a[1]); lb, hb = bbox(b[1])
            if any(ha[k] < lb[k] - 0.01 or hb[k] < la[k] - 0.01 for k in range(3)):
                continue
            v = volume(common(a[1], b[1]))
            if v > tol:
                out.append((a[0], b[0], round(v, 4)))
    return out


def clearances(S, pairs, three_d=False):
    by = {p["name"]: p for p in S.parts}
    return {f"{a} | {b}": round(distance(S.placed(by[a], three_d), S.placed(by[b], three_d)), 3) for a, b in pairs}


def pinion_bearings():
    """the pinion's two 6000-2Z as drawn: their centres 42 and 54 from the apex (CART), the mean mesh at R_m cos(delta_p)
    from it, so the mesh overhangs the inner bearing by a and the bearings are l apart [OC: statics]; the loads are the
    first cut's (sim/drive_sizing_results.json gear pinion_loads_*: an idler's two meshes push its axle 2 F_t)."""
    xm = GG["R_m"] * math.cos(math.radians(GG["delta_pinion_deg"]))
    c1, c2 = 0.5 * sum(CART["b1"]), 0.5 * sum(CART["b2"])
    a, l = c1 - xm, c2 - c1
    out = dict(mesh_from_apex_mm=xm, inner_centre_mm=c1, outer_centre_mm=c2, overhang_a_mm=a, spacing_l_mm=l,
               first_cut=dict(overhang_a_mm=12.0, spacing_l_mm=16.0))
    for case, key in (("steady", "pinion_loads_steady"), ("limit", "pinion_loads_fault")):
        F = _DR["gear"][key]["F_net_N"]
        R_in, R_out = F * (a + l) / l, F * a / l
        out[case] = dict(F_net_N=F, R_inner_N=R_in, R_outer_N=R_out, first_cut_R_inner_N=_DR["gear"][key]["R_inner_N"],
                         static_safety=B6000["C0"] / R_in, L10_h=(B6000["C"] / max(R_in, 1.0)) ** 3 * 1e6 / (60 * GG["pinion_rpm"]),
                         axle_sigma_MPa=32 * F * a * 1e-3 / (math.pi * 0.010 ** 3) / 1e6)
    return out


def main():
    t0 = time.time()
    res = dict(note="solids for the proposed parts the layout's model does not carry (sim/unmodelled_parts.py)",
               sources=dict(choke="sim/parts_first_cut_results.json la_lb.chosen", kick="sim/parts-first-cut-findings.md §3",
                            drive="sim/drive_sizing_results.json gear, belt, envelope; docs/drive-gear-belt.md §5-§8"),
               status="PROPOSED; the drive on the record's 940 mm stack-up, to be re-cut on the layout (ledger §6, item 71)")
    # --- the gears
    g = {}
    for nm, f in (("side_rotor", lambda: side_gear("rotor")), ("side_cr", lambda: side_gear("cr")), ("pinion", pinion)):
        bl, gt, data = f()
        rho = RHO["pom"] if nm == "pinion" else RHO["ss"]
        g[nm] = dict({k: (round(v, 4) if isinstance(v, float) else v) for k, v in data.items()},
                     valid_blank=valid(bl), valid_toothed=valid(gt), mass_kg=round(volume(gt) * 1e-9 * rho, 4),
                     blank_mass_kg=round(volume(bl) * 1e-9 * rho, 4))
    g["first_cut_masses_kg"] = dict(side=GS["m_side_kg"], hub=GS["m_hub_kg"], pinion=GS["m_pinion_kg"])
    res["gears"] = g
    # --- the reverser: overlaps (blanks and teeth), the mesh, the clearances between bodies
    R = reverser_sub()
    mesh = [(f"pinion_{j + 1}", gname) for j in range(3) for gname in ("gear_cr", "gear_rotor")]
    res["reverser"] = dict(parts=len(R.parts), overlaps_blank=overlaps(R, tol=0.5, exclude=mesh))
    res["reverser"]["mesh_overlap_mm3"] = {f"{a} | {b}": v for a, b, v in overlaps(R, pairs=mesh, tol=1e-6, three_d=True)} or "none"
    res["reverser"]["mesh_clearance_mm"] = clearances(R, mesh, three_d=True)
    pairs = [("gear_rotor", "case"), ("gear_rotor", "retaining_ring"), ("gear_rotor", "gear_cr"), ("gear_cr", "case"),
             ("gear_cr", "spacer_A"), ("gear_cr", "cartridge_1"), ("gear_rotor", "cartridge_1"),
             ("hub", "case"), ("hub", "collar"), ("hub", "spacer_A"), ("end_disc", "collar"), ("end_disc", "case"),
             ("pinion_1", "cartridge_1"), ("pinion_1", "spacer_A"), ("pinion_1", "case"), ("stub_1", "spacer_A"),
             ("pulley_80T", "bell"), ("pulley_80T", "case"), ("spacer_B", "retaining_ring")]
    res["reverser"]["clearance_mm"] = clearances(R, pairs)
    res["reverser"]["pinion_bearings"] = pinion_bearings()
    # --- the belt drive
    B = belt_sub()
    res["belt"] = dict(pitch_length_mm=round(belt_pitch_length(), 2), catalogue_mm=750.0, centres_mm=BELT["centre_mm"],
                       overlaps=overlaps(B, tol=0.5),
                       clearance_mm=clearances(B, [("belt", "bell"), ("belt", "case"), ("pulley_20T", "motor_plate"),
                                                   ("belt", "motor_plate"), ("pulley_80T", "bell")]))
    # --- the choke and the kick
    C = choke_sub()
    m_fe = (volume(C.placed(C.parts[0])) + volume(C.placed(C.parts[1]))) * 1e-9 * 0.95 * 7700.0   # k 0.95, 7700 (as sized)
    res["choke"] = dict(data=C.data, overlaps=overlaps(C, tol=1e-3), iron_kg_model=round(m_fe, 4),
                        iron_kg_first_cut=CH["m_fe_kg"], copper_kg_first_cut=CH["m_cu_kg"], total_kg_first_cut=CH["m_with_bobbin_kg"])
    K = kick_sub()
    res["kick"] = dict(overlaps=overlaps(K, tol=1e-3), parts=[p["name"] for p in K.parts])
    # --- every part's envelope, and the made parts' masses (the bought parts' are their makers')
    parts = {}
    for S in (R, B, C, K):
        for p in S.parts:
            k = p["proto"]
            s = S.placed(p, True)
            v = volume(s)
            rho = MADE_RHO.get(k)
            parts.setdefault(f"{S.key}/{k}", dict(material=S.protos[k][2], n=0, bbox_first=bbox(s), volume_mm3=round(v, 1),
                                                  **({"mass_kg": round(v * 1e-9 * rho, 4)} if rho else {})))
            parts[f"{S.key}/{k}"]["n"] += 1
    res["parts"] = parts
    res["run_s"] = round(time.time() - t0, 1)
    with open(OUT, "w") as f:
        json.dump(res, f, indent=1, default=str)
    print(json.dumps({k: res[k] for k in ("gears", "reverser", "belt", "choke", "kick")}, indent=1, default=str)[:6000])
    print(f"wrote {os.path.relpath(OUT, ROOT)} ({res['run_s']} s)")


if __name__ == "__main__":
    main()
