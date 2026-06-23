#!/usr/bin/env bash
# run_stages.sh — the staged ngspice .tran driver (S0 linear -> S1 varicap -> S2 resonant).
# Each stage is a milestone AND a localizer. The Python comparison + verdict is in
# sim/ngspice_validate.py (which writes these decks and parses the waveforms).
set -e
cd "$(dirname "$0")"
echo "ngspice version:"; ngspice --version 2>/dev/null | head -1
for cir in s0_tank.cir s1_varicap_attempt.cir s2_R2.cir s2_R20.cir s2_R100.cir; do
  echo "=== $cir ==="; ngspice -b "$cir" 2>&1 | grep -iE "thalf|vbank|vc |vf |error" | head
done
echo ""
echo "full staged comparison + verdict:  python3 ../sim/ngspice_validate.py"
