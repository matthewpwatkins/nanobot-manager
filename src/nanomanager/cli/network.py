from __future__ import annotations

import typer
from rich.console import Console
from rich.table import Table

from nanomanager.core.proxy import add_domain, remove_domain
from nanomanager.state import load_state
from nanomanager.sudo import require_root

app = typer.Typer(help="Network domain allowlist management")
console = Console()


@app.command()
def allow(
    domain: str = typer.Argument(..., help="Domain to allow (e.g. api.example.com)"),
) -> None:
    """Add a domain to the network allowlist."""
    require_root()
    state = load_state()
    if state is None:
        console.print("[red]Error:[/red] nanomanager not installed.")
        raise typer.Exit(1)
    if not state.install_options.proxy_enabled:
        console.print("[yellow]Warning:[/yellow] Proxy is not enabled; domain allowlist has no effect.")
    add_domain(domain, state)


@app.command()
def block(
    domain: str = typer.Argument(..., help="Domain to block/remove from allowlist"),
) -> None:
    """Remove a domain from the network allowlist."""
    require_root()
    state = load_state()
    if state is None:
        console.print("[red]Error:[/red] nanomanager not installed.")
        raise typer.Exit(1)
    remove_domain(domain, state)


@app.command("list")
def list_domains() -> None:
    """List all allowed network domains."""
    state = load_state()
    if state is None:
        console.print("[yellow]No state file found. Is nanomanager installed?[/yellow]")
        return

    if not state.network_domains:
        console.print("[dim]No domains in allowlist.[/dim]")
        return

    table = Table(title="Network Allowlist")
    table.add_column("Domain", style="cyan")
    table.add_column("Type")
    table.add_column("Added At")

    for nd in sorted(state.network_domains, key=lambda d: d.domain):
        domain_type = "[dim]builtin[/dim]" if nd.builtin else "custom"
        table.add_row(
            nd.domain,
            domain_type,
            nd.added_at.strftime("%Y-%m-%d %H:%M"),
        )

    console.print(table)
