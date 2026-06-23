# KICAD-OVERLAY — findings

**Verdict: `SCHEMATIC-IMPORTED`.** The real KiCad schematic now renders in the tool with every one of its
**43 components showing a live value** via re-tagged `sv_<REF>` slots; the fail-closed consistency stamp is
**green — schematic ↔ `REF_MAP` ↔ netlist of record all reconcile by label (43 = 43 = 43)**; the interim
hand-drawn draft is retired (kept behind `--interim`); the dual canary is untouched (solver path empty-diff).
*Status: [ME]/[OC]/[IR] — pure tooling, firewall intact, mergeable. Two items flagged for TMD (design
authority): the export hides values, and the `C__AR4` refdes typo.*

## The six named checks (brief §5)

### 1. KiCad SVG exported; refs parseable; matches the 43-comp / 8-gap set
TMD's fresh export (`DCCREG_Turbine_circuit.svg` + `.net`, dated 2026-06-23, placed in `docs/kicad/`) is the
SSOT visual. `kicad-cli` is unavailable in this environment, so the **export was supplied pre-rendered** by
TMD — no re-render needed. The SVG carries each component's reference designator as **parseable `<text>`**
(KiCad emits each label as an invisible `<text>` with the string + position, immediately followed by a
`<g class="stroked-text">` of visible glyph paths). Parsed **43 reference designators**, exactly the
**43-comp / 8-gap** machine: `C1 C2 · Ca1 Cb1 · Cx3 Cx4 · C_R1 · Lx3 Lx4 · L_R1 L_R2 · L_A1–6 · L_B1–6 ·
C_AR1,2,3,5,6 + C__AR4 · C_BR1–6 · SG1 SG2 SG3a1 SG3b1 SG4a1 SG4b1 · BS3 BS4` — **all 8 gaps present in the
drawing.**

> **Deviation, flagged [ME]:** this sheet's export shows **reference designators only — component values are
> hidden** (zero value `<text>` elements). The brief's preferred mechanism (§2: "re-tag KiCad's own value
> text") therefore has nothing to re-tag. Adopted the re-export-robust fallback the brief itself anticipates
> (§6 `KICAD-EXPORT-ISSUE` note): **inject** a value slot anchored to each refdes's KiCad position. Binding
> stays by `id`/label and re-derives on every re-export — the durability the brief asks for is preserved.
> *(If TMD turns value fields on in KiCad, the same `gen_artifacts` pass can be pointed at the value text.)*

### 2. `gen_artifacts.py` re-tags each value as `sv_<REF>`; `schematic.svg` is the real layout; interim retired
New `tag_kicad_svg()` in `tools/gen_artifacts.py`:
- lays a **white backing rect** so the black KiCad strokes read in the dark drawer;
- for **every** drawn refdes, injects `<text id="sv_<REF>" …>--</text>` anchored a line below KiCad's own
  refdes position (font/anchor inherited from the export);
- writes `tools/schematic.svg` (the real KiCad layout carrying the live slots).

Run output: `43 refdes re-tagged as sv_<REF> live slots · reconcile vs netlist of record: MATCH`. The
interim hand-drawn `gen_schematic()` is **retired from the default path** and kept behind
`python3 tools/gen_artifacts.py --interim` (TMD's call, per §2). `openRef()` now loads `schematic.svg` as
*"real KiCad layout"* — the `varcap.svg` / `schematic.cir` / "interim" / `AWAITING-KICAD` scaffolding is gone.

### 3. `REF_MAP` covers every drawn component (no partial set); units correct
The authoritative map is now **`REF_MAP`** (one place; `fillSchematicValues`, the legend, and the stamp all
read it). One entry per drawn component, **43 total**:

| family | refs | live field | unit | kind |
|---|---|---|---|---|
| C1 / C2 | C1, C2 | `C1max_pF` | pF | live |
| Ca / Cb | Ca1, Cb1 | `Ca_pF` | pF | live |
| Cx3 / Cx4 | Cx3, Cx4 | `Cx_maxMm` | pF | live |
| C_R1 | C_R1 | `C_R_pF` | pF | live |
| Lx3 / Lx4 | Lx3, Lx4 | `Lx_mH` | mH | live |
| SG1–4 | SG1, SG2, SG3a1, SG3b1, SG4a1, SG4b1 | `V_strike_kV` | kV | live |
| BS3 / BS4 | BS3, BS4 | `0.6·V_strike_kV` (FE onset) | kV | derived (live) |
| L_R1 / L_R2 | L_R1, L_R2 | 39.5 µH | µH | static |
| L_A1–6 | L_A1…L_A6 | 0.64 H | H | static |
| L_B1–6 | L_B1…L_B6 | 0.64 H | H | static |
| C_AR1–6 | C_AR1,2,3,5,6 + C__AR4 | 440 nF | nF | static |
| C_BR1–6 | C_BR1…C_BR6 | 440 nF | nF | static |

The caps/island-inductor/gap-`V_strike` values are **live from the solver** (`evaluate_design`); the motor
coils, per-coil DC-block caps, and resonator coils are **Block-D / fixed design constants** (the solver in
the live tool runs `design_synth`, which does not compute the Block-D motor) and are marked **`· static`** in
the legend, honestly distinguished from the live ones. `BS3/BS4` track `0.6·V_strike` (the FE backstop onset).

### 4. The consistency stamp reconciles SVG ↔ `REF_MAP` ↔ netlist — green
The stamp (`consistencyCheck`) asserts the three sets agree **by label**:
**drawn** (refdes in `schematic.svg`) = **mapped** (`REF_MAP` keys) = **netlist of record**
(`topology_edge_list.csv` components). Result: **MATCH — 43 drawn = 43 mapped = 43 netlist.** Any
drawn-but-unmapped / mapped-but-undrawn / netlist-only / drawn-not-in-netlist ref is **listed** (amber),
never a silent blank — green only when all three reconcile.

> **Note:** the netlist of record is `topology_edge_list.csv` (the pin-exact geometric extraction, **all 8
> gaps**), *not* the KiCad `.net` — that netlister under-exports the gaps (only the two `SolderJumper` gaps
> SG3a1/SG4a1; the known `NETLIST-CORRECTION` issue). The **SVG visual** and `topology_edge_list.csv` both
> carry the full 8-gap set and agree exactly, so the stamp is green on the complete machine.

### 5. The dual canary still passes (overlay doesn't disturb the solver path)
`sim/design_synth.py`, the frozen cores, and the canary logic are **byte-identical** on this branch
(`git diff` empty vs `numpy-pyodide-compat`). `evaluate_design(established_anchor())` still returns operating
η **0.518**, regression z **1.3336**, feasible — and every field the overlay reads
(`C1max_pF/Ca_pF/Cx_maxMm/C_R_pF/Lx_mH/V_strike_kV`) is present. The HTML JS passes `node --check`.

### 6. Re-export robustness
`gen_artifacts.py` re-reads the ref set **and** positions from the export on every run — nothing is
hand-placed. Re-running on a fresh export re-binds all slots automatically; if a component is added/removed,
its slot appears/disappears and the stamp catches any `REF_MAP` lag (drawn-but-unmapped). This is the
property that makes the **Ca/Cb cut (one DC-block cap per branch)** drop in on a re-run with no hand-editing.

## Flags for TMD (design authority on the schematic)
1. **Values hidden in the export** — turn the value fields on in KiCad if you want the overlay to re-tag
   KiCad's own value positions (cosmetically tighter) instead of the anchored-below injection. *(The current
   anchored slots can sit close to a refdes/wire on a few parts; functional, refine in KiCad if desired.)*
2. **`C__AR4` refdes typo** — stray double underscore vs its `C_AR{1,2,3,5,6}` siblings. Handled verbatim in
   `REF_MAP` (so the stamp stays green), but worth normalizing to `C_AR4` in KiCad.

## Deliverables
- `docs/kicad/DCCREG_Turbine_circuit.svg` + `.net` — TMD's real export (SSOT visual + provenance).
- `tools/gen_artifacts.py` — `tag_kicad_svg()` (the export post-processor + re-tag + reconcile); interim
  behind `--interim`.
- `tools/schematic.svg` — the re-tagged KiCad layout (43 `sv_<REF>` slots, white backing).
- `tools/charge-pump-synth-live.html` — `REF_MAP` (authoritative), `fillSchematicValues` over all 43, the
  legend grouped from `REF_MAP`, the three-way fail-closed stamp, `openRef` loading the real export.
- `tools/README.md` — the KiCad-overlay pipeline + the two TMD flags.

**Frozen solvers + `design_synth` empty-diff. `SCHEMATIC-IMPORTED` — mergeable: a tooling feature + a drift
guard.**
