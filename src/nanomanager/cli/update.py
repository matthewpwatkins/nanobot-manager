from __future__ import annotations

import typer
from rich.console import Console

from nanomanager.core.service import restart_service, stop_service
from nanomanager.core.uv import get_nanobot_version, get_uv_path, lock_install_dirs, unlock_install_dirs, upgrade_nanobot
from nanomanager.state import load_state
from nanomanager.sudo import require_root

console = Console()


def update(
    version: str = typer.Option(None, "--version", help="Specific version to install"),
) -> None:
    """Update nanobot-ai to the latest version."""
    require_root()

    state = load_state()
    nanobot_user = state.nanobot_user if state else "nanobot"

    current = get_nanobot_version(nanobot_user)
    console.print(f"Current version: [bold]{current or 'unknown'}[/bold]")

    console.print("[cyan]Stopping nanobot service...[/cyan]")
    try:
        stop_service("nanobot")
    except Exception:
        pass

    console.print("[cyan]Unlocking install directories...[/cyan]")
    unlock_install_dirs(nanobot_user)

    try:
        if version:
            import subprocess, os
            uv = get_uv_path()
            console.print(f"[cyan]Installing nanobot-ai=={version}...[/cyan]")
            subprocess.run(
                ["sudo", "-u", nanobot_user, uv, "tool", "install", f"nanobot-ai=={version}", "--force"],
                check=True,
                env={**os.environ, "HOME": f"/home/{nanobot_user}"},
            )
        else:
            upgrade_nanobot(nanobot_user)
    finally:
        console.print("[cyan]Re-locking install directories...[/cyan]")
        lock_install_dirs(nanobot_user)

    new_version = get_nanobot_version(nanobot_user)
    console.print(f"New version: [bold green]{new_version or 'unknown'}[/bold green]")

    console.print("[cyan]Restarting nanobot service...[/cyan]")
    try:
        restart_service("nanobot")
        console.print("[green]nanobot updated and restarted.[/green]")
    except Exception as e:
        console.print(f"[yellow]Warning: could not restart service: {e}[/yellow]")
