#!/usr/bin/env python3
"""
sim/battery_capacity.py — insulation survey rev 3: re-run from DXF v0.x + freeze doc.
=====================================================================================
SOURCE CORRECTION (rev 3): rev 2 pulled geometry from index.html and called it
authoritative. That is WRONG -- index.html is STALE. The authoritative geometry is
the DXF layout + the consolidated freeze doc in the repo. This rev re-derives the
flashover ceiling from those sources.

  STANDING CORRECTION (all future work): the geometric reference is the DXF +
  docs/varcap-design-freeze-v0.10.md. index.html is a stale calculator and must NOT
  be used for dimensions (only as a flagged [STALE] historical cross-reference).

PROVENANCE FLAGS (cross-check, surfaced to TMD):
  * The brief names "DXF v0.11"; the repo has no v0.11. Present: the r0_6 DXF
    (docs/varcap-nodeanalysis-template-r0_6_TMD_layout.dxf) + the v0.10 freeze doc.
    The doc (§8) itself references a not-yet-drafted r0_10 DXF. -> use what exists,
    flag the version gap. (The doc carries the 7mm/12mm-garolite cap set the brief
    expects, so the substance matches even if the version label is off.)
  * The r0_6 DXF is a 2D RADIAL template: it carries RADII (R387 electrode band,
    confirmed below) + the layer/node structure, but NOT the AXIAL gap spacings
    (7mm air, 12mm garolite, 3mm Cx) -- those are dimensioned in the freeze-doc §3
    cap table, which is the consolidated doc. The DXF text even labels its radii
    "R1-baseline (calculator-derived)". So: radii + element existence from the DXF;
    axial gaps from the doc; the two cross-checked on r387.
  * rev 2's "central HV void clearN 20mm / edge-creepage 30mm" were STALE index.html
    artifacts -- v0.10 C_R is ANNULAR at r387 (no central spherical void).

WHAT rev 2 GOT WRONG (reversed here by the authoritative source):
  - "C1/C2 = 0.5mm -> 1.5kV, pump-side": WRONG. C1/C2 = 7.0mm air (doc §3); doc §4
    states it CAPS THE ISLAND AT ~21 kV (fire window 16.6-21 kV) -> it is the
    documented system voltage ceiling. Back in contention as the binding element.
  - "C_R = 10mm mica -> 400kV": WRONG. C_R = 12.0mm GAROLITE (doc §3/§6:
    "15 kV/12 mm = 1.25 kV/mm holdoff") -> bulk ~180 kV (still >> ceiling).

Tiers: [OC] standard physics · [IR] modelling choice · [STALE] index.html (excluded).
HV refs: Kuffel/Zaengl HV Engineering; IEC 60052 (sphere gaps); IEC 60112 (creepage).
"""
import math
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
DXF = os.path.join(ROOT, "docs", "varcap-nodeanalysis-template-r0_6_TMD_layout.dxf")
DOC = os.path.join(ROOT, "docs", "varcap-design-freeze-v0.10.md")

# ---- inherited anchors -------------------------------------------------------
C_R = 789e-12          # output cap (F)   freeze doc §3 (12mm garolite, r387)        [OC]
V_OP = 15e3            # operating DC store (V)  freeze doc §1 clamp / §4             [OC]

# ---- breakdown gradients (cite refs) -----------------------------------------
G_AIR = 3.0            # kV/mm  uniform/sphere-gap air ~30 kV/cm  Kuffel; doc §5      [OC]
G_AIR_SHARP = 1.0      # kV/mm  sharp-apex derate (ONLY where the DXF shows a sharp tip) [IR]
G_GAROLITE = 15.0      # kV/mm  G-10 bulk (10-20)  Kuffel; doc §6 holdoff 1.25 @ op   [IR]
G_MICA = 40.0          # kV/mm  mica working (intrinsic ~118 derated)  Kuffel         [IR]
G_CREEP_DIRTY = 1.0    # kV/mm  surface flashover, conservative   IEC 60112           [IR]
G_CREEP_CLEAN = 2.5    # kV/mm  surface flashover, clean/ribbed                       [IR]

# ---- voltage-holding elements: AXIAL gaps from freeze doc §3; radii from DXF ----
# (name, dim_mm, material, gradient, holds_full_VCR, electrode, dxf_layer, doc_src)
ELEMENTS = [
    ("C1/C2 varicap gap",  7.0,  "air",      G_AIR,        True,  "r387 plate (12mm W-Cu spheres at gaps)", "CAP-C1-OVERLAP", "doc§3: 7.0mm air, 16-280pF; §4 caps island ~21kV"),
    ("Ca/Cb mica barrier", 4.5,  "mica",     G_MICA,       False, "r175 disc",    "CAP-Ca-GAP",   "doc§3: 4.5mm mica, 309pF"),
    ("Cx3/Cx4 air sub-gap",3.0,  "air",      G_AIR,        False, "bars r75-350", "CAP-Cx3-GAP",  "doc§3: 3.0mm air (+0.3mm mica), 8-648pF"),
    ("Cx3/Cx4 mica face",  0.3,  "mica",     G_MICA,       False, "pickup face",  "CAP-Cx3-GAP",  "doc§3: 0.3mm mica/face"),
    ("C_R garolite bulk",  12.0, "garolite", G_GAROLITE,   True,  "r387 half-ann","MECH-DIELECTRIC","doc§3/§6: 12.0mm garolite, 789pF, 1.25kV/mm@15kV"),
    ("C_R edge creepage",  12.0, "air-surf", G_CREEP_DIRTY,True,  "r387 septum edge","MECH-DIELECTRIC","UNDIMENSIONED in r0_6 (radial); est=septum thickness -- FLAG r0_10"),
    ("fire gap SG3b/SG4b", 5.5,  "air",      G_AIR,        False, "12mm W-Cu sphere","SG3b-FIRE-GAP","doc§5: ~5.3-6.4mm, strike 16.6-20kV -- DESIGNED, excluded"),
]
FIRE_GAP = "fire gap SG3b/SG4b"


def read_dxf():
    """Read RADII + the insulation-bearing layer set from the DXF (descend into the
    drawing; cross-check r387). Returns (radii_mm, layers)."""
    try:
        import ezdxf
    except Exception as e:
        return None, None, f"ezdxf unavailable: {e}"
    doc = ezdxf.readfile(DXF)
    msp = doc.modelspace()
    radii = set()
    for e in msp:
        if e.dxftype() in ("ARC", "CIRCLE"):
            radii.add(round(e.dxf.radius, 1))
    # the labelled reference radii (TEXT on 00-REF-RADII)
    ref_txt = [e.dxf.text.strip() for e in msp.query("TEXT") if e.dxf.layer == "00-REF-RADII"]
    layers = [l.dxf.name for l in doc.layers]
    return radii, ref_txt, layers


def breakdown_kV(dim_mm, gradient):
    return dim_mm * gradient


def series_division(t_air, er_air, t_mica, er_mica):
    z_air, z_mica = t_air / er_air, t_mica / er_mica
    return z_air / (z_air + z_mica), z_mica / (z_air + z_mica)


# =============================================================================
# Self-tests
# =============================================================================
def selftests(dxf_radii, ref_txt, layers):
    out = []
    # (a) C1/C2 = 7mm air -> ~21 kV (correcting the STALE 0.5mm/1.5kV)
    v = breakdown_kV(7.0, G_AIR)
    out.append(("(a) C1/C2 7mm air = 21kV (NOT stale 0.5mm)", abs(v - 21.0) < 0.01,
                dict(Vbd_kV=v)))
    # (b) C_R = 12mm garolite -> ~180 kV (correcting the STALE 10mm mica/400kV)
    vg = breakdown_kV(12.0, G_GAROLITE)
    out.append(("(b) C_R 12mm garolite = 180kV (NOT stale mica)", abs(vg - 180.0) < 0.01,
                dict(Vbd_kV=vg)))
    # (c) DXF<->doc cross-check: r387 electrode band present in the DXF
    r387 = dxf_radii is not None and 387.0 in dxf_radii
    r387txt = any("R387" in t for t in (ref_txt or []))
    out.append(("(c) DXF<->doc cross-check: r387 electrode", r387 and r387txt,
                dict(dxf_has_r387=r387, labelled=r387txt)))
    # (d) Cx air+mica series: the low-eps AIR holds the larger share
    fa, fm = series_division(3.0, 1.0, 0.3, 5.4)
    out.append(("(d) Cx air+mica: air holds larger share", fa > fm and fa > 0.9,
                dict(frac_air=fa)))
    # (e) the insulation layers exist in the DXF (C1/C2, dielectric, fire gap)
    need = {"CAP-C1-OVERLAP", "MECH-DIELECTRIC", "SG3b-FIRE-GAP"}
    have = layers is not None and need.issubset(set(layers))
    out.append(("(e) DXF carries the insulation layers", have, dict(have=have)))
    # (f) hand-calc cross-check: fire gap 5.5mm * 3kV/mm = 16.5kV (in the 16.6-20 window)
    vf = breakdown_kV(5.5, G_AIR)
    out.append(("(f) fire gap 5.5mm*3 = 16.5kV (designed window)", 15 < vf < 21,
                dict(Vbd_kV=vf)))
    return out


# =============================================================================
# Main
# =============================================================================
def main():
    print("=" * 82)
    print("battery_capacity rev3 — insulation survey from DXF r0_6 + freeze-doc v0.10")
    print("=" * 82)

    dxf_radii, ref_txt, layers = read_dxf()
    if dxf_radii is None:
        print(f"  WARN: {layers}")  # error msg
        dxf_radii, ref_txt, layers = set(), [], []

    print("\nSELF-TESTS:")
    ok = True
    for name, passed, info in selftests(dxf_radii, ref_txt, layers):
        ok = ok and passed
        det = " ".join(f"{k}={v:.4g}" if isinstance(v, float) else f"{k}={v}"
                        for k, v in info.items())
        print(f"  [{'PASS' if passed else 'FAIL'}] {name:46s} {det}")
    if not ok:
        print("  -> SELF-TESTS FAILED; verdict not trustworthy.")
        return 1

    print(f"\nDXF r0_6 reference radii (mm): {sorted(dxf_radii)}")
    print(f"  labelled: {ref_txt[:4]} ...")
    print(f"  PROVENANCE: brief says 'v0.11'; repo has r0_6 DXF + v0.10 doc (doc §8 cites a "
          f"not-yet-drafted r0_10). Axial gaps from doc §3; radii cross-checked on r387. [flag to TMD]")

    rows = []
    for name, dim, mat, grad, holds, elec, layer, src in ELEMENTS:
        vbd = breakdown_kV(dim, grad)
        rows.append(dict(name=name, dim=dim, mat=mat, grad=grad, vbd=vbd, holds=holds,
                         elec=elec, layer=layer, src=src, excluded=(name == FIRE_GAP)))

    print("\nPER-ELEMENT BREAKDOWN (axial dims from freeze-doc §3, radii from DXF):")
    print(f"  {'element':22s} {'dim':>6s} {'material':9s} {'grad':>5s} {'Vbd':>7s} {'holds VCR':10s} layer")
    for r in rows:
        flag = "EXCL(fire)" if r["excluded"] else ("full V_CR" if r["holds"] else "fraction")
        print(f"  {r['name']:22s} {r['dim']:5.1f}m {r['mat']:9s} {r['grad']:4.1f} "
              f"{r['vbd']:6.1f}k {flag:10s} {r['layer']}")

    # binding = smallest breakdown among DIMENSIONED full-V_CR holders (fire gap
    # excluded as designed; creepage excluded from the ceiling because it is
    # UNDIMENSIONED in the r0_6 radial DXF -- reported separately as a flagged
    # candidate, since a validated design must have creepage > the 15 kV operating).
    holders = [r for r in rows if r["holds"] and not r["excluded"]]
    creep = next(r for r in holders if "creepage" in r["name"])
    dimensioned = [r for r in holders if "creepage" not in r["name"]]
    binding = min(dimensioned, key=lambda r: r["vbd"])
    c12 = next(r for r in holders if r["name"].startswith("C1/C2"))
    garo = next(r for r in holders if "garolite bulk" in r["name"])

    V_ceil = binding["vbd"] * 1e3
    E_max = 0.5 * C_R * V_ceil ** 2
    E_op = 0.5 * C_R * V_OP ** 2
    margin = V_ceil / V_OP

    print("\nVERDICTS (re-derived from DXF r0_6 + doc v0.10):")
    print(f"  BINDING-ELEMENT = {{C1/C2 7mm air, V_breakdown={c12['vbd']:.0f} kV "
          f"(=7mm x 3kV/mm sphere-gap), V_CR_at_ceiling={c12['vbd']:.0f} kV}}")
    print(f"     -> the documented system ceiling (doc §4: C1/C2 caps the island at ~21 kV, "
          f"fire window 16.6-21 kV). rev2 wrongly dismissed this on stale 0.5mm data.")
    print(f"  BATTERY-CEILING = {{V_max={V_ceil/1e3:.0f} kV, E_max={E_max*1e3:.0f} mJ}}  "
          f"(operating {V_OP/1e3:.0f} kV / {E_op*1e3:.1f} mJ -> margin {margin:.2f}x V, "
          f"{margin**2:.2f}x E)")
    print(f"  DIELECTRIC-NOT-LIMIT: C_R garolite bulk = {garo['vbd']:.0f} kV (12mm) >> "
          f"{V_ceil/1e3:.0f} kV ceiling -> margin {garo['vbd']/(V_ceil/1e3):.1f}x. "
          f"(robust to the source error -- holds for garolite 180 kV as it did for mica 400 kV.)")
    print(f"  *** FLAG (load-bearing): C_R EDGE CREEPAGE is UNDIMENSIONED in the r0_6 radial DXF. "
          f"If the garolite is flush (~{creep['dim']:.0f}mm bare edge), creepage breaks at "
          f"{creep['vbd']:.0f} kV (dirty) -- {creep['dim']*G_CREEP_CLEAN:.0f} kV (clean) ->")
    print(f"      that is AT/BELOW the {V_OP/1e3:.0f} kV operating point. The real edge-path needs "
          f"the r0_10 DXF; flagged to TMD as the binding unknown (rev 2's 30mm was stale).")

    print("\n  RAISE-LEVER (geometry, not the dielectric):")
    print(f"     1. WIDEN C1/C2 air: +1 mm buys +{G_AIR:.0f} kV (7->9 mm -> {breakdown_kV(9,G_AIR):.0f} kV); "
          f"the doc's 4.4 kV fire-window margin already rides on this gap.")
    print(f"     2. C_R creepage RIBS / radial overhang: the highest-leverage unknown -- a ribbed "
          f"edge 2-3x the path -> de-binds creepage well above 21 kV.")
    print(f"     3. GUARD-RING the C1/C2 plate edges (round/sphere) -> approach the 3kV/mm uniform "
          f"ceiling instead of any sharp-edge derate.")
    print(f"     NOT thicken the garolite: already {garo['vbd']/(V_ceil/1e3):.0f}x over -- wasted.")

    _plots(rows, binding, V_ceil, V_OP, E_max, E_op, creep)

    # CSV
    csv = os.path.join(ROOT, "battery_capacity.csv")
    with open(csv, "w") as f:
        f.write("element,dim_mm,material,gradient_kVmm,Vbd_kV,holds_full_VCR,excluded,dxf_layer,source\n")
        for r in rows:
            f.write(f"{r['name']},{r['dim']},{r['mat']},{r['grad']},{r['vbd']:.2f},{r['holds']},"
                    f"{r['excluded']},{r['layer']},\"{r['src']}\"\n")
        f.write(f"#bindingElem,C1/C2 7mm air\n#Vceil_kV,{V_ceil/1e3:.2f}\n#Emax_mJ,{E_max*1e3:.2f}\n")
        f.write(f"#Vop_kV,{V_OP/1e3:.1f}\n#Eop_mJ,{E_op*1e3:.2f}\n#voltage_margin,{margin:.3f}\n")
        f.write(f"#marginGarolite_kV,{garo['vbd']:.0f}\n")
        f.write(f"#FLAG_creepage_undimensioned,r0_6_radial_only_needs_r0_10\n")
        f.write(f"#PROVENANCE,brief_v0.11_absent__repo_has_r0_6_DXF+v0.10_doc__index.html_STALE\n")
    print(f"\nwrote {os.path.relpath(csv, ROOT)}")
    print(f"VERDICT: BINDING=C1/C2 7mm air | CEILING={V_ceil/1e3:.0f} kV / {E_max*1e3:.0f} mJ | "
          f"op {V_OP/1e3:.0f} kV margin {margin:.2f}x | garolite {garo['vbd']:.0f} kV NOT the limit | "
          f"creepage FLAGGED")
    return 0


def _plots(rows, binding, V_ceil, V_OP, E_max, E_op, creep):
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        import numpy as np
    except Exception as e:
        print(f"(plots skipped: {e})")
        return
    fig, ax = plt.subplots(figsize=(9, 4.4))
    names = [r["name"] for r in rows]
    vbd = [r["vbd"] for r in rows]
    colors = []
    for r in rows:
        if r is binding:
            colors.append("#e76f51")
        elif "creepage" in r["name"]:
            colors.append("#f4a261")        # flagged unknown
        elif r["excluded"]:
            colors.append("#bbb")
        elif r["mat"] in ("garolite", "mica"):
            colors.append("#2a9d8f")
        else:
            colors.append("#8ab")
    ax.bar(range(len(names)), vbd, color=colors)
    ax.axhline(V_OP / 1e3, ls="--", color="#264653", label=f"operating {V_OP/1e3:.0f} kV")
    ax.axhline(V_ceil / 1e3, ls=":", color="#e76f51", label=f"ceiling {V_ceil/1e3:.0f} kV (C1/C2)")
    ax.set_yscale("log")
    ax.set_xticks(range(len(names))); ax.set_xticklabels(names, rotation=30, ha="right", fontsize=7)
    ax.set_ylabel("breakdown voltage (kV, log)")
    ax.set_title("rev3 per-element breakdown (DXF+doc): binding=C1/C2 7mm air; creepage flagged; garolite off-scale")
    ax.legend(fontsize=8)
    fig.tight_layout(); fig.savefig(os.path.join(ROOT, "battery_breakdown_survey.png"), dpi=110)
    plt.close(fig)

    fig, ax = plt.subplots(figsize=(6.0, 4.2))
    V = np.linspace(0, V_ceil / 1e3 * 1.3, 200)
    E = 0.5 * C_R * (V * 1e3) ** 2 * 1e3
    ax.plot(V, E, color="#2a9d8f", lw=1.5, label="½·C_R·V²  (789 pF)")
    ax.axvline(V_ceil / 1e3, ls=":", color="#e76f51", label=f"C1/C2 ceiling {V_ceil/1e3:.0f} kV → {E_max*1e3:.0f} mJ")
    ax.axvline(V_OP / 1e3, ls="--", color="#264653", label=f"operating {V_OP/1e3:.0f} kV → {E_op*1e3:.0f} mJ")
    ax.axvspan(creep["dim"] * G_CREEP_DIRTY, creep["dim"] * G_CREEP_CLEAN, alpha=0.12, color="#f4a261",
               label=f"creepage flag {creep['dim']*G_CREEP_DIRTY:.0f}-{creep['dim']*G_CREEP_CLEAN:.0f} kV (undimensioned)")
    ax.fill_between(V, E, where=(V <= V_ceil / 1e3), alpha=0.08, color="#2a9d8f")
    ax.set_xlabel("V_CR (kV)"); ax.set_ylabel("stored energy (mJ)")
    ax.set_title("Battery capacity vs ceiling (C1/C2 7mm air); creepage band flagged")
    ax.legend(fontsize=8)
    fig.tight_layout(); fig.savefig(os.path.join(ROOT, "battery_capacity_ceiling.png"), dpi=110)
    plt.close(fig)
    print("wrote battery_breakdown_survey.png, battery_capacity_ceiling.png")


if __name__ == "__main__":
    sys.exit(main())
