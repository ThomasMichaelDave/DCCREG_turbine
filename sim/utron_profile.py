"""sim/utron_profile.py -- the wound utron and its passive stator bridge as dimensioned parts: one source for the solids
(sim/tube_geometry.py --rel wound) and the detail drawing (docs/make_utron_drawing.py).

Local frame of one utron: u radial (mm from the machine axis, along the utron's centre line), v tangential (mm), w axial
(mm from the lamination stack's lower end). The magnetic section is the 2-D model's (sim/pole_fd2d.Design: tips w_p,
slot s x d, back iron b, coil clearance clr, gap g at r_g, stack L_stk) [OC: the solved section]; the build details are
first-cut choices [IR/RH]:
  * core: two L-shaped half-cores of M235-35A laminations (tip + half back iron), stacked axially; the tip faces lie on
    the gap arc r_g (cut or ground after stacking), the tips are parallel-sided so the slot keeps its width s [IR];
  * neck (sets Psi_s): a laminated 80 % NiFe strip under the back iron, full core width; the half-cores sit on it and are
    parted by a G10-filled air break, so the flux has to cross the strip. Strip thickness from the operating point's
    saturation flux at B_NIFE, rounded to whole 0.1 mm NiFe laminations (the saturation flux follows the built strip)
    [RH: B_sat 0.75 T at ~60 C; the two lap joints add ~3 % to the aligned reluctance; with a
    12 mm break the saturated incremental L is ~5 % of aligned and ~30 % of unaligned. The 2-D model has linear SiFe and
    the ^6 law at Psi_s instead, so this needs a nonlinear field check]. The check (sim/neck-nonlinear-findings.md,
    2026-10-09): the built flux takes a stacking factor of 1 (at 0.90 the knee is 5 % lower), the laps cost 11 % of the
    aligned L (the foils lie across the radius), and past the knee the incremental L is 12.8 % / 52 %;
  * coil: one coil on the back iron between the tips (+ side in the slot, - side under the core) with rounded-rectangle
    turns (inner corner radius clr, outer clr + h_c) at 50 % fill, wound on a 1 mm G10 former (the clearance clr);
  * slot cover: G10 between the tips' inner faces, its flat bottom 0.1 mm above the coil, its top on the gap arc less
    0.2 mm; bonded in the vacuum impregnation, with no grooves (grooves at the slot edge would leave a 0.1-0.2 mm sliver
    of lamination at the tip corner). The coil needs no wedge to stay put: it is a closed loop around the back iron, so its
    slot side is carried by the loop (it bends ~0.001 mm under the 600 rpm load) [OC: beam estimate; RH: the
    impregnated bundle's stiffness];
  * cheeks: G10 plates on both stack ends over each tip, outside the coil, held by two A4 M6 studs (Ø 6.4 clearance
    holes, ISO 273 fine) through each half-core and bolted to the rotor's carrier disc, one disc per stack end [IR];
  * bridge: an M235-35A annular sector from r_g + g to r_g + g + t_b, with arc length l_b at its face, standing 1 mm proud
    of the bore of a G10 bridge ring (the counter-rotor) [IR].
Pure python (no numpy): numbers, rectangles (u0, u1, v0, v1) and polylines.
"""
import math

B_NIFE, NIFE_LAM = 0.75, 0.1  # T, 80 % NiFe at ~60 C [RH]; the strip is a stack of 0.1 mm laminations
BRK = 12.0                    # mm, air break in the back iron (G10 spacer) [RH]
WEDGE_LIFT, COVER_DROP = 0.1, 0.2   # G10 slot cover: lift off the coil, its top below the gap arc
T_CHEEK, T_DISC = 10.0, 12.0  # G10 cheek plate and carrier disc thicknesses (axial)
CHEEK_LAP = 14.0              # cheek root below the carrier disc's rim (bolted face to face)
RING_T, PROUD = 12.0, 1.0     # G10 bridge ring outside the bridges; bridge face proud of the ring bore
SP = 3.0                      # axial clearance from the end turns to the section ends
STUD_D = 6.4                  # holes for the A4 M6 studs through the half-cores and cheeks (ISO 273 fine)
FILL, RHO_CU, RHO_FE, RHO_NIFE, RHO_G10, RHO_CU_KG = 0.50, 1.72e-8, 7650.0, 8700.0, 1850.0, 8900.0
SLEEVE_R = 20.5


def spec(design, op=None, row=None, L_stk=None, n_u=3):
    """every dimension of one utron + bridge set from the pole design dict (sim/pole_design_variants_op.json 'design'),
    its operating point ('best') and its characterised row (L_al, L_un, ...)."""
    d = dict(design)
    r_g, g, w_p, s, dd = (float(d[k]) for k in ("r_g", "g", "w_p", "s", "d"))
    b = float(d.get("b") or w_p)
    L = float(L_stk or d.get("L_stk") or 100.0)
    clr = float(d.get("clr", 1.0))
    n_br = int(d.get("n_br", 6))
    t_b = float(d.get("t_b") or w_p)
    W_u = 2 * w_p + s
    l_b = float(d.get("l_b") or W_u)
    cv = s / 2 - clr                                   # coil half-width (tangential)
    u_p0, u_p1 = r_g - dd + clr, r_g - 2.0             # + side (pole_fd2d.Design.coil_rects)
    h_c = u_p1 - u_p0
    u_y0, u_y1 = r_g - dd - b, r_g - dd                # back iron
    u_m1 = u_y0 - clr
    u_m0 = u_m1 - h_c                                  # - side
    depth = r_g - (u_m0 - clr)                         # pole_fd2d.Design.radial_depth
    over = clr + h_c                                   # end-turn overhang beyond the stack
    u_w0 = u_p1 + WEDGE_LIFT
    v_w = s / 2
    u_w1 = math.sqrt((r_g - COVER_DROP) ** 2 - v_w ** 2)              # the slot cover's height at the tips' inner faces
    u_arc_tip = math.sqrt(r_g ** 2 - (s / 2 + w_p) ** 2)     # the gap arc at the tip's outer edge
    r_disc = u_m0 - clr
    sp = dict(r_g=r_g, g=g, w_p=w_p, s=s, d=dd, b=b, L=L, clr=clr, n_br=n_br, t_b=t_b, W_u=W_u, l_b=l_b, n_u=n_u,
              cv=cv, u_p0=u_p0, u_p1=u_p1, h_c=h_c, u_y0=u_y0, u_y1=u_y1, u_m0=u_m0, u_m1=u_m1, depth=depth, over=over,
              u_w0=u_w0, u_w1=u_w1, v_w=v_w, u_arc_tip=u_arc_tip, brk=BRK, r_disc=r_disc, t_cheek=T_CHEEK, t_disc=T_DISC,
              u_ch0=r_disc - CHEEK_LAP, u_ch1=u_arc_tip - 1.0,
              r_br0=r_g + g, r_br1=r_g + g + t_b, br_deg=math.degrees(l_b / (r_g + g)),
              r_ring0=r_g + g + PROUD, r_ring1=r_g + g + t_b + RING_T, sp=SP, L_rel=L + 2 * (over + SP),
              stud_d=STUD_D, t_wedge=u_w1 - u_w0)
    # the neck: saturation flux per utron from the operating point (group Psi_s over 3 coils of N_u turns)
    if op:
        phi_s = op["psi_s"] / (n_u * op["N_u"])
        t_exact = phi_s / (B_NIFE * L * 1e-3) * 1e3
        t_n = max(NIFE_LAM, round(t_exact / NIFE_LAM) * NIFE_LAM)     # whole 0.1 mm laminations
        sp.update(phi_s_Wb=phi_s, t_n_exact=t_exact, t_n=t_n, n_nife=int(round(t_n / NIFE_LAM)),
                  phi_s_built_Wb=B_NIFE * t_n * L * 1e-6, neck_sife_mm=op.get("neck_mm"), N_u=op["N_u"])
    else:
        sp.update(phi_s_Wb=None, t_n=0.25 * b, N_u=None)
    sp["u_n1"] = u_y0 + sp["t_n"]                      # bottom of the half-cores (top of the strip)
    assert sp["t_n"] < 0.5 * b, "neck strip thicker than half the back iron"
    # studs: one in the tip / back-iron corner, one in the tip, centred on the tip (positions on a 0.5 mm grid)
    v_st = s / 2 + w_p / 2
    half = lambda x: round(2.0 * x) / 2.0
    sp["studs"] = [(sp["u_n1"] + half(0.5 * (u_y1 - sp["u_n1"])), v_st),
                   (sp["u_n1"] + half(u_y1 + 0.45 * (u_arc_tip - u_y1) - sp["u_n1"]), v_st)]
    sp.update(_derived(sp, op, row))
    return sp


def mean_turn(sp):
    """rounded-rectangle turn at mid-build around the back iron (= pole_fd2d.mean_turn_mm)."""
    return 2 * (sp["L"] + sp["b"]) + 2 * math.pi * (sp["clr"] + sp["h_c"] / 2)


def _area(poly):
    a = 0.0
    for (u0, v0), (u1, v1) in zip(poly, poly[1:] + poly[:1]):
        a += u0 * v1 - u1 * v0
    return abs(a) / 2


def _derived(sp, op, row):
    """masses, the winding, the electrical numbers."""
    L = sp["L"]
    a_coil = 2 * sp["cv"] * sp["h_c"]
    lt = mean_turn(sp)
    hc_a = _area(half_core(sp, +1, arc=True)) - 2 * math.pi * (sp["stud_d"] / 2) ** 2
    out = dict(a_coil_mm2=a_coil, l_turn_mm=lt,
               m_sife_kg=2 * hc_a * L * 1e-9 * RHO_FE,
               m_nife_kg=sp["W_u"] * sp["t_n"] * L * 1e-9 * RHO_NIFE,
               m_cu_kg=a_coil * FILL * lt * 1e-9 * RHO_CU_KG,
               m_g10_kg=(sp["brk"] * (sp["u_y1"] - sp["u_n1"]) + _area(wedge(sp))) * L * 1e-9 * RHO_G10
               + 4 * (sp["u_ch1"] - sp["u_ch0"]) * sp["w_p"] * sp["t_cheek"] * 1e-9 * RHO_G10,
               axial_mm=L + 2 * sp["over"])
    out["m_utron_kg"] = out["m_sife_kg"] + out["m_nife_kg"] + out["m_cu_kg"] + out["m_g10_kg"]
    ring_a = math.pi * (sp["r_ring1"] ** 2 - sp["r_ring0"] ** 2)
    br_a = math.radians(sp["br_deg"]) / 2 * (sp["r_br1"] ** 2 - sp["r_br0"] ** 2)
    out["m_bridge_kg"] = br_a * L * 1e-9 * RHO_FE
    out["m_disc_kg"] = math.pi * (sp["r_disc"] ** 2 - SLEEVE_R ** 2) * sp["t_disc"] * 1e-9 * RHO_G10
    if op:
        N = op["N_u"]
        aw = FILL * a_coil / N
        out.update(wire_mm2=aw, wire_d_mm=math.sqrt(4 * aw / math.pi), R_coil_ohm=RHO_CU * N * lt * 1e-3 / (aw * 1e-6),
                   I_pk_A=op.get("I_pk"), I_rms_A=op.get("I_rms"), V_pk_V=op.get("V_pk"), L_group_H=op.get("L_group_H"))
        if row:
            out.update(L_al_coil_H=N ** 2 * row["L_al"], L_un_coil_H=N ** 2 * row["L_un"], kappa=row["kappa"], tau_s=row["tau"])
    return out


def half_core(sp, side=+1, arc=True, n_arc=48):
    """closed polyline (u, v) of one L-shaped half-core (side +1: v > 0). arc=False replaces the tip face by a straight
    edge 2 mm beyond r_g (the solid builder then cuts it with the gap cylinder)."""
    s2, wp, r_g = sp["s"] / 2, sp["w_p"], sp["r_g"]
    pts = [(sp["u_n1"], sp["brk"] / 2), (sp["u_y1"], sp["brk"] / 2), (sp["u_y1"], s2)]
    if arc:
        for k in range(n_arc + 1):
            v = s2 + wp * k / n_arc
            pts.append((math.sqrt(r_g ** 2 - v ** 2), v))
    else:
        pts += [(r_g + 2.0, s2), (r_g + 2.0, s2 + wp)]
    pts.append((sp["u_n1"], s2 + wp))
    return [(u, side * v) for u, v in pts]


def wedge(sp, n_arc=32):
    """closed polyline (u, v) of the G10 slot cover: flat bottom just above the coil, sides on the tips' inner faces,
    the top on the arc r_g - COVER_DROP."""
    s2, r = sp["s"] / 2, sp["r_g"] - COVER_DROP
    top = [(math.sqrt(r ** 2 - v ** 2), v) for v in (s2 - 2 * s2 * k / n_arc for k in range(n_arc + 1))]
    return [(sp["u_w0"], -s2), (sp["u_w0"], s2)] + top


def rects(sp):
    """the remaining (u, v) sections (u0, u1, v0, v1), extruded over the stack w 0..L, plus the coil sides."""
    cv, W2 = sp["cv"], sp["W_u"] / 2
    return dict(strip=(sp["u_y0"], sp["u_n1"], -W2, W2),
                spacer=(sp["u_n1"], sp["u_y1"], -sp["brk"] / 2, sp["brk"] / 2),
                wedge=(sp["u_w0"], sp["u_w1"], -sp["v_w"], sp["v_w"]),
                coil_plus=(sp["u_p0"], sp["u_p1"], -cv, cv),
                coil_minus=(sp["u_m0"], sp["u_m1"], -cv, cv),
                cheek_pos=(sp["u_ch0"], sp["u_ch1"], sp["s"] / 2, sp["s"] / 2 + sp["w_p"]),
                cheek_neg=(sp["u_ch0"], sp["u_ch1"], -sp["s"] / 2 - sp["w_p"], -sp["s"] / 2))


def coil_ring(sp):
    """the winding in the (u, w) plane: outer and inner rounded rectangles (u0, u1, w0, w1, radius); width 2 cv in v."""
    L, c, o = sp["L"], sp["clr"], sp["over"]
    return dict(outer=(sp["u_m0"], sp["u_p1"], -o, L + o, o), inner=(sp["u_m1"], sp["u_p0"], -c, L + c, c))


def rounded_rect(u0, u1, w0, w1, R, n=12):
    """closed polyline of a rounded rectangle (for drawings)."""
    pts = []
    for (cu, cw, a0) in ((u1 - R, w1 - R, 0), (u0 + R, w1 - R, 90), (u0 + R, w0 + R, 180), (u1 - R, w0 + R, 270)):
        for k in range(n + 1):
            a = math.radians(a0 + 90 * k / n)
            pts.append((cu + R * math.cos(a), cw + R * math.sin(a)))
    return pts


if __name__ == "__main__":
    import json
    import os
    here = os.path.dirname(os.path.abspath(__file__))
    op = json.load(open(os.path.join(here, "pole_design_variants_op.json")))["designs"]
    for tag, rec in op.items():
        if not rec.get("best"):
            continue
        sp = spec(rec["design"], rec["best"])
        print(tag, {k: round(v, 3) for k, v in sp.items() if isinstance(v, float)})
