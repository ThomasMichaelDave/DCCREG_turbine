"""sim/integrated_multiplier.py -- the multiplier stacked into the doubler (the designer's sketch of 2026-10-10) and the
rings' supply taken from it. ngspice. Writes sim/integrated_multiplier_results.json; the findings are
sim/integrated-multiplier-findings.md.

The designer's circuit (the sketch of 2026-10-10, read back and confirmed by the designer):
  the record's doubler (the varicaps C1 / C2 on nodes 1 / 4, Ca 1-2, Cb 3-4, D1 / D2 from the shaft to nodes 2 / 3)
  with each cross diode replaced by a three-diode chain through a two-stage capacitor ladder: C3 (2-l1) and C5 (l1-l2)
  stand on node 2, C4 (3-r1) and C6 (r1-r2) on node 3, and the chains run
      0 -D1-> 2 -D3-> r1 -D6-> l2 -D7-> 4      and      0 -D2-> 3 -D4-> l1 -D5-> r2 -D8-> 1
  (as drawn: positive, every diode pointing away from the shaft; l1 / l2 / r1 / r2 name the sketch's unlabelled dots).
The designer's answers (2026-10-10): D5-D8 and C3-C6 are the new parts; the polarity can go either way; the rings'
supply is to be worked out here; the clamps Z1 / Z4 stay on nodes 1 / 4; C3-C6 are sized here; the rings need the high
voltage, and the doubler and the magnetic pump's Schottky circuit stay on one revolving body (the rotor, as the record:
docs/ledger/DCCREG-design-ledger.md §3.1).

What it runs (every deck: the record's cosine C(theta) between the stack's two solved values, C1 / C2 to the
counter-rotor s, s to the shaft through the reference link, the record's ND and DZ unless real parts are named):
1. topology, on the record's 2-D set (sim/core_field.py: C_min / C_max / Ca of the stack of record, 20 pF a node [RH]):
   - the gate: the record's doubler (sim/core_field_results.json 'free none': z from -1 kV, 12 cycles);
   - the sketch as drawn, over C3-C6: the free gain z, and the clamped levels and reverse peaks at one value;
   - polarity: the bipolar doubler (one chain reversed) over C2's phase against C1, and every mirror-symmetric diode
     set (mirror and negate) on the four-node doubler, in phase and in antiphase;
   - the bipolar ladder (the sketch with chain 2 reversed) in phase and in antiphase.
2. as built (sim/tube_strays_results.json decks.sets['as built']: the solved C1 / C2, Ca, node strays and couplings and
   the rings' strays), ND:
   - the gates: the record's doubler (z) and the record's supply (z at start-up from -10 V; the clamped rings);
   - the proposal: the bipolar ladder continued one stage past each varicap node to its ring -- ring B: C7 (l2-xb),
     D9 4->xb, D10 xb->eb; ring A: C8 (r2-xa), D11 xa->1, D12 ea->xa -- each ring on a smoothing capacitor to the
     shaft, the clamps at the record's V_op: over C3-C6, the free gain and the clamped steady state (the rings, the
     field at the null, the ripple, the reverse peaks and the sticks they take, each capacitor's DC, the clamps, the
     belt, the reference link);
   - its sensitivities: the new nodes' strays, the ring stage's coupling node, its capacitor; and the alternative
     without the ladder (the bipolar doubler with the ring stages);
   - the pick, started from a consistent 1 kV.
3. as built with real HV sticks and clamp strings (sim/diodes_real.py's stick and clamp models, typical, maximum and hot
   leakage): the gain from 10 V and from 1 kV, the smallest seed that starts it (sim/diodes_real.py's rule and
   bisection), the clamped steady state; the record's supply with the same parts as the gate
   (sim/diodes_real_results.json electrostatic_as_built).
4. the in-phase stack's side effects: the reference link's current, a floating counter-rotor, the varicaps' torque.
Gates: the record's 2-D z; the as-built z bare and with the rings' chains, and the rings' levels; the record's supply
with typical sticks (z from 1 kV); every new steady run's energy balance; one run at twice the steps.
Tags (CONVENTIONS.md §1): [OC] derivable physics; [IR] a modelling or engineering choice; [RH] heuristic, not
load-bearing. Never a bare d: g for a gap.
Usage: python3 sim/integrated_multiplier.py [--procs 4] [--only topo ab real side] [--cache FILE]
       (needs ngspice; about two CPU-hours; --cache keeps every finished run in FILE, outside the repository)
"""
import argparse
import itertools
import json
import math
import os
import subprocess
import sys
import tempfile
import time
from multiprocessing import Pool

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
import core_field as CF            # noqa: E402  (the 2-D stack of record, V_op, F, the link)
import diodes_real as DR           # noqa: E402  (the HV stick and clamp-string models, the as-built set, the start rule)

OUT_JSON = os.path.join(HERE, "integrated_multiplier_results.json")
SRC = {
    "sketch": "the designer's sketch and answers, 2026-10-10 (CHANGELOG.md; docs/ledger/DCCREG-design-ledger.md §5.2)",
    "set_2d": "sim/core_field.py design() (sim/air_stack_sizing_results.json thick_vanes, 3 mm, 6 + 6), CPAR 20 pF",
    "gate_2d": "sim/core_field_results.json rows 'free none' (z)",
    "as_built": "sim/tube_strays_results.json decks.sets['as built'] (the solved capacitances), decks.table['as built']",
    "supply": "sim/hub_rings_build_results.json record_supply (n_cw 2, n_cw_a 2, a_ref shaft, c_cw 100 pF, r_leak)",
    "real": "sim/diodes_real.py STICK / stick_params, CLAMP / clamp_params, LEAK, ZLEAK, V_LEAK, ab_verdict, _bisect; "
            "sim/diodes_real_results.json electrostatic_as_built",
    "k_null": "sim/hub_rings_build_results.json record.k_kV_cm_per_kV",
}
F, T = CF.F, 1.0 / CF.F
V_OP = CF.V_OP
K_NULL = DR.K_NULL
SUP = DR.REC_SUP
C_CW = SUP["c_cw"]                 # 100 pF: the record's chain capacitors; the ring stages and smoothing take it [IR]
R_LEAK = SUP["r_leak"]             # 100 GOhm per ring to the shaft (the record's deck)
SET_2D = dict(cmin=CF.CMIN, cmax=CF.CMAX, ca=CF.CA, Cp={n: CF.CPAR for n in "1234"}, Cx={}, Cx_rings={},
              c_e=3e-12, c_gap=2e-12, label="the record's 2-D set (sim/core_field.py)")
SET_AB = dict(DR.AB_SET)
S_NEW = 24.5e-12                   # each new node's stray, as nodes 2 / 3 as built [RH: no stack drawn]
STEPS_GATE = 20000                 # the record's deck (sim/core_field.py deck) for the gates
STEPS = 4000                       # the new runs [IR; the step check below]
OUT_PER_CYCLE = 1000
CACHE = None


# ------------------------------------------------------------------------------------------------ the decks
def topology(kind, cl=200e-12, c7=C_CW, cs=C_CW, s_new=S_NEW, cpl="top", ca=None):
    """the elements of one circuit: ("C", name, a, b, F), ("D", name, anode, cathode), ("R", name, a, b, ohm),
    ("Z", name, node, +1 / -1) a clamp (+1: the node clamped at +V_op, -1: at -V_op). Kinds:
    record      the record's doubler (negative: D1 2->0, D2 3->0, D3 1->3, D4 4->2) and clamps;
    supply      the record's doubler and its rings' supply (sim/core_field.py dc: 2 + 2 stages from the shaft);
    sketch      the designer's circuit as drawn (positive);
    bip_doubler the record's doubler bipolar: side A negative, side B positive (D1 0->2, D4 2->4, D2 3->0, D3 1->3);
    bip_ladder  the sketch with chain 2 reversed (D2 3->0, D4 l1->3, D5 r2->l1, D8 1->r2): side A negative;
    proposal    bip_ladder continued one stage past each varicap node to its ring;
    bip_stages  the bipolar doubler with the same ring stages (no ladder), coupled to nodes 2 / 3."""
    ca = ca or None
    el = [("C", "Ca", "1", "2", ca), ("C", "Cb", "3", "4", ca)]
    lad = [("C", "C3", "2", "l1", cl), ("C", "C4", "3", "r1", cl), ("C", "C5", "l1", "l2", cl),
           ("C", "C6", "r1", "r2", cl)]
    new = lambda nodes: [("C", f"Cn_{n}", n, "0", s_new) for n in nodes if s_new]
    rings = lambda: [("C", "Csa", "ea", "0", cs), ("C", "Csb", "eb", "0", cs), ("R", "Rea", "ea", "0", R_LEAK),
                     ("R", "Reb", "eb", "0", R_LEAK)]
    if kind in ("record", "supply"):
        el += [("D", "D1", "2", "0"), ("D", "D2", "3", "0"), ("D", "D3", "1", "3"), ("D", "D4", "4", "2"),
               ("Z", "z1", "1", -1), ("Z", "z4", "4", -1)]
        if kind == "supply":                            # sim/core_field.py deck, opt dc, n_cw = n_cw_a = 2, a_ref shaft
            el += [("C", "Co1", "4", "m1", C_CW), ("D", "Dc1", "0", "m1"), ("D", "Dp1", "m1", "b1"),
                   ("C", "Cs1", "b1", "0", C_CW), ("C", "Co2", "m1", "m2", C_CW), ("D", "Dc2", "b1", "m2"),
                   ("D", "Dp2", "m2", "eb"), ("C", "Cs2", "eb", "b1", C_CW),
                   ("C", "Coa1", "1", "n1", C_CW), ("D", "Dca1", "n1", "0"), ("D", "Dpa1", "a1", "n1"),
                   ("C", "Csa1", "a1", "0", C_CW), ("C", "Coa2", "n1", "n2", C_CW), ("D", "Dca2", "n2", "a1"),
                   ("D", "Dpa2", "ea", "n2"), ("C", "Csa2", "ea", "a1", C_CW),
                   ("R", "Rea", "ea", "0", R_LEAK), ("R", "Reb", "eb", "0", R_LEAK)]
        return el
    if kind == "sketch":
        return el + lad + new(("l1", "l2", "r1", "r2")) + [
            ("D", "D1", "0", "2"), ("D", "D2", "0", "3"), ("D", "D3", "2", "r1"), ("D", "D4", "3", "l1"),
            ("D", "D5", "l1", "r2"), ("D", "D6", "r1", "l2"), ("D", "D7", "l2", "4"), ("D", "D8", "r2", "1"),
            ("Z", "z1", "1", +1), ("Z", "z4", "4", +1)]
    clamps = [("Z", "z1", "1", -1), ("Z", "z4", "4", +1)]
    if kind in ("bip_doubler", "bip_stages"):
        el += [("D", "D1", "0", "2"), ("D", "D4", "2", "4"), ("D", "D2", "3", "0"), ("D", "D3", "1", "3")] + clamps
        if kind == "bip_stages":
            el += [("C", "C7", "2", "xb", c7), ("D", "D9", "4", "xb"), ("D", "D10", "xb", "eb"),
                   ("C", "C8", "3", "xa", c7), ("D", "D11", "xa", "1"), ("D", "D12", "ea", "xa")]
            el += new(("xa", "xb")) + rings()
        return el
    el += lad + new(("l1", "l2", "r1", "r2")) + [
        ("D", "D1", "0", "2"), ("D", "D3", "2", "r1"), ("D", "D6", "r1", "l2"), ("D", "D7", "l2", "4"),
        ("D", "D2", "3", "0"), ("D", "D4", "l1", "3"), ("D", "D5", "r2", "l1"), ("D", "D8", "1", "r2")] + clamps
    if kind == "proposal":
        kb, ka = {"top": ("l2", "r2"), "mid": ("l1", "r1"), "base": ("2", "3")}[cpl]
        el += [("C", "C7", kb, "xb", c7), ("D", "D9", "4", "xb"), ("D", "D10", "xb", "eb"),
               ("C", "C8", ka, "xa", c7), ("D", "D11", "xa", "1"), ("D", "D12", "ea", "xa")]
        el += new(("xa", "xb")) + rings()
    return el


def bipolar(kind):
    return kind not in ("record", "supply", "sketch")


def seeds(kind, v0):
    """a consistent start [IR]: nodes 1 / 4 at the seed (both at -|v0| for the record, -|v0| / +|v0| for a bipolar
    circuit, both +|v0| for the sketch as drawn), every node a diode chain carries past them at the same level (so no
    diode starts forward biased), the rest at 0."""
    a = abs(v0)
    if kind in ("record", "supply"):
        return {"1": -a, "4": -a}
    if kind == "sketch":
        return {"1": a, "4": a}
    return {"1": -a, "4": a, "xa": -a, "ea": -a, "xb": a, "eb": a}


def stick_counts(el, vr_kV):
    """the sticks per position by the record's x2-rated guidance (sim/diodes_real.py): one where twice the reverse
    peak is within one stick's rating, else two [IR]."""
    return {e[1]: (1 if 2.0 * vr_kV.get(e[1], 0.0) <= DR.STICK_KV else 2) for e in el if e[0] == "D"}


def build(el, S, phase="anti", model="ND", ic=None, n_cyc=12, steps=STEPS, split=True, link=True, cx=None, vop=V_OP,
          ns=None, reltol=1e-5, rings_strays=True):
    """the netlist. el: topology(); S: a capacitance set; phase 'anti' (the record: C2 half a pitch from C1) or 'in';
    model 'ND' (the record's diodes and DZ clamps) or one of DR.ES_MODELS' real ones (HV-typ / HV-max / HV-hot /
    HV-noleak); split: each varicap as a linear part at its t = 0 value plus a charge-defined (C(t) - C(0)) V, so the
    seed is consistent (sim/diodes_real.py split_varicaps) [IR]; link: the reference link (sim/core_field.py R_LINK),
    else the counter-rotor floats on cx to the shaft; ns: sticks per diode position (real parts)."""
    w = 2 * math.pi * F
    s1 = f"(0.5*(1+cos({w:.8e}*time)))"
    s2 = s1 if phase == "in" else f"(0.5*(1-cos({w:.8e}*time)))"
    cmin, cmax = S["cmin"], S["cmax"]
    dC = cmax - cmin
    c10, c20 = cmax, (cmax if phase == "in" else cmin)
    t = ["* sim/integrated_multiplier.py"]
    for k, (node, s, c0) in enumerate((("1", s1, c10), ("4", s2, c20)), 1):
        if split:
            t += [f"C{k}v0 {node} s {c0:.10e}", f"C{k}v {node} s Q='(({cmin:.6e}+{dC:.6e}*{s})-{c0:.10e})*V({node},s)'"]
        else:
            t += [f"C{k}v {node} s Q='({cmin:.6e}+{dC:.6e}*{s})*V({node},s)'"]
    t += [f"Rlink s 0 {CF.R_LINK:g}"] if link else [f"Cxs s 0 {cx:.4e}", "Rxs s 0 1e13"]
    t += [f"Cp{n} {n} 0 {S['Cp'][n]:.6e}" for n in "1234"]
    nodes = {"1", "2", "3", "4", "s"}
    for e in el:
        nodes |= {x for x in e[2:4] if isinstance(x, str)} if e[0] in ("C", "R", "D") else {e[2]}
    nodes.discard("0")
    cx_all = dict(S.get("Cx", {}))
    if rings_strays and {"ea", "eb"} <= nodes:
        cx_all.update(S.get("Cx_rings", {}))
        t += [f"Cea_e ea 0 {S['c_e']:.6e}", f"Ceb_e eb 0 {S['c_e']:.6e}", f"Cgap ea eb {S['c_gap']:.6e}"]
    t += [f"Cx{k.replace(' ', '_')} {k} {v:.6e}" for k, v in cx_all.items() if v > 0 and set(k.split()) <= nodes]
    ca = S["ca"]
    for e in el:
        if e[0] == "C":
            t.append(f"{e[1]} {e[2]} {e[3]} {(e[4] if e[4] is not None else ca):.6e}")
        elif e[0] == "R":
            t.append(f"{e[1]} {e[2]} {e[3]} {e[4]:.6e}")
    ics = {n: 0.0 for n in nodes}
    ics.update(ic or {})
    icv = lambda n: 0.0 if n == "0" else ics.get(n, 0.0)
    real = model != "ND"
    spec = DR.ES_MODELS[model] if real else None
    models = {}
    if not real:
        models["ND"] = ".model ND D(is=1e-9 n=0.005 rs=1e-3 cjo=0)"
        models["DZ"] = f".model DZ D(is=1e-14 n=1 bv={vop:.0f} ibv=1e-6 nbv=1 rs=1e5 cjo=0)"
    leak = spec.get("leak") if real else None
    for e in el:
        if e[0] == "D":
            nm, a, k = e[1], e[2], e[3]
            if not real:
                t.append(f"D_{nm} {a} {k} ND")
                continue
            n_s = (ns or {}).get(nm, 1)
            p = DR.stick_params(n_s, spec.get("vf_k", 1.0))
            if not spec["cj"]:
                p["Cjo"] = 0.0
            p["Tt"] = spec["tt"]
            models[f"DS{n_s}"] = DR.diode_line(f"DS{n_s}", p)
            vd0 = icv(a) - icv(k)
            t += [f"R_{nm} {a} {nm}_j {p['Rs']:.6g}", f"D_{nm} {nm}_j {k} DS{n_s} ic={vd0:.10g}"]
            ics[f"{nm}_j"] = icv(a)
            if leak:
                models[f"DL{n_s}"] = f".model DL{n_s} D(is={DR.LEAK[leak]:.6g} n={DR.V_LEAK / DR.VT:.8g} rs=0 cjo=0)"
                t.append(f"D_{nm}L {a} {k} DL{n_s} ic={vd0:.10g}")
    zs = [e for e in el if e[0] == "Z"]
    if zs and real:
        p = DR.clamp_params(vop, DR.CLAMP_P_I) if vop != V_OP else dict(DR.CLAMP_P)
        if not spec["cj"]:
            p["Cjo"] = 0.0
        models["DZS"] = DR.diode_line("DZS", p)
        if leak:
            models["DZL"] = f".model DZL D(is={DR.ZLEAK[leak]:.6g} n={DR.V_LEAK / DR.VT:.8g} rs=0 cjo=0)"
    for e in zs:
        z, node, sg = e[1], e[2], e[3]
        an, ca_ = (node, f"j{z}") if sg < 0 else (f"j{z}", node)
        t.append(f"V{z} 0 {z} 0")
        if real:
            t += [f"D{z} {an} {ca_} DZS ic={icv(an) - icv(ca_):.10g}", f"R{z} j{z} {z} {p['Rs']:.6g}"]
            if leak:
                t.append(f"D{z}L {node if sg < 0 else z} {z if sg < 0 else node} DZL")
            ics[f"j{z}"] = 0.0
        else:
            t.append(f"D{z} {an.replace('j' + z, z)} {ca_.replace('j' + z, z)} DZ")
    # power integrators: the belt (the varicaps' mechanical input), the clamps, the rings' leakage, the link
    sg = "+" if phase == "in" else "-"
    P = {"belt": f"{dC * 0.5 * w:.6e}*sin({w:.8e}*time)*0.5*(V(1,s)*V(1,s){sg}V(4,s)*V(4,s))"}
    if zs:
        P["clamps"] = "+".join(f"(-V({e[2]})*i(V{e[1]}))" for e in zs)
    if {"ea", "eb"} <= nodes:
        P["leak"] = f"(V(ea)*V(ea)+V(eb)*V(eb))/{R_LEAK:.6e}"
    if link:
        P["link"] = f"V(s)*V(s)/{CF.R_LINK:g}"
    for nd, ex in P.items():
        t += [f"Bp_{nd} 0 e_{nd} I='{ex}'", f"Cp_{nd} e_{nd} 0 1", f"Rp_{nd} e_{nd} 0 1e18"]
        ics[f"e_{nd}"] = 0.0
    t += list(models.values())
    vnodes = sorted(n for n in nodes)
    vecs = [f"v({n})" for n in vnodes] + [f"i(V{e[1]})" for e in zs] + [f"v(e_{nd})" for nd in P]
    ms = T / steps
    t += [".ic" + "".join(f" v({n})={v:g}" for n, v in ics.items()), ".control",
          f"tran {T / OUT_PER_CYCLE:.6e} {n_cyc * T:.6e} 0 {ms:.6e} uic", "wrdata out.dat " + " ".join(vecs), ".endc",
          f".options reltol={reltol:g} abstol=1e-12 vntol=1e-6 gmin=1e-15 maxstep={ms:.4e} method=gear interp", ".end"]
    return "\n".join(t) + "\n", vecs, list(P)


DR.CLAMP_P_I = DR.REC_SUP["Z1"]["I_pk_mA"] * 1e-3     # the record's clamp peak current, the string's trim point


def spice(txt, n_cyc, timeout=14400):
    for rt in (None, 3e-5, 1e-4):                     # a run that stops early is redone looser (sim/diodes_real.py)
        tx = txt if rt is None else txt.replace("reltol=1e-05", f"reltol={rt:g}")
        with tempfile.TemporaryDirectory() as d:
            open(os.path.join(d, "x.cir"), "w").write(tx)
            r = subprocess.run(["ngspice", "-b", "x.cir"], capture_output=True, text=True, timeout=timeout, cwd=d)
            try:
                raw = np.loadtxt(os.path.join(d, "out.dat"))
            except (OSError, ValueError):
                raw = None
        if raw is not None and raw.ndim == 2 and raw[-1, 0] >= 0.99 * n_cyc * T:
            return raw, (rt or 1e-5), ""
    return raw, None, (r.stdout + r.stderr)[-500:]


def _stats(y):
    return dict(mean=float(np.mean(y)), min=float(np.min(y)), max=float(np.max(y)), pp=float(np.max(y) - np.min(y)))


def run(job):
    """one deck: job = dict(kind, set '2d' | 'ab', phase, model, v0, n_cyc, clamp, steps, split, link, cx, topo kw)."""
    j = dict(job)
    kind = j["kind"]
    S = SET_2D if j.get("set", "ab") == "2d" else SET_AB
    el = topology(kind, **j.get("topo", {}))
    if not j.get("clamp", True):
        el = [e for e in el if e[0] != "Z"]
    ic = seeds(kind, j.get("v0", 1000.0))
    phase = j.get("phase", "in" if bipolar(kind) else "anti")
    ns = j.get("ns")
    txt, vecs, pk = build(el, S, phase=phase, model=j.get("model", "ND"), ic=ic, n_cyc=j["n_cyc"],
                          steps=j.get("steps", STEPS), split=j.get("split", True), link=j.get("link", True),
                          cx=j.get("cx"), ns=ns, vop=j.get("vop", V_OP))
    t0 = time.time()
    raw, rt, err = spice(txt, j["n_cyc"])
    out = dict(job=job, run_s=round(time.time() - t0, 1), reltol=rt)
    if raw is None or rt is None:
        out.update(done=False, error=err)
        return out
    t = raw[:, 0]
    c = {v: raw[:, 2 * i + 1] for i, v in enumerate(vecs)}
    n = j["n_cyc"]
    cyc = [(t >= k * T - 1e-12) & (t < (k + 1) * T - 1e-12) for k in range(n)]
    out["done"] = True
    pk1 = [float(max(np.abs(c["v(1)"][m]).max(), np.abs(c["v(4)"][m]).max())) for m in cyc]
    out["V14_peak_per_cycle_kV"] = [p / 1e3 for p in pk1]
    lo = j.get("fit_from", 3)
    k = np.arange(lo, n)
    out["z"] = float(math.exp(np.polyfit(k, np.log(np.maximum(np.array(pk1[lo:n]), 1e-30)), 1)[0]))
    out["z_late"] = float((pk1[-1] / pk1[-6]) ** 0.2) if n > 6 else None
    rings = "v(ea)" in c and "v(eb)" in c
    if rings:
        gap = c["v(eb)"] - c["v(ea)"]
        out["gap_per_cycle_kV"] = [float(gap[m].mean() / 1e3) for m in cyc]
    if not j.get("clamp", True) or j.get("free_only"):
        return out
    win = j.get("window", 8)
    s = t >= (n - win) * T - 1e-12
    ts = t[s]
    dur = ts[-1] - ts[0]
    for nd in pk:
        y = c[f"v(e_{nd})"]
        out[f"P_{nd}_W"] = float((np.interp(ts[-1], t, y) - np.interp(ts[0], t, y)) / dur)
    out["P_other_W"] = out["P_belt_W"] - sum(out.get(f"P_{nd}_W", 0.0) for nd in ("clamps", "leak", "link"))
    vn = {v[2:-1]: c[v][s] for v in vecs if v.startswith("v(") and not v.startswith("v(e_")}
    out["V_kV"] = {nd: _stats(y / 1e3) for nd, y in vn.items() if nd != "s"}
    V = lambda nd: 0.0 if nd == "0" else vn[nd]
    out["VR_pk_kV"] = {e[1]: float(np.max(V(e[3]) - V(e[2])) / 1e3) for e in el if e[0] == "D"}
    out["VC_kV"] = {e[1]: _stats((V(e[2]) - V(e[3])) / 1e3) for e in el if e[0] == "C"}
    zi = {e[1]: e for e in el if e[0] == "Z"}
    for z, e in zi.items():
        i = c[f"i(V{z})"][s] * (1 if e[3] < 0 else -1)
        out[f"I_{z}_avg_uA"] = float(np.mean(i) * 1e6)
        out[f"I_{z}_pk_mA"] = float(np.max(i) * 1e3)
    if j.get("link", True):
        il = vn["s"] / CF.R_LINK
        out["link_mA_rms"] = float(math.sqrt(np.mean(il * il)) * 1e3)
        out["link_mA_pk"] = float(np.max(np.abs(il)) * 1e3)
    else:
        out["V_s_kV"] = _stats(vn["s"] / 1e3)
    # the varicaps' torque on the rotor: the belt's power over the relative angular speed [OC]
    w = 2 * math.pi * F
    dC = S["cmax"] - S["cmin"]
    v1, v4 = vn["1"] - vn["s"], vn["4"] - vn["s"]
    sgn = 1.0 if phase == "in" else -1.0
    p_t = dC * 0.5 * w * np.sin(w * ts) * 0.5 * (v1 * v1 + sgn * v4 * v4)
    omega = 2 * math.pi * CF.RPM / 60.0
    out["torque_mNm"] = _stats(p_t / omega * 1e3)
    if rings:
        va, vb = vn["ea"], vn["eb"]
        g = vb - va
        out["V_A_kV"], out["V_B_kV"] = float(np.mean(va) / 1e3), float(np.mean(vb) / 1e3)
        out["ripple_A_V"], out["ripple_B_V"] = float(np.ptp(va)), float(np.ptp(vb))
        out["E_null_kV_cm"] = float(K_NULL * np.mean(g) / 1e3)
        out["E_null_pp_kV_cm"] = float(K_NULL * np.ptp(g) / 1e3)
        gk = out["gap_per_cycle_kV"]
        out["settled"] = settled(gk)
        fin = float(np.mean(gk[-3:]))
        hit = [i for i, x in enumerate(gk) if abs(x) >= 0.95 * abs(fin)]
        out["cycles_to_95pc"] = (hit[0] + 1) if hit and j.get("from_seed") else None
    return out


def settled(gk):
    """the rings have settled when the gap moved less than 0.1 % over the last 50 cycles [IR]. (sim/tube_strays.py's
    0.3 % over ten cycles passes while a ring still drains through its 100 GOhm at about 0.04 % a cycle.)"""
    return bool(gk and len(gk) > 60 and abs(gk[-1] - gk[-50]) < 1e-3 * abs(gk[-1]))


# ------------------------------------------------------------------------------------------------ the cache
def _key(job):
    return json.dumps(job, sort_keys=True)


def cached(job):
    if CACHE and os.path.exists(CACHE):
        k = _key(job)
        with open(CACHE) as f:
            for line in f:
                q = json.loads(line)
                if q["key"] == k:
                    return q["r"]
    r = run(job)
    if CACHE and r.get("done"):
        with open(CACHE, "a") as f:
            f.write(json.dumps(dict(key=_key(job), r=r)) + "\n")
    return r


def pool_map(jobs, procs, log=print):
    out = []
    with Pool(procs) as p:
        for r in p.imap(cached, jobs):
            j = r["job"]
            log(f"  {j.get('tag', '')} {j['kind']} {j.get('model', 'ND')} {j.get('topo', {})} n {j['n_cyc']}: "
                + (f"z {r['z']:.4f}" if r.get("done") else f"FAILED {r.get('error', '')[-120:]}")
                + (f", A {r['V_A_kV']:.2f} / B {r['V_B_kV']:.2f} kV" if "V_A_kV" in r else "")
                + f" ({r['run_s']:.0f} s)")
            out.append(r)
    return out


def cycles_for(z, v0, extra, floor):
    """sim/tube_strays.py _cycles from the seed's own amplitude: 1.3 x the cycles to grow from |v0| to the clamp at
    gain z, plus extra to settle and measure, never fewer than floor; None where z <= 1 [IR]."""
    if not z or z <= 1.0:
        return None
    return max(floor, int(math.ceil(extra + 1.3 * math.log(V_OP / abs(v0)) / math.log(z))))


# ------------------------------------------------------------------------------------------------ 1. topology
M_MIRROR = {"0": "0", "1": "4", "4": "1", "2": "3", "3": "2"}


def symmetric_sets():
    """every diode set on the four-node doubler (Ca 1-2, Cb 3-4) that maps onto itself under the mirror (1 <-> 4,
    2 <-> 3) with every diode reversed -- the symmetry of a bipolar pump about the shaft [OC]: the classes (0,2)~(0,3),
    (2,4)~(3,1), (0,1)~(0,4), each absent / one way / the other, and the self-mirror pairs (2,3), (1,4)."""
    classes, selfs = [("0", "2"), ("2", "4"), ("0", "1")], [("2", "3"), ("1", "4")]
    for st in itertools.product((0, 1, -1), repeat=5):
        ds = []
        for (a, b), sg in zip(classes, st[:3]):
            if sg:
                an, ka = (a, b) if sg > 0 else (b, a)
                ds += [(an, ka), (M_MIRROR[ka], M_MIRROR[an])]
        for (a, b), sg in zip(selfs, st[3:]):
            if sg:
                ds.append((a, b) if sg > 0 else (b, a))
        if len(ds) >= 3:
            yield ds


def brute_job(arg):
    ds, phase = arg
    el = [("C", "Ca", "1", "2", None), ("C", "Cb", "3", "4", None)] + \
        [("D", f"D{i}", a, b) for i, (a, b) in enumerate(ds)]
    txt, vecs, _ = build(el, SET_2D, phase=phase, ic={"1": -1000.0, "4": 1000.0}, n_cyc=12, steps=3000, split=True)
    raw, rt, err = spice(txt, 12)
    if raw is None or rt is None:
        return dict(diodes=ds, phase=phase, z=None)
    t = raw[:, 0]
    c = {v: raw[:, 2 * i + 1] for i, v in enumerate(vecs)}
    cyc = [(t >= k * T - 1e-12) & (t < (k + 1) * T - 1e-12) for k in range(12)]
    pk = [float(max(np.abs(c["v(1)"][m]).max(), np.abs(c["v(4)"][m]).max())) for m in cyc]
    z = float(math.exp(np.polyfit(np.arange(3, 12), np.log(np.array(pk[3:])), 1)[0]))
    m = cyc[-1]
    lv = {n: [round(float(c[f"v({n})"][m].min() / pk[-1]), 3), round(float(c[f"v({n})"][m].max() / pk[-1]), 3)]
          for n in "1234"}
    bip = lv["1"][1] <= 0.02 and lv["4"][0] >= -0.02 and lv["1"][0] < -0.5 and lv["4"][1] > 0.5
    return dict(diodes=ds, phase=phase, z=z, levels_x_peak=lv, bipolar=bip)


def phase_job(deg):
    """the bipolar doubler with C2 lagging C1 by deg (2-D set, ND, 12 cycles from -1 / +1 kV)."""
    el = [e for e in topology("bip_doubler") if e[0] != "Z"]
    txt, vecs, _ = build(el, SET_2D, phase="in", ic=seeds("bip_doubler", 1000.0), n_cyc=12, steps=STEPS_GATE)
    w = 2 * math.pi * F
    ph = math.radians(deg)
    c20 = SET_2D["cmin"] + (SET_2D["cmax"] - SET_2D["cmin"]) * 0.5 * (1 + math.cos(-ph))
    lines = txt.split("\n")
    s2 = f"(0.5*(1+cos({w:.8e}*time-{ph:.8f})))"
    for i, ln in enumerate(lines):
        if ln.startswith("C2v0 "):
            lines[i] = f"C2v0 4 s {c20:.10e}"
        elif ln.startswith("C2v "):
            lines[i] = (f"C2v 4 s Q='(({SET_2D['cmin']:.6e}+{SET_2D['cmax'] - SET_2D['cmin']:.6e}*{s2})-{c20:.10e})"
                        f"*V(4,s)'")
        elif ln.startswith("Bp_belt"):
            lines[i] = ln  # the belt is not used here
    raw, rt, err = spice("\n".join(lines), 12)
    t = raw[:, 0]
    c = {v: raw[:, 2 * i + 1] for i, v in enumerate(vecs)}
    cyc = [(t >= k * T - 1e-12) & (t < (k + 1) * T - 1e-12) for k in range(12)]
    pk = [float(max(np.abs(c["v(1)"][m]).max(), np.abs(c["v(4)"][m]).max())) for m in cyc]
    return dict(lag_deg=deg, z=float(math.exp(np.polyfit(np.arange(3, 12), np.log(np.array(pk[3:])), 1)[0])))


def part_topology(procs, log):
    res = {}
    g = dict(set="2d", steps=STEPS_GATE, split=False, n_cyc=12, clamp=False, v0=1000.0, tag="gate 2-D")
    r = pool_map([dict(g, kind="record")], 1, log)[0]
    ref = json.load(open(os.path.join(HERE, "core_field_results.json")))
    zr = [q for q in ref["rows"] if q["name"] == "free none"][0]["z"]
    res["gate_record_2d"] = dict(z=r["z"], z_record=zr, ok=abs(r["z"] - zr) < 2e-3)
    log(f"  gate: the record's 2-D doubler z {r['z']:.4f} against {zr:.4f}")
    cls = (1e-12, 10e-12, 47e-12, 100e-12, 220e-12, 451e-12, 2e-9, 10e-9)
    jobs = [dict(kind="sketch", set="2d", n_cyc=16, clamp=False, v0=1000.0, topo=dict(cl=cl, s_new=0.0),
                 tag="sketch free") for cl in cls]
    jobs += [dict(kind=k, set="2d", n_cyc=16, clamp=False, v0=1000.0, phase=ph, topo=dict(cl=100e-12, s_new=0.0),
                  tag="bipolar free") for k in ("bip_doubler", "bip_ladder") for ph in ("in", "anti")]
    jobs += [dict(kind="sketch", set="2d", n_cyc=90, v0=1000.0, topo=dict(cl=cl, s_new=0.0), tag="sketch clamped")
             for cl in (100e-12, 451e-12)]
    jobs += [dict(kind="record", set="2d", n_cyc=90, v0=1000.0, tag="record clamped")]
    rr = pool_map(jobs, procs, log)
    res["sketch_free"] = [dict(C3_C6_pF=q["job"]["topo"]["cl"] * 1e12, z=q["z"]) for q in rr[:len(cls)]]
    res["bipolar_free"] = [dict(kind=q["job"]["kind"], phase=q["job"]["phase"], z=q["z"]) for q in rr[len(cls):len(cls) + 4]]
    res["clamped_2d"] = {}
    for q in rr[len(cls) + 4:]:
        nm = "record" if q["job"]["kind"] == "record" else f"sketch {q['job']['topo']['cl'] * 1e12:.0f} pF"
        res["clamped_2d"][nm] = dict(V_kV={k: [v["min"], v["max"]] for k, v in q["V_kV"].items()},
                                     VR_pk_kV=q["VR_pk_kV"], I_z1_avg_uA=q.get("I_z1_avg_uA"), P_clamps_W=q.get("P_clamps_W"))
    with Pool(procs) as p:
        res["bipolar_phase"] = p.map(phase_job, (0, 30, 60, 90, 120, 150, 180))
        allsets = [(ds, ph) for ds in symmetric_sets() for ph in ("in", "anti")]
        bres = p.map(brute_job, allsets, chunksize=4)
    ok = [b for b in bres if b["z"]]
    best = sorted([b for b in ok if b["bipolar"]], key=lambda b: -b["z"])
    res["symmetric_sets"] = dict(n_sets=len(allsets) // 2, n_runs=len(allsets), n_bipolar_growing=sum(
        1 for b in ok if b["bipolar"] and b["z"] > 1.0), best=best[:6], best_z_by_phase={
        ph: max([b["z"] for b in best if b["phase"] == ph] or [None]) for ph in ("in", "anti")})
    log(f"  symmetric sets: best bipolar z {res['symmetric_sets']['best_z_by_phase']}")
    return res


# ------------------------------------------------------------------------------------------------ 2. as built
CL_SWEEP = (47e-12, 100e-12, 150e-12, 180e-12, 200e-12, 220e-12, 330e-12)


def part_as_built(procs, log):
    res = {}
    ab = json.load(open(os.path.join(HERE, "tube_strays_results.json")))["decks"]["table"]["as built"]
    # the gates: the record's doubler bare, and the record's supply at start-up and clamped (as the record ran them)
    g = dict(set="ab", steps=STEPS_GATE, split=False, n_cyc=12, clamp=False)
    jobs = [dict(g, kind="record", v0=1000.0, tag="gate ab bare"), dict(g, kind="supply", v0=10.0, tag="gate ab supply")]
    rr = pool_map(jobs, 2, log)
    res["gate_bare"] = dict(z=rr[0]["z"], z_record=ab["z"], ok=abs(rr[0]["z"] - ab["z"]) < 2e-3)
    res["gate_supply_start"] = dict(z=rr[1]["z"], z_record=ab["z_rings_start"], ok=abs(rr[1]["z"] - ab["z_rings_start"]) < 3e-3)
    # the record's supply clamped as built, as sim/tube_strays.py ran it (the deck as is, from -1 kV, its cycles)
    rs = pool_map([dict(kind="supply", set="ab", steps=10000, split=False, n_cyc=ab["rings_cycles"], v0=1000.0,
                        tag="gate ab supply clamped")], 1, log)[0]
    res["gate_supply_clamped"] = dict(V_A_kV=rs["V_A_kV"], V_B_kV=rs["V_B_kV"], E_null_kV_cm=rs["E_null_kV_cm"],
                                      V_A_record=ab["V_A_kV"], V_B_record=ab["V_B_kV"],
                                      ok=abs(rs["V_A_kV"] - ab["V_A_kV"]) < 0.03 and abs(rs["V_B_kV"] - ab["V_B_kV"]) < 0.03)
    res["record_supply_as_built"] = summary(rs)
    # the free gains of the proposal over C3-C6 and its variants
    base = dict(kind="proposal", set="ab", n_cyc=40, clamp=False, v0=1000.0, fit_from=10, tag="free")
    var = [("cl", dict(cl=cl)) for cl in CL_SWEEP]
    var += [("s_new", dict(cl=200e-12, s_new=s)) for s in (0.0, 5e-12, 40e-12)]
    var += [("cpl", dict(cl=200e-12, cpl=cp)) for cp in ("mid", "base")]
    var += [("c7", dict(cl=200e-12, c7=c7)) for c7 in (47e-12, 220e-12)]
    var += [("cs", dict(cl=200e-12, cs=cs)) for cs in (47e-12, 330e-12)]
    jobs = [dict(base, topo=tp, tag=f"free {nm}") for nm, tp in var]
    jobs += [dict(base, kind="bip_stages", topo=dict(c7=c7), tag="free no ladder") for c7 in (47e-12, 100e-12)]
    jobs += [dict(base, kind="bip_doubler", tag="free bipolar doubler"), dict(base, kind="bip_ladder", topo=dict(cl=200e-12),
                                                                              tag="free bipolar ladder")]
    jobs += [dict(base, kind="record", tag="free record doubler"), dict(base, kind="supply", v0=10.0, tag="free record supply")]
    jobs += [dict(base, kind="sketch", topo=dict(cl=cl), tag="free sketch") for cl in (100e-12, 200e-12)]
    jobs += [dict(base, phase="anti", topo=dict(cl=200e-12), tag="free proposal in antiphase")]
    rf = pool_map(jobs, procs, log)
    res["free"] = [dict(kind=q["job"]["kind"], phase=q["job"].get("phase", "in" if bipolar(q["job"]["kind"]) else "anti"),
                        topo=q["job"].get("topo", {}), z=q["z"], z_late=q["z_late"]) for q in rf]
    # the clamped steady states, each from the consistent 1 kV start (as the record's decks start), long enough to
    # reach the clamp at its own gain and settle (sim/tube_strays.py _cycles), doubled until the rings settle
    zf = {(q["job"]["kind"], json.dumps(q["job"].get("topo", {}), sort_keys=True)): q["z"] for q in rf
          if q["job"].get("phase", "in") == "in"}
    cl_jobs = []
    for nm, tp in var + [("no ladder", None)]:
        kind = "bip_stages" if tp is None else "proposal"
        tp = tp or dict(c7=100e-12)
        n = cycles_for(zf.get((kind, json.dumps(tp, sort_keys=True))), 1000.0, 300, 400) or 960
        cl_jobs.append(dict(kind=kind, set="ab", n_cyc=n, v0=1000.0, topo=tp, from_seed=True, tag=f"clamped {nm}"))
    rc = pool_map(cl_jobs, procs, log)
    for _ in range(2):                                            # doubled until the rings settle
        redo = [i for i, q in enumerate(rc) if q.get("done") and not settled(q.get("gap_per_cycle_kV"))]
        if not redo:
            break
        again = pool_map([dict(rc[i]["job"], n_cyc=2 * rc[i]["job"]["n_cyc"]) for i in redo], procs, log)
        for i, q in zip(redo, again):
            rc[i] = q
    res["clamped"] = [summary(q) for q in rc]
    return res, rc


def summary(q):
    if not q.get("done"):
        return dict(job=q["job"], done=False)
    keep = ("V_A_kV", "V_B_kV", "E_null_kV_cm", "E_null_pp_kV_cm", "ripple_A_V", "ripple_B_V", "settled", "P_belt_W",
            "P_clamps_W", "P_leak_W", "P_link_W", "P_other_W", "I_z1_avg_uA", "I_z4_avg_uA", "I_z1_pk_mA", "I_z4_pk_mA",
            "link_mA_rms", "link_mA_pk", "VR_pk_kV", "torque_mNm", "cycles_to_95pc", "run_s", "reltol")
    s = dict(job=q["job"], done=True, **{k: q[k] for k in keep if k in q})
    if "gap_per_cycle_kV" in q:
        s["settled"] = settled(q["gap_per_cycle_kV"])
    s["V_kV"] = {k: [round(v["min"], 4), round(v["max"], 4)] for k, v in q["V_kV"].items()}
    s["VC_kV"] = {k: [round(v["min"], 4), round(v["max"], 4)] for k, v in q["VC_kV"].items()}
    s["sticks"] = stick_counts(topology(q["job"]["kind"], **q["job"].get("topo", {})), q["VR_pk_kV"])
    s["n_cyc"] = q["job"]["n_cyc"]
    return s


def pick_cl(res):
    """the pick: the C3-C6 whose rings sit nearest the record's +-14.96 kV (sim/hub_rings_build_results.json
    record_supply) with ideal diodes and never above it, the rings' polar bead being 0.4 % under its rating at that
    level (ledger §3.6) [IR]."""
    target = 0.5 * (SUP["V_eb_kV"]["mean"] - SUP["V_ea_kV"]["mean"])
    rows = [q for q in res["clamped"] if q["done"] and q["job"]["kind"] == "proposal" and set(q["job"]["topo"]) == {"cl"}]
    ok = [q for q in rows if 0.5 * (q["V_B_kV"] - q["V_A_kV"]) <= target]
    best = max(ok, key=lambda q: q["V_B_kV"] - q["V_A_kV"]) if ok else min(rows, key=lambda q: q["V_B_kV"])
    return best["job"]["topo"]["cl"], target


# ------------------------------------------------------------------------------------------------ 3. real parts
REAL = ("HV-typ", "HV-max", "HV-hot")


def threshold(arg):
    """the smallest seed that starts the machine (clamped, real parts): sim/diodes_real.py's rule (ab_verdict) and
    bisection (_bisect), trials of 120 cycles doubled while undecided up to 960 [IR]."""
    kind, model, ns, topo, v_hi = arg["kind"], arg["model"], arg["ns"], arg.get("topo", {}), arg.get("v_hi", 10e3)
    trials = []

    def grows(v):
        n = 120
        while True:
            r = cached(dict(kind=kind, set="ab", n_cyc=n, v0=v, model=model, ns=ns, topo=topo, free_only=True,
                            tag="trial"))
            rr = dict(r, V1_peak_per_cycle_kV=r.get("V14_peak_per_cycle_kV"))
            g_, dec = DR.ab_verdict(rr)
            if dec or n >= 960:
                break
            n *= 2
        pk = r.get("V14_peak_per_cycle_kV") or [0.0]
        trials.append(dict(v0_V=v, n_cyc=n, grows=g_, decided=dec, reached_clamp=bool(max(pk) >= 0.97 * V_OP / 1e3)))
        return g_
    return DR._bisect(grows, v_hi, dict(kind=kind, model=model), trials)


def part_real(procs, log, cl, ns_prop, ns_sup):
    res = dict(C3_C6_pF=cl * 1e12, sticks_proposal=ns_prop, sticks_supply=ns_sup)
    tp = dict(cl=cl)
    jobs = []
    for m in REAL:
        for v0 in (10.0, 1000.0):
            jobs.append(dict(kind="proposal", set="ab", n_cyc=40, clamp=False, v0=v0, model=m, ns=ns_prop, topo=tp,
                             fit_from=10, tag=f"real free {v0:g} V"))
            jobs.append(dict(kind="supply", set="ab", n_cyc=12, clamp=False, v0=v0, model=m, ns=ns_sup,
                             tag=f"real supply free {v0:g} V", split=True))
    rf = pool_map(jobs, procs, log)
    res["free"] = [dict(kind=q["job"]["kind"], model=q["job"]["model"], v0=q["job"]["v0"], z=q.get("z"),
                        z_late=q.get("z_late")) for q in rf]
    gate = json.load(open(os.path.join(HERE, "diodes_real_results.json")))["electrostatic_as_built"]["table"]
    sup_typ = [q for q in rf if q["job"]["kind"] == "supply" and q["job"]["model"] == "HV-typ" and q["job"]["v0"] == 1000.0][0]
    res["gate_supply_typ_1kV"] = dict(z=sup_typ.get("z"), z_record=gate["HV-typ"]["z_free_1kV"],
                                      ok=abs(sup_typ.get("z", 0) - gate["HV-typ"]["z_free_1kV"]) < 3e-3)
    with Pool(procs) as p:
        thr = p.map(threshold, [dict(kind="proposal", model=m, ns=ns_prop, topo=tp) for m in REAL])
    res["thresholds"] = thr
    jobs = []
    for m, t_ in zip(REAL, thr):
        vg = t_.get("v_grows_V")
        if vg is None:
            continue
        v0 = max(1000.0, 1.25 * vg)
        zf = [q["z"] for q in rf if q["job"]["kind"] == "proposal" and q["job"]["model"] == m and q["job"]["v0"] == 1000.0][0]
        n = cycles_for(zf, v0, 300, 400) or 960
        jobs.append(dict(kind="proposal", set="ab", n_cyc=min(n, 1600), v0=v0, model=m, ns=ns_prop, topo=tp,
                         from_seed=True, tag=f"real clamped {m}"))
    rc = pool_map(jobs, procs, log) if jobs else []
    res["clamped"] = [summary(q) for q in rc]
    return res


# ------------------------------------------------------------------------------------------------ 4. side effects
def part_side(procs, log, cl):
    tp = dict(cl=cl)
    jobs = [dict(kind="proposal", set="ab", n_cyc=40, clamp=False, v0=1000.0, link=False, cx=cx, topo=tp, fit_from=10,
                 tag=f"floating {cx * 1e12:g} pF") for cx in (100e-12, 10e-9)]
    jobs += [dict(kind="record", set="ab", n_cyc=40, clamp=False, v0=1000.0, link=False, cx=cx, fit_from=10,
                  tag=f"record floating {cx * 1e12:g} pF") for cx in (100e-12, 10e-9)]
    jobs += [dict(kind="record", set="ab", n_cyc=72, v0=1000.0, tag="record clamped (link, torque)")]
    rr = pool_map(jobs, procs, log)
    return dict(floating=[dict(kind=q["job"]["kind"], cx_pF=q["job"]["cx"] * 1e12 if q["job"].get("cx") else None,
                               z=q.get("z")) for q in rr[:4]],
                record_clamped=summary(rr[4]))


# ------------------------------------------------------------------------------------------------ derived lines
def derive(out):
    """the pick's numbers in one place, for the findings and the schematic (docs/make_integrated_multiplier_schematic.py)."""
    cl = out["pick"]["C3_C6_pF"] * 1e-12
    ab = out["as_built"]
    st = [q for q in ab["clamped"] if q["done"] and q["job"]["kind"] == "proposal" and q["job"]["topo"] == dict(cl=cl)]
    out["pick"]["steady"] = max(st, key=lambda q: q["n_cyc"])
    out["pick"]["z_free"] = [q["z"] for q in ab["free"] if q["kind"] == "proposal" and q["phase"] == "in"
                             and q["topo"] == dict(cl=cl)][0]
    z0 = [q for q in ab["clamped"] if q["done"] and q["job"]["topo"].get("s_new") == 0.0]
    if z0:
        out["rings_at_zero_strays_kV"] = max(z0, key=lambda q: q["n_cyc"])["V_B_kV"]
    rc = (out.get("side") or {}).get("record_clamped")
    if rc and rc.get("done"):
        out["record_VR_pk_kV"] = max(rc["VR_pk_kV"].values())
        out["record_VC_Ca_kV"] = max(abs(x) for x in rc["VC_kV"]["Ca"])
    re_ = out.get("real")
    if re_:
        fz = {(q["kind"], q["model"], q["v0"]): q["z"] for q in re_["free"]}
        th = {q["model"]: q for q in re_["thresholds"]}
        parts = []
        for m, lab in (("HV-typ", "typical"), ("HV-max", "maximum"), ("HV-hot", "hot")):
            vg = th.get(m, {}).get("v_grows_V")
            parts.append(f"{lab} z {fz[('proposal', m, 1000.0)]:.4f} from 1 kV (record {fz[('supply', m, 1000.0)]:.4f}), "
                         + (f"starts from {vg:.0f} V" if vg else "no start up to 10 kV"))
        re_["summary_line"] = "; ".join(parts)
    return out


# ------------------------------------------------------------------------------------------------ main
def main():
    global CACHE
    ap = argparse.ArgumentParser()
    ap.add_argument("--procs", type=int, default=4)
    ap.add_argument("--only", nargs="*", default=["topo", "ab", "real", "side"])
    ap.add_argument("--cache", default=None)
    a = ap.parse_args()
    CACHE = a.cache
    t0 = time.time()
    old = json.load(open(OUT_JSON)) if os.path.exists(OUT_JSON) else {}
    out = dict(old, note=__doc__.split("\n\n")[0], sources=SRC, tags="CONVENTIONS.md §1",
               set_ab_pF={k: (v * 1e12 if isinstance(v, float) else v) for k, v in SET_AB.items() if k in ("cmin", "cmax", "ca")},
               V_op_kV=V_OP / 1e3, s_new_pF=S_NEW * 1e12, c_cw_pF=C_CW * 1e12, r_leak_ohm=R_LEAK, k_null=K_NULL)
    log = lambda s: print(s, flush=True)
    if "topo" in a.only:
        log("1. topology (2-D set)")
        out["topology"] = part_topology(a.procs, log)
    if "ab" in a.only:
        log("2. as built, ND")
        out["as_built"], rc = part_as_built(a.procs, log)
        cl, target = pick_cl(out["as_built"])
        out["pick"] = dict(C3_C6_pF=cl * 1e12, rings_target_kV=target)
        log(f"  the pick: C3-C6 {cl * 1e12:.0f} pF (rings at most +-{target:.2f} kV with ND)")
        # the pick from a consistent 1 kV start (the start-up), and the step check at twice the steps
        st = [q for q in out["as_built"]["clamped"] if q["done"] and q["job"]["kind"] == "proposal"
              and q["job"]["topo"] == dict(cl=cl)][0]
        rp = pool_map([dict(st["job"], steps=2 * STEPS, tag="pick step check")], 1, log)
        out["pick"]["step_check"] = summary(rp[0])
    if "real" in a.only:
        log("3. real parts")
        cl = out["pick"]["C3_C6_pF"] * 1e-12
        sweep = [q for q in out["as_built"]["clamped"] if q["done"] and q["job"]["kind"] == "proposal"
                 and q["job"]["topo"] == dict(cl=cl)][0]
        ns_prop = sweep["sticks"]
        ns_sup = stick_counts(topology("supply"), DR._vr_rec())
        out["real"] = part_real(a.procs, log, cl, ns_prop, ns_sup)
    if "side" in a.only:
        log("4. side effects")
        out["side"] = part_side(a.procs, log, out["pick"]["C3_C6_pF"] * 1e-12)
    if out.get("pick") and out.get("as_built"):
        derive(out)
    out["run_s"] = round(time.time() - t0) + (old.get("run_s", 0) if set(a.only) != {"topo", "ab", "real", "side"} else 0)
    json.dump(out, open(OUT_JSON, "w"), indent=1)
    log(f"wrote {OUT_JSON} ({out['run_s']} s)")


if __name__ == "__main__":
    main()
