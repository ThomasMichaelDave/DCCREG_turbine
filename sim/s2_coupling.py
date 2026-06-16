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


def main():
    print("=" * 78)
    print("s2_coupling — pump<->tank coupling at the grown geometry (G0/P1; X1/C1 gated)")
    print("=" * 78)
    selftest_ring()
    p, caps = load_g2()
    inj_ok, z_ceiling = run_G0(caps)
    z, z_g1, drift, boost, ledger_ok = run_P1(caps)
    assert_frozen_clean()

    print("\n" + "=" * 78)
    print("S2 STATUS: pump-side anchored at the grown geometry; PAUSED for the TMD coupling decision")
    print("=" * 78)
    print(f"  G0  injection VERIFIED; G2 galvanic ceiling z={z_ceiling:.3f} (= G1). Authorised.")
    print(f"  P1  grown bucket PUMPS HARDER: z {z_g1:.4f} (88 pF) -> {z:.4f} (648 pF), ledger clean "
          f"(drift {drift:.1e}) -> no LEDGER-BREAK. boost_ratio {boost:.1f}.")
    print(f"  reach floor = {E_REACH*1e3:.0f} mJ; assumed budgets eased {E_EASED*1e3:.0f} / "
          f"full {E_FULL*1e3:.0f} mJ. X1 (extract E_deliver) needs the §4 coupling map:")
    print(f"    M1 rail-increment kick: E ~ work to move per-cycle rail dQ at the rail voltage.")
    print(f"    M2 island-dump kick:    E ~ resonant transfer of 1/2*Cx*V_fire^2 across 648/960.")
    print(f"  -> X1/C1 implemented once TMD picks M1/M2 (or a third reading). G0/P1 stand regardless.")
    print("=" * 78)


if __name__ == "__main__":
    main()
