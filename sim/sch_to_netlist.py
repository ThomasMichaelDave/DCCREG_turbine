#!/usr/bin/env python3
"""
sim/sch_to_netlist.py — reconstruct the netlist directly from the KiCad schematic geometry.
============================================================================================
The shipped `.net` export was a stale/partial capture (37 comps, 2 of 8 gaps). TMD's
`DCCREG_Turbine_circuit.kicad_sch` is the live source of record (43 comps, all 8 commutation gaps),
but it has NO net labels -- connectivity is pure wire geometry + junctions. This tool extracts the
connectivity directly from the schematic so the topology-driven re-derive consumes TMD's actual
design without waiting on a KiCad re-export.

Method [ME]: parse the lib_symbol pin offsets; transform each instance pin to absolute coords
(at/angle/mirror); union-find over coincident wire endpoints + pin positions. Validation: every pin
must land on a wire endpoint (the calibration hit 82/82 -> the transform is exact). Reproduces the
non-gap nets of the old export, so the gap nets are trustworthy.
"""
import math
import os
import re
import sys
from collections import defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
SCH = os.path.join(ROOT, "docs", "kicad", "DCCREG_Turbine_circuit.kicad_sch")

GAP_REFS = {"SG1", "SG2", "SG3a1", "SG3b1", "SG4a1", "SG4b1", "BS3", "BS4"}


def _bal(s, st):
    d = 0
    for x in range(st, len(s)):
        if s[x] == "(":
            d += 1
        elif s[x] == ")":
            d -= 1
            if d == 0:
                return s[st:x + 1]
    return s[st:]


def extract(sch_path=SCH):
    """Return (components: {ref: lib_id}, nets: [sorted [ref.pin, ...]], calib_hits)."""
    t = open(sch_path).read()
    # lib pin offsets
    libpins = {}
    lib = _bal(t, t.find("(lib_symbols"))
    for m in re.finditer(r'\(symbol "([^"]+)"', lib):
        name = m.group(1)
        if ":" not in name:
            continue
        b = _bal(lib, m.start())
        pins = re.findall(r"\(pin\s+\w+\s+\w+\s*\(at ([-\d.]+) ([-\d.]+) ([-\d.]+)\)\s*\(length ([-\d.]+)\)",
                          b, re.S)
        nums = re.findall(r'\(number "([^"]+)"', b)
        libpins[name] = [(num, float(x), float(y)) for (x, y, a, L), num in zip(pins, nums)]
    # instances
    insts, comps = [], {}
    for m in re.finditer(r'\(symbol\s*\(lib_id "([^"]+)"', t):
        b = _bal(t, m.start()); libid = m.group(1)
        at = re.search(r"\(at ([-\d.]+) ([-\d.]+) ([-\d.]+)\)", b)
        ref = re.search(r'\(property "Reference" "([^"]+)"', b)
        mir = re.search(r"\(mirror (\w+)\)", b)
        if not ref or libid not in libpins:
            continue
        insts.append(dict(ref=ref.group(1), lib=libid, ox=float(at.group(1)), oy=float(at.group(2)),
                          ang=float(at.group(3)), mir=mir.group(1) if mir else None))
        comps[ref.group(1)] = libid
    # wires
    wires = []
    for m in re.finditer(r"\(wire\s*\(pts", t):
        b = _bal(t, m.start())
        pts = re.findall(r"\(xy ([-\d.]+) ([-\d.]+)\)", b)
        wires.append(((round(float(pts[0][0]), 2), round(float(pts[0][1]), 2)),
                      (round(float(pts[1][0]), 2), round(float(pts[1][1]), 2))))

    def pinabs(inst, lx, ly):
        x0, y0 = lx, ly
        if inst["mir"] == "y":
            x0 = -x0
        if inst["mir"] == "x":
            y0 = -y0
        a = math.radians(inst["ang"])
        return (round(inst["ox"] + x0 * math.cos(a) - y0 * math.sin(a), 2),
                round(inst["oy"] + x0 * math.sin(a) + y0 * math.cos(a), 2))

    parent = {}

    def find(x):
        parent.setdefault(x, x)
        while parent[x] != x:
            parent[x] = parent[parent[x]]; x = parent[x]
        return x

    for a, b in wires:
        parent[find(a)] = find(b)
    wpts = {p for w in wires for p in w}
    pinmap = defaultdict(list)
    hits = 0; tot = 0
    for inst in insts:
        for num, lx, ly in libpins[inst["lib"]]:
            c = pinabs(inst, lx, ly); find(c); tot += 1
            if c in wpts:
                hits += 1
            pinmap[c].append(f"{inst['ref']}.{num}")
    nets = defaultdict(list)
    for c, refs in pinmap.items():
        nets[find(c)].extend(refs)
    return comps, [sorted(v) for v in nets.values()], (hits, tot)


# node signatures read FROM the real schematic nets (not the lumped assumption)
def node_of(members):
    s = set(members)
    if {"C1.2", "Ca1.1"} <= s:
        return "1 (A rail)"
    if {"C2.2", "Cb1.2"} <= s:
        return "4 (B rail)"
    if "Ca1.2" in s and any(x.startswith("C_AR") for x in s):
        return "2 (AR bank)"
    if "Cb1.1" in s and any(x.startswith("C_BR") for x in s):
        return "3 (BR bank)"
    if "Cx3.1" in s:
        return "7 (island A)"
    if "Cx4.2" in s:
        return "8 (island B)"
    if {"C1.1", "L_R1.1"} <= s:
        return "R-A (resonator A end)"
    if {"C2.1", "L_R2.2"} <= s:
        return "R-B (resonator B end)"
    return None


def gap_topology(sch_path=SCH):
    """Return {gap_ref: (node_a, node_b)} read from the real schematic."""
    comps, nets, _ = extract(sch_path)
    ref_nodes = defaultdict(set)
    for n in nets:
        nd = node_of(n)
        for x in n:
            ref = x.split(".")[0]
            if ref in GAP_REFS and nd:
                ref_nodes[ref].add(nd)
    return {g: tuple(sorted(v)) for g, v in ref_nodes.items()}


def main():
    print("=" * 90)
    print("SCH-TO-NETLIST — connectivity reconstructed from TMD's KiCad schematic geometry")
    print("=" * 90)
    comps, nets, (hits, tot) = extract()
    print(f"\nsource: {os.path.relpath(SCH, ROOT)}")
    print(f"calibration: {hits}/{tot} pins land on wire endpoints "
          f"({'EXACT — transform validated' if hits == tot else 'PARTIAL'})")
    print(f"{len(comps)} components, {len(nets)} nets\n")
    print("the 8 commutation gaps, as wired in the schematic:")
    topo = gap_topology()
    roles = {"SG3a1": "branch-A LOAD (rail->island)", "SG3b1": "branch-A FIRE (island->BR bank)",
             "SG4a1": "branch-B LOAD (rail->island)", "SG4b1": "branch-B FIRE (island->AR bank)",
             "BS3": "branch-A FE backstop (parallel to SG3b fire)",
             "BS4": "branch-B FE backstop (parallel to SG4b fire)",
             "SG1": "AR-bank -> resonator A end (bank fire to tank)",
             "SG2": "BR-bank -> resonator B end (bank fire to tank)"}
    for g in ["SG3a1", "SG3b1", "SG4a1", "SG4b1", "BS3", "BS4", "SG1", "SG2"]:
        print(f"  {g:7s} {str(topo.get(g, '?')):44s} {roles.get(g, '')}")
    return comps, nets, topo


if __name__ == "__main__":
    main()
