# Brief — Drafting infrastructure, Phase 1: first rule, first enforced check, independent checker

| Rev | Date | Author | Change |
|---|---|---|---|
| 0.1 | 2026-10-16 | chat (scrutiny layer) | First issue, for designer review |

## Entry condition

Phase 0 merged by the designer, all its named checks PASS. Same branch scheme: `claude/drafting-infra-p1` cut from
`claude/synthesis-phase1`, PR back, the designer merges.

## Purpose

Carry one real correction all the way up the ladder, so the mechanism is proven end to end before it is scaled, and
stand up an independent drawing checker that can itself be shown to be wrong. The worked example is the general
tolerance note: the drawing set prints "ISO 2768-mK", but ISO 2768-2 (the geometrical "K" class) was withdrawn and
replaced by ISO 22081:2021; ISO 2768-1 ("m") remains valid. [OC]

## Out of scope

The frozen set, `rebuild/s0_base/`, building PDFs, the `mech-drafting` skill body (Phase 2), anything electrical
(Phase 3). Fixes to existing sheets: this phase reports failures, it does not repair them.

## Steps (reasoning and approach; implementation is yours)

1. **Scoped rule file.** Create `.claude/rules/drafting.md` holding only rung-1 items, each one or two lines with its
   correction-log id. Scope its `paths:` to the generator scripts (`docs/make_drawing_set.py`,
   `docs/make_core_drawing.py`, `sim/tube_geometry.py` and the other drawing writers) as well as the drawing outputs,
   because sheets are produced by running a script through the shell and a rule scoped only to outputs never loads.
   Confirm the rule actually loads when a generator script is opened, and report how you confirmed it.

2. **The worked example, rung by rung.** Log the 2768-mK correction (rung 0) and add it to the rule file (rung 1).
   Then write a check that reads the general-notes text of a sheet and fails if it cites ISO 2768-2 or a geometrical
   "K"/"H"/"L" class, and requires an ISO 2768-1 class, ISO 22081 and ISO 8015. Give it a regression fixture: the
   current default note, which must keep failing forever. Ask the designer whether "mK" should warn or fail during the
   transition, because some shops still accept it. Change the default note in `make_drawing_set.py` (not frozen) only
   after he agrees. When the check is green on the corrected fixture, delete the prose line from the rule file and set
   the log entry to rung 3 with enforced-by pointing at the check. The deletion is part of the method: enforced rules
   leave the advisory layer so it stays short enough to be followed. [IR]

3. **Title-block and general-notes check.** Using `docs/drawings/set-index.json` and text extracted with pypdf from the
   existing PDFs (no rebuild), check the ISO 7200 mandatory fields (legal owner, identification number, date of issue,
   sheet number, title, approver, creator, document type), the first-angle projection symbol or note, sheet size
   against frame, and no "TBD" strings. Report every failure per sheet; fix none.

4. **Correction-log hookup.** Every failure from these checks appends to, or increments, the matching
   `corrections.jsonl` entry with origin `hook`/`checker`, so recurrence is counted without anyone remembering to log
   it.

5. **Independent checker agent.** Create `.claude/agents/drawing-checker.md`: read-only tools, a PreToolUse block on
   writes in its own frontmatter, `memory: project`. It receives artifact paths, check outputs and the rubric only,
   never the producing conversation. Draft the rubric as a separate committed file: each item PASS / FAIL / WARN with
   a severity, and an explicit instruction to flag only issues affecting correctness, manufacturability or HV safety
   (reviewers asked to find gaps reliably find some). The rubric is the pre-committed verdict, so it is committed and
   reviewed by the designer **before** the first run. Numbers are judged from check outputs and extracted text, never
   from looking at a rendered image; a visual pass, if used, is limited to overlaps, legibility, hatching and missing
   views, on cropped tiles with an opaque background. [IR]

6. **Checker canary.** Make one known-good fixture sheet and one known-bad fixture with seeded defects (the 2768-mK
   note, a missing title-block field, a "TBD"). Every checker run includes both. If either is misjudged, the run is
   reported as `CHECKER-CANARY-FAIL` and none of its verdicts count. This is the dual-canary idiom applied to the
   checker itself. [ME]

7. **Reflect skill.** Create `.claude/skills/reflect/`: reads `corrections.jsonl`, clusters entries, and proposes
   promotions (rung 0→1 on second occurrence; 1→2 when a rule needs tables or a procedure; →3 when a script can decide
   it) and prunes (rules that never fired). It writes a proposal table and applies nothing; the designer approves
   promotions, and each approved promotion is its own small commit with its fixture.

## Named checks

| ID | Check | Pass condition |
|---|---|---|
| R-LOAD | Open a generator script | `drafting.md` is in context; method reported |
| C-2768-OLD | 2768 check on current default note | FAIL |
| C-2768-NEW | 2768 check on corrected fixture | PASS |
| C-2768-PRUNE | Rule file after green | 2768 line removed; log entry rung 3, enforced-by set |
| C-TB-RUN | Title-block check over existing set | Runs on every sheet in `set-index.json`; per-sheet report |
| K-RUBRIC | Rubric committed before first checker run | Commit order verifiable in history |
| K-CANARY | Checker on good / bad fixtures | Good PASS, bad FAIL on each seeded defect |
| K-BLIND | Checker invocation | Receives paths, outputs, rubric only |
| K-RO | Checker attempts a write | Blocked |
| L-AUTO | A check failure | Log entry created or incremented with origin set |

## Pre-committed verdicts

PASS: all named checks pass, and the checker returns verdicts on three real sheets the designer chooses.
On C-TB-RUN, any count of failing sheets is an acceptable result and is the deliverable. Zero failures across the
whole set is treated as suspicious, not as success: re-run K-CANARY and inspect the extraction before reporting it,
because a check that has never fired is unproven. [ME]
FAIL-ANY on K-CANARY voids the checker's verdicts in this phase; report and stop.

## Deliverables

PR `claude/drafting-infra-p1` → `claude/synthesis-phase1` containing: `.claude/rules/drafting.md`, the 2768 and
title-block checks with fixtures, the rubric file, `.claude/agents/drawing-checker.md`, `.claude/skills/reflect/`,
the designer-approved change to the default note (if approved), CHANGELOG entry. Exit report: named-check table,
per-sheet title-block failures, checker verdicts on the three chosen sheets, canary result, and the log entries that
moved rungs. Negative results are deliverables.

Frozen empty-diff asserted. Not merged.
