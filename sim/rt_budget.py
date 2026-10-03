#!/usr/bin/env python3
"""sim/rt_budget.py -- the stray budget (design loop step 0): what each stray group must come down to for
z >= 1 + m, engine only, on a field-solved C(theta) [ME].

Groups (scaled on the reduced profiles, merged nets):
  C1  1|R-A, 4|R-B   floor scaled by f, swing kept:  C - (1 - f) min C
  Cx  7|n17, 8|n23   floor scaled by f, swing kept
  X   every other node-node coupling (not the ladder's)   x f
  E   every node's coupling to the reference (the can, or infinity in free space)   x f [GROUND]
  Ca  1|2, 3|4   x f
Usage: python3 sim/rt_budget.py [tag ...]   (default freeze-t15 freeze-t15-free) -> sim/rt_budget.json
"""
import itertools
import json
import os
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path[:0] = [HERE, os.path.join(ROOT, "reference")]
import numpy as np                       # noqa: E402
import round_trip as RTP                 # noqa: E402

E_MIN = 0.02                             # E is never scaled below this: an isolated node makes C singular [ME]
LADDER = {RTP._key(*ab) for ab in RTP.VARICAP_KEYS.values()}
FLOOR = {"C1": [RTP._key("1", "R-A"), RTP._key("4", "R-B")], "Cx": [RTP._key("7", "n17"), RTP._key("8", "n23")]}
CA = [RTP._key("1", "2"), RTP._key("3", "4")]


def scaled(prof, f):
    """prof with the group factors f = {group: factor} applied."""
    p = {k: np.array(v, float) for k, v in prof.items()}
    for g in ("C1", "Cx"):
        if g in f:
            for k in FLOOR[g]:
                p[k] = p[k] - (1.0 - f[g]) * p[k].min()
    if "Ca" in f:
        for k in CA:
            p[k] = p[k] * f["Ca"]
    for k in p:
        if k in LADDER:
            continue
        if "enc" in k and "E" in f:
            p[k] = p[k] * max(f["E"], E_MIN)
        elif "enc" not in k and "X" in f:
            p[k] = p[k] * f["X"]
    return p


def z_of(thetas, prof, f, ref=None):
    import pump_synth as SY
    import rt_engine as RT
    cfg = SY.engine_cfg(*SY.sized({}))
    cm = RTP.CModel(thetas, scaled(prof, f), tip_deg=RTP.RT_GEOM["sg_tip_deg"])
    kw = dict(cmodel=cm) if ref is None else dict(cmodel=cm, ref=ref)
    m = RT.run(RT.build_net(cfg, **kw), cfg)
    return float(m["z"]), bool(m["converged"])


def budget(tag, log=print):
    th, pr = RTP.profiles_of(tag)
    rows = []

    def run(name, f, ref=None):
        t0 = time.time()
        try:
            z, c = z_of(th, pr, f, ref)
        except np.linalg.LinAlgError:
            z, c = float("nan"), False
        rows.append(dict(name=name, f=f, ref=ref, z=z, converged=c))
        log(f"{tag:18s} {name:34s} z {z:.4f} {'conv' if c else '----'} ({time.time() - t0:.0f} s)")
    run("base", {})
    run("base, ref R-A", {}, ref="R-A")
    for g in ("C1", "Cx", "X", "E"):
        for v in (0.5, 0.25, 0.1, 0.0):
            run(f"{g} x{v:g}", {g: v})
    for v in (0.5, 2.0, 3.0):
        run(f"Ca x{v:g}", {"Ca": v})
    lv = (1.0, 0.5, 0.25, 0.1)
    for a, b, c in itertools.product(lv, lv, lv):
        if (a, b, c).count(1.0) >= 2:
            continue
        run(f"C1 x{a:g} E x{b:g} X x{c:g}", {"C1": a, "E": b, "X": c})
    for a, b, c in itertools.product((0.25, 0.1), (0.25, 0.1), (0.25, 0.1)):
        run(f"C1 x{a:g} E x{b:g} X x{c:g} Cx x0.1", {"C1": a, "E": b, "X": c, "Cx": 0.1})
    return rows


def main():
    tags = sys.argv[1:] or ["freeze-t15", "freeze-t15-free"]
    path = os.path.join(HERE, "rt_budget.json")
    out = json.load(open(path)) if os.path.exists(path) else {}
    for t in tags:
        out[t] = budget(t)
        json.dump(out, open(path, "w"), indent=1)


if __name__ == "__main__":
    main()
