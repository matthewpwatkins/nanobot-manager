from __future__ import annotations

import os
import subprocess
from pathlib import Path

from rich.console import Console

console = Console(stderr=True)

NVM_DIR = Path("/home/nanobot/.nvm")


def nvm_installed() -> bool:
    return (NVM_DIR / "nvm.sh").is_file()


def node_installed() -> bool:
    """Check if node is installed via nvm in the nanobot home."""
    if not nvm_installed():
        return False
    node = _find_node_bin()
    return node is not None


def _find_node_bin() -> Path | None:
    """Find the active node binary under nvm."""
    # nvm installs to NVM_DIR/versions/node/vX.Y.Z/bin/node
    versions_dir = NVM_DIR / "versions" / "node"
    if not versions_dir.exists():
        return None
    # Pick the latest installed version
    versions = sorted(versions_dir.iterdir(), reverse=True)
    for v in versions:
        node = v / "bin" / "node"
        if node.is_file():
            return node
    return None


def get_node_bin_dir() -> Path | None:
    """Get the bin directory containing node/npx."""
    node = _find_node_bin()
    if node:
        return node.parent
    return None


def install_nvm_and_node(nanobot_user: str = "nanobot") -> Path:
    """Install nvm and Node.js LTS under /home/nanobot/.nvm.

    Returns the path to the node bin directory.
    """
    import pwd
    nanobot_pw = pwd.getpwnam(nanobot_user)

    if not nvm_installed():
        console.print("[cyan]Installing nvm...[/cyan]")
        # Download nvm install script and run it with NVM_DIR set
        env = {
            "HOME": f"/home/{nanobot_user}",
            "NVM_DIR": str(NVM_DIR),
            "PATH": os.environ.get("PATH", "/usr/bin:/bin"),
        }
        subprocess.run(
            ["bash", "-c", "curl -o- https://raw.githubusercontent.com/nvm-sh/nvm/v0.40.3/install.sh | bash"],
            check=True,
            env=env,
        )
        console.print("[green]nvm installed.[/green]")
    else:
        console.print("[yellow]nvm already installed, skipping.[/yellow]")

    # Install Node.js LTS using nvm
    console.print("[cyan]Installing Node.js LTS via nvm...[/cyan]")
    env = {
        "HOME": f"/home/{nanobot_user}",
        "NVM_DIR": str(NVM_DIR),
        "PATH": os.environ.get("PATH", "/usr/bin:/bin"),
    }
    subprocess.run(
        ["bash", "-c", f'source "{NVM_DIR}/nvm.sh" && nvm install --lts'],
        check=True,
        env=env,
    )

    node_bin_dir = get_node_bin_dir()
    if node_bin_dir is None:
        raise RuntimeError("Node.js installation failed — no node binary found")

    console.print(f"[green]Node.js installed at {node_bin_dir}[/green]")

    # Lock nvm dir: root-owned, readable by nanobot group
    _lock_nvm_dir(nanobot_user)

    return node_bin_dir


def _lock_nvm_dir(nanobot_user: str = "nanobot") -> None:
    """Make nvm dir owned by root:nanobot, readable but not writable."""
    import pwd
    nanobot_gid = pwd.getpwnam(nanobot_user).pw_gid

    for dirpath, dirnames, filenames in os.walk(NVM_DIR):
        os.chown(dirpath, 0, nanobot_gid)
        os.chmod(dirpath, 0o755)
        for fname in filenames:
            fpath = os.path.join(dirpath, fname)
            os.chown(fpath, 0, nanobot_gid)
            os.chmod(fpath, 0o644)

    # Make binaries executable
    node_bin_dir = get_node_bin_dir()
    if node_bin_dir and node_bin_dir.exists():
        for f in node_bin_dir.iterdir():
            if f.is_file():
                os.chmod(f, 0o755)
