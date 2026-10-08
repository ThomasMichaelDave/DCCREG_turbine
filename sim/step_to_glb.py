#!/usr/bin/env python3
"""sim/step_to_glb.py -- an XCAF STEP (e.g. docs/geometry/tube/*.step) as a binary glTF (.glb) for 3-D viewers.

Reads the STEP back (the assembly tree, every instance's placement, the product colours and names), tessellates each
product ONCE (BRepMesh, per-face vertices so the CAD edges stay sharp; area-weighted normals within a face) and writes
one glTF mesh per product and one node per placed instance. Units: the STEP's mm under a root node scaled to metres.
Each node carries its STEP instance label and, parsed from it, extras {part, group, body, material}.
Usage: python3 sim/step_to_glb.py docs/geometry/tube/tube-r150-n8-wound-g0p5-6br.step [out.glb] [--deflection 0.1]
       [--json model.json]   (viewer: tools/step-viewer/)
"""
import argparse
import json
import os
import struct

import numpy as np


def read_assembly(path):
    """products {key: (shape, colour, name)} and instances [(key, 4x4 matrix, label)] from an XCAF STEP."""
    from OCP.STEPCAFControl import STEPCAFControl_Reader
    from OCP.TDocStd import TDocStd_Document
    from OCP.TCollection import TCollection_ExtendedString
    from OCP.XCAFDoc import XCAFDoc_DocumentTool, XCAFDoc_ColorType
    from OCP.TDF import TDF_Label, TDF_ChildIterator
    from OCP.TDataStd import TDataStd_Name
    from OCP.TopLoc import TopLoc_Location
    from OCP.Quantity import Quantity_Color
    doc = TDocStd_Document(TCollection_ExtendedString("XmlOcaf"))
    rd = STEPCAFControl_Reader(); rd.SetNameMode(True); rd.SetColorMode(True)
    rd.ReadFile(path); rd.Transfer(doc)
    tool = XCAFDoc_DocumentTool.ShapeTool_s(doc.Main())
    ctool = XCAFDoc_DocumentTool.ColorTool_s(doc.Main())

    def nm(lab):
        a = TDataStd_Name()
        return a.Get().ToExtString() if lab.FindAttribute(TDataStd_Name.GetID_s(), a) else ""

    def colour(lab):
        c = Quantity_Color()
        for t in (XCAFDoc_ColorType.XCAFDoc_ColorSurf, XCAFDoc_ColorType.XCAFDoc_ColorGen):
            if ctool.GetColor_s(lab, t, c):
                return (c.Red(), c.Green(), c.Blue())
        return (0.7, 0.7, 0.7)

    def mat(loc):
        t = loc.Transformation()
        M = np.eye(4)
        for i in range(3):
            for j in range(4):
                M[i, j] = t.Value(i + 1, j + 1)
        return M
    products, instances = {}, []

    def walk(lab, loc, label):
        if tool.IsAssembly_s(lab):
            it = TDF_ChildIterator(lab, False)
            while it.More():
                c = it.Value()
                if tool.IsComponent_s(c):
                    ref = TDF_Label(); tool.GetReferredShape_s(c, ref)
                    walk(ref, loc.Multiplied(tool.GetLocation_s(c)), nm(c))
                it.Next()
        else:
            key = lab.EntryDumpToString() if hasattr(lab, "EntryDumpToString") else nm(lab)
            if key not in products:
                products[key] = (tool.GetShape_s(lab), colour(lab), nm(lab))
            instances.append((key, mat(loc), label))
    it = TDF_ChildIterator(tool.Label(), False)
    while it.More():
        lab = it.Value()
        if tool.IsFree_s(lab) and tool.IsShape_s(lab):
            walk(lab, TopLoc_Location(), nm(lab))
        it.Next()
    return products, instances


def srgb_to_linear(c):
    """glTF base colours are linear; the STEP colours are display (sRGB) values."""
    return tuple(x / 12.92 if x <= 0.04045 else ((x + 0.055) / 1.055) ** 2.4 for x in c)


def tessellate(shape, deflection=0.1, angular=0.15):
    """positions (N, 3) float32, normals (N, 3) float32, indices (M, 3) uint32; vertices are per face."""
    from OCP.BRepMesh import BRepMesh_IncrementalMesh
    from OCP.BRep import BRep_Tool
    from OCP.TopoDS import TopoDS
    from OCP.TopExp import TopExp_Explorer
    from OCP.TopAbs import TopAbs_FACE, TopAbs_REVERSED
    from OCP.TopLoc import TopLoc_Location
    BRepMesh_IncrementalMesh(shape, deflection, False, angular, True)
    P, N, I, base = [], [], [], 0
    e = TopExp_Explorer(shape, TopAbs_FACE)
    while e.More():
        f = TopoDS.Face(e.Current()); loc = TopLoc_Location()
        tri = BRep_Tool.Triangulation_s(f, loc)
        if tri is not None and tri.NbTriangles() > 0:
            tr = loc.Transformation()
            p = np.array([[q.X(), q.Y(), q.Z()] for q in (tri.Node(i).Transformed(tr) for i in range(1, tri.NbNodes() + 1))])
            t = np.array([tri.Triangle(k).Get() for k in range(1, tri.NbTriangles() + 1)], dtype=np.int64) - 1
            if f.Orientation() == TopAbs_REVERSED:
                t = t[:, [0, 2, 1]]
            fn = np.cross(p[t[:, 1]] - p[t[:, 0]], p[t[:, 2]] - p[t[:, 0]])         # area-weighted face normals
            n = np.zeros_like(p)
            for k in range(3):
                np.add.at(n, t[:, k], fn)
            n /= np.maximum(np.linalg.norm(n, axis=1, keepdims=True), 1e-30)
            P.append(p); N.append(n); I.append(t + base); base += len(p)
        e.Next()
    if not P:
        return None
    return (np.concatenate(P).astype(np.float32), np.concatenate(N).astype(np.float32),
            np.concatenate(I).astype(np.uint32))


def parse_label(label):
    """'group / name - desc [material, body]' (sim/tube_geometry.Machine.add) -> extras."""
    out = dict(label=label)
    try:
        group, rest = label.split(" / ", 1)
        name = rest.split(" - ", 1)[0]
        mat, body = rest.rsplit("[", 1)[1].rstrip("]").rsplit(", ", 1)
        out.update(group=group, part=name, material=mat, body=body)
    except (ValueError, IndexError):
        pass
    return out


def write_glb(path, meshes, nodes, scale=1e-3, title=""):
    """meshes: [(name, colour, metal, P, N, I)], nodes: [(mesh index, 4x4 matrix in mm, name, extras)]."""
    blob, views, accessors, gl_meshes, materials = bytearray(), [], [], [], []

    def add_view(arr, target):
        while len(blob) % 4:
            blob.append(0)
        off = len(blob)
        blob.extend(arr.tobytes())
        views.append(dict(buffer=0, byteOffset=off, byteLength=arr.nbytes, target=target))
        return len(views) - 1
    for k, (name, col, metal, P, N, I) in enumerate(meshes):
        vp = add_view(P, 34962); vn = add_view(N, 34962); vi = add_view(I.reshape(-1), 34963)
        accessors += [dict(bufferView=vp, componentType=5126, count=len(P), type="VEC3",
                           min=[float(x) for x in P.min(0)], max=[float(x) for x in P.max(0)]),
                      dict(bufferView=vn, componentType=5126, count=len(N), type="VEC3"),
                      dict(bufferView=vi, componentType=5125, count=int(I.size), type="SCALAR")]
        materials.append(dict(name=name, pbrMetallicRoughness=dict(baseColorFactor=[*map(float, srgb_to_linear(col)), 1.0],
                                                                    metallicFactor=metal, roughnessFactor=0.55),
                              doubleSided=True))
        gl_meshes.append(dict(name=name, primitives=[dict(attributes=dict(POSITION=3 * k, NORMAL=3 * k + 1),
                                                          indices=3 * k + 2, material=k)]))
    gl_nodes = [dict(name=title or "assembly", scale=[scale] * 3, children=list(range(1, len(nodes) + 1)))]
    for mi, M, name, extras in nodes:
        gl_nodes.append(dict(mesh=mi, name=name, matrix=[float(x) for x in M.T.reshape(-1)], extras=extras))
    gltf = dict(asset=dict(version="2.0", generator="DCCREG sim/step_to_glb.py"), scene=0, scenes=[dict(nodes=[0])],
                nodes=gl_nodes, meshes=gl_meshes, materials=materials, accessors=accessors, bufferViews=views,
                buffers=[dict(byteLength=len(blob))])
    js = json.dumps(gltf, separators=(",", ":")).encode()
    js += b" " * (-len(js) % 4)
    while len(blob) % 4:
        blob.append(0)
    with open(path, "wb") as f:
        f.write(struct.pack("<III", 0x46546C67, 2, 12 + 8 + len(js) + 8 + len(blob)))
        f.write(struct.pack("<II", len(js), 0x4E4F534A)); f.write(js)
        f.write(struct.pack("<II", len(blob), 0x004E4942)); f.write(bytes(blob))
    return path


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("step")
    ap.add_argument("out", nargs="?")
    ap.add_argument("--deflection", type=float, default=0.1)
    ap.add_argument("--json", help="also write the GLB base64-wrapped in this JSON file (for hosts that do not serve .glb)")
    a = ap.parse_args()
    out = a.out or os.path.splitext(a.step)[0] + ".glb"
    products, instances = read_assembly(a.step)
    keys, meshes, n_tri = {}, [], 0
    for key, (shape, col, name) in products.items():
        t = tessellate(shape, a.deflection)
        if t is None:
            continue
        metal = 0.6 if any(w in name.lower() for w in ("steel", "bearing", "al ", "al vane", "al plate", "sife", "nife",
                                                        "m235", "laminat", "cu ")) else 0.05
        keys[key] = len(meshes)
        meshes.append((name, col, metal, *t))
        n_tri += len(t[2])
    nodes = [(keys[k], M, lab, parse_label(lab)) for k, M, lab in instances if k in keys]
    write_glb(out, meshes, nodes, title=os.path.basename(a.step))
    if a.json:
        import base64
        json.dump(dict(format="glb-base64", source=f"{a.step} via sim/step_to_glb.py",
                       glb=base64.b64encode(open(out, "rb").read()).decode()), open(a.json, "w"))
    print(json.dumps(dict(out=out, bytes=os.path.getsize(out), products=len(meshes), instances=len(nodes),
                          triangles_unique=n_tri,
                          triangles_drawn=int(sum(len(meshes[m][5]) for m, *_ in nodes)))))


if __name__ == "__main__":
    main()
