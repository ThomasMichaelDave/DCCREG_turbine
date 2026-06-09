#!/usr/bin/env python3
"""
clocking_map.py  —  mechanical clocking map (polar)
===================================================
Wraps the firing sequence onto ONE mechanical revolution to guide disc layout.

Mapping (alternating-sector topology):
  - one revolution holds  Nsec/2  pump cycles  (ceil if Nsec odd)         [OC]
  - so the 4-pulse group {SG3, SG2, SG4, SG1} repeats  Nsec/2  times/rev
  - group pitch          = 360 / (Nsec/2)  = 720/Nsec   [deg mechanical]
  - the two strokes (SG3, SG4) are half a group-pitch apart
  - followers (SG2, SG1) lag their cross-couple by a small angle

Each RING = one timing disc/track (the pulses live on several discs in the
real design; this panel is their projection onto a single circle). A wedge =
where that gap's trigger feature sits, and how wide its conduction window is.
The absolute angular origin is arbitrary; the RELATIVE clocking is the output.

Tiers: [OC] geometry/clock · [IR] window/lag widths (display) · [RH] framing
"""
import numpy as np
import matplotlib.pyplot as plt

# ---- design point (Nsec ties PRF to rotation: PRF = (Nsec/2)*f_rot) -------
Nsec   = 12                         # rotor sectors (geometry block)        [OC]
PRF    = 300.0                      # pump rate [Hz]                        [OC]
N_rep  = int(np.ceil(Nsec / 2))     # pulse-groups per revolution
f_rot  = PRF / N_rep                # mechanical rev rate [Hz]
T_rev  = 1.0 / f_rot                # revolution period [s]
pitch  = 360.0 / N_rep              # group pitch [deg mechanical]
stroke_off = pitch / 2.0            # stroke-2 offset within a group
win_frac, lag_frac = 0.06, 0.05     # conduction window / follower lag (of pitch) [IR]
win = win_frac * pitch
lag = lag_frac * pitch

# ---- the four tracks: (name, base radius, colour, within-group offset) ----
GAPS = [
    ("SG1  2→rail", 3.9, "#e8857f", 0.0),               # return leads (Ca branch {D1,D3})
    ("SG3  1→3",   3.1, "#1f77b4", lag),                # cross-couple follows, after SG1 quenches
    ("SG2  3→rail", 2.3, "#5fa8d3", stroke_off),        # return leads (Cb branch {D2,D4})
    ("SG4  4→2",   1.5, "#d62728", stroke_off + lag),   # cross-couple follows, after SG2 quenches
]
RING_T = 0.6

# ---- plot -----------------------------------------------------------------
plt.rcParams.update({"figure.facecolor": "white", "font.size": 10})
fig = plt.figure(figsize=(8.4, 8.4))
ax = fig.add_subplot(111, projection="polar")
ax.set_theta_zero_location("N")
ax.set_theta_direction(-1)          # clockwise = rotation sense            [RH]
ax.set_rorigin(-0.6)
ax.set_rmax(4.8)
ax.set_yticklabels([])
ax.set_xticks(np.deg2rad(np.arange(0, 360, pitch)))
ax.set_xticklabels([f"{int(a)}°" for a in np.arange(0, 360, pitch)], fontsize=8.5)
ax.grid(color="#ccc", lw=0.6, alpha=0.7)

# faint half-pitch spokes (stroke-2 lines)
for j in range(N_rep):
    a = np.deg2rad(j * pitch + stroke_off)
    ax.plot([a, a], [1.0, 4.6], color="#bbb", lw=0.5, ls=(0, (2, 3)), alpha=0.6)

# wedges
for name, r0, col, off in GAPS:
    for j in range(N_rep):
        th = np.deg2rad(j * pitch + off)
        ax.bar(th, RING_T, width=np.deg2rad(win), bottom=r0,
               color=col, edgecolor="white", lw=0.6, align="center", zorder=4)
    # ring label at the 0-group, just outside the first wedge
    ax.text(np.deg2rad(off), r0 + RING_T / 2, "  " + name, rotation=0,
            ha="left", va="center", fontsize=8.0, color=col,
            zorder=5)

# group index labels at outer rim
for j in range(N_rep):
    a = np.deg2rad(j * pitch)
    ax.text(a, 4.75, f"g{j}", ha="center", va="center", fontsize=7.5, color="#999")

# rotation arrow
ax.annotate("", xy=(np.deg2rad(28), 4.6), xytext=(np.deg2rad(8), 4.6),
            arrowprops=dict(arrowstyle="->", color="#666", lw=1.4))
ax.text(np.deg2rad(18), 4.5, "rotation", ha="center", va="bottom",
        fontsize=8, color="#666")

# centre summary
ax.text(0, -0.6,
        f"Nsec = {Nsec}\n"
        f"groups/rev = Nsec/2 = {N_rep}\n"
        f"PRF = {PRF:.0f} Hz\n"
        f"f_rot = {f_rot:.0f} Hz   (T_rev = {T_rev*1e3:.1f} ms)\n"
        f"group pitch = {pitch:.0f}°\n"
        f"stroke offset = {stroke_off:.0f}°",
        ha="center", va="center", fontsize=9, color="#333",
        bbox=dict(boxstyle="round,pad=0.5", fc="#f4f2fb", ec="#ccc"))

ax.set_title("Mechanical clocking map — 4 pulse zones × (Nsec/2) groups per revolution\n"
             "each ring = one timing disc/track · wedge = trigger-feature angle & window",
             fontsize=10.5, fontweight="bold", pad=22)

out = "/home/claude/clocking_map.png"
fig.savefig(out, dpi=150, bbox_inches="tight")
print(f"Nsec={Nsec} groups/rev={N_rep} pitch={pitch:.1f}deg stroke_off={stroke_off:.1f}deg "
      f"f_rot={f_rot:.0f}Hz ; saved {out}")
