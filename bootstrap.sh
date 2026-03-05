#!/bin/bash
# Bootstrap nanomanager: installs uv if missing, then installs nanomanager.
# Run with: sudo ./bootstrap.sh
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

# Install uv for the real user if not found
if ! sudo -u "$REAL_USER" sh -c 'command -v uv' &>/dev/null; then
    echo "Installing uv for $REAL_USER..."
    sudo -u "$REAL_USER" sh -c 'curl -LsSf https://astral.sh/uv/install.sh | sh'
fi
UV_BIN="$REAL_HOME/.local/bin/uv"

# Install nanomanager for the real user
echo "Installing nanomanager..."
sudo -u "$REAL_USER" "$UV_BIN" tool install --from "$SCRIPT_DIR" nanobot-manager

# Symlink into /usr/local/bin so it's available under sudo
NANOMANAGER_BIN="$REAL_HOME/.local/bin/nanomanager"
ln -sf "$NANOMANAGER_BIN" /usr/local/bin/nanomanager
echo "Linked /usr/local/bin/nanomanager -> $NANOMANAGER_BIN"

# Ensure ~/.local/bin is in the user's PATH for non-sudo usage
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
    chown "$REAL_USER":"$(id -gn "$REAL_USER")" "$RC_FILE"
    echo "Added ~/.local/bin to PATH in $RC_FILE"
fi

echo ""
echo "Done. Run 'sudo nanomanager install' to set up the sandbox."
