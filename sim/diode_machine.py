"""sim/diode_machine.py -- the DIODE machine: the bare de Queiroz electronic Bennet doubler (4 diodes, no flying bucket,
no spark gaps) on the disc or the tube geometry, and the power available to the motor C-EMs against operating voltage.

Circuit: pump_engine.core_net (the solveDoubler4 topology: nodes 1-4, D1 2->ref, D2 3->ref, D3 1->3, D4 4->2, C1, C2,
Ca, Cb, Cpar) with CONTINUOUS varicaps (stack_sizing.core_net). No Cx / Lx islands, no SG / BS gaps, no clocking decks.
The tube layout drops the Cx vanes and the clocking decks (plates bucket=False).

C-EM placements, compared side by side:
- SERIES: each 6-coil group in series with a rail diode (A group with D1, B group with D2). The coils carry that diode's
  conduction current, which with diodes flows for milliseconds while C changes (not a us spark pulse).
- DC TAP: the C-EMs are a motor fed from the pump's surplus (load diodes + reservoir), the core unchanged.
Utrons: IRON (reluctance, torque = 1/2 i^2 dL/dtheta) or PM (permanent magnet, torque = k_t i, k_t = N dPhi n_utron / 2).

Everything is reported against the operating voltage (highest node) up to the gap breakdown: the engine is scale-free, so
energies go as V^2, currents as V, iron torque as V^2, PM torque as V.

Stator balance (stator standing, belt holding the relative speed): T_net = T_motor - T_pump - T_bearing - T_air, with
T_pump = W per cycle x cycles per rev / 2 pi, the pump's own reaction torque on the stator [OC].

Tags: [OC] standard physics, [IR] modelling choice, [RH] estimate / default to be replaced by data.
Usage: python3 sim/diode_machine.py   (prints the default disc and tube)
"""
import json
import math
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)
import stack_sizing as S                                  # noqa: E402
import pump_sizing as PS                                  # noqa: E402

CEM_DEFAULTS = {
    # per coil; 6 coils per group (A, B). dLdth: peak dL/dtheta of one coil with the 0.40 mm winding (N 1846):
    # disc from sim/cem_inductance.py (0.1 mm Si-steel core), tube from sim/tube_ledger.py (r_u 130) [IR]
    "disc": dict(n_coils=6, N=1846, R_coil=44.5, dLdth=2.761, swing=0.135, n_utron=6, dphi_mWb=0.27, T_bear_mNm=70.0,
                 T_air_mNm=0.0),
    "tube": dict(n_coils=6, N=1846, R_coil=44.5, dLdth=0.979, swing=0.128, n_utron=3, dphi_mWb=0.27, T_bear_mNm=14.7,
                 T_air_mNm=4.6),
}
MOTOR_DEFAULTS = dict(utron="iron", phase=0.5, eta_pm=0.8, eta_iron=None, V_min_kV=2.0, n_sweep=10, V_max_kV=None)
# phase: fraction of the coil current that falls in the torque-producing window (rising L for iron, the right flux slope
# for PM); 0.5 = conduction spread evenly over both slopes. eta_iron None = the swing (dL/L_aligned) as a DC-tap
# reluctance-motor efficiency bound. All [RH].


def size(geometry, plates=None, choices=None):
    p = dict(plates or {})
    if geometry == "tube":
        p.setdefault("bucket", False)
    return S.size_stack(geometry, p, choices)


def _cfg(lad):
    import pump_synth as SY
    fi = dict(SY.FIRING_DEFAULTS) if hasattr(SY, "FIRING_DEFAULTS") else SY.split({})[2]
    return SY.engine_cfg(lad, fi)


def _conduction(net, rec, s, T_cyc):
    """per rail diode (D1, D2): charge per cycle and conduction time from the eigen-cycle record (scaled by s)."""
    out = {}
    pts = rec["points"]
    for dn, node in (("D1", "2"), ("D2", "3")):
        i = net.idx[node]
        Q, t = 0.0, 0.0
        for a, b in zip(pts[:-1], pts[1:]):
            if dn in a["cond"] and dn in b["cond"]:
                qa = (net.K(a["th"]) @ a["V"])[i]
                qb = (net.K(b["th"]) @ b["V"])[i]
                Q += abs(qb - qa)
                dth = (b["th"] - a["th"]) % 60.0
                t += dth / 60.0 * T_cyc
        out[dn] = dict(Q_C=Q * s, t_cond_s=t)
    return out


def evaluate(geometry="tube", plates=None, choices=None, cem=None, motor=None, log=None):
    import rt_engine as RT
    lad = size(geometry, plates, choices)
    c = dict(CEM_DEFAULTS[geometry]); c.update(cem or {})
    mo = dict(MOTOR_DEFAULTS); mo.update(motor or {})
    cfg = _cfg(lad)
    net = S.core_net(cfg)
    m = RT.run(net, cfg, record=True, log=log)
    rec = m["rec"]
    zs = [h["z"] for h in m["hist"][-4:]]
    spread = (max(zs) - min(zs)) / max(zs) if zs else 0.0     # two near-identical switching patterns can alternate [IR]
    settled = bool(m["converged"] or spread < 1e-3)
    V = np.array([p["V"] for p in rec["points"]])
    top = float(np.abs(V).max())
    V_ref = 20e3
    s = V_ref / top
    geo = lad.get("tube") or lad.get("plates")
    n_sec = geo.get("N_sec", 12)
    rpm = lad["choices"]["rpm"]
    cyc_rev = math.ceil(n_sec / 2)
    f = cyc_rev * rpm / 60.0
    w_rel = 2 * math.pi * rpm / 60.0
    W = rec["ledger"]["W"] * s * s
    dE = (rec["E1"] - rec["E0"]) * s * s
    L = sum(rec["by"].values()) * s * s
    cond = _conduction(net, rec, s, 1.0 / f)
    g, diel = geo.get("g_vMm"), geo.get("dielectric", "air")
    V_bd = S.gap_breakdown_kV(g, diel) * 1e3
    V_max = (mo["V_max_kV"] * 1e3) if mo["V_max_kV"] else V_bd
    k_t = c["N"] * c["dphi_mWb"] * 1e-3 * c["n_utron"] / 2.0          # N m / A per coil (PM) [RH]
    eta_iron = c["swing"] if mo["eta_iron"] is None else mo["eta_iron"]
    T_air = c["T_air_mNm"] * 1e-3 if diel == "air" else 0.0
    rows = []
    n = max(2, int(mo["n_sweep"]))
    for j in range(n):
        Vop = mo["V_min_kV"] * 1e3 + (V_max - mo["V_min_kV"] * 1e3) * j / (n - 1)
        k = Vop / V_ref
        P_belt, P_sur, P_loss = W * f * k * k, dE * f * k * k, L * f * k * k
        T_pump = W * k * k * cyc_rev / (2 * math.pi)
        # SERIES: the coil groups carry the D1 / D2 conduction current
        I2 = sum((cond[d]["Q_C"] * k) ** 2 / cond[d]["t_cond_s"] for d in cond if cond[d]["t_cond_s"] > 0)   # A^2 s / cycle, both groups
        Iavg = sum(cond[d]["Q_C"] * k * f for d in cond)                                                      # A, summed over groups
        if mo["utron"] == "pm":
            T_ser = mo["phase"] * c["n_coils"] * k_t * Iavg
        else:
            T_ser = mo["phase"] * c["n_coils"] * 0.5 * c["dLdth"] * I2 * f
        P_ser = T_ser * w_rel
        P_cu = c["n_coils"] * c["R_coil"] * I2 * f
        # DC TAP: a motor on the surplus
        eta = mo["eta_pm"] if mo["utron"] == "pm" else eta_iron
        P_tap = eta * P_sur
        T_tap = P_tap / w_rel
        T_drag = c["T_bear_mNm"] * 1e-3 + T_air
        rows.append(dict(V_kV=Vop / 1e3, margin=V_bd / Vop, P_belt_W=P_belt, P_surplus_W=P_sur, P_loss_W=P_loss,
                         T_pump_mNm=T_pump * 1e3, T_drag_mNm=T_drag * 1e3,
                         series=dict(T_mNm=T_ser * 1e3, P_mech_W=P_ser, P_cu_W=P_cu, I_avg_mA=Iavg * 1e3,
                                     surplus_left_W=P_sur - P_ser - P_cu, valid=bool(P_ser + P_cu <= P_belt + 1e-12),
                                     T_net_mNm=(T_ser - T_pump - T_drag) * 1e3),
                         tap=dict(T_mNm=T_tap * 1e3, P_mech_W=P_tap, eta=eta, T_net_mNm=(T_tap - T_pump - T_drag) * 1e3)))
    Lg = lad["ladder"]
    tg = lad.get("tube_geometry") or {}
    return json.loads(json.dumps(dict(
        geometry=geometry, ladder=lad,
        core=dict(z=m["z"], converged=bool(m["converged"]), settled=settled, z_spread=spread, top_node_ref_kV=V_ref / 1e3, W_mJ=W * 1e3, surplus_mJ=dE * 1e3,
                  loss_mJ=L * 1e3, closure_J=W - dE - L, eta=dE / W if W > 0 else None, cycles_per_s=f, cycles_per_rev=cyc_rev,
                  conduction={d: dict(Q_uC=cond[d]["Q_C"] * 1e6, t_cond_ms=cond[d]["t_cond_s"] * 1e3) for d in cond}),
        breakdown=dict(gap_mm=g, dielectric=diel, V_bd_kV=V_bd / 1e3),
        cem=c, motor=dict(mo, k_t_NmA=k_t, eta_iron=eta_iron),
        summary=dict(C_max_pF=Lg["C_max"]["value"], C_min_pF=Lg["C_min"]["value"], kappa=lad["kappa_C"],
                     length_mm=tg.get("L_total_mm"), diameter_mm=tg.get("diameter_mm") or lad.get("rotor_dia_mm")),
        sweep=rows), default=float))


def _selftest():
    """cheap checks (no engine run): the tube without the bucket drops the Cx vanes and clocking decks."""
    lad = size("tube")
    kinds = {e["kind"] for e in lad["tube_geometry"]["elements"]}
    assert "Cx vane" not in kinds and "clocking" not in kinds and "clk tip" not in kinds, kinds
    assert abs(CEM_DEFAULTS["tube"]["N"] * 0.27e-3 * 3 / 2 - 0.748) < 0.01
    return True


SELFTEST_OK = _selftest()

if __name__ == "__main__":
    for geo, pl in (("disc", dict(dielectric="air")), ("disc", dict(dielectric="vacuum")), ("tube", {})):
        for ut in ("iron", "pm"):
            r = evaluate(geo, plates=pl, choices=dict(rpm=300.0), motor=dict(utron=ut, n_sweep=4))
            co, sm = r["core"], r["summary"]
            print(f"{geo} {r['breakdown']['dielectric']} g {r['breakdown']['gap_mm']} mm, {ut}: z {co['z']:.4f} conv {co['converged']}, "
                  f"C {sm['C_max_pF']:.0f}/{sm['C_min_pF']:.1f} pF, length {sm['length_mm']}, V_bd {r['breakdown']['V_bd_kV']:.1f} kV, "
                  f"cond {co['conduction']}")
            for w in r["sweep"]:
                se, tp = w["series"], w["tap"]
                print(f"   {w['V_kV']:5.1f} kV: belt {w['P_belt_W']:.2f} W surplus {w['P_surplus_W']:.2f} W | pump {w['T_pump_mNm']:.1f} drag "
                      f"{w['T_drag_mNm']:.1f} mN m | SERIES T {se['T_mNm']:.3g} mN m P {se['P_mech_W']:.3g} W (I {se['I_avg_mA']:.3f} mA) net "
                      f"{se['T_net_mNm']:.1f} | TAP T {tp['T_mNm']:.2f} mN m P {tp['P_mech_W']:.2f} W net {tp['T_net_mNm']:.1f}")
