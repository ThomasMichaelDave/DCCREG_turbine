#!/usr/bin/env python3
"""Bump the varcap node-analysis DXF template r0.1 -> r0.2.

Applies the design-intent-lock.md §9 layer-scheme additions (two-tier 5-6 resonator clamp +
static-sealed vacuum chamber) to the r0.1 template and regenerates the r0.2 template. Pure additive
edit (no existing layer/geometry touched) so the diff is reviewable. Run from docs/:

    python3 varcap-nodeanalysis-template-bump.py

Reads  docs/varcap-nodeanalysis-template-r0.1.dxf
Writes docs/varcap-nodeanalysis-template-r0.2.dxf

Colour convention is inherited from r0.1 (ACI): the new layers join existing functional families
so they read correctly in any CAD without a custom palette —
  glow/soft clamp -> 4 (cyan, the MECH-RESONATOR-TANK / 5-6 resonator family; the void IS the
                       resonator clamp), hard crowbar -> 6 (magenta, the SG* spark-gap family;
  it IS a spark), vacuum chamber -> 9 (the MECH-ENVELOPE family), nipple -> 7 (MECH hardware).
CLAMP-SOFT-UPSTREAM is defined but OFF+FROZEN — it is a §6.3 [OPEN] decision (upstream vs in-void
soft governor); the layer name is frozen so the choice is a one-flag flip, but nothing should be
drafted onto it until confirmed.
"""
import os
import ezdxf

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(HERE, "varcap-nodeanalysis-template-r0.1.dxf")
DST = os.path.join(HERE, "varcap-nodeanalysis-template-r0.2.dxf")

# (name, ACI colour, description for the legend, frozen?) — design-intent-lock.md §9
NEW_LAYERS = [
    ("CLAMP-VOID-GLOW-5-6", 4,
     "CLAMP-VOID-GLOW-5-6: soft glow governor across ND5<->ND6 (smooth, low-field; normal-glow self-reg)",
     False),
    ("CLAMP-CROWBAR-HARD-5-6", 6,
     "CLAMP-CROWBAR-HARD-5-6: hard spark crowbar across ND5<->ND6 (symmetric/bidirectional; last-resort)",
     False),
    ("MECH-VACUUM-CHAMBER", 9,
     "MECH-VACUUM-CHAMBER: sealed inter-shaft chamber (STATIC seal line - co-rotation locked, no rotating seal)",
     False),
    ("MECH-VACUUM-NIPPLE", 7,
     "MECH-VACUUM-NIPPLE: re-sealable evacuation/fill valve (sets pd into the glow band)",
     False),
    ("CLAMP-SOFT-UPSTREAM", 4,
     "CLAMP-SOFT-UPSTREAM: [PENDING 6.3 confirm; layer OFF+FROZEN] optional island/pickup-side soft governor",
     True),
]

TITLE_OLD = "VARCAP NODE-ANALYSIS TEMPLATE  -  LAYER SCHEME (draft parts onto node layers)"
TITLE_NEW = "VARCAP NODE-ANALYSIS TEMPLATE  r0.2  -  LAYER SCHEME (draft parts onto node layers)"


def main():
    doc = ezdxf.readfile(SRC)

    # 1) add the new layers (additive; skip if a re-run finds them already present)
    for name, color, _desc, frozen in NEW_LAYERS:
        if name in doc.layers:
            continue
        ly = doc.layers.add(name, color=color)
        if frozen:
            ly.off()
            ly.freeze()

    msp = doc.modelspace()

    # 2) mark the revision in the title text
    for e in msp:
        if e.dxftype() == "TEXT" and e.dxf.layer == "00-LEGEND" and e.dxf.text == TITLE_OLD:
            e.dxf.text = TITLE_NEW
            break

    # 3) extend the legend (continue the -560 column downward; r0.1 ended at y=502, dy=22, h=12)
    x0, dy, h = -560.0, 22.0, 12.0
    y = 502.0 - 2 * dy
    lines = ["", "r0.2 (2026-06-15) additions  -  see docs/design-intent-lock.md (clamp tiers + 5-6 vacuum-glow void):"]
    lines += [desc for _n, _c, desc, _f in NEW_LAYERS]
    for txt in lines:
        if txt:
            msp.add_text(txt, height=h, dxfattribs={"layer": "00-LEGEND", "style": "Standard",
                                                    "insert": (x0, y)})
        y -= dy

    doc.saveas(DST)
    print(f"wrote {DST}  (+{len(NEW_LAYERS)} layers, legend r0.2)")


if __name__ == "__main__":
    main()
