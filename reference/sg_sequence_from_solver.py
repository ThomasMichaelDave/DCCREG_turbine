#!/usr/bin/env python3
"""
sg_sequence_from_solver.py
==========================
Three time-aligned panels, now DRIVEN BY THE SOLVER trace (doubler_core, the
validated mirror of the frozen solveDoubler4):

  TOP    cross-couple gap stress |V1-V3| (SG3) and |V4-V2| (SG4). The per-cycle
         PEAK heights and their cycle-over-cycle growth are the solver's actual
         node voltages and its z (here the 'device' point, z~1.20). The convex
         within-stroke rise is the varicap 1/C law (interpolation between the
         solver's two phase samples per cycle).
  MIDDLE conduction / trigger logic (SG3+SG2 stroke 1, SG4+SG1 stroke 2).
  BOTTOM the ONE physically-measurable curve: V across 5-6 at the shaft ends.
         L1 shorts the slow swing, so this is the f0 ring; each transfer kicks it
         with amplitude ~ the solver |V| at that stroke, so the ring GROWS as the
         doubler pumps. (Coupling/Q/f0 still parameters -> next build.)

MEASURABILITY: nodes 1-4 live on the free counter-rotating stator and are
unprobeable; the only galvanic access is the two rotor halves via the shaft
ends = nodes 5-6. So the calculator is DESIGN GUIDANCE; only the bottom panel
maps to a bench measurement.

Tiers: [OC] · [IR] · [RH]   STATUS: diode-ideal trajectory (unbounded growth);
in hardware the SG firing clamps this at the breakdown ceiling (next coupling).
"""
import numpy as np
import matplotlib.pyplot as plt
from doubler_core import solve_doubler4

# ---- operating point (canonical 'device' preset) --------------------------
C1min, C1max = 160.0, 1000.0
C2min, C2max = 160.0, 1000.0
Ca = Cb = 100.0; Cpar = 20.0
f_pump = 300.0                      # PRF [Hz]                         [OC]
N_show = 6                          # asymptotic cycles to display
kappa  = C1max / C1min              # varicap swing ratio (=r1)        [OC]

# ---- run the validated mirror, grab the trace -----------------------------
# iterations chosen so the show-window sits post-burn but pre-rescale (|V|<1e6)
z, rec = solve_doubler4(C1min, C1max, C2min, C2max, Ca, Cb, Cpar,
                        iterations=70, burn=60, trace=True)
by_cycle = {}
for cyc, ph, c1, c2, V in rec:
    by_cycle.setdefault(cyc, {})[ph] = V
cyc_ids = sorted(by_cycle)[-N_show:]

# per-cycle solver quantities
peakSG3 = np.array([abs(by_cycle[c]["B"][0] - by_cycle[c]["B"][2]) for c in cyc_ids])  # |V1-V3| @ C1min
peakSG4 = np.array([abs(by_cycle[c]["A"][3] - by_cycle[c]["A"][1]) for c in cyc_ids])  # |V4-V2| @ C2min
kickSG3 = np.array([abs(by_cycle[c]["B"][0]) for c in cyc_ids])                         # |V1| @ C1min
kickSG4 = np.array([abs(by_cycle[c]["A"][3]) for c in cyc_ids])                         # |V4| @ C2min
norm = max(peakSG3.max(), peakSG4.max())
peakSG3 /= norm; peakSG4 /= norm
kn = max(kickSG3.max(), kickSG4.max()); kickSG3 /= kn; kickSG4 /= kn

T = 1.0 / f_pump
t_end = N_show * T
t = np.linspace(0, t_end, 8000)
V_res = 0.04                        # post-fire residual (normalised)  [IR]
cond_win, foll_lag = 0.05, 0.012

# convex within-stroke rise: V ~ 1/C(tau), anchored residual->peak     [IR]
_s0 = 1.0                                   # 1/C at tau=0 (C=Cmax, normalised)
_s1 = 1.0 / (1.0 / kappa)                   # 1/C at tau=1 (C=Cmin) = kappa
def rise01(tau):
    s = 1.0 / (1.0 - (1.0 - 1.0 / kappa) * tau)
    return (s - _s0) / (_s1 - _s0)

def gap_trace(peaks, half):     # half=0 -> stroke1 (SG3), half=1 -> stroke2 (SG4)
    v = np.full_like(t, V_res); fires = []
    for k, pk in enumerate(peaks):
        a = (k + 0.5 * half) * T
        b = a + 0.5 * T
        tau = (t - a) / (0.5 * T)
        rng = (tau >= 0) & (tau < 1)
        v[rng] = V_res + (pk - V_res) * rise01(tau[rng])
        tf = b
        if tf <= t_end + 1e-9: fires.append(min(tf, t_end))
    return v, np.array(fires)

vSG3, firesSG3 = gap_trace(peakSG3, 0)
vSG4, firesSG4 = gap_trace(peakSG4, 1)

def pulse(fires, lag=0.0):
    y = np.zeros_like(t)
    for tf in fires:
        on = tf + lag * T
        y[(t >= on) & (t < on + cond_win * T)] = 1.0
    return y
pSG3, pSG2 = pulse(firesSG3), pulse(firesSG3, foll_lag)
pSG4, pSG1 = pulse(firesSG4), pulse(firesSG4, foll_lag)

# ---- resonator tank across 5-6: kicks grow with solver |V| -----------------
f0, Q0 = 238e3, 40.0
tau0 = Q0 / (np.pi * f0)
t_fine = np.linspace(0, t_end, 80000)
v56 = np.zeros_like(t_fine); env = np.zeros_like(t_fine)
events = [(firesSG3[k], +kickSG3[k]) for k in range(len(firesSG3))] + \
         [(firesSG4[k], -kickSG4[k]) for k in range(len(firesSG4))]
A56 = 28.0
for tf, amp in events:
    m = t_fine >= tf; dt = t_fine[m] - tf
    decay = np.exp(-dt / tau0)
    v56[m] += amp * A56 * decay * np.sin(2 * np.pi * f0 * dt)
    env[m] = np.maximum(env[m], abs(amp) * A56 * decay)

# ---- PLOT -----------------------------------------------------------------
plt.rcParams.update({"figure.facecolor": "white", "axes.facecolor": "#fbfbfd",
                     "axes.edgecolor": "#888", "font.size": 10})
fig, (axV, axL, axR) = plt.subplots(3, 1, figsize=(11, 8.8), sharex=True,
        gridspec_kw={"height_ratios": [2.7, 1.25, 1.8], "hspace": 0.13})
C_SG3, C_SG4 = "#1f77b4", "#d62728"
C_SG2, C_SG1 = "#5fa8d3", "#e8857f"
C_RES = "#7d3cb5"

def guides(ax):
    for tf in firesSG3: ax.axvline(tf*1e3, color=C_SG3, lw=0.8, alpha=0.22)
    for tf in firesSG4: ax.axvline(tf*1e3, color=C_SG4, lw=0.8, alpha=0.22)

# top
axV.plot(t*1e3, vSG3, color=C_SG3, lw=2.0, label=r"|$V_1-V_3$|  (SG3)")
axV.plot(t*1e3, vSG4, color=C_SG4, lw=2.0, label=r"|$V_4-V_2$|  (SG4)")
axV.scatter(firesSG3*1e3, peakSG3, color=C_SG3, s=40, ec="white", zorder=5)
axV.scatter(firesSG4*1e3, peakSG4, color=C_SG4, s=40, ec="white", zorder=5)
guides(axV)
# growth annotation: ratio of last two SG3 peaks ~ z per cycle
axV.annotate(f"peaks grow ×{z:.3f}/cycle\n(= solver z, 'device' point)",
             xy=(firesSG3[-1]*1e3, peakSG3[-1]), xytext=(firesSG3[-3]*1e3, 0.55),
             color=C_SG3, fontsize=9, ha="center",
             arrowprops=dict(arrowstyle="->", color=C_SG3, lw=1.0))
axV.set_ylim(0, 1.18); axV.set_ylabel("gap stress  (normalised)")
axV.set_title("Firing sequence driven by the solver — diode-ideal trajectory "
              f"(z = {z:.3f}); SG firing would clamp this at the breakdown ceiling",
              loc="left", fontweight="bold", fontsize=10.5)
axV.legend(loc="upper left", framealpha=0.9, fontsize=9)
axV.grid(True, axis="y", alpha=0.25)
axV.text(t_end*1e3*0.995, 1.10, "scale is arbitrary (solver eigenvector) — "
         "shape + growth are real, absolute kV set by operating point",
         ha="right", va="top", fontsize=7.5, color="#999")

# middle
rows = [("SG3  1→3 (triggered)", pSG3, C_SG3), ("SG2  3→rail (follower)", pSG2, C_SG2),
        ("SG4  4→2 (triggered)", pSG4, C_SG4), ("SG1  2→rail (follower)", pSG1, C_SG1)]
for i, (name, y, c) in enumerate(rows):
    base = len(rows) - 1 - i
    axL.fill_between(t*1e3, base, base + 0.78*y, step="pre", color=c, alpha=0.85)
    axL.text(-0.12, base + 0.34, name, ha="right", va="center", fontsize=8.5, color=c)
guides(axL)
for k in range(N_show):
    axL.axvspan(k*T*1e3, (k+0.5)*T*1e3, color=C_SG3, alpha=0.04)
    axL.axvspan((k+0.5)*T*1e3, (k+1)*T*1e3, color=C_SG4, alpha=0.04)
axL.set_ylim(-0.1, len(rows)); axL.set_yticks([])
axL.set_title("Conduction / trigger logic   ·   stroke 1 = blue (Cb path) · stroke 2 = red (Ca path)",
              loc="left", fontsize=9.5)

# bottom
axR.plot(t_fine*1e3,  v56, color=C_RES, lw=0.4, alpha=0.45)
axR.plot(t_fine*1e3,  env, color=C_RES, lw=1.2)
axR.plot(t_fine*1e3, -env, color=C_RES, lw=1.2)
axR.fill_between(t_fine*1e3, -env, env, color=C_RES, alpha=0.07)
axR.axhline(0, color="#bbb", lw=0.7); guides(axR)
axR.set_ylim(-A56*1.15, A56*1.15)
axR.set_ylabel("V across 5–6  (a.u.)")
axR.set_xlabel("time  [ms]   ·   the ONLY bench-measurable curve (rotor halves, via shaft ends)")
axR.set_title(f"Resonator tank 5–6: f0≈{f0/1e3:.0f} kHz ring, kicked ∝ solver |V| each transfer "
              f"→ envelope grows as the pump ramps (Q≈{Q0:.0f})", loc="left", fontsize=9.5)
axR.set_xlim(0, t_end*1e3)
axins = axR.inset_axes([0.63, 0.10, 0.35, 0.45])
tz0 = firesSG3[len(firesSG3)//2]; win = 30e-6
sel = (t_fine >= tz0 - 2e-6) & (t_fine <= tz0 + win)
axins.plot((t_fine[sel]-tz0)*1e6, v56[sel], color=C_RES, lw=1.0)
axins.axhline(0, color="#ccc", lw=0.6)
axins.set_title("f0 ring detail", fontsize=7.5)
axins.set_xlabel("µs after a fire", fontsize=7); axins.tick_params(labelsize=7)
axins.set_facecolor("#fdfcff")

fig.text(0.5, 0.005, "Curves from the validated Python mirror of the frozen solveDoubler4 "
         "(anchors reproduced). Diode-ideal; SG clamp + real tank coupling = next build.  [IR]",
         ha="center", fontsize=7.5, color="#888")
fig.tight_layout(rect=(0.10, 0.02, 1, 1))
out = "/home/claude/sg_sequence_from_solver.png"
fig.savefig(out, dpi=150, bbox_inches="tight")
print(f"z(device) = {z:.4f} ; peaks SG3 = {np.round(peakSG3,3)} ; saved {out}")
