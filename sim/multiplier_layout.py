#!/usr/bin/env python3
"""sim/multiplier_layout.py -- the mechanical layout of the multiplier stacked into the doubler (PROPOSED): where its
capacitors and diodes sit in the machine's stack, side B on top and side A below, and what that does to the circuit,
the hub's field and the shafts.

The circuit is sim/integrated_multiplier.py's proposal at its pick (C1 / C2 in phase, chain 2 reversed, one ring stage
per chain; sim/integrated-multiplier-findings.md), the setup the designer took "for now" on 2026-10-11.

1. The working voltages: the pick's steady state re-run as built (ideal diodes, sim/integrated_multiplier.py's deck);
   every node's and every pair's peak and rms over its last cycles [OC: the deck].
2. The stack (side A from the hub outward; side B its mirror):
   - the hub as locked, inside a grounded can on the rotor (r 60, |z| <= 85);
   - the deck: a G10 ring round the can carrying every diode, C3-C8, Csa / Csb and the clamp string, each part potted;
   - the column: Ca / Cb as the record's six plates, node 2 / 3 toward the deck, node 1 / 4 toward the vanes;
   - the vane stack, the record's 6 + 6 with its ends swapped, a rotor vane at its hub end;
   - the Ca|reluctance bearing and the reluctance section as the record.
   The record's hub-face bearings go: a counter-rotor spider between the vanes and the hub leaves no path for a rotor
   wire except the shaft [OC: the bodies], and nodes 1 / 4 cannot run in the shaft (0.0027 of z per pF,
   sim/tube-strays-findings.md §5). Each axial gap is the clearance its two sides' peak needs (IEC 60664-1 as
   sim/parts_first_cut.py applies it) [IR].
3. The decks' plans: each part's place and envelope and its nets; the distances against the bare clearance and the
   solid insulation of the potting [IR; RH: the parts' envelopes].
4. The interfaces, as sim/parts-first-cut-findings.md §4 tabulates them for the record [IR].
5. The grounded can: the field at the null and the rings' capacitance with the can as the hub's REF boundary, against
   the record's box (sim/hub_beads_settled.py hub_solve, the record's beads and grooves) [OC: the solver].
6. The strays the layout changes, per node [RH: line, cylinder and plate formulas, not a field solve]; the circuit with
   them (z, the rings), and C3-C6 picked again by the study's rule (the rings at the record's level, never above).
7. The shafts without the hub-face bearings: sim/shaft_bearings.py's two-body model of record with its solids moved
   to this layout and the new parts added [IR].
8. The masses, the length and the decks' balance.
Writes sim/multiplier_layout_results.json; the findings are sim/multiplier-layout-findings.md; the drawing is
docs/make_multiplier_layout.py.
Tags (CONVENTIONS.md §1): [OC] derivable from the circuit or the geometry; [IR] a modelling or engineering choice,
datasheet-class values included; [RH] heuristic, not load-bearing. g is a gap, never a bare d.
Usage: python3 sim/multiplier_layout.py [--procs 4] [--only volts strays hub shaft]   (about 10 minutes; needs
ngspice and OCP)
"""
import argparse
import copy
import json
import math
import os
import sys
import time
from multiprocessing import Pool

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
import stack_sizing as S                 # noqa: E402  (shaft, sleeve, bearing, flange of record)
import integrated_multiplier as IM       # noqa: E402  (the proposal's deck, the as-built set, V_op, the rings' rule)
import parts_first_cut as PF             # noqa: E402  (clearance, creepage, ribs, materials, the potting's rule)

OUT_JSON = os.path.join(HERE, "multiplier_layout_results.json")
SRC = {
    "circuit": "sim/integrated_multiplier.py topology('proposal'), build, spice; the pick: "
               "sim/integrated_multiplier_results.json pick (C3-C6 180 pF, the steady job)",
    "as_built": "sim/tube_strays_results.json decks.sets['as built'] (via sim/diodes_real.py AB_SET)",
    "strays_record": "sim/tube-strays-findings.md §3 (node 1 / 4 and node 2 / 3 by the part reached)",
    "stack": "sim/stack_sizing.py SHAFT_R, SLEEVE_R, BEARING, FLANGE_T; the record's tube layout "
             "(sim/tube_geometry.py record_plates via sim/shaft_bearings.py record_parts)",
    "hub": "presets/hub-locked.json retainer, shaft_coupler, shaft",
    "rules": "sim/parts_first_cut.py clearance_case_a, creepage, ribbed, MATERIALS, DC_MARGIN, CLR_MARGIN, E_POT "
             "(sim/parts-first-cut-findings.md §4, §5)",
    "hub_field": "sim/hub_beads_settled.py hub_solve; sim/hub_rings_build_results.json record",
    "shaft": "sim/shaft_bearings.py record_parts, two_body; sim/shaft_bearings_record_results.json",
}
HUB = json.load(open(os.path.join(ROOT, "presets", "hub-locked.json")))
HV = lambda k: HUB[k]["value"]
PICK = json.load(open(os.path.join(HERE, "integrated_multiplier_results.json")))["pick"]
CL_PICK = PICK["C3_C6_pF"] * 1e-12

# ---------------------------------------------------------------------------------------------------- the stack
T_V, G_V, R_IN, R_OUT = 3.0, 6.0, 50.0, 150.0     # the record's vanes and plates: 3 mm Al, 6 mm gaps, r 50-150
N_VANES = 12                                       # 6 stator + 6 rotor vanes per stack (the record's pick)
N_CA = 6                                           # Ca / Cb: six full-annulus plates, five gaps (481.6 pF as built)
L_STACK = N_VANES * T_V + (N_VANES - 1) * G_V      # 102 mm
L_COL = N_CA * T_V + (N_CA - 1) * G_V              # 48 mm
REL_OUT = 198.0                                    # the record's Ca|reluctance bearing centre to the machine's end
SLOT = S.BEARING["slot"]                           # 20 mm, the bearing hub's slot (sim/stack_sizing.py)
CAGE_R0, CAGE_R1 = R_OUT + 12.0, R_OUT + 16.0      # the counter-rotor's G10 cage (the record's r 162-166)
RET_R, RET_Z = HV("retainer")["r_max_mm"], HV("retainer")["absz_max_mm"]          # 30, 72
CPL_R1, CPL_Z = RET_R + HV("shaft_coupler")["wall_mm"], 80.0                       # 33; |z| <= 80 (its shape)
FL_Z0, FL_Z1 = HV("shaft")["flange_absz_mm"]                                       # 72, 80
FL_R = RET_R                                        # the flanges turned to the coupler's bore (docs/rings-design.md §2)
SHAFT_R, SLEEVE_R = S.SHAFT_R, S.SLEEVE_R           # 12.5 (d 25 in the tube model), 20.5
# the grounded can over the hub (rotor, REF) [IR, PROPOSED]: an aluminium cylinder and two end discs on the shaft
CAN_R, CAN_T, CAN_Z, CAN_DISC_T = 48.0, 2.0, 85.0, 2.0
# the deck (per side) [IR, PROPOSED]: a G10 ring plate round the can, the parts potted on its outer face
DECK_R0, DECK_R1 = CAN_R + 2.0, R_OUT              # r 62-150: inside the cage with the record's 12 mm
DECK_Z0, DECK_T, DECK_H = 30.0, 6.0, 42.0           # the plate at |z| 30-36, the parts' zone |z| 36-78
POT = 8.0                                           # mm of silicone over each part (sim/parts-first-cut-findings.md §5)
LEAD_MIN = 3.0                                      # mm of lead each end of a part, at least [RH]
# the parts' envelopes: the body and its potted housing [RH: datasheet-class shapes, to be taken from the parts chosen]
PART = {
    "stick": dict(what="HV rectifier stick, 2CL77 class (20 kV, 5 mA, avalanche)", body_d=8.0, body_l=40.0),
    "rsurge": dict(what="22 kOhm surge resistor, HV thick film, >= 15 kV, >= 1 W", body_d=8.0, body_l=40.0),
    "c180": dict(what="180 pF / 30 kV, class 1 HV ceramic (or PP / PTFE film), screw terminals", body_d=30.0, body_l=22.0),
    "c100": dict(what="100 pF / 30 kV, class 1 HV ceramic (or film)", body_d=25.0, body_l=20.0),
    "c100h": dict(what="100 pF / 40 kV, class 1 HV ceramic (or film)", body_d=30.0, body_l=24.0),
    "clamp": dict(what="the clamp string: 66 x 1.5KE200A in a meander, its HV and REF ends at opposite ends",
                  body_w=34.0, body_l=134.0, body_h=20.0),
}
for k, p in PART.items():
    if k == "clamp":
        p.update(w=p["body_w"] + 2 * POT, l=p["body_l"] + 2 * POT, h=p["body_h"] + 2 * POT)
    else:
        p.update(d=p["body_d"] + 2 * POT, l=p["body_l"] + 2 * POT + (10.0 if k in ("stick", "rsurge") else 0.0))
# the circuit's mirror: side A's nets and parts and side B's (sim/integrated_multiplier.py M_MIRROR, extended)
MIRROR = {"0": "0", "1": "4", "2": "3", "l1": "r1", "r1": "l1", "l2": "r2", "r2": "l2", "xa": "xb", "ea": "eb"}
MIRROR.update({v: k for k, v in list(MIRROR.items())})
PART_MIRROR = {"D1": "D2", "D3": "D4", "D5": "D6", "D8": "D7", "D11": "D9", "D12": "D10", "C3": "C4", "C6": "C5",
               "C8": "C7", "Csa": "Csb", "Z1": "Z4", "R1": "R2", "R3": "R4"}


# ==================================================================================================== 1. the volts
def run_deck(job):
    """the proposal as built at C3-C6 = job cl, with per-node strays job strays (F; the new nodes) and nodes 1-4's strays
    job cp (F; None: as built), from the consistent 1 kV start. keep: every node's waveform statistics over the last
    eight cycles."""
    t0 = time.time()
    Sab = copy.deepcopy(IM.SET_AB)
    if job.get("cp"):
        Sab["Cp"] = dict(Sab["Cp"], **job["cp"])
    el = IM.topology("proposal", cl=job["cl"], c7=job.get("c7", IM.C_CW), s_new=0.0)
    el += [("C", f"Cn_{n}", n, "0", c) for n, c in sorted(job["strays"].items()) if c > 0]
    clamp = job.get("clamp", True)
    if not clamp:
        el = [e for e in el if e[0] != "Z"]
    n = job["n_cyc"]
    txt, vecs, pk = IM.build(el, Sab, phase="in", model="ND", ic=IM.seeds("proposal", job.get("v0", 1000.0)), n_cyc=n,
                             steps=job.get("steps", IM.STEPS), vop=job.get("vop", IM.V_OP))
    raw, rt, err = IM.spice(txt, n)
    out = dict(job=job, run_s=round(time.time() - t0, 1))
    if raw is None or rt is None:
        return dict(out, done=False, error=err)
    t = raw[:, 0]
    c = {v: raw[:, 2 * i + 1] for i, v in enumerate(vecs)}
    cyc = [(t >= k * IM.T - 1e-12) & (t < (k + 1) * IM.T - 1e-12) for k in range(n)]
    pk1 = [float(max(np.abs(c["v(1)"][m]).max(), np.abs(c["v(4)"][m]).max())) for m in cyc]
    lo = job.get("fit_from", 3)
    out["z"] = float(math.exp(np.polyfit(np.arange(lo, n), np.log(np.maximum(np.array(pk1[lo:n]), 1e-30)), 1)[0]))
    out["done"] = True
    if not clamp:
        return out
    gap = c["v(eb)"] - c["v(ea)"]
    gk = [float(gap[m].mean() / 1e3) for m in cyc]
    s = t >= (n - 8) * IM.T - 1e-12
    out.update(V_A_kV=float(np.mean(c["v(ea)"][s]) / 1e3), V_B_kV=float(np.mean(c["v(eb)"][s]) / 1e3),
               settled=IM.settled(gk), gap_last_kV=gk[-1])
    out["E_null_kV_cm"] = float(IM.K_NULL * np.mean(gap[s]) / 1e3)
    if job.get("keep"):
        vn = {v[2:-1]: c[v][s] for v in vecs if v.startswith("v(") and not v.startswith("v(e_") and v != "v(s)"}
        vn["0"] = np.zeros(int(s.sum()))
        nodes = sorted(vn)
        out["V_kV"] = {k: dict(min=float(vn[k].min() / 1e3), max=float(vn[k].max() / 1e3), mean=float(vn[k].mean() / 1e3),
                               rms=float(math.sqrt(np.mean(vn[k] ** 2)) / 1e3)) for k in nodes if k != "0"}
        pairs = {}
        for i, a in enumerate(nodes):
            for b in nodes[i + 1:]:
                dv = (vn[a] - vn[b]) / 1e3
                pairs[f"{a}|{b}"] = dict(pk=float(np.abs(dv).max()), rms=float(math.sqrt(np.mean(dv * dv))),
                                         min=float(dv.min()), max=float(dv.max()))
        out["pairs"] = pairs
    return out


def pool(jobs, procs, log):
    with Pool(procs) as p:
        res = p.map(run_deck, jobs)
    for r in res:
        j = r["job"]
        log(f"  {j.get('tag', '')}: cl {j['cl'] * 1e12:.0f} pF, n {j['n_cyc']}: "
            + (f"z {r['z']:.4f}" if r.get("done") else "FAILED")
            + (f", rings {r['V_A_kV']:+.3f} / {r['V_B_kV']:+.3f} kV, settled {r['settled']}" if "V_A_kV" in r else "")
            + f" ({r['run_s']:.0f} s)")
    return res


def volt(V, a, b):
    """the pair a-b's statistics from the steady run (the order of the key is alphabetical)."""
    if a == b:
        return dict(pk=0.0, rms=0.0)
    k = f"{a}|{b}" if f"{a}|{b}" in V["pairs"] else f"{b}|{a}"
    return V["pairs"][k]


def worst(V, nets_a, nets_b):
    """the largest peak (and its rms) between any net of nets_a and any of nets_b."""
    best = dict(pk=0.0, rms=0.0, pair=None)
    for a in nets_a:
        for b in nets_b:
            q = volt(V, a, b)
            if q["pk"] > best["pk"]:
                best = dict(pk=q["pk"], rms=q["rms"], pair=f"{a}-{b}")
    return best


def clearance(u_pk):
    return PF.clearance_case_a(PF.CLR_MARGIN * u_pk) if u_pk > 0 else 0.0


# ==================================================================================================== 2. the stack
def stack(V):
    """every element of the layout, side A from the hub outward (h = |z| from the hub's centre), with its body and
    node; the column's place from the clearance between its node-2 plate and the deck's nets."""
    nets_deck = ["0", "1", "2", "l1", "r1", "r2", "xa", "ea"]
    w = worst(V, ["2"], nets_deck)
    c_col = math.ceil(clearance(w["pk"]))
    h_parts = DECK_Z0 + DECK_T + DECK_H                              # the parts' outer face, |z| 78
    h_col = h_parts + c_col                                          # the column's node-2 plate
    el = []

    def add(kind, body, node, h0, h1, r0, r1, **kw):
        el.append(dict(kind=kind, body=body, node=node, h0=h0, h1=h1, r0=r0, r1=r1, **kw))
    # the hub as locked (the drawing's outline; the solids are sim/tube_geometry.py's)
    add("retainer", "rotor", "", 0.0, RET_Z, 0.0, RET_R)
    add("coupler", "rotor", "", 0.0, CPL_Z, RET_R, CPL_R1)
    add("flange", "rotor", "REF", FL_Z0, FL_Z1, 0.0, FL_R)
    add("can", "rotor", "REF", 0.0, CAN_Z, CAN_R - CAN_T, CAN_R)
    add("can disc", "rotor", "REF", CAN_Z, CAN_Z + CAN_DISC_T, SHAFT_R, CAN_R)
    add("deck plate", "rotor", "", DECK_Z0, DECK_Z0 + DECK_T, DECK_R0, DECK_R1)
    add("deck parts", "rotor", "HV", DECK_Z0 + DECK_T, h_parts, DECK_R0, DECK_R1, envelope=True)
    # the column: node 2 toward the deck, node 1 toward the vanes (the record's plates, its order reversed)
    for k in range(N_CA):
        h0 = h_col + k * (T_V + G_V)
        add("Ca plate", "rotor", "2" if k % 2 == 0 else "1", h0, h0 + T_V, R_IN, R_OUT, index=N_CA - k)
    h = h_col + L_COL + G_V                                          # the dead gap: node 1 against node 1
    for k in range(N_VANES):                                         # from the hub end: rotor, stator, ...
        rotor = k % 2 == 0
        add("C1 vane", "rotor" if rotor else "stator", "1" if rotor else "0", h, h + T_V,
            S.SLEEVE_R if rotor else R_IN, R_OUT if rotor else R_OUT + 12.0, index=k + 1)
        h += T_V + G_V
    h_vanes_end = h - G_V
    h_brg = h_vanes_end + G_V + 0.5 * SLOT                            # the Ca|reluctance bearing's centre
    add("bearing", "bearing", "", h_brg - 0.5 * S.BEARING["width"], h_brg + 0.5 * S.BEARING["width"], SHAFT_R,
        0.5 * S.BEARING["od"], where="Ca|reluctance")
    add("spider", "stator", "", h_brg - 0.5 * S.BEARING["spider_t"], h_brg + 0.5 * S.BEARING["spider_t"],
        0.5 * S.BEARING["od"], CAGE_R0, where="Ca|reluctance")
    add("sleeve", "rotor", "", CAN_Z + CAN_DISC_T, h_brg - 0.5 * S.BEARING["width"], SHAFT_R, SLEEVE_R)
    add("cage", "stator", "", 0.0, h_brg, CAGE_R0, CAGE_R1)
    h_end = h_brg + REL_OUT
    add("reluctance", "mixed", "", h_brg + 0.5 * SLOT, h_end, SLEEVE_R, CAGE_R0 - 5.0, envelope=True,
        note="the record's wound utrons, carrier discs, bridges and bridge ring, unchanged (sim/tube_geometry.py)")
    add("end bearing", "frame", "", h_end - 10.0 - 0.5 * S.BEARING["width"], h_end - 10.0 + 0.5 * S.BEARING["width"],
        SHAFT_R, 0.5 * S.BEARING["od"])
    add("shaft", "rotor", "REF", FL_Z1, h_end, 0.0, SHAFT_R)
    # the record's Ca|reluctance bearing sits 272 mm from the hub's centre (sim/stack_sizing.py layout, record)
    L = 2.0 * h_end
    return dict(elements=el, c_col_mm=c_col, c_col_pair=w, h_parts_mm=h_parts, h_col_mm=h_col, h_vanes=(h_col + L_COL + G_V,
                h_vanes_end), h_bearing_mm=h_brg, h_end_mm=h_end, L_mm=L, L_record_mm=940.0, dL_mm=L - 940.0,
                dh_side_mm=h_brg - 272.0)


def record_reluctance(dh):
    """the record's reluctance sections and end bearings (sim/stack_sizing.py layout of record, the wound utrons) for
    the drawing: side A where it was, side B moved out by the layout's growth (2 dh) [OC: the record's elements]."""
    import tube_geometry as TG
    lad = S.size_stack("tube", TG.record_plates())
    keep = ("w utron", "w disc", "w bridge", "w ring", "w flange", "bearing")
    out = []
    for e in lad["tube_geometry"]["elements"]:
        if e["kind"] not in keep or (e["kind"] == "bearing" and e.get("where") != "end"):
            continue
        q = {k: v for k, v in e.items() if isinstance(v, (int, float, str))}
        if e["kind"] == "w ring":
            q["pocket_r1"] = e["pockets"]["r1"]
        shift = 0.0 if e["z1"] <= 470.0 else 2.0 * dh
        for k in ("z0", "z1", "zc", "zs0", "zs1"):
            if k in q:
                q[k] += shift
        out.append(q)
    return out


# ==================================================================================================== 3. the decks
def pol(r, th):
    t = math.radians(th)
    return np.array([r * math.cos(t), r * math.sin(t)])


# deck A's plan [IR, PROPOSED], (r mm, theta deg). Two lanes on the plate's outer face:
#   the outer lane (r 132): the eight sticks lying along it as one chain round the deck,
#       REF - R1 - 0' - D1 - 2 - R3 - 2' - D3 - r1 | l1 - D5 - r2 - D8 - 1 - D11 - xa - D12 - ea,
#     each junction a potted block between two housings' ends;
#   the inner lane (r 90): C3, C6 and C8 standing, the clamp string Z1 as an arc module, its HV end under node 1's
#     junction; Csa standing beyond the chain's end;
#   REF: straps to the can from R1's end, Z1's REF end and Csa's foot; the rest joined by PTFE HV wire over the parts.
# The open sector (Csa to R1's REF end, 44 deg) parts ring A's ea from REF. Deck B is deck A mirrored about the
# bisector of A's two cross-net junctions (r1, l1), its nets and parts mirrored (MIRROR, PART_MIRROR): so B's l1 lies
# over A's l1 and B's r1 over A's r1, and the cross nets run straight across.
R_O, R_I = 132.0, 90.0
JUNC_A = {"0": -149.7, "0'": -120.1, "2": -88.9, "2'": -57.7, "r1": -27.8, "l1": -14.8, "r2": 15.1, "1": 46.3,
          "xa": 77.5, "ea": 107.4}
PARTS_A = [  # name, kind, its two nets (the ends' order along the lane), centre (r, theta), orientation
    ("R1", "rsurge", ("0", "0"), (R_O, -135.7), "tan"),
    ("D1", "stick", ("0", "2"), (R_O, -104.5), "tan"),
    ("R3", "rsurge", ("2", "2"), (R_O, -73.3), "tan"),
    ("D3", "stick", ("2", "r1"), (R_O, -42.1), "tan"),
    ("D5", "stick", ("l1", "r2"), (R_O, -0.5), "tan"),
    ("D8", "stick", ("r2", "1"), (R_O, 30.7), "tan"),
    ("D11", "stick", ("1", "xa"), (R_O, 61.9), "tan"),
    ("D12", "stick", ("xa", "ea"), (R_O, 93.1), "tan"),
    ("C3", "c180", ("2", "l1"), (86.0, -68.0), "up"),
    ("C6", "c180", ("r1", "r2"), (85.0, -30.0), "up"),
    ("C8", "c100", ("r2", "xa"), (102.0, 15.1), "up"),                # under r2's junction
    ("Z1", "clamp", ("1", "0"), (R_I, 76.0), "arc"),               # its HV end beyond D11, its REF end under the open sector
    ("Csa", "c100h", ("ea", "0"), (126.0, 172.0), "up"),
]
TH_M = 0.5 * (JUNC_A["r1"] + JUNC_A["l1"])                         # deck B's mirror line
# R1 and R3 sit in series with D1 and D3 (sim/parts-first-cut-findings.md §2.2): R1 at D1's REF end, R3 at D3's node-2
# end; their ends are at their diode's net within 2 mV (22 kOhm x 81 uA), so the plan gives each one net.
# the leads: (from, to) as junction names or part terminals 'P:k' (k = 0, 1 the part's ends in its nets' order)
LEADS_A = [("C3:0", "2"), ("C3:1", "l1"), ("C6:0", "r1"), ("C6:1", "r2"), ("C8:0", "r2"), ("C8:1", "xa"),
           ("Z1:0", "1"), ("Csa:0", "ea")]
STRAPS_A = [("R1:0", "0"), ("Z1:1", "0"), ("Csa:1", "0")]          # to the can


def plan(mirror=False):
    """the deck as drawn: each part's centre, its axis as a polyline (a standing part: one point), its envelope's
    half-width, its terminals, its two nets; the junctions; the leads and straps."""
    th_ = (lambda t: 2.0 * TH_M - t) if mirror else (lambda t: t)
    mp = (lambda n: MIRROR[n]) if mirror else (lambda n: n)
    junc = {}
    for k, th in JUNC_A.items():
        n = k.rstrip("'")
        junc[mp(n) + ("'" if k.endswith("'") else "")] = pol(R_O, th_(th)).tolist()
    out = []
    for nm, kind, (na, nb), (r, th), orient in PARTS_A:
        p = PART[kind]
        c = pol(r, th_(th))
        if orient == "up":
            pts, body, rad, term = [c], [c], 0.5 * p["d"], [c, c]
        elif orient == "arc":
            span = math.degrees((p["l"] - p["w"]) / r)               # the module's ends are its envelope's round
            ths = np.linspace(th, th + span, 9)
            pts, rad = [pol(r, th_(t)) for t in ths], 0.5 * p["w"]
            body = pts
            term = [pol(r, th_(th - math.degrees(0.5 * p["w"] / r))), pol(r, th_(th + span + math.degrees(0.5 * p["w"] / r)))]
            c = pol(r, th_(th + 0.5 * span))
        else:
            t = np.array([-math.sin(math.radians(th_(th))), math.cos(math.radians(th_(th)))])
            rad = 0.5 * p["d"]
            # the housing as a capsule with its rounds inside its flat ends; the body its central length; the
            # terminals at the housing's ends
            pts = [c - (0.5 * p["l"] - rad) * t, c + (0.5 * p["l"] - rad) * t]
            body = [c - 0.5 * p["body_l"] * t, c + 0.5 * p["body_l"] * t]
            term = [c - 0.5 * p["l"] * t, c + 0.5 * p["l"] * t]
            if mirror:
                pts, body, term = pts[::-1], body[::-1], term[::-1]
        out.append(dict(name=PART_MIRROR[nm] if mirror else nm, kind=kind, nets=(mp(na), mp(nb)),
                        centre=c.tolist(), pts=[q.tolist() for q in pts], body_pts=[q.tolist() for q in body], rad=rad,
                        orient=orient, terminals=[term[0].tolist(), term[-1].tolist()]))
    names = {q["name"]: q for q in out}
    pm = (lambda s: PART_MIRROR[s]) if mirror else (lambda s: s)

    def where(x):
        if ":" in x:
            nm, k = x.split(":")
            return names[pm(nm)]["terminals"][int(k)]
        n = x.rstrip("'")
        return junc[mp(n) + ("'" if x.endswith("'") else "")]
    leads = [dict(a=where(a), b=where(b), net=names[pm(a.split(":")[0])]["nets"][int(a.split(":")[1])]) for a, b in LEADS_A]
    straps = []
    for a, _ in STRAPS_A:
        p0 = where(a)
        r0 = float(np.linalg.norm(p0))
        straps.append(dict(a=p0, b=(np.asarray(p0) * CAN_R / r0).tolist()))
    return dict(junctions=junc, parts=out, leads=leads, straps=straps, mirror_deg=TH_M if mirror else None)


def seg_dist(p0, p1, q0, q1):
    """the least distance between two segments in the plane (equal ends make a point)."""
    p0, p1, q0, q1 = map(np.asarray, (p0, p1, q0, q1))

    def pt_seg(x, a, b):
        ab = b - a
        L2 = float(ab @ ab)
        u = 0.0 if L2 == 0 else max(0.0, min(1.0, float((x - a) @ ab) / L2))
        return float(np.linalg.norm(x - (a + u * ab)))
    d = min(pt_seg(p0, q0, q1), pt_seg(p1, q0, q1), pt_seg(q0, p0, p1), pt_seg(q1, p0, p1))

    def cross(a, b, c):
        return (b[0] - a[0]) * (c[1] - a[1]) - (b[1] - a[1]) * (c[0] - a[0])
    if (np.linalg.norm(p1 - p0) > 0 and np.linalg.norm(q1 - q0) > 0 and
            cross(p0, p1, q0) * cross(p0, p1, q1) < 0 and cross(q0, q1, p0) * cross(q0, q1, p1) < 0):
        d = 0.0
    return d


def poly_dist(P, Q):
    """the least distance between two polylines (a single point is a polyline of one)."""
    P = P if len(P) > 1 else [P[0], P[0]]
    Q = Q if len(Q) > 1 else [Q[0], Q[0]]
    return min(seg_dist(P[i], P[i + 1], Q[j], Q[j + 1]) for i in range(len(P) - 1) for j in range(len(Q) - 1))


def pieces(q, n_seg=6):
    """a part as pieces (a polyline, the potentials its two ends hold as mixes of the part's two nets): a lying part
    grades linearly from its first net to its second (series junctions, a resistive or capacitive grading) [IR], so a
    piece at the fraction f holds (1 - f) V_a + f V_b; a standing part holds either net at one place."""
    na, nb = q["nets"]
    if q["orient"] == "up":
        return [(q["pts"], [{na: 1.0}, {nb: 1.0}])]
    P = [np.asarray(x) for x in q["body_pts"]]
    if len(P) == 2:
        P = [P[0] + (P[1] - P[0]) * k / n_seg for k in range(n_seg + 1)]
    n = len(P)
    return [([P[i].tolist(), P[i + 1].tolist()],
             [{na: 1 - i / (n - 1), nb: i / (n - 1)}, {na: 1 - (i + 1) / (n - 1), nb: (i + 1) / (n - 1)}]) for i in range(n - 1)]


def u_bound(V, sa, sb):
    """the peak between two mixed potentials: |sum_x sa_x V_x - sum_y sb_y V_y| <= sum sa_x sb_y |V_x - V_y|_pk, the
    weights summing to one on each side [OC: the triangle inequality]; linear in each end's fraction, so a piece's
    bound is the larger at its two ends."""
    return sum(wa * wb * volt(V, x, y)["pk"] for x, wa in sa.items() for y, wb in sb.items() if wa > 0 and wb > 0)


def deck_check(dk, V):
    """every pair of parts on a deck, piece by piece: the housings may not overlap where their potentials differ; the
    bodies' distance (the axes' distance less both body radii) against the solid insulation the potting gives (the
    peak / 2 kV/mm, sim/parts_first_cut.py E_POT) and against the bare clearance (as if unpotted) for the peak
    between the two pieces [IR]. Every part also against the can (REF) and the cage."""
    rows, parts = [], dk["parts"]
    body_r = lambda q: 0.5 * (PART[q["kind"]].get("body_d") or PART[q["kind"]]["body_w"])
    P = {q["name"]: pieces(q) for q in parts}
    for i, a in enumerate(parts):
        for b in parts[i + 1:]:
            gap_h = poly_dist(a["pts"], b["pts"]) - a["rad"] - b["rad"]          # the housings (flat-ended)
            w = None
            for pa, sa in P[a["name"]]:
                for pb, sb in P[b["name"]]:
                    u = max(u_bound(V, x, y) for x in sa for y in sb)
                    gap_b = poly_dist(pa, pb) - body_r(a) - body_r(b)
                    q = dict(U=u, gap_b=gap_b, m_bare=gap_b - clearance(u), m_solid=gap_b - u / PF.E_POT)
                    if w is None or q["m_bare"] < w["m_bare"]:
                        w = dict(q, worst_solid=w["worst_solid"] if w else q)
                    if q["m_solid"] < w["worst_solid"]["m_solid"]:
                        w["worst_solid"] = q
            ws = w["worst_solid"]
            rows.append(dict(a=a["name"], b=b["name"], pair=f"{'/'.join(a['nets'])} - {'/'.join(b['nets'])}",
                             U_pk_kV=w["U"], housing_gap_mm=gap_h, body_gap_mm=w["gap_b"],
                             solid_mm=w["U"] / PF.E_POT, clearance_mm=clearance(w["U"]),
                             ok_solid=bool(gap_h >= 0.0 and ws["m_solid"] >= 0.0), ok_bare=bool(w["m_bare"] >= 0.0),
                             solid_margin_mm=min(gap_h, ws["m_solid"]), bare_margin_mm=w["m_bare"]))
    can = []
    for a in parts:
        rs = [float(np.linalg.norm(e)) for e in a["pts"]]
        r_min, r_max = min(rs) - a["rad"], max(rs) + a["rad"]
        worst_c = None
        for pa, sa in P[a["name"]]:
            u = max(u_bound(V, x, {"0": 1.0}) for x in sa)
            g = min(float(np.linalg.norm(e)) for e in pa) - body_r(a) - CAN_R          # the body to the can
            m = g - clearance(u)
            if worst_c is None or m < worst_c["m"]:
                worst_c = dict(m=m, u=u, g=g)
        can.append(dict(part=a["name"], r_min_mm=r_min, r_max_mm=r_max, to_can_mm=r_min - CAN_R, to_cage_mm=CAGE_R0 - r_max,
                        U_pk_kV=worst_c["u"], body_to_can_mm=worst_c["g"], clearance_mm=clearance(worst_c["u"]),
                        ok=bool(r_min >= DECK_R0 and CAGE_R0 - r_max >= 12.0 and worst_c["g"] >= worst_c["u"] / PF.E_POT),
                        ok_bare=bool(worst_c["m"] >= 0.0)))
    return dict(pairs=rows, to_can=can, n_pairs=len(rows), all_solid=all(r["ok_solid"] for r in rows),
                all_bare=all(r["ok_bare"] for r in rows), all_can=all(q["ok"] for q in can),
                n_bare_short=sum(1 for r in rows if not r["ok_bare"]),
                bare_short=[(r["a"], r["b"], round(r["bare_margin_mm"], 1)) for r in rows if not r["ok_bare"]],
                can_bare_short=[(q["part"], round(q["body_to_can_mm"] - q["clearance_mm"], 1)) for q in can if not q["ok_bare"]],
                worst_bare=min(rows, key=lambda r: r["bare_margin_mm"]),
                worst_solid=min(rows, key=lambda r: r["solid_margin_mm"]),
                min_housing_gap=min(rows, key=lambda r: r["housing_gap_mm"]))


def part_volume(a):
    """the housing's and the body's volumes (mm^3) of a placed part."""
    p = PART[a["kind"]]
    if a["kind"] == "clamp":
        return p["w"] * p["l"] * p["h"], p["body_w"] * p["body_l"] * p["body_h"]
    return math.pi / 4 * p["d"] ** 2 * p["l"], math.pi / 4 * p["body_d"] ** 2 * p["body_l"]


def deck_mass(dk):
    """the deck's mass and its centroid's offset from the axis (the balance) [RH: silicone 1.15, G10 1.85, the parts'
    bodies 2.5 g/cm3 (glass, ceramic and metal); each junction a 20 mm block of silicone]."""
    m_tot, mx = 0.0, np.zeros(2)
    for a in dk["parts"]:
        v_h, v_b = part_volume(a)
        m = ((v_h - v_b) * 1.15 + v_b * 2.5) * 1e-6                  # kg
        m_tot += m
        mx += m * np.asarray(a["centre"])
    for k, c in dk["junctions"].items():
        m = math.pi / 4 * 20.0 ** 2 * 20.0 * 1.15e-6
        m_tot += m
        mx += m * np.asarray(c)
    m_plate = math.pi * (DECK_R1 ** 2 - DECK_R0 ** 2) * DECK_T * 1.85e-6
    off = float(np.linalg.norm(mx) / (m_tot + m_plate))
    ang = float(math.degrees(math.atan2(mx[1], mx[0])))
    return dict(parts_kg=m_tot, plate_kg=m_plate, kg=m_tot + m_plate, offset_mm=off, offset_deg=ang,
                imbalance_g_mm=float(np.linalg.norm(mx) * 1e3),
                balance_mass_g_at_r140=float(np.linalg.norm(mx) * 1e3 / 140.0))


# ==================================================================================================== 4. interfaces
def interfaces(V, st, chk):
    """the layout's interfaces: the working voltage, the clearance (bare, 1.5 x the peak), the creepage design on
    PTFE / silicone (group I) and on G10 (IIIa) at x 1.25, the solid insulation, and what the layout gives [IR]."""
    h_col, h_parts = st["h_col_mm"], st["h_parts_mm"]
    hv0, hv1 = st["h_vanes"]
    rows = []

    def row(name, nets_a, nets_b, kind, available, note=""):
        """kind 'air': a bare gap, against the clearance; 'surface': an insulating surface between the two, against
        the creepage on G10 (and on PTFE / silicone, if the surface is covered); 'insulated': a solid insulation
        (wire, bushing, potting) holds it, against its thickness."""
        w = worst(V, nets_a, nets_b)
        clr = clearance(w["pk"])
        cr_i = PF.creepage(w["rms"], "I") * PF.DC_MARGIN
        cr_g = PF.creepage(w["rms"], "IIIa") * PF.DC_MARGIN
        margin = None
        if kind == "air":
            ok = bool(available >= clr)
        elif kind == "surface":
            ok = dict(G10=bool(available >= cr_g), PTFE_or_silicone=bool(available >= cr_i))
        elif kind == "cage":                                         # the record's 12 mm to the cage [IR]
            ok = bool(available >= 12.0)
        elif kind == "gap":                                          # a working gap: its breakdown over the peak
            margin = S.gap_breakdown_kV(available, "air") / w["pk"]
            ok = bool(margin >= 1.45)                                # the record's warm figure (1.46) [IR]
        else:
            ok = None
        rows.append(dict(interface=name, kind=kind, pair=w["pair"], U_rms_kV=w["rms"], U_pk_kV=w["pk"],
                         clearance_mm=clr, creepage_PTFE_mm=cr_i, creepage_G10_mm=cr_g, solid_mm=w["pk"] / PF.E_POT,
                         ribbed_PTFE=PF.ribbed(cr_i, clr), available_mm=available, breakdown_margin=margin, ok=ok,
                         note=note))
    row("Ca's plates: node 1 <-> node 2 (and Cb: 4 <-> 3), the 6 mm gap", ["1"], ["2"], "gap", G_V,
        "13.2 kV DC across 6 mm of air, as the vanes hold V_op: 1.5 to breakdown (the record's air margin)")
    row("the vanes: node 1 <-> REF, the 6 mm gap", ["1"], ["0"], "gap", G_V, "the varicap's own gap, as the record")
    row("the column's node-2 plate <-> the can's end disc (REF)", ["2"], ["0"], "air", h_col - CAN_Z - CAN_DISC_T)
    row("the column's node-2 plate <-> the deck's parts (their potted outer face)", ["2"],
        ["0", "1", "l1", "r1", "r2", "xa", "ea"], "air", h_col - h_parts,
        "sets the column's place; the parts' bodies sit 8 mm deeper still")
    row("node 1's riser in the column's bore <-> the node-2 plates' inner rims", ["1"], ["2"], "insulated", R_IN - 35.0 - 2.0,
        "PTFE HV wire >= 20 kV DC at r 35 on PTFE standoffs, 13 mm from the rims")
    r_out = max(q["r_max_mm"] for s_ in chk.values() for q in s_["to_can"])
    row("the decks' outermost housings <-> the cage (r 162: G10 on the counter-rotor, not REF)", ["ea", "xa", "r1", "2"],
        ["0"], "cage", CAGE_R0 - r_out, "potted; the record keeps 12 mm between its plates' rims and the cage")
    row("deck A <-> deck B, across the equator (ring stage to ring stage)", ["ea", "xa", "1", "r2"],
        ["eb", "xb", "4", "l2"], "air", 2.0 * (DECK_Z0 + DECK_T),
        "between the two plates' outer faces; the parts' bodies are 8 mm of potting further out")
    row("the cross nets l1 <-> r1 (PTFE HV wire, side by side between the decks)", ["l1"], ["r1"], "insulated", None,
        "each wire's insulation holds the pair")
    row("the cross nets <-> the can (REF)", ["l1", "r1"], ["0"], "air", R_O - CAN_R - 2.0)
    row("a ring's lead <-> the can's wall (a PTFE bushing; the lead's insulation continuous)", ["ea"], ["0"], "insulated",
        None, "solid: the lead's PTFE (>= 30 kV DC) through the bushing, no bare metal")
    row("ring A's lead <-> ring B's lead", ["ea"], ["eb"], "insulated", None,
        "each on its own deck, as the record (never a shared bare surface)")
    row("the G10 sleeve, hub side: the first rotor vane's ring (node 1) <-> the can's disc (REF)", ["1"], ["0"],
        "surface", hv0 - (CAN_Z + CAN_DISC_T), "along the sleeve's surface under the column")
    row("the G10 sleeve, outer side: the last rotor vane's ring (node 1) <-> the Ca|reluctance bearing (REF)", ["1"],
        ["0"], "surface", (st["h_bearing_mm"] - 0.5 * S.BEARING["width"]) - (hv0 + (N_VANES - 2) * (T_V + G_V) + T_V),
        "the record's own open point at its hub end (sim/parts-first-cut-findings.md §4), moved to the outer end")
    return rows


# ==================================================================================================== 5. the can
def hub_can():
    """the record's hub field (each band edge its bead in its groove, sim/hub_beads_settled.py hub_solve) in the
    record's REF box (the cage at r 162, a vane at |z| 110) and with the grounded can as the box (r CAN_R - CAN_T,
    |z| CAN_Z): the field at the null per kV and the rings' capacitances [OC: the solver]."""
    import core_rings as CR
    import hub_rings_build as HB
    import hub_beads_settled as HS
    rec = json.load(open(os.path.join(HERE, "hub_rings_build_results.json")))["record"]
    orig = HB.hub_system
    out = {}
    for lab, (R, Z) in (("record box", (None, None)), ("the can", (CAN_R - CAN_T, CAN_Z))):
        HB.hub_system = (lambda R=R, Z=Z: dict(orig(), **({} if R is None else dict(R_box=R, Z_box=Z))))
        t0 = time.time()
        q = HS.hub_solve(rec, None, groove="rect", h=0.25)
        res = q["res"]
        out[lab] = dict(R_box_mm=HB.hub_system()["R_box"], Z_box_mm=HB.hub_system()["Z_box"],
                        k_kV_cm_per_kV=q["k_kV_cm_per_kV"], C_ring_ref_pF=res.get("C_ring_ref_pF"),
                        C_ring_ring_pF=res.get("C_ring_ring_pF"), run_s=round(time.time() - t0, 1))
    # the can's radius and length against the field at the null (the same solve)
    out["sensitivity"] = []
    for R, Z in ((58.0, 85.0), (88.0, 85.0), (CAN_R - CAN_T, 100.0), (160.0, 100.0)):
        HB.hub_system = (lambda R=R, Z=Z: dict(orig(), R_box=R, Z_box=Z))
        q = HS.hub_solve(rec, None, groove="rect", h=0.25)
        out["sensitivity"].append(dict(R_box_mm=R, Z_box_mm=Z, k_kV_cm_per_kV=q["k_kV_cm_per_kV"],
                                       k_ratio=q["k_kV_cm_per_kV"] / out["record box"]["k_kV_cm_per_kV"],
                                       C_ring_ref_pF=q["res"].get("C_ring_ref_pF")))
    HB.hub_system = orig
    a, b = out["record box"], out["the can"]
    out["k_ratio"] = b["k_kV_cm_per_kV"] / a["k_kV_cm_per_kV"]
    out["k_record"] = rec.get("k_kV_cm_per_kV")
    return out


def bore_wire():
    """a node's wire in the shaft's bore, the path a hub-face bearing would force on it [OC: a coax]: PTFE HV wire
    (a 1 mm conductor, 3 mm over its PTFE, eps 2.1) in an 8 mm bore of the steel shaft (REF); the path from the
    flange's face under a bearing to a radial exit, 80 mm with its two exits [IR]; and what it costs the pump at the
    record's price of a pF on nodes 1 and 4 together (sim/tube-strays-findings.md §5: 0.0027 of z)."""
    a, b, R = 0.5, 1.5, 4.0
    c = 2 * math.pi * EPS0 / (math.log(b / a) / 2.1 + math.log(R / b)) * 1e12          # pF/m
    path = 80.0
    return dict(pF_per_m=c, path_mm=path, pF=c * path * 1e-3, dz_nodes_1_4=0.0027 * c * path * 1e-3,
                stiffness_loss=(8.0 / 25.0) ** 4)


# ==================================================================================================== 6. strays
EPS0 = 8.8541878128e-12


def c_cyl_plane(L_mm, a_mm, h_mm):
    """a cylinder of radius a, length L, its axis h from a plane at REF (pF) [OC]."""
    return 2 * math.pi * EPS0 * L_mm * 1e-3 / math.acosh(max(h_mm / a_mm, 1.0001)) * 1e12


def c_wire_cyl(L_mm, a_mm, D_mm, R_mm):
    """a wire of radius a, length L, parallel to a REF cylinder of radius R, axes D apart (pF) [OC]."""
    x = (D_mm ** 2 - a_mm ** 2 - R_mm ** 2) / (2 * a_mm * R_mm)
    return 2 * math.pi * EPS0 * L_mm * 1e-3 / math.acosh(max(x, 1.0001)) * 1e12


def strays(st, dk):
    """per node, what the layout adds (+) or takes (-) against the as-built set [RH: the formulas, each part a body of
    its envelope near the can; the plates' share from the record's solve by the part reached]."""
    add = {n: {} for n in ("1", "2", "l1", "r1", "r2", "xa", "ea")}
    # the deck's parts: each body to the can (its nearer REF); a two-terminal body half to each end's net
    for q in dk["parts"]:
        p = PART[q["kind"]]
        r_c = float(np.mean([np.linalg.norm(e) for e in q["pts"]]))
        if q["kind"] == "clamp":
            # the string's 66 parts hold a linear gradient from REF to node 1: of its body's stray a third reaches node 1
            # (sum of (k / 66)^2) [RH]; its junctions' own series capacitance is the part's, not the layout's
            a_eq = math.sqrt(p["body_w"] * p["body_h"] / math.pi)
            add["1"]["Z1 (a third of its body)"] = c_cyl_plane(p["body_l"], a_eq, r_c - CAN_R) / 3.0
            continue
        if q["orient"] == "up":                                      # standing: its axis parallel to the can's
            c = c_wire_cyl(p["body_l"], 0.5 * p["body_d"], r_c, CAN_R)
        else:                                                        # lying along the lane
            c = c_cyl_plane(p["body_l"], 0.5 * p["body_d"], r_c - CAN_R)
        for n in q["nets"]:
            if n in add:
                add[n][q["name"]] = add[n].get(q["name"], 0.0) + 0.5 * c
    # the junctions: a 6 mm block each, 20 mm long, to the can
    for k, c in dk["junctions"].items():
        if k in add:
            add[k]["junction"] = c_cyl_plane(20.0, 6.0, float(np.linalg.norm(c)) - CAN_R)
    # node 1's riser: in the column's bore at r 35 over the column and the dead gap, then out to the deck's post (wire
    # radius 1 mm against the shaft under its G10 sleeve, the sleeve taken as raising the shaft's radius to 18.4 mm)
    l_bore = L_COL + G_V + (st["h_col_mm"] - st["h_parts_mm"])
    add["1"]["riser (bore)"] = c_wire_cyl(l_bore, 1.0, 35.0, 18.4)
    add["1"]["riser (to the deck)"] = c_cyl_plane(R_I - 35.0, 1.0, 0.5 * (st["h_col_mm"] - CAN_Z))
    # the node-2 tap from the column's node-2 plate down to post 2
    add["2"]["tap"] = c_cyl_plane(st["h_col_mm"] - st["h_parts_mm"], 1.0, R_O - CAN_R)
    # the cross nets: between the decks (|z| < 36) parallel to the can, and the ring lead is on Csa's side (DC)
    for n in ("l1", "r1"):
        add[n]["cross wire"] = c_wire_cyl(2 * (DECK_Z0 + DECK_T), 1.0, R_O, CAN_R)
    # the column's node-2 plate now faces the can's end disc instead of the Ca|reluctance spider, its bearing and the
    # utrons: the record's 11.62 (utrons) + 2.46 (bearings) of node 2's 24.52 pF go; the plate's overlap with the
    # disc (r 50-60) and its fringe come in [RH]
    g_disc = st["h_col_mm"] - CAN_Z - CAN_DISC_T
    plate_disc = EPS0 * math.pi * max(0.0, CAN_R ** 2 - R_IN ** 2) * 1e-6 / (g_disc * 1e-3) * 1e12
    add["2"]["plate to the can's disc (overlap)"] = plate_disc
    add["2"]["plate to the can's disc (fringe)"] = 1.0                         # the disc's rim to the plate's bore [RH]
    add["2"]["the record's utrons, bearings (gone)"] = -(11.62 + 2.46)
    tot = {n: sum(v.values()) for n, v in add.items()}
    return dict(parts=add, total_pF=tot)


Z_TRIM = (59, 60, 61, 62)                          # clamp-string parts (of the record's 66), each 1.5 % of V_op
C7_TRIM = (47e-12, 68e-12)                          # the ring stages' capacitors, E6 values below the record's 100 pF


# ==================================================================================================== 7. the shafts
def shaft(st):
    """sim/shaft_bearings.py's two-body model of record with the solids moved: side A unchanged up to its Ca|reluctance
    bearing; the vanes and Ca plates to their new places; the hub-face bearings and spiders out; the hub, side B and
    its reluctance section moved by the layout's growth; the cage, the sleeve, the can and the decks as new parts [IR]."""
    import shaft_bearings as SB
    lad, parts = SB.record_parts()
    el = lad["tube_geometry"]["elements"]
    z_hub = 470.0                                                     # the record's hub centre (z 398-542)
    dh = st["dh_side_mm"]
    zc_new = z_hub + dh                                               # the new hub centre (side A grows by dh)
    h_brg = st["h_bearing_mm"]

    def z_map(z_rec):
        """record z -> new z for a part of the reluctance sections, the end and Ca|reluctance bearings or the hub."""
        if z_rec <= 208.0:                                            # side A's reluctance section and bearings
            return z_rec
        if z_rec >= 732.0:                                            # side B's
            return z_rec + 2 * dh
        return z_rec + dh                                             # the hub
    vane_A = [e for e in el if e["kind"] == "C1 vane"]
    vane_B = [e for e in el if e["kind"] == "C2 vane"]
    hv0, hv1 = st["h_vanes"]
    new_parts = []
    for p_ in parts:
        nm = p_["name"]
        if "hub_face" in nm or nm.startswith("rotor_sleeve") or "stator_cage" in nm:
            continue
        q = dict(p_)
        if nm.startswith("A_C1_") or nm.startswith("B_C2_"):
            side = nm[0]
            # the record's stack spans h 100-202 from the hub's centre, its hub end a stator vane; here it spans
            # hv0-hv1 with its ends swapped (a rotor vane at the hub end)
            h_rec = 470.0 - p_["z"] if side == "A" else p_["z"] - 470.0
            h_new = hv0 + (202.0 - h_rec)
            q["z"] = (zc_new - h_new) if side == "A" else (zc_new + h_new)
        elif nm.startswith("A_Ca_") or nm.startswith("B_Cb_"):
            side = nm[0]
            h_rec = 470.0 - p_["z"] if side == "A" else p_["z"] - 470.0    # record: h 208-256, node 1 at 208
            h_new = st["h_col_mm"] + (256.0 - h_rec)                      # new: node 2 at h_col, node 1 outward
            q["z"] = (zc_new - h_new) if side == "A" else (zc_new + h_new)
        else:
            q["z"] = z_map(p_["z"])
        new_parts.append(q)
    L = st["L_mm"]

    def ring(name, body, kg, zc, r0, r1, t):
        J = kg * (r0 ** 2 + r1 ** 2) / 4.0 * 1e-6 + kg * (t * 1e-3) ** 2 / 12.0
        return dict(name=name, body=body, material="new", kg=kg, x=0.0, z=zc, J_yy_kgm2=J)

    def tube(name, body, rho, r0, r1, z0, z1):
        kg = math.pi * (r1 ** 2 - r0 ** 2) * (z1 - z0) * rho * 1e-9
        J = kg * ((r0 ** 2 + r1 ** 2) / 4.0 * 1e-6 + ((z1 - z0) * 1e-3) ** 2 / 12.0)
        return dict(name=name, body=body, material="new", kg=kg, x=0.0, z=0.5 * (z0 + z1), J_yy_kgm2=J)
    za_brg, zb_brg = zc_new - h_brg, zc_new + h_brg
    new_parts.append(tube("cage", "stator", 1850.0, CAGE_R0, CAGE_R1, za_brg, zb_brg))
    for sg, nm in ((-1, "A"), (1, "B")):
        z0, z1 = sorted((zc_new + sg * (CAN_Z + CAN_DISC_T), zc_new + sg * (h_brg - 0.5 * S.BEARING["width"])))
        new_parts.append(tube(f"{nm}_sleeve", "rotor", 1850.0, SHAFT_R, SLEEVE_R, z0, z1))
        new_parts.append(ring(f"{nm}_can_disc", "rotor", math.pi * (CAN_R ** 2 - SHAFT_R ** 2) * CAN_DISC_T * 2700e-9,
                              zc_new + sg * (CAN_Z + 0.5 * CAN_DISC_T), SHAFT_R, CAN_R, CAN_DISC_T))
        dk = st["deck_mass"][nm]
        new_parts.append(ring(f"{nm}_deck", "rotor", dk["kg"], zc_new + sg * (DECK_Z0 + 0.5 * (DECK_T + DECK_H)),
                              DECK_R0, DECK_R1, DECK_T + DECK_H))
    new_parts.append(tube("can", "rotor", 2700.0, CAN_R - CAN_T, CAN_R, zc_new - CAN_Z, zc_new + CAN_Z))
    lad2 = copy.deepcopy(lad)
    el2 = []
    for e in lad2["tube_geometry"]["elements"]:
        if e["kind"] == "bearing" and e.get("where") == "hub face":
            continue
        # the model reads the bearings, the hub, the counter-rotor's extent and the utron planes from these; the
        # vanes' and plates' own positions are their solids' (mapped above)
        for k in ("z0", "z1", "zc", "zs0", "zs1"):
            if k in e:
                e[k] = z_map(e[k])
        el2.append(e)
    lad2["tube_geometry"]["elements"] = el2
    lad2["tube_geometry"]["L_total_mm"] = L
    rows = []
    rec_rows = json.load(open(os.path.join(HERE, "shaft_bearings_record_results.json")))["rows"]
    ring_ends = (10.0 + 18.0, L - 10.0 - 18.0)
    k_real = 0.86e8                           # a preloaded 6205 in a G10 spider (sim/rotor-mechanics-findings.md §4)
    cases = [(25.0, (), SB.K_BEARING), (30.0, (), SB.K_BEARING), (40.0, (), SB.K_BEARING),
             (25.0, ring_ends, SB.K_BEARING), (30.0, ring_ends, SB.K_BEARING), (40.0, ring_ends, SB.K_BEARING),
             (25.0, ring_ends, k_real), (30.0, ring_ends, k_real), (40.0, ring_ends, k_real)]
    for d, extra, kb in cases:
        r_new = SB.two_body(lad2, new_parts, d, "coupler", k_b=kb, k_mag=2e5, extra_inner=extra)
        r_rec = SB.two_body(lad, parts, d, "coupler", k_b=kb, k_mag=2e5, extra_inner=((10.0 + 18.0, 940.0 - 10.0 - 18.0)
                                                                                    if extra else ()))
        crit = 3 * SB.F_REL_HZ
        rows.append(dict(d_mm=d, bridge_ring_bearings=bool(extra), k_b_N_per_m=kb, f_Hz=r_new["f_Hz"][:3], f1_Hz=r_new["f1_Hz"],
                         gap_change_um=r_new["gap_change_um"], defl_shaft_max_um=r_new["defl_shaft_max_um"],
                         bearing_loads_1g_N=r_new["bearing_loads_1g_N"], m_rotor_kg=r_new["m_rotor_kg"],
                         m_counter_rotor_kg=r_new["m_counter_rotor_kg"],
                         record=dict(f1_Hz=r_rec["f1_Hz"], gap_change_um=r_rec["gap_change_um"]),
                         ok=bool(r_new["f1_Hz"] >= crit and max(abs(x) for x in r_new["gap_change_um"]) <= 50.0)))
    gate = [r for r in rec_rows if r["d_mm"] == 25.0 and r["hub_joint"] == "coupler" and r.get("k_mag_N_per_m")
            and not r["extra_inner_z_mm"]][0]
    r_gate = SB.two_body(lad, parts, 25.0, "coupler", k_mag=2e5)
    return dict(rows=rows, criterion_f1_Hz=3 * SB.F_REL_HZ, gate=dict(f1_Hz=r_gate["f1_Hz"], f1_record_Hz=gate["f1_Hz"],
                ok=bool(abs(r_gate["f1_Hz"] - gate["f1_Hz"]) < 0.05)), z_hub_new=zc_new)


# ==================================================================================================== main
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--procs", type=int, default=4)
    ap.add_argument("--only", nargs="*", default=["volts", "strays", "hub", "shaft"])
    a = ap.parse_args()
    log = lambda s: print(s, flush=True)
    t0 = time.time()
    old = json.load(open(OUT_JSON)) if os.path.exists(OUT_JSON) else {}
    out = dict(old, note=__doc__.split("\n\n")[0], sources=SRC, tags="CONVENTIONS.md §1", C3_C6_pick_pF=PICK["C3_C6_pF"])
    s_new = IM.S_NEW
    base_strays = {n: s_new for n in ("l1", "l2", "r1", "r2", "xa", "xb")}
    steady = PICK["steady"]["job"]
    if "volts" in a.only or "volts" not in old:
        log("1. the working voltages: the pick's steady state as built, kept")
        q = pool([dict(cl=CL_PICK, strays=base_strays, n_cyc=steady["n_cyc"], keep=True, tag="the pick, steady")], 1, log)[0]
        out["volts"] = dict(job=q["job"], z=q["z"], V_A_kV=q["V_A_kV"], V_B_kV=q["V_B_kV"], settled=q["settled"],
                            V_kV=q["V_kV"], pairs=q["pairs"], gate=dict(V_B_kV=q["V_B_kV"], V_B_pick_kV=PICK["steady"]["V_B_kV"],
                                                                       ok=bool(abs(q["V_B_kV"] - PICK["steady"]["V_B_kV"]) < 0.01)))
    V = out["volts"]
    log("2. the stack")
    st = stack(V)
    log(f"  the column's node-2 plate at |z| {st['h_col_mm']:.0f} mm ({st['c_col_mm']} mm from the deck's parts, "
        f"{st['c_col_pair']['pair']} {st['c_col_pair']['pk']:.2f} kV); the Ca|rel bearing at {st['h_bearing_mm']:.0f} "
        f"(record 272); length {st['L_mm']:.0f} mm")
    log("3. the decks")
    dA, dB = plan(False), plan(True)
    chk = {"A": deck_check(dA, V), "B": deck_check(dB, V)}
    st["deck_mass"] = {"A": deck_mass(dA), "B": deck_mass(dB)}
    for s_ in "AB":
        c = chk[s_]
        wb = c["worst_bare"]
        ws, mh = c["worst_solid"], c["min_housing_gap"]
        log(f"  deck {s_}: {c['n_pairs']} pairs; solid {c['all_solid']} (least margin {ws['a']}-{ws['b']} "
            f"{ws['solid_margin_mm']:.1f} mm; least housing gap {mh['a']}-{mh['b']} {mh['housing_gap_mm']:.1f} mm); bare "
            f"{c['all_bare']}: {c['bare_short']}; the can, bare: {c['can_bare_short']}; can / cage "
            f"{c['all_can']}; {st['deck_mass'][s_]['kg']:.2f} kg, centroid {st['deck_mass'][s_]['offset_mm']:.1f} mm off "
            f"the axis at {st['deck_mass'][s_]['offset_deg']:.0f} deg")
    st["record_reluctance"] = record_reluctance(st["dh_side_mm"])
    out["stack"] = st
    out["decks"] = dict(A=dA, B=dB, checks=chk, parts=PART, lanes=dict(outer_r_mm=R_O, inner_r_mm=R_I),
                        junctions_A=JUNC_A, plan_A=[list(p) for p in PARTS_A], mirror_deg=TH_M,
                        zone=dict(plate_absz_mm=[DECK_Z0, DECK_Z0 + DECK_T], parts_absz_mm=[DECK_Z0 + DECK_T,
                                  DECK_Z0 + DECK_T + DECK_H], r_mm=[DECK_R0, DECK_R1], potting_mm=POT))
    log("4. the interfaces")
    out["interfaces"] = interfaces(V, st, chk)
    for r in out["interfaces"]:
        log(f"  {r['interface'][:70]:70s} {r['pair']} {r['U_pk_kV']:5.2f} kV pk {r['U_rms_kV']:5.2f} rms: clearance "
            f"{r['clearance_mm']:5.1f} mm, creepage {r['creepage_PTFE_mm']:5.1f} / {r['creepage_G10_mm']:5.1f} mm; "
            f"available {r['available_mm']}  {r['ok']}")
    if "hub" in a.only or "hub" not in old:
        log("5. the grounded can and the hub's field")
        out["hub"] = hub_can()
        log(f"  k {out['hub']['record box']['k_kV_cm_per_kV']:.5f} -> {out['hub']['the can']['k_kV_cm_per_kV']:.5f} "
            f"(x {out['hub']['k_ratio']:.5f}); C ring-REF {out['hub']['record box']['C_ring_ref_pF']} -> "
            f"{out['hub']['the can']['C_ring_ref_pF']} pF")
    if "strays" in a.only or "strays" not in old:
        log("6. the strays and the circuit with them")
        sy = strays(st, dA)
        ab = IM.SET_AB["Cp"]
        cp = {"1": ab["1"] + sy["total_pF"]["1"] * 1e-12, "4": ab["4"] + sy["total_pF"]["1"] * 1e-12,
              "2": ab["2"] + sy["total_pF"]["2"] * 1e-12, "3": ab["3"] + sy["total_pF"]["2"] * 1e-12}
        tp = sy["total_pF"]
        # r2 and xa are deck A's alone (l2 and xb, their mirrors, deck B's); l1 and r1 sit on both decks, so deck A's
        # share and deck B's (the mirror of deck A's other cross net) add
        new = {"r2": tp["r2"], "l2": tp["r2"], "xa": tp["xa"], "xb": tp["xa"], "l1": tp["l1"] + tp["r1"],
               "r1": tp["r1"] + tp["l1"]}
        new = {k: v * 1e-12 for k, v in new.items()}
        sy["deck_strays_pF"] = {k: v * 1e12 for k, v in new.items()}
        sy["cp_pF"] = {k: v * 1e12 for k, v in cp.items()}
        jobs = []
        n_cl = steady["n_cyc"]
        for cl in (100e-12, 120e-12, 150e-12, 180e-12):          # the study's rule over C3-C6 (it barely moves them)
            jobs.append(dict(cl=cl, strays=new, cp=cp, n_cyc=n_cl, tag="layout, C3-C6, clamped"))
            jobs.append(dict(cl=cl, strays=new, cp=cp, n_cyc=40, clamp=False, fit_from=10, tag="layout, C3-C6, free"))
        for n_z in Z_TRIM:                                        # the clamp strings trimmed: n parts of the 66
            jobs.append(dict(cl=CL_PICK, strays=new, cp=cp, n_cyc=n_cl, vop=IM.V_OP * n_z / 66.0, n_z=n_z,
                             tag=f"layout, clamps of {n_z}"))
        for c7 in C7_TRIM:                                        # the ring stages' capacitors smaller
            jobs.append(dict(cl=CL_PICK, strays=new, cp=cp, n_cyc=n_cl, c7=c7, tag=f"layout, C7 / C8 {c7 * 1e12:.0f} pF"))
            jobs.append(dict(cl=CL_PICK, strays=new, cp=cp, n_cyc=40, c7=c7, clamp=False, fit_from=10,
                             tag=f"layout, C7 / C8 {c7 * 1e12:.0f} pF, free"))
        jobs.append(dict(cl=CL_PICK, strays=base_strays, n_cyc=40, clamp=False, fit_from=10, tag="the study's strays, free"))
        res = pool(jobs, a.procs, log)
        for _ in range(2):                                            # the clamped runs doubled until the rings settle
            redo = [i for i, q in enumerate(res) if q.get("done") and q["job"].get("clamp", True) and not q["settled"]]
            if not redo:
                break
            again = pool([dict(res[i]["job"], n_cyc=2 * res[i]["job"]["n_cyc"]) for i in redo], a.procs, log)
            for i, q in zip(redo, again):
                res[i] = q
        sy["runs"] = [dict(cl_pF=q["job"]["cl"] * 1e12, c7_pF=q["job"].get("c7", IM.C_CW) * 1e12,
                           V_op_kV=q["job"].get("vop", IM.V_OP) / 1e3, n_z=q["job"].get("n_z", 66),
                           clamp=q["job"].get("clamp", True), tag=q["job"]["tag"], n_cyc=q["job"]["n_cyc"], z=q.get("z"),
                           V_A_kV=q.get("V_A_kV"), V_B_kV=q.get("V_B_kV"), E_null_kV_cm=q.get("E_null_kV_cm"),
                           settled=q.get("settled")) for q in res]
        target = 0.5 * (IM.SUP["V_eb_kV"]["mean"] - IM.SUP["V_ea_kV"]["mean"])
        sy["rings_target_kV"] = target
        within = lambda r: r["clamp"] and r["V_B_kV"] is not None and 0.5 * (r["V_B_kV"] - r["V_A_kV"]) <= target
        rules = {}
        for key, sel, val in (("C3_C6_pF", lambda r: "C3-C6" in r["tag"], "cl_pF"),
                              ("clamp_parts", lambda r: "clamps of" in r["tag"], "n_z"),
                              ("C7_C8_pF", lambda r: r["tag"].startswith("layout, C7") and r["clamp"], "c7_pF")):
            ok = [r for r in sy["runs"] if sel(r) and within(r)]
            best = max(ok, key=lambda r: r["V_B_kV"]) if ok else None
            rules[key] = dict(value=best[val] if best else None, rings_kV=best["V_B_kV"] if best else None)
        sy["picks"] = rules
        out["strays"] = sy
    if "shaft" in a.only or "shaft" not in old:
        log("7. the shafts without the hub-face bearings")
        out["shaft"] = shaft(st)
        g = out["shaft"]["gate"]
        log(f"  gate: the record d 25 f1 {g['f1_Hz']:.2f} Hz (record {g['f1_record_Hz']:.2f}) {g['ok']}")
        for r in out["shaft"]["rows"]:
            log(f"  d {r['d_mm']:.0f}{' + bridge-ring bearings' if r['bridge_ring_bearings'] else ''}, k_b "
                f"{r['k_b_N_per_m']:.2g}: f "
                f"{', '.join(f'{x:.0f}' for x in r['f_Hz'])} Hz (record f1 {r['record']['f1_Hz']:.0f}); gap change "
                f"{', '.join(f'{x:+.0f}' for x in r['gap_change_um'])} um (record "
                f"{', '.join(f'{x:+.0f}' for x in r['record']['gap_change_um'])}); ok {r['ok']}")
    out["bore_wire"] = bore_wire()
    out["run_s"] = round(time.time() - t0)
    json.dump(out, open(OUT_JSON, "w"), indent=1, default=float)
    log(f"wrote {OUT_JSON} ({out['run_s']} s)")


if __name__ == "__main__":
    main()
