#!/usr/bin/env bash
#
# start.sh - Stop whatever is on the app ports, then start backend +
# translator + reader.
#
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

VENV_DIR=".venv"
BACKEND_LOG="logs/backend.log"
FRONTEND_LOG="logs/frontend.log"
READER_LOG="logs/reader.log"
AVAHI_LOG="logs/avahi.log"
BACKEND_PORT="${BACKEND_PORT:-8000}"
FRONTEND_PORT="${FRONTEND_PORT:-5173}"
READER_PORT="${READER_PORT:-5174}"
LAN_NAME="${LAN_NAME:-read.local}"

echo "=== DeepSeek Translator launcher ==="

if [[ ! -d "$VENV_DIR" ]]; then
    echo "ERROR: venv '$VENV_DIR' not found. Run ./install.sh first." >&2
    exit 1
fi
if ! [[ -d frontend/node_modules ]]; then
    echo "ERROR: frontend/node_modules not found. Run ./install.sh first." >&2
    exit 1
fi

mkdir -p logs

bash "$SCRIPT_DIR/stop.sh"

# Stale Vite optimize cache is what 504 "Outdated Optimize Dep" is.
rm -rf frontend/node_modules/.vite

listen_pids() {
    local port="$1"
    if command -v lsof >/dev/null 2>&1; then
        lsof -t -iTCP:"$port" -sTCP:LISTEN 2>/dev/null || true
        return
    fi
    ss -lptn "sport = :$port" 2>/dev/null \
        | sed -n 's/.*pid=\([0-9][0-9]*\).*/\1/p' \
        | sort -u
}

wait_listen() {
    local port="$1" name="$2" log="$3"
    for _ in $(seq 1 50); do
        if [[ -n "$(listen_pids "$port")" ]]; then
            return 0
        fi
        sleep 0.1
    done
    echo "ERROR: $name did not bind :$port. Check $log." >&2
    exit 1
}

lan_ip() {
    ip -4 route get 1.1.1.1 2>/dev/null | awk '{for (i=1;i<=NF;i++) if ($i=="src") {print $(i+1); exit}}' \
        || hostname -I 2>/dev/null | awk '{print $1}' \
        || true
}

echo "Starting backend (uvicorn, port $BACKEND_PORT)..."
nohup "$VENV_DIR/bin/uvicorn" backend.main:app \
    --host 0.0.0.0 --port "$BACKEND_PORT" \
    > "$BACKEND_LOG" 2>&1 &

echo "Starting frontend (vite, port $FRONTEND_PORT)..."
cd frontend
nohup ./node_modules/.bin/vite --port "$FRONTEND_PORT" \
    > "$SCRIPT_DIR/$FRONTEND_LOG" 2>&1 &
cd "$SCRIPT_DIR"

echo "Starting reader (vite, port $READER_PORT, LAN)..."
cd frontend
nohup ./node_modules/.bin/vite --config vite.reader.config.ts --host --port "$READER_PORT" \
    > "$SCRIPT_DIR/$READER_LOG" 2>&1 &
cd "$SCRIPT_DIR"

wait_listen "$BACKEND_PORT" "backend" "$BACKEND_LOG"
wait_listen "$FRONTEND_PORT" "translator" "$FRONTEND_LOG"
wait_listen "$READER_PORT" "reader" "$READER_LOG"

LAN_IP="$(lan_ip)"
if command -v avahi-publish >/dev/null 2>&1 && [[ -n "$LAN_IP" ]]; then
    if ! systemctl is-active --quiet avahi-daemon 2>/dev/null; then
        sudo systemctl start avahi-daemon 2>/dev/null || true
    fi
    nohup avahi-publish -a -R "$LAN_NAME" "$LAN_IP" > "$AVAHI_LOG" 2>&1 &
    echo "Published $LAN_NAME -> $LAN_IP"
elif [[ -z "$LAN_IP" ]]; then
    echo "WARNING: could not detect LAN IP; $LAN_NAME was not published."
else
    echo "WARNING: avahi-publish not found. Install avahi-utils for $LAN_NAME."
fi

echo
echo "Started."
echo "  Translator: http://localhost:$FRONTEND_PORT"
echo "  Reader:     http://$LAN_NAME:$READER_PORT"
echo "  Backend:    http://localhost:$BACKEND_PORT/api/health"
echo "  Logs:       $BACKEND_LOG , $FRONTEND_LOG , $READER_LOG"
echo "Stop with: ./stop.sh"
