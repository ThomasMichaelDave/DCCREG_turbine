"""docs/make_schematic_rotor.py -- writes docs/schematic-rotor-circuits.{svg,png}: the machine's two circuits as built
(the tube with wound utrons, sim/tube_geometry.py --rel wound), with the body each part rides on.
(a) RELUCTANCE: the magnetic dual doubler (sim/magnetic_doubler.py netlist) -- the A / B groups of 3 wound utrons each,
    the AH coil of its branch in series, La / Lb, the wiring strays Lp2 / Lp3, D1*-D4*; everything on the rotor. The
    counter-rotor's passive bridges make L(theta); no wire crosses between the bodies.
(b) ELECTROSTATIC: the de Queiroz diode doubler (sim/bicone_drive.py netlist) -- C1 / C2 between the counter-rotor's
    stator vanes and the rotor vanes, Ca / Cb, D1-D4, the 20 kV clamps, the bicone cones from the rotor vanes to the
    shaft; one brush from the counter-rotor's reference rail to the shaft.
Values: sim/pole_design_variants_op.json (the pick), sim/utron_profile.py, sim/bicone_drive.py and its results,
sim/tube_geometry_wound_results.json.
Usage: python3 docs/make_schematic_rotor.py   (the PNG needs playwright + chromium)
"""
import json
import math
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(ROOT, "sim"))
import bicone_drive as BDm         # noqa: E402  (the ES netlist's constants)
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
    bd = json.load(open(os.path.join(ROOT, "sim", "bicone_drive_results.json")))
    tube = json.load(open(os.path.join(ROOT, "sim", "tube_geometry_wound_results.json")))
    return dict(op=op, b=b, sp=sp, Lg=Lg, ah=ah, F=F, csn=csn, rsn=rsn, la=LA_RATIO * Lg, lp=MDm.R_PAR * Lg,
                bd_d=[r for r in bd["rows"] if r["mode"] == "diodes"][0],
                bd_g=[r for r in bd["rows"] if r["mode"] == "dump" and "steps" not in r and "reltol" not in r][0],
                bd_F=bd["F"], tube=tube)


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
    box(xa + 60, 520, 190, 66, "kick")
    tx(xa + 70, 540, "START KICK: source open", "tk2")
    tx(xa + 70, 557, f"once, ≥ {100 * b['kick_frac']:.0f} % of I_pk ({b['kick_mJ']:.0f} mJ)", "ms")
    tx(xa + 70, 573, "into the utron loop at start-up", "ms")
    # the node snubber, drawn once
    xs, ys = xc + 70, 528
    dot(xs, ys); tx(xs + 10, ys + 4, "any node", "ms")
    ln(xs, ys, xs, ys + 14); cap_v(xs, ys + 14, 12); ln(xs, ys + 24, xs, ys + 36); res_v(xs, ys + 36, 30)
    ln(xs, ys + 66, xs, ys + 74); ground(xs, ys + 74)
    tx(xs + 22, ys + 30, "RC to REF at each", "ms"); tx(xs + 22, ys + 45, "of the 8 nodes [IR]", "ms")
    tx(xs + 22, ys + 60, f"{N['csn'] * 1e9:.0f} nF + {N['rsn']:.0f} Ω", "ms")


def panel_a_table(ox, y, N):
    b, sp, ah = N["b"], N["sp"], N["ah"]
    rows = [
        ("A1–A3, B1–B3", f"wound utrons at 0 / 120 / 240°, {sp['N_u']} t of Ø{sp['wire_d_mm']:.2f} mm Cu: "
                         f"{1e3 * sp['L_al_coil_H']:.1f} / {1e3 * sp['L_un_coil_H']:.1f} mH (aligned / unaligned), "
                         f"{sp['R_coil_ohm']:.2f} Ω each"),
        ("group", f"L̂ {N['Lg']:.3f} H, ratio κ {N['op']['kappa']:.1f}, τ = L/R {N['op']['tau']:.3f} s; "
                  f"Ψs {b['psi_s']:.3f} Wb-t (the {sp['t_n']:.1f} mm NiFe neck)"),
        ("bridges", f"a passing bridge closes the utron's flux path: L(θ) {sp['n_br']} × per rev; B row half a pitch on"),
        ("AH", f"anti-Helmholtz pair at the hub, one coil per branch: {ah['N']} t, {ah['L'] * 1e3:.2f} mH, "
               f"{ah['R']:.2f} Ω each [RH]"),
        ("La, Lb", f"{N['la']:.3f} H ({LA_RATIO:g} L̂), {N['la'] / TAU_FIXED:.2f} Ω (τ {TAU_FIXED:g} s) [RH]: gapped cores, not designed"),
        ("Lp2, Lp3", f"{N['lp'] * 1e3:.1f} mH wiring stray, as modelled (dual of Cpar) [IR]"),
        ("D1*–D4*", f"Si, 0.55 V at 1 A; {b['I_pk']:.1f} A peak; reverse voltage not yet checked"),
    ]
    y = table(ox + 42, y, rows)
    I_min = b["AT_min"] / ah["N"]
    tx(ox + 42, y + 6, f"At {b['rpm']:.0f} rpm relative ({N['F']:.0f} Hz): {I_min:.2f}–{b['I_pk']:.2f} A in each branch, "
                       f"{b['V_pk']:.0f} V peak per group; AH {b['AT_min']:.0f}–{b['AT_pk']:.0f} A-turns.", "op")
    tx(ox + 42, y + 24, f"Belt {b['P_belt_el_W']:.1f} W = utron Cu 6 × {b['P_utron_coil_W']:.2f} + La / Lb {b['P_fixed_W']:.2f} "
                        f"+ AH {b['P_AH_W']:.2f} + diodes {b['P_diode_W']:.2f} W; + iron {2 * b['P_fe_side_W']:.2f} W "
                        f"= {b['P_total_W']:.1f} W.", "op")


# ------------------------------------------------------------------------------------------------ (b) electrostatic
def panel_b(ox, N):
    x1, x2, x3, x4 = ox + 120, ox + 240, ox + 380, ox + 500
    x1z, x4z = x1 + 56, x4 - 56
    top, y_d3, y_d4, y_z, y_cr, y_bd, y_sh = 236, 278, 314, 350, 432, 488, 690
    box(ox + 30, 110, 600, y_bd - 112, "zone_cr")
    tx(ox + 42, 128, "COUNTER-ROTOR", "zh")
    tx(ox + 42, 145, "stator vanes, the Ca / Cb plates, the diodes and clamps", "m")
    tx(ox + 42, 162, "nodes 1–4 run negative, clamped at −20 kV", "m")
    box(ox + 30, y_bd + 2, 600, 256, "zone_r")
    tx(ox + 620, y_bd + 250, "ROTOR · rotor vanes, cones, shaft", "zh", "end")
    for x, nm in ((x1, "node 1"), (x2, "node 2"), (x3, "node 3"), (x4, "node 4")):
        dot(x, top); tx(x, top - 14, nm, "nd", "middle")
    # Ca (1-2), Cb (3-4)
    xm = (x1 + x2) / 2 - 5
    ln(x1, top, xm, top); cap_h(xm, top); ln(xm + 10, top, x2, top); tx(xm + 5, top - 22, "Ca", "t", "middle", 'font-weight="bold"')
    xm = (x3 + x4) / 2 - 5
    ln(x3, top, xm, top); cap_h(xm, top); ln(xm + 10, top, x4, top); tx(xm + 5, top - 22, "Cb", "t", "middle", 'font-weight="bold"')
    # D3: 1 -> 3 ; D4: 4 -> 2
    dot(x1, y_d3); ln(x1, y_d3, x3 - 34, y_d3); diode(x3 - 34, y_d3, "right"); ln(x3 - 16, y_d3, x3, y_d3); dot(x3, y_d3)
    tx(x3 - 25, y_d3 - 15, "D3", "t", "middle")
    dot(x4, y_d4); ln(x4, y_d4, x2 + 34, y_d4); diode(x2 + 34, y_d4, "left"); ln(x2 + 16, y_d4, x2, y_d4); dot(x2, y_d4)
    tx(x2 + 25, y_d4 - 15, "D4", "t", "middle")
    # D1: 2 -> ref ; D2: 3 -> ref (the counter-rotor rail)
    for x, nm in ((x2, "D1"), (x3, "D2")):
        ln(x, top, x, 372); diode(x, 372, "down"); ln(x, 390, x, y_cr)
        tx(x + 16 if nm == "D1" else x - 16, 386, nm, "t", "start" if nm == "D1" else "end")
    # clamps Z1 (1 -> rail), Z4 (4 -> rail)
    for x, xz, nm in ((x1, x1z, "Z1"), (x4, x4z, "Z4")):
        dot(x, y_z); pl([(x, y_z), (xz, y_z), (xz, 372)], "lim"); diode(xz, 372, "down", "#7d3c98", zener=True)
        ln(xz, 390, xz, y_cr, "lim"); tx(xz + (14 if x == x1 else -14), 386, nm, "tl", "start" if x == x1 else "end")
    ln(x1z, y_cr, x4z, y_cr, "rail")
    for x in (x1z, x2, x3, x4z):
        dot(x, y_cr)
    tx((x2 + x3) / 2, y_cr + 18, "counter-rotor reference rail", "ms", "middle")
    # C1 / C2 straddle the bodies: stator vanes above, rotor vanes below
    for x, nm, rail, cone, side in ((x1, "C1(θ)", "R-A", "cone A", -1), (x4, "C2(θ)", "R-B", "cone B", +1)):
        ln(x, top, x, y_bd - 8)
        cap_v(x, y_bd - 8, 20); var_arrow(x, y_bd - 3, 50, 40)
        ln(x, y_bd + 2, x, y_bd + 34); dot(x, y_bd + 34)
        tx(x - 14 if side < 0 else x + 14, y_bd + 38, rail, "nd", "end" if side < 0 else "start")
        ye = coil_v(x, y_bd + 50, 5, "ah"); ln(x, y_bd + 34, x, y_bd + 50); ln(x, ye, x, y_sh)
        tx(x + 18, y_bd + 78, cone, "ta", "start", 'font-weight="bold"')
        tx(x + 18, y_bd + 94, "lower cone" if side < 0 else "upper cone", "ms")
        o.append(f'<circle cx="{x - 8:.1f}" cy="{y_bd + 52:.1f}" r="2.6" fill="#c0392b"/>')    # dot convention: aiding
        tx(x - 34 if side < 0 else x + 34, y_bd + 2, nm, "t", "end" if side < 0 else "start", 'font-weight="bold"')
    tx(x1 + 30, y_bd - 16, "8 stator vanes (node 1)", "ms"); tx(x1 + 30, y_bd + 22, "8 rotor vanes (R-A)", "ms")
    # the brush: the one rotating contact
    xm = (x2 + x3) / 2
    ln(xm, y_cr, xm, y_bd - 14)
    o.append(f'<rect x="{xm - 6:.1f}" y="{y_bd - 14:.1f}" width="12" height="13" class="brush"/>')
    ln(xm - 26, y_bd + 1, xm + 26, y_bd + 1, "ring")
    ln(xm, y_bd + 1, xm, y_sh)
    tx(xm + 14, y_bd - 4, "brush", "t", "start", 'font-weight="bold"')
    tx(xm + 14, y_bd + 20, "the only rotating contact", "ms")
    # shaft
    ln(x1 - 20, y_sh, x4 + 20, y_sh, "rail")
    for x in (x1, xm, x4):
        dot(x, y_sh)
    tx(x1 - 20, y_sh + 20, "shaft (rotor) = REF, shared with (a)", "m")


def panel_b_table(ox, y, N):
    t = N["tube"]
    d, g = N["bd_d"], N["bd_g"]
    rows = [
        ("C1, C2", f"8 + 8 vanes, 6 sectors, 3 mm vacuum gaps: {BDm.CMIN * 1e12:.1f}–{t['C_max_pF']:.0f} pF "
                   f"(κ {t['kappa']:.1f}); C2 in antiphase"),
        ("Ca, Cb", f"8 fixed plates each (4 at each node): {BDm.CA * 1e12:.0f} pF ({BDm.CA / BDm.CMAX:.1f} C_max)"),
        ("D1–D4", "HV diode stacks for the 20 kV swing (part not chosen)"),
        ("Z1, Z4", "avalanche clamps, BV 20 kV; option: a 20 kV spark gap + quench diode (the dump)"),
        ("cones A, B", f"the bicone halves, {BDm.N_CONE} t, {BDm.L_CONE * 1e6:.1f} µH, {BDm.R_CONE:.2f} Ω each; "
                       f"M {BDm.M_CONE * 1e6:.1f} µH (k {BDm.M_CONE / BDm.L_CONE:.3f}, aiding) [RH]"),
        ("strays", f"≈ {BDm.CPAR * 1e12:.0f} pF at every node [RH]"),
        ("brush", "rail to shaft: carries the cone current (mA); with the dump, the 21 A pulses"),
    ]
    y = table(ox + 42, y, rows, w_key=76)
    tx(ox + 42, y + 6, f"At {60 * N['bd_F'] / 6:.0f} rpm relative ({N['bd_F']:.0f} Hz; the pick runs 1200 rpm, 120 Hz, "
                       "about twice the power: not re-run):", "op")
    tx(ox + 42, y + 24, f"diodes only: belt {d['P_belt_W']:.1f} W into the clamps; cones {d['I_cone_rms_mA']:.1f} mA rms "
                        f"({d['AT_pk']:.2f} A-turns): the bicone is decorative.", "op")
    tx(ox + 42, y + 42, f"dump: {g['I_cone_pk_A']:.0f} A peak, {g['AT_pk']:.0f} A-turns, {g['E_per_dump_mJ']:.0f} mJ per dump, "
                        f"{g['dumps_per_s_A']:.0f} per s per side, ring {g['f_ring_analytic_MHz']:.1f} MHz.", "op")


# ------------------------------------------------------------------------------------------------ sheet
def main():
    N = numbers()
    W, H = 1440, 1150
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
    .ring{stroke:#111;stroke-width:5} .dot{fill:#111}
    .zone_cr{fill:#f3f0e6;stroke:#b9ad8a;stroke-width:1;stroke-dasharray:6 4} .zone_r{fill:#eef3f8;stroke:#9fb3c8;stroke-width:1;stroke-dasharray:6 4}
    .kick{fill:#fff7ec;stroke:#d68910;stroke-width:1.4;stroke-dasharray:5 4} .frame{fill:none;stroke:#999;stroke-width:1}
    .t{fill:#111} .tu{fill:#1f6fb2} .ta{fill:#c0392b} .tl{fill:#7d3c98} .nd{fill:#111;font-size:12.5px}
    .m{fill:#444;font-size:12px} .ms{fill:#555;font-size:11px} .zh{fill:#333;font-size:12.5px;font-weight:bold;letter-spacing:0.06em}
    .tk{fill:#111;font-size:11.5px;font-weight:bold} .tk2{fill:#9c640c;font-size:11.5px;font-weight:bold} .tv{fill:#333;font-size:11.5px}
    .op{fill:#1d3f5e;font-size:11.5px} .h{font-size:17px;font-weight:bold;fill:#111} .h2{font-size:14px;font-weight:bold;fill:#111}
    .n{fill:#444;font-size:11.5px}
  </style>""")
    b = N["b"]
    tx(20, 30, "DCCREG turbine: the rotor's two circuits as built (tube, wound utrons; rotor and counter-rotor geared 1 : −1)", "h")
    tx(20, 52, f"(a) the reluctance pump drives the AH pair, all on the rotor · (b) the electrostatic pump drives the bicone, "
               f"across both bodies · operating point {PICK} relative · only diodes switch", "m")
    for ox, w, title in ((20, 760, "(a) RELUCTANCE: magnetic dual doubler → AH pair"),
                         (800, 620, "(b) ELECTROSTATIC: de Queiroz diode doubler → bicone")):
        box(ox, 70, w, 900, "frame")
        tx(ox + 12, 94, title, "h2")
    panel_a(20, N)
    panel_b(780, N)
    panel_a_table(20, 778, N)
    panel_b_table(780, 778, N)
    notes = [
        "Bodies. Rotor: shaft, sleeve, rotor vanes (R-A, R-B), the 6 utrons on their carrier discs, the hub (bicone, AH pair). "
        "Counter-rotor: stator cage, stator vanes, Ca / Cb plates, bridges. Frame: end bearings, the gear.",
        "Not in the solids yet: La, Lb, D1*–D4*, the RC snubbers and the kick source (rotor); D1–D4 and Z1 / Z4 (counter-rotor). "
        "The two pumps share only the shaft; each one's reaction torque goes into the gear.",
        "(a) is the planar dual of (b) [OC]: C → L, V → I, Q → Ψ, Ca / Cb → La / Lb, Cpar → Lp2 / Lp3, D1–D4 → D1*–D4*, "
        "the 20 kV clamp → the NiFe neck's saturation.",
        "A and B swap every half cycle: one group generates (L falling) while the other motors. The AH coils are named by branch; "
        "sim/magnetic_doubler.py calls them AH top / bottom (A was then the upper side).",
        f"Numbers: sim/pole_design_variants_op.json ({PICK}), sim/utron_profile.py, sim/bicone_drive_results.json, "
        "sim/tube_geometry_wound_results.json · netlists: sim/magnetic_doubler.py, sim/bicone_drive.py",
        "Findings: sim/pole-design-findings.md, sim/hub-drive-findings.md · generator: docs/make_schematic_rotor.py",
    ]
    y = 994
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
