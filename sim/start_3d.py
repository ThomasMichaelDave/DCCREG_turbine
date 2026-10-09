"""sim/start_3d.py -- the magnetic pump's start with the utrons in 3-D (sim/utron-3d-findings.md, the ledger's model
check 34): the record's start (sim/parts-first-cut-findings.md §3) re-run with each 3-D utron set in place of the
record's 2-D one. Writes sim/start_3d_results.json; the findings are sim/start-3d-findings.md.

What runs, for each utron set (sim/utron_3d_results.json "variants"), with the 22 mF bypass (PROPOSED) throughout:
1. the steady state: the record's seed (30 % of Psi_s, 60 cycles), as sim/ah_steady_cusp.py runs it;
2. the seed threshold: a seed of frac * Psi_s / L_max in every coil, 40 cycles (sim/parts_first_cut.py SEED_FRACS and
   three larger ones, since a weaker pump needs more);
3. the K4 kick (470 uF at 9 V dumped across La through the SCR) at full speed, at the four rotor phases;
4. K4 below full speed: the speed from which it starts the pump at both phases the parts study ran (80 cycles);
5. a running pump slowing down: does a large seed (60 % of Psi_s, the parts study's proxy) hold at a lower speed?

Each run is sim/parts_first_cut.mag_job, unchanged, with the deck's three utron inputs (prof, tau, L_max) replaced as
sim/utron_3d.py replaces them [IR], and La / Lb held at the record's 0.146 H: the parts' first cut is trimmed to it
(sim/parts-first-cut-findings.md §1) [IR]. The utron's own copper R stays (tau = L_al / R_per_n2, R_per_n2 the
record's).
"It starts": the AH coil reaches half of its own utron set's steady peak [IR]. The parts study's 225 A-turns is half
of the 450 the pick was sized to, and a 3-D set's steady peak with the bypass is 226-251 A-turns. A pump that does not
start dies to about 0, except one slow start at a set's edge (sim/start-3d-findings.md §1). Below full speed, "it
runs" is the parts study's own (> 50 A-turns over the last 4 of 80 cycles).
The gate: the record's own set reproduces sim/parts_first_cut_results.json (its threshold pair, K4 at two phases, the
speed rows at 950 and 1000 rpm relative, and the hold at 700 and 800).
Tags (CONVENTIONS.md §1): [OC] derivable physics; [IR] a modelling choice; [RH] heuristic, not load-bearing.
Usage: python3 sim/start_3d.py [--procs 4] [--cache FILE]   (needs ngspice; about 20 minutes on 2 processes)
--cache: a JSON-lines file of finished runs, appended as they finish and read instead of re-running them.
"""
import argparse
import json
import os
import sys
import time
from multiprocessing import Pool

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import parts_first_cut as P        # noqa: E402  (mag_job, the kick's constants, t_on_cap)
import rotor_parts_duty as RP      # noqa: E402  (the pick's kwargs)

SRC = {"utron_3d": "sim/utron_3d_results.json", "parts": "sim/parts_first_cut_results.json",
       "op": "sim/pole_design_variants_op.json"}
SETS = ("record", "frame_a", "cyl_one_reversed", "cyl_aiding")
SEED_FRACS = P.SEED_FRACS + (0.35, 0.40, 0.50)
K4 = P.KICKS[3]                                      # ("K4 470 uF at 9 V (a 9 V cell)", "cap", 470.0, 9.0, None, None)
SPEED_HZ = (95.0, 100.0, 105.0, 110.0, 115.0)        # 950-1150 rpm relative; 120 Hz is the full-speed run
SPEED_PHASES = (1.0, 1.5)                            # as sim/parts_first_cut.py's speed rows
HOLD_HZ = (75.0, 80.0, 85.0, 90.0, 95.0, 100.0)      # a running pump slowing down (the record holds from 80 Hz)
GATE = dict(seeds=(0.14, 0.16), k4_phases=(1.0, 1.5), speed_hz=(95.0, 100.0), hold_hz=(70.0, 80.0))


def load(key):
    return json.load(open(os.path.join(os.path.dirname(HERE), SRC[key])))


def utron_sets():
    V = load("utron_3d")["variants"]
    return {k: dict(V[k], la_ratio=RP.LA_RATIO * V["record"]["L_max"] / V[k]["L_max"]) for k in SETS}


def _job(args):
    """one sim/parts_first_cut.mag_job with a utron set in the deck (sim/utron_3d.py _deck_one's override)."""
    name, var, job = args
    base = RP._kw
    if var.get("replace"):
        def kw_override(tf, _v=var):
            kw = base(tf)
            kw.update(prof=_v["prof"], tau=_v["tau"], L_max=_v["L_max"], seed=RP.SEED_FRAC * kw["psi_s"] / _v["L_max"],
                      la_ratio=_v["la_ratio"])
            return kw
        RP._kw = kw_override
    t = time.time()
    try:
        r = P.mag_job(dict(job))
    finally:
        RP._kw = base
    r["name"], r["wall_s"] = name, time.time() - t
    return r


def jobs(sets, la_rec):
    J = []
    kd = lambda ph: dict(kind="cap", V0=K4[3], pol=1, phase=ph, into="a", label=None, C_mF=K4[2] * 1e-3,
                         t_on=P.t_on_cap(K4[2], la_rec))
    for s, var in sets.items():
        gate = s == "record"
        J.append((f"{s}|steady", var, dict(bypass_mF=P.C_BYP_MF)))
        for f in (GATE["seeds"] if gate else SEED_FRACS):
            J.append((f"{s}|seed|{f:.2f}", var, dict(seed_frac=f, n_cyc=40, bypass_mF=P.C_BYP_MF)))
        for ph in (GATE["k4_phases"] if gate else P.KICK_PHASES):
            J.append((f"{s}|K4|{ph:g}", var, dict(seed_frac=0.0, n_cyc=40, bypass_mF=P.C_BYP_MF, kick=kd(ph))))
        for F in (GATE["speed_hz"] if gate else SPEED_HZ):
            for ph in SPEED_PHASES:
                J.append((f"{s}|speed|{F:g}|{ph:g}", var, dict(seed_frac=0.0, n_cyc=P.N_CYC_SPEED,
                                                                 bypass_mF=P.C_BYP_MF, kick=kd(ph), F_Hz=F)))
        for F in (GATE["hold_hz"] if gate else HOLD_HZ):        # as sim/parts_first_cut.py's speed|hold rows
            J.append((f"{s}|hold|{F:g}", var, dict(seed_frac=P.HOLD_FRAC, n_cyc=P.N_CYC_SPEED, bypass_mF=P.C_BYP_MF,
                                                   F_Hz=F)))
    return J


def row(q, half):
    if "error" in q:
        return dict(error=q["error"])
    out = dict(AH_AT=q["AHt_AT_max"], z_early=q["z_early"], retried=q["retried"], starts=q["AHt_AT_max"] > half)
    if "runs" in q:
        out["runs"] = q["runs"]
    if "kick" in q:
        out["kick_E_out_mJ"] = q["kick"].get("E_out_mJ")
    return out


def gate(R, parts):
    """the record's set against sim/parts_first_cut_results.json [IR: the same deck, so it must agree closely]."""
    th = {r_["frac"]: r_ for r_ in parts["kick"]["thresholds"]["bypass"]["table"]}
    runs = {r_["name"]: r_ for r_ in parts["kick"]["runs"]}
    sp = {(r_["F_Hz"], r_["phase_cycles"]): r_ for r_ in parts["kick"]["speed"]["rows"]
          if r_["what"] == "K4" and r_["diodes"] == "rec"}
    hd = {r_["F_Hz"]: r_ for r_ in parts["kick"]["speed"]["rows"] if r_["what"] == "hold"}
    G = []
    for f in GATE["seeds"]:
        a, b = R[f"record|seed|{f:.2f}"], th[f]
        G.append(dict(what=f"seed {f:.2f}", here=a["AHt_AT_max"], record=b["AH_AT"], agree=_agree(a["AHt_AT_max"], b["AH_AT"])))
    for ph in GATE["k4_phases"]:
        a, b = R[f"record|K4|{ph:g}"], runs[f"kick|{K4[0]}|+|{ph:g}"]
        G.append(dict(what=f"K4 at phase {ph:g}", here=a["AHt_AT_max"], record=b["AH_AT"],
                      agree=_agree(a["AHt_AT_max"], b["AH_AT"])))
    for F in GATE["speed_hz"]:
        for ph in SPEED_PHASES:
            a, b = R[f"record|speed|{F:g}|{ph:g}"], sp[(F, ph)]
            G.append(dict(what=f"K4 at {F * 10:.0f} rpm relative, phase {ph:g}", here=a["AHt_AT_max"], record=b["AH_AT"],
                          runs_here=a["runs"], runs_record=b["runs"],
                          agree=_agree(a["AHt_AT_max"], b["AH_AT"]) and a["runs"] == b["runs"]))
    for F in GATE["hold_hz"]:
        a, b = R[f"record|hold|{F:g}"], hd[F]
        G.append(dict(what=f"hold at {F * 10:.0f} rpm relative", here=a["AHt_AT_max"], record=b["AH_AT"],
                      runs_here=a["runs"], runs_record=b["runs"],
                      agree=_agree(a["AHt_AT_max"], b["AH_AT"]) and a["runs"] == b["runs"]))
    return dict(rows=G, all_agree=all(g["agree"] for g in G))


def _agree(x, y):
    """the same verdict and, for a started pump, the same A-turns within 0.1 % [IR]."""
    if x is None or y is None:
        return False
    if max(x, y) < 1.0:                                           # both died
        return True
    return abs(x - y) <= 1e-3 * max(abs(x), abs(y))


def summarise(R, sets):
    S = {}
    for s in sets:
        st = R[f"{s}|steady"]
        half = 0.5 * st["AHt_AT_max"]
        seeds = sorted(k for k in R if k.startswith(f"{s}|seed|"))
        rows = {float(k.split("|")[2]): row(R[k], half) for k in seeds}
        ok = [f for f, q in rows.items() if q.get("starts") is True]
        no = [f for f, q in rows.items() if q.get("starts") is False]
        k4 = {float(k.split("|")[2]): row(R[k], half) for k in R if k.startswith(f"{s}|K4|")}
        spd = {}
        for k in R:
            if k.startswith(f"{s}|speed|"):
                _, _, F, ph = k.split("|")
                spd.setdefault(float(F), {})[float(ph)] = row(R[k], half)
        all_ph = [F for F, q in spd.items() if all(v.get("runs") for v in q.values())]
        hold = {float(k.split("|")[2]): row(R[k], half) for k in R if k.startswith(f"{s}|hold|")}
        held = None                                             # the lowest speed above which every speed holds
        for F in sorted(hold, reverse=True):
            if not hold[F].get("runs"):
                break
            held = F
        lost = [F for F, q in hold.items() if q.get("runs") is False]
        # from which speed K4 starts it at every phase run: the lowest speed above which every speed runs (120 Hz is
        # the full-speed set of four phases)
        from_hz = None
        if all(v.get("starts") for v in k4.values()):
            from_hz = 120.0
            for F in sorted(spd, reverse=True):
                if F in all_ph:
                    from_hz = F
                else:
                    break
        S[s] = dict(steady=dict(AH_AT_max=st["AHt_AT_max"], z_early=st["z_early"], P_belt_W=st["P_belt_W"],
                                AH_I_mean_A=st["AHt_I_mean_A"]),
                    start_criterion_AT=half,
                    seed=dict(rows={f"{f:.2f}": q for f, q in sorted(rows.items())}, min_start=min(ok) if ok else None,
                              max_no_start=max(no) if no else None),
                    K4_full_speed={f"{ph:g}": q for ph, q in sorted(k4.items())},
                    K4_all_phases_start=all(v.get("starts") for v in k4.values()),
                    K4_speed={f"{F * 10:.0f}": {f"{ph:g}": v for ph, v in sorted(q.items())} for F, q in sorted(spd.items())},
                    K4_every_phase_from_rpm_relative=from_hz * 10 if from_hz else None,
                    hold={f"{F * 10:.0f}": q for F, q in sorted(hold.items())},
                    holds_from_rpm_relative=10 * held if held else None,
                    stops_at_rpm_relative=10 * max(lost) if lost else None)
    return S


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--procs", type=int, default=4)
    ap.add_argument("--cache", help="a JSON-lines file of finished runs (appended; read instead of re-running)")
    a = ap.parse_args()
    t0 = time.time()
    sets = utron_sets()
    la_rec = RP.LA_RATIO * load("op")["designs"][RP.PICK]["best"]["L_group_H"]
    J = jobs(sets, la_rec)
    R = {}
    if a.cache and os.path.exists(a.cache):
        for ln in open(a.cache):
            if ln.strip():
                q = json.loads(ln)
                R[q["name"]] = q
    todo = [j for j in J if j[0] not in R]
    print(f"{len(J)} runs, {len(J) - len(todo)} from the cache, on {a.procs} processes", flush=True)
    with Pool(a.procs) as pool:
        for r in pool.imap_unordered(_job, todo, chunksize=1):
            R[r["name"]] = r
            if a.cache:
                with open(a.cache, "a") as fh:
                    fh.write(json.dumps(r) + "\n")
            v = r.get("AHt_AT_max")
            print(f"[{len(R)}/{len(J)}] {r['name']}: " + (r["error"] if "error" in r else
                  f"AH {v:.1f} A-t, z_early {r['z_early']}, {r['wall_s']:.0f} s"), flush=True)
    names = {j[0] for j in J}
    R = {k: v for k, v in R.items() if k in names}
    parts = load("parts")
    out = dict(
        sources=SRC,
        tags={"the deck and its inputs": "IR (sim/parts_first_cut.mag_job, sim/rotor_parts_duty._kw)",
              "the utron sets": "IR (sim/utron_3d.py: the 3-D solves, the record's grid)",
              "La / Lb held at 0.146 H": "IR (the parts' first cut)",
              "it starts: half the set's own steady peak": "IR"},
        La_H=la_rec,
        utron_sets={k: dict(name=v["name"], kappa=v["kappa"], L_max_H=v["L_max"], tau_s=v["tau"], la_ratio=v["la_ratio"])
                    for k, v in sets.items()},
        gate=gate(R, parts),
        sets=summarise(R, sets),
        raw={k: {q: v for q, v in r.items() if q not in ("job", "kw")} for k, r in sorted(R.items()) if k in names},
        run_time_s=time.time() - t0)
    json.dump(out, open(os.path.join(HERE, "start_3d_results.json"), "w"), indent=1)
    print("gate:", "PASS" if out["gate"]["all_agree"] else "FAIL")
    for g in out["gate"]["rows"]:
        print("  ", g)
    for s, q in out["sets"].items():
        print(s, f"steady {q['steady']['AH_AT_max']:.1f} A-t; seed from {q['seed']['min_start']} (no start at "
                 f"{q['seed']['max_no_start']}); K4 all phases at full speed: {q['K4_all_phases_start']}; every phase from "
                 f"{q['K4_every_phase_from_rpm_relative']} rpm relative; a running pump holds from "
                 f"{q['holds_from_rpm_relative']} (stops at {q['stops_at_rpm_relative']})")
    print(f"done in {time.time() - t0:.0f} s")


if __name__ == "__main__":
    main()
