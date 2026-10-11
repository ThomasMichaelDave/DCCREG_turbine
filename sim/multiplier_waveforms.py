#!/usr/bin/env python3
"""sim/multiplier_waveforms.py -- the multiplier as laid out, running: every node's voltage and every diode's current
through one cycle in steady state, and the rings' charge-up from the seed, for the 3-D viewer
(tools/step-viewer/layout.html) and as the record of what each part does when.

The deck is sim/multiplier_layout.py's (sim/integrated_multiplier.py's proposal as built: ideal diodes ND, C1 / C2 in
phase, chain 2 reversed, one ring stage per chain) at the layout's picks (sim/multiplier_layout_results.json strays):
C3-C6 180 pF, the layout's strays on the new nodes and on nodes 1-4, the clamp strings of 60 parts (V_op 11.94 kV),
from the consistent 1 kV seed. A 0 V source in series with each diode reads its current [OC: it changes nothing; G1].
One cycle (1 / 120 s) is one vane pitch of relative rotation, 60 deg: the rotor turns +30 deg and the counter-rotor
-30 deg; at its start the vanes are aligned and C1 = C2 = C_max (the solids' rotor angle 0).
Writes sim/multiplier_waveforms_results.json; the findings are sim/multiplier-waveforms-findings.md.
Gates: G1 the rings as the layout study's 'clamps of 60' run; G2 the steady cycle's charge balance (each ring stage's
diode passes its ring's leakage); G3 one run at twice the steps.
Tags (CONVENTIONS.md §1): [OC] the circuit's arithmetic; [IR] the deck's choices (sim/integrated_multiplier.py); [RH] its
inputs (the layout's strays, sim/multiplier-layout-findings.md §6).
Usage: python3 sim/multiplier_waveforms.py   (needs ngspice; about three minutes)
"""
import copy
import json
import math
import os
import sys
import time
from multiprocessing import Pool

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
import integrated_multiplier as IM     # noqa: E402  (the proposal's deck, the as-built set, V_op, the rings' rule)

OUT_JSON = os.path.join(HERE, "multiplier_waveforms_results.json")
LAYOUT = json.load(open(os.path.join(HERE, "multiplier_layout_results.json")))
SRC = {"deck": "sim/integrated_multiplier.py topology('proposal'), build, spice, seeds; as sim/multiplier_layout.py run_deck",
       "picks": "sim/multiplier_layout_results.json strays: deck_strays_pF, cp_pF, picks.clamp_parts, runs['layout, clamps "
                "of 60']; C3-C6: sim/integrated_multiplier_results.json pick",
       "k_null": "sim/hub_rings_build_results.json record.k_kV_cm_per_kV (IM.K_NULL); the can's ratio: "
                 "sim/multiplier_layout_results.json hub.k_ratio"}
N_OUT = 360                  # points of the steady cycle kept (1 deg of the relative rotation each, 6 ms / 360)
NODES = ("1", "2", "3", "4", "l1", "l2", "r1", "r2", "xa", "xb", "ea", "eb", "s")


def job_of(steps=IM.STEPS):
    sy = LAYOUT["strays"]
    n_z = sy["picks"]["clamp_parts"]["value"]
    run = [r for r in sy["runs"] if r["tag"] == f"layout, clamps of {n_z}"][0]
    return dict(cl=json.load(open(os.path.join(HERE, "integrated_multiplier_results.json")))["pick"]["C3_C6_pF"] * 1e-12,
                strays={k: v * 1e-12 for k, v in sy["deck_strays_pF"].items()},
                cp={k: v * 1e-12 for k, v in sy["cp_pF"].items()}, n_cyc=run["n_cyc"], vop=IM.V_OP * n_z / 66.0, n_z=n_z,
                steps=steps, ref=dict(V_A_kV=run["V_A_kV"], V_B_kV=run["V_B_kV"], n_cyc=run["n_cyc"]))


def deck(job, last=False):
    """sim/multiplier_layout.py run_deck's netlist. last: the same deck writing only its last cycle, at every solver
    step (no interpolation)."""
    Sab = copy.deepcopy(IM.SET_AB)
    Sab["Cp"] = dict(Sab["Cp"], **job["cp"])
    el = IM.topology("proposal", cl=job["cl"], c7=IM.C_CW, s_new=0.0)
    el += [("C", f"Cn_{n}", n, "0", c) for n, c in sorted(job["strays"].items()) if c > 0]
    n = job["n_cyc"]
    txt, vecs, pk = IM.build(el, Sab, phase="in", model="ND", ic=IM.seeds("proposal", 1000.0), n_cyc=n,
                             steps=job["steps"], vop=job["vop"])
    diodes = [(e[1], e[2], e[3]) for e in el if e[0] == "D"]
    if not last:
        return txt, vecs, diodes, Sab
    out = []
    for ln in txt.split("\n"):
        if ln.startswith("tran "):
            w = ln.split()
            w[3] = f"{(n - 1) * IM.T:.6e}"                     # tstart: the last cycle only
            out.append(" ".join(w))
        elif ln.startswith(".options"):
            out.append(ln.replace(" interp", ""))
        else:
            out.append(ln)
    return "\n".join(out), vecs, diodes, Sab


def caps_of(txt):
    """every linear capacitor of the netlist as (node, node, F), the varicaps' constant parts (C1v0, C2v0) included."""
    out = []
    for ln in txt.split("\n"):
        w = ln.split()
        if len(w) == 4 and w[0][0] in "Cc" and not w[1].startswith("e_"):
            try:
                out.append((w[1], w[2], float(w[3])))
            except ValueError:
                pass
    return out


def kcl(t, V, caps, Sab, I_clamp, edges):
    """each diode's charge in each bin from Kirchhoff's current law [OC]: each chain is one path of diodes from the shaft
    to its ring, so working in from the ring every diode passes what the nodes beyond it took up (C dV over the bin,
    C(t) V for the varicaps, the rings' leakage) and the clamp at its varicap node took. The node voltages are smooth;
    an ideal diode's own current at a solver step is not (it turns on within one step), so it is never read."""
    Ve = {nd: np.interp(edges, t, y) for nd, y in V.items()}
    Ve["0"] = np.zeros_like(edges)
    w = 2 * math.pi * IM.F
    cmin, cmax = Sab["cmin"], Sab["cmax"]
    Ct = cmin + (cmax - cmin) * 0.5 * (1 + np.cos(w * edges))       # C1 = C2 (in phase), C_max at the cycle's start

    def took(n):                                                    # out of node n into its capacitors, per bin
        q = np.zeros(len(edges) - 1)
        for a, b, C in caps:
            if a == n:
                q += C * np.diff(Ve[a] - Ve[b])
            elif b == n:
                q += C * np.diff(Ve[b] - Ve[a])
        if n in ("1", "4"):                                         # the varicap's part beyond its C_max (C1v / C2v)
            q += np.diff((Ct - cmax) * (Ve[n] - Ve["s"]))
        return q
    dt = np.diff(edges)
    leak = {r: 0.5 * (Ve[r][1:] + Ve[r][:-1]) * dt / IM.R_LEAK for r in ("ea", "eb")}
    Q = {}
    Q["D10"] = took("eb") + leak["eb"]                              # chain 1 and ring B: 0 -D1-> 2 ... 4 -D9-> xb -D10-> eb
    Q["D9"] = Q["D10"] + took("xb")
    Q["D7"] = Q["D9"] + I_clamp["z4"] + took("4")
    Q["D6"] = Q["D7"] + took("l2")
    Q["D3"] = Q["D6"] + took("r1")
    Q["D1"] = Q["D3"] + took("2")
    Q["D12"] = -took("ea") - leak["ea"]                             # chain 2 and ring A: ea -D12-> xa -D11-> 1 ... 3 -D2-> 0
    Q["D11"] = Q["D12"] - took("xa")
    Q["D8"] = Q["D11"] + I_clamp["z1"] - took("1")
    Q["D5"] = Q["D8"] - took("r2")
    Q["D4"] = Q["D5"] - took("l1")
    Q["D2"] = Q["D4"] - took("3")
    return Q, Ve


def bins(t, y, t0, T, n):
    """y's mean over each of n equal bins of [t0, t0 + T], from its integral over the solver's own steps."""
    q = np.concatenate([[0.0], np.cumsum(0.5 * (y[1:] + y[:-1]) * np.diff(t))])
    edges = t0 + T * np.arange(n + 1) / n
    Q = np.interp(edges, t, q)
    return (np.diff(Q) / (T / n)).tolist()


def run(job):
    """the start-up (every cycle's statistics, interpolated output) or, job['last'], the last cycle in full."""
    t0 = time.time()
    last = job.get("last", False)
    txt, vecs, diodes, Sab = deck(job, last)
    raw, rt, err = IM.spice(txt, job["n_cyc"])
    if raw is None or rt is None:
        return dict(job=job, done=False, error=err)
    T, n = IM.T, job["n_cyc"]
    t = raw[:, 0]
    c = {v: raw[:, 2 * i + 1] for i, v in enumerate(vecs)}
    V = {nd: c[f"v({nd})"] for nd in NODES}
    out = dict(job={k: v for k, v in job.items() if k not in ("strays", "cp")}, done=True, run_s=round(time.time() - t0, 1),
               reltol=rt)
    if not last:
        cyc = [(t >= k * T - 1e-12) & (t < (k + 1) * T - 1e-12) for k in range(n)]
        out["per_cycle"] = {nd: dict(mean=[float(V[nd][m].mean()) for m in cyc], min=[float(V[nd][m].min()) for m in cyc],
                                     max=[float(V[nd][m].max()) for m in cyc]) for nd in NODES}
        s8 = t >= (n - 8) * T - 1e-12
        out.update(V_A_kV=float(V["ea"][s8].mean() / 1e3), V_B_kV=float(V["eb"][s8].mean() / 1e3))
        gap = V["eb"] - V["ea"]
        gk = [float(gap[m].mean() / 1e3) for m in cyc]
        fin = float(np.mean(gk[-3:]))
        hit = [j for j, x in enumerate(gk) if abs(x) >= 0.95 * abs(fin)]
        out["rings"] = dict(gap_per_cycle_kV=gk, settled=IM.settled(gk), cycles_to_95pc=(hit[0] + 1) if hit else None)
        return out
    t_a = (n - 1) * T
    keep = t >= t_a - 1e-15
    t = t[keep]
    V = {v[2:-1]: c[v][keep] for v in vecs if v.startswith("v(") and not v.startswith("v(e_")}
    edges = t_a + T * np.arange(N_OUT + 1) / N_OUT
    zq = {"z1": c["i(Vz1)"][keep], "z4": -c["i(Vz4)"][keep]}      # each clamp positive when it clamps (IM.run)
    Iz = {z: np.array(bins(t, y, t_a, T, N_OUT)) * (T / N_OUT) for z, y in zq.items()}   # its charge per bin
    Qd, Ve = kcl(t, V, caps_of(txt), Sab, Iz, edges)
    Qd.update(Iz)
    grid = edges[:-1]
    out["cycle"] = dict(theta_rel_deg=(np.arange(N_OUT) * 60.0 / N_OUT).tolist(),
                        V={nd: Ve[nd][:-1].tolist() for nd in NODES},
                        I={nm: (q / (T / N_OUT)).tolist() for nm, q in Qd.items()})
    w = 2 * math.pi * IM.F
    cmin, cmax = Sab["cmin"], Sab["cmax"]
    out["cycle"]["C1_pF"] = [(cmin + (cmax - cmin) * 0.5 * (1 + math.cos(w * (x - t_a)))) * 1e12 for x in grid]
    dev = {}
    ends = {nm: (a, k) for nm, a, k in diodes}
    ends.update({"z1": ("1", "0"), "z4": ("0", "4")})
    back, idle = {}, {}
    for nm, q in Qd.items():
        ib = q / (T / N_OUT)
        pk = float(ib.max())
        on = ib > 0.01 * pk if pk > 0 else np.zeros(N_OUT, bool)
        spans, s0 = [], None
        for j in range(N_OUT):
            if on[j] and s0 is None:
                s0 = j
            if s0 is not None and (not on[j] or j == N_OUT - 1):
                spans.append([s0 * 60.0 / N_OUT, (j + (1 if on[j] else 0)) * 60.0 / N_OUT])
                s0 = None
        a, k = ends[nm]
        vak = Ve[a] - Ve[k]
        dev[nm] = dict(anode=a, cathode=k, charge_nC=float(q.sum() * 1e9), I_avg_uA=float(q.sum() / T * 1e6),
                       I_peak_bin_mA=pk * 1e3, conducts_deg=spans, conduction_deg=float(on.sum() * 60.0 / N_OUT),
                       V_reverse_peak_kV=float(-vak.min() / 1e3) if nm.startswith("D") else None)
        if nm.startswith("D") and pk > 0:
            back[nm] = float(-ib.min() / pk)                        # a diode cannot conduct backwards
            rev = (vak[1:] < -50.0) & (vak[:-1] < -50.0)            # nor while reverse biased by 50 V or more
            idle[nm] = float(np.abs(ib[rev]).max() / pk) if rev.any() else 0.0
    out["kcl_checks"] = dict(backward_max=back, reverse_biased_max=idle)
    out["devices"] = dev
    out["V_A_kV"], out["V_B_kV"] = (float(np.trapezoid(V[r], t) / (t[-1] - t[0]) / 1e3) for r in ("ea", "eb"))
    out["ripple_A_V"], out["ripple_B_V"] = float(np.ptp(V["ea"])), float(np.ptp(V["eb"]))
    out["n_steps"] = int(len(t))
    return out


def main():
    t0 = time.time()
    log = lambda s_: print(s_, flush=True)
    job = job_of()
    jobs = [job, dict(job, last=True), dict(job_of(2 * IM.STEPS), last=True)]
    with Pool(3) as p:
        ra, rb, r2 = p.map(run, jobs)
    for r in (ra, rb, r2):
        assert r["done"], r.get("error")
    ref, T = job["ref"], IM.T
    log(f"the layout's deck at its picks: C3-C6 {job['cl'] * 1e12:.0f} pF, clamps of {job['n_z']} (V_op "
        f"{job['vop'] / 1e3:.3f} kV), {job['n_cyc']} cycles: rings {ra['V_A_kV']:+.3f} / {ra['V_B_kV']:+.3f} kV "
        f"({ra['run_s']} s; the last cycle {rb['run_s']} s, {rb['n_steps']} solver steps)")
    g1 = dict(V_A_kV=ra["V_A_kV"], V_B_kV=ra["V_B_kV"], study_V_A_kV=ref["V_A_kV"], study_V_B_kV=ref["V_B_kV"],
              last_cycle_V_A_kV=rb["V_A_kV"], last_cycle_V_B_kV=rb["V_B_kV"],
              ok=bool(max(abs(ra["V_A_kV"] - ref["V_A_kV"]), abs(ra["V_B_kV"] - ref["V_B_kV"]),
                          abs(rb["V_A_kV"] - ra["V_A_kV"]), abs(rb["V_B_kV"] - ra["V_B_kV"])) < 0.01))
    # the steady cycle's charge balance [OC: no DC through a capacitor]: along chain 1 (0 -D1-> 2 -D3-> r1 -D6-> l2 -D7-> 4)
    # and chain 2 (4 ... reversed: 3 -D2-> 0, l1 -D4-> 3, r2 -D5-> l1, 1 -D8-> r2) every diode passes the same charge; at
    # node 4 it leaves through D9 and the clamp z4, at node 1 it arrives through D11 and the clamp z1; each ring stage
    # passes its ring's leakage
    Q = {nm: d["charge_nC"] for nm, d in rb["devices"].items()}
    leak = {"B": rb["V_B_kV"] * 1e3 / IM.R_LEAK * T * 1e9, "A": -rb["V_A_kV"] * 1e3 / IM.R_LEAK * T * 1e9}
    rel = lambda a, b: abs(a - b) / max(abs(a), abs(b), 1e-9)
    checks = {"chain 1: D1 = D3 = D6 = D7": max(rel(Q["D1"], Q[k]) for k in ("D3", "D6", "D7")),
              "chain 2: D2 = D4 = D5 = D8": max(rel(Q["D2"], Q[k]) for k in ("D4", "D5", "D8")),
              "node 4: D7 = D9 + z4": rel(Q["D7"], Q["D9"] + Q["z4"]), "node 1: D8 = D11 + z1": rel(Q["D8"], Q["D11"] + Q["z1"]),
              "ring B's stage: D9 = D10": rel(Q["D9"], Q["D10"]), "ring A's stage: D11 = D12": rel(Q["D11"], Q["D12"])}
    # each ring stage passes its ring's leakage and what the ring still takes up as it creeps toward its level
    ring_vs_leak = {"B": Q["D10"] / leak["B"] - 1.0, "A": Q["D12"] / leak["A"] - 1.0}
    kc = rb["kcl_checks"]
    checks["no diode conducts backwards (of its peak)"] = max(kc["backward_max"].values())
    checks["none conducts while reverse biased by 50 V (of its peak)"] = max(kc["reverse_biased_max"].values())
    g2 = dict(charges_nC=Q, ring_leak_nC=leak, ring_stage_over_leak=ring_vs_leak, worst={k: v for k, v in checks.items()},
              ok=bool(all(v < 0.03 for v in checks.values())))
    # each device's charge against the chain's (the ring stages pass 0.6 % of it, so their own change is noise-sized)
    q_chain = Q["D1"]
    dq = max(abs(r2["devices"][k]["charge_nC"] - Q[k]) / q_chain for k in Q)
    g3 = dict(V_A_kV=r2["V_A_kV"], V_B_kV=r2["V_B_kV"], max_charge_change_of_chain=dq,
              ok=bool(abs(r2["V_A_kV"] - rb["V_A_kV"]) < 0.01 and abs(r2["V_B_kV"] - rb["V_B_kV"]) < 0.01 and dq < 0.005))
    hub = LAYOUT["hub"]
    gap = ra["V_B_kV"] - ra["V_A_kV"]
    out = dict(note=__doc__.split("\n\n")[0], sources=SRC, tags="CONVENTIONS.md §1", job=ra["job"],
               rings=dict(ra["rings"], V_A_kV=ra["V_A_kV"], V_B_kV=ra["V_B_kV"], ripple_A_V=rb["ripple_A_V"],
                          ripple_B_V=rb["ripple_B_V"], E_null_kV_cm=IM.K_NULL * gap,
                          E_null_can_kV_cm=IM.K_NULL * hub["k_ratio"] * gap, k_ratio_can=hub["k_ratio"]),
               devices=rb["devices"], cycle=rb["cycle"], per_cycle=ra["per_cycle"],
               gates=dict(G1_rings=g1, G2_charge_balance=g2, G3_steps=g3), run_s=round(time.time() - t0))
    for nm in sorted((k for k in Q if k.startswith("D")), key=lambda s_: int(s_[1:])) + ["z1", "z4"]:
        d = rb["devices"][nm]
        log(f"  {nm:4s} {d['anode']:>3s} -> {d['cathode']:<3s}: {d['charge_nC']:9.3f} nC a cycle ({d['I_avg_uA']:7.3f} uA), "
            f"bin peak {d['I_peak_bin_mA']:7.4f} mA, conducts {d['conduction_deg']:5.1f} deg "
            f"{[[round(a, 1), round(b, 1)] for a, b in d['conducts_deg']]}"
            + (f", reverse {d['V_reverse_peak_kV']:6.2f} kV" if d["V_reverse_peak_kV"] is not None else ""))
    log(f"rings settled {ra['rings']['settled']}, 95 % at cycle {ra['rings']['cycles_to_95pc']}; ripple "
        f"{rb['ripple_A_V']:.1f} / {rb['ripple_B_V']:.1f} V; the field at the null {out['rings']['E_null_can_kV_cm']:.3f} kV/cm "
        "with the can")
    log(f"G1 the rings vs the study: {g1}")
    log(f"G2 the charge balance: {g2['worst']} -> {g2['ok']}")
    log(f"G3 twice the steps: {g3}")
    json.dump(out, open(OUT_JSON, "w"), indent=1, default=float)
    log(f"wrote {os.path.relpath(OUT_JSON, ROOT)} ({out['run_s']} s)")


if __name__ == "__main__":
    main()
