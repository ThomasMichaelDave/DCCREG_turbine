#!/usr/bin/env python3
"""
sim/stack_sizing.py -- the pump ladder for a DISC or a TUBE machine, and z under the record or the v4 topology
=============================================================================================================
DISC: exactly sim/pump_sizing.size (the PUMP-SYNTH ladder: one rotor/stator plate pair per varicap, R95-R387).
TUBE: per side an interleaved stack of self-supporting metal vanes in air (the air-variable-capacitor build):
  * n_plates rotor vanes and n_plates stator vanes per varicap per side -> 2 n_plates - 1 working gaps;
  * stator vanes: N_sec / 2 sectors of ws_deg, rotor vanes: N_sec / 2 sectors of wr_deg (wr < the stator gap, so
    there is a position with zero overlap) [OC: TMD];
  * C(theta) per gap from a 2-D cell (x periodic over one sector period at radius r, z periodic over
    stator vane | gap | rotor vane | gap), solved for the aligned and the opposed position at n_r radii and
    integrated over r_in..r_out. Air (moist-air eps_r) is the only dielectric. Inner / outer edge fringing is
    not in the 2-D cell: a fixed edge floor (C_edge_pF) is added to C_min [IR];
  * the rest of the ladder by the PUMP-SYNTH ratios (Ca = Cb = 1.10 C_max, Cx = 1.68 C_max, ...), pins allowed.
  * geometry readouts: stack lengths (C1 / Cx varicaps, Ca fixed plates), vane masses, rotor inertia, the stored
    rotational energy at the rpm, rim speed.
TOPOLOGY for z: 'record' = the netlist of record (pump_synth.engine_cfg + z_of, the calculator's path);
'v4' = DCCREG_Turbine_circuit_v4: C-EMs in series with SG1 / SG2 (6 per side, lumped), the coil-gap node
stray and the screened lead across the coil, the parallel tank (coil chain across R-A / R-B) [IR].
Pure EE, numpy only (runs in Pyodide). Tiers [OC]/[IR]/[RH]/[ME].
"""
import json
import math

import numpy as np

import pump_sizing as PS

EPS0_MM = 8.8541878128e-15                     # F/mm

TUBE_DEFAULTS = dict(
    r_inMm=50.0, r_outMm=160.0,                # vane band (the bicone hub sits between the A and B stacks)
    g_vMm=3.0, t_vaneMm=1.5,                   # air gap, vane thickness (Al)
    N_sec=12, ws_deg=30.0, wr_deg=22.0,        # 6 stator sectors of 30 deg, 6 rotor vanes of 22 deg
    n_plates=7,                                # rotor vanes = stator vanes per varicap per side
    dielectric="air", tempC=20.0, p_hPa=1013.0, rh=50.0,
    C_edge_pF=2.0,                             # inner + outer edge fringe floor added to C_min [IR]
    h_mm=0.25, n_r=5,                          # 2-D cell resolution, radii for the r integral [ME]
    rho_vane=2700.0,                           # Al, kg/m^3
    hub_mm=120.0, clock_mm=80.0, rel_mm=120.0, # axial allowances: central hub, clocking deck, reluctance section (per side)
    pitch_fixed_mm=4.5,                        # Ca / Cb fixed plates: 3 mm air + 1.5 mm plate per working gap
)
V4_DEFAULTS = dict(L_coil_H=1.85, R_coil=44.0, n_coils=6, C_mid_pF=1.0, C_screen_pF=57.0,
                   L_tank_uH=425.0, C_tank_pF=789.0, Q_tank=30.0)


# ---------------------------------------------------------------------------------------------------------
# the 2-D vane cell (matrix-free CG on a uniform grid, periodic in x and z) [ME]
# ---------------------------------------------------------------------------------------------------------
def _cell(r, p, shift_deg):
    """C per gap per mm of radius (F/mm) of ONE sector period at radius r, the rotor vanes turned by shift_deg
    from aligned (tube_caps multiplies by the N_sec / 2 periods)."""
    period_deg = 360.0 / (p["N_sec"] / 2.0)
    P = math.radians(period_deg) * r
    h = p["h_mm"]
    nx = max(16, int(round(P / h))); hx = P / nx
    t, g = p["t_vaneMm"], p["g_vMm"]
    # conductor cells are fixed at their centres: the potential drops over (ng + 1) cells, so hz = g / (ng + 1)
    # makes the electrical gap exactly g; the vane is nt cells (geometric thickness (nt + 1) hz ~ t)
    ng = max(4, int(round(g / h)))
    hz = g / (ng + 1)
    nt = max(1, int(round(t / hz)) - 1)
    nz = 2 * (nt + ng)
    x = (np.arange(nx) + 0.5) * hx
    xd = np.degrees(x / r)
    def band(c_deg, w_deg):
        d = (xd - c_deg + 0.5 * period_deg) % period_deg - 0.5 * period_deg
        return np.abs(d) < 0.5 * w_deg
    st = band(0.5 * period_deg, p["ws_deg"])
    ro = band(0.5 * period_deg + shift_deg, p["wr_deg"])
    cond = np.full((nx, nz), -1, dtype=np.int8)
    cond[np.ix_(st, np.arange(0, nt))] = 1                     # stator vane at 1 V
    cond[np.ix_(ro, np.arange(nt + ng, 2 * nt + ng))] = 0      # rotor vane at 0 V
    fixed = cond >= 0
    V = np.where(cond == 1, 1.0, 0.0)
    free = ~fixed
    ax, az = 1.0 / hx ** 2, 1.0 / hz ** 2
    diag = 2 * ax + 2 * az

    def lap(U):
        return (ax * (np.roll(U, 1, 0) + np.roll(U, -1, 0)) + az * (np.roll(U, 1, 1) + np.roll(U, -1, 1)) - diag * U)
    # solve lap(V) = 0 on free cells: A u = b with u the free values (Dirichlet on the vanes), CG
    Vb = np.where(fixed, V, 0.0)
    b = lap(Vb) * free
    def A(u):
        U = np.where(free, u, 0.0)
        return -lap(U) * free
    u = np.zeros_like(V); res = b - A(u); pdir = res * (1.0 / diag); z = pdir.copy()
    rz = float(np.sum(res * z))
    b2 = float(np.sum(b * b)) or 1.0
    for it in range(20000):
        Ap = A(pdir)
        alpha = rz / float(np.sum(pdir * Ap))
        u += alpha * pdir; res -= alpha * Ap
        if float(np.sum(res * res)) < 1e-20 * b2:
            break
        z = res * (1.0 / diag)
        rz_new = float(np.sum(res * z))
        pdir = z + (rz_new / rz) * pdir; rz = rz_new
    Vt = np.where(free, u, Vb)
    # C = 2 W / V^2 with W = 1/2 eps0 sum over faces (dV)^2 (face area / spacing), per mm of radius
    ex = np.roll(Vt, -1, 0) - Vt; ez = np.roll(Vt, -1, 1) - Vt
    W2 = np.sum(ex * ex) * (hz / hx) + np.sum(ez * ez) * (hx / hz)
    er = PS.eps_r(p)
    return EPS0_MM * er * W2 / 2.0, it        # two gaps per z period -> per gap


def tube_caps(p):
    """C_max, C_min (pF) per varicap per side, and the per-gap values."""
    n_gap = 2 * int(p["n_plates"]) - 1
    rs = np.linspace(p["r_inMm"], p["r_outMm"], int(p["n_r"]))
    period_deg = 360.0 / (p["N_sec"] / 2.0)
    cmx, cmn = [], []
    for r in rs:
        cmx.append(_cell(r, p, 0.0)[0]); cmn.append(_cell(r, p, 0.5 * period_deg)[0])
    n_per = p["N_sec"] / 2.0                                         # sector periods around the ring
    integ = lambda y: n_per * float(np.sum(0.5 * (np.array(y[1:]) + np.array(y[:-1])) * np.diff(rs))) * 1e12   # pF per gap (trapezoid; numpy 1 and 2)
    gmax, gmin = integ(cmx), integ(cmn)
    return dict(n_gap=n_gap, per_gap_max_pF=gmax, per_gap_min_pF=gmin, C_max=n_gap * gmax,
                C_min=n_gap * gmin + p["C_edge_pF"], radii=list(map(float, rs)),
                c_max_pF_per_mm=[c * 1e12 for c in cmx], c_min_pF_per_mm=[c * 1e12 for c in cmn])


def tube_geometry(p, lad, rpm):
    """axial lengths, vane masses, inertia and stored energy (rotor body: both sides' rotor vanes)."""
    n = int(p["n_plates"]); t, g = p["t_vaneMm"], p["g_vMm"]
    L_var = 2 * n * t + (2 * n - 1) * g                           # one varicap stack (C1 or C2)
    cpg = lad["per_gap_max_pF"]                                    # pF per working gap (same vanes for Cx)
    n_cx = math.ceil(lad["cx_max"] / cpg) if cpg > 0 else 0       # Cx working gaps per side
    L_cx = (n_cx + 1) * t + n_cx * g
    A_full = math.pi * (p["r_outMm"] ** 2 - p["r_inMm"] ** 2)      # fixed plates: full annulus, air [IR]
    c_fixed_gap = EPS0_MM * PS.eps_r(p) * A_full / g * 1e12
    n_ca = math.ceil(lad["Ca"] / c_fixed_gap)
    L_ca = n_ca * p["pitch_fixed_mm"]
    side = L_var + L_cx + L_ca + p["clock_mm"] + p["rel_mm"]
    L_tot = 2 * side + p["hub_mm"]
    frac_r = (p["N_sec"] / 2) * p["wr_deg"] / 360.0
    A_rv = frac_r * A_full * 1e-6                                  # m^2 per rotor vane
    m_vane = A_rv * t * 1e-3 * p["rho_vane"]
    n_rv = 2 * (n + math.ceil(n_cx / 2))                           # rotor vanes, both sides (C1/C2 + Cx)
    m_rot = n_rv * m_vane
    I_rot = m_rot * 0.5 * ((p["r_inMm"] * 1e-3) ** 2 + (p["r_outMm"] * 1e-3) ** 2)
    w = 2 * math.pi * rpm / 60.0
    return dict(L_varicap_mm=L_var, n_gap_cx=n_cx, L_cx_mm=L_cx, n_gap_ca=n_ca, L_ca_mm=L_ca, L_side_mm=side,
                L_total_mm=L_tot, diameter_mm=2 * p["r_outMm"], n_rotor_vanes=n_rv, m_rotor_vanes_kg=m_rot,
                I_rotor_vanes_kgm2=I_rot, E_rot_J=0.5 * I_rot * w * w, rim_mps=w * p["r_outMm"] * 1e-3)


# ---------------------------------------------------------------------------------------------------------
# the ladder for either geometry (same dict shape as pump_sizing.size, so pump_synth.engine_cfg takes it)
# ---------------------------------------------------------------------------------------------------------
def size_stack(geometry="disc", plates=None, choices=None):
    if geometry == "disc":
        lad = PS.size(plates, choices)
        lad["geometry"] = "disc"
        return lad
    if geometry != "tube":
        raise ValueError(geometry)
    p = dict(TUBE_DEFAULTS); p.update(plates or {})
    tc = tube_caps(p)
    c = dict(PS.CHOICE_DEFAULTS); c.update(choices or {})
    # reuse pump_sizing's ladder rules by giving it the tube's C_max / C_min through pins
    pins = dict(c.get("pins") or {})
    pins.setdefault("C_max", tc["C_max"]); pins.setdefault("C_min", tc["C_min"])
    cmax = pins["C_max"]
    for k, ratio in (("Ca", c["ratio_Ca"]), ("Cb", c["ratio_Ca"]), ("cx_max", c["ratio_Cx"])):
        pins.setdefault(k, ratio * cmax)
    if c["cpar_mode"] == "scaled":                 # D-CPAR scaled: strays follow the TUBE's C_max (not the disc law)
        sc = cmax / PS.C_FREEZE_PF
        for k, base in (("Cpar", c["Cpar_pF"]), ("gap_stray", c["gap_stray_pF"]), ("pCboss", c["pCboss_pF"]),
                        ("island_stray", c["island_stray_pF"]), ("cx_min", c["cx_min_pF"])):
            pins.setdefault(k, base * sc)
        c["cpar_mode"] = "fixed"
    c["pins"] = pins
    pd = dict(PS.PLATE_DEFAULTS, r_inMm=p["r_inMm"], r_outMm=p["r_outMm"], g_vMm=p["g_vMm"], dielectric=p["dielectric"],
              tempC=p["tempC"], p_hPa=p["p_hPa"], rh=p["rh"], N_sec=p["N_sec"])
    lad = PS.size(pd, c)
    for k in ("C_max", "C_min"):
        lad["ladder"][k]["rule"] = ("2-D vane cell, aligned, x (2 n - 1) gaps" if k == "C_max" else
                                    "2-D vane cell, opposed (zero overlap) x (2 n - 1) gaps + edge floor")
        lad["ladder"][k]["tag"] = "[ME] 2-D cell; [IR] edge floor"
        lad["ladder"][k]["pinned"] = k in (choices or {}).get("pins", {})
    user_pins = (choices or {}).get("pins", {})
    for k in ("Ca", "Cb", "cx_max", "Cpar", "gap_stray", "pCboss", "island_stray", "cx_min"):
        lad["ladder"][k]["pinned"] = k in user_pins
    lad["cpar_mode"] = (choices or {}).get("cpar_mode", "fixed")
    L = lad["ladder"]
    lad.update(geometry="tube", tube=p, tube_caps=tc,
               kappa_C=L["C_max"]["value"] / L["C_min"]["value"] if L["C_min"]["value"] > 0 else None)
    lad["tube_geometry"] = tube_geometry(p, dict(per_gap_max_pF=tc["per_gap_max_pF"], cx_max=L["cx_max"]["value"],
                                                 Ca=L["Ca"]["value"]), c["rpm"])
    lad["rotor_dia_mm"] = 2 * p["r_outMm"]; lad["rim_mps"] = lad["tube_geometry"]["rim_mps"]
    return lad


# ---------------------------------------------------------------------------------------------------------
# z under the record or the v4 topology
# ---------------------------------------------------------------------------------------------------------
def z_stack(lad, firing=None, topology="record", v4=None, log=None):
    import pump_synth as SY
    import rt_engine as RT
    import pump_engine as PE
    fi = dict(SY.FIRING_DEFAULTS) if hasattr(SY, "FIRING_DEFAULTS") else SY.split({})[2]
    fi.update(firing or {})
    cfg = SY.engine_cfg(lad, fi)
    if topology == "record":
        z, conv = SY.z_of(cfg)
        return dict(z=z, converged=bool(conv), topology="record")
    if topology != "v4":
        raise ValueError(topology)
    q = dict(V4_DEFAULTS); q.update(v4 or {})
    net = RT.build_net(cfg, tank="series", C_R1_pF=q["C_tank_pF"])
    Lt = q["L_tank_uH"] * 1e-6
    Rt = (1 / math.sqrt(Lt * q["C_tank_pF"] * 1e-12)) * Lt / q["Q_tank"]
    net.inds.append(("L_tank_chain", net.n("R-B"), PE.GND, Lt, Rt, "lx"))           # R-A = reference
    n = q["n_coils"]
    for gname, node, mid in (("SG1", "2", "mA"), ("SG2", "3", "mB")):
        k = [i for i, g in enumerate(net.gaps) if g[0] == gname][0]
        g = list(net.gaps[k]); ni, nm = net.n(node), net.n(mid)
        j = 1 if g[1] == ni else 2
        g[j] = nm; net.gaps[k] = tuple(g)
        net.inds.append((f"L_{mid}", ni, nm, q["L_coil_H"] / n, q["R_coil"] / n, "lx"))
        net.caps.append((f"Cmid_{mid}", nm, PE.GND, n * q["C_mid_pF"] * 1e-12))
        net.caps.append((f"Cscreen_{mid}", nm, ni, n * q["C_screen_pF"] * 1e-12))
    m = RT.run(net, cfg, log=log)
    return dict(z=m["z"], converged=bool(m["converged"]), topology="v4")


def evaluate(geometry="disc", plates=None, choices=None, firing=None, topology="record", v4=None, log=None):
    lad = size_stack(geometry, plates, choices)
    r = z_stack(lad, firing, topology, v4, log)
    return json.loads(json.dumps(dict(ladder=lad, result=r), default=float))


# ---------------------------------------------------------------------------------------------------------
# self-test (on load): the 2-D cell against the parallel-plate limit; disc mode = pump_sizing
# ---------------------------------------------------------------------------------------------------------
def _selftest():
    ok = True
    # wide vanes, full overlap, small gap: C per gap per mm -> eps0 er w / g within 2 %
    p = dict(TUBE_DEFAULTS, ws_deg=59.0, wr_deg=59.0, g_vMm=1.0, t_vaneMm=1.0, dielectric="vacuum", h_mm=0.25)
    c, _ = _cell(160.0, p, 0.0)
    w = math.radians(59.0) * 160.0
    pp = EPS0_MM * w / 1.0
    ok &= 0.995 < c / pp < 1.06                            # parallel plate + a little edge fringe
    # opposed with zero overlap is far below aligned
    p2 = dict(TUBE_DEFAULTS, dielectric="vacuum")
    cmx, _ = _cell(160.0, p2, 0.0); cmn, _ = _cell(160.0, p2, 30.0)
    ok &= cmx / cmn > 10.0
    # disc mode is pump_sizing verbatim
    ok &= abs(size_stack("disc")["ladder"]["C_max"]["value"] - PS.size()["ladder"]["C_max"]["value"]) < 1e-12
    if not ok:
        raise AssertionError("stack_sizing on-load self-test FAILED")
    return True


SELFTEST_OK = _selftest()

if __name__ == "__main__":
    import sys
    lad = size_stack("tube")
    print(json.dumps(dict(tube_caps={k: v for k, v in lad["tube_caps"].items() if not isinstance(v, list)},
                          kappa=lad["kappa_C"], geometry=lad["tube_geometry"],
                          ladder={k: round(v["value"], 2) for k, v in lad["ladder"].items()}), indent=1))
