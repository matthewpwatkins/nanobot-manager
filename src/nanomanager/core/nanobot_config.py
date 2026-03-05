from __future__ import annotations

import json
import os
from pathlib import Path

from rich.console import Console

console = Console(stderr=True)

CONFIG_PATH = Path("/home/nanobot/.nanobot/config.json")

PROVIDER_DOMAINS: dict[str, list[str]] = {
    "anthropic": ["api.anthropic.com"],
    "openai": ["api.openai.com"],
    "openrouter": ["openrouter.ai"],
    "deepseek": ["api.deepseek.com"],
    "groq": ["api.groq.com"],
    "gemini": ["generativelanguage.googleapis.com"],
}

CHANNEL_DOMAINS: dict[str, list[str]] = {
    "slack": ["slack.com"],
    "discord": ["discord.com", "gateway.discord.gg"],
    "telegram": ["api.telegram.org"],
}

DEFAULT_CONFIG: dict = {
    "restrictToWorkspace": True,
    "mcpServers": {},
}


def set_proxy_in_config(config: dict, proxy_port: int = 3128) -> dict:
    config["httpProxy"] = f"http://127.0.0.1:{proxy_port}"
    config["httpsProxy"] = f"http://127.0.0.1:{proxy_port}"
    return config


def read_config(path: Path = CONFIG_PATH) -> dict:
    with path.open() as f:
        return json.load(f)


def write_config(
    config: dict,
    path: Path = CONFIG_PATH,
    owner_user: str | None = None,
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w") as f:
        json.dump(config, f, indent=2)
        f.write("\n")

    import pwd
    nanobot_gid = pwd.getpwnam("nanobot").pw_gid

    if owner_user:
        try:
            owner_uid = pwd.getpwnam(owner_user).pw_uid
        except KeyError:
            owner_uid = 0
    else:
        owner_uid = 0

    os.chown(path, owner_uid, nanobot_gid)
    os.chmod(path, 0o640)
    console.print(f"[green]Wrote config to {path}[/green]")


def validate_config(config: dict) -> list[str]:
    errors: list[str] = []
    if not isinstance(config, dict):
        errors.append("Config must be a JSON object")
        return errors
    if not config.get("restrictToWorkspace", False):
        errors.append("restrictToWorkspace must be true")
    return errors
