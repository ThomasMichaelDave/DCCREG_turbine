#!/usr/bin/env python3
"""
xsim_from_solver.py — SPICE cross-validation comparison CONSUMER (Phase 6, brief §6).
=====================================================================================
A PURE CONSUMER: it runs the generated ngspice netlists (the independent WITNESS), parses the
`.raw` output, pulls the NATIVE values from `shuttle_core.py` (the producer), and emits the §5
comparison table (native value · SPICE value · Δ · pass/fail) + overlay plots. No physics is
re-derived here and no native module is modified (brief §2.1). The galvanic anchor
(z = 1.2033, reference/doubler_core.py) is the tiebreaker; ngspice is the witness, not the judge.

Campaign order is enforced (brief §4): X0 anchor must recover before any comparison is admitted;
the ideal tier (X1) must pass before the arc tier (X2) is reported.

Tiers: [OC] solver-derived / standard parsing · [IR] witness modelling choices.
"""
import os
import sys
import math
import subprocess

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

import shuttle_core as sc
import xsim_netgen as gen

HERE = os.path.dirname(os.path.abspath(__file__))
RAWDIR = os.path.join(HERE, ".xsim_raw")          # scratch for .raw (gitignored)
os.makedirs(RAWDIR, exist_ok=True)


# ----------------------------------------------------------------------------------------
# ngspice driver + binary .raw parser (brief X-1: parseable .raw confirmed on ngspice-42)
# ----------------------------------------------------------------------------------------
def have_ngspice():
    try:
        subprocess.run(["ngspice", "--version"], capture_output=True, check=True)
        return True
    except Exception:
        return False


def run_ngspice(netpath, rawname):
    """Batch-run a netlist, return parsed (names, data). Raises on a failed/aborted run."""
    rawpath = os.path.join(RAWDIR, rawname)
    r = subprocess.run(["ngspice", "-b", "-r", rawpath, netpath],
                       capture_output=True, text=True)
    if "aborted" in (r.stderr + r.stdout).lower():
        raise RuntimeError(f"ngspice aborted on {os.path.basename(netpath)}:\n{r.stderr[-500:]}")
    return read_raw(rawpath)


def read_raw(path):
    """Parse an ngspice binary rawfile -> (names, data[npts, nvars]). [OC]"""
    with open(path, "rb") as fh:
        raw = fh.read()
    idx = raw.find(b"Binary:\n")
    if idx < 0:
        raise RuntimeError(f"{path}: no Binary: section (run produced no data)")
    head = raw[:idx].decode("latin1")
    body = raw[idx + len(b"Binary:\n"):]
    nvars = int(_hline(head, "No. Variables:"))
    npts = int(_hline(head, "No. Points:"))
    names, invar = [], False
    for line in head.splitlines():
        if line.startswith("Variables:"):
            invar = True
            continue
        if invar:
            parts = line.split()
            if len(parts) >= 2 and parts[0].isdigit():
                names.append(parts[1])
    data = np.frombuffer(body[:npts * nvars * 8], dtype="<f8").reshape(npts, nvars)
    return names, data


def _hline(head, key):
    for line in head.splitlines():
        if line.startswith(key):
            return line.split(":", 1)[1].strip()
    raise RuntimeError(f"rawfile header missing {key}")


def col(names, data, name):
    return data[:, names.index(name)]


# ----------------------------------------------------------------------------------------
# z extraction: post-burn per-cycle growth of the rail |V1|+|V4| (matches the native metric)
# ----------------------------------------------------------------------------------------
def z_from_rail(names, data, T, n_cycles, burn_frac=0.42, win=25):
    """Sample the rail at each pump-period boundary; z = geometric-mean per-cycle ratio over a
    post-burn window (the native takes the median post-burn ratio — same invariant). [OC]"""
    t = col(names, data, "time")
    rail = np.abs(col(names, data, "v(1)")) + np.abs(col(names, data, "v(4)"))
    samp = np.array([rail[max(0, np.searchsorted(t, k * T) - 1)] for k in range(1, n_cycles)])
    ratios = samp[1:] / np.maximum(samp[:-1], 1e-30)
    lo = int(burn_frac * len(ratios))
    window = ratios[lo:lo + win]
    z_geo = float(np.exp(np.mean(np.log(np.clip(window, 1e-30, None)))))
    return z_geo, samp, ratios


# ----------------------------------------------------------------------------------------
# §5 comparison-row helper
# ----------------------------------------------------------------------------------------
class Row:
    def __init__(self, quantity, native, spice, tol, kind="abs", note=""):
        self.quantity, self.native, self.spice = quantity, native, spice
        self.tol, self.kind, self.note = tol, kind, note
        numeric = isinstance(spice, (int, float)) and isinstance(native, (int, float))
        self.delta = (spice - native) if numeric else None
        self.passed = (self.delta is not None and abs(self.delta) <= tol)

    def line(self):
        nv = "—" if self.native is None else f"{self.native:.5g}"
        sv = "—" if self.spice is None else f"{self.spice:.5g}"
        dv = "—" if self.delta is None else f"{self.delta:+.4g}"
        flag = "PASS" if self.passed else "FAIL"
        return f"  {self.quantity:30s} native={nv:>9s} spice={sv:>9s} Δ={dv:>9s} (≤{self.tol:g}) {flag}"


# ----------------------------------------------------------------------------------------
# X0 — degenerate galvanic anchor (authorises the netlist)
# ----------------------------------------------------------------------------------------
def run_x0(p):
    net, meta = gen.netlist_x0_galvanic(p)
    netpath = os.path.join(HERE, "xsim_x0_galvanic.net")
    with open(netpath, "w") as fh:
        fh.write(net)
    names, data = run_ngspice(netpath, "x0.raw")
    z_spice, samp, ratios = z_from_rail(names, data, meta["T"], meta["n_cycles"])
    z_native = sc.galvanic_z()                       # 1.2033 (consumed, not re-derived)
    row = Row("X0 anchor z (galvanic)", z_native, z_spice, 0.03,
              note="near-ideal 1-way diodes; LR short")
    return row, dict(meta=meta, samp=samp, ratios=ratios, z_spice=z_spice, z_native=z_native)


def plot_x0(x0d, path):
    """Overlay plot (brief §6): ngspice rail growth + per-cycle ratio vs the native anchor."""
    samp, ratios = x0d["samp"], x0d["ratios"]
    z_s, z_n = x0d["z_spice"], x0d["z_native"]
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(11, 4.2))
    ax1.semilogy(range(1, len(samp) + 1), samp, "-o", ms=3, color="#1f77b4")
    ax1.set_title("X0 galvanic anchor — rail |V1|+|V4| (ngspice witness)")
    ax1.set_xlabel("pump cycle"); ax1.set_ylabel("rail (log)"); ax1.grid(alpha=0.3)
    ax2.plot(range(1, len(ratios) + 1), ratios, "-o", ms=3, color="#1f77b4",
             label=f"ngspice z={z_s:.4f}")
    ax2.axhline(z_n, color="#d62728", ls="--", label=f"native anchor z={z_n:.4f}")
    ax2.axhspan(z_n - 0.03, z_n + 0.03, color="#d62728", alpha=0.12, label="±0.03 band")
    ax2.set_title("per-cycle growth ratio → z")
    ax2.set_xlabel("pump cycle"); ax2.set_ylabel("ratio"); ax2.set_ylim(1.0, 1.35)
    ax2.legend(fontsize=8); ax2.grid(alpha=0.3)
    fig.tight_layout(); fig.savefig(path, dpi=140); plt.close(fig)


# ----------------------------------------------------------------------------------------
# Native §5 reference gather (consumed from shuttle_core — never re-derived)
# ----------------------------------------------------------------------------------------
def native_references():
    """Pull every §5 native value from the producer. Cheap quantities are computed live;
    the expensive campaign quantities (arc clamp, bootstrap thresholds) are taken from the
    producer's own published constants / findings (cited), all sourced from shuttle_core."""
    refs = {}
    refs["anchor_z"] = sc.galvanic_z()                       # 1.2033
    z_ideal, _, _ = sc.shuttle_run(sc.Params(), 80, 40)
    refs["z_ideal"] = z_ideal                                # 1.18938
    tr, _ = sc.steady_trace(sc.Params())
    ang = {r["label"]: r["theta"] for r in tr}
    refs["angles"] = ang
    refs["delta"] = ang["SG3b"] - ang["SG1"]                 # 0.2175 (emergent invariant)
    # island ledger drift (hard-fail identity)
    leds = []
    V = {1: -1.0, 2: 0.0, 3: 0.0, 4: -1.0, 7: 0.0, 8: 0.0}
    for _ in range(60):
        V, led = sc.shuttle_cycle(V, sc.Params())
        leds.append(led)
        mx = max(abs(v) for v in V.values())
        if mx > 1e6:
            V = {n: v / mx for n, v in V.items()}
    refs["ledger_drift"] = sc.assert_island_ledger(leds[20:])
    # arc tier clean conduction gain at the mid corner (B0b reference)
    Pmid = sc.make_params("arc", "mid", rpm=3000.0)
    Pmid.tau_rec = 0.0
    refs["z_arc_mid"] = sc.spark_run(Pmid)[0]                # ~1.18441
    # expensive campaign quantities — cited from the producer's findings (sourced from sc)
    refs["clamp_vs_strike"] = 1.04                           # spark-derate-findings §C3 (≈1.04x)
    refs["boot_vfloor_mid"] = 187.0                          # bootstrap-findings B1 (mid)
    refs["boot_vsustain_mid"] = 437.0                        # bootstrap-findings B1 (mid@3000rpm)
    return refs


# ----------------------------------------------------------------------------------------
# Main (X0 runs; X1..X3 shuttle tiers reported with native targets — SPICE side per status)
# ----------------------------------------------------------------------------------------
BLOCKED = object()           # sentinel: ngspice witness not available for this quantity


def full_table(x0, refs):
    """Build the full §5 comparison table (brief §7: the full table, not just failures)."""
    a = refs["angles"]
    rows = [x0]
    # X1 ideal tier
    rows.append(Row("X1 z (ideal shuttle)", refs["z_ideal"], BLOCKED, 0.005))
    rows.append(Row("X1 emergent δ (SG1→SG3b)", refs["delta"], BLOCKED, 0.010))
    for lbl in ("SG1", "SG3a", "SG3b", "SG2", "SG4a", "SG4b"):
        rows.append(Row(f"X1 event angle {lbl}", a[lbl], BLOCKED, 0.010))
    rows.append(Row("X1 island ledger drift", refs["ledger_drift"], BLOCKED, 1e-6, kind="hard"))
    # X2 arc tier
    rows.append(Row("X2 z_arc (mid corner)", refs["z_arc_mid"], BLOCKED, 0.010))
    rows.append(Row("X2 clamp (× strike)", refs["clamp_vs_strike"], BLOCKED, 0.05))
    # X3 bootstrap
    rows.append(Row("X3 V_floor (mid, V)", refs["boot_vfloor_mid"], BLOCKED, 0.15 * 187,
                    note="±15%"))
    rows.append(Row("X3 V_sustain (mid@3000, V)", refs["boot_vsustain_mid"], BLOCKED,
                    0.15 * 437, note="±15%"))
    return rows


def main():
    if not have_ngspice():
        print("XSIM-BLOCKED-ENVIRONMENT: ngspice not runnable; emit artifacts for TMD-side run.")
        sys.exit(2)
    p = gen.read_params()
    print("=" * 78)
    print("xsim — SPICE cross-validation (ngspice witness vs shuttle_core native)")
    print("=" * 78)

    # ---- X0 anchor: must recover before any comparison is admitted (brief §4/§7) --------
    x0, x0d = run_x0(p)
    print("\n[X0] degenerate galvanic anchor (authorises the netlist / engine):")
    print(x0.line())
    if not x0.passed:
        print("\nX0 anchor NOT recovered — netlist unauthorised; halting (brief §7).")
        sys.exit(1)
    print("  -> anchor recovered; engine + charge-defined-cap method authorised.")
    plot_x0(x0d, os.path.join(HERE, "xsim_x0_anchor.png"))

    # ---- full §5 table: native targets + SPICE where the witness is available -----------
    refs = native_references()
    rows = full_table(x0, refs)
    # comparison CSV (the full table, machine-readable)
    import csv
    with open(os.path.join(HERE, "xsim_comparison.csv"), "w", newline="") as fh:
        cw = csv.writer(fh)
        cw.writerow(["quantity", "native", "spice", "delta", "tol", "status"])
        for r in rows:
            sp = "BLOCKED" if r.spice is BLOCKED else f"{r.spice:.6g}"
            dl = "" if r.delta is None else f"{r.delta:.6g}"
            st = "BLOCKED" if r.spice is BLOCKED else ("PASS" if r.passed else "FAIL")
            cw.writerow([r.quantity, f"{r.native:.6g}", sp, dl, r.tol, st])
    print("\n[§5] full comparison table (native value · SPICE value · Δ · pass/fail):")
    for r in rows:
        if r.spice is BLOCKED:
            nv = f"{r.native:.5g}"
            print(f"  {r.quantity:30s} native={nv:>9s} spice={'BLOCKED':>9s} "
                  f"(≤{r.tol:g}) {'BLOCKED':>6s}")
        else:
            print(r.line())

    print("\n[verdict] X0 RECOVERED (engine + method confirmed at the degenerate limit).")
    print("          X1–X3 shuttle tiers: SPICE witness BLOCKED — the quasi-static")
    print("          flying-bucket shuttle (isolated-island Cx collapse + emergent strike,")
    print("          charge-defined behavioral caps through gated one-way gaps) triggers")
    print("          ngspice timestep collapse at the load-station cap↔gap loop, or fails")
    print("          to ratchet when it runs. Named, not engineered around (brief §6).")
    print("          Native targets above stand for a refined-netlist / TMD-side re-run.")
    return rows


if __name__ == "__main__":
    main()
