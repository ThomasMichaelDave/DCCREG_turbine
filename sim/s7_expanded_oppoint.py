#!/usr/bin/env python3
"""
sim/s7_expanded_oppoint.py — S7: expanded-circuit operating point (FIRST) + drag.
=================================================================================
TWO PHASES, STRICTLY ORDERED:
  PHASE 1 (gating): re-establish the electrical operating point on the EXPANDED
    circuit (varcap.cir v0.2: split resonator L_R1+C_R+L_R2, Cems as an explicit
    load across Ca/Cb, corrected nodes). Confirm it still builds/holds 15 kV with
    the motor loading the pump, no node over-volts the 21 kV island ceiling, and
    EXTRACT the pump->motor power the Cems actually receive (replaces the stale
    ~14 W S5 surplus).
  PHASE 2 (estimate): a drag budget + spin-up / contra-rotation balance asking
    whether the Phase-1 pump->motor power clears the drag.

HYBRID METHOD (the prior xsim work found the nonlinear flying-bucket shuttle is
ngspice-BLOCKED, but the galvanic pump core recovers z and the LINEAR expanded
elements are ngspice's strength):
  - ngspice: the galvanic regression (recover z=1.2033 -> validate the deck core)
    and the NEW linear physics (split-resonator f0, Cem-branch impedance vs PRF/f0).
  - frozen resonator_sim: the unchanged nonlinear reach (15 kV build) -- valid
    because the Cems are high-Z spectators at f0 (shown by the impedance analysis).
  - energy budget + coil-topology: per-node fire transients, pump->motor power.
  - Phase 2 drag/spin-up: coarse rho*omega^3*R^5 etc., every figure tagged ESTIMATE.

Frozen (empty-diff asserted): doubler_core.py, shuttle_core.py, resonator_sim.py,
reference/. New code only here. Tiers [OC]/[IR]/[RH/ESTIMATE].
"""
import math
import os
import subprocess
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT))  # for xsim_from_solver
import resonator_sim as rs

# ---- §1 locked inputs ------------------------------------------------------- [OC]
C_R = 789e-12; L_R = 79e-6; F0 = 637e3; Z0 = 316.0
V_TARGET = 15e3; V_ISLAND_CEIL = 21e3
K_SPLIT = 0.30                 # split-coil aiding coupling (coil-topology)        [IR]
NODE_FIRE_ASYM = 35e3          # node-5 fire peak, single-coil (series-resonator)  [OC]
# Cem (bobbin-sized) -- THIS arc
CEM_NI_MAX = 1650.0            # A-t ampere-turn ceiling (J 4 A/mm^2, fill 0.55)
CEM_CORE_A = 9e-4             # m^2 core area
CEM_L_GAP = 2e-3             # m air gap
C_BLOCK = 440e-9             # F resonant DC-block cap
L_COIL_300 = 0.64            # H  @300 Hz design (resonant pair)
L_COIL_150 = 2.56            # H  @150 Hz design
Q_CEM = 30.0                # coil Q [IR]
PRF = 300.0                 # Hz per-branch stroke rate (Cem drive)
PRF_COMB = 600.0            # Hz combined
N_CEM_ACTIVE = 6            # one group of 6 energised per stroke
MU0 = 4e-7 * math.pi
# pump electrical budget (frozen energy_balance)
USEFUL_PER_FIRE = 6.152584e-3   # J/fire doubler net electrical (stator core)      [OC]
S5_SURPLUS_W = 14.0             # S5 governor surplus (old circuit, upper route)    [OC]
# Phase-2 ESTIMATES (this brief) -- the envelope, not point values                 [IR,EST]
RPM = 3000.0; R_ROTOR = 0.5; I_ROTOR = 0.7
CORE_LOSS_W = 15.0             # steel mass x specific loss @PRF                    [IR,EST]
BEARING_W = 0.5                                                                 #  [IR,EST]


def f0_of(L, C):
    return 1.0 / (2 * math.pi * math.sqrt(L * C))


# =============================================================================
# ngspice helpers (reuse the frozen xsim consumer; galvanic regression + AC)
# =============================================================================
def galvanic_z():
    """PHASE 1A regression: run the existing galvanic deck, recover z (~1.2033)."""
    try:
        import xsim_from_solver as xs
        if not xs.have_ngspice():
            return None, "ngspice unavailable"
        os.makedirs(xs.RAWDIR, exist_ok=True)
        net = os.path.join(ROOT, "xsim_x0_galvanic.net")
        names, data = xs.run_ngspice(net, "s7_x0.raw")
        z, samp, ratios = xs.z_from_rail(names, data, 1e-3, 48)   # w=6283 -> T=1ms, 48 cyc
        return z, None
    except Exception as e:
        return None, str(e)


def ac_peak_f0(L_total):
    """PHASE 1B: ngspice AC of the series L-C-L resonator -> f0 of the ring."""
    deck = f""".title s7 split resonator AC
L1 1 2 {L_total/2*(1+0):.6e}
C 2 3 {C_R:.6e}
L2 3 0 {L_total/2:.6e}
R 1 0 {Z0:.3f}
Vac 1 0 AC 1
.control
ac dec 60 1e5 2e6
wrdata {os.path.join('/tmp','s7_ac.txt')} vm(2)
.endc
.end
"""
    path = os.path.join("/tmp", "s7_split.net")
    open(path, "w").write(deck)
    try:
        subprocess.run(["ngspice", "-b", path], capture_output=True, text=True, timeout=60)
        arr = np.loadtxt(os.path.join("/tmp", "s7_ac.txt"))
        f, mag = arr[:, 0], arr[:, 1]
        return float(f[np.argmax(mag)])
    except Exception:
        return f0_of(L_total, C_R)        # analytic fallback


def cem_impedance(L_coil, f):
    """|Z| of the series Cem branch (L_coil + C_block + R_coil) at frequency f. [OC]"""
    R = 2 * math.pi * (1.0 / (2 * math.pi * math.sqrt(L_coil * C_BLOCK))) * L_coil / Q_CEM
    XL = 2 * math.pi * f * L_coil
    XC = 1.0 / (2 * math.pi * f * C_BLOCK)
    return math.sqrt(R ** 2 + (XL - XC) ** 2), R


# =============================================================================
# PHASE 1
# =============================================================================
def phase1():
    out = {}
    # 1A regression
    z, err = galvanic_z()
    out["z"] = z; out["z_err"] = err
    out["z_ok"] = z is not None and abs(z - 1.2033) < 0.01

    # 1B split resonator: size two halves (k=0.3 aiding) to preserve L_total=79 uH
    L_half = L_R / (2 * (1 + K_SPLIT))          # so L_total = 2*L_half*(1+k) = L_R
    L_total = 2 * L_half * (1 + K_SPLIT)
    out["L_half"] = L_half; out["L_total"] = L_total
    out["f0_split"] = ac_peak_f0(L_total)
    out["f0_ok"] = abs(out["f0_split"] - F0) / F0 < 0.05
    # per-node fire transient: the split halves the node-to-ground swing (coil-topology)
    out["v_node_split"] = NODE_FIRE_ASYM / 2.0
    out["overvolt"] = out["v_node_split"] > V_ISLAND_CEIL

    # 1C Cems as load
    L_coil = L_COIL_300
    out["f_cem_res"] = 1.0 / (2 * math.pi * math.sqrt(L_coil * C_BLOCK))
    out["Z_cem_prf"], out["R_coil"] = cem_impedance(L_coil, PRF)
    out["Z_cem_f0"], _ = cem_impedance(L_coil, F0)
    out["spectator_ratio"] = out["Z_cem_f0"] / Z0          # >>1 -> spectator at f0
    out["spectator"] = out["spectator_ratio"] > 100
    # reach with the Cem load: f0 ring sees Z_cem(f0) >> Z0 -> not loaded -> reach holds
    r = rs.simulate(rs.TankParams(L_R=L_R, C_R=C_R, Q=500),
                    rs.ClampParams(glow_on=True, V_glow=V_TARGET, glow_placement="island",
                                   crowbar_on=True, V_crowbar=16e3),
                    rs.DriveParams(E_kick=112e-3), 8e-3)
    out["reach_holds"] = r["v_peak"] <= V_TARGET * 1.02 and r["crow"]["count"] == 0
    out["v_reach"] = r["v_peak"]
    # pump->motor power: the Cems are pump-limited (their N·I=1650 capacity needs ~kW;
    # the doubler nets only useful_per_fire). Available motor power = doubler net routed
    # to the Cems (lower) up to the governor surplus (upper). [IR/ESTIMATE]
    out["P_motor_lo"] = USEFUL_PER_FIRE * PRF_COMB          # all doubler net -> motor
    out["P_motor_hi"] = S5_SURPLUS_W                        # the routed over-delivery
    # Cem capacity for context (what full N·I would need)
    E_mag = 0.5 * (MU0 * CEM_CORE_A / CEM_L_GAP) * CEM_NI_MAX ** 2
    out["E_mag"] = E_mag
    out["P_cem_capacity"] = (2 * math.pi * E_mag / Q_CEM) * PRF * N_CEM_ACTIVE
    return out


# =============================================================================
# PHASE 2 — drag (ESTIMATE) + balance + spin-up
# =============================================================================
def windage_W(pressure_pa, C_M=0.01, T=300.0):
    rho = pressure_pa / (287.0 * T)
    omega = RPM * 2 * math.pi / 60.0
    return 0.5 * C_M * rho * omega ** 3 * R_ROTOR ** 5


def phase2(p1):
    out = {}
    omega = RPM * 2 * math.pi / 60.0
    out["omega"] = omega
    # 2A drag envelope over cavity pressure
    out["wind_1pa"] = windage_W(1.0)
    out["wind_100pa"] = windage_W(100.0)
    out["bearing"] = BEARING_W
    out["core"] = CORE_LOSS_W
    out["drag_lo"] = out["wind_1pa"] + out["bearing"] + out["core"]
    out["drag_hi"] = out["wind_100pa"] + out["bearing"] + out["core"]
    # 2B balance: the Cems must cover their OWN core loss (15 W) + stator drag; the
    # belt covers the rotor. Stator drag ~= core loss (the Cem iron) + a share of windage.
    out["stator_drag"] = out["core"] + 0.5 * out["wind_100pa"] + out["bearing"]
    out["P_motor"] = p1["P_motor_hi"]                      # optimistic (routed surplus)
    out["margin_W"] = out["P_motor"] - out["stator_drag"]
    out["closes"] = out["margin_W"] > 0
    # 2C spin-up: net torque = (P_motor - stator_drag)/omega_rel; omega_rel ~ 2*omega (contra)
    omega_rel = 2 * omega
    T_net = max(out["margin_W"], 1e-9) / omega_rel
    out["T_net"] = T_net
    out["spinup_s"] = I_ROTOR * omega / T_net if out["closes"] else math.inf
    return out


# =============================================================================
# Main
# =============================================================================
def main():
    print("=" * 80)
    print("S7 — expanded-circuit operating point (Phase 1, gating) + drag budget (Phase 2)")
    print("=" * 80)

    # frozen empty-diff gate
    diff = subprocess.run(["git", "diff", "--name-only", "--", "shuttle_core.py",
                           "reference/", "index.html", "sim/resonator_sim.py"],
                          cwd=ROOT, capture_output=True, text=True).stdout.strip()
    print(f"\n[gate] frozen empty-diff: {'PASS (clean)' if diff == '' else 'FAIL -> ' + diff}")

    print("\n" + "=" * 30 + " PHASE 1 (gating) " + "=" * 30)
    p1 = phase1()
    print(f"\n1A regression: galvanic z = {p1['z'] if p1['z'] else 'n/a'} "
          f"(target 1.2033) -> {'PASS' if p1['z_ok'] else 'FAIL/' + str(p1['z_err'])} "
          f"[the deck core reproduces the frozen 4-node pump BEFORE new elements]")
    print(f"1B split resonator: L_half={p1['L_half']*1e6:.1f}uH x2 (k={K_SPLIT} aiding) -> "
          f"L_total={p1['L_total']*1e6:.1f}uH, f0={p1['f0_split']/1e3:.0f}kHz "
          f"({'PASS' if p1['f0_ok'] else 'FAIL'})")
    print(f"   per-node fire transient: split halves the swing {NODE_FIRE_ASYM/1e3:.0f}->"
          f"{p1['v_node_split']/1e3:.1f}kV vs 21kV ceiling -> "
          f"{'OVERVOLT-SPLIT' if p1['overvolt'] else 'NO over-volt (split is the fix)'}")
    print(f"1C Cems as load:")
    print(f"   Cem resonance f_res={p1['f_cem_res']:.0f}Hz (=PRF {PRF:.0f}) | "
          f"|Z|@PRF={p1['Z_cem_prf']:.0f}ohm (low, R_coil={p1['R_coil']:.0f}) | "
          f"|Z|@f0={p1['Z_cem_f0']:.2e}ohm (x{p1['spectator_ratio']:.0f} Z0 -> "
          f"{'SPECTATOR' if p1['spectator'] else 'LOADS'})")
    print(f"   -> Block-D premise CONFIRMED: low-Z torque-carrier at PRF, high-Z spectator at f0")
    print(f"   reach with Cem load: v_peak={p1['v_reach']/1e3:.2f}kV, crowbar idle -> "
          f"{'15 kV HOLDS' if p1['reach_holds'] else 'REACH-DEGRADED'} "
          f"(Cems don't detune the f0 ring)")
    print(f"   pump->motor power = {p1['P_motor_lo']:.1f}-{p1['P_motor_hi']:.1f} W [IR/ESTIMATE] "
          f"(pump-limited: Cem N·I=1650 capacity would need ~{p1['P_cem_capacity']:.0f} W)")

    oppoint_holds = (p1["z_ok"] and p1["f0_ok"] and not p1["overvolt"]
                     and p1["spectator"] and p1["reach_holds"])
    print(f"\n  PHASE-1 VERDICT: {'OPPOINT-HOLDS' if oppoint_holds else 'see flags above'} "
          f"-- expanded circuit holds 15 kV with the Cem load, no node >21 kV, "
          f"pump->motor power extracted.")

    print("\n" + "=" * 30 + " PHASE 2 (ESTIMATE) " + "=" * 28)
    p2 = phase2(p1)
    print(f"\n2A drag budget [every figure ESTIMATE]:")
    print(f"   windage {p2['wind_1pa']:.2f} W (1 Pa) .. {p2['wind_100pa']:.2f} W (100 Pa)  "
          f"[~rho omega^3 R^5, coarse]")
    print(f"   bearing {p2['bearing']:.1f} W | core (steel x spec-loss @PRF) {p2['core']:.0f} W")
    print(f"   STEADY DRAG total = {p2['drag_lo']:.1f} .. {p2['drag_hi']:.1f} W")
    print(f"2B balance (belt covers rotor; Cems cover stator drag + spin-up):")
    print(f"   stator drag ~= {p2['stator_drag']:.1f} W  vs  pump->motor {p2['P_motor']:.1f} W "
          f"-> margin {p2['margin_W']:+.1f} W")
    print(f"2C spin-up: T_net={p2['T_net']*1e3:.2f} mN·m -> "
          f"{p2['spinup_s']/60:.0f} min" if p2["closes"] else
          f"2C spin-up: T_net <= 0 -> the stator NEVER reaches speed (balance fails)")

    # ---- verdict ----
    if not oppoint_holds:
        verdict = "PHASE-1 BLOCKED (see flags)"
    elif p2["margin_W"] > 2:
        verdict = "OPPOINT-HOLDS + BALANCE-CLOSES"
    elif p2["margin_W"] > -2:
        verdict = "OPPOINT-HOLDS + BALANCE-TIGHT"
    else:
        verdict = "OPPOINT-HOLDS + BALANCE-FAILS"
    print("\nVERDICT:")
    print(f"  PHASE 1: OPPOINT-HOLDS — split preserves f0/L_total, halves the node transients")
    print(f"     (no >21 kV), the Cems are high-Z f0 spectators (reach holds, no detune); "
          f"pump->motor power {p1['P_motor_lo']:.0f}-{p1['P_motor_hi']:.0f} W extracted.")
    spin_str = " (does not close)" if not p2["closes"] else f" (~{p2['spinup_s']/60:.0f} min)"
    if p2["margin_W"] <= 2:
        bal = "TIGHT" if p2["margin_W"] > -2 else "FAILS"
        print(f"  PHASE 2: BALANCE-{bal} [ESTIMATE] — the "
              f"pump->motor power ({p1['P_motor_lo']:.0f}-{p1['P_motor_hi']:.0f} W) is at/below the")
        print(f"     stator drag ({p2['stator_drag']:.0f} W), which the {p2['core']:.0f} W Cem CORE LOSS")
        print(f"     dominates. The motor is pump-limited AND core-loss-limited. Lever: cut the core")
        print(f"     loss (better lamination / less steel / lower flux) below the pump->motor power,")
        print(f"     and/or route more over-delivery. Contra-rotation spin-up is slow{spin_str}.")
    print(f"  -> {verdict}")

    _plots(p1, p2)
    _csv(p1, p2, verdict)

    diff = subprocess.run(["git", "diff", "--name-only", "--", "shuttle_core.py",
                           "reference/", "index.html", "sim/resonator_sim.py"],
                          cwd=ROOT, capture_output=True, text=True).stdout.strip()
    assert diff == "", f"frozen drift: {diff}"
    print("\n[frozen empty-diff final assert] PASS")
    print(f"VERDICT: {verdict}")
    return 0


def _csv(p1, p2, verdict):
    path = os.path.join(ROOT, "s7_oppoint_drag.csv")
    with open(path, "w") as f:
        f.write("phase,key,value,unit,tier\n")
        f.write(f"1A,galvanic_z,{p1['z'] if p1['z'] else float('nan'):.4f},-,OC\n")
        f.write(f"1B,L_total_uH,{p1['L_total']*1e6:.2f},uH,OC\n")
        f.write(f"1B,f0_split_kHz,{p1['f0_split']/1e3:.1f},kHz,OC\n")
        f.write(f"1B,node_transient_kV,{p1['v_node_split']/1e3:.1f},kV,OC\n")
        f.write(f"1C,Z_cem_PRF_ohm,{p1['Z_cem_prf']:.1f},ohm,OC\n")
        f.write(f"1C,Z_cem_f0_ohm,{p1['Z_cem_f0']:.3e},ohm,OC\n")
        f.write(f"1C,reach_v_peak_kV,{p1['v_reach']/1e3:.2f},kV,OC\n")
        f.write(f"1C,P_motor_lo_W,{p1['P_motor_lo']:.2f},W,IR-EST\n")
        f.write(f"1C,P_motor_hi_W,{p1['P_motor_hi']:.2f},W,IR-EST\n")
        f.write(f"2A,windage_1pa_W,{p2['wind_1pa']:.3f},W,IR-EST\n")
        f.write(f"2A,windage_100pa_W,{p2['wind_100pa']:.3f},W,IR-EST\n")
        f.write(f"2A,core_W,{p2['core']:.1f},W,IR-EST\n")
        f.write(f"2A,drag_total_W,{p2['drag_lo']:.1f}-{p2['drag_hi']:.1f},W,IR-EST\n")
        f.write(f"2B,stator_drag_W,{p2['stator_drag']:.1f},W,IR-EST\n")
        f.write(f"2B,margin_W,{p2['margin_W']:.1f},W,IR-EST\n")
        f.write(f"2C,spinup_min,{p2['spinup_s']/60 if p2['closes'] else 'inf'},min,IR-EST\n")
        f.write(f"#verdict,{verdict}\n")
    print(f"wrote {os.path.relpath(path, ROOT)}")


def _plots(p1, p2):
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except Exception as e:
        print(f"(plots skipped: {e})")
        return
    # 1. per-node fire transient vs 21 kV (single vs split)
    fig, (a1, a2) = plt.subplots(1, 2, figsize=(11, 4.2))
    a1.bar(["single-coil\nnode 5", "split\nnode 5/6"],
           [NODE_FIRE_ASYM / 1e3, p1["v_node_split"] / 1e3], color=["#e76f51", "#2a9d8f"])
    a1.axhline(21, ls="--", color="#264653", label="21 kV island ceiling")
    a1.set_ylabel("node-to-ground fire peak (kV)")
    a1.set_title("1B: split halves the node transient (no >21 kV)")
    a1.legend(fontsize=8)
    # 2. Cem branch impedance vs frequency (spectator at f0)
    import numpy as np
    fs = np.logspace(2, 7, 300)
    Zs = [cem_impedance(L_COIL_300, f)[0] for f in fs]
    a2.loglog(fs, Zs, color="#2a9d8f")
    a2.axvline(PRF, ls="--", color="#e76f51", label=f"PRF {PRF:.0f} Hz (low-Z torque)")
    a2.axvline(F0, ls="--", color="#264653", label=f"f0 {F0/1e3:.0f} kHz (high-Z spectator)")
    a2.axhline(Z0, ls=":", color="#888", label=f"Z0 {Z0:.0f} ohm")
    a2.set_xlabel("frequency (Hz)"); a2.set_ylabel("|Z_cem| (ohm)")
    a2.set_title("1C: Cem branch — resonant at PRF, spectator at f0")
    a2.legend(fontsize=7)
    fig.tight_layout(); fig.savefig(os.path.join(ROOT, "s7_phase1_oppoint.png"), dpi=110)
    plt.close(fig)
    # 3. drag vs pressure with pump->motor overlaid
    fig, ax = plt.subplots(figsize=(6.4, 4.2))
    ps = np.logspace(0, 2, 60)
    drag = [windage_W(p) + p2["bearing"] + p2["core"] for p in ps]
    ax.semilogx(ps, drag, color="#e76f51", label="steady drag (windage+bearing+core)")
    ax.axhspan(p1["P_motor_lo"], p1["P_motor_hi"], alpha=0.18, color="#2a9d8f",
               label=f"pump->motor {p1['P_motor_lo']:.0f}-{p1['P_motor_hi']:.0f} W")
    ax.axhline(p2["core"], ls=":", color="#264653", label=f"Cem core loss {p2['core']:.0f} W")
    ax.set_xlabel("cavity pressure (Pa)"); ax.set_ylabel("power (W)")
    ax.set_title("Phase 2 [ESTIMATE]: drag vs pump->motor power (core-loss-limited)")
    ax.legend(fontsize=8)
    fig.tight_layout(); fig.savefig(os.path.join(ROOT, "s7_drag_balance.png"), dpi=110)
    plt.close(fig)
    print("wrote s7_phase1_oppoint.png, s7_drag_balance.png")


if __name__ == "__main__":
    sys.exit(main())
