"""sim/diode_stack_compare.py -- spark gaps vs a diode stack on the tube's capacitances (exact engine, 20 kV, 300 rpm).

Cases:
- the record schematic with its spark gaps (rail / backstop valves, load / fire ring-down);
- the record schematic with every gap an ideal diode;
- the bare de Queiroz 4-diode doubler core (pump_engine.core_net = solveDoubler4 topology), with its two-state
  stepped capacitances AND with smooth cosine capacitances (diodes always armed).
Scaled so the highest node peaks at 20 kV (the breakdown-limited node); also shown with nodes 1 / 4 at 20 kV.

Usage: python3 sim/diode_stack_compare.py   (writes sim/diode_stack_compare_results.json)
"""
import json
import os
import sys, math, numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import stack_sizing as S, pump_synth as SY, pump_engine as PE, rt_engine as RT
lad=S.size_stack('tube'); fi=dict(SY.FIRING_DEFAULTS) if hasattr(SY,'FIRING_DEFAULTS') else SY.split({})[2]
OUT = []


def show(tag,net,cfg):
    m=RT.run(net,cfg,record=True); rec=m['rec']; V=np.array([p['V'] for p in rec['points']])
    pk={n:np.abs(V[:,i]).max() for n,i in net.idx.items()}; top=max(pk.values())
    s2=(20e3/top)**2; W=rec['ledger']['W']*s2; dE=(rec['E1']-rec['E0'])*s2; d=sum(rec['by'].values())*s2
    # also scale so that the main nodes 1/4 peak at 20 kV
    m14=max(pk['1'],pk['4']); r=(top/m14)**2
    print(f"{tag}: z {m['z']:.4f}; node peaks (rel. to max) "+", ".join(f"{n} {v/top:.2f}" for n,v in sorted(pk.items(),key=lambda x:-x[1])[:6]))
    OUT.append(dict(case=tag, z=m['z'], converged=bool(m['converged']), node_peak_rel={n: v / top for n, v in pk.items()},
                    P_belt_W=W * 30, P_surplus_W=dE * 30, eta=dE / W, P_surplus_nodes14_20kV_W=dE * 30 * r))
    print(f"   capped at the max node 20 kV: belt {W*30:.2f} W surplus {dE*30:.2f} W eta {dE/W:.3f} | if nodes 1/4 at 20 kV: belt {W*30*r:.2f} W surplus {dE*30*r:.2f} W")
allv=dict(gm_rail='valve',gm_load='valve',gm_fire='valve',gm_backstop='valve')
for tag,over in (('record, spark gaps',{}),('record, all diodes',allv)):
    cfg=SY.engine_cfg(lad,fi,over=over); show(tag,PE.build_net(cfg),cfg)
# de Queiroz core with SMOOTH (cosine) caps instead of the two-state steps
cfg=SY.engine_cfg(lad,fi,over=dict(topology='core'))
for smooth in (False,True):
    net=PE.core_net(cfg)
    if smooth:
        c1lo,c1hi,c2lo,c2hi=(cfg[k]*1e-12 for k in ('C1min','C1max','C2min','C2max'))
        f1=lambda th: c1lo+(c1hi-c1lo)*0.5*(1+math.cos(2*math.pi*(th-15.0)/60.0))
        f2=lambda th: c2lo+(c2hi-c2lo)*0.5*(1-math.cos(2*math.pi*(th-15.0)/60.0))
        net.caps=[(nm,i,j,(f1 if nm=='C1' else f2 if nm=='C2' else C)) for nm,i,j,C in net.caps]
        net.gaps=[(g[0],g[1],g[2],g[3],(0.0,60.0),g[5],g[6]) for g in net.gaps]
    show('de Queiroz core, '+('smooth cosine caps, diodes always armed' if smooth else 'stepped caps (solveDoubler4)'),net,cfg)
json.dump(OUT, open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "diode_stack_compare_results.json"), "w"),
          indent=1, default=float)
