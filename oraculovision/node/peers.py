"""Peer address helpers for control actions."""

from __future__ import annotations

from typing import Any


def peer_address(peer: dict[str, Any]) -> str:
    """Return the connection address used by disconnectnode."""
    return str(peer.get("addr") or peer.get("address") or "")


def peer_ban_subnet(addr: str) -> str:
    """Derive a single-host ban subnet from a host:port address."""
    host = addr.rsplit(":", 1)[0].strip()
    if not host:
        raise ValueError(f"Invalid peer address: {addr!r}")
    # IPv6 literals contain multiple colons.
    if host.count(":") > 1:
        return f"{host}/128"
    return f"{host}/32"


def peer_direction(peer: dict[str, Any]) -> str:
    return "in" if peer.get("inbound") else "out"


def peer_client(peer: dict[str, Any]) -> str:
    subver = str(peer.get("subver", ""))
    if subver.startswith("/") and subver.endswith("/"):
        subver = subver[1:-1]
    return subver[:28] or "?"


def peer_height(peer: dict[str, Any]) -> str:
    synced = peer.get("synced_headers")
    start = peer.get("startingheight")
    if synced is not None:
        return str(synced)
    if start is not None:
        return str(start)
    return "?"