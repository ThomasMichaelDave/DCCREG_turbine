# Patent notes: oblique-field and C_min-reducing electrostatic generators

Prepared for the design loop (TMD's pointer to the 1960s "oblique" patents).

**Source caveat.** These notes come from search-engine snippets (abstracts, bibliographic data, citation lists). The full patent texts could not be fetched from the session's network. Tags:

| tag | meaning |
|---|---|
| [B] | bibliographic data seen consistently |
| [S] | snippet text |
| [I] | inference |

## Patents with "oblique" in the title (Cosmic Inc., USAF/NASA contracts, early 1960s)

### US 3,173,033 — *Oblique field electrostatic generator* [B]

- Cosmic Inc., priority 1962-05-08, published 1965-03-09. Inventor not confirmed.
- https://patents.google.com/patent/US3173033A/en
- [S] The inductor electrodes keep a **constant, oblique field** (tangential and radial components) through which the conveyors move. Rotor conductors act as charge inductors and stator conductors as charge conveyors. Multipole (4-pole and 8-pole) versions behave as several generators in parallel.
- [I] The aim is power density at a near-breakdown field, held steady instead of collapsing each cycle the way a parallel-plate varicap's field does. A lower C_min is not claimed in the snippets.

### US 3,320,517 — *Brushless oblique field electrostatic generator* [B]

- Cosmic Inc., priority 1963-05-28, published 1967-05-16.
- https://patents.google.com/patent/US3320517A/en
- [S] It removes brushes, resistor chains and semiconductive coatings, and builds on US 3,173,033.

### Companion reports, with the geometry and measured data; worth obtaining

- Anton, Gignoux, Shea, *Constant Oblique Field Electrostatic Generator*, ASD-TDR-63-87 (1963). DTIC AD0405119: https://apps.dtic.mil/sti/citations/AD0405119
- Gignoux and Anton, NASA CR-54347 (1965), NTRS 19650011682. It compares the "single capacitor generator" with the "constant oblique field generator".

## Related patents on C_min, strays and field shaping (no "oblique" in the title)

| patent | assignee / author | idea | tag |
|---|---|---|---|
| US 3,094,653 *Electrostatic generator* (1963) | Tylan Corp | Rows of radial bars; **some bars are dedicated to shaping the field**, the rest form the varicap. The closest match to our C_min problem | [S] |
| US 3,107,326 *Variable capacitance electrostatic generator* (1963) | not confirmed | Multipole interleaved rotor and stator for vacuum. C_max at pole–pole, C_min at pole–gap | [S] |
| US 3,013,201 | Goldie, High Voltage Engineering | Self-excited variable-capacitance generator | [B] |
| US 2,194,839 | Van de Graaff and Trump | The root of the interleaved fan-plate vacuum family | [B] |
| US 3,225,275 *Ganged variable capacitors* | — | **A shield removes stray capacitance between isolated segments** | [S] |
| US 3,412,318 *Variable capacitor electric power generator* | — | not read | — |
| US 4,127,804 and US 4,126,822 | — | later work | — |
| US 8,264,121 and US 8,643,249 (LLNL-style) | — | later work | — |

## Bearing on our build [I]

1. **Field-shaping or guard electrodes**, earthed or driven, behind the stator face and between sectors. They intercept the see-through field to the Ca counter-plate (28 pF) and the hardware share (63 pF). This is move M1.
2. **An inter-sector angular gap much wider than the 7 mm plate gap**, and offset rotor and stator edges. These cut the 79 pF of coincident-edge fringe. This is move M2.
3. **Multipole or interleaved layouts**, which lower the fringe-to-area ratio.
4. **The oblique constant-field principle** is a different operating mode: the field stays constant, charge conveyors move through it. Adopting it would be a topology change, not a geometry tweak. Obtain CR-54347 before judging it.
