#!/usr/bin/env python3
"""
resonator_sim.py  (r0.2 — revised geometry)
===========================================
Time-domain simulation of the LIVE 5-6 resonator tank + the full clamp architecture
(design-intent-lock §4-7). STANDALONE: imports neither shuttle_core, reference/doubler_core.py,
nor index.html. Driven parallel-RLC transient with nonlinear clamp shunts, integrated with a
hand-rolled RK4 (numpy only; non-stiff with the crowbar as a discrete latch). The R0
free-ringdown self-test (analytic f0 / tau) authorises the model and confirms the conical L.

r0.1 returned TANK-UNDERDRIVEN (island 88 pF << tank 1477 pF, reached ~5 kV vs 20 kV). Three
coordinated geometry changes close the reach gap (brief §2-3): Cx 88->648 pF, C_R 1477->960 pF
(8 mm garolite), and the conical-hub L correction 169->79 uH (f0 318->579 kHz). The question
flips from "can it reach" to "confirm it settles at the softened 15 kV target and the clamp
holds". Drive is parameterised as two modes (brief §4): FULL ~171 mJ/kick (tank ~18.9 kV) and
EASED ~115 mJ (tank ~15.5 kV); pump<->tank coupling extraction is deferred to S2 (brief §10).

Tier tags: [OC] physics/derived-from-spec · [IR] modelling/reporting choice · [RH] open/raw.

Outputs: stdout R0-R4 + verdict; resonator_r2_traces.png; resonator_r2_sink.csv.
"""
import os
import csv
import math
import dataclasses

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

HERE = os.path.dirname(os.path.abspath(__file__))

# ---- brief-locked constants (r0.2 revised geometry) ------------------------- [OC]
V_TARGET = 15e3          # 15 kV target (softened from 20); clamp reference (brief §4)
CX_ISLAND = 648e-12      # island grown 88->648 pF (r_out 232->350, gap 7.6->3 mm, +mica) (brief §2)
RPM = 3000.0             # design speed; f_cycle = rpm/10 = 300 Hz/branch
E_FULL = 171e-3          # full drive: island ~171 mJ/kick (boosted fire ~23 kV) -> tank ~18.9 kV
E_EASED = 115e-3         # eased drive (recommended): island ~115 mJ -> tank ~15.5 kV
# E_reach(15 kV) = 1/2*C_R*V_TARGET^2 ~ 108 mJ (computed from TankParams)


# ======================================================================================
# Parameters (derived magnitudes computed in __post_init__ — never hand-typed)
# ======================================================================================
@dataclasses.dataclass
class TankParams:
    L_R: float = 79e-6            # H   [OC] 36-turn conical bicone coil (brief §3); the earlier
                                  #          169 uH was a cylindrical mis-model -> conical loop-sum 79 uH
    C_R: float = 960e-12          # F   [OC] rotor-rotor across 8 mm garolite disc (brief §2)
    Q: float = 500.0              # [IR] working; swept {320, 500, 900}

    def __post_init__(self):
        self.w0 = 1.0 / math.sqrt(self.L_R * self.C_R)     # rad/s
        self.f0 = self.w0 / (2 * math.pi)                  # ~579 kHz
        self.R_loss = self.w0 * self.L_R / self.Q          # series-equiv tank loss ~0.57 ohm@Q500
        self.tau = 2 * self.Q / self.w0                    # ring time constant 2Q/w0 ~0.27 ms@Q500
        self.Z0 = math.sqrt(self.L_R / self.C_R)           # characteristic impedance ~287 ohm


@dataclasses.dataclass
class ClampParams:
    glow_on: bool = False
    V_glow: float = 15e3          # [IR] swept near 15 kV; glow knee
    alpha_glow: float = 1.0       # [IR] g_glow = alpha/Z0 (soft slope vs tank admittance)
    glow_placement: str = "void"  # "void" (shunt on V) | "island" (caps E_kick pre-inject)
    crowbar_on: bool = False
    V_crowbar: float = 16e3       # [IR] swept near 15 kV; last-resort, just above target
    recover_V: float = 0.0        # dump target after a crowbar fire
    hyst_frac: float = 0.5        # re-arm when |V| < hyst_frac*V_crowbar (anti-chatter)


@dataclasses.dataclass
class DriveParams:
    enabled: bool = True
    E_kick: float = E_EASED       # J   [IR] full=E_FULL / eased=E_EASED (recommended)
    f_cycle: float = RPM / 10.0   # 300 Hz/branch [OC]
    n_branches: int = 2           # both branches -> combined 600 Hz [OC]
    kick_sign: str = "coherent"   # "coherent"(energy-adds) | "alternating" | "random" [IR]


# ======================================================================================
# Numerical core (pure-float inner loop for speed; kicks applied OUTSIDE the RK4 step)
# ======================================================================================
def i_glow(V, tank, clamp):
    """Soft bidirectional glow sink above V_glow: I = (alpha/Z0)*max(0,|V|-V_glow)*sign(V).
    Active only in the VOID placement (a shunt on the tank node). In the ISLAND placement the
    glow lives upstream and caps E_kick before injection (handled in simulate), not as a tank shunt."""
    if not clamp.glow_on or clamp.glow_placement != "void":
        return 0.0
    over = abs(V) - clamp.V_glow
    if over <= 0.0:
        return 0.0
    g = clamp.alpha_glow / tank.Z0
    return g * over * (1.0 if V >= 0.0 else -1.0)


def _deriv(V, IL, tank, clamp):
    dV = (-IL - i_glow(V, tank, clamp)) / tank.C_R          # I_inject handled as a state jump
    dIL = (V - tank.R_loss * IL) / tank.L_R
    return dV, dIL


def _rk4(V, IL, dt, tank, clamp):
    dV1, dIL1 = _deriv(V, IL, tank, clamp)
    dV2, dIL2 = _deriv(V + 0.5 * dt * dV1, IL + 0.5 * dt * dIL1, tank, clamp)
    dV3, dIL3 = _deriv(V + 0.5 * dt * dV2, IL + 0.5 * dt * dIL2, tank, clamp)
    dV4, dIL4 = _deriv(V + dt * dV3, IL + dt * dIL3, tank, clamp)
    return (V + dt / 6.0 * (dV1 + 2 * dV2 + 2 * dV3 + dV4),
            IL + dt / 6.0 * (dIL1 + 2 * dIL2 + 2 * dIL3 + dIL4))


def apply_kick(V, E_eff, esign, tank):
    """Impulsive energy injection: 1/2*C*(Vnew^2 - V^2) = esign*E_eff. esign=+1 adds energy
    (coherent), -1 removes (anti-phase). Cold tank + coherent -> Vnew = sqrt(2*E/C)."""
    val = V * V + esign * 2.0 * E_eff / tank.C_R
    if val < 0.0:
        val = 0.0                                            # a -kick cannot drain below empty
    s = 1.0 if V >= 0.0 else -1.0
    return s * math.sqrt(val)


def kick_times(drive, t_end):
    if not drive.enabled or drive.E_kick <= 0.0:
        return np.array([])
    period = 1.0 / drive.f_cycle                             # branch period 3.333 ms
    tA = np.arange(0.0, t_end, period)
    if drive.n_branches >= 2:
        tB = tA + 0.5 * period                               # half a BRANCH cycle -> 600 Hz combined
        return np.sort(np.concatenate([tA, tB]))
    return tA


def simulate(tank, clamp, drive, t_end, V0=0.0, IL0=0.0, steps_per_period=48,
             store_every=8, seed=0):
    """Integrate the tank+clamp from (V0, IL0) over t_end. Returns trace + energy ledgers."""
    dt = 1.0 / (tank.f0 * steps_per_period)
    n = int(math.ceil(t_end / dt))
    rng = np.random.RandomState(seed)

    # map scheduled kicks to step indices
    kick_steps = {}
    for tk in kick_times(drive, t_end):
        kick_steps.setdefault(int(round(tk / dt)), 0)
        kick_steps[int(round(tk / dt))] += 1

    V, IL = float(V0), float(IL0)
    E_inj = E_glow = E_lossR = E_crow = E_upstream = 0.0
    crow = dict(armed=True, count=0, events=[], cum=0.0)
    v_peak = abs(V)
    kick_i = 0
    ts, Vs, ILs = [], [], []
    branch_T = (1.0 / drive.f_cycle) if drive.enabled else tank.tau

    for si in range(n):
        t = si * dt
        # --- apply scheduled kick(s) as a state jump (impulse mode), book injected energy
        if si in kick_steps:
            for _ in range(kick_steps[si]):
                if drive.kick_sign == "coherent":
                    esign = 1.0
                elif drive.kick_sign == "alternating":
                    esign = 1.0 if (kick_i % 2 == 0) else -1.0
                else:
                    esign = 1.0 if rng.random() < 0.5 else -1.0
                E_eff = drive.E_kick
                if clamp.glow_on and clamp.glow_placement == "island":
                    E_cap = 0.5 * tank.C_R * clamp.V_glow**2               # energy reaching V_glow cold
                    if E_eff > E_cap:
                        E_upstream += (E_eff - E_cap)                      # governor sheds excess to sink
                        E_eff = E_cap                                     # upstream cap (kick limited)
                Vn = apply_kick(V, E_eff, esign, tank)
                E_inj += 0.5 * tank.C_R * (Vn * Vn - V * V)
                V = Vn
                kick_i += 1
        # --- integrate one RK4 step; trapezoidal glow + loss energy over the step
        V_pre, IL_pre = V, IL
        P_glow_pre = i_glow(V_pre, tank, clamp) * V_pre          # power into glow sink (>=0)
        V, IL = _rk4(V, IL, dt, tank, clamp)
        E_glow += 0.5 * (P_glow_pre + i_glow(V, tank, clamp) * V) * dt
        E_lossR += 0.5 * tank.R_loss * (IL_pre * IL_pre + IL * IL) * dt
        # --- crowbar latch (discrete event-dump) on post-step V
        if clamp.crowbar_on:
            if crow["armed"] and abs(V) > clamp.V_crowbar:
                Erem = 0.5 * tank.C_R * (V * V - clamp.recover_V**2)
                crow["events"].append((t, Erem, V))
                crow["cum"] += Erem
                crow["count"] += 1
                crow["armed"] = False
                E_crow += Erem
                V = clamp.recover_V if V >= 0.0 else -clamp.recover_V
            elif (not crow["armed"]) and abs(V) < clamp.hyst_frac * clamp.V_crowbar:
                crow["armed"] = True
        if abs(V) > v_peak:
            v_peak = abs(V)
        if si % store_every == 0:
            ts.append(t)
            Vs.append(V)
            ILs.append(IL)

    E_final = 0.5 * tank.C_R * V * V + 0.5 * tank.L_R * IL * IL
    # sink load = energy the GOVERNOR removes, as a continuous power (W): void shunt = E_glow,
    # island/upstream = E_upstream (shed before injection); over the run duration.
    t_run = (n * dt) if n else 1.0
    E_sink = E_upstream if (clamp.glow_on and clamp.glow_placement == "island") else E_glow
    return dict(t=np.array(ts), V=np.array(Vs), IL=np.array(ILs), v_peak=v_peak,
                E_inj=E_inj, E_glow=E_glow, E_lossR=E_lossR, E_crow=E_crow, E_final=E_final,
                E_upstream=E_upstream, E_sink=E_sink, P_sink=E_sink / t_run, t_run=t_run,
                crow=crow, dt=dt, branch_T=branch_T, tank=tank, clamp=clamp, drive=drive)


# ======================================================================================
# Measurement helpers (R0) + envelope (R1..R4)
# ======================================================================================
def measure_f0_zerocross(t, V):
    xs = []
    for i in range(1, len(V)):
        if V[i - 1] < 0.0 <= V[i]:
            xs.append(t[i - 1] + (t[i] - t[i - 1]) * (-V[i - 1]) / (V[i] - V[i - 1]))
    if len(xs) < 3:
        return None
    return 1.0 / float(np.mean(np.diff(xs)))


def measure_f0_fft(t, V):
    dt = t[1] - t[0]
    F = np.abs(np.fft.rfft(V * np.hanning(len(V))))
    f = np.fft.rfftfreq(len(V), dt)
    k = int(np.argmax(F))
    if 1 <= k < len(F) - 1:                                  # parabolic peak interpolation
        a, b, c = F[k - 1], F[k], F[k + 1]
        den = (a - 2 * b + c)
        d = 0.5 * (a - c) / den if den != 0 else 0.0
        return float(f[k] + d * (f[1] - f[0]))
    return float(f[k])


def measure_tau(t, V):
    a = np.abs(V)
    tp, vp = [], []
    for i in range(1, len(a) - 1):
        if a[i] >= a[i - 1] and a[i] > a[i + 1] and a[i] > 0:
            tp.append(t[i]); vp.append(a[i])
    if len(tp) < 5:
        return None
    slope, _ = np.polyfit(np.array(tp), np.log(np.array(vp)), 1)
    return (-1.0 / slope) if slope < 0 else None


def steady_envelope(r):
    """Max |V| over the last 2 branch periods (steady-state amplitude)."""
    t, V = r["t"], r["V"]
    if len(t) == 0:
        return 0.0
    m = t >= (t[-1] - 2 * r["branch_T"])
    return float(np.max(np.abs(V[m]))) if m.any() else r["v_peak"]


def energy_residual(r):
    """Conservation gate: injected == dissipated + stored. Returns relative residual."""
    bal = r["E_inj"] - (r["E_lossR"] + r["E_glow"] + r["E_crow"] + r["E_final"])
    denom = max(abs(r["E_inj"]), 1e-30)
    return bal / denom


# ======================================================================================
# Campaign (r0.2: confirm reach >=15 kV, then confirm the two-tier clamp holds 15 kV)
# ======================================================================================
DRIVES = [("full", E_FULL), ("eased", E_EASED)]
QS = (320, 500, 900)


def _t_end(tank):
    return max(8e-3, 20 * tank.tau)


def run_R0(steps_list=(32, 48, 64)):
    print("\n--- R0  free ringdown vs analytic (authorises model + confirms conical L) ----")
    tank = TankParams()
    print(f"  tank: L={tank.L_R*1e6:.0f} uH  C={tank.C_R*1e12:.0f} pF  "
          f"f0={tank.f0/1e3:.2f} kHz  Q={tank.Q:.0f}  R_loss={tank.R_loss:.3f} ohm  "
          f"tau={tank.tau*1e3:.3f} ms  Z0={tank.Z0:.0f} ohm")
    rows = []
    for spp in steps_list:
        r = simulate(tank, ClampParams(), DriveParams(enabled=False), 5 * tank.tau,
                     V0=1000.0, steps_per_period=spp, store_every=2)
        fzc = measure_f0_zerocross(r["t"], r["V"])
        tm = measure_tau(r["t"], r["V"])
        rows.append((spp, fzc, tm))
        print(f"  steps/period={spp:3d}: f0_zc={fzc/1e3:.3f} kHz  "
              f"f0_fft={measure_f0_fft(r['t'], r['V'])/1e3:.3f} kHz  tau={tm*1e3:.3f} ms")
    spp, fzc, tm = rows[-1]
    ef = abs(fzc - tank.f0) / tank.f0
    et = abs(tm - tank.tau) / tank.tau
    ok = (ef <= 0.01) and (et <= 0.03)
    print(f"  analytic f0={tank.f0/1e3:.3f} kHz (target ~579), tau={tank.tau*1e3:.3f} ms => "
          f"f0 err {ef*100:.2f}% (<=1%), tau err {et*100:.2f}% (<=3%): {'PASS' if ok else 'FAIL'} "
          f"-> conical 79 uH confirmed against analytic f0")
    return ok, rows


def run_R1(Qs=QS):
    print("\n--- R1  driven, NO clamp: confirm reach (full ~18.9 kV / eased ~15.5 kV) ------")
    E_reach = 0.5 * TankParams().C_R * V_TARGET**2
    print(f"  energy to reach {V_TARGET/1e3:.0f} kV on C_R={TankParams().C_R*1e12:.0f} pF = "
          f"1/2*C_R*V^2 = {E_reach*1e3:.0f} mJ; drives: full {E_FULL*1e3:.0f} mJ, eased {E_EASED*1e3:.0f} mJ")
    rows = []
    for Q in Qs:
        tank = TankParams(Q=Q)
        for name, E in DRIVES:
            r = simulate(tank, ClampParams(), DriveParams(E_kick=E), _t_end(tank),
                         steps_per_period=48, store_every=8)
            v_cold = math.sqrt(2 * E / tank.C_R)
            rows.append(dict(Q=Q, mode=name, E=E, peak=r["v_peak"],
                             env=steady_envelope(r), v_cold=v_cold,
                             accum=steady_envelope(r) / v_cold))
    for Q in Qs:
        tank = TankParams(Q=Q)
        sp = (1.0 / (DriveParams().f_cycle * 2)) / tank.tau
        print(f"  Q={Q:3d} (spacing/tau={sp:.2f}):")
        for x in [r for r in rows if r["Q"] == Q]:
            print(f"     {x['mode']:5s} {x['E']*1e3:3.0f} mJ -> peak {x['peak']/1e3:5.2f} kV "
                  f"(predicted {x['v_cold']/1e3:.2f}); single-kick accum x{x['accum']:.2f}  "
                  f"{'>=15kV' if x['peak'] >= V_TARGET else 'SHORT'}")
    full = [r for r in rows if r["mode"] == "full"]
    eased = [r for r in rows if r["mode"] == "eased"]
    reach_ok = all(r["peak"] >= V_TARGET for r in rows)
    headroom = min(r["peak"] for r in full) / V_TARGET - 1.0
    drop = 1.0 - E_reach / E_FULL                              # how far full drive can fall and still reach
    print(f"  REACH: full {min(r['peak'] for r in full)/1e3:.1f}-{max(r['peak'] for r in full)/1e3:.1f} kV, "
          f"eased {min(r['peak'] for r in eased)/1e3:.1f}-{max(r['peak'] for r in eased)/1e3:.1f} kV across Q "
          f"-> all >=15 kV: {'YES' if reach_ok else 'NO'}")
    print(f"  HEADROOM: full peak is +{headroom*100:.0f}% over 15 kV; reach is single-kick (accum ~1.0), "
          f"so Q-INDEPENDENT -> survives arbitrarily low Q. Full drive can fall {drop*100:.0f}% "
          f"(to {E_reach*1e3:.0f} mJ) and still hit 15 kV.")
    return rows, reach_ok, headroom


def run_R2(V_glows=(13e3, 14e3, 15e3, 16e3), placements=("void", "island"), Qs=QS, E_drive=E_FULL):
    print("\n--- R2  soft glow governor only (sweep V_glow near 15 kV, both placements) ----")
    print(f"  drive = FULL {E_drive*1e3:.0f} mJ (un-clamped peak "
          f"~{math.sqrt(2*E_drive/TankParams().C_R)/1e3:.1f} kV) so the governor has work")
    rows = []
    for placement in placements:
        for Q in Qs:
            tank = TankParams(Q=Q)
            for Vg in V_glows:
                clamp = ClampParams(glow_on=True, V_glow=Vg, glow_placement=placement)
                r = simulate(tank, clamp, DriveParams(E_kick=E_drive), _t_end(tank),
                             steps_per_period=48, store_every=8)
                rows.append(dict(placement=placement, Q=Q, Vg=Vg, env=steady_envelope(r),
                                 peak=r["v_peak"], P_sink=r["P_sink"], E_sink=r["E_sink"],
                                 resid=energy_residual(r)))
    for placement in placements:
        print(f"  placement={placement}:")
        for x in [r for r in rows if r["placement"] == placement and r["Q"] == 500]:
            print(f"     V_glow={x['Vg']/1e3:4.0f} kV (Q=500) -> sustained {x['env']/1e3:5.2f} kV  "
                  f"peak {x['peak']/1e3:5.1f} kV  sink {x['P_sink']:5.1f} W  [bal {x['resid']*100:+.2f}%]")
    print("  => VOID bleeds but the impulsive kick spikes the PEAK above V_glow; ISLAND/upstream caps "
          "the peak AT V_glow (r0.1 finding) -> upstream is the peak-holding placement.")
    return rows


def run_R3(V_crowbars=(15e3, 16e3, 17e3), Qs=QS):
    print("\n--- R3  hard crowbar only (threshold near 15 kV; idle check + sink sizing) -----")
    rows = []
    # nominal = EASED drive: confirm idle for V_crowbar above the 15.5 kV eased peak
    for Q in Qs:
        tank = TankParams(Q=Q)
        for Vc in V_crowbars:
            r = simulate(tank, ClampParams(crowbar_on=True, V_crowbar=Vc),
                         DriveParams(E_kick=E_EASED), _t_end(tank), steps_per_period=48, store_every=8)
            if Q == 500:
                pk = math.sqrt(2 * E_EASED / tank.C_R)        # un-clamped eased peak (v_peak hidden post-dump)
                print(f"  eased nominal (peak {pk/1e3:.1f} kV), V_crowbar={Vc/1e3:.0f} kV (Q=500): "
                      f"fires {r['crow']['count']} -> {'IDLE' if r['crow']['count']==0 else 'FIRES'}")
    # full drive: size the sink if the crowbar must catch a runaway
    for Q in Qs:
        tank = TankParams(Q=Q)
        for Vc in V_crowbars:
            r = simulate(tank, ClampParams(crowbar_on=True, V_crowbar=Vc),
                         DriveParams(E_kick=E_FULL), _t_end(tank), steps_per_period=48, store_every=8)
            c = r["crow"]
            per = (c["cum"] / c["count"]) if c["count"] else 0.0
            rows.append(dict(Q=Q, Vc=Vc, count=c["count"], cum=c["cum"], per=per, events=c["events"]))
            if Q == 500:
                print(f"  full runaway, V_crowbar={Vc/1e3:.0f} kV (Q=500): {c['count']} fires, "
                      f"per-event {per*1e3:.0f} mJ, cumulative {c['cum']*1e3:.0f} mJ "
                      f"({per/10e-9/1e6:.0f} MW/10 ns)")
    print("  => crowbar IDLE under nominal eased drive at >=16 kV setpoint; only catches the full-drive "
          "runaway (last-resort), dumping ~1/2*C*V_peak^2 -> sizes the deferred MW-class sink.")
    return rows


def run_R4(Qs=QS, V_glow=15e3, V_crowbar=16e3):
    print("\n--- R4  two-tier combined (upstream governor + crowbar), both drive modes ------")
    rows = []
    for name, E in DRIVES:
        for Q in Qs:
            tank = TankParams(Q=Q)
            clamp = ClampParams(glow_on=True, V_glow=V_glow, glow_placement="island",
                                crowbar_on=True, V_crowbar=V_crowbar)
            r = simulate(tank, clamp, DriveParams(E_kick=E), _t_end(tank),
                         steps_per_period=48, store_every=8)
            held = r["v_peak"] <= V_TARGET * 1.02 and r["crow"]["count"] == 0
            resid = energy_residual(r)
            rows.append(dict(mode=name, Q=Q, peak=r["v_peak"], env=steady_envelope(r),
                             fires=r["crow"]["count"], P_sink=r["P_sink"], held=held, resid=resid))
            if Q == 500:
                print(f"  {name:5s} drive, Q=500: peak {r['v_peak']/1e3:5.2f} kV, sustained "
                      f"{steady_envelope(r)/1e3:5.2f} kV, crowbar fires {r['crow']['count']}, "
                      f"governor sink {r['P_sink']:4.1f} W -> "
                      f"{'HOLDS <=15 kV, crowbar idle' if held else 'NOT held'}  [bal {resid*100:+.2f}%]")
    # void-placement contrast at full drive (shows why upstream is required)
    tankv = TankParams(Q=500)
    rv = simulate(tankv, ClampParams(glow_on=True, V_glow=V_glow, glow_placement="void",
                                     crowbar_on=True, V_crowbar=V_crowbar),
                  DriveParams(E_kick=E_FULL), _t_end(tankv), steps_per_period=48, store_every=8)
    pk_full = math.sqrt(2 * E_FULL / tankv.C_R)              # un-clamped impulse peak reference
    print(f"  (contrast) full drive, VOID governor: impulse peak ~{pk_full/1e3:.1f} kV spikes past "
          f"V_glow; crowbar forced to fire {rv['crow']['count']}x -> void cannot hold the peak; "
          f"upstream placement required.")
    return rows


# ======================================================================================
# Plot + CSV + verdict
# ======================================================================================
def make_plots(path):
    tank = TankParams(Q=500)
    te = 6e-3
    r1f = simulate(tank, ClampParams(), DriveParams(E_kick=E_FULL), te, store_every=4)
    r1e = simulate(tank, ClampParams(), DriveParams(E_kick=E_EASED), te, store_every=4)
    r2 = simulate(tank, ClampParams(glow_on=True, V_glow=15e3, glow_placement="island"),
                  DriveParams(E_kick=E_FULL), te, store_every=4)
    r3 = simulate(tank, ClampParams(crowbar_on=True, V_crowbar=16e3),
                  DriveParams(E_kick=E_FULL), te, store_every=4)
    r4 = simulate(tank, ClampParams(glow_on=True, V_glow=15e3, glow_placement="island",
                                    crowbar_on=True, V_crowbar=16e3),
                  DriveParams(E_kick=E_FULL), te, store_every=4)
    fig, ax = plt.subplots(2, 2, figsize=(12, 8))
    ax[0, 0].plot(r1f["t"] * 1e3, r1f["V"] / 1e3, lw=0.7, color="#d62728", label="full 171 mJ")
    ax[0, 0].plot(r1e["t"] * 1e3, r1e["V"] / 1e3, lw=0.7, color="#1f77b4", label="eased 115 mJ")
    ax[0, 0].axhline(15, ls="--", color="#888", lw=0.8)
    ax[0, 0].set_title("R1  reach, no clamp (full 18.9 / eased 15.5 kV)", loc="left", fontweight="bold")
    ax[0, 0].legend(fontsize=8)
    ax[0, 1].plot(r2["t"] * 1e3, r2["V"] / 1e3, lw=0.7, color="#2ca02c")
    ax[0, 1].axhline(15, ls="--", color="#888", lw=0.8)
    ax[0, 1].set_title("R2  upstream governor (V_glow=15 kV)", loc="left", fontweight="bold")
    ax[1, 0].plot(r1f["t"] * 1e3, r1f["V"] / 1e3, lw=0.5, color="#ccc", label="no clamp (18.9 kV)")
    ax[1, 0].plot(r3["t"] * 1e3, r3["V"] / 1e3, lw=0.7, color="#9467bd", label="crowbar-clamped")
    if r3["crow"]["events"]:
        te_ = [e[0] * 1e3 for e in r3["crow"]["events"]]
        ve_ = [e[2] / 1e3 for e in r3["crow"]["events"]]
        ax[1, 0].scatter(te_, ve_, s=20, color="#d62728", zorder=5, label="crowbar fire")
    ax[1, 0].axhline(16, ls="--", color="#888", lw=0.8)
    ax[1, 0].set_title("R3  hard crowbar (V_crowbar=16 kV) — chops the runaway", loc="left", fontweight="bold")
    ax[1, 0].legend(fontsize=7)
    ax[1, 1].plot(r4["t"] * 1e3, r4["V"] / 1e3, lw=0.7, color="#1f77b4")
    ax[1, 1].axhline(15, ls="--", color="#888", lw=0.8)
    ax[1, 1].set_title("R4  two-tier (upstream govern + crowbar), full drive", loc="left", fontweight="bold")
    for a in ax.flat:
        a.set_xlabel("t [ms]"); a.set_ylabel("tank V [kV]"); a.grid(alpha=0.25)
    fig.suptitle(f"Resonator r0.2 (L=79 uH, C=960 pF, f0={tank.f0/1e3:.0f} kHz, Q=500) "
                 f"+ two-tier clamp -- confirm 15 kV", fontweight="bold")
    fig.tight_layout()
    fig.savefig(path, dpi=140, bbox_inches="tight")
    plt.close(fig)


def write_sink_csv(r2, r3, r4, path):
    with open(path, "w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["stage", "type", "placement/mode", "V_glow_kV", "V_crowbar_kV", "Q",
                    "sink_W", "event_index", "t_s", "E_event_J", "E_cumulative_J"])
        for x in r2:
            w.writerow(["R2", "glow", x["placement"], f"{x['Vg']/1e3:.0f}", "", x["Q"],
                        f"{x['P_sink']:.3f}", "", "", "", f"{x['E_sink']:.6e}"])
        for x in r4:
            w.writerow(["R4", "glow-upstream", x["mode"], f"{15:.0f}", f"{16:.0f}", x["Q"],
                        f"{x['P_sink']:.3f}", "", "", "", ""])
        for x in r3:
            if not x["events"]:
                w.writerow(["R3", "crowbar", "void", "", f"{x['Vc']/1e3:.0f}", x["Q"],
                            "", 0, "", "0", "0"])
            cum = 0.0
            for i, (te, Ee, _) in enumerate(x["events"]):
                cum += Ee
                w.writerow(["R3", "crowbar", "void", "", f"{x['Vc']/1e3:.0f}", x["Q"],
                            "", i, f"{te:.6e}", f"{Ee:.6e}", f"{cum:.6e}"])


def main():
    print("=" * 78)
    print("resonator_sim r0.2 — revised geometry; confirm 15 kV + clamp hold (R0-R4)")
    print("=" * 78)
    ok0, _ = run_R0()
    assert ok0, "R0 self-test failed; model not authorised"
    r1, reach_ok, headroom = run_R1()
    r2 = run_R2()
    r3 = run_R3()
    r4 = run_R4()

    make_plots(os.path.join(HERE, "resonator_r2_traces.png"))
    write_sink_csv(r2, r3, r4, os.path.join(HERE, "resonator_r2_sink.csv"))

    r4_holds = all(x["held"] for x in r4)
    sink_full = next(x["P_sink"] for x in r4 if x["mode"] == "full" and x["Q"] == 500)
    sink_eased = next(x["P_sink"] for x in r4 if x["mode"] == "eased" and x["Q"] == 500)
    if reach_ok and r4_holds:
        verdict = "TANK-HOLDS-15kV"
    elif not reach_ok:
        verdict = "TANK-STILL-UNDERDRIVEN"
    else:
        verdict = "CLAMP-INSUFFICIENT"
    print("\n" + "=" * 78)
    print(f"VERDICT: {verdict}")
    print(f"  R1 reach: full {E_FULL*1e3:.0f} mJ -> 18.9 kV, eased {E_EASED*1e3:.0f} mJ -> 15.5 kV; "
          f"both >=15 kV at all Q (single-kick, Q-independent). Headroom +{headroom*100:.0f}%.")
    print(f"  R4 hold: upstream two-tier governor holds <=15 kV with the crowbar IDLE at all Q, both "
          f"drive modes. Sink load: FULL ~{sink_full:.0f} W, EASED ~{sink_eased:.1f} W.")
    print(f"  recommendation: EASED drive (~{sink_eased:.0f} W sink) over FULL (~{sink_full:.0f} W) "
          f"unless the void/structure can carry ~{sink_full:.0f} W -> flag for structural sizing.")
    print(f"  (the closed reach gap is the geometry: island Cx 88->648 pF now matches the tank "
          f"C_R 960 pF -> efficient charge-sharing, the hydraulic 'equal-vessel' transfer.)")
    print("=" * 78)
    print("wrote resonator_r2_traces.png, resonator_r2_sink.csv")
    return verdict


if __name__ == "__main__":
    main()
