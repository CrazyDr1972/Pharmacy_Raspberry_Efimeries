#!/bin/sh

set -eu

cd /home/niklyk1/pharmacy-display
/home/niklyk1/pharmacy-display/.venv/bin/python -m app.refresh_pdf
exec /home/niklyk1/pharmacy-display/.venv/bin/python /home/niklyk1/pharmacy-display/scripts/generate_data.py
