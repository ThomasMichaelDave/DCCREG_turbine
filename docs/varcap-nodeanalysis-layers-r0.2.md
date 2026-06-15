# Varcap node-analysis — layer scheme (r0.2)

Companion to the DXF template `varcap-nodeanalysis-template-r0.2.dxf`. The DXF is the authoritative
artifact (drafters draw parts onto the node/cap layers); this file is the human-readable index.

> **Provenance note.** The r0.1 markdown record was not present in this repo; this r0.2 index was
> regenerated **from the r0.1 DXF template** (supplied by TMD) plus the §9 additions, so the layer
> table below is read back from the actual DXF rather than transcribed. The DXF bump is reproducible
> via `varcap-nodeanalysis-template-bump.py` (pure-additive `ezdxf` edit; no existing layer or
> geometry touched).

## Revision history

| Rev | Date | Change |
|---|---|---|
| r0.1 | (TMD) | Base node-analysis template: construction guides, node electrodes (ND1–8), capacitance overlaps (CAP-*), spark gaps (SG*), mechanical envelope (MECH-*), R1-baseline reference radii. |
| r0.2 | 2026-06-15 | + two-tier 5–6 resonator clamp and static-sealed vacuum chamber per `design-intent-lock.md` §6–7/§9: `CLAMP-VOID-GLOW-5-6`, `CLAMP-CROWBAR-HARD-5-6`, `MECH-VACUUM-CHAMBER`, `MECH-VACUUM-NIPPLE`, and `CLAMP-SOFT-UPSTREAM` (defined OFF+FROZEN, pending the §6.3 [OPEN] decision). Legend + title bumped to r0.2. Pure-additive. |

## Node map (unchanged from r0.1)

- **Stator nodes 1–4** | **5 shaft A**, **6 shaft B** (the resonator differential) | **7 island (on B)**, **8 island (on A)**.
- C1: ND1 ↔ rotor · C2: ND4 ↔ rotor · Ca: ND1 ↔ ND2 · Cb: ND3 ↔ ND4 · Cx3: ND7 ↔ ND3 (pickup) · Cx4: ND8 ↔ ND2 (pickup).
- Units mm; assembly reference at 0,0; construction layers (`00-*`) are guides only. Reference radii
  are R1-baseline (calculator-derived); rotor-side node labels (ND5/ND6 faces) are best-guess from
  the model — confirm against drafting.

## Colour convention (ACI)

Colour groups parts by **function**, so the drawing reads in any CAD without a custom palette: node 1/4
rail = `1`, node 2 = `2`, node 3 = `3`, shafts 5/6 = `5`, islands + **all spark gaps** = `6`,
resonator/soft-clamp = `4` (cyan), mechanical envelope = `9`, mechanical hardware = `7`, strays/guides
= `8`, dielectric = `30`. The r0.2 clamp/vacuum layers **join these existing families** (see below).

## Layers

### Construction / reference (`00-*`, guides only)
| Layer | ACI |
|---|---|
| `00-DATUM-AXIS` | 4 |
| `00-REF-RADII` | 8 |
| `00-SECTOR-GRID-12` | 8 |
| `00-VIEW-FRAMES` | 9 |
| `00-LEGEND` | 7 |

### Node electrodes (`ND*`)
| Layer | ACI | | Layer | ACI |
|---|---|---|---|---|
| `ND1-C1-STATOR-PLATE` | 1 | | `ND4-C2-STATOR-PLATE` | 1 |
| `ND1-Ca-ELECTRODE` | 1 | | `ND4-Cb-ELECTRODE` | 1 |
| `ND2-Ca-ELECTRODE` | 2 | | `ND5-ROTOR-C1-FACE` / `ND5-SHAFT-A-BODY` | 5 |
| `ND2-Cx4-PICKUP-STATOR` | 2 | | `ND6-ROTOR-C2-FACE` / `ND6-SHAFT-B-BODY` | 5 |
| `ND3-Cb-ELECTRODE` | 3 | | `ND7-ISLAND-BARS-onB` | 6 |
| `ND3-Cx3-PICKUP-STATOR` | 3 | | `ND8-ISLAND-BARS-onA` | 6 |

### Capacitance overlaps (`CAP-*`) — the Cmin/Cmax extraction surfaces
| Layer | ACI |
|---|---|
| `CAP-C1-OVERLAP`, `CAP-C2-OVERLAP` | 1 |
| `CAP-Ca-GAP`, `CAP-Cx4-GAP` | 2 |
| `CAP-Cb-GAP`, `CAP-Cx3-GAP` | 3 |
| `CAP-Cpar-STRAY` | 8 |

### Spark gaps (`SG*`, all ACI 6)
`SG1-RETURN-GAP` · `SG2-RETURN-GAP` · `SG3a-LOAD-GAP` · `SG3b-FIRE-GAP` · `SG4a-LOAD-GAP` ·
`SG4b-FIRE-GAP` · `SG-BS3-BACKSTOP` · `SG-BS4-BACKSTOP`

### Mechanical (`MECH-*`)
| Layer | ACI |
|---|---|
| `MECH-BEARINGS-MOUNT`, `MECH-HUB-COUPLER` | 7 |
| `MECH-ENVELOPE` | 9 |
| `MECH-RESONATOR-TANK` | 4 |
| `MECH-DIELECTRIC` | 30 |

### Dimensions / misc
`DIM-ANGULAR` · `DIM-RADIAL` · `DIM-TEXT` (7) · `Defpoints` · `0`

### **r0.2 additions — clamp tiers + vacuum chamber** (`design-intent-lock.md` §6–7)
| Layer | ACI | Family tie | Notes |
|---|---|---|---|
| `CLAMP-VOID-GLOW-5-6` | 4 | resonator (cyan) | soft glow governor across ND5↔ND6; smooth, low-field-enhancement; normal-glow self-regulation. The inter-shaft void run in glow regime. |
| `CLAMP-CROWBAR-HARD-5-6` | 6 | spark-gap (magenta) | hard spark crowbar across ND5↔ND6; symmetric/bidirectional; last-resort ceiling (fires ~never). |
| `MECH-VACUUM-CHAMBER` | 9 | envelope | sealed inter-shaft chamber envelope; **static seal line** (shafts co-rotate locked ⇒ rigid-body chamber, no rotating seal). |
| `MECH-VACUUM-NIPPLE` | 7 | hardware | re-sealable evacuation/fill valve; sets pd into the glow band. |
| `CLAMP-SOFT-UPSTREAM` | 4 | resonator (cyan) | **OFF + FROZEN** — pending the §6.3 [OPEN] decision (upstream island/pickup soft governor vs in-void). Name frozen; do not draft onto it until confirmed. |
