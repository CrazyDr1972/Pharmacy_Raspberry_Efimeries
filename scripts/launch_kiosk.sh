#!/bin/sh

set -eu

SCRIPT_DIR="$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)"
PROJECT_DIR="$(CDPATH= cd -- "$SCRIPT_DIR/.." && pwd)"
PROFILE_DIR="$PROJECT_DIR/.chromium-profile"
VIEWER_URL="file://$PROJECT_DIR/viewer/index.html"
LOG_FILE="$PROJECT_DIR/logs/kiosk-launch.log"

mkdir -p "$PROFILE_DIR"
mkdir -p "$PROJECT_DIR/logs"

timestamp() {
  date '+%Y-%m-%d %H:%M:%S'
}

log() {
  printf '%s %s\n' "$(timestamp)" "$1" >>"$LOG_FILE"
}

log "launch script start"

if [ -z "${DISPLAY:-}" ] && [ -S /tmp/.X11-unix/X0 ]; then
  export DISPLAY=:0
fi

if [ -z "${XAUTHORITY:-}" ] && [ -f "$HOME/.Xauthority" ]; then
  export XAUTHORITY="$HOME/.Xauthority"
fi

if [ -z "${DISPLAY:-}" ] && [ -z "${WAYLAND_DISPLAY:-}" ]; then
  log "no GUI session found"
  echo "No active GUI session found. Start the Raspberry Pi desktop first, or let autostart launch the kiosk after login." >&2
  exit 1
fi

log "using DISPLAY=${DISPLAY:-} WAYLAND_DISPLAY=${WAYLAND_DISPLAY:-} XAUTHORITY=${XAUTHORITY:-}"

/usr/bin/chromium \
  --kiosk \
  --start-fullscreen \
  --start-maximized \
  --allow-file-access-from-files \
  --user-data-dir="$PROFILE_DIR" \
  --password-store=basic \
  --use-mock-keychain \
  --no-first-run \
  --noerrdialogs \
  --disable-session-crashed-bubble \
  --disable-infobars \
  --check-for-update-interval=31536000 \
  --app="$VIEWER_URL" &

CHROMIUM_PID=$!
log "chromium started pid=$CHROMIUM_PID"

if [ -n "${DISPLAY:-}" ] && command -v xdotool >/dev/null 2>&1; then
  sleep 3
  WINDOW_ID="$(DISPLAY="$DISPLAY" XAUTHORITY="${XAUTHORITY:-}" xdotool search --sync --onlyvisible --class chromium 2>/dev/null | tail -n 1 || true)"
  if [ -n "$WINDOW_ID" ]; then
    DISPLAY="$DISPLAY" XAUTHORITY="${XAUTHORITY:-}" xdotool windowactivate "$WINDOW_ID" 2>/dev/null || true
    DISPLAY="$DISPLAY" XAUTHORITY="${XAUTHORITY:-}" xdotool key --window "$WINDOW_ID" F11 2>/dev/null || true
  fi
fi

if wait "$CHROMIUM_PID"; then
  EXIT_CODE=0
else
  EXIT_CODE=$?
fi
log "chromium exited code=$EXIT_CODE"
exit "$EXIT_CODE"
