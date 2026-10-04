#!/usr/bin/env python3
"""sim/rt_interleave.py -- interleaved (multi-layer) C1 / C2 and Cx stacks, derived from a pump-geometry build
(design loop round 4, TMD) [IR].

N = rotor plates per stack = stator plates per stack, so every stack has 2N - 1 gaps (N = 1 is the build as is).
Between a stack's inner electrode (the one nearer the septum) and its outer electrode, 2(N - 1) double-sided
intermediate plates are inserted, alternating in type (the first one is the outer electrode's type), each a foil
| carrier | foil on a thin carrier of the build's carrier material. Everything beyond the stack's outer electrode
moves axially outward by the added thickness (rods and sectors that span the boundary are stretched).

Wiring (so that every node stays one net):
  - the type with the smaller inner radius is linked at its inner rim: an axial rod at r_in + 4 mm through all
    plates of that type; the other type's carriers have a bore that clears it;
  - the other type is linked at its outer rim: a small foil tab (4 deg, at each sector centre) on every plate of
    that type, reaching an axial rod at max(r_out) + 6 mm; the first type's carriers stop short of that rod.
Mica facings (sectored, the foil footprint + margin) are added on every new gap face, as the build has them.

This is a screening build for the field solve and the integrity tool. If interleaving is adopted it moves into
the pump-geometry builder (Python + JS) and the CAD exports.
Usage: python3 sim/rt_interleave.py <base design.json> <N> <out design.json>
"""
import copy
import json
import math
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path[:0] = [HERE]

STACKS = {   # side -> stacks: (inner electrode, outer electrode, gap id)
    "A": [("C1_rotor", "C1_stator", "C1-gap"), ("Cx4_pickup", "Cx4_bars", "Cx4-gap")],
    "B": [("C2_rotor", "C2_stator", "C2-gap"), ("Cx3_pickup", "Cx3_bars", "Cx3-gap")],
}
T_MID = 4.0           # intermediate plate carrier thickness (mm) [IR mechanical]
LINK_R = 2.0          # link rod radius (mm)
CLEAR = 2.0           # radial clearance of a carrier edge to the other type's link rod (mm)
TAB_W = 4.0           # tab width (deg)


def _zs(p):
    if p["shape"] == "sector":
        return [p["z0"], p["z1"]]
    if p["shape"] == "sphere":
        return [p["c"][2]]
    return [p["p0"][2], p["p1"][2]]


def _shift(parts, zb, dz, side, keep=()):
    """move every z beyond zb (side A: z <= zb, B: z >= zb) by dz outward; spanning parts stretch."""
    beyond = (lambda z: z <= zb + 1e-9) if side == "A" else (lambda z: z >= zb - 1e-9)
    sgn = -1.0 if side == "A" else 1.0
    for p in parts:
        if p["name"] in keep:
            continue
        if p["shape"] == "sector":
            z0, z1 = p["z0"], p["z1"]
            if beyond(z0) and beyond(z1):
                p["z0"], p["z1"] = z0 + sgn * dz, z1 + sgn * dz
            elif beyond(z0) or beyond(z1):
                if side == "A":
                    p["z0"] = z0 + sgn * dz                    # z0 is the outer (more negative) face
                else:
                    p["z1"] = z1 + sgn * dz
        elif p["shape"] == "sphere":
            if beyond(p["c"][2]):
                p["c"] = [p["c"][0], p["c"][1], p["c"][2] + sgn * dz]
        else:
            for k in ("p0", "p1"):
                if beyond(p[k][2]):
                    p[k] = [p[k][0], p[k][1], p[k][2] + sgn * dz]


def _follow_partners(parts, before, dz, sgn, reach=30.0):
    """a spark-gap sphere left behind follows its moved partner (same r and angle, across the gap), so every gap
    keeps its spacing; rod endpoints at its centre (the stem) follow, the stem stretches [IR mechanical flag]."""
    sph = {p["name"]: p for p in parts if p["shape"] == "sphere"}
    moved = [n for n, p in sph.items() if abs(p["c"][2] - before[n][2]) > 1e-9]
    stay = [n for n in sph if n not in moved]
    follow = []
    for n in stay:
        c = before[n]
        for m in moved:
            b = before[m]
            if sph[m].get("node") == sph[n].get("node"):
                continue
            # a rotating gap: the tip sweeps past its stator sphere on the same radius (revolved), across z
            if (abs(math.hypot(c[0], c[1]) - math.hypot(b[0], b[1])) < 1.0 and abs(c[2] - b[2]) < reach
                    and str(sph[m].get("body", ""))[:5] != str(sph[n].get("body", ""))[:5]):
                follow.append(n)
                break
    for n in follow:
        c = before[n]
        sph[n]["c"] = [c[0], c[1], c[2] + sgn * dz]
        for p in parts:
            if p["shape"] == "rod":
                for k in ("p0", "p1"):
                    if math.dist(p[k], c) < 1e-6:
                        p[k] = [c[0], c[1], c[2] + sgn * dz]
    return follow


def _shift_stack(items, zb, dz, side):
    for it in items:
        q = dict(name="", shape="sector", z0=it["z0"], z1=it["z1"])
        _shift([q], zb, dz, side)
        it["z0"], it["z1"] = q["z0"], q["z1"]


def _pol(r, a, z):
    return [r * math.cos(math.radians(a)), r * math.sin(math.radians(a)), z]


def interleave(design, N):
    d = copy.deepcopy(design)
    if N <= 1:
        return d
    g = d["geom"]
    fp = d["footprints"]
    stack = {it["id"]: it for it in d["stack"]}
    parts = d["parts"]
    tf = g["t_foil"]
    mat = g.get("carrier_mat", "G10")
    added = []
    for side in ("A", "B"):
        sgn = -1.0 if side == "A" else 1.0
        for inner, outer, gap_id in STACKS[side]:
            gi = stack[gap_id]
            gapt = gi["z1"] - gi["z0"]
            fin, fout = fp[inner], fp[outer]
            def find(e):
                return next(p for p in parts if p.get("role") == "foil" and p["shape"] == "sector" and p.get("cap") == e["cap"]
                            and p["node"] == e["node"] and abs(p["r_in"] - e["r_in"]) < 1e-6 and abs(p["r_out"] - e["r_out"]) < 1e-6)
            pin, pout = find(fin), find(fout)
            cap = pin["cap"]
            body_in, body_out = pin["body"], pout["body"]
            # the face of the inner electrode toward the gap, and the boundary (the outer electrode's gap face)
            z_face = gi["z1"] if side == "A" else gi["z0"]           # inner electrode's gap face
            zb = gi["z0"] if side == "A" else gi["z1"]               # outer electrode's gap face
            per = gapt + 2 * tf + T_MID
            dz = 2 * (N - 1) * per
            outer_facings = [p["name"] for p in parts if p.get("role") == "dielectric" and f"facing on {outer} " in p.get("label", "")]
            # move the outer electrode, its facings and everything beyond it
            before = {p["name"]: list(p["c"]) for p in parts if p["shape"] == "sphere"}
            _shift(parts, zb, dz, side, keep=outer_facings)
            _follow_partners(parts, before, dz, sgn)
            for p in parts:
                if p["name"] in outer_facings:
                    p["z0"], p["z1"] = p["z0"] + sgn * dz, p["z1"] + sgn * dz
            _shift_stack(d["stack"], zb, dz, side)
            # inner-linked type: the smaller r_in
            types = {"in": dict(fp=fin, node=fin["node"], body=body_in, part=pin), "out": dict(fp=fout, node=fout["node"], body=body_out, part=pout)}
            inner_link = "in" if fin["r_in"] <= fout["r_in"] else "out"
            tab_link = "out" if inner_link == "in" else "in"
            r_link_in = types[inner_link]["fp"]["r_in"] + 4.0
            r_link_out = max(fin["r_out"], fout["r_out"]) + 6.0
            # facing thickness / margin as the build has them in this gap
            fac = [p for p in parts if p.get("role") == "dielectric" and p.get("cap") == cap and p["name"].startswith(f"{cap}_mica")]
            t_fac = (fac[0]["z1"] - fac[0]["z0"]) if fac else 0.0
            m_fac = (g["ca_margin"] if cap.startswith("Cx") else g.get("c1_mica_m", 1.0))
            z = z_face
            seq = [("out" if k % 2 == 0 else "in") for k in range(2 * (N - 1))]
            foils_by_type = {"in": [(pin, None)], "out": []}
            for k, ty in enumerate(seq):
                T = types[ty]
                e = T["fp"]
                z_gap_end = z + sgn * gapt
                z_f1 = (z_gap_end, z_gap_end + sgn * tf)
                z_c = (z_f1[1], z_f1[1] + sgn * T_MID)
                z_f2 = (z_c[1], z_c[1] + sgn * tf)
                z = z_f2[1]
                lo = lambda a, b: (min(a, b), max(a, b))
                if ty == inner_link:
                    c_rin, c_rout = 0.0 if T["body"].startswith("rotor") else max(0.0, e["r_in"] - 8.0), r_link_out - LINK_R - CLEAR
                else:
                    c_rin, c_rout = r_link_in + LINK_R + CLEAR, max(d["r_edge"] * 402.0 / 500.0, r_link_out + 6.0)
                tag = f"IL{side}_{cap}_{k + 1}"
                z0, z1 = lo(*z_c)
                added.append(dict(name=f"{tag}_carrier", label=f"carriers / {tag}_carrier - interleave plate {k + 1} carrier ({cap}), insulating [{mat} carrier, {T['body']}]",
                                  assembly="carriers", role="carrier", carrier=tag, node="", cap="", material=f"{mat} carrier",
                                  body=T["body"], shape="sector", chains=[tag], r_in=c_rin, r_out=c_rout, start_deg=0.0, w_deg=360.0,
                                  z0=z0, z1=z1, rgb=[0.35, 0.4, 0.47], volume=math.pi * (c_rout ** 2 - c_rin ** 2) * (z1 - z0)))
                for j, zf in enumerate((z_f1, z_f2)):
                    a0, a1 = lo(*zf)
                    for s_i, s0 in enumerate(e["starts"]):
                        added.append(dict(name=f"{tag}_foil{j}_{s_i + 1}", label=f"node-{T['node']} / {tag}_foil{j}_{s_i + 1} - interleave plate {k + 1} {cap} foil [Al foil, {T['body']}]",
                                          assembly=f"node-{T['node']}", role="foil", carrier=tag, node=T["node"], cap=cap, material="Al foil",
                                          body=T["body"], shape="sector", chains=[tag], r_in=e["r_in"], r_out=e["r_out"], start_deg=s0,
                                          w_deg=e["w_deg"], z0=a0, z1=a1, rgb=[0.8, 0.8, 0.8], volume=0.0))
                        if t_fac > 0:                     # facing on the gap side of this foil
                            # foil 0 faces back toward the previous gap, foil 1 outward to the next one
                            if side == "A":
                                fz = (a1, a1 + t_fac) if j == 0 else (a0 - t_fac, a0)
                            else:
                                fz = (a0 - t_fac, a0) if j == 0 else (a1, a1 + t_fac)
                            dw = math.degrees(m_fac / max(e["r_in"], 1e-9))
                            added.append(dict(name=f"{tag}_mica{j}_{s_i + 1}", label=f"dielectrics / {tag}_mica{j}_{s_i + 1} - {cap} mica facing [mica, {T['body']}]",
                                              assembly="dielectrics", role="dielectric", carrier=tag, node="", cap=cap, material="mica",
                                              body=T["body"], shape="sector", chains=[tag], r_in=max(0.0, e["r_in"] - m_fac),
                                              r_out=e["r_out"] + m_fac, start_deg=s0 - dw, w_deg=e["w_deg"] + 2 * dw,
                                              z0=min(fz), z1=max(fz), rgb=[0.9, 0.85, 0.6], volume=0.0))
                    foils_by_type[ty].append((dict(z0=a0, z1=a1), tag))
                z = z_f2[1]
            # the facing on the inner face of the (moved) outer electrode exists already; the facing on the last
            # intermediate's outer face toward it was added above. The outer electrode's own foils:
            foils_by_type["out"].append((pout, None))
            # links
            for ty, how in ((inner_link, "inner"), (tab_link, "tab")):
                T = types[ty]; e = T["fp"]
                fl = foils_by_type[ty]
                zmids = [0.5 * (f["z0"] + f["z1"]) for f, _ in fl]
                z_lo, z_hi = min(zmids), max(zmids)
                for s_i, s0 in enumerate(e["starts"]):
                    a = s0 + e["w_deg"] / 2
                    r = r_link_in if how == "inner" else r_link_out
                    added.append(dict(name=f"IL{side}_{cap}_{ty}_link_{s_i + 1}", label=f"node-{T['node']} / IL{side}_{cap}_{ty}_link_{s_i + 1} - interleave link [Cu link, {T['body']}]",
                                      assembly=f"node-{T['node']}", role="link", carrier="", node=T["node"], cap="", material="Cu link",
                                      body=T["body"], shape="rod", chains=[f"IL{side}-{cap}-{ty}"], p0=_pol(r, a, z_lo), p1=_pol(r, a, z_hi),
                                      r=LINK_R, rgb=[0.9, 0.6, 0.3], volume=0.0))
                    if how == "tab":
                        for f, tg in fl:
                            added.append(dict(name=f"IL{side}_{cap}_{ty}_tab_{tg or 'base'}_{f['z0']:.2f}_{s_i + 1}", label=f"node-{T['node']} / tab - interleave link tab [Al foil, {T['body']}]",
                                              assembly=f"node-{T['node']}", role="foil", carrier=tg or "", node=T["node"], cap="", material="Al foil",
                                              body=T["body"], shape="sector", chains=[f"IL{side}-{cap}-{ty}"], r_in=e["r_out"] - 2.0,
                                              r_out=r_link_out + LINK_R + 1.0, start_deg=a - TAB_W / 2, w_deg=TAB_W,
                                              z0=f["z0"], z1=f["z1"], rgb=[0.8, 0.8, 0.8], volume=0.0))
            stack = {it["id"]: it for it in d["stack"]}
    d["parts"] = parts + added
    d["interleave"] = dict(N=N, gaps_per_stack=2 * N - 1, t_mid=T_MID, note="screening build (sim/rt_interleave.py)")
    return d


if __name__ == "__main__":
    src, N, dst = sys.argv[1], int(sys.argv[2]), sys.argv[3]
    d = interleave(json.load(open(src)), N)
    json.dump(d, open(dst, "w"))
    print(dst, len(d["parts"]), "parts")
