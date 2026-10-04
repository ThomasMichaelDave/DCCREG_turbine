"""sim/circuit_integrity.py -- CIRCUIT INTEGRITY for the DCCREG electrostatic machine (TMD 2026-10-02).

Rebuilds the circuit from the 3-D solids alone and holds it against the netlist of record
(topology_edge_list.csv, KiCad pin-exact). Nothing is taken from the generator's own bookkeeping: copper that
touches is one net, foils that face each other are a capacitor, spheres that meet across a band are a spark gap.
Then every name and every group must say the node its copper is on.

Inputs: a pump-geometry JSON (its bill of solids, `parts`), or a STEP file written from it by FreeCAD or Fusion 360
(the STEP path needs OCP: `pip install cadquery-ocp`). Run:

    python3 sim/circuit_integrity.py docs/geometry/freeze-v010-CaCb.json        (or .step)
    python3 sim/circuit_integrity.py model.step --json report.json

Rules (FAIL = the build is not the netlist; WARN = look at it; INFO = for the record):
  I1 net purity      every galvanic net carries exactly one node -- else SHORT, with the parts that bridge
  I2 node continuity every node is one net -- else OPEN, with its fragments
  I3 nodes of record every drawn node is a netlist node (old aliases such as 5 / 6 are named); the netlist nodes
                     with nothing drawn are listed (off-model)
  I4 rotating joint  no net has copper on the rotor and on the stator (rotor and stator counter-rotate: such a
                     connection would be torn off; the only rotor-stator paths are the spark gaps)
  I5 orphans         every net holds a foil electrode -- no lead, stem or sphere floats on its own
  I6 capacitors      every drawn netlist capacitor is realized by facing foils of exactly its two nodes, fixed or
                     rotating as the machine needs (C1 / C2 / Cx3 / Cx4 rotate); every other pair of facing foils of
                     two nets is a STRAY capacitor, reported with its parallel-plate value and the component it
                     shunts
  I7 spark gaps      every netlist gap is realized by stator spheres facing rotor spheres of exactly its two nodes;
                     any other different-net rotor/stator sphere pair that comes as close is a PARASITIC GAP
  I8 names           every part's label, its group and its gap / capacitor name state the node its copper is on
  I9 off-model       the netlist components not drawn (inductors, the motor banks) and the drawn nets they join

Physics [OC]: capacitances are parallel plate over the plan overlap, through the insulators in between (series
layers, air elsewhere), no fringing; rotor/stator pairs -- and fixed pairs behind rotating copper -- are swept
over a full relative turn (C_max / C_min). Only foils with at most one partly shielding layer of copper between
them are coupled: past that the field ends on the copper in between and a parallel-plate figure means nothing.
Insulator permittivities by material name; an unknown one is assumed G10 (4.7) and flagged. No file I/O on import.
"""
import csv
import json
import math
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TOOL = "circuit-integrity/1"
EPS0 = 8.8541878128e-12
EPS_AIR = 1.0006
CONTACT_TOL = 0.01          # mm: copper closer than this is one net
GAP_NEAR = 15.0             # mm: rotor/stator spheres closer than this (surface to surface, aligned) form a gap
STRAY_MIN_PF = 1.0          # facing-foil couplings at least this large are reported
DELTA_STEP = 1.0            # deg: relative-rotation step for rotor/stator couplings

DRAWN_CAPS = ("C1", "C2", "Ca1", "Cb1", "Cx3", "Cx4", "C_R1")     # the netlist capacitors the stack realizes
VARIABLE_CAPS = ("C1", "C2", "Cx3", "Cx4")                          # one plate on the rotor, one on the stator
CAP_PREFIX = {"C1": "C1", "C2": "C2", "Ca": "Ca1", "Cb": "Cb1", "Cx3": "Cx3", "Cx4": "Cx4", "CR": "C_R1"}
ALIAS = {"5": "R-A", "6": "R-B", "9": "n18", "10": "n00"}           # DXF-era ids -> the netlist of record
NODE_INFO = {
    "1": "ND1 - A-rail: C1 stator plate + Ca counter-electrode",
    "2": "ND2 - AR bank: Ca electrode",
    "3": "ND3 - BR bank: Cb electrode",
    "4": "ND4 - B-rail: C2 stator plate + Cb counter-electrode",
    "R-A": "ND5 - resonator end A: rotor A (C1 rotor face)",
    "R-B": "ND6 - resonator end B: rotor B (C2 rotor face)",
    "7": "ND7 - island on rotor B (Cx3 bars)",
    "8": "ND8 - island on rotor A (Cx4 bars)",
    "n18": "ND9 - C_R plate on rotor A (L_R1 to R-A)",
    "n00": "ND10 - C_R plate on rotor B (L_R2 to R-B)",
    "n17": "Cx3 pickup on ND3 (Lx3 to node 3)",
    "n23": "Cx4 pickup on ND2 (Lx4 to node 2)",
}
CONDUCTORS = ("Al foil", "Cu lead", "Cu link", "Cu stem", "Cu bus", "W-Cu sphere", "polished sphere")
EPS_TABLE = (("glass-bonded", 6.9), ("mica", 5.4), ("garolite", 4.7), ("G10", 4.7), ("kapton", 3.4), ("mylar", 3.2), ("pp_film", 2.2),
             ("PP film", 2.2), ("PTFE", 2.1))
NODE_TOKEN = re.compile(r"\bnode (R-[AB]|n\d+|\d+)\b")
GROUP_NODE = re.compile(r"\(node (R-[AB]|n\d+|\d+)[,):]")
LEGACY_BODY = {"A-disc": "rotor A", "A-flange": "rotor A", "B-disc": "rotor B", "B-flange": "rotor B"}


# ---- the netlist of record ----------------------------------------------------------------------------------
def load_netlist(path=None):
    """[{name, a, b, kind}] from topology_edge_list.csv (comment rows '#...' skipped)."""
    rows = []
    with open(path or os.path.join(ROOT, "topology_edge_list.csv"), newline="") as f:
        for r in csv.reader(f):
            if not r or r[0].startswith("#") or r[0] == "component":
                continue
            rows.append(dict(name=r[0], a=r[1], b=r[2], kind=comp_kind(r[0])))
    return rows


def comp_kind(name):
    if name.startswith(("SG", "BS")):
        return "gap"
    if name.startswith("C"):
        return "capacitor"
    if name.startswith("L"):
        return "inductor"
    return "other"


def canon(n):
    """a node id as the netlist of record writes it ('8 (floating on A)' -> '8'; '5' -> 'R-A')."""
    if n is None or n == "":
        return None
    s = str(n).split(" ")[0]
    return ALIAS.get(s, s)


def is_conductor(material):
    return any(k in (material or "") for k in CONDUCTORS)


def eps_of(material):
    for k, e in EPS_TABLE:
        if k in (material or ""):
            return e, True
    return 4.7, False


def frame_of(body):
    return "rotor" if str(body).startswith("rotor") else "stator"


# ---- parts from a pump-geometry design (its bill of solids) --------------------------------------------------
def parts_from_design(design):
    glabel = {a["key"]: a["label"] for a in design.get("assemblies", [])}
    out = []
    for p in design["parts"]:
        mat = p.get("material", "")
        body = p.get("body") or LEGACY_BODY.get(p.get("carrier", ""), "rotor AB" if p["name"].startswith("septum") else "stator")
        cond = is_conductor(mat)
        sh = p.get("shape", "sector")
        q = dict(name=p["name"], label=p.get("label", p["name"]), group=p.get("assembly", ""),
                 group_label=glabel.get(p.get("assembly", ""), ""), material=mat, body=body, frame=frame_of(body),
                 node_raw=str(p.get("node", "")) if cond else "", node=canon(p.get("node")) if cond else None)
        if not cond:
            q["kind"] = "insulator"
            q["eps"], q["eps_known"] = eps_of(mat)
        else:
            q["kind"] = {"sector": "foil", "sphere": "sphere", "rod": "rod"}[sh]
        if sh == "sector":
            q.update(r_in=p["r_in"], r_out=p["r_out"], a0=p["start_deg"], w=p["w_deg"], z0=p["z0"], z1=p["z1"])
        elif sh == "sphere":
            q.update(c=list(p["c"]), r=p["r"])
        else:
            q.update(p0=list(p["p0"]), p1=list(p["p1"]), r=p["r"])
        out.append(q)
    return out


# ---- geometry -----------------------------------------------------------------------------------------------
def _sdeg(x):
    return x - 360.0 * math.floor((x + 180.0) / 360.0)


def _dist(p, q):
    return math.sqrt((p[0] - q[0]) ** 2 + (p[1] - q[1]) ** 2 + (p[2] - q[2]) ** 2)


def _lerp(p, q, t):
    return [p[0] + (q[0] - p[0]) * t, p[1] + (q[1] - p[1]) * t, p[2] + (q[2] - p[2]) * t]


def _d_pt_sector(pt, s):
    """exact distance from a point to an annular-sector slab."""
    r = math.hypot(pt[0], pt[1])
    dz = max(0.0, s["z0"] - pt[2], pt[2] - s["z1"])
    if s["w"] >= 360.0 - 1e-9 or r < 1e-12:
        inside = True
    else:
        a = math.degrees(math.atan2(pt[1], pt[0]))
        inside = abs(_sdeg(a - (s["a0"] + s["w"] / 2))) <= s["w"] / 2
    if inside:
        dp = max(0.0, s["r_in"] - r, r - s["r_out"])
    else:
        dp = float("inf")
        for e in (s["a0"], s["a0"] + s["w"]):
            ex, ey = math.cos(math.radians(e)), math.sin(math.radians(e))
            t = min(s["r_out"], max(s["r_in"], pt[0] * ex + pt[1] * ey))
            dp = min(dp, math.hypot(pt[0] - t * ex, pt[1] - t * ey))
    return math.hypot(dp, dz)


def _d_seg_sector(p0, p1, s):
    """distance from a segment to an annular-sector slab: sampled every <= 1 mm, the best bracket refined."""
    n = max(1, int(math.ceil(_dist(p0, p1) / 1.0 - 1e-9)))
    vals = [_d_pt_sector(_lerp(p0, p1, i / n), s) for i in range(n + 1)]
    i = min(range(n + 1), key=lambda k: (vals[k], k))
    lo, hi = max(0.0, (i - 1) / n), min(1.0, (i + 1) / n)
    for _ in range(40):
        m1, m2 = lo + (hi - lo) / 3, hi - (hi - lo) / 3
        if _d_pt_sector(_lerp(p0, p1, m1), s) < _d_pt_sector(_lerp(p0, p1, m2), s):
            hi = m2
        else:
            lo = m1
    return min(vals[i], _d_pt_sector(_lerp(p0, p1, 0.5 * (lo + hi)), s))


def _d_pt_seg(c, p, q):
    d = [q[i] - p[i] for i in range(3)]
    L2 = d[0] * d[0] + d[1] * d[1] + d[2] * d[2]
    t = 0.0 if L2 < 1e-18 else min(1.0, max(0.0, sum((c[i] - p[i]) * d[i] for i in range(3)) / L2))
    return _dist(c, [p[i] + d[i] * t for i in range(3)])


def _seg_seg(p, q, r, s):
    """the smallest distance between segments p-q and r-s (Ericson)."""
    d1 = [q[i] - p[i] for i in range(3)]; d2 = [s[i] - r[i] for i in range(3)]; w = [p[i] - r[i] for i in range(3)]
    a = sum(x * x for x in d1); e = sum(x * x for x in d2); f_ = sum(d2[i] * w[i] for i in range(3))
    if a < 1e-18 and e < 1e-18:
        return _dist(p, r)
    if a < 1e-18:
        t, u = 0.0, min(1.0, max(0.0, f_ / e))
    else:
        c = sum(d1[i] * w[i] for i in range(3))
        if e < 1e-18:
            t, u = min(1.0, max(0.0, -c / a)), 0.0
        else:
            bb = sum(d1[i] * d2[i] for i in range(3)); den = a * e - bb * bb
            t = min(1.0, max(0.0, (bb * f_ - c * e) / den)) if den > 1e-12 else 0.0
            u = (bb * t + f_) / e
            if u < 0.0:
                t, u = min(1.0, max(0.0, -c / a)), 0.0
            elif u > 1.0:
                t, u = min(1.0, max(0.0, (bb - c) / a)), 1.0
    return _dist([p[i] + d1[i] * t for i in range(3)], [r[i] + d2[i] * u for i in range(3)])


def _seg_rminmax(p, q):
    dx, dy = q[0] - p[0], q[1] - p[1]
    L2 = dx * dx + dy * dy
    t = 0.0 if L2 < 1e-18 else min(1.0, max(0.0, -(p[0] * dx + p[1] * dy) / L2))
    return math.hypot(p[0] + t * dx, p[1] + t * dy), max(math.hypot(p[0], p[1]), math.hypot(q[0], q[1]))


def _iv(a0, w):
    """an arc as intervals within [0, 360)."""
    if w >= 360.0 - 1e-9:
        return [(0.0, 360.0)]
    s = a0 - 360.0 * math.floor(a0 / 360.0)
    e = s + w
    return [(s, e)] if e <= 360.0 else [(s, 360.0), (0.0, e - 360.0)]


def _merge(ivs):
    out = []
    for s, e in sorted(ivs):
        if out and s <= out[-1][1] + 1e-12:
            if e > out[-1][1]:
                out[-1] = (out[-1][0], e)
        else:
            out.append((s, e))
    return out


def _inter(A, B):
    out, i, j = [], 0, 0
    while i < len(A) and j < len(B):
        lo, hi = max(A[i][0], B[j][0]), min(A[i][1], B[j][1])
        if hi > lo:
            out.append((lo, hi))
        if A[i][1] < B[j][1]:
            i += 1
        else:
            j += 1
    return out


def _meas(A):
    return sum(e - s for s, e in A)


def _shift(ivs_src, d):
    out = []
    for a0, w in ivs_src:
        out += _iv(a0 + d, w)
    return _merge(out)


def _bbox(p):
    if p["kind"] == "sphere":
        c, r = p["c"], p["r"]
        return [c[0] - r, c[1] - r, c[2] - r, c[0] + r, c[1] + r, c[2] + r]
    if p["kind"] == "rod":
        a, b, r = p["p0"], p["p1"], p["r"]
        return [min(a[0], b[0]) - r, min(a[1], b[1]) - r, min(a[2], b[2]) - r,
                max(a[0], b[0]) + r, max(a[1], b[1]) + r, max(a[2], b[2]) + r]
    R = p["r_out"]
    if p["w"] >= 360.0 - 1e-9:
        return [-R, -R, p["z0"], R, R, p["z1"]]
    angs = [p["a0"], p["a0"] + p["w"]] + [90.0 * k for k in range(-8, 9) if p["a0"] < 90.0 * k < p["a0"] + p["w"]]
    xs, ys = [], []
    for a in angs:
        for rr in (p["r_in"], p["r_out"]):
            xs.append(rr * math.cos(math.radians(a))); ys.append(rr * math.sin(math.radians(a)))
    return [min(xs), min(ys), p["z0"], max(xs), max(ys), p["z1"]]


def _gap(p, q):
    """surface-to-surface distance of two conductors (<= 0: they overlap)."""
    kp, kq = p["kind"], q["kind"]
    if kp == "foil" and kq == "foil":
        zg = max(p["z0"] - q["z1"], q["z0"] - p["z1"], 0.0)
        rg = max(max(p["r_in"], q["r_in"]) - min(p["r_out"], q["r_out"]), 0.0)
        A, B = _merge(_iv(p["a0"], p["w"])), _merge(_iv(q["a0"], q["w"]))
        ag = 0.0
        if _meas(_inter(A, B)) <= 1e-12 and p["w"] < 360.0 - 1e-9 and q["w"] < 360.0 - 1e-9:
            e1, e2 = p["a0"] + p["w"], q["a0"] + q["w"]
            ag = min(abs(_sdeg(q["a0"] - e1)), abs(_sdeg(p["a0"] - e2)))
            ag = math.radians(ag) * min(p["r_out"], q["r_out"])
        return math.sqrt(zg * zg + rg * rg + ag * ag)
    if kp == "foil" or kq == "foil":
        s, o = (p, q) if kp == "foil" else (q, p)
        if o["kind"] == "sphere":
            return _d_pt_sector(o["c"], s) - o["r"]
        lo, hi = min(o["p0"][2], o["p1"][2]), max(o["p0"][2], o["p1"][2])
        zg = max(s["z0"] - hi, lo - s["z1"])
        rmin, rmax = _seg_rminmax(o["p0"], o["p1"])
        rg = max(s["r_in"] - rmax, rmin - s["r_out"])
        if zg > o["r"] + CONTACT_TOL or rg > o["r"] + CONTACT_TOL:
            return max(zg, rg) - o["r"]
        return _d_seg_sector(o["p0"], o["p1"], s) - o["r"]
    if kp == "sphere" and kq == "sphere":
        return _dist(p["c"], q["c"]) - p["r"] - q["r"]
    if kp == "sphere" or kq == "sphere":
        s, o = (p, q) if kp == "sphere" else (q, p)
        return _d_pt_seg(s["c"], o["p0"], o["p1"]) - s["r"] - o["r"]
    return _seg_seg(p["p0"], p["p1"], q["p0"], q["p1"]) - p["r"] - q["r"]


# ---- the analysis -------------------------------------------------------------------------------------------
def _f(x, n):
    """x to n decimals, half away from zero (= JS toFixed)."""
    from decimal import Decimal, ROUND_HALF_UP
    q = Decimal(1).scaleb(-n)
    s = str(Decimal(x).quantize(q, rounding=ROUND_HALF_UP))
    return "0" + s[2:] if s.startswith("-0") and set(s[1:].replace(".", "")) <= {"0"} else s


def nets_of(parts):
    """galvanic nets: union-find over every pair of touching conductors."""
    cond = [i for i, p in enumerate(parts) if p["kind"] != "insulator"]
    boxes = {i: _bbox(parts[i]) for i in cond}
    par = {i: i for i in cond}

    def find(i):
        while par[i] != i:
            par[i] = par[par[i]]
            i = par[i]
        return i
    edges = []
    order = sorted(cond, key=lambda i: boxes[i][0])
    for x, i in enumerate(order):
        bi = boxes[i]
        for j in order[x + 1:]:
            bj = boxes[j]
            if bj[0] > bi[3] + CONTACT_TOL:
                break
            if bj[1] > bi[4] + CONTACT_TOL or bi[1] > bj[4] + CONTACT_TOL or bj[2] > bi[5] + CONTACT_TOL or bi[2] > bj[5] + CONTACT_TOL:
                continue
            if _gap(parts[i], parts[j]) <= CONTACT_TOL:
                a, b = (i, j) if i < j else (j, i)
                edges.append((a, b))
                ra, rb = find(a), find(b)
                if ra != rb:
                    par[max(ra, rb)] = min(ra, rb)
    edges.sort()
    groups = {}
    for i in cond:
        groups.setdefault(find(i), []).append(i)
    nets = [sorted(v) for v in groups.values()]
    nets.sort(key=lambda v: v[0])
    return nets, edges


def couplings(parts, nets):
    """facing foils of different nets: parallel-plate C through the insulators in between [OC], fixed (same frame)
    or swept over a full relative turn (rotor vs stator). Returns {(net_i, net_j, relation): C or [C(delta)]}."""
    net_of = {}
    for k, v in enumerate(nets):
        for i in v:
            net_of[i] = k
    plates = {}
    for i, p in enumerate(parts):
        if p["kind"] != "foil":
            continue
        key = (net_of[i], p["frame"], round(p["z0"], 6), round(p["z1"], 6), round(p["r_in"], 6), round(p["r_out"], 6))
        plates.setdefault(key, dict(net=net_of[i], frame=p["frame"], z0=p["z0"], z1=p["z1"], r_in=p["r_in"],
                                    r_out=p["r_out"], arcs=[], names=[]))
        plates[key]["arcs"].append((p["a0"], p["w"]))
        plates[key]["names"].append(p["name"])
    P = [plates[k] for k in sorted(plates, key=lambda k: (k[2], k[4], k[0], k[1], k[3], k[5]))]
    ins = [p for p in parts if p["kind"] == "insulator" and "r_in" in p]
    deltas = [k * DELTA_STEP for k in range(int(round(360.0 / DELTA_STEP)))]
    out = {}
    for x in range(len(P)):
        for y in range(x + 1, len(P)):
            A, B = P[x], P[y]
            if A["net"] == B["net"]:
                continue
            ra, rb = max(A["r_in"], B["r_in"]), min(A["r_out"], B["r_out"])
            if rb - ra <= 1e-9:
                continue
            if A["z1"] <= B["z0"] + 1e-9:
                zlo, zhi = A["z1"], B["z0"]
            elif B["z1"] <= A["z0"] + 1e-9:
                zlo, zhi = B["z1"], A["z0"]
            else:
                continue
            d = zhi - zlo
            if d <= CONTACT_TOL:
                continue
            sh = [S for S in P if S is not A and S is not B and S["z0"] >= zlo - 1e-9 and S["z1"] <= zhi + 1e-9
                  and min(S["r_out"], rb) - max(S["r_in"], ra) > 1e-9]
            lay = [I for I in ins if min(I["z1"], zhi) - max(I["z0"], zlo) > 1e-9 and min(I["r_out"], rb) - max(I["r_in"], ra) > 1e-9]
            bounds = sorted({ra, rb} | {v for S in sh for v in (S["r_in"], S["r_out"]) if ra < v < rb}
                            | {v for I in lay for v in (I["r_in"], I["r_out"]) if ra < v < rb})
            rot = A["frame"] != B["frame"] or any(S["frame"] != A["frame"] for S in sh)
            ds = deltas if rot else [0.0]
            C = [0.0] * len(ds)
            a_ = _shift(A["arcs"], 0.0)                 # A's frame is the reference: the other frame turns by delta
            for b0, b1 in zip(bounds[:-1], bounds[1:]):
                if b1 - b0 <= 1e-9:
                    continue
                layers = {}
                for I in lay:
                    if I["r_in"] <= b0 + 1e-9 and I["r_out"] >= b1 - 1e-9:
                        z0, z1 = max(I["z0"], zlo), min(I["z1"], zhi)
                        layers[(round(z0, 6), round(z1, 6))] = (z1 - z0, I["eps"])
                tt = sum(t for t, _ in layers.values())
                t_eff = sum(t / e for t, e in layers.values()) + max(0.0, d - tt) / EPS_AIR
                shb = [S for S in sh if S["r_in"] <= b0 + 1e-9 and S["r_out"] >= b1 - 1e-9]
                if len({(round(S["z0"], 6), round(S["z1"], 6)) for S in shb}) > 1:
                    continue                            # two copper layers between: no parallel-plate coupling here
                k_area = 0.5 * math.pi / 180.0 * (b1 * b1 - b0 * b0)
                for n_, dl in enumerate(ds):
                    b_ = _shift(B["arcs"], dl if B["frame"] != A["frame"] else 0.0)
                    ov = _inter(a_, b_)
                    if not ov:
                        continue
                    u = []
                    for S in shb:
                        u += _shift(S["arcs"], dl if S["frame"] != A["frame"] else 0.0)
                    L = _meas(ov) - (_meas(_inter(ov, _merge(u))) if u else 0.0)
                    if L > 1e-12:
                        C[n_] += EPS0 * k_area * L * 1e-6 / (t_eff * 1e-3) * 1e12
            if max(C) <= 0.0:
                continue
            i, j = sorted((A["net"], B["net"]))
            rel = "rotating" if A["frame"] != B["frame"] else ("modulated" if rot else "fixed")
            key = (i, j, rel)
            if key in out:
                out[key] = [p + q for p, q in zip(out[key], C)]
            else:
                out[key] = C
    return out


def sphere_gaps(parts, nets):
    """stator sphere vs rotor sphere: aligned closest approach over the relative turn."""
    net_of = {}
    for k, v in enumerate(nets):
        for i in v:
            net_of[i] = k
    sph = [i for i, p in enumerate(parts) if p["kind"] == "sphere"]
    st = [i for i in sph if parts[i]["frame"] == "stator"]
    ro = [i for i in sph if parts[i]["frame"] == "rotor"]
    out = []
    for i in st:
        s = parts[i]
        rs = math.hypot(s["c"][0], s["c"][1])
        best = {}
        for j in ro:
            t = parts[j]
            g = math.hypot(rs - math.hypot(t["c"][0], t["c"][1]), s["c"][2] - t["c"][2]) - s["r"] - t["r"]
            if g < GAP_NEAR:
                k = net_of[j]
                if k not in best or g < best[k][0] - 1e-12:
                    best[k] = (g, j)
        out.append(dict(stator=i, partners=sorted(best.items())))
    return out


def analyze(parts, netlist=None, source=""):
    netlist = netlist if netlist is not None else load_netlist()
    nl_nodes = sorted({x for c in netlist for x in (c["a"], c["b"])})
    find = []

    def add(rule, level, text):
        find.append(dict(rule=rule, level=level, text=text))
    for p in parts:
        if p["kind"] == "unrecognized":
            add("I0", "FAIL", f"solid {p['name']} is not recognized as a sector slab, sphere or rod: not analyzed")
    parts = [p for p in parts if p["kind"] != "unrecognized"]
    nets, edges = nets_of(parts)
    tags = []
    for v in nets:
        tags.append(sorted({parts[i]["node"] for i in v if parts[i]["node"]}))
    node_of_net = [t[0] if len(t) == 1 else None for t in tags]
    # I1 purity
    for k, v in enumerate(nets):
        if len(tags[k]) > 1:
            br = [(a, b) for a, b in edges if a in v and parts[a]["node"] != parts[b]["node"]]
            via = "; ".join(f"{parts[a]['name']} (node {parts[a]['node']}) touches {parts[b]['name']} (node {parts[b]['node']})" for a, b in br[:3])
            add("I1", "FAIL", f"SHORT: one net joins nodes {', '.join(tags[k])} -- {via}")
    if not any(f["rule"] == "I1" for f in find):
        add("I1", "PASS", f"{len(nets)} galvanic nets, each on one node")
    # I2 continuity
    by_node = {}
    for k, t in enumerate(tags):
        for n in t:
            by_node.setdefault(n, []).append(k)
    for n in sorted(by_node):
        ks = by_node[n]
        if len(ks) > 1:
            frag = "; ".join(f"{len(nets[k])} parts from {parts[nets[k][0]]['name']}" for k in ks[:4])
            add("I2", "FAIL", f"OPEN: node {n} is split into {len(ks)} nets ({frag})")
    if not any(f["rule"] == "I2" for f in find):
        add("I2", "PASS", f"every node is one net ({len(by_node)} nodes)")
    # I3 nodes of record
    raw_alias = sorted({(p["node_raw"].split(" ")[0], p["node"]) for p in parts
                        if p["node"] and p["node_raw"] and p["node_raw"].split(" ")[0] != p["node"]})
    for a, b in raw_alias:
        add("I3", "WARN", f"node id '{a}' is an old alias: the netlist of record calls it {b}")
    for n in sorted(by_node):
        if n not in nl_nodes:
            add("I3", "FAIL", f"node {n} is drawn but is not in the netlist of record")
    undrawn = [n for n in nl_nodes if n not in by_node]
    add("I3", "PASS" if not any(f["rule"] == "I3" and f["level"] == "FAIL" for f in find) else "INFO",
        f"drawn nodes {', '.join(sorted(by_node))}; netlist nodes with nothing drawn (off-model): {', '.join(undrawn) or 'none'}")
    # I4 rotating joint
    for k, v in enumerate(nets):
        fr = sorted({parts[i]["frame"] for i in v})
        if len(fr) > 1:
            add("I4", "FAIL", f"the net of node {', '.join(tags[k]) or '?'} has copper on the rotor and on the stator (e.g. {parts[v[0]]['name']}): "
                               "it would be torn off -- rotor and stator meet only across spark gaps")
    if not any(f["rule"] == "I4" for f in find):
        add("I4", "PASS", "no net crosses the rotating joint")
    # I5 orphans
    for k, v in enumerate(nets):
        if not any(parts[i]["kind"] == "foil" for i in v):
            add("I5", "FAIL", f"ORPHAN: {len(v)} conductor(s) on no electrode, e.g. {parts[v[0]]['name']} (node {parts[v[0]]['node']})")
    if not any(f["rule"] == "I5" for f in find):
        add("I5", "PASS", "every net holds a foil electrode")
    # I6 capacitors
    cp_net = couplings(parts, nets)
    cp = {}                                              # per node pair (an OPEN node's fragments summed)
    for (i, j, rel), val in sorted(cp_net.items()):
        a, b = sorted((node_of_net[i] or "+".join(tags[i]), node_of_net[j] or "+".join(tags[j])))
        k = (a, b, rel)
        cp[k] = [x + y for x, y in zip(cp[k], val)] if k in cp else list(val)
    caps, strays = [], []
    used = set()
    for c in netlist:
        if c["name"] not in DRAWN_CAPS:
            continue
        want = {c["a"], c["b"]}
        hit = [(key, val) for key, val in sorted(cp.items()) if {key[0], key[1]} == want]
        if not hit:
            add("I6", "FAIL", f"{c['name']} ({c['a']}-{c['b']}) is not realized: no foils of these two nodes face each other")
            caps.append(dict(name=c["name"], nodes=[c["a"], c["b"]], realized=False))
            continue
        for key, val in hit:
            used.add(key)
            rot = key[2] == "rotating"
            row = dict(name=c["name"], nodes=[c["a"], c["b"]], realized=True, relation=key[2],
                       C_max_pF=max(val), C_min_pF=min(val))
            caps.append(row)
            if rot != (c["name"] in VARIABLE_CAPS) and key[2] != "modulated":
                add("I6", "FAIL", f"{c['name']} is drawn {key[2]} but the machine needs it "
                                   f"{'rotating (a rotor plate against a stator plate)' if c['name'] in VARIABLE_CAPS else 'fixed'}")
    for key, val in sorted(cp.items()):
        if key in used or max(val) < STRAY_MIN_PF:
            continue
        a, b = key[0], key[1]
        across = [c["name"] for c in netlist if {c["a"], c["b"]} == {a, b}]
        row = dict(nodes=[a, b], relation=key[2], C_max_pF=max(val), C_min_pF=min(val), across=across)
        strays.append(row)
        val_s = f"{_f(max(val), 1)} pF" if key[2] == "fixed" else f"{_f(min(val), 1)}-{_f(max(val), 1)} pF over a turn"
        if key[2] == "modulated":
            val_s += " (fixed plates, rotating copper between)"
        add("I6", "WARN", f"STRAY capacitor {a}-{b} ({key[2]}): {val_s}" + (f", across {', '.join(across)}" if across else ""))
    if not any(f["rule"] == "I6" and f["level"] == "FAIL" for f in find):
        add("I6", "PASS", f"all {sum(1 for c in caps if c['realized'])} drawn netlist capacitors realized on their nodes")
    # I7 spark gaps
    nl_gaps = {c["name"]: c for c in netlist if c["kind"] == "gap"}
    sg = sphere_gaps(parts, nets)
    gaps = {}
    for g in sg:
        s = parts[g["stator"]]
        gname = s["name"].split("_")[0] if s["name"].split("_")[0] in nl_gaps else None
        if not g["partners"]:
            add("I7", "WARN", f"stator sphere {s['name']} faces no rotor sphere")
            continue
        for k, (dist, j) in g["partners"]:
            pair = {s["node"], parts[j]["node"]}
            ok = [n for n, c in nl_gaps.items() if {c["a"], c["b"]} == pair]
            if not ok:
                add("I7", "FAIL", f"PARASITIC GAP: {s['name']} (node {s['node']}) meets {parts[j]['name']} (node {parts[j]['node']}) "
                                   f"at {_f(dist, 2)} mm -- no gap joins these nodes in the netlist")
                continue
            name = gname if gname in ok else (ok[0] if len(ok) == 1 and gname is None else None)
            if name is None:
                add("I7", "FAIL", f"{s['name']} is named {gname or '(no gap)'} but joins nodes {', '.join(sorted(pair))}, "
                                   f"which the netlist gives to {', '.join(ok)}")
                continue
            e = gaps.setdefault(name, dict(name=name, nodes=[nl_gaps[name]["a"], nl_gaps[name]["b"]], spheres=0, s_min=dist, s_max=dist,
                                           d_stator=2 * s["r"], d_rotor=2 * parts[j]["r"], _seen=[]))
            if s["name"] not in e["_seen"]:
                e["_seen"].append(s["name"])
                e["spheres"] += 1
            e["s_min"], e["s_max"] = min(e["s_min"], dist), max(e["s_max"], dist)
    for n in nl_gaps:
        if n not in gaps:
            add("I7", "FAIL", f"{n} ({nl_gaps[n]['a']}-{nl_gaps[n]['b']}) is not realized by any sphere pair")
    for e in gaps.values():
        if e["s_max"] - e["s_min"] > 1e-6:
            add("I7", "WARN", f"{e['name']}: its spokes differ in spacing ({_f(e['s_min'], 3)}-{_f(e['s_max'], 3)} mm)")
    if not any(f["rule"] == "I7" and f["level"] == "FAIL" for f in find):
        add("I7", "PASS", f"all {len(gaps)} netlist gaps realized on their nodes, no parasitic gap")
    gaps = [{k: v for k, v in gaps[n].items() if k != "_seen"} for n in sorted(gaps)]
    # I8 names
    nl_by = {c["name"]: c for c in netlist}
    seen = {}
    for p in parts:
        seen[p["name"]] = seen.get(p["name"], 0) + 1
    for n in sorted(k for k, v in seen.items() if v > 1):
        add("I8", "FAIL", f"name {n} is used {seen[n]} times")
    nbad = 0
    for p in parts:
        lab = p["label"]
        desc = lab.split(" - ", 1)[1] if " - " in lab else lab
        m = NODE_TOKEN.search(desc)
        if p["kind"] == "insulator":
            if m:
                add("I8", "WARN", f"insulator {p['name']} is labelled 'node {m.group(1)}' -- an insulator is on no node")
                nbad += 1
            continue
        if m and canon(m.group(1)) != p["node"]:
            add("I8", "FAIL", f"{p['name']}: its label says node {m.group(1)}, its copper is on node {p['node']}")
            nbad += 1
        dec = canon(p["group"][5:]) if p["group"].startswith("node-") else None
        if dec is None:
            mg = GROUP_NODE.search(p["group_label"])
            dec = canon(mg.group(1)) if mg else None
        if dec is not None and dec != p["node"]:
            add("I8", "FAIL", f"{p['name']} (node {p['node']}) sits in group '{p['group']}', which declares node {dec}")
            nbad += 1
        pre = p["name"].split("_")[0]
        comp = nl_gaps.get(pre) or (nl_by.get(CAP_PREFIX[pre]) if pre in CAP_PREFIX else None)
        if comp and p["node"] not in (comp["a"], comp["b"]):
            add("I8", "FAIL", f"{p['name']} belongs to {comp['name']} ({comp['a']}-{comp['b']}) by name, but its copper is on node {p['node']}")
            nbad += 1
    if not any(f["rule"] == "I8" and f["level"] in ("FAIL", "WARN") for f in find):
        add("I8", "PASS", f"{len(parts)} parts: every label, group and gap / capacitor name states the node its copper is on")
    # I9 off-model
    off = []
    drawn_nodes = set(by_node)
    for c in netlist:
        if c["name"] in DRAWN_CAPS or c["kind"] == "gap":
            continue
        off.append(dict(name=c["name"], kind=c["kind"], nodes=[c["a"], c["b"]], drawn=[n for n in (c["a"], c["b"]) if n in drawn_nodes]))
    both = [o["name"] for o in off if len(o["drawn"]) == 2]
    add("I9", "INFO", f"{len(off)} netlist components are off-model; {len(both)} join two drawn nets and need a "
                      f"connection there: {', '.join(both) or 'none'}")
    # the nets table
    nt = []
    for k, v in enumerate(nets):
        kinds = {}
        for i in v:
            kinds[parts[i]["kind"]] = kinds.get(parts[i]["kind"], 0) + 1
        node = node_of_net[k]
        nt.append(dict(net=k, node=node if node else "+".join(tags[k]) or "?", info=NODE_INFO.get(node, ""), parts=len(v),
                       kinds={x: kinds[x] for x in sorted(kinds)}, frame="+".join(sorted({parts[i]["frame"] for i in v}))))
    nt.sort(key=lambda r: (r["node"], r["net"]))
    lv = [f["level"] for f in find]
    rep = dict(tool=TOOL, source=source, verdict="FAIL" if "FAIL" in lv else "PASS",
               counts=dict(FAIL=lv.count("FAIL"), WARN=lv.count("WARN"), PASS=lv.count("PASS"), INFO=lv.count("INFO")),
               nets=nt, capacitors=caps, strays=strays, gaps=gaps, offmodel=off, findings=find,
               parts=len(parts), conductors=sum(1 for p in parts if p["kind"] != "insulator"))
    return rep


def render(rep):
    L = [f"CIRCUIT INTEGRITY ({rep['tool']}) - {rep['source']}",
         f"verdict {rep['verdict']}: {rep['counts']['FAIL']} FAIL, {rep['counts']['WARN']} WARN  "
         f"({rep['parts']} parts, {rep['conductors']} conductors, {len(rep['nets'])} nets)", "", "nets:"]
    byn = {}
    for n in rep["nets"]:
        byn.setdefault(n["node"], []).append(n)
    for node in sorted(byn):
        v = byn[node]
        tail = f"  ({len(v)} separate nets: OPEN)" if len(v) > 1 else ""
        L.append(f"  {node:>6}  {sum(x['parts'] for x in v):>4} parts  {v[0]['frame']:<6} {v[0]['info']}{tail}")
    L += ["", "capacitors of the netlist:"]
    for c in rep["capacitors"]:
        if not c["realized"]:
            L.append(f"  {c['name']:<6} {'-'.join(c['nodes']):<9} NOT REALIZED")
        elif c["relation"] == "fixed":
            L.append(f"  {c['name']:<6} {'-'.join(c['nodes']):<9} fixed     {_f(c['C_max_pF'], 2)} pF")
        else:
            L.append(f"  {c['name']:<6} {'-'.join(c['nodes']):<9} rotating  {_f(c['C_min_pF'], 2)}-{_f(c['C_max_pF'], 2)} pF")
    if rep["strays"]:
        L += ["", "stray capacitors (facing foils not in the netlist):"]
        for s in rep["strays"]:
            v = _f(s["C_max_pF"], 2) + " pF" if s["relation"] == "fixed" else f"{_f(s['C_min_pF'], 2)}-{_f(s['C_max_pF'], 2)} pF"
            L.append(f"  {'-'.join(s['nodes']):<9} {s['relation']:<9} {v}" + (f"  across {', '.join(s['across'])}" if s["across"] else ""))
    L += ["", "spark gaps of the netlist:"]
    for g in rep["gaps"]:
        L.append(f"  {g['name']:<6} {'-'.join(g['nodes']):<7} {g['spheres']} stator spheres, gap {_f(g['s_min'], 2)} mm "
                 f"(spheres {_f(g['d_stator'], 1)} / {_f(g['d_rotor'], 1)} mm)")
    L += ["", "findings:"]
    for f in rep["findings"]:
        L.append(f"  [{f['level']:<4}] {f['rule']} {f['text']}")
    return "\n".join(L)


# ---- STEP: the same parts, recognized from the B-rep (FreeCAD / Fusion 360 exports; needs OCP) ----------------
LABEL_TAIL = re.compile(r"\[([^\[\],]+), (stator|rotor A|rotor B|rotor AB)\]\s*$")
# "<group> / <name> - <description>"; Fusion 360 writes "/" as "-" ("node-2 - SG1_sph_6 - ...")
LABEL_HEAD = re.compile(r"^(node-(?:R-[AB]|n\d+|\d+)|carriers|dielectrics|[A-Za-z0-9_]+(?:-[A-Za-z]+)?) [/-] ([A-Za-z0-9_]+) - (.*)$")


def parts_from_step(path):
    """Every solid of a STEP written from the bill of solids, as an analysis part: its name and label from the
    STEP product, its node from the label's group prefix (node-X), its material and body from the label's tail,
    its geometry recognized from its faces (annular sector slab, sphere, cylinder)."""
    from OCP.STEPCAFControl import STEPCAFControl_Reader
    from OCP.TDocStd import TDocStd_Document
    from OCP.TCollection import TCollection_ExtendedString
    from OCP.XCAFDoc import XCAFDoc_DocumentTool
    from OCP.TDF import TDF_Label, TDF_ChildIterator
    from OCP.TDataStd import TDataStd_Name
    from OCP.TopLoc import TopLoc_Location
    doc = TDocStd_Document(TCollection_ExtendedString("XmlOcaf"))
    rd = STEPCAFControl_Reader()
    rd.SetNameMode(True)
    rd.ReadFile(path)
    rd.Transfer(doc)
    tool = XCAFDoc_DocumentTool.ShapeTool_s(doc.Main())

    def name_of(lab):
        a = TDataStd_Name()
        return a.Get().ToExtString() if lab.FindAttribute(TDataStd_Name.GetID_s(), a) else ""
    solids = []

    def walk(lab, loc, group):
        if tool.IsAssembly_s(lab):
            it = TDF_ChildIterator(lab, False)
            while it.More():
                c = it.Value()
                if tool.IsComponent_s(c):
                    ref = TDF_Label()
                    tool.GetReferredShape_s(c, ref)
                    walk(ref, loc.Multiplied(tool.GetLocation_s(c)), name_of(lab))
                it.Next()
        else:
            shp = tool.GetShape_s(lab)
            solids.append((name_of(lab), group, shp.Moved(loc)))
    it = TDF_ChildIterator(tool.Label(), False)          # the top-level shapes; the free ones are the roots
    while it.More():
        lab = it.Value()
        if tool.IsFree_s(lab) and tool.IsShape_s(lab):
            walk(lab, TopLoc_Location(), "")
        it.Next()
    out = []
    if solids and not any(LABEL_TAIL.search(lb) or NODE_TOKEN.search(lb) for lb, _, _ in solids):
        raise ValueError("no part names with a node in this STEP: the names did not survive the export")
    for label, group, shp in solids:
        g = _recognize(shp)
        mh = LABEL_HEAD.match(label)
        if mh:
            grp, name = mh.group(1), mh.group(2)
        else:
            head = label.split(" - ", 1)[0]
            grp, name = (head.split(" / ", 1) + [""])[:2] if " / " in head else ("", head)
        name = name or label
        m = LABEL_TAIL.search(label)
        if m:
            mat, body = m.group(1), m.group(2)
        else:                                            # a STEP written before the [material, body] tail
            mat, body = _legacy_material(name, label), LEGACY_BODY.get(grp, "rotor AB" if name.startswith("septum") else "stator")
        cond = is_conductor(mat)
        desc = mh.group(3) if mh else (label.split(" - ", 1)[1] if " - " in label else label)
        mt = NODE_TOKEN.search(desc)
        node = canon(grp[5:]) if grp.startswith("node-") else (canon(mt.group(1)) if mt else None)
        raw = (grp[5:] if grp.startswith("node-") else (mt.group(1) if mt else "")) if cond else ""
        q = dict(name=name, label=label, group=grp, group_label=group, material=mat, body=body,
                 frame=frame_of(body), node_raw=raw, node=node if cond else None)
        if g is None:
            q.update(kind="unrecognized")
        elif not cond:
            q.update(kind="insulator", **g)
            q["eps"], q["eps_known"] = eps_of(mat)
        else:
            q.update(kind={"sector": "foil", "sphere": "sphere", "rod": "rod"}[g.pop("shape")], **g)
        q.pop("shape", None)
        out.append(q)
    return out


def _legacy_material(name, label):
    """the material of a solid from an older STEP (no [material, body] tail), from its name and label."""
    if "Al foil" in label:
        return "Al foil"
    for key, mat in (("_sph_", "W-Cu sphere"), ("tip_", "W-Cu sphere"), ("_btn_", "W-Cu sphere"), ("_stem_", "Cu stem"),
                     ("_lead_", "Cu lead"), ("_link_", "Cu link"), ("bus_", "Cu bus")):
        if key in name:
            return mat
    for key in ("garolite", "mica", "G10", "carrier", "flange", "rotor disc"):
        if key in label:
            return "G10 carrier" if key in ("carrier", "flange", "rotor disc") else key
    return ""


def _recognize(shp):
    """annular sector slab about z / sphere / cylinder (rod), from the faces of a solid; None if neither."""
    from OCP.TopExp import TopExp_Explorer
    from OCP.TopAbs import TopAbs_FACE
    from OCP.TopoDS import TopoDS
    from OCP.BRepAdaptor import BRepAdaptor_Surface
    from OCP.GeomAbs import GeomAbs_Plane, GeomAbs_Cylinder, GeomAbs_Sphere
    from OCP.GProp import GProp_GProps
    from OCP.BRepGProp import BRepGProp
    from OCP.Bnd import Bnd_Box
    from OCP.BRepBndLib import BRepBndLib
    planes, cyls, sphs = [], [], []
    ex = TopExp_Explorer(shp, TopAbs_FACE)
    while ex.More():
        f = (getattr(TopoDS, "Face_s", None) or TopoDS.Face)(ex.Current())      # (the name differs across OCP builds)
        s = BRepAdaptor_Surface(f)
        t = s.GetType()
        if t == GeomAbs_Plane:
            pl = s.Plane()
            pr = GProp_GProps(); BRepGProp.SurfaceProperties_s(f, pr)
            c = pr.CentreOfMass()
            n = pl.Axis().Direction()
            planes.append(((n.X(), n.Y(), n.Z()), (c.X(), c.Y(), c.Z())))
        elif t == GeomAbs_Cylinder:
            cy = s.Cylinder()
            a = cy.Axis()
            cyls.append((cy.Radius(), (a.Direction().X(), a.Direction().Y(), a.Direction().Z()), (a.Location().X(), a.Location().Y(), a.Location().Z())))
        elif t == GeomAbs_Sphere:
            sp = s.Sphere()
            c = sp.Location()
            sphs.append((sp.Radius(), (c.X(), c.Y(), c.Z())))
        else:
            return None
        ex.Next()
    if sphs:
        r, c = sphs[0]
        return dict(shape="sphere", c=[c[0], c[1], c[2]], r=r)
    zc = [cy for cy in cyls if abs(abs(cy[1][2]) - 1.0) < 1e-9 and math.hypot(cy[2][0], cy[2][1]) < 1e-6]
    zp = [p for p in planes if abs(abs(p[0][2]) - 1.0) < 1e-9]
    if zc and len(zp) == 2 and len(zc) == len(cyls):
        rs = sorted({round(cy[0], 9) for cy in zc})
        r_in, r_out = (0.0, rs[0]) if len(rs) == 1 else (rs[0], rs[-1])
        z0, z1 = sorted((zp[0][1][2], zp[1][1][2]))
        rad = [p for p in planes if abs(p[0][2]) < 1e-9]
        if not rad:
            return dict(shape="sector", r_in=r_in, r_out=r_out, a0=0.0, w=360.0, z0=z0, z1=z1)
        pr = GProp_GProps(); BRepGProp.VolumeProperties_s(shp, pr)
        cm = pr.CentreOfMass()
        am = math.degrees(math.atan2(cm.Y(), cm.X()))
        ang = sorted(math.degrees(math.atan2(p[1][1], p[1][0])) for p in rad)
        d = [_sdeg(a - am) for a in ang]
        lo, hi = min(d), max(d)
        return dict(shape="sector", r_in=r_in, r_out=r_out, a0=am + lo, w=hi - lo, z0=z0, z1=z1)
    if len(cyls) == 1 and len(planes) == 2:
        r, dvec, _ = cyls[0]
        c0, c1 = planes[0][1], planes[1][1]
        return dict(shape="rod", p0=list(c0), p1=list(c1), r=r)
    bb = Bnd_Box(); BRepBndLib.Add_s(shp, bb)
    return None


# ---- self-test (on load) --------------------------------------------------------------------------------------
def _mini():
    """a two-plate rotor/stator machine with one gap, and its netlist."""
    def foil(name, node, body, z0, grp="node-x"):
        return dict(name=name, label=f"{grp} / {name} - plate, node {node} [Al foil, {body}]", group=grp, group_label="",
                    material="Al foil", body=body, frame=frame_of(body), node_raw=node, node=node, kind="foil",
                    r_in=100.0, r_out=200.0, a0=0.0, w=30.0, z0=z0, z1=z0 + 1.0)
    st = foil("C1_stator_1", "1", "stator", 0.0, "node-1")
    ro = foil("C1_rotor_1", "R-A", "rotor A", 8.0, "node-R-A")
    s1 = dict(name="SG1_sph_1", label="node-2 / SG1_sph_1 - sphere, node 2 [W-Cu sphere, stator]", group="node-2", group_label="",
              material="W-Cu sphere", body="stator", frame="stator", node_raw="2", node="2", kind="sphere", c=[300.0, 0.0, 0.0], r=6.0)
    s2 = dict(s1, name="rt_1", label="node-R-A / rt_1 - tip, node R-A [W-Cu sphere, rotor A]", group="node-R-A", body="rotor A",
              frame="rotor", node_raw="R-A", node="R-A", c=[300.0, 0.0, 17.5])
    f2 = dict(foil("Ca_el_1", "2", "stator", -10.0, "node-2"), r_in=290.0, r_out=310.0)
    lead = dict(name="SG1_lead_1a", label="node-2 / SG1_lead_1a - lead, node 2 [Cu lead, stator]", group="node-2", group_label="",
                material="Cu lead", body="stator", frame="stator", node_raw="2", node="2", kind="rod",
                p0=[300.0, 0.0, 0.0], p1=[300.0, 0.0, -9.5], r=1.5)
    ro_tie = dict(lead, name="rt_lead_1a", label="node-R-A / rt_lead_1a - lead, node R-A [Cu lead, rotor A]", group="node-R-A",
                  body="rotor A", frame="rotor", node_raw="R-A", node="R-A", p0=[300.0, 0.0, 17.5], p1=[190.0, 0.0, 8.5])
    nl = [dict(name="C1", a="R-A", b="1", kind="capacitor"), dict(name="SG1", a="2", b="R-A", kind="gap")]
    return [st, ro, s1, s2, f2, lead, ro_tie], nl


def _selftest():
    base, nl = _mini()
    lv = lambda rep, rule: {f["level"] for f in rep["findings"] if f["rule"] == rule}
    ok = True
    r0 = analyze([dict(p) for p in base], nl, "selftest")
    ok &= lv(r0, "I1") == {"PASS"} and lv(r0, "I2") == {"PASS"} and lv(r0, "I4") == {"PASS"} and lv(r0, "I7") == {"PASS"}
    c1 = [c for c in r0["capacitors"] if c["name"] == "C1"][0]
    want = EPS0 * EPS_AIR * (0.5 * math.radians(30.0) * (200.0 ** 2 - 100.0 ** 2)) * 1e-6 / 7e-3 * 1e12   # 9.94 pF
    ok &= c1["relation"] == "rotating" and abs(c1["C_max_pF"] - want) < 1e-9 * want and c1["C_min_pF"] == 0.0
    # a lead that touches a different node: SHORT
    short = [dict(p) for p in base] + [dict(base[5], name="bad", p0=[300.0, 0.0, -9.5], p1=[150.0, 0.0, 0.5], node="2", node_raw="2")]
    ok &= "FAIL" in lv(analyze(short, nl), "I1")
    # the same node in two pieces: OPEN
    op = [dict(p) for p in base] + [dict(base[0], name="C1_stator_2", a0=180.0)]
    ok &= "FAIL" in lv(analyze(op, nl), "I2")
    # a part grouped under another node (the ND1 / SG1 case): NAMES
    mis = [dict(p) for p in base]
    mis[2] = dict(mis[2], group="ND1", group_label="ND1 - stator carrier ND1 (node 1): C1 stator plate")
    ok &= "FAIL" in lv(analyze(mis, nl), "I8")
    # a gap named SG1 drawn on the wrong pair: GAP
    wg = [dict(p) for p in base]
    wg[3] = dict(wg[3], node="1", node_raw="1")
    ok &= "FAIL" in lv(analyze(wg, nl), "I7")
    # copper from the rotor tied to the stator: ROTATING JOINT
    rj = [dict(p) for p in base] + [dict(base[6], name="rt_bad", body="stator", frame="stator", p0=[190.0, 0.0, 8.5], p1=[190.0, 0.0, 0.5])]
    ok &= "FAIL" in lv(analyze(rj, nl), "I4")
    if not ok:
        raise AssertionError("circuit_integrity on-load self-test FAILED")
    return True


SELFTEST_OK = _selftest()


def main(argv):
    import argparse
    ap = argparse.ArgumentParser(description="circuit integrity of a DCCREG pump-geometry build against the netlist of record")
    ap.add_argument("model", help="pump-geometry JSON (bill of solids) or a STEP written from it")
    ap.add_argument("--netlist", default=os.path.join(ROOT, "topology_edge_list.csv"))
    ap.add_argument("--json", help="write the report as JSON here")
    a = ap.parse_args(argv)
    nl = load_netlist(a.netlist)
    if a.model.lower().endswith((".step", ".stp")):
        parts = parts_from_step(a.model)
    else:
        parts = parts_from_design(json.load(open(a.model)))
    rep = analyze(parts, nl, os.path.basename(a.model))
    print(render(rep))
    if a.json:
        with open(a.json, "w") as f:
            json.dump(rep, f, indent=1)
    return 0 if rep["verdict"] == "PASS" else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
