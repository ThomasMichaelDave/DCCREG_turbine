# -*- coding: utf-8 -*-
"""PumpGeometry -- Fusion 360 script: build the PUMP-SYNTH stage-2 plate geometry from pump-geometry.json.

Install: Utilities > ADD-INS > Scripts and Add-Ins > Scripts tab > "+" (or the green plus) > pick this folder
(tools/fusion360/PumpGeometry). Run it, pick the pump-geometry-<hash>.json exported by tools/pump-synth.html stage 2.

It creates a NEW design: one top component (the lock hash + description), one sub-component per carrier
(rotor discs, flanges, stator carriers) plus "Dielectrics", and one named body per solid -- exactly the bill of
solids in the JSON ("parts"), the same names the FreeCAD macro writes into STEP. Units: the JSON is in mm; the
Fusion API works in cm (converted here). Geometry only -- no physics is evaluated.

Validated outside Fusion by sim/pump_geometry_gates.py (gate G-F360): this file runs against an OpenCascade
stand-in for the adsk modules and every body's volume is checked against the analytic value.
"""
import json
import math
import os
import traceback

import adsk.core
import adsk.fusion

MM = 0.1                                    # mm -> cm (Fusion API internal length unit)
BAD = '/\\:*?"<>|'                         # characters Fusion does not accept in names


def _name(s):
    for c in BAD:
        s = s.replace(c, "-")
    return s


def _pick_json(ui):
    p = os.environ.get("PUMP_GEOMETRY_JSON")
    if p:
        return p
    dlg = ui.createFileDialog()
    dlg.title = "pump-geometry.json (PUMP-SYNTH stage 2)"
    dlg.filter = "JSON (*.json)"
    if dlg.showOpen() != adsk.core.DialogResults.DialogOK:
        return None
    return dlg.filename


def annulus(tbm, rin, rout, z0, z1, a0, w):
    """Annular sector solid (inputs in mm, angles in degrees, w < 180 or a full ring)."""
    P = adsk.core.Point3D.create
    p0, p1 = P(0, 0, z0 * MM), P(0, 0, z1 * MM)
    body = tbm.createCylinderOrCone(p0, rout * MM, p1, rout * MM)
    if rin > 1e-9:
        tbm.booleanOperation(body, tbm.createCylinderOrCone(p0, rin * MM, p1, rin * MM),
                             adsk.fusion.BooleanTypes.DifferenceBooleanType)
    if w < 360.0 - 1e-9:
        if w >= 180.0:
            raise ValueError("sector wider than 180 deg is not supported")
        L, H = 4.0 * rout * MM, 4.0 * abs(z1 - z0) * MM + 1.0
        zc = 0.5 * (z0 + z1) * MM
        for ang, side in ((a0, 1.0), (a0 + w, -1.0)):
            a = math.radians(ang)
            u = adsk.core.Vector3D.create(math.cos(a), math.sin(a), 0)
            n = adsk.core.Vector3D.create(-math.sin(a), math.cos(a), 0)
            c = P(side * n.x * L / 2, side * n.y * L / 2, zc)
            box = adsk.core.OrientedBoundingBox3D.create(c, u, n, 2 * L, L, H)
            tbm.booleanOperation(body, tbm.createBox(box), adsk.fusion.BooleanTypes.IntersectionBooleanType)
    return body


def solid(tbm, p):
    """One part of the bill of solids: an annular sector, a sphere (gap electrode) or a rod (post / arm / lead)."""
    shape = p.get("shape", "sector")
    P = adsk.core.Point3D.create
    if shape == "sphere":
        c = p["c"]
        return tbm.createSphere(P(c[0] * MM, c[1] * MM, c[2] * MM), p["r"] * MM)
    if shape == "rod":
        a, b = p["p0"], p["p1"]
        return tbm.createCylinderOrCone(P(a[0] * MM, a[1] * MM, a[2] * MM), p["r"] * MM,
                                        P(b[0] * MM, b[1] * MM, b[2] * MM), p["r"] * MM)
    return annulus(tbm, p["r_in"], p["r_out"], p["z0"], p["z1"], p["start_deg"], p["w_deg"])


def _appearance(app, design, key, rgb, cache):
    """A per-colour appearance copied from the Fusion appearance library (skipped if unavailable)."""
    if key in cache:
        return cache[key]
    ap = None
    try:
        lib = None
        for nm in ("Fusion Appearance Library", "Fusion 360 Appearance Library"):
            lib = app.materialLibraries.itemByName(nm)
            if lib:
                break
        base = lib.appearances.itemByName("Paint - Enamel Glossy (Yellow)") if lib else None
        if base:
            ap = design.appearances.addByCopy(base, "PumpGeometry " + key)
            for i in range(ap.appearanceProperties.count):
                prop = adsk.core.ColorProperty.cast(ap.appearanceProperties.item(i))
                if prop:
                    prop.value = adsk.core.Color.create(int(rgb[0] * 255), int(rgb[1] * 255), int(rgb[2] * 255), 0)
                    break
    except Exception:
        ap = None
    cache[key] = ap
    return ap


def build(app, design, data):
    tbm = adsk.fusion.TemporaryBRepManager.get()
    root = design.rootComponent
    parametric = design.designType == adsk.fusion.DesignTypes.ParametricDesignType
    top = root.occurrences.addNewComponent(adsk.core.Matrix3D.create())
    top.component.name = _name(data["top_label"])
    comps = {}
    for a in data["assemblies"]:
        occ = top.component.occurrences.addNewComponent(adsk.core.Matrix3D.create())
        occ.component.name = _name(a["label"])
        comps[a["key"]] = occ.component
    made, cache = [], {}
    by_comp = {}
    for p in data["parts"]:
        by_comp.setdefault(p["assembly"], []).append(p)
    for key, plist in by_comp.items():
        comp = comps[key]
        bf = None
        if parametric:
            bf = comp.features.baseFeatures.add()
            bf.startEdit()
        for p in plist:
            body = solid(tbm, p)
            b = comp.bRepBodies.add(body, bf) if bf else comp.bRepBodies.add(body)
            b.name = _name(p["label"])
            ap = _appearance(app, design, "%.3f,%.3f,%.3f" % tuple(p["rgb"]), p["rgb"], cache)
            if ap:
                try:
                    b.appearance = ap
                except Exception:
                    pass
            made.append(dict(name=p["name"], label=b.name, component=comp.name, volume=b.volume / MM ** 3,
                             expect=p["volume"]))
            adsk.doEvents()
        if bf:
            bf.finishEdit()
    return made


def run(context):
    app = adsk.core.Application.get()
    ui = app.userInterface
    try:
        path = _pick_json(ui)
        if not path:
            return
        data = json.load(open(path))
        if data.get("schema") != "pump-geometry/1" or "parts" not in data:
            ui.messageBox("Not a pump-geometry/1 file with a bill of solids: re-export it from tools/pump-synth.html stage 2.")
            return
        app.documents.add(adsk.core.DocumentTypes.FusionDesignDocumentType)
        design = adsk.fusion.Design.cast(app.activeProduct)
        made = build(app, design, data)
        err = max(abs(m["volume"] - m["expect"]) / m["expect"] for m in made) if made else 0.0
        globals()["RESULT"] = made
        ui.messageBox("PumpGeometry %s: %d bodies in %d components built (worst volume error %.1e).\n\n"
                      "Names follow the parts table (pump-geometry ...-parts.csv / FreeCAD STEP)."
                      % (data["lock"].get("hash", ""), len(made), len(data["assemblies"]), err))
    except Exception:
        ui.messageBox("PumpGeometry failed:\n" + traceback.format_exc())
