#!/usr/bin/env python3
"""sim/tube_geometry.py -- the TUBE machine as solids (OpenCascade): STEP output, checks, renders.

Source of truth: sim/stack_sizing.layout() (the same element list that sets the calculator's length and draws its
section). Every element becomes solids here:
  * C1 / C2 / Cx vanes: 6 sectors fused to a ring (stator: outer ring r_out..r_out+12 to the cage; rotor: inner ring
    from the rotor sleeve to r_in). Stator sectors 30 deg and rotor vanes 22 deg, both centred on 0 + 60k (rotor angle 0
    = aligned) [IR];
  * Ca / Cb fixed plates: full annuli, stator, two nodes alternating (their connections are not drawn) [IR];
  * clocking: per station a rotor disc with 6 tip spheres (0 + 60k) and a stator ring with 6 spheres at the station
    angle (+ 60k), spheres half-embedded, gap and sphere sizes from the CAD build;
  * reluctance: the designer's squared C-EM pieces (core, 2 spool halves, coil; sim/motor_geometry src) x 6 per side
    and the utron (core, 2 open coil halves) x 3 per side on a rotor hub, placed at the utron radius;
  * shaft (rotor), rotor sleeve, insulating stator cage per side, hub placeholder (vacuum sphere + bicone shell).
Repeated parts are stored once in the STEP and instanced.
Checks: G-TUBE-CLASH (no two solids share volume, except the intended joins), G-TUBE-SWEEP (no stator solid in the
volume a rotor solid sweeps; the utron ring against the C-EM pieces exactly), G-TUBE-GAP (tip to sphere at
alignment = the set gap), G-TUBE-REL (C-EM to C-EM, utron to sleeve), the envelope diameters.
Usage: python3 sim/tube_geometry.py [--n-plates 8] [--r-out 150] [--no-step]
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
import stack_sizing as S                                 # noqa: E402
import motor_geometry as MG                              # noqa: E402

OUT_DIR = os.path.join(ROOT, "docs", "geometry", "tube")
SRC = os.path.join(ROOT, "docs", "geometry", "motor", "src")
RESULTS = os.path.join(HERE, "tube_geometry_results.json")
COL = {"stator vane": (0.78, 0.57, 0.92), "rotor vane": (0.49, 0.82, 1.0), "fixed plate": (0.27, 0.77, 0.42),
       "fixed plate 2": (0.18, 0.54, 0.29), "g10": (0.55, 0.6, 0.5), "sphere": (1.0, 0.71, 0.33), "tip": (0.9, 0.3, 0.3),
       "steel": (0.42, 0.45, 0.5), "glass": (0.75, 0.85, 0.9), "hub": (0.5, 0.52, 0.55)}


# ---------------------------------------------------------------------------------------------------------
# primitives
# ---------------------------------------------------------------------------------------------------------
def _ax(z0):
    from OCP.gp import gp_Ax2, gp_Pnt, gp_Dir
    return gp_Ax2(gp_Pnt(0, 0, z0), gp_Dir(0, 0, 1))


def sector(r0, r1, z0, z1, a0_deg=0.0, w_deg=360.0):
    from OCP.BRepPrimAPI import BRepPrimAPI_MakeCylinder
    from OCP.BRepAlgoAPI import BRepAlgoAPI_Cut
    h = z1 - z0
    full = w_deg >= 360.0 - 1e-9
    o = (BRepPrimAPI_MakeCylinder(_ax(z0), r1, h) if full else BRepPrimAPI_MakeCylinder(_ax(z0), r1, h, math.radians(w_deg))).Shape()
    if r0 > 1e-9:
        i = (BRepPrimAPI_MakeCylinder(_ax(z0), r0, h) if full else BRepPrimAPI_MakeCylinder(_ax(z0), r0, h, math.radians(w_deg))).Shape()
        o = BRepAlgoAPI_Cut(o, i).Shape()
    if not full and abs(a0_deg) > 1e-12:
        o = MG.moved(o, MG.trsf(0, 0, 0, a0_deg))
    return o


def sphere(r, c):
    from OCP.BRepPrimAPI import BRepPrimAPI_MakeSphere
    from OCP.gp import gp_Pnt
    return BRepPrimAPI_MakeSphere(gp_Pnt(*c), r).Shape()


def fuse(shapes):
    from OCP.BRepAlgoAPI import BRepAlgoAPI_Fuse
    from OCP.ShapeUpgrade import ShapeUpgrade_UnifySameDomain
    s = shapes[0]
    for t in shapes[1:]:
        s = BRepAlgoAPI_Fuse(s, t).Shape()
    u = ShapeUpgrade_UnifySameDomain(s, True, True, True); u.Build()
    return u.Shape()


def cone_shell(r_small, r_big, z0, z1, wall):
    from OCP.BRepPrimAPI import BRepPrimAPI_MakeCone
    from OCP.BRepAlgoAPI import BRepAlgoAPI_Cut
    from OCP.gp import gp_Ax2, gp_Pnt, gp_Dir
    up = z1 > z0
    ax = gp_Ax2(gp_Pnt(0, 0, min(z0, z1)), gp_Dir(0, 0, 1))
    h = abs(z1 - z0)
    ra, rb = (r_small, r_big) if up else (r_big, r_small)
    o = BRepPrimAPI_MakeCone(ax, ra, rb, h).Shape()
    i = BRepPrimAPI_MakeCone(ax, max(0.1, ra - wall), max(0.1, rb - wall), h).Shape()
    return BRepAlgoAPI_Cut(o, i).Shape()


def read_step(path):
    from OCP.STEPControl import STEPControl_Reader
    r = STEPControl_Reader(); r.ReadFile(path); r.TransferRoots()
    return r.OneShape()


# ---------------------------------------------------------------------------------------------------------
# the machine: prototypes + placements
# ---------------------------------------------------------------------------------------------------------
class Machine:
    def __init__(self, lad):
        self.lad = lad
        self.p = lad["tube"]
        self.el = lad["tube_geometry"]["elements"]
        self.protos = {}          # key -> (shape, colour, material)
        self.parts = []           # dict(name, label, proto, loc trsf args, body, node, join, group)

    def proto(self, key, make, colour, material):
        if key not in self.protos:
            self.protos[key] = (make(), colour, material)
        return key

    def add(self, name, proto, body, node, group, join=None, dz=0.0, rot=0.0, dx=0.0, desc=""):
        mat = self.protos[proto][2]
        self.parts.append(dict(name=name, proto=proto, body=body, node=node, group=group, join=join or name,
                               place=dict(dx=dx, dz=dz, rot=rot),
                               label=f"{group} / {name} - {desc} [{mat}, {body}]"))

    def build(self):
        p, el = self.p, self.el
        ri, ro, t = p["r_inMm"], p["r_outMm"], p["t_vaneMm"]
        hs, hw = 0.5 * p["ws_deg"], 0.5 * p["wr_deg"]
        per = 360.0 / (p["N_sec"] / 2.0)
        n_sec = int(p["N_sec"] / 2)
        stator_vane = lambda: fuse([sector(ri, ro, 0.0, t, k * per - hs, p["ws_deg"]) for k in range(n_sec)]
                                   + [sector(ro, ro + 12.0, 0.0, t)])
        rotor_vane = lambda: fuse([sector(ri, ro, 0.0, t, k * per - hw, p["wr_deg"]) for k in range(n_sec)]
                                  + [sector(S.SLEEVE_R, ri, 0.0, t)])
        self.proto("stator_vane", stator_vane, COL["stator vane"], "Al vane")
        self.proto("rotor_vane", rotor_vane, COL["rotor vane"], "Al vane")
        self.proto("fixed_plate", lambda: sector(ri, ro, 0.0, t), COL["fixed plate"], "Al plate")
        z_lo, z_hi = min(e["z0"] for e in el), max(e["z1"] for e in el)
        # shaft (rotor axle) and the rotor sleeve over the whole length
        self.proto("shaft", lambda: sector(0.0, S.SHAFT_R, z_lo, z_hi), COL["steel"], "steel shaft")
        self.proto("sleeve", lambda: sector(S.SHAFT_R, S.SLEEVE_R, z_lo + 5.0, z_hi - 5.0), COL["g10"], "G10 rotor sleeve")
        self.add("shaft", "shaft", "rotor", "", "rotor", join="rotor-core", desc="rotor axle")
        self.add("rotor_sleeve", "sleeve", "rotor", "", "rotor", join="rotor-core", desc="rotor sleeve, carries every rotor part")
        counts = {}
        for e in el:
            k = e["kind"]
            side = e["side"]
            counts[(k, side)] = counts.get((k, side), 0) + 1
            i = counts[(k, side)]
            if k.endswith("vane"):
                pr = "stator_vane" if e["body"] == "stator" else "rotor_vane"
                nm = f"{side}_{k.split()[0]}_{e['body'][0]}{i:02d}"
                self.add(nm, pr, e["body"], e["node"], f"side-{side}", join="rotor-core" if e["body"] == "rotor" else f"cage-{side}",
                         dz=e["z0"], desc=f"{k}, node {e['node']}")
            elif k.endswith("plate"):
                self.add(f"{side}_{k.split()[0]}_{i:02d}", "fixed_plate", "stator", e["node"], f"side-{side}",
                         dz=e["z0"], desc=f"{k}, node {e['node']} (connection not drawn)")
            elif k == "clk rotor disc":
                key = f"clk_rdisc_{e['r1']:.1f}"
                self.proto(key, lambda e=e: sector(e["r0"], e["r1"], 0.0, e["z1"] - e["z0"]), COL["g10"], "G10 rotor disc")
                self.add(f"{side}_{e['station']}_rotor_disc", key, "rotor", "", f"clock-{side}", join="rotor-core", dz=e["z0"],
                         desc=f"clocking rotor disc, {e['station']}")
            elif k == "clk stator ring":
                key = f"clk_sring_{e['r0']:.1f}"
                self.proto(key, lambda e=e: sector(e["r0"], e["r1"], 0.0, e["z1"] - e["z0"]), COL["g10"], "G10 stator ring")
                self.add(f"{side}_{e['station']}_stator_ring", key, "stator", "", f"clock-{side}", join=f"ring-{side}-{e['station']}",
                         dz=e["z0"], desc=f"clocking stator ring, {e['station']}")
            elif k in ("clk tip", "clk sphere"):
                key = f"{'tip' if k == 'clk tip' else 'sph'}_{e['R']:.2f}"
                self.proto(key, lambda e=e: sphere(e["R"], (0.0, 0.0, 0.0)), COL["sphere" if k == "clk sphere" else "tip"],
                           "W-Cu sphere")
                for j, a in enumerate(e["angles"]):
                    jn = "rotor-core" if k == "clk tip" else f"ring-{side}-{e['station']}"
                    self.add(f"{side}_{e['station']}_{'tip' if k == 'clk tip' else 'sph'}_{j + 1}", key, e["body"], e["node"],
                             f"clock-{side}", join=jn, dx=e["r"], dz=e["zc"], rot=a,
                             desc=f"{e['station']} {'rotor tip' if k == 'clk tip' else 'stator sphere'}, node {e['node']}")
            elif k == "cem":
                for piece, mat, col in (("cem_core", "C-EM core (laminated, material OPEN)", (0.45, 0.45, 0.5)),
                                        ("cem_spool_1", "spool (insulating)", (0.85, 0.85, 0.8)),
                                        ("cem_spool_2", "spool (insulating)", (0.85, 0.85, 0.8)),
                                        ("cem_coil", "Cu magnet wire", (0.85, 0.5, 0.2))):
                    self.proto(piece, lambda piece=piece: read_step(os.path.join(SRC, piece + ".step")), col, mat)
                    for j, a in enumerate(e["angles"]):
                        self.add(f"{side}_CEM{j + 1}_{piece.split('_', 1)[1]}", piece, "stator", e["node"] if piece == "cem_core" else "",
                                 f"rel-{side}", join=f"cem-{side}-{j}", dx=e["r_u"], dz=e["zc"], rot=a,
                                 desc=f"C-EM {side}{j + 1} {piece.split('_', 1)[1]}" + (f", bonded to node {e['node']}" if piece == "cem_core" else ""))
            elif k == "utron":
                for piece, mat, col in (("utron_core", "utron core (laminated M235-35A, OPEN)", (0.3, 0.3, 0.35)),
                                        ("utron_coil_1", "Cu, open (not in the circuit)", (0.8, 0.45, 0.2)),
                                        ("utron_coil_2", "Cu, open (not in the circuit)", (0.8, 0.45, 0.2))):
                    self.proto(piece, lambda piece=piece: read_step(os.path.join(SRC, piece + ".step")), col, mat)
                    for j, a in enumerate(e["angles"]):
                        self.add(f"{side}_UTRON{j + 1}_{piece.split('_', 1)[1]}", piece, "rotor", "floating", f"rel-{side}",
                                 join="rotor-core", dx=e["r_u"], dz=e["zc"], rot=a, desc=f"utron {side}{j + 1} {piece.split('_', 1)[1]}")
            elif k == "utron hub":
                key = f"utron_hub_{e['r1']:.2f}"
                self.proto(key, lambda e=e: sector(e["r0"], e["r1"], 0.0, e["z1"] - e["z0"]), COL["g10"], "G10 rotor hub")
                self.add(f"{side}_utron_hub", key, "rotor", "", f"rel-{side}", join="rotor-core", dz=e["z0"], desc="utron hub ring")
            elif k == "hub":
                zc, hh = 0.5 * (e["z0"] + e["z1"]), 0.5 * (e["z1"] - e["z0"])
                rs = min(45.0, hh - 8.0)
                rb = min(0.8 * ro, hh * 1.25)
                self.proto("vac_sphere", lambda: sphere(rs, (0, 0, 0)), COL["glass"], "glass vacuum vessel (placeholder)")
                self.proto("bicone_lo", lambda: cone_shell(S.SLEEVE_R + 2, rb, -hh + 2, 0.0, 3.0), COL["hub"], "G10 bicone (placeholder)")
                self.proto("bicone_hi", lambda: cone_shell(S.SLEEVE_R + 2, rb, hh - 2, 0.0, 3.0), COL["hub"], "G10 bicone (placeholder)")
                self.add("hub_vacuum_sphere", "vac_sphere", "rotor", "", "hub", join="rotor-core", dz=zc, desc="vacuum sphere, AH / C_R hub (placeholder)")
                self.add("hub_bicone_lower", "bicone_lo", "rotor", "", "hub", join="rotor-core", dz=zc, desc="bicone shell, lower")
                self.add("hub_bicone_upper", "bicone_hi", "rotor", "", "hub", join="rotor-core", dz=zc, desc="bicone shell, upper")
        # insulating stator cage per side (holds the stator vanes' outer rings and the clocking stator rings)
        for side in ("A", "B"):
            zs = [e for e in el if e["side"] == side and e["body"] == "stator" and e["kind"] in
                  ("C1 vane", "C2 vane", "Cx vane", "Ca plate", "Cb plate", "clk stator ring")]
            z0, z1 = min(e["z0"] for e in zs), max(e["z1"] for e in zs)
            key = f"cage_{side}"
            self.proto(key, lambda z0=z0, z1=z1: sector(ro + 12.0, ro + 16.0, z0, z1), COL["g10"], "G10 stator cage")
            self.add(f"{side}_stator_cage", key, "stator", "", f"side-{side}", join=f"cage-{side}", desc="insulating stator cage")
        return self

    def placed(self, part):
        pl = part["place"]
        return MG.moved(self.protos[part["proto"]][0], self.trsf(pl))

    @staticmethod
    def trsf(pl):
        from OCP.gp import gp_Trsf, gp_Vec
        t = MG.trsf(pl["dx"], 0.0, 0.0, pl["rot"])
        z = gp_Trsf(); z.SetTranslation(gp_Vec(0, 0, pl["dz"]))
        return z.Multiplied(t)


# ---------------------------------------------------------------------------------------------------------
# checks
# ---------------------------------------------------------------------------------------------------------
def bbox(shape):
    from OCP.Bnd import Bnd_Box
    from OCP.BRepBndLib import BRepBndLib
    b = Bnd_Box(); BRepBndLib.Add_s(shape, b)
    p, q = b.CornerMin(), b.CornerMax()
    return np.array([p.X(), p.Y(), p.Z()]), np.array([q.X(), q.Y(), q.Z()])


def checks(m, log=print):
    from OCP.BRepAlgoAPI import BRepAlgoAPI_Common
    from OCP.BRepExtrema import BRepExtrema_DistShapeShape
    res = {}
    shapes = [(pt, m.placed(pt)) for pt in m.parts]
    boxes = [bbox(s) for _, s in shapes]
    skip = lambda a, b: a["join"] == b["join"] or "coil" in a["proto"] or "coil" in b["proto"]
    clash, n_pairs = [], 0
    for i in range(len(shapes)):
        for j in range(i + 1, len(shapes)):
            (a, sa), (b, sb) = shapes[i], shapes[j]
            (amin, amax), (bmin, bmax) = boxes[i], boxes[j]
            if np.any(amax < bmin - 1e-6) or np.any(bmax < amin - 1e-6) or skip(a, b):
                continue
            n_pairs += 1
            v = MG.props(BRepAlgoAPI_Common(sa, sb).Shape())["volume"]
            if v > 1e-3:
                clash.append((a["name"], b["name"], round(v, 3)))
    res["G-TUBE-CLASH"] = dict(pairs_tested=n_pairs, clashes=clash[:30], n_clash=len(clash), pass_=not clash)
    log(f"G-TUBE-CLASH: {n_pairs} pairs, {len(clash)} clashes")
    # sweep: revolved envelopes (r, z) of rotor solids vs stator solids (vanes are interleaved: z disjoint)
    def rev(s):
        lo, hi = bbox(s)
        P = MG.mesh_points(s, 1.0)
        rr = np.hypot(P[:, 0], P[:, 1])
        return rr.min(), rr.max(), lo[2], hi[2]
    revs = {}
    for pt, s in shapes:
        if "coil" in pt["proto"] or "sph" in pt["proto"]:
            revs[pt["name"]] = rev(s)
        else:
            revs[pt["name"]] = None
    sweep_hits = []
    rotor = [(pt, s) for pt, s in shapes if pt["body"] == "rotor" and pt["join"] == "rotor-core" and pt["name"] not in ("shaft",)]
    stator = [(pt, s) for pt, s in shapes if pt["body"] == "stator"]
    from OCP.BRepPrimAPI import BRepPrimAPI_MakeRevol
    for pr, sr in rotor:
        if pr["proto"] in ("shaft", "sleeve"):
            continue
        r0, r1, z0, z1 = revs[pr["name"]] or rev(sr)
        ring = MG.annulus(max(0.0, r0 - 0.05), r1 + 0.05, z0 - 0.05, z1 + 0.05)
        rlo, rhi = bbox(ring)
        for ps, ss in stator:
            lo, hi = bbox(ss)
            if np.any(hi < rlo) or np.any(rhi < lo):
                continue
            v = MG.props(BRepAlgoAPI_Common(ring, ss).Shape())["volume"] if "coil" not in ps["proto"] else \
                (1.0 if (revs[ps["name"]] and revs[ps["name"]][0] < r1 and revs[ps["name"]][1] > r0
                         and revs[ps["name"]][2] < z1 and revs[ps["name"]][3] > z0) else 0.0)
            if v > 1e-3:
                sweep_hits.append((pr["name"], ps["name"], round(v, 3)))
    res["G-TUBE-SWEEP"] = dict(hits=sweep_hits[:30], n_hits=len(sweep_hits), pass_=not sweep_hits,
                               note="each rotor solid revolved into a ring (its r and z extent) against every stator solid")
    log(f"G-TUBE-SWEEP: {len(sweep_hits)} hits")
    # gaps at alignment: tip turned onto its stator sphere
    gaps = []
    for e in m.el:
        if e["kind"] != "clk sphere":
            continue
        tip = [t for t in m.el if t["kind"] == "clk tip" and t["side"] == e["side"] and t["station"] == e["station"]][0]
        a = e["angles"][0]
        s_sph = MG.moved(sphere(e["R"], (0, 0, 0)), Machine.trsf(dict(dx=e["r"], dz=e["zc"], rot=a)))
        s_tip = MG.moved(sphere(tip["R"], (0, 0, 0)), Machine.trsf(dict(dx=tip["r"], dz=tip["zc"], rot=a)))
        d = BRepExtrema_DistShapeShape(s_sph, s_tip); d.Perform()
        gaps.append(dict(station=e["station"], side=e["side"], set_mm=e["gap"], got_mm=round(d.Value(), 4)))
    res["G-TUBE-GAP"] = dict(rows=gaps, pass_=all(abs(g["got_mm"] - g["set_mm"]) < 1e-3 for g in gaps))
    # reluctance fit: adjacent C-EM cores, utron to sleeve, envelope
    rel = {}
    for side in ("A", "B"):
        cores = [s for pt, s in shapes if pt["proto"] == "cem_core" and pt["group"] == f"rel-{side}"]
        d = BRepExtrema_DistShapeShape(cores[0], cores[1]); d.Perform()
        ut = [s for pt, s in shapes if pt["proto"] == "utron_core" and pt["group"] == f"rel-{side}"][0]
        P = MG.mesh_points(ut, 0.5)
        rel[side] = dict(cem_to_cem_mm=round(d.Value(), 2), utron_inner_r_mm=round(float(np.hypot(P[:, 0], P[:, 1]).min()), 2))
    e_cem = [e for e in m.el if e["kind"] == "cem"][0]
    rel.update(r_utron_centre=e_cem["r_u"], reluctance_envelope_dia_mm=2 * (e_cem["r_u"] + S.REL_X_MAX), sleeve_r=S.SLEEVE_R)
    res["G-TUBE-REL"] = rel
    return res


# ---------------------------------------------------------------------------------------------------------
# STEP (instanced) and the parts list
# ---------------------------------------------------------------------------------------------------------
def write_step(m, path):
    from OCP.STEPCAFControl import STEPCAFControl_Writer
    from OCP.STEPControl import STEPControl_AsIs
    from OCP.TDocStd import TDocStd_Document
    from OCP.TCollection import TCollection_ExtendedString
    from OCP.XCAFDoc import XCAFDoc_DocumentTool, XCAFDoc_ColorType
    from OCP.TDataStd import TDataStd_Name
    from OCP.TopLoc import TopLoc_Location
    from OCP.Quantity import Quantity_Color, Quantity_TypeOfColor
    from OCP.Interface import Interface_Static
    doc = TDocStd_Document(TCollection_ExtendedString("XmlOcaf"))
    stl = XCAFDoc_DocumentTool.ShapeTool_s(doc.Main())
    col = XCAFDoc_DocumentTool.ColorTool_s(doc.Main())
    name = lambda lab, t: TDataStd_Name.Set_s(lab, TCollection_ExtendedString(t))
    top = stl.NewShape(); name(top, "DCCREG tube machine - " + m.lad["tube_geometry"].get("tag", ""))
    groups = {}
    for pt in m.parts:
        if pt["group"] not in groups:
            lab = stl.NewShape(); name(lab, pt["group"]); groups[pt["group"]] = lab
    protos = {}
    for k, (s, c, mat) in m.protos.items():
        lab = stl.AddShape(s, False); name(lab, f"{k} [{mat}]")
        col.SetColor(lab, Quantity_Color(*c, Quantity_TypeOfColor.Quantity_TOC_RGB), XCAFDoc_ColorType.XCAFDoc_ColorSurf)
        protos[k] = lab
    for pt in m.parts:
        comp = stl.AddComponent(groups[pt["group"]], protos[pt["proto"]], TopLoc_Location(Machine.trsf(pt["place"])))
        name(comp, pt["label"])
    for g, lab in groups.items():
        c = stl.AddComponent(top, lab, TopLoc_Location()); name(c, g)
    stl.UpdateAssemblies()
    Interface_Static.SetCVal_s("write.step.product.name", "DCCREG tube machine")
    w = STEPCAFControl_Writer(); w.SetNameMode(True); w.SetColorMode(True)
    w.Transfer(doc, STEPControl_AsIs); w.Write(path)
    return path


def read_back(path):
    """the written STEP read again: placed solid instances (walking the assembly) and distinct products."""
    from OCP.STEPCAFControl import STEPCAFControl_Reader
    from OCP.TDocStd import TDocStd_Document
    from OCP.TCollection import TCollection_ExtendedString
    from OCP.XCAFDoc import XCAFDoc_DocumentTool
    from OCP.TDF import TDF_Label, TDF_ChildIterator
    doc = TDocStd_Document(TCollection_ExtendedString("XmlOcaf"))
    rd = STEPCAFControl_Reader(); rd.SetNameMode(True); rd.ReadFile(path); rd.Transfer(doc)
    tool = XCAFDoc_DocumentTool.ShapeTool_s(doc.Main())
    cnt = dict(instances=0, assemblies=0)

    def walk(lab):
        if tool.IsAssembly_s(lab):
            cnt["assemblies"] += 1
            it = TDF_ChildIterator(lab, False)
            while it.More():
                c = it.Value()
                if tool.IsComponent_s(c):
                    ref = TDF_Label(); tool.GetReferredShape_s(c, ref); walk(ref)
                it.Next()
        else:
            cnt["instances"] += 1
    it = TDF_ChildIterator(tool.Label(), False)
    while it.More():
        lab = it.Value()
        if tool.IsFree_s(lab) and tool.IsShape_s(lab):
            walk(lab)
        it.Next()
    cnt["products"] = len(MG.read_leaves(path))
    return cnt


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--n-plates", type=int, default=None)
    ap.add_argument("--r-out", type=float, default=None)
    ap.add_argument("--no-step", action="store_true")
    a = ap.parse_args()
    plates = {}
    if a.n_plates: plates["n_plates"] = a.n_plates
    if a.r_out: plates["r_outMm"] = a.r_out
    lad = S.size_stack("tube", plates)
    g = lad["tube_geometry"]
    tag = f"tube-r{lad['tube']['r_outMm']:g}-n{lad['tube']['n_plates']}"
    g["tag"] = tag
    m = Machine(lad).build()
    os.makedirs(OUT_DIR, exist_ok=True)
    print(f"{tag}: {len(m.parts)} placed solids from {len(m.protos)} prototypes", flush=True)
    res = dict(tag=tag, n_parts=len(m.parts), n_protos=len(m.protos), L_total_mm=g["L_total_mm"],
               vane_dia_mm=g["diameter_mm"], C_max_pF=lad["ladder"]["C_max"]["value"], kappa=lad["kappa_C"])
    res.update(checks(m))
    json.dump(dict(parts=[{k: v for k, v in pt.items()} for pt in m.parts], elements=g["elements"]),
              open(os.path.join(OUT_DIR, f"{tag}.parts.json"), "w"), indent=0, default=float)
    res["renders"] = renders(m, OUT_DIR, tag)
    if not a.no_step:
        path = write_step(m, os.path.join(OUT_DIR, f"{tag}.step"))
        res["step"] = os.path.relpath(path, ROOT)
        res["step_bytes"] = os.path.getsize(path)
        res["step_read_back"] = rb = read_back(path)
        res["step_read_back"]["pass_"] = rb["instances"] == len(m.parts)
    json.dump(res, open(RESULTS, "w"), indent=1, default=float)
    for k, v in res.items():
        print(k, ":", json.dumps(v, default=float)[:500], flush=True)



# ---------------------------------------------------------------------------------------------------------
# renders: exact planar cuts of the placed solids
# ---------------------------------------------------------------------------------------------------------
def cut_polylines(shape, plane):
    """plane: ('y', 0) for the meridional plane through 0 / 180 deg, ('z', z0) for a plan cut. Returns [Nx2 arrays]."""
    from OCP.BRepAlgoAPI import BRepAlgoAPI_Section
    from OCP.gp import gp_Pln, gp_Pnt, gp_Dir
    from OCP.TopExp import TopExp_Explorer
    from OCP.TopAbs import TopAbs_EDGE
    from OCP.TopoDS import TopoDS
    from OCP.BRepAdaptor import BRepAdaptor_Curve
    from OCP.GCPnts import GCPnts_QuasiUniformDeflection
    ax, v = plane
    pln = gp_Pln(gp_Pnt(0, 0, v if ax == "z" else 0), gp_Dir(0, 0, 1) if ax == "z" else gp_Dir(0, 1, 0))
    sec = BRepAlgoAPI_Section(shape, pln); sec.Build()
    out = []
    e = TopExp_Explorer(sec.Shape(), TopAbs_EDGE)
    while e.More():
        c = BRepAdaptor_Curve(TopoDS.Edge(e.Current()))
        d = GCPnts_QuasiUniformDeflection(c, 0.2)
        if d.IsDone() and d.NbPoints() > 1:
            pts = np.array([[d.Value(i).X(), d.Value(i).Y(), d.Value(i).Z()] for i in range(1, d.NbPoints() + 1)])
            out.append(pts[:, [0, 2]] if ax == "y" else pts[:, [0, 1]])
        e.Next()
    return out


def renders(m, out_dir, tag):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    el = m.el
    colours = {}
    for pt in m.parts:
        c = m.protos[pt["proto"]][1]
        colours[pt["name"]] = c
    shapes = [(pt, m.placed(pt)) for pt in m.parts if "coil" not in pt["proto"]]
    coils = [(pt, m.placed(pt)) for pt in m.parts if "coil" in pt["proto"]]
    files = []
    # 1. meridional section (plane y = 0: 0 deg on the right, 180 deg on the left)
    fig, ax = plt.subplots(figsize=(7.5, 16))
    for pt, s in shapes:
        lo, hi = bbox(s)
        if lo[1] > 0.01 or hi[1] < -0.01:
            continue
        for P in cut_polylines(s, ("y", 0.0)):
            ax.plot(P[:, 0], P[:, 1], color=colours[pt["name"]], lw=0.7)
    ax.axvline(0, color="#888", lw=0.5, ls="--")
    ax.set_aspect("equal"); ax.set_xlabel("x [mm] (0 deg right, 180 deg left)"); ax.set_ylabel("z [mm]")
    ax.set_title(f"{tag}: section through the shaft (y = 0), exact cut of the solids\nrotor angle 0: vanes aligned; "
                 "C-EM B at 0/180 deg cut, C-EM A at 30+60k and the utrons at 15+120k lie outside this plane", fontsize=8)
    f = os.path.join(out_dir, f"{tag}-section.png"); fig.tight_layout(); fig.savefig(f, dpi=110); plt.close(fig); files.append(f)
    # 2. reluctance A: plan cuts at the jaw height and the utron mid-plane
    cem = [e for e in el if e["kind"] == "cem" and e["side"] == "A"][0]
    fig, axs = plt.subplots(1, 2, figsize=(14, 7))
    for a, (zz, title) in zip(axs, ((cem["zc"] + 44.0, "jaw / arm height (z = utron centre + 44)"), (cem["zc"], "utron mid-plane"))):
        for pt, s in shapes + coils:
            lo, hi = bbox(s)
            if lo[2] > zz or hi[2] < zz or pt["group"] not in ("rel-A", "rotor"):
                continue
            for P in cut_polylines(s, ("z", zz)):
                a.plot(P[:, 0], P[:, 1], color=colours[pt["name"]], lw=0.8)
        a.set_aspect("equal"); a.set_title(f"reluctance A: {title}", fontsize=9)
        a.set_xlim(-200, 200); a.set_ylim(-200, 200)
    fig.suptitle(f"{tag}: 6 C-EMs (A at 30 + 60k) and 3 utrons (15 + 120k, rotor angle 0) around the sleeve (r 20)", fontsize=9)
    f = os.path.join(out_dir, f"{tag}-reluctance-plan.png"); fig.tight_layout(); fig.savefig(f, dpi=100); plt.close(fig); files.append(f)
    # 3. clocking A: each deck cut at its gap height (between the tip and the sphere)
    decks = [e for e in el if e["kind"] == "clk sphere" and e["side"] == "A"]
    fig, axs = plt.subplots(1, 4, figsize=(20, 5.6))
    for a, sp in zip(axs, decks):
        tip = [t for t in el if t["kind"] == "clk tip" and t["side"] == "A" and t["station"] == sp["station"]][0]
        zt = tip["zc"] - tip["R"] * 0.5 if tip["zc"] > sp["zc"] else tip["zc"] + tip["R"] * 0.5
        zs = sp["zc"] + sp["R"] * 0.5 if tip["zc"] > sp["zc"] else sp["zc"] - sp["R"] * 0.5
        for pt, s in shapes:
            if sp["station"] not in pt["name"]:
                continue
            for zz, ls in ((zt, "-"), (zs, "-")):
                lo, hi = bbox(s)
                if lo[2] > zz or hi[2] < zz:
                    continue
                for P in cut_polylines(s, ("z", zz)):
                    a.plot(P[:, 0], P[:, 1], color=colours[pt["name"]], lw=0.8, ls=ls)
        for k in range(6):
            th = math.radians(60 * k); a.plot([0, 170 * math.cos(th)], [0, 170 * math.sin(th)], color="#ccc", lw=0.4)
        a.set_aspect("equal"); a.set_xlim(-175, 175); a.set_ylim(-175, 175)
        a.set_title(f"{sp['station']}: sphere {sp['angles'][0]} + 60k (node {sp['node']}), tip 0 + 60k "
                    f"(node {tip['node']}), gap {sp['gap']} mm", fontsize=8)
    fig.suptitle(f"{tag}: clocking deck A, plan cuts through each tip and sphere (rotor angle 0; the gap fires when the rotor "
                 "has turned to the station angle)", fontsize=9)
    f = os.path.join(out_dir, f"{tag}-clocking-plan.png"); fig.tight_layout(); fig.savefig(f, dpi=90); plt.close(fig); files.append(f)
    return [os.path.relpath(x, ROOT) for x in files]


if __name__ == "__main__":
    main()
