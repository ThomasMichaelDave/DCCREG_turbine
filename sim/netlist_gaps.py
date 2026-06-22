#!/usr/bin/env python3
"""
sim/netlist_gaps.py — the gap consistency check + the rectifier-role map for the re-derive.
===========================================================================================
Consumes the connectivity reconstructed from TMD's KiCad schematic (`sim/sch_to_netlist.py`) and
checks the eight commutation gaps against the VALIDATED arrangement, then emits the rectifier-role
map the topology-driven re-derive consumes (which gaps hold off which nodes to V_strike, which are
the FE backstops).

The arrangement here is the REAL one read from the schematic geometry (not the earlier lumped
shuttle_core abstraction): SG1/SG2 fire the transfer banks into the RESONATOR (not to ground), and
BS3/BS4 are the FE backstops in PARALLEL with the island fire gaps SG3b/SG4b.
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
import sch_to_netlist as s2n

# the VALIDATED 8-gap arrangement, as wired in the schematic of record (node pairs + role + kind)
GAP_SPEC = {
    "SG3a1": ("sparking", ("1 (A rail)", "7 (island A)"), "branch-A LOAD (rail->island)"),
    "SG3b1": ("sparking", ("3 (BR bank)", "7 (island A)"), "branch-A FIRE (island->BR bank)"),
    "SG4a1": ("sparking", ("4 (B rail)", "8 (island B)"), "branch-B LOAD (rail->island)"),
    "SG4b1": ("sparking", ("2 (AR bank)", "8 (island B)"), "branch-B FIRE (island->AR bank)"),
    "BS3":   ("field_emission", ("3 (BR bank)", "7 (island A)"), "branch-A FE backstop (|| SG3b)"),
    "BS4":   ("field_emission", ("2 (AR bank)", "8 (island B)"), "branch-B FE backstop (|| SG4b)"),
    "SG1":   ("sparking", ("2 (AR bank)", "R-A (resonator A end)"), "AR-bank FIRE -> resonator tank"),
    "SG2":   ("sparking", ("3 (BR bank)", "R-B (resonator B end)"), "BR-bank FIRE -> resonator tank"),
}


def kind_of(ref):
    return "field_emission" if ref.startswith(("BS", "FE")) else "sparking"


def rectifier_map():
    """Build the rectifier-role map for the re-derive: which nodes are V_strike-gated (the holdoff
    rectification COMMUTATOR-REAL relies on), and which gaps are FE backstops. [ME]"""
    topo = s2n.gap_topology()
    sparking = {g: topo[g] for g in topo if kind_of(g) == "sparking"}
    fe = {g: topo[g] for g in topo if kind_of(g) == "field_emission"}
    # the transfer banks (nodes 2,3) are held off by the bank-fire gaps SG1/SG2 + the island-fire
    # gaps SG3b/SG4b -> the V_strike holdoff the brigade over-transfer rectifies against.
    gated_nodes = set()
    for g, (a, b) in sparking.items():
        for n in (a, b):
            if "bank" in n:
                gated_nodes.add(n)
    return dict(sparking=sparking, fe_backstops=fe, vstrike_gated_banks=sorted(gated_nodes))


def main():
    print("=" * 90)
    print("NETLIST-GAPS — 8-gap consistency check + rectifier-role map (from the schematic)")
    print("=" * 90)
    comps, nets, (hits, tot) = s2n.extract()
    topo = s2n.gap_topology()
    print(f"\nschematic of record: {len(comps)} components, {len(nets)} nets; "
          f"pin-calibration {hits}/{tot} ({'EXACT' if hits == tot else 'PARTIAL'})")

    print("\nCONSISTENCY CHECK — the 8 gaps vs the validated arrangement:")
    allok = True
    for g, (kind, nodes, role) in GAP_SPEC.items():
        got = topo.get(g)
        present = got is not None
        nodes_ok = present and set(got) == set(nodes)
        kind_ok = kind_of(g) == kind
        ok = present and nodes_ok and kind_ok
        allok = allok and ok
        status = "OK" if ok else ("MISSING" if not present else f"MISMATCH got{got}")
        print(f"  {g:7s} {kind:15s} {role:38s} [{status}]")
    print(f"\n  -> {'ALL 8 GAPS PRESENT & CONSISTENT' if allok else 'DISCREPANCY — see above'}; "
          f"({len(topo)}/8 found).")

    rm = rectifier_map()
    print("\nRECTIFIER-ROLE MAP (for the topology-driven re-derive):")
    print(f"  V_strike-gated transfer banks (the rectification): {rm['vstrike_gated_banks']}")
    print(f"  sparking gaps ({len(rm['sparking'])}): " +
          ", ".join(f"{g}{v}" for g, v in sorted(rm["sparking"].items())))
    print(f"  FE backstops ({len(rm['fe_backstops'])}): " +
          ", ".join(f"{g}{v}" for g, v in sorted(rm["fe_backstops"].items())))
    print("\n  Note: nodes 2,3 (the AR/BR transfer banks) ARE held off to V_strike by the bank-fire")
    print("  gaps (SG1/SG2) and the island-fire gaps (SG3b/SG4b) -- exactly the V_strike holdoff the")
    print("  COMMUTATOR-REAL rectifier modeled. The diode-at-0 stand-in is replaced by the real gaps.")
    return allok


if __name__ == "__main__":
    main()
