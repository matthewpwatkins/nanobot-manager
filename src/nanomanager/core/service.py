from __future__ import annotations

import subprocess
from pathlib import Path

from jinja2 import Environment, PackageLoader
from rich.console import Console

console = Console(stderr=True)

SYSTEMD_DIR = Path("/etc/systemd/system")


def write_nanobot_service(
    nanobot_user: str = "nanobot",
    proxy_port: int = 3128,
    proxy_enabled: bool = True,
    firewall_enabled: bool = True,
    node_bin_dir: str | None = None,
    enable_display: bool = False,
) -> None:
    env = Environment(loader=PackageLoader("nanomanager", "templates"))
    template = env.get_template("nanobot.service.j2")
    content = template.render(
        nanobot_user=nanobot_user,
        proxy_port=proxy_port,
        proxy_enabled=proxy_enabled,
        firewall_enabled=firewall_enabled,
        node_bin_dir=node_bin_dir,
        enable_display=enable_display,
    )
    unit_path = SYSTEMD_DIR / "nanobot.service"
    unit_path.parent.mkdir(parents=True, exist_ok=True)
    unit_path.write_text(content)
    console.print(f"[green]Wrote {unit_path}[/green]")


def write_firewall_service() -> None:
    env = Environment(loader=PackageLoader("nanomanager", "templates"))
    template = env.get_template("nanomanager-firewall.service.j2")
    content = template.render()
    unit_path = SYSTEMD_DIR / "nanomanager-firewall.service"
    unit_path.parent.mkdir(parents=True, exist_ok=True)
    unit_path.write_text(content)
    console.print(f"[green]Wrote {unit_path}[/green]")


def daemon_reload() -> None:
    subprocess.run(["systemctl", "daemon-reload"], check=True)


def enable_service(name: str) -> None:
    subprocess.run(["systemctl", "enable", name], check=True)
    console.print(f"[green]Enabled {name}.[/green]")


def disable_service(name: str) -> None:
    subprocess.run(["systemctl", "disable", name], check=True)


def start_service(name: str) -> None:
    subprocess.run(["systemctl", "start", name], check=True)
    console.print(f"[green]Started {name}.[/green]")


def stop_service(name: str) -> None:
    subprocess.run(["systemctl", "stop", name], check=True)
    console.print(f"[green]Stopped {name}.[/green]")


def restart_service(name: str) -> None:
    subprocess.run(["systemctl", "restart", name], check=True)
    console.print(f"[green]Restarted {name}.[/green]")


def get_service_status(name: str) -> dict[str, str]:
    properties = ["ActiveState", "SubState", "LoadState", "MainPID", "ExecMainStatus"]
    result = subprocess.run(
        ["systemctl", "show", "--no-pager", f"--property={','.join(properties)}", name],
        capture_output=True,
        text=True,
    )
    status: dict[str, str] = {}
    for line in result.stdout.splitlines():
        if "=" in line:
            key, _, value = line.partition("=")
            status[key] = value
    return status
