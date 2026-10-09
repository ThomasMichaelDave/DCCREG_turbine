"""sim/hub_beads_settled.py -- the rings' beads once the DC has settled, the contact wedge where a bead touches the glass,
the field in the PEEK and at the AH's end, and the grooves' shape (ledger §5.2 "the beads in the settled DC state",
"the bead-glass contact wedge", "the AH ends facing the polar beads"; docs/rings-design.md §8).

At switch-on the DC shares itself by the permittivities. Over minutes to hours the insulators' leakage moves it to the
conduction-settled state (sim/hub_drift.py, within about 2 h); then the conductivities share it [OC]. Both states are
solved on the same geometry.
- **The geometry, as drawn** (docs/drawings/DCCREG-HUB-201, docs/make_rings_drawing.py): each edge carries its own bead
  (Cu wire, 3 mm across at the polar edge, 2 mm at the equatorial), each in a gel-filled groove with parallel walls
  rho + 0.5 mm off the bead's centre-line and a flat top 2 rho + 0.5 mm over the contact, in the 0.5 mm gel pocket.
  The record's own bead solve (sim/hub_rings_build.py edge_peak) filled its whole local box with gel to the groove's
  depth and put one bead size at both edges; that path is reproduced first, as the check against the record's
  4.85 / 1.41 and 4.36 / 2.97 kV/mm.
- **1. The hub** (0.25 mm cells, both modes, ring A at V_A and ring B at V_B; sim/core_rings.py's solver, sigma / eps0
  in place of eps when settled) [OC law, IR grid]. The vacuum carries no current: a vanishing sigma there (Laplace
  inside the glass, which is what the settled vacuum obeys) [IR]. The field at the null with the beads (the record's
  was solved for the bands alone), and at half the cell.
- **2. Each bead's box** (0.025 mm cells, +-4 mm, its edges from the hub): the peak field in the gel and the glass along
  the bead's normals (edge_peak's sampling), and in the PEEK 0.05 / 0.1 / 0.25 mm and more from the gel (the drawn
  groove's machined corners are sharp in the model) [IR].
- **3. The contact wedge** (a nested box of 0.0025 mm cells, +-0.5 mm about the contact, its edges from the bead's box):
  on the bare-glass side, the gap g(s) between the bead and the glass at a distance s from the contact is about
  s^2 / 2 rho, below a cell where s < 0.1 mm. So the gel's field across the gap is taken from the glass's normal field
  and the interface condition: D continuous at switch-on (E_gel = eps_glass / eps_gel E_glass), J continuous settled
  (E_gel = sigma_glass / sigma_gel E_glass) [OC]; where the gap is resolved, V / g across it checks that. The voltage
  across the gap is set against air's Paschen breakdown for a void of that gap (A 15 /(cm Torr), B 365 V/(cm Torr),
  gamma 0.01; its minimum, about 0.3 kV, for gaps below the minimum's) [IR]: under 1, the contact needs no gel to stay
  free of discharge.
- **4. The PEEK at the hub's scale:** its peak away from the conductors, in the AH seat (from the polar groove's top to
  the AH's end) and at the AH end's corner [IR].
- **5. The interface and the air:** the tangential field along the glass between the rings (the rating is its average,
  1 kV/mm [RH]); the field in the air within 2 mm of the hub's outside.
- **6. The AH end's corner** (a 0.025 mm box about it): the corner rounded to RC_AH, the PEEK's peak near it [IR].
- **7. The grooves' tops full-round** (a ball-end cut concentric with the bead, 0.5 / 0.75 / 1.0 mm of gel over it).
- **8. The settled beads against sigma_glass / sigma_gel** (SWEEP; the gel at 1e-13 S/m), for the drawn and the
  recommended groove: the limit that holds the equatorial bead's gel to its rating.
Conductivities: sim/hub_drift.py SIG (datasheet-class [IR]): glass and gel 1e-13 S/m, PEEK 1e-14, G10 1e-13, air
2e-14; the glass at 40 C 5.4e-13.
Writes sim/hub_beads_settled_results.json (about 25 min on four cores).
Usage: python3 sim/hub_beads_settled.py
"""
import json
import math
import os
import sys
import time

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import core_rings as CR            # noqa: E402
import hub_drift as D              # noqa: E402
import hub_locked as HL            # noqa: E402
import hub_rings_build as B        # noqa: E402

EPS0 = 8.8541878128e-12
H_HUB = 0.25                       # mm, the hub's cells (as the build and the drift run)
H_BOX, HALF_BOX = 0.025, 4.0       # mm, the bead's box (as edge_peak)
H_W, HALF_W = 0.0025, 0.5          # mm, the wedge's box
SIG_VAC = 1e-24                    # S/m: the vacuum, numerically [IR]
STATES = (("switch-on", None), ("settled, 25 C", D.SIG["glass"]), ("settled, glass at 40 C", D.SIG["glass40"]))
SWEEP = (0.3, 1.0, 2.0, 3.0, 4.0, 5.4, 8.0)       # sigma_glass / sigma_gel, settled [IR: the materials' spread]
RC_AH = (0.0, 0.75, 1.5, 2.5)                     # mm, the AH end's corner radius (0: the register's square envelope)
GROOVES = ("round:0.5", "round:0.75", "round:1.0")  # full-round tops: 0.5 / 0.75 / 1.0 mm of gel over the bead
REC_GROOVE = "round:1.0"                           # the groove this study recommends (see the findings)
PEEK_OFF = (0.05, 0.1, 0.25)       # mm from the gel: where the PEEK's peak is read
S_WEDGE = (0.025, 0.05, 0.1, 0.2, 0.3, 0.45)            # mm from the contact, in the wedge's box
S_BOX = (0.6, 0.8, 1.0, 1.5, 2.0, 2.5)                  # mm from the contact, in the bead's box
PASCHEN = dict(A=15.0, B=365.0, gamma=0.01, p_torr=760.0)
VAC, GLASS, GEL, PEEK, G10, AIR = range(6)


def rec_beads(rec):
    return {"pol": (rec["theta_p"], rec["rho_pol_mm"]), "eq": (rec["theta_e"], rec["rho_eq_mm"])}


def materials(R, Z, rec, hub, groove="rect"):
    """the material of each cell (VAC, GLASS, GEL, PEEK, G10, AIR): the retainer, its coupler, the gel pocket and each
    bead's groove. groove "rect" is the drawing's (parallel walls rho + 0.5 from the bead's centre-line, a flat top
    2 rho + 0.5 over the contact), "round" the same with its top full-round about the bead's centre (radius rho + 0.5),
    None no grooves (the build's and the drift's maps)."""
    rho = np.hypot(R, Z)
    m = np.full(R.shape, AIR, dtype=np.int8)
    ret = (R <= hub["ret_r"]) & (Z <= hub["ret_z"]) & (rho >= hub["R_v"])
    m[ret] = PEEK
    m[ret & (R > hub["ret_r"] - hub["cpl_t"])] = G10
    m[ret & (rho < hub["R_v"] + hub["fill_t"])] = GEL
    if groove:
        for th, rb in rec_beads(rec).values():
            u = (math.sin(math.radians(th)), math.cos(math.radians(th)))       # the contact's outward normal
            a = R * u[0] + Z * u[1] - hub["R_v"]                               # height over the contact
            b = np.abs(R * u[1] - Z * u[0])                                    # offset from the bead's centre-line
            kind, _, tg = groove.partition(":")                                 # "round:0.75": 0.75 mm of gel
            tg = float(tg) if tg else hub["fill_t"]
            w = rb + tg
            if kind == "rect":
                g = (b <= w) & (a <= 2 * rb + tg)
            else:
                g = ((b <= w) & (a <= rb)) | (np.hypot(R - (hub["R_v"] + rb) * u[0], Z - (hub["R_v"] + rb) * u[1]) <= w)
            m[ret & g] = GEL
    m[(rho >= hub["R_in"]) & (rho < hub["R_v"])] = GLASS
    m[rho < hub["R_in"]] = VAC
    return m


def prop(m, hub, sig_glass):
    """eps_r of each cell (sig_glass None) or its sigma / eps0, the glass at sig_glass (S/m): the solver takes either."""
    if sig_glass is None:
        tab = {VAC: 1.0, GLASS: hub["eps_glass"], GEL: hub["eps_fill"], PEEK: hub["eps_ret"], G10: hub["eps_cpl"],
               AIR: 1.0}
    else:
        tab = {VAC: SIG_VAC, GLASS: sig_glass, GEL: D.SIG["gel"], PEEK: D.SIG["peek"], G10: D.SIG["g10"],
               AIR: D.SIG["air"]}
        tab = {k: v / EPS0 for k, v in tab.items()}
    out = np.empty(m.shape)
    for k, v in tab.items():
        out[m == k] = v
    return out


def ratio(hub, sig_glass):
    """the glass's property over the gel's: what carries the glass's normal field into the gel at their interface."""
    return hub["eps_glass"] / hub["eps_fill"] if sig_glass is None else sig_glass / D.SIG["gel"]


def maps_fn(rec, sig_glass=None, groove="rect", keep=None):
    """a maps function for sim/core_rings.py's solver: the hub with each edge's own bead in its groove (groove None: the
    build's maps without beads); eps (sig_glass None) or sigma / eps0. keep, a dict, receives the grid, the materials
    and the conductors."""
    def fn(ring, theta, coils, h_, hub_):
        r, z, _, cond = HL.maps(ring, theta, coils, h_, hub_)
        R, Z = np.meshgrid(r, z, indexing="ij")
        m = materials(R, Z, rec, hub_, groove=groove)
        if groove:
            for th, rb in rec_beads(rec).values():
                cx, cz = (hub_["R_v"] + rb) * math.sin(math.radians(th)), (hub_["R_v"] + rb) * math.cos(math.radians(th))
                cond[(np.hypot(R - cx, Z - cz) <= max(rb, 0.5 * h_)) & (cond == 0)] = 2
        if keep is not None:
            keep.update(r=r, z=z, m=m, cond=cond)
        return r, z, prop(m, hub_, sig_glass), cond
    return fn


def hub_solve(rec, sig_glass, groove="rect", h=H_HUB):
    """the hub (both modes): each edge with its own bead in its groove; groove None: the build's maps without beads
    (the bands alone). Returns V (V), its interpolator, the field at the null, the grid, materials and conductors."""
    hub = B.hub_system()
    keep = {}
    res = CR.solve(HL.band(rec["theta_p"], rec["theta_e"]), 0.0, True, h, hub=hub, keep=True,
                   maps_fn=maps_fn(rec, sig_glass, groove, keep))
    V, at = B.hub_potential(res, rec["V_A_kV"] * 1e3, rec["V_B_kV"] * 1e3)
    k = abs(res["E_centre_kV_cm_per_kV"])
    return dict(V=V, at=at, k_kV_cm_per_kV=k, E_null_kV_cm=k * rec["V_gap_kV"], h_mm=h, res=res, **keep)


def interp(V, r0, z0, h):
    """a bilinear interpolator of cell values V (cells from (r0, z0), cell h mm) at points (r, z)."""
    nr, nz = V.shape

    def at(r, z):
        x = np.clip((np.asarray(r, dtype=float) - r0) / h - 0.5, 0, nr - 1.001)
        y = np.clip((np.asarray(z, dtype=float) - z0) / h - 0.5, 0, nz - 1.001)
        i, j = np.floor(x).astype(int), np.floor(y).astype(int)
        u, w = x - i, y - j
        return (1 - u) * (1 - w) * V[i, j] + u * (1 - w) * V[i + 1, j] + (1 - u) * w * V[i, j + 1] + u * w * V[i + 1, j + 1]
    return at


def emag(V, h):
    return np.hypot(np.gradient(V, h * 1e-3, axis=0), np.gradient(V, h * 1e-3, axis=1)) / 1e6      # kV/mm


def grid(r0, z0, n, h):
    r = r0 + (np.arange(n) + 0.5) * h
    z = z0 + (np.arange(n) + 0.5) * h
    return np.meshgrid(r, z, indexing="ij")


def peaks(Em, bx, h):
    """the peak field (kV/mm) in the gel and in the glass along the bead's normals (edge_peak's sampling)."""
    out = {"filler": 0.0, "glass": 0.0}
    for a, sx, sz, p2, p4, where in bx["normals"]:
        e0 = 2 * B._bilin(Em, *p2, bx["r0"], bx["z0"], h) - B._bilin(Em, *p4, bx["r0"], bx["z0"], h)
        out[where] = max(out[where], float(e0))
    return out


def dist_from(mask, h):
    """each cell's distance (mm) from the nearest cell of mask (a Euclidean distance transform)."""
    from scipy.ndimage import distance_transform_edt
    return distance_transform_edt(~mask) * h


def peek_peaks(Em, m, h, R, Z):
    """the PEEK's largest field at least each PEEK_OFF from the gel and the box's edges, and where it is."""
    dg = dist_from(m == GEL, h)
    edge = np.zeros(m.shape, dtype=bool)
    edge[:3, :] = edge[-3:, :] = edge[:, :3] = edge[:, -3:] = True
    out = {}
    for off in PEEK_OFF:
        sel = (m == PEEK) & (dg >= off) & ~edge
        if sel.any():
            i = np.argmax(np.where(sel, Em, -1.0))
            out[f"{off:g} mm"] = dict(E_kV_mm=float(Em.flat[i]), r_mm=float(R.flat[i]), z_mm=float(Z.flat[i]))
    return out


def bead_box(rec, which, sig_glass, hubV, groove="rect"):
    """a bead's box, solved with the hub's solution (hubV) on its edges: V, |E|, the materials, the box."""
    hub = B.hub_system()
    th, rb = rec_beads(rec)[which]
    bx = B._edge_box(rec["theta_p"], rec["theta_e"], rb, which, H_BOX, HALF_BOX)     # the conductors and the normals
    R, Z = grid(bx["r0"], bx["z0"], bx["n"], H_BOX)
    m = materials(R, Z, rec, hub, groove)
    V = B.local_fv(prop(m, hub, sig_glass), bx["cond"], rec["V_B_kV"] * 1e3, H_BOX, bx["r0"], bx["z0"], hubV)
    return dict(V=V, Em=emag(V, H_BOX), m=m, bx=bx, R=R, Z=Z)


def gap_mm(rec, which, s, hub):
    """the gap along the glass's outward normal from the point s (mm, along the glass) beyond the contact on the
    bare-glass side to the bead (None once the normal misses it)."""
    th, rb = rec_beads(rec)[which]
    side = -1.0 if which == "pol" else 1.0                     # toward the pole / toward the equator
    t = math.radians(th) + side * s / hub["R_v"]
    c = np.array([(hub["R_v"] + rb) * math.sin(math.radians(th)), (hub["R_v"] + rb) * math.cos(math.radians(th))])
    u = np.array([math.sin(t), math.cos(t)])
    p = hub["R_v"] * u
    b = float(np.dot(p - c, u))                                 # |p + x u - c|^2 = rb^2: x^2 + 2 b x + (|p-c|^2 - rb^2) = 0
    q = float(np.dot(p - c, p - c)) - rb * rb
    disc = b * b - q
    return (-b - math.sqrt(disc)) if disc >= 0 else None


def paschen_kV(g_mm):
    """air's breakdown voltage (kV) across a gap g at 1 atm; below the minimum's gap, the minimum [IR]."""
    A, Bc, gam, p = PASCHEN["A"], PASCHEN["B"], PASCHEN["gamma"], PASCHEN["p_torr"]
    k = math.log(math.log(1 + 1 / gam))
    pd_min = math.e * math.exp(k) / A
    pd = max(p * g_mm * 0.1, pd_min)
    return Bc * pd / (math.log(A * pd) - k) / 1e3


def wedge_rows(rec, which, sig_glass, V, r0, z0, h, ss):
    """along the bare-glass side at distances ss from the contact: the voltage across the gap, the gap, the field
    across it (V / g where the gap spans 4 cells or more) and the gel's field at the glass from the interface
    condition, against Paschen's breakdown of a void of that gap."""
    hub = B.hub_system()
    th, rb = rec_beads(rec)[which]
    side = -1.0 if which == "pol" else 1.0
    at = interp(V, r0, z0, h)
    k = ratio(hub, sig_glass)
    rows = []
    for s in ss:
        t = math.radians(th) + side * s / hub["R_v"]
        u = (math.sin(t), math.cos(t))
        dep = max(2 * h, 0.1 * s)                               # the normal derivative in the glass, two depths
        v0 = float(at(hub["R_v"] * u[0], hub["R_v"] * u[1]))
        v1 = float(at((hub["R_v"] - dep) * u[0], (hub["R_v"] - dep) * u[1]))
        v2 = float(at((hub["R_v"] - 2 * dep) * u[0], (hub["R_v"] - 2 * dep) * u[1]))
        e_gl = abs((3 * v0 - 4 * v1 + v2) / (2 * dep)) / 1e3     # kV/mm, the normal field in the glass, one-sided
        g = gap_mm(rec, which, s, hub)
        dv = (rec["V_B_kV"] * 1e3 - v0) / 1e3
        pk = paschen_kV(g) if g else None
        rows.append(dict(s_mm=s, gap_mm=g, dV_kV=dv, E_glass_n_kV_mm=e_gl, E_gel_interface_kV_mm=k * e_gl,
                         E_gap_mean_kV_mm=(dv / g) if (g and g >= 4 * h) else None, paschen_kV=pk,
                         paschen_ratio=(dv / pk) if pk else None))
    return rows


def wedge_box(rec, which, sig_glass, bead, groove="rect"):
    """the nested box about the contact, its edges from the bead's box."""
    hub = B.hub_system()
    th, rb = rec_beads(rec)[which]
    cr, cz = hub["R_v"] * math.sin(math.radians(th)), hub["R_v"] * math.cos(math.radians(th))
    bcx, bcz = (hub["R_v"] + rb) * math.sin(math.radians(th)), (hub["R_v"] + rb) * math.cos(math.radians(th))
    n = int(round(2 * HALF_W / H_W))
    r0, z0 = cr - HALF_W, cz - HALF_W
    R, Z = grid(r0, z0, n, H_W)
    rho = np.hypot(R, Z)
    pol = np.degrees(np.arctan2(R, Z))
    m = materials(R, Z, rec, hub, groove)
    cond = (rho >= hub["R_v"]) & (rho <= hub["R_v"] + B.FOIL_T) & (pol >= rec["theta_p"]) & (pol <= rec["theta_e"])
    cond |= np.hypot(R - bcx, Z - bcz) <= rb
    vbc = interp(bead["V"], bead["bx"]["r0"], bead["bx"]["z0"], H_BOX)
    V = B.local_fv(prop(m, hub, sig_glass), cond, rec["V_B_kV"] * 1e3, H_W, r0, z0, vbc)
    return V, r0, z0


def bead_state(rec, which, sig_glass, hubq, groove="rect", wedge=True):
    """one bead (ring B's; ring A's is its mirror image) in one state: the gel, the glass, the PEEK, the wedge."""
    bead = bead_box(rec, which, sig_glass, hubq["at"], groove)
    p = peaks(bead["Em"], bead["bx"], H_BOX)
    out = dict(E_gel_kV_mm=p["filler"], E_glass_kV_mm=p["glass"],
               E_peek=peek_peaks(bead["Em"], bead["m"], H_BOX, bead["R"], bead["Z"]),
               interface_ratio=ratio(B.hub_system(), sig_glass))
    if wedge:
        Vw, r0, z0 = wedge_box(rec, which, sig_glass, bead, groove)
        rows = wedge_rows(rec, which, sig_glass, Vw, r0, z0, H_W, S_WEDGE)
        rows += wedge_rows(rec, which, sig_glass, bead["V"], bead["bx"]["r0"], bead["bx"]["z0"], H_BOX, S_BOX)
        wmax = max(rows, key=lambda q: q["E_gel_interface_kV_mm"])
        pmax = max((q for q in rows if q["paschen_ratio"] is not None), key=lambda q: q["paschen_ratio"])
        out.update(wedge=rows, wedge_max=dict(s_mm=wmax["s_mm"], E_gel_kV_mm=wmax["E_gel_interface_kV_mm"]),
                   wedge_paschen_max=dict(s_mm=pmax["s_mm"], ratio=pmax["paschen_ratio"], dV_kV=pmax["dV_kV"],
                                          gap_mm=pmax["gap_mm"]))
    return out


def say(tag, q):
    w = (f"; wedge max {q['wedge_max']['E_gel_kV_mm']:.2f} kV/mm at {q['wedge_max']['s_mm']:g} mm, Paschen ratio "
         f"{q['wedge_paschen_max']['ratio']:.2f} at {q['wedge_paschen_max']['s_mm']:g} mm") if "wedge" in q else ""
    print(f"  {tag}: gel {q['E_gel_kV_mm']:.2f}, glass {q['E_glass_kV_mm']:.2f} kV/mm; PEEK "
          + ", ".join(f"{a} {b['E_kV_mm']:.2f}" for a, b in q["E_peek"].items()) + w, flush=True)


def check_record(rec):
    """the record's own path (edge_peak: the box filled with gel to the groove's depth, one bead size at both edges)."""
    out = {}
    for which in ("pol", "eq"):
        rho_e = rec["rho_pol_mm"] if which == "pol" else rec["rho_eq_mm"]
        q = B.edge_peak(rec, rho_e, which)
        ref = rec["E_" + which]
        out[which] = dict(E_gel_kV_mm=q["E_filler_kV_mm"], E_glass_kV_mm=q["E_glass_kV_mm"], record_gel=ref["gel"],
                          record_glass=ref["glass"],
                          ok=bool(abs(q["E_filler_kV_mm"] - ref["gel"]) < 0.01 and abs(q["E_glass_kV_mm"] - ref["glass"]) < 0.01))
        print(f"check {which}: gel {q['E_filler_kV_mm']:.3f} (record {ref['gel']:.3f}), glass {q['E_glass_kV_mm']:.3f} "
              f"(record {ref['glass']:.3f})", flush=True)
    return out


def ah_conductor(R, Z, hub, rc):
    """the AH's REF envelope (r <= ah_r, z >= ah_z[0]) with its end's outer corner rounded to rc."""
    ar, az = hub["ah_r"], hub["ah_z"][0]
    c = (R <= ar) & (Z >= az)
    if rc > 0:
        c &= ~((R > ar - rc) & (Z < az + rc) & (np.hypot(R - (ar - rc), Z - (az + rc)) > rc))
    return c


def ah_end(rec, hubs):
    """the AH end's corner toward the polar bead: a box (0.025 mm cells, +-4 mm) about it with the hub's solution on its
    edges, the corner rounded to each of RC_AH; the PEEK's largest field 0.05 / 0.1 / 0.25 mm and more off it, within
    2.5 mm of the corner (nearer the box's edges the hub's sharp corner, held there, would show)."""
    hub = B.hub_system()
    cx, cz = hub["ah_r"], hub["ah_z"][0]
    n = int(round(2 * HALF_BOX / H_BOX))
    r0, z0 = cx - HALF_BOX, cz - HALF_BOX
    R, Z = grid(r0, z0, n, H_BOX)
    m = materials(R, Z, rec, hub)
    near = np.hypot(R - cx, Z - cz) <= 2.5
    out = {}
    for label, sig_glass in STATES:
        rows = []
        for rc in RC_AH:
            cond = ah_conductor(R, Z, hub, rc)
            V = B.local_fv(prop(m, hub, sig_glass), cond, 0.0, H_BOX, r0, z0, hubs[label]["at"])
            Em = emag(V, H_BOX)
            dc = dist_from(cond, H_BOX)
            row = dict(rc_mm=rc)
            for off in PEEK_OFF:
                sel = (m == PEEK) & (dc >= off) & (dc <= off + 0.5) & near
                i = np.argmax(np.where(sel, Em, -1.0))
                row[f"{off:g} mm"] = dict(E_kV_mm=float(Em.flat[i]), r_mm=float(R.flat[i]), z_mm=float(Z.flat[i]))
            rows.append(row)
        out[label] = rows
        print(f"  AH end, {label}: " + "; ".join(f"rc {q['rc_mm']:g}: " + ", ".join(
            f"{off:g} mm {q[f'{off:g} mm']['E_kV_mm']:.2f}" for off in PEEK_OFF) for q in rows), flush=True)
    return out


def air_field(rec, hubs):
    """the largest field in the air within 2 mm of the hub's outside (the coupler and the flanges), two cells or more
    off any conductor: what the coupler's radius leaves the air."""
    out = {}
    for label, _ in STATES:
        q = hubs[label]
        R, Z = np.meshgrid(q["r"], q["z"], indexing="ij")
        Em = emag(q["V"], H_HUB)
        solid = (q["m"] != AIR) | (q["cond"] > 0)
        sel = (q["m"] == AIR) & (dist_from(solid, H_HUB) <= 2.0) & (dist_from(q["cond"] > 0, H_HUB) >= 2 * H_HUB)
        i = np.argmax(np.where(sel, Em, -1.0))
        out[label] = dict(E_air_max_kV_mm=float(Em.flat[i]), at_mm=(float(R.flat[i]), float(Z.flat[i])),
                          V_coupler_surface_max_kV=float(np.abs(q["at"](33.25, np.linspace(0.5, 71.5, 300))).max() / 1e3))
    return out


def hub_peek(rec, hubs):
    """the PEEK at the hub's scale: its largest field two cells or more off any conductor, in the AH seat (from the
    polar groove's top to the AH's end) and within 1 mm of the AH end's corner."""
    hub = B.hub_system()
    tp, rb = rec_beads(rec)["pol"]
    z_groove = (hub["R_v"] + 2 * rb + hub["fill_t"]) * math.cos(math.radians(tp))
    out = {}
    for label, _ in STATES:
        q = hubs[label]
        R, Z = np.meshgrid(q["r"], q["z"], indexing="ij")
        Em = emag(q["V"], H_HUB)
        near = dist_from(q["cond"] > 0, H_HUB) < 2 * H_HUB
        peek = (q["m"] == PEEK) & ~near
        seat = peek & (R <= hub["ah_r"]) & (Z > z_groove) & (Z < hub["ah_z"][0])
        corner = peek & (np.hypot(R - hub["ah_r"], Z - hub["ah_z"][0]) <= 1.0)
        i = np.argmax(np.where(peek, Em, -1.0))
        out[label] = dict(E_peek_max_kV_mm=float(Em.flat[i]), at_mm=(float(R.flat[i]), float(Z.flat[i])),
                          E_seat_max_kV_mm=float(Em[seat].max()), E_seat_mean_kV_mm=float(Em[seat].mean()),
                          E_ah_corner_kV_mm=float(Em[corner].max()), seat_z_mm=(z_groove, hub["ah_z"][0]))
    return out


def interface(rec, hubs):
    """the tangential field along the glass's outer surface between the rings: its peak and its mean (kV/mm)."""
    hub = B.hub_system()
    out = {}
    th = np.radians(np.linspace(rec["theta_e"] + 0.2, 90.0, 400))
    for label, _ in STATES:
        at = hubs[label]["at"]
        rr = hub["R_v"] + 0.5 * H_HUB
        v = at(rr * np.sin(th), rr * np.cos(th))
        et = np.abs(np.gradient(v, rr * th)) / 1e3                  # kV/mm along the arc
        out[label] = dict(E_t_peak_kV_mm=float(et.max()), at_deg=float(np.degrees(th[np.argmax(et)])),
                          E_t_mean_kV_mm=float(abs(v[0] - v[-1]) / (rr * (th[-1] - th[0])) / 1e3))
    return out


def main():
    t0 = time.time()
    rec = json.load(open(os.path.join(HERE, "hub_rings_build_results.json")))["record"]
    out = dict(note="see the module docstring", sig_S_m=D.SIG, sig_vac_S_m=SIG_VAC, h_hub_mm=H_HUB, h_box_mm=H_BOX,
               h_wedge_mm=H_W, paschen=PASCHEN, record=dict((k, rec.get(k)) for k in (
                   "theta_p", "theta_e", "rho_pol_mm", "rho_eq_mm", "V_A_kV", "V_B_kV", "V_gap_kV", "E_null_kV_cm",
                   "E_null_bands_kV_cm")))
    out["check_record"] = check_record(rec)
    # the gates on the hub: without beads it is the record's bands alone (sim/hub_rings_build.py's k before its
    # as-built step); as drawn, settled, it is where sim/hub_drift.py's drift ends (6 h)
    drift = json.load(open(os.path.join(HERE, "hub_drift_results.json")))["drift"]
    d6 = {c["name"]: c["E_kV_cm"][-1] for c in drift}
    q0 = hub_solve(rec, None, groove=None)
    q = hub_solve(rec, D.SIG["glass"])
    q40 = hub_solve(rec, D.SIG["glass40"])
    e_bands = rec.get("E_null_bands_kV_cm", rec["E_null_kV_cm"])
    out["check_settled"] = dict(
        E_null_switch_on_no_beads_kV_cm=q0["E_null_kV_cm"], record_bands_kV_cm=e_bands,
        E_null_kV_cm=q["E_null_kV_cm"], drift_6h_kV_cm=d6["PEEK retainer, gel, 25 C"],
        E_null_40C_kV_cm=q40["E_null_kV_cm"], drift_6h_40C_kV_cm=d6["PEEK retainer, gel, 40 C glass"])
    out["check_settled"]["ok"] = bool(abs(q["E_null_kV_cm"] / d6["PEEK retainer, gel, 25 C"] - 1) < 0.005
                                      and abs(q40["E_null_kV_cm"] / d6["PEEK retainer, gel, 40 C glass"] - 1) < 0.005
                                      and abs(q0["E_null_kV_cm"] / e_bands - 1) < 0.005)
    print("check settled:", json.dumps(out["check_settled"]), flush=True)
    hubs = {label: hub_solve(rec, sig) for label, sig in STATES}
    out["null_as_drawn_kV_cm"] = {label: hubs[label]["E_null_kV_cm"] for label, _ in STATES}
    fine = hub_solve(rec, None, h=0.5 * H_HUB)
    out["null_as_drawn_mesh"] = dict(h_mm=(H_HUB, 0.5 * H_HUB),
                                     E_null_kV_cm=(hubs["switch-on"]["E_null_kV_cm"], fine["E_null_kV_cm"]))
    del fine
    print("the null, as drawn:", json.dumps(out["null_as_drawn_kV_cm"]), json.dumps(out["null_as_drawn_mesh"]), flush=True)
    out["beads"] = {}
    for which in ("pol", "eq"):
        t1 = time.time()
        out["beads"][which] = dict(theta_deg=rec_beads(rec)[which][0], rho_mm=rec_beads(rec)[which][1])
        for label, sig in STATES:
            out["beads"][which][label] = bead_state(rec, which, sig, hubs[label])
            say(f"{which} {label}", out["beads"][which][label])
        out["beads"][which]["run_s"] = time.time() - t1
    out["hub_peek"] = hub_peek(rec, hubs)
    print("PEEK at the hub's scale:", json.dumps(out["hub_peek"]), flush=True)
    out["interface"] = interface(rec, hubs)
    print("interface:", json.dumps(out["interface"]), flush=True)
    out["air"] = air_field(rec, hubs)
    print("air outside the hub:", json.dumps(out["air"]), flush=True)
    out["ah_end"] = ah_end(rec, hubs)
    # the grooves' tops full-round (a ball-end cut concentric with the bead), 0.5 / 0.75 / 1.0 mm of gel over it
    out["grooves"] = {}
    for g in GROOVES:
        out["grooves"][g] = {}
        hg = {label: hub_solve(rec, sig, groove=g) for label, sig in STATES}
        for label, sig in STATES:
            out["grooves"][g][label] = dict(E_null_kV_cm=hg[label]["E_null_kV_cm"])
            for which in ("pol", "eq"):
                out["grooves"][g][label][which] = bead_state(rec, which, sig, hg[label], groove=g, wedge=(g == REC_GROOVE))
                say(f"groove {g}, {which} {label}", out["grooves"][g][label][which])
        out["grooves"][g]["hub_peek"] = hub_peek(rec, hg)
        print(f"groove {g}, PEEK at the hub's scale:", json.dumps(out["grooves"][g]["hub_peek"]), flush=True)
        if g == REC_GROOVE:
            out["grooves"][g]["ah_end"] = ah_end(rec, hg)
        del hg
    # the settled beads against the glass's conductivity over the gel's (the gel at 1e-13 S/m), both grooves
    out["sweep"] = {}
    for g in ("rect", REC_GROOVE):
        out["sweep"][g] = []
        for k in SWEEP:
            sig = k * D.SIG["gel"]
            hq = hub_solve(rec, sig, groove=g)
            row = dict(sigma_glass_over_gel=k, E_null_kV_cm=hq["E_null_kV_cm"])
            for which in ("pol", "eq"):
                row[which] = bead_state(rec, which, sig, hq, groove=g)
                row[which].pop("wedge")
                say(f"sweep {g} {k:g}, {which}", row[which])
            out["sweep"][g].append(row)
    out["run_s"] = time.time() - t0
    json.dump(out, open(os.path.join(HERE, "hub_beads_settled_results.json"), "w"), indent=1, default=float)


if __name__ == "__main__":
    main()
