#!/usr/bin/env python3
"""sim/motor_geometry.py -- the C-EM / utron motor from the designer's STEP, placed outside the spark-gap zone.

Source: docs/geometry/motor/C-em_and_motor_coil_export.step (Fusion 360). One C-EM and one utron, with the
C-EM-to-utron spacing as the designer drew it. Only the distance of the pair from the rotation axis
changes here.                                                                                       [OC]
Frame of the source, read from the solids: x = radial (C opening toward the axis), y = tangential
(the utron's direction of travel), z = axial. Local origin = the utron centre (292, 0, 0).         [IR]

Placement:
  * innermost motor point (the utron coil) = the outermost stator object of the build + r_clear;
  * C-EMs at the register stations (A 30 + 60k, B 0 + 60k, stator);
  * utrons at the pole stations (15 + 60k, rotor, aligned with neither C-EM at rotor angle 0);
  * z = 0, the septum plane.                                                                        [OC]

Outputs:
  * docs/geometry/motor/src/<piece>.step: each source solid in the local frame;
  * docs/geometry/motor/motor-<tag>.json: the motor parts in the bill-of-solids schema, with shape "import";
  * docs/geometry/<build>-motor.step: the build plus the motor as one STEP, with each piece stored once and
    instanced;
  * sim/motor_geometry_results.json: the checks.
Usage: python3 sim/motor_geometry.py [--r-clear 40] [--no-step]
"""
import argparse
import json
import math
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path[:0] = [HERE]
import em_register as R                                  # noqa: E402

BUILD_TAG = "il2f-6563b90d"
BUILD = os.path.join(ROOT, "docs", "geometry", BUILD_TAG + ".json")
MOTOR_DIR = os.path.join(ROOT, "docs", "geometry", "motor")
SRC_STEP = os.path.join(MOTOR_DIR, "C-em_and_motor_coil_export.step")
SRC_DIR = os.path.join(MOTOR_DIR, "src")
RESULTS = os.path.join(HERE, "motor_geometry_results.json")
LOCAL_ORIGIN = (292.0, 0.0, 0.0)                         # utron centre in the source file [IR]

# source product -> piece key, role, body, material, colour
PIECES = {
    "em- V2": ("cem_core", "cem-core", "stator", "C-EM core (material OPEN: <=0.1 mm laminations / amorphous, see findings)", (0.45, 0.45, 0.5)),
    "spool half V2": ("cem_spool_1", "cem-spool", "stator", "spool, insulating (printed)", (0.85, 0.85, 0.8)),
    "spool half V2 v1(Mirror)": ("cem_spool_2", "cem-spool", "stator", "spool, insulating (printed)", (0.85, 0.85, 0.8)),
    "C magnet coil": ("cem_coil", "cem-coil", "stator", "Cu magnet wire, enamelled", (0.85, 0.5, 0.2)),
    "utron": ("utron_core", "utron-core", "rotor AB", "utron core (material OPEN: laminated steel / SMC, see findings)", (0.3, 0.3, 0.35)),
    "utron coil top": ("utron_coil_1", "utron-coil", "rotor AB", "Cu magnet wire, open ends (not in the circuit; may be omitted)", (0.8, 0.45, 0.2)),
    "utron coil top(Mirror)": ("utron_coil_2", "utron-coil", "rotor AB", "Cu magnet wire, open ends (not in the circuit; may be omitted)", (0.8, 0.45, 0.2)),
}
POLE_DEG = [15.0 + 60.0 * k for k in range(6)]


# ---------------------------------------------------------------------------------------------------------
# STEP I/O (OpenCascade)
# ---------------------------------------------------------------------------------------------------------
def read_leaves(path):
    """{product name: located shape} for every leaf solid of an XCAF STEP."""
    from OCP.STEPCAFControl import STEPCAFControl_Reader
    from OCP.TDocStd import TDocStd_Document
    from OCP.TCollection import TCollection_ExtendedString
    from OCP.XCAFDoc import XCAFDoc_DocumentTool
    from OCP.TDF import TDF_Label, TDF_ChildIterator
    from OCP.TDataStd import TDataStd_Name
    from OCP.TopLoc import TopLoc_Location
    doc = TDocStd_Document(TCollection_ExtendedString("XmlOcaf"))
    rd = STEPCAFControl_Reader(); rd.SetNameMode(True)
    rd.ReadFile(path); rd.Transfer(doc)
    tool = XCAFDoc_DocumentTool.ShapeTool_s(doc.Main())

    def nm(lab):
        a = TDataStd_Name()
        return a.Get().ToExtString() if lab.FindAttribute(TDataStd_Name.GetID_s(), a) else ""
    out = {}

    def walk(lab, loc):
        if tool.IsAssembly_s(lab):
            it = TDF_ChildIterator(lab, False)
            while it.More():
                c = it.Value()
                if tool.IsComponent_s(c):
                    ref = TDF_Label(); tool.GetReferredShape_s(c, ref)
                    walk(ref, loc.Multiplied(tool.GetLocation_s(c)))
                it.Next()
        else:
            out[nm(lab)] = tool.GetShape_s(lab).Moved(loc)
    it = TDF_ChildIterator(tool.Label(), False)
    while it.More():
        lab = it.Value()
        if tool.IsFree_s(lab) and tool.IsShape_s(lab):
            walk(lab, TopLoc_Location())
        it.Next()
    return out


def trsf(dx=0.0, dy=0.0, dz=0.0, rot_deg=0.0):
    """translate, then rotate about the machine axis (z)."""
    from OCP.gp import gp_Trsf, gp_Vec, gp_Ax1, gp_Pnt, gp_Dir
    t = gp_Trsf(); t.SetTranslation(gp_Vec(dx, dy, dz))
    r = gp_Trsf(); r.SetRotation(gp_Ax1(gp_Pnt(0, 0, 0), gp_Dir(0, 0, 1)), math.radians(rot_deg))
    return r.Multiplied(t)


def moved(shape, t):
    from OCP.BRepBuilderAPI import BRepBuilderAPI_Transform
    return BRepBuilderAPI_Transform(shape, t, True).Shape()


def props(shape):
    from OCP.GProp import GProp_GProps
    from OCP.BRepGProp import BRepGProp
    from OCP.Bnd import Bnd_Box
    from OCP.BRepBndLib import BRepBndLib
    g = GProp_GProps(); BRepGProp.VolumeProperties_s(shape, g)
    b = Bnd_Box(); BRepBndLib.Add_s(shape, b)
    if b.IsVoid():
        return dict(volume=0.0, centre=None, bb_min=None, bb_max=None)
    p, q = b.CornerMin(), b.CornerMax()
    c = g.CentreOfMass()
    return dict(volume=g.Mass(), centre=[c.X(), c.Y(), c.Z()], bb_min=[p.X(), p.Y(), p.Z()], bb_max=[q.X(), q.Y(), q.Z()])


def mesh_points(shape, defl=0.3):
    from OCP.BRepMesh import BRepMesh_IncrementalMesh
    from OCP.BRep import BRep_Tool
    from OCP.TopoDS import TopoDS
    from OCP.TopExp import TopExp_Explorer
    from OCP.TopAbs import TopAbs_FACE
    from OCP.TopLoc import TopLoc_Location
    BRepMesh_IncrementalMesh(shape, defl, False, 0.3, True)
    e = TopExp_Explorer(shape, TopAbs_FACE); P = []
    while e.More():
        f = TopoDS.Face(e.Current()); loc = TopLoc_Location()
        tri = BRep_Tool.Triangulation_s(f, loc)
        if tri is not None:
            tr = loc.Transformation()
            for i in range(1, tri.NbNodes() + 1):
                p = tri.Node(i).Transformed(tr); P.append((p.X(), p.Y(), p.Z()))
        e.Next()
    return np.array(P)


def cem_squaring(core):
    """the C-EM core is a flat plate (30 mm); in the source it is turned about its own z axis and its mid-plane
    is off the utron centre. Returns (tilt_deg, mid-plane offset mm, the correcting transform): rotate by -tilt
    about the z axis through the mid-plane point nearest the utron centre, then shift tangentially so that the
    mid-plane passes through the utron centre (y = 0).                                               [OC]"""
    from OCP.TopExp import TopExp_Explorer
    from OCP.TopAbs import TopAbs_FACE
    from OCP.TopoDS import TopoDS
    from OCP.BRepAdaptor import BRepAdaptor_Surface
    from OCP.GeomAbs import GeomAbs_Plane
    from OCP.GProp import GProp_GProps
    from OCP.BRepGProp import BRepGProp
    from OCP.gp import gp_Trsf, gp_Vec, gp_Ax1, gp_Pnt, gp_Dir
    n, offs = None, []
    e = TopExp_Explorer(core, TopAbs_FACE)
    while e.More():
        f = TopoDS.Face(e.Current()); ad = BRepAdaptor_Surface(f)
        if ad.GetType() == GeomAbs_Plane:
            d = ad.Plane().Axis().Direction(); d = np.array([d.X(), d.Y(), d.Z()])
            if abs(d[2]) < 1e-6 and abs(d[1]) > 0.9:                       # the two plate faces
                n = d * np.sign(d[1]) if n is None else n
                g = GProp_GProps(); BRepGProp.SurfaceProperties_s(f, g); c = g.CentreOfMass()
                offs.append(float(np.dot([c.X(), c.Y(), c.Z()], n)))
        e.Next()
    tilt = math.degrees(math.atan2(-n[0], n[1]))
    mid = 0.5 * (min(offs) + max(offs))
    p0 = mid * n
    r = gp_Trsf(); r.SetRotation(gp_Ax1(gp_Pnt(p0[0], p0[1], 0.0), gp_Dir(0, 0, 1)), math.radians(-tilt))
    t = gp_Trsf(); t.SetTranslation(gp_Vec(0.0, -p0[1], 0.0))
    return tilt, mid, max(offs) - min(offs), t.Multiplied(r)


CEM_KEYS = ("cem_core", "cem_spool_1", "cem_spool_2", "cem_coil")


def split_source():
    """each source solid -> src/<key>.step in the local frame (the C-EM squared to the utron, cem_squaring);
    returns ({key: (shape, props, meta)}, unused products, squaring)."""
    from OCP.STEPControl import STEPControl_Writer, STEPControl_AsIs
    from OCP.Interface import Interface_Static
    leaves = read_leaves(SRC_STEP)
    missing = [k for k in PIECES if k not in leaves]
    if missing:
        raise SystemExit(f"source STEP lacks {missing}; has {sorted(leaves)}")
    os.makedirs(SRC_DIR, exist_ok=True)
    t = trsf(-LOCAL_ORIGIN[0], -LOCAL_ORIGIN[1], -LOCAL_ORIGIN[2])
    core_prod = [p for p, v in PIECES.items() if v[0] == "cem_core"][0]
    tilt, mid, thick, sq = cem_squaring(moved(leaves[core_prod], t))
    out = {}
    for prod, (key, role, body, mat, rgb) in PIECES.items():
        s = moved(leaves[prod], t)
        if key in CEM_KEYS:
            s = moved(s, sq)
        path = os.path.join(SRC_DIR, key + ".step")
        Interface_Static.SetCVal_s("write.step.product.name", key)
        w = STEPControl_Writer(); w.Transfer(s, STEPControl_AsIs); w.Write(path)
        out[key] = (s, props(s), dict(source_product=prod, role=role, body=body, material=mat, rgb=rgb,
                                      file=os.path.relpath(path, MOTOR_DIR)))
    check_tilt, check_mid, _, _ = cem_squaring(out["cem_core"][0])
    squaring = dict(source_tilt_deg=tilt, source_midplane_offset_mm=mid, core_plate_mm=thick,
                    after_tilt_deg=check_tilt, after_midplane_offset_mm=check_mid,
                    note="C-EM turned by -tilt about its own z axis, mid-plane shifted onto the utron centre "
                         "(the shift is %.2f deg of station angle at the placement radius)" % 0.0)
    return out, sorted(set(leaves) - set(PIECES)), squaring


# ---------------------------------------------------------------------------------------------------------
# the build envelope
# ---------------------------------------------------------------------------------------------------------
def revolved(p):
    """(r_min, r_max, z_min, z_max) of a bill-of-solids part revolved about the axis."""
    s = p["shape"]
    if s == "sector":
        return p["r_in"], p["r_out"], p["z0"], p["z1"]
    if s == "sphere":
        c, r = p["c"], p["r"]; rc = math.hypot(c[0], c[1])
        return max(0.0, rc - r), rc + r, c[2] - r, c[2] + r
    if s == "rod":
        a, b, r = np.array(p["p0"]), np.array(p["p1"]), p["r"]
        ts = np.linspace(0, 1, 41); P = a[None] + ts[:, None] * (b - a)[None]
        rr = np.hypot(P[:, 0], P[:, 1])
        return max(0.0, rr.min() - r), rr.max() + r, min(a[2], b[2]) - r, max(a[2], b[2]) + r
    raise ValueError(s)


def build_envelope(build):
    rows = [(revolved(p), p) for p in build["parts"]]
    outer = max(rows, key=lambda x: x[0][1])
    return rows, outer


# ---------------------------------------------------------------------------------------------------------
# placement and parts
# ---------------------------------------------------------------------------------------------------------
def placement(pieces, build, r_clear):
    rows, (env, worst) = build_envelope(build)
    x_in = min(pr["bb_min"][0] for _, pr, _ in pieces.values())          # innermost local x (the utron coil)
    r_u = env[1] + r_clear - x_in
    return dict(r_utron_centre=r_u, r_clear=r_clear, local_x_min=x_in, build_r_out=env[1], build_r_out_part=worst["name"])


def motor_parts(pieces, pl):
    st = R.val(R.preset("RA"), "stator", "cem_stations_deg")
    parts = []

    def add(key, name, theta, node, group, desc):
        _, pr, m = pieces[key]
        lab = f"{group} / {name} - {desc} [{m['material']}, {m['body']}]"
        parts.append(dict(name=name, label=lab, assembly=group, role=m["role"], node=node, material=m["material"],
                          body=m["body"], shape="import", file=m["file"], piece=key,
                          place=dict(r=pl["r_utron_centre"], theta_deg=theta, z=0.0),
                          rgb=list(m["rgb"]), volume=pr["volume"], chains=[f"motor-{name.split('_')[1]}"]))
    for lab, th in sorted(st.items()):
        side, k = lab[0], lab[1:]
        node = "2" if side == "A" else "3"                                 # core bonded to the coil's rail end (D-6) [OC]
        mid = f"m{side}{k}"
        add("cem_core", f"CEM_{lab}_core", th, node, "motor-stator", f"C-EM {lab} core, bonded to node {node} (rail end of L_{lab})")
        add("cem_spool_1", f"CEM_{lab}_spool1", th, "", "motor-stator", f"C-EM {lab} spool half")
        add("cem_spool_2", f"CEM_{lab}_spool2", th, "", "motor-stator", f"C-EM {lab} spool half")
        add("cem_coil", f"CEM_{lab}_coil", th, "", "motor-stator", f"L_{lab}: node {node} -> {mid} -> SG{1 if side == 'A' else 2}-{k}")
    for k, th in enumerate(POLE_DEG, 1):
        add("utron_core", f"UTRON_{k}_core", th, "floating", "motor-rotor", f"utron {k} core, floating")
        add("utron_coil_1", f"UTRON_{k}_coil1", th, "floating", "motor-rotor", f"utron {k} coil half 1, open, not in the circuit")
        add("utron_coil_2", f"UTRON_{k}_coil2", th, "floating", "motor-rotor", f"utron {k} coil half 2, open, not in the circuit")
    return parts


def part_trsf(p):
    pl = p["place"]
    return trsf(pl["r"], 0.0, pl["z"], pl["theta_deg"])


# ---------------------------------------------------------------------------------------------------------
# checks
# ---------------------------------------------------------------------------------------------------------
def annulus(r0, r1, z0, z1):
    from OCP.BRepPrimAPI import BRepPrimAPI_MakeCylinder
    from OCP.BRepAlgoAPI import BRepAlgoAPI_Cut
    from OCP.gp import gp_Ax2, gp_Pnt, gp_Dir
    ax = gp_Ax2(gp_Pnt(0, 0, z0), gp_Dir(0, 0, 1))
    o = BRepPrimAPI_MakeCylinder(ax, r1, z1 - z0).Shape()
    i = BRepPrimAPI_MakeCylinder(ax, r0, z1 - z0).Shape()
    return BRepAlgoAPI_Cut(o, i).Shape()


def common_volume(a, b):
    from OCP.BRepAlgoAPI import BRepAlgoAPI_Common
    return props(BRepAlgoAPI_Common(a, b).Shape())["volume"]


def jaw_gap(pieces):
    """the air gap between the jaws and the utron (core and coil), from an axial line scan of the core at y = 0."""
    from OCP.BRepClass3d import BRepClass3d_SolidClassifier
    from OCP.gp import gp_Pnt
    from OCP.TopAbs import TopAbs_IN
    core = pieces["cem_core"][0]
    u = pieces["utron_core"][1]
    coil_z = max(abs(pieces[k][1]["bb_max"][2]) for k in ("utron_coil_1", "utron_coil_2"))
    coil_z = max(coil_z, max(abs(pieces[k][1]["bb_min"][2]) for k in ("utron_coil_1", "utron_coil_2")))
    rows = []
    for x in np.arange(u["bb_min"][0], u["bb_max"][0] + 1e-9, 2.0):
        zs = np.arange(0.0, 70.0, 0.05)
        inside = [z for z in zs if BRepClass3d_SolidClassifier(core, gp_Pnt(x, 0.0, z), 1e-4).State() == TopAbs_IN]
        if inside:
            rows.append((float(x), float(min(inside))))
    jaw = min(z for _, z in rows) if rows else None
    xs = [x for x, z in rows]
    return dict(jaw_inner_z_min=jaw, jaw_x_range_over_utron=[min(xs), max(xs)] if xs else None,
                utron_core_half_height=u["bb_max"][2], utron_coil_half_height=coil_z,
                gap_core_mm=jaw - u["bb_max"][2] if jaw else None, gap_coil_mm=jaw - coil_z if jaw else None, scan=rows)


def jaw_utron_capacitance(pieces, gap):
    """parallel-plate estimate of the jaw-utron capacitance at alignment (two jaws in parallel, overlap in x and
    y); a floor -- fringing adds roughly as much again.                                             [RH]"""
    from OCP.BRepClass3d import BRepClass3d_SolidClassifier
    from OCP.gp import gp_Pnt
    from OCP.TopAbs import TopAbs_IN
    core = pieces["cem_core"][0]; u = pieces["utron_core"][1]
    z = gap["jaw_inner_z_min"] + 0.5
    xs = np.arange(u["bb_min"][0], u["bb_max"][0], 1.0); ys = np.arange(u["bb_min"][1], u["bb_max"][1], 1.0)
    area = sum(1 for x in xs for y in ys if BRepClass3d_SolidClassifier(core, gp_Pnt(x, y, z), 1e-4).State() == TopAbs_IN)
    C = 2 * 8.854e-12 * area * 1e-6 / (gap["gap_core_mm"] * 1e-3)
    return dict(overlap_mm2_per_jaw=float(area), C_pF_parallel_plate=C * 1e12)


def checks(pieces, pl, parts, build):
    from OCP.TopoDS import TopoDS_Compound
    from OCP.BRep import BRep_Builder
    res = {}
    rows, _ = build_envelope(build)
    # 1. radial zone: every motor piece beyond the build's outermost object by r_clear
    rmin = {}
    for key, (s, pr, m) in pieces.items():
        P = mesh_points(s, 0.5) + np.array([pl["r_utron_centre"], 0, 0])
        rmin[key] = float(np.hypot(P[:, 0], P[:, 1]).min())
    res["G-MOT-ZONE"] = dict(build_r_out=pl["build_r_out"], build_r_out_part=pl["build_r_out_part"], r_clear=pl["r_clear"],
                             motor_r_min={k: round(v, 2) for k, v in rmin.items()},
                             pass_=bool(min(rmin.values()) >= pl["build_r_out"] + pl["r_clear"] - 1.0))
    # 2. the sweeps: the rotor's utron ring vs every stator solid; the stator's C-EM ring vs every rotor solid
    u_keys = ["utron_core", "utron_coil_1", "utron_coil_2"]
    c_keys = ["cem_core", "cem_spool_1", "cem_spool_2", "cem_coil"]

    def ring_of(keys):
        r0, r1, z0, z1 = 1e9, 0, 1e9, -1e9
        for k in keys:
            P = mesh_points(pieces[k][0], 0.5) + np.array([pl["r_utron_centre"], 0, 0])
            rr = np.hypot(P[:, 0], P[:, 1]); r0, r1 = min(r0, rr.min()), max(r1, rr.max())
            z0, z1 = min(z0, P[:, 2].min()), max(z1, P[:, 2].max())
        return float(r0), float(r1), float(z0), float(z1)
    U, Cr = ring_of(u_keys), ring_of(c_keys)
    sw_u = annulus(*U)
    hit_c = {}
    for k in c_keys:                                                     # exact: the C-EM pieces vs the utron ring
        v = common_volume(sw_u, moved(pieces[k][0], trsf(pl["r_utron_centre"])))
        if v > 1e-3:
            hit_c[k] = v

    def env_hits(ring, bodies):
        out = []
        for (r0, r1, z0, z1), p in rows:
            if p.get("body") not in bodies:
                continue
            if r1 > ring[0] and r0 < ring[1] and z1 > ring[2] and z0 < ring[3]:
                out.append(p["name"])
        return out
    res["G-MOT-SWEEP"] = dict(utron_ring=U, cem_ring=Cr,
                              utron_ring_vs_cem_mm3=hit_c,
                              utron_ring_vs_build_stator=env_hits(U, ("stator",)),
                              cem_ring_vs_build_rotor=env_hits(Cr, ("rotor A", "rotor B", "rotor AB")),
                              pass_=not hit_c and not env_hits(U, ("stator",)) and not env_hits(Cr, ("rotor A", "rotor B", "rotor AB")))
    # 3. the trunnion path: the plane z ~ 0 between the build rim and the utron's inner face must be free of stator parts
    tz = 25.0
    path = [p["name"] for (r0, r1, z0, z1), p in rows if p.get("body") == "stator" and r1 > 500.0 and z1 > -tz and z0 < tz]
    res["G-MOT-TRUNNION"] = dict(band=dict(r=[500.0, U[0]], z=[-tz, tz]), stator_parts_in_band=path, pass_=not path,
                                 note="a rotor spoke / trunnion from the septum rim to the utron sweeps this band at every angle")
    # 4. jaw gap and the jaw-utron capacitance (the utron is a floating carrier between A cores (node 2) and B cores (node 3))
    g = jaw_gap(pieces)
    res["G-MOT-JAW"] = {k: v for k, v in g.items() if k != "scan"}
    res["G-MOT-JAW"].update(jaw_utron_capacitance(pieces, g))
    # 5. the mid-node lead SG1-k -> C-EM coil: its length against the 3.3 pF per-node budget (v4 pump check)
    sph = {p["name"]: p for p in build["parts"] if p["shape"] == "sphere"}
    coil_c = np.array(pieces["cem_coil"][1]["centre"]) + np.array([pl["r_utron_centre"], 0, 0])
    st = R.val(R.preset("RA"), "stator", "cem_stations_deg")
    leads = []
    for lab, th in sorted(st.items()):
        side = lab[0]
        a = math.radians(th)
        cc = np.array([coil_c[0] * math.cos(a) - coil_c[1] * math.sin(a), coil_c[0] * math.sin(a) + coil_c[1] * math.cos(a), coil_c[2]])
        rc, thc = math.hypot(cc[0], cc[1]), math.degrees(math.atan2(cc[1], cc[0]))
        # its gap sphere: the nearest SG1 (A) / SG2 (B) sphere in angle -- a lower bound on the route [IR: not drawn]
        best = None
        for n, s in sph.items():
            if not n.startswith(f"SG{1 if side == 'A' else 2}_sph_"):
                continue
            c = np.array(s["c"]); rs = math.hypot(c[0], c[1])
            dth = abs(((thc - math.degrees(math.atan2(c[1], c[0])) + 180.0) % 360.0) - 180.0)
            L = abs(rc - rs) + abs(cc[2] - c[2]) + math.radians(dth) * rs    # Manhattan route: radial + axial + arc [RH]
            if best is None or L < best[0]:
                best = (L, n, dth)
        if best is None:
            continue
        L, sname, dth = best
        leads.append(dict(cem=lab, sphere=sname, arc_deg=round(dth, 1), route_mm=round(L, 0)))
    Ls = [l["route_mm"] for l in leads]
    # bare wire, 1.5 mm radius, ~40 mm from the nearest other-node conductor: C' = 2 pi eps0 / acosh(h/a) [RH]
    Cp = 2 * math.pi * 8.854e-12 / math.acosh(40.0 / 1.5) * 1e12 / 1000.0       # pF per mm
    res["G-MOT-LEAD"] = dict(leads=leads, route_mm=[min(Ls), max(Ls)] if Ls else None, C_bare_pF_per_mm=Cp,
                             C_bare_pF=[min(Ls) * Cp, max(Ls) * Cp] if Ls else None, budget_pF=3.3,
                             pass_bare=bool(Ls and max(Ls) * Cp <= 3.3),
                             note="the lead SG-k -> coil is the mid node; bare, it uses up the 3.3 pF budget; screened "
                                  "(inner = mid node, screen = the rail-end node, the core bonded to it) its capacitance "
                                  "moves across the coil, where 50 pF costs dz ~ -0.024")
    return res


# ---------------------------------------------------------------------------------------------------------
# combined STEP: the build + the motor, each piece stored once and instanced
# ---------------------------------------------------------------------------------------------------------
def write_combined(pieces, parts, out_path, base_step):
    from OCP.STEPCAFControl import STEPCAFControl_Reader, STEPCAFControl_Writer
    from OCP.STEPControl import STEPControl_AsIs
    from OCP.TDocStd import TDocStd_Document
    from OCP.TCollection import TCollection_ExtendedString
    from OCP.XCAFDoc import XCAFDoc_DocumentTool, XCAFDoc_ColorType
    from OCP.TDataStd import TDataStd_Name
    from OCP.TopLoc import TopLoc_Location
    from OCP.Quantity import Quantity_Color, Quantity_TypeOfColor
    from OCP.Interface import Interface_Static
    doc = TDocStd_Document(TCollection_ExtendedString("XmlOcaf"))
    if base_step:
        rd = STEPCAFControl_Reader(); rd.SetNameMode(True); rd.SetColorMode(True)
        rd.ReadFile(base_step); rd.Transfer(doc)
    stl = XCAFDoc_DocumentTool.ShapeTool_s(doc.Main())
    col = XCAFDoc_DocumentTool.ColorTool_s(doc.Main())
    name = lambda lab, t: TDataStd_Name.Set_s(lab, TCollection_ExtendedString(t))
    top = stl.NewShape(); name(top, "motor - C-EMs (stator) and utrons (rotor), from C-em_and_motor_coil_export.step")
    groups = {}
    for g in ("motor-stator", "motor-rotor"):
        lab = stl.NewShape(); name(lab, g); groups[g] = lab
    protos = {}
    for key, (s, pr, m) in pieces.items():
        lab = stl.AddShape(s, False); name(lab, key)
        col.SetColor(lab, Quantity_Color(*m["rgb"], Quantity_TypeOfColor.Quantity_TOC_RGB), XCAFDoc_ColorType.XCAFDoc_ColorSurf)
        protos[key] = lab
    for p in parts:
        comp = stl.AddComponent(groups[p["assembly"]], protos[p["piece"]], TopLoc_Location(part_trsf(p)))
        name(comp, p["label"])
    for g, lab in groups.items():
        c = stl.AddComponent(top, lab, TopLoc_Location()); name(c, g)
    stl.UpdateAssemblies()
    Interface_Static.SetCVal_s("write.step.product.name", "PumpGeometry+motor")
    w = STEPCAFControl_Writer(); w.SetNameMode(True); w.SetColorMode(True)
    w.Transfer(doc, STEPControl_AsIs); w.Write(out_path)
    return out_path


# ---------------------------------------------------------------------------------------------------------
# design JSONs for the CAD macros (tools/pump-geometry.FCMacro, the Fusion 360 add-in), and the macro check
# ---------------------------------------------------------------------------------------------------------
MOTOR_ASSEMBLIES = [dict(key="motor-stator", label="motor-stator - C-EMs: cores (bonded to the rail end), spools, coils"),
                    dict(key="motor-rotor", label="motor-rotor - utrons: cores and coils, floating")]


def design_jsons(build, parts, tag):
    """<tag>+motor.json (the build plus the motor) and <tag>-motor-only.json, both pump-geometry/1, in MOTOR_DIR
    so that the parts' "file" paths (src/...) resolve."""
    merged = dict(build)
    merged["assemblies"] = list(build["assemblies"]) + MOTOR_ASSEMBLIES
    merged["parts"] = list(build["parts"]) + parts
    merged["top_label"] = build["top_label"] + " + motor"
    only = dict(schema="pump-geometry/1", lock=dict(build["lock"]), assemblies=MOTOR_ASSEMBLIES, parts=parts,
                top_label="motor (" + tag + ")")
    paths = []
    for d, nm in ((merged, f"{tag}+motor.json"), (only, f"{tag}-motor-only.json")):
        p = os.path.join(MOTOR_DIR, nm)
        json.dump(d, open(p, "w"), indent=0)
        paths.append(p)
    return paths


def macro_check(pieces, parts, only_json):
    """run tools/pump-geometry.FCMacro (through the OpenCascade stand-in of sim/pump_geometry_gates.py) on the
    motor-only design and compare every placed solid with the instanced STEP placement: volume and centroid."""
    import pump_geometry_gates as GG
    fc = GG._install_occ_freecad()
    part = sys.modules["Part"]
    Shape = type(part.makeSphere(1.0, fc.Vector()))
    from OCP.STEPControl import STEPControl_Reader
    from OCP.BRepBuilderAPI import BRepBuilderAPI_Copy

    def read(path):
        r = STEPControl_Reader(); r.ReadFile(path); r.TransferRoots(); return Shape(r.OneShape())

    def translate(self, v):
        self.s = moved(self.s, trsf(v.x, v.y, v.z)); return self

    def copy(self):
        return Shape(BRepBuilderAPI_Copy(self.s).Shape())
    part.read, Shape.translate, Shape.copy = read, translate, copy
    os.environ["PUMP_GEOMETRY_JSON"] = only_json
    src = open(os.path.join(ROOT, "tools", "pump-geometry.FCMacro"), encoding="utf8").read()
    ns = {"__name__": "__macro__"}
    exec(compile(src, "pump-geometry.FCMacro", "exec"), ns)
    for ext in (".step", ".FCStd"):                                     # the macro's own export: not instanced, ~10x larger
        f = os.path.splitext(only_json)[0] + ext
        if os.path.exists(f):
            os.remove(f)
    doc = fc.DOCS[-1]
    objs = {o.Label: o for o in doc.Objects if o.TypeId == "Part::Feature"}
    worst_v, worst_c = 0.0, 0.0
    for p in parts:
        a = props(objs[p["label"]].Shape.s)
        b = props(moved(pieces[p["piece"]][0], part_trsf(p)))
        worst_v = max(worst_v, abs(a["volume"] - b["volume"]) / b["volume"])
        worst_c = max(worst_c, float(np.linalg.norm(np.array(a["centre"]) - np.array(b["centre"]))))
    return dict(n=len(parts), n_built=len(objs), worst_rel_volume=worst_v, worst_centroid_mm=worst_c,
                pass_=bool(len(objs) == len(parts) and worst_v < 1e-6 and worst_c < 1e-6))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--r-clear", type=float, default=40.0, help="mm between the build's outermost object and the motor")
    ap.add_argument("--no-step", action="store_true")
    a = ap.parse_args()
    build = json.load(open(BUILD))
    pieces, skipped, squaring = split_source()
    pl = placement(pieces, build, a.r_clear)
    squaring["note"] = squaring["note"].replace("0.00 deg", "%.2f deg" % math.degrees(abs(squaring["source_midplane_offset_mm"]) / pl["r_utron_centre"]))
    pl["cem_squaring"] = squaring
    parts = motor_parts(pieces, pl)
    tag = f"{BUILD_TAG}-rc{a.r_clear:g}"
    jpath = os.path.join(MOTOR_DIR, f"motor-{tag}.json")
    json.dump(dict(schema="motor-parts/1", build=BUILD_TAG, source=os.path.relpath(SRC_STEP, ROOT), local_origin=LOCAL_ORIGIN,
                   frame="x radial (C opening toward the axis), y tangential, z axial; placed by translate x by place.r, "
                         "then rotate about z by place.theta_deg, then z += place.z",
                   placement=pl, pieces={k: dict(m, **{kk: vv for kk, vv in pr.items()}) for k, (s, pr, m) in pieces.items()},
                   source_products_not_used=skipped, parts=parts), open(jpath, "w"), indent=1)
    merged_json, only_json = design_jsons(build, parts, tag)
    res = dict(placement=pl, parts_json=os.path.relpath(jpath, ROOT), n_parts=len(parts), source_products_not_used=skipped,
               design_json=os.path.relpath(merged_json, ROOT), design_json_motor_only=os.path.relpath(only_json, ROOT))
    res["G-MOT-MACRO"] = macro_check(pieces, parts, only_json)
    res.update(checks(pieces, pl, parts, build))
    if not a.no_step:
        out = os.path.join(ROOT, "docs", "geometry", f"{tag}-motor.step")
        write_combined(pieces, parts, out, os.path.join(ROOT, "docs", "geometry", BUILD_TAG + ".step"))
        res["step"] = os.path.relpath(out, ROOT)
        mo = os.path.join(MOTOR_DIR, f"motor-{tag}.step")
        write_combined(pieces, parts, mo, None)
        res["step_motor_only"] = os.path.relpath(mo, ROOT)
    json.dump(res, open(RESULTS, "w"), indent=1, default=float)
    for k, v in res.items():
        print(k, ":", json.dumps(v, default=float)[:600])


if __name__ == "__main__":
    main()
