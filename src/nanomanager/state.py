from __future__ import annotations

import os
from datetime import datetime
from pathlib import Path
from typing import Literal

import yaml
from pydantic import BaseModel, Field

STATE_PATH = Path("/etc/nanomanager/state.yaml")


class AclGrant(BaseModel):
    path: str
    mode: Literal["rX", "rwX"]
    granted_at: datetime = Field(default_factory=datetime.now)


class NetworkDomain(BaseModel):
    domain: str
    builtin: bool = False
    added_at: datetime = Field(default_factory=datetime.now)


class InstallOptions(BaseModel):
    proxy_enabled: bool = True
    firewall_enabled: bool = True
    squid_was_preinstalled: bool = False
    proxy_port: int = 3128


class ManagerState(BaseModel):
    installed_at: datetime = Field(default_factory=datetime.now)
    nanobot_user: str = "nanobot"
    managing_user: str = ""
    install_options: InstallOptions = Field(default_factory=InstallOptions)
    acl_grants: list[AclGrant] = Field(default_factory=list)
    network_domains: list[NetworkDomain] = Field(default_factory=list)


def ensure_state_dir() -> None:
    STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
    os.chmod(STATE_PATH.parent, 0o755)


def load_state() -> ManagerState | None:
    if not STATE_PATH.exists():
        return None
    with STATE_PATH.open() as f:
        data = yaml.safe_load(f)
    if data is None:
        return None
    return ManagerState.model_validate(data)


def save_state(state: ManagerState) -> None:
    ensure_state_dir()
    with STATE_PATH.open("w") as f:
        yaml.dump(state.model_dump(mode="json"), f, default_flow_style=False)
    os.chmod(STATE_PATH, 0o600)
