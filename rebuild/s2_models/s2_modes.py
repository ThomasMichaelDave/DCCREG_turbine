"""rebuild/s2_models/s2_modes.py -- moving the S2a model's modes away from the pump's 120 Hz (the designer, 2026-10-16:
"the 120 Hz margins, how do we move away from that frequency? extra tabs on Ca and Cb? hyperaccelerate our way outside
of that band? ..."; then "yes, run s2_modes and bring the fixes into the model").

1. The electrostatic drive on every plate and vane [OC]: the pull across a gap is eps0 V^2 / (2 g^2) times the area
   facing; a plate between two neighbours of the other net is pulled alike both ways, so only a plate with one
   such neighbour is driven, at 120 Hz and its harmonics (the force goes as V^2). The others feel only the residual of
   a tolerance: a plate delta off centre in its gaps keeps 4 delta / g of one side's pull [OC: first order], at
   delta = 0.2 mm [IR].
2. The driven parts' modes by finite elements on their own solids [IR: the method]: each part's solid from
   rebuild/s2_models/s2_geometry.py, meshed by Gmsh (second-order tetrahedra), solved by CalculiX (*FREQUENCY), both
   as FreeCAD 1.1 ships them; each part held where the model holds it (the comb tubes' holes for the Ca plates and
   the rotor vanes, and the rotor vanes' rings on the cover; the tie rods' holes for the stator vanes). Variants:
   the thickness of the driven parts.
3. The rotor's bending modes against the couplings' diameter (rebuild/s2_models/s2_structure.py's beam model).
4. A Campbell check: the drive at 6 x the relative rotation (6 sectors), its 2nd and 3rd harmonics, across the shaft
   speed 400-800 rpm (the counter-rotor at the same speed the other way), against every mode; the windows where all
   three clear every mode by +-20 % [IR: the margin].
Writes rebuild/s2_models/s2_modes_results.json and s2-modes-campbell.png.
Usage: python3 rebuild/s2_models/s2_modes.py [--quick]   (the FE sweep, the rotor, about 15 minutes)
       python3 rebuild/s2_models/s2_modes.py --campbell   (the Campbell check of the choice, from its results)
"""
import json
import math
import os
import re
import subprocess
import sys
import tempfile

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "sim"))
sys.path.insert(0, HERE)
import s2_geometry as G  # noqa: E402
import s2_structure as SS  # noqa: E402
import tube_geometry as TG  # noqa: E402

FC_BIN = os.path.join(os.environ.get("LOCALAPPDATA", ""), "Programs", "FreeCAD 1.1", "bin")
GMSH, CCX = os.path.join(FC_BIN, "gmsh.exe"), os.path.join(FC_BIN, "ccx.exe")
EPS0 = 8.854e-12
DELTA = 0.2e-3                       # the gap tolerance, m [IR]
MARGIN = 0.20                        # the modes' clearance from every drive line [IR]
AL = dict(E=69000.0, nu=0.33, rho=2.7e-9)   # N/mm2, t/mm3 (the mm-N-t system)


# ------------------------------------------------------------------------------------------- 1. the drive per plate
def drive(m):
    V = m.V
    t, g = G.VANE["t"] * 1e-3, G.VANE["g"] * 1e-3
    A_ca = math.pi * ((G.VANE["r_out"] * 1e-3) ** 2 - (G.VANE["r_in"] * 1e-3) ** 2)
    A_sec = A_ca * G.VANE["n_sec"] * G.VANE["wr"] / 360.0          # the sectors' overlap at its largest [OC]
    pk = lambda a, b: G.ML.volt(V, a, b)["pk"] * 1e3                # noqa: E731
    p = lambda U: 0.5 * EPS0 * (U / g) ** 2                         # noqa: E731
    rows = []
    stack = [("Ca_06", "2"), ("Ca_05", "1"), ("Ca_04", "2"), ("Ca_03", "1"), ("Ca_02", "2"), ("Ca_01", "1")] + \
        [(f"C1_{'r' if k % 2 == 0 else 's'}{k + 1:02d}", "1" if k % 2 == 0 else "0") for k in range(G.VANE["n_vanes"])]
    for i, (nm, net) in enumerate(stack):
        A = A_ca if nm.startswith("Ca") else A_sec
        sides = []
        for j in (i - 1, i + 1):
            if 0 <= j < len(stack):
                nb, nn = stack[j]
                gap_ok = not ((nm == "Ca_01" and nb.startswith("C1")) or (nm.startswith("C1") and nb == "Ca_01"))
                U = pk(net, nn) if net != nn else 0.0
                sides.append(p(U) * A if gap_ok or U > 0 else 0.0)
            else:
                sides.append(0.0)
        net_F = abs(sides[0] - sides[1])
        resid = 4 * DELTA / g * max(sides) if sides[0] > 0 and sides[1] > 0 else 0.0
        rows.append(dict(part=nm, net=net, pull_each_side_N=sides, net_N=net_F, tolerance_residual_N=resid,
                         driven=bool(net_F > 0.05 * max(sides + [1e-12]))))
    return rows


# ------------------------------------------------------------------------------------------- 2. finite elements
def fe_modes(shape, fixed_pred, label, n=6, clmax=3.0):
    """mesh the solid with Gmsh, fix the nodes fixed_pred(x, y, z) picks, solve CalculiX's *FREQUENCY; the first n."""
    from OCP.BRepTools import BRepTools
    d = tempfile.mkdtemp(prefix="s2modes_")
    brep = os.path.join(d, "part.brep")
    BRepTools.Write_s(shape, brep)
    inp = os.path.join(d, "mesh.inp")
    r = subprocess.run([GMSH, brep, "-3", "-order", "2", "-clmax", f"{clmax}", "-format", "inp", "-o", inp],
                       capture_output=True, text=True, timeout=1800)
    if not os.path.exists(inp):
        return dict(label=label, error=(r.stdout + r.stderr)[-400:])
    txt = open(inp).read()
    nodes = {}
    blk = re.search(r"\*NODE\s*\n(.*?)\n\*", txt, re.S | re.I).group(1)
    for ln in blk.splitlines():
        q = ln.split(",")
        if len(q) >= 4:
            nodes[int(q[0])] = (float(q[1]), float(q[2]), float(q[3]))
    # keep only the C3D10 elements (Gmsh writes the surface triangles too)
    parts = re.split(r"(?=\*ELEMENT)", txt, flags=re.I)
    head = parts[0]
    vol = "".join(p for p in parts[1:] if re.search(r"type\s*=\s*C3D10", p, re.I))
    vol = re.sub(r"ELSET\s*=\s*\w+", "ELSET=EALL", vol, flags=re.I)
    fixed = [k for k, x in nodes.items() if fixed_pred(*x)]
    if not fixed:
        return dict(label=label, error="no fixed nodes")
    job = os.path.join(d, "job.inp")
    with open(job, "w") as f:
        f.write(head + vol)
        f.write("*NSET,NSET=FIX\n")
        for i in range(0, len(fixed), 12):
            f.write(", ".join(str(k) for k in fixed[i:i + 12]) + "\n")
        f.write(f"*MATERIAL,NAME=AL\n*ELASTIC\n{AL['E']},{AL['nu']}\n*DENSITY\n{AL['rho']}\n"
                "*SOLID SECTION,ELSET=EALL,MATERIAL=AL\n*BOUNDARY\nFIX,1,3\n"
                f"*STEP\n*FREQUENCY\n{n}\n*END STEP\n")
    r = subprocess.run([CCX, "-i", "job"], capture_output=True, text=True, timeout=3600, cwd=d)
    dat = os.path.join(d, "job.dat")
    if not os.path.exists(dat):
        return dict(label=label, error=(r.stdout + r.stderr)[-400:])
    t = open(dat).read()
    sec = t.split("E I G E N V A L U E   O U T P U T")[1] if "E I G E N V A L U E   O U T P U T" in t else ""
    f_hz = []
    for ln in sec.splitlines():
        q = ln.split()
        if len(q) >= 4 and q[0].isdigit():
            try:
                f_hz.append(float(q[3]))                            # the cycles/time column
            except ValueError:
                pass
    # the effective modal mass along z (the pull's direction): a uniform pull drives a mode in proportion to it, so
    # the modes that carry z-mass are the ones the pump excites [OC: modal participation]
    mz = []
    if "E F F E C T I V E   M O D A L   M A S S" in t:
        blk = t.split("E F F E C T I V E   M O D A L   M A S S")[1]
        for ln in blk.splitlines():
            q = ln.split()
            if len(q) >= 4 and q[0].isdigit():
                try:
                    mz.append(abs(float(q[3])))
                except ValueError:
                    pass
            if ln.strip().startswith("TOTAL"):
                break
    mz = mz[:len(f_hz)]
    tot = sum(mz) if mz else 0.0
    share = [x / tot if tot else 0.0 for x in mz]
    return dict(label=label, f_Hz=f_hz[:n], z_mass_share=share[:n], n_nodes=len(nodes), n_fixed=len(fixed),
                clmax_mm=clmax, excited_Hz=[f for f, sh in zip(f_hz[:n], share[:n]) if sh >= 0.05])


def holds_at(points_xy, r_hold, also_r=None):
    """nodes within r_hold of any of the points (a hole's wall), or (also) on a radius also_r (a bore)."""
    P = np.array(points_xy)

    def pred(x, y, z):
        if np.min(np.hypot(P[:, 0] - x, P[:, 1] - y)) <= r_hold + 0.05:
            return True
        return also_r is not None and abs(math.hypot(x, y) - also_r) <= 0.05
    return pred


def part_shapes(m, t_scale):
    """the driven parts' prototypes as solids at the origin (z 0 to t), thickness t_scale x 3 mm [IR]: Ca_06 (N2, the
    first plate), Ca_01 (N1), the first rotor vane, the last stator vane; by rebuilding their prototypes."""
    ri, ro, n = G.VANE["r_in"], G.VANE["r_out"], G.VANE["n_sec"]
    t = G.VANE["t"] * t_scale
    rb, rbo = G.BAR["r"], 0.5 * G.BAR["od"]
    a1 = [G.TH_N1 + 120.0 * k for k in range(3)]
    a2 = [x + 60.0 for x in a1]

    def with_tabs(base, angles):
        tabs = [TG.sector(G.TAB["r0"], ri + 0.5, 0.0, t, a - math.degrees(0.5 * G.TAB["w"] / rb),
                          math.degrees(G.TAB["w"] / rb)) for a in angles]
        shp = TG.fuse([base] + tabs)
        return TG._cut(shp, *[TG.cyl_z(*(rb * TG._u(a))[:2], rbo + 0.05, -1.0, t + 1.0) for a in angles])
    ca1 = with_tabs(TG.sector(ri, ro, 0.0, t), a1)
    rot = TG._cut(TG.fuse([TG.sector(ri, ro, 0.0, t, k * G.PITCH - 0.5 * G.VANE["wr"], G.VANE["wr"]) for k in range(n)]
                          + [TG.sector(G.SLEEVE_OUT, ri, 0.0, t)]),
                  *[TG.cyl_z(*(rb * TG._u(a))[:2], rbo + 0.05, -1.0, t + 1.0) for a in a1])
    la = [G.LUG["th0"] + k * 360.0 / G.LUG["n"] for k in range(G.LUG["n"])]
    lug = lambda a: TG.sector(G.STATOR_RING[1] - 0.5, G.LUG["r1"], 0.0, t, a - math.degrees(0.5 * G.LUG["w"] / G.TIE["r"]),  # noqa
                              math.degrees(G.LUG["w"] / G.TIE["r"]))
    sta = TG._cut(TG.fuse([TG.sector(ri, ro, 0.0, t, k * G.PITCH - 0.5 * G.VANE["ws"], G.VANE["ws"]) for k in range(n)]
                          + [TG.sector(*G.STATOR_RING, 0.0, t)] + [lug(a) for a in la]),
                  *[TG.cyl_z(*(G.TIE["r"] * TG._u(a))[:2], 0.5 * G.TIE["d"] + 0.05, -1.0, t + 1.0) for a in la])
    return dict(
        ca_plate=(ca1, holds_at([(rb * TG._u(a))[:2] for a in a1], rbo)),
        rotor_vane=(rot, holds_at([(rb * TG._u(a))[:2] for a in a1], rbo, also_r=G.SLEEVE_OUT)),
        stator_vane=(sta, holds_at([(G.TIE["r"] * TG._u(a))[:2] for a in la], 0.5 * G.TIE["d"])))


# ------------------------------------------------------------------------------------------- 3. the rotor's modes
def rotor_modes(m, rows, od_list):
    out = {}
    base = G.COUPLING["od"]
    for od in od_list:
        G.COUPLING["od"] = od
        bm = beam_modes_od(m, rows, od)
        out[f"{od:g}"] = bm
    G.COUPLING["od"] = base
    return out


def beam_modes_od(m, rows, od):
    """s2_structure.beam_modes with the coupling's tube od / 2 for its section (the plug fills its bore) [IR]."""
    import types
    src = SS.beam_modes

    def EIpatched(m_, rows_):
        return src(m_, rows_)
    # rebuild the EI function by a closure over od: simplest to monkey-patch the constants the function reads
    saved = SS.beam_modes.__globals__["G"].COUPLING["od"]
    m.coupling_od_mm = od
    res = _beam(m, rows, od)
    return res


def _beam(m, rows, od, n_el=120):
    zA, zB = m.zz("A", m.h_fb + 0.5 * G.FB["width"]), m.zz("B", m.h_fb + 0.5 * G.FB["width"])
    z = np.linspace(zA, zB, n_el + 1)
    zc = m.zc
    mm = 1e-3
    I = lambda ro, ri=0.0: math.pi / 4 * (ro ** 4 - ri ** 4)               # noqa: E731
    rc = 0.5 * od * mm

    def EI(zm):
        h = abs(zm - zc)
        if h <= G.FL_Z0:
            return 18e9 * I(33 * mm, 30 * mm) + 3.6e9 * I(30 * mm, 25.5 * mm)
        if h <= G.FL_Z1:
            return 193e9 * I(30 * mm) + 18e9 * I(33 * mm, 30 * mm)
        if h <= m.h_c0:
            return 193e9 * I(12.5 * mm) + 18e9 * I(20.5 * mm, 12.5 * mm)
        if h <= m.h_end:
            return 193e9 * I(12.5 * mm) + 18e9 * I(rc, 12.5 * mm)
        if h <= m.h_stub0:
            return 18e9 * I(rc)
        if h <= m.h_c1:
            return 193e9 * I(12.5 * mm) + 18e9 * I(rc, 12.5 * mm)
        return 193e9 * I(12.5 * mm)
    ndof = 2 * (n_el + 1)
    K, M = np.zeros((ndof, ndof)), np.zeros((ndof, ndof))
    for e in range(n_el):
        L = (z[e + 1] - z[e]) * mm
        ei = EI(0.5 * (z[e] + z[e + 1]))
        k = ei / L ** 3 * np.array([[12, 6 * L, -12, 6 * L], [6 * L, 4 * L * L, -6 * L, 2 * L * L],
                                    [-12, -6 * L, 12, -6 * L], [6 * L, 2 * L * L, -6 * L, 4 * L * L]])
        idx = [2 * e, 2 * e + 1, 2 * e + 2, 2 * e + 3]
        K[np.ix_(idx, idx)] += k
    m_sta = 0.0
    for r in rows:
        if r["body"] in ("rotor", "bearing"):
            idx = [i for i in range(n_el + 1) if r["z0_mm"] - 1e-6 <= z[i] <= r["z1_mm"] + 1e-6] or \
                [int(np.argmin(abs(z - r["z_mm"])))]
            for i in idx:
                M[2 * i, 2 * i] += r["m_kg"] / len(idx)
        elif r["body"] == "stator":
            m_sta += r["m_kg"]
    for s_ in "AB":
        zb = m.zz(s_, m.h_brg0 + 0.5 * G.BEARING["width"])
        i = int(np.argmin(abs(z - zb)))
        M[2 * i, 2 * i] += 0.5 * m_sta
    for i in range(n_el + 1):
        M[2 * i + 1, 2 * i + 1] += 1e-7
        M[2 * i, 2 * i] += 1e-6
    span = 2 * (m.frame_a - G.PROFILE) * mm
    k_frame = 2 * 48 * 69e9 * 7.0e-8 / span ** 3
    K[0, 0] += k_frame
    K[-2, -2] += k_frame
    from scipy.linalg import eigh
    w2 = eigh(K, M, eigvals_only=True)
    f = np.sqrt(np.clip(w2, 0, None)) / (2 * math.pi)
    return dict(f_Hz=[float(x) for x in f if x > 0.5][:4])


# ------------------------------------------------------------------------------------------- 4. Campbell
def campbell(modes, rpm=np.arange(400, 801, 5)):
    """the drive lines 6 x f_rel x k (k 1-3) against every mode; the shaft speeds where every line clears every mode."""
    ok = []
    for n_ in rpm:
        f_rel = 2 * n_ / 60.0
        lines = [6 * f_rel * k for k in (1, 2, 3)]
        clear = all(abs(L - f) > MARGIN * f for L in lines for f in modes)
        ok.append(bool(clear))
    windows, cur = [], None
    for n_, c in zip(rpm, ok):
        if c and cur is None:
            cur = [n_, n_]
        elif c:
            cur[1] = n_
        elif cur is not None:
            windows.append(cur)
            cur = None
    if cur is not None:
        windows.append(cur)
    return dict(rpm=[float(x) for x in rpm], clear=ok, windows_rpm=[[float(a), float(b)] for a, b in windows],
                at_600=bool(ok[list(rpm).index(600)]) if 600 in rpm else None)


def figure(modes_named, path, title):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    rpm = np.arange(300, 901, 5)
    fig, ax = plt.subplots(figsize=(9, 5.5))
    for k, c in ((1, "#c0392b"), (2, "#e67e22"), (3, "#f1c40f")):
        ax.plot(rpm, 6 * 2 * rpm / 60.0 * k, color=c, lw=2, label=f"the pump's drive, x{k} (6 x relative rotation x {k})")
    ys = []
    for nm, f in sorted(modes_named, key=lambda m: m[1]):
        y = f if not ys or f - ys[-1] >= 9 else ys[-1] + 9
        ys.append(y)
        ax.text(905, y, nm, fontsize=7, va="center")
    for nm, f in modes_named:
        ax.axhspan(f * (1 - MARGIN), f * (1 + MARGIN), color="#3498db", alpha=0.08)
        ax.axhline(f, color="#2c3e50", lw=0.8)
    ax.axvline(600, color="#777", ls="--", lw=1)
    ax.set_xlim(300, 900)
    ax.set_ylim(0, 450)
    ax.set_xlabel("shaft speed (rpm; the counter-rotor the same, the other way)")
    ax.set_ylabel("Hz")
    ax.set_title(title, fontsize=9)
    ax.legend(fontsize=7, loc="upper left")
    fig.tight_layout()
    fig.savefig(path, dpi=130)


def main():
    quick = "--quick" in sys.argv
    m = G.S2Core()
    m.build()
    rows = SS.solids(m)
    out = dict(margin=MARGIN, delta_m=DELTA)
    dr = drive(m)
    out["drive"] = dr
    print("driven:", [(r["part"], round(r["net_N"], 2)) for r in dr if r["driven"]],
          "| the balanced ones' tolerance residual, largest", round(max(r["tolerance_residual_N"] for r in dr), 2), "N")
    # FE: the driven parts at 3, 4, 5, 6 mm
    fe = {}
    for ts in ((1.0, 2.0) if quick else (1.0, 4.0 / 3.0, 1.5, 5.0 / 3.0, 2.0)):
        shapes = part_shapes(m, ts)
        for key, (shp, pred) in shapes.items():
            r = fe_modes(shp, pred, f"{key} t {3 * ts:.1f} mm", n=10, clmax=3.0 if ts < 1.5 else 4.0)
            fe[f"{key}_{3 * ts:.1f}mm"] = r
            print("FE", r["label"], [round(x, 1) for x in r.get("f_Hz", [])], "excited:",
                  [round(x, 1) for x in r.get("excited_Hz", [])], r.get("error", ""))
    out["fe"] = fe
    # the rotor vs the couplings
    rm = rotor_modes(m, rows, [34.0, 40.0, 50.0, 60.0])
    out["rotor_vs_coupling_od"] = rm
    print("rotor modes vs coupling od:", {k: [round(x, 1) for x in v["f_Hz"]] for k, v in rm.items()})
    json.dump(out, open(os.path.join(HERE, "s2_modes_results.json"), "w"), indent=1, default=float)


if __name__ == "__main__" and "--campbell" not in sys.argv:
    main()


# ------------------------------------------------------------------------------------------- the choice (--campbell)
CHOICE = dict(ca_plate="4.0", rotor_vane="4.0", stator_vane="4.5")    # mm, the driven end plates: s2_geometry.py
# T_CA_END, T_ROT_END, T_STA_END; every other plate keeps 3 mm (rebuild/s2_models/s2_thickness.py, the designer's
# delegation 2026-10-17), its modes reached by the gaps' tolerance residual only


def finalize():
    """the Campbell check of the thicknesses chosen, against the 3 mm before, from the FE results already run."""
    path = os.path.join(HERE, "s2_modes_results.json")
    out = json.load(open(path))
    fe = out["fe"]
    before = [(f"{k} 3 mm", f) for k in ("ca_plate", "rotor_vane", "stator_vane") for f in fe[f"{k}_3.0mm"]["excited_Hz"]
              if f < 600]
    after = [(f"{k} {v} mm", f) for k, v in CHOICE.items() for f in fe[f"{k}_{v}mm"]["excited_Hz"] if f < 600]
    rpm = np.arange(300, 901, 5)

    def clear(modes):
        ok = []
        for n_ in rpm:
            L1, L2 = 6 * 2 * n_ / 60.0, 12 * 2 * n_ / 60.0
            ok.append(all(abs(L1 - f) > MARGIN * f and abs(L2 - f) > 0.5 * MARGIN * f for _, f in modes))
        win, cur = [], None
        for n_, c in zip(rpm, ok):
            if c and cur is None:
                cur = [float(n_), float(n_)]
            elif c:
                cur[1] = float(n_)
            elif cur is not None:
                win.append(cur); cur = None
        if cur is not None:
            win.append(cur)
        return dict(windows_rpm=win, at_600=bool(ok[list(rpm).index(600)]))
    out["campbell"] = dict(rule="the 1x drive (6 x the relative rotation) +-20 %, the 2x +-10 %, from every mode a "
                                "uniform pull excites (effective z-mass >= 5 %) [IR]",
                           before=dict(modes=before, **clear(before)), after=dict(modes=after, **clear(after)),
                           choice_mm=CHOICE,
                           rotor_bending="not excited by the pump: the six sectors' pulls are axial and their lateral "
                                         "parts cancel [OC]; only the 1x out-of-balance drives it (10 Hz against the "
                                         "first mode's 35.6 Hz, rebuild/s2_models/s2_structure_results.json)",
                           torsion="the pump's torque pulses at 120 Hz: the torsional modes run through the 1:-1 drive, "
                                   "not modelled yet (OPEN)")
    json.dump(out, open(path, "w"), indent=1, default=float)
    figure(after + [("(inner, 3 mm, tolerance only) " + n.replace(" 3 mm", ""), f) for n, f in before],
           os.path.join(HERE, "s2-modes-campbell.png"),
           "the pull-driven modes against the pump's drive (rebuild/s2_models/s2_modes.py)" + chr(10)
           + "the driven end plates: Ca 4.0, rotor vane 4.0, stator vane 4.5 mm; the inner plates 3 mm (the record)")
    out["campbell"]["inner_3mm_note"] = ("the inner plates keep 3 mm: their modes (before) are reached by the gaps' "
                                         "tolerance residual only, at most 10 um at 120 Hz (s2_thickness_results.json)")
    json.dump(out, open(path, "w"), indent=1, default=float)
    print("before:", clear(before), "\nafter:", clear(after))


if __name__ == "__main__" and "--campbell" in sys.argv:
    finalize()
