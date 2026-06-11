#!/usr/bin/env python3
"""
d3_duty_sign_from_solver.py — D3/D4 duty-sign screen (xcap viability gate)
==========================================================================
Pure CONSUMER of reference/doubler_core.py (the frozen Python mirror of
solveDoubler4). Reads exported outputs only; never modifies the core, never
imports private symbols. Brief: xcap-duty-sign rev 0.1, charge-sign-only
screen authorised by TMD (option i): the dV-at-onset chart/self-assert is
DROPPED and replaced by the forward-bias fact (an ideal diode conducts only
forward, so sign(dV_onset) = + by the conduction condition). See
xcap-duty-sign-findings.md.

What it does
------------
1. Runs the canonical cycle (device point) to steady state, trace=True.
2. For every D3 and D4 conduction event, reconstructs the signed transferred
   charge Q_k by conserved-charge differencing on the event's SINK node,
   using only the exported `charges_from_voltages` (the sink node's only
   delivering diode in the phase it conducts is D3 / D4 — D2 / D1 are off,
   verified per event).
3. Computes per branch the sign sequence s_k = sign(Q_k) and the magnitude
   ratios |Q_k| / |Q_{k-1}|.
4. Charts a 2x2 PNG (rows = D3, D4; cols = signed Q_k, |Q_k|/|Q_{k-1}|),
   writes a machine-readable CSV, and prints the three-way determination
   (XCAP-AC-CONFIRMED / XCAP-RATCHET-BLOCKED / XCAP-INDETERMINATE).

Sign convention (matches brief §2.2 and doubler_core.DIODES):
  DIODES = [(2,0),(3,0),(1,3),(4,2)] = D1,D2,D3,D4 (anode -> cathode).
  D3 = (1->3): + Q = charge INTO node 3 = 1 -> 3 (forward).
  D4 = (4->2): + Q = charge INTO node 2 = 4 -> 2 (forward).

Tiers: [OC] solver-derived / standard charge accounting · [IR] criterion choices
"""
import os
import sys
import csv

import matplotlib
matplotlib.use("Agg")            # headless; deterministic file output
import matplotlib.pyplot as plt

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "reference"))
import doubler_core as dc        # consumer import of the frozen mirror  [OC]

# ---- canonical operating point (device preset) ---------------------------
C1MIN, C1MAX = 160.0, 1000.0
C2MIN, C2MAX = 160.0, 1000.0
CA = CB = 100.0
CPAR = 20.0
ITERS = 60                       # |V| stays < 1e6 across the whole run -> the solver's
                                 # overflow-rescale never fires (asserted below), so every
                                 # cycle's charges share ONE scale and are directly comparable.
                                 # (70 already trips the 1e6 rescale at the device point.) [IR]

# Sink-node index (0-based) and "other diode that must be OFF" check per branch.
#   D3 conducts in phase A; sink = node 3 (index 2); D2 must be off => |v3| not clamped to 0.
#   D4 conducts in phase B; sink = node 2 (index 1); D1 must be off => |v2| not clamped to 0.
SINK = {"D3": 2, "D4": 1}


def node_charge(V, C1cur, C2cur, idx):
    """Stored charge on the caps attached to node `idx+1`, via the EXPORTED
    charges_from_voltages. For the sink nodes 2 and 3 this is independent of
    C1/C2 (node 2 -> Ca,Cpar ; node 3 -> Cb,Cpar), so the differencing is
    robust to which cap config is passed. [OC]"""
    return float(dc.charges_from_voltages(V, C1cur, C2cur, CA, CB, CPAR)[idx])


def collect_events():
    """Run the cycle and reconstruct per-event signed transferred charge."""
    z, rec = dc.solve_doubler4(C1MIN, C1MAX, C2MIN, C2MAX, CA, CB, CPAR,
                               iterations=ITERS, burn=ITERS // 2, trace=True)
    # index records by (cycle, phase)
    by = {}
    maxabs = 0.0
    for cyc, ph, c1, c2, V in rec:
        by[(cyc, ph)] = (c1, c2, V)
        maxabs = max(maxabs, max(abs(v) for v in V))
    assert maxabs < 1e6, f"solver rescale fired (max|V|={maxabs:.3e}); lower ITERS"

    n = max(c for (c, _ph) in by)
    events = {"D3": [], "D4": []}
    for c in range(1, n + 1):      # need previous phase-A for D4; start at cycle 1
        cB1, cB2, VB = by[(c, "B")]
        cA1, cA2, VA = by[(c, "A")]
        _pA1, _pA2, VprevA = by[(c - 1, "A")]

        # D3 (phase A, sink node 3): charge into node 3 between onset (= end of
        # phase B, the solver's conserved Q for phase A) and post-phase-A. [OC]
        q3_before = node_charge(VB, cB1, cB2, 2)
        q3_after = node_charge(VA, cA1, cA2, 2)
        Q_D3 = q3_after - q3_before
        d2_off = abs(VA[2]) > 1e-9 * (max(abs(v) for v in VA) + 1e-30)  # v3 not clamped to ground

        # D4 (phase B, sink node 2): onset = end of previous phase A. [OC]
        q2_before = node_charge(VprevA, _pA1, _pA2, 1)
        q2_after = node_charge(VB, cB1, cB2, 1)
        Q_D4 = q2_after - q2_before
        d1_off = abs(VB[1]) > 1e-9 * (max(abs(v) for v in VB) + 1e-30)  # v2 not clamped to ground

        events["D3"].append({"cycle": c, "phase": "A", "Q": Q_D3, "sink_ok": d2_off})
        events["D4"].append({"cycle": c, "phase": "B", "Q": Q_D4, "sink_ok": d1_off})
    return z, events


def sgn(x, eps=1e-12):
    return 0 if abs(x) <= eps else (1 if x > 0 else -1)


def steady_window(evs, tol=0.01, run=3, min_win=20):
    """[IR, adjustable] The diode-ideal pump grows x z each cycle, so there is no
    fixed steady-state magnitude; the convergence criterion is applied to the
    per-branch cycle-over-cycle charge-magnitude RATIO |Q_k|/|Q_{k-1}| (which
    converges to the constant z), not the raw magnitude. Steady = the ratio is
    within `tol` relative change for `run` consecutive cycles for BOTH branches;
    then take >= `min_win` further cycles as the analysis window."""
    def ratios(branch):
        Q = [e["Q"] for e in evs[branch]]
        return [abs(Q[k]) / abs(Q[k - 1]) if abs(Q[k - 1]) > 0 else float("nan")
                for k in range(1, len(Q))]
    r3, r4 = ratios("D3"), ratios("D4")
    onset = None
    for i in range(run, min(len(r3), len(r4))):
        ok = all(abs(r[j] - r[j - 1]) <= tol * abs(r[j - 1])
                 for r in (r3, r4) for j in range(i - run + 1, i + 1))
        if ok:
            onset = i + 1  # ratio index i corresponds to event index i+1
            break
    if onset is None:
        onset = max(0, len(evs["D3"]) - min_win)
    return onset


def determine(evs, lo, hi):
    """Three pre-committed outcomes, on MEMBERSHIP/SIGN only (no dV)."""
    notes = []
    branch_const, branch_alt = {}, {}
    for b in ("D3", "D4"):
        s = [sgn(e["Q"]) for e in evs[b][lo:hi]]
        const = len(set(s)) == 1
        alt = all(s[k + 1] == -s[k] for k in range(len(s) - 1)) and len(s) >= 2
        branch_const[b], branch_alt[b] = const, alt
        notes.append(f"{b}: signs={''.join('+' if x>0 else ('-' if x<0 else '0') for x in s)}"
                     f"  ({'constant' if const else 'alternating' if alt else 'irregular'})")
    if branch_alt["D3"] and branch_alt["D4"]:
        return "XCAP-AC-CONFIRMED", notes
    if branch_const["D3"] or branch_const["D4"]:
        return "XCAP-RATCHET-BLOCKED", notes
    return "XCAP-INDETERMINATE", notes


def main():
    z, evs = collect_events()
    lo = steady_window(evs)
    hi = len(evs["D3"])
    win = hi - lo
    # ---- self-assertions (on-load) ----
    assert win >= 20, f"analysis window too short: {win} < 20 cycles"
    # forward-bias fact (replaces the dropped sign(Q)<->sign(dV) check): an ideal
    # diode conducts only forward, so EVERY event's charge sign must be + . [OC]
    viol = [(b, e["cycle"], e["Q"]) for b in ("D3", "D4")
            for e in evs[b][lo:hi] if sgn(e["Q"]) < 0]
    sink_bad = [(b, e["cycle"]) for b in ("D3", "D4")
                for e in evs[b][lo:hi] if not e["sink_ok"]]
    if viol:
        print("  [FLAG] reverse-sign events (expected forward-only):", viol)
    if sink_bad:
        print("  [FLAG] sink-node clamped (reconstruction precondition broken):", sink_bad)

    outcome, notes = determine(evs, lo, hi)

    # ---- CSV ----
    csv_path = os.path.join(HERE, "d3_duty_sign_events.csv")
    with open(csv_path, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["branch", "cycle", "phase", "Q_signed", "sign",
                    "abs_ratio_vs_prev", "in_window", "sink_off_ok"])
        for b in ("D3", "D4"):
            Q = [e["Q"] for e in evs[b]]
            for k, e in enumerate(evs[b]):
                ratio = abs(Q[k]) / abs(Q[k - 1]) if k > 0 and abs(Q[k - 1]) > 0 else ""
                w.writerow([b, e["cycle"], e["phase"], f"{e['Q']:.6e}",
                            "+" if sgn(e["Q"]) > 0 else ("-" if sgn(e["Q"]) < 0 else "0"),
                            (f"{ratio:.6f}" if ratio != "" else ""),
                            int(lo <= k < hi), int(e["sink_ok"])])

    # ---- chart (2x2; dV panels dropped per option i -> magnitude-ratio panels) ----
    fig, ax = plt.subplots(2, 2, figsize=(11, 7.2))
    fig.suptitle(f"D3/D4 duty-sign screen (device point, z={z:.3f}) — charge-sign only "
                 f"[dV dropped, option i]\nOutcome: {outcome}", fontsize=12, fontweight="bold")
    for row, (b, col) in enumerate((("D3", "#1f77b4"), ("D4", "#d62728"))):
        idx = list(range(len(evs[b])))
        Q = [e["Q"] for e in evs[b]]
        ratio = [float("nan")] + [abs(Q[k]) / abs(Q[k - 1]) if abs(Q[k - 1]) > 0 else float("nan")
                                  for k in range(1, len(Q))]
        a0, a1 = ax[row][0], ax[row][1]
        a0.axhline(0, color="#bbb", lw=0.8)
        a0.bar(idx, Q, color=col, width=0.8)
        a0.axvspan(lo - 0.5, hi - 0.5, color=col, alpha=0.08, label="analysis window")
        a0.set_title(f"{b}: signed transferred charge $Q_k$  (+ = forward)")
        a0.set_xlabel("event index (= cycle)"); a0.set_ylabel("$Q_k$ (a.u.)")
        a0.legend(fontsize=8, loc="upper left")
        a1.axhline(z, color="#888", ls="--", lw=1.0, label=f"z = {z:.3f}")
        a1.plot(idx, ratio, "o-", color=col, ms=3)
        a1.axvspan(lo - 0.5, hi - 0.5, color=col, alpha=0.08)
        a1.set_title(f"{b}: $|Q_k|/|Q_{{k-1}}|$  (steady -> z)")
        a1.set_xlabel("event index (= cycle)"); a1.set_ylabel("ratio")
        a1.legend(fontsize=8, loc="upper right")
    fig.text(0.5, 0.005,
             "Reconstructed from the frozen doubler_core trace via charges_from_voltages "
             "(conserved-charge differencing on the sink node). dV-at-onset omitted by TMD "
             "authorisation; forward-bias gives sign(dV_onset)=+ by construction.  [OC]/[IR]",
             ha="center", fontsize=7.5, color="#777")
    fig.tight_layout(rect=(0, 0.02, 1, 0.96))
    png_path = os.path.join(HERE, "d3_duty_sign_chart.png")
    fig.savefig(png_path, dpi=150)

    # ---- console summary (deterministic) ----
    print(f"device z = {z:.4f} ; events D3={len(evs['D3'])} D4={len(evs['D4'])} ; "
          f"window cycles [{lo+1}..{hi}] = {win}")
    for line in notes:
        print("  " + line)
    print(f"  reverse-sign events: {len(viol)} ; sink-clamp flags: {len(sink_bad)}")
    print(f"OUTCOME: {outcome}")
    print(f"wrote {os.path.basename(csv_path)} and {os.path.basename(png_path)}")
    return outcome


if __name__ == "__main__":
    main()
