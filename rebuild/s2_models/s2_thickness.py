"""rebuild/s2_models/s2_thickness.py -- the plates' thickness: the best compromise between the pump's function (its
gain, its rims' corona margin, its gaps held still at 120 Hz) and its performance (mass, length), the designer
(2026-10-17): "Decide what the overal best compromise is when considering priority on functional behavior and overall
performance".

Options, each a thickness per plate (Ca / Cb plates, rotor vanes, stator vanes; mm):
  A  the record: everything 3 mm;
  B  s2_modes' first fix: every Ca plate 4, every rotor vane 4, every stator vane 4.5;
  C  only the driven plates thickened (the stacks' end plates, the only ones with a net pull, s2_modes drive()):
     Ca_06 and Ca_01 4 mm, the first rotor vane 4 mm, the last stator vane 4.5 mm; the rest 3 mm;
  D  as B, the stator vanes 4 mm (their mode 150 Hz, 1.25 x the pump).
For each:
1. The gain [IR: sim/air_stack_sizing.py's 2-D cell with full-round edges, 6 + 6 vanes, 22 deg sectors, 6 mm air;
   the absolute kappa is the 2-D cell's, the 3-D stack's is lower (rims), so the differences are what count]: per gap
   C_max / C_min at 3, 4 and 4.5 mm; a gap between two thicknesses takes the mean of the two [IR]; z and the
   eigen-cycle power interpolated in C_min between the uniform stacks [IR].
2. The rims' peak field at 13.13 kV (the clamp level) against Peek's onset (sim/vane_cell.py edge_field) [RH].
3. The plates' response at 120 Hz [IR: one mode, the modal mass the plate's mass, the peak twice the mean
   deflection; RH: damping 1 % (bolted aluminium in air), 0.5 % as the low case]: x = 2 F / (M w^2) / |1 - r^2 + 2 i
   zeta r|, r = 120 Hz / f, f from s2_modes' FE (s2_modes_results.json), F the net pull (driven plates) or the gaps'
   tolerance residual (the rest); against the 6 mm gap. Also the worst case: f exactly on 120 Hz.
4. The Campbell rule (s2_modes): every mode a plate's force really reaches, outside 120 Hz +-20 % and 240 Hz +-10 %;
   for C, the 3 mm plates' modes are reached by the tolerance residual only, and their deflection is judged instead.
5. Mass and the stack's length against A.
Writes rebuild/s2_models/s2_thickness_results.json.
Usage: python3 rebuild/s2_models/s2_thickness.py
"""
import json
import math
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, os.path.join(ROOT, "sim"))
sys.path.insert(0, HERE)
import air_stack_sizing as AS  # noqa: E402
import vane_cell as VC  # noqa: E402

G_MM, N_PL, U_KV, F_PUMP = 6.0, 6, 13.13, 120.0
RHO = 2700.0
ZETA, ZETA_LO = 0.01, 0.005
MODES = json.load(open(os.path.join(HERE, "s2_modes_results.json")))
FE = {k: v["excited_Hz"][0] for k, v in MODES["fe"].items()}            # e.g. "rotor_vane_4.0mm": 174.1
DRV = {r["part"]: r for r in MODES["drive"]}
F_END = dict(ca_plate=DRV["Ca_06"]["net_N"], rotor_vane=DRV["C1_r01"]["net_N"], stator_vane=DRV["C1_s12"]["net_N"])
F_RES = max(r["tolerance_residual_N"] for r in MODES["drive"])

OPTIONS = {
    "A": dict(name="the record, all 3 mm", end=dict(ca_plate=3.0, rotor_vane=3.0, stator_vane=3.0),
              inner=dict(ca_plate=3.0, rotor_vane=3.0, stator_vane=3.0)),
    "B": dict(name="all thickened (s2_modes' first fix)", end=dict(ca_plate=4.0, rotor_vane=4.0, stator_vane=4.5),
              inner=dict(ca_plate=4.0, rotor_vane=4.0, stator_vane=4.5)),
    "C": dict(name="only the driven end plates thickened", end=dict(ca_plate=4.0, rotor_vane=4.0, stator_vane=4.5),
              inner=dict(ca_plate=3.0, rotor_vane=3.0, stator_vane=3.0)),
    "D": dict(name="all thickened, the stator vanes 4 mm", end=dict(ca_plate=4.0, rotor_vane=4.0, stator_vane=4.0),
              inner=dict(ca_plate=4.0, rotor_vane=4.0, stator_vane=4.0)),
}
# the stack per side: 6 Ca plates (2 end, 4 inner) and 6 + 6 vanes (rotor r01 and stator s12 at the ends)
COUNT = dict(ca_plate=(2, 4), rotor_vane=(1, 5), stator_vane=(1, 5))


def area_m2(kind):
    """a plate's face, m^2 [IR: the tabs and lugs left out, a few %]."""
    ri, ro, s = 0.050, 0.150, 6 * 22.0 / 360.0
    ann = math.pi * (ro * ro - ri * ri)
    if kind == "ca_plate":
        return ann
    if kind == "rotor_vane":
        return s * ann + math.pi * (ri * ri - 0.0225 ** 2)
    return s * ann + math.pi * (0.162 ** 2 - ro * ro)


def mass(kind, t):
    return area_m2(kind) * t * 1e-3 * RHO


def response(kind, t, F, f=None):
    f = f or FE[f"{kind}_{t:.1f}mm"]
    M, w = mass(kind, t), 2 * math.pi * f
    r = F_PUMP / f
    x0 = 2 * F / (M * w * w)
    amp = lambda z: x0 / math.hypot(1 - r * r, 2 * z * r)                 # noqa: E731
    return dict(f_Hz=f, F_N=F, M_kg=M, x_um=amp(ZETA) * 1e6, x_um_lo_damping=amp(ZETA_LO) * 1e6,
                x_um_on_resonance=x0 / (2 * ZETA) * 1e6, x_pct_gap=amp(ZETA) * 1e3 / G_MM * 100)


def campbell_ok(f):
    return abs(F_PUMP - f) > 0.20 * f and abs(2 * F_PUMP - f) > 0.10 * f


def gains():
    rows = {}
    for t in (3.0, 4.0, 4.5):
        geo = dict(N_sec=12, ws_deg=22.0, wr_deg=22.0, t_vaneMm=t, edge="round", pitch_fixed_mm=G_MM + t)
        q = AS.stack(G_MM, N_PL, "air", geo, v_op=U_KV * 1e3)
        rows[t] = dict(per_gap_max_pF=q["per_gap_max_pF"], per_gap_min_pF=q["per_gap_min_pF"], C_max_pF=q["C_max_pF"],
                       C_min_pF=q["C_min_pF"], kappa=q["kappa"], z=q["z"], P_eigen_W=q["P_eigen_W"], n_gap=q["n_gap"])
        print(f"t {t}: per gap {q['per_gap_min_pF']:.3f} / {q['per_gap_max_pF']:.3f} pF, kappa {q['kappa']:.3f}, "
              f"z {q['z']:.4f}, P {q['P_eigen_W']:.3f} W", flush=True)
    return rows


def stack_gain(rows, t_end_rot, t_end_sta, t_rot, t_sta):
    """the 11 gaps of one side's 6 + 6 vanes, r01 s01 r02 ... s06 in order (r01 the first rotor vane, s06 = s12 the
    last stator vane); each gap the mean of its two vanes' uniform cells [IR]."""
    ts = []
    for k in range(6):
        ts.append(t_end_rot if k == 0 else t_rot)
        ts.append(t_end_sta if k == 5 else t_sta)
    cell = lambda t, key: (rows[t][key] if t in rows else None)           # noqa: E731
    cmx = sum(0.5 * (cell(a, "per_gap_max_pF") + cell(b, "per_gap_max_pF")) for a, b in zip(ts, ts[1:]))
    cmn = sum(0.5 * (cell(a, "per_gap_min_pF") + cell(b, "per_gap_min_pF")) for a, b in zip(ts, ts[1:]))
    edge = rows[3.0]["C_min_pF"] - rows[3.0]["n_gap"] * rows[3.0]["per_gap_min_pF"]
    C_max, C_min = cmx, cmn + edge
    # z and P interpolated in C_min between the uniform 3 and 4 mm stacks [IR]
    a, b = rows[3.0], rows[4.0]
    s = (C_min - a["C_min_pF"]) / (b["C_min_pF"] - a["C_min_pF"])
    return dict(C_max_pF=C_max, C_min_pF=C_min, kappa=C_max / C_min, z=a["z"] + s * (b["z"] - a["z"]),
                P_eigen_W=a["P_eigen_W"] + s * (b["P_eigen_W"] - a["P_eigen_W"]))


def main():
    out = dict(rule=dict(damping=ZETA, damping_low=ZETA_LO, gap_mm=G_MM, pump_Hz=F_PUMP, F_end_N=F_END, F_residual_N=F_RES))
    rows = gains()
    out["uniform"] = {f"{k:g}": v for k, v in rows.items()}
    rims = {}
    for t in (3.0, 4.0, 4.5):
        e = VC.edge_field(t, G_MM, "round")
        E = e["E_peak_per_V"] * U_KV * 10.0
        rims[f"{t:g}"] = dict(E_kV_cm=E, peek_kV_cm=VC.peek_kV_per_cm(0.5 * t), ratio=E / VC.peek_kV_per_cm(0.5 * t))
    out["rims"] = rims
    print("rims:", {k: round(v["ratio"], 3) for k, v in rims.items()})
    base = None
    out["options"] = {}
    for key, o in OPTIONS.items():
        e, i = o["end"], o["inner"]
        g = stack_gain(rows, e["rotor_vane"], e["stator_vane"], i["rotor_vane"], i["stator_vane"])
        m = sum(mass(k, e[k]) * COUNT[k][0] + mass(k, i[k]) * COUNT[k][1] for k in COUNT) * 2      # both sides
        L = sum(e[k] * COUNT[k][0] + i[k] * COUNT[k][1] for k in COUNT)                           # one side's metal
        resp = {}
        for k in COUNT:
            resp[f"{k} end ({e[k]:g} mm)"] = response(k, e[k], F_END[k])
            resp[f"{k} inner ({i[k]:g} mm)"] = response(k, i[k], F_RES)
        driven_ok = all(campbell_ok(FE[f"{k}_{e[k]:.1f}mm"]) for k in COUNT)
        inner_ok = all(campbell_ok(FE[f"{k}_{i[k]:.1f}mm"]) for k in COUNT)
        rim = max(rims[f"{t:g}"]["ratio"] for t in (e["rotor_vane"], e["stator_vane"], i["rotor_vane"], i["stator_vane"]))
        row = dict(name=o["name"], end_mm=e, inner_mm=i, gain=g, rim_ratio_worst=rim, mass_kg=m, metal_mm_per_side=L,
                   response=resp, campbell_driven_ok=driven_ok, campbell_inner_ok=inner_ok,
                   x_um_worst=max(r["x_um"] for r in resp.values()),
                   x_um_worst_lo_damping=max(r["x_um_lo_damping"] for r in resp.values()))
        base = base or row
        row.update(d_mass_kg=m - base["mass_kg"], d_length_mm=L - base["metal_mm_per_side"],
                   d_kappa_pct=100 * (g["kappa"] / base["gain"]["kappa"] - 1), d_z=g["z"] - base["gain"]["z"],
                   d_P_pct=100 * (g["P_eigen_W"] / base["gain"]["P_eigen_W"] - 1))
        out["options"][key] = row
        print(f"{key} {o['name']}: kappa {g['kappa']:.3f} ({row['d_kappa_pct']:+.1f} %), z {g['z']:.4f}, "
              f"P {row['d_P_pct']:+.1f} %, mass {row['d_mass_kg']:+.2f} kg, length {row['d_length_mm']:+.1f} mm/side, "
              f"rim {rim:.3f}, Campbell driven {driven_ok} inner {inner_ok}, worst x {row['x_um_worst']:.1f} um "
              f"({row['x_um_worst_lo_damping']:.1f} at 0.5 %)")
        for nm, r in resp.items():
            print(f"     {nm}: {r['f_Hz']:.1f} Hz, F {r['F_N']:.2f} N, x {r['x_um']:.1f} um "
                  f"(on resonance {r['x_um_on_resonance']:.0f} um)")
    json.dump(out, open(os.path.join(HERE, "s2_thickness_results.json"), "w"), indent=1, default=float)


if __name__ == "__main__":
    main()
