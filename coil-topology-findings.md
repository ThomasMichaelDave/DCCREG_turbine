# Findings — split L_R + bifilar self-resonant coil study

**Branch** `coil-topology` (off `series-resonator` `b62e642`). **Verdict:**
`SPLIT-L` do-it (node stress ×0.50) · `TRANSIENT-RELIEF` 35→17.5 kV (clears the C1/C2 overstress) ·
`DOWNBACK-L` fields-add 300 µH (opposed = the non-inductive trap) · `SELF-C` simple 4.8 pF / bifilar 790 pF ·
`SELF-RESONANCE` bifilar SRF→f₀, G≈408, modes 559/761 kHz, Q_sr 408 · **`ANTINODE-STRESS` 2.9–5.8 kV/mm at
the air limit** → **top-level: `ANTINODE-STRESS-DOMINATES` → `SIMPLE-DOWNBACK-PREFERRED`**.

**The two-part answer:** Part A (the symmetric split) is a **clean win — do it**; it halves the
fire-transient node-to-ground stress and removes a real C1/C2 overstress the asymmetric topology introduced.
Part B (the Tesla-bifilar self-resonant coil) is the fork: the bifilar *can* be tuned so its self-resonance
lands on f₀ (a genuine distributed resonator with voltage gain), **but** the quarter-wave antinode
concentrates the resonant voltage onto a few inter-filar gaps at **2.9–5.8 kV/mm — at/above the 3 kV/mm air
limit** — manufacturing a new air/surface stress *inside the winding*, in a machine already shown to be
air/surface-bound (battery-capacity rev 3). The conservative **simple down-and-back** is preferred.

**Scope:** resonator-topology study. Inherits the resonator (L_R 79 µH, C_R 789 pF, f₀ 637 kHz, Z₀ 316 Ω) +
the 36-turn Cu 3/1 mm conical coil (r28→76 mm, 108 mm axial), the series-resonator fire transient (~20 kV
across L_R → ~35 kV node-5 peak, `series_resonator.csv` @ `b62e642`), and the battery-capacity rev-3 survey
(C1/C2 7 mm air = 21 kV binding; the undimensioned creepage flag 12–30 kV). **Geometry from the DXF r0_6 +
`docs/varcap-design-freeze-v0.10.md` §3 — not index.html** (the rev-3 standing correction). Frozen modules
byte-identical (0 producer edits, asserted). **Ordinary distributed-circuit EE — no DCCREG.** Refs: Medhurst
(self-C, Q); helical-resonator theory; Kuffel/Zaengl (inter-turn standoff).

---

## Part A — the symmetric split (clean win)

**`SPLIT-L`.** Two L_R/2 = 39.5 µH halves, one at each end of C_R, axially adjacent on the bicone → they
mutually couple (M = k·L_half, k ≈ 0.30 `[IR]`). **Aiding** sense chosen: L_total = L_R/2 + L_R/2 + 2M =
**102.7 µH** (opposed would give 55.3 µH — rejected). f₀ shifts 637 → **559 kHz**; restore by retuning C_R
**789 → 608 pF**, *or* size each half below L_R/2 so the coupled total returns to 79 µH. Anchor: at M = 0 the
two halves give exactly L_R (self-test a).

**`TRANSIENT-RELIEF`.** With a grounded centre reference the ~20 kV L_R swing splits into two ~10 kV drops,
so each rotor node sees **half** the node-to-ground swing: **V(node 5) = V(node 6) = 17.5 kV vs the 35 kV
asymmetric baseline (stress factor 0.50)**.

**Insulation benefit (tied to rev 3).** The asymmetric baseline puts **35 kV** on node 5 — **above** the
C1/C2 7 mm-air binding limit (**21 kV**): the single-coil series topology *overstresses* the binding element
on every fire. The split brings it to **17.5 kV, safely below 21 kV** — it doesn't just balance, it **fixes a
real overstress**. For the flagged bare-edge creepage (12–30 kV), 17.5 kV clears a **clean** edge (≥30 kV →
margin restored above the 15 kV operating point) but not a fully-dirty 12 kV edge — so the split **buys the
creepage margin for a clean/ribbed edge before r0_10 is even drafted**, and de-risks the rest.

## Part B — coil topology

**`DOWNBACK-L` (B1).** Down-the-cone-and-back-up with the go/return fields **adding** → L = 2·L_pass +
2k·L_pass = **300 µH** (vs the 79 µH reference; more turns in the same space). **Opposed** sense → **15.8 µH**
— the **non-inductive bifilar trap** (L nearly cancels); flagged. The fields *must* add; a design hits the
needed per-half L by turns count.

**`SELF-C` (B2, Medhurst).** Simple down-and-back (low-ΔV return path) → **C_self ≈ 4.8 pF** (≈ a plain
solenoid of equal L). **Tesla-bifilar** (adjacent filars at large ΔV) → **C_self ≈ 790 pF** (×165), the value
that lands f_SRF on f₀. Ordering bifilar ≫ simple ≈ solenoid (self-test d).

**`SELF-RESONANCE` (B3).**
- **SRF.** Simple coil f_SRF = 1/(2π√(L·C_self)) = **8.2 MHz** ≫ f₀ → it is a **lumped inductor** (the present
  coil); the distributed quarter-wave cross-check (c/4l_wire) = 6.4 MHz agrees within the helical correction
  (self-test e). The **bifilar tuned to C_self = 790 pF lands f_SRF = 637 kHz = f₀** — the design point: the
  coil is *meant* to ring at resonance (self-test e2).
- **Standing wave.** Grounded at the shaft, high-Z at the C_R end → a quarter-wave resonator: **voltage node
  at the shaft, voltage antinode at the C_R end**, current the reverse.
- **Resonant gain.** G = V_antinode/V_drive ≈ Q ≈ **408**.
- **Coupled modes.** The A and B self-resonant coils, coupled by k and sharing C_R, split into
  **even (f₊ = f₀/√(1+k) = 559 kHz, in-phase — the symmetric fire selects it)** and **odd (f₋ = 761 kHz)**.
- **Self-resonant Q.** Skin-limited R_AC = 0.77 Ω (δ = 82 µm, ×3 proximity) → **Q_sr ≈ 408**, comparable to
  the lumped tank Q ≈ 500 — the self-resonant coil *can* hold a usable Q.
- **Functional implication.** If it self-resonates, the **AC ring lives in the coil and the DC accumulation
  stays in C_R** — the coil becomes a resonant step-up charger (antinode → C_R), separating the two roles
  C_R currently carries. This clean split *does* emerge electrically — the coil and C_R don't fight (the
  bifilar SRF is designed onto f₀). The catch is mechanical/insulation, not electrical:

**`ANTINODE-STRESS` (B4) — the decisive number.** The standing wave concentrates the full resonant voltage at
the antinode, so the inter-filar stress is highest there (not the uniform estimate). Inter-filar ΔV ≈
0.5·V_antinode `[IR]` across the ~3 mm filar gap:
- **Split charger view (V_antinode = 17.5 kV): 2.9 kV/mm** — margin only **1.03×** to the 3 kV/mm air limit.
- **Unsplit (35 kV): 5.8 kV/mm** — **1.9× over** the air limit.
- And these are the **clamped lower bound**; the resonant gain **G ≈ 408** magnifies any unclamped buildup,
  and a tighter filar gap (needed to *reach* the 790 pF self-C) raises the stress further.

A destructive inter-filar flashover needs a real design margin, not 1.03× — and the bifilar antinode sits
**at or above the air limit even at the clamped lower bound**, inside a machine already air/surface-bound. So
the self-resonant coil **manufactures the very failure mode rev 3 identified, concentrated in the winding**.

## Dispositions (all three, for the TMD gate)

- **`PARASITIC`** — minimise self-C (4.8 pF), lumped resonator, operate f₀ = 637 kHz ≪ SRF = 8 MHz. **Clean;
  the present coil is already here.** Recommended with Part A.
- **`LUMPED-TANK`** — let the self-C add to C_R (operate < SRF). The simple coil's 4.8 pF is < 0.7 % of
  789 pF → negligible retune. Equivalent to PARASITIC in practice.
- **`SELF-RESONANT`** — operate *at* SRF (bifilar tuned to f₀): coil = AC ring + step-up charger, C_R = pure
  DC store. Electrically elegant and the Q holds — **but the antinode air/surface stress is the binding
  limit**, so not robust for this machine.

## Top-level verdict

**`ANTINODE-STRESS-DOMINATES` → `SIMPLE-DOWNBACK-PREFERRED`.** Do Part A (the split) unconditionally — it is a
clean electrical + mechanical balance win that removes a real C1/C2 overstress and buys creepage margin. For
Part B take the **simple down-and-back** (low self-C, lumped inductor, operate ≪ SRF): the self-resonant
bifilar's upside (coil = ring, C_R = DC store, with real Q and gain) is genuine, but the quarter-wave antinode
puts the full resonant voltage across a few inter-filar gaps at the air/surface limit — the one failure mode
this machine is known to have. The verdict hinges on that single number, and it lands against the bifilar.

## Self-tests (all PASS)

(a) split M = 0 → exactly L_R (equivalence anchor); (b) 35 kV asymmetric → 17.5 kV symmetric node-to-ground;
(c) down-and-back fields-add 300 µH O(79 µH), opposed → 15.8 µH (the non-inductive trap); (d) self-C ordering
bifilar (790 pF) ≫ simple (4.8 pF) ≈ solenoid; (e) SRF lumped 8.2 MHz vs quarter-wave 6.4 MHz agree within
the helical correction; (e2) bifilar SRF tuned onto f₀ (637 kHz); (f) antinode inter-turn stress hand calc
(0.5·17.5 kV ÷ 3 mm = 2.9 kV/mm) matches.

## Deliverables

`sim/coil_topology.py` (split model + coupling + self-resonant helical treatment + 7 self-tests) ·
`coil-topology-findings.md` (this) · `coil_topology.csv` · `coil_transient_split.png` (Part A node-voltage
relief vs the C1/C2 and creepage limits) · `coil_standing_wave.png` (the quarter-wave profile, antinode at the
C_R end, inter-filar-stress band) · `coil_srf_modes.png` (SRF & coupled modes vs self-C — the bifilar tuning
knob). Frozen modules byte-identical; **not merged**.
