"""rebuild/s0_base/make_schematic.py -- draws the Stage 0 base schematic, de Queiroz's Fig. 1, from s0_base.TOPOLOGY,
with its numbers from s0_base_results.json. Writes rebuild/s0_base/schematic-s0-base.svg.
Layout as the paper draws it (Fig. 1): D3 and D4 across the top, their leads crossing between nodes 2 and 3.
Usage: python3 rebuild/s0_base/make_schematic.py  (run s0_base.py first)
"""
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from s0_base import TOPOLOGY  # noqa: E402

RES = json.load(open(os.path.join(HERE, "s0_base_results.json")))
o = []
X = {"1": 170, "2": 290, "3": 390, "4": 510}      # node columns
YN, YT, YG = 250, 130, 400                         # node row, top row, REF


def ln(x1, y1, x2, y2, cl="w"):
    o.append(f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" class="{cl}"/>')


def tx(x, y, s, cl="t", extra=""):
    o.append(f'<text x="{x}" y="{y}" class="{cl}" {extra}>{s}</text>')


def dot(x, y):
    o.append(f'<circle cx="{x}" cy="{y}" r="4" class="dot"/>')


def diode_up(x, y):
    """vertical diode, anode at the bottom (y + 20), cathode bar on top (y)."""
    o.append(f'<polygon points="{x - 12},{y + 20} {x + 12},{y + 20} {x},{y}" class="w"/>')
    ln(x - 12, y, x + 12, y)


def diode_h(x, y, right):
    """horizontal diode from x to x + 20; right: anode left, cathode bar at x + 20."""
    if right:
        o.append(f'<polygon points="{x},{y - 12} {x},{y + 12} {x + 20},{y}" class="w"/>')
        ln(x + 20, y - 12, x + 20, y + 12)
    else:
        o.append(f'<polygon points="{x + 20},{y - 12} {x + 20},{y + 12} {x},{y}" class="w"/>')
        ln(x, y - 12, x, y + 12)


def cap_h(x, y):
    ln(x, y - 16, x, y + 16); ln(x + 12, y - 16, x + 12, y + 16)


def cap_v_var(x, y):
    ln(x - 20, y, x + 20, y); ln(x - 20, y + 12, x + 20, y + 12)
    ln(x - 26, y + 26, x + 24, y - 14)
    o.append(f'<polygon points="{x + 26},{y - 16} {x + 14},{y - 13} {x + 21},{y - 5}" class="dot"/>')


def ground(x, y):
    ln(x - 14, y, x + 14, y); ln(x - 9, y + 5, x + 9, y + 5); ln(x - 4, y + 10, x + 4, y + 10)


def main():
    T = TOPOLOGY
    # the drawing hard-codes Fig. 1's layout; refuse to draw a different topology [OC check]
    assert T["diodes"] == {"D1": ("0", "2"), "D2": ("0", "3"), "D3": ("3", "1"), "D4": ("2", "4")}
    assert {k: c["nodes"] for k, c in T["capacitors"].items()} == {
        "C1": ("1", "0"), "C2": ("4", "0"), "Ca": ("1", "2"), "Cb": ("3", "4")}
    W, H = 1000, 520
    o.append(f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}" '
             'font-family="DejaVu Sans, Arial, sans-serif" font-size="14">')
    o.append("<title>S0 base schematic</title>")
    o.append(f'<rect width="{W}" height="{H}" fill="#ffffff"/>')
    o.append("<style>.w{stroke:#111;stroke-width:2;fill:none} .t{fill:#111} .m{fill:#555;font-size:12px}"
             " .h{font-size:17px;font-weight:bold;fill:#111} .dot{fill:#111} .n{fill:#1f6fb2;font-weight:bold}</style>")
    tx(20, 30, "Stage 0 — the base schematic: de Queiroz's symmetrical unipolar generator (his Fig. 1)", "h")
    tx(20, 50, "Positive polarity as printed. Diodes anode → cathode. Leads that cross without a dot are not "
               "connected.", "m")
    x1, x2, x3, x4 = X["1"], X["2"], X["3"], X["4"]
    # node row: Ca 1-2, Cb 3-4
    ln(x1, YN, x1 + 54, YN); cap_h(x1 + 54, YN); ln(x1 + 66, YN, x2, YN); tx(x1 + 48, YN - 24, "Ca")
    ln(x3, YN, x3 + 54, YN); cap_h(x3 + 54, YN); ln(x3 + 66, YN, x4, YN); tx(x3 + 48, YN - 24, "Cb")
    # top row: D3 from node 3 to node 1 (pointing left), D4 from node 2 to node 4 (pointing right); leads cross
    ln(x1, YN, x1, YT); ln(x1, YT, x1 + 50, YT); diode_h(x1 + 50, YT, right=False); ln(x1 + 70, YT, x2 - 10, YT)
    ln(x2 - 10, YT, x3, YN - 40); ln(x3, YN - 40, x3, YN)
    tx(x1 + 50, YT - 18, "D3")
    ln(x2, YN, x2, YN - 40); ln(x2, YN - 40, x3 + 10, YT); ln(x3 + 10, YT, x4 - 70, YT)
    diode_h(x4 - 70, YT, right=True); ln(x4 - 50, YT, x4, YT); ln(x4, YT, x4, YN)
    tx(x4 - 70, YT - 18, "D4")
    # verticals: C1, D1, D2, C2 to REF
    for x, lab in ((x1, "C1"), (x4, "C2")):
        ln(x, YN, x, 300); cap_v_var(x, 300); ln(x, 312, x, YG); ground(x, YG)
        tx(x - 70 if x == x1 else x + 30, 312, lab)
    for x, lab in ((x2, "D1"), (x3, "D2")):
        ln(x, YN, x, 310); diode_up(x, 310); ln(x, 330, x, YG); ground(x, YG)
        tx(x + 16 if x == x3 else x - 36, 326, lab)
    for k, x in X.items():
        dot(x, YN)
        tx(x - 18 if k in "12" else x + 8, YN + 22 if k in "23" else YN - 8, k, "n")
    # the record: values and numbers
    I, S, P, A = RES["ideal"], RES["ngspice"], RES["paper"], RES["agreement"]
    v = RES["values"]
    xr = 600
    notes = [
        ("h", "Parts"),
        ("t", "C1 (1–REF), C2 (4–REF): varicaps in antiphase,"),
        ("t", "    C1 + C2 constant"),
        ("t", "Ca (1–2), Cb (3–4): fixed transfer capacitors"),
        ("t", "D1 REF→2, D2 REF→3, D3 3→1, D4 2→4"),
        ("h", "Example values (the paper's)"),
        ("t", f"C1, C2 {v['Cmin'] * 1e12:.0f}–{v['Cmax'] * 1e12:.0f} pF; Ca = Cb = {v['Ca'] * 1e12:.0f} pF; "
              f"{v['F']:.0f} Hz"),
        ("h", "Startup gain (ideal diodes)"),
        ("t", f"z = {I['z_cycle']:.6f} per cycle; √z = {I['sqrt_z_half_cycle']:.6f} per half"),
        ("t", f"e21/e11 = {I['a_e21_e11']:.6f}; e41/e11 = {I['b_e41_e11']:.5f}"),
        ("m", f"paper: √z {P['sqrt_z']}, a {P['a']}, b {P['b']}"),
        ("m", f"ngspice (near-ideal ND): z {S['z_cycle']:.6f} ({A['ngspice_vs_ideal_z'] * 100:+.4f} %)"),
        ("h", "Stage 0 scope"),
        ("m", "Topology only. Values, polarity, clamps Z1 / Z4, strays"),
        ("m", "and real diodes enter in Stage 1 (rebuild/README.md)."),
    ]
    y = 90
    for cl, s in notes:
        if cl == "h":
            y += 10
        tx(xr, y, s, "t" if cl == "h" else cl, 'font-weight="bold"' if cl == "h" else "")
        y += 20
    tx(20, H - 40, "Source: A. C. M. de Queiroz, \"Analysis of Electronic Electrostatic Generators\", Fig. 1 "
                   "(docs/reference/). Numbers: rebuild/s0_base/s0_base_results.json.", "m")
    tx(20, H - 22, "Drawn by rebuild/s0_base/make_schematic.py from s0_base.TOPOLOGY.", "m")
    o.append("</svg>")
    open(os.path.join(HERE, "schematic-s0-base.svg"), "w", encoding="utf-8").write("\n".join(o) + "\n")


if __name__ == "__main__":
    main()
