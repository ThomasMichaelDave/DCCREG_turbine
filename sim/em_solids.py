#!/usr/bin/env python3
"""sim/em_solids.py -- named solids for the electromagnet register and the clearance / HV gates
(BRIEF_ELECTROMAGNET_REGISTER §3.9, §4, §5.4, §6, §7): G-CLR-HUB, G-CLR-AH, G-CLR-ROT, G-CLR-SG (with the re-clock
search), G-HV-MOTOR, G-HV-POLE, G-MOTOR-SWEEP, against the CAD build (docs/geometry/il2f-6563b90d.json).
Solids are emitted in the stage-2 part schema (shape sector / sphere / rod, body, node, material) so the bill of
solids and the build checks read them unchanged.                                                        [OC/IR]
Usage: python3 sim/em_solids.py -> sim/em_register_results.json ['solids'], docs/geometry/em-register-RA-*.json
"""
import json
import math
import os
import sys

import numpy as np
from matplotlib.path import Path

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path[:0] = [HERE]
import em_register as R                                  # noqa: E402
import rt_buildcheck as BC                               # noqa: E402

BUILD = os.path.join(ROOT, "docs", "geometry", "il2f-6563b90d.json")
OUT_DIR = os.path.join(ROOT, "docs", "geometry")


def ring(name, r_in, r_out, z0, z1, body, material, node="", role="em", **kw):
    return dict(name=name, shape="sector", r_in=float(max(0.0, r_in)), r_out=float(r_out), start_deg=0.0, w_deg=360.0,
                z0=float(min(z0, z1)), z1=float(max(z0, z1)), body=body, material=material, node=node, role=role, **kw)


# ---------------------------------------------------------------------------------------------------------
# RA hub solids (rotor body)
# ---------------------------------------------------------------------------------------------------------
def ra_solids(var):
    import em_ladder as L
    p = L.preset()
    A = L.ra_assembly(var, False, p)
    parts = []
    ves = L.V(p, "vessel")
    hub = L.V(p, "hub_shell")
    rod = L.V(p, "AH_rod")
    fo = L.V(p, "AH_former")
    sh = L.V(p, "shaft")
    sep = L.V(p, "septum")
    var_ = L.V(p, "AH_variants")[var]
    tip = var_["shaft_tip_absz_mm"]
    for s, side, node in ((-1, "A", "R-A"), (+1, "B", "R-B")):
        body = f"rotor {side}"
        zs = sep["half_thickness_mm"]
        parts.append(ring(f"RA_CR_electrode_{side}", 30.0, A.meta["r_electrode_mm"], s * zs, s * (zs + 1.0), body, "Al foil", node, "foil"))
        rpz_o = hub["outer_r_plus_absz_mm"]
        rpz_i = rpz_o - hub["thickness_mm"] * math.sqrt(2)
        for zz in np.arange(zs, 100.0, 2.0):                     # the cone shell as 2 mm stacked rings
            parts.append(ring(f"RA_hub_shell_{side}_{zz:.0f}", rpz_i - zz - 2.0, rpz_o - zz, s * zz, s * (zz + 2.0), body, "garolite"))
        parts.append(ring(f"RA_rod_{side}", 0.0, rod["d_mm"] / 2, s * rod["absz_mm"][0], s * rod["absz_mm"][1], body, "MnZn 77", "join", "core"))
        parts.append(ring(f"RA_former_{side}", fo["id_mm"] / 2, fo["od_mm"] / 2, s * rod["absz_mm"][0], s * rod["absz_mm"][1], body, "G-10"))
        parts.append(ring(f"RA_seat_{side}", 0.0, fo["od_mm"] / 2, s * ves["pole_absz_mm"], s * rod["absz_mm"][0], body, "PEEK"))
        parts.append(ring(f"RA_bore_tube_{side}", 13.5, 15.0, s * 26.0, s * 60.0, body, "garolite"))
        if tip >= rod["absz_mm"][1]:
            parts.append(ring(f"RA_shaft_{side}", 0.0, sh["d_mm"] / 2, s * (tip + 1.0), s * 200.0, body, "steel/316", node, "shaft"))
        else:
            parts.append(ring(f"RA_shaft_tip_{side}", sh["bore_d_mm"] / 2, 10.0, s * tip, s * sh["full_from_absz_mm"], body, "316", node, "shaft"))
            parts.append(ring(f"RA_shaft_{side}", 0.0, sh["d_mm"] / 2, s * max(rod["absz_mm"][1], sh["full_from_absz_mm"]), s * 200.0, body,
                              "steel/316", node, "shaft"))
            parts.append(ring(f"RA_shaft_bore_wall_{side}", sh["bore_d_mm"] / 2, sh["d_mm"] / 2, s * sh["full_from_absz_mm"],
                              s * rod["absz_mm"][1], body, "316", node, "shaft"))
    parts.append(dict(name="RA_vessel", shape="sphere", c=[0.0, 0.0, 0.0], r=ves["od_mm"] / 2, body="rotor AB", material="glass", node="",
                      role="em"))
    for i, t in enumerate(A.turns):
        body = "rotor A" if t["z"] < 0 else "rotor B"
        parts.append(ring(f"RA_{t['w']}_t{i}", t["r"] - t["rc"], t["r"] + t["rc"], t["z"] - t["rc"], t["z"] + t["rc"], body,
                          "Cu capillary" if t["ins"] == "bare" else "Cu enamel", t["w"], "winding"))
    if var_["layers"] % 2 == 0:                                 # the return lead: one axial rod beside the outer layer
        for s, side in ((-1, "A"), (+1, "B")):
            ra_ = fo["od_mm"] / 2 + 1.6 * var_["layers"] + 0.8
            z0 = rod["absz_mm"][0] + (0.65 if var == "a" else 0.3)
            z1 = z0 + var_["turns_per_layer"] * 1.6
            parts.append(dict(name=f"RA_AH_return_lead_{side}", shape="rod", p0=[ra_, 0.0, s * z0], p1=[ra_, 0.0, s * z1], r=0.8,
                              body=f"rotor {side}", material="Cu enamel", node="L_" + ("TA" if s < 0 else "BA"), role="lead"))
    return parts, A


def v15_solids():
    p = R.preset("V15")
    spec = R.val(p, "rotor", "L_R")
    k = np.arange(spec["n"])
    parts = []
    a = spec["od_mm"] / 2
    for s, side in ((-1, "A"), (+1, "B")):
        for kk in k:
            r = spec["r0_mm"] + spec["dr_mm"] * kk
            z = s * (spec["z0_mm"] + spec["dz_mm"] * kk)
            parts.append(ring(f"V15_L_R{1 if s < 0 else 2}_t{kk}", r - a, r + a, z - a, z + a, f"rotor {side}", "Cu capillary",
                              "L_R1" if s < 0 else "L_R2", "winding"))
    return parts


# ---------------------------------------------------------------------------------------------------------
# revolved-image collision / distance between two part lists (rt_buildcheck images)
# ---------------------------------------------------------------------------------------------------------
def clash(parts_a, parts_b, need=0.0, skip=lambda a, b: False):
    """every pair: revolved (r, z) overlap (collision) and distance below `need`."""
    ia = [BC.rz_pts(p) for p in parts_a]
    ib = [BC.rz_pts(p) for p in parts_b]
    ba = [BC.box_of(x) for x in ia]
    bb = [BC.box_of(x) for x in ib]
    coll, near = [], []
    for i, pa in enumerate(parts_a):
        for j, pb in enumerate(parts_b):
            if skip(pa, pb):
                continue
            g = math.hypot(max(0.0, ba[i][0] - bb[j][1], bb[j][0] - ba[i][1]), max(0.0, ba[i][2] - bb[j][3], bb[j][2] - ba[i][3]))
            if g > max(need, 0.0) + 1e-9:
                continue
            d = BC.dist(ia[i], ib[j])
            if d <= 1e-6 and BC.overlap(ia[i], ib[j]):
                coll.append((pa["name"], pb["name"]))
            elif d < need:
                near.append((round(d, 2), pa["name"], pb["name"]))
    near.sort()
    return coll, near


def same_body_overlap(parts_a, parts_b):
    """true overlap between same-body parts: revolved overlap AND angular overlap (both sector ranges)."""
    out = []
    ia = [BC.rz_pts(p) for p in parts_a]
    ib = [BC.rz_pts(p) for p in parts_b]
    for i, pa in enumerate(parts_a):
        for j, pb in enumerate(parts_b):
            if BC.body(pa) != BC.body(pb) and not ("AB" in str(pa.get("body")) or "AB" in str(pb.get("body"))):
                continue
            if not (BC.dist(ia[i], ib[j]) <= 1e-6 and BC.overlap(ia[i], ib[j])):
                continue
            ang = True
            if pa["shape"] == "sector" and pb["shape"] == "sector" and pa["w_deg"] < 360 and pb["w_deg"] < 360:
                a0, a1 = pa["start_deg"] % 360, pa["start_deg"] % 360 + pa["w_deg"]
                b0, b1 = pb["start_deg"] % 360, pb["start_deg"] % 360 + pb["w_deg"]
                ang = any(min(a1, b1 + o) - max(a0, b0 + o) > 1e-6 for o in (-360, 0, 360))
            if ang:
                out.append((pa["name"], pb["name"]))
    return out


def g_clr_hub(log=print):
    d = json.load(open(BUILD))
    build = d["parts"]
    need = d["geom"]["sg_khv"] * max(d["geom"]["sg_s_ret"], d["geom"]["sg_s_load"], d["geom"]["sg_s_fire"], d["geom"]["sg_s_bs"])
    out = {}
    stator = [p for p in build if BC.body(p) == "stator"]
    rotor = [p for p in build if BC.body(p) == "rotor"]
    for gen in ("RA-a", "RA-b", "RA-c", "V15"):
        if gen == "V15":
            parts = v15_solids()
        else:
            parts, A = ra_solids(gen[-1])
            if gen == "RA-a":
                out["RA_dropped_TC_turns"] = A.meta["TC_dropped"]
        coll_s, near_s = clash(parts, stator, need, skip=lambda a, b: not (BC.is_cond(b) or "Cu" in str(a.get("material")))
                               and False)
        cond_near = [x for x in near_s if any(k in x[1] for k in ("foil", "bus", "SG", "counter", "el_", "tab"))]
        coll_r = same_body_overlap(parts, rotor)
        out[gen] = dict(collisions_with_stator=coll_s[:30], n_collisions_with_stator=len(coll_s),
                        interference_with_rotor_parts=coll_r[:30], n_interference_with_rotor=len(coll_r),
                        hv_below_rule_vs_stator=near_s[:15], n_hv_below=len(near_s), need_mm=need,
                        pass_=not coll_s and not coll_r and not near_s)
        log(f"G-CLR-HUB {gen}: {len(coll_s)} counter-rotating collisions, {len(coll_r)} same-body interferences, {len(near_s)} HV"
            f" approaches < {need:.0f} mm; e.g. {(coll_s or coll_r or near_s)[:3]}")
    return out


def g_clr_ah(log=print):
    out = {}
    for var in "abc":
        f = R.ah_fit(var)
        ok = f["axial_margin_mm"] >= 0 and f["radial_margin_at_lead_mm"] >= 0 and (f["peek_sleeve_fits_bore"] in (None, True)) \
            and f["seat_space_mm"] > 0
        out[var] = dict(**f, pass_=bool(ok))
        log(f"G-CLR-AH ({var}): axial {f['axial_margin_mm']:.2f} mm, radial {f['radial_margin_mm']:.2f} (at the lead"
            f" {f['radial_margin_at_lead_mm']:.2f}), PEEK sleeve fits: {f['peek_sleeve_fits_bore']}, seat space {f['seat_space_mm']:.1f} mm"
            f" -> {'PASS' if ok else 'FAIL'}")
    return out


# ---------------------------------------------------------------------------------------------------------
# the motor as a parametric part (§3.9)
# ---------------------------------------------------------------------------------------------------------
OUTER = [(410.48, 19.32), (433.91, 44.55), (487.40, 44.55), (503.50, 25.16)]
INNER = [(410.48, 19.32), (436.63, 19.32), (446.53, 29.98), (471.15, 29.98), (477.50, 25.16)]
R_POLE0 = 424.32


def cem_paths(dr):
    o = [(r + dr, z) for r, z in OUTER]
    i = [(r + dr, z) for r, z in INNER]
    outer = o + [(r, -z) for r, z in o[::-1]]
    window = i + [(r, -z) for r, z in i[::-1]]
    return Path(outer + [outer[0]]), Path(window + [window[0]])


def cem_cloud(theta_deg, dr, w_t, h=1.0):
    """points inside one C-EM core (straight bar extruded tangentially) in the global frame."""
    po, pw = cem_paths(dr)
    rr = np.arange(410.48 + dr, 503.5 + dr + h, h)
    zz = np.arange(-44.55, 44.55 + h, h)
    RR, ZZ = np.meshgrid(rr, zz, indexing="ij")
    P = np.c_[RR.ravel(), ZZ.ravel()]
    inside = po.contains_points(P) & ~pw.contains_points(P)
    P = P[inside]
    ys = np.arange(-w_t / 2, w_t / 2 + h / 2, h)
    th = math.radians(theta_deg)
    pts = []
    for y in ys:
        x = P[:, 0] * math.cos(th) - y * math.sin(th)
        yy = P[:, 0] * math.sin(th) + y * math.cos(th)
        pts.append(np.c_[x, yy, P[:, 1]])
    return np.vstack(pts)


def cem_parts(dr, w_t):
    """the C-EM cores as stage-2 parts (a revolved-image proxy: the section's bounding pieces, angular sectors)."""
    parts = []
    st = R.val(R.preset("RA"), "stator", "cem_stations_deg")
    for lab, th in st.items():
        rm = 0.5 * (410.48 + 503.5) + dr
        wdeg = math.degrees(w_t / rm)
        common = dict(body="stator", material="Si-steel laminated", node="core", role="cem_core", start_deg=th - wdeg / 2, w_deg=wdeg,
                      shape="sector")
        parts.append(dict(name=f"CEM_{lab}_spine", r_in=477.5 + dr, r_out=503.5 + dr, z0=-44.55, z1=44.55, **common))
        parts.append(dict(name=f"CEM_{lab}_arm_top", r_in=433.91 + dr, r_out=503.5 + dr, z0=29.98, z1=44.55, **common))
        parts.append(dict(name=f"CEM_{lab}_arm_bot", r_in=433.91 + dr, r_out=503.5 + dr, z0=-44.55, z1=-29.98, **common))
        parts.append(dict(name=f"CEM_{lab}_jaw_top", r_in=410.48 + dr, r_out=446.53 + dr, z0=19.32, z1=44.55, **common))
        parts.append(dict(name=f"CEM_{lab}_jaw_bot", r_in=410.48 + dr, r_out=446.53 + dr, z0=-44.55, z1=-19.32, **common))
    return parts


def pole_parts(r_pole):
    out = []
    for k in range(6):
        th = math.radians(15 + 60 * k)
        c = [r_pole * math.cos(th), r_pole * math.sin(th)]
        out.append(dict(name=f"POLE_{k + 1}", shape="rod", p0=[c[0], c[1], -17.33], p1=[c[0], c[1], 17.33], r=17.324, body="rotor AB",
                        material="low-carbon iron", node="floating", role="pole"))
    return out


def seg_dist(P, a, b):
    a, b = np.asarray(a, float), np.asarray(b, float)
    ab = b - a
    t = np.clip(((P - a) @ ab) / max(ab @ ab, 1e-12), 0, 1)
    return np.linalg.norm(P - (a + t[:, None] * ab), axis=1)


def item_dist(P, it):
    """P: a cKDTree of cloud points (or an array). Sphere: nearest point - r; rod: the segment sampled at 0.25 mm."""
    from scipy.spatial import cKDTree
    T = P if isinstance(P, cKDTree) else cKDTree(P)
    if it["kind"] == "sphere":
        return float(T.query(np.asarray(it["c"], float))[0] - it["r"])
    a, b = np.asarray(it["p0"], float), np.asarray(it["p1"], float)
    n = max(2, int(np.linalg.norm(b - a) / 0.25) + 1)
    S = a + np.linspace(0, 1, n)[:, None] * (b - a)
    return float(T.query(S)[0].min() - it["r"])


def rot(it, deg):
    th = math.radians(deg)
    c, s = math.cos(th), math.sin(th)
    f = lambda p: [p[0] * c - p[1] * s, p[0] * s + p[1] * c, p[2]]
    out = dict(it)
    for k in ("c", "p0", "p1"):
        if k in it and it[k] is not None:
            out[k] = f(it[k])
    return out


def g_clr_sg(dr, w_t, need, items, clouds=None, h=1.0, deltas=np.arange(-30.0, 30.01, 1.0)):
    """re-clock search: SG1 (stator items SG1_* + rotor tips rotortip_A_*) and SG2 (SG2_* + rotortip_B_*) turned by
    the same angle; stator items vs the 12 C-EMs (same body, 3-D), rotor tips vs the 6 poles (same body, 3-D)."""
    st = R.val(R.preset("RA"), "stator", "cem_stations_deg")
    if clouds is None:
        clouds = {lab: cem_cloud(th, dr, w_t, h) for lab, th in st.items()}
    from scipy.spatial import cKDTree
    allc = cKDTree(np.vstack(list(clouds.values())))
    r_pole = R_POLE0 + dr
    poles = []
    for k in range(6):
        th = math.radians(15 + 60 * k)
        poles.append(dict(kind="rod", p0=[r_pole * math.cos(th), r_pole * math.sin(th), -17.33],
                          p1=[r_pole * math.cos(th), r_pole * math.sin(th), 17.33], r=17.324))
    out = {}
    for gap, tipname in (("SG1", "rotortip_A"), ("SG2", "rotortip_B")):
        st_items = [it for it in items if it["name"].startswith(gap + "_") and it.get("body") == "stator"]
        tips = [it for it in items if it["name"].startswith(tipname)]
        rows = []
        for dlt in deltas:
            ds = min(item_dist(allc, rot(it, dlt)) for it in st_items)
            # rotor tip (sphere + stem) vs the pole cylinders: sample the pole axis densely
            dp = float("inf")
            for it in tips:
                itr = rot(it, dlt)
                for pl in poles:
                    zs = np.linspace(pl["p0"][2], pl["p1"][2], 35)
                    axisP = np.c_[np.full_like(zs, pl["p0"][0]), np.full_like(zs, pl["p0"][1]), zs]
                    if itr["kind"] == "sphere":
                        dd = np.min(np.linalg.norm(axisP - np.asarray(itr["c"]), axis=1)) - itr["r"] - pl["r"]
                    else:
                        dd = np.min(seg_dist(axisP, itr["p0"], itr["p1"])) - itr["r"] - pl["r"]
                    dp = min(dp, float(dd))
            rows.append(dict(delta_deg=float(dlt), d_stator_items_to_CEM_mm=ds, d_rotor_tip_to_pole_mm=dp,
                             feasible=bool(ds >= need and dp >= need)))
        feas = [r["delta_deg"] for r in rows if r["feasible"]]
        r0 = [r for r in rows if abs(r["delta_deg"]) < 1e-9][0]
        out[gap] = dict(at_drawn=r0, feasible_deltas=feas, n_feasible=len(feas), rows=rows)
    return out


def rotor_vs_cem(dr, w_t, build_parts, need):
    """G-CLR-ROT: every rotor part (incl. tips and stems) against the C-EM cores' revolved image; poles vs stator."""
    po, pw = cem_paths(dr)
    rotor = [p for p in build_parts if BC.body(p) == "rotor"]
    coll, near = [], []
    rr = np.arange(400.0 + dr, 506.0 + dr, 0.5)
    zz = np.arange(-45.0, 45.01, 0.5)
    RR, ZZ = np.meshgrid(rr, zz, indexing="ij")
    P = np.c_[RR.ravel(), ZZ.ravel()]
    Pin = P[po.contains_points(P) & ~pw.contains_points(P)]
    for p in rotor:
        img = BC.rz_pts(p)
        pts, inf_, box = img
        if box is not None:
            r0, r1, z0, z1 = box
            if r1 < Pin[:, 0].min() - need or r0 > Pin[:, 0].max() + need or z1 < -45 - need or z0 > 45 + need:
                continue
            dx = np.maximum(0, np.maximum(r0 - Pin[:, 0], Pin[:, 0] - r1))
            dz = np.maximum(0, np.maximum(z0 - Pin[:, 1], Pin[:, 1] - z1))
            d = float(np.min(np.hypot(dx, dz)))
        else:
            d = float(min(np.min(np.hypot(Pin[:, 0] - r, Pin[:, 1] - z)) for r, z in pts) - inf_)
        if d <= 0.25:
            coll.append(p["name"])
        elif d < need and BC.is_cond(p):
            near.append((round(d, 2), p["name"]))
    return coll, sorted(near)


def motor_sweep(log=print):
    d = json.load(open(BUILD))
    build = d["parts"]
    items = d["sparkgaps"]["items"]
    need = d["geom"]["sg_khv"] * max(d["geom"]["sg_s_ret"], d["geom"]["sg_s_load"], d["geom"]["sg_s_fire"], d["geom"]["sg_s_bs"])
    R_frame = d["sparkgaps"]["R_frame"]
    import rt_engine as RT
    cr = RT.counter_rotation(3000.0)
    w_rot = cr["rpm_rotor"] * 2 * math.pi / 60
    rows = []
    rotor_r_out = max(BC.box_of(BC.rz_pts(p))[1] for p in build if BC.body(p) == "rotor")
    for r_pole in (424.32, 450.0, 480.0, 500.0, rotor_r_out + 17.324 + 2.0, 540.0):
        dr = r_pole - R_POLE0
        for w_t in (26.0, 35.0, 44.0):
            coll, near = rotor_vs_cem(dr, w_t, build, need)
            sg = g_clr_sg(dr, w_t, need, items)
            spine_out = math.hypot(503.5 + dr, w_t / 2)
            frame_ok = spine_out + 2.0 <= R_frame
            pole_in = r_pole - 17.324
            host = "poles inside the rotor discs" if r_pole + 17.324 <= rotor_r_out else \
                ("discs must be extended to host the poles" if pole_in > rotor_r_out else "poles straddle the disc rim")
            pole_deg = math.degrees(2 * 17.324 / r_pole)
            jaw_deg = math.degrees(w_t / (423.0 + dr))
            window = 0.5 * (pole_deg + jaw_deg) + math.degrees(2 * 4.0 / r_pole)
            a_al = min(26.15, 34.65) * min(w_t, 34.65)
            depth = (a_al / 4.0) / (26.15 * w_t / 38.64)
            gates = dict(G_CLR_ROT=not coll, G_CLR_SG=sg["SG1"]["n_feasible"] > 0 and sg["SG2"]["n_feasible"] > 0,
                         G_CLR_SG_as_drawn=sg["SG1"]["at_drawn"]["feasible"] and sg["SG2"]["at_drawn"]["feasible"], frame=frame_ok)
            margins = dict(rotor_collisions=len(coll), hv_near=len(near), spine_outer_r=spine_out, R_frame=R_frame,
                           SG1_drawn=sg["SG1"]["at_drawn"], SG2_drawn=sg["SG2"]["at_drawn"])
            binding = [k for k in ("G_CLR_ROT", "frame", "G_CLR_SG") if not gates[k]]
            rows.append(dict(r_pole=r_pole, w_t=w_t, gates=gates, binding=binding or ["none"], margins=margins,
                             rotor_collisions=coll[:12], hv_near=near[:8], SG1_feasible_deltas=sg["SG1"]["feasible_deltas"],
                             SG2_feasible_deltas=sg["SG2"]["feasible_deltas"], host=host,
                             rim_speed_pole_m_s=w_rot * (r_pole + 17.324) * 1e-3, rising_window_deg=window, L_depth_est=depth))
            log(f"  motor r_pole {r_pole:.1f} w_t {w_t:.0f}: rotor collisions {len(coll)} (e.g. {coll[:3]}), SG re-clock feasible"
                f" SG1 {len(sg['SG1']['feasible_deltas'])}/SG2 {len(sg['SG2']['feasible_deltas'])} (as drawn {gates['G_CLR_SG_as_drawn']}),"
                f" spine r {spine_out:.0f} vs frame {R_frame:.0f}; binding {binding}; window {window:.1f} deg, depth ~{depth:.1f}")
    return dict(rows=rows, need_mm=need, rotor_r_out=rotor_r_out)


def hv_motor_pole():
    """G-HV-MOTOR: 2.0 mm air jaw-pole at ~3 kV/mm (freeze gradient; Paschen a little more at 2 mm) against the
    kV-class stator-to-rotor voltage (V_strike 20 kV anchor); G-HV-POLE: 2 x 20 mm surface path foil edge -> pole ->
    foil across the septum against the C_R ring (15 kV)."""
    gap_kV = (6.0, 8.0)
    need_kV = 20.0
    creep = 2 * 20.0
    ring_kV = 15.0
    rule_mm_per_kV = 2.5                                         # [RH] clean insulating surface in air, sustained HV
    return {"G-HV-MOTOR": dict(gap_mm=2.0, withstand_kV=gap_kV, stator_rotor_kV_class=need_kV, pass_=gap_kV[1] >= need_kV,
                               note="the floating pole and the core bonding (D-6) set the real gap voltage; at a 20 kV class"
                                    " difference the 2 mm gap does not hold unless the core is bonded so the difference stays < 6 kV"),
            "G-HV-POLE": dict(creepage_mm=creep, ring_kV=ring_kV, rule_mm_per_kV=rule_mm_per_kV, need_mm=ring_kV * rule_mm_per_kV,
                              pass_=creep >= ring_kV * rule_mm_per_kV, jaw_pole_C_pF=8.854e-12 * 26.15e-3 * 26.15e-3 / 2e-3 * 1e12)}


def export(var, parts, tag):
    path = os.path.join(OUT_DIR, f"em-register-{tag}.json")
    json.dump(dict(schema="em-register-solids/1", generation=tag, variant=var, plan_view_side="unknown",
                   note="electromagnet-register solids (stage-2 part schema); cones as 2 mm stacked rings, turns as square rings",
                   parts=parts), open(path, "w"), indent=0)
    return path


if __name__ == "__main__":
    res = {}
    res["G-CLR-HUB"] = g_clr_hub()
    res["G-CLR-AH"] = g_clr_ah()
    for var in "abc":
        parts, _ = ra_solids(var)
        res.setdefault("exports", []).append(os.path.relpath(export(var, parts, f"RA-{var}"), ROOT))
    res["exports"].append(os.path.relpath(export(None, v15_solids(), "V15"), ROOT))
    res["exports"].append(os.path.relpath(export(None, cem_parts(0.0, 35.0) + pole_parts(R_POLE0), "motor-drawn-w35"), ROOT))
    res["G-MOTOR-SWEEP"] = motor_sweep()
    res.update(hv_motor_pole())
    R.save(dict(solids=res))
    print("->", R.RESULTS)
