"""Named node connection profiles (local RPC, remote RPC, SSH)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from oraculovision.node.client import NodeClient
from oraculovision.node.security import (
    validate_rpc_host,
    validate_safe_path_token,
    validate_ssh_target,
)


@dataclass
class NodeProfile:
    name: str
    cli_path: str = "bitcoin-cli"
    datadir: str = ""
    rpcconnect: str = ""
    rpcport: int | None = None
    rpcuser: str = ""
    rpcpassword: str = ""
    ssh_target: str = ""


def parse_profile(name: str, data: dict[str, Any]) -> NodeProfile:
    rpcport = data.get("rpcport")
    return NodeProfile(
        name=name,
        cli_path=str(data.get("cli_path", "bitcoin-cli")),
        datadir=str(data.get("datadir", "")),
        rpcconnect=validate_rpc_host(str(data.get("rpcconnect", ""))),
        rpcport=int(rpcport) if rpcport not in (None, "") else None,
        rpcuser=validate_safe_path_token(
            str(data.get("rpcuser", "")),
            name="rpcuser",
            allow_empty=True,
        ),
        rpcpassword=validate_safe_path_token(
            str(data.get("rpcpassword", "")),
            name="rpcpassword",
            allow_empty=True,
        ),
        ssh_target=validate_ssh_target(str(data.get("ssh_target", ""))),
    )


def load_profiles(data: dict[str, Any]) -> dict[str, NodeProfile]:
    raw = data.get("profiles") or {}
    profiles: dict[str, NodeProfile] = {}
    if not isinstance(raw, dict):
        return profiles
    for name, section in raw.items():
        if isinstance(section, dict):
            profiles[str(name)] = parse_profile(str(name), section)
    return profiles


def build_client(profile: NodeProfile, *, timeout: float = 30.0) -> NodeClient:
    return NodeClient(
        cli_path=profile.cli_path or None,
        datadir=profile.datadir or None,
        rpcconnect=profile.rpcconnect or None,
        rpcport=profile.rpcport,
        rpcuser=profile.rpcuser or None,
        rpcpassword=profile.rpcpassword or None,
        ssh_target=profile.ssh_target or None,
        timeout=timeout,
    )


def profile_cycle(names: list[str], current: str) -> str:
    if not names:
        return current
    if current not in names:
        return names[0]
    index = names.index(current)
    return names[(index + 1) % len(names)]