#!/bin/sh

set -eu

SCRIPT_DIR="$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)"
PROJECT_DIR="$(CDPATH= cd -- "$SCRIPT_DIR/.." && pwd)"
PYTHON_BIN="$PROJECT_DIR/.venv/bin/python"
MARKER_PATH="$PROJECT_DIR/data/viewer_refresh_marker.txt"

cd "$PROJECT_DIR"

if [ ! -x "$PYTHON_BIN" ]; then
  echo "Missing Python virtualenv interpreter at $PYTHON_BIN" >&2
  exit 1
fi

"$PYTHON_BIN" -m app.refresh_pdf
"$PYTHON_BIN" "$PROJECT_DIR/scripts/generate_data.py"
date -u '+%Y-%m-%dT%H:%M:%SZ' >"$MARKER_PATH"
