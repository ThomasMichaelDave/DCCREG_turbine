"""rebuild/s2_models/s2_structure.py -- the structural integrity of the S2a model (the designer, 2026-10-16: "fill in the
missing structural components and check the structural and electrostatic integrity").

Read from the model itself (rebuild/s2_models/s2_geometry.py S2Core: every solid's volume and centroid by OpenCascade,
each material's density [IR: datasheet-class]):
  1. the masses: the rotor, the counter-rotor, the retainer;
  2. the spin stresses at 1.25 x the 600 rpm (750 rpm) [IR: the overspeed factor]:
     - the Ca / Cb plates and the vanes' rings as rotating annuli (Timoshenko's free annulus, the hoop stress at the
       bore) [OC];
     - the vanes' sectors as radial cantilevers in centrifugal tension at their root [OC];
     - the G10 cage, the spiders, the coupling tubes as thin rings [OC];
     - the stator vanes' lugs on the tie rods: each rod a beam between its spacers under the lugs' pull [IR];
  3. the bearings' loads: the axis vertical [IR], the rotating masses' weight on the lower frame bearing; the
     out-of-balance force at ISO 1940 G2.5 [IR];
  4. the rotor's bending modes: an Euler-Bernoulli beam (Hermite elements) between the frame bearings (pinned, with
     the cross beams' stiffness as springs), its sections from the model (shaft and sleeve, the hub's coupler and
     retainer, the couplings, the stubs), every rotor solid's mass lumped at its z, the counter-rotor's mass at the
     REF-link bearings [IR]; against 10 Hz (the shaft), 20 Hz (the relative rotation) and 120 Hz (the pump);
  5. the electrostatic pull on the plates at the varicap's peak (13.8 kV across 6 mm) and the plates' first axial
     mode against 120 Hz: an annular plate clamped at its supports, free outside (Rayleigh-Ritz) [IR], and the
     sectors as tapered cantilevers [IR].
Writes rebuild/s2_models/s2_structure_results.json.
Usage: python3 rebuild/s2_models/s2_structure.py
"""
import json
import math
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "sim"))
sys.path.insert(0, HERE)
import s2_geometry as G  # noqa: E402

RPM = 600.0
OVERSPEED = 1.25
OM = 2 * math.pi * RPM / 60.0
OM_O = OM * OVERSPEED
EPS0 = 8.854e-12
# density kg/m3, E GPa, strength MPa (yield, or flexural for G10 / ceramic), Poisson [IR: datasheet-class]
MAT = [("PTFE", 2200, 0.5, 10, 0.46), ("silicone", 1150, 0.005, 5, 0.49), ("mica", 2800, 170, 100, 0.25),
       ("steatite", 2700, 100, 120, 0.25), ("G10", 1850, 18, 300, 0.12), ("glass-epoxy", 1850, 18, 300, 0.12),
       ("PEEK", 1300, 3.6, 95, 0.4), ("borosilicate", 2230, 64, 40, 0.2), ("brass", 8500, 100, 200, 0.34),
       ("Cu", 8960, 117, 70, 0.34), ("stainless", 7900, 193, 205, 0.29), ("steel", 7900, 193, 205, 0.29),
       ("bearing", 7900, 200, 1000, 0.3), ("6063", 2700, 69, 170, 0.33), ("T-slot", 2700, 69, 170, 0.33),
       ("Al", 2700, 69, 160, 0.33), ("HV rectifier", 2500, 50, 50, 0.3), ("33 x", 2500, 50, 50, 0.3),
       ("clamp", 2500, 50, 50, 0.3), ("gel", 1100, 0.001, 1, 0.49)]


def material(text):
    for key, rho, E, sig, nu in MAT:
        if key.lower() in text.lower():
            return dict(key=key, rho=rho, E=E * 1e9, sigma=sig * 1e6, nu=nu)
    return dict(key="?", rho=1800, E=10e9, sigma=50e6, nu=0.3)


def solids(m):
    from OCP.GProp import GProp_GProps
    from OCP.BRepGProp import BRepGProp
    rows = []
    for pt in m.parts:
        shp = m.placed(pt)
        gp = GProp_GProps()
        BRepGProp.VolumeProperties_s(shp, gp)
        c = gp.CentreOfMass()
        mat = material(m.protos[pt["proto"]][2])
        v = gp.Mass() * 1e-9                                            # m3
        import tube_geometry as TG
        lo, hi = TG.bbox(shp)
        rows.append(dict(name=pt["name"], body=pt["body"], group=pt["group"], mat=mat["key"], V_m3=v,
                         m_kg=v * mat["rho"], z_mm=c.Z(), z0_mm=float(lo[2]), z1_mm=float(hi[2]),
                         r_mm=math.hypot(c.X(), c.Y())))
    return rows


def ring_hoop(rho, om, ri, ro, nu):
    """the free rotating annulus: the hoop stress at the bore (the largest) [OC: Timoshenko]."""
    return (3 + nu) / 4.0 * rho * om ** 2 * (ro ** 2 + (1 - nu) / (3 + nu) * ri ** 2)


def sector_root(rho, om, r0, r1):
    """a radial bar of uniform section from r0 to r1, its root stress from its own spin [OC]: rho om^2 (r1^2 - r0^2)/2;
    a sector widening outward carries more, by the area ratio at its tip over its root [IR: bounded by r1 / r0]."""
    return rho * om ** 2 * (r1 ** 2 - r0 ** 2) / 2.0 * (r1 / r0)


def beam_modes(m, rows, n_el=120):
    """the rotor's lateral modes between the frame bearings."""
    zA, zB = m.zz("A", m.h_fb + 0.5 * G.FB["width"]), m.zz("B", m.h_fb + 0.5 * G.FB["width"])
    z = np.linspace(zA, zB, n_el + 1)
    zc = m.zc

    def EI(zm):
        h = abs(zm - zc)
        I = lambda ro, ri=0.0: math.pi / 4 * (ro ** 4 - ri ** 4)                                     # noqa: E731
        mm = 1e-3
        if h <= G.FL_Z0:                                                    # the hub: the coupler and the retainer
            return 18e9 * I(33 * mm, 30 * mm) + 3.6e9 * I(30 * mm, 25.5 * mm)
        if h <= G.FL_Z1:                                                    # the flanges in the coupler
            return 193e9 * I(30 * mm) + 18e9 * I(33 * mm, 30 * mm)
        if h <= m.h_c0:                                                     # the shaft in its sleeve and cover
            return 193e9 * I(12.5 * mm) + 18e9 * I(20.5 * mm, 12.5 * mm)
        if h <= m.h_end:                                                    # the coupling over the shaft
            return 193e9 * I(12.5 * mm) + 18e9 * I(17 * mm, 12.5 * mm)
        if h <= m.h_stub0:                                                  # the coupling's G10 plug: the weak link
            return 18e9 * I(17 * mm)
        if h <= m.h_c1:
            return 193e9 * I(12.5 * mm) + 18e9 * I(17 * mm, 12.5 * mm)
        return 193e9 * I(12.5 * mm)
    ndof = 2 * (n_el + 1)
    K = np.zeros((ndof, ndof))
    M = np.zeros((ndof, ndof))
    for e in range(n_el):
        L = (z[e + 1] - z[e]) * 1e-3
        ei = EI(0.5 * (z[e] + z[e + 1]))
        k = ei / L ** 3 * np.array([[12, 6 * L, -12, 6 * L], [6 * L, 4 * L * L, -6 * L, 2 * L * L],
                                    [-12, -6 * L, 12, -6 * L], [6 * L, 2 * L * L, -6 * L, 4 * L * L]])
        idx = [2 * e, 2 * e + 1, 2 * e + 2, 2 * e + 3]
        K[np.ix_(idx, idx)] += k
    # the masses: every rotor solid at its node; the counter-rotor (stator) at the REF-link bearings [IR]
    m_rot, m_sta = 0.0, 0.0
    for r in rows:
        if r["body"] in ("rotor", "bearing"):
            # spread over the solid's own length [IR]
            idx = [i for i in range(n_el + 1) if r["z0_mm"] - 1e-6 <= z[i] <= r["z1_mm"] + 1e-6] or                 [int(np.argmin(abs(z - r["z_mm"])))]
            for i in idx:
                M[2 * i, 2 * i] += r["m_kg"] / len(idx)
            m_rot += r["m_kg"]
        elif r["body"] == "stator":
            m_sta += r["m_kg"]
    for s_ in "AB":
        zb = m.zz(s_, m.h_brg0 + 0.5 * G.BEARING["width"])
        i = int(np.argmin(abs(z - zb)))
        M[2 * i, 2 * i] += 0.5 * m_sta
    for i in range(n_el + 1):                                               # a little rotary inertia keeps M regular
        M[2 * i + 1, 2 * i + 1] += 1e-7
        M[2 * i, 2 * i] += 1e-6
    # the supports: the frame bearings on the cross beams [IR: two 40 x 40 beams, simply supported over their span]
    span = 2 * (m.frame_a - G.PROFILE) * 1e-3
    I_p = 7.0e-8                                                            # m4, a 40 x 40 B-type profile [RH]
    k_frame = 2 * 48 * 69e9 * I_p / span ** 3
    K[0, 0] += k_frame
    K[-2, -2] += k_frame
    from scipy.linalg import eigh
    w2, vec = eigh(K, M)
    f = np.sqrt(np.clip(w2, 0, None)) / (2 * math.pi)
    modes = [float(x) for x in f if x > 0.5][:4]
    return dict(f_Hz=modes, m_rotor_kg=m_rot, m_counter_rotor_kg=m_sta, k_frame_N_per_m=k_frame,
                span_mm=float(zB - zA), weak_link="the couplings' G10 plugs (Ø25 G10, E 18 GPa)",
                note="pinned at the frame bearings on the cross beams' stiffness; the counter-rotor's mass at the "
                     "REF-link bearings; no gyroscopic stiffening (conservative for the forward modes) [IR]")


def plate_mode(E, nu, rho, t, a, b, clamped="inner"):
    """the first axisymmetric mode of an annular plate, clamped on one edge and free on the other, by Rayleigh-Ritz
    with w = (r - r_c)^2 (1 + c (r - r_c)) [IR]; a = outer, b = inner radius (m)."""
    D = E * t ** 3 / (12 * (1 - nu ** 2))
    r = np.linspace(b, a, 400)
    rc = b if clamped == "inner" else a
    best = None
    for c in np.linspace(-30.0, 30.0, 121):
        x = (r - rc)
        w = x ** 2 * (1 + c * x)
        w1 = np.gradient(w, r)
        w2 = np.gradient(w1, r)
        U = np.trapezoid((w2 + w1 / r) ** 2 - 2 * (1 - nu) * w2 * w1 / r, r * 2 * math.pi * r / r) if False else \
            np.trapezoid(((w2 + w1 / r) ** 2 - 2 * (1 - nu) * w2 * w1 / r) * r, r)
        T = np.trapezoid(w ** 2 * r, r)
        om2 = D * U / (rho * t * T)
        if om2 > 0 and (best is None or om2 < best):
            best = om2
    return math.sqrt(best) / (2 * math.pi)


def cantilever_mode(E, rho, t, L, taper=1.0):
    """a cantilever of thickness t, length L: 1.875^2 / (2 pi L^2) sqrt(E t^2 / 12 rho); a width growing toward the tip
    lowers it, taken by the tip / root width ratio's square root [IR]."""
    return 1.875 ** 2 / (2 * math.pi * L ** 2) * math.sqrt(E * t ** 2 / (12 * rho)) / math.sqrt(taper)


def main():
    m = G.S2Core().build()
    rows = solids(m)
    by_body = {}
    for r in rows:
        by_body[r["body"]] = by_body.get(r["body"], 0.0) + r["m_kg"]
    out = dict(rpm=RPM, overspeed=OVERSPEED, masses_kg=by_body)
    print("masses kg:", {k: round(v, 2) for k, v in by_body.items()})
    # 2. spin stresses at 750 rpm
    al = material("Al")
    t = G.VANE["t"] * 1e-3
    ri, ro = G.VANE["r_in"] * 1e-3, G.VANE["r_out"] * 1e-3
    st = {}
    st["Ca plate (Al annulus r 50-150)"] = ring_hoop(al["rho"], OM_O, ri, ro, al["nu"])
    st["rotor vane ring (r 22.5-50)"] = ring_hoop(al["rho"], OM_O, G.SLEEVE_OUT * 1e-3, ri, al["nu"])
    st["rotor vane sector root (r 50-150)"] = sector_root(al["rho"], OM_O, ri, ro)
    st["stator vane ring with lugs (r 150-190)"] = ring_hoop(al["rho"], OM_O, ro, G.LUG["r1"] * 1e-3, al["nu"])
    st["stator vane sector (r 150 inward to 50): compression at its root, taken as tension's size"] = \
        sector_root(al["rho"], OM_O, ri, ro)
    g10 = material("G10")
    st["G10 cage (r 192-196)"] = g10["rho"] * OM_O ** 2 * (G.CAGE[1] * 1e-3) ** 2
    st["Al spider (r 26-192)"] = ring_hoop(al["rho"], OM_O, 0.026, G.CAGE[0] * 1e-3, al["nu"])
    st["G10 coupling (r 12.5-17)"] = g10["rho"] * OM_O ** 2 * 0.017 ** 2
    # the tie rods: the lugs' pull spread over the rod between spacers (the spacers butt the lugs: the rod is a pin in
    # shear) [IR]; a lug 20 x 28 x 3 mm at r 176
    lug_m = 2700 * 0.020 * 0.028 * 0.003
    F_lug = lug_m * OM_O ** 2 * 0.176
    tau = F_lug / (math.pi / 4 * (G.TIE["d"] * 1e-3) ** 2)
    st["a tie rod's shear under one lug's pull"] = tau
    lim = {"Ca plate (Al annulus r 50-150)": al["sigma"], "rotor vane ring (r 22.5-50)": al["sigma"],
           "rotor vane sector root (r 50-150)": al["sigma"], "stator vane ring with lugs (r 150-190)": al["sigma"],
           "stator vane sector (r 150 inward to 50): compression at its root, taken as tension's size": al["sigma"],
           "G10 cage (r 192-196)": g10["sigma"], "Al spider (r 26-192)": al["sigma"], "G10 coupling (r 12.5-17)": g10["sigma"],
           "a tie rod's shear under one lug's pull": 0.58 * 205e6}
    out["spin_stress_750rpm"] = {k: dict(MPa=v / 1e6, limit_MPa=lim[k] / 1e6, safety=lim[k] / v) for k, v in st.items()}
    for k, v in out["spin_stress_750rpm"].items():
        print(f"   {k}: {v['MPa']:.3f} MPa, safety {v['safety']:.0f}")
    # 3. the bearings
    m_rot = sum(r["m_kg"] for r in rows if r["body"] in ("rotor", "bearing"))
    m_sta = sum(r["m_kg"] for r in rows if r["body"] == "stator")
    e_perm = 2.5e-3 / OM                                                    # m: G2.5 is 2.5 mm/s [IR]
    F_imb = (m_rot + m_sta) * e_perm * OM ** 2
    out["bearings"] = dict(axial_on_lower_frame_bearing_N=(m_rot + m_sta) * 9.81, radial_imbalance_N=F_imb,
                           ref_link_axial_N=m_sta * 9.81,
                           rating="6205 class: C 14.8 kN, C0 7.8 kN [IR: catalogue class]",
                           note="the axis vertical; the counter-rotor rides on the REF-link bearings, the whole on the "
                                "lower frame bearing")
    print("bearings:", {k: (round(v, 1) if isinstance(v, float) else v) for k, v in out["bearings"].items()})
    # 4. the rotor's modes
    bm = beam_modes(m, rows)
    out["rotor_modes"] = bm
    print("rotor lateral modes Hz:", [round(x, 1) for x in bm["f_Hz"]], f"(rotor {bm['m_rotor_kg']:.1f} kg, counter-rotor "
                                                                        f"{bm['m_counter_rotor_kg']:.1f} kg)")
    # 5. the electrostatic pull and the plates' modes
    V_pk, g = 13.8e3, G.VANE["g"] * 1e-3
    p = 0.5 * EPS0 * (V_pk / g) ** 2
    A = math.pi * (ro ** 2 - ri ** 2)
    f_ca_clamped = plate_mode(al["E"], al["nu"], al["rho"], t, ro, ri, "inner")
    f_rotor_sector = cantilever_mode(al["E"], al["rho"], t, ro - ri, taper=ro / ri)
    f_stator_sector = cantilever_mode(al["E"], al["rho"], t, ro - ri, taper=ri / ro)
    out["electrostatic"] = dict(pressure_Pa=p, force_per_plate_N=p * A, at="13.8 kV across 6 mm, twice a cycle (120 Hz)",
                                ca_plate_first_axial_Hz_if_clamped_round_its_bore=f_ca_clamped,
                                ca_plate_note="it is held by three tabs, not clamped all round: its first mode lies below "
                                              "this bound [IR]",
                                rotor_sector_first_Hz=f_rotor_sector, stator_sector_first_Hz=f_stator_sector,
                                hand_estimates_note="the hand estimates above are superseded by the modal FE "
                                                    "(rebuild/s2_models/s2_modes_results.json)")
    try:
        cb = json.load(open(os.path.join(HERE, "s2_modes_results.json")))["campbell"]["after"]
        out["electrostatic"]["fe_pull_excited_Hz"] = dict(cb["modes"])
        out["electrostatic"]["fe_windows_rpm"], out["electrostatic"]["fe_600_clear"] = cb["windows_rpm"], cb["at_600"]
    except (OSError, KeyError):
        pass
    print("electrostatic:", {k: (round(v, 2) if isinstance(v, float) else v) for k, v in out["electrostatic"].items()})
    json.dump(out, open(os.path.join(HERE, "s2_structure_results.json"), "w"), indent=1, default=float)


if __name__ == "__main__":
    main()
