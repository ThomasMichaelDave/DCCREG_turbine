"""docs/make_integrated_multiplier_schematic.py -- writes docs/schematic-integrated-multiplier.{svg,png}: the multiplier
stacked into the doubler (the designer's sketch of 2026-10-10) as sim/integrated_multiplier.py proposes it, the rings'
supply taken from it:
  the designer's ladder (C3-C6, D5-D8) drawn as the sketch draws it, two capacitor columns on nodes 2 / 3 with the
  diodes crossing between them; run bipolar (chain 2 reversed: D2, D4, D5, D8), with C1 / C2 in phase, each chain
  continued one stage past its varicap node to its ring (C7 / C8, D9-D12) and each ring on a smoothing capacitor to the
  shaft; every node's swing, every diode's reverse peak and every capacitor's DC from the as-built steady state of the
  pick; the hub with the rings and the field at the null.
Usage: python3 docs/make_integrated_multiplier_schematic.py   (the PNG needs playwright + chromium)
"""
import json
import math
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
import make_schematic_rotor as SR        # noqa: E402  (its SVG primitives write into SR.o)
import make_rings_supply_schematic as RS  # noqa: E402  (the style sheet and the hub)

OUT = os.path.join(HERE, "schematic-integrated-multiplier")
o = SR.o
ln, pl, tx, dot, diode, cap_v, ground, box, kv, table = (SR.ln, SR.pl, SR.tx, SR.dot, SR.diode, SR.cap_v, SR.ground,
                                                         SR.box, SR.kv, SR.table)
POS, NEG = "#1f6fb2", "#c0392b"          # the chain to ring B (positive), the chain to ring A (negative)


def ddiode(a, k, col, t=0.5, hop=None):
    """a diode on the straight wire from its anode a to its cathode k (any angle), its symbol at the fraction t along
    it; hop: a point on the wire where it bridges another wire (a half circle of 7 px). Returns the symbol's centre."""
    (x0, y0), (x1, y1) = a, k
    L = math.hypot(x1 - x0, y1 - y0)
    ux, uy = (x1 - x0) / L, (y1 - y0) / L
    xm, ym = x0 + t * (x1 - x0), y0 + t * (y1 - y0)
    s0, s1 = (xm - 9 * ux, ym - 9 * uy), (xm + 9 * ux, ym + 9 * uy)
    segs = [((x0, y0), s0), (s1, (x1, y1))]
    if hop:
        hx, hy = hop
        out = []
        for p_, q_ in segs:                                # split the segment that holds the hop
            tt = (hx - p_[0]) * ux + (hy - p_[1]) * uy
            if 0 < tt < math.hypot(q_[0] - p_[0], q_[1] - p_[1]):
                h0, h1 = (hx - 7 * ux, hy - 7 * uy), (hx + 7 * ux, hy + 7 * uy)
                out += [(p_, h0), (h1, q_)]
                o.append(f'<path d="M{h0[0]:.1f} {h0[1]:.1f} A7 7 0 0 {1 if ux >= 0 else 0} {h1[0]:.1f} {h1[1]:.1f}" '
                         f'fill="none" stroke="{col}" stroke-width="1.8"/>')
            else:
                out.append((p_, q_))
        segs = out
    for p_, q_ in segs:
        o.append(f'<line x1="{p_[0]:.1f}" y1="{p_[1]:.1f}" x2="{q_[0]:.1f}" y2="{q_[1]:.1f}" stroke="{col}" '
                 'stroke-width="1.8"/>')
    ang = math.degrees(math.atan2(uy, ux))
    o.append(f'<g transform="rotate({ang:.2f} {s0[0]:.1f} {s0[1]:.1f})">')
    diode(s0[0], s0[1], "right", col)
    o.append("</g>")
    return xm, ym


def dlabel(x, y, name, vr, col, anchor="middle"):
    """a diode's name (in its chain's colour) and reverse peak on one line."""
    o.append(f'<text x="{x:.1f}" y="{y:.1f}" class="t" text-anchor="{anchor}"><tspan font-weight="bold" fill="{col}">'
             f'{name}</tspan> <tspan class="ms" font-size="12">{vr:.1f} kV</tspan></text>')


def vcap(x, y0, y1, name, val, side=1, var=False):
    """a capacitor in the vertical wire x from y0 to y1, its plates centred; its name and value (and DC) beside it."""
    ym = 0.5 * (y0 + y1) - 5
    ln(x, y0, x, ym); ln(x, ym + 10, x, y1)
    cap_v(x, ym)
    if var:
        SR.var_arrow(x, ym + 5)
    a = "start" if side > 0 else "end"
    tx(x + side * 26, ym + 1, name, "t", a, 'font-weight="bold"')
    tx(x + side * 26, ym + 15, val, "ms", a)


def hcap(x0, x1, y, label):
    xm = 0.5 * (x0 + x1) - 5
    ln(x0, y, xm, y); ln(xm + 10, y, x1, y)
    SR.cap_h(xm, y, 12)
    tx(xm + 5, y - 20, label, "t", "middle")


def sv(v):
    """a level with its sign: a real minus, a plus, and no negative zero."""
    v = 0.0 if abs(v) < 0.05 else v
    return ("+" if v > 0 else "") + kv(v)


def nlabel(x, y, name, lv, anchor="start"):
    o.append(f'<text x="{x:.1f}" y="{y:.1f}" class="ms" text-anchor="{anchor}"><tspan font-weight="bold">{name}</tspan> '
             f'{sv(lv[0])} ↔ {sv(lv[1])} kV</text>')


def main():
    R = json.load(open(os.path.join(ROOT, "sim", "integrated_multiplier_results.json")))
    H_ = json.load(open(os.path.join(ROOT, "sim", "hub_rings_build_results.json")))
    rec = H_["record"]
    pick = R["pick"]
    s = pick["steady"]
    V, VR, VC = s["V_kV"], s["VR_pk_kV"], s["VC_kV"]
    vdc = lambda c: max(abs(VC[c][0]), abs(VC[c][1]))
    cl_pf = pick["C3_C6_pF"]
    cmin, cmax, ca_pf = R["set_ab_pF"]["cmin"], R["set_ab_pF"]["cmax"], R["set_ab_pF"]["ca"]
    sup = R["as_built"]["record_supply_as_built"]
    re_ = R.get("real", {})
    W, Hh = 1440, 1030
    o.clear()
    o.append(f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {Hh}" width="{W}" height="{Hh}" '
             'font-family="DejaVu Sans, Arial, sans-serif" font-size="13">')
    o.append("<title>Integrated multiplier</title>")
    o.append(f'<rect width="{W}" height="{Hh}" fill="#ffffff"/>')
    o.append(RS.style_block())
    tx(20, 30, "DCCREG turbine: the multiplier stacked into the doubler, run bipolar, feeding the rings — PROPOSED "
               "(2026-10-10)", "h")
    tx(20, 52, "The designer's ladder C3–C6 / D5–D8 as sketched; chain 2 reversed (D2, D4, D5, D8): side A negative, side B "
               "positive; C1 / C2 in phase; one stage past each varicap node to its ring. As built, ideal diodes.", "m")
    box(20, 70, 1400, 720, "frame")
    tx(40, 92, "blue: the chain that charges ring B (side B, positive) · red: the chain that charges ring A (side A, "
               "negative) · rev.: reversed against the sketch · new: added for the rings", "ms")
    x1, xL, xR, x4 = 200, 440, 660, 900
    y_ra, y_r, y_x, y_t, y_b, y_a, y_n, y_ref = 108, 128, 196, 278, 392, 505, 620, 742
    yg = y_n + 64                                                 # the shaft's ground symbols
    ax_, bx = x1 + 130, x4 - 130
    # the varicaps, in phase, to the counter-rotor's stator vanes (REF); REF reaches the shaft through the link
    vcap(x1, y_n, y_ref, "C1", f"{cmin:.0f}–{cmax:.0f} pF", side=1, var=True)
    vcap(x4, y_n, y_ref, "C2", f"{cmin:.0f}–{cmax:.0f} pF", side=-1, var=True)
    tx(x1 + 26, 0.5 * (y_n + y_ref) + 24, "side A", "ms", "start")
    tx(x4 - 26, 0.5 * (y_n + y_ref) + 24, "side B, in phase with C1", "ms", "end")
    ln(x1, y_ref, x4, y_ref)
    tx(0.5 * (x1 + x4), y_ref + 17, "REF: the counter-rotor's stator vanes; one inner bearing to the shaft carries "
                                     f"{1e3 * s['link_mA_rms']:.2f} µA rms (the record's {1e3 * sup['link_mA_rms']:.0f} µA)",
       "ms", "middle")
    # nodes 1-4, Ca / Cb, D1 / D2 to the shaft, the clamps outside
    hcap(x1, xL, y_n, f"<tspan font-weight='bold'>Ca</tspan> {ca_pf:.0f} pF · {vdc('Ca'):.1f} kV")
    hcap(xR, x4, y_n, f"<tspan font-weight='bold'>Cb</tspan> {ca_pf:.0f} pF · {vdc('Cb'):.1f} kV")
    for x_ in (x1, xL, xR, x4):
        dot(x_, y_n)
    ddiode((xL, yg), (xL, y_n), POS)
    ground(xL, yg)
    dlabel(xL - 14, y_n + 46, "D1", VR["D1"], POS, "end")
    ddiode((xR, y_n), (xR, yg), NEG)
    ground(xR, yg)
    dlabel(xR + 14, y_n + 46, "D2 rev.", VR["D2"], NEG, "start")
    zx1, zx4 = x1 - 80, x4 + 80
    pl([(x1, y_n), (zx1, y_n), (zx1, y_n + 22)])
    diode(zx1, y_n + 22, "down", "#111", zener=True)
    ln(zx1, y_n + 40, zx1, yg); ground(zx1, yg)
    tx(zx1 - 14, y_n + 30, "Z1", "t", "end", 'font-weight="bold"')
    tx(zx1 - 14, y_n + 44, f"{kv(-R['V_op_kV'])} kV", "ms", "end")
    pl([(x4, y_n), (zx4, y_n), (zx4, y_n + 22)])
    diode(zx4, y_n + 40, "up", "#111", zener=True)
    ln(zx4, y_n + 40, zx4, yg); ground(zx4, yg)
    tx(zx4 + 14, y_n + 30, "Z4", "t", "start", 'font-weight="bold"')
    tx(zx4 + 14, y_n + 44, f"+{R['V_op_kV']:.1f} kV", "ms", "start")
    nlabel(x1 - 12, y_n - 12, "1", V["1"], "end")
    nlabel(xL - 12, y_n + 20, "2", V["2"], "end")
    nlabel(xR + 12, y_n + 20, "3", V["3"], "start")
    nlabel(x4 + 12, y_n - 12, "4", V["4"], "start")
    # the two columns
    vcap(xL, y_n, y_a, "C3", f"{cl_pf:.0f} pF · {vdc('C3'):.1f} kV", side=-1)
    vcap(xL, y_a, y_b, "C5", f"{cl_pf:.0f} pF · {vdc('C5'):.1f} kV", side=-1)
    vcap(xR, y_n, y_a, "C4", f"{cl_pf:.0f} pF · {vdc('C4'):.1f} kV", side=1)
    vcap(xR, y_a, y_b, "C6", f"{cl_pf:.0f} pF · {vdc('C6'):.1f} kV", side=1)
    for x_, y_ in ((xL, y_a), (xR, y_a), (xL, y_b), (xR, y_b)):
        dot(x_, y_)
    nlabel(xL - 12, y_a - 8, "l1", V["l1"], "end")
    nlabel(xR + 12, y_a - 8, "r1", V["r1"], "start")
    nlabel(xL - 12, y_b + 20, "l2", V["l2"], "end")
    nlabel(xR + 12, y_b + 20, "r2", V["r2"], "start")
    # the crossings, as the sketch draws them: D3 (2 -> r1) / D4 (l1 -> 3); D6 (r1 -> l2) / D5 (r2 -> l1)
    xm = 0.5 * (xL + xR)
    p3 = ddiode((xL, y_n), (xR, y_a), POS, t=0.22)
    p4 = ddiode((xL, y_a), (xR, y_n), NEG, t=0.78, hop=(xm, 0.5 * (y_n + y_a)))
    dlabel(p3[0], y_n + 20, "D3", VR["D3"], POS)
    dlabel(p4[0], y_n + 20, "D4 rev.", VR["D4"], NEG)
    p6 = ddiode((xR, y_a), (xL, y_b), POS, t=0.22)
    p5 = ddiode((xR, y_b), (xL, y_a), NEG, t=0.78, hop=(xm, 0.5 * (y_a + y_b)))
    dlabel(xm - 6, y_a + 4, "D5 rev.", VR["D5"], NEG, "end")       # between the two crossings, clear of the nodes
    dlabel(xm + 6, y_a + 4, "D6", VR["D6"], POS, "start")
    # the top: l2's lead to D7 and C7, r2's lead to D8 and C8, crossing once (as the sketch's D7 / D8 leads)
    p0, p1 = (xL, y_b - 26), (bx, y_t)
    q0, q1 = (xR, y_b - 26), (ax_, y_t)
    ln(xL, y_b, *p0); ln(xR, y_b, *q0); ln(*p0, *p1)
    den = (p1[0] - p0[0]) * (q0[1] - q1[1]) - (p1[1] - p0[1]) * (q0[0] - q1[0])
    t_ = ((q0[0] - p0[0]) * (q0[1] - q1[1]) - (q0[1] - p0[1]) * (q0[0] - q1[0])) / den
    cx_, cy_ = p0[0] + t_ * (p1[0] - p0[0]), p0[1] + t_ * (p1[1] - p0[1])
    L = math.hypot(q1[0] - q0[0], q1[1] - q0[1])
    ux, uy = (q1[0] - q0[0]) / L, (q1[1] - q0[1]) / L
    h0, h1 = (cx_ - 7 * ux, cy_ - 7 * uy), (cx_ + 7 * ux, cy_ + 7 * uy)
    ln(*q0, *h0); ln(*h1, *q1)
    o.append(f'<path d="M{h0[0]:.1f} {h0[1]:.1f} A7 7 0 0 0 {h1[0]:.1f} {h1[1]:.1f}" fill="none" stroke="#111" '
             'stroke-width="1.8"/>')
    ln(x4, y_n, x4, y_x); ln(x1, y_n, x1, y_x)                  # node 4's rail up the right, node 1's up the left
    ddiode((bx, y_t), (x4, y_t), POS)
    dlabel(0.5 * (bx + x4), y_t - 14, "D7", VR["D7"], POS)
    vcap(bx, y_t, y_x, "C7 new", f"{R['c_cw_pF']:.0f} pF · {vdc('C7'):.1f} kV", side=1)
    ddiode((x4, y_x), (bx, y_x), POS)
    dlabel(0.5 * (bx + x4), y_x - 14, "D9 new", VR["D9"], POS)
    ddiode((x1, y_t), (ax_, y_t), NEG)
    dlabel(0.5 * (x1 + ax_), y_t - 14, "D8 rev.", VR["D8"], NEG)
    vcap(ax_, y_t, y_x, "C8 new", f"{R['c_cw_pF']:.0f} pF · {vdc('C8'):.1f} kV", side=-1)
    ddiode((ax_, y_x), (x1, y_x), NEG)
    dlabel(0.5 * (x1 + ax_), y_x - 14, "D11 new", VR["D11"], NEG)
    for x_, y_ in ((bx, y_t), (ax_, y_t), (x4, y_t), (x1, y_t), (x4, y_x), (x1, y_x), (bx, y_x), (ax_, y_x)):
        dot(x_, y_)
    nlabel(bx - 12, y_x + 22, "xb", V["xb"], "end")
    nlabel(ax_ + 12, y_x + 22, "xa", V["xa"], "start")
    ddiode((bx, y_x), (bx, y_r), POS)
    dlabel(bx - 14, 0.5 * (y_x + y_r) + 4, "D10 new", VR["D10"], POS, "end")
    ddiode((ax_, y_r), (ax_, y_x), NEG)
    dlabel(ax_ + 14, 0.5 * (y_x + y_r) + 4, "D12 new", VR["D12"], NEG, "start")
    # the hub, and the rings' leads: ring B's along the top to the hub's left, ring A's above it to the hub's right
    xh, yh, rv = 1225, 452, 78
    (rbx, rby), (rax, ray) = RS.hub(xh, yh, rec, rv)
    ray_r = (2 * xh - rax, ray)                                   # ring A's right-hand arc
    xb_lead, xa_lead = 1080, 1405
    pl([(bx, y_r), (xb_lead, y_r), (xb_lead, rby), (rbx, rby)])
    pl([(ax_, y_r), (ax_, y_ra), (xa_lead, y_ra), (xa_lead, ray), ray_r])
    dot(bx, y_r); dot(ax_, y_r)
    # the smoothing capacitors, each ring to the shaft, beside the hub
    ln(xb_lead, 214, 1100, 214); SR.cap_h(1100, 214, 11); pl([(1110, 214), (1130, 214), (1130, 226)]); ground(1130, 226)
    dot(xb_lead, 214)
    tx(1105, 196, f"<tspan font-weight='bold'>Csb</tspan> {R['c_cw_pF']:.0f} pF · {vdc('Csb'):.1f} kV", "ms", "middle")
    ln(xa_lead, 172, 1385, 172); SR.cap_h(1375, 172, 11); pl([(1375, 172), (1355, 172), (1355, 184)]); ground(1355, 184)
    dot(xa_lead, 172)
    tx(1340, 154, f"<tspan font-weight='bold'>Csa</tspan> {R['c_cw_pF']:.0f} pF · {vdc('Csa'):.1f} kV", "ms", "end")
    tx(xh, yh - 168, "THE HUB (untouched)", "zh", "middle")
    tx(1090, rby - 30, f"ring B +{s['V_B_kV']:.2f} kV", "tu", "start", 'font-weight="bold"')
    tx(1290, ray + 20, f"ring A {kv(s['V_A_kV'], '{:.2f}')} kV", "ta", "start", 'font-weight="bold"')
    tx(xh, yh + 168, f"{s['E_null_kV_cm']:.2f} kV/cm at the null, B to A", "te", "middle")
    tx(xh, yh + 185, f"ripple {s['E_null_pp_kV_cm']:.3f} kV/cm p-p · the null at 0 V by symmetry", "ms", "middle")
    tx(xh, yh + 202, f"the record as built: {sup['E_null_kV_cm']:.2f} kV/cm (±{sup['V_B_kV']:.2f} kV)", "ms", "middle")
    # the table
    th = {q["model"]: q for q in re_.get("thresholds", [])}
    fz = {(q["kind"], q["model"], q["v0"]): q["z"] for q in re_.get("free", [])}
    rc = {q["job"]["model"]: q for q in re_.get("clamped", []) if q.get("done")}
    rows = [
        ("circuit", f"the designer's ladder (C3–C6 {cl_pf:.0f} pF, D5–D8), bipolar: chain 2 reversed; C1 / C2 in phase "
                    "(in antiphase it does not pump); each chain one stage past its varicap node to its ring"),
        ("levels", f"nodes 1 / 4 at the clamps' {kv(V['1'][0])} / +{V['4'][1]:.1f} kV (V_op of record); the rings "
                   f"{kv(s['V_A_kV'], '{:.2f}')} / +{s['V_B_kV']:.2f} kV, {s['E_null_kV_cm']:.2f} kV/cm at the null "
                   f"(the record as built ±{sup['V_B_kV']:.2f} kV, {sup['E_null_kV_cm']:.2f} kV/cm)"),
        ("diodes", f"12 HV sticks, one a position, reverse ≤ {max(VR.values()):.1f} kV (the record: 14, its D3 / D4 "
                   f"{max(sup['VR_pk_kV'].values()):.1f} kV on two each)"),
        ("capacitors", f"Ca / Cb now hold {vdc('Ca'):.1f} kV (the record's {max(abs(x) for x in sup['VC_kV']['Ca']):.1f}); "
                       f"C5 / C6 {vdc('C5'):.1f}, C3 / C4 {vdc('C3'):.1f}, C7 / C8 {vdc('C7'):.1f}, Csa / Csb "
                       f"{vdc('Csa'):.1f} kV"),
        ("pump", f"z {pick['z_free']:.4f} as built (the record with its chains {R['as_built']['gate_supply_start']['z']:.4f}); "
                 f"the clamps {1e3 * s['P_clamps_W']:.0f} mW; 95 % in {s['cycles_to_95pc'] / 120.0:.2f} s; "
                 "the counter-rotor can float (Q1 = −Q2)"),
        ("real sticks", "seeds " + " / ".join(f"{th[m]['v_grows_V']:.0f} V" for m in ("HV-typ", "HV-max", "HV-hot") if m in th)
                        + " (typical / maximum / hot; the record 122 V / 1.0 kV / 3.65 kV); the rings "
                        + " / ".join(f"±{rc[m]['V_B_kV']:.2f}" for m in ("HV-typ", "HV-max", "HV-hot") if m in rc)
                        + " kV, " + " / ".join(f"{rc[m]['E_null_kV_cm']:.2f}" for m in ("HV-typ", "HV-max", "HV-hot")
                                               if m in rc) + " kV/cm"),
        ("open", f"the new nodes' strays (24.5 pF each assumed) set the rings: with none they reach "
                 f"±{R['rings_at_zero_strays_kV']:.1f} kV; trim the clamp strings on the bench before the hub sees it"),
    ]
    table(42, 818, rows, w_key=104, dy=21)
    tx(20, 1012, "Numbers: sim/integrated_multiplier_results.json (pick, as_built, real) · findings: "
                 "sim/integrated-multiplier-findings.md · generator: docs/make_integrated_multiplier_schematic.py", "n")
    o.append("</svg>")
    svg = OUT + ".svg"
    open(svg, "w").write("\n".join(o) + "\n")
    png = None
    try:
        from playwright.sync_api import sync_playwright
        png = OUT + ".png"
        with sync_playwright() as p:
            b = p.chromium.launch(executable_path=os.environ.get("CHROMIUM", "/opt/pw-browsers/chromium"))
            pg = b.new_page(viewport={"width": W, "height": Hh}, device_scale_factor=2)
            pg.set_content(f'<html><body style="margin:0">{open(svg).read()}</body></html>')
            pg.screenshot(path=png, clip=dict(x=0, y=0, width=W, height=Hh))
            b.close()
    except ImportError:
        pass
    print(json.dumps(dict(svg=os.path.relpath(svg, ROOT), png=png and os.path.relpath(png, ROOT))))


if __name__ == "__main__":
    main()
