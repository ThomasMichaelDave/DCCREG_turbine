"""docs/make_hub_bench_figure.py -- writes docs/figures/hub-bench-predictions.png: what the bench test of the rings should
see (sim/hub_drift.py -> sim/hub_drift_results.json), for the rings as built (sim/hub_rings_build.py's record).
  (a) the start-up: the field at the null, cycle by cycle, as the pump charges the rings through the multiplier;
  (b) the 120 Hz ripple over two cycles of the pump: its nodes 1 and 4, the rings about their DC, the field at the
      null (three charts on one time axis);
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
    if rec.get("a_ref") == "shaft":
        sup = f"the symmetric supply, {rec['n_a']} + {rec['n_cw']} stages"
    else:
        sup = (f"ring A on {rec['n_a']} and ring B on {rec['n_cw']}" if rec["n_a"] else f"ring B on {rec['n_cw']}") + \
            " stages"
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

    # (b) the 120 Hz ripple, in three charts on one time axis (no twin axes): the pump's nodes, the rings, the field
    sub = gs[0, 1].subgridspec(3, 1, hspace=0.16)
    tm = np.array(sw["t_ms"])
    v1, v4 = np.array(sw["V1_kV"]), np.array(sw["V4_kV"])
    va, vb = np.array(sw["V_A_kV"]), np.array(sw["V_B_kV"])
    T_ms = 1e3 / 120.0
    i_a = [int(np.argmin(np.where((tm >= k * T_ms) & (tm < (k + 1) * T_ms), va, np.inf))) for k in (0, 1)]
    i_b = [int(np.argmax(np.where((tm >= k * T_ms) & (tm < (k + 1) * T_ms), vb, -np.inf))) for k in (0, 1)]
    axN = fig.add_subplot(sub[0])
    axN.plot(tm, v4, color=C_B, lw=1.5, label="node 4 (drives ring B's chain)")
    axN.plot(tm, v1, color=C_A, lw=1.5, label="node 1 (drives ring A's chain)")
    style(axN, f"(b) the 120 Hz ripple: {sw['E_pp_kV_cm']:.3f} kV/cm p-p on {sw['E_mean_kV_cm']:.2f} "
               f"({100 * sw['E_pp_kV_cm'] / sw['E_mean_kV_cm']:.1f} %), no swing from A to B", "kV")
    axN.legend(fontsize=6.8, frameon=True, facecolor="white", edgecolor="none", framealpha=0.92, loc="upper right",
               ncol=2)
    axN.set_ylim(min(v1.min(), v4.min()) - 1.0, max(v1.max(), v4.max()) + 3.2)
    axR = fig.add_subplot(sub[1], sharex=axN)
    axR.plot(tm, 1e3 * (vb - vb.mean()), color=C_B, lw=1.5, label=f"ring B about {kv(vb.mean(), '+{:.2f}')} kV")
    axR.plot(tm, 1e3 * (va - va.mean()), color=C_A, lw=1.5, label=f"ring A about {kv(va.mean(), '{:.2f}')} kV")
    style(axR, "", "V")
    axR.legend(fontsize=6.8, frameon=True, facecolor="white", edgecolor="none", framealpha=0.92, loc="upper right",
               ncol=2)
    lim = 1e3 * max(np.ptp(va), np.ptp(vb))
    axR.set_ylim(-1.0 * lim, 1.25 * lim)
    axE = fig.add_subplot(sub[2], sharex=axN)
    axE.plot(tm, sw["E_kV_cm"], color="#0d366b", lw=1.6)
    style(axE, "", "kV/cm", "time over two cycles of the pump (ms)")
    axE.set_ylim(sw["E_mean_kV_cm"] - 1.4 * sw["E_pp_kV_cm"], sw["E_mean_kV_cm"] + 1.4 * sw["E_pp_kV_cm"])
    for k in (0, 1):                                                   # the top-ups: ring A at node 1's low, B at node 4's high
        for ax_ in (axN, axR, axE):
            ax_.axvline(tm[i_a[k]], color=C_A, lw=0.7, ls=(0, (2, 2)))
            ax_.axvline(tm[i_b[k]], color=C_B, lw=0.7, ls=(0, (2, 2)))
    axE.annotate(f"ring A tops up, then ring B {abs(tm[i_b[0]] - tm[i_a[0]]):.2f} ms later: the ripples add",
                 (tm[i_b[0]], float(np.interp(tm[i_b[0]], tm, sw["E_kV_cm"]))), (tm[i_b[0]] + 0.6,
                 sw["E_mean_kV_cm"] + 1.05 * sw["E_pp_kV_cm"]), fontsize=6.9, color=INK2, va="center")
    for ax_ in (axN, axR):
        plt.setp(ax_.get_xticklabels(), visible=False)
    axE.set_xlim(tm[0], tm[-1])
    axE.text(1.0, -0.62, f"the AH's ampere-turns ripple "
             f"{100 * (D['ah_ripple']['AT_max'] - D['ah_ripple']['AT_min']) / D['ah_ripple']['AT_mean']:.1f} % p-p "
             "(22 mF across each coil)", transform=axE.transAxes, ha="right", fontsize=7.0, color=INK2)

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
         f"95 % in {t[hit]:.2f} s; {sw['E_pp_kV_cm']:.3f} kV/cm p-p at 120 Hz on {sw['E_mean_kV_cm']:.2f}: a "
         "steady field from B to A, no swing"),
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
