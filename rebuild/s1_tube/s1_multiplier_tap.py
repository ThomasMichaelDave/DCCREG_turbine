"""rebuild/s1_tube/s1_multiplier_tap.py -- Stage 1: a two-stage multiplier on top of the S0 doubler, tapped into a
buffer instead of a dissipating limiter.

The designer (2026-10-14): "I would like to see the maximum voltage difference between two nodes of the multiplier
considering we add a two stage on top of the doubler. Where do we tap that difference? The idea is not to dissipate
anything, ideally I want all energy cycling back and forth, with limited losses. Can we do that with a buffer
somewhere for instance?"

The principle (CONVENTIONS.md, the equalization-is-the-pump rule, locked): the pump's own transfers cannot be resonated
for recovery; only a downstream SINK transfer recovers. A buffer at the multiplier's tap is such a sink: the surplus
that a clamp would burn is stored instead [OC: an ideal capacitor sink is lossless].

Cases (ideal diodes, S1's air values, the S0 core unchanged; the general solver of s1_stress_options.py):
  B0  the S0 core, its nodes 1 and 4 into one buffer through a diode each (the bare core's limit as storage);
  BP  core + a 2-stage Cockcroft-Walton on node 1 and one on node 4, both positive; their tops tied to one buffer
      between the top and REF;
  BB  core + a 2-stage positive CW on node 1 and a 2-stage NEGATIVE CW on node 4 (every ladder diode reversed): the
      buffer sits between the + top and the - top, floating, so the tap is the difference of the two ladders.
The buffer is a capacitor of 1e4 x C_min [IR: a stiff store; a real one is a capacitor bank behind a converter, de
Queiroz's §II.B and his Fig. 2]. After each cycle its energy gain is counted and the WHOLE state is divided by the
buffer's voltage, so V_buf returns to 1: with ideal diodes and linear capacitors, scaling every voltage alike is an
exact symmetry [OC], so this holds the buffer at a fixed voltage without injecting any charge.

Reported per case, in the limited steady state:
  - every node's peak and the largest voltage between ANY two nodes over a cycle (÷ V_buf);
  - every discrete part's peak (diode reverse, fixed capacitor), and the varicap nodes' peak;
  - the energy into the buffer a cycle, E_buf, and the mechanical work into the varicaps a cycle,
    W_mech = -sum 1/2 V^2 dC [OC: dE = -1/2 V^2 dC at fixed charge], so E_buf / W_mech is the share stored;
  - the energy that cycles: the varicaps' stored-energy swing within the cycle, against the net W_mech.
Units: C in C_min, V in V_buf; energies in C_min V_buf^2 (x 128.4 pF x V_buf^2 for joules).

Writes rebuild/s1_tube/s1_multiplier_tap_results.json.
Usage: python3 rebuild/s1_tube/s1_multiplier_tap.py
"""
import json
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import s1_stress_options as so  # noqa: E402  (Circuit, c1, c2, the air values)

CM = so.CMIN                                   # pF; the varicaps in pF as in so
CA = so.CA
C_BUF = 1e4 * CM      # stiff enough: the state is rescaled to V_buf = 1 every cycle (below)
N_HALF = 600
CYCLES = 700
F = 120.0


def core():
    caps = [(1, 0, so.c1), (4, 0, so.c2), (1, 2, CA), (3, 4, CA)]
    diodes = [(0, 2), (0, 3), (3, 1), (2, 4)]
    return caps, diodes, 5


def ladder(caps, diodes, nxt, drive, M, sign):
    """a Villard / Cockcroft-Walton ladder of M stages driven by node `drive`; sign -1 reverses every diode."""
    o = list(range(nxt, nxt + M)); nxt += M
    s = list(range(nxt, nxt + M)); nxt += M
    po, ps = drive, 0
    for i in range(M):
        caps += [(po, o[i], CA), (ps, s[i], CA)]
        for a, c in ((ps, o[i]), (o[i], s[i])):
            diodes.append((a, c) if sign > 0 else (c, a))
        po, ps = o[i], s[i]
    return nxt, s[-1]


def build(case, M=2):
    caps, diodes, nxt = core()
    if case == "B0":
        buf = nxt; nxt += 1
        caps.append((buf, 0, C_BUF))
        diodes += [(1, buf), (4, buf)]
        return so.Circuit("B0 core -> buffer", nxt - 1, caps, diodes, (1, 4)), dict(buf=(buf, 0))
    if case == "BP":
        nxt, t1 = ladder(caps, diodes, nxt, 1, M, +1)
        nxt, t4 = ladder(caps, diodes, nxt, 4, M, +1)
        buf = nxt; nxt += 1
        caps.append((buf, 0, C_BUF))
        diodes += [(t1, buf), (t4, buf)]
        return so.Circuit(f"BP core + 2 x CW{M} (+,+) -> buffer to REF", nxt - 1, caps, diodes, (1, 4)), \
            dict(buf=(buf, 0), tops=(t1, t4))
    if case == "BB":
        nxt, t1 = ladder(caps, diodes, nxt, 1, M, +1)
        nxt, t4 = ladder(caps, diodes, nxt, 4, M, -1)
        caps.append((t1, t4, C_BUF))
        return so.Circuit(f"BB core + CW{M} (+) on 1, CW{M} (-) on 4 -> buffer across the tops", nxt - 1, caps,
                          diodes, (1, 4)), dict(buf=(t1, t4), tops=(t1, t4))
    raise ValueError(case)


def run(case):
    c, meta = build(case)
    n = c.n
    a, b = meta["buf"]

    def vbuf(v):
        return (v[a - 1] if a else 0.0) - (v[b - 1] if b else 0.0)

    v = np.zeros(n)
    v[0] = v[3] = 0.05                              # a small seed on the varicaps
    if b:                                           # the floating buffer: +0.5 / -0.5
        v[a - 1], v[b - 1] = 0.5, -0.5
    else:
        v[a - 1] = 1.0
    v = c.step(c.K(0.0), c.K(0.0) @ v)
    v = v / vbuf(v)
    sgrid = np.r_[np.linspace(0, 1, N_HALF + 1), np.linspace(1, 0, N_HALF + 1)[1:]]
    hist = []
    prev = v.copy()
    for k in range(CYCLES + 1):
        W = 0.0
        R = []
        e_var = []
        K0 = c.K(0.0)
        E0 = 0.5 * v @ K0 @ v
        Vb0 = vbuf(v)
        for s0, s1 in zip(sgrid[:-1], sgrid[1:]):
            Ka, Kb = c.K(s0), c.K(s1)
            vo = v
            v = c.step(Kb, Ka @ v)
            for p, cf in ((1, so.c1), (4, so.c2)):          # work into the varicaps: -1/2 V^2 dC, trapezoid [OC]
                W += -0.25 * (vo[p - 1] ** 2 + v[p - 1] ** 2) * (cf(s1) - cf(s0))
            R.append(v.copy())
            e_var.append(sum(0.5 * cf(s1) * v[p - 1] ** 2 for p, cf in ((1, so.c1), (4, so.c2))))
        E1 = 0.5 * v @ K0 @ v
        Vb1 = vbuf(v)
        E_buf = 0.5 * C_BUF * (Vb1 ** 2 - Vb0 ** 2)          # the store's gain this cycle [OC]
        hist.append(dict(k=k, W_mech=W, E_buf=E_buf, dE_total=E1 - E0, v1=float(np.max(np.array(R)[:, 0]))))
        v = v / Vb1                                          # the exact rescale: V_buf back to 1
        R = [r / Vb1 for r in R]                             # (the traced cycle at the same scale, within 1/Vb1)
        if k >= 60 and np.abs(v - prev).max() < 1e-10:
            break
        prev = v.copy()
    R = np.array(R)
    full = np.hstack([np.zeros((len(R), 1)), R])            # column 0 = REF
    diff = np.abs(full[:, :, None] - full[:, None, :]).max(axis=0)
    i, j = np.unravel_index(np.argmax(diff), diff.shape)

    def nv(x):
        return full[:, x]
    d_rev = [float((nv(cth) - nv(an)).max()) for an, cth in c.diodes]
    fixed = [(x, y) for x, y, cv in c.caps if not callable(cv) and cv < C_BUF]
    c_fix = [float(np.abs(nv(x) - nv(y)).max()) for x, y in fixed]
    v_var = float(max(np.abs(nv(1)).max(), np.abs(nv(4)).max()))
    h = hist[-1]
    out = dict(name=c.name, cycles_run=len(hist), converged=len(hist) <= CYCLES,
               node_peaks={str(k): float(np.abs(nv(k)).max()) for k in range(1, n + 1)},
               max_pair=dict(nodes=[int(i), int(j)], V=float(diff[i, j])),
               varicap_peak=v_var, diode_rev=d_rev, diode_max=max(d_rev), cap_fixed=c_fix, cap_max=max(c_fix),
               E_buf=h["E_buf"] / CM, W_mech=h["W_mech"] / CM, stored_share=h["E_buf"] / h["W_mech"],
               loss_share=(h["W_mech"] - h["dE_total"]) / h["W_mech"],
               E_var_swing=float((max(e_var) - min(e_var)) / CM), E_var_mean=float(np.mean(e_var) / CM),
               meta={k: list(v) if isinstance(v, tuple) else v for k, v in meta.items()})
    out["cycling_over_net"] = out["E_var_swing"] / out["W_mech"]
    # scaled: the varicap peak set to the record's 13.13 kV [RH: a reference scale only, not a design value]
    vs = 13.13e3 / v_var
    out["at_varicap_13p13kV"] = dict(V_buf_kV=vs / 1e3, max_pair_kV=out["max_pair"]["V"] * vs / 1e3,
                                     diode_max_kV=out["diode_max"] * vs / 1e3, cap_max_kV=out["cap_max"] * vs / 1e3,
                                     P_buf_W=out["E_buf"] * CM * 1e-12 * vs ** 2 * F,
                                     P_mech_W=out["W_mech"] * CM * 1e-12 * vs ** 2 * F)
    return out


def main():
    res = dict(inputs=dict(Cmin_pF=CM, Cmax_pF=so.CMAX, Ca_pF=CA, M=2, N_half=N_HALF, F_Hz=F), rows=[])
    for case in ("B0", "BP", "BB"):
        r = run(case)
        res["rows"].append(r)
        s = r["at_varicap_13p13kV"]
        print(f"{r['name']}: {r['cycles_run']} cycles{'' if r['converged'] else ' (NOT converged)'}")
        print(f"   ÷V_buf: varicap {r['varicap_peak']:.3f}, max pair {r['max_pair']['V']:.3f} {r['max_pair']['nodes']}, "
              f"diode max {r['diode_max']:.3f}, cap max {r['cap_max']:.3f}")
        print(f"   stored share {r['stored_share']:.4f}, step loss {r['loss_share']:.2e}; cycling/net {r['cycling_over_net']:.2f}; "
              f"at 13.13 kV varicap: V_buf {s['V_buf_kV']:.2f} kV, max pair {s['max_pair_kV']:.2f} kV, "
              f"diode {s['diode_max_kV']:.2f} kV, P_buf {s['P_buf_W']:.3f} W of P_mech {s['P_mech_W']:.3f} W")
        print("   node peaks", {k: round(x, 3) for k, x in r["node_peaks"].items()})
    json.dump(res, open(os.path.join(HERE, "s1_multiplier_tap_results.json"), "w"), indent=1)


if __name__ == "__main__":
    main()
