"""sim/parts_first_cut.py -- first-cut designs and ratings for the parts the locked design leaves "not chosen" or "not
designed" (docs/ledger/DCCREG-design-ledger.md §5.1-§5.2). Writes sim/parts_first_cut_results.json; the findings are
sim/parts-first-cut-findings.md.

1. La / Lb: a gapped EI DC choke for 0.146 H at the record's 0.87-1.15 A (sim/rotor_parts_duty_results.json), over the
   standard scrapless EI sizes: turns for the peak flux density, a real layer winding of IEC 60317 grade-2 wire in the
   bobbin, the gap, R at 20 C (the model's basis) and in service, losses, mass, outline and the load at a radius. The
   chosen size and a compact one run in the pump (ngspice) at their own tau = L / R.
2. Ratings: the duty of every part from fresh ngspice runs of the two netlists of record, set against a rating:
   - the magnetic dual doubler at the pick, exactly as sim/rotor_parts_duty.py runs it (sim/magnetic_doubler.py deck,
     sim/pole_design_variants_op.json), without and with the 22 mF AH bypass (sim/ah_steady_cusp.py's C + ESR):
     D1*-D4*, the node snubbers, the bypass, La / Lb; and the diodes' forward drop as a sensitivity;
   - the electrostatic pump with the rings' symmetric supply, exactly as sim/hub_rings_build.py runs record_supply
     (sim/core_field.py dc, 2 + 2 stages, 100 pF, 100 GOhm, 280 cycles): D1-D4, the 8 chain diodes, the 8 chain
     capacitors, the clamps Z1 / Z4, the surge resistors; and a flashover's surge, by charge sharing [IR].
3. The start kick: the seed sim/pole_design.py gives (a current frac * Psi_s / L_max in every coil) and its energy; the
   threshold refined; the seed's sign reversed; a capacitor (or a cell) dumped across La through an SCR, both
   polarities, against the threshold; and below full speed: the speed from which the chosen kick starts the pump, and
   whether a running pump holds as it slows (the same parts on a stretched cycle).
4. Creepage and clearance of the rotor's HV parts and the Ca / Cb mounts, IEC 60664-1 style (pollution degree 2,
   material groups by CTI); [RH] wherever the table is extrapolated above 1 kV.
5. Potting and impregnation: a short specification (data only).
Tags (CONVENTIONS.md §1): [OC] derivable physics; [IR] a modelling or engineering choice, datasheet-class values
included; [RH] heuristic, not load-bearing. Never a bare d: g for a gap, "diameter" spelled out.
Usage: python3 sim/parts_first_cut.py [--procs 4] [--cache FILE]   (about 20 minutes on 4 idle cores; needs ngspice)
"""
import argparse
import json
import math
import os
import pickle
import re
import subprocess
import sys
import tempfile
from multiprocessing import Pool

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
import core_field as CF            # noqa: E402  (the electrostatic deck of record)
import magnetic_doubler as M       # noqa: E402  (the magnetic dual doubler's deck)
import rotor_parts_duty as RP      # noqa: E402  (the pick's kwargs, exactly as the duty study runs it)

_trapz = getattr(np, "trapezoid", getattr(np, "trapz", None))     # numpy 1.x / 2.x (CONVENTIONS.md §3)

SRC = {
    "duty": "sim/rotor_parts_duty_results.json",
    "op": "sim/pole_design_variants_op.json",
    "cusp": "sim/ah_steady_cusp_results.json",
    "rings": "sim/hub_rings_build_results.json",
    "core": "sim/core_field_results.json",
    "hub": "presets/hub-locked.json",
}
PICK = RP.PICK
AT_TARGET = 450.0                  # the AH target the pick was sized to (sim/pole_design.py AT_TARGET)
START_AT = 0.5 * AT_TARGET         # "it starts": the AH reaches half the target, as sim/pole_design.py size_op [IR]
ESR_BYP = 0.01                     # the bypass's ESR, as sim/ah_steady_cusp.py [RH]
C_BYP_MF = 22.0                    # the bypass of sim/ah-steady-cusp-findings.md (PROPOSED)

# ---------------------------------------------------------------------------------------------------- the choke
EI = {"EI-66": 22.0, "EI-76": 25.4, "EI-84": 28.0, "EI-96": 32.0, "EI-105": 35.0, "EI-120": 40.0}
# scrapless EI [OC: the proportions]: centre leg a, outer legs a / 2, window a / 2 x 3a / 2, outline 3a x 2.5a
STACK_RATIOS = (1.0, 1.25, 1.5, 2.0)             # stack height / centre-leg width; bobbins come in such steps [IR]
B_MAX = 1.20                                     # T at the steady peak current, non-oriented SiFe [IR]
B_KNEE = 1.45                                    # T: above it the inductance starts to fall (M400-50A class) [IR]
K_STACK = 0.95                                   # lamination stacking factor [IR]
MU_R, MU_R_RANGE = 3000.0, (1500.0, 8000.0)      # the iron at 1.2 T with DC bias [RH]; it only trims the gap
L_FE_PER_A = 6.0                                 # mean magnetic path of a scrapless EI, in a [IR]
P15_50, RHO_FE = 4.0, 7700.0                     # M400-50A: 4.0 W/kg max at 1.5 T, 50 Hz (EN 10106) [IR datasheet-class]
FE_LOSS_K = 1.5                                  # x for the DC bias and the non-sinusoidal ripple [RH]
RHO20, ALPHA_CU, RHO_CU = 1.7241e-8, 0.00393, 8890.0   # annealed copper (IEC 60028) [OC]
WIRES = (0.50, 0.56, 0.63, 0.71, 0.75, 0.80, 0.85, 0.90, 0.95, 1.00, 1.06, 1.12, 1.18, 1.25, 1.32, 1.40, 1.50,
         1.60, 1.70, 1.80, 1.90, 2.00, 2.12, 2.24, 2.36, 2.50)     # IEC 60317 R20 bare diameters, mm
OD_K, OD_ADD = 1.03, 0.05                        # grade-2 overall diameter ~ 1.03 x bare + 0.05 mm [IR datasheet-class]
T_BOB, CLR_LEG, T_FLANGE, CLR_OUT, T_TAPE, PITCH, BUILD_USE = 1.0, 0.25, 1.5, 1.0, 0.05, 1.04, 0.95
# bobbin wall, clearance to the leg, flange, clearance to the outer leg, polyester interlayer, winding pitch / OD, the
# share of the build used (5 % spare) -- all mm [IR]
T_AMB_C, H_CONV = 40.0, 25.0                     # rotor ambient and forced convection, as sim/pole_design.py [RH]
W_ROTOR = 2 * math.pi * 600.0 / 60.0             # the rotor's own speed against the frame, rad/s [OC]

# ---------------------------------------------------------------------------------------------------- the diodes
DIODE_MODELS = {
    # name: (is, n, rs) at 27 C; V_F at 1 A / 3 A
    "rec": (1e-9, 1.0, 1e-3),        # the record's (sim/magnetic_doubler.py ND, nd 1): 0.54 V at 1 A [IR]
    "si": (2.3e-9, 1.6, 0.027),      # a 3 A, 400 V Si rectifier of the 1N540x class: 0.85 / 0.95 V typ. [IR datasheet-class]
    "sch": (6.5e-7, 1.2, 0.058),     # a 100 V, 3-5 A Schottky: 0.50 / 0.65 V typ. [IR datasheet-class]
    "sch200": (4.8e-9, 1.3, 0.0565), # a 200 V, 3-5 A Schottky: 0.70 / 0.85 V typ. [IR datasheet-class]
}
# the kick's candidates [IR]: (name, kind, C in uF or None, V, the cell path's R or None, closure s or None)
KICKS = (
    ("K1 film 10 uF at 50 V", "cap", 10.0, 50.0, None, None),
    ("K2 film 22 uF at 50 V", "cap", 22.0, 50.0, None, None),
    ("K3 100 uF at 25 V", "cap", 100.0, 25.0, None, None),
    ("K4 470 uF at 9 V (a 9 V cell)", "cap", 470.0, 9.0, None, None),
    ("K5 4.7 mF at 3.6 V (a 3.6 V cell)", "cap", 4700.0, 3.6, None, None),
    ("K6 3.6 V cell, 1 ohm, 20 ms", "cell", None, 3.6, 1.0, 0.02),
    ("K7 9 V cell, 2 ohm, 20 ms", "cell", None, 9.0, 2.0, 0.02),
)
KICK_E_SWEEP = (("10 uF", 10.0, (20.0, 30.0, 40.0)), ("100 uF", 100.0, (10.0, 15.0, 20.0)))   # uF, V [IR]
R_KICK = 0.1                         # the kick path's ESR + wiring, ohm [IR]
KICK_PHASES = (1.0, 1.25, 1.5, 1.75)     # the kick's time in pump cycles (0: L1 aligned) [IR]
# below full speed (the pick is 120 Hz, 1200 rpm relative): the K4 kick, the record's seed, and a large seed as a proxy
# for a running pump that slows down [IR]
SPEED_K4_HZ = (40.0, 80.0, 90.0, 95.0, 100.0, 105.0, 110.0)    # 40 Hz: 200 rpm each way
SPEED_K4_DIODES = (("sch", (95.0, 100.0)), ("si", (105.0, 110.0, 115.0)))
SPEED_SEED_HZ = (100.0, 110.0)
SPEED_HOLD_HZ = (60.0, 70.0, 80.0, 90.0)
HOLD_FRAC = 0.6                      # the large seed: 60 % of Psi_s in every coil [IR]
N_CYC_SPEED = 80
RUN_AT = 50.0                        # "it runs": > 50 A-turns over the last 4 of 80 cycles; a dying pump is at ~0 [IR]


def t_on_cap(c_uF, L):
    """the SCR conducts for its dump (a pulsed gate): a quarter period of L with C, x 1.25, + 1 ms [IR]."""
    return 1.25 * 0.5 * math.pi * math.sqrt(L * c_uF * 1e-6) + 1e-3
SEED_FRACS = (0.10, 0.12, 0.14, 0.16, 0.18, 0.20, 0.25, 0.30)

# ---------------------------------------------------------------------------------------------------- HV parts
R_SURGE = 22e3                       # per D1-D4 position: the middle of sim/diode-stack-findings.md's 10-47 kOhm [IR]
STICK_KV = 20.0                      # one HV rectifier stick (the 2CL77 class of sim/diode-stack-findings.md) [IR]
Z_N, Z_V = 66, 200.0                 # the clamp string's first cut (docs/ledger/DCCREG-design-ledger.md §3.4)
Z_TOL, Z_TC = 0.05, 0.001            # +-5 % parts (B / A suffix), +0.1 %/K for 200 V avalanche parts [IR datasheet-class]
C_CHAIN_KV = 30.0                    # the chains' 100 pF parts, 30 kV (docs/rings-design.md §4)
E_POT = 2.0                          # kV/mm average in void-free silicone potting, DC design [RH]
# IEC 60664-1, Table F.4 (creepage, pollution degree 2): 5.0 / 7.1 / 10.0 mm at 1 kV rms for material groups I / II /
# III, proportional to the voltage from 250 V to 1 kV in the table [IR: the table, as recalled]; above 1 kV taken
# proportional again [RH]. Pollution degree 3: 12.5 / 14 / 16 mm at 1 kV [IR], proportional above [RH].
CREEP_PD2 = {"I": 5.0, "II": 7.1, "IIIa": 10.0, "IIIb": 10.0}
CREEP_PD3 = {"I": 12.5, "II": 14.0, "IIIa": 16.0, "IIIb": 16.0}
DC_MARGIN = 1.25                     # x on creepage: a DC field on a rotor collects dust [RH]
MATERIALS = {                        # material group by CTI (IEC 60112) [IR datasheet-class]
    "PTFE": ("I", "CTI >= 600"),
    "silicone (potting surface)": ("I", "CTI >= 600 typical of silicone elastomers"),
    "G10 / FR4": ("IIIa", "CTI 175-250 typical"),
    "PEEK, unfilled": ("IIIb", "CTI 150 (Victrex 450G datasheet)"),
    "glazed alumina / steatite": ("inorganic", "does not track: creepage need not exceed the clearance (IEC 60664-1)"),
}
# IEC 60664-1, Table F.2, case A (inhomogeneous field), clearance against impulse withstand voltage, up to 2000 m
# [IR: the table, as recalled]
F2_CASE_A = ((2.5, 1.5), (4.0, 3.0), (5.0, 4.0), (6.0, 5.5), (8.0, 8.0), (10.0, 11.0), (12.0, 14.0), (15.0, 18.0),
             (20.0, 25.0), (25.0, 33.0), (30.0, 40.0), (40.0, 60.0), (50.0, 75.0), (60.0, 90.0), (80.0, 130.0),
             (100.0, 170.0))
CLR_MARGIN = 1.5                     # withstand = 1.5 x the DC peak: the record's air margin (V_op = breakdown / 1.5) [RH]


def load(key):
    return json.load(open(os.path.join(ROOT, SRC[key])))


# ==================================================================================================== 1. La / Lb
def od_mm(bare):
    return OD_K * bare + OD_ADD


def winding(a, s, N):
    """the largest grade-2 wire that winds N turns in layers on the bobbin of a scrapless EI with centre leg a and
    stack s (mm), with BUILD_USE of the build; per-layer mean turns [IR geometry]."""
    w_w, h_w = 0.5 * a, 1.5 * a
    h_av = h_w - 2 * (T_FLANGE + CLR_LEG)
    b_av = (w_w - T_BOB - CLR_LEG - CLR_OUT) * BUILD_USE
    best = None
    for bare in WIRES:
        o = od_mm(bare)
        per = math.floor(h_av / (PITCH * o))
        if per < 1:
            continue
        layers = math.ceil(N / per)
        build = layers * (o + T_TAPE)
        if build > b_av:
            continue
        left, length = N, 0.0
        for k in range(1, layers + 1):
            nk = min(per, left)
            left -= nk
            r = CLR_LEG + T_BOB + (k - 0.5) * (o + T_TAPE)          # the layer's offset from the leg
            length += nk * (2 * (a + s) + 2 * math.pi * r)          # a rounded rectangle round a x s [OC]
        a_w = math.pi * bare ** 2 / 4.0
        best = dict(wire_mm=bare, wire_od_mm=o, wire_mm2=a_w, per_layer=per, layers=layers, build_mm=build,
                    build_avail_mm=b_av / BUILD_USE, length_m=length * 1e-3, mlt_mm=length / N,
                    fill=N * a_w / (w_w * h_w), R20_ohm=RHO20 * length * 1e-3 / (a_w * 1e-6))
    return best


def fringing(g_i, a_fe, h_w):
    """McLyman's fringing factor of one gap g_i (m) in a leg of area a_fe (m^2) under a winding h_w long (m) [IR]."""
    return 1.0 + (g_i / math.sqrt(a_fe)) * math.log(2.0 * h_w / g_i)


def gap_for(L, N, a_fe, l_fe, h_w, mu_r):
    """total gap g (m) for L: N^2 / L = l_fe / (mu0 mu_r A) + g / (mu0 A F), two equal gaps of g / 2 in series
    (E and I butted on a spacer: the centre leg and the two outer legs, of equal total area) [OC/IR]."""
    mu0 = 4e-7 * math.pi
    g = mu0 * N ** 2 * a_fe / L - l_fe / mu_r
    if g <= 0:
        return None, None
    for _ in range(30):
        F = fringing(0.5 * g, a_fe, h_w)
        g = F * (mu0 * N ** 2 * a_fe / L - l_fe / mu_r)
    return g, F


def choke(name, a, s, duty):
    """one EI choke for the record's L at its peak current [IR choices above]."""
    L, I_pk, I_rms, I_min = duty["L_H"], duty["I_pk_A"], duty["I_rms_A"], duty["I_min_A"]
    a_fe = a * s * K_STACK * 1e-6
    N = math.ceil(L * I_pk / (B_MAX * a_fe))
    w = winding(a, s, N)
    if w is None:
        return dict(core=name, a_mm=a, stack_mm=s, fits=False)
    l_fe, h_w = L_FE_PER_A * a * 1e-3, 1.5 * a * 1e-3
    g, F = gap_for(L, N, a_fe, l_fe, h_w, MU_R)
    if g is None:
        return dict(core=name, a_mm=a, stack_mm=s, fits=False, why="the iron alone gives less than L: N would rise")
    mu0 = 4e-7 * math.pi

    def L_at(mu_r):
        return N ** 2 / (l_fe / (mu0 * mu_r * a_fe) + g / (mu0 * a_fe * F))
    B_pk = L * I_pk / (N * a_fe)
    dB_pp = L * (I_pk - I_min) / (N * a_fe)
    m_fe = 6 * a * a * s * K_STACK * 1e-9 * RHO_FE
    m_cu = RHO_CU * w["length_m"] * w["wire_mm2"] * 1e-6
    p_fe = FE_LOSS_K * m_fe * P15_50 * (duty["f_Hz"] / 50.0) ** 1.3 * (0.5 * dB_pp / 1.5) ** 2      # [RH]
    depth = s + 2 * (CLR_LEG + T_BOB + w["build_mm"])
    outline = (3 * a, 2.5 * a, depth)
    area = 2 * (outline[0] * outline[1] + outline[0] * outline[2] + outline[1] * outline[2]) * 1e-6
    T = T_AMB_C
    for _ in range(5):                                   # copper temperature: ambient + the choke's own rise [RH]
        R_T = w["R20_ohm"] * (1 + ALPHA_CU * (T - 20.0))
        P = R_T * I_rms ** 2 + p_fe
        T = T_AMB_C + P / (H_CONV * area)
    force = B_pk ** 2 * a * s * K_STACK * 1e-6 / (2 * mu0)      # the centre-leg gap's pull at the peak [OC]
    m = m_fe + m_cu
    return dict(core=name, a_mm=a, stack_mm=s, fits=True, turns=N, B_pk_T=B_pk, B_ripple_pp_T=dB_pp, **w,
                gap_total_mm=g * 1e3, spacer_mm=0.5 * g * 1e3, centre_gap_only_mm=g * 1e3, fringing_F=F,
                iron_share_of_reluctance=(l_fe / MU_R) / (l_fe / MU_R + g / F),
                L_at_mu_r_H={f"{int(mu)}": L_at(mu) for mu in (MU_R_RANGE[0], MU_R, MU_R_RANGE[1])},
                I_knee_A=B_KNEE * N * a_fe / L, tau20_s=L / w["R20_ohm"], T_cu_C=T, R_T_ohm=R_T, tau_T_s=L / R_T,
                P_cu_W=R_T * I_rms ** 2, P_cu20_W=w["R20_ohm"] * I_rms ** 2, P_fe_W=p_fe, m_fe_kg=m_fe, m_cu_kg=m_cu,
                m_kg=m, m_with_bobbin_kg=1.08 * m, outline_mm=outline, gap_force_N=force,
                F_centrifugal_N={f"r {r} mm": m * W_ROTOR ** 2 * r * 1e-3 for r in (50, 80, 110)},
                accel_g={f"r {r} mm": W_ROTOR ** 2 * r * 1e-3 / 9.81 for r in (50, 80, 110)},
                unbalance_g_mm={f"r {r} mm": m * 1e3 * r for r in (50, 80, 110)})


def chokes(duty_rec):
    la, lb = duty_rec["la_lb"]["La"], duty_rec["la_lb"]["Lb"]
    duty = dict(L_H=duty_rec["la_lb"]["L_H"], R_model_ohm=duty_rec["la_lb"]["R_ohm"], f_Hz=duty_rec["la_lb"]["f_Hz"],
                I_pk_A=max(la["I_max_A"], lb["I_max_A"]), I_min_A=min(la["I_min_A"], lb["I_min_A"]),
                I_rms_A=max(la["I_rms_A"], lb["I_rms_A"]), I_mean_A=max(la["I_mean_A"], lb["I_mean_A"]),
                V_pk_V=max(la["V_pk_V"], lb["V_pk_V"]), W_pk_J=max(la["W_pk_J"], lb["W_pk_J"]))
    duty["ripple_pp_A"] = duty["I_pk_A"] - duty["I_min_A"]
    duty["ripple_frac"] = 0.5 * duty["ripple_pp_A"] / (0.5 * (duty["I_pk_A"] + duty["I_min_A"]))
    duty["flux_ripple_Wbt"] = duty["L_H"] * duty["ripple_pp_A"]
    rows = []
    for nm, a in EI.items():
        for k in STACK_RATIOS:
            rows.append(choke(nm, a, float(round(k * a)), duty))
    ok = [r for r in rows if r["fits"]]
    R_mod = duty["R_model_ohm"]
    chosen = min([r for r in ok if r["R20_ohm"] <= R_mod], key=lambda r: r["m_kg"])     # meets the model [IR rule]
    compact = min([r for r in ok if r["R20_ohm"] <= 2.0 * R_mod], key=lambda r: r["m_kg"])  # tau >= 0.25 s [IR rule]
    return dict(duty=duty, rows=rows, chosen=chosen, compact=compact, record_first_cut=duty_rec["la_core"][0],
                rule=dict(chosen="the lightest standard EI (iron + copper) with R at 20 C <= the modelled "
                                 f"{R_mod:.3f} ohm (the model's copper is at 20 C, as the utrons')",
                          compact=f"the lightest with R at 20 C <= {2 * R_mod:.3f} ohm (tau >= 0.25 s)"))


# ==================================================================================================== ngspice
MEAS_RE = re.compile(r"^\s*([a-z_][a-z0-9_]*)\s*=\s*([-+]?(?:\d+\.?\d*|\.\d+)(?:e[-+]?\d+)?)", re.I)


def ngspice_meas(txt, ctl, timeout=1200):
    """the deck with its .control block replaced by ctl; the meas results by name (lower case)."""
    deck = re.sub(r"\.control\n.*?\.endc", lambda m: ".control\n" + "\n".join(ctl) + "\n.endc", txt, flags=re.S)
    with tempfile.TemporaryDirectory() as tdir:
        open(os.path.join(tdir, "x.cir"), "w").write(deck)
        try:
            r = subprocess.run(["ngspice", "-b", "x.cir"], capture_output=True, text=True, timeout=timeout, cwd=tdir)
        except subprocess.TimeoutExpired:
            return {"_error": f"ngspice timed out after {timeout} s"}
    out = {}
    for line in r.stdout.splitlines():
        m = MEAS_RE.match(line)
        if m:
            out[m.group(1).lower()] = float(m.group(2))
    if not out:
        out["_error"] = (r.stdout + r.stderr)[-600:]
    return out


def model_line(name, p):
    return f".model {name} D(is={p[0]:.3e} n={p[1]:g} rs={p[2]:g} cjo=0)"


def mag_job(job):
    """one run of the magnetic dual doubler at the pick: sim/rotor_parts_duty.py's kwargs, with optional changes
    (tau_fixed, psi_s, the seed as a signed fraction of Psi_s, n_cyc), the AH bypass, the diodes' models and a kick
    circuit. Everything is measured by ngspice meas; the analysis mirrors sim/magnetic_doubler.analyse."""
    kw = RP._kw(job.get("tau_fixed", RP.TAU_FIXED))
    kw["n_cyc"] = n = job.get("n_cyc", RP.N_CYC)
    if job.get("F_Hz"):
        # another speed: the same parts on a stretched cycle [OC]. The utrons' L(theta) is fixed in angle and every
        # L and R stays; snub_k keeps the snubbers' physical C and R (sim/magnetic_doubler.py snub "scaled")
        kw["snub_k"] = (job["F_Hz"] / kw["F"]) ** 2
        kw["F"] = job["F_Hz"]
    if job.get("psi_s"):
        kw["psi_s"] = job["psi_s"]
    kw["seed"] = job.get("seed_frac", RP.SEED_FRAC) * kw["psi_s"] / kw["L_max"]
    txt, vecs, info = M.deck(**kw)
    F, T = kw["F"], 1.0 / kw["F"]
    h = kw["ah_custom"]
    add = []
    if job.get("bypass_mF"):                                         # sim/ah_steady_cusp.py's bypass [IR]
        # across each AH coil: x1 -> node d, x2 -> node b (the deck's own node names, sim/magnetic_doubler.py)
        c = job["bypass_mF"] * 1e-3
        add += [f"R_bypA x1 xb1 {ESR_BYP:g}", f"C_bypA xb1 d {c:g}", f"R_bypB x2 xb2 {ESR_BYP:g}", f"C_bypB xb2 b {c:g}"]
    dm = job.get("diodes")                                           # {"D1s": "si", ...}
    if dm:
        for dn in ("D1s", "D2s", "D3s", "D4s"):
            txt = re.sub(rf"^({dn} \S+ \S+) ND$", rf"\1 DM_{dm[dn]}", txt, flags=re.M)
        add += [model_line(f"DM_{k}", DIODE_MODELS[k]) for k in sorted(set(dm.values()))]
    ic_extra = {}
    k = job.get("kick")
    if k:                                                            # the start kick [IR]
        # where the kick's current goes: "a" (into La's node), "c" (into Lb's) or "ac" (both, through a diode-OR);
        # pol +1 drives it into the node(s) from REF (the deck's sign), -1 the other way
        tgt = k.get("into", "a")
        tk, ton = k["phase"] * T, k["t_on"]
        # the SCR / reed as a conductance ramped over 20 us (an abrupt switch stalls the solver) in series with the
        # SCR's junction: one-way, about 1 V on [IR]
        g_on = (f"(1e-9+100*(0.5+0.5*tanh((time-{tk:.6e})/2e-5))*(0.5+0.5*tanh(({tk + ton:.6e}-time)/2e-5)))")
        add += [".model DK D(is=1e-9 n=1.6 rs=0.05 cjo=100p)"]       # with its junction capacitance [IR]
        if k["kind"] == "cap":
            add += [f"Ck kp 0 {k['C_mF'] * 1e-3:g}", f"Rk kp kq {R_KICK:g}"]
            ic_extra["kp"] = k["V0"] if k["pol"] > 0 else -k["V0"]
        else:                                                        # the cell itself
            add += [f"Vcell kp 0 DC {k['V0'] if k['pol'] > 0 else -k['V0']:g}", f"Rk kp kq {k['R']:g}"]
        for j, node in enumerate(tgt):
            if k["pol"] > 0:                                         # kq -> D -> switch -> node
                add += [f"Dk{j} kq ks{j} DK", f"Bsk{j} ks{j} km{j} I='V(ks{j},km{j})*{g_on}'", f"Vkm{j} km{j} {node} 0"]
            else:                                                    # node -> switch -> D -> kq (pulls current out)
                add += [f"Vkm{j} {node} km{j} 0", f"Bsk{j} km{j} ks{j} I='V(km{j},ks{j})*{g_on}'", f"Dk{j} ks{j} kq DK"]
            add += [f"Cks{j} ks{j} 0 1n"]                            # the SCR's stray: no floating node [IR]
    seed_only = job.get("seed_only")                                  # keep the seed in these coils only
    if seed_only:
        for nm in ("L1", "AHt", "La", "L2", "AHb", "Lb"):
            if nm not in seed_only:
                txt = re.sub(rf"v\(ps_{nm}\)=\S+", f"v(ps_{nm})=0", txt)
    txt = txt.replace("\n.control", "\n" + "\n".join(add) + "\n.control") if add else txt
    if ic_extra:
        txt = re.sub(r"^(\.ic .*)$", lambda m: m.group(1) + "".join(f" v({a})={b:g}" for a, b in ic_extra.items()),
                     txt, flags=re.M)
    t0, t1 = (n - 4) * T, n * T
    win = f"from={t0:.6e} to={t1:.6e}"
    a_ = M._coeffs(kw)
    w = 2 * math.pi * F
    sh1, _ = M._shape_expr(a_, w, 0.0)
    sh2, _ = M._shape_expr(a_, w, math.pi)
    lp, la = info["lp"], info["la"]
    psi = kw["psi_s"]
    ctl = ["save all @d1s[id] @d2s[id] @d3s[id] @d4s[id]",
           f"tran {T / 2000:.4e} {n * T:.6e} uic",
           f"let i1 = v(ps_l1)/({kw['L_max']:.6e}*{sh1}+{lp:.6e})*(1+(abs(v(ps_l1))/{psi:.6e})^6)",
           f"let i2 = v(ps_l2)/({kw['L_max']:.6e}*{sh2}+{lp:.6e})*(1+(abs(v(ps_l2))/{psi:.6e})^6)",
           "let ai1 = abs(i1)", "let ai2 = abs(i2)",
           f"let iaht = v(ps_aht)/{h['L']:.6e}", f"let iahb = v(ps_ahb)/{h['L']:.6e}",
           f"let ila = v(ps_la)/{la:.6e}", f"let ilb = v(ps_lb)/{la:.6e}"]
    for c_ in range(n):                                              # per-cycle peaks: z as magnetic_doubler.analyse
        ctl += [f"meas tran pa{c_} MAX ai1 from={c_ * T:.6e} to={(c_ + 1) * T:.6e}",
                f"meas tran pb{c_} MAX ai2 from={c_ * T:.6e} to={(c_ + 1) * T:.6e}"]
    ctl += ["meas tran t_last MAX time", f"meas tran i1max MAX ai1 {win}", f"meas tran i1min MIN ai1 {win}", f"meas tran i1rms RMS i1 {win}",
            f"meas tran ahtmax MAX iaht {win}", f"meas tran ahtmin MIN iaht {win}", f"meas tran ahtavg AVG iaht {win}",
            f"meas tran ahbmax MAX iahb {win}", f"meas tran ahbmin MIN iahb {win}", f"meas tran ahbavg AVG iahb {win}",
            "meas tran ahtall_max MAX iaht", "meas tran ahtall_min MIN iaht",
            "meas tran laall_max MAX ila", "meas tran laall_min MIN ila",
            "meas tran lball_max MAX ilb", "meas tran lball_min MIN ilb"]
    for nm in ("la", "lb"):
        ctl += [f"meas tran {nm}max MAX i{nm} {win}", f"meas tran {nm}min MIN i{nm} {win}",
                f"meas tran {nm}avg AVG i{nm} {win}", f"meas tran {nm}rms RMS i{nm} {win}"]
    for e in [v_[4:-1] for v_ in vecs if v_.startswith("v(e_")]:   # the power ledger's integrators
        ctl += [f"meas tran e0_{e} FIND v(e_{e}) AT={t0:.6e}", f"meas tran e1_{e} FIND v(e_{e}) AT={t1 * (1 - 1e-9):.6e}",
                # a fallback a little before the end: rounded, the AT above can fall past the last time point
                f"meas tran e2_{e} FIND v(e_{e}) AT={t1 - T / 4000:.9e}"]
    if job.get("duty"):
        ctl += ["let id1 = @d1s[id]", "let id2 = @d2s[id]", "let id3 = @d3s[id]", "let id4 = @d4s[id]",
                "let vr1 = v(b)-v(f2)", "let vr2 = v(f3)-v(c)", "let vr3 = v(d)", "let vr4 = v(b)",
                "let pd1 = id1*(v(f2)-v(b))", "let pd2 = id2*(v(c)-v(f3))", "let pd3 = id3*(0-v(d))", "let pd4 = id4*(0-v(b))"]
        for j in "1234":
            ctl += [f"meas tran d{j}avg AVG id{j} {win}", f"meas tran d{j}rms RMS id{j} {win}",
                    f"meas tran d{j}pk MAX id{j} {win}", f"meas tran d{j}vr MAX vr{j} {win}",
                    f"meas tran d{j}p AVG pd{j} {win}", f"meas tran d{j}pkall MAX id{j}", f"meas tran d{j}vrall MAX vr{j}"]
        rsn = M.RSNUB * (kw["L_max"] / M.L_MAX) * (F / 60.0) / math.sqrt(kw.get("snub_k", 1.0))
        for nd in ("a", "b", "c", "d", "f2", "f3", "x1", "x2"):
            ctl += [f"let ps_{nd} = v(sn_{nd})*v(sn_{nd})/{rsn:.6e}", f"let vc_{nd} = v({nd})-v(sn_{nd})",
                    f"meas tran sp_{nd} AVG ps_{nd} {win}", f"meas tran spk_{nd} MAX ps_{nd}",
                    f"meas tran vcmax_{nd} MAX vc_{nd}", f"meas tran vcmin_{nd} MIN vc_{nd}",
                    f"meas tran vnmax_{nd} MAX v({nd})", f"meas tran vnmin_{nd} MIN v({nd})"]
    if job.get("bypass_mF"):
        ctl += ["let vb1 = v(xb1)-v(d)", "let vb2 = v(xb2)-v(b)", f"let ib1 = (v(x1)-v(xb1))/{ESR_BYP:g}",
                f"meas tran vb1min MIN vb1 {win}", f"meas tran vb1max MAX vb1 {win}", f"meas tran vb1avg AVG vb1 {win}",
                f"meas tran ib1rms RMS ib1 {win}", "meas tran vb1allmin MIN vb1", "meas tran vb1allmax MAX vb1",
                "meas tran vb2allmin MIN vb2", "meas tran vb2allmax MAX vb2"]
    if k:
        nk = len(k.get("into", "a"))
        ctl += ["let ik = " + "+".join(f"abs(i(vkm{j}))" for j in range(nk)),
                "meas tran ikmax MAX ik", f"meas tran qk INTEG ik from=0 to={n * T * (1 - 1e-9):.6e}",
                "meas tran lbtall_max MAX ilb", "meas tran lbtall_min MIN ilb"]
        if k["kind"] == "cap":                                       # the capacitor's own voltage
            ctl += ["let vck = v(kp)", f"meas tran vckend FIND vck AT={n * T * (1 - 1e-9):.6e}",
                    "meas tran vckmin MIN vck", "meas tran vckmax MAX vck"]
    r = ngspice_meas(txt, ctl)
    retried = False
    if "_error" in r or r.get("t_last", 0.0) < 0.999 * n * T:
        # ngspice stopped early ("timestep too small" in a diode of the pump): once more with a looser reltol and half
        # the maxstep; the verdicts do not depend on such numerics [IR]
        txt2 = re.sub(r"reltol=\S+", "reltol=3e-5", txt)
        txt2 = re.sub(r"maxstep=(\S+)", lambda m: f"maxstep={0.5 * float(m.group(1)):.4e}", txt2)
        r = ngspice_meas(txt2, ctl)
        retried = True
    if "_error" in r:
        return dict(job=job, error=r["_error"])
    if r.get("t_last", 0.0) < 0.999 * n * T:                          # still stopped early: no verdict
        return dict(job=job, error=f"incomplete: the run stopped at {r.get('t_last', 0.0) / T:.1f} of {n} cycles")
    pk = [max(r.get(f"pa{c_}", 0.0), r.get(f"pb{c_}", 0.0)) for c_ in range(n)]
    z = [pk[c_ + 1] / pk[c_] for c_ in range(n - 1) if pk[c_] > 0]
    # ngspice prints names in lower case: cu_l1, mech_l1, cu_aht, ...
    P = {}
    for e in [e_[3:] for e_ in r if e_.startswith("e0_")]:
        if f"e1_{e}" in r:
            P[e] = (r[f"e1_{e}"] - r[f"e0_{e}"]) / (t1 - t0)
        elif f"e2_{e}" in r:                                         # the fallback, a little before the end
            P[e] = (r[f"e2_{e}"] - r[f"e0_{e}"]) / (t1 - T / 4000 - t0)
    P_mech = sum(v_ for k_, v_ in P.items() if k_.startswith("mech_"))
    P_cu_ut = P.get("cu_l1", 0.0) + P.get("cu_l2", 0.0)
    P_cu_fixed = sum(v_ for k_, v_ in P.items() if k_.startswith("cu_l")) - P_cu_ut
    P_ah = P.get("cu_aht", 0.0) + P.get("cu_ahb", 0.0)
    AT = lambda mx, mn: h["N"] * max(abs(mx), abs(mn))
    out = dict(job=job, kw=dict(psi_s=kw["psi_s"], seed_A=kw["seed"], tau_fixed=kw["tau_fixed"], L_max=kw["L_max"],
                                la=la, n_cyc=n), retried=retried,
               z_early=float(np.median(z[2:8])) if len(z) > 8 else None,
               AH_AT_pk_branch=h["N"] * r.get("i1max", 0.0), AH_AT_min_branch=h["N"] * r.get("i1min", 0.0),
               AHt_AT_max=AT(r.get("ahtmax", 0), r.get("ahtmin", 0)), AHt_I_mean_A=r.get("ahtavg"),
               AHb_AT_max=AT(r.get("ahbmax", 0), r.get("ahbmin", 0)), AHb_I_mean_A=r.get("ahbavg"),
               AHt_I_range_A=(r.get("ahtmin"), r.get("ahtmax")), AHt_I_whole_run_A=(r.get("ahtall_min"), r.get("ahtall_max")),
               P_belt_W=P_mech, P_cu_utron_W=P_cu_ut, P_cu_fixed_W=P_cu_fixed, P_AH_W=P_ah, P_snub_W=P.get("snub", 0.0),
               P_diode_W=P_mech - P_cu_ut - P_cu_fixed - P_ah - P.get("snub", 0.0), I1_rms_A=r.get("i1rms"))
    out["starts"] = out["AHt_AT_max"] > START_AT
    if job.get("F_Hz"):
        out["F_Hz"] = F
        out["runs"] = out["AHt_AT_max"] > RUN_AT
        out["pk_A"] = pk                                              # each cycle's branch peak
    for nm in ("la", "lb"):
        out[nm] = dict(I_max=r.get(f"{nm}max"), I_min=r.get(f"{nm}min"), I_mean=r.get(f"{nm}avg"), I_rms=r.get(f"{nm}rms"),
                       I_whole_run=(r.get(f"{nm}all_min"), r.get(f"{nm}all_max")))
    if job.get("duty"):
        out["diodes"] = {f"D{j}*": dict(I_avg_A=r.get(f"d{j}avg"), I_rms_A=r.get(f"d{j}rms"), I_pk_A=r.get(f"d{j}pk"),
                                        I_pk_whole_run_A=r.get(f"d{j}pkall"), VR_pk_V=r.get(f"d{j}vr"),
                                        VR_pk_whole_run_V=r.get(f"d{j}vrall"), P_W=r.get(f"d{j}p")) for j in "1234"}
        out["snubbers"] = {nd: dict(P_R_avg_W=r.get(f"sp_{nd}"), P_R_pk_W=r.get(f"spk_{nd}"),
                                    V_C_max_V=max(abs(r.get(f"vcmax_{nd}", 0)), abs(r.get(f"vcmin_{nd}", 0))),
                                    V_node_max_V=max(abs(r.get(f"vnmax_{nd}", 0)), abs(r.get(f"vnmin_{nd}", 0))))
                           for nd in ("a", "b", "c", "d", "f2", "f3", "x1", "x2")}
        out["snubber_R_C"] = (rsn, M.CSNUB * (M.L_MAX / kw["L_max"]) * (60.0 / F) ** 2 * kw.get("snub_k", 1.0))
    if job.get("bypass_mF"):
        out["bypass"] = dict(V_min=r.get("vb1min"), V_max=r.get("vb1max"), V_mean=r.get("vb1avg"), I_rms_A=r.get("ib1rms"),
                             V_whole_run=(min(r.get("vb1allmin", 0), r.get("vb2allmin", 0)),
                                          max(r.get("vb1allmax", 0), r.get("vb2allmax", 0))),
                             P_esr_pair_W=2 * ESR_BYP * r.get("ib1rms", 0.0) ** 2)
    if k:
        out["kick"] = dict(I_max_A=r.get("ikmax"), Q_C=r.get("qk"), V_end=r.get("vckend"),
                           V_range=(r.get("vckmin"), r.get("vckmax")))
        if k["kind"] == "cap":
            c = k["C_mF"] * 1e-3
            out["kick"]["E0_mJ"] = 0.5 * c * k["V0"] ** 2 * 1e3
            out["kick"]["E_out_mJ"] = 0.5 * c * (k["V0"] ** 2 - (r.get("vckend") or 0.0) ** 2) * 1e3
        else:
            out["kick"]["E_out_mJ"] = k["V0"] * abs(r.get("qk") or 0.0) * 1e3      # the cell's energy delivered
    return out


def restore_job(job):
    """run, then rescale Psi_s twice so the AH branch peak returns to the record's (as sim/pole_design.solve_real)."""
    target = job.pop("AT_target")
    runs = []
    psi = None
    for _ in range(3):
        q = mag_job(dict(job, psi_s=psi) if psi else dict(job))
        runs.append(q)
        if "error" in q or not q["AH_AT_pk_branch"]:
            break
        psi = q["kw"]["psi_s"] * target / q["AH_AT_pk_branch"]
    return runs


def run_any(job):
    return restore_job(dict(job)) if "AT_target" in job else mag_job(job)


# ---------------------------------------------------------------------------------------------------- electrostatic
def es_record():
    """the record's supply (sim/hub_rings_build_results.json record_supply's parameters) from the start, 280 cycles at
    10 000 steps per cycle, the last 8 cycles written: node voltages, the clamps' currents, the power integrators."""
    rs = load("rings")["record_supply"]
    kw = dict(opt=rs["opt"], n_cw=rs["n_cw"], n_cw_a=rs["n_cw_a"], c_core=rs["c_core"], c_cw=rs["c_cw"],
              r_leak=rs["r_leak"], a_ref=rs["a_ref"], n_cyc=rs["n_cyc"], steps=rs["steps"])
    txt, vecs, pk = CF.deck(**kw)
    T = 1.0 / CF.F
    n = kw["n_cyc"]
    txt = re.sub(r"tran (\S+) (\S+) uic", lambda m: f"tran {m.group(1)} {m.group(2)} {(n - 8) * T:.6e} uic", txt)
    with tempfile.TemporaryDirectory() as tdir:
        open(os.path.join(tdir, "x.cir"), "w").write(txt)
        subprocess.run(["ngspice", "-b", "x.cir"], capture_output=True, text=True, timeout=7200, cwd=tdir)
        raw = np.loadtxt(os.path.join(tdir, "out.dat"))
    t = raw[:, 0]
    c = {v: raw[:, 2 * j + 1] for j, v in enumerate(vecs)}
    return dict(rs=rs, kw=kw, t=t, c=c, pk=pk, vecs=vecs, T=T)


def es_analyse(E):
    """duties over the last 8 cycles. Diode currents by KCL at each node that holds exactly two diodes, one in and one
    out, never conducting together (ideal diodes) [OC]; capacitor currents C dV/dt [OC]."""
    keep = np.r_[True, np.diff(E["t"]) > 0]                          # ngspice repeats time points at breakpoints
    t, T = E["t"][keep], E["T"]
    c = {k_: v_[keep] for k_, v_ in E["c"].items()}
    dur = t[-1] - t[0]
    V = {k[2:-1]: c[k] for k in c if k.startswith("v(") and not k.startswith("v(e_")}
    V["0"] = np.zeros_like(t)

    def ddt(y):
        return np.gradient(y, t)

    def avg(y):
        return float(_trapz(y, t) / dur)

    def rms(y):
        return math.sqrt(max(0.0, avg(y * y)))

    Ca = CF.CA
    Cp = CF.CPAR
    ccw = E["kw"]["c_cw"]
    split = {}                                                        # node: (in-diode, out-diode, net current in)
    split["2"] = ("D4", "D1", Ca * ddt(V["2"] - V["1"]) + Cp * ddt(V["2"]))
    split["3"] = ("D3", "D2", Ca * ddt(V["3"] - V["4"]) + Cp * ddt(V["3"]))
    split["n1"] = ("Dpa1", "Dca1", ccw * ddt(V["n1"] - V["1"]) + ccw * ddt(V["n1"] - V["n2"]))
    split["n2"] = ("Dpa2", "Dca2", ccw * ddt(V["n2"] - V["n1"]))
    split["m1"] = ("Dc1", "Dp1", ccw * ddt(V["m1"] - V["4"]) + ccw * ddt(V["m1"] - V["m2"]))
    split["m2"] = ("Dc2", "Dp2", ccw * ddt(V["m2"] - V["m1"]))
    # V(cathode) - V(anode) of every diode (sim/core_field.py's netlist)
    vr = {"D1": -V["2"], "D2": -V["3"], "D3": V["3"] - V["1"], "D4": V["2"] - V["4"],
          "Dca1": -V["n1"], "Dpa1": V["n1"] - V["a1"], "Dca2": V["a1"] - V["n2"], "Dpa2": V["n2"] - V["ea"],
          "Dc1": V["m1"], "Dp1": V["b1"] - V["m1"], "Dc2": V["m2"] - V["b1"], "Dp2": V["eb"] - V["m2"]}
    diodes = {}
    for node, (din, dout, inet) in split.items():
        for nm, i in ((din, np.clip(inet, 0, None)), (dout, np.clip(-inet, 0, None))):
            diodes[nm] = dict(I_avg_uA=avg(i) * 1e6, I_rms_uA=rms(i) * 1e6, I_pk_mA=float(i.max()) * 1e3,
                              VR_pk_kV=float(vr[nm].max()) / 1e3, VR_rms_kV=rms(vr[nm]) / 1e3)
    caps = {"Ca": (V["1"], V["2"], Ca), "Cb": (V["4"], V["3"], Ca),
            "Coa1": (V["1"], V["n1"], ccw), "Csa1": (V["0"], V["a1"], ccw), "Coa2": (V["n1"], V["n2"], ccw),
            "Csa2": (V["a1"], V["ea"], ccw), "Co1": (V["4"], V["m1"], ccw), "Cs1": (V["b1"], V["0"], ccw),
            "Co2": (V["m1"], V["m2"], ccw), "Cs2": (V["eb"], V["b1"], ccw)}
    capd = {}
    for nm, (va, vb, cc) in caps.items():
        dv = va - vb
        capd[nm] = dict(C_pF=cc * 1e12, V_dc_kV=abs(avg(dv)) / 1e3, V_pk_kV=float(np.abs(dv).max()) / 1e3,
                        V_pp_V=float(dv.max() - dv.min()), I_rms_uA=rms(cc * ddt(dv)) * 1e6)
    clamps = {}
    for z, nd in (("Z1", "1"), ("Z4", "4")):
        i = c[f"i(V{z.lower()})"]
        on = i > 0.05 * i.max()
        clamps[z] = dict(I_pk_mA=float(i.max()) * 1e3, I_avg_uA=avg(i) * 1e6, I_rms_uA=rms(i) * 1e6,
                         P_W=avg(-V[nd] * i), E_cycle_mJ=avg(-V[nd] * i) / CF.F * 1e3,
                         conduction=float(np.sum(np.diff(t)[on[:-1]]) / dur), V_node_pk_kV=float(np.abs(V[nd]).max()) / 1e3)
    nodes = {k: dict(mean_kV=avg(v) / 1e3, min_kV=float(v.min()) / 1e3, max_kV=float(v.max()) / 1e3, rms_kV=rms(v) / 1e3)
             for k, v in V.items() if k not in ("0", "s")}
    pairs = {"1-2 (Ca)": V["1"] - V["2"], "4-3 (Cb)": V["4"] - V["3"], "1-4": V["1"] - V["4"],
             "ea-eb (the ring leads)": V["ea"] - V["eb"]}
    pair_st = {k: dict(pk_kV=float(np.abs(v).max()) / 1e3, rms_kV=rms(v) / 1e3, mean_kV=avg(v) / 1e3)
               for k, v in pairs.items()}
    P = {}
    for nd in E["pk"]:
        y = c[f"v(e_{nd})"]
        P[nd] = float((y[-1] - y[0]) / dur)
    # the instant of node 1's lowest point, and node 4's: the worst instant for a vane flashover on that side
    i1, i4 = int(np.argmin(V["1"])), int(np.argmin(V["4"]))
    at = {"node 1 lowest": dict({k: float(v[i1]) for k, v in V.items() if k != "0"}, t=float(t[i1])),
          "node 4 lowest": dict({k: float(v[i4]) for k, v in V.items() if k != "0"}, t=float(t[i4]))}
    return dict(diodes=diodes, caps=capd, clamps=clamps, nodes=nodes, pairs=pair_st, P_W=P, at=at)


def es_network(c_cw, t):
    """the rotor's electrostatic network of record (sim/core_field.py dc, the mirror chains) at time t: capacitors
    (a, b, C) and diodes (anode, cathode); s, the stator vanes, is REF through the bearing's 1 ohm [IR]."""
    w = 2 * math.pi * CF.F
    c1 = CF.CMIN + (CF.CMAX - CF.CMIN) * 0.5 * (1 + math.cos(w * t))
    c2 = CF.CMIN + (CF.CMAX - CF.CMIN) * 0.5 * (1 - math.cos(w * t))
    caps = [("1", "0", c1), ("4", "0", c2), ("1", "2", CF.CA), ("3", "4", CF.CA)] + \
           [(n_, "0", CF.CPAR) for n_ in "1234"] + \
           [("1", "n1", c_cw), ("a1", "0", c_cw), ("n1", "n2", c_cw), ("ea", "a1", c_cw),
            ("4", "m1", c_cw), ("b1", "0", c_cw), ("m1", "m2", c_cw), ("eb", "b1", c_cw),
            ("ea", "0", 3e-12), ("eb", "0", 3e-12), ("ea", "eb", 2e-12)]           # sim/core_field.py c_e, c_gap
    diodes = [("D1", "2", "0"), ("D2", "3", "0"), ("D3", "1", "3"), ("D4", "4", "2"),
              ("Z1 (forward)", "1", "0"), ("Z4 (forward)", "4", "0"),
              ("Dca1", "n1", "0"), ("Dpa1", "a1", "n1"), ("Dca2", "n2", "a1"), ("Dpa2", "ea", "n2"),
              ("Dc1", "0", "m1"), ("Dp1", "m1", "b1"), ("Dc2", "b1", "m2"), ("Dp2", "m2", "eb")]
    return caps, diodes


def settle(caps, diodes, v_before, fixed_after):
    """an arc forces some nodes to new voltages at once; the rest keep their charge, then every forward-biased ideal
    diode passes charge until it is at 0 V [OC: charge conservation; each equalisation of a diode at V_f dissipates
    1/2 dq V_f]. Returns each diode's first forward step, the charge it passed, the energy, and the final voltages."""
    names = sorted({n_ for a, b, _ in caps for n_ in (a, b)} | {n_ for _, a, b in diodes for n_ in (a, b)})
    fixed = dict(fixed_after, **{"0": 0.0})
    free = [n_ for n_ in names if n_ not in fixed]
    ix = {n_: i for i, n_ in enumerate(free)}
    N = len(free)
    Cm = np.zeros((N, N))
    for a, b, cv in caps:
        for p_, q_ in ((a, b), (b, a)):
            if p_ in ix:
                Cm[ix[p_], ix[p_]] += cv
                if q_ in ix:
                    Cm[ix[p_], ix[q_]] -= cv

    def charges(v):                                                   # charge on each free node's plates
        Q = np.zeros(N)
        for a, b, cv in caps:
            if a in ix:
                Q[ix[a]] += cv * (v[a] - v[b])
            if b in ix:
                Q[ix[b]] += cv * (v[b] - v[a])
        return Q

    def volts(Q):
        rhs = Q.copy()
        for a, b, cv in caps:
            if a in ix and b in fixed:
                rhs[ix[a]] += cv * fixed[b]
            if b in ix and a in fixed:
                rhs[ix[b]] += cv * fixed[a]
        x = np.linalg.solve(Cm, rhs)
        v = dict(fixed)
        v.update({n_: float(x[ix[n_]]) for n_ in free})
        return v

    Q = charges(v_before)
    v = volts(Q)
    Ci = np.linalg.inv(Cm)
    first = {}
    passed = {dio[0]: 0.0 for dio in diodes}
    energy = {dio[0]: 0.0 for dio in diodes}
    for _ in range(20000):
        fw = [(v[a] - v[b], nm, a, b) for nm, a, b in diodes]
        for f_, nm, a, b in fw:
            first.setdefault(nm, max(0.0, f_))
        f_, nm, a, b = max(fw)
        if f_ < 1.0:                                                  # within a volt: settled
            break
        ia, ib = ix.get(a), ix.get(b)
        k = (Ci[ia, ia] if ia is not None else 0.0) + (Ci[ib, ib] if ib is not None else 0.0) - \
            (2 * Ci[ia, ib] if ia is not None and ib is not None else 0.0)
        dq = f_ / k
        if ia is not None:
            Q[ia] -= dq
        if ib is not None:
            Q[ib] += dq
        passed[nm] += dq
        energy[nm] += 0.5 * dq * f_
        v = volts(Q)
    return dict(first_step_V=first, charge_C=passed, energy_J=energy, v_after=v)


def flashover(es, c_cw):
    """a vane flashover takes a pumping node to REF at its lowest point (the worst instant), the arc holding it there
    while the rest settles through ideal diodes [IR]. With a surge resistor R_s in a diode's path, its peak current is
    the first forward step over R_s and the path's energy goes into R_s (the arc's few ohms are small beside it) [IR]."""
    out = {}
    for side, nd, key in (("A: node 1 to REF", "1", "node 1 lowest"), ("B: node 4 to REF", "4", "node 4 lowest")):
        at = es["at"][key]
        caps, diodes = es_network(c_cw, at["t"])
        vb = {k_: v_ for k_, v_ in at.items() if k_ != "t"}
        vb["0"] = 0.0
        vb.setdefault("s", 0.0)
        st = settle(caps, diodes, vb, {nd: 0.0, "s": 0.0})
        rows = {}
        for nm, a, b in diodes:
            fs, q, e = st["first_step_V"][nm], st["charge_C"][nm], st["energy_J"][nm]
            if q <= 0 and fs <= 0:
                continue
            row = dict(first_step_kV=fs / 1e3, charge_uC=q * 1e6, energy_mJ=e * 1e3)
            if nm in ("D1", "D2", "D3", "D4"):
                row.update(I_pk_with_Rs_A=fs / R_SURGE, I2t_with_Rs_A2s=(fs / R_SURGE) ** 2 * (q / max(fs / R_SURGE, 1e-12)) / 2)
            else:
                row.update(I_pk_with_22k_A=fs / R_SURGE)
            rows[nm] = row
        out[side] = dict(node_before_kV=at[nd] / 1e3, t_in_cycle=(at["t"] * CF.F) % 1.0, diodes=rows,
                         rings_before_kV=(at["ea"] / 1e3, at["eb"] / 1e3),
                         rings_after_kV=(st["v_after"]["ea"] / 1e3, st["v_after"]["eb"] / 1e3),
                         smoothing_after_kV=(st["v_after"]["a1"] / 1e3, st["v_after"]["b1"] / 1e3))
    return out


# ==================================================================================================== 4. creepage
def clearance_case_a(u_kv):
    """IEC 60664-1 Table F.2 case A, interpolated log-log [IR as recalled]; above 100 kV extrapolated [RH]."""
    xs = np.log([p[0] for p in F2_CASE_A])
    ys = np.log([p[1] for p in F2_CASE_A])
    return float(np.exp(np.interp(math.log(u_kv), xs, ys, left=None, right=None)))


def creepage(u_rms_kv, group, pd=2):
    tab = CREEP_PD2 if pd == 2 else CREEP_PD3
    if group == "inorganic":
        return None
    return tab[group] * u_rms_kv                                     # mm; proportional above 1 kV [RH]


def ribbed(creep_mm, clear_mm, rib=5.0, pitch=8.0):
    """a ribbed standoff: height for the clearance, ribs of depth rib (mm) on a pitch (mm) to make up the creepage
    (each rib adds 2 x its depth; IEC 60664-1 counts ribs wider than X = 1 mm at PD2) [IR]."""
    h = float(math.ceil(max(clear_mm, 10.0)))
    n = max(0, math.ceil((creep_mm - h) / (2 * rib)))
    while n * pitch > h:                                             # the ribs must fit on the height
        h += pitch
        n = max(0, math.ceil((creep_mm - h) / (2 * rib)))
    return dict(height_mm=h, ribs=n, rib_depth_mm=rib, creepage_mm=h + 2 * n * rib)


def creep_table(es):
    nodes, pairs = es["nodes"], es["pairs"]
    items = [
        ("Ca plates: node 1 <-> node 2 (and Cb: 4 <-> 3)", pairs["1-2 (Ca)"]["rms_kV"], pairs["1-2 (Ca)"]["pk_kV"]),
        ("node 1 / 4 metal <-> REF (rotor vanes' rings on the sleeve, Ca node-1 plates, Z1 / Z4 top, D3 / D4, Coa1 / Co1)",
         max(nodes["1"]["rms_kV"], nodes["4"]["rms_kV"]), max(-nodes["1"]["min_kV"], -nodes["4"]["min_kV"])),
        ("node 2 / 3 metal <-> REF (Ca node-2 plates, D1 / D2, D4 / D3 ends)", max(nodes["2"]["rms_kV"], nodes["3"]["rms_kV"]),
         max(-nodes["2"]["min_kV"], -nodes["3"]["min_kV"])),
        ("node 1 <-> node 4 (only where side A meets side B)", pairs["1-4"]["rms_kV"], pairs["1-4"]["pk_kV"]),
        ("a clamp string, end to end (= node 1 / 4 <-> REF)", max(nodes["1"]["rms_kV"], nodes["4"]["rms_kV"]),
         max(es["clamps"]["Z1"]["V_node_pk_kV"], es["clamps"]["Z4"]["V_node_pk_kV"])),
        ("one chain stage: its diode / capacitor (7.5 kV)", es["diodes"]["Dc2"]["VR_rms_kV"],
         max(v["VR_pk_kV"] for k, v in es["diodes"].items() if k.startswith(("Dc", "Dp", "Dca", "Dpa")))),
        ("Co1: node 4 <-> m1 (13.2 kV DC)", es["caps"]["Co1"]["V_dc_kV"], es["caps"]["Co1"]["V_pk_kV"]),
        ("a ring's lead and the chain's top <-> REF (+-15 kV DC)", max(abs(nodes["ea"]["mean_kV"]), abs(nodes["eb"]["mean_kV"])),
         max(abs(nodes["ea"]["min_kV"]), abs(nodes["eb"]["max_kV"]))),
        ("ring A's lead <-> ring B's lead (keep apart)", pairs["ea-eb (the ring leads)"]["rms_kV"],
         pairs["ea-eb (the ring leads)"]["pk_kV"]),
    ]
    rows = []
    for nm, u_rms, u_pk in items:
        clr = clearance_case_a(CLR_MARGIN * u_pk)
        row = dict(interface=nm, U_rms_kV=u_rms, U_pk_kV=u_pk, clearance_mm=clr, solid_mm=u_pk / E_POT, creepage_mm={},
                   creepage_PD3_mm={}, design_creepage_mm={})
        for mat, (grp, _) in MATERIALS.items():
            cr = creepage(u_rms, grp)
            row["creepage_mm"][mat] = cr if cr is not None else clr
            row["creepage_PD3_mm"][mat] = creepage(u_rms, grp, pd=3) if cr is not None else clr
            row["design_creepage_mm"][mat] = (cr * DC_MARGIN) if cr is not None else clr
        row["ribbed_PTFE"] = ribbed(row["design_creepage_mm"]["PTFE"], clr)
        row["ribbed_G10"] = ribbed(row["design_creepage_mm"]["G10 / FR4"], clr, rib=6.0, pitch=8.0)
        rows.append(row)
    return rows


# ==================================================================================================== jobs
def jobs_for(ch):
    J = {}
    J["base"] = dict(duty=True)
    J["byp"] = dict(duty=True, bypass_mF=C_BYP_MF)
    for f in (0.20, 0.25, 0.30):                                     # the seed of the other sign
        J[f"rev{f:.2f}"] = dict(seed_frac=-f)
        J[f"rev{f:.2f}_byp"] = dict(bypass_mF=C_BYP_MF, seed_frac=-f)
    for f in SEED_FRACS:
        J[f"seed{f:.2f}"] = dict(seed_frac=f, n_cyc=40)
        J[f"seed{f:.2f}_byp"] = dict(seed_frac=f, n_cyc=40, bypass_mF=C_BYP_MF)
    la = RP.LA_RATIO * load("op")["designs"][PICK]["best"]["L_group_H"]

    def kick(kind, c_uF, V, r_cell, ton, pol, ph, into="a"):
        kd = dict(kind=kind, V0=V, pol=pol, phase=ph, into=into, label=None)
        if kind == "cap":
            kd.update(C_mF=c_uF * 1e-3, t_on=t_on_cap(c_uF, la))
        else:
            kd.update(R=r_cell, t_on=ton)
        return dict(seed_frac=0.0, n_cyc=40, bypass_mF=C_BYP_MF, kick=kd)
    for nm, kind, c_uF, V, r_cell, ton in KICKS:
        for ph in KICK_PHASES:
            J[f"kick|{nm}|+|{ph:g}"] = kick(kind, c_uF, V, r_cell, ton, 1, ph)
    for ph in (1.0, 1.5):                                            # the other sign, and both nodes at once
        J[f"kick|{KICKS[1][0]}|-|{ph:g}"] = kick(*KICKS[1][1:], -1, ph)
        J[f"kick|{KICKS[1][0]}|+ac|{ph:g}"] = kick(*KICKS[1][1:], 1, ph, into="ac")
    for fam, c_uF, volts in KICK_E_SWEEP:                            # how little energy a fast dump needs
        for V in volts:
            for ph in (1.0, 1.5):
                J[f"kickE|{fam}|{V:g}|{ph:g}"] = kick("cap", c_uF, V, None, None, 1, ph)
    J["kick_nobyp"] = dict(kick(*KICKS[1][1:], 1, 1.0), bypass_mF=0.0)
    si = {"D1s": "si", "D2s": "si", "D3s": "si", "D4s": "si"}
    mix = {"D1s": "si", "D2s": "si", "D3s": "sch", "D4s": "sch"}
    sch = {"D1s": "sch200", "D2s": "sch200", "D3s": "sch", "D4s": "sch"}
    J["vf_si"] = dict(diodes=si, duty=True)
    J["vf_mix"] = dict(diodes=mix, duty=True)
    J["vf_sch"] = dict(diodes=sch, duty=True)
    for f in (0.20, 0.25, 0.30, 0.40):
        J[f"vf_si_seed{f:.2f}"] = dict(diodes=si, seed_frac=f, n_cyc=40)
        J[f"vf_mix_seed{f:.2f}"] = dict(diodes=mix, seed_frac=f, n_cyc=40)
    for f in (0.14, 0.16, 0.20, 0.25):
        J[f"vf_sch_seed{f:.2f}"] = dict(diodes=sch, seed_frac=f, n_cyc=40)
    for kc in (KICKS[1], KICKS[3], KICKS[4]):                         # the capacitor kicks with real diodes
        for nm, dm in (("si", si), ("mix", mix), ("sch", sch)):
            for ph in KICK_PHASES:
                J[f"kickD|{kc[0]}|{nm}|{ph:g}"] = dict(kick(*kc[1:], 1, ph), diodes=dm)
    k4 = KICKS[3][1:]
    for F in SPEED_K4_HZ:                                            # the kick below full speed
        for ph in (1.0, 1.5):
            J[f"speed|K4|rec|{F:g}|{ph:g}"] = dict(kick(*k4, 1, ph), F_Hz=F, n_cyc=N_CYC_SPEED)
    for dnm, Fs in SPEED_K4_DIODES:
        for F in Fs:
            for ph in (1.0, 1.5):
                J[f"speed|K4|{dnm}|{F:g}|{ph:g}"] = dict(kick(*k4, 1, ph), F_Hz=F, n_cyc=N_CYC_SPEED,
                                                         diodes=dict(si=si, sch=sch)[dnm])
    f_rec = load("op")["designs"][PICK]["best"]["kick_frac"]
    for F in SPEED_SEED_HZ:                                          # the record's seed below full speed
        J[f"speed|seed|rec|{F:g}|0"] = dict(seed_frac=f_rec, n_cyc=N_CYC_SPEED, bypass_mF=C_BYP_MF, F_Hz=F)
    for F in SPEED_HOLD_HZ:                                          # a large seed: does a running pump hold?
        J[f"speed|hold|rec|{F:g}|0"] = dict(seed_frac=HOLD_FRAC, n_cyc=N_CYC_SPEED, bypass_mF=C_BYP_MF, F_Hz=F)
    at_rec = load("duty")["tau_sweep"][-1]["AH_AT_pk"]
    for nm in ("chosen", "compact"):
        tau = ch["duty"]["L_H"] / ch[nm]["R20_ohm"]
        J[f"tau_{nm}"] = dict(tau_fixed=tau, AT_target=at_rec)
    return J


# ==================================================================================================== assemble
def kick_seed_energy(base_kw, frac):
    """what sim/pole_design.py's seed is [OC]: the deck starts L1, L2, the AH pair, La and Lb at i0 = frac Psi_s / L_max
    (sim/magnetic_doubler.py deck); the co-energy at t = 0, L1 / L2 with the saturation law."""
    kw = RP._kw(RP.TAU_FIXED)
    a = M._coeffs(kw)
    Lmax, psi_s = kw["L_max"], kw["psi_s"]
    lp = M.R_PAR * Lmax
    l1 = Lmax * sum(a) + lp
    l2 = Lmax * sum(ak * (-1) ** k for k, ak in enumerate(a)) + lp
    la = RP.LA_RATIO * Lmax
    i0 = frac * psi_s / Lmax

    def w_sat(L):
        psi = i0 * L
        return psi ** 2 / (2 * L) + psi ** 8 / (8 * L * psi_s ** 6)
    w = w_sat(l1) + w_sat(l2) + kw["ah_custom"]["L"] * i0 ** 2 + la * i0 ** 2
    return dict(frac=frac, i0_A=i0, E_seed_mJ=w * 1e3, E_L1_mJ=w_sat(l1) * 1e3, L1_H=l1, L2_H=l2, La_H=la,
                E_old_basis_mJ=0.5 * Lmax * (frac * base_kw["I_pk"]) ** 2 * 1e3)


def threshold(R, prefix, fracs, suffix=""):
    rows = [(f, R.get(f"{prefix}{f:.2f}{suffix}")) for f in fracs]
    table = [dict(frac=f, starts=None, error=q.get("error")) if "error" in q else
             dict(frac=f, starts=q["starts"], AH_AT=q["AHt_AT_max"], retried=q.get("retried")) for f, q in rows if q]
    starts = [r_["frac"] for r_ in table if r_["starts"] is True]
    return dict(table=table, min_start=min(starts) if starts else None,
                max_no_start=max([r_["frac"] for r_ in table if r_["starts"] is False], default=None))


def ratings(mag, magb, es, ch, cusp22, Z, fl, kick=None):
    rows = []
    D = mag["diodes"]
    Db = magb["diodes"]
    for j, part in (("1", "D1*"), ("2", "D2*"), ("3", "D3*"), ("4", "D4*")):
        d0, d1 = D[f"D{j}*"], Db[f"D{j}*"]
        vr = max(d0["VR_pk_V"], d1["VR_pk_V"], d0["VR_pk_whole_run_V"], d1["VR_pk_whole_run_V"])
        ipk = max(d0["I_pk_A"], d1["I_pk_A"], d0["I_pk_whole_run_A"], d1["I_pk_whole_run_A"])
        iav = max(d0["I_avg_A"], d1["I_avg_A"])
        p = max(d0["P_W"], d1["P_W"])
        v_sch = 150.0 if j in "34" else 200.0
        rows.append(dict(part=part, qty=1, group="magnetic pump (rotor)",
                         duty=f"VR {vr:.0f} V pk (start-up included); IF {iav:.2f} A avg, "
                              f"{max(d0['I_rms_A'], d1['I_rms_A']):.2f} A rms, {ipk:.2f} A pk; {p:.2f} W at the model's 0.54 V",
                         rating=(f"Schottky rectifier, {v_sch:.0f} V" + (" (100 V at least)" if j in "34" else "") +
                                 ", 3 A avg at least (5 A preferred); a 400 V, 3 A Si rectifier of the 1N5404 class "
                                 "(VRRM 400 V, IF(AV) 3 A, IFSM 200 A) also holds the duty but costs gain (vf_sensitivity)"),
                         margin=f"VR x{v_sch / vr:.1f} (Schottky) / x{400.0 / vr:.1f} (1N5404); IF(AV) x{3.0 / iav:.1f} at 3 A",
                         VR_pk_V=vr, I_pk_A=ipk, I_avg_A=iav, P_W=p))
    for nm in ("D1", "D2", "D3", "D4"):
        dio = es["diodes"][nm]
        n_st = 1 if dio["VR_pk_kV"] * 2 <= STICK_KV else 2
        rows.append(dict(part=nm, qty=1, group="electrostatic pump (rotor)",
                         duty=f"VR {dio['VR_pk_kV']:.2f} kV pk; IF {dio['I_avg_uA']:.0f} uA avg, {dio['I_pk_mA']:.2f} mA pk",
                         rating=f"{n_st} x {STICK_KV:.0f} kV HV rectifier stick, avalanche, 5 mA class, + {R_SURGE / 1e3:.0f} kOhm surge resistor",
                         margin=f"VR x{n_st * STICK_KV / dio['VR_pk_kV']:.1f} (guidance x2); IF x{5e3 / dio['I_avg_uA']:.0f}",
                         VR_pk_kV=dio["VR_pk_kV"], sticks=n_st))
    chain = [k for k in es["diodes"] if k.startswith(("Dc", "Dp"))]
    vr_c = max(es["diodes"][k]["VR_pk_kV"] for k in chain)
    i_c = max(es["diodes"][k]["I_pk_mA"] for k in chain)
    rows.append(dict(part="chain diodes Dc1 Dc2 Dp1 Dp2 Dca1 Dca2 Dpa1 Dpa2", qty=8, group="rings' supply (rotor)",
                     duty=f"VR {vr_c:.2f} kV pk each; IF {max(es['diodes'][k]['I_avg_uA'] for k in chain):.2f} uA avg "
                          f"(the rings' leakage), {i_c:.3f} mA pk",
                     rating=f"1 x {STICK_KV:.0f} kV stick each, avalanche, selected for IR <= 25 nA at 7.5 kV, 25 C",
                     margin=f"VR x{STICK_KV / vr_c:.1f}; IR: 7.5 kV / 25 nA = 3e11 ohm per diode, the ledger's per stage",
                     VR_pk_kV=vr_c))
    zc = es["clamps"]
    p_dev = max(zc["Z1"]["P_W"], zc["Z4"]["P_W"]) / Z_N
    rows.append(dict(part="Z1 / Z4 clamp strings", qty=2, group="electrostatic pump (rotor)",
                     duty=f"BV = V_op {Z['V_op_kV']:.2f} kV; {max(zc['Z1']['P_W'], zc['Z4']['P_W']):.2f} W, "
                          f"{max(zc['Z1']['I_pk_mA'], zc['Z4']['I_pk_mA']):.2f} mA pk, {zc['Z1']['I_avg_uA']:.0f} uA avg",
                     rating=f"{Z_N} x {Z_V:.0f} V avalanche diodes per string: TVS 190-210 V at 1 mA (1.5KE200A class) or "
                            f"5 W Zener 190-210 V (1N5388B class); one lot, BV-sorted",
                     margin=f"{p_dev * 1e3:.1f} mW per device against >= 1.5 W (x{1.5 / p_dev:.0f}); 0.95 mA against "
                            f"~25 mA (5 W / 200 V)",
                     P_per_device_W=p_dev, BV_string_kV=Z["BV_kV"], BV_band_kV=Z["BV_worst_kV"]))
    caps = es["caps"]
    vmax = max(caps[k]["V_dc_kV"] for k in caps if k.startswith(("Co", "Cs")))
    rows.append(dict(part="chain capacitors Co1 Co2 Cs1 Cs2 Coa1 Coa2 Csa1 Csa2", qty=8, group="rings' supply (rotor)",
                     duty="DC " + ", ".join(f"{k} {caps[k]['V_dc_kV']:.1f}" for k in caps if k.startswith(("Co", "Cs"))) +
                          f" kV; ripple <= {max(caps[k]['V_pp_V'] for k in caps if k.startswith(('Co', 'Cs'))):.0f} V p-p; "
                          f"<= {max(caps[k]['I_rms_uA'] for k in caps if k.startswith(('Co', 'Cs'))):.0f} uA rms",
                     rating=f"100 pF +-10 %, {C_CHAIN_KV:.0f} kV DC, HV ceramic class 1 (N750-N4700) or PP / PTFE film; "
                            "IR >= 1e11 ohm guaranteed (>= 1e12 typical), PD-free at 1.25 x",
                     margin=f"x{C_CHAIN_KV / vmax:.1f} on Co1's {vmax:.1f} kV; x{C_CHAIN_KV / 7.5:.1f} on 7.5 kV",
                     V_dc_max_kV=vmax))
    sn = mag["snubbers"]
    snb = magb["snubbers"]
    rsn, csn = mag["snubber_R_C"]
    vc = max(max(v["V_C_max_V"] for v in sn.values()), max(v["V_C_max_V"] for v in snb.values()))
    pr = max(max(v["P_R_avg_W"] for v in sn.values()), max(v["P_R_avg_W"] for v in snb.values()))
    prk = max(max(v["P_R_pk_W"] for v in sn.values()), max(v["P_R_pk_W"] for v in snb.values()))
    rows.append(dict(part="node snubbers (RC to REF)", qty=8, group="magnetic pump (rotor)",
                     duty=f"C {csn * 1e9:.1f} nF at <= {vc:.0f} V; R {rsn:.0f} ohm: {pr * 1e3:.2f} mW avg, {prk:.1f} W pk",
                     rating="22 nF +-10 % PP film, 250 V DC, pulse-rated; 240 ohm (E24), 0.5 W, pulse-rated thick-film or "
                            "carbon-composition, non-inductive",
                     margin=f"C x{250.0 / vc:.1f} on voltage; R x{0.5 / pr:.0f} on average power",
                     V_C_max_V=vc, P_R_avg_W=pr, P_R_pk_W=prk))
    by = magb["bypass"]
    rows.append(dict(part="AH bypass (if used; PROPOSED)", qty=2, group="AH (rotor, beside the hub)",
                     duty=f"{C_BYP_MF:.0f} mF; {by['V_min']:+.2f} to {by['V_max']:+.2f} V across it (nodes d / b positive); "
                          f"{by['I_rms_A']:.2f} A rms at 120 Hz; at most {1e3 * (kick or {}).get('byp_worst_V', 0.0):.1f} mV the "
                          "wrong way in any run (start-ups, reversed seeds and kicks included); "
                          f"{1e3 * by['P_esr_pair_W']:.1f} mW for the pair at 10 mohm",
                     rating="22 mF, 6.3-10 V aluminium electrolytic, 105 C, ripple >= 2 A rms at 120 Hz, ESR <= 20 mohm; "
                            "polarised parts + to nodes d / b (the diodes set the sign, whatever the kick's)",
                     margin=f"V x{6.3 / max(abs(by['V_min']), abs(by['V_max'])):.0f}; ripple x{2.0 / by['I_rms_A']:.1f}",
                     V_max_V=by["V_max"], I_rms_A=by["I_rms_A"]))
    d_es = es["diodes"]
    p_r = max(d_es[k]["I_rms_uA"] for k in ("D1", "D2", "D3", "D4")) ** 2 * 1e-12 * R_SURGE
    pump = [r_ for s_ in fl.values() for nm, r_ in s_["diodes"].items() if nm in ("D1", "D2", "D3", "D4")]
    e_fl = max(r_["energy_mJ"] for r_ in pump)
    i_fl = max(r_["I_pk_with_Rs_A"] for r_ in pump)
    v_fl = max(r_["first_step_kV"] for r_ in pump)
    rows.append(dict(part="surge resistors (one per D1-D4)", qty=4, group="electrostatic pump (rotor)",
                     duty=f"normal: {p_r * 1e3:.2f} mW; a vane flashover: up to {v_fl:.1f} kV across, {i_fl:.2f} A pk, "
                          f"{e_fl:.1f} mJ, tau {R_SURGE * CF.CA * 1e6:.0f} us",
                     rating=f"{R_SURGE / 1e3:.0f} kOhm +-5 %, >= 15 kV working across the body, >= 1 W, >= 0.1 J single pulse "
                            "(an HV thick-film resistor, or 6 x 3.9 kOhm 0.5 W metal-glaze parts of >= 2.5 kV each in series)",
                     margin=f"voltage x{15.0 / v_fl:.1f}; pulse energy x{100.0 / e_fl:.0f}; power x{1.0 / p_r:.0f}",
                     V_pulse_kV=v_fl, E_pulse_mJ=e_fl))
    ch_fl = [r_ for s_ in fl.values() for nm, r_ in s_["diodes"].items() if nm.startswith(("Dc", "Dp", "Dca", "Dpa"))]
    rows.append(dict(part="chain-input resistors (in series with Coa1 / Co1; added here)", qty=2,
                     group="rings' supply (rotor)",
                     duty=f"a vane flashover puts up to {max(r_['first_step_kV'] for r_ in ch_fl):.1f} kV forward across "
                          "the chains' first diodes, limited only by the arc and the wiring",
                     rating=f"the surge resistors' part: {R_SURGE / 1e3:.0f} kOhm, >= 15 kV across the body, >= 0.1 J",
                     margin=f"{max(r_['I_pk_with_22k_A'] for r_ in ch_fl):.2f} A pk; R C {R_SURGE * 1e-10 * 1e6:.1f} us, "
                            "no effect at 120 Hz"))
    if kick:
        k = kick["candidates"][kick["recommended"]]
        thr = kick["thresholds"]
        rows.append(dict(part="start kick (PROPOSED)", qty=1, group="magnetic pump (rotor)",
                         duty=f"the seed starts it from {100 * thr['no_bypass']['min_start']:.0f} % of Psi_s "
                              f"({thr['no_bypass']['E_seed_mJ_at_min_start']:.1f} mJ seeded; "
                              f"{100 * thr['si_diodes']['min_start']:.0f} % with 1N540x-class diodes); "
                              "a fast capacitor dump into La from 8 mJ stored (sim)",
                         rating=f"{kick['recommended']}: {k['E0_mJ']:.0f} mJ, {k['I_pk_A']:.2f} A pk, a {k['t_dump_ms']:.0f} ms dump "
                                "through an SCR (>= 400 V, >= 1 A) into node a (+), the gate pulsed by a reed switch and "
                                "an outside magnet at speed; the capacitor bipolar (it swings to "
                                f"{k['V_cap_range'][0]:.1f} V after the dump)"
                                + (f"; fired at full speed, never below {kick['speed_from_rpm']:.0f} rpm relative (every "
                                   "phase tried starts from there)" if kick.get("speed_from_rpm") else ""),
                         margin=f"x{k['E0_mJ'] / 8.0:.1f} on 8 mJ; starts at all 4 phases with every diode set"))
    c = ch["chosen"]
    rows.append(dict(part="La / Lb chokes", qty=2, group="magnetic pump (rotor)",
                     duty=f"{ch['duty']['L_H']:.3f} H; {ch['duty']['I_min_A']:.2f}-{ch['duty']['I_pk_A']:.2f} A "
                          f"({ch['duty']['I_rms_A']:.2f} A rms); <= {ch['duty']['V_pk_V']:.0f} V; the whole run's peak "
                          f"{max(abs(x) for q_ in (mag, magb) for x in q_['la']['I_whole_run'] + q_['lb']['I_whole_run'] if x is not None):.2f} A "
                          "(with the bypass)",
                     rating=f"{c['core']} x {c['stack_mm']:.0f} mm, {c['turns']} t of {c['wire_mm']:.2f} mm grade 2, "
                            f"gap {c['gap_total_mm']:.3f} mm total ({c['spacer_mm']:.3f} mm spacer), R20 {c['R20_ohm']:.3f} ohm",
                     margin=f"B {c['B_pk_T']:.2f} T at {ch['duty']['I_pk_A']:.2f} A ("
                            f"{c['B_pk_T'] * magb['la']['I_min'] / -ch['duty']['I_pk_A']:.2f} T with the bypass); the knee "
                            f"({B_KNEE} T) at {c['I_knee_A']:.2f} A (x{c['I_knee_A'] / ch['duty']['I_pk_A']:.2f})"))
    return rows


def clamp_string(V_op_kV):
    bv = Z_N * Z_V / 1e3
    sig = Z_TOL / math.sqrt(3) / math.sqrt(Z_N)                     # uniform +-5 % parts, independent [IR]
    return dict(N=Z_N, V_Z=Z_V, BV_kV=bv, V_op_kV=V_op_kV, step_per_part_pc=100.0 / Z_N,
                BV_worst_kV=(bv * (1 - Z_TOL), bv * (1 + Z_TOL)), BV_sigma_kV=bv * sig,
                TC_V_per_K=bv * 1e3 * Z_TC, dV_for_25K_kV=bv * Z_TC * 25.0,
                note="series string: one current, no sharing; avalanche parts take any voltage imbalance below BV without "
                     "grading [OC/IR]")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--procs", type=int, default=4)
    ap.add_argument("--cache", help="a pickle of the raw ngspice results: written after the runs, read instead of them "
                                    "if it exists (to rework the analysis only)")
    args = ap.parse_args()
    duty_rec = load("duty")
    op = load("op")["designs"][PICK]["best"]
    cusp = load("cusp")
    cusp22 = [r for r in cusp["rows"] if r["C_byp_mF"] == C_BYP_MF][0]
    core = load("core")
    hub = load("hub")
    ch = chokes(duty_rec)
    J = jobs_for(ch)
    print(f"La / Lb: chosen {ch['chosen']['core']} x {ch['chosen']['stack_mm']:.0f} (R20 {ch['chosen']['R20_ohm']:.3f} ohm, "
          f"{ch['chosen']['m_kg']:.2f} kg); compact {ch['compact']['core']} x {ch['compact']['stack_mm']:.0f} "
          f"(R20 {ch['compact']['R20_ohm']:.3f} ohm, {ch['compact']['m_kg']:.2f} kg); {len(J)} magnetic runs + the "
          "electrostatic record", flush=True)
    R, E = ({}, None)
    if args.cache and os.path.exists(args.cache):                    # reuse what an earlier run left [dev aid]
        R, E = pickle.load(open(args.cache, "rb"))
        R = {k_: v_ for k_, v_ in R.items() if k_ in J}
    names = [k_ for k_ in J if k_ not in R]
    with Pool(args.procs) as pool:
        es_async = pool.apply_async(es_record) if E is None else None
        res = pool.map(run_any, [J[k_] for k_ in names], chunksize=1)
        if es_async is not None:
            E = es_async.get()
    R.update(dict(zip(names, res)))
    if args.cache:
        pickle.dump((R, E), open(args.cache, "wb"))
    bad = [k for k, v in R.items() if isinstance(v, dict) and "error" in v]
    if bad:
        print("ngspice errors:", bad, flush=True)
    es = es_analyse(E)
    fl = flashover(es, E["kw"]["c_cw"])
    Z = clamp_string(core["design"]["V_op_kV"])
    base, byp = R["base"], R["byp"]
    # ---- the kick
    seed_rec = kick_seed_energy(op, op.get("kick_frac", 0.2))
    thr = dict(no_bypass=threshold(R, "seed", SEED_FRACS), bypass=threshold(R, "seed", SEED_FRACS, "_byp"),
               si_diodes=threshold(R, "vf_si_seed", (0.20, 0.25, 0.30, 0.40)),
               si_schottky=threshold(R, "vf_mix_seed", (0.20, 0.25, 0.30, 0.40)),
               all_schottky=threshold(R, "vf_sch_seed", (0.14, 0.16, 0.20, 0.25)))
    for k_, v_ in thr.items():
        v_["E_seed_mJ_at_min_start"] = kick_seed_energy(op, v_["min_start"])["E_seed_mJ"] if v_["min_start"] else None
    kicks = []
    for k_, q in R.items():
        if k_.startswith("kickD|"):
            continue
        if k_.startswith("kick") and "error" in q:
            parts = k_.split("|")
            kk = q["job"]["kick"]
            kicks.append(dict(name=k_, candidate=parts[1] if len(parts) > 1 else "K2 (no bypass)", error=q["error"],
                              starts=None, into=kk["into"], phase_cycles=kk["phase"],
                              polarity="+ (the deck's sign)" if kk["pol"] > 0 else "-"))
        elif k_.startswith("kick"):
            kk = q["job"]["kick"]
            parts = k_.split("|")
            kicks.append(dict(name=k_, candidate=parts[1] if len(parts) > 1 else "K2 (no bypass)", kind=kk["kind"], retried=q["retried"],
                              C_uF=kk["C_mF"] * 1e3 if kk.get("C_mF") else None, V0=kk["V0"], into=kk["into"],
                              polarity="+ (the deck's sign)" if kk["pol"] > 0 else "-", phase_cycles=kk["phase"],
                              t_on_ms=kk["t_on"] * 1e3, bypass=bool(q["job"].get("bypass_mF")), starts=q["starts"],
                              AH_AT=q["AHt_AT_max"], AH_I_mean_A=q["AHt_I_mean_A"], La_whole_run_A=q["la"]["I_whole_run"],
                              Lb_whole_run_A=q["lb"]["I_whole_run"], **q["kick"],
                              bypass_V_whole_run=q.get("bypass", {}).get("V_whole_run")))
    cand = {}
    for nm, kind, c_uF, V, r_cell, ton in KICKS:
        rows_ = [x for x in kicks if x["candidate"] == nm and x["polarity"].startswith("+") and x["into"] == "a"
                 and x["name"].startswith("kick|")]
        E0 = 0.5 * c_uF * 1e-6 * V ** 2 * 1e3 if kind == "cap" else None
        ok_ = [x for x in rows_ if x["starts"] is not None]
        cand[nm] = dict(kind=kind, C_uF=c_uF, V=V, E0_mJ=E0, t_dump_ms=(t_on_cap(c_uF, RP.LA_RATIO * op["L_group_H"]) * 1e3
                                                                        if kind == "cap" else ton * 1e3),
                        phases_run=[x["phase_cycles"] for x in rows_],
                        phases_started=[x["phase_cycles"] for x in rows_ if x["starts"]],
                        phases_no_verdict=[x["phase_cycles"] for x in rows_ if x["starts"] is None],
                        all_phases_start=bool(rows_) and all(x["starts"] is True for x in rows_),
                        I_pk_A=max((x["I_max_A"] or 0.0) for x in ok_) if ok_ else None,
                        E_out_mJ=max((x["E_out_mJ"] or 0.0) for x in ok_) if ok_ else None,
                        V_cap_range=((min(x["V_range"][0] for x in ok_), max(x["V_range"][1] for x in ok_))
                                     if ok_ and kind == "cap" else None),
                        bypass_V_whole_run=(min(x["bypass_V_whole_run"][0] for x in ok_),
                                            max(x["bypass_V_whole_run"][1] for x in ok_)) if ok_ else None)
    esweep = {}
    for fam, c_uF, volts in KICK_E_SWEEP:
        for V in volts:
            rows_ = [x for x in kicks if x["name"].startswith(f"kickE|{fam}|{V:g}|")]
            esweep[f"{fam} at {V:g} V"] = dict(E0_mJ=0.5 * c_uF * 1e-6 * V ** 2 * 1e3,
                                               starts={f"{x['phase_cycles']:g}": x["starts"] for x in rows_})
    always = [nm for nm, v in cand.items() if v["all_phases_start"] and v["kind"] == "cap"]
    kick_diodes = {}
    for k_, q in R.items():
        if not k_.startswith("kickD|"):
            continue
        _, cnm, dnm, ph = k_.split("|")
        row = kick_diodes.setdefault(cnm, {}).setdefault(dnm, dict(phases_started=[], phases_run=[], no_verdict=[]))
        row["phases_run"].append(float(ph))
        if "error" in q:
            row["no_verdict"].append(float(ph))
        elif q["starts"]:
            row["phases_started"].append(float(ph))
    robust = [nm for nm in always if nm in kick_diodes and
              all(len(v_["phases_started"]) == len(v_["phases_run"]) == len(KICK_PHASES) for v_ in kick_diodes[nm].values())]
    # the recommendation [IR]: of the capacitor kicks that start at every phase with every diode set, the one a primary
    # cell charges directly (no charging port, no converter); else the first that does
    rec = next((nm for nm in robust if "cell" in nm), robust[0] if robust else (always[0] if always else None))
    others = {x["name"]: dict(starts=x["starts"], error=x.get("error"), AH_AT=x.get("AH_AT"), V_range=x.get("V_range"),
                              La_whole_run_A=x.get("La_whole_run_A"), bypass_V_whole_run=x.get("bypass_V_whole_run"))
              for x in kicks if "|-|" in x["name"] or "|+ac|" in x["name"] or x["name"] == "kick_nobyp"}
    rev = {k_[3:]: R[k_] for k_ in R if k_.startswith("rev")}
    rev_sum = {k_: (dict(starts=None, error=v["error"]) if "error" in v else
                    dict(starts=v["starts"], AH_AT=v["AHt_AT_max"], AHt_I_mean_A=v["AHt_I_mean_A"],
                         AHt_I_whole_run_A=v["AHt_I_whole_run_A"], retried=v["retried"],
                         bypass_V_whole_run=v.get("bypass", {}).get("V_whole_run"))) for k_, v in rev.items()}
    tau_runs = {nm: R[f"tau_{nm}"] for nm in ("chosen", "compact")}
    tau_sum = {}
    for nm, runs in tau_runs.items():
        held, fin = runs[0], runs[-1]
        tau_sum[nm] = dict(tau_fixed_s=held["kw"]["tau_fixed"],
                           psi_held=dict(z_early=held["z_early"], AH_AT_pk=held["AH_AT_pk_branch"], P_belt_W=held["P_belt_W"],
                                         P_cu_fixed_W=held["P_cu_fixed_W"]),
                           AH_restored=dict(psi_s=fin["kw"]["psi_s"], z_early=fin["z_early"], AH_AT_pk=fin["AH_AT_pk_branch"],
                                            P_belt_W=fin["P_belt_W"], P_cu_fixed_W=fin["P_cu_fixed_W"],
                                            P_cu_utron_W=fin["P_cu_utron_W"], P_AH_W=fin["P_AH_W"], P_diode_W=fin["P_diode_W"]))
    vf = {}
    for nm in ("base", "vf_si", "vf_mix", "vf_sch"):
        q = R[nm]
        vf[nm] = dict(z_early=q["z_early"], AH_AT_pk=q["AH_AT_pk_branch"], P_belt_W=q["P_belt_W"], P_diode_W=q["P_diode_W"],
                      P_diodes_direct_W=sum(dio["P_W"] for dio in q["diodes"].values()))
    byp_worst = max(q["bypass"]["V_whole_run"][1] for q in R.values() if isinstance(q, dict) and "bypass" in q)
    # ---- below full speed
    f_pick, rpm_pick = RP.pick()[2], op["rpm"]
    sp_rows = []
    for k_, q in R.items():
        if not k_.startswith("speed|"):
            continue
        _, what, dnm, F_, ph = k_.split("|")
        row = dict(what=what, diodes=dnm, F_Hz=float(F_), rpm_relative=rpm_pick * float(F_) / f_pick,
                   phase_cycles=float(ph) if what == "K4" else None, n_cyc=N_CYC_SPEED)
        if "error" in q:
            row.update(runs=None, error=q["error"])
        else:
            row.update(runs=q["runs"], AH_AT=q["AHt_AT_max"], z_early=q["z_early"], retried=q["retried"],
                       pk_A_every_8_cycles=q["pk_A"][::8], P_belt_W=q["P_belt_W"] if q["runs"] else None)
        sp_rows.append(row)
    for dnm, prefix in (("rec", f"kick|{KICKS[3][0]}|+|"), ("si", f"kickD|{KICKS[3][0]}|si|"),
                        ("sch", f"kickD|{KICKS[3][0]}|sch|")):
        for ph in KICK_PHASES:                                       # full speed: the kick runs above
            q = R.get(f"{prefix}{ph:g}")
            if q and "error" not in q:
                sp_rows.append(dict(what="K4", diodes=dnm, F_Hz=f_pick, rpm_relative=rpm_pick, phase_cycles=ph, n_cyc=40,
                                    runs=q["starts"], AH_AT=q["AHt_AT_max"], z_early=q["z_early"], retried=q["retried"]))
    sp_rows.sort(key=lambda x: (x["what"], x["diodes"], x["F_Hz"], x["phase_cycles"] or 0.0))
    sp_sum = {}
    for x in sp_rows:
        g_ = sp_sum.setdefault(f"{x['what']} / {x['diodes']}", {})
        s_ = g_.setdefault(f"{x['rpm_relative']:.0f}", dict(runs=0, of=0, AH_AT=None))
        s_["of"] += 1
        if x["runs"]:
            s_["runs"] += 1
            s_["AH_AT"] = x["AH_AT"]
    for g_ in sp_sum.values():                                       # the lowest speed from which every phase runs
        sp_ = sorted(g_, key=float, reverse=True)
        ok_ = [s for i_, s in enumerate(sp_) if all(g_[t]["runs"] == g_[t]["of"] for t in sp_[:i_ + 1])]
        g_["all_phases_from_rpm_relative"] = float(ok_[-1]) if ok_ else None
    speed = dict(note="the same parts on a stretched cycle (the utrons' L(theta) fixed in angle; every L, R and snubber "
                      "kept); the 22 mF bypass fitted; K4 = the recommended kick; 'hold': a seed of "
                      f"{HOLD_FRAC:.0%} of Psi_s in every coil, a proxy for a running pump that slows down [IR]",
                 run_criterion=f"more than {RUN_AT:.0f} A-turns in the AH coil over the last 4 of {N_CYC_SPEED} cycles "
                               f"(a pump that dies is at ~0); at {rpm_pick:.0f} rpm relative the kick runs' own criterion",
                 rpm_relative_per_Hz=rpm_pick / f_pick, rows=sp_rows, summary=sp_sum)
    rat = ratings(base, byp, es, ch, cusp22, Z, fl, dict(candidates=cand, recommended=rec, thresholds=thr,
                                                        byp_worst_V=byp_worst,
                                                        speed_from_rpm=sp_sum.get("K4 / rec", {}).get(
                                                            "all_phases_from_rpm_relative")))
    creep = creep_table(es)
    out = dict(
        sources=SRC, pick=PICK,
        tags="CONVENTIONS.md §1: [OC] derivable physics; [IR] a modelling or engineering choice, datasheet-class values "
             "included; [RH] heuristic, not load-bearing",
        la_lb=dict(**ch, spice=tau_sum,
                   record_tau_sweep=duty_rec["tau_sweep"],
                   assumptions=dict(B_max_T=B_MAX, B_knee_T=B_KNEE, k_stack=K_STACK, mu_r=MU_R, mu_r_range=MU_R_RANGE,
                                    l_fe_per_a=L_FE_PER_A, lamination="M400-50A class, 0.5 mm, P1.5/50 4.0 W/kg",
                                    fe_loss="(f / 50)^1.3 (B / 1.5)^2 x 1.5 [RH]", wire="IEC 60317 grade 2, overall diameter 1.03 x the bare diameter + 0.05 mm",
                                    bobbin_mm=dict(wall=T_BOB, leg_clearance=CLR_LEG, flange=T_FLANGE, outer_clearance=CLR_OUT,
                                                   tape=T_TAPE, pitch_factor=PITCH, build_used=BUILD_USE),
                                    T_amb_C=T_AMB_C, h_W_m2K=H_CONV, rotor_rad_s=W_ROTOR)),
        magnetic=dict(base=base, bypass=byp, vf_sensitivity=vf, diode_models=DIODE_MODELS,
                      record_check=dict(z_early=(base["z_early"], duty_rec["tau_sweep"][-1]["z_early"]),
                                        AH_AT_pk=(base["AH_AT_pk_branch"], duty_rec["tau_sweep"][-1]["AH_AT_pk"]),
                                        P_belt_W=(base["P_belt_W"], duty_rec["tau_sweep"][-1]["P_belt_W"]),
                                        La_I_max=(base["la"]["I_max"], duty_rec["la_lb"]["La"]["I_max_A"]),
                                        bypass_I_rms=(byp["bypass"]["I_rms_A"], cusp22["I_byp_rms_A"]))),
        kick=dict(bypass_worst_reverse_V=byp_worst, seed_record=seed_rec, seed_basis="sim/pole_design.py run_real: seed = frac * Psi_s / L_max, a current "
                                                   "in L1, L2, the AH pair, La and Lb (sim/magnetic_doubler.py deck)",
                  record_kick_frac=op.get("kick_frac"), record_kick_mJ=op.get("kick_mJ"),
                  thresholds=thr, reversed_seed=rev_sum, runs=kicks, candidates=cand, energy_sweep=esweep,
                  other_sign_two_nodes_no_bypass=others, with_real_diodes=kick_diodes, robust=robust,
                  start_criterion=f"the AH coil reaches {START_AT:.0f} A-turns within 40 cycles (sim/pole_design.py size_op)",
                  recommended=rec, speed=speed),
        electrostatic=dict(record_check=dict(P_belt_W=(es["P_W"].get("belt"), E["rs"]["P_belt_W"]),
                                             Z1_P_W=(es["clamps"]["Z1"]["P_W"], E["rs"]["Z1"]["P_W"]),
                                             VR_D3_kV=(es["diodes"]["D3"]["VR_pk_kV"], E["rs"]["VR_pk_kV"]["D3"])),
                           **es, flashover=fl, clamp_string=Z, R_surge_ohm=R_SURGE),
        ratings=rat,
        creepage=dict(rows=creep, materials=MATERIALS, creep_pd2_mm_per_kV=CREEP_PD2, creep_pd3_mm_per_kV=CREEP_PD3,
                      dc_margin=DC_MARGIN, clearance_margin=CLR_MARGIN, F2_case_A=F2_CASE_A, E_potting_kV_mm=E_POT),
        hub_inputs=dict(AH=hub["AH"]["value"], AH_seat=hub["AH_seat"]["value"], retainer=hub["retainer"]["value"]["material"]),
    )
    json.dump(out, open(os.path.join(HERE, "parts_first_cut_results.json"), "w"), indent=1, default=float)
    c = ch["chosen"]
    print(f"La / Lb: {c['core']} x {c['stack_mm']:.0f} mm, {c['turns']} t of {c['wire_mm']:.2f} mm, gap {c['gap_total_mm']:.3f} mm, "
          f"R20 {c['R20_ohm']:.3f} ohm ({c['R_T_ohm']:.3f} at {c['T_cu_C']:.0f} C), B {c['B_pk_T']:.2f} T, {c['m_kg']:.2f} kg", flush=True)
    for nm, v in tau_sum.items():
        print(f"  tau {nm} {v['tau_fixed_s']:.3f} s: held z {v['psi_held']['z_early']:.4f} AH {v['psi_held']['AH_AT_pk']:.0f} "
              f"belt {v['psi_held']['P_belt_W']:.2f} W | restored AH {v['AH_restored']['AH_AT_pk']:.0f} belt "
              f"{v['AH_restored']['P_belt_W']:.2f} W", flush=True)
    print(f"record check: z {base['z_early']:.4f} vs {duty_rec['tau_sweep'][-1]['z_early']:.4f}; AH "
          f"{base['AH_AT_pk_branch']:.1f} vs {duty_rec['tau_sweep'][-1]['AH_AT_pk']:.1f}; ES belt {es['P_W'].get('belt'):.4f} "
          f"vs {E['rs']['P_belt_W']:.4f} W", flush=True)
    print(f"kick: seed {seed_rec['frac']} -> {seed_rec['i0_A']:.3f} A, {seed_rec['E_seed_mJ']:.2f} mJ (old basis "
          f"{seed_rec['E_old_basis_mJ']:.1f}); thresholds {[(k_, v_['min_start']) for k_, v_ in thr.items()]}; "
          f"candidates that start at every phase: {always}; with every diode set too: {robust}; recommended {rec}",
          flush=True)
    for nm, v in cand.items():
        print(f"  {nm}: phases started {v['phases_started']} of {v['phases_run']} (no verdict {v['phases_no_verdict']}), "
              f"I_pk {v['I_pk_A']}, V_cap {v['V_cap_range']}, bypass V {v['bypass_V_whole_run']}", flush=True)
    print("  other sign / two nodes / no bypass:", others, flush=True)
    print("  the capacitor kicks with real diodes:", {c_: {d_: v_["phases_started"] for d_, v_ in x_.items()}
                                                      for c_, x_ in kick_diodes.items()}, flush=True)
    print("  energy sweep:", esweep, flush=True)
    print("reversed seed:", {k_: (v_.get("starts"), v_.get("AHt_I_mean_A"), v_.get("bypass_V_whole_run")) for k_, v_ in rev_sum.items()},
          flush=True)
    for g_, v_ in sp_sum.items():
        print(f"  below full speed, {g_}: every phase runs from {v_['all_phases_from_rpm_relative']} rpm relative; "
              + ", ".join(f"{s} rpm {x['runs']}/{x['of']}" + (f" ({x['AH_AT']:.0f} A-t)" if x["AH_AT"] else "")
                          for s, x in sorted(((s, x) for s, x in v_.items() if s[0].isdigit()), key=lambda t: float(t[0]))),
              flush=True)
    for r_ in rat:
        print(f"  {r_['part']}: {r_['duty']} | {r_['rating']} | {r_['margin']}", flush=True)


if __name__ == "__main__":
    main()
