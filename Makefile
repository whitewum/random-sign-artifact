PYTHON ?= python3
export GOCACHE := $(CURDIR)/.cache/go-build
export MPLCONFIGDIR := $(CURDIR)/.cache/matplotlib

.PHONY: build test smoke figures audit
build:
	$(PYTHON) scripts/artifact.py build
test: build
	cd sim/iblt2r && go test ./...
	cd sim/peelsim && go test ./...
	bin/peelsim -selftest
	cd sim/peelsim && $(PYTHON) -m unittest -q test_distribution
smoke: build
	$(PYTHON) scripts/artifact.py smoke
figures:
	$(PYTHON) scripts/artifact.py figures
audit:
	$(PYTHON) scripts/audit.py
