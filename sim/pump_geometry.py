#!/usr/bin/env python3
"""
sim/pump_geometry.py — PUMP-SYNTH stage 2: a LOCKED stage-1 design -> capacitor plate geometry
==============================================================================================
Stage 1 (sim/pump_sizing.py + the exact engine) fixes the capacitances. Stage 2 turns them into plates:
electrode footprints (annular sectors on named carrier discs), dielectric slabs and an axial stack that a
3-D package can check for geometric feasibility. Mirrored 1:1 in JS (tools/pump-geometry.js, gate G-JS);
the FreeCAD macro tools/pump-geometry.FCMacro builds the 3-D model from this module's JSON (gate G-CAD).

First cut (TMD, 2026-10-01): **Ca / Cb are geometrized**; every other electrode is placed as LOCKED CONTEXT
from the r0.15 DXF part views (radii, 30-degree sector sets) so the plate distribution is complete.

Seed, read off docs/varcap-nodeanalysis-template-r0.15_TMD_layout.dxf (the "Ca electrodes", "Cb electrodes"
and "stack section (assembly)" frames) and docs/varcap-design-freeze-v0.10.md §3 [OC]:
  ND1 C1 stator plate   r95-387, odd sectors (30-60, 90-120, ...)      ND4 C2 stator  r95-387, even sectors
  ND9/ND10 rotor faces  r75-387, odd sectors                           (C1 / C2 rotor faces, nodes 5 / 6)
  ND2 Ca electrode      r110-175, odd sectors  (faces ND1 through 4.5 mm mica)
  ND3 Cb electrode      r110-175, even sectors (faces ND4 through 4.5 mm mica)
  ND2 Cx4 pickup        r58-350, even sectors   ND8 island bars (on A) r75-350, even sectors
  ND3 Cx3 pickup        r58-350, odd sectors    ND7 island bars (on B) r75-350, odd sectors
  6 x 30 deg of r110-175 = 0.029099 m^2 -> 309.18 pF on 4.5 mm mica (eps_r 5.4): the DXF and the freeze agree.

Axial stack (NOT in the DXF -- its "stack section" frame is a plan overlay). Seeded with the one order in which
every capacitor's two electrodes face each other across exactly its own dielectric [IR, confirm in CAD]:
each rotor half is a clamshell around its stator pair --
  A flange (ND8 bars) | Cx4 gap | ND2 carrier | Ca mica | ND1 carrier | C1 air | A disc (ND9) | septum (C_R) |
  B disc (ND10) | C2 air | ND4 carrier | Cb mica | ND3 carrier | Cx3 gap | B flange (ND7 bars)
Stator "plates" are insulating carriers with foil electrodes on their faces (both faces of ND2/ND3 carry
different electrodes of the same node in complementary sectors, so a solid metal plate would not realize the
drawn areas) [IR]. Thicknesses of carriers / foils are placeholders [IR]; the gaps are the stage-1 / freeze
values [OC]. adjacency() checks the stack (gate G-ADJ).

Model of each capacitor: ideal parallel plate over the overlap of its two footprints, C = eps0 eps_r A / t
(no fringing: [OC] law, fringing out of scope as in Block C-I). Tags [OC]/[IR]/[RH]/[ME]. No file I/O on import.
"""
import hashlib
import json
import math
from decimal import Decimal, ROUND_HALF_UP

EPS0 = 8.8541878128e-12
SCHEMA = "pump-geometry/1"
DIELECTRICS = {"mica": 5.4, "mylar": 3.2, "kapton": 3.4, "pp_film": 2.2, "garolite": 4.7, "air": 1.0006}
ODD = [30.0 + 60.0 * k for k in range(6)]     # sector start angles (deg), 30-degree sectors [OC DXF]
EVEN = [60.0 * k for k in range(6)]

GEOM_DEFAULTS = dict(
    # Ca / Cb (the geometrized pair) -- DXF / freeze seed
    ca_diel="mica", ca_t=4.5,                 # dielectric and its thickness (mm)            [OC freeze]
    ca_w=30.0,                                # sector width (deg); the sector COUNT is the locked n_kept
                                              # (Ca/Cb sit in their counter-plate's kept sectors) [OC DXF]
    ca_mode="r_out",                          # solve: 'r_out' (r_in pinned) | 'r_in' (r_out pinned) | 'width' | 'forward'
    ca_rin=110.0, ca_rout=175.0,              # mm (the pinned one is used; the other is solved) [OC DXF]
    ca_round=0.0,                             # manufacturing step on the solved dimension (mm or deg; 0 = exact)
    ca_margin=5.0,                            # dielectric overlap margin around the foil (mm, radial and arc) [IR]
    # stack placeholders [IR]
    t_foil=1.0, t_carrier=3.0, t_rotor=10.0, t_flange=6.0, t_septum=12.0,
    cx_air=3.0, cx_mica=0.3,                  # Cx gap: air + mica per face (freeze v0.10) [OC]
    r_bore=50.0,                              # stator carrier bore (mm), clears the hub/coil r28-76 bicone [IR]
    rotor_in_off=20.0,                        # rotor face r_in = active r_in - 20 (DXF 75 vs 95) [IR]
    # ---- spark gaps (freeze v0.10 §5 table; placement [IR]) ----
    sg_rg=345.0,                              # bar-track radius (load / fire / backstop), freeze ~r340-350 [OC freeze]
    sg_rret=285.0,                            # rail-track radius (SG1/SG2 returns), its own plane [IR]
    sg_d=12.0, sg_dbs=25.0,                   # W-Cu switching sphere / smooth backstop electrode (mm) [OC freeze]
    sg_s_ret=5.5, sg_s_load=4.75, sg_s_fire=5.5, sg_s_bs=5.5,   # spacings at alignment (mm); BS: [IR] (freeze TODO)
    sg_glat=1.0,                              # lateral gap for the I11 overlap law (design_synth) [IR]
    sg_clear=5.0,                             # clearance plane-to-plane / plane-to-flange (mm) [IR]
    sg_rod=6.0,                               # post / arm / lead rod diameter (mm) [IR]
    sg_rhub=35.0,                             # rail arms run axially through the stator bores at this radius [IR]
    sg_frame=60.0,                            # stationary lead frame radius = carrier edge + this (over the stator) [IR]
    sg_khv=2.0,                               # HV clearance >= k x the largest spacing, different nodes [IR]
)


def _round(x, step):
    """Manufacturing step, half-up (identical in the JS mirror; Python's round() is half-even)."""
    return x if not step else math.floor(x / step + 0.5) * step


def sector_area(rin, rout, w_deg, n):
    """Area of n annular sectors (mm^2)."""
    return 0.5 * math.radians(w_deg) * max(0.0, rout * rout - rin * rin) * n


def cap_pF(area_mm2, t_mm, eps_r):
    return EPS0 * eps_r * area_mm2 * 1e-6 / (t_mm * 1e-3) * 1e12


def solve_transfer(C_pF, g, n):
    """Ca/Cb inverse: the electrode footprint for a target capacitance. Returns the geometry, the realized C
    (after the manufacturing rounding) and the deviation."""
    er = DIELECTRICS[g["ca_diel"]]
    A = C_pF * 1e-12 * g["ca_t"] * 1e-3 / (EPS0 * er) * 1e6          # mm^2 needed [OC] Eq. (20)
    w, rin, rout = g["ca_w"], g["ca_rin"], g["ca_rout"]
    k = 0.5 * math.radians(w) * n                                    # A = k (rout^2 - rin^2)
    mode = g["ca_mode"]
    note = ""
    if mode == "r_out":
        rout = _round(math.sqrt(rin * rin + A / k), g["ca_round"])
    elif mode == "r_in":
        d = rout * rout - A / k
        if d < 0:
            rin, note = 0.0, "target area exceeds the full disc inside r_out: r_in clamped to 0"
        else:
            rin = _round(math.sqrt(d), g["ca_round"])
    elif mode == "width":
        w = _round(math.degrees(A / (0.5 * n * (rout * rout - rin * rin))), g["ca_round"])
    elif mode != "forward":
        raise ValueError(mode)
    area = sector_area(rin, rout, w, n)
    C = cap_pF(area, g["ca_t"], er)
    return dict(C_target_pF=C_pF, C_pF=C, dC_rel=(C - C_pF) / C_pF, area_mm2=area, area_needed_mm2=A,
                r_in=rin, r_out=rout, w_deg=w, n=n, t=g["ca_t"], diel=g["ca_diel"], eps_r=er, mode=mode, note=note)


def _fp(name, node, cap, rin, rout, starts, w):
    return dict(name=name, node=node, cap=cap, r_in=rin, r_out=rout, starts=list(starts), w_deg=w)


def build(locked, geom=None):
    """locked: the stage-1 lock record (inputs, ladder values, z). Returns the full geometry design (JSON-safe)."""
    g = dict(GEOM_DEFAULTS); g.update(geom or {})
    L = locked["ladder"]; P = locked["plates"]
    nk = int(P["n_kept"])
    ca = solve_transfer(L["Ca"], g, nk)                              # Cb uses the same geometry spec
    cb = solve_transfer(L["Cb"], g, nk)
    ri, ro = P["r_inMm"], P["r_outMm"]
    rr_in = max(0.0, ri - g["rotor_in_off"])
    # plate-carrier outer radius: the DXF R500 plate edge, scaled with the active band [IR]
    r_edge = ro * 500.0 / 387.0
    cx_rin, cx_rout = ro * 58.0 / 387.0, ro * 350.0 / 387.0         # Cx pickups, DXF ratios [IR]
    bar_rin = ro * 75.0 / 387.0
    sb = P["N_sec"]
    w_sec = 360.0 / sb
    odd = [w_sec + 2 * w_sec * k for k in range(sb // 2)]
    even = [2 * w_sec * k for k in range(sb // 2)]
    ca_starts = [s + (w_sec - ca["w_deg"]) / 2 for s in odd]         # centred in the facing sector
    cb_starts = [s + (w_sec - cb["w_deg"]) / 2 for s in even]
    fp = dict(
        C1_stator=_fp("C1 stator plate", "1", "C1", ri, ro, odd, w_sec),
        C1_rotor=_fp("C1 rotor face", "5", "C1", rr_in, ro, odd, w_sec),
        C2_stator=_fp("C2 stator plate", "4", "C2", ri, ro, even, w_sec),
        C2_rotor=_fp("C2 rotor face", "6", "C2", rr_in, ro, odd, w_sec),
        Ca_el=_fp("Ca electrode", "2", "Ca", ca["r_in"], ca["r_out"], ca_starts, ca["w_deg"]),
        Ca_counter=_fp("Ca counter (ND1 back face)", "1", "Ca", ri, ro, odd, w_sec),
        Cb_el=_fp("Cb electrode", "3", "Cb", cb["r_in"], cb["r_out"], cb_starts, cb["w_deg"]),
        Cb_counter=_fp("Cb counter (ND4 back face)", "4", "Cb", ri, ro, even, w_sec),
        Cx4_pickup=_fp("Cx4 pickup", "n23", "Cx4", cx_rin, cx_rout, even, w_sec),   # n23 -Lx4- node 2 (netlist)
        Cx4_bars=_fp("island bars on A", "8", "Cx4", bar_rin, cx_rout, even, w_sec),
        Cx3_pickup=_fp("Cx3 pickup", "n17", "Cx3", cx_rin, cx_rout, odd, w_sec),   # n17 -Lx3- node 3 (netlist)
        Cx3_bars=_fp("island bars on B", "7", "Cx3", bar_rin, cx_rout, odd, w_sec),
        CR_A=_fp("C_R face (rotor A)", "5", "C_R", rr_in, ro, [0.0], 360.0),
        CR_B=_fp("C_R face (rotor B)", "6", "C_R", rr_in, ro, [0.0], 360.0),
    )
    # ---- axial stack (z up, mm): a strict layer sequence from the septum outward, foils as their own layers
    #      (every gap value is foil-to-foil) [IR]; side A at z < 0, side B mirrored at z > 0 ----
    tf, tc = g["t_foil"], g["t_carrier"]
    gv, tcx = P["g_vMm"], g["cx_air"] + 2 * g["cx_mica"]
    cxm = f"air {g['cx_air']:g} + mica {g['cx_mica']:g}/face"

    def C(id_, kind, node, t, rin):
        return dict(id=id_, kind=kind, node=node, t=t, r_in=rin, r_out=r_edge)

    def F(key):
        return dict(id=key, kind="foil", key=key, t=tf)

    def G(id_, cap, t, medium, footprint=None, margin=0.0):
        return dict(id=id_, kind="gap", cap=cap, t=t, medium=medium, footprint=footprint, margin=margin)
    seqA = [F("CR_A"), C("A-disc", "rotor", "5", g["t_rotor"], 0.0), F("C1_rotor"), G("C1-gap", "C1", gv, "air"),
            F("C1_stator"), C("ND1", "stator", "1", tc, g["r_bore"]), F("Ca_counter"),
            G("Ca-diel", "Ca", ca["t"], ca["diel"], "Ca_el", g["ca_margin"]), F("Ca_el"),
            C("ND2", "stator", "2", tc, g["r_bore"]), F("Cx4_pickup"), G("Cx4-gap", "Cx4", tcx, cxm),
            F("Cx4_bars"), C("A-flange", "rotor-flange", "8 (floating on A)", g["t_flange"], 0.0)]
    seqB = [F("CR_B"), C("B-disc", "rotor", "6", g["t_rotor"], 0.0), F("C2_rotor"), G("C2-gap", "C2", gv, "air"),
            F("C2_stator"), C("ND4", "stator", "4", tc, g["r_bore"]), F("Cb_counter"),
            G("Cb-diel", "Cb", cb["t"], cb["diel"], "Cb_el", g["ca_margin"]), F("Cb_el"),
            C("ND3", "stator", "3", tc, g["r_bore"]), F("Cx3_pickup"), G("Cx3-gap", "Cx3", tcx, cxm),
            F("Cx3_bars"), C("B-flange", "rotor-flange", "7 (floating on B)", g["t_flange"], 0.0)]
    h = g["t_septum"] / 2
    stack = [dict(G("septum", "C_R", g["t_septum"], "garolite"), z0=-h, z1=h, side="mid", r_in=0.0, r_out=r_edge)]
    for side, seq, sgn in (("A", seqA, -1), ("B", seqB, +1)):
        zz = h
        for it in seq:
            it = dict(it); a, b = sgn * zz, sgn * (zz + it["t"])
            it.update(z0=min(a, b), z1=max(a, b), side=side)
            if it["kind"] == "foil":
                it.update(fp[it["key"]])
            stack.append(it); zz += it["t"]
    stack.sort(key=lambda it: it["z0"])
    foils = [it for it in stack if it["kind"] == "foil"]
    design = dict(schema=SCHEMA, units="mm", lock=dict(locked), geom=g, Ca=ca, Cb=cb, footprints=fp,
                  stack=stack, foils=foils, z_total=stack[-1]["z1"] - stack[0]["z0"], r_edge=r_edge)
    design["sparkgaps"] = sparkgaps(design)
    design["z_total"] = design["sparkgaps"]["z_max"] - design["sparkgaps"]["z_min"]
    design["checks"] = checks(design)
    for k, v in design["sparkgaps"]["checks"].items():
        design["checks"]["gaps: " + k] = v
    design["assemblies"], design["parts"] = parts(design)
    design["top_label"] = (f"PumpGeometry {locked.get('hash', '')} - DCCREG drawn pump, stage 2 plate geometry "
                           f"(Ca/Cb geometrized)")
    return design


# ---- the bill of solids: one entry per CAD solid, with its name and readable label. The CAD builders
#      (tools/pump-geometry.FCMacro, tools/fusion360/PumpGeometry) only build what this list says, so FreeCAD and
#      Fusion 360 name everything identically. Labels are ASCII (STEP names are ASCII). ----
NODE_RGB = {"1": (0.49, 0.82, 1.0), "2": (1.0, 0.71, 0.33), "3": (0.27, 0.77, 0.42), "4": (0.90, 0.28, 0.30),
            "5": (0.78, 0.57, 0.92), "6": (0.97, 0.46, 0.56), "7": (0.62, 0.81, 0.42), "8": (0.88, 0.69, 0.41),
            "n17": (0.55, 0.90, 0.80), "n23": (1.0, 0.88, 0.55)}


def node_rgb(node):
    n = str(node).split(" ")[0]
    return NODE_RGB.get(n, NODE_RGB.get(n[:1], CARRIER_RGB))
MEDIUM_RGB = {"garolite": (0.55, 0.50, 0.30), "mica": (0.75, 0.70, 0.55)}
CARRIER_RGB = (0.35, 0.40, 0.47)
MATERIAL = {"stator": "G10 carrier", "rotor": "rotor disc", "rotor-flange": "rotor flange (insulating)"}
CARRIER_ROLE = {"A-flange": "rotor A outer flange, carries the island bars (node 8, floating)",
                "B-flange": "rotor B outer flange, carries the island bars (node 7, floating)",
                "A-disc": "rotor A main disc (node 5): C1 rotor face + C_R face",
                "B-disc": "rotor B main disc (node 6): C2 rotor face + C_R face",
                "ND1": "stator carrier ND1 (node 1): C1 stator plate + Ca counter-electrode",
                "ND2": "stator carrier ND2 (node 2): Ca electrode + Cx4 pickup (node n23, via Lx4)",
                "ND3": "stator carrier ND3 (node 3): Cb electrode + Cx3 pickup (node n17, via Lx3)",
                "ND4": "stator carrier ND4 (node 4): C2 stator plate + Cb counter-electrode"}
CARRIER_KINDS = ("rotor", "stator", "rotor-flange")


def _mm(x):
    """2 decimals, half away from zero (= JS toFixed), trailing zeros dropped."""
    s = str(Decimal(x).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP))
    s = s.rstrip("0").rstrip(".") if "." in s else s
    return "0" if s in ("-0", "") else s


def _m360(x):
    return x % 360.0


def _zr(it):
    return f"z {_mm(it['z0'])}..{_mm(it['z1'])}"


# ---- spark gaps: the commutator in 3-D (TMD 2026-10-01: each load gap fires on its bar's side; the stator node
#      reaches it by a lead over the stator) [IR placement, OC netlist / stations] ----
# netlist of record (topology_edge_list.csv): gap -> (stator-side node, rotor-side electrode)
GAPS = (  # name, class, stator node, rotor electrode, side, track, station (deg, = DXF marker = engine st_*)
    ("SG1", "return", "2", "rail A (node 5)", "A", "rail", 3.00),
    ("SG4a1", "load", "4", "bar 8", "A", "bar", 37.20),
    ("SG4b1", "fire", "2", "bar 8", "A", "bar", 46.05),
    ("BS4", "backstop", "2", "bar 8", "A", "bar", 49.00),
    ("SG2", "return", "3", "rail B (node 6)", "B", "rail", 33.00),
    ("SG3a1", "load", "1", "bar 7", "B", "bar", 7.20),
    ("SG3b1", "fire", "3", "bar 7", "B", "bar", 16.05),
    ("BS3", "backstop", "3", "bar 7", "B", "bar", 19.00),
)
NETLIST_GAPS = {"SG1": ("2", "R-A"), "SG2": ("3", "R-B"), "SG3a1": ("1", "7"), "SG3b1": ("7", "3"), "BS3": ("7", "3"),
                "SG4a1": ("4", "8"), "SG4b1": ("8", "2"), "BS4": ("8", "2")}
ROTOR_NODE = {"rail A (node 5)": "R-A", "rail B (node 6)": "R-B", "bar 7": "7", "bar 8": "8"}
NODE_CARRIER = {"1": "ND1", "2": "ND2", "3": "ND3", "4": "ND4"}
SIDE_OF_CARRIER = {"ND1": "A", "ND2": "A", "ND3": "B", "ND4": "B"}
SPACING_KEY = {"return": "sg_s_ret", "load": "sg_s_load", "fire": "sg_s_fire", "backstop": "sg_s_bs"}
SPOKES = 6                                       # each gap x 6, every 60 deg (freeze §5)


def _pol(r, a_deg, z):
    a = math.radians(a_deg)
    return [r * math.cos(a), r * math.sin(a), z]


def sparkgaps(design):
    g = design["geom"]; st = design["stack"]; fp = design["footprints"]
    byid = {it["id"]: it for it in st}
    zA_out, zB_out = st[0]["z0"], st[-1]["z1"]               # flange outer faces (side A: z < 0)
    Rb = max(g["sg_d"], g["sg_dbs"]) / 2                     # largest electrode radius on a bar plane
    Rr = g["sg_d"] / 2
    planes = {}
    for side, zo, sgn in (("A", zA_out, -1), ("B", zB_out, +1)):
        zb = zo + sgn * (g["sg_clear"] + Rb)
        zr = zb + sgn * (Rb + g["sg_clear"] + Rr)
        planes[side] = dict(bar=zb, rail=zr)
    R_frame = design["r_edge"] + g["sg_frame"]
    rod = g["sg_rod"] / 2
    gaps, items = [], []                                     # items: geometry for the CAD part list

    def carrier_mid(cid):
        c = byid[cid]; return 0.5 * (c["z0"] + c["z1"])
    for name, cls, snode, rot, side, track, stn in GAPS:
        s_ = g[SPACING_KEY[cls]]
        d_rot = g["sg_d"]
        d_st = g["sg_dbs"] if cls == "backstop" else g["sg_d"]
        r_track = g["sg_rg"] if track == "bar" else g["sg_rret"]
        r_st = r_track + (d_rot + d_st) / 2 + s_                # stator sphere centre: radially outboard, in-plane
        z = planes[side][track]
        car = NODE_CARRIER[snode]; zc = carrier_mid(car)
        crossover = SIDE_OF_CARRIER[car] != side
        lead_len = (R_frame - r_st) + abs(z - zc) + (R_frame - design["r_edge"])
        gaps.append(dict(name=name, cls=cls, stator_node=snode, rotor=rot, side=side, track=track, station=stn,
                         spacing=s_, d_rotor=d_rot, d_stator=d_st, r_track=r_track, r_stator=r_st, z=z,
                         carrier=car, crossover=crossover, lead_len=lead_len))
        for k in range(SPOKES):
            a = stn + 60.0 * k
            ch = [f"lead-{name}-{k + 1}", car]
            items.append(dict(kind="sphere", name=f"{name}_el_{k + 1}", gap=name, node=snode, role="gap-stator",
                              c=_pol(r_st, a, z), r=d_st / 2, chains=ch, side=side,
                              desc=f"{name} stator electrode {k + 1} of {SPOKES} ({cls}), node {snode}, "
                                   f"{_mm(d_st)} mm {'smooth' if cls == 'backstop' else 'W-Cu'} sphere at r{_mm(r_st)} "
                                   f"{_mm(a % 360.0)} deg, deck {side} {track} plane z {_mm(z)}, gap {_mm(s_)} mm to {rot}"))
            items.append(dict(kind="rod", name=f"{name}_post_{k + 1}", gap=name, node=snode, role="gap-lead",
                              p0=_pol(r_st, a, z), p1=_pol(R_frame, a, z), r=rod, chains=ch, side=side,
                              desc=f"{name} post {k + 1}: electrode to the lead frame R{_mm(R_frame)}, node {snode}"))
            items.append(dict(kind="rod", name=f"{name}_riser_{k + 1}", gap=name, node=snode, role="gap-lead",
                              p0=_pol(R_frame, a, z), p1=_pol(R_frame, a, zc), r=rod, chains=ch, side=side,
                              desc=f"{name} lead {k + 1} along R{_mm(R_frame)} from deck {side} to {car} (node {snode})"
                                   + (" - CROSSOVER over the stator" if crossover else "")))
            items.append(dict(kind="rod", name=f"{name}_stub_{k + 1}", gap=name, node=snode, role="gap-lead",
                              p0=_pol(R_frame, a, zc), p1=_pol(design["r_edge"], a, zc), r=rod, chains=ch, side=side,
                              desc=f"{name} lead {k + 1} into the {car} carrier rim, node {snode}"))
    # rotor electrodes: tips at 0 mod 60 deg (so the fire angle = the station angle) [IR]
    for side, flange, bars, disc in (("A", "A-flange", "Cx4_bars", "A-disc"), ("B", "B-flange", "Cx3_bars", "B-disc")):
        zb, zr = planes[side]["bar"], planes[side]["rail"]
        bar = fp[bars]
        bar_node = bar["node"]
        zf = 0.5 * (byid[bars]["z0"] + byid[bars]["z1"])        # the arm starts inside its bar foil
        zd = 0.5 * (byid[disc]["z0"] + byid[disc]["z1"])
        rail_node = "5" if side == "A" else "6"
        for k in range(SPOKES):
            a = 60.0 * k
            chb = [f"bar-{side}", flange, bars]
            items.append(dict(kind="sphere", name=f"bartip_{side}_{k + 1}", gap="", node=bar_node, role="gap-rotor",
                              c=_pol(g["sg_rg"], a, zb), r=g["sg_d"] / 2, chains=chb, side=side,
                              desc=f"island bar {bar_node} tip {k + 1} of {SPOKES} (rotor {side}), {_mm(g['sg_d'])} mm W-Cu "
                                   f"sphere at r{_mm(g['sg_rg'])} {_mm(a)} deg, bar plane z {_mm(zb)}"))
            items.append(dict(kind="rod", name=f"bararm_{side}_{k + 1}", gap="", node=bar_node, role="gap-rotor",
                              p0=_pol(g["sg_rg"], a, zf), p1=_pol(g["sg_rg"], a, zb), r=rod, chains=chb, side=side,
                              desc=f"island bar {bar_node} arm {k + 1}: through the {flange} to its tip (rotates with rotor {side})"))
            chr_ = [f"rail-{side}", disc, flange]               # passes through its own rotor's disc and flange
            items.append(dict(kind="sphere", name=f"railtip_{side}_{k + 1}", gap="", node=rail_node, role="gap-rotor",
                              c=_pol(g["sg_rret"], a, zr), r=g["sg_d"] / 2, chains=chr_, side=side,
                              desc=f"rail tip {k + 1} of {SPOKES} (rotor {side}, node {rail_node}), {_mm(g['sg_d'])} mm W-Cu "
                                   f"sphere at r{_mm(g['sg_rret'])} {_mm(a)} deg, rail plane z {_mm(zr)}"))
            items.append(dict(kind="rod", name=f"railarm_{side}_{k + 1}a", gap="", node=rail_node, role="gap-rotor",
                              p0=_pol(g["sg_rhub"], a, zd), p1=_pol(g["sg_rhub"], a, zr), r=rod, chains=chr_, side=side,
                              desc=f"rail arm {k + 1} (node {rail_node}): from the {disc} through the stator bores at "
                                   f"r{_mm(g['sg_rhub'])} to the rail plane"))
            items.append(dict(kind="rod", name=f"railarm_{side}_{k + 1}b", gap="", node=rail_node, role="gap-rotor",
                              p0=_pol(g["sg_rhub"], a, zr), p1=_pol(g["sg_rret"], a, zr), r=rod, chains=chr_, side=side,
                              desc=f"rail arm {k + 1} (node {rail_node}): radial in the rail plane to its tip"))
    zs = [it["c"][2] - it["r"] for it in items if it["kind"] == "sphere"] + \
         [it["c"][2] + it["r"] for it in items if it["kind"] == "sphere"]
    out = dict(planes=planes, R_frame=R_frame, gaps=gaps, items=items,
               z_min=min(zs + [st[0]["z0"]]), z_max=max(zs + [st[-1]["z1"]]))
    out["checks"] = gap_checks(design, out)
    return out


def gap_checks(design, sg):
    g = design["geom"]; fp = design["footprints"]
    res = {}
    smax = max(g["sg_s_ret"], g["sg_s_load"], g["sg_s_fire"], g["sg_s_bs"])
    need = g["sg_khv"] * smax
    rod = g["sg_rod"] / 2
    # 1. every gap joins the netlist's nodes
    bad = [x["name"] for x in sg["gaps"] if set(NETLIST_GAPS[x["name"]]) != {x["stator_node"], ROTOR_NODE[x["rotor"]]}]
    res["nodes = netlist of record (topology_edge_list.csv)"] = (not bad, "all 8 gaps" if not bad else "mismatch: " + ", ".join(bad))
    # 2. alignment spacing
    worst = max(abs((x["r_stator"] - x["r_track"]) - (x["d_rotor"] + x["d_stator"]) / 2 - x["spacing"]) for x in sg["gaps"])
    res["spacing at alignment = the freeze table"] = (worst < 1e-9, "; ".join(f"{x['name']} {_mm(x['spacing'])}" for x in sg["gaps"]) + " mm")
    # 3. cross-fire: a tip aligned with one station is farther from every other different-node electrode on its plane
    worst_xf, det = float("inf"), ""
    for x in sg["gaps"]:
        tip = _pol(x["r_track"], x["station"], x["z"])
        for y in sg["gaps"]:
            if y is x or y["side"] != x["side"] or y["track"] != x["track"]:
                continue
            for k in range(SPOKES):
                c = _pol(y["r_stator"], y["station"] + 60.0 * k, y["z"])
                dist = math.dist(tip, c) - x["d_rotor"] / 2 - y["d_stator"] / 2
                if y["stator_node"] == x["stator_node"]:
                    continue
                margin = dist - max(x["spacing"], y["spacing"])
                if margin < worst_xf - 1e-9:                 # ties: the first in order (mirror decks tie exactly)
                    worst_xf, det = margin, f"{x['name']} tip vs {y['name']} electrode: {_mm(dist)} mm"
    res["no cross-firing to a different-node station"] = (worst_xf >= 0.5 * max(g["sg_s_load"], g["sg_s_fire"]),
                                                          f"tightest {det} (margin {_mm(worst_xf)} mm over its spacing)")
    # 4. the I11 overlap law at the PLACED radius (stage 1 judged it at the lock's r_gap)
    ov = math.degrees((g["sg_d"] + 2 * g["sg_glat"]) / g["sg_rg"])
    res["I11 cross-fire at the placed bar radius"] = (ov < 2.95, f"overlap {_mm(ov)} deg < SG3b-BS3 2.95 deg at r{_mm(g['sg_rg'])}")
    # 5. the tracks: bar tips on the bar foil, rail track inboard of the bar track, rail arms clear the stator bores
    bar = fp["Cx4_bars"]
    res["bar tip radius on the island bar"] = (bar["r_in"] + rod <= g["sg_rg"] <= bar["r_out"] - rod,
                                               f"r{_mm(g['sg_rg'])} within the bar r{_mm(bar['r_in'])}-{_mm(bar['r_out'])}")
    cl = g["r_bore"] - g["sg_rhub"] - rod
    res["rail arms clear the stator bores (HV)"] = (cl >= need, f"{_mm(cl)} mm >= {_mm(need)} mm ({_mm(g['sg_khv'])} x {_mm(smax)})")
    cl2 = min(bar["r_in"], fp["Cx3_bars"]["r_in"]) - g["sg_rhub"] - rod
    res["rail arms clear the island bars in the flange (HV)"] = (cl2 >= need, f"{_mm(cl2)} mm >= {_mm(need)} mm")
    # 6. stationary vs rotating, per plane: the stator electrodes / posts stay outside the rotating tip sweep except
    #    across the intended gap; the rail-plane posts must clear the rail tips (they do by construction) and the
    #    rail tips must not reach the bar track
    gap_rr = (g["sg_rg"] - g["sg_d"] / 2) - (g["sg_rret"] + g["sg_d"] / 2 + max(g["sg_s_ret"], 0))
    res["rail track well inboard of the bar track"] = (gap_rr >= need, f"{_mm(gap_rr)} mm radial between the tracks")
    # 7. lead frame clears the rotor rim (HV)
    clf = sg["R_frame"] - rod - design["r_edge"]
    res["lead frame clears the rotor rim (HV)"] = (clf >= need, f"R{_mm(sg['R_frame'])}: {_mm(clf)} mm over the R{_mm(design['r_edge'])} rims")
    # 8. planes clear the flanges and each other
    zc = min(abs(p["bar"]) for p in sg["planes"].values()) - max(abs(design["stack"][0]["z0"]), abs(design["stack"][-1]["z1"])) \
        - max(g["sg_d"], g["sg_dbs"]) / 2
    res["gap planes clear the flanges"] = (zc >= g["sg_clear"] - 1e-9, f"{_mm(zc)} mm")
    # 9. stationary electrodes of different nodes on one plane keep the HV clearance between them
    worst, det = float("inf"), ""
    for x in sg["gaps"]:
        for y in sg["gaps"]:
            if x is y or x["side"] != y["side"] or x["track"] != y["track"] or x["stator_node"] == y["stator_node"]:
                continue
            for k in range(SPOKES):
                d = math.dist(_pol(x["r_stator"], x["station"], x["z"]), _pol(y["r_stator"], y["station"] + 60 * k, y["z"])) \
                    - x["d_stator"] / 2 - y["d_stator"] / 2
                if d < worst - 1e-9:
                    worst, det = d, f"{x['name']} / {y['name']}"
    res["different-node stator electrodes keep the HV clearance"] = (worst >= need, f"tightest {det}: {_mm(worst)} mm >= {_mm(need)} mm")
    cross = [x["name"] for x in sg["gaps"] if x["crossover"]]
    res["load-gap crossovers over the stator (info)"] = (True, ", ".join(
        f"{x['name']}: node {x['stator_node']} from {x['carrier']} to deck {x['side']}, lead {_mm(x['lead_len'])} mm" for x in sg["gaps"] if x["crossover"]) or "none")
    return {k: dict(pass_=bool(v[0]), detail=v[1]) for k, v in res.items()}


def parts(design):
    st = design["stack"]; fp = design["footprints"]
    asm, out = [], []

    def assembly(key, label):
        if not any(a["key"] == key for a in asm):
            asm.append(dict(key=key, label=label))
        return key
    carrier_of, face_of = {}, {}
    for i, it in enumerate(st):
        if it["kind"] != "foil":
            continue
        nb = [st[j] for j in (i - 1, i + 1) if 0 <= j < len(st) and st[j]["kind"] in CARRIER_KINDS]
        carrier_of[it["id"]] = nb[0]["id"] if nb else "foils"
        face_of[it["id"]] = "septum side" if nb and abs(it["z0"]) < abs(nb[0]["z0"]) else "outer side"

    def P(name, label, akey, role, carrier, node, cap, material, rin, rout, a0, w, z0, z1, rgb):
        out.append(dict(name=name, label=label, assembly=akey, role=role, carrier=carrier, node=node, cap=cap,
                        material=material, shape="sector", chains=[carrier or akey],
                        r_in=rin, r_out=rout, start_deg=a0, w_deg=w, z0=z0, z1=z1, rgb=list(rgb),
                        volume=0.5 * math.radians(min(w, 360.0)) * (rout * rout - rin * rin) * (z1 - z0)))
    for it in st:
        kind = it["kind"]
        if kind in CARRIER_KINDS:
            a = assembly(it["id"], f"{it['id']} - {CARRIER_ROLE.get(it['id'], kind)}")
            P(it["id"].replace("-", "_") + "_carrier",
              f"{it['id']} carrier - {MATERIAL[kind]}, node {it['node']}, r{_mm(it['r_in'])}-{_mm(it['r_out'])} mm, "
              f"{_mm(it['t'])} mm thick, {_zr(it)}",
              a, "carrier", it["id"], it["node"], "", MATERIAL[kind], it["r_in"], it["r_out"], 0.0, 360.0,
              it["z0"], it["z1"], CARRIER_RGB)
        elif kind == "foil":
            car = carrier_of[it["id"]]
            a = assembly(car, f"{car} - {CARRIER_ROLE.get(car, '')}")
            n = len(it["starts"])
            for k, s0 in enumerate(it["starts"]):
                if it["w_deg"] >= 360.0 - 1e-9:
                    ang = "full ring"
                else:
                    e = _m360(s0 + it["w_deg"])
                    ang = f"sector {k + 1} of {n} ({_mm(_m360(s0))}-{_mm(e if e != 0 else 360.0)} deg)"
                P(f"{it['key']}_{k + 1}",
                  f"{car} / {it['key']}_{k + 1} - {it['name']}, node {it['node']}, {it['cap']}, {ang}, "
                  f"r{_mm(it['r_in'])}-{_mm(it['r_out'])} mm, Al foil {_mm(it['z1'] - it['z0'])} mm, "
                  f"{face_of[it['id']]}, {_zr(it)}",
                  a, "foil", car, it["node"], it["cap"], "Al foil", it["r_in"], it["r_out"], s0, it["w_deg"],
                  it["z0"], it["z1"], node_rgb(it["node"]))
        elif kind == "gap" and it.get("medium") in MEDIUM_RGB:
            a = assembly("dielectrics", "Dielectrics - septum (C_R, garolite) and the Ca/Cb mica slabs")
            if it.get("footprint"):
                e = fp[it["footprint"]]; m = it.get("margin", 0.0)
                rin, rout = max(0.0, e["r_in"] - m), e["r_out"] + m
                dw = math.degrees(m / max(e["r_in"], 1e-9))
                n = len(e["starts"])
                for k, s0 in enumerate(e["starts"]):
                    w = min(e["w_deg"] + 2 * dw, 360.0); a0 = s0 - dw
                    P(f"{it['id'].replace('-', '_')}_{k + 1}",
                      f"{it['id']}_{k + 1} - {it['medium']} dielectric for {it['cap']} (between the {it['cap']} electrode "
                      f"and its counter), slab {k + 1} of {n} ({_mm(_m360(a0))}-{_mm(_m360(a0 + w))} deg), "
                      f"r{_mm(rin)}-{_mm(rout)} mm, {_mm(it['t'])} mm thick (foil + {_mm(m)} mm margin), {_zr(it)}",
                      a, "dielectric", "", "", it["cap"], it["medium"], rin, rout, a0, w, it["z0"], it["z1"],
                      MEDIUM_RGB[it["medium"]])
            else:
                rin, rout = it.get("r_in", 0.0), it.get("r_out", design["r_edge"])
                P(it["id"].replace("-", "_"),
                  f"{it['id']} - {it['medium']}, {it['cap']} dielectric between rotor A and rotor B, "
                  f"r{_mm(rin)}-{_mm(rout)} mm, {_mm(it['t'])} mm thick, {_zr(it)}",
                  a, "dielectric", "", "", it["cap"], it["medium"], rin, rout, 0.0, 360.0, it["z0"], it["z1"],
                  MEDIUM_RGB[it["medium"]])
    sgp = design.get("sparkgaps")
    if sgp:
        for side in ("A", "B"):
            for role, lab in (("gap-rotor", f"Spark gaps deck {side} - rotor tips and arms (rotate with rotor {side})"),
                              ("gap-stator", f"Spark gaps deck {side} - stator electrodes, posts and leads")):
                key = f"gaps-{side}-{'rotor' if role == 'gap-rotor' else 'stator'}"
                for it in sgp["items"]:
                    if it["side"] != side or (it["role"] == "gap-rotor") != (role == "gap-rotor"):
                        continue
                    a = assembly(key, lab)
                    base = dict(name=it["name"], label=f"{it['name']} - {it['desc']}", assembly=a, role=it["role"],
                                carrier="", node=it["node"], cap=it["gap"], rgb=list(node_rgb(it["node"])),
                                chains=list(it["chains"]))
                    if it["kind"] == "sphere":
                        base.update(shape="sphere", material="W-Cu" if it["r"] <= 6.0 + 1e-9 else "smooth electrode",
                                    c=list(it["c"]), r=it["r"], volume=4.0 / 3.0 * math.pi * it["r"] ** 3)
                    else:
                        L = math.dist(it["p0"], it["p1"])
                        base.update(shape="rod", material="Cu rod", p0=list(it["p0"]), p1=list(it["p1"]), r=it["r"],
                                    volume=math.pi * it["r"] ** 2 * L)
                    out.append(base)
    return asm, out


def _arc_overlap(a0, w0, a1, w1):
    """Angular overlap (deg) of two arcs [a, a+w) on the circle."""
    tot = 0.0
    for sh in (-360.0, 0.0, 360.0):
        lo, hi = max(a0, a1 + sh), min(a0 + w0, a1 + w1 + sh)
        tot += max(0.0, hi - lo)
    return tot


def overlap_area(f1, f2):
    """Plan overlap area (mm^2) of two sector-set footprints."""
    rin, rout = max(f1["r_in"], f2["r_in"]), min(f1["r_out"], f2["r_out"])
    if rout <= rin:
        return 0.0
    ang = sum(_arc_overlap(a, f1["w_deg"], b, f2["w_deg"]) for a in f1["starts"] for b in f2["starts"])
    return 0.5 * math.radians(ang) * (rout * rout - rin * rin)


PAIRS = dict(C1=("C1_stator", "C1_rotor"), C2=("C2_stator", "C2_rotor"), Ca=("Ca_el", "Ca_counter"),
             Cb=("Cb_el", "Cb_counter"), Cx4=("Cx4_pickup", "Cx4_bars"), Cx3=("Cx3_pickup", "Cx3_bars"),
             C_R=("CR_A", "CR_B"))
ROTATING = ("C1", "C2", "Cx3", "Cx4")       # one electrode on a rotor (or its island bars)


def adjacency(design):
    """For each capacitor: its two foils are separated by exactly one layer, a gap carrying this capacitor's
    name and thickness, and they overlap in plan [ME]. Returns {cap: (ok, detail)}."""
    st = design["stack"]
    pos = {it["id"]: i for i, it in enumerate(st)}
    out = {}
    for cap, (k1, k2) in PAIRS.items():
        i1, i2 = sorted((pos[k1], pos[k2]))
        between = st[i1 + 1:i2]
        a, b = st[pos[k1]], st[pos[k2]]
        ov0 = overlap_area(a, b)
        rot = cap in ROTATING
        # a rotating pair (stator vs rotor) is judged at its aligned angle: the max over one sector pitch
        ovm = max(overlap_area(a, dict(b, starts=[x + d for x in b["starts"]])) for d in range(0, 61)) if rot else ov0
        ok = len(between) == 1 and between[0]["kind"] == "gap" and between[0]["cap"] == cap and ovm > 0
        out[cap] = (bool(ok), f"{k1} <-> {k2} across {[b_['id'] for b_ in between]}, plan overlap "
                              + (f"{ov0:.0f} at 0 deg / {ovm:.0f} aligned mm^2" if rot else f"{ov0:.0f} mm^2 (fixed)"))
    return out


def _pct(x):
    """percent, with a rounded zero printed as +0.0000 (float noise must not flip the sign; JS mirror alike)"""
    v = x * 100
    return 0.0 if abs(v) < 5e-5 else v


def checks(design):
    """Geometric feasibility checks for the geometrized pair (Ca/Cb) and the stack [OC geometry]."""
    fp = design["footprints"]; g = design["geom"]
    res = {}
    for cap, el, ct in (("Ca", "Ca_el", "Ca_counter"), ("Cb", "Cb_el", "Cb_counter")):
        e, c = fp[el], fp[ct]
        geo = design[cap]
        inside = (e["r_in"] >= c["r_in"] - 1e-9 and e["r_out"] <= c["r_out"] + 1e-9 and e["w_deg"] <= c["w_deg"] + 1e-9)
        res[f"{cap}: electrode inside its counter-electrode"] = (
            inside, f"r{e['r_in']:.1f}-{e['r_out']:.1f} x {e['w_deg']:.2f} deg within r{c['r_in']:.0f}-{c['r_out']:.0f} x {c['w_deg']:.0f} deg")
        ov = overlap_area(e, c)
        res[f"{cap}: overlap area = electrode area"] = (abs(ov - geo["area_mm2"]) <= 1e-6 * geo["area_mm2"],
                                                         f"{ov:.1f} vs {geo['area_mm2']:.1f} mm^2")
        res[f"{cap}: clears the carrier bore"] = (e["r_in"] - g["ca_margin"] >= g["r_bore"],
                                                  f"r_in {e['r_in']:.1f} - margin {g['ca_margin']:.0f} >= bore {g['r_bore']:.0f}")
        res[f"{cap}: dielectric margin fits the sector pitch"] = (
            e["w_deg"] + 2 * math.degrees(g["ca_margin"] / max(e["r_in"], 1e-9)) <= 360.0 / (len(e["starts"]) or 1),
            f"foil {e['w_deg']:.1f} deg + 2 x {g['ca_margin']:.0f} mm margin at r_in")
        res[f"{cap}: realized C = locked C"] = (abs(geo["dC_rel"]) <= 1e-9 or g["ca_round"] > 0,
                                                f"{geo['C_pF']:.3f} vs {geo['C_target_pF']:.3f} pF ({_pct(geo['dC_rel']):+.4f} %)"
                                                + (" -- rounding: engine round-trip decides" if g["ca_round"] > 0 else ""))
    P = design["lock"]["plates"]
    res["layout: alternating sectors (n_kept = N_sec / 2, as drawn)"] = (
        int(P["n_kept"]) * 2 == int(P["N_sec"]), f"n_kept {P['n_kept']} of N_sec {P['N_sec']}")
    for cap, (ok, det) in adjacency(design).items():
        res[f"stack: {cap} electrodes face each other"] = (ok, det)
    return {k: dict(pass_=bool(v[0]), detail=v[1]) for k, v in res.items()}


def lock_record(lad, inputs, z, converged, engine_version="", strip=None):
    """The stage-1 lock: what stage 2 may not change. hash = sha256 of the canonical JSON (first 12 hex)."""
    rec = dict(inputs=inputs, plates={k: lad["plates"][k] for k in ("r_inMm", "r_outMm", "g_vMm", "N_sec", "n_kept")},
               ladder={k: v["value"] for k, v in lad["ladder"].items()}, z=z, converged=converged,
               engine=engine_version)
    rec["hash"] = hashlib.sha256(canonical(dict(inputs=rec["inputs"], ladder=rec["ladder"])).encode()).hexdigest()[:12]
    return rec


def _js_num(x):
    """A number exactly as JavaScript's JSON.stringify writes it (so the page and Python agree on lock hashes)."""
    if isinstance(x, bool):
        return "true" if x else "false"
    if isinstance(x, int):
        return str(x)
    if x == int(x) and abs(x) < 1e21:
        return str(int(x))
    r = repr(x)
    if "e" in r:
        m, e = r.split("e")
        r = m + "e" + ("-" if e.startswith("-") else "+") + e.lstrip("+-").lstrip("0")
    return r


def canonical(o):
    """Sorted-key compact JSON, identical to tools/pump-geometry.js canonical()."""
    if isinstance(o, dict):
        return "{" + ",".join(json.dumps(k) + ":" + canonical(o[k]) for k in sorted(o)) + "}"
    if isinstance(o, (list, tuple)):
        return "[" + ",".join(canonical(v) for v in o) + "]"
    if isinstance(o, (int, float)) and not isinstance(o, bool) or isinstance(o, bool):
        return _js_num(o)
    return json.dumps(o, ensure_ascii=False)


def _selftest():
    import os
    import sys
    here = os.path.dirname(os.path.abspath(__file__))
    if here not in sys.path:
        sys.path.insert(0, here)
    import pump_sizing as PS
    lad = PS.size(dict(dielectric="vacuum"))
    rec = lock_record(lad, {}, 1.3254745316585308, True)
    # the DXF seed reproduces the freeze 309 pF (forward mode at r110-175, 6 x 30 deg, 4.5 mm mica)
    fwd = solve_transfer(309.0, dict(GEOM_DEFAULTS, ca_mode="forward"), 6)
    ok = abs(fwd["area_mm2"] - 29099.002) < 0.01 and abs(fwd["C_pF"] - 309.18) < 0.01
    d = build(rec)
    ok &= abs(d["Ca"]["C_pF"] - lad["ladder"]["Ca"]["value"]) < 1e-9 and all(v["pass_"] for v in d["checks"].values())
    ok &= all(v[0] for v in adjacency(d).values())
    if not ok:
        raise AssertionError("pump_geometry on-load self-test FAILED")
    return True


SELFTEST_OK = _selftest()

if __name__ == "__main__":
    import pump_sizing as PS
    lad = PS.size()
    d = build(lock_record(lad, {}, 1.3254745316585308, True))
    print(json.dumps({k: d[k] for k in ("Ca", "Cb", "z_total")}, indent=1))
    for k, v in d["checks"].items():
        print(("PASS " if v["pass_"] else "FAIL ") + k + " -- " + v["detail"])
    for s in d["stack"]:
        print(f"{s['id']:10s} {s['kind']:12s} z {s['z0']:8.2f} .. {s['z1']:8.2f}  t {s['t']}")
    print("selftest", _selftest())
