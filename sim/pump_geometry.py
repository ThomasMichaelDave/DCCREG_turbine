#!/usr/bin/env python3
"""
sim/pump_geometry.py — PUMP-SYNTH stage 2: a LOCKED stage-1 design -> capacitor plate geometry
==============================================================================================
Stage 1 (sim/pump_sizing.py + the exact engine) fixes the capacitances. Stage 2 turns them into plates:
electrode footprints (annular sectors on named carrier discs), dielectric slabs and an axial stack that a
3-D package can check for geometric feasibility. Mirrored 1:1 in JS (tools/pump-geometry.js, gate G-JS);
the FreeCAD macro tools/pump-geometry.FCMacro builds the 3-D model from this module's JSON (gate G-CAD).

First cut (TMD, 2026-10-01): **Ca / Cb are geometrized**; every other electrode is placed as LOCKED CONTEXT
from the r0.15 DXF part views (radii, 30-degree sector sets) so the plate distribution is complete.

Seed, read off docs/varcap-nodeanalysis-template-r0.15_TMD_layout.dxf (the "Ca electrodes", "Cb electrodes"
and "stack section (assembly)" frames) and docs/varcap-design-freeze-v0.10.md §3 [OC]:
  ND1 C1 stator plate   r95-387, odd sectors (30-60, 90-120, ...)      ND4 C2 stator  r95-387, even sectors
  ND9/ND10 rotor faces  r75-387, odd sectors                           (C1 / C2 rotor faces, nodes 5 / 6)
  ND2 Ca electrode      r110-175, odd sectors  (faces ND1 through 4.5 mm mica)
  ND3 Cb electrode      r110-175, even sectors (faces ND4 through 4.5 mm mica)
  ND2 Cx4 pickup        r58-350, even sectors   ND8 island bars (on A) r75-350, even sectors
  ND3 Cx3 pickup        r58-350, odd sectors    ND7 island bars (on B) r75-350, odd sectors
  6 x 30 deg of r110-175 = 0.029099 m^2 -> 309.18 pF on 4.5 mm mica (eps_r 5.4): the DXF and the freeze agree.

Axial stack (NOT in the DXF -- its "stack section" frame is a plan overlay). Seeded with the one order in which
every capacitor's two electrodes face each other across exactly its own dielectric [IR, confirm in CAD]:
each rotor half is a clamshell around its stator pair --
  A flange (ND8 bars) | Cx4 gap | ND2 carrier | Ca mica | ND1 carrier | C1 air | A disc (ND9) | septum (C_R) |
  B disc (ND10) | C2 air | ND4 carrier | Cb mica | ND3 carrier | Cx3 gap | B flange (ND7 bars)
Stator "plates" are insulating carriers with foil electrodes on their faces (both faces of ND2/ND3 carry
different electrodes of the same node in complementary sectors, so a solid metal plate would not realize the
drawn areas) [IR]. Thicknesses of carriers / foils are placeholders [IR]; the gaps are the stage-1 / freeze
values [OC]. adjacency() checks the stack (gate G-ADJ).

Model of each capacitor: ideal parallel plate over the overlap of its two footprints, C = eps0 eps_r A / t
(no fringing: [OC] law, fringing out of scope as in Block C-I). Tags [OC]/[IR]/[RH]/[ME]. No file I/O on import.
"""
import hashlib
import json
import math

EPS0 = 8.8541878128e-12
SCHEMA = "pump-geometry/1"
DIELECTRICS = {"mica": 5.4, "mylar": 3.2, "kapton": 3.4, "pp_film": 2.2, "garolite": 4.7, "air": 1.0006}
ODD = [30.0 + 60.0 * k for k in range(6)]     # sector start angles (deg), 30-degree sectors [OC DXF]
EVEN = [60.0 * k for k in range(6)]

GEOM_DEFAULTS = dict(
    # Ca / Cb (the geometrized pair) -- DXF / freeze seed
    ca_diel="mica", ca_t=4.5,                 # dielectric and its thickness (mm)            [OC freeze]
    ca_w=30.0,                                # sector width (deg); the sector COUNT is the locked n_kept
                                              # (Ca/Cb sit in their counter-plate's kept sectors) [OC DXF]
    ca_mode="r_out",                          # solve: 'r_out' (r_in pinned) | 'r_in' (r_out pinned) | 'width' | 'forward'
    ca_rin=110.0, ca_rout=175.0,              # mm (the pinned one is used; the other is solved) [OC DXF]
    ca_round=0.0,                             # manufacturing step on the solved dimension (mm or deg; 0 = exact)
    ca_margin=5.0,                            # dielectric overlap margin around the foil (mm, radial and arc) [IR]
    # stack placeholders [IR]
    t_foil=1.0, t_carrier=3.0, t_rotor=10.0, t_flange=6.0, t_septum=12.0,
    cx_air=3.0, cx_mica=0.3,                  # Cx gap: air + mica per face (freeze v0.10) [OC]
    r_bore=50.0,                              # stator carrier bore (mm), clears the hub/coil r28-76 bicone [IR]
    rotor_in_off=20.0,                        # rotor face r_in = active r_in - 20 (DXF 75 vs 95) [IR]
)


def _round(x, step):
    """Manufacturing step, half-up (identical in the JS mirror; Python's round() is half-even)."""
    return x if not step else math.floor(x / step + 0.5) * step


def sector_area(rin, rout, w_deg, n):
    """Area of n annular sectors (mm^2)."""
    return 0.5 * math.radians(w_deg) * max(0.0, rout * rout - rin * rin) * n


def cap_pF(area_mm2, t_mm, eps_r):
    return EPS0 * eps_r * area_mm2 * 1e-6 / (t_mm * 1e-3) * 1e12


def solve_transfer(C_pF, g, n):
    """Ca/Cb inverse: the electrode footprint for a target capacitance. Returns the geometry, the realized C
    (after the manufacturing rounding) and the deviation."""
    er = DIELECTRICS[g["ca_diel"]]
    A = C_pF * 1e-12 * g["ca_t"] * 1e-3 / (EPS0 * er) * 1e6          # mm^2 needed [OC] Eq. (20)
    w, rin, rout = g["ca_w"], g["ca_rin"], g["ca_rout"]
    k = 0.5 * math.radians(w) * n                                    # A = k (rout^2 - rin^2)
    mode = g["ca_mode"]
    note = ""
    if mode == "r_out":
        rout = _round(math.sqrt(rin * rin + A / k), g["ca_round"])
    elif mode == "r_in":
        d = rout * rout - A / k
        if d < 0:
            rin, note = 0.0, "target area exceeds the full disc inside r_out: r_in clamped to 0"
        else:
            rin = _round(math.sqrt(d), g["ca_round"])
    elif mode == "width":
        w = _round(math.degrees(A / (0.5 * n * (rout * rout - rin * rin))), g["ca_round"])
    elif mode != "forward":
        raise ValueError(mode)
    area = sector_area(rin, rout, w, n)
    C = cap_pF(area, g["ca_t"], er)
    return dict(C_target_pF=C_pF, C_pF=C, dC_rel=(C - C_pF) / C_pF, area_mm2=area, area_needed_mm2=A,
                r_in=rin, r_out=rout, w_deg=w, n=n, t=g["ca_t"], diel=g["ca_diel"], eps_r=er, mode=mode, note=note)


def _fp(name, node, cap, rin, rout, starts, w):
    return dict(name=name, node=node, cap=cap, r_in=rin, r_out=rout, starts=list(starts), w_deg=w)


def build(locked, geom=None):
    """locked: the stage-1 lock record (inputs, ladder values, z). Returns the full geometry design (JSON-safe)."""
    g = dict(GEOM_DEFAULTS); g.update(geom or {})
    L = locked["ladder"]; P = locked["plates"]
    nk = int(P["n_kept"])
    ca = solve_transfer(L["Ca"], g, nk)                              # Cb uses the same geometry spec
    cb = solve_transfer(L["Cb"], g, nk)
    ri, ro = P["r_inMm"], P["r_outMm"]
    rr_in = max(0.0, ri - g["rotor_in_off"])
    # plate-carrier outer radius: the DXF R500 plate edge, scaled with the active band [IR]
    r_edge = ro * 500.0 / 387.0
    cx_rin, cx_rout = ro * 58.0 / 387.0, ro * 350.0 / 387.0         # Cx pickups, DXF ratios [IR]
    bar_rin = ro * 75.0 / 387.0
    sb = P["N_sec"]
    w_sec = 360.0 / sb
    odd = [w_sec + 2 * w_sec * k for k in range(sb // 2)]
    even = [2 * w_sec * k for k in range(sb // 2)]
    ca_starts = [s + (w_sec - ca["w_deg"]) / 2 for s in odd]         # centred in the facing sector
    cb_starts = [s + (w_sec - cb["w_deg"]) / 2 for s in even]
    fp = dict(
        C1_stator=_fp("C1 stator plate", "1", "C1", ri, ro, odd, w_sec),
        C1_rotor=_fp("C1 rotor face", "5", "C1", rr_in, ro, odd, w_sec),
        C2_stator=_fp("C2 stator plate", "4", "C2", ri, ro, even, w_sec),
        C2_rotor=_fp("C2 rotor face", "6", "C2", rr_in, ro, odd, w_sec),
        Ca_el=_fp("Ca electrode", "2", "Ca", ca["r_in"], ca["r_out"], ca_starts, ca["w_deg"]),
        Ca_counter=_fp("Ca counter (ND1 back face)", "1", "Ca", ri, ro, odd, w_sec),
        Cb_el=_fp("Cb electrode", "3", "Cb", cb["r_in"], cb["r_out"], cb_starts, cb["w_deg"]),
        Cb_counter=_fp("Cb counter (ND4 back face)", "4", "Cb", ri, ro, even, w_sec),
        Cx4_pickup=_fp("Cx4 pickup", "2", "Cx4", cx_rin, cx_rout, even, w_sec),
        Cx4_bars=_fp("island bars on A", "8", "Cx4", bar_rin, cx_rout, even, w_sec),
        Cx3_pickup=_fp("Cx3 pickup", "3", "Cx3", cx_rin, cx_rout, odd, w_sec),
        Cx3_bars=_fp("island bars on B", "7", "Cx3", bar_rin, cx_rout, odd, w_sec),
        CR_A=_fp("C_R face (rotor A)", "5", "C_R", rr_in, ro, [0.0], 360.0),
        CR_B=_fp("C_R face (rotor B)", "6", "C_R", rr_in, ro, [0.0], 360.0),
    )
    # ---- axial stack (z up, mm): a strict layer sequence from the septum outward, foils as their own layers
    #      (every gap value is foil-to-foil) [IR]; side A at z < 0, side B mirrored at z > 0 ----
    tf, tc = g["t_foil"], g["t_carrier"]
    gv, tcx = P["g_vMm"], g["cx_air"] + 2 * g["cx_mica"]
    cxm = f"air {g['cx_air']:g} + mica {g['cx_mica']:g}/face"

    def C(id_, kind, node, t, rin):
        return dict(id=id_, kind=kind, node=node, t=t, r_in=rin, r_out=r_edge)

    def F(key):
        return dict(id=key, kind="foil", key=key, t=tf)

    def G(id_, cap, t, medium, footprint=None, margin=0.0):
        return dict(id=id_, kind="gap", cap=cap, t=t, medium=medium, footprint=footprint, margin=margin)
    seqA = [F("CR_A"), C("A-disc", "rotor", "5", g["t_rotor"], 0.0), F("C1_rotor"), G("C1-gap", "C1", gv, "air"),
            F("C1_stator"), C("ND1", "stator", "1", tc, g["r_bore"]), F("Ca_counter"),
            G("Ca-diel", "Ca", ca["t"], ca["diel"], "Ca_el", g["ca_margin"]), F("Ca_el"),
            C("ND2", "stator", "2", tc, g["r_bore"]), F("Cx4_pickup"), G("Cx4-gap", "Cx4", tcx, cxm),
            F("Cx4_bars"), C("A-flange", "rotor-flange", "8 (floating on A)", g["t_flange"], 0.0)]
    seqB = [F("CR_B"), C("B-disc", "rotor", "6", g["t_rotor"], 0.0), F("C2_rotor"), G("C2-gap", "C2", gv, "air"),
            F("C2_stator"), C("ND4", "stator", "4", tc, g["r_bore"]), F("Cb_counter"),
            G("Cb-diel", "Cb", cb["t"], cb["diel"], "Cb_el", g["ca_margin"]), F("Cb_el"),
            C("ND3", "stator", "3", tc, g["r_bore"]), F("Cx3_pickup"), G("Cx3-gap", "Cx3", tcx, cxm),
            F("Cx3_bars"), C("B-flange", "rotor-flange", "7 (floating on B)", g["t_flange"], 0.0)]
    h = g["t_septum"] / 2
    stack = [dict(G("septum", "C_R", g["t_septum"], "garolite"), z0=-h, z1=h, side="mid", r_in=0.0, r_out=r_edge)]
    for side, seq, sgn in (("A", seqA, -1), ("B", seqB, +1)):
        zz = h
        for it in seq:
            it = dict(it); a, b = sgn * zz, sgn * (zz + it["t"])
            it.update(z0=min(a, b), z1=max(a, b), side=side)
            if it["kind"] == "foil":
                it.update(fp[it["key"]])
            stack.append(it); zz += it["t"]
    stack.sort(key=lambda it: it["z0"])
    foils = [it for it in stack if it["kind"] == "foil"]
    design = dict(schema=SCHEMA, units="mm", lock=dict(locked), geom=g, Ca=ca, Cb=cb, footprints=fp,
                  stack=stack, foils=foils, z_total=stack[-1]["z1"] - stack[0]["z0"], r_edge=r_edge)
    design["checks"] = checks(design)
    return design


def _arc_overlap(a0, w0, a1, w1):
    """Angular overlap (deg) of two arcs [a, a+w) on the circle."""
    tot = 0.0
    for sh in (-360.0, 0.0, 360.0):
        lo, hi = max(a0, a1 + sh), min(a0 + w0, a1 + w1 + sh)
        tot += max(0.0, hi - lo)
    return tot


def overlap_area(f1, f2):
    """Plan overlap area (mm^2) of two sector-set footprints."""
    rin, rout = max(f1["r_in"], f2["r_in"]), min(f1["r_out"], f2["r_out"])
    if rout <= rin:
        return 0.0
    ang = sum(_arc_overlap(a, f1["w_deg"], b, f2["w_deg"]) for a in f1["starts"] for b in f2["starts"])
    return 0.5 * math.radians(ang) * (rout * rout - rin * rin)


PAIRS = dict(C1=("C1_stator", "C1_rotor"), C2=("C2_stator", "C2_rotor"), Ca=("Ca_el", "Ca_counter"),
             Cb=("Cb_el", "Cb_counter"), Cx4=("Cx4_pickup", "Cx4_bars"), Cx3=("Cx3_pickup", "Cx3_bars"),
             C_R=("CR_A", "CR_B"))
ROTATING = ("C1", "C2", "Cx3", "Cx4")       # one electrode on a rotor (or its island bars)


def adjacency(design):
    """For each capacitor: its two foils are separated by exactly one layer, a gap carrying this capacitor's
    name and thickness, and they overlap in plan [ME]. Returns {cap: (ok, detail)}."""
    st = design["stack"]
    pos = {it["id"]: i for i, it in enumerate(st)}
    out = {}
    for cap, (k1, k2) in PAIRS.items():
        i1, i2 = sorted((pos[k1], pos[k2]))
        between = st[i1 + 1:i2]
        a, b = st[pos[k1]], st[pos[k2]]
        ov0 = overlap_area(a, b)
        rot = cap in ROTATING
        # a rotating pair (stator vs rotor) is judged at its aligned angle: the max over one sector pitch
        ovm = max(overlap_area(a, dict(b, starts=[x + d for x in b["starts"]])) for d in range(0, 61)) if rot else ov0
        ok = len(between) == 1 and between[0]["kind"] == "gap" and between[0]["cap"] == cap and ovm > 0
        out[cap] = (bool(ok), f"{k1} <-> {k2} across {[b_['id'] for b_ in between]}, plan overlap "
                              + (f"{ov0:.0f} at 0 deg / {ovm:.0f} aligned mm^2" if rot else f"{ov0:.0f} mm^2 (fixed)"))
    return out


def _pct(x):
    """percent, with a rounded zero printed as +0.0000 (float noise must not flip the sign; JS mirror alike)"""
    v = x * 100
    return 0.0 if abs(v) < 5e-5 else v


def checks(design):
    """Geometric feasibility checks for the geometrized pair (Ca/Cb) and the stack [OC geometry]."""
    fp = design["footprints"]; g = design["geom"]
    res = {}
    for cap, el, ct in (("Ca", "Ca_el", "Ca_counter"), ("Cb", "Cb_el", "Cb_counter")):
        e, c = fp[el], fp[ct]
        geo = design[cap]
        inside = (e["r_in"] >= c["r_in"] - 1e-9 and e["r_out"] <= c["r_out"] + 1e-9 and e["w_deg"] <= c["w_deg"] + 1e-9)
        res[f"{cap}: electrode inside its counter-electrode"] = (
            inside, f"r{e['r_in']:.1f}-{e['r_out']:.1f} x {e['w_deg']:.2f} deg within r{c['r_in']:.0f}-{c['r_out']:.0f} x {c['w_deg']:.0f} deg")
        ov = overlap_area(e, c)
        res[f"{cap}: overlap area = electrode area"] = (abs(ov - geo["area_mm2"]) <= 1e-6 * geo["area_mm2"],
                                                         f"{ov:.1f} vs {geo['area_mm2']:.1f} mm^2")
        res[f"{cap}: clears the carrier bore"] = (e["r_in"] - g["ca_margin"] >= g["r_bore"],
                                                  f"r_in {e['r_in']:.1f} - margin {g['ca_margin']:.0f} >= bore {g['r_bore']:.0f}")
        res[f"{cap}: dielectric margin fits the sector pitch"] = (
            e["w_deg"] + 2 * math.degrees(g["ca_margin"] / max(e["r_in"], 1e-9)) <= 360.0 / (len(e["starts"]) or 1),
            f"foil {e['w_deg']:.1f} deg + 2 x {g['ca_margin']:.0f} mm margin at r_in")
        res[f"{cap}: realized C = locked C"] = (abs(geo["dC_rel"]) <= 1e-9 or g["ca_round"] > 0,
                                                f"{geo['C_pF']:.3f} vs {geo['C_target_pF']:.3f} pF ({_pct(geo['dC_rel']):+.4f} %)"
                                                + (" -- rounding: engine round-trip decides" if g["ca_round"] > 0 else ""))
    P = design["lock"]["plates"]
    res["layout: alternating sectors (n_kept = N_sec / 2, as drawn)"] = (
        int(P["n_kept"]) * 2 == int(P["N_sec"]), f"n_kept {P['n_kept']} of N_sec {P['N_sec']}")
    for cap, (ok, det) in adjacency(design).items():
        res[f"stack: {cap} electrodes face each other"] = (ok, det)
    return {k: dict(pass_=bool(v[0]), detail=v[1]) for k, v in res.items()}


def lock_record(lad, inputs, z, converged, engine_version="", strip=None):
    """The stage-1 lock: what stage 2 may not change. hash = sha256 of the canonical JSON (first 12 hex)."""
    rec = dict(inputs=inputs, plates={k: lad["plates"][k] for k in ("r_inMm", "r_outMm", "g_vMm", "N_sec", "n_kept")},
               ladder={k: v["value"] for k, v in lad["ladder"].items()}, z=z, converged=converged,
               engine=engine_version)
    blob = json.dumps(dict(inputs=rec["inputs"], ladder=rec["ladder"]), sort_keys=True, separators=(",", ":"))
    rec["hash"] = hashlib.sha256(blob.encode()).hexdigest()[:12]
    return rec


def _selftest():
    import os
    import sys
    here = os.path.dirname(os.path.abspath(__file__))
    if here not in sys.path:
        sys.path.insert(0, here)
    import pump_sizing as PS
    lad = PS.size(dict(dielectric="vacuum"))
    rec = lock_record(lad, {}, 1.3254745316585308, True)
    # the DXF seed reproduces the freeze 309 pF (forward mode at r110-175, 6 x 30 deg, 4.5 mm mica)
    fwd = solve_transfer(309.0, dict(GEOM_DEFAULTS, ca_mode="forward"), 6)
    ok = abs(fwd["area_mm2"] - 29099.002) < 0.01 and abs(fwd["C_pF"] - 309.18) < 0.01
    d = build(rec)
    ok &= abs(d["Ca"]["C_pF"] - lad["ladder"]["Ca"]["value"]) < 1e-9 and all(v["pass_"] for v in d["checks"].values())
    ok &= all(v[0] for v in adjacency(d).values())
    if not ok:
        raise AssertionError("pump_geometry on-load self-test FAILED")
    return True


SELFTEST_OK = _selftest()

if __name__ == "__main__":
    import pump_sizing as PS
    lad = PS.size()
    d = build(lock_record(lad, {}, 1.3254745316585308, True))
    print(json.dumps({k: d[k] for k in ("Ca", "Cb", "z_total")}, indent=1))
    for k, v in d["checks"].items():
        print(("PASS " if v["pass_"] else "FAIL ") + k + " -- " + v["detail"])
    for s in d["stack"]:
        print(f"{s['id']:10s} {s['kind']:12s} z {s['z0']:8.2f} .. {s['z1']:8.2f}  t {s['t']}")
    print("selftest", _selftest())
