#!/usr/bin/env python3
"""sim/rotor_parts_drive.py -- the magnetic pump's parts that drive the AH, placed on the rotor, and the bevel reverser
with its belt drive re-cut onto the layout's side A end (PROPOSED, 2026-10-12; the places are the designer's to decide).

  * The parts (sim/parts-first-cut-findings.md, their first cuts; sim/unmodelled_parts.py, their solids): La / Lb, the
    Schottky rectifiers D1*-D4*, the eight node snubbers, the two AH bypass capacitors and the K4 start kick. They go in
    the reluctance bays' three free wedges between the utrons (at 60, 180 and 300 deg; the utrons at 0, 120, 240), each
    wedge a G10 cradle between the bay's two carrier discs: two end plates bolted to the discs' inboard faces, a
    backplate across the wedge's outer end that takes the parts' centrifugal load. Side A: S1 La; S2 D1*, D3*, the
    snubbers at a, d, x1, f2 and bypass A; S3 the K4 kick. Side B the same turned over (S1 Lb; S2 D2*, D4*, the snubbers
    at b, c, x2, f3 and bypass B; S3 ballast only). S2 and S3 carry brass ballast so that each wedge's m r (and its m r z)
    equals the choke wedge's: each side then balances on its own, and the rotor has no couple [IR].
  * Two LV leads cross the hub: b (AH_B's finish) to bay A for D1* / D4*, d (AH_A's finish) to bay B for D2*. Each runs
    in a groove in both flanges' inboard faces, through the coupler's wall, along the coupler at r 39 (the ring leads
    run at r 36 on the far side), from bore to bore [IR].
  * The drive (docs/drive-gear-belt.md §5-§8, as drawn by sim/unmodelled_parts.py) moved up by 30.5 mm, so that its
    gear-end bearing lands on the layout's bridge-ring bearing A (z 22.5-37.5): that bearing and its cartridge now take
    the first cut's gear-end bearing, the counter-rotor's hub and its end disc (dropped); the counter-rotor's side gear
    bolts by its back flange under the cartridge; the case loses its lip (cut at z 22.5, under the spider); the layout's
    frame end bearing A and its spider go, the locating bearing in the case floor takes their place; the collar sits on
    the bearing's inner ring, the reluctance sleeve shortened to start above it; the shaft runs on to its drive end.
Every number is read from the studies' results or set here and tagged: [OC] arithmetic, [IR] a modelling choice, [RH] a
placeholder. LayoutMachine (sim/tube_geometry.py) builds the parts from this module when asked
(LayoutMachine(pump_parts=True, drive=True); python3 sim/tube_geometry.py --layout --full).
Checks: no part overlaps any other; every part that turns against another keeps clear of it at every relative angle
(the bodies sampled every 6 deg, refined to 1 deg); the balance; the centrifugal loads; the cross leads' field [RH].
Writes sim/rotor_parts_drive_results.json and docs/figures/rotor-parts-drive.png.
Usage: python3 sim/rotor_parts_drive.py   (about two minutes; OCP)
"""
import json
import math
import os
import sys
import time

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
import tube_geometry as TG                                                   # noqa: E402
import unmodelled_parts as UP                                                # noqa: E402

OUT = os.path.join(HERE, "rotor_parts_drive_results.json")
FIG = os.path.join(ROOT, "docs", "figures", "rotor-parts-drive.png")
box, ring, apply, frame, rot_z, cut, fuse = UP.box, UP.ring, UP.apply, UP.frame, UP.rot_z, UP.cut, UP.fuse
COL = UP.COL

RPM, RPM_CHECK = 600.0, 750.0       # each body (DCCREG-design-ledger.md §3.1); the rotor-mechanics check speed
#                                     (sim/rotor-mechanics-findings.md: "at 750 rpm every part holds")
RHO = dict(UP.RHO, brass=8500.0, silicone=1100.0, pa=1200.0)     # kg/m3 [IR: handbook values]
ROTOR_KG = 33.8                     # the layout's rotor (DCCREG-design-ledger.md §6, item 70, corrected)
G25_N = 2.5                         # balance grade G2.5 per body (DCCREG-design-ledger.md §3.6)

# ---------------------------------------------------------------------------------------------------------------------
# the bays (side A; side B is side A turned over about each wedge's radial axis through the hub's centre)
# ---------------------------------------------------------------------------------------------------------------------
UTRONS = (0.0, 120.0, 240.0)        # the utrons' angles, both sides (sim/tube_geometry.py LayoutMachine el, 'w utron')
SECTORS = {"S1": 60.0, "S2": 180.0, "S3": 300.0}   # the free wedges' bisectors [OC: between the utrons]
DISC_Z = (61.0, 181.0)              # the carrier discs' inboard faces, side A (the 'w disc' elements: z 49-61, 181-193)
END_T = 6.0                         # the cradle's G10 end plates [RH]
R_END = (22.5, 122.0)               # their radii: 2 mm off the sleeve (r 20.5); out to the backplate's corners [IR]
BAND = (40.0, 32.0)                 # each end plate keeps out of the utron's band (|y| <= 29 from x 43: its cheeks,
#                                     z 61-71 and 171-181) by 3 mm [IR]
BACK = dict(u=(110.0, 116.0), v=32.0, z=(DISC_Z[0] + END_T, DISC_Z[1] - END_T))   # the G10 backplate: r 120 at its
#                                     corners, 10 mm inside the bridges (r 130.5) [IR]
BAL = dict(v=27.0, z=102.0)         # the brass ballast's half width and length, on the backplate's inner face [IR]
BOARD_T = 3.0                       # the G10 board the S2 / S3 parts sit on, on the ballast [IR]
CHOKE_U0 = 26.0                     # La / Lb: the E's outer legs flat on the backplate (x 84 radial, u 26-110), the stack
#                                     tangential, the legs axial (y 70, z 86-156) [IR]
LEAD_UP = 4.0                       # an axial part's leads: 4 mm straight, then bent down through the board [IR]

# the parts' masses: the choke's is its first cut's; the bought parts' [RH] (the makers' class), the made parts' from
# their solids
M_BOUGHT = dict(diode=0.0011, r76=0.0025, ox=0.0010, snap=0.032, cell=0.036, k_cap=0.006, k_scr=0.0003, k_res=0.0003,
                k_reed=0.002, k_link=0.001, k_holder=0.008)
CHOKE_KG = UP.CH["m_with_bobbin_kg"]                  # 1.665 (sim/parts_first_cut_results.json la_lb.chosen)

# ---------------------------------------------------------------------------------------------------------------------
# the cross-hub leads and the drive's re-cut
# ---------------------------------------------------------------------------------------------------------------------
CROSS = dict(b=dict(theta=-10.0, to="A", what="b, AH_B's finish, to bay A (D1*, D4*)"),
             d=dict(theta=-30.0, to="B", what="d, AH_A's finish, to bay B (D2*)"))   # [IR: the angles, far from the
#                                     rings' leads at 150-175 deg]
CROSS_R, CROSS_WIRE_R, GROOVE = 39.0, 1.25, (3.0, 3.0)   # the run's radius (coupler r 33, can r 46), the lead's radius
#                                     (2.5 mm over its insulation) [RH], the flanges' grooves (width, depth) [IR]
DZ_DRIVE = 30.5                     # the first cut's gear-end bearing (z -8..7) onto the bridge-ring bearing (22.5-37.5)
SHAFT_A_Z0 = -133.0 + DZ_DRIVE      # the shaft's drive end, under the lock nut (sim/unmodelled_parts.py reverser_sub)
SLEEVE_A_Z0 = 17.0 + DZ_DRIVE       # the reluctance sleeve starts on the collar (collar z 7-17 in the first cut)
CASE_TOP = -8.0 + DZ_DRIVE          # the case cut under the bridge-ring spider (z 26): its lip goes
DROP_LAYOUT = ("A_bearing_end", "A_spider_end")       # the layout's frame end bearing A and its spider
DROP_DRIVE = ("shaft", "bearing_gear_end", "hub", "end_disc")   # the first cut's parts the layout already carries or loses


def _u(th):
    t = math.radians(th)
    return np.array([math.cos(t), math.sin(t), 0.0])


def bay_T(phi, side, zc):
    """the wedge at phi: its own x radial (u), y tangential (v), z along the axis; side B turned over about u through
    the hub's centre zc (v -> -v, z -> 2 zc - z) [IR]."""
    u, v = _u(phi), _u(phi + 90.0)
    if side == "A":
        return frame(u, v, (0, 0, 1))
    return frame(u, -v, (0, 0, -1), (0, 0, 2.0 * zc))


def on_board(u_f, v0, z0, deg=0.0):
    """a part standing on a board whose face is at u_f (facing the axis): the part's x along the machine's axis, its y
    tangential, its z up off the board (toward the axis), at (v0, z0) on the board; turned deg about its own z."""
    c, s = math.cos(math.radians(deg)), math.sin(math.radians(deg))
    X = (-0.0, s, c)                    # the part's x: axial, turned toward v by deg
    Y = (0.0, c, -s)
    return frame(X, Y, (-1.0, 0.0, 0.0), (u_f, v0, z0))


# ---------------------------------------------------------------------------------------------------------------------
# parts in their own frames (a board's face at z = 0, the part above it)
# ---------------------------------------------------------------------------------------------------------------------
def axial_part(D, L, d, lead=LEAD_UP, into=BOARD_T):
    """an axial part lying on the board (its body 0.5 mm off it), leads straight out lead mm and bent down through the
    board [IR]: x along its axis, centred."""
    from OCP.BRepPrimAPI import BRepPrimAPI_MakeCylinder
    from OCP.gp import gp_Ax2, gp_Pnt, gp_Dir
    h = 0.5 * D + 0.5
    ax = lambda x0, r, l: BRepPrimAPI_MakeCylinder(gp_Ax2(gp_Pnt(x0, 0, h), gp_Dir(1, 0, 0)), r, l).Shape()
    half = 0.5 * L
    xs = half + lead
    legs = [UP.cyl_z(sx * xs, 0.0, 0.5 * d, -into, h + 0.5 * d) for sx in (-1, 1)]
    return fuse([ax(-half, 0.5 * D, L), ax(-xs, 0.5 * d, xs - half + 0.01), ax(half - 0.01, 0.5 * d, xs - half + 0.01)] + legs)


def r76_part(into=BOARD_T):
    """the snubber's KEMET R76 box standing on the board, its two leads through it (10 mm pitch along x)."""
    c = UP.R76
    return fuse([box(-0.5 * c["L"], 0.5 * c["L"], -0.5 * c["W"], 0.5 * c["W"], 0.0, c["H"])] +
                [UP.cyl_z(sx * 0.5 * c["pitch"], 0.0, 0.5 * c["d"], -into, 0.01) for sx in (-1, 1)])


def snap_part(into=BOARD_T):
    """the bypass capacitor standing on the board, its snap-in pins cut to the board [IR]."""
    q = UP.SNAP
    can = fuse([UP.cyl_z(0, 0, 0.5 * q["D"], 0.0, q["H"]), UP.cyl_z(0, 0, 0.5 * q["D"] - 1.5, q["H"], q["H"] + 0.6)])
    pins = [box(sx * 0.5 * q["pitch"] - 0.5 * q["pin_w"], sx * 0.5 * q["pitch"] + 0.5 * q["pin_w"], -0.5 * q["pin_t"],
                0.5 * q["pin_t"], -into, 0.01) for sx in (-1, 1)]
    return fuse([can] + pins)


def end_plate():
    """a cradle's end plate in the wedge's frame: the 120 deg sector r 22.5-122, flat at the backplate's outer face,
    clear of both neighbouring utrons' bands; z 0..END_T."""
    s = UP.common(TG.sector(R_END[0], R_END[1], 0.0, END_T, -60.0, 120.0), box(0.0, BACK["u"][1], -130, 130, -1, END_T + 1))
    bands = [apply(box(BAND[0], 220.0, -BAND[1], BAND[1], -1.0, END_T + 1.0), rot_z(a)) for a in (-60.0, 60.0)]
    return cut(s, *bands)


# ---------------------------------------------------------------------------------------------------------------------
# the parts of one side's three wedges
# ---------------------------------------------------------------------------------------------------------------------
NODES = {"A": ("a", "d", "x1", "f2"), "B": ("b", "c", "x2", "f3")}     # the snubbers' nodes (sim/parts-first-cut-findings.md §2)
DIODES = {"A": ("D1*", "D3*"), "B": ("D2*", "D4*")}


def _spec(name, shape, colour, material, body, group, join, desc, mass, kind="made", net=None):
    return dict(name=name, shape=shape, colour=colour, material=material, body=body, group=group, join=join, desc=desc,
                mass_kg=mass, kind=kind, net=net)


def _mass(shape, rho):
    return UP.volume(shape) * 1e-9 * rho


def sector_parts(side, key, t_bal=None, v_bal=0.0, z_bal=None, zc=507.0):
    """the parts of wedge key on side (in the machine's frame): its cradle, and S1 the choke; S2 the rectifiers, the
    snubbers and the bypass capacitor on a board on the ballast; S3 the kick (side A) on a board on the ballast, or the
    ballast alone (side B). t_bal, v_bal, z_bal: the ballast's thickness, tangential offset and axial centre (side A's z)."""
    phi = SECTORS[key]
    T = bay_T(phi, side, zc)
    P = lambda s, t=None: apply(s if t is None else apply(s, t), T)
    grp, out = f"pump-{side}", []
    pre = f"{side}_{key}"
    jn = f"cradle-{side}-{key}"
    # the cradle
    ep = end_plate()
    for nm, z0 in (("end_plate_lo", DISC_Z[0]), ("end_plate_hi", DISC_Z[1] - END_T)):
        s = P(ep, rot_z(0.0, dz=z0))
        out.append(_spec(f"{pre}_{nm}", s, COL["g10"], "G10, 6 mm, bolted to the carrier disc", "rotor", grp, jn,
                         f"the {key} cradle's end plate, on the carrier disc's inboard face", _mass(s, RHO["g10"])))
    bk = P(box(BACK["u"][0], BACK["u"][1], -BACK["v"], BACK["v"], BACK["z"][0], BACK["z"][1]))
    out.append(_spec(f"{pre}_backplate", bk, COL["g10"], "G10, 6 mm, the cradle's backplate", "rotor", grp, jn,
                     f"the {key} cradle's backplate: takes the parts' centrifugal load into the end plates",
                     _mass(bk, RHO["g10"])))
    u_f = BACK["u"][0]                                  # the face the parts (or the ballast) sit on
    if key == "S1":
        C = UP.choke_sub()
        Tc = frame((1, 0, 0), (0, 0, 1), (0, -1, 0), (CHOKE_U0, 0.5 * UP.CH_S, 86.0))
        nm_c = "La" if side == "A" else "Lb"
        vols = {p["name"]: UP.volume(C.placed(p, True)) for p in C.parts}
        rho = dict(E_stack=1.0, I_stack=1.0)
        v_fe = vols["E_stack"] + vols["I_stack"]
        m_fe, m_cu = UP.CH["m_fe_kg"], UP.CH["m_cu_kg"]
        m_rest = CHOKE_KG - m_fe - m_cu
        v_rest = sum(v for k, v in vols.items() if k not in ("E_stack", "I_stack", "winding") and not k.startswith("lead"))
        for p in C.parts:
            n = p["name"]
            if n.startswith("lead"):
                continue                                # the leads go to the harness (not drawn)
            s = P(C.placed(p, True), Tc)
            m = (m_fe * vols[n] / v_fe if n in rho else m_cu if n == "winding" else m_rest * vols[n] / v_rest)
            out.append(_spec(f"{pre}_{nm_c}_{n}", s, C.protos[p["proto"]][1], C.protos[p["proto"]][2], "rotor", grp,
                             f"choke-{side}", f"{nm_c}, EI-84 x 35: {n.replace('_', ' ')}", m, kind="choke",
                             net="lv"))
        return out
    has_board = not (side == "B" and key == "S3")
    if t_bal is None:
        t_bal = 20.0
    zb = 0.5 * (BACK["z"][0] + BACK["z"][1]) if z_bal is None else z_bal
    bl = P(box(u_f - t_bal, u_f, v_bal - BAL["v"], v_bal + BAL["v"], zb - 0.5 * BAL["z"], zb + 0.5 * BAL["z"]))
    out.append(_spec(f"{pre}_ballast", bl, COL["brass"], f"brass CuZn39Pb3 ballast, {t_bal:.1f} mm (non-magnetic)", "rotor",
                     grp, jn, f"the {key} wedge's ballast: its m r and m r z the choke wedge's", _mass(bl, RHO["brass"]),
                     kind="ballast"))
    if not has_board:
        return out
    ub = u_f - t_bal
    bd = P(box(ub - BOARD_T, ub, -30.0, 30.0, 70.0, 172.0))
    i_board = len(out)
    out.append(_spec(f"{pre}_board", bd, COL["g10"], "G10 board, 3 mm, drilled for the parts' leads", "rotor", grp, jn,
                     f"the {key} wedge's board, on the ballast", 0.0))
    face = ub - BOARD_T
    jp = f"board-{side}-{key}"
    if key == "S2":
        cp = P(snap_part(), on_board(face, -14.0, 88.0))
        out.append(_spec(f"{pre}_bypass_{side}", cp, COL["blue"], "Rubycon 10MXG22000MEFCSN30X30, 22 000 uF 10 V snap-in",
                         "rotor", grp, jp, f"the AH bypass capacitor, side {side}", M_BOUGHT["snap"], kind="bought",
                         net="lv"))
        for j, (vv, dn) in enumerate(((9.0, DIODES[side][0]), (21.0, DIODES[side][1]))):
            q = UP.DO201AD
            s = P(axial_part(q["D"], q["L"], q["d"]), on_board(face, vv, 88.0))
            out.append(_spec(f"{pre}_{dn.replace('*', 's')}", s, COL["black"], "Schottky rectifier, DO-201AD (SB5200 / SR5150 class)",
                             "rotor", grp, jp, f"{dn}, the magnetic pump's rectifier", M_BOUGHT["diode"], kind="bought",
                             net="lv"))
        for j, (zz, vv) in enumerate(((122.0, -25.5), (122.0, 5.0), (156.0, -25.5), (156.0, 5.0))):
            nd = NODES[side][j]
            c = P(r76_part(), on_board(face, vv, zz))
            q = UP.OX
            r = P(apply(axial_part(q["D"], q["L"], q["d"], lead=3.0), rot_z(0.0, dy=10.0)), on_board(face, vv, zz))
            out.append(_spec(f"{pre}_snubber_{nd}_C", c, COL["film"], "KEMET R76 22 nF 400 V, the snubber's capacitor",
                             "rotor", grp, jp, f"the snubber at node {nd}: its capacitor", M_BOUGHT["r76"], kind="bought",
                             net="lv"))
            out.append(_spec(f"{pre}_snubber_{nd}_R", r, COL["brown"], "Ohmite OX221KE 220 ohm, the snubber's resistor",
                             "rotor", grp, jp, f"the snubber at node {nd}: its resistor", M_BOUGHT["ox"], kind="bought",
                             net="lv"))
        return _drill(out, i_board)
    # S3 side A: the K4 kick, its base on the board (x axial, y tangential)
    K = UP.kick_sub()
    Tk = on_board(face, 0.0, 121.0).Multiplied(rot_z(0.0, dx=-50.0, dy=-30.0))
    mk = dict(k_base=None, k_pcb=None, k_pot=RHO["silicone"], k_holder=None, k_cell=None, k_cap=None, k_scr=None,
              k_res=None, k_reed=None, k_link=None)
    for p in K.parts:
        s = P(K.placed(p, True), Tk)
        k = p["proto"]
        if k in ("k_base", "k_pcb"):
            m = _mass(s, RHO["g10"])
        elif k == "k_pot":
            m = _mass(s, RHO["silicone"])
        else:
            m = M_BOUGHT[{"k_cell": "cell", "k_holder": "k_holder"}.get(k, k)]
        out.append(_spec(f"{pre}_K4_{p['name']}", s, K.protos[k][1], K.protos[k][2], "rotor", grp, "kick-A",
                         f"the K4 kick: {p['name'].replace('_', ' ')}", m, kind="bought" if mk[k] is None and k not in
                         ("k_base", "k_pcb") else "made", net="lv"))
    return _drill(out, i_board)


def _drill(out, i):
    """the board drilled where the parts on it pass through it (their leads, pins and the kick's base screws)."""
    b = out[i]
    s = b["shape"]
    lo, hi = UP.bbox(s)
    for q in out[i + 1:]:
        ql, qh = UP.bbox(q["shape"])
        if all(ql[k] < hi[k] and qh[k] > lo[k] for k in range(3)):
            s = cut(s, q["shape"])
    b["shape"], b["mass_kg"] = s, _mass(s, RHO["g10"])
    return out


def moments(specs, phi, side, zc):
    """a wedge's m, m u, m v and m u z (u, v in its own frame, z on side A's axis), from its parts' solids' centroids."""
    from OCP.BRepGProp import BRepGProp
    from OCP.GProp import GProp_GProps
    u, v = _u(phi), _u(phi + 90.0)
    sv = 1.0 if side == "A" else -1.0
    M = dict(m=0.0, mu=0.0, mv=0.0, muz=0.0)
    for q in specs:
        g = GProp_GProps(); BRepGProp.VolumeProperties_s(q["shape"], g)
        c = g.CentreOfMass()
        p = np.array([c.X(), c.Y(), c.Z()])
        pu, pv = float(p @ u), sv * float(p @ v)
        pz = p[2] if side == "A" else 2.0 * zc - p[2]
        m = q["mass_kg"]
        q["cg"] = [round(float(x), 2) for x in p]
        M["m"] += m; M["mu"] += m * pu; M["mv"] += m * pv; M["muz"] += m * pu * pz
    return M


def balanced(side, zc=507.0, log=print):
    """each side's three wedges, the ballast of S2 / S3 solved so that every wedge has the choke wedge's m u, m v and
    m u z [OC: three equal moments at 120 deg sum to zero; their equal axial lever leaves no couple]."""
    s1 = sector_parts(side, "S1", zc=zc)
    M1 = moments(s1, SECTORS["S1"], side, zc)
    z1 = M1["muz"] / M1["mu"]
    out, rows = {"S1": s1}, {"S1": dict(M1, z_lever=z1)}
    A = 2.0 * BAL["v"] * BAL["z"]
    for key in ("S2", "S3"):
        t, vb, zb = 20.0, 0.0, None
        for it in range(30):
            sp = sector_parts(side, key, t, vb, zb, zc)
            rest = [q for q in sp if q["kind"] != "ballast"]
            Mr = moments(rest, SECTORS[key], side, zc)
            # brass: m_b = rho A t at u_b = u_f - t / 2  ->  rho A (u_f t - t^2 / 2) = M1 mu - Mr mu
            k = RHO["brass"] * 1e-9 * A
            need = M1["mu"] - Mr["mu"]
            uf = BACK["u"][0]
            t_new = uf - math.sqrt(max(uf * uf - 2.0 * need / k, 0.0))
            mb, ub = k * t_new, uf - 0.5 * t_new
            vb_new = (M1["mv"] - Mr["mv"]) / mb
            zb_new = (M1["muz"] - Mr["muz"]) / (mb * ub)
            zb_new = zb_new if side == "A" else zb_new           # z on side A's axis either way
            done = abs(t_new - t) < 1e-4 and abs(vb_new - vb) < 1e-4 and (zb is not None and abs(zb_new - zb) < 1e-4)
            t, vb, zb = t_new, vb_new, zb_new
            if done:
                break
        sp = sector_parts(side, key, t, vb, zb, zc)
        Mk = moments(sp, SECTORS[key], side, zc)
        out[key] = sp
        rows[key] = dict(Mk, z_lever=Mk["muz"] / Mk["mu"], ballast_t_mm=t, ballast_v_mm=vb, ballast_zc_mm=zb,
                         ballast_kg=RHO["brass"] * 1e-9 * A * t, iterations=it + 1)
        log(f"  side {side} {key}: ballast {t:.2f} mm ({rows[key]['ballast_kg']:.3f} kg), v {vb:+.2f}, z {zb:.2f}")
    return out, rows


def harness(side, zc, ze):
    """the bay's harness: from the LV cable's radial exit (r 24 at 0 deg, z ze) round the sleeve at r 30 above the outer
    carrier disc, out along each wedge's bisector to r 62, down outside the disc to the cradle's end plate (through its
    grommet, not drawn) [IR]."""
    out = []
    zh = DISC_Z[1] + 2.0                                          # 0.5 over the end plate's outer face (z 181)
    for key, phi in SECTORS.items():
        a1 = phi if phi <= 180.0 else phi - 360.0
        n = max(2, int(abs(a1) / 15.0) + 1)
        arc = [tuple(30.0 * _u(a1 * j / (n - 1))[:2]) for j in range(n)]
        pts = [(24.0, 0.0, ze)] + [(x, y, ze) for x, y in arc] + [tuple(62.0 * _u(a1)[:2]) + (ze,),
                                                                     tuple(62.0 * _u(a1)[:2]) + (zh,)]
        if side == "B":
            pts = [(x, y, 2.0 * zc - z) for x, y, z in pts]
        out.append(dict(name=f"{side}_{key}_harness", pts=pts))
    return out


def cross_leads(zc, fl_h0, fl_t):
    """the cross-hub leads' paths: in the flanges' inboard grooves, through the coupler, along it at r 39."""
    zA, zB = zc - fl_h0 - 0.5 * GROOVE[1], zc + fl_h0 + 0.5 * GROOVE[1]
    out = []
    for k, q in CROSS.items():
        u = _u(q["theta"])
        P = [tuple(3.75 * u[:2]) + (zB,), tuple(CROSS_R * u[:2]) + (zB,), tuple(CROSS_R * u[:2]) + (zA,),
             tuple(3.75 * u[:2]) + (zA,)]
        out.append(dict(name=f"lv_cross_{k}", pts=P, theta=q["theta"], what=q["what"], z=(zA, zB)))
    return out


def flange_grooves(side, fl_t, r1):
    """the grooves in a flange's inboard face (its local z: side A's at z = fl_t, side B's at 0), one per cross lead."""
    w, dpt = GROOVE
    z0, z1 = (fl_t - dpt, fl_t + 1.0) if side == "A" else (-1.0, dpt)
    return [apply(box(-1.0, r1 + 1.0, -0.5 * w, 0.5 * w, z0, z1), rot_z(q["theta"])) for q in CROSS.values()]


def coupler_holes(fl_h0):
    """the coupler's holes for the cross leads (in the hub's frame, z from its centre): r 1.6 radial through the wall."""
    zr = fl_h0 + 0.5 * GROOVE[1]
    return [TG.cyl_between(tuple(26.0 * _u(q["theta"])[:2]) + (s * zr,), tuple(37.0 * _u(q["theta"])[:2]) + (s * zr,), 1.6)
            for q in CROSS.values() for s in (-1.0, 1.0)]


# ---------------------------------------------------------------------------------------------------------------------
# the drive
# ---------------------------------------------------------------------------------------------------------------------
BODY = {"rotor": "rotor", "counter-rotor": "stator", "frame": "frame", "pinion": "pinion", "rotor | counter-rotor": "bearing",
        "rotor | frame": "bearing", "pinion | frame": "pinion", "belt": "belt", "motor": "motor"}


def drive_parts():
    """the reverser and the belt drive (sim/unmodelled_parts.py, their first cut as drawn) moved up DZ_DRIVE, less the
    parts the layout already carries (the shaft, the bridge-ring bearing for the gear-end one) or no longer needs (the
    counter-rotor's hub and end disc); the case cut at CASE_TOP. Returns the specs and each part's 2-D shape (the gears'
    and pulleys' blanks) for the sweep checks."""
    R, B = UP.reverser_sub(), UP.belt_sub()
    T = rot_z(0.0, dz=DZ_DRIVE)
    out = []
    seen = set()
    for S in (R, B):
        for p in S.parts:
            if p["name"] in DROP_DRIVE or p["name"] in seen:
                continue
            seen.add(p["name"])
            s3, s2 = apply(S.placed(p, True), T), apply(S.placed(p, False), T)
            if p["name"] == "case":
                top = ring(0.0, 200.0, CASE_TOP, CASE_TOP + 100.0)
                s3, s2 = cut(s3, top), cut(s2, top)
            k = p["proto"]
            body = BODY[p["body"]]
            join = f"drv-{p['name']}"
            rho = UP.MADE_RHO.get(k)
            m = UP.volume(s3) * 1e-9 * rho if rho else None
            out.append(dict(_spec(f"A_drv_{p['name']}", s3, S.protos[k][1], S.protos[k][2], body, "drive", join,
                                  p["label"].split(" - ", 1)[1].rsplit(" [", 1)[0], m, kind="drive",
                                  net="0" if body == "rotor" else None), blank=s2))
    return out


def shaft_keyway():
    """the rotor gear's keyway in the shaft, as the first cut cuts it, moved with the drive."""
    zb = UP.GG["apex_to_side_pitch_circle"] + UP.BACK
    return apply(box(UP.R_SHAFT - 4.0, UP.R_SHAFT + 1.0, -4.0, 4.0, 0.0, 12.0), UP.flip_x(-UP.PHI_P[0], dz=UP.Z_APEX - zb + DZ_DRIVE))


# =====================================================================================================================
# the study
# =====================================================================================================================
def rz_box(s, defl=0.25):
    """a solid's reach about the axis: its least radius (exact: its distance from the axis), its greatest (from its
    mesh, plus the mesh's deflection) and its z range (its bounding box)."""
    import motor_geometry as MG
    from OCP.BRepBuilderAPI import BRepBuilderAPI_MakeEdge
    from OCP.gp import gp_Pnt
    lo, hi = UP.bbox(s)
    axis = BRepBuilderAPI_MakeEdge(gp_Pnt(0, 0, lo[2] - 10.0), gp_Pnt(0, 0, hi[2] + 10.0)).Edge()
    P = MG.mesh_points(s, defl)
    r = np.hypot(P[:, 0], P[:, 1])
    return float(UP.distance(s, axis)), float(r.max()) + defl, lo[2], hi[2]


def revolved(s, tol=0.3):
    """whether a solid is a body of revolution about the axis, to the eye of its bounding box turned by 37 deg (a
    blank, a ring, a disc; to the mesh's deflection, 0.25 mm) [IR]: then one angle gives the least distance."""
    lo, hi = UP.bbox(s)
    l2, h2 = UP.bbox(apply(s, rot_z(37.0)))
    return all(abs(x - y) < tol for x, y in zip(lo + hi, l2 + h2)) and abs(lo[0] + hi[0]) < tol and abs(lo[1] + hi[1]) < tol


def turning_clearance(a, b, step=6.0, fine=1.0):
    """the least distance between a and b as b turns about the axis against a (a full turn, every step deg, then
    refined round the least to fine deg)."""
    best = (1e9, 0.0)
    for k in range(int(360.0 / step)):
        d = UP.distance(a, apply(b, rot_z(k * step)))
        if d is not None and d < best[0]:
            best = (d, k * step)
    a0 = best[1]
    for k in (range(-int(step / fine), int(step / fine) + 1) if step < 360.0 else ()):
        d = UP.distance(a, apply(b, rot_z(a0 + k * fine)))
        if d is not None and d < best[0]:
            best = (d, a0 + k * fine)
    return best


def solids(m, log):
    """every drawn solid on the rotor or the counter-rotor (the frame's, the pinions', the belt's and the motor's left
    out) with its mass, centroid and inertia, and the elements the two-body model reads (sim/bridge_ring_bearings.py
    solids_parts, with the drive's locating bearing as side A's end bearing). Masses: this study's where it sets them,
    else by material (sim/bridge_ring_bearings.py RHO_LAYOUT, then sim/shaft_bearings.py DENSITY)."""
    import bridge_ring_bearings as BRB
    import shaft_bearings as SB
    from OCP.BRepGProp import BRepGProp
    from OCP.GProp import GProp_GProps
    extra = [("brass", 8500.0), ("Al 6082", 2700.0), ("stainless", 7900.0), ("POM", 1410.0), ("bearing SKF", 7800.0),
             ("lock nut", 7800.0), ("taper bush", 7800.0), ("pulley", 7200.0), ("key", 7800.0), ("collar", 7900.0),
             ("spacer", 7900.0), ("retaining", 7900.0), ("LV", 2950.0), ("G10", 1850.0), ("FR-4", 1850.0)]
    parts, unknown = [], set()
    for pt in m.parts:
        if pt["body"] not in ("rotor", "stator", "bearing"):
            continue
        mat = m.protos[pt["proto"]][2]
        g = GProp_GProps(); BRepGProp.VolumeProperties_s(m.placed(pt), g)
        c, I = g.CentreOfMass(), g.MatrixOfInertia()
        kg = m.rpd_mass.get(pt["name"])
        rho = next((v for k, v in BRB.RHO_LAYOUT + extra if k in mat), None)
        if kg is None:
            if rho is None:
                try:
                    rho = SB._density(mat)
                except KeyError:
                    rho = 2700.0
                    unknown.add(mat)
            kg = g.Mass() * 1e-9 * rho
        J = I.Value(2, 2) * kg / max(g.Mass(), 1e-9) * 1e-6        # about its centroid, kg m2
        parts.append(dict(name=pt["name"], body=pt["body"], material=mat, kg=kg, x=c.X(), z=c.Z(), J_yy_kgm2=J))
    by = {p_["name"]: p_ for p_ in parts}
    fl = [e for e in m.lay["stack"]["elements"] if e["kind"] == "flange"][0]
    el = [dict(kind="hub", body="rotor", z0=m.zc - fl["h0"], z1=m.zc + fl["h0"])]
    for s_ in "AB":
        end = "A_drv_bearing_locating" if (s_ == "A" and m.drive) else f"{s_}_bearing_end"
        for where, nm in (("end", end), ("Ca|reluctance", f"{s_}_bearing_Ca-reluctance"),
                          ("bridge ring", f"{s_}_bearing_bridge-ring")):
            el.append(dict(kind="bearing", body="stator", side=s_, where=where, zc=by[nm]["z"], z0=by[nm]["z"], z1=by[nm]["z"]))
    st_ = [pt for pt in m.parts if pt["body"] == "stator" and not pt["name"].endswith("_spider_end")]
    zs = [UP.bbox(m.placed(pt)) for pt in st_]
    el.append(dict(kind="counter-rotor", body="stator", z0=min(lo[2] for lo, _ in zs), z1=max(hi[2] for _, hi in zs)))
    el += [dict(e, body="rotor") for e in m.el if e["kind"] == "w utron"]
    lad = dict(tube=m.lad["tube"], tube_geometry=dict(elements=el, L_total_mm=m.L_mm))
    if unknown:
        log(f"  masses by a 2700 kg/m3 default: {sorted(unknown)}")
    return lad, parts, sorted(unknown)


def shafts(m_full, log):
    """the two-body modes of the layout as drawn (with the mounts), and with this study's parts and drive, by the same
    reading of the solids [OC: sim/shaft_bearings.py two_body; d 25, the coupler joint, k_mag 2e5 N/m]."""
    import bridge_ring_bearings as BRB
    import shaft_bearings as SB
    m0 = TG.LayoutMachine().build()
    out = {}
    for tag, m in (("layout", m0), ("full", m_full)):
        lad, parts, unk = solids(m, log)
        rows = []
        for kb in (SB.K_BEARING, BRB.K_REAL):
            r = SB.two_body(lad, parts, 25.0, "coupler", k_b=kb, k_mag=2e5)
            rows.append(dict(k_b_N_per_m=kb, f_Hz=[round(x, 2) for x in r["f_Hz"][:4]], m_rotor_kg=round(r["m_rotor_kg"], 2),
                             m_counter_rotor_kg=round(r["m_counter_rotor_kg"], 2)))
        out[tag] = dict(rows=rows, default_density=unk)
        log(f"  shafts, {tag}: " + "; ".join(f"k_b {q['k_b_N_per_m']:.2e}: f {q['f_Hz'][:3]} Hz, rotor {q['m_rotor_kg']} kg"
                                             for q in rows))
    out["criterion_Hz"] = 60.0
    out["note"] = ("the layout as drawn now (its mounts in) against the same with the AH-drive parts, the drive and the "
                   "frame bearing A at the case floor; the pinions, the case and the belt are the frame's")
    return out


def main():
    t0 = time.time()
    log = lambda s: print(s, flush=True)
    m = TG.LayoutMachine(pump_parts=True, drive=True).build()
    log(f"layout with the rotor parts and the drive: {len(m.parts)} parts ({time.time() - t0:.0f} s)")
    new = set(m.rpd_names)
    by = {pt["name"]: pt for pt in m.parts}
    shp = {pt["name"]: m.placed(pt) for pt in m.parts}
    boxes = {n: UP.bbox(s) for n, s in shp.items()}
    res = dict(note="the magnetic pump's AH-drive parts placed on the rotor and the drive re-cut onto the layout's side A "
                    "end (sim/rotor_parts_drive.py)", status="PROPOSED (2026-10-12): the places and the re-cut are the "
                                                            "designer's to decide",
               sources=dict(parts="sim/parts_first_cut_results.json; sim/unmodelled_parts.py (the solids)",
                            drive="sim/drive_sizing_results.json; sim/unmodelled_parts.py reverser_sub, belt_sub",
                            layout="sim/tube_geometry.py LayoutMachine; sim/multiplier_layout_results.json; "
                                   "sim/bridge_ring_bearings.py"))
    # ---- placements
    res["placements"] = dict(sectors=SECTORS, utrons=UTRONS, cradle=dict(end_plate_t=END_T, end_plate_r=R_END, band=BAND,
                                                                         backplate=BACK, ballast=BAL, board_t=BOARD_T),
                             contents={"A": {"S1": "La", "S2": "D1*, D3*, snubbers a, d, x1, f2, bypass A",
                                             "S3": "K4 kick + ballast"},
                                       "B": {"S1": "Lb", "S2": "D2*, D4*, snubbers b, c, x2, f3, bypass B",
                                             "S3": "ballast"}},
                             choke=dict(u_mm=[CHOKE_U0, CHOKE_U0 + 3 * UP.CH_A], z_mm=[86.0, 86.0 + 2.5 * UP.CH_A],
                                        orientation="x (84) radial, the stack tangential, the legs axial"))
    # ---- the balance and the masses (m.rpd_rows from LayoutMachine's build)
    bal = {}
    w = 2.0 * math.pi * RPM / 60.0
    w2 = 2.0 * math.pi * RPM_CHECK / 60.0
    for side in "AB":
        rows = m.rpd_rows[side]
        tot = sum(r_["m"] for r_ in rows.values())
        vec = sum((r_["mu"] * _u(SECTORS[k]) + r_["mv"] * (1 if side == "A" else -1) * _u(SECTORS[k] + 90.0))
                  for k, r_ in rows.items())
        vz = sum((r_["muz"] * _u(SECTORS[k])) for k, r_ in rows.items())
        sec = {}
        for k, r_ in rows.items():
            r_cg = r_["mu"] / r_["m"]
            sec[k] = dict({a: round(b, 5) if isinstance(b, float) else b for a, b in r_.items()}, r_cg_mm=round(r_cg, 2),
                          F_600rpm_N=round(r_["m"] * w * w * r_cg * 1e-3, 1), F_750rpm_N=round(r_["m"] * w2 * w2 * r_cg * 1e-3, 1))
        bal[side] = dict(sectors=sec, mass_kg=round(tot, 4), residual_g_mm=round(float(np.linalg.norm(vec[:2])) * 1e3, 4),
                         residual_couple_g_mm2=round(float(np.linalg.norm(vz[:2])) * 1e3, 2))
    added = sum(b["mass_kg"] for b in bal.values())      # the cradles are in the wedges' sums
    U_per = 9549.0 * G25_N * (ROTOR_KG + added) / RPM      # ISO 21940-11: U = 9549 G m / n (g mm, m kg, n rpm)
    res["balance"] = dict(sides=bal, added_kg=round(added, 3), rotor_kg_before=ROTOR_KG,
                          rotor_kg_after=round(ROTOR_KG + added, 2), added_fraction=round(added / ROTOR_KG, 3),
                          G25_permissible_g_mm=round(U_per, 0),
                          note="each wedge's m r, m v and m r z equal the choke wedge's, so each side sums to zero and the "
                               "two sides leave no couple [OC]; the residual is the solver's. The as-built balance is the "
                               "rotor's G2.5 at assembly (DCCREG-design-ledger.md §3.6) [IR]")
    # the centrifugal load path: each wedge's parts on the backplate, the backplate on the two end plates, the end plates
    # on the carrier discs; M5 bolts [RH: their count]
    Fmax = max(s_["F_750rpm_N"] for b in bal.values() for s_ in b["sectors"].values())
    n_b, A_m5 = 8, 14.2
    res["loads"] = dict(F_max_750rpm_N=Fmax, bolts_per_wedge=n_b, M5_stress_area_mm2=A_m5,
                        bolt_shear_MPa=round(Fmax / n_b / A_m5, 2), G10_bearing_MPa=round(Fmax / n_b / (5.0 * END_T), 2),
                        end_plate_tension_MPa=round(0.5 * Fmax / (END_T * 40.0), 2),
                        note="[RH] the bolts (8 per wedge, M5) and the end plates' least width (40 mm, in-plane tension); G10's shear and "
                             "bearing strengths are some 100 MPa and more, so the cradle is lightly loaded; the carrier "
                             "discs' extra duty is OPEN against sim/rotor-mechanics-findings.md")
    log(f"  balance: added {added:.2f} kg, residuals {bal['A']['residual_g_mm']} / {bal['B']['residual_g_mm']} g mm")
    # ---- clash: every new part against every part
    clash, n_pairs = [], 0
    from OCP.BRepAlgoAPI import BRepAlgoAPI_Common
    names = list(shp)
    for a in sorted(new):
        la, ha = boxes[a]
        for b in names:
            if b == a or (b in new and b < a):
                continue
            lb, hb = boxes[b]
            if any(ha[k] < lb[k] - 0.01 or hb[k] < la[k] - 0.01 for k in range(3)):
                continue
            if by[a]["join"] == by[b]["join"]:
                continue
            n_pairs += 1
            v = UP.volume(BRepAlgoAPI_Common(shp[a], shp[b]).Shape())
            if v > 1e-3:
                clash.append((a, b, round(v, 4)))
    res["clash"] = dict(pairs_tested=n_pairs, clashes=clash, pass_=not clash)
    log(f"  clash: {n_pairs} pairs, {len(clash)} clashes {clash[:6]}")
    # ---- turning clearances: rotor | counter-rotor | frame, each pair whose reach about the axis comes within 15 mm
    blank = m.rpd_blank
    sh2 = lambda n: blank.get(n, shp[n])
    turning = [n for n in names if by[n]["body"] in ("rotor", "stator", "frame")]
    rz = {n: rz_box(sh2(n)) for n in turning}
    pairs = []
    for i, a in enumerate(turning):
        for b in turning[i + 1:]:
            ba, bb = by[a]["body"], by[b]["body"]
            if ba == bb or not (a in new or b in new or "frame" in (ba, bb)):
                continue
            ra, rb = rz[a], rz[b]
            if ra[0] > rb[1] + 15 or rb[0] > ra[1] + 15 or ra[2] > rb[3] + 15 or rb[2] > ra[3] + 15:
                continue
            pairs.append((a, b))
    log(f"  turning: {len(pairs)} pairs")
    tc = []
    for i, (a, b) in enumerate(pairs):
        ra, rb = rz[a], rz[b]
        gap_r = max(rb[0] - ra[1], ra[0] - rb[1])
        gap_z = max(rb[2] - ra[3], ra[2] - rb[3])
        row = dict(a=a, b=b, bodies=f"{by[a]['body']} | {by[b]['body']}")
        if max(gap_r, gap_z) > 0.0:                 # apart in r or in z: no turn brings them closer [OC]
            row.update(least_mm=round(max(gap_r, gap_z), 3), how="apart in " + ("r" if gap_r >= gap_z else "z"))
        else:
            rev = revolved(sh2(a)) or revolved(sh2(b))
            d, ang = turning_clearance(sh2(a), sh2(b), step=360.0 if rev else 6.0)
            row.update(least_mm=round(d, 3), at_deg=ang, how="turned")
            log(f"  turned {a} | {b}: {d:.2f} mm at {ang:.0f} deg ({time.time() - t0:.0f} s)")
        tc.append(row)
    tc.sort(key=lambda r_: r_["least_mm"])
    res["turning"] = dict(pairs=len(tc), least=tc[:25], hits=[r_ for r_ in tc if r_["least_mm"] < 1.0],
                          pass_=all(r_["least_mm"] >= 1.0 for r_ in tc),
                          note="each pair of parts on different bodies (rotor, counter-rotor, frame) whose reach about "
                               "the axis comes within 15 mm: where their r ranges or z ranges are apart, the gap (no "
                               "turn brings them closer); else the one turned a full turn against the other (every 6 "
                               "deg, refined to 1 deg), or once where either is a body of revolution. The gears and pulleys as their blanks. "
                               "Pass: 1 mm or more [IR]")
    log(f"  turning: least {tc[0] if tc else None}")
    # ---- the drive's stack-up as placed
    dz = lambda n: [round(boxes[n][0][2], 2), round(boxes[n][1][2], 2)]
    res["drive"] = dict(dz_mm=DZ_DRIVE, dropped_first_cut=list(DROP_DRIVE), dropped_layout=list(DROP_LAYOUT),
                        case_top_mm=CASE_TOP, shaft_A_from_mm=SHAFT_A_Z0, sleeve_rel_A_from_mm=SLEEVE_A_Z0,
                        z_mm={n.replace("A_drv_", ""): dz(n) for n in sorted(new) if n.startswith("A_drv_")},
                        bridge_ring_bearing_A_mm=dz("A_bearing_bridge-ring"),
                        frame_bearings_mm=[round(0.5 * sum(dz("A_drv_bearing_locating")), 2),
                                           round(0.5 * sum(dz("B_bearing_end")), 2)],
                        machine_z_mm=[round(min(b[0][2] for b in boxes.values()), 2), round(max(b[1][2] for b in boxes.values()), 2)])
    fb = res["drive"]["frame_bearings_mm"]
    res["drive"]["frame_bearing_span_mm"] = round(fb[1] - fb[0], 2)
    res["drive"]["frame_bearing_span_before_mm"] = 1004.0 - 10.0        # sim/bridge_ring_bearings_results.json z_frame_mm
    # ---- the cross leads' field [RH]: the coax ring | can, the lead at 0 V at r 39
    V = json.load(open(os.path.join(HERE, "multiplier_layout_results.json")))["volts"]["V_B_kV"]
    r_ring, r_can = 25.0, 46.0           # the rings on the vessel (OD 50, presets/hub-locked.json), the can's bore
    E0 = V / (CROSS_R * math.log(r_can / r_ring))
    phi_loc = V * math.log(r_can / CROSS_R) / math.log(r_can / r_ring)
    h = r_can - CROSS_R
    a = CROSS_WIRE_R
    Es = phi_loc / (a * math.log(2.0 * h / a))
    peek = 3.0 * (1.0 + 0.301 / math.sqrt(0.1 * a))           # Peek's onset in air, kV/mm: 30 (1 + 0.301 / sqrt(r_cm)) kV/cm
    res["cross_leads"] = dict(paths={q["name"]: dict(theta_deg=q["theta"], z_mm=q["z"], what=q["what"]) for q in m.rpd_cross},
                              r_mm=CROSS_R, wire_r_mm=CROSS_WIRE_R, V_ring_kV=round(V, 2),
                              E_coax_at_r39_kV_mm=round(E0, 3), V_local_kV=round(phi_loc, 2),
                              E_surface_kV_mm=round(Es, 2), Peek_onset_kV_mm=round(peek, 2),
                              note="[RH] a coax estimate: the rings (+/-14.9 kV, r 25) inside the grounded can (r 46), "
                                   "the lead at about 0 V where the field would put it at the local potential; its "
                                   "surface field a line charge's over the can 7 mm away. A field solve of the hub with "
                                   "the leads is OPEN; so is what the leads do to the rings' field on the coupler")
    # ---- the shafts
    res["shafts"] = shafts(m, log)
    # ---- the renders
    res["figure"] = figure(m, shp, new, log)
    res["n_parts_layout_full"] = len(m.parts)
    res["n_new"] = len(new)
    res["run_s"] = round(time.time() - t0, 1)
    json.dump(res, open(OUT, "w"), indent=1, default=float)
    log(json.dumps({k: res[k] for k in ("balance", "loads", "clash", "drive", "cross_leads")}, indent=1, default=float)[:5000])
    log(f"wrote {os.path.relpath(OUT, ROOT)} ({res['run_s']} s)")


def figure(m, shp, new, log):
    """(a), (b) plan cuts through bays A and B at their mid-plane; (c) side A's end through the shaft (y = 0) with the
    drive; (d) the hub cut through the cross lead b's plane (-10 deg)."""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.patches import Patch
    by = {pt["name"]: pt for pt in m.parts}
    zc = m.zc
    fig = plt.figure(figsize=(20, 13.5))

    def sel(pred):
        return [(by[n], s) for n, s in shp.items() if pred(n, s)]

    def plan(ax, zz, side):
        P = sel(lambda n, s: UP.bbox(s)[0][2] <= zz <= UP.bbox(s)[1][2])
        TG._draw(ax, TG._sections(m, P, ("z", zz)), lw=0.3)
        for key, phi in SECTORS.items():
            c = 75.0 * _u(phi)
            lab = dict(A={"S1": "S1: La", "S2": "S2: D1*, D3*,\nsnubbers, bypass A", "S3": "S3: K4 kick,\nballast"},
                       B={"S1": "S1: Lb", "S2": "S2: D2*, D4*,\nsnubbers, bypass B", "S3": "S3: ballast"})[side][key]
            ax.annotate(lab, c[:2], 158.0 * _u(phi)[:2], fontsize=7.5, ha="center", va="center",
                        arrowprops=dict(arrowstyle="-", lw=0.5, color="#333"))
        for a in UTRONS:
            ax.text(*(100.0 * _u(a)[:2]), "utron", fontsize=6.5, ha="center", va="center", rotation=a - 90 if a else -90,
                    color="#222")
        ax.set_aspect("equal"); ax.set_xlim(-175, 175); ax.set_ylim(-175, 175); ax.tick_params(labelsize=7)
        ax.set_title(f"({'a' if side == 'A' else 'b'}) bay {side} at z {zz:.0f}, its mid-plane, seen from +z", fontsize=9.5,
                     loc="left")
    plan(fig.add_axes((0.02, 0.505, 0.30, 0.44)), 121.0, "A")
    plan(fig.add_axes((0.02, 0.03, 0.30, 0.43)), 2.0 * zc - 121.0, "B")
    # (c) side A's end
    ac = fig.add_axes((0.34, 0.04, 0.40, 0.92))
    P = sel(lambda n, s: UP.bbox(s)[0][1] <= 0.01 <= UP.bbox(s)[1][1] + 0.02 and UP.bbox(s)[0][2] < 240.0)
    TG._draw(ac, TG._sections(m, P, ("y", 0.0)), lw=0.35)
    ac.axvline(0, color="#888", lw=0.5, ls="--")
    ac.set_aspect("equal"); ac.set_xlim(-290, 300); ac.set_ylim(-115, 240); ac.tick_params(labelsize=7)
    ac.set_xlabel("x [mm] (y = 0: 0 deg right, 180 deg left)", fontsize=8)
    ac.set_ylabel("z [mm] from side A's end (the layout's)", fontsize=8)
    lab = dict(fontsize=7.2, ha="left", va="center", color="#222")
    for z_, t_ in ((121.0, "bay A: S2 at 180 deg\n(ballast, board, parts)"),
                   (30.0, "bridge-ring bearing A in\nits cartridge; the CR gear\nbolted under it"),
                   (-5.5, "the pinions' plane\n(z -5.5), the case"), (-56.0, "the locating bearing\n(frame), the case floor"),
                   (-83.0, "the belt plane: the 80T\npulley in the bell")):
        ac.annotate(t_, (-60.0, z_), (-285.0, z_), arrowprops=dict(arrowstyle="-", lw=0.4, color="#666"), **lab)
    ac.text(190, 85.0, "the motor (200 W) on its\nplate, 245 mm out along +x", **lab)
    ac.set_title("(c) side A's end through the shaft, exact cut: the drive re-cut onto the layout (+30.5 mm)", fontsize=9.5,
                 loc="left")
    # (d) the hub through lead b's plane
    ad = fig.add_axes((0.76, 0.50, 0.23, 0.46))
    th = CROSS["b"]["theta"]
    P = [(by[n], apply(s, rot_z(-th))) for n, s in shp.items() if 400.0 < UP.bbox(s)[1][2] and UP.bbox(s)[0][2] < 610.0
         and min(abs(UP.bbox(s)[0][0]), abs(UP.bbox(s)[1][0])) < 60.0]
    P = [(pt, s) for pt, s in P if UP.bbox(s)[0][1] <= 0.01 <= UP.bbox(s)[1][1] + 0.02]
    TG._draw(ad, TG._sections(m, P, ("y", 0.0)), lw=0.35)
    ad.set_aspect("equal"); ad.set_xlim(-5, 60); ad.set_ylim(415, 600); ad.tick_params(labelsize=7)
    ad.text(41, 507, "lead b at r 39,\nin the can", fontsize=7, ha="left")
    ad.set_title(f"(d) the hub through the cross lead b's plane ({th:.0f} deg)", fontsize=9, loc="left")
    an = fig.add_axes((0.76, 0.04, 0.23, 0.42)); an.axis("off")
    leg = [("g10", "G10 (cradles, boards, sleeve)"), ("brass", "brass ballast"), ("fe", "SiFe laminations (La / Lb)"),
           ("cu", "Cu (windings)"), ("blue", "bypass capacitor"), ("black", "Schottky / kick parts"),
           ("al", "Al 6082 (case, bell, pulleys)"), ("ss", "stainless (gears, spacers)"), ("pom", "POM pinions"),
           ("steel", "steel (shaft, bearings)"), ("lv", "LV harness, cross leads")]
    an.legend(handles=[Patch(facecolor=COL[k], label=t) for k, t in leg], loc="upper left", fontsize=8, frameon=False)
    an.text(0.0, 0.42, "PROPOSED (2026-10-12), the designer's to decide:\nthe magnetic pump's parts in the reluctance "
            "bays'\nfree wedges on G10 cradles, ballasted so each\nside balances; the drive re-cut onto the layout's\n"
            "side A end. sim/rotor_parts_drive.py; its results\nand findings.", fontsize=8.2, va="top", transform=an.transAxes)
    fig.suptitle("The AH-drive parts on the rotor and the drive at side A, in the layout's solids", fontsize=12, x=0.01,
                 y=0.995, ha="left")
    os.makedirs(os.path.dirname(FIG), exist_ok=True)
    fig.savefig(FIG, dpi=110); plt.close(fig)
    log(f"  wrote {os.path.relpath(FIG, ROOT)}")
    return os.path.relpath(FIG, ROOT)


if __name__ == "__main__":
    main()
