"""rebuild/kicad/make_kicad.py -- the rebuild's schematics as KiCad 10 projects, and their netlist check.

The designer (2026-10-15): "We will first install kicad on my machine so we can deliver the proper netlist"; "When you
generate the schematic, provide the proper text in the schematic to explain all components"; "when you are done with
creating the schematic, open the GUI and let me reorganize so it becomes readable by a human too."

Two sheets, each its own KiCad project:
  s0_base/s0_base.kicad_sch   S0: de Queiroz Fig. 1 at the paper's example values (frozen topology, 42747f4);
  s1_tube/s1_tube.kicad_sch   S1: the S0 core at the tube's air values, plus the pulsed core's load: C_k across
                              N1-N4 and each core electrode's stray to REF (rebuild/s1_tube/s1-pulsed-core-findings.md).
Every component carries its explanation on the sheet (a legend keyed by reference, and the symbol's Description
field); every net is named (REF, N1-N4).

The layout is the generator's first placement. The designer rearranges it in the GUI and saves; from then on the
saved sheet is the drawing of record and this script does not overwrite it (use --force to regenerate). What makes
the netlist of record is the check, which runs on whatever sheet is there:
  kicad-cli exports the netlist; its connectivity must equal the source topology node for node
  (S0: rebuild/s0_base/s0_base.py TOPOLOGY and its deck s0_base.cir; S1: S0's TOPOLOGY plus the additions, and the
  solver circuit of rebuild/s1_tube/s1_pulsed_core.py); kicad-cli's ERC is recorded alongside.

Writes the projects (if absent, or with --force), the exported netlists s*/s*.net, and
rebuild/kicad/kicad_check_results.json.
Usage: python3 rebuild/kicad/make_kicad.py [--force] [--check-only]
"""
import json
import os
import textwrap
import re
import subprocess
import sys
import uuid

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
KICAD_BIN = os.environ.get("KICAD_BIN", os.path.join(os.environ.get("LOCALAPPDATA", ""), "Programs", "KiCad", "10.0",
                                                     "bin"))
KICAD_CLI = os.path.join(KICAD_BIN, "kicad-cli.exe" if os.name == "nt" else "kicad-cli")
SYMLIB = os.path.join(KICAD_BIN, "..", "share", "kicad", "symbols", "Device.kicad_sym")
TEMPLATE_PRO = os.path.join(KICAD_BIN, "..", "share", "kicad", "template", "kicad.kicad_pro")
U = 2.54                                       # the layout grid, mm
OX, OY = 8, 14                                 # the drawing's offset from the sheet origin, grid units

sys.path.insert(0, os.path.join(ROOT, "rebuild", "s0_base"))
sys.path.insert(0, os.path.join(ROOT, "rebuild", "s1_tube"))


def uid(*key):
    return str(uuid.uuid5(uuid.NAMESPACE_URL, "dccreg-rebuild/" + "/".join(map(str, key))))


def q(s):
    return '"' + s.replace("\\", "\\\\").replace('"', '\\"').replace("\n", "\\n") + '"'


# ---------------------------------------------------------------- the library symbols, copied from KiCad's Device lib
def lib_block(name):
    txt = open(SYMLIB, encoding="utf-8").read().replace("\r\n", "\n")
    i = txt.index(f'\n\t(symbol "{name}"\n')
    depth, j = 0, i + 2
    for j in range(i + 2, len(txt)):
        if txt[j] == "(":
            depth += 1
        elif txt[j] == ")":
            depth -= 1
            if depth == 0:
                break
    blk = txt[i + 2:j + 1]
    return blk.replace(f'(symbol "{name}"', f'(symbol "Device:{name}"', 1)


# pin offsets in symbol coordinates (y up), from Device.kicad_sym: C / C_Variable pins 1 (0, 3.81), 2 (0, -3.81);
# D pin 1 = K (-3.81, 0), pin 2 = A (3.81, 0)
PINS = {"C": {"1": (0, 3.81), "2": (0, -3.81)}, "C_Variable": {"1": (0, 3.81), "2": (0, -3.81)},
        "D": {"1": (-3.81, 0), "2": (3.81, 0)}}


def pin_xy(sym, at, rot, pin):
    """the schematic position of a pin: y flipped, then rotated counter-clockwise on screen by rot degrees."""
    px, py = PINS[sym][pin]
    x, y = px, -py
    c, s = {0: (1, 0), 90: (0, 1), 180: (-1, 0), 270: (0, -1)}[rot]
    return (round(at[0] + x * c + y * s, 4), round(at[1] - x * s + y * c, 4))


# ---------------------------------------------------------------- the sheets
class Sheet:
    def __init__(self, name, title, comment):
        self.name, self.title, self.comment = name, title, comment
        self.parts, self.wires, self.labels, self.texts = [], [], [], []

    def part(self, ref, sym, at, rot, value, desc, bom=True):
        at = ((at[0] + OX) * U, (at[1] + OY) * U)
        self.parts.append(dict(ref=ref, sym=sym, at=at, rot=rot, value=value, desc=desc, bom=bom))
        return {p: pin_xy(sym, at, rot, p) for p in PINS[sym]}

    def wire_mm(self, *pts):
        for a, b in zip(pts[:-1], pts[1:]):
            self.wires.append((a, b))

    def label(self, name, at_u, rot=0):
        self.labels.append((name, (round((at_u[0] + OX) * U, 4), round((at_u[1] + OY) * U, 4)), rot))

    def text(self, s, at_u, size=1.27, bold=False, width=84):
        """free text, wrapped to `width` characters (the sheet's right-hand column), hanging indent kept."""
        lines = []
        for ln in s.split("\n"):
            ind = len(ln) - len(ln.lstrip(" -"))
            lines += textwrap.wrap(ln, width, subsequent_indent=" " * ind) or [""]
        self.texts.append(("\n".join(lines), (at_u[0] * U, at_u[1] * U), size, bold))
        return len(lines)

    # wires end where another wire passes: split there, and put a junction dot where three or more ends meet
    def _resolve(self):
        segs = list(self.wires)
        changed = True
        while changed:
            changed = False
            ends = {p for s in segs for p in s}
            for i, (a, b) in enumerate(segs):
                for p in ends:
                    if p in (a, b):
                        continue
                    if a[0] == b[0] == p[0] and min(a[1], b[1]) < p[1] < max(a[1], b[1]) or \
                       a[1] == b[1] == p[1] and min(a[0], b[0]) < p[0] < max(a[0], b[0]):
                        segs[i:i + 1] = [(a, p), (p, b)]
                        changed = True
                        break
                if changed:
                    break
        cnt = {}
        for s in segs:
            for p in s:
                cnt[p] = cnt.get(p, 0) + 1
        pins = {xy for pt in self.parts for xy in (pin_xy(pt["sym"], pt["at"], pt["rot"], k) for k in PINS[pt["sym"]])}
        junc = [p for p, n in cnt.items() if n + (1 if p in pins else 0) >= 3]
        return segs, junc

    def render(self, project):
        segs, junc = self._resolve()
        root = uid(self.name, "sheet")
        out = ["(kicad_sch", "\t(version 20260101)", '\t(generator "eeschema")', '\t(generator_version "10.0")',
               f"\t(uuid {q(root)})", '\t(paper "A3")', "\t(title_block", f"\t\t(title {q(self.title)})",
               '\t\t(date "2026-10-15")', '\t\t(rev "generated")', '\t\t(company "DCCREG turbine rebuild")',
               f"\t\t(comment 1 {q(self.comment)})", '\t\t(comment 2 "generated by rebuild/kicad/make_kicad.py")',
               "\t)", "\t(lib_symbols"]
        for sym in sorted({p["sym"] for p in self.parts}):
            out.append("\t\t" + lib_block(sym).replace("\n", "\n\t"))
        out.append("\t)")
        for p in junc:
            out += ["\t(junction", f"\t\t(at {p[0]} {p[1]})", "\t\t(diameter 0)", "\t\t(color 0 0 0 0)",
                    f"\t\t(uuid {q(uid(self.name, 'j', p))})", "\t)"]
        for a, b in segs:
            out += ["\t(wire", "\t\t(pts", f"\t\t\t(xy {a[0]} {a[1]}) (xy {b[0]} {b[1]})", "\t\t)",
                    "\t\t(stroke", "\t\t\t(width 0)", "\t\t\t(type default)", "\t\t)",
                    f"\t\t(uuid {q(uid(self.name, 'w', a, b))})", "\t)"]
        for name, at, rot in self.labels:
            out += [f"\t(label {q(name)}", f"\t\t(at {at[0]} {at[1]} {rot})", "\t\t(effects", "\t\t\t(font",
                    "\t\t\t\t(size 1.524 1.524)", "\t\t\t\t(bold yes)", "\t\t\t)", "\t\t\t(justify left bottom)", "\t\t)",
                    f"\t\t(uuid {q(uid(self.name, 'l', name, at))})", "\t)"]
        for k, (s, at, size, bold) in enumerate(self.texts):
            out += [f"\t(text {q(s)}", "\t\t(exclude_from_sim yes)", f"\t\t(at {at[0]:.2f} {at[1]:.2f} 0)",
                    "\t\t(effects", "\t\t\t(font", f"\t\t\t\t(size {size} {size})"] + \
                   (["\t\t\t\t(bold yes)"] if bold else []) + \
                   ["\t\t\t)", "\t\t\t(justify left top)", "\t\t)", f"\t\t(uuid {q(uid(self.name, 't', k))})", "\t)"]
        for p in self.parts:
            x, y = p["at"]
            vert = p["rot"] in (0, 180) and p["sym"].startswith("C") or p["rot"] in (90, 270) and p["sym"] == "D"
            rx, ry = (x + 3.81, y - 1.27) if vert else (x, y - 3.81)
            vx, vy = (x + 3.81, y + 1.27) if vert else (x, y + 3.81)
            just = "(justify left)" if vert else ""

            fa = 90 if p["rot"] in (90, 270) else 0          # the field's angle: it turns with the symbol

            def prop(k, v, px, py, hide=False, size=1.27):
                r = [f"\t\t(property {q(k)} {q(v)}", f"\t\t\t(at {px:.2f} {py:.2f} {fa})"]
                if hide:
                    r.append("\t\t\t(hide yes)")
                r += ["\t\t\t(show_name no)", "\t\t\t(do_not_autoplace no)", "\t\t\t(effects", "\t\t\t\t(font",
                      f"\t\t\t\t\t(size {size} {size})", "\t\t\t\t)"] + ([f"\t\t\t\t{just}"] if just else []) + \
                     ["\t\t\t)", "\t\t)"]
                return r
            out += ["\t(symbol", f'\t\t(lib_id "Device:{p["sym"]}")', f"\t\t(at {x:.2f} {y:.2f} {p['rot']})",
                    "\t\t(unit 1)", "\t\t(body_style 1)", "\t\t(exclude_from_sim no)",
                    f"\t\t(in_bom {'yes' if p['bom'] else 'no'})", "\t\t(on_board yes)",
                    "\t\t(in_pos_files yes)", "\t\t(dnp no)", f"\t\t(uuid {q(uid(self.name, 'p', p['ref']))})"]
            out += prop("Reference", p["ref"], rx, ry, size=1.524)
            out += prop("Value", p["value"], vx, vy)
            out += prop("Footprint", "", x, y, hide=True)
            out += prop("Datasheet", "", x, y, hide=True)
            out += prop("Description", p["desc"].replace("\n", " "), x, y, hide=True)
            for pn in PINS[p["sym"]]:
                out += [f"\t\t(pin {q(pn)}", f"\t\t\t(uuid {q(uid(self.name, 'pin', p['ref'], pn))})", "\t\t)"]
            out += ["\t\t(instances", f"\t\t\t(project {q(project)}", f"\t\t\t\t(path {q('/' + root)}",
                    f"\t\t\t\t\t(reference {q(p['ref'])})", "\t\t\t\t\t(unit 1)", "\t\t\t\t)", "\t\t\t)", "\t\t)", "\t)"]
        out += ["\t(sheet_instances", '\t\t(path "/"', '\t\t\t(page "1")', "\t\t)", "\t)", "\t(embedded_fonts no)", ")"]
        return "\n".join(out) + "\n"


def core(sh, vals, desc):
    """the S0 core, de Queiroz Fig. 1, laid out as the paper draws it: the varicaps at the sides, the transfer
    capacitors on top, the return diodes down to REF, the cross diodes above (grid units of 2.54 mm)."""
    c1 = sh.part("C1", "C_Variable", (20, 52), 0, vals["C1"], desc["C1"])
    c2 = sh.part("C2", "C_Variable", (80, 52), 0, vals["C2"], desc["C2"])
    ca = sh.part("Ca", "C", (30, 30), 90, vals["Ca"], desc["Ca"])          # pin 1 left (N1), pin 2 right (N2)
    cb = sh.part("Cb", "C", (70, 30), 90, vals["Cb"], desc["Cb"])          # pin 1 left (N3), pin 2 right (N4)
    d1 = sh.part("D1", "D", (40, 45), 270, vals["D1"], desc["D1"])         # K up (N2), A down (REF)
    d2 = sh.part("D2", "D", (60, 45), 270, vals["D2"], desc["D2"])         # K up (N3), A down (REF)
    d4 = sh.part("D4", "D", (50, 20), 180, vals["D4"], desc["D4"])         # A left (N2), K right (N4)
    d3 = sh.part("D3", "D", (40, 12), 0, vals["D3"], desc["D3"])           # K left (N1), A right (N3)
    mm = lambda u: (round((u[0] + OX) * U, 4), round((u[1] + OY) * U, 4))   # noqa: E731
    W = sh.wire_mm
    # N1
    W(c1["1"], mm((20, 30)), ca["1"]); W(mm((20, 30)), mm((20, 12)), d3["1"])
    # N2
    W(ca["2"], mm((40, 30)), d1["1"]); W(mm((40, 30)), mm((40, 20)), d4["2"])
    # N3
    W(cb["1"], mm((60, 30)), d2["1"]); W(mm((60, 30)), mm((60, 12)), d3["2"])
    # N4
    W(cb["2"], mm((80, 30)), c2["1"]); W(d4["1"], mm((80, 20)), mm((80, 30)))
    # REF
    W(c1["2"], mm((20, 60)), mm((40, 60)), mm((60, 60)), mm((80, 60)), c2["2"])
    W(d1["2"], mm((40, 60))); W(d2["2"], mm((60, 60)))
    for n, at in (("N1", (23, 30)), ("N2", (35, 30)), ("N3", (63, 30)), ("N4", (75, 30)), ("REF", (50, 60))):
        sh.label(n, at)
    return mm


def legend(sh, entries, at=(116, 6)):
    x, y = at
    sh.text("COMPONENTS", (x, y), size=2.0, bold=True)
    y += 2.5
    for ref, body in entries:
        sh.text(ref, (x, y), size=1.524, bold=True)
        n = sh.text(" ".join(body.split("\n")), (x + 4, y), size=1.27, width=80)
        y += 1.6 + 0.62 * (n - 1) + 0.6
    return y


def s0_sheet():
    import s0_base
    V = s0_base.VALUES
    cmin, cmax, ca = V["Cmin"] * 1e12, V["Cmax"] * 1e12, V["Ca"] * 1e12
    vals = dict(C1=f"{cmin:g}-{cmax:g} pF", C2=f"{cmin:g}-{cmax:g} pF", Ca=f"{ca:g} pF", Cb=f"{V['Cb']*1e12:g} pF",
                D1="ideal", D2="ideal", D3="ideal", D4="ideal")
    desc = dict(
        C1="Varicap A, N1 to REF. Its capacitance swings with the rotor between C_min and C_max; C_max at phase 1.\n"
           "In the tube: the top vane stack. Values: the paper's example [OC].",
        C2="Varicap B, N4 to REF. The same swing, 180 deg after C1 (C1 + C2 constant).\n"
           "In the tube: the bottom vane stack.",
        Ca="Transfer capacitor A, N1 to N2. Carries charge from varicap A's side to the cross diode D4.\n"
           "In the tube: a fixed plate stack on the rotor.",
        Cb="Transfer capacitor B, N3 to N4. The mirror of Ca, toward the cross diode D3.",
        D1="Return diode, REF -> N2. Holds N2 at or above REF; refills Ca from REF each cycle.",
        D2="Return diode, REF -> N3. The mirror of D1, for Cb.",
        D3="Cross diode, N3 -> N1. Passes Cb's charge onto varicap A; holds N1 at or above N3.",
        D4="Cross diode, N2 -> N4. Passes Ca's charge onto varicap B; holds N4 at or above N2.")
    sh = Sheet("s0_base", "S0 - the base schematic: de Queiroz Fig. 1",
               "symmetrical unipolar generator, positive polarity, varicaps 180 deg apart")
    core(sh, vals, desc)
    y = legend(sh, [(k, desc[k]) for k in ("C1", "C2", "Ca", "Cb", "D1", "D2", "D3", "D4")])
    r = json.load(open(os.path.join(ROOT, "rebuild", "s0_base", "s0_base_results.json")))
    z_ideal, z_ng = find_num(r, "z", "ideal"), find_num(r, "z", "ngspice")
    sh.text("NOTES", (116, y + 1), size=2.0, bold=True)
    sh.text("\n".join([
        "Source: J. de Queiroz (2019), Fig. 1, the symmetrical unipolar generator",
        "  (docs/reference/deQueiroz-2019-analysis-electronic-electrostatic-generators.pdf).",
        "Stage S0, frozen at commit 42747f4 (rebuild/s0_base/). REF = the paper's node 0, the varicaps' common side.",
        "Polarity positive: every node at or above REF (DECIDED 2026-10-14).",
        "The varicaps run 180 deg apart. In phase the doubler does not pump",
        "  (rebuild/s1_tube/s1-pulsed-core-findings.md).",
        f"Gain per cycle z = {z_ideal} ideal, {z_ng} ngspice (rebuild/s0_base/s0_base_results.json).",
        f"Values: the paper's example, {cmin:g}-{cmax:g} pF varicaps, Ca = Cb = {ca:g} pF, {V['F']:g} Hz. S1 gives the tube's.",
        "Netlist checked node for node against TOPOLOGY (rebuild/s0_base/s0_base.py) and s0_base.cir",
        "  by rebuild/kicad/make_kicad.py (rebuild/kicad/kicad_check_results.json).",
    ]), (116, y + 3.5))
    return sh


def find_num(obj, *keys):
    """the first number in a results file whose key path contains all the given words (z with ideal / ngspice)."""
    hits = []

    def walk(o, path):
        if isinstance(o, dict):
            for k, v in o.items():
                walk(v, path + [str(k).lower()])
        elif isinstance(o, (int, float)) and not isinstance(o, bool):
            p = "/".join(path)
            if all(k in p for k in keys):
                hits.append((len(p), p, o))
    walk(obj, [])
    if not hits:
        return "?"
    hits.sort()
    return f"{hits[0][2]:.6f}"


def s1_sheet():
    import s1_stress_options as so
    import s1_pulsed_core as pc
    pr = json.load(open(os.path.join(ROOT, "rebuild", "s1_tube", "s1_pulsed_core_results.json")))
    z_bare = pr["C_load"][0]["z_cycle"]
    z_rec = pr["C_load"][1]["z_cycle"]
    dif = pr["B_limited_B0"]["diff_max"]
    stick = "HV stick, 20 kV V_RRM"
    vals = dict(C1=f"{so.CMIN:g}-{so.CMAX:g} pF", C2=f"{so.CMIN:g}-{so.CMAX:g} pF", Ca=f"{so.CA:g} pF",
                Cb=f"{so.CA:g} pF", D1=stick, D2=stick, D3=stick, D4=stick,
                Ck=f"C_k (S2; record {pc.C_RR:g} pF)", Cr1=f"stray (record {pc.C_RREF:g} pF)",
                Cr4=f"stray (record {pc.C_RREF:g} pF)")
    st = "rebuild/s1_tube/s1-bare-findings.md"
    desc = dict(
        C1=f"Varicap A, N1 to REF: the top vane stack, 6 mm air gaps. {so.CMIN:g}-{so.CMAX:g} pF from the 3-D solve\n"
           "(sim/tube-strays-findings.md section 4; kappa 3.51) [IR: S2 re-solves it]. Carries the full node voltage:\n"
           "the gap breaks down at 19.70 kV (sim/air_stack_sizing_results.json).",
        C2="Varicap B, N4 to REF: the bottom vane stack, 180 deg after C1. The same values and limit.",
        Ca=f"Transfer capacitor A, N1 to N2: a plate stack on the rotor, {so.CA:g} pF = 1.1 C_max (the sixth gap,\n"
           f"DECIDED). Sees 0.528 of the varicap peak ({st}).",
        Cb="Transfer capacitor B, N3 to N4: the mirror of Ca. The same value and stress.",
        D1=f"Return diode REF -> N2: one HV stick, 20 kV V_RRM, avalanche at 24 kV, leakage 25 nA typ\n"
           f"(sim/diodes_real.py). Reverse voltage 0.472 of the varicap peak ({st}).",
        D2="Return diode REF -> N3: the mirror of D1. The same stick and stress.",
        D3=f"Cross diode N3 -> N1: the same stick. Reverse 0.956 of the varicap peak, the most stressed part.\n"
           f"With no limit added, its avalanche is the bare core's only ceiling: 29.7 kV on N1 ({st}).",
        D4="Cross diode N2 -> N4: the mirror of D3. The same stick and stress.",
        Ck="The core's electrode pair, N1 (top) to N4 (bottom). The field across the core reverses every half\n"
           f"cycle: V1 - V4 swings +/-{dif:.2f} of the varicap peak. A load on the pump, its energy reactive\n"
           "(it returns to the varicaps) [OC: ideal]. Value from the S2 field solve; the record's rings 1.1 pF\n"
           "(sim/hub-rings-build-findings.md). Not a bought part.",
        Cr1="Stray of the top core electrode (on N1) to REF. Record 5.1 pF; S2 re-solves it at the 2 mm wall.\n"
            "Not a bought part.",
        Cr4="Stray of the bottom core electrode (on N4) to REF. The mirror of Cr1.")
    sh = Sheet("s1_tube", "S1 - the core at the tube's values, with the pulsed core",
               "S0's core in air, 120 Hz; the core electrodes across N1-N4")
    mm = core(sh, vals, desc)
    # the additions: C_k across N1-N4 above everything, the strays beside the varicaps
    ck = sh.part("Ck", "C", (50, 4), 90, vals["Ck"], desc["Ck"], bom=False)
    cr1 = sh.part("Cr1", "C", (5, 52), 0, vals["Cr1"], desc["Cr1"], bom=False)
    cr4 = sh.part("Cr4", "C", (95, 52), 0, vals["Cr4"], desc["Cr4"], bom=False)
    W = sh.wire_mm
    W(mm((20, 12)), mm((20, 4)), ck["1"]); W(ck["2"], mm((80, 4)), mm((80, 20)))
    W(cr1["1"], mm((5, 40)), mm((20, 40))); W(cr1["2"], mm((5, 60)), mm((20, 60)))
    W(cr4["1"], mm((95, 40)), mm((80, 40))); W(cr4["2"], mm((95, 60)), mm((80, 60)))
    y = legend(sh, [(k, desc[k]) for k in ("C1", "C2", "Ca", "Cb", "D1", "D2", "D3", "D4", "Ck", "Cr1", "Cr4")])
    sh.text("NOTES", (116, y + 1), size=2.0, bold=True)
    sh.text("\n".join([
        "Stage S1: the frozen S0 core (42747f4) at the tube's values in air, 120 Hz (rebuild/s1_tube/).",
        f"Gain per cycle z = {z_bare:.5f} bare, {z_rec:.5f} with the record's C_k and strays",
        "  (rebuild/s1_tube/s1_pulsed_core_results.json). Real sticks: 1.1806 bare (rebuild/s1_tube/s1_bare_results.json).",
        "The core is pulsed (DECIDED 2026-10-15): S0's 180 deg makes V1 - V4 a pure alternating wave, no extra part.",
        "Ground: it floats in the core (its midplane is the neutral), or a virtual one from N1 and N4 if necessary",
        "  (DECIDED 2026-10-15). REF is the varicaps' stator side, not the ground.",
        "Ck, Cr1 and Cr4 are field quantities, not bought parts: drawn so the netlist carries them (not in the BOM).",
        "Not drawn, by decision or still open:",
        "  - the voltage limit: S1 shows one is needed under the gap's 19.70 kV; its kind is OPEN (s1-bare-findings.md);",
        "  - an HV seed source: only if the machine does not start (DECIDED 2026-10-15);",
        "  - the buffer / multiplier options: studied, not chosen (s1-multiplier-tap-findings.md, s1-stress-options-findings.md).",
        "Netlist checked node for node against S0's TOPOLOGY plus these additions, and against the solver circuit",
        "  of rebuild/s1_tube/s1_pulsed_core.py (rebuild/kicad/kicad_check_results.json).",
    ]), (116, y + 3.5))
    return sh


# ---------------------------------------------------------------- the check
def expected(stage):
    """the source topology as {ref: (kind, frozenset or (anode, cathode))} with nets REF, N1-N4."""
    import s0_base
    T = s0_base.TOPOLOGY
    net = lambda n: "REF" if n == "0" else "N" + n                       # noqa: E731
    e = {k: ("C", frozenset(map(net, v["nodes"]))) for k, v in T["capacitors"].items()}
    e.update({k: ("D", (net(a), net(c))) for k, (a, c) in T["diodes"].items()})
    if stage == "s1_tube":
        e.update(Ck=("C", frozenset(("N1", "N4"))), Cr1=("C", frozenset(("N1", "REF"))),
                 Cr4=("C", frozenset(("N4", "REF"))))
    return e


def from_deck(path):
    e = {}
    for ln in open(path):
        t = ln.split()
        if not t or t[0].startswith(("*", ".")):
            continue
        name = t[0][:-1] if t[0].endswith("v") else t[0]
        nn = ["REF" if x == "0" else "N" + x for x in t[1:3]]
        if name[0] == "C":
            e[name] = ("C", frozenset(nn))
        elif name[0] == "D":
            e[name] = ("D", tuple(nn))
    return e


def from_solver():
    """rebuild/s1_tube/s1_pulsed_core.py core(ck, c_rref): node numbers to nets, as a multiset of elements."""
    import s1_pulsed_core as pc
    c = pc.core(ck=1.0, c_rref=1.0)
    net = lambda n: "REF" if n == 0 else f"N{n}"                          # noqa: E731
    caps = sorted(tuple(sorted((net(a), net(b)))) for a, b, _ in c.caps)
    dio = sorted((net(a), net(k)) for a, k in c.diodes)
    return caps, dio


def sexpr(txt):
    """a minimal s-expression reader: lists of atoms and strings."""
    tok = re.findall(r'\(|\)|"(?:[^"\\]|\\.)*"|[^\s()"]+', txt)
    stack = [[]]
    for t in tok:
        if t == "(":
            stack.append([])
        elif t == ")":
            x = stack.pop()
            stack[-1].append(x)
        else:
            stack[-1].append(t[1:-1] if t.startswith('"') else t)
    return stack[0][0]


def field(node, key):
    for x in node:
        if isinstance(x, list) and x and x[0] == key:
            return x
    return None


def from_netlist(path):
    tree = sexpr(open(path, encoding="utf-8").read())
    pins = {}
    for n in field(tree, "nets")[1:]:
        name = field(n, "name")[1].lstrip("/")
        for nd in n:
            if isinstance(nd, list) and nd[0] == "node":
                pins[(field(nd, "ref")[1], field(nd, "pin")[1])] = name
    refs = sorted({r for r, _ in pins})
    e = {}
    for r in refs:
        if r.startswith("D"):
            e[r] = ("D", (pins[(r, "2")], pins[(r, "1")]))                # pin 2 = A, pin 1 = K
        else:
            e[r] = ("C", frozenset((pins[(r, "1")], pins[(r, "2")])))
    return e


def run(cmd):
    p = subprocess.run(cmd, capture_output=True, text=True)
    return p.returncode, (p.stdout + p.stderr).strip()


def check(stage):
    d = os.path.join(HERE, stage)
    sch, net = os.path.join(d, stage + ".kicad_sch"), os.path.join(d, stage + ".net")
    rc, msg = run([KICAD_CLI, "sch", "export", "netlist", "--format", "kicadsexpr", "-o", net, sch])
    got = from_netlist(net)
    want = expected(stage)
    res = dict(netlist=os.path.relpath(net, ROOT).replace("\\", "/"), export_rc=rc,
               vs_topology=dict(match=got == want,
                                diff=sorted(set(map(str, got.items())) ^ set(map(str, want.items())))))
    if stage == "s0_base":
        deck = from_deck(os.path.join(ROOT, "rebuild", "s0_base", "s0_base.cir"))
        res["vs_ngspice_deck"] = dict(match=deck == got, deck="rebuild/s0_base/s0_base.cir")
    else:
        caps, dio = from_solver()
        gc = sorted(tuple(sorted(v[1])) for v in got.values() if v[0] == "C")
        gd = sorted(v[1] for v in got.values() if v[0] == "D")
        res["vs_solver"] = dict(match=(gc, gd) == (caps, dio), solver="rebuild/s1_tube/s1_pulsed_core.py core()")
    erc = os.path.join(d, stage + "-erc.rpt")
    rc, _ = run([KICAD_CLI, "sch", "erc", "--severity-all", "-o", erc, sch])
    rpt = open(erc, encoding="utf-8").read() if os.path.exists(erc) else ""
    m = re.search(r"\*\* ERC messages: (\d+)\s+Errors (\d+)\s+Warnings (\d+)", rpt)
    res["erc"] = dict(rc=rc, report=os.path.relpath(erc, ROOT).replace("\\", "/"),
                      messages=int(m.group(1)) if m else None, errors=int(m.group(2)) if m else None,
                      warnings=int(m.group(3)) if m else None,
                      kinds=sorted(set(re.findall(r"^\[(\w+)\]", rpt, re.M))))
    return res


def main():
    force = "--force" in sys.argv
    out = dict(kicad_cli=KICAD_CLI, version=run([KICAD_CLI, "version"])[1], stages={})
    for stage, make in (("s0_base", s0_sheet), ("s1_tube", s1_sheet)):
        d = os.path.join(HERE, stage)
        os.makedirs(d, exist_ok=True)
        sch = os.path.join(d, stage + ".kicad_sch")
        if "--check-only" not in sys.argv and (force or not os.path.exists(sch)):
            open(sch, "w", encoding="utf-8", newline="\n").write(make().render(stage))
            pro = json.load(open(TEMPLATE_PRO, encoding="utf-8"))
            pro.setdefault("meta", {})["filename"] = stage + ".kicad_pro"
            json.dump(pro, open(os.path.join(d, stage + ".kicad_pro"), "w", encoding="utf-8", newline="\n"), indent=2)
            open(os.path.join(d, "sym-lib-table"), "w", encoding="utf-8", newline="\n").write(
                '(sym_lib_table\n\t(version 7)\n\t(lib (name "Device") (type "KiCad") '
                '(uri "${KICAD10_SYMBOL_DIR}/Device.kicad_sym") (options "") (descr "KiCad Device symbols"))\n)\n')
            print("wrote", os.path.relpath(sch, ROOT))
        r = check(stage)
        out["stages"][stage] = r
        print(stage, json.dumps({k: v for k, v in r.items() if k != "netlist"}))
    json.dump(out, open(os.path.join(HERE, "kicad_check_results.json"), "w", encoding="utf-8", newline="\n"), indent=1)


if __name__ == "__main__":
    main()
