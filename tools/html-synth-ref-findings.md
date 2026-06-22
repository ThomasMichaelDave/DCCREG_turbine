# Findings — HTML-SYNTH-REF: reference layer, slack normalization, SVG fix, run guide

**Branch** `html-synth` (r0.2 of the tool). **Verdict:** **`REF-LAYER-COMPLETE`** — the rotor SVG is
de-compressed (A); slack is one uniform, documented convention with the anchor still **I10-bound** (B);
the on-request reference drawer maps every value to **both** SSOT-generated artifacts (C) with a
verified glossary (D); the `tools/README.md` run guide ships (E). The two artifacts are **rendered, not
deferred** — `schemdraw`/`lcapy` are absent in-env, so the schematic was **hand-drafted directly from
the netlist** (connectivity-checked) rather than shipped as a placeholder. No physics, search, invariant
*logic*, guard, or bus-margin changed — only the slack *normalization*, the SVG layout, and new docs.

## §-checks

| # | check | result |
|---|---|---|
| 1 | frozen empty-diff; `design_synth.py` change limited to the slack normalization (B) | ✓ frozen byte-identical; only the I3 slack formula + detail strings + a convention docstring changed |
| 2 | **SVG** — anchor + `max_eta` render with clear gutters; nothing clips (coordinate proof) | ✓ (table below) — **scale-invariant**: dia-label 31 px clear, active-label 39 px clear, at *every* rotor size |
| 3 | **slack** uniform on all 10; anchor binding still **I10 ≈ 0.048**; apples-to-apples ranking shown | ✓ (ranking below) |
| 4 | **cross-section** from the DXF (4 ref-radii + features); **schematic** from the netlist, connectivity-checked | ✓ cross-section ← R25/95/387/491/500 + features; schematic ← **42 components, 22/22 nodes, MATCH** |
| 5 | **reference panel** on demand, closed by default; value table cross-references both; single-source | ✓ `tools/reference.md` rendered into the drawer; both SVGs embedded |
| 6 | **glossary** mappings verified against the netlist + DXF (corrections reported) | ✓ all 9 free-var mappings verified; **no corrections needed** |
| 7 | `tools/README.md` present and correct | ✓ serve-from-root, badge-as-acceptance-test, troubleshooting |

## A — the rotor SVG, de-compressed

`viewBox 0 0 320 372`, centre **(160, 188)**, max ring **R_MAX = 132**; the dia label sits in the **top
gutter (y 30)**, the active-band label in the **bottom gutter (y 356)**. Because the scale normalizes to
the plate edge, the geometry is **r_out-independent** — the clearances hold at every synthesizable rotor:

| design | plate ring | rotor top / bottom | dia-label clearance | active-label clearance |
|---|---|---|---|---|
| anchor (~983 mm) | 129.4 px | 60.8 / 317.4 | **31 px** (≥24) | **39 px** (≥24) |
| max_eta (~889 mm) | 129.4 px | 60.8 / 317.4 | 31 px | 39 px |
| max / min r_out | 129.4 px | 60.8 / 317.4 | 31 px | 39 px |

Rotor top ≥ y56, bottom ≤ y320, nothing clips the viewBox — at every design.

## B — slack: one normalization, documented

**Convention (now in the `invariants()` docstring):** slack = signed fractional **headroom to the
bound, normalized by the bound** (`0` = wall/binding, `<0` = violated, `0.10` = 10 % headroom). The
**only formula that changed** is **I3** (two-sided z band): from band-width normalization (capped at
0.5) to the **nearer-edge** normalization — apples-to-apples with the one-sided limits. Each `detail`
now carries the value/bound + the slack (e.g. `rim 154/200 m/s (limit); slack 0.228`). The anchor
ranking is now a clean fraction-of-headroom:

```
I10 0.048  < I3 0.080  < I9 0.228  < I7 0.400  < I2/I8/I1 1.0  < I5 1.58  < I4 1.64  < I6 13.0
```

**Binding still I10 ≈ 0.048** (the shuttle strike-vs-ceiling margin), as required. I3 now correctly
reads **0.080** (z 1.334 is ~8 % from its nearer band edge 1.45) instead of the misleading 0.466 it
showed under band-width normalization. **I6 reads large (~13) and that is correct** — the modulation
headroom is genuinely big; I6's teeth are indirect (as C_max→C_par the z collapses, caught by I3) — now
documented so it isn't read as a bug.

## C + D — the reference panel + the artifacts

A drawer (the **"ⓘ reference"** button, closed by default) renders `tools/reference.md` — the **single
source** — with the value table cross-referencing both SSOT artifacts:

- **`cross-section.svg`** ← the DXF (`ezdxf`): the ref-radii **R25/R95/R387/R491/R500** (assert-checked
  against the drawn circles) + the named features (varicap plate wedges ND1/ND9, island bars ND7/ND8,
  the C_R septum, the 12 Cem cores).
- **`schematic.svg`** ← `topology_edge_list.csv` (the DXF-sourced netlist of record; `varcap.cir` is not
  on this branch). **Connectivity check: 42 components, 22/22 nodes, MATCH** (every endpoint in the node
  set; K1 the coupling element correctly flagged as no-net). TMD remains the design authority on the
  final schematic aesthetic; this draft **derives from the netlist** so the two cannot silently diverge.

**Glossary (D) verified** against the netlist + DXF — all nine free-var mappings check out with **no
corrections**: `r_out`→R387, `g_v`→ND1↔ND9 gap, `C_min`→C1/C2 nodes, `Ca`→Ca 1‑2/Cb 3‑4, `C_par`→(not
drawn), `C_x,max`→Cx3 7‑3/Cx4 8‑2 (ND7/ND8 bars), `C_R`→nodes 9‑10 (12 mm septum), `rpm`→PRF/rim.

## E — the run guide

`tools/README.md`: **serve from the repo root** (not `file://`; the page fetches `../reference/*.py`),
first load needs the Pyodide/numpy CDN, **the badge is the acceptance test** (`SOLVER: live` /
`CANARY-FAIL` / `down`), and troubleshooting (served-from-inside-tools → 404, offline → stuck booting,
port busy).

## Deliverables

`tools/charge-pump-synth-live.html` (SVG fix + the reference drawer) · `sim/design_synth.py` (slack
normalization only; frozen empty-diff) · `tools/reference.md` (canonical reference + glossary) ·
`tools/cross-section.svg` (from the DXF) · `tools/schematic.svg` (from the netlist, connectivity-checked)
· `tools/gen_artifacts.py` (the SSOT generators + the check) · `tools/README.md` · this findings doc.
Frozen empty-diff asserted. **Not merged.**

> **Note on the schematic SSOT.** The brief proposed `varcap.cir` + `schemdraw`/`lcapy`; neither is on
> this branch / in-env. The schematic is drafted from **`topology_edge_list.csv`** (the netlist of
> record) and rendered by hand-emitted SVG (no renderer dep), connectivity-checked against the same CSV
> — so it is **netlist-faithful and not a placeholder** (`REF-LAYER-COMPLETE`, not `ARTIFACT-DEFERRED`).
> If `varcap.cir` lands on a future branch, point `gen_artifacts.py` at it (the check logic is identical).
