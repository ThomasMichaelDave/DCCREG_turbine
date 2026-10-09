#!/usr/bin/env python3
"""sim/rotor_mechanics.py -- the rotating mechanics of the locked machine: centrifugal loads and banding, the utrons'
magnetic pull, the 0.5 mm utron gap budget (runout), windage and balancing.

Writes sim/rotor_mechanics_results.json; the findings are sim/rotor-mechanics-findings.md.
Usage: python3 sim/rotor_mechanics.py          (under a minute; importing sim/stack_sizing.py runs its self-test)

Every input is read from the record (the file is named where it is read) or is a datasheet-class value tagged [IR]:
  * the utron, the bridge and their fastening: sim/utron_profile.spec of the pick in sim/pole_design_variants_op.json
    ("g 0.5 / 6 bridges / 1200 rpm"), the same numbers that build the solids and DCCREG-UTR-101;
  * the vane stacks of record: sim/air_stack_sizing_results.json (thick_vanes.compare, 3 mm, 6 + 6) and the ring
    geometry of sim/air_stack_sizing.masses (stator ring 12 mm into the cage, rotor ring to the sleeve);
  * the layout along the shaft: sim/stack_sizing.layout with that stack, the wound reluctance section and the locked
    hub's flanges at |z| 72-80 (presets/hub-locked.json) -> 940 mm;
  * the hub: presets/hub-locked.json; the shaft Ø25 (sim/stack_sizing.py SHAFT_R) or Ø30 (presets/hub-locked.json);
  * the belt's power: sim/ah_steady_cusp_results.json (22 mF row), sim/pole_design_variants_op.json (iron),
    sim/core_field_results.json (electrostatic, clamped).
Models (tags per CONVENTIONS.md section 1):
  * centrifugal loads: rigid bodies at 600 rpm each way and a 1.25 x overspeed (750 rpm) [IR]; thin-ring, rotating-disc
    (Lame) and beam formulas [OC]; datasheet-class strengths [IR];
  * magnetic pull: Maxwell stress on the tip faces at the record's clamp flux, fringing ignored (an upper bound) [OC];
    the unbalanced pull of three poles in series at constant current, reduced by the record's clamp law
    i = Psi/L (1 + (Psi/Psi_s)^6) applied per utron [IR];
  * the shaft and the counter-rotor: Euler-Bernoulli beams (consistent mass), the counter-rotor FLOATING on the shaft
    through the four inner bearings, only the two end bearings to the (rigid) frame [IR]; bearings as linear springs
    (Hertz stiffness at an axial spring preload) in series with their G10 spiders [IR/RH]; static and modal solves
    [OC: linear elasticity];
  * gap budget: worst-case (arithmetic) and statistical (RSS) stack-ups of the closing terms [IR];
  * windage: Daily & Nece (1960) enclosed rotating-disc correlations, Bilgen & Boulos (1973) Taylor-Couette torque (as
    used for machine air gaps by Saari 1998), Theodorsen & Regier (1944) for a cylinder in still air, form drag on the
    vane edges and on the salient utrons [IR correlations / RH coefficients]; bearing friction by Palmgren's M0 [IR];
  * balancing: ISO 21940-11 rigid-rotor grades, e_per = G / omega [OC: the standard's definition; IR: the grade].
Pure numpy / scipy; reads the repository's modules read-only (no .pyc is written).
"""
import sys

sys.dont_write_bytecode = True                         # read-only use of the record's modules

import json                                            # noqa: E402
import math                                            # noqa: E402
import os                                              # noqa: E402

import numpy as np                                     # noqa: E402
from scipy import linalg, optimize                     # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
import stack_sizing as S                               # noqa: E402
import utron_profile as U                              # noqa: E402

G0 = 9.80665
MU0 = 4e-7 * math.pi
PICK = "g 0.5 / 6 bridges / 1200 rpm"

# ---------------------------------------------------------------------------------------------------------------
# 0. inputs
# ---------------------------------------------------------------------------------------------------------------
RPM = 600.0                                            # each body; 1200 rpm relative (docs/ledger section 1)
OVERSPEED = 1.25                                       # spin-test / design overspeed [IR]
SPEEDS = {"600 rpm": RPM, "750 rpm": OVERSPEED * RPM}

# datasheet-class materials [IR]; rho of G10 / Al / SiFe / NiFe / Cu as the record uses them (sim/utron_profile.py,
# sim/stack_sizing.py, sim/shaft_bearings.py)
MAT = {
    "G10": dict(rho=1850.0, Ey=18e9, nu=0.15, Rm_inplane=250e6, bearing=200e6, shear_out=60e6, ilss=30e6,
                comp_flat=400e6, alpha_in=13e-6, alpha_in_range=(10e-6, 16e-6), alpha_thr=60e-6),
    "Al6061-T6": dict(rho=2700.0, Ey=69e9, nu=0.33, Rp=240e6, alpha=23.4e-6),
    "PEEK": dict(rho=1320.0, Ey=3.6e9, nu=0.40, Rm=95e6, alpha=47e-6),
    "borosilicate": dict(rho=2230.0, Ey=63e9, nu=0.20, design_tensile=7e6, alpha=3.3e-6),
    "SiFe M235-35A": dict(rho=7650.0, Ey=200e9, Rp=300e6, alpha=12e-6),
    "NiFe 80": dict(rho=8700.0, alpha=12.5e-6),
    "Cu": dict(rho=8900.0, Ey=117e9, Rp=60e6, alpha=17e-6),
    "steel A4 (316)": dict(rho=7950.0, Ey=193e9, alpha=16e-6),
    "bearing steel": dict(alpha=11.5e-6),
    "MnZn": dict(rho=4900.0),
}
A4_70 = dict(Rp=450e6, Rm=700e6, tau=0.6 * 700e6)      # ISO 3506-1 property class 70 [IR]
M6 = dict(dia=6.0, As=20.1, d3=4.773)                    # ISO 898 / 261 stress area, minor diameter (mm, mm^2)
M5 = dict(dia=5.0, As=14.2, d3=4.019)
MU_FRICTION = 0.2                                      # dry G10 / SiFe and G10 / G10 [IR]
BOND = dict(flatwise=5e6, shear=5e6)                   # epoxy VPI or bonding varnish, conservative [RH]
AIR = dict(rho=1.204, mu=1.81e-5, nu=1.81e-5 / 1.204)  # 20 C, 1013 hPa [OC]


def load(rel):
    with open(os.path.join(ROOT, rel)) as f:
        return json.load(f)


def inputs():
    op = load("sim/pole_design_variants_op.json")["designs"][PICK]
    sp = U.spec(op["design"], op["best"])
    air = [q for q in load("sim/air_stack_sizing_results.json")["thick_vanes"]["compare"]
           if q["t_vaneMm"] == 3.0 and q["n_plates"] == 6][0]
    cusp = [r for r in load("sim/ah_steady_cusp_results.json")["rows"] if r["C_byp_mF"] == 22.0][0]
    core = load("sim/core_field_results.json")["design"]
    hub = load("presets/hub-locked.json")
    belt = dict(magnetic_W=cusp["P_belt_W"], iron_W=2 * op["best"]["P_fe_side_W"], electrostatic_W=core["P_clamped_W"])
    belt["total_W"] = sum(belt.values())
    return dict(op=op, sp=sp, air=air, hub=hub, belt=belt,
                sources=dict(utron="sim/utron_profile.py spec of sim/pole_design_variants_op.json '" + PICK + "'",
                             stack="sim/air_stack_sizing_results.json thick_vanes.compare (t 3 mm, 6 + 6)",
                             hub="presets/hub-locked.json",
                             belt_magnetic="sim/ah_steady_cusp_results.json rows (C_byp 22 mF) P_belt_W",
                             belt_iron="sim/pole_design_variants_op.json best P_fe_side_W x 2",
                             belt_es="sim/core_field_results.json design.P_clamped_W"))


def layout(sp, hub_mm):
    """the build along the shaft: sim/stack_sizing.layout with the air stack of record (3 mm vanes, 6 + 6, 6 mm gaps,
    Ca / Cb 6 plates with 5 gaps), the wound reluctance section and the locked hub (z = 0 at the bottom, side A)."""
    p = dict(S.TUBE_DEFAULTS)
    p.update(g_vMm=6.0, t_vaneMm=3.0, n_plates=6, N_sec=12, ws_deg=22.0, wr_deg=22.0, pitch_fixed_mm=9.0, bucket=False,
             dielectric="air", hub_mm=hub_mm, hv_on_rotor=True, rel=dict(sp, kind="wound"))
    n_pl, t, g, n_ca = 6, 3.0, 6.0, 5
    L_var, L_ca = 2 * n_pl * t + (2 * n_pl - 1) * g, n_ca * p["pitch_fixed_mm"]
    side = L_var + L_ca
    el = S.layout(p, n_pl, 0, n_ca, L_var, 0.0, L_ca, side, 2 * side + hub_mm)
    get = lambda kind, side=None, where=None: [x for x in el if x["kind"] == kind and (side is None or x["side"] == side)
                                               and (where is None or x.get("where") == where)]
    z = {}
    for s in ("A", "B"):
        z[f"end_{s}"] = get("bearing", s, "end")[0]["zc"]
        z[f"carel_{s}"] = get("bearing", s, "Ca|reluctance")[0]["zc"]
        z[f"hubface_{s}"] = get("bearing", s, "hub face")[0]["zc"]
        u = get("w utron", s)[0]
        z[f"stack_{s}"] = (u["zs0"], u["zs1"])
        z[f"utron_{s}"] = (u["z0"], u["z1"])
        z[f"discs_{s}"] = [0.5 * (x["z0"] + x["z1"]) for x in get("w disc", s)]
        r = get("w ring", s)[0]
        z[f"ring_{s}"] = (r["z0"], r["z1"])
        v = [x for x in el if x["side"] == s and x["kind"].endswith("vane")]
        z[f"rotor_vanes_{s}"] = (min(x["z0"] for x in v if x["body"] == "rotor"), max(x["z1"] for x in v if x["body"] == "rotor"))
        z[f"stator_vanes_{s}"] = (min(x["z0"] for x in v if x["body"] == "stator"), max(x["z1"] for x in v if x["body"] == "stator"))
        c = [x for x in el if x["side"] == s and x["kind"] in ("Ca plate", "Cb plate")]
        z[f"ca_{s}"] = (min(x["z0"] for x in c), max(x["z1"] for x in c))
        f = get("flange", s)[0]
        z[f"flange_{s}"] = (f["z0"], f["z1"])
    h = get("hub")[0]
    z["hub"] = (h["z0"], h["z1"])
    z["L_total"] = max(x["z1"] for x in el)
    # the cage spans the inner bearing hubs (sim/tube_geometry.py: stator parts + non-end bearings), one tube across the hub
    z["cage"] = (get("bearing", "A", "Ca|reluctance")[0]["z0"], get("bearing", "B", "Ca|reluctance")[0]["z1"])
    return z


# ---------------------------------------------------------------------------------------------------------------
# 1. geometry, masses and centres of mass
# ---------------------------------------------------------------------------------------------------------------
def poly_props(pts):
    """area, centroid u and the second moment about the centroidal axis parallel to v (u = first coordinate)."""
    A = cu = Iu = 0.0
    npt = len(pts)
    for i in range(npt):
        (x0, y0), (x1, y1) = pts[i], pts[(i + 1) % npt]
        c = x0 * y1 - x1 * y0
        A += c
        cu += (x0 + x1) * c
        Iu += (x0 * x0 + x0 * x1 + x1 * x1) * c
    A *= 0.5
    cu /= (6 * A)
    Iu = Iu / 12.0 - A * cu * cu
    return abs(A), cu, abs(Iu)


def sector_rbar(r1, r2, beta_rad):
    """the radial position of an annular sector's centroid along its centre line [OC]."""
    return (2.0 / 3.0) * (r2 ** 3 - r1 ** 3) / (r2 ** 2 - r1 ** 2) * math.sin(beta_rad / 2) / (beta_rad / 2)


def utron_parts(sp):
    """[(part, kg, u_centroid_mm)] of one utron (sim/utron_profile.py's parts and densities), and the half-core's
    section (area, centroid, I) for the stack-as-beam check."""
    L = sp["L"]
    hole = math.pi * (sp["stud_d"] / 2) ** 2
    A_hc, u_hc, I_hc = poly_props(U.half_core(sp, +1, arc=True))
    st = sp["studs"]
    A_net = A_hc - 2 * hole
    u_net = (A_hc * u_hc - hole * (st[0][0] + st[1][0])) / A_net
    I_net = (I_hc + A_hc * (u_hc - u_net) ** 2) - sum(hole * (u - u_net) ** 2 for u, _ in st)   # holes' own I ignored
    rects = U.rects(sp)
    sife = 2 * A_net * L * 1e-9 * U.RHO_FE
    strip = rects["strip"]
    nife = (strip[1] - strip[0]) * (strip[3] - strip[2]) * L * 1e-9 * U.RHO_NIFE
    sp_r = rects["spacer"]
    a_sp = (sp_r[1] - sp_r[0]) * (sp_r[3] - sp_r[2])
    A_w, u_w, _ = poly_props(U.wedge(sp))
    ch = rects["cheek_pos"]
    a_ch = (ch[1] - ch[0]) * (ch[3] - ch[2]) - 2 * hole
    m_ch = a_ch * sp["t_cheek"] * 1e-9 * U.RHO_G10
    cu = sp["m_cu_kg"]
    u_cu = 0.5 * (sp["u_m0"] + sp["u_p1"])            # the turn is symmetric about the mid-line of its two sides [OC]
    parts = [("SiFe half-cores (2)", sife, u_net), ("NiFe neck strip", nife, 0.5 * (strip[0] + strip[1])),
             ("Cu coil", cu, u_cu), ("G10 spacer", a_sp * L * 1e-9 * U.RHO_G10, 0.5 * (sp_r[0] + sp_r[1])),
             ("G10 slot cover", A_w * L * 1e-9 * U.RHO_G10, u_w),
             ("G10 cheeks (4)", 4 * m_ch, 0.5 * (ch[0] + ch[1]))]
    return parts, dict(A_mm2=A_net, u_mm=u_net, I_mm4=I_net, A_gross_mm2=A_hc, cheek_m_kg=m_ch)


def masses(inp, z, shaft_dia=25.0):
    """per body: [(item, kg, z_mm or (z0, z1), r_cm_mm or None, source / tag)], and the derived CoM radii."""
    sp, air, hv = inp["sp"], inp["air"], inp["hub"]
    parts, hc = utron_parts(sp)
    m_u = sum(m for _, m, _ in parts)
    r_u = sum(m * u for _, m, u in parts) / m_u
    beta = math.radians(sp["br_deg"])
    m_br = sp["m_bridge_kg"]
    r_br = sector_rbar(sp["r_br0"], sp["r_br1"], beta)
    pocket = 6 * beta / 2 * (sp["r_br1"] ** 2 - sp["r_ring0"] ** 2) * sp["L"]
    L_ring = z["ring_A"][1] - z["ring_A"][0]
    m_ring = (math.pi * (sp["r_ring1"] ** 2 - sp["r_ring0"] ** 2) * L_ring - pocket) * 1e-9 * MAT["G10"]["rho"]
    rho_al = MAT["Al6061-T6"]["rho"]
    ann = math.pi * (150.0 ** 2 - 50.0 ** 2)
    frac = 6 * 22.0 / 360.0
    a_sector = ann * frac / 6                                              # one 22 deg sector, r 50-150 (mm^2)
    m_sector = a_sector * 3.0 * 1e-9 * rho_al
    r_sector = sector_rbar(50.0, 150.0, math.radians(22.0))
    m_rv = air["rotor_vanes_kg"] / 12                                      # per vane (6 per side, both sides)
    m_sv = air["stator_vanes_kg"] / 12
    m_ca = air["ca_plates_kg"] / 12
    sleeve_mu = math.pi * (S.SLEEVE_R ** 2 - S.SHAFT_R ** 2) * 1e-6 * MAT["G10"]["rho"]       # kg/m
    sleeve_spans = [(z["utron_A"][0] - 3.0, z["carel_A"] - 10.0), (z["carel_A"] + 10.0, z["hubface_A"] - 10.0),
                    (z["hubface_B"] + 10.0, z["carel_B"] - 10.0), (z["carel_B"] + 10.0, z["utron_B"][1] + 3.0)]
    L_sleeve = sum(b - a for a, b in sleeve_spans)
    rho_s = MAT["steel A4 (316)"]["rho"]
    L_shaft = (z["flange_A"][0] - 0.0) + (z["L_total"] - z["flange_B"][1])
    m_shaft = math.pi / 4 * shaft_dia ** 2 * L_shaft * 1e-9 * rho_s
    m_flange = math.pi * S.FLANGE_R ** 2 * S.FLANGE_T * 1e-9 * rho_s
    # the hub (presets/hub-locked.json): vessel, AH cores and coils, PEEK retainer, gel, G10 coupler
    vd, vt = hv["vessel"]["value"]["od_mm"], hv["vessel_wall"]["value"]["t_mm"]
    R_o, R_i = vd / 2, vd / 2 - vt
    m_glass = 4 / 3 * math.pi * (R_o ** 3 - R_i ** 3) * 1e-9 * MAT["borosilicate"]["rho"]
    ah = hv["AH"]["value"]
    core_d, (cz0, cz1) = ah["core"]["d_mm"], ah["core"]["absz_mm"]
    m_ahcore = 2 * math.pi / 4 * core_d ** 2 * (cz1 - cz0) * 1e-9 * MAT["MnZn"]["rho"]
    (cr0, cr1), (kz0, kz1) = ah["coil"]["r_mm"], ah["coil"]["absz_mm"]
    m_ahcoil = 2 * math.pi * (cr1 ** 2 - cr0 ** 2) * (kz1 - kz0) * 0.6 * 1e-9 * MAT["Cu"]["rho"]     # fill 0.6 [RH]
    ret = hv["retainer"]["value"]
    r_ret, z_ret = ret["r_max_mm"], ret["absz_max_mm"]
    v_ret = math.pi * r_ret ** 2 * 2 * z_ret - 4 / 3 * math.pi * (R_o + 0.5) ** 3 - 2 * math.pi * cr1 ** 2 * (cz1 - cz0)
    m_ret = v_ret * 1e-9 * MAT["PEEK"]["rho"]
    m_gel = 4 * math.pi * (R_o + 0.25) ** 2 * hv["interface_filler"]["value"]["t_mm"] * 1e-9 * 1000.0
    cw = hv["shaft_coupler"]["value"]["wall_mm"]
    m_coup = math.pi * ((r_ret + cw) ** 2 - r_ret ** 2) * 2 * z_ret * 1e-9 * MAT["G10"]["rho"]
    m_hub = m_glass + m_ahcore + m_ahcoil + m_ret + m_gel + m_coup
    zh = 0.5 * (z["hub"][0] + z["hub"][1])
    m_cage = math.pi * (166.0 ** 2 - 162.0 ** 2) * (z["cage"][1] - z["cage"][0]) * 1e-9 * MAT["G10"]["rho"]
    m_spider = math.pi * (162.0 ** 2 - 26.0 ** 2) * S.BEARING["spider_t"] * 1e-9 * MAT["G10"]["rho"]   # full plate [IR]
    m_6205 = 0.128                                       # whole bearing, datasheet-class [IR]
    m_disc = sp["m_disc_kg"]
    rotor = []
    for s in ("A", "B"):
        rotor += [(f"utrons {s} (3)", 3 * m_u, 0.5 * sum(z[f"stack_{s}"]), r_u, "sim/utron_profile.py (as built)"),
                  (f"carrier discs {s} (2)", 2 * m_disc, list(z[f"discs_{s}"]), None, "sim/utron_profile.py m_disc_kg"),
                  (f"rotor vanes {s} (6)", 6 * m_rv, z[f"rotor_vanes_{s}"], None, "sim/air_stack_sizing_results.json"),
                  (f"Ca/Cb plates {s} (6)", 6 * m_ca, z[f"ca_{s}"], None, "sim/air_stack_sizing_results.json; on the rotor "
                   "(sim/core-field-findings.md section 7)"),
                  (f"flange {s}", m_flange, 0.5 * sum(z[f"flange_{s}"]), None, "sim/stack_sizing.py FLANGE_R / FLANGE_T")]
    brg_s = [z[k] for k in ("end_A", "carel_A", "hubface_A", "hubface_B", "carel_B", "end_B")]    # point lists
    brg_c = [z[k] for k in ("carel_A", "hubface_A", "hubface_B", "carel_B")]
    rotor += [("shaft halves (d %g, A4 / 316)" % shaft_dia, m_shaft, (0.0, z["L_total"]), None, "d: sim/stack_sizing.py / "
               "presets/hub-locked.json"),
              ("G10 sleeve", sleeve_mu * L_sleeve * 1e-3, "sleeve", None, "sim/stack_sizing.py SLEEVE_R"),
              ("hub (vessel, AH, PEEK retainer, gel, G10 coupler)", m_hub, zh, None, "presets/hub-locked.json"),
              ("bearing inner rings (6)", 6 * 0.35 * m_6205, brg_s, None, "[IR] 35 % of a 6205"),
              ("La / Lb chokes (first cut, tau 0.5 s)", 2 * (1.00 + 0.41), zh, None, "sim/rotor-parts-duty-findings.md section 1 [RH]"),
              ("electronics: Z1 / Z4, D1-D4, CW chains, D1*-D4*, snubbers, bypass, wiring, potting", 1.5, zh, None,
               "[RH] not designed")]
    counter = []
    for s in ("A", "B"):
        counter += [(f"bridges {s} (6)", 6 * m_br, 0.5 * sum(z[f"stack_{s}"]), r_br, "sim/utron_profile.py m_bridge_kg"),
                    (f"bridge ring {s}", m_ring, z[f"ring_{s}"], None, "sim/utron_profile.py r_ring0 / r_ring1, layout"),
                    (f"stator vanes {s} (6)", 6 * m_sv, z[f"stator_vanes_{s}"], None, "sim/air_stack_sizing_results.json")]
    counter += [("G10 stator cage r 162-166", m_cage, z["cage"], None, "sim/tube_geometry.py cage; layout"),
                ("inner bearing spiders (4, G10 8 mm, r 26-162)", 4 * m_spider, brg_c, None, "sim/stack_sizing.py BEARING [IR]"),
                ("bearing outer rings, balls, cages (4)", 4 * 0.65 * m_6205, brg_c, None, "[IR] 65 % of a 6205")]
    out = dict(rotor=rotor, counter=counter, m_rotor=sum(m for _, m, *_ in rotor), m_counter=sum(m for _, m, *_ in counter),
               utron=dict(parts=parts, m_kg=m_u, r_cm_mm=r_u, record_m_kg=sp["m_utron_kg"], half_core=hc),
               bridge=dict(m_kg=m_br, r_cm_mm=r_br, ring_m_kg=m_ring, ring_L_mm=L_ring),
               vane=dict(m_sector_kg=m_sector, r_sector_mm=r_sector, m_rotor_vane_kg=m_rv, m_stator_vane_kg=m_sv,
                         m_ca_plate_kg=m_ca),
               hub=dict(glass=m_glass, ah_cores=m_ahcore, ah_coils=m_ahcoil, retainer=m_ret, gel=m_gel, coupler=m_coup,
                        total=m_hub),
               cage_kg=m_cage, spider_kg=m_spider, sleeve_kg_per_m=sleeve_mu, sleeve_spans=sleeve_spans,
               shaft_kg=m_shaft, flange_kg=m_flange, disc_kg=m_disc)
    return out


# ---------------------------------------------------------------------------------------------------------------
# 2. centrifugal loads, stresses and banding
# ---------------------------------------------------------------------------------------------------------------
def rotating_annulus_hoop(rho, nu, w, a, b, r):
    """hoop stress in a free rotating annular disc (plane stress, Lame) [OC]."""
    return (3 + nu) / 8 * rho * w * w * (b * b + a * a + a * a * b * b / (r * r) - (1 + 3 * nu) / (3 + nu) * r * r)


def centrifugal(inp, M):
    sp = inp["sp"]
    g10 = MAT["G10"]
    U_ = M["utron"]
    parts = U_["parts"]
    m_u, r_u = U_["m_kg"], U_["r_cm_mm"] * 1e-3
    m_ch = U_["half_core"]["cheek_m_kg"]
    m_studs = m_u - 4 * m_ch                                            # what the studs carry (all but the cheeks)
    r_studs = (sum(m * u for _, m, u in parts) - 4 * m_ch * 0.5 * (sp["u_ch0"] + sp["u_ch1"])) / m_studs * 1e-3
    hc = U_["half_core"]
    L = sp["L"]
    span = L + sp["t_cheek"]                                             # stud span between the cheeks' mid-planes
    I_d3 = math.pi * M6["d3"] ** 4 / 64
    Z_d3 = math.pi * M6["d3"] ** 3 / 32
    A_d3 = math.pi * M6["d3"] ** 2 / 4
    preload = 5.0e3                                                      # N per stud, ~55 % of the A4-70 M6 proof load [IR]
    preload_root = 3.5e3                                                 # N per M5 root bolt, ~55 % of proof [IR]
    rows = {}
    for tag, rpm in SPEEDS.items():
        w = 2 * math.pi * rpm / 60.0
        w2 = w * w
        F_u = m_u * w2 * r_u                                             # per utron, N
        F_st = m_studs * w2 * r_studs                                    # carried by the 4 studs
        f_stud = F_st / 4
        F_cheek = F_u / 4                                                # each of 4 cheeks
        # A. the bonded, preloaded stack is a beam between the cheeks; the studs carry it in shear at the two end faces
        w_hc = (F_st / 2) / L                                            # per half-core, N/mm
        M_hc = w_hc * L * L / 8
        c_hc = max(sp["r_g"] - hc["u_mm"], hc["u_mm"] - sp["u_n1"])
        sig_stack = M_hc * c_hc / hc["I_mm4"]                            # MPa, normal to the laminations
        tau_stack = 1.5 * (F_st / 4) / hc["A_mm2"]
        prestress = 2 * preload / hc["A_mm2"]                            # MPa, along w, from the two studs of a half-core
        tau_stud = (f_stud / 2) / A_d3                                   # two shear planes (the stack's end faces)
        fric = MU_FRICTION * 2 * preload                                 # N per half-core end face
        # B. no credit for the bond or the preload: the studs carry the stack as beams over the span
        q = f_stud / L
        M_b = (f_stud / 2) * (span / 2) - q * (L / 2) ** 2 / 2
        sig_stud_b = M_b / Z_d3
        defl_b = (q * L * (8 * span ** 3 - 4 * span * L * L + L ** 3)) / (384 * MAT["steel A4 (316)"]["Ey"] * 1e-6 * I_d3)
        # the cheeks (G10, 14 x 10 mm): net tension at the stud holes, bearing at the holes
        w_ch = sp["w_p"]
        sig_ch = F_cheek / ((w_ch - sp["stud_d"]) * sp["t_cheek"])
        brg_ch = (F_cheek / 2) / (M6["dia"] * sp["t_cheek"])
        # the cheek root: one A4-70 M5 per cheek through the 14 mm lap on the carrier disc (assumed) [IR]
        lap = sp["r_disc"] - sp["u_ch0"]
        edge = sp["r_disc"] - (sp["u_ch0"] + 0.5 * lap)                  # bolt to the disc's rim
        tau_root = F_cheek / (math.pi * M5["dia"] ** 2 / 4)
        brg_root = F_cheek / (M5["dia"] * sp["t_disc"])
        shear_out = F_cheek / (2 * (edge - M5["dia"] / 2) * sp["t_disc"])
        fric_root = MU_FRICTION * preload_root
        # the carrier disc: three utrons' half loads at r ~50 on a G10 ring r 20.5-57 x 12 [OC: thin ring, N point loads]
        f_disc = 2 * F_cheek
        a_d, b_d = S.SLEEVE_R, sp["r_disc"]
        Rm = 0.5 * (a_d + b_d)
        Ad = (b_d - a_d) * sp["t_disc"]
        Id = sp["t_disc"] * (b_d - a_d) ** 3 / 12
        al = math.pi / 3
        ten_ring = f_disc / (2 * math.sin(al))
        M_ring = f_disc * Rm / 2 * (1 / al - 1 / math.tan(al))
        sig_disc = ten_ring / Ad + M_ring * 0.5 * (b_d - a_d) / Id + \
            rotating_annulus_hoop(g10["rho"], g10["nu"], w, a_d * 1e-3, b_d * 1e-3, a_d * 1e-3) * 1e-6
        # the coil's slot side: an impregnated bundle (composite beam) or loose wires (each its own beam), over the stack
        m_side = sp["cv"] * 2 * sp["h_c"] * U.FILL * L * 1e-9 * U.RHO_CU_KG
        q_side = m_side * w2 * 0.5 * (sp["u_p0"] + sp["u_p1"]) * 1e-3 / L
        Ib = 2 * sp["cv"] * sp["h_c"] ** 3 / 12
        defl_vpi = 5 * q_side * L ** 4 / (384 * U.FILL * MAT["Cu"]["Ey"] * 1e-6 * Ib)
        n_w = sp["N_u"]
        I_w = n_w * math.pi * sp["wire_d_mm"] ** 4 / 64
        defl_loose = 5 * q_side * L ** 4 / (384 * MAT["Cu"]["Ey"] * 1e-6 * I_w)
        F_cu = sp["m_cu_kg"] * w2 * 0.5 * (sp["u_m0"] + sp["u_p1"]) * 1e-3
        p_former = F_cu / (2 * sp["cv"] * L)
        # the bridges in their ring (counter-rotor)
        m_b, r_b = M["bridge"]["m_kg"], M["bridge"]["r_cm_mm"] * 1e-3
        F_b = m_b * w2 * r_b
        p_floor = F_b / (math.radians(sp["br_deg"]) * sp["r_br1"] * L)
        R_r = 0.5 * (sp["r_br1"] + sp["r_ring1"])
        t_r = sp["r_ring1"] - sp["r_br1"]
        hoop_b = 6 * F_b / (2 * math.pi) / (t_r * L)                      # smeared over the 12 x 100 mm band behind the pockets
        M_rb = F_b * R_r / 2 * (1 / (math.pi / 6) - 1 / math.tan(math.pi / 6))
        bend_b = M_rb / (L * t_r ** 2 / 6)
        hoop_self = g10["rho"] * w2 * (R_r * 1e-3) ** 2 * 1e-6
        sig_ring = hoop_b + bend_b + hoop_self
        # the aluminium vanes (sector roots in radial tension, rings in hoop) and the Ca / Cb plates (free annuli)
        vane = M["vane"]
        F_sec = vane["m_sector_kg"] * w2 * vane["r_sector_mm"] * 1e-3
        root_r = F_sec / (math.radians(22.0) * 50.0 * 3.0)               # rotor sector root at r 50
        root_s = F_sec / (math.radians(22.0) * 150.0 * 3.0)              # stator sector root at r 150
        al_ = MAT["Al6061-T6"]
        ring_r = rotating_annulus_hoop(al_["rho"], al_["nu"], w, S.SLEEVE_R * 1e-3, 0.05, S.SLEEVE_R * 1e-3) * 1e-6 + \
            2 * (6 * F_sec / (2 * math.pi * 50.0 * 3.0)) * 50.0 ** 2 / (50.0 ** 2 - S.SLEEVE_R ** 2)
        ring_s = al_["rho"] * w2 * 0.156 ** 2 * 1e-6 + (F_sec / (2 * math.sin(math.pi / 6))) / (12.0 * 3.0)   # 6 loads
        ca = rotating_annulus_hoop(al_["rho"], al_["nu"], w, 0.05, 0.15, 0.05) * 1e-6
        # the G10 cage (r 162-166) and the stator vanes' rings pressing on it
        cage_self = g10["rho"] * w2 * 0.164 ** 2 * 1e-6
        F_vane = (6 * vane["m_sector_kg"] * vane["r_sector_mm"] + (vane["m_stator_vane_kg"] - 6 * vane["m_sector_kg"]) * 156.0) * 1e-3 * w2
        p_cage = F_vane / (2 * math.pi * 162.0 * 3.0)
        b_eff = 3.0 + 1.56 * math.sqrt(162.0 * 4.0)
        cage = cage_self + p_cage * 162.0 / 4.0 * (3.0 / b_eff)
        # the hub: glass sphere, PEEK retainer, G10 coupler; the gel's grip
        gl, pk = MAT["borosilicate"], MAT["PEEK"]
        glass = gl["rho"] * w2 * 0.025 ** 2 * 1e-6
        peek = (3 + pk["nu"]) / 8 * pk["rho"] * w2 * 0.030 ** 2 * 1e-6
        coup = g10["rho"] * w2 * 0.0315 ** 2 * 1e-6
        rows[tag] = dict(
            omega=w, g_at_r130=w2 * 0.13 / G0, F_utron_N=F_u, F_on_studs_N=F_st, F_per_stud_N=f_stud, F_per_cheek_N=F_cheek,
            stack_bend_MPa=sig_stack, stack_shear_MPa=tau_stack, stack_prestress_MPa=prestress, stud_shear_MPa=tau_stud,
            friction_per_end_face_N=fric, end_face_load_N=F_st / 4,
            studs_as_beams=dict(bend_MPa=sig_stud_b, deflection_mm=defl_b),
            cheek_net_MPa=sig_ch, cheek_bearing_MPa=brg_ch,
            root_bolt_shear_MPa=tau_root, root_bearing_MPa=brg_root, disc_shear_out_MPa=shear_out,
            root_friction_N=fric_root, disc_MPa=sig_disc, disc_ring_tension_N=ten_ring,
            coil=dict(slot_side_kg=m_side, defl_impregnated_mm=defl_vpi, defl_loose_wires_mm=defl_loose,
                      F_coil_N=F_cu, former_pressure_MPa=p_former),
            bridge=dict(F_N=F_b, pocket_floor_MPa=p_floor, ring_hoop_MPa=hoop_b, ring_bend_MPa=bend_b,
                        ring_self_MPa=hoop_self, ring_total_MPa=sig_ring),
            vanes=dict(F_sector_N=F_sec, rotor_root_MPa=root_r, stator_root_MPa=root_s, rotor_ring_MPa=ring_r,
                       stator_ring_MPa=ring_s, ca_plate_bore_MPa=ca),
            cage_MPa=cage, hub=dict(glass_MPa=glass, peek_MPa=peek, coupler_MPa=coup))
    hi = rows["750 rpm"]
    sf = [("utron stack as a beam (bond, normal to the laminations)", BOND["flatwise"] / (hi["stack_bend_MPa"] * 1e6), "[RH] bond"),
          ("  ... the same with the stud preload (stack never decompresses)", hi["stack_prestress_MPa"] / hi["stack_bend_MPa"], "[IR]"),
          ("A4-70 M6 studs, shear at the stack's end faces", A4_70["tau"] / (hi["stud_shear_MPa"] * 1e6), "[IR]"),
          ("stack-to-cheek friction (preload 5 kN per stud)", hi["friction_per_end_face_N"] / hi["end_face_load_N"], "[IR]"),
          ("studs as beams, NO bond or preload credit (yield)", A4_70["Rp"] / (hi["studs_as_beams"]["bend_MPa"] * 1e6), "[IR]"),
          ("G10 cheek, net tension at the stud holes", g10["Rm_inplane"] / (hi["cheek_net_MPa"] * 1e6), "[IR]"),
          ("G10 cheek, bearing at the stud holes", g10["bearing"] / (hi["cheek_bearing_MPa"] * 1e6), "[IR]"),
          ("A4-70 M5 cheek-root bolt, shear (assumed fastening)", A4_70["tau"] / (hi["root_bolt_shear_MPa"] * 1e6), "[IR]"),
          ("G10 carrier disc, shear-out at its rim", g10["shear_out"] / (hi["disc_shear_out_MPa"] * 1e6), "[IR]"),
          ("cheek-root friction (M5 preload 3.5 kN)", hi["root_friction_N"] / hi["F_per_cheek_N"], "[IR]"),
          ("G10 carrier disc, ring tension + bending", g10["Rm_inplane"] / (hi["disc_MPa"] * 1e6), "[IR]"),
          ("G10 bridge ring, hoop + bending + self", g10["Rm_inplane"] / (hi["bridge"]["ring_total_MPa"] * 1e6), "[IR]"),
          ("Al vanes, sector roots and rings", MAT["Al6061-T6"]["Rp"] / (max(hi["vanes"]["rotor_root_MPa"], hi["vanes"]["rotor_ring_MPa"],
                                                                           hi["vanes"]["stator_ring_MPa"]) * 1e6), "[IR]"),
          ("Al Ca / Cb plates, hoop at the bore", MAT["Al6061-T6"]["Rp"] / (hi["vanes"]["ca_plate_bore_MPa"] * 1e6), "[IR]"),
          ("G10 stator cage", g10["Rm_inplane"] / (hi["cage_MPa"] * 1e6), "[IR]"),
          ("PEEK retainer", MAT["PEEK"]["Rm"] / (hi["hub"]["peek_MPa"] * 1e6), "[IR]"),
          ("borosilicate vessel (rotation only)", MAT["borosilicate"]["design_tensile"] / (hi["hub"]["glass_MPa"] * 1e6), "[IR]")]
    return dict(rows=rows, sf_750=[dict(item=a, sf=b, tag=c) for a, b, c in sf], m_on_studs_kg=m_studs, r_studs_mm=r_studs * 1e3,
                assumed=dict(stud_preload_N=preload, root_bolt="1 x A4-70 M5 per cheek root, reamed hole, preload 3.5 kN",
                             friction=MU_FRICTION, bond_flatwise_MPa=BOND["flatwise"] * 1e-6))


# ---------------------------------------------------------------------------------------------------------------
# 3. the magnetic pull
# ---------------------------------------------------------------------------------------------------------------
def magnetic(inp):
    sp, op = inp["sp"], inp["op"]["best"]
    psi_s, N, n_u = op["psi_s"], op["N_u"], 3
    phi_s = psi_s / (n_u * N)                                            # Wb per utron at the clamp
    A = sp["w_p"] * sp["L"] * 1e-6                                       # one tip face
    B = phi_s / A
    F_face = phi_s ** 2 / (2 * MU0 * A)
    F_u = 2 * F_face
    # peak flux with the record's law i = Psi / L (1 + (Psi/Psi_s)^6) at the aligned L and the branch's peak current
    x_pk = optimize.brentq(lambda x: x * (1 + x ** 6) - op["I_pk"] * op["L_group_H"] / psi_s, 0.1, 3.0)
    D = lambda x: 1 + 6 * x ** 6 / (1 + x ** 6)                          # d ln(MMF) / d ln(Phi) of the law
    g = sp["g"] * 1e-3
    k_lin = 3 * F_u / g                                                  # 3 poles, constant current, linear iron [OC]
    xs = np.linspace(0.05, x_pk, 400)
    k_law = 3 * F_u * xs ** 2 / (g * np.array([D(x) for x in xs]))
    k_max = float(k_law.max())
    w = 2 * math.pi * RPM / 60.0
    m_b, r_b = sp["m_bridge_kg"], sector_rbar(sp["r_br0"], sp["r_br1"], math.radians(sp["br_deg"])) * 1e-3
    rpm_eq = math.sqrt(F_u / (m_b * r_b)) * 60 / (2 * math.pi)
    return dict(phi_s_Wb=phi_s, phi_s_built_Wb=sp["phi_s_built_Wb"], tip_face_m2=A, B_gap_T=B, B_body_T_record=op["B_body_T"],
                F_face_N=F_face, F_utron_N=F_u, x_peak=x_pk, F_utron_peak_N=F_u * x_pk ** 2,
                k_lin_N_per_m=k_lin, k_lin_peak_N_per_m=k_lin * x_pk ** 2, k_clamp_at_s_N_per_m=k_lin / D(1.0),
                k_clamp_max_N_per_m=k_max, x_at_k_max=float(xs[int(np.argmax(k_law))]),
                F_bridge_centrifugal_600_N=m_b * w * w * r_b, rpm_pull_equals_centrifugal=rpm_eq,
                note="per side, all three utrons aligned at once (A at rotor angle 0, B at 30 deg); the pull pulses at "
                     "the 120 Hz pump frequency, A and B in antiphase")


# ---------------------------------------------------------------------------------------------------------------
# 4. the shaft and the counter-rotor: a coupled beam model
# ---------------------------------------------------------------------------------------------------------------
def bearing_k(Fa=100.0, alpha_deg=10.0, Z=9, Dw=7.938):
    """radial stiffness of a 6205-class deep-groove bearing under an axial spring preload: Palmgren's point-contact
    deflection delta = 4.36e-4 q^(2/3) / Dw^(1/3) (mm, N) per ball, Z balls of Dw at contact angle alpha [IR]."""
    a = math.radians(alpha_deg)
    q_ball = Fa / (Z * math.sin(a))
    c = 4.36e-4 / Dw ** (1 / 3)
    kn = 1.5 * q_ball ** (1 / 3) / c                                          # N/mm, tangent
    return 0.5 * Z * kn * math.cos(a) ** 2 * 1e3                         # N/m


class Rotor2:
    """the shaft (with the hub coupler) and the floating counter-rotor, one lateral plane, SI units.
    Options: ground_all (the earlier sim/shaft_bearings.py model: every bearing to ground, i.e. a grounded counter-rotor);
    end_span_dia (a stepped shaft, that diameter between the end and Ca|rel bearing seats); extra_inner (more shaft-to-
    counter-rotor bearings at these z, each on a G10 end disc on its bridge ring); z_frame (the two frame bearings);
    z_belt (the pulley) [IR]."""

    def __init__(self, z, M, shaft_dia=25.0, k_inner=7.5e7, k_end=7.5e7, joint="coupler", k_mag=0.0, Ey_shaft=None,
                 ground_all=False, end_span_dia=None, extra_inner=(), z_frame=None, z_belt=None):
        self.z, self.M = z, M
        mm = 1e-3
        Ey_s = Ey_shaft or MAT["steel A4 (316)"]["Ey"]
        rho_s = MAT["steel A4 (316)"]["rho"]
        Ey_g = MAT["G10"]["Ey"]
        Lt = z["L_total"]
        self.z_frame = tuple(z_frame) if z_frame else (z["end_A"], z["end_B"])
        self.z_belt = z_belt if z_belt is not None else self.z_frame[0] - 50.0     # an overhung pulley [RH]
        self.extra_inner = list(extra_inner)
        cr0 = min([z["ring_A"][0]] + self.extra_inner)
        cr1 = max([z["ring_B"][1]] + self.extra_inner)
        s0 = min(-100.0, self.z_frame[0] - 40.0, self.z_belt - 20.0)
        s1 = max(Lt + 100.0, self.z_frame[1] + 40.0)
        keys = [s0, 0.0, Lt, s1, *self.z_frame, self.z_belt, *self.extra_inner]
        for s in ("A", "B"):
            keys += [z[f"end_{s}"], z[f"carel_{s}"], z[f"hubface_{s}"], *z[f"stack_{s}"], 0.5 * sum(z[f"stack_{s}"]),
                     *z[f"flange_{s}"], *z[f"ring_{s}"], *z[f"discs_{s}"]]
        keys += list(z["hub"]) + [0.5 * sum(z["hub"])]

        def nodes(kk, grid):
            """the key points plus a 10 mm grid, grid points within 2 mm of a key point dropped (no tiny elements)."""
            kk = np.unique(np.round(np.array(kk), 3))
            g_ = [x for x in grid if np.min(np.abs(kk - x)) > 2.0]
            return np.unique(np.concatenate([kk, np.array(g_)]))
        zs = nodes(keys, np.arange(s0, s1 + 1e-9, 10.0))
        zc = nodes([k for k in keys if cr0 <= k <= cr1] + [cr0, cr1], np.arange(cr0, cr1 + 1e-9, 10.0))
        self.zs, self.zc = zs, zc
        ns, nc = len(zs), len(zc)
        self.hinge = joint == "hinge"
        zh = 0.5 * sum(z["hub"])
        self.ih = int(np.argmin(np.abs(zs - zh)))
        ndof = 2 * ns + 2 * nc + (1 if self.hinge else 0)
        K = np.zeros((ndof, ndof)); Mm = np.zeros((ndof, ndof))
        self.ds = lambda i: (2 * i, 2 * i + 1)
        self.dc = lambda j: (2 * ns + 2 * j, 2 * ns + 2 * j + 1)
        I_sh = math.pi / 64 * (shaft_dia * mm) ** 4
        A_sh = math.pi / 4 * (shaft_dia * mm) ** 2
        I_fl = math.pi / 4 * (S.FLANGE_R * mm) ** 4
        hv = M["_hub_dims"]                                              # retainer r and coupler wall (m)
        I_cp = math.pi / 4 * ((hv[0] + hv[1]) ** 4 - hv[0] ** 4)
        self.EI = dict(shaft=Ey_s * I_sh, coupler=Ey_g * I_cp)
        mu_cp = M["hub"]["coupler"] / ((z["hub"][1] - z["hub"][0]) * mm)
        spans = [(z["end_A"] + 10.0, z["carel_A"] - 10.0), (z["carel_B"] + 10.0, z["end_B"] - 10.0)]
        for ie in range(ns - 1):
            za, zb = zs[ie], zs[ie + 1]
            zm = 0.5 * (za + zb)
            if z["hub"][0] < zm < z["hub"][1]:
                EI, mu = Ey_g * I_cp, mu_cp                                # the G10 coupler; the hub's contents are lumped
            elif any(f[0] - 1e-9 <= zm <= f[1] + 1e-9 for f in (z["flange_A"], z["flange_B"])):
                EI, mu = Ey_s * I_fl, rho_s * math.pi * (S.FLANGE_R * mm) ** 2
            elif end_span_dia and any(a <= zm <= b for a, b in spans):
                EI, mu = Ey_s * math.pi / 64 * (end_span_dia * mm) ** 4, rho_s * math.pi / 4 * (end_span_dia * mm) ** 2
            else:
                EI, mu = Ey_s * I_sh, rho_s * A_sh
            dofs = [*self.ds(ie), *self.ds(ie + 1)]
            if self.hinge and ie == self.ih:                             # the element right of the hinge node
                dofs[1] = ndof - 1
            self._add(K, Mm, dofs, (zb - za) * mm, EI, mu)
        I_cage = math.pi / 4 * (0.166 ** 4 - 0.162 ** 4)
        I_ring = math.pi / 4 * ((M["_ring_r"][1] * mm) ** 4 - (M["_ring_r"][0] * mm) ** 4)
        mu_cage = M["cage_kg"] / ((z["cage"][1] - z["cage"][0]) * mm)
        mu_ring = M["bridge"]["ring_m_kg"] / (M["bridge"]["ring_L_mm"] * mm)
        for ie in range(nc - 1):
            za, zb = zc[ie], zc[ie + 1]
            zm = 0.5 * (za + zb)
            in_ring = z["ring_A"][0] <= zm <= z["ring_A"][1] or z["ring_B"][0] <= zm <= z["ring_B"][1]
            in_cage = z["cage"][0] <= zm <= z["cage"][1]
            if not (in_ring or in_cage):                                 # an end disc's hub out to an extra bearing [IR]
                EI, mu = Ey_g * I_ring, 0.0
            else:
                EI = max(Ey_g * I_ring if in_ring else 0.0, Ey_g * I_cage if in_cage else 0.0)
                mu = (mu_ring if in_ring else 0.0) + (mu_cage if in_cage else 0.0)
            self._add(K, Mm, [*self.dc(ie), *self.dc(ie + 1)], (zb - za) * mm, EI, max(mu, 1e-3))
        # lumped / distributed masses of the parts (the shaft, flanges, coupler, cage and rings are in the beams)
        for body, items in (("s", M["rotor"]), ("c", M["counter"])):
            for name, m, where, _, _ in items:
                if name.startswith(("shaft", "flange", "G10 stator cage", "bridge ring")):
                    continue
                if name.startswith("hub"):
                    m -= M["hub"]["coupler"]
                if where == "sleeve":
                    L_tot = sum(b - a for a, b in M["sleeve_spans"])
                    for a, b in M["sleeve_spans"]:
                        self.add_mass(Mm, "s", (a, b), m * (b - a) / L_tot)
                    continue
                self.add_mass(Mm, body, where, m)
        m_disc_end = math.pi * (M["_ring_r"][1] ** 2 - 26.0 ** 2) * 10.0 * 1e-9 * MAT["G10"]["rho"]   # G10 end disc, 10 mm
        for zz in self.extra_inner:
            self.add_mass(Mm, "c", zz, m_disc_end + 0.65 * 0.128)
        self.springs = []
        for s, zf in zip(("A", "B"), self.z_frame):
            self.springs.append((f"frame {s}", self.node("s", zf), None, k_end))
        for name in ("carel_A", "hubface_A", "hubface_B", "carel_B"):
            self.springs.append((name.replace("carel", "Ca|rel").replace("hubface", "hub face").replace("_", " "),
                                 self.node("s", z[name]), self.node("c", z[name]), k_inner))
        for zz in self.extra_inner:
            side = "A" if zz < 0.5 * Lt else "B"
            self.springs.append((f"ring end {side}", self.node("s", zz), self.node("c", zz), k_inner))
        for nm, i, j, k in self.springs:
            self._spring(K, i, j, k)
        if ground_all:                                                   # the earlier model: the counter-rotor is ground
            for name in ("carel_A", "hubface_A", "hubface_B", "carel_B"):
                self._spring(K, self.node("c", z[name]), None, 1e13)
                K[self.node("c", z[name]) + 1, self.node("c", z[name]) + 1] += 1e9
        self.ground_all = ground_all
        self.k_mag = k_mag
        if k_mag:
            for s in ("A", "B"):
                for zz, wgt in zip(self.stack_pts(s), (0.25, 0.5, 0.25)):
                    self._spring(K, self.node("s", zz), self.node("c", zz), -k_mag * wgt)
        self.K, self.Mm, self.ndof = K, Mm, ndof

    @staticmethod
    def _add(K, Mm, dofs, l, EI, mu):
        k = EI / l ** 3 * np.array([[12, 6 * l, -12, 6 * l], [6 * l, 4 * l * l, -6 * l, 2 * l * l],
                                    [-12, -6 * l, 12, -6 * l], [6 * l, 2 * l * l, -6 * l, 4 * l * l]])
        m = mu * l / 420 * np.array([[156, 22 * l, 54, -13 * l], [22 * l, 4 * l * l, 13 * l, -3 * l * l],
                                     [54, 13 * l, 156, -22 * l], [-13 * l, -3 * l * l, -22 * l, 4 * l * l]])
        for a in range(4):
            for b in range(4):
                K[dofs[a], dofs[b]] += k[a, b]
                Mm[dofs[a], dofs[b]] += m[a, b]

    def node(self, body, zz):
        arr = self.zs if body == "s" else self.zc
        i = int(np.argmin(np.abs(arr - zz)))
        return self.ds(i)[0] if body == "s" else self.dc(i)[0]

    def add_mass(self, Mm, body, where, m):
        """a point mass at z, m spread over a span tuple (z0, z1) (7 points), or shared by a list of points."""
        if isinstance(where, (tuple, list)):
            pts = np.linspace(where[0], where[1], 7) if isinstance(where, tuple) else np.array(where)
            for p in pts:
                Mm[self.node(body, p), self.node(body, p)] += m / len(pts)
        else:
            Mm[self.node(body, where), self.node(body, where)] += m

    @staticmethod
    def _spring(K, i, j, k):
        K[i, i] += k
        if j is not None:
            K[j, j] += k; K[i, j] -= k; K[j, i] -= k

    def stack_pts(self, s):
        a, b = self.z[f"stack_{s}"]
        return (a, 0.5 * (a + b), b)

    def gap(self, u, s):
        """relative radial displacement shaft - counter-rotor at the stack's ends and centre (m)."""
        return np.array([u[self.node("s", p)] - u[self.node("c", p)] for p in self.stack_pts(s)])

    def solve(self, f):
        return linalg.solve(self.K, f, assume_a="sym")

    def modes(self, n_modes=6):
        w2, vecs = linalg.eigh(self.K, self.Mm)
        out = []
        for k in range(n_modes):
            v = vecs[:, k]
            ke = v * (self.Mm @ v)
            ns = len(self.zs)
            ts = float(np.sum(ke[:2 * ns])); tc = float(np.sum(ke[2 * ns:2 * ns + 2 * len(self.zc)]))
            out.append(dict(f_Hz=math.sqrt(max(w2[k], 0.0)) / (2 * math.pi), kinetic_rotor=ts / (ts + tc),
                            kinetic_counter=tc / (ts + tc)))
        return out, w2

    def offsets(self):
        """influence of a unit eccentricity at each bearing on the relative displacement at the two stacks
        (max over the stack's ends and centre, with sign at that point)."""
        res = {}
        for nm, i, j, k in self.springs:
            f = np.zeros(self.ndof)
            f[i] += k
            if j is not None:
                f[j] -= k
            u = self.solve(f)
            res[nm] = {s: self.gap(u, s).tolist() for s in ("A", "B")}
        return res

    def gravity(self):
        gv = np.zeros(self.ndof)
        gv[0:2 * len(self.zs):2] = G0
        gv[2 * len(self.zs):2 * len(self.zs) + 2 * len(self.zc):2] = G0
        f = self.Mm @ gv
        u = self.solve(f)
        loads = {nm: float(k * (u[i] - (u[j] if j is not None else 0.0))) for nm, i, j, k in self.springs}
        ws = u[0:2 * len(self.zs):2]
        return dict(gap_A_um=(self.gap(u, "A") * 1e6).tolist(), gap_B_um=(self.gap(u, "B") * 1e6).tolist(),
                    shaft_max_um=float(np.max(np.abs(ws)) * 1e6), bearing_loads_N=loads)

    def pair_force(self, s, F=1.0):
        f = np.zeros(self.ndof)
        for zz, wgt in zip(self.stack_pts(s), (0.25, 0.5, 0.25)):
            f[self.node("s", zz)] += F * wgt
            f[self.node("c", zz)] -= F * wgt
        u = self.solve(f)
        return self.gap(u, s), u

    def point_force(self, body, zz, F):
        f = np.zeros(self.ndof)
        f[self.node(body, zz)] += F
        return self.solve(f)


def fe_study(z, M, mag):
    """the coupled model: bearing stiffness, modes, 1 g, the relative stiffness at the stacks, the runout influence
    coefficients, the magnetic pull's amplification, a belt pull, the unbalance."""
    kb = dict(preload_50N=bearing_k(50.0), preload_100N=bearing_k(100.0), record=2e8)
    k_sp = 3e8                                                           # G10 spider / frame housing, radial [RH]
    k_eff = lambda kbr: 1.0 / (1.0 / kbr + 1.0 / k_sp)
    nominal = dict(shaft_dia=25.0, k_inner=k_eff(kb["preload_100N"]), k_end=k_eff(kb["preload_100N"]), joint="coupler")
    cases = {"Ø25, preload 100 N (nominal)": nominal,
             "Ø30, preload 100 N": dict(nominal, shaft_dia=30.0),
             "Ø25, hub as a hinge": dict(nominal, joint="hinge"),
             "Ø25, record's 2e8 N/m, rigid spiders": dict(nominal, k_inner=2e8, k_end=2e8),
             "Ø25, soft: 3e7 N/m": dict(nominal, k_inner=3e7, k_end=3e7),
             "Ø25, Ti-6Al-4V shaft (Young's modulus 114 GPa)": dict(nominal, Ey_shaft=114e9),
             "record's model on this build: all six to ground, 2e8 N/m": dict(nominal, k_inner=2e8, k_end=2e8, ground_all=True),
             "Ø25, end spans stepped to Ø40": dict(nominal, end_span_dia=40.0),
             "Ø30, end spans stepped to Ø40": dict(nominal, shaft_dia=30.0, end_span_dia=40.0),
             "Ø25, 8 bearings: + one at each bridge ring's outer end": dict(nominal, extra_inner=(z["end_A"] + 18.0, z["end_B"] - 18.0)),
             "Ø30, 8 bearings": dict(nominal, shaft_dia=30.0, extra_inner=(z["end_A"] + 18.0, z["end_B"] - 18.0)),
             "Ø25, the drive proposal: gear-end bearing on side A": dict(nominal, extra_inner=(1.0,), z_frame=(-87.5, z["end_B"]),
                                                                        z_belt=-114.0),
             # the record's own parameters (sim/shaft_bearings.py two_body: 2e8 N/m, E 210 GPa), for the cross-check
             "cross-check, 6 bearings at the record's 2e8 N/m and 210 GPa steel": dict(nominal, k_inner=2e8, k_end=2e8, Ey_shaft=210e9),
             "cross-check, 8 bearings at the record's 2e8 N/m and 210 GPa steel": dict(nominal, k_inner=2e8, k_end=2e8, Ey_shaft=210e9,
                                                                                   extra_inner=(z["end_A"] + 18.0, z["end_B"] - 18.0))}
    out = dict(k_bearing_N_per_m=kb, k_spider_N_per_m=k_sp, k_effective_N_per_m=k_eff(kb["preload_100N"]), cases={})
    for name, c in cases.items():
        m = Rotor2(z, M, **c)
        md, _ = m.modes(6)
        gr = m.gravity()
        dA, _ = m.pair_force("A")
        k_rel = 1.0 / float(np.max(np.abs(dA)))
        off = m.offsets()
        row = dict(params={k: v for k, v in c.items()}, modes=md, gravity_1g=gr, k_rel_A_N_per_m=k_rel, offsets=off,
                   EI_shaft=m.EI["shaft"], EI_coupler=m.EI["coupler"], z_frame_mm=m.z_frame, z_belt_mm=m.z_belt,
                   z_extra_inner_mm=m.extra_inner, n_inner=4 + len(m.extra_inner))
        for s in ("A", "B"):
            a = {nm: float(np.max(np.abs(v[s]))) for nm, v in off.items()}
            row[f"influence_{s}"] = dict(each=a, sum=sum(a.values()), rss=math.sqrt(sum(x * x for x in a.values())))
        # with the magnetic pull (the bound and the clamp-law value) on both sides at once [IR: conservative]
        for tag, km in (("clamp", mag["k_clamp_max_N_per_m"]), ("bound", mag["k_lin_N_per_m"]), ("extreme", mag["k_lin_peak_N_per_m"])):
            mk = Rotor2(z, M, k_mag=km, **c)
            ev = linalg.eigvalsh(mk.K)
            mdk, _ = mk.modes(3)
            offk = mk.offsets()
            amp = []
            for nm in off:
                for s in ("A", "B"):
                    a0 = np.max(np.abs(off[nm][s])); a1 = np.max(np.abs(offk[nm][s]))
                    if a0 > 1e-3:
                        amp.append(a1 / a0)
            row[f"mag_{tag}"] = dict(k_mag_N_per_m=km, ratio_k_mag_to_k_rel=km / k_rel, stable=bool(ev.min() > 0),
                                     f1_Hz=mdk[0]["f_Hz"], amplification=max(amp), offsets=offk)
        # a belt pull of 100 N on a pulley overhung 50 mm beyond the frame bearing (the drive is not designed) [RH]
        u = m.point_force("s", m.z_belt, 100.0)
        row["belt_100N"] = dict(z_mm=m.z_belt, gap_A_um=(m.gap(u, "A") * 1e6).tolist(), gap_B_um=(m.gap(u, "B") * 1e6).tolist())
        out["cases"][name] = row
    return out


# ---------------------------------------------------------------------------------------------------------------
# 5. the 0.5 mm gap budget
# ---------------------------------------------------------------------------------------------------------------
ISO492 = {                                                               # 6205: d 25 (18-30), D 52 (50-80), um [IR]
    "P0": dict(K_ia=13, K_ea=25), "P6": dict(K_ia=8, K_ea=13), "P5": dict(K_ia=4, K_ea=8), "P4": dict(K_ia=3, K_ea=5)}
CLEARANCE = dict(C2=(1, 11), CN=(5, 20), C3=(13, 28))                   # radial internal clearance, d 24-30, um [IR]
SEATS = dict(journal_TIR_um=5.0, housing_TIR_um=10.0)                   # proposed seat runouts to the datum axes [IR]


def thermal(sp):
    """radial thermal growth of the tip circle (rotor) and of the bridge faces (counter-rotor), cold-ground at 20 C,
    running at the record's 40 C ambient (sim/pole_design.py T_AMB 313 K) with the coils at 46 C [IR chain model]."""
    g = MAT["G10"]
    a_s, a_b, a_fe = MAT["steel A4 (316)"]["alpha"], MAT["bearing steel"]["alpha"], MAT["SiFe M235-35A"]["alpha"]
    r_bolt = sp["u_ch0"] + 0.5 * (sp["r_disc"] - sp["u_ch0"])
    r_stud = 0.5 * (sp["studs"][0][0] + sp["studs"][1][0])
    r_pilot = 140.0                                                      # where the bridge ring is located on its spider [IR]

    def rotor(dT_amb, dT_core, dT_cheek, dT_disc, a_in):
        return (a_s * dT_amb * S.SHAFT_R + g["alpha_thr"] * dT_amb * (S.SLEEVE_R - S.SHAFT_R)
                + a_in * dT_disc * (r_bolt - S.SLEEVE_R) + a_in * dT_cheek * (r_stud - r_bolt)
                + a_fe * dT_core * (sp["r_g"] - r_stud))

    def counter(dT, a_in):
        return (a_s * dT * S.SHAFT_R + a_b * dT * (26.0 - S.SHAFT_R) + a_in * dT * (r_pilot - 26.0)
                + a_in * dT * (sp["r_br1"] - r_pilot) - a_fe * dT * sp["t_b"])
    lo, hi = g["alpha_in_range"]
    amb = 20.0
    nom_r = rotor(amb, amb + 6.0, amb + 4.0, amb + 2.0, g["alpha_in"])
    nom_c = counter(amb + 1.0, g["alpha_in"])
    worst_r = rotor(amb, amb + 6.0, amb + 4.0, amb + 2.0, hi) + 10e-6 * amb * (S.SLEEVE_R - S.SHAFT_R)
    worst_c = counter(amb, lo)
    self_heat = rotor(0.0, 6.0, 4.0, 2.0, g["alpha_in"])
    return dict(rotor_tip_growth_mm=nom_r, bridge_face_growth_mm=nom_c, closing_nominal_mm=nom_r - nom_c,
                closing_worst_mm=worst_r - worst_c, self_heating_only_mm=self_heat,
                chain=dict(r_bolt_mm=r_bolt, r_stud_mm=r_stud, r_pilot_mm=r_pilot),
                note="uniform +20 K (ground at 20 C, run at the record's 40 C ambient), the utron core +6 K over it "
                     "(46 C coils), cheek +4, disc +2; the counter-rotor +1 K (bridge iron 0.1 W each); worst: G10 in-plane "
                     "alpha 16e-6 on the rotor, 10e-6 on the counter-rotor, sleeve +10e-6 through the thickness")


def centrifugal_growth(inp, M, cent):
    """elastic radial growth of the tip circle (cheek tension, two bolted joints, the disc) and of the bridge faces
    (the ring's hoop strain); joint slip excluded (preloaded, fitted) [IR]."""
    sp = inp["sp"]
    Ey = MAT["G10"]["Ey"] * 1e-6                                          # N/mm^2
    r_bolt = sp["u_ch0"] + 0.5 * (sp["r_disc"] - sp["u_ch0"])
    r_stud = 0.5 * (sp["studs"][0][0] + sp["studs"][1][0])
    out = {}
    for tag, row in cent["rows"].items():
        Fc = row["F_per_cheek_N"]
        cheek = Fc * (r_stud - r_bolt) / (Ey * sp["w_p"] * sp["t_cheek"])
        joints = 2 * Fc / (Ey * sp["t_cheek"])                            # bolt-in-hole bearing compliance ~ 1 / (Ey t) [RH]
        Rm = 0.5 * (S.SLEEVE_R + sp["r_disc"])
        Id = sp["t_disc"] * (sp["r_disc"] - S.SLEEVE_R) ** 3 / 12
        al = math.pi / 3                                                 # thin ring, 3 equal radial loads (Roark), no sleeve
        disc = 2 * Fc * Rm ** 3 / (Ey * Id) * ((al + math.sin(al) * math.cos(al)) / (4 * math.sin(al) ** 2) - 1 / (2 * al))
        b = row["bridge"]
        R_r = 0.5 * (sp["r_br1"] + sp["r_ring1"])
        I_r = sp["L"] * (sp["r_ring1"] - sp["r_br1"]) ** 3 / 12
        th6 = math.pi / 6                                                # 6 radial loads: the ring bulges at each bridge
        local = b["F_N"] * R_r ** 3 / (Ey * I_r) * ((th6 + math.sin(th6) * math.cos(th6)) / (4 * math.sin(th6) ** 2) - 1 / (2 * th6))
        ring = (b["ring_hoop_MPa"] + b["ring_self_MPa"]) / Ey * sp["r_br1"] + local
        out[tag] = dict(tip_mm=cheek + joints + abs(disc), cheek_mm=cheek, joints_mm=joints, disc_mm=abs(disc),
                        bridge_face_open_mm=ring)
    return out


def gap_budget(inp, M, cent, mag, fe, th, cg):
    """the closing terms at the worst utron, per structural variant: the deterministic ones (profiles, centrifugal growth,
    the magnetic pull on the retention, thermal, a 100 N belt pull, the G2.5 unbalance whirl) and the eccentricity from
    the bearings (the variant's influence coefficients x the per-bearing eccentricity, x the magnetic amplification),
    stacked worst-case (all in phase) and statistically (RSS) [IR]."""
    sp = inp["sp"]
    g0 = sp["g"]
    m_max = max(M["m_rotor"], M["m_counter"])
    options = {
        "P0, CN clearance, no preload": dict(cls="P0", G_r=CLEARANCE["CN"][1]),
        "P0, axial spring preload": dict(cls="P0", G_r=0),
        "P6, axial spring preload": dict(cls="P6", G_r=0),
        "P5, axial spring preload": dict(cls="P5", G_r=0)}
    variants = ["Ø25, preload 100 N (nominal)", "Ø30, preload 100 N", "Ø30, end spans stepped to Ø40",
                "Ø25, 8 bearings: + one at each bridge ring's outer end", "Ø30, 8 bearings",
                "Ø25, the drive proposal: gear-end bearing on side A"]
    out = {}
    for vn in variants:
        v = fe["cases"][vn]
        infl = {}
        for s in ("A", "B"):
            each = v[f"influence_{s}"]["each"]
            inner = {k: a for k, a in each.items() if not k.startswith("frame")}
            frame = {k: a for k, a in each.items() if k.startswith("frame")}
            infl[s] = dict(inner=inner, frame=frame, sum=sum(inner.values()) + sum(frame.values()),
                           rss=math.sqrt(sum(a * a for a in inner.values()) + sum(a * a for a in frame.values())))
        side = max(("A", "B"), key=lambda s: infl[s]["sum"])
        I = infl[side]
        amp_c, amp_b = v["mag_clamp"]["amplification"], v["mag_bound"]["amplification"]
        k_rel, f1 = v["k_rel_A_N_per_m"], v["modes"][0]["f_Hz"]
        belt = max(max(map(abs, v["belt_100N"]["gap_A_um"])), max(map(abs, v["belt_100N"]["gap_B_um"]))) * 1e-3
        rows = {}
        for tag, rpm in SPEEDS.items():
            w = 2 * math.pi * rpm / 60.0
            dyn = 1.0 / abs(1.0 - (rpm / 60.0 / f1) ** 2)
            unb = m_max * (2.5 / w * 1e-3) * w * w / k_rel * dyn * 1e3
            det = dict(tip_profile=0.020, bridge_profile=0.020, centrifugal=cg[tag]["tip_mm"],
                       magnetic_on_retention=cg[tag]["tip_mm"] * mag["F_utron_peak_N"] / cent["rows"][tag]["F_utron_N"],
                       thermal_worst=th["closing_worst_mm"], belt_100N=belt, unbalance_G2p5=unb)
            res = {}
            for oname, o in options.items():
                b = ISO492[o["cls"]]
                TIR = b["K_ia"] + b["K_ea"] + SEATS["journal_TIR_um"] + SEATS["housing_TIR_um"] + o["G_r"]
                ecc_b = 0.5 * TIR * 1e-3                                 # mm of eccentricity per bearing
                ecc_w, ecc_r = I["sum"] * ecc_b * amp_b, I["rss"] * ecc_b * amp_c
                closing_w = sum(det.values()) + ecc_w
                rnd = math.sqrt(det["tip_profile"] ** 2 + det["bridge_profile"] ** 2 + ecc_r ** 2)
                closing_s = (det["centrifugal"] + det["magnetic_on_retention"] + th["closing_nominal_mm"] + det["belt_100N"]
                             + det["unbalance_G2p5"] + rnd)
                res[oname] = dict(TIR_per_bearing_um=TIR, ecc_worst_mm=ecc_w, ecc_rss_mm=ecc_r, ecc_over_gap_worst=ecc_w / g0,
                                  ecc_over_gap_rss=ecc_r / g0, g_min_worst_mm=g0 - closing_w, g_min_rss_mm=g0 - closing_s)
            det_sum = sum(det.values())
            allowed = dict(no_rub_0p25_worst=2e3 * (g0 - 0.25 - det_sum) / (I["sum"] * amp_b),
                           ecc_10pc_worst=2e3 * 0.10 * g0 / (I["sum"] * amp_b),
                           ecc_10pc_rss=2e3 * 0.10 * g0 / (I["rss"] * amp_c))
            rows[tag] = dict(deterministic_mm=det, options=res, allowed_TIR_um=allowed, dynamic_factor=dyn)
        out[vn] = dict(influence=infl, worst_side=side, amplification=dict(clamp=amp_c, bound=amp_b), k_rel_N_per_m=k_rel,
                       f1_Hz=f1, rows=rows)
    return dict(variants=out, seats=SEATS, iso492_um=ISO492, clearance_um=CLEARANCE, thermal=th, centrifugal_growth=cg,
                criteria=dict(no_rub="g_min >= 0.25 mm (half the gap) at 750 rpm, hot, worst-case stack-up [IR]",
                              eccentricity="eccentricity at the gap <= 10 % of g [RH: a common rule for machine air gaps]"))


# ---------------------------------------------------------------------------------------------------------------
# 6. windage and bearing friction
# ---------------------------------------------------------------------------------------------------------------
def daily_nece(Re, G):
    """moment coefficient (both faces) c_M = 2 torque / (rho Omega^2 a^5) of an enclosed rotor-stator disc, the four
    regimes of Daily & Nece (1960); the envelope (largest) is used [IR]."""
    c = dict(I=2 * math.pi / (G * Re), II=3.70 * G ** 0.1 / Re ** 0.5, III=0.080 / (G ** (1 / 6) * Re ** 0.25),
             IV=0.102 * G ** 0.1 / Re ** 0.2)
    k = max(c, key=c.get)
    return c[k], k, c


def disc_gap_W(a, r_in, s, Om, cr=1.0):
    """power dissipated in one rotor-stator gap of axial clearance s between discs of outer radius a (inner r_in), at
    the relative speed Om; cr scales for counter-rotation (each face against a non-rotating core) [IR]."""
    nu, rho = AIR["nu"], AIR["rho"]
    Re = Om * a * a / nu
    cm_, reg, _ = daily_nece(Re, s / a)
    expo = 4.0 if reg == "I" else 4.6
    torque = cm_ * rho * Om * Om * a ** 5 / 4 * (1 - (r_in / a) ** expo)
    return cr * torque * Om, dict(Re=Re, G=s / a, c_M=cm_, regime=reg)


def tc_cf(Re, dr):
    """Bilgen & Boulos (1973) as in Saari (1998): torque = c_f pi rho Om^2 r^4 L [IR]."""
    if Re < 64:
        return 5.0 * dr ** 0.3 / Re
    if Re < 500:
        return 1.0 * dr ** 0.3 / Re ** 0.6
    if Re < 1e4:
        return 0.515 * dr ** 0.3 / Re ** 0.5
    return 0.0325 * dr ** 0.3 / Re ** 0.2


def tc_W(r, delta, L, Om, k=1.0, cr=1.0):
    Re = Om * r * delta / AIR["nu"]
    cf_ = tc_cf(Re, delta / r)
    return cr * k * cf_ * math.pi * AIR["rho"] * Om ** 3 * r ** 4 * L, dict(Re=Re, c_f=cf_)


def tr_cf(Re):
    """Theodorsen & Regier (1944), a cylinder in still air: 1/sqrt(cf) = -0.6 + 4.07 log10(Re sqrt(cf)) [IR]."""
    return optimize.brentq(lambda c: 1 / math.sqrt(c) + 0.6 - 4.07 * math.log10(Re * math.sqrt(c)), 1e-4, 0.1)


def free_cyl_W(r, L, w):
    Re = w * r * r / AIR["nu"]
    cf = tr_cf(Re)
    return cf * math.pi * AIR["rho"] * w ** 3 * r ** 4 * L, dict(Re=Re, c_f=cf)


def edge_W(t, r1, r2, w, cd, n_sec):
    """form drag of n vane sectors' leading + trailing edges (full round, thickness t), each moving at w r through
    air with no mean rotation [RH]."""
    return n_sec * cd * 0.5 * AIR["rho"] * t * w ** 3 * (r2 ** 4 - r1 ** 4) / 4


def paddle_W(w, cd, cf, r1=0.057, r2=0.130, h=0.156, Rr=0.1315, Lr=0.162, n_u=3):
    """the reluctance section as a paddle wheel: three utrons drive the section's air (core rotation K w) against the
    counter-rotating bridge-ring bore and spider and the frame's end wall; torque balance for K, then the power [RH]."""
    rho, nu = AIR["rho"], AIR["nu"]
    Ip = n_u * 0.5 * rho * cd * h * (r2 ** 4 - r1 ** 4) / 4
    Re_d = 2 * w * Rr * Rr / nu
    cm1 = 0.073 / Re_d ** 0.2                                            # one face, turbulent [IR]
    ring = lambda K: cf * 0.5 * rho * ((1 + K) * w * Rr) ** 2 * 2 * math.pi * Rr * Lr * Rr
    sp_ = lambda K: cm1 * 0.5 * rho * ((1 + K) * w) ** 2 * Rr ** 5
    ew = lambda K: cm1 * 0.5 * rho * (K * w) ** 2 * Rr ** 5
    tq_p = lambda K: Ip * ((1 - K) * w) ** 2
    K = optimize.brentq(lambda K: tq_p(K) - ring(K) - sp_(K) - ew(K), 0.0, 1.0)
    return (tq_p(K) + ring(K) + sp_(K)) * w, dict(K=K)


BRG_6205 = dict(c_dyn=14.8e3, c_stat=7.8e3, f0=14.0, dm=38.5, Z=9, Dw=7.938)   # deep-groove 25 / 52 / 15, datasheet-class [IR]


def palmgren_W(n_rpm, f0, nu_cst, Fa=100.0, Fr=0.0, b=BRG_6205):
    """Palmgren: M0 = 1e-7 f0 (nu n)^(2/3) dm^3 (N mm, nu n >= 2000); M1 = f1 p1 dm with f1 = 0.0007 (p0 / c_stat)^0.5,
    p1 = max(Fr, 3 Fa - 0.1 Fr) for a deep-groove bearing, p0 = max(Fr, 0.6 Fr + 0.5 Fa) [IR]."""
    dm = b["dm"]
    vn = nu_cst * n_rpm
    M0 = 1e-7 * f0 * vn ** (2 / 3) * dm ** 3 if vn >= 2000 else 160e-7 * f0 * dm ** 3
    p1 = max(Fr, 3 * Fa - 0.1 * Fr)
    p0 = max(Fr, 0.6 * Fr + 0.5 * Fa)
    M1 = 0.0007 * (p0 / b["c_stat"]) ** 0.5 * p1 * dm
    return (M0 + M1) * 1e-3 * 2 * math.pi * n_rpm / 60.0, M0 + M1


def bearing_life(Fa, Fr, n_rpm, b=BRG_6205):
    """basic rating life L10h of a deep-groove bearing (ISO 281 form, X / Y from the f0 Fa / c_stat table) [IR]."""
    tab = [(0.172, 0.19, 2.30), (0.345, 0.22, 1.99), (0.689, 0.26, 1.71), (1.03, 0.28, 1.55), (1.38, 0.30, 1.45),
           (2.07, 0.34, 1.31), (3.45, 0.38, 1.15), (5.17, 0.42, 1.04), (6.89, 0.44, 1.00)]
    x = b["f0"] * Fa / b["c_stat"]
    xs, es, ys = zip(*tab)
    lim, Y = float(np.interp(x, xs, es)), float(np.interp(x, xs, ys))
    p_eq = Fr if (Fr > 0 and Fa / Fr <= lim) else 0.56 * Fr + Y * Fa
    return dict(load_eq_N=p_eq, L10h=(b["c_dyn"] / p_eq) ** 3 * 1e6 / (60 * n_rpm), ratio_limit=lim, Y=Y)


def windage(inp, M, z):
    w = 2 * math.pi * RPM / 60.0
    Om = 2 * w
    sp = inp["sp"]
    cov_r = ((50.0 / 150) ** 4.6 - (S.SLEEVE_R / 150) ** 4.6) + (6 * 22 / 360) * (1 - (50.0 / 150) ** 4.6)
    cov_s = (6 * 22 / 360) * (1 - (50.0 / 150) ** 4.6)
    cov = 0.5 * (cov_r + cov_s)
    n_gap = 2 * 11
    n_sec = 2 * 12 * 6
    P_gap, info_gap = disc_gap_W(0.150, S.SLEEVE_R * 1e-3, 0.006, Om)
    P_caf, info_caf = disc_gap_W(0.150, 0.050, 0.012, Om)
    P_rim, info_rim = tc_W(0.150, 0.012, (z["ca_A"][1] - z["ca_A"][0]) * 1e-3, Om)
    gap_eff = 0.42 * (sp["r_br0"] - sp["r_g"]) + 0.58 * (sp["r_ring0"] - sp["r_g"])      # bridges cover 42 % of the bore
    P_rel, info_rel = tc_W(sp["r_g"] * 1e-3, gap_eff * 1e-3, (sp["L"] + 2 * sp["over"]) * 1e-3, Om)
    P_pad_nom, info_pad = paddle_W(w, 2.0, 0.005)
    P_pad_lo, _ = paddle_W(w, 1.0, 0.004)
    P_pad_hi, _ = paddle_W(w, 3.0, 0.008)
    L_cage = (z["cage"][1] - z["cage"][0]) * 1e-3
    P_cage, info_cage = free_cyl_W(0.166, L_cage, w)
    P_rings, info_rings = free_cyl_W(sp["r_ring1"] * 1e-3, 2 * (z["ring_A"][1] - z["ring_A"][0]) * 1e-3, w)
    P_ringend, _ = disc_gap_W(sp["r_ring1"] * 1e-3, sp["r_ring0"] * 1e-3, 0.006, w)
    P_hub, info_hub = free_cyl_W(0.033, (z["hub"][1] - z["hub"][0]) * 1e-3, Om)
    P_disc_in, _ = disc_gap_W(sp["r_disc"] * 1e-3, S.SLEEVE_R * 1e-3, 0.021, Om)
    P_disc_out, _ = disc_gap_W(sp["r_disc"] * 1e-3, S.SLEEVE_R * 1e-3, 0.015, w)
    crf = 0.72                                                           # (0.5 / 0.6)^1.8, counter- vs rotor-stator [RH]
    comp = {}
    comp["vane stacks: face friction (22 gaps)"] = dict(
        nominal=n_gap * P_gap * crf * cov, low=n_gap * P_gap * crf * cov, high=n_gap * P_gap,
        how=f"Daily & Nece regime {info_gap['regime']} at the relative speed (Re {info_gap['Re']:.3g}, G {info_gap['G']:.3f}, "
            f"c_M {info_gap['c_M']:.4f}); x {crf} counter-rotation and x {cov:.3f} metal coverage (nominal / low), "
            f"full discs (high)")
    comp["vane stacks: sector edges (144 sectors)"] = dict(
        nominal=edge_W(0.003, 0.05, 0.15, w, 0.4, n_sec), low=edge_W(0.003, 0.05, 0.15, w, 0.1, n_sec),
        high=edge_W(0.003, 0.05, 0.15, w, 0.8, n_sec),
        how="c_D 0.4 on the 3 mm full-round edge pair at w r against air with no mean rotation; 0.1 (the windows' air "
            "half entrained) to 0.8")
    comp["Ca / Cb stacks: outer plate vs the Ca|rel spider (2)"] = dict(
        nominal=2 * P_caf * crf, low=2 * P_caf * crf, high=2 * P_caf,
        how=f"Daily & Nece regime {info_caf['regime']}, s 12 mm, r 50-150, relative speed")
    comp["Ca / Cb stacks: rims vs the cage (2)"] = dict(
        nominal=2 * P_rim * crf * 1.5, low=2 * P_rim * crf, high=2 * P_rim * 2.5,
        how=f"Taylor-Couette r 150, gap 12 mm, 48 mm long (Re {info_rim['Re']:.3g}); grooves k 1.5 (1-2.5)")
    comp["reluctance sections: salient utrons in the bridge ring (2)"] = dict(
        nominal=2 * P_pad_nom, low=2 * min(P_pad_lo, P_rel), high=2 * max(P_pad_hi, 2.5 * P_rel),
        how=f"paddle model (c_D 2, ring c_f 0.005: core rotation K {info_pad['K']:.2f}); cross-check Taylor-Couette r 130, "
            f"gap {gap_eff:.2f} mm, L {sp['L'] + 2 * sp['over']:.0f} mm: {2 * P_rel:.2f} W smooth (k 1-2.5)")
    comp["counter-rotor outside in still air: cage and bridge rings"] = dict(
        nominal=P_cage + P_rings, low=0.7 * (P_cage + P_rings), high=1.3 * (P_cage + P_rings),
        how=f"Theodorsen & Regier, cage r 166 x {L_cage * 1e3:.0f} mm (Re {info_cage['Re']:.3g}, c_f {info_cage['c_f']:.4f}) "
            f"+ bridge rings r 156.5 x 2 x 174 mm; +-30 %")
    comp["bridge-ring ends vs the frame's end spiders (2)"] = dict(
        nominal=2 * P_ringend * crf, low=2 * P_ringend * crf, high=2 * P_ringend, how="Daily & Nece, annulus r 131.5-156.5, s 6 mm")
    comp["hub coupler in the counter-rotor's cavity"] = dict(
        nominal=P_hub, low=P_hub, high=2 * P_hub, how="cylinder r 33 x 144 mm at the relative speed")
    comp["carrier discs vs the end walls (4)"] = dict(
        nominal=2 * (P_disc_in + P_disc_out), low=2 * (P_disc_in + P_disc_out) * crf, high=4 * (P_disc_in + P_disc_out),
        how="Daily & Nece, r 20.5-57")
    tot = {k: sum(c[k] for c in comp.values()) for k in ("nominal", "low", "high")}
    # bearing friction (not windage; also paid by the belt): four inner at 1200 rpm relative, two frame at 600; the axis is
    # vertical, so the bottom frame bearing locates both bodies (their weight) and one inner bearing on side A locates
    # the counter-rotor (its weight); the others float on an axial spring preload of 100 N [IR]
    W_all, W_cr = (M["m_rotor"] + M["m_counter"]) * G0, M["m_counter"] * G0
    pre = 100.0
    duty = [("frame A (locating: both bodies)", RPM, W_all), ("frame B (floating)", RPM, pre),
            ("Ca|rel A (locating: the counter-rotor)", 2 * RPM, W_cr), ("hub face A", 2 * RPM, pre),
            ("hub face B", 2 * RPM, pre), ("Ca|rel B", 2 * RPM, pre)]
    br = {}
    for k, (f0, nu_) in dict(nominal=(1.0, 30.0), low=(0.75, 15.0), high=(2.0, 70.0)).items():
        each = {nm: palmgren_W(n_rpm, f0, nu_, Fa=fa, Fr=20.0) for nm, n_rpm, fa in duty}
        br[k] = dict(W=sum(p for p, _ in each.values()), each_W={nm: p for nm, (p, _) in each.items()},
                     each_Nmm={nm: mm_ for nm, (_, mm_) in each.items()}, f0=f0, nu_cSt=nu_)
    life = {nm: dict(Fa_N=fa, rpm=n_rpm, **bearing_life(fa, 20.0, n_rpm)) for nm, n_rpm, fa in duty}
    belt = inp["belt"]
    return dict(components={k: dict(v) for k, v in comp.items()}, total_W=tot, bearings=br, bearing_life=life, belt_W=belt,
                ratio_to_belt=dict((k, tot[k] / belt["total_W"]) for k in tot),
                mechanical_total_W={k: tot[k] + br[k]["W"] for k in tot}, coverage=cov, counter_rotation_factor=crf,
                air=AIR, speed=dict(rpm_each=RPM, omega=w, omega_rel=Om))


# ---------------------------------------------------------------------------------------------------------------
# 7. balancing
# ---------------------------------------------------------------------------------------------------------------
def inertia(M, inp, wd):
    """polar inertia of the main parts (mean-square radius of each annulus or sector) and the stored energy; the
    coast-down rate with the drive cut, from the nominal mechanical loss [OC: I = sum m r^2; IR: the parts counted]."""
    sp, vane = inp["sp"], M["vane"]
    ms = lambda a, b: 0.5 * (a * a + b * b) * 1e-6                        # mean r^2 of an annulus (m^2)
    m_ring_sv = vane["m_stator_vane_kg"] - 6 * vane["m_sector_kg"]
    m_ring_rv = vane["m_rotor_vane_kg"] - 6 * vane["m_sector_kg"]
    rotor = {"utrons (6)": 6 * M["utron"]["m_kg"] * ((M["utron"]["r_cm_mm"] * 1e-3) ** 2 + 0.02 ** 2),
             "rotor vanes (12)": 12 * (6 * vane["m_sector_kg"] * ms(50, 150) + m_ring_rv * ms(S.SLEEVE_R, 50)),
             "Ca / Cb plates (12)": 12 * vane["m_ca_plate_kg"] * ms(50, 150),
             "carrier discs (4)": 4 * M["disc_kg"] * ms(S.SLEEVE_R, sp["r_disc"])}
    counter = {"bridges (12)": 12 * M["bridge"]["m_kg"] * ((M["bridge"]["r_cm_mm"] * 1e-3) ** 2),
               "bridge rings (2)": 2 * M["bridge"]["ring_m_kg"] * ms(sp["r_ring0"], sp["r_ring1"]),
               "cage": M["cage_kg"] * 0.164 ** 2,
               "stator vanes (12)": 12 * (6 * vane["m_sector_kg"] * ms(50, 150) + m_ring_sv * ms(150, 162)),
               "spiders (4)": 4 * M["spider_kg"] * ms(26, 162)}
    I_r, I_c = sum(rotor.values()), sum(counter.values())
    out = dict(rotor_kgm2=I_r, counter_kgm2=I_c, rotor_parts=rotor, counter_parts=counter)
    for tag, rpm in SPEEDS.items():
        w = 2 * math.pi * rpm / 60.0
        out[f"E_{tag.split()[0]}_J"] = dict(rotor=0.5 * I_r * w * w, counter=0.5 * I_c * w * w)
    w = 2 * math.pi * RPM / 60.0
    p_mech = wd["mechanical_total_W"]["nominal"]
    out["coast_down_rpm_per_s_at_600"] = p_mech / ((I_r + I_c) * w) * 60 / (2 * math.pi)
    return out


def balancing(M, inp):
    w = 2 * math.pi * RPM / 60.0
    out = {}
    for body, m in (("rotor", M["m_rotor"]), ("counter-rotor", M["m_counter"])):
        grades = {}
        for G in (6.3, 2.5, 1.0):
            off = G / w                                                  # mm (G in mm/s): the mass centre's offset
            U_ = off * m * 1e3                                           # g mm
            grades[f"G{G:g}"] = dict(offset_per_um=off * 1e3, U_per_gmm=U_, U_per_plane_gmm=U_ / 2, F_600_N=U_ * 1e-6 * w * w)
        out[body] = dict(m_kg=m, grades=grades)
    sp = inp["sp"]
    u = out["rotor"]["grades"]["G2.5"]["U_per_plane_gmm"]
    c = out["counter-rotor"]["grades"]["G2.5"]["U_per_plane_gmm"]
    out["matching_G2p5"] = dict(
        utron_dm_g=u / M["utron"]["r_cm_mm"], utron_dm_pc=100 * u / M["utron"]["r_cm_mm"] / (M["utron"]["m_kg"] * 1e3),
        utron_dr_mm=u / (M["utron"]["m_kg"] * 1e3), bridge_dm_g=c / M["bridge"]["r_cm_mm"],
        bridge_dm_pc=100 * c / M["bridge"]["r_cm_mm"] / (M["bridge"]["m_kg"] * 1e3),
        correction_rotor_g_at_r50=u / 50.0, correction_counter_g_at_r150=c / 150.0)
    out["note"] = "ISO 21940-11: the permissible mass-centre offset = G / omega, U_per = that offset x m, split equally " \
                  "between two correction planes of a symmetric body [OC: the standard's definitions; IR: the grade]"
    return out


# ---------------------------------------------------------------------------------------------------------------
def main():
    inp = inputs()
    sp = inp["sp"]
    hub = inp["hub"]
    fl = hub["shaft"]["value"]["flange_absz_mm"]
    hub_mm = 2 * fl[0]                                                    # flanges outboard of |z| 72 (presets/hub-locked.json)
    z = layout(sp, hub_mm)
    M = masses(inp, z)
    M["_hub_dims"] = (hub["retainer"]["value"]["r_max_mm"] * 1e-3, hub["shaft_coupler"]["value"]["wall_mm"] * 1e-3)
    M["_ring_r"] = (sp["r_ring0"], sp["r_ring1"])
    M30 = masses(inp, z, shaft_dia=30.0)
    cent = centrifugal(inp, M)
    mag = magnetic(inp)
    fe = fe_study(z, M, mag)
    th = thermal(sp)
    cg = centrifugal_growth(inp, M, cent)
    gb = gap_budget(inp, M, cent, mag, fe, th, cg)
    wd = windage(inp, M, z)
    bal = balancing(M, inp)
    ine = inertia(M, inp, wd)
    res = dict(
        schema="rotor-mechanics/1", pick=PICK, sources=inp["sources"], speeds_rpm=SPEEDS,
        layout_mm={k: v for k, v in z.items()},
        masses=dict(rotor_kg=M["m_rotor"], counter_rotor_kg=M["m_counter"], rotor_kg_dia30=M30["m_rotor"],
                    rotor=[dict(item=it, kg=kg, z_mm=zz, r_cm_mm=rc, source=src) for it, kg, zz, rc, src in M["rotor"]],
                    counter_rotor=[dict(item=it, kg=kg, z_mm=zz, r_cm_mm=rc, source=src) for it, kg, zz, rc, src in M["counter"]],
                    utron=dict(parts=[dict(part=a, kg=b, u_mm=c) for a, b, c in M["utron"]["parts"]], m_kg=M["utron"]["m_kg"],
                               record_m_kg=M["utron"]["record_m_kg"], r_cm_mm=M["utron"]["r_cm_mm"],
                               half_core=M["utron"]["half_core"]),
                    bridge=M["bridge"], vane=M["vane"], hub=M["hub"], cage_kg=M["cage_kg"], spider_kg=M["spider_kg"]),
        centrifugal=cent, magnetic=mag, fe=fe, gap=gb, windage=wd, balancing=bal, inertia=ine, materials=MAT)
    with open(os.path.join(HERE, "rotor_mechanics_results.json"), "w") as f:
        json.dump(res, f, indent=1, default=float)
    # ---- summary ----
    print(f"layout {z['L_total']:.0f} mm; rotor {M['m_rotor']:.1f} kg (Ø25), counter-rotor {M['m_counter']:.1f} kg")
    print(f"utron {M['utron']['m_kg']:.4f} kg (record {M['utron']['record_m_kg']:.4f}), r_cm {M['utron']['r_cm_mm']:.1f} mm; "
          f"bridge {M['bridge']['m_kg']:.4f} kg at {M['bridge']['r_cm_mm']:.1f} mm; bridge ring {M['bridge']['ring_m_kg']:.2f} kg")
    for tag, r in cent["rows"].items():
        print(f"{tag}: utron {r['F_utron_N']:.0f} N ({r['g_at_r130']:.1f} g at r 130); stack bend {r['stack_bend_MPa']:.2f} MPa, "
              f"studs-as-beams {r['studs_as_beams']['bend_MPa']:.0f} MPa / {r['studs_as_beams']['deflection_mm']:.2f} mm; "
              f"bridge {r['bridge']['F_N']:.0f} N, ring {r['bridge']['ring_total_MPa']:.2f} MPa")
    for s in cent["sf_750"]:
        print(f"   SF at 750 rpm {s['sf']:8.1f}  {s['item']}")
    print(f"magnetic: B {mag['B_gap_T']:.3f} T, {mag['F_utron_N']:.1f} N per utron (peak {mag['F_utron_peak_N']:.1f}); "
          f"k {mag['k_clamp_max_N_per_m']:.3g} (clamp law) / {mag['k_lin_N_per_m']:.3g} (bound) N/m per side")
    for name, row in fe["cases"].items():
        fs = ", ".join("%.0f" % m_["f_Hz"] for m_ in row["modes"][:4])
        print(f"FE {name}: f {fs} Hz; k_rel {row['k_rel_A_N_per_m']:.3g}; "
              f"1 g gap A {max(map(abs, row['gravity_1g']['gap_A_um'])):.1f} um; amp {row['mag_bound']['amplification']:.3f}")
    for vn, gv in gb["variants"].items():
        I = gv["influence"][gv["worst_side"]]
        print(f"== gap, {vn}: f1 {gv['f1_Hz']:.0f} Hz, k_rel {gv['k_rel_N_per_m']:.3g}; influence (side {gv['worst_side']}) "
              f"sum {I['sum']:.2f} rss {I['rss']:.2f}: " + ", ".join(f"{k} {a:.2f}" for k, a in {**I['inner'], **I['frame']}.items()))
        for tag, r in gv["rows"].items():
            print(f"  {tag}: det " + ", ".join(f"{k} {1e3 * x:.1f}" for k, x in r["deterministic_mm"].items())
                  + " um; allowed TIR " + ", ".join(f"{k} {x:.0f}" for k, x in r["allowed_TIR_um"].items()) + " um")
            for o, v in r["options"].items():
                print(f"     {o:30s} TIR {v['TIR_per_bearing_um']:.0f} um  ecc {v['ecc_worst_mm'] * 1e3:.0f} / "
                      f"{v['ecc_rss_mm'] * 1e3:.0f} um  g_min worst {v['g_min_worst_mm']:.3f} / rss {v['g_min_rss_mm']:.3f} mm")
    for k, v in wd["components"].items():
        print(f"windage {k:60s} {v['nominal']:6.2f} W ({v['low']:.2f}-{v['high']:.2f})")
    print(f"windage total {wd['total_W']}; bearings {[(k, round(v['W'], 2)) for k, v in wd['bearings'].items()]}; belt {wd['belt_W']}")
    for b in ("rotor", "counter-rotor"):
        print(f"balance {b} {bal[b]['m_kg']:.1f} kg: " + ", ".join(f"{k} {v['U_per_gmm']:.0f} g mm ({v['offset_per_um']:.0f} um)"
                                                                 for k, v in bal[b]["grades"].items()))
    print(bal["matching_G2p5"])
    print(f"inertia rotor {ine['rotor_kgm2']:.3f} / counter {ine['counter_kgm2']:.3f} kg m2; E600 {ine['E_600_J']}; "
          f"coast-down {ine['coast_down_rpm_per_s_at_600']:.2f} rpm/s")
    for nm, v in wd["bearing_life"].items():
        print(f"bearing {nm:40s} Fa {v['Fa_N']:.0f} N, {v['rpm']:.0f} rpm: load {v['load_eq_N']:.0f} N, L10h {v['L10h']:.3g} h; "
              f"friction {wd['bearings']['nominal']['each_W'][nm]:.2f} W")


if __name__ == "__main__":
    main()
