#!/usr/bin/env python3
"""sim/doubler_caps.py -- the doubler's capacitors as built: how C1 / C2 (the vane stacks) and Ca / Cb (the plate
columns) are held in the multiplier's layout (PROPOSED, 2026-10-11), checked against the record's HV rules, and what
the mounts do to Ca, the strays, the pump and the shafts.

The record draws the vanes and the plates bare ("connection and mounts not drawn", sim/tube_geometry.py) and gives the
Ca mounts a first cut only (sim/parts-first-cut-findings.md §4). In the layout Ca / Cb hold 13.2 kV DC, as the vanes
hold V_op (sim/multiplier-layout-findings.md §4). The proposal [IR: the arrangement; RH: the sizes]:
  * Ca / Cb: two combs, each on its own three posts in the column's bore at r 35 (the riser's radius), so that no
    support touches two adjacent plates and no plate is notched. Each plate carries three tabs into the bore at its
    comb's angles. The node-1 comb (Ca_05, _03, _01) hangs from the first rotor vane on Al spacers, and the riser
    lands on its first post. The node-2 comb (Ca_06, _04, _02) stands on three glazed steatite standoffs on the can's
    end disc (REF). The plates stay full annuli, so Ca keeps its overlap.
  * C1 / C2, rotor: G10 spacer rings between the rotor vanes' hub rings on the sleeve, bonded, with three G10 dowels.
    No node-1 metal touches the sleeve below the first rotor vane, so the PTFE cover's 84 mm stays.
  * C1 / C2, stator: each stator vane gets six lugs outside its ring. Six glass-epoxy tie rods with G10 spacer tubes
    stack the vanes from a G10 ring under the first to the Ca|reluctance spider. The cage tube moves out to r 182-186
    and the lugs locate in its bore, so it stays one tube from spider to spider; the spiders grow to r 182.
Sections:
  1. the mounts' placement (placement(), which sim/tube_geometry.py LayoutMachine reads);
  2. the HV rules at every new interface (sim/parts_first_cut.py as sim/multiplier_layout.py applies them), and the
     record's rule that no support may touch two adjacent plates;
  3. the fields where one comb's tab crosses the other comb's bore edge with its post in front (sim/vane_cell.py
     edge_field, the record's rim model, and an axisymmetric post-through-a-hole solve), against Peek's onset on a
     handled surface: the record's rim criterion (sim/vane-matrix-findings.md §2);
  4. Ca with the tabs (2-D fringe) and the strays the mounts add [RH: sim/multiplier_layout.py's line and cylinder
     formulas];
  5. the circuit with them: sim/multiplier_layout.py run_deck at the pick, for the start-up gain and the rings;
  6. the masses and the shafts: the drawn solids with and without the mounts (sim/bridge_ring_bearings.py
     solids_parts, sim/shaft_bearings.py two_body).
Writes sim/doubler_caps_results.json and docs/figures/doubler-caps.png; the findings are sim/doubler-caps-findings.md.
Tags (CONVENTIONS.md §1): [OC] derivable; [IR] a modelling or engineering choice; [RH] heuristic. g is a gap.
Usage: python3 sim/doubler_caps.py [--procs 4] [--only rules fields strays circuit shafts]   (about ten minutes;
ngspice and OCP)
"""
import argparse
import json
import math
import os
import sys
import time

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path[:0] = [HERE]
import stack_sizing as S                                 # noqa: E402

OUT_JSON = os.path.join(HERE, "doubler_caps_results.json")
FIG = os.path.join(ROOT, "docs", "figures", "doubler-caps.png")
LAYOUT_JSON = os.path.join(HERE, "multiplier_layout_results.json")
SRC = {
    "stack": "sim/multiplier_layout_results.json stack (the column, the vanes, the can's disc, the spider) and decks "
             "(the junctions: the riser's and the tap's angles)",
    "volts": "sim/multiplier_layout_results.json volts.pairs (the pick's steady state as built)",
    "rules": "sim/parts_first_cut.py clearance_case_a, creepage, DC_MARGIN, CLR_MARGIN (via sim/multiplier_layout.py "
             "clearance, worst; sim/parts-first-cut-findings.md §4)",
    "rim model": "sim/vane_cell.py edge_field, _round_field, peek_kV_per_cm; sim/vane_matrix.py M_HANDLED 0.85",
    "strays": "sim/multiplier_layout.py c_wire_cyl, c_cyl_plane, strays (its total_pF, cp_pF, deck_strays_pF)",
    "Ca as laid out": "sim/tube-strays-findings.md §4 (480.5 pF solved); sim/integrated_multiplier.py SET_AB ca",
    "circuit": "sim/multiplier_layout.py run_deck (sim/integrated_multiplier.py proposal at the pick, C3-C6 180 pF)",
    "shafts": "sim/bridge_ring_bearings.py solids_parts, K_REAL; sim/shaft_bearings.py two_body, K_BEARING, F_REL_HZ",
}

# ---------------------------------------------------------------------------------------------------- the mounts
# the Ca / Cb column [IR: the arrangement; RH: the sizes]
R_POST = 35.0          # the posts' circle in the column's bore, the riser's radius (sim/tube_geometry.py R_RISER)
POST_D = 8.0           # Al spacers (EN AW-6082) Ø8, M4 female, joined by A4 studs through the plates' tabs
TAB_LOBE_R = 8.0       # a tab: the hull of a lobe R8 round its post and a 24 mm chord on the plate's bore (r 50)
TAB_W = 24.0
HOLE_D = 4.5           # M4 clearance (ISO 273, medium)
CSK_D = 8.96           # the countersink's diameter for an ISO 10642 M4 head (dk 8.96), 90 deg
STANDOFF_D, STANDOFF_L = 16.0, 30.0       # node 2's feet: glazed steatite C 221 (IEC 60672), M4 brass inserts
STANDOFF_MATERIAL = "glazed steatite C 221 standoff, M4 brass inserts"
BOOT = (9.0, 8.0)      # a silicone boot over a lug's joint: radius, height [RH]
# C1 / C2, rotor
VSP_R1 = 32.0          # G10 spacer rings r 20.5-32 x 15 between the rotor vanes' hub rings, bonded
DOWEL_D, DOWEL_R = 5.0, 26.25
DOWEL_TH = (90.0, 210.0, 330.0)            # in the vanes' frame (the blades at 0 + 60 k) [RH]
# C1 / C2, stator
LUG_TH = tuple(30.0 + 60.0 * k for k in range(6))   # between the blades
ROD_R, ROD_D, ROD_HOLE = 173.0, 8.0, 8.5   # glass-epoxy threaded rod M8 (G10 class), its holes 8.5
LUG_R, LUG_W = 9.0, 28.0                   # a lug: the hull of R9 round the rod and a 28 mm chord on the ring (r 162)
SSP_D = 16.0                               # G10 spacer tubes Ø16 / 8.5 on the rods
CAGE_R0, CAGE_R1 = 182.0, 186.0            # the cage tube moved out: the lugs locate in its bore
END_RING = (166.0, 182.0, 10.0)            # G10 ring r 166-182 x 10 bonded in the cage's bore under the first vane
NUT = (13.0, 6.5)                          # an M8 nut, glass-epoxy: across flats, height
SPIDER_R1 = CAGE_R0                        # the Ca|reluctance spider grows to the cage's bore
ROD_MATERIAL = "G10-class glass-epoxy threaded rod M8"


def _ang(xy):
    return math.degrees(math.atan2(xy[1], xy[0]))


def _norm(a):
    return (a + 180.0) % 360.0 - 180.0


def placement(lay=None):
    """the mounts in the layout's frame: h from the hub's centre (side A toward its end; side B the mirror), angles in
    the machine's frame (deg). The posts of each comb, segment by segment; what each segment touches and what it
    passes; the vane stacks' spacers, dowels, lugs, rods and rings; the cage tube; the riser's new end."""
    lay = lay or json.load(open(LAYOUT_JSON))
    st, dk = lay["stack"], lay["decks"]
    E = st["elements"]
    kinds = lambda k: [e for e in E if e["kind"] == k]
    one = lambda k: kinds(k)[0]
    mirror = {"0": "0", "1": "4", "2": "3"}
    plates = sorted(kinds("Ca plate"), key=lambda e: e["h0"])          # Ca_06 (node 2) at the deck's end
    vanes = sorted(kinds("C1 vane"), key=lambda e: e["h0"])
    rotor = [e for e in vanes if e["body"] == "rotor"]
    stator = [e for e in vanes if e["body"] == "stator"]
    cdi, sp = one("can disc"), one("spider")
    comb = {"1": [e for e in plates if e["node"] == "1"], "2": [e for e in plates if e["node"] == "2"]}
    r01 = rotor[0]
    nm = lambda e: f"Ca_{e['index']:02d}"
    # node 1: Ca_05 -> Ca_03 -> Ca_01 -> the first rotor vane; node 2: the can's disc -> Ca_06 -> Ca_04 -> Ca_02
    seg1 = [dict(kind="spacer", h0=a["h1"], h1=b["h0"], below=nm(a), above=(nm(b) if b in plates else "r01"))
            for a, b in zip(comb["1"], comb["1"][1:] + [r01])]
    seg2 = [dict(kind="standoff", h0=cdi["h1"], h1=comb["2"][0]["h0"], below="can disc", above=nm(comb["2"][0]))] + \
        [dict(kind="spacer", h0=a["h1"], h1=b["h0"], below=nm(a), above=nm(b)) for a, b in zip(comb["2"], comb["2"][1:])]
    for seg, other in ((seg1, comb["2"]), (seg2, comb["1"])):
        for q in seg:
            q["L"] = q["h1"] - q["h0"]
            q["passes"] = [nm(e) for e in other if e["h0"] >= q["h0"] - 1e-9 and e["h1"] <= q["h1"] + 1e-9]
    sides = {}
    for s_ in "AB":
        mp = (lambda n: n) if s_ == "A" else (lambda n: mirror[n])
        J = dk[s_]["junctions"]
        th_r, th_t = _ang(J[mp("1")]), _ang(J[mp("2")])
        sides[s_] = dict(node_1=mp("1"), node_2=mp("2"), theta_riser_deg=th_r, theta_tap_deg=th_t,
                         theta_n1_deg=[_norm(th_r + 120.0 * k) for k in range(3)],
                         theta_n2_deg=[_norm(th_r + 60.0 + 120.0 * k) for k in range(3)])
    # the C1 / C2 stacks
    vsp = [dict(h0=a["h1"], h1=b["h0"]) for a, b in zip(rotor, rotor[1:])]
    ssp = [dict(h0=a["h1"], h1=b["h0"]) for a, b in zip(stator, stator[1:])] + [dict(h0=stator[-1]["h1"], h1=sp["h0"])]
    ring = dict(r0=END_RING[0], r1=END_RING[1], h0=stator[0]["h0"] - END_RING[2], h1=stator[0]["h0"])
    rods = dict(h0=ring["h0"] - NUT[1], h1=sp["h1"] + NUT[1], nuts=[(ring["h0"] - NUT[1], ring["h0"]),
                                                                       (sp["h1"], sp["h1"] + NUT[1])])
    h_cage = st["h_bearing_mm"] + 0.5 * S.BEARING["slot"]               # the tube's ends, as the layout's (299)
    return dict(params=dict(R_POST=R_POST, POST_D=POST_D, TAB_LOBE_R=TAB_LOBE_R, TAB_W=TAB_W, HOLE_D=HOLE_D,
                            STANDOFF=[STANDOFF_D, STANDOFF_L], VSP_R1=VSP_R1, DOWEL=[DOWEL_D, DOWEL_R], ROD_R=ROD_R,
                            ROD_D=ROD_D, LUG=[LUG_R, LUG_W], SSP_D=SSP_D, CAGE=[CAGE_R0, CAGE_R1], END_RING=list(END_RING)),
                sides=sides, comb={k: [nm(e) for e in v] for k, v in comb.items()},
                plates={nm(e): dict(h0=e["h0"], h1=e["h1"], node=e["node"]) for e in plates},
                posts_n1=seg1, posts_n2=seg2, r01=dict(h0=r01["h0"], h1=r01["h1"]),
                riser_end_h=comb["1"][0]["h0"], can_disc=dict(h0=cdi["h0"], h1=cdi["h1"], r0=cdi["r0"], r1=cdi["r1"]),
                vane_spacers=vsp, dowels=dict(h0=rotor[0]["h0"], h1=rotor[-1]["h1"], r=DOWEL_R, d=DOWEL_D, theta_deg=list(DOWEL_TH)),
                rotor_vanes=[dict(h0=e["h0"], h1=e["h1"], index=e["index"]) for e in rotor],
                stator_vanes=[dict(h0=e["h0"], h1=e["h1"], index=e["index"]) for e in stator],
                stator_spacers=ssp, end_ring=ring, rods=rods, lugs_deg=list(LUG_TH),
                spider=dict(h0=sp["h0"], h1=sp["h1"], r0=sp["r0"], r1=SPIDER_R1),
                cage=dict(r0=CAGE_R0, r1=CAGE_R1, h=h_cage),
                sleeve_cover=dict(h0=one("sleeve")["h0"], h1=r01["h0"]))


def tab_outline(n=48):
    """a tab's outline in its plate's frame (the tab on the x axis), counter-clockwise: the hull of the lobe and the
    chord, its outer points 1 mm inside the plate's bore so that the union is solid [RH]."""
    from scipy.spatial import ConvexHull
    r_in = S.R_IN_DEFAULT if hasattr(S, "R_IN_DEFAULT") else 50.0
    a = np.linspace(0.0, 2 * math.pi, n, endpoint=False)
    P = np.c_[R_POST + TAB_LOBE_R * np.cos(a), TAB_LOBE_R * np.sin(a)]
    r_o = r_in + 1.0
    phi = math.asin(0.5 * TAB_W / r_o)
    P = np.vstack([P, [[r_o * math.cos(phi), r_o * math.sin(phi)], [r_o * math.cos(phi), -r_o * math.sin(phi)]]])
    h = ConvexHull(P)
    return [tuple(map(float, P[i])) for i in h.vertices]


def lug_outline(n=48):
    """a stator vane's lug in its frame (the lug on the x axis): the hull of R9 round the rod and a 28 mm chord on the
    ring, its inner points 1 mm inside the ring (r 161) [RH]."""
    from scipy.spatial import ConvexHull
    a = np.linspace(0.0, 2 * math.pi, n, endpoint=False)
    P = np.c_[ROD_R + LUG_R * np.cos(a), LUG_R * np.sin(a)]
    r_i = 161.0
    phi = math.asin(0.5 * LUG_W / r_i)
    P = np.vstack([P, [[r_i * math.cos(phi), r_i * math.sin(phi)], [r_i * math.cos(phi), -r_i * math.sin(phi)]]])
    h = ConvexHull(P)
    return [tuple(map(float, P[i])) for i in h.vertices]


def tab_area():
    P = np.array(tab_outline(240))
    x, y = P[:, 0], P[:, 1]
    full = 0.5 * abs(np.dot(x, np.roll(y, 1)) - np.dot(y, np.roll(x, 1)))
    # less the part inside the plate (r >= 50): numerically, on a fine grid
    g = np.linspace(-20.0, 60.0, 801)
    X, Y = np.meshgrid(g, g)
    from matplotlib.path import Path
    inside = Path(P).contains_points(np.c_[X.ravel(), Y.ravel()]).reshape(X.shape)
    cell = (g[1] - g[0]) ** 2
    beyond = float((inside & (np.hypot(X, Y) < 50.0)).sum() * cell)
    return dict(hull_mm2=full, in_bore_mm2=beyond)


# ---------------------------------------------------------------------------------------------------- 2. the rules
def rules(V, pl):
    """every interface the mounts make, against the record's rules (bare air: Table F.2 case A at 1.5 x the peak;
    surfaces: creepage at PD2 x 1.25 on PTFE / silicone (I) or G10 (IIIa); glazed steatite does not track, so its
    creepage is its clearance), and the rule that no support may touch two adjacent plates [IR]."""
    import multiplier_layout as ML
    import parts_first_cut as PF
    rows = []

    def row(name, nets_a, nets_b, kind, available, note=""):
        w = ML.worst(V, nets_a, nets_b)
        clr = ML.clearance(w["pk"])
        cr_i = PF.creepage(w["rms"], "I") * PF.DC_MARGIN
        cr_g = PF.creepage(w["rms"], "IIIa") * PF.DC_MARGIN
        need = {"air": clr, "steatite": clr, "PTFE": cr_i, "G10": cr_g}.get(kind)
        ok = None if need is None or available is None else bool(available >= need - 1e-9)
        rows.append(dict(interface=name, kind=kind, pair=w["pair"], U_pk_kV=w["pk"], U_rms_kV=w["rms"], clearance_mm=clr,
                         creepage_PTFE_mm=cr_i, creepage_G10_mm=cr_g, need_mm=need, available_mm=available, ok=ok,
                         note=note))
    chord = 2.0 * R_POST * math.sin(math.radians(30.0))                  # adjacent posts, 60 deg apart
    row("a node-1 post <-> the nearest node-2 post (Ca), bare air", ["1"], ["2"], "air", chord - POST_D,
        "posts 60 deg apart on r 35, both Ø8")
    row("a post <-> the other comb's bore edges (r 50), bare air", ["1"], ["2"], "field", 50.0 - R_POST - 0.5 * POST_D,
        "the column's own class: its plates hold the same 13.2 kV across 6 mm; judged by the field (§3), not case A")
    row("a node-2 standoff, node 2 <-> the can's disc (REF): along glazed steatite", ["2"], ["0"], "steatite",
        STANDOFF_L, "inorganic: creepage need not exceed the clearance (IEC 60664-1)")
    row("the same, were it PTFE (the alternate)", ["2"], ["0"], "PTFE", STANDOFF_L, "")
    row("Ca_06's tabs <-> the can's disc (REF), bare air", ["2"], ["0"], "air",
        pl["plates"]["Ca_06"]["h0"] - pl["can_disc"]["h1"], "the plate's own interface as the layout")
    row("the node-1 comb's lowest metal (Ca_05) <-> the can's disc (REF), bare air", ["1"], ["0"], "air",
        pl["plates"]["Ca_05"]["h0"] - pl["can_disc"]["h1"], "the riser's lug under Ca_05 is in its silicone boot")
    row("the sleeve's PTFE cover, the first rotor vane (node 1) <-> the can's disc: no node-1 metal on it below", ["1"],
        ["0"], "PTFE", pl["sleeve_cover"]["h1"] - pl["sleeve_cover"]["h0"], "unchanged from the layout (84 mm)")
    row("a rotor-vane spacer ring (G10, between node-1 vanes) <-> the stator blades' inner ends (r 50)", ["1"], ["0"],
        "insulator", 50.0 - VSP_R1, "the ring bridges node-1 vanes only; the blades' ends face the vanes' hub rings "
        "across the varicap's own 6 mm gap; the 12 mm rule for an insulator, as the cage")
    row("the rotor vanes' rims (r 150) <-> the stator stack's G10 spacer tubes", ["1"], ["0"], "insulator",
        ROD_R - 0.5 * SSP_D - 150.0, "the record keeps 12 mm between the rims and the cage's G10 (12 mm rule)")
    row("the Ca plates' and the first rotor vane's rims (r 150) <-> the G10 end ring and its nuts", ["1", "2"], ["0"],
        "insulator", min(END_RING[0], ROD_R - 0.5 * NUT[0] * 2 / math.sqrt(3)) - 150.0, "the 12 mm rule")
    row("the decks' outermost housings <-> the cage, moved out to r 182", ["ea", "xa", "r1", "2"], ["0"], "insulator",
        CAGE_R0 - 150.0, "the layout's 13 mm becomes 33 mm")
    for r in rows:
        if r["kind"] == "insulator":
            r["need_mm"], r["ok"] = 12.0, bool(r["available_mm"] >= 12.0)
    # the record's rule: no support may touch two adjacent plates (sim/parts-first-cut-findings.md §4)
    order = list(pl["plates"])                                           # Ca_06 .. Ca_01 by height
    comb_of = {n: q["node"] for n, q in pl["plates"].items()}
    touch = []
    for c, seg in (("1", pl["posts_n1"]), ("2", pl["posts_n2"])):
        for q in seg:
            ends = [x for x in (q["below"], q["above"]) if x in comb_of]
            ok = all(comb_of[x] == c for x in ends) and all(comb_of[x] != c for x in q["passes"])
            touch.append(dict(comb=c, h0=q["h0"], h1=q["h1"], touches=ends, passes=q["passes"], ok=bool(ok)))
    adjacent = [(a, b) for a, b in zip(order, order[1:])]
    return dict(rows=rows, touches=touch, adjacent_pairs=adjacent,
                no_support_touches_two_adjacent=bool(all(t["ok"] for t in touch)),
                ok=bool(all(r["ok"] is not False for r in rows) and all(t["ok"] for t in touch)))


# ---------------------------------------------------------------------------------------------------- 3. the fields
def _laplace(inside, val, h, rr=None, bc=None):
    """5-point Laplace on a uniform grid (axis 0 x or rho, axis 1 z); planar, or axisymmetric with node radii rr
    along axis 0. Dirichlet on the inside nodes (val); each side Neumann (a mirror) unless bc names its potential."""
    import scipy.sparse as sp_
    import scipy.sparse.linalg as spl
    nx, nz = inside.shape
    fr = ~inside
    idx = -np.ones((nx, nz), dtype=np.int64)
    idx[fr] = np.arange(int(fr.sum()))
    I, K = np.nonzero(fr)
    me = idx[I, K]
    rows, cols, vals = [], [], []
    rhs, diag = np.zeros(len(me)), np.zeros(len(me))
    names = {(-1, 0): "left", (1, 0): "right", (0, -1): "bottom", (0, 1): "top"}
    for (di, dk), side in names.items():
        w = np.ones(len(me)) if (rr is None or di == 0) else 1.0 + di * 0.5 * h / rr[I]
        i2, k2 = I + di, K + dk
        out = (i2 < 0) | (i2 >= nx) | (k2 < 0) | (k2 >= nz)
        v_b = (bc or {}).get(side)
        if v_b is not None:
            diag[out] += w[out]; rhs[out] += w[out] * v_b
        i2c, k2c = np.clip(i2, 0, nx - 1), np.clip(k2, 0, nz - 1)
        cnd = ~out & inside[i2c, k2c]
        diag[cnd] += w[cnd]; rhs[cnd] += w[cnd] * val[i2c[cnd], k2c[cnd]]
        nb = ~out & ~inside[i2c, k2c]
        diag[nb] += w[nb]
        rows.append(me[nb]); cols.append(idx[i2c[nb], k2c[nb]]); vals.append(-w[nb])
    rows.append(me); cols.append(me); vals.append(diag)
    A = sp_.csr_matrix((np.concatenate(vals), (np.concatenate(rows), np.concatenate(cols))), shape=(len(me), len(me)))
    V = np.array(val, float)
    V[fr] = spl.spsolve(A.tocsc(), rhs)
    return V


def _charge(V, cond, h):
    """the flux (per unit length, in units of eps0 x volts) leaving the conductor nodes cond into the free nodes,
    planar 5-point."""
    q = 0.0
    nx, nz = V.shape
    I, K = np.nonzero(cond)
    for di, dk in ((1, 0), (-1, 0), (0, 1), (0, -1)):
        i2, k2 = I + di, K + dk
        ok = (i2 >= 0) & (i2 < nx) & (k2 >= 0) & (k2 < nz)
        i2, k2, ii, kk = i2[ok], k2[ok], I[ok], K[ok]
        free = ~cond[i2, k2]
        q += float(np.sum(V[ii[free], kk[free]] - V[i2[free], k2[free]]))
    return q


def post_through_hole(a, gap, t=3.0, g=6.0, h=0.05):
    """a post (radius a, the comb's potential, 0) through a hole in the other comb's plate (radius a + gap, its edge
    a full round, at 1), the post's own tabs as planes g from the plate's faces: axisymmetric about the post's axis,
    the plate's mid-plane a mirror. The post's surface field (the coax law fitted over its first cells) and the
    edge's (sim/vane_cell.py _round_field), per volt [OC: the solve; the hole all round is the post's worst case]."""
    import vane_cell as VC
    R, H = 0.5 * t, 0.5 * t + g
    b = a + gap
    rr = a + h * np.arange(int(round((b + 25.0 - a) / h)) + 1)
    zs = h * np.arange(int(round(H / h)) + 1)
    RR, ZZ = np.meshgrid(rr, zs, indexing="ij")
    post, plane = RR <= a + 1e-9, ZZ >= H - 1e-9
    plate = ((RR >= b + R) & (ZZ <= R + 1e-9)) | ((RR - (b + R)) ** 2 + ZZ ** 2 <= R * R * (1 + 1e-9))
    V = _laplace(post | plane | plate, np.where(plate, 1.0, 0.0), h, rr=rr)
    Ep = []
    L = a * np.log(rr[2:9] / a)
    for k in range(len(zs)):
        if zs[k] < H - 0.2:
            Ep.append(float(np.dot(L, V[2:9, k]) / np.dot(L, L)))
    ang, e = VC._round_field(V, RR, ZZ, b + R, 0.0, R, h, 1.0, lambda x, z: x <= b + R)
    return dict(E_post_per_V=max(Ep), E_edge_per_V=float(e.max()), edge_angle_deg=float(ang[int(np.argmax(e))]))


def aligned_rims(t=3.0, g=6.0, h=0.05, field=False):
    """the column's own rims: a plate at 1 V and its neighbour at 0 ending together (full rounds), the stack
    alternating (mirrors at both plates' mid-planes), open beyond the rims [OC: the solve]. Per volt; and the
    neighbours' charge per unit length of rim."""
    import vane_cell as VC
    R, P = 0.5 * t, t + g
    xs = -22.5 + h * np.arange(int(round(47.5 / h)))
    zs = h * np.arange(int(round(P / h)) + 1)
    X, Z = np.meshgrid(xs, zs, indexing="ij")
    p1 = ((X <= -R) & (Z <= R + 1e-9)) | ((X + R) ** 2 + Z ** 2 <= R * R * (1 + 1e-9))
    p0 = ((X <= -R) & (Z >= P - R - 1e-9)) | ((X + R) ** 2 + (Z - P) ** 2 <= R * R * (1 + 1e-9))
    V = _laplace(p1 | p0, np.where(p1, 1.0, 0.0), h)
    ang, e = VC._round_field(V, X, Z, -R, 0.0, R, h, 1.0, lambda x, z: x >= -R)
    out = dict(E_peak_per_V=float(e.max()), angle_deg=float(ang[int(np.argmax(e))]), q_per_V=_charge(V, p1, h))
    if field:
        out.update(V=V, xs=xs, zs=zs)
    return out


def tab_crossing(gw, t=3.0, g=6.0, h=0.05):
    """a plate's edge under the other comb's tab: the plate at 1 V between continuing planes at 0 (sim/vane_cell.py
    edge_field's geometry, the record's rim model), the tab's post a wall at 0 gw in front of its tip; the stack's
    period as aligned_rims, so the charges compare [OC: the solve]."""
    import vane_cell as VC
    R, P = 0.5 * t, t + g
    xs = -22.5 + h * np.arange(int(round((22.5 + gw) / h)))
    zs = h * np.arange(int(round(P / h)) + 1)
    X, Z = np.meshgrid(xs, zs, indexing="ij")
    p1 = ((X <= -R) & (Z <= R + 1e-9)) | ((X + R) ** 2 + Z ** 2 <= R * R * (1 + 1e-9))
    p0 = Z >= P - R - 1e-9
    V = _laplace(p1 | p0, np.where(p1, 1.0, 0.0), h, bc=dict(right=0.0))
    ang, e = VC._round_field(V, X, Z, -R, 0.0, R, h, 1.0, lambda x, z: x >= -R)
    return dict(E_peak_per_V=float(e.max()), angle_deg=float(ang[int(np.argmax(e))]), q_per_V=_charge(V, p1, h))


def fields(V, log=print):
    """§3: the corona onset of every edge the mounts make, on a handled surface (Peek, m 0.85), against the peak it
    holds; the record's own rims for scale (the C1 rims between the stator rings, the column's aligned rims)."""
    import vane_cell as VC
    import vane_matrix as VM
    m = VM.M_HANDLED
    v12, v10 = V["pairs"]["1|2"]["pk"], V["pairs"]["0|1"]["pk"]
    on_rim = VC.peek_kV_per_cm(1.5) * m
    on_post = VC.peek_kV_per_cm(0.5 * POST_D) * m

    def mg(E_per_V, Vpk, onset):
        E = E_per_V * Vpk * 10.0
        return dict(E_kV_cm=E, onset_kV_cm=onset, margin=onset / E, V_onset_kV=Vpk * onset / E)
    c1 = VC.edge_field(3.0, 6.0, "round")
    al = aligned_rims()
    gw = 50.0 - R_POST - 0.5 * POST_D
    tc = tab_crossing(gw)
    ph = post_through_hole(0.5 * POST_D, gw)
    out = dict(m_handled=m, peaks_kV=dict(Ca=v12, C1=v10),
               C1_rims=dict(model="sim/vane_cell.py edge_field(3, 6): a rotor rim between the stator rings", **mg(c1["E_peak_per_V"], v10, on_rim)),
               Ca_aligned_rims=dict(model="the column's own rims, ending together", **mg(al["E_peak_per_V"], v12, on_rim)),
               tab_crossing=dict(model=f"a bore edge under the other comb's tab, its post {gw:.0f} mm in front (a wall)",
                                 gap_mm=gw, **mg(tc["E_peak_per_V"], v12, on_rim)),
               hole_edge=dict(model="the same edge round the post (axisymmetric, a hole all round)", gap_mm=gw,
                              **mg(ph["E_edge_per_V"], v12, on_rim)),
               post=dict(model="the post's own surface (axisymmetric, the hole all round)", radius_mm=0.5 * POST_D,
                         **mg(ph["E_post_per_V"], v12, on_post)))
    sweep = []
    for g_ in (5.0, 6.0, 7.0, 8.0, 9.0, 11.0, 13.0, 15.0, 20.0):
        q = tab_crossing(g_)
        sweep.append(dict(gap_mm=g_, **mg(q["E_peak_per_V"], v12, on_rim)))
    out["sweep_tab_crossing"] = sweep
    out["criterion"] = "the handled-surface onset above the peak (margin >= 1), the record's rim criterion; reported " \
                       "against the C1 rims, which hold the same peak"
    out["ok"] = bool(min(out[k]["margin"] for k in ("tab_crossing", "hole_edge", "post")) >= 1.0)
    for k in ("C1_rims", "Ca_aligned_rims", "tab_crossing", "hole_edge", "post"):
        log(f"  {k:16s} {out[k]['E_kV_cm']:5.1f} kV/cm against onset {out[k]['onset_kV_cm']:5.1f}: margin "
            f"{out[k]['margin']:.3f}")
    # Ca's fringe at a crossing: the charge per mm of edge, the crossing against the aligned rims [OC: same period]
    out["fringe"] = dict(q_aligned_per_V=al["q_per_V"], q_crossing_per_V=tc["q_per_V"],
                         dC_pF_per_mm=(tc["q_per_V"] - al["q_per_V"]) * 2.0 * S.EPS0_MM * 1e12)
    return out


# ---------------------------------------------------------------------------------------------------- 4. Ca, strays
def ca_and_strays(pl, fl):
    """Ca with the tabs: the overlap unchanged (each tab lies in the bore, where the other comb has no metal) [OC], and
    the fringe at every crossing of a bore edge under a tab (§3's charge, per mm of edge, x the tab's 24 mm at the
    bore) [OC: 2-D; RH: the width]. The strays the mounts add per node, as sim/multiplier_layout.py strays sizes them
    [RH]: each comb's three columns of posts and tabs as wires of the lobe's radius to the shaft under its sleeve;
    the standoffs' ceramic (eps 6) between their inserts; Ca_06's tabs over the can's disc; the riser 45 mm shorter."""
    import multiplier_layout as ML
    lay = json.load(open(LAYOUT_JSON))
    # crossings per side: a node-2 bore edge under a node-1 tab (both faces when node-1 tabs lie on both sides)
    plates = pl["plates"]
    order = list(plates)
    faces = 0.0
    for i, n in enumerate(order):
        node = plates[n]["node"]
        nb = [order[j] for j in (i - 1, i + 1) if 0 <= j < len(order)]
        if n == "Ca_01":
            nb = [x for x in nb] + ["r01"]
        other = [x for x in nb if (x == "r01" and node == "2") or (x in plates and plates[x]["node"] != node)]
        faces += 0.5 * len(other)                                       # a face per neighbour of the other comb
    n_tabs = 3
    dC = fl["fringe"]["dC_pF_per_mm"] * TAB_W * faces * n_tabs
    ca_laid = 480.5                                                     # sim/tube-strays-findings.md §4
    ca = dict(laid_out_pF=ca_laid, crossings_full_faces=faces * n_tabs, fringe_pF=dC, with_mounts_pF=ca_laid + dC,
              ratio_to_C_max=(ca_laid + dC) / 450.0, rule=1.1, laid_out_ratio=ca_laid / 450.0)
    sh = 18.4                       # the shaft's radius raised by its G10 sleeve, as sim/multiplier_layout.py strays
    L1 = pl["r01"]["h0"] - plates["Ca_05"]["h0"]                        # Ca_05 to the first rotor vane, 45 mm
    L2 = plates["Ca_02"]["h1"] - plates["Ca_06"]["h0"]                  # Ca_06 to Ca_02's top, 39 mm
    col = lambda L: ML.c_wire_cyl(L, TAB_LOBE_R, R_POST, sh)
    eps_st = 6.0                                                        # steatite C 221 [IR datasheet-class]
    insert_r, insert_l = 3.5, 8.0
    c_st = 8.8541878128e-12 * eps_st * math.pi * insert_r ** 2 * 1e-6 / ((STANDOFF_L - 2 * insert_l) * 1e-3) * 1e12
    ta = tab_area()
    c_tab_disc = 8.8541878128e-12 * 3 * ta["in_bore_mm2"] * 1e-6 / ((plates["Ca_06"]["h0"] - pl["can_disc"]["h1"]) * 1e-3) * 1e12
    l_bore = ML.L_COL + ML.G_V + (lay["stack"]["h_col_mm"] - lay["stack"]["h_parts_mm"])
    riser = lay["strays"]["parts"]["1"]["riser (bore)"]
    d_riser = -riser * (pl["r01"]["h0"] - pl["riser_end_h"]) / l_bore
    n1 = {"the node-1 comb's three columns (posts and tabs)": 3 * col(L1), "the riser, ending at Ca_05": d_riser}
    n2 = {"the node-2 comb's three columns": 3 * col(L2), "the three steatite standoffs": 3 * c_st,
          "Ca_06's tabs over the can's disc": c_tab_disc}
    d1, d2 = sum(n1.values()), sum(n2.values())
    cp0 = lay["strays"]["cp_pF"]
    cp = {"1": cp0["1"] + d1, "4": cp0["4"] + d1, "2": cp0["2"] + d2, "3": cp0["3"] + d2}
    return dict(Ca=ca, tab_area=ta, strays=dict(node_1=n1, node_2=n2, d_node_1_pF=d1, d_node_2_pF=d2), cp_layout_pF=cp0,
                cp_mounts_pF=cp, deck_strays_pF=lay["strays"]["deck_strays_pF"])


# ---------------------------------------------------------------------------------------------------- 5. the circuit
def _run(job):
    import integrated_multiplier as IM
    import multiplier_layout as ML
    if job.get("ca_scale"):
        IM.SET_AB = dict(IM.SET_AB, ca=IM.SET_AB["ca"] * job["ca_scale"])
    try:
        return ML.run_deck(job)
    finally:
        if job.get("ca_scale"):
            IM.SET_AB = dict(IM.SET_AB, ca=IM.SET_AB["ca"] / job["ca_scale"])


def circuit(cs, procs, log):
    """the layout's deck at the pick (C3-C6 180 pF) with the layout's strays (a gate: it must give the layout study's
    rows) and with the mounts' (node strays and Ca): the start-up gain (40 free cycles, the clamps out) and the rings
    (the clamped steady state, doubled until settled)."""
    from multiprocessing import Pool
    import multiplier_layout as ML
    lay = json.load(open(LAYOUT_JSON))
    runs = lay["strays"]["runs"]
    ref_free = [r for r in runs if r["tag"] == "layout, C3-C6, free" and abs(r["cl_pF"] - 180.0) < 1e-6][0]
    ref_cl = [r for r in runs if r["tag"] == "layout, C3-C6, clamped" and abs(r["cl_pF"] - 180.0) < 1e-6][0]
    new = {k: v * 1e-12 for k, v in cs["deck_strays_pF"].items()}
    cp0 = {k: v * 1e-12 for k, v in cs["cp_layout_pF"].items()}
    cp1 = {k: v * 1e-12 for k, v in cs["cp_mounts_pF"].items()}
    scale = cs["Ca"]["with_mounts_pF"] / cs["Ca"]["laid_out_pF"]
    n_cl = ref_cl["n_cyc"]
    jobs = [dict(cl=ML.CL_PICK, strays=new, cp=cp0, n_cyc=40, clamp=False, fit_from=10, tag="layout, free"),
            dict(cl=ML.CL_PICK, strays=new, cp=cp1, n_cyc=40, clamp=False, fit_from=10, ca_scale=scale, tag="mounts, free"),
            dict(cl=ML.CL_PICK, strays=new, cp=cp0, n_cyc=n_cl, tag="layout, clamped"),
            dict(cl=ML.CL_PICK, strays=new, cp=cp1, n_cyc=n_cl, ca_scale=scale, tag="mounts, clamped")]
    with Pool(procs) as p:
        res = p.map(_run, jobs)
    for _ in range(2):
        redo = [i for i, q in enumerate(res) if q.get("done") and q["job"].get("clamp", True) and not q.get("settled")]
        if not redo:
            break
        with Pool(procs) as p:
            again = p.map(_run, [dict(res[i]["job"], n_cyc=2 * res[i]["job"]["n_cyc"]) for i in redo])
        for i, q in zip(redo, again):
            res[i] = q
    out = {}
    for q in res:
        j = q["job"]
        out[j["tag"]] = dict(z=q.get("z"), V_A_kV=q.get("V_A_kV"), V_B_kV=q.get("V_B_kV"), settled=q.get("settled"),
                             E_null_kV_cm=q.get("E_null_kV_cm"), n_cyc=j["n_cyc"], run_s=q.get("run_s"))
        log(f"  {j['tag']:16s} z {q.get('z', float('nan')):.5f}" + (f", rings {q['V_A_kV']:+.3f} / {q['V_B_kV']:+.3f} kV, "
                                                                   f"settled {q['settled']}" if q.get("V_A_kV") is not None else "")
            + f" ({q.get('run_s', 0):.0f} s)")
    g_free = abs(out["layout, free"]["z"] - ref_free["z"]) < 1e-6
    g_cl = abs(out["layout, clamped"]["V_B_kV"] - ref_cl["V_B_kV"]) < 1e-3
    out["gate"] = dict(z_free=out["layout, free"]["z"], z_free_layout=ref_free["z"], rings=out["layout, clamped"]["V_B_kV"],
                       rings_layout=ref_cl["V_B_kV"], ok=bool(g_free and g_cl))
    out["dz_free"] = out["mounts, free"]["z"] - out["layout, free"]["z"]
    out["d_rings_kV"] = out["mounts, clamped"]["V_B_kV"] - out["layout, clamped"]["V_B_kV"]
    out["ca_scale"] = scale
    return out


# ---------------------------------------------------------------------------------------------------- 6. the shafts
def shafts(log):
    """the drawn solids (sim/tube_geometry.py LayoutMachine) without and with the mounts: the masses each body gains,
    the new parts' masses, and the two bodies' modes and gap change (sim/shaft_bearings.py two_body, d 25 and 30, the
    stiff seat and the record's G10 spider)."""
    import bridge_ring_bearings as BRB
    import shaft_bearings as SB
    out, by = {}, {}
    for key, mounts in (("layout", False), ("mounts", True)):
        lad, parts, m = BRB.solids_parts(log, mounts=mounts)
        by[key] = {p_["name"]: p_ for p_ in parts}
        rows = []
        for d in (25.0, 30.0):
            for kb in (SB.K_BEARING, BRB.K_REAL):
                r = SB.two_body(lad, parts, d, "coupler", k_b=kb, k_mag=2e5)
                rows.append(dict(BRB.row_of(r, kb, d), ok=bool(r["f1_Hz"] >= 3 * SB.F_REL_HZ
                                                                and max(abs(x) for x in r["gap_change_um"]) <= 50.0)))
        out[key] = dict(rows=rows, m_rotor_kg=rows[0]["m_rotor_kg"], m_counter_rotor_kg=rows[0]["m_counter_rotor_kg"],
                        n_solids=len(parts))
        f1s = ", ".join("%.1f" % r_["f1_Hz"] for r_ in rows)
        log(f"  {key}: {len(parts)} solids; rotor {rows[0]['m_rotor_kg']:.2f} kg, counter-rotor "
            f"{rows[0]['m_counter_rotor_kg']:.2f} kg; f1 {f1s} Hz")
    new = sorted(set(by["mounts"]) - set(by["layout"]))
    gone = sorted(set(by["layout"]) - set(by["mounts"]))
    changed = sorted(n for n in set(by["mounts"]) & set(by["layout"]) if abs(by["mounts"][n]["kg"] - by["layout"][n]["kg"]) > 1e-6)
    grp = {}
    for n in new:
        p_ = by["mounts"][n]
        k = (p_["body"], p_["material"])
        g_ = grp.setdefault(k, dict(n=0, kg=0.0))
        g_["n"] += 1; g_["kg"] += p_["kg"]
    out["new_parts"] = [dict(body=b, material=mt, n=v["n"], kg=v["kg"]) for (b, mt), v in sorted(grp.items())]
    out["changed_parts"] = {n: dict(kg_layout=by["layout"][n]["kg"], kg_mounts=by["mounts"][n]["kg"]) for n in changed}
    out["gone_parts"] = gone
    out["d_rotor_kg"] = out["mounts"]["m_rotor_kg"] - out["layout"]["m_rotor_kg"]
    out["d_counter_rotor_kg"] = out["mounts"]["m_counter_rotor_kg"] - out["layout"]["m_counter_rotor_kg"]
    out["criterion_f1_Hz"] = 3 * SB.F_REL_HZ
    out["ok"] = bool(all(r["ok"] for r in out["mounts"]["rows"]))
    return out


# ---------------------------------------------------------------------------------------------------- the figure
def figure(res):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.patches import Rectangle, Circle, Polygon
    INK, INK2, GRID = "#1d1d1f", "#52514e", "#d9d8d3"
    C_N1, C_N2, C_REF, C_INS = "#2a78d6", "#eb6834", "#7d7d7d", "#c9b88a"
    pl = res["placement"]
    fig = plt.figure(figsize=(15.0, 9.4))
    # (a) the half-section through the column and the vane stack at a node-1 post (left) and a node-2 post (right)
    for k, (comb, title) in enumerate((("1", "(a) at a node-1 post (r 35)"), ("2", "(b) at a node-2 post (r 35)"))):
        ax = fig.add_axes((0.045 + 0.29 * k, 0.385, 0.26, 0.545))
        for n, q in pl["plates"].items():
            col = C_N1 if q["node"] == "1" else C_N2
            r0 = 27.0 if q["node"] == comb else 50.0
            ax.add_patch(Rectangle((r0, q["h0"]), 150.0 - r0, q["h1"] - q["h0"], fc=col, ec="none"))
            ax.text(152.0, 0.5 * (q["h0"] + q["h1"]), n, fontsize=6.5, va="center", color=INK2)
        for q in pl["rotor_vanes"]:
            ax.add_patch(Rectangle((20.5, q["h0"]), 129.5, q["h1"] - q["h0"], fc=C_N1, ec="none"))
        for q in pl["stator_vanes"]:
            ax.add_patch(Rectangle((50.0, q["h0"]), 132.0, q["h1"] - q["h0"], fc=C_REF, ec="none"))
        for q in pl["vane_spacers"]:
            ax.add_patch(Rectangle((20.5, q["h0"]), VSP_R1 - 20.5, q["h1"] - q["h0"], fc=C_INS, ec="none"))
        for q in pl["stator_spacers"]:
            ax.add_patch(Rectangle((ROD_R - 0.5 * SSP_D, q["h0"]), SSP_D, q["h1"] - q["h0"], fc=C_INS, ec="none"))
        er = pl["end_ring"]
        ax.add_patch(Rectangle((er["r0"], er["h0"]), er["r1"] - er["r0"], er["h1"] - er["h0"], fc=C_INS, ec="none"))
        spd = pl["spider"]
        ax.add_patch(Rectangle((26.0, spd["h0"]), spd["r1"] - 26.0, spd["h1"] - spd["h0"], fc=C_INS, ec="none"))
        ax.add_patch(Rectangle((CAGE_R0, 0.0), CAGE_R1 - CAGE_R0, pl["cage"]["h"], fc=C_INS, ec="none"))
        cd = pl["can_disc"]
        ax.add_patch(Rectangle((cd["r0"], cd["h0"]), cd["r1"] - cd["r0"], cd["h1"] - cd["h0"], fc=C_REF, ec="none"))
        ax.add_patch(Rectangle((46.0, 0.0), 2.0, 85.0, fc=C_REF, ec="none"))
        ax.add_patch(Rectangle((12.5, cd["h1"]), 8.0, 281.5 - cd["h1"], fc=C_INS, ec="none"))
        ax.add_patch(Rectangle((0.0, 0.0), 12.5, 300.0, fc="#b9bdc5", ec="none"))
        for q in (pl["posts_n1"] if comb == "1" else pl["posts_n2"]):
            col = C_N1 if comb == "1" else C_N2
            if q["kind"] == "standoff":
                col = "#e8e2d0"
            ax.add_patch(Rectangle((R_POST - 0.5 * (STANDOFF_D if q["kind"] == "standoff" else POST_D), q["h0"]),
                                   STANDOFF_D if q["kind"] == "standoff" else POST_D, q["h1"] - q["h0"], fc=col,
                                   ec=INK if q["kind"] == "standoff" else "none", lw=0.4))
        ax.plot([ROD_R, ROD_R], [pl["rods"]["h0"], pl["rods"]["h1"]], color="#6d5a2f", lw=1.6)
        if comb == "1":                          # the riser: in at h 101.5, up the bore to its post under Ca_05
            h_in = 0.5 * (78.0 + 117.0) + 4.0
            ax.plot([132.0, R_POST, R_POST], [h_in, h_in, pl["riser_end_h"]], color=C_N1, lw=1.1, ls=(0, (3, 1.5)))
            ax.text(90.0, h_in - 2.0, "the riser", fontsize=7, color=C_N1, ha="center")
        ax.set_xlim(0, 192); ax.set_ylim(300, 80); ax.set_aspect("equal")
        ax.set_xlabel("r [mm]", fontsize=8.5, color=INK); ax.tick_params(labelsize=7.5, colors=INK2)
        if k == 0:
            ax.set_ylabel("h from the hub's centre [mm] (side A; side B its mirror)", fontsize=8.5, color=INK)
        for s_ in ("top", "right"):
            ax.spines[s_].set_visible(False)
        ax.set_title(title, fontsize=9.5, loc="left", color=INK)
    # (c) plan of the plates' tabs
    ax = fig.add_axes((0.64, 0.41, 0.33, 0.50))
    th = np.linspace(0, 2 * math.pi, 361)
    for r_ in (50.0, 150.0):
        ax.plot(r_ * np.cos(th), r_ * np.sin(th), color=INK2, lw=0.6)
    P = np.array(tab_outline())
    s_ = pl["sides"]["A"]
    for k, ths in enumerate((s_["theta_n1_deg"], s_["theta_n2_deg"])):
        for a in ths:
            c, s = math.cos(math.radians(a)), math.sin(math.radians(a))
            Q = P @ np.array([[c, s], [-s, c]])
            ax.add_patch(Polygon(Q, closed=True, fc=(C_N1, C_N2)[k], ec="none", alpha=0.85))
            ax.add_patch(Circle((R_POST * c, R_POST * s), 0.5 * POST_D, fc="white", ec=INK, lw=0.5))
    ax.add_patch(Circle((0, 0), 22.5, fc="#e8e2d0", ec=INK2, lw=0.5))
    a = math.radians(s_["theta_riser_deg"])
    ax.plot([R_POST * math.cos(a), 132.0 * math.cos(a)], [R_POST * math.sin(a), 132.0 * math.sin(a)], color=C_N1, lw=1.0,
            ls=(0, (3, 2)))
    ax.text(100 * math.cos(a) + 4, 100 * math.sin(a), "riser", fontsize=7, color=C_N1)
    for k, (ths, lab) in enumerate(((s_["theta_n1_deg"], "node-1 post"), (s_["theta_n2_deg"], "node-2 post"))):
        b = math.radians(ths[1])
        ax.annotate(lab, (R_POST * math.cos(b), R_POST * math.sin(b)), (95 * math.cos(b), 95 * math.sin(b)), fontsize=7,
                    color=(C_N1, C_N2)[k], ha="center", arrowprops=dict(arrowstyle="-", color=(C_N1, C_N2)[k], lw=0.6))
    ax.set_xlim(-160, 160); ax.set_ylim(-160, 160); ax.set_aspect("equal"); ax.axis("off")
    ax.set_title("(c) side A, plan: the node-1 tabs (blue) and the node-2 tabs (orange)\n    in the bore; the plates r 50-150",
                 fontsize=9.5, loc="left", color=INK)
    # (d) the corona margin against the post's distance
    ax = fig.add_axes((0.47, 0.07, 0.50, 0.25))
    f = res["fields"]
    g_ = [q["gap_mm"] for q in f["sweep_tab_crossing"]]
    mg = [q["margin"] for q in f["sweep_tab_crossing"]]
    ax.plot(g_, mg, color=C_N2, lw=2.0, marker="o", ms=5)
    for key, col, lab in (("C1_rims", C_REF, "the C1 rims (the record's)"), ("Ca_aligned_rims", C_N1, "the column's aligned rims")):
        ax.axhline(f[key]["margin"], color=col, lw=1.2, ls=(0, (4, 2)))
        ax.text(19.8, f[key]["margin"] + 0.012, lab, fontsize=7.5, color=col, ha="right")
    ax.axhline(1.0, color=INK2, lw=0.8)
    ax.text(19.8, 1.006, "onset at the peak (margin 1)", fontsize=7.5, color=INK2, ha="right")
    gw = f["tab_crossing"]["gap_mm"]
    ax.axvline(gw, color=GRID, lw=1.0)
    ax.text(gw + 0.25, 1.40, f"as drawn: {gw:.0f} mm\nedge {f['tab_crossing']['margin']:.3f} (wall)\n"
            f"{f['hole_edge']['margin']:.3f} (round the post)\npost {f['post']['margin']:.2f}", fontsize=7.5, color=INK, va="top")
    ax.set_xlim(4, 20.5); ax.set_ylim(0.9, 1.5)
    ax.set_xlabel("the post's surface to the other comb's bore edge [mm]", fontsize=8.5, color=INK)
    ax.set_ylabel("corona onset / peak field, handled surface (Peek, m 0.85)", fontsize=8.5, color=INK)
    ax.tick_params(labelsize=7.5, colors=INK2)
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)
    ax.grid(True, color=GRID, lw=0.5)
    ax.set_title(f"(d) a bore edge under the other comb's tab, {f['peaks_kV']['Ca']:.1f} kV peak", fontsize=9.5, loc="left",
                 color=INK)
    # the legend for (a) / (b)
    lx = fig.add_axes((0.045, 0.04, 0.38, 0.27)); lx.axis("off")
    items = [(C_N1, "node 1 (4): Ca's node-1 comb, the rotor vanes, its posts"), (C_N2, "node 2 (3): Ca's node-2 comb, its posts"),
             ("#e8e2d0", "glazed steatite standoffs; the PTFE cover"), (C_REF, "REF: the stator vanes, the can"),
             (C_INS, "G10: spacer rings and tubes, the end ring, the spider, the cage"), ("#6d5a2f", "glass-epoxy tie rods M8"),
             (None, "(a), (b): schematic half-sections, side A; the tie rods drawn at their radius r 173")]
    for i, (c, t) in enumerate(items):
        if c:
            lx.add_patch(Rectangle((0.0, 0.9 - i * 0.13), 0.06, 0.08, fc=c, ec="none", transform=lx.transAxes))
        lx.text(0.09 if c else 0.0, 0.94 - i * 0.13, t, fontsize=7.8, color=INK if c else INK2, transform=lx.transAxes,
                va="center")
    fig.suptitle("The doubler's capacitors as built (PROPOSED): the Ca / Cb combs on their own posts in the bore, the vanes "
                 "on spacers; the field where a tab crosses an edge (sim/doubler_caps.py)", fontsize=11.5, x=0.01, ha="left",
                 color=INK)
    fig.savefig(FIG, dpi=130)
    plt.close(fig)
    return os.path.relpath(FIG, ROOT)


# ---------------------------------------------------------------------------------------------------- main
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--procs", type=int, default=4)
    ap.add_argument("--only", nargs="*", default=["rules", "fields", "strays", "circuit", "shafts"])
    a = ap.parse_args()
    log = lambda s: print(s, flush=True)
    t0 = time.time()
    old = json.load(open(OUT_JSON)) if os.path.exists(OUT_JSON) else {}
    lay = json.load(open(LAYOUT_JSON))
    V = lay["volts"]
    out = dict(old, note=__doc__.split("\n\n")[0], sources=SRC, tags="CONVENTIONS.md §1", status="PROPOSED")
    log("1. the placement")
    pl = placement(lay)
    out["placement"] = pl
    for s_ in "AB":
        q = pl["sides"][s_]
        log(f"  side {s_}: the riser at {q['theta_riser_deg']:.1f} deg; node-{q['node_1']} posts "
            f"{', '.join(f'{x:.1f}' for x in q['theta_n1_deg'])}; node-{q['node_2']} posts "
            f"{', '.join(f'{x:.1f}' for x in q['theta_n2_deg'])}")
    if "rules" in a.only or "rules" not in old:
        log("2. the HV rules")
        out["rules"] = rules(V, pl)
        for r in out["rules"]["rows"]:
            log(f"  {r['interface'][:86]:86s} {r['pair']:5s} {r['U_pk_kV']:5.2f} kV: need {r['need_mm']} mm, "
                f"available {r['available_mm']:.1f}  {r['ok']}")
        log(f"  no support touches two adjacent plates: {out['rules']['no_support_touches_two_adjacent']}")
    if "fields" in a.only or "fields" not in old:
        log("3. the fields")
        out["fields"] = fields(V, log)
    if "strays" in a.only or "strays" not in old:
        log("4. Ca and the strays")
        out["ca_strays"] = ca_and_strays(pl, out["fields"])
        c = out["ca_strays"]
        log(f"  Ca {c['Ca']['laid_out_pF']:.1f} -> {c['Ca']['with_mounts_pF']:.1f} pF ({c['Ca']['ratio_to_C_max']:.4f} C_max); "
            f"node 1 / 4 {c['strays']['d_node_1_pF']:+.2f} pF, node 2 / 3 {c['strays']['d_node_2_pF']:+.2f} pF")
    if "circuit" in a.only or "circuit" not in old:
        log("5. the circuit")
        out["circuit"] = circuit(out["ca_strays"], a.procs, log)
    if "shafts" in a.only or "shafts" not in old:
        log("6. the masses and the shafts")
        out["shafts"] = shafts(log)
    g = dict(G1_rules=out["rules"]["ok"], G2_fields=out["fields"]["ok"],
             G3_Ca=bool(out["ca_strays"]["Ca"]["with_mounts_pF"] >= out["ca_strays"]["Ca"]["laid_out_pF"] - 1e-9),
             G4_circuit_gate=out["circuit"]["gate"]["ok"], G4_pumps=bool(out["circuit"]["mounts, free"]["z"] > 1.0),
             G5_shafts=out["shafts"]["ok"])
    out["gates"] = g
    out["figure"] = figure(out)
    out["run_s"] = round(time.time() - t0)
    json.dump(out, open(OUT_JSON, "w"), indent=1, default=float)
    log(f"gates {g}")
    log(f"wrote {os.path.relpath(OUT_JSON, ROOT)} and {out['figure']} ({out['run_s']} s)")


if __name__ == "__main__":
    main()
