"""sim/hub_thermal.py -- the hub's temperature, and the vessel's conductivity at it (ledger §5.2 "the vessel's
resistivity"; the condition sim/hub_beads_settled.py sets on the glass's conductivity over the gel's).

1. **The AH coils as wound** [IR]: 160 turns in the record's window (r 8.25-11.45 mm, |z| 31.35-71.35 mm: 3.2 x 40 mm,
   presets/hub-locked.json AH) take the largest IEC 60317 grade-1 enamelled round wire that fits orthocyclically
   (layers d_o * sqrt(3) / 2 apart). Its resistance from the mean turn (Cu 1.724e-8 ohm m at 20 C) stands against the
   deck's 0.27 ohm (sim/magnetic_doubler.py AH r160, "R ~ N^2 in the same window": a window full of bare copper). The
   pump's deck re-run with that R (the pick as sim/rotor_parts_duty.py runs it, the 22 mF bypass as
   sim/ah_steady_cusp.py adds it) gives the coils' current, without and with the bypass.
2. **The heat:** I_rms^2 R per coil at the coil's temperature (Cu +0.393 %/K) [OC]. The MnZn rods' loss at 0.12 T DC
   with the bypassed 120 Hz ripple, and the rings' leakage (pA), are negligible [RH].
3. **The conduction** [OC law; IR materials, datasheet-class]: axisymmetric finite volumes on the hub's half z >= 0,
   0.25 mm cells; the midplane adiabatic (the two coils alike). The vessel and its vacuum (radiation across it as an
   effective conductivity, 4 sigma_SB T^3 D / (2 / emissivity - 1) [RH]); the gel; the PEEK retainer; the G10 coupler
   and formers; the MnZn rods; the coils (an impregnated winding's effective conductivity [IR]); the potting between a
   rod and its former and at the coil's ends; the stainless flanges and shaft. The AH bonded into its bore and its rod
   onto the flange [IR]. Convection off the coupler, the flanges and the shaft at h: a cylinder turning at 600 rpm in
   the stirred air between the vane stacks, about 20 W/m^2 K [RH]; the shaft beyond |z| 110 mm an infinite fin.
4. **The vessel's conductivity** [IR]: Arrhenius through the record's two points (1e-13 S/m at 25 C, 5.4e-13 at 40 C:
   sim/hub_drift.py SIG; 0.90 eV) at the glass's temperatures, against the gel's 1e-13 S/m. The gel's own temperature
   dependence is not in the records; it is held [RH].
The air between the vane stacks is taken at the room's temperature plus DT_AIR [RH]; every rise is also given above
it. Writes sim/hub_thermal_results.json.
Usage: python3 sim/hub_thermal.py
"""
import json
import math
import os
import subprocess
import sys
import tempfile
import time
from multiprocessing import Pool

import numpy as np
import scipy.sparse as sp
import scipy.sparse.linalg as spla

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import ah_steady_cusp as SC        # noqa: E402
import hub_drift as D              # noqa: E402
import hub_locked as HL            # noqa: E402
import magnetic_doubler as M       # noqa: E402
import rotor_parts_duty as RP      # noqa: E402

RHO_CU20, ALPHA_CU = 1.724e-8, 0.00393         # ohm m at 20 C, 1/K [OC]
# IEC 60317-0-1 grade 1: nominal bare diameter -> maximum overall diameter (mm) [IR datasheet-class]
WIRES = ((0.71, 0.775), (0.75, 0.817), (0.80, 0.869), (0.85, 0.922), (0.90, 0.976), (0.95, 1.028), (1.00, 1.080))
N_TURNS = HL.V("AH")["coil"]["turns"]
COIL_R = tuple(HL.V("AH")["coil"]["r_mm"])     # (8.25, 11.45)
COIL_Z = tuple(HL.V("AH")["coil"]["absz_mm"])  # (31.35, 71.35)
CORE_R = 0.5 * HL.V("AH")["core"]["d_mm"]      # 6.15
FORMER_R = (0.5 * HL.V("AH")["former"]["id_mm"], 0.5 * HL.V("AH")["former"]["od_mm"])   # (6.75, 8.25)
K = dict(vac=None, glass=1.15, gel=0.20, peek=0.25, g10=0.30, mnzn=4.0, coil=1.0, pot=0.20, steel=16.0)   # W/m K [IR]
H_CONV = (10.0, 20.0, 40.0)        # W/m^2 K: the hub's surfaces [RH]; 20 the base
K_COIL = (0.5, 1.0, 2.0)           # W/m K: the winding's effective conductivity, the sensitivity
T_ROOM, DT_AIR = 25.0, 5.0         # C: the room, and the air between the vane stacks above it [RH]
EMISS = 0.9                        # the glass's inner surface, in the infrared [IR]
H, R_DOM, Z_DOM = 0.25, 34.0, 110.0    # mm
EA_EV = None                       # set from the two points below
BEAD_LIMIT = os.path.join(HERE, "hub_beads_settled_results.json")


# ----------------------------------------------------------------------------------- 1. the coil as wound
def winding():
    """the largest grade-1 wire that winds N_TURNS orthocyclically in the window, its layers and resistance."""
    build, length = COIL_R[1] - COIL_R[0], COIL_Z[1] - COIL_Z[0]
    best = None
    for dn, do in WIRES:
        per = int(length // do)
        layers = math.ceil(N_TURNS / per)
        radial = do + (layers - 1) * do * math.sqrt(3) / 2
        if radial <= build + 1e-9:
            radii = [COIL_R[0] + do / 2 + k * do * math.sqrt(3) / 2 for k in range(layers)]
            turns = [per] * (layers - 1) + [N_TURNS - per * (layers - 1)]
            mean_r = sum(r * n for r, n in zip(radii, turns)) / N_TURNS
            wire_m = N_TURNS * 2 * math.pi * mean_r * 1e-3
            r20 = RHO_CU20 * wire_m / (math.pi / 4 * (dn * 1e-3) ** 2)
            best = dict(d_bare_mm=dn, d_overall_mm=do, per_layer=per, layers=layers, radial_build_mm=radial,
                        mean_turn_r_mm=mean_r, wire_m=wire_m, R20_ohm=r20)
    return best


def deck_current(args):
    """the pick's AH coil current (rms and mean, both coils) for a coil resistance R and a bypass C (mF)."""
    r_ohm, c_mf = args
    kw = RP._kw(RP.TAU_FIXED)
    kw["ah_custom"] = dict(kw["ah_custom"], R=r_ohm)
    txt, vecs, info = M.deck(**kw)
    if c_mf:
        byp = [f"R_bypA x1 xb1 {SC.ESR:g}", f"C_bypA xb1 d {c_mf * 1e-3:g}",
               f"R_bypB x2 xb2 {SC.ESR:g}", f"C_bypB xb2 b {c_mf * 1e-3:g}"]
        txt = txt.replace("D1s f2 b ND", "\n".join(byp) + "\nD1s f2 b ND")
    ex = ["v(ps_AHt)", "v(ps_AHb)"]
    txt = txt.replace("wrdata out.dat " + " ".join(vecs), "wrdata out.dat " + " ".join(vecs + ex))
    with tempfile.TemporaryDirectory() as d:
        open(os.path.join(d, "x.cir"), "w").write(txt)
        subprocess.run(["ngspice", "-b", "x.cir"], capture_output=True, text=True, timeout=3600, cwd=d)
        raw = np.loadtxt(os.path.join(d, "out.dat"))
    t = raw[:, 0]
    c = {v: raw[:, 2 * j + 1] for j, v in enumerate(vecs + ex)}
    s = t >= (kw["n_cyc"] - 4) / kw["F"]
    out = dict(R_ohm=r_ohm, C_byp_mF=c_mf)
    for el in ("AHt", "AHb"):
        i = c[f"v(ps_{el})"][s] / kw["ah_custom"]["L"]
        ts = t[s]
        rms = math.sqrt(float(np.sum(0.5 * (i[1:] ** 2 + i[:-1] ** 2) * np.diff(ts)) / (ts[-1] - ts[0])))
        out[el] = dict(I_mean_A=float(abs(i.mean())), I_rms_A=rms, AT_mean=float(abs(i.mean()) * kw["ah_custom"]["N"]))
    return out


# ----------------------------------------------------------------------------------- 3. the conduction
def maps(k_coil, h=None):
    """the thermal conductivity of each cell (W/m K; 0 the air) and the coil's cells."""
    hub = HL.HUB
    h = h or H
    nr, nz = int(round(R_DOM / h)), int(round(Z_DOM / h))
    r = (np.arange(nr) + 0.5) * h
    z = (np.arange(nz) + 0.5) * h
    R, Z = np.meshgrid(r, z, indexing="ij")
    rho = np.hypot(R, Z)
    k = np.zeros((nr, nz))
    ret_r, ret_z = HL.V("retainer")["r_max_mm"], HL.V("retainer")["absz_max_mm"]   # 30, 72
    cpl_t = HL.V("shaft_coupler")["wall_mm"]
    inside = (R <= ret_r + cpl_t) & (Z <= ret_z)
    k[inside] = K["peek"]
    k[inside & (R > ret_r)] = K["g10"]
    k[inside & (rho < hub["R_v"] + HL.V("interface_filler")["t_mm"])] = K["gel"]
    k[(rho >= hub["R_in"]) & (rho < hub["R_v"])] = K["glass"]
    t_rad = 0.5 * (T_ROOM + DT_AIR + 10.0) + 273.15                                  # about the glass's own
    k_vac = 4 * 5.670374e-8 * t_rad ** 3 * (2 * hub["R_in"] * 1e-3) / (2 / EMISS - 1)
    k[rho < hub["R_in"]] = k_vac
    ah = (Z >= hub["ah_z"][0]) & (Z <= hub["ah_z"][1])
    k[ah & (R <= COIL_R[1])] = K["pot"]                                             # the bore's fill, the coil's ends
    k[ah & (R <= FORMER_R[1]) & (R > FORMER_R[0])] = K["g10"]
    k[ah & (R <= CORE_R)] = K["mnzn"]
    coil = (R > COIL_R[0]) & (R <= COIL_R[1]) & (Z >= COIL_Z[0]) & (Z <= COIL_Z[1])
    k[coil] = k_coil
    fl = (R <= hub["fl_r"]) & (Z >= hub["fl_z"][0]) & (Z <= hub["fl_z"][1])
    k[fl] = K["steel"]
    k[(R <= hub["sh_r"]) & (Z > hub["fl_z"][1])] = K["steel"]
    return r, z, k, coil, dict(k_vac_W_mK=k_vac)


def solve(k, coil, q_coil_W, h_conv, r, h=None):
    """the steady temperature rise over the air (K) for q_coil_W in the coil (half the hub: one coil)."""
    nr, nz = k.shape
    hm = (h or H) * 1e-3
    solid = k > 0
    idx = -np.ones((nr, nz), dtype=np.int64)
    idx[solid] = np.arange(int(solid.sum()))
    n = int(solid.sum())
    diag, rhs = np.zeros(n), np.zeros(n)
    rows, cols, vals = [], [], []
    rf = np.arange(1, nr) * hm                                       # radial faces' radii
    rc = r * 1e-3

    def faces(ka, kb, area):
        """conductances of faces between cells a and b (half a cell each side); air (k 0) as a convective face."""
        with np.errstate(divide="ignore", invalid="ignore"):
            ra = np.where(ka > 0, 0.5 * hm / np.maximum(ka, 1e-30), 1.0 / h_conv)
            rb = np.where(kb > 0, 0.5 * hm / np.maximum(kb, 1e-30), 1.0 / h_conv)
        return area / (ra + rb)
    # radial faces (between i and i+1): area 2 pi r_f h
    A = 2 * math.pi * rf[:, None] * hm * np.ones((1, nz))
    G = faces(k[:-1, :], k[1:, :], A)
    sa, sb = solid[:-1, :], solid[1:, :]
    a, b = idx[:-1, :], idx[1:, :]
    both = sa & sb
    np.add.at(diag, a[sa], G[sa])                                   # a solid: its face, to b or to the air
    np.add.at(diag, b[sb], G[sb])
    rows += [a[both], b[both]]; cols += [b[both], a[both]]; vals += [-G[both], -G[both]]
    # axial faces (between j and j+1): area pi (r_o^2 - r_i^2) = 2 pi r_c h
    A = 2 * math.pi * rc[:, None] * hm * np.ones((1, nz - 1))
    G = faces(k[:, :-1], k[:, 1:], A)
    sa, sb = solid[:, :-1], solid[:, 1:]
    a, b = idx[:, :-1], idx[:, 1:]
    both = sa & sb
    np.add.at(diag, a[sa], G[sa])
    np.add.at(diag, b[sb], G[sb])
    rows += [a[both], b[both]]; cols += [b[both], a[both]]; vals += [-G[both], -G[both]]
    # the outer radial boundary (air beyond R_DOM) and the top (z = Z_DOM): the shaft continues as an infinite fin
    f = solid[-1, :]
    if f.any():
        np.add.at(diag, idx[-1, :][f], 2 * math.pi * R_DOM * 1e-3 * hm / (0.5 * hm / k[-1, :][f] + 1 / h_conv))
    sh = solid[:, -1]
    p_fin = 2 * math.pi * HL.HUB["sh_r"] * 1e-3
    a_fin = math.pi * (HL.HUB["sh_r"] * 1e-3) ** 2
    g_fin = math.sqrt(h_conv * p_fin * K["steel"] * a_fin)                          # W/K, the whole shaft's end
    a_cell = 2 * math.pi * rc * hm
    g_end = 1.0 / (0.5 * hm / (k[:, -1] * a_cell + 1e-30) + 1.0 / (g_fin * a_cell / a_fin))
    np.add.at(diag, idx[:, -1][sh], g_end[sh])
    # the source
    vol = 2 * math.pi * rc[:, None] * hm * hm * np.ones((1, nz))
    qv = q_coil_W / float(vol[coil].sum())
    np.add.at(rhs, idx[coil], qv * vol[coil])
    Amat = sp.csr_matrix((np.concatenate(vals + [diag]), (np.concatenate(rows + [np.arange(n)]),
                                                          np.concatenate(cols + [np.arange(n)]))), shape=(n, n))
    T = np.full((nr, nz), np.nan)
    T[solid] = spla.spsolve(Amat.tocsc(), rhs)
    return T, dict(g_fin_W_K=g_fin, q_W=q_coil_W)


def readouts(T, r, z, coil):
    hub = HL.HUB
    R, Z = np.meshgrid(r, z, indexing="ij")
    rho = np.hypot(R, Z)
    th = np.degrees(np.arctan2(R, Z))
    glass = (rho >= hub["R_in"]) & (rho < hub["R_v"])
    out = dict(coil_max=float(np.nanmax(T[coil])), coil_mean=float(np.nanmean(T[coil])),
               core_tip=float(T[(R <= CORE_R) & (np.abs(Z - hub["ah_z"][0] - 0.5) < 0.3)].mean()),
               glass_max=float(T[glass].max()), glass_mean=float(T[glass].mean()), glass_min=float(T[glass].min()),
               glass_pole=float(T[glass & (th < 5)].mean()), glass_equator=float(T[glass & (th > 85)].mean()),
               glass_band_gap=float(T[glass & (th >= 55.7)].mean()),
               coupler_surface_max=float(np.nanmax(T[(R > 32.75) & (R <= 33.0) & (Z <= 72)])),
               flange=float(np.nanmean(T[(R <= hub["fl_r"]) & (Z >= hub["fl_z"][0]) & (Z <= hub["fl_z"][1])])))
    return out


def sigma_glass(t_c, ea_ev):
    """the vessel's conductivity (S/m) at t_c, Arrhenius through 25 C [IR]."""
    kb = 8.617333e-5
    return D.SIG["glass"] * math.exp(ea_ev / kb * (1 / 298.15 - 1 / (t_c + 273.15)))


def bead_limit():
    """the largest sigma_glass / sigma_gel holding the equatorial bead's gel to its rating, settled (from the bead
    study's sweep, by interpolation), for the drawn and the recommended groove."""
    if not os.path.exists(BEAD_LIMIT):
        return None
    d = json.load(open(BEAD_LIMIT))
    out = {}
    rating = 5.0
    for g, rows in d.get("sweep", {}).items():
        ks = [q["sigma_glass_over_gel"] for q in rows]
        es = [q["eq"]["E_gel_kV_mm"] for q in rows]
        lim = None
        for (k0, e0), (k1, e1) in zip(zip(ks, es), zip(ks[1:], es[1:])):
            if e0 <= rating < e1:
                lim = k0 + (rating - e0) * (k1 - k0) / (e1 - e0)
        out[g] = dict(ratio_limit=lim, rating_kV_mm=rating, rows=list(zip(ks, es)))
    return out


def main():
    t0 = time.time()
    w = winding()
    print("the winding:", json.dumps(w), flush=True)
    with Pool(4) as pool:
        runs = pool.map(deck_current, [(M.AH["r160"]["R"], 0.0), (M.AH["r160"]["R"], 22.0), (w["R20_ohm"], 0.0),
                                       (w["R20_ohm"], 22.0)], chunksize=1)
    for q in runs:
        print("deck:", json.dumps(q), flush=True)
    ea = 8.617333e-5 * math.log(D.SIG["glass40"] / D.SIG["glass"]) / (1 / 298.15 - 1 / 313.15)
    out = dict(note="see the module docstring", winding=w, deck=runs, k_W_mK=K, T_room_C=T_ROOM, dT_air_K=DT_AIR,
               Ea_glass_eV=ea, cases=[])
    # the coil's current: the wound R with the bypass (PROPOSED) and without it (the record's circuit)
    base = {c: next(q for q in runs if q["R_ohm"] == w["R20_ohm"] and q["C_byp_mF"] == c) for c in (0.0, 22.0)}
    for c_mf, i_rms in ((22.0, max(base[22.0]["AHt"]["I_rms_A"], base[22.0]["AHb"]["I_rms_A"])),
                        (0.0, max(base[0.0]["AHt"]["I_rms_A"], base[0.0]["AHb"]["I_rms_A"]))):
        for h_conv in H_CONV:
            for k_coil in K_COIL:
                if h_conv != 20.0 and k_coil != 1.0:
                    continue
                r, z, k, coil, info = maps(k_coil)
                t_air = T_ROOM + DT_AIR
                tc = t_air + 10.0
                for _ in range(6):                                               # the copper's temperature
                    q = i_rms ** 2 * w["R20_ohm"] * (1 + ALPHA_CU * (tc - 20.0))
                    T, sinfo = solve(k, coil, q, h_conv, r)
                    ro = readouts(T, r, z, coil)
                    tc = t_air + ro["coil_mean"]
                ro_c = {kk: t_air + v for kk, v in ro.items()}
                sg = {kk: sigma_glass(ro_c[kk], ea) for kk in ("glass_mean", "glass_max", "glass_band_gap")}
                case = dict(C_byp_mF=c_mf, I_rms_A=i_rms, h_W_m2K=h_conv, k_coil_W_mK=k_coil, P_coil_W=q,
                            rise_K=ro, T_C=ro_c, sigma_glass_S_m=sg,
                            sigma_glass_over_gel={kk: v / D.SIG["gel"] for kk, v in sg.items()}, **info, **sinfo)
                out["cases"].append(case)
                print(f"C {c_mf:g} mF, h {h_conv:g}, k_coil {k_coil:g}: P {q:.3f} W/coil; coil {ro_c['coil_max']:.1f} C, "
                      f"glass {ro_c['glass_min']:.1f}-{ro_c['glass_max']:.1f} C (band to the equator "
                      f"{ro_c['glass_band_gap']:.1f}); sigma_glass/gel {case['sigma_glass_over_gel']['glass_band_gap']:.2f}",
                      flush=True)
    # the mesh: the base case at half the cell
    b = next(q for q in out["cases"] if q["C_byp_mF"] == 22.0 and q["h_W_m2K"] == 20.0 and q["k_coil_W_mK"] == 1.0)
    r2, z2, k2, coil2, _ = maps(1.0, 0.5 * H)
    T2, _ = solve(k2, coil2, b["P_coil_W"], 20.0, r2, 0.5 * H)
    ro2 = readouts(T2, r2, z2, coil2)
    out["mesh"] = dict(h_mm=(H, 0.5 * H), coil_max_K=(b["rise_K"]["coil_max"], ro2["coil_max"]),
                       glass_band_gap_K=(b["rise_K"]["glass_band_gap"], ro2["glass_band_gap"]),
                       glass_pole_K=(b["rise_K"]["glass_pole"], ro2["glass_pole"]))
    out["mesh"]["ok"] = bool(all(abs(v[1] / v[0] - 1) < 0.02 for kk, v in out["mesh"].items() if kk.endswith("_K")))
    print("mesh:", json.dumps(out["mesh"]), flush=True)
    out["bead_limit"] = bead_limit()
    # the room at which the band's glass reaches the beads' limit (the base case, the bypass, h 20, k_coil 1)
    if out["bead_limit"]:
        out["room_limit_C"] = {}
        for g, lim in out["bead_limit"].items():
            if lim["ratio_limit"]:
                t_lim = 1 / (1 / 298.15 - 8.617333e-5 * math.log(lim["ratio_limit"]) / ea) - 273.15
                out["room_limit_C"][g] = dict(glass_C=t_lim, room_C=t_lim - DT_AIR - b["rise_K"]["glass_band_gap"])
        print("the beads' limit:", json.dumps(out["bead_limit"]), json.dumps(out.get("room_limit_C")), flush=True)
    out["run_s"] = time.time() - t0
    json.dump(out, open(os.path.join(HERE, "hub_thermal_results.json"), "w"), indent=1, default=float)


if __name__ == "__main__":
    main()
