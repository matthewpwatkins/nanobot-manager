from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path

from rich.console import Console

console = Console(stderr=True)


def check_acl_available() -> bool:
    return shutil.which("setfacl") is not None


def grant_acl(
    path: str,
    acl_user: str,
    mode: str,
    recursive: bool = False,
    set_default: bool = False,
) -> None:
    path_obj = Path(path)
    if not path_obj.exists():
        raise FileNotFoundError(f"Path does not exist: {path}")

    cmd = ["setfacl"]
    if recursive:
        cmd.append("-R")
    cmd += ["-m", f"u:{acl_user}:{mode}", path]
    subprocess.run(cmd, check=True)

    if set_default and path_obj.is_dir():
        cmd_default = ["setfacl"]
        if recursive:
            cmd_default.append("-R")
        cmd_default += ["-m", f"d:u:{acl_user}:{mode}", path]
        subprocess.run(cmd_default, check=True)

    console.print(f"[green]Granted ACL u:{acl_user}:{mode} on {path}[/green]")


def revoke_acl(path: str, acl_user: str, recursive: bool = False) -> None:
    cmd = ["setfacl"]
    if recursive:
        cmd.append("-R")
    cmd += ["-x", f"u:{acl_user}", path]
    subprocess.run(cmd, check=True)

    if Path(path).is_dir():
        cmd_default = ["setfacl"]
        if recursive:
            cmd_default.append("-R")
        cmd_default += ["-x", f"d:u:{acl_user}", path]
        subprocess.run(cmd_default, check=True)

    console.print(f"[green]Revoked ACL for u:{acl_user} on {path}[/green]")


def get_acl(path: str) -> str:
    result = subprocess.run(["getfacl", path], capture_output=True, text=True, check=True)
    return result.stdout


def setup_nanobot_dirs(nanobot_home: str = "/home/nanobot", managing_user: str | None = None) -> None:
    home = Path(nanobot_home)
    nanobot_dir = home / ".nanobot"
    workspace_dir = nanobot_dir / "workspace"
    local_dir = home / ".local"

    # Create dirs
    nanobot_dir.mkdir(parents=True, exist_ok=True)
    workspace_dir.mkdir(parents=True, exist_ok=True)
    local_dir.mkdir(parents=True, exist_ok=True)

    import pwd
    nanobot_uid = pwd.getpwnam("nanobot").pw_uid
    nanobot_gid = pwd.getpwnam("nanobot").pw_gid

    if managing_user:
        try:
            managing_uid = pwd.getpwnam(managing_user).pw_uid
        except KeyError:
            managing_uid = nanobot_uid
    else:
        managing_uid = nanobot_uid

    # ~/.nanobot/ owned by managing_user:nanobot, 750
    os.chown(nanobot_dir, managing_uid, nanobot_gid)
    os.chmod(nanobot_dir, 0o750)

    # ~/.nanobot/workspace/ owned by nanobot:nanobot, 750
    os.chown(workspace_dir, nanobot_uid, nanobot_gid)
    os.chmod(workspace_dir, 0o750)

    # ~/.local/ owned by root:nanobot, 750
    os.chown(local_dir, 0, nanobot_gid)
    os.chmod(local_dir, 0o750)

    console.print(f"[green]Set up nanobot directories in {nanobot_home}[/green]")
