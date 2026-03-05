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

# Ensure ~/.local/bin is in PATH
LOCAL_BIN='export PATH="$HOME/.local/bin:$PATH"'
if ! echo "$PATH" | grep -q "$HOME/.local/bin"; then
    # Detect shell rc file
    RC_FILE=""
    case "$(basename "${SHELL:-bash}")" in
        zsh)  RC_FILE="$HOME/.zshrc" ;;
        fish) RC_FILE="$HOME/.config/fish/config.fish" ;;
        *)    RC_FILE="$HOME/.bashrc" ;;
    esac

    if [ -n "$RC_FILE" ] && ! grep -qF '.local/bin' "$RC_FILE" 2>/dev/null; then
        read -rp "Add ~/.local/bin to PATH in $RC_FILE? [Y/n] " answer
        answer="${answer:-Y}"
        if [[ "$answer" =~ ^[Yy] ]]; then
            echo "" >> "$RC_FILE"
            echo '# Added by nanomanager bootstrap' >> "$RC_FILE"
            echo "$LOCAL_BIN" >> "$RC_FILE"
            echo "Added to $RC_FILE. Run 'source $RC_FILE' or open a new shell."
        fi
    fi

    # Also export for the rest of this session
    export PATH="$HOME/.local/bin:$PATH"
fi

echo ""
echo "Done. Run 'sudo nanomanager install' to set up the sandbox."
