from __future__ import annotations

from pathlib import Path

import typer
from rich.console import Console
from rich.table import Table

from nanomanager.core.permissions import get_acl, grant_acl, revoke_acl
from nanomanager.state import AclGrant, load_state, save_state
from nanomanager.sudo import require_root

app = typer.Typer(help="Filesystem access management for nanobot")
console = Console()


@app.command()
def grant(
    path: str = typer.Argument(..., help="Path to grant access to"),
    write: bool = typer.Option(False, "--write", "-w", help="Grant write access (default: read-only)"),
) -> None:
    """Grant nanobot read or write access to a path."""
    require_root()

    mode = "rwX" if write else "rX"
    grant_acl(path, "nanobot", mode, recursive=True, set_default=True)

    state = load_state()
    if state is None:
        console.print("[yellow]Warning: no state file found, ACL applied but not recorded.[/yellow]")
        return

    # Update or add grant
    existing = next((g for g in state.acl_grants if g.path == path), None)
    if existing:
        existing.mode = mode  # type: ignore[assignment]
    else:
        state.acl_grants.append(AclGrant(path=path, mode=mode))  # type: ignore[arg-type]
    save_state(state)
    console.print(f"[green]Granted {'read/write' if write else 'read'} access to {path}[/green]")


@app.command()
def revoke(
    path: str = typer.Argument(..., help="Path to revoke access from"),
) -> None:
    """Revoke nanobot's access to a path."""
    require_root()

    revoke_acl(path, "nanobot", recursive=True)

    state = load_state()
    if state is None:
        console.print("[yellow]Warning: no state file found.[/yellow]")
        return

    state.acl_grants = [g for g in state.acl_grants if g.path != path]
    save_state(state)
    console.print(f"[green]Revoked access to {path}[/green]")


@app.command("list")
def list_grants() -> None:
    """List all filesystem access grants."""
    state = load_state()
    if state is None:
        console.print("[yellow]No state file found. Is nanomanager installed?[/yellow]")
        return

    if not state.acl_grants:
        console.print("[dim]No filesystem grants configured.[/dim]")
        return

    table = Table(title="Filesystem Access Grants")
    table.add_column("Path", style="cyan")
    table.add_column("Mode", style="bold")
    table.add_column("Granted At")
    table.add_column("Status")

    for grant in state.acl_grants:
        path_exists = Path(grant.path).exists()
        status = "[green]ok[/green]" if path_exists else "[red]missing[/red]"
        table.add_row(
            grant.path,
            "read/write" if grant.mode == "rwX" else "read",
            grant.granted_at.strftime("%Y-%m-%d %H:%M"),
            status,
        )

    console.print(table)
