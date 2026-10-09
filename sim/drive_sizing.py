#!/usr/bin/env python3
"""sim/drive_sizing.py -- the drive of the locked machine: the 1 : -1 reversing gear between the rotor (+600 rpm) and
the counter-rotor (-600 rpm), the belt drive, the reaction torque's path into the frame, and a bill of parts.
Status: PROPOSED (the designer accepts it). Write-up: docs/drive-gear-belt.md.

What it does, in order:
 1. The bodies: each rotating part's mass and polar inertia, from the records: sim/utron_profile.py's spec of the
    magnetic pick (utrons, bridges, bridge rings, carrier discs), sim/air_stack_sizing_results.json (the vanes and the
    Ca / Cb plates of record), the tube model's parts (cage, spiders; docs/geometry/tube/...parts.json) and
    presets/hub-locked.json (the hub). Parts the records do not place are [RH] lumps, named as such.
 2. The steady torques: the pumps' power of record at 1200 rpm relative, the bearings' drag (SKF-class) and a stated
    windage allowance, split into what acts between the bodies (at the relative speed) and what acts on each body
    against the frame (at 600 rpm). Through a 1 : -1 gear whose carrier is the frame, the gear applies the same torque
    to both bodies and the frame takes the sum [OC].
 3. The pulsation: the magnetic pump's instantaneous torque from its deck of record (sim/rotor_parts_duty.py's pick, with
    the 22 mF bypass exactly as sim/ah_steady_cusp.py adds it; ngspice) and the electrostatic pump's from the
    one-revolution record (sim/hub_revolution_results.json: T = -1/2 V^2 dC/dtheta). A 7-inertia torsional model
    (motor; gear end, side A and side B of each body) gives what the gear, the hub joint, the cage and the belt carry,
    with stainless or polymer pinions [IR].
 4. The run-up from rest with the chosen motor (constant torque at the driver's limit), and the fault torque.
 5. The gear: geometry, Lewis / AGMA-class bending and Hertz contact on the virtual spur gear at the mean section [IR],
    the pinions' shafts and bearings, the bearings' lives.
 6. The belt: HTD 5M with a catalogue-class specific tooth load [IR]; ratio, pulleys, length, tension, hub loads.
 7. The frame's loads, the envelope at the frame end (side A, below), and the bill of parts against the cost sheet's
    placeholders (docs/make_cost_sheet.py BOM fixed: gear 250, drive 250, frame 300).
Tags: [OC] derivable physics; [IR] a modelling / engineering choice (incl. catalogue-class values); [RH] heuristic or
placeholder (CONVENTIONS.md section 1). Symbols: g is a gap, never a bare d; diameters are written Ø.
Usage: python3 sim/drive_sizing.py [--no-spice] [--figure]
  --no-spice   reuse the magnetic pump's harmonics stored in sim/drive_sizing_results.json instead of re-running ngspice
  --figure     also write docs/figures/drive-gear-concept.svg (the kinematic sketch, drawn from these dimensions)
Writes sim/drive_sizing_results.json.
"""
import json
import math
import os
import shutil
import subprocess
import sys
import tempfile

sys.dont_write_bytecode = True                  # no new __pycache__ entries beside the records
import numpy as np                              # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
OUT = os.path.join(HERE, "drive_sizing_results.json")
FIG = os.path.join(ROOT, "docs", "figures", "drive-gear-concept.svg")
G0 = 9.81

SOURCES = []                                    # provenance of every input number


def cite(name, value, unit, source, tag, note=""):
    SOURCES.append(dict(name=name, value=value, unit=unit, source=source, tag=tag, note=note))
    return value


def load(rel):
    with open(os.path.join(ROOT, rel)) as f:
        return json.load(f)


# ======================================================================================================== the record
PICK = "g 0.5 / 6 bridges / 1200 rpm"
RPM_BODY = cite("speed of each body", 600.0, "rpm", "sim/pole-design-findings.md section 6 (recommendation); "
                "docs/ledger/DCCREG-design-ledger.md section 1 (600 rpm each way, 1200 relative)", "[IR] decided")
W_BODY = 2 * math.pi * RPM_BODY / 60.0                       # rad/s, each body against the frame
W_REL = 2 * W_BODY                                           # rad/s, rotor against counter-rotor [OC]
F_PUMP = 6 * 2 * RPM_BODY / 60.0                             # 6 cycles per relative revolution -> 120 Hz [OC]

_cusp = [r for r in load("sim/ah_steady_cusp_results.json")["rows"] if r["C_byp_mF"] == 22.0][0]
P_MAG = cite("magnetic pump, belt power (22 mF bypass)", _cusp["P_belt_W"], "W",
             "sim/ah_steady_cusp_results.json rows[C_byp_mF=22].P_belt_W", "[OC] ngspice record")
_op = load("sim/pole_design_variants_op.json")["designs"][PICK]
P_FE = cite("magnetic pump, iron loss (both sides)", 2 * _op["best"]["P_fe_side_W"], "W",
            "sim/pole_design_variants_op.json designs[pick].best.P_fe_side_W x 2", "[RH] M235-35A rating scaled")
_es = [r for r in load("sim/core_field_results.json")["rows"] if r.get("name") == "none" and "P_belt_W" in r][0]
P_ES = cite("electrostatic pump, belt power", _es["P_belt_W"], "W",
            "sim/core_field_results.json rows[name='none'].P_belt_W", "[OC] ngspice record")
P_PUMPS = P_MAG + P_FE + P_ES

# the old pump's reaction torque, for the record (sim/spinup-findings.md: W 6 / 2 pi at 20 kV, 300 rpm relative)
T_PUMP_OLD = cite("earlier electrostatic pump's reaction torque", 0.078, "N m", "sim/spinup-findings.md (T_pump)",
                  "[OC] for an earlier pump")

# ------------------------------------------------------------------------------------------- geometry of the record
_air = [r for r in load("sim/air_stack_sizing_results.json")["thick_vanes"]["compare"]
        if r["t_vaneMm"] == 3.0 and r["n_plates"] == 6][0]
M_RV = cite("rotor vanes, both sides (12)", _air["rotor_vanes_kg"], "kg",
            "sim/air_stack_sizing_results.json thick_vanes.compare[t 3, 6 + 6]", "[OC] geometry")
M_SV = cite("stator vanes, both sides (12)", _air["stator_vanes_kg"], "kg", "same row", "[OC] geometry")
M_CA = cite("Ca / Cb plates, both sides (12), on the rotor", _air["ca_plates_kg"], "kg",
            "same row; on the rotor per sim/core-field-findings.md (HV side on the rotor)", "[OC] geometry")
L_TUBE_REC = cite("tube length with the air stack of record", _air["L_tube_mm"], "mm", "same row", "[IR] layout")
L_ES_SIDE = cite("electrostatic stacks per side (C1 + Ca)", _air["L_es_side_mm"], "mm", "same row", "[IR] layout")
DL_HUB = cite("growth of the tube for the locked hub", 24.0, "mm", "sim/hub-locked-findings.md section 4", "[IR]")
T_VANE, R_IN, R_OUT, SEC_DEG, N_SEC = 3.0, 50.0, 150.0, 22.0, 6  # vane band, 6 x 22 deg (ledger section 3.4)

REC_PARTS = "docs/geometry/tube/tube-r150-n6-air6-wound-g0p5-6br-hub50.parts.json"   # the design of record in solids
_parts = load(REC_PARTS)["elements"]
L_TUBE = cite("machine length of record (rotating parts, end slots included)", max(e["z1"] for e in _parts), "mm",
              REC_PARTS + " (= 916 + 24: sim/tube-shaft-findings.md section 0)", "[IR] layout")
assert abs(L_TUBE - (L_TUBE_REC + DL_HUB)) < 1.0, "the record's solids and the air stack's length disagree"
_ring = [e for e in _parts if e["kind"] == "w ring" and e["side"] == "A"][0]
L_RING = cite("G10 bridge ring length", _ring["z1"] - _ring["z0"], "mm", REC_PARTS + " (w ring A)", "[IR] as modelled")
_brg_rel = [e for e in _parts if e["kind"] == "bearing" and e["side"] == "A" and e["where"] == "Ca|reluctance"][0]
Z_CAGE0 = cite("cage starts at the Ca|reluctance bearing slot", _brg_rel["z0"], "mm", REC_PARTS + " (bearing A Ca|reluctance)",
               "[IR] as modelled")


def z_of(kind, body=None, side="A"):
    """mean z (mm) of the record's elements of a kind on side A (z 0 at the bottom end-bearing slot)."""
    es = [e for e in _parts if e["kind"] == kind and e.get("side") == side and (body is None or e["body"] == body)]
    return sum(0.5 * (e["z0"] + e["z1"]) for e in es) / len(es)


Z_SPIDERS_A = sum(e["zc"] for e in _parts if e["kind"] == "bearing" and e["side"] == "A" and e["where"] != "end") / 2
R_CAGE0, R_CAGE1 = R_OUT + 12.0, R_OUT + 16.0                   # sim/tube_geometry.py: sector(ro + 12, ro + 16)
L_CAGE = L_TUBE - 2 * Z_CAGE0                                   # one tube across the hub (570 mm)

import stack_sizing as SS                                       # noqa: E402  (constants only)
import utron_profile as UP                                      # noqa: E402

BRG = SS.BEARING                                                # 6205-class 25 / 52 / 15, 8 mm G10 spider, 20 mm slot
R_SHAFT, R_SLEEVE = SS.SHAFT_R, SS.SLEEVE_R
SP = UP.spec(_op["design"], _op["best"])                        # the pick's utron and bridge, every dimension
_hub = load("presets/hub-locked.json")
HUB_FLANGE_ABSZ = _hub["shaft"]["value"]["flange_absz_mm"]      # [72, 80]
SHAFT_D_REGISTER = _hub["shaft"]["value"]["d_mm"]               # 30 (REGISTER; the tube model has 25: OPEN)
cite("shaft diameter, tube model / hub register", [2 * R_SHAFT, SHAFT_D_REGISTER], "mm",
     "sim/stack_sizing.py SHAFT_R; presets/hub-locked.json shaft.d_mm", "[IR] OPEN")
_la = [r for r in load("sim/rotor_parts_duty_results.json")["la_core"] if r["tau_s"] == 0.5][0]
M_CHOKE = cite("La / Lb first-cut choke, each", _la["m_core_kg"] + _la["m_cu_kg"], "kg",
               "sim/rotor_parts_duty_results.json la_core[tau 0.5]", "[RH] first cut, not designed")

RHO = dict(al=2700.0, g10=1850.0, sife=UP.RHO_FE, nife=UP.RHO_NIFE, cu=UP.RHO_CU_KG, ss=7900.0, peek=1300.0,
           glass=2230.0, mnzn=4800.0, pom=1410.0, steel=7850.0)
G_SS, G_G10 = 77e9, 5e9                         # shear moduli: austenitic stainless [OC]; G10 in-plane [RH]


# =========================================================================================== 1. the bodies' inertias
def poly_area_J(poly):
    """area (mm^2) and polar second moment about the machine axis (mm^4) of a closed (u, v) polyline [OC]."""
    a = jx = jy = 0.0
    for (x0, y0), (x1, y1) in zip(poly, poly[1:] + poly[:1]):
        c = x0 * y1 - x1 * y0
        a += c
        jx += c * (y0 * y0 + y0 * y1 + y1 * y1)
        jy += c * (x0 * x0 + x0 * x1 + x1 * x1)
    s = 1.0 if a > 0 else -1.0
    return s * a / 2.0, s * (jx + jy) / 12.0


def rect_area_J(u0, u1, v0, v1):
    return (u1 - u0) * (v1 - v0), (u1 ** 3 - u0 ** 3) / 3.0 * (v1 - v0) + (u1 - u0) * (v1 ** 3 - v0 ** 3) / 3.0


def sector_area_J(r0, r1, deg=360.0):
    f = deg / 360.0
    return f * math.pi * (r1 ** 2 - r0 ** 2), f * math.pi / 2.0 * (r1 ** 4 - r0 ** 4)


def solid(A_J, t_mm, rho):
    """mass (kg) and polar inertia (kg m^2) of a prism of section (area, J) and length t."""
    a, j = A_J
    return rho * a * t_mm * 1e-9, rho * j * t_mm * 1e-15


def utron_inertia(sp):
    """one wound utron about the machine axis: SiFe half-cores, NiFe neck strip, G10 (spacer, cover, cheeks) and the
    copper on its mean turn (sim/utron_profile.py dimensions) [OC: geometry; IR: the copper on the mean turn]."""
    L = sp["L"]
    out = {}
    m = j = 0.0
    for sd in (+1, -1):                                         # two L-shaped half-cores
        mm, jj = solid(poly_area_J(UP.half_core(sp, sd, arc=True)), L, RHO["sife"])
        m += mm; j += jj
    for (u, v) in sp["studs"]:                                  # the two stud holes in each half-core
        for sd in (+1, -1):
            a = math.pi * (sp["stud_d"] / 2.0) ** 2
            m -= RHO["sife"] * a * L * 1e-9
            j -= RHO["sife"] * a * L * (u * u + v * v) * 1e-15
    out["sife"] = (m, j)
    R = UP.rects(sp)
    out["nife"] = solid(rect_area_J(*R["strip"]), L, RHO["nife"])
    g = [solid(rect_area_J(*R["spacer"]), L, RHO["g10"]), solid(poly_area_J(UP.wedge(sp)), L, RHO["g10"])]
    for k in ("cheek_pos", "cheek_neg"):
        mm, jj = solid(rect_area_J(*R[k]), sp["t_cheek"], RHO["g10"])
        g.append((2 * mm, 2 * jj))                              # one cheek per stack end
    out["g10"] = (sum(x[0] for x in g), sum(x[1] for x in g))
    # copper: the mean turn (rounded rectangle in the (u, w) plane) carries m_cu uniformly; the section adds v^2
    um, up_ = 0.5 * (sp["u_m0"] + sp["u_m1"]), 0.5 * (sp["u_p0"] + sp["u_p1"])
    rc = sp["clr"] + sp["h_c"] / 2.0
    pts, wts = [], []
    for u in (um, up_):                                         # the two straight sides along the stack, length L
        pts.append(u * u); wts.append(L)
    n = 200                                                     # the two end parts: 2 x (2 quarter arcs + b)
    for k in range(n):
        ph = math.pi * (k + 0.5) / n                            # a half turn from u_m to u_p around one end
        u_arc = 0.5 * (um + up_) - 0.5 * (up_ - um) * math.cos(ph)
        pts.append(u_arc * u_arc); wts.append(2 * (math.pi * rc + sp["b"]) / n)
    mean_u2 = sum(p * w for p, w in zip(pts, wts)) / sum(wts)
    m_cu = sp["m_cu_kg"]
    out["cu"] = (m_cu, m_cu * (mean_u2 + sp["cv"] ** 2 / 3.0) * 1e-6)
    out["total"] = (sum(v[0] for k, v in out.items()), sum(v[1] for k, v in out.items()))
    return out


def vane_part(kind):
    """one vane or plate of record, 3 mm Al: (area, J) of its section [OC: geometry]."""
    sec = sector_area_J(R_IN, R_OUT, N_SEC * SEC_DEG)
    if kind == "rotor":                                         # 6 x 22 deg sectors + the inner ring on the sleeve
        ring = sector_area_J(R_SLEEVE, R_IN)
    elif kind == "stator":                                      # 6 x 22 deg sectors + the outer ring into the cage
        ring = sector_area_J(R_OUT, R_OUT + 12.0)
    else:                                                       # Ca / Cb: full annulus
        return sector_area_J(R_IN, R_OUT)
    return sec[0] + ring[0], sec[1] + ring[1]


def bodies():
    """every part: (name, body, station, z_mm, mass_kg, J_kgm2, tag). z from the old end-bearing slot's bottom (z 0),
    side A below; side B mirrored about the hub centre L_TUBE / 2. Stations: R0 / C0 the gear end, RA / CA side A,
    RB / CB side B."""
    zc = L_TUBE / 2.0
    mir = lambda z: 2 * zc - z
    P = []

    def add(name, body, side, z, m, j, tag, both=True):
        if both:
            P.append((name + " A", body, body[0].upper() + "A", z, m / 2, j / 2, tag))
            P.append((name + " B", body, body[0].upper() + "B", mir(z), m / 2, j / 2, tag))
        else:
            P.append((name, body, side, z, m, j, tag))
    ut = utron_inertia(SP)
    add("utrons (3 + 3)", "rotor", None, z_of("w utron"), 6 * ut["total"][0], 6 * ut["total"][1], "[OC] geometry of the pick")
    m, j = solid(sector_area_J(R_SLEEVE, SP["r_disc"]), SP["t_disc"], RHO["g10"])
    add("utron carrier discs (2 + 2)", "rotor", None, 101.0, 4 * m, 4 * j, "[OC] geometry")
    a, jj = vane_part("rotor")
    k = M_RV / (12 * RHO["al"] * a * T_VANE * 1e-9)             # normalise to the record's mass (k = 1.000)
    add("rotor vanes (6 + 6)", "rotor", None, z_of("C1 vane", "rotor"), M_RV, 12 * k * RHO["al"] * jj * T_VANE * 1e-15, "[OC] geometry")
    a, jj = vane_part("ca")
    k = M_CA / (12 * RHO["al"] * a * T_VANE * 1e-9)
    add("Ca / Cb plates (6 + 6)", "rotor", None, z_of("Ca plate"), M_CA, 12 * k * RHO["al"] * jj * T_VANE * 1e-15, "[OC] geometry")
    r_ch = 0.090                                                # [RH] where the chokes ride: not drawn
    add("La / Lb chokes (1 + 1)", "rotor", None, 200.0, 2 * M_CHOKE, 2 * M_CHOKE * r_ch ** 2,
        "[RH] placement at r 90 mm (not drawn)")
    add("rotor electronics, wiring, potting (1 + 1 kg)", "rotor", None, 300.0, 2.0, 2.0 * 0.100 ** 2,
        "[RH] lump at r 100 mm: D1-D4, Z1 / Z4, the chains, the AH bypass, snubbers")
    L_sl = 2 * (L_TUBE / 2.0 - HUB_FLANGE_ABSZ[1] - BRG["slot"])
    m, j = solid(sector_area_J(R_SHAFT, R_SLEEVE), L_sl, RHO["g10"])
    add("G10 rotor sleeve", "rotor", None, 200.0, m, j, "[IR] between the end slot and the flanges")
    # the hub (presets/hub-locked.json): vessel, PEEK retainer, G10 coupler, MnZn rods, AH coils, the two flanges
    r_v = 25.0
    m_v = RHO["glass"] * 4 / 3 * math.pi * (r_v ** 3 - (r_v - 1.5) ** 3) * 1e-9
    m_ret = RHO["peek"] * (math.pi * 30.0 ** 2 * 144.0 - 4 / 3 * math.pi * r_v ** 3) * 1e-9
    m_cpl = RHO["g10"] * math.pi * (33.0 ** 2 - 30.0 ** 2) * 144.0 * 1e-9
    m_ah = 2 * (RHO["mnzn"] * math.pi * 6.15 ** 2 * 41.3 + 0.6 * RHO["cu"] * math.pi * (11.45 ** 2 - 8.25 ** 2) * 40.0) * 1e-9
    m_fl, j_fl = solid(sector_area_J(0.0, 32.0), 8.0, RHO["ss"])
    j_hub = (m_v * (2 / 3) * (0.0243 ** 2) + m_ret * 0.030 ** 2 / 2 + m_cpl * (0.030 ** 2 + 0.033 ** 2) / 2
             + m_ah * 0.010 ** 2 + 2 * j_fl)
    add("hub: vessel, retainer, coupler, AH, flanges", "rotor", None, zc - 40.0, m_v + m_ret + m_cpl + m_ah + 2 * m_fl,
        j_hub, "[IR] presets/hub-locked.json extents")
    # the shaft (austenitic stainless, Ø 25 tube model), from the drive end (z -132) to the top journal (L + 20)
    z_lo, z_hi = Z_SHAFT_END, L_TUBE + 20.0
    m_sh = RHO["ss"] * math.pi * R_SHAFT ** 2 * (z_hi - z_lo) * 1e-9
    j_sh = m_sh * (R_SHAFT * 1e-3) ** 2 / 2
    f0 = (20.0 - z_lo) / (z_hi - z_lo)
    P.append(("shaft, gear end (below z 20)", "rotor", "R0", 0.5 * (z_lo + 20), m_sh * f0, j_sh * f0, "[IR] Ø 25"))
    P.append(("shaft A", "rotor", "RA", 0.5 * (20 + zc), m_sh * (1 - f0) / 2, j_sh * (1 - f0) / 2, "[IR] Ø 25"))
    P.append(("shaft B", "rotor", "RB", 0.5 * (zc + z_hi), m_sh * (1 - f0) / 2, j_sh * (1 - f0) / 2, "[IR] Ø 25"))
    # the drive's own rotating parts (this design): the rotor's side gear, the pulley; the counter-rotor's end parts
    P.append(("rotor side gear (z 30, stainless)", "rotor", "R0", GEAR["z_rotor_gear"], GEAR["m_side_kg"], GEAR["J_side"],
              "[IR] this design"))
    P.append(("machine pulley HTD 5M 80T", "rotor", "R0", GEAR["z_pulley"], BELT["m_pulley_kg"], BELT["J_pulley"],
              "[IR] this design"))
    P.append(("counter-rotor side gear + hub", "counter", "C0", GEAR["z_cr_gear"], GEAR["m_side_kg"] + GEAR["m_hub_kg"],
              GEAR["J_side"] + GEAR["J_hub"], "[IR] this design"))
    m, j = solid(sector_area_J(GEAR["r_disc0"], SP["r_ring1"]), GEAR["t_disc"], RHO["g10"])
    P.append(("counter-rotor end disc (G10 10 mm)", "counter", "C0", 15.0, m, j, "[IR] this design, solid"))
    # the counter-rotor of record
    a, jj = vane_part("stator")
    k = M_SV / (12 * RHO["al"] * a * T_VANE * 1e-9)
    add("stator vanes (6 + 6)", "counter", None, z_of("C1 vane", "stator"), M_SV, 12 * k * RHO["al"] * jj * T_VANE * 1e-15, "[OC] geometry")
    m, j = solid(sector_area_J(SP["r_br0"], SP["r_br1"], SP["br_deg"]), SP["L"], RHO["sife"])
    add("bridges (6 + 6)", "counter", None, z_of("w bridge"), 12 * m, 12 * j, "[OC] geometry of the pick")
    m1, j1 = solid(sector_area_J(SP["r_ring0"], SP["r_ring1"]), L_RING, RHO["g10"])
    m2, j2 = solid(sector_area_J(SP["r_ring0"] - 1.0, SP["r_br1"], SP["br_deg"]), SP["L"], RHO["g10"])
    add("G10 bridge rings (1 + 1, less the pockets)", "counter", None, z_of("w ring"), 2 * (m1 - 6 * m2), 2 * (j1 - 6 * j2),
        "[IR] as modelled (25 mm wall)")
    m, j = solid(sector_area_J(BRG["od"] / 2, R_OUT + 12.0), BRG["spider_t"], RHO["g10"])
    add("G10 bearing spiders (2 + 2), solid", "counter", None, Z_SPIDERS_A, 4 * m, 4 * j, "[IR] as modelled (solid discs)")
    m, j = solid(sector_area_J(R_CAGE0, R_CAGE1), L_CAGE, RHO["g10"])
    add("G10 stator cage", "counter", None, 0.5 * (Z_CAGE0 + zc), m, j, "[IR] as modelled")
    return P, ut


# ===================================================================================== the drive's geometry (choices)
# the gear: a straight bevel reverser, the classic differential with its carrier held by the frame [IR]
GEAR = dict(m=2.0, z_s=30, z_p=20, N_p=3, b=12.0, alpha_deg=20.0,
            side_mat="austenitic stainless 1.4305", pinion_mat="POM-C",
            r_disc0=30.0, t_disc=10.0,                                 # the counter-rotor's end disc (G10)
            m_side_kg=0.30, m_hub_kg=0.25, m_pinion_kg=0.035)          # [IR] blank masses
GEAR["J_side"] = GEAR["m_side_kg"] * (0.0125 ** 2 + 0.030 ** 2) / 2   # [IR] a ring r 12.5-30
GEAR["J_hub"] = GEAR["m_hub_kg"] * (0.0125 ** 2 + 0.040 ** 2) / 2
BELT = dict(profile="HTD 5M", pitch=5.0, z_motor=20, z_machine=80, width=15.0, L_belt=750.0,
            m_pulley_kg=0.50)                                         # [IR] Al pulley with a taper bush
BELT["J_pulley"] = BELT["m_pulley_kg"] * (0.5 * BELT["z_machine"] * BELT["pitch"] / math.pi * 1e-3) ** 2 * 0.6
MOTOR = dict(kind="brushless DC servo-class, 48 V, with a speed-loop driver", P_rated=200.0, n_rated=3000.0,
             T_rated=0.64, T_peak_factor=3.0, I_lim_factor=1.5, J=3.5e-5, eta=0.80)   # [IR] catalogue-class;
#                the driver's current limit is set at 1.5 x rated: the 15 mm belt's catalogue-class rating at the limit
ETA_MESH, ETA_BELT = 0.97, 0.97                                       # [IR] stainless-POM greased; synchronous belt
P_WIND = cite("windage allowance at 600 rpm each way", 25.0, "W", "this study: a stated margin, pending the separate "
              "windage estimate", "[RH]")
WIND_REL_SHARE = 0.8                     # [RH] inside the cage (vanes, utrons / bridges) vs the cage's outside
F0_BRG, NU_GREASE = 1.0, 100.0           # [IR] SKF-class: f0 for a run-in, greased deep-groove bearing; base oil cSt
C_6205, C0_6205, DM_6205 = 14.8e3, 7.8e3, 38.5   # [IR] catalogue 6205: C, C0 (N), mean diameter (mm)
C_6000, C0_6000, DM_6000 = 4.55e3, 1.96e3, 18.0  # [IR] catalogue 6000
T_RUNUP_TARGET = 30.0                    # s, the target ramp; the motor's limit sets the actual [IR]
Z_SHAFT_END = -132.0                     # mm, the shaft's drive end (the stack-up below)


def bevel_geometry():
    """straight bevel, shaft angle 90 deg, equal-addendum teeth; mean-section virtual spur gear [OC: geometry]."""
    g = GEAR
    m, zs, zp, b = g["m"], g["z_s"], g["z_p"], g["b"]
    dia_s, dia_p = m * zs, m * zp
    delta_s = math.atan2(zs, zp)                                   # side gear pitch angle
    delta_p = math.pi / 2 - delta_s
    Re = 0.5 * m * math.hypot(zs, zp)
    Rm = Re - b / 2
    mm = m * Rm / Re
    dia_ms, dia_mp = dia_s * Rm / Re, dia_p * Rm / Re
    zvs, zvp = zs / math.cos(delta_s), zp / math.cos(delta_p)
    dia_vs, dia_vp = dia_ms / math.cos(delta_s), dia_mp / math.cos(delta_p)
    al = math.radians(g["alpha_deg"])
    ra_s, ra_p = dia_vs / 2 + mm, dia_vp / 2 + mm                    # equal addendum h_a = m at the mean section
    rb_s, rb_p = dia_vs / 2 * math.cos(al), dia_vp / 2 * math.cos(al)
    a_v = (dia_vs + dia_vp) / 2
    eps = (math.sqrt(ra_s ** 2 - rb_s ** 2) + math.sqrt(ra_p ** 2 - rb_p ** 2) - a_v * math.sin(al)) / (math.pi * mm * math.cos(al))
    tip_s, tip_p = dia_s + 2 * m * math.cos(delta_s), dia_p + 2 * m * math.cos(delta_p)
    assembly = (2 * zs) % g["N_p"] == 0                        # two equal side gears, N equally spaced pinions
    return dict(dia_side=dia_s, dia_pinion=dia_p, delta_side_deg=math.degrees(delta_s), delta_pinion_deg=math.degrees(delta_p), R_e=Re,
                R_m=Rm, m_m=mm, dia_m_side=dia_ms, dia_m_pinion=dia_mp, r_m_side=dia_ms / 2, z_v_side=zvs, z_v_pinion=zvp,
                dia_v_side=dia_vs, dia_v_pinion=dia_vp, u_v=zvs / zvp, eps_alpha=eps, tip_dia_side=tip_s, tip_dia_pinion=tip_p,
                b_over_Re=b / Re, assembly_ok=assembly, ratio_side_to_pinion=zs / zp,
                pinion_rpm=RPM_BODY * zs / zp, mesh_Hz=zs * RPM_BODY / 60.0,
                apex_to_side_pitch_circle=Re * math.cos(delta_s), apex_to_pinion_pitch_circle=Re * math.cos(delta_p))


def stackup(bg):
    """the frame end (side A, below): z of every part of the drive, from the old end-bearing slot (z 0..20, the frame
    spider of record) downward [IR]. The counter-rotor's bridge ring A ends at z 20 (the tube model)."""
    back = 8.0                                                 # [IR] side gear's back behind its outer pitch circle
    mount = bg["apex_to_side_pitch_circle"] + back             # apex to the side gear's mounting face
    hub_h = 18.0                                               # [IR] the counter-rotor's hub: the 6205 + a flange
    z_disc = (10.0, 20.0)                                      # the counter-rotor's end disc under the ring
    z_apex = z_disc[0] - hub_h - mount
    z_case_floor = z_apex - mount - 12.0 - 3.0                 # the rotor's side gear hub (12) and a gap (3)
    Ri = bg["R_e"] - GEAR["b"]                                 # the inner end of the face, from the apex
    inner = Ri * math.cos(math.radians(bg["delta_side_deg"])) - GEAR["m"] * Ri / bg["R_e"] * math.sin(
        math.radians(bg["delta_side_deg"]))                    # the side gear's tooth tip at the inner end
    s = [("counter-rotor end disc (G10 10 mm, bolted to bridge ring A; the bottom spider re-purposed)", z_disc[0],
          z_disc[1]),
         ("counter-rotor hub with the gear-end inner bearing 6205-2Z", z_disc[0] - hub_h, z_disc[0]),
         ("counter-rotor side gear z 30 (bolted under the hub)", z_apex + inner, z_apex + mount),
         ("pinion plane: 3 x POM pinion z 20 on radial axes (envelope of the tips)", z_apex - bg["tip_dia_pinion"] / 2,
          z_apex + bg["tip_dia_pinion"] / 2),
         ("rotor side gear z 30 with its hub (keyed in the hub, Ø 25 journal)", z_apex - mount - 12.0, z_apex - inner),
         ("gear case floor with the locating end bearing 6205-2Z (frame)", z_case_floor - 17.0, z_case_floor),
         ("machine pulley HTD 5M 80T, 15 mm belt (24 mm over flanges)", z_case_floor - 17.0 - 6.0 - 24.0,
          z_case_floor - 17.0 - 6.0),
         ("shaft end with lock nut", Z_SHAFT_END, z_case_floor - 17.0 - 6.0 - 24.0),
         ("base plate (20 mm) under the case's bell", Z_SHAFT_END - 4.0 - 20.0, Z_SHAFT_END - 4.0)]
    rows = [dict(part=p, z0=round(a, 1), z1=round(b, 1)) for p, a, b in s]
    pinion_outer_r = bg["apex_to_pinion_pitch_circle"] + 8.0   # the pinion's back face
    case_r = pinion_outer_r + 2 * 8.0 + 4.0 + 6.0 + 8.0        # 2 x 6000 bearings, spacer, cap, wall [IR]
    return dict(rows=rows, z_apex=z_apex, z_rotor_gear=z_apex - mount + 6.0, z_cr_gear=z_apex + mount - 6.0,
                z_pulley=z_case_floor - 35.0, z_base_bottom=Z_SHAFT_END - 24.0, case_outer_r=case_r,
                pinion_back_r=pinion_outer_r, added_below_slot_mm=-(Z_SHAFT_END - 24.0),
                overall_height_mm=(L_TUBE + 20.0) - (Z_SHAFT_END - 24.0),
                note="z from the record's bottom end-bearing slot (z 0..20, now the counter-rotor's end disc and hub); "
                     "the tube's top end bearing at z 920..940 with a 20 mm top plate above it")


# ========================================================================================== 2. drags and the budget
def m_bearing(rpm, dia_m, C0, P1=50.0, f0=F0_BRG):
    """frictional moment (N m) of a greased deep-groove ball bearing, SKF-class (M0 + M1) [IR]."""
    vn = NU_GREASE * rpm
    M0 = (1e-7 * f0 * vn ** (2 / 3) if vn >= 2000 else 160e-7 * f0) * dia_m ** 3
    M1 = 0.0007 * math.sqrt(max(P1, 1.0) / C0) * P1 * dia_m
    return (M0 + M1) * 1e-3


def budget(P_wind=P_WIND, pumps=True, mag=True, w_body=W_BODY):
    """steady torques (N m) at body speed w_body: what acts between the bodies, on each against the frame, through the
    gear, on the belt [OC: the balance; IR: the drag models]."""
    rpm = w_body * 60 / (2 * math.pi)
    s = w_body / W_BODY
    T_pump = ((P_MAG + P_FE) * (1 if mag else 0) + P_ES) / W_REL if pumps else 0.0   # constant in speed [OC]
    T_brg_in = 5 * m_bearing(2 * rpm, DM_6205, C0_6205, P1=20.0, f0=F0_BRG)
    T_wind_rel = WIND_REL_SHARE * P_wind / W_REL * s ** 2      # windage ~ w^3 in power [OC scaling, RH level]
    T_rel = T_pump + T_brg_in + T_wind_rel
    D_c = (1 - WIND_REL_SHARE) * P_wind / W_BODY * s ** 2
    D_r = m_bearing(rpm, DM_6205, C0_6205, P1=0.9 * W_ALL) + m_bearing(rpm, DM_6205, C0_6205, P1=10.0)
    T_pin_brg = GEAR["N_p"] * 2 * m_bearing(rpm * GEAR["z_s"] / GEAR["z_p"], DM_6000, C0_6000, P1=10.0) * GEAR["z_s"] / GEAR["z_p"]
    tau_c = T_rel + D_c                                        # the gear's torque on the counter-rotor
    tau_r = tau_c / ETA_MESH ** 2 + T_pin_brg                  # the gear's torque on the rotor
    T_belt = T_rel + D_r + tau_r                               # at the machine pulley (rotor)
    return dict(T_pump=T_pump, T_brg_inner=T_brg_in, T_wind_rel=T_wind_rel, T_rel=T_rel, D_c=D_c, D_r=D_r,
                T_pinion_brg=T_pin_brg, tau_gear_cr=tau_c, tau_gear_rotor=tau_r, T_carrier=tau_c + tau_r,
                T_belt=T_belt, P_belt=T_belt * w_body, P_motor_shaft=T_belt * w_body / ETA_BELT,
                P_elec=T_belt * w_body / ETA_BELT / MOTOR["eta"],
                P_split=dict(pumps=T_pump * 2 * w_body, inner_bearings=T_brg_in * 2 * w_body,
                             windage=(T_wind_rel * 2 + D_c) * w_body, end_bearings=D_r * w_body,
                             gear=(tau_r - tau_c) * w_body))


# ============================================================================================== 3. the pulsation
def magnetic_wave(no_spice):
    """complex harmonics (N m, n = 1..) of the magnetic pump's torque on side A and side B, phase 0 = group A aligned;
    from the deck of record re-run in ngspice (the pick, sim/rotor_parts_duty.py _kw, with sim/ah_steady_cusp.py's
    22 mF bypass) [OC: the circuit; IR: the deck's models]."""
    if no_spice or shutil.which("ngspice") is None:
        if os.path.exists(OUT):
            old = json.load(open(OUT))["pulsation"]["magnetic"]
            hA = [complex(*z) for z in old["harmonics_A"]]
            hB = [complex(*z) for z in old["harmonics_B"]]
            return hA, hB, dict(old, source="reused from the previous sim/drive_sizing_results.json (no ngspice run)")
        return None, None, dict(note="ngspice not available and no stored harmonics: the magnetic pulsation is skipped")
    import magnetic_doubler as M
    import rotor_parts_duty as RP
    import ah_steady_cusp as AC
    kw = RP._kw(RP.TAU_FIXED)
    txt, vecs, info = M.deck(**kw)
    c_mf = 22.0
    byp = [f"R_bypA x1 xb1 {AC.ESR:g}", f"C_bypA xb1 d {c_mf * 1e-3:g}",
           f"R_bypB x2 xb2 {AC.ESR:g}", f"C_bypB xb2 b {c_mf * 1e-3:g}"]
    txt = txt.replace("D1s f2 b ND", "\n".join(byp) + "\nD1s f2 b ND")
    with tempfile.TemporaryDirectory() as tmp:
        open(os.path.join(tmp, "x.cir"), "w").write(txt)
        subprocess.run(["ngspice", "-b", "x.cir"], capture_output=True, text=True, timeout=3600, cwd=tmp)
        raw = np.loadtxt(os.path.join(tmp, "out.dat"))
    t = raw[:, 0]
    c = {v: raw[:, 2 * j + 1] for j, v in enumerate(vecs)}
    m = M.analyse(t, c, info, kw)
    T = 1.0 / kw["F"]
    n_cyc = kw["n_cyc"]
    pA = np.gradient(c["v(e_mech_L1)"], t) / W_REL             # instantaneous torque on the relative motion [OC]
    pB = np.gradient(c["v(e_mech_L2)"], t) / W_REL
    N = 4 * 512
    tu = (n_cyc - 4) * T + np.arange(N) * 4 * T / N            # the last 4 cycles; (n_cyc - 4) T is a cycle boundary
    yA, yB = np.interp(tu, t, pA), np.interp(tu, t, pB)
    FA, FB = np.fft.rfft(yA) / N, np.fft.rfft(yB) / N
    nh = 12
    hA = [2 * FA[4 * n] for n in range(1, nh + 1)]
    hB = [2 * FB[4 * n] for n in range(1, nh + 1)]
    tot = yA + yB
    info = dict(source="ngspice: the pick (sim/rotor_parts_duty.py _kw) + 22 mF bypass (sim/ah_steady_cusp.py)",
                P_belt_W=m["P_belt_W"], z_early=m["z_early"], mean_A=float(yA.mean()), mean_B=float(yB.mean()),
                total_max=float(tot.max()), total_min=float(tot.min()), A_max=float(yA.max()), A_min=float(yA.min()),
                B_max=float(yB.max()), B_min=float(yB.min()),
                harmonics_A=[[z.real, z.imag] for z in hA], harmonics_B=[[z.real, z.imag] for z in hB],
                amp_total=[abs(a + b) for a, b in zip(hA, hB)], amp_diff=[abs(a - b) for a, b in zip(hA, hB)])
    return hA, hB, info


def electrostatic_wave():
    """complex harmonics of the electrostatic pump's torque, side A (C1, node 1) and B (C2, node 4), phase 0 = C1 at
    maximum: T = -1/2 V^2 dC/dtheta_rel from the one-revolution record [OC]."""
    h = load("sim/hub_revolution_results.json")
    th = np.radians(np.array(h["rotor_deg"]))                  # the rotor's angle; relative = 2 x (1 : -1 gear)
    C1, C2 = np.array(h["C1_pF"]) * 1e-12, np.array(h["C2_pF"]) * 1e-12
    V1, V4 = np.array(h["V_kV"]["1"]) * 1e3, np.array(h["V_kV"]["4"]) * 1e3
    dth = 2 * (th[1] - th[0])
    dia1 = (np.roll(C1, -1) - np.roll(C1, 1)) / (2 * dth)        # periodic over the revolution
    dia2 = (np.roll(C2, -1) - np.roll(C2, 1)) / (2 * dth)
    yA, yB = -0.5 * V1 ** 2 * dia1, -0.5 * V4 ** 2 * dia2
    N = len(th)
    FA, FB = np.fft.rfft(yA) / N, np.fft.rfft(yB) / N          # 12 pump cycles in the record
    nh = 12
    hA = [2 * FA[12 * n] for n in range(1, nh + 1)]
    hB = [2 * FB[12 * n] for n in range(1, nh + 1)]
    tot = yA + yB
    return hA, hB, dict(source="sim/hub_revolution_results.json (C1, C2, V1, V4 over one revolution)",
                        mean_W=float(tot.mean() * W_REL), mean_A=float(yA.mean()), mean_B=float(yB.mean()),
                        total_max=float(tot.max()), total_min=float(tot.min()), A_max=float(yA.max()),
                        A_min=float(yA.min()), amp_total=[abs(a + b) for a, b in zip(hA, hB)],
                        amp_diff=[abs(a - b) for a, b in zip(hA, hB)])


DOF = ["M", "R0", "RA", "RB", "C0", "CA", "CB"]
ETA_STRUCT = 0.03                                              # [RH] loss factor of every spring (G10, POM, joints)


def mesh_stiffness(pinion_mat):
    """the reverser's torsional stiffness in its gear mode (N m/rad): N pinions, two meshes in series per pinion, at the
    side gear's mean radius. c_gamma 20 N/(mm um) steel-steel spur x 0.85 for bevels (ISO 6336 / 10300 class) [IR];
    a polymer member scales it by 2 E_p / E_s [OC: springs in series]."""
    bg = bevel_geometry()
    c = 20.0 * 0.85
    if pinion_mat == "POM-C":
        c *= 2 * 2.8 / 193.0                                   # POM-C 2.8 GPa against stainless 193 GPa [IR]
    k_mesh = c * GEAR["b"] * 1e6                               # N/m per mesh
    r = bg["r_m_side"] * 1e-3
    return GEAR["N_p"] * (k_mesh / 2) * r * r, k_mesh


def torsion_model(P, gear_k, g_g10=None):
    """M, K (real) of the 7-inertia chain: motor -(belt)- R0 -(shaft)- RA -(shaft + hub)- RB; C0 -(end disc + ring)- CA
    -(cage)- CB; the gear couples R0 and C0 with theta_R0 + theta_C0 = 0 (reversing) [IR]."""
    G_G10_ = G_G10 if g_g10 is None else g_g10
    J = {k: 0.0 for k in DOF}
    zJ = {k: 0.0 for k in DOF}
    for name, body, st, z, m, j, tag in P:
        J[st] += j; zJ[st] += j * z
    z = {k: (zJ[k] / J[k] if J[k] > 0 else 0.0) for k in DOF}
    z["R0"], z["C0"] = GEAR["z_rotor_gear"], GEAR["z_cr_gear"]                # the springs start at the meshes
    J["M"] = MOTOR["J"] * (BELT["z_machine"] / BELT["z_motor"]) ** 2          # referred to the machine pulley
    Jp = math.pi / 32 * (2 * R_SHAFT * 1e-3) ** 4
    GJs = G_SS * Jp
    zc = L_TUBE / 2.0
    k_0A = GJs / ((z["RA"] - z["R0"]) * 1e-3)
    k_hub = 3.0e4                                               # [RH] flanges, G10 coupler and PEEK retainer
    l_AB = ((zc - HUB_FLANGE_ABSZ[1]) - z["RA"]) + (z["RB"] - (zc + HUB_FLANGE_ABSZ[1]))
    k_AB = 1.0 / (l_AB * 1e-3 / GJs + 1.0 / k_hub)
    r_i, r_o = GEAR["r_disc0"] * 1e-3, SP["r_ring0"] * 1e-3
    k_disc = 4 * math.pi * G_G10_ * GEAR["t_disc"] * 1e-3 / (1 / r_i ** 2 - 1 / r_o ** 2)   # annulus in shear [OC]
    J_ring = math.pi / 2 * ((SP["r_ring1"] * 1e-3) ** 4 - (SP["r_ring0"] * 1e-3) ** 4)
    k_ring = G_G10_ * J_ring / max((z["CA"] - 20.0) * 1e-3, 0.02)
    k_0Ac = 1.0 / (1 / k_disc + 1 / k_ring)
    J_cage = math.pi / 2 * ((R_CAGE1 * 1e-3) ** 4 - (R_CAGE0 * 1e-3) ** 4)
    k_cAB = G_G10_ * J_cage / ((z["CB"] - z["CA"]) * 1e-3)
    bl = belt_geometry()
    k_belt = 2 * bl["EA_N"] / (bl["span_mm"] * 1e-3) * (bl["dia_machine_mm"] / 2 * 1e-3) ** 2
    idx = {k: i for i, k in enumerate(DOF)}
    K = np.zeros((7, 7))

    def spring(a, b, k, sign=-1.0):
        i, j = idx[a], idx[b]
        K[i, i] += k; K[j, j] += k; K[i, j] += sign * k; K[j, i] += sign * k
    spring("M", "R0", k_belt)
    spring("R0", "RA", k_0A)
    spring("RA", "RB", k_AB)
    spring("C0", "CA", k_0Ac)
    spring("CA", "CB", k_cAB)
    spring("R0", "C0", gear_k, sign=+1.0)                      # energy 1/2 k (theta_R0 + theta_C0)^2
    Mm = np.diag([J[k] for k in DOF])
    springs = dict(belt=k_belt, shaft_gear_to_A=k_0A, shaft_A_to_B_with_hub=k_AB, hub_joint=k_hub,
                   cr_end_disc_and_ring=k_0Ac, cage_A_to_B=k_cAB, gear=gear_k)
    return Mm, K, J, z, springs


def modes(Mm, K, springs):
    """undamped modes; each with its shape and the share of its strain energy in each spring (which one it 'is')."""
    w2, V = np.linalg.eig(np.linalg.solve(Mm, K))
    w2 = np.real(w2)
    order = np.argsort(w2)
    idx = {k: i for i, k in enumerate(DOF)}
    pairs = dict(belt=("M", "R0", -1), shaft_gear_to_A=("R0", "RA", -1), shaft_A_to_B_with_hub=("RA", "RB", -1),
                 cr_end_disc_and_ring=("C0", "CA", -1), cage_A_to_B=("CA", "CB", -1), gear=("R0", "C0", +1))
    out = []
    for i in order:
        if w2[i] > 1e-6:
            v = np.real(V[:, i]); v = v / np.max(np.abs(v))
            e = {k: springs[k] * (v[idx[a]] + sg * v[idx[b]]) ** 2 for k, (a, b, sg) in pairs.items()}
            tot = sum(e.values()) or 1.0
            share = {k: round(x / tot, 3) for k, x in e.items()}
            out.append(dict(f_Hz=math.sqrt(w2[i]) / (2 * math.pi), shape={k: round(float(x), 3) for k, x in zip(DOF, v)},
                            energy_share=share, mainly=max(share, key=share.get)))
    return out


def forced(Mm, K, hA, hB, n_list, gear_k, k_AB, k_cAB, k_belt):
    """per harmonic n of 120 Hz: the complex amplitudes of the gear's torque on each body (-k phi), the hub joint, the
    cage and the belt. The pumps act -T on the rotor's side station and +T on the counter-rotor's [OC]."""
    idx = {k: i for i, k in enumerate(DOF)}
    res = []
    for n, a, b in zip(n_list, hA, hB):
        w = 2 * math.pi * F_PUMP * n
        A = K * (1 + 1j * ETA_STRUCT) - w * w * Mm
        Fv = np.zeros(7, dtype=complex)
        Fv[idx["RA"]] -= a; Fv[idx["CA"]] += a
        Fv[idx["RB"]] -= b; Fv[idx["CB"]] += b
        X = np.linalg.solve(A, Fv)
        kc = 1 + 1j * ETA_STRUCT
        res.append(dict(n=n, gear=-gear_k * kc * (X[idx["R0"]] + X[idx["C0"]]),
                        hub=k_AB * kc * (X[idx["RA"]] - X[idx["RB"]]),
                        cage=k_cAB * kc * (X[idx["CA"]] - X[idx["CB"]]),
                        belt=k_belt * kc * (X[idx["M"]] - X[idx["R0"]])))
    return res


def wave_of(res, key, n_pts=720):
    th = np.linspace(0, 2 * math.pi, n_pts, endpoint=False)
    y = np.zeros(n_pts)
    for r in res:
        y += np.real(r[key] * np.exp(1j * r["n"] * th))
    return y


def pump_peaks(hAm, hBm, hAe, hBe):
    """the pumps' torque between the bodies over one cycle (mean of record + the harmonics), worst over the
    electrostatic phase: total, side A, side B [OC]."""
    nh = len(hAe)
    th = np.linspace(0, 2 * math.pi, 1440, endpoint=False)
    mA = mB = 0.5 * P_PUMPS / W_REL
    best = None
    for ph_deg in range(0, 360, 5):
        ph = math.radians(ph_deg)
        yA = np.full_like(th, mA); yB = np.full_like(th, mB)
        for i in range(nh):
            n = i + 1
            a = (hAm[i] if hAm else 0) + hAe[i] * np.exp(1j * n * ph)
            b = (hBm[i] if hBm else 0) + hBe[i] * np.exp(1j * n * ph)
            yA += np.real(a * np.exp(1j * n * th)); yB += np.real(b * np.exp(1j * n * th))
        tot = yA + yB
        row = dict(phase_deg=ph_deg, total_max=float(tot.max()), total_min=float(tot.min()), A_max=float(yA.max()),
                   A_min=float(yA.min()), mean=float(tot.mean()))
        if best is None or row["total_max"] - row["total_min"] > best["total_max"] - best["total_min"]:
            best = row
    return best


def pulsation(P, hAm, hBm, hAe, hBe, mean):
    """the pulsating torques the drive carries, for stainless / POM and stainless / stainless meshes, over a scan of the
    electrostatic pump's phase against the magnetic one (their clocking is not documented) [IR]."""
    out = {}
    nh = len(hAe)
    for mat in ("POM-C", "stainless"):
        k_g, k_mesh = mesh_stiffness(mat)
        Mm, K, J, z, spr = torsion_model(P, k_g)
        md = modes(Mm, K, spr)
        worst = None
        for ph_deg in range(0, 360, 15):
            ph = math.radians(ph_deg)
            A = [(hAm[i] if hAm else 0) + hAe[i] * np.exp(1j * (i + 1) * ph) for i in range(nh)]
            B = [(hBm[i] if hBm else 0) + hBe[i] * np.exp(1j * (i + 1) * ph) for i in range(nh)]
            res = forced(Mm, K, A, B, list(range(1, nh + 1)), k_g, spr["shaft_A_to_B_with_hub"], spr["cage_A_to_B"],
                         spr["belt"])
            g = wave_of(res, "gear")
            row = dict(phase_deg=ph_deg, gear_osc_max=float(g.max()), gear_osc_min=float(g.min()),
                       gear_pp=float(g.max() - g.min()),
                       hub_pp=float(np.ptp(wave_of(res, "hub"))), cage_pp=float(np.ptp(wave_of(res, "cage"))),
                       belt_pp=float(np.ptp(wave_of(res, "belt"))),
                       gear_by_harmonic=[abs(r["gear"]) for r in res])
            if ph_deg == 0:
                at0 = row
            if worst is None or row["gear_pp"] > worst["gear_pp"]:
                worst = row
        tau_mean = -mean["tau_gear_cr"]                         # the gear's mean torque on each body (driving sense < 0)
        reverses = (tau_mean + worst["gear_osc_max"]) > 0
        Jr = J["R0"] + J["RA"] + J["RB"]; Jc = J["C0"] + J["CA"] + J["CB"]
        rigid = abs(Jr - Jc) / (Jr + Jc)
        path = lambda m_: m_["energy_share"]["gear"] + m_["energy_share"]["shaft_gear_to_A"] + m_["energy_share"]["cr_end_disc_and_ring"]
        gp = [m_ for m_ in md if path(m_) >= 0.45]
        # the cage's A-B torsion near the 3rd harmonic: its sensitivity to G10's shear modulus [RH]
        cage = []
        for gg in (3e9, 5e9, 10e9):
            Mm2, K2, _, _, spr2 = torsion_model(P, k_g, g_g10=gg)
            ph = math.radians(worst["phase_deg"])
            A = [(hAm[i] if hAm else 0) + hAe[i] * np.exp(1j * (i + 1) * ph) for i in range(nh)]
            B = [(hBm[i] if hBm else 0) + hBe[i] * np.exp(1j * (i + 1) * ph) for i in range(nh)]
            r2 = forced(Mm2, K2, A, B, list(range(1, nh + 1)), k_g, spr2["shaft_A_to_B_with_hub"], spr2["cage_A_to_B"],
                        spr2["belt"])
            fc = [m_["f_Hz"] for m_ in modes(Mm2, K2, spr2) if m_["mainly"] == "cage_A_to_B"]
            cage.append(dict(G_GPa=gg / 1e9, cage_mode_Hz=fc[0] if fc else None, cage_pp_Nm=float(np.ptp(wave_of(r2, "cage"))),
                             gear_pp_Nm=float(np.ptp(wave_of(r2, "gear")))))
        out[mat] = dict(k_mesh_N_per_m=k_mesh, k_gear_Nm_per_rad=k_g, springs=spr, J_station=J, z_station_mm=z,
                        modes=md, at_phase_0=at0, worst=worst, tau_mean_on_each_body=tau_mean,
                        flank_reversal=bool(reverses), rigid_gear_share=rigid,
                        gear_mode_Hz=[max(md, key=lambda m_: m_["energy_share"]["gear"])["f_Hz"]],
                        gear_path_mode_Hz=gp[0]["f_Hz"] if gp else None, cage_vs_G10=cage)
    return out


def windage_crosscheck():
    """a crude cross-check of the windage allowance, not used in the sizing [RH]: the 12 rotor vanes as full discs
    between stator vanes 6 mm away (enclosed disc, laminar separate boundary layers, Daily & Nece regime II:
    C_M = 3.7 (s/R)^0.1 Re^-0.5 for both faces) at the relative speed, and the cage's outside as a turbulent
    flat plate (C_f = 0.074 Re^-0.2) at 600 rpm in still air."""
    rho, nu = 1.2, 1.5e-5
    Rv, gap = R_OUT * 1e-3, 6e-3
    Re = W_REL * Rv ** 2 / nu
    CM = 3.7 * (gap / Rv) ** 0.1 * Re ** -0.5
    T_vane = 0.5 * CM * rho * W_REL ** 2 * Rv ** 5
    v = W_BODY * R_CAGE1 * 1e-3
    ReL = v * L_CAGE * 1e-3 / nu
    Cf = 0.074 * ReL ** -0.2
    T_cage = 0.5 * rho * v * v * Cf * math.pi * 2 * R_CAGE1 * 1e-3 * L_CAGE * 1e-3 * R_CAGE1 * 1e-3
    P_v, P_c = 12 * T_vane * W_REL, T_cage * W_BODY
    return dict(Re_vane=Re, C_M=CM, P_vanes_W=P_v, P_cage_outside_W=P_c, P_total_W=P_v + P_c,
                allowance_over_estimate=P_WIND / (P_v + P_c),
                note="crude [RH]: the sectors' churning, the utron cavities and the Ca / Cb plates are not in it")


def selfcheck_rigid_limit():
    """the torsional solver against the closed form: with a near-rigid gear and rigid bodies the gear carries
    (J_c - J_r) / (J_r + J_c) of the pumps' summed pulsation, and nothing for equal inertias [OC]."""
    idx = {k: i for i, k in enumerate(DOF)}
    out = []
    for Jr, Jc in ((0.5, 0.5), (0.288, 0.670)):
        J = dict(M=1e-3, R0=1e-4, RA=Jr / 2, RB=Jr / 2, C0=1e-4, CA=Jc / 2, CB=Jc / 2)
        Mm = np.diag([J[k] for k in DOF])
        K = np.zeros((7, 7))

        def spring(a, b, k, sign=-1.0):
            i, j = idx[a], idx[b]
            K[i, i] += k; K[j, j] += k; K[i, j] += sign * k; K[j, i] += sign * k
        spring("M", "R0", 1.0)
        for a, b in (("R0", "RA"), ("RA", "RB"), ("C0", "CA"), ("CA", "CB")):
            spring(a, b, 1e9)
        spring("R0", "C0", 1e8, +1.0)
        global ETA_STRUCT
        keep, ETA_STRUCT = ETA_STRUCT, 1e-6
        g = abs(forced(Mm, K, [1.0], [1.0], [2], 1e8, 1.0, 1.0, 1.0)[0]["gear"])
        ETA_STRUCT = keep
        out.append(dict(J_r=Jr, J_c=Jc, gear_share=g / 2.0, closed_form=abs(Jc - Jr) / (Jr + Jc)))
    return out


# ================================================================================================ 4. the run-up
def runup(J_bodies, J_c, J_mot_ref, mag_on, t_target=T_RUNUP_TARGET, lim=1.0, P_wind=P_WIND):
    """from rest to 600 rpm each way: the speed loop follows a linear ramp (600 rpm in t_target) unless the driver's
    torque limit (lim x rated) holds it back [IR]. The belt carries the bodies' inertia and the drags; the motor's own
    inertia stays on the motor side. Returns the time and the peak gear, belt and motor torques."""
    i_b = BELT["z_machine"] / BELT["z_motor"]
    T_drive_max = lim * MOTOR["T_rated"] * i_b * ETA_BELT      # at the machine pulley
    alpha_ramp = W_BODY / t_target
    w, t, dt = 0.0, 0.0, 0.005
    peak_g = peak_b = P_peak = 0.0
    limited = False
    while w < W_BODY and t < 900:
        b = budget(P_wind=P_wind, pumps=True, mag=mag_on, w_body=max(w, 1e-3))
        T_load = b["T_belt"]
        a_lim = (T_drive_max - T_load) / (J_bodies + J_mot_ref)
        alpha = min(a_lim, alpha_ramp)
        limited = limited or a_lim < alpha_ramp
        if alpha <= 0:
            return dict(t_s=None, reached=False, w_max=w)
        peak_g = max(peak_g, b["tau_gear_cr"] + J_c * alpha)
        T_b = T_load + J_bodies * alpha
        peak_b = max(peak_b, T_b)
        P_peak = max(P_peak, (T_b + J_mot_ref * alpha) * w / ETA_BELT)
        w += alpha * dt; t += dt
    return dict(t_s=t, reached=True, t_target_s=t_target, torque_limited=limited, peak_gear_Nm=peak_g,
                peak_belt_Nm=peak_b, peak_motor_Nm=(peak_b + J_mot_ref * alpha_ramp) / (i_b * ETA_BELT),
                peak_motor_shaft_W=P_peak, mag_on=mag_on, limit_x_rated=lim)


# ================================================================================================= 5. the gear
POM = dict(E=2.8e3, nu=0.35, sF_fat=20.0, sF_short=45.0, sH_fat=36.0, sH_short=60.0)       # MPa, VDI 2736-class [IR]
SS_ = dict(E=193e3, nu=0.29, sF_fat=120.0, sF_short=250.0, sH_fat=350.0, sH_short=600.0)   # 1.4305, unhardened [IR]
LEWIS_Y = [(12, 0.245), (13, 0.261), (14, 0.277), (15, 0.290), (16, 0.296), (17, 0.303), (18, 0.309), (19, 0.314),
           (20, 0.322), (21, 0.328), (22, 0.331), (24, 0.337), (26, 0.346), (28, 0.353), (30, 0.359), (34, 0.371),
           (38, 0.384), (43, 0.397), (50, 0.409), (60, 0.422), (75, 0.435), (100, 0.447), (150, 0.460), (300, 0.472)]
K_O, K_M, K_GAMMA, Y_M_IDLER, Z_K = 1.25, 1.3, 1.2, 0.7, 0.85   # [IR] AGMA / ISO-class factors


def lewis_y(z):
    for (z0, y0), (z1, y1) in zip(LEWIS_Y, LEWIS_Y[1:]):
        if z0 <= z <= z1:
            return y0 + (y1 - y0) * (z - z0) / (z1 - z0)
    return LEWIS_Y[-1][1]


def k_v(v_mps, Qv=8):
    """AGMA dynamic factor [IR]."""
    B = 0.25 * (12 - Qv) ** (2 / 3)
    A = 50 + 56 * (1 - B)
    return ((A + math.sqrt(200 * v_mps)) / A) ** B


def gear_check(tau, case, fatigue):
    """bending (Lewis, AGMA-class factors) and contact (Hertz on the virtual spur pair at the mean section) per mesh,
    for the gear's torque tau on a side gear (N m) [IR]."""
    bg = bevel_geometry()
    r_m = bg["r_m_side"] * 1e-3
    Ft = abs(tau) * K_GAMMA / (GEAR["N_p"] * r_m)              # N per mesh, with the load-sharing factor
    v = W_BODY * r_m
    Kv = k_v(v)
    K = K_O * Kv * K_M
    b, mm = GEAR["b"], bg["m_m"]
    sF_p = Ft * K / (b * mm * lewis_y(bg["z_v_pinion"]))
    sF_s = Ft * K / (b * mm * lewis_y(bg["z_v_side"]))
    ZE = math.sqrt(1 / (math.pi * ((1 - POM["nu"] ** 2) / POM["E"] + (1 - SS_["nu"] ** 2) / SS_["E"])))
    al = math.radians(GEAR["alpha_deg"])
    ZH = math.sqrt(2 / (math.cos(al) ** 2 * math.tan(al)))
    Ze = math.sqrt((4 - bg["eps_alpha"]) / 3)
    u = bg["u_v"]
    sH = ZE * ZH * Ze * Z_K * math.sqrt(Ft * K / (b * bg["dia_v_pinion"]) * (u + 1) / u)
    lim_p = (POM["sF_fat"] * Y_M_IDLER, POM["sH_fat"]) if fatigue else (POM["sF_short"], POM["sH_short"])
    lim_s = (SS_["sF_fat"] * Y_M_IDLER, SS_["sH_fat"]) if fatigue else (SS_["sF_short"], SS_["sH_short"])
    return dict(case=case, tau_Nm=abs(tau), F_t_per_mesh_N=Ft, K_v=Kv, sigma_F_pinion_MPa=sF_p, S_F_pinion=lim_p[0] / sF_p,
                sigma_F_side_MPa=sF_s, S_F_side=lim_s[0] / sF_s, sigma_H_MPa=sH, S_H_pinion=lim_p[1] / sH,
                S_H_side=lim_s[1] / sH, Z_E=ZE, limits_pinion=lim_p, limits_side=lim_s,
                fatigue=fatigue)


def pinion_loads(tau):
    """forces on one pinion (an idler: the two meshes push its axle the same way, 2 F_t) and its two 6000 bearings,
    16 mm apart, the mesh 12 mm outboard of the inner one [OC: statics; IR: the spacing]."""
    bg = bevel_geometry()
    Ft = abs(tau) * K_GAMMA / (GEAR["N_p"] * bg["r_m_side"] * 1e-3)
    al = math.radians(GEAR["alpha_deg"])
    dia_s, dia_p = math.radians(bg["delta_side_deg"]), math.radians(bg["delta_pinion_deg"])
    F_net = 2 * Ft                                             # tangential, perpendicular to the pinion's axis
    F_ax = 2 * Ft * math.tan(al) * math.sin(dia_p)                # the pinion's thrust outward, both meshes
    a, l = 12.0, 16.0
    R_in = F_net * (a + l) / l
    R_out = F_net * a / l
    F_side_axial = Ft * math.tan(al) * math.sin(dia_s)           # per mesh on a side gear, along the machine axis
    return dict(F_t=Ft, F_net_N=F_net, F_axial_N=F_ax, R_inner_N=R_in, R_outer_N=R_out,
                side_gear_thrust_N=GEAR["N_p"] * F_side_axial, M_axle_Nm=F_net * a * 1e-3,
                sigma_axle_MPa=32 * F_net * a * 1e-3 / (math.pi * 0.010 ** 3) / 1e6)


def l10_h(C, P, rpm):
    return (C / max(P, 1.0)) ** 3 * 1e6 / (60 * rpm)


def dg_equivalent(Fr, Fa, C0=C0_6205):
    """deep-groove equivalent load (catalogue e / X / Y interpolation) [IR]."""
    tab = [(0.014, 0.19, 2.30), (0.028, 0.22, 1.99), (0.056, 0.26, 1.71), (0.084, 0.28, 1.55), (0.11, 0.30, 1.45),
           (0.17, 0.34, 1.31), (0.28, 0.38, 1.15), (0.42, 0.42, 1.04), (0.56, 0.44, 1.00)]
    x = Fa / C0
    e, Y = tab[0][1], tab[0][2]
    for (x0, e0, y0), (x1, e1, y1) in zip(tab, tab[1:]):
        if x0 <= x <= x1:
            f = (x - x0) / (x1 - x0); e = e0 + f * (e1 - e0); Y = y0 + f * (y1 - y0)
    if x > tab[-1][0]:
        e, Y = tab[-1][1], tab[-1][2]
    if Fr > 0 and Fa / Fr <= e:
        return Fr
    return 0.56 * Fr + Y * Fa


# ================================================================================================= 6. the belt
def belt_geometry():
    """HTD 5M: pulleys, centre distance for the chosen length, wrap, teeth in mesh, speed, span [OC: geometry]."""
    p = BELT["pitch"]
    dia1 = BELT["z_motor"] * p / math.pi
    dia2 = BELT["z_machine"] * p / math.pi
    Lb = BELT["L_belt"]
    # L = 2 c + pi (dia1 + dia2) / 2 + (dia2 - dia1)^2 / (4 c)
    A_ = 2.0; B_ = math.pi * (dia1 + dia2) / 2 - Lb; C_ = (dia2 - dia1) ** 2 / 4
    c = (-B_ + math.sqrt(B_ * B_ - 4 * A_ * C_)) / (2 * A_)
    wrap = math.pi - 2 * math.asin((dia2 - dia1) / (2 * c))
    span = c * math.cos(math.asin((dia2 - dia1) / (2 * c)))
    i = BELT["z_machine"] / BELT["z_motor"]
    n_m = RPM_BODY * i
    v = math.pi * dia1 * 1e-3 * n_m / 60
    EA = 5000.0 * BELT["width"]                                # N, glass cord, catalogue-class [IR]
    return dict(dia_motor_mm=dia1, dia_machine_mm=dia2, ratio=i, motor_rpm=n_m, centre_mm=c, wrap_small_deg=math.degrees(wrap),
                teeth_in_mesh=int(BELT["z_motor"] * math.degrees(wrap) / 360), v_mps=v, span_mm=span, EA_N=EA,
                n_teeth=int(Lb / p))


def belt_check(T_motor_steady, T_motor_max):
    """width from a specific tooth load, tensions and hub loads [IR: catalogue-class values]."""
    bl = belt_geometry()
    F_tsp = 0.5                                                # N per mm of width per tooth in mesh, HTD 5M at ~4 m/s
    c2 = 1.6                                                   # service factor: start-stop, run-ups at the limit
    z_m = min(bl["teeth_in_mesh"], 6 + 2)                      # catalogues count at most ~6-8 teeth
    r1 = bl["dia_motor_mm"] / 2 * 1e-3
    Fe_s, Fe_m = T_motor_steady / r1, T_motor_max / r1
    b_need_steady = c2 * Fe_s / (z_m * F_tsp)
    b_need_max = Fe_m / (z_m * F_tsp)
    m_lin = 0.0036 * BELT["width"]                             # kg/m, HTD 5M [IR]
    T_st = 0.75 * Fe_m + m_lin * bl["v_mps"] ** 2              # static tension per strand: the slack side stays tight
    hub = 2 * T_st * math.sin(math.radians(bl["wrap_small_deg"]) / 2)
    st_ = stackup(bevel_geometry())
    zf_ = [r for r in st_["rows"] if r["part"].startswith("gear case floor")][0]
    zp_ = [r for r in st_["rows"] if r["part"].startswith("machine pulley")][0]
    arm = (0.5 * (zf_["z0"] + zf_["z1"]) - 0.5 * (zp_["z0"] + zp_["z1"])) * 1e-3        # bearing centre to pulley centre
    sig = lambda F: 32 * F * arm / (math.pi * (2 * R_SHAFT * 1e-3) ** 3) / 1e6
    f_span = 1 / (2 * bl["span_mm"] * 1e-3) * math.sqrt(T_st / m_lin)
    T_allow = 25.0 * BELT["width"]                             # N, allowable working tension, glass cord [IR]
    return dict(bl, journal_arm_mm=arm * 1e3, journal_sigma_MPa=sig(hub), journal_sigma_max_MPa=sig(2 * T_st + Fe_m),
                F_tsp=F_tsp, service_factor=c2, z_m_rated=z_m, F_e_steady_N=Fe_s, F_e_max_N=Fe_m,
                width_needed_steady_mm=b_need_steady, width_needed_at_limit_mm=b_need_max, width_mm=BELT["width"],
                T_static_per_strand_N=T_st, hub_load_N=hub, T_tight_max_N=T_st + Fe_m / 2, T_allow_N=T_allow,
                f_span_Hz=f_span, mesh_Hz_motor=BELT["z_motor"] * bl["motor_rpm"] / 60)


# ================================================================================================ 7. the concepts
def concepts(bg, st, mean, pul):
    """the comparison (numbers where this study computes them; first-cut estimates otherwise) [IR / RH]."""
    pom = pul["POM-C"]; ssg = pul["stainless"]
    return [
        dict(key="a", name="bevel reverser, carrier = frame (recommended)",
             kinematics="exact 1 : -1 (equal side gears, positive drive) [OC]",
             axial_mm=round(st["added_below_slot_mm"]), radial_dia_mm=round(2 * st["case_outer_r"]),
             radial_load_on_bodies="none net from the gear (3 pinions at 120 deg) [OC]; belt hub load into the "
                                   "locating end bearing only",
             backlash="one stage, two meshes in series; does not matter to the pumps [OC]",
             pulsation_share=(f"POM pinions: gear-path mode {pom['gear_path_mode_Hz']:.0f} Hz, the gear's ripple "
                              f"+/-{100 * pom['worst']['gear_pp'] / 2 / max(abs(pom['tau_mean_on_each_body']), 1e-9):.0f} % "
                              f"of its mean; stainless: {ssg['gear_path_mode_Hz']:.0f} Hz, "
                              f"+/-{100 * ssg['worst']['gear_pp'] / 2 / max(abs(ssg['tau_mean_on_each_body']), 1e-9):.0f} %; "
                              f"no flank reversal either way"),
             noise="low with POM pinions (mesh 300 Hz)", cost_EUR="~330-460 (BOM below)",
             reaction="pinion cartridges -> gear case -> base: 2 x the gear torque [OC]",
             risks="the side gears' axial setting (shims); POM creep under the bores (steel hubs)"),
        dict(key="b", name="star gear with stepped planets, carrier = frame",
             kinematics="1 : -1 only for z_s z_p2 = z_p1 z_r, e.g. sun 45 / planets 15 + 30 / ring 90 at m 1.5 [OC]",
             axial_mm=90, radial_dia_mm=170,
             radial_load_on_bodies="none net (3 planets)",
             backlash="two stages in series; the stepped planets must be timed",
             pulsation_share="as (a) for the same materials", noise="moderate: internal gear, 6 meshes",
             cost_EUR="~600-900 (internal ring and stepped planets made one-off) [RH]",
             reaction="planet pins -> carrier -> frame: 2 x the gear torque",
             risks="cost, the ring's bell must reach round the planets from the counter-rotor"),
        dict(key="c", name="two belts, the second reversed (double-sided belt on its back, or an idler pair)",
             kinematics="1 : -1 on average (equal tooth counts); elastic phase wobble [OC]",
             axial_mm=110, radial_dia_mm=260,
             radial_load_on_bodies="the counter-rotor's pulley pulls ~120 N on its overhung end unless it gets its own "
                                   "frame bearing (then the counter-rotor is frame-supported)",
             backlash="belt compliance; soft", pulsation_share="small (soft belts, the bodies' inertia)",
             noise="low", cost_EUR="~300-400",
             reaction="two hub loads and the motor mount",
             risks="back-side drive (double-sided belt, short wrap), tooth jump in a run-up, two tensioners"),
        dict(key="d1", name="two motors, one per body, phase-locked (an electric gear)",
             kinematics="1 : -1 by control; not one belt", axial_mm=60, radial_dia_mm=300,
             radial_load_on_bodies="a hub load on each body's end", backlash="none (control)",
             pulsation_share="none through a gear; each loop sees its body's share",
             noise="low", cost_EUR="~550-700 (two drives + controller) [RH]",
             reaction="each motor mount", risks="departs from the decided single belt; a drive trip unbalances"),
        dict(key="d2", name="spur layshaft with an internal ring on the counter-rotor",
             kinematics="1 : -1 for z1 z3 = z2 z4", axial_mm=80, radial_dia_mm=220,
             radial_load_on_bodies="unbalanced: one layshaft pushes both bodies sideways (~2 F_t)",
             backlash="two meshes", pulsation_share="as (a)", noise="moderate", cost_EUR="~400-600",
             reaction="layshaft bearings -> frame", risks="side loads at the 0.5 mm utron gap's end"),
        dict(key="d3", name="friction (traction) bevel reverser",
             kinematics="not exact: 0.5-3 % slip [RH]", axial_mm=90, radial_dia_mm=160,
             radial_load_on_bodies="none net", backlash="none", pulsation_share="slip absorbs it",
             noise="very low", cost_EUR="~200-300", reaction="roller axles -> frame",
             risks="the speed split drifts; wear; the designer's 1 : -1 is not held"),
    ]


# ================================================================================================= 8. the BOM
BOM = [  # (group, item, qty, unit EUR [RH placeholder], economy unit EUR [RH], note)
    ("gear", "side gears, stainless 1.4305, m 2, z 30, b 12 (the wheel of a 1.5 : 1 bevel set), keyed in the hub / bolted",
     2, 45.0, 25.0, "economy: C45 stock gears, if the non-magnetic rule is waived this far from the utrons"),
    ("gear", "pinions, POM-C, m 2, z 20, b 12, pressed on stainless stub shafts", 3, 20.0, 12.0, "catalogue or cut from rod"),
    ("gear", "pinion cartridges: stub shaft Ø 10, 2 x 6000-2Z, sleeve, shims", 3, 18.0, 15.0, ""),
    ("gear", "gear case and bell, Al 6082, machined: 3 pinion bores at 120 deg, the locating 6205 seat, belt windows",
     1, 140.0, 80.0, "it is also the frame's bottom end-bearing housing; economy: a bolted plate case"),
    ("gear", "counter-rotor gear hub, Al 6082 (bolts under the re-purposed bottom spider)", 1, 35.0, 30.0,
     "the sheet's bottom G10 spider becomes the counter-rotor's end disc (no new part)"),
    ("gear", "gear-end inner bearing 6205-2Z, at bridge ring A's outer end", 1, 12.0, 12.0,
     "the bottom one of the bearing pair sim/tube-shaft-findings.md section 0 proposes (8 bearings); with the "
     "six-bearing option it is a seventh"),
    ("gear", "grease (POM-compatible), keys, circlips, fasteners", 1, 20.0, 15.0, ""),
    ("drive", "brushless DC motor 200 W, 3000 rpm, 48 V, with driver (speed loop, ramps, current limit)", 1, 190.0, 130.0,
     "economy: a 0.25 kW 4-pole induction motor on a 0.4 kW VFD (pulleys 24T / 56T), no DC supply"),
    ("drive", "48 V DC supply, 300 W", 1, 45.0, 0.0, "none with the VFD"),
    ("drive", "HTD 5M belt, 15 mm, 750 mm (150 teeth)", 1, 15.0, 15.0, ""),
    ("drive", "pulleys HTD 5M: 20T (motor) and 80T (machine, taper bush)", 1, 60.0, 50.0, "15 + 45"),
    ("drive", "motor plate with tensioning slots", 1, 30.0, 20.0, ""),
    ("frame", "base plate, 20 mm, machined seats for the case and the motor plate", 1, 120.0, 80.0, ""),
    ("frame", "three columns, aluminium extrusion 45 x 45, ~1.2 m", 3, 25.0, 20.0, ""),
    ("frame", "top plate with the floating top end-bearing housing (6205)", 1, 90.0, 60.0, ""),
    ("frame", "levelling feet, brackets, fasteners", 1, 30.0, 20.0, ""),
]
BOM_OPTIONS = [("gear", "friction torque limiter (slip hub) under the counter-rotor's side gear, set ~6 N m", 1, 80.0,
                "protects the gear and the bodies in a rub at the 0.5 mm gap")]
SHEET = dict(gear=250.0, drive=250.0, frame=300.0)            # docs/make_cost_sheet.py BOM fixed, Mechanics


# ===================================================================================================== the figure
def figure(bg, st, bl, mean, pul, runs, peaks):
    """docs/figures/drive-gear-concept.svg: a kinematic section through the frame end (side A, below) and the drive.
    z to scale; radii to scale out to r 80 mm and compressed beyond (the right half only: the left half is broken at
    r 80); the motor's offset shortened. Dark ink on white; fills: rotor light grey, counter-rotor white, frame hatched."""
    W, H = 1100, 780
    s = 2.6                                                    # px per mm
    x0, y_top, z_top = 380.0, 112.0, 45.0
    ink, mid = "#1a1a1a", "#4d4d4d"
    F_ROT, F_CR, F_FR, F_BRG = "#d9d9d9", "#ffffff", "url(#hatch)", "#bfbfbf"
    R_BREAK = 80.0

    def Y(z):
        return y_top + (z_top - z) * s

    def R(r):
        return r * s if r <= R_BREAK else R_BREAK * s + (r - R_BREAK) * 0.4 * s

    def X(r, side=+1):
        return x0 + side * R(r)
    o = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}" '
         f'font-family="Helvetica, Arial, sans-serif" font-size="12" fill="none" stroke="{ink}" stroke-width="1.4">',
         '<defs><pattern id="hatch" width="6" height="6" patternUnits="userSpaceOnUse" patternTransform="rotate(45)">'
         f'<rect width="6" height="6" fill="#ffffff" stroke="none"/><line x1="0" y1="0" x2="0" y2="6" stroke="{mid}" '
         'stroke-width="1"/></pattern></defs>',
         f'<rect x="0" y="0" width="{W}" height="{H}" fill="#ffffff" stroke="none"/>']

    def text(x, y, t, anchor="start", col=ink, size=12, bold=False):
        b = ' font-weight="bold"' if bold else ""
        o.append(f'<text x="{x:.1f}" y="{y:.1f}" text-anchor="{anchor}" font-size="{size}" fill="{col}" '
                 f'stroke="none"{b}>{t}</text>')

    def line(x1, y1, x2, y2, w=1.4, dash=None, col=ink):
        dsh = f' stroke-dasharray="{dash}"' if dash else ""
        o.append(f'<line x1="{x1:.1f}" y1="{y1:.1f}" x2="{x2:.1f}" y2="{y2:.1f}" stroke="{col}" stroke-width="{w}"{dsh}/>')

    def poly(pts, fill="none", w=1.4, dash=None):
        dsh = f' stroke-dasharray="{dash}"' if dash else ""
        p = " ".join(f"{a:.1f},{b:.1f}" for a, b in pts)
        o.append(f'<polygon points="{p}" fill="{fill}" stroke-width="{w}"{dsh}/>')

    def box(r0, r1, z0, z1, fill, side=+1, w=1.4, dash=None):
        if side < 0:
            r1 = min(r1, R_BREAK)
            if r0 >= r1:
                return
        xa, xb = sorted((X(r0, side), X(r1, side)))
        poly([(xa, Y(z1)), (xb, Y(z1)), (xb, Y(z0)), (xa, Y(z0))], fill, w, dash)
        if side < 0 and r1 == R_BREAK:                        # a break line where the left half is cut
            xm_, ya, yb = X(R_BREAK, -1), Y(z1), Y(z0)
            pts = [(xm_, ya)] + [(xm_ + (4 if k % 2 else -4), ya + (yb - ya) * (k + 0.5) / 4) for k in range(4)] + [(xm_, yb)]
            o.append('<polyline points="' + " ".join(f"{a:.1f},{b:.1f}" for a, b in pts) +
                     f'" fill="none" stroke="{ink}" stroke-width="1.0"/>')

    def bearing(r0, r1, z0, z1, side):
        box(r0, r1, z0, z1, F_BRG, side, 1.0)
        line(X(r0, side), Y(z1), X(r1, side), Y(z0), 0.8); line(X(r1, side), Y(z1), X(r0, side), Y(z0), 0.8)

    def leader(xa, ya, xb, yb, lines, anchor="start", bold_first=False):
        line(xa, ya, xb, yb, 0.8, col=mid)
        dx = 4 if anchor == "start" else -4
        for k, t in enumerate(lines):
            text(xb + dx, yb + 4 + 15 * k, t, anchor, bold=(bold_first and k == 0))
    text(20, 30, "The 1 : -1 bevel reverser at the frame end (side A, below), and the belt drive", size=17, bold=True)
    text(20, 52, "PROPOSED. Kinematic section through the axis, drawn by sim/drive_sizing.py --figure. Heights to scale; "
                 "radii to scale out to r 80 mm and compressed beyond (right half); the left half is broken at r 80.",
         col=mid)
    text(20, 70, "Fills: rotor light grey; counter-rotor white; frame hatched; bearings crossed. The motor's offset is "
                 "drawn shortened.", col=mid)
    za = st["z_apex"]
    zf = [r for r in st["rows"] if r["part"].startswith("gear case floor")][0]
    zp = [r for r in st["rows"] if r["part"].startswith("machine pulley")][0]
    zb = [r for r in st["rows"] if r["part"].startswith("base plate")][0]
    Re, delS, delP = bg["R_e"], math.radians(bg["delta_side_deg"]), math.radians(bg["delta_pinion_deg"])
    Ri = Re - GEAR["b"]
    rc = st["case_outer_r"]
    for side in (+1, -1):
        box(SP["r_ring0"], SP["r_ring1"], 20.0, z_top, F_CR, side)                     # bridge ring A (continues up)
        box(GEAR["r_disc0"], SP["r_ring1"], 10.0, 20.0, F_CR, side)                    # the end disc
        box(R_SHAFT + 0.6, 40.0, -8.0, 10.0, F_CR, side)                               # the counter-rotor's hub
        bearing(R_SHAFT, 26.0, -5.0, 10.0, side)                                       # the gear-end inner bearing
        zo, zi = za + Re * math.cos(delS), za + Ri * math.cos(delS)
        ro, ri = Re * math.sin(delS), Ri * math.sin(delS)
        poly([(X(R_SHAFT + 1.5, side), Y(-8.0)), (X(ro + 2.0, side), Y(-8.0)), (X(ro + 2.0, side), Y(zo)),
              (X(ri, side), Y(zi)), (X(R_SHAFT + 1.5, side), Y(zi))], F_CR)            # counter-rotor side gear
        zback = za - Re * math.cos(delS) - 8.0
        poly([(X(R_SHAFT, side), Y(zback - 12.0)), (X(20.0, side), Y(zback - 12.0)), (X(20.0, side), Y(zback)),
              (X(ro + 2.0, side), Y(zback)), (X(ro + 2.0, side), Y(za - Re * math.cos(delS))),
              (X(ri, side), Y(za - Ri * math.cos(delS))), (X(R_SHAFT, side), Y(za - Ri * math.cos(delS)))], F_ROT)
        rpo, rpi = Re * math.cos(delP), Ri * math.cos(delP)
        ho, hi = Re * math.sin(delP), Ri * math.sin(delP)
        poly([(X(rpi, side), Y(za + hi)), (X(rpo, side), Y(za + ho)), (X(rpo + 8.0, side), Y(za + ho)),
              (X(rpo + 8.0, side), Y(za - ho)), (X(rpo, side), Y(za - ho)), (X(rpi, side), Y(za - hi))], "#ffffff", 2.0)
        line(X(rpi, side), Y(za), X(rc - 2.0, side), Y(za), 2.4)                       # the pinion's stub shaft
        bearing(rpo + 10.0, rpo + 18.0, za - 6.5, za + 6.5, side)
        bearing(rpo + 22.0, rpo + 30.0, za - 6.5, za + 6.5, side)
        box(rpo + 9.0, rc - 8.0, za + 7.0, za + 9.0, F_FR, side, 0.8)                  # the cartridge sleeve
        box(rpo + 9.0, rc - 8.0, za - 9.0, za - 7.0, F_FR, side, 0.8)
        box(rc - 8.0, rc, zf["z0"], za + 34.0, F_FR, side)                             # the case wall
        box(44.0, rc - 8.0, za + 28.0, za + 34.0, F_FR, side)                          # its top lip (labyrinth)
        box(26.0, rc - 8.0, zf["z0"], zf["z1"], F_FR, side)                            # the floor
        bearing(R_SHAFT, 26.0, zf["z0"] + 2.0, zf["z1"], side)                         # the locating end bearing
        box(rc - 8.0, rc, zb["z1"], zf["z0"], F_FR, side, 1.0, dash="5,3")             # the bell (belt windows)
        box(R_SHAFT, bl["dia_machine_mm"] / 2, zp["z0"], zp["z1"], F_ROT, side)          # the machine pulley
    box(0.0, R_SHAFT, Z_SHAFT_END, z_top, F_ROT, +1, 1.2); box(0.0, R_SHAFT, Z_SHAFT_END, z_top, F_ROT, -1, 1.2)
    box(0.0, 18.0, Z_SHAFT_END, Z_SHAFT_END + 6.0, F_ROT, +1, 1.0); box(0.0, 18.0, Z_SHAFT_END, Z_SHAFT_END + 6.0, F_ROT, -1, 1.0)
    line(X(0), Y(z_top + 3), X(0), Y(zb["z0"] - 6), 0.8, "12,4,2,4", mid)
    xb0, xb1 = X(R_BREAK, -1) - 10, 1080.0
    poly([(xb0, Y(zb["z1"])), (xb1, Y(zb["z1"])), (xb1, Y(zb["z0"])), (xb0, Y(zb["z0"]))], F_FR)
    # the belt and the motor (offset shortened)
    xm = 1000.0
    rp_m = bl["dia_motor_mm"] / 2 * s
    yb1, yb0 = Y(zp["z1"] - 5.0), Y(zp["z0"] + 5.0)
    line(X(bl["dia_machine_mm"] / 2), yb1, xm - rp_m, yb1, 2.0, "8,4")
    line(X(bl["dia_machine_mm"] / 2), yb0, xm - rp_m, yb0, 2.0, "8,4")
    poly([(xm - rp_m, Y(zp["z1"])), (xm + rp_m, Y(zp["z1"])), (xm + rp_m, Y(zp["z0"])), (xm - rp_m, Y(zp["z0"]))], F_ROT)
    poly([(xm - 36, Y(zp["z1"]) - 78), (xm + 36, Y(zp["z1"]) - 78), (xm + 36, Y(zp["z1"]) - 10), (xm - 36, Y(zp["z1"]) - 10)],
         "#ffffff")
    poly([(xm - 54, Y(zp["z1"]) - 10), (xm + 54, Y(zp["z1"]) - 10), (xm + 54, Y(zp["z1"]) - 2), (xm - 54, Y(zp["z1"]) - 2)],
         F_FR, 1.0)
    line(xm, Y(zp["z1"]) - 2, xm, Y(zp["z1"]), 2.0)
    text(xm, Y(zp["z1"]) - 52, "BLDC", "middle", bold=True)
    text(xm, Y(zp["z1"]) - 36, "200 W", "middle")
    text(xm, Y(zp["z1"]) - 20, f"{bl['motor_rpm']:.0f} rpm", "middle")
    text(xm, Y(zp["z0"]) + 16, f"{BELT['z_motor']}T", "middle")
    xmid = 0.5 * (X(bl["dia_machine_mm"] / 2) + xm)
    text(xmid, yb1 - 8, f"HTD 5M belt, {BELT['width']:.0f} mm, {BELT['L_belt']:.0f} mm; ratio {bl['ratio']:.0f} : 1; "
         f"centres {bl['centre_mm']:.0f} mm", "middle")
    text(xmid, yb0 + 18, "motor plate slotted for the tension", "middle", mid)
    # labels: the right column = counter-rotor and frame; the left column = rotor
    xr = X(SP["r_ring1"]) + 14
    text(xr, Y(z_top) + 10, "counter-rotor, -600 rpm", bold=True)
    text(xr, Y(z_top) + 25, "bridge ring A (G10); the bridges")
    text(xr, Y(z_top) + 40, "and the reluctance section above")
    leader(X(120.0), Y(15.0), xr - 4, Y(15.0) + 20, ["end disc, G10 10 mm: the bottom", "spider re-purposed (new role)"])
    leader(X(38.0), Y(4.0), xr - 4, Y(4.0) + 58, ["hub with the gear-end inner bearing", "6205-2Z (1200 rpm relative)"])
    leader(X(31.0), Y(-15.0), xr - 4, Y(-15.0) + 82, ["side gear z 30, m 2, stainless", "(the counter-rotor's)"])
    leader(X(34.0), Y(za + 12.0), xr - 4, Y(za) + 78, [f"POM pinion z 20, x 3 at 120 deg,", "on a stub shaft in 2 x 6000-2Z"])
    leader(X(rc), Y(za - 24.0), xr - 4, Y(za - 24.0) + 70, ["gear case = the carrier (frame),",
                                                           f"Al 6082: takes {mean['T_carrier']:.1f} N m steady"])
    xl = X(R_BREAK, -1) - 18
    text(xl, Y(z_top) + 10, "shaft (rotor), +600 rpm", "end", bold=True)
    text(xl, Y(z_top) + 25, "journal Ø 25 at the gear end", "end")
    line(xl + 4, Y(z_top) + 6, X(R_SHAFT, -1), Y(z_top) + 6, 0.8, col=mid)
    leader(X(28.0, -1), Y(za - 30.0), xl, Y(za - 30.0), ["rotor side gear z 30,"], "end")
    text(xl - 4, Y(za - 30.0) + 19, "keyed in its hub", "end")
    leader(X(20.0, -1), Y(zf["z0"] + 9.0), xl, Y(zf["z0"] + 9.0), ["locating end bearing"], "end")
    text(xl - 4, Y(zf["z0"] + 9.0) + 19, "6205-2Z (frame)", "end")
    leader(X(56.0, -1), Y(0.5 * (zp["z0"] + zp["z1"])), xl, Y(0.5 * (zp["z0"] + zp["z1"])), [f"pulley HTD 5M {BELT['z_machine']}T"],
           "end")
    text(xl - 4, Y(0.5 * (zp["z0"] + zp["z1"])) + 19, "(rotor)", "end")
    text(xb0, Y(zb["z0"]) + 18, "base plate (frame); the columns up to the top end bearing are not drawn", "start", mid)
    # the numbers, below the drawing
    by = Y(zb["z0"]) + 44
    rows_l = [("Steady, 600 rpm each way", True),
              (f"pumps between the bodies {mean['T_pump']:.3f} N m (1200 rpm relative)", False),
              (f"  swinging {peaks['total_min']:.2f} .. {peaks['total_max']:.2f} N m at 120 / 240 Hz", False),
              (f"with bearings and {P_WIND:.0f} W of windage {mean['T_rel']:.2f} N m", False),
              (f"gear on each body {mean['tau_gear_cr']:.2f} N m; frame (carrier) {mean['T_carrier']:.2f} N m", False)]
    rows_r = [("Drive", True),
              (f"belt at the shaft {mean['T_belt']:.2f} N m, {mean['P_belt']:.0f} W; motor {mean['P_motor_shaft']:.0f} W", False),
              (f"run-up to 600 rpm {runs['pumps_on']['t_s']:.0f} s at the motor's rated torque", False),
              (f"gear peak {runs['pumps_on']['peak_gear_Nm']:.1f} N m (run-up); ripple {pul['POM-C']['worst']['gear_pp']:.2f} N m p-p", False),
              ("the ripple stays in the bodies: the gear-path mode is 20 Hz", False)]
    for col, rows in ((20, rows_l), (560, rows_r)):
        for k, (t, b) in enumerate(rows):
            text(col, by + 18 * k, t, bold=b)
    o.append("</svg>")
    os.makedirs(os.path.dirname(FIG), exist_ok=True)
    with open(FIG, "w") as f:
        f.write("\n".join(o) + "\n")


# ======================================================================================================== main
W_ALL = 0.0                                                    # set in main: the rotating weight on the locating bearing


def main():
    global W_ALL
    no_spice = "--no-spice" in sys.argv
    bg = bevel_geometry()
    st = stackup(bg)
    GEAR.update(z_rotor_gear=st["z_rotor_gear"], z_cr_gear=st["z_cr_gear"])
    GEAR["z_pulley"] = st["z_pulley"]
    P, ut = bodies()
    m_r = sum(p[4] for p in P if p[1] == "rotor"); m_c = sum(p[4] for p in P if p[1] == "counter")
    J_r = sum(p[5] for p in P if p[1] == "rotor"); J_c = sum(p[5] for p in P if p[1] == "counter")
    W_ALL = (m_r + m_c) * G0
    mean = budget()
    print(f"bodies: rotor {m_r:.1f} kg, J {J_r:.3f} kg m^2; counter-rotor {m_c:.1f} kg, J {J_c:.3f} kg m^2", flush=True)
    print(f"steady: pumps {mean['T_pump']*1e3:.1f} mN m rel.; T_rel {mean['T_rel']:.3f}; gear {mean['tau_gear_cr']:.3f} / "
          f"{mean['tau_gear_rotor']:.3f}; carrier {mean['T_carrier']:.3f}; belt {mean['T_belt']:.3f} N m, "
          f"{mean['P_belt']:.1f} W", flush=True)
    sens = [dict(P_wind_W=pw, **{k: v for k, v in budget(P_wind=pw).items() if k != "P_split"}) for pw in (0, 25, 50, 100)]
    # the pulsation
    hAe, hBe, es_info = electrostatic_wave()
    hAm, hBm, mag_info = magnetic_wave(no_spice)
    print(f"electrostatic wave: mean {es_info['mean_W']:.3f} W; magnetic: {mag_info.get('P_belt_W', 'stored')}", flush=True)
    pul = pulsation(P, hAm, hBm, hAe, hBe, mean)
    peaks = pump_peaks(hAm, hBm, hAe, hBe)
    print(f"pumps' torque between the bodies: {peaks['total_min']:.2f} .. {peaks['total_max']:.2f} N m (mean "
          f"{peaks['mean']:.3f}); side A {peaks['A_min']:.2f} .. {peaks['A_max']:.2f}", flush=True)
    for k, v in pul.items():
        print(f"  {k:9s}: gear-path mode {v['gear_path_mode_Hz']:.1f} Hz, gear p-p {v['worst']['gear_pp']:.4f} N m (worst phase "
              f"{v['worst']['phase_deg']} deg), reversal {v['flank_reversal']}, hub p-p {v['worst']['hub_pp']:.3f}, "
              f"cage p-p {v['worst']['cage_pp']:.3f}, belt p-p {v['worst']['belt_pp']:.4f}", flush=True)
    # the run-up and the fault
    i_b = BELT["z_machine"] / BELT["z_motor"]
    J_mref = MOTOR["J"] * i_b ** 2
    J_tot = J_r + J_c + J_mref
    runs = dict(pumps_on=runup(J_r + J_c, J_c, J_mref, True), es_only=runup(J_r + J_c, J_c, J_mref, False),
                at_limit=runup(J_r + J_c, J_c, J_mref, True, t_target=5.0, lim=MOTOR["I_lim_factor"]),
                slow_60s=runup(J_r + J_c, J_c, J_mref, True, t_target=60.0))
    for row in sens:                                             # how long the 200 W motor needs, by windage
        r_ = runup(J_r + J_c, J_c, J_mref, True, P_wind=row["P_wind_W"])
        row["t_runup_s"] = r_["t_s"]
        row["motor_load_of_rated"] = row["P_motor_shaft"] / (MOTOR["T_rated"] * W_BODY * i_b)
    T_fault = MOTOR["I_lim_factor"] * MOTOR["T_rated"] * i_b * ETA_BELT        # the driver's current limit at the shaft
    b0 = budget(pumps=True, mag=True)
    alpha_f = (T_fault - budget(pumps=True, mag=True, w_body=1e-3)["T_belt"]) / J_tot   # from rest: the most
    fault = dict(T_belt_Nm=T_fault, alpha=alpha_f,
                 tau_gear_Nm=max(budget(w_body=1e-3)["tau_gear_cr"] + J_c * alpha_f, runs["at_limit"]["peak_gear_Nm"]),
                 tau_gear_braking_Nm=J_c * (T_fault + b0["T_belt"]) / J_tot - b0["tau_gear_cr"],
                 note=f"the driver's current limit ({MOTOR['I_lim_factor']:g} x rated) at the shaft: the most the belt can "
                      "push or brake; the gear's share is the counter-rotor's inertia share [OC; IR the limit]")
    print(f"run-up: {runs['pumps_on']['t_s']:.1f} s (pumps on), peak gear {runs['pumps_on']['peak_gear_Nm']:.2f} N m; "
          f"fault gear {fault['tau_gear_Nm']:.2f} N m", flush=True)
    # the gear checks
    pom = pul["POM-C"]
    tau_fat = mean["tau_gear_rotor"] + 0.5 * pom["worst"]["gear_pp"]
    checks = [gear_check(tau_fat, "steady + pulsation (10^9 cycles)", True),
              gear_check(runs["pumps_on"]["peak_gear_Nm"], "run-up peak (10^4 cycles a start)", False),
              gear_check(max(fault["tau_gear_Nm"], fault["tau_gear_braking_Nm"]), "driver current limit (fault)", False)]
    pl = pinion_loads(fault["tau_gear_Nm"])
    pl_s = pinion_loads(mean["tau_gear_rotor"])
    for c in checks:
        print(f"  {c['case']:38s}: tau {c['tau_Nm']:.2f} N m, sF pinion {c['sigma_F_pinion_MPa']:.1f} MPa (S {c['S_F_pinion']:.1f}), "
              f"sH {c['sigma_H_MPa']:.1f} MPa (S {c['S_H_pinion']:.1f})", flush=True)
    # bearings
    W_c = m_c * G0
    th = pinion_loads(mean["tau_gear_rotor"])["side_gear_thrust_N"]
    P_gear_end = dg_equivalent(5.0, W_c + th)
    unb = lambda m: m * (2.5e-3 / W_BODY) * W_BODY ** 2       # ISO 21940 G 2.5 [IR]
    bc = belt_check(mean["P_motor_shaft"] / (W_BODY * i_b), MOTOR["I_lim_factor"] * MOTOR["T_rated"])
    P_bottom = dg_equivalent(bc["hub_load_N"] + unb(m_r), W_ALL + GEAR["m_side_kg"] * G0)
    p_rpm = bg["pinion_rpm"]
    bearings = dict(
        gear_end_inner=dict(part="6205-2Z", rpm_rel=2 * RPM_BODY, F_axial_N=W_c + th, F_radial_N=5.0 + unb(m_c),
                            P_N=P_gear_end, L10_h=l10_h(C_6205, P_gear_end, 2 * RPM_BODY),
                            note="locates the counter-rotor axially (carries its weight); it is the bearing at bridge "
                                 "ring A's outer end that sim/tube-shaft-findings.md section 0 proposes"),
        bottom_end_locating=dict(part="6205-2Z", rpm=RPM_BODY, F_axial_N=W_ALL, F_radial_N=bc["hub_load_N"] + unb(m_r),
                                 P_N=P_bottom, L10_h=l10_h(C_6205, P_bottom, RPM_BODY),
                                 note="carries both bodies' weight and the belt's hub load"),
        pinion_inner_steady=dict(part="6000-2Z", rpm=p_rpm, F_N=pl_s["R_inner_N"], L10_h=l10_h(C_6000, max(pl_s["R_inner_N"], 5.0), p_rpm)),
        pinion_inner_fault=dict(part="6000-2Z", F_N=pl["R_inner_N"], static_ratio=C0_6000 / max(pl["R_inner_N"], 1)),
        unbalance_N=dict(rotor=unb(m_r), counter_rotor=unb(m_c)))
    frame = dict(weight_on_locating_bearing_N=W_ALL, carrier_torque_Nm=dict(steady=mean["T_carrier"],
                 run_up=runs["pumps_on"]["peak_gear_Nm"] * (1 + 1 / ETA_MESH ** 2), fault=fault["tau_gear_Nm"] * (1 + 1 / ETA_MESH ** 2)),
                 motor_mount_torque_Nm=dict(steady=mean["P_motor_shaft"] / (W_BODY * i_b),
                                            limit=MOTOR["I_lim_factor"] * MOTOR["T_rated"]),
                 belt_hub_load_N=bc["hub_load_N"], belt_hub_load_max_N=2 * bc["T_static_per_strand_N"] + bc["F_e_max_N"],
                 pulsation_into_frame_pp_Nm=2 * pom["worst"]["gear_pp"],
                 note="the carrier torque and the motor mount's reaction close through the base plate; about the "
                      "axis the frame's net load is the drags only [OC]")
    # BOM
    tot, eco = {}, {}
    for grp, item, q, u, ue, note in BOM:
        tot[grp] = tot.get(grp, 0.0) + q * u
        eco[grp] = eco.get(grp, 0.0) + q * ue
    bom = dict(rows=[dict(group=g, item=i, qty=q, unit_EUR=u, extended_EUR=q * u, economy_EUR=q * ue, note=n)
                     for g, i, q, u, ue, n in BOM],
               options=[dict(group=g, item=i, qty=q, unit_EUR=u, note=n) for g, i, q, u, n in BOM_OPTIONS],
               totals_EUR=tot, total_EUR=sum(tot.values()), economy_totals_EUR=eco, economy_total_EUR=sum(eco.values()),
               sheet_EUR=SHEET, sheet_total_EUR=sum(SHEET.values()),
               extra_elsewhere="~150 mm more shaft below the old end slot (+18 at the sheet's 120 /m); the sheet's six G10 "
                               "spiders stay six (the bottom one becomes the counter-rotor's end disc)")
    res = dict(
        status="PROPOSED (the designer accepts it)",
        sources=SOURCES,
        speeds=dict(rpm_body=RPM_BODY, rpm_rel=2 * RPM_BODY, w_body=W_BODY, w_rel=W_REL, f_pump_Hz=F_PUMP),
        pumps=dict(P_mag_W=P_MAG, P_fe_W=P_FE, P_es_W=P_ES, P_total_W=P_PUMPS, T_rel_Nm=P_PUMPS / W_REL,
                   T_mag_Nm=(P_MAG + P_FE) / W_REL, T_es_Nm=P_ES / W_REL, T_old_pump_Nm=T_PUMP_OLD,
                   per_body_Nm_at_600=P_PUMPS / W_REL,
                   note="the pumps' torque acts between the bodies at 1200 rpm relative; each body sees it against its "
                        "own 600 rpm, so each body's share of the power is half [OC]"),
        bodies=dict(rotor_kg=m_r, counter_rotor_kg=m_c, J_rotor=J_r, J_counter_rotor=J_c,
                    utron=dict(m_kg=ut["total"][0], J_kgm2=ut["total"][1],
                               parts={k: dict(m_kg=v[0], J_kgm2=v[1]) for k, v in ut.items() if k != "total"}),
                    parts=[dict(name=p[0], body=p[1], station=p[2], z_mm=p[3], m_kg=p[4], J_kgm2=p[5], tag=p[6]) for p in P],
                    E_kinetic_J=0.5 * (J_r + J_c) * W_BODY ** 2),
        steady=mean, windage_sensitivity=sens,
        pulsation=dict(electrostatic=es_info, magnetic=mag_info, pumps_between_bodies=peaks,
                       drive={k: {kk: vv for kk, vv in v.items()} for k, v in pul.items()}),
        runup=runs, fault=fault, windage_crosscheck=windage_crosscheck(), selfcheck_rigid_limit=selfcheck_rigid_limit(),
        gear=dict(spec=dict(GEAR), geometry=bg, checks=checks, pinion_loads_fault=pl, pinion_loads_steady=pl_s,
                  backlash=dict(j_n_mm=[0.10, 0.15], note="set by shims under the pinion cartridges and the rotor gear's "
                                "spacer; the pumps do not see it (both pumps' A / B phases are internal to each body) [OC]")),
        belt=bc, motor=MOTOR, bearings=bearings, frame=frame, envelope=st,
        concepts=concepts(bg, st, mean, pul), bom=bom)
    with open(OUT, "w") as f:
        json.dump(res, f, indent=1, default=lambda x: [x.real, x.imag] if isinstance(x, complex) else float(x))
    print(f"wrote {os.path.relpath(OUT, ROOT)}", flush=True)
    if "--figure" in sys.argv:
        figure(bg, st, belt_geometry(), mean, pul, runs, peaks)
        print(f"wrote {os.path.relpath(FIG, ROOT)}", flush=True)


if __name__ == "__main__":
    main()
