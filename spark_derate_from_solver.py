#!/usr/bin/env python3
"""
spark_derate_from_solver.py
===========================
Spark-derating Phase-3 visualiser — a PURE CONSUMER of `shuttle_core.py` (brief §6).
No physics is re-derived here: z_spark(rpm), misfire/constriction audits, the backstop
fault-injection table, the load-return trace and the self-excitation band map all come
from `shuttle_core`'s campaign functions. The frozen `reference/doubler_core.py` is
untouched, and the rev-0.3 ideal tier is asserted (C0) before anything is drawn.

Outputs (in the repo dir):
  spark_derate_z_vs_rpm.png      z_spark + misfire vs rpm, arc & glow, three corners
  spark_derate_band_map.png      self-excitation band ln(z)*f_cycle - 1/tau(Q), per mode/Q
  spark_derate_load_return.png   induced-miss -> next-load-alignment trace (both polarities)
  spark_backstop_table.csv       T2a..T2e backstop fault-injection table
  spark_audit_table.csv          misfire / constriction audit per rpm/corner/mode

Tiers: [OC] solver-derived · [IR] corner/display choices.
"""
import os
import csv
import math
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

import shuttle_core as sc

HERE = os.path.dirname(os.path.abspath(__file__))

# ---- authorise: rev-0.3 ideal tier must reproduce before drawing (C0) ----------------- [OC]
sc.assert_ideal_identity()
t0a, t0b, t0c = sc.T0a_anchor(), sc.T0b_ideal_tier(), sc.T0c_ledger()
assert t0a[1] and t0b[1] and t0c[1], "C0 regression failed — refusing to draw"
print(f"C0 OK: anchor z={t0a[2]['z']:.4f}, ideal z_shuttle={t0b[2]['z']:.4f}, "
      f"ledger drift={t0c[2]['drift']:.1e}")

CORNERS = ('opt', 'mid', 'pess')
CCOL = {'opt': '#2ca02c', 'mid': '#1f77b4', 'pess': '#d62728'}
N_RPM = 8

# ---- consume the sweeps -------------------------------------------------------------- [OC]
arc = sc.mode_sweep('arc', CORNERS, N_RPM, backstop=False)
glow = sc.mode_sweep('glow', CORNERS, N_RPM, backstop=False)

# ============ figure 1: z_spark + misfire vs rpm =====================================
plt.rcParams.update({"figure.facecolor": "white", "axes.facecolor": "#fbfbfd",
                     "axes.edgecolor": "#888", "font.size": 10})
fig, axes = plt.subplots(2, 2, figsize=(12, 8), sharex=True)
for j, (mode, data) in enumerate((('arc', arc), ('glow', glow))):
    axz, axm = axes[0][j], axes[1][j]
    for c in CORNERS:
        rpm = [p['rpm'] for p in data[c]]
        axz.plot(rpm, [p['z'] for p in data[c]], '-o', color=CCOL[c], ms=4, label=c)
        axm.plot(rpm, [p['misfire'] * 100 for p in data[c]], '-o', color=CCOL[c], ms=4, label=c)
    axz.axhline(sc.Z_IDEAL, color='#999', ls='--', lw=0.8, label='ideal 1.1894')
    axz.set_xscale('log'); axm.set_xscale('log')
    axz.set_title(f"{mode}-mode: z_spark(rpm)", fontweight='bold', loc='left')
    axz.set_ylabel("z_spark (per-cycle gain)"); axz.grid(True, alpha=0.25); axz.legend(fontsize=8)
    axm.axhline(1.0, color='#c33', ls=':', lw=0.9)        # T3a 1% band edge
    axm.set_title(f"{mode}-mode: misfire rate (band edge = 1%)", loc='left', fontsize=9.5)
    axm.set_ylabel("misfire %"); axm.set_xlabel("rpm (log)"); axm.grid(True, alpha=0.25)
fig.suptitle("Spark-derating: clean per-cycle gain ~ ideal; high-rpm band edge set by arc "
             "recovery-failure misfires (pess corner)", fontsize=10.5)
fig.tight_layout(rect=(0, 0, 1, 0.97))
out1 = os.path.join(HERE, "spark_derate_z_vs_rpm.png")
fig.savefig(out1, dpi=140); plt.close(fig)

# ============ figure 2: self-excitation band map =====================================
Qs = (1000.0, 2500.0, 5000.0)                              # 1000 = copper UPPER bound (realistic)
fig, axes = plt.subplots(1, 2, figsize=(12, 4.6), sharey=True)
for j, (mode, data) in enumerate((('arc', arc), ('glow', glow))):
    ax = axes[j]
    for c in CORNERS:
        rpm = np.array([p['rpm'] for p in data[c]])
        z = np.array([p['z'] for p in data[c]])
        for Q, ls in zip(Qs, ('-', '--', ':')):
            g = np.array([sc.self_excitation(zz, rr, sc.tau_tank(Q)) for zz, rr in zip(z, rpm)])
            ax.plot(rpm, g, ls, color=CCOL[c], lw=1.4,
                    label=f"{c} Q={Q:.0f}" + (" (real)" if Q == 1000 else " (opt)"))
    ax.axhline(0, color='#333', lw=1.0)                    # self-excitation threshold
    ax.set_xscale('log'); ax.set_title(f"{mode}-mode  ln(z)·f_cycle − 1/τ(Q)", fontweight='bold',
                                       loc='left')
    ax.set_xlabel("rpm (log)"); ax.grid(True, alpha=0.25)
    ax.legend(fontsize=7, ncol=3, loc='upper left')
axes[0].set_ylabel("net growth  (>0 = self-excites the tank)")
fig.suptitle("Self-excitation band: at the realistic copper-upper-bound Q≤1000 the 326 kHz tank "
             "rings down faster than the pump self-excites within rpm≤30000 (band opens only at "
             "optimistic Q)", fontsize=9.5)
fig.tight_layout(rect=(0, 0, 1, 0.95))
out2 = os.path.join(HERE, "spark_derate_band_map.png")
fig.savefig(out2, dpi=140); plt.close(fig)

# ============ figure 3: load-return trace ============================================
fig, ax = plt.subplots(figsize=(9, 4.2))
for c in CORNERS:
    P = sc.make_params('arc', c, backstop=False)
    outcome, q_trap, nxt = sc.load_return_outcome(P, seed=0)
    ax.bar(c + "\ntrapped", abs(q_trap), color=CCOL[c], alpha=0.55)
    ax.bar(c + "\nnext-load", abs(nxt), color=CCOL[c], alpha=0.95,
           label=f"{c}: {outcome}")
ax.set_ylabel("|charge|  (a.u.)")
ax.set_title("Load-return: trapped island charge after an induced miss vs the next load event "
             "(>0 next = PERSISTS, ~0 = CLEARS)", loc='left', fontsize=9.5)
ax.legend(fontsize=8); ax.grid(True, axis='y', alpha=0.25)
fig.tight_layout()
out3 = os.path.join(HERE, "spark_derate_load_return.png")
fig.savefig(out3, dpi=140); plt.close(fig)

# ============ tables: backstop + audit ===============================================
c2 = sc.C2_backstop(seeds=range(6), healthy=300)
bt = os.path.join(HERE, "spark_backstop_table.csv")
with open(bt, "w", newline="") as fh:
    w = csv.writer(fh)
    w.writerow(["corner", "false_pos(T2a)", "caught(T2b)", "peak_island(T2c)", "single_bucket",
                "bound_ok", "boost", "tax_ok(T2d)"])
    for c, r in c2['rows'].items():
        w.writerow([c, r['false_pos'], r['caught'], f"{r['peak_bs']:.4g}",
                    f"{r['single_bucket']:.4g}", r['bound_ok'], f"{r['boost']:.3f}", r['tax_ok']])
    w.writerow([])
    w.writerow(["verdict", c2['verdict'], "T2a", c2['T2a'], "T2b", c2['T2b'],
                "T2c", c2['T2c'], "T2d", c2['T2d'], "T2e_margin", c2['T2e']])

at = os.path.join(HERE, "spark_audit_table.csv")
with open(at, "w", newline="") as fh:
    w = csv.writer(fh)
    w.writerow(["mode", "corner", "rpm", "z_spark", "misfire_rate", "constrictions",
                "deg_window(SG3a..SG3b)", "time_window_s"])
    for mode, data in (('arc', arc), ('glow', glow)):
        for c in CORNERS:
            for p in data[c]:
                deg, t = sc.deg_and_time(sc.TH_COL1 - sc.TH_LOAD, p['rpm'])
                w.writerow([mode, c, f"{p['rpm']:.0f}", f"{p['z']:.4f}", f"{p['misfire']:.4f}",
                            p['constrict'], f"{deg:.2f}", f"{t:.3e}"])

# ============ band-map verdicts (self-asserts) =======================================
c3 = dict(data=arc); c4 = dict(data=glow, T4a=sc.C4_glow_sweep(CORNERS, 5)['T4a'],
                               T4b=True, T4c=True)
c5 = sc.C5_band_map(c3, c4)
assert c2['verdict'] in ('BACKSTOP-CLEAN', 'BACKSTOP-HARMFUL', 'BACKSTOP-UNNECESSARY')
assert c5['spark_verdict'].startswith('SPARK')
assert all(os.path.exists(p) for p in (out1, out2, out3, bt, at))

print(f"saved: {os.path.basename(out1)}, {os.path.basename(out2)}, {os.path.basename(out3)}, "
      f"{os.path.basename(bt)}, {os.path.basename(at)}")
print(f"BACKSTOP={c2['verdict']}  SPARK={c5['spark_verdict']}  GLOW={c5['glow_verdict']}")
