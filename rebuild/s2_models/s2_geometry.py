"""rebuild/s2_models/s2_geometry.py -- S2a, step 2: the tube as solids for the S1b circuit, built from scratch.

The designer (2026-10-16): "we explicitely agreed to build from scratch, then why am I seeing the entire build again
with reluctance sections and all?" -- the model is therefore built from the S1b circuit up, by the rule of addition
(rebuild/README.md): only what the circuit needs, plus the bare minimum of mechanics (the designer's choice), nothing
inherited without evidence. The designer's choices of 2026-10-16: the bare-minimum mechanics; no can round the hub; the
decks beside the hub; the hub without the AH (the magnetic pump is not earned yet).

What the model holds, per side (side A below the hub, side B its mirror; h = |z| from the hub's centre):
  - the hub as locked (presets/hub-locked.json, the 2 mm wall; sim/tube_geometry.py Machine.locked_hub, the decided
    part, read only), without its AH cores, formers and coils: the vessel, rings A / B (the core's electrode pair, N1 /
    N4) and their beads, the gel, the PEEK retainer, the G10 coupler (to h 80) with the ring leads' channels and the
    REF terminals' holes; the shaft halves' flanges (REF, h 72-80);
  - the shaft half (REF) and its G10 rotor sleeve;
  - the deck beside the hub (rebuild/s2_models/s2_deck.py, --bare-can --no-can): its G10 plate bonded on the coupler,
    two HV sticks, the clamp string as two series halves, the junctions, the leads over the parts, the REF straps to
    brass terminals through the coupler into the flange, ring A's (B's) lead to the N1 (N4) junction, the cross nets N2 /
    N3 straight across on the PTFE bracket at the midplane with its twin;
  - the column Ca (Cb): the record's six full-annulus plates, node 2 toward the deck, at the clearance the deck and the
    flange allow;
  - the vane stack C1 (C2): the record's 6 + 6 (sim/air_stack_sizing_results.json thick_vanes, the stack S1's values
    come from), a rotor vane at the hub end, the rotor vanes on the sleeve; side B's rotor vanes half a pitch on
    (antiphase, S0's 180 deg);
  - the minimum mechanics [IR, placeholders]: G10 spacer rings between the rotor vanes (one net, N1), a G10 carrier
    tube holding the stator vanes, and the REF link of the 2026-10-08 decision ("through an inner bearing for now, a
    brush later") as a bearing on the shaft with an Al spider to the carrier.
Left OPEN, not drawn (they need design, not a placeholder): how the plates of one net are tied together (the column's
node-1 / node-2 ties, the rotor vanes' tie to the column, the stator vanes' REF bus), the column's mechanical support,
the riser and the tap from the deck to the column, the joint between the two counter-rotor halves, the drive. The
field solve (S2b) gives every conductor its net from the parts list, so it does not need the ties drawn.

Checks: no two solids share volume; no counter-rotor solid in a rotor solid's swept volume; every conductor of two
different nets, outside the designed 6 mm cells and the potting, at least the bare clearance of the pair's peak apart
(IEC 60664-1 case A at 1.5 x, sim/multiplier_layout.py clearance), the peaks from S1b's design case (s2_deck.py volts).
Writes rebuild/s2_models/geometry/<tag>.step, <tag>.parts.json, <tag>.FCStd and <tag>-view.png (through FreeCAD's GUI
program, so the parts display), and rebuild/s2_models/s2_geometry_results.json.
Usage: python3 rebuild/s2_models/s2_geometry.py [--no-step] [--no-fcstd]
"""
import json
import math
import os
import subprocess
import sys
import tempfile
import time

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "sim"))
sys.path.insert(0, HERE)
import tube_geometry as TG  # noqa: E402  (its primitives, the locked hub and the STEP writer; read only)
import multiplier_layout as ML  # noqa: E402  (the clearance rule, the parts' envelopes; read only)
import s2_deck as SD  # noqa: E402  (registers the half-string envelope)

OUT_DIR = os.path.join(HERE, "geometry")
DECK = json.load(open(os.path.join(HERE, "s2_deck_bare_nocan_results.json")))
# the designer (2026-10-16): "Implement v1b" -- the decks two-fold symmetric with their wiring, deck B deck A turned
# 180 deg (rebuild/s2_models/s2_deck_symmetry.py, s2-deck-symmetry-findings.md); the rules, the stack and the voltages
# stay the no-can deck's
_SYM = [v for v in json.load(open(os.path.join(HERE, "s2_deck_symmetry_results.json")))["variants"]
        if v["name"].startswith("V1b")][0]
DECK["deck_A"], DECK["deck_B"] = _SYM["deck_A"], _SYM["deck_B"]
DECK["balance"] = dict(DECK["balance"], plate_r_mm=_SYM["plate_r_mm"], static_g_mm=_SYM["static_A_g_mm"],
                       couple_g_mm2=_SYM["couple_g_mm2"], source="rebuild/s2_models/s2_deck_symmetry_results.json V1b")
TAG = "s2-tube-s1b-from-scratch"
WIRE = 1.5                                            # the PTFE HV wire's radius (sim/tube_geometry.py WIRE_R)
FREECAD_EXE = os.path.join(os.environ.get("LOCALAPPDATA", ""), "Programs", "FreeCAD 1.1", "bin", "freecad.exe")
COL = dict(TG.COL)
COL.update({"bracket": (0.95, 0.95, 0.88), "placeholder": (0.85, 0.80, 0.60)})
H = json.load(open(os.path.join(ROOT, "presets", "hub-locked.json")))
_REC = [q for q in json.load(open(os.path.join(ROOT, "sim", "air_stack_sizing_results.json")))["thick_vanes"]["compare"]
        if q["t_vaneMm"] == 3.0 and q["n_plates"] == 6][0]
VANE = dict(t=_REC["t_vaneMm"], g=_REC["gap_mm"], ws=_REC["ws_deg"], wr=_REC["wr_deg"], n_sec=_REC["sectors"],
            r_in=ML.R_IN, r_out=ML.R_OUT, n_vanes=ML.N_VANES)
PITCH = 360.0 / VANE["n_sec"]
SHAFT_R, SLEEVE_R = ML.SHAFT_R, ML.SLEEVE_R          # 12.5, 20.5 (sim/stack_sizing.py)
FL_Z0, FL_Z1, FL_R = ML.FL_Z0, ML.FL_Z1, ML.FL_R    # the flanges, h 72-80, r 30 (presets/hub-locked.json shaft)
CPL_R1 = ML.CPL_R1                                   # the coupler's outer face, r 33
STATOR_RING = (VANE["r_out"], VANE["r_out"] + 12.0)  # the stator vanes' outer ring, as the record (r 150-162)
CARRIER = (STATOR_RING[1], STATOR_RING[1] + 4.0)     # the G10 carrier tube [IR, placeholder], as the record's cage
SPACER_R = (SLEEVE_R, SLEEVE_R + 5.5)                # the rotor vanes' G10 spacer rings [IR, placeholder]
BEARING = dict(od=52.0, width=15.0, name="6205 class")   # the REF link's bearing (the record's class) [RH]
SPIDER_T = 8.0
REF_TERM = (2.5, 74.5)                               # the REF terminals through the coupler into the flange
                                                     # (h 72-80): radius, h [IR]
STRAP_LOW = 60.0                                     # the straps run in low, under the column's reach [IR]


def volts():
    return DECK["volts_design"]


class S2Core(TG.Machine):
    """only what the S1b circuit needs, the bare minimum of mechanics; Machine's prototypes, placing and hub."""

    def __init__(self):
        self.p = dict(r_inMm=VANE["r_in"], r_outMm=VANE["r_out"], t_vaneMm=VANE["t"])
        self.lad = dict(tube_geometry=dict(tag=TAG))
        self.el, self.protos, self.parts, self.nets = [], {}, [], {}
        self.V = volts()
        self.plan()

    # ---- the stack, h from the hub's centre (side A; side B its mirror)
    def plan(self):
        t, g = VANE["t"], VANE["g"]
        z_dk = ML.DECK_Z0 + ML.DECK_T + ML.DECK_H                    # 78: the deck's parts' outer face
        clr = lambda a, b: ML.clearance(ML.volt(self.V, a, b)["pk"])  # noqa: E731
        # the column's node-2 plate: off the deck's parts (s2_deck.py), and both its first plates off the flange's
        # outer corner (r 30, h 80) in air: N2 at the plate's bore (r 50), N1 one plate and one gap further out [OC]
        dr = VANE["r_in"] - FL_R
        need = dict(deck=z_dk + DECK["stack"]["c_col_mm"],
                    n2_flange=FL_Z1 + math.sqrt(max(0.0, clr("0", "2") ** 2 - dr ** 2)),
                    n1_flange=FL_Z1 + math.sqrt(max(0.0, clr("0", "1") ** 2 - dr ** 2)) - (t + g))
        self.h_col = float(math.ceil(max(need.values())))
        self.col_need = need
        self.h_vanes0 = self.h_col + ML.N_CA * t + (ML.N_CA - 1) * g + g      # the dead gap: node 1 against node 1
        self.h_vanes1 = self.h_vanes0 + VANE["n_vanes"] * t + (VANE["n_vanes"] - 1) * g
        last_rotor = self.h_vanes0 + (VANE["n_vanes"] - 2) * (t + g) + t        # the outermost rotor vane's outer face
        # the REF link: the bearing and its spider clear the outermost rotor vane (N1) in air [OC: the rule]
        self.h_brg0 = float(math.ceil(max(self.h_vanes1 + g, last_rotor + clr("0", "1"))))
        self.h_end = self.h_brg0 + BEARING["width"] + 10.0
        self.zc = self.h_end
        self.L_mm = 2.0 * self.h_end

    def zz(self, side, h):
        return self.zc - h if side == "A" else self.zc + h

    def zs(self, side, h0, h1):
        a, b = self.zz(side, h0), self.zz(side, h1)
        return (a, b) if a < b else (b, a)

    def put(self, name, key, make, colour, material, body, group, join=None, net=None, dz=0.0, rot=0.0, dx=0.0, desc=""):
        if key not in self.protos:
            self.proto(key, make, colour, material)
        self.add(name, key, body, net if isinstance(net, str) else "", group, join=join, dz=dz, rot=rot, dx=dx, desc=desc)
        if net is not None:
            self.nets[name] = dict(net) if isinstance(net, dict) else {"net": net}

    def put_wire(self, name, pts, net, group, join, colour=None, material="PTFE HV wire, 1 mm Cu in 3 mm PTFE",
                 r=TG.WIRE_R, desc=""):
        P = [tuple(float(x) for x in q) for q in pts]
        P = [q for i, q in enumerate(P) if i == 0 or np.linalg.norm(np.subtract(q, P[i - 1])) > 0.2]
        self.put(name, name, lambda P=P: TG.wire(P, r), colour or COL["ptfe"], material, "rotor", group, join=join,
                 net=net, desc=desc)
        self.nets[name]["path"] = [list(q) for q in P]

    # ---- the build
    def build(self):
        dA, dB = DECK["deck_A"], DECK["deck_B"]
        self.th_lead = {"A": TG._ang(dA["junctions"]["1"]), "B": TG._ang(dB["junctions"]["4"])}
        self.hub()
        self.shafts()
        self.columns_and_vanes()
        self.ref_link()
        self.decks()
        return self

    def hub(self):
        # the coupler to the flanges' outer face (h 80), the ring leads' channels toward the N1 / N4 junctions, the REF
        # terminals' holes; then the AH's parts dropped (the magnetic pump is not earned) [the designer, 2026-10-16]
        self.ref_terms = []
        cuts = []
        for s_, d in (("A", DECK["deck_A"]), ("B", DECK["deck_B"])):
            sg = -1 if s_ == "A" else 1
            for st_ in d["straps"]:
                th = TG._ang(st_["a"])
                u = TG._u(th)
                a = u * (FL_R - 1.0) + [0.0, 0.0, sg * REF_TERM[1]]
                b = u * (CPL_R1 + 1.0) + [0.0, 0.0, sg * REF_TERM[1]]
                cuts.append(TG.cyl_between(a, b, REF_TERM[0]))
                self.ref_terms.append((s_, th))
        self.hub_opts = dict(coupler_absz=FL_Z1, channels=[(-1, self.th_lead["A"]), (1, self.th_lead["B"])],
                             coupler_material="G10 shaft coupler: a tube over the retainer and both flanges",
                             extra_cuts=cuts)
        self.locked_hub(dict(z0=self.zc - FL_Z0, z1=self.zc + FL_Z0))
        self.parts = [p for p in self.parts if not p["name"].startswith("hub_AH_")]
        self.ah_dropped = True
        for s_, n in (("A", "1"), ("B", "4")):
            for nm in (f"hub_ring_{s_}", f"hub_bead_{s_}_pol", f"hub_bead_{s_}_eq"):
                self.nets[nm] = {"net": n}

    def shafts(self):
        tf = FL_Z1 - FL_Z0
        self.proto("flange", lambda: TG.sector(0.0, FL_R, 0.0, tf), COL["steel"],
                   "austenitic stainless flange, non-magnetic, Ø60")
        for s_ in "AB":
            z0, _ = self.zs(s_, FL_Z0, FL_Z1)
            self.put(f"{s_}_flange", "flange", None, None, None, "rotor", "hub", join="rotor-core", net="0", dz=z0,
                     desc=f"shaft-half flange {s_} (REF), bonded and pinned in the coupler")
            z0, z1 = self.zs(s_, FL_Z1, self.h_end)
            self.put(f"shaft_{s_}", f"shaft_{s_}", lambda z0=z0, z1=z1: TG.sector(0.0, SHAFT_R, z0, z1), COL["steel"],
                     "austenitic stainless shaft half, non-magnetic", "rotor", "rotor", join="rotor-core", net="0",
                     desc=f"shaft half {s_} (REF)")
            z0, z1 = self.zs(s_, FL_Z1, self.h_brg0 - 1.0)
            self.put(f"{s_}_sleeve", f"sleeve_{s_}", lambda z0=z0, z1=z1: TG.sector(SHAFT_R, SLEEVE_R, z0, z1),
                     COL["g10"], "G10 rotor sleeve", "rotor", "rotor", join="rotor-core",
                     desc="the rotor sleeve under the column and the vanes")
        for s_, th in self.ref_terms:
            sg = -1 if s_ == "A" else 1
            u = TG._u(th)
            a = u * (FL_R - 1.0) + [0.0, 0.0, self.zc + sg * REF_TERM[1]]
            b = u * (CPL_R1 + 0.5) + [0.0, 0.0, self.zc + sg * REF_TERM[1]]
            self.put(f"{s_}_ref_term_{th:.0f}", f"ref_term_{s_}_{th:.0f}", lambda a=a, b=b: TG.cyl_between(a, b, REF_TERM[0]),
                     COL["brass"], "brass REF terminal through the coupler into the flange [IR]", "rotor", "hub",
                     join="rotor-core", net="0", desc="a deck's REF strap lands here: through the coupler into the flange")

    def columns_and_vanes(self):
        t, g, ri, ro = VANE["t"], VANE["g"], VANE["r_in"], VANE["r_out"]
        n = VANE["n_sec"]
        self.proto("ca_plate", lambda: TG.sector(ri, ro, 0.0, t), COL["fixed plate"], "Al plate, 3 mm, full annulus")
        self.proto("rotor_vane", lambda: TG.fuse([TG.sector(ri, ro, 0.0, t, k * PITCH - 0.5 * VANE["wr"], VANE["wr"])
                                                  for k in range(n)] + [TG.sector(SLEEVE_R, ri, 0.0, t)]),
                   COL["rotor vane"], f"Al rotor vane, 3 mm, {n} sectors of {VANE['wr']:g} deg on its ring")
        self.proto("stator_vane", lambda: TG.fuse([TG.sector(ri, ro, 0.0, t, k * PITCH - 0.5 * VANE["ws"], VANE["ws"])
                                                   for k in range(n)] + [TG.sector(*STATOR_RING, 0.0, t)]),
                   COL["stator vane"], f"Al stator vane, 3 mm, {n} sectors of {VANE['ws']:g} deg on its ring")
        self.proto("rotor_spacer", lambda: TG.sector(*SPACER_R, 0.0, 2 * g + t), COL["g10"],
                   "G10 spacer ring between two rotor vanes [IR, placeholder]")
        for s_ in "AB":
            cn, vn = ("Ca", "C1") if s_ == "A" else ("Cb", "C2")
            n1, n2 = ("1", "2") if s_ == "A" else ("4", "3")
            for k in range(ML.N_CA):                              # node 2 toward the deck, alternating
                h0 = self.h_col + k * (t + g)
                z0, _ = self.zs(s_, h0, h0 + t)
                nd = n2 if k % 2 == 0 else n1
                self.put(f"{s_}_{cn}_{ML.N_CA - k:02d}", "ca_plate", None, None, None, "rotor", f"side-{s_}", net=nd,
                         join=f"{s_}_{cn}_{k}", dz=z0, desc=f"{cn} plate, node {nd} (support OPEN)")
            rot_b = 0.5 * PITCH if s_ == "B" else 0.0              # antiphase: side B's rotor half a pitch on
            for k in range(VANE["n_vanes"]):
                h0 = self.h_vanes0 + k * (t + g)
                z0, _ = self.zs(s_, h0, h0 + t)
                rotor = k % 2 == 0
                self.put(f"{s_}_{vn}_{'r' if rotor else 's'}{k + 1:02d}", "rotor_vane" if rotor else "stator_vane",
                         None, None, None, "rotor" if rotor else "stator", f"side-{s_}",
                         join="rotor-vanes-" + s_ if rotor else "stator-" + s_, net=n1 if rotor else "s",
                         dz=z0, rot=rot_b if rotor else 0.0,
                         desc=f"{vn} {'rotor vane, node ' + n1 if rotor else 'stator vane, REF (the counter-rotor)'}"
                              + (", half a pitch on: antiphase to C1" if rotor and s_ == "B" else ""))
                if rotor and k + 2 < VANE["n_vanes"]:
                    z0, _ = self.zs(s_, h0 + t, h0 + 2 * (t + g))
                    self.put(f"{s_}_rotor_spacer_{k // 2 + 1}", "rotor_spacer", None, None, None, "rotor", f"side-{s_}",
                             join="rotor-vanes-" + s_, dz=z0, desc="G10 spacer between two rotor vanes (placeholder)")
            z0, z1 = self.zs(s_, self.h_vanes0 + t + g - 1.0, self.h_brg0 + 0.5 * BEARING["width"] + 0.5 * SPIDER_T)
            self.put(f"{s_}_carrier", f"carrier_{s_}", lambda z0=z0, z1=z1: TG.sector(*CARRIER, z0, z1), COL["g10"],
                     "G10 carrier tube for the stator vanes [IR, placeholder]", "stator", "stator",
                     join="stator-" + s_, desc="the counter-rotor's carrier: holds the stator vanes, ends on the spider")

    def ref_link(self):
        self.proto("bearing", lambda: TG.sector(SHAFT_R, 0.5 * BEARING["od"], 0.0, BEARING["width"]), COL["steel"],
                   f"{BEARING['name']} bearing: the REF link [placeholder, the 2026-10-08 decision]")
        self.proto("spider", lambda: TG.sector(0.5 * BEARING["od"], CARRIER[1], 0.0, SPIDER_T), COL["al"],
                   "Al spider: the bearing's outer ring to the carrier, REF [placeholder]")
        for s_ in "AB":
            z0, _ = self.zs(s_, self.h_brg0, self.h_brg0 + BEARING["width"])
            self.put(f"{s_}_ref_bearing", "bearing", None, None, None, "bearing", "ref-link", join=f"brg-{s_}", net="0",
                     dz=z0, desc="the REF link: rotor (the shaft) to the counter-rotor, through the bearing (for now)")
            hc = self.h_brg0 + 0.5 * BEARING["width"]
            z0, _ = self.zs(s_, hc - 0.5 * SPIDER_T, hc + 0.5 * SPIDER_T)
            self.put(f"{s_}_ref_spider", "spider", None, None, None, "stator", "ref-link", join="stator-" + s_, net="s",
                     dz=z0, desc="the REF link's spider: the bearing to the carrier (REF of the counter-rotor)")

    # ---- the decks, as s2_deck.py planned them (no can)
    def decks(self):
        P = {k: ML.PART[k] for k in ("stick", "clamp_half")}
        h_face = ML.DECK_Z0 + ML.DECK_T
        tpl = ML.DECK_T
        dA = DECK["deck_A"]
        holes = [dA["junctions"]["2"], dA["junctions"]["3x"], dA["junctions"]["1"]]   # the cross nets; ring A's lead
        holes_b = [DECK["deck_B"]["junctions"]["4"]]                                       # ring B's (mirrored plate)
        r_pl = DECK["balance"]["plate_r_mm"][1]
        for key, hs in (("deck_plate_A", holes), ("deck_plate_B", [dA["junctions"]["2"], dA["junctions"]["3x"]] + holes_b)):
            self.proto(key, lambda hs=hs: TG._cut(TG.sector(CPL_R1, r_pl, 0.0, tpl),
                                                  *[TG.cyl_z(x, y, 3.0, -1.0, tpl + 1.0) for x, y in hs]),
                       COL["g10"], f"G10 deck plate, 6 mm, r {CPL_R1:.0f}-{r_pl:.0f}, bonded on the coupler; the cross "
                                   "nets' and the ring lead's holes [IR]")
        q = P["stick"]
        rad, bl, br = 0.5 * q["d"], q["body_l"], 0.5 * q["body_d"]
        half = 0.5 * q["l"] - rad
        body = lambda: TG.cyl_between((0, -0.5 * bl, 0), (0, 0.5 * bl, 0), br)                    # noqa: E731
        lead = lambda sg: TG.cyl_between((0, sg * 0.5 * bl, 0), (0, sg * 0.5 * q["l"], 0), 0.6)    # noqa: E731
        self.proto("stick_body", body, COL["stick"], q["what"])
        self.proto("stick_pot", lambda: TG._cut(TG.capsule_y(rad, half), body(), lead(1), lead(-1)), COL["silicone"],
                   "silicone potting, 8 mm over the part")
        for sg, nm in ((-1, "neg"), (1, "pos")):
            self.proto(f"stick_lead_{nm}", lambda sg=sg: lead(sg), COL["cu"], "tinned Cu lead, 1.2 mm")
        qc = P["clamp_half"]
        Rz = dA.get("Rz") or dA["z_place"][1]
        span = math.degrees((qc["l"] - qc["w"]) / Rz)

        def cl_lead(end):
            c_end = TG._u(0.0 if end == 0 else span) * Rz
            term = TG._u(-math.degrees(0.5 * qc["w"] / Rz) if end == 0 else span + math.degrees(0.5 * qc["w"] / Rz)) * Rz
            u = (term - c_end) / np.linalg.norm(term - c_end)
            return TG.cyl_between(c_end + (0.5 * qc["body_w"] + 0.7) * u, term, 0.6)
        cl_body = lambda: TG.arc_capsule(Rz, span, 0.5 * qc["body_w"], -0.5 * qc["body_h"], 0.5 * qc["body_h"])  # noqa
        self.proto("clamph_body", cl_body, COL["clamp"], qc["what"])
        self.proto("clamph_pot", lambda: TG._cut(TG.arc_capsule(Rz, span, 0.5 * qc["w"], -0.5 * qc["h"], 0.5 * qc["h"]),
                                                 cl_body(), cl_lead(0), cl_lead(1)),
                   COL["silicone"], "silicone potting, 8 mm over the half module")
        for end in (0, 1):
            self.proto(f"clamph_lead_{end}", lambda end=end: cl_lead(end), COL["cu"], "tinned Cu lead, 1.2 mm")
        jr, jl = TG.J_COND
        self.proto("j_cond", lambda: TG.cyl_z(0.0, 0.0, jr, -0.5 * jl, 0.5 * jl), COL["brass"], "brass junction terminal")
        self.proto("j_pot", lambda: TG._cut(TG.cyl_z(0.0, 0.0, TG.J_POT[0], -0.5 * TG.J_POT[1], 0.5 * TG.J_POT[1]),
                                            TG.cyl_z(0.0, 0.0, jr, -0.5 * jl, 0.5 * jl)),
                   COL["silicone"], "silicone potting, the junction's block")
        h_ax = lambda kind: h_face + 0.5 * (P[kind]["d"] if kind == "stick" else P[kind]["h"])       # noqa: E731
        j_top = h_face + 0.5 * P["stick"]["d"] + 0.5 * jl
        j_in = h_face + 0.5 * P["stick"]["d"] - 0.5 * jl
        rg, Ro = H["rings"]["value"], 0.5 * H["vessel"]["value"]["od_mm"]
        te, rho = math.radians(rg["equatorial_edge_deg"]), 0.5 * rg["bead_d_mm"]["equatorial"]
        for s_, d in (("A", DECK["deck_A"]), ("B", DECK["deck_B"])):
            g, jn = f"deck-{s_}", f"deck-{s_}"
            n1 = "1" if s_ == "A" else "4"
            zh = lambda h, s_=s_: np.array([0.0, 0.0, self.zz(s_, h)])                              # noqa: E731
            z0, _ = self.zs(s_, ML.DECK_Z0, ML.DECK_Z0 + ML.DECK_T)
            self.put(f"{s_}_deck_plate", f"deck_plate_{s_}", None, None, None, "rotor", g, join="hub-coupler", dz=z0,
                     desc=f"deck {s_}: the G10 plate on the coupler, |z| 30-36")
            Jxy = {n: np.array([x, y, 0.0]) for n, (x, y) in d["junctions"].items() if not n.startswith("0")}
            for n, c in Jxy.items():
                r_, th = float(np.hypot(c[0], c[1])), TG._ang(c)
                self.put(f"{s_}_J_{n}", "j_cond", None, None, None, "rotor", g, join=jn, net=n.rstrip("x"), dx=r_, rot=th,
                         dz=self.zz(s_, h_ax("stick")), desc=f"junction N{n.rstrip('x')}: brass terminal in its block")
                self.put(f"{s_}_J_{n}_pot", "j_pot", None, None, None, "rotor", g, join=jn, dx=r_, rot=th,
                         dz=self.zz(s_, h_ax("stick")), desc=f"junction N{n.rstrip('x')}: potting")
            for q in d["parts"]:
                nm, kind, (na, nb) = q["name"], q["kind"], q["nets"]
                c = np.array([q["centre"][0], q["centre"][1], 0.0])
                r_c, th_c = float(np.hypot(c[0], c[1])), TG._ang(c)
                T = [np.array([*x, 0.0]) for x in q["terminals"]]
                if kind == "stick":
                    zax = self.zz(s_, h_ax(kind))
                    b0, b1 = (np.array([x, y, zax]) for x, y in q["body_pts"])
                    self.put(f"{s_}_{nm}_body", "stick_body", None, None, None, "rotor", g, join=f"{s_}_{nm}_body",
                             net={"nets": [na, nb], "axis": [b0.tolist(), b1.tolist()], "device": nm}, dx=r_c, rot=th_c,
                             dz=zax, desc=f"{nm} ({na} -> {nb}): {P[kind]['what']}")
                    self.put(f"{s_}_{nm}_pot", "stick_pot", None, None, None, "rotor", g, join=jn, dx=r_c, rot=th_c,
                             dz=zax, desc=f"{nm}: its potted housing")
                    tvec = np.array([-math.sin(math.radians(th_c)), math.cos(math.radians(th_c)), 0.0])
                    k_neg = 0 if np.linalg.norm(c - 0.5 * P[kind]["l"] * tvec - T[0]) < 1e-6 else 1
                    for sg, end_nm in ((-1, "neg"), (1, "pos")):
                        k = k_neg if sg < 0 else 1 - k_neg
                        self.put(f"{s_}_{nm}_lead_{end_nm}", f"stick_lead_{end_nm}", None, None, None, "rotor", g,
                                 join=jn, net=(na, nb)[k], dx=r_c, rot=th_c, dz=zax, desc=f"{nm}: its lead, net {(na, nb)[k]}")
                else:
                    a0, a1 = TG._ang(q["pts"][0]), TG._ang(q["pts"][-1])
                    d_ = (a1 - a0 + 540.0) % 360.0 - 180.0
                    rot_ = a0 if d_ > 0 else a1
                    zc_ = self.zz(s_, h_ax(kind))
                    self.put(f"{s_}_{nm}_body", "clamph_body", None, None, None, "rotor", g, join=f"{s_}_{nm}_body",
                             net={"nets": [na, nb], "arc": dict(r=Rz, th=[TG._ang(x) for x in q["terminals"]], z=zc_),
                                  "device": nm}, rot=rot_, dz=zc_, desc=f"{nm} ({na} - {nb}): {P[kind]['what']}")
                    self.put(f"{s_}_{nm}_pot", "clamph_pot", None, None, None, "rotor", g, join=jn, rot=rot_, dz=zc_,
                             desc=f"{nm}: its potted housing")
                    for end in (0, 1):
                        k = end if d_ > 0 else 1 - end
                        self.put(f"{s_}_{nm}_lead_{end}", f"clamph_lead_{end}", None, None, None, "rotor", g, join=jn,
                                 net=(na, nb)[k], rot=rot_, dz=zc_, desc=f"{nm}: its lead, net {(na, nb)[k]}")
            # the leads over the parts: the clamp's HV end to N1 (6 mm off the junction's centre, the ring's lead the
            # other side), the midpoint lead round the open side of the lane
            side = 1.0
            for i, L in enumerate(d["leads"]):
                a, b = np.array([*L["a"], 0.0]), np.array([*L["b"], 0.0])
                if not L["net"].startswith("m"):
                    # a short joint (V1b): the half's terminal to the stick's end beside it, in the potting; onto the
                    # junction's terminal (N1 / N4) or the stick's REF end
                    on_block = L["net"] in ("1", "4")
                    end = b + zh(j_top if on_block else h_ax("stick"))
                    self.put_wire(f"{s_}_joint_{i}_{L['net']}", [a + zh(h_ax("clamp_half")), b + zh(h_ax("clamp_half")), end],
                                  L["net"], g, jn, desc=f"joint, net {L['net']}: the clamp half to the stick's end beside it")
                    continue
                ta, tb = TG._ang(a), TG._ang(b)
                dtt = (tb - ta) % 360.0 if L.get("dir", 1) > 0 else (tb - ta) % 360.0 - 360.0
                ra, rb = float(np.linalg.norm(a)), float(np.linalg.norm(b))
                n_pt = max(2, int(abs(dtt) / 6.0) + 1)
                arc = [TG._u(ta + dtt * f) * (ra + (rb - ra) * f) + zh(TG.Z_OVER) for f in np.linspace(0, 1, n_pt)]
                self.put_wire(f"{s_}_ring_m_{i}", [a + zh(h_ax("clamp_half"))] + arc + [b + zh(h_ax("clamp_half"))],
                              L["net"], g, jn, desc=f"the midpoint ring {L['net']}, its {'+' if dtt > 0 else '-'} half, "
                                                    "over the parts in the potting")
            # the REF straps: up to the terminal's height, in to the coupler's face, onto the brass terminal
            for st_ in d["straps"]:
                Tq = np.array([*st_["a"], 0.0])
                u = Tq / np.linalg.norm(Tq)
                h_s = REF_TERM[1]
                self.put_wire(f"{s_}_strap_{TG._ang(Tq):.0f}", [Tq + zh(h_ax("stick")), Tq + zh(STRAP_LOW),
                                                                u * (CPL_R1 + 3.0) + zh(STRAP_LOW), u * (CPL_R1 + 3.0) + zh(h_s),
                                                                u * (CPL_R1 + 0.5) + zh(h_s)],
                              "0", g, jn, colour=COL["cu"], material="Cu strap (REF)", desc="REF strap to the terminal in the coupler")
            # ring A's (B's) lead: from its equatorial bead along the normal through the PEEK and the coupler, out of the
            # coupler below the deck plate, radially out under the plate to the N1 (N4) junction's place, up through the
            # plate's hole into the junction from below: far from the flange (REF) and over no part [IR]
            sg = -1 if s_ == "A" else 1
            th = math.radians(self.th_lead[s_])
            u3 = np.array([math.sin(te) * math.cos(th), math.sin(te) * math.sin(th), sg * math.cos(te)])
            hub0 = np.array([0.0, 0.0, self.zc])
            p1, p2 = hub0 + (Ro + 2.0 * rho) * u3, hub0 + (34.0 / math.sin(te)) * u3
            Jr = Jxy[n1]
            p3 = Jr + [0.0, 0.0, p2[2]]
            self.put_wire(f"{s_}_ring_lead", [p1, p2, p3, Jr + zh(ML.DECK_Z0 + ML.DECK_T)], n1, "wiring", f"ring-{s_}",
                          desc=f"ring {s_}'s lead: through the PEEK and the coupler, out under the deck, up to the N{n1} junction")
            self.put_wire(f"{s_}_ring_lead_deck", [Jr + zh(ML.DECK_Z0 + ML.DECK_T), Jr + zh(j_in)], n1, g, jn,
                          desc=f"ring {s_}'s lead: up through the plate into the junction, in the potting")
        # the cross nets and their bracket
        for n, ja, jb in (("2", "2", "2x"), ("3", "3x", "3")):
            c = np.array([*DECK["deck_A"]["junctions"][ja], 0.0])
            cb = np.array([*DECK["deck_B"]["junctions"][jb], 0.0])
            assert np.linalg.norm(c - cb) < 1e-6
            za = lambda h, c=c: c + [0.0, 0.0, self.zz("A", h)]                                       # noqa: E731
            zb = lambda h, c=c: c + [0.0, 0.0, self.zz("B", h)]                                       # noqa: E731
            self.put_wire(f"A_cross_{n}", [za(j_in), za(h_face)], n, "deck-A", "deck-A", desc=f"N{n}, in deck A's potting")
            self.put_wire(f"cross_{n}", [za(h_face), zb(h_face)], n, "wiring", f"cross-{n}",
                          desc=f"the cross net N{n}: straight across between the decks, held by the bracket")
            self.put_wire(f"B_cross_{n}", [zb(h_face), zb(j_in)], n, "deck-B", "deck-B", desc=f"N{n}, in deck B's potting")
        self.bracket()

    def open_way(self, d, ta, tb):
        sticks = [TG._ang(q["centre"]) for q in d["parts"] if q["kind"] == "stick"]
        best = None
        for dtt in ((tb - ta) % 360.0, (tb - ta) % 360.0 - 360.0):
            m = min(abs((ta + dtt * f - s + 540.0) % 360.0 - 180.0) for f in np.linspace(0, 1, 60) for s in sticks)
            if best is None or m > best[0]:
                best = (m, dtt)
        return best[1]

    def bracket(self):
        """the cross wires' support: bracket B (rebuild/s2_models/s2_bracket.py; the designer: "go with B"), in V1b's
        form: the two cross wires sit on opposite sides (s2_deck_symmetry.py), so each of two identical G10 arms holds
        one wire and the arms balance each other; the wire-to-wire path P1 is gone, and each arm keeps its mica
        barriers across it (P2, wire to the coupler): 0.3 mm muscovite in sawn slots, proud of both faces and past
        both edges. A split G10 collar round the coupler at the midplane carries both arms."""
        br = [v for v in json.load(open(os.path.join(HERE, "s2_bracket_results.json")))["variants"]
              if v["name"].startswith("B:")][0]
        T, M_SEAT, H_BAR, T_MICA, SLOT = 6.0, 8.0, 8.0, 0.3, 0.4      # s2_bracket.py variant_B's sizes [IR]
        C_T, C_H, C_GAP = 6.0, 12.0, 1.0                              # the collar: radial wall, height, split gap
        r_c0, r_c1 = CPL_R1, CPL_R1 + C_T
        xA = DECK["deck_A"]["junctions"]
        wires = [np.array(xA["2"]), np.array(xA["3x"])]
        r_w = float(np.mean([np.linalg.norm(p) for p in wires]))
        w = 2 * (WIRE + M_SEAT)
        x_end = r_w + WIRE + M_SEAT
        # the barriers across the arm, counted for this deck's wire radius: the plain path from the seat to the collar's
        # face plus 2 H_BAR per barrier must meet variant B's need (G10, the worst group on the path) [OC]
        L2 = r_w - WIRE - r_c1
        k2 = max(0, math.ceil((br["P2"]["need_mm"] - L2) / (2 * H_BAR)))
        p2_have = L2 + 2 * k2 * H_BAR
        xs = [r_c1 + (k + 1) * L2 / (k2 + 1) for k in range(k2)]

        def barriers(t_):
            return TG.fuse([TG.box(x_ - 0.5 * t_, x_ + 0.5 * t_, -0.5 * w - H_BAR, 0.5 * w + H_BAR, -0.5 * T - H_BAR,
                                   0.5 * T + H_BAR) for x_ in xs])

        def arm():
            a = TG._cut(TG.box(r_c1, x_end, -0.5 * w, 0.5 * w, -0.5 * T, 0.5 * T), barriers(SLOT))
            return TG._cut(a, TG.cyl_z(r_w, 0.0, WIRE + 0.05, -T, T))
        self.proto("brk_arm", arm, COL["g10"], f"G10 arm, 6 mm, {w:.0f} wide, one drilled wire seat, sawn slots for "
                                               "the mica (bracket B, one wire per arm)")
        self.proto("brk_mica", lambda: barriers(T_MICA), (0.78, 0.66, 0.38),
                   f"mica barriers, 0.3 mm muscovite: {k2} across the arm, {H_BAR:g} mm proud (bracket B)")
        half = lambda a0: TG.sector(r_c0, r_c1, -0.5 * C_H, 0.5 * C_H, a0 + math.degrees(0.5 * C_GAP / r_c1),   # noqa: E731
                                    180.0 - math.degrees(C_GAP / r_c1))
        self.proto("brk_collar_half", lambda: half(-90.0), COL["g10"],
                   "G10 split collar half, 6 x 12 mm, clamped round the coupler (two screws across each split, not drawn)")
        angs = [TG._ang(p) for p in wires]
        for k, (nm, th) in enumerate((("N2", angs[0]), ("N3", angs[1]))):
            self.put(f"xbracket_arm_{nm}", "brk_arm", None, None, None, "rotor", "wiring", join="xbracket", rot=th,
                     dz=self.zc, desc=f"bracket B: the G10 arm carrying the cross wire {nm}")
            self.put(f"xbracket_arm_{nm}_mica", "brk_mica", None, None, None, "rotor", "wiring", join="xbracket", rot=th,
                     dz=self.zc, desc="bracket B: its mica barriers")
            self.put(f"xbracket_collar_{k + 1}", "brk_collar_half", None, None, None, "rotor", "wiring", join="xbracket",
                     rot=th, dz=self.zc, desc="bracket B: the split collar's half, on the coupler")
        lo, hi = TG.bbox(self.protos["brk_mica"][0])
        alo, ahi = TG.bbox(self.protos["brk_arm"][0])
        self.bracket_B = dict(form="one wire per arm (V1b)", arm_mm=dict(r=(r_c1, x_end), width=w, thickness=T),
                              collar_mm=dict(r=(r_c0, r_c1), h=C_H), arms_deg=angs,
                              wires_apart_mm=float(np.linalg.norm(wires[0] - wires[1])),
                              barriers=dict(across=k2, proud_mm=H_BAR, t_mm=T_MICA, x_mm=xs),
                              P2=dict(have_mm=p2_have, need_mm=br["P2"]["need_mm"], plain_mm=L2, group=br["P2"]["group"],
                                      ok=bool(p2_have >= br["P2"]["need_mm"])),
                              P1="none: the wires are on opposite sides",
                              coverage=dict(proud_of_faces_mm=[float(alo[2] - lo[2]), float(hi[2] - ahi[2])],
                                            past_edges_mm=[float(alo[1] - lo[1]), float(hi[1] - ahi[1])],
                                            pass_=bool(min(alo[2] - lo[2], hi[2] - ahi[2], alo[1] - lo[1],
                                                           hi[1] - ahi[1]) >= H_BAR - 1e-6)),
                              source="rebuild/s2_models/s2_bracket_results.json variant B; s2_deck_symmetry V1b")

# ---------------------------------------------------------------------------------------------------------- checks
def checks(m, log=print):
    """G-CLASH (no two solids share volume, the intended joins excepted), G-SWEEP (no counter-rotor solid in a rotor
    solid's revolved envelope), G-AIR (every two conductors of different nets, outside the designed 6 mm cells and the
    potting, at least the bare clearance of their pair's peak apart)."""
    from OCP.BRepAlgoAPI import BRepAlgoAPI_Common
    from OCP.BRepExtrema import BRepExtrema_DistShapeShape
    import motor_geometry as MG
    shapes = [(pt, m.placed(pt)) for pt in m.parts]
    boxes = [TG.bbox(s) for _, s in shapes]
    clash, n_pairs = [], 0
    for i in range(len(shapes)):
        for j in range(i + 1, len(shapes)):
            (a, sa), (b, sb) = shapes[i], shapes[j]
            (amin, amax), (bmin, bmax) = boxes[i], boxes[j]
            if np.any(amax < bmin - 1e-6) or np.any(bmax < amin - 1e-6) or a["join"] == b["join"]:
                continue
            n_pairs += 1
            v = MG.props(BRepAlgoAPI_Common(sa, sb).Shape())["volume"]
            if v > 1e-3:
                clash.append((a["name"], b["name"], round(v, 3)))
    res = dict(G_CLASH=dict(pairs_tested=n_pairs, n_clash=len(clash), clashes=clash[:30], pass_=not clash))
    log(f"G-CLASH: {n_pairs} pairs, {len(clash)} clashes")

    # G-SWEEP, as sim/tube_geometry.py checks() does it: each rotor solid revolved into an annulus (its mesh's radial
    # extent, its z extent) against every counter-rotor solid; any shared volume is a hit [OC]
    hits = []
    stator = [(pt, s) for pt, s in shapes if pt["body"] == "stator"]
    for pr, sr in shapes:
        if pr["body"] != "rotor" or pr["proto"].startswith(("shaft", "sleeve", "flange")):
            continue
        lo, hi = TG.bbox(sr)
        P = MG.mesh_points(sr, 1.0)
        rr = np.hypot(P[:, 0], P[:, 1])
        ring = MG.annulus(max(0.0, rr.min() - 0.05), rr.max() + 0.05, lo[2] - 0.05, hi[2] + 0.05)
        rlo, rhi = TG.bbox(ring)
        for ps, ss in stator:
            slo, shi = TG.bbox(ss)
            if np.any(shi < rlo) or np.any(rhi < slo):
                continue
            if MG.props(BRepAlgoAPI_Common(ring, ss).Shape())["volume"] > 1e-3:
                hits.append((pr["name"], ps["name"]))
    res["G_SWEEP"] = dict(n_hits=len(hits), hits=hits[:30], pass_=not hits,
                          note="each rotor solid revolved into an annulus against every counter-rotor solid")
    log(f"G-SWEEP: {len(hits)} hits")
    # G-AIR
    V = m.V
    cond = []
    for k, (pt, s) in enumerate(shapes):
        nv = m.nets.get(pt["name"], {})
        n = nv.get("net")
        if n and n != "lv":
            cond.append((k, "0" if n == "s" else n))
        elif "nets" in nv:
            cond.append((k, tuple(nv["nets"])))
    if hasattr(m, "bracket_B"):
        res["bracket_B"] = m.bracket_B
    cell = lambda a, b: any(x in a["name"] for x in ("_C1_", "_C2_", "_Ca_", "_Cb_")) and \
        any(x in b["name"] for x in ("_C1_", "_C2_", "_Ca_", "_Cb_"))                       # the designed cells
    potted = lambda a: a["group"].startswith("deck-")                                       # inside the potting
    on_sleeve = lambda a, b: {a["name"].split("_")[0], b["name"].split("_")[0]} & {"shaft"} and         any(("_C1_r" in x["name"] or "_C2_r" in x["name"]) for x in (a, b))               # through the G10 sleeve
    rows, worst = [], None
    for ii in range(len(cond)):
        for jj in range(ii + 1, len(cond)):
            (i, ni), (j, nj) = cond[ii], cond[jj]
            a, b = shapes[i][0], shapes[j][0]
            if cell(a, b) or (potted(a) and potted(b)) or on_sleeve(a, b):
                continue
            na = ni if isinstance(ni, tuple) else (ni,)
            nb = nj if isinstance(nj, tuple) else (nj,)
            u = max(ML.volt(V, x, y)["pk"] for x in na for y in nb)
            if u <= 0:
                continue
            need = ML.clearance(u)
            (amin, amax), (bmin, bmax) = boxes[i], boxes[j]
            if np.any(amax + need < bmin) or np.any(bmax + need < amin):
                continue
            ext = BRepExtrema_DistShapeShape(shapes[i][1], shapes[j][1])
            dd = ext.Value()
            # a diode or string body grades from its first net to its second along its axis (sim/multiplier_layout.py
            # pieces) [IR]: at the closest point the peak is the bound of the graded potential against the other
            for which, (k, nk, nother) in enumerate(((i, ni, nj), (j, nj, ni))):
                ax = m.nets.get(shapes[k][0]["name"], {}).get("axis")
                if ax and isinstance(nk, tuple):
                    pnt = ext.PointOnShape1(1) if which == 0 else ext.PointOnShape2(1)
                    p0, p1 = np.array(ax[0]), np.array(ax[1])
                    x = np.array([pnt.X(), pnt.Y(), pnt.Z()])
                    f = float(np.clip((x - p0) @ (p1 - p0) / ((p1 - p0) @ (p1 - p0)), 0.0, 1.0))
                    other = nother if isinstance(nother, tuple) else (nother,)
                    u = max(ML.u_bound(V, {nk[0]: 1.0 - f, nk[1]: f}, {o: 1.0}) for o in other)
                    need = ML.clearance(u) if u > 0 else 0.0
            if dd < need:
                rows.append(dict(a=a["name"], b=b["name"], U_pk_kV=round(u, 2), gap_mm=round(dd, 1), need_mm=round(need, 1)))
    res["G_AIR"] = dict(n_short=len(rows), shorts=sorted(rows, key=lambda r: r["gap_mm"] - r["need_mm"])[:60],
                        pass_=not rows, rule="IEC 60664-1 case A at 1.5 x the peak (sim/multiplier_layout.py clearance); "
                                             "the 6 mm cells (vanes, Ca) and potted-to-potted pairs excepted")
    log(f"G-AIR: {len(rows)} pairs short of the bare clearance")
    # G-POT: inside the potting, every two conductors of different nets at least U / E_POT apart (sim/parts_first_cut.py
    # E_POT, the deck study's solid rule), the diode bodies graded along their axes as in G-AIR
    import parts_first_cut as PF
    pot_rows = []
    for ii in range(len(cond)):
        for jj in range(ii + 1, len(cond)):
            (i, ni), (j, nj) = cond[ii], cond[jj]
            a, b = shapes[i][0], shapes[j][0]
            if not (potted(a) and potted(b)):
                continue
            na = ni if isinstance(ni, tuple) else (ni,)
            nb = nj if isinstance(nj, tuple) else (nj,)
            if set(na) & set(nb) and (len(na) == 1 or len(nb) == 1):
                continue                                   # a conductor joined to a part's end (same net)
            u = max(ML.volt(V, x, y)["pk"] for x in na for y in nb)
            if u <= 0:
                continue
            need = u / PF.E_POT
            (amin, amax), (bmin, bmax) = boxes[i], boxes[j]
            if np.any(amax + need < bmin) or np.any(bmax + need < amin):
                continue
            ext = BRepExtrema_DistShapeShape(shapes[i][1], shapes[j][1])
            dd = ext.Value()
            for which, (k, nk, nother) in enumerate(((i, ni, nj), (j, nj, ni))):
                ax = m.nets.get(shapes[k][0]["name"], {}).get("axis")
                if ax and isinstance(nk, tuple):
                    pnt = ext.PointOnShape1(1) if which == 0 else ext.PointOnShape2(1)
                    p0, p1 = np.array(ax[0]), np.array(ax[1])
                    x = np.array([pnt.X(), pnt.Y(), pnt.Z()])
                    f = float(np.clip((x - p0) @ (p1 - p0) / ((p1 - p0) @ (p1 - p0)), 0.0, 1.0))
                    other = nother if isinstance(nother, tuple) else (nother,)
                    u = max(ML.u_bound(V, {nk[0]: 1.0 - f, nk[1]: f}, {o: 1.0}) for o in other)
                    need = u / PF.E_POT
            if dd < need:
                pot_rows.append(dict(a=a["name"], b=b["name"], U_pk_kV=round(u, 2), gap_mm=round(dd, 2),
                                     need_mm=round(need, 2)))
    res["G_POT"] = dict(n_short=len(pot_rows), shorts=sorted(pot_rows, key=lambda r: r["gap_mm"] - r["need_mm"])[:40],
                        pass_=not pot_rows, rule=f"in the potting, U / {PF.E_POT:g} kV/mm (sim/parts_first_cut.py E_POT)")
    log(f"G-POT: {len(pot_rows)} potted pairs short of the solid rule")
    # G-CREEP: along the rotor sleeve's G10 surface, from the rotor vanes (N1 / N4, which sit on it) to the REF parts at
    # its ends (the flange's coupler at h 80, the REF link's bearing); the rule as the redesign's (sim/doubler_caps.py
    # rules): IEC 60664-1 PD2 creepage x 1.25 DC on the rms, G10 group IIIa, PTFE group I if covered
    import parts_first_cut as PF
    q = ML.volt(V, "0", "1")
    need_g10 = PF.creepage(q["rms"], "IIIa") * PF.DC_MARGIN
    need_ptfe = PF.creepage(q["rms"], "I") * PF.DC_MARGIN
    t = VANE["t"]
    first, last = m.h_vanes0, m.h_vanes0 + (VANE["n_vanes"] - 2) * (t + VANE["g"]) + t
    paths = dict(to_flange=first - FL_Z1, to_bearing=m.h_brg0 - last)
    res["G_CREEP"] = dict(U_rms_kV=q["rms"], need_G10_mm=need_g10, need_PTFE_cover_mm=need_ptfe, paths_mm=paths,
                          pass_=all(v >= need_g10 for v in paths.values()),
                          note="the rotor vanes' rings sit on the sleeve; its surface runs to REF at both ends")
    log(f"G-CREEP: sleeve paths {paths} mm against {need_g10:.0f} (G10) / {need_ptfe:.0f} (PTFE cover) needed")
    return res


def net_check(m):
    groups = {}
    for nm, v in m.nets.items():
        if v.get("net"):
            groups.setdefault(v["net"], []).append(nm)
    want = {"1": ["hub_ring_A", "A_J_1", "A_ring_lead", "A_C1_r01", "A_Ca_05"],
            "4": ["hub_ring_B", "B_J_4", "B_ring_lead", "B_C2_r01", "B_Cb_05"],
            "2": ["A_J_2", "cross_2", "B_J_2x", "A_Ca_06"], "3": ["B_J_3", "cross_3", "A_J_3x", "B_Cb_06"],
            "0": ["shaft_A", "A_flange", "A_ref_bearing"], "s": ["A_C1_s02", "A_ref_spider"]}
    res = {n: dict(missing=[x for x in names if x not in set(groups.get(n, []))], n=len(groups.get(n, [])))
           for n, names in want.items()}
    res["pass_"] = all(not v["missing"] for v in res.values())
    return res


def to_fcstd(step, fcstd, timeout_s=900):
    """the FreeCAD document from the STEP through FreeCAD's GUI program, so its parts display (a document written by
    freecadcmd has no view providers and opens blank)."""
    d = tempfile.mkdtemp()
    done = os.path.join(d, "done.txt")
    still = fcstd.replace(".FCStd", "-view.png")
    lines = ["import FreeCAD, FreeCADGui, ImportGui", "from PySide import QtCore",
             "doc = FreeCAD.newDocument('s2_tube')", f"ImportGui.insert(r'{step}', doc.Name)", "doc.recompute()",
             "v = FreeCADGui.getDocument(doc.Name).activeView()", "v.viewIsometric()", "v.fitAll()",
             "FreeCADGui.updateGui()", f"v.saveImage(r'{still}', 1600, 1000, 'White')", f"doc.saveAs(r'{fcstd}')",
             f"open(r'{done}', 'w').write('objects %d' % len(doc.Objects))",
             "QtCore.QTimer.singleShot(500, FreeCADGui.getMainWindow().close)"]
    macro = os.path.join(d, "make_fcstd.py")
    open(macro, "w").write("\n".join(lines) + "\n")
    p = subprocess.Popen([FREECAD_EXE, macro])
    t0 = time.time()
    while not os.path.exists(done) and time.time() - t0 < timeout_s:
        time.sleep(2)
    ok = os.path.exists(done)
    msg = open(done).read() if ok else "timed out"
    try:
        p.wait(timeout=60)
    except subprocess.TimeoutExpired:
        p.kill()
    return dict(ok=ok, result=msg, still=os.path.relpath(still, ROOT).replace(os.sep, "/"))


def main():
    t0 = time.time()
    log = lambda s: print(s, flush=True)                                                     # noqa: E731
    os.makedirs(OUT_DIR, exist_ok=True)
    m = S2Core().build()
    log(f"{TAG}: {len(m.parts)} solids from {len(m.protos)} prototypes, {m.L_mm:.0f} mm; column at h {m.h_col:.0f} "
        f"({m.col_need}); vanes h {m.h_vanes0:.0f}-{m.h_vanes1:.0f}; REF link at h {m.h_brg0:.0f}")
    res = dict(tag=TAG, status="PROPOSED (S2a from scratch, 2026-10-16)",
               source="rebuild/s2_models/s2_deck_bare_nocan_results.json (the decks, the bracket, the volts); "
                      "sim/air_stack_sizing_results.json thick_vanes (the vane stack of record); presets/hub-locked.json "
                      "(the hub, the 2 mm wall); sim/tube_geometry.py (primitives, locked_hub; the AH dropped)",
               n_parts=len(m.parts), n_protos=len(m.protos), L_total_mm=m.L_mm, hub_centre_z_mm=m.zc,
               stack=dict(h_col_mm=m.h_col, column_needs_mm=m.col_need, h_vanes_mm=[m.h_vanes0, m.h_vanes1],
                          h_ref_bearing_mm=m.h_brg0, h_end_mm=m.h_end),
               open_items=["the ties between the plates of one net (the column's node 1 / node 2, the rotor vanes to the "
                           "column, the stator vanes' REF bus)", "the column's mechanical support",
                           "the riser and the tap from the deck to the column", "the joint between the counter-rotor's "
                           "halves", "the drive", "the decks' plate fixing on the coupler"])
    res["NETS"] = net_check(m)
    log(f"nets: {json.dumps(res['NETS'])}")
    res.update(checks(m, log))
    json.dump(dict(parts=m.parts, nets=m.nets, zc_mm=m.zc, L_mm=m.L_mm),
              open(os.path.join(OUT_DIR, f"{TAG}.parts.json"), "w"), indent=0, default=float)
    if "--no-step" not in sys.argv:
        path = TG.write_step(m, os.path.join(OUT_DIR, f"{TAG}.step"))
        res["step"] = os.path.relpath(path, ROOT).replace(os.sep, "/")
        res["step_bytes"] = os.path.getsize(path)
        rb = TG.read_back(path)
        res["step_read_back"] = dict(rb, pass_=rb["instances"] == len(m.parts))
        if "--no-fcstd" not in sys.argv and os.path.exists(FREECAD_EXE):
            fc = os.path.join(OUT_DIR, f"{TAG}.FCStd")
            res["fcstd"] = dict(to_fcstd(os.path.abspath(path), os.path.abspath(fc)),
                                path=os.path.relpath(fc, ROOT).replace(os.sep, "/"))
    res["run_s"] = round(time.time() - t0)
    json.dump(res, open(os.path.join(HERE, "s2_geometry_results.json"), "w"), indent=1, default=float)
    for k in ("G_CLASH", "G_SWEEP", "G_AIR", "G_POT", "bracket_B", "step_read_back", "fcstd"):
        if k in res:
            log(f"{k}: {json.dumps(res[k], default=float)[:900]}")


if __name__ == "__main__":
    main()
