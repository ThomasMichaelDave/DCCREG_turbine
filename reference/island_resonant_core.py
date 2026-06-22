#!/usr/bin/env python3
"""
reference/island_resonant_core.py — the series-LC island transfer model (the efficiency fix).
==============================================================================================
TMD added a series inductor to each island variable cap (Lx3 in series with Cx3 → the BR bank;
Lx4 in series with Cx4 → the AR bank; confirmed from DCCREG_Turbine_circuit.net, 37 components).
This converts the island charge transfer from a DIRECT DUMP (loses 1/2 C_eff dV^2 irrespective of
R -- the two-capacitor paradox) into a HALF-CYCLE LC RESONANT TRANSFER (loses only the ring's
resistive dissipation, -> 0 as Q rises).

This is a NEW model: the frozen `shuttle_core`/`island_charging_cosim` stay the DIRECT-transfer
baseline for the comparison. Conservation is impeccable -- the recovered tax is energy REDISTRIBUTED
into the receiving bank, not invented. Pure EE: a real inductor + standard LC physics.

  closed_form(...)  -> the brief-§1 estimate (C_eff, Z, t_half, i_pk, Q, E_loss, f_rec)
  integrate(...)    -> [SOLVER] a series-RLC transient (authoritative over the closed form):
                       q, E_bank_gained, E_loss(integral), t_half(current-zero), i_pk, residual
  conservation(...) -> the energy guard + the +5% R/Lx non-tautology trip (Rule 6.1)

Tiers [OC] derivable LC · [IR] design choice · [ME] method. Symbol hygiene (g, theta, *Mm, Lx).
"""
import math


def closed_form(C_src, C_bank, dV, Lx, R):
    """Brief-§1 closed-form estimate. C in F, dV in V, Lx in H, R in ohm.
    Returns C_eff, Z, t_half, i_pk, Q, E_2cap (the direct two-cap loss), E_loss, f_rec."""
    C_eff = C_src * C_bank / (C_src + C_bank)
    Z = math.sqrt(Lx / C_eff)                       # ring impedance
    t_half = math.pi * math.sqrt(Lx * C_eff)        # half-period, transfer completes at current-zero
    i_pk = dV / Z                                   # = dV*sqrt(C_eff/Lx)
    Q = Z / R if R > 0 else float("inf")
    E_2cap = 0.5 * C_eff * dV ** 2                  # the DIRECT dump loss (two-cap paradox)
    # resistive loss over the half-cycle ring; -> 0 as Q -> inf (vs the fixed E_2cap)
    E_loss = (math.pi / (2 * Q)) * E_2cap if Q != float("inf") else 0.0
    f_rec = 1.0 - math.pi / (2 * Q) if Q != float("inf") else 1.0   # recovered-tax fraction
    return dict(C_eff=C_eff, Z=Z, t_half=t_half, i_pk=i_pk, Q=Q,
                E_2cap=E_2cap, E_loss=E_loss, f_rec=f_rec)


def integrate(C_src, C_bank, dV, Lx, R, V_bank0=0.0, n=20000, perturb_R=0.0):
    """[SOLVER] series-RLC transient transfer C_src -> Lx/R -> C_bank, from i=0 to the first
    current-zero. Energy-conserving RK4; the AUTHORITATIVE result (truncation/non-ideal half-cycle
    captured). `perturb_R` (the +5% trip) scales R in the LOSS INTEGRAL ONLY -- the dynamics use the
    true R, so a non-zero perturb breaks the independent energy balance (proving the guard isn't an
    identity). Returns the transfer ledger + the conservation residual."""
    V_src = V_bank0 + dV                             # src starts dV above the bank
    V_bank = V_bank0
    i = 0.0
    cf = closed_form(C_src, C_bank, dV, Lx, R)
    dt = cf["t_half"] / n * 1.5                       # cover a little past t_half to catch the zero
    E_src0 = 0.5 * C_src * V_src ** 2
    E_bank0 = 0.5 * C_bank * V_bank ** 2
    E_loss = 0.0                                      # independent dissipation integral (i^2 R dt)
    i_pk = 0.0; started = False; t = 0.0; t_half = None
    R_loss = R * (1.0 + perturb_R)                    # the +5% trip enters ONLY the loss accounting

    def deriv(V_s, V_b, ii):
        return (-ii / C_src, ii / C_bank, (V_s - V_b - ii * R) / Lx)

    for _ in range(int(n * 1.5)):
        k1 = deriv(V_src, V_bank, i)
        k2 = deriv(V_src + .5*dt*k1[0], V_bank + .5*dt*k1[1], i + .5*dt*k1[2])
        k3 = deriv(V_src + .5*dt*k2[0], V_bank + .5*dt*k2[1], i + .5*dt*k2[2])
        k4 = deriv(V_src + dt*k3[0], V_bank + dt*k3[1], i + dt*k3[2])
        Vsn = V_src + dt/6*(k1[0]+2*k2[0]+2*k3[0]+k4[0])
        Vbn = V_bank + dt/6*(k1[1]+2*k2[1]+2*k3[1]+k4[1])
        iN = i + dt/6*(k1[2]+2*k2[2]+2*k3[2]+k4[2])
        E_loss += R_loss * 0.5 * (i*i + iN*iN) * dt   # trapezoidal i^2 R
        i_pk = max(i_pk, abs(iN))
        if abs(iN) > 1e-12:
            started = True
        if started and iN * i < 0:                    # current-zero -> half-cycle complete
            t_half = t + dt; V_src, V_bank, i = Vsn, Vbn, iN; break
        t += dt; V_src, V_bank, i = Vsn, Vbn, iN
    if t_half is None:
        t_half = t
    E_src_f = 0.5 * C_src * V_src ** 2
    E_bank_f = 0.5 * C_bank * V_bank ** 2
    E_resid_L = 0.5 * Lx * i ** 2                      # inductor residual at the stop (->0 ideal)
    E_src_lost = E_src0 - E_src_f
    E_bank_gained = E_bank_f - E_bank0
    q = C_bank * (V_bank - V_bank0)                    # charge delivered to the bank
    # the energy balance (independent of the i^2R integral): src lost = bank + loss + L-residual
    E_loss_balance = E_src_lost - E_bank_gained - E_resid_L
    resid = abs(E_loss - E_loss_balance) / max(E_src_lost, 1e-30)
    # recovered tax = direct two-cap loss - resonant loss (the actual reduction in dissipation)
    recovered = cf["E_2cap"] - E_loss
    f_rec = recovered / cf["E_2cap"] if cf["E_2cap"] > 0 else 0.0
    return dict(q=q, E_src_lost=E_src_lost, E_bank_gained=E_bank_gained, E_loss=E_loss,
                E_resid_L=E_resid_L, t_half=t_half, i_pk=i_pk, Q=cf["Q"], C_eff=cf["C_eff"],
                Z=cf["Z"], V_src_final=V_src, V_bank_final=V_bank, E_2cap_direct=cf["E_2cap"],
                recovered=recovered, f_rec=f_rec, resid=resid)


def conservation(C_src, C_bank, dV, Lx, R):
    """The energy guard + the +5% non-tautology trip. Returns (closes, resid, trips, resid_trip).
    The guard checks the independent i^2R loss integral against the state-energy balance; the +5%
    R perturbation enters the loss integral only -> the balance no longer matches -> the residual
    jumps (Rule 6.1: the guard CAN fail; it is not an identity)."""
    base = integrate(C_src, C_bank, dV, Lx, R)
    trip = integrate(C_src, C_bank, dV, Lx, R, perturb_R=0.05)
    closes = base["resid"] < 1e-3
    trips = trip["resid"] > 5 * max(base["resid"], 1e-9) and trip["resid"] > 1e-3
    return closes, base["resid"], trips, trip["resid"]


if __name__ == "__main__":
    # a quick self-demo at a representative island transfer
    C_src, C_bank, dV = 471e-12, 2640e-9, 5000.0      # island 471 pF -> ~2.6 uF bank, 5 kV above
    for Lx, R, tag in [(1e-3, 2.0, "Q~hi"), (1e-3, 20.0, "Q~mid"), (1e-3, 100.0, "Q~lo")]:
        cf = closed_form(C_src, C_bank, dV, Lx, R)
        it = integrate(C_src, C_bank, dV, Lx, R)
        print(f"[{tag}] Lx={Lx*1e3:.1f}mH R={R}ohm | Q={cf['Q']:.1f} t1/2={cf['t_half']*1e6:.1f}us "
              f"i_pk={cf['i_pk']:.2f}A | E_2cap={cf['E_2cap']*1e3:.3f}mJ "
              f"E_loss cf={cf['E_loss']*1e3:.4f}/int={it['E_loss']*1e3:.4f}mJ f_rec={it['f_rec']:.3f} "
              f"resid={it['resid']:.1e}")
    print("conservation+trip:", conservation(C_src, C_bank, dV, 1e-3, 20.0))
