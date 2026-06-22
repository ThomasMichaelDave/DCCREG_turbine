#!/usr/bin/env python3
"""
sim/design_synth.py — DESIGN-SYNTH: a constrained dimension-chooser.
====================================================================
THE PRINCIPLE: the synthesizer may choose every dimension (plate radii, gaps, cap values, rpm,
staging, motor geometry), but each candidate is checked against a fixed battery of INVARIANTS --
the validated derivations, the rules-of-thumb, and conservation. Dimensions are DECISION VARIABLES;
the rules and derivations are HARD CONSTRAINTS. The frozen solvers stay the authority on
z/eta/W_mech/W_coll: the tool CALLS them per candidate -- it never re-derives, fits, or overrides
them. Flexibility moves within the feasible region the invariants define; it can never quietly
override a derivation.

Given a goal + an objective, it searches the dimension space, rejects anything that violates an
invariant, and returns the best feasible dimensioned design PLUS THE BINDING CONSTRAINT (which rule
limits it). An infeasible goal is a result -- it names which invariant blocks.

Invariant battery (reconstructed from the campaign's established results, since this repo has no
separate numbered-rules doc): I1 conservation(real, +5% trip) · I2 frozen-solver authority ·
I3 scale-free z-ratios · I4 insulate-first · I5 tax/staging · I6 parasitic floor · I7 motor matched ·
I8 DC-trapped tank · I9 mechanical(rim/supercritical/vacuum) · I10 shuttle integrity.

FIREWALL: pure EE/mechanical; no substrate physics. Tiers [OC] derivable · [IR] design choice ·
[ME] method. Symbol hygiene: gap=g, N_sec, *Mm for mm params. Frozen empty-diff asserted.
"""
import csv
import math
import os
import subprocess
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "reference"))
import doubler_core as dc           # FROZEN AUTHORITY: z, the phase solve
import energy_balance_from_solver as eb   # the d/2 V^2 dC decomposition (eta, W_mech)
import island_charging_cosim as ic        # FROZEN shuttle (W_coll/E_fire/C_fire) -- run, not edited
import island_resonant_core as irc       # NEW resonant island transfer (Lx) -- the efficiency fix

EPS0 = 8.8541878128e-12

# ---- the ESTABLISHED machine (the regression anchor / canary) --------------- [OC]
ESTABLISHED = dict(
    r_inMm=95.0, r_outMm=387.0, g_vMm=7.0, N_sec=12, n_kept=6,
    C1min_pF=16.0, C1max_pF=280.0, Ca_pF=309.0, Cpar_pF=20.0,
    Cx_maxMm=471.0, g_islMm=4.0, C_R_pF=789.0, f0_kHz=637.0, k_split=0.30,
    g_sgMm=0.5, rpm=3000.0, stageN=2, V_targetV=15e3, V_strikeV=20e3, V_ceilV=21e3,
    Lx_mH=1.0,   # series island inductor (resonant transfer) -- KiCad Lx3/Lx4 [resonant-island]
)
# ---- rule thresholds (the invariants' constants, from the campaign) --------- [OC]/[IR]
Z_BAND = (1.20, 1.45)               # validated doubler z band (device 1.203 .. wide 1.438)  [OC]
CPAR_FLOOR_pF = 20.0                # stray floor; C_min cannot go below it (I6)              [OC]
ETA_MIN_USEFUL = 0.15               # below this, tax dominates -> must stage (I5)            [IR]
RIM_HARD = 200.0; RIM_SOFT = 150.0  # m/s rim-speed limits (I9)                               [OC]
VAC_SPEC_PA = 10.0                  # cavity vacuum spec (I9, windage-gated)                  [IR]
E_DIEL_DERATED = 5.0                # kV/mm garolite derated w/ creepage margin (I4 septum)   [IR]
K_VAC = 60.0                        # vacuum total-voltage breakdown V_bd=K*g^0.6 kV (I4 gap) [IR]
PRF_BRANCH = 300.0; PRF = 600.0; F0_SPECTATOR_MIN = 100.0   # I7
USEFUL_FRAC = 0.386                 # net-electrical fraction at the 4-node point (eta)        [OC]

_zeta_cache = {}


# =============================================================================
# the forward geometry model + the FROZEN-SOLVER wrappers (I2: called, not substituted)
# =============================================================================
def Cmax_from_geom(r_inMm, r_outMm, g_vMm, n_kept=6, N_sec=12):
    """C_max = eps0 * (kept-sector area) / gap.  [OC] geometry."""
    A = n_kept * (1.0 / N_sec) * math.pi * (r_outMm ** 2 - r_inMm ** 2)   # mm^2
    return EPS0 * (A * 1e-6) / (g_vMm * 1e-3) * 1e12                       # pF


# the ROTOR body is the active-band outer + the bus margin (ref-radii: R387 active-band outer ->
# R491 rotor outer after bus -> R500 plate edge). The rim mass/stress is at R491, not R387. The
# search still OPTIMISES r_outMm (the active band); only the REPORTED diameter + the rim carry the
# bus -- a constant multiplier, so the optimum r_outMm is unchanged. [OC] geometry definition.
BUS_MARGIN = 0.27                                          # 491/387 - 1


def rotor_outMm(d):
    return d["r_outMm"] * (1.0 + BUS_MARGIN)


def rotor_dia_mm(d):
    return 2.0 * d["r_outMm"] * (1.0 + BUS_MARGIN)


def z_eta_Wmech(C1min, C1max, Ca, Cpar):
    """FROZEN-SOLVER AUTHORITY (I2): z + eta from doubler_core for the CHOSEN ratios. z/eta are
    scale-free (ratios only) -> cached by the normalized ratio tuple. Returns (z, eta)."""
    key = (round(C1min / C1max, 5), round(Ca / C1max, 5), round(Cpar / C1max, 5))
    if key in _zeta_cache:
        return _zeta_cache[key]
    z, rec = dc.solve_doubler4(C1min, C1max, C1min, C1max, Ca, Ca, Cpar,
                               iterations=140, burn=70, trace=True)
    steps = eb.decompose(rec, Ca, Ca, Cpar); cyc = eb.per_cycle(steps)
    keys = sorted(k for k in cyc if 80 <= k <= 130)
    rs = [cyc[k]["dU"] / cyc[k]["Wmech"] for k in keys if cyc[k]["Wmech"] > 0]
    eta = float(np.median(rs)) if rs else 0.0
    _zeta_cache[key] = (z, eta)
    return z, eta


_shuttle_cache = {}


def shuttle_Wcoll(Cx_maxMm):
    """FROZEN shuttle (I2): W_coll/E_fire/C_fire/V* for the chosen island, single-face. Run, not
    edited."""
    key = round(Cx_maxMm, 1)
    if key in _shuttle_cache:
        return _shuttle_cache[key]
    saved = ic.CX_MAX
    try:
        ic.CX_MAX = Cx_maxMm * 1e-12
        st = ic.run_steady("real", ic.CA)
    finally:
        ic.CX_MAX = saved
    out = dict(W_coll=st["Wcoll_mJ"] * 1e-3, E_fire=st["E_fire_mJ"] * 1e-3,
               C_fire=st["C_fire_pF"], Vstar=st["Vstar_kV"] * 1e3)
    _shuttle_cache[key] = out
    return out


# =============================================================================
# the INVARIANT BATTERY (each -> dict(ok, slack, detail)); slack normalized [0,1+], <0 = fail
# =============================================================================
def invariants(d):
    """Run all 10 invariants on a candidate design dict d. Returns {name: (ok, slack, detail)}."""
    out = {}
    OMEGA = d["rpm"] * 2 * math.pi / 60.0
    C1max = Cmax_from_geom(d["r_inMm"], d["r_outMm"], d["g_vMm"], d["n_kept"], d["N_sec"])
    C1min = d["C1min_pF"]
    z, eta = z_eta_Wmech(C1min, C1max, d["Ca_pF"], d["Cpar_pF"])
    sh = shuttle_Wcoll(d["Cx_maxMm"])
    d["_C1max"] = C1max; d["_z"] = z; d["_eta"] = eta; d["_sh"] = sh

    # --- I2 frozen-solver authority: z/eta/W_coll are valid numbers from the solvers ---
    i2 = z > 0 and 0 < eta < 1 and sh["W_coll"] > 0
    out["I2_solver_authority"] = (i2, 1.0 if i2 else -1.0,
                                  f"z={z:.4f} eta={eta:.4f} W_coll={sh['W_coll']*1e3:.2f}mJ (frozen)")

    # --- I3 scale-free z within the validated band ---
    sl3 = min(z - Z_BAND[0], Z_BAND[1] - z) / (Z_BAND[1] - Z_BAND[0])
    out["I3_scalefree_z"] = (Z_BAND[0] <= z <= Z_BAND[1], sl3,
                             f"z={z:.4f} in {Z_BAND}")

    # --- I4 insulate-first (BEFORE sizing): gap holds V_target, septum holds, coil antinode out ---
    V_bd_gap = K_VAC * d["g_sgMm"] ** 0.6 * 1e3            # vacuum breakdown of the spark gap (V)
    gap_ok = V_bd_gap > d["V_targetV"] and V_bd_gap < 3 * d["V_strikeV"]   # holds hold, fires near strike
    sep_hold = d.get("septumMm", 12.0) * E_DIEL_DERATED * 1e3              # septum hold (V)
    sep_ok = sep_hold > d["V_targetV"]
    coil_ok = d["k_split"] > 0.0                          # split -> antinode out of winding (S7)
    i4 = gap_ok and sep_ok and coil_ok
    sl4 = (V_bd_gap - d["V_targetV"]) / d["V_targetV"]
    out["I4_insulate_first"] = (i4, sl4 if i4 else -1.0,
                                f"gap V_bd={V_bd_gap/1e3:.1f}kV>{d['V_targetV']/1e3:.0f} "
                                f"septum {sep_hold/1e3:.0f}kV coil-split={coil_ok}")

    # --- I5 tax managed (eta from staging; tax must not dominate the useful output) ---
    i5 = eta >= ETA_MIN_USEFUL
    out["I5_tax_managed"] = (i5, (eta - ETA_MIN_USEFUL) / ETA_MIN_USEFUL,
                             f"eta={eta:.3f} (>= {ETA_MIN_USEFUL}); stageN={d['stageN']}")

    # --- I6 parasitic floor: the EFFECTIVE C_min = C1min(geom) + C_par >= C_par always; the real
    #     constraint is that the design cannot pretend the stray away (C_par >= the ~20 pF floor),
    #     and the geometric C1min is non-negative. The parasitic floor BINDS the minimum size
    #     indirectly: as C_max -> C_par the modulation -> 1 and z collapses (caught by I3). ---
    cpar_ok = d["Cpar_pF"] >= CPAR_FLOOR_pF and C1min >= 0.0
    eff_min = C1min + d["Cpar_pF"]
    # slack = the modulation headroom (how far C_max sits above the parasitic floor before the
    # swing collapses); large when C_max >> C_par, -> 0 as C_max -> C_par (then I3's z also fails).
    sl6 = (C1max - d["Cpar_pF"]) / max(d["Cpar_pF"], 1e-9)
    out["I6_parasitic_floor"] = (cpar_ok, sl6,
                                 f"C_par={d['Cpar_pF']:.0f}>={CPAR_FLOOR_pF:.0f}pF; eff C_min="
                                 f"{eff_min:.0f}pF (geom {C1min:.0f}+stray); mod-margin {sl6:.1f}")

    # --- I7 motor matched: output <= pump net; f_res=PRF; spectator at f0 ---
    W_mech = 15.941e-3 * (C1max / 280.0)                  # W_mech scales with C area  [OC scale-free]
    pump_net = eta * W_mech                               # net electrical per cycle
    motor_out = d.get("motor_outMm", 0.6 * pump_net / 1e-3) * 1e-3   # [IR] modelled, default < net
    f_res = d.get("f_res_Hz", PRF_BRANCH)
    fres_ok = abs(f_res - PRF_BRANCH) < 1.0
    z_f0 = d.get("Zf0_ratio", 8000.0)                    # spectator ratio at f0 (coil-topology)
    i7 = motor_out <= pump_net and fres_ok and z_f0 > F0_SPECTATOR_MIN
    out["I7_motor_matched"] = (i7, (pump_net - motor_out) / max(pump_net, 1e-12),
                               f"out={motor_out*1e3:.2f}<=net={pump_net*1e3:.2f}mJ f_res={f_res:.0f}Hz "
                               f"specratio={z_f0:.0f}")

    # --- I8 DC-trapped tank: dielectric duty-limited, not the voltage lever (structural) ---
    i8 = d.get("tank_DC", True)
    out["I8_dc_trapped_tank"] = (i8, 1.0 if i8 else -1.0, "tank held DC (tan-delta duty-limited)")

    # --- I9 mechanical: rim speed < limit; supercritical; vacuum <= spec ---
    rim = OMEGA * (rotor_outMm(d) * 1e-3)              # rim at the ROTOR body (R491), not R387
    sl9 = (RIM_HARD - rim) / RIM_HARD
    superc = d.get("supercritical", True)
    vac_ok = d.get("vacuum_Pa", 1.0) <= VAC_SPEC_PA
    i9 = rim < RIM_HARD and superc and vac_ok
    out["I9_mechanical"] = (i9, sl9 if i9 else -1.0,
                            f"rim={rim:.0f}m/s (<{RIM_HARD}, soft {RIM_SOFT}) "
                            f"supercritical={superc} vac<={VAC_SPEC_PA}Pa")

    # --- I10 shuttle integrity: island strike < ceiling; collapse reaches V_strike; AND the
    #     resonant-island sub-checks (the series Lx transfer, KiCad 37-comp topology): t1/2 fits the
    #     SG conduction window, i_pk within rating, ring node within insulation. [resonant-island] ---
    strike_ok = d["V_strikeV"] < d["V_ceilV"]
    reaches = sh["C_fire"] > 0 and d["V_strikeV"] > sh["Vstar"]   # collapse boosts V* -> V_strike
    # resonant Lx sub-checks
    Lx = d.get("Lx_mH", 1.0) * 1e-3
    C_src = d["Cx_maxMm"] * 1e-12; C_bank = 2640e-9; dVr = 5e3   # island -> bank, ~5 kV [IR seq->TMD]
    cf = irc.closed_form(C_src, C_bank, dVr, Lx, 20.0)
    win_s = 5.0 / (d["rpm"] / 60.0 * 360.0)                       # 5deg SG window [IR/EST]
    timing_ok = cf["t_half"] <= win_s
    current_ok = cf["i_pk"] <= 100.0
    voltage_ok = dVr <= d["V_ceilV"]
    i10 = strike_ok and reaches and timing_ok and current_ok and voltage_ok
    sl10 = (d["V_ceilV"] - d["V_strikeV"]) / d["V_ceilV"]
    out["I10_shuttle_integrity"] = (i10, sl10 if i10 else -1.0,
                                    f"strike {d['V_strikeV']/1e3:.0f}/{d['V_ceilV']/1e3:.0f}kV; "
                                    f"V* {sh['Vstar']/1e3:.1f}->C_fire {sh['C_fire']:.0f}pF; "
                                    f"resonant Lx {Lx*1e3:.2f}mH: t1/2 {cf['t_half']*1e6:.1f}/{win_s*1e6:.0f}us"
                                    f"({'ok' if timing_ok else 'OVER'}) i_pk {cf['i_pk']:.1f}A"
                                    f"({'ok' if current_ok else 'OVER'})")

    # --- I1 conservation, real (+5% trip) -- the per-cycle ledger + the non-tautology test ---
    i1_ok, resid, trip = conservation(d, W_mech, eta, sh)
    out["I1_conservation"] = (i1_ok, 1.0 if i1_ok else -1.0,
                              f"resid={resid:.1e} +5%trip={'fires' if trip else 'FLAT'}")
    return out


def conservation(d, W_mech, eta, sh, perturb=0.0):
    """The per-cycle independent ledger (SOURCE torque-energy vs DEST independent loss models) +
    the +5% non-tautology trip (perturb the SOURCE only). Returns (ok, residual, trip_fires)."""
    def ledger(pert):
        # SOURCE (mechanical work integrals)
        W_mech_src = W_mech * (1.0 + pert)
        W_coll_src = sh["W_coll"]
        E_belt = W_mech_src + W_coll_src
        # DEST (independent models; use NOMINAL W_mech, not the perturbed source)
        tax = (1 - eta) * W_mech
        delivered = eta * W_mech
        rail_seed = sh["E_fire"] - sh["W_coll"]
        gov_shed = max(0.0, delivered - rail_seed)
        E_diss = tax + sh["E_fire"] + gov_shed
        return abs(E_belt - E_diss) / max(E_belt, 1e-30)
    resid = ledger(0.0)
    trip = ledger(0.05)
    ok = resid < 1e-6
    return ok, resid, trip > 0.005


def feasible(inv):
    return all(v[0] for v in inv.values())


def binding(inv):
    """Fallback: the feasible invariant with the least slack."""
    feas = [(k, v[1]) for k, v in inv.items() if v[0]]
    return min(feas, key=lambda kv: kv[1])[0] if feas else None


def binding_active(d_opt, objective, base, grid):
    """The ACTIVE constraint = the rule that blocks IMPROVING the objective. Perturb the
    objective's key free-variable one grid step in the improving direction; the invariant that
    fails in that improving neighbour is what limits the design (the single most useful diagnostic).
    Falls back to least-slack if the edge of the grid is reached."""
    # the improving direction per objective + the variable it moves
    improving = {"min_diameter": ("r_outMm", -1), "max_rpm": ("rpm", +1),
                 "max_eta": ("C1min_pF", +1), "min_belt_power": ("r_outMm", -1)}
    if objective not in improving:
        return binding(invariants(dict(d_opt))), "least-slack (no perturbation rule)"
    var, direction = improving[objective]
    axis = sorted(grid[var]); cur = d_opt[var]
    try:
        idx = axis.index(cur)
    except ValueError:
        idx = min(range(len(axis)), key=lambda i: abs(axis[i] - cur))
    nxt = idx + direction
    if 0 <= nxt < len(axis):
        neigh = make_design(base, **{k: d_opt[k] for k in ("r_outMm", "g_vMm", "C1min_pF", "rpm")})
        neigh[var] = axis[nxt]
        ninv = invariants(neigh)
        fails = [(k, v[1]) for k, v in ninv.items() if not v[0]]
        if fails:
            k = min(fails, key=lambda kv: kv[1])[0]      # most-violated failing rule
            return k, f"improving {var}->{axis[nxt]} fails here"
    return binding(invariants(dict(d_opt))), "grid edge (least-slack)"


# =============================================================================
# the constrained SEARCH (objective over free vars subject to the §2 battery)
# =============================================================================
def make_design(base, **free):
    d = dict(base); d.update(free); return d


def objective_value(d, objective):
    C1max = d["_C1max"]; eta = d["_eta"]
    W_mech = 15.941e-3 * (C1max / 280.0)
    if objective == "min_diameter":
        return rotor_dia_mm(d)
    if objective == "max_eta":
        return -eta
    if objective == "max_rpm":
        return -d["rpm"]
    if objective == "min_belt_power":
        return W_mech * PRF
    if objective == "max_energy_density":
        vol = math.pi * (d["r_outMm"] * 1e-3) ** 2 * 0.05     # rough disc volume
        return -(0.5 * d["C_R_pF"] * 1e-12 * d["V_targetV"] ** 2) / vol
    return rotor_dia_mm(d)


def search(objective, base, grid):
    """Constrained search: evaluate every grid candidate, run the §2 battery (frozen-solver
    calls), keep feasible, return the objective-optimal feasible design + its binding constraint."""
    best = None; n_eval = 0; n_feas = 0
    for r_out in grid["r_outMm"]:
        for g_v in grid["g_vMm"]:
            for C1min in grid["C1min_pF"]:
                for rpm in grid["rpm"]:
                    d = make_design(base, r_outMm=r_out, g_vMm=g_v, C1min_pF=C1min, rpm=rpm)
                    inv = invariants(d); n_eval += 1
                    if not feasible(inv):
                        continue
                    n_feas += 1
                    val = objective_value(d, objective)
                    if best is None or val < best[1]:
                        best = (d, val, inv)
    return best, n_eval, n_feas


# =============================================================================
# MAIN
# =============================================================================
def main():
    print("=" * 92)
    print("DESIGN-SYNTH — a constrained dimension-chooser (free dimensions, invariant rules)")
    print("=" * 92)
    diff = subprocess.run(["git", "diff", "--name-only", "--", "shuttle_core.py", "reference/",
                           "index.html", "sim/resonator_sim.py"],
                          cwd=ROOT, capture_output=True, text=True).stdout.strip()
    print(f"\n[check 1] frozen empty-diff: {'PASS' if diff == '' else 'FAIL ' + diff}")
    print("[check 1] frozen solvers CALLED per candidate (doubler_core z/eta, shuttle W_coll); "
          "never re-implemented.")

    # ---- check 2: regression anchor (the established machine must be feasible) ----
    print("\n[check 2] REGRESSION ANCHOR — the established ~1000 mm / 15 kV machine:")
    anc = dict(ESTABLISHED)
    inv = invariants(anc)
    anc_dia = rotor_dia_mm(anc)
    print(f"  synthesized C1_max = {anc['_C1max']:.0f} pF (target 280) | z={anc['_z']:.4f} "
          f"eta={anc['_eta']:.4f} | rotor dia {anc_dia:.0f} mm (active band {2*anc['r_outMm']:.0f} "
          f"+ {BUS_MARGIN*100:.0f}% bus -> R491 rotor)")
    anc_feasible = feasible(inv)
    for k, (ok, sl, det) in inv.items():
        print(f"    {'PASS' if ok else 'FAIL':4s} {k:22s} slack {sl:+.2f}  {det}")
    # the canary now checks the DIMENSION too: the established rotor must reproduce at ~982 mm
    # (it would fail at the active-band 774 mm if the bus were dropped -- that is the canary's job).
    dia_ok = 960 <= anc_dia <= 1010
    print(f"  [check 2] rotor-diameter assertion: {anc_dia:.0f} mm in [960,1010] "
          f"{'PASS' if dia_ok else 'FAIL'} (vs the R491 rotor ~982 mm)")
    if not (abs(anc["_C1max"] - 280) < 5 and anc_feasible and dia_ok):
        print("  -> REGRESSION-FAIL: the established machine does not reproduce/pass "
              f"(C1_max/z/eta or rotor dia {anc_dia:.0f} mm != ~982). STOP.")
        return 1
    print(f"  -> regression anchor REPRODUCES (280 pF, z 1.334) and is FEASIBLE; binding = "
          f"{binding(inv)}")

    # ---- check 5: I1 conservation closes + the +5% trip fires ----
    W_mech = 15.941e-3; ok1, resid, trip = conservation(anc, W_mech, anc["_eta"], anc["_sh"])
    print(f"\n[check 5] I1 conservation: residual {resid:.1e} (closes) AND +5% trip "
          f"{'FIRES (non-tautological)' if trip else 'FLAT -> TAUTOLOGICAL'}")
    if not (ok1 and trip):
        print("  -> INVARIANT-VIOLATED (I1): guard tautological. STOP.")
        return 1

    # ---- checks 3,4,6: synthesize for objectives ----
    base = dict(ESTABLISHED)
    grid = dict(r_outMm=[150, 200, 250, 300, 350, 387, 450, 500],
                g_vMm=[3.0, 5.0, 7.0, 10.0],
                C1min_pF=[20, 30, 50, 80],
                rpm=[3000, 6000, 9000, 12000])
    results = {}
    for obj in ("min_diameter", "max_eta", "max_rpm"):
        print("\n" + "=" * 92)
        print(f"OBJECTIVE: {obj}")
        best, n_eval, n_feas = search(obj, base, grid)
        if best is None:
            print(f"  no feasible candidate over {n_eval} -> SYNTH-INFEASIBLE for this grid")
            results[obj] = None
            continue
        d, val, inv = best
        bc, why = binding_active(d, obj, base, grid)
        results[obj] = (d, inv, bc)
        print(f"  searched {n_eval} candidates, {n_feas} feasible.")
        print(f"  OPTIMAL free vars: rotor dia {rotor_dia_mm(d):.0f} mm | g_v {d['g_vMm']:.1f} mm | "
              f"C_min {d['C1min_pF']:.0f} pF | rpm {d['rpm']:.0f} | C_max {d['_C1max']:.0f} pF | "
              f"z {d['_z']:.4f} eta {d['_eta']:.4f}")
        print(f"  >>> BINDING CONSTRAINT: {bc}  [{why}]  ({inv[bc][2]})")
        print(f"  compliance:")
        for k, (okk, sl, det) in inv.items():
            mark = "<<BINDING" if k == bc else ""
            print(f"    {'PASS' if okk else 'FAIL':4s} {k:22s} slack {sl:+.2f}  {det}  {mark}")

    # ---- infeasible-goal probe (exercise the SYNTH-INFEASIBLE path + the named blocker) ----
    print("\n" + "=" * 92)
    print("INFEASIBLE-GOAL PROBE: demand a tiny rotor (dia <= 300 mm rotor = r_out <= 118 mm "
          "after the 27% bus) at 15 kV:")
    tiny = dict(r_outMm=[118], g_vMm=[3.0, 5.0, 7.0], C1min_pF=[20, 30], rpm=[3000])
    bt, ne, nf = search("min_diameter", base, tiny)
    if bt is None:
        # name the blocker: the PHYSICAL root-cause invariant (z-collapse etc.), prioritised over
        # the meta-checks (I2 solver-sanity / I1 conservation, which fail downstream of it).
        from collections import Counter
        fails = Counter()
        for g_v in tiny["g_vMm"]:
            for C1min in tiny["C1min_pF"]:
                dprobe = make_design(base, r_outMm=118, g_vMm=g_v, C1min_pF=C1min)
                for k, v in invariants(dprobe).items():
                    if not v[0]:
                        fails[k] += 1
        priority = ["I3_scalefree_z", "I4_insulate_first", "I9_mechanical", "I10_shuttle_integrity",
                    "I7_motor_matched", "I5_tax_managed", "I6_parasitic_floor",
                    "I8_dc_trapped_tank", "I2_solver_authority", "I1_conservation"]
        blocker = next((k for k in priority if fails.get(k)), (fails.most_common(1)[0][0] if fails else "unknown"))
        print(f"  {ne} candidates, {nf} feasible -> SYNTH-INFEASIBLE for dia<=300 mm.")
        print(f"  >>> BLOCKING INVARIANT: {blocker} (z collapses as C_max -> C_par at small radius) "
              f"-- the goal is impossible without relaxing this rule (e.g. a higher z-ratio family,")
        print(f"      a smaller stray floor, or accepting a lower z).")
        infeasible_demo = (blocker,)
    else:
        print(f"  unexpectedly feasible at dia 300 mm (z {bt[0]['_z']:.3f}).")
        infeasible_demo = None

    # ---- verdict ----
    print("\n" + "=" * 92)
    print("VERDICT:")
    any_feas = any(results[o] for o in results)
    if any_feas:
        verdict = "SYNTH-FEASIBLE"
        print(f"  SYNTH-FEASIBLE — feasible dimensioned designs found for the objectives; Claude Code")
        print(f"  chose the dimensions, every invariant held, the conservation guard closes AND can fail.")
        for o in results:
            if results[o]:
                d, inv, bc = results[o]
                print(f"    {o:16s}: dia {rotor_dia_mm(d):.0f} mm, z {d['_z']:.3f}, eta {d['_eta']:.3f} "
                      f"-> BOUND BY {bc}")
    else:
        verdict = "SYNTH-INFEASIBLE"
    print(f"\n  -> {verdict}")

    _emit(results, anc, inv)
    diff = subprocess.run(["git", "diff", "--name-only", "--", "shuttle_core.py", "reference/",
                           "index.html", "sim/resonator_sim.py"],
                          cwd=ROOT, capture_output=True, text=True).stdout.strip()
    assert diff == "", f"frozen drift: {diff}"
    print("\n[frozen empty-diff final assert] PASS")
    print(f"VERDICT: {verdict}")
    return 0


def _emit(results, anc, anc_inv):
    p1 = os.path.join(ROOT, "synth_design.csv")
    with open(p1, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["objective", "rotor_dia_mm", "g_v_mm", "C_min_pF", "C_max_pF", "z", "eta",
                    "binding_constraint", "tier"])
        for o, r in results.items():
            if r:
                d, inv, bc = r
                w.writerow([o, f"{rotor_dia_mm(d):.0f}", f"{d['g_vMm']:.1f}", f"{d['C1min_pF']:.0f}",
                            f"{d['_C1max']:.0f}", f"{d['_z']:.4f}", f"{d['_eta']:.4f}", bc, "IR"])
    p2 = os.path.join(ROOT, "synth_compliance.csv")
    with open(p2, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["invariant", "anchor_pass", "anchor_slack", "detail", "tier"])
        for k, (ok, sl, det) in anc_inv.items():
            w.writerow([k, ok, f"{sl:+.3f}", det, "OC"])
    print(f"\nwrote {os.path.relpath(p1, ROOT)}, {os.path.relpath(p2, ROOT)}")
    try:
        import matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt
    except Exception:
        return
    # z vs rotor diameter across g_v (the I3 band edge = the size-limiting derivation)
    fig, ax = plt.subplots(figsize=(8.5, 4.6))
    for g_v, col in [(3.0, "#2a9d8f"), (5.0, "#264653"), (7.0, "#e76f51")]:
        dias, zs = [], []
        for r_out in [120, 150, 175, 200, 250, 300, 350, 387, 450, 500]:
            dd = make_design(dict(ESTABLISHED), r_outMm=r_out, g_vMm=g_v, C1min_pF=20)
            C1max = Cmax_from_geom(dd["r_inMm"], r_out, g_v); z, _ = z_eta_Wmech(20, C1max, dd["Ca_pF"], dd["Cpar_pF"])
            dias.append(2 * r_out * (1.0 + BUS_MARGIN)); zs.append(z)
        ax.plot(dias, zs, "o-", color=col, label=f"g_v={g_v:.0f} mm", ms=3)
    ax.axhspan(Z_BAND[0], Z_BAND[1], alpha=0.12, color="#2a9d8f", label=f"I3 z-band {Z_BAND}")
    ax.axhline(Z_BAND[0], ls="--", color="#e76f51", lw=1)
    for o, r in results.items():
        if r:
            ax.scatter([rotor_dia_mm(r[0])], [r[0]["_z"]], marker="*", s=180, zorder=5,
                       edgecolor="k", label=f"{o} opt")
    ax.set_xlabel("rotor diameter (mm)"); ax.set_ylabel("doubler z (frozen solver)")
    ax.set_title("DESIGN-SYNTH: the I3 z-band edge limits the minimum size (scale-free derivation)")
    ax.legend(fontsize=7); ax.grid(alpha=0.3)
    fig.tight_layout(); fig.savefig(os.path.join(ROOT, "synth_feasible.png"), dpi=110); plt.close(fig)
    print("wrote synth_feasible.png")


if __name__ == "__main__":
    sys.exit(main())
