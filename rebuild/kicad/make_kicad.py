"""rebuild/kicad/make_kicad.py -- the rebuild's schematics as one KiCad 10 project, and its netlist check.

The designer (2026-10-15/16): "We will first install kicad on my machine so we can deliver the proper netlist"; "When
you generate the schematic, provide the proper text in the schematic to explain all components"; "please set
everything up so the development stays in one project with all stages and changes in separate sheets".

The project rebuild/kicad/dccreg_rebuild/:
  dccreg_rebuild.kicad_sch    the root sheet: one box per stage, and an index of the stages, the naming and the check;
  s0_base.kicad_sch           S0: de Queiroz Fig. 1 at the paper's example values (frozen topology, 42747f4);
  s1_tube.kicad_sch           S1: the S0 core at the tube's air values, plus the pulsed core's load: C_k across
                              N1-N4 and each core electrode's stray to REF (rebuild/s1_tube/s1-pulsed-core-findings.md).
A new stage or change is a new entry in STAGES with its sheet function: its own sheet, its own hundred of part
numbers (S0 1xx, S1 2xx, ...). The labels are local to their sheet, so the stages never connect.
Every component carries its explanation on its sheet (a legend keyed by reference, with its name in the source in
brackets, and the symbol's Description field); every net is named (REF, N1-N4).

The layout is the generator's first placement; the designer rearranges it in the GUI and saves. A saved sheet is the
drawing of record: this script writes a sheet only if it is absent or with --force, and redraws the root only when a
stage is added. What makes the netlist of record is the check, which runs on whatever is saved:
  kicad-cli exports the project netlist; it is cut by sheet, and each stage's connectivity must equal its source node
  for node (S0: rebuild/s0_base/s0_base.py TOPOLOGY and its deck s0_base.cir; S1: S0's TOPOLOGY plus the additions,
  and the solver circuit of rebuild/s1_tube/s1_pulsed_core.py); kicad-cli's ERC on the project is recorded alongside.

Writes the project (the parts absent, or all with --force), its netlist dccreg_rebuild.net, each stage's nets
(netlists/<stage>.txt), the ERC report, and rebuild/kicad/kicad_check_results.json.
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
        "D_Zener": {"1": (-3.81, 0), "2": (3.81, 0)},
        "D": {"1": (-3.81, 0), "2": (3.81, 0)}}


def pin_xy(sym, at, rot, pin):
    """the schematic position of a pin: y flipped, then rotated counter-clockwise on screen by rot degrees."""
    px, py = PINS[sym][pin]
    x, y = px, -py
    c, s = {0: (1, 0), 90: (0, 1), 180: (-1, 0), 270: (0, -1)}[rot]
    return (round(at[0] + x * c + y * s, 4), round(at[1] - x * s + y * c, 4))


# ---------------------------------------------------------------- the sheets
KEEP = "\x01"                                  # text between two KEEP marks is not renamed (the legend's "(C1)")


class Sheet:
    def __init__(self, name, title, comment, date="2026-10-15"):
        self.name, self.title, self.comment, self.date = name, title, comment, date
        self.parts, self.wires, self.labels, self.texts = [], [], [], []
        self.ren = {}                          # the stage's reference map, e.g. C1 -> C101 (set by stage_map)

    def R(self, s):
        """the text with every reference of this sheet renamed to its stage number; KEEP-marked text untouched."""
        if not self.ren:
            return s.replace(KEEP, "")
        pat = re.compile(r"(?<![\w])(" + "|".join(sorted(map(re.escape, self.ren), key=len, reverse=True)) + r")(?![\w])")
        parts = s.split(KEEP)
        return "".join(p if i % 2 else pat.sub(lambda m: self.ren[m.group(1)], p) for i, p in enumerate(parts))

    def part(self, ref, sym, at, rot, value, desc, bom=True, left=False):
        at = ((at[0] + OX) * U, (at[1] + OY) * U)
        self.parts.append(dict(ref=ref, sym=sym, at=at, rot=rot, value=value, desc=desc, bom=bom, left=left))
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

    def render(self, project, inst_path):
        """the sub-sheet file; inst_path is the sheet's place in the project, "/<root uuid>/<sheet symbol uuid>"."""
        segs, junc = self._resolve()
        root = uid(self.name, "sheet")
        out = ["(kicad_sch", "\t(version 20260101)", '\t(generator "eeschema")', '\t(generator_version "10.0")',
               f"\t(uuid {q(root)})", '\t(paper "A3")', "\t(title_block", f"\t\t(title {q(self.title)})",
               f'\t\t(date "{self.date}")', '\t\t(rev "generated")', '\t\t(company "DCCREG turbine rebuild")',
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
            out += [f"\t(text {q(self.R(s))}", "\t\t(exclude_from_sim yes)", f"\t\t(at {at[0]:.2f} {at[1]:.2f} 0)",
                    "\t\t(effects", "\t\t\t(font", f"\t\t\t\t(size {size} {size})"] + \
                   (["\t\t\t\t(bold yes)"] if bold else []) + \
                   ["\t\t\t)", "\t\t\t(justify left top)", "\t\t)", f"\t\t(uuid {q(uid(self.name, 't', k))})", "\t)"]
        for p in self.parts:
            x, y = p["at"]
            vert = p["rot"] in (0, 180) and p["sym"].startswith("C") or p["rot"] in (90, 270) and p["sym"] in ("D", "D_Zener")
            rx, ry = (x + 3.81, y - 1.27) if vert else (x, y - 3.81)
            vx, vy = (x + 3.81, y + 1.27) if vert else (x, y + 3.81)
            just = "(justify left)" if vert else ""
            if vert and p.get("left"):                          # the fields on the symbol's left
                rx, vx, just = x - 3.81, x - 3.81, "(justify right)"

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
            ref = self.R(p["ref"])
            out += prop("Reference", ref, rx, ry, size=1.524)
            out += prop("Value", p["value"], vx, vy)
            out += prop("Footprint", "", x, y, hide=True)
            out += prop("Datasheet", "", x, y, hide=True)
            out += prop("Description", self.R(p["desc"]).replace("\n", " "), x, y, hide=True)
            for pn in PINS[p["sym"]]:
                out += [f"\t\t(pin {q(pn)}", f"\t\t\t(uuid {q(uid(self.name, 'pin', p['ref'], pn))})", "\t\t)"]
            out += ["\t\t(instances", f"\t\t\t(project {q(project)}", f"\t\t\t\t(path {q(inst_path)}",
                    f"\t\t\t\t\t(reference {q(ref)})", "\t\t\t\t\t(unit 1)", "\t\t\t\t)", "\t\t\t)", "\t\t)", "\t)"]
        out += [")"]
        return "\n".join(out) + "\n"


def stage_map(sh, base):
    """KiCad's multi-sheet numbering: each stage's parts in its own hundred (S0 1xx, S1 2xx); the letters stay.
    C1 -> C101, Ca -> Ca101, D4 -> D104, Cr4 -> Cr104 (+100 per stage)."""
    for p in sh.parts:
        m = re.fullmatch(r"([A-Za-z]+)(\d*)", p["ref"])
        sh.ren[p["ref"]] = f"{m.group(1)}{base + int(m.group(2) or 1)}"
    return sh


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
        body = f"{KEEP}[source: {ref}]{KEEP} " + " ".join(body.split("\n"))
        n = sh.text(body, (x + 5, y), size=1.27, width=80)
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


def s1_sheet(stage="s1_tube"):
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
    if stage == "s1b_clamp":
        sh = Sheet("s1b_clamp", "S1b - the S1 core with the zener clamp",
                   "one string per node, Z1 on N1 and Z4 on N4, at 13.13 kV (DECIDED 2026-10-16)", date="2026-10-16")
    else:
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
    if stage == "s1b_clamp":
        return s1b_additions(sh, mm, desc)
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


def s1b_additions(sh, mm, desc):
    """S1b: the S1 sheet plus the two clamp strings, Z1 (N1 -> REF) and Z4 (N4 -> REF)."""
    r = json.load(open(os.path.join(ROOT, "rebuild", "s1_tube", "s1b_clamp_results.json")))
    A = r["A_nominal"]["steady"]
    zc = r["inputs"]["clamp"]
    src = "rebuild/s1_tube/s1b_clamp_results.json"
    val = f"{zc['n']} x {zc['v_dev']:.0f} V"
    desc = dict(desc)
    desc["Z1"] = (f"Clamp string on N1, to REF: {zc['n']} avalanche parts of the {zc['v_dev']:.0f} V class in series "
                  f"(1.5KE200A class), BV {r['inputs']['clamp_BV_nominal_V'] / 1e3:.1f} kV at 1 mA. It holds N1 at "
                  f"{A['V1_kV']:.2f} kV, x{A['margin_to_breakdown']:.2f} under the gap's 19.70 kV, and takes "
                  f"{A['Z1']['P_W']:.2f} W ({A['Z1']['P_per_part_W'] * 1e3:.0f} mW per part, {A['Z1']['I_pk_mA']:.2f} mA peak) "
                  f"({src}). Disconnect it to run the bench without a limit (the designer, 2026-10-16).")
    desc["Z4"] = (f"Clamp string on N4, to REF: the mirror of Z1. Holds N4 at {A['V4_kV']:.2f} kV and takes "
                  f"{A['Z4']['P_W']:.2f} W.")
    z1 = sh.part("Z1", "D_Zener", (30, 52), 270, val, desc["Z1"])        # K up (N1), A down (REF)
    z4 = sh.part("Z4", "D_Zener", (70, 52), 270, val, desc["Z4"], left=True)        # K up (N4), A down (REF)
    W = sh.wire_mm
    W(mm((20, 48)), mm((30, 48)), z1["1"]); W(z1["2"], mm((30, 60)))
    W(mm((80, 48)), mm((70, 48)), z4["1"]); W(z4["2"], mm((70, 60)))
    y = legend(sh, [(k, desc[k]) for k in ("C1", "C2", "Ca", "Cb", "D1", "D2", "D3", "D4", "Ck", "Cr1", "Cr4",
                                           "Z1", "Z4")])
    C = r["C_self_start"]
    fmt = lambda t: (t["threshold_V"] if isinstance(t["threshold_V"], str) else          # noqa: E731
                     f"{t['threshold_V'][1]:.0f} V" if t["threshold_V"] else "no growth")
    B = {k: r[k]["steady"] for k in r if k.startswith("B_") and "steady" in r[k]}
    sh.text("NOTES", (116, y + 1), size=2.0, bold=True)
    sh.text("\n".join([
        "Stage S1b: the S1 sheet's circuit plus the zener clamp (rebuild/s1_tube/s1b_clamp.py). The designer, 2026-10-16:",
        "  \"For now we are going to deside the zener voltage clamp. Not using it on the physical bench is just matter",
        "  of disconnecting it.\" Level 13.13 kV (the gap's 19.70 kV / 1.5), one string per node.",
        f"Clamped steady state (ngspice, real sticks, typical leakage): N1 {A['V1_kV']:.2f} kV, N4 {A['V4_kV']:.2f} kV;",
        f"  both strings {A['P_total_W']:.2f} W together; the core's V1 - V4 {A['diff_kV'][0]:+.2f} to {A['diff_kV'][1]:+.2f} kV.",
        "The strings' spread (N1 peak, kV): " + "; ".join(f"{k[2:].replace('_', ' ')} {v['V1_kV']:.2f}" for k, v in B.items()) + ".",
        "Self-start seed with the strings' leakage: " + "; ".join(f"{k.replace('_', ' ')} {fmt(v)}" for k, v in C.items()) + ".",
        "The other limit options stay on file, to be revisited when called for: the buffer + converter, the 6BK4C,",
        "  the sphere gap, the inductive gap across N1-N4.",
        "Netlist checked node for node against TOPOLOGY in rebuild/s1_tube/s1b_clamp.py, from which the study's deck",
        "  is written (rebuild/kicad/kicad_check_results.json).",
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
    if stage == "s1b_clamp":                                  # its own TOPOLOGY, the study's single source
        import s1b_clamp
        T = s1b_clamp.TOPOLOGY
        e = {k: ("C", frozenset(map(net, v["nodes"]))) for k, v in T["capacitors"].items()}
        e.update({k: ("D", (net(a), net(c))) for k, (a, c) in {**T["diodes"], **T["clamps"]}.items()})
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


def run(cmd):
    p = subprocess.run(cmd, capture_output=True, text=True)
    return p.returncode, (p.stdout + p.stderr).strip()


# ---------------------------------------------------------------- the project: a root sheet indexing the stages
PROJECT = "dccreg_rebuild"
PROJ_DIR = os.path.join(HERE, PROJECT)
STAGES = [  # one sheet per stage or change; add a new entry (and its sheet function) for each new one
    dict(key="s0_base", name="S0 base", make=lambda: s0_sheet(), base=100,
         status="FROZEN at 42747f4. de Queiroz Fig. 1 at the paper's example values.",
         source="rebuild/s0_base/"),
    dict(key="s1_tube", name="S1 tube", make=lambda: s1_sheet(), base=200,
         status="The S0 core at the tube's air values; adds the pulsed core's load C_k (N1-N4) and the electrode "
                "strays.", source="rebuild/s1_tube/"),
    dict(key="s1b_clamp", name="S1b clamp", make=lambda: s1_sheet("s1b_clamp"), base=300,
         status="S1 plus the zener clamp: Z1 on N1, Z4 on N4, 66 x 200 V each, at 13.13 kV (DECIDED 2026-10-16).",
         source="rebuild/s1_tube/s1b_clamp.py"),
]
ROOT_UUID = uid(PROJECT, "root")


def sheet_uuid(st):
    return uid(PROJECT, "sheet-symbol", st["key"])


def root_sheet():
    out = ["(kicad_sch", "\t(version 20260101)", '\t(generator "eeschema")', '\t(generator_version "10.0")',
           f"\t(uuid {q(ROOT_UUID)})", '\t(paper "A3")', "\t(title_block",
           '\t\t(title "DCCREG rebuild - the stages")', '\t\t(date "2026-10-16")', '\t\t(rev "generated")',
           '\t\t(company "DCCREG turbine rebuild")',
           '\t\t(comment 1 "one sheet per stage or change; open a sheet from the hierarchy")',
           '\t\t(comment 2 "generated by rebuild/kicad/make_kicad.py")', "\t)", "\t(lib_symbols", "\t)"]
    x0, y0, w, h, gap = 30.48, 50.8, 76.2, 25.4, 15.24
    for i, st in enumerate(STAGES):
        y = y0 + i * (h + gap)
        out += ["\t(sheet", f"\t\t(at {x0} {y:.2f})", f"\t\t(size {w} {h})", "\t\t(exclude_from_sim no)",
                "\t\t(in_bom yes)", "\t\t(on_board yes)", "\t\t(dnp no)", "\t\t(stroke", "\t\t\t(width 0.3)",
                "\t\t\t(type solid)", "\t\t)", "\t\t(fill", "\t\t\t(color 0 0 0 0)", "\t\t)",
                f"\t\t(uuid {q(sheet_uuid(st))})",
                f"\t\t(property \"Sheetname\" {q(st['name'])}", f"\t\t\t(at {x0} {y - 0.76:.2f} 0)",
                "\t\t\t(show_name no)", "\t\t\t(do_not_autoplace no)", "\t\t\t(effects", "\t\t\t\t(font",
                "\t\t\t\t\t(size 2 2)", "\t\t\t\t\t(bold yes)", "\t\t\t\t)", "\t\t\t\t(justify left bottom)", "\t\t\t)",
                "\t\t)",
                f"\t\t(property \"Sheetfile\" {q(st['key'] + '.kicad_sch')}", f"\t\t\t(at {x0} {y + h + 0.6:.2f} 0)",
                "\t\t\t(show_name no)", "\t\t\t(do_not_autoplace no)", "\t\t\t(effects", "\t\t\t\t(font",
                "\t\t\t\t\t(size 1.27 1.27)", "\t\t\t\t)", "\t\t\t\t(justify left top)", "\t\t\t)", "\t\t)",
                "\t\t(instances", f"\t\t\t(project {q(PROJECT)}", f"\t\t\t\t(path {q('/' + ROOT_UUID)}",
                f"\t\t\t\t\t(page {q(str(i + 2))})", "\t\t\t\t)", "\t\t\t)", "\t\t)", "\t)"]
    lines = ["THE STAGES", "",
             "Each stage, and each later change, is its own sheet in this one project. Open a sheet by",
             "double-clicking its box, or from the hierarchy panel.", ""]
    for i, st in enumerate(STAGES):
        lines += [f"{st['name']} (sheet {i + 2}, parts {st['base'] + 1}-{st['base'] + 99}): {st['status']}",
                  f"   source: {st['source']}", ""]
    lines += ["PART NAMES: each stage numbers its parts in its own hundred, as KiCad does for multi-sheet",
              "projects. S0 = 1xx, S1 = 2xx; the letters stay (C1 -> C101 in S0, C201 in S1; Ca -> Ca101;",
              "D4 -> D104). Each sheet's legend gives every part's name in its source in brackets.",
              "",
              "NETS: the labels are local to their sheet (REF, N1-N4), so the stages never connect. In the",
              "project netlist they read /S0 base/N1, /S1 tube/N1 ...",
              "",
              "CHECK: python3 rebuild/kicad/make_kicad.py --check-only exports the project netlist and",
              "compares each sheet node for node with its source (rebuild/kicad/kicad_check_results.json)."]
    out += [f"\t(text {q(chr(10).join(lines))}", "\t\t(exclude_from_sim yes)", "\t\t(at 127 50.8 0)", "\t\t(effects",
            "\t\t\t(font", "\t\t\t\t(size 1.524 1.524)", "\t\t\t)", "\t\t\t(justify left top)", "\t\t)",
            f"\t\t(uuid {q(uid(PROJECT, 'root-text'))})", "\t)"]
    out += ["\t(sheet_instances", '\t\t(path "/"', '\t\t\t(page "1")', "\t\t)", "\t)", "\t(embedded_fonts no)", ")"]
    return "\n".join(out) + "\n"


# ---------------------------------------------------------------- the check, on the whole project
def check(maps):
    """export the project netlist; split it by sheet; compare each stage with its source under the stage's names."""
    root = os.path.join(PROJ_DIR, PROJECT + ".kicad_sch")
    net = os.path.join(PROJ_DIR, PROJECT + ".net")
    rc, msg = run([KICAD_CLI, "sch", "export", "netlist", "--format", "kicadsexpr", "-o", net, root])
    tree = sexpr(open(net, encoding="utf-8").read())
    inv = {new: (st, old) for st, m in maps.items() for old, new in m.items()}
    pins = {}                                                    # (stage, original ref, pin) -> local net name
    for n in field(tree, "nets")[1:]:
        name = field(n, "name")[1]
        local = name.rsplit("/", 1)[-1]
        for nd in n:
            if isinstance(nd, list) and nd[0] == "node":
                ref, pin = field(nd, "ref")[1], field(nd, "pin")[1]
                st, old = inv.get(ref, (None, ref))
                pins[(st, old, pin)] = (local, name)
    res = dict(netlist=os.path.relpath(net, ROOT).replace("\\", "/"), export_rc=rc, stages={})
    os.makedirs(os.path.join(PROJ_DIR, "netlists"), exist_ok=True)
    unknown = sorted({k[1] for k in pins if k[0] is None})
    for st in STAGES:
        key = st["key"]
        mine = {(old, pin): v for (s, old, pin), v in pins.items() if s == key}
        got = {}
        for old in sorted({o for o, _ in mine}):
            if old[0] in "DZ":                                            # diodes and clamp strings
                got[old] = ("D", (mine[(old, "2")][0], mine[(old, "1")][0]))        # pin 2 = A, pin 1 = K
            else:
                got[old] = ("C", frozenset((mine[(old, "1")][0], mine[(old, "2")][0])))
        sheets = sorted({v[1].rsplit("/", 1)[0] for v in mine.values()})
        want = expected(key)
        r = dict(sheet_paths=sheets, names=maps[key],
                 vs_topology=dict(match=got == want,
                                  diff=sorted(set(map(str, got.items())) ^ set(map(str, want.items())))))
        if key == "s0_base":
            deck = from_deck(os.path.join(ROOT, "rebuild", "s0_base", "s0_base.cir"))
            r["vs_ngspice_deck"] = dict(match=deck == got, deck="rebuild/s0_base/s0_base.cir")
        elif key == "s1_tube":
            caps, dio = from_solver()
            gc = sorted(tuple(sorted(v[1])) for v in got.values() if v[0] == "C")
            gd = sorted(v[1] for v in got.values() if v[0] == "D")
            r["vs_solver"] = dict(match=(gc, gd) == (caps, dio), solver="rebuild/s1_tube/s1_pulsed_core.py core()")
        # the stage's own netlist, as a readable listing (net: part.pin ...), cut from the project netlist
        by_net = {}
        for (old, pin), (local, _) in sorted(mine.items()):
            by_net.setdefault(local, []).append(f"{maps[key][old]}.{pin}")
        path = os.path.join(PROJ_DIR, "netlists", key + ".txt")
        with open(path, "w", encoding="utf-8", newline="\n") as fh:
            fh.write(f"# {st['name']}: the stage's nets, cut from {PROJECT}.net by rebuild/kicad/make_kicad.py\n")
            fh.write("# part.pin; C pins 1 / 2; D pin 1 = K (cathode), pin 2 = A (anode)\n")
            for nn in sorted(by_net):
                fh.write(f"{nn}: {' '.join(by_net[nn])}\n")
        r["stage_netlist"] = os.path.relpath(path, ROOT).replace("\\", "/")
        res["stages"][key] = r
    res["parts_outside_any_stage"] = unknown
    erc = os.path.join(PROJ_DIR, PROJECT + "-erc.rpt")
    rc, _ = run([KICAD_CLI, "sch", "erc", "--severity-all", "-o", erc, root])
    rpt = open(erc, encoding="utf-8").read() if os.path.exists(erc) else ""
    m = re.search(r"\*\* ERC messages: (\d+)\s+Errors (\d+)\s+Warnings (\d+)", rpt)
    res["erc"] = dict(rc=rc, report=os.path.relpath(erc, ROOT).replace("\\", "/"),
                      messages=int(m.group(1)) if m else None, errors=int(m.group(2)) if m else None,
                      warnings=int(m.group(3)) if m else None,
                      kinds=sorted(set(re.findall(r"^\[(\w+)\]", rpt, re.M))))
    return res


def main():
    force = "--force" in sys.argv
    write = "--check-only" not in sys.argv
    os.makedirs(PROJ_DIR, exist_ok=True)
    maps = {}
    for st in STAGES:
        sh = stage_map(st["make"](), st["base"])
        maps[st["key"]] = dict(sh.ren)
        sch = os.path.join(PROJ_DIR, st["key"] + ".kicad_sch")
        if write and (force or not os.path.exists(sch)):
            open(sch, "w", encoding="utf-8", newline="\n").write(
                sh.render(PROJECT, f"/{ROOT_UUID}/{sheet_uuid(st)}"))
            print("wrote", os.path.relpath(sch, ROOT))
    root = os.path.join(PROJ_DIR, PROJECT + ".kicad_sch")
    have = open(root, encoding="utf-8").read() if os.path.exists(root) else ""
    if write and (force or not all(f'"{st["key"]}.kicad_sch"' in have for st in STAGES)):
        open(root, "w", encoding="utf-8", newline="\n").write(root_sheet())     # new stage: the index is redrawn
        print("wrote", os.path.relpath(root, ROOT))
    pro = os.path.join(PROJ_DIR, PROJECT + ".kicad_pro")
    if write and (force or not os.path.exists(pro)):
        p = json.load(open(TEMPLATE_PRO, encoding="utf-8"))
        p.setdefault("meta", {})["filename"] = PROJECT + ".kicad_pro"
        json.dump(p, open(pro, "w", encoding="utf-8", newline="\n"), indent=2)
        open(os.path.join(PROJ_DIR, "sym-lib-table"), "w", encoding="utf-8", newline="\n").write(
            '(sym_lib_table\n\t(version 7)\n\t(lib (name "Device") (type "KiCad") '
            '(uri "${KICAD10_SYMBOL_DIR}/Device.kicad_sym") (options "") (descr "KiCad Device symbols"))\n)\n')
    r = check(maps)
    out = dict(kicad_cli=KICAD_CLI, version=run([KICAD_CLI, "version"])[1], project=os.path.relpath(
        pro, ROOT).replace("\\", "/"), **r)
    for k, v in r["stages"].items():
        print(k, {kk: vv.get("match") for kk, vv in v.items() if isinstance(vv, dict) and "match" in vv})
    print("erc", r["erc"]["errors"], "errors", r["erc"]["warnings"], "warnings", r["erc"]["kinds"],
          "| parts outside any stage:", r["parts_outside_any_stage"])
    json.dump(out, open(os.path.join(HERE, "kicad_check_results.json"), "w", encoding="utf-8", newline="\n"), indent=1)


if __name__ == "__main__":
    main()
