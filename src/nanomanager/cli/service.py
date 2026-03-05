from __future__ import annotations

import os
import subprocess
import sys

import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from nanomanager.core.service import get_service_status
from nanomanager.state import load_state
from nanomanager.sudo import require_root

console = Console()


def start() -> None:
    """Start the nanobot service."""
    require_root()
    subprocess.run(["systemctl", "start", "nanobot"], check=True)
    console.print("[green]nanobot service started.[/green]")
    _print_quick_status()


def stop() -> None:
    """Stop the nanobot service."""
    require_root()
    subprocess.run(["systemctl", "stop", "nanobot"], check=True)
    console.print("[yellow]nanobot service stopped.[/yellow]")


def restart() -> None:
    """Restart the nanobot service."""
    require_root()
    subprocess.run(["systemctl", "restart", "nanobot"], check=True)
    console.print("[green]nanobot service restarted.[/green]")
    _print_quick_status()


def status(
    json_output: bool = typer.Option(False, "--json", help="Output as JSON"),
) -> None:
    """Show nanobot service status and health."""
    svc = get_service_status("nanobot")
    state = load_state()

    if json_output:
        import json as json_mod
        data: dict = {"service": svc}
        if state:
            data["proxy_enabled"] = state.install_options.proxy_enabled
            data["firewall_enabled"] = state.install_options.firewall_enabled
        console.print_json(json_mod.dumps(data))
        return

    # Service status
    active = svc.get("ActiveState", "unknown")
    sub = svc.get("SubState", "unknown")
    color = "green" if active == "active" else "red"

    table = Table(show_header=False, box=None, padding=(0, 2))
    table.add_column("Key", style="bold")
    table.add_column("Value")
    table.add_row("Service", f"[{color}]{active} ({sub})[/{color}]")
    table.add_row("PID", svc.get("MainPID", "—"))

    if state:
        proxy_state = "enabled" if state.install_options.proxy_enabled else "disabled"
        fw_state = "enabled" if state.install_options.firewall_enabled else "disabled"
        proxy_color = "green" if state.install_options.proxy_enabled else "yellow"
        fw_color = "green" if state.install_options.firewall_enabled else "yellow"
        table.add_row("Proxy", f"[{proxy_color}]{proxy_state}[/{proxy_color}]")
        table.add_row("Firewall", f"[{fw_color}]{fw_state}[/{fw_color}]")
        table.add_row("Managing user", state.managing_user)
        table.add_row("ACL grants", str(len(state.acl_grants)))
        table.add_row("Allowed domains", str(len(state.network_domains)))

    # Config health
    from pathlib import Path
    from nanomanager.core.nanobot_config import CONFIG_PATH, validate_config
    config_ok = "[red]missing[/red]"
    if CONFIG_PATH.exists():
        try:
            import json
            config = json.loads(CONFIG_PATH.read_text())
            errors = validate_config(config)
            config_ok = "[green]valid[/green]" if not errors else f"[red]{len(errors)} error(s)[/red]"
        except Exception as e:
            config_ok = f"[red]invalid JSON[/red]"
    table.add_row("Config", config_ok)

    console.print(Panel(table, title="[bold]Nanobot Status[/bold]", border_style="cyan"))


def logs(
    follow: bool = typer.Option(False, "--follow", "-f", help="Follow log output"),
    lines: int = typer.Option(50, "--lines", "-n", help="Number of lines to show"),
) -> None:
    """Show nanobot service logs."""
    cmd = ["journalctl", "-u", "nanobot", f"-n{lines}", "--no-pager"]
    if follow:
        cmd.append("-f")
    os.execvp("journalctl", cmd)


def _print_quick_status() -> None:
    svc = get_service_status("nanobot")
    active = svc.get("ActiveState", "unknown")
    sub = svc.get("SubState", "unknown")
    color = "green" if active == "active" else "red"
    console.print(f"Status: [{color}]{active} ({sub})[/{color}]")
