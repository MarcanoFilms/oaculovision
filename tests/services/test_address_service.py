"""Tests for address inspection service."""

from __future__ import annotations

from unittest.mock import MagicMock

from oraculovision.node.client import BitcoinCLIError
from oraculovision.services.address_service import AddressService


def test_inspect_address_balance_and_mempool() -> None:
    client = MagicMock()
    client.validate_address.return_value = {
        "isvalid": True,
        "witness_v0_keyhash": True,
    }
    client.scantxoutset_address.return_value = {
        "total_amount": 0.25,
        "unspents": [{"txid": "a" * 64, "vout": 0}],
    }
    client.get_raw_mempool.return_value = ["tx1"]
    client.get_raw_transaction.return_value = {
        "vout": [
            {
                "value": 0.01,
                "scriptPubKey": {
                    "address": "bc1qtestaddressxxxxxxxxxxxxxxxxxxxxxx",
                },
            }
        ]
    }

    svc = AddressService(client)
    result = svc.inspect_address("bc1qtestaddressxxxxxxxxxxxxxxxxxxxxxx")

    assert result.valid
    assert result.balance_btc == 0.25
    assert result.utxo_count == 1


def test_inspect_invalid_address() -> None:
    client = MagicMock()
    client.validate_address.return_value = {"isvalid": False}
    svc = AddressService(client)
    result = svc.inspect_address("bc1qtestaddressxxxxxxxxxxxxxxxxxxxxxx")
    assert not result.valid
    assert result.error


def test_scantxoutset_failure_surfaces_error() -> None:
    client = MagicMock()
    client.validate_address.return_value = {"isvalid": True}
    client.scantxoutset_address.side_effect = BitcoinCLIError("scan failed")
    svc = AddressService(client)
    result = svc.inspect_address("bc1qtestaddressxxxxxxxxxxxxxxxxxxxxxx")
    assert result.error