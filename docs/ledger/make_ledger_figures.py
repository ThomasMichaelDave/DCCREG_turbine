"""docs/ledger/make_ledger_figures.py -- the design ledger's own figure: docs/ledger/figures/architecture.{svg,png}, the
locked machine in one diagram. It shows the drive and the two counter-rotating bodies, the magnetic and the
electrostatic pumps, and the hub with the two fields they hold at its centre; where the belt's power goes; and the
reference. Numbers: the records named in docs/ledger/DCCREG-design-ledger.md.
Usage: python3 docs/ledger/make_ledger_figures.py   (the PNG needs playwright + chromium)
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
DOCS = os.path.dirname(HERE)
sys.path.insert(0, DOCS)
import make_schematic_rotor as SR  # noqa: E402  (its SVG primitives write into SR.o)
import make_rings_supply_schematic as RS  # noqa: E402  (the schematics' shared style sheet)

OUT = os.path.join(HERE, "figures", "architecture")
o = SR.o
W, H = 1440, 872


def arrow(x1, y1, x2, y2, col="#1d3f5e", w=2.2, label=None, dy=-8, anchor="middle"):
    """a straight arrow from (x1, y1) to (x2, y2), with an optional label above its middle."""
    import math
    a = math.atan2(y2 - y1, x2 - x1)
    xb, yb = x2 - 12 * math.cos(a), y2 - 12 * math.sin(a)
    o.append(f'<line x1="{x1:.1f}" y1="{y1:.1f}" x2="{xb:.1f}" y2="{yb:.1f}" stroke="{col}" stroke-width="{w}"/>')
    p = [(x2, y2), (xb - 6 * math.sin(a), yb + 6 * math.cos(a)), (xb + 6 * math.sin(a), yb - 6 * math.cos(a))]
    o.append('<polygon points="' + " ".join(f"{x:.1f},{y:.1f}" for x, y in p) + f'" fill="{col}"/>')
    if label:
        SR.tx(0.5 * (x1 + x2), 0.5 * (y1 + y2) + dy, label, "ms", anchor)


def block(x, y, w, h, title, lines, fill, stroke, tcol="#111"):
    o.append(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="6" fill="{fill}" stroke="{stroke}" stroke-width="1.4"/>')
    SR.tx(x + 12, y + 22, title, "tk", "start", f'style="fill:{tcol}"')
    for i, s in enumerate(lines):
        SR.tx(x + 12, y + 42 + 16 * i, s, "tv")


def main():
    o.clear()
    o.append(f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}" '
             'font-family="DejaVu Sans, Arial, sans-serif" font-size="13">')
    o.append("<title>The locked machine</title>")
    o.append(f'<rect width="{W}" height="{H}" fill="#ffffff"/>')
    o.append(RS.style_block())
    SR.tx(20, 32, "DCCREG turbine, the locked design (2026-10-09): what drives what", "h")
    SR.tx(20, 54, "Two counter-rotating bodies on one shaft; on each shaft half a magnetic pump and an electrostatic pump; "
                  "both pumps hold a static field at the hub's centre. Side A below, side B above, mirror images.", "m")
    MAG, MAGS = "#eef3f8", "#9fb3c8"
    ES, ESS = "#f3f0e6", "#b9ad8a"
    # the drive and the bodies
    block(20, 90, 230, 150, "DRIVE (the frame)", ["drive motor and belt", "reversing gear 1 : −1", "end bearings, housings",
                                                  "(a first cut, PROPOSED)"], "#f6f6f4", "#999")
    block(20, 300, 230, 132, "ROTOR, +600 rpm", ["shaft (REF), sleeve, hub", "utrons, rotor vanes", "Ca / Cb, D1–D4, Z1 / Z4",
                                                "both pumps' circuits"], "#ffffff", "#5d6670")
    block(20, 470, 230, 116, "COUNTER-ROTOR, −600 rpm", ["stator cage, stator vanes", "(REF via one inner bearing)",
                                                        "SiFe bridges, no wires"], "#ffffff", "#5d6670")
    arrow(135, 240, 135, 298, label="")
    SR.tx(146, 274, "1200 rpm relative", "ms")
    o.append('<line x1="135" y1="432" x2="135" y2="468" stroke="#5d6670" stroke-width="1.6" stroke-dasharray="4 3"/>')
    SR.tx(146, 455, "four inner bearings", "ms")
    # the magnetic pump (upper row)
    SR.tx(300, 110, "THE MAGNETIC PUMP: a reluctance machine, the planar dual of the electrostatic doubler", "zh")
    block(300, 124, 250, 150, "Utrons × bridges", ["3 wound utrons per side (rotor)", "6 SiFe bridges per side (counter)",
                                                   "gap 0.5 mm, 120 Hz", "L 81 ↔ 9.4 mH (3-D: 83 ↔ 12.4)"], MAG, MAGS)
    block(590, 124, 250, 150, "Magnetic dual doubler", ["groups A / B in antiphase", "La / Lb 0.146 H, D1*–D4*",
                                                        "clamp: the NiFe neck saturates", "kick start; z 1.14–1.21"],
          MAG, MAGS)
    block(880, 124, 220, 150, "AH coil pair", ["160 turns, one per branch", "22 mF bypass each (PROPOSED)",
                                               "300 A-turns ±3 % (3-D: 221–245)", "belt 18.1 W + 1.25 W iron"],
          MAG, MAGS)
    arrow(550, 199, 590, 199)
    arrow(840, 199, 880, 199)
    # the electrostatic pump (lower row)
    SR.tx(300, 352, "THE ELECTROSTATIC PUMP: the de Queiroz diode doubler, HV side on the rotor", "zh")
    block(300, 366, 250, 166, "Air vane stack C1 / C2", ["6 + 6 vanes per side, Al 3 mm", "6 mm gaps, R1.5 full rounds",
                                                         "rotor vanes = nodes 1 / 4", "stator vanes = REF",
                                                         "55 ↔ 410 pF, 120 Hz"], ES, ESS)
    block(590, 366, 250, 166, "Diode doubler", ["Ca / Cb 451 pF on the rotor", "D1–D4; a seed (≥ 17–260 V) starts it",
                                                "clamps Z1 / Z4 at 13.1 kV", "nodes 1 / 4: −13.2 ↔ −5.7 kV",
                                                "z 1.31 bare; belt 2.14 W"], ES, ESS)
    block(880, 366, 220, 166, "Two mirrored chains", ["Cockcroft-Walton, 2 stages", "each, from the shaft",
                                                      "node 1 → ring A −15.0 kV", "node 4 → ring B +15.0 kV",
                                                      "8 diodes, 8 × 100 pF"], ES, ESS)
    arrow(550, 449, 590, 449)
    arrow(840, 449, 880, 449)
    # the hub
    o.append('<rect x="1140" y="96" width="282" height="532" rx="8" fill="#fbfbfa" stroke="#1d3f5e" stroke-width="1.6"/>')
    SR.tx(1281, 122, "THE HUB (rotor)", "zh", "middle")
    cx, cy, rv = 1281, 330, 78
    o.append(f'<circle cx="{cx}" cy="{cy}" r="{rv}" class="glass"/>')
    import math
    for top, col in ((1, "#1f6fb2"), (-1, "#c0392b")):
        for side in (-1, 1):
            pts = [(cx + side * (rv + 3) * math.sin(math.radians(t)), cy - top * (rv + 3) * math.cos(math.radians(t)))
                   for t in [26.25 + i * (55.71 - 26.25) / 23 for i in range(24)]]
            o.append('<polyline points="' + " ".join(f"{x:.1f},{y:.1f}" for x, y in pts) +
                     f'" fill="none" stroke="{col}" stroke-width="6" stroke-linecap="round"/>')
    hw = rv * 11.45 / 25.0
    for s in (1, -1):
        y0, y1 = cy - s * rv * 30.7 / 25.0, cy - s * rv * 46.0 / 25.0
        a, b = sorted((y0, y1))
        o.append(f'<rect x="{cx - hw:.1f}" y="{a:.1f}" width="{2 * hw:.1f}" height="{b - a:.1f}" fill="#9aa3ad" '
                 'stroke="#5d6670" stroke-width="1"/>')
    SR.ln(cx, cy - 26, cx, cy + 12, "ef")
    o.append(f'<polygon points="{cx},{cy + 24} {cx - 6},{cy + 12} {cx + 6},{cy + 12}" fill="#1d3f5e"/>')
    SR.tx(cx + 10, cy + 4, "E", "te", "start")
    SR.tx(1154, 150, "AH cores (MnZn) on the axis", "ms")
    SR.tx(1154, 166, "ring B +15.0 kV (blue), A −15.0 kV (red)", "ms")
    SR.tx(1154, 498, "50 mm borosilicate sphere, vacuum,", "ms")
    SR.tx(1154, 514, "1.5 mm wall; PEEK retainer + 0.5 mm gel,", "ms")
    SR.tx(1154, 530, "G10 coupler; flanges at |z| 72–80 mm", "ms")
    SR.tx(1154, 560, "at the null:", "tk")
    SR.tx(1154, 578, "B: the AH's steady cusp (the null)", "tv")
    SR.tx(1154, 596, "E: 7.62 kV/cm, B to A, 2.57 Pa (8.2 settled)", "tv")
    SR.tx(1154, 614, "(ripple 0.19 %, no sign change)", "ms")
    arrow(1100, 199, 1196, 262)
    arrow(1100, 449, 1196, 398)
    # the power and the reference
    o.append('<rect x="20" y="648" width="1402" height="186" rx="6" fill="#ffffff" stroke="#c3c2b7" stroke-width="1"/>')
    SR.tx(36, 674, "WHERE THE BELT'S POWER GOES (at 1200 rpm relative)", "zh")
    rows = [
        ("magnetic pump", "18.1 W belt + 1.25 W iron: utron copper 13.5 W, AH coils 2.0 W, diodes 2.0 W, La / Lb 0.7 W; "
                          "the bypass 8 mW; with the 3-D utrons 10.2–12.3 W belt"),
        ("electrostatic pump", "2.14 W belt, all into the clamps Z1 / Z4 (1.07 W each); the rings' leakage 4.5 mW at "
                               "100 GΩ per ring"),
        ("the mechanics", "windage about 12 W and the bearings 5 W, so about 39 W in all from the belt; the gear puts "
                          "the same torque on both bodies, the frame takes twice it"),
        ("the products", "two static fields at the hub's centre: the AH's cusp (300 A-turns per coil; 221–245 with the "
                         "3-D utrons) and the DC field 7.62 kV/cm (8.2 settled); no electrical output is drawn"),
        ("the reference", "the shaft (REF); the counter-rotor's stator vanes reach it through one inner bearing "
                          "(0.41 mA rms, pure AC)"),
        ("not yet built in", "the gear and belt, La / Lb and the HV parts are not in the 3-D model; the record's stacks, "
                             "hub, AH and rings are (see the ledger's register)"),
    ]
    SR.table(36, 702, rows, w_key=150, dy=24)
    SR.tx(20, 858, "Sources: docs/ledger/DCCREG-design-ledger.md · generator: docs/ledger/make_ledger_figures.py", "n")
    o.append("</svg>")
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    svg = OUT + ".svg"
    open(svg, "w").write("\n".join(o) + "\n")
    from playwright.sync_api import sync_playwright
    png = OUT + ".png"
    with sync_playwright() as p:
        b = p.chromium.launch(executable_path=os.environ.get("CHROMIUM", "/opt/pw-browsers/chromium"))
        pg = b.new_page(viewport={"width": W, "height": H}, device_scale_factor=2)
        pg.set_content(f'<html><body style="margin:0">{open(svg).read()}</body></html>')
        pg.screenshot(path=png, clip=dict(x=0, y=0, width=W, height=H))
        b.close()
    print(svg, png)


if __name__ == "__main__":
    main()
