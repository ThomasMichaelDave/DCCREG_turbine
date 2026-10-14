# Synthesis Plan — Phase 1

**Date:** 2026-10-13
**Baseline evidence:** design state `09243c7` (locked 2026-10-09), branch `claude/new-session-0az7f9` — read-only.
**Agent:** synthesis-director

## What is being synthesised

The DCCREG tube without spark gaps, specified from validated principles, with the locked design as the evidence
ledger. The synthesis writes only under `synthesis/`; it edits no evidence file and no frozen file.

| Included | Excluded (Phase 2+) |
|:--|:--|
| The core engine: the doubler's validated parameters and the conservation principle | Spark-gap commutator |
| Varicaps C1 / C2, Ca / Cb, node-stray budget | The rings themselves (stator) — interface only |
| The rings' supply (the §3.9 ladder C3–C8, D5–D12, Csa / Csb; the record's CW chains as evidence) | Control electronics beyond K4 |
| HV sticks D1–D4, clamp strings Z1 / Z4 | Hub structure — interface only (envelope stated by the tube spec) |
| Motor parts: D1*–D4*, La / Lb, AH bypass, snubbers, K4 | |
| Air insulation stack | |
| Electrical integrity: breakdown, creepage, field clearance | |
| Retainer: bearings, motor, drive, cage | |
| Conservation closure across all specs | |

## A framing condition the director enforces at every gate

The brief names z = 1.334, η = 0.386 direct / ≈ 0.50 with the island. Those are the **disc spark-gap machine's**
validated numbers (`docs/efficiency-resolution.md`; frozen `reference/doubler_core` regression) [OC]. The design of
record is the tube with the de Queiroz **diode** core, whose transfers are lossless at the transfer (η 1.00,
`sim/diode-stack-findings.md`), whose products are static fields, and which "has no efficiency of record"
(`CONVENTIONS.md`, efficiency section; ledger §6 item 12) [IR].

So the core spec must:
1. state z 1.334 / η 0.386 / ≈ 0.50 as the frozen engine's validated anchor, with their source, **and** say they
   belong to the superseded disc machine (no island exists in Phase 1, since spark gaps and islands are out of scope);
2. state the tube's operating engine numbers separately: z 1.31 bare (1.3095 ngspice), 1.191 with the chains, as built
   1.058 / 1.031, the §3.9 redesign 1.0142 → 1.0164 laid out → 1.01589 with the mounts;
3. state the equalization principle as the governing constraint for both: the belt's power into the pump ends as heat
   in the clamps (the tube's "sink" is dissipative); no spec may claim recovery from the rectifying transfers.

Any spec that applies η ≈ 0.50 or 0.70 to the diode tube fails its gate.

## Agent sequence and dependencies

```
Step 1  core-engine-spec                         → synthesis/core-engine-spec.md
        ↓ gate 1
Step 2  tube-synth                               → synthesis/tube-spec.md
        ↓ gate 2
Step 3  electrical-integrity ‖ retainer-spec     → synthesis/electrical-integrity-audit.md, synthesis/retainer-spec.md
        ↓ gate 3
Step 4  conservation-auditor                     → synthesis/conservation-audit.md
        ↓ gate 4 (FAIL → correct the cause, re-audit)
Step 5  director: cross-spec check               → synthesis/synthesis-report.md
```

## Gates

| Gate | Checks |
|:--|:--|
| 1 core | z 1.334 / η 0.386 / ≈ 0.50 stated and correctly attributed; the tube's z set stated; equalization principle governing; varicap requirement (κ, C_min / C_max); clamp requirement (BV, tolerance); stray budget |
| 2 tube | every component of the latest design (§3.9 layout, mounts, AH-drive parts) included; κ 3.51 vs 7.47 decided with reasons; strays allocated (66 / 25 record, 1–3 laid out, 24.5 assumed; 74.61 / 18.30 with the mounts); clamp 66 → 60 decided or OPEN with rationale; every diode typed and rated; tube envelope; shaft interface |
| 3 EI + retainer | every gap and creepage path checked; hot limits; flashover (ring B → 19.0 kV, item 41); bearings with preload (100 N vs 125–250 N); drive; cage (r 182–186); thermal; bay mode f2 108–117 Hz (item 77); no contradiction cage-clearance ↔ field, ventilation ↔ HV safety |
| 4 conservation | the power budget closes (pumps + windage + bearings = heat); η not imported onto the tube; charge balance per chain (208.5 nC/cycle: clamps 207.2 + rings 1.27); equalization intact |

## Cross-spec targets (director, after gate 4)

1. **Thermal:** tube + motor-part dissipation vs the retainer's cooling → steady temperatures below the hot-operation
   limits (sticks' hot leakage sets the seed: 4.87 kV hot for the redesign).
2. **Dynamics:** f1 79–85 Hz at d 25 and f2 108–117 Hz (item 77) vs 120 Hz pump and 240 Hz pulsation; 191 mN·m p-p
   varicap torque ripple in phase (§3.9).
3. **κ:** 3.51 (3-D, as built) vs 7.47 (2-D deck).
4. **Strays and clamp trim:** 66 vs 60 parts against the rings' ±14.77 – ±16.25 kV.
5. **Interfaces:** tube → retainer (shaft d 25 / d 30 OPEN, seats, masses 35.88 / 36.40 kg + 9.74 kg AH-drive parts,
   loads); tube → rings (±14.77 kV, 25.0 µA/chain charge, ripple); tube → commutator (Phase 2 wiring points).
6. **Evidence consistency:** §6 items resolved vs carried forward; components missed.
