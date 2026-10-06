"""sim/reverse_vdg_budget.py -- first-pass budget for the reversed US 2,945,141 motor on the tube machine
(context package docs/context-reverse-vdg/). Numbers only; no field solve.

The patent runs a toothed iron rotor past C-shaped, magnetised stator cores and rectifies each coil's EMF into a series
HV stack. Reversed: the pump's HV DC link drives the same series stack of coils through one switch per coil (the
rectifier position), and the coils' back-EMF -- summed in series -- stands off the link voltage. The motor then draws
the link's surplus as V x I at tens of uA, with negligible copper loss.

Usage: python3 sim/reverse_vdg_budget.py   (writes sim/reverse_vdg_budget_results.json)
"""
import json
import math
import os

HERE = os.path.dirname(os.path.abspath(__file__))
LED = json.load(open(os.path.join(HERE, "tube_ledger_results.json")))

V_LINK = 20e3                       # DC link = the pump's 20 kV operating peak [IR]
N_COILS = 12                        # 6 C-EM cores per side, all coils of both sides in one series string [IR]
R_TOOTH = 130.0                     # mm, the toothed ring at the utron radius (r_u 130) [IR]
GAP_MECH = 1.0                      # mm running clearance tooth-to-tooth [IR; was 7 mm jaw gap]
A_SPINE = 750.0                     # mm^2, C-EM spine section (cem_inductance.CORE_A_MM2)
B_SWING = 0.4                       # T, peak-to-peak flux-density swing in the spine with PM bias [RH]
WIN_LEN, WIN_DEPTH, FILL, MLT = 48.0, 13.0, 0.45, 176.0     # bobbin window (mm), fill, mean turn (mm)
RHO_CU = 1.72e-8
ETA_MOTOR = (0.5, 0.8)              # PM flux-switching at this size, incl. switch loss [RH]


def coil(d_mm):
    do = d_mm + 0.03 if d_mm < 0.2 else d_mm + 0.04
    N = int(FILL * WIN_LEN * WIN_DEPTH / (math.pi / 4 * do ** 2))
    R = RHO_CU * N * MLT * 1e-3 / (math.pi / 4 * (d_mm * 1e-3) ** 2)
    return N, R


def main():
    om = LED["drag"]["omega_rel"]
    rpm = om * 60 / (2 * math.pi)
    P_av = [L["P_surplus_W"] for L in LED["ledger"]]                     # W at 20 kV, strays fixed / scaled
    T_need = (LED["drag"]["T_need_vacuum_or_shell_Nm"], LED["drag"]["T_need_open_air_Nm"])
    out = dict(V_link=V_LINK, n_coils=N_COILS, rpm_rel=rpm, P_available_W=P_av, T_need_Nm=T_need, rows=[], teeth=[])
    I_dc = [p / V_LINK for p in P_av]
    out["I_link_uA"] = [i * 1e6 for i in I_dc]
    out["T_available_Nm"] = {f"eta {e}": [e * p / om for p in P_av] for e in ETA_MOTOR}
    for pitch in (10.0, 13.6, 20.0):                                    # tooth pitch at r 130 (mm)
        n_t = round(2 * math.pi * R_TOOTH / pitch)
        f_e = n_t * rpm / 60
        out["teeth"].append(dict(pitch_mm=pitch, n_teeth=n_t, pitch_over_gap=pitch / GAP_MECH, f_elec_Hz=f_e))
    n_t = round(2 * math.pi * R_TOOTH / 13.6); f_e = n_t * rpm / 60
    dphi = B_SWING * A_SPINE * 1e-6                                       # Wb peak-to-peak
    e_per_turn = math.pi * f_e * dphi                                     # V peak per turn (sinusoidal swing)
    N_need = V_LINK / N_COILS / e_per_turn
    for d in (0.08, 0.10, 0.12, 0.16, 0.20, 0.25, 0.40):
        N, R = coil(d)
        e_pk = N * e_per_turn
        out["rows"].append(dict(d_mm=d, N=N, R_ohm=R, emf_pk_V=e_pk, string_emf_kV=N_COILS * e_pk / 1e3,
                                I2R_W=max(I_dc) ** 2 * R * N_COILS, I_stall_A=V_LINK / (N_COILS * R)))
    out.update(n_teeth=n_t, f_elec_Hz=f_e, dphi_Wb=dphi, emf_per_turn_V=e_per_turn, N_needed_per_coil=N_need)
    json.dump(out, open(os.path.join(HERE, "reverse_vdg_budget_results.json"), "w"), indent=1, default=float)
    print(f"link {V_LINK / 1e3:.0f} kV, surplus {P_av[0]:.2f}-{P_av[1]:.2f} W -> {out['I_link_uA'][0]:.0f}-{out['I_link_uA'][1]:.0f} uA")
    for k, v in out["T_available_Nm"].items():
        print(f"torque available ({k}): {v[0] * 1e3:.0f}-{v[1] * 1e3:.0f} mN m   vs need {T_need[0] * 1e3:.0f} (shell/vacuum) "
              f"to {T_need[1] * 1e3:.0f} (open air) mN m")
    for t in out["teeth"]:
        print(f"tooth pitch {t['pitch_mm']} mm: {t['n_teeth']} teeth, pitch/gap {t['pitch_over_gap']:.0f}, f_e {t['f_elec_Hz']:.0f} Hz")
    print(f"{n_t} teeth: f_e {f_e:.0f} Hz, emf {e_per_turn * 1e3:.1f} mV/turn, need {N_need:.0f} turns per coil for "
          f"{V_LINK / N_COILS / 1e3:.2f} kV")
    for r in out["rows"]:
        print(f"  wire {r['d_mm']} mm: N {r['N']}, R {r['R_ohm'] / 1e3:.1f} kohm, string emf {r['string_emf_kV']:.1f} kV, "
              f"I2R {r['I2R_W'] * 1e3:.2f} mW, stall {r['I_stall_A'] * 1e3:.1f} mA")


if __name__ == "__main__":
    main()
