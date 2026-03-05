from __future__ import annotations

import subprocess
import sys

from rich.console import Console

console = Console(stderr=True)


def require_root() -> None:
    import os
    if os.geteuid() != 0:
        console.print("[bold red]Error:[/bold red] This command must be run as root (sudo nanomanager ...).")
        sys.exit(1)


def run_as_user(user: str, cmd: list[str], **kwargs) -> subprocess.CompletedProcess:
    full_cmd = ["sudo", "-u", user] + cmd
    return subprocess.run(full_cmd, **kwargs)


def run_privileged(cmd: list[str], **kwargs) -> subprocess.CompletedProcess:
    kwargs.setdefault("check", True)
    return subprocess.run(cmd, **kwargs)
