# Findings — Topology recon r0.2: net-for-net vs r0_13

**Branch** `topology-recon-r0_13` (off `main`). **Verdict:** **`TOPOLOGY-INCOMPLETE` (gating precondition
unmet).** r0.2 was gated on the **r0_13 EE schematic being committed** so its drawn nets could be traced and
diffed net-for-net against deck v0.3. **r0_13 is not in the repo.** An exhaustive scan of *every* `.dxf` blob
across *all* git history finds only three files — r0_6, r0.1, r0.2 — and **all are radial-layout templates**
(no ND9/10, no motor, no schematic/wire layer, zero INSERTs). There are **no drawn nets to trace**, so the
net-for-net wiring diff the brief requires **cannot run**. This run does **not** fabricate a trace of a file
that isn't there.

**Escalation.** This is the **second brief** (the r0_15 recon, then this r0_13 one) gated on a schematic DXF
that **has never entered the repo**. The recurring blocker is the **schematic itself, not the deck** — the
graph keeps being "the topology we believe" because the drawing that would let us *show* it has not been
committed. A drawing punch-list (`dxf_flags.md`) is handed back so the next DXF rev can unblock the lock.

---

## §4 named checks

| # | check | result |
|---|---|---|
| 1 | r0_13 committed + parsed | **NOT committed** — exhaustive scan of all history finds no EE schematic |
| 2 | r0_13 netlist by net-tracing | **N/A** — no drawn nets exist to trace |
| 3 | mislabel / symmetry audit on r0_13 | unchanged from r0.1 (r0_6 symmetry exact; no r0_13 to re-check) |
| 4 | four `[?]` confirmed against drawn nets | **still freeze §5 + physics** — no drawing to confirm against |
| 5 | split resonator (9/10) verified as drawn | **absent from every DXF** |
| 6 | motor (11–22) verified as drawn | **absent from every DXF** |
| 7 | net-for-net diff vs deck v0.3 | **blocked** — no DXF netlist to diff |
| 8 | reconciled deck + verdict | r0.1 graph re-affirmed; **`TOPOLOGY-INCOMPLETE`** |

## Stage A — the gating precondition (exhaustive)

| committed DXF | layers | ND9/10 | motor | schematic | INSERTs | EE-schematic? |
|---|---|---|---|---|---|---|
| `…r0_6_TMD_layout.dxf` | 48 | — | — | — | 0 | **no** (radial) |
| `…r0.1.dxf` | 44 | — | — | — | 0 | **no** (radial) |
| `…r0.2.dxf` | 49 | — | — | — | 0 | **no** (radial) |

All three are **geometry templates** (node→component via layer names), not wired schematics. None carries the
split resonator (ND9/10), the motor (L_A/C_AR/L_B/C_BR/quadricores), a schematic/wire layer, or any polar
array. **The r0_13 the brief names — "ND1–10, the split resonator, the SG electrode bodies, and the motor
quadricores" — does not exist anywhere in the repo or its history.**

## Stages B–D — re-affirmed from r0.1 (the best available authority)

With no schematic to advance against, the r0.1 result **stands unchanged** and is the strongest claim
available:
- **The 42-component manifest is reconciled** from the freeze §5 node map + the Block-D Cem map + charge-pump
  physics; the **A/B symmetry is exact** (r0.1, on the r0_6 layers — no mislabel).
- **The four `[?]` are resolved** (freeze §5 + physics): **SG3a 1-7, SG4a 4-8** (load), **BS3 3-7, BS4 2-8**
  (backstop, blocking the *reverse* of the 7→3 / 8→2 fire). These remain **freeze-sourced, not yet
  drawn-net-confirmed** — exactly the gap r0.2 was meant to close.
- **The split resonator (ND9/10) and the 24 motor branches remain undrawn** in any DXF — a representation gap,
  not a deck error (no edge disagrees; parts are missing from the *drawing*).

So `topology_edge_list.csv` stays **source = freeze §5 + physics**, *not* DXF-sourced; it cannot be re-stamped
"net-for-net vs r0_13" because r0_13 is absent.

## Stage E — escalation + drawing punch-list

`dxf_flags.md` lists exactly what the EE-schematic DXF must contain to unblock `TOPOLOGY-CONFIRMED` and the
v0.11 freeze: **(1) drawn nets** (wires/terminals, not just layer-named bodies); **(2) the split resonator**
ND9/10 (L_R1 5-9 + C_R 9-10 + L_R2 10-6); **(3) the 24 motor components** (L_A/C_AR across Ca on 11–16,
L_B/C_BR across Cb on 17–22, the 12 quadricore irons + 440 nF caps); **(4) the four `[?]` as drawn nets** to
confirm the freeze-§5 + physics resolution against the actual drawing. The tracer **auto-detects** the
schematic (ND9/10 + motor) on the next run, so once r0_13 is committed, re-running `sim/topology_recon.py`
proceeds straight to the net-trace.

## Verdict + roadmap

**`TOPOLOGY-INCOMPLETE` (gating precondition unmet).** The graph cannot be marked DXF-sourced and v0.11 cannot
freeze against r0_13 until the schematic is actually committed. The deck's connectivity is trustworthy *where
checkable* (the 18 core/comm/resonator components + the resolved shuttle path), so the **shuttle/Cem model
upgrade may still proceed on that locked sub-graph**, treating the motor branch as deck-only — but the
*net-for-net confirmation* of the full graph, and the v0.11 freeze against the drawing, **wait on committing
the EE-schematic DXF**. This is the gate between "the topology we believe" and "the topology we can show"; it
stays closed until the drawing arrives. **Action:** commit r0_13 per `dxf_flags.md`, then re-run this exact
tracer.

## Deliverables

`sim/topology_recon.py` r0.2 (exhaustive cross-history DXF inventory + the gate that auto-detects a real
schematic + the re-affirmed manifest; refuses to trace a non-existent file) · this findings doc ·
`dxf_flags.md` (the drawing punch-list) · `topology_edge_list.csv` (re-affirmed, source still freeze §5 +
physics, *not* DXF). DXF + frozen read-only; empty-diff asserted. **Not merged.**
