# The rebuild's KiCad schematics and netlists: findings

**Source:** `rebuild/kicad/make_kicad.py` → `kicad_check_results.json`. The project is `dccreg_rebuild/`; it holds the
project netlist `dccreg_rebuild.net`, each stage's nets in `netlists/<stage>.txt`, and the ERC report
`dccreg_rebuild-erc.rpt`. KiCad 10.0.6.

**The designer's requests (2026-10-15):**
- "We will first install kicad on my machine so we can deliver the proper netlist."
- "When you generate the schematic, provide the proper text in the schematic to explain all components."
- "Open the GUI and let me reorganize so it becomes readable by a human too."
- After the review: "Both are ok, no need to add actual diagonals, that would be pure aesthetic."
- 2026-10-16: "please set everything up so the development stays in one project with all stages and changes in
  separate sheets".

## Headline

**One project, one sheet per stage. Each stage's nets match its source node for node, and the project's ERC is clean
(0 errors, 0 warnings).**

| sheet (in `dccreg_rebuild/`) | contents | parts | its nets against |
|:--|:--|:--|:--|
| `dccreg_rebuild.kicad_sch` (root) | a box per stage, and the index: the stages, the naming, the check | — | — |
| `s0_base.kicad_sch` (sheet 2) | de Queiroz Fig. 1 at the paper's values; nets REF, N1–N4 | C101, C102 (varicaps), Ca101, Cb101, D101–D104 | `rebuild/s0_base/s0_base.py` TOPOLOGY: match; the deck `s0_base.cir`: match |
| `s1_tube.kicad_sch` (sheet 3) | the S0 core at the tube's air values, plus the core's electrode pair across N1–N4 and each electrode's stray to REF | C201, C202, Ca201, Cb201, D201–D204, Ck201, Cr201, Cr204 | S0's TOPOLOGY plus the three additions: match; the solver circuit of `rebuild/s1_tube/s1_pulsed_core.py`: match |

- **The naming:** each stage numbers its parts in its own hundred, as KiCad does for multi-sheet projects. The
  letters stay: C1 is C101 in S0 and C201 in S1. Each legend gives a part's name in its source in brackets, so the
  check maps back to TOPOLOGY.
- **The nets are local labels,** so the stages never connect: the project netlist reads /S0 base/N1, /S1 tube/N1 and
  so on.
- **A new stage or change** is a new entry in the script's STAGES list, with its own sheet and its own hundred. The
  root's index is redrawn when a stage is added.
- **The two separate projects of 2026-10-15** (`s0_base/`, `s1_tube/` as their own projects, commit `05ea57f`) are
  replaced by this one. Their layout carries over unchanged; only the part names gain their stage number.

- **Every component is explained on its sheet:**
  - a legend gives what it is physically, its role, and its rating or stress, with the study cited;
  - the same text is in the part's Description field;
  - a notes block gives the source, the decisions in force and what is deliberately not drawn (the voltage limit,
    OPEN; the seed, only if the machine does not start; the buffer and multiplier options, not chosen).
- **C_k, Cr1 and Cr4 (Ck201, Cr201, Cr204) are field quantities, not bought parts.** They are in the netlist, but marked not in the BOM.
  Their values come from S2.
- **The layout:** the designer reviewed the generated layout in the GUI and accepted it. The saved sheets are the
  drawings of record. The script regenerates a sheet only with `--force`. Without `--force` it re-checks whatever is
  saved: `python3 rebuild/kicad/make_kicad.py --check-only`.
