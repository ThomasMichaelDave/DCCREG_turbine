"""docs/make_schematic_hub.py -- writes docs/schematic-hub-drive.svg: the central cavity driven by the two pumps.
(a) the MAGNETIC dual doubler on the rotor: A / B wound-utron groups (variable inductors against the stator's toothed
    C-EM iron), fixed coupling inductors La / Lb, four diodes, AH top in the A branch and AH bottom in the B branch;
    with the A / B current over one cycle (sim/magnetic_doubler.py).
(b) the ELECTROSTATIC diode doubler on the stator vanes with the bicone halves in series with C1 / C2 on the rotor side,
    limited either by avalanche clamps (diodes only) or by spark gaps with quench diodes (the dump test)
    (sim/bicone_drive.py).
Rotor and stator are geared 1 : -1 (300 rpm each, 600 rpm relative).
Usage: python3 docs/make_schematic_hub.py
"""
import json
import os

HERE = os.path.dirname(os.path.abspath(__file__))
MD = json.load(open(os.path.join(HERE, "..", "sim", "magnetic_doubler_results.json")))
BD = json.load(open(os.path.join(HERE, "..", "sim", "bicone_drive_results.json")))
o = []


def ln(x1, y1, x2, y2, cl="w"):
    o.append(f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" class="{cl}"/>')


def tx(x, y, s, cl="t", extra=""):
    o.append(f'<text x="{x}" y="{y}" class="{cl}" {extra}>{s}</text>')


def dot(x, y):
    o.append(f'<circle cx="{x}" cy="{y}" r="3.5" class="dot"/>')


def coil_v(x, y, n=5, cl="w"):
    o.append(f'<path d="M{x} {y}' + "".join(" q10 6 0 12" for _ in range(n)) + f'" class="{cl}"/>')
    return y + 12 * n


def coil_h(x, y, n=5, cl="w"):
    o.append(f'<path d="M{x} {y}' + "".join(" q6 -10 12 0" for _ in range(n)) + f'" class="{cl}"/>')
    return x + 12 * n


def arrow_var(x, y):                       # variable-element arrow across a coil
    ln(x - 22, y + 26, x + 22, y - 26, "w")
    o.append(f'<polygon points="{x + 22},{y - 26} {x + 13},{y - 23} {x + 19},{y - 16}" fill="#111"/>')


def diode_v(x, y, down=True, col="#111", cl="w"):
    if down:
        o.append(f'<polygon points="{x - 11},{y} {x + 11},{y} {x},{y + 18}" fill="none" stroke="{col}" stroke-width="2"/>')
        ln(x - 11, y + 18, x + 11, y + 18, cl)
    else:
        o.append(f'<polygon points="{x - 11},{y + 18} {x + 11},{y + 18} {x},{y}" fill="none" stroke="{col}" stroke-width="2"/>')
        ln(x - 11, y, x + 11, y, cl)


def diode_h(x, y, right=True, col="#111", cl="w"):
    if right:
        o.append(f'<polygon points="{x},{y - 11} {x},{y + 11} {x + 18},{y}" fill="none" stroke="{col}" stroke-width="2"/>')
        ln(x + 18, y - 11, x + 18, y + 11, cl)
    else:
        o.append(f'<polygon points="{x + 18},{y - 11} {x + 18},{y + 11} {x},{y}" fill="none" stroke="{col}" stroke-width="2"/>')
        ln(x, y - 11, x, y + 11, cl)


def row(case_prefix):
    return [r for r in MD["rows"] if r["case"].startswith(case_prefix)][0]


def panel_a(ox):
    """magnetic dual: nodes a b c d f2 f3, ref 0 (bottom rail)."""
    REF = 600
    ln(ox + 20, REF, ox + 560, REF)
    tx(ox + 24, REF + 18, "REF = rotor (shaft); everything in (a) turns with the rotor", "m")
    xa, xd, xc, xb = ox + 110, ox + 230, ox + 350, ox + 470
    yt = 200
    # La: 0 -> a (left column, bottom to node a)
    for x in (xa, xd, xc, xb):
        dot(x, yt)
    tx(xa - 16, yt - 10, "a"); tx(xd - 4, yt - 10, "d"); tx(xc - 4, yt - 10, "c"); tx(xb + 6, yt - 10, "b")
    # La from ref up to a
    ln(xa, REF, xa, 470); yb = coil_v(xa, 400, 6); ln(xa, yb, xa, 470)
    ln(xa, 400, xa, yt); tx(xa - 64, 440, "La", "t", 'font-weight="bold"'); tx(xa - 78, 456, "fixed, 1.1 L̂", "m")
    # Lb from c down to ref
    ln(xc, yt, xc, 400); yb = coil_v(xc, 400, 6); ln(xc, yb, xc, REF)
    tx(xc + 16, 440, "Lb", "t", 'font-weight="bold"'); tx(xc + 16, 456, "fixed", "m")
    # L1: a -> d along the top (A utron group + AH top)
    ln(xa, yt, xa + 8, yt); xe = coil_h(xa + 8, yt, 4, "ut"); arrow_var((xa + 8 + xe) / 2, yt)
    ln(xe, yt, xe + 6, yt); xe2 = coil_h(xe + 6, yt, 2, "ah"); ln(xe2, yt, xd, yt)
    tx(xa + 6, yt - 42, "A utrons ×3", "tu", 'font-weight="bold"'); tx(xa + 6, yt - 28, "L1(θ)", "tu")
    tx(xe - 2, yt + 26, "AH top", "ta", 'font-weight="bold"')
    # L2: c -> b along the top (B utron group + AH bottom)
    ln(xc, yt, xc + 8, yt); xe = coil_h(xc + 8, yt, 4, "ut"); arrow_var((xc + 8 + xe) / 2, yt)
    ln(xe, yt, xe + 6, yt); xe2 = coil_h(xe + 6, yt, 2, "ah"); ln(xe2, yt, xb, yt)
    tx(xc + 6, yt - 42, "B utrons ×3", "tu", 'font-weight="bold"'); tx(xc + 6, yt - 28, "L2(θ), antiphase", "tu")
    tx(xe - 10, yt + 26, "AH bottom", "ta", 'font-weight="bold"')
    # D3*: 0 -> d (anode ref, cathode d): diode pointing up
    ln(xd, yt, xd, 330); diode_v(xd, 330, down=False); ln(xd, 348, xd, REF); tx(xd + 14, 344, "D3*")
    # D4*: 0 -> b: pointing up
    ln(xb, yt, xb, 330); diode_v(xb, 330, down=False); ln(xb, 348, xb, REF); tx(xb + 14, 344, "D4*")
    # Lp3 + D2*: c -> f3 -> d  (D2* anode c, cathode f3; Lp3 d -> f3)
    y2 = 270
    dot(xc, y2); ln(xc, y2, xc - 20, y2); diode_h(xc - 38, y2, right=False); ln(xc - 38, y2, xd + 40, y2)
    coil_h(xd + 4, y2, 3, "w"); ln(xd, y2, xd + 4, y2); dot(xd, y2)
    tx(xc - 44, y2 - 14, "D2*"); tx(xd + 4, y2 + 24, "Lp3", "m")
    # Lp2 + D1*: a -> f2 -> b   (Lp2 f2 -> a; D1* anode f2, cathode b), routed at y 520 under the ring
    y1 = 520
    dot(xa, y1) if False else None
    ln(xa + 0, 470, xa, 470)
    dot(xa, 380); ln(xa, 380, xa + 30, 380); ln(xa + 30, 380, xa + 30, y1)
    ln(xa + 30, y1, xa + 50, y1); xe = coil_h(xa + 50, y1, 3, "w"); ln(xe, y1, xb - 60, y1)
    diode_h(xb - 60, y1, right=True); ln(xb - 42, y1, xb + 30, y1); ln(xb + 30, y1, xb + 30, 290); ln(xb + 30, 290, xb, 290)
    dot(xb, 290); tx(xa + 50, y1 + 24, "Lp2", "m"); tx(xb - 64, y1 - 16, "D1*")
    tx(ox + 24, 120, "Diodes steer current between A and B: one group generates (L falling) while the other motors.", "m")
    # waveform inset
    r = row("SAT kappa 8 tau 0.118 s, AH r160")
    w = r["wave"]
    x0, y0, Wd, Hd = ox + 30, 652, 520, 86
    o.append(f'<rect x="{x0}" y="{y0}" width="{Wd}" height="{Hd}" fill="none" stroke="#bbb"/>')
    imax = max(max(abs(v) for v in w["iA"]), max(abs(v) for v in w["iB"]))
    T = max(w["t_ms"])
    for key, col in (("iA", "#c0392b"), ("iB", "#1f6fb2")):
        pts = " ".join(f"{x0 + Wd * t / T:.1f},{y0 + Hd - Hd * abs(i) / imax * 0.92:.1f}" for t, i in zip(w["t_ms"], w[key]))
        o.append(f'<polyline points="{pts}" fill="none" stroke="{col}" stroke-width="2"/>')
    tx(x0, y0 - 8, f"|i| over one cycle ({T:.1f} ms), 0 – {imax:.1f} A:", "m")
    tx(x0 + 250, y0 - 8, "A group + AH top", "tn"); tx(x0 + 380, y0 - 8, "B group + AH bottom", "tb")


def panel_b(ox):
    REF = 600
    ln(ox + 20, REF, ox + 560, REF)
    tx(ox + 24, REF + 18, "REF: shaft (rotor) ↔ stator reference through the shaft brush", "m")
    n1, n2, n3, n4 = ox + 120, ox + 230, ox + 340, ox + 450
    top = 200
    for x, nm in ((n1, "node 1"), (n2, "node 2"), (n3, "node 3"), (n4, "node 4")):
        dot(x, top); tx(x - 22, top - 10, nm, "m")
    # Ca, Cb
    ln(n1, top, n1 + 48, top); ln(n1 + 48, top - 14, n1 + 48, top + 14); ln(n1 + 58, top - 14, n1 + 58, top + 14); ln(n1 + 58, top, n2, top)
    tx(n1 + 40, top - 20, "Ca")
    ln(n4, top, n4 - 48, top); ln(n4 - 48, top - 14, n4 - 48, top + 14); ln(n4 - 58, top - 14, n4 - 58, top + 14); ln(n4 - 58, top, n3, top)
    tx(n4 - 66, top - 20, "Cb")
    # D1 / D2 to ref
    for x, dn in ((n2, "D1"), (n3, "D2")):
        ln(x, top, x, 470); diode_v(x, 470); ln(x, 488, x, REF); tx(x + 14, 484, dn)
    # D3, D4
    dot(n1, 250); ln(n1, 250, n3 - 30, 250); diode_h(n3 - 30, 250); ln(n3 - 12, 250, n3, 250); dot(n3, 250); tx(n3 - 34, 236, "D3")
    dot(n4, 300); ln(n4, 300, n2 + 30, 300); diode_h(n2 + 12, 300, right=False); ln(n2 + 12, 300, n2, 300); dot(n2, 300); tx(n2 + 14, 286, "D4")
    # C1 / C2 (stator vane -> rotor vane) then the cones on the rotor side
    for x, cn, cone, rail in ((n1, "C1(θ)", "cone A", "R-A"), (n4, "C2(θ)", "cone B", "R-B")):
        ln(x, top, x, 340)
        ln(x - 18, 340, x + 18, 340); ln(x - 18, 350, x + 18, 350)
        ln(x - 26, 364, x + 26, 328)
        ln(x, 350, x, 400); dot(x, 400); tx(x + 10, 404, rail, "m")
        yb = coil_v(x, 410, 5, "ah"); ln(x, 400, x, 410, "w"); ln(x, yb, x, REF)
        tx(x + 16, 440, cone, "ta", 'font-weight="bold"'); tx(x + 16, 456, "32 t", "m")
        tx(x + 24, 344, cn)
    tx(n1 - 100, 380, "stator ↑", "m"); tx(n1 - 100, 396, "rotor ↓", "m")
    ln(ox + 20, 375, ox + 560, 375, "sep")
    # limiters node 1 / node 4 -> ref: avalanche clamp OR gap + quench diode
    for x, xl, nm in ((n1, ox + 40, "1"), (n4, ox + 530, "4")):
        dot(x, 225); ln(x, 225, xl, 225, "lim"); ln(xl, 225, xl, 470, "lim")
        o.append(f'<circle cx="{xl}" cy="{482}" r="7" fill="none" stroke="#7d3c98" stroke-width="2"/>')
        o.append(f'<circle cx="{xl}" cy="{500}" r="7" fill="none" stroke="#7d3c98" stroke-width="2"/>')
        ln(xl, 470, xl, 475, "lim"); ln(xl, 507, xl, 520, "lim")
        diode_v(xl, 540, down=False, col="#7d3c98", cl="lim"); ln(xl, 520, xl, 540, "lim"); ln(xl, 558, xl, REF, "lim")
    tx(ox + 24, 120, "Limiter at nodes 1 / 4 (purple): an avalanche clamp (diodes only) OR a 20 kV spark gap", "m")
    tx(ox + 24, 136, "with a quench diode (drawn), which dumps C1 / C2 through its cone.", "m")
    d = [r for r in BD["rows"] if r["mode"] == "diodes"][0]
    g = [r for r in BD["rows"] if r["mode"] == "dump" and "steps" not in r and "reltol" not in r][0]
    x0, y0 = ox + 30, 640
    tx(x0, y0 + 14, f"diodes only: cone {d['I_cone_rms_mA']:.1f} mA rms ({d['AT_pk']:.2f} A-turns peak) — negligible", "m")
    tx(x0, y0 + 32, f"spark-gap dump: cone {g['I_cone_pk_A']:.0f} A peak, {g['AT_pk']:.0f} A-turns, ~{g['dumps_per_s_A']:.0f} dumps/s per side,", "m")
    tx(x0, y0 + 50, f"~{g['E_per_dump_mJ']:.0f} mJ each, ring {g['f_ring_analytic_MHz']:.1f} MHz; pump belt {g['P_belt_W']:.1f} W at 600 rpm relative", "m")


def main():
    W, H = 1200, 900
    o.append(f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}" '
             'font-family="DejaVu Sans, Arial, sans-serif" font-size="13">')
    o.append("<title>Hub drive: two pumps</title>")
    o.append(f'<rect width="{W}" height="{H}" fill="#ffffff"/>')
    o.append("""<style>
    .w{stroke:#111;stroke-width:2;fill:none} .ut{stroke:#1f6fb2;stroke-width:2.4;fill:none} .ah{stroke:#c0392b;stroke-width:2.6;fill:none}
    .lim{stroke:#7d3c98;stroke-width:2.2;fill:none} .sep{stroke:#999;stroke-width:1;stroke-dasharray:6 4}
    .t{fill:#111} .tu{fill:#1f6fb2} .ta{fill:#c0392b} .tn{fill:#c0392b;font-size:11.5px} .tb{fill:#1f6fb2;font-size:11.5px}
    .m{fill:#555;font-size:11.5px} .h{font-size:16px;font-weight:bold;fill:#111} .h2{font-size:14px;font-weight:bold;fill:#111}
    .box{stroke:#999;stroke-dasharray:5 4;fill:none} .dot{fill:#111}
  </style>""")
    tx(20, 28, "Central cavity driven by two pumps — rotor and stator geared 1 : −1 (300 rpm each, 600 rpm relative)", "h")
    tx(20, 48, "(a) AH pair ← magnetic dual doubler on the rotor (wound utrons vs the stator's toothed C-EM iron) · "
               "(b) bicone ← electrostatic diode doubler. Only diodes switch; the gap in (b) is the optional dump test.", "m")
    for ox, title in ((20, "(a) MAGNETIC doubler → AH pair (pulsed, A / B in antiphase)"),
                      (620, "(b) ELECTROSTATIC doubler → bicone cones")):
        o.append(f'<rect x="{ox}" y="70" width="560" height="680" class="box"/>')
        tx(ox + 10, 92, title, "h2")
    panel_a(20)
    panel_b(620)
    r = row("SAT kappa 8 tau 0.118 s, AH r160")
    notes = [
        f"(a) design point: L ratio {r['kappa']:g} (toothed poles), τ = L/R {r['tau']:g} s, 3 coils × 1150 t per group, AH rewound to 160 t: "
        f"utron current {abs(r['I1_min']):.1f}–{r['I1_pk']:.1f} A, AH {r['AH_AT_min']:.0f}–{r['AH_AT_pk']:.0f} A-turns (rod limit ≈ 600).",
        f"     Growth stops at iron saturation (B {r['B_core_pk_T']:.2f} T). Belt {r['P_belt_W']:.0f} W, copper {r['P_cu_utron_W'] + r['P_cu_fixed_W']:.0f} W on the rotor "
        "(currents scale with the core's saturation flux, power with its square).",
        "     Threshold: L ratio ≳ 3 and τ ≳ 0.08 s at 60 Hz; dual nodes carry 10 nF + 1 kΩ snubbers (winding capacitance) [IR].",
        "(b) cones sit on the rotor side of C1 / C2 (R-A / R-B → cone → shaft): no rotating contact; the ES nodes live on the stator vanes.",
        "Numbers: sim/magnetic_doubler_results.json, sim/bicone_drive_results.json · findings: sim/hub-drive-findings.md · generator: docs/make_schematic_hub.py",
    ]
    y = 775
    for s in notes:
        tx(20, y, s, "m"); y += 18
    o.append("</svg>")
    open(os.path.join(HERE, "schematic-hub-drive.svg"), "w").write("\n".join(o) + "\n")


if __name__ == "__main__":
    main()
