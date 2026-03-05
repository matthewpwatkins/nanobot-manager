from __future__ import annotations

import typer
from rich.console import Console
from rich.table import Table

from nanomanager.core.nanobot_config import CONFIG_PATH, read_config, write_config
from nanomanager.state import load_state
from nanomanager.sudo import require_root

app = typer.Typer(help="MCP server management")
console = Console()


@app.command()
def add(
    name: str = typer.Argument(..., help="MCP server name"),
    server_type: str = typer.Option(..., "--type", help="Server type: stdio or sse"),
    command: str = typer.Option(None, "--command", help="Command for stdio servers"),
    url: str = typer.Option(None, "--url", help="URL for SSE servers"),
) -> None:
    """Add an MCP server to nanobot config."""
    require_root()

    if server_type not in ("stdio", "sse"):
        console.print("[red]Error:[/red] --type must be 'stdio' or 'sse'")
        raise typer.Exit(1)
    if server_type == "stdio" and not command:
        console.print("[red]Error:[/red] --command is required for stdio servers")
        raise typer.Exit(1)
    if server_type == "sse" and not url:
        console.print("[red]Error:[/red] --url is required for sse servers")
        raise typer.Exit(1)

    config = read_config()
    if "mcpServers" not in config:
        config["mcpServers"] = {}

    entry: dict = {"type": server_type}
    if server_type == "stdio":
        parts = command.split()  # type: ignore[union-attr]
        entry["command"] = parts[0]
        if len(parts) > 1:
            entry["args"] = parts[1:]
    else:
        entry["url"] = url

    config["mcpServers"][name] = entry

    state = load_state()
    write_config(config, owner_user=state.managing_user if state else None)
    console.print(f"[green]Added MCP server '{name}'.[/green]")


@app.command()
def remove(
    name: str = typer.Argument(..., help="MCP server name to remove"),
) -> None:
    """Remove an MCP server from nanobot config."""
    require_root()

    config = read_config()
    servers = config.get("mcpServers", {})
    if name not in servers:
        console.print(f"[yellow]MCP server '{name}' not found.[/yellow]")
        raise typer.Exit(1)

    del servers[name]
    config["mcpServers"] = servers

    state = load_state()
    write_config(config, owner_user=state.managing_user if state else None)
    console.print(f"[green]Removed MCP server '{name}'.[/green]")


@app.command("list")
def list_servers() -> None:
    """List configured MCP servers."""
    if not CONFIG_PATH.exists():
        console.print("[yellow]No config found. Run 'sudo nanomanager onboard' first.[/yellow]")
        return

    import json
    try:
        config = read_config()
    except json.JSONDecodeError:
        console.print("[red]Config is invalid JSON.[/red]")
        raise typer.Exit(1)

    servers = config.get("mcpServers", {})
    if not servers:
        console.print("[dim]No MCP servers configured.[/dim]")
        return

    table = Table(title="MCP Servers")
    table.add_column("Name", style="cyan")
    table.add_column("Type")
    table.add_column("Command / URL")

    for name, cfg in servers.items():
        stype = cfg.get("type", "unknown")
        if stype == "stdio":
            cmd_parts = [cfg.get("command", "")] + cfg.get("args", [])
            detail = " ".join(cmd_parts)
        else:
            detail = cfg.get("url", "")
        table.add_row(name, stype, detail)

    console.print(table)
