"""Tests for node profile loading and client construction."""

from __future__ import annotations

import pytest

from oraculovision.node.client import NodeClient
from oraculovision.node.profiles import (
    build_client,
    parse_profile,
    profile_cycle,
)
from oraculovision.node.security import validate_ssh_target


def test_parse_profile_remote_rpc() -> None:
    profile = parse_profile(
        "remote",
        {
            "cli_path": "bitcoin-cli",
            "rpcconnect": "10.0.0.5",
            "rpcport": 8332,
            "rpcuser": "rpcuser",
            "rpcpassword": "secret",
        },
    )
    assert profile.name == "remote"
    assert profile.rpcconnect == "10.0.0.5"
    assert profile.rpcport == 8332


def test_profile_cycle_order() -> None:
    names = ["local", "remote", "ssh-node"]
    assert profile_cycle(names, "local") == "remote"
    assert profile_cycle(names, "ssh-node") == "local"


def test_validate_ssh_target_rejects_shell_meta() -> None:
    with pytest.raises(ValueError):
        validate_ssh_target("user@host;rm")


def test_build_client_adds_rpc_and_ssh_flags(monkeypatch) -> None:
    monkeypatch.setattr(
        "oraculovision.node.client.resolve_bitcoin_cli",
        lambda _path: "/usr/bin/bitcoin-cli",
    )
    profile = parse_profile(
        "ssh-node",
        {
            "ssh_target": "miner@node.example.com",
            "rpcconnect": "127.0.0.1",
            "rpcport": 8332,
        },
    )
    client = build_client(profile)
    assert client._base_cmd() == [
        "ssh",
        "miner@node.example.com",
        "--",
        "/usr/bin/bitcoin-cli",
        "-rpcconnect",
        "127.0.0.1",
        "-rpcport",
        "8332",
    ]
    assert "ssh miner@node.example.com" in client.cli_path