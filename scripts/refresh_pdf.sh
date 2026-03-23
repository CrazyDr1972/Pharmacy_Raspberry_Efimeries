#!/bin/sh

set -eu

cd /home/niklyk1/pharmacy-display
PYTHON_BIN="/home/niklyk1/pharmacy-display/.venv/bin/python"

if [ ! -x "$PYTHON_BIN" ]; then
  echo "Missing Python virtualenv interpreter at $PYTHON_BIN" >&2
  exit 1
fi

"$PYTHON_BIN" -m app.refresh_pdf
exec "$PYTHON_BIN" /home/niklyk1/pharmacy-display/scripts/generate_data.py
