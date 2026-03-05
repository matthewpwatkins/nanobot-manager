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

# Nanobot config.json follows this structure:
# {
#   "providers": { "<name>": { "apiKey": "..." } },
#   "agents": { "defaults": { "model": "...", "provider": "..." } },
#   "channels": { "<name>": { "enabled": true, ... } }
# }

DEFAULT_CONFIG: dict = {
    "providers": {},
    "agents": {
        "defaults": {
            "model": "",
            "provider": "",
        },
    },
    "channels": {},
}


def build_config(
    provider: str,
    api_key: str,
    model: str,
    channel: str | None = None,
    channel_config: dict | None = None,
) -> dict:
    config: dict = {
        "providers": {
            provider: {
                "apiKey": api_key,
            },
        },
        "agents": {
            "defaults": {
                "model": model,
                "provider": provider,
            },
        },
        "channels": {},
    }
    if channel and channel_config:
        config["channels"][channel] = {"enabled": True, **channel_config}
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
    if "providers" not in config:
        errors.append("Missing 'providers' section")
    if "agents" not in config:
        errors.append("Missing 'agents' section")
    elif "defaults" not in config.get("agents", {}):
        errors.append("Missing 'agents.defaults' section")
    return errors
