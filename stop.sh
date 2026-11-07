#!/usr/bin/env bash
#
# stop.sh - Stop the background backend, translator frontend, and reader.
#
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

stop_pid_file() {
    local pid_file="$1" label="$2"
    if [[ -f "$pid_file" ]] && kill -0 "$(cat "$pid_file")" 2>/dev/null; then
        local pid
        pid="$(cat "$pid_file")"
        echo "Stopping $label (PID $pid)..."
        kill "$pid" 2>/dev/null || true
        for _ in $(seq 1 20); do
            kill -0 "$pid" 2>/dev/null || break
            sleep 0.5
        done
        kill -9 "$pid" 2>/dev/null || true
    fi
    rm -f "$pid_file"
}

# Also reclaim stale processes from previous runs that the PID file no longer
# tracks. Match by command line (not port) so we don't kill unrelated apps
# that happen to share a port, and still work if the port was changed.
kill_pattern() {
    local pattern="$1" label="$2" pids
    pids="$(pgrep -f "$pattern" 2>/dev/null || true)"
    if [[ -n "$pids" ]]; then
        # shellcheck disable=SC2086
        kill $pids 2>/dev/null || true
        sleep 1
        # shellcheck disable=SC2086
        kill -9 $pids 2>/dev/null || true
    fi
}

stop_pid_file ".backend.pid" "backend"
stop_pid_file ".frontend.pid" "frontend"
stop_pid_file ".reader.pid" "reader"
stop_pid_file ".avahi.pid" "avahi"
kill_pattern "uvicorn backend.main:app" "backend"
kill_pattern "vite.*--port ${FRONTEND_PORT:-5173}" "frontend"
kill_pattern "vite.reader.config" "reader"
kill_pattern "avahi-publish -a -R ${LAN_NAME:-read.local}" "avahi"

echo "Stopped."
