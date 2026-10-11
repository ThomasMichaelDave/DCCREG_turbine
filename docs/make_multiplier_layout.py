"""docs/make_multiplier_layout.py -- writes docs/figures/multiplier-layout.png: the mechanical layout of the multiplier
stacked into the doubler (PROPOSED), every dimension and check from sim/multiplier_layout_results.json:
  (a) the machine's half-section through the shaft, side B on top: the reluctance sections and end bearings as the
      record; each side's vane stack against its Ca|reluctance bearing, the column (Ca / Cb) toward the hub, the deck
      round the grounded can over the hub; no hub-face bearing; node 1's riser, the node-2 tap, the cross nets, the
      rings' leads and the magnetic pump's low-voltage path through the shaft;
  (b) side A's central bay at twice the scale, with the gaps that set it;
  (c) deck A in plan: the sticks along the outer lane, C3 / C6 / C8 and the clamp string on the inner, Csa beyond the
      chain's end; each junction's net and its swing; deck B is its mirror;
  (d) the stack, the parts and the checks.
Usage: python3 docs/make_multiplier_layout.py
"""
import json
import math
import os

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt                                   # noqa: E402
from matplotlib.patches import Rectangle, Circle, Wedge, Polygon, FancyBboxPatch    # noqa: E402
import numpy as np                                                # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
RES = json.load(open(os.path.join(ROOT, "sim", "multiplier_layout_results.json")))
IMR = json.load(open(os.path.join(ROOT, "sim", "integrated_multiplier_results.json")))
HUB = json.load(open(os.path.join(ROOT, "presets", "hub-locked.json")))
OUT = os.path.join(HERE, "figures", "multiplier-layout.png")

# the record's palette (sim/tube_geometry.py COL), and the new parts'
rgb = lambda t: "#%02x%02x%02x" % tuple(int(round(255 * x)) for x in t)
C = dict(stator=rgb((0.78, 0.57, 0.92)), rotor=rgb((0.49, 0.82, 1.0)), plate1=rgb((0.27, 0.77, 0.42)),
         plate2=rgb((0.18, 0.54, 0.29)), g10=rgb((0.55, 0.6, 0.5)), steel=rgb((0.42, 0.45, 0.5)),
         glass=rgb((0.75, 0.85, 0.9)), sife=rgb((0.33, 0.35, 0.4)), cu=rgb((0.8, 0.47, 0.22)),
         peek=rgb((0.86, 0.80, 0.62)), mnzn=rgb((0.30, 0.27, 0.25)), ring=rgb((0.85, 0.36, 0.12)),
         can="#b4bac4", pot="#ece6d2", body="#3b3b3b", cap="#c9b48a", clamp="#8e6fb5", deckplate="#a9b39a")
INK, INK2, DIM = "#1d1d1f", "#52514e", "#3a4a66"
NEG, POS, REFC = "#2166ac", "#b2182b", "#555555"
st = RES["stack"]
EL = st["elements"]
HC = st["h_end_mm"]                                              # the hub's centre in machine z (bottom end z = 0)
DK = RES["decks"]
V = RES["volts"]["V_kV"]


def zr(h, side):
    """machine z of a point h from the hub's centre on side A (below) or B (above)."""
    return HC - h if side == "A" else HC + h


def rect(ax, r0, r1, h0, h1, side, fc, ec=INK, lw=0.35, hatch=None, alpha=1.0, z=2):
    z0, z1 = sorted((zr(h0, side), zr(h1, side)))
    ax.add_patch(Rectangle((r0, z0), r1 - r0, z1 - z0, fc=fc, ec=ec, lw=lw, hatch=hatch, alpha=alpha, zorder=z))


def label(ax, xy, xytext, text, fs=7.0, ha="left", color=INK2):
    ax.annotate(text, xy, xytext, fontsize=fs, color=color, ha=ha, va="center", zorder=12,
                arrowprops=dict(arrowstyle="-", lw=0.4, color=color, shrinkA=0, shrinkB=0))


def dim_z(ax, x, za, zb, text, fs=6.6, side="right", color=DIM):
    ax.annotate("", (x, za), (x, zb), arrowprops=dict(arrowstyle="<|-|>", lw=0.5, color=color, mutation_scale=5,
                                                      shrinkA=0, shrinkB=0), zorder=11)
    ax.text(x + (2.5 if side == "right" else -2.5), 0.5 * (za + zb), text, fontsize=fs, color=color,
            ha="left" if side == "right" else "right", va="center", rotation=0, zorder=11,
            bbox=dict(fc="white", ec="none", pad=0.15, alpha=0.85))


def net_color(n):
    if n == "0":
        return REFC
    m = V[n]["mean"] if n in V else 0.0
    return NEG if m < 0 else POS


def net_text(n):
    if n == "0":
        return "REF"
    q = V.get(n)
    return f"{n}  {q['min']:+.1f}…{q['max']:+.1f}" if q and q["max"] - q["min"] > 0.05 else f"{n}  {q['mean']:+.2f} kV"


# ----------------------------------------------------------------------------------------------- the hub (locked)
def hub(ax, side, detail=False):
    """the locked hub's outline: retainer, coupler, flange, vessel, rings, AH core and coil (presets/hub-locked.json)."""
    ah, ves = HUB["AH"]["value"], HUB["vessel"]["value"]
    R_v = 0.5 * ves["od_mm"]
    sg = -1 if side == "A" else 1
    for e in EL:
        if e["kind"] in ("retainer", "coupler", "flange"):
            fc = {"retainer": C["peek"], "coupler": C["g10"], "flange": C["steel"]}[e["kind"]]
            rect(ax, e["r0"], e["r1"], e["h0"], e["h1"], side, fc, lw=0.3, z=3)
    th = np.radians(np.linspace(0, 90, 60))
    ax.add_patch(Polygon([(0, HC)] + [(R_v * math.sin(t), HC + sg * R_v * math.cos(t)) for t in th], closed=True,
                         fc=C["glass"], ec=INK, lw=0.35, zorder=4))
    ax.add_patch(Polygon([(0, HC)] + [((R_v - 1.5) * math.sin(t), HC + sg * (R_v - 1.5) * math.cos(t)) for t in th],
                         closed=True, fc="white", ec="none", zorder=4))
    rg = HUB["rings"]["value"]
    tb = np.radians(np.linspace(rg["polar_edge_deg"], rg["equatorial_edge_deg"], 30))
    pts = [((R_v + 0.0) * math.sin(t), HC + sg * R_v * math.cos(t)) for t in tb]
    pts += [((R_v + 1.2) * math.sin(t), HC + sg * (R_v + 1.2) * math.cos(t)) for t in tb[::-1]]
    ax.add_patch(Polygon(pts, closed=True, fc=C["ring"], ec="none", zorder=5))
    c0, c1 = ah["core"]["absz_mm"]
    rect(ax, 0.0, 0.5 * ah["core"]["d_mm"], c0, c1, side, C["mnzn"], lw=0.3, z=5)
    k0, k1 = ah["coil"]["absz_mm"]
    rect(ax, ah["coil"]["r_mm"][0], ah["coil"]["r_mm"][1], k0, k1, side, C["cu"], lw=0.3, z=5)


# ----------------------------------------------------------------------------------------------- one side's stack
def side_stack(ax, side, leads=True):
    for e in EL:
        k = e["kind"]
        if k in ("retainer", "coupler", "flange"):
            continue
        if k == "Ca plate":
            rect(ax, e["r0"], e["r1"], e["h0"], e["h1"], side, C["plate1"] if e["node"] == "1" else C["plate2"], lw=0.3)
        elif k == "C1 vane":
            rect(ax, e["r0"], e["r1"], e["h0"], e["h1"], side, C["rotor"] if e["body"] == "rotor" else C["stator"], lw=0.3)
        elif k in ("bearing", "end bearing"):
            rect(ax, e["r0"], e["r1"], e["h0"], e["h1"], side, C["steel"], lw=0.3, z=3)
        elif k == "spider":
            rect(ax, e["r0"], e["r1"], e["h0"], e["h1"], side, C["g10"], lw=0.3)
        elif k == "sleeve":
            rect(ax, e["r0"], e["r1"], e["h0"], e["h1"], side, C["g10"], lw=0.25)
        elif k == "cage":
            rect(ax, e["r0"], e["r1"], e["h0"], e["h1"], side, C["g10"], lw=0.25)
        elif k == "can":
            rect(ax, e["r0"], e["r1"], e["h0"], e["h1"], side, C["can"], lw=0.3, z=3)
        elif k == "can disc":
            rect(ax, e["r0"], e["r1"], e["h0"], e["h1"], side, C["can"], lw=0.3, z=3)
        elif k == "deck plate":
            rect(ax, e["r0"], e["r1"], e["h0"], e["h1"], side, C["deckplate"], lw=0.3)
        elif k == "deck parts":
            rect(ax, e["r0"], e["r1"], e["h0"], e["h1"], side, C["pot"], ec="#8a8270", lw=0.4, z=2)
            # the two lanes in section: the outer lane's sticks, the inner lane's capacitors and clamp module
            zo = DK["zone"]["parts_absz_mm"]
            r_o, r_i = DK["lanes"]["outer_r_mm"], DK["lanes"]["inner_r_mm"]
            for rc, rr, hh, fc in ((r_o, 4.0, 4.0, C["body"]), (r_i, 15.0, 11.0, C["cap"])):
                hm = 0.5 * (zo[0] + zo[1])
                rect(ax, rc - rr, rc + rr, hm - hh, hm + hh, side, fc, lw=0.2, z=3)
        elif k == "shaft":
            rect(ax, e["r0"], e["r1"], e["h0"], e["h1"], side, C["steel"], lw=0.3, z=3)
    # the reluctance section and the end bearing (the record's elements)
    for e in st["record_reluctance"]:
        if (side == "A") != (e["z1"] < HC):
            continue
        z0, z1 = e["z0"], e["z1"]
        k = e["kind"]
        if k == "w utron":
            ax.add_patch(Rectangle((e["r0"], e["zs0"]), e["r1"] - e["r0"], e["zs1"] - e["zs0"], fc=C["sife"], ec=INK,
                                   lw=0.3, zorder=2))
            ax.add_patch(Rectangle((e["r0"] - 6, z0), 6, z1 - z0, fc=C["cu"], ec="none", zorder=2))
        elif k == "w disc":
            ax.add_patch(Rectangle((e["r0"], z0), e["r1"] - e["r0"], z1 - z0, fc=C["g10"], ec=INK, lw=0.3, zorder=2))
        elif k == "w bridge":
            ax.add_patch(Rectangle((e["r0"], z0), e["r1"] - e["r0"], z1 - z0, fc=C["sife"], ec=INK, lw=0.3, zorder=3))
        elif k == "w ring":
            ax.add_patch(Rectangle((e["r0"], z0), e["r1"] - e["r0"], z1 - z0, fc=C["g10"], ec=INK, lw=0.3, zorder=2))
        elif k == "w flange":
            ax.add_patch(Rectangle((e["r0"], z0), e["r1"] - e["r0"], z1 - z0, fc=C["g10"], ec=INK, lw=0.3, zorder=2))
        elif k == "bearing":
            ax.add_patch(Rectangle((e["r0"], z0), 26.0 - e["r0"], z1 - z0, fc=C["steel"], ec=INK, lw=0.3, zorder=3))
            ax.add_patch(Rectangle((26.0, 0.5 * (z0 + z1) - 4), e["r1"] - 26.0, 8, fc=C["g10"], ec=INK, lw=0.3, zorder=2))
    hub(ax, side)
    if not leads:
        return
    sg = -1 if side == "A" else 1
    r_o = DK["lanes"]["outer_r_mm"]
    h_par, h_col = st["h_parts_mm"], st["h_col_mm"]
    hv0 = st["h_vanes"][0]
    c1 = NEG if side == "A" else POS
    c2 = POS if side == "A" else NEG
    # node 1's riser: from the hub-end rotor vane's ring up the column's bore, out to node 1's junction on the deck
    hr = 0.5 * (st["h_parts_mm"] + h_col) + 4
    xs, hs = [32, 35, 35, r_o - 6, r_o - 6], [hv0 + 1.5, hv0 - 2, hr, hr, h_par]
    ax.plot(xs, [zr(h, side) for h in hs], color=c1, lw=1.1, zorder=9, solid_capstyle="round")
    # the node-2 tap: the column's node-2 plate down to node 2's junction
    ax.plot([r_o + 6, r_o + 6], [zr(h_col, side), zr(h_par, side)], color=c2, lw=1.1, zorder=9)
    # the ring's lead: from its equatorial bead along the normal through the PEEK and the coupler, along the coupler,
    # out through the can's wall to the deck
    ves = HUB["vessel"]["value"]
    rg = HUB["rings"]["value"]
    te = math.radians(rg["equatorial_edge_deg"])
    R_b = 0.5 * ves["od_mm"] + 1.0
    rb, hb = R_b * math.sin(te), R_b * math.cos(te)
    r_c = 33.0
    hc = hb + (r_c - rb) / math.tan(te)
    hl = 0.5 * (DK["zone"]["parts_absz_mm"][0] + DK["zone"]["parts_absz_mm"][1])
    ax.plot([rb, r_c, r_c + 2, r_c + 2, 112], [zr(hb, side), zr(hc, side), zr(hc, side), zr(hl, side), zr(hl, side)],
            color=C["ring"], lw=1.2, zorder=9)


# ----------------------------------------------------------------------------------------------- (a) the machine
def panel_section(ax):
    for s_ in "AB":
        side_stack(ax, s_)
    L = st["L_mm"]
    # the cross nets between the decks, the LV path in the shaft, the REF link
    r_o = DK["lanes"]["outer_r_mm"]
    z_d = DK["zone"]["plate_absz_mm"][0]
    ax.plot([r_o, r_o], [HC - z_d, HC + z_d], color="#7a3e9d", lw=1.4, zorder=9)
    hb = st["h_bearing_mm"]
    for s_ in "AB":
        ax.plot([2.0, 2.0], [zr(80, s_), zr(hb + 40, s_)], color="#d68910", lw=1.2, ls=(0, (3, 2)), zorder=10)
        ax.plot([2.0, 30.0], [zr(hb + 40, s_)] * 2, color="#d68910", lw=1.2, ls=(0, (3, 2)), zorder=10)
    ax.set_xlim(-6, 330)
    ax.set_ylim(-20, L + 25)
    ax.set_aspect("equal")
    ax.axvline(0, color="#999", lw=0.5, ls="-.", zorder=1)
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)
    ax.set_xlabel("r (mm)", fontsize=7.5)
    ax.set_ylabel("z (mm), from the bottom end (side A below)", fontsize=7.5)
    ax.tick_params(labelsize=6.5)
    ax.set_xticks([0, 50, 100, 150])
    # labels, side B (top) then the hub, then side A
    hv0, hv1 = st["h_vanes"]
    hc = st["h_col_mm"]
    x_t = 182
    lab = [
        (HC + hb + 100, "reluctance B as the record: 3 wound\nutrons (rotor), 6 bridges (counter-rotor)"),
        (HC + hb, f"Ca|reluctance bearing + spider (counter-rotor), z {HC + hb:.0f}"),
        (HC + 0.5 * (hv0 + hv1), "C2: 6 rotor + 6 stator vanes, the record's,\nits ends swapped: a rotor vane (node 4) at\nthe hub end, a stator vane (REF) outward;\nIN PHASE with C1"),
        (HC + hc + 24, "Cb: the record's 6 plates, 481.6 pF;\nnode 3 toward the deck, node 4 outward"),
        (HC + 57, "deck B round the can: D2, D4, D6, D7, D9, D10,\nC4, C5, C7, Csb, Z4 (each potted)"),
        (HC, "the hub as locked, inside a grounded can (r 48,\n|z| <= 85): the field at the null x "
             f"{RES['hub']['k_ratio']:.4f}"),
        (HC - 57, "deck A: D1, D3, D5, D8, D11, D12, C3, C6, C8,\nCsa, Z1; l1 / r1 cross to deck B (purple)"),
        (HC - hc - 24, "Ca: node 2 toward the deck, node 1 outward"),
        (HC - 0.5 * (hv0 + hv1), "C1: as C2, mirrored"),
        (HC - hb, f"Ca|reluctance bearing, z {HC - hb:.0f}: the REF link"),
        (HC - hb - 100, "reluctance A, as the record"),
        (HC - hb - 175, "end bearing (frame)"), (HC + hb + 175, "end bearing (frame)"),
    ]
    for z, t in lab:
        ax.text(x_t, z, t, fontsize=6.6, color=INK2, va="center", ha="left", zorder=12)
        ax.plot([166, x_t - 2], [z, z], color="#bbb", lw=0.4, zorder=1)
    dim_z(ax, 172, 0, L, "", side="right")
    ax.text(172, L + 14, f"{L:.0f} mm overall (the record 940)", fontsize=6.8, color=DIM, ha="center", va="bottom")
    ax.set_title("(a) the machine through the shaft, side B above: no hub-face bearings, the counter-rotor\non the "
                 "two Ca|reluctance bearings; amber dashed: the magnetic pump's LV leads in the shaft", fontsize=8.2,
                 loc="left", color=INK)


# ----------------------------------------------------------------------------------------------- (b) side A, close
def panel_zoom(ax):
    side_stack(ax, "A")
    r_o = DK["lanes"]["outer_r_mm"]
    z_d = DK["zone"]["plate_absz_mm"][0]
    ax.plot([r_o, r_o], [HC - z_d, HC + 4], color="#7a3e9d", lw=1.4, zorder=9)
    hb = st["h_bearing_mm"]
    ax.plot([2.0, 2.0], [zr(80, "A"), zr(hb + 30, "A")], color="#d68910", lw=1.2, ls=(0, (3, 2)), zorder=10)
    ax.set_xlim(-2, 345)
    ax.set_ylim(HC - hb - 30, HC + 6)
    ax.set_aspect("equal")
    ax.axhline(HC, color="#999", lw=0.5, ls="-.")
    ax.axvline(0, color="#999", lw=0.5, ls="-.")
    ax.tick_params(labelsize=6.5)
    ax.set_xlabel("r (mm)", fontsize=7.5)
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)
    hv0, hv1 = st["h_vanes"]
    hcol, hpar = st["h_col_mm"], st["h_parts_mm"]
    zo = DK["zone"]
    # dimensions (|z| from the hub's centre), just outside the cage; the labels beyond them
    x = 172
    dim_z(ax, x, zr(0, "A"), zr(zo["plate_absz_mm"][0], "A"), f"|z| {zo['plate_absz_mm'][0]:.0f}: the deck's plate")
    dim_z(ax, x, zr(zo["parts_absz_mm"][0], "A"), zr(zo["parts_absz_mm"][1], "A"),
          f"the parts, {zo['parts_absz_mm'][1] - zo['parts_absz_mm'][0]:.0f} mm")
    dim_z(ax, x, zr(hpar, "A"), zr(hcol, "A"), f"{st['c_col_mm']} mm: node 2 vs\nring A's lead,\n"
          f"{st['c_col_pair']['pk']:.1f} kV at 1.5 x")
    dim_z(ax, x, zr(hcol, "A"), zr(hcol + 48, "A"), "Ca, 48 mm")
    dim_z(ax, x, zr(hv0, "A"), zr(hv1, "A"), "C1, 102 mm")
    dim_z(ax, x, zr(hv1, "A"), zr(hb, "A"), f"{hb - hv1:.0f} mm")
    ax.text(x + 3, zr(hb + 13, "A"), f"the Ca|reluctance bearing\nat |z| {hb:.0f} (the record 272)", fontsize=6.4,
            color=DIM, va="center")
    xt = 248
    lab = [(r_o, zr(14, "A"), zr(10, "A"), "l1, r1 to deck B"),
           (95, zr(57, "A"), zr(32, "A"), "ring A's lead, out\nthrough the can"),
           (47.0, zr(76, "A"), zr(58, "A"), "the can (Al, REF):\nr 46-48, |z| <= 85"),
           (r_o - 6, zr(hpar + 15, "A"), zr(86, "A"), "node 1's riser: PTFE\nHV wire at r 35 in\nthe column's bore"),
           (r_o + 6, zr(hcol - 12, "A"), zr(118, "A"), "the node-2 tap"),
           (21, zr(hv0 + 70, "A"), zr(hv0 + 60, "A"), "the sleeve: PTFE-\ncovered under the\ncolumn, sheds at\nits outer end"),
           (3, zr(hb - 30, "A"), zr(hb - 34, "A"), "the LV leads (AH\ncoils <-> utrons)\nin an 8 mm bore")]
    for xa, ya, yt, t in lab:
        label(ax, (xa, ya), (xt, yt), t, fs=6.4)
    ax.set_title("(b) side A's central bay, twice (a)'s scale: the gaps that set it", fontsize=8.2, loc="left", color=INK)


# ----------------------------------------------------------------------------------------------- (c) deck A, plan
def panel_plan(ax):
    d = DK["A"]
    ax.add_patch(Circle((0, 0), 166, fc="none", ec=C["g10"], lw=3.0, zorder=1))
    ax.add_patch(Wedge((0, 0), 150, 0, 360, width=100, fc="#f3f1e8", ec="#999", lw=0.4, zorder=1))
    ax.add_patch(Wedge((0, 0), 48, 0, 360, width=2, fc=C["can"], ec=INK, lw=0.4, zorder=2))
    ax.add_patch(Circle((0, 0), 33, fc=C["g10"], ec=INK, lw=0.3, zorder=2))
    ax.add_patch(Circle((0, 0), 12.5, fc=C["steel"], ec=INK, lw=0.3, zorder=3))
    P = DK["parts"]
    for q in d["parts"]:
        p = P[q["kind"]]
        pts = np.array(q["pts"])
        if q["orient"] == "up":
            ax.add_patch(Circle(q["centre"], q["rad"], fc=C["pot"], ec="#8a8270", lw=0.5, zorder=4))
            ax.add_patch(Circle(q["centre"], 0.5 * p["body_d"], fc=C["cap"], ec=INK, lw=0.4, zorder=5))
        else:
            w = 2 * q["rad"]
            ax.plot(pts[:, 0], pts[:, 1], color=C["pot"], lw=w * 0.95 * FIG_MM, solid_capstyle="round", zorder=4)
            bp = np.array(q["body_pts"])
            bw = (p.get("body_d") or p["body_w"])
            ax.plot(bp[:, 0], bp[:, 1], color=(C["clamp"] if q["kind"] == "clamp" else C["body"]),
                    lw=bw * FIG_MM, solid_capstyle="butt" if q["kind"] != "clamp" else "round", zorder=5)
        cx, cy = q["centre"]
        rr = math.hypot(cx, cy)
        off = 1.0 if q["orient"] == "up" else (1.0 + (11.0 if rr > 110 else -2.0) / rr)
        ax.text(cx * off, cy * off, q["name"], fontsize=6.4, ha="center", va="center", zorder=8, color="white"
                if q["orient"] != "up" else INK, weight="bold")
    for ld in d["leads"]:
        ax.plot([ld["a"][0], ld["b"][0]], [ld["a"][1], ld["b"][1]], color=net_color(ld["net"]), lw=0.9, zorder=6)
    for sp in d["straps"]:
        ax.plot([sp["a"][0], sp["b"][0]], [sp["a"][1], sp["b"][1]], color=REFC, lw=0.9, ls=(0, (2, 1.5)), zorder=6)
    for n, (x, y) in d["junctions"].items():
        nn = n.rstrip("'")
        ax.add_patch(Circle((x, y), 5.0, fc=net_color(nn), ec="white", lw=0.6, zorder=7))
        rr = math.hypot(x, y)
        ux, uy = x / rr, y / rr
        ax.text(x + 24 * ux, y + 24 * uy, n if nn == "0" else n, fontsize=6.4, ha="center", va="center", zorder=8,
                color=net_color(nn), weight="bold")
    # the cross nets, the riser, the tap, the ring lead
    for n, t in (("r1", "r1 -> deck B"), ("l1", "l1 -> deck B")):
        x, y = d["junctions"][n]
        ax.add_patch(Circle((x, y), 7.5, fc="none", ec="#7a3e9d", lw=1.2, zorder=8))
    ax.text(0, -182, "deck A from the hub's side; deck B is its mirror about the dash-dot line (its nets mirrored: 1 -> 4, "
            "2 -> 3,\nl1 <-> r1, r2 -> l2, xa -> xb, ea -> eb), so l1 and r1 (purple rings) run straight across between "
            "the decks", fontsize=6.2, ha="center", va="top", color=INK2)
    th = math.radians(DK["mirror_deg"])
    ax.plot([-170 * math.cos(th), 170 * math.cos(th)], [-170 * math.sin(th), 170 * math.sin(th)], color="#999", lw=0.5,
            ls="-.", zorder=0)
    x1, y1 = d["junctions"]["1"]
    ax.annotate("node 1's riser\nfrom the column", (x1, y1), (x1 + 60, y1 + 75), fontsize=6.2, color=NEG, ha="center",
                arrowprops=dict(arrowstyle="-", lw=0.4, color=NEG))
    x2, y2 = d["junctions"]["2"]
    ax.annotate("node 2's tap\nfrom the column", (x2, y2), (x2 - 95, y2 - 18), fontsize=6.2, color=POS, ha="center",
                arrowprops=dict(arrowstyle="-", lw=0.4, color=POS))
    cs = [q for q in d["parts"] if q["name"] == "Csa"][0]
    ax.annotate("ring A's lead\n(through the can)", cs["centre"], (cs["centre"][0] - 10, cs["centre"][1] + 55),
                fontsize=6.2, color=C["ring"], ha="center", arrowprops=dict(arrowstyle="-", lw=0.4, color=C["ring"]))
    ax.text(0, 0, "can\nr 48", fontsize=6.0, ha="center", va="center", color=INK2, zorder=9)
    ax.text(-118, 140, "cage r 162 (G10,\ncounter-rotor)", fontsize=6.0, color=INK2, ha="center")
    ax.set_xlim(-185, 185)
    ax.set_ylim(-205, 185)
    ax.set_aspect("equal")
    ax.axis("off")
    ck = DK["checks"]["A"]
    dm = st["deck_mass"]["A"]
    ax.set_title(f"(c) deck A in plan: {len(d['parts'])} parts potted, {ck['n_pairs']} pairs checked: all clear bare and "
                 f"potted;\n{dm['kg']:.2f} kg, its centroid {dm['offset_mm']:.0f} mm off the axis (balanced with the "
                 "rotor). Junctions coloured by sign (blue −, red +)", fontsize=8.2, loc="left", color=INK)


# ----------------------------------------------------------------------------------------------- (d) the tables
def panel_tables(ax):
    ax.axis("off")
    pk = IMR["pick"]["steady"]
    vr, vc = pk["VR_pk_kV"], pk["VC_kV"]
    # the parts per deck
    rows = [("deck A", "deck B", "part", "duty (as built)", "rating")]
    pairs = [("D1", "D2"), ("D3", "D4"), ("D5", "D6"), ("D8", "D7"), ("D11", "D9"), ("D12", "D10")]
    for a, b in pairs:
        rows.append((a, b, "HV stick, 2CL77 class", f"{max(vr[a], vr[b]):.2f} kV reverse", "20 kV (x2 rule)"))
    rows.append(("C3", "C4", "180 pF, class 1 / film", f"{max(abs(x) for x in vc['C3']):.1f} kV DC", "30 kV"))
    rows.append(("C6", "C5", "180 pF, class 1 / film", f"{max(abs(x) for x in vc['C6']):.1f} kV DC", "30 kV"))
    rows.append(("C8", "C7", "100 pF, class 1 / film", f"{max(abs(x) for x in vc['C8']):.1f} kV DC", "30 kV"))
    rows.append(("Csa", "Csb", "100 pF to REF", f"{max(abs(x) for x in vc['Csa']):.1f} kV DC", "40 kV"))
    nz = RES["strays"]["picks"]["clamp_parts"]["value"]
    rows.append(("Z1", "Z4", f"{nz} x 1.5KE200A, potted", f"V_op {IMR['V_op_kV'] * nz / 66:.2f} kV (66 in the record)",
                 "200 V per part"))
    rows.append(("R1, R3", "R2, R4", "22 kOhm surge", "6.6 kV step", ">= 15 kV, 1 W"))
    y = 1.0
    ax.text(0.0, y, "the parts, each potted (>= 8 mm of silicone)", fontsize=7.6, color=INK, weight="bold",
            transform=ax.transAxes, va="top")
    y -= 0.035
    xs = (0.0, 0.07, 0.14, 0.33, 0.47)
    for i, r in enumerate(rows):
        for x, t in zip(xs, r):
            ax.text(x, y, t, fontsize=6.6, color=INK if i else INK2, transform=ax.transAxes, va="top",
                    weight="bold" if i == 0 else "normal")
        y -= 0.027
    # the interfaces
    y -= 0.02
    ax.text(0.0, y, "the interfaces (IEC 60664-1 as sim/parts_first_cut.py; clearance at 1.5 x the peak, creepage x 1.25)",
            fontsize=7.6, color=INK, weight="bold", transform=ax.transAxes, va="top")
    y -= 0.035
    hdr = ("interface", "peak / rms kV", "clearance", "creepage PTFE / G10", "has", "")
    xs2 = (0.0, 0.42, 0.53, 0.62, 0.76, 0.83)
    for x, t in zip(xs2, hdr):
        ax.text(x, y, t, fontsize=6.4, color=INK2, transform=ax.transAxes, va="top", weight="bold")
    y -= 0.028
    short = {"Ca's plates": "Ca's plates, node 1 / 2 (6 mm air)", "the vanes": "the vanes, node 1 / REF (6 mm)"}
    for r in RES["interfaces"]:
        nm = r["interface"]
        for k, v in short.items():
            if nm.startswith(k):
                nm = v
        nm = nm.replace(" (PTFE HV wire, side by side between the decks)", "").replace(
            " (a PTFE bushing; the lead's insulation continuous)", " (bushing)")
        if len(nm) > 70:
            nm = nm[:68] + "…"
        av = r["available_mm"]
        ok = r["ok"]
        if isinstance(ok, dict):
            okt = "G10 " + ("ok" if ok["G10"] else "no") + ", PTFE " + ("ok" if ok["PTFE_or_silicone"] else "no")
        elif ok is None:
            okt = "insulated"
        else:
            okt = "ok" if ok else "SHORT"
        if r["kind"] == "gap":
            okt = f"x {r['breakdown_margin']:.2f} to breakdown"
        vals = (nm, f"{r['U_pk_kV']:.1f} / {r['U_rms_kV']:.1f}", f"{r['clearance_mm']:.0f} mm",
                f"{r['creepage_PTFE_mm']:.0f} / {r['creepage_G10_mm']:.0f} mm", "—" if av is None else f"{av:.0f} mm", okt)
        col = INK if ("no" not in okt and "SHORT" not in okt) else "#b03a2e"
        for x, t in zip(xs2, vals):
            ax.text(x, y, t, fontsize=6.1, color=col, transform=ax.transAxes, va="top")
        y -= 0.0235
    # the results
    sy = RES["strays"]
    runs = {r["tag"]: r for r in sy["runs"]}
    sh = RES["shaft"]
    picks = sy["picks"]
    y -= 0.02
    ax.text(0.0, y, "what it does", fontsize=7.6, color=INK, weight="bold", transform=ax.transAxes, va="top")
    y -= 0.034
    f1 = {(r["d_mm"], r["bridge_ring_bearings"], r["k_b_N_per_m"]): r for r in sh["rows"]}
    sel = lambda tag, cl=180.0: [r for r in sy["runs"] if r["tag"] == tag and r["cl_pF"] == cl][0]
    z_lay, z_std = sel("layout, C3-C6, free")["z"], sel("the study's strays, free")["z"]
    rings_lay = sel("layout, C3-C6, clamped")["V_B_kV"]
    rings_c3 = [r["V_B_kV"] for r in sy["runs"] if r["tag"] == "layout, C3-C6, clamped"]
    rings_c7 = [r["V_B_kV"] for r in sy["runs"] if r["tag"].startswith("layout, C7") and r["clamp"]]
    pz = picks["clamp_parts"]
    dpf = sy["deck_strays_pF"]
    lines = [
        f"length {st['L_mm']:.0f} mm (the record 940): +{st['dh_side_mm']:.0f} mm a side; the decks sit where the "
        "hub-face bearings were",
        f"strays (estimated, [RH]): node 1 / 4 +{sy['total_pF']['1']:.1f} pF, node 2 / 3 {sy['total_pF']['2']:+.1f} pF, "
        f"each new node {min(dpf.values()):.1f}-{max(dpf.values()):.1f} pF (the study assumed 24.5)",
        f"so the free gain z {z_lay:.4f} against the study's {z_std:.4f}, and the rings rise to ±{rings_lay:.2f} kV; "
        f"C3-C6 at 100-180 pF gives ±{min(rings_c3):.2f}-{max(rings_c3):.2f}, C7 / C8 at 47-68 pF "
        f"±{min(rings_c7):.2f}-{max(rings_c7):.2f}",
        f"so trim the clamps: strings of {pz['value']} parts (V_op {IMR['V_op_kV'] * pz['value'] / 66:.2f} kV) hold "
        f"the rings at ±{pz['rings_kV']:.2f} kV, the most within the record's ±{sy['rings_target_kV']:.2f}",
        f"shafts: without the hub-face bearings d 25 drops to {f1[(25.0, False, 2e8)]['f1_Hz']:.0f} Hz "
        f"(the record {f1[(25.0, False, 2e8)]['record']['f1_Hz']:.0f}), d 40 to {f1[(40.0, False, 2e8)]['f1_Hz']:.0f}; "
        f"with the bridge-ring bearings {f1[(25.0, True, 2e8)]['f1_Hz']:.0f} Hz (stiff) / "
        f"{f1[(25.0, True, 0.86e8)]['f1_Hz']:.0f} Hz (realistic seats); the criterion 60 Hz",
        f"the hub's field with the grounded can: x {RES['hub']['k_ratio']:.4f}; each ring's capacitance to REF "
        f"{RES['hub']['record box']['C_ring_ref_pF']:.2f} -> {RES['hub']['the can']['C_ring_ref_pF']:.2f} pF",
        "the sleeve (red rows): PTFE over it under the column (84 mm against 62); at its outer end two 12 mm PTFE sheds "
        "(17.5 + 4 x 12 = 65.5 mm) — the record's own open point, moved there",
    ]
    for t in lines:
        ax.text(0.0, y, "• " + t, fontsize=6.6, color=INK, transform=ax.transAxes, va="top")
        y -= 0.027
    ax.set_title("(d) the parts, the interfaces and what the layout does (sim/multiplier_layout_results.json)",
                 fontsize=8.2, loc="left", color=INK)


FIG_MM = 1.0


def main():
    global FIG_MM
    fig = plt.figure(figsize=(23.4, 16.5), facecolor="white")
    gs = fig.add_gridspec(2, 3, width_ratios=[1.02, 1.0, 1.25], height_ratios=[1.0, 0.86], left=0.035, right=0.99,
                          top=0.905, bottom=0.03, wspace=0.10, hspace=0.12)
    axa = fig.add_subplot(gs[:, 0])
    axb = fig.add_subplot(gs[0, 1])
    axc = fig.add_subplot(gs[0, 2])
    axd = fig.add_subplot(gs[1, 1:])
    panel_section(axa)
    panel_zoom(axb)
    # the plan's line widths in points per mm of the drawing
    fig.canvas.draw()
    bb = axc.get_position()
    w_in = bb.width * fig.get_figwidth()
    FIG_MM = w_in * 72.0 / 370.0
    panel_plan(axc)
    panel_tables(axd)
    fig.suptitle("The multiplier stacked into the doubler: the mechanical layout (PROPOSED, 2026-10-11) — Ca / Cb in "
                 "each side's column, every diode and the multiplier's capacitors on a potted deck round a grounded can "
                 "over the hub", fontsize=11.5, x=0.035, y=0.985, ha="left", color=INK)
    fig.text(0.035, 0.962, "the circuit: sim/integrated_multiplier.py's proposal at its pick (C1 / C2 in phase, chain 2 "
             "reversed, one ring stage per chain, C3-C6 180 pF); the layout and its checks: sim/multiplier_layout.py; "
             "the record's palette (sim/tube_geometry.py)", fontsize=7.4, color=INK2, ha="left")
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    fig.savefig(OUT, dpi=100)
    print(os.path.relpath(OUT, ROOT))


if __name__ == "__main__":
    main()
