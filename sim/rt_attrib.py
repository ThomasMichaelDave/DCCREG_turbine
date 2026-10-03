#!/usr/bin/env python3
"""sim/rt_attrib.py -- stray ownership (design loop step 1): every net is split into its physical parts
(foils by capacitor, bus + links, leads + stems, spheres) and the build is field-solved with each part a
separate conductor. Each net-to-net coupling is then the sum of its part-to-part couplings, so every stray
is attributed to the parts that carry it [ME].

Basis: free space (the machine floats, TMD) unless --can. Usage:
  python3 sim/rt_attrib.py <tag> [theta_geom ...] [--can]   -> docs/geometry/rt/<tag>.attrib.json
"""
import json
import os
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path[:0] = [HERE, os.path.join(ROOT, "reference")]
import numpy as np                       # noqa: E402
import round_trip as RTP                 # noqa: E402

CLASS = {"bus": "bus", "link": "bus", "gap-lead": "lead", "gap-stem": "lead", "gap-stator": "sph", "gap-rotor": "sph"}


def part_class(p):
    if p.get("role") == "foil":
        return "foil-" + str(p.get("cap") or "?")
    return CLASS.get(p.get("role"), p.get("role") or "?")


def split(design):
    d = json.loads(json.dumps(design))
    for p in d["parts"]:
        if p.get("node"):
            p["node"] = f"{p['node']}|{part_class(p)}"
    return d


def net_of(sub):
    n = sub.split("|")[0]
    return RTP.MERGE.get(n, n)


def attribute(sol):
    """one split solve -> {(netA, netB): {(subA, subB): pF}}, 'inf' for the reference (free space or can)."""
    names = sol["names"]
    C = np.array(sol["C"])
    out = {}
    for i, a in enumerate(names):
        ra = float(C[i].sum())                                     # to the reference
        out.setdefault((net_of(a), "inf"), {})[(a, "inf")] = ra
        for j in range(i + 1, len(names)):
            b = names[j]
            na, nb = net_of(a), net_of(b)
            if na == nb:
                continue
            key = tuple(sorted((na, nb)))
            sub = (a, b) if (na, nb) == key else (b, a)
            out.setdefault(key, {})[sub] = float(-C[i, j])
    return out


def run(tag, thetas=(0.0, 30.0), enclosure=None, log=print):
    design = json.load(open(os.path.join(ROOT, "docs", "geometry", "rt", f"{tag}.design.json")))
    d = split(design)
    path = os.path.join(ROOT, "docs", "geometry", "rt", f"{tag}.attrib{'' if enclosure is None else '-can'}.json")
    rec = json.load(open(path)) if os.path.exists(path) else {}
    for t in thetas:
        k = f"{t:g}"
        if k in rec:
            continue
        t0 = time.time()
        sol = RTP.solve_theta(d, t, "c", enclosure=enclosure)
        att = attribute(sol)
        rec[k] = {"|".join(key): {" / ".join(s): v for s, v in sorted(parts.items(), key=lambda kv: -abs(kv[1]))}
                  for key, parts in att.items()}
        rec[k + "_info"] = dict(cells=sol["info"]["cells"], conductors=len(sol["names"]), t_s=time.time() - t0)
        log(f"{tag} theta {t:g}: {len(sol['names'])} conductors, {sol['info']['cells']} cells, {time.time() - t0:.0f} s")
        json.dump(rec, open(path, "w"), indent=1)
    return rec


if __name__ == "__main__":
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    tag = args[0] if args else "freeze-t15-free"
    th = tuple(float(x) for x in args[1:]) or (0.0, 30.0)
    run(tag, th, enclosure=50.0 if "--can" in sys.argv else None)
