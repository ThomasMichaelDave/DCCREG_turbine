# [Domain] Scrutiny Findings

**Date:** YYYY-MM-DD
**Baseline:** design state `09243c7` (locked 2026-10-09)
**Branch:** `claude/new-session-0az7f9`
**Agent:** [agent name]

## Summary verdict

[One paragraph: CLEAN / CONCERNS / BLOCKERS. State the headline finding.]

## Checks performed

### [Check title]

| Field | Value |
|:------|:------|
| **Source** | [file that holds the authoritative number] |
| **Expected** | [what the design record says] |
| **Found** | [what the scrutiny found] |
| **Verdict** | PASS / CONCERN / FAIL / OPEN |
| **Tag** | `[OC]` / `[IR]` / `[RH]` |
| **Ledger §6 item** | [item number, if applicable] |

**Note:** [explanation if verdict is not PASS — what the discrepancy is,
what it means, and what would resolve it]

---

[Repeat the table-and-note block for each check item.]

## Cross-domain flags

Items that affect another domain's margins. The director uses these
for cross-referencing.

| Item | Value | Feeds into | Note |
|:-----|:------|:-----------|:-----|
| [e.g. magnetic pull per utron] | [28 N] | mech — gap survival | [source file] |

## Items deferred to bench

Quantities that only measurement can settle. These are not failures;
they are OPEN by design.

| Item | Why it is open | What the bench measures | Source |
|:-----|:---------------|:-----------------------|:-------|
| [e.g. rings' hold-off voltage] | [no reliable model for surface creepage at this scale] | [breakdown voltage of the ring stack in air] | [file] |

## Recommendations

[Actions for the designer, if any. Each tagged PROPOSED — never DECIDED.
The designer decides.]
