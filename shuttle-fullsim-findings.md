# shuttle-fullsim — gate report (rev 0.2): LR-value BLOCKER

**Status:** [IR] **BLOCKED before build — missing `LR` value.** Brief rev 0.2 resolved the two rev-0.1 gates (T0 station map re-anchored to SG1-at-C1-max with the shuttle direction reversed; export Gate-2 resolved via option (a), C(θ)/LR parameterised inside `shuttle_core.py`). But the option-(a) resolution adds a hard precondition — constraint #2: *"LR: numeric value read from `docs/commutator-design.md` (resonator section) and cited verbatim (symbol + value + section). If absent there, STOP and report a BLOCKER — do not invent a value."* **That value is absent.** Per the brief I stop here; no `shuttle_core.py`, anchor test, campaign, or timing diagram was built.

Branch: `shuttle-fullsim` (from `main` `9136624`). `reference/doubler_core.py` untouched (empty diff); `index.html` untouched (out of scope). Tiers: **[OC]** solver/standard · **[IR]** interpretive.

---

## Prior gates (rev 0.1) — resolved by brief rev 0.2

- **T0 (conduction anchor)** — RESOLVED. Rev 0.1 verified SG1/D1 conducts in the phase where **C1 = max** (phase A: C1=1000 → {D1,D3}; phase B: C1=160 → {D2,D4}). Rev 0.2 re-anchors the station map to SG1-at-C1-max and **reverses the shuttle direction** (load from stack nodes 3/2, fire into terminal nodes 1/4). [OC for the phase table; IR for the corrected map]
- **Export sufficiency** — RESOLVED via option (a): `C1(θ)/C2(θ)`, `Cx(θ)`, and `LR` are parameterised inside the new `shuttle_core.py` (consuming only the frozen scalar device-point values + `solve_doubler4`/`ANCHORS`), with a degenerate-limit anchor test (`z = 1.203 ± 0.03`) as the authorisation. [IR, TMD-approved]

---

## New gate (rev 0.2) — `LR` numeric value → **BLOCKER**

The brief fixes the LR source as `docs/commutator-design.md` and forbids both inventing it and importing from `index.html` (constraint #1). Inspection of `docs/commutator-design.md`:

- The only mentions of the resonator inductor are **qualitative** (lines 27–29):
  > "*Ground ≡ resonator rail.* The solver's ground (node 0) is physically the resonator rail (nodes 5–6, coil `L_RES`/`L1`). At PRF, `L1` is a near-short — the repo's 'L1-is-a-short-at-PRF' argument …"
- The **symbol** `L_RES`/`L1` is named, but there is **no numeric value** and **no resonator section** carrying one. (`grep -niE 'induct|µH|nH|henr|L_?RES|L1' docs/commutator-design.md` → only the lines above; no number.)

**BLOCKER (verbatim):**
```
MISSING: a numeric LR value in docs/commutator-design.md.
  Present: symbol only — "coil L_RES/L1" + the L1-short-at-PRF argument (lines 27–29).
  Absent:  any numeric inductance (no µH/nH/H value, no resonator section with a value).
Constraint #2 forbids inventing a value; constraint #1 forbids sourcing it from index.html.
=> No compliant source exists. STOP per constraint #2 / acceptance §7.
```

Note `LR` is needed for the §3 LR-modeled steady runs (campaign steps 2–5: pump with LR between nodes 5–6 at the cited value). The degenerate-limit anchor test shorts LR and would not need the value, but §3 specifies the module models LR at the cited value, and constraint #2 is an unconditional precondition — so the build does not start until LR is supplied.

---

## Decision returned to TMD (one line unblocks the whole build)

Record the authoritative resonator inductance in `docs/commutator-design.md` as **symbol + value + section** (e.g. a one-line "Resonator: `L_RES` ≈ ⟨value⟩ µH" in or near §2), then re-issue. After that, **every other input is present** and the full build proceeds: C(θ) raised-cosine profile (default), `Cx(θ)`/`pCboss`, the §1 reversed-shuttle station map, the threshold-fired gaps with emergent δ, the conservation ledgers, the degenerate-limit anchor, the campaign, and the timing diagram.

**For TMD's reference only (not used here):** a resonator inductance *is* computed in Block R (`resonatorCore` in `index.html`) and reported in `docs/report-external-review.md` as `L ≈ 123 µH` (default coupled tank) / `≈ 131 µH` (capillary self-test config). Per constraints #1/#2 I will neither import that nor adopt it as authoritative — TMD should confirm and record the value in `docs/commutator-design.md`.

No pre-committed **SHUTTLE-{PUMP-CONFIRMED | PUMP-BLOCKED | INDETERMINATE}** branch is declared: the simulation was gated out before the anchor test could run. A halted result is a deliverable, not a failure (acceptance §7: *"LR value cited verbatim … or BLOCKER reported."*).

---

## Constraints honoured

- `reference/doubler_core.py` untouched (empty diff); no imports from `index.html`; no invented LR value; no `shuttle_core.py` built.
- `index.html` untouched (out of scope).
- Symbol names cited verbatim (`L_RES`/`L1`); `θ`/`rotor`, `Nsec`, gap `g` hygiene respected; epistemic tags applied.
- Branch left for TMD review; **not merged** to `main`.
