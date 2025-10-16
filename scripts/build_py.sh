#!/usr/bin/env bash
set -euo pipefail

PROJECT_DIR=$(cd "$(dirname "$0")/.." && pwd)
cd "$PROJECT_DIR"

# Ensure venv exists
if [ ! -x .venv/bin/python3 ]; then
  python3 -m venv .venv
fi

source .venv/bin/activate

# Install build deps
python -m pip install --upgrade pip
pip install pyinstaller -r requirements.txt

# Output directory
OUT_DIR="python_dist"
rm -rf "$OUT_DIR"
mkdir -p "$OUT_DIR"

# Build helpers
pyinstaller --onefile python_tools/test_connection.py \
  --name test_connection \
  --distpath "$OUT_DIR"

pyinstaller --onefile python_tools/run_import.py \
  --name run_import \
  --distpath "$OUT_DIR" \
  --add-data "src:src" \
  --add-data "bundled_tools:bundled_tools" \
  --hidden-import rich \
  --hidden-import notion_client \
  --hidden-import beautifulsoup4 \
  --hidden-import lxml \
  --hidden-import flask \
  --hidden-import requests \
  --hidden-import python-dotenv

# Show results
ls -lh "$OUT_DIR"
