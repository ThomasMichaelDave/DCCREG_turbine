"""rebuild/s2_models/s2_bracket.py -- the cross wires' support, without machined PTFE: variants side by side.

The designer (2026-10-16): "the PTFE bracket is both structural and dielectrically important (for creepage?) I would
like to see it design differently where it doesn't use PTFE machined parts. We could lengthen the creepage paths by
adding more slots with for instance thin mica plates, the structural section ofcourse also needs to be taken into
account, wathever works there. Let's try some things out ..."

The job [OC: the S2a model, rebuild/s2_models/s2_deck_bare_nocan_results.json]: hold the two cross wires (N2 and N3,
3 mm PTFE HV wire, 25.8 mm apart at r ~84) at the hub's midplane, on the rotor at 600 rpm, between the decks; balanced
by a twin 180 deg round. Its surfaces are creepage paths:
  P1  wire to wire (N2 - N3): 6.38 kV peak, 5.06 kV rms;
  P2  each wire to the coupler's face, behind which sit the deck's ring (N1 / N4) and the flange (REF): the worst
      pair N2 - N1, 7.38 kV peak, 6.74 kV rms [IR, conservative: the ring taken at the coupler's face].
The rules, as the deck's and the redesign's mounts (sim/doubler_caps.py rules()) [IR]: creepage IEC 60664-1 PD2 x 1.25
DC on the rms (sim/parts_first_cut.py creepage: group I 5.0, IIIa 10.0 mm/kV rms); an inorganic surface (glazed
ceramic, mica, glass-bonded mica) does not track, so its creepage need not exceed the clearance; a path that crosses
several materials is rated at the worst of them [IR: IEC practice as recalled]; the clearance IEC 60664-1 case A at
1.5 x the peak (sim/multiplier_layout.py clearance).

The structure, for every variant but A [IR]: a split collar clamped round the coupler at the midplane carries the arm
and its twin, so the spin loads the collar in hoop tension, not a bonded joint in peel. Loads: the arm's own mass and
the wires' at 600 rpm (s2_deck.py bracket); the safety factor is the material's strength over the root's stress.

Variants:
  A  the S2a reference: one machined PTFE arm on the coupler, two ribs (s2_deck.py bracket);
  B  G10 collar and arms; mica barrier plates (0.3 mm muscovite, in sawn slots, bonded) across the creepage paths:
     between the seats (P1) and across the arm toward the collar (P2); each barrier adds twice its height to a path;
  C  G10 collar; per wire one catalogue glazed-steatite post insulator (moulded, IEC 60672 C 221) screwed to the
     collar's arm, the wire in a clip on its top;
  D  one moulded glass-bonded-mica piece (collar and arms, inorganic, non-tracking), the wires in moulded seats.
Writes rebuild/s2_models/s2_bracket_results.json and s2-bracket-variants.png.
Usage: python3 rebuild/s2_models/s2_bracket.py
"""
import json
import math
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "sim"))
import multiplier_layout as ML  # noqa: E402
import parts_first_cut as PF  # noqa: E402

DECK = json.load(open(os.path.join(HERE, "s2_deck_bare_nocan_results.json")))
V = DECK["volts_design"]
BR = DECK["bracket"]
RPM = 600.0
OM = 2 * math.pi * RPM / 60.0
WIRE_R = 1.5
# the materials [IR: datasheet-class]: density g/cm3, strength MPa (flexural, or tensile where it governs), group
MAT = {
    "PTFE (machined)": dict(rho=2.2, sigma=10.0, group="I", note="yield ~10 MPa, creeps under load; machined"),
    "G10 / FR4": dict(rho=1.85, sigma=300.0, group="IIIa", note="glass-epoxy laminate; sawn and drilled"),
    "mica (muscovite sheet)": dict(rho=2.8, sigma=None, group="inorganic", note="0.3 mm sheet, cut; a barrier only"),
    "glazed steatite C 221": dict(rho=2.7, sigma=120.0, group="inorganic", note="pressed and fired; catalogue posts"),
    "glass-bonded mica (moulded)": dict(rho=3.0, sigma=90.0, group="inorganic", note="moulded; non-tracking"),
}


def need(group, q):
    """the creepage a path of this group needs for the pair q (rms, peak)."""
    clr = ML.clearance(q["pk"])
    if group == "inorganic":
        return clr
    return max(PF.creepage(q["rms"], group) * PF.DC_MARGIN, clr)


def worst_group(groups):
    order = ["inorganic", "I", "II", "IIIa", "IIIb"]
    return max(groups, key=order.index)


def geometry():
    xA = DECK["deck_A"]["junctions"]
    p2, p3 = np.array(xA["2"]), np.array(xA["3x"])
    r_w = 0.5 * (np.linalg.norm(p2) + np.linalg.norm(p3))
    sep = float(np.linalg.norm(p2 - p3))
    return dict(r_w=float(r_w), sep=sep, r_cpl=ML.CPL_R1)


def load(m_arm_g, r_cg):
    """the arm's own centrifugal pull at its root, and the wires' (s2_deck.py bracket) [OC]."""
    F_arm = m_arm_g * 1e-3 * OM ** 2 * r_cg * 1e-3
    return F_arm + BR["load"]["wires_N"], F_arm


def variant_A(g, q12, q2r):
    w, T, ribs = BR["width_mm"], BR["thickness_mm"], BR["ribs"]
    L = g["r_w"] + WIRE_R + 6.0 - g["r_cpl"]
    m = BR["mass_g"]
    F, _ = load(m, g["r_cpl"] + 0.5 * L)
    root = w * T                                                # mm^2: the arm in tension at its bond
    p1 = g["sep"] - 2 * WIRE_R + 2 * ribs["n"] * ribs["depth_mm"]
    p2 = g["r_w"] - WIRE_R - g["r_cpl"]
    mat = MAT["PTFE (machined)"]
    return dict(name="A: machined PTFE arm, bonded on the coupler (the S2a reference)", parts=[
        "PTFE arm, machined, two ribs", "its twin"], materials=["PTFE (machined)"],
        P1=dict(have_mm=p1, need_mm=need("I", q12), group="I"), P2=dict(have_mm=p2, need_mm=need("I", q2r), group="I"),
        mass_g=2 * m, root_force_N=F, root_stress_MPa=F / root, safety=mat["sigma"] / (F / root),
        joint="bonded to the coupler: the spin pulls the joint in tension (peel)", machined_ptfe=True)


def variant_B(g, q12, q2r):
    """G10 collar + arms; mica barriers across P1 (between the seats) and across the arm (P2)."""
    T, w = 6.0, g["sep"] + 2 * (WIRE_R + 8.0)                  # a 6 mm G10 arm, 8 mm round each seat
    grp = worst_group(["IIIa", "inorganic"])                   # the path crosses G10 and mica: rated as G10
    n1 = need(grp, q12)
    n2 = need(grp, q2r)
    gap = g["sep"] - 2 * WIRE_R
    # P1: barriers between the seats, standing h above both faces (a barrier through a slot shows on both faces and
    # past the arm's outer edge, so every way round it adds 2 h) [OC]
    h1 = 8.0
    k1 = max(1, math.ceil((n1 - gap) / (2 * h1)))
    p1 = gap + 2 * k1 * h1
    # P2: barriers across the arm between the seats and the collar, each standing h2 above both faces and past both
    # edges; the plain path is the arm's length from the seat to the collar's face
    L2 = g["r_w"] - WIRE_R - (g["r_cpl"] + 6.0)                # the collar is 6 mm thick round the coupler
    h2 = 8.0
    k2 = max(0, math.ceil((n2 - L2) / (2 * h2)))
    p2 = L2 + 2 * k2 * h2
    L = g["r_w"] + WIRE_R + 8.0 - (g["r_cpl"] + 6.0)
    m_arm = (L * w * T * MAT["G10 / FR4"]["rho"] + (k1 * (T + 2 * h1) * L * 0.3 + k2 * (T + 2 * h2) * (w + 2 * h2) * 0.3)
             * MAT["mica (muscovite sheet)"]["rho"]) * 1e-3
    m_collar = math.pi * ((g["r_cpl"] + 6.0) ** 2 - g["r_cpl"] ** 2) * 12.0 * MAT["G10 / FR4"]["rho"] * 1e-3
    F, _ = load(m_arm, g["r_cpl"] + 6.0 + 0.5 * L)
    root = w * T
    return dict(name="B: G10 collar and arms, mica barriers in sawn slots", parts=[
        "G10 split collar 6 x 12 mm round the coupler, two screws", "G10 arm and its twin, 6 mm, sawn",
        f"{k1} mica barrier(s) between the seats, {h1:g} mm proud of each face", f"{k2} mica barrier(s) across each arm, "
        f"{h2:g} mm proud", "the wires in drilled seats, tied"], materials=["G10 / FR4", "mica (muscovite sheet)"],
        P1=dict(have_mm=p1, need_mm=n1, group=grp, barriers=k1), P2=dict(have_mm=p2, need_mm=n2, group=grp, barriers=k2),
        mass_g=2 * m_arm + m_collar, root_force_N=F, root_stress_MPa=F / root,
        safety=MAT["G10 / FR4"]["sigma"] / (F / root),
        joint="the collar clamps the coupler; the spin loads it in hoop tension", machined_ptfe=False)


def variant_C(g, q12, q2r):
    """G10 collar; per wire a glazed-steatite post insulator; the path from wire to wire runs down one post, along the
    G10 arm, up the other: it crosses G10, so it is rated as G10."""
    H_post, D_post = 25.0, 16.0                                # a catalogue standoff, Ø16 x 25, M4 inserts [RH]
    grp = worst_group(["inorganic", "IIIa"])
    n1, n2 = need(grp, q12), need(grp, q2r)
    p1 = 2 * H_post + max(0.0, g["sep"] - D_post)              # down, across the arm, up [OC]
    L2 = g["r_w"] - (g["r_cpl"] + 6.0)
    p2 = H_post + L2 - 0.5 * D_post
    T, w = 6.0, g["sep"] + D_post + 12.0
    L = g["r_w"] + 0.5 * D_post + 6.0 - (g["r_cpl"] + 6.0)
    m_post = math.pi / 4 * D_post ** 2 * H_post * 0.7 * MAT["glazed steatite C 221"]["rho"] * 1e-3   # 70 % solid [RH]
    m_arm = L * w * T * MAT["G10 / FR4"]["rho"] * 1e-3 + 2 * m_post
    m_collar = math.pi * ((g["r_cpl"] + 6.0) ** 2 - g["r_cpl"] ** 2) * 12.0 * MAT["G10 / FR4"]["rho"] * 1e-3
    F, _ = load(m_arm, g["r_cpl"] + 6.0 + 0.5 * L)
    # the posts stand along z (the wires' direction is z): the spin loads each post in shear / bending at its foot
    F_post = m_post * 1e-3 * OM ** 2 * g["r_w"] * 1e-3 + 0.5 * BR["load"]["wires_N"]
    M = F_post * 0.5 * H_post                                  # N mm, the load at mid-height [IR]
    Z = math.pi * D_post ** 3 / 32.0
    root = w * T
    return dict(name="C: G10 collar and arm, catalogue glazed-steatite posts", parts=[
        "G10 split collar 6 x 12 mm, two screws", "G10 arm and its twin, 6 mm", f"2 glazed steatite posts Ø{D_post:g} x "
        f"{H_post:g}, M4 inserts (catalogue, IEC 60672 C 221)", "the wires in clips on the posts' tops"],
        materials=["G10 / FR4", "glazed steatite C 221"],
        P1=dict(have_mm=p1, need_mm=n1, group=grp), P2=dict(have_mm=p2, need_mm=n2, group=grp),
        mass_g=2 * m_arm + m_collar, root_force_N=F, root_stress_MPa=F / root,
        safety=min(MAT["G10 / FR4"]["sigma"] / (F / root), MAT["glazed steatite C 221"]["sigma"] / (M / Z)),
        post_bending_MPa=M / Z, joint="the collar clamps the coupler; the posts screw to the arm", machined_ptfe=False)


def variant_D(g, q12, q2r):
    """one moulded glass-bonded-mica piece: every path on an inorganic surface, so the clearance governs."""
    T, w = 8.0, g["sep"] + 2 * (WIRE_R + 6.0)
    n1, n2 = need("inorganic", q12), need("inorganic", q2r)
    p1 = g["sep"] - 2 * WIRE_R
    p2 = g["r_w"] - WIRE_R - (g["r_cpl"] + 6.0)
    L = g["r_w"] + WIRE_R + 6.0 - (g["r_cpl"] + 6.0)
    rho = MAT["glass-bonded mica (moulded)"]["rho"]
    m_arm = L * w * T * rho * 1e-3
    m_collar = math.pi * ((g["r_cpl"] + 6.0) ** 2 - g["r_cpl"] ** 2) * 12.0 * rho * 1e-3
    F, _ = load(m_arm, g["r_cpl"] + 6.0 + 0.5 * L)
    root = w * T
    return dict(name="D: one moulded glass-bonded-mica collar with both arms", parts=[
        "glass-bonded mica, moulded in one: a split collar and the two arms, the wires' seats moulded in",
        "two screws across the split (in the collar, away from the seats)"], materials=["glass-bonded mica (moulded)"],
        P1=dict(have_mm=p1, need_mm=n1, group="inorganic"), P2=dict(have_mm=p2, need_mm=n2, group="inorganic"),
        mass_g=2 * m_arm + m_collar, root_force_N=F, root_stress_MPa=F / root,
        safety=MAT["glass-bonded mica (moulded)"]["sigma"] / (F / root),
        joint="the collar clamps the coupler; brittle: a moulded part, a mould to make", machined_ptfe=False)


def figure(g, rows, path):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.patches import Circle, Rectangle
    fig, axs = plt.subplots(1, 4, figsize=(16, 4.6))
    for ax, r in zip(axs, rows):
        key = r["name"][0]
        ax.add_patch(Circle((0, 0), g["r_cpl"], fill=False, color="#888"))
        ys = (-0.5 * g["sep"], 0.5 * g["sep"])
        if key == "A":
            ax.add_patch(Rectangle((g["r_cpl"], -0.5 * BR["width_mm"]), BR["r_mm"][1] - g["r_cpl"], BR["width_mm"],
                                   fc="#f2f2e0", ec="#999"))
            for k in range(BR["ribs"]["n"]):
                y_ = -0.5 * g["sep"] + WIRE_R + (k + 1) * (g["sep"] - 2 * WIRE_R) / (BR["ribs"]["n"] + 1)
                ax.plot([g["r_cpl"], BR["r_mm"][1] + 5], [y_, y_], color="#bbb", lw=2)
        else:
            ax.add_patch(Circle((0, 0), g["r_cpl"] + 6.0, fill=False, color="#6b8e23", lw=3))
            col = {"B": "#c9d9a0", "C": "#c9d9a0", "D": "#d8cfb8"}[key]
            w = g["sep"] + (16.0 + 12.0 if key == "C" else 2 * (WIRE_R + 8.0 if key == "B" else WIRE_R + 6.0))
            ax.add_patch(Rectangle((g["r_cpl"] + 6.0, -0.5 * w), g["r_w"] + 8.0 - g["r_cpl"] - 6.0, w, fc=col, ec="#777"))
            if key == "B":
                for k in range(r["P1"]["barriers"]):
                    y_ = -0.5 * g["sep"] + WIRE_R + (k + 1) * (g["sep"] - 2 * WIRE_R) / (r["P1"]["barriers"] + 1)
                    ax.plot([g["r_cpl"] + 6.0, g["r_w"] + 16.0], [y_, y_], color="#b8860b", lw=1.5)
                for k in range(r["P2"]["barriers"]):
                    x_ = g["r_cpl"] + 6.0 + (k + 1) * (g["r_w"] - WIRE_R - g["r_cpl"] - 6.0) / (r["P2"]["barriers"] + 1)
                    ax.plot([x_, x_], [-0.5 * w - 8, 0.5 * w + 8], color="#b8860b", lw=1.5)
            if key == "C":
                for y_ in ys:
                    ax.add_patch(Circle((g["r_w"], y_), 8.0, fc="#efe8d8", ec="#999"))
        for y_ in ys:
            ax.add_patch(Circle((g["r_w"], y_), WIRE_R, color="#c0392b"))
        ax.set_aspect("equal")
        ax.set_xlim(0, 120)
        ax.set_ylim(-45, 45)
        ok1 = "ok" if r["P1"]["have_mm"] >= r["P1"]["need_mm"] else "SHORT"
        ok2 = "ok" if r["P2"]["have_mm"] >= r["P2"]["need_mm"] else "SHORT"
        ax.set_title(f"{r['name'][:40]}\nP1 {r['P1']['have_mm']:.0f}/{r['P1']['need_mm']:.0f} mm {ok1}; "
                     f"P2 {r['P2']['have_mm']:.0f}/{r['P2']['need_mm']:.0f} mm {ok2}\n{r['mass_g']:.0f} g, safety "
                     f"{r['safety']:.0f}", fontsize=8)
        ax.set_xlabel("r (mm), plan at the midplane")
    fig.suptitle("The cross wires' support without machined PTFE (rebuild/s2_models/s2_bracket.py): red, the wires; "
                 "olive, the collar; gold, mica barriers; P1 wire to wire, P2 wire to the coupler", fontsize=9)
    fig.tight_layout()
    fig.savefig(path, dpi=130)


def main():
    g = geometry()
    q12 = V["pairs"]["2|3"]
    q2r = max((V["pairs"][k] for k in ("1|2", "0|2", "0|3", "3|4")), key=lambda q: q["rms"])
    rows = [f(g, q12, q2r) for f in (variant_A, variant_B, variant_C, variant_D)]
    for r in rows:
        r["P1"]["ok"] = bool(r["P1"]["have_mm"] >= r["P1"]["need_mm"])
        r["P2"]["ok"] = bool(r["P2"]["have_mm"] >= r["P2"]["need_mm"])
        print(f"{r['name']}\n   P1 wire-wire {r['P1']['have_mm']:.1f} / {r['P1']['need_mm']:.1f} mm ({r['P1']['group']}), "
              f"P2 wire-coupler {r['P2']['have_mm']:.1f} / {r['P2']['need_mm']:.1f} mm; {r['mass_g']:.0f} g (pair + collar); "
              f"root {r['root_stress_MPa']:.3f} MPa, safety {r['safety']:.0f}")
    figure(g, rows, os.path.join(HERE, "s2-bracket-variants.png"))
    out = dict(inputs=dict(geometry=g, pair_P1=q12, pair_P2=q2r, rpm=RPM, materials=MAT,
                           rules="IEC 60664-1 PD2 x 1.25 DC on the rms (sim/parts_first_cut.py creepage, DC_MARGIN); "
                                 "inorganic: creepage = clearance; mixed paths at the worst group [IR]; clearance case "
                                 "A at 1.5 x the peak (sim/multiplier_layout.py clearance)"), variants=rows)
    json.dump(out, open(os.path.join(HERE, "s2_bracket_results.json"), "w"), indent=1, default=float)


if __name__ == "__main__":
    main()
