# Makefile for sstate binary compilation


.PHONY: build clean install test help venv clean-venv

# Virtualenv settings
# VENV: location of virtualenv (default .venv)
# USE_VENV: if 1, Makefile will prefer the venv python for build/test (default 1)
VENV ?= .venv
USE_VENV ?= 1

ifeq ($(USE_VENV),1)
PYTHON := $(VENV)/bin/python
PIP := $(VENV)/bin/pip
export PATH := $(VENV)/bin:$(PATH)
else
PYTHON := python3
PIP := pip3
endif

# Default target
all: build

# If USE_VENV is enabled, ensure venv is created before building
ifneq ($(USE_VENV),0)
BUILD_DEPS = venv
else
BUILD_DEPS =
endif

# Create a virtualenv if missing and install requirements (if present)
venv:
	@if [ -d "$(VENV)" ]; then \
		echo "Virtualenv already exists at $(VENV)"; \
	else \
		echo "Creating virtualenv at $(VENV) (using system python3)..."; \
		python3 -m venv $(VENV); \
	fi
	@$(PIP) install --upgrade pip setuptools wheel || true
	@if [ -f requirements.txt ]; then \
		echo "Installing Python dependencies from requirements.txt..."; \
		$(PIP) install -r requirements.txt; \
	fi
	@echo "Virtualenv ready at $(VENV). Use: export PYTHON=$(VENV)/bin/python"

# Sync dependencies into an existing virtualenv (does not create it)
venv-sync:
	@if [ ! -d "$(VENV)" ]; then \
		echo "No virtualenv at $(VENV). Run 'make venv' first."; \
		exit 1; \
	fi
	@$(PIP) install --upgrade pip setuptools wheel || true
	@if [ -f requirements.txt ]; then \
		echo "Installing Python dependencies from requirements.txt..."; \
		$(PIP) install -r requirements.txt; \
	fi

# Build the binary
build: $(BUILD_DEPS)
	@if [ "$(USE_VENV)" = "1" ]; then \
		if [ ! -x "$(VENV)/bin/python" ]; then \
			echo "Error: Virtualenv not found at $(VENV). Run 'make venv' first."; \
			exit 1; \
		fi; \
		if ! $(VENV)/bin/python -m pip show pyinstaller >/dev/null 2>&1; then \
			echo "Error: PyInstaller not installed in venv. Run 'make venv' or 'make venv-sync'."; \
			exit 1; \
		fi; \
	fi
	@echo "Building sstate binary..."
	@$(PYTHON) build.py

# Clean build artifacts (does not remove virtualenv by default)
clean:
	@echo "Cleaning build artifacts..."
	@$(PYTHON) build.py clean || true
	@echo "Removed build artifacts (if any)."

# Remove the virtualenv
clean-venv:
	@echo "Removing virtualenv at $(VENV)..."
	@rm -rf $(VENV)
	@echo "Virtualenv removed."

# Clean everything
clean-all: clean clean-venv
	@echo "Cleaned all build artifacts and virtualenv."

# Install the binary to /usr/local/bin (requires sudo)
install: build
	@echo "Installing sstate to /usr/local/bin..."
	@sudo cp ./dist/sstate /usr/local/bin/sstate
	@sudo chmod +x /usr/local/bin/sstate
	@echo "Installation complete! You can now run 'sstate' from anywhere."

# Test the binary
test: build
	@echo "Testing the binary..."
	@./dist/sstate --help

# Show help
help:
	@echo "Available targets:"
	@echo "  venv        - Create a Python virtualenv at $(VENV) if missing and install requirements.txt"
	@echo "  venv-sync   - Install/upgrade requirements into existing virtualenv (no recreate)"
	@echo "  build       - Build the sstate binary (depends on venv when USE_VENV=1)"
	@echo "  clean       - Clean build artifacts (keeps the virtualenv)"
	@echo "  clean-venv  - Remove the virtualenv directory ($(VENV))"
	@echo "  install     - Install binary to /usr/local/bin (requires sudo)"
	@echo "  test        - Test the built binary"
	@echo "Environment variables you can set:"
	@echo "  USE_VENV=0  - disable automatic venv usage for build/test (default 1)"
	@echo "  VENV=...    - path to virtualenv directory (default .venv)"
	@echo "  PYTHON=...  - override python interpreter to use"
