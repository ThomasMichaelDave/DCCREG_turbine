#!/usr/bin/env python3
"""sim/rt_buildcheck.py -- machine-build review of any pump-geometry design JSON, read from its parts list (so a
derived build, e.g. sim/rt_interleave.py, is checked the same way as a builder output) [OC geometry, IR limits].

Checks (rotor A, rotor B and the septum co-rotate as one body; the stator counter-rotates):
  C1 counter-rotation: no rotor part's revolved (r, z) envelope overlaps a stator part's   -> FAIL if any
  C2 running clearance: the tightest revolved rotor-stator gap (any material)              -> WARN below 2 mm
  C3 HV, counter-rotating: an EXPOSED conductor (sphere, stem, lead in air, interleave link) against any conductor
     of a different node on the other body, revolved distance >= sg_khv x the largest spark-gap spacing (the
     builder's rule); spark-gap electrode pairs and capacitor foil faces are the intended gaps -> FAIL
  C4 HV, same body: different-node conductors (not capacitor foil pairs), revolved distance as a lower bound of
     the true distance; below the rule -> WARN (inspect: the true 3-D distance may be larger)
  M  mechanics (info): longest stem and its slenderness, thinnest carrier spanning more than 200 mm, axial length,
     masses per body, rim speed at the rotor's outer radius at max rpm.
Usage: python3 sim/rt_buildcheck.py <design.json> [more ...] -> prints, and <design>.buildcheck.json
"""
import json
import math
import os
import sys

DENS = {"al foil": 2.70, "cu ": 8.96, "w-cu": 15.0, "polished sphere": 15.0, "mica": 2.8, "ptfe": 2.2, "g10": 1.85,
        "garolite": 1.85}                                       # g/cm^3 [IR]
CAP_ROLES = ("foil",)
GAP_ROLES = ("gap-stator", "gap-rotor", "gap-stem")


def body(p):
    b = str(p.get("body", ""))
    return "rotor" if b.startswith("rotor") else "stator"


def is_cond(p):
    m = str(p.get("material", "")).lower()
    return any(k in m for k in ("al foil", "cu ", "w-cu", "sphere"))


def rz_pts(p, n=12):
    """points of the part's revolved image in the (r, z) half-plane, and an inflation radius."""
    if p["shape"] == "sector":
        return None, 0.0, (p["r_in"], p["r_out"], p["z0"], p["z1"])
    if p["shape"] == "sphere":
        c = p["c"]
        return [(math.hypot(c[0], c[1]), c[2])], p["r"], None
    a, b = p["p0"], p["p1"]
    pts = []
    for j in range(n + 1):
        t = j / n
        x = [a[i] + (b[i] - a[i]) * t for i in range(3)]
        pts.append((math.hypot(x[0], x[1]), x[2]))
    return pts, p["r"], None


def box_of(img):
    pts, inf_, box = img
    if box is not None:
        return box
    return (min(q[0] for q in pts) - inf_, max(q[0] for q in pts) + inf_, min(q[1] for q in pts) - inf_, max(q[1] for q in pts) + inf_)


def dist(i1, i2):
    """revolved (r, z) distance between two parts' images (0 when they overlap)."""
    p1, f1, b1 = i1
    p2, f2, b2 = i2
    if b1 is not None and b2 is not None:
        return math.hypot(max(0.0, b1[0] - b2[1], b2[0] - b1[1]), max(0.0, b1[2] - b2[3], b2[2] - b1[3]))
    if b1 is not None or b2 is not None:
        pts, f, b = (p2, f2, b1) if b1 is not None else (p1, f1, b2)
        return max(0.0, min(math.hypot(max(0.0, b[0] - r, r - b[1]), max(0.0, b[2] - z, z - b[3])) for r, z in pts) - f)
    return max(0.0, min(math.hypot(r1 - r2, z1 - z2) for r1, z1 in p1 for r2, z2 in p2) - f1 - f2)


def overlap(i1, i2):
    a, b = box_of(i1), box_of(i2)
    if i1[2] is not None and i2[2] is not None:
        return min(a[1], b[1]) - max(a[0], b[0]) > 1e-6 and min(a[3], b[3]) - max(a[2], b[2]) > 1e-6
    return dist(i1, i2) <= 1e-6 and min(a[1], b[1]) - max(a[0], b[0]) > 1e-6 and min(a[3], b[3]) - max(a[2], b[2]) > 1e-6


def exposed_names(d):
    """the builder's exposure rule: spheres, gap stems and non-embedded, non-riser gap leads; plus the interleave
    links (they cross the air gaps between plates)."""
    out = set()
    for it in (d.get("sparkgaps") or {}).get("items", []):
        if it["kind"] == "sphere" or (it["kind"] == "rod" and (it["role"] == "gap-stem" or (
                it["role"] == "gap-lead" and not it.get("embedded") and not it.get("riser")))):
            out.add(it["name"])
    out |= {p["name"] for p in d["parts"] if p.get("role") == "link" and p["name"].startswith("IL")}   # VIA* are embedded
    return out


def review(d):
    g = d["geom"]
    expo = exposed_names(d)
    need = g["sg_khv"] * max(g["sg_s_ret"], g["sg_s_load"], g["sg_s_fire"], g["sg_s_bs"])
    parts = d["parts"]
    img = [rz_pts(p) for p in parts]
    box = [box_of(i) for i in img]
    R = [k for k, p in enumerate(parts) if body(p) == "rotor"]
    S = [k for k, p in enumerate(parts) if body(p) == "stator"]
    out = dict(need_hv_mm=need)
    # C1 / C2 / C3
    coll, run_w, run_d, hv_w, hv_d, hv_list = [], float("inf"), "", float("inf"), "", []
    for i in R:
        for j in S:
            bi, bj = box[i], box[j]
            gap_box = math.hypot(max(0.0, bi[0] - bj[1], bj[0] - bi[1]), max(0.0, bi[2] - bj[3], bj[2] - bi[3]))
            if gap_box > max(need, 2.0) + 1e-9:
                continue
            pi, pj = parts[i], parts[j]
            dd = dist(img[i], img[j])
            if dd <= 1e-6 and overlap(img[i], img[j]):
                coll.append(f"{pi['name']} / {pj['name']}")
                continue
            if dd < run_w:
                run_w, run_d = dd, f"{pi['name']} / {pj['name']}: {dd:.2f} mm"
            if is_cond(pi) and is_cond(pj) and pi.get("node") != pj.get("node") and (pi["name"] in expo or pj["name"] in expo):
                if pi.get("role") in GAP_ROLES and pj.get("role") in GAP_ROLES:
                    continue                                  # the spark gaps themselves
                if pi.get("role") in CAP_ROLES and pj.get("role") in CAP_ROLES:
                    continue                                  # capacitor faces (their dielectric is D-MEDIUM)
                if dd < need:
                    hv_list.append((dd, f"{pi['name']} (node {pi.get('node')}) / {pj['name']} (node {pj.get('node')}): {dd:.2f} mm"))
                if dd < hv_w:
                    hv_w, hv_d = dd, f"{pi['name']} (node {pi.get('node')}) / {pj['name']} (node {pj.get('node')}): {dd:.2f} mm"
    hv_list.sort()
    out["C1_counter_rotation"] = dict(pass_=not coll, collisions=coll[:20], n=len(coll))
    out["C2_running_clearance"] = dict(warn=run_w < 2.0, tightest=run_d, mm=run_w)
    out["C3_hv_counter_rotating"] = dict(pass_=hv_w >= need - 1e-9, tightest=hv_d, n_below=len(hv_list),
                                         below=[s for _, s in hv_list[:15]])
    # C4 same body
    w4, d4, n4 = float("inf"), "", 0
    for grp in (R, S):
        cond = [k for k in grp if is_cond(parts[k])]
        for a in range(len(cond)):
            i = cond[a]
            for j in cond[a + 1:]:
                pi, pj = parts[i], parts[j]
                if pi.get("node") == pj.get("node"):
                    continue
                if pi.get("role") in CAP_ROLES and pj.get("role") in CAP_ROLES:
                    continue
                if pi.get("role") in GAP_ROLES and pj.get("role") in GAP_ROLES:
                    continue
                bi, bj = box[i], box[j]
                if math.hypot(max(0.0, bi[0] - bj[1], bj[0] - bi[1]), max(0.0, bi[2] - bj[3], bj[2] - bi[3])) > need:
                    continue
                dd = dist(img[i], img[j])
                if dd < need:
                    n4 += 1
                if dd < w4:
                    w4, d4 = dd, f"{pi['name']} (node {pi.get('node')}) / {pj['name']} (node {pj.get('node')}): {dd:.2f} mm"
    out["C4_hv_same_body_lower_bound"] = dict(warn=w4 < need, tightest=d4, n_below=n4)
    # mechanics
    stems = [(math.dist(p["p0"], p["p1"]), p["name"], p["r"]) for p in parts if p["shape"] == "rod" and p.get("role") == "gap-stem"]
    st = max(stems) if stems else (0, "", 1)
    thin = sorted(((p["z1"] - p["z0"], p["r_out"] - p["r_in"], p["name"], p.get("material")) for p in parts
                   if p["shape"] == "sector" and p.get("role") == "carrier" and p["r_out"] - p["r_in"] > 200))[:3]
    zs = [z for b in box for z in (b[2], b[3])]
    mass = {"rotor": 0.0, "stator": 0.0}
    for p in parts:
        m = str(p.get("material", "")).lower()
        rho = next((v for k, v in DENS.items() if k in m), None)
        if rho is None:
            continue
        if p["shape"] == "sector":
            v = math.pi * (p["r_out"] ** 2 - p["r_in"] ** 2) * (p["w_deg"] / 360.0) * (p["z1"] - p["z0"])
        elif p["shape"] == "sphere":
            v = 4.0 / 3.0 * math.pi * p["r"] ** 3
        else:
            v = math.pi * p["r"] ** 2 * math.dist(p["p0"], p["p1"])
        mass[body(p)] += rho * v * 1e-6                    # kg (mm^3 x g/cm^3 x 1e-6)
    r_rot = max(box[k][1] for k in R)
    out["M_mechanics"] = dict(longest_stem_mm=st[0], longest_stem=st[1], stem_slenderness=st[0] / (2 * st[2]) if st[2] else None,
                              thinnest_wide_carriers=[dict(t_mm=t, span_mm=s, name=n, material=m) for t, s, n, m in thin],
                              axial_length_mm=max(zs) - min(zs), mass_kg=mass, rotor_outer_r_mm=r_rot)
    out["verdict"] = "BUILD-OK" if out["C1_counter_rotation"]["pass_"] and out["C3_hv_counter_rotating"]["pass_"] else "BUILD-ISSUES"
    return out


if __name__ == "__main__":
    for path in sys.argv[1:]:
        d = json.load(open(path))
        r = review(d)
        json.dump(r, open(os.path.splitext(path)[0] + ".buildcheck.json", "w"), indent=1)
        print("==", os.path.basename(path), r["verdict"])
        for k, v in r.items():
            if isinstance(v, dict):
                print(f"  {k}: " + json.dumps({a: b for a, b in v.items() if a not in ('below', 'collisions')})[:420])
        if r["C1_counter_rotation"]["collisions"]:
            print("   collisions:", r["C1_counter_rotation"]["collisions"][:8])
        if r["C3_hv_counter_rotating"]["below"]:
            print("   HV below rule:", r["C3_hv_counter_rotating"]["below"][:8])
