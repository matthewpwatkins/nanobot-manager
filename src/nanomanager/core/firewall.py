from __future__ import annotations

import os
import stat
import subprocess
from pathlib import Path

from jinja2 import Environment, PackageLoader
from rich.console import Console

console = Console(stderr=True)

FIREWALL_SCRIPT_PATH = Path("/etc/nanomanager/apply-firewall.sh")


def get_nanobot_uid(username: str = "nanobot") -> int:
    import pwd
    return pwd.getpwnam(username).pw_uid


def write_firewall_script(nanobot_user: str = "nanobot", proxy_port: int = 3128) -> None:
    uid = get_nanobot_uid(nanobot_user)
    env = Environment(loader=PackageLoader("nanomanager", "templates"))
    template = env.get_template("nanomanager-apply-fw.sh.j2")
    content = template.render(nanobot_uid=uid, proxy_port=proxy_port)

    FIREWALL_SCRIPT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with FIREWALL_SCRIPT_PATH.open("w") as f:
        f.write(content)
    os.chmod(FIREWALL_SCRIPT_PATH, stat.S_IRWXU | stat.S_IRGRP | stat.S_IXGRP | stat.S_IROTH | stat.S_IXOTH)
    console.print(f"[green]Wrote firewall script to {FIREWALL_SCRIPT_PATH}[/green]")


def apply_firewall_rules(nanobot_user: str = "nanobot") -> None:
    subprocess.run([str(FIREWALL_SCRIPT_PATH), "apply"], check=True)
    console.print("[green]Firewall rules applied.[/green]")


def flush_firewall_rules(nanobot_user: str = "nanobot") -> None:
    if not FIREWALL_SCRIPT_PATH.exists():
        # Try to flush by UID directly
        try:
            uid = get_nanobot_uid(nanobot_user)
            subprocess.run(
                ["iptables", "-t", "filter", "-D", "OUTPUT", "-m", "owner",
                 "--uid-owner", str(uid), "-j", "nanobot_output"],
                capture_output=True,
            )
            subprocess.run(["iptables", "-t", "filter", "-F", "nanobot_output"], capture_output=True)
            subprocess.run(["iptables", "-t", "filter", "-X", "nanobot_output"], capture_output=True)
        except Exception:
            pass
        return
    subprocess.run([str(FIREWALL_SCRIPT_PATH), "flush"], check=True)
    console.print("[green]Firewall rules flushed.[/green]")
