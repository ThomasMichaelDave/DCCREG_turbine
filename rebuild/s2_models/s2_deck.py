"""rebuild/s2_models/s2_deck.py -- S2a, step 1: the compact deck for the S1b circuit, and the stack it gives.

The designer (2026-10-16): "option 2, eventually we will have to redesign the deck but thats for the future. A bigger
deck then required would insert an unnecessary compromise for no reason." So the deck is planned for the S1b parts
only, not cut down from the 10-11 redesign's (sim/multiplier_layout.py, 13 parts and ten junctions per side).

Per side (side A below the hub; side B its mirror, nets 1 <-> 4, 2 <-> 3; rebuild/s2_models/s2-plan.md):
  D1  HV stick, REF -> N2  (D2 on side B: REF -> N3)
  D3  HV stick, N3 -> N1   (D4 on side B: N2 -> N4)   its anode end takes the cross net from the other deck
  Z1  the clamp string, N1 -> REF (Z4 on side B), 66 x 200 V as an arc module
  junctions: N1 (the riser to the vanes, ring A's lead, D3's cathode, Z1's HV end), N2 (the tap to Ca's node-2 plate,
  D1's cathode, the cross net to deck B's D4), N3x (the cross net from deck B to D3's anode); REF: straps to the can.

The rules and the parts' envelopes are the redesign study's, imported, not copied (sim/multiplier_layout.py PART,
clearance, pieces, u_bound, deck_check, the can, the cage, the deck plate's place; sim/parts_first_cut.py E_POT,
CLR_MARGIN, IEC 60664-1 case A) [IR there]. The working voltages are the S1b circuit's own (rebuild/s1_tube/
s1b_clamp.py's deck), at the strings' +5 % case, the highest of its spread (s1b-clamp-findings.md) [IR: design to the
worst string].

The plan [IR]: one lane at radius R. The two junctions that take the cross nets (N2 and N3x) sit symmetric about the
mirror line at 0 deg, so each cross net runs straight across between the decks (deck B is deck A mirrored about it).
D1 runs from its REF end to N2 below the line, D3 from N3x to N1 above it, Z1's arc from N1 on. The search: the
smallest R, then the junctions' least separation, at which every pair of parts passes the potting rule (no housing
overlap; the bodies at least U / E_POT apart) and every part clears the can and the cage; the bare clearance (as if
unpotted) is reported as in the redesign study.
Then the stack: the column's node-2 plate moves to the clearance its peak against the deck's nets needs (as the
redesign's stack() does), which is what the smaller deck buys axially.

Writes rebuild/s2_models/s2_deck_results.json and rebuild/s2_models/s2-deck-plan.png.
Usage: python3 rebuild/s2_models/s2_deck.py [--reuse-volts] [--bare-can]   (--reuse-volts: the ngspice runs' pairs from the last
       results file)
"""

import json
import math
import os
import subprocess
import sys
import tempfile

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "sim"))
sys.path.insert(0, os.path.join(ROOT, "rebuild", "s1_tube"))
import multiplier_layout as ML  # noqa: E402  the redesign study's rules, envelopes and checks (read only)
import parts_first_cut as PF  # noqa: E402
import s1b_clamp as SB  # noqa: E402  the S1b circuit's deck

PARTS = {"A": [("D1", "stick", ("0", "2")), ("D3", "stick", ("3", "1")), ("Z1a", "clamp_half", ("1", "m1")),
              ("Z1b", "clamp_half", ("m1", "0"))]}
MIRROR = {"0": "0", "1": "4", "2": "3", "3": "2", "4": "1", "m1": "m4", "m4": "m1"}
PART_MIRROR = {"D1": "D2", "D3": "D4", "Z1a": "Z4a", "Z1b": "Z4b"}
# each clamp string split into two series halves of 33 parts, its arc module halved in length (the same section and
# potting as sim/multiplier_layout.py PART["clamp"]) [IR]: electrically the same string; mechanically two masses the
# deck can balance with. Their midpoint m1 (m4) holds half the node's voltage [IR: two equal halves in series]
_C = ML.PART["clamp"]
ML.PART["clamp_half"] = dict(what="half the clamp string: 33 x 1.5KE200A in a meander", body_w=_C["body_w"],
                             body_l=0.5 * _C["body_l"], body_h=_C["body_h"])
ML.PART["clamp_half"].update(w=_C["body_w"] + 2 * ML.POT, l=0.5 * _C["body_l"] + 2 * ML.POT, h=_C["body_h"] + 2 * ML.POT)
_part_volume = ML.part_volume


def _part_volume_s2(a):
    """ML.part_volume, with the half module boxed as the whole one is (sim/ is not edited)."""
    if a["kind"] == "clamp_half":
        p = ML.PART["clamp_half"]
        return p["w"] * p["l"] * p["h"], p["body_w"] * p["body_l"] * p["body_h"]
    return _part_volume(a)


ML.part_volume = _part_volume_s2                    # ML.deck_mass looks it up in its module at call time
DESIGN_CASE = dict(name="strings +5 %", zscale=(1.05, 1.05))


# ---------------------------------------------------------------------------------------------- 1. the working volts
def volts(zscale, n_cyc=40, keep=8):
    """every pair's peak and rms among REF and N1-N4 over the last cycles of the clamped steady state (kV)."""
    txt = SB.deck(3000.0, n_cyc, zscale=zscale)
    with tempfile.TemporaryDirectory() as d:
        open(os.path.join(d, "x.cir"), "w").write(txt)
        subprocess.run(["ngspice", "-b", "x.cir"], capture_output=True, text=True, timeout=3600, cwd=d)
        raw = np.loadtxt(os.path.join(d, "out.dat"))
    t = raw[:, 0]
    s = t >= (n_cyc - keep) / SB.V["F"]
    vn = {str(k + 1): raw[s, 2 * k + 1] / 1e3 for k in range(4)}
    vn["0"] = np.zeros(int(s.sum()))
    vn["m1"], vn["m4"] = 0.5 * vn["1"], 0.5 * vn["4"]                  # the half-strings' midpoints [IR]
    nodes = sorted(vn)
    pairs = {}
    for i, a in enumerate(nodes):
        for b in nodes[i + 1:]:
            dv = vn[a] - vn[b]
            pairs[f"{a}|{b}"] = dict(pk=float(np.abs(dv).max()), rms=float(math.sqrt(np.mean(dv * dv))))
    return dict(pairs=pairs, V_kV={k: dict(max=float(v.max()), min=float(v.min())) for k, v in vn.items() if k != "0"})


# ---------------------------------------------------------------------------------------------- 2. the deck's plan
def pol(r, th):
    return np.array([r * math.cos(math.radians(th)), r * math.sin(math.radians(th))])


def plan(R, delta_deg, gap_mm, mirror=False, z_place=None):
    """deck A (or B, mirrored about 0 deg) in the redesign study's plan format (ML.deck_check reads it)."""
    th_ = (lambda t: -t) if mirror else (lambda t: t)
    mp = (lambda n: MIRROR[n]) if mirror else (lambda n: n)
    ps = ML.PART["stick"]
    L_st = ps["l"]                                            # the stick's housing length (66 mm)
    deg = lambda mm: math.degrees(mm / R)                    # noqa: E731  arc length -> angle at R
    # the junctions: N2 at -delta, N3x at +delta (the cross nets), N1 beyond D3, Z1 from N1 on
    j2, j3 = -delta_deg, delta_deg
    th_d1 = j2 - deg(0.5 * L_st)                              # D1: its N2 end at j2
    th_d3 = j3 + deg(0.5 * L_st)                              # D3: its N3 end at j3
    j1 = j3 + deg(L_st)
    j0 = j2 - deg(L_st)                                       # D1's REF end (a strap to the can)
    out = []

    def lying(nm, kind, nets, th, rev):
        p = ML.PART[kind]
        c = pol(R, th_(th))
        tt = np.array([-math.sin(math.radians(th_(th))), math.cos(math.radians(th_(th)))])
        rad = 0.5 * p["d"]
        pts = [c - (0.5 * p["l"] - rad) * tt, c + (0.5 * p["l"] - rad) * tt]
        body = [c - 0.5 * p["body_l"] * tt, c + 0.5 * p["body_l"] * tt]
        term = [c - 0.5 * p["l"] * tt, c + 0.5 * p["l"] * tt]
        if rev:                                                # the nets' order along increasing angle
            pts, body, term = pts[::-1], body[::-1], term[::-1]
        if mirror:
            pts, body, term = pts[::-1], body[::-1], term[::-1]
        out.append(dict(name=PART_MIRROR[nm] if mirror else nm, kind=kind, nets=(mp(nets[0]), mp(nets[1])),
                        centre=c.tolist(), pts=[q.tolist() for q in pts], body_pts=[q.tolist() for q in body], rad=rad,
                        orient="tan", terminals=[term[0].tolist(), term[-1].tolist()]))
    lying("D1", "stick", ("0", "2"), th_d1, False)           # REF end at lower angle, N2 end at j2
    lying("D3", "stick", ("3", "1"), th_d3, False)           # N3 end at j3, N1 end at j1
    # Z1: an arc module from just past N1, its HV end at N1's side
    pz = ML.PART["clamp_half"]
    # z_place: ((centre angle a, centre angle b), radius) of the two half modules; default: one after the other
    # beyond N1 on the lane
    if z_place is None:
        sp0 = math.degrees((pz["l"]) / R)
        za = j1 + deg(gap_mm) + 0.5 * sp0 + deg(0.5 * pz["w"])
        z_place = ((za, za + sp0 + deg(gap_mm)), R)
    (ca, cb), Rz = z_place
    span = math.degrees((pz["l"] - pz["w"]) / Rz)
    terms = {}
    for nm, cc, nets in (("Z1a", ca, ("1", "m1")), ("Z1b", cb, ("m1", "0"))):
        th0 = cc - 0.5 * span
        ths = np.linspace(th0, th0 + span, 7)
        pts = [pol(Rz, th_(t)) for t in ths]
        term = [pol(Rz, th_(th0 - math.degrees(0.5 * pz["w"] / Rz))),
                pol(Rz, th_(th0 + span + math.degrees(0.5 * pz["w"] / Rz)))]
        terms[nm] = term
        out.append(dict(name=PART_MIRROR[nm] if mirror else nm, kind="clamp_half", nets=(mp(nets[0]), mp(nets[1])),
                        centre=pol(Rz, th_(cc)).tolist(), pts=[q.tolist() for q in pts],
                        body_pts=[q.tolist() for q in pts], rad=0.5 * pz["w"], orient="arc",
                        terminals=[term[0].tolist(), term[1].tolist()]))
    term = terms["Z1b"]
    # the junctions sit at the sticks' ends (a lying housing's end is off the lane's circle by its chord) [OC]
    d1, d3 = out[0], out[1]
    junc = {mp("2"): d1["terminals"][1], mp("3") + "x": d3["terminals"][0], mp("1"): d3["terminals"][1],
            "0": d1["terminals"][0], "0z": term[1].tolist()}
    straps = [dict(a=junc["0"], b=(np.asarray(junc["0"]) * ML.CAN_R / R).tolist()),
              dict(a=junc["0z"], b=(np.asarray(junc["0z"]) * ML.CAN_R / float(np.linalg.norm(junc["0z"]))).tolist())]
    leads = [dict(a=out[2]["terminals"][0], b=junc[mp("1")], net=mp("1")),          # Z1a's HV end to N1
             dict(a=out[2]["terminals"][1], b=out[3]["terminals"][0], net=mp("m1"))]  # Z1a to Z1b, the midpoint
    return dict(junctions=junc, parts=out, leads=leads, straps=straps, R=R, delta_deg=delta_deg, gap_mm=gap_mm,
                span_deg=[j0, th0 + span + deg(0.5 * pz["w"])], z_place=z_place)


def balanced(dk, V):
    """Z1 moved opposite the rest of the deck, at the radius that cancels its moment (or as near as the plate allows),
    its HV end wired to N1 by a lead over the parts as the redesign wires its leads [IR]; then the checks again."""
    rest = dict(dk, parts=[q for q in dk["parts"] if q["kind"] != "clamp_half"])
    m_rest = ML.deck_mass(rest)                                     # the sticks and the junctions
    z = [q for q in dk["parts"] if q["kind"] == "clamp_half"][0]
    v_h, v_b = ML.part_volume(z)
    m_h = ((v_h - v_b) * 1.15 + v_b * 2.5) * 1e-6                   # kg per half, as ML.deck_mass
    pz = ML.PART["clamp_half"]
    Rz = ML.DECK_R0 + 0.5 * pz["w"]                                 # the halves as far in as the plate allows
    if BARE_CAN:                                                    # ... or as far as the bare clearance to the can
        u = ML.volt(V, "0", "1")["pk"]
        Rz = max(Rz, ML.CAN_R + ML.clearance(u) + 0.5 * pz["body_w"] + 0.5)
    ang = m_rest["offset_deg"] + 180.0
    # two equal masses at ang +- phi cancel the rest's moment S when 2 m_h Rz cos(phi) = S [OC]
    cphi = m_rest["imbalance_g_mm"] / (2.0 * m_h * 1e3 * Rz)
    phi0 = math.degrees(math.acos(min(1.0, cphi)))
    best = None
    for dph in np.arange(-10.0, 10.1, 1.0):
        phi = phi0 + dph
        dk2 = plan(dk["R"], dk["delta_deg"], dk["gap_mm"], z_place=((ang - phi, ang + phi), Rz))
        ok, c = check(dk2, V)
        if ok:
            b = balance(dk2)
            if best is None or b["imbalance_g_mm"] < best[2]["imbalance_g_mm"]:
                best = (dk2, c, b)
    return best


J_COND_R, J_POT_R = 5.0, 10.0     # a junction's brass terminal and its potted block, radii (sim/tube_geometry.py J_COND,
WIRE_R = 1.5                      # J_POT) [RH there]; the PTFE HV wire (sim/tube_geometry.py WIRE_R) [IR there]


def junction_net(n):
    return "0" if n.startswith("0") else n.rstrip("x")


BARE_CAN = False      # --bare-can: every part's body also clears the can (REF) by the bare clearance, as if unpotted


def check(dk, V):
    """the redesign's deck_check (parts against parts, the can and the cage), plus what it did not need for this plan
    [IR]: every junction block against every other (no overlap; the terminals U / E_POT apart) and against every part
    not ending at it (no overlap; the terminal to the body U / E_POT); and the two cross nets, bare PTFE wires running
    straight across in air between the decks, the bare clearance of their peak apart."""
    c = ML.deck_check(dk, V)
    J = {n: np.asarray(p) for n, p in dk["junctions"].items() if not n.startswith("0z")}
    body_r = lambda q: 0.5 * (ML.PART[q["kind"]].get("body_d") or ML.PART[q["kind"]]["body_w"])  # noqa: E731
    rows = []
    names = list(J)
    for i, a in enumerate(names):
        for b in names[i + 1:]:
            u = ML.volt(V, junction_net(a), junction_net(b))["pk"]
            if u == 0:
                continue
            g = float(np.linalg.norm(J[a] - J[b]))
            rows.append(dict(a=a, b=b, U_pk_kV=u, block_gap_mm=g - 2 * J_POT_R, cond_gap_mm=g - 2 * J_COND_R,
                             ok=bool(g - 2 * J_POT_R >= 0 and g - 2 * J_COND_R >= u / PF.E_POT)))
    for n, p in J.items():
        jn = junction_net(n)
        for q in dk["parts"]:
            at_own = any(float(np.linalg.norm(np.asarray(t) - p)) < 1.0 for t in q["terminals"]) or any(
                float(np.linalg.norm(np.asarray(L["b"]) - p)) < 1.0 and any(
                    float(np.linalg.norm(np.asarray(L["a"]) - np.asarray(t))) < 1.0 for t in q["terminals"])
                for L in dk["leads"])                       # a part wired to the junction by a lead
            if at_own:
                continue
            for pa, sa in ML.pieces(q):
                u = max(ML.u_bound(V, {jn: 1.0}, x) for x in sa)
                g = ML.poly_dist([p.tolist()], pa)
                rows.append(dict(a=n, b=q["name"], U_pk_kV=u, block_gap_mm=g - J_POT_R - q["rad"],
                                 cond_gap_mm=g - J_COND_R - body_r(q),
                                 ok=bool(g - J_POT_R - q["rad"] >= 0 and g - J_COND_R - body_r(q) >= u / PF.E_POT)))
    xa = [n for n in J if n.endswith("x")][0]
    xb = [n for n in J if not n.endswith("x") and junction_net(n) == MIRROR[junction_net(xa)]][0]
    u_x = ML.volt(V, junction_net(xa), junction_net(xb))["pk"]
    g_x = float(np.linalg.norm(J[xa] - J[xb])) - 2 * WIRE_R
    cross = dict(pair=f"{xb}-{xa}", U_pk_kV=u_x, wire_gap_mm=g_x, clearance_mm=ML.clearance(u_x),
                 ok=bool(g_x >= ML.clearance(u_x)))
    c.update(junctions=rows, junctions_ok=all(r["ok"] for r in rows), cross=cross)
    ok = c["all_solid"] and c["all_can"] and c["junctions_ok"] and cross["ok"]
    if BARE_CAN:
        ok = ok and all(q["ok_bare"] for q in c["to_can"])
    return ok, c


def bracket(dk, V, rpm=600.0):
    """the cross wires' support (the designer, 2026-10-16: "Make sure here the wires have a bracket to support them when
    crossing. Eventually that bracket will be integrated in later design considerations but for now it requires a
    support."). [IR] A PTFE arm on the can's outer face at the hub's midplane (z 0, halfway across the 60 mm gap
    between the deck plates, |z| < 30), reaching out under both wires, each held in a U-seat; ribs between the seats
    for the creepage between the two cross nets; an identical arm 180 deg round for the balance. The rules:
    sim/parts_first_cut.py creepage (PTFE material group I, pollution degree 2) x DC_MARGIN on the rms, and
    sim/multiplier_layout.py clearance on the peak."""
    xa = [n for n in dk["junctions"] if n.endswith("x")][0]
    xb = MIRROR[junction_net(xa)]
    pa, pb = np.asarray(dk["junctions"][xa]), np.asarray(dk["junctions"][xb])
    r_w = 0.5 * (float(np.linalg.norm(pa)) + float(np.linalg.norm(pb)))
    sep = float(np.linalg.norm(pa - pb))                              # centre to centre
    th = math.degrees(math.atan2(0.5 * (pa + pb)[1], 0.5 * (pa + pb)[0]))
    q_ab, q_a0 = V["pairs"][f"{min(junction_net(xa), xb)}|{max(junction_net(xa), xb)}"], ML.volt(V, "0", xb)
    q_b0 = ML.volt(V, "0", junction_net(xa))
    q_r0 = q_a0 if q_a0["pk"] >= q_b0["pk"] else q_b0
    creep_ab = PF.creepage(q_ab["rms"], "I", 2) * PF.DC_MARGIN
    creep_r0 = PF.creepage(q_r0["rms"], "I", 2) * PF.DC_MARGIN
    gap_seats = sep - 2 * WIRE_R                                      # the face between the two seats
    rib_d, rib_w = 5.0, 2.0                                           # [IR] ribs wider than X = 1 mm count (PD2)
    n_rib = max(0, math.ceil((creep_ab - gap_seats) / (2 * rib_d)))
    n_rib = n_rib + 1                                                 # one spare rib: the need is met with margin [IR]
    T, M = 8.0, 6.0                                                   # the arm's axial thickness; material round the seats
    r0, r1 = ML.CAN_R, r_w + WIRE_R + M
    w = sep + 2 * (WIRE_R + M)
    vol = (r1 - r0) * w * T + n_rib * rib_d * rib_w * T               # mm^3
    m = vol * 2.2e-3                                                  # g, PTFE 2.2 g/cm^3
    om = 2 * math.pi * rpm / 60.0
    wire_g_per_m = (math.pi / 4 * 1.0 ** 2 * 8.96 + math.pi / 4 * (3.0 ** 2 - 1.0 ** 2) * 2.2)   # Cu 1 mm in PTFE 3 mm
    span = 2 * ML.DECK_Z0                                             # the gap between the plates
    F = 2 * 0.5 * span * 1e-3 * wire_g_per_m * 1e-3 * om ** 2 * r_w * 1e-3   # N: each wire's middle half-span
    return dict(material="PTFE (material group I, CTI >= 600; sim/parts_first_cut.py MATERIALS)", at_z_mm=0.0,
                angle_deg=th, r_mm=(r0, r1), width_mm=w, thickness_mm=T, wire_r_mm=r_w, wire_sep_mm=sep,
                seats="two U-seats, 3 mm wire, the wire bonded or tied in [IR]", ribs=dict(n=n_rib, depth_mm=rib_d,
                width_mm=rib_w), creepage_between_wires=dict(U_rms_kV=q_ab["rms"], need_mm=creep_ab,
                have_mm=gap_seats + 2 * n_rib * rib_d, ok=bool(gap_seats + 2 * n_rib * rib_d >= creep_ab)),
                creepage_wire_to_can=dict(U_rms_kV=q_r0["rms"], need_mm=creep_r0, have_mm=r_w - WIRE_R - r0,
                                          ok=bool(r_w - WIRE_R - r0 >= creep_r0)),
                clearance_wire_to_can=dict(U_pk_kV=q_r0["pk"], need_mm=ML.clearance(q_r0["pk"]),
                                           have_mm=r_w - WIRE_R - ML.CAN_R),
                mass_g=m, balance="an identical arm at angle + 180 deg (no wires): the pair balances [OC]",
                load=dict(rpm=rpm, accel_g=om ** 2 * r_w * 1e-3 / 9.81, wires_N=F,
                          note="the wires' centrifugal load at the seats; the arm's own load into the can's face"))


def balance(dk):
    """the deck's static imbalance [RH: sim/multiplier_layout.py deck_mass's densities], with the plate cut to the parts'
    outer radius + 6 mm; the balance mass that cancels it at the lane's radius, opposite."""
    m = ML.deck_mass(dk)
    r1 = max(float(np.linalg.norm(p)) for q in dk["parts"] for p in q["pts"]) + max(q["rad"] for q in dk["parts"]) + 6.0
    plate = math.pi * (r1 ** 2 - ML.DECK_R0 ** 2) * ML.DECK_T * 1.85e-6
    return dict(parts_and_junctions_kg=m["parts_kg"], plate_r_mm=(ML.DECK_R0, r1), plate_kg=plate,
                imbalance_g_mm=m["imbalance_g_mm"], imbalance_deg=m["offset_deg"],
                balance_mass_g_at_lane=m["imbalance_g_mm"] / dk["R"], balance_at_deg=m["offset_deg"] + 180.0)


def search(V):
    """the smallest lane radius, then the least junction separation and part gap, that pass [IR: 1 mm / 0.5 deg]."""
    for R in np.arange(ML.CAN_R + 2.0 + 0.5 * ML.PART["stick"]["d"], ML.R_OUT + 0.1, 1.0):
        u_x = ML.volt(V, "2", "3")["pk"]
        # the least half-separation the two cross-net junctions allow: their wires' bare clearance in air, their blocks
        # not overlapping, their terminals U / E_POT apart [OC: the chord 2 R sin(delta)]
        need = max(ML.clearance(u_x) + 2 * WIRE_R, 2 * J_POT_R, 2 * J_COND_R + u_x / PF.E_POT)
        d0 = math.degrees(math.asin(min(1.0, 0.5 * need / R)))
        for delta in np.arange(math.ceil(2 * d0) / 2, math.ceil(2 * d0) / 2 + 12.0, 1.0):
            for gap in (2.0, 6.0, 12.0, 20.0):
                dk = plan(float(R), float(delta), gap)
                ok, c = check(dk, V)
                if ok and dk["span_deg"][1] - dk["span_deg"][0] < 360.0 - 2 * delta:
                    return dk, c
    return None, None


# ---------------------------------------------------------------------------------------------- 3. the stack
def stack(V):
    """the redesign's stack() with the S1b deck's nets: the column's node-2 plate moves to the clearance its peak against
    the deck's nets needs; everything else is the redesign's [IR there]."""
    nets_deck = ["0", "1", "2", "3", "m1"]
    w = ML.worst(V, ["2"], nets_deck)
    c_col = math.ceil(ML.clearance(w["pk"]))
    h_parts = ML.DECK_Z0 + ML.DECK_T + ML.DECK_H
    return dict(c_col_mm=c_col, c_col_pair=w, h_parts_mm=h_parts, h_col_mm=h_parts + c_col,
                h_col_redesign_mm=h_parts + 39.0, dh_mm=39.0 - c_col,
                note="the redesign's column sat 39 mm from the deck's parts (sim/multiplier-layout-3d-findings.md); "
                     "each side's stack beyond the deck moves in by dh")


def figure(dkA, dkB, path):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.patches import Circle
    fig, axs = plt.subplots(1, 2, figsize=(12, 6))
    for ax, dk, side in ((axs[0], dkA, "A (below the hub)"), (axs[1], dkB, "B (above, mirrored)")):
        ax.add_patch(Circle((0, 0), ML.CAN_R, fill=False, color="#888", lw=1.5))
        ax.add_patch(Circle((0, 0), ML.CAGE_R0, fill=False, color="#bbb", lw=1, ls="--"))
        ax.add_patch(Circle((0, 0), ML.DECK_R1, fill=False, color="#ddd", lw=0.8, ls=":"))
        col = {"stick": "#c0392b", "clamp_half": "#2e86c1"}
        for q in dk["parts"]:
            P = np.array(q["pts"])
            # the potted housing: discs of its radius along its axis (its outline in plan) [OC: the envelope]
            for k in range(len(P) - 1):
                for f in np.linspace(0, 1, 12):
                    ax.add_patch(Circle(tuple(P[k] + f * (P[k + 1] - P[k])), q["rad"], color=col[q["kind"]],
                                        alpha=0.06, lw=0))
            B = np.array(q["body_pts"])
            ax.plot(B[:, 0], B[:, 1], color=col[q["kind"]], lw=3)
            c = np.array(q["centre"]) * 1.18
            ax.text(c[0], c[1], f"{q['name']}\n{q['nets'][0]}->{q['nets'][1]}", ha="center", va="center", fontsize=8)
        for n, p in dk["junctions"].items():
            ax.plot(*p, "ko", ms=4)
            ax.text(p[0] * 0.84, p[1] * 0.84, "REF" if n.startswith("0") else f"N{n.rstrip('x')}" + (
                " (cross)" if n.endswith("x") else ""), fontsize=7, ha="center", va="center")
        for L in dk["leads"]:                  # the leads over the parts, drawn round the lane (their route) [IR]
            ta, tb = (math.degrees(math.atan2(L[k][1], L[k][0])) for k in ("a", "b"))
            if tb - ta > 180:
                tb -= 360
            if ta - tb > 180:
                ta -= 360
            ra, rb = float(np.linalg.norm(L["a"])), float(np.linalg.norm(L["b"]))
            tt = np.linspace(ta, tb, 40)
            rr = np.linspace(ra, rb, 40) + 14.0 * np.sin(np.linspace(0, math.pi, 40))
            ax.plot(rr * np.cos(np.radians(tt)), rr * np.sin(np.radians(tt)), color="#7d3c98", lw=1, ls="--")
            m = len(tt) // 2
            ax.text(rr[m] * math.cos(math.radians(tt[m])) * 1.08, rr[m] * math.sin(math.radians(tt[m])) * 1.08,
                    f"lead {L['net']}", fontsize=6, color="#7d3c98", ha="center")
        for s_ in dk["straps"]:
            ax.plot([s_["a"][0], s_["b"][0]], [s_["a"][1], s_["b"][1]], color="#555", lw=1)
        ax.axhline(0, color="#aaa", lw=0.5, ls="-.")
        ax.set_aspect("equal")
        ax.set_xlim(-175, 175)
        ax.set_ylim(-175, 175)
        ax.set_title(f"deck {side}: lane r {dk['R']:.0f} mm")
        ax.set_xlabel("x (mm)")
    fig.suptitle("S2a: the compact deck for the S1b circuit (rebuild/s2_models/s2_deck.py); the can r 48, "
                 "the cage r 162 (dashed), the redesign's deck edge r 150 (dotted); shaded: the potted housings; dashed purple: "
                 "the leads", fontsize=8)
    fig.tight_layout()
    fig.savefig(path, dpi=130)


def main():
    global BARE_CAN
    BARE_CAN = "--bare-can" in sys.argv
    tag = "_bare" if BARE_CAN else ""
    res_path = os.path.join(HERE, f"s2_deck{tag}_results.json")
    old = json.load(open(res_path)) if "--reuse-volts" in sys.argv and os.path.exists(res_path) else {}
    V = old.get("volts_design") or volts(DESIGN_CASE["zscale"])
    Vn = old.get("volts_nominal") or volts((1.0, 1.0))
    print("volts (+5 %):", {k: round(v["pk"], 2) for k, v in V["pairs"].items()})
    dkA, cA = search(V)
    if dkA is None:
        print("no plan passes")
        return
    bal_chain = balance(dkA)
    bz = balanced(dkA, V)
    if bz is not None:
        dkA, cA, bal = bz
    else:
        bal = bal_chain
    dkB = plan(dkA["R"], dkA["delta_deg"], dkA["gap_mm"], mirror=True, z_place=dkA.get("z_place"))
    okB, cB = check(dkB, V)
    print(f"chain plan: {bal_chain['balance_mass_g_at_lane']:.0f} g balance mass; with Z1 placed to balance: "
          f"{bal['balance_mass_g_at_lane']:.0f} g (Z1 at {dkA.get('z_place')})")
    st = stack(V)
    br = bracket(dkA, V)
    print(f"deck A: lane r {dkA['R']:.0f} mm, junctions +-{dkA['delta_deg']:.1f} deg, part gap {dkA['gap_mm']:.0f} mm; "
          f"spans {dkA['span_deg'][0]:.0f}..{dkA['span_deg'][1]:.0f} deg; solid OK {cA['all_solid']}, can/cage OK "
          f"{cA['all_can']}; bare short {cA['bare_short']}; deck B OK {okB}")
    print(f"stack: column clearance {st['c_col_mm']} mm (pair {st['c_col_pair']['pair']}, {st['c_col_pair']['pk']:.2f} kV) "
          f"against the redesign's 39 -> each side {st['dh_mm']:.0f} mm shorter")
    print(f"cross nets {cA['cross']['pair']}: {cA['cross']['U_pk_kV']:.2f} kV, wires {cA['cross']['wire_gap_mm']:.1f} mm apart "
          f"(bare needs {cA['cross']['clearance_mm']:.1f}); junctions OK {cA['junctions_ok']}")
    print(f"balance: {bal['imbalance_g_mm']:.0f} g mm at {bal['imbalance_deg']:.0f} deg -> {bal['balance_mass_g_at_lane']:.0f} g at "
          f"r {dkA['R']:.0f}, {bal['balance_at_deg']:.0f} deg; plate r {bal['plate_r_mm'][0]:.0f}-{bal['plate_r_mm'][1]:.0f}, "
          f"{bal['plate_kg']*1e3:.0f} g; parts + junctions {bal['parts_and_junctions_kg']*1e3:.0f} g")
    print(f"bracket: PTFE arm r {br['r_mm'][0]:.0f}-{br['r_mm'][1]:.0f} x {br['width_mm']:.0f} x {br['thickness_mm']:.0f} mm at z 0, "
          f"{br['ribs']['n']} rib(s); creepage between the wires {br['creepage_between_wires']['have_mm']:.1f} / "
          f"{br['creepage_between_wires']['need_mm']:.1f} mm, to the can {br['creepage_wire_to_can']['have_mm']:.1f} / "
          f"{br['creepage_wire_to_can']['need_mm']:.1f} mm; {br['mass_g']:.0f} g (+ its twin); {br['load']['accel_g']:.0f} g, "
          f"{br['load']['wires_N']:.2f} N from the wires")
    for r in cA["pairs"]:
        print(f"   {r['a']}-{r['b']} {r['pair']}: U {r['U_pk_kV']:.2f} kV, housing gap {r['housing_gap_mm']:.1f}, body gap "
              f"{r['body_gap_mm']:.1f} mm (solid needs {r['solid_mm']:.1f}, bare {r['clearance_mm']:.1f})")
    for q in cA["to_can"]:
        print(f"   {q['part']}: r {q['r_min_mm']:.1f}-{q['r_max_mm']:.1f}, to the can {q['to_can_mm']:.1f}, cage {q['to_cage_mm']:.1f} mm; "
              f"body to can {q['body_to_can_mm']:.1f} (bare needs {q['clearance_mm']:.1f})")
    figure(dkA, dkB, os.path.join(HERE, f"s2-deck-plan{tag}.png"))
    out = dict(inputs=dict(parts=PARTS, design_case=DESIGN_CASE, envelopes={k: ML.PART[k] for k in ("stick", "clamp", "clamp_half")},
                           rules="sim/multiplier_layout.py deck_check, clearance; sim/parts_first_cut.py E_POT "
                                 f"{PF.E_POT} kV/mm, CLR_MARGIN {PF.CLR_MARGIN}",
                           can_r=ML.CAN_R, cage_r0=ML.CAGE_R0, deck_r=(ML.DECK_R0, ML.DECK_R1),
                           deck_z=(ML.DECK_Z0, ML.DECK_Z0 + ML.DECK_T + ML.DECK_H)),
               volts_design=V, volts_nominal=Vn, deck_A=dkA, deck_B=dkB, check_A=cA, check_B=cB, stack=st, balance=bal, balance_chain=bal_chain, bracket=br,
               redesign=dict(parts_per_deck=13, junctions=10, deck_r=(ML.DECK_R0, ML.DECK_R1), lane_r=(ML.R_I, ML.R_O)))
    out["inputs"]["bare_clearance_to_can_required"] = BARE_CAN
    json.dump(out, open(res_path, "w"), indent=1, default=float)


if __name__ == "__main__":
    main()
