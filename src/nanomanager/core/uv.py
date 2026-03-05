from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path

from rich.console import Console

console = Console(stderr=True)


def find_uv() -> str | None:
    """Find the uv binary, checking common locations beyond just PATH."""
    found = shutil.which("uv")
    if found:
        return found
    # Check common install locations (uv installer puts it in ~/.local/bin)
    for candidate in [
        Path.home() / ".local" / "bin" / "uv",
        Path("/usr/local/bin/uv"),
        Path("/root/.local/bin/uv"),
    ]:
        if candidate.is_file():
            return str(candidate)
    # Check the SUDO_USER's home too
    sudo_user = os.environ.get("SUDO_USER")
    if sudo_user:
        import pwd
        try:
            user_home = Path(pwd.getpwnam(sudo_user).pw_dir)
            candidate = user_home / ".local" / "bin" / "uv"
            if candidate.is_file():
                return str(candidate)
        except KeyError:
            pass
    return None


def check_uv_installed() -> bool:
    return find_uv() is not None


def get_uv_path() -> str:
    """Get the full path to uv, raising if not found."""
    path = find_uv()
    if path is None:
        raise FileNotFoundError("uv not found")
    return path


def install_uv() -> None:
    console.print("[cyan]Installing uv...[/cyan]")
    # Install as the real user if running under sudo, otherwise current user
    sudo_user = os.environ.get("SUDO_USER")
    if sudo_user:
        subprocess.run(
            ["sudo", "-u", sudo_user, "sh", "-c",
             "curl -LsSf https://astral.sh/uv/install.sh | sh"],
            check=True,
        )
    else:
        subprocess.run(
            ["sh", "-c", "curl -LsSf https://astral.sh/uv/install.sh | sh"],
            check=True,
        )
    console.print("[green]uv installed.[/green]")


def get_nanobot_bin_path(nanobot_user: str = "nanobot") -> Path:
    return Path(f"/home/{nanobot_user}/.local/bin/nanobot")


def install_nanobot(nanobot_user: str = "nanobot") -> None:
    uv = get_uv_path()
    console.print(f"[cyan]Installing nanobot-ai for user '{nanobot_user}'...[/cyan]")
    subprocess.run(
        ["sudo", "-u", nanobot_user, uv, "tool", "install", "nanobot-ai"],
        check=True,
        env={**os.environ, "HOME": f"/home/{nanobot_user}"},
    )
    console.print("[green]nanobot-ai installed.[/green]")


def upgrade_nanobot(nanobot_user: str = "nanobot") -> None:
    uv = get_uv_path()
    console.print(f"[cyan]Upgrading nanobot-ai...[/cyan]")
    subprocess.run(
        ["sudo", "-u", nanobot_user, uv, "tool", "upgrade", "nanobot-ai"],
        check=True,
        env={**os.environ, "HOME": f"/home/{nanobot_user}"},
    )
    console.print("[green]nanobot-ai upgraded.[/green]")


def get_nanobot_version(nanobot_user: str = "nanobot") -> str | None:
    uv = get_uv_path()
    result = subprocess.run(
        ["sudo", "-u", nanobot_user, uv, "tool", "list"],
        capture_output=True,
        text=True,
        env={**os.environ, "HOME": f"/home/{nanobot_user}"},
    )
    for line in result.stdout.splitlines():
        if "nanobot-ai" in line:
            parts = line.split()
            if len(parts) >= 2:
                return parts[1].strip("v()")
    return None


def lock_install_dirs(nanobot_user: str = "nanobot") -> None:
    import pwd
    nanobot_gid = pwd.getpwnam(nanobot_user).pw_gid
    local_dir = Path(f"/home/{nanobot_user}/.local")
    if local_dir.exists():
        os.chown(local_dir, 0, nanobot_gid)
        os.chmod(local_dir, 0o750)
    console.print(f"[green]Locked install dirs for '{nanobot_user}'.[/green]")


def unlock_install_dirs(nanobot_user: str = "nanobot") -> None:
    import pwd
    pw = pwd.getpwnam(nanobot_user)
    local_dir = Path(f"/home/{nanobot_user}/.local")
    if local_dir.exists():
        os.chown(local_dir, pw.pw_uid, pw.pw_gid)
        os.chmod(local_dir, 0o750)
    console.print(f"[green]Unlocked install dirs for '{nanobot_user}'.[/green]")
