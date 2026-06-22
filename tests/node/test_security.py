"""Tests for node security validation."""

from __future__ import annotations

import pytest

from oraculovision.node.addresses import parse_address_query
from oraculovision.node.security import (
    validate_rpc_host,
    validate_rpc_method,
    validate_safe_path_token,
    validate_ssh_target,
    validate_write_rpc_method,
)


def test_validate_rpc_method_rejects_injection() -> None:
    with pytest.raises(ValueError):
        validate_rpc_method("getblock;rm")


def test_write_rpc_allowlist() -> None:
    assert validate_write_rpc_method("setban") == "setban"
    with pytest.raises(ValueError):
        validate_write_rpc_method("stop")


def test_validate_ssh_target() -> None:
    assert validate_ssh_target("user@node.example.com") == "user@node.example.com"
    with pytest.raises(ValueError):
        validate_ssh_target("bad;host")


def test_validate_rpc_host() -> None:
    assert validate_rpc_host("127.0.0.1") == "127.0.0.1"
    with pytest.raises(ValueError):
        validate_rpc_host("host|evil")


def test_safe_path_rejects_shell_meta() -> None:
    with pytest.raises(ValueError):
        validate_safe_path_token("/tmp/evil;rm", name="path", allow_empty=False)


def test_parse_address_query() -> None:
    addr = parse_address_query("bc1qtestaddressxxxxxxxxxxxxxxxxxxxxxx")
    assert addr.startswith("bc1q")