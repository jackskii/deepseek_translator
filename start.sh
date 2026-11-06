#!/usr/bin/env bash
#
# start.sh - Launch the DeepSeek Translator (backend + frontend) in the
# background. Restarts if already running so .env changes take effect.
#
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

VENV_DIR=".venv"
BACKEND_PID_FILE=".backend.pid"
FRONTEND_PID_FILE=".frontend.pid"
BACKEND_LOG="logs/backend.log"
FRONTEND_LOG="logs/frontend.log"
BACKEND_PORT="${BACKEND_PORT:-8000}"
FRONTEND_PORT="${FRONTEND_PORT:-5173}"

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

# --- Stop any existing instances --------------------------------------------
stop_pid_file() {
    local pid_file="$1"
    if [[ -f "$pid_file" ]] && kill -0 "$(cat "$pid_file")" 2>/dev/null; then
        local pid
        pid="$(cat "$pid_file")"
        echo "Stopping existing process (PID $pid)..."
        kill "$pid" 2>/dev/null || true
        for _ in $(seq 1 20); do
            kill -0 "$pid" 2>/dev/null || break
            sleep 0.5
        done
        kill -9 "$pid" 2>/dev/null || true
        sleep 0.5
    fi
    rm -f "$pid_file"
}

# Kill stale processes from previous runs that the PID file no longer tracks.
# We match by the exact command line (not by port), so:
#   * we never kill an unrelated app that happens to use the same port, and
#   * we still find our processes even if the port was changed via env vars.
kill_pattern() {
    local pattern="$1" label="$2"
    local pids
    pids="$(pgrep -f "$pattern" 2>/dev/null || true)"
    if [[ -n "$pids" ]]; then
        echo "Reclaiming stale $label (PIDs: $(echo $pids | tr '\n' ' '))..."
        # shellcheck disable=SC2086
        kill $pids 2>/dev/null || true
        for _ in $(seq 1 20); do
            pids="$(pgrep -f "$pattern" 2>/dev/null || true)"
            [[ -z "$pids" ]] && break
            sleep 0.5
        done
        # shellcheck disable=SC2086
        kill -9 $pids 2>/dev/null || true
        sleep 0.5
    fi
}

stop_pid_file "$BACKEND_PID_FILE"
stop_pid_file "$FRONTEND_PID_FILE"
kill_pattern "uvicorn backend.main:app" "backend"
kill_pattern "vite.*--port $FRONTEND_PORT" "frontend"

# --- Launch backend ----------------------------------------------------------
echo "Starting backend (uvicorn, port $BACKEND_PORT)..."
nohup "$VENV_DIR/bin/uvicorn" backend.main:app \
    --host 0.0.0.0 --port "$BACKEND_PORT" \
    > "$BACKEND_LOG" 2>&1 &
BACKEND_PID=$!
echo "$BACKEND_PID" > "$BACKEND_PID_FILE"

# --- Launch frontend ---------------------------------------------------------
echo "Starting frontend (vite dev, port $FRONTEND_PORT)..."
cd frontend
nohup npm run dev -- --port "$FRONTEND_PORT" \
    > "$SCRIPT_DIR/$FRONTEND_LOG" 2>&1 &
FRONTEND_PID=$!
echo "$FRONTEND_PID" > "$SCRIPT_DIR/$FRONTEND_PID_FILE"
cd "$SCRIPT_DIR"

# --- Verify they're alive ---------------------------------------------------
sleep 1.5
if ! kill -0 "$BACKEND_PID" 2>/dev/null; then
    echo "ERROR: backend exited immediately. Check $BACKEND_LOG." >&2
    rm -f "$BACKEND_PID_FILE"
    exit 1
fi
if ! kill -0 "$FRONTEND_PID" 2>/dev/null; then
    echo "ERROR: frontend exited immediately. Check $FRONTEND_LOG." >&2
    rm -f "$FRONTEND_PID_FILE"
    exit 1
fi

echo
echo "Started."
echo "  Frontend: http://localhost:$FRONTEND_PORT"
echo "  Backend:  http://localhost:$BACKEND_PORT/api/health"
echo "  Logs:     $BACKEND_LOG , $FRONTEND_LOG"
echo "Stop with: ./stop.sh"
