"""rebuild/s1_tube/s1_pulsed_core.py -- Stage 1: a pulsed core field from the S0 doubler.

The designer (2026-10-15): "The core is meant to be pulsed yes, it's meant to go back and forth between the top and
bottom section. Potentially we need to account for it in the schematic. Lets say the centre is the neutral and top and
bottom switch polarities when going through their phases. Then how do we account for it in the doubler. Is a mere
phase shift of the top varicap against the bottom varicap enough?"

Questions answered (ideal diodes, S1's air values, the frozen S0 core; the general solver of s1_stress_options.py):
  A  the gain z per cycle against the phase shift phi between C1 (top) and C2 (bottom): 0 deg = in phase, 180 deg = S0;
  B  at S0's antiphase, the waveforms of the field-making quantities: the difference V1 - V4 (what drives a field
     between a top and a bottom electrode, through a symmetric centre) and the common mode (V1 + V4) / 2;
     in the growing mode, and in the limited state with the B0 buffer of s1_multiplier_tap.py;
  C  the core as a load in the schematic: a capacitor C_k between node 1 and node 4 (the electrode pair across the
     core), with the record's ring strays to REF on each; z and the difference's amplitude against C_k;
  D  the neutral: with the centre as the reference (a symmetric midpoint between nodes 1 and 4), where REF (the
     varicaps' stator side) then sits.
The capacitance profile is S1's: linear in the rotor angle over each half cycle (a triangle in time) [IR].

Writes rebuild/s1_tube/s1_pulsed_core_results.json.
Usage: python3 rebuild/s1_tube/s1_pulsed_core.py
"""
import json
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import s1_stress_options as so  # noqa: E402

CM, CA = so.CMIN, so.CA
NT = 3000                     # steps per cycle
CYC = 40
F = 120.0
K_NULL = 0.25457701665749793  # (kV/cm)/kV across the rings at the null, sim/diodes_real_results.json k_null_kV_cm_per_kV
C_RREF, C_RR = 5.1, 1.1       # pF, the record's ring strays (sim/hub-rings-build-findings.md, record checks)
V_REF_PEAK = 13.13e3          # V, the record's varicap peak: a reference scale only [RH]


def tri(t):
    t = t % 1.0
    return 2 * t if t < 0.5 else 2 - 2 * t


def c_top(t):
    return so.c1(tri(t))


def c_bot(phi):
    return lambda t: so.c1(tri(t + phi / 360.0))   # phi = 180 gives so.c2 exactly [OC: tri(t+1/2) = 1 - tri(t)]


def core(phi=180.0, ck=0.0, c_rref=0.0, buffer=False):
    caps = [(1, 0, c_top), (4, 0, c_bot(phi)), (1, 2, CA), (3, 4, CA)]
    diodes = [(0, 2), (0, 3), (3, 1), (2, 4)]
    n = 4
    if ck:
        caps.append((1, 4, ck))
    if c_rref:
        caps += [(1, 0, c_rref), (4, 0, c_rref)]
    if buffer:
        n = 5
        caps.append((5, 0, 1e4 * CM))
        diodes += [(1, 5), (4, 5)]
    return so.Circuit(f"core phi={phi:g} ck={ck:g} crref={c_rref:g} buf={buffer}", n, caps, diodes, (1, 4))


def cycle(c, v, trace=False):
    ts = np.linspace(0, 1, NT + 1)
    R = []
    for t0, t1 in zip(ts[:-1], ts[1:]):
        v = c.step(c.K(t1), c.K(t0) @ v)
        if trace:
            R.append(v.copy())
    return v, (np.array(R) if trace else None)


def growth(c):
    v = np.zeros(c.n)
    v[0] = v[3] = 1.0
    v = c.step(c.K(0.0), c.K(0.0) @ v)
    zs = []
    for _ in range(CYC):
        v = v / np.abs(v).max()
        v0 = v.copy()
        v, _ = cycle(c, v)
        zs.append(float(np.abs(v).max() / np.abs(v0).max()))
    conv = abs(zs[-1] / zs[-2] - 1) < 1e-4
    v = v / np.abs(v).max()
    v, R = cycle(c, v, trace=True)
    R = R / zs[-1] ** np.linspace(0, 1, len(R))[:, None]      # the growth within the cycle divided out [OC]
    return zs[-1], conv, R


def limited(c):
    """the B0 buffer held at 1 by the exact rescale each cycle (s1_multiplier_tap.py's method)."""
    v = np.zeros(c.n)
    v[0] = v[3] = 0.05
    v[4] = 1.0
    v = c.step(c.K(0.0), c.K(0.0) @ v)
    v = v / v[4]
    prev = v.copy()
    for k in range(400):
        v, _ = cycle(c, v)
        v = v / v[4]
        if k > 30 and np.abs(v - prev).max() < 1e-10:
            break
        prev = v.copy()
    v, R = cycle(c, v, trace=True)
    return R / v[4], k + 1


def waves(R):
    """the field-making quantities over one cycle, divided by the varicap nodes' peak."""
    v1, v4 = R[:, 0], R[:, 3]
    pk = max(np.abs(v1).max(), np.abs(v4).max())
    dif, cm = (v1 - v4) / pk, 0.5 * (v1 + v4) / pk
    spec = np.abs(np.fft.rfft(dif)) / len(dif) * 2
    return dict(
        varicap_min_over_peak=float(min(v1.min(), v4.min()) / pk),
        diff_max=float(dif.max()), diff_min=float(dif.min()), diff_mean=float(dif.mean()),
        diff_fundamental_amp=float(spec[1]), diff_h2_amp=float(spec[2]), diff_h3_amp=float(spec[3]),
        diff_rms=float(np.sqrt((dif ** 2).mean())),
        cm_mean=float(cm.mean()), cm_min=float(cm.min()), cm_max=float(cm.max()),
        # D: the centre (a symmetric midpoint of 1 and 4) as the neutral; REF then sits at -cm
        top_vs_neutral=[float((dif / 2).min()), float((dif / 2).max())],
        ref_vs_neutral=[float(-cm.max()), float(-cm.min())],
        trace_t=np.linspace(0, 1, len(dif) + 1)[1:][::30].tolist(),
        trace_diff=dif[::30].tolist(), trace_cm=cm[::30].tolist(),
        trace_v1=(v1 / pk)[::30].tolist(), trace_v4=(v4 / pk)[::30].tolist())


def scaled(w):
    s = V_REF_PEAK / 1e3
    return dict(diff_pp_kV=(w["diff_max"] - w["diff_min"]) * s, diff_peak_kV=max(w["diff_max"], -w["diff_min"]) * s,
                E_null_peak_kV_cm=K_NULL * max(w["diff_max"], -w["diff_min"]) * s,
                E_null_pp_kV_cm=K_NULL * (w["diff_max"] - w["diff_min"]) * s,
                ref_vs_neutral_kV=[x * s for x in w["ref_vs_neutral"]])


def main():
    res = dict(inputs=dict(Cmin_pF=CM, Cmax_pF=so.CMAX, Ca_pF=CA, steps_per_cycle=NT, F_Hz=F, k_null=K_NULL,
                           ring_strays_pF=dict(to_ref=C_RREF, ring_ring=C_RR), varicap_peak_scale_V=V_REF_PEAK))
    # A: the phase shift
    res["A_phase"] = []
    for phi in (0, 30, 60, 90, 120, 150, 165, 180):
        z, conv, _ = growth(core(phi))
        res["A_phase"].append(dict(phi_deg=phi, z_cycle=z, converged=conv))
        print(f"A phi {phi:3d}: z {z:.5f}{'' if conv else ' (not converged)'}")
    # B: antiphase waveforms, growth and limited
    z, conv, R = growth(core())
    res["B_growth"] = dict(z_cycle=z, **waves(R))
    Rl, ncyc = limited(core(buffer=True))
    wl = waves(Rl)
    res["B_limited_B0"] = dict(cycles=ncyc, **wl, at_13p13kV=scaled(wl))
    for key in ("B_growth", "B_limited_B0"):
        w = res[key]
        print(f"B {key}: diff {w['diff_min']:+.3f}..{w['diff_max']:+.3f} mean {w['diff_mean']:+.1e} "
              f"fund {w['diff_fundamental_amp']:.3f} h2 {w['diff_h2_amp']:.1e} h3 {w['diff_h3_amp']:.3f}; "
              f"cm {w['cm_min']:.3f}..{w['cm_max']:.3f}; varicap min {w['varicap_min_over_peak']:.3f}")
    print("   limited at 13.13 kV:", {k: (round(v, 3) if isinstance(v, float) else [round(x, 3) for x in v])
                                       for k, v in res["B_limited_B0"]["at_13p13kV"].items()})
    # C: the core as a load across 1-4 (and the ring strays to REF)
    res["C_load"] = []
    for ck, cr in ((0, 0), (C_RR, C_RREF), (5, C_RREF), (20, C_RREF), (50, C_RREF), (128.4, C_RREF)):
        z, conv, R = growth(core(ck=ck, c_rref=cr))
        Rl, _ = limited(core(ck=ck, c_rref=cr, buffer=True))
        w, wl = waves(R), waves(Rl)
        # the energy that swings in C_k each half cycle, at the 13.13 kV varicap scale [OC: 1/2 C dV^2 terms]
        e_pk = 0.5 * ck * 1e-12 * (max(wl["diff_max"], -wl["diff_min"]) * V_REF_PEAK) ** 2
        res["C_load"].append(dict(ck_pF=ck, c_rref_pF=cr, z_cycle=z, converged=conv,
                                  diff_amp_growth=max(w["diff_max"], -w["diff_min"]),
                                  diff_amp_limited=max(wl["diff_max"], -wl["diff_min"]),
                                  E_ck_peak_J_at_13p13kV=e_pk, E_ck_swing_W_at_120Hz=2 * e_pk * F))
        r = res["C_load"][-1]
        print(f"C ck {ck:6.1f} crref {cr:3.1f}: z {z:.5f}  diff amp growth {r['diff_amp_growth']:.3f} "
              f"limited {r['diff_amp_limited']:.3f}  E_ck {e_pk*1e3:.3f} mJ")
    json.dump(res, open(os.path.join(HERE, "s1_pulsed_core_results.json"), "w"), indent=1)


if __name__ == "__main__":
    main()
