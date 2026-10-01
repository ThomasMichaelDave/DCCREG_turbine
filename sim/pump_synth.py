"""sim/pump_synth.py -- PUMP-SYNTH (brief r0.1): rotor plates -> ladder -> exact engine -> PUMPS YES/NO,
the gap-model robustness strip, the invariant battery (NOT-EVALUATED aware) and the objective searches.

Producer / consumer split: `pump_sizing.size()` produces every capacitance from the plates; the exact
engine `pump_engine` consumes them. This module only composes the two and searches; it adds no physics.

Tags: [OC] derivable/standard . [IR] design choice/interpretive . [RH] heuristic, never load-bearing . [ME] method.

Key fact [OC] (within the model): z depends only on capacitance ratios (gate S4; exact once Lx and R_lx are
co-scaled, 4e-9 with only the C's scaled -- the island ring time is the only non-capacitive scale). With every
capacitor a ratio of C_max and the floors fixed (D-CPAR = fixed), z depends on the plates only through C_max
and kappa_C, so `min_diameter` is a 1-D bisection in C_max via r_out.

Warm start [ME]: a run may start from the previous run's eigen-state (settle 0) instead of the cold seed
(settle 2). The engine's own stopping rule is unchanged -- converged only when the cycle taped from the
eigen-state repeats the switching pattern with |dz| <= 1e-12 -- so a warm run is the same exact run, only
fewer cycles. Gate W0 (sim/pump_synth_gates.py) checks warm = cold to 1e-9. A warm run that does not
converge is redone cold.
"""
import math
import time

import numpy as np

import pump_engine as PE
import pump_sizing as PS

try:
    import design_synth as DS
except Exception:                                   # the lamps degrade to NOT-EVALUATED, never block z
    DS = None

SYNTH_VERSION = "pump_synth r0.1"

# ---- firing / drive / objective defaults ------------------------------------------------------------
FIRING_DEFAULTS = dict(
    # D-GAPDEFAULT [IR]: M-RD(->0) for load and fire ("if it pumps under ring-down, it pumps"); rails and
    # backstops ideal valves (their own D-GAPDEFAULT rows are unchanged from pump-calc).
    gm_rail="valve", gm_load="ringdown", gm_fire="ringdown", gm_backstop="valve",
    ih_rail=0.0, ih_load=0.0, ih_fire=0.0, ih_backstop=0.0,
    trec_rail=0.0, trec_load=0.0, trec_fire=0.0, trec_backstop=0.0,
    motor=False,                     # D-MOTORDEFAULT [IR]: off, "not assessed" (pump-calc M2/M3 fail)
    V_strike_kV=20.0, V_ceil_kV=21.0,            # design_synth.ESTABLISHED (D-SCALE anchor)   [IR]
    d_ballMm=12.0, g_latMm=1.0,                  # sphere-gap ball / lateral gap (I11)        [IR]
    r_gap_frac=1.0,                  # gap placement radius / r_out (ESTABLISHED r_gap 387 = r_out) [IR]
    # I4 (provisional, D-MEDIUM) -- design_synth's sphere-gap + septum rule, plus the rotor-gap
    # insulation law used by min_diameter: g_v >= V_ceil / E_bd(medium)                        [IR]/[RH]
    medium="air", E_bd_air_kV_mm=3.0, g_sgMm=0.5, V_target_kV=15.0, septumMm=12.0, k_split=0.30,
    margin=0.20,                     # min_diameter: z >= 1 + m (m 0.20 reaches the I3 band)       [IR]
    dia_max_mm=983.0,                # max_margin: the stated maximum rotor diameter
    win_deg=5.0,                     # SG conduction window for the island ring (design_synth I10) [IR]
    i_pk_max_A=100.0,                # ring current rating (design_synth I10)                      [IR]
)
FIRING_KEYS = tuple(FIRING_DEFAULTS)
STRIP = (                                            # the robustness strip (pump-calc §5), load + fire
    ("M-OW", dict(gm_load="valve", gm_fire="valve")),
    ("M-RD(->0)", dict(gm_load="ringdown", gm_fire="ringdown", ih_load=0.0, ih_fire=0.0)),
    ("M-SR(0.1 us)", dict(gm_load="recover", gm_fire="recover", ih_load=0.3, ih_fire=0.3,
                          trec_load=0.1, trec_fire=0.1)),
    ("M-SR(1 us)", dict(gm_load="recover", gm_fire="recover", ih_load=0.3, ih_fire=0.3,
                        trec_load=1.0, trec_fire=1.0)),
)
# M-SR I_hold 0.3 i_pk1: the lowest I_hold at which Pass A' saw a surviving gain                [IR]
MEDIA = dict(air="air, uniform field 3 kV/mm [RH]", hard_vacuum="hard vacuum, K_VAC g^0.6 law (design_synth)",
             low_pressure="<= 10 Pa (Paschen) -- NOT-EVALUATED")
DISABLED_OBJECTIVES = dict(
    max_eta="D-CUT: eta is cut-dependent for an unloaded, growing pump [OC]; no single eta until TMD picks the cut.",
    min_belt_power="D-GOVERNOR: needs W_mech at a loaded operating point (Phase 2).")
BLOCKER_PRIORITY = ["I3_z_band", "I4_insulate_first", "I9_mechanical", "I10_shuttle_integrity",
                    "I11_crossfire", "I13_island_recovery", "I12_resonant_timing", "I7_motor_matched",
                    "I6_parasitic_floor", "I1_conservation", "I2_solver_authority"]
PASS, FAIL, NE, NA, INFO = "pass", "fail", "not-evaluated", "n/a", "info"


def defaults():
    d = dict(PS.PLATE_DEFAULTS); d.update(PS.CHOICE_DEFAULTS); d.update(FIRING_DEFAULTS)
    d["pins"] = {}
    return d


def split(inp):
    """One flat input dict -> (plates, choices, firing). Unknown keys are an error (fail-closed)."""
    inp = dict(inp or {})
    plates = {k: inp.pop(k) for k in list(inp) if k in PS.PLATE_DEFAULTS}
    choices = {k: inp.pop(k) for k in list(inp) if k in PS.CHOICE_DEFAULTS}
    firing = {k: inp.pop(k) for k in list(inp) if k in FIRING_DEFAULTS}
    if inp:
        raise KeyError(f"unknown input key(s): {sorted(inp)}")
    return plates, choices, dict(FIRING_DEFAULTS, **firing)


def sized(inp):
    plates, choices, firing = split(inp)
    return PS.size(plates, choices), firing


def engine_cfg(lad, firing, over=None):
    """Ladder + firing -> the engine config (gap models, motor, D-SCALE anchor, I11 geometry)."""
    r_out = lad["plates"]["r_outMm"]
    ex = {k: firing[k] for k in FIRING_KEYS if k in PE.DEFAULTS}
    ex.update(r_gapMm=firing["r_gap_frac"] * r_out, r_outMm=r_out, r_inMm=lad["plates"]["r_inMm"],
              g_vMm=lad["plates"]["g_vMm"])
    ex.update(over or {})
    return PE.make_config(PS.engine_config(lad, ex))


# ---- exact runs (warm-started monodromy) ------------------------------------------------------------
_WARM = {}
STATS = dict(runs=0, cycles=0, cold=0, warm=0, warm_redo=0)


def _key(cfg, lx, galvanic):
    return (cfg["topology"], bool(cfg["motor"]), cfg["motor_topology"], lx == 0.0, bool(galvanic),
            tuple(cfg["gm_" + c] for c in PE.CLASSES))


def run(cfg, lx=None, galvanic=None, record=False, events=False, log=None, warm=True):
    """One exact engine run. Returns (mono, net)."""
    net = PE.build_net(cfg, lx=lx, galvanic=galvanic)
    key = _key(cfg, lx, galvanic)
    v = _WARM.get(key) if warm else None
    mono = None
    if v is not None:
        sim = PE.make_sim(net, cfg)
        if v.shape[0] == sim.N + len(sim.I):
            PE._setstate(sim, v / np.linalg.norm(v))
            mono = PE.monodromy(net, cfg, settle=0, sim=sim, log=log, record=record, events=events)
            STATS["warm"] += 1
            if not mono["converged"]:
                STATS["warm_redo"] += 1
                mono = None
    if mono is None:
        mono = PE.monodromy(net, cfg, log=log, record=record, events=events)
        STATS["cold"] += 1
    STATS["runs"] += 1; STATS["cycles"] += mono["k"]
    if mono["converged"]:
        _WARM[key] = np.real(mono["v"]).astype(float)
    return mono, net


def z_of(cfg, **kw):
    mono, _ = run(cfg, **kw)
    return mono["z"], mono["converged"]


def headline(cfg, log=None, warm=True):
    """The headline machine: full observables (as pump_engine.evaluate's main machine)."""
    t0 = time.time()
    mono, net = run(cfg, record=True, events=True, log=log, warm=warm)
    res = dict(z=mono["z"], converged=mono["converged"], align=mono["align"])
    res.update(PE.summarize(net, cfg, mono, mono["rec"]))
    res["scaled"] = PE.scale_readouts(res, cfg)
    res["time_s"] = time.time() - t0
    return res


def strip(cfg, head=None, log=None, warm=True):
    """z under each gap model (load + fire); the one matching the headline's models reuses it."""
    out = []
    for name, ov in STRIP:
        c = dict(cfg); c.update(ov)
        same = head is not None and all(cfg.get(k) == c[k] for k in ov)
        t0 = time.time()
        if same:
            z, conv = head["z"], head["converged"]
        else:
            if log:
                log(f"robustness strip: {name}")
            z, conv = z_of(PE.make_config({k: c[k] for k in PE.DEFAULTS}), warm=warm)
        out.append(dict(model=name, z=z, converged=conv, pumps=bool(conv and z > 1.0), shared=same,
                        time_s=time.time() - t0))
    return out


def twins(cfg, head, log=None, warm=True):
    tw = {}
    for name, kw in (("G", dict(lx=0.0)), ("G0", dict(galvanic=True))):
        t0 = time.time()
        if log:
            log(f"twin {name}")
        mono, net = run(cfg, log=None, warm=warm, **kw)
        tw[name] = dict(z=mono["z"], converged=mono["converged"], dz=head["z"] - mono["z"],
                        time_s=time.time() - t0)
    return tw


# ---- invariant battery ------------------------------------------------------------------------------
def _inv(status, slack, detail, tag="[IR]"):
    return dict(status=status, slack=slack, detail=detail, tag=tag)


def g_v_insulation(firing):
    """Rotor-gap insulation law used by min_diameter (provisional, D-MEDIUM): g_v = V_ceil / E_bd."""
    V = firing["V_ceil_kV"]
    if firing["medium"] == "air":
        return V / firing["E_bd_air_kV_mm"]
    if firing["medium"] == "hard_vacuum":
        return (V / PE_K_VAC()) ** (1.0 / 0.6)
    return None


def PE_K_VAC():
    return DS.K_VAC if DS is not None else 60.0


def battery(lad, firing, cfg, head, tw=None, canary_ok=True):
    """§4: every invariant is pass / fail / not-evaluated / n/a / info. Feasibility and the named blocker
    use the evaluated ones only (pass/fail)."""
    inv = {}
    z = head["z"]; conv = head["converged"]
    led = head.get("ledger", {})
    res_ = abs(led.get("resid", float("nan")))
    inv["I1_conservation"] = _inv(PASS if res_ <= 1e-9 else FAIL, 1e-9 - res_,
                                  f"ledger residual {res_:.1e} (W = dE + E_diss; gate E4)", "[OC]")
    inv["I2_solver_authority"] = _inv(PASS if (canary_ok and conv) else FAIL, 1.0 if conv else -1.0,
                                      f"K1-K4 + E0 {'pass' if canary_ok else 'FAIL'}; pattern "
                                      f"{'repeats' if conv else 'NOT converged'}", "[OC]")
    lo, hi = (DS.Z_BAND if DS else (1.20, 1.45))
    inv["I3_z_band"] = _inv(PASS if (conv and lo <= z <= hi) else FAIL,
                            min(z - lo, hi - z) / (hi - lo),
                            f"z={z:.4f} in [{lo}, {hi}] (robust-margin lamp; PUMPS = z > 1)", "[IR] band")
    # I4 provisional (D-MEDIUM): design_synth's spark-gap/septum/coil rule + the rotor-gap law
    if DS is None:
        inv["I4_insulate_first"] = _inv(NE, 0.0, "design_synth unavailable")
    else:
        Vbd = DS.K_VAC * firing["g_sgMm"] ** 0.6
        gap_ok = Vbd > firing["V_target_kV"] and Vbd < 3 * firing["V_strike_kV"]
        sep_ok = firing["septumMm"] * DS.E_DIEL_DERATED > firing["V_target_kV"]
        coil_ok = firing["k_split"] > 0
        gins = g_v_insulation(firing)
        gv = lad["plates"]["g_vMm"]
        if gins is None:
            inv["I4_insulate_first"] = _inv(NE, 0.0, f"medium {MEDIA[firing['medium']]}")
        else:
            ok = gap_ok and sep_ok and coil_ok and gv >= gins - 1e-9
            inv["I4_insulate_first"] = _inv(PASS if ok else FAIL, (gv - gins) / gins,
                                            f"PROVISIONAL (D-MEDIUM: {MEDIA[firing['medium']]}). rotor g_v "
                                            f"{gv:.2f} >= {gins:.2f} mm for V_ceil {firing['V_ceil_kV']:.0f} kV; "
                                            f"spark gap V_bd {Vbd:.1f} kV; septum {firing['septumMm'] * DS.E_DIEL_DERATED:.0f} kV; "
                                            f"coil split {coil_ok}", "[IR] provisional")
    ec = head.get("eta_cut", {})
    inv["I5_tax"] = _inv(INFO, 0.0, f"eta(cut) band [{ec.get('min', float('nan')):.3f}, "
                                    f"{ec.get('max', float('nan')):.3f}] -- informational until D-CUT", "[IR]")
    floor = DS.CPAR_FLOOR_pF if DS else 20.0
    cpar = lad["ladder"]["Cpar"]["value"]
    inv["I6_parasitic_floor"] = _inv(PASS if cpar >= floor - 1e-12 else FAIL, (cpar - floor) / floor,
                                     f"Cpar {cpar:.1f} >= {floor:.0f} pF", "[OC]")
    prf = lad["PRF_branch"]
    if cfg["motor"]:
        cb = lad["ladder"]["C_blk_nF"]["value"] * 1e-9
        fres = 1.0 / (2 * math.pi * math.sqrt(lad["choices"]["L_coil_H"] * cb))
        inv["I7_motor_matched"] = _inv(PASS if abs(fres - prf) < 1.0 else FAIL, 1.0 - abs(fres - prf),
                                       f"f_res {fres:.1f} Hz vs PRF_branch {prf:.1f} Hz; the motor-output "
                                       f"sub-check is NOT-EVALUATED (D-GOVERNOR)", "[OC]")
    else:
        inv["I7_motor_matched"] = _inv(NE, 0.0, "motor off (D-MOTORDEFAULT): not assessed")
    inv["I8_dc_tank"] = _inv(NA, 0.0, "tank collapsed (out of scope)")
    rim = lad["rim_mps"]
    rh = DS.RIM_HARD if DS else 200.0
    inv["I9_mechanical"] = _inv(PASS if rim < rh else FAIL, (rh - rim) / rh,
                                f"rim {rim:.0f} m/s < {rh:.0f} at the rotor body R{lad['rotor_outMm']:.0f}; "
                                f"vacuum_Pa and supercritical NOT-EVALUATED", "[OC]")
    # I10: the engine's island ledger + ring sub-checks
    win_s = math.radians(firing["win_deg"]) / (cfg["rpm"] * 2 * math.pi / 60.0)
    th = [e["t_half_us"] for e in head.get("episodes", []) if e.get("t_half_us")]
    t_half = max(th) * 1e-6 if th else 0.0
    sc = head.get("scaled") or {}
    ipk = max([r["i_pk_A"] for r in sc.get("rows", [])] + [0.0])
    ok10 = conv and t_half <= win_s and ipk <= firing["i_pk_max_A"] and firing["V_strike_kV"] < firing["V_ceil_kV"]
    inv["I10_shuttle_integrity"] = _inv(PASS if ok10 else FAIL, (win_s - t_half) / win_s,
                                        f"ring t1/2 {t_half * 1e6:.2f} us <= {firing['win_deg']:.0f} deg window "
                                        f"{win_s * 1e6:.0f} us; i_pk {ipk:.1f} A <= {firing['i_pk_max_A']:.0f} A "
                                        f"(D-SCALE); strike {firing['V_strike_kV']:.0f} < ceiling "
                                        f"{firing['V_ceil_kV']:.0f} kV", "[IR]")
    lamps = PE.lamps(cfg, dict(z=z, events=head.get("episodes", [])))
    for src, dst in (("I11_crossfire", "I11_crossfire"), ("I12_resonant_timing", "I12_resonant_timing")):
        L = lamps.get(src)
        inv[dst] = _inv(NE, 0.0, "design_synth unavailable") if L is None else \
            _inv(PASS if L["pass_"] else FAIL, 1.0 if L["pass_"] else -1.0, L["detail"], "[IR]")
    if DS is not None:   # numeric slacks for the two lamps
        ov = DS.overlap_deg(cfg["d_ballMm"], cfg["r_gapMm"], cfg["g_latMm"])
        sp = cfg["st_BS3"] - cfg["st_SG3b"]
        inv["I11_crossfire"]["slack"] = (sp - ov) / sp
        t_ov = math.radians(ov) / (cfg["rpm"] * 2 * math.pi / 60.0)
        need = DS.T_STRIKE_S + t_half + DS.T_COND_S
        inv["I12_resonant_timing"]["slack"] = (t_ov - need) / need
    trv = lamps.get("TRV_admissible", dict(pass_=True, detail=""))
    if tw:
        g = tw.get("G", {})
        ok13 = trv["pass_"] and g.get("converged", False)
        inv["I13_island_recovery"] = _inv(PASS if ok13 else FAIL, 1.0 if ok13 else -1.0,
                                          f"exact twin dz(Lx vs shorted) {g.get('dz', float('nan')):+.5f}; "
                                          f"TRV: {trv['detail']}", "[OC] twin")
    else:
        inv["I13_island_recovery"] = _inv(PASS if trv["pass_"] else FAIL, 1.0 if trv["pass_"] else -1.0,
                                          f"TRV: {trv['detail']} (twin not yet run)", "[OC]")
    return inv


def feasible(inv):
    return all(v["status"] == PASS for v in inv.values() if v["status"] in (PASS, FAIL))


def blocker(inv):
    """The named blocker over EVALUATED invariants: the first failing one by design_synth's priority;
    if none fails, the least-slack passing one (design_synth.binding)."""
    fails = [k for k in BLOCKER_PRIORITY if k in inv and inv[k]["status"] == FAIL]
    if fails:
        return dict(item=fails[0], how="fails")
    ev = [(k, v["slack"]) for k, v in inv.items() if v["status"] == PASS]
    return dict(item=min(ev, key=lambda kv: kv[1])[0], how="least slack") if ev else dict(item=None, how="")


# ---- the page's one call -----------------------------------------------------------------------------
def evaluate(inp=None, with_strip=True, with_twins=True, canary_ok=True, log=None, warm=True):
    t0 = time.time()
    lad, firing = sized(inp)
    cfg = engine_cfg(lad, firing)
    head = headline(cfg, log=log, warm=warm)
    t_head = time.time() - t0
    st = strip(cfg, head, log=log, warm=warm) if with_strip else None
    t_strip = time.time() - t0
    tw = twins(cfg, head, log=log, warm=warm) if with_twins else None
    inv = battery(lad, firing, cfg, head, tw, canary_ok=canary_ok)
    out = dict(sizing=lad, firing=firing, engine=head, strip=st, twins=tw, invariants=inv,
               feasible=feasible(inv), blocker=blocker(inv), pumps=bool(head["converged"] and head["z"] > 1.0),
               z=head["z"], margin=head["z"] - 1.0, converged=head["converged"],
               times=dict(headline_s=t_head, headline_strip_s=t_strip, total_s=time.time() - t0),
               version=SYNTH_VERSION)
    return PE._jsonable(out)


# ---- critical values (the headroom meter) -------------------------------------------------------------
LADDER_KNOBS = ("Ca", "cx_max", "Cpar", "C_min", "cx_min", "gap_stray", "island_stray", "pCboss")


def _z_pinned(inp, key, value, warm=True):
    d = dict(inp or {}); pins = dict(d.get("pins") or {}); pins[key] = value; d["pins"] = pins
    lad, firing = sized(d)
    return z_of(engine_cfg(lad, firing), warm=warm)


def critical(inp, key, rel_tol=2e-3, max_runs=14, log=None):
    """The z = 1 value of one ladder item (all else as sized): bracket outward from the current value by
    factors of 2, then bisect in log(value) [ME] (the findCriticalCa bracket-and-bisect, on the exact engine)."""
    lad, _ = sized(inp)
    v0 = lad["ladder"][key]["value"]
    z0, c0 = _z_pinned(inp, key, v0)
    runs = 1
    if not c0:
        return dict(key=key, value=v0, z=z0, critical=None, note="not converged at the current value")
    best = None
    for direction in (0.5, 2.0):          # try decreasing then increasing
        a, za = v0, z0
        b = v0
        for _ in range(5):
            b = b * direction
            zb, cb = _z_pinned(inp, key, b); runs += 1
            if log:
                log(f"critical {key}: {b:.4g} -> z={zb:.5f}")
            if not cb:
                break
            if (za - 1.0) * (zb - 1.0) <= 0:
                best = (a, za, b, zb)
                break
            a, za = b, zb
        if best:
            break
    if not best:
        return dict(key=key, value=v0, z=z0, critical=None, runs=runs,
                    note="no z = 1 crossing within x1/32 .. x32 of the current value")
    a, za, b, zb = best
    while runs < max_runs and abs(math.log(b / a)) > rel_tol:
        m = math.sqrt(a * b)
        zm, cm = _z_pinned(inp, key, m); runs += 1
        if log:
            log(f"critical {key}: {m:.4g} -> z={zm:.5f}")
        if (za - 1.0) * (zm - 1.0) <= 0:
            b, zb = m, zm
        else:
            a, za = m, zm
    lna, lnb = math.log(a), math.log(b)
    vc = math.exp(lna + (lnb - lna) * (za - 1.0) / (za - zb)) if za != zb else a
    head = (v0 - vc) / v0
    return dict(key=key, value=v0, z=z0, critical=vc, headroom=head, bracket=[a, b], runs=runs,
                tol=rel_tol, note="z = 1 at the critical value (log-linear inside the final bracket) [ME]")


# ---- objectives --------------------------------------------------------------------------------------
def _with(inp, **kw):
    d = dict(inp or {}); d.update(kw); return d


def _z_at_rout(inp, r_out, log=None):
    lad, firing = sized(_with(inp, r_outMm=r_out))
    z, c = z_of(engine_cfg(lad, firing))
    if log:
        log(f"r_out {r_out:.1f} mm (C_max {lad['ladder']['C_max']['value']:.1f} pF) -> z={z:.5f}")
    return z, c, lad


def _geom_checks(inp, r_out):
    """The analytic part of the battery for a candidate r_out (I4 / I9 / I11) -- no engine run."""
    lad, firing = sized(_with(inp, r_outMm=r_out))
    cfg = engine_cfg(lad, firing)
    fake = dict(z=1.3, converged=True, ledger=dict(resid=0.0), episodes=[], scaled=None, eta_cut={})
    inv = battery(lad, firing, cfg, fake)
    return {k: inv[k] for k in ("I4_insulate_first", "I9_mechanical", "I11_crossfire")}


def min_diameter(inp=None, n_scan=0, tol_mm=1.0, r_lo=None, r_hi=None, log=None):
    """The smallest rotor with z >= 1 + m that also passes I4 (at the insulation g_v for V_ceil), I9, I11
    and I12. 1-D bisection in C_max via r_out at that g_v [ME]; H-SYN2 (monotone segment) is checked on
    the bisection's own points; on a violation the scan answer is returned (SYNTH-SCAN-ONLY)."""
    t0 = time.time()
    lad0, firing = sized(inp)
    m = firing["margin"]
    target = 1.0 + m
    gins = g_v_insulation(firing)
    base = dict(inp or {})
    if gins is not None:
        base["g_vMm"] = gins
    r_in = lad0["plates"]["r_inMm"]
    lo = r_lo if r_lo is not None else r_in + 10.0
    hi = r_hi if r_hi is not None else max(lad0["plates"]["r_outMm"] * 1.6, lo + 50.0)
    pts = []

    def f(r):
        z, c, lad = _z_at_rout(base, r, log)
        pts.append(dict(r_outMm=r, C_max_pF=lad["ladder"]["C_max"]["value"], z=z, converged=c,
                        dia_mm=lad["rotor_dia_mm"]))
        return z if c else float("nan")
    zlo, zhi = f(lo), f(hi)
    note = ""
    if not (zhi >= target):
        return PE._jsonable(dict(objective="min_diameter", found=False, points=pts, g_vMm=base.get("g_vMm"),
                                 note=f"z < {target:.2f} even at r_out {hi:.0f} mm", time_s=time.time() - t0))
    if zlo >= target:
        r_star = lo; note = "already pumps at the lower search bound"
    else:
        a, b = lo, hi
        while b - a > tol_mm:
            mid = 0.5 * (a + b)
            if f(mid) >= target:
                b = mid
            else:
                a = mid
        r_star = b
    # H-SYN2: z monotone (non-decreasing) in C_max over the bisection points
    sp = sorted([p for p in pts if p["converged"]], key=lambda p: p["C_max_pF"])
    mono = all(sp[i + 1]["z"] >= sp[i]["z"] - 1e-12 for i in range(len(sp) - 1))
    scan = None
    if n_scan or not mono:
        n = max(n_scan, 15)
        rs = list(np.linspace(lo, hi, n))
        scan = []
        for r in rs:
            z, c, lad = _z_at_rout(base, r, log)
            scan.append(dict(r_outMm=float(r), C_max_pF=lad["ladder"]["C_max"]["value"], z=z, converged=c))
        if not mono:
            ok = [s for s in scan if s["converged"] and s["z"] >= target]
            r_star = min(s["r_outMm"] for s in ok) if ok else None
            note = "SYNTH-SCAN-ONLY: z not monotone in C_max on the bisected segment"
    # the analytic constraints (I4/I9/I11) at r_star; I9 caps r_out from above, I11 from below
    geo = _geom_checks(base, r_star) if r_star else {}
    bind_geom = [k for k, v in geo.items() if v["status"] == FAIL]
    r_final = r_star
    if r_star and "I11_crossfire" in bind_geom and DS is not None:
        # I11 overlap (d_ball + 2 g_lat)/r_gap < SG3b-BS3 spacing: r_out >= that / r_gap_frac  [OC] closed form
        r11 = (firing["d_ballMm"] + 2 * firing["g_latMm"]) / math.radians(DS.SG3B_BS3_SPACING_DEG) / firing["r_gap_frac"]
        r_final = max(r_star, math.ceil(r11 * 10 + 1e-9) / 10.0 + 0.1)
        geo = _geom_checks(base, r_final)
        bind_geom = [k for k, v in geo.items() if v["status"] == FAIL]
    # H-SYN3 + I12: the verdict is an exact run with the full battery at the result
    final = None
    if r_final:
        final = evaluate(_with(base, r_outMm=r_final), with_strip=False, with_twins=False, log=log)
    ok = bool(final and final["converged"] and final["z"] >= target - 1e-12 and final["feasible"])
    binding = "z >= 1 + m (I3 margin)" if r_final == r_star else "I11_crossfire"
    if final and not final["feasible"]:
        binding = final["blocker"]["item"]
    return PE._jsonable(dict(objective="min_diameter", found=ok, r_outMm=r_final, r_out_z=r_star,
                             g_vMm=base.get("g_vMm", lad0["plates"]["g_vMm"]), target=target,
                             dia_mm=(final["sizing"]["rotor_dia_mm"] if final else None),
                             z=(final["z"] if final else None), binding=binding, monotone=mono,
                             points=pts, scan=scan, final=final, geom=geo, note=note,
                             runs=len(pts) + (len(scan) if scan else 0) + (1 if final else 0),
                             time_s=time.time() - t0))


def max_margin(inp=None, ca_search=False, ca_lo=0.6, ca_hi=2.0, n_golden=8, log=None):
    """The largest z at the stated maximum rotor diameter (r_out = dia_max / (2 (1 + BUS_MARGIN))) -- z is
    non-decreasing in C_max, so the largest permitted r_out; optionally a golden-section search on the
    Ca ratio (the engine's z-optimal Ca vs the ladder's 1.10, D-CA)."""
    t0 = time.time()
    lad0, firing = sized(inp)
    r_out = firing["dia_max_mm"] / (2.0 * (1.0 + PS.BUS_MARGIN))
    base = _with(inp, r_outMm=r_out)
    res = evaluate(base, with_strip=False, with_twins=False, log=log)
    gs = None
    if ca_search:
        phi = (math.sqrt(5) - 1) / 2
        a, b = ca_lo, ca_hi
        pts = []

        def f(x):
            lad, fi = sized(_with(base, ratio_Ca=x))
            z, c = z_of(engine_cfg(lad, fi))
            pts.append(dict(ratio_Ca=x, z=z, converged=c))
            if log:
                log(f"Ca ratio {x:.4f} -> z={z:.5f}")
            return z if c else -1.0
        c_, d_ = b - phi * (b - a), a + phi * (b - a)
        fc, fd = f(c_), f(d_)
        for _ in range(n_golden):
            if fc > fd:
                b, d_, fd = d_, c_, fc
                c_ = b - phi * (b - a); fc = f(c_)
            else:
                a, c_, fc = c_, d_, fd
                d_ = a + phi * (b - a); fd = f(d_)
        xbest = c_ if fc > fd else d_
        gs = dict(ratio_Ca_opt=xbest, z_opt=max(fc, fd), bracket=[a, b], points=pts,
                  ladder_ratio=firing and lad0["choices"]["ratio_Ca"],
                  note="golden-section on z(Ca ratio), exact runs; unimodality assumed [ME]")
    return PE._jsonable(dict(objective="max_margin", r_outMm=r_out, dia_mm=res["sizing"]["rotor_dia_mm"],
                             z=res["z"], margin=res["margin"], feasible=res["feasible"], blocker=res["blocker"],
                             final=res, ca=gs, time_s=time.time() - t0))


def max_rpm(inp=None, log=None):
    """The highest rpm passing I9 (rim <= RIM_HARD at the rotor body) and I12 (overlap time >= strike +
    t1/2 + dwell). Analytic in rpm given the ring t1/2 (rpm-independent: the ring is far faster than the
    rotation [OC]); motor on: C_blk re-sized at the new PRF and I7 re-checked. One confirming exact run."""
    t0 = time.time()
    lad0, firing = sized(inp)
    rh = DS.RIM_HARD if DS else 200.0
    rpm9 = rh / (lad0["rotor_outMm"] * 1e-3) * 60.0 / (2 * math.pi)
    head = evaluate(inp, with_strip=False, with_twins=False, log=log)
    th = [e["t_half_us"] for e in head["engine"].get("episodes", []) if e.get("t_half_us")]
    t_half = max(th) * 1e-6 if th else 0.0
    cfg = engine_cfg(lad0, firing)
    if DS is not None:
        ov = math.radians(DS.overlap_deg(cfg["d_ballMm"], cfg["r_gapMm"], cfg["g_latMm"]))
        need = DS.T_STRIKE_S + t_half + DS.T_COND_S
        rpm12 = ov / need * 60.0 / (2 * math.pi)
    else:
        rpm12 = float("inf")
    rpm_max = math.floor(min(rpm9, rpm12) * (1 - 1e-9))
    binding = "I9_mechanical" if rpm9 <= rpm12 else "I12_resonant_timing"
    conf = evaluate(_with(inp, rpm=float(rpm_max)), with_strip=False, with_twins=False, log=log)
    return PE._jsonable(dict(objective="max_rpm", rpm=rpm_max, rpm_I9=rpm9, rpm_I12=rpm12, binding=binding,
                             t_half_us=t_half * 1e6, confirm=conf, z=conf["z"], feasible=conf["feasible"],
                             time_s=time.time() - t0))


def solve(objective, inp=None, log=None, **kw):
    if objective in DISABLED_OBJECTIVES:
        return dict(objective=objective, disabled=True, reason=DISABLED_OBJECTIVES[objective])
    fn = dict(min_diameter=min_diameter, max_margin=max_margin, max_rpm=max_rpm).get(objective)
    if fn is None:
        raise KeyError(f"unknown objective {objective!r}")
    return fn(inp, log=log, **kw)


def _selftest():
    """On-load self-test (cheap, no engine runs): the defaults split and size, the insulation law gives
    7.0 mm for 21 kV in air, the strip/blocker tables are consistent."""
    lad, firing = sized({})
    cfg = engine_cfg(lad, firing)
    ok = abs(g_v_insulation(firing) - 7.0) < 1e-12
    ok &= cfg["gm_load"] == "ringdown" and cfg["gm_fire"] == "ringdown" and not cfg["motor"]
    ok &= abs(cfg["C1max"] - lad["ladder"]["C_max"]["value"]) < 1e-12 and abs(cfg["r_gapMm"] - 387.0) < 1e-12
    ok &= len(STRIP) == 4 and set(DISABLED_OBJECTIVES) == {"max_eta", "min_belt_power"}
    if not ok:
        raise AssertionError("pump_synth on-load self-test FAILED")
    return True


SELFTEST_OK = _selftest()

if __name__ == "__main__":
    import json
    r = evaluate({}, log=print)
    print(json.dumps(dict(z=r["z"], strip=r["strip"], blocker=r["blocker"], times=r["times"],
                          inv={k: (v["status"], v["detail"]) for k, v in r["invariants"].items()}), indent=1))
