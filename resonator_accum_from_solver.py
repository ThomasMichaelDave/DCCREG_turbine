#!/usr/bin/env python3
"""
resonator_accum_from_solver.py
==============================
Pure-consumer visualiser for the resonator-accumulation gate (Phase 4, brief §6). Consumes
`resonator_accum` (and, through it, the `shuttle_core` kick train) and renders the comparative
evidence. No physics re-derived; the A0 regression (V1/V2/V3) is asserted before anything is drawn.

Outputs (repo dir):
  resonator_accum_Mmap.png        M over f0 x Q_loaded x rpm (the battery-grade contour M>=10/50)
  resonator_accum_routes.png      comparative route panel (DC store/retention/eta; coherent lock)
  resonator_accum_damping.png     HF-DAMPING-SPEC: residue/damping vs the T2a/T2e margins
  resonator_accum_routes.csv      comparative route table
  resonator_accum_Mmap.csv        M-map table (with implied L_RES)

Tiers: [OC] · [IR] · [RH parked, not load-bearing — firewall §2.6].
"""
import os
import csv
import math
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

import resonator_accum as ra

HERE = os.path.dirname(os.path.abspath(__file__))

# ---- A0 gate: refuse to draw unless V1/V2/V3 pass ----------------------------------- [OC]
assert ra.V1_single_kick()[1] and ra.V2_closed_form()[1] and ra.V3_regression()[1], \
    "A0 gate (V1/V2/V3) failed — refusing to draw"
print("A0 OK: V1 ringdown, V2 closed-form, V3 regression all pass")

CCOL = {'opt': '#2ca02c', 'mid': '#1f77b4', 'pess': '#d62728'}

# ============ figure 1: M-map ========================================================
f0_list = [326e3, 100e3, 50e3, 10e3, 5e3, 2e3, 1e3]
rows = ra.M_map(f0_list=f0_list, rpm_list=(3000, 10000, 30000))
fig, ax = plt.subplots(figsize=(9, 5))
for corner in ('opt', 'mid', 'pess'):
    for rpm, ls in zip((3000, 10000, 30000), ('-', '--', ':')):
        xs = [r['f0'] / 1e3 for r in rows if r['corner'] == corner and r['rpm'] == rpm]
        ms = [r['M'] for r in rows if r['corner'] == corner and r['rpm'] == rpm]
        ax.plot(xs, ms, ls, color=CCOL[corner], marker='o', ms=3,
                label=f"{corner} {rpm}rpm")
ax.axhline(10, color='#333', lw=1.0, label='M=10 (battery)')
ax.axhline(50, color='#333', lw=0.8, ls='--', label='M=50')
ax.axhline(0.15, color='#999', lw=0.8, ls=':')
ax.set_xscale('log'); ax.set_yscale('log')
ax.set_xlabel("tank f0 [kHz] (log)"); ax.set_ylabel("M = Q_loaded·PRF/(2π·f0)")
ax.set_title("Incoherent figure of merit M: battery grade (M≥10) needs a kHz-class f0 redesign; "
             "the 326 kHz tank sits at M≈0.06–0.15", loc='left', fontsize=9.5)
ax.legend(fontsize=7, ncol=3); ax.grid(True, which='both', alpha=0.25)
fig.tight_layout()
f1 = os.path.join(HERE, "resonator_accum_Mmap.png"); fig.savefig(f1, dpi=140); plt.close(fig)

# ============ figure 2: comparative routes ===========================================
dc = ra.dc_route()
v5 = ra.V5_lock()
fig, axes = plt.subplots(1, 2, figsize=(12, 4.6))
# left: DC store + retention by corner
axL = axes[0]
corners = ['opt', 'mid', 'pess']
taus = [next(r['tau_leak_h'] for r in dc['rows'] if r['corner'] == c) for c in corners]
etas = [next(r['eta'] for r in dc['rows'] if r['corner'] == c) for c in corners]
axL.bar(corners, taus, color=[CCOL[c] for c in corners], alpha=0.8)
for i, (c, e) in enumerate(zip(corners, etas)):
    axL.text(i, taus[i], f"η={e:.3f}", ha='center', va='bottom', fontsize=8)
axL.set_ylabel("self-discharge τ_leak [hours]")
axL.set_title(f"DC route: store {dc['E_store']*1e3:.0f} mJ on C_R; retention + transfer η "
              f"(ledger {dc['ledger_ok']})", loc='left', fontsize=9.5)
axL.grid(True, axis='y', alpha=0.25)
# right: coherent lock — current vs battery-grade
axR = axes[1]
rn = v5[2]['rows']; rb = v5[2]['rows_bg']
axR.plot([x['kappa'] for x in rn], [x['ratio'] for x in rn], '-o', color='#888',
         label=f"current 326kHz (M≪1): no lock")
axR.plot([x['kappa'] for x in rb], [x['ratio'] for x in rb], '-o', color='#1f77b4',
         label=f"battery-grade 2kHz: lock κ≥{v5[2]['kappa_threshold_batterygrade']}")
axR.axhline(3.0, color='#c33', lw=1.0, ls='--', label='V5 lock threshold (3×)')
axR.set_yscale('log'); axR.set_xlabel("coupling κ"); axR.set_ylabel("energy / diffusive baseline")
axR.set_title("Coherent injection-locking: impossible at the current lossy tank, viable after the "
              "kHz redesign", loc='left', fontsize=9.5)
axR.legend(fontsize=8); axR.grid(True, alpha=0.25)
fig.tight_layout()
f2 = os.path.join(HERE, "resonator_accum_routes.png"); fig.savefig(f2, dpi=140); plt.close(fig)

# ============ figure 3: HF-damping spec ==============================================
fig, ax = plt.subplots(figsize=(8, 4.4))
for corner in ('opt', 'mid', 'pess'):
    hf = ra.hf_damping_spec(corner)
    ds = [r['damping'] for r in hf['rows']]
    vr = [r['v_res'] for r in hf['rows']]
    ax.plot(ds, vr, '-o', color=CCOL[corner],
            label=f"{corner}: f_HF={hf['f_HF']}, min damping={hf['min_damping']}×")
ax.axhline(ra.MARGIN_T2E, color='#c33', lw=1.0, ls='--', label=f'T2e margin {ra.MARGIN_T2E}')
ax.axhline(ra.MARGIN_T2A, color='#e80', lw=1.0, ls=':', label=f'T2a margin {ra.MARGIN_T2A}')
ax.set_xscale('log', base=2); ax.set_xlabel("HF damping factor (×)")
ax.set_ylabel("residue / operating overvoltage")
ax.set_title("HF-DAMPING-SPEC: minimum damping so the ring residue stays below the gap-trigger "
             "margins (firewall-consistent: bounds HF from above)", loc='left', fontsize=9.0)
ax.legend(fontsize=8); ax.grid(True, which='both', alpha=0.25)
fig.tight_layout()
f3 = os.path.join(HERE, "resonator_accum_damping.png"); fig.savefig(f3, dpi=140); plt.close(fig)

# ============ tables =================================================================
rt = os.path.join(HERE, "resonator_accum_routes.csv")
with open(rt, "w", newline="") as fh:
    w = csv.writer(fh)
    w.writerow(["route", "corner", "metric", "value", "note"])
    for r in dc['rows']:
        w.writerow(["DC", r['corner'], "E_store_mJ", f"{r['E_store']*1e3:.2f}", "1/2 C_R V^2 @20kV"])
        w.writerow(["DC", r['corner'], "tau_leak_h", f"{r['tau_leak_h']:.3f}", "mica rho_v cited"])
        w.writerow(["DC", r['corner'], "transfer_eta", f"{r['eta']:.4f}", "half-cycle LC, Q_loaded"])
    M0 = ra.M_factor(ra.q_loaded(ra.Q_UPPER, 'mid'), 300.0, ra.F0)
    w.writerow(["incoherent", "mid", "M_operating", f"{M0:.3f}", "326kHz, sub-battery"])
    for r in [x for x in rows if x['ge10'] and x['corner'] == 'mid']:
        w.writerow(["incoherent", "mid", "M_ge10_triple",
                    f"f0={r['f0']/1e3:.0f}kHz rpm={r['rpm']} M={r['M']:.1f}",
                    f"L_implied={r['L_implied']*1e3:.1f}mH"])
    w.writerow(["coherent", "mid", "kappa_lock_current", str(v5[2]['kappa_threshold']), "no lock @326kHz"])
    w.writerow(["coherent", "mid", "kappa_lock_batterygrade",
                str(v5[2]['kappa_threshold_batterygrade']), "lock @2kHz"])

mm = os.path.join(HERE, "resonator_accum_Mmap.csv")
with open(mm, "w", newline="") as fh:
    w = csv.writer(fh)
    w.writerow(["corner", "Q_loaded", "f0_kHz", "rpm", "PRF_Hz", "M", "L_implied_mH", "ge10", "ge50"])
    for r in rows:
        w.writerow([r['corner'], f"{r['Qloaded']:.0f}", f"{r['f0']/1e3:.1f}", r['rpm'],
                    f"{r['prf']:.0f}", f"{r['M']:.3f}", f"{r['L_implied']*1e3:.2f}",
                    r['ge10'], r['ge50']])

# verdict (consumer recompute) + self-asserts
res = ra.run_accum_campaign(verbose=False)
assert res['verdict'] in ('ACCUM-DC-PREFERRED', 'ACCUM-INCOHERENT-VIABLE',
                          'ACCUM-COHERENT-VIABLE', 'ACCUM-BLOCKED')
assert all(os.path.exists(p) for p in (f1, f2, f3, rt, mm))
print(f"saved: {', '.join(os.path.basename(p) for p in (f1, f2, f3, rt, mm))}")
print(f"PRIMARY: {res['verdict']}  ·  HF-DAMPING-SPEC ≥ {res['HF']['min_damping']}× (mid)")
