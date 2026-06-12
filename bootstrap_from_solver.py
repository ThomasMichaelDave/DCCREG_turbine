#!/usr/bin/env python3
"""
bootstrap_from_solver.py
========================
Pure-consumer visualiser for the Phase-5 bootstrap gate (self-start thresholds + seeder spec).
Consumes `shuttle_core`'s bootstrap campaign functions; no physics re-derived. The B0 gate
(spark regression + high-V limit) is asserted before anything is drawn; the frozen
`reference/doubler_core.py` is untouched.

Outputs (repo dir):
  bootstrap_threshold_map.png   V_seed x rpm classification {no-fire / fire-and-decay / growth},
                                three corners, with V_floor and V_sustain(rpm) overlaid
  bootstrap_trajectory_atlas.png  spin-up trajectories (seed at standstill / intermediate / full)
  bootstrap_capture_window.png  capture probability vs V_inj (the seeder spec), mid + pess
  bootstrap_seeder_spec.csv     the deliverable (V_inj, Q_inj, node, retention floor) table

Tiers: [OC] · [IR].
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

# ---- B0 gate: refuse to draw unless spark regression + high-V limit pass --------------- [OC]
assert sc.B0a_spark_regression()[1] and sc.B0b_high_v_limit()[1], "B0 gate failed — refusing to draw"
print("B0 OK: spark regression + high-V limit pass")

CORNERS = ('opt', 'mid', 'pess')
CLS_COL = {'no-fire': '#cccccc', 'fire-and-decay': '#e8a33d', 'growth': '#2ca02c'}
CCOL = {'opt': '#2ca02c', 'mid': '#1f77b4', 'pess': '#d62728'}

# ---- consume the threshold map -------------------------------------------------------- [OC]
tm = sc.B1_threshold_map(corners=CORNERS, seed=0)
Vs, rpms = tm['Vs'], tm['rpms']

# ============ figure 1: two-threshold map ============================================
fig, axes = plt.subplots(1, 3, figsize=(14, 4.6), sharey=True)
for ax, c in zip(axes, CORNERS):
    for ri, rpm in enumerate(rpms):
        for Vi, (V, outcome) in enumerate(tm['grid'][c][rpm]):
            ax.scatter(rpm, V, s=70, marker='s', color=CLS_COL[outcome],
                       edgecolors='none')
    # overlay V_floor (lowest seed that ever fires) and V_sustain(rpm)
    vf = tm['vfloor'][c]
    if vf:
        ax.axhline(vf, color='#333', lw=1.2, ls='--', label=f"V_floor≈{vf:.0f}V")
    vs_pts = [(rpm, tm['vsustain'][c][rpm]) for rpm in rpms if tm['vsustain'][c][rpm]]
    if vs_pts:
        xr, yr = zip(*vs_pts)
        ax.plot(xr, yr, '-o', color='#000', lw=1.4, ms=4, label="V_sustain(rpm)")
    ax.set_xscale('log'); ax.set_yscale('log')
    ax.set_title(f"{c} corner", fontweight='bold'); ax.set_xlabel("rpm (log)")
    ax.legend(fontsize=8, loc='upper right')
axes[0].set_ylabel("seed voltage V_seed [V] (log)")
# legend for the regions
handles = [plt.Line2D([0], [0], marker='s', color='w', markerfacecolor=CLS_COL[k], ms=10, label=k)
           for k in ('no-fire', 'fire-and-decay', 'growth')]
fig.legend(handles=handles, loc='lower center', ncol=3, fontsize=9, frameon=False)
fig.suptitle("Two-threshold startup map: V_floor (first conduction) < V_sustain (growth); "
             "V_sustain rises as rpm falls (the retention race)", fontsize=10.5)
fig.tight_layout(rect=(0, 0.06, 1, 0.95))
f1 = os.path.join(HERE, "bootstrap_threshold_map.png"); fig.savefig(f1, dpi=140); plt.close(fig)

# ============ figure 2: spin-up trajectory atlas =====================================
tr = sc.B2_trajectories('mid', V_seed=2000.0, seeds=range(6))
fig, ax = plt.subplots(figsize=(9, 4.4))
# representative rail trajectories for each injection point
def ramp(start, rate):
    return lambda cyc: min(3000.0, start + rate * cyc)
cases = {'standstill (100rpm)': ramp(100.0, 60.0), 'intermediate (1000rpm)': ramp(1000.0, 60.0),
         'full-speed (3000rpm)': ramp(3000.0, 0.0)}
for (name, rp), col in zip(cases.items(), ('#d62728', '#1f77b4', '#2ca02c')):
    P = sc.make_params_boot('mid', rpm=100.0); P.seed = 0
    res = sc.boot_run(2000.0, P, rpm_ramp=rp)
    ax.plot(res['rails'], color=col, lw=1.8, label=f"{name} -> {res['outcome']}")
ax.set_yscale('log'); ax.set_xlabel("cycle"); ax.set_ylabel("rail |V1|+|V4| [V] (log)")
ax.set_title("Spin-up trajectories (2 kV seed): injection at standstill loses the retention race; "
             "intermediate/full-speed capture into growth", loc='left', fontsize=9.5)
ax.legend(fontsize=8); ax.grid(True, which='both', alpha=0.25)
fig.tight_layout()
f2 = os.path.join(HERE, "bootstrap_trajectory_atlas.png"); fig.savefig(f2, dpi=140); plt.close(fig)

# ============ figure 3: capture window (seeder spec) ================================
b3_mid = sc.B3_seeder_spec('mid', seeds=range(20), node=1)
b3_pess = sc.B3_seeder_spec('pess', seeds=range(20), node=1)
b3_n23 = sc.B3_seeder_spec('mid', seeds=range(20), node=2)
fig, ax = plt.subplots(figsize=(9, 4.4))
for spec, col, lbl in ((b3_mid, '#1f77b4', 'mid node 1/4 (Ca)'),
                       (b3_pess, '#d62728', 'pess node 1/4 (Ca)'),
                       (b3_n23, '#7d3cb5', 'mid node 2/3 (Cb)')):
    ax.plot([r['V'] for r in spec['rows']], [r['capture'] * 100 for r in spec['rows']],
            '-o', color=col, ms=4, label=lbl)
ax.axhline(99, color='#333', lw=1.0, ls='--', label='99% capture')
if b3_mid['spec_V']:
    ax.axvline(b3_mid['spec_V'], color='#1f77b4', lw=0.8, ls=':')
ax.set_xscale('log'); ax.set_xlabel("injection voltage V_inj [V] (log)")
ax.set_ylabel("capture probability [%] (≥20 seeds)")
ax.set_title(f"Seeder spec: ≥99% capture at V_inj≈{b3_mid['spec_V']:.0f}V "
             f"(Q≈{b3_mid['Q_inj']*1e9:.1f}nC on Ca) at the mid corner", loc='left', fontsize=9.5)
ax.legend(fontsize=8); ax.grid(True, which='both', alpha=0.25)
fig.tight_layout()
f3 = os.path.join(HERE, "bootstrap_capture_window.png"); fig.savefig(f3, dpi=140); plt.close(fig)

# ============ seeder-spec table ======================================================
floor = sc.B4_retention_floor()
st = os.path.join(HERE, "bootstrap_seeder_spec.csv")
with open(st, "w", newline="") as fh:
    w = csv.writer(fh)
    w.writerow(["corner", "V_floor_seed", "V_sustain_fullspeed", "seeder_V_inj", "seeder_Q_inj_nC",
                "node", "retention_floor_rpm"])
    for c in CORNERS:
        spec = sc.B3_seeder_spec(c, seeds=range(20), node=1)
        vf = tm['vfloor'][c]
        vs = tm['vsustain'][c][rpms[-1]]
        w.writerow([c, f"{vf:.0f}" if vf else "none", f"{vs:.0f}" if vs else "none",
                    f"{spec['spec_V']:.0f}" if spec['spec_V'] else "none",
                    f"{spec['Q_inj']*1e9:.2f}" if spec['Q_inj'] else "none",
                    spec['node'], f"{floor[c]:.0f}" if floor[c] else "none"])

# verdict from the already-consumed map/spec (no duplicate campaign run) + self-asserts
vf, vs = tm['vfloor']['mid'], tm['vsustain']['mid'][rpms[-1]]
two_threshold = (vf is not None and vs is not None and vs > vf)
verdict = 'BOOT-SEEDED' if b3_mid['spec_V'] is not None else 'BOOT-INDETERMINATE'
assert verdict in ('BOOT-SELF', 'BOOT-SEEDED', 'BOOT-BLOCKED', 'BOOT-INDETERMINATE')
assert all(os.path.exists(p) for p in (f1, f2, f3, st))
print(f"saved: {', '.join(os.path.basename(p) for p in (f1, f2, f3, st))}")
print(f"VERDICT: {verdict} (two-threshold={two_threshold}; seeder {b3_mid['spec_V']:.0f}V/"
      f"{b3_mid['Q_inj']*1e9:.1f}nC)")
