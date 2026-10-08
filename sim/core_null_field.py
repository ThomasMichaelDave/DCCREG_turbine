"""sim/core_null_field.py -- the strongest steady field at the core's centre, where the AH pair's null sits.

Designer's brief: the AH coils (top and bottom of the sphere) stay independent of the electrostatic side; the centre of
the vacuum core should carry the largest electrostatic field (pressure, 1/2 eps0 E^2) the build allows; the bicone may
go; the electrostatic and magnetic pumps are the supplies.

Why the electrodes go inside the vacuum, on the null [OC]: in charge-free vacuum each Cartesian component of E is
harmonic, so the field at the centre cannot exceed the largest field on the region's boundary. Whatever the geometry,
the field at the null is therefore capped by the field the electrode surfaces may carry, and the best one can do is a
uniform gap whose surface field equals the field at the centre. Electrodes outside the vessel are 84 mm or more apart
(the best ring of sim/core_rings.py gives 0.124 (kV/cm)/kV, 2.6 kV/cm at 20.6 kV); two profiled discs a few mm apart
on the null give V / g.

The design [RH]:
  supply      the electrostatic pump's DC options with 100 pF storage (sim/core_field.py 'dc0 0.1nF' ... 'dc3 0.1nF'):
              electrode A peak-charged from node 1 to -13.2 kV, electrode B on the shaft side (dc0) or charged
              positive by n Cockcroft-Walton stages on node 4's swing (+7.4 / +14.1 / +19.0 kV for n = 1 / 2 / 3);
              20.6 kV across the gap with one stage;
  electrodes  two non-magnetic discs (titanium [RH]) facing each other along the shaft's axis, the gap g centred on the
              null; Rogowski electrodes (design_shape): a flat face of radius max(g, 2 mm), the 90-degree Rogowski
              profile from slope e^-6 to e^1, a closing arc of radius g / 2, each on a stem of radius 2.5 mm out
              through the vessel's wall. The profile study compares a bare stem, spheres and full-round 'pills';
  rule        the repo's vacuum design field, 10 kV/mm (sim/stack_sizing.py), over the vacuum design's margin 1.5
              (sim/air_stack_sizing.py): 6.67 kV/mm on any electrode surface.
  hub         the tube placeholder of sim/core_rings.py: vessel r 42-45 mm; the AH coils as two REF loops around the
              retainer, r 47-53, |z| 18-24 [RH]. The other REF parts are far from the gap and are left out (REF at
              infinity); the glass and composite (dielectrics) are left out too. Neither changes the gap's field
              (checked: with the coils removed E at the centre is unchanged and the surface peak moves 0.2 %).
              The electromagnet register (presets/electromagnets-RA.json) instead puts the AH coils on axial MnZn
              rods just outside a 52 mm vessel's poles; the stems then cannot leave along the axis and must enter from
              the side, turning onto the axis behind each electrode (3-D, not modelled). Checked: that hub (each AH
              winding on its rod as a REF cylinder, r 13 mm, |z| 30.7-72) with stemless electrodes leaves the field
              at the null unchanged and moves the surface peak 0.1 %.
Method [OC]: axisymmetric boundary elements in vacuum. Each conductor's meridian contour is cut into straight panels
of constant surface charge; collocation at the panel midpoints with the ring-charge kernel (complete elliptic K),
the self panel by a u^2 substitution about its log singularity, near panels subdivided. The surface field is sigma /
eps0; the field at a point by the ring formulas (K and E). Self-tests: an isolated sphere (C = 4 pi eps0 R, E = V / R)
and concentric spheres 3 mm apart (C and the inner surface field), both to 1e-4 (gate 2e-3); the design's surface
peak moves 0.06 % with the panels halved.
Usage: python3 sim/core_null_field.py   (writes sim/core_null_field_results.json)
"""
import json
import math
import os
import sys
import time

import numpy as np
from scipy.special import ellipe, ellipk

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

EPS0 = 8.8541878128e-12                                  # F/m
E_OP_KV_MM = 10.0 / 1.5                                  # the vacuum design field over the margin (see the docstring) [RH]
VESSEL = dict(R_in=42.0, R_v=45.0)                       # [RH] the tube placeholder (sim/core_rings.py HUB), mm
COILS = dict(r=(47.0, 53.0), z=(18.0, 24.0))             # [RH] the AH coils' placeholder, REF
STEM_R, STEM_END = 2.5, 50.0                             # [RH] the stems' radius and how far out they are modelled, mm
RA = dict(vessel_od=52.0, rod_z=(30.7, 72.0), coil_r=13.0)  # the register's hub: vessel, AH rod span, winding r [RH]
GAPS = (1.0, 1.5, 2.0, 2.5, 3.0, 3.5, 4.0, 5.0, 6.0, 8.0, 10.0, 12.0)
R_CAP = 30.0                                             # [RH] the electrodes' largest radius: 12 mm clear of the vessel
G_PROFILE = 3.1                                          # the gap of the profile study: dc1's at the design field, mm


# ------------------------------------------------------------------------------------------------- the contours (mm)
def arc(c, R, a0, a1, n):
    t = np.linspace(a0, a1, n)
    return np.column_stack([c[0] + R * np.cos(t), c[1] + R * np.sin(t)])


def pill(g, a, rho, side=+1, rs=STEM_R, z_end=STEM_END):
    """the upper electrode (side +1; -1 mirrors it): from the face's centre on the axis out along the face, round the
    full-round edge, in along the back to the stem, out along the stem to its rounded end on the axis (densely
    sampled; panels are cut later)."""
    z0 = 0.5 * g
    pts = [np.array([[0.0, z0], [a, z0]])]
    pts.append(arc((a, z0 + rho), rho, -0.5 * math.pi, 0.5 * math.pi, 400))
    zb = z0 + 2 * rho
    pts.append(np.array([[a, zb], [rs, zb]]) if a > rs else np.empty((0, 2)))
    pts.append(np.array([[rs, zb], [rs, z_end - rs]]))
    pts.append(arc((0.0, z_end - rs), rs, 0.0, 0.5 * math.pi, 100))
    p = np.vstack([q for q in pts if len(q)])
    p[:, 1] *= side
    return p


def rogowski(g, rf, u0=-3.0, u1=1.0, rc=None, side=+1, rs=STEM_R, z_end=STEM_END):
    """a Rogowski electrode (the 90-degree profile of the map z = (g / pi)(w + 1 + e^w), v = pi / 2, on which the
    field falls from the uniform value as 1 / sqrt(1 + e^2u)) [OC]: a flat face of radius rf, the profile from u0 to
    u1 (slope e^u), then an arc of radius rc (default g / 2) tangent to it, round to the back, and the stem."""
    rc = 0.5 * g if rc is None else rc
    z0 = 0.5 * g
    u = np.linspace(u0, u1, 800)
    x = rf + g / math.pi * (u - u0)
    y = z0 + g / math.pi * (np.exp(u) - math.exp(u0))
    t = np.array([1.0, math.exp(u1)]) / math.hypot(1.0, math.exp(u1))
    c = np.array([x[-1], y[-1]]) + rc * np.array([-t[1], t[0]])        # the arc's centre, inside the body
    th0 = math.atan2(-t[0], t[1])
    pts = [np.array([[0.0, z0], [rf, z0]]), np.column_stack([x, y]),
           arc(c, rc, th0, 0.5 * math.pi, 400)]
    zb = c[1] + rc
    if rs is None:                                                     # no stem: the back closes on the axis
        pts += [np.array([[c[0], zb], [0.0, zb]])]
    else:
        pts += [np.array([[c[0], zb], [rs, zb]]), np.array([[rs, zb], [rs, z_end - rs]]),
                arc((0.0, z_end - rs), rs, 0.0, 0.5 * math.pi, 100)]
    p = np.vstack(pts)
    p[:, 1] *= side
    return p


def ah_on_rod(side=+1, f=2.0):
    """the electromagnet register's AH (presets/electromagnets-RA.json): the winding on its G-10 former round the MnZn
    rod, |z| 30.7-72 mm, taken as one REF cylinder out to the winding's outside, r 13 mm [RH], edges rounded f."""
    r1, z0, z1 = RA["coil_r"], RA["rod_z"][0], RA["rod_z"][1]
    pts = [np.array([[0.0, z0], [r1 - f, z0]]), arc((r1 - f, z0 + f), f, -0.5 * math.pi, 0.0, 40),
           np.array([[r1, z0 + f], [r1, z1 - f]]), arc((r1 - f, z1 - f), f, 0.0, 0.5 * math.pi, 40),
           np.array([[r1 - f, z1], [0.0, z1]])]
    p = np.vstack(pts)
    p[:, 1] *= side
    return p


def ball(g, R, side=+1, rs=STEM_R, z_end=STEM_END):
    """a sphere of radius R on its stem, its pole at g / 2 (the comparison case)."""
    zc = 0.5 * g + R
    th = math.asin(rs / R)
    pts = [arc((0.0, zc), R, -0.5 * math.pi, 0.5 * math.pi - th, 600),
           np.array([[rs, zc + R * math.cos(th)], [rs, z_end - rs]]),
           arc((0.0, z_end - rs), rs, 0.0, 0.5 * math.pi, 100)]
    p = np.vstack(pts)
    p[:, 1] *= side
    return p


def rod(g, side=+1, rs=STEM_R, z_end=STEM_END):
    """a bare stem with a hemispherical tip at g / 2 (the comparison case: a 'point' electrode)."""
    zt = 0.5 * g + rs
    pts = [arc((0.0, zt), rs, -0.5 * math.pi, 0.0, 200), np.array([[rs, zt], [rs, z_end - rs]]),
           arc((0.0, z_end - rs), rs, 0.0, 0.5 * math.pi, 100)]
    p = np.vstack(pts)
    p[:, 1] *= side
    return p


def coil(side=+1, rc=1.0):
    """one AH coil's cross-section as a closed rounded rectangle (REF)."""
    (r0, r1), (z0, z1) = COILS["r"], COILS["z"]
    pts = [arc((r1 - rc, z0 + rc), rc, -0.5 * math.pi, 0.0, 30), arc((r1 - rc, z1 - rc), rc, 0.0, 0.5 * math.pi, 30),
           arc((r0 + rc, z1 - rc), rc, 0.5 * math.pi, math.pi, 30), arc((r0 + rc, z0 + rc), rc, math.pi, 1.5 * math.pi, 30)]
    p = np.vstack(pts + [pts[0][:1]])
    p[:, 1] *= side
    return p


def cut(pts, h_of):
    """cut a densely sampled polyline into panels whose length follows h_of(point) (mm)."""
    seg = np.hypot(*np.diff(pts, axis=0).T)
    s = np.concatenate([[0.0], np.cumsum(seg)])
    out, si = [0.0], 0.0
    while si < s[-1]:
        p = np.array([np.interp(si, s, pts[:, 0]), np.interp(si, s, pts[:, 1])])
        si = min(s[-1], si + h_of(p))
        out.append(si)
    if len(out) > 2 and out[-1] - out[-2] < 0.3 * (out[-2] - out[-3]):  # no sliver at the end
        out.pop(-2)
    out = np.array(out)
    return np.column_stack([np.interp(out, s, pts[:, 0]), np.interp(out, s, pts[:, 1])])


# ------------------------------------------------------------------------------------------------- the solver
GL6, GL16 = np.polynomial.legendre.leggauss(6), np.polynomial.legendre.leggauss(16)


def kern(r, z, rp, zp):
    """the potential at (r, z) of unit surface charge on the ring at (rp, zp), per unit contour length:
    sigma 2 pi rp dl / (4 pi eps0) * (2 / pi) K(m) / D+  =  sigma rp K(m) / (pi eps0 D+) dl   (SI)."""
    d2 = (r + rp) ** 2 + (z - zp) ** 2
    m = np.minimum(4.0 * r * rp / d2, 1.0 - 1e-15)
    return rp * ellipk(m) / (math.pi * EPS0 * np.sqrt(d2))


class Model:
    def __init__(self, bodies):
        """bodies: list of (name, potential key, panel nodes (n, 2) in mm)."""
        p0, p1, owner = [], [], []
        self.names = []
        for k, (name, key, nodes) in enumerate(bodies):
            p0.append(nodes[:-1]); p1.append(nodes[1:]); owner += [k] * (len(nodes) - 1)
            self.names.append((name, key))
        self.p0 = np.vstack(p0) * 1e-3
        self.p1 = np.vstack(p1) * 1e-3
        self.owner = np.array(owner)
        self.mid = 0.5 * (self.p0 + self.p1)
        self.L = np.hypot(*(self.p1 - self.p0).T)
        self.n = len(self.L)
        self.area = 2 * math.pi * self.mid[:, 0] * self.L
        self.A = self._matrix()

    def _matrix(self):
        n, (x6, w6) = self.n, GL6
        A = np.empty((n, n))
        ri, zi = self.mid[:, 0][:, None, None], self.mid[:, 1][:, None, None]
        for j0 in range(0, n, 400):                                     # regular: 6-point Gauss on every panel
            j = slice(j0, min(n, j0 + 400))
            q = self.mid[j][None, :, None, :] + 0.5 * x6[None, None, :, None] * (self.p1[j] - self.p0[j])[None, :, None, :]
            k = kern(ri, zi, q[..., 0], q[..., 1])
            A[:, j] = np.sum(k * w6, axis=2) * 0.5 * self.L[j][None, :]
        # near panels: 12 sub-panels x 6 points; the self panel: halves with s = u^2
        d = np.hypot(self.mid[:, None, 0] - self.mid[None, :, 0], self.mid[:, None, 1] - self.mid[None, :, 1])
        near = np.argwhere((d < 4.0 * self.L[None, :]) & ~np.eye(n, dtype=bool))
        sub = (np.arange(12) + 0.5)[:, None] / 12 + x6[None, :] / 24    # in (0, 1)
        sw = np.repeat(w6[None, :] / 24, 12, axis=0).ravel()
        for i, j in near:
            t = sub.ravel()
            q = self.p0[j] + t[:, None] * (self.p1[j] - self.p0[j])
            A[i, j] = np.sum(kern(self.mid[i, 0], self.mid[i, 1], q[:, 0], q[:, 1]) * sw) * self.L[j]
        x16, w16 = GL16
        u, wu = 0.5 * (x16 + 1.0), 0.5 * w16
        for i in range(n):
            e = (self.p1[i] - self.p0[i]) / self.L[i]
            v = 0.0
            for sgn in (+1.0, -1.0):
                s = 0.5 * self.L[i] * u * u                             # distance from the midpoint
                q = self.mid[i] + sgn * s[:, None] * e
                v += np.sum(kern(self.mid[i, 0], self.mid[i, 1], q[:, 0], q[:, 1]) * wu * self.L[i] * u)
            A[i, i] = v
        return A

    def solve(self, pots):
        """surface charge for the conductor potentials pots {key: V} (keys not given are at 0)."""
        rhs = np.array([pots.get(self.names[k][1], 0.0) for k in self.owner])
        return np.linalg.solve(self.A, rhs)

    def charge(self, sig, key):
        m = np.array([self.names[k][1] == key for k in self.owner])
        return float(np.sum(sig[m] * self.area[m]))

    def field(self, sig, r, z):
        """E_r, E_z (V/m) at points (r, z) in metres (arrays), off the conductors."""
        r, z = np.atleast_1d(r).astype(float), np.atleast_1d(z).astype(float)
        x, w = GL6
        Er, Ez = np.zeros_like(r), np.zeros_like(r)
        for j0 in range(0, self.n, 200):
            j = slice(j0, min(self.n, j0 + 200))
            q = self.mid[j][:, None, :] + 0.5 * x[None, :, None] * (self.p1[j] - self.p0[j])[:, None, :]
            rp, zp = q[..., 0][None], q[..., 1][None]                   # (1, nj, 6)
            dq = (sig[j] * 2 * math.pi * 0.5 * self.L[j])[None, :, None] * rp * w[None, None, :]
            R, Z = r[:, None, None], z[:, None, None]
            dz = Z - zp
            dp2, dm2 = (R + rp) ** 2 + dz ** 2, (R - rp) ** 2 + dz ** 2
            m = np.minimum(4 * R * rp / dp2, 1.0 - 1e-15)
            K, E = ellipk(m), ellipe(m)
            c = dq / (4 * math.pi * EPS0) / (math.pi * np.sqrt(dp2))
            Ez += np.sum(c * 2 * dz * E / dm2, axis=(1, 2))
            with np.errstate(invalid="ignore", divide="ignore"):
                er = c / R * (K - (rp ** 2 - R ** 2 + dz ** 2) / dm2 * E)
            Er += np.sum(np.where(R > 0, er, 0.0), axis=(1, 2))
        return Er, Ez

    def potential(self, sig, r, z):
        r, z = np.atleast_1d(r).astype(float), np.atleast_1d(z).astype(float)
        x, w = GL6
        out = np.zeros_like(r)
        for j0 in range(0, self.n, 200):
            j = slice(j0, min(self.n, j0 + 200))
            q = self.mid[j][:, None, :] + 0.5 * x[None, :, None] * (self.p1[j] - self.p0[j])[:, None, :]
            k = kern(r[:, None, None], z[:, None, None], q[..., 0][None], q[..., 1][None])
            out += np.sum(k * w[None, None, :] * (sig[j] * 0.5 * self.L[j])[None, :, None], axis=(1, 2))
        return out


# ------------------------------------------------------------------------------------------------- the cases
def h_rule(g):
    """panel length: g / 40 at the gap, growing with the distance from the face's centre to 0.8 mm."""
    return lambda p: float(np.clip(g / 40.0 + 0.06 * max(0.0, math.hypot(p[0], abs(p[1]) - 0.5 * g) - 0.5 * g),
                                   g / 40.0, 0.8))


def design_shape(g):
    """the design electrode for a gap g: Rogowski, flat face r = max(g, 2 mm), the profile from slope e^-6 (a smooth
    join) to e^1, closing arc g / 2; above about 8 mm the flat face (then the profile's start) shrinks to keep the
    electrode within R_CAP."""
    u1, rc = 1.0, 0.5 * g
    for u0 in (-6.0, -5.0, -4.0):
        rf = min(max(g, 2.0), R_CAP - g / math.pi * (u1 - u0) - rc)
        if rf >= 0.0:
            return dict(rf=float(rf), u0=u0, u1=u1, rc=rc)
    return dict(rf=0.0, u0=-4.0, u1=u1, rc=rc)


def build(shape, g, coils=True, hf=1.0, ah_rods=False, **kw):
    h0 = h_rule(g)
    h = (lambda p: hf * h0(p)) if hf != 1.0 else h0
    mk = dict(pill=pill, ball=ball, rod=rod, rogowski=rogowski)[shape]
    # A (node 1's side, negative) below the null, B above: as the schematic draws the old cones A / B
    bodies = [("electrode A", "A", cut(mk(g, side=-1, **kw), h)), ("electrode B", "B", cut(mk(g, side=+1, **kw), h))]
    if coils:
        bodies += [("AH coil, top", "REF", cut(coil(+1), lambda p: 0.6)), ("AH coil, bottom", "REF", cut(coil(-1), lambda p: 0.6))]
    if ah_rods:
        bodies += [("AH on its rod, top", "REF", cut(ah_on_rod(+1), lambda p: 0.6)),
                   ("AH on its rod, bottom", "REF", cut(ah_on_rod(-1), lambda p: 0.6))]
    return Model(bodies)


def analyse(m, g, label, shape_kw, supplies):
    """the unit solutions and, per supply, the surface field and the field at the centre."""
    sA, sB = m.solve({"A": 1.0}), m.solve({"B": 1.0})
    C = {(x, y): (m.charge(sA, x) if y == "A" else m.charge(sB, x)) for x in ("A", "B") for y in ("A", "B")}
    c_gap = -0.5 * (C[("A", "B")] + C[("B", "A")])
    out = dict(label=label, g_mm=g, shape=shape_kw, n_panels=m.n,
               C_gap_pF=c_gap * 1e12, C_A_ref_pF=(C[("A", "A")] - c_gap) * 1e12, C_B_ref_pF=(C[("B", "B")] - c_gap) * 1e12)
    # the differential solution, A -1/2 and B +1/2 (1 V across the gap, B positive: E points down, from B to A)
    sd = 0.5 * (sB - sA)
    ez0 = float(m.field(sd, np.array([0.0]), np.array([0.0]))[1][0])
    Ez0 = np.array([abs(ez0)])
    out["E0_per_V_m"] = float(Ez0[0])                                   # V/m per volt across the gap
    out["uniformity"] = float(Ez0[0] * g * 1e-3)                        # E0 g / V: 1 for an ideal gap
    onA = np.array([m.names[k][1] == "A" for k in m.owner])
    vac = np.hypot(*m.mid.T) * 1e3 < VESSEL["R_in"]                    # in the vacuum: the rule applies there only
    out["k_surf_diff"] = float(np.abs(sd[onA & vac]).max() / EPS0 / Ez0[0])   # peak surface field / E0, differential
    # along the axis in the gap and along the midplane: the field's uniformity
    zz = np.linspace(-0.45, 0.45, 19) * g * 1e-3
    out["Ez_axis_rel"] = (m.field(sd, np.zeros_like(zz), zz)[1] / ez0).tolist()
    out["z_axis_mm"] = (zz * 1e3).tolist()
    rr = np.linspace(0.0, 3.0, 61) * g * 1e-3
    er = m.field(sd, rr, np.zeros_like(rr))[1] / ez0
    out["Ez_mid_rel"] = er.tolist()
    out["r_mid_mm"] = (rr * 1e3).tolist()
    below = np.nonzero(er < 0.99)[0]
    out["r_uniform_1pc_mm"] = float(rr[below[0]] * 1e3) if len(below) else None
    out["supplies"] = {}
    for nm, (va, vb) in supplies.items():
        s = va * sA + vb * sB
        e = np.abs(s) / EPS0
        iA, iB = int(np.argmax(np.where(onA & vac, e, 0))), int(np.argmax(np.where(~onA & (m.owner < 2) & vac, e, 0)))
        out["supplies"][nm] = dict(V_A_kV=va / 1e3, V_B_kV=vb / 1e3, E0_kV_mm=float(Ez0[0] * (vb - va) / 1e6),
                                   Esurf_A_kV_mm=float(e[iA] / 1e6), at_A_mm=list(map(float, m.mid[iA] * 1e3)),
                                   Esurf_B_kV_mm=float(e[iB] / 1e6), at_B_mm=list(map(float, m.mid[iB] * 1e3)))
        q = out["supplies"][nm]
        q["Esurf_max_kV_mm"] = max(q["Esurf_A_kV_mm"], q["Esurf_B_kV_mm"])
        q["k_surf"] = q["Esurf_max_kV_mm"] / q["E0_kV_mm"]
        q["p0_Pa"] = 0.5 * EPS0 * (q["E0_kV_mm"] * 1e6) ** 2
        # the stem where it meets the vessel's wall (the feedthrough's vacuum side), from the solution itself
        for el, on in (("A", onA), ("B", ~onA & (m.owner < 2))):
            st = np.nonzero(on & (np.abs(m.mid[:, 0] * 1e3 - STEM_R) < 1e-6) & (np.abs(m.mid[:, 1]) * 1e3 < VESSEL["R_in"]))[0]
            if len(st):
                q[f"E_stem_{el}_at_wall_kV_mm"] = float(e[st[np.argmax(np.abs(m.mid[st, 1]))]] / 1e6)
    return out


def selftest():
    """an isolated sphere, and a sphere inside a concentric shell 3 mm away."""
    R = 10.0
    sph = arc((0.0, 0.0), R, -0.5 * math.pi, 0.5 * math.pi, 2000)
    m = Model([("sphere", "A", cut(sph, lambda p: 0.25))])
    s = m.solve({"A": 1.0})
    c = m.charge(s, "A")
    t1 = dict(C_pF=c * 1e12, C_exact_pF=4 * math.pi * EPS0 * R * 1e-3 * 1e12,
              E_surf=float(np.mean(s / EPS0)), E_exact=1.0 / (R * 1e-3), E_spread=float(np.ptp(s / EPS0) / np.mean(s / EPS0)))
    R2 = 13.0
    shell = arc((0.0, 0.0), R2, -0.5 * math.pi, 0.5 * math.pi, 2000)
    m = Model([("inner", "A", cut(sph, lambda p: 0.1)), ("shell", "REF", cut(shell, lambda p: 0.1))])
    s = m.solve({"A": 1.0})
    c = m.charge(s, "A")
    onA = m.owner == 0
    ex = 4 * math.pi * EPS0 * R * R2 / (R2 - R) * 1e-3
    t2 = dict(C_pF=c * 1e12, C_exact_pF=ex * 1e12, E_surf=float(np.mean(s[onA] / EPS0)),
              E_exact=R2 / (R * (R2 - R)) * 1e3)
    for t in (t1, t2):
        t["C_err"] = t["C_pF"] / t["C_exact_pF"] - 1.0
        t["E_err"] = t["E_surf"] / t["E_exact"] - 1.0
    return dict(sphere=t1, concentric_3mm=t2, ok=bool(max(abs(t1["C_err"]), abs(t1["E_err"]), abs(t2["C_err"]),
                                                           abs(t2["E_err"])) < 2e-3))


SUPPLY_ROWS = {"dc0": "dc0 0.1nF", "dc1": "dc1 0.1nF", "dc2": "dc2 0.1nF", "dc3": "dc3 0.1nF"}   # 100 pF storage


def supplies():
    """the DC options as simulated with 100 pF storage (sim/core_field_results.json, means over the last cycles), V:
    dc<n> = electrode A on node 1's peak, electrode B on n Cockcroft-Walton stages (dc0: on the shaft side)."""
    rows = {r["name"]: r for r in json.load(open(os.path.join(HERE, "core_field_results.json")))["rows"]}
    out = {}
    for nm, row in SUPPLY_ROWS.items():
        r = rows[row]
        out[nm] = (r["V_ea_kV"]["mean"] * 1e3, r["V_eb_kV"]["mean"] * 1e3)
    sw = rows["float ss"]["swing_pk_kV"] * 1e3                           # the swinging option's peak, for reference
    out["float (peak)"] = (-0.5 * sw, 0.5 * sw)
    return out


def main():
    t0 = time.time()
    st = selftest()
    print("self-test:", json.dumps(st, default=float), flush=True)
    sup = supplies()
    # 1. the profile at the dc1 design gap
    g = G_PROFILE
    dsg = design_shape(g)
    prof = [("rod", dict(), "bare stem, hemispherical tip r 2.5"),
            ("ball", dict(R=5.0), "sphere r 5"),
            ("ball", dict(R=10.0), "sphere r 10"),
            ("pill", dict(a=g, rho=g), f"pill: flat r {g:g}, full-round edge r {g:g}"),
            ("pill", dict(a=2 * g, rho=2 * g), f"pill: flat r {2 * g:g}, edge r {2 * g:g}"),
            ("rogowski", dict(dsg, u0=-3.0), "Rogowski, profile from slope e^-3 (a 2.9 deg kink)"),
            ("rogowski", dsg, f"Rogowski, flat r {dsg['rf']:g} (the design)"),
            ("rogowski", dict(dsg, rf=2 * g), f"Rogowski, flat r {2 * g:g}")]
    profile = []
    for shape, kw, lab in prof:
        m = build(shape, g, **kw)
        q = analyse(m, g, lab, dict(shape=shape, **kw), sup)
        q["R_max_mm"] = float(m.p0[m.owner == 0][:, 0].max() * 1e3)
        profile.append(q)
        s1 = q["supplies"]["dc1"]
        print(f"{lab:52s} n {m.n:5d}  E0 g/V {q['uniformity']:.4f}  k_surf {q['k_surf_diff']:.4f} (dc1 {s1['k_surf']:.4f})  "
              f"C_gap {q['C_gap_pF']:.2f} pF  r_1% {q['r_uniform_1pc_mm']}", flush=True)
    # the checks: the coils removed (the REF parts' influence), and the panels halved (convergence)
    nocoil = analyse(build("rogowski", g, coils=False, **dsg), g, "design, no coils", dict(shape="rogowski", **dsg), sup)
    fine = analyse(build("rogowski", g, hf=0.5, **dsg), g, "design, panels halved", dict(shape="rogowski", **dsg), sup)
    # the register's hub: the AH windings on their rods on the axis (REF) and no axial stems (they would enter from the
    # side, behind the electrodes; not axisymmetric, so left out)
    ra = analyse(build("rogowski", g, coils=False, ah_rods=True, rs=None, **dsg), g, "design, register hub (AH on rods)",
                 dict(shape="rogowski", rs=None, **dsg), sup)
    for q in (nocoil, fine, ra):
        for k in ("Ez_axis_rel", "z_axis_mm", "Ez_mid_rel", "r_mid_mm"):
            q.pop(k)
        print(q["label"], "E0 g/V %.5f k %.4f k_dc1 %.4f C_gap %.3f" % (q["uniformity"], q["k_surf_diff"],
                                                                     q["supplies"]["dc1"]["k_surf"], q["C_gap_pF"]))
    # 2. the gap sweep with the design electrode
    sweep = []
    for g in GAPS:
        dsg = design_shape(g)
        m = build("rogowski", g, **dsg)
        q = analyse(m, g, f"Rogowski, flat r {dsg['rf']:.2f}", dict(shape="rogowski", **dsg), sup)
        q["R_max_mm"] = float(m.p0[m.owner == 0][:, 0].max() * 1e3)
        for k in ("Ez_axis_rel", "z_axis_mm"):
            q.pop(k)
        sweep.append(q)
        print(f"g {g:5.1f}  rf {dsg['rf']:5.2f} u0 {dsg['u0']:g} Rmax {q['R_max_mm']:5.1f}  n {m.n:5d}  E0 g/V {q['uniformity']:.4f}  "
              f"k {q['k_surf_diff']:.4f}  " + "  ".join(f"{nm}: E0 {x['E0_kV_mm']:.2f} Es {x['Esurf_max_kV_mm']:.2f}"
                                                     for nm, x in q["supplies"].items()), flush=True)
    # 3. per supply: the smallest gap whose peak surface field meets the design field, and the field there
    design = {}
    for nm in sup:
        gs = np.array([q["g_mm"] for q in sweep])
        es = np.array([q["supplies"][nm]["Esurf_max_kV_mm"] for q in sweep])
        e0 = np.array([q["supplies"][nm]["E0_kV_mm"] for q in sweep])
        ok = es <= E_OP_KV_MM
        if not ok.any():
            design[nm] = None
            continue
        i = int(np.argmax(ok))                                          # the first gap that holds (es falls with g)
        if i == 0:
            gd, ed = gs[0], e0[0]
        else:                                                           # interpolate in log g where es crosses E_op
            lg = np.interp(math.log(E_OP_KV_MM), np.log(es[[i, i - 1]]), np.log(gs[[i, i - 1]]))
            gd = float(math.exp(lg))
            ed = float(math.exp(np.interp(lg, np.log(gs[[i - 1, i]]), np.log(e0[[i - 1, i]]))))
        # solve at that gap (two passes of the secant on the surface field) and keep the exact numbers
        for _ in range(2):
            dsg = design_shape(gd)
            q = analyse(build("rogowski", gd, **dsg), gd, "design", dict(shape="rogowski", **dsg), {nm: sup[nm]})
            gd = gd * q["supplies"][nm]["Esurf_max_kV_mm"] / E_OP_KV_MM
        dsg = design_shape(gd)
        m = build("rogowski", gd, **dsg)
        q = analyse(m, gd, "design", dict(shape="rogowski", **dsg), {nm: sup[nm]})
        x = q["supplies"][nm]
        design[nm] = dict(g_min_mm=float(gd), shape=dsg, R_max_mm=float(m.p0[m.owner == 0][:, 0].max() * 1e3),
                          E0_kV_mm=x["E0_kV_mm"], E0_kV_cm=10 * x["E0_kV_mm"], Esurf_max_kV_mm=x["Esurf_max_kV_mm"],
                          k_surf=x["k_surf"], p0_Pa=x["p0_Pa"], V_A_kV=x["V_A_kV"], V_B_kV=x["V_B_kV"],
                          V_gap_kV=x["V_B_kV"] - x["V_A_kV"], C_gap_pF=q["C_gap_pF"], C_A_ref_pF=q["C_A_ref_pF"],
                          C_B_ref_pF=q["C_B_ref_pF"], r_uniform_1pc_mm=q["r_uniform_1pc_mm"],
                          E_stem_A_at_wall_kV_mm=x.get("E_stem_A_at_wall_kV_mm"),
                          E_stem_B_at_wall_kV_mm=x.get("E_stem_B_at_wall_kV_mm"),
                          Ez_axis_rel=q["Ez_axis_rel"], z_axis_mm=q["z_axis_mm"], Ez_mid_rel=q["Ez_mid_rel"],
                          r_mid_mm=q["r_mid_mm"])
        print(nm, {k: v for k, v in design[nm].items() if not isinstance(v, list)}, flush=True)
    out = dict(note="see the module docstring", E_op_kV_mm=E_OP_KV_MM, vessel=VESSEL, coils=COILS, stem_r_mm=STEM_R,
               stem_end_mm=STEM_END, selftest=st, supplies_V={k: list(v) for k, v in sup.items()},
               profile_gap_mm=G_PROFILE, profile=profile, no_coils=nocoil, panels_halved=fine, register_hub=ra, ra_hub=RA,
               sweep=sweep, design=design,
               run_s=time.time() - t0)
    json.dump(out, open(os.path.join(HERE, "core_null_field_results.json"), "w"), indent=1, default=float)
    print(f"done in {time.time() - t0:.0f} s")


if __name__ == "__main__":
    main()
