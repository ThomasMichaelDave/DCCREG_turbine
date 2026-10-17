"""rebuild/s2_models/s2_fv.py -- S2b-1: the S2a model for the field solve (rebuild/s2_models/s2b-plan.md §2, §4).

The record's finite-volume solver (sim/tube_strays.py, imported, not edited) needs each part as an analytic test
inside(x, y, z). The S2a model (rebuild/s2_models/s2_geometry.py) builds OpenCascade solids from a few primitives
(sim/tube_geometry.py: sector, cyl_z, cyl_between, wire, box, prism, sphere, capsule_y, arc_capsule, fuse, _cut; the
hub's band, torus and common). Here every primitive is shadowed: the same build runs with each call returning an Sh,
a constructive-solid tree whose leaves are the primitives' exact inside tests [OC: the primitives' definitions]. No
OpenCascade solid is built on that path. Then:
- each part's role from its net and material: a conductor on its net; a graded conductor (a diode stick or a clamp
  half, its potential linear from one net to the other along its axis or arc) cut into slices; a dielectric with its
  eps_r; or air;
- the vanes and plates take the record's full-round edges, radius half the thickness (sim/tube_strays.py Vane) in
  place of the square edges the model draws [IR: the record states the rounds]; their tabs, lugs and holes stay the
  model's;
- the HV wire is its 1 mm copper core (the conductor) in its 3 mm PTFE (a dielectric).
Gates (python3 rebuild/s2_models/s2_fv.py):
- G-GEOM: every prototype's shadow against OpenCascade's own solid (BRepClass3d_SolidClassifier) on random points in
  its box: they may disagree only within 0.05 mm of the solid's surface; every net of the parts list present;
- G-PLACE: a placed part's shadow against its placed solid, for a sample of rotated and lifted parts.
Writes rebuild/s2_models/s2_fv_results.json.
Tags: [OC] derivable; [IR] a modelling choice; [RH] a heuristic (CONVENTIONS.md §1).
"""
import json
import math
import os
import sys
import time

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, os.path.join(ROOT, "sim"))
sys.path.insert(0, HERE)
import tube_geometry as TG  # noqa: E402

EPS = 1e-9
# eps_r per material, by a keyword of the model's material string [IR: datasheet classes; the hub's from its preset]
_H = json.load(open(os.path.join(ROOT, "presets", "hub-locked.json")))
EPS_R = [("borosilicate", _H["vessel"]["value"]["eps_r"]), ("silicone gel", _H["interface_filler"]["value"]["eps_r"]),
         ("PEEK", _H["retainer"]["value"]["eps_r"]), ("G10", 4.7), ("PTFE", 2.1), ("steatite", 6.0), ("mica", 6.5),
         ("silicone potting", 2.8)]
GRADED_SLICES = 4                     # a graded part cut into this many slices [IR]
WIRE_CORE = 0.5                       # mm: the HV wire's copper (TG: "1 mm Cu in 3 mm PTFE")


# ============================================================================================== the shadow solids
class Sh:
    """a solid as an inside test on Cartesian points (arrays, mm) and its box (lo, hi)."""

    def __init__(self, f, lo, hi, what=""):
        self.f, self.lo, self.hi, self.what = f, np.asarray(lo, float), np.asarray(hi, float), what

    def inside(self, X, Y, Z):
        X, Y, Z = np.asarray(X, float), np.asarray(Y, float), np.asarray(Z, float)
        out = np.zeros(np.shape(X), dtype=bool)
        m = (X >= self.lo[0] - 1e-6) & (X <= self.hi[0] + 1e-6) & (Y >= self.lo[1] - 1e-6) & (Y <= self.hi[1] + 1e-6) & \
            (Z >= self.lo[2] - 1e-6) & (Z <= self.hi[2] + 1e-6)
        if m.any():
            out[m] = self.f(X[m], Y[m], Z[m])
        return out

    def Shape(self):                   # OCC's builders' API, for the hub's BRepAlgoAPI calls
        return self


def _ang_in(X, Y, a0, w):
    """the angle of (X, Y) within [a0, a0 + w] degrees."""
    a = np.degrees(np.arctan2(Y, X))
    return np.mod(a - a0, 360.0) <= w + 1e-9


def sector(r0, r1, z0, z1, a0_deg=0.0, w_deg=360.0):
    full = w_deg >= 360.0 - 1e-9

    def f(X, Y, Z):
        R = np.hypot(X, Y)
        m = (R >= r0 - EPS) & (R <= r1 + EPS) & (Z >= z0 - EPS) & (Z <= z1 + EPS)
        return m if full else m & _ang_in(X, Y, a0_deg, w_deg)
    return Sh(f, (-r1, -r1, z0), (r1, r1, z1), "sector")


def sphere(r, c):
    c = np.asarray(c, float)
    return Sh(lambda X, Y, Z: (X - c[0]) ** 2 + (Y - c[1]) ** 2 + (Z - c[2]) ** 2 <= r * r + EPS, c - r, c + r, "sphere")


def box(x0, x1, y0, y1, z0, z1):
    return Sh(lambda X, Y, Z: (X >= x0 - EPS) & (X <= x1 + EPS) & (Y >= y0 - EPS) & (Y <= y1 + EPS) & (Z >= z0 - EPS)
              & (Z <= z1 + EPS), (x0, y0, z0), (x1, y1, z1), "box")


def cyl_z(x, y, r, z0, z1):
    return Sh(lambda X, Y, Z: ((X - x) ** 2 + (Y - y) ** 2 <= r * r + EPS) & (Z >= z0 - EPS) & (Z <= z1 + EPS),
              (x - r, y - r, z0), (x + r, y + r, z1), "cyl_z")


def cyl_between(p0, p1, r):
    a, b = np.asarray(p0, float), np.asarray(p1, float)
    v = b - a
    L = float(np.linalg.norm(v))
    u = v / L

    def f(X, Y, Z):
        dx, dy, dz = X - a[0], Y - a[1], Z - a[2]
        s = dx * u[0] + dy * u[1] + dz * u[2]
        d2 = dx * dx + dy * dy + dz * dz - s * s
        return (s >= -EPS) & (s <= L + EPS) & (d2 <= r * r + EPS)
    ext = r * np.sqrt(np.maximum(0.0, 1.0 - u * u))
    return Sh(f, np.minimum(a, b) - ext, np.maximum(a, b) + ext, "cyl_between")


def prism(poly, z0, z1):
    P = np.asarray(poly, float)

    def f(X, Y, Z):
        ins = np.zeros(np.shape(X), dtype=bool)
        for (xa, ya), (xb, yb) in zip(P, np.roll(P, -1, axis=0)):          # even-odd rule [OC]
            c = ((ya > Y) != (yb > Y))
            with np.errstate(divide="ignore", invalid="ignore"):
                xi = xa + (Y - ya) * (xb - xa) / (yb - ya)
            ins ^= c & (X < xi)
        return ins & (Z >= z0 - EPS) & (Z <= z1 + EPS)
    return Sh(f, (P[:, 0].min(), P[:, 1].min(), z0), (P[:, 0].max(), P[:, 1].max(), z1), "prism")


def fuse(shapes):
    shapes = list(shapes)
    return Sh(lambda X, Y, Z: np.logical_or.reduce([s.inside(X, Y, Z) for s in shapes]),
              np.min([s.lo for s in shapes], axis=0), np.max([s.hi for s in shapes], axis=0), "fuse")


def _cut(a, *bs):
    if not bs:
        return a
    return Sh(lambda X, Y, Z: a.inside(X, Y, Z) & ~np.logical_or.reduce([b.inside(X, Y, Z) for b in bs]), a.lo, a.hi, "cut")


def common(a, b):
    return Sh(lambda X, Y, Z: a.inside(X, Y, Z) & b.inside(X, Y, Z), np.maximum(a.lo, b.lo), np.minimum(a.hi, b.hi), "common")


def wire(points, r):
    pts = [np.asarray(p, float) for p in points]
    keep = [pts[0]] + [q for p_, q in zip(pts[:-1], pts[1:]) if np.linalg.norm(q - p_) > 1e-6]
    parts = [cyl_between(a, b, r) for a, b in zip(keep[:-1], keep[1:])] + [sphere(r, q) for q in keep[1:-1]]
    return fuse(parts) if len(parts) > 1 else parts[0]


def capsule_y(rad, half):
    return fuse([cyl_between((0, -half, 0), (0, half, 0), rad), sphere(rad, (0, -half, 0)), sphere(rad, (0, half, 0))])


def arc_capsule(r, span_deg, rad, z0, z1):
    t = math.radians(span_deg)
    return fuse([sector(r - rad, r + rad, z0, z1, 0.0, span_deg), cyl_z(r, 0.0, rad, z0, z1),
                 cyl_z(r * math.cos(t), r * math.sin(t), rad, z0, z1)])


def torus(z0, R, rho):
    return Sh(lambda X, Y, Z: (np.hypot(X, Y) - R) ** 2 + (Z - z0) ** 2 <= rho * rho + EPS,
              (-R - rho, -R - rho, z0 - rho), (R + rho, R + rho, z0 + rho), "torus")


def bbox(s):
    return s.lo, s.hi


# the hub's OCC calls (sim/tube_geometry.py Machine.locked_hub imports them inside the function)
class _Cut(Sh):
    def __init__(self, a, b):
        s = _cut(a, b)
        super().__init__(s.f, s.lo, s.hi, "cut")


class _Common(Sh):
    def __init__(self, a, b):
        s = common(a, b)
        super().__init__(s.f, s.lo, s.hi, "common")


class _Torus(Sh):
    def __init__(self, ax, R, rho):
        s = torus(ax.Location().Z(), R, rho)
        super().__init__(s.f, s.lo, s.hi, "torus")


def shadow_core():
    """S2Core built with every primitive shadowed: its protos hold Sh, its parts and nets as the model's."""
    import OCP.BRepAlgoAPI as BA
    import OCP.BRepPrimAPI as BP
    import s2_geometry as G
    names = dict(sector=sector, sphere=sphere, box=box, cyl_z=cyl_z, cyl_between=cyl_between, prism=prism, fuse=fuse,
                 _cut=_cut, wire=wire, capsule_y=capsule_y, arc_capsule=arc_capsule, bbox=bbox)
    saved = {k: getattr(TG, k) for k in names}
    saved_oc = (BA.BRepAlgoAPI_Cut, BA.BRepAlgoAPI_Common, BP.BRepPrimAPI_MakeTorus)
    try:
        for k, v in names.items():
            setattr(TG, k, v)
        BA.BRepAlgoAPI_Cut, BA.BRepAlgoAPI_Common, BP.BRepPrimAPI_MakeTorus = _Cut, _Common, _Torus
        m = G.S2Core().build()
    finally:
        for k, v in saved.items():
            setattr(TG, k, v)
        BA.BRepAlgoAPI_Cut, BA.BRepAlgoAPI_Common, BP.BRepPrimAPI_MakeTorus = saved_oc
    return m


def placed(sh, pl):
    """a prototype's shadow at its place: TG.Machine.trsf, p' = Rz(rot) (p + dx x) + dz z, inverted [OC]."""
    dx, dz, rot = pl["dx"], pl["dz"], pl["rot"]
    if abs(dx) < 1e-12 and abs(dz) < 1e-12 and abs(rot) < 1e-12:
        return sh
    c, s = math.cos(math.radians(rot)), math.sin(math.radians(rot))

    def f(X, Y, Z):
        x = c * X + s * Y - dx
        y = -s * X + c * Y
        return sh.inside(x, y, Z - dz)
    # the box: the prototype's box corners moved, then bounded
    lo, hi = sh.lo, sh.hi
    cr = np.array([[x, y] for x in (lo[0] + dx, hi[0] + dx) for y in (lo[1], hi[1])])
    xy = cr @ np.array([[c, s], [-s, c]])
    return Sh(f, (xy[:, 0].min(), xy[:, 1].min(), lo[2] + dz), (xy[:, 0].max(), xy[:, 1].max(), hi[2] + dz), "placed")


# ============================================================================================== the parts' roles
VANE_PROTOS = ("rotor_vane", "rotor_vane_end", "stator_vane", "stator_vane_end")


def eps_of(material):
    for k, e in EPS_R:
        if k.lower() in material.lower():
            return e
    return None


def rounded(m, proto, sh):
    """a vane or plate with the record's full-round edges (sim/tube_strays.py Vane) over its active band r_in-r_out,
    the model's own solid elsewhere (tabs, lugs, the rings' inner and outer parts, holes) [IR]."""
    import s2_geometry as G
    import tube_strays as TS
    t = float(sh.hi[2] - sh.lo[2])
    ri, ro = G.VANE["r_in"], G.VANE["r_out"]
    if proto.startswith("rotor_vane"):
        v = TS.Vane("rotor", 0.0, t, 0.0, 0.5 * G.VANE["wr"], ri, ro, G.SLEEVE_OUT, G.STATOR_RING[1])
    elif proto.startswith("stator_vane"):
        v = TS.Vane("stator", 0.0, t, 0.0, 0.5 * G.VANE["ws"], ri, ro, G.SLEEVE_OUT, G.STATOR_RING[1])
    else:
        v = TS.Vane("plate", 0.0, t, r_in=ri, r_out=ro)

    def f(X, Y, Z):
        R = np.hypot(X, Y)
        band = (R >= ri - 1e-6) & (R <= ro + 1e-6)
        own = sh.inside(X, Y, Z) & ~band
        rv = v.inside(R, np.arctan2(Y, X), Z) & band
        return own | rv
    return Sh(f, sh.lo, sh.hi, "rounded " + proto)


def roles(m):
    """per part: dict(name, kind 'cond' | 'graded' | 'diel' | 'air', net or nets, eps, sh (placed), slices)."""
    out = []
    REF = {"0": "REF", "s": "REF"}
    for p in m.parts:
        sh0, mat = m.protos[p["proto"]][0], m.protos[p["proto"]][2]
        if p["proto"] in VANE_PROTOS or p["proto"].startswith("ca_n"):
            sh0 = rounded(m, p["proto"], sh0)
        sh = placed(sh0, p["place"])
        nt = m.nets.get(p["name"], {})
        row = dict(name=p["name"], proto=p["proto"], group=p["group"], material=mat, sh=sh)
        if "nets" in nt:
            row.update(kind="graded", nets=[REF.get(x, x) for x in nt["nets"]], axis=nt.get("axis"), arc=nt.get("arc"))
        elif "net" in nt:
            net = REF.get(nt["net"], nt["net"])
            if "PTFE HV wire" in mat:
                core = wire([placed_pt(q, p["place"]) for q in nt["path"]], WIRE_CORE)
                out.append(dict(row, name=p["name"] + "_core", kind="cond", net=net, sh=core))
                row.update(kind="diel", eps=eps_of("PTFE"))
            else:
                row.update(kind="cond", net=net)
        else:
            e = eps_of(mat)
            row.update(kind="diel" if e else "air", eps=e)
        out.append(row)
    return out


def placed_pt(q, pl):
    c, s = math.cos(math.radians(pl["rot"])), math.sin(math.radians(pl["rot"]))
    x, y, z = q[0] + pl["dx"], q[1], q[2]
    return (c * x - s * y, s * x + c * y, z + pl["dz"])


# ============================================================================================== the gates
def _occ_inside(shape, P, tol=1e-6):
    from OCP.BRepClass3d import BRepClass3d_SolidClassifier
    from OCP.TopAbs import TopAbs_IN, TopAbs_ON
    from OCP.gp import gp_Pnt
    cl = BRepClass3d_SolidClassifier(shape)
    out = np.zeros(len(P), dtype=bool)
    for i, (x, y, z) in enumerate(P):
        cl.Perform(gp_Pnt(float(x), float(y), float(z)), tol)
        out[i] = cl.State() in (TopAbs_IN, TopAbs_ON)
    return out


def _surface_dist(shape, P):
    from OCP.BRepBuilderAPI import BRepBuilderAPI_MakeVertex
    from OCP.BRepExtrema import BRepExtrema_DistShapeShape
    from OCP.gp import gp_Pnt
    d = []
    for x, y, z in P:
        v = BRepBuilderAPI_MakeVertex(gp_Pnt(float(x), float(y), float(z))).Vertex()
        e = BRepExtrema_DistShapeShape(v, shape)
        d.append(e.Value() if e.IsDone() else 0.0)
    return np.array(d)


def gate_geom(m_occ, m_sh, n=2000, tol=0.05, seed=1, log=print):
    """every prototype: the shadow's inside test (square-edged, as the model draws it) against OCC's classifier."""
    from OCP.BRepGProp import BRepGProp
    from OCP.GProp import GProp_GProps
    rng = np.random.default_rng(seed)
    rows, bad = {}, []
    for key, (shp, _, mat) in m_occ.protos.items():
        sh = m_sh.protos[key][0]
        lo, hi = sh.lo - 0.5, sh.hi + 0.5
        P = lo + (hi - lo) * rng.random((n, 3))
        a = sh.inside(P[:, 0], P[:, 1], P[:, 2])
        b = _occ_inside(shp, P)
        dis = np.nonzero(a != b)[0]
        far = []
        if len(dis):
            dd = _surface_dist(shp, P[dis])
            far = [int(i) for i, x in zip(dis, dd) if x > tol]
        g = GProp_GProps(); BRepGProp.VolumeProperties_s(shp, g)
        rows[key] = dict(points=n, inside_occ=int(b.sum()), disagree=int(len(dis)), disagree_far=len(far),
                         volume_occ_mm3=float(g.Mass()), material=mat)
        if far:
            bad.append(key)
            log(f"  G-GEOM {key}: {len(far)} of {n} points disagree beyond {tol} mm (e.g. {P[far[0]].round(2).tolist()})")
    return dict(prototypes=len(rows), failed=bad, pass_=not bad, tol_mm=tol, rows=rows)


def gate_place(m_occ, m_sh, k=12, n=1500, tol=0.05, seed=2, log=print):
    """placed parts (rotated, lifted) against their placed OCC solids."""
    rng = np.random.default_rng(seed)
    cand = [p for p in m_occ.parts if abs(p["place"]["rot"]) > 1e-6 or abs(p["place"]["dz"]) > 1e-6]
    pick = [cand[i] for i in rng.choice(len(cand), size=min(k, len(cand)), replace=False)]
    rows, bad = {}, []
    for p in pick:
        shp = m_occ.placed(p)
        sh = placed(m_sh.protos[p["proto"]][0], p["place"])
        lo, hi = sh.lo - 0.5, sh.hi + 0.5
        P = lo + (hi - lo) * rng.random((n, 3))
        a, b = sh.inside(*P.T), _occ_inside(shp, P)
        dis = np.nonzero(a != b)[0]
        far = [int(i) for i, x in zip(dis, _surface_dist(shp, P[dis]))if x > tol] if len(dis) else []
        rows[p["name"]] = dict(place=p["place"], inside=int(b.sum()), disagree=int(len(dis)), disagree_far=len(far))
        if far:
            bad.append(p["name"])
    return dict(parts=len(rows), failed=bad, pass_=not bad, rows=rows)


def net_presence(m_sh, rl):
    """every net of the model carried by at least one conductor (or a graded part's end)."""
    have = {r["net"] for r in rl if r["kind"] == "cond"} | {x for r in rl if r["kind"] == "graded" for x in r["nets"]}
    want = {("REF" if v.get("net") in ("0", "s") else v.get("net")) for v in m_sh.nets.values() if "net" in v}
    want |= {("REF" if x in ("0", "s") else x) for v in m_sh.nets.values() for x in v.get("nets", [])}
    return dict(nets=sorted(have), missing=sorted(want - have), pass_=not (want - have))


def main():
    import s2_geometry as G
    t0 = time.time()
    m_sh = shadow_core()
    print(f"shadow model: {len(m_sh.parts)} parts, {len(m_sh.protos)} prototypes ({time.time() - t0:.0f} s)", flush=True)
    rl = roles(m_sh)
    kinds = {}
    for r in rl:
        kinds[r["kind"]] = kinds.get(r["kind"], 0) + 1
    print("roles:", kinds)
    t0 = time.time()
    m_occ = G.S2Core().build()
    print(f"OCC model built ({time.time() - t0:.0f} s)", flush=True)
    t0 = time.time()
    gg = gate_geom(m_occ, m_sh)
    print(f"G-GEOM: {gg['prototypes']} prototypes, failed {gg['failed']} ({time.time() - t0:.0f} s)", flush=True)
    # the thin parts (foils, rings, leads) that few random points land in: again with ten times the points
    thin = [k for k, v in gg["rows"].items() if v["inside_occ"] < 30]

    class _Sub:
        pass
    a_, b_ = _Sub(), _Sub()
    a_.protos, b_.protos = {k: m_occ.protos[k] for k in thin}, {k: m_sh.protos[k] for k in thin}
    gt = gate_geom(a_, b_, n=20000, seed=7)
    gg["thin"] = dict(points=20000, rows=gt["rows"], failed=gt["failed"], pass_=gt["pass_"])
    gg["pass_"] = gg["pass_"] and gt["pass_"]
    print(f"G-GEOM, the thin parts again at 20000 points: {thin}, failed {gt['failed']}", flush=True)
    gp = gate_place(m_occ, m_sh)
    print(f"G-PLACE: {gp['parts']} parts, failed {gp['failed']}")
    nets = net_presence(m_sh, rl)
    print("nets:", nets)
    out = dict(note="S2b-1: the S2a model's parts as analytic inside tests for the field solve (s2b-plan.md)",
               eps_r=dict(EPS_R), graded_slices=GRADED_SLICES, wire_core_mm=WIRE_CORE, roles=kinds,
               parts=[{k: v for k, v in r.items() if k != "sh"} for r in rl],
               G_GEOM=gg, G_PLACE=gp, nets=nets)
    json.dump(out, open(os.path.join(HERE, "s2_fv_results.json"), "w"), indent=1, default=float)


if __name__ == "__main__":
    main()
