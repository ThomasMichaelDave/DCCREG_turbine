#!/usr/bin/env python3
"""
sim/topology_recon.py — r0.2: net-for-net recon vs the r0_13 EE schematic.
==========================================================================
r0.1 returned TOPOLOGY-INCOMPLETE because no EE-schematic DXF was in the repo (only
the r0_6 radial-layout template: nodes 1-8, no split resonator, no motor). r0.2 was
GATED on the r0_13 schematic being COMMITTED so its drawn nets could be traced and
diffed net-for-net against deck v0.3.

GATING PRECONDITION CHECK (Stage A, the first thing this run does): r0_13 is NOT in
the repo. An exhaustive scan of EVERY .dxf blob across ALL git history finds only
three files -- r0_6, r0.1, r0.2 -- and ALL are radial-layout templates: NONE has
ND9/10 (the split resonator), NONE has the motor (L_A/C_AR/L_B/C_BR/quadricores),
NONE has a schematic/wire layer, NONE has any INSERT (polar array). So the
net-for-net wiring diff the brief asks for is IMPOSSIBLE -- there are no drawn nets
to trace. The precondition fails; the verdict is TOPOLOGY-INCOMPLETE again, with the
ESCALATION that this is the SECOND brief (r0_15, then r0_13) blocked on a schematic
DXF that has never been committed.

This run does NOT fabricate a net-trace of a non-existent file. It (1) documents the
unmet precondition with the exhaustive DXF inventory, (2) re-affirms the r0.1
reconciled graph (the 42-component manifest, the four [?] resolved from freeze §5 +
physics -- still the best available authority), and (3) emits a drawing punch-list
(dxf_flags.md) of exactly what the schematic DXF must contain to unblock CONFIRMED.

DXF + frozen read-only (empty-diff asserted). Tiers [OC]/[IR]/[RH].
"""
import os
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)

# the r0.1 reconciled manifest (re-affirmed; the prior the drawn nets were to test)
MANIFEST = (
    [("C1", 1, 5), ("C2", 4, 6), ("Ca", 1, 2), ("Cb", 3, 4), ("Cx3", 7, 3), ("Cx4", 8, 2),
     ("SG1", 2, 5), ("SG2", 3, 6), ("SG3a", 1, 7), ("SG3b", 7, 3), ("BS3", 3, 7),
     ("SG4a", 4, 8), ("SG4b", 8, 2), ("BS4", 2, 8),
     ("L_R1", 5, 9), ("L_R2", 10, 6), ("C_R", 9, 10), ("K1", None, None)]
    + [(f"L_A{i}", 1, 10 + i) for i in range(1, 7)] + [(f"C_AR{i}", 10 + i, 2) for i in range(1, 7)]
    + [(f"L_B{i}", 4, 16 + i) for i in range(1, 7)] + [(f"C_BR{i}", 16 + i, 3) for i in range(1, 7)]
)
QMARKS = {"SG3a": (1, 7), "SG4a": (4, 8), "BS3": (3, 7), "BS4": (2, 8)}


def dxf_inventory():
    """Scan EVERY .dxf blob across ALL git history; classify each as EE-schematic
    (ND9/10 + motor + nets) or radial-layout. Returns the inventory + whether any
    schematic exists."""
    try:
        import ezdxf
    except Exception as e:
        return [], False, f"ezdxf unavailable: {e}"
    hashes = subprocess.run(["git", "log", "--all", "--format=%H"], cwd=ROOT,
                            capture_output=True, text=True).stdout.split()
    seen = {}
    for h in hashes:
        for f in subprocess.run(["git", "ls-tree", "-r", "--name-only", h], cwd=ROOT,
                                capture_output=True, text=True).stdout.split("\n"):
            if f.endswith(".dxf") and f not in seen:
                seen[f] = h
    inv = []; any_schem = False
    for f, h in seen.items():
        blob = subprocess.run(["git", "show", f"{h}:{f}"], cwd=ROOT, capture_output=True).stdout
        try:
            tf = tempfile.NamedTemporaryFile(suffix=".dxf", delete=False); tf.write(blob); tf.close()
            d = ezdxf.readfile(tf.name); ls = [l.dxf.name for l in d.layers]
            nd910 = any("ND9" in x or "ND10" in x for x in ls)
            motor = any(k in x.upper() for x in ls for k in
                        ("L_A", "C_AR", "L_B", "C_BR", "QUADR", "C-CORE", "MOTOR"))
            schem = any(k in x.upper() for x in ls for k in ("SCHEM", "EE-", "-NET", "WIRE"))
            ins = len(list(d.modelspace().query("INSERT")))
            is_schem = nd910 and motor
            any_schem = any_schem or is_schem
            inv.append(dict(name=f.split("/")[-1], layers=len(ls), nd910=nd910, motor=motor,
                            schem=schem, inserts=ins, is_schematic=is_schem))
            os.unlink(tf.name)
        except Exception as e:
            inv.append(dict(name=f, layers=0, error=str(e)))
    return inv, any_schem, None


def main():
    print("=" * 84)
    print("TOPOLOGY RECON r0.2 — net-for-net vs r0_13 (gated on r0_13 being committed)")
    print("=" * 84)

    diff = subprocess.run(["git", "diff", "--name-only", "--", "reference/", "shuttle_core.py",
                           "index.html", "docs/"], cwd=ROOT, capture_output=True, text=True).stdout.strip()
    print(f"\n[check 1] frozen + DXF read-only (hygiene): {'PASS' if diff == '' else 'FAIL ' + diff}")

    print("\nSTAGE A — gating precondition: is the r0_13 EE schematic committed?")
    inv, any_schem, err = dxf_inventory()
    print(f"  exhaustive DXF inventory across ALL git history ({len(inv)} distinct files):")
    print(f"  {'file':50s} {'layers':>6s} {'ND9/10':>7s} {'motor':>6s} {'nets':>5s} {'INSERTs':>7s} {'EE-schem?':>9s}")
    for r in inv:
        if "error" in r:
            print(f"  {r['name']:50s} (parse error)"); continue
        print(f"  {r['name']:50s} {r['layers']:>6d} {str(r['nd910']):>7s} {str(r['motor']):>6s} "
              f"{str(r['schem']):>5s} {r['inserts']:>7d} {str(r['is_schematic']):>9s}")
    print(f"  [check 2] r0_13 (or ANY EE schematic with ND9/10 + motor + drawn nets): "
          f"{'PRESENT' if any_schem else 'ABSENT'}")
    if any_schem:
        print("  -> precondition MET; (net-tracer would run here). [not reached this rev]")
        return 0
    print(f"  -> GATING PRECONDITION UNMET. All three committed DXFs are RADIAL-LAYOUT templates")
    print(f"     (no ND9/10, no motor, no schematic layer, zero INSERTs). There are NO DRAWN NETS to")
    print(f"     trace -- the net-for-net diff is impossible. (Refusing to fabricate a trace of a file")
    print(f"     that isn't there.)")

    print("\nSTAGE B-D — re-affirm the r0.1 reconciled graph (the best available authority):")
    print(f"  the 42-component manifest stands (freeze §5 node map + Block-D Cem map + charge-pump")
    print(f"  physics); the four [?] resolved: " +
          ", ".join(f"{k}={v}" for k, v in QMARKS.items()) + " (blocking sense = reverse of the fire).")
    print(f"  A/B symmetry exact (r0.1); motor + split resonator still UNDRAWN in any DXF.")
    print(f"  [check 3-7] UNCHANGED from r0.1 -- cannot be advanced to DXF-sourced without the schematic.")

    print("\nSTAGE E — escalation + drawing punch-list:")
    _punch_list(inv)
    _edge_csv()

    print("\nVERDICT:")
    print(f"  TOPOLOGY-INCOMPLETE (precondition unmet) — r0_13 is NOT committed; the net-for-net")
    print(f"  wiring diff the brief requires cannot run. This is the SECOND brief (r0_15, then r0_13)")
    print(f"  gated on a schematic DXF that has never entered the repo -- the recurring blocker is the")
    print(f"  schematic itself, not the deck. The r0.1 result stands: the reconcilable graph (the 18")
    print(f"  core/comm/resonator components + the four [?] from freeze §5 + physics) is correct and")
    print(f"  the deck's connectivity is trustworthy where checkable; what is missing is the DRAWING")
    print(f"  (the motor, ND9/10, and the drawn nets) -- a representation gap, not a deck error.")
    print(f"  ACTION: commit the r0_13 EE schematic (per dxf_flags.md), then re-run this exact tracer.")
    print(f"  Until then the graph cannot be marked DXF-sourced and v0.11 cannot freeze against r0_13.")
    print(f"  -> TOPOLOGY-INCOMPLETE")

    diff = subprocess.run(["git", "diff", "--name-only", "--", "reference/", "shuttle_core.py",
                           "index.html", "docs/"], cwd=ROOT, capture_output=True, text=True).stdout.strip()
    assert diff == "", f"read-only violated: {diff}"
    print("\n[read-only final assert] PASS (authorities untouched)")
    print("VERDICT: TOPOLOGY-INCOMPLETE (gating precondition unmet — r0_13 absent)")
    return 0


def _punch_list(inv):
    path = os.path.join(ROOT, "dxf_flags.md")
    latest = max((r for r in inv if "error" not in r), key=lambda r: r["layers"])
    with open(path, "w") as f:
        f.write("# DXF punch-list — what the EE-schematic DXF (the brief's r0_13/r0_15) must contain\n\n")
        f.write("**Status:** the recon is BLOCKED on a schematic DXF that has never been committed. ")
        f.write("Two briefs (r0_15, then r0_13) assumed it exists; an exhaustive scan of all git ")
        f.write("history finds only radial-layout templates. To unblock `TOPOLOGY-CONFIRMED` and v0.11, ")
        f.write("an EE-schematic DXF must be committed with:\n\n")
        f.write("1. **Drawn nets** (wires/polylines + symbol terminals), not just layer-named bodies — so\n")
        f.write("   connectivity can be traced by spatial junction (the methodological point of r0.2).\n")
        f.write("2. **The split resonator** — nodes ND9/ND10 with L_R1(5-9) + C_R(9-10) + L_R2(10-6).\n")
        f.write("   (Absent from every committed DXF; the radial templates draw a single hub coil.)\n")
        f.write("3. **The 24 motor components** — L_A1-6/C_AR1-6 (nodes 11-16, across Ca: coil-outer ND1,\n")
        f.write("   cap-inner ND2) and L_B1-6/C_BR1-6 (nodes 17-22, across Cb: ND4/ND3). The 12 quadricore\n")
        f.write("   irons + 440 nF caps. (Undrafted in every committed DXF.)\n")
        f.write("4. **The four [?] gaps as drawn nets** — SG3a 1-7, SG4a 4-8 (load), BS3 3-7, BS4 2-8\n")
        f.write("   (backstop, blocking the reverse of the 7->3 / 8->2 fire) — to confirm the freeze-§5 +\n")
        f.write("   physics resolution against the actual drawing.\n\n")
        f.write(f"**Latest committed DXF:** `{latest['name']}` ({latest['layers']} layers, radial layout, ")
        f.write("no ND9/10, no motor, 0 INSERTs). It is a geometry template (node->component via layer ")
        f.write("names), not a wired schematic — sufficient for r0.1's layer-name recon, not for r0.2's ")
        f.write("net-for-net diff.\n\n")
        f.write("Once committed, re-run `python3 sim/topology_recon.py` — the gate auto-detects the ")
        f.write("schematic (ND9/10 + motor) and proceeds to the net-trace.\n")
    print(f"  wrote {os.path.relpath(path, ROOT)} (the drawing punch-list for the next DXF rev)")


def _edge_csv():
    path = os.path.join(ROOT, "topology_edge_list.csv")
    with open(path, "w") as f:
        f.write("component,node_a,node_b,source,qmark_resolved,authority\n")
        for c, a, b in MANIFEST:
            q = c in QMARKS
            src = "freeze-nodemap+physics (NOT yet DXF-sourced — r0_13 absent)"
            f.write(f"{c},{a if a is not None else ''},{b if b is not None else ''},"
                    f"\"{src}\",{q},\"freeze-§5+physics\"\n")
        f.write("#status,INCOMPLETE — r0_13 EE schematic absent; graph not yet DXF-sourced\n")
        f.write("#qmarks,SG3a=1-7;SG4a=4-8;BS3=3-7;BS4=2-8 (freeze-§5+physics, awaiting drawn-net confirm)\n")
    print(f"  wrote {os.path.relpath(path, ROOT)} (manifest of record — source still freeze, not DXF)")


if __name__ == "__main__":
    sys.exit(main())
