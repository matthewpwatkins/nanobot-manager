#!/bin/bash
# Bootstrap nanomanager: installs uv if missing, then installs nanomanager via uv.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

# Install uv if not found
if ! command -v uv &>/dev/null; then
    echo "Installing uv..."
    curl -LsSf https://astral.sh/uv/install.sh | sh
    export PATH="$HOME/.local/bin:$PATH"
fi

echo "Installing nanomanager..."
uv tool install --from "$SCRIPT_DIR" nanobot-manager

echo ""
echo "Done. Run 'sudo nanomanager install' to set up the sandbox."
