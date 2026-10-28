PYTHON ?= python3
GOTESTFLAGS ?=
export GOCACHE := $(CURDIR)/.cache/go-build
export MPLCONFIGDIR := $(CURDIR)/.cache/matplotlib

.PHONY: build test smoke figures tables check-tables audit
build:
	$(PYTHON) scripts/artifact.py build
test: build
	cd sim/iblt2r && go test $(GOTESTFLAGS) ./...
	cd sim/peelsim && go test ./...
	bin/peelsim -selftest
	cd sim/peelsim && $(PYTHON) -m unittest -q test_distribution
smoke: build
	$(PYTHON) scripts/artifact.py smoke
figures:
	$(PYTHON) scripts/artifact.py figures
tables:
	$(PYTHON) scripts/tables.py
check-tables: tables
	$(PYTHON) scripts/check_tables.py
audit:
	$(PYTHON) scripts/audit.py
