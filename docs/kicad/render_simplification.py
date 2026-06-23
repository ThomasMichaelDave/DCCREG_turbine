import re, math
import matplotlib; matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch
SCH="docs/kicad/DCCREG_Turbine_circuit.kicad_sch"
t=open(SCH).read()
def bal(s,st):
    d=0
    for x in range(st,len(s)):
        if s[x]=='(':d+=1
        elif s[x]==')':
            d-=1
            if d==0:return s[st:x+1]
    return s[st:]
# lib pin offsets
libpins={}
lib=bal(t,t.find('(lib_symbols'))
for m in re.finditer(r'\(symbol "([^"]+)"',lib):
    name=m.group(1)
    if ':' not in name: continue
    b=bal(lib,m.start())
    pins=re.findall(r'\(pin\s+\w+\s+\w+\s*\(at ([-\d.]+) ([-\d.]+) ([-\d.]+)\)\s*\(length ([-\d.]+)\)',b,re.S)
    libpins[name]=[(float(x),float(y)) for (x,y,a,L) in pins]
# instances
insts=[]
for m in re.finditer(r'\(symbol\s*\(lib_id "([^"]+)"',t):
    b=bal(t,m.start()); libid=m.group(1)
    at=re.search(r'\(at ([-\d.]+) ([-\d.]+) ([-\d.]+)\)',b)
    ref=re.search(r'\(property "Reference" "([^"]+)"',b)
    mir=re.search(r'\(mirror (\w+)\)',b)
    if not ref or libid not in libpins: continue
    insts.append(dict(ref=ref.group(1),lib=libid,ox=float(at.group(1)),oy=float(at.group(2)),
                      ang=float(at.group(3)),mir=mir.group(1) if mir else None))
# wires
wires=[]
for m in re.finditer(r'\(wire\s*\(pts',t):
    b=bal(t,m.start()); pts=re.findall(r'\(xy ([-\d.]+) ([-\d.]+)\)',b)
    if len(pts)>=2: wires.append(((float(pts[0][0]),float(pts[0][1])),(float(pts[1][0]),float(pts[1][1]))))
def pinabs(inst,lx,ly):
    x0,y0=lx,ly
    if inst['mir']=='y':x0=-x0
    if inst['mir']=='x':y0=-y0
    a=math.radians(inst['ang'])
    return (inst['ox']+x0*math.cos(a)-y0*math.sin(a), inst['oy']+x0*math.sin(a)+y0*math.cos(a))

REMOVE={f"L_A{i}" for i in range(1,7)}|{f"L_B{i}" for i in range(1,7)}   # the 12 brigade inductors
ISLAND={"Lx3","Lx4","Cx3","Cx4"}                                         # the real recovery (KEEP)
GAPS={"SG1","SG2","SG3a1","SG3b1","SG4a1","SG4b1","BS3","BS4"}
def kind(ref,lib):
    if ref in REMOVE: return 'remove'
    if ref in ISLAND: return 'island'
    if ref in GAPS: return 'gap'
    if 'C_Variable' in lib: return 'varicap'
    if 'Device:C' in lib: return 'cap'
    if 'Device:L' in lib: return 'ind'
    return 'other'
COL={'remove':'#e5484d','island':'#2a9d8f','gap':'#b8975a','varicap':'#7cd0ff','cap':'#5a7a96','ind':'#8a9aa8','other':'#888'}

# KiCad Y is downward -> flip for display
ys=[p[1] for w in wires for p in w]+[i['oy'] for i in insts]
ymax=max(ys)
fig,ax=plt.subplots(figsize=(15,10))
for (a,b) in wires:
    ax.plot([a[0],b[0]],[ymax-a[1],ymax-b[1]],color='#cdd6df',lw=0.7,zorder=1)
for inst in insts:
    k=kind(inst['ref'],inst['lib']); c=COL[k]
    x,y=inst['ox'],ymax-inst['oy']
    # draw the symbol body box
    rm = k=='remove'
    ax.add_patch(FancyBboxPatch((x-3.0,y-3.0),6,6,boxstyle="round,pad=0.3",
                 fc=c if not rm else '#fde2e2', ec=c, lw=2.2 if rm else 1.0, zorder=3,
                 alpha=0.95))
    ax.text(x,y,inst['ref'],ha='center',va='center',fontsize=6.5 if len(inst['ref'])<5 else 5.5,
            color='#101010' if not rm else '#a01020', zorder=4, weight='bold' if rm else 'normal')
    if rm:  # big red X over removed parts
        ax.plot([x-3.4,x+3.4],[y-3.4,y+3.4],color='#e5484d',lw=2.4,zorder=5)
        ax.plot([x-3.4,x+3.4],[y+3.4,y-3.4],color='#e5484d',lw=2.4,zorder=5)
ax.set_aspect('equal'); ax.axis('off')
# legend
from matplotlib.patches import Patch
import matplotlib.lines as mlines
leg=[Patch(fc='#fde2e2',ec='#e5484d',lw=2,label='REMOVE — brigade inductors L_A1-6 / L_B1-6 (×12)'),
     Patch(fc=COL['island'],label='KEEP — island recovery (Cx3/4, Lx3/4) — the real η lift'),
     Patch(fc=COL['varicap'],label='rotor varicaps (C1/C2)'),
     Patch(fc=COL['cap'],label='caps: Ca/Cb coupling, C_AR/C_BR banks, C_R tank'),
     Patch(fc=COL['ind'],label='resonator L_R1/L_R2'),
     Patch(fc=COL['gap'],label='commutation gaps (SG*/BS*)')]
ax.legend(handles=leg,loc='upper left',fontsize=9,framealpha=0.95)
ax.set_title("DCCREG schematic — the Ca/Cb simplification: remove the 12 brigade inductors (red ✕),\n"
             "revert the rotor→bank coupling to direct Ca/Cb; KEEP the island Cx/Lx (the validated recovery). 43 → 31 components.",
             fontsize=12)
fig.tight_layout(); fig.savefig('docs/kicad/schematic_simplification.png',dpi=120,bbox_inches='tight')
print("wrote docs/kicad/schematic_simplification.png")
print(f"REMOVE ({len(REMOVE)}): {', '.join(sorted(REMOVE))}")
print(f"total symbols: {len(insts)}; after removal: {len(insts)-len([i for i in insts if i['ref'] in REMOVE])}")
# (re-render tightened to the component bounding box)
xs=[i['ox'] for i in insts]; ysd=[ymax-i['oy'] for i in insts]
ax.set_xlim(min(xs)-12,max(xs)+12); ax.set_ylim(min(ysd)-12,max(ysd)+8)
ax.legend(handles=leg,loc='lower left',fontsize=10,framealpha=0.97)
fig.savefig('docs/kicad/schematic_simplification.png',dpi=130,bbox_inches='tight')
print("re-rendered tight")
