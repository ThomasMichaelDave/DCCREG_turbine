"""docs/make_cost_sheet.py -- writes docs/cost/dccreg-air-build-cost-sheet.xlsx, the cost sheet template of the air
build. Every design of the vane matrix (sim/vane_matrix_results.json: 2700 stacks) carries its physics as values and its
cost as live formulas on the Inputs sheet's targets and prices. The Optimum sheet picks the design that meets the
targets at the lowest total cost (or cost per watt) and lists the next ten:
  - the voltage the electric field on the core needs (E target x electrode spacing) against the core's voltage: the
    operating peak with a steady field (a diode charges cone A), or the swing's peak with the swinging field on floating
    cones (sim/core_swing_grid.json, which also gives each design's gain and power with the cones on its nodes);
  - the electrostatic pump's clamped power, its gain z, the vane-count cap, the radius cap, corona-safe rims;
  - the AH's steady ampere-turns (the 22 mF bypass delivers 300 at the pick: sim/ah_steady_cusp_results.json).
The BOM sheet holds the parts that do not depend on the stack (magnetic pump, AH and its bypass, hub, mechanics).
Prices are placeholders [RH] to be replaced by quotes; geometry-derived quantities are documented on the Notes sheet.
Usage: python3 docs/make_cost_sheet.py   (then recalculate: the xlsx skill's scripts/recalc.py)
"""
import json
import math
import os

from openpyxl import Workbook
from openpyxl.comments import Comment
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter
from openpyxl.workbook.defined_name import DefinedName
from openpyxl.worksheet.datavalidation import DataValidation

HERE = os.path.dirname(os.path.abspath(__file__))
SIM = os.path.join(HERE, "..", "sim")
OUT = os.path.join(HERE, "cost", "dccreg-air-build-cost-sheet.xlsx")

ARIAL = "Arial"
F_IN = Font(name=ARIAL, size=10, color="0000FF")                 # hardcoded inputs
F_CALC = Font(name=ARIAL, size=10, color="000000")               # formulas
F_LINK = Font(name=ARIAL, size=10, color="008000")               # links to another sheet
F_TXT = Font(name=ARIAL, size=10, color="000000")
F_NOTE = Font(name=ARIAL, size=9, color="595959", italic=True)
F_HEAD = Font(name=ARIAL, size=10, bold=True, color="000000")
F_TITLE = Font(name=ARIAL, size=13, bold=True, color="000000")
F_SEC = Font(name=ARIAL, size=11, bold=True, color="1F3864")
FILL_KEY = PatternFill("solid", fgColor="FFFF00")               # key assumptions / cells to fill in
FILL_HEAD = PatternFill("solid", fgColor="D9E1F2")
FILL_BEST = PatternFill("solid", fgColor="E2EFDA")
THIN = Side(style="thin", color="BFBFBF")
BOX = Border(left=THIN, right=THIN, top=THIN, bottom=THIN)
MONEY = '#,##0;(#,##0);"-"'
MONEY2 = '#,##0.00;(#,##0.00);"-"'
NUM1, NUM2, NUM3 = "0.0", "0.00", "0.000"
PCT = "0.0%"

# Al density the sweep's masses use (stack_sizing.TUBE_DEFAULTS rho_vane), G10's, the sleeve / shaft radii (mm)
RHO_AL, RHO_G10, R_SLEEVE, R_SHAFT, R_IN, RING, CAGE_W = 2700.0, 1850.0, 20.5, 12.5, 50.0, 12.0, 4.0


def name(wb, nm, ref):
    wb.defined_names[nm] = DefinedName(nm, attr_text=ref)


def put(ws, cell, value, font=F_CALC, fmt=None, fill=None, comment=None, bold=False, align=None):
    c = ws[cell]
    c.value = value
    c.font = Font(name=font.name, size=font.size, color=font.color, bold=bold or font.bold, italic=font.italic)
    if fmt:
        c.number_format = fmt
    if fill:
        c.fill = fill
    if comment:
        c.comment = Comment(comment, "cost sheet")
    if align:
        c.alignment = align
    return c


def geometry(q):
    """cut length and rounded-edge length (m) of all vanes and Ca / Cb plates, both sides, and the G10 cage and sleeve
    masses (kg), from the stack's geometry (6 sectors, stator = rotor width; see the Notes sheet)."""
    ro, w = q["r_outMm"], math.radians(q["ws_deg"])
    n, nca, ns = q["n_plates"], q["n_gap_ca"] + 1, 6
    gap_arc = math.pi / 3 - w                                     # the 60 deg pitch less one sector, rad
    stator_inner = ns * (2 * (ro - R_IN) + R_IN * w + ro * gap_arc)   # the exposed contour: sides, inner arcs, ring edge
    rotor_outer = ns * (2 * (ro - R_IN) + ro * w + R_IN * gap_arc)    # sides, outer arcs, ring edge
    stator_cut = stator_inner + 2 * math.pi * (ro + RING)             # + the outer circle (held in the cage)
    rotor_cut = rotor_outer + 2 * math.pi * R_SLEEVE                  # + the bore on the sleeve
    plate = 2 * math.pi * (ro + R_IN)                                 # Ca / Cb: both circles cut and rounded
    sides = 2
    cut = sides * (n * (stator_cut + rotor_cut) + nca * plate) / 1e3
    rnd = sides * (n * (stator_inner + rotor_outer) + nca * plate) / 1e3
    L_cage = (q["L_es_side_mm"] + 50.0) * 1e-3                        # + the two bearing spiders' seats, per side
    cage = sides * math.pi * (((ro + RING + CAGE_W) * 1e-3) ** 2 - ((ro + RING) * 1e-3) ** 2) * L_cage * RHO_G10
    sleeve = sides * math.pi * ((R_SLEEVE * 1e-3) ** 2 - (R_SHAFT * 1e-3) ** 2) * L_cage * RHO_G10
    return dict(n_vanes=4 * n, n_plates=sides * nca, cut_m=cut, round_m=rnd, cage_kg=cage, sleeve_kg=sleeve)


def swing_model():
    """the swinging core's corrections from sim/core_swing_grid.json (sim/core_field.py --grid), bilinear in log C_max and
    log kappa, clamped to the grid: the swing's peak / V_op, z with the cones / bare, power with the cones / bare."""
    gr = json.load(open(os.path.join(SIM, "core_swing_grid.json")))
    X, Y = [math.log(v) for v in gr["grid_C_max_pF"]], [math.log(v) for v in gr["grid_kappa"]]
    cell = {(q["C_max_pF"], q["kappa"]): q for q in gr["rows"]}

    def ratios(q):
        if not q.get("ok"):
            return 0.0, 1.0, 0.0
        p = q["P_float_W"] / q["P_none_W"] if q["P_none_W"] > 1e-6 else 0.0
        return q["swing_pk_kV"] / gr["V_op_kV"], q["z_float"] / q["z_none"], max(0.0, p)
    T = [[ratios(cell[(cm, k)]) for k in gr["grid_kappa"]] for cm in gr["grid_C_max_pF"]]

    def at(c_max, kappa):
        x, y = min(max(math.log(c_max), X[0]), X[-1]), min(max(math.log(kappa), Y[0]), Y[-1])
        i = min(max(0, sum(1 for v in X if v <= x) - 1), len(X) - 2)
        j = min(max(0, sum(1 for v in Y if v <= y) - 1), len(Y) - 2)
        u, w = (x - X[i]) / (X[i + 1] - X[i]), (y - Y[j]) / (Y[j + 1] - Y[j])
        return tuple((1 - u) * (1 - w) * T[i][j][n] + u * (1 - w) * T[i + 1][j][n] + (1 - u) * w * T[i][j + 1][n]
                     + u * w * T[i + 1][j + 1][n] for n in range(3))
    return at, gr


def build():
    m = json.load(open(os.path.join(SIM, "vane_matrix_results.json")))
    swing_at, grid = swing_model()
    cusp = json.load(open(os.path.join(SIM, "ah_steady_cusp_results.json")))
    at22 = [r for r in cusp["rows"] if r["C_byp_mF"] == 22.0][0]["top"]["AT_mean"]
    rows = sorted(m["rows"], key=lambda q: (q["r_outMm"], q["gap_mm"], q["t_vaneMm"], q["ws_deg"], q["n_plates"]))
    wb = Workbook()

    # ------------------------------------------------------------------------------------------------- Read me
    rd = wb.active
    rd.title = "Read me"
    rd.column_dimensions["A"].width = 3
    rd.column_dimensions["B"].width = 120
    lines = [
        ("DCCREG turbine, air build: cost sheet template", F_TITLE),
        ("", F_TXT),
        ("What it does", F_SEC),
        ("Every stack of the vane matrix (2700 designs: gap, vane thickness, outer radius, vane count, sector width) is "
         "costed with live formulas on the Inputs sheet.", F_TXT),
        ("The Optimum sheet picks the design that meets your targets at the lowest total cost (or cost per watt), and lists "
         "the next ten.", F_TXT),
        ("Targets: the voltage the electric field on the core needs, the electrostatic pump's power and gain, the vane and "
         "radius caps, corona-safe rims, and the AH's steady ampere-turns.", F_TXT),
        ("Core field: swinging (the cones float on coupling capacitors; the default) or steady (a diode charges cone A). "
         "The swinging field reaches about 0.55 of the operating peak and costs small stacks gain; see the Notes sheet.",
         F_TXT),
        ("", F_TXT),
        ("How to use it", F_SEC),
        ("1. On Inputs, edit the yellow cells with blue text: the targets first, then the materials and the process prices.",
         F_TXT),
        ("2. On BOM fixed, edit the quantities and unit prices of the parts that do not depend on the stack (blue text).",
         F_TXT),
        ("3. Read the result on Optimum. Nothing else needs editing: black cells are formulas, green cells link to another "
         "sheet.", F_TXT),
        ("The Designs sheet's physics columns (grey header note) are results of sim/vane_matrix.py; do not edit them.",
         F_TXT),
        ("", F_TXT),
        ("Legend", F_SEC),
        ("Blue text on yellow: an input to fill in (key assumption). Blue text: an input. Black: a formula. Green: a link "
         "to another sheet.", F_TXT),
        ("Every price is a placeholder [RH] for a one-off prototype in EUR. Replace each with a quote; the source column "
         "says what each number stands for.", F_TXT),
        ("", F_TXT),
        ("Sources", F_SEC),
        ("Physics per design: sim/vane_matrix_results.json (sim/vane_matrix.py; findings sim/vane-matrix-findings.md). "
         "Clamped power: the eigen-cycle power calibrated by 12 ngspice runs (-4 to +11 %).", F_TXT),
        (f"AH steady ampere-turns delivered: {at22:.0f} with 22 mF across each AH coil at the pick "
         "(sim/ah_steady_cusp_results.json, sim/ah-steady-cusp-findings.md).", F_TXT),
        ("Magnetic pump quantities: the pick's utron masses (sim/pole_design_variants_op.json / pole_design_variants.json), "
         "La / Lb first-cut chokes (sim/rotor_parts_duty_results.json).", F_TXT),
        ("Geometry-derived quantities (cut and rounded-edge lengths, G10 masses): see the Notes sheet.", F_TXT),
    ]
    for i, (txt, f) in enumerate(lines, start=2):
        put(rd, f"B{i}", txt, f)
        rd[f"B{i}"].alignment = Alignment(wrap_text=True, vertical="top")

    # ------------------------------------------------------------------------------------------------- Inputs
    ws = wb.create_sheet("Inputs")
    for col, wd in zip("ABCDE", (3, 52, 14, 12, 90)):
        ws.column_dimensions[col].width = wd
    put(ws, "B2", "Inputs: targets, materials and prices", F_TITLE)
    put(ws, "B3", "Edit the yellow cells (blue text). Black cells are formulas.", F_NOTE)
    for c, h in zip("BCDE", ("item", "value", "unit", "source / note")):
        put(ws, f"{c}5", h, F_HEAD, fill=FILL_HEAD)
    r = 6
    put(ws, f"B{r}", "Currency label", F_TXT); put(ws, f"C{r}", "EUR", F_IN, fill=FILL_KEY)
    put(ws, f"E{r}", "Used in the headers. Every price below is a placeholder in this currency.", F_NOTE)
    name(wb, "CUR", f"Inputs!$C${r}")

    def row(label, val, unit, note, nm, key=False, fmt=None, formula=False):
        nonlocal r
        r += 1
        put(ws, f"B{r}", label, F_TXT)
        put(ws, f"C{r}", val, F_CALC if formula else F_IN, fmt=fmt, fill=FILL_KEY if key else None)
        put(ws, f"D{r}", unit, F_TXT)
        put(ws, f"E{r}", note, F_NOTE)
        name(wb, nm, f"Inputs!$C${r}")
        return r

    r += 1; put(ws, f"B{r}", "Targets", F_SEC)
    row("Electric field wanted on the core", 2.0, "kV/cm", "Placeholder: set your target. With the spacing below it sets "
        "the voltage the electrostatic pump must hold on the core.", "E_CORE", key=True, fmt=NUM2)
    row("Core electrode spacing", 50.0, "mm", "Placeholder: the distance across which that field is applied (e.g. between "
        "the two cones at the centre).", "D_CORE", key=True, fmt=NUM1)
    row("Core field (1 steady, 2 swinging)", 2, "", "1: a diode charges cone A to the operating peak, cone B on the shaft "
        "(DC). 2: the cones float on coupling capacitors from nodes 1 / 4 and swing at the pump frequency; the cones' "
        "strays then cost gain (sim/core-field-findings.md).", "CORE_MODE", key=True)
    row("Voltage needed on the core", "=E_CORE*D_CORE/10", "kV", "Formula: E x spacing. A design qualifies when the "
        "core's voltage reaches it: the operating peak (steady) or the swing's peak (swinging).", "V_NEED", fmt=NUM2,
        formula=True)
    row("Minimum electrostatic pump power (clamped)", 2.0, "W", "Placeholder: what the core's leakage, corona and margin "
        "need. The pump only has to replace the charge that leaks away.", "P_MIN", key=True, fmt=NUM2)
    row("Minimum gain per cycle z", 1.3, "", "The searches' floor; real losses eat into a thin margin.", "Z_MIN", key=True,
        fmt=NUM2)
    row("Maximum vanes per varicap per side", 6, "", "The cap (6 stator + 6 rotor). Set 16 to lift it.", "N_CAP", key=True)
    row("Maximum vane outer radius", 300, "mm", "150 today; the matrix runs to 300.", "R_MAX", key=True)
    row("Require corona-safe rims (1 yes, 0 no)", 1, "", "Rims must hold the operating peak on a handled surface "
        "(Peek, m 0.85).", "CORONA_REQ", key=True)
    row("AH steady ampere-turns wanted at the centre", 300, "A-turns", "The stable cusp's strength per coil. Checked on "
        "the Optimum sheet; it does not depend on the stack.", "AT_TARGET", key=True)
    row("AH steady ampere-turns delivered", round(at22), "A-turns", "22 mF across each AH coil at the pick "
        "(sim/ah_steady_cusp_results.json). Above this, the AH or the pump must be re-sized (not costed here).",
        "AT_DELIVERED", fmt=NUM1)
    row("Objective (1 lowest total cost, 2 lowest cost per watt)", 1, "", "How the Optimum sheet ranks the designs that "
        "meet the targets.", "OBJECTIVE", key=True)

    r += 2; put(ws, f"B{r}", "Materials", F_SEC)
    r += 1
    for c, h in zip("BCDE", ("material", "density", "price", "source / note")):
        put(ws, f"{c}{r}", h, F_HEAD, fill=FILL_HEAD)
    put(ws, f"D{r}", '="price ("&CUR&"/kg)"', F_HEAD, fill=FILL_HEAD)
    mats = [("Al 5083 plate", 2660, 9.0, "Marine-grade plate; machines and polishes well. Placeholder price."),
            ("Al 6082-T6 plate", 2700, 10.0, "Structural plate; the default the sweep's masses assume (2700). Placeholder."),
            ("Al 1050 sheet", 2705, 8.0, "Soft, cheap; harder to give a polished full round. Placeholder."),
            ("Stainless 304 plate", 7930, 7.0, "Holds a polish; 3x the mass. Placeholder."),
            ("Copper C101 plate", 8940, 14.0, "Best finish and conductivity; 3.3x the mass. Placeholder.")]
    m0 = r + 1
    for nm_, rho, pr, note in mats:
        r += 1
        put(ws, f"B{r}", nm_, F_IN); put(ws, f"C{r}", rho, F_IN, fmt="#,##0"); put(ws, f"D{r}", pr, F_IN, fmt=NUM2)
        put(ws, f"E{r}", note, F_NOTE)
    m1 = r
    name(wb, "MAT_NAMES", f"Inputs!$B${m0}:$B${m1}")
    name(wb, "MAT_RHO", f"Inputs!$C${m0}:$C${m1}")
    name(wb, "MAT_PRICE", f"Inputs!$D${m0}:$D${m1}")
    put(ws, f"C{m0 - 1}", "density (kg/m³)", F_HEAD, fill=FILL_HEAD)
    r += 1
    dv = DataValidation(type="list", formula1="MAT_NAMES", allow_blank=False)
    ws.add_data_validation(dv)
    row("Vane material (rotor and stator vanes)", mats[0][0], "", "Pick from the list above.", "VANE_MAT", key=True)
    dv.add(f"C{r}")
    row("Ca / Cb plate material", mats[0][0], "", "Pick from the list above. They need not match the vanes.", "PLATE_MAT",
        key=True)
    dv.add(f"C{r}")
    row("Vane density", "=INDEX(MAT_RHO,MATCH(VANE_MAT,MAT_NAMES,0))", "kg/m³", "Formula.", "RHO_VANE", fmt="#,##0",
        formula=True)
    row("Vane price", "=INDEX(MAT_PRICE,MATCH(VANE_MAT,MAT_NAMES,0))", "/kg", "Formula.", "PRICE_VANE", fmt=NUM2,
        formula=True)
    row("Plate density", "=INDEX(MAT_RHO,MATCH(PLATE_MAT,MAT_NAMES,0))", "kg/m³", "Formula.", "RHO_PLATE", fmt="#,##0",
        formula=True)
    row("Plate price", "=INDEX(MAT_PRICE,MATCH(PLATE_MAT,MAT_NAMES,0))", "/kg", "Formula.", "PRICE_PLATE", fmt=NUM2,
        formula=True)
    row("Plate yield loss (extra stock for nesting sectors)", 0.35, "fraction", "Placeholder: sectored discs waste a lot "
        "of a rectangular plate.", "SCRAP", key=True, fmt=PCT)

    r += 2; put(ws, f"B{r}", "Process prices (placeholders [RH]: replace with quotes)", F_SEC)
    row("Waterjet / laser cutting", 1.5, "/m of cut", "Placeholder, 1.5-4 mm Al.", "CUT_M", key=True, fmt=NUM2)
    row("Cutting set-up per part", 1.0, "/part", "Placeholder: pierce, handling.", "CUT_SET", fmt=NUM2)
    row("CNC full-round edge", 5.0, "/m of edge", "Placeholder: radius t/2 on every exposed edge (corner-round cutter).",
        "ROUND_M", key=True, fmt=NUM2)
    row("Deburr and polish", 8.0, "/part", "Placeholder: the rounds must be smooth for the corona margin.", "FINISH_PART",
        fmt=NUM2)
    row("Insulating spacers and studs", 3.0, "/vane", "Placeholder: PEEK / POM spacers, studs, per vane.", "SPACER_VANE",
        fmt=NUM2)
    row("Labour rate", 45.0, "/h", "Placeholder.", "LABOUR", key=True, fmt=NUM2)
    row("Stack assembly", 0.25, "h per vane or plate", "Placeholder: stacking, spacing, alignment.", "ASM_H", fmt=NUM2)
    row("G10 tube (stator cage)", 60.0, "/kg", "Placeholder: filament-wound tube.", "G10_CAGE", fmt=NUM2)
    row("G10 rotor sleeve", 60.0, "/kg", "Placeholder.", "G10_SLEEVE", fmt=NUM2)
    row("Steel shaft, machined", 120.0, "/m", "Placeholder: d 25, ground at the bearing seats.", "SHAFT_M", fmt=NUM2)
    row("Shaft set-up", 80.0, "/shaft", "Placeholder.", "SHAFT_SET", fmt=NUM2)
    row("Clamp Zener voltage", 200.0, "V", "The clamp strings Z1 / Z4 at the operating peak (sim/rotor_parts_duty.py).",
        "V_ZENER", fmt="#,##0")
    row("Clamp Zener price", 0.6, "/each", "Placeholder.", "PRICE_Z", fmt=NUM2)
    row("HV diode stick rating", 20.0, "kV", "e.g. a 2CL77-class stick.", "V_STICK", fmt=NUM1)
    row("HV diode stick price", 2.5, "/each", "Placeholder.", "PRICE_STICK", fmt=NUM2)
    row("HV diode derating (stack rating / operating peak)", 1.5, "", "D1-D4 and the core diode Dk, each a series stack.",
        "DIODE_SAFETY",
        fmt=NUM2)
    row("Contingency", 0.15, "fraction", "On the whole build.", "CONT", key=True, fmt=PCT)

    r += 2; put(ws, f"B{r}", "Fixed parts", F_SEC)
    row("Fixed BOM total (from BOM fixed)", "='BOM fixed'!$F$4", "", "Link: the parts that do not depend on the stack.",
        "FIXED_BOM", fmt=MONEY)
    ws[f"C{r}"].font = Font(name=ARIAL, size=10, color="008000")

    # ------------------------------------------------------------------------------------------------- BOM fixed
    bm = wb.create_sheet("BOM fixed")
    for col, wd in zip("ABCDEFG", (3, 30, 48, 9, 12, 13, 78)):
        bm.column_dimensions[col].width = wd
    put(bm, "B2", "Fixed parts: everything that does not depend on the stack", F_TITLE)
    put(bm, "B4", "Total", F_HEAD)
    hdr = ("group", "item", "qty", "unit price", "extended", "source / note")
    for c, h in zip("BCDEFG", hdr):
        put(bm, f"{c}6", h, F_HEAD, fill=FILL_HEAD)
    put(bm, "E6", '="unit price ("&CUR&")"', F_HEAD, fill=FILL_HEAD)
    put(bm, "F6", '="extended ("&CUR&")"', F_HEAD, fill=FILL_HEAD)
    bom = [
        ("Magnetic pump", "Utron SiFe core, M235-35A, laser-cut + bonded (1.26 kg each)", 6, 35.0,
         "Quantity: 3 utrons per side; mass from pole_design_variants.json. Placeholder price."),
        ("Magnetic pump", "Utron winding copper, 1.89 mm², 200 turns (1.07 kg each)", 6, 18.0,
         "15 /kg wire + former. Placeholder."),
        ("Magnetic pump", "Utron NiFe neck strip, cheeks, slot cover, air-break spacer", 6, 25.0, "Placeholder."),
        ("Magnetic pump", "Utron winding labour (h)", 12, "=LABOUR", "2 h per utron. Placeholder hours."),
        ("Magnetic pump", "G10 carrier discs", 4, 25.0, "2 per side. Placeholder."),
        ("Magnetic pump", "SiFe passive bridges, laminated (counter-rotor)", 12, 15.0, "6 per side. Placeholder."),
        ("Magnetic pump", "G10 bridge rings (counter-rotor)", 2, 60.0, "Placeholder."),
        ("Magnetic pump", "La / Lb gapped EI chokes (1.0 kg iron, 0.41 kg Cu)", 2, 45.0,
         "First cut, rotor_parts_duty_results.json. Placeholder."),
        ("Magnetic pump", "D1*-D4* power diodes", 4, 3.0, "Low-voltage, high-current. Placeholder."),
        ("Magnetic pump", "Node snubbers (RC)", 8, 1.5, "Placeholder."),
        ("Magnetic pump", "Start-kick source (capacitor + push-button)", 1, 30.0, "Open item: 15-20 % of Psi_s, tens of mJ."),
        ("AH (hub)", "AH coils, 160 turns, on the former", 2, 15.0, "Placeholder."),
        ("AH (hub)", "AH bypass capacitors, 10 mF / 6.3 V (2 per coil = 20 mF)", 4, 8.0,
         "The steady cusp (sim/ah-steady-cusp-findings.md). Bipolar parts if the kick polarity is free."),
        ("AH (hub)", "MnZn rod", 1, 30.0, "Placeholder."),
        ("Hub", "Core electrodes on the two G10 cones (conductive layer or foil; not chosen)", 2, 40.0,
         "The cones are non-metallic (G10), so each carries an electrode (sim/core-field-findings.md). Placeholder."),
        ("Hub", "Vacuum sphere (glass vessel)", 1, 250.0, "Placeholder."),
        ("Hub", "Core capacitors, 1 nF / 30 kV (ceramic doorknob): C_core, or Cca + Ccb", "=IF(CORE_MODE=1,1,2)", 25.0,
         "Steady: C_core holds cone A at the peak. Swinging: Cca / Ccb couple the cones to nodes 1 / 4. Placeholder."),
        ("Hub", "The electrodes' HV leads and their clearances to the flanges and each other", 1, 60.0,
         "Creepage along the G10 shells is open (the electrode geometry is not chosen). Placeholder."),
        ("Electrostatic (fixed)", "Rotor HV insulation: sleeve bore bonded or coated, potting of D1-D4, Z1 / Z4, Dk", 1,
         80.0, "The HV side is on the rotor now (sim/core-field-findings.md). Placeholder."),
        ("Electrostatic (fixed)", "Surge resistors for D1-D4", 4, 5.0, "10-47 kOhm HV resistors. Placeholder."),
        ("Electrostatic (fixed)", "HV wiring, insulation, standoffs (on the rotor)", 1, 60.0, "Placeholder."),
        ("Electrostatic (fixed)", "Reference link (brush or bearing strap)", 1, 20.0, "Placeholder."),
        ("Mechanics", "Bearings, 6205-class", 6, 12.0, "4 inner + 2 end. Placeholder."),
        ("Mechanics", "G10 bearing spiders", 4, 30.0, "Placeholder."),
        ("Mechanics", "Shaft-half flanges", 2, 40.0, "Placeholder."),
        ("Mechanics", "1 : -1 reversing gear", 1, 250.0, "Placeholder."),
        ("Mechanics", "Drive motor and belt", 1, 250.0, "Placeholder."),
        ("Mechanics", "Frame and end-bearing housings", 1, 300.0, "Placeholder."),
        ("Mechanics", "Balancing", 1, 150.0, "Placeholder: rotor and counter-rotor."),
    ]
    b0 = 7
    for i, (grp, item, qty, price, note) in enumerate(bom):
        rr = b0 + i
        put(bm, f"B{rr}", grp, F_TXT); put(bm, f"C{rr}", item, F_TXT)
        put(bm, f"D{rr}", qty, F_CALC if isinstance(qty, str) else F_IN, fmt="#,##0")
        if isinstance(price, str):
            put(bm, f"E{rr}", price, F_LINK, fmt=MONEY2)
        else:
            put(bm, f"E{rr}", price, F_IN, fmt=MONEY2)
        put(bm, f"F{rr}", f"=D{rr}*E{rr}", F_CALC, fmt=MONEY)
        put(bm, f"G{rr}", note, F_NOTE)
    b1 = b0 + len(bom) - 1
    put(bm, "F4", f"=SUM(F{b0}:F{b1})", F_CALC, fmt=MONEY, bold=True)
    put(bm, "G4", "Excludes contingency (applied on Designs).", F_NOTE)

    # ------------------------------------------------------------------------------------------------- Designs
    ds = wb.create_sheet("Designs")
    cols = [  # (header, key or formula template, format, width, kind)
        ("design", None, "0", 7, "id"),
        ("gap (mm)", "gap_mm", NUM1, 8, "v"),
        ("vane t (mm)", "t_vaneMm", NUM1, 8, "v"),
        ("r_out (mm)", "r_outMm", "0", 8, "v"),
        ("sector (deg)", "ws_deg", "0", 8, "v"),
        ("vanes N", "n_plates", "0", 7, "v"),
        ("V_op (kV)", "V_op_kV", NUM2, 9, "v"),
        ("C_min (pF)", "C_min_pF", "0", 9, "v"),
        ("C_max (pF)", "C_max_pF", "0", 9, "v"),
        ("kappa", "kappa", NUM2, 8, "v"),
        ("z", "z", NUM3, 8, "v"),
        ("P clamped (W)", "P_clamped_est_W", NUM2, 9, "v"),
        ("stacks/side (mm)", "L_es_side_mm", "0", 9, "v"),
        ("tube (mm)", "L_tube_mm", "0", 8, "v"),
        ("rim onset, handled (kV)", "V_onset_handled_kV", NUM2, 10, "v"),
        ("vanes, Al-equiv (kg)", None, NUM2, 10, "vanekg"),
        ("Ca/Cb, Al-equiv (kg)", "ca_plates_kg", NUM2, 10, "v"),
        ("vanes (count)", None, "0", 8, "nv"),
        ("plates (count)", None, "0", 8, "np"),
        ("cut (m)", None, NUM1, 8, "cut"),
        ("rounded edge (m)", None, NUM1, 9, "rnd"),
        ("G10 cage (kg)", None, NUM2, 8, "cage"),
        ("G10 sleeve (kg)", None, NUM3, 8, "sleeve"),
        ("vane metal", "=P{r}*RHO_VANE/2700*(1+SCRAP)*PRICE_VANE", MONEY, 10, "f"),
        ("plate metal", "=Q{r}*RHO_PLATE/2700*(1+SCRAP)*PRICE_PLATE", MONEY, 10, "f"),
        ("cutting", "=T{r}*CUT_M+(R{r}+S{r})*CUT_SET", MONEY, 9, "f"),
        ("full rounds", "=U{r}*ROUND_M", MONEY, 9, "f"),
        ("deburr + polish", "=(R{r}+S{r})*FINISH_PART", MONEY, 9, "f"),
        ("spacers + assembly", "=R{r}*SPACER_VANE+(R{r}+S{r})*ASM_H*LABOUR", MONEY, 10, "f"),
        ("G10 cage + sleeve", "=V{r}*G10_CAGE+W{r}*G10_SLEEVE", MONEY, 9, "f"),
        ("shaft", "=N{r}/1000*SHAFT_M+SHAFT_SET", MONEY, 8, "f"),
        ("HV parts", "=2*ROUNDUP(G{r}*1000/V_ZENER,0)*PRICE_Z+(4+IF(CORE_MODE=1,1,0))*ROUNDUP(G{r}*DIODE_SAFETY/V_STICK,0)"
                     "*PRICE_STICK", MONEY, 9, "f"),
        ("stack subtotal", "=SUM(X{r}:AF{r})", MONEY, 10, "f"),
        ("fixed BOM", "=FIXED_BOM", MONEY, 9, "link"),
        ("total incl. contingency", "=(AG{r}+AH{r})*(1+CONT)", MONEY, 11, "f"),
        ("per watt", "=IF(AR{r}>0,AI{r}/AR{r},1E+12)", MONEY, 9, "f"),
        ("meets targets", "=IF(AND(AP{r}>=V_NEED,AR{r}>=P_MIN,AQ{r}>=Z_MIN,F{r}<=N_CAP,D{r}<=R_MAX,"
                          "OR(CORONA_REQ=0,O{r}>=G{r})),1,0)", "0", 8, "fv"),
        ("score", "=IF(AK{r}=1,IF(OBJECTIVE=1,AI{r},AJ{r}),1E+12)+ROW()*1E-9", "0.00", 10, "fv"),
        ("core swing, floating (kV)", None, NUM2, 9, "swing"),
        ("z, swinging core", None, NUM3, 8, "zsw"),
        ("P clamped, swinging core (W)", None, NUM2, 9, "psw"),
        ("core voltage (kV)", "=IF(CORE_MODE=1,G{r},AM{r})", NUM2, 9, "fv"),
        ("z with the core", "=IF(CORE_MODE=1,K{r},AN{r})", NUM3, 8, "fv"),
        ("P with the core (W)", "=IF(CORE_MODE=1,L{r},AO{r})", NUM2, 9, "fv"),
    ]
    assert [get_column_letter(i + 1) for i in range(len(cols))][38:44] == ["AM", "AN", "AO", "AP", "AQ", "AR"]
    assert [get_column_letter(i + 1) for i in range(len(cols))][23] == "X"     # the formulas' column letters
    put(ds, "A1", "Designs: the vane matrix with live costs", F_TITLE)
    put(ds, "A2", "Columns B-W: results of sim/vane_matrix.py (values, do not edit). Columns X-AL: formulas on Inputs. "
                  "AM-AO: the swinging core's swing, z and power (sim/core_swing_grid.json; values). AP-AR: the core "
                  "mode's voltage, z and power (formulas). Al-equivalent masses assume 2700 kg/m³ and are rescaled by "
                  "the chosen materials' densities.", F_NOTE)
    for i, (h, key, fmt, wd, kind) in enumerate(cols):
        col = get_column_letter(i + 1)
        ds.column_dimensions[col].width = wd
        c = put(ds, f"{col}4", h, F_HEAD, fill=FILL_HEAD, align=Alignment(wrap_text=True, vertical="top"))
        if kind in ("f", "link"):
            c.value = f'="{h} ("&CUR&")"'
    ds.row_dimensions[4].height = 42
    ds.freeze_panes = "B5"
    r0 = 5
    for k, q in enumerate(rows):
        rr = r0 + k
        gq = geometry(q)
        sw = swing_at(q["C_max_pF"], q["kappa"])                    # swing / V_op, z ratio, power ratio
        for i, (h, key, fmt, wd, kind) in enumerate(cols):
            col = get_column_letter(i + 1)
            if kind == "id":
                v, f = k + 1, F_TXT
            elif kind == "v":
                v, f = q[key], F_TXT
            elif kind == "vanekg":
                v, f = q["rotor_vanes_kg"] + q["stator_vanes_kg"], F_TXT
            elif kind == "nv":
                v, f = gq["n_vanes"], F_TXT
            elif kind == "np":
                v, f = gq["n_plates"], F_TXT
            elif kind in ("cut", "rnd", "cage", "sleeve"):
                v, f = gq[{"cut": "cut_m", "rnd": "round_m", "cage": "cage_kg", "sleeve": "sleeve_kg"}[kind]], F_TXT
            elif kind == "swing":
                v, f = sw[0] * q["V_op_kV"], F_TXT
            elif kind == "zsw":
                v, f = sw[1] * q["z"], F_TXT
            elif kind == "psw":
                v, f = sw[2] * q["P_clamped_est_W"], F_TXT
            else:
                v, f = key.format(r=rr), (F_LINK if kind == "link" else F_CALC)
            cell = ds[f"{col}{rr}"]
            cell.value = round(v, 6) if isinstance(v, float) else v
            cell.font = f
            cell.number_format = fmt
    r1 = r0 + len(rows) - 1
    name(wb, "SCORE", f"Designs!$AL${r0}:$AL${r1}")
    name(wb, "MEETS", f"Designs!$AK${r0}:$AK${r1}")

    # ------------------------------------------------------------------------------------------------- Optimum
    op = wb.create_sheet("Optimum", 1)
    for col, wd in zip("ABCDEFGHIJKLMNOPQRS", (3, 34, 14, 12, 12, 10, 10, 10, 10, 10, 11, 12, 13, 13, 13, 13, 12, 12, 12)):
        op.column_dimensions[col].width = wd
    put(op, "B2", "Optimum: the design that meets the targets at the lowest cost", F_TITLE)
    put(op, "B3", "Formulas only. Change the targets and prices on Inputs.", F_NOTE)
    put(op, "B5", "Designs that meet the targets", F_TXT)
    put(op, "C5", "=COUNTIF(MEETS,1)", F_CALC, fmt="#,##0")
    put(op, "B6", "Best row on Designs", F_TXT)
    put(op, "C6", "=IF(MIN(SCORE)>=1E+12,0,MATCH(MIN(SCORE),SCORE,0))", F_CALC, fmt="0")
    put(op, "B7", "Status", F_TXT)
    put(op, "C7", '=IF(C6=0,"No design meets the targets: relax them on Inputs","Best design below")', F_CALC)
    put(op, "E5", "AH steady cusp (does not depend on the stack)", F_TXT)
    put(op, "E6", '="delivered "&TEXT(AT_DELIVERED,"0")&" A-turns per coil against "&TEXT(AT_TARGET,"0")&" wanted"', F_CALC)
    put(op, "E7", '=IF(AT_DELIVERED>=AT_TARGET,"met with the 22 mF bypass","re-size the AH or the pump (not costed here)")',
        F_CALC)
    name(wb, "BEST", "Optimum!$C$6")
    fields = [("gap", "B", NUM1, "mm"), ("vane thickness (full round)", "C", NUM1, "mm"), ("outer radius", "D", "0", "mm"),
              ("sector width", "E", "0", "deg"), ("vanes per varicap per side", "F", "0", "stator = rotor"),
              ("operating peak", "G", NUM2, "kV"), ("core voltage (peak, for the core field chosen)", "AP", NUM2, "kV"),
              ("C_max", "I", "0", "pF"), ("kappa", "J", NUM2, ""), ("z, bare pump", "K", NUM3, ""),
              ("z with the core", "AQ", NUM3, ""), ("clamped power, bare pump", "L", NUM2, "W"),
              ("clamped power with the core", "AR", NUM2, "W"), ("stacks per side", "M", "0", "mm"),
              ("tube length", "N", "0", "mm"),
              ("rim onset, handled", "O", NUM2, "kV"), ("vane metal", "X", MONEY, "cur"), ("plate metal", "Y", MONEY, "cur"),
              ("cutting", "Z", MONEY, "cur"), ("full rounds", "AA", MONEY, "cur"), ("deburr + polish", "AB", MONEY, "cur"),
              ("spacers + assembly", "AC", MONEY, "cur"), ("G10 cage + sleeve", "AD", MONEY, "cur"), ("shaft", "AE", MONEY, "cur"),
              ("HV parts", "AF", MONEY, "cur"), ("stack subtotal", "AG", MONEY, "cur"), ("fixed BOM", "AH", MONEY, "cur"),
              ("total incl. contingency", "AI", MONEY, "cur"), ("per watt", "AJ", MONEY, "cur")]
    put(op, "B9", "best design", F_HEAD, fill=FILL_HEAD); put(op, "C9", "value", F_HEAD, fill=FILL_HEAD)
    put(op, "D9", "unit", F_HEAD, fill=FILL_HEAD)
    for i, (lab, col, fmt, unit) in enumerate(fields):
        rr = 10 + i
        put(op, f"B{rr}", lab, F_TXT)
        put(op, f"C{rr}", f'=IF(BEST=0,"",INDEX(Designs!${col}${r0}:${col}${r1},BEST))', F_LINK, fmt=fmt, fill=FILL_BEST)
        put(op, f"D{rr}", "=CUR" if unit == "cur" else unit, F_CALC if unit == "cur" else F_TXT)
    rk = 10 + len(fields) + 2
    put(op, f"B{rk}", "The next best (rank by the objective on Inputs)", F_SEC)
    top_cols = [("rank", None, "0"), ("gap (mm)", "B", NUM1), ("t (mm)", "C", NUM1), ("r_out (mm)", "D", "0"),
                ("sector", "E", "0"), ("N", "F", "0"), ("core (kV)", "AP", NUM2), ("z", "AQ", NUM3), ("P (W)", "AR", NUM2),
                ("stack/side (mm)", "M", "0"), ("stack subtotal", "AG", MONEY), ("total", "AI", MONEY),
                ("per watt", "AJ", MONEY)]
    hr = rk + 1
    for j, (h, col, fmt) in enumerate(top_cols):
        c = get_column_letter(2 + j)
        put(op, f"{c}{hr}", h if col not in ("AG", "AI", "AJ") else f'="{h} ("&CUR&")"', F_HEAD, fill=FILL_HEAD)
    for k in range(1, 11):
        rr = hr + k
        put(op, f"B{rr}", k, F_TXT)
        idx = f'IF(SMALL(SCORE,{k})>=1E+12,0,MATCH(SMALL(SCORE,{k}),SCORE,0))'
        for j, (h, col, fmt) in enumerate(top_cols[1:], start=1):
            c = get_column_letter(2 + j)
            put(op, f"{c}{rr}", f'=IF({idx}=0,"",INDEX(Designs!${col}${r0}:${col}${r1},{idx}))', F_LINK, fmt=fmt)
    mr = hr + 13
    put(op, f"B{mr}", "Material: the best design's vanes and plates in each material", F_SEC)
    for j, h in enumerate(("material", "density (kg/m³)", "metal (kg)", "metal cost", "vs the chosen")):
        put(op, f"{get_column_letter(2 + j)}{mr + 1}", h if j != 3 else '="metal cost ("&CUR&")"', F_HEAD, fill=FILL_HEAD)
    for i in range(len(mats)):
        rr = mr + 2 + i
        put(op, f"B{rr}", f"=INDEX(MAT_NAMES,{i + 1})", F_LINK)
        put(op, f"C{rr}", f"=INDEX(MAT_RHO,{i + 1})", F_LINK, fmt="#,##0")
        put(op, f"D{rr}", f'=IF(BEST=0,"",(INDEX(Designs!$P${r0}:$P${r1},BEST)+INDEX(Designs!$Q${r0}:$Q${r1},BEST))'
                          f'*C{rr}/2700)', F_CALC, fmt=NUM1)
        put(op, f"E{rr}", f'=IF(BEST=0,"",D{rr}*(1+SCRAP)*INDEX(MAT_PRICE,{i + 1}))', F_CALC, fmt=MONEY)
        put(op, f"F{rr}", f'=IF(BEST=0,"",E{rr}-(INDEX(Designs!$X${r0}:$X${r1},BEST)+INDEX(Designs!$Y${r0}:$Y${r1},BEST)))',
            F_CALC, fmt=MONEY)
    put(op, f"B{mr + 2 + len(mats)}", "The material does not change the electrostatics (any good conductor works); it "
        "changes mass, finish and cost.", F_NOTE)

    # ------------------------------------------------------------------------------------------------- Notes
    nt = wb.create_sheet("Notes")
    nt.column_dimensions["A"].width = 3
    nt.column_dimensions["B"].width = 125
    notes = [
        ("Geometry-derived quantities on Designs (values computed by docs/make_cost_sheet.py)", F_SEC),
        ("Vanes: 6 sectors on a 60 deg pitch, stator = rotor width w, from r_in 50 mm to r_out. Stator vane: sectors on an "
         "outer ring r_out..r_out+12 (held in the cage). Rotor vane: an inner ring 20.5..50 (on the sleeve) with the "
         "sectors.", F_TXT),
        ("Rounded edges (full round R = t/2): the stator's sides, inner arcs and the ring's inner edge between sectors; "
         "the rotor's sides, outer arcs and the ring's outer edge; both rims of each Ca / Cb plate.", F_TXT),
        ("Cut length: the rounded edges plus the stator's outer circle (r_out+12) and the rotor's bore (20.5); both "
         "circles of each plate. Counts: 4N vanes and 2 (n_ca+1) plates for the two sides.", F_TXT),
        ("G10: the stator cage r_out+12..r_out+16 and the rotor sleeve 12.5..20.5, each over the stacks plus 50 mm per "
         "side for the bearing spiders' seats, at 1850 kg/m³.", F_TXT),
        ("Masses: the matrix's rotor and stator vanes (sectors and rings) and full-annulus plates at 2700 kg/m³; the "
         "rounds take < 1 % off and are ignored.", F_TXT),
        ("", F_TXT),
        ("What is not in the cost", F_SEC),
        ("Re-sizing the AH or the magnetic pump for more than the delivered steady ampere-turns; the shaft and bearings "
         "for the heavier rotors at large radius (not checked); design, test equipment, the vacuum system, tooling.",
         F_TXT),
        ("The electric field on the core (Inputs: core field). The electrostatic circuit's HV side is on the rotor "
         "(sim/core_field.py, sim/core-field-findings.md). A design qualifies when the core's voltage reaches E x "
         "spacing.", F_TXT),
        ("2, swinging (the default): the cones float, each coupled through 1 nF to node 1 / 4, and the core sees the AC "
         "of V(1) - V(4) at the pump frequency. Its peak (AM on Designs) is about 0.55 of the operating peak. The cones' "
         "strays (20 pF each, 10 pF between them [RH]) sit on the pumping nodes, so small stacks lose gain and power "
         "(AN, AO). AM-AO come from ngspice over C_max x kappa (sim/core_swing_grid.json), interpolated per design.",
         F_TXT),
        ("1, steady: the core diode Dk charges cone A to the operating peak and C_core holds it; cone B sits on the "
         "shaft. The pump keeps its gain and power if the core's leakage stays above about 1 GOhm. HV parts then count a "
         "fifth diode stack (Dk).", F_TXT),
    ]
    for i, (txt, f) in enumerate(notes, start=2):
        put(nt, f"B{i}", txt, f)
        nt[f"B{i}"].alignment = Alignment(wrap_text=True, vertical="top")

    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    wb.save(OUT)
    print(OUT, len(rows), "designs")


if __name__ == "__main__":
    build()
