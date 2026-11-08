#!/usr/bin/env bash
#
# stop.sh - Free the app ports and stop avahi. Shared by start.sh.
#
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

BACKEND_PORT="${BACKEND_PORT:-8000}"
FRONTEND_PORT="${FRONTEND_PORT:-5173}"
READER_PORT="${READER_PORT:-5174}"
LAN_NAME="${LAN_NAME:-read.local}"

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

free_port() {
    local port="$1" label="$2"
    local pids
    pids="$(listen_pids "$port")"
    if [[ -z "$pids" ]]; then
        return 0
    fi
    echo "Stopping $label on :$port"
    # shellcheck disable=SC2086
    kill $pids 2>/dev/null || true
    for _ in $(seq 1 25); do
        [[ -z "$(listen_pids "$port")" ]] && return 0
        sleep 0.2
    done
    pids="$(listen_pids "$port")"
    if [[ -n "$pids" ]]; then
        # shellcheck disable=SC2086
        kill -9 $pids 2>/dev/null || true
        sleep 0.2
    fi
}

free_port "$BACKEND_PORT" "backend"
free_port "$FRONTEND_PORT" "translator"
free_port "$READER_PORT" "reader"

# npm wrappers can outlive the listener; they do not hold the port.
pkill -f "npm run dev -- --port ${FRONTEND_PORT}" 2>/dev/null || true
pkill -f "npm run reader -- --port ${READER_PORT}" 2>/dev/null || true
pkill -f "avahi-publish -a -R ${LAN_NAME}" 2>/dev/null || true

rm -f .backend.pid .frontend.pid .reader.pid .avahi.pid

echo "Stopped."
