# sstate
sstate is a rewrite of a perl-based utility in Python, which will give the current resource state of any Slurm-based HPC cluster with color-coded output for easy visual identification.

## Features
- Color-coded node states for quick visual identification:
  - 🟡 **Mixed** = Yellow
  - 🔴 **Allocated** = Red  
  - 🟢 **Idle** = Green
  - 🔴 **Down/Drain/Fail** = Bright Red
  - 🔵 **Other states** = Cyan
- Detailed resource usage statistics (CPU, Memory)
- Partition filtering support

## Requirements
- Python 3.7+
- tabulate library (for table formatting)
- colorama library (for colored output)

## Installation and Usage

### Method 1: Running as Python script

Install dependencies and run directly:

```bash
pip3 install -r requirements.txt
python sstate.py
```

### Method 2: Building a standalone binary (Recommended)

Build a single executable that doesn't require Python or dependencies to be installed on the target system.

#### Prerequisites

```bash
pip3 install pyinstaller
```

#### Build the binary

Using the provided build script:

```bash
python build.py
```

Or using make:

```bash
make build
```

The binary will be created at `./dist/sstate`

#### Install system-wide (optional)

```bash
make install
```

This will copy the binary to `/usr/local/bin/sstate` so you can run it from anywhere.

#### Clean build artifacts

```bash
make clean
```

### Usage Examples

```bash
# Query all nodes
./dist/sstate

# Query specific partition
./dist/sstate -p compute

# Show help
./dist/sstate --help
```
