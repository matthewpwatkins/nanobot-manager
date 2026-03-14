from __future__ import annotations

import typer

from nanomanager.cli import access, config_cmd, mcp, network
from nanomanager.cli import install as install_mod
from nanomanager.cli import onboard as onboard_mod
from nanomanager.cli import service as service_mod
from nanomanager.cli import update as update_mod

app = typer.Typer(
    name="nanomanager",
    help="Nanobot AI assistant manager - hardened sandbox management",
    no_args_is_help=True,
)

# Service lifecycle
app.command("install")(install_mod.install)
app.command("uninstall")(install_mod.uninstall)
app.command("onboard")(onboard_mod.onboard)
app.command("start")(service_mod.start)
app.command("stop")(service_mod.stop)
app.command("restart")(service_mod.restart)
app.command("status")(service_mod.status)
app.command("logs")(service_mod.logs)
app.command("update")(update_mod.update)

# Sub-apps
app.add_typer(access.app, name="access")
app.add_typer(network.app, name="network-lock")
app.add_typer(config_cmd.app, name="config")
app.add_typer(mcp.app, name="mcp")

if __name__ == "__main__":
    app()
