"""docs/make_core_swing_figure.py -- writes docs/figures/core-swing-waveforms.png: why each core electrode swings
asymmetrically against the shaft while the field across the core is symmetric.
The floating wiring of sim/core_field.py (each electrode coupled to node 1 / 4 through 1 nF) is restarted from its
steady state ('float ss' in sim/core_field_results.json) for 24 cycles; the last two cycles are drawn:
  (a) the pump's nodes 1 and 4, with node 1's average and the midpoint of its swing;
  (b) the electrodes against the shaft, and their common mode;
  (c) across the core, electrode A - electrode B.
The harmonics of each over the last 4 cycles go in the figure and in sim/core_swing_waveforms.json.
Usage: python3 docs/make_core_swing_figure.py
"""
import json
import os
import subprocess
import sys
import tempfile

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt                                   # noqa: E402
import numpy as np                                                # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
SIM = os.path.join(HERE, "..", "sim")
sys.path.insert(0, SIM)
import core_field as CF                                           # noqa: E402

SURF, INK, INK2, MUTED, GRID, AXIS = "#fcfcfb", "#0b0b0b", "#52514e", "#898781", "#e1e0d9", "#c3c2b7"
C_A, C_B, C_N1, C_N4, C_CM = "#c0392b", "#1f6fb2", "#1c5cab", "#86b6ef", "#898781"   # as the schematic's cones
OUT = os.path.join(HERE, "figures", "core-swing-waveforms.png")


def waves(n_cyc=24, per=4000):
    r = {q["name"]: q for q in json.load(open(os.path.join(SIM, "core_field_results.json")))["rows"]}["float ss"]
    txt, vecs, _ = CF.deck(opt="float", ic=r["ic"], n_cyc=n_cyc)
    with tempfile.TemporaryDirectory() as d:
        open(os.path.join(d, "x.cir"), "w").write(txt)
        subprocess.run(["ngspice", "-b", "x.cir"], capture_output=True, text=True, cwd=d, timeout=1800)
        raw = np.loadtxt(os.path.join(d, "out.dat"))
    t = raw[:, 0]
    c = {v: raw[:, 2 * j + 1] for j, v in enumerate(vecs)}
    T = 1.0 / CF.F
    tu = (n_cyc - 4) * T + np.arange(4 * per) * T / per                # the last 4 cycles, uniform
    u = {k[2:-1]: np.interp(tu, t, c[k]) / 1e3 for k in ("v(1)", "v(4)", "v(ka)", "v(kb)")}
    u["t_ms"] = (tu - tu[0]) * 1e3
    return u, T


def harmonics(y, n=5):
    Y = np.fft.rfft(y) / len(y) * 2                                   # 4 cycles in the window: harmonic k at bin 4k
    return [float(abs(Y[4 * k])) for k in range(1, n + 1)]


def style(ax, title, ylabel):
    ax.set_facecolor(SURF)
    ax.set_title(title, fontsize=10, loc="left", color=INK)
    ax.set_ylabel(ylabel, fontsize=8.5, color=INK2)
    ax.grid(True, color=GRID, lw=0.6)
    ax.set_axisbelow(True)
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)
    for s in ("left", "bottom"):
        ax.spines[s].set_color(AXIS)
    ax.tick_params(colors=INK2, labelsize=8)


def main():
    u, T = waves()
    v1, v4, ka, kb = u["1"], u["4"], u["ka"], u["kb"]
    d, cm = ka - kb, 0.5 * (ka + kb)
    m1, mid1 = v1.mean(), 0.5 * (v1.min() + v1.max())
    above = float(np.mean(v1 > m1))
    H = {k: harmonics(y) for k, y in (("node 1", v1), ("electrode A", ka), ("across the core", d), ("common mode", cm))}
    stats = {k: dict(min=float(y.min()), max=float(y.max()), mean=float(y.mean()))
             for k, y in (("node 1", v1), ("node 4", v4), ("electrode A", ka), ("electrode B", kb),
                          ("across the core", d), ("common mode", cm))}
    json.dump(dict(stats_kV=stats, harmonics_kV=H, node1_above_mean_fraction=above, node1_mean_kV=float(m1),
                   node1_midpoint_kV=float(mid1)), open(os.path.join(SIM, "core_swing_waveforms.json"), "w"), indent=1)

    w = u["t_ms"] < 2e3 * T                                           # draw two cycles
    t = u["t_ms"][w]
    fig, axs = plt.subplots(3, 1, figsize=(10.5, 9.2), sharex=True, facecolor="white")
    fig.subplots_adjust(left=0.085, right=0.72, top=0.89, bottom=0.07, hspace=0.34)
    fig.suptitle("The floating core electrodes: why each swings −4.4 / +2.7 kV against the shaft, while the field across "
                 "the core is symmetric", fontsize=11.2, x=0.01, ha="left", color=INK)
    fig.text(0.01, 0.935, "Stack of record (3 mm, 6 + 6, 6 mm gaps, 13.1 kV clamp), 1200 rpm relative (120 Hz); each "
             "electrode coupled through 1 nF to node 1 / 4, its DC set by its leakage (sim/core_field.py).",
             fontsize=8.3, color=INK2)

    ax = axs[0]
    ax.plot(t, v1[w], color=C_N1, lw=1.8, label="node 1")
    ax.plot(t, v4[w], color=C_N4, lw=1.4, label="node 4 (half a cycle later)")
    ax.axhline(m1, color=INK2, lw=1.0, ls=(0, (5, 3)))
    ax.axhline(mid1, color=MUTED, lw=0.9, ls=(0, (1, 2)))
    box = dict(fc=SURF, ec="none", pad=0.6, alpha=0.9)
    ax.text(t[-1], m1 + 0.25, f"node 1's average {m1:.1f} kV".replace("-", "−"), fontsize=7.6, color=INK2, ha="right",
            va="bottom", bbox=box)
    ax.text(t[-1], mid1 - 0.25, f"midpoint of its swing {mid1:.1f} kV".replace("-", "−"), fontsize=7.6, color=MUTED,
            ha="right", va="top", bbox=box)
    style(ax, f"(a) the pump's nodes: node 1 spends {100 * above:.0f} % of the cycle above its average", "kV to the shaft")
    ax.set_ylim(v1.min() - 0.6, v1.max() + 1.6)
    ax.legend(fontsize=7.8, frameon=False, loc="upper left", ncol=2)

    ax = axs[1]
    ax.plot(t, ka[w], color=C_A, lw=1.8, label="electrode A (on node 1 through 1 nF)")
    ax.plot(t, kb[w], color=C_B, lw=1.4, label="electrode B (on node 4)")
    ax.plot(t, cm[w], color=C_CM, lw=1.2, ls=(0, (2, 2)), label="their common mode, (A + B) / 2")
    ax.axhline(0.0, color=INK2, lw=0.8)
    ax.annotate(f"+{ka.max():.1f} kV", (t[-1], ka[w][-1]), (6, 0), textcoords="offset points", fontsize=7.6, color=C_A,
                va="center")
    i_min = int(np.argmin(ka[w]))
    ax.annotate(f"{ka.min():.1f} kV".replace("-", "−"), (t[i_min], ka.min()), (0, -5), textcoords="offset points",
                fontsize=7.6, color=C_A, ha="center", va="top")
    style(ax, "(b) the electrodes against the shaft: the capacitor passes node 1 less its average", "kV to the shaft")
    ax.set_ylim(ka.min() - 0.8, ka.max() + 2.2)
    ax.legend(fontsize=7.8, frameon=False, loc="upper left", ncol=3)

    ax = axs[2]
    ax.plot(t, d[w], color=INK, lw=1.8, label="A − B")
    ax.axhline(0.0, color=INK2, lw=0.8)
    for y in (d.max(), d.min()):
        ax.axhline(y, color=MUTED, lw=0.7, ls=(0, (4, 3)))
    ax.text(t[-1], d.max() + 0.3, f"+{d.max():.2f} kV", fontsize=7.6, color=INK2, ha="right", va="bottom")
    ax.text(t[-1], d.min() - 0.3, f"{d.min():.2f} kV".replace("-", "−"), fontsize=7.6, color=INK2, ha="right", va="top")
    style(ax, "(c) across the core, A − B: symmetric", "kV")
    ax.set_xlabel("time (ms), two pump cycles", fontsize=8.5, color=INK2)
    ax.set_ylim(d.min() - 1.6, d.max() + 1.6)

    rows = [("× 120 Hz", "1", "2", "3", "4")]
    for k, h in H.items():
        rows.append((k,) + tuple(f"{x:.2f}" for x in h[:4]))
    y0 = 0.86
    fig.text(0.745, y0, "Harmonic amplitudes, kV", fontsize=9, color=INK, weight="bold")
    for i, r in enumerate(rows):
        yy = y0 - 0.03 * (i + 1)
        fig.text(0.745, yy, r[0], fontsize=7.8, color=INK if i == 0 else INK2, weight="bold" if i == 0 else "normal")
        for j, x in enumerate(r[1:]):
            fig.text(0.885 + 0.034 * j, yy, x, fontsize=7.8, color=INK if i == 0 else INK2, ha="right",
                     weight="bold" if i == 0 else "normal")
    notes = [
        "Node 1 is not a sine: it rests near its top for most of the cycle and dips briefly to the clamp at minimum C. Its "
        "average therefore sits nearer the top than the midpoint.",
        "The coupling capacitor removes only that average, so each electrode swings more to the negative side than to the "
        "positive side: the 2nd harmonic.",
        "Node 4 is node 1 half a cycle later. Half a cycle reverses the odd harmonics but leaves the even ones, so in A − B "
        "the 2nd harmonic cancels and the field is symmetric.",
        "In (A + B) / 2 the fundamental cancels and the 2nd harmonic stays: both electrodes move together at 240 Hz against "
        "the shaft. That moves the core's potential, not its field.",
    ]
    import textwrap
    fig.text(0.745, y0 - 0.03 * (len(rows) + 1.2), "\n\n".join(textwrap.fill(s, 46) for s in notes), fontsize=7.7,
             color=INK2, va="top")
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    fig.savefig(OUT, dpi=140, facecolor="white")
    plt.close(fig)
    print(OUT)
    print(json.dumps(dict(above=above, mean=m1, mid=mid1, H=H, stats=stats), indent=1)[:1500])


if __name__ == "__main__":
    main()
