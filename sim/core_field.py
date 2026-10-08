"""sim/core_field.py -- the electrostatic pump with its high-voltage side on the ROTOR, and an electric field on the core.
ngspice; the air build's capped stack (sim/air_stack_sizing.py stage 4c: 3 mm full-round vanes, 6 + 6 per varicap per
side, 6 x 22 / 22 deg, 6 mm gaps, r 150) at 1200 rpm relative (120 pump cycles per second), V_op 13.1 kV.

The move (designer's decision):
- C1 / C2: the rotor vanes R-A / R-B become nodes 1 / 4; the stator vanes on the counter-rotor are the reference of both.
- Ca / Cb, D1-D4 and the clamps Z1 / Z4 ride on the rotor with the hub, referred to the shaft.
- The counter-rotor joins the shaft through the reference link (one inner bearing for now). The link carries C1 and C2's
  displacement current; the DC through the diodes and clamps now circulates on the rotor.
The core is sim/bicone_drive.py's diodes-only netlist with C1 / C2 returned to the counter-rotor's node s. Nothing else
changes, so the pump is the stack's own (checked: `none` against the stack's eigen-cycle z and clamped power).

The cones (the bicone halves) can now reach the HV nodes without a rotating contact. Ways to put a field on the core [IR]:
  series  the cones stay coils in series with C1 / C2, now between node 1 / 4 and the rotor vanes: the core sees the
          cones' difference, about V(1) - V(4);
  ca      no series coil; cone A on node 1, cone B on node 2: the core sees V_Ca = V(1) - V(2);
  peak    no series coil; cone A charged from node 1 through an HV diode (anode on the cone) and held by C_core to the
          shaft, with the core's leakage R_leak across it; cone B on the shaft: the core sees node 1's peak, about -V_op.
A swinging field on floating cones (designer's choice, after the above):
  float   each cone coupled to its node (A to 1, B to 4) through an HV capacitor CC; nothing else ties the cones to the
          shaft but their leakage R_leak each: the core sees the AC of V(1) - V(4), each cone swings about the shaft;
  swing   the cones straight on nodes 1 / 4: the same swing, on the nodes' -9.5 kV common mode;
  swing23 the cones straight on nodes 2 / 3: V(2) - V(3).
Strays [RH]: 20 pF at each of nodes 1-4 (as before), 20 pF from each cone to the shaft side, 10 pF cone to cone.
Side checks [IR]: the counter-rotor floating (no link; C_x from it to the shaft), down to a capacitive link of 10 nF.
--grid: the swinging core's cost on any stack of the vane matrix -- z, the clamped power and the core's swing, bare and
with the float wiring, over C_max x kappa (Ca = 1.1 C_max); writes sim/core_swing_grid.json for docs/make_cost_sheet.py.
Runs: free (no clamp, from -1 kV): the gain z per cycle, fitted on the node-1 peaks; clamped: the steady state over the
last 8 of 24 cycles; one start-up of the peak option from -1 kV with the clamp on.
Usage: python3 sim/core_field.py [--procs 4] [--only NAME ...]   (writes sim/core_field_results.json)
       python3 sim/core_field.py --grid                             (writes sim/core_swing_grid.json)
"""
import argparse
import json
import math
import os
import subprocess
import sys
import tempfile
from multiprocessing import Pool

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import bicone_drive as BD          # noqa: E402  (the cones' L / M / R and the strays of record)

RPM, F = 1200.0, 120.0
CPAR = BD.CPAR                     # 20 pF at each of nodes 1-4 [RH]
C_CONE, C_CC = 20e-12, 10e-12      # each cone to the shaft side (flange, AH, hub), cone to cone [RH]
D_CORE_MM, E_WANT_KV_CM = 50.0, 2.0     # the cost sheet's placeholders (docs/make_cost_sheet.py: D_CORE, E_CORE) [RH]
R_LINK = 1.0                       # the reference link: the bearing's contact, ohm [RH]; a 0 V source stalls ngspice [IR]
CC = 1e-9                          # the float wiring's coupling capacitors, node -> cone [RH]
GRID_CMAX = (130, 250, 450, 800, 1500, 3000, 6000, 12000)      # pF, the matrix spans 136-11154
GRID_KAPPA = (3, 5, 8, 13, 22, 40, 75)                          # the matrix spans 3.0-74


def design():
    """the capped stack of record: 3 mm full rounds, 6 + 6 (sim/air_stack_sizing_results.json, stage 4c)."""
    rows = json.load(open(os.path.join(HERE, "air_stack_sizing_results.json")))["thick_vanes"]["compare"]
    return [q for q in rows if q["t_vaneMm"] == 3.0 and q["n_plates"] == 6][0]


Q = design()
CMIN, CMAX, CA = Q["C_min_pF"] * 1e-12, Q["C_max_pF"] * 1e-12, Q["Ca_pF"] * 1e-12
V_OP = Q["V_op_kV"] * 1e3


def deck(opt="none", clamp=True, link=True, n_cyc=24, steps=20000, c_core=1e-9, r_leak=10e9, cx=100e-12, v0=-1000.0,
         vk0=None, reltol=1e-5, cmin=None, cmax=None, ca=None, cc=CC, ic=None):
    """the rotor-side netlist. Nodes: 1-4 the pump (rotor), s the counter-rotor (stator vanes), 0 the shaft;
    series: ra / rb the rotor vanes behind the cones; peak: k cone A; float: ka / kb the floating cones.
    cmin / cmax / ca default to the stack of record; ic overrides the initial node voltages."""
    CMIN_, CMAX_, CA_ = (CMIN if cmin is None else cmin), (CMAX if cmax is None else cmax), (CA if ca is None else ca)
    w = 2 * math.pi * F
    s1 = f"(0.5*(1+cos({w:.8e}*time)))"
    s2 = f"(0.5*(1-cos({w:.8e}*time)))"
    a, b = ("ra", "rb") if opt == "series" else ("1", "4")              # the rotor vanes' node
    dC = CMAX_ - CMIN_
    t = [f"* core field: {opt}, clamp {clamp}, link {link}",
         f"C1v {a} s Q='({CMIN_:.6e}+{dC:.6e}*{s1})*V({a},s)'",
         f"C2v {b} s Q='({CMIN_:.6e}+{dC:.6e}*{s2})*V({b},s)'",
         f"Ca 1 2 {CA_:.6e}", f"Cb 3 4 {CA_:.6e}"]
    t += [f"Cp{n} {n} 0 {CPAR:.3e}" for n in "1234"]
    t += [".model ND D(is=1e-9 n=0.005 rs=1e-3 cjo=0)", "Dd1 2 0 ND", "Dd2 3 0 ND", "Dd3 1 3 ND", "Dd4 4 2 ND"]
    t += [f"Rlink s 0 {R_LINK:g}"] if link else [f"Cx s 0 {cx:.3e}", "Rx s 0 1e13"]
    if opt == "series":
        t += [f"Lca 1 ca {BD.L_CONE:.6e}", f"Rca ca ma {BD.R_CONE}", "Vma ma ra 0",
              f"Lcb 4 cb {BD.L_CONE:.6e}", f"Rcb cb mb {BD.R_CONE}", "Vmb mb rb 0",
              f"Kc Lca Lcb {BD.M_CONE / BD.L_CONE:.4f}",
              f"Cna ra 0 {C_CONE:.3e}", f"Cnb rb 0 {C_CONE:.3e}", f"Cnn ra rb {C_CC:.3e}"]
    elif opt == "ca":
        t += [f"Cna 1 0 {C_CONE:.3e}", f"Cnb 2 0 {C_CONE:.3e}", f"Cnn 1 2 {C_CC:.3e}"]
    elif opt == "swing":
        t += [f"Cna 1 0 {C_CONE:.3e}", f"Cnb 4 0 {C_CONE:.3e}", f"Cnn 1 4 {C_CC:.3e}"]
    elif opt == "swing23":
        t += [f"Cna 2 0 {C_CONE:.3e}", f"Cnb 3 0 {C_CONE:.3e}", f"Cnn 2 3 {C_CC:.3e}"]
    elif opt == "float":
        t += [f"Cka 1 ka {cc:.4e}", f"Ckb 4 kb {cc:.4e}", f"Cna ka 0 {C_CONE:.3e}", f"Cnb kb 0 {C_CONE:.3e}",
              f"Cnn ka kb {C_CC:.3e}", f"Rla ka 0 {r_leak:.4e}", f"Rlb kb 0 {r_leak:.4e}"]
    elif opt == "peak":
        t += ["Dk k 1 ND", f"Ck k 0 {c_core + C_CONE + C_CC:.4e}", f"Rk k 0 {r_leak:.4e}"]
    P = {"belt": f"{dC * 0.5 * w:.6e}*sin({w:.8e}*time)*0.5*(V({a},s)*V({a},s)-V({b},s)*V({b},s))"}
    if clamp:
        t += [f".model DZ D(is=1e-14 n=1 bv={V_OP:.0f} ibv=1e-6 nbv=1 rs=1e5 cjo=0)",
              "Vz1 0 z1 0", "Dz1 1 z1 DZ", "Vz4 0 z4 0", "Dz4 4 z4 DZ"]
        P["limit"] = "-V(1)*i(Vz1)-V(4)*i(Vz4)"
    if opt == "peak":
        P["leak"] = f"V(k)*V(k)/{r_leak:.4e}"
    if opt == "float":
        P["leak"] = f"(V(ka)*V(ka)+V(kb)*V(kb))/{r_leak:.4e}"
    if opt == "series":
        P["cone"] = f"{BD.R_CONE}*(i(Vma)*i(Vma)+i(Vmb)*i(Vmb))"
    for nd, ex in P.items():
        t += [f"Bp_{nd} 0 e_{nd} I='{ex}'", f"Cp_{nd} e_{nd} 0 1", f"Rp_{nd} e_{nd} 0 1e18"]
    ics = {"1": v0, "4": v0, "2": 0.0, "3": 0.0, "s": 0.0}
    if opt == "series":
        ics.update(ra=v0, rb=v0, ma=v0, mb=v0, ca=v0, cb=v0)
    if opt == "peak":
        ics["k"] = v0 if vk0 is None else vk0
    if opt == "float":
        ics.update(ka=0.0, kb=0.0)
    ics.update(ic or {})
    ics.update({f"e_{nd}": 0.0 for nd in P})
    vecs = ["v(1)", "v(2)", "v(3)", "v(4)", "v(s)"]
    vecs += ["v(ra)", "v(rb)", "i(Vma)", "i(Vmb)"] if opt == "series" else []
    vecs += ["v(k)"] if opt == "peak" else []
    vecs += ["v(ka)", "v(kb)"] if opt == "float" else []
    vecs += ["i(Vz1)", "i(Vz4)"] if clamp else []
    vecs += [f"v(e_{nd})" for nd in P]
    ms = 1.0 / F / steps
    t += [".ic" + "".join(f" v({n})={v:g}" for n, v in ics.items()), ".control",
          f"tran {ms:.4e} {n_cyc / F:.6e} uic", "wrdata out.dat " + " ".join(vecs), ".endc",
          f".options reltol={reltol:g} abstol=1e-12 vntol=1e-6 gmin=1e-15 maxstep={ms:.4e} method=gear", ".end"]
    return "\n".join(t) + "\n", vecs, list(P)


def _stats(y):
    return dict(mean=float(np.mean(y)), min=float(y.min()), max=float(y.max()), pp=float(y.max() - y.min()))


def run(case):
    name, kw = case
    kw = dict(kw)
    kw.setdefault("n_cyc", 24)
    txt, vecs, pk = deck(**{k: v for k, v in kw.items() if k != "start"})
    with tempfile.TemporaryDirectory() as d:
        open(os.path.join(d, "x.cir"), "w").write(txt)
        r = subprocess.run(["ngspice", "-b", "x.cir"], capture_output=True, text=True, timeout=7200, cwd=d)
        try:
            raw = np.loadtxt(os.path.join(d, "out.dat"))
        except (OSError, ValueError):
            return dict(name=name, **kw, error=(r.stdout + r.stderr)[-400:])
    t = raw[:, 0]
    c = {v: raw[:, 2 * j + 1] for j, v in enumerate(vecs)}
    n, T = kw["n_cyc"], 1.0 / F
    out = dict(name=name, **kw, t_end=float(t[-1]), done=bool(t[-1] >= 0.99 * n * T))
    if not out["done"]:
        return out
    cyc = [(t >= k * T) & (t < (k + 1) * T) for k in range(n)]
    nodes = [v_ for v_ in vecs if v_.startswith("v(") and not v_.startswith("v(e_")]
    out["end"] = {v_: float(c[v_][-1]) for v_ in nodes}                    # the state at the end (phase 0)
    out["mean_last"] = {v_: float(np.mean(c[v_][cyc[-1]])) for v_ in nodes}
    pk1 = [float(np.abs(c["v(1)"][m]).max()) for m in cyc]
    out["V1_peak_per_cycle_kV"] = [p / 1e3 for p in pk1]
    if kw.get("opt") == "peak":
        out["Vk_per_cycle_kV"] = [float(c["v(k)"][m].min() / 1e3) for m in cyc]
    if not kw.get("clamp", True):
        k = np.arange(3, n)                                            # the gain per cycle: skip the first cycles
        out["z"] = float(math.exp(np.polyfit(k, np.log(np.array(pk1[3:n])), 1)[0]))
        if not kw.get("link", True):
            out["Vs"] = _stats(c["v(s)"][cyc[-1]])
        return out
    if kw.get("start"):                                                # the start-up: time to 95 % of the final level
        vk = np.array(out["Vk_per_cycle_kV"])
        fin = vk[-3:].mean()
        hit = np.nonzero(vk <= 0.95 * fin)[0]
        out["Vk_final_kV"] = float(fin)
        out["cycles_to_95pc"] = int(hit[0]) + 1 if len(hit) else None
        out["t_to_95pc_s"] = out["cycles_to_95pc"] / F if len(hit) else None
        return out
    s = t >= (n - 8) * T
    ts = t[s]
    dt, dur = np.diff(ts), ts[-1] - ts[0]

    def avg(y):
        return float(np.sum(0.5 * (y[1:] + y[:-1]) * dt) / dur)
    for nd in pk:
        y = c[f"v(e_{nd})"]
        out[f"P_{nd}_W"] = float((np.interp(ts[-1], t, y) - np.interp(ts[0], t, y)) / dur)
    out["P_other_W"] = out["P_belt_W"] - sum(out[f"P_{nd}_W"] for nd in pk if nd != "belt")
    v = {n_: c[f"v({n_})"][s] for n_ in "1234"}
    out["V"] = {n_: _stats(v[n_] / 1e3) for n_ in "1234"}
    out["V_Ca_kV"] = _stats((v["1"] - v["2"]) / 1e3)
    out["V_1_4_kV"] = _stats((v["1"] - v["4"]) / 1e3)
    out["V_cm_ca_kV"] = _stats(0.5 * (v["1"] + v["2"]) / 1e3)          # cones on node 1 / node 2: their common mode
    for z_, nd in (("Z1", "1"), ("Z4", "4")):
        i = c[f"i(V{z_.lower()})"][s]
        out[z_] = dict(I_avg_mA=avg(i) * 1e3, I_pk_mA=float(i.max() * 1e3), P_W=avg(-v[nd] * i))
    vr = dict(D1=-v["2"], D2=-v["3"], D3=v["3"] - v["1"], D4=v["2"] - v["4"])     # reverse across each diode
    if kw.get("opt") == "peak":
        vr["Dk"] = v["1"] - c["v(k)"][s]
    if kw.get("opt") == "float":                                       # across the coupling capacitors, either sign
        vr["CC"] = np.maximum(np.abs(v["1"] - c["v(ka)"][s]), np.abs(v["4"] - c["v(kb)"][s]))
    out["VR_pk_kV"] = {k: float(x.max() / 1e3) for k, x in vr.items()}
    if kw.get("link", True):
        il = c["v(s)"][s] / R_LINK                                     # counter-rotor -> shaft
        out["link"] = dict(I_rms_mA=math.sqrt(avg(il * il)) * 1e3, I_pk_mA=float(np.abs(il).max() * 1e3),
                           I_avg_uA=avg(il) * 1e6)
    else:
        out["Vs_kV"] = _stats(c["v(s)"][s] / 1e3)
    opt = kw.get("opt", "none")
    if opt == "series":
        vc = (c["v(ra)"][s] - c["v(rb)"][s]) / 1e3
        ia = c["i(Vma)"][s]
        out["cone_I_rms_mA"] = math.sqrt(avg(ia * ia)) * 1e3
        out["AT_pk"] = BD.N_CONE * float(max(np.abs(ia).max(), np.abs(c["i(Vmb)"][s]).max()))
    elif opt == "ca":
        vc = (v["1"] - v["2"]) / 1e3
    elif opt == "peak":
        vc = c["v(k)"][s] / 1e3
        out["V_k_kV"] = _stats(vc)
        out["droop_analytic_kV"] = float(abs(np.mean(vc)) / (kw.get("r_leak", 10e9) * (kw.get("c_core", 1e-9) + C_CONE + C_CC)
                                                             * F))
    elif opt in ("swing", "swing23"):
        a_, b_ = ("1", "4") if opt == "swing" else ("2", "3")
        vc = (v[a_] - v[b_]) / 1e3
        out["V_cm_kV"] = _stats(0.5 * (v[a_] + v[b_]) / 1e3)           # the cones' common mode against the shaft
    elif opt == "float":
        ka, kb = c["v(ka)"][s], c["v(kb)"][s]
        vc = (ka - kb) / 1e3
        out["V_ka_kV"], out["V_kb_kV"] = _stats(ka / 1e3), _stats(kb / 1e3)
        out["V_cm_kV"] = _stats(0.5 * (ka + kb) / 1e3)
        out["cone_swing_kV"] = 0.5 * max(out["V_ka_kV"]["pp"], out["V_kb_kV"]["pp"])   # each cone about its mean
    else:
        vc = v["1"] / 1e3                                              # cone A straight on node 1, cone B on the shaft
    out["V_core_kV"] = _stats(vc)
    out["swing_pk_kV"] = float(np.abs(vc).max())
    out["E_pk_kV_cm"] = out["swing_pk_kV"] / (D_CORE_MM / 10.0)
    st = out["V_core_kV"]
    out["E_mean_kV_cm"] = abs(st["mean"]) / (D_CORE_MM / 10.0)
    out["E_swing_kV_cm"] = st["pp"] / (D_CORE_MM / 10.0)
    out["ripple_pc"] = 100.0 * st["pp"] / max(1e-9, abs(st["mean"]))
    return out


CASES = [
    # free: the gain per cycle (no clamp, 12 cycles from -1 kV)
    ("free none", dict(opt="none", clamp=False, n_cyc=12)),
    ("free series", dict(opt="series", clamp=False, n_cyc=12)),
    ("free ca", dict(opt="ca", clamp=False, n_cyc=12)),
    ("free peak 1nF 10G", dict(opt="peak", clamp=False, n_cyc=12, c_core=1e-9, r_leak=10e9)),
    ("free peak 1nF 1G", dict(opt="peak", clamp=False, n_cyc=12, c_core=1e-9, r_leak=1e9)),
    ("free peak 1nF 0.1G", dict(opt="peak", clamp=False, n_cyc=12, c_core=1e-9, r_leak=0.1e9)),
    ("free peak 1nF 0.05G", dict(opt="peak", clamp=False, n_cyc=12, c_core=1e-9, r_leak=0.05e9)),
    ("free peak 1nF 0.03G", dict(opt="peak", clamp=False, n_cyc=12, c_core=1e-9, r_leak=0.03e9)),
    ("free peak 0.1nF 10G", dict(opt="peak", clamp=False, n_cyc=12, c_core=0.1e-9, r_leak=10e9)),
    ("free swing", dict(opt="swing", clamp=False, n_cyc=12)),
    ("free swing23", dict(opt="swing23", clamp=False, n_cyc=12)),
    ("free float", dict(opt="float", clamp=False, n_cyc=12)),
    # the counter-rotor floating (no link): C_x from it to the shaft, up to a capacitive link
    ("free cr 100pF", dict(opt="none", clamp=False, link=False, n_cyc=12, cx=100e-12)),
    ("free cr 1nF", dict(opt="none", clamp=False, link=False, n_cyc=12, cx=1e-9)),
    ("free cr 3.3nF", dict(opt="none", clamp=False, link=False, n_cyc=12, cx=3.3e-9)),
    ("free cr 10nF", dict(opt="none", clamp=False, link=False, n_cyc=12, cx=10e-9)),
    # clamped at V_op: the steady state
    ("none", dict(opt="none")),
    ("series", dict(opt="series")),
    ("ca", dict(opt="ca")),
    ("peak 1nF 10G", dict(opt="peak", c_core=1e-9, r_leak=10e9, vk0=-V_OP)),
    ("peak 1nF 1G", dict(opt="peak", c_core=1e-9, r_leak=1e9, vk0=-V_OP)),
    ("peak 1nF 0.1G", dict(opt="peak", c_core=1e-9, r_leak=0.1e9, vk0=-V_OP, n_cyc=120)),   # slow to settle
    ("peak 0.1nF 10G", dict(opt="peak", c_core=0.1e-9, r_leak=10e9, vk0=-V_OP)),
    ("swing", dict(opt="swing")),
    ("swing23", dict(opt="swing23")),
    ("float", dict(opt="float")),
    ("cr 100pF", dict(opt="none", link=False, cx=100e-12)),
    ("cr 10nF", dict(opt="none", link=False, cx=10e-9)),
    # the start-up of the peak option: from -1 kV, the clamp on
    ("start peak 1nF 10G", dict(opt="peak", c_core=1e-9, r_leak=10e9, n_cyc=150, steps=5000, start=True)),
]


def float_ss(r):
    """the floating cones' steady state: restart the 'float' run from its end state with the cones' DC removed, i.e.
    where their leakage to the shaft leaves it after many R_leak * CC (seconds); the AC is the same."""
    ic = {k[2:-1]: v for k, v in r["end"].items()}
    for cone in ("ka", "kb"):
        ic[cone] = r["end"][f"v({cone})"] - r["mean_last"][f"v({cone})"]
    return ("float ss", dict(opt="float", ic=ic))


def grid(procs):
    """the swinging core over the matrix's range: bare and float wiring, free (z) and clamped (power, swing)."""
    cases = []
    for cm in GRID_CMAX:
        for k in GRID_KAPPA:
            cap = dict(cmax=cm * 1e-12, cmin=cm / k * 1e-12, ca=1.1 * cm * 1e-12)
            for opt in ("none", "float"):
                cases += [(f"g {opt} free {cm} {k}", dict(opt=opt, clamp=False, n_cyc=12, v0=-10.0, **cap)),   # z is
                          # amplitude-free; from -1 kV the fast-growing corners reach ~1 MV and stall the solver
                          (f"g {opt} {cm} {k}", dict(opt=opt, **cap))]
    res = {}
    with Pool(procs) as pool:
        for r in pool.imap_unordered(run, cases):
            res[r["name"]] = r
            print(r["name"], r.get("done"), r.get("z", r.get("P_belt_W")), flush=True)
    rows = []
    for cm in GRID_CMAX:
        for k in GRID_KAPPA:
            g = {nm: res.get(f"g {nm} {cm} {k}", {}) for nm in ("none free", "float free", "none", "float")}
            if not all(x.get("done") for x in g.values()):
                rows.append(dict(C_max_pF=cm, kappa=k, ok=False))
                continue
            rows.append(dict(C_max_pF=cm, kappa=k, ok=True, z_none=g["none free"]["z"], z_float=g["float free"]["z"],
                             P_none_W=g["none"]["P_belt_W"], P_float_W=g["float"]["P_belt_W"],
                             swing_pk_kV=g["float"]["swing_pk_kV"], cone_swing_kV=g["float"]["cone_swing_kV"]))
    out = dict(V_op_kV=V_OP / 1e3, F_Hz=F, CPAR_pF=CPAR * 1e12, C_CONE_pF=C_CONE * 1e12, C_CC_pF=C_CC * 1e12,
               CC_nF=CC * 1e9, Ca_over_Cmax=1.1, grid_C_max_pF=list(GRID_CMAX), grid_kappa=list(GRID_KAPPA), rows=rows)
    json.dump(out, open(os.path.join(HERE, "core_swing_grid.json"), "w"), indent=1, default=float)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--procs", type=int, default=4)
    ap.add_argument("--only", nargs="*", default=None, help="case names to run (default: all)")
    ap.add_argument("--grid", action="store_true", help="the swinging core over C_max x kappa, for the cost sheet")
    a = ap.parse_args()
    if a.grid:
        return grid(a.procs)
    path = os.path.join(HERE, "core_field_results.json")
    old = {r["name"]: r for r in json.load(open(path))["rows"]} if os.path.exists(path) else {}
    todo = [c for c in CASES if a.only is None or c[0] in a.only]
    order = sorted(todo, key=lambda c: -c[1].get("n_cyc", 24) * c[1].get("steps", 20000))   # the long one first
    with Pool(a.procs) as pool:
        for r in pool.imap_unordered(run, order):
            old[r["name"]] = r
            print(json.dumps({k: v for k, v in r.items() if not isinstance(v, list)}, default=float)[:700], flush=True)
    if "float" in old and old["float"].get("done") and (a.only is None or "float" in a.only or "float ss" in a.only):
        r = run(float_ss(old["float"]))
        old[r["name"]] = r
        print(json.dumps({k: v for k, v in r.items() if not isinstance(v, (list, dict))}, default=float)[:700])
    rows = [old[c[0]] for c in CASES + [("float ss", None)] if c[0] in old]
    out = dict(design={k: Q[k] for k in ("gap_mm", "t_vaneMm", "n_plates", "ws_deg", "wr_deg", "C_min_pF", "C_max_pF",
                                         "Ca_pF", "kappa", "z", "P_clamped_W", "V_op_kV")},
               F_Hz=F, rpm_rel=RPM, CPAR_pF=CPAR * 1e12, C_CONE_pF=C_CONE * 1e12, C_CC_pF=C_CC * 1e12,
               D_CORE_mm=D_CORE_MM, E_want_kV_cm=E_WANT_KV_CM, rows=rows)
    json.dump(out, open(path, "w"), indent=1, default=float)


if __name__ == "__main__":
    main()
