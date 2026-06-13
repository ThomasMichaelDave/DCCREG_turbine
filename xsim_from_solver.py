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
        self.delta = (spice - native) if (spice is not None and native is not None) else None
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


# ----------------------------------------------------------------------------------------
# Main (incremental: X0 first; X1..X3 added as tiers land)
# ----------------------------------------------------------------------------------------
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
    print("\n[X0] degenerate galvanic anchor (authorises the netlist):")
    print(x0.line())
    if not x0.passed:
        print("\nX0 anchor NOT recovered — netlist unauthorised; halting (brief §7).")
        sys.exit(1)
    print("  -> anchor recovered; netlist authorised.")

    # X1..X3 tiers are appended here as they land (campaign order enforced).
    return [x0]


if __name__ == "__main__":
    main()
