#!/usr/bin/env python3
"""
xsim_netgen.py — ngspice netlist GENERATOR for the SPICE cross-validation gate (Phase 6).
==========================================================================================
A PRODUCER of `.net` files; a CONSUMER of the consensus circuit. It reads the device point,
profiles and thresholds from the canonical sources (it does NOT hand-enter them, brief §2.2):
  - `shuttle_core.py`  module constants (C1MIN/C1MAX/C2MIN/C2MAX, CPAR, CA, CB, the Cx
    plateau/collapse profile, pCboss/pCboss2, theta_backstop, PASCHEN_CORNER, paschen_strike,
    the TH_* event stations, L_RES_UH, F0_KHZ);
  - `presets/R1-baseline.json` (pgap, rrpm, vhvKV — the machine context).

The netlist is an INDEPENDENT time-domain realisation of the SAME circuit the native
quasi-static `shuttle_core` producer solves — a genuinely different method (trapezoidal/Gear
time-stepping vs fixed-point cluster-solve). ngspice is the WITNESS, never the judge; the
galvanic anchor (z = 1.2033, reference/doubler_core.py) is the tiebreaker (brief §1).

Netlist primitives (verified against ngspice-42, brief §3):
  - time-varying caps  -> charge-defined `Cxxx n+ n- Q='C(theta(t))*V(n+,n-)'` (the i=dQ/dt
    form injects BOTH C*dV/dt and the V*dC/dt pump term natively);
  - spark gaps / ideal diodes -> voltage-controlled switches `Sxxx` + `.model SW(vt vh ron roff)`
    with hysteresis (strike-on / hold-off-off). Near-ideal at X0 (no diode forward drop). [IR]

Symbol hygiene (CONVENTIONS.md): rotor angle `theta`; gap `g`; `Nsec`; p-prefix; *Mm. [OC]/[IR].
"""
import os
import json
import math

import shuttle_core as sc

HERE = os.path.dirname(os.path.abspath(__file__))
NETDIR = HERE                                  # flat filenames (CONVENTIONS.md)


# ----------------------------------------------------------------------------------------
# Canonical parameter read (brief §2.2 — read, never hand-enter)
# ----------------------------------------------------------------------------------------
def read_params():
    """Pull the device point + machine context from the canonical sources. Returns a dict in
    SI-friendly raw values (pF kept as pF; converted to farads at netlist-emit time)."""
    with open(os.path.join(HERE, "presets", "R1-baseline.json")) as fh:
        preset = json.load(fh)
    pv = {k: v["value"] for k, v in preset["params"].items()}
    P = sc.Params()                            # default ideal-tier Params (for Cx profile etc.)
    return dict(
        # frozen device-point caps (pF) — consumed from shuttle_core
        C1MIN=sc.C1MIN, C1MAX=sc.C1MAX, C2MIN=sc.C2MIN, C2MAX=sc.C2MAX,
        CA=sc.CA, CB=sc.CB, CPAR=sc.CPAR,
        # Cx flying-bucket profile (pF) + strays
        cx_max=P.cx_max, cx_min=P.cx_min, pCboss=P.pCboss, pCboss2=0.0,
        gap_stray=P.gap_stray,
        # event stations (sector fraction) — the native timing the witness must reproduce
        TH_RET=sc.TH_RET, TH_LOAD=sc.TH_LOAD, TH_QUENCH=sc.TH_QUENCH,
        TH_COL0=sc.TH_COL0, TH_COL1=sc.TH_COL1,
        theta_backstop=P.theta_backstop,
        # tank / machine context
        L_RES_UH=sc.L_RES_UH, F0_KHZ=sc.F0_KHZ,
        pgap_mm=pv["pgap"], rrpm=pv["rrpm"], vhvKV=pv["vhvKV"],
        # Paschen corners (for arc/bootstrap tiers)
        PASCHEN_CORNER=dict(sc.PASCHEN_CORNER), ENHANCE=dict(sc.ENHANCE),
        anchor_z=sc.Z_BASELINE,
    )


def pf(x):
    """pF value -> SPICE farad literal."""
    return f"{x * 1e-12:.6e}"


# ----------------------------------------------------------------------------------------
# X0 — degenerate-limit galvanic anchor (brief §4 X0, §3 X0-anchor-switches)
# ----------------------------------------------------------------------------------------
# Shuttles -> near-ideal galvanic diodes 1->3 / 4->2 (frozen direction); LR shorted; the
# islands/Cx are dropped (the diodes carry the charge directly). Must recover z = 1.2033.
#
# [IR — NAMED MODELLING NOTE, deviates from brief §3 "near-ideal switches"]: a ngspice
# voltage-controlled switch (`Sxxx`/`.model SW`) conducts BIDIRECTIONALLY while closed, so it
# cannot RECTIFY — the parametric pump never ratchets and the rail just sloshes (measured z=1.0,
# no growth, verified). The faithful one-way element is a near-ideal `.model D` diode with the
# forward drop driven to ~0 (large is, small n, small rs). Empirically its residual Vf does NOT
# pull z under 1.2033 (measured z=1.204, slightly ABOVE the anchor, insensitive to n over
# 0.001..0.02). So X0 uses near-ideal DIODES; the brief's concern (diode drop pulling z under)
# does not materialise at this device point. Surfaced, not engineered around.
GALV_DIODES = [(2, 0), (3, 0), (1, 3), (4, 2)]     # D1,D2,D3,D4 anode->cathode (frozen)
DIODE_MODEL = ".model ND D(is=1e-9 n=0.005 rs=1e-3 cjo=0)"   # near-ideal one-way (Vf->0)
# robust integration options: the behavioral-Q cap carries an internal node (c1v_int1) that
# trips "timestep too small" under over-tight tol; these settle the pump cleanly to ~48 cycles.
X0_OPTIONS = ".options reltol=1e-5 abstol=1e-12 vntol=1e-9 gmin=1e-14"


def netlist_x0_galvanic(p, f_pump=1000.0, n_cycles=48, step_per_cycle=800, k_square=12.0):
    """Continuous-time galvanic doubler. C1/C2 swing (tanh square, anti-phase: C1 max when C2
    min) between the frozen extremes; near-ideal one-way diodes commutate 2->0,3->0,1->3,4->2.
    The unloaded lossless pump grows the rail |V1|+|V4| ~ z per mechanical cycle; the consumer
    reads z from the post-burn per-cycle ratio (brief X0). f_pump is arbitrary (ideal tier is
    scale-invariant). k_square sharpens the two-phase edges toward the native discrete steps."""
    T = 1.0 / f_pump
    tstop = n_cycles * T
    tmax = T / step_per_cycle
    w = 2.0 * math.pi * f_pump
    L = []
    L.append("* xsim X0 — degenerate galvanic anchor (shuttles -> near-ideal diodes, LR short)")
    L.append("* must recover z = 1.2033 = reference/doubler_core.py ANCHORS['device']")
    L.append(f".param w={w:.8e}")
    L.append("")
    # tanh square swings, anti-phase: C1 high on phase A (sin>0), C2 high on phase B (sin<0).
    # theta(t)=f_pump*time mod 1; the sharp edges trap charge during collapse (the V*dC/dt boost).
    c1_lo, c1_hi = p["C1MIN"], p["C1MAX"]
    c2_lo, c2_hi = p["C2MIN"], p["C2MAX"]
    s1 = f"(0.5*(1+tanh({k_square:.1f}*sin(w*time))))"
    s2 = f"(0.5*(1+tanh({k_square:.1f}*sin(w*time+{math.pi:.8f}))))"
    c1expr = f"({pf(c1_lo)}+{pf(c1_hi - c1_lo)}*{s1})"
    c2expr = f"({pf(c2_lo)}+{pf(c2_hi - c2_lo)}*{s2})"
    L.append("* time-varying rotor caps (charge-defined; parametric V*dC/dt pump term native)")
    L.append(f"C1v 1 0 Q='{c1expr}*V(1)'")
    L.append(f"C2v 4 0 Q='{c2expr}*V(4)'")
    L.append("* fixed strays / transfer caps")
    L.append(f"Cpar1 1 0 {pf(p['CPAR'])}")
    L.append(f"Cpar2 2 0 {pf(p['CPAR'])}")
    L.append(f"Cpar3 3 0 {pf(p['CPAR'])}")
    L.append(f"Cpar4 4 0 {pf(p['CPAR'])}")
    L.append(f"Ca 1 2 {pf(p['CA'])}")
    L.append(f"Cb 3 4 {pf(p['CB'])}")
    L.append("")
    L.append("* near-ideal one-way diodes (Vf->0) — a SW switch is bidirectional => no pump [IR]")
    L.append(DIODE_MODEL)
    for i, (a, c) in enumerate(GALV_DIODES, 1):
        L.append(f"Dd{i} {a} {c} ND")           # diode anode->cathode = frozen D-direction
    L.append("")
    L.append("* seed the down-pumping eigenvector V=[-1,0,0,-1] (brief: galvanic seed)")
    L.append(".ic v(1)=-1 v(2)=0 v(3)=0 v(4)=-1")
    L.append(f".tran {tmax:.6e} {tstop:.6e} uic")
    L.append(f"{X0_OPTIONS} maxstep={tmax:.6e}")
    L.append(".end")
    meta = dict(f_pump=f_pump, T=T, n_cycles=n_cycles, tstop=tstop, tmax=tmax,
                k_square=k_square)
    return "\n".join(L) + "\n", meta


# ----------------------------------------------------------------------------------------
# X1' — ideal flying-bucket shuttle, Queiroz source-imposed islands (rev 0.3 addendum)
# ----------------------------------------------------------------------------------------
# Unblocks the rev-0.1 shuttle (timestep collapse / no ratchet). Construction:
#   - C1v/C2v: charge-defined Q= caps (proven in X0; compose on shared nodes with Ca/CPAR).
#   - islands Cx3 (7-3), Cx4 (8-2): CHARGE-CONTROLLED (Queiroz) V=Q/Cx, Cx+boss lumped so each
#     island node carries a single cap + gaps (no over-constraint). The collapse boost V=Q/Cx(t)
#     is imposed by the source law -> ratchet by construction, no behavioral-Q internal node.
#   - return SG1/SG2 + load SG3a/SG4a: CLOCKED BIDIRECTIONAL switches (the ideal-tier native gaps
#     are cluster-merge equalizations; one-way diodes are wrong here and never conduct down-pumping).
#   - fire SG3b/SG4b: SOURCE-IMPOSED soft-threshold dump I=win*gm*max(0,V(isl,snk)-Vstr) — one-way,
#     THRESHOLD Vstr (emergent: sweeping Vstr moves the fire angle, demonstrated), self-extinguishing,
#     eligibility = collapse window (the Cx profile), NOT a fire clock edge (addendum firewall §1).
# [IR] K is a dimensionless conditioner that cancels in V=Q/C (K-invariant by construction).
GSW_MODEL = ".model GSW SW(vt=0.5 vh=0.2 ron=1 roff=1e9)"
X1_OPTIONS = ".options reltol=1e-5 abstol=1e-12 vntol=1e-9 gmin=1e-11"


def _cx_wave(p, th, c0):
    """Cx farads waveform string over rotor angle th: plateau cx_max+boss, a raised-cosine collapse
    to cx_min+boss across [c0,c0+span], then reinflate to plateau (the island is empty post-fire, so
    immediate reinflation is immaterial to the pump and keeps Cx CONTINUOUS across the th=1->0 wrap —
    a held-collapse profile slams V=Q/Cx at the wrap and trips the integrator). [IR profile]"""
    boss = p["pCboss"]
    span = p["TH_COL1"] - p["TH_COL0"]
    hi, lo = pf(p["cx_max"] + boss), pf(p["cx_min"] + boss)
    dn = (f"({lo}+{pf(p['cx_max'] - p['cx_min'])}*0.5*"
          f"(1+cos(3.14159265*({th}-{c0})/{span})))")
    return f"( ({th}<{c0})? {hi} : (({th}<{c0 + span})? {dn} : {hi}) )"


def _island(p, idx, isl, snk, c0):
    """Queiroz charge-controlled island `idx` between island node `isl` and sink `snk`."""
    return [
        f"Bc{idx} c{idx} 0 V='Kc*{_cx_wave(p, 'V(th)', c0)}'",
        f"Bv{idx} {isl} m{idx} V='V(q{idx})/V(c{idx})'",
        f"Vs{idx} m{idx} {snk} 0",
        f"Gq{idx} 0 q{idx} VALUE='Kc*I(Vs{idx})'",
        f"Cq{idx} q{idx} 0 1",
        f"Rq{idx} q{idx} 0 1e15",
        f"Cstab{idx} {isl} 0 1e-15",            # tiny start-up stabiliser (negligible)
    ]


def netlist_x1_shuttle(p, K=1e9, Vstrike=0.0, gm=1e-3, seed=-1.0,
                       f_pump=1000.0, n_cycles=45, step_per_cycle=400, k_square=12.0):
    """Ideal flying-bucket shuttle (branch A 1->island7->3, branch B 4->island8->2). Returns the
    netlist + meta. z read from the post-burn rail ratio; the fire angle (emergent δ) is read from
    the island-overvoltage peak by the consumer. Vstrike sweeps the strike threshold (emergence)."""
    T = 1.0 / f_pump
    tstop, tmax = n_cycles * T, T / step_per_cycle
    w = 2.0 * math.pi * f_pump
    RET, LOAD, QU = p["TH_RET"], p["TH_LOAD"], p["TH_QUENCH"]
    COL0, COL1 = p["TH_COL0"], p["TH_COL1"]

    def win(a, b):
        return f"(V(th)>{a})*(V(th)<{b})"

    s1 = f"(0.5*(1+tanh({k_square:.1f}*sin(w*time))))"
    s2 = f"(0.5*(1+tanh({k_square:.1f}*sin(w*time+{math.pi:.8f}))))"
    c1 = f"({pf(p['C1MIN'])}+{pf(p['C1MAX'] - p['C1MIN'])}*{s1})"
    c2 = f"({pf(p['C2MIN'])}+{pf(p['C2MAX'] - p['C2MIN'])}*{s2})"
    L = ["* xsim X1' — ideal flying-bucket shuttle (Queiroz source-imposed islands; rev 0.3)",
         "* fire SG3b/SG4b = threshold strike (emergent δ), NOT clocked (addendum §1 firewall)",
         f".param w={w:.8e} Kc={K:.3e} Vstr={Vstrike} gm={gm:.3e}",
         f"Vth th 0 PULSE(0 1 0 {0.999 * T:.6e} 1n 1n {T:.6e})",
         "* rotor caps (charge-defined Q=; pump term native) + fixed strays/transfer caps",
         f"C1v 1 0 Q='{c1}*V(1)'", f"C2v 4 0 Q='{c2}*V(4)'",
         f"Cpar1 1 0 {pf(p['CPAR'])}", f"Cpar2 2 0 {pf(p['CPAR'])}",
         f"Cpar3 3 0 {pf(p['CPAR'])}", f"Cpar4 4 0 {pf(p['CPAR'])}",
         f"Ca 1 2 {pf(p['CA'])}", f"Cb 3 4 {pf(p['CB'])}",
         "* Queiroz charge-controlled islands (V=Q/Cx; collapse boost imposed, no stiff Q-node)"]
    L += _island(p, 3, 7, 3, COL0)
    L += _island(p, 4, 8, 2, COL0 + 0.5)
    L += [GSW_MODEL,
          "* clocked bidirectional return (clamp) + load (equalize src<->island) gaps",
          f"Bcr1 cr1 0 V='{win(RET, 0.5)}'", "Sret1 2 0 cr1 0 GSW",
          f"Bcr2 cr2 0 V='{win(0.5 + RET, 1.0)}'", "Sret2 3 0 cr2 0 GSW",
          f"Bcl1 cl1 0 V='{win(LOAD, QU)}'", "Sld1 1 7 cl1 0 GSW",
          f"Bcl2 cl2 0 V='{win(0.5 + LOAD, 0.5 + QU)}'", "Sld2 4 8 cl2 0 GSW",
          "* source-imposed threshold fire (emergent angle; eligibility = collapse window)",
          f"Bfr1 7 3 I='{win(COL0, COL1)}*gm*max(0,V(7)-V(3)-Vstr)'",
          f"Bfr2 8 2 I='{win(0.5 + COL0, 0.5 + COL1)}*gm*max(0,V(8)-V(2)-Vstr)'",
          f".ic v(1)={seed} v(4)={seed} v(2)=0 v(3)=0 v(q3)=0 v(q4)=0",
          f".tran {tmax:.6e} {tstop:.6e} uic",
          f"{X1_OPTIONS} maxstep={tmax:.6e}", ".end"]
    meta = dict(f_pump=f_pump, T=T, n_cycles=n_cycles, tmax=tmax, K=K, Vstrike=Vstrike,
                gm=gm, COL0=COL0, COL1=COL1, RET=RET)
    return "\n".join(L) + "\n", meta


# ----------------------------------------------------------------------------------------
# Emit
# ----------------------------------------------------------------------------------------
def write_all():
    p = read_params()
    out = {}
    net, meta = netlist_x0_galvanic(p)
    path = os.path.join(NETDIR, "xsim_x0_galvanic.net")
    with open(path, "w") as fh:
        fh.write(net)
    out["x0"] = dict(path=path, meta=meta)
    net1, meta1 = netlist_x1_shuttle(p)
    path1 = os.path.join(NETDIR, "xsim_x1_shuttle.net")
    with open(path1, "w") as fh:
        fh.write(net1)
    out["x1"] = dict(path=path1, meta=meta1)
    return p, out


if __name__ == "__main__":
    params, written = write_all()
    print("xsim_netgen — canonical params read from shuttle_core + presets/R1-baseline.json")
    print(f"  device point: C1 {params['C1MIN']:.0f}-{params['C1MAX']:.0f} pF, "
          f"C2 {params['C2MIN']:.0f}-{params['C2MAX']:.0f} pF, CPAR {params['CPAR']:.0f}, "
          f"CA/CB {params['CA']:.0f}/{params['CB']:.0f} pF; anchor z={params['anchor_z']}")
    for k, v in written.items():
        print(f"  wrote {os.path.basename(v['path'])}  ({v['meta']})")
