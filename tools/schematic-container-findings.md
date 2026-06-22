# Findings — SCHEMATIC-CONTAINER: host the KiCad schematic + legend + live values + the consistency check

**Branch** `html-synth` (r0.5 of the tool). **Verdict:** **`AWAITING-KICAD`** — the **expected interim
state, not a failure**: the container, the legend/live-value table, the label-match report, and the
netlist↔topology consistency check are all built and verified against the **interim** stand-in;
`tools/varcap.svg` / `tools/schematic.cir` are not yet committed by TMD. The moment TMD commits the two
KiCad exports the clean schematic appears in the slot and the stamp flips to MATCH — **with no further
code**. This brief **supersedes** the "Claude Code generates the schematic" path: the tool now only
**hosts + checks**; KiCad is the source of record.

No change to the physics, the search, the invariant logic, the guard, or the bus margin. Frozen
solvers byte-identical.

## §-checks

| # | check | result |
|---|---|---|
| 1 | frozen empty-diff; no physics/search/guard/bus change | ✓ frozen byte-identical; only the HTML container + `reference.md`/`README.md` changed |
| 2 | container opens on request, closed by default; slot scales-to-fit with **click-to-enlarge**; placeholder when `varcap.svg` absent | ✓ slot loads `varcap.svg` → interim `schematic.svg` (labelled) → placeholder; lightbox on click / "⤢ enlarge" |
| 3 | legend/value table renders; **value column live** from `evaluate_design`, tracks a design change; statics marked | ✓ C1/C2←`C1min`, Cx←`Cx_max`, Ca/Cb←`Ca`, C_R←`C_R`, C_max(derived)←`_C1max`; L_R **static** 39.5 µH; SG/BS commutation |
| 4 | **label-mismatch report** — every table `ref` vs the SVG labels | ✓ all 17 part labels present in the interim → **no mismatch**; derived `C_max` excepted (not a part) |
| 5 | **consistency check** on `schematic.cir` vs `topology_edge_list.csv` (component + node counts) | ✓ parser verified: a stand-in SPICE netlist gives **42 components, 22/22 nodes, MATCH** (K1 mutual-coupling handled); live state **AWAITING-KICAD** (no `schematic.cir` yet) |
| 6 | KiCad export commands documented in `README.md` | ✓ (+ in `reference.md`) |

## The flow (authoring is TMD's; the tool consumes)

```
TMD draws varcap.kicad_sch in KiCad (clean, symmetric — once)
  ├─ kicad-cli sch export svg     --output tools/            varcap.kicad_sch  → tools/varcap.svg
  └─ kicad-cli sch export netlist --format spice --output tools/schematic.cir  varcap.kicad_sch
       → commit to tools/
           → the container embeds tools/varcap.svg + the legend/value table
           → the check verifies tools/schematic.cir == the design topology of record
```

KiCad is **build-time** (TMD touches it only on a design change); the container is **runtime** and only
displays/checks the committed exports — **no auto-layout, no correction loop.**

## 1 — the container (in the reference drawer)

A schematic region inside the on-request drawer (closed by default), top to bottom:

1. **The schematic slot** — fetches `./varcap.svg` (the KiCad export, **drop-in**); if absent, falls
   back to the **interim** `./schematic.svg` *clearly labelled* "interim — KiCad export pending"; if
   that's absent too, a placeholder ("schematic pending KiCad export — run the two kicad-cli commands
   and commit `tools/varcap.svg`"). **Click-to-enlarge** (the slot or the "⤢ enlarge" button) opens the
   SVG at 92 vh in a lightbox, because the ND labels and values need zoom to read.
2. **The legend + live-value table** (below).
3. **The consistency stamp** — one line: MATCH / ⚠ MISMATCH / AWAITING-KICAD.

## 2 — the legend + live-value table (label-matched, not coordinate-overlaid)

One table, cross-referenced to the schematic **by the same labels KiCad uses** (robust to layout
edits). The **role** column is static (authored in `reference.md`); the **value** column is **live**
from the same `evaluate_design(...)` dict the calculator calls, refreshed when the design changes or
the drawer opens. **The schematic art does not change** (option 1 — clean fixed KiCad layout; the live
numbers live in the table). Fixed design constants (L_R, Cem coil, C_block) are marked **static**.

A **label-mismatch report** lists any table `ref` *not* found in the SVG text (so TMD can reconcile the
KiCad refdes to the table) — against the interim it is clean (all 17 labels present); the derived
`C_max` row is excepted (it is not a drawn part).

## 3 — the consistency check (the no-divergence guarantee)

Parses the KiCad SPICE netlist (`tools/schematic.cir`) and verifies it matches the design topology of
record (`topology_edge_list.csv`): **component count + node count**. This is what makes KiCad-as-source
safe — the drawn schematic is *proven* to be the design's electrical graph, not just a picture. The
parser was verified against a stand-in SPICE netlist generated from the topology: **42 components, 22/22
nodes → MATCH** (K-lines, e.g. `K1 L_R1 L_R2 0.3`, are counted as a component but contribute no nodes,
matching the topology where K1 has no net; ground `0` excluded). On mismatch the container shows ⚠ and
names the counts; with no `schematic.cir` committed the state is **AWAITING-KICAD** (the check reports
the design topology counts and waits). *(If a future `varcap.cir` ever co-exists with
`topology_edge_list.csv`, the same parser checks against both and flags any disagreement between them.)*

## 4 — bootstrap (testable before the KiCad SVG lands)

Until TMD commits `tools/varcap.svg`, the slot shows the interim/placeholder **and the legend/value
table + the consistency check still work** (they don't depend on the KiCad SVG). The existing
hand-emitted `tools/schematic.svg` is the **temporary visual stand-in**, clearly labelled. The KiCad
SVG is a **drop-in** (same path) — committing it is the only step to `CONTAINER-READY`.

## Deliverables

`tools/charge-pump-synth-live.html` (the schematic container: SVG slot + click-to-enlarge lightbox +
legend/live-value table + label-mismatch + consistency stamp, in the reference drawer; the netlist
check in-page) · `tools/reference.md` (legend roles + the KiCad export commands) · `tools/README.md`
(the export commands + the drop-in/stamp behaviour) · this findings doc. The interim `tools/schematic.svg`
+ `tools/cross-section.svg` + `tools/gen_artifacts.py` remain (the cross-section is still DXF-sourced;
the schematic SVG is now only the interim stand-in). Frozen empty-diff asserted. **Not merged.**

### To reach `CONTAINER-READY`

TMD runs the two `kicad-cli` commands and commits `tools/varcap.svg` + `tools/schematic.cir`. The
container then shows the clean KiCad schematic in the slot and the stamp flips to **MATCH** (assuming
the KiCad netlist equals the 42-component / 22-node design graph) — no code change.
