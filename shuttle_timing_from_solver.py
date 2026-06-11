#!/usr/bin/env python3
"""
shuttle_timing_from_solver.py
=============================
Timing diagram for the flying-bucket shuttle doubler — a PURE CONSUMER of
`shuttle_core.py` (brief §5). No physics is re-derived here: the event angles,
node voltages and signed charges all come from `shuttle_core.steady_trace`, and
the continuous C(theta) curves from `shuttle_core.profiles`. The frozen
`reference/doubler_core.py` is untouched.

Shared theta axis over one sector. Panels:
  (a) C1, C2, Cx3, Cx4 with the conduction / collapse windows shaded;
  (b) node voltages V1-V4 plus the floating islands V7, V8;
  (c) cumulative per-cycle charge ledger per branch.
All six event stations are marked at their SIMULATED angles, including the
emergent SG1<->SG3b relation. Self-assertions (event count, SG3a<SG3b,
island-ledger balance, per-branch direction sign) fail loudly.

On a SHUTTLE-PUMP-CONFIRMED verdict the event-angle table is exported as
`shuttle_event_angles.csv` for the phase-plate DXF relative-angle check.

Tiers: [OC] solver-derived · [IR] display/profile choices.
"""
import os
import csv
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

import shuttle_core as sc

HERE = os.path.dirname(os.path.abspath(__file__))

# ---- authorise + pull simulated data (consumer only) ----------------------- [OC]
ok, z_anchor = sc.anchor_test()
assert ok, f"anchor failed (z={z_anchor:.4f}); refusing to draw timing on an unauthorised producer"
P = sc.Params()
trace, led = sc.steady_trace(P)
z_shuttle, _, _ = sc.shuttle_run(P, 80, 40)

# ---- self-assertions on the simulated trace (fail loudly, brief §5) -------- [OC]
labels = [r["label"] for r in trace]
assert len(trace) == 6, f"expected 6 event stations, got {len(trace)}: {labels}"
ev = {r["label"]: r for r in trace}
for need in ("SG1", "SG2", "SG3a", "SG3b", "SG4a", "SG4b"):
    assert need in ev, f"missing event {need} in {labels}"
assert ev["SG3a"]["theta"] < ev["SG3b"]["theta"], "causality: SG3a must precede SG3b"
assert ev["SG4a"]["theta"] < ev["SG4b"]["theta"], "causality: SG4a must precede SG4b"
# island ledger balance per branch (load_in == fire_out)
for br in ("A", "B"):
    L = led[br]
    rel = abs(L["load_in"] - L["fire_out"]) / max(abs(L["load_in"]), 1e-30)
    assert rel < 1e-6, f"island ledger drift branch {br}: {rel:.2e}"
# per-branch direction: forward charge into the sink (1->3, 4->2) => signed q > 0
assert ev["SG3b"]["q"] > 0, "branch A direction not 1->3 (q_D3 <= 0)"
assert ev["SG4b"]["q"] > 0, "branch B direction not 4->2 (q_D4 <= 0)"

# emergent SG1<->SG3b relation (an OUTPUT, not asserted): report the lead/lag
delta_1_3b = ev["SG3b"]["theta"] - ev["SG1"]["theta"]
delta_2_4b = ev["SG4b"]["theta"] - ev["SG2"]["theta"]

# ---- continuous profiles over one sector (consumer feed) ------------------- [IR]
th = np.linspace(0, 1, 600, endpoint=False)
C1 = np.empty_like(th); C2 = np.empty_like(th); Cx3 = np.empty_like(th); Cx4 = np.empty_like(th)
for i, t in enumerate(th):
    C1[i], C2[i], Cx3[i], Cx4[i] = sc.profiles(t, P)

# voltage trajectories at the simulated event angles (step between stations)
order = sorted(trace, key=lambda r: r["theta"])
th_ev = np.array([r["theta"] for r in order])
Vtrace = {n: np.array([r["V"][n] for r in order]) for n in sc.NODES}

# cumulative per-branch charge ledger across the sector (forward = +)
q_events = [(r["theta"], r["label"], r["q"]) for r in order if r["q"] is not None]
cumA = []; cumB = []; ca = 0.0; cb = 0.0
for t, lab, q in q_events:
    if lab in ("SG3a", "SG3b"):
        if lab == "SG3b": ca += q          # fire into node 3 = delivered charge
        cumA.append((t, ca))
    if lab in ("SG4a", "SG4b"):
        if lab == "SG4b": cb += q
        cumB.append((t, cb))

# ---- PLOT ------------------------------------------------------------------
plt.rcParams.update({"figure.facecolor": "white", "axes.facecolor": "#fbfbfd",
                     "axes.edgecolor": "#888", "font.size": 10})
fig, (axC, axV, axQ) = plt.subplots(3, 1, figsize=(11, 9.2), sharex=True,
        gridspec_kw={"height_ratios": [2.2, 2.2, 1.6], "hspace": 0.13})

C_C1, C_C2, C_X3, C_X4 = "#1f77b4", "#d62728", "#2ca02c", "#9467bd"
EVCOL = {"SG1": "#e8857f", "SG2": "#5fa8d3", "SG3a": "#2ca02c", "SG3b": "#176917",
         "SG4a": "#9467bd", "SG4b": "#5b2d91"}

def mark_events(ax, ytext=None):
    for r in order:
        c = EVCOL[r["label"]]
        ax.axvline(r["theta"], color=c, lw=1.1, alpha=0.55, ls="--")
        if ytext is not None:
            ax.text(r["theta"], ytext, r["label"], rotation=90, color=c,
                    ha="right", va="top", fontsize=8, fontweight="bold")

# panel (a): capacitances + windows
axC.plot(th, C1, color=C_C1, lw=2.0, label=r"$C_1(\theta)$")
axC.plot(th, C2, color=C_C2, lw=2.0, label=r"$C_2(\theta)$")
axC.plot(th, Cx3, color=C_X3, lw=1.8, label=r"$C_{x3}(\theta)$ (branch A bucket)")
axC.plot(th, Cx4, color=C_X4, lw=1.8, label=r"$C_{x4}(\theta)$ (branch B bucket)")
# shade collapse windows (load->fire) per branch
axC.axvspan(sc.TH_COL0, sc.TH_COL1, color=C_X3, alpha=0.08)
axC.axvspan(sc.TH_COL0 + 0.5, sc.TH_COL1 + 0.5, color=C_X4, alpha=0.08)
mark_events(axC, ytext=axC.get_ylim()[1])
axC.set_ylabel("capacitance  [pF]")
axC.set_title(f"Shuttle timing — simulated (anchor z={z_anchor:.4f}, "
              f"$z_{{shuttle}}$={z_shuttle:.4f}); boost={P.boost_ratio():.1f}, "
              f"$L_{{RES}}$={sc.L_RES_UH:.0f} µH on the 5–6 ring (commutator-design.md §2)",
              loc="left", fontweight="bold", fontsize=10.5)
axC.legend(loc="lower center", framealpha=0.9, fontsize=8.5, ncol=2)
axC.grid(True, axis="y", alpha=0.2)

# panel (b): node voltages + islands
for n, col, lw in [(1, "#1f77b4", 2.0), (2, "#5fa8d3", 1.4), (3, "#d62728", 2.0),
                   (4, "#e8857f", 1.4), (7, "#2ca02c", 1.8), (8, "#9467bd", 1.8)]:
    style = "-" if n in (1, 2, 3, 4) else "--"
    axV.plot(th_ev, Vtrace[n], style, marker="o", ms=4, color=col, lw=lw,
             label=f"V{n}" + ("  (island)" if n in (7, 8) else ""))
mark_events(axV)
axV.axhline(0, color="#bbb", lw=0.7)
axV.set_ylabel("node voltage  (normalised eigenvector)")
axV.legend(loc="lower left", framealpha=0.9, fontsize=8.5, ncol=3)
axV.grid(True, axis="y", alpha=0.2)
axV.text(0.5, axV.get_ylim()[1]*0.96,
         f"emergent: SG1 leads SG3b by Δθ={delta_1_3b:.3f} sector · "
         f"SG2 leads SG4b by Δθ={delta_2_4b:.3f}",
         ha="center", va="top", fontsize=8.5, color="#444")

# panel (c): cumulative charge ledger per branch
if cumA:
    ta, qa = zip(*cumA); axQ.step([0] + list(ta) + [1], [0] + list(qa) + [qa[-1]],
                                  where="post", color=C_X3, lw=2.0, label="branch A  1→3 (ΣQ_D3)")
if cumB:
    tb, qb = zip(*cumB); axQ.step([0] + list(tb) + [1], [0] + list(qb) + [qb[-1]],
                                  where="post", color=C_X4, lw=2.0, label="branch B  4→2 (ΣQ_D4)")
mark_events(axQ)
axQ.axhline(0, color="#bbb", lw=0.7)
axQ.set_ylabel("cumulative delivered\ncharge per cycle  [a.u.]")
axQ.set_xlabel(r"rotor sector phase  $\theta$  (one sector = one pump cycle)")
axQ.legend(loc="upper left", framealpha=0.9, fontsize=8.5)
axQ.grid(True, axis="y", alpha=0.2)
axQ.set_xlim(0, 1)

fig.text(0.5, 0.005, "All curves/markers from shuttle_core.steady_trace + .profiles "
         "(frozen doubler_core.py untouched). Ideal-switch tier; scale is the solver "
         "eigenvector — shape, ordering and direction are the result.  [IR]",
         ha="center", fontsize=7.5, color="#888")
fig.subplots_adjust(left=0.09, right=0.98, top=0.95, bottom=0.07, hspace=0.13)
out_png = os.path.join(HERE, "shuttle_timing_from_solver.png")
fig.savefig(out_png, dpi=150, bbox_inches="tight")

# ---- verdict gate + event-angle CSV export (brief §5, §6) ------------------
confirmed = (z_shuttle > 1.0 + 1e-3 and ok and ev["SG3b"]["q"] > 0 and ev["SG4b"]["q"] > 0)
verdict = "SHUTTLE-PUMP-CONFIRMED" if confirmed else "NOT-CONFIRMED"

if confirmed:
    out_csv = os.path.join(HERE, "shuttle_event_angles.csv")
    win = {"SG1": (sc.TH_RET, sc.TH_LOAD), "SG3a": (sc.TH_LOAD, sc.TH_COL0),
           "SG3b": (sc.TH_COL0, sc.TH_COL1),
           "SG2": (sc.TH_RET + 0.5, sc.TH_LOAD + 0.5),
           "SG4a": (sc.TH_LOAD + 0.5, sc.TH_COL0 + 0.5),
           "SG4b": (sc.TH_COL0 + 0.5, sc.TH_COL1 + 0.5)}
    with open(out_csv, "w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["event", "theta_sector", "theta_deg_60", "window_start", "window_end",
                    "signed_charge", "branch_direction"])
        for r in order:
            lab = r["label"]; w0, w1 = win[lab]
            br = "1->3" if lab in ("SG1", "SG3a", "SG3b") else "4->2"
            q = "" if r["q"] is None else f"{r['q']:.6e}"
            # one sector = 60 deg of C1's 360 deg electrical (max->min->max spans 60 deg)
            w.writerow([lab, f"{r['theta']:.4f}", f"{r['theta']*60:.3f}",
                        f"{w0:.4f}", f"{w1:.4f}", q, br])
    print(f"event-angle table -> {out_csv}")

print(f"anchor z={z_anchor:.4f}  z_shuttle={z_shuttle:.4f}")
print("events (θ): " + " · ".join(f"{r['label']}={r['theta']:.3f}" for r in order))
print(f"emergent Δθ(SG1→SG3b)={delta_1_3b:.3f}  Δθ(SG2→SG4b)={delta_2_4b:.3f}")
print(f"=> {verdict}; saved {out_png}")
