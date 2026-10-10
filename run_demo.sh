#!/usr/bin/env bash
# ==============================================================================
# pymanager — Automated Reproduction Demo Script
# ==============================================================================
# This script sets up a fresh virtual environment, installs pymanager,
# enables the auto-compatibility hook, and runs the multi-version demo.
# ==============================================================================

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo "=================================================================="
echo "  🚀 pymanager — Multi-Version Python Environment Demo"
echo "=================================================================="

# 1. Check Python version
PYTHON_BIN="${PYTHON:-python3}"
if ! command -v "$PYTHON_BIN" &>/dev/null; then
    echo "❌ Error: Python 3 not found in PATH. Please install Python 3.8+."
    exit 1
fi

PY_VERSION=$("$PYTHON_BIN" --version)
echo "• Using host interpreter: $PY_VERSION"

# 2. Create fresh virtual environment if not already present
DEMO_VENV="$SCRIPT_DIR/.demo_venv"
if [ ! -d "$DEMO_VENV" ]; then
    echo "• Creating fresh virtual environment at .demo_venv..."
    "$PYTHON_BIN" -m venv "$DEMO_VENV"
fi

VENV_PYTHON="$DEMO_VENV/bin/python"
VENV_PIP="$DEMO_VENV/bin/pip"

# 3. Install pymanager into the environment
echo "• Installing pymanager into virtual environment..."
"$VENV_PIP" install -q -e .

# 4. Install native dependencies (requests, click)
echo "• Installing native dependencies..."
"$VENV_PIP" install -q requests click

# 5. Enable the under-the-hood auto-compatibility hook
echo "• Enabling auto-compatibility hook in virtual environment..."
"$VENV_PYTHON" -m pymanager enable --venv "$DEMO_VENV"

# 6. Copy requirements to demo root for discovery
cp examples/requirements.txt "$DEMO_VENV/requirements.txt"

# 7. Run the demo script
echo "• Executing examples/multi_version_demo.py..."
echo "=================================================================="
"$VENV_PYTHON" examples/multi_version_demo.py
