"""sim/stack_sizing_reference.py -- regenerate sim/stack_sizing_results.json: the default tube at 6 / 8 / 12 / 16 vanes, both
stray modes, under the record, v4 and bare de Queiroz diode-core topologies, at 300 rpm, with the 20 kV power ledger."""
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import stack_sizing as S          # noqa: E402

rows = []
for strays in ("fixed", "scaled"):
    for top in ("record", "v4", "core"):
        for n in (6, 8, 12, 16):
            r = S.evaluate("tube", plates=dict(n_plates=n), choices=dict(rpm=300.0, cpar_mode=strays), topology=top)
            lad, res = r["ladder"], r["result"]
            L = res["ledger"]
            rows.append(dict(strays=strays, topology=top, n_plates=n, C_max=lad["ladder"]["C_max"]["value"],
                             C_min=lad["ladder"]["C_min"]["value"], kappa=lad["kappa_C"], z=res["z"], conv=res["converged"],
                             L_total_mm=lad["tube_geometry"]["L_total_mm"], P_belt_W=L["P_belt_W"], P_surplus_W=L["P_surplus_W"],
                             eta=L["eta"], top_node=L["top_node"]))
            print(rows[-1], flush=True)
p = S.TUBE_DEFAULTS
json.dump(dict(defaults=f"r {p['r_inMm']:g}-{p['r_outMm']:g}, {p['g_vMm']:g} mm {p['dielectric']} (breakdown {S.gap_breakdown_kV(p['g_vMm'], p['dielectric']):.1f} kV), "
                        f"{p['t_vaneMm']:g} mm vanes, {p['ws_deg']:g}/{p['wr_deg']:g} deg, 300 rpm, ledger at {S.V_OP / 1e3:g} kV",
               rows=rows), open(os.path.join(HERE, "stack_sizing_results.json"), "w"), indent=1, default=float)
