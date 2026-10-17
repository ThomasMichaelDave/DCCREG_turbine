---
name: log-correction
description: >
  Log a correction the designer gives (a drafting, wiring or documentation convention, or any other
  correction of the record) in .claude/corrections.jsonl: bump the count of a matching entry, or append a
  new schema-valid one. Use when the designer types /log-correction <what was wrong>, or accepts an offer
  to log a correction.
argument-hint: <what was wrong>
allowed-tools: Read, Bash(python3 .claude/corrections.py *), Bash(python .claude/corrections.py *)
---

# /log-correction

Record one correction in `.claude/corrections.jsonl` (schema: `.claude/corrections.schema.json`). This skill
changes that file and nothing else. All reads and writes go through `.claude/corrections.py`; never edit the log
by hand. Use `python3`, or `python` if `python3` is the Windows Store stub.

The correction: **$ARGUMENTS**

1. **Look for a match.** Run `python3 .claude/corrections.py find <word> ...` with two or three distinctive words
   from the correction, and again with other words if nothing comes back. A match is an entry with the same
   *rule*: the same thing done wrong in the same way, even if worded differently, or found in another file.
   A related rule is not a match.

2. **A match:** run `python3 .claude/corrections.py bump <id>`. Do not add a line. Report the id, the entry's
   rule and its new count. If the designer's wording adds a source the entry lacks, say so; don't change it.

3. **No match:** assemble a new entry and run `python3 .claude/corrections.py add '<json>'` with:
   - `domain`: mech, elec, doc or process;
   - `wrong`: what was wrong, in the designer's terms;
   - `rule`: the correct rule;
   - `source`: the standard clause or repo file that holds it;
   - `tag`: [OC], [IR] or [RH], with `CONVENTIONS.md` §1's meanings (a standard not yet checked is [RH]);
   - `origin`: `designer` (or `hook` / `checker` when one of those raised it).
   The tool sets `id`, `date`, `count` 1, `rung` 0, an empty `enforced_by` and `fixture`. If the rule or the
   source is not in the designer's words or a file you can cite, ask the designer for it. Never invent either.

4. **Validate.** Run `python3 .claude/corrections.py validate`. It must report 0 schema errors. Report what was
   logged in one or two lines.
