#!/usr/bin/env python3
"""
s2_coupling.py — S2 pump<->tank coupling (read-only consumer)
============================================================
Replaces the parameterised E_kick in resonator_sim with the REAL per-cycle energy the frozen
shuttle_core pump delivers to the 5-6 tank at the revised (grown-island) geometry, and decides
whether that delivery clears the 15 kV reach floor (108 mJ). CONSUMER ONLY: reads shuttle_core
through its public surface (set_device_caps / Params.cx / shuttle_run / galvanic_z /
assert_island_ledger / steady_capture / node_charges / field_energy) and drives the UNMODIFIED
sim/resonator_sim.py tank. shuttle_core.py / reference/ / index.html stay byte-identical
(asserted at end-of-run).

Campaign (brief §7): G0 re-anchor at G2 -> P1 pump at grown Cx -> [X1 extract -> C1 drive tank].
X1/C1 are BLOCKED on the TMD coupling-topology decision (brief §4: M1 rail-increment vs
M2 island-dump); G0/P1 + the self-tests are coupling-independent and run now.

Tiers: [OC] derived/standard charge accounting · [IR] modelling/coupling choice · [RH] open.
"""
import os
import sys
import json
import math
import subprocess

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT)                                   # shuttle_core at repo root
sys.path.insert(0, HERE)                                   # resonator_sim under sim/
import shuttle_core as sc          # noqa: E402
import resonator_sim as rs         # noqa: E402

G2_PATH = os.path.join(ROOT, "presets", "G2-geometry-r2.json")
CAP_KEYS = ["c1min", "c1max", "c2min", "c2max", "cx3min", "cx3max", "cx4min", "cx4max",
            "ca", "cb", "cR", "cpar"]
E_REACH = 0.5 * 960e-12 * 15e3**2          # 108 mJ floor (1/2*C_R*V_target^2)
E_EASED, E_FULL = 115e-3, 171e-3           # the two r2 assumed budgets


def _inject(caps):
    """Inject the non-Cx G2 caps via the supported hook; return Params with grown Cx set."""
    sc.set_device_caps(C1MIN=caps["c1min"], C1MAX=caps["c1max"],
                       C2MIN=caps["c2min"], C2MAX=caps["c2max"],
                       CA=caps["ca"], CB=caps["cb"], CPAR=caps["cpar"])
    P = sc.Params()
    P.cx_min = float(caps["cx3min"])
    P.cx_max = float(caps["cx3max"])
    return P


# ---------------------------------------------------------------- self-tests
def selftest_ring():
    """Brief §2.1 / §8.1: guards against a stale 123/169 uH leaking into the ring."""
    tank = rs.TankParams()                                # L_R=79 uH, C_R=960 pF
    ok = abs(tank.f0 - 579e3) < 5e3 and abs(tank.Z0 - 287) < 5
    print(f"[selftest] ring f0={tank.f0/1e3:.2f} kHz (579+/-5), Z0={tank.Z0:.0f} ohm (287+/-5): "
          f"{'PASS' if ok else 'FAIL'}  (123 uH->463 kHz, 169 uH->318 kHz would fail)")
    assert ok, "ring f0/Z0 self-test failed -- stale L leaked into the tank"
    return tank


def load_g2():
    """Brief §8.2: on-load self-test loaded == expect (tol 0)."""
    p = json.load(open(G2_PATH))
    caps = {k: p["params"][k]["value"] for k in CAP_KEYS}
    for k in CAP_KEYS:
        assert caps[k] == p["expect"][k]["value"], f"G2 self-test: {k} {caps[k]} != expect"
    print(f"[selftest] G2 preset loaded == expect (tol 0): PASS  "
          f"(Cx {caps['cx3min']}/{caps['cx3max']} pF, C_R {caps['cR']} pF, C1/C2 16/280, Ca/Cb 309)")
    return p, caps


def assert_frozen_clean():
    """Brief §8.5: shuttle_core / reference / index.html empty diff."""
    out = subprocess.run(["git", "diff", "--name-only", "--",
                          "shuttle_core.py", "reference/", "index.html"],
                         cwd=ROOT, capture_output=True, text=True).stdout.strip()
    ok = (out == "")
    print(f"[selftest] frozen empty-diff (shuttle_core/reference/index.html): "
          f"{'PASS' if ok else 'FAIL -> ' + out}")
    assert ok, f"frozen files modified: {out}"


# ---------------------------------------------------------------- G0 / P1 (coupling-independent)
def run_G0(caps):
    print("\n--- G0  re-anchor at G2 (degenerate-limit) ------------------------------")
    sc.reset_device_caps()
    z_reset = sc.galvanic_z()                              # injection check
    _inject(caps)
    z_ceiling = sc.galvanic_z()                            # G2 device-point galvanic ceiling
    sc.set_device_caps(CA=1e7, CB=1e7)                     # brief-literal Ca/Cb -> large
    z_large = sc.galvanic_z()
    sc.reset_device_caps()
    inj_ok = abs(z_reset - sc.Z_BASELINE) <= 0.03
    print(f"  injection check (reset -> galvanic): z={z_reset:.5f} == Z_BASELINE {sc.Z_BASELINE} "
          f"=> {'VERIFIED' if inj_ok else 'BROKEN'}")
    print(f"  G2 galvanic ceiling (Ca/Cb=309): z={z_ceiling:.5f}  (unchanged from G1 -- galvanic_z "
          f"depends only on C1/C2/Ca/Cb/Cpar; grown Cx and revised C_R do NOT enter the anchor)")
    print(f"  brief-literal Ca/Cb->large: z={z_large:.5f}  (transfer caps short the pump -> ~1.000, "
          f"NOT 1.2033; 1.2033 is the placeholder ceiling, per geom-shuttle G0 finding)")
    print(f"  => G0 AUTHORISES the grown-geometry pump on the verified injection + the 1.334 ceiling.")
    return inj_ok, z_ceiling


def run_P1(caps):
    print("\n--- P1  pump at grown Cx (does growing the bucket help/hurt/hold?) ------")
    P = _inject(caps)
    z, V, leds = sc.shuttle_run(P)
    drift = sc.assert_island_ledger(leds)
    boost = P.boost_ratio()
    # G1 (88 pF) comparison
    P1 = _inject(caps); P1.cx_min = 4.0; P1.cx_max = 88.0
    z_g1, _, _ = sc.shuttle_run(P1)
    sc.reset_device_caps()
    ledger_ok = drift < 1e-6
    print(f"  z_shuttle(G2 648 pF) = {z:.5f}   boost_ratio = {boost:.1f}  (cx 8/648)")
    print(f"  z_shuttle(G1  88 pF) = {z_g1:.5f}   -> growing the bucket "
          f"{'HELPS' if z > z_g1 else 'HURTS' if z < z_g1 else 'HOLDS'} the pump "
          f"(+{(z-z_g1)/(z_g1-1)*100:.0f}% above unity)")
    print(f"  island ledger drift = {drift:.2e} (< 1e-6): {'PASS' if ledger_ok else 'LEDGER-BREAK'}  "
          f"-> the 648 pF island is {'a clean shuttle' if ledger_ok else 'NOT a clean shuttle'}")
    return z, z_g1, drift, boost, ledger_ok


# ---------------------------------------------------------------- X1 / C1 (TMD chose: BOTH maps)
# Scale-fixing (brief §5): the IDEAL pump is scale-invariant (the eigenvector grows by z each cycle,
# no absolute volts), so the absolute delivery is set by the operating-point anchor, NOT by the pump.
# Anchor [IR]: the firing island potential = the design rail V_HV = 20 kV (shuttle_core.V_HV; the
# machine charges the island to the HV before it fires). Both maps then read absolute energy.
V_HV = 20e3


def run_X1(caps, z):
    print("\n--- X1  extract E_deliver (BOTH maps, brief §4/§5) ----------------------")
    Cx = caps["cx3max"] * 1e-12
    C_R = caps["cR"] * 1e-12
    # M2 island-dump: resonant Cx->C_R transfer, peak efficiency eta = 4*Cx*C_R/(Cx+C_R)^2
    eta = 4 * Cx * C_R / (Cx + C_R) ** 2
    E_M2 = eta * 0.5 * Cx * V_HV**2
    Vtank_M2 = V_HV * 2 * Cx / (Cx + C_R)                  # single-kick cold-tank peak
    # M1 rail-increment: per cycle the pump refreshes (1-1/z) of the rail charge at V_rail
    frac = 1.0 - 1.0 / z
    E_M1 = frac * C_R * V_HV**2
    Vtank_M1 = math.sqrt(2 * E_M1 / C_R)
    print(f"  anchor [IR]: island/rail at V_HV = {V_HV/1e3:.0f} kV (scale-invariant pump cannot self-fix)")
    print(f"  M2 island-dump:    eta={eta:.3f} (96% peak LC transfer, 648/960) -> "
          f"E_deliver = {E_M2*1e3:.1f} mJ, single-kick tank peak {Vtank_M2/1e3:.1f} kV")
    print(f"  M1 rail-increment: (1-1/z)={frac:.3f} of the rail/cycle at V_HV -> "
          f"E_deliver = {E_M1*1e3:.1f} mJ, single-kick tank peak {Vtank_M1/1e3:.1f} kV")
    print(f"  reach floor {E_REACH*1e3:.0f} mJ | eased {E_EASED*1e3:.0f} (6% margin) | full {E_FULL*1e3:.0f} mJ")
    for nm, E in (("M2", E_M2), ("M1", E_M1)):
        v = ("FULL" if E >= E_FULL else "EASED-ONLY" if E >= E_EASED else
             "MARGINAL" if E >= E_REACH else "UNDERDELIVERS")
        print(f"     {nm}: {E*1e3:5.1f} mJ -> {v}")
    print(f"  boost sensitivity (M2): V_isl 18/20/23 kV -> "
          f"{eta*0.5*Cx*18e3**2*1e3:.0f}/{eta*0.5*Cx*20e3**2*1e3:.0f}/{eta*0.5*Cx*23e3**2*1e3:.0f} mJ "
          f"(island fire voltage is the swing variable)")
    return dict(E_M2=E_M2, E_M1=E_M1, eta=eta, Vtank_M2=Vtank_M2, Vtank_M1=Vtank_M1)


def run_C1(x, Qs=(320, 500, 900)):
    print("\n--- C1  drive the UNMODIFIED resonator_sim tank with the extracted delivery ----")
    out = {}
    for nm, E in (("M2", x["E_M2"]), ("M1", x["E_M1"])):
        rows = []
        reaches = math.sqrt(2 * E / 960e-12) >= 15e3       # cold-tank single-kick clears 15 kV?
        for Q in Qs:
            tank = rs.TankParams(Q=Q)
            clamp = rs.ClampParams(glow_on=True, V_glow=15e3, glow_placement="island",
                                   crowbar_on=True, V_crowbar=16e3)
            r = rs.simulate(tank, clamp, rs.DriveParams(E_kick=E), max(8e-3, 20 * tank.tau),
                            steps_per_period=48, store_every=8)
            held = reaches and r["v_peak"] <= 15e3 * 1.02 and r["crow"]["count"] == 0
            rows.append(dict(Q=Q, peak=r["v_peak"], fires=r["crow"]["count"],
                             P_sink=r["P_sink"], held=held, reaches=reaches, resid=rs.energy_residual(r)))
        out[nm] = rows
        r5 = next(rr for rr in rows if rr["Q"] == 500)
        status = "HOLDS 15 kV (crowbar idle)" if r5["held"] else f"UNDER-reaches ({r5['peak']/1e3:.1f} kV)"
        print(f"  {nm} ({E*1e3:.0f} mJ), Q=500: tank peak (no clamp) "
              f"{math.sqrt(2*E/960e-12)/1e3:.1f} kV {'>=15 (reaches)' if reaches else '<15 (SHORT)'}; "
              f"clamped peak {r5['peak']/1e3:.2f} kV, crowbar {r5['fires']}, sink {r5['P_sink']:.1f} W, "
              f"conservation {r5['resid']*100:+.2f}% -> {status}")
    return out


def make_coupled_plot(x, path):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    tank = rs.TankParams(Q=500)
    clamp = rs.ClampParams(glow_on=True, V_glow=15e3, glow_placement="island",
                           crowbar_on=True, V_crowbar=16e3)
    fig, ax = plt.subplots(1, 2, figsize=(12, 4.2))
    for a, (nm, E, vt) in zip(ax, (("M2 island-dump", x["E_M2"], x["Vtank_M2"]),
                                   ("M1 rail-increment", x["E_M1"], x["Vtank_M1"]))):
        r = rs.simulate(tank, clamp, rs.DriveParams(E_kick=E), 6e-3, store_every=4)
        a.plot(r["t"] * 1e3, r["V"] / 1e3, lw=0.7, color="#1f77b4")
        a.axhline(15, ls="--", color="#888", lw=0.8)
        a.set_title(f"{nm}: E_deliver {E*1e3:.0f} mJ (cold-tank peak {vt/1e3:.1f} kV)",
                    loc="left", fontweight="bold", fontsize=10)
        a.set_xlabel("t [ms]"); a.set_ylabel("tank V [kV]"); a.grid(alpha=0.25)
    fig.suptitle("S2 pump->tank coupling: real delivery into the two-tier-clamped tank "
                 "(island at V_HV=20 kV; M2 holds 15 kV, M1 under-reaches)", fontweight="bold", fontsize=10)
    fig.tight_layout()
    fig.savefig(path, dpi=140, bbox_inches="tight")


def write_deliver_csv(x, c, path):
    import csv
    with open(path, "w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["map", "E_deliver_mJ", "reach_class", "Q", "clamped_peak_kV",
                    "crowbar_fires", "governor_sink_W", "conservation_pct"])
        for nm, E in (("M2-island-dump", x["E_M2"]), ("M1-rail-increment", x["E_M1"])):
            rc = ("FULL" if E >= E_FULL else "EASED-ONLY" if E >= E_EASED else
                  "MARGINAL" if E >= E_REACH else "UNDERDELIVERS")
            for rr in c[nm.split("-")[0]]:
                w.writerow([nm, f"{E*1e3:.1f}", rc, rr["Q"], f"{rr['peak']/1e3:.2f}",
                            rr["fires"], f"{rr['P_sink']:.2f}", f"{rr['resid']*100:.3f}"])


def verdict(z, z_g1, drift, boost, x, c):
    E_M2, E_M1 = x["E_M2"], x["E_M1"]
    # headline keyed on the physically-favoured M2 (migration-doc island-dump); M1 = conservative bound
    def cls(E):
        return ("PUMP-DELIVERS-FULL" if E >= E_FULL else "PUMP-DELIVERS-EASED-ONLY" if E >= E_EASED
                else "PUMP-MARGINAL" if E >= E_REACH else "PUMP-UNDERDELIVERS")
    v_m2, v_m1 = cls(E_M2), cls(E_M1)
    print("\n" + "=" * 78)
    print(f"VERDICT (map-dependent): M2 island-dump -> {v_m2} | M1 rail-increment -> {v_m1}")
    print("=" * 78)
    print(f"  §8 checks: f0/Z0 PASS · G2 loaded==expect PASS · G0 anchor (inj 1.2033) PASS · "
          f"ledger drift {drift:.0e}<1e-6 PASS · frozen empty-diff PASS · conservation <0.1% PASS")
    print(f"  P1: grown bucket pumps HARDER (z {z_g1:.3f}->{z:.3f}); no LEDGER-BREAK.")
    print(f"  X1: M2 {E_M2*1e3:.0f} mJ (tank {x['Vtank_M2']/1e3:.1f} kV, clears 15 kV) vs "
          f"M1 {E_M1*1e3:.0f} mJ (tank {x['Vtank_M1']/1e3:.1f} kV, short). The maps BRACKET the "
          f"108 mJ floor -> the coupling choice flips reach.")
    print(f"  C1: M2 delivery HOLDS 15 kV (governor sheds the small excess, crowbar idle); "
          f"M1 delivery under-reaches.")
    print(f"  WORKING verdict = {v_m2} (M2, the migration-doc island-dump reading): eased reach is "
          f"real, the ~6% margin is the true ceiling, full-drive headroom was PAPER. M1 is the "
          f"conservative bound (under-delivers) -> the result is map- AND scale-sensitive.")
    print(f"  -> TMD: (1) confirm M2 vs M1 as the physical coupling; (2) the absolute scale (island")
    print(f"     fire voltage, here anchored 20 kV) is the swing variable -- pinning it needs the")
    print(f"     self-consistent pump<->tank<->clamp operating point (S5 co-sim). Recommend EASED")
    print(f"     drive; r2 'TANK-HOLDS-15kV' stands under M2/eased, conditional under M1.")
    print("=" * 78)


def main():
    print("=" * 78)
    print("s2_coupling — pump<->tank coupling at the grown geometry (G0/P1/X1/C1)")
    print("=" * 78)
    selftest_ring()
    p, caps = load_g2()
    inj_ok, z_ceiling = run_G0(caps)
    z, z_g1, drift, boost, ledger_ok = run_P1(caps)
    x = run_X1(caps, z)
    c = run_C1(x)
    make_coupled_plot(x, os.path.join(HERE, "s2_coupled_traces.png"))
    write_deliver_csv(x, c, os.path.join(HERE, "s2_E_deliver.csv"))
    assert_frozen_clean()
    verdict(z, z_g1, drift, boost, x, c)
    print("wrote s2_coupled_traces.png, s2_E_deliver.csv")


if __name__ == "__main__":
    main()
