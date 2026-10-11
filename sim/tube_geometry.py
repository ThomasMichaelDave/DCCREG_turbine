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
  * reluctance (default): the designer's squared C-EM pieces (core, 2 spool halves, coil; sim/motor_geometry src) x 6
    per side and the utron (core, 2 open coil halves) x 3 per side on a rotor hub, placed at the utron radius;
  * reluctance, --rel wound (the diode build, geared 1 : -1): per side 3 wound utrons (split M235-35A U-core, NiFe neck
    strip, air-break spacer, slot cover, yoke coil with rounded end turns, cheeks) on two G10 carrier discs, and n_br
    passive bridges in a G10 ring on the counter-rotor (the stator body: its cage joined across the hub), every dimension
    from sim/utron_profile.py for an operating point of sim/pole_design_variants_op.json;
  * shaft (rotor), rotor sleeve, insulating stator cage per side, hub placeholder (vacuum sphere + bicone shell).
Repeated parts are stored once in the STEP and instanced.
Checks: G-TUBE-CLASH (no two solids share volume, except the intended joins), G-TUBE-SWEEP (no stator solid in the
volume a rotor solid sweeps; the utron ring against the C-EM pieces exactly), G-TUBE-GAP (tip to sphere at
alignment = the set gap), G-TUBE-REL (C-EM to C-EM, utron to sleeve), the envelope diameters; with --rel wound
G-TUBE-WOUND (the air gap aligned / unaligned, the coil's clearances to the iron, slot cover, cheeks, discs and ring, the tip
arc) and filled exact-section renders.
Usage: python3 sim/tube_geometry.py [--n-plates 8] [--r-out 150] [--no-step] [--rel wound [--pick "g 0.5 / 6 bridges / 1200 rpm"]]
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
       "steel": (0.42, 0.45, 0.5), "glass": (0.75, 0.85, 0.9), "hub": (0.5, 0.52, 0.55),
       "sife": (0.33, 0.35, 0.4), "nife": (0.16, 0.56, 0.56), "cu": (0.8, 0.47, 0.22),
       "peek": (0.86, 0.80, 0.62), "gel": (0.62, 0.86, 0.80), "mnzn": (0.30, 0.27, 0.25), "ring": (0.85, 0.36, 0.12)}


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


def box(x0, x1, y0, y1, z0, z1):
    from OCP.BRepPrimAPI import BRepPrimAPI_MakeBox
    from OCP.gp import gp_Pnt
    return BRepPrimAPI_MakeBox(gp_Pnt(x0, y0, z0), gp_Pnt(x1, y1, z1)).Shape()


def cyl_z(x, y, r, z0, z1):
    from OCP.BRepPrimAPI import BRepPrimAPI_MakeCylinder
    from OCP.gp import gp_Ax2, gp_Pnt, gp_Dir
    return BRepPrimAPI_MakeCylinder(gp_Ax2(gp_Pnt(x, y, z0), gp_Dir(0, 0, 1)), r, z1 - z0).Shape()


def prism(poly, z0, z1):
    """a closed polyline [(x, y), ...] extruded from z0 to z1."""
    from OCP.BRepBuilderAPI import BRepBuilderAPI_MakePolygon, BRepBuilderAPI_MakeFace
    from OCP.BRepPrimAPI import BRepPrimAPI_MakePrism
    from OCP.gp import gp_Pnt, gp_Vec
    mp = BRepBuilderAPI_MakePolygon()
    for x, y in poly:
        mp.Add(gp_Pnt(x, y, z0))
    mp.Close()
    return BRepPrimAPI_MakePrism(BRepBuilderAPI_MakeFace(mp.Wire()).Face(), gp_Vec(0, 0, z1 - z0)).Shape()


def rounded_box_y(x0, x1, y0, y1, z0, z1, R):
    """a box with its four edges parallel to y rounded to radius R (a coil's turns in the x-z plane)."""
    from OCP.BRepFilletAPI import BRepFilletAPI_MakeFillet
    from OCP.TopExp import TopExp_Explorer
    from OCP.TopAbs import TopAbs_EDGE
    from OCP.TopoDS import TopoDS
    from OCP.BRepAdaptor import BRepAdaptor_Curve
    b = box(x0, x1, y0, y1, z0, z1)
    mk = BRepFilletAPI_MakeFillet(b)
    seen = set()
    e = TopExp_Explorer(b, TopAbs_EDGE)
    while e.More():
        ed = TopoDS.Edge(e.Current())
        c = BRepAdaptor_Curve(ed)
        p0, p1 = c.Value(c.FirstParameter()), c.Value(c.LastParameter())
        key = (round(p0.X(), 6), round(p0.Z(), 6))
        if abs(p0.X() - p1.X()) < 1e-9 and abs(p0.Z() - p1.Z()) < 1e-9 and key not in seen:
            seen.add(key)
            mk.Add(R, ed)
        e.Next()
    return mk.Shape()


def cyl_between(p0, p1, r):
    """a cylinder of radius r from the point p0 to the point p1."""
    from OCP.BRepPrimAPI import BRepPrimAPI_MakeCylinder
    from OCP.gp import gp_Ax2, gp_Pnt, gp_Dir
    a, b = np.asarray(p0, float), np.asarray(p1, float)
    v = b - a
    L = float(np.linalg.norm(v))
    u = v / L
    return BRepPrimAPI_MakeCylinder(gp_Ax2(gp_Pnt(*map(float, a)), gp_Dir(*map(float, u))), r, L).Shape()


def wire(points, r):
    """a round wire along a polyline: a cylinder per segment and a sphere at each inner joint, fused."""
    pts = [np.asarray(p, float) for p in points]
    keep = [pts[0]] + [q for p_, q in zip(pts[:-1], pts[1:]) if np.linalg.norm(q - p_) > 1e-6]
    parts = [cyl_between(a, b, r) for a, b in zip(keep[:-1], keep[1:])]
    parts += [sphere(r, tuple(map(float, q))) for q in keep[1:-1]]
    return fuse(parts) if len(parts) > 1 else parts[0]


def capsule_y(rad, half):
    """a capsule along y, centred at the origin: a cylinder of radius rad over |y| <= half with a sphere at each end."""
    return fuse([cyl_between((0, -half, 0), (0, half, 0), rad), sphere(rad, (0, -half, 0)), sphere(rad, (0, half, 0))])


def arc_capsule(r, span_deg, rad, z0, z1):
    """a capsule bent along an arc of radius r from angle 0 to span_deg (an annular sector with a round end of radius
    rad at each end), extruded from z0 to z1."""
    t = math.radians(span_deg)
    return fuse([sector(r - rad, r + rad, z0, z1, 0.0, span_deg), cyl_z(r, 0.0, rad, z0, z1),
                 cyl_z(r * math.cos(t), r * math.sin(t), rad, z0, z1)])


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
        # the shaft is split at the hub: two halves, each ending in a flange bolted to its bicone apex [OC: TMD]
        hub = [e for e in el if e["kind"] == "hub"][0]
        fl = {e["side"]: e for e in el if e["kind"] == "flange"}
        brg = sorted([e for e in el if e["kind"] == "bearing"], key=lambda e: e["z0"])
        self.proto("shaft_A", lambda: sector(0.0, S.SHAFT_R, z_lo, fl["A"]["z0"]), COL["steel"], "austenitic stainless shaft half, non-magnetic")
        self.proto("shaft_B", lambda: sector(0.0, S.SHAFT_R, fl["B"]["z1"], z_hi), COL["steel"], "austenitic stainless shaft half, non-magnetic")
        self.proto("flange", lambda: sector(0.0, S.FLANGE_R, 0.0, S.FLANGE_T), COL["steel"], "austenitic stainless flange, non-magnetic")
        self.add("shaft_A", "shaft_A", "rotor", "", "rotor", join="rotor-core", desc="shaft half A")
        self.add("shaft_B", "shaft_B", "rotor", "", "rotor", join="rotor-core", desc="shaft half B")
        for side in ("A", "B"):
            self.add(f"{side}_flange", "flange", "rotor", "", "hub", join="rotor-core", dz=fl[side]["z0"],
                     desc=f"shaft-half flange {side}, bolted to the bicone apex")
        # rotor sleeve: one segment between each pair of neighbouring bearing hubs (not across the hub)
        cuts = [b["z1"] for b in brg] , [b["z0"] for b in brg]
        segs = []
        for b0, b1 in zip(brg[:-1], brg[1:]):
            if b0["z1"] <= hub["z0"] <= b1["z0"]:
                continue                                       # the hub span: flanges + bicone, no sleeve
            segs.append((b0["z1"], b1["z0"]))
        for i, (a, b) in enumerate(segs):
            key = f"sleeve_{i}"
            self.proto(key, lambda a=a, b=b: sector(S.SHAFT_R, S.SLEEVE_R, a, b), COL["g10"], "G10 rotor sleeve")
            self.add(f"rotor_sleeve_{i + 1}", key, "rotor", "", "rotor", join="rotor-core", desc="rotor sleeve segment")
        # bearing hubs: the bearing (inner ring on the shaft) in a G10 spider tied into the stator cage / the frame
        B = S.BEARING
        self.proto("bearing", lambda: sector(S.SHAFT_R, 0.5 * B["od"], 0.0, B["width"]), COL["steel"], f"{B['name']} bearing")
        self.proto("spider", lambda: sector(0.5 * B["od"], ro + 12.0, 0.0, B["spider_t"]), COL["g10"], "G10 bearing spider")
        for i, b in enumerate(brg):
            frame = b["where"] == "end"
            self.add(f"{b['side']}_bearing_{b['where'].replace(' ', '_').replace('|', '-')}", "bearing", "bearing", "",
                     f"bearings", join=f"brg-{i}", dz=b["zc"] - 0.5 * B["width"], desc=f"bearing, {b['where']}")
            self.add(f"{b['side']}_spider_{b['where'].replace(' ', '_').replace('|', '-')}", "spider", "stator", "",
                     f"bearings", join=f"brg-{i}" if frame else f"cage-{b['side']}", dz=b["zc"] - 0.5 * B["spider_t"],
                     desc=("frame bearing hub" if frame else "bearing hub, tied into the stator cage"))
        counts = {}
        for e in el:
            k = e["kind"]
            side = e["side"]
            counts[(k, side)] = counts.get((k, side), 0) + 1
            i = counts[(k, side)]
            if k.endswith("vane"):
                pr = "stator_vane" if e["body"] == "stator" else "rotor_vane"
                nm = f"{side}_{k.split()[0]}_{e['body'][0]}{i:02d}"
                # C2 runs half a pitch on from C1 (the deck's s1 / s2): side B's stator vanes turn by half the vane
                # pitch, as side B's bridges do, so at rotor angle 0 C1 is at its maximum and C2 at its minimum [IR]
                rot = 0.5 * per if (k.split()[0] == "C2" and e["body"] == "stator") else 0.0
                self.add(nm, pr, e["body"], e["node"], f"side-{side}", join="rotor-core" if e["body"] == "rotor" else f"cage-{side}",
                         dz=e["z0"], rot=rot, desc=f"{k}, node {e['node']}")
            elif k.endswith("plate"):
                self.add(f"{side}_{k.split()[0]}_{i:02d}", "fixed_plate", e["body"], e["node"], f"side-{side}",
                         dz=e["z0"], desc=f"{k}, node {e['node']} (connection and mounts not drawn)")
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
            elif k in ("w utron", "w disc", "w bridge", "w ring", "w flange"):
                self.wound_element(e, k, side, i)
            elif k == "hub" and p.get("hub") == "locked":
                self.locked_hub(e)
            elif k == "hub":
                zc, hh = 0.5 * (e["z0"] + e["z1"]), 0.5 * (e["z1"] - e["z0"])
                rs = min(45.0, hh - 8.0)
                rb = min(0.8 * ro, hh * 1.25)
                self.proto("vac_sphere", lambda: sphere(rs, (0, 0, 0)), COL["glass"], "glass vacuum vessel (placeholder)")
                self.proto("bicone_lo", lambda: cone_shell(S.FLANGE_R, rb, -hh, 0.0, 3.0), COL["hub"], "G10 bicone (placeholder)")
                self.proto("bicone_hi", lambda: cone_shell(S.FLANGE_R, rb, hh, 0.0, 3.0), COL["hub"], "G10 bicone (placeholder)")
                self.add("hub_vacuum_sphere", "vac_sphere", "rotor", "", "hub", join="rotor-core", dz=zc, desc="vacuum sphere, AH / C_R hub (placeholder)")
                self.add("hub_bicone_lower", "bicone_lo", "rotor", "", "hub", join="rotor-core", dz=zc, desc="bicone shell, lower")
                self.add("hub_bicone_upper", "bicone_hi", "rotor", "", "hub", join="rotor-core", dz=zc, desc="bicone shell, upper")
        # insulating stator cage per side (holds the stator vanes' outer rings and the clocking stator rings)
        cz = {}
        for side in ("A", "B"):
            zs = [e for e in el if e["side"] == side and e["body"] == "stator" and e["kind"] in
                  ("C1 vane", "C2 vane", "Cx vane", "Ca plate", "Cb plate", "clk stator ring")] + \
                 [e for e in el if e["side"] == side and e["kind"] == "bearing" and e["where"] != "end"]
            z0, z1 = min(e["z0"] for e in zs), max(e["z1"] for e in zs)
            key = f"cage_{side}"
            self.proto(key, lambda z0=z0, z1=z1: sector(ro + 12.0, ro + 16.0, z0, z1), COL["g10"], "G10 stator cage")
            self.add(f"{side}_stator_cage", key, "stator", "", f"side-{side}", join=f"cage-{side}", desc="insulating stator cage")
            cz[side] = (z0, z1)
        if (p.get("rel") or {}).get("kind") == "wound":
            # geared 1 : -1: the two cages are one counter-rotating body, joined across the hub [IR]
            a1, b0 = cz["A"][1], cz["B"][0]
            self.proto("cage_hub", lambda: sector(ro + 12.0, ro + 16.0, a1, b0), COL["g10"], "G10 stator cage, hub span")
            self.add("hub_stator_cage", "cage_hub", "stator", "", "hub", join="cage-hub",
                     desc="cage across the hub: A and B stator bodies are one counter-rotor")
        return self

    def wound_element(self, e, k, side, i):
        """one element of a wound reluctance section (the diode build): the utrons, a carrier disc, the bridges, the
        bridge ring or its flange; i counts the element's kind on its side."""
        if k == "w utron":
            sp = self.p["rel"]
            self.wound_protos(sp)
            for j, a in enumerate(e["angles"]):
                u = f"{side}_U{j + 1}"
                for piece, desc in (("wu_core_pos", "half-core +v (M235-35A)"), ("wu_core_neg", "half-core -v (M235-35A)"),
                                    ("wu_strip", "neck strip (80 % NiFe)"),
                                    ("wu_spacer", "air-break spacer (G10)"), ("wu_wedge", "slot cover (G10, bonded)"),
                                    ("wu_winding", f"yoke coil, {sp['N_u']} turns, {e['node']}")):
                    self.add(f"{u}_{piece[3:]}", piece, "rotor", e["node"] if piece == "wu_winding" else "", f"rel-{side}",
                             dz=e["zs0"], rot=a, desc=f"utron {side}{j + 1} {desc}")
                for piece in ("wu_cheek_pos", "wu_cheek_neg"):
                    for end, dz in (("lo", e["zs0"]), ("hi", e["zs1"] + sp["t_cheek"])):
                        self.add(f"{u}_{piece[3:]}_{end}", piece, "rotor", "", f"rel-{side}", dz=dz, rot=a,
                                 desc=f"utron {side}{j + 1} cheek (G10), {end} end")
        elif k == "w disc":
            key = f"w_disc_{e['r1']:.1f}"
            self.proto(key, lambda e=e: sector(e["r0"], e["r1"], 0.0, e["z1"] - e["z0"]), COL["g10"], "G10 utron carrier disc")
            self.add(f"{side}_carrier_disc_{i}", key, "rotor", "", f"rel-{side}", dz=e["z0"], desc="utron carrier disc")
        elif k == "w bridge":
            self.proto("w_bridge", lambda e=e: sector(e["r0"], e["r1"], 0.0, e["z1"] - e["z0"], -0.5 * e["width_deg"], e["width_deg"]),
                       COL["sife"], "bridge, M235-35A laminated")
            for j, a in enumerate(e["angles"]):
                self.add(f"{side}_bridge_{j + 1}", "w_bridge", "stator", "", f"rel-{side}", dz=e["z0"], rot=a,
                         desc=f"passive bridge {side}{j + 1} at {a:g} deg")
        elif k == "w ring":
            def ring(e=e):
                from OCP.BRepAlgoAPI import BRepAlgoAPI_Cut
                pk, h = e["pockets"], e["z1"] - e["z0"]
                o = sector(e["r0"], e["r1"], 0.0, h)
                for a in pk["angles"]:
                    o = BRepAlgoAPI_Cut(o, sector(e["r0"] - 1.0, pk["r1"], pk["z0"] - e["z0"], pk["z1"] - e["z0"],
                                                  a - 0.5 * pk["width_deg"], pk["width_deg"])).Shape()
                return o
            self.proto(f"w_ring_{side}", ring, COL["g10"], "G10 bridge ring")
            self.add(f"{side}_bridge_ring", f"w_ring_{side}", "stator", "", f"rel-{side}", dz=e["z0"],
                     desc="bridge ring (counter-rotor), bridges set 1 mm proud of its bore")
        elif k == "w flange":
            key = f"w_flange_{e['r0']:.1f}_{e['r1']:.1f}"
            self.proto(key, lambda e=e: sector(e["r0"], e["r1"], 0.0, e["z1"] - e["z0"]), COL["g10"], "G10 ring flange")
            self.add(f"{side}_ring_flange", key, "stator", "", f"rel-{side}", dz=e["z0"],
                     desc="flange: bridge ring to the stator cage at the Ca|reluctance spider")

    def locked_hub(self, e):
        """the locked hub (presets/hub-locked.json; docs/rings-design.md; docs/drawings/DCCREG-HUB-201), centred on the hub
        element's mid-plane, every part on the rotor: the borosilicate vessel; rings A (below) and B (above), copper foil
        bands with their beads; the silicone gel in the 0.5 mm pocket; the PEEK retainer with its pocket, bead grooves and AH
        bores; the G10 coupler; the AH cores, formers and coils. The shaft halves' flanges come from the layout. [IR] the
        bands' edges are cut normal to the axis (0.1 mm foil); the grooves are the beads' own tori; the retainer is drawn
        whole (the equatorial split is PROPOSED), the coupler a plain tube (its shape is OPEN); the leads' channels and
        the AH ends' caps are not drawn (OPEN)."""
        from OCP.BRepAlgoAPI import BRepAlgoAPI_Common, BRepAlgoAPI_Cut
        from OCP.BRepPrimAPI import BRepPrimAPI_MakeTorus
        from OCP.gp import gp_Ax2, gp_Dir, gp_Pnt
        H = json.load(open(os.path.join(ROOT, "presets", "hub-locked.json")))
        ves, wall = H["vessel"]["value"], H["vessel_wall"]["value"]["t_mm"]
        rg, ah = H["rings"]["value"], H["AH"]["value"]
        ret, gel, cpl = H["retainer"]["value"], H["interface_filler"]["value"], H["shaft_coupler"]["value"]
        zc = 0.5 * (e["z0"] + e["z1"])
        Ro = 0.5 * ves["od_mm"]
        Ri, tf, Rg = Ro - wall, rg["foil_t_mm"], Ro + gel["t_mm"]
        tp, te = math.radians(rg["polar_edge_deg"]), math.radians(rg["equatorial_edge_deg"])
        rho = {"pol": 0.5 * rg["bead_d_mm"]["polar"], "eq": 0.5 * rg["bead_d_mm"]["equatorial"]}
        th = {"pol": tp, "eq": te}
        z_ret, r_ret = ret["absz_max_mm"], ret["r_max_mm"]
        core, former, coil = ah["core"], ah["former"], ah["coil"]
        # LayoutMachine's options: the coupler over both flanges (docs/rings-design.md §2, PROPOSED) and the rings' leads'
        # channels; the record draws neither (its coupler a plain tube over the retainer, the channels OPEN)
        opts = getattr(self, "hub_opts", None) or {}
        z_cpl = opts.get("coupler_absz", z_ret)
        cpl_mat = opts.get("coupler_material", "G10 shaft coupler (shape OPEN: a plain tube)")

        def channel(sg, th):
            """a ring's lead's channel: from its equatorial bead along the sphere's normal past the coupler (r 34)."""
            return cyl_between(lead_dir(sg, th) * (Ro + rho["eq"]), lead_dir(sg, th) * (34.0 / math.sin(te)), 1.6)

        def lead_dir(sg, th):
            t_ = math.radians(th)
            return np.array([math.sin(te) * math.cos(t_), math.sin(te) * math.sin(t_), sg * math.cos(te)])
        chans = lambda: [channel(sg, th) for sg, th in opts.get("channels", ())]

        def cut(a, *bs):
            for b in bs:
                a = BRepAlgoAPI_Cut(a, b).Shape()
            return a

        def band(sg):
            """ring B (sg +1, above) or A (sg -1): the foil between the polar and the equatorial edge."""
            Rm = Ro + 0.5 * tf
            za, zb = sorted((sg * Rm * math.cos(te), sg * Rm * math.cos(tp)))
            return BRepAlgoAPI_Common(cut(sphere(Ro + tf, (0, 0, 0)), sphere(Ro, (0, 0, 0))),
                                      sector(0.0, Ro + tf + 1.0, za, zb)).Shape()

        def bead(sg, w):
            R_c = Ro + rho[w]                                        # the bead touches the glass at its edge [OC]
            return BRepPrimAPI_MakeTorus(gp_Ax2(gp_Pnt(0, 0, sg * R_c * math.cos(th[w])), gp_Dir(0, 0, 1)),
                                         R_c * math.sin(th[w]), rho[w]).Shape()

        def ah_bore(sg):
            za, zb = sorted((sg * core["absz_mm"][0], sg * z_ret))
            return sector(0.0, coil["r_mm"][1], za, zb)

        def gel_shape():
            return cut(sphere(Rg, (0, 0, 0)), sphere(Ro, (0, 0, 0)), band(1), band(-1),
                       *[bead(sg, w) for sg in (1, -1) for w in ("pol", "eq")])

        def retainer():
            return cut(sector(0.0, r_ret, -z_ret, z_ret), sphere(Rg, (0, 0, 0)),
                       *[bead(sg, w) for sg in (1, -1) for w in ("pol", "eq")], ah_bore(1), ah_bore(-1), *chans())
        self.proto("hub_vessel", lambda: cut(sphere(Ro, (0, 0, 0)), sphere(Ri, (0, 0, 0))), COL["glass"],
                   f"borosilicate vessel, OD {2 * Ro:g} mm, wall {wall:g} mm (vacuum inside)")
        self.proto("hub_gel", gel_shape, COL["gel"], f"silicone gel, {gel['t_mm']:g} mm, vacuum-cast")
        self.proto("hub_retainer", retainer, COL["peek"], "PEEK retainer, unfilled")
        self.proto("hub_coupler", lambda: cut(sector(r_ret, r_ret + cpl["wall_mm"], -z_cpl, z_cpl), *chans()), COL["g10"],
                   cpl_mat)
        self.add("hub_vessel", "hub_vessel", "rotor", "", "hub", join="hub-vessel", dz=zc,
                 desc="the vessel: borosilicate sphere, vacuum inside")
        self.add("hub_gel", "hub_gel", "rotor", "", "hub", join="hub-gel", dz=zc, desc="interface filler: silicone gel")
        self.add("hub_retainer", "hub_retainer", "rotor", "", "hub", join="hub-retainer", dz=zc,
                 desc="retainer: PEEK, the pocket over the glass, the bead grooves, the AH bores and seats")
        self.add("hub_coupler", "hub_coupler", "rotor", "", "hub", join="hub-coupler", dz=zc,
                 desc="shaft coupler: G10 around the retainer, between the flanges")
        for sg, nm, v in ((1, "B", "+15.0 kV"), (-1, "A", "-15.0 kV")):
            self.proto(f"hub_ring_{nm}", lambda sg=sg: band(sg), COL["ring"], f"Cu-ETP foil {tf:g} mm, a band")
            self.add(f"hub_ring_{nm}", f"hub_ring_{nm}", "rotor", f"ring {nm}", "hub", join=f"ring-{nm}", dz=zc,
                     desc=f"ring {nm} ({v}): the foil band, {rg['polar_edge_deg']:g}-{rg['equatorial_edge_deg']:g} deg")
            for w, d_ in (("pol", rg["bead_d_mm"]["polar"]), ("eq", rg["bead_d_mm"]["equatorial"])):
                self.proto(f"hub_bead_{nm}_{w}", lambda sg=sg, w=w: bead(sg, w), COL["ring"], f"Cu wire ring, {d_:g} mm")
                self.add(f"hub_bead_{nm}_{w}", f"hub_bead_{nm}_{w}", "rotor", f"ring {nm}", "hub", join=f"ring-{nm}",
                         dz=zc, desc=f"ring {nm}'s {'polar' if w == 'pol' else 'equatorial'} bead, soldered to the foil")
        for sg, nm in ((1, "B"), (-1, "A")):
            for piece, r0, r1, z_, colr, mat in (
                    ("core", 0.0, 0.5 * core["d_mm"], core["absz_mm"], COL["mnzn"], f"{core['material']} rod ({core['part']})"),
                    ("former", 0.5 * former["id_mm"], 0.5 * former["od_mm"], core["absz_mm"], COL["g10"], "G-10 former"),
                    ("coil", coil["r_mm"][0], coil["r_mm"][1], coil["absz_mm"], COL["cu"], f"Cu coil, {coil['turns']} turns")):
                za, zb = sorted((sg * z_[0], sg * z_[1]))
                self.proto(f"ah_{piece}_{nm}", lambda r0=r0, r1=r1, za=za, zb=zb: sector(r0, r1, za, zb), colr, mat)
                self.add(f"hub_AH_{nm}_{piece}", f"ah_{piece}_{nm}", "rotor", "REF" if piece == "core" else "",
                         "hub", join=f"ah-{nm}", dz=zc, desc=f"AH {nm} ({'above' if sg > 0 else 'below'}): {piece}")

    def wound_protos(self, sp):
        """the wound utron's parts (sim/utron_profile.py), local u = x (radius along the centre line), v = y, w = z from
        the stack's lower end; built once, placed per utron."""
        import utron_profile as U
        from OCP.BRepAlgoAPI import BRepAlgoAPI_Common, BRepAlgoAPI_Cut
        L = sp["L"]
        R = U.rects(sp)

        def core(sd):
            """one L-shaped half-core (sd +1: v > 0), a laminated stack of its own."""
            c = BRepAlgoAPI_Common(prism(U.half_core(sp, sd, arc=False), 0.0, L),
                                   cyl_z(0.0, 0.0, sp["r_g"], -1.0, L + 1.0)).Shape()      # tip face on the gap arc
            for (u, v) in sp["studs"]:
                c = BRepAlgoAPI_Cut(c, cyl_z(u, sd * v, 0.5 * sp["stud_d"], -1.0, L + 1.0)).Shape()
            return c

        def winding():
            cr = U.coil_ring(sp)
            (u0, u1, w0, w1, Ro), (i0, i1, j0, j1, Ri) = cr["outer"], cr["inner"]
            return BRepAlgoAPI_Cut(rounded_box_y(u0, u1, -sp["cv"], sp["cv"], w0, w1, Ro),
                                   rounded_box_y(i0, i1, -sp["cv"] - 1.0, sp["cv"] + 1.0, j0, j1, Ri)).Shape()

        def cheek(sd):
            r = R["cheek_pos" if sd > 0 else "cheek_neg"]
            c = box(r[0], r[1], r[2], r[3], -sp["t_cheek"], 0.0)
            for (u, v) in sp["studs"]:
                c = BRepAlgoAPI_Cut(c, cyl_z(u, sd * v, 0.5 * sp["stud_d"], -sp["t_cheek"] - 1.0, 1.0)).Shape()
            return c
        bx = lambda r: box(r[0], r[1], r[2], r[3], 0.0, L)
        self.proto("wu_core_pos", lambda: core(+1), COL["sife"], "utron half-core, M235-35A laminated (studded)")
        self.proto("wu_core_neg", lambda: core(-1), COL["sife"], "utron half-core, M235-35A laminated (studded)")
        self.proto("wu_strip", lambda: bx(R["strip"]), COL["nife"], "neck strip, 80 % NiFe laminated 0.1 mm")
        self.proto("wu_spacer", lambda: bx(R["spacer"]), COL["g10"], "G10 air-break spacer")
        self.proto("wu_wedge", lambda: prism(U.wedge(sp), 0.0, L), COL["g10"], "G10 slot cover")
        self.proto("wu_winding", winding, COL["cu"], f"Cu yoke coil, {sp['N_u']} turns of {sp.get('wire_d_mm', 0):.2f} mm")
        self.proto("wu_cheek_pos", lambda: cheek(+1), COL["g10"], "G10 cheek")
        self.proto("wu_cheek_neg", lambda: cheek(-1), COL["g10"], "G10 cheek")

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
# the multiplier laid out in the machine (sim/multiplier_layout.py, PROPOSED 2026-10-11)
# ---------------------------------------------------------------------------------------------------------
LAYOUT_JSON = os.path.join(HERE, "multiplier_layout_results.json")
COL.update({"can": (0.64, 0.69, 0.75), "silicone": (0.80, 0.86, 0.89), "stick": (0.16, 0.17, 0.20),
            "rsurge": (0.30, 0.49, 0.36), "cap": (0.30, 0.47, 0.71), "clamp": (0.60, 0.45, 0.20),
            "brass": (0.80, 0.66, 0.30), "ptfe": (0.93, 0.93, 0.90), "lv": (0.87, 0.55, 0.08),
            "cartridge": (0.70, 0.72, 0.76), "steatite": (0.92, 0.90, 0.84), "al": (0.72, 0.74, 0.78),
            "rod": (0.55, 0.47, 0.30)})
WIRE_R = 1.5            # PTFE HV wire: a 1 mm conductor in 3 mm of PTFE (sim/multiplier_layout.py bore_wire) [IR]
LV_R = 2.5              # the magnetic pump's LV leads drawn as one 5 mm cable [RH]
LV_BORE = 8.0           # the LV bore in each shaft half (sim/multiplier-layout-findings.md §7)
LV_EXIT = 306.0         # |z| of its radial exit: between the Ca|reluctance bearing and the inner carrier disc [IR]
Z_OVER = 76.5           # |z| at which the deck's leads run over the parts (their zone ends at 78) [IR]
J_COND = (5.0, 12.0)    # a junction's brass terminal: radius, length, standing [RH]
J_POT = (10.0, 24.0)    # its potted block, 20 mm across (sim/multiplier_layout.py deck_mass), as tall as the housings [RH]
POST = 60.0             # |z| of a junction block's outer face, where the riser and the tap leave it
STUD_R = 2.5            # a standing part's screw terminals (M5) [RH]
BUSH = (5.0, 1.6, 12.0)  # a ring lead's PTFE bushing through the can: outer radius, bore, length [RH]
SHED = (12.0, 2.0)      # the sleeve's PTFE sheds: radial height (sim/multiplier-layout-findings.md §4), thickness [RH]
COVER_T = 2.0           # the PTFE cover over the sleeve under the column [RH]
LEAD_Z = 57.0           # |z| at which a ring's lead leaves the can: the parts' mid-height (docs/make_multiplier_layout.py)
LEAD_R = 36.0           # the radius of its run along the coupler [IR]
R_RISER = 35.0          # node 1's riser in the column's bore (sim/multiplier_layout.py strays) [IR]


def _ang(xy):
    return math.degrees(math.atan2(xy[1], xy[0]))


def _u(th_deg):
    t = math.radians(th_deg)
    return np.array([math.cos(t), math.sin(t), 0.0])


def _cut(a, *bs):
    from OCP.BRepAlgoAPI import BRepAlgoAPI_Cut
    for b in bs:
        a = BRepAlgoAPI_Cut(a, b).Shape()
    return a


class LayoutMachine(Machine):
    """the design of record re-stacked as sim/multiplier_layout.py lays the multiplier out (PROPOSED; its results: the
    stack, both decks' plans, the record's reluctance sections moved), each side from the hub outward: the hub as locked
    inside a grounded Al can; the deck, a G10 plate with every diode, C3-C8, Csa / Csb, the clamp string and the surge
    resistors potted on it; Ca / Cb's six plates; the vane stack with its ends swapped, C1 and C2 in phase; the
    Ca|reluctance bearing; the record's reluctance section; with ring_bearings, a bearing between the shaft and each
    bridge ring's outer end (sim/bridge_ring_bearings.py, PROPOSED: in the record's end-bearing slot, the end bearing
    one slot out; its cartridge, spider and the ring joining the spider to the bridge ring); with mounts, the
    capacitors' mounts (sim/doubler_caps.py placement, PROPOSED: Ca / Cb's two combs on their own posts in the bore,
    the rotor vanes on G10 spacer rings and dowels, the stator vanes on lugs, tie rods and spacer tubes, the cage
    moved out to r 182). No hub-face bearings; one cage from spider to spider. Drawn as well: the junctions, the leads over the parts, the straps to the can, node 1's
    riser, node 2's tap, the cross nets l1 / r1, the rings' leads through the can, the sleeve's PTFE cover and sheds,
    the magnetic pump's LV cable in its bore [IR; the parts' envelopes and the junctions RH]. self.nets: each
    conductor's net (or its two nets and the line or arc it grades along) for the viewer."""

    def __init__(self, pick="g 0.5 / 6 bridges / 1200 rpm", ring_bearings=True, mounts=True):
        import copy
        import bridge_ring_bearings as BRB               # the bridge-ring bearings' placement and part
        import doubler_caps as DC                        # the capacitors' mounts (PROPOSED)
        super().__init__(S.size_stack("tube", record_plates(pick)))
        self.lay = json.load(open(LAYOUT_JSON))
        self.mounts = DC.placement(self.lay) if mounts else None
        st = self.lay["stack"]
        rec = self.lad["tube_geometry"]["elements"]
        hub = [e for e in rec if e["kind"] == "hub"][0]
        z_rec = 0.5 * (hub["z0"] + hub["z1"])                 # the record's hub centre (470)
        self.ring = BRB.placement(st) if ring_bearings else None
        self.ring_slot = BRB.SLOT if ring_bearings else 0.0
        # the new hub centre from side A's end (487, or 507 with the bridge-ring bearings) and the length (974, 1014)
        self.zc, self.L_mm = st["h_end_mm"] + self.ring_slot, st["L_mm"] + 2.0 * self.ring_slot
        # the record's reluctance sections and end bearings: side A where it was, side B out by 2 dh (as
        # sim/multiplier_layout.py record_reluctance moves them). With the bridge-ring bearings each end bearing moves
        # one slot further out: in z from side A's end, side A's sections move by the slot and its end bearing stays
        sh_b = 2.0 * (st["h_end_mm"] - z_rec)
        self.el = []
        for e in rec:
            if e["kind"] not in ("w utron", "w disc", "w bridge", "w ring", "w flange", "reluctance") and not (
                    e["kind"] == "bearing" and e.get("where") == "end"):
                continue
            q = copy.deepcopy(e)
            end, sl = q["kind"] == "bearing", self.ring_slot
            dz = (0.0 if end else sl) if q["side"] == "A" else sh_b + (2.0 if end else 1.0) * sl
            for k in ("z0", "z1", "zc", "zs0", "zs1"):
                if k in q:
                    q[k] += dz
            if "pockets" in q:
                q["pockets"] = dict(q["pockets"], z0=q["pockets"]["z0"] + dz, z1=q["pockets"]["z1"] + dz)
            self.el.append(q)
        self.lad["tube_geometry"]["L_total_mm"] = self.L_mm
        self.nets = {}

    def zz(self, side, h):
        return self.zc - h if side == "A" else self.zc + h

    def zs(self, side, h0, h1):
        a, b = self.zz(side, h0), self.zz(side, h1)
        return (a, b) if a < b else (b, a)

    def put(self, name, key, make, colour, material, body, group, join=None, net=None, dz=0.0, rot=0.0, dx=0.0, desc=""):
        """a part (its prototype made once): net a net's name, or {'nets': [a, b], 'axis' | 'arc': ...} for a part whose
        potential grades from a to b."""
        self.proto(key, make, colour, material)
        self.add(name, key, body, net if isinstance(net, str) else "", group, join=join, dz=dz, rot=rot, dx=dx, desc=desc)
        if net is not None:
            self.nets[name] = dict(net) if isinstance(net, dict) else {"net": net}

    def put_wire(self, name, pts, net, group, join, colour=None, material="PTFE HV wire, 1 mm Cu in 3 mm PTFE", r=WIRE_R,
                 desc="", body="rotor"):
        P = [tuple(float(x) for x in q) for q in pts]
        self.put(name, name, lambda P=P: wire(P, r), colour or COL["ptfe"], material, body, group, join=join, net=net,
                 desc=desc)
        self.nets[name]["path"] = [list(q) for q in P]

    def build(self):
        import multiplier_layout as ML                   # the study's leads, straps and mirror (its own constants)
        p, st, dk = self.p, self.lay["stack"], self.lay["decks"]
        E = st["elements"]
        kinds = lambda k: [e for e in E if e["kind"] == k]
        one = lambda k: kinds(k)[0]
        ri, ro, t = p["r_inMm"], p["r_outMm"], p["t_vaneMm"]
        assert (ri, ro, t) == (ML.R_IN, ML.R_OUT, ML.T_V), "the layout's vanes and plates are the record's"
        hs, hw = 0.5 * p["ws_deg"], 0.5 * p["wr_deg"]
        per = 360.0 / (p["N_sec"] / 2.0)
        n_sec = int(p["N_sec"] / 2)
        if not self.mounts:                              # with the mounts every vane and plate has its own prototype
            self.proto("stator_vane", lambda: fuse([sector(ri, ro, 0.0, t, k * per - hs, p["ws_deg"]) for k in range(n_sec)]
                                                   + [sector(ro, ro + 12.0, 0.0, t)]), COL["stator vane"], "Al vane")
            self.proto("rotor_vane", lambda: fuse([sector(ri, ro, 0.0, t, k * per - hw, p["wr_deg"]) for k in range(n_sec)]
                                                  + [sector(S.SLEEVE_R, ri, 0.0, t)]), COL["rotor vane"], "Al vane")
            self.proto("fixed_plate", lambda: sector(ri, ro, 0.0, t), COL["fixed plate"], "Al plate")
        zc, mirror = self.zc, ML.MIRROR
        if self.mounts:
            self.mount_protos(ML, dk, ri, ro, t, hs, hw, per, n_sec)
        mp = {"A": lambda n: n, "B": lambda n: mirror[n]}
        plan = {s_: {q["name"]: q for q in dk[s_]["parts"]} for s_ in "AB"}
        csa = {"A": plan["A"]["Csa"], "B": plan["B"]["Csb"]}
        th_lead = {s_: _ang(csa[s_]["centre"]) for s_ in "AB"}          # each ring's lead leaves the can toward its Cs
        bore = 0.5 * LV_BORE
        # ---- the hub as locked (its coupler over both flanges, its leads' channels), the flanges, the shaft halves
        fl, cpl = one("flange"), one("coupler")
        self.hub_opts = dict(coupler_absz=cpl["h1"], channels=[(-1, th_lead["A"]), (1, th_lead["B"])],
                             coupler_material="G10 shaft coupler: a straight tube over the retainer and both flanges "
                                              "(docs/rings-design.md §2, PROPOSED)")
        self.locked_hub(dict(z0=zc - fl["h0"], z1=zc + fl["h0"]))
        for nm in ("hub_ring_A", "hub_bead_A_pol", "hub_bead_A_eq"):
            self.nets[nm] = {"net": "ea"}
        for nm in ("hub_ring_B", "hub_bead_B_pol", "hub_bead_B_eq"):
            self.nets[nm] = {"net": "eb"}
        for s_ in "AB":
            self.nets[f"hub_AH_{s_}_core"] = {"net": "0"}
        tf = fl["h1"] - fl["h0"]
        self.proto("flange_lv", lambda: _cut(sector(0.0, fl["r1"], 0.0, tf), cyl_z(0.0, 0.0, bore, -1.0, tf + 1.0)),
                   COL["steel"], "austenitic stainless flange, non-magnetic, turned to 60 mm, its LV bore 8 mm")
        sh = one("shaft")
        for s_ in "AB":
            z0, _ = self.zs(s_, fl["h0"], fl["h1"])
            self.put(f"{s_}_flange", "flange_lv", None, None, None, "rotor", "hub", join="rotor-core", net="0", dz=z0,
                     desc=f"shaft-half flange {s_}, bonded and pinned in the coupler")
            z0, z1 = self.zs(s_, sh["h0"], sh["h1"] + self.ring_slot)       # to the end bearing, one slot out
            ze, zf = self.zz(s_, LV_EXIT), self.zz(s_, sh["h0"])
            lo, hi = (ze - bore, zf + 1.0) if s_ == "A" else (zf - 1.0, ze + bore)     # the bore ends round its exit

            def shaft_half(z0=z0, z1=z1, lo=lo, hi=hi, ze=ze):
                return _cut(sector(0.0, S.SHAFT_R, z0, z1), cyl_z(0.0, 0.0, bore, lo, hi),
                            cyl_between((0.0, 0.0, ze), (S.SHAFT_R + 1.0, 0.0, ze), bore))
            self.put(f"shaft_{s_}", f"shaft_{s_}", shaft_half, COL["steel"], "austenitic stainless shaft half, non-magnetic",
                     "rotor", "rotor", join="rotor-core", net="0", desc=f"shaft half {s_}, its LV bore 8 mm")
            # the magnetic pump's LV cable: from the flange's face down the bore, out radially in the reluctance bay
            self.put_wire(f"{s_}_lv_cable", [(0.0, 0.0, self.zz(s_, fl["h0"])), (0.0, 0.0, ze), (S.SLEEVE_R + 3.5, 0.0, ze)],
                          "lv", "rotor", f"lv-{s_}", colour=COL["lv"], r=LV_R,
                          material="LV cable: the AH coils to La / Lb, D1*-D4* and the utrons (sim/multiplier-layout-findings.md §7)",
                          desc="the magnetic pump's LV leads in the shaft's bore")
        # ---- the can over the hub (REF), its end discs and the rings' leads' bushings
        can, cdi = one("can"), one("can disc")
        lead_pt = lambda s_, r: _u(th_lead[s_]) * r + np.array([0.0, 0.0, self.zz(s_, LEAD_Z)])
        self.put("can", "can", lambda: _cut(sector(can["r0"], can["r1"], zc - can["h1"], zc + can["h1"]),
                                            *[cyl_between(lead_pt(s_, can["r0"] - 2.0), lead_pt(s_, can["r1"] + 2.0), BUSH[0])
                                              for s_ in "AB"]),
                 COL["can"], "Al can over the hub, 2 mm, on the shaft (REF)", "rotor", "can", join="can", net="0",
                 desc="the grounded can: r 46-48, |z| <= 85 (sim/multiplier-layout-findings.md §5)")
        for s_ in "AB":
            z0, _ = self.zs(s_, cdi["h0"], cdi["h1"])
            if self.mounts:                              # three M4 holes for node 2's standoffs
                self.put(f"{s_}_can_disc", "can_disc_m", None, None, None, "rotor", "can", join="can", net="0", dz=z0,
                         rot=self.mounts["sides"][s_]["theta_n2_deg"][0],
                         desc=f"the can's end disc {s_}, on the shaft; node {mp[s_]('2')}'s three standoffs on it")
            else:
                self.put(f"{s_}_can_disc", "can_disc", lambda: sector(cdi["r0"], cdi["r1"], 0.0, cdi["h1"] - cdi["h0"]),
                         COL["can"], "Al end disc of the can", "rotor", "can", join="can", net="0", dz=z0,
                         desc=f"the can's end disc {s_}, on the shaft")
            a_, b_ = lead_pt(s_, 48.0 - 0.5 * BUSH[2]), lead_pt(s_, 48.0 + 0.5 * BUSH[2])
            self.put(f"{s_}_bushing", f"bushing_{s_}", lambda a_=a_, b_=b_: _cut(cyl_between(a_, b_, BUSH[0]),
                                                                                 cyl_between(a_ - (b_ - a_), b_ + (b_ - a_), BUSH[1])),
                     COL["ptfe"], "PTFE bushing", "rotor", "can", join="can", desc=f"ring {s_}'s lead through the can")
        # ---- the column, the vanes (C1 and C2 in phase: no offset), the sleeves, the PTFE cover and sheds
        hv0 = st["h_vanes"][0]
        hb = st["h_bearing_mm"]
        for s_ in "AB":
            cn, vn = ("Ca", "C1") if s_ == "A" else ("Cb", "C2")
            for e in kinds("Ca plate"):
                z0, _ = self.zs(s_, e["h0"], e["h1"])
                nd = mp[s_](e["node"])
                if self.mounts:                          # its comb's tabs and holes (sim/doubler_caps.py)
                    q = self.mounts["sides"][s_]
                    key = {6: f"ca_n2_base_{s_}", 5: f"ca_n1_end_{s_}", 4: "ca_n2", 3: "ca_n1", 2: f"ca_n2_end_{s_}",
                           1: "ca_n1"}[e["index"]]
                    rot = q["theta_n1_deg"][0] if e["node"] == "1" else q["theta_n2_deg"][0]
                    self.put(f"{s_}_{cn}_{e['index']:02d}", key, None, None, None, "rotor", f"side-{s_}",
                             join=f"ca{e['node']}-{s_}", net=nd, dz=z0, rot=rot,
                             desc=f"{cn} fixed plate, node {nd}: three tabs into the bore on its comb's posts")
                else:
                    self.put(f"{s_}_{cn}_{e['index']:02d}", "fixed_plate", None, None, None, "rotor", f"side-{s_}", net=nd,
                             dz=z0, desc=f"{cn} fixed plate, node {nd} (the record's six, node {mp[s_]('2')} toward the "
                                         "deck; their rods and mounts not drawn)")
            for e in kinds("C1 vane"):
                z0, _ = self.zs(s_, e["h0"], e["h1"])
                rot_ = e["body"] == "rotor"
                key = "rotor_vane" if rot_ else "stator_vane"
                if self.mounts:
                    key = (f"rotor_vane_end_{s_}" if e["index"] == 1 else "rotor_vane_m") if rot_ else "stator_vane_m"
                self.put(f"{s_}_{vn}_{'r' if rot_ else 's'}{e['index']:02d}", key, None,
                         None, None, "rotor" if rot_ else "stator", f"side-{s_}", join="rotor-core" if rot_ else "cage",
                         net=mp[s_](e["node"]) if rot_ else "s", dz=z0,
                         desc=f"{vn} vane, node {mp[s_](e['node']) if rot_ else 'REF (the counter-rotor)'}"
                              + (", in phase with C1" if s_ == "B" else ""))
            sl = one("sleeve")
            z0, z1 = self.zs(s_, sl["h0"], sl["h1"])
            self.put(f"{s_}_rotor_sleeve_vanes", "sleeve_vanes", lambda z0=z0, z1=z1: sector(S.SHAFT_R, S.SLEEVE_R, 0.0, z1 - z0),
                     COL["g10"], "G10 rotor sleeve", "rotor", "rotor", join="rotor-core", dz=z0,
                     desc="rotor sleeve: the vane bay, the can's disc to the Ca|reluctance bearing")
            eb = [e for e in self.el if e["kind"] == "bearing" and e["side"] == s_][0]
            ze = self.zz(s_, LV_EXIT)
            z0, z1 = (eb["z1"] + self.ring_slot, self.zz("A", hb + 0.5 * S.BEARING["slot"])) if s_ == "A" else \
                (self.zz("B", hb + 0.5 * S.BEARING["slot"]), eb["z0"] - self.ring_slot)
            self.put(f"{s_}_rotor_sleeve_rel", f"sleeve_rel_{s_}",
                     lambda z0=z0, z1=z1, ze=ze: _cut(sector(S.SHAFT_R, S.SLEEVE_R, z0, z1),
                                                      cyl_between((S.SHAFT_R - 1.0, 0.0, ze), (S.SLEEVE_R + 1.0, 0.0, ze), bore)),
                     COL["g10"], "G10 rotor sleeve", "rotor", "rotor", join="rotor-core",
                     desc="rotor sleeve: the reluctance bay (the record's), its LV exit 8 mm")
            z0, z1 = self.zs(s_, sl["h0"], hv0)
            self.put(f"{s_}_sleeve_cover", "sleeve_cover", lambda z0=z0, z1=z1: sector(S.SLEEVE_R, S.SLEEVE_R + COVER_T, 0.0, z1 - z0),
                     COL["ptfe"], "PTFE cover over the sleeve", "rotor", f"side-{s_}", join=f"cover-{s_}", dz=z0,
                     desc="the sleeve's PTFE cover under the column: 84 mm of creepage (sim/multiplier-layout-findings.md §4)")
            last = max((e for e in kinds("C1 vane") if e["body"] == "rotor"), key=lambda e: e["h1"])
            gap = (hb - 0.5 * S.BEARING["width"]) - last["h1"]
            for j in (1, 2):
                h_ = last["h1"] + j * gap / 3.0
                z0, _ = self.zs(s_, h_ - 0.5 * SHED[1], h_ + 0.5 * SHED[1])
                self.put(f"{s_}_shed_{j}", "shed", lambda: sector(S.SLEEVE_R, S.SLEEVE_R + SHED[0], 0.0, SHED[1]), COL["ptfe"],
                         "PTFE shed, 12 mm", "rotor", f"side-{s_}", join=f"cover-{s_}", dz=z0,
                         desc="a PTFE shed on the sleeve's outer end (two give 65.5 mm of creepage)")
        # ---- the bearings: the Ca|reluctance pair (the REF link) and the end pair (frame); one cage, spider to spider
        B = S.BEARING
        self.proto("bearing", lambda: sector(S.SHAFT_R, 0.5 * B["od"], 0.0, B["width"]), COL["steel"], f"{B['name']} bearing")
        self.proto("spider", lambda: sector(0.5 * B["od"], ro + 12.0, 0.0, B["spider_t"]), COL["g10"], "G10 bearing spider")
        for s_ in "AB":
            zb = self.zz(s_, hb)
            self.put(f"{s_}_bearing_Ca-reluctance", "bearing", None, None, None, "bearing", "bearings", join=f"brg-{s_}-rel",
                     net="0", dz=zb - 0.5 * B["width"], desc="bearing, Ca|reluctance: the REF link to the counter-rotor")
            self.put(f"{s_}_spider_Ca-reluctance", "spider_rel" if self.mounts else "spider", None, None, None, "stator",
                     "bearings", join="cage", dz=zb - 0.5 * B["spider_t"],
                     desc="bearing hub, tied into the stator cage" + (" and the stator vanes' tie rods" if self.mounts else ""))
            eb = [e for e in self.el if e["kind"] == "bearing" and e["side"] == s_][0]
            self.put(f"{s_}_bearing_end", "bearing", None, None, None, "bearing", "bearings", join=f"brg-{s_}-end", net="0",
                     dz=eb["zc"] - 0.5 * B["width"], desc="bearing, end (frame)")
            self.put(f"{s_}_spider_end", "spider", None, None, None, "stator", "bearings", join=f"brg-{s_}-end",
                     dz=eb["zc"] - 0.5 * B["spider_t"], desc="frame bearing hub")
        if self.ring:
            self.ring_bearing_parts()
        za, zb_ = self.zz("A", hb + 0.5 * B["slot"]), self.zz("B", hb + 0.5 * B["slot"])
        rc0, rc1 = (self.mounts["cage"]["r0"], self.mounts["cage"]["r1"]) if self.mounts else (ro + 12.0, ro + 16.0)
        self.put("stator_cage", "cage", lambda: sector(rc0, rc1, za, zb_), COL["g10"], "G10 stator cage",
                 "stator", "cage", join="cage", desc="the counter-rotor's cage: one tube from spider to spider, no hub-face bearing"
                 + (f"; r {rc0:.0f}-{rc1:.0f}, the stator vanes' lugs located in its bore" if self.mounts else ""))
        if self.mounts:
            self.mount_parts(mp)
        # ---- the record's reluctance sections
        counts = {}
        for e in self.el:
            k, s_ = e["kind"], e["side"]
            counts[(k, s_)] = counts.get((k, s_), 0) + 1
            if k.startswith("w "):
                self.wound_element(e, k, s_, counts[(k, s_)])
        for nm, pt in [(q["name"], q) for q in self.parts]:
            if pt["proto"] in ("w_bridge",) or pt["proto"].startswith("wu_core"):
                self.nets[nm] = {"net": "s" if pt["body"] == "stator" else "0"}
        # ---- the decks
        self.decks(ML, dk, st, kinds, one, mp, plan, th_lead, hv0)
        return self

    def ring_bearing_parts(self):
        """the bridge-ring bearings (sim/bridge_ring_bearings.py placement, PROPOSED): each bearing in its stainless
        cartridge (barrel, a flange on the spider's outboard face, a lip over the outer ring inboard), the 8 mm G10
        spider centred in its slot, and the 6 mm G10 ring from the spider's rim to the bridge ring's outer face; side B
        the mirror of side A [IR; the cartridge's walls RH]."""
        import bridge_ring_bearings as BRB
        P, part = self.ring["side_A"], BRB.PART
        mz = lambda s_, z0, z1: (z0, z1) if s_ == "A" else (2.0 * self.zc - z1, 2.0 * self.zc - z0)
        b, sp, ad = P["bearing"], P["spider"], P["adapter"]
        self.proto("ring_bearing", lambda: sector(b["r0"], b["r1"], 0.0, b["z1"] - b["z0"]), COL["steel"],
                   f"{part['maker']} {part['designation']} deep groove ball bearing, 25 / 52 / 15 (PROPOSED)")
        self.proto("ring_spider", lambda: sector(sp["r0"], sp["r1"], 0.0, sp["z1"] - sp["z0"]), COL["g10"],
                   "G10 bearing spider, the bridge-ring bearing's")
        self.proto("ring_adapter", lambda: sector(ad["r0"], ad["r1"], 0.0, ad["z1"] - ad["z0"]), COL["g10"],
                   "G10 ring, the spider's rim to the bridge ring's outer face")
        for s_ in "AB":
            def cart(s_=s_):
                return fuse([sector(q["r0"], q["r1"], *mz(s_, q["z0"], q["z1"]))
                             for q in (P["cartridge_barrel"], P["cartridge_flange"], P["cartridge_lip"])])
            self.proto(f"ring_cartridge_{s_}", cart, COL["cartridge"], BRB.CART_MATERIAL)
            role = "locates the counter-rotor axially" if s_ == "A" else "floats on its spring preload"
            self.put(f"{s_}_bearing_bridge-ring", "ring_bearing", None, None, None, "bearing", "bearings",
                     join=f"brg-{s_}-ring", net="0", dz=mz(s_, b["z0"], b["z1"])[0],
                     desc=f"bearing, bridge ring {s_}'s outer end: {part['maker']} {part['designation']}; {role}")
            self.put(f"{s_}_cartridge_bridge-ring", f"ring_cartridge_{s_}", None, None, None, "stator", "bearings",
                     join=f"brg-{s_}-ring", net="0", desc="the bridge-ring bearing's cartridge, bolted to its spider")
            self.put(f"{s_}_spider_bridge-ring", "ring_spider", None, None, None, "stator", "bearings", join=f"ring-{s_}",
                     dz=mz(s_, sp["z0"], sp["z1"])[0], desc=f"the bridge-ring bearing's spider, on bridge ring {s_}")
            self.put(f"{s_}_ring_adapter", "ring_adapter", None, None, None, "stator", "bearings", join=f"ring-{s_}",
                     dz=mz(s_, ad["z0"], ad["z1"])[0], desc=f"the spider's rim to bridge ring {s_}'s outer face")

    def mount_protos(self, ML, dk, ri, ro, t, hs, hw, per, n_sec):
        """the capacitors' mounts' prototypes (sim/doubler_caps.py, PROPOSED): the Ca plates with their comb's tabs
        (each placed turned to its comb's first post), the rotor vanes with their dowel holes (the first with its
        posts' countersinks), the stator vanes with their lugs, the posts, the standoffs, the spacers, the rods, the
        nuts, the end ring, the Ca|reluctance spider grown to the cage, and the can's disc with its three holes.
        Countersinks face away from the plate's working gap; side A's prototypes carry them on their local z = t
        face where the part's h0 face is meant (z falls as h grows on side A) [IR]."""
        import doubler_caps as DC
        from OCP.BRepPrimAPI import BRepPrimAPI_MakeCone
        from OCP.gp import gp_Ax2, gp_Pnt, gp_Dir
        M = self.mounts
        tab = DC.tab_outline()
        lug = DC.lug_outline()
        rotz = lambda P, a: [(x * math.cos(math.radians(a)) - y * math.sin(math.radians(a)),
                              x * math.sin(math.radians(a)) + y * math.cos(math.radians(a))) for x, y in P]
        pol = lambda r, a: (r * math.cos(math.radians(a)), r * math.sin(math.radians(a)))

        def csk(x, y, face, d_hole=DC.HOLE_D, d_top=DC.CSK_D):
            """a 90-degree countersink cone from the face (0: z = 0, 1: z = t) into the plate."""
            h = 0.5 * (d_top - d_hole) + 0.02
            z_f, up = (-0.01, 1) if face == 0 else (t + 0.01, -1)
            return BRepPrimAPI_MakeCone(gp_Ax2(gp_Pnt(x, y, z_f), gp_Dir(0, 0, up)), 0.5 * d_top + 0.01, 0.5 * d_hole, h).Shape()

        def plate(tabs, holes, csks=(), extra=()):
            """an annulus ri-ro, its tabs at tabs (deg), the holes [(x, y, d)], the countersinks [(x, y, face)]."""
            s = fuse([sector(ri, ro, 0.0, t)] + [prism(rotz(tab, a), 0.0, t) for a in tabs])
            cuts = [cyl_z(x, y, 0.5 * d, -1.0, t + 1.0) for x, y, d in list(holes) + list(extra)]
            cuts += [csk(x, y, f) for x, y, f in csks]
            return _cut(s, *cuts)
        A3 = (0.0, 120.0, 240.0)
        P3 = [pol(DC.R_POST, a) for a in A3]
        holes = [(x, y, DC.HOLE_D) for x, y in P3]
        h0f = lambda s_: 1 if s_ == "A" else 0        # the local face at a part's h0 (toward the hub)
        h1f = lambda s_: 0 if s_ == "A" else 1
        self.proto("ca_n1", lambda: plate(A3, holes), COL["fixed plate"], "Al plate, Ca's node-1 comb (three tabs)")
        self.proto("ca_n2", lambda: plate(A3, holes), COL["fixed plate"], "Al plate, Ca's node-2 comb (three tabs)")
        land = self._landings(ML, dk)
        for s_ in "AB":
            q = M["sides"][s_]
            # Ca_05: countersunk under posts 1 and 2; post 0 plain (the riser's lug under its button head)
            self.proto(f"ca_n1_end_{s_}", lambda s_=s_: plate(A3, holes, [(x, y, h0f(s_)) for x, y in P3[1:]]),
                       COL["fixed plate"], "Al plate, Ca's node-1 comb, its end (Ca_05)")
            self.proto(f"ca_n2_end_{s_}", lambda s_=s_: plate(A3, holes, [(x, y, h1f(s_)) for x, y in P3]),
                       COL["fixed plate"], "Al plate, Ca's node-2 comb, its end (Ca_02)")
            jt = land[s_]["tap"]
            a_t = _ang(jt) - q["theta_n2_deg"][0]
            r_t = float(np.hypot(jt[0], jt[1]))
            xt, yt = pol(r_t, a_t)
            self.proto(f"ca_n2_base_{s_}", lambda s_=s_, xt=xt, yt=yt: plate(A3, holes, [(xt, yt, h1f(s_))],
                                                                              extra=[(xt, yt, DC.HOLE_D)]),
                       COL["fixed plate"], "Al plate, Ca's node-2 comb, its base (Ca_06) on the standoffs; the tap's hole")
            th1 = [a for a in q["theta_n1_deg"]]
            self.proto(f"rotor_vane_end_{s_}", lambda s_=s_, th1=th1: _cut(
                fuse([sector(ri, ro, 0.0, t, k * per - hw, self.p["wr_deg"]) for k in range(n_sec)] + [sector(S.SLEEVE_R, ri, 0.0, t)]),
                *[cyl_z(*pol(DC.DOWEL_R, a), 0.5 * DC.DOWEL_D, -1.0, t + 1.0) for a in DC.DOWEL_TH],
                *[cyl_z(*pol(DC.R_POST, a), 0.5 * DC.HOLE_D, -1.0, t + 1.0) for a in th1],
                *[csk(*pol(DC.R_POST, a), h1f(s_)) for a in th1]),
                COL["rotor vane"], "Al vane, the first (r01): the node-1 comb's posts' countersinks, the dowels' holes")
        self.proto("rotor_vane_m", lambda: _cut(
            fuse([sector(ri, ro, 0.0, t, k * per - hw, self.p["wr_deg"]) for k in range(n_sec)] + [sector(S.SLEEVE_R, ri, 0.0, t)]),
            *[cyl_z(*pol(DC.DOWEL_R, a), 0.5 * DC.DOWEL_D, -1.0, t + 1.0) for a in DC.DOWEL_TH]),
            COL["rotor vane"], "Al vane, its hub ring drilled for the three dowels")
        self.proto("stator_vane_m", lambda: _cut(
            fuse([sector(ri, ro, 0.0, t, k * per - hs, self.p["ws_deg"]) for k in range(n_sec)] + [sector(ro, ro + 12.0, 0.0, t)]
                 + [prism(rotz(lug, a), 0.0, t) for a in DC.LUG_TH]),
            *[cyl_z(*pol(DC.ROD_R, a), 0.5 * DC.ROD_HOLE, -1.0, t + 1.0) for a in DC.LUG_TH]),
            COL["stator vane"], "Al vane, six lugs on its ring for the tie rods")
        cdi = M["can_disc"]
        self.proto("can_disc_m", lambda: _cut(sector(cdi["r0"], cdi["r1"], 0.0, cdi["h1"] - cdi["h0"]),
                                              *[cyl_z(x, y, 0.5 * DC.HOLE_D, -1.0, 3.0) for x, y in P3]),
                   COL["can"], "Al end disc of the can, three M4 holes for the standoffs")
        for L in sorted({round(q_["L"], 3) for q_ in M["posts_n1"] + M["posts_n2"] if q_["kind"] == "spacer"}):
            self.proto(f"post_{L:g}", lambda L=L: cyl_z(0.0, 0.0, 0.5 * DC.POST_D, 0.0, L), COL["al"],
                       f"Al spacer EN AW-6082, Ø{DC.POST_D:g} x {L:g}, M4 female")
        self.proto("standoff", lambda: cyl_z(0.0, 0.0, 0.5 * DC.STANDOFF_D, 0.0, DC.STANDOFF_L), COL["steatite"],
                   "glazed steatite C 221 standoff, M4 inserts")
        vs = M["vane_spacers"][0]
        self.proto("vane_spacer", lambda: _cut(sector(S.SLEEVE_R, DC.VSP_R1, 0.0, vs["h1"] - vs["h0"]),
                                               *[cyl_z(*pol(DC.DOWEL_R, a), 0.5 * DC.DOWEL_D, -1.0, 40.0) for a in DC.DOWEL_TH]),
                   COL["g10"], "G10 spacer ring between the rotor vanes, bonded")
        dw = M["dowels"]
        self.proto("dowel", lambda: cyl_z(0.0, 0.0, 0.5 * DC.DOWEL_D - 0.01, 0.0, dw["h1"] - dw["h0"]), COL["g10"],
                   "G10 dowel Ø5, through the rotor vanes and their spacers")
        for L in sorted({round(q_["h1"] - q_["h0"], 3) for q_ in M["stator_spacers"]}):
            self.proto(f"stator_spacer_{L:g}", lambda L=L: _cut(cyl_z(0.0, 0.0, 0.5 * DC.SSP_D, 0.0, L),
                                                                cyl_z(0.0, 0.0, 0.5 * DC.ROD_HOLE, -1.0, L + 1.0)),
                       COL["g10"], f"G10 spacer tube Ø{DC.SSP_D:g} / {DC.ROD_HOLE:g} x {L:g} on a tie rod")
        rd = M["rods"]
        self.proto("tie_rod", lambda: cyl_z(0.0, 0.0, 0.5 * DC.ROD_D, 0.0, rd["h1"] - rd["h0"]), COL["rod"],
                   "G10-class glass-epoxy threaded rod M8")
        af, hn = DC.NUT
        hexa = [(af / math.sqrt(3.0) * math.cos(math.radians(30 + 60 * k)), af / math.sqrt(3.0) * math.sin(math.radians(30 + 60 * k)))
                for k in range(6)]
        self.proto("rod_nut", lambda: _cut(prism(hexa, 0.0, hn), cyl_z(0.0, 0.0, 0.5 * DC.ROD_D, -1.0, hn + 1.0)),
                   COL["rod"], "G10-class glass-epoxy nut M8")
        er = M["end_ring"]
        self.proto("end_ring", lambda: _cut(sector(er["r0"], er["r1"], 0.0, er["h1"] - er["h0"]),
                                            *[cyl_z(*pol(DC.ROD_R, a), 0.5 * DC.ROD_HOLE, -1.0, 20.0) for a in DC.LUG_TH]),
                   COL["g10"], "G10 end ring in the cage's bore, under the first stator vane")
        B = S.BEARING
        sp = M["spider"]
        self.proto("spider_rel", lambda: _cut(sector(0.5 * B["od"], sp["r1"], 0.0, B["spider_t"]),
                                              *[cyl_z(*pol(DC.ROD_R, a), 0.5 * DC.ROD_HOLE, -1.0, 20.0) for a in DC.LUG_TH]),
                   COL["g10"], "G10 bearing spider, the Ca|reluctance one, grown to the cage for the tie rods")

    def mount_parts(self, mp):
        """the mounts' parts placed, both sides (h mirrored; each side's posts at its own angles)."""
        M = self.mounts
        import doubler_caps as DC
        for s_ in "AB":
            q = M["sides"][s_]
            n1, n2 = mp[s_]("1"), mp[s_]("2")
            for comb, segs, ths, net_ in (("1", M["posts_n1"], q["theta_n1_deg"], n1), ("2", M["posts_n2"], q["theta_n2_deg"], n2)):
                for k, th in enumerate(ths):
                    for j, sg in enumerate(segs):
                        z0, z1 = self.zs(s_, sg["h0"], sg["h1"])
                        if sg["kind"] == "standoff":
                            top, bot = self.zz(s_, sg["h1"]), self.zz(s_, sg["h0"])
                            u = _u(th) * DC.R_POST
                            self.put(f"{s_}_standoff_{k + 1}", "standoff", None, None, None, "rotor", f"side-{s_}",
                                     join=f"ca2-{s_}", net={"nets": [net_, "0"], "axis": [(u + [0, 0, top]).tolist(),
                                                                                         (u + [0, 0, bot]).tolist()]},
                                     dx=DC.R_POST, rot=th, dz=z0,
                                     desc=f"node {net_}'s standoff {k + 1}: glazed steatite, Ca_06 on the can's disc (REF)")
                        else:
                            self.put(f"{s_}_post{comb}_{k + 1}_{j + 1}", f"post_{round(sg['L'], 3):g}", None, None, None,
                                     "rotor", f"side-{s_}", join=f"ca{comb}-{s_}", net=net_, dx=DC.R_POST, rot=th, dz=z0,
                                     desc=f"node {net_}'s post {k + 1}, spacer {j + 1}: {sg['below']} to {sg['above']}")
            for j, vs in enumerate(M["vane_spacers"]):
                z0, _ = self.zs(s_, vs["h0"], vs["h1"])
                self.put(f"{s_}_vane_spacer_{j + 1}", "vane_spacer", None, None, None, "rotor", f"side-{s_}", join="rotor-core",
                         dz=z0, desc=f"the G10 spacer ring between rotor vanes {2 * j + 1} and {2 * j + 3}, bonded")
            dw = M["dowels"]
            z0, _ = self.zs(s_, dw["h0"], dw["h1"])
            for k, th in enumerate(DC.DOWEL_TH):
                self.put(f"{s_}_dowel_{k + 1}", "dowel", None, None, None, "rotor", f"side-{s_}", join="rotor-core",
                         dx=DC.DOWEL_R, rot=th, dz=z0, desc="a G10 dowel through the rotor vanes and their spacers")
            rd = M["rods"]
            for k, th in enumerate(DC.LUG_TH):
                for j, ss in enumerate(M["stator_spacers"]):
                    z0, _ = self.zs(s_, ss["h0"], ss["h1"])
                    self.put(f"{s_}_stator_spacer_{k + 1}_{j + 1}", f"stator_spacer_{round(ss['h1'] - ss['h0'], 3):g}", None,
                             None, None, "stator", f"side-{s_}", join="cage", dx=DC.ROD_R, rot=th, dz=z0,
                             desc=f"a G10 spacer tube on tie rod {k + 1}")
                z0, _ = self.zs(s_, rd["h0"], rd["h1"])
                self.put(f"{s_}_tie_rod_{k + 1}", "tie_rod", None, None, None, "stator", f"side-{s_}", join="cage",
                         dx=DC.ROD_R, rot=th, dz=z0, desc="a glass-epoxy tie rod M8: the end ring, the stator vanes, the spider")
                for j, (a_, b_) in enumerate(rd["nuts"]):
                    z0, _ = self.zs(s_, a_, b_)
                    self.put(f"{s_}_rod_nut_{k + 1}_{j + 1}", "rod_nut", None, None, None, "stator", f"side-{s_}", join="cage",
                             dx=DC.ROD_R, rot=th, dz=z0, desc="a glass-epoxy nut M8")
            er = M["end_ring"]
            z0, _ = self.zs(s_, er["h0"], er["h1"])
            self.put(f"{s_}_end_ring", "end_ring", None, None, None, "stator", f"side-{s_}", join="cage", dz=z0,
                     desc="the G10 end ring in the cage's bore: the stator stack's foot")

    def _landings(self, ML, dk):
        """per side, where the riser and the tap leave their junctions (two on one junction land 2.5 mm either side of
        its centre, along the lane), as decks() lands them."""
        mirror = ML.MIRROR
        out = {}
        for s_ in "AB":
            mp = (lambda n: n) if s_ == "A" else (lambda n: mirror[n])
            J = {n: np.array([x, y, 0.0]) for n, (x, y) in dk[s_]["junctions"].items()}
            jname = lambda b, mp=mp: mp(b.rstrip("'")) + ("'" if b.endswith("'") else "")
            land = {}
            for a_, b_ in ML.LEADS_A:
                land.setdefault(jname(b_), []).append(("lead", a_))
            n1, n2 = mp("1"), mp("2")
            land.setdefault(n1, []).append(("riser", None))
            land.setdefault(n2, []).append(("tap", None))

            def landing(n, who, J=J, land=land):
                lst = land[n]
                if len(lst) == 1:
                    return J[n]
                th = math.radians(_ang(J[n]))
                tv = np.array([-math.sin(th), math.cos(th), 0.0])
                return J[n] + (-2.5 if lst.index(who) == 0 else 2.5) * tv
            out[s_] = dict(riser=landing(n1, ("riser", None)), tap=landing(n2, ("tap", None)))
        return out

    def decks(self, ML, dk, st, kinds, one, mp, plan, th_lead, hv0):
        P, zone = dk["parts"], dk["zone"]
        h_face = zone["parts_absz_mm"][0]                       # 36: the plate's outer face
        dpl = one("deck plate")
        holes = [dk["A"]["junctions"][n] for n in ("l1", "r1")]  # the cross nets (deck B's l1 / r1 sit over deck A's)
        tpl = dpl["h1"] - dpl["h0"]
        self.proto("deck_plate", lambda: _cut(sector(dpl["r0"], dpl["r1"], 0.0, tpl),
                                              *[cyl_z(x, y, 3.0, -1.0, tpl + 1.0) for x, y in holes]),
                   COL["g10"], "G10 deck plate, 6 mm, the cross nets' holes 6 mm")
        # the prototypes, each centred on its own mid-height so one serves both decks (side A's parts hang below)
        for kind in ("stick", "rsurge"):
            q = P[kind]
            rad, bl, br = 0.5 * q["d"], q["body_l"], 0.5 * q["body_d"]
            half = 0.5 * q["l"] - rad
            body = lambda bl=bl, br=br: cyl_between((0, -0.5 * bl, 0), (0, 0.5 * bl, 0), br)
            lead = lambda sg, bl=bl, q=q: cyl_between((0, sg * 0.5 * bl, 0), (0, sg * 0.5 * q["l"], 0), 0.6)
            self.proto(f"{kind}_body", body, COL["stick" if kind == "stick" else "rsurge"], q["what"])
            self.proto(f"{kind}_pot", lambda rad=rad, half=half, body=body, lead=lead: _cut(capsule_y(rad, half), body(),
                                                                                          lead(1), lead(-1)),
                       COL["silicone"], "silicone potting, 8 mm over the part")
            for sg, nm in ((-1, "neg"), (1, "pos")):
                self.proto(f"{kind}_lead_{nm}", lambda sg=sg, lead=lead: lead(sg), COL["cu"], "tinned Cu lead, 1.2 mm")
        for kind in ("c180", "c100", "c100h"):
            q = P[kind]
            rad, L, br, bl = 0.5 * q["d"], q["l"], 0.5 * q["body_d"], q["body_l"]
            self.proto(f"{kind}_body", lambda br=br, bl=bl: cyl_z(0.0, 0.0, br, -0.5 * bl, 0.5 * bl), COL["cap"], q["what"])
            self.proto(f"{kind}_pot", lambda rad=rad, L=L, br=br, bl=bl: _cut(
                cyl_z(0.0, 0.0, rad, -0.5 * L, 0.5 * L), cyl_z(0.0, 0.0, br, -0.5 * bl, 0.5 * bl),
                cyl_z(0.0, 0.0, STUD_R, 0.5 * bl, 0.5 * L), cyl_z(0.0, 0.0, STUD_R, -0.5 * L, -0.5 * bl)),
                COL["silicone"], "silicone potting, 8 mm over the part")
        pot = ML.POT
        self.proto("stud", lambda: cyl_z(0.0, 0.0, STUD_R, -0.5 * pot, 0.5 * pot), COL["brass"], "brass screw terminal, M5")
        qc = P["clamp"]
        span = math.degrees((qc["l"] - qc["w"]) / ML.R_I)             # the study's arc (sim/multiplier_layout.py plan)
        # a lead from the body's round end to the module's terminal as the plan places it (on the arc), leaving the round
        # end along its radius toward the terminal, 0.7 mm off it
        def cl_lead(end):
            c_end = _u(0.0 if end == 0 else span) * ML.R_I
            term = _u(-math.degrees(0.5 * qc["w"] / ML.R_I) if end == 0 else span + math.degrees(0.5 * qc["w"] / ML.R_I)) * ML.R_I
            u = (term - c_end) / np.linalg.norm(term - c_end)
            return cyl_between(c_end + (0.5 * qc["body_w"] + 0.7) * u, term, 0.6)
        cl_body = lambda: arc_capsule(ML.R_I, span, 0.5 * qc["body_w"], -0.5 * qc["body_h"], 0.5 * qc["body_h"])
        self.proto("clamp_body", cl_body, COL["clamp"], qc["what"])
        self.proto("clamp_pot", lambda: _cut(arc_capsule(ML.R_I, span, 0.5 * qc["w"], -0.5 * qc["h"], 0.5 * qc["h"]), cl_body(),
                                             cl_lead(0), cl_lead(1)), COL["silicone"], "silicone potting, 8 mm over the module")
        for end in (0, 1):
            self.proto(f"clamp_lead_{end}", lambda end=end: cl_lead(end), COL["cu"], "tinned Cu lead, 1.2 mm")
        jr, jl = J_COND
        self.proto("j_cond", lambda: cyl_z(0.0, 0.0, jr, -0.5 * jl, 0.5 * jl), COL["brass"], "brass junction terminal")
        self.proto("j_pot", lambda: _cut(cyl_z(0.0, 0.0, J_POT[0], -0.5 * J_POT[1], 0.5 * J_POT[1]),
                                         cyl_z(0.0, 0.0, jr, -0.5 * jl, 0.5 * jl)),
                   COL["silicone"], "silicone potting, the junction's block")
        h_ax = lambda kind: h_face + 0.5 * (P[kind]["d"] if kind in ("stick", "rsurge") else
                                           P[kind]["h"] if kind == "clamp" else P[kind]["l"])
        j_top = h_face + 0.5 * P["stick"]["d"] + 0.5 * jl            # 54: a junction terminal's outer face
        j_in = h_face + 0.5 * P["stick"]["d"] - 0.5 * jl             # 42: its face toward the hub
        for s_ in "AB":
            g, jn = f"deck-{s_}", f"deck-{s_}"
            z0, _ = self.zs(s_, dpl["h0"], dpl["h1"])
            self.put(f"{s_}_deck_plate", "deck_plate", None, None, None, "rotor", g, join=f"plate-{s_}", dz=z0,
                     desc=f"deck {s_}: the G10 plate round the can, r 50-150, |z| 30-36")
            J = {n: np.array([x, y, 0.0]) for n, (x, y) in dk[s_]["junctions"].items()}
            tag = lambda n: n.replace("'", "p")
            for n, c in J.items():
                r_, th = float(np.hypot(c[0], c[1])), _ang(c)
                self.put(f"{s_}_J_{tag(n)}", "j_cond", None, None, None, "rotor", g, join=jn, net=n.rstrip("'"), dx=r_, rot=th,
                         dz=self.zz(s_, h_ax("stick")), desc=f"junction {n}: brass terminal in its potted block")
                self.put(f"{s_}_J_{tag(n)}_pot", "j_pot", None, None, None, "rotor", g, join=jn, dx=r_, rot=th,
                         dz=self.zz(s_, h_ax("stick")), desc=f"junction {n}: potting")
            for q in dk[s_]["parts"]:
                nm, kind, (na, nb) = q["name"], q["kind"], q["nets"]
                c = np.array([q["centre"][0], q["centre"][1], 0.0])
                r_c, th_c = float(np.hypot(c[0], c[1])), _ang(c)
                dev = {"stick": nm, "clamp": nm}.get(kind)
                if q["orient"] == "tan":
                    zax = self.zz(s_, h_ax(kind))
                    b0, b1 = (np.array([x, y, zax]) for x, y in q["body_pts"])
                    body_net = {"nets": [na, nb], "axis": [b0.tolist(), b1.tolist()]}
                    if dev:
                        body_net["device"] = dev
                    self.put(f"{s_}_{nm}_body", f"{kind}_body", None, None, None, "rotor", g, join=f"{s_}_{nm}_body",
                             net=body_net, dx=r_c, rot=th_c, dz=zax, desc=f"{nm} ({na} - {nb}): {P[kind]['what']}")
                    self.put(f"{s_}_{nm}_pot", f"{kind}_pot", None, None, None, "rotor", g, join=jn, dx=r_c, rot=th_c, dz=zax,
                             desc=f"{nm}: its potted housing")
                    tvec = np.array([-math.sin(math.radians(th_c)), math.cos(math.radians(th_c)), 0.0])
                    tip_neg = c - 0.5 * P[kind]["l"] * tvec
                    T0 = np.array([*q["terminals"][0], 0.0])
                    k_neg = 0 if np.linalg.norm(tip_neg - T0) < 1e-6 else 1          # which net the local -y end holds
                    for sg, end_nm in ((-1, "neg"), (1, "pos")):
                        k = k_neg if sg < 0 else 1 - k_neg
                        self.put(f"{s_}_{nm}_lead_{end_nm}", f"{kind}_lead_{end_nm}", None, None, None, "rotor", g, join=jn,
                                 net=(na, nb)[k], dx=r_c, rot=th_c, dz=zax, desc=f"{nm}: its lead, net {(na, nb)[k]}")
                        T = np.array([*q["terminals"][k], 0.0])
                        jn_ = min(J, key=lambda n: np.linalg.norm(J[n] - T))
                        self.put_wire(f"{s_}_{nm}_to_{tag(jn_)}", [T + [0, 0, zax], J[jn_] + [0, 0, zax]], jn_.rstrip("'"), g, jn,
                                      colour=COL["cu"], material="tinned Cu lead, in the potting",
                                      desc=f"{nm}'s lead to junction {jn_}")
                elif q["orient"] == "up":
                    zc_ = self.zz(s_, h_ax(kind))
                    L, bl = P[kind]["l"], P[kind]["body_l"]
                    top, foot = self.zz(s_, h_face + 0.5 * L + 0.5 * bl), self.zz(s_, h_face + 0.5 * L - 0.5 * bl)
                    self.put(f"{s_}_{nm}_body", f"{kind}_body", None, None, None, "rotor", g, join=f"{s_}_{nm}_body",
                             net={"nets": [na, nb], "axis": [(c + [0, 0, top]).tolist(), (c + [0, 0, foot]).tolist()]},
                             dx=r_c, rot=th_c, dz=zc_, desc=f"{nm} ({na} at its top, {nb} at its foot): {P[kind]['what']}")
                    self.put(f"{s_}_{nm}_pot", f"{kind}_pot", None, None, None, "rotor", g, join=jn, dx=r_c, rot=th_c, dz=zc_,
                             desc=f"{nm}: its potted housing")
                    for end_nm, net_, hz in (("top", na, h_face + L - 0.5 * pot), ("foot", nb, h_face + 0.5 * pot)):
                        self.put(f"{s_}_{nm}_stud_{end_nm}", "stud", None, None, None, "rotor", g, join=jn, net=net_, dx=r_c,
                                 rot=th_c, dz=self.zz(s_, hz), desc=f"{nm}: its {end_nm} terminal, net {net_}")
                else:                                                      # the clamp module along its arc
                    a0, a1 = _ang(q["pts"][0]), _ang(q["pts"][-1])
                    d_ = (a1 - a0 + 540.0) % 360.0 - 180.0
                    rot_ = a0 if d_ > 0 else a1                            # the arc's lower end
                    hv_local0 = d_ > 0                                     # its first terminal (net 1 / 4) at local 0
                    zc_ = self.zz(s_, h_ax(kind))
                    th_t = [_ang(x) for x in q["terminals"]]
                    self.put(f"{s_}_{nm}_body", "clamp_body", None, None, None, "rotor", g, join=f"{s_}_{nm}_body",
                             net={"nets": [na, nb], "arc": dict(r=ML.R_I, th=th_t, z=zc_), "device": nm},
                             rot=rot_, dz=zc_, desc=f"{nm} ({na} - {nb}): {P[kind]['what']}")
                    self.put(f"{s_}_{nm}_pot", "clamp_pot", None, None, None, "rotor", g, join=jn, rot=rot_, dz=zc_,
                             desc=f"{nm}: its potted housing")
                    for end in (0, 1):
                        k = end if hv_local0 else 1 - end
                        self.put(f"{s_}_{nm}_lead_{end}", f"clamp_lead_{end}", None, None, None, "rotor", g, join=jn,
                                 net=(na, nb)[k], rot=rot_, dz=zc_, desc=f"{nm}: its lead, net {(na, nb)[k]}")
            # the leads over the parts (sim/multiplier_layout.py LEADS_A, mirrored), each landing on its junction's
            # outer face; two on one junction land 2.5 mm either side of its centre, along the lane
            pm = (lambda n: n) if s_ == "A" else (lambda n: ML.PART_MIRROR[n])
            jname = lambda b: mp[s_](b.rstrip("'")) + ("'" if b.endswith("'") else "")
            land = {}
            for a_, b_ in ML.LEADS_A:
                land.setdefault(jname(b_), []).append(("lead", a_))
            n1, n2 = mp[s_]("1"), mp[s_]("2")
            land.setdefault(n1, []).append(("riser", None))
            land.setdefault(n2, []).append(("tap", None))

            def landing(n, who):
                lst = land[n]
                if len(lst) == 1:
                    return J[n]
                th = math.radians(_ang(J[n]))
                tv = np.array([-math.sin(th), math.cos(th), 0.0])
                return J[n] + (-2.5 if lst.index(who) == 0 else 2.5) * tv
            zh = lambda h: np.array([0.0, 0.0, self.zz(s_, h)])
            for a_, b_ in ML.LEADS_A:
                nm, k = a_.split(":")
                q = plan[s_][pm(nm)]
                n = jname(b_)
                Jp = landing(n, ("lead", a_))
                c = np.array([q["centre"][0], q["centre"][1], 0.0])
                if q["orient"] == "up" and int(k) == 0:
                    pts = [c + zh(h_face + P[q["kind"]]["l"]), c + zh(Z_OVER)]
                elif q["orient"] == "up":
                    u = (Jp - c) / np.linalg.norm(Jp - c)
                    e_ = c + (0.5 * P[q["kind"]]["d"] + 2.5) * u
                    pts = [c + zh(h_face + 0.5 * pot), e_ + zh(h_face + 0.5 * pot), e_ + zh(Z_OVER)]
                else:
                    T = np.array([*q["terminals"][int(k)], 0.0])
                    pts = [T + zh(h_ax(q["kind"])), T + zh(Z_OVER)]
                pts += [Jp + zh(Z_OVER), Jp + zh(j_top)]
                self.put_wire(f"{s_}_lead_{pm(nm)}_{k}", pts, n.rstrip("'"), g, jn,
                              desc=f"lead: {pm(nm)}'s terminal {k} to junction {n}, over the parts")
            # the REF straps to the can (sim/multiplier_layout.py STRAPS_A)
            for a_, _ in ML.STRAPS_A:
                nm, k = a_.split(":")
                q = plan[s_][pm(nm)]
                if q["orient"] == "up":
                    T, h0 = np.array([q["centre"][0], q["centre"][1], 0.0]), h_face + 0.5 * pot
                else:
                    T, h0 = np.array([*q["terminals"][int(k)], 0.0]), h_ax(q["kind"])
                h_s = h_face + WIRE_R + 0.5
                pts = [T + zh(h0), T + zh(h_s), T / np.linalg.norm(T) * ML.CAN_R + zh(h_s)]
                self.put_wire(f"{s_}_strap_{pm(nm)}", pts, "0", g, jn, colour=COL["cu"], material="Cu strap to the can (REF)",
                              desc=f"REF strap: {pm(nm)}'s terminal {k} to the can")
            # node 1's riser (4 on side B) and node 2's tap (3): from their junctions' outer faces out of the deck
            Jr, Jt = landing(n1, ("riser", None)), landing(n2, ("tap", None))
            u1 = J[n1] / np.linalg.norm(J[n1])
            hr = 0.5 * (st["h_parts_mm"] + st["h_col_mm"]) + 4.0      # docs/make_multiplier_layout.py's riser height
            self.put_wire(f"{s_}_riser_deck", [Jr + zh(j_top), Jr + zh(POST)], n1, g, jn, desc=f"node {n1}'s riser, in the potting")
            h_end = self.mounts["riser_end_h"] if self.mounts else hv0
            self.put_wire(f"{s_}_riser", [Jr + zh(POST), Jr + zh(hr), u1 * R_RISER + zh(hr), u1 * R_RISER + zh(h_end)], n1,
                          "wiring", f"riser-{s_}",
                          desc=(f"node {n1}'s riser: up from the deck, in to r 35, up the column's bore to its comb's first "
                                "post, under Ca_05" if self.mounts else
                                f"node {n1}'s riser: up from the deck, in to r 35, up the column's bore to the first rotor vane"))
            self.put_wire(f"{s_}_tap_deck", [Jt + zh(j_top), Jt + zh(POST)], n2, g, jn, desc=f"node {n2}'s tap, in the potting")
            self.put_wire(f"{s_}_tap", [Jt + zh(POST), Jt + zh(st["h_col_mm"])], n2, "wiring", f"tap-{s_}",
                          desc=f"node {n2}'s tap: up from the deck to the column's node-{n2} plate")
            if self.mounts:
                # the riser's lug under the first node-1 post and the tap's under Ca_06, each in a silicone boot
                import doubler_caps as DC
                br, bh = DC.BOOT
                for nm_, xy, h1, net_, jn_ in (("riser", u1 * R_RISER, h_end, n1, f"riser-{s_}"),
                                               ("tap", Jt, st["h_col_mm"], n2, f"tap-{s_}")):
                    z0, _ = self.zs(s_, h1 - bh, h1)
                    self.put(f"{s_}_{nm_}_boot", "boot", lambda br=br, bh=bh: cyl_z(0.0, 0.0, br, 0.0, bh), COL["silicone"],
                             "silicone potting: a boot over the lug's joint", "rotor", "wiring", join=jn_,
                             dx=float(np.hypot(xy[0], xy[1])), rot=_ang(xy), dz=z0,
                             desc=f"the {nm_}'s ring lug and its screw, in a silicone boot (node {net_})")
            # ring A's lead (B's): from its equatorial bead along the normal through the PEEK and the coupler, along the
            # coupler, out through the can's bushing to Csa (Csb) [docs/rings-design.md §2; sim/multiplier-layout-findings.md §5]
            H = json.load(open(os.path.join(ROOT, "presets", "hub-locked.json")))
            rg, Ro = H["rings"]["value"], 0.5 * H["vessel"]["value"]["od_mm"]
            te, rho = math.radians(rg["equatorial_edge_deg"]), 0.5 * rg["bead_d_mm"]["equatorial"]
            sg = -1 if s_ == "A" else 1
            th = math.radians(th_lead[s_])
            u3 = np.array([math.sin(te) * math.cos(th), math.sin(te) * math.sin(th), sg * math.cos(te)])
            hub0 = np.array([0.0, 0.0, self.zc])
            p1, p2 = hub0 + (Ro + 2.0 * rho) * u3, hub0 + (33.0 / math.sin(te)) * u3
            ul = _u(th_lead[s_])
            p3 = ul * LEAD_R + [0.0, 0.0, p2[2]]
            p4, p5 = ul * LEAD_R + zh(LEAD_Z), ul * (48.0 + 0.5 * BUSH[2]) + zh(LEAD_Z)
            ring = "ea" if s_ == "A" else "eb"
            self.put_wire(f"{s_}_ring_lead", [p1, p2, p3, p4, p5], ring, "wiring", f"ring-{s_}",
                          desc=f"ring {s_}'s lead: from its equatorial bead through the PEEK and the coupler, along the "
                               "coupler, out through the can's PTFE bushing")
            cs = plan[s_]["Csa" if s_ == "A" else "Csb"]
            c = np.array([cs["centre"][0], cs["centre"][1], 0.0])
            self.put_wire(f"{s_}_ring_lead_deck", [p5, ul * (48.0 + 0.5 * BUSH[2] + 2.0) + zh(LEAD_Z),
                                                   c + zh(h_face + P[cs["kind"]]["l"])], ring, g, jn,
                          desc=f"ring {s_}'s lead on the deck, to {cs['name']}'s top")
        # the cross nets l1 and r1: straight across between the decks, through the plates' holes
        for n in ("l1", "r1"):
            c = np.array([*dk["A"]["junctions"][n], 0.0])
            za, zb = lambda h: c + [0.0, 0.0, self.zz("A", h)], lambda h: c + [0.0, 0.0, self.zz("B", h)]
            self.put_wire(f"A_cross_{n}", [za(j_in), za(h_face)], n, "deck-A", "deck-A", desc=f"the cross net {n}, in deck A's potting")
            self.put_wire(f"cross_{n}", [za(h_face), zb(h_face)], n, "wiring", f"cross-{n}",
                          desc=f"the cross net {n}: PTFE HV wire straight across between the decks")
            self.put_wire(f"B_cross_{n}", [zb(h_face), zb(j_in)], n, "deck-B", "deck-B", desc=f"the cross net {n}, in deck B's potting")


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
    rotor = [(pt, s) for pt, s in shapes if pt["body"] == "rotor" and pt["name"] not in ("shaft",)]
    stator = [(pt, s) for pt, s in shapes if pt["body"] == "stator"]
    from OCP.BRepPrimAPI import BRepPrimAPI_MakeRevol
    for pr, sr in rotor:
        if pr["proto"].startswith(("shaft", "sleeve", "flange")):
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
    if any(pt["proto"].startswith("wu_core") for pt in m.parts):
        res["G-TUBE-WOUND"] = wound_checks(m, shapes, log)
    if not any(pt["proto"] == "cem_core" for pt in m.parts):
        return res
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


def compound(shapes):
    from OCP.BRep import BRep_Builder
    from OCP.TopoDS import TopoDS_Compound
    b, c = BRep_Builder(), TopoDS_Compound()
    b.MakeCompound(c)
    for s in shapes:
        b.Add(c, s)
    return c


def layout_checks(m, log=print):
    """G-LAYOUT: the solids against the study (sim/multiplier_layout.py, its results). Per deck, every pair of parts:
    the housings' and the bodies' least distance in 3-D against the plan's (the study's housings as capsules and arcs,
    its bodies of their radius along their axes) -- the solids may only be farther apart, the clamp's true arc within
    its 9-point polyline's sagitta (0.22 mm); the least housing gap and its pair; every body to the can. The stack's
    gaps: the column's node-2 plate to the deck's parts, deck A's conductors to deck B's, the decks to the cage, the
    riser to the node-2 plates' bores."""
    import multiplier_layout as ML
    from OCP.BRepExtrema import BRepExtrema_DistShapeShape
    by = {pt["name"]: pt for pt in m.parts}
    shp = {}

    def S_(n):
        if n not in shp:
            shp[n] = m.placed(by[n])
        return shp[n]

    def dist(a, b):
        d = BRepExtrema_DistShapeShape(a, b); d.Perform()
        return float(d.Value())
    P, out, ok = m.lay["decks"]["parts"], {}, True
    tol = 0.25
    body_r = lambda q: 0.5 * (P[q["kind"]].get("body_d") or P[q["kind"]]["body_w"])
    for s_ in "AB":
        parts = m.lay["decks"][s_]["parts"]
        rows = []
        for i, a in enumerate(parts):
            for b in parts[i + 1:]:
                ph = ML.poly_dist(a["pts"], b["pts"]) - a["rad"] - b["rad"]
                pb = ML.poly_dist(a["body_pts"], b["body_pts"]) - body_r(a) - body_r(b)
                sh = dist(S_(f"{s_}_{a['name']}_pot"), S_(f"{s_}_{b['name']}_pot"))
                sb = dist(S_(f"{s_}_{a['name']}_body"), S_(f"{s_}_{b['name']}_body"))
                rows.append(dict(a=a["name"], b=b["name"], plan_housing_mm=ph, solid_housing_mm=sh, plan_body_mm=pb,
                                 solid_body_mm=sb))
        dh = min(r["solid_housing_mm"] - max(r["plan_housing_mm"], 0.0) for r in rows)
        db = min(r["solid_body_mm"] - r["plan_body_mm"] for r in rows)
        least = min(rows, key=lambda r: r["solid_housing_mm"])
        study = m.lay["decks"]["checks"][s_]["min_housing_gap"]
        can = m.placed(by["can"])
        to_can = {q["name"]: dist(S_(f"{s_}_{q['name']}_body"), can) for q in parts}
        plan_can = {}
        for q in parts:
            pts = [np.asarray(x) for x in q["body_pts"]]
            if len(pts) == 2:
                pts = [pts[0] + (pts[1] - pts[0]) * k / 40.0 for k in range(41)]
            plan_can[q["name"]] = min(float(np.linalg.norm(x)) for x in pts) - body_r(q) - ML.CAN_R
        dc = min(to_can[n] - plan_can[n] for n in to_can)
        same = [r for r in rows if {r["a"], r["b"]} == {study["a"], study["b"]}][0]
        good = dh >= -tol and db >= -tol and dc >= -tol and abs(same["solid_housing_mm"] - study["housing_gap_mm"]) < 0.05 \
            and least["solid_housing_mm"] >= study["housing_gap_mm"] - 0.05          # a tie (C8 under r2) may name another pair
        ok &= good
        out[s_] = dict(pairs=len(rows), housing_solid_minus_plan_min_mm=dh, body_solid_minus_plan_min_mm=db,
                       least_housing=dict(pair=f"{least['a']}-{least['b']}", solid_mm=least["solid_housing_mm"],
                                          study_pair=f"{study['a']}-{study['b']}", study_mm=study["housing_gap_mm"]),
                       body_to_can_mm={n: round(v, 2) for n, v in to_can.items()}, can_solid_minus_plan_min_mm=dc,
                       rows=rows, pass_=bool(good))
        log(f"G-LAYOUT deck {s_}: {len(rows)} pairs; housings solid - plan >= {dh:+.3f} mm, bodies >= {db:+.3f} mm, the can "
            f">= {dc:+.3f} mm; least housing gap {least['a']}-{least['b']} {least['solid_housing_mm']:.2f} mm (the study "
            f"{study['a']}-{study['b']} {study['housing_gap_mm']:.2f}); {good}")
    # the stack's gaps
    deck = lambda s_: [n for n, pt in by.items() if pt["group"] == f"deck-{s_}"]
    hv = lambda s_: [n for n in deck(s_) if n in m.nets and not n.endswith("_plate") and "cross" not in n
                     and "riser" not in n and "tap" not in n]
    st = m.lay["stack"]
    col2 = {"A": "A_Ca_06", "B": "B_Cb_06"}
    g = {}
    for s_ in "AB":
        g[f"column {s_}: node-{'2' if s_ == 'A' else '3'} plate to the deck's parts"] = (
            dist(S_(col2[s_]), compound([S_(n) for n in deck(s_) if "riser" not in n and "tap" not in n])), st["c_col_mm"])
        g[f"the riser {s_} to the column's plates (their bores)"] = (
            dist(S_(f"{s_}_riser"), compound([S_(n) for n in by if n.startswith(f"{s_}_C{'a' if s_ == 'A' else 'b'}_")
                                              and m.nets.get(n, {}).get("net") in ("2", "3")])), 13.0)
        g[f"deck {s_} to the cage"] = (dist(compound([S_(n) for n in deck(s_)]), S_("stator_cage")), 12.0)
    g["deck A's conductors to deck B's"] = (dist(compound([S_(n) for n in hv("A")]), compound([S_(n) for n in hv("B")])),
                                           2 * (st["elements"][[e["kind"] for e in st["elements"]].index("deck parts")]["h0"]))
    gaps = {k: dict(solid_mm=round(v, 2), needs_or_study_mm=w, ok=bool(v >= w - 0.05)) for k, (v, w) in g.items()}
    for k, v in gaps.items():
        log(f"G-LAYOUT {k}: {v['solid_mm']} mm (the study / need {v['needs_or_study_mm']}) {v['ok']}")
        ok &= v["ok"]
    out["gaps"] = gaps
    out["pass_"] = bool(ok)
    return out


def wound_checks(m, shapes, log=print):
    """the wound section: the air gap aligned / unaligned, the coil's clearances, the tip arc, the envelope."""
    from OCP.BRepExtrema import BRepExtrema_DistShapeShape
    sp = m.p["rel"]
    by = {pt["name"]: s for pt, s in shapes}
    pts = {pt["name"]: pt for pt, _ in shapes}

    def dist(a, b):
        d = BRepExtrema_DistShapeShape(a, b); d.Perform()
        return round(d.Value(), 4)

    def turned(name, rot):
        pl = dict(pts[name]["place"]); pl["rot"] = pl["rot"] + rot
        return MG.moved(m.protos[pts[name]["proto"]][0], Machine.trsf(pl))
    out, ok = dict(gap_set_mm=sp["g"], clr_set_mm=sp["clr"]), True
    half = 180.0 / sp["n_br"]
    for side in ("A", "B"):
        cores = [f"{side}_U1_core_pos", f"{side}_U1_core_neg"]       # the two half-cores
        bridges = [n for n in by if n.startswith(f"{side}_bridge_") and pts[n]["proto"] == "w_bridge"]
        cd = lambda shape_of, other: min(dist(shape_of(c), other) for c in cores)
        at0 = min(cd(lambda c: by[c], by[b]) for b in bridges)
        turn = half if side == "B" else 0.0              # B is unaligned at rotor angle 0: turn it onto a bridge
        al = min(cd(lambda c: turned(c, turn), by[b]) for b in bridges)
        un = min(cd(lambda c: turned(c, half if side == "A" else 0.0), by[b]) for b in bridges)
        w = f"{side}_U1_winding"
        row = dict(gap_at_rotor_0_mm=at0, gap_aligned_mm=al, gap_unaligned_mm=un,
                   winding_to_core_mm=cd(lambda c: by[c], by[w]), winding_to_strip_mm=dist(by[w], by[f"{side}_U1_strip"]),
                   winding_to_wedge_mm=dist(by[w], by[f"{side}_U1_wedge"]),
                   winding_to_cheek_mm=min(dist(by[w], by[n]) for n in by if n.startswith(f"{side}_U1_cheek")),
                   winding_to_disc_mm=min(dist(by[w], by[n]) for n in by if n.startswith(f"{side}_carrier_disc")),
                   winding_to_ring_mm=dist(by[w], by[f"{side}_bridge_ring"]),
                   core_to_ring_mm=cd(lambda c: by[c], by[f"{side}_bridge_ring"]),
                   half_core_to_half_core_mm=dist(by[cores[0]], by[cores[1]]))
        P = np.vstack([MG.mesh_points(by[c], 0.02) for c in cores])
        row["core_r_max_mm"] = round(float(np.hypot(P[:, 0], P[:, 1]).max()), 3)
        P = MG.mesh_points(by[w], 0.05)
        row["winding_r_max_mm"] = round(float(np.hypot(P[:, 0], P[:, 1]).max()), 2)
        row["winding_r_min_mm"] = round(float(np.hypot(P[:, 0], P[:, 1]).min()), 2)
        ok &= abs(al - sp["g"]) < 2e-3 and un > 5 * sp["g"] and abs(row["winding_to_core_mm"] - sp["clr"]) < 2e-3
        ok &= abs(row["winding_to_strip_mm"] - sp["clr"]) < 2e-3 and row["winding_to_cheek_mm"] >= sp["clr"] - 1e-3
        ok &= row["winding_to_disc_mm"] >= sp["clr"] - 1e-3 and row["winding_to_ring_mm"] > sp["g"]
        ok &= row["core_r_max_mm"] <= sp["r_g"] + 1e-3
        out[side] = row
        log(f"G-TUBE-WOUND {side}: gap aligned {al} mm, unaligned {un} mm; winding to core {row['winding_to_core_mm']} mm")
    env = [e for e in m.el if e["kind"] == "reluctance"]
    out.update(envelope_dia_mm=2 * max(e["r1"] for e in env), section_len_mm=env[0]["z1"] - env[0]["z0"],
               utron_radial_mm=(round(sp["r_g"] - sp["depth"], 2), sp["r_g"]), utron_axial_mm=sp["axial_mm"], pass_=bool(ok))
    return out


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
    used = {pt["proto"] for pt in m.parts}
    for k, (s, c, mat) in m.protos.items():
        if k not in used:                                # a prototype no part places would read back as a free shape
            continue
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


def wound_rel(pick):
    """the wound reluctance section of an operating point (sim/pole_design_variants_op.json, sim/utron_profile.py)."""
    import utron_profile as U
    op = json.load(open(os.path.join(HERE, "pole_design_variants_op.json")))["designs"][pick]
    rows = json.load(open(os.path.join(HERE, "pole_design_variants.json")))["rows"]
    row = [r for r in rows if r["design"] == op["design"]]
    rel = U.spec(op["design"], op["best"], row[0] if row else None)
    rel.update(kind="wound", pick=pick)
    return rel


def record_plates(pick="g 0.5 / 6 bridges / 1200 rpm"):
    """the design of record's inputs to stack_sizing: the air stack of record (sim/air_stack_sizing_results.json, 3 mm
    full-round vanes, 6 + 6), the HV side on the rotor, the locked hub (presets/hub-locked.json), the wound utrons."""
    rec = [q for q in json.load(open(os.path.join(HERE, "air_stack_sizing_results.json")))["thick_vanes"]["compare"]
           if q["t_vaneMm"] == 3.0 and q["n_plates"] == 6][0]
    H = json.load(open(os.path.join(ROOT, "presets", "hub-locked.json")))
    return dict(g_vMm=rec["gap_mm"], n_plates=rec["n_plates"], dielectric="air", t_vaneMm=rec["t_vaneMm"],
                N_sec=2 * rec["sectors"], ws_deg=rec["ws_deg"], wr_deg=rec["wr_deg"], edge=rec["edge"],
                pitch_fixed_mm=rec["gap_mm"] + rec["t_plate_mm"], hv_on_rotor=True, hub="locked",
                hub_mm=2 * H["shaft"]["value"]["flange_absz_mm"][0], bucket=False, rel=wound_rel(pick))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--n-plates", type=int, default=None)
    ap.add_argument("--r-out", type=float, default=None)
    ap.add_argument("--no-step", action="store_true")
    ap.add_argument("--rel", choices=("cem", "wound"), default="cem",
                    help="reluctance section: the designer's C-EMs (default) or the wound utrons + bridges (diode build, geared 1 : -1)")
    ap.add_argument("--pick", default="g 0.5 / 6 bridges / 1200 rpm", help="operating point in sim/pole_design_variants_op.json")
    ap.add_argument("--record", action="store_true",
                    help="the design of record: the air stack of record (sim/air_stack_sizing_results.json: 3 mm full-round "
                         "vanes, 6 + 6, 6 mm gaps), the HV side on the rotor (Ca / Cb on the rotor, the stator vanes REF) and "
                         "the locked hub (presets/hub-locked.json); implies --rel wound")
    ap.add_argument("--layout", action="store_true",
                    help="the multiplier laid out in the machine (sim/multiplier_layout_results.json, PROPOSED): the record "
                         "re-stacked round the decks and the grounded can, no hub-face bearings")
    a = ap.parse_args()
    if a.layout:
        return main_layout(a)
    if a.record:
        a.rel = "wound"
    plates = {}
    if a.n_plates: plates["n_plates"] = a.n_plates
    if a.r_out: plates["r_outMm"] = a.r_out
    results = RESULTS
    if a.rel == "wound":
        rel = wound_rel(a.pick)
        plates.update(bucket=False, rel=rel)
        results = os.path.join(HERE, "tube_geometry_wound_results.json")
    if a.record:
        plates.update(record_plates(a.pick))
        rel = plates["rel"]
        results = os.path.join(HERE, "tube_geometry_record_results.json")
    lad = S.size_stack("tube", plates)
    g = lad["tube_geometry"]
    tag = f"tube-r{lad['tube']['r_outMm']:g}-n{lad['tube']['n_plates']}"
    if a.record:
        tag += f"-air{lad['tube']['g_vMm']:g}"
    if a.rel == "wound":
        d = rel
        tag += f"-wound-g{str(d['g']).replace('.', 'p')}-{d['n_br']}br"
    if a.record:
        tag += "-hub50"
    g["tag"] = tag
    m = Machine(lad).build()
    os.makedirs(OUT_DIR, exist_ok=True)
    print(f"{tag}: {len(m.parts)} placed solids from {len(m.protos)} prototypes", flush=True)
    res = dict(tag=tag, n_parts=len(m.parts), n_protos=len(m.protos), L_total_mm=g["L_total_mm"],
               vane_dia_mm=g["diameter_mm"], C_max_pF=lad["ladder"]["C_max"]["value"], kappa=lad["kappa_C"])
    res.update(checks(m))
    json.dump(dict(parts=[{k: v for k, v in pt.items()} for pt in m.parts], elements=g["elements"]),
              open(os.path.join(OUT_DIR, f"{tag}.parts.json"), "w"), indent=0, default=float)
    res["renders"] = renders_wound(m, OUT_DIR, tag) if a.rel == "wound" else renders(m, OUT_DIR, tag)
    if a.rel == "wound":
        res["rel"] = {k: v for k, v in rel.items() if not isinstance(v, (list, dict))}
    if not a.no_step:
        path = write_step(m, os.path.join(OUT_DIR, f"{tag}.step"))
        res["step"] = os.path.relpath(path, ROOT)
        res["step_bytes"] = os.path.getsize(path)
        res["step_read_back"] = rb = read_back(path)
        res["step_read_back"]["pass_"] = rb["instances"] == len(m.parts)
    json.dump(res, open(results, "w"), indent=1, default=float)
    for k, v in res.items():
        print(k, ":", json.dumps(v, default=float)[:500], flush=True)


def main_layout(a):
    import time
    t0 = time.time()
    log = lambda s: print(s, flush=True)
    m = LayoutMachine(a.pick).build()
    rel = m.p["rel"]
    tag = (f"tube-r{m.p['r_outMm']:g}-n{m.p['n_plates']}-air{m.p['g_vMm']:g}-wound-g{str(rel['g']).replace('.', 'p')}-"
           f"{rel['n_br']}br-hub50-layout")
    m.lad["tube_geometry"]["tag"] = tag
    log(f"{tag}: {len(m.parts)} placed solids from {len(m.protos)} prototypes, {m.L_mm:.0f} mm")
    res = dict(tag=tag, source="sim/multiplier_layout_results.json (the stack, the decks' plans); the record's solids "
                               "(record_plates); presets/hub-locked.json", status="PROPOSED (the layout, 2026-10-11)",
               n_parts=len(m.parts), n_protos=len(m.protos), L_total_mm=m.L_mm, hub_centre_z_mm=m.zc)
    res.update(checks(m, log))
    res["G-LAYOUT"] = layout_checks(m, log)
    json.dump(dict(parts=m.parts, nets=m.nets, zc_mm=m.zc, L_mm=m.L_mm),
              open(os.path.join(OUT_DIR, f"{tag}.parts.json"), "w"), indent=0, default=float)
    res["renders"] = renders_layout(m, OUT_DIR, tag, log)
    if not a.no_step:
        path = write_step(m, os.path.join(OUT_DIR, f"{tag}.step"))
        res["step"] = os.path.relpath(path, ROOT)
        res["step_bytes"] = os.path.getsize(path)
        res["step_read_back"] = rb = read_back(path)
        res["step_read_back"]["pass_"] = rb["instances"] == len(m.parts)
    res["run_s"] = round(time.time() - t0)
    out = os.path.join(HERE, "tube_geometry_layout_results.json")
    json.dump(res, open(out, "w"), indent=1, default=float)
    for k, v in res.items():
        if k != "G-LAYOUT":
            log(f"{k} : {json.dumps(v, default=float)[:400]}")
    log(f"wrote {os.path.relpath(out, ROOT)} ({res['run_s']} s)")



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


def section_faces(shape, plane):
    """the exact planar section of a solid as filled triangles: plane ('y', 0) -> (x, z), ('z', z0) -> (x, y)."""
    from OCP.BRepAlgoAPI import BRepAlgoAPI_Common
    from OCP.BRepBuilderAPI import BRepBuilderAPI_MakeFace
    from OCP.BRepMesh import BRepMesh_IncrementalMesh
    from OCP.BRep import BRep_Tool
    from OCP.TopoDS import TopoDS
    from OCP.TopExp import TopExp_Explorer
    from OCP.TopAbs import TopAbs_FACE
    from OCP.TopLoc import TopLoc_Location
    from OCP.gp import gp_Pln, gp_Pnt, gp_Dir
    ax, v = plane
    pln = gp_Pln(gp_Pnt(0, 0, v if ax == "z" else 0), gp_Dir(0, 0, 1) if ax == "z" else gp_Dir(0, 1, 0))
    c = BRepAlgoAPI_Common(shape, BRepBuilderAPI_MakeFace(pln, -5000, 5000, -5000, 5000).Face()).Shape()
    BRepMesh_IncrementalMesh(c, 0.1, False, 0.2, True)
    tris = []
    e = TopExp_Explorer(c, TopAbs_FACE)
    while e.More():
        f = TopoDS.Face(e.Current()); loc = TopLoc_Location()
        tri = BRep_Tool.Triangulation_s(f, loc)
        if tri is not None:
            tr = loc.Transformation()
            P = [tri.Node(i).Transformed(tr) for i in range(1, tri.NbNodes() + 1)]
            P = [(q.X(), q.Z()) if ax == "y" else (q.X(), q.Y()) for q in P]
            for k in range(1, tri.NbTriangles() + 1):
                a, b, d = tri.Triangle(k).Get()
                tris.append((P[a - 1], P[b - 1], P[d - 1]))
        e.Next()
    return tris


MAT_LEGEND = [("sife", "SiFe laminations (utron cores, bridges)"), ("nife", "80 % NiFe neck strip"), ("cu", "Cu windings"),
              ("stator vane", "Al stator vane"), ("rotor vane", "Al rotor vane"), ("fixed plate", "Al Ca / Cb plate"),
              ("g10", "G10 (sleeve, cage, spiders, carriers, ring)"), ("steel", "steel (shaft, flanges, bearings)"),
              ("hub", "bicone (placeholder)"), ("glass", "vacuum sphere (placeholder)")]


def mat_legend(m):
    """the legend for a build: the placeholder hub's, or the locked hub's materials."""
    if m.p.get("hub") != "locked":
        return MAT_LEGEND
    return MAT_LEGEND[:8] + [("glass", "borosilicate vessel"), ("ring", "Cu rings + beads"), ("gel", "silicone gel"),
                             ("peek", "PEEK retainer"), ("mnzn", "MnZn AH cores")]


def _sections(m, parts_shapes, plane):
    """exact filled section + outline of each part in a plane: {name: (colour, triangles, polylines)}."""
    out = {}
    for pt, s in parts_shapes:
        tris = section_faces(s, plane)
        polys = cut_polylines(s, plane)
        if tris or polys:
            out[pt["name"]] = (m.protos[pt["proto"]][1], tris, polys)
    return out


def _draw(ax, sec, lw=0.35, edge="#222", keep=None):
    from matplotlib.collections import PolyCollection
    for name, (c, tris, polys) in sec.items():
        if keep and not keep(name):
            continue
        if tris:
            ax.add_collection(PolyCollection(tris, facecolors=[c], edgecolors=[c], linewidths=0.3, antialiaseds=False))
        for P in polys:
            ax.plot(P[:, 0], P[:, 1], color=edge, lw=lw)


def render_hub(m, sec, out_dir, tag):
    """the locked hub as built in the solids: the y = 0 section, enlarged, labelled."""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.patches import Patch
    hub = [e for e in m.el if e["kind"] == "hub"][0]
    zc = 0.5 * (hub["z0"] + hub["z1"])
    fig = plt.figure(figsize=(12.5, 11))
    ax = fig.add_axes((0.06, 0.06, 0.52, 0.86))
    near = lambda n: n.startswith(("hub_", "A_flange", "B_flange", "shaft_A", "shaft_B"))
    _draw(ax, sec, lw=0.45, keep=near)
    ax.axvline(0, color="#888", lw=0.5, ls="--")
    ax.set_aspect("equal"); ax.set_xlim(-38, 38); ax.set_ylim(hub["z0"] - 22, hub["z1"] + 22)
    ax.set_yticks([zc + k for k in range(-90, 91, 30)]); ax.set_yticklabels([f"{k:+d}" for k in range(-90, 91, 30)])
    ax.set_xlabel("x [mm] (y = 0)", fontsize=8.5); ax.set_ylabel("z [mm] from the hub's mid-plane", fontsize=8.5)
    ax.tick_params(labelsize=7.5)
    ax.set_title("the locked hub in the solids: section y = 0 (presets/hub-locked.json)", fontsize=10, loc="left")
    H = json.load(open(os.path.join(ROOT, "presets", "hub-locked.json")))
    rg = H["rings"]["value"]
    tp, te = math.radians(rg["polar_edge_deg"]), math.radians(rg["equatorial_edge_deg"])
    lab = [((0.0, zc + 12), "vacuum"),
           ((24.2 * math.sin(0.3), zc + 24.2 * math.cos(0.3)), "vessel: borosilicate, OD 50, wall 1.5"),
           ((25.05 * math.sin(0.5 * (tp + te)), zc + 25.05 * math.cos(0.5 * (tp + te))),
            f"ring B: Cu foil 0.1, {rg['polar_edge_deg']:g}-{rg['equatorial_edge_deg']:g} deg (+15.0 kV)"),
           ((26.5 * math.sin(tp), zc + 26.5 * math.cos(tp)), "polar bead, Cu Ø3, in its groove"),
           ((26.0 * math.sin(te), zc + 26.0 * math.cos(te)), "equatorial bead, Cu Ø2"),
           ((25.25 * math.sin(1.35), zc + 25.25 * math.cos(1.35)), "silicone gel, 0.5 mm pocket"),
           ((28.0, zc + 40), "PEEK retainer (r 30, |z| 72)"),
           ((31.5, zc + 20), "G10 coupler (r 30-33)"),
           ((3.0, zc + 50), "AH B core: 77 MnZn, Ø12.3"),
           ((7.5, zc + 60), "G-10 former"),
           ((9.8, zc + 45), "AH B coil: 160 turns"),
           ((5.0, zc + 27.5), "AH seat: PEEK, 5.7 mm"),
           ((20.0, hub["z1"] + 4), "flange B (REF), r 32 x 8"),
           ((8.0, hub["z1"] + 16), "shaft half B (REF)"),
           ((25.05 * math.sin(0.5 * (tp + te)), zc - 25.05 * math.cos(0.5 * (tp + te))), "ring A (-15.0 kV): the mirror"),
           ((0.0, hub["z0"] - 12), "shaft half A, flange A, AH A: the mirror")]
    ys = np.linspace(hub["z1"] + 16, hub["z0"] - 16, len(lab))
    for (pt_, text), yy in zip(sorted(lab, key=lambda q: -q[0][1]), ys):
        ax.annotate(text, pt_, (44, yy), fontsize=8, va="center", ha="left", annotation_clip=False,
                    arrowprops=dict(arrowstyle="-", lw=0.45, color="#444", shrinkA=0, shrinkB=0))
    leg = [("glass", "borosilicate vessel"), ("ring", "Cu rings + beads"), ("gel", "silicone gel"), ("peek", "PEEK retainer"),
           ("g10", "G10 coupler, G-10 formers"), ("mnzn", "MnZn AH cores"), ("cu", "Cu AH coils"), ("steel", "steel shaft, flanges")]
    fig.legend(handles=[Patch(facecolor=COL[k], label=t) for k, t in leg], loc="lower right", fontsize=8.5, frameon=False,
               ncol=2, bbox_to_anchor=(0.99, 0.02))
    fig.text(0.60, 0.17, "Not drawn (open): the retainer's split (the equatorial split is PROPOSED), the rings' leads and their\n"
             "channels, the AH ends' caps, the coupler's shape (a plain tube here). The grooves are the beads' own tori.",
             fontsize=8, va="top", color="#333")
    fig.suptitle(f"{tag}: the hub", fontsize=12, x=0.01, ha="left")
    f = os.path.join(out_dir, f"{tag}-hub.png"); fig.savefig(f, dpi=110, bbox_inches="tight"); plt.close(fig)
    return f


def renders_wound(m, out_dir, tag):
    """arrangement section (y = 0) with an enlarged detail of reluctance A, and plan cuts through both reluctance
    sections: exact sections of the solids, filled."""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.patches import Patch, Rectangle
    sp, el, ro = m.p["rel"], m.el, m.p["r_outMm"]
    shapes = [(pt, m.placed(pt)) for pt in m.parts]
    files = []
    in_plane = [(pt, s) for pt, s in shapes if bbox(s)[0][1] <= 0.01 and bbox(s)[1][1] >= -0.01]
    sec = _sections(m, in_plane, ("y", 0.0))
    L = max(e["z1"] for e in el)
    R_out = max(sp["r_ring1"], ro + 16.0)
    hub = [e for e in el if e["kind"] == "hub"][0]
    uA = [e for e in el if e["kind"] == "w utron" and e["side"] == "A"][0]
    rA = [e for e in el if e["kind"] == "reluctance" and e["side"] == "A"][0]
    fig = plt.figure(figsize=(19, 14))
    ax = fig.add_axes((0.02, 0.03, 0.50, 0.90)); ax.set_anchor("N")
    _draw(ax, sec)
    ax.axvline(0, color="#888", lw=0.5, ls="--")
    xr = R_out + 14

    def span(z0, z1, text, x=xr, col="#333"):
        ax.annotate("", (x, z0), (x, z1), arrowprops=dict(arrowstyle="|-|", color=col, lw=0.6, shrinkA=0, shrinkB=0,
                                                         mutation_scale=3))
        ax.text(x + 6, 0.5 * (z0 + z1), text, va="center", ha="left", fontsize=8, color=col)
    for side in ("A", "B"):
        se = [e for e in el if e["side"] == side]
        v = [e for e in se if e["kind"].endswith("vane")]
        c = [e for e in se if e["kind"].endswith("plate")]
        r = [e for e in se if e["kind"] == "reluctance"][0]
        vn, cn = ("C1", "Ca") if side == "A" else ("C2", "Cb")
        span(min(e["z0"] for e in v), max(e["z1"] for e in v),
             f"{vn} varicap {side}: {len(v) // 2} stator + {len(v) // 2}\nrotor vanes, {m.p['g_vMm']:g} mm "
             f"{'air' if m.p.get('dielectric') == 'air' else 'vacuum'} gaps")
        span(min(e["z0"] for e in c), max(e["z1"] for e in c), f"{cn} fixed plates {side}: {len(c)}"
             + (" (rotor)" if c and c[0]["body"] == "rotor" else ""))
        span(r["z0"], r["z1"], f"reluctance {side}: 3 wound utrons\n(rotor), {sp['n_br']} passive bridges\n(counter-rotor)"
             + (f", offset {180 / sp['n_br']:g} deg" if side == "B" else "") + ("\n(detail at right)" if side == "A" else ""))
    span(hub["z0"], hub["z1"], "hub (locked): 50 mm sphere, rings\nA / B, AH pair, PEEK + gel, G10" if m.p.get("hub") == "locked"
         else "hub: bicone + AH / C_R\n(placeholder)")
    for b in [e for e in el if e["kind"] == "bearing"]:
        ax.text(-R_out - 10, b["zc"], f"bearing, {b['where']}" + (" (frame)" if b["where"] == "end" else ""),
                ha="right", va="center", fontsize=7.5, color="#555")
    ax.annotate("", (-ro - 16, -24), (ro + 16, -24), arrowprops=dict(arrowstyle="<->", lw=0.6, color="#333"))
    ax.text(0, -31, f"cage OD {2 * (ro + 16):.0f} mm, vane OD {2 * ro:.0f} mm, bridge ring OD {2 * sp['r_ring1']:.0f} mm",
            ha="center", va="top", fontsize=8.5)
    ax.annotate("", (-R_out - 128, 0), (-R_out - 128, L), arrowprops=dict(arrowstyle="<->", lw=0.6, color="#333"))
    ax.text(-R_out - 132, 0.5 * L, f"overall {L:.0f} mm", rotation=90, ha="right", va="center", fontsize=8.5)
    ax.text(-R_out - 120, L + 40, "B side (top)", fontsize=10, ha="left")
    ax.text(-R_out - 120, -55, "A side (bottom)", fontsize=10, ha="left")
    ax.set_aspect("equal")
    ax.set_xlim(-R_out - 150, R_out + 205)
    ax.set_ylim(-70, L + 60)
    ax.set_xlabel("x [mm] (0 deg right, 180 deg left)", fontsize=8.5); ax.set_ylabel("z [mm] (shaft vertical)", fontsize=8.5)
    ax.tick_params(labelsize=7.5)
    ax.set_title("section through the shaft (plane y = 0), exact cut of the solids, rotor angle 0", fontsize=10, loc="left")
    # detail: reluctance A enlarged, right half, with labels
    ad = fig.add_axes((0.535, 0.40, 0.455, 0.53)); ad.set_anchor("N")
    zlo, zhi = rA["z0"] - 24, rA["z1"] + 30
    near = lambda n: n.startswith("A_") or n.startswith(("shaft_A", "rotor_sleeve"))
    _draw(ad, sec, lw=0.5, keep=near)
    ad.set_xlim(-8, R_out + 150); ad.set_ylim(zlo, zhi); ad.set_aspect("equal")
    zc, zs0, zs1 = uA["zc"], uA["zs0"], uA["zs1"]
    xl = R_out + 12
    lab = [((0.5 * (sp["u_p0"] + sp["u_p1"]), zc + 22), f"coil U A1: {sp['N_u']} turns, Ø{sp.get('wire_d_mm', 0):.2f} mm Cu,\n"
            f"rounded end turns (R {sp['over']:.0f}), on a 1 mm G10 former"),
           ((0.5 * (sp["u_y0"] + sp["u_n1"]), zc - 4), f"neck strip: 80 % NiFe {sp['t_n']:.2f} x {sp['L']:.0f} mm\n(sets Psi_s)"),
           ((0.5 * (sp["u_n1"] + sp["u_y1"]), zc - 32), f"air break {sp['brk']:.0f} mm, G10 spacer"),
           ((0.5 * (sp["u_w0"] + sp["r_g"]), zc + 40), "slot cover, G10 (bonded)"),
           ((0.5 * (sp["r_br0"] + sp["r_br1"]), zc - 20), f"bridge A1 (SiFe), gap {sp['g']:g} mm"),
           ((sp["r_ring1"] - 3, zs1 + 18), "bridge ring, G10 (counter-rotor)"),
           ((0.5 * (24 + sp["r_disc"]), zs0 - sp["t_cheek"] - 0.5 * sp["t_disc"]), "carrier discs, G10, on the rotor sleeve"),
           ((0.5 * (24 + sp["r_disc"]), zs1 + sp["t_cheek"] + 0.5 * sp["t_disc"]), "carrier discs, G10, on the rotor sleeve"),
           ((16.5, zc), "rotor sleeve, G10, on the shaft"),
           ((60.0, [b for b in el if b["kind"] == "bearing" and b["side"] == "A" and b["where"] != "end"
                    and b["zc"] < hub["z0"]][-1]["zc"]), "Ca|reluctance bearing + spider (counter-rotor)"),
           ((60.0, [b for b in el if b["kind"] == "bearing" and b["side"] == "A" and b["where"] == "end"][0]["zc"]),
            "end bearing + spider (frame)")]
    ys = np.linspace(zhi - 18, zlo + 18, len(lab) + 2)[1:-1]
    for (pt_, text), yy in zip(sorted(lab, key=lambda q: -q[0][1]), ys):
        ad.annotate(text, pt_, (xl, yy), fontsize=8, va="center", ha="left",
                    arrowprops=dict(arrowstyle="-", lw=0.5, color="#444", shrinkA=0, shrinkB=0))
    ad.set_title("detail: reluctance A, right half (0 deg): utron A1 aligned under bridge A1", fontsize=10, loc="left")
    ad.tick_params(labelsize=7.5)
    # legend + notes
    an = fig.add_axes((0.535, 0.03, 0.455, 0.42)); an.axis("off")
    rec = m.p.get("hub") == "locked"
    an.legend(handles=[Patch(facecolor=COL[k], label=t) for k, t in mat_legend(m)], loc="upper left", fontsize=8.5,
              frameon=False, ncol=2)
    an.text(0.0, 0.32, (("Bodies. Rotor: shaft halves, flanges, the hub (vessel, rings, gel, retainer, coupler, AH pair), rotor\n"
                        "sleeve, rotor vanes (nodes 1 / 4), Ca / Cb plates (mounts not drawn), utrons + carrier discs.\n"
                        "Counter-rotor, geared 1 : -1 (gear not drawn): stator cage (one tube across the hub), stator vanes\n"
                        "(REF), the hub-face and Ca|reluctance spiders, bridges + bridge rings.\n") if rec else
            ("Bodies. Rotor: shaft halves, flanges, bicone, rotor sleeve, rotor vanes, utrons + carrier discs.\n"
             "Counter-rotor, geared 1 : -1 (gear or reversing belt, not drawn): stator cage (one tube across the hub),\n"
             "stator vanes, Ca / Cb plates, the hub-face and Ca|reluctance spiders, bridges + bridge rings.\n")) +
            "Frame: the two end bearings and their spiders. The inner bearings run at the relative speed.\n"
            f"At rotor angle 0: utron A1 is aligned (gap {sp['g']:g} mm), utron B1 sits between two B bridges (antiphase);\n"
            "C1 is at its maximum and C2, its stator vanes half a pitch on, at its minimum.\n"
            "This plane (v = 0) cuts the coil, the neck strip and the air-break spacer; the SiFe half-cores and the\n"
            "cheeks lie at |v| >= s / 2 (see the plan cuts and the utron detail drawing).",
            fontsize=8.5, va="top", transform=an.transAxes)
    fig.suptitle(f"{tag}: arrangement ({sp.get('pick', '')}), {L:.0f} mm long", fontsize=12, x=0.01, ha="left")
    f = os.path.join(out_dir, f"{tag}-section.png"); fig.savefig(f, dpi=105, bbox_inches="tight"); plt.close(fig)
    files.append(f)
    if m.p.get("hub") == "locked":
        files.append(render_hub(m, sec, out_dir, tag))
    # 2. plan cuts: A and B at the stack mid-plane, A through the end turns and cheeks
    uB = [e for e in el if e["kind"] == "w utron" and e["side"] == "B"][0]
    cuts = ((uA["zc"], "A", f"A, stack mid-plane (z {uA['zc']:.0f}): utrons aligned"),
            (uB["zc"], "B", f"B, stack mid-plane (z {uB['zc']:.0f}): bridges offset {180 / sp['n_br']:g} deg, unaligned"),
            (uA["zs0"] - 0.5 * sp["t_cheek"], "A", f"A, through the end turns and cheeks (z {uA['zs0'] - 0.5 * sp['t_cheek']:.0f})"))
    fig, axs = plt.subplots(1, 3, figsize=(21, 7.6))
    lim = sp["r_ring1"] + 14
    for a, (zz, side, title) in zip(axs, cuts):
        sel = []
        for pt, s in shapes:
            lo, hi = bbox(s)
            if lo[2] <= zz <= hi[2] and (pt["group"] in (f"rel-{side}", "rotor") or pt["name"].startswith(side)):
                sel.append((pt, s))
        _draw(a, _sections(m, sel, ("z", zz)), lw=0.3)
        t = np.linspace(0, 2 * np.pi, 361)
        a.plot(sp["r_g"] * np.cos(t), sp["r_g"] * np.sin(t), color="#999", lw=0.4, ls="--")
        for e in [e for e in el if e["kind"] == "w bridge" and e["side"] == side]:
            for j, ang in enumerate(e["angles"]):
                q = math.radians(ang)
                a.text((lim - 3) * math.cos(q), (lim - 3) * math.sin(q), f"{side}b{j + 1}\n{ang:g}°", ha="center",
                       va="center", fontsize=6.5, color="#333")
        for j, ang in enumerate(uA["angles"]):
            q = math.radians(ang)
            rr = max(0.5 * (sp["r_disc"] + 20.5), sp["r_disc"] - 12)
            a.text(rr * math.cos(q), rr * math.sin(q), f"U{side}{j + 1}", ha="center", va="center", fontsize=7.5, color="#222")
        a.set_aspect("equal"); a.set_xlim(-lim - 6, lim + 6); a.set_ylim(-lim - 6, lim + 6)
        a.set_title(title, fontsize=9, loc="left"); a.tick_params(labelsize=7)
    fig.suptitle(f"{tag}: plan cuts through the reluctance sections, rotor angle 0 (dashed: the gap radius r_g {sp['r_g']:g} mm, "
                 f"gap {sp['g']:g} mm). 3 utrons per side at 120 deg on the rotor, {sp['n_br']} bridges per side at "
                 f"{360 / sp['n_br']:g} deg on the counter-rotor.", fontsize=10, x=0.01, ha="left")
    fig.legend(handles=[Patch(facecolor=COL[k], label=t) for k, t in mat_legend(m)[:3] + mat_legend(m)[6:7]], loc="lower left",
               fontsize=8, frameon=False, ncol=4)
    f = os.path.join(out_dir, f"{tag}-reluctance-plan.png"); fig.tight_layout(rect=(0, 0.04, 1, 0.95)); fig.savefig(f, dpi=100)
    plt.close(fig); files.append(f)
    return [os.path.relpath(x, ROOT) for x in files]


LAYOUT_LEGEND = [("sife", "SiFe (utron cores, bridges)"), ("cu", "Cu (coils, leads, straps)"), ("stator vane", "Al stator vane"),
                 ("rotor vane", "Al rotor vane"), ("fixed plate", "Al Ca / Cb plate"), ("can", "Al can (REF)"),
                 ("g10", "G10"), ("steel", "steel"), ("silicone", "silicone potting"), ("stick", "HV rectifier stick"),
                 ("rsurge", "surge resistor"), ("cap", "HV capacitor"), ("clamp", "clamp string"),
                 ("brass", "brass terminals"), ("ptfe", "PTFE (wire, bushing, cover, sheds)"), ("lv", "LV cable"),
                 ("glass", "borosilicate vessel"), ("ring", "Cu rings + beads"), ("peek", "PEEK retainer"),
                 ("cartridge", "stainless bearing cartridge"), ("steatite", "glazed steatite standoffs (Ca's node-2 comb)"),
                 ("al", "Al spacers (Ca's posts)"), ("rod", "glass-epoxy tie rods and nuts")]


def renders_layout(m, out_dir, tag, log=print):
    """the layout's exact sections: (a) the machine through the shaft (y = 0), (b) side A's central bay enlarged,
    (c) / (d) plan cuts through deck A and deck B at the sticks' axis (|z| 48), each seen from the hub's side, (e) side
    A's end enlarged: the end bearing and the bridge-ring bearing."""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.patches import Patch
    st, zc, L = m.lay["stack"], m.zc, m.L_mm
    shapes = [(pt, m.placed(pt)) for pt in m.parts]
    in_plane = [(pt, s) for pt, s in shapes if bbox(s)[0][1] <= 0.01 and bbox(s)[1][1] >= -0.01]
    sec = _sections(m, in_plane, ("y", 0.0))
    log(f"  the section: {len(sec)} parts cut")
    fig = plt.figure(figsize=(21, 15))
    ax = fig.add_axes((0.015, 0.04, 0.36, 0.9))
    _draw(ax, sec, lw=0.25)
    ax.axvline(0, color="#888", lw=0.5, ls="--")
    ax.set_aspect("equal"); ax.set_xlim(-175, 175); ax.set_ylim(-10, L + 10)
    ax.set_xlabel("x [mm] (y = 0: 0 deg right, 180 deg left)", fontsize=8.5)
    ax.set_ylabel("z [mm] from side A's end (shaft vertical, side B above)", fontsize=8.5)
    ax.tick_params(labelsize=7.5)
    ax.set_title(f"(a) the machine through the shaft, exact cut of the solids, rotor angle 0; {L:.0f} mm", fontsize=10, loc="left")
    hb, hv0, hv1 = st["h_bearing_mm"], st["h_vanes"][0], st["h_vanes"][1]
    hc_ = st["h_col_mm"]
    for z, t_ in ((zc + hb + 100, "reluctance B (the record's)"), (zc + 0.5 * (hv0 + hv1), "C2, in phase with C1"),
                  (zc + hc_ + 24, "Cb"), (zc + 57, "deck B"), (zc, "the hub in its can"), (zc - 57, "deck A"),
                  (zc - hc_ - 24, "Ca"), (zc - 0.5 * (hv0 + hv1), "C1"), (zc - hb - 100, "reluctance A (the record's)")):
        ax.text(172, z, t_, fontsize=7.5, va="center", ha="left", color="#333", clip_on=False)
    # (b) side A's central bay
    ad = fig.add_axes((0.40, 0.33, 0.32, 0.62))
    _draw(ad, sec, lw=0.45, keep=lambda n: not n.startswith(("B_", "shaft_B")))
    ad.axvline(0, color="#888", lw=0.5, ls="--")
    ad.set_aspect("equal"); ad.set_xlim(-170, 170); ad.set_ylim(zc - hb - 22, zc + 12)
    ad.set_yticks([zc - k for k in range(0, int(hb) + 1, 50)])
    ad.set_yticklabels([f"{k}" for k in range(0, int(hb) + 1, 50)])
    ad.set_ylabel("|z| from the hub's centre [mm], side A", fontsize=8.5); ad.tick_params(labelsize=7.5)
    ad.set_title("(b) side A's central bay: the can, deck A, Ca, the dead gap, C1, the Ca|reluctance bearing", fontsize=10,
                 loc="left")
    # (c), (d) the decks in plan
    for k, s_ in enumerate("AB"):
        a = fig.add_axes((0.40 + 0.165 * k, 0.03, 0.155, 0.27))
        zz_ = m.zz(s_, 48.0)
        sel = [(pt, s) for pt, s in shapes if bbox(s)[0][2] <= zz_ <= bbox(s)[1][2] and (pt["group"] in (f"deck-{s_}", "can", "hub", "cage", "rotor", "wiring"))]
        _draw(a, _sections(m, sel, ("z", zz_)), lw=0.3)
        for q in m.lay["decks"][s_]["parts"]:
            a.text(q["centre"][0], q["centre"][1], q["name"], fontsize=6.0, ha="center", va="center", color="#111", zorder=9)
        a.set_aspect("equal"); a.set_xlim(-170, 170); a.set_ylim(-170, 170); a.tick_params(labelsize=6.5)
        a.set_title(f"({'c' if s_ == 'A' else 'd'}) deck {s_} at |z| 48, seen from +z", fontsize=9, loc="left")
    if m.ring:
        import bridge_ring_bearings as BRB
        ae = fig.add_axes((0.745, 0.035, 0.245, 0.265))
        _draw(ae, sec, lw=0.5, keep=lambda n: not n.startswith(("B_", "shaft_B")))
        ae.axvline(0, color="#888", lw=0.5, ls="--")
        ae.set_aspect("equal"); ae.set_xlim(-12, 238); ae.set_ylim(-4, 76); ae.tick_params(labelsize=6.5)
        ae.set_xticks([0, 25, 50, 75, 100, 125, 150])
        ae.set_ylabel("z [mm]", fontsize=7.5)
        pl, P = m.ring, m.ring["side_A"]
        SPIDER_T_ = P["spider"]["z1"] - P["spider"]["z0"]
        lab = dict(fontsize=6.3, va="center", ha="left", color="#222")
        ae.text(165, pl["z_frame_mm"][0], f"end bearing (frame) on its\nspider, z {pl['z_frame_mm'][0]:.0f}", **lab)
        ae.text(165, pl["z_ring_mm"][0], f"the bridge-ring bearing's G10\nspider, {SPIDER_T_:.0f} mm, and the {pl['side_A']['adapter']['z1'] - pl['side_A']['adapter']['z0']:.0f} mm\nring to bridge ring A", **lab)
        ae.text(165, 60, "bridge ring A (the record's)", **lab)
        ae.annotate(f"bearing z {pl['z_ring_mm'][0]:.0f} in its stainless cartridge", (24.0, P["bearing"]["z0"] + 1.0),
                    (42.0, 18.0), arrowprops=dict(arrowstyle="-", lw=0.5, color="#222"), **lab)
        ae.text(60, P["spider"]["z1"] + 0.5 * pl["clear_spider_to_turns_mm"],
                f"{pl['clear_spider_to_turns_mm']:.0f} mm to the utrons' end turns", **lab)
        ae.set_title(f"(e) side A's end: the bridge-ring bearing ({BRB.PART['maker']} {BRB.PART['designation']}), "
                     f"z {pl['z_ring_mm'][0]:.0f}", fontsize=8.5, loc="left")
    an = fig.add_axes((0.74, 0.33, 0.25, 0.62)); an.axis("off")
    an.legend(handles=[Patch(facecolor=COL[k_], label=t_) for k_, t_ in LAYOUT_LEGEND], loc="upper left", fontsize=8.5,
              frameon=False, ncol=1)
    an.text(0.0, 0.30, "The layout of sim/multiplier-layout-findings.md (PROPOSED, 2026-10-11) in solids:\n"
            "every part of the decks from the study's plans, the record's\nhub, column plates, vanes and reluctance "
            "sections; the wiring\nas sim/tube_geometry.py LayoutMachine routes it; the bridge-ring\nbearings as "
            "sim/bridge_ring_bearings.py places them (PROPOSED)"
            + (";\nthe capacitors' mounts as sim/doubler_caps.py places them\n(PROPOSED): Ca / Cb's combs on their posts, "
               "the vanes' spacers,\nlugs and tie rods, the cage at r 182.\n\nNot drawn: the decks' standoffs to the can, "
               "the screws and\nstuds, the gear." if m.mounts else
               ".\n\nNot drawn: Ca / Cb's rods and mounts, the decks' standoffs to\nthe can, the plates' interconnections, "
               "the gear."), fontsize=8.5, va="top",
            transform=an.transAxes)
    fig.suptitle(f"{tag}: the multiplier laid out in the machine", fontsize=12, x=0.01, ha="left")
    f = os.path.join(out_dir, f"{tag}-section.png"); fig.savefig(f, dpi=100); plt.close(fig)
    return [os.path.relpath(f, ROOT)]


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
    r_u = cem["r_u"]
    lim = 10.0 * math.ceil((r_u + S.REL_X_MAX + 25.0) / 10.0)          # reluctance envelope + margin
    fig, axs = plt.subplots(1, 2, figsize=(14, 7))
    for a, (zz, title) in zip(axs, ((cem["zc"] + 44.0, "jaw / arm height (z = utron centre + 44)"), (cem["zc"], "utron mid-plane"))):
        t = [2 * math.pi * i / 180 for i in range(181)]
        a.plot([r_u * math.cos(x) for x in t], [r_u * math.sin(x) for x in t], color="#bbb", lw=0.6, ls="--")
        for pt, s in shapes + coils:
            lo, hi = bbox(s)
            if lo[2] > zz or hi[2] < zz or pt["group"] not in ("rel-A", "rotor"):
                continue
            for P in cut_polylines(s, ("z", zz)):
                a.plot(P[:, 0], P[:, 1], color=colours[pt["name"]], lw=0.8)
        a.set_aspect("equal"); a.set_title(f"reluctance A: {title}", fontsize=9)
        a.set_xlim(-lim, lim); a.set_ylim(-lim, lim)
    fig.suptitle(f"{tag}: 6 C-EMs (A at 30 + 60k) and 3 utrons (15 + 120k, rotor angle 0) around the sleeve (r 20); "
                 f"dashed: utron-centre circle r {r_u:.0f}", fontsize=9)
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
