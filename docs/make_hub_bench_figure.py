"""docs/make_hub_bench_figure.py -- writes docs/figures/hub-bench-predictions.png: what the bench test of the rings should
see (sim/hub_drift.py -> sim/hub_drift_results.json), for the rings as built (sim/hub_rings_build.py's record).
  (a) the start-up: the field at the null, cycle by cycle, as the pump charges the rings through the multiplier;
  (b) the 120 Hz swing: the field at the null and the rings over two cycles of the pump;
  (c) the drift: the field at the null over six hours as the glass, the gel, the retainer and the coupler leak;
  (d) the test's phases and what each should read.
Usage: python3 docs/make_hub_bench_figure.py
"""
import json
import os
import textwrap

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt                                   # noqa: E402
import numpy as np                                                # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
SIM = os.path.join(HERE, "..", "sim")
SURF, INK, INK2, MUTED, GRID, AXIS = "#fcfcfb", "#0b0b0b", "#52514e", "#898781", "#e1e0d9", "#c3c2b7"
C_A, C_B = "#c0392b", "#1f6fb2"
CASE_STYLE = {  # the drift cases: the design first
    "PEEK retainer, gel, 25 C": ("#0d366b", "-", 2.0),
    "PEI retainer, gel, 25 C": ("#3987e5", "-", 1.4),
    "G10 retainer, gel, 25 C": ("#86b6ef", "-", 1.4),
    "PEEK retainer, gel, 40 C glass": ("#0d366b", (0, (4, 2)), 1.3),
    "PEEK retainer, no gel (air gaps), 25 C": ("#898781", (0, (1, 1.5)), 1.3),
}
OUT = os.path.join(HERE, "figures", "hub-bench-predictions.png")


def kv(v, f="{:.1f}"):
    return f.format(v).replace("-", "−")


def style(ax, title, ylabel, xlabel=None):
    ax.set_facecolor(SURF)
    ax.set_title(title, fontsize=9.6, loc="left", color=INK)
    ax.set_ylabel(ylabel, fontsize=8.3, color=INK2)
    if xlabel:
        ax.set_xlabel(xlabel, fontsize=8.3, color=INK2)
    ax.grid(True, color=GRID, lw=0.6)
    ax.set_axisbelow(True)
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)
    for s in ("left", "bottom"):
        ax.spines[s].set_color(AXIS)
    ax.tick_params(colors=INK2, labelsize=7.8)


def at(q, t):
    return float(np.interp(t, q["t_s"], q["E_kV_cm"]))


def main():
    D = json.load(open(os.path.join(SIM, "hub_drift_results.json")))
    rec, sw = D["record"], D["swing"]
    fig = plt.figure(figsize=(16.5, 10.2), facecolor="white")
    gs = fig.add_gridspec(2, 3, width_ratios=(1, 1, 1.15), height_ratios=(1, 1.05), hspace=0.42, wspace=0.27,
                          left=0.045, right=0.985, top=0.87, bottom=0.06)
    sup = (f"ring A on {rec['n_a']} and ring B on {rec['n_cw']}" if rec["n_a"] else f"ring B on {rec['n_cw']}") + " stages"
    fig.suptitle(f"The bench test of the rings: what the field at the null should do ({sup}, {rec['V_gap_kV']:.1f} kV "
                 f"across, bands {rec['theta_p']:.1f}–{rec['theta_e']:.1f}°)", fontsize=11.8, x=0.01, ha="left", color=INK)
    fig.text(0.01, 0.915, "sim/hub_drift.py: the pump's supply in ngspice (100 pF storage, 100 GΩ per ring), the hub's finite "
             "volumes for the drift (C dV/dt + G V = b; conductivities datasheet-class [IR]). The field at the null as "
             "connected follows the DC across the rings; the leaking insulators then move it.", fontsize=8.3, color=INK2)

    # (a) the start-up
    axA = fig.add_subplot(gs[0, 0])
    t, e = np.array(sw["startup_t_s"]), np.array(sw["startup_E_kV_cm"])
    axA.plot(t, e, color=C_B, lw=1.8)
    fin = float(np.mean(e[-5:]))
    hit = int(np.nonzero(e >= 0.95 * fin)[0][0]) if np.any(e >= 0.95 * fin) else len(e) - 1
    axA.axhline(fin, color=MUTED, lw=0.9, ls=(0, (4, 2)))
    axA.plot([t[hit]], [e[hit]], "o", ms=6, mfc="none", mec=INK, mew=1.2)
    axA.annotate(f"95 % at {t[hit]:.2f} s ({hit + 1} cycles)", (t[hit], e[hit]), (10, -18), textcoords="offset points",
                 fontsize=7.4, color=INK)
    style(axA, "(a) the start-up: the pump self-excites and charges the rings\nthrough the multiplier (the lowest field "
               "each cycle)", "kV/cm at the null", "time from the seed (s)")
    axA.set_ylim(0, None)

    # (b) the 120 Hz swing
    axB = fig.add_subplot(gs[0, 1])
    tm = np.array(sw["t_ms"])
    axB.plot(tm, sw["E_kV_cm"], color="#0d366b", lw=1.8, label="the field at the null")
    axB.set_ylim(sw["E_mean_kV_cm"] - 1.5 * sw["E_pp_kV_cm"] - 0.05, sw["E_mean_kV_cm"] + 1.5 * sw["E_pp_kV_cm"] + 0.05)
    style(axB, f"(b) the 120 Hz swing: {sw['E_pp_kV_cm']:.3f} kV/cm p-p on {sw['E_mean_kV_cm']:.2f} "
               f"({100 * sw['E_pp_kV_cm'] / sw['E_mean_kV_cm']:.1f} %);\nthe AH's ampere-turns swing "
               f"{100 * (D['ah_ripple']['AT_max'] - D['ah_ripple']['AT_min']) / D['ah_ripple']['AT_mean']:.1f} % p-p "
               "(22 mF across each coil)", "kV/cm at the null", "time over two cycles (ms)")
    ax2 = axB.twinx()
    ax2.plot(tm, 1e3 * (np.array(sw["V_B_kV"]) - np.mean(sw["V_B_kV"])), color=C_B, lw=1.0, ls=(0, (3, 1.5)),
             label=f"ring B about its {kv(np.mean(sw['V_B_kV']), '+{:.1f}')} kV")
    ax2.plot(tm, 1e3 * (np.array(sw["V_A_kV"]) - np.mean(sw["V_A_kV"])), color=C_A, lw=1.0, ls=(0, (3, 1.5)),
             label=f"ring A about its {kv(np.mean(sw['V_A_kV']))} kV")
    lim = 1e3 * max(np.ptp(sw["V_B_kV"]), np.ptp(sw["V_A_kV"]))
    ax2.set_ylim(-1.6 * lim, 1.6 * lim)
    ax2.set_ylabel("V about the mean", fontsize=8.0, color=INK2)
    ax2.tick_params(colors=INK2, labelsize=7.6)
    for s in ("top",):
        ax2.spines[s].set_visible(False)
    ax2.spines["right"].set_color(AXIS)
    h1, l1 = axB.get_legend_handles_labels()
    h2, l2 = ax2.get_legend_handles_labels()
    axB.legend(h1 + h2, l1 + l2, fontsize=7.0, frameon=True, facecolor="white", edgecolor="none", framealpha=0.92,
               loc="upper right")

    # (c) the drift
    axC = fig.add_subplot(gs[1, :2])
    for q in D["drift"]:
        col, ls, lw = CASE_STYLE.get(q["name"], (INK2, "-", 1.2))
        tt = np.array(q["t_s"][1:])
        axC.plot(tt / 60.0, q["E_kV_cm"][1:], color=col, ls=ls, lw=lw,
                 label=f"{q['name']}: {q['E_kV_cm'][0]:.2f} → {at(q, 3600):.2f} (1 h) → {q['E_kV_cm'][-1]:.2f} (6 h)")
    axC.set_xscale("log")
    axC.set_xlim(1.0 / 60, 6 * 60)
    style(axC, "(c) the drift: the field at the null after switch-on, the rings held at their DC (kV/cm: at switch-on → "
               "1 h → 6 h)", "kV/cm at the null", "time after switch-on (min)")
    axC.legend(fontsize=7.2, frameon=True, facecolor="white", edgecolor="none", framealpha=0.92, loc="upper left")

    # (d) the phases and what each should read
    axT = fig.add_subplot(gs[:, 2]); axT.axis("off")
    axT.set_title("(d) the bench test (docs/bench-test-rings.md)", fontsize=9.6, loc="left", color=INK)
    d0 = D["drift"][0]
    rows = [
        ("1. hold-off", "coupons, then the sphere: ramp the DC to flashover / breakdown; partial discharge at the design "
                        "voltage", f"sets the ratings: 1 kV/mm along the glass and 5 kV/mm in the gel (the record), "
                                   f"2 / 8 to qualify more stages"),
        ("2. leakage", "each ring from a lab supply; the current to REF on an electrometer; then the multiplier's parts",
         f"≥ 100 GΩ per ring (the ledger: {D['leakage_total_ohm'] / 1e9:.0f} GΩ); the diodes and capacitors dominate"),
        ("3. DC drift", "rings on lab supplies at the record's DC; the field at the null on the probe for 6 h",
         f"{d0['E_kV_cm'][0]:.2f} kV/cm at switch-on, {at(d0, 600):.2f} at 10 min, {at(d0, 3600):.2f} at 1 h, "
         f"{d0['E_kV_cm'][-1]:.2f} at 6 h (PEEK, gel, 25 °C)"),
        ("4. the pump", "the rings on the rotor's supply: start-up, ripple, then the drift again",
         f"95 % in {t[hit]:.2f} s; {sw['E_pp_kV_cm']:.3f} kV/cm p-p at 120 Hz on {sw['E_mean_kV_cm']:.2f}"),
    ]
    y, dl = 0.96, 0.0165                                           # dl: one line of 7.5 pt text on this axis
    for ph, how, exp in rows:
        axT.text(0.0, y, ph, fontsize=8.2, color=INK, weight="bold", va="top", transform=axT.transAxes)
        y -= 1.5 * dl
        for txt, col in (("how: " + how, INK2), ("expect: " + exp, "#0d366b")):
            ln = textwrap.wrap(txt, 66)
            axT.text(0.02, y, "\n".join(ln), fontsize=7.5, color=col, va="top", transform=axT.transAxes,
                     linespacing=1.3)
            y -= dl * len(ln) + 0.6 * dl
        y -= 0.8 * dl
    notes = [
        "The probe: an electro-optic (Pockels) BGO sensor on a fibre, entering through the pumping tube at one pole along "
        "the axis, where it barely disturbs the axial field. The bench's vessel must be evacuated: air inside would carry "
        "its own ions and screen the DC in minutes.",
        "The drift is the leakage redistributing the potential along the glass and through the gel and retainer: the "
        "field moves from the electrostatic value at switch-on toward the conduction-settled value. Fit E(t) with one or "
        "two exponentials; the time constants check the conductivities, the end value their ratios.",
    ]
    axT.text(0.0, y - 0.01, "\n".join(textwrap.fill(s_, 72) for s_ in notes), fontsize=7.2, color=INK2, va="top",
             transform=axT.transAxes, linespacing=1.35)
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    fig.savefig(OUT, dpi=130, facecolor="white")
    plt.close(fig)
    print(OUT)


if __name__ == "__main__":
    main()
