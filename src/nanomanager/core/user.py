from __future__ import annotations

import getpass
import os
import subprocess
from pathlib import Path

from rich.console import Console

console = Console(stderr=True)


def user_exists(username: str) -> bool:
    try:
        import pwd
        pwd.getpwnam(username)
        return True
    except KeyError:
        return False


def get_current_user() -> str:
    # When running with sudo, get the original user
    return os.environ.get("SUDO_USER") or getpass.getuser()


def _group_exists(name: str) -> bool:
    import grp
    try:
        grp.getgrnam(name)
        return True
    except KeyError:
        return False


def create_nanobot_user(username: str = "nanobot", enable_display: bool = False) -> bool:
    if user_exists(username):
        console.print(f"[yellow]User '{username}' already exists, skipping.[/yellow]")
        return False
    shell = "/bin/bash" if enable_display else "/usr/sbin/nologin"
    cmd = [
        "useradd",
        "--system",
        "--create-home",
        "--home-dir", f"/home/{username}",
        "--shell", shell,
    ]
    if _group_exists(username):
        cmd += ["-g", username]
    else:
        cmd.append("--user-group")
    cmd.append(username)
    subprocess.run(cmd, check=True)
    console.print(f"[green]Created system user '{username}'.[/green]")
    return True


def enable_display_login(username: str = "nanobot") -> None:
    """Enable display login for an existing nanobot user: set shell, password, and groups."""
    import pwd
    pw = pwd.getpwnam(username)

    # Set login shell if currently nologin
    if pw.pw_shell in ("/usr/sbin/nologin", "/bin/false"):
        subprocess.run(["usermod", "--shell", "/bin/bash", username], check=True)
        console.print(f"[green]Set login shell to /bin/bash for '{username}'.[/green]")

    # Add to display-related groups
    for group in ("video", "audio", "input", "render"):
        if _group_exists(group):
            subprocess.run(["usermod", "-aG", group, username], check=True)
    console.print(f"[green]Added '{username}' to display groups.[/green]")

    # Set password
    console.print(f"[bold]Set a password for '{username}':[/bold]")
    subprocess.run(["passwd", username], check=True)

    # Ensure display manager shows the nanobot user
    # (system users have low UIDs and are hidden by default)
    _configure_display_manager(username)


def remove_nanobot_user(username: str = "nanobot", keep_home: bool = False) -> None:
    if not user_exists(username):
        console.print(f"[yellow]User '{username}' does not exist, skipping.[/yellow]")
        return
    cmd = ["userdel"]
    if not keep_home:
        cmd.append("-r")
    cmd.append(username)
    subprocess.run(cmd, check=True)
    console.print(f"[green]Removed user '{username}'.[/green]")
    if _group_exists(username):
        subprocess.run(["groupdel", username], check=True)
        console.print(f"[green]Removed group '{username}'.[/green]")


def _configure_display_manager(username: str) -> None:
    """Configure the display manager to show the nanobot user on the login screen."""
    lightdm_dir = Path("/etc/lightdm/lightdm.conf.d")
    if lightdm_dir.parent.exists():
        lightdm_dir.mkdir(parents=True, exist_ok=True)
        conf = lightdm_dir / "50-show-nanobot.conf"
        conf.write_text("[Seat:*]\ngreeter-hide-users=false\n")
        console.print(f"[green]Configured LightDM to show '{username}' on login screen.[/green]")
    else:
        console.print("[yellow]LightDM not found — you may need to configure your display manager manually.[/yellow]")


def add_user_to_group(username: str, group: str) -> None:
    subprocess.run(["usermod", "-aG", group, username], check=True)
    console.print(f"[green]Added '{username}' to group '{group}'.[/green]")


def get_user_home(username: str) -> Path:
    import pwd
    return Path(pwd.getpwnam(username).pw_dir)
