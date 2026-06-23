#!/usr/bin/env bash
# sim/run_pyodide_parity.sh -- the standing Pyodide-numpy parity check.
# ====================================================================
# Runs sim/pyodide_parity.py under BOTH the numpy-1.26 parity venv (the local proxy for
# Pyodide 0.26.2's numpy) AND the CLI numpy (2.x). Both must be ALL GREEN for the in-browser
# load to be guaranteed numpy-wise. Emits numpy_parity.txt (the two-version pass table).
# [numpy-pyodide-compat] [ME]
#
#   make pyodide-parity        # preferred entry point
#   bash sim/run_pyodide_parity.sh
#
# Pinned parity target: numpy 1.26.4 (Pyodide 0.26.2's pyodide-lock.json bundle).
set -uo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"
PARITY_PY="$ROOT/.pyodide-parity/bin/python"
OUT="$ROOT/numpy_parity.txt"

if [[ ! -x "$PARITY_PY" ]]; then
  echo "ERROR: parity venv missing at $PARITY_PY" >&2
  echo "  create it:  python3 -m venv .pyodide-parity && .pyodide-parity/bin/pip install 'numpy==1.26.4'" >&2
  exit 2
fi

{
  echo "numpy_parity.txt -- the two-version Pyodide-numpy pass table  [numpy-pyodide-compat]"
  echo "generated: $(date -u +%Y-%m-%dT%H:%M:%SZ)  by sim/run_pyodide_parity.sh"
  echo "parity target: numpy 1.26.4 (Pyodide 0.26.2 bundle)  |  CLI: $(python3 -V 2>&1)"
  echo
} > "$OUT"

rc_total=0

echo "########################################################################" | tee -a "$OUT"
echo "## A. PARITY VENV  (.pyodide-parity, numpy 1.26.4 -- the Pyodide proxy) ##" | tee -a "$OUT"
echo "########################################################################" | tee -a "$OUT"
"$PARITY_PY" "$ROOT/sim/pyodide_parity.py" 2>&1 | tee -a "$OUT"
rc_parity=${PIPESTATUS[0]}
[[ $rc_parity -ne 0 ]] && rc_total=1

echo | tee -a "$OUT"
echo "########################################################################" | tee -a "$OUT"
echo "## B. CLI numpy  (the validation environment, numpy 2.x)              ##" | tee -a "$OUT"
echo "########################################################################" | tee -a "$OUT"
python3 "$ROOT/sim/pyodide_parity.py" 2>&1 | tee -a "$OUT"
rc_cli=${PIPESTATUS[0]}
[[ $rc_cli -ne 0 ]] && rc_total=1

echo | tee -a "$OUT"
if [[ $rc_total -eq 0 ]]; then
  echo "VERDICT: NUMPY-COMPAT-CLEAN -- green under BOTH numpy 1.26 (Pyodide) and CLI 2.x." | tee -a "$OUT"
else
  echo "VERDICT: PARITY FAILURE -- parity rc=$rc_parity, cli rc=$rc_cli (see above)." | tee -a "$OUT"
fi
exit $rc_total
