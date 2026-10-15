# The rebuild's KiCad schematics and netlists: findings

**Source:** `rebuild/kicad/make_kicad.py` → `kicad_check_results.json`, the exported netlists `s0_base/s0_base.net` and
`s1_tube/s1_tube.net`, and the ERC reports `s*/s*-erc.rpt`. KiCad 10.0.6.

**The designer's requests (2026-10-15):**
- "We will first install kicad on my machine so we can deliver the proper netlist."
- "When you generate the schematic, provide the proper text in the schematic to explain all components."
- "Open the GUI and let me reorganize so it becomes readable by a human too."
- After the review: "Both are ok, no need to add actual diagonals, that would be pure aesthetic."

## Headline

**Both sheets deliver a netlist that matches its source node for node, with a clean ERC (0 errors, 0 warnings).**

| sheet | contents | netlist against | ERC |
|:--|:--|:--|:--|
| `s0_base/s0_base.kicad_sch` | de Queiroz Fig. 1 at the paper's values: C1, C2 (varicaps), Ca, Cb, D1–D4; nets REF, N1–N4 | `rebuild/s0_base/s0_base.py` TOPOLOGY: match; the deck `s0_base.cir`: match | 0 / 0 |
| `s1_tube/s1_tube.kicad_sch` | the S0 core at the tube's air values, plus C_k (N1–N4, the core's electrode pair) and Cr1 / Cr4 (each electrode's stray to REF) | S0's TOPOLOGY plus the three additions: match; the solver circuit of `rebuild/s1_tube/s1_pulsed_core.py`: match | 0 / 0 |

- **Every component is explained on its sheet:**
  - a legend gives what it is physically, its role, and its rating or stress, with the study cited;
  - the same text is in the part's Description field;
  - a notes block gives the source, the decisions in force and what is deliberately not drawn (the voltage limit,
    OPEN; the seed, only if the machine does not start; the buffer and multiplier options, not chosen).
- **C_k, Cr1 and Cr4 are field quantities, not bought parts.** They are in the netlist, but marked not in the BOM.
  Their values come from S2.
- **The layout:** the designer reviewed the generated layout in the GUI and accepted it. The saved sheets are the
  drawings of record. The script regenerates a sheet only with `--force`. Without `--force` it re-checks whatever is
  saved: `python3 rebuild/kicad/make_kicad.py --check-only`.
