#!/usr/bin/env python3
"""
tools/gen_artifacts.py — generate the two reference artifacts from their SSOTs.
==============================================================================
  cross-section.svg  <- the authoritative DXF (ezdxf): the spin axis + the ref-radii
                        (R25/R95/R387/R491/R500) + the named features (varicap plates,
                        island bars, the C_R septum, the Cem cores).
  schematic.svg      <- the netlist of record `topology_edge_list.csv` (DXF-sourced r0.15;
                        varcap.cir is not on this branch). Nodes/components labelled to match
                        the netlist, CONNECTIVITY-CHECKED against it (count + every endpoint in
                        the node set). TMD is the design authority on the final schematic
                        aesthetic; this draft DERIVES from the netlist so the two cannot drift.

Read-only over the DXF + the CSV; emits two SVGs + prints the connectivity check. No physics.
"""
import csv
import math
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
DXF = os.path.join(ROOT, "docs", "varcap-nodeanalysis-template-r0.15_TMD_layout.dxf")
EDGES = os.path.join(ROOT, "topology_edge_list.csv")


# =============================================================================
# 1. CROSS-SECTION from the DXF ref-radii + named features
# =============================================================================
def gen_cross_section():
    import ezdxf
    doc = ezdxf.readfile(DXF); msp = doc.modelspace()
    circ = sorted(e.dxf.radius for e in msp if e.dxf.layer == "00-REF-RADII"
                  and e.dxftype() == "CIRCLE")            # 25, 95, 387 (drawn circles)
    # R491 (rotor outer after bus) + R500 (plate edge) are text-only in the DXF -> read them
    radii = {25.0: "R25 ring-in", 95.0: "R95 active inner", 387.0: "R387 active outer",
             491.0: "R491 rotor outer (after bus)", 500.0: "R500 plate edge"}
    present = set(circ) | {491.0, 500.0}
    assert {25.0, 95.0, 387.0}.issubset(set(circ)), "DXF ref-radii drift"
    W, H, CX, CY = 460, 460, 230, 230
    Rmax = 500.0; sc = 200.0 / Rmax
    def ring(r, col, w, dash=""):
        da = f' stroke-dasharray="{dash}"' if dash else ""
        return (f'<circle cx="{CX}" cy="{CY}" r="{r*sc:.1f}" fill="none" stroke="{col}" '
                f'stroke-width="{w}"{da}/>')
    parts = [f'<rect width="{W}" height="{H}" fill="#0b0f14"/>',
             f'<text x="{CX}" y="20" fill="#b8975a" font-size="12" text-anchor="middle" '
             f'font-family="monospace">CROSS-SECTION — r0.15 ref-radii (from DXF)</text>']
    # ref-radii rings + radial leader labels
    cols = {25.0: "#3a4a5a", 95.0: "#5fa8d3", 387.0: "#7cd0ff", 491.0: "#b8975a", 500.0: "#1e2733"}
    for r in sorted(radii):
        parts.append(ring(r, cols.get(r, "#3a4a5a"), 2 if r in (387, 491) else 1,
                           "" if r in (387, 491, 500) else "3 3"))
        ly = CY - r * sc
        parts.append(f'<line x1="{CX}" y1="{ly:.1f}" x2="{CX+96}" y2="{ly:.1f}" stroke="#2a3a48" '
                     f'stroke-width="0.5"/>'
                     f'<text x="{CX+100}" y="{ly+3:.1f}" fill="#9fb0bf" font-size="8.5" '
                     f'font-family="monospace">{radii[r]}</text>')
    # named features
    # 6 alternating varicap wedges (ND1/ND9 plates) in R95..R387
    for i in range(6):
        a0, a1 = math.radians(i*60-12), math.radians(i*60+12)
        ri, ro = 95*sc, 387*sc
        p = lambda r, a: f"{CX+r*math.cos(a):.1f},{CY+r*math.sin(a):.1f}"
        parts.append(f'<path d="M {p(ri,a0)} L {p(ro,a0)} A {ro:.1f} {ro:.1f} 0 0 1 {p(ro,a1)} '
                     f'L {p(ri,a1)} A {ri:.1f} {ri:.1f} 0 0 0 {p(ri,a0)} Z" fill="#13202c" '
                     f'stroke="#2a4a5e" stroke-width="0.6"/>')
    # island bars (ND7/ND8) — short ticks near r350
    for i in range(12):
        a = math.radians(i*30+15); r0, r1 = 330*sc, 360*sc
        parts.append(f'<line x1="{CX+r0*math.cos(a):.1f}" y1="{CY+r0*math.sin(a):.1f}" '
                     f'x2="{CX+r1*math.cos(a):.1f}" y2="{CY+r1*math.sin(a):.1f}" '
                     f'stroke="#e0a83a" stroke-width="1.4"/>')
    # C_R septum (center disc) + Cem cores (ring of squares ~ r440)
    parts.append(f'<circle cx="{CX}" cy="{CY}" r="{25*sc:.1f}" fill="#7d3cb5" opacity="0.5"/>'
                 f'<text x="{CX}" y="{CY+3}" fill="#dfe8f1" font-size="7" text-anchor="middle" '
                 f'font-family="monospace">C_R</text>')
    for i in range(12):
        a = math.radians(i*30); r = 440*sc; x, y = CX+r*math.cos(a), CY+r*math.sin(a)
        parts.append(f'<rect x="{x-3:.1f}" y="{y-3:.1f}" width="6" height="6" fill="#8ab" '
                     f'opacity="0.7"/>')
    # feature legend
    leg = [("#13202c","varicap plates ND1/ND9 (R95–R387)"), ("#e0a83a","island bars ND7/ND8 (~R350)"),
           ("#7d3cb5","C_R septum (12 mm, centre)"), ("#8ab","Cem cores (12, ~R440)")]
    for i,(c,t) in enumerate(leg):
        parts.append(f'<rect x="10" y="{H-58+i*13}" width="9" height="9" fill="{c}"/>'
                     f'<text x="23" y="{H-50+i*13}" fill="#9fb0bf" font-size="8" '
                     f'font-family="monospace">{t}</text>')
    svg = f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" font-family="monospace">' + "".join(parts) + "</svg>"
    open(os.path.join(HERE, "cross-section.svg"), "w").write(svg)
    return sorted(present)


# =============================================================================
# 2. SCHEMATIC from the netlist of record + the CONNECTIVITY CHECK
# =============================================================================
def load_edges():
    rows = []
    for r in csv.reader(open(EDGES)):
        if not r or r[0].startswith("#") or r[0] == "component":
            continue
        rows.append((r[0], r[1], r[2] if len(r) > 2 else ""))
    return rows


def gen_schematic(values=None):
    """Draw a READABLE schematic matching the reference layout (shuttle top, the two Cem ladders
    on the flanks, the 4-node core + Ca/Cb/C1/C2/SG1/SG2 in the middle, the L_R1-C_R-L_R2 resonator
    at the bottom) with real component symbols. Part numbers are fixed labels; the CAP VALUES carry
    `id="sv_*"` placeholders the live drawer overrides from the solver (`values`, else the anchor).
    Still connectivity-checked against the netlist of record."""
    rows = load_edges()
    nodes = set()
    for c, a, b in rows:
        if a: nodes.add(a)
        if b: nodes.add(b)
    n_comp = len(rows); expect = {str(i) for i in range(1, 23)}
    bad = [(c, a, b) for c, a, b in rows if (a and a not in expect) or (b and b not in expect)]
    no_net = [c for c, a, b in rows if not a and not b]
    check = dict(n_components=n_comp, n_nodes=len(nodes & expect), nodes_ok=(nodes & expect) == expect,
                 bad_endpoints=bad, no_net=no_net,
                 ok=(n_comp == 42 and (nodes & expect) == expect and not bad))

    v = dict(C1="280 pF", Ca="309 pF", Cx="471 pF", CR="789 pF", LR="39.5 µH",
             Lcoil="0.64 H", Cblk="440 nF", gap="0.5 mm")
    if values:
        v.update(values)

    # ---------- colours + symbol helpers ----------
    WIRE, CAP, COILM, COILR, GAP, NODE, LBL, VAL, NDC = (
        "#46627a", "#7cd0ff", "#8fb0c8", "#b48ad0", "#e0a83a", "#0e141c", "#cfe9ff", "#ffb454", "#b8975a")
    P = []
    def wire(x1, y1, x2, y2, col=WIRE, w=1.2):
        P.append(f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" stroke="{col}" stroke-width="{w}"/>')
    def label(x, y, t, col=LBL, sz=9, anc="middle"):
        P.append(f'<text x="{x}" y="{y}" fill="{col}" font-size="{sz}" text-anchor="{anc}">{t}</text>')
    def value(x, y, vid, t, anc="middle"):
        P.append(f'<text id="{vid}" x="{x}" y="{y}" fill="{VAL}" font-size="8" text-anchor="{anc}">{t}</text>')
    def node(x, y, nd):
        P.append(f'<circle cx="{x}" cy="{y}" r="3.2" fill="{NDC}"/>')
        label(x + 9, y + 3, f"ND{nd}", NDC, 8, "start")
    def mnode(x, y, nd):                                          # ladder mid-node: label below
        P.append(f'<circle cx="{x}" cy="{y}" r="3" fill="{NDC}"/>')
        label(x, y + 12, f"ND{nd}", NDC, 6.5)
    def cap_v(cx, cy, name, vid=None, val=None, varicap=False):   # vertical cap, leads up/down
        wire(cx, cy-13, cx, cy-4); wire(cx, cy+4, cx, cy+13)
        P.append(f'<line x1="{cx-9}" y1="{cy-4}" x2="{cx+9}" y2="{cy-4}" stroke="{CAP}" stroke-width="1.6"/>')
        P.append(f'<line x1="{cx-9}" y1="{cy+4}" x2="{cx+9}" y2="{cy+4}" stroke="{CAP}" stroke-width="1.6"/>')
        if varicap:
            P.append(f'<line x1="{cx-11}" y1="{cy+9}" x2="{cx+11}" y2="{cy-9}" stroke="{CAP}" stroke-width="1" marker-end="url(#ar)"/>')
        label(cx-13, cy+2, name, LBL, 8.5, "end")
        if vid: value(cx+13, cy+2, vid, val, "start")
    def cap_h(cx, cy, name, vid=None, val=None):                  # horizontal cap, leads left/right
        wire(cx-13, cy, cx-4, cy); wire(cx+4, cy, cx+13, cy)
        P.append(f'<line x1="{cx-4}" y1="{cy-9}" x2="{cx-4}" y2="{cy+9}" stroke="{CAP}" stroke-width="1.6"/>')
        P.append(f'<line x1="{cx+4}" y1="{cy-9}" x2="{cx+4}" y2="{cy+9}" stroke="{CAP}" stroke-width="1.6"/>')
        label(cx, cy-12, name, LBL, 8.5)
        if vid: value(cx, cy+18, vid, val)
    def coil_h(x1, x2, cy, name, val, col=COILM):                 # horizontal inductor (4 humps)
        n = 4; step = (x2 - x1) / n; r = step / 2
        d = f'M {x1} {cy} '
        for i in range(n):
            xa = x1 + i*step
            d += f'A {r} {r} 0 0 1 {xa+step} {cy} '
        P.append(f'<path d="{d}" fill="none" stroke="{col}" stroke-width="1.4"/>')
        label((x1+x2)/2, cy-9, name, LBL, 8)
        label((x1+x2)/2, cy+15, val, VAL, 7.5)
    def gap_v(cx, cy, name):                                      # vertical spark gap (tip-to-tip)
        wire(cx, cy-13, cx, cy-5); wire(cx, cy+5, cx, cy+13)
        P.append(f'<path d="M {cx-6} {cy-5} L {cx+6} {cy-5} L {cx} {cy-0.5} Z" fill="{GAP}"/>')
        P.append(f'<path d="M {cx-6} {cy+5} L {cx+6} {cy+5} L {cx} {cy+0.5} Z" fill="{GAP}"/>')
        label(cx+10, cy+2, name, GAP, 8, "start")
    def gap_seg(x1, y1, x2, y2, name, val=None):                  # a gap drawn mid a sloped wire
        mx, my = (x1+x2)/2, (y1+y2)/2
        wire(x1, y1, x2, y2, GAP, 1.2)
        P.append(f'<circle cx="{mx}" cy="{my}" r="2.6" fill="none" stroke="{GAP}" stroke-width="1.2"/>')
        label(mx, my-5, name, GAP, 7.5)
    def cr_sym(cx, cy, vid, val):                                 # C_R resonator: cap inside a diamond
        P.append(f'<path d="M {cx} {cy-15} L {cx+15} {cy} L {cx} {cy+15} L {cx-15} {cy} Z" '
                 f'fill="none" stroke="{COILR}" stroke-width="1.2"/>')
        P.append(f'<line x1="{cx-6}" y1="{cy-7}" x2="{cx-6}" y2="{cy+7}" stroke="{CAP}" stroke-width="1.5"/>')
        P.append(f'<line x1="{cx+6}" y1="{cy-7}" x2="{cx+6}" y2="{cy+7}" stroke="{CAP}" stroke-width="1.5"/>')
        wire(cx-21, cy, cx-15, cy); wire(cx+15, cy, cx+21, cy)
        label(cx, cy-20, "C_R", LBL, 9); value(cx, cy+28, vid, val)

    W, H = 680, 760
    P.append(f'<rect width="{W}" height="{H}" fill="#0b0f14"/>')
    P.append('<defs><marker id="ar" markerWidth="7" markerHeight="7" refX="5" refY="3" orient="auto">'
             f'<path d="M0 0 L6 3 L0 6 Z" fill="{CAP}"/></marker></defs>')
    label(W/2, 22, "SCHEMATIC — varicap doubler + shuttle + Cem motor + resonator", NDC, 12)
    label(W/2, 36, "(structure from topology_edge_list.csv; part values inherited from the solver)", "#7e8b99", 8.5)

    # ============ key node coordinates ============
    N = {"1": (175, 470), "2": (305, 470), "3": (375, 470), "4": (505, 470),
         "5": (110, 690), "6": (570, 690), "7": (230, 120), "8": (450, 120),
         "9": (300, 690), "10": (380, 690)}
    for i in range(11, 17): N[str(i)] = (235, 250 + (i-11)*34)     # left bank mid-nodes
    for i in range(17, 23): N[str(i)] = (445, 250 + (i-17)*34)     # right bank mid-nodes

    # ============ SHUTTLE (top) ============
    node(*N["7"], "7"); node(*N["8"], "8")
    # SG3a: node1 -> island7 (left)
    gap_seg(N["1"][0], 250, N["7"][0], N["7"][1]+8, "SG3a")
    wire(N["1"][0], 250, N["1"][0], N["1"][1])                     # down the node1 bus
    # Cx3 / SG3b / BS3: island7 -> node3 (cross to the right); draw as a small stacked group
    label(N["7"][0]-6, N["7"][1]-14, "Cx3", LBL, 8.5, "end"); value(N["7"][0]-6, N["7"][1]-25, "sv_Cx3", v["Cx"], "end")
    P.append(f'<line x1="{N["7"][0]-10}" y1="{N["7"][1]-6}" x2="{N["7"][0]-10}" y2="{N["7"][1]+6}" stroke="{CAP}" stroke-width="1.5"/>')
    P.append(f'<line x1="{N["7"][0]-4}" y1="{N["7"][1]-6}" x2="{N["7"][0]-4}" y2="{N["7"][1]+6}" stroke="{CAP}" stroke-width="1.5"/>')
    gap_seg(N["7"][0], N["7"][1]+8, N["3"][0], 250, "SG3b")        # 7 -> 3 (the cross, right-down)
    gap_seg(N["7"][0]+12, N["7"][1]+16, N["3"][0]-8, 258, "BS3")  # backstop (parallel)
    wire(N["3"][0], 250, N["3"][0], N["3"][1])                     # node3 bus down
    # SG4a: node4 -> island8 (right)
    gap_seg(N["4"][0], 250, N["8"][0], N["8"][1]+8, "SG4a")
    wire(N["4"][0], 250, N["4"][0], N["4"][1])
    # Cx4 / SG4b / BS4: island8 -> node2 (cross to the left)
    label(N["8"][0]+6, N["8"][1]-14, "Cx4", LBL, 8.5, "start"); value(N["8"][0]+6, N["8"][1]-25, "sv_Cx4", v["Cx"], "start")
    P.append(f'<line x1="{N["8"][0]+10}" y1="{N["8"][1]-6}" x2="{N["8"][0]+10}" y2="{N["8"][1]+6}" stroke="{CAP}" stroke-width="1.5"/>')
    P.append(f'<line x1="{N["8"][0]+4}" y1="{N["8"][1]-6}" x2="{N["8"][0]+4}" y2="{N["8"][1]+6}" stroke="{CAP}" stroke-width="1.5"/>')
    gap_seg(N["8"][0], N["8"][1]+8, N["2"][0], 250, "SG4b")        # 8 -> 2 (the cross, left-down)
    gap_seg(N["8"][0]-12, N["8"][1]+16, N["2"][0]+8, 258, "BS4")
    wire(N["2"][0], 250, N["2"][0], N["2"][1])

    # ============ Cem ladders (flanks) ============
    # left bank A: node1 bus (x=175) -> L_Ai -> ND(11-16) -> C_ARi -> node2 bus (x=305)
    for i in range(11, 17):
        y = N[str(i)][1]
        coil_h(175, 235, y, f"L_A{i-10}", v["Lcoil"], COILM)
        mnode(235, y, str(i))
        cap_h(280, y, f"C_AR{i-10}", None, None)
        wire(245, y, 305, y) if False else None
    wire(175, 250, 175, N["1"][1]); wire(305, 250, 305, N["2"][1])   # the two buses to core
    for i in range(11, 17):
        wire(305, N[str(i)][1], 305, N[str(i)][1])
    # right bank B: node4 bus (x=505) -> L_Bi -> ND(17-22) -> C_BRi -> node3 bus (x=375)
    for i in range(17, 23):
        y = N[str(i)][1]
        coil_h(445, 505, y, f"L_B{i-16}", v["Lcoil"], COILM)
        mnode(445, y, str(i))
        cap_h(400, y, f"C_BR{i-16}", None, None)
    wire(505, 250, 505, N["4"][1]); wire(375, 250, 375, N["3"][1])

    # ============ core + transfer ============
    for k in ("1", "2", "3", "4"): node(*N[k], k)
    cap_h((N["1"][0]+N["2"][0])/2, N["1"][1], "Ca", "sv_Ca", v["Ca"]); wire(N["1"][0]+13, N["1"][1], (N["1"][0]+N["2"][0])/2-13, N["1"][1]); wire((N["1"][0]+N["2"][0])/2+13, N["1"][1], N["2"][0], N["2"][1])
    cap_h((N["3"][0]+N["4"][0])/2, N["4"][1], "Cb", "sv_Cb", v["Ca"]); wire(N["3"][0], N["3"][1], (N["3"][0]+N["4"][0])/2-13, N["4"][1]); wire((N["3"][0]+N["4"][0])/2+13, N["4"][1], N["4"][0], N["4"][1])
    # C1 (1-5) far left varicap, C2 (4-6) far right
    wire(N["1"][0], N["1"][1], 70, N["1"][1]); wire(70, N["1"][1], 70, 560)
    cap_v(70, 575, "C1", "sv_C1", v["C1"], varicap=True); wire(70, 590, 70, N["5"][1]); wire(70, N["5"][1], N["5"][0], N["5"][1])
    wire(N["4"][0], N["4"][1], 610, N["4"][1]); wire(610, N["4"][1], 610, 560)
    cap_v(610, 575, "C2", "sv_C2", v["C1"], varicap=True); wire(610, 590, 610, N["6"][1]); wire(610, N["6"][1], N["6"][0], N["6"][1])
    # SG1 (2-5), SG2 (3-6)
    wire(N["2"][0], N["2"][1], N["2"][0], 560); gap_v(N["2"][0], 575, "SG1"); wire(N["2"][0], 590, N["2"][0], N["5"][1]); wire(N["2"][0], N["5"][1], N["5"][0], N["5"][1])
    wire(N["3"][0], N["3"][1], N["3"][0], 560); gap_v(N["3"][0], 575, "SG2"); wire(N["3"][0], 590, N["3"][0], N["6"][1]); wire(N["3"][0], N["6"][1], N["6"][0], N["6"][1])

    # ============ resonator (bottom) ============
    node(*N["5"], "5"); node(*N["6"], "6"); node(*N["9"], "9"); node(*N["10"], "10")
    coil_h(N["5"][0], N["9"][0]-22, N["5"][1], "L_R1", v["LR"], COILR); wire(N["9"][0]-22, N["5"][1], N["9"][0]-21, N["5"][1])
    cr_sym((N["9"][0]+N["10"][0])/2, N["5"][1], "sv_CR", v["CR"])
    coil_h(N["10"][0]+22, N["6"][0], N["5"][1], "L_R2", v["LR"], COILR); wire(N["10"][0], N["5"][1], N["10"][0]+22, N["5"][1])

    # connectivity stamp
    label(W/2, H-10, f"connectivity vs netlist: {n_comp} components, {check['n_nodes']}/22 nodes — "
          f"{'MATCH' if check['ok'] else 'MISMATCH'}", "#46c46a" if check["ok"] else "#e5484d", 9)
    svg = f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" font-family="monospace">' + "".join(P) + "</svg>"
    open(os.path.join(HERE, "schematic.svg"), "w").write(svg)
    return check


if __name__ == "__main__":
    radii = gen_cross_section()
    print(f"cross-section.svg <- DXF ref-radii {radii} + named features")
    chk = gen_schematic()
    print(f"schematic.svg <- netlist of record: {chk['n_components']} components, "
          f"{chk['n_nodes']}/22 nodes, nodes_ok={chk['nodes_ok']}, "
          f"bad_endpoints={chk['bad_endpoints']}, no-net(K1 etc.)={chk['no_net']}")
    print(f"CONNECTIVITY CHECK: {'PASS — schematic matches the netlist' if chk['ok'] else 'FAIL'}")
    sys.exit(0 if chk["ok"] else 1)
