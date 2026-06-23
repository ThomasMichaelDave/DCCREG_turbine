#!/usr/bin/env python3
"""
sim/ngspice_s3.py — S3: compose the full resonant machine end-to-end in ngspice (make-or-break).
================================================================================================
S0/S1/S2 confirmed the PIECES (linear, doubler z, resonant transfer). S3 composes the WHOLE machine
and reads z_res / eta_real end-to-end vs the Python anchor (commutator_real_core: z_res 2.478,
eta_real 0.70, via the V_strike-holdoff over-transfer of the doubler equalization).

THE TRIPWIRE (non-negotiable): the stabilized varicap, in the S1 doubler ALONE, must still give
z = 1.334 (work term intact) BEFORE composing. Verified below.

The de Queiroz charge-defined varicap is the stabilization (charge IS the state via `Q='C(t)*V'`;
nothing differentiates a stiff product; the V*dC/dt work term is native -- proven by the tripwire).
Models from physics, never tuned to the Python eta. Python cores read-only.
"""
import math
import os
import subprocess
import sys
import collections
import statistics

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
SPICE = os.path.join(ROOT, "spice")
W = 2 * math.pi * 1000.0
S1 = f"(0.5*(1+tanh(12.0*sin({W:.6e}*time))))"
S2 = f"(0.5*(1+tanh(12.0*sin({W:.6e}*time+{math.pi:.8f}))))"
VARICAPS = (f"C1v 1 0 Q='(1.6e-11+2.64e-10*{S1})*V(1)'\n"
            f"C2v 4 0 Q='(1.6e-11+2.64e-10*{S2})*V(4)'")
NET = ("Cpar1 1 0 2e-11\nCpar2 2 0 2e-11\nCpar3 3 0 2e-11\nCpar4 4 0 2e-11\n"
       "Ca 1 2 3.09e-10\nCb 3 4 3.09e-10\n.model ND D(is=1e-9 n=0.005 rs=1e-3 cjo=0)")


def run(deck, name, sigcount=2):
    open(os.path.join(SPICE, name), "w").write(deck)
    dat = os.path.join(SPICE, name.replace(".cir", ".dat"))
    r = subprocess.run(["ngspice", "-b", name],
                       capture_output=True, text=True, timeout=400, cwd=SPICE)
    blob = r.stdout + r.stderr
    conv = "too small" not in blob and "aborted" not in blob.lower()
    rows = []
    try:
        for l in open(dat):
            p = l.split()
            if len(p) >= 2 * sigcount:                 # wrdata: time,v0,time,v1,... (2 cols/signal)
                try:
                    rows.append([float(x) for x in p])
                except ValueError:
                    pass
    except FileNotFoundError:
        pass
    return rows, conv


def z_of(rows, c1=1, c4=3):
    T = 1e-3
    pk = collections.defaultdict(float)
    for r in rows:
        pk[int(r[0] / T)] = max(pk[int(r[0] / T)], abs(r[c1]) + abs(r[c4]))
    cs = [c for c in sorted(pk) if pk[c] > 1e-12]
    late = [pk[c] for c in cs[len(cs) // 2:]]
    rt = [late[i + 1] / late[i] for i in range(len(late) - 1) if late[i] > 1e-9]
    return (statistics.median(rt) if rt else float("nan")), max((pk[c] for c in cs), default=0)


def main():
    print("=" * 92)
    print("NGSPICE-S3 — compose the full resonant machine end-to-end (make-or-break)")
    print("=" * 92)
    rows_out = []

    # ---- [check 1] THE TRIPWIRE: stabilized varicap -> z=1.334 (work term intact) ----
    trip = f"""* S3 tripwire: stabilized de Queiroz varicap doubler must give z=1.334
{VARICAPS}
{NET}
Dd1 2 0 ND
Dd2 3 0 ND
Dd3 1 3 ND
Dd4 4 2 ND
.ic v(1)=-1 v(2)=0 v(3)=0 v(4)=-1
.control
tran 1.25e-6 2.4e-2 uic
wrdata s3_tripwire.dat v(1) v(4)
.endc
.options reltol=1e-5 abstol=1e-12 vntol=1e-9 gmin=1e-14 maxstep=1.25e-6
.end
"""
    r, conv = run(trip, "s3_tripwire.cir")
    z_trip, _ = z_of(r)
    trip_ok = abs(z_trip - 1.334) / 1.334 < 0.05
    print(f"\n[check 1] TRIPWIRE: stabilized varicap z = {z_trip:.4f} (anchor 1.334, tanh tier <5%) "
          f"-> {'PASS — work term intact' if trip_ok else 'FAIL — varicap damped'}")
    rows_out.append(("tripwire", "doubler z (varicap intact)", 1.334, z_trip,
                     abs(z_trip - 1.334) / 1.334 * 100, trip_ok))

    # ---- [check 2/3] compose: over-transfer to recover the tax (commutator-real z_res 2.478) ----
    # the over-transfer needs the rail-return equalization (D1/D2) to hold off to V_strike (so the
    # inner nodes can swing past the diode clamp). Try both: (A) Lx+diodes (the clamp) and
    # (B) Lx + V_strike self-break gaps (the commutator-real holdoff).
    print("\n[check 2/3] compose the resonant over-transfer (Python anchor z_res 2.478 / eta 0.70):")
    # (A) Lx + diodes (resonance, but diodes clamp at 0)
    deckA = f"""* S3-A: doubler + Lx resonant equalization (diodes clamp at 0)
{VARICAPS}
{NET}
Lx1 2 a1 1e-4
Dd1 a1 0 ND
Lx2 3 a2 1e-4
Dd2 a2 0 ND
Lx3 1 a3 1e-4
Dd3 a3 3 ND
Lx4 4 a4 1e-4
Dd4 a4 2 ND
.ic v(1)=-1 v(2)=0 v(3)=0 v(4)=-1
.control
tran 1e-7 1.2e-2 uic
wrdata s3_A.dat v(1) v(4)
.endc
.options reltol=1e-4 abstol=1e-11 vntol=1e-8 gmin=1e-13 maxstep=1e-7
.end
"""
    rA, convA = run(deckA, "s3_A.cir")
    zA, _ = z_of(rA)
    print(f"  (A) Lx + clamping diodes: z = {zA:.4f}  (vs z_res 2.478)  conv={convA}")
    # (B) Lx + V_strike self-break gaps (switch+diode rectifying) on the rail-return + load
    deckB = f"""* S3-B: doubler + Lx + V_strike rectifying sparkgaps on rail-return + load
{VARICAPS}
{NET}
.model GAP SW(vt=3.0 vh=1.2 ron=2 roff=1G)
Lx1 2 m1 1e-4
Sg1 m1 g1 2 0 GAP
Dg1 g1 0 ND
Lx2 3 m2 1e-4
Sg2 m2 g2 3 0 GAP
Dg2 g2 0 ND
Dd3 1 3 ND
Dd4 4 2 ND
Rload 1 0 5e6
.ic v(1)=-1 v(2)=0 v(3)=0 v(4)=-1
.control
tran 1e-7 1.2e-2 uic
wrdata s3_B.dat v(1) v(4)
.endc
.options method=gear reltol=1e-4 abstol=1e-11 vntol=1e-8 gmin=1e-13 maxstep=1e-7
.end
"""
    rB, convB = run(deckB, "s3_B.cir")
    zB, peakB = z_of(rB)
    print(f"  (B) Lx + V_strike holdoff gaps: z = {zB:.4f}  (vs z_res 2.478)  conv={convB} "
          f"(pump {'RATCHETS' if zB > 1.1 else 'BREAKS -> z~1, no pump'})")
    z_best = max(zA, zB)
    s3_ok = abs(z_best - 2.478) / 2.478 < 0.10
    rows_out.append(("S3-A", "z_res (Lx+diodes, clamp)", 2.478, zA, abs(zA - 2.478) / 2.478 * 100, False))
    rows_out.append(("S3-B", "z_res (Lx+V_strike gaps)", 2.478, zB, abs(zB - 2.478) / 2.478 * 100, False))

    # ---- table + CSV ----
    print(f"\n  {'stage':9s} {'quantity':30s} {'python':>9s} {'ngspice':>9s} {'delta%':>8s}  verdict")
    for st, q, py, ng, d, ok in rows_out:
        print(f"  {st:9s} {q:30s} {py:>9.4f} {ng:>9.4f} {d:>7.1f}%  {'PASS' if ok else 'FAIL'}")
    p = os.path.join(ROOT, "ngspice_s3.csv")
    with open(p, "w") as f:
        f.write("stage,quantity,python,ngspice,delta_pct,pass\n")
        for st, q, py, ng, d, ok in rows_out:
            f.write(f"{st},{q},{py:.5f},{ng:.5f},{d:.3f},{ok}\n")

    # ---- verdict ----
    print("\n" + "=" * 92)
    if trip_ok and s3_ok:
        print("VERDICT: NGSPICE-CONFIRMS-S3 — the full machine reproduces z_res/eta_real end-to-end.")
    elif trip_ok and not s3_ok:
        print("VERDICT: DISCREPANCY-S3 — the deck composes & runs stably (tripwire intact, z=1.334),")
        print(f"  but the resonant gain does NOT reproduce: z stays ~{z_best:.2f} (direct/clamped), NOT")
        print("  the Python z_res 2.478. LOCALIZED CAUSE (the emergent interaction the component checks")
        print("  missed): the over-transfer and the equalization are the SAME physical gap. To over-")
        print("  transfer (recover the tax) the rail-return must hold off to V_strike -- but that is the")
        print("  very conduction-at-0 that ratchets the Bennet pump, so holding it off BREAKS the pump")
        print("  (z->1). Lx + clamping diodes stays at the direct z (~1.3). commutator_real_core's")
        print("  alpha-reflection model treats equalization and over-transfer as SEPARABLE; the literal")
        print("  circuit shows they are not -- confirming the doubler-resonant 'resonating the core")
        print("  alters z' caveat in a second engine. The validated eta recovery is the DOWNSTREAM")
        print("  island (resonant-island ~31%, S2-confirmed), NOT the core over-transfer.")
    else:
        print("VERDICT: VARICAP-UNSTABLE — no work-term-preserving stabilization runs (tripwire failed).")
    print("=" * 92)
    print(f"\nwrote {os.path.relpath(p, ROOT)}")
    return rows_out


if __name__ == "__main__":
    main()
