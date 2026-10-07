"""docs/make_schematic_switchless.py -- writes docs/schematic-diode-core-switchless.svg: the bare de Queiroz diode core
with the C-EMs connected WITHOUT switches, two placements side by side (sim/switchless_cem.py):
(a) LEG: coil strings in series with the varicaps C1 / C2; (b) BUS: coil strings in series with D5 / D6 into C_bus.
Polarity as drawn = the engine's negative mode (all nodes <= 0); D1 2->ref, D2 3->ref, D3 1->3, D4 4->2.
Usage: python3 docs/make_schematic_switchless.py  (the numbers in the notes come from sim/switchless_cem_results.json)
"""
import json
import os

HERE = os.path.dirname(os.path.abspath(__file__))
RES = json.load(open(os.path.join(HERE, "..", "sim", "switchless_cem_results.json")))
REF = 670
o = []


def ln(x1, y1, x2, y2, cl="w"):
    o.append(f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" class="{cl}"/>')


def tx(x, y, s, cl="t", extra=""):
    o.append(f'<text x="{x}" y="{y}" class="{cl}" {extra}>{s}</text>')


def dot(x, y):
    o.append(f'<circle cx="{x}" cy="{y}" r="3.5" class="dot"/>')


def diode_v(x, y, down=True, cl="w", col="#111", zener=False):
    """vertical diode, anode on top if down (triangle points down to the cathode bar at y+20)."""
    if down:
        o.append(f'<polygon points="{x - 12},{y} {x + 12},{y} {x},{y + 20}" fill="none" stroke="{col}" stroke-width="2"/>')
        by = y + 20
    else:
        o.append(f'<polygon points="{x - 12},{y + 20} {x + 12},{y + 20} {x},{y}" fill="none" stroke="{col}" stroke-width="2"/>')
        by = y
    ln(x - 12, by, x + 12, by, cl)
    if zener:
        ln(x - 12, by, x - 16, by - 5, cl); ln(x + 12, by, x + 16, by + 5, cl)


def diode_h(x, y, right=True, cl="w", col="#111"):
    """horizontal diode from x to x+20; right: anode left, cathode bar at x+20."""
    if right:
        o.append(f'<polygon points="{x},{y - 12} {x},{y + 12} {x + 20},{y}" fill="none" stroke="{col}" stroke-width="2"/>')
        ln(x + 20, y - 12, x + 20, y + 12, cl)
    else:
        o.append(f'<polygon points="{x + 20},{y - 12} {x + 20},{y + 12} {x},{y}" fill="none" stroke="{col}" stroke-width="2"/>')
        ln(x, y - 12, x, y + 12, cl)


def cap_v(x, y, cl="w", var=False, col="#111"):
    ln(x - 20, y, x + 20, y, cl); ln(x - 20, y + 12, x + 20, y + 12, cl)
    if var:
        ln(x - 28, y + 25, x + 28, y - 13, cl)
        o.append(f'<polygon points="{x + 28},{y - 13} {x + 18},{y - 11} {x + 23},{y - 4}" fill="{col}"/>')


def cap_h(x, y, cl="w"):
    ln(x, y - 16, x, y + 16, cl); ln(x + 12, y - 16, x + 12, y + 16, cl)


def coil_v(x, y, n=5, cl="cm"):
    d = f"M{x} {y}" + "".join(" q10 6 0 12" for _ in range(n))
    o.append(f'<path d="{d}" class="{cl}"/>')
    return y + 12 * n


def core(ox, leg):
    """the core in a panel at x offset ox. Node columns n1 n2 n3 n4; returns their x."""
    n1, n2, n3, n4 = ox + 110, ox + 220, ox + 330, ox + 440
    top = 230
    # node 1 column
    ln(n1, top, n1, 380)
    if leg:
        yb = coil_v(n1, 380, 6)
        tx(n1 + 16, 400, "C-EM A", "tc", 'font-weight="bold"'); tx(n1 + 16, 416, "6 coils in", "m"); tx(n1 + 16, 430, "series + PM", "m")
        ln(n1, yb, n1, 480, "cm")
        tx(n1 - 92, 470, "node 1v", "m")
    else:
        ln(n1, 380, n1, 480)
    cap_v(n1, 480, var=True); ln(n1, 492, n1, REF); tx(n1 - 60, 500, "C1(θ)", "t")
    # node 4 column
    ln(n4, top, n4, 380)
    if leg:
        yb = coil_v(n4, 380, 6)
        tx(n4 - 74, 400, "C-EM B", "tc", 'font-weight="bold"'); tx(n4 - 74, 416, "6 coils", "m"); tx(n4 - 74, 430, "+ PM", "m")
        ln(n4, yb, n4, 480, "cm")
    else:
        ln(n4, 380, n4, 480)
    cap_v(n4, 480, var=True); ln(n4, 492, n4, REF); tx(n4 - 84, 500, "C2(θ)", "t")
    dot(n1, top); dot(n4, top)
    tx(n1 - 56, top + 4, "node 1"); tx(n4 + 8, top + 18, "node 4")
    # Ca / Cb at y 280
    y = 280
    dot(n1, y); ln(n1, y, n1 + 49, y); cap_h(n1 + 49, y); ln(n1 + 61, y, n2, y); tx(n1 + 42, y - 22, "Ca")
    dot(n4, y); ln(n4, y, n4 - 49, y); cap_h(n4 - 61, y); ln(n4 - 61, y, n3, y); tx(n4 - 68, y - 22, "Cb")
    # node 2 / node 3 columns with D1 / D2 to ref
    for x, nm, dn in ((n2, "node 2", "D1"), (n3, "node 3", "D2")):
        dot(x, y); ln(x, y, x, 560); diode_v(x, 560); ln(x, 580, x, REF); tx(x + 16, 576, dn)
        tx(x + 6, y - 8, nm, "m")
    # D3 node1 -> node3 at y 330 (crosses node 2 without a junction)
    y3 = 330
    dot(n1, y3); ln(n1, y3, n3 - 40, y3); diode_h(n3 - 40, y3, right=True); ln(n3 - 20, y3, n3, y3); dot(n3, y3)
    tx(n3 - 44, y3 - 16, "D3")
    # D4 node4 -> node2 at y 450 (crosses node 3 without a junction)
    y4 = 450
    dot(n4, y4) if not leg else None
    if leg:
        # D4 leaves node 4 above the coil string: route at y 360
        y4 = 360
        dot(n4, y4)
    ln(n4, y4, n2 + 40, y4); diode_h(n2 + 20, y4, right=False); ln(n2 + 20, y4, n2, y4); dot(n2, y4)
    tx(n2 + 22, y4 - 16, "D4")
    # clamps (avalanche strings) node 1 / node 4 -> ref
    for xn, xc, yt in ((n1, ox + 40, 250), (n4, ox + 490, 250)):
        dot(xn, yt); ln(xn, yt, xc, yt, "cl"); ln(xc, yt, xc, 590, "cl")
        diode_v(xc, 590, down=True, cl="cl", col="#7d3c98", zener=True); ln(xc, 610, xc, REF, "cl")
        dot(xc, REF)
    tx(ox + 22, 640, "Z1", "tz"); tx(ox + 500, 640, "Z4", "tz")
    for x in (n1, n2, n3, n4):
        dot(x, REF)
    return n1, n2, n3, n4


def rows(place):
    return [r for r in RES["rows"] if r.get("place") == place and "P_mech_W" in r and not r.get("aborted")]


def best(place, m=6):
    rr = [r for r in rows(place) if r.get("m", 6) == m]
    return max(rr, key=lambda r: r["P_mech_W"]) if rr else None


def main():
    W, H = 1200, 900
    o.append(f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}" '
             'font-family="DejaVu Sans, Arial, sans-serif" font-size="13">')
    o.append("<title>Switchless C-EM placements</title>")
    o.append(f'<rect width="{W}" height="{H}" fill="#ffffff"/>')
    o.append("""<style>
    .w{stroke:#111;stroke-width:2;fill:none} .new{stroke:#c0392b;stroke-width:2.4;fill:none}
    .cm{stroke:#1f6fb2;stroke-width:2.4;fill:none} .cl{stroke:#7d3c98;stroke-width:2.2;fill:none}
    .t{fill:#111} .tn{fill:#c0392b} .tc{fill:#1f6fb2} .tz{fill:#7d3c98} .m{fill:#555;font-size:11.5px}
    .h{font-size:16px;font-weight:bold;fill:#111} .h2{font-size:14px;font-weight:bold;fill:#111}
    .box{stroke:#999;stroke-dasharray:5 4;fill:none} .dot{fill:#111}
  </style>""")
    tx(20, 28, "Diode machine (de Queiroz core, no flying bucket): C-EMs connected WITHOUT switches — two placements", "h")
    tx(20, 48, "black = core (solveDoubler4 netlist: D1 2→ref, D2 3→ref, D3 1→3, D4 4→2, anode→cathode) · blue = C-EM strings (PM utrons) · "
               "purple = avalanche clamp · red = bus parts", "m")
    tx(20, 64, "Negative polarity (all nodes ≤ 0). No transistor, thyristor, spark gap, commutator or controller anywhere: every one-way "
               "element is a diode. Wires that cross without a dot are not connected.", "m")
    for ox, leg, title in ((20, True, "(a) LEG — each string in series with its varicap"),
                           (620, False, "(b) BUS — each string in series with D5 / D6 into C_bus")):
        o.append(f'<rect x="{ox}" y="80" width="560" height="620" class="box"/>')
        tx(ox + 10, 100, title, "h2")
        ln(ox + 10, REF, ox + 550, REF)
        tx(ox + 14, REF + 20, "REF = rotor rail R-A / R-B", "m")
        n1, n2, n3, n4 = core(ox, leg)
        if not leg:
            yb = 130
            ln(n1, yb, ox + 535, yb, "new"); tx(ox + 150, yb - 8, "DC BUS (−V)", "tn", 'font-weight="bold"')
            tx(ox + 290, yb - 8, "C_bus 10 nF ∥ R_bleed 10 GΩ to REF", "m")
            for x, dn, cn in ((n1, "D5", "C-EM A"), (n4, "D6", "C-EM B")):
                dot(x, yb)
                o.append(f'<rect x="{x - 7}" y="{yb + 6}" width="14" height="22" fill="none" stroke="#c0392b" stroke-width="2"/>')
                ln(x, yb, x, yb + 6, "new"); ln(x, yb + 28, x, yb + 36, "new")
                tx(x + 12, yb + 22, "R_s", "tn")
                diode_v(x, yb + 36, down=True, cl="new", col="#c0392b"); tx(x + 16, yb + 52, dn, "tn")
                ln(x, yb + 56, x, yb + 60, "new")
                yc = coil_v(x, yb + 60, 3)
                tx(x + 16, yb + 80, cn, "tc")
                ln(x, yc, x, 230, "cm")
            xb = ox + 535
            ln(xb, yb, xb, 400, "new"); cap_v(xb, 400, cl="new"); ln(xb, 412, xb, REF, "new"); dot(xb, REF)
            tx(xb - 60, 396, "C_bus", "tn")

            tx(ox + 250, 168, "R_s 22 kΩ; snubber 10 MΩ", "m"); tx(ox + 250, 182, "across each C-EM string", "m")
    a = [r for r in rows("leg") if r.get("k") == 20.0 and r.get("phi_deg", 0) == 0 and r.get("m", 6) == 6 and "no clamp" not in r["case"]][0]
    b = best("bus")
    note = []
    if a:
        note.append(f"(a) design point k {a['k']:g} (≈ {a['k'] * 1846:.0f} turns per coil, string EMF {a['E_peak_V'] / 1e3:.1f} kV pk), "
                    f"flux extreme at plate alignment: {a['P_mech_W']:.2f} W to the shaft, {a['T_motor_mNm']:.0f} mN·m; belt "
                    f"{a['P_belt_W']:.1f} W, clamp {a['P_clamp_W']:.1f} W, copper {a['P_cu_W']:.2f} W.")
        note.append(f"     Stator: pump reaction {a['T_pump_mNm']:.0f} mN·m + drag {RES['T_drag_mNm']:.1f} mN·m → net "
                    f"{a['T_net_mNm']:.0f} mN·m (dragged along, as for every pump-fed motor). k 10: 2.1 W; k 40: copper and clamp take over.")
    if b:
        note.append(f"(b) bus, k 1: {b['T_motor_mNm']:.2f} mN·m (once C_bus is charged only the 2 µA bleed flows through D5 / D6); "
                    "k 20: −99 mN·m, a brake (the PM EMF drives 3.1 W into the snubbers); at two phases the pump collapses.")
        note.append("     Without switches a DC bus cannot turn the coils (constant current, periodic flux → zero average torque) [OC].")
    note += ["Z1 / Z4: avalanche-diode strings (BV 20 kV, soft knee, ~100 kΩ): they set the operating voltage and take the surplus "
             "the coils don't.",
             "     Without them the pump runs away at every rewind (coil power ∝ V, pump surplus ∝ V²).",
             "Coil timing comes from the plates alone: each coil must see 6 flux periods per rev (one per pump cycle), so 6 PM "
             "utrons per side.",
             "     The present 3 utrons per side give ≈ 0 average torque. Each string floats at node potential: coil insulation ≥ 20 kV.",
             "ngspice, tube defaults at 300 rpm: near-ideal diodes, cosine varicaps, PM swing 0.27 mWb per coil [RH, gate G-SWING open].",
             "     Numbers: sim/switchless_cem_results.json · findings: sim/switchless-cem-findings.md · generator: docs/make_schematic_switchless.py."]
    y = 730
    for s in note:
        tx(20, y, s, "m"); y += 18
    o.append("</svg>")
    open(os.path.join(HERE, "schematic-diode-core-switchless.svg"), "w").write("\n".join(o) + "\n")


if __name__ == "__main__":
    main()
