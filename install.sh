#!/usr/bin/env bash
#
# install.sh - Set up the DeepSeek Translator (FastAPI + React).
#
# Creates a Python venv, installs backend deps, runs npm install for the
# frontend, and sets up .env from .env.example if missing.
#
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

VENV_DIR=".venv"
BACKEND_REQ="backend/requirements.txt"
ENV_FILE=".env"
ENV_EXAMPLE=".env.example"

echo "=== DeepSeek Translator installer ==="
echo "Project directory: $SCRIPT_DIR"
echo

# --- 1. Python ---------------------------------------------------------------
if ! command -v python3 >/dev/null 2>&1; then
    echo "ERROR: python3 not found." >&2
    exit 1
fi

if [[ -d "$VENV_DIR" ]]; then
    echo "Reusing existing venv '$VENV_DIR'."
else
    echo "Creating venv in '$VENV_DIR'..."
    python3 -m venv "$VENV_DIR"
fi

echo "Upgrading pip..."
"$VENV_DIR/bin/python" -m pip install --upgrade pip

echo "Installing backend dependencies..."
"$VENV_DIR/bin/python" -m pip install -r "$BACKEND_REQ"

# --- 2. Node -----------------------------------------------------------------
if ! command -v npm >/dev/null 2>&1; then
    echo "ERROR: npm not found. Install Node.js (v18+) and re-run." >&2
    exit 1
fi

echo "Installing frontend dependencies..."
cd frontend
npm install
cd "$SCRIPT_DIR"

# --- 3. .env -----------------------------------------------------------------
if [[ -f "$ENV_FILE" ]]; then
    echo ".env already exists - leaving it untouched."
else
    if [[ -f "$ENV_EXAMPLE" ]]; then
        cp "$ENV_EXAMPLE" "$ENV_FILE"
        echo "Created $ENV_FILE from $ENV_EXAMPLE."
    else
        cat > "$ENV_FILE" <<'EOF'
LLM_PROVIDER="deepseek"
DEEPSEEK_API_KEY="your_deepseek_key_here"
DEEPSEEK_MODEL="deepseek-reasoner"
OPENROUTER_API_KEY="your_openrouter_key_here"
OPENROUTER_MODEL="deepseek/deepseek-r1"
EOF
        echo "Created a default $ENV_FILE."
    fi
    echo "IMPORTANT: Edit $ENV_FILE and set your API key before starting the app."
fi

echo
echo "=== Installation complete ==="
echo "Run ./start.sh to launch the app."
