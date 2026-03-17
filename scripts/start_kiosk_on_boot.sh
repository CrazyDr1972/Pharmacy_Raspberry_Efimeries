#!/bin/sh

set -eu

PROJECT_DIR="/home/niklyk1/pharmacy-display"
LOG_DIR="$PROJECT_DIR/logs"
BOOT_LOG="$LOG_DIR/kiosk-startup.log"
PYTHON_BIN="$PROJECT_DIR/.venv/bin/python"
GENERATOR_SCRIPT="$PROJECT_DIR/scripts/generate_data.py"
REFRESH_SCRIPT="$PROJECT_DIR/scripts/refresh_pdf.sh"
LAUNCH_SCRIPT="$PROJECT_DIR/scripts/launch_kiosk.sh"
LATEST_PDF="$PROJECT_DIR/data/latest.pdf"
VIEWER_JSON="$PROJECT_DIR/data/viewer_data.json"

cd "$PROJECT_DIR"
mkdir -p "$LOG_DIR"

timestamp() {
  date '+%Y-%m-%d %H:%M:%S'
}

log() {
  printf '%s %s\n' "$(timestamp)" "$1" >>"$BOOT_LOG"
}

log "boot wrapper start"

if [ ! -f "$VIEWER_JSON" ] && [ -f "$LATEST_PDF" ]; then
  log "viewer_data.json missing, generating from latest.pdf"
  "$PYTHON_BIN" "$GENERATOR_SCRIPT" >/tmp/pharmacy-display-generate.log 2>&1 || true
fi

if command -v pkill >/dev/null 2>&1; then
  log "stopping existing chromium instances if any"
  pkill -f '/usr/bin/chromium' >/dev/null 2>&1 || true
  sleep 2
fi

(
  sleep 10
  log "background refresh start"
  "$REFRESH_SCRIPT" >/tmp/pharmacy-display-refresh.log 2>&1 || true
  log "background refresh finished"
) &

sleep 8
log "launching kiosk viewer"
exec "$LAUNCH_SCRIPT"
