#!/bin/sh

set -eu

PROFILE_DIR="/home/niklyk1/pharmacy-display/.chromium-profile"
VIEWER_URL="file:///home/niklyk1/pharmacy-display/viewer/index.html"

mkdir -p "$PROFILE_DIR"

if [ -z "${DISPLAY:-}" ] && [ -S /tmp/.X11-unix/X0 ]; then
  export DISPLAY=:0
fi

if [ -z "${XAUTHORITY:-}" ] && [ -f /home/niklyk1/.Xauthority ]; then
  export XAUTHORITY=/home/niklyk1/.Xauthority
fi

if [ -z "${DISPLAY:-}" ] && [ -z "${WAYLAND_DISPLAY:-}" ]; then
  echo "No active GUI session found. Start the Raspberry Pi desktop first, or let autostart launch the kiosk after login." >&2
  exit 1
fi

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

if [ -n "${DISPLAY:-}" ] && command -v xdotool >/dev/null 2>&1; then
  sleep 3
  WINDOW_ID="$(DISPLAY="$DISPLAY" XAUTHORITY="${XAUTHORITY:-}" xdotool search --sync --onlyvisible --class chromium 2>/dev/null | tail -n 1 || true)"
  if [ -n "$WINDOW_ID" ]; then
    DISPLAY="$DISPLAY" XAUTHORITY="${XAUTHORITY:-}" xdotool windowactivate "$WINDOW_ID" 2>/dev/null || true
    DISPLAY="$DISPLAY" XAUTHORITY="${XAUTHORITY:-}" xdotool key --window "$WINDOW_ID" F11 2>/dev/null || true
  fi
fi

wait "$CHROMIUM_PID"
