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
        TH_RET=sc.TH_RET, TH_LOAD=sc.TH_LOAD, TH_COL0=sc.TH_COL0, TH_COL1=sc.TH_COL1,
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
    return p, out


if __name__ == "__main__":
    params, written = write_all()
    print("xsim_netgen — canonical params read from shuttle_core + presets/R1-baseline.json")
    print(f"  device point: C1 {params['C1MIN']:.0f}-{params['C1MAX']:.0f} pF, "
          f"C2 {params['C2MIN']:.0f}-{params['C2MAX']:.0f} pF, CPAR {params['CPAR']:.0f}, "
          f"CA/CB {params['CA']:.0f}/{params['CB']:.0f} pF; anchor z={params['anchor_z']}")
    for k, v in written.items():
        print(f"  wrote {os.path.basename(v['path'])}  ({v['meta']})")
