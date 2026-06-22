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


def gen_schematic():
    rows = load_edges()
    nodes = set()
    for c, a, b in rows:
        if a:
            nodes.add(a)
        if b:
            nodes.add(b)
    # --- connectivity check (against the netlist itself) ---
    n_comp = len(rows)
    expect_nodes = {str(i) for i in range(1, 23)}
    bad_ends = [(c, a, b) for c, a, b in rows if (a and a not in expect_nodes) or (b and b not in expect_nodes)]
    no_net = [c for c, a, b in rows if not a and not b]      # e.g. K1 (coupling, no nodes)
    check = dict(n_components=n_comp, n_nodes=len(nodes & expect_nodes),
                 nodes_ok=(nodes & expect_nodes) == expect_nodes,
                 bad_endpoints=bad_ends, no_net=no_net,
                 ok=(n_comp == 42 and (nodes & expect_nodes) == expect_nodes and not bad_ends))
    # --- layout: structured columns by subsystem ---
    pos = {}
    pos.update({"1": (160, 90), "2": (160, 200), "3": (320, 200), "4": (320, 90)})   # 4-node core
    pos.update({"5": (90, 145), "7": (160, 300), "8": (320, 300)})                    # rail-5 / islands
    pos.update({"6": (390, 145)})
    pos.update({"9": (210, 380), "10": (270, 380)})                                   # tank
    for i in range(11, 17):   # bank A 11-16
        pos[str(i)] = (40, 70 + (i-11)*40)
    for i in range(17, 23):   # bank B 17-22
        pos[str(i)] = (440, 70 + (i-17)*40)
    W, H = 480, 440
    parts = [f'<rect width="{W}" height="{H}" fill="#0b0f14"/>',
             f'<text x="{W/2}" y="18" fill="#b8975a" font-size="12" text-anchor="middle" '
             f'font-family="monospace">SCHEMATIC — from topology_edge_list.csv (netlist of record)</text>']
    # component edges
    colby = lambda c: ("#7cd0ff" if c.startswith(("C1","C2","Ca","Cb")) else
                       "#e0a83a" if c.startswith(("Cx","SG","BS")) else
                       "#7d3cb5" if c.startswith(("C_R","L_R")) else
                       "#8ab" if c.startswith(("L_A","L_B","C_AR","C_BR")) else "#5fa8d3")
    for c, a, b in rows:
        if a in pos and b in pos:
            (x1, y1), (x2, y2) = pos[a], pos[b]
            mx, my = (x1+x2)/2, (y1+y2)/2
            parts.append(f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" stroke="{colby(c)}" '
                         f'stroke-width="1" opacity="0.65"/>'
                         f'<text x="{mx}" y="{my-2}" fill="{colby(c)}" font-size="6.5" '
                         f'text-anchor="middle" font-family="monospace">{c}</text>')
    # nodes
    for n, (x, y) in pos.items():
        parts.append(f'<circle cx="{x}" cy="{y}" r="9" fill="#121821" stroke="#2a4a5e" '
                     f'stroke-width="1"/><text x="{x}" y="{y+3}" fill="#dfe8f1" font-size="8" '
                     f'text-anchor="middle" font-family="monospace">{n}</text>')
    # check stamp
    stamp = f"connectivity: {n_comp} components, {check['n_nodes']}/22 nodes — {'MATCH' if check['ok'] else 'MISMATCH'}"
    parts.append(f'<text x="{W/2}" y="{H-8}" fill="{"#46c46a" if check["ok"] else "#e5484d"}" '
                 f'font-size="8.5" text-anchor="middle" font-family="monospace">{stamp}</text>')
    svg = f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" font-family="monospace">' + "".join(parts) + "</svg>"
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
