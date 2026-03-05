from __future__ import annotations

import json
import os
import subprocess
import tempfile
from pathlib import Path

import typer
from rich.console import Console
from rich.panel import Panel
from rich.syntax import Syntax

from nanomanager.core.nanobot_config import CONFIG_PATH, read_config, validate_config, write_config
from nanomanager.state import load_state
from nanomanager.sudo import require_root

app = typer.Typer(help="Nanobot configuration management")
console = Console()

SECRET_KEYS = {"apiKey", "token", "botToken", "appToken", "accessToken", "appSecret"}


def _redact(config: dict) -> dict:
    result = {}
    for k, v in config.items():
        if k in SECRET_KEYS and isinstance(v, str) and v:
            result[k] = "***REDACTED***"
        elif isinstance(v, dict):
            result[k] = _redact(v)
        else:
            result[k] = v
    return result


@app.command()
def show(
    reveal_secrets: bool = typer.Option(False, "--reveal-secrets", help="Show API keys and tokens"),
) -> None:
    """Display current nanobot configuration."""
    if not CONFIG_PATH.exists():
        console.print(f"[red]Config not found at {CONFIG_PATH}[/red]")
        console.print("Run [cyan]sudo nanomanager onboard[/cyan] to configure.")
        raise typer.Exit(1)

    try:
        config = read_config()
    except json.JSONDecodeError as e:
        console.print(f"[red]Config is invalid JSON:[/red] {e}")
        raise typer.Exit(1)

    display = config if reveal_secrets else _redact(config)
    json_str = json.dumps(display, indent=2)
    syntax = Syntax(json_str, "json", theme="monokai", line_numbers=True)
    console.print(Panel(syntax, title=f"[bold]{CONFIG_PATH}[/bold]", border_style="cyan"))

    errors = validate_config(config)
    if errors:
        console.print("[red]Validation errors:[/red]")
        for err in errors:
            console.print(f"  - {err}")


@app.command()
def edit() -> None:
    """Open nanobot config in $EDITOR with validation."""
    require_root()

    if not CONFIG_PATH.exists():
        console.print(f"[red]Config not found at {CONFIG_PATH}[/red]")
        raise typer.Exit(1)

    state = load_state()
    editor = os.environ.get("EDITOR", "nano")
    original = CONFIG_PATH.read_text()

    with tempfile.NamedTemporaryFile(suffix=".json", mode="w", delete=False) as tmp:
        tmp.write(original)
        tmp_path = Path(tmp.name)

    try:
        subprocess.run([editor, str(tmp_path)], check=True)
        new_content = tmp_path.read_text()

        # Validate JSON
        try:
            new_config = json.loads(new_content)
        except json.JSONDecodeError as e:
            console.print(f"[red]Invalid JSON, aborting:[/red] {e}")
            raise typer.Exit(1)

        errors = validate_config(new_config)
        if errors:
            console.print("[red]Validation errors:[/red]")
            for err in errors:
                console.print(f"  - {err}")
            if not typer.confirm("Save anyway?"):
                raise typer.Exit(0)

        owner_user = state.managing_user if state else None
        write_config(new_config, owner_user=owner_user)
        console.print("[green]Config saved.[/green]")
    finally:
        tmp_path.unlink(missing_ok=True)
