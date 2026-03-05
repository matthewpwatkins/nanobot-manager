from __future__ import annotations

import typer
from rich.console import Console
from rich.table import Table

from nanomanager.core.nanobot_config import CONFIG_PATH, read_config, write_config
from nanomanager.state import load_state
from nanomanager.sudo import require_root

app = typer.Typer(help="MCP server management")
console = Console()


def _get_mcp_servers(config: dict) -> dict:
    return config.get("tools", {}).get("mcpServers", {})


def _set_mcp_servers(config: dict, servers: dict) -> None:
    if "tools" not in config:
        config["tools"] = {"restrictToWorkspace": True}
    config["tools"]["mcpServers"] = servers


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
    servers = _get_mcp_servers(config)

    entry: dict = {}
    if server_type == "stdio":
        parts = command.split()  # type: ignore[union-attr]
        entry["command"] = parts[0]
        if len(parts) > 1:
            entry["args"] = parts[1:]
    else:
        entry["url"] = url

    servers[name] = entry
    _set_mcp_servers(config, servers)

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
    servers = _get_mcp_servers(config)
    if name not in servers:
        console.print(f"[yellow]MCP server '{name}' not found.[/yellow]")
        raise typer.Exit(1)

    del servers[name]
    _set_mcp_servers(config, servers)

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

    servers = _get_mcp_servers(config)
    if not servers:
        console.print("[dim]No MCP servers configured.[/dim]")
        return

    table = Table(title="MCP Servers")
    table.add_column("Name", style="cyan")
    table.add_column("Type")
    table.add_column("Command / URL")

    for name, cfg in servers.items():
        if "command" in cfg:
            cmd_parts = [cfg.get("command", "")] + cfg.get("args", [])
            detail = " ".join(cmd_parts)
        else:
            detail = cfg.get("url", "")
        stype = "stdio" if "command" in cfg else "sse"
        table.add_row(name, stype, detail)

    console.print(table)
