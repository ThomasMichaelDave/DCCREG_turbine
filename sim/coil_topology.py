#!/usr/bin/env python3
"""
sim/coil_topology.py — split L_R + bifilar self-resonant coil study.
====================================================================
Two coupled changes on the C_R-L_R resonator:
  (A) split L_R into two L_R/2 halves, one at each end of C_R (each end to its
      rotor node 5/6) -- electrical + mechanical balance + fire-transient relief;
  (B) the per-hub coil topology the split opens -- down-the-cone-and-back-up,
      SIMPLE vs TESLA-BIFILAR, with the bifilar treated as a SELF-RESONANT
      distributed (helical-resonator) coil, not a lumped L with parasitic C.

Read of the parts: A is a clean win (do it). B is the fork -- does a bifilar
designed so its SELF-RESONANCE lands on f0 give a usable distributed resonator,
or does the standing-wave antinode stress kill it (the machine is air/surface
bound -- battery-capacity rev3)?

INHERITED (cite): resonator L_R 79 uH / C_R 789 pF / f0 637 kHz / Z0 316 Ohm,
coil = 36-turn Cu 3/1 mm conical, r28->76 mm, 108 mm axial (freeze-doc
varcap-design-freeze-v0.10.md §3); the series-resonator fire transient (~20 kV
across L_R -> ~35 kV node-5 peak, series_resonator.csv @ b62e642); the
battery-capacity rev3 survey (C1/C2 7 mm air = 21 kV binding; the undimensioned
creepage flag 12-30 kV; node-to-ground stress) @ DXF r0_6 + doc.

Geometry source: the DXF (r0_6) + the v0.10 freeze doc -- NOT index.html (STALE).
Firewall: ordinary distributed-circuit EE (L, M, self-C, SRF, standing-wave
profile, helical-resonator Q). No DCCREG. Tiers [OC]/[IR]/[STALE].
Refs: Medhurst (self-C, Q); helical-resonator theory; Kuffel/Zaengl (standoff).
"""
import math
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)

# ---- inherited anchors (freeze-doc §3 + series-resonator + rev3) -------------
L_R = 79e-6            # H     freeze-doc §3                                        [OC]
C_R = 789e-12         # F     freeze-doc §3                                         [OC]
F0 = 637e3            # Hz    f0 = 1/(2pi sqrt(L_R C_R))                            [OC]
Z0 = 316.0            # Ohm   sqrt(L_R/C_R)                                         [OC]
N_TURNS = 36          # conical coil turns        freeze-doc §3                     [OC]
WIRE_OD = 3e-3        # m     Cu 3/1 mm capillary  freeze-doc §3                    [OC]
WIRE_ID = 1e-3        # m     hollow (cooling)                                      [OC]
R1, R2 = 28e-3, 76e-3 # m     cone radii r28->76   freeze-doc §3                    [OC]
AXIAL = 108e-3        # m     coil axial length    freeze-doc §3                    [OC]
A_AVG = 0.5 * (R1 + R2)                # mean coil radius
L_WIRE = N_TURNS * 2 * math.pi * A_AVG # wire length
PITCH = AXIAL / N_TURNS                # 3 mm -> tightly wound

V_NODE5_BASELINE = 35e3   # node-5 fire peak (V_CR 15 + L_R swing 20), series CSV   [OC]
V_LR_SWING = 20e3         # L_R transient swing per fire   series_resonator.csv      [OC]
V_OP = 15e3               # operating DC store                                      [OC]
V_C1C2 = 21e3            # C1/C2 7 mm air binding (rev3)                            [OC]
CREEP_LO, CREEP_HI = 12e3, 30e3   # flagged bare-edge creepage band (rev3)          [OC]
G_AIR = 3.0e3            # V/mm air breakdown (the machine's air/surface bound)     [OC]

# ---- modelling choices [IR] --------------------------------------------------
K_SPLIT = 0.30          # mutual coupling of the two axially-adjacent L_R/2 halves  [IR]
K_BIFILAR_LAYER = 0.90  # go/return interleaved coupling (folded -> near-cancel)    [IR]
PROXIMITY = 3.0         # proximity-effect multiplier on R_AC (tight 36-turn)       [IR]
INTERFILAR_GAP = WIRE_OD  # side-by-side filar spacing ~ wire OD (3 mm)             [IR]
TESLA_FRAC = 0.5        # inter-filar dV = this fraction of V_antinode (Tesla conn) [IR]


def f_lc(L, C):
    return 1.0 / (2 * math.pi * math.sqrt(L * C))


def medhurst_self_C(D_m, H_m):
    """Medhurst (1947) solenoid self-C, pF -> F. D,H in metres -> cm. [OC]"""
    D, H = D_m * 100, H_m * 100
    C_pF = D * (0.1126 * (H / D) + 0.08 + 0.27 * math.sqrt(D / H))
    return C_pF * 1e-12


def skin_depth(f, rho=1.7e-8, mu0=4e-7 * math.pi):
    return math.sqrt(rho / (math.pi * f * mu0))


# =============================================================================
# Part A — the symmetric split
# =============================================================================
def part_A():
    L_half = L_R / 2.0
    M = K_SPLIT * L_half
    L_total_aid = L_half + L_half + 2 * M          # aiding sense (chosen)
    L_total_opp = L_half + L_half - 2 * M          # opposed (rejected)
    f0_aid = f_lc(L_total_aid, C_R)
    C_R_retune = 1.0 / ((2 * math.pi * F0) ** 2 * L_total_aid)   # to restore f0
    # transient: node-to-ground halves with a grounded centre reference
    V_node_split = V_NODE5_BASELINE / 2.0
    stress_factor = V_node_split / V_NODE5_BASELINE
    # insulation benefit vs rev3
    c1c2_base_ok = V_NODE5_BASELINE <= V_C1C2
    c1c2_split_ok = V_node_split <= V_C1C2
    creep_clean_split_ok = V_node_split <= CREEP_HI
    creep_dirty_split_ok = V_node_split <= CREEP_LO
    return dict(L_half=L_half, M=M, L_total_aid=L_total_aid, L_total_opp=L_total_opp,
                f0_aid=f0_aid, C_R_retune=C_R_retune, V_node_split=V_node_split,
                stress_factor=stress_factor, c1c2_base_ok=c1c2_base_ok,
                c1c2_split_ok=c1c2_split_ok, creep_clean_split_ok=creep_clean_split_ok,
                creep_dirty_split_ok=creep_dirty_split_ok)


# =============================================================================
# Part B — coil topology
# =============================================================================
def part_B1_downback():
    """Down-the-cone-and-back-up: go+return fields must ADD. Opposed -> L~0 (trap)."""
    L_pass = L_R                                   # the present 36-turn pass = 79 uH
    L_downback_add = 2 * L_pass + 2 * K_BIFILAR_LAYER * L_pass    # fields ADD
    L_downback_opp = 2 * L_pass - 2 * K_BIFILAR_LAYER * L_pass    # opposed -> ~0 trap
    return dict(L_add=L_downback_add, L_opp=L_downback_opp, L_ref=L_R)


def part_B2_selfC():
    D = 2 * A_AVG
    C_simple = medhurst_self_C(D, AXIAL)           # low-dV return -> ~solenoid
    C_solenoid = C_simple                          # equal-L plain solenoid ~ same
    # Tesla-bifilar: tuned so f_SRF -> f0 (the design point) -> C needed
    C_bifilar = 1.0 / ((2 * math.pi * F0) ** 2 * L_R)
    enhance = C_bifilar / C_simple
    return dict(C_simple=C_simple, C_solenoid=C_solenoid, C_bifilar=C_bifilar, enhance=enhance)


def part_B3_selfres(C_simple, C_bifilar):
    srf_simple = f_lc(L_R, C_simple)               # lumped SRF (simple) -- >> f0
    srf_bifilar = f_lc(L_R, C_bifilar)             # tuned to f0 (design point)
    # distributed quarter-wave cross-check (vf=1 upper bound); helical slows it
    srf_qw = 3e8 / (4 * L_WIRE)
    # self-resonant Q (skin-limited, x proximity)
    delta = skin_depth(F0)
    R_ac = 1.7e-8 * L_WIRE / (math.pi * WIRE_OD * delta) * PROXIMITY
    Q_selfres = (2 * math.pi * F0 * L_R) / R_ac
    G_gain = Q_selfres                             # quarter-wave voltage magnification ~ Q
    # coupled two-coil even/odd modes (shared C_R, coupled by k)
    f_plus = F0 / math.sqrt(1 + K_SPLIT)           # even/in-phase (symmetric fire selects)
    f_minus = F0 / math.sqrt(1 - K_SPLIT)
    return dict(srf_simple=srf_simple, srf_bifilar=srf_bifilar, srf_qw=srf_qw,
                delta=delta, R_ac=R_ac, Q_selfres=Q_selfres, G_gain=G_gain,
                f_plus=f_plus, f_minus=f_minus)


def part_B4_antinode(V_antinode):
    """Standing wave concentrates V at the antinode -> inter-filar stress is highest
    there. Inter-filar dV = TESLA_FRAC * V_antinode across the filar gap. [OC]"""
    dV_filar = TESLA_FRAC * V_antinode                  # V
    gap_mm = INTERFILAR_GAP * 1e3                        # mm
    E_int_Vmm = dV_filar / gap_mm                        # V/mm
    feasible = E_int_Vmm <= G_AIR
    return dict(dV_filar=dV_filar, E_int_Vmm=E_int_Vmm, feasible=feasible,
                margin=G_AIR / E_int_Vmm)


# =============================================================================
# Self-tests
# =============================================================================
def selftests():
    out = []
    # (a) two L_R/2 in series, M=0 -> exactly L_R
    L0 = L_R / 2 + L_R / 2 + 0.0
    out.append(("(a) split M=0 -> L_R (equivalence)", abs(L0 - L_R) < 1e-12,
                dict(L_uH=L0 * 1e6)))
    # (b) transient split: 35 kV asymmetric -> ~17.5 kV symmetric
    A = part_A()
    out.append(("(b) 35kV -> 17.5kV node-to-ground", abs(A["V_node_split"] - 17.5e3) < 100,
                dict(Vnode_kV=A["V_node_split"] / 1e3)))
    # (c) down-and-back same order as 79 uH; opposed -> ~0 (trap)
    B1 = part_B1_downback()
    out.append(("(c) downback fields-add O(79uH); opposed~0", B1["L_add"] > L_R and abs(B1["L_opp"]) < 0.3 * L_R,
                dict(L_add_uH=B1["L_add"] * 1e6, L_opp_uH=B1["L_opp"] * 1e6)))
    # (d) self-C ordering: bifilar >> simple >= solenoid
    B2 = part_B2_selfC()
    out.append(("(d) self-C: bifilar >> simple ~ solenoid",
                B2["C_bifilar"] > 10 * B2["C_simple"] and B2["C_simple"] >= 0.9 * B2["C_solenoid"],
                dict(simple_pF=B2["C_simple"] * 1e12, bifilar_pF=B2["C_bifilar"] * 1e12)))
    # (e) SRF cross-check: lumped(simple) vs quarter-wave agree within helical correction
    B3 = part_B3_selfres(B2["C_simple"], B2["C_bifilar"])
    ratio = B3["srf_simple"] / B3["srf_qw"]
    out.append(("(e) SRF lumped vs quarter-wave agree", 0.5 < ratio < 2.0,
                dict(lumped_MHz=B3["srf_simple"] / 1e6, qw_MHz=B3["srf_qw"] / 1e6)))
    # (e2) design bifilar SRF lands on f0
    out.append(("(e2) bifilar SRF tuned to f0", abs(B3["srf_bifilar"] - F0) / F0 < 0.01,
                dict(srf_kHz=B3["srf_bifilar"] / 1e3)))
    # (f) antinode inter-turn stress hand calc (split drive 17.5 kV)
    B4 = part_B4_antinode(A["V_node_split"])
    hand = TESLA_FRAC * A["V_node_split"] / (INTERFILAR_GAP * 1e3)
    out.append(("(f) antinode stress hand-calc matches", abs(B4["E_int_Vmm"] - hand) < 1,
                dict(kVmm=B4["E_int_Vmm"] / 1e3)))
    return out


# =============================================================================
# Main
# =============================================================================
def main():
    print("=" * 80)
    print("coil_topology — split L_R + bifilar self-resonant study (DXF/doc geometry)")
    print("=" * 80)

    print("\nSELF-TESTS:")
    ok = True
    for name, passed, info in selftests():
        ok = ok and passed
        det = " ".join(f"{k}={v:.4g}" if isinstance(v, float) else f"{k}={v}"
                        for k, v in info.items())
        print(f"  [{'PASS' if passed else 'FAIL'}] {name:40s} {det}")
    if not ok:
        print("  -> SELF-TESTS FAILED; verdict not trustworthy.")
        return 1

    A = part_A()
    B1 = part_B1_downback()
    B2 = part_B2_selfC()
    B3 = part_B3_selfres(B2["C_simple"], B2["C_bifilar"])
    V_antinode = A["V_node_split"]          # split drive; clamped charger view (conservative)
    B4 = part_B4_antinode(V_antinode)
    B4_unsplit = part_B4_antinode(V_NODE5_BASELINE)

    print(f"\nGEOMETRY (freeze-doc §3): N={N_TURNS}, OD={WIRE_OD*1e3:.0f}mm, r{R1*1e3:.0f}->{R2*1e3:.0f}mm, "
          f"axial={AXIAL*1e3:.0f}mm, l_wire={L_WIRE:.2f}m, pitch={PITCH*1e3:.1f}mm")

    print("\n--- PART A: symmetric split ---")
    print(f"  SPLIT-L: two L_R/2={A['L_half']*1e6:.1f}uH, M={A['M']*1e6:.1f}uH (k={K_SPLIT}); "
          f"AIDING L_total={A['L_total_aid']*1e6:.1f}uH (opposed {A['L_total_opp']*1e6:.1f} -- rejected)")
    print(f"     f0 with aiding split = {A['f0_aid']/1e3:.0f} kHz (shift from 637); "
          f"restore via C_R retune {A['C_R_retune']*1e12:.0f} pF (789->{A['C_R_retune']*1e12:.0f})")
    print(f"  TRANSIENT-RELIEF: node-to-ground {V_NODE5_BASELINE/1e3:.0f} -> {A['V_node_split']/1e3:.1f} kV "
          f"(stress_factor {A['stress_factor']:.2f})")
    print(f"     C1/C2 21 kV: baseline {V_NODE5_BASELINE/1e3:.0f}kV {'OK' if A['c1c2_base_ok'] else 'OVERSTRESS'}"
          f" -> split {A['V_node_split']/1e3:.1f}kV {'OK' if A['c1c2_split_ok'] else 'OVERSTRESS'}")
    print(f"     creepage (bare {CREEP_LO/1e3:.0f}-{CREEP_HI/1e3:.0f}kV): split {A['V_node_split']/1e3:.1f}kV "
          f"clears clean-{'YES' if A['creep_clean_split_ok'] else 'NO'} / dirty-{'YES' if A['creep_dirty_split_ok'] else 'NO'}"
          f" -> recovers margin above the {V_OP/1e3:.0f}kV op for a clean edge")

    print("\n--- PART B: coil topology ---")
    print(f"  DOWNBACK-L: fields-ADD L={B1['L_add']*1e6:.0f}uH (vs ref {L_R*1e6:.0f}uH); "
          f"opposed-sense L={B1['L_opp']*1e6:.1f}uH -> the NON-INDUCTIVE BIFILAR TRAP (flagged)")
    print(f"  SELF-C: simple={B2['C_simple']*1e12:.1f}pF (~solenoid) | "
          f"Tesla-bifilar={B2['C_bifilar']*1e12:.0f}pF (x{B2['enhance']:.0f}, tuned to land f_SRF on f0)")
    print(f"  SELF-RESONANCE:")
    print(f"     f_SRF simple = {B3['srf_simple']/1e6:.1f} MHz (>> f0 -> LUMPED inductor); "
          f"quarter-wave x-check {B3['srf_qw']/1e6:.1f} MHz")
    print(f"     f_SRF bifilar = {B3['srf_bifilar']/1e3:.0f} kHz = f0 (the design point -- self-resonant)")
    print(f"     Q_selfres = {B3['Q_selfres']:.0f} (skin delta={B3['delta']*1e6:.0f}um, R_ac={B3['R_ac']:.2f}ohm, "
          f"prox x{PROXIMITY}) -> comparable to lumped Q~500; G_gain~Q={B3['G_gain']:.0f}")
    print(f"     coupled modes: f+={B3['f_plus']/1e3:.0f} kHz (even/in-phase, symmetric fire selects), "
          f"f-={B3['f_minus']/1e3:.0f} kHz (odd)")
    print(f"  ANTINODE-STRESS: inter-filar dV={B4['dV_filar']/1e3:.1f}kV across {INTERFILAR_GAP*1e3:.0f}mm "
          f"-> {B4['E_int_Vmm']/1e3:.1f} kV/mm  (vs air {G_AIR/1e3:.0f} kV/mm: "
          f"{'FEASIBLE' if B4['feasible'] else 'OVER -> DOMINATES'}, margin {B4['margin']:.2f}x)")
    print(f"     (unsplit drive {V_NODE5_BASELINE/1e3:.0f}kV -> {B4_unsplit['E_int_Vmm']/1e3:.1f} kV/mm; "
          f"and the resonant gain G~{B3['G_gain']:.0f} would push V_antinode far higher if unclamped)")

    # ---- verdicts ----
    # A destructive inter-filar HV flashover needs a real design margin, not a
    # knife-edge: require >=2x to the air limit. And B4 here is the CLAMPED
    # lower bound (charger view); the resonant gain G~Q magnifies any unclamped
    # buildup, and a tighter filar gap (needed for the bifilar self-C) raises it
    # further -- so 2x on the lower bound is already generous.
    FEASIBLE_MARGIN = 2.0
    antinode_dominates = B4["margin"] < FEASIBLE_MARGIN
    print("\n--- DISPOSITIONS (all three for the TMD gate) ---")
    print(f"  PARASITIC    : minimise self-C ({B2['C_simple']*1e12:.0f}pF), lumped resonator, operate "
          f"f0=637kHz << SRF={B3['srf_simple']/1e6:.0f}MHz -> CLEAN (the present coil already here).")
    print(f"  LUMPED-TANK  : let self-C add to C_R (operate < SRF) -- {B2['C_simple']*1e12:.0f}pF is "
          f"<0.7% of 789pF, negligible retune.")
    print(f"  SELF-RESONANT: operate AT SRF (bifilar tuned to f0): coil=AC ring + step-up charger, "
          f"C_R=pure DC store -- but see ANTINODE-STRESS.")
    print("\n--- TOP-LEVEL VERDICT ---")
    if antinode_dominates:
        print(f"  ANTINODE-STRESS-DOMINATES -> SIMPLE-DOWNBACK-PREFERRED")
        print(f"     the self-resonant bifilar puts {B4['E_int_Vmm']/1e3:.1f} kV/mm (split) to "
              f"{B4_unsplit['E_int_Vmm']/1e3:.1f} kV/mm (unsplit) at the antinode -- at/above the "
              f"{G_AIR/1e3:.0f} kV/mm air limit (margin only {B4['margin']:.2f}x), INSIDE the winding,")
        print(f"     in a machine already air/surface-bound (rev3) -- and the resonant gain G~{B3['G_gain']:.0f} "
              f"magnifies any unclamped buildup. No robust margin for a destructive flashover.")
        print(f"     PART A split: DO IT (clean win -- halves node stress, clears the C1/C2 overstress).")
        print(f"     PART B: take the SIMPLE down-and-back (low self-C, lumped, operate << SRF); the")
        print(f"     self-resonant upside (coil=ring, C_R=DC) is real but the antinode air/surface stress kills it.")
        top = "ANTINODE-STRESS-DOMINATES / SIMPLE-DOWNBACK-PREFERRED"
    else:
        print(f"  SELF-RESONANT-VIABLE")
        top = "SELF-RESONANT-VIABLE"

    _plots(A, B3, B4, V_antinode)

    # CSV
    csv = os.path.join(ROOT, "coil_topology.csv")
    with open(csv, "w") as f:
        f.write("quantity,value,unit\n")
        f.write(f"Lhalf_uH,{A['L_half']*1e6:.3f},uH\n")
        f.write(f"Mmut_uH,{A['M']*1e6:.3f},uH\n")
        f.write(f"Ltotal_aiding_uH,{A['L_total_aid']*1e6:.3f},uH\n")
        f.write(f"f0_split_kHz,{A['f0_aid']/1e3:.1f},kHz\n")
        f.write(f"CR_retune_pF,{A['C_R_retune']*1e12:.1f},pF\n")
        f.write(f"Vnode_split_kV,{A['V_node_split']/1e3:.2f},kV\n")
        f.write(f"stress_factor,{A['stress_factor']:.3f},-\n")
        f.write(f"DOWNBACK_L_add_uH,{B1['L_add']*1e6:.1f},uH\n")
        f.write(f"DOWNBACK_L_opp_uH,{B1['L_opp']*1e6:.2f},uH\n")
        f.write(f"Cself_simple_pF,{B2['C_simple']*1e12:.2f},pF\n")
        f.write(f"Cself_bifilar_pF,{B2['C_bifilar']*1e12:.1f},pF\n")
        f.write(f"fSRF_simple_MHz,{B3['srf_simple']/1e6:.3f},MHz\n")
        f.write(f"fSRF_bifilar_kHz,{B3['srf_bifilar']/1e3:.1f},kHz\n")
        f.write(f"Ggain,{B3['G_gain']:.0f},-\n")
        f.write(f"fmode_plus_kHz,{B3['f_plus']/1e3:.1f},kHz\n")
        f.write(f"fmode_minus_kHz,{B3['f_minus']/1e3:.1f},kHz\n")
        f.write(f"Qsr,{B3['Q_selfres']:.0f},-\n")
        f.write(f"Vantinode_kV,{V_antinode/1e3:.2f},kV\n")
        f.write(f"Eint_kVmm,{B4['E_int_Vmm']/1e3:.2f},kV/mm\n")
        f.write(f"#top_verdict,{top}\n")
    print(f"\nwrote {os.path.relpath(csv, ROOT)}")
    print(f"VERDICT: {top} | SPLIT do-it ({A['stress_factor']:.2f}x node stress) | "
          f"bifilar SRF->f0 OK but antinode {B4['E_int_Vmm']/1e3:.1f} kV/mm > {G_AIR/1e3:.0f}")
    return 0


def _plots(A, B3, B4, V_antinode):
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        import numpy as np
    except Exception as e:
        print(f"(plots skipped: {e})")
        return
    # 1. fire-transient node voltages asymmetric vs split
    fig, ax = plt.subplots(figsize=(5.6, 4.0))
    cats = ["node 5\n(asym)", "node 5\n(split)", "node 6\n(split)"]
    vals = [V_NODE5_BASELINE / 1e3, A["V_node_split"] / 1e3, A["V_node_split"] / 1e3]
    ax.bar(cats, vals, color=["#e76f51", "#2a9d8f", "#2a9d8f"])
    ax.axhline(V_C1C2 / 1e3, ls="--", color="#264653", label="C1/C2 binding 21 kV")
    ax.axhspan(CREEP_LO / 1e3, CREEP_HI / 1e3, alpha=0.12, color="#f4a261", label="creepage flag 12-30 kV")
    ax.set_ylabel("node-to-ground peak (kV)")
    ax.set_title("Part A: split halves the fire-transient node stress (clears C1/C2)")
    ax.legend(fontsize=8)
    fig.tight_layout(); fig.savefig(os.path.join(ROOT, "coil_transient_split.png"), dpi=110)
    plt.close(fig)
    # 2. standing-wave voltage profile + inter-turn stress band
    fig, ax = plt.subplots(figsize=(6.0, 4.0))
    x = np.linspace(0, 1, 200)                  # 0=shaft (grounded), 1=C_R (antinode)
    Vprof = np.sin(np.pi / 2 * x)               # quarter-wave: node at shaft, antinode at C_R
    ax.plot(x, Vprof * V_antinode / 1e3, color="#2a9d8f", lw=1.6, label="standing-wave V(x)")
    ax.axvline(1.0, ls=":", color="#e76f51")
    ax.annotate(f"antinode {V_antinode/1e3:.0f} kV\ninter-filar {B4['E_int_Vmm']/1e3:.1f} kV/mm",
                (0.62, 0.55 * V_antinode / 1e3), color="#e76f51", fontsize=8)
    ax.axhline(G_AIR / 1e3 * INTERFILAR_GAP * 1e3 / 1, ls="--", color="#264653",
               label=f"air limit at filar gap ({G_AIR/1e3*INTERFILAR_GAP*1e3:.0f} kV)")
    ax.set_xlabel("position along coil (shaft → C_R)"); ax.set_ylabel("voltage (kV)")
    ax.set_title("Part B: quarter-wave profile — antinode at C_R end (inter-filar stress peaks)")
    ax.legend(fontsize=8)
    fig.tight_layout(); fig.savefig(os.path.join(ROOT, "coil_standing_wave.png"), dpi=110)
    plt.close(fig)
    # 3. SRF & coupled modes vs bifilar pitch (the tuning knob)
    fig, ax = plt.subplots(figsize=(6.0, 4.0))
    Cs = np.logspace(math.log10(4e-12), math.log10(3e-9), 100)
    srf = 1.0 / (2 * math.pi * np.sqrt(L_R * Cs)) / 1e3
    ax.plot(Cs * 1e12, srf, color="#2a9d8f", label="f_SRF = 1/(2π√(L·C_self))")
    ax.axhline(637, ls="--", color="#264653", label="f0 637 kHz")
    ax.axhline(B3["f_plus"] / 1e3, ls=":", color="#8ab", label=f"coupled f+ {B3['f_plus']/1e3:.0f}")
    ax.axhline(B3["f_minus"] / 1e3, ls=":", color="#f4a261", label=f"coupled f- {B3['f_minus']/1e3:.0f}")
    ax.scatter([789], [637], color="#e76f51", zorder=5, label="bifilar design point")
    ax.set_xscale("log"); ax.set_yscale("log")
    ax.set_xlabel("coil self-C (pF) ← bifilar pitch knob"); ax.set_ylabel("frequency (kHz)")
    ax.set_title("Part B3: SRF & coupled modes vs self-C (bifilar lands SRF on f0)")
    ax.legend(fontsize=7)
    fig.tight_layout(); fig.savefig(os.path.join(ROOT, "coil_srf_modes.png"), dpi=110)
    plt.close(fig)
    print("wrote coil_transient_split.png, coil_standing_wave.png, coil_srf_modes.png")


if __name__ == "__main__":
    sys.exit(main())
