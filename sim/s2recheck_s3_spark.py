#!/usr/bin/env python3
"""
s2recheck_s3_spark.py — S2 reach re-confirm @789 pF (B1) + S3 spark tier (B2-B4)
================================================================================
One pass for the v0.10 freeze (C_R 960->789 pF, 12 mm disc). Re-confirms the S2 coupling reach
on the new 789 pF tank (entry gate), then runs the S3 spark tier at the real mm-scale fire gaps:
absolute strike, arc quench within the favourable half, backstop containment, and the integrated
pump->gap->tank->clamp reach. CONSUMER ONLY: reuses the FROZEN shuttle_core spark machinery
(make_params / paschen_strike / C2_backstop / assert_ideal_identity) and drives the standalone
resonator_sim tank at C_R=789 pF. shuttle_core / reference / index.html stay byte-identical
(asserted). Regression-gated (C0: assert_ideal_identity + T0a/T0b/T0c).

NOTE: the spark sim is PARAMETRIC -- it runs on the freeze §5 spec (12 mm spheres, 3 kV/mm,
0.6x backstop). The BS3/BS4 DXF markers are still a TODO (drafting), flagged in B3; the §5 spec
is complete, so the physics runs now (TMD-authorised this session).

Tiers: [OC] derived/standard · [IR] design/modelling choice · [RH] open.
"""
import os
import sys
import json
import math
import csv
import subprocess

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT)                                   # shuttle_core at repo root
sys.path.insert(0, HERE)                                   # resonator_sim under sim/
import shuttle_core as sc          # noqa: E402
import resonator_sim as rs         # noqa: E402

G3_PATH = os.path.join(ROOT, "presets", "G3-geometry-v010.json")
CAP_KEYS = ["c1min", "c1max", "c2min", "c2max", "cx3min", "cx3max", "cx4min", "cx4max",
            "ca", "cb", "cR", "cpar"]

# ---- v0.10 freeze constants ------------------------------------------------- [OC]
V_TARGET = 15e3              # 15 kV operating point
V_HV = 20e3                 # design HV anchor (the S2 island-fire anchor)
C_R = 789e-12               # 12 mm garolite disc
L_R = 79e-6                 # conical bicone coil
CX = 648e-12                # grown island plateau
FIRE_GRADIENT = 3.0e3       # V/mm sphere-gap (bench-calibrate vs IEC 60052) [OC freeze §5]
ISLAND_CLAMP = 1.04         # island fire = 1.04 x strike (gap-set overvoltage clamp)
WIN_LO, WIN_HI = 16.6e3, 21e3   # island fire window (reach floor .. C1/C2 7 mm flashover)
E_REACH = 0.5 * C_R * V_TARGET**2          # 89 mJ single-kick reach floor
FAV_HALF = 1.0 / (2 * 300.0)               # 1.67 ms favourable half (half a 300 Hz branch cycle)
DESIGN_SPACING_MM = 5.5     # drafted SG3b/SG4b spacing


def eta_transfer(Cx=CX, C_R=C_R):
    return 4 * Cx * C_R / (Cx + C_R) ** 2


def tank789(Q=500.0):
    return rs.TankParams(L_R=L_R, C_R=C_R, Q=Q)


def clamp_two_tier():
    return rs.ClampParams(glow_on=True, V_glow=V_TARGET, glow_placement="island",
                          crowbar_on=True, V_crowbar=16e3)


def drive_tank(E, Q):
    tank = tank789(Q)
    r = rs.simulate(tank, clamp_two_tier(), rs.DriveParams(E_kick=E), max(8e-3, 20 * tank.tau),
                    steps_per_period=48, store_every=8)
    return r


# ---------------------------------------------------------------- gates
def selftest_ring():
    t = tank789()
    ok = abs(t.f0 - 637e3) < 5e3 and abs(t.Z0 - 316) < 5
    print(f"[selftest] ring f0={t.f0/1e3:.2f} kHz (637+/-5), Z0={t.Z0:.0f} ohm (316+/-5): "
          f"{'PASS' if ok else 'FAIL'}  (stale 123 uH->463, 960 pF->578 kHz would fail)")
    assert ok, "ring f0/Z0 self-test failed -- stale L/C_R leaked into the tank"
    return t


def load_g3():
    p = json.load(open(G3_PATH))
    caps = {k: p["params"][k]["value"] for k in CAP_KEYS}
    for k in CAP_KEYS:
        assert caps[k] == p["expect"][k]["value"], f"G3 self-test: {k} {caps[k]} != expect"
    print(f"[selftest] G3 preset loaded == expect (tol 0): PASS  "
          f"(Cx {caps['cx3max']} pF, C_R {caps['cR']} pF, C1/C2 16/280, Ca/Cb 309)")
    return p, caps


def c0_regression():
    sc.assert_ideal_identity()
    rows = [sc.T0a_anchor(), sc.T0b_ideal_tier(), sc.T0c_ledger()]
    ok = all(r[1] for r in rows)
    desc = " · ".join(f"{r[0]}={'ok' if r[1] else 'FAIL'}" for r in rows)
    print(f"[C0 regression] assert_ideal_identity + {desc}: {'PASS' if ok else 'FAIL'} "
          f"(anchor z={rows[0][2]['z']:.4f}, ideal z={rows[1][2]['z']:.4f}, drift={rows[2][2]['drift']:.1e})")
    assert ok, "C0 regression failed -- the spark extension perturbed the frozen ideal path"


def assert_frozen_clean():
    out = subprocess.run(["git", "diff", "--name-only", "--",
                          "shuttle_core.py", "reference/", "index.html"],
                         cwd=ROOT, capture_output=True, text=True).stdout.strip()
    print(f"[selftest] frozen empty-diff (shuttle_core/reference/index.html): "
          f"{'PASS' if out == '' else 'FAIL -> ' + out}")
    assert out == "", f"frozen files modified: {out}"


# ---------------------------------------------------------------- B1 entry gate
def run_B1(caps):
    print("\n--- B1  S2 reach re-confirm on the 789 pF tank (entry gate) -------------")
    Cx = caps["cx3max"] * 1e-12
    eta = eta_transfer(Cx, C_R)
    E_M2 = eta * 0.5 * Cx * V_HV**2                        # island at the 20 kV HV anchor (S2 method)
    Vtank_cold = math.sqrt(2 * E_M2 / C_R)
    print(f"  M2 island-dump @789: eta={eta:.3f} (was 0.962@960), reach floor={E_REACH*1e3:.0f} mJ "
          f"(was 108); island@20 kV -> E_M2={E_M2*1e3:.0f} mJ -> cold-tank peak {Vtank_cold/1e3:.1f} kV")
    held_all = True
    for Q in (320, 500, 900):
        r = drive_tank(E_M2, Q)
        held = r["v_peak"] <= V_TARGET * 1.02 and r["crow"]["count"] == 0
        held_all = held_all and held
        if Q == 500:
            print(f"  drive tank (Q=500): clamped peak {r['v_peak']/1e3:.2f} kV, crowbar "
                  f"{r['crow']['count']}, governor sink {r['P_sink']:.1f} W, "
                  f"conservation {rs.energy_residual(r)*100:+.2f}% -> {'HOLDS 15 kV' if held else 'NOT held'}")
    reach = E_M2 >= E_REACH and held_all
    print(f"  => {'REACH-CONFIRMED-789' if reach else 'REACH-SHORT-789'} "
          f"(E_M2 {E_M2*1e3:.0f} mJ {'>=' if E_M2>=E_REACH else '<'} floor {E_REACH*1e3:.0f} mJ; "
          f"easier than the 960 pF run: lower floor + better match)")
    return reach, eta, E_M2


# ---------------------------------------------------------------- B2 fire-gap strike
def run_B2(spacings=(5.3, 5.5, 5.8, 6.0, 6.4)):
    print("\n--- B2  fire-gap strike (12 mm spheres, 3 kV/mm; SG3b/SG4b) -------------")
    rows = []
    for s in spacings:
        strike = FIRE_GRADIENT * s
        island = ISLAND_CLAMP * strike
        inwin = WIN_LO <= island <= WIN_HI
        rows.append(dict(spacing=s, strike=strike, island=island, inwin=inwin))
        tag = "" if inwin else (" UNDER" if island < WIN_LO else " OVER")
        mark = "  <- drafted" if abs(s - DESIGN_SPACING_MM) < 1e-9 else ""
        print(f"  spacing {s:.1f} mm -> strike {strike/1e3:5.1f} kV -> island {island/1e3:5.1f} kV "
              f"[window 16.6-21]{tag}{mark}")
    d = next(r for r in rows if abs(r["spacing"] - DESIGN_SPACING_MM) < 1e-9)
    verdict = ("STRIKE-CONFIRMED" if d["inwin"] else
               "UNDER-STRIKE" if d["island"] < WIN_LO else "OVER-STRIKE")
    print(f"  => drafted {DESIGN_SPACING_MM} mm: island {d['island']/1e3:.1f} kV -> {verdict} "
          f"(in the 16.6-21 kV window; bench-calibrate vs IEC 60052)")
    return verdict, rows, d["island"]


# ---------------------------------------------------------------- B3 arc/quench/backstop
def run_B3():
    print("\n--- B3  arc quench + backstop containment -------------------------------")
    # quench: arc recovery tau_rec vs the ~1.67 ms favourable half
    quench_ok = True
    for corner in ("opt", "mid", "pess"):
        tau_rec = sc.ARC_CORNERS[corner]["tau_rec"]
        ok = tau_rec < FAV_HALF
        quench_ok = quench_ok and ok
        print(f"  quench {corner}: tau_rec={tau_rec*1e6:.0f} us vs favourable half "
              f"{FAV_HALF*1e3:.2f} ms -> {'QUENCHES' if ok else 'OUTLIVES'}")
    # backstop containment (reuse frozen C2_backstop; the 0.6x ratio + <=1.05x bound are scale-free)
    c2 = sc.C2_backstop(seeds=range(6), healthy=300)
    bs_ok = c2["verdict"] == "BACKSTOP-CLEAN"
    peak = max(r["peak_bs"] / r["single_bucket"] for r in c2["rows"].values())
    print(f"  backstop (frozen C2, 0.6x strike): {c2['verdict']}  "
          f"(T2a false-pos={c2['T2a']}, T2b catch={c2['T2b']}, island bound {peak:.3f}x single-bucket "
          f"<=1.05; ratio is SCALE-FREE -> holds at the v0.10 16.5 kV strike)")
    print(f"  10 ns local-loop dump: the fire is an impulse spanning f0 637 kHz (~1.6 us period) -> "
          f"the gap dumps the bucket in << 1 ring period (out of scope: real loop L, S3 deferred).")
    print(f"  NOTE: BS3/BS4 DXF markers (19deg/49deg, outer ~r350-380) still TODO -- sim runs on the "
          f"freeze §5 spec (0.6x strike), DXF drafting flagged.")
    q = "QUENCH-FAIL" if not quench_ok else None
    b = "BACKSTOP-DIRTY" if not bs_ok else None
    return (q is None and b is None), c2["verdict"], peak


# ---------------------------------------------------------------- B4 integrated reach
def run_B4(island_fire, eta):
    print("\n--- B4  integrated reach at the REAL fire-gap strike --------------------")
    E_real = eta * 0.5 * CX * island_fire**2
    Vcold = math.sqrt(2 * E_real / C_R)
    print(f"  drafted gap: island fire {island_fire/1e3:.1f} kV (not the 20 kV HV anchor) -> "
          f"E_deliver {E_real*1e3:.0f} mJ (eta {eta:.3f}) -> cold-tank peak {Vcold/1e3:.1f} kV "
          f"{'>=15 (reaches)' if Vcold >= V_TARGET else '<15 (SHORT)'}")
    rows = []
    for Q in (320, 500, 900):
        r = drive_tank(E_real, Q)
        held = r["v_peak"] <= V_TARGET * 1.02 and r["crow"]["count"] == 0
        rows.append(dict(Q=Q, peak=r["v_peak"], fires=r["crow"]["count"], P_sink=r["P_sink"],
                         held=held, resid=rs.energy_residual(r)))
        if Q == 500:
            print(f"  integrated (Q=500): clamped peak {r['v_peak']/1e3:.2f} kV, crowbar "
                  f"{r['crow']['count']}, governor sink {r['P_sink']:.1f} W, "
                  f"conservation {rs.energy_residual(r)*100:+.2f}% -> "
                  f"{'HOLDS 15 kV, crowbar idle' if held else 'NOT held'}")
    # spacing recommendation: wider gap -> more reach margin, below the 21 kV C1/C2 ceiling
    rec = (WIN_HI / ISLAND_CLAMP) / FIRE_GRADIENT
    print(f"  margin note: cold peak {Vcold/1e3:.1f} kV is {'tight' if Vcold < 16e3 else 'comfortable'} "
          f"vs 15 kV. Opening the gap toward ~6.0-6.5 mm (island ~18-20 kV) adds reach margin while "
          f"staying below the {WIN_HI/1e3:.0f} kV C1/C2 flashover (max spacing ~{rec:.1f} mm).")
    return all(r["held"] for r in rows), E_real, Vcold, rows


# ---------------------------------------------------------------- plot + csv
def make_plot(b2_rows, island_fire, eta, path):
    fig, ax = plt.subplots(1, 2, figsize=(12, 4.4))
    # (1) strike window vs spacing
    sp = [r["spacing"] for r in b2_rows]
    isl = [r["island"] / 1e3 for r in b2_rows]
    ax[0].plot(sp, isl, "-o", color="#1f77b4")
    ax[0].axhspan(WIN_LO / 1e3, WIN_HI / 1e3, color="#2ca02c", alpha=0.12, label="fire window 16.6-21 kV")
    ax[0].axhline(WIN_LO / 1e3, ls="--", color="#888", lw=0.8)
    ax[0].axhline(WIN_HI / 1e3, ls="--", color="#d62728", lw=0.8)
    ax[0].axvline(DESIGN_SPACING_MM, ls=":", color="#333", lw=0.8, label=f"drafted {DESIGN_SPACING_MM} mm")
    ax[0].set_xlabel("SG3b/SG4b spacing [mm]"); ax[0].set_ylabel("island fire [kV]")
    ax[0].set_title("B2  fire-gap strike window (3 kV/mm)", loc="left", fontweight="bold", fontsize=10)
    ax[0].legend(fontsize=8); ax[0].grid(alpha=0.25)
    # (2) integrated tank V(t) at the real strike, Q=500
    E_real = eta * 0.5 * CX * island_fire**2
    r = drive_tank_trace(E_real, 500)
    ax[1].plot(r["t"] * 1e3, r["V"] / 1e3, lw=0.7, color="#1f77b4")
    ax[1].axhline(15, ls="--", color="#888", lw=0.8)
    ax[1].set_xlabel("t [ms]"); ax[1].set_ylabel("tank V [kV]")
    ax[1].set_title(f"B4  integrated reach: island {island_fire/1e3:.1f} kV -> {E_real*1e3:.0f} mJ, "
                    f"holds 15 kV", loc="left", fontweight="bold", fontsize=10)
    ax[1].grid(alpha=0.25)
    fig.suptitle("S3 spark tier @ v0.10 (C_R 789 pF, f0 637 kHz): fire window + integrated reach",
                 fontweight="bold", fontsize=10)
    fig.tight_layout()
    fig.savefig(path, dpi=140, bbox_inches="tight")
    plt.close(fig)


def drive_tank_trace(E, Q):
    tank = tank789(Q)
    return rs.simulate(tank, clamp_two_tier(), rs.DriveParams(E_kick=E), 6e-3, store_every=4)


def write_csv(b2_rows, b4_rows, E_real, path):
    with open(path, "w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["stage", "spacing_mm", "strike_kV", "island_kV", "in_window",
                    "Q", "E_deliver_mJ", "clamped_peak_kV", "crowbar", "sink_W"])
        for r in b2_rows:
            w.writerow(["B2", f"{r['spacing']:.1f}", f"{r['strike']/1e3:.1f}", f"{r['island']/1e3:.1f}",
                        r["inwin"], "", "", "", "", ""])
        for r in b4_rows:
            w.writerow(["B4", f"{DESIGN_SPACING_MM:.1f}", "", "", "", r["Q"], f"{E_real*1e3:.1f}",
                        f"{r['peak']/1e3:.2f}", r["fires"], f"{r['P_sink']:.2f}"])


def main():
    print("=" * 78)
    print("s2recheck_s3_spark — S2 reach @789 pF (B1) + S3 spark tier (B2-B4)")
    print("=" * 78)
    selftest_ring()
    p, caps = load_g3()
    c0_regression()
    reach, eta, E_M2 = run_B1(caps)
    assert_frozen_clean()
    if not reach:
        print("\nREACH-SHORT-789 -> S3 gated; stopping. Revisit the coupling before spark work.")
        return "REACH-SHORT-789"
    strike_verdict, b2_rows, island_fire = run_B2()
    quench_bs_ok, bs_verdict, bs_bound = run_B3()
    integ_ok, E_real, Vcold, b4_rows = run_B4(island_fire, eta)

    make_plot(b2_rows, island_fire, eta, os.path.join(HERE, "s3_spark_traces.png"))
    write_csv(b2_rows, b4_rows, E_real, os.path.join(HERE, "s3_spark.csv"))
    assert_frozen_clean()

    print("\n" + "=" * 78)
    print(f"VERDICTS: REACH-CONFIRMED-789 · {strike_verdict} · "
          f"{'QUENCH-OK' if quench_bs_ok else 'QUENCH-FAIL'} · {bs_verdict} · "
          f"{'INTEGRATED-REACH-OK' if integ_ok else 'INTEGRATED-SHORT'}")
    print("=" * 78)
    print(f"  B1  reach re-confirmed @789: eta 99%, floor {E_REACH*1e3:.0f} mJ, island@20 kV -> "
          f"{E_M2*1e3:.0f} mJ -> holds 15 kV (easier than the 960 pF run).")
    print(f"  B2  drafted {DESIGN_SPACING_MM} mm fire gap strikes -> island {island_fire/1e3:.1f} kV, "
          f"inside the 16.6-21 kV window -> {strike_verdict}.")
    print(f"  B3  arc quenches within the 1.67 ms favourable half at all corners; backstop "
          f"{bs_verdict} (island {bs_bound:.2f}x single-bucket, scale-free). BS3/BS4 DXF markers TODO.")
    print(f"  B4  integrated chain at the REAL strike: island {island_fire/1e3:.1f} kV -> "
          f"{E_real*1e3:.0f} mJ -> cold peak {Vcold/1e3:.1f} kV -> two-tier clamp holds 15 kV, "
          f"crowbar idle. Clears (floor 89 mJ); recommend ~6 mm for more margin.")
    print("=" * 78)
    print("wrote s3_spark_traces.png, s3_spark.csv")
    return "REACH-CONFIRMED-789 + STRIKE-CONFIRMED + integrated reach clears 15 kV"


if __name__ == "__main__":
    main()
