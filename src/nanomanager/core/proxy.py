from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

from jinja2 import Environment, PackageLoader
from rich.console import Console

from nanomanager.state import ManagerState, NetworkDomain, save_state

console = Console(stderr=True)

SQUID_CONF_PATH = Path("/etc/squid/squid.conf")
SQUID_ALLOWLIST_PATH = Path("/etc/nanomanager/squid-domains.acl")
PROXY_PORT = 3128


def detect_package_manager() -> str:
    for pm in ("apt-get", "dnf", "pacman", "zypper"):
        if shutil.which(pm):
            return pm
    raise RuntimeError("No supported package manager found (apt-get, dnf, pacman, zypper)")


def check_squid_installed() -> bool:
    return shutil.which("squid") is not None


def install_squid() -> None:
    pm = detect_package_manager()
    console.print(f"[cyan]Installing squid via {pm}...[/cyan]")
    if pm == "apt-get":
        subprocess.run(["apt-get", "install", "-y", "squid"], check=True)
    elif pm == "dnf":
        subprocess.run(["dnf", "install", "-y", "squid"], check=True)
    elif pm == "pacman":
        subprocess.run(["pacman", "-S", "--noconfirm", "squid"], check=True)
    elif pm == "zypper":
        subprocess.run(["zypper", "install", "-y", "squid"], check=True)
    console.print("[green]Squid installed.[/green]")


def write_domain_allowlist(domains: list[str]) -> None:
    SQUID_ALLOWLIST_PATH.parent.mkdir(parents=True, exist_ok=True)
    with SQUID_ALLOWLIST_PATH.open("w") as f:
        for domain in sorted(set(domains)):
            f.write(domain + "\n")


def write_squid_config(proxy_port: int = PROXY_PORT) -> None:
    env = Environment(loader=PackageLoader("nanomanager", "templates"))
    template = env.get_template("squid.conf.j2")
    content = template.render(
        allowlist_path=str(SQUID_ALLOWLIST_PATH),
        proxy_port=proxy_port,
    )
    # Back up original squid.conf if it exists and we haven't already
    backup = SQUID_CONF_PATH.with_suffix(".conf.nanomanager-backup")
    if SQUID_CONF_PATH.exists() and not backup.exists():
        import shutil as sh
        sh.copy2(SQUID_CONF_PATH, backup)
        console.print(f"[cyan]Backed up original squid.conf to {backup}[/cyan]")

    SQUID_CONF_PATH.parent.mkdir(parents=True, exist_ok=True)
    with SQUID_CONF_PATH.open("w") as f:
        f.write(content)
    console.print(f"[green]Wrote squid config to {SQUID_CONF_PATH}[/green]")


def reload_squid() -> None:
    subprocess.run(["systemctl", "reload", "squid"], check=True)


def restart_squid() -> None:
    subprocess.run(["systemctl", "restart", "squid"], check=True)


def add_domain(domain: str, state: ManagerState) -> None:
    existing = {d.domain for d in state.network_domains}
    if domain in existing:
        console.print(f"[yellow]Domain '{domain}' already in allowlist.[/yellow]")
        return
    state.network_domains.append(NetworkDomain(domain=domain))
    save_state(state)
    write_domain_allowlist([d.domain for d in state.network_domains])
    try:
        reload_squid()
    except subprocess.CalledProcessError:
        restart_squid()
    console.print(f"[green]Added '{domain}' to network allowlist.[/green]")


def remove_domain(domain: str, state: ManagerState) -> None:
    original_len = len(state.network_domains)
    state.network_domains = [d for d in state.network_domains if d.domain != domain]
    if len(state.network_domains) == original_len:
        console.print(f"[yellow]Domain '{domain}' not found in allowlist.[/yellow]")
        return
    save_state(state)
    write_domain_allowlist([d.domain for d in state.network_domains])
    try:
        reload_squid()
    except subprocess.CalledProcessError:
        restart_squid()
    console.print(f"[green]Removed '{domain}' from network allowlist.[/green]")
