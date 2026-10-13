# [Domain] Specification

**Date:** YYYY-MM-DD
**Baseline evidence:** design state `09243c7` (locked 2026-10-09), branch `claude/new-session-0az7f9`
**Synthesis branch:** `claude/synthesis-phase1`
**Agent:** [agent name]

## Purpose

[One paragraph: what this specification covers, what it does not, and what it
depends on from other specs.]

## Governing constraints

[The non-negotiable requirements this spec must satisfy — conservation laws,
breakdown limits, the equalization-is-the-pump principle, the designer's DECIDED
items. Each cites its source.]

## Specification

### [Section title]

| Parameter | Value | Source / basis | Tag | Status |
|:----------|:------|:---------------|:----|:-------|
| [name] | [value with units] | [evidence file or derivation] | `[OC]` / `[IR]` / `[RH]` | DECIDED / PROPOSED / OPEN |

**Rationale:** [Why this value. What the evidence shows. What the alternatives
are and why they were not chosen — or why the choice is OPEN for the designer.]

---

[Repeat the table-and-rationale block for each section.]

## Evidence ledger

What the current design does, where it works, and where it doesn't — the
evidence that drove this spec's choices.

| Item | Current design | Evidence | Issue (if any) |
|:-----|:---------------|:---------|:---------------|
| [e.g. varicap κ] | [3.51 as built] | [tube-strays-findings §4] | [κ discrepancy: deck uses 7.47] |

## Cross-spec dependencies

Items that another spec must accept or provide.

| Item | Value | Needed by | Note |
|:-----|:------|:----------|:-----|
| [e.g. tube outer envelope] | [Ø 340 mm × 420 mm] | retainer-spec | [from tube-synth §3] |

## Items deferred to bench

Quantities only measurement can settle. These are OPEN by specification.

| Item | Why it is open | What the bench measures | Source |
|:-----|:---------------|:-----------------------|:-------|
| [e.g. rings' hold-off] | [no reliable model for surface creepage at this scale] | [breakdown voltage of the ring stack in air] | [bench-test-rings.md] |

## Recommendations for the designer

[Actions for the designer, if any. Each tagged PROPOSED — never DECIDED.
The designer decides.]
