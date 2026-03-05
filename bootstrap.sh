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

# Symlink into /usr/local/bin so 'sudo nanomanager' works
# (sudo resets PATH and won't find ~/.local/bin)
NANOMANAGER_BIN="$HOME/.local/bin/nanomanager"
if [ -f "$NANOMANAGER_BIN" ] && [ ! -f /usr/local/bin/nanomanager ]; then
    echo "Linking nanomanager into /usr/local/bin (requires sudo)..."
    sudo ln -sf "$NANOMANAGER_BIN" /usr/local/bin/nanomanager
fi

echo ""
echo "Done. Run 'sudo nanomanager install' to set up the sandbox."
