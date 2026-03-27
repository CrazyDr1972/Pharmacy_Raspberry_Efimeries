#!/bin/sh

set -eu

SCRIPT_DIR="$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)"
PROJECT_DIR="$(CDPATH= cd -- "$SCRIPT_DIR/.." && pwd)"
LOG_DIR="$PROJECT_DIR/logs"
BOOT_LOG="$LOG_DIR/kiosk-startup.log"
REFRESH_SCRIPT="$PROJECT_DIR/scripts/refresh_pdf.sh"
LAUNCH_SCRIPT="$PROJECT_DIR/scripts/launch_kiosk.sh"
RETRY_INTERVAL_SEC=180

cd "$PROJECT_DIR"
mkdir -p "$LOG_DIR"

timestamp() {
  date '+%Y-%m-%d %H:%M:%S'
}

log() {
  printf '%s %s\n' "$(timestamp)" "$1" >>"$BOOT_LOG"
}

log "boot wrapper start"

if [ ! -x "$REFRESH_SCRIPT" ]; then
  log "missing refresh script at $REFRESH_SCRIPT"
fi

if command -v pkill >/dev/null 2>&1; then
  log "stopping existing chromium instances if any"
  pkill -f '/usr/bin/chromium' >/dev/null 2>&1 || true
  sleep 2
fi

run_refresh() {
  reason="$1"
  log "refresh start ($reason)"
  if "$REFRESH_SCRIPT" >/tmp/pharmacy-display-refresh.log 2>&1; then
    log "refresh finished ($reason)"
    return 0
  fi

  log "refresh failed ($reason), see /tmp/pharmacy-display-refresh.log"
  return 1
}

run_refresh_with_retry() {
  reason="$1"
  while ! run_refresh "$reason"; do
    log "refresh retry in ${RETRY_INTERVAL_SEC}s ($reason)"
    sleep "$RETRY_INTERVAL_SEC"
  done
}

(
  run_refresh_with_retry "boot"

  tracked_date="$(date +%F)"
  while true; do
    sleep 30
    current_date="$(date +%F)"
    if [ "$current_date" != "$tracked_date" ]; then
      run_refresh_with_retry "day-change $tracked_date -> $current_date"
      tracked_date="$current_date"
    fi
  done
) &
log "refresh controller started (boot + day-change, retry=${RETRY_INTERVAL_SEC}s)"

sleep 8
log "launching kiosk viewer"
exec "$LAUNCH_SCRIPT"
