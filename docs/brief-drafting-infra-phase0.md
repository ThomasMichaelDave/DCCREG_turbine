# Brief — Drafting infrastructure, Phase 0: guardrails, correction intake, baseline

| Rev | Date | Author | Change |
|---|---|---|---|
| 0.1 | 2026-10-16 | chat (scrutiny layer) | First issue, for designer review |

## Purpose

The repo writes corrections down well (L1–L12, ledger §2.4 and §6, `dxf_flags.md`), but nothing moves a correction
from prose to enforcement, so drafting and electrical corrections recur. Phase 0 builds the intake and the guardrails
that every later phase relies on: a committed correction log, two hooks that enforce the freeze without depending on
the model's attention, pinned dependencies, and a clean agent roster. It adds no drafting knowledge yet. That is
deliberate: the ladder (log → scoped rule → skill → enforced check) needs its bottom rung and its enforcement
mechanism proven before anything is placed on it. [IR]

## Baseline and branch

Work on a new branch `claude/drafting-infra` cut from `claude/synthesis-phase1` (the live branch; `main` is stale
since 2026-06-20). Open a PR into `claude/synthesis-phase1`. The designer merges; you do not.

## Out of scope

Any change to the frozen set or `rebuild/s0_base/`. Any change to `docs/make_drawing_set.py` or
`docs/make_core_drawing.py`. Building PDFs (the designer, 2026-10-15). Drafting rules, skills or checks beyond what
is listed here; those are Phase 1.

## Constraints that shape the approach

The designer runs Claude Code in VS Code on Windows, with cmd.exe rather than PowerShell; sessions also run in the
cloud. Hooks are shell commands, so write every hook as a small Python script under `.claude/hooks/` and call it the
same way from `settings.json`, so one definition works in both places. Watch the interpreter name: the repo's
CLAUDE.md uses `python3`, which on Windows may resolve to the Store stub. Find a command form that works on both and
prove it on both (check H-WIN). [IR]

The frozen-file check already exists as a command in `README.md`. The hooks must call that same logic rather than
re-implement it, so there is one definition of "frozen". [IR]

## Steps (reasoning and approach; implementation is yours)

1. **Agent roster.** Read every file in `.claude/agents/` in full. Several hard-code `claude/new-session-0az7f9` as
   baseline and fix output paths; some may lack `tools:` restrictions. Produce one reviewable diff that points them at
   the current baseline (preferably by reference to CLAUDE.md rather than a hard-coded branch name, so this does not
   rot again) and adds read-only tool lists to the scrutiny agents, which should never write. Ask before changing any
   agent's scope.

2. **Freeze enforcement, two layers.** A PreToolUse hook denies Edit/Write on any path in the frozen set or under
   `rebuild/s0_base/`, with a message naming freeze commit `b33baa2` and stating that only the designer lifts a freeze.
   Edit/Write hooks do not see files changed by shell commands, so add a Stop hook that runs the frozen empty-diff check
   at the end of each turn and blocks if it is non-zero. The Stop hook must respect `stop_hook_active` so it cannot
   loop. Keep the frozen list in one place that both hooks and the README check read.

3. **Correction log.** Create `.claude/corrections.jsonl` (committed) and a schema beside it. One entry per correction,
   with: id, date, domain (mech / elec / doc / process), what was wrong, the correct rule, source (standard clause or
   repo file), epistemic tag, occurrence count, current rung (0–3), enforced-by (empty until rung 3), fixture path, and
   origin (designer / hook / checker). Seed it from rebuild L1–L12, the drafting- and wiring-relevant items in ledger
   §2.4 and §6, `dxf_flags.md`, and the defect table in the plan report (ISO 2768-2 withdrawn → ISO 22081:2021;
   IEC 60664-1 out of scope above 1.5 kV DC; ISO 21920 acceptance rule; ISO 128-2 line weights as `[RH]` until
   verified; KiCad 9 vs 10 pin). Do not invent entries; every seed cites where it came from.

4. **Intake skill.** Create `.claude/skills/log-correction/` so the designer can type `/log-correction <what was
   wrong>` in any session. It appends a schema-valid entry, or, if a matching entry exists, increments its count
   instead of duplicating. It changes nothing else. Add one line to CLAUDE.md: when the designer corrects a drafting,
   wiring or documentation convention, offer to log it with this skill.

5. **Pin dependencies.** Record the versions currently installed for the drawing, ledger and check path (OCP,
   matplotlib, pypdf, ezdxf, numpy, and whatever else those scripts import) in a requirements file, so that a canary
   failure points at the design and not at a library drift.

6. **CLAUDE.md trim.** Propose, as a diff, a CLAUDE.md that keeps only the invariants (guardrails, read order, run /
   verify, commits, scope) plus the pointer to the correction log. Do not apply the trim; the designer reviews it.

## Named checks

| ID | Check | Pass condition |
|---|---|---|
| H-FROZEN-EDIT | Deliberate Edit to `shuttle_core.py` | Denied, message names `b33baa2`; file unchanged |
| H-FROZEN-SHELL | Deliberate shell write to a frozen file | Stop hook blocks; then revert; frozen check prints 0 |
| H-LOOP | Stop hook with `stop_hook_active` set | Does not re-block |
| H-WIN | H-FROZEN-EDIT and H-FROZEN-SHELL on Windows VS Code and in a cloud session | Identical behaviour in both |
| L-SCHEMA | Every line of `corrections.jsonl` validates | Zero schema errors |
| L-SEED | Every seeded entry cites a source | Zero entries without source |
| L-DEDUP | `/log-correction` with a known item | Count increments; no new line |
| A-BRANCH | Grep `.claude/agents/` for `new-session-0az7f9` | Zero hits |
| D-PIN | Fresh venv from the requirements file | `make pyodide-parity` green; frozen check prints 0 |

## Pre-committed verdicts

PASS: all named checks pass. FAIL-ANY: stop at the failing check and report it; do not work around it.
Specific negative result to report rather than hide: if hooks cannot be made to behave identically on Windows and in
the cloud (H-WIN), report what differs, and propose a git pre-commit hook as the fallback enforcement layer. That
outcome is a deliverable, not a failure.

## Deliverables

PR `claude/drafting-infra` → `claude/synthesis-phase1` containing: `.claude/settings.json`, `.claude/hooks/`,
`.claude/corrections.jsonl` and its schema, `.claude/skills/log-correction/`, agent-roster diff, requirements file,
CLAUDE.md trim as a proposed diff (not applied), CHANGELOG entry. Exit report with the named-check table filled in.

Frozen empty-diff asserted. Not merged.
