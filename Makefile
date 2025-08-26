# Makefile for sstate binary compilation

.PHONY: build clean install test help

# Python command (adjust if needed for your environment)
PYTHON = conda run --name sstate python

# Default target
all: build

# Build the binary
build:
	@echo "Building sstate binary..."
	@$(PYTHON) build.py

# Clean build artifacts
clean:
	@echo "Cleaning build artifacts..."
	@$(PYTHON) build.py clean

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
	@echo "  build    - Build the sstate binary"
	@echo "  clean    - Clean build artifacts"
	@echo "  install  - Install binary to /usr/local/bin (requires sudo)"
	@echo "  test     - Test the built binary"
	@echo "  help     - Show this help message"
