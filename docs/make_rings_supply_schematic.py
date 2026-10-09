"""docs/make_rings_supply_schematic.py -- writes docs/schematic-rings-supply.{svg,png}: the rings' DC supply of record in
full, the symmetric (mirror) pair (sim/hub_rings_build_results.json record and record_supply; sim/core_field.py dc with
n_cw_a and a_ref "shaft"):
  ring B on a positive Cockcroft-Walton chain driven by the pump's node 4, ring A on its mirror image driven by node 1,
  both chains standing on the shaft (REF), which the AH, the flanges and the null share; every stage drawn, with its
  DC level, each diode's reverse peak and the parts' ratings; the hub with the rings and the field at the null.
Usage: python3 docs/make_rings_supply_schematic.py   (the PNG needs playwright + chromium)
"""
import json
import math
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
import make_schematic_rotor as SR  # noqa: E402  (its SVG primitives write into SR.o)

OUT = os.path.join(HERE, "schematic-rings-supply")
o = SR.o
ln, pl, tx, dot, diode, cap_h, cap_v, ground, box, kv, table = (SR.ln, SR.pl, SR.tx, SR.dot, SR.diode, SR.cap_h, SR.cap_v,
                                                                SR.ground, SR.box, SR.kv, SR.table)


def style_block():
    """the rotor schematic's style sheet, so both sheets read alike."""
    src = open(os.path.join(HERE, "make_schematic_rotor.py")).read()
    return re.search(r'o\.append\("""(<style>.*?</style>)"""\)', src, re.S).group(1)


def vdiode(x, y_anode, y_cathode):
    """a vertical diode between two rails, centred, pointing from its anode to its cathode."""
    sg = 1 if y_cathode > y_anode else -1
    y0 = 0.5 * (y_anode + y_cathode) - 9 * sg
    ln(x, y_anode, x, y0)
    diode(x, y0, "down" if sg > 0 else "up")
    ln(x, y0 + 18 * sg, x, y_cathode)
    dot(x, y_anode); dot(x, y_cathode)


def chain(x0, y_osc, y_smo, sign, vr, stages, tags, cdc):
    """one Cockcroft-Walton chain as a ladder: the oscillating column on y_osc, driven from the left through Co1; the
    smoothing column on y_smo, starting at the shaft at x0. sign +1: ring B's chain (the clamp diodes' anodes on the
    smoothing side, the levels rise); -1: ring A's mirror image (both diodes reversed, the levels fall). Each part
    carries its name, its DC (capacitors) or its reverse peak (diodes). Returns the output's point."""
    pitch = 230
    up = y_smo > y_osc                                                  # the oscillating column on top (ring B)
    prev_osc, prev_smo = x0 - 60, x0
    for k in range(1, stages + 1):
        last = k == stages
        xc = x0 + 10 + (k - 1) * pitch                                  # Co_k's left plate
        xd, xs_c, xp = xc + 45, xc + 95, xc + 150                       # the clamp diode, Cs_k's left plate, the peak diode
        x_end = xp if last else xc + pitch
        ln(prev_osc, y_osc, xc, y_osc); cap_h(xc, y_osc, 12)
        nm_o, nm_s = ("Co" if sign > 0 else "Coa") + str(k), ("Cs" if sign > 0 else "Csa") + str(k)
        yo = y_osc - 34 if up else y_osc + 34                           # outside the ladder
        tx(xc + 5, yo, nm_o, "t", "middle", 'font-weight="bold"')
        tx(xc + 5, yo + 14, f"{cdc[nm_o]:.1f} kV", "ms", "middle")
        ln(xc + 10, y_osc, x_end, y_osc)
        tx(xc + 100, y_osc + (-8 if up else 18), ("m" if sign > 0 else "n") + str(k), "ms", "middle")
        ln(prev_smo, y_smo, xs_c, y_smo); cap_h(xs_c, y_smo, 12)
        ys = y_smo + 30 if up else y_smo - 32
        tx(xs_c + 5, ys, nm_s, "t", "middle", 'font-weight="bold"')
        tx(xs_c + 5, ys + 14, f"{cdc[nm_s]:.1f} kV", "ms", "middle")
        s_end = xp + 40 if last else xc + pitch + 45
        ln(xs_c + 10, y_smo, s_end, y_smo)
        nm_c, nm_p = ("Dc", "Dp") if sign > 0 else ("Dca", "Dpa")
        if sign > 0:
            vdiode(xd, y_smo, y_osc); vdiode(xp, y_osc, y_smo)
        else:
            vdiode(xd, y_osc, y_smo); vdiode(xp, y_smo, y_osc)
        ym = 0.5 * (y_osc + y_smo)
        tx(xd - 14, ym + 4, f"{nm_c}{k}", "t", "end", 'font-weight="bold"')
        tx(xd - 14, ym + 18, f"{vr[nm_c + str(k)]:.1f} kV", "ms", "end")
        tx(xp + 14, ym + 4, f"{nm_p}{k}", "t", "start", 'font-weight="bold"')
        tx(xp + 14, ym + 18, f"{vr[nm_p + str(k)]:.1f} kV", "ms", "start")
        tx(xp + 10, ys, tags[k - 1], "tu" if sign > 0 else "ta", "start", 'font-weight="bold"')   # the node's level
        prev_osc, prev_smo = x_end, s_end
    return (prev_smo, y_smo)


def hub(xc, yc, rec, rv=78):
    """the vessel with ring B (upper) and ring A (lower) outside it; the AH cores on the axis, each at REF; E at the
    null, B to A. Returns the rings' lead points (B, A), on the left arcs' middles."""
    o.append(f'<circle cx="{xc:.1f}" cy="{yc:.1f}" r="{rv:.1f}" class="glass"/>')
    for top, col in ((1, "#1f6fb2"), (-1, "#c0392b")):
        for side in (-1, 1):
            pts = [(xc + side * (rv + 3) * math.sin(math.radians(t)), yc - top * (rv + 3) * math.cos(math.radians(t)))
                   for t in [rec["theta_p"] + i * (rec["theta_e"] - rec["theta_p"]) / 23 for i in range(24)]]
            o.append('<polyline points="' + " ".join(f"{x:.1f},{y:.1f}" for x, y in pts) +
                     f'" fill="none" stroke="{col}" stroke-width="6" stroke-linecap="round"/>')
    hw = rv * 11.45 / 25.0
    for s in (1, -1):                                                 # the AH cores (REF), to scale
        y0, y1 = yc - s * rv * 30.7 / 25.0, yc - s * rv * 46.0 / 25.0
        a, b = sorted((y0, y1))
        o.append(f'<rect x="{xc - hw:.1f}" y="{a:.1f}" width="{2 * hw:.1f}" height="{b - a:.1f}" '
                 'fill="#9aa3ad" stroke="#5d6670" stroke-width="1"/>')
        ym = 0.5 * (a + b)
        ln(xc + hw, ym, xc + hw + 22, ym); ln(xc + hw + 22, ym, xc + hw + 22, ym + 8); ground(xc + hw + 22, ym + 8)
        tx(xc + hw + 38, ym + 4, "AH core, REF", "ms")
    ln(xc, yc - 26, xc, yc + 12, "ef")
    o.append(f'<polygon points="{xc:.1f},{yc + 24:.1f} {xc - 6:.1f},{yc + 12:.1f} {xc + 6:.1f},{yc + 12:.1f}" fill="#1d3f5e"/>')
    tx(xc + 10, yc + 4, "E", "te", "start")
    tm = math.radians(0.5 * (rec["theta_p"] + rec["theta_e"]))
    return ((xc - (rv + 3) * math.sin(tm), yc - (rv + 3) * math.cos(tm)),
            (xc - (rv + 3) * math.sin(tm), yc + (rv + 3) * math.cos(tm)))


def main():
    R = json.load(open(os.path.join(ROOT, "sim", "hub_rings_build_results.json")))
    rec, sup, fr = R["record"], R["record_supply"], R["record_supply_free"]
    assert rec.get("a_ref") == "shaft", "the record is not the mirror pair"
    vr = sup["VR_pk_kV"]
    sw = json.load(open(os.path.join(ROOT, "sim", "hub_drift_results.json")))["swing"]
    t_, c1 = sw["t_ms"], [x < 1e3 / 120.0 for x in sw["t_ms"]]           # the first of the two recorded cycles
    i_a = min((i for i in range(len(t_)) if c1[i]), key=lambda i: sw["V_A_kV"][i])
    i_b = max((i for i in range(len(t_)) if c1[i]), key=lambda i: sw["V_B_kV"][i])
    sw = dict(sw, dt_topup_cyc=abs(t_[i_b] - t_[i_a]) * 120.0 / 1e3,
              gap_pp_V=1e3 * (max(b - a for a, b in zip(sw["V_A_kV"], sw["V_B_kV"])) -
                              min(b - a for a, b in zip(sw["V_A_kV"], sw["V_B_kV"]))))
    n = rec["n_cw"]
    stage = sup["V_eb_kV"]["mean"] / n
    W, H = 1440, 890
    o.clear()
    o.append(f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}" '
             'font-family="DejaVu Sans, Arial, sans-serif" font-size="13">')
    o.append("<title>Rings supply</title>")
    o.append(f'<rect width="{W}" height="{H}" fill="#ffffff"/>')
    o.append(style_block())
    tx(20, 30, "DCCREG turbine: the rings' DC supply of record, the symmetric pair (each ring on its own chain from the "
               "shaft)", "h")
    tx(20, 52, f"Ring B on {n} positive Cockcroft-Walton stages driven by the pump's node 4, ring A on the mirror image "
               f"driven by node 1; both chains stand on the shaft (REF), which the AH and the null share. 100 pF "
               f"storage, {R['R_leak_est'] / 1e9:.0f} GΩ per ring.", "m")
    box(20, 70, 1400, 590, "frame")
    # the pump: its two pumping nodes, half a cycle apart
    box(40, 140, 190, 480, "zone_r")
    tx(52, 162, "THE PUMP (rotor)", "zh")
    for i, s_ in enumerate(("de Queiroz diode doubler,", "docs/schematic-rotor-circuits", "panel (b): C1 / C2, Ca / Cb,",
                            "D1–D4, the clamps Z1 / Z4")):
        tx(52, 182 + 15 * i, s_, "ms")
    v1, v4 = sup["V"]["1"], sup["V"]["4"]
    ml = {k[2:-1]: v / 1e3 for k, v in sup["mean_last"].items()}       # the nodes' DC (kV), the last cycle's mean
    cdc = {}                                                            # each capacitor's DC, plate to plate
    for k in range(1, n + 1):
        m_, mp = f"m{k}", ("4" if k == 1 else f"m{k - 1}")
        b_, bp = ("eb" if k == n else f"b{k}"), ("0" if k == 1 else f"b{k - 1}")
        n_, np_ = f"n{k}", ("1" if k == 1 else f"n{k - 1}")
        a_, ap = ("ea" if k == n else f"a{k}"), ("0" if k == 1 else f"a{k - 1}")
        cdc[f"Co{k}"], cdc[f"Cs{k}"] = abs(ml[m_] - ml[mp]), abs(ml[b_] - ml.get(bp, 0.0))
        cdc[f"Coa{k}"], cdc[f"Csa{k}"] = abs(ml[n_] - ml[np_]), abs(ml[a_] - ml.get(ap, 0.0))
    tx(52, 262, "node 4", "nd", "start", 'font-weight="bold"')
    tx(52, 278, f"{kv(v4['min'])} ↔ {kv(v4['max'])} kV", "ms")
    tx(52, 542, "node 1", "nd", "start", 'font-weight="bold"')
    tx(52, 558, f"{kv(v1['min'])} ↔ {kv(v1['max'])} kV", "ms")
    tx(52, 578, "the same swing,", "ms"); tx(52, 593, "half a cycle later", "ms")
    # the chains: B above the shaft rail, A below it (mirror images); the rail is the core's centre, both pump against it
    y_rail = 380
    x0 = 330
    tags_b = [f"+{kv(stage * k)} kV" for k in range(1, n)] + [f"B +{kv(sup['V_eb_kV']['mean'])} kV"]
    tags_a = [f"{kv(-stage * k)} kV" for k in range(1, n)] + [f"A {kv(sup['V_ea_kV']['mean'])} kV"]
    pl([(230, 240), (250, 240), (250, 190), (x0 - 60, 190)])
    out_b = chain(x0, 190, 300, +1, vr, n, tags_b, cdc)
    pl([(230, 520), (250, 520), (250, 570), (x0 - 60, 570)])
    out_a = chain(x0, 570, 460, -1, vr, n, tags_a, cdc)
    # the shaft rail between the chains, joined to both chains' first smoothing nodes
    xh, yh = 1080, y_rail
    ln(x0 - 40, y_rail, xh - 108, y_rail, "rail")
    ln(x0, 300, x0, y_rail); ln(x0, 460, x0, y_rail)
    dot(x0, y_rail)
    ln(x0 - 40, y_rail, x0 - 40, y_rail + 10); ground(x0 - 40, y_rail + 10)
    tx(x0 + 8, y_rail - 8, "shaft (rotor) = REF, 0 V", "m")
    # the hub
    (bx_, by_), (ax_, ay_) = hub(xh, yh, rec)
    pl([out_b, (xh - 90, out_b[1]), (xh - 90, by_), (bx_, by_)])
    pl([out_a, (xh - 90, out_a[1]), (xh - 90, ay_), (ax_, ay_)])
    ln(xh - 108, y_rail, xh - 12, y_rail, "mag")                       # no wire: the null's potential, by symmetry
    tx(xh, yh + 46, "null: 0 V, as REF", "ms", "middle")
    tx(xh, yh + 60, "(by symmetry)", "ms", "middle")
    tx(xh + 96, yh - 92, f"ring B +{kv(sup['V_eb_kV']['mean'])} kV", "tu", "start", 'font-weight="bold"')
    tx(xh + 96, yh - 76, f"{rec['theta_p']:.2f}–{rec['theta_e']:.2f}° from the axis", "ms")
    tx(xh + 96, yh + 84, f"ring A {kv(sup['V_ea_kV']['mean'])} kV", "ta", "start", 'font-weight="bold"')
    tx(xh + 96, yh + 100, "ring B's mirror image", "ms")
    tx(xh + 96, yh - 4, f"{rec['E_null_kV_cm']:.2f} kV/cm at the null, B to A", "te")
    tx(xh + 96, yh + 12, f"{rec['p_null_Pa']:.2f} Pa, steady (ripple {sw['E_pp_kV_cm']:.3f} kV/cm p-p)", "ms")
    tx(xh, yh - 172, "THE HUB", "zh", "middle")
    tx(xh, yh - 156, "the vessel, the AH cores on its axis", "ms", "middle")
    # the parts and the numbers
    y = 690
    rows = [
        ("chains", f"{n} stages each; ring B's from node 4 (Co, Dc, Dp, Cs), ring A's from node 1 (Coa, Dca, Dpa, Csa), the "
                   "diodes reversed"),
        ("levels", f"each stage adds node 4's / node 1's swing: {kv(stage)} kV a stage at {R['R_leak_est'] / 1e9:.0f} GΩ per "
                   f"ring; {sup['V_eb_kV']['mean'] - sup['V_ea_kV']['mean']:.1f} kV across the rings"),
        ("diodes", f"{4 * n} HV stacks, reverse ≤ {max(v for k, v in vr.items() if k[:2] in ('Dc', 'Dp')):.1f} kV each "
                   "(20 kV stacks, derated 1.5×)"),
        ("capacitors", f"{4 * n} × 100 pF / 30 kV; each holds about one stage's {kv(stage)} kV DC, but Co1 "
                       f"{cdc['Co1']:.1f} and Coa1 {cdc['Coa1']:.1f} kV: nodes 4 and 1 sit at {kv(v4['mean'])} kV mean"),
        ("ripple", f"ring A {1e3 * sup['V_ea_kV']['pp']:.0f} V, ring B {1e3 * sup['V_eb_kV']['pp']:.0f} V p-p at "
                   f"{SR.json.load(open(os.path.join(ROOT, 'sim', 'core_field_results.json')))['F_Hz']:.0f} Hz; ring A tops "
                   f"up as node 1 bottoms, ring B as node 4 peaks, {sw['dt_topup_cyc']:.3f} of a cycle later: "
                   f"{sw['gap_pp_V']:.0f} V p-p across the gap, {100 * sw['E_pp_kV_cm'] / sw['E_mean_kV_cm']:.1f} % of the "
                   "field; no swing"),
        ("pump", f"belt {sup['P_belt_W']:.2f} W into the clamps; leakage {1e3 * sup['P_leak_W']:.1f} mW; start-up gain z "
                 f"{fr['z']:.3f}"),
        ("rings", f"Cu foil bands, beads Ø{2 * rec['rho_pol_mm']:g} / Ø{2 * rec['rho_eq_mm']:g} mm (polar / equatorial) "
                  f"in gel; strays {rec['C_ring_ref_pF']:.1f} pF each to REF, {rec['C_ring_ring_pF']:.1f} pF between"),
    ]
    table(42, y, rows, w_key=96, dy=21)
    tx(20, 870, "Numbers: sim/hub_rings_build_results.json (record, record_supply), sim/hub_drift_results.json (swing), "
                "sim/core_field.py (the deck) · "
                "findings: sim/hub-rings-build-findings.md · generator: docs/make_rings_supply_schematic.py", "n")
    o.append("</svg>")
    svg = OUT + ".svg"
    open(svg, "w").write("\n".join(o) + "\n")
    png = None
    try:
        from playwright.sync_api import sync_playwright
        png = OUT + ".png"
        with sync_playwright() as p:
            b = p.chromium.launch(executable_path=os.environ.get("CHROMIUM", "/opt/pw-browsers/chromium"))
            pg = b.new_page(viewport={"width": W, "height": H}, device_scale_factor=2)
            pg.set_content(f'<html><body style="margin:0">{open(svg).read()}</body></html>')
            pg.screenshot(path=png, clip=dict(x=0, y=0, width=W, height=H))
            b.close()
    except ImportError:
        pass
    print(json.dumps(dict(svg=os.path.relpath(svg, ROOT), png=png and os.path.relpath(png, ROOT))))


if __name__ == "__main__":
    main()
