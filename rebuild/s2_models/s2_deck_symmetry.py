"""rebuild/s2_models/s2_deck_symmetry.py -- the decks' symmetry along the axis: mirrored decks against decks balanced
by their own symmetry.

The designer (2026-10-16): "check if there is a way of creating more symmetry along the axis with regards to the
component placement on the decks, Either the A vs the B deck needs to be balanced/mirrored or every deck should be
perfectly balanced. We are dealing with 2 times two parts per deck so it's worth iterating an investigation, take your
time."

What balance means on the rotor [OC]: each deck's mass moment S = sum m r (in the plane) is its static imbalance; the
two decks sit at z = -h and +h, so their moments also make a couple C = sum m z r, which rocks the rotor about its
centre even when S_A + S_B = 0. Both vanish together only if each deck's own S is zero.

The two pairs per deck (s2_deck.py): two HV sticks (37 g each), the clamp string's two halves (217 g each) [RH: the
redesign's mass model]; four junction blocks (7.2 g); the leads and straps (the 3 mm PTFE wire, 21 g/m).
The variants:
  V0  the deck of record (s2_deck_bare_nocan_results.json): the sticks side by side, the halves placed to cancel them;
      deck B the mirror of deck A about a plane through the axis;
  V1  each deck two-fold symmetric: the sticks diametrically opposite, the halves diametrically opposite (a cross),
      every junction then opposite its twin; deck B is deck A turned 180 deg about the axis, which puts B's D4 anode
      over A's N2 and B's D2 cathode over A's N3, so the cross nets still run straight across [OC: the rotation maps
      D3's N3 end onto D1's N2 end]; the two cross wires then sit on opposite sides;
  V2  deck B the mirror of deck A about the midplane (the same angles): not possible with straight cross nets, since
      the part over A's D1 would be D2, whose end is N3, not N2 [OC]; recorded, not built.
V1 is searched [IR: 1 mm, 5 deg]: the sticks' lane R, the halves' radius and angle, the halves' orientations; each plan
passes every rule s2_deck.py applies (the potting, the bare clearance to the coupler, the junctions, the cross nets),
the smallest outer radius first, then the shortest midpoint lead.
Writes rebuild/s2_models/s2_deck_symmetry_results.json and s2-deck-symmetry.png.
Usage: python3 rebuild/s2_models/s2_deck_symmetry.py
"""
import json
import math
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "sim"))
sys.path.insert(0, HERE)
import multiplier_layout as ML  # noqa: E402
import s2_deck as SD  # noqa: E402

REC = json.load(open(os.path.join(HERE, "s2_deck_bare_nocan_results.json")))
V = REC["volts_design"]
SD.BARE_CAN, SD.NO_CAN = True, True                     # the deck of record's rules: bare to the coupler, no can
ML.CAN_R, ML.DECK_R0 = ML.CPL_R1, ML.CPL_R1 + 2.0
WIRE_G_PER_MM = (math.pi / 4 * 1.0 * 8.96 + math.pi / 4 * (9.0 - 1.0) * 2.2) * 1e-3   # g/mm, 1 mm Cu in 3 mm PTFE
Z_AX = {"stick": ML.DECK_Z0 + ML.DECK_T + 0.5 * ML.PART["stick"]["d"],                  # the axes' |z| [OC]
        "clamp_half": ML.DECK_Z0 + ML.DECK_T + 0.5 * ML.PART["clamp_half"]["h"], "junction": 48.0,
        "lead": 76.5, "strap": 60.0}


def pol(r, th):
    return np.array([r * math.cos(math.radians(th)), r * math.sin(math.radians(th))])


def stick(nm, nets, th, R, first_low):
    """a stick lying tangent at angle th; nets[0]'s end at the lower angle if first_low."""
    p = ML.PART["stick"]
    c = pol(R, th)
    tt = np.array([-math.sin(math.radians(th)), math.cos(math.radians(th))])
    rad = 0.5 * p["d"]
    lo_hi = lambda a: [c - a * tt, c + a * tt]                                   # noqa: E731
    pts, body, term = lo_hi(0.5 * p["l"] - rad), lo_hi(0.5 * p["body_l"]), lo_hi(0.5 * p["l"])
    if not first_low:
        pts, body, term = pts[::-1], body[::-1], term[::-1]
    return dict(name=nm, kind="stick", nets=tuple(nets), centre=c.tolist(), pts=[q.tolist() for q in pts],
                body_pts=[q.tolist() for q in body], rad=rad, orient="tan", terminals=[term[0].tolist(), term[1].tolist()])


def half(nm, nets, th_c, Rz, first_low):
    pz = ML.PART["clamp_half"]
    span = math.degrees((pz["l"] - pz["w"]) / Rz)
    th0 = th_c - 0.5 * span
    ths = list(np.linspace(th0, th0 + span, 7))
    ew = math.degrees(0.5 * pz["w"] / Rz)
    term = [pol(Rz, th0 - ew), pol(Rz, th0 + span + ew)]
    pts = [pol(Rz, t) for t in ths]
    if not first_low:
        pts, term = pts[::-1], term[::-1]
    return dict(name=nm, kind="clamp_half", nets=tuple(nets), centre=pol(Rz, th_c).tolist(), pts=[q.tolist() for q in pts],
                body_pts=[q.tolist() for q in pts], rad=0.5 * pz["w"], orient="arc",
                terminals=[term[0].tolist(), term[1].tolist()])


def plan_v1(R, alpha, Rz, beta, t_a, t_b):
    """deck A, two-fold symmetric: D1 at alpha (REF end low), D3 at alpha + 180 (its rotation: N1 end low, N3 high);
    Z1a at beta, Z1b at beta + 180; t_a / t_b: whether Z1a's N1 end / Z1b's m1 end lie at the lower angle."""
    d1 = stick("D1", ("0", "2"), alpha, R, True)
    d3 = stick("D3", ("3", "1"), alpha + 180.0, R, False)           # its N1 end at the lower angle (D1's REF end turned)
    za = half("Z1a", ("1", "m1"), beta, Rz, t_a)
    zb = half("Z1b", ("m1", "0"), beta + 180.0, Rz, t_b)
    J = {"2": d1["terminals"][1], "0": d1["terminals"][0], "3x": d3["terminals"][0], "1": d3["terminals"][1],
         "0z": zb["terminals"][1]}
    leads = [dict(a=za["terminals"][0], b=J["1"], net="1"), dict(a=za["terminals"][1], b=zb["terminals"][0], net="m1")]
    straps = [dict(a=J[k], b=(np.asarray(J[k]) * ML.CAN_R / float(np.linalg.norm(J[k]))).tolist()) for k in ("0", "0z")]
    return dict(junctions=J, parts=[d1, d3, za, zb], leads=leads, straps=straps, R=R, Rz=Rz, alpha=alpha, beta=beta,
                orient=dict(t_a=t_a, t_b=t_b))


def plan_v1b(R, Rz, gap):
    """deck A, two-fold symmetric including its wiring: D1 at 0 deg (REF end low), D3 at 180 deg (N1 end low);
    Z1a beside D3's N1 end (its N1 end there), Z1b beside D1's REF end (its REF end there): the two short joints are
    each other's rotation; the halves' m1 ends then sit 180 deg apart, joined by a closed ring at m1 (both ways
    round), whose mass centre is on the axis [OC]."""
    d1 = stick("D1", ("0", "2"), 0.0, R, True)
    d3 = stick("D3", ("3", "1"), 180.0, R, False)
    pz = ML.PART["clamp_half"]
    end_r = math.hypot(R, 0.5 * ML.PART["stick"]["l"])
    th_ref = math.degrees(math.atan2(d1["terminals"][0][1], d1["terminals"][0][0]))      # D1's REF end
    full = math.degrees(pz["l"] / Rz)                                                     # the half's angular length
    c_b = th_ref - math.degrees(gap / Rz) - 0.5 * full                                    # Z1b, below D1's REF end
    zb = half("Z1b", ("m1", "0"), c_b, Rz, True)                                          # m1 low, REF high
    za = half("Z1a", ("m1", "1"), c_b + 180.0, Rz, True)                                  # its rotation: m1 low, N1 high
    za = dict(za, nets=("1", "m1"), terminals=za["terminals"][::-1], pts=za["pts"][::-1], body_pts=za["body_pts"][::-1])
    J = {"2": d1["terminals"][1], "0": d1["terminals"][0], "3x": d3["terminals"][0], "1": d3["terminals"][1],
         "0z": zb["terminals"][1]}
    leads = [dict(a=za["terminals"][0], b=J["1"], net="1"), dict(a=zb["terminals"][1], b=J["0"], net="0"),
             dict(a=za["terminals"][1], b=zb["terminals"][0], net="m1", dir=1),
             dict(a=za["terminals"][1], b=zb["terminals"][0], net="m1", dir=-1)]
    straps = [dict(a=J["0"], b=(np.asarray(J["0"]) * ML.CAN_R / float(np.linalg.norm(J["0"]))).tolist())]
    return dict(junctions=J, parts=[d1, d3, za, zb], leads=leads, straps=straps, R=R, Rz=Rz, gap=gap,
                end_r=end_r, z_centres_deg=[c_b + 180.0, c_b])


def search_v1b():
    pz = ML.PART["clamp_half"]
    rz_min = ML.CAN_R + ML.clearance(ML.volt(V, "0", "1")["pk"]) + 0.5 * pz["body_w"] + 0.5
    best, tried = None, 0
    for R in np.arange(ML.CAN_R + 30.0, 120.0, 1.0):
        for Rz in np.arange(math.ceil(rz_min), 121.0, 1.0):
            for gap in (2.0, 4.0, 6.0, 10.0):
                dA = plan_v1b(float(R), float(Rz), gap)
                tried += 1
                okA, _ = SD.check(dA, V)
                if not okA:
                    continue
                dB = turned(dA)
                okB, _ = SD.check(dB, V)
                if not okB:
                    continue
                r_out = max(float(np.linalg.norm(p)) + q["rad"] for q in dA["parts"] for p in q["pts"])
                SA = float(np.linalg.norm(moments(dA, -1)[0]))
                key = (round(r_out, 0), SA)
                if best is None or key < best[0]:
                    best = (key, dA, dB)
        if best is not None:
            return best[1], best[2], tried
    return None, None, tried


def turned(dk):
    """deck B: deck A turned 180 deg about the axis, its nets and names the circuit's mirror (1 <-> 4, 2 <-> 3)."""
    neg = lambda p: [-p[0], -p[1]]                                                          # noqa: E731
    mp = lambda n: SD.MIRROR[n]                                                             # noqa: E731
    parts = []
    for q in dk["parts"]:
        parts.append(dict(q, name=SD.PART_MIRROR[q["name"]], nets=tuple(mp(n) for n in q["nets"]), centre=neg(q["centre"]),
                          pts=[neg(p) for p in q["pts"]], body_pts=[neg(p) for p in q["body_pts"]],
                          terminals=[neg(p) for p in q["terminals"]]))
    jm = {"2": "3", "3x": "2x", "1": "4", "0": "0", "0z": "0z"}
    J = {jm[k]: neg(v) for k, v in dk["junctions"].items()}
    return dict(dk, parts=parts, junctions=J, leads=[dict(L, a=neg(L["a"]), b=neg(L["b"]), net=mp(L["net"]))
                                                     for L in dk["leads"]],
                straps=[dict(a=neg(s["a"]), b=neg(s["b"])) for s in dk["straps"]])


def lead_path(dk, L):
    """the lead's route over the parts: round the lane the way that keeps farther from the sticks (s2_geometry.py)."""
    a, b = np.asarray(L["a"]), np.asarray(L["b"])
    ta, tb = (math.degrees(math.atan2(x[1], x[0])) for x in (a, b))
    sticks = [math.degrees(math.atan2(q["centre"][1], q["centre"][0])) for q in dk["parts"] if q["kind"] == "stick"]
    best = None
    ways = ((tb - ta) % 360.0, (tb - ta) % 360.0 - 360.0)
    if L.get("dir"):                                         # a lead with its way set (the midpoint ring's halves)
        ways = tuple(w for w in ways if w * L["dir"] > 0) or ways
    for d in ways:
        if not L["net"].startswith("m") and abs(d) > 180.0 and not L.get("dir"):
            continue
        m = min(abs((ta + d * f - s + 540.0) % 360.0 - 180.0) for f in np.linspace(0, 1, 60) for s in sticks)
        if best is None or m > best[0]:
            best = (m, d)
    d = best[1]
    ra, rb = float(np.linalg.norm(a)), float(np.linalg.norm(b))
    P = [pol(ra + (rb - ra) * f, ta + d * f) for f in np.linspace(0, 1, 61)]
    return P, float(sum(np.linalg.norm(P[k + 1] - P[k]) for k in range(len(P) - 1)))


def moments(dk, sign):
    """the deck's static moment S (g mm, a plane vector) and its couple C (g mm^2) at its side (sign -1: A, +1: B)."""
    S, C, m_tot = np.zeros(2), np.zeros(2), 0.0
    for q in dk["parts"]:
        v_h, v_b = ML.part_volume(q)
        m = ((v_h - v_b) * 1.15 + v_b * 2.5) * 1e-3                    # g, as sim/multiplier_layout.py deck_mass
        r = np.asarray(q["centre"])
        S += m * r
        C += m * sign * Z_AX[q["kind"]] * r
        m_tot += m
    mj = math.pi / 4 * 20.0 ** 2 * 20.0 * 1.15e-3
    for k, c in dk["junctions"].items():
        if k == "0z":
            continue
        S += mj * np.asarray(c)
        C += mj * sign * Z_AX["junction"] * np.asarray(c)
        m_tot += mj
    for L in dk["leads"]:
        P, length = lead_path(dk, L)
        cen = np.mean(np.array(P), axis=0)
        m = WIRE_G_PER_MM * length
        S += m * cen
        C += m * sign * Z_AX["lead"] * cen
        m_tot += m
    for s_ in dk["straps"]:
        a, b = np.asarray(s_["a"]), np.asarray(s_["b"])
        m = WIRE_G_PER_MM * float(np.linalg.norm(a - b))
        S += m * 0.5 * (a + b)
        C += m * sign * Z_AX["strap"] * 0.5 * (a + b)
        m_tot += m
    return S, C, m_tot


def score(name, dA, dB):
    okA, cA = SD.check(dA, V)
    okB, cB = SD.check(dB, V)
    SA, CA, mA = moments(dA, -1)
    SB, CB, mB = moments(dB, +1)
    r_out = max(float(np.linalg.norm(p)) + q["rad"] for d in (dA, dB) for q in d["parts"] for p in q["pts"])
    mid = sum(lead_path(dA, L)[1] for L in dA["leads"] if L["net"].startswith("m"))
    n1 = [lead_path(dA, L)[1] for L in dA["leads"] if L["net"] == "1"][0]
    xa, xb = np.asarray(dA["junctions"]["2"]), np.asarray(dA["junctions"]["3x"])
    return dict(name=name, pass_=bool(okA and okB), parts_r_out_mm=r_out, plate_r_mm=(ML.CPL_R1, r_out + 6.0),
                static_A_g_mm=float(np.linalg.norm(SA)), static_B_g_mm=float(np.linalg.norm(SB)),
                static_total_g_mm=float(np.linalg.norm(SA + SB)), couple_g_mm2=float(np.linalg.norm(CA + CB)),
                couple_as_two_masses_g=float(np.linalg.norm(CA + CB)) / (2 * 54.0 * r_out),
                deck_mass_g=mA, lead_mid_mm=mid, lead_n1_mm=n1,
                cross_wires=dict(angles_deg=[math.degrees(math.atan2(x[1], x[0])) for x in (xa, xb)],
                                 apart_mm=float(np.linalg.norm(xa - xb))),
                check_A=dict(solid=cA["all_solid"], can=cA["all_can"], junctions=cA["junctions_ok"],
                             cross=cA["cross"]["ok"], inner_bare=all(q["ok_bare"] for q in cA["inner"])),
                check_B=dict(solid=cB["all_solid"], can=cB["all_can"], junctions=cB["junctions_ok"],
                             cross=cB["cross"]["ok"], inner_bare=all(q["ok_bare"] for q in cB["inner"])),
                deck_A=dA, deck_B=dB, worst_pairs=sorted(cA["pairs"], key=lambda r: r["solid_margin_mm"])[:3])


def search():
    pz = ML.PART["clamp_half"]
    rz_min = ML.CAN_R + ML.clearance(ML.volt(V, "0", "1")["pk"]) + 0.5 * pz["body_w"] + 0.5
    best = None
    tried = 0
    for R in np.arange(ML.CAN_R + 30.0, 120.0, 1.0):
        for Rz in np.arange(math.ceil(rz_min), 121.0, 2.0):
            for dbeta in range(-60, 61, 5):
                for t_a in (True, False):
                    for t_b in (True, False):
                        dA = plan_v1(float(R), 0.0, float(Rz), 90.0 + dbeta, t_a, t_b)
                        tried += 1
                        ok, _ = SD.check(dA, V)
                        if not ok:
                            continue
                        dB = turned(dA)
                        okB, _ = SD.check(dB, V)
                        if not okB:
                            continue
                        r_out = max(float(np.linalg.norm(p)) + q["rad"] for q in dA["parts"] for p in q["pts"])
                        mid = [lead_path(dA, L)[1] for L in dA["leads"] if L["net"].startswith("m")][0]
                        key = (round(r_out, 1), mid)
                        if best is None or key < best[0]:
                            best = (key, dA, dB)
        if best is not None:
            return best[1], best[2], tried
    return None, None, tried


def figure(rows, path):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.patches import Circle
    fig, axs = plt.subplots(len(rows), 2, figsize=(11, 5.5 * len(rows)))
    col = {"stick": "#c0392b", "clamp_half": "#2e86c1"}
    for i, r in enumerate(rows):
        for j, (dk, side) in enumerate(((r["deck_A"], "A (below)"), (r["deck_B"], "B (above)"))):
            ax = axs[i][j]
            ax.add_patch(Circle((0, 0), ML.CPL_R1, fill=False, color="#888", lw=1.5))
            for q in dk["parts"]:
                P = np.array(q["pts"])
                for k in range(len(P) - 1):
                    for f in np.linspace(0, 1, 10):
                        ax.add_patch(Circle(tuple(P[k] + f * (P[k + 1] - P[k])), q["rad"], color=col[q["kind"]],
                                            alpha=0.06, lw=0))
                B = np.array(q["body_pts"])
                ax.plot(B[:, 0], B[:, 1], color=col[q["kind"]], lw=3)
                c = np.array(q["centre"]) * 1.28
                ax.text(c[0], c[1], f"{q['name']}\n{q['nets'][0]}->{q['nets'][1]}", ha="center", va="center", fontsize=7)
            for n, p in dk["junctions"].items():
                if n == "0z":
                    continue
                ax.plot(*p, "ko", ms=4)
                ax.text(p[0] * 0.8, p[1] * 0.8, "REF" if n == "0" else f"N{n.rstrip('x')}", fontsize=7, ha="center")
            for L in dk["leads"]:
                P, _ = lead_path(dk, L)
                P = np.array(P) * 1.0
                ax.plot(P[:, 0], P[:, 1], color="#7d3c98", lw=1, ls="--")
            for n in ("2", "3x", "3", "2x"):
                if n in dk["junctions"]:
                    p = dk["junctions"][n]
                    ax.add_patch(Circle(tuple(p), 4.0, fill=False, color="#e67e22", lw=1.5))
            ax.set_aspect("equal")
            ax.set_xlim(-140, 140)
            ax.set_ylim(-140, 140)
            ax.set_title(f"{r['name'][:3]} deck {side}: static {r['static_A_g_mm' if j == 0 else 'static_B_g_mm']:.0f} g mm",
                         fontsize=9)
        axs[i][0].set_ylabel(f"{r['name'][:60]}\ncouple {r['couple_g_mm2']:.0f} g mm2, total static "
                             f"{r['static_total_g_mm']:.0f} g mm", fontsize=8)
    fig.suptitle("The decks' symmetry (rebuild/s2_models/s2_deck_symmetry.py): orange rings, the cross nets' "
                 "junctions; purple, the leads", fontsize=9)
    fig.tight_layout()
    fig.savefig(path, dpi=120)


def main():
    v0 = score("V0: the deck of record, B the mirror of A about a plane through the axis", REC["deck_A"], REC["deck_B"])
    dA, dB, tried = search()
    rows = [v0]
    if dA is not None:
        rows.append(score("V1: each deck two-fold symmetric (a cross), B = A turned 180 deg", dA, dB))
    dA2, dB2, tried2 = search_v1b()
    if dA2 is not None:
        rows.append(score("V1b: two-fold symmetric with its wiring (short joints, an m1 ring), B = A turned 180 deg",
                          dA2, dB2))
        print(f"   V1b plan: lane R {dA2['R']:.0f}, halves r {dA2['Rz']:.0f} at {[round(x) for x in dA2['z_centres_deg']]} deg, "
              f"gap {dA2['gap']:.0f} mm; {tried2} plans tried")
    for r in rows:
        print(f"{r['name']}\n   pass {r['pass_']}; parts to r {r['parts_r_out_mm']:.1f}; static A {r['static_A_g_mm']:.0f}, "
              f"B {r['static_B_g_mm']:.0f}, total {r['static_total_g_mm']:.0f} g mm; couple {r['couple_g_mm2']:.0f} g mm2 "
              f"(~{r['couple_as_two_masses_g']:.1f} g pair); deck {r['deck_mass_g']:.0f} g; mid lead {r['lead_mid_mm']:.0f} mm, "
              f"N1 lead {r['lead_n1_mm']:.0f} mm; cross wires at {[round(a) for a in r['cross_wires']['angles_deg']]} deg, "
              f"{r['cross_wires']['apart_mm']:.0f} mm apart")
    if dA is not None:
        print(f"   V1 plan: lane R {dA['R']:.0f}, halves r {dA['Rz']:.0f} at {dA['beta']:.0f} / {dA['beta'] + 180:.0f} deg, "
              f"orient {dA['orient']}; {tried} plans tried")
    figure(rows, os.path.join(HERE, "s2-deck-symmetry.png"))
    out = dict(inputs=dict(rules="s2_deck.py check (--bare-can --no-can)", masses="sim/multiplier_layout.py deck_mass "
                           "densities; the wire 1 mm Cu in 3 mm PTFE", z_axes_mm=Z_AX, plans_tried=tried),
               V2_midplane_mirror=dict(possible=False, reason="with deck B at deck A's angles, the part over A's D1 is "
                                       "D2, whose end is N3, not N2: the cross nets could not run straight across [OC]"),
               variants=rows)
    json.dump(out, open(os.path.join(HERE, "s2_deck_symmetry_results.json"), "w"), indent=1, default=float)


if __name__ == "__main__":
    main()
