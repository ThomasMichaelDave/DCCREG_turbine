"""sim/switchless_cem.py -- C-EMs driven WITHOUT switches on the bare de Queiroz diode core (tube), two placements side by
side, circuit-level in ngspice (time domain: KCL, diodes, coil L / R / PM back-EMF).

Why ngspice and not pump_engine: the engine is scale-free (eigen-cycle), a PM back-EMF is a fixed-amplitude source that
does not scale with the pump voltage, so it cannot sit in the engine's linear map [IR].

Core (as drawn, negative polarity): C1(t) 1v-ref, C2(t) 4v-ref (cosine, antiphase, C 71.1 / 1113.4 pF), Ca 1-2, Cb 3-4
(1224.7 pF), Cpar 20 pF per node; D1 2->ref, D2 3->ref, D3 1->3, D4 4->2 (anode -> cathode) [OC].
Without a coil, node 1v = node 1 and node 4v = node 4.

Placements (no switches anywhere):
- LEG: coil string A (6 coils) in series with C1 (node 1 -> coils -> 1v -> C1 -> ref), string B with C2. The string
  carries C1's own displacement current d(C1 V)/dt: AC, locked to rotor angle by the plates.
- BUS: coil string A in series with D5 (bus -> D5 -> coils -> node 1), B with D6 -> node 4; C_bus 10 nF to ref,
  R_bleed 10 G, R_s 22 k. (The bus of docs/schematic-diode-core-dcbus.svg with the switched drive removed.)

Coil string per side: 6 coils in phase, N = k x 1846 turns in the same window: L = 6 x 1.9 H x k^2, R = 6 x 44.5 x k^2,
PM flux per coil Phi = dPhi/2 cos(m theta + phi), so EMF peak per string = 6 N dPhi/2 m w_rel [RH: dPhi 0.27 mWb,
flux-switching PM C-core, gate G-SWING open]. m = flux periods per rev seen by a coil: 6 utron passes per rev matches
the 6 pump cycles per rev (N_sec 12); the present tube has 3 utrons per side (m 3) [IR].
Operating-voltage limit: a passive avalanche clamp (series avalanche-diode string, BV 20 kV) from node 1 and node 4 to
ref -- a diode, not a switch; it books whatever surplus the coils do not take [IR].

Power book per cycle (all from the waveforms): belt = sum -1/2 V^2 dC/dt over C1, C2 [OC]; mechanical to the coils =
e i; copper = i^2 R; clamp = V i. Torque on the stator = P / w_rel.

Usage: python3 sim/switchless_cem.py   (writes sim/switchless_cem_results.json)
"""
import json
import math
import os
import subprocess
import sys
import tempfile

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
RPM = 300.0
CYC_REV = 6
F = CYC_REV * RPM / 60.0                      # 30 pump cycles per second
W_REL = 2 * math.pi * RPM / 60.0
CMIN, CMAX, CA, CPAR = 71.1155e-12, 1113.358e-12, 1224.694e-12, 20e-12
N0, L0, R0 = 1846, 1.9, 44.5                  # per coil at the present winding (sim/tube_ledger.py)
N_COILS = 6
DPHI = 0.27e-3
V_OP = 20e3
T_DRAG = 14.7e-3                               # tube bearings, vacuum (no windage) [RH]
T_PUMP_REF = 78e-3                             # pump reaction at 20 kV (sim/diode_machine.py) for reference
STEPS = 20000                                  # max step = one pump cycle / STEPS
RS_CLAMP = 1e5
RSN = 10e6                                     # bus placement: snubber across each coil string
N_CYC = 26                                     # simulated cycles; the last 6 are averaged
SEED = -1000.0


def emf_peak(k, m):
    return N_COILS * k * N0 * DPHI / 2 * m * W_REL


def deck(place, k=1.0, m=6, phi_deg=0.0, clamp=True, coils=True, reltol=1e-5, n_d=0.005, seed=SEED, n_cyc=N_CYC):
    w = 2 * math.pi * F
    s1 = f"(0.5*(1+cos({w:.8e}*time)))"
    s2 = f"(0.5*(1-cos({w:.8e}*time)))"
    E = emf_peak(k, m) if coils else 0.0
    fe = m * RPM / 60.0
    ph = math.radians(phi_deg)
    L, R = N_COILS * L0 * k * k, N_COILS * R0 * k * k
    a1, a4 = ("1v", "4v") if (place == "leg" and coils) else ("1", "4")
    t = [f"* switchless C-EM: {place} k {k} m {m} phi {phi_deg}",
         f"C1v {a1} 0 Q='({CMIN:.6e}+{CMAX - CMIN:.6e}*{s1})*V({a1})'",
         f"C2v {a4} 0 Q='({CMIN:.6e}+{CMAX - CMIN:.6e}*{s2})*V({a4})'",
         f"Ca 1 2 {CA:.6e}", f"Cb 3 4 {CA:.6e}"]
    t += [f"Cp{n} {n} 0 {CPAR:.3e}" for n in ("1", "2", "3", "4")]
    t += [f".model ND D(is=1e-9 n={n_d:g} rs=1e-3 cjo=0)",
          "Dd1 2 0 ND", "Dd2 3 0 ND", "Dd3 1 3 ND", "Dd4 4 2 ND"]
    if clamp:
        # avalanche string: reverse-biased at negative node voltage, conducts above V_OP; a soft knee and 100 k of
        # string resistance, as a stack of avalanche diodes has [RH] (a hard knee is also under-resolved in time)
        t += [f".model DZ D(is=1e-14 n=1 bv={V_OP:.0f} ibv=1e-6 nbv=1 rs={RS_CLAMP:g} cjo=0)",
              "Vz1 0 z1 0", "Dz1 1 z1 DZ", "Vz4 0 z4 0", "Dz4 4 z4 DZ"]

    def string(tag, a, b, phase):
        # a -> ammeter -> R -> L -> EMF -> b ; e drops in the current direction (motor)
        return [f"Vi{tag} {a} i{tag} 0", f"Rc{tag} i{tag} r{tag} {R:.6e}", f"Lc{tag} r{tag} l{tag} {L:.6e}",
                f"Be{tag} l{tag} {b} V='{E:.6e}*sin({2 * math.pi * fe:.8e}*time+{phase:.6f})'"]
    if coils and place == "leg":
        t += string("A", "1", "1v", ph) + string("B", "4", "4v", ph + math.pi)
    if place == "bus":
        # D5 / D6: an ordinary diode knee (n 1), as a real stack has; the near-ideal core model stalls the solver here
        t += ["Cbus bus 0 10e-9", "Rbl bus 0 10e9", ".model NB D(is=1e-12 n=1 rs=10 cjo=0)",
              "Rs bus s5 22e3", "Rs6 bus s6 22e3"]
        if coils:
            t += ["Dd5 s5 c5 NB", "Dd6 s6 c6 NB"]
            t += string("A", "c5", "1", ph) + string("B", "c6", "4", ph + math.pi)
            # snubber across each string: D5 / D6 cut the coil current every cycle; the coil energy needs a path [RH]
            t += [f"RsnA c5 1 {RSN:g}", f"RsnB c6 4 {RSN:g}"]
        else:
            t += ["Dd5 s5 1 NB", "Dd6 s6 4 NB"]
    # power integrators: a B current source into a 1 F cap, so ngspice integrates each power term on its own adaptive
    # step (sampling the output points under-resolves the clamp's current spikes) [IR]
    dc = (CMAX - CMIN) * 0.5 * w
    P = {"eb": f"{dc:.6e}*sin({w:.8e}*time)*0.5*(V({a1})*V({a1})-V({a4})*V({a4}))"}
    if coils and place in ("leg", "bus"):
        bA, bB = ("1v", "4v") if place == "leg" else ("1", "4")
        P["em"] = f"V(lA,{bA})*i(ViA)+V(lB,{bB})*i(ViB)"
        P["ec"] = f"{R:.6e}*(i(ViA)*i(ViA)+i(ViB)*i(ViB))"
    if clamp:
        P["ez"] = "-V(1)*i(Vz1)-V(4)*i(Vz4)"
    if place == "bus":
        P["ebus"] = "V(bus)*V(bus)/10e9"
        P["ers"] = "((V(bus)-V(s5))*(V(bus)-V(s5))+(V(bus)-V(s6))*(V(bus)-V(s6)))/22e3"
        if coils:
            P["esn"] = f"(V(c5,1)*V(c5,1)+V(c6,4)*V(c6,4))/{RSN:g}"
    for nd, ex in P.items():
        t += [f"Bp_{nd} 0 {nd} I='{ex}'", f"Cp_{nd} {nd} 0 1", f"Rp_{nd} {nd} 0 1e18"]
    tstop = n_cyc / F
    ms = 1.0 / F / STEPS
    vecs = ["v(1)", "v(4)"] + [f"v({nd})" for nd in P]
    if place == "bus":
        vecs += ["v(bus)"]
    # every series node starts at its neighbour's voltage (uic: an unset node is 0 V and a 0 V source to a -1 kV node
    # would start with an infinite current)
    SEED_ = seed
    ics = {"1": SEED_, "4": SEED_, a1: SEED_, a4: SEED_, "2": 0.0, "3": 0.0}
    if coils and place in ("leg", "bus"):
        ics.update({f"{p}{s}": SEED_ for p in ("i", "r", "l") for s in ("A", "B")})
    if place == "bus":
        ics.update(bus=SEED_, s5=SEED_, s6=SEED_, c5=SEED_, c6=SEED_)     # bus pre-charged to the seed: D5 / D6 start at 0 V
    ic = ".ic" + "".join(f" v({n})={v:g}" for n, v in ics.items())
    ic += "".join(f" v({nd})=0" for nd in P)
    t += [ic, ".control", f"tran {ms:.4e} {tstop:.6e} uic", "wrdata out.dat " + " ".join(vecs), ".endc",
          f".options reltol={reltol:g} abstol=1e-12 vntol=1e-6 gmin=1e-15 maxstep={ms:.4e} method=gear", ".end"]
    return "\n".join(t) + "\n", vecs, R


def _spice(place, kw, reltol):
    txt, vecs, R = deck(place, reltol=reltol, **kw)
    with tempfile.TemporaryDirectory() as d:
        open(os.path.join(d, "x.cir"), "w").write(txt)
        r = subprocess.run(["ngspice", "-b", "x.cir"], capture_output=True, text=True, timeout=1800, cwd=d)
        try:
            raw = np.loadtxt(os.path.join(d, "out.dat"))
        except (OSError, ValueError):
            return None, None, R, (r.stdout + r.stderr)[-400:]
    return raw[:, 0], {v: raw[:, 2 * j + 1] for j, v in enumerate(vecs)}, R, None


def run(place, **kw):
    for reltol in (1e-5, 1e-4, 1e-3):
        t, cols, R, err = _spice(place, kw, reltol)
        if err:
            return dict(place=place, **kw, error=err)
        done = t[-1] >= 0.99 * kw.get("n_cyc", N_CYC) / F
        if done or not kw.get("clamp", True):
            break
    out = analyse(place, t, cols, R, kw)
    out["reltol"] = reltol
    return out


def _C(t, which):
    s = 0.5 * (1 + np.cos(2 * math.pi * F * t))
    s = s if which == 1 else 1 - s
    return CMIN + (CMAX - CMIN) * s


def _dC(t, which):
    d = -(CMAX - CMIN) * 0.5 * 2 * math.pi * F * np.sin(2 * math.pi * F * t)
    return d if which == 1 else -d


def analyse(place, t, c, R, kw):
    T = 1.0 / F
    N_CYC = kw.get("n_cyc", globals()["N_CYC"])
    cyc = np.floor(t / T).astype(int)
    peaks = [float(np.abs(np.r_[c["v(1)"][cyc == n], c["v(4)"][cyc == n]]).max()) for n in range(N_CYC) if np.any(cyc == n)]
    z = [peaks[i + 1] / peaks[i] for i in range(len(peaks) - 1) if peaks[i] > 0]
    zf = float(np.median(z[1:5])) if len(z) > 5 else None
    if t[-1] < 0.99 * N_CYC * T:                 # ngspice stopped (without the clamp: the pump runs away)
        return dict(place=place, **kw, z_first=zf, aborted=True, t_end_s=float(t[-1]),
                    V_peak_last_kV=float(np.abs(c["v(1)"]).max() / 1e3))
    t0, t1 = (N_CYC - 6) * T, t[-1]

    def mean(nd):                                # mean power over the last 6 cycles from the solver-side integral
        y = c[f"v({nd})"]
        return float((np.interp(t1, t, y) - np.interp(t0, t, y)) / (t1 - t0))
    P_belt = mean("eb")
    out = dict(place=place, **kw, z_first=zf, V_peak_last_kV=peaks[-1] / 1e3, P_belt_W=P_belt)
    if "v(em)" in c:
        P_m, P_cu = mean("em"), mean("ec")
        out.update(P_mech_W=P_m, P_cu_W=P_cu, I_rms_mA=1e3 * math.sqrt(max(P_cu, 0.0) / (2 * R)),
                   E_peak_V=emf_peak(kw.get("k", 1.0), kw.get("m", 6)), T_motor_mNm=P_m / W_REL * 1e3)
    if "v(ez)" in c:
        out["P_clamp_W"] = mean("ez")
    if "v(bus)" in c:
        out["V_bus_kV"] = float(c["v(bus)"][-1] / 1e3)
        out["P_bleed_W"] = mean("ebus")
        out["P_Rs_W"] = mean("ers")
        if "v(esn)" in c:
            out["P_snub_W"] = mean("esn")
        vb0, vb1 = np.interp(t0, t, c["v(bus)"]), np.interp(t1, t, c["v(bus)"])
        out["P_bus_store_W"] = 0.5 * 10e-9 * (vb1 ** 2 - vb0 ** 2) / (t1 - t0)
    out["P_other_W"] = P_belt - sum(out.get(x, 0.0) for x in ("P_mech_W", "P_cu_W", "P_clamp_W", "P_bleed_W", "P_Rs_W",
                                                     "P_bus_store_W", "P_snub_W"))
    out["T_pump_mNm"] = P_belt / W_REL * 1e3
    out["T_net_mNm"] = out.get("T_motor_mNm", 0.0) - out["T_pump_mNm"] - T_DRAG * 1e3
    return out


def main(only=None):
    rows = []
    path = os.path.join(HERE, "switchless_cem_results.json")
    if only:                                     # re-run one placement, keep the other rows
        rows = [r for r in json.load(open(path))["rows"] if r.get("place") != only]

    def rec(tag, place, **kw):
        if only and place != only:
            return None
        r = run(place, **kw)
        r["case"] = tag
        rows.append(r)
        if "error" in r:
            print(f"{tag:44s} ERROR {r['error']}", flush=True); return r
        if r.get("aborted"):
            why = "runs away" if r["V_peak_last_kV"] > 2 * abs(SEED) / 1e3 else "solver stopped"
            print(f"{tag:44s} z {r['z_first']} | {why}: ngspice stopped at {r['V_peak_last_kV']:.0f} kV, "
                  f"t {r['t_end_s']:.3f} s", flush=True); return r
        s = (f"{tag:44s} z {r['z_first'] if r['z_first'] is None else round(r['z_first'], 3)} | V {r['V_peak_last_kV']:6.2f} kV"
             f" | belt {r['P_belt_W']:6.3f} W")
        if "P_mech_W" in r:
            s += (f" | mech {r['P_mech_W']:7.4f} W cu {r['P_cu_W']:7.4f} W  I_rms {r['I_rms_mA']:.3f} mA"
                  f"  E {r['E_peak_V']:.0f} V  T_motor {r['T_motor_mNm']:7.3f} mN m")
        if "P_clamp_W" in r:
            s += f" | clamp {r['P_clamp_W']:.3f} W"
        if "V_bus_kV" in r:
            s += f" | bus {r['V_bus_kV']:.2f} kV"
        print(s + f" | other {r['P_other_W']:.3f} W | T_net {r['T_net_mNm']:.1f} mN m", flush=True)
        return r

    rec("bare core, no clamp (z check)", "leg", coils=False, clamp=False)
    BUSKW = dict(n_cyc=160)                       # the bus loads the pump: it climbs at z ~1.03 per cycle, so run longer
    rec("BUS, no coils", "bus", coils=False, **BUSKW)
    rec("bare core + 20 kV clamp", "leg", coils=False)
    for k in (1.0, 5.0, 20.0):
        rec(f"LEG k {k} m 6 phi 0, no clamp", "leg", k=k, clamp=False)
    for k in (1.0, 5.0, 10.0, 20.0, 40.0):
        for phi in (0, 45, 90, 135, 180, 225, 270, 315):
            rec(f"LEG k {k} m 6 phi {phi}", "leg", k=k, phi_deg=phi)
    rec("LEG k 20 m 3 (3 utrons) phi 0", "leg", k=20.0, m=3)
    rec("LEG k 20 m 3 (3 utrons) phi 90", "leg", k=20.0, m=3, phi_deg=90)
    for k in (1.0, 20.0):
        for phi in (0, 90, 180, 270):
            rec(f"BUS k {k} m 6 phi {phi}", "bus", k=k, phi_deg=phi, **BUSKW)
    json.dump(dict(rpm=RPM, f_cycles=F, V_op=V_OP, T_drag_mNm=T_DRAG * 1e3, rows=rows),
              open(path, "w"), indent=1, default=float)


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "one":
        print(json.dumps(run(sys.argv[2], **json.loads(sys.argv[3])), default=float)[:1500])
    else:
        main(sys.argv[1] if len(sys.argv) > 1 else None)
