#!/bin/bash
# Bootstrap nanomanager: installs uv if missing, then installs nanomanager.
# Run with: sudo ./bootstrap.sh
# Idempotent — safe to run repeatedly regardless of system state.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

# Must run as root
if [ "$(id -u)" -ne 0 ]; then
    echo "Usage: sudo $0"
    exit 1
fi

# Resolve the real user (not root)
REAL_USER="${SUDO_USER:-}"
if [ -z "$REAL_USER" ]; then
    echo "Error: could not determine calling user. Run with sudo, not as root directly."
    exit 1
fi
REAL_HOME="$(eval echo "~$REAL_USER")"
REAL_GROUP="$(id -gn "$REAL_USER")"
UV_BIN="$REAL_HOME/.local/bin/uv"

# --- Step 1: Ensure uv is installed for the real user ---
if [ ! -f "$UV_BIN" ]; then
    echo "Installing uv for $REAL_USER..."
    sudo -u "$REAL_USER" sh -c 'curl -LsSf https://astral.sh/uv/install.sh | sh'
fi

# --- Step 2: Clean up any stale nanomanager install ---
# Fix root-owned files (caused by running nanomanager under sudo, which writes .pyc as root)
UV_TOOLS_DIR="$REAL_HOME/.local/share/uv/tools/nanobot-manager"
if [ -d "$UV_TOOLS_DIR" ]; then
    chown -R "$REAL_USER":"$REAL_GROUP" "$UV_TOOLS_DIR"
fi

# Fully uninstall and clear cache to avoid stale builds
sudo -u "$REAL_USER" "$UV_BIN" tool uninstall nanobot-manager 2>/dev/null || true
sudo -u "$REAL_USER" "$UV_BIN" cache clean nanobot-manager 2>/dev/null || true

# --- Step 3: Install nanomanager ---
echo "Installing nanomanager..."
sudo -u "$REAL_USER" "$UV_BIN" tool install --from "$SCRIPT_DIR" --reinstall nanobot-manager

# --- Step 4: Symlink into /usr/local/bin so 'sudo nanomanager' works ---
NANOMANAGER_BIN="$REAL_HOME/.local/bin/nanomanager"
ln -sf "$NANOMANAGER_BIN" /usr/local/bin/nanomanager
echo "Linked /usr/local/bin/nanomanager -> $NANOMANAGER_BIN"

# --- Step 5: Ensure ~/.local/bin is in the user's PATH ---
SHELL_NAME="$(basename "$(getent passwd "$REAL_USER" | cut -d: -f7)")"
case "$SHELL_NAME" in
    zsh)  RC_FILE="$REAL_HOME/.zshrc" ;;
    fish) RC_FILE="$REAL_HOME/.config/fish/config.fish" ;;
    *)    RC_FILE="$REAL_HOME/.bashrc" ;;
esac

if [ -n "$RC_FILE" ] && ! grep -qF '.local/bin' "$RC_FILE" 2>/dev/null; then
    echo "" >> "$RC_FILE"
    echo '# Added by nanomanager bootstrap' >> "$RC_FILE"
    echo 'export PATH="$HOME/.local/bin:$PATH"' >> "$RC_FILE"
    chown "$REAL_USER":"$REAL_GROUP" "$RC_FILE"
    echo "Added ~/.local/bin to PATH in $RC_FILE"
fi

echo ""
echo "Done. Run 'sudo nanomanager install' to set up the sandbox."
