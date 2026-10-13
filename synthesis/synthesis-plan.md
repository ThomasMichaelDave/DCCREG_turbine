# Synthesis Plan — Phase 1

## What is being synthesised

The DCCREG tube without spark gaps, rebuilt from validated principles.
Evidence ledger: design state `09243c7`, branch `claude/new-session-0az7f9`.
The evidence is read-only; the synthesis produces new specifications.

### Phase 1 scope

| Included | Excluded (Phase 2+) |
|:---------|:--------------------|
| Core Bennet doubler engine (validated parameters) | Spark-gap commutator |
| Varicaps C1/C2, node stray budget | Rings as stator assembly |
| Rings supply chain (chain diodes, chain caps) | Control electronics beyond K4 |
| HV sticks D1–D4, clamp strings Z1/Z4 | Hub structure (interface only) |
| Motor parts: D1*–D4*, La/Lb, AH bypass, snubbers, K4 | |
| Air insulation stack | |
| Electrical integrity (breakdown, creepage, field) | |
| Retainer (bearings, motor, drive, cage) | |
| Conservation closure across all specs | |

## Agent sequence and dependencies

```
Step 1: core-engine-spec          (alone — the target)
        ↓ gate
Step 2: tube-synth                (needs core spec)
        ↓ gate
Step 3: electrical-integrity  ‖   retainer-spec    (parallel, both need tube spec)
        ↓ gate (both)
Step 4: conservation-auditor      (needs all four)
        ↓ gate
Step 5: cross-spec check + consolidated report
```

## Cross-spec targets

1. **Thermal:** tube dissipation (diode losses + copper + windage) vs retainer
   cooling capacity → steady-state temperature below hot-operation limit
2. **Shaft dynamics:** bearing stiffness → f1 vs 2× PRF (120 Hz); bay mode
   f2 at 108–117 Hz vs 120 Hz excitation (§6 item 77)
3. **κ discrepancy:** 3.51 (as-built 3-D solve) vs 7.47 (deck). The tube spec
   must decide which value governs and why.
4. **Stray budget:** three estimates (66/25, 1–3, 24.5 pF). The tube spec must
   allocate and justify.
5. **Clamp trim:** 66 → 60 TVS. The tube spec must decide or leave OPEN.
6. **Interface completeness:** tube → retainer (shaft, bearings, mass, loads);
   tube → rings (voltage, current, ripple); tube → commutator (wiring, deferred)

## Conservation gates

| Gate | What it checks |
|:-----|:---------------|
| After Step 1 | z consistent with η; equalization principle stated |
| After Step 2 | Component losses sum correctly; stray budget allocated |
| After Step 3 | No contradictions between electrical and mechanical specs |
| After Step 4 | Full power budget closes; η ≈ 0.50 not 0.70; equalization intact |
| At every gate | The equalization-is-the-pump principle is not violated |
