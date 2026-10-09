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
            elif k == "w utron":
                sp = p["rel"]
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
                       *[bead(sg, w) for sg in (1, -1) for w in ("pol", "eq")], ah_bore(1), ah_bore(-1))
        self.proto("hub_vessel", lambda: cut(sphere(Ro, (0, 0, 0)), sphere(Ri, (0, 0, 0))), COL["glass"],
                   f"borosilicate vessel, OD {2 * Ro:g} mm, wall {wall:g} mm (vacuum inside)")
        self.proto("hub_gel", gel_shape, COL["gel"], f"silicone gel, {gel['t_mm']:g} mm, vacuum-cast")
        self.proto("hub_retainer", retainer, COL["peek"], "PEEK retainer, unfilled")
        self.proto("hub_coupler", lambda: sector(r_ret, r_ret + cpl["wall_mm"], -z_ret, z_ret), COL["g10"],
                   "G10 shaft coupler (shape OPEN: a plain tube)")
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
    a = ap.parse_args()
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
