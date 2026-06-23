#!/usr/bin/env bash
# run_s3.sh — the S3 end-to-end composition driver (tripwire -> compose -> measure).
# The Python comparison + the make-or-break verdict is in sim/ngspice_s3.py.
set -e
cd "$(dirname "$0")"
echo "ngspice:"; ngspice --version 2>/dev/null | head -1
for cir in s3_tripwire.cir s3_A.cir s3_B.cir; do
  [ -f "$cir" ] && { echo "=== $cir ==="; ngspice -b "$cir" 2>&1 | grep -iE "error|too small" | head -3; }
done
echo "full S3 verdict:  python3 ../sim/ngspice_s3.py"
