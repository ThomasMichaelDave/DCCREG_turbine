#!/usr/bin/env python3
"""sim/bridge_ring_bearings.py -- the bridge-ring bearings of the multiplier's layout (PROPOSED, 2026-10-11): where they
go, which part, and what the shafts do with them as drawn.

Without the hub-face bearings (sim/multiplier-layout-findings.md §7) the counter-rotor rides on the shaft at its two
Ca|reluctance bearings only, and its bridge rings overhang them toward the machine's ends. A bearing between the shaft
and each bridge ring's outer end (the record's eighth pair, sim/tube-shaft-findings.md §0) closes the overhang. This
study:
  1. places the pair [IR]: each bearing in the record's end-bearing slot (h 467-487 mm from the hub's centre), and the
     end bearing (frame) moved out one 20 mm slot (h 487-507). The machine grows 974 -> 1014 mm. The seat is an
     austenitic stainless cartridge in an 8 mm G10 spider, centred in its slot like every spider of the record. A 6 mm
     G10 ring joins the spider's rim to the bridge ring's outer face. The spider then stays 9 mm clear of the utrons'
     end turns; an end disc on the face itself would leave 3 mm;
  2. names the part [IR: catalogue data, PART and ALTERNATES below];
  3. re-runs the shafts: sim/shaft_bearings.py two_body on the record's solids as sim/multiplier_layout.py shaft()
     moves them, with the slot and the new parts. It is gated on that study's own rows and cross-checked against the
     drawn solids' masses (sim/tube_geometry.py LayoutMachine);
  4. reports the bearings' loads, lives, speed, friction and stiffness, from sim/rotor_mechanics.py's functions at the
     part's ratings.
Usage: python3 sim/bridge_ring_bearings.py [--no-solids] -> sim/bridge_ring_bearings_results.json and
       docs/figures/bridge-ring-bearings.png (about two minutes; --no-solids skips the cross-check on the drawn solids)
"""
import argparse
import copy
import json
import math
import os
import sys
import time

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path[:0] = [HERE]
import stack_sizing as S                                 # noqa: E402

OUT_JSON = os.path.join(HERE, "bridge_ring_bearings_results.json")
FIG = os.path.join(ROOT, "docs", "figures", "bridge-ring-bearings.png")
LAYOUT_JSON = os.path.join(HERE, "multiplier_layout_results.json")
SRC = {
    "stack": "sim/multiplier_layout_results.json stack (the layout: h_end 487, L 974, the record's reluctance sections)",
    "shaft model": "sim/shaft_bearings.py two_body; sim/multiplier_layout.py shaft() (the record's solids moved)",
    "gate rows": "sim/multiplier_layout_results.json shaft.rows",
    "bearing functions": "sim/rotor_mechanics.py bearing_k, bearing_life, palmgren_W (rotor-mechanics-findings §4-§6)",
    "the solids": "sim/tube_geometry.py LayoutMachine (--layout), which imports this file's placement",
    "the part": "PART / ALTERNATES below: catalogue data as a web search rendered it on 2026-10-11",
}

# ---------------------------------------------------------------------------------------------------- the part
# [IR] catalogue data as a web search rendered the distributors' listings and SKF's Explorer brochure (2026-10-11). The
# makers' own sites are outside this session's network policy: re-read the current product page before ordering.
PART = dict(
    maker="SKF", designation="6205-2Z",
    what="SKF Explorer deep groove ball bearing, single row; a sheet-steel shield each side (2Z, non-contact); normal "
         "radial internal clearance (CN); greased for life",
    d_mm=25.0, D_mm=52.0, B_mm=15.0, C_N=14.8e3, C0_N=7.8e3, Pu_N=335.0, kr=0.025, f0=14.0,
    n_ref_rpm=28000.0, n_lim_rpm=14000.0, kg=0.13, da_min_mm=30.6, Da_max_mm=46.4,
    running_accuracy="ISO P5 (SKF Explorer bearings up to 52 mm outside diameter; the 6205's is 52)",
    dimensional_accuracy="ISO P6, the width to 0 / -60 um",
    sources={
        "ratings, speeds, mass, abutments": "https://www.simplybearings.co.uk/products/6205-2z-skf",
        "Pu, reference speed, kr, f0": "https://www.simplybearings.co.uk/products/6205-skf",
        "limiting speed 14 000 r/min (2Z)": "https://uk.rs-online.com/web/p/ball-bearings/2868038",
        "Explorer accuracy: running P5 up to 52 mm OD, dimensions P6":
            "https://www.skf.com/binaries/pub12/Images/SKF%20Explorer%20deep%20groove%20ball%20bearings%20with%20RSL%20"
            "and%20RSH%20seals_6270%20EN_tcm_12-179206.pdf",
        "the same, trade press": "https://www.machinedesign.com/archive/bearings-products-deep-groove-bearings",
        "spring preload F = k d, k 0.005-0.01 kN/mm for small motors (SKF's rule)":
            "https://www.designworldonline.com/what-are-the-best-methods-for-preload-in-a-bearing-system/"})
ALTERNATES = [
    dict(maker="Schaeffler (FAG)", designation="6205-C-2Z", C_N=15.9e3, C0_N=7.8e3, Pu_N=530.0, f0=13.8,
         n_ref_rpm=16000.0, n_lim_rpm=18400.0, kg=0.129,
         note="Generation C, shields both sides; its running accuracy is to be confirmed (P6 or better is needed)",
         sources=["https://medias-at.schaeffler.com/de/product/rotary/rolling-and-plain-bearings/ball-bearings/"
                  "deep-groove-ball-bearings/6205-c-2z-l207>v/p/1695363",
                  "https://csapagy-bolt.hu/catalog/product/57621", "https://uk.rs-online.com/web/p/ball-bearings/1371663"]),
    dict(maker="NSK", designation="6205ZZ", C_N=14.0e3, C0_N=7.85e3, n_lim_rpm=15000.0, kg=0.129,
         note="shields both sides; normal tolerances unless a P6 / P5 suffix is ordered; distributors list Cr 14.0 kN",
         sources=["https://uk.rs-online.com/web/p/ball-bearings/4090502", "https://www.imssupply.com/catalog/nsk/6205zz.html"]),
]

# ---------------------------------------------------------------------------------------------------- the placement
SLOT = S.BEARING["slot"]                                 # 20 mm, the record's bearing-hub slot (sim/stack_sizing.py)
WIDTH, SPIDER_T, R_OD = S.BEARING["width"], S.BEARING["spider_t"], 0.5 * S.BEARING["od"]     # 15, 8, 26
CART_R1 = 30.0              # the cartridge's barrel r 26-30 [RH: a 4 mm wall], the spider's bore
CART_FLANGE_R1 = 38.0       # its flange on the spider's outboard face [RH]
CART_LIP_R0 = 0.5 * PART["Da_max_mm"]                    # 23.2: the lip over the outer ring, inside the housing abutment
CART_LIP_T = 1.5            # [RH]
ADAPTER_T = 0.5 * (SLOT - SPIDER_T)                      # 6: the spider centred in its slot reaches the ring's face
CART_MATERIAL = "austenitic stainless cartridge (1.4404), non-magnetic, as the shaft"
PRELOAD_N = 100.0           # the record's axial spring preload (sim/rotor-mechanics-findings.md §4)
K_SPIDER = 3e8              # a G10 spider, radial (sim/rotor_mechanics.py fe_study) [RH]
K_REAL = 0.86e8             # a preloaded 6205 in a G10 spider: the record's (sim/rotor-mechanics-findings.md §4)


def ring_section(st):
    """the record's bridge ring and utron (side A, in the layout's frame: z from side A's end of the 974 mm stack)."""
    rel = {e["kind"]: e for e in st["record_reluctance"] if e["side"] == "A"}
    return rel["w ring"], rel["w utron"]


def placement(st):
    """the drawn placement [IR]: z from side A's end of the longer machine, h from the hub's centre (mm); the parts of
    side A from the bearing's centre z_r outward and inward (side B mirrored)."""
    h_end0, L0 = st["h_end_mm"], st["L_mm"]
    wr, wu = ring_section(st)
    h_face = h_end0 - wr["z0"]                            # the bridge ring's outer face, h 467
    h_turns = h_end0 - wu["z0"]                           # the utrons' end turns, h 464
    zc, L = h_end0 + SLOT, L0 + 2 * SLOT                  # 507, 1014
    h_ring = h_end0 - 0.5 * SLOT                          # 477: the record's end-bearing slot
    h_frame = h_end0 + 0.5 * SLOT                         # 497: one slot out
    za = zc - h_ring
    parts = dict(
        bearing=dict(r0=S.SHAFT_R, r1=R_OD, z0=za - 0.5 * WIDTH, z1=za + 0.5 * WIDTH),
        cartridge_barrel=dict(r0=R_OD, r1=CART_R1, z0=za - 0.5 * WIDTH, z1=za + 0.5 * WIDTH),
        cartridge_flange=dict(r0=CART_R1, r1=CART_FLANGE_R1, z0=za - 0.5 * WIDTH, z1=za - 0.5 * SPIDER_T),
        cartridge_lip=dict(r0=CART_LIP_R0, r1=R_OD, z0=za + 0.5 * WIDTH, z1=za + 0.5 * WIDTH + CART_LIP_T),
        spider=dict(r0=CART_R1, r1=wr["r1"], z0=za - 0.5 * SPIDER_T, z1=za + 0.5 * SPIDER_T),
        adapter=dict(r0=wr["r0"], r1=wr["r1"], z0=za + 0.5 * SPIDER_T, z1=zc - h_face))
    assert abs(parts["adapter"]["z1"] - parts["adapter"]["z0"] - ADAPTER_T) < 1e-9
    return dict(L_mm=L, L_layout_mm=L0, zc_mm=zc, h_ring_mm=h_ring, h_frame_mm=h_frame, h_ca_rel_mm=st["h_bearing_mm"],
                z_ring_mm=[zc - h_ring, zc + h_ring], z_frame_mm=[zc - h_frame, zc + h_frame],
                z_ca_rel_mm=[zc - st["h_bearing_mm"], zc + st["h_bearing_mm"]], side_A=parts,
                clear_spider_to_turns_mm=(h_ring - 0.5 * SPIDER_T) - h_turns, clear_face_to_turns_mm=h_face - h_turns,
                clear_frame_spider_mm=(h_frame - 0.5 * SPIDER_T) - (h_ring + 0.5 * WIDTH),
                bearing_faces_gap_mm=(h_frame - 0.5 * WIDTH) - (h_ring + 0.5 * WIDTH))


def ann(kg_per_mm3, r0, r1, z0, z1):
    """an annulus's mass (kg) and its inertia about a diameter through its centroid (kg m^2)."""
    kg = math.pi * (r1 ** 2 - r0 ** 2) * (z1 - z0) * kg_per_mm3
    return kg, kg * ((r0 ** 2 + r1 ** 2) / 4.0 + (z1 - z0) ** 2 / 12.0) * 1e-6


def new_parts(pl):
    """the bridge-ring bearings' parts as lumped masses [IR: the record's densities]: the bearing on the shaft (the
    record's convention), the cartridge, spider and adapter on the counter-rotor."""
    import shaft_bearings as SB
    rho = {"cartridge": SB._density("stainless") * 1e-9, "g10": SB._density("G10") * 1e-9}
    out = []
    for s_, sg in (("A", 1.0), ("B", -1.0)):
        zc = pl["zc_mm"]
        put = lambda z: zc - sg * (zc - z)                # side A's z mirrored onto side B
        p = pl["side_A"]
        b = p["bearing"]
        zb = put(0.5 * (b["z0"] + b["z1"]))
        J = PART["kg"] * ((b["r0"] ** 2 + b["r1"] ** 2) / 4.0 + WIDTH ** 2 / 12.0) * 1e-6
        out.append(dict(name=f"{s_}_bearing_bridge-ring", body="bearing", material="bearing", kg=PART["kg"], x=0.0, z=zb,
                        J_yy_kgm2=J))
        pieces = [ann(rho["cartridge"], q["r0"], q["r1"], q["z0"], q["z1"]) + (0.5 * (q["z0"] + q["z1"]),)
                  for q in (p["cartridge_barrel"], p["cartridge_flange"], p["cartridge_lip"])]
        m_c = sum(k for k, _, _ in pieces)
        z_c = sum(k * z for k, _, z in pieces) / m_c
        J_c = sum(J_ + k * (z - z_c) ** 2 * 1e-6 for k, J_, z in pieces)
        out.append(dict(name=f"{s_}_cartridge_bridge-ring", body="stator", material="stainless", kg=m_c, x=0.0,
                        z=put(z_c), J_yy_kgm2=J_c))
        for nm, q in (("spider_bridge-ring", p["spider"]), ("ring_adapter", p["adapter"])):
            kg, J_ = ann(rho["g10"], q["r0"], q["r1"], q["z0"], q["z1"])
            out.append(dict(name=f"{s_}_{nm}", body="stator", material="G10", kg=kg, x=0.0, z=put(0.5 * (q["z0"] + q["z1"])),
                            J_yy_kgm2=J_))
    return out


# ---------------------------------------------------------------------------------------------------- the shafts
_REC = {}


def _record():
    import shaft_bearings as SB
    if "rec" not in _REC:
        _REC["rec"] = SB.record_parts()
    return _REC["rec"]


def moved(st, slot, ring):
    """sim/multiplier_layout.py shaft()'s model: the record's solids moved to the layout (side A unchanged up to its
    Ca|reluctance bearing; the vanes and Ca plates to their new places; the hub-face bearings, the old cage and
    sleeves out; the hub and side B moved by the layout's growth; the cage, the sleeves, the can and the decks in).
    Here each end bearing and its frame spider move out a further slot (slot mm), and with ring the bridge-ring
    bearings' parts come in. Returns (lad, parts, the bridge-ring bearings' z)."""
    import multiplier_layout as ML
    lad, parts = _record()
    el = lad["tube_geometry"]["elements"]
    z_hub, dh = 470.0, st["dh_side_mm"]                   # the record's hub centre (z 398-542); the layout's growth
    zc_new = z_hub + dh + slot
    h_brg = st["h_bearing_mm"]

    def z_map(z_rec, end=False):
        """record z -> new z: side A's reluctance section and bearings, side B's, or the hub; the end bearings one more
        slot out."""
        if z_rec <= 208.0:
            return z_rec + (0.0 if end else slot)
        if z_rec >= 732.0:
            return z_rec + 2 * dh + (2 * slot if end else slot)
        return z_rec + dh + slot
    hv0, hv1 = st["h_vanes"]
    out = []
    for p_ in parts:
        nm = p_["name"]
        if "hub_face" in nm or nm.startswith("rotor_sleeve") or "stator_cage" in nm:
            continue
        q = dict(p_)
        if nm.startswith("A_C1_") or nm.startswith("B_C2_"):
            side = nm[0]
            h_rec = 470.0 - p_["z"] if side == "A" else p_["z"] - 470.0
            h_new = hv0 + (202.0 - h_rec)
            q["z"] = (zc_new - h_new) if side == "A" else (zc_new + h_new)
        elif nm.startswith("A_Ca_") or nm.startswith("B_Cb_"):
            side = nm[0]
            h_rec = 470.0 - p_["z"] if side == "A" else p_["z"] - 470.0
            h_new = st["h_col_mm"] + (256.0 - h_rec)
            q["z"] = (zc_new - h_new) if side == "A" else (zc_new + h_new)
        else:
            q["z"] = z_map(p_["z"], end=nm.endswith(("_bearing_end", "_spider_end")))
        out.append(q)
    L = st["L_mm"] + 2 * slot

    def disc(name, body, kg, zc, r0, r1, t):
        J = kg * (r0 ** 2 + r1 ** 2) / 4.0 * 1e-6 + kg * (t * 1e-3) ** 2 / 12.0
        return dict(name=name, body=body, material="new", kg=kg, x=0.0, z=zc, J_yy_kgm2=J)

    def tube(name, body, rho, r0, r1, z0, z1):
        kg = math.pi * (r1 ** 2 - r0 ** 2) * (z1 - z0) * rho * 1e-9
        J = kg * ((r0 ** 2 + r1 ** 2) / 4.0 * 1e-6 + ((z1 - z0) * 1e-3) ** 2 / 12.0)
        return dict(name=name, body=body, material="new", kg=kg, x=0.0, z=0.5 * (z0 + z1), J_yy_kgm2=J)
    za_brg, zb_brg = zc_new - h_brg, zc_new + h_brg
    out.append(tube("cage", "stator", 1850.0, ML.CAGE_R0, ML.CAGE_R1, za_brg, zb_brg))
    for sg, nm in ((-1, "A"), (1, "B")):
        z0, z1 = sorted((zc_new + sg * (ML.CAN_Z + ML.CAN_DISC_T), zc_new + sg * (h_brg - 0.5 * S.BEARING["width"])))
        out.append(tube(f"{nm}_sleeve", "rotor", 1850.0, ML.SHAFT_R, ML.SLEEVE_R, z0, z1))
        out.append(disc(f"{nm}_can_disc", "rotor", math.pi * (ML.CAN_R ** 2 - ML.SHAFT_R ** 2) * ML.CAN_DISC_T * 2700e-9,
                        zc_new + sg * (ML.CAN_Z + 0.5 * ML.CAN_DISC_T), ML.SHAFT_R, ML.CAN_R, ML.CAN_DISC_T))
        dk = st["deck_mass"][nm]
        out.append(disc(f"{nm}_deck", "rotor", dk["kg"], zc_new + sg * (ML.DECK_Z0 + 0.5 * (ML.DECK_T + ML.DECK_H)),
                        ML.DECK_R0, ML.DECK_R1, ML.DECK_T + ML.DECK_H))
    out.append(tube("can", "rotor", 2700.0, ML.CAN_R - ML.CAN_T, ML.CAN_R, zc_new - ML.CAN_Z, zc_new + ML.CAN_Z))
    lad2 = copy.deepcopy(lad)
    el2 = []
    for e in lad2["tube_geometry"]["elements"]:
        if e["kind"] == "bearing" and e.get("where") == "hub face":
            continue
        end = e["kind"] == "bearing" and e.get("where") == "end"
        for k in ("z0", "z1", "zc", "zs0", "zs1"):
            if k in e:
                e[k] = z_map(e[k], end=end)
        el2.append(e)
    if ring:
        pl = placement(st)
        assert abs(pl["L_mm"] - L) < 1e-9 and abs(pl["zc_mm"] - zc_new) < 1e-9
        out += new_parts(pl)
        sp = pl["side_A"]["spider"]
        for s_, (z0, z1) in (("A", (sp["z0"], sp["z1"])), ("B", (L - sp["z1"], L - sp["z0"]))):
            # the counter-rotor reaches its bridge-ring spiders: its beam spans them
            el2.append(dict(kind="spider", body="stator", side=s_, where="bridge ring", z0=z0, z1=z1, node=""))
        z_ring = tuple(pl["z_ring_mm"])
    else:
        z_ring = (10.0 + 18.0, L - 10.0 - 18.0)               # the layout study's (beside the end bearings)
    lad2["tube_geometry"]["elements"] = el2
    lad2["tube_geometry"]["L_total_mm"] = L
    return lad2, out, z_ring


def row_of(r, kb, d):
    return dict(d_mm=d, k_b_N_per_m=kb, f_Hz=r["f_Hz"][:3], f1_Hz=r["f1_Hz"], gap_change_um=r["gap_change_um"],
                defl_shaft_max_um=r["defl_shaft_max_um"], bearing_loads_1g_N=r["bearing_loads_1g_N"],
                m_rotor_kg=r["m_rotor_kg"], m_counter_rotor_kg=r["m_counter_rotor_kg"])


def shafts(st, log):
    import shaft_bearings as SB
    crit = 3 * SB.F_REL_HZ
    out = dict(criterion_f1_Hz=crit, pumps_Hz=[120.0, 240.0], k_stiff_N_per_m=SB.K_BEARING, k_real_N_per_m=K_REAL)
    # G1: this file's copy of the layout study's model reproduces its rows
    lad0, parts0, ring0 = moved(st, 0.0, False)
    ref = json.load(open(LAYOUT_JSON))["shaft"]["rows"]
    g1 = []
    for rr in ref:
        r = SB.two_body(lad0, parts0, rr["d_mm"], "coupler", k_b=rr["k_b_N_per_m"], k_mag=2e5,
                        extra_inner=ring0 if rr["bridge_ring_bearings"] else ())
        g1.append(dict(d_mm=rr["d_mm"], bridge_ring_bearings=rr["bridge_ring_bearings"], k_b_N_per_m=rr["k_b_N_per_m"],
                       f_Hz=r["f_Hz"][:3], f_layout_Hz=rr["f_Hz"][:3],
                       dev=max(abs(a - b) / b for a, b in zip(r["f_Hz"][:3], rr["f_Hz"][:3]))))
    out["gate_copy"] = dict(rows=g1, worst_rel=max(x["dev"] for x in g1), ok=bool(max(x["dev"] for x in g1) < 1e-9))
    log(f"  G1 the layout study's model, copied: worst {out['gate_copy']['worst_rel']:.1e} relative over {len(g1)} rows")
    # the drawn placement
    lad1, parts1, ring1 = moved(st, SLOT, True)
    out["z_ring_mm"] = list(ring1)
    out["L_mm"] = lad1["tube_geometry"]["L_total_mm"]
    rows = []
    for d in (25.0, 30.0, 40.0):
        for kb in (SB.K_BEARING, K_REAL):
            r = SB.two_body(lad1, parts1, d, "coupler", k_b=kb, k_mag=2e5, extra_inner=ring1)
            rows.append(dict(row_of(r, kb, d), ok=bool(r["f1_Hz"] >= crit and max(abs(x) for x in r["gap_change_um"]) <= 50.0)))
            log(f"  d {d:.0f}, k_b {kb:.2e}: f {', '.join(f'{x:.1f}' for x in r['f_Hz'][:3])} Hz; gap {r['gap_change_um'][0]:+.1f} um;"
                f" rotor {r['m_rotor_kg']:.2f} kg, counter-rotor {r['m_counter_rotor_kg']:.2f} kg")
    out["rows"] = rows
    # sweep the seat stiffness at the drawn placement (the figure)
    sweep = {}
    for d in (25.0, 30.0):
        ks = [float(k) for k in np.geomspace(4e7, 5e8, 15)]
        fs = [SB.two_body(lad1, parts1, d, "coupler", k_b=k, k_mag=2e5, extra_inner=ring1)["f_Hz"][:3] for k in ks]
        sweep[f"{d:.0f}"] = dict(k_b_N_per_m=ks, f_Hz=fs)
    out["sweep"] = sweep
    m = SB.two_body(lad1, parts1, 25.0, "coupler", k_b=K_REAL, k_mag=2e5, extra_inner=ring1, n_shapes=3)
    el = lad1["tube_geometry"]["elements"]
    out["shapes_d25_real"] = dict(z_mm=m["z_mm"], modes=m["shapes"],
                                  bearings=dict(frame=sorted(e["zc"] for e in el if e["kind"] == "bearing" and e.get("where") == "end"),
                                                inner=sorted(e["zc"] for e in el if e["kind"] == "bearing" and e.get("where") != "end"),
                                                ring=list(ring1)),
                                  utron_planes=sorted(e["zc"] for e in el if e["kind"] == "w utron"))
    return out, (lad1, parts1, ring1)


# ---------------------------------------------------------------------------------------------------- the drawn solids
RHO_LAYOUT = [("silicone potting", 1150.0), ("PTFE HV wire", 2950.0), ("LV cable", 2950.0), ("PTFE", 2200.0),
              ("brass", 8500.0), ("tinned Cu", 8900.0), ("Cu strap", 8900.0), ("HV rectifier stick", 2500.0),
              ("surge resistor", 2500.0), ("HV ceramic", 2500.0), ("the clamp string", 2500.0)]
# kg/m^3: [RH] silicone and the parts' bodies as sim/multiplier_layout.py deck_mass; [IR] PTFE, brass, Cu, and the HV
# wire as 1 mm Cu in 3 mm PTFE (an eighth Cu by section); then the record's table (sim/shaft_bearings.py DENSITY)


def solids_parts(log):
    """every drawn solid of the layout (sim/tube_geometry.py LayoutMachine, with the bridge-ring bearings) with its body,
    mass, centroid and inertia, and the elements the two-body model reads."""
    import shaft_bearings as SB
    import tube_geometry as TG
    from OCP.BRepGProp import BRepGProp
    from OCP.GProp import GProp_GProps
    m = TG.LayoutMachine().build()
    parts = []
    for pt in m.parts:
        mat = m.protos[pt["proto"]][2]
        rho = next((v for k, v in RHO_LAYOUT if k in mat), None) or SB._density(mat)
        g = GProp_GProps(); BRepGProp.VolumeProperties_s(m.placed(pt), g)
        c, I = g.CentreOfMass(), g.MatrixOfInertia()
        parts.append(dict(name=pt["name"], body=pt["body"], material=mat, kg=g.Mass() * 1e-9 * rho, x=c.X(), z=c.Z(),
                          J_yy_kgm2=I.Value(2, 2) * 1e-15 * rho))
    zc, L = m.zc, m.L_mm
    fl = [e for e in m.lay["stack"]["elements"] if e["kind"] == "flange"][0]
    el = [dict(kind="hub", body="rotor", z0=zc - fl["h0"], z1=zc + fl["h0"])]
    by = {p_["name"]: p_ for p_ in parts}
    for s_ in "AB":
        for where, nm in (("end", f"{s_}_bearing_end"), ("Ca|reluctance", f"{s_}_bearing_Ca-reluctance"),
                          ("bridge ring", f"{s_}_bearing_bridge-ring")):
            el.append(dict(kind="bearing", body="stator", side=s_, where=where, zc=by[nm]["z"], z0=by[nm]["z"], z1=by[nm]["z"]))
    st_ = [p_ for p_ in parts if p_["body"] == "stator" and not p_["name"].endswith("_spider_end")]
    zs = [TG.bbox(m.placed(pt)) for pt in m.parts if pt["name"] in {p_["name"] for p_ in st_}]
    el.append(dict(kind="counter-rotor", body="stator", z0=min(lo[2] for lo, _ in zs), z1=max(hi[2] for _, hi in zs)))
    el += [dict(e, body="rotor") for e in m.el if e["kind"] == "w utron"]
    lad = dict(tube=m.lad["tube"], tube_geometry=dict(elements=el, L_total_mm=L))
    log(f"  the drawn solids: {len(parts)}; on the rotor {sum(p_['kg'] for p_ in parts if p_['body'] != 'stator'):.2f} kg "
        f"(the shaft halves' solids {sum(p_['kg'] for p_ in parts if p_['name'].startswith('shaft_')):.2f} of it), "
        f"counter-rotor {sum(p_['kg'] for p_ in st_):.2f} kg")
    return lad, parts, m


def cross_check(st, lad1, parts1, ring1, log):
    import shaft_bearings as SB
    lad, parts, m = solids_parts(log)
    rows = []
    for kb in (SB.K_BEARING, K_REAL):
        r = SB.two_body(lad, parts, 25.0, "coupler", k_b=kb, k_mag=2e5)
        q = SB.two_body(lad1, parts1, 25.0, "coupler", k_b=kb, k_mag=2e5, extra_inner=ring1)
        rows.append(dict(k_b_N_per_m=kb, solids=row_of(r, kb, 25.0), moved=row_of(q, kb, 25.0),
                         dev_f1=(r["f1_Hz"] - q["f1_Hz"]) / q["f1_Hz"]))
        log(f"  cross-check k_b {kb:.2e}: solids f {', '.join(f'{x:.1f}' for x in r['f_Hz'][:3])} Hz "
            f"(rotor {r['m_rotor_kg']:.2f}, counter-rotor {r['m_counter_rotor_kg']:.2f} kg) against "
            f"{', '.join(f'{x:.1f}' for x in q['f_Hz'][:3])} Hz")
    by = {p_["name"]: p_ for p_ in parts}
    pl = placement(st)
    drawn = dict(z_ring_mm=[by["A_bearing_bridge-ring"]["z"], by["B_bearing_bridge-ring"]["z"]],
                 z_frame_mm=[by["A_bearing_end"]["z"], by["B_bearing_end"]["z"]],
                 z_ca_rel_mm=[by["A_bearing_Ca-reluctance"]["z"], by["B_bearing_Ca-reluctance"]["z"]], L_mm=m.L_mm,
                 zc_mm=m.zc)
    ok_place = all(abs(a - b) < 1e-6 for k in ("z_ring_mm", "z_frame_mm", "z_ca_rel_mm") for a, b in zip(drawn[k], pl[k])) \
        and abs(drawn["L_mm"] - pl["L_mm"]) < 1e-9
    new = {nm: dict(kg=by[nm]["kg"], z=by[nm]["z"]) for nm in by if "bridge-ring" in nm or "ring_adapter" in nm}
    return dict(rows=rows, worst_dev_f1=max(abs(x["dev_f1"]) for x in rows), drawn=drawn, place_ok=bool(ok_place),
                new_solids=new, ok=bool(max(abs(x["dev_f1"]) for x in rows) < 0.05 and ok_place))


# ---------------------------------------------------------------------------------------------------- the loads
def duty(sh, st):
    """the bearings' duty on a vertical axis [IR: ISO 281 form and Palmgren, at the part's ratings]: the bottom frame
    bearing locates both bodies, the bottom bridge-ring bearing the counter-rotor (as the drive's first cut's gear-end
    bearing does, docs/drive-gear-belt.md §5); the others float on the spring preload."""
    import rotor_mechanics as RM
    b = dict(RM.BRG_6205, c_dyn=PART["C_N"], c_stat=PART["C0_N"], f0=PART["f0"])
    r = [x for x in sh["rows"] if x["d_mm"] == 25.0 and abs(x["k_b_N_per_m"] - K_REAL) < 1.0][0]
    g = 9.81
    W_cr, W_r = r["m_counter_rotor_kg"] * g, r["m_rotor_kg"] * g
    n_rel, n_abs = 1200.0, 600.0
    rows = {}

    def put(name, Fa, n, note):
        life = RM.bearing_life(Fa, 0.0, n, b)
        W, M = RM.palmgren_W(n, 1.0, 30.0, Fa=Fa, b=b)
        W_hi, _ = RM.palmgren_W(n, 2.0, 70.0, Fa=Fa, b=b)
        rows[name] = dict(Fa_N=Fa, n_rpm=n, P_N=life["load_eq_N"], L10h=life["L10h"], s0=PART["C0_N"] / (0.5 * Fa),
                          friction_W=W, friction_W_high=W_hi, k_hertz_N_per_m=RM.bearing_k(Fa),
                          k_seat_N_per_m=1.0 / (1.0 / RM.bearing_k(Fa) + 1.0 / K_SPIDER), note=note)
    put("bottom bridge-ring bearing (A), locating the counter-rotor", W_cr, n_rel, "the counter-rotor's weight")
    put("top bridge-ring bearing (B), floating", PRELOAD_N, n_rel, "the spring preload")
    put("bottom end bearing (A, frame), locating both bodies", W_cr + W_r, n_abs, "both bodies' weight")
    # handling: 1 g lateral, the machine on its side (the axial weight then gone) [OC: the two-body statics]
    lat = {k: dict(Fr_N=abs(v), s0=PART["C0_N"] / max(abs(v), 1e-9)) for k, v in r["bearing_loads_1g_N"].items()}
    # SKF's minimum load, radial: Frm = kr (nu n / 1000)^(2/3) (dm / 100)^2 kN; the axial preload stands in for it
    Frm = {f"{nu:.0f} mm2/s": PART["kr"] * (nu * n_rel / 1000.0) ** (2 / 3) * (RM.BRG_6205["dm"] / 100.0) ** 2 * 1e3
           for nu in (30.0, 70.0)}
    pre = {f"{F:.0f} N": dict(k_hertz_N_per_m=RM.bearing_k(F), friction_W=RM.palmgren_W(n_rel, 1.0, 30.0, Fa=F, b=b)[0])
           for F in (100.0, 125.0, 150.0, 250.0)}
    added = rows["bottom bridge-ring bearing (A), locating the counter-rotor"]["friction_W"] + \
        rows["top bridge-ring bearing (B), floating"]["friction_W"]
    # the windage the new spiders change [IR: the record's correlations and conventions, sim/rotor_mechanics.py
    # windage]: the bridge rings' ends no longer face the frame's spiders (6 mm); the new spiders do (12 mm, at the
    # counter-rotor's speed); the outer carrier discs face a counter-rotating spider (15 mm, the relative speed)
    # instead of the frame's
    w = 2 * math.pi * RM.RPM / 60.0
    wr, _ = ring_section(st)
    disc = [e for e in st["record_reluctance"] if e["side"] == "A" and e["kind"] == "w disc"][0]
    pl = placement(st)
    sp = pl["side_A"]["spider"]
    gap_frame = sp["z0"] - (pl["z_frame_mm"][0] + 0.5 * SPIDER_T)
    gap_disc = min(e["z0"] for e in st["record_reluctance"] if e["side"] == "A" and e["kind"] == "w disc") + SLOT - sp["z1"]
    crf = 0.72
    P_ringend = RM.disc_gap_W(wr["r1"] * 1e-3, wr["r0"] * 1e-3, 0.006, w)[0]
    P_spider = RM.disc_gap_W(sp["r1"] * 1e-3, sp["r0"] * 1e-3, gap_frame * 1e-3, w)[0]
    P_disc_w = RM.disc_gap_W(disc["r1"] * 1e-3, S.SLEEVE_R * 1e-3, gap_disc * 1e-3, w)[0]
    P_disc_Om = RM.disc_gap_W(disc["r1"] * 1e-3, S.SLEEVE_R * 1e-3, gap_disc * 1e-3, 2 * w)[0]
    windage = dict(ring_ends_gone_W=-2 * crf * P_ringend, spiders_to_frame_W=2 * crf * P_spider,
                   outer_discs_W=2 * (P_disc_Om - P_disc_w), gap_frame_mm=gap_frame, gap_disc_mm=gap_disc)
    windage["net_W"] = windage["ring_ends_gone_W"] + windage["spiders_to_frame_W"] + windage["outer_discs_W"]
    return dict(masses_kg=dict(rotor=r["m_rotor_kg"], counter_rotor=r["m_counter_rotor_kg"]), bearings=rows,
                handling_1g=lat, min_load_radial_N=Frm, preload_rule_N=[k * PART["d_mm"] * 1e3 for k in (0.005, 0.01)],
                preloads=pre, speed=dict(n_rel_rpm=n_rel, n_lim_rpm=PART["n_lim_rpm"], frac=n_rel / PART["n_lim_rpm"],
                                         ndm=n_rel * RM.BRG_6205["dm"]), friction_added_W=added, windage=windage,
                ratings_record=dict(c_dyn=RM.BRG_6205["c_dyn"], c_stat=RM.BRG_6205["c_stat"], f0=RM.BRG_6205["f0"]))


# ---------------------------------------------------------------------------------------------------- the figure
def figure(sh, pl):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    INK, INK2, GRID = "#1d1d1f", "#52514e", "#d9d8d3"
    MODE = ("#2a78d6", "#eb6834", "#1baf7a")        # categorical slots 1-3 (validated all-pairs, both modes)
    fig = plt.figure(figsize=(13.5, 6.2))
    ax = fig.add_axes((0.06, 0.12, 0.40, 0.76))
    for d, ls in (("25", "-"), ("30", (0, (4, 2)))):
        sw = sh["sweep"][d]
        k = np.asarray(sw["k_b_N_per_m"])
        f = np.asarray(sw["f_Hz"])
        for j in range(3):
            ax.plot(k, f[:, j], color=MODE[j], lw=2.0, ls=ls, solid_capstyle="round")
        ax.text(k[-1] * 1.04, f[-1, 0], f"d {d}", fontsize=8, color=INK2, va="center")
    for j in range(3):
        f = np.asarray(sh["sweep"]["25"]["f_Hz"])
        ax.text(sh["sweep"]["25"]["k_b_N_per_m"][0] * 0.96, f[0, j], f"mode {j + 1}", fontsize=8, color=MODE[j], ha="right",
                va="center", fontweight="bold")
    for y, t in ((sh["criterion_f1_Hz"], "the criterion: 3 x 20 Hz"), (120.0, "the pumps: 120 Hz"), (240.0, "240 Hz")):
        ax.axhline(y, color=INK2, lw=0.8, ls=(0, (2, 2)), zorder=1)
        ax.text(5.2e8, y + 3, t, fontsize=8, color=INK2, ha="right", va="bottom")
    for x, t in ((K_REAL, "G10 spider\n(the record's 0.86e8)"), (2e8, "stiff seat\n(2e8)")):
        ax.axvline(x, color=GRID, lw=1.0, zorder=0)
        ax.text(x, 8, t, fontsize=7.5, color=INK2, ha="center", va="bottom")
    ax.set_xscale("log"); ax.set_xlim(2.2e7, 6e8); ax.set_ylim(0, 300)
    ticks = [3e7, 5e7, 1e8, 2e8, 5e8]
    ax.set_xticks(ticks); ax.set_xticklabels([f"{t / 1e8:g}e8" for t in ticks]); ax.minorticks_off()
    ax.set_xlabel("each bearing's radial seat stiffness k_b [N/m]", fontsize=9, color=INK)
    ax.set_ylabel("the two bodies' bending modes [Hz]", fontsize=9, color=INK)
    ax.tick_params(labelsize=8, colors=INK2)
    for s_ in ("top", "right"):
        ax.spines[s_].set_visible(False)
    ax.grid(True, which="major", color=GRID, lw=0.5)
    ax.set_title("(a) the first three modes against the seats' stiffness: d 25 (solid), d 30 (dashed)", fontsize=10,
                 loc="left", color=INK)
    # (b) the mode shapes
    bx = fig.add_axes((0.56, 0.12, 0.42, 0.76))
    m = sh["shapes_d25_real"]
    z = np.asarray(m["z_mm"])
    for j, md in enumerate(m["modes"]):
        ws, wc = np.asarray(md["w_shaft"]), np.asarray(md["w_counter_rotor"])
        off = -2.4 * j
        bx.plot(z, off + ws, color=MODE[j], lw=2.0)
        inside = np.abs(wc) > 0
        zc_ = np.where(inside, z, np.nan)
        bx.plot(zc_, off + np.where(inside, wc, np.nan), color=MODE[j], lw=1.4, ls=(0, (3, 2)))
        bx.text(z[-1] + 12, off, f"mode {j + 1}\n{md['f_Hz']:.0f} Hz", fontsize=8.5, color=MODE[j], va="center",
                fontweight="bold")
        bx.axhline(off, color=GRID, lw=0.5, zorder=0)
    for kind, mk, t in (("frame", "^", "end bearing (frame)"), ("inner", "o", "Ca|reluctance bearing"),
                        ("ring", "D", "bridge-ring bearing")):
        zz = m["bearings"][kind]
        bx.plot(zz, [1.3] * len(zz), mk, color=INK, ms=6, ls="none", label=t)
    for zp in m["utron_planes"]:
        bx.axvspan(zp - 50, zp + 50, color="#f1efe8", zorder=0)
    bx.text(m["utron_planes"][0], -6.6, "utrons A", fontsize=7.5, color=INK2, ha="center")
    bx.text(m["utron_planes"][-1], -6.6, "utrons B", fontsize=7.5, color=INK2, ha="center")
    bx.set_xlim(-10, z[-1] + 110); bx.set_ylim(-7.0, 2.5)
    bx.set_yticks([])
    bx.set_xlabel(f"z from side A's end [mm] ({pl['L_mm']:.0f} mm)", fontsize=9, color=INK)
    bx.tick_params(labelsize=8, colors=INK2)
    for s_ in ("top", "right", "left"):
        bx.spines[s_].set_visible(False)
    bx.legend(loc="upper center", bbox_to_anchor=(0.45, 1.01), ncol=3, fontsize=8, frameon=False, handletextpad=0.3)
    bx.set_title("(b) the mode shapes, d 25 on G10 spiders: shaft solid, counter-rotor dashed",
                 fontsize=10, loc="left", color=INK)
    fig.suptitle(f"The bridge-ring bearings as drawn ({PART['maker']} {PART['designation']}, PROPOSED): the shafts' modes "
                 f"(sim/bridge_ring_bearings.py)", fontsize=11.5, x=0.01, ha="left", color=INK)
    fig.savefig(FIG, dpi=130)
    plt.close(fig)
    return os.path.relpath(FIG, ROOT)


# ---------------------------------------------------------------------------------------------------- main
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--no-solids", action="store_true")
    a = ap.parse_args()
    log = lambda s: print(s, flush=True)
    t0 = time.time()
    st = json.load(open(LAYOUT_JSON))["stack"]
    pl = placement(st)
    log(f"1. the placement: {pl['L_layout_mm']:.0f} -> {pl['L_mm']:.0f} mm; the bridge-ring bearings at z "
        f"{pl['z_ring_mm'][0]:.0f} / {pl['z_ring_mm'][1]:.0f}, the end bearings at {pl['z_frame_mm'][0]:.0f} / "
        f"{pl['z_frame_mm'][1]:.0f}; the spider {pl['clear_spider_to_turns_mm']:.1f} mm from the end turns")
    out = dict(note=__doc__.split("\n\n")[0], sources=SRC, tags="CONVENTIONS.md §1", status="PROPOSED (2026-10-11)",
               part=PART, alternates=ALTERNATES, placement=pl)
    out["part_gate"] = dict(
        envelope_ok=bool((PART["d_mm"], PART["D_mm"], PART["B_mm"]) == (2 * S.SHAFT_R, S.BEARING["od"], S.BEARING["width"])),
        ratings_ok=None)
    log("2. the shafts")
    sh, (lad1, parts1, ring1) = shafts(st, log)
    out["shafts"] = sh
    if not a.no_solids:
        log("3. the cross-check on the drawn solids")
        out["cross_check"] = cross_check(st, lad1, parts1, ring1, log)
    log("4. the duty")
    out["duty"] = du = duty(sh, st)
    rr = du["ratings_record"]
    out["part_gate"]["ratings_ok"] = bool(rr["c_dyn"] == PART["C_N"] and rr["c_stat"] == PART["C0_N"] and rr["f0"] == PART["f0"])
    for k, v in du["bearings"].items():
        log(f"  {k}: Fa {v['Fa_N']:.0f} N at {v['n_rpm']:.0f} rpm, L10 {v['L10h']:.3g} h, friction {v['friction_W']:.2f} W "
            f"({v['friction_W_high']:.2f} high), k {v['k_hertz_N_per_m']:.2e} N/m (seat {v['k_seat_N_per_m']:.2e})")
    log(f"  windage: {du['windage']['net_W']:+.3f} W net ({', '.join(f'{k} {v:+.3f}' for k, v in du['windage'].items() if k.endswith('_W') and k != 'net_W')})")
    out["figure"] = figure(sh, pl)
    d25 = [x for x in sh["rows"] if x["d_mm"] == 25.0]
    out["gates"] = {
        "G1 the layout study's shaft model, copied": dict(ok=sh["gate_copy"]["ok"], worst_rel=sh["gate_copy"]["worst_rel"]),
        "G2 the part fits the record's slot and ratings": dict(ok=bool(out["part_gate"]["envelope_ok"] and out["part_gate"]["ratings_ok"])),
        "G3 d 25 meets 3 x 20 Hz on stiff and G10 seats": dict(ok=bool(all(x["ok"] for x in d25)),
                                                             f1_Hz=[x["f1_Hz"] for x in d25]),
    }
    if "cross_check" in out:
        cc = out["cross_check"]
        out["gates"]["G4 the drawn solids: the placement, and f1 within 5 %"] = dict(ok=cc["ok"], worst_dev_f1=cc["worst_dev_f1"],
                                                                                   place_ok=cc["place_ok"])
    out["run_s"] = round(time.time() - t0)
    json.dump(out, open(OUT_JSON, "w"), indent=1, default=float)
    for k, v in out["gates"].items():
        log(f"{k}: {'PASS' if v['ok'] else 'FAIL'}")
    log(f"wrote {os.path.relpath(OUT_JSON, ROOT)}, {out['figure']} ({out['run_s']} s)")


if __name__ == "__main__":
    main()
