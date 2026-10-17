# DCCREG_turbine -- developer make targets.
# [numpy-pyodide-compat] The live cores are validated on the CLI numpy (2.x) but RUN in-browser
# on Pyodide 0.26.2's numpy (1.26.4). `pyodide-parity` runs every HTML-loaded live core + the
# dual canary under BOTH numpys so a version-fragile name (the trapz<->trapezoid class) is caught
# here, not by a user staring at `SOLVER: down`.

PARITY_VENV := .pyodide-parity
PARITY_NUMPY := numpy==1.26.4   # Pyodide 0.26.2 pyodide-lock.json bundle
# A venv keeps its interpreter in bin/ on POSIX and in Scripts/ on Windows.
ifeq ($(OS),Windows_NT)
PARITY_PY := $(PARITY_VENV)/Scripts/python.exe
else
PARITY_PY := $(PARITY_VENV)/bin/python
endif

.PHONY: pyodide-parity pyodide-parity-venv

# Run the standing parity check under both numpy 1.26 (Pyodide proxy) and the CLI numpy.
pyodide-parity: $(PARITY_PY)
	bash sim/run_pyodide_parity.sh

# Create the numpy-1.26 parity venv (the local Pyodide-numpy proxy) if it is missing.
$(PARITY_PY):
	python3 -m venv $(PARITY_VENV)
	$(PARITY_PY) -m pip install --quiet --upgrade pip
	$(PARITY_PY) -m pip install --quiet '$(PARITY_NUMPY)'

pyodide-parity-venv: $(PARITY_PY)
	@$(PARITY_PY) -c "import numpy; print('parity venv numpy', numpy.__version__)"
