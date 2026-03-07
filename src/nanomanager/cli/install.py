from __future__ import annotations

import shutil
import sys
from pathlib import Path

import typer
from rich.console import Console
from rich.panel import Panel

from nanomanager.core.firewall import apply_firewall_rules, write_firewall_script
from nanomanager.core.nanobot_config import (
    DEFAULT_CONFIG,
    write_config,
)
from nanomanager.core.permissions import check_acl_available, setup_nanobot_dirs
from nanomanager.core.proxy import (
    PROXY_PORT,
    SQUID_ALLOWLIST_PATH,
    check_squid_installed,
    install_squid,
    write_domain_allowlist,
    write_squid_config,
)
from nanomanager.core.service import (
    daemon_reload,
    disable_service,
    enable_service,
    restart_service,
    stop_service,
    write_firewall_service,
    write_nanobot_service,
    SYSTEMD_DIR,
)
from nanomanager.core.user import (
    add_user_to_group,
    create_nanobot_user,
    get_current_user,
    remove_nanobot_user,
    user_exists,
)
from nanomanager.core.uv import find_uv, install_nanobot, lock_install_dirs
from nanomanager.state import (
    InstallOptions,
    ManagerState,
    NetworkDomain,
    ensure_state_dir,
    load_state,
    save_state,
)
from nanomanager.sudo import require_root

console = Console()
err_console = Console(stderr=True)

# Default builtin domains always allowed
BUILTIN_DOMAINS = [
    # Common CDN/infra used by many providers
]


def install(
    skip_proxy: bool = typer.Option(False, "--skip-proxy", help="Skip squid proxy setup"),
    skip_firewall: bool = typer.Option(False, "--skip-firewall", help="Skip iptables firewall setup"),
    yes: bool = typer.Option(False, "--yes", "-y", help="Skip confirmation prompt"),
) -> None:
    """Install and configure nanobot in a hardened sandbox."""
    require_root()

    console.print(Panel.fit("[bold cyan]Nanobot Manager - Install[/bold cyan]"))

    # Preflight checks
    if not find_uv():
        err_console.print("[red]Error:[/red] 'uv' not found. Re-run [cyan]sudo ./bootstrap.sh[/cyan] to install it.")
        raise typer.Exit(1)
    if not check_acl_available():
        console.print("[yellow]'setfacl' is not available.[/yellow]")
        from nanomanager.core.proxy import detect_package_manager
        try:
            pm = detect_package_manager()
            if yes or typer.confirm(f"Install 'acl' package via {pm}?", default=True):
                import subprocess
                if pm == "apt-get":
                    subprocess.run(["apt-get", "install", "-y", "acl"], check=True)
                elif pm == "dnf":
                    subprocess.run(["dnf", "install", "-y", "acl"], check=True)
                elif pm == "pacman":
                    subprocess.run(["pacman", "-S", "--noconfirm", "acl"], check=True)
                elif pm == "zypper":
                    subprocess.run(["zypper", "install", "-y", "acl"], check=True)
            else:
                err_console.print("[red]Error:[/red] setfacl is required. Install the 'acl' package.")
                raise typer.Exit(1)
        except RuntimeError:
            err_console.print("[red]Error:[/red] setfacl is required. Install the 'acl' package for your distro.")
            raise typer.Exit(1)

    managing_user = get_current_user()
    console.print(f"Managing user: [bold]{managing_user}[/bold]")
    console.print(f"Proxy: {'[green]enabled[/green]' if not skip_proxy else '[yellow]skipped[/yellow]'}")
    console.print(f"Firewall: {'[green]enabled[/green]' if not skip_firewall else '[yellow]skipped[/yellow]'}")

    if not yes:
        typer.confirm("\nProceed with installation?", abort=True)

    # 1. Create nanobot system user
    console.print("\n[bold]Step 1:[/bold] Creating system user...")
    create_nanobot_user("nanobot")
    add_user_to_group(managing_user, "nanobot")

    # 2. Install nanobot via uv
    console.print("\n[bold]Step 2:[/bold] Installing nanobot-ai...")
    install_nanobot("nanobot")
    lock_install_dirs("nanobot")

    # 3. Set up directories
    console.print("\n[bold]Step 3:[/bold] Setting up directories...")
    setup_nanobot_dirs("/home/nanobot", managing_user=managing_user)

    # 4. Write default config (placeholder — onboard fills in provider/channel)
    console.print("\n[bold]Step 4:[/bold] Writing default config...")
    config = dict(DEFAULT_CONFIG)
    write_config(config, owner_user=managing_user)

    squid_was_preinstalled = False

    # 5. Set up squid proxy
    if not skip_proxy:
        console.print("\n[bold]Step 5:[/bold] Configuring squid proxy...")
        squid_was_preinstalled = check_squid_installed()
        if not squid_was_preinstalled:
            install_squid()
        write_squid_config(PROXY_PORT)
        existing = load_state()
        existing_domains = [d.domain for d in existing.network_domains] if existing else []
        write_domain_allowlist(existing_domains)
        import subprocess
        try:
            subprocess.run(["systemctl", "enable", "--now", "squid"], check=True)
        except Exception:
            pass

    # 6. Set up firewall
    if not skip_firewall:
        console.print("\n[bold]Step 6:[/bold] Applying firewall rules...")
        write_firewall_script("nanobot", PROXY_PORT)
        apply_firewall_rules("nanobot")
        write_firewall_service()

    # 7. Write systemd units
    console.print("\n[bold]Step 7:[/bold] Installing systemd services...")
    write_nanobot_service(
        nanobot_user="nanobot",
        proxy_port=PROXY_PORT,
        proxy_enabled=not skip_proxy,
        firewall_enabled=not skip_firewall,
    )
    daemon_reload()
    if not skip_firewall:
        enable_service("nanomanager-firewall")
    enable_service("nanobot")

    # 8. Save state (preserve existing domains/grants if re-installing)
    existing_state = load_state()
    state = ManagerState(
        managing_user=managing_user,
        install_options=InstallOptions(
            proxy_enabled=not skip_proxy,
            firewall_enabled=not skip_firewall,
            squid_was_preinstalled=squid_was_preinstalled,
            proxy_port=PROXY_PORT,
        ),
        acl_grants=existing_state.acl_grants if existing_state else [],
        network_domains=existing_state.network_domains if existing_state else [],
    )
    save_state(state)

    console.print("\n[bold green]Installation complete![/bold green]")
    console.print("\nNext steps:")
    console.print("  1. [cyan]sudo nanomanager onboard[/cyan]   — configure API key and channels")
    console.print("  2. [cyan]sudo nanomanager start[/cyan]      — start the service")
    console.print("  3. [cyan]sudo nanomanager status[/cyan]     — check service health")


def uninstall(
    keep_data: bool = typer.Option(False, "--keep-data", help="Keep /home/nanobot and config"),
    yes: bool = typer.Option(False, "--yes", "-y", help="Skip confirmation prompt"),
) -> None:
    """Uninstall nanobot and remove sandbox configuration."""
    require_root()

    console.print(Panel.fit("[bold red]Nanobot Manager - Uninstall[/bold red]"))

    if not yes:
        typer.confirm("This will remove nanobot and all related configuration. Proceed?", abort=True)

    state = load_state()

    # Stop and disable services
    console.print("\n[bold]Stopping services...[/bold]")
    for svc in ("nanobot", "nanomanager-firewall"):
        try:
            stop_service(svc)
        except Exception:
            pass
        try:
            disable_service(svc)
        except Exception:
            pass

    # Flush firewall rules
    if state and state.install_options.firewall_enabled:
        console.print("[bold]Flushing firewall rules...[/bold]")
        from nanomanager.core.firewall import flush_firewall_rules
        try:
            flush_firewall_rules("nanobot")
        except Exception:
            pass

    # Restore squid config
    if state and state.install_options.proxy_enabled and not state.install_options.squid_was_preinstalled:
        console.print("[bold]Removing squid configuration...[/bold]")
        from nanomanager.core.proxy import SQUID_CONF_PATH
        backup = SQUID_CONF_PATH.with_suffix(".conf.nanomanager-backup")
        if backup.exists():
            import shutil as sh
            sh.copy2(backup, SQUID_CONF_PATH)
            backup.unlink()
        try:
            import subprocess
            subprocess.run(["systemctl", "restart", "squid"], capture_output=True)
        except Exception:
            pass

    # Remove systemd unit files
    console.print("[bold]Removing systemd units...[/bold]")
    for unit in ("nanobot.service", "nanomanager-firewall.service"):
        unit_path = SYSTEMD_DIR / unit
        if unit_path.exists():
            unit_path.unlink()
    daemon_reload()

    # Remove nanobot user
    console.print("[bold]Removing nanobot user...[/bold]")
    remove_nanobot_user("nanobot", keep_home=keep_data)

    # Remove /etc/nanomanager
    if not keep_data:
        import shutil as sh
        nanomgr_dir = Path("/etc/nanomanager")
        if nanomgr_dir.exists():
            sh.rmtree(nanomgr_dir)
            console.print("[green]Removed /etc/nanomanager[/green]")

    console.print("\n[bold green]Uninstall complete.[/bold green]")
    if keep_data:
        console.print("Note: /home/nanobot data was preserved (--keep-data).")
