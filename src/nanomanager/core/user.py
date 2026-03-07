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


def create_nanobot_user(username: str = "nanobot") -> bool:
    if user_exists(username):
        console.print(f"[yellow]User '{username}' already exists, skipping.[/yellow]")
        return False
    cmd = [
        "useradd",
        "--system",
        "--create-home",
        "--home-dir", f"/home/{username}",
        "--shell", "/usr/sbin/nologin",
    ]
    if _group_exists(username):
        cmd += ["-g", username]
    else:
        cmd.append("--user-group")
    cmd.append(username)
    subprocess.run(cmd, check=True)
    console.print(f"[green]Created system user '{username}'.[/green]")
    return True


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


def add_user_to_group(username: str, group: str) -> None:
    subprocess.run(["usermod", "-aG", group, username], check=True)
    console.print(f"[green]Added '{username}' to group '{group}'.[/green]")


def get_user_home(username: str) -> Path:
    import pwd
    return Path(pwd.getpwnam(username).pw_dir)
