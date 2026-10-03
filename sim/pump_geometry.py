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
  rotor faces           r75-387, odd sectors: the C1 / C2 rotor faces (R-A / R-B, DXF ND5 / ND6) and, on the
                        septum side, the C_R plates (n18 / n00, DXF ND9 / ND10; L_R1 / L_R2 join them to R-A / R-B)
  ND2 Ca electrode      r110-175, odd sectors  (faces ND1 through 4.5 mm mica)
  ND3 Cb electrode      r110-175, even sectors (faces ND4 through 4.5 mm mica)
  ND2 Cx4 pickup        r58-350, even sectors   ND8 island bars (on A) r75-350, even sectors
  ND3 Cx3 pickup        r58-350, odd sectors    ND7 island bars (on B) r75-350, odd sectors
  6 x 30 deg of r110-175 = 0.029099 m^2 -> 309.18 pF on 4.5 mm mica (eps_r 5.4): the DXF and the freeze agree.

Axial stack (NOT in the DXF -- its "stack section" frame is a plan overlay). Seeded with the one order in which
every capacitor's two electrodes face each other across exactly its own dielectric [IR, confirm in CAD]:
each rotor half is a clamshell around its stator pair --
  A flange (ND8 bars) | Cx4 gap | ND2 carrier | Ca mica | ND1 carrier | C1 air | A disc (R-A | n18) | septum (C_R) |
  B disc (n00 | R-B) | C2 air | ND4 carrier | Cb mica | ND3 carrier | Cx3 gap | B flange (ND7 bars)
Node ids are the netlist of record's (topology_edge_list.csv): 1 2 3 4, R-A R-B, 7 8, n18 n00, n17 n23;
sim/circuit_integrity.py checks every build against it. The spark gaps live in the stack too (sparkgaps()): the bar
band (load / fire / backstop) beside the trimmed ND2 / ND3 rim (sg_layout 'radial', the default) or in a recessed band
of the Cx gap ('axial'), the return band (SG1 / SG2) in the C1 / C2 gap.
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
    ca_mode="outer",                          # solve: 'outer' (r_out at the counter edge - margin, r_in solved: the node-2 /
                                              # 3 sectors as far out as they go, next to the bar band -- TMD 2026-10-02)
                                              # | 'r_out' (r_in pinned) | 'r_in' (r_out pinned) | 'width' | 'forward'
    ca_rin=110.0, ca_rout=175.0,              # mm (the pinned one is used; the other is solved) [OC DXF]
    ca_round=0.0,                             # manufacturing step on the solved dimension (mm or deg; 0 = exact)
    ca_margin=5.0,                            # dielectric overlap margin around the foil (mm, radial and arc) [IR]
    ca_cal=1.0,                               # parallel-plate share of the locked Ca / Cb: the area law sizes the electrode
                                              # for ca_cal x C, so a field-solved fringe (ROUND-TRIP FS7) can be
                                              # calibrated out (1 = no fringe allowance, as stage 2) [ME]
    # stack placeholders [IR]; the carrier thicknesses are the BASE (minimum) values -- see zs_mode
    t_foil=1.0, t_carrier=3.0, t_rotor=10.0, t_flange=6.0, t_septum=12.0,
    cx_air=3.0, cx_mica=0.3,                  # Cx gap: air + mica per face (freeze v0.10) [OC]
    r_bore=50.0,                              # stator carrier bore (mm), clears the hub/coil r28-76 bicone [IR]
    rotor_in_off=20.0,                        # rotor face r_in = active r_in - 20 (DXF 75 vs 95) [IR]
    # ---- spark gaps IN the stack (TMD 2026-10-01): every rotary gap sits in the axial gap between the rotor face
    #      and the stator face it joins, in a radial band reserved beyond the capacitor electrodes [IR placement] ----
    sg_rbar=375.0,                            # bar band (load / fire / backstop) in the Cx gap: bars r350 + 11 mm HV + the 25 mm backstop [IR];
                                              # in the radial layout the least tip radius (the tips sit just outside the trimmed rim)
    sg_rrail=410.0,                           # return band (SG1 / SG2, the engine's 'rail' class) in the C1 / C2 gap, beyond r387 [IR]
    sg_d=12.0, sg_dbs=25.0,                   # SPHERE diameter: W-Cu switching (= stage-1 d_ball) / polished backstop (mm) [OC freeze]
    sg_s_ret=5.5, sg_s_load=4.75, sg_s_fire=5.5, sg_s_bs=5.5,   # spacings at alignment (mm); BS: [IR] (freeze TODO)
    sg_glat=1.0,                              # lateral gap for the I11 overlap law (design_synth) [IR]
    sg_expose=0.5,                            # spherical electrodes (TMD 2026-10-02): every sphere stands at least this
                                              # fraction of its diameter proud of its band face (0.5 = a hemisphere; the
                                              # rest sits in a socket) [IR]
    sg_stem=4.0,                              # stem diameter, sphere centre -> the lead plane (mm) [IR]
    sg_wall=1.0,                              # minimum carrier wall left under a recessed band (mm) [IR]
    sg_seat=3.0,                              # stem seated below the deeper of the face / the socket bottom (mm) [IR]
    sg_rod=3.0,                               # lead diameter (embedded in the carrier, then along the frame) (mm) [IR]
    sg_cover=2.0,                             # insulation (carrier) kept around every embedded lead (mm) [IR]
    sg_chord=15.0,                            # embedded leads change sector on a ring this far inside the carrier edge (mm) [IR]
    sg_bus=3.0,                               # bus ring (square section, mm) embedded under each electrode: it joins
                                              # the electrode's sectors into one net, one riser per sector [IR]
    sg_frame=60.0,                            # stator lead frame radius = carrier edge + this (over the stator) [IR]
    sg_khv=2.0,                               # HV clearance >= k x the largest spacing, different nodes [IR]
    # ---- bar band layout (TMD 2026-10-02). 'radial': ND2 / ND3 end at a trimmed rim just beyond their electrodes; the
    #      island-bar tips (nodes 8 / 7) hang from the flange just outside that rim; the fire and backstop spheres (nodes
    #      2 / 3) stand on RADIAL stems out of the rim, straight under the tip path (vertical gaps), and their leads run
    #      straight in to the Ca / Cb electrode; the load sphere (node 4 / 1) sits beside the tip at the tip's height, on
    #      a radial arm in from the stator frame (horizontal gap). Three of the four spheres hang on horizontal stems,
    #      which the spin loads along their axis. 'axial': every bar-band sphere on a vertical stem in a recessed band of
    #      the Cx gap (rev 5-7) [IR placement] ----
    sg_layout="radial",
    sg_rimgap=3.0,                            # trimmed ND2 / ND3 rim beyond its outermost foil + dielectric margin (mm) [IR]
    sg_clear=2.0,                             # running clearance: tip to the trimmed rim, load sphere to the flange face (mm) [IR]
    sg_stem_air=2.0,                          # rim stem left bare between the rim and its sphere (mm) [IR]
    counter_trim=0,                           # 1 = the Ca / Cb counter-electrodes cover only their electrode's band +
                                              # the dielectric margin (0 = the full stator plate r_in-r_out, as drawn):
                                              # the rest of the plate faces the island Cx foils (ROUND-TRIP step 1) [IR]
    c_w_deg=0.0,                              # C1 / C2 kept-sector width (deg; 0 = the full sector pitch, as drawn).
                                              # Narrower sectors on the same centres widen the gaps between them and
                                              # cut the disaligned fringe (ROUND-TRIP lever 2) [IR]
    cx_w_deg=0.0,                             # island bars + Cx pickups sector width (deg; 0 = as drawn) [IR]
    sg_tip_deg=0.0,                           # rotor-tip angle in the rotor frame (deg, mod 60). Stage 2 put the tips at 0
                                              # (the C1 faces aligned when a tip meets its station); the engine's timing
                                              # has C1 aligned 15 deg after theta = 0, which tips at 15 realize
                                              # (ROUND-TRIP, sim/round-trip-findings.md) [IR]
    # ---- Z-stretch (TMD 2026-10-02): the two foils of a node sit on the two faces of one carrier and are joined by
    #      explicit links, so a carrier's thickness is free along z. 'auto' stretches every carrier to hold its gap
    #      seats and embedded leads with the margins above; 'fixed' keeps the base thicknesses (checks then show the
    #      shortfall). The capacitor gaps -- and so every C -- are untouched by the stretch [OC geometry] ----
    zs_mode="auto",
)
CARRIER_BASE = {"ND1": "t_carrier", "ND2": "t_carrier", "ND3": "t_carrier", "ND4": "t_carrier", "A-disc": "t_rotor",
                "B-disc": "t_rotor", "A-flange": "t_flange", "B-flange": "t_flange"}
# the two same-node foils of a carrier, joined through it by one link per sector [IR]; ND2 / ND3 carry node 2 / 3
# and the pickup n23 / n17, joined only through Lx4 / Lx3 (off-model)
FAR_GAP = {"ND1": "ca_t", "ND2": "ca_t", "ND3": "ca_t", "ND4": "ca_t", "A-disc": "t_septum", "B-disc": "t_septum"}
LINKS = {"ND1": ("C1_stator", "Ca_counter"), "ND4": ("C2_stator", "Cb_counter")}
# (the rotor discs carry two DIFFERENT nodes: the C1 / C2 rotor face R-A / R-B and the C_R plate n18 / n00, which the
#  netlist joins only through the resonator coils L_R1 / L_R2 -- a link there would short the coil)
# radial bar band: the foils of the trimmed carriers; the outermost edge + the dielectric margin + sg_rimgap is the rim [IR]
RIM_FOILS = {"ND2": ("Ca_el", "Cx4_pickup"), "ND3": ("Cb_el", "Cx3_pickup")}


def _round(x, step):
    """Manufacturing step, half-up (identical in the JS mirror; Python's round() is half-even)."""
    return x if not step else math.floor(x / step + 0.5) * step


def sector_area(rin, rout, w_deg, n):
    """Area of n annular sectors (mm^2)."""
    return 0.5 * math.radians(w_deg) * max(0.0, rout * rout - rin * rin) * n


def cap_pF(area_mm2, t_mm, eps_r):
    return EPS0 * eps_r * area_mm2 * 1e-6 / (t_mm * 1e-3) * 1e12


def solve_transfer(C_pF, g, n, r_max=None):
    """Ca/Cb inverse: the electrode footprint for a target capacitance. Returns the geometry, the realized C
    (after the manufacturing rounding) and the deviation. r_max: the outermost r_out ('outer' mode) -- the
    counter-electrode's edge less the dielectric margin."""
    er = DIELECTRICS[g["ca_diel"]]
    A = C_pF * 1e-12 * g["ca_t"] * 1e-3 / (EPS0 * er) * 1e6          # mm^2 needed [OC] Eq. (20)
    w, rin, rout = g["ca_w"], g["ca_rin"], g["ca_rout"]
    k = 0.5 * math.radians(w) * n                                    # A = k (rout^2 - rin^2)
    mode = g["ca_mode"]
    note = ""
    if mode == "outer":
        rout = r_max if r_max is not None else rout
    if mode == "r_out":
        rout = _round(math.sqrt(rin * rin + A / k), g["ca_round"])
    elif mode in ("r_in", "outer"):
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


def band_needs(g, P):
    """(side, band) -> the bare face gap D (its capacitor gap + both foils), the face-to-face gap G its SPHERES need,
    the recess per face, each sphere's protrusion p (apex above its face) and the socket depth e = d - p of the
    deepest sphere on each side. Every sphere shows at least sg_expose of its diameter: the rotor tip exactly that, and
    each gap's stator sphere as much as its spacing leaves (G - s - p_rot; a sphere showing more than its diameter
    stands on its stem above the face). It depends only on the gaps, so the Z-stretch is solved before the stack
    is laid out [OC geometry]. The radial bar band (sg_layout 'radial') is solved by _radial_needs."""
    D = {"bar": g["cx_air"] + 2 * g["cx_mica"] + 2 * g["t_foil"], "return": P["g_vMm"] + 2 * g["t_foil"]}
    out = {}
    for (side, band) in BANDS:
        mine = [x for x in GAPS if x[4] == side and x[5] == band]
        if band == "bar" and g["sg_layout"] == "radial":
            out[(side, band)] = _radial_needs(g, D[band], mine)
            continue
        p_rot = g["sg_expose"] * g["sg_d"]
        need = max(g[SPACING_KEY[x[1]]] + p_rot + g["sg_expose"] * sphere_d(g, x[1]) for x in mine)
        G = max(D[band], need)
        p = {x[0]: G - g[SPACING_KEY[x[1]]] - p_rot for x in mine}
        out[(side, band)] = dict(D=D[band], need=need, G=G, rec=max(0.0, need - D[band]) / 2, p_rot=p_rot, p=p,
                                 e_st=max(max(0.0, sphere_d(g, x[1]) - p[x[0]]) for x in mine),
                                 e_rot=max(0.0, g["sg_d"] - p_rot), layout="axial")
    return out


def _radial_needs(g, D, mine):
    """The radial bar band along z (TMD 2026-10-02), as zeta = height above the stator's bare Cx face toward the flange
    (the flange face is at zeta = D). The tip centre sits as high as the load sphere beside it allows (its top
    sg_clear under the flange face) and low enough that every rim stem keeps its cover under the Cx face; each
    vertical gap's sphere hangs straight under the tip, centre to centre R_tip + s + R. The other leads of the carrier
    (the SG1 / SG2 hops, in from the frame through the open space beside the rim) enter at the deepest rim stem's
    plane, and never closer than the HV clearance below the tip path; the deepest sphere bottom or that lead sets the
    stator carrier's thickness. No recess, no socket: the spheres stand clear on their stems, the tip hangs from the
    flange face [OC geometry, IR clearances]."""
    R_t = g["sg_d"] / 2
    load = [x for x in mine if x[1] == "load"]
    vert = [x for x in mine if x[1] != "load"]
    R_l = max(sphere_d(g, x[1]) / 2 for x in load)
    hold = max(g["sg_stem"], g["sg_rod"]) / 2 + g["sg_cover"]
    hv = g["sg_khv"] * max(g["sg_s_ret"], g["sg_s_load"], g["sg_s_fire"], g["sg_s_bs"])
    z_tip = min(D - (R_l + g["sg_clear"]),
                min(R_t + g[SPACING_KEY[x[1]]] + sphere_d(g, x[1]) / 2 for x in vert) - hold)
    zeta = {x[0]: z_tip for x in load}
    zeta.update({x[0]: z_tip - (R_t + g[SPACING_KEY[x[1]]] + sphere_d(g, x[1]) / 2) for x in vert})
    lead = min(min(zeta[x[0]] for x in vert), z_tip - R_t - hv - g["sg_rod"] / 2)
    depth = max(max(max(sphere_d(g, x[1]), g["sg_stem"], g["sg_rod"]) / 2 - zeta[x[0]] for x in vert), g["sg_rod"] / 2 - lead)
    return dict(D=D, need=D, G=D, rec=0.0, p_rot=D - z_tip + R_t, p={x[0]: sphere_d(g, x[1]) for x in mine},
                e_st=0.0, e_rot=0.0, layout="radial", zeta_tip=z_tip, zeta=zeta, depth=depth, lead=lead)


def sphere_d(g, cls):
    return g["sg_dbs"] if cls == "backstop" else g["sg_d"]


def far_cover(g, c):
    """The cover a band host keeps between its lead plane and its far face. Leads of different nodes in the two
    carriers facing each other across a fixed gap (ND1 | Ca | ND2, ND4 | Cb | ND3; A-disc | septum | B-disc, which
    co-rotate) may cross in plan, so both covers plus that gap must make the HV clearance [IR]."""
    hv = g["sg_khv"] * max(g["sg_s_ret"], g["sg_s_load"], g["sg_s_fire"], g["sg_s_bs"])
    fixed = FAR_GAP.get(c)
    if fixed is None:
        return g["sg_cover"]
    return max(g["sg_cover"], (hv - (g[fixed] + 2 * g["t_foil"])) / 2)


def zstretch(g, P):
    """Every carrier's thickness along z: its base value, or -- zs_mode 'auto' -- stretched to what it must hold
    [IR margins]: a band host keeps recess + sphere socket + stem seat + lead + its far cover; a carrier that only receives leads
    keeps lead + 2 x cover. The two foils of a node are joined by explicit links, so this costs no capacitance."""
    need = band_needs(g, P)
    req = {k: (0.0, "") for k in CARRIER_BASE}
    for (side, band), (rc, rfoil, sc) in BANDS.items():
        n = need[(side, band)]
        if n["layout"] == "radial":
            # the flange seats the hanging tips' stems and their leads; the stator carrier is as deep as its deepest
            # rim sphere hangs (the rim stems and every lead plane lie above that)
            for c, r, why in ((rc, g["sg_seat"] + g["sg_rod"] + far_cover(g, rc),
                               f"{side} bar band (radial): tip stem seat {_mm(g['sg_seat'])} + lead {_mm(g['sg_rod'])} "
                               f"+ cover {_mm(far_cover(g, rc))}"),
                              (sc, n["depth"] + far_cover(g, sc),
                               f"{side} bar band (radial): rim spheres hang {_mm(n['depth'])} below the Cx face "
                               f"+ cover {_mm(far_cover(g, sc))}")):
                if r > req[c][0] + 1e-9:
                    req[c] = (r, why)
            continue
        for c, e in ((rc, n["e_rot"]), (sc, n["e_st"])):
            fc = far_cover(g, c)
            r = n["rec"] + e + g["sg_seat"] + g["sg_rod"] + fc
            why = (f"{side} {band} band: recess {_mm(n['rec'])} + socket {_mm(e)} + seat {_mm(g['sg_seat'])} "
                   f"+ lead {_mm(g['sg_rod'])} + cover {_mm(fc)}")
            if r > req[c][0] + 1e-9:
                req[c] = (r, why)
    mid = g["sg_rod"] + 2 * g["sg_cover"]
    for x in GAPS:
        c = NODE_CARRIER[x[2]]
        if mid > req[c][0] + 1e-9:
            req[c] = (mid, f"lead at mid-plane: {_mm(g['sg_rod'])} + 2 x cover {_mm(g['sg_cover'])}")
    out = {}
    for k, base_key in CARRIER_BASE.items():
        base = g[base_key]; r, why = req[k]
        t = max(base, r) if g["zs_mode"] == "auto" else base
        out[k] = dict(base=base, req=r, t=t, why=why, stretched=t > base + 1e-9)
    return out


def build(locked, geom=None):
    """locked: the stage-1 lock record (inputs, ladder values, z). Returns the full geometry design (JSON-safe)."""
    g = dict(GEOM_DEFAULTS); g.update(geom or {})
    L = locked["ladder"]; P = locked["plates"]
    nk = int(P["n_kept"])
    ri, ro = P["r_inMm"], P["r_outMm"]
    ca = solve_transfer(L["Ca"] * g["ca_cal"], g, nk, ro - g["ca_margin"])   # Cb uses the same geometry spec; the
    cb = solve_transfer(L["Cb"] * g["ca_cal"], g, nk, ro - g["ca_margin"])   # counters span the stator plate r_in-r_out
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
    w_c = g["c_w_deg"] or w_sec                                       # C1 / C2 faces, on the sector centres
    w_x = g["cx_w_deg"] or w_sec                                      # island bars + pickups
    c_odd = [s + (w_sec - w_c) / 2 for s in odd]; c_even = [s + (w_sec - w_c) / 2 for s in even]
    x_odd = [s + (w_sec - w_x) / 2 for s in odd]; x_even = [s + (w_sec - w_x) / 2 for s in even]
    ct_ri = (lambda e: max(ri, e["r_in"] - g["ca_margin"])) if g["counter_trim"] else (lambda e: ri)
    fp = dict(
        C1_stator=_fp("C1 stator plate", "1", "C1", ri, ro, c_odd, w_c),
        C1_rotor=_fp("C1 rotor face", "R-A", "C1", rr_in, ro, c_odd, w_c),
        C2_stator=_fp("C2 stator plate", "4", "C2", ri, ro, c_even, w_c),
        C2_rotor=_fp("C2 rotor face", "R-B", "C2", rr_in, ro, c_odd, w_c),
        Ca_el=_fp("Ca electrode", "2", "Ca", ca["r_in"], ca["r_out"], ca_starts, ca["w_deg"]),
        Ca_counter=_fp("Ca counter (ND1 back face)", "1", "Ca", ct_ri(ca), ro, odd, w_sec),
        Cb_el=_fp("Cb electrode", "3", "Cb", cb["r_in"], cb["r_out"], cb_starts, cb["w_deg"]),
        Cb_counter=_fp("Cb counter (ND4 back face)", "4", "Cb", ct_ri(cb), ro, even, w_sec),
        Cx4_pickup=_fp("Cx4 pickup", "n23", "Cx4", cx_rin, cx_rout, x_even, w_x),   # n23 -Lx4- node 2 (netlist)
        Cx4_bars=_fp("island bars on A", "8", "Cx4", bar_rin, cx_rout, x_even, w_x),
        Cx3_pickup=_fp("Cx3 pickup", "n17", "Cx3", cx_rin, cx_rout, x_odd, w_x),   # n17 -Lx3- node 3 (netlist)
        Cx3_bars=_fp("island bars on B", "7", "Cx3", bar_rin, cx_rout, x_odd, w_x),
        # C_R faces: the rotor-face sectors (host Ametal_full = keptFrac x full radial span, index.html plateGeom),
        # aligned on A and B -- both discs co-rotate, so C_R is fixed and its sectoring is a free choice [OC host]
        CR_A=_fp("C_R plate (rotor A)", "n18", "C_R", rr_in, ro, odd, w_sec),
        CR_B=_fp("C_R plate (rotor B)", "n00", "C_R", rr_in, ro, odd, w_sec),
    )
    # ---- axial stack (z up, mm): a strict layer sequence from the septum outward, foils as their own layers
    #      (every gap value is foil-to-foil) [IR]; side A at z < 0, side B mirrored at z > 0 ----
    tf = g["t_foil"]
    gv, tcx = P["g_vMm"], g["cx_air"] + 2 * g["cx_mica"]
    zs = zstretch(g, P)
    tc = {k: v["t"] for k, v in zs.items()}
    cxm = f"air {g['cx_air']:g} + mica {g['cx_mica']:g}/face"
    # radial bar band: ND2 / ND3 end at a rim just beyond their outermost foil and its dielectric margin [IR]
    rim = {}
    if g["sg_layout"] == "radial":
        rim = {c: min(r_edge, max(fp[k]["r_out"] for k in ks) + g["ca_margin"] + g["sg_rimgap"]) for c, ks in RIM_FOILS.items()}

    def C(id_, kind, node, t, rin):
        return dict(id=id_, kind=kind, node=node, t=t, r_in=rin, r_out=rim.get(id_, r_edge))

    def F(key):
        return dict(id=key, kind="foil", key=key, t=tf)

    def G(id_, cap, t, medium, footprint=None, margin=0.0):
        return dict(id=id_, kind="gap", cap=cap, t=t, medium=medium, footprint=footprint, margin=margin)
    seqA = [F("CR_A"), C("A-disc", "rotor", "", tc["A-disc"], 0.0), F("C1_rotor"), G("C1-gap", "C1", gv, "air"),
            F("C1_stator"), C("ND1", "stator", "", tc["ND1"], g["r_bore"]), F("Ca_counter"),
            G("Ca-diel", "Ca", ca["t"], ca["diel"], "Ca_el", g["ca_margin"]), F("Ca_el"),
            C("ND2", "stator", "", tc["ND2"], g["r_bore"]), F("Cx4_pickup"), G("Cx4-gap", "Cx4", tcx, cxm),
            F("Cx4_bars"), C("A-flange", "rotor-flange", "", tc["A-flange"], 0.0)]
    seqB = [F("CR_B"), C("B-disc", "rotor", "", tc["B-disc"], 0.0), F("C2_rotor"), G("C2-gap", "C2", gv, "air"),
            F("C2_stator"), C("ND4", "stator", "", tc["ND4"], g["r_bore"]), F("Cb_counter"),
            G("Cb-diel", "Cb", cb["t"], cb["diel"], "Cb_el", g["ca_margin"]), F("Cb_el"),
            C("ND3", "stator", "", tc["ND3"], g["r_bore"]), F("Cx3_pickup"), G("Cx3-gap", "Cx3", tcx, cxm),
            F("Cx3_bars"), C("B-flange", "rotor-flange", "", tc["B-flange"], 0.0)]
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
    z_base = stack[-1]["z1"] - stack[0]["z0"] - sum(tc[k] - g[CARRIER_BASE[k]] for k in CARRIER_BASE)
    design = dict(schema=SCHEMA, units="mm", lock=dict(locked), geom=g, Ca=ca, Cb=cb, footprints=fp,
                  stack=stack, foils=foils, z_total=stack[-1]["z1"] - stack[0]["z0"], r_edge=r_edge,
                  zstretch=zs, z_base=z_base)
    design["sparkgaps"] = sparkgaps(design)
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
            "R-A": (0.78, 0.57, 0.92), "R-B": (0.97, 0.46, 0.56), "7": (0.62, 0.81, 0.42), "8": (0.88, 0.69, 0.41),
            "n17": (0.55, 0.90, 0.80), "n23": (1.0, 0.88, 0.55), "n18": (0.55, 0.45, 0.95), "n00": (0.95, 0.55, 0.80)}
NODE_DESC = {   # the netlist of record's nodes (= sim/circuit_integrity.py NODE_INFO)
    "1": "ND1 - A-rail: C1 stator plate + Ca counter-electrode",
    "2": "ND2 - AR bank: Ca electrode",
    "3": "ND3 - BR bank: Cb electrode",
    "4": "ND4 - B-rail: C2 stator plate + Cb counter-electrode",
    "R-A": "ND5 - resonator end A: rotor A (C1 rotor face)",
    "R-B": "ND6 - resonator end B: rotor B (C2 rotor face)",
    "7": "ND7 - island on rotor B (Cx3 bars)",
    "8": "ND8 - island on rotor A (Cx4 bars)",
    "n18": "ND9 - C_R plate on rotor A (L_R1 to R-A)",
    "n00": "ND10 - C_R plate on rotor B (L_R2 to R-B)",
    "n17": "Cx3 pickup on ND3 (Lx3 to node 3)",
    "n23": "Cx4 pickup on ND2 (Lx4 to node 2)",
}


def node_rgb(node):
    return NODE_RGB.get(str(node), CARRIER_RGB)
MEDIUM_RGB = {"garolite": (0.55, 0.50, 0.30), "mica": (0.75, 0.70, 0.55)}
CARRIER_RGB = (0.35, 0.40, 0.47)
MATERIAL = {"stator": "G10 carrier", "rotor": "G10 rotor disc", "rotor-flange": "G10 rotor flange"}   # all insulating [IR]
CARRIER_ROLE = {"A-flange": "rotor A outer flange; holds the ND8 island bars",
                "B-flange": "rotor B outer flange; holds the ND7 island bars",
                "A-disc": "rotor A main disc; holds the C1 rotor face (R-A) and, septum side, the C_R plate (n18)",
                "B-disc": "rotor B main disc; holds the C2 rotor face (R-B) and, septum side, the C_R plate (n00)",
                "ND1": "stator carrier ND1; holds the C1 stator plate and the Ca counter-electrode (A-rail, 1)",
                "ND2": "stator carrier ND2; holds the Ca electrode (AR bank, 2) and the Cx4 pickup (n23)",
                "ND3": "stator carrier ND3; holds the Cb electrode (BR bank, 3) and the Cx3 pickup (n17)",
                "ND4": "stator carrier ND4; holds the C2 stator plate and the Cb counter-electrode (B-rail, 4)"}
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


# ---- spark gaps IN the stack: the commutator built into the capacitor stack (TMD 2026-10-01) ----
# Rotor and stator COUNTER-rotate, so any rotor part and any stator part at overlapping radius must be separated
# axially (their revolved (r, z) envelopes may not overlap: sweep_check). A rotary gap therefore lives in the axial
# gap between the one rotor face and the one stator face it joins:
#   bar gaps (load / fire / backstop): island-bar tip on the FLANGE <-> sphere on ND2 / ND3, in the Cx gap,
#                                      in a band beyond the bars and pickups;
#   return gaps (SG1 / SG2):          rotor-face tip on the rotor DISC (R-A / R-B) <-> sphere on ND1 / ND4, in the
#                                      C1 / C2 gap, in a band beyond the plates.
# Buttons of a node foreign to their carrier (SG4a node 4 on ND2, SG3a node 1 on ND3: the CROSSOVERS over the
# stator; SG1 node 2 on ND1, SG2 node 3 on ND4: neighbour hops) are fed by a lead embedded in the carrier to its
# rim, then along the stator frame beyond the rotor rims.
# The radial bar band (sg_layout 'radial', TMD 2026-10-02): ND2 / ND3 end at a trimmed rim just beyond Ca / Cb, so the
# space between the flange and ND1 / ND4 opens beyond it. The tips hang there from the flange; the fire and backstop
# spheres stand on radial stems out of the rim, straight under the tip path (vertical gaps), their leads straight in
# to Ca / Cb; the load sphere sits beside the tip at its height, on a radial arm in from the stator frame (horizontal
# gap), which also carries its crossover. The tips still pass every stator part axially or radially clear: the
# revolved envelopes stay disjoint.
GAPS = (  # name, class, stator node, rotor electrode, side, band, station (deg = DXF marker = engine st_*)
    ("SG1", "return", "2", "rotor A (R-A)", "A", "return", 3.00),
    ("SG4a1", "load", "4", "island bar 8", "A", "bar", 37.20),
    ("SG4b1", "fire", "2", "island bar 8", "A", "bar", 46.05),
    ("BS4", "backstop", "2", "island bar 8", "A", "bar", 49.00),
    ("SG2", "return", "3", "rotor B (R-B)", "B", "return", 33.00),
    ("SG3a1", "load", "1", "island bar 7", "B", "bar", 7.20),
    ("SG3b1", "fire", "3", "island bar 7", "B", "bar", 16.05),
    ("BS3", "backstop", "3", "island bar 7", "B", "bar", 19.00),
)
NETLIST_GAPS = {"SG1": ("2", "R-A"), "SG2": ("3", "R-B"), "SG3a1": ("1", "7"), "SG3b1": ("7", "3"), "BS3": ("7", "3"),
                "SG4a1": ("4", "8"), "SG4b1": ("8", "2"), "BS4": ("8", "2")}
ROTOR_NODE = {"rotor A (R-A)": "R-A", "rotor B (R-B)": "R-B", "island bar 7": "7", "island bar 8": "8"}
NODE_CARRIER = {"1": "ND1", "2": "ND2", "3": "ND3", "4": "ND4"}
SIDE_OF_CARRIER = {"ND1": "A", "ND2": "A", "ND3": "B", "ND4": "B"}
SPACING_KEY = {"return": "sg_s_ret", "load": "sg_s_load", "fire": "sg_s_fire", "backstop": "sg_s_bs"}
# (side, band) -> (rotor carrier, rotor foil whose node the tip carries, stator carrier)
BANDS = {("A", "bar"): ("A-flange", "Cx4_bars", "ND2"), ("A", "return"): ("A-disc", "C1_rotor", "ND1"),
         ("B", "bar"): ("B-flange", "Cx3_bars", "ND3"), ("B", "return"): ("B-disc", "C2_rotor", "ND4")}
BODY_OF = {"stator": "stator", "rotor A": "rotor", "rotor B": "rotor"}      # A and B co-rotate: one body for HV
ROTOR_BODY = {"A-disc": "rotor A", "A-flange": "rotor A", "B-disc": "rotor B", "B-flange": "rotor B"}
SPOKES = 6                                       # each gap x 6, every 60 deg (freeze §5)


def _pol(r, a_deg, z):
    a = math.radians(a_deg)
    return [r * math.cos(a), r * math.sin(a), z]


def _face_toward(c, other):
    """The z of carrier c's face that looks at carrier other (the bare carrier face, behind its foil)."""
    return c["z1"] if other["z0"] >= c["z1"] - 1e-9 else c["z0"]


def _sdeg(x):
    """x wrapped to [-180, 180) degrees (same arithmetic as the JS mirror)."""
    return x - 360.0 * math.floor((x + 180.0) / 360.0)


def _nearest_inside(a, starts, w, ins):
    """The angle nearest to a that lies inside one of the sectors (start, width w) by at least ins degrees
    (a itself when it already does). Unwrapped about a; ties go to the first sector."""
    half = max(0.0, w / 2 - ins)
    best = None
    for s0 in starts:
        d = _sdeg(a - (s0 + w / 2))
        cl = min(half, max(-half, d))
        if best is None or abs(d - cl) < abs(best) - 1e-9:
            best = d - cl
    return a - best if best is not None else a


def _route(r0, a0, z, foil, zf, R_ch, run_starts, w_run, ins_mm):
    """An embedded lead from (r0, a0) at depth z to foil (riser to its mid-plane zf) [IR routing]: radial runs are
    made in the sectors of the OTHER parity (run_starts), where the facing carriers hold no counter-electrode of
    this one; sector changes happen on the chord ring R_ch (beyond every electrode) or under the target foil
    itself. Returns the polyline as (r, a, z) points and one description per segment."""
    r_t = foil["r_out"] - min(10.0, (foil["r_out"] - foil["r_in"]) / 2)
    ins = math.degrees(ins_mm / r_t)
    pts, what = [(r0, a0, z)], []
    # the electrode stands right over its own foil: straight down to it
    if foil["r_in"] + ins_mm <= r0 <= foil["r_out"] - ins_mm and abs(_nearest_inside(a0, foil["starts"], foil["w_deg"], math.degrees(ins_mm / r0)) - a0) < 1e-9:
        pts.append((r0, a0, zf)); what.append(f"riser straight to {foil['id']} (node {foil['node']})")
        return pts, what

    def arc(r, a_from, a_to, txt):
        n = max(1, math.ceil(abs(a_to - a_from) / 10.0 - 1e-9))
        for i in range(1, n + 1):
            pts.append((r, a_from + (a_to - a_from) * i / n, z)); what.append(txt)
    ar = _nearest_inside(a0, run_starts, w_run, ins)
    if abs(ar - a0) > 1e-9:
        pts.append((R_ch, a0, z)); what.append(f"radial to the chord ring R{_mm(R_ch)}")
        arc(R_ch, a0, ar, f"round the chord ring to {_mm(_m360(ar))} deg")
    at = _nearest_inside(ar, foil["starts"], foil["w_deg"], ins)
    pts.append((r_t, ar, z)); what.append(f"radial to r{_mm(r_t)} at {_mm(_m360(ar))} deg")
    if abs(at - ar) > 1e-9:
        arc(r_t, ar, at, f"under {foil['id']} to {_mm(_m360(at))} deg")
    pts.append((r_t, at, zf)); what.append(f"riser to {foil['id']} (node {foil['node']})")
    return pts, what


def _route_rim(r0, a0, z, foil, zf, R_ch, run_starts, w_run, ins_mm):
    """A lead entering its own carrier at the rim (radial bar band): straight in at a0 under the foil and up into it
    when a0 lies inside one of the foil's sectors, else the general route [IR routing]."""
    r_t = foil["r_out"] - min(10.0, (foil["r_out"] - foil["r_in"]) / 2)
    if abs(_nearest_inside(a0, foil["starts"], foil["w_deg"], math.degrees(ins_mm / r_t)) - a0) < 1e-9:
        return ([(r0, a0, z), (r_t, a0, z), (r_t, a0, zf)],
                [f"radial in to r{_mm(r_t)} under {foil['id']}", f"riser to {foil['id']} (node {foil['node']})"])
    return _route(r0, a0, z, foil, zf, R_ch, run_starts, w_run, ins_mm)


def _foil_carriers(st):
    """foil id -> the carrier it lies on (its neighbour in the stack)."""
    out = {}
    for i, it in enumerate(st):
        if it["kind"] == "foil":
            nb = [st[j] for j in (i - 1, i + 1) if 0 <= j < len(st) and st[j]["kind"] in CARRIER_KINDS]
            out[it["id"]] = nb[0]["id"] if nb else ""
    return out


def sparkgaps(design):
    g = design["geom"]; st = design["stack"]; fp = design["footprints"]
    byid = {it["id"]: it for it in st}
    on = _foil_carriers(st)
    R_e = design["r_edge"]
    R_frame = R_e + g["sg_frame"]
    R_ch = R_e - g["sg_chord"]
    rim = {c: byid[c]["r_out"] for c in CARRIER_BASE}          # carrier rims (ND2 / ND3 trimmed in the radial layout)
    chord = {c: rim[c] - g["sg_chord"] for c in CARRIER_BASE}   # each carrier's chord ring
    rod = g["sg_rod"] / 2
    ins_mm = rod + g["sg_cover"]
    smap = {cls: g[k] for cls, k in SPACING_KEY.items()}
    w_sec = 360.0 / design["lock"]["plates"]["N_sec"]
    grid = {"odd": [w_sec + 2 * w_sec * k for k in range(int(design["lock"]["plates"]["N_sec"]) // 2)],
            "even": [2 * w_sec * k for k in range(int(design["lock"]["plates"]["N_sec"]) // 2)]}

    def run_of(foil):                                  # the grid sectors of the other parity than this foil
        c = foil["starts"][0] + foil["w_deg"] / 2
        return grid["even"] if int(math.floor(_m360(c) / w_sec + 1e-9)) % 2 else grid["odd"]
    needs = band_needs(g, design["lock"]["plates"])
    bands, recesses, lead_z = {}, [], {}
    for (side, band), (rc, rfoil, sc) in BANDS.items():
        rcar, scar = byid[rc], byid[sc]
        zr, zs = _face_toward(rcar, scar), _face_toward(scar, rcar)
        D = abs(zs - zr)                                   # bare face to bare face (gap + both foils)
        nb = needs[(side, band)]
        sgn = 1.0 if zs > zr else -1.0                     # direction rotor face -> stator face
        mine = [x for x in GAPS if x[4] == side and x[5] == band]
        R_t = g["sg_d"] / 2
        if nb["layout"] == "radial":
            # the tips just outside the trimmed rim (room for the bare rim stems and the running clearance), the load
            # sphere beside them, centre to centre R_tip + s_load + R_load further out; heights from _radial_needs
            ld = next(x for x in mine if x[1] == "load")
            R_v = max(sphere_d(g, x[1]) / 2 for x in mine if x[1] != "load")
            r_c = max(g["sg_rbar"], rim[sc] + max(g["sg_stem_air"] + R_v, R_t + g["sg_clear"]))
            r_l = r_c + R_t + smap[ld[1]] + sphere_d(g, ld[1]) / 2
            bands[(side, band)] = dict(side=side, band=band, rotor_carrier=rc, stator_carrier=sc, r=r_c, r0=rim[sc],
                                       r1=r_l + sphere_d(g, ld[1]) / 2 + 2.0, D=D, G=D, recess=0.0, Fr=zr, Fs=zs, sgn=sgn,
                                       rotor_node=fp[rfoil]["node"], p_rot=nb["p_rot"], e_st=0.0, e_rot=0.0,
                                       layout="radial", r_rim=rim[sc], r_load=r_l, z_tip=zs - sgn * nb["zeta_tip"],
                                       z_st={k: zs - sgn * v for k, v in nb["zeta"].items()})
            lead_z[sc] = zs - sgn * nb["lead"]             # the deepest rim stem's plane (the other leads use it too)
            lead_z[rc] = zr - sgn * (g["sg_seat"] + rod)   # behind the tip stems' seats in the flange
            continue
        rec = max(0.0, nb["need"] - D) / 2                 # recess each face by half the shortfall
        Fr, Fs = zr - sgn * rec, zs + sgn * rec            # recessed band faces
        G = abs(Fs - Fr)
        r_c = g["sg_rbar"] if band == "bar" else g["sg_rrail"]
        dmax = max(sphere_d(g, x[1]) for x in mine)
        r0, r1 = r_c - dmax / 2 - 2.0, r_c + dmax / 2 + 2.0   # band ring (2 mm margin around the spheres)
        bands[(side, band)] = dict(side=side, band=band, rotor_carrier=rc, stator_carrier=sc, r=r_c, r0=r0, r1=r1,
                                   D=D, G=G, recess=rec, Fr=Fr, Fs=Fs, sgn=sgn, rotor_node=fp[rfoil]["node"],
                                   p_rot=nb["p_rot"], e_st=nb["e_st"], e_rot=nb["e_rot"], layout="axial", r_rim=rim[sc],
                                   r_load=r_c, z_tip=Fr + sgn * (nb["p_rot"] - R_t),
                                   z_st={x[0]: Fs - sgn * ((G - smap[x[1]] - nb["p_rot"]) - sphere_d(g, x[1]) / 2) for x in mine})
        # the lead plane of a band host: below the deepest socket + the stem seat (into the carrier, away from the gap)
        lead_z[sc] = Fs + sgn * (nb["e_st"] + g["sg_seat"] + rod)
        lead_z[rc] = Fr - sgn * (nb["e_rot"] + g["sg_seat"] + rod)
        if rec > 0:
            recesses.append(dict(carrier=rc, r0=r0, r1=r1, depth=rec, face=("z1" if sgn > 0 else "z0")))
            recesses.append(dict(carrier=sc, r0=r0, r1=r1, depth=rec, face=("z0" if sgn > 0 else "z1")))
    for c in CARRIER_BASE:
        lead_z.setdefault(c, 0.5 * (byid[c]["z0"] + byid[c]["z1"]))

    def target(carrier, node, z):
        """the foil of this node on this carrier nearest the lead plane (ties: stack order)"""
        best = None
        for it in st:
            if it["kind"] == "foil" and on[it["id"]] == carrier and it["node"] == node:
                dz = abs(0.5 * (it["z0"] + it["z1"]) - z)
                if best is None or dz < best[0] - 1e-9:
                    best = (dz, it)
        return best[1]
    gaps, items, routes = [], [], []

    def polyline(pts, name, gap, node, chains, side, body, carrier, what, embedded):
        """rod items along a polyline of (r, a, z) points; letters a, b, ... in order"""
        out = []
        for i in range(len(pts) - 1):
            p0, p1 = _pol(*pts[i]), _pol(*pts[i + 1])
            if math.dist(p0, p1) < 1e-9:
                continue
            out.append(dict(kind="rod", name=f"{name}{chr(97 + len(out))}", gap=gap, node=node, role="gap-lead",
                            p0=p0, p1=p1, r=rod, chains=chains, side=side, body=body, carrier=carrier[i] if isinstance(carrier, list) else carrier,
                            embedded=embedded[i] if isinstance(embedded, list) else embedded, riser=i == len(pts) - 2,
                            desc=f"{what[i] if isinstance(what, list) else what}"))
        return out
    for name, cls, snode, rot, side, band, stn in GAPS:
        b = bands[(side, band)]
        s_ = smap[cls]
        d_st = sphere_d(g, cls)
        R_ = d_st / 2
        car = NODE_CARRIER[snode]; host = b["stator_carrier"]
        foreign = car != host
        crossover = foreign and SIDE_OF_CARRIER[car] != side
        hz, cz = lead_z[host], lead_z[car]
        z_st = b["z_st"][name]
        if b["layout"] == "radial":                        # stems in air: the whole sphere is exposed, no socket
            mount = "arm" if cls == "load" else "rim"
            p_st, e_ = d_st, 0.0
            r_st = b["r_load"] if mount == "arm" else b["r"]
        else:
            mount = "socket"
            p_st = b["G"] - s_ - b["p_rot"]
            e_ = d_st - p_st                               # socket depth (< 0: the sphere stands on its stem)
            r_st = b["r"]
        s_car = "stator frame" if mount == "arm" else host
        lead_len = arm_len = 0.0
        for k in range(SPOKES):
            a = stn + 60.0 * k
            ch = [f"btn-{name}-{k + 1}", host] + ([car] if foreign else [])
            cen = _pol(r_st, a, z_st)
            if mount == "socket":
                where = (f"on {host} at r{_mm(r_st)} {_mm(a % 360.0)} deg, apex {_mm(p_st)} mm proud, "
                         + (f"{_mm(e_)} mm in its socket" if e_ >= 0 else f"on its stem {_mm(-e_)} mm above the face"))
                s_end, s_what = (r_st, a, hz), f"sphere centre to the lead plane in {host}"
            elif mount == "rim":
                where = (f"at r{_mm(r_st)} {_mm(a % 360.0)} deg on a radial stem out of the {host} rim r{_mm(b['r_rim'])}, "
                         f"centre {_mm(abs(z_st - b['Fs']))} mm below its Cx face, under the tip path (vertical gap)")
                s_end = (b["r_rim"] - g["sg_seat"], a, z_st)
                s_what = f"radial, sphere centre into the {host} rim (seated {_mm(g['sg_seat'])} mm)"
            else:
                where = (f"at r{_mm(r_st)} {_mm(a % 360.0)} deg on a radial arm in from the stator frame R{_mm(R_frame)}, "
                         f"at the tip height beside its path (horizontal gap)")
                s_end, s_what = (R_frame, a, z_st), f"radial, sphere centre out to the stator frame R{_mm(R_frame)}"
            items.append(dict(kind="sphere", name=f"{name}_sph_{k + 1}", gap=name, node=snode, role="gap-stator",
                              c=cen, r=R_, chains=ch, side=side, body="stator", carrier=s_car, band=f"{side}-{band}",
                              desc=f"{name} stator sphere {k + 1} of {SPOKES} ({cls}), node {snode}, {_mm(d_st)} mm "
                                   f"{'polished' if cls == 'backstop' else 'W-Cu'} {where}, gap {_mm(s_)} mm to the {rot} tip"
                                   + (f" - fed from {car}" + (" by a CROSSOVER over the stator" if crossover else "") if foreign else "")))
            items.append(dict(kind="rod", name=f"{name}_stem_{k + 1}", gap=name, node=snode, role="gap-stem",
                              p0=list(cen), p1=_pol(*s_end), r=g["sg_stem"] / 2, chains=ch, side=side, body="stator",
                              carrier=s_car, embedded=False, band=f"{side}-{band}",
                              desc=f"{name} {'arm' if mount == 'arm' else 'stem'} {k + 1} (node {snode}): {s_what}"))
            f = target(car, snode, z_st if mount == "rim" else cz)
            zf = 0.5 * (f["z0"] + f["z1"])
            nm = f"{name}_lead_{k + 1}"
            if mount == "rim":                             # straight in from the rim to its own electrode
                pts, w_in = _route_rim(s_end[0], a, z_st, f, zf, chord[car], run_of(f), w_sec, ins_mm)
                n_in = len(pts) - 1
                carriers, emb = car, [True] * (n_in - 1) + [False]
                what = [f"in {car}: {x}" for x in w_in]
            elif mount == "arm":                           # from the arm's frame end along the frame into its node's carrier
                inner, w_in = _route(rim[car], a, cz, f, zf, chord[car], run_of(f), w_sec, ins_mm)
                pts = [s_end, (R_frame, a, cz)] + inner
                n_in = len(inner) - 1
                carriers = ["stator frame", car] + [car] * n_in
                emb = [False, False] + [True] * (n_in - 1) + [False]
                what = ([f"along the frame R{_mm(R_frame)} to {car}" + (" - CROSSOVER over the stator" if crossover else ""),
                         f"into the {car} rim"] + [f"in {car}: {x}" for x in w_in])
            elif foreign:
                inner, w_in = _route(rim[car], a, cz, f, zf, chord[car], run_of(f), w_sec, ins_mm)
                pts = [(r_st, a, hz), (rim[host], a, hz), (R_frame, a, hz), (R_frame, a, cz)] + inner
                n_in = len(inner) - 1
                carriers = [host, host, host] + [car] * (n_in + 1)
                emb = [True, False, False, False] + [True] * (n_in - 1) + [False]      # risers are not "embedded runs"
                what = ([f"embedded in {host}, radial to its rim", "out to the stator frame",
                         f"along the frame R{_mm(R_frame)} to {car}" + (" - CROSSOVER over the stator" if crossover else ""),
                         f"into the {car} rim"] + [f"in {car}: {x}" for x in w_in])
            else:
                pts, w_in = _route(r_st, a, hz, f, zf, chord[host], run_of(f), w_sec, ins_mm)
                n_in = len(pts) - 1
                carriers, emb = host, [True] * (n_in - 1) + [False]
                what = [f"in {host}: {x}" for x in w_in]
            segs = polyline(pts, nm, name, snode, ch, side, "stator", carriers, what, emb)
            for sgm in segs:
                sgm["desc"] = f"{name} lead {k + 1} (node {snode}): " + sgm["desc"]
            items += segs
            routes.append(dict(electrode=f"{name}_sph_{k + 1}", node=snode, foil=f["id"], carrier=car, end=list(pts[-1])))
            if k == 0:
                lead_len = sum(math.dist(x["p0"], x["p1"]) for x in segs)
                arm_len = math.dist(cen, _pol(*s_end)) if mount == "arm" else 0.0
        gaps.append(dict(name=name, cls=cls, stator_node=snode, rotor=rot, side=side, band=band, station=stn,
                         spacing=s_, d_stator=d_st, d_rotor=g["sg_d"], r=r_st, p_stator=p_st, p_rotor=b["p_rot"], socket=e_,
                         host=host, carrier=car, foreign=foreign, crossover=crossover, lead_len=lead_len, mount=mount,
                         gap_axis="horizontal" if mount == "arm" else "vertical", z_stator=z_st, r_tip=b["r"],
                         z_tip=b["z_tip"], arm_len=arm_len))
    for (side, band), b in bands.items():
        rc = b["rotor_carrier"]
        bar = band == "bar"
        radial = b["layout"] == "radial"
        rfoil = BANDS[(side, band)][1]
        tipn = "bartip" if bar else "rotortip"
        kind_t = "island bar" if bar else "rotor face"
        f = target(rc, b["rotor_node"], lead_z[rc])
        zf = 0.5 * (f["z0"] + f["z1"])
        for k in range(SPOKES):
            a = 60.0 * k + g["sg_tip_deg"]                 # a tip meets station s when the rotor has turned by s - tip [IR]
            ch = [f"tip-{side}-{band}", rc, rfoil]
            cen = _pol(b["r"], a, b["z_tip"])
            where = (f"hanging from {rc} at r{_mm(b['r'])} {_mm(a)} deg outside the {b['stator_carrier']} rim "
                     f"r{_mm(b['r_rim'])}, its bottom {_mm(b['p_rot'])} mm below the face" if radial else
                     f"on {rc} at r{_mm(b['r'])} {_mm(a)} deg, apex {_mm(b['p_rot'])} mm proud, "
                     f"{_mm(g['sg_d'] - b['p_rot'])} mm in its socket")
            items.append(dict(kind="sphere", name=f"{tipn}_{side}_{k + 1}", gap="", node=b["rotor_node"],
                              role="gap-rotor", c=cen, r=g["sg_d"] / 2, chains=ch, side=side, body=ROTOR_BODY[rc], carrier=rc,
                              band=f"{side}-{band}",
                              desc=f"{kind_t} tip {k + 1} of {SPOKES} (node {b['rotor_node']}, {ROTOR_BODY[rc]}), "
                                   f"{_mm(g['sg_d'])} mm W-Cu sphere {where}"))
            items.append(dict(kind="rod", name=f"{tipn}_{side}_stem_{k + 1}", gap="", node=b["rotor_node"], role="gap-stem",
                              p0=list(cen), p1=_pol(b["r"], a, lead_z[rc]), r=g["sg_stem"] / 2, chains=ch, side=side,
                              body=ROTOR_BODY[rc], carrier=rc, embedded=False, band=f"{side}-{band}",
                              desc=f"{kind_t} tip {k + 1} stem (node {b['rotor_node']}): sphere centre to the lead plane in {rc}"))
            # radial: the flange lead changes sector at the tip radius, inside the load arms passing under the flange
            pts, w_in = _route(b["r"], a, lead_z[rc], f, zf, b["r"] if radial else chord[rc], run_of(f), w_sec, ins_mm)
            n_in = len(pts) - 1
            what = [f"in {rc}: {x}" for x in w_in]
            segs = polyline(pts, f"{tipn}_{side}_lead_{k + 1}", "", b["rotor_node"], ch, side, ROTOR_BODY[rc], rc, what,
                            [True] * (n_in - 1) + [False])
            for sgm in segs:
                sgm["desc"] = f"{kind_t} tip {k + 1} lead (node {b['rotor_node']}): " + sgm["desc"]
            items += segs
            routes.append(dict(electrode=f"{tipn}_{side}_{k + 1}", node=b["rotor_node"], foil=f["id"], carrier=rc, end=list(pts[-1])))
    # equipotential links: the two same-node foils of a carrier, one link per sector, through the carrier
    for c, (k1, k2) in LINKS.items():
        f1, f2, cc = byid[k1], byid[k2], byid[c]
        rr = 0.5 * (max(f1["r_in"], f2["r_in"]) + min(f1["r_out"], f2["r_out"]))
        for k, s0 in enumerate(f1["starts"]):
            a = s0 + f1["w_deg"] / 2
            items.append(dict(kind="rod", name=f"{c.replace('-', '_')}_link_{k + 1}", gap="", node=f1["node"], role="link",
                              p0=_pol(rr, a, 0.5 * (f1["z0"] + f1["z1"])), p1=_pol(rr, a, 0.5 * (f2["z0"] + f2["z1"])), r=rod,
                              chains=[f"link-{c}", c], side=cc["side"], body=ROTOR_BODY.get(c, "stator"), carrier=c, embedded=False,
                              desc=f"{c} equipotential link {k + 1} of {len(f1['starts'])} (node {f1['node']}): {k1} <-> {k2} through "
                                   f"{c} at r{_mm(rr)} {_mm(_m360(a))} deg, {_mm(abs(cc['z1'] - cc['z0']))} mm"))
    # bus rings: an electrode's sectors are one net only if something joins them. One ring per node per carrier,
    # embedded under the face of that node's foil (the foil with a FIXED partner if it has one), at the electrode's
    # inner edge, one riser into every sector; a later ring of another node in the same carrier moves outward to
    # keep the HV clearance [IR]
    hv = g["sg_khv"] * max(g["sg_s_ret"], g["sg_s_load"], g["sg_s_fire"], g["sg_s_bs"])
    bw = g["sg_bus"]
    for c in CARRIER_BASE:
        cc = byid[c]
        mine = [it for it in st if it["kind"] == "foil" and on[it["id"]] == c]
        mine = [it for it in mine if it["cap"] in ROTATING] + [it for it in mine if it["cap"] not in ROTATING]
        nodes = []
        for it in mine:
            if it["node"] not in nodes:
                nodes.append(it["node"])
        placed = []
        for nd in nodes:
            fs = [it for it in mine if it["node"] == nd]
            f = next((it for it in fs if it["cap"] not in ROTATING), fs[0])
            up = f["z0"] >= cc["z1"] - 1e-9                # the foil lies on the carrier's upper face
            fc = far_cover(g, c)
            zc = (cc["z1"] - fc - bw / 2) if up else (cc["z0"] + fc + bw / 2)
            r = f["r_in"] + bw / 2
            for rp, zp in placed:
                dzs = max(0.0, abs(zc - zp) - bw)
                if dzs < hv:
                    r = max(r, rp + bw + math.sqrt(hv * hv - dzs * dzs))
            placed.append((r, zc))
            nk = nd.replace("-", "")
            ch = [f"bus-{c}-{nd}", c]
            body = ROTOR_BODY.get(c, "stator")
            items.append(dict(kind="sector", name=f"bus_{c.replace('-', '_')}_{nk}", gap="", node=nd, role="bus",
                              r_in=r - bw / 2, r_out=r + bw / 2, start_deg=0.0, w_deg=360.0, z0=zc - bw / 2, z1=zc + bw / 2,
                              chains=ch, side=cc["side"], body=body, carrier=c, embedded=True,
                              desc=f"{c} bus ring (node {nd}): joins the {len(f['starts'])} sectors of {f['id']}, r{_mm(r)}, "
                                   f"{_mm(bw)} x {_mm(bw)} mm, embedded {_mm(fc)} mm under its face"))
            for k, s0 in enumerate(f["starts"]):
                a = s0 + f["w_deg"] / 2
                items.append(dict(kind="rod", name=f"bus_{c.replace('-', '_')}_{nk}_riser_{k + 1}", gap="", node=nd, role="bus",
                                  p0=_pol(r, a, zc), p1=_pol(r, a, 0.5 * (f["z0"] + f["z1"])), r=rod, chains=ch, side=cc["side"],
                                  body=body, carrier=c, embedded=False, riser=True,
                                  desc=f"{c} bus riser {k + 1} of {len(f['starts'])} (node {nd}): bus ring to {f['id']} at "
                                       f"{_mm(_m360(a))} deg"))
    out = dict(R_frame=R_frame, R_chord=R_ch, bands={f"{k[0]}-{k[1]}": v for k, v in bands.items()}, recesses=recesses,
               lead_z=lead_z, gaps=gaps, routes=routes, items=items)
    out["checks"] = gap_checks(design, out)
    return out


def cx_facings(design):
    """The mica facings of the Cx gaps (freeze v0.10: air + cx_mica per face): one slab on each foil's face, the
    foil's footprint + the dielectric margin, on the foil's body (pickup: stator, bars: rotor) [OC freeze]."""
    g = design["geom"]; st = design["stack"]; fp = design["footprints"]
    on = _foil_carriers(st)
    m, t = g["ca_margin"], g["cx_mica"]
    out = []
    if t <= 0:
        return out
    for i, it in enumerate(st):
        if it["kind"] != "gap" or it["cap"] not in ("Cx3", "Cx4"):
            continue
        for j, low in ((i - 1, True), (i + 1, False)):
            f = st[j]
            e = fp[f["key"]]
            z0, z1 = (it["z0"], it["z0"] + t) if low else (it["z1"] - t, it["z1"])
            rin, rout = max(0.0, e["r_in"] - m), e["r_out"] + m
            dw = math.degrees(m / max(e["r_in"], 1e-9))
            body = ROTOR_BODY.get(on[f["id"]], "stator")
            for k, s0 in enumerate(e["starts"]):
                out.append(dict(name=f"{it['cap']}_mica_{'bars' if body != 'stator' else 'pickup'}_{k + 1}", cap=it["cap"],
                                foil=f["id"], r_in=rin, r_out=rout, start_deg=s0 - dw, w_deg=min(e["w_deg"] + 2 * dw, 360.0),
                                z0=z0, z1=z1, body=body, carrier=on[f["id"]]))
    return out


def sweep_check(design, sg):
    """Counter-rotation: no rotor part may share (r, z) with any stator part once both are revolved. Returns
    (n_rotor, n_stator, hits) over the carriers (with their recesses), the foils, the dielectrics and the gap parts."""
    st = design["stack"]
    carrier_of = {}
    for i, it in enumerate(st):
        if it["kind"] == "foil":
            nb = [st[j] for j in (i - 1, i + 1) if 0 <= j < len(st) and st[j]["kind"] in CARRIER_KINDS]
            carrier_of[it["id"]] = nb[0]["id"] if nb else ""
    env = []
    for it in st:
        if it["kind"] in CARRIER_KINDS:
            b = ROTOR_BODY.get(it["id"], "stator")
            for ring in _carrier_rings(it, sg["recesses"]):
                env.append((b, it["id"], ring))
        elif it["kind"] == "foil":
            env.append((ROTOR_BODY.get(carrier_of[it["id"]], "stator"), it["id"], (it["r_in"], it["r_out"], it["z0"], it["z1"])))
        elif it["kind"] == "gap" and it.get("medium") in MEDIUM_RGB and it.get("footprint"):
            e = design["footprints"][it["footprint"]]; m = it.get("margin", 0.0)
            env.append(("stator", it["id"], (max(0.0, e["r_in"] - m), e["r_out"] + m, it["z0"], it["z1"])))
        elif it["kind"] == "gap" and it.get("medium") in MEDIUM_RGB:
            env.append(("rotor AB", it["id"], (it.get("r_in", 0.0), it.get("r_out", design["r_edge"]), it["z0"], it["z1"])))
    for x in cx_facings(design):
        env.append((x["body"], x["name"], (x["r_in"], x["r_out"], x["z0"], x["z1"])))
    for it in sg["items"]:
        if it["kind"] == "sector":
            e = (it["r_in"], it["r_out"], it["z0"], it["z1"])
        elif it["kind"] == "sphere":
            rc_, R_ = math.hypot(it["c"][0], it["c"][1]), it["r"]
            e = (rc_ - R_, rc_ + R_, it["c"][2] - R_, it["c"][2] + R_)
        else:
            a, b = it["p0"], it["p1"]
            ra, rb = math.hypot(a[0], a[1]), math.hypot(b[0], b[1])
            rr = it["r"]
            if math.hypot(a[0] - b[0], a[1] - b[1]) < 1e-9:   # axial stem / riser / link: a disc of radius r about its axis
                e = (ra - rr, ra + rr, min(a[2], b[2]), max(a[2], b[2]))
            else:                                           # any other lead: its radial span (chords dip inward) +- r
                e = (_seg_rmin(a, b) - rr, max(ra, rb) + rr, min(a[2], b[2]) - rr, max(a[2], b[2]) + rr)
        env.append((it["body"], it["name"], e))
    rot = [x for x in env if x[0] in ("rotor A", "rotor B", "rotor AB")]
    sta = [x for x in env if x[0] == "stator"]
    hits = []
    for b1, n1, e in rot:
        for b2, n2, f in sta:
            if e[0] < f[1] - 1e-9 and f[0] < e[1] - 1e-9 and e[2] < f[3] - 1e-9 and f[2] < e[3] - 1e-9:
                hits.append((n1, n2))
    return len(rot), len(sta), hits


def _seg_rmin(a, b):
    """the smallest distance from the z axis along the segment a-b (its plan projection)."""
    dx, dy = b[0] - a[0], b[1] - a[1]
    L2 = dx * dx + dy * dy
    t = 0.0 if L2 < 1e-18 else min(1.0, max(0.0, -(a[0] * dx + a[1] * dy) / L2))
    return math.hypot(a[0] + t * dx, a[1] + t * dy)


def _seg_dist(p, q, r, s):
    """the smallest distance between segments p-q and r-s (3-D)."""
    d1 = [q[i] - p[i] for i in range(3)]; d2 = [s[i] - r[i] for i in range(3)]; w = [p[i] - r[i] for i in range(3)]
    a = sum(x * x for x in d1); e = sum(x * x for x in d2); f_ = sum(d2[i] * w[i] for i in range(3))
    if a < 1e-18 and e < 1e-18:
        return math.dist(p, r)
    if a < 1e-18:
        t, u = 0.0, min(1.0, max(0.0, f_ / e))
    else:
        c = sum(d1[i] * w[i] for i in range(3))
        if e < 1e-18:
            t, u = min(1.0, max(0.0, -c / a)), 0.0
        else:
            bb = sum(d1[i] * d2[i] for i in range(3)); den = a * e - bb * bb
            t = min(1.0, max(0.0, (bb * f_ - c * e) / den)) if den > 1e-12 else 0.0
            u = (bb * t + f_) / e
            if u < 0.0:
                t, u = min(1.0, max(0.0, -c / a)), 0.0
            elif u > 1.0:
                t, u = min(1.0, max(0.0, (bb - c) / a)), 1.0
    return math.dist([p[i] + d1[i] * t for i in range(3)], [r[i] + d2[i] * u for i in range(3)])


def _foil_dist(pt, f, lat=0.0):
    """distance from a point to a foil (its sectors as annular slabs); lat: the lateral radius of a vertical rod
    through the point (its flat end then faces the foil)."""
    r = math.hypot(pt[0], pt[1]); a = math.degrees(math.atan2(pt[1], pt[0]))
    dz = max(0.0, f["z0"] - pt[2], pt[2] - f["z1"])
    best = float("inf")
    for s0 in f["starts"]:
        d = _sdeg(a - (s0 + f["w_deg"] / 2))
        if abs(d) <= f["w_deg"] / 2 or f["w_deg"] >= 360.0 - 1e-9:
            dp = max(0.0, f["r_in"] - r, r - f["r_out"])
        else:
            dp = float("inf")
            for e_ in (s0, s0 + f["w_deg"]):
                ex, ey = math.cos(math.radians(e_)), math.sin(math.radians(e_))
                t = min(f["r_out"], max(f["r_in"], pt[0] * ex + pt[1] * ey))
                dp = min(dp, math.hypot(pt[0] - t * ex, pt[1] - t * ey))
        best = min(best, math.hypot(max(0.0, dp - lat), dz))
    return best


def _carrier_rings(c, recesses):
    """A carrier as radial rings (r0, r1, z0, z1): full thickness, thinned where a band is recessed."""
    cuts = sorted([r for r in recesses if r["carrier"] == c["id"]], key=lambda r: r["r0"])
    rings, r = [], c["r_in"]
    for cut in cuts:
        if cut["r0"] > r:
            rings.append((r, cut["r0"], c["z0"], c["z1"]))
        z0, z1 = c["z0"], c["z1"]
        if cut["face"] == "z1":
            z1 -= cut["depth"]
        else:
            z0 += cut["depth"]
        rings.append((cut["r0"], cut["r1"], z0, z1))
        r = cut["r1"]
    if r < c["r_out"]:
        rings.append((r, c["r_out"], c["z0"], c["z1"]))
    return rings


def gap_checks(design, sg):
    g = design["geom"]; fp = design["footprints"]; byid = {it["id"]: it for it in design["stack"]}
    res = {}
    smax = max(g["sg_s_ret"], g["sg_s_load"], g["sg_s_fire"], g["sg_s_bs"])
    need = g["sg_khv"] * smax
    bad = [x["name"] for x in sg["gaps"] if set(NETLIST_GAPS[x["name"]]) != {x["stator_node"], ROTOR_NODE[x["rotor"]]}]
    res["nodes = netlist of record (topology_edge_list.csv)"] = (not bad, "all 8 gaps" if not bad else "mismatch: " + ", ".join(bad))
    # spacing at alignment: the two sphere centres (same angle) less both radii, along the gap's own axis
    worst = 0.0
    for x in sg["gaps"]:
        cc = math.hypot(x["r"] - x["r_tip"], x["z_stator"] - x["z_tip"])
        worst = max(worst, abs(cc - x["d_stator"] / 2 - x["d_rotor"] / 2 - x["spacing"]))
    hor = [x["name"] for x in sg["gaps"] if x["gap_axis"] == "horizontal"]
    res["spacing at alignment = the freeze table"] = (worst < 1e-9, "; ".join(f"{x['name']} {_mm(x['spacing'])}" for x in sg["gaps"]) + " mm"
                                                      + (f" ({', '.join(hor)} horizontal, the rest vertical)" if hor else ""))
    # spheres in sockets show their exposure; the radial bar band's spheres and tips stand clear on their stems
    ex = sorted(((x["p_stator"] / x["d_stator"], f"{x['name']} {_mm(x['p_stator'])} of {_mm(x['d_stator'])} mm")
                 for x in sg["gaps"] if x["mount"] == "socket"), key=lambda t: t[0])[0]
    exr = min(b["p_rot"] / g["sg_d"] for b in sg["bands"].values() if b["layout"] == "axial")
    free = [x["name"] for x in sg["gaps"] if x["mount"] != "socket"]
    res["every sphere shows at least its exposure above the face"] = (
        min(ex[0], exr) >= g["sg_expose"] - 1e-9,
        f"stator: least {ex[1]} ({_mm(100 * ex[0])} %), rotor tips {_mm(100 * exr)} % (>= {_mm(100 * g['sg_expose'])} %)"
        + (f"; {', '.join(free)} and the bar tips stand clear on their stems (radial bar band)" if free else ""))
    wr, wn = 0.0, ""
    for x in sg["gaps"]:
        q = x["spacing"] / min(x["d_stator"], x["d_rotor"])
        if q > wr + 1e-9:
            wr, wn = q, x["name"]
    res["sphere gaps in the uniform-field range (s <= 0.5 D, IEC 60052)"] = (wr <= 0.5 + 1e-9, f"largest s/D {_mm(wr)} ({wn})")
    db = float(design["lock"].get("inputs", {}).get("d_ballMm", 12.0))
    res["switching sphere = the stage-1 sphere-gap ball d_ball"] = (abs(g["sg_d"] - db) < 1e-9, f"{_mm(g['sg_d'])} vs d_ball {_mm(db)} mm")
    # recess material
    worst, det = float("inf"), "no recess needed"
    for rc in sg["recesses"]:
        c = byid[rc["carrier"]]
        left = (c["z1"] - c["z0"]) - rc["depth"]
        if left < worst:
            worst, det = left, f"{rc['carrier']} keeps {_mm(left)} mm under a {_mm(rc['depth'])} mm recess"
    res["recessed bands leave a carrier wall"] = (worst >= g["sg_wall"] - 1e-9, det)
    # bands clear the capacitor electrodes radially (HV)
    for (side, band), (rc, rfoil, sc) in BANDS.items():
        b = sg["bands"][f"{side}-{band}"]
        if band == "bar":
            outer = max(fp[rfoil]["r_out"], fp["Cx4_pickup" if side == "A" else "Cx3_pickup"]["r_out"])
            what = "bars / pickups"
        else:
            outer = max(fp["C1_stator" if side == "A" else "C2_stator"]["r_out"], fp[rfoil]["r_out"])
            what = "C1 / C2 plates"
        cl = (b["r"] - max(g["sg_d"], g["sg_dbs"] if band == "bar" else g["sg_d"]) / 2) - outer
        res[f"{side} {band} band clears the {what} (HV)"] = (cl >= need, f"r{_mm(b['r'])} band: {_mm(cl)} mm beyond r{_mm(outer)} (>= {_mm(need)})")
        res[f"{side} {band} band inside the carriers"] = (b["r1"] <= design["r_edge"] - 1e-9, f"band r{_mm(b['r0'])}-{_mm(b['r1'])} within R{_mm(design['r_edge'])}"
                                                         + (f", under the {rc} (the {sc} rim trimmed to r{_mm(b['r_rim'])})" if b["layout"] == "radial" else ""))
    # the radial bar band: the tips run clear of the trimmed rim, the rim stems keep a bare length, the load sphere
    # (on its arm at the tip's height) runs clear of the flange face
    for b in sg["bands"].values():
        if b["layout"] != "radial":
            continue
        mine = [x for x in sg["gaps"] if x["side"] == b["side"] and x["band"] == b["band"]]
        cl_rim = b["r"] - g["sg_d"] / 2 - b["r_rim"]
        bare = min(x["r"] - x["d_stator"] / 2 - b["r_rim"] for x in mine if x["mount"] == "rim")
        cl_fl = min(abs(b["Fr"] - x["z_stator"]) - x["d_stator"] / 2 for x in mine if x["mount"] == "arm")
        res[f"{b['side']} bar band beside the trimmed {b['stator_carrier']} rim (radial)"] = (
            cl_rim >= g["sg_clear"] - 1e-9 and bare >= g["sg_stem_air"] - 1e-9 and cl_fl >= g["sg_clear"] - 1e-9,
            f"{b['stator_carrier']} trimmed to r{_mm(b['r_rim'])}; tips at r{_mm(b['r'])} clear it by {_mm(cl_rim)} mm, rim stems "
            f"{_mm(bare)} mm bare, the load sphere at r{_mm(b['r_load'])} {_mm(cl_fl)} mm under the {b['rotor_carrier']} face "
            f"(>= {_mm(g['sg_clear'])})")
    # cross-fire between stations on one band (tip aligned with one, distance to every other different-node sphere)
    worst_xf, det = float("inf"), ""
    for x in sg["gaps"]:
        tip = _pol(x["r_tip"], x["station"], x["z_tip"])      # the tip sphere centre, aligned with x
        for y in sg["gaps"]:
            if y is x or y["side"] != x["side"] or y["band"] != x["band"] or y["stator_node"] == x["stator_node"]:
                continue
            for k in range(SPOKES):
                c = _pol(y["r"], y["station"] + 60.0 * k, y["z_stator"])
                surf = math.dist(tip, c) - x["d_rotor"] / 2 - y["d_stator"] / 2       # sphere to sphere
                margin = surf - max(x["spacing"], y["spacing"])
                if margin < worst_xf - 1e-9:
                    worst_xf, det = margin, f"{x['name']} tip vs {y['name']} sphere: {_mm(surf)} mm"
    res["no cross-firing to a different-node station"] = (worst_xf >= 0.5 * max(g["sg_s_load"], g["sg_s_fire"]),
                                                          f"tightest {det} (margin {_mm(worst_xf)} mm over its spacing)")
    r_i = min(b["r"] for b in sg["bands"].values() if b["band"] == "bar")
    ov = math.degrees((g["sg_d"] + 2 * g["sg_glat"]) / r_i)
    res["I11 cross-fire at the placed bar radius"] = (ov < 2.95, f"overlap {_mm(ov)} deg < SG3b-BS3 2.95 deg at r{_mm(r_i)}")
    clf = sg["R_frame"] - g["sg_rod"] / 2 - design["r_edge"]
    res["lead frame clears the rotor rims (HV)"] = (clf >= need, f"R{_mm(sg['R_frame'])}: {_mm(clf)} mm over the R{_mm(design['r_edge'])} rims")
    # ---- Z-stretch and wiring (TMD 2026-10-02) ----
    zs = design["zstretch"]
    short = [k for k, v in zs.items() if v["t"] < v["req"] - 1e-9]
    grown = ", ".join(f"{k} {_mm(v['base'])}->{_mm(v['t'])}" for k, v in zs.items() if v["stretched"])
    res["Z-stretch: every carrier holds its gap seats and leads"] = (not short, (
        "short: " + ", ".join(f"{k} {_mm(zs[k]['t'])} < {_mm(zs[k]['req'])} mm" for k in short)) if short else (
        f"stretched {grown}; stack {_mm(design['z_base'])} -> {_mm(design['z_total'])} mm" if grown
        else f"no stretch needed; stack {_mm(design['z_total'])} mm"))
    bad = []
    for rt in sg["routes"]:
        f = byid[rt["foil"]]
        r, a, z = rt["end"]
        ok = (f["node"] == rt["node"] and f["z0"] - 1e-9 <= z <= f["z1"] + 1e-9 and f["r_in"] - 1e-9 <= r <= f["r_out"] + 1e-9
              and any(abs(_sdeg(a - (s0 + f["w_deg"] / 2))) <= f["w_deg"] / 2 + 1e-9 for s0 in f["starts"]))
        if not ok:
            bad.append(rt["electrode"])
    res["every gap electrode is wired to its node's foil"] = (not bad, (
        f"{len(sg['routes'])} electrodes, each lead ends on a foil of its own node") if not bad else "unwired: " + ", ".join(bad[:4]))
    rec_by = {}
    for rc in sg["recesses"]:
        rec_by.setdefault(rc["carrier"], []).append(rc)
    on = _foil_carriers(design["stack"])
    rings = [it for it in sg["items"] if it["role"] == "bus" and it["kind"] == "sector"]
    foils = [it for it in design["stack"] if it["kind"] == "foil"] + [
        dict(id=x["name"], node=x["node"], r_in=x["r_in"], r_out=x["r_out"], z0=x["z0"], z1=x["z1"], starts=[0.0], w_deg=360.0)
        for x in rings]
    for x in rings:
        on[x["name"]] = x["carrier"]
    w_cov, d_cov, w_own, d_own, w_oth, d_oth = (float("inf"), "none") * 3

    def faces(cid, ra=None, rb=None):                   # a carrier's faces; a recess counts everywhere unless a
        c = byid[cid]                                   # radial span is given (then only where it overlaps)
        lo, hi = c["z0"], c["z1"]
        for rc in rec_by.get(cid, []):
            if ra is not None and (rb <= rc["r0"] or ra >= rc["r1"]):
                continue
            if rc["face"] == "z1":
                hi = min(hi, c["z1"] - rc["depth"])
            else:
                lo = max(lo, c["z0"] + rc["depth"])
        return lo, hi
    for x in rings:
        lo, hi = faces(x["carrier"], x["r_in"], x["r_out"])
        cov = min(x["z0"] - lo, hi - x["z1"])
        if cov < w_cov - 1e-9:
            w_cov, d_cov = cov, f"{x['name']} in {x['carrier']}: {_mm(cov)} mm"
    for it in sg["items"]:
        if it["kind"] != "rod" or it["role"] not in ("gap-lead", "gap-stem"):
            continue
        p0, p1, rr = it["p0"], it["p1"], it["r"]
        stem = it["role"] == "gap-stem"
        zlo, zhi = min(p0[2], p1[2]) - rr, max(p0[2], p1[2]) + rr
        if it["embedded"]:                              # a run inside its carrier keeps its cover to both faces
            lo, hi = faces(it["carrier"])
            cov = min(zlo - lo, hi - zhi)
            if cov < w_cov - 1e-9:
                w_cov, d_cov = cov, f"{it['name']} in {it['carrier']}: {_mm(cov)} mm"
        n = max(1, math.ceil(math.dist(p0, p1) / 2.0 - 1e-9))
        pts = [[p0[i] + (p1[i] - p0[i]) * j / n for i in range(3)] for j in range(n + 1)]
        for f in foils:
            if f["node"] == it["node"] or f["z0"] > zhi + 20.0 or f["z1"] < zlo - 20.0:
                continue
            dd = min(_foil_dist(q, f, rr) for q in pts) if stem else min(_foil_dist(q, f) for q in pts) - rr
            if on[f["id"]] == it["carrier"]:
                if dd < w_own - 1e-9:
                    w_own, d_own = dd, f"{it['name']} (node {it['node']}) to {f['id']} (node {f['node']}) on {it['carrier']}: {_mm(dd)} mm"
            elif it["embedded"] and dd < w_oth - 1e-9:
                w_oth, d_oth = dd, f"{it['name']} (node {it['node']}) to {f['id']} (node {f['node']}) on {on[f['id']]}: {_mm(dd)} mm"
    res["embedded leads and bus rings keep their cover inside the carrier"] = (w_cov >= g["sg_cover"] - 1e-9, f"tightest {d_cov} (>= {_mm(g['sg_cover'])})")
    res["leads clear different-node foils on their carrier"] = (w_own >= g["sg_cover"] - 1e-9, f"tightest {d_own} (>= {_mm(g['sg_cover'])})")
    # different-node conductors on one body (stator, or one rotor half): HV clearance
    # (links and risers are left out: each ends in its own node's foil, inside that foil's sector, so it sees the
    #  counter-electrode across the capacitor's own dielectric -- that is the capacitor, not a clearance)
    cond = [dict(it, p0=it["c"], p1=it["c"]) if it["kind"] == "sphere" else it
            for it in sg["items"] if it["kind"] in ("rod", "sphere") and it["role"] != "link" and not it.get("riser")]
    box = [(min(it["p0"][i], it["p1"][i]) - it["r"], max(it["p0"][i], it["p1"][i]) + it["r"]) for it in cond for i in range(3)]
    w_hv, d_hv = float("inf"), "none"
    for i, x in enumerate(cond):
        bx = box[3 * i:3 * i + 3]
        for j in range(i + 1, len(cond)):
            y = cond[j]
            if BODY_OF[y["body"]] != BODY_OF[x["body"]] or y["node"] == x["node"]:
                continue
            by_ = box[3 * j:3 * j + 3]
            if any(bx[k][0] - by_[k][1] > need or by_[k][0] - bx[k][1] > need for k in range(3)):
                continue
            dd = _seg_dist(x["p0"], x["p1"], y["p0"], y["p1"]) - x["r"] - y["r"]
            if dd < w_hv - 1e-9:
                w_hv, d_hv = dd, f"{x['name']} (node {x['node']}) / {y['name']} (node {y['node']}): {_mm(dd)} mm"
    # the bus rings against them and against each other (a ring is a full annulus: plan distance = radial gap)
    for ri_, R in enumerate(rings):
        Rf = dict(R, starts=[0.0], w_deg=360.0)
        for y in cond:
            if BODY_OF[y["body"]] != BODY_OF[R["body"]] or y["node"] == R["node"]:
                continue
            zl, zh = min(y["p0"][2], y["p1"][2]) - y["r"], max(y["p0"][2], y["p1"][2]) + y["r"]
            rmin, rmax = _seg_rmin(y["p0"], y["p1"]), max(math.hypot(y["p0"][0], y["p0"][1]), math.hypot(y["p1"][0], y["p1"][1]))
            if max(R["z0"] - zh, zl - R["z1"], R["r_in"] - rmax - y["r"], rmin - y["r"] - R["r_out"]) > need:
                continue
            n = max(1, math.ceil(math.dist(y["p0"], y["p1"]) / 2.0 - 1e-9))
            dd = min(_foil_dist([y["p0"][i] + (y["p1"][i] - y["p0"][i]) * j / n for i in range(3)], Rf) for j in range(n + 1)) - y["r"]
            if dd < w_hv - 1e-9:
                w_hv, d_hv = dd, f"{R['name']} (node {R['node']}) / {y['name']} (node {y['node']}): {_mm(dd)} mm"
        for Q in rings[ri_ + 1:]:
            if BODY_OF[Q["body"]] != BODY_OF[R["body"]] or Q["node"] == R["node"]:
                continue
            dd = math.hypot(max(0.0, R["r_in"] - Q["r_out"], Q["r_in"] - R["r_out"]), max(0.0, R["z0"] - Q["z1"], Q["z0"] - R["z1"]))
            if dd < w_hv - 1e-9:
                w_hv, d_hv = dd, f"{R['name']} (node {R['node']}) / {Q['name']} (node {Q['node']}): {_mm(dd)} mm"
    res["different-node leads, spheres and bus rings on one body keep the HV clearance"] = (w_hv >= need - 1e-9, f"tightest {d_hv} (>= {_mm(need)})")
    # every sphere against the foils of the other nodes on its own body (the rotor halves co-rotate: one body)
    fbody = {it["id"]: BODY_OF[ROTOR_BODY.get(on[it["id"]], "stator")] for it in design["stack"] if it["kind"] == "foil"}
    w_sf, d_sf = float("inf"), "none"
    for it in sg["items"]:
        if it["kind"] != "sphere":
            continue
        for f in design["stack"]:
            if f["kind"] != "foil" or f["node"] == it["node"] or fbody[f["id"]] != BODY_OF[it["body"]]:
                continue
            dd = _foil_dist(it["c"], f) - it["r"]
            if dd < w_sf - 1e-9:
                w_sf, d_sf = dd, f"{it['name']} (node {it['node']}) / {f['id']} (node {f['node']}): {_mm(dd)} mm"
    res["spheres keep the HV clearance to different-node foils of their own body"] = (w_sf >= need - 1e-9, f"tightest {d_sf} (>= {_mm(need)})")
    # rotor and stator counter-rotate: every exposed conductor (sphere, stem, lead in air) against the copper and
    # foils of the other body at the closest approach any relative angle brings, i.e. their revolved (r, z) distance.
    # A band's tips (+ stems) against that band's stator spheres (+ stems) are the gaps themselves [OC geometry]
    w_rv, d_rv = _revolved_hv(design, sg, need, on)
    res["counter-rotating copper keeps the HV clearance (revolved, gap pairs aside)"] = (w_rv >= need - 1e-9, (
        f"tightest {d_rv} (>= {_mm(need)})" if w_rv < float("inf") else
        f"no exposed conductor comes within {_mm(need)} mm of the other body's copper"))
    res["leads near foils of other carriers (info: breakdown model out of scope)"] = (True, f"closest {d_oth}")
    nl = {c: sum(1 for it in sg["items"] if it["role"] == "link" and it["carrier"] == c) for c in LINKS}
    res["equipotential links and bus rings (info)"] = (True, ", ".join(f"{c} {n} x ({LINKS[c][0]} <-> {LINKS[c][1]})" for c, n in nl.items())
                                         + f"; {len(rings)} bus rings, one per node per carrier; ND2 / ND3 hold node 2 / 3 and pickup n23 / n17 "
                                           "(Lx4 / Lx3), the rotor discs R-A / R-B and the C_R plate n18 / n00 (L_R1 / L_R2): off-model")
    nr, ns, hits = sweep_check(design, sg)
    res["counter-rotation: no rotor/stator collision"] = (not hits, f"{nr} rotor x {ns} stator revolved envelopes, "
                                                          + (f"{len(hits)} overlap(s): {hits[0][0]} / {hits[0][1]}" if hits else "none overlap"))
    cross = [x for x in sg["gaps"] if x["crossover"]]
    res["load-gap crossovers over the stator (info)"] = (True, ", ".join(
        f"{x['name']}: node {x['stator_node']} from {x['carrier']} to {x['host']} ({x['side']}), lead {_mm(x['lead_len'])} mm"
        + (f" + arm {_mm(x['arm_len'])} mm" if x["mount"] == "arm" else "") for x in cross) or "none")
    # the spin load on the bar-band electrodes: radial stems (rim, arm) carry it along their axis, vertical stems in
    # bending [OC mechanics]; at the full relative speed, an upper bound for either counter-rotating body
    rpm = float(design["lock"].get("inputs", {}).get("rpm", 3000.0))
    bar = [b for b in sg["bands"].values() if b["band"] == "bar"]
    r_out = max(b["r_load"] for b in bar)
    acc = (2 * math.pi * rpm / 60.0) ** 2 * r_out * 1e-3 / 9.80665
    radial_bar = [b for b in bar if b["layout"] == "radial"]
    res["spin load on the bar-band electrodes (info)"] = (True, f"up to {_mm(acc)} g at r{_mm(r_out)} ({rpm:g} rpm, the full relative "
        "speed: an upper bound for either body): " + ("along the stem for the fire / backstop spheres (rim stems in tension) "
                                                     "and the load spheres (arms in compression: the sphere is at the inner end), "
                                                     "in bending for the tips on their short vertical stems" if radial_bar else
                                                     "every bar-band sphere and tip stands on a vertical stem: all in bending"))
    return {k: dict(pass_=bool(v[0]), detail=v[1]) for k, v in res.items()}


def _rz_img(it):
    """The revolved (r, z) image of a part: sample points along it with its radius (rod, sphere), or its (r, z) box
    (a sector set sweeps its full annulus under relative rotation)."""
    if it["kind"] == "sphere":
        return [(math.hypot(it["c"][0], it["c"][1]), it["c"][2])], it["r"], None
    if it["kind"] == "rod":
        p0, p1 = it["p0"], it["p1"]
        n = max(1, math.ceil(math.dist(p0, p1) / 2.0 - 1e-9))
        pts = []
        for j in range(n + 1):
            q = [p0[i] + (p1[i] - p0[i]) * j / n for i in range(3)]
            pts.append((math.hypot(q[0], q[1]), q[2]))
        return pts, it["r"], None
    return None, 0.0, (it["r_in"], it["r_out"], it["z0"], it["z1"])


def _revolved_hv(design, sg, need, on):
    """Tightest revolved (r, z) clearance between an exposed conductor of one body and any conductor or foil of a
    different node on the other body; the gap electrodes of one band against each other are left out."""
    elec = ("gap-stator", "gap-rotor", "gap-stem")
    expo = [it for it in sg["items"] if it["kind"] == "sphere" or (it["kind"] == "rod" and (
        it["role"] == "gap-stem" or (it["role"] == "gap-lead" and not it["embedded"] and not it.get("riser"))))]
    other = list(sg["items"]) + [dict(f, name=f["id"], role="foil", band="", body=ROTOR_BODY.get(on[f["id"]], "stator"))
                                 for f in design["stack"] if f["kind"] == "foil"]
    img = []
    for y in other:
        pts, inf_, box = _rz_img(y)
        if box is None:
            box = (min(p[0] for p in pts) - inf_, max(p[0] for p in pts) + inf_, min(p[1] for p in pts) - inf_, max(p[1] for p in pts) + inf_)
        img.append((pts, inf_, box))
    w, det = float("inf"), "none"
    for x in expo:
        px, ix, _ = _rz_img(x)
        bx = (min(p[0] for p in px) - ix, max(p[0] for p in px) + ix, min(p[1] for p in px) - ix, max(p[1] for p in px) + ix)
        for y, (py, iy, by) in zip(other, img):
            if BODY_OF[y["body"]] == BODY_OF[x["body"]] or y["node"] == x["node"]:
                continue
            if x["role"] in elec and y["role"] in elec and x["band"] == y["band"]:
                continue
            if max(bx[0] - by[1], by[0] - bx[1], bx[2] - by[3], by[2] - bx[3]) > need:
                continue
            if py is None:
                dd = min(math.hypot(max(0.0, by[0] - r, r - by[1]), max(0.0, by[2] - z, z - by[3])) for r, z in px) - ix
            else:
                dd = min(math.hypot(r1 - r2, z1 - z2) for r1, z1 in px for r2, z2 in py) - ix - iy
            if dd < w - 1e-9:
                w, det = dd, (f"{x['name']} (node {x['node']}, {BODY_OF[x['body']]}) / {y['name']} (node {y['node']}, "
                              f"{BODY_OF[y['body']]}): {_mm(dd)} mm")
    return w, det


def parts(design):
    """The bill of solids. CAD groups are ELECTRICAL: every conductor sits in the group of its node ("node-2 - Node 2
    ..."), the insulators in "carriers" and "dielectrics"; where a conductor is mounted is said in its label. Every
    label is "<group> / <name> - <description> [<material>, <body>]" and states its own node first, so a STEP
    re-read (sim/circuit_integrity.py) recovers node, material and body from the name alone."""
    st = design["stack"]; fp = design["footprints"]
    asm, out = [], []

    def assembly(key, label):
        if not any(a["key"] == key for a in asm):
            asm.append(dict(key=key, label=label))
        return key

    def node_group(node):
        return assembly(f"node-{node}", f"node-{node} - Node {node}: {NODE_DESC.get(node, '')}")
    carrier_of, face_of = {}, {}
    for i, it in enumerate(st):
        if it["kind"] != "foil":
            continue
        nb = [st[j] for j in (i - 1, i + 1) if 0 <= j < len(st) and st[j]["kind"] in CARRIER_KINDS]
        carrier_of[it["id"]] = nb[0]["id"] if nb else "foils"
        face_of[it["id"]] = "septum side" if nb and abs(it["z0"]) < abs(nb[0]["z0"]) else "outer side"

    def P(name, desc, akey, role, carrier, node, cap, material, body, rin, rout, a0, w, z0, z1, rgb):
        out.append(dict(name=name, label=f"{akey} / {name} - {desc} [{material}, {body}]", assembly=akey, role=role,
                        carrier=carrier, node=node, cap=cap, material=material, body=body, shape="sector",
                        chains=[carrier or akey], r_in=rin, r_out=rout, start_deg=a0, w_deg=w, z0=z0, z1=z1, rgb=list(rgb),
                        volume=0.5 * math.radians(min(w, 360.0)) * (rout * rout - rin * rin) * (z1 - z0)))
    diel = "dielectrics"
    for it in st:
        kind = it["kind"]
        if kind in CARRIER_KINDS:
            a = assembly("carriers", "carriers - the insulating carrier discs (G10); no node")
            body = ROTOR_BODY.get(it["id"], "stator")
            rings = _carrier_rings(it, (design.get("sparkgaps") or {}).get("recesses", []))
            for ri, (r0, r1, z0, z1) in enumerate(rings):
                thin = abs((z1 - z0) - it["t"]) > 1e-9
                P(it["id"].replace("-", "_") + "_carrier" + (f"_{ri + 1}" if len(rings) > 1 else ""),
                  f"{it['id']} carrier{(' ring ' + str(ri + 1) + ' of ' + str(len(rings))) if len(rings) > 1 else ''}, "
                  f"insulating: {CARRIER_ROLE.get(it['id'], kind)}; r{_mm(r0)}-{_mm(r1)} mm, {_mm(z1 - z0)} mm thick"
                  f"{' (recessed spark-gap band)' if thin else ''}, z {_mm(z0)}..{_mm(z1)}",
                  a, "carrier", it["id"], "", "", MATERIAL[kind], body, r0, r1, 0.0, 360.0, z0, z1, CARRIER_RGB)
        elif kind == "foil":
            car = carrier_of[it["id"]]
            a = node_group(it["node"])
            body = ROTOR_BODY.get(car, "stator")
            n = len(it["starts"])
            for k, s0 in enumerate(it["starts"]):
                if it["w_deg"] >= 360.0 - 1e-9:
                    ang = "full ring"
                else:
                    e = _m360(s0 + it["w_deg"])
                    ang = f"sector {k + 1} of {n} ({_mm(_m360(s0))}-{_mm(e if e != 0 else 360.0)} deg)"
                P(f"{it['key']}_{k + 1}",
                  f"{it['name']}, node {it['node']}, {it['cap']}, {ang}, r{_mm(it['r_in'])}-{_mm(it['r_out'])} mm, "
                  f"Al foil {_mm(it['z1'] - it['z0'])} mm, {face_of[it['id']]} of {car}, {_zr(it)}",
                  a, "foil", car, it["node"], it["cap"], "Al foil", body, it["r_in"], it["r_out"], s0, it["w_deg"],
                  it["z0"], it["z1"], node_rgb(it["node"]))
        elif kind == "gap" and it.get("medium") in MEDIUM_RGB:
            a = assembly(diel, "dielectrics - septum (C_R, garolite), the Ca / Cb mica slabs and the Cx mica facings; no node")
            if it.get("footprint"):
                e = fp[it["footprint"]]; m = it.get("margin", 0.0)
                rin, rout = max(0.0, e["r_in"] - m), e["r_out"] + m
                dw = math.degrees(m / max(e["r_in"], 1e-9))
                n = len(e["starts"])
                for k, s0 in enumerate(e["starts"]):
                    w = min(e["w_deg"] + 2 * dw, 360.0); a0 = s0 - dw
                    P(f"{it['id'].replace('-', '_')}_{k + 1}",
                      f"{it['id']}_{k + 1}, {it['medium']} dielectric for {it['cap']} (between the {it['cap']} electrode "
                      f"and its counter), slab {k + 1} of {n} ({_mm(_m360(a0))}-{_mm(_m360(a0 + w))} deg), "
                      f"r{_mm(rin)}-{_mm(rout)} mm, {_mm(it['t'])} mm thick (foil + {_mm(m)} mm margin), {_zr(it)}",
                      a, "dielectric", "", "", it["cap"], it["medium"], "stator", rin, rout, a0, w, it["z0"], it["z1"],
                      MEDIUM_RGB[it["medium"]])
            else:
                rin, rout = it.get("r_in", 0.0), it.get("r_out", design["r_edge"])
                P(it["id"].replace("-", "_"),
                  f"{it['id']}, {it['medium']}, {it['cap']} dielectric between rotor A and rotor B, "
                  f"r{_mm(rin)}-{_mm(rout)} mm, {_mm(it['t'])} mm thick, {_zr(it)}",
                  a, "dielectric", "", "", it["cap"], it["medium"], "rotor AB", rin, rout, 0.0, 360.0, it["z0"], it["z1"],
                  MEDIUM_RGB[it["medium"]])
    for x in cx_facings(design):
        a = assembly(diel, "dielectrics - septum (C_R, garolite), the Ca / Cb mica slabs and the Cx mica facings; no node")
        P(x["name"], f"{x['cap']} mica facing on {x['foil']} ({x['carrier']}), r{_mm(x['r_in'])}-{_mm(x['r_out'])} mm, "
                     f"{_mm(x['z1'] - x['z0'])} mm, z {_mm(x['z0'])}..{_mm(x['z1'])}",
          a, "dielectric", x["carrier"], "", x["cap"], "mica", x["body"], x["r_in"], x["r_out"], x["start_deg"], x["w_deg"],
          x["z0"], x["z1"], MEDIUM_RGB["mica"])
    sgp = design.get("sparkgaps")
    if sgp:
        for it in sgp["items"]:
            # electrical grouping: the part's node; where it is mounted is in its label
            akey = node_group(it["node"])
            if it["kind"] == "sector":
                mat = "Cu bus"
            elif it["kind"] == "sphere":
                mat = "W-Cu sphere" if it["r"] <= 6.0 + 1e-9 else "polished sphere"
            else:
                mat = {"link": "Cu link", "gap-stem": "Cu stem", "bus": "Cu bus"}.get(it["role"], "Cu lead")
            base = dict(name=it["name"], label=f"{akey} / {it['name']} - {it['desc']}, in {it['carrier']} [{mat}, {it['body']}]",
                        assembly=akey, role=it["role"], carrier=it["carrier"], node=it["node"], cap=it["gap"], material=mat,
                        body=it["body"], rgb=list(node_rgb(it["node"])), chains=list(it["chains"]))
            if it["kind"] == "sector":
                base.update(shape="sector", r_in=it["r_in"], r_out=it["r_out"], start_deg=it["start_deg"],
                            w_deg=it["w_deg"], z0=it["z0"], z1=it["z1"],
                            volume=0.5 * math.radians(it["w_deg"]) * (it["r_out"] ** 2 - it["r_in"] ** 2) * (it["z1"] - it["z0"]))
            elif it["kind"] == "sphere":
                base.update(shape="sphere", c=list(it["c"]), r=it["r"], volume=4.0 / 3.0 * math.pi * it["r"] ** 3)
            else:
                L = math.dist(it["p0"], it["p1"])
                base.update(shape="rod", p0=list(it["p0"]), p1=list(it["p1"]), r=it["r"], volume=math.pi * it["r"] ** 2 * L)
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
CR_RATIO = 2.82                             # C_R / C_max, = pump_sizing ratio_CR (tank collapsed) [IR]


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
        res[f"{cap}: inset from its counter-electrode edge by the margin"] = (
            e["r_out"] <= c["r_out"] - g["ca_margin"] + 1e-9 and e["r_in"] >= c["r_in"] + g["ca_margin"] - 1e-9,
            f"r{e['r_in']:.1f}-{e['r_out']:.1f} within r{c['r_in']:.0f}-{c['r_out']:.0f} less {g['ca_margin']:.0f} mm")
        res[f"{cap}: clears the carrier bore"] = (e["r_in"] - g["ca_margin"] >= g["r_bore"],
                                                  f"r_in {e['r_in']:.1f} - margin {g['ca_margin']:.0f} >= bore {g['r_bore']:.0f}")
        res[f"{cap}: dielectric margin fits the sector pitch"] = (
            e["w_deg"] + 2 * math.degrees(g["ca_margin"] / max(e["r_in"], 1e-9)) <= 360.0 / (len(e["starts"]) or 1),
            f"foil {e['w_deg']:.1f} deg + 2 x {g['ca_margin']:.0f} mm margin at r_in")
        res[f"{cap}: realized C = locked C"] = (abs(geo["dC_rel"]) <= 1e-9 or g["ca_round"] > 0,
                                                f"{geo['C_pF']:.3f} vs {geo['C_target_pF']:.3f} pF ({_pct(geo['dC_rel']):+.4f} %)"
                                                + (" -- rounding: engine round-trip decides" if g["ca_round"] > 0 else ""))
    # C_R (tank, collapsed in the engine): through the septum vs the ladder's 2.82 x C_max (pump_sizing D default);
    # 1 % tolerance, the host's hub-ring term is not drawn here [IR]
    cr_t = CR_RATIO * design["lock"]["ladder"]["C_max"]
    cr = cap_pF(overlap_area(fp["CR_A"], fp["CR_B"]), g["t_septum"], DIELECTRICS["garolite"])
    res["C_R: septum C = 2.82 x C_max (tank, shown only)"] = (abs(cr / cr_t - 1) <= 0.01,
        f"{cr:.1f} vs {cr_t:.1f} pF ({_pct(cr / cr_t - 1):+.2f} %), {len(fp['CR_A']['starts'])} x {fp['CR_A']['w_deg']:.0f} deg on {g['t_septum']:.1f} mm garolite")
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
    # the radial bar band (default): load gaps horizontal, every other gap vertical; ND2 / ND3 trimmed; the axial
    # layout still builds clean
    ax = {x["name"]: x["gap_axis"] for x in d["sparkgaps"]["gaps"]}
    ok &= all((ax[n] == "horizontal") == (n in ("SG3a1", "SG4a1")) for n in ax)
    ok &= all(it["r_out"] < d["r_edge"] - 1e-9 for it in d["stack"] if it["id"] in RIM_FOILS)
    ok &= all(v["pass_"] for v in build(rec, dict(sg_layout="axial"))["checks"].values())
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
