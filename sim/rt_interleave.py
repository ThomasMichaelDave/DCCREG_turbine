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
VIA_R = 1.0           # through-plate via radius (mm)
SLEEVE = 3.0          # PTFE sleeve wall on every inter-plate link (mm): the link is then insulated [IR]
PLATE_MAT = "glass-bonded mica plate"   # intermediate plates (mica-glass composite, eps ~6.9) [IR mechanical]


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


def _sector(name, label, asm, role, carrier, node, cap, mat, body, r_in, r_out, a0, w, z0, z1, chains, rgb):
    return dict(name=name, label=label, assembly=asm, role=role, carrier=carrier, node=node, cap=cap, material=mat,
                body=body, shape="sector", chains=chains, r_in=r_in, r_out=r_out, start_deg=a0, w_deg=w,
                z0=min(z0, z1), z1=max(z0, z1), rgb=rgb, volume=0.0)


def _rod(name, label, asm, node, body, p0, p1, r, chains, role="link", mat="Cu link"):
    return dict(name=name, label=label, assembly=asm, role=role, carrier="", node=node, cap="", material=mat,
                body=body, shape="rod", chains=chains, p0=p0, p1=p1, r=r, rgb=[0.9, 0.6, 0.3], volume=0.0)


def interleave(design, N, hv=None):
    """N rotor plates = N stator plates per stack (2N - 1 gaps). hv: the HV clearance kept between an exposed
    inter-plate link and the other type's intermediate foils (default: the build's sg_khv x largest spacing)."""
    d = copy.deepcopy(design)
    if N <= 1:
        return d
    g = d["geom"]
    hv = hv if hv is not None else g["sg_khv"] * max(g["sg_s_ret"], g["sg_s_load"], g["sg_s_fire"], g["sg_s_bs"])
    fp = d["footprints"]
    parts = d["parts"]
    tf = g["t_foil"]
    mat = PLATE_MAT
    added = []
    for side in ("A", "B"):
        sgn = -1.0 if side == "A" else 1.0
        for inner, outer, gap_id in STACKS[side]:
            gi = {it["id"]: it for it in d["stack"]}[gap_id]
            gapt = gi["z1"] - gi["z0"]
            fin, fout = fp[inner], fp[outer]

            def find(e):
                return next(p for p in parts if p.get("role") == "foil" and p["shape"] == "sector" and p.get("cap") == e["cap"]
                            and p["node"] == e["node"] and abs(p["r_in"] - e["r_in"]) < 1e-6 and abs(p["r_out"] - e["r_out"]) < 1e-6)
            pin, pout = find(fin), find(fout)
            cap = pin["cap"]
            m_fac = g["ca_margin"] if cap.startswith("Cx") else g.get("c1_mica_m", 1.0)
            fac = [p for p in parts if p.get("role") == "dielectric" and p.get("cap") == cap and p["name"].startswith(f"{cap}_mica")]
            t_fac = (fac[0]["z1"] - fac[0]["z0"]) if fac else 0.0
            z_face = gi["z1"] if side == "A" else gi["z0"]           # the inner electrode's gap face
            zb = gi["z0"] if side == "A" else gi["z1"]               # the outer electrode's gap face
            dz = 2 * (N - 1) * (gapt + 2 * tf + T_MID)
            outer_facings = [p["name"] for p in parts if p.get("role") == "dielectric" and f"facing on {outer} " in p.get("label", "")]
            before = {p["name"]: list(p["c"]) for p in parts if p["shape"] == "sphere"}
            _shift(parts, zb, dz, side, keep=outer_facings)
            for p in parts:
                if p["name"] in outer_facings:
                    p["z0"], p["z1"] = p["z0"] + sgn * dz, p["z1"] + sgn * dz
            _follow_partners(parts, before, dz, sgn)
            _shift_stack(d["stack"], zb, dz, side)
            T = {"in": dict(fp=fin, node=fin["node"], body=pin["body"]), "out": dict(fp=fout, node=fout["node"], body=pout["body"])}
            ilink = "in" if fin["r_in"] <= fout["r_in"] else "out"       # linked at the inner rim
            tlink = "out" if ilink == "in" else "in"                      # linked at the outer rim (tabs)
            r_li = T[ilink]["fp"]["r_in"] + 4.0
            # C1 / C2: the link sits 4 mm beyond the foil edge, so the rotor spark-gap tips (r~404-416) keep the HV rule
            # from its core; Cx: beyond the wider mica facing margin
            r_lo = max(fin["r_out"], fout["r_out"]) + (4.0 if not cap.startswith("Cx") else m_fac + LINK_R + CLEAR + 1.0)
            # the other type's INTERMEDIATE foils keep hv from each exposed link (foil + facing margin)
            # links are sleeved (insulated): the other type's intermediate foils (+ facing) keep CLEAR from the sleeve
            r_sl = LINK_R + SLEEVE
            trim = {tlink: dict(r_in=max(T[tlink]["fp"]["r_in"], r_li + r_sl + CLEAR + m_fac)),
                    ilink: dict(r_out=min(T[ilink]["fp"]["r_out"], r_lo - r_sl - CLEAR - m_fac))}
            plates = {"in": [dict(foils=[(pin["z0"], pin["z1"])], base=True, chains=list(pin.get("chains", [])))], "out": []}
            z = z_face
            for k, ty in enumerate([("out" if k % 2 == 0 else "in") for k in range(2 * (N - 1))]):
                e = T[ty]["fp"]
                ri, ro = trim[ty].get("r_in", e["r_in"]), trim[ty].get("r_out", e["r_out"])
                f0 = (z + sgn * gapt, z + sgn * (gapt + tf))
                cz = (f0[1], f0[1] + sgn * T_MID)
                f1 = (cz[1], cz[1] + sgn * tf)
                z = f1[1]
                tag = f"IL{side}_{cap}_{k + 1}"
                body = T[ty]["body"]
                if ty == ilink:
                    c_ri = 0.0 if body.startswith("rotor") else max(0.0, e["r_in"] - 8.0)
                    c_ro = r_lo - r_sl - CLEAR
                else:
                    c_ri = r_li + r_sl + CLEAR
                    # ends inside the island-bar tip stems (r 404.5 - stem radius) and still holds the sleeved link end
                    c_ro = max(d["r_edge"] * 398.0 / 500.0, r_lo + r_sl + 1.0)
                added.append(_sector(f"{tag}_carrier", f"carriers / {tag}_carrier - interleave plate {k + 1} carrier ({cap}), insulating [{mat}, {body}]",
                                     "carriers", "carrier", tag, "", "", mat, body, c_ri, c_ro, 0.0, 360.0, cz[0], cz[1], [tag], [0.35, 0.4, 0.47]))
                for j, zf in enumerate((f0, f1)):
                    for s_i, s0 in enumerate(e["starts"]):
                        added.append(_sector(f"{tag}_foil{j}_{s_i + 1}", f"node-{T[ty]['node']} / {tag}_foil{j}_{s_i + 1} - interleave plate {k + 1} {cap} foil, r{ri:.1f}-{ro:.1f} [Al foil, {body}]",
                                             f"node-{T[ty]['node']}", "foil", tag, T[ty]["node"], cap, "Al foil", body, ri, ro, s0, e["w_deg"], zf[0], zf[1], [tag], [0.8, 0.8, 0.8]))
                        if t_fac > 0:
                            a0_, a1_ = min(zf), max(zf)
                            if side == "A":
                                fz = (a1_, a1_ + t_fac) if j == 0 else (a0_ - t_fac, a0_)
                            else:
                                fz = (a0_ - t_fac, a0_) if j == 0 else (a1_, a1_ + t_fac)
                            dw = math.degrees(m_fac / max(ri, 1e-9))
                            added.append(_sector(f"{tag}_mica{j}_{s_i + 1}", f"dielectrics / {tag}_mica{j}_{s_i + 1} - {cap} mica facing [mica, {body}]",
                                                 "dielectrics", "dielectric", tag, "", cap, "mica", body, max(0.0, ri - m_fac), ro + m_fac,
                                                 s0 - dw, e["w_deg"] + 2 * dw, fz[0], fz[1], [tag], [0.9, 0.85, 0.6]))
                # the plate's two foils joined through its own carrier (embedded, as the build's ND1 links)
                for s_i, s0 in enumerate(e["starts"]):
                    a = s0 + e["w_deg"] / 2; rr = 0.5 * (ri + ro)
                    # a 1 mm via from foil to foil inside the carrier: its end caps touch the foils' inner faces
                    added.append(_rod(f"VIA{side}_{cap}_{k + 1}_{s_i + 1}", f"node-{T[ty]['node']} / VIA{side}_{cap}_{k + 1}_{s_i + 1} - through-plate via [Cu link, {body}]",
                                      f"node-{T[ty]['node']}", T[ty]["node"], body, _pol(rr, a, cz[0] + sgn * VIA_R), _pol(rr, a, cz[1] - sgn * VIA_R),
                                      VIA_R, [tag]))
                plates[ty].append(dict(foils=[f0, f1], base=False, ri=ri, ro=ro, chains=[tag]))
            plates["out"].append(dict(foils=[(pout["z0"], pout["z1"])], base=True, chains=list(pout.get("chains", []))))
            # inter-plate links: from the first plate's outer foil to the last plate's inner foil of each type
            for ty, how in ((ilink, "inner"), (tlink, "tab")):
                pl = plates[ty]
                if len(pl) < 2:
                    continue
                # end caps (radius LINK_R) touch each end foil from behind its gap face, without poking into a gap:
                # the end point sits LINK_R behind the foil's gap-side face (inside the foil + its carrier)
                fa, fb = pl[0]["foils"][-1], pl[-1]["foils"][0]
                if side == "A":                                  # outward = decreasing z: fa above fb
                    z_a, z_b = min(fa) + LINK_R, max(fb) - LINK_R
                else:
                    z_a, z_b = max(fa) - LINK_R, min(fb) + LINK_R
                e = T[ty]["fp"]; body = T[ty]["body"]
                r = r_li if how == "inner" else r_lo
                for s_i, s0 in enumerate(e["starts"]):
                    a = s0 + e["w_deg"] / 2
                    joins = [f"IL{side}-{cap}-{ty}"] + [c for q in pl for c in q["chains"]]     # joined on purpose
                    nm = f"IL{side}_{cap}_{ty}_link_{s_i + 1}"
                    added.append(_rod(nm, f"node-{T[ty]['node']} / {nm} - interleave link [Cu link, {body}]",
                                      f"node-{T[ty]['node']}", T[ty]["node"], body, _pol(r, a, z_a), _pol(r, a, z_b), LINK_R, joins))
                    added.append(_rod(nm + "_sleeve", f"carriers / {nm}_sleeve - PTFE sleeve on the interleave link, {SLEEVE:g} mm wall [PTFE sleeve, {body}]",
                                      "carriers", "", body, _pol(r, a, z_a), _pol(r, a, z_b), LINK_R + SLEEVE, joins + [nm],
                                      role="sleeve", mat="PTFE sleeve"))
                    if how == "tab":
                        for q, f in ((pl[0], pl[0]["foils"][-1]), (pl[-1], pl[-1]["foils"][0])):
                            ro_f = q.get("ro", e["r_out"])
                            nm = f"IL{side}_{cap}_{ty}_tab_{f[0]:.2f}_{s_i + 1}"
                            added.append(_sector(nm, f"node-{T[ty]['node']} / {nm} - interleave link tab, plate at z {f[0]:.2f} [Al foil, {body}]",
                                                 f"node-{T[ty]['node']}", "foil", "", T[ty]["node"], "", "Al foil", body, ro_f - 2.0, r + LINK_R,
                                                 a - TAB_W / 2, TAB_W, f[0], f[1], [f"IL{side}-{cap}-{ty}"] + q["chains"], [0.8, 0.8, 0.8]))
    d["parts"] = parts + added
    for p in d["parts"]:                                   # the axial shift stretched some parts: volumes anew
        if p["shape"] == "sector":
            p["volume"] = math.pi * (p["r_out"] ** 2 - p["r_in"] ** 2) * (p["w_deg"] / 360.0) * (p["z1"] - p["z0"])
        elif p["shape"] == "rod":
            p["volume"] = math.pi * p["r"] ** 2 * math.dist(p["p0"], p["p1"])
        else:
            p["volume"] = 4.0 / 3.0 * math.pi * p["r"] ** 3
    d["interleave"] = dict(N=N, gaps_per_stack=2 * N - 1, t_mid=T_MID, hv_mm=hv, note="screening build (sim/rt_interleave.py)")
    return d


if __name__ == "__main__":
    src, N, dst = sys.argv[1], int(sys.argv[2]), sys.argv[3]
    d = interleave(json.load(open(src)), N)
    json.dump(d, open(dst, "w"))
    print(dst, len(d["parts"]), "parts")
