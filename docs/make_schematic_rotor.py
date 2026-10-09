"""docs/make_schematic_rotor.py -- writes docs/schematic-rotor-circuits.{svg,png}: the machine's two circuits as built
(the tube with wound utrons, sim/tube_geometry.py --rel wound), with the body each part rides on.
(a) RELUCTANCE: the magnetic dual doubler (sim/magnetic_doubler.py netlist) -- the A / B groups of 3 wound utrons each,
    the AH coil of its branch in series, La / Lb, the wiring strays Lp2 / Lp3, D1*-D4*; everything on the rotor. The
    counter-rotor's passive bridges make L(theta); no wire crosses between the bodies.
(b) ELECTROSTATIC: the de Queiroz diode doubler with its HV side on the rotor (sim/core_field.py netlist; the air
    build's capped stack) -- C1 / C2 between the rotor vanes (nodes 1 / 4) and the counter-rotor's stator vanes, which
    are the reference; Ca / Cb, D1-D4 and the clamps Z1 / Z4 on the rotor; two rings outside the hub's glass vessel
    (the designer's choice; presets/hub-locked.json), each on its own two-stage Cockcroft-Walton chain from the shaft,
    ring A on node 1 and ring B on node 4 (the symmetric supply of record), so the AH null sees a steady field
    (sim/hub-rings-build-findings.md; the drawing also handles the earlier Dk supply);
    the stator vanes joined to the shaft through one inner bearing for now (a brush later).
(a) also draws the 22 mF bypass across each AH coil (PROPOSED; sim/ah-steady-cusp-findings.md), dashed.
Values: sim/pole_design_variants_op.json (the pick), sim/utron_profile.py, sim/rotor_parts_duty_results.json (La / Lb,
D1*-D4* at the pick), sim/core_field_results.json (the electrostatic pump), sim/hub_rings_build_results.json (the rings
as built and their supply in full: the clamps, the link), sim/hub_drift_results.json (the settled field),
sim/ah_steady_cusp_results.json (the bypass).
Usage: python3 docs/make_schematic_rotor.py   (the PNG needs playwright + chromium)
"""
import json
import math
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(ROOT, "sim"))
import magnetic_doubler as MDm     # noqa: E402  (the dual's constants: AH rewinds, strays, snubbers)
import utron_profile as U          # noqa: E402

PICK = "g 0.5 / 6 bridges / 1200 rpm"
LA_RATIO, TAU_FIXED, AH_KEY = 0.6, 0.5, "r160"     # as sim/pole_design.size_op runs the pick
OUT = os.path.join(HERE, "schematic-rotor-circuits")
o = []


# ------------------------------------------------------------------------------------------------ primitives (SVG px)
def ln(x1, y1, x2, y2, cl="w"):
    o.append(f'<line x1="{x1:.1f}" y1="{y1:.1f}" x2="{x2:.1f}" y2="{y2:.1f}" class="{cl}"/>')


def pl(pts, cl="w"):
    o.append('<polyline points="' + " ".join(f"{x:.1f},{y:.1f}" for x, y in pts) + f'" class="{cl}"/>')


def tx(x, y, s, cl="t", anchor="start", extra=""):
    o.append(f'<text x="{x:.1f}" y="{y:.1f}" class="{cl}" text-anchor="{anchor}" {extra}>{s}</text>')


def dot(x, y, r=3.6):
    o.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="{r}" class="dot"/>')


def coil_h(x, y, n=3, cl="w"):
    """n bumps upward from (x, y) to the right; returns the end x."""
    o.append(f'<path d="M{x:.1f} {y:.1f}' + "".join(" q6 -10 12 0" for _ in range(n)) + f'" class="{cl}"/>')
    return x + 12 * n


def coil_v(x, y, n=5, cl="w"):
    """n bumps to the right from (x, y) downward; returns the end y."""
    o.append(f'<path d="M{x:.1f} {y:.1f}' + "".join(" q10 6 0 12" for _ in range(n)) + f'" class="{cl}"/>')
    return y + 12 * n


def var_arrow(cx, cy, w=38, h=34, col="#111"):
    """the variable-element arrow, lower left to upper right through (cx, cy)."""
    x0, y0, x1, y1 = cx - w / 2, cy + h / 2, cx + w / 2, cy - h / 2
    ln(x0, y0, x1, y1, "va")
    a = math.atan2(y1 - y0, x1 - x0)
    p = [(x1, y1), (x1 - 9 * math.cos(a - 0.38), y1 - 9 * math.sin(a - 0.38)),
         (x1 - 9 * math.cos(a + 0.38), y1 - 9 * math.sin(a + 0.38))]
    o.append('<polygon points="' + " ".join(f"{px:.1f},{py:.1f}" for px, py in p) + f'" fill="{col}"/>')


def diode(x, y, d, col="#111", zener=False):
    """a diode whose triangle starts at (x, y) and points along d ('up' 'down' 'left' 'right'); 18 px long."""
    v = dict(down=(0, 1), up=(0, -1), right=(1, 0), left=(-1, 0))[d]
    n = (-v[1], v[0])
    tip = (x + 18 * v[0], y + 18 * v[1])
    tri = [(x + 11 * n[0], y + 11 * n[1]), (x - 11 * n[0], y - 11 * n[1]), tip]
    o.append('<polygon points="' + " ".join(f"{px:.1f},{py:.1f}" for px, py in tri) +
             f'" fill="none" stroke="{col}" stroke-width="2"/>')
    b0 = (tip[0] + 11 * n[0], tip[1] + 11 * n[1]); b1 = (tip[0] - 11 * n[0], tip[1] - 11 * n[1])
    if zener:                                                  # the bent ends of an avalanche (Z) diode
        pl([(b0[0] - 5 * v[0] + 0 * n[0], b0[1] - 5 * v[1]), b0, b1, (b1[0] + 5 * v[0], b1[1] + 5 * v[1])], "zl")
    else:
        o.append(f'<line x1="{b0[0]:.1f}" y1="{b0[1]:.1f}" x2="{b1[0]:.1f}" y2="{b1[1]:.1f}" stroke="{col}" stroke-width="2"/>')
    return tip


def cap_h(x, y, h=14):
    """capacitor in a horizontal wire: plates at x and x + 10."""
    ln(x, y - h, x, y + h, "pl"); ln(x + 10, y - h, x + 10, y + h, "pl")


def cap_v(x, y, w=19):
    """capacitor in a vertical wire: plates at y and y + 10."""
    ln(x - w, y, x + w, y, "pl"); ln(x - w, y + 10, x + w, y + 10, "pl")


def res_v(x, y, h=32, cl="w"):
    k = 6
    pts = [(x, y)] + [(x + (7 if i % 2 == 0 else -7), y + h * (i + 0.5) / k) for i in range(k)] + [(x, y + h)]
    pl(pts, cl)


def ground(x, y):
    ln(x - 12, y, x + 12, y); ln(x - 7, y + 5, x + 7, y + 5); ln(x - 3, y + 10, x + 3, y + 10)


def box(x, y, w, h, cl):
    o.append(f'<rect x="{x:.1f}" y="{y:.1f}" width="{w:.1f}" height="{h:.1f}" class="{cl}"/>')


def kv(v, f="{:.1f}"):
    """a voltage with a real minus sign."""
    return f.format(v).replace("-", "−")


def table(x, y, rows, w_key=92, dy=19.5):
    for i, (k, v) in enumerate(rows):
        tx(x, y + i * dy, k, "tk")
        tx(x + w_key, y + i * dy, v, "tv")
    return y + len(rows) * dy


# ------------------------------------------------------------------------------------------------ the numbers
def numbers():
    op = json.load(open(os.path.join(ROOT, "sim", "pole_design_variants_op.json")))["designs"][PICK]
    b = op["best"]
    rows = json.load(open(os.path.join(ROOT, "sim", "pole_design_variants.json")))["rows"]
    sp = U.spec(op["design"], b, [r for r in rows if r["design"] == op["design"]][0])
    Lg = b["L_group_H"]
    ah = MDm.AH[AH_KEY]
    F = b["f_utron_Hz"]
    csn = MDm.CSNUB * (MDm.L_MAX / Lg) * (60.0 / F) ** 2          # magnetic_doubler.deck(snub="scaled")
    rsn = MDm.RSNUB * (Lg / MDm.L_MAX) * (F / 60.0)
    duty = json.load(open(os.path.join(ROOT, "sim", "rotor_parts_duty_results.json")))
    cf = json.load(open(os.path.join(ROOT, "sim", "core_field_results.json")))
    cfr = {r["name"]: r for r in cf["rows"]}
    hb = json.load(open(os.path.join(ROOT, "sim", "hub_rings_build_results.json")))       # the rings as built
    dr = json.load(open(os.path.join(ROOT, "sim", "hub_drift_results.json")))
    ring = dict(hb["record"], E_dc_kV_cm=hb["record"]["E_null_kV_cm"], p_dc_Pa=hb["record"]["p_null_Pa"],
                E_settled_kV_cm=dr["drift"][0]["E_kV_cm"][-1])                            # PEEK, gel, 25 C at 6 h
    cusp = [r for r in json.load(open(os.path.join(ROOT, "sim", "ah_steady_cusp_results.json")))["rows"]
            if r["C_byp_mF"] == 22.0][0]                                           # the bypass (PROPOSED)
    return dict(op=op, b=b, sp=sp, Lg=Lg, ah=ah, F=F, csn=csn, rsn=rsn, la=LA_RATIO * Lg, lp=MDm.R_PAR * Lg, duty=duty, cusp=cusp,
                cf=cf, cfr=cfr, hb=hb, dc=hb["record_supply"], dc_free=hb["record_supply_free"], ring=ring)


# ------------------------------------------------------------------------------------------------ (a) reluctance
def panel_a(ox, N):
    b, sp, ah = N["b"], N["sp"], N["ah"]
    REF = 690
    xa, xd, xc, xb = ox + 70, ox + 340, ox + 460, ox + 690
    yt = 300
    # the counter-rotor's bridges: passive iron, magnetically coupled, no wires
    box(ox + 30, 110, 700, 64, "zone_cr")
    tx(ox + 42, 128, "COUNTER-ROTOR", "zh")
    tx(ox + 42, 145, f"{sp['n_br']} SiFe bridges per side: passive iron, no wires", "m")
    tx(ox + 42, 162, f"B row {180 / sp['n_br']:g}° offset · radial gap {sp['g']:g} mm at r {sp['r_g']:g} mm", "m")
    for k in range(6):                                     # A row of bridges / B row shifted half a pitch
        o.append(f'<rect x="{ox + 412 + k * 50:.1f}" y="126" width="26" height="9" class="br"/>')
        o.append(f'<rect x="{ox + 437 + k * 50:.1f}" y="150" width="26" height="9" class="br"/>')
    tx(ox + 400, 134, "A", "m", "end"); tx(ox + 400, 158, "B", "m", "end")
    box(ox + 30, 186, 700, 560, "zone_r")
    tx(ox + 720, 736, "ROTOR · the whole circuit, no rotating contact", "zh", "end")
    # nodes on the ring
    for x, nm, dx in ((xa, "a", -16), (xd, "d", -4), (xc, "c", -4), (xb, "b", 8)):
        dot(x, yt); tx(x + dx, yt - 14, nm, "nd")
    # A branch a -> A1 A2 A3 -> x1 -> AH -> d ; B branch c -> B1 B2 B3 -> x2 -> AH -> b
    for x0, x1n, grp, col_lbl in ((xa, xd, "A", "tu"), (xc, xb, "B", "tu")):
        x = x0
        ln(x, yt, x + 14, yt); x += 14
        for k in range(3):
            xe = coil_h(x, yt, 3, "ut")
            var_arrow((x + xe) / 2, yt - 5)
            ln((x + xe) / 2, 176, (x + xe) / 2, yt - 26, "mag")         # the bridge's flux path closes on this utron
            tx((x + xe) / 2, yt + 22, f"{grp}{k + 1}", "tu", "middle")
            x = xe
            ln(x, yt, x + 14, yt); x += 14
        dot(x, yt, 2.8); tx(x, yt + 22, "x1" if grp == "A" else "x2", "ms", "middle")
        ln(x, yt, x + 14, yt); x += 14
        xe = coil_h(x, yt, 3, "ah")
        tx((x + xe) / 2, yt + 22, "AH", "ta", "middle", 'font-weight="bold"')
        ln(xe, yt, x1n, yt)
        # the 22 mF bypass across the coil (PROPOSED): dashed
        xm, yb = 0.5 * (x + xe), yt - 34
        pl([(x - 4, yt), (x - 4, yb), (xm - 5, yb)], "prop"); pl([(xm + 5, yb), (xe + 4, yb), (xe + 4, yt)], "prop")
        ln(xm - 5, yb - 9, xm - 5, yb + 9, "propc"); ln(xm + 5, yb - 9, xm + 5, yb + 9, "propc")
        tx(xm, yb - 14, f"{N['cusp']['C_byp_mF']:.0f} mF (PROPOSED)", "tp", "middle")
        tx(x0 + 14, yt + 46, f"{grp} group  L{1 if grp == 'A' else 2}(θ)", "tu", "start", 'font-weight="bold"')
        tx(x0 + 14, yt + 62, "3 utrons + AH coil" + ("" if grp == "A" else ", antiphase"), "ms")
    # La: ref -> a ; Lb: c -> ref
    y_lc = 470
    ln(xa, yt, xa, y_lc); ye = coil_v(xa, y_lc, 6); ln(xa, ye, xa, REF)
    tx(xa - 14, y_lc + 30, "La", "t", "end", 'font-weight="bold"')
    ln(xc, yt, xc, y_lc); ye = coil_v(xc, y_lc, 6); ln(xc, ye, xc, REF)
    tx(xc + 18, y_lc + 30, "Lb", "t", "start", 'font-weight="bold"')
    # D3*: ref -> d (anode ref) ; D4*: ref -> b
    for x, nm, sd in ((xd, "D3*", 1), (xb, "D4*", -1)):
        ln(x, yt, x, 480); diode(x, 498, "up"); ln(x, 498, x, REF); tx(x + 16 * sd, 494, nm, "t", "start" if sd > 0 else "end")
    # Lp3 + D2*: d -> Lp3 -> f3 <- D2* <- c
    y2 = 370
    dot(xd, y2); ln(xd, y2, xd + 10, y2); xe = coil_h(xd + 10, y2, 3, "st"); ln(xe, y2, xe + 10, y2)
    dot(xe + 10, y2, 2.8); tx(xe + 10, y2 + 20, "f3", "ms", "middle")
    ln(xe + 10, y2, xe + 18, y2); diode(xe + 36, y2, "left"); ln(xe + 36, y2, xc, y2); dot(xc, y2)
    tx(xd + 28, y2 - 16, "Lp3", "ms", "middle"); tx(xe + 27, y2 - 16, "D2*", "t", "middle")
    # Lp2 + D1*: a -> Lp2 -> f2 -> D1* -> b, routed under the ring
    y1 = 640
    dot(xa, 430); pl([(xa, 430), (xa + 30, 430), (xa + 30, y1), (xa + 44, y1)])
    xe = coil_h(xa + 44, y1, 3, "st"); ln(xe, y1, xe + 14, y1); dot(xe + 14, y1, 2.8)
    tx(xe + 14, y1 + 20, "f2", "ms", "middle"); tx(xa + 62, y1 - 16, "Lp2", "ms", "middle")
    ln(xe + 14, y1, xb - 70, y1); diode(xb - 70, y1, "right"); tx(xb - 61, y1 - 16, "D1*", "t", "middle")
    pl([(xb - 52, y1), (xb + 30, y1), (xb + 30, 400), (xb, 400)]); dot(xb, 400)
    # REF rail
    ln(xa - 30, REF, xb + 10, REF, "rail")
    for x in (xa, xd, xc, xb):
        dot(x, REF)
    tx(xa - 30, REF + 20, "REF = shaft (rotor), shared with (b)", "m")
    # start kick: not designed (no connection drawn)
    box(xa + 60, 514, 200, 80, "kick")
    tx(xa + 70, 534, "START KICK: source open", "tk2")
    tx(xa + 70, 551, f"once, ≥ {100 * b['kick_frac']:.0f} % of Ψs at start-up:", "ms")
    tx(xa + 70, 567, f"{b['kick_I_A']:.2f} A, {b['kick_mJ']:.1f} mJ seeded", "ms")
    tx(xa + 70, 583, "into the utron loop", "ms")
    # the node snubber, drawn once
    xs, ys = xc + 70, 528
    dot(xs, ys); tx(xs + 10, ys + 4, "any node", "ms")
    ln(xs, ys, xs, ys + 14); cap_v(xs, ys + 14, 12); ln(xs, ys + 24, xs, ys + 36); res_v(xs, ys + 36, 30)
    ln(xs, ys + 66, xs, ys + 74); ground(xs, ys + 74)
    tx(xs + 22, ys + 30, "RC to REF at each", "ms"); tx(xs + 22, ys + 45, "of the 8 nodes [IR]", "ms")
    tx(xs + 22, ys + 60, f"{N['csn'] * 1e9:.0f} nF + {N['rsn']:.0f} Ω", "ms")


def panel_a_table(ox, y, N):
    b, sp, ah = N["b"], N["sp"], N["ah"]
    la, ch = N["duty"]["la_lb"]["La"], N["duty"]["la_core"][0]
    rows = [
        ("A1–A3, B1–B3", f"wound utrons at 0 / 120 / 240°, {sp['N_u']} t of Ø{sp['wire_d_mm']:.2f} mm Cu: "
                         f"{1e3 * sp['L_al_coil_H']:.1f} / {1e3 * sp['L_un_coil_H']:.1f} mH (aligned / unaligned), "
                         f"{sp['R_coil_ohm']:.2f} Ω each"),
        ("group", f"L̂ {N['Lg']:.3f} H, ratio κ {N['op']['kappa']:.1f}, τ = L/R {N['op']['tau']:.3f} s; "
                  f"Ψs {b['psi_s']:.3f} Wb-t (the {sp['t_n']:.1f} mm NiFe neck)"),
        ("bridges", f"a passing bridge closes the utron's flux path: L(θ) {sp['n_br']} × per rev; B row half a pitch on"),
        ("AH", f"anti-Helmholtz pair at the hub, one coil per branch: {ah['N']} t, {ah['L'] * 1e3:.2f} mH, "
               f"{ah['R']:.2f} Ω each [RH]"),
        ("", f"bypass {N['cusp']['C_byp_mF']:.0f} mF across each coil, ESR {1e3 * 0.01:.0f} mΩ [RH] (PROPOSED)"),
        ("La, Lb", f"{N['la']:.3f} H DC chokes: {la['I_min_A']:.2f}–{la['I_max_A']:.2f} A, ≤ {la['V_pk_V']:.0f} V, "
                   f"{N['la'] / TAU_FIXED:.2f} Ω (τ {TAU_FIXED:g} s [RH]); not designed"),
        ("", f"first cut [RH]: gapped EI of M235-35A, {ch['a_mm']:.0f} mm leg, {ch['turns']} t, {ch['gap_mm']:.2f} mm gap, "
             f"{ch['m_core_kg']:.1f} kg Fe + {ch['m_cu_kg']:.1f} kg Cu each"),
        ("Lp2, Lp3", f"{N['lp'] * 1e3:.1f} mH wiring stray, as modelled (dual of Cpar) [IR]"),
        ("D1*–D4*", f"Si, 0.55 V at 1 A; {b['I_pk']:.1f} A peak; reverse "
                    + " / ".join(f"{v:.0f}" for v in N['duty']['la_lb']['diode_VR_pk_V'].values()) + " V peak"),
    ]
    y = table(ox + 42, y, rows)
    I_min = b["AT_min"] / ah["N"]
    cu = N["cusp"]
    tx(ox + 42, y + 6, f"At {b['rpm']:.0f} rpm relative ({N['F']:.0f} Hz): {I_min:.2f}–{b['I_pk']:.2f} A per branch, "
                       f"{b['V_pk']:.0f} V peak per group; AH {b['AT_min']:.0f}–{b['AT_pk']:.0f} A-turns unbypassed.", "op")
    y += 18
    tx(ox + 42, y + 6, f"With the bypass (PROPOSED): {cu['top']['AT_min']:.0f}–{cu['top']['AT_max']:.0f} A-turns per coil "
                       f"({cu['top']['AT_mean']:.0f} mean), top and bottom within {cu['dAT_max']:.0f}.", "op")
    tx(ox + 42, y + 24, f"Belt {b['P_belt_el_W']:.1f} W = utron Cu 6 × {b['P_utron_coil_W']:.2f} + La / Lb {b['P_fixed_W']:.2f} "
                        f"+ AH {b['P_AH_W']:.2f} + diodes {b['P_diode_W']:.2f} W; + iron {2 * b['P_fe_side_W']:.2f} W "
                        f"= {b['P_total_W']:.1f} W.", "op")
    tx(ox + 42, y + 42, f"With the bypass the belt reads {cu['P_belt_W']:.1f} W + iron {2 * b['P_fe_side_W']:.2f} W "
                        "(sim/ah-steady-cusp-findings.md).", "op")


# ------------------------------------------------------------------------------------------------ (b) electrostatic
def ring_core(xc, yc, th0, th1, rv=40):
    """the glass vessel with the two rings outside it: B on the upper hemisphere, A on the lower, each a band from th0
    to th1 (deg from the axis), drawn on both sides of the section; E at the null points down, from B (+) to A (-).
    Returns the points where B's and A's leads leave (the upper left and lower right bands' middles)."""
    o.append(f'<circle cx="{xc:.1f}" cy="{yc:.1f}" r="{rv:.1f}" class="glass"/>')
    for top, col in ((1, "#1f6fb2"), (-1, "#c0392b")):
        for side in (-1, 1):
            pts = [(xc + side * (rv + 2.5) * math.sin(math.radians(t)), yc - top * (rv + 2.5) * math.cos(math.radians(t)))
                   for t in np.linspace(th0, th1, 24)]
            o.append('<polyline points="' + " ".join(f"{x:.1f},{y:.1f}" for x, y in pts) +
                     f'" fill="none" stroke="{col}" stroke-width="5" stroke-linecap="round"/>')
    ln(xc, yc - 13, xc, yc + 6, "ef")
    o.append(f'<polygon points="{xc:.1f},{yc + 15:.1f} {xc - 4.5:.1f},{yc + 6:.1f} {xc + 4.5:.1f},{yc + 6:.1f}" fill="#1d3f5e"/>')
    tx(xc - 7, yc + 4, "E", "te", "end")
    tm = math.radians(0.5 * (th0 + th1))
    return ((xc - (rv + 2.5) * math.sin(tm), yc - (rv + 2.5) * math.cos(tm)),
            (xc + (rv + 2.5) * math.sin(tm), yc + (rv + 2.5) * math.cos(tm)))


def panel_b(ox, N):
    x1, x2, x3, x4, xb = ox + 250, ox + 345, ox + 440, ox + 535, ox + 605
    x1z, x4z = x1 + 48, x4 - 48
    y_s, y_bd, y_n, y_d3, y_d4, y_z, y_k, y_sh = 176, 199, 262, 300, 336, 372, 448, 700
    box(ox + 30, 110, 600, y_bd - 112, "zone_cr")
    tx(ox + 42, 128, "COUNTER-ROTOR", "zh")
    tx(ox + 42, 145, "stator vanes only: the reference plates of C1 / C2, no HV", "m")
    tx(ox + 42, 161, "joined to the shaft through one inner bearing (right)", "m")
    box(ox + 30, y_bd + 3, 600, 756 - y_bd - 3, "zone_r")
    tx(ox + 620, 748, "ROTOR · the HV circuit and the core, no rotating contact", "zh", "end")
    # the stator vanes' rail (the counter-rotor's reference) and C1 / C2 across the bodies
    ln(x1 - 20, y_s, xb, y_s, "rail")
    for x, nm, nd in ((x1, "C1(θ)", "node 1"), (x4, "C2(θ)", "node 4")):
        dot(x, y_s)
        ln(x, y_s, x, y_bd - 5)
        cap_v(x, y_bd - 5, 20); var_arrow(x, y_bd, 50, 40)
        ln(x, y_bd + 5, x, y_n)
        tx(x - 38, y_bd + 2, nm, "t", "end", 'font-weight="bold"')
    tx(x1 + 30, y_bd - 9, "6 stator vanes (REF)", "ms")
    tx(x1 + 12, y_bd + 24, "6 rotor vanes (R-A)", "ms")
    for x, nm, anc, dx in ((x1, "node 1", "end", -10), (x2, "node 2", "middle", 0), (x3, "node 3", "middle", 0),
                           (x4, "node 4", "start", 10)):
        dot(x, y_n); tx(x + dx, y_n - 12 if anc == "middle" else y_n - 6, nm, "nd", anc)
    # Ca (1-2), Cb (3-4)
    for xa, xb_, nm in ((x1, x2, "Ca"), (x3, x4, "Cb")):
        xm = (xa + xb_) / 2 - 5
        ln(xa, y_n, xm, y_n); cap_h(xm, y_n); ln(xm + 10, y_n, xb_, y_n)
        tx(xm + 5, y_n - 22, nm, "t", "middle", 'font-weight="bold"')
    # D3: 1 -> 3 ; D4: 4 -> 2
    dot(x1, y_d3); ln(x1, y_d3, x3 - 34, y_d3); diode(x3 - 34, y_d3, "right"); ln(x3 - 16, y_d3, x3, y_d3); dot(x3, y_d3)
    tx(x3 - 25, y_d3 - 15, "D3", "t", "middle")
    ln(x4, y_n, x4, y_z)
    dot(x4, y_d4); ln(x4, y_d4, x2 + 34, y_d4); diode(x2 + 34, y_d4, "left"); ln(x2 + 16, y_d4, x2, y_d4); dot(x2, y_d4)
    tx(x2 + 25, y_d4 - 15, "D4", "t", "middle")
    # D1: 2 -> shaft ; D2: 3 -> shaft
    for x, nm in ((x2, "D1"), (x3, "D2")):
        ln(x, y_n, x, 392); diode(x, 392, "down"); ln(x, 410, x, y_sh)
        tx(x + 16 if nm == "D1" else x - 16, 406, nm, "t", "start" if nm == "D1" else "end")
    # clamps Z1 (1 -> shaft), Z4 (4 -> shaft)
    for x, xz, nm in ((x1, x1z, "Z1"), (x4, x4z, "Z4")):
        dot(x, y_z); pl([(x, y_z), (xz, y_z), (xz, 392)], "lim"); diode(xz, 392, "down", "#7d3c98", zener=True)
        ln(xz, 410, xz, y_sh, "lim"); tx(xz + (14 if x == x1 else -14), 406, nm, "tl", "start" if x == x1 else "end")
    # the core: two rings outside the glass. B on the record's Cockcroft-Walton stages on node 4's swing; A either on
    # node 1's negative peak (Dk, C_A) or, the symmetric supply, on the mirror-image chain on node 1 (Coa, Dca, Dpa, Csa);
    # each chain's stage drawn once; all storage 100 pF to the shaft
    dc, nl = N["dc"], N["ring"]
    sym = nl.get("a_ref") == "shaft"
    xk, yc, xl = ox + 105, 345, ox + 48
    y_cw = 590 if sym else 536
    y_a = 466 if sym else y_k
    ln(x4, y_z, x4, y_cw); dot(x4, y_cw)
    (xbl, ybl), (xar, yar) = ring_core(xk, yc, nl["theta_p"], nl["theta_e"])
    if sym:
        # A: the lower ring's lead round to its chain's output; Csa to the shaft; Dpa from A into the oscillating node
        ln(x1, y_n, x1, y_a); dot(x1, y_a)
        pl([(xar, yar), (xar, 398), (ox + 30, 398), (ox + 30, y_a), (ox + 100, y_a)])
        dot(xl, y_a); ln(xl, y_a, xl, y_a + 24); cap_v(xl, y_a + 24, 14); ln(xl, y_a + 34, xl, y_a + 50)
        ground(xl, y_a + 50)
        tx(xl + 20, y_a + 33, "Csa", "t", "start", 'font-weight="bold"')
        ln(ox + 30, y_a, ox + 100, y_a); diode(ox + 100, y_a, "right"); ln(ox + 118, y_a, ox + 150, y_a)   # Dpa: A -> n
        tx(ox + 109, y_a - 15, "Dpa", "t", "middle", 'font-weight="bold"')
        dot(ox + 150, y_a); tx(ox + 150, y_a - 10, "n", "ms", "middle")
        ln(ox + 150, y_a, ox + 150, y_a + 12); diode(ox + 150, y_a + 12, "down"); ln(ox + 150, y_a + 30, ox + 150, y_a + 50)
        ground(ox + 150, y_a + 50)                                                                  # Dca: n -> shaft
        tx(ox + 166, y_a + 27, "Dca", "t", "start", 'font-weight="bold"')
        ln(ox + 150, y_a, ox + 190, y_a); cap_h(ox + 190, y_a, 10); ln(ox + 200, y_a, x1, y_a)   # Coa: node 1 -> n
        tx(ox + 195, y_a - 16, "Coa", "t", "middle", 'font-weight="bold"')
        o.append(f'<rect x="{ox + 22:.1f}" y="{y_a - 32:.1f}" width="{ox + 222 - (ox + 22):.1f}" height="94" '
                 'fill="none" stroke="#7f8c8d" stroke-width="1.2" stroke-dasharray="5 4"/>')
        tx(ox + 228, y_a - 36, f"× {nl['n_a']} stages, mirrored", "t", "end", 'font-weight="bold"')
    else:
        ln(x1, y_n, x1, y_k); dot(x1, y_k)
        # A: from the lower ring down to the Dk lead; C_A to the shaft
        pl([(xar, yar), (xar, y_k), (xk, y_k)])
        ln(xk, y_k, ox + 170, y_k); diode(ox + 170, y_k, "right"); ln(ox + 188, y_k, x1, y_k)
        tx(ox + 179, y_k - 15, "Dk", "t", "middle", 'font-weight="bold"')
        dot(ox + 132, y_k); ln(ox + 132, y_k, ox + 132, y_k + 18); cap_v(ox + 132, y_k + 18, 14)
        ln(ox + 132, y_k + 28, ox + 132, y_k + 44); ground(ox + 132, y_k + 44)
        tx(ox + 152, y_k + 27, "C_A", "t", "start", 'font-weight="bold"')
    # B: from the upper ring up and round to the multiplier's output; Cs to the shaft
    pl([(xbl, ybl), (xbl, 270), (xl - 30 if sym else xl, 270), (xl - 30 if sym else xl, y_cw), (ox + 100, y_cw)])
    dot(xl, y_cw); ln(xl, y_cw, xl, y_cw + 30); cap_v(xl, y_cw + 30, 14); ln(xl, y_cw + 40, xl, y_cw + 58)
    ground(xl, y_cw + 58)
    tx(xl + 20, y_cw + 39, "Cs", "t", "start", 'font-weight="bold"')
    diode(ox + 118, y_cw, "left"); ln(ox + 118, y_cw, ox + 150, y_cw)                       # Dp: m -> B
    tx(ox + 109, y_cw - 15, "Dp", "t", "middle", 'font-weight="bold"')
    dot(ox + 150, y_cw); tx(ox + 150, y_cw - 10, "m", "ms", "middle")
    ln(ox + 150, y_cw, ox + 150, y_cw + 18); diode(ox + 150, y_cw + 36, "up"); ln(ox + 150, y_cw + 36, ox + 150, y_cw + 58)
    ground(ox + 150, y_cw + 58)                                                                # Dc: shaft -> m
    tx(ox + 166, y_cw + 31, "Dc", "t", "start", 'font-weight="bold"')
    ln(ox + 150, y_cw, ox + 190, y_cw); cap_h(ox + 190, y_cw, 10); ln(ox + 200, y_cw, x4, y_cw)   # Co: node 4 -> m
    tx(ox + 195, y_cw - 16, "Co", "t", "middle", 'font-weight="bold"')
    o.append(f'<rect x="{ox + 22 if sym else ox + 36:.1f}" y="{y_cw - 34:.1f}" '
             f'width="{ox + 222 - (ox + 22 if sym else ox + 36):.1f}" height="104" '
             'fill="none" stroke="#7f8c8d" stroke-width="1.2" stroke-dasharray="5 4"/>')
    tx(ox + 228, y_cw - 38, f"× {nl['n_cw']} stages", "t", "end", 'font-weight="bold"')
    tx(ox + 42, y_cw + 90, ("Coa, Csa, Co, Cs" if sym else "C_A, Co, Cs") + " 100 pF · ground = the shaft", "ms", "start")
    tx(xk + 50, yc - 23, f"B +{nl['V_B_kV']:.1f} kV", "tu", "start", 'font-weight="bold"')
    tx(xk + 50, yc - 5, f"rings {nl['theta_p']:.0f}–{nl['theta_e']:.0f}°", "ms")
    tx(xk + 50, yc + 9, f"{nl['E_dc_kV_cm']:.1f} kV/cm ↓", "ms")
    tx(xk + 50, yc + 23, f"{nl['p_dc_Pa']:.1f} Pa", "ms")
    tx(xk + 50, yc + 43, f"A {kv(nl['V_A_kV'])} kV", "ta", "start", 'font-weight="bold"')
    tx(ox + 42, 226, "THE CORE (hub)", "zh")
    tx(ox + 42, 242, "rings outside the glass", "ms")
    # the one rotating contact: an inner bearing (outer ring on the counter-rotor, inner ring on the shaft)
    ln(xb, y_s, xb, y_bd - 10)
    ln(xb - 17, y_bd - 10, xb + 17, y_bd - 10, "ring"); ln(xb - 17, y_bd + 10, xb + 17, y_bd + 10, "ring")
    for dx in (-10, 0, 10):
        o.append(f'<circle cx="{xb + dx:.1f}" cy="{y_bd:.1f}" r="3.8" class="ball"/>')
    ln(xb, y_bd + 10, xb, y_sh)
    lk = N["dc"]["link"]
    y_lb = 614 if sym else 560                                         # clear of the B chain's Co lead
    for i, t_ in enumerate(("inner bearing", "(6205), for now;", "a brush later", f"{lk['I_rms_mA']:.2f} mA rms AC",
                            "no DC")):
        tx(xb - 8, y_lb + 14 * i, t_, "t" if i == 0 else "ms", "end", 'font-weight="bold"' if i == 0 else "")
    # shaft
    ln(x1z - 18, y_sh, xb + 12, y_sh, "rail")
    for x in (x1z, x2, x3, x4z, xb):
        dot(x, y_sh)
    tx(x1z - 18, y_sh + 20, "shaft (rotor) = REF, shared with (a)", "m")


def panel_b_table(ox, y, N):
    d, cf, R = N["cf"]["design"], N["cf"], N["cfr"]
    fs, nl = N["dc"], N["ring"]
    vr = fs["VR_pk_kV"]
    zs = N["duty"]["clamp_string"]
    n_z = math.ceil(d["V_op_kV"] * 1e3 / zs["V_Z"])
    rows = [
        ("C1, C2", f"{d['n_plates']} + {d['n_plates']} vanes, 6 × {d['ws_deg']:g}° / {d['wr_deg']:g}°, {d['gap_mm']:g} mm "
                   f"air gaps, {d['t_vaneMm']:g} mm full rounds: {d['C_min_pF']:.0f}–{d['C_max_pF']:.0f} pF, "
                   f"κ {d['kappa']:.1f}"),
        ("Ca, Cb", f"{d['Ca_pF']:.0f} pF (1.1 C_max): full-annulus plates, now on the rotor"),
        ("D1–D4", f"HV stacks, reverse peaks {vr['D1']:.1f} / {vr['D2']:.1f} / {vr['D3']:.1f} / {vr['D4']:.1f} kV; "
                  "parts not chosen"),
        ("Z1, Z4", f"avalanche strings, BV {d['V_op_kV']:.1f} kV (e.g. {n_z} × {zs['V_Z']:.0f} V), on the rotor: "
                   f"{fs['Z1']['P_W']:.2f} W, {fs['Z1']['I_pk_mA']:.2f} mA peak each"),
        ("core", f"two rings outside the 50 mm glass: Cu foil bands {nl['theta_p']:.1f}–{nl['theta_e']:.1f}°, "
                 f"{nl['gap_mm']:.1f} mm apart along it"),
        ("", f"beaded edges Ø{2 * nl['rho_pol_mm']:g} / Ø{2 * nl['rho_eq_mm']:g} mm (polar / equatorial) in gel, "
             "under the PEEK retainer"),
        ("supply", (f"A: {nl['n_a']} CW stages on node 1, mirrored, {kv(nl['V_A_kV'])} kV" if nl.get("a_ref") == "shaft"
                    else f"A: Dk + C_A on node 1's peak, {kv(nl['V_A_kV'])} kV") +
                   f" · B: {nl['n_cw']} CW stages on node 4, +{nl['V_B_kV']:.1f} kV"),
        ("", f"100 pF storage; {'Dca, Dpa, Dc, Dp' if nl.get('a_ref') == 'shaft' else 'Dk, Dc, Dp'} ≤ "
             f"{max(v for k, v in vr.items() if k[:2] in ('Dk', 'Dc', 'Dp')):.1f} kV "
             f"reverse; {1e3 * fs['P_leak_W']:.0f} mW leakage at 100 GΩ/ring [RH]"),
        ("", f"{nl['V_gap_kV']:.1f} kV across: {nl['E_dc_kV_cm']:.1f} kV/cm, {nl['p_dc_Pa']:.1f} Pa at the null "
             f"(as connected; {nl['E_settled_kV_cm']:.1f} settled)"),
        ("strays", f"≈ {cf['CPAR_pF']:.0f} pF per node [RH]; the rings {nl['C_ring_ref_pF']:.1f} pF each to REF, "
                   f"{nl['C_ring_ring_pF']:.1f} pF between"),
        ("bearing", f"one inner bearing, for now: {fs['link']['I_rms_mA']:.2f} mA rms AC "
                    f"({fs['link']['I_pk_mA']:.2f} mA pk), no DC"),
    ]
    y = table(ox + 42, y, rows, w_key=76)
    tx(ox + 42, y + 6, f"At {cf['rpm_rel']:.0f} rpm relative ({cf['F_Hz']:.0f} Hz): belt {fs['P_belt_W']:.2f} W, into "
                       f"Z1 + Z4; z at start {N['dc_free']['z']:.3f} (bare {R['free none']['z']:.3f}).", "op")


# ------------------------------------------------------------------------------------------------ sheet
def main():
    N = numbers()
    W, H = 1440, 1288
    o.append(f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}" '
             'font-family="DejaVu Sans, Arial, sans-serif" font-size="13">')
    o.append("<title>Rotor circuits</title>")
    o.append(f'<rect width="{W}" height="{H}" fill="#ffffff"/>')
    o.append("""<style>
    .w{stroke:#111;stroke-width:2;fill:none} .ut{stroke:#1f6fb2;stroke-width:2.4;fill:none} .ah{stroke:#c0392b;stroke-width:2.6;fill:none}
    .st{stroke:#8a8a8a;stroke-width:2;fill:none} .lim{stroke:#7d3c98;stroke-width:2.2;fill:none}
    .zl{stroke:#7d3c98;stroke-width:2;fill:none} .va{stroke:#111;stroke-width:1.6}
    .pl{stroke:#111;stroke-width:2.6} .rail{stroke:#111;stroke-width:3} .mag{stroke:#7f8c8d;stroke-width:1.4;stroke-dasharray:3 4}
    .br{fill:#9aa3ad;stroke:#5d6670;stroke-width:1} .brush{fill:#444;stroke:#111;stroke-width:1}
    .ring{stroke:#111;stroke-width:4} .ball{fill:#fff;stroke:#111;stroke-width:1.6} .dot{fill:#111}
    .zone_cr{fill:#f3f0e6;stroke:#b9ad8a;stroke-width:1;stroke-dasharray:6 4} .zone_r{fill:#eef3f8;stroke:#9fb3c8;stroke-width:1;stroke-dasharray:6 4}
    .kick{fill:#fff7ec;stroke:#d68910;stroke-width:1.4;stroke-dasharray:5 4} .frame{fill:none;stroke:#999;stroke-width:1}
    .prop{stroke:#9c640c;stroke-width:1.6;fill:none;stroke-dasharray:5 3} .propc{stroke:#9c640c;stroke-width:2.4}
    .tp{fill:#9c640c;font-size:10.5px}
    .t{fill:#111} .tu{fill:#1f6fb2} .ta{fill:#c0392b} .tl{fill:#7d3c98} .nd{fill:#111;font-size:12.5px}
    .m{fill:#444;font-size:12px} .ms{fill:#555;font-size:11px} .zh{fill:#333;font-size:12.5px;font-weight:bold;letter-spacing:0.06em}
    .tk{fill:#111;font-size:11.5px;font-weight:bold} .tk2{fill:#9c640c;font-size:11.5px;font-weight:bold} .tv{fill:#333;font-size:11.5px}
    .op{fill:#1d3f5e;font-size:11.5px} .h{font-size:17px;font-weight:bold;fill:#111} .h2{font-size:14px;font-weight:bold;fill:#111}
    .n{fill:#444;font-size:11.5px} .te{fill:#1d3f5e;font-size:12px;font-weight:bold} .ef{stroke:#1d3f5e;stroke-width:1.8}
    .cone_a{fill:#f6d5d1;stroke:#c0392b;stroke-width:2.6} .cone_b{fill:#dbe7f3;stroke:#1f6fb2;stroke-width:2.6}
    .glass{fill:#eaf3f8;fill-opacity:0.92;stroke:#6f8ea6;stroke-width:1.3}
  </style>""")
    b = N["b"]
    tx(20, 30, "DCCREG turbine: the rotor's two circuits as built (tube, wound utrons; rotor and counter-rotor geared 1 : −1)", "h")
    tx(20, 52, f"(a) the reluctance pump drives the AH pair · (b) the electrostatic pump's rings hold a DC field on the AH null; only C1 / C2 "
               f"straddle the bodies · operating point {PICK} relative · only diodes switch", "m")
    for ox, w, title in ((20, 760, "(a) RELUCTANCE: magnetic dual doubler → AH pair"),
                         (800, 620, "(b) ELECTROSTATIC: de Queiroz diode doubler → DC field on the null")):
        box(ox, 70, w, 1000, "frame")
        tx(ox + 12, 94, title, "h2")
    panel_a(20, N)
    panel_b(780, N)
    panel_a_table(20, 778, N)
    panel_b_table(780, 778, N)
    notes = [
        "Bodies. Rotor: shaft, sleeve, rotor vanes (nodes 1 / 4), Ca / Cb plates, the 6 utrons on their carrier discs, the hub "
        "(the glass vessel with the rings outside it, the AH pair, retainer and coupler).",
        "Counter-rotor: stator cage, stator vanes (REF), bridges. Frame: end bearings, the gear.",
        "Not in the solids yet: La, Lb, D1*–D4*, the RC snubbers, the kick source, D1–D4, Z1 / Z4, " +
        ("the two CW chains, " if N["ring"].get("a_ref") == "shaft" else "Dk, the CW stage, C_A, ") +
        "the rings (all rotor);",
        "sim/tube_geometry.py still puts Ca / Cb on the counter-rotor. Each pump's reaction torque goes into the gear.",
        "(a) is the planar dual of (b) [OC]: C → L, V → I, Q → Ψ, Ca / Cb → La / Lb, Cpar → Lp2 / Lp3, D1–D4 → D1*–D4*, "
        "the clamps Z1 / Z4 → the NiFe neck's saturation.",
        "A and B swap every half cycle: one group generates (L falling) while the other motors. The AH coils are named by branch; "
        "sim/magnetic_doubler.py calls them AH top / bottom (A was then the upper side).",
        ("Polarity: (b) runs negative; ring A on its own chain from node 1, negative, and ring B on the mirror chain from "
         "node 4, positive (the symmetric supply): E at the null " if N["ring"].get("a_ref") == "shaft" else
         f"Polarity: (b) runs negative; ring A takes node 1's negative peak and ring B {N['ring']['n_cw']} CW stages "
         "positive: E at the null ") +
        "is steady, B to A.",
        "de Queiroz's Fig. 1 draws the core positive, all four diodes the other way (sim/queiroz_fig1_check.py).",
        f"Numbers: sim/pole_design_variants_op.json ({PICK}), sim/utron_profile.py, sim/rotor_parts_duty_results.json, "
        "sim/core_field_results.json, sim/hub_rings_build_results.json (b: the air build's capped stack)",
        "Netlists: sim/magnetic_doubler.py, sim/core_field.py · findings: sim/pole-design-findings.md, sim/hub-rings-build-findings.md "
        "· generator: docs/make_schematic_rotor.py",
    ]
    y = 1094
    for s in notes:
        tx(20, y, s, "n"); y += 19
    o.append("</svg>")
    svg = OUT + ".svg"
    open(svg, "w").write("\n".join(o) + "\n")
    png = render_png(svg, W, H)
    print(json.dumps(dict(svg=os.path.relpath(svg, ROOT), png=png and os.path.relpath(png, ROOT))))


def render_png(svg, W, H, scale=2):
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        return None
    png = OUT + ".png"
    with sync_playwright() as p:
        b = p.chromium.launch(executable_path=os.environ.get("CHROMIUM", "/opt/pw-browsers/chromium"))
        pg = b.new_page(viewport={"width": W, "height": H}, device_scale_factor=scale)
        pg.set_content(f'<html><body style="margin:0">{open(svg).read()}</body></html>')
        pg.screenshot(path=png, clip=dict(x=0, y=0, width=W, height=H))
        b.close()
    return png


if __name__ == "__main__":
    main()
