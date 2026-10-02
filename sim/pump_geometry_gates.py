#!/usr/bin/env python3
"""sim/pump_geometry_gates.py -- PUMP-SYNTH stage 2 (plate geometry) build checks.

  G-SEED  the geometrizer's seed equals the r0.15 DXF part views (Ca odd / Cb even 30-deg sectors r110-175,
          C1/C2 stators r95-387, Cx pickups r58-350, island bars r75-350) and the freeze 309 pF
  G-RT    round trip: inverse geometry realizes the locked Ca/Cb to 1e-12; a manufacturing rounding is run
          through the exact engine (z with Ca/Cb pinned at the realized values)
  G-ADJ   every capacitor's two foils face each other across exactly its own gap (stack order)
  G-JS    tools/pump-geometry.js = sim/pump_geometry.py (design JSON, 1e-12) on randomized inputs
  G-CAD   tools/pump-geometry.FCMacro executed through an OpenCascade stand-in for FreeCAD/Part:
          every solid valid, its volume = the analytic value (1e-6), no two solids interpenetrate,
          STEP written (docs/geometry/freeze-v010-CaCb.step) from docs/geometry/freeze-v010-CaCb.json
  G-Z     Z-stretch: the stretched build passes every check, the base thicknesses show the shortfall, no C changes
  G-SGR   radial bar band (TMD 2026-10-02), from the solids: fire / backstop on radial rim stems meeting the tip
          vertically, load on a radial frame arm meeting it horizontally (3 of 4 spheres on horizontal stems per
          side), spacings = the freeze table, ND2 / ND3 trimmed inside the tip path; the axial layout still clean
  G-F360  tools/fusion360/PumpGeometry built through an OpenCascade stand-in for adsk: the same solids and names
  G-CI    sim/circuit_integrity.py: the reference build is the netlist of record (JSON and STEP), JS parity, faults
Usage: python3 sim/pump_geometry_gates.py [--only G-SEED,...]
"""
import json
import math
import os
import random
import subprocess
import sys
import types

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path[:0] = [HERE, ROOT, os.path.join(ROOT, "reference")]
import pump_geometry as PG          # noqa: E402
import pump_sizing as PS            # noqa: E402

OUTDIR = os.path.join(ROOT, "docs", "geometry")
OUT = {}


def freeze_lock(z=1.3254745316585308):
    return PG.lock_record(PS.size(), {}, z, True, "pump_engine r0.1")


def gate_seed():
    import ezdxf
    doc = ezdxf.readfile(os.path.join(ROOT, "docs", "varcap-nodeanalysis-template-r0.15_TMD_layout.dxf"))
    msp = doc.modelspace()
    C = (3600.0, -2900.0)                         # the "stack section (assembly)" plan overlay centre
    got = {}
    for lay in ("ND2-Ca-ELECTRODE", "ND3-Cb-ELECTRODE", "ND1-C1-STATOR-PLATE", "ND4-C2-STATOR-PLATE",
                "ND2-Cx4-PICKUP-STATOR", "ND3-Cx3-PICKUP-STATOR", "ND7-ISLAND-BARS-onB", "ND8-ISLAND-BARS-onA"):
        radii, starts = set(), set()
        for e in msp:
            if e.dxf.layer != lay:
                continue
            if e.dxftype() == "ARC" and abs(e.dxf.center.x - C[0]) < 1 and abs(e.dxf.center.y - C[1]) < 1:
                starts.add(round(e.dxf.start_angle, 2) % 360.0)
            if e.dxftype() in ("LWPOLYLINE", "LINE"):
                pts = [(p[0], p[1]) for p in e.get_points()] if e.dxftype() == "LWPOLYLINE" else \
                    [(e.dxf.start.x, e.dxf.start.y), (e.dxf.end.x, e.dxf.end.y)]
                for x, y in pts:
                    if abs(x - C[0]) < 520 and abs(y - C[1]) < 520:
                        radii.add(round(math.hypot(x - C[0], y - C[1]), 1))
        got[lay] = (min(radii), max(radii), sorted(starts))
    d = PG.build(freeze_lock(), dict(ca_mode="forward"))
    fp = d["footprints"]
    want = {"ND2-Ca-ELECTRODE": fp["Ca_el"], "ND3-Cb-ELECTRODE": fp["Cb_el"], "ND1-C1-STATOR-PLATE": fp["C1_stator"],
            "ND4-C2-STATOR-PLATE": fp["C2_stator"], "ND2-Cx4-PICKUP-STATOR": fp["Cx4_pickup"],
            "ND3-Cx3-PICKUP-STATOR": fp["Cx3_pickup"], "ND7-ISLAND-BARS-onB": fp["Cx3_bars"],
            "ND8-ISLAND-BARS-onA": fp["Cx4_bars"]}
    rows = []
    for lay, f in want.items():
        rmin, rmax, st = got[lay]
        ok = abs(rmin - f["r_in"]) < 0.05 and abs(rmax - f["r_out"]) < 0.05 and \
            sorted(round(s % 360.0, 2) for s in f["starts"]) == st
        rows.append(dict(layer=lay, dxf=[rmin, rmax, st], model=[f["r_in"], f["r_out"], sorted(f["starts"])], pass_=ok))
    # spark-gap stations: the placed stator electrodes sit at the DXF SG markers (mod 60) = the engine stations
    import pump_engine as PE
    sg_rows = []
    lay = {"SG1": "SG1-RETURN-GAP", "SG2": "SG2-RETURN-GAP", "SG3a1": "SG3a-LOAD-GAP", "SG3b1": "SG3b-FIRE-GAP",
           "SG4a1": "SG4a-LOAD-GAP", "SG4b1": "SG4b-FIRE-GAP", "BS3": "SG-BS3-BACKSTOP", "BS4": "SG-BS4-BACKSTOP"}
    for x in d["sparkgaps"]["gaps"]:
        angs = sorted({round(math.degrees(math.atan2(e.dxf.start.y, e.dxf.start.x)) % 60.0, 2)
                       for e in msp if e.dxf.layer == lay[x["name"]] and e.dxftype() == "LINE"})
        eng = PE.DXF[x["name"].replace("a1", "a").replace("b1", "b")]
        sg_rows.append(dict(gap=x["name"], placed=x["station"], dxf=angs, engine=eng,
                            pass_=angs == [round(x["station"] % 60.0, 2)] and abs(eng - x["station"]) < 1e-9))
    rows += sg_rows
    fwd = PG.solve_transfer(309.0, dict(PG.GEOM_DEFAULTS, ca_mode="forward"), 6)
    return dict(pass_=all(r["pass_"] for r in rows) and abs(fwd["C_pF"] - 309.0) < 0.5, rows=rows,
                seed_C_pF=fwd["C_pF"], seed_area_mm2=fwd["area_mm2"])


def gate_rt():
    lock = freeze_lock()
    rows = []
    for mode in ("outer", "r_out", "r_in", "width"):
        d = PG.build(lock, dict(ca_mode=mode))
        rows.append(dict(mode=mode, dC_rel=d["Ca"]["dC_rel"], r_in=d["Ca"]["r_in"], r_out=d["Ca"]["r_out"], w=d["Ca"]["w_deg"]))
    ok = all(abs(r["dC_rel"]) <= 1e-12 for r in rows)
    # a manufacturing rounding (r_out to 1 mm) -> realized C -> the exact engine with Ca/Cb pinned
    d = PG.build(lock, dict(ca_mode="r_out", ca_round=1.0))
    import pump_synth as SY
    lad, fi = SY.sized({"pins": {"Ca": d["Ca"]["C_pF"], "Cb": d["Cb"]["C_pF"]}})
    z, conv = SY.z_of(SY.engine_cfg(lad, fi), warm=False)
    return dict(pass_=bool(ok and conv), modes=rows, rounded=dict(r_out=d["Ca"]["r_out"], C_pF=d["Ca"]["C_pF"],
                dC_rel=d["Ca"]["dC_rel"], z=z, z_locked=lock["z"], dz=z - lock["z"]))


def gate_adj():
    d = PG.build(freeze_lock())
    a = PG.adjacency(d)
    return dict(pass_=all(v[0] for v in a.values()), rows={k: v[1] for k, v in a.items()},
                checks={k: v for k, v in d["checks"].items()})


def _caps(d):
    """every capacitor of the stack: its two footprints' (aligned) overlap across the one layer between them."""
    st = d["stack"]; pos = {it["id"]: i for i, it in enumerate(st)}
    out = {}
    for cap, (k1, k2) in PG.PAIRS.items():
        i1, i2 = sorted((pos[k1], pos[k2]))
        gap = st[i1 + 1]
        a, b = st[pos[k1]], st[pos[k2]]
        ov = max(PG.overlap_area(a, dict(b, starts=[x + dd for x in b["starts"]])) for dd in range(0, 61))
        if gap["medium"] in PG.DIELECTRICS:
            C = PG.cap_pF(ov, gap["t"], PG.DIELECTRICS[gap["medium"]])
        else:                                     # the Cx gap: air + mica per face in series
            g = d["geom"]
            t_eff = g["cx_air"] / PG.DIELECTRICS["air"] + 2 * g["cx_mica"] / PG.DIELECTRICS["mica"]
            C = PG.cap_pF(ov, t_eff, 1.0)
        out[cap] = C
    return out


def gate_z():
    """Z-stretch: the stretched freeze build passes every check; the same design at the base thicknesses shows the
    shortfall; the stretch changes no capacitance (it only thickens carriers between a node's own foils)."""
    lock = freeze_lock()
    dz, d0 = PG.build(lock), PG.build(lock, dict(zs_mode="fixed"))
    cz, c0 = _caps(dz), _caps(d0)
    same_C = all(abs(cz[k] - c0[k]) <= 1e-12 * c0[k] for k in cz)
    same_fp = dz["footprints"] == d0["footprints"]
    allpass = all(v["pass_"] for v in dz["checks"].values())
    k = "gaps: Z-stretch: every carrier holds its gap seats and leads"
    links = sum(1 for p in dz["parts"] if p["role"] == "link")
    return dict(pass_=bool(same_C and same_fp and allpass and not d0["checks"][k]["pass_"] and links == 12),
                caps_pF={c: round(v, 4) for c, v in cz.items()}, same_C=same_C, same_footprints=same_fp,
                stretched=dz["checks"][k]["detail"], base=d0["checks"][k]["detail"],
                z_total=dict(stretched=dz["z_total"], base=d0["z_total"]), checks_pass=allpass,
                failing_at_base=[c for c, v in d0["checks"].items() if not v["pass_"]], links=links,
                thickness={c: v["t"] for c, v in dz["zstretch"].items()})


def gate_sgr():
    """RADIAL BAR BAND (TMD 2026-10-02), read from the reference build's bill of solids, not its gap records: per side
    the fire and backstop spheres sit on radial (horizontal) stems out of the trimmed ND2 / ND3 rim and meet the tip
    VERTICALLY, the load sphere sits on a radial arm in from the stator frame and meets it HORIZONTALLY, the tip hangs
    on a vertical stem -- three of the four spheres on horizontal stems; every spacing at alignment measured between
    the solids is the freeze table's; ND2 / ND3 end inside the tip path; every check passes; the axial layout (rev 5-7)
    still builds clean."""
    lock = freeze_lock()
    d, dax = PG.build(lock), PG.build(lock, dict(sg_layout="axial"))
    P = {p["name"]: p for p in d["parts"]}

    def ang(p):
        return math.degrees(math.atan2(p[1], p[0]))
    rows, per_side = [], {}
    for x in d["sparkgaps"]["gaps"]:
        if x["band"] != "bar":
            continue
        s, st = P[f"{x['name']}_sph_1"], P[f"{x['name']}_stem_1"]
        tip, ts = P[f"bartip_{x['side']}_1"], P[f"bartip_{x['side']}_stem_1"]
        # the tip turned to this station (rotate its centre by the station angle)
        a = math.radians(x["station"])
        tc = [tip["c"][0] * math.cos(a) - tip["c"][1] * math.sin(a), tip["c"][0] * math.sin(a) + tip["c"][1] * math.cos(a), tip["c"][2]]
        dr, dz = math.hypot(s["c"][0], s["c"][1]) - math.hypot(tc[0], tc[1]), s["c"][2] - tc[2]
        gap = math.dist(s["c"], tc) - s["r"] - tip["r"]
        axis = "horizontal" if abs(dz) < 1e-9 else ("vertical" if abs(dr) < 1e-9 else "oblique")
        stem_h = abs(st["p0"][2] - st["p1"][2]) < 1e-9 and abs(ang(st["p0"]) - ang(st["p1"])) < 1e-9
        tip_v = math.hypot(ts["p0"][0] - ts["p1"][0], ts["p0"][1] - ts["p1"][1]) < 1e-9
        want = "horizontal" if x["cls"] == "load" else "vertical"
        ok = axis == want and stem_h and tip_v and abs(gap - x["spacing"]) < 1e-9
        per_side[x["side"]] = per_side.get(x["side"], 0) + (1 if stem_h else 0)
        rows.append(dict(gap=x["name"], cls=x["cls"], axis=axis, spacing_mm=gap, stem="radial" if stem_h else "other",
                         sphere_r=math.hypot(s["c"][0], s["c"][1]), mount=x["mount"], pass_=ok))
    bands = d["sparkgaps"]["bands"]
    rims = {it["id"]: it["r_out"] for it in d["stack"] if it["id"] in ("ND2", "ND3")}
    rim_ok = all(rims[b["stator_carrier"]] < d["r_edge"] - 1e-9 and rims[b["stator_carrier"]] <= b["r"] - d["geom"]["sg_d"] / 2
                 - d["geom"]["sg_clear"] + 1e-9 for b in bands.values() if b["band"] == "bar")
    allpass = all(v["pass_"] for v in d["checks"].values())
    ax_ok = all(v["pass_"] for v in dax["checks"].values())
    return dict(pass_=bool(all(r["pass_"] for r in rows) and per_side == {"A": 3, "B": 3} and rim_ok and allpass and ax_ok),
                rows=rows, horizontal_stems_per_side=per_side, rims=rims, tip_r={k: v["r"] for k, v in bands.items() if v["band"] == "bar"},
                checks_pass=allpass, axial_checks_pass=ax_ok, z_total=dict(radial=d["z_total"], axial=dax["z_total"]),
                solids=dict(radial=len(d["parts"]), axial=len(dax["parts"])))


def _rand_geom(rng):
    return dict(ca_diel=rng.choice(list(PG.DIELECTRICS)), ca_t=rng.uniform(0.5, 8), ca_w=rng.uniform(10, 30),
                ca_mode=rng.choice(["outer", "r_out", "r_in", "width", "forward"]), ca_rin=rng.uniform(60, 150),
                ca_rout=rng.uniform(160, 300), ca_round=rng.choice([0, 0, 0.5, 1.0]), ca_margin=rng.uniform(0, 10),
                t_foil=rng.uniform(0.2, 2), t_carrier=rng.uniform(1, 6), t_rotor=rng.uniform(5, 20),
                t_flange=rng.uniform(3, 10), t_septum=rng.uniform(6, 20), r_bore=rng.uniform(30, 55),
                sg_rbar=rng.uniform(300, 420), sg_rrail=rng.uniform(395, 460), sg_d=rng.uniform(6, 20), sg_dbs=rng.uniform(15, 35),
                sg_s_ret=rng.uniform(3, 8), sg_s_load=rng.uniform(3, 8), sg_s_fire=rng.uniform(3, 8), sg_s_bs=rng.uniform(3, 8),
                sg_expose=rng.uniform(0.2, 1.2), sg_stem=rng.uniform(2, 6), sg_rod=rng.uniform(2, 6),
                sg_seat=rng.uniform(1, 6), sg_cover=rng.uniform(0.5, 4), sg_chord=rng.uniform(5, 40),
                zs_mode=rng.choice(["auto", "auto", "fixed"]), sg_frame=rng.uniform(20, 120), sg_khv=rng.uniform(1, 3),
                sg_layout=rng.choice(["radial", "radial", "axial"]), sg_rimgap=rng.uniform(0, 10), sg_clear=rng.uniform(0.5, 6),
                sg_stem_air=rng.uniform(0, 8))


def gate_js(n=60):
    rng = random.Random(20261001)
    cases = []
    for _ in range(n):
        plates = dict(r_outMm=rng.uniform(250, 500), g_vMm=rng.uniform(3, 12))
        lock = PG.lock_record(PS.size(plates), {}, 1.3, True)
        cases.append((lock, _rand_geom(rng)))
    js = subprocess.run(["node", "-e", "const G=require('./tools/pump-geometry.js');"
                         "const cs=JSON.parse(require('fs').readFileSync(0,'utf8'));"
                         "console.log(JSON.stringify(cs.map(([l,g])=>G.build(l,g))))"],
                        cwd=ROOT, input=json.dumps(cases), capture_output=True, text=True)
    if js.returncode:
        return dict(pass_=False, error=js.stderr[-800:])
    J = json.loads(js.stdout)
    worst = [0.0]; mism = []

    def cmp(a, b, path):
        if isinstance(a, dict):
            if set(a) != set(b):
                mism.append(path + " keys " + str(sorted(set(a) ^ set(b)))); return
            for k in a:
                cmp(a[k], b[k], path + "." + k)
        elif isinstance(a, list):
            if len(a) != len(b):
                mism.append(path + " len"); return
            for i, (x, y) in enumerate(zip(a, b)):
                cmp(x, y, f"{path}[{i}]")
        elif isinstance(a, bool) or a is None or isinstance(a, str):
            if a != b:
                mism.append(f"{path}: {a!r} != {b!r}")
        else:
            worst[0] = max(worst[0], abs(a - b) / max(1.0, abs(a)))
    for (lock, g), o in zip(cases, J):
        cmp(PG.build(lock, g), o, "")
    return dict(pass_=bool(worst[0] <= 1e-12 and not mism), n=n, worst_rel=worst[0], mismatches=mism[:6])


# ---- an OpenCascade stand-in for FreeCAD / Part (just the calls the macro makes) ----------------------
def _install_occ_freecad():
    from OCP.BRepPrimAPI import BRepPrimAPI_MakeCylinder
    from OCP.BRepAlgoAPI import BRepAlgoAPI_Cut, BRepAlgoAPI_Common
    from OCP.BRepBuilderAPI import BRepBuilderAPI_Transform
    from OCP.gp import gp_Ax2, gp_Pnt, gp_Dir, gp_Trsf, gp_Ax1
    from OCP.GProp import GProp_GProps
    from OCP.BRepGProp import BRepGProp
    from OCP.BRepCheck import BRepCheck_Analyzer
    from OCP.STEPControl import STEPControl_Writer, STEPControl_AsIs
    from OCP.Bnd import Bnd_Box
    from OCP.BRepBndLib import BRepBndLib

    class Vector:
        def __init__(self, x=0, y=0, z=0):
            self.x, self.y, self.z = float(x), float(y), float(z)

        def __sub__(self, o):
            return Vector(self.x - o.x, self.y - o.y, self.z - o.z)

        @property
        def Length(self):
            return math.sqrt(self.x ** 2 + self.y ** 2 + self.z ** 2)

    class Shape:
        def __init__(self, s):
            self.s = s

        def cut(self, other):
            return Shape(BRepAlgoAPI_Cut(self.s, other.s).Shape())

        def common(self, other):
            return Shape(BRepAlgoAPI_Common(self.s, other.s).Shape())

        def rotate(self, base, axis, deg):
            t = gp_Trsf(); t.SetRotation(gp_Ax1(gp_Pnt(base.x, base.y, base.z), gp_Dir(axis.x, axis.y, axis.z)), math.radians(deg))
            self.s = BRepBuilderAPI_Transform(self.s, t, True).Shape()
            return self

        @property
        def Volume(self):
            p = GProp_GProps(); BRepGProp.VolumeProperties_s(self.s, p); return p.Mass()

        def isValid(self):
            return BRepCheck_Analyzer(self.s).IsValid()

        def bbox(self):
            b = Bnd_Box(); BRepBndLib.Add_s(self.s, b); return b

    def makeCylinder(r, h, pnt=None, d=None, angle=360.0):
        pnt = pnt or Vector(); d = d or Vector(0, 0, 1)
        ax = gp_Ax2(gp_Pnt(pnt.x, pnt.y, pnt.z), gp_Dir(d.x, d.y, d.z))
        mk = BRepPrimAPI_MakeCylinder(ax, r, h) if angle >= 360.0 else BRepPrimAPI_MakeCylinder(ax, r, h, math.radians(angle))
        return Shape(mk.Shape())

    def makeSphere(r, c):
        from OCP.BRepPrimAPI import BRepPrimAPI_MakeSphere
        return Shape(BRepPrimAPI_MakeSphere(gp_Pnt(c.x, c.y, c.z), r).Shape())

    def export(objs, path):
        w = STEPControl_Writer()
        for o in objs:
            w.Transfer(o.Shape.s, STEPControl_AsIs)
        w.Write(path)

    def import_export(objs, path):
        """FreeCAD's Import.export (OCAF): App::Part -> named assembly, Part::Feature -> named, coloured part."""
        from OCP.TDocStd import TDocStd_Document
        from OCP.TCollection import TCollection_ExtendedString
        from OCP.XCAFDoc import XCAFDoc_DocumentTool, XCAFDoc_ColorType
        from OCP.TDataStd import TDataStd_Name
        from OCP.STEPCAFControl import STEPCAFControl_Writer
        from OCP.Quantity import Quantity_Color, Quantity_TypeOfColor
        from OCP.TopLoc import TopLoc_Location
        from OCP.Interface import Interface_Static
        doc = TDocStd_Document(TCollection_ExtendedString("XmlOcaf"))
        stl = XCAFDoc_DocumentTool.ShapeTool_s(doc.Main())
        col = XCAFDoc_DocumentTool.ColorTool_s(doc.Main())
        name = lambda lab, t: TDataStd_Name.Set_s(lab, TCollection_ExtendedString(t))

        def add(o, parent):
            if o.TypeId == "App::Part":
                lab = stl.NewShape(); name(lab, o.Label)
                for ch in o.Group:
                    add(ch, lab)
            else:
                lab = stl.AddShape(o.Shape.s, False); name(lab, o.Label)
                if getattr(o, "Colour", None):
                    r, g, b = o.Colour
                    col.SetColor(lab, Quantity_Color(r, g, b, Quantity_TypeOfColor.Quantity_TOC_RGB), XCAFDoc_ColorType.XCAFDoc_ColorSurf)
            if parent is not None:
                comp = stl.AddComponent(parent, lab, TopLoc_Location()); name(comp, o.Label)
            return lab
        for o in objs:
            add(o, None)
        stl.UpdateAssemblies()
        Interface_Static.SetCVal_s("write.step.product.name", "PumpGeometry")
        w = STEPCAFControl_Writer(); w.SetNameMode(True); w.SetColorMode(True)
        w.Transfer(doc, STEPControl_AsIs); w.Write(path)

    class Obj:
        def __init__(self, type_id, name):
            self.TypeId, self.Name, self.Label, self.Shape, self.Group, self.Colour = type_id, name, name, None, [], None

        def addObject(self, o):
            for other in getattr(o, "_parents", []):        # an object lives in one container (FreeCAD rule)
                other.Group.remove(o)
            o._parents = [self]
            self.Group.append(o)

    class Doc:
        def __init__(self, name):
            self.Name, self.Label, self.Objects, self.saved = name, name, [], None

        def addObject(self, type_id, name):
            base, k = name, 1
            while any(o.Name == name for o in self.Objects):
                k += 1; name = f"{base}{k:03d}"
            o = Obj(type_id, name); self.Objects.append(o); return o

        def recompute(self):
            pass

        def saveAs(self, p):
            self.saved = p                        # (no .FCStd writer outside FreeCAD)

    fc = types.ModuleType("FreeCAD")
    fc.Vector, fc.GuiUp = Vector, False
    fc.DOCS = []
    fc.newDocument = lambda n: (fc.DOCS.append(Doc(n)) or fc.DOCS[-1])
    fc.Console = types.SimpleNamespace(PrintMessage=lambda m: None)
    part = types.ModuleType("Part")
    part.makeCylinder, part.export, part.makeSphere = makeCylinder, export, makeSphere
    imp = types.ModuleType("Import")
    imp.export = import_export
    sys.modules["FreeCAD"], sys.modules["Part"], sys.modules["Import"] = fc, part, imp
    return fc


def gate_cad():
    os.makedirs(OUTDIR, exist_ok=True)
    d = PG.build(freeze_lock())
    jpath = os.path.join(OUTDIR, "freeze-v010-CaCb.json")
    open(jpath, "w").write(json.dumps(d, indent=1) + "\n")
    fc = _install_occ_freecad()
    os.environ["PUMP_GEOMETRY_JSON"] = jpath
    src = open(os.path.join(ROOT, "tools", "pump-geometry.FCMacro"), encoding="utf8").read()
    ns = {"__name__": "__macro__"}
    exec(compile(src, "pump-geometry.FCMacro", "exec"), ns)
    made = ns["RESULT"]
    doc = fc.DOCS[-1]
    objs = [o for o in doc.Objects if o.TypeId == "Part::Feature"]
    vol_err = max(abs(m["volume"] - m["expect"]) / m["expect"] for m in made)
    invalid = [o.Name for o in objs if not o.Shape.isValid()]
    # interference: no two solids share volume (foils touch their carriers, they must not cut into them)
    clash = []
    CH = {m["name"]: m.get("chains", []) for m in made}
    boxes = [(o, o.Shape.bbox()) for o in objs]
    for i in range(len(boxes)):
        for j in range(i + 1, len(boxes)):
            (a, ba), (b, bb) = boxes[i], boxes[j]
            if ba.IsOut(bb):
                continue
            if set(CH.get(a.Name, ())) & set(CH.get(b.Name, ())):
                continue                                  # joined on purpose (a lead into its post, an arm through its rotor)
            v = a.Shape.common(b.Shape).Volume
            if v > 1e-6 * min(a.Shape.Volume, b.Shape.Volume):
                clash.append((a.Name, b.Name, v))
    step = os.path.splitext(jpath)[0] + ".step"
    import re
    txt = open(step, encoding="latin-1").read().replace("\r", "").replace("\n", "")   # line breaks are not significant in STEP
    products = [m.replace("''", "'") for m in re.findall(r"=\s*PRODUCT\(\s*'((?:[^']|'')*)'", txt)]   # STEP doubles a quote
    anon = [p for p in products if "Open CASCADE" in p]
    labels = {o.Label for o in objs}
    missing = sorted(labels - set(products))
    asm = [g.Label for g in doc.Objects if g.TypeId == "App::Part"]
    csvp = os.path.splitext(jpath)[0] + "-parts.csv"
    rows = sum(1 for _ in open(csvp)) - 1
    names_ok = not anon and not missing and rows == len(objs) and all(a in products for a in asm)
    roles = {}
    for m in made:
        roles[m["role"]] = roles.get(m["role"], 0) + 1
    return dict(pass_=bool(vol_err <= 1e-6 and not invalid and not clash and os.path.getsize(step) > 0 and names_ok),
                names=dict(products=len(products), anonymous=len(anon), labels_missing=missing[:5], assemblies=asm,
                           parts_csv=os.path.relpath(csvp, ROOT), csv_rows=rows, sample=sorted(labels)[:3]),
                solids=len(objs), roles=roles, worst_volume_rel=vol_err, invalid=invalid, clashes=clash[:10],
                json=os.path.relpath(jpath, ROOT), step=os.path.relpath(step, ROOT), step_bytes=os.path.getsize(step),
                lock=d["lock"]["hash"], z_total_mm=d["z_total"])


# ---- an OpenCascade stand-in for Fusion 360's adsk.core / adsk.fusion (the calls PumpGeometry.py makes) ----
def _install_occ_adsk(json_path):
    from OCP.BRepPrimAPI import BRepPrimAPI_MakeCylinder, BRepPrimAPI_MakeBox
    from OCP.BRepAlgoAPI import BRepAlgoAPI_Cut, BRepAlgoAPI_Common
    from OCP.gp import gp_Ax2, gp_Pnt, gp_Dir
    from OCP.GProp import GProp_GProps
    from OCP.BRepGProp import BRepGProp
    from OCP.BRepCheck import BRepCheck_Analyzer

    class Point3D:
        def __init__(self, x, y, z): self.x, self.y, self.z = x, y, z
        create = staticmethod(lambda x=0, y=0, z=0: Point3D(x, y, z))

    class Vector3D(Point3D):
        create = staticmethod(lambda x=0, y=0, z=0: Vector3D(x, y, z))

    class OBB:
        def __init__(self, c, u, w, L, W, H): self.c, self.u, self.w, self.L, self.W, self.H = c, u, w, L, W, H

    class Body:
        def __init__(self, s): self.s, self.name = s, ""

        @property
        def volume(self):
            p = GProp_GProps(); BRepGProp.VolumeProperties_s(self.s, p); return p.Mass()

    class TBM:
        def createCylinderOrCone(self, p0, r0, p1, r1):
            assert abs(r0 - r1) < 1e-12
            d = (p1.x - p0.x, p1.y - p0.y, p1.z - p0.z); L = math.sqrt(sum(c * c for c in d))
            return Body(BRepPrimAPI_MakeCylinder(gp_Ax2(gp_Pnt(p0.x, p0.y, p0.z), gp_Dir(*d)), r0, L).Shape())

        def createSphere(self, c, r):
            from OCP.BRepPrimAPI import BRepPrimAPI_MakeSphere
            return Body(BRepPrimAPI_MakeSphere(gp_Pnt(c.x, c.y, c.z), r).Shape())

        def createBox(self, b):
            # corner = centre - L/2 u - W/2 w - H/2 n, frame (u, w, n = u x w)
            n = (b.u.y * b.w.z - b.u.z * b.w.y, b.u.z * b.w.x - b.u.x * b.w.z, b.u.x * b.w.y - b.u.y * b.w.x)
            cx = b.c.x - b.L / 2 * b.u.x - b.W / 2 * b.w.x - b.H / 2 * n[0]
            cy = b.c.y - b.L / 2 * b.u.y - b.W / 2 * b.w.y - b.H / 2 * n[1]
            cz = b.c.z - b.L / 2 * b.u.z - b.W / 2 * b.w.z - b.H / 2 * n[2]
            ax = gp_Ax2(gp_Pnt(cx, cy, cz), gp_Dir(*n), gp_Dir(b.u.x, b.u.y, b.u.z))
            return Body(BRepPrimAPI_MakeBox(ax, b.L, b.W, b.H).Shape())

        def booleanOperation(self, target, tool, kind):
            op = BRepAlgoAPI_Cut if kind == "diff" else BRepAlgoAPI_Common
            target.s = op(target.s, tool.s).Shape()
            return True

    class Bodies:
        def __init__(self): self.items = []

        def add(self, body, bf=None):
            assert (bf is not None) == PARAMETRIC[0], "parametric designs need a base feature"
            assert bf is None or bf.editing, "bodies are added inside startEdit/finishEdit"
            b = Body(body.s); self.items.append(b); return b

    class BaseFeature:
        def __init__(self): self.editing = False
        def startEdit(self): self.editing = True
        def finishEdit(self): self.editing = False

    class Component:
        def __init__(self):
            self.name, self.bRepBodies, self.occurrences = "", Bodies(), Occurrences()
            self.features = types.SimpleNamespace(baseFeatures=types.SimpleNamespace(add=lambda: BaseFeature()))

    class Occurrences:
        def __init__(self): self.items = []
        def addNewComponent(self, m):
            o = types.SimpleNamespace(component=Component()); self.items.append(o); return o

    PARAMETRIC = [True]
    root = Component()
    design = types.SimpleNamespace(rootComponent=root, designType="parametric", appearances=None)
    msgs = []
    ui = types.SimpleNamespace(messageBox=lambda m: msgs.append(m), createFileDialog=lambda: None)
    app = types.SimpleNamespace(userInterface=ui, activeProduct=design,
                                documents=types.SimpleNamespace(add=lambda t: None),
                                materialLibraries=types.SimpleNamespace(itemByName=lambda n: None))
    core = types.ModuleType("adsk.core")
    core.Point3D, core.Vector3D, core.Matrix3D = Point3D, Vector3D, types.SimpleNamespace(create=lambda: None)
    core.OrientedBoundingBox3D = types.SimpleNamespace(create=lambda c, u, w, L, W, H: OBB(c, u, w, L, W, H))
    core.Application = types.SimpleNamespace(get=lambda: app)
    core.DialogResults = types.SimpleNamespace(DialogOK=1)
    core.DocumentTypes = types.SimpleNamespace(FusionDesignDocumentType=0)
    core.ColorProperty = types.SimpleNamespace(cast=lambda x: None)
    core.Color = types.SimpleNamespace(create=lambda *a: a)
    fus = types.ModuleType("adsk.fusion")
    fus.TemporaryBRepManager = types.SimpleNamespace(get=lambda: TBM())
    fus.BooleanTypes = types.SimpleNamespace(DifferenceBooleanType="diff", IntersectionBooleanType="inter")
    fus.DesignTypes = types.SimpleNamespace(ParametricDesignType="parametric")
    fus.Design = types.SimpleNamespace(cast=lambda p: p)
    adsk = types.ModuleType("adsk"); adsk.core, adsk.fusion = core, fus; adsk.doEvents = lambda: None
    sys.modules.update({"adsk": adsk, "adsk.core": core, "adsk.fusion": fus})
    os.environ["PUMP_GEOMETRY_JSON"] = json_path
    return root, msgs, BRepCheck_Analyzer


def gate_f360():
    d = PG.build(freeze_lock())
    jpath = os.path.join(OUTDIR, "freeze-v010-CaCb.json")
    open(jpath, "w").write(json.dumps(d, indent=1) + "\n")
    root, msgs, Analyzer = _install_occ_adsk(jpath)
    src = open(os.path.join(ROOT, "tools", "fusion360", "PumpGeometry", "PumpGeometry.py"), encoding="utf8").read()
    ns = {"__name__": "PumpGeometry"}
    exec(compile(src, "PumpGeometry.py", "exec"), ns)
    ns["run"]({})
    made = ns.get("RESULT") or []
    if not made:
        return dict(pass_=False, error=" | ".join(msgs)[-800:])
    top = root.occurrences.items[0].component
    subs = [o.component for o in top.occurrences.items]
    bodies = [b for c in subs for b in c.bRepBodies.items]
    bad = '/\\:*?"<>|'
    clean = lambda t: "".join("-" if ch in bad else ch for ch in t)
    names_ok = (top.name == clean(d["top_label"]) and [c.name for c in subs] == [clean(a["label"]) for a in d["assemblies"]]
                and sorted(b.name for b in bodies) == sorted(clean(p["label"]) for p in d["parts"]))
    vol = max(abs(m["volume"] - m["expect"]) / m["expect"] for m in made)
    invalid = [b.name for b in bodies if not Analyzer(b.s).IsValid()]
    return dict(pass_=bool(len(bodies) == len(d["parts"]) and vol <= 1e-6 and not invalid and names_ok),
                bodies=len(bodies), components=len(subs) + 1, worst_volume_rel=vol, invalid=invalid[:5],
                names_ok=names_ok, top=top.name, sample=bodies[3].name if len(bodies) > 3 else None,
                message=msgs[-1][:200] if msgs else "")


def _ci_cmp(a, b, path, out, worst):
    if isinstance(a, dict):
        if set(a) != set(b):
            out.append(f"{path} keys {sorted(set(a) ^ set(b))}"); return
        for k in a:
            _ci_cmp(a[k], b[k], path + "." + k, out, worst)
    elif isinstance(a, list):
        if len(a) != len(b):
            out.append(f"{path} len {len(a)} != {len(b)}"); return
        for i, (x, y) in enumerate(zip(a, b)):
            _ci_cmp(x, y, f"{path}[{i}]", out, worst)
    elif isinstance(a, bool) or a is None or isinstance(a, str):
        if a != b:
            out.append(f"{path}: {a!r} != {b!r}")
    else:
        worst[0] = max(worst[0], abs(a - b) / max(1.0, abs(a)))


def _ci_summary(r):
    return dict(verdict=r["verdict"], nets=sorted((n["node"], n["parts"]) for n in r["nets"]),
                caps=[(c["name"], c.get("relation"), round(c.get("C_max_pF", 0.0), 3), round(c.get("C_min_pF", 0.0), 3)) for c in r["capacitors"]],
                gaps=[(g["name"], g["spheres"], round(g["s_min"], 4)) for g in r["gaps"]],
                strays=sorted((tuple(x["nodes"]), x["relation"], round(x["C_max_pF"], 2), round(x["C_min_pF"], 2)) for x in r["strays"]))


def gate_ci():
    """CIRCUIT INTEGRITY (sim/circuit_integrity.py): the reference build IS the netlist of record -- one net per node,
    every netlist capacitor and gap realized on its nodes, every name and CAD group on the node of its copper -- read
    from its JSON and again from its STEP (B-rep recognition, independent of the generator); the JS tool reports
    exactly what the Python does; and every seeded fault is caught by the rule meant for it."""
    import copy
    import circuit_integrity as CI
    nl = CI.load_netlist()
    d = PG.build(freeze_lock())
    rep = CI.analyze(CI.parts_from_design(d), nl, "reference JSON")
    ref_ok = (rep["verdict"] == "PASS" and len(rep["nets"]) == 12 and all(c["realized"] for c in rep["capacitors"])
              and len(rep["gaps"]) == 8 and rep["counts"]["FAIL"] == 0)
    step = os.path.join(OUTDIR, "freeze-v010-CaCb.step")
    try:
        srep = CI.analyze(CI.parts_from_step(step), nl, "reference STEP")
        step_ok, step_note = _ci_summary(srep) == _ci_summary(rep), f"{srep['parts']} solids re-read"
    except Exception as e:                                       # pragma: no cover
        step_ok, step_note = False, repr(e)[:300]
    # the JS mirror: the reference and randomized designs
    rng = random.Random(20261002)
    designs = [d] + [PG.build(PG.lock_record(PS.size(dict(r_outMm=rng.uniform(250, 500), g_vMm=rng.uniform(3, 12))), {}, 1.3, True),
                              _rand_geom(rng)) for _ in range(8)]
    js = subprocess.run(["node", "-e", "const CI=require('./tools/circuit-integrity.js');const fs=require('fs');"
                         "const nl=CI.parse_netlist(fs.readFileSync('topology_edge_list.csv','utf8'));"
                         "const ds=JSON.parse(fs.readFileSync(0,'utf8'));"
                         "console.log(JSON.stringify({r: ds.map(x=>CI.analyze(CI.parts_from_design(x),nl,'x')), st: CI.selftest()}))"],
                        cwd=ROOT, input=json.dumps(designs), capture_output=True, text=True)
    if js.returncode:
        return dict(pass_=False, error=js.stderr[-800:])
    J = json.loads(js.stdout)
    mism, worst = [], [0.0]
    for x, y in zip([CI.analyze(CI.parts_from_design(z), nl, "x") for z in designs], J["r"]):
        _ci_cmp(x, y, "", mism, worst)
    js_ok = not mism and worst[0] <= 1e-9 and J["st"]["pass"]

    # seeded faults, each must be caught by its rule
    def fault(fn):
        dd = copy.deepcopy(d)
        fn(dd)
        r = CI.analyze(CI.parts_from_design(dd), nl, "fault")
        return {f["rule"] for f in r["findings"] if f["level"] == "FAIL"}

    def by(dd, name):
        return next(p for p in dd["parts"] if p["name"] == name)

    def rod(name, node, body, p0, p1, carrier="ND2"):
        return dict(name=name, label=f"node-{node} / {name} - injected lead, node {node} [Cu lead, {body}]", assembly=f"node-{node}",
                    role="gap-lead", carrier=carrier, node=node, cap="", material="Cu lead", body=body, shape="rod",
                    p0=p0, p1=p1, r=1.5, chains=[name], rgb=[1, 1, 1], volume=1.0)

    def f_group(dd):        # the reported case: a node-2 sphere grouped under the node-1 carrier
        by(dd, "SG1_sph_6")["assembly"] = "ND1"
        dd["assemblies"].append(dict(key="ND1", label="ND1 - stator carrier ND1 (node 1): C1 stator plate + Ca counter-electrode"))

    def f_short(dd):        # a lead from a node-2 sphere to a node-4 sphere
        dd["parts"].append(rod("bad_lead", "2", "stator", by(dd, "SG4b1_sph_1")["c"], by(dd, "SG4a1_sph_1")["c"]))

    def f_open(dd):         # a C_R plate sector loses its bus riser
        dd["parts"] = [p for p in dd["parts"] if p["name"] != "bus_A_disc_n18_riser_1"]

    def f_gap(dd):          # a rotor tip drawn on node 1
        by(dd, "rotortip_A_1")["node"] = "1"

    def f_tie(dd):          # the rev-3 assumption: the C_R plate on R-A
        for p in dd["parts"]:
            if p["name"].startswith("CR_A_") or p["name"].startswith("bus_A_disc_n18"):
                p["node"] = "R-A"

    def f_joint(dd):        # stator copper touching a rotor foil
        c = by(dd, "C1_rotor_1")
        a = 0.5 * (c["start_deg"] * 2 + c["w_deg"]) * math.pi / 180
        r = 0.5 * (c["r_in"] + c["r_out"])
        dd["parts"].append(rod("bad_joint", "R-A", "stator", [r * math.cos(a), r * math.sin(a), 0.5 * (c["z0"] + c["z1"])],
                               [r * math.cos(a), r * math.sin(a), c["z0"] - 5.0], "ND1"))
    want = dict(group={"I8"}, short={"I1"}, open={"I2"}, gap={"I1", "I7"}, tie={"I2", "I6", "I8"}, joint={"I4"})
    got = {k: fault(fn) for k, fn in (("group", f_group), ("short", f_short), ("open", f_open), ("gap", f_gap), ("tie", f_tie), ("joint", f_joint))}
    faults_ok = all(want[k] <= got[k] for k in want)
    return dict(pass_=bool(ref_ok and step_ok and js_ok and faults_ok), reference=_ci_summary(rep), counts=rep["counts"],
                warnings=[f["text"] for f in rep["findings"] if f["level"] == "WARN"], step=step_ok, step_note=step_note,
                js=dict(ok=js_ok, designs=len(designs), worst_rel=worst[0], mismatches=mism[:6], selftest=J["st"]),
                faults={k: dict(want=sorted(want[k]), caught=sorted(got[k])) for k in want})


GATES = [("G-SEED", gate_seed), ("G-ADJ", gate_adj), ("G-Z", gate_z), ("G-SGR", gate_sgr), ("G-JS", gate_js), ("G-CAD", gate_cad),
         ("G-F360", gate_f360), ("G-CI", gate_ci), ("G-RT", gate_rt)]


def main():
    only = None
    if "--only" in sys.argv:
        only = set(sys.argv[sys.argv.index("--only") + 1].split(","))
    path = os.path.join(HERE, "pump_geometry_gates.json")
    if os.path.exists(path):
        OUT.update(json.load(open(path)))
    for name, fn in GATES:
        if only and name not in only:
            continue
        try:
            r = fn()
        except Exception as e:
            import traceback
            r = dict(pass_=False, error=f"{type(e).__name__}: {e}", tb=traceback.format_exc()[-1200:])
        OUT[name] = r
        print(f"[{name}] {'PASS' if r.get('pass_') else 'FAIL'}", {k: v for k, v in r.items() if k in
              ("error", "worst_rel", "worst_volume_rel", "solids", "roles", "clashes", "rounded", "seed_C_pF", "mismatches", "names", "names_ok", "bodies", "components", "sample")})
        open(path, "w").write(json.dumps(OUT, indent=1, default=str) + "\n")
    OUT["verdict"] = "GEOMETRY-STAGE2-PASS" if all((OUT.get(n) or {}).get("pass_") for n, _ in GATES) else "GEOMETRY-STAGE2-PARTIAL"
    open(path, "w").write(json.dumps(OUT, indent=1, default=str) + "\n")
    print("VERDICT", OUT["verdict"])


if __name__ == "__main__":
    main()
