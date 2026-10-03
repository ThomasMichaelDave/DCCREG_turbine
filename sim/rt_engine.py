#!/usr/bin/env python3
"""
sim/rt_engine.py — ROUND-TRIP engine: the pump engine fed by the 3-D build                       [ME]
==================================================================================================
DERIVED from sim/pump_engine.py (frozen, imported read-only) and held to it by gate RT0: with every
extension off, build_net() IS pump_engine.build_net() and z is pump-synth's freeze headline to 1e-9.

Extensions (each gated in sim/rt_gates.py):
  * SERIES TANK at the pump frequency [OC] (D-TANK): the drawn tank is R-A -L_R1- n18 -C_R1- n00 -L_R2-
    R-B. At the 300 Hz pump rate the coils are ~0.07 ohm, so n18 = R-A and n00 = R-B and the rotor
    halves are joined ONLY by C_R1 (the freeze's parallel tank, where L_R shorts R-A to R-B, is the
    'collapsed' case). Probe convention (RT1): R-A is the reference, every ladder stray to it, R-B a
    node with C_R1 to the reference. With a capacitance model the reference is the enclosure.
  * CAPACITANCE-MATRIX INPUT: a reduced model of the build (round_trip.CModel) -- every pair of drawn
    nets and every net to the enclosure, fixed or a function of the relative angle -- replaces the
    ladder values AND the fixed floors (C_min, Cx_min, Cpar, gap and island strays, the boss term).
  * COUNTER-ROTATION [OC]: rpm_rel = rpm_rotor + rpm_stator drives the pump (the field and the engine see
    the relative angle only, so z does not change); I9 is checked PER BODY at its own radius and speed;
    D-SPLIT = rpm_stator / rpm_rel, default 0.5 [IR].
  * MOTOR IN, CONTINUOUS TIME: see motor_* below (MC1-MC3).
Pure EE. No file I/O on import.
"""
import math
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
for _p in (HERE, ROOT, os.path.join(ROOT, "reference")):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import pump_engine as PE                    # frozen, read-only

RT_VERSION = "rt_engine r0.1 (derived from pump_engine r0.1)"
GND = PE.GND
TANK_MERGE = {"n18": "R-A", "n00": "R-B"}  # coils shorted at the pump frequency [OC]
DRAWN_NETS = ("1", "2", "3", "4", "7", "8", "n17", "n23", "R-A", "R-B")
D_SPLIT = 0.5                               # rpm_stator / rpm_rel [IR, TMD-gated]


class RTNet(PE.Net):
    """pump_engine's Net with a configurable set of node names tied to the reference."""

    def __init__(self, ground=("0", "R-A", "R-B", "ref", "enc")):
        super().__init__()
        self.ground = set(ground)

    def n(self, name):
        name = TANK_MERGE.get(name, name)
        if name in self.ground:
            return GND
        if name not in self.idx:
            self.idx[name] = len(self.nodes); self.nodes.append(name)
        return self.idx[name]


LADDER_PARTS = ("C1", "C2", "Ca", "Cb", "Cx3", "Cx4", "floors")


def build_net(cfg, tank="collapsed", C_R1_pF=None, cmodel=None, lx=None, galvanic=None, ladder=None, extra=(),
              ref=None):
    """The drawn pump. tank 'collapsed' + no cmodel = pump_engine.build_net (RT0). tank 'series': R-B a
    node joined to R-A only by C_R1 (C_R1_pF, or the cmodel's extracted R-A - R-B coupling).
    cmodel: a round_trip.CModel -- all capacitances from the build, reference = the enclosure.
    For the ledger (one change at a time): `ladder` = the ladder parts kept (LADDER_PARTS; default all
    without a cmodel, none with one), `extra` = (name, a, b, C | callable(theta)) caps added (b may be
    'enc'), `ref` = 'R-A' (probe convention: the enclosure is tied to rotor A) or 'enc'."""
    if tank == "collapsed" and cmodel is None and ladder is None and not extra:
        return PE.build_net(cfg, lx=lx, galvanic=galvanic)
    if cfg["topology"] != "drawn":
        raise ValueError("round-trip extensions apply to the drawn topology")
    lx = cfg["Lx_mH"] * 1e-3 if lx is None else lx
    galvanic = cfg["galvanic"] if galvanic is None else galvanic
    if galvanic:
        raise ValueError("the galvanic twin (G0) is not round-tripped")
    compat = cfg["arming"] == "r02"
    W = PE.windows(cfg, compat)
    keep = set(LADDER_PARTS if cmodel is None else ()) if ladder is None else set(ladder)
    ref = ref or ("R-A" if cmodel is None else "enc")
    if ref == "R-A":                         # probe convention: R-A (and the enclosure) = the reference
        net = RTNet(ground=("0", "R-A", "ref", "enc"))
    else:                                    # the enclosure is the reference; both rotor halves float
        net = RTNet(ground=("0", "ref", "enc"))
    net.prof = PE.make_profile(cfg)
    boss = (cfg["pCboss"] + cfg["pCboss2"]) * 1e-12
    gstray = cfg["gap_stray"] * 1e-12
    for n in ("1", "2", "3", "4"):
        net.n(n)
    if cmodel is not None or extra:
        for n in DRAWN_NETS:
            if not (ref == "R-A" and n == "R-A"):
                net.n(n)
    for comp, a, b in PE.EDGES:
        if comp in PE.TANK_PARTS or (comp in PE.MOTOR_PARTS and not cfg["motor"]):
            continue
        i, j = net.n(a), net.n(b)
        if comp in ("C1", "C2", "Ca1", "Cb1", "Cx3", "Cx4"):
            if comp.rstrip("1") not in keep and comp not in keep:
                continue                     # realized by the capacitance model / an extra coupling
            if comp == "C1":
                net.caps.append(("C1", j, i, "C1"))
            elif comp == "C2":
                net.caps.append(("C2", j, i, "C2"))
            elif comp == "Ca1":
                net.caps.append((comp, i, j, cfg["Ca"] * 1e-12))
            elif comp == "Cb1":
                net.caps.append((comp, i, j, cfg["Cb"] * 1e-12))
            else:
                net.caps.append((comp, i, j, comp))
                if "floors" in keep:
                    net.caps.append((comp + "_boss", i, j, boss))
        elif comp in ("Lx3", "Lx4"):
            net.inds.append((comp, i, j, lx, cfg["R_lx"], "lx"))
        elif comp.startswith("L_A") or comp.startswith("L_B"):
            net.inds.append((comp, i, j, cfg["L_motor"], cfg["R_motor"], "motor"))
        elif comp.startswith("C_AR") or comp.startswith("C__AR") or comp.startswith("C_BR"):
            net.caps.append((comp, i, j, cfg["C_motor_nF"] * 1e-9))
        elif comp in PE.GAP_CLASS:
            net.gaps.append(PE.gap_tuple(cfg, comp, i, j, W[comp], PE.GAP_CLASS[comp]))
            if "floors" in keep:
                net.caps.append((comp + "_stray", i, j, gstray))
        else:
            raise ValueError(comp)
    if C_R1_pF is not None:
        net.caps.append(("C_R1", net.n("R-B"), net.n("R-A"), float(C_R1_pF) * 1e-12))
    if "floors" in keep:
        for n in ("1", "2", "3", "4"):
            net.caps.append((f"Cpar{n}", net.n(n), GND, cfg["Cpar"] * 1e-12))
        if cfg["island_stray"] > 0:
            for n in ("7", "8", "n17", "n23"):
                net.caps.append((f"Cs_{n}", net.n(n), GND, cfg["island_stray"] * 1e-12))
    caps = list(cmodel.caps()) if cmodel is not None else []
    for name, a, b, f in caps + list(extra):
        ia = net.n(a)
        ib = GND if b == "enc" else net.n(b)
        if ia == ib:
            continue                         # both ends on the reference (e.g. R-A to enc, probe convention)
        net.caps.append((name, ia, ib, f))
    net.meta = dict(lx=lx, galvanic=False, motor=cfg["motor"], topology="drawn", tank=tank,
                    cmodel=None if cmodel is None else cmodel.tag)
    return net


def run(net, cfg, record=False, events=False, log=None):
    """One cold exact run (the standard seed) -> pump_engine.monodromy's dict."""
    return PE.monodromy(net, cfg, log=log, record=record, events=events)


def z_of(cfg, **kw):
    net = build_net(cfg, **kw)
    m = run(net, cfg)
    return m["z"], m["converged"]


# ---------------------------------------------------------------------------------------------------
# counter-rotation (per body I9)
# ---------------------------------------------------------------------------------------------------
def counter_rotation(rpm_rel, split=D_SPLIT, r_rotor_mm=491.49, r_stator_mm=None, rim_hard=None):
    """Each body's speed and rim speed for a relative speed and a split rpm_stator / rpm_rel. The PRF
    follows rpm_rel. r_stator_mm: the stator's outermost spinning radius (the lead frame)."""
    import design_synth as DS
    rh = DS.RIM_HARD if rim_hard is None else rim_hard
    rr, rs = (1.0 - split) * rpm_rel, split * rpm_rel
    v_r = 2 * math.pi * rr / 60.0 * r_rotor_mm * 1e-3
    v_s = 2 * math.pi * rs / 60.0 * (r_stator_mm or r_rotor_mm) * 1e-3
    return dict(rpm_rel=rpm_rel, split=split, rpm_rotor=rr, rpm_stator=rs, rim_rotor=v_r, rim_stator=v_s,
                I9_rotor=v_r < rh, I9_stator=v_s < rh, rim_hard=rh, prf_hz=6 * rpm_rel / 60.0)


def max_rpm_rel(split=D_SPLIT, r_rotor_mm=491.49, r_stator_mm=None, rpm_I12=float("inf"), rim_hard=None):
    """The largest relative rpm passing I9 on both bodies (and the split-independent I12 bound)."""
    import design_synth as DS
    rh = DS.RIM_HARD if rim_hard is None else rim_hard
    w = lambda r: rh / (r * 1e-3) * 60.0 / (2 * math.pi)
    lim = [rpm_I12]
    if split < 1.0:
        lim.append(w(r_rotor_mm) / (1.0 - split))
    if split > 0.0:
        lim.append(w(r_stator_mm or r_rotor_mm) / split)
    return min(lim)


def _selftest():
    cfg = PE.make_config({})
    n0 = build_net(cfg)
    ok = isinstance(n0, PE.Net) and len(n0.gaps) == 8
    n1 = build_net(cfg, tank="series", C_R1_pF=785.0)
    ok &= "R-B" in n1.nodes and any(c[0] == "C_R1" for c in n1.caps) and len(n1.gaps) == 8
    ok &= abs(max_rpm_rel(0.0) - 200.0 / 0.49149 * 60 / (2 * math.pi)) < 1e-6
    if not ok:
        raise AssertionError("rt_engine on-load self-test FAILED")
    return True


SELFTEST_OK = _selftest()
