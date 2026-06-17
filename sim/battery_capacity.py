#!/usr/bin/env python3
"""
sim/battery_capacity.py — insulation-coordination survey: the real flashover ceiling.
=====================================================================================
How much energy can C_R hold? Bounded by the WEAKEST insulation element across the
machine. This block surveys every voltage-holding element, computes each breakdown
from the ACTUAL geometry in index.html, maps each stress to V_CR, and reports which
flashes first -- correcting rev 1's mis-attribution ("21 kV from 12 mm garolite").

CORRECTION CARRIED THROUGH (rev 2): 12 mm garolite *bulk* is the STRONG part
(>100 kV); the real limit is an air gap or a surface-creepage path. And the brief's
own SUSPECTED dimensions turn out NOT to be in index.html (the authoritative source):
  - the suspected "C1/C2 7 mm air gap" does not exist -- the varicap gap is
    pgap = 0.5 mm (index.html:206-207, R1 preset:1865);
  - C_R is not "12 mm garolite" -- it is a 10 mm MICA disc (mdisch=10, eps_r 5.4,
    index.html:322,1448,1495), an even STRONGER dielectric.
So this survey computes the ceiling from the real geometry and names the binding
element, rather than inheriting either rev's assumed number.

INHERITED (cite): the series accumulation model + 88.8 mJ-at-15 kV anchor
(series_resonator.csv @ b62e642); C_R = 789 pF; the machine geometry from index.html
(the authoritative dimensions, surveyed).

Tiers: [OC] standard physics · [IR] modelling choice · [RH]. No DCCREG.
HV refs: Kuffel/Zaengl HV Engineering; IEC 60052 (sphere gaps); IEC 60112 (creepage).
"""
import math
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)

# ---- inherited anchors -------------------------------------------------------
C_R = 789e-12          # output cap (F)        inherited series_resonator @b62e642   [OC]
V_OP = 15e3            # operating DC store (V) series clamp / freeze v0.10           [OC]
V_DESIGN_HV = 20e3     # design HV (V)         index.html vhvKV default :134,1869     [OC]

# ---- breakdown gradients (cite refs; index.html's own design deratings) ------
G_AIR_INTRINSIC = 3.0  # kV/mm  uniform-field air ~30 kV/cm at STP   Kuffel/Zaengl    [OC]
G_AIR_SHARP = 1.0      # kV/mm  index.html sharp-tip derate (no guard) :2663-2666     [IR]
G_AIR_GUARD = 2.0      # kV/mm  index.html guard-ring derate          :2834           [IR]
G_MICA = 40.0          # kV/mm  mica working (intrinsic ~118, derated) Kuffel         [IR]
G_MYLAR = 40.0         # kV/mm  Mylar single-sheet caution            index.html:1714 [IR]
G_GAROLITE = 15.0      # kV/mm  G-10 bulk (10-20 kV/mm)  reference only               [IR]
G_CREEP_DIRTY = 1.0    # kV/mm  surface flashover, conservative       IEC 60112       [IR]
G_CREEP_CLEAN = 2.5    # kV/mm  surface flashover, clean/ribbed                       [IR]

# ---- the voltage-holding elements, ACTUAL index.html geometry ----------------
# (name, dim_mm, material, gradient_kV_mm, holds_full_VCR, electrode, src)
ELEMENTS = [
    ("C1/C2 varicap gap",   0.5,  "air",      G_AIR_INTRINSIC, False, "flat sectored", "index.html:206 pgap=0.5"),
    ("Ca/Cb transfer film", 1.0,  "Mylar",    G_MYLAR,         False, "flat plate",    "index.html:666 tcMylarThkMm=1.0"),
    ("C_R mica bulk",       10.0, "mica",     G_MICA,          True,  "cone faces",    "index.html:322 mdisch=10"),
    ("C_R edge creepage",   30.0, "air-surf", G_CREEP_DIRTY,   True,  "disc edge",     "index.html:1351 edgeEE=2*(voidR-discVoidR)+discH"),
    ("HV void clearN (e->n)",20.0,"air",      G_AIR_SHARP,     True,  "cone apex",     "index.html:1349 voidR=20 (sharp-tip 1kV/mm)"),
    ("HV void clearEE (e->e)",40.0,"air",     G_AIR_SHARP,     True,  "cone-cone",     "index.html:1350 2*voidR=40"),
    ("fire gap SG3b/SG4b",  6.0,  "air",      G_AIR_INTRINSIC, False, "W-Cu sphere",   "designed 20 kV breakdown (V_bd, inherited) -- EXCLUDED"),
    ("commutator kbargap",  2.0,  "air",      G_AIR_INTRINSIC, False, "Cu bars",       "index.html:406 kbargap=2 (display-only)"),
]
FIRE_GAP = "fire gap SG3b/SG4b"   # designed breakdown -> excluded from the ceiling


def breakdown_kV(dim_mm, gradient):
    """Uniform-field / surface breakdown = gap x gradient. [OC]"""
    return dim_mm * gradient


def sphere_gap_factor(s_mm, D_mm):
    """Sphere-gap uniformity rolloff: ~uniform for s/D < 0.5, falls toward the
    sharp-tip limit beyond (IEC 60052). Returns an effective-gradient multiplier. [OC]"""
    r = s_mm / D_mm
    if r <= 0.5:
        return 1.0
    return max(0.4, 1.0 - 0.7 * (r - 0.5))   # rolls off toward sharp-tip


def series_division(t_air, er_air, t_mica, er_mica):
    """Voltage share in an air+mica series stack: V_i proportional to t_i/er_i
    (the low-eps AIR holds the larger share). Returns (frac_air, frac_mica). [OC]"""
    z_air = t_air / er_air
    z_mica = t_mica / er_mica
    return z_air / (z_air + z_mica), z_mica / (z_air + z_mica)


# =============================================================================
# Self-tests
# =============================================================================
def selftests():
    out = []
    # (a) the ACTUAL C1/C2 gap (pgap=0.5mm), correcting the suspected "7mm -> 21kV"
    v = breakdown_kV(0.5, G_AIR_INTRINSIC)
    out.append(("(a) C1/C2 actual 0.5mm air = 1.5kV (NOT 7mm/21kV)", abs(v - 1.5) < 0.01,
                dict(Vbd_kV=v)))
    # (b) C_R dielectric bulk (10mm mica) is the headroom, >100 kV
    v_mica = breakdown_kV(10.0, G_MICA)
    out.append(("(b) C_R mica 10mm bulk > 100 kV", v_mica > 100, dict(Vbd_kV=v_mica)))
    # garolite reference too (12mm * 15 = 180 kV), the rev-1 element, also >>ceiling
    v_garo = breakdown_kV(12.0, G_GAROLITE)
    # (c) air+mica series division: AIR holds the larger share (low eps)
    fa, fm = series_division(3.0, 1.0, 0.3, 5.4)
    out.append(("(c) air+mica series: air holds larger share", fa > fm and fa > 0.9,
                dict(frac_air=fa, frac_mica=fm)))
    # (d) creepage uses the EDGE path (30mm), not the 10mm thickness
    out.append(("(d) creepage = 30mm edge path, not 10mm thick",
                next(e[1] for e in ELEMENTS if e[0] == "C_R edge creepage") == 30.0,
                dict(L_mm=30.0)))
    # (e) hand-calc cross-check: void clearN 20mm * 1kV/mm = 20 kV
    v_void = breakdown_kV(20.0, G_AIR_SHARP)
    out.append(("(e) void clearN 20mm * 1kV/mm = 20 kV", abs(v_void - 20.0) < 0.01,
                dict(Vbd_kV=v_void)))
    # (f) garolite/mica margin sanity (both >> any ~20-30 kV ceiling)
    out.append(("(f) dielectric bulk margin >> ceiling", v_mica > 100 and v_garo > 100,
                dict(mica_kV=v_mica, garolite_kV=v_garo)))
    return out


# =============================================================================
# Survey
# =============================================================================
def survey():
    rows = []
    for name, dim, mat, grad, holds, elec, src in ELEMENTS:
        vbd = breakdown_kV(dim, grad)
        # intrinsic-air optimistic bound for air gaps (for the reported range)
        vbd_opt = breakdown_kV(dim, G_AIR_INTRINSIC) if mat.startswith("air") else vbd
        rows.append(dict(name=name, dim=dim, mat=mat, grad=grad, vbd=vbd, vbd_opt=vbd_opt,
                         holds=holds, elec=elec, src=src,
                         excluded=(name == FIRE_GAP)))
    return rows


def main():
    print("=" * 80)
    print("battery_capacity — insulation-coordination survey (actual index.html geometry)")
    print("=" * 80)

    print("\nSELF-TESTS:")
    ok = True
    for name, passed, info in selftests():
        ok = ok and passed
        det = " ".join(f"{k}={v:.4g}" if isinstance(v, float) else f"{k}={v}"
                        for k, v in info.items())
        print(f"  [{'PASS' if passed else 'FAIL'}] {name:48s} {det}")
    if not ok:
        print("  -> SELF-TESTS FAILED; verdict not trustworthy.")
        return 1

    rows = survey()
    print("\nPER-ELEMENT BREAKDOWN (actual geometry):")
    print(f"  {'element':24s} {'dim':>6s} {'material':8s} {'grad':>5s} {'Vbd':>7s} {'holds VCR':9s} note")
    for r in rows:
        flag = "EXCLUDED(fire)" if r["excluded"] else ("full V_CR" if r["holds"] else "fraction")
        print(f"  {r['name']:24s} {r['dim']:5.1f}m {r['mat']:8s} {r['grad']:4.1f} "
              f"{r['vbd']:6.1f}k {flag:9s} {r['src'].split(' -- ')[0]}")

    # binding element = smallest breakdown among elements that hold the FULL V_CR
    # (exclude the designed fire gap and the pump-side fractional elements)
    vcr_holders = [r for r in rows if r["holds"] and not r["excluded"]]
    binding = min(vcr_holders, key=lambda r: r["vbd"])
    V_ceil = binding["vbd"] * 1e3
    V_ceil_opt = binding["vbd_opt"] * 1e3
    E_max = 0.5 * C_R * V_ceil ** 2
    E_op = 0.5 * C_R * V_OP ** 2
    margin = V_ceil / V_OP

    # dielectric-bulk reference (mica + garolite)
    mica = next(r for r in rows if r["name"] == "C_R mica bulk")
    v_garo = breakdown_kV(12.0, G_GAROLITE)
    fire = next(r for r in rows if r["excluded"])

    print("\nVERDICTS:")
    print(f"  BINDING-ELEMENT = {{{binding['name']}, V_breakdown={binding['vbd']:.0f} kV "
          f"(={binding['dim']:.0f}mm x {binding['grad']:.0f}kV/mm sharp-tip), "
          f"V_CR_at_ceiling={binding['vbd']:.0f} kV}}")
    print(f"     (next: C_R creepage {next(r['vbd'] for r in vcr_holders if 'creep' in r['name']):.0f} kV, "
          f"clearEE {next(r['vbd'] for r in vcr_holders if 'clearEE' in r['name']):.0f} kV "
          f"-- all central-HV, all ~20-40 kV)")
    print(f"  BATTERY-CEILING = {{V_max={V_ceil/1e3:.0f} kV (conservative 1 kV/mm; "
          f"{V_ceil_opt/1e3:.0f} kV at intrinsic 3 kV/mm), E_max={E_max*1e3:.0f} mJ}}")
    print(f"     operating point: {V_OP/1e3:.0f} kV / {E_op*1e3:.1f} mJ -> margin {margin:.2f}x in voltage, "
          f"{margin**2:.2f}x in energy")
    print(f"  GAROLITE-NOT-LIMIT (actually MICA): C_R bulk = {mica['vbd']:.0f} kV (10mm mica) "
          f">> {V_ceil/1e3:.0f} kV ceiling -> margin {mica['vbd']/(V_ceil/1e3):.0f}x.")
    print(f"     (12mm garolite ref = {v_garo:.0f} kV, also >> ceiling -- the dielectric VOLUME is the "
          f"strong part, exactly as rev 2 said.)")
    print(f"  FIRE-GAP (designed, excluded): {fire['name']} strikes ~20 kV (V_bd) -- the island fires "
          f"here by design, not a failure.")

    # raise levers
    print("\n  RAISE-LEVER (lift the ceiling -- NOT by thickening the dielectric):")
    print(f"     1. GUARD RING on the central electrode: 1->2 kV/mm (round the cone apex) "
          f"-> ceiling {V_ceil/1e3:.0f} -> {breakdown_kV(binding['dim'], G_AIR_GUARD):.0f} kV (2x, biggest lever).")
    print(f"     2. WIDEN the void gap: +1 mm of clearN buys +{G_AIR_SHARP:.0f} kV "
          f"(20->30 mm -> {breakdown_kV(30, G_AIR_SHARP):.0f} kV ceiling).")
    print(f"     3. CREEPAGE ribs/skirts: 2-3x the surface path in the same axial space "
          f"-> 30->75 mm -> {breakdown_kV(75, G_CREEP_DIRTY):.0f} kV (de-binds creepage).")
    print(f"     NOT thicken the mica: already {mica['vbd']/(V_ceil/1e3):.0f}x over -- wasted.")

    print("\n  CORRECTION TO THE BRIEF: the suspected '7mm C1/C2 gap' is not in index.html "
          f"(actual pgap=0.5mm -> 1.5 kV, pump-side); C_R is 10mm MICA, not 12mm garolite. "
          f"The ~20 kV ceiling is the CENTRAL HV VOID (clearN, sharp-tip), = the design HV "
          f"(index.html sizes void=20mm=20kV/1kV/mm) -- near rev-1's 21 kV but a different element.")

    _plots(rows, vcr_holders, binding, V_ceil, V_OP, E_max, E_op)

    # CSV
    csv = os.path.join(ROOT, "battery_capacity.csv")
    with open(csv, "w") as f:
        f.write("element,dim_mm,material,gradient_kVmm,Vbd_kV,Vbd_intrinsic_kV,holds_full_VCR,excluded,source\n")
        for r in rows:
            f.write(f"{r['name']},{r['dim']},{r['mat']},{r['grad']},{r['vbd']:.2f},{r['vbd_opt']:.2f},"
                    f"{r['holds']},{r['excluded']},{r['src']}\n")
        f.write(f"#bindingElem,{binding['name']}\n#Vceil_kV,{V_ceil/1e3:.2f}\n")
        f.write(f"#Emax_mJ,{E_max*1e3:.2f}\n#Vop_kV,{V_OP/1e3:.1f}\n#Eop_mJ,{E_op*1e3:.2f}\n")
        f.write(f"#marginGarolite_kV,{mica['vbd']:.0f}\n#voltage_margin,{margin:.3f}\n")
    print(f"\nwrote {os.path.relpath(csv, ROOT)}")
    print(f"VERDICT: BINDING={binding['name']} | CEILING={V_ceil/1e3:.0f} kV / {E_max*1e3:.0f} mJ | "
          f"op {V_OP/1e3:.0f} kV margin {margin:.2f}x | MICA bulk {mica['vbd']:.0f} kV NOT the limit")
    return 0


def _plots(rows, vcr_holders, binding, V_ceil, V_OP, E_max, E_op):
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        import numpy as np
    except Exception as e:
        print(f"(plots skipped: {e})")
        return
    # 1. per-element breakdown bar (binding highlighted, dielectric off-scale-high)
    fig, ax = plt.subplots(figsize=(9, 4.4))
    names = [r["name"] for r in rows]
    vbd = [r["vbd"] for r in rows]
    colors = []
    for r in rows:
        if r is binding:
            colors.append("#e76f51")          # binding
        elif r["excluded"]:
            colors.append("#bbb")             # designed fire gap
        elif r["mat"] in ("mica", "Mylar"):
            colors.append("#2a9d8f")          # dielectric (strong)
        else:
            colors.append("#8ab")
    ax.bar(range(len(names)), vbd, color=colors)
    ax.axhline(V_OP / 1e3, ls="--", color="#264653", label=f"operating {V_OP/1e3:.0f} kV")
    ax.axhline(V_ceil / 1e3, ls=":", color="#e76f51", label=f"ceiling {V_ceil/1e3:.0f} kV (binding)")
    ax.set_yscale("log")
    ax.set_xticks(range(len(names)))
    ax.set_xticklabels(names, rotation=30, ha="right", fontsize=7)
    ax.set_ylabel("breakdown voltage (kV, log)")
    ax.set_title("Per-element breakdown vs operating stress (binding=red, dielectric=teal, off-scale-high)")
    ax.legend(fontsize=8)
    fig.tight_layout(); fig.savefig(os.path.join(ROOT, "battery_breakdown_survey.png"), dpi=110)
    plt.close(fig)
    # 2. capacity vs V_CR with ceiling + operating point
    fig, ax = plt.subplots(figsize=(6.0, 4.2))
    V = np.linspace(0, V_ceil / 1e3 * 1.3, 200)
    E = 0.5 * C_R * (V * 1e3) ** 2 * 1e3
    ax.plot(V, E, color="#2a9d8f", lw=1.5, label="½·C_R·V²  (789 pF)")
    ax.axvline(V_ceil / 1e3, ls=":", color="#e76f51",
               label=f"ceiling {V_ceil/1e3:.0f} kV → {E_max*1e3:.0f} mJ")
    ax.axvline(V_OP / 1e3, ls="--", color="#264653",
               label=f"operating {V_OP/1e3:.0f} kV → {E_op*1e3:.0f} mJ")
    ax.fill_between(V, E, where=(V <= V_ceil / 1e3), alpha=0.08, color="#2a9d8f")
    ax.set_xlabel("V_CR (kV)"); ax.set_ylabel("stored energy (mJ)")
    ax.set_title(f"Battery capacity vs the binding-element ceiling ({binding['name']})")
    ax.legend(fontsize=8)
    fig.tight_layout(); fig.savefig(os.path.join(ROOT, "battery_capacity_ceiling.png"), dpi=110)
    plt.close(fig)
    print("wrote battery_breakdown_survey.png, battery_capacity_ceiling.png")


if __name__ == "__main__":
    sys.exit(main())
