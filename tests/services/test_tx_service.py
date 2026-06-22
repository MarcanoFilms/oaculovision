"""Unit tests for transaction inspection service."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from oraculovision.analysis.bip110 import TxAnalysis
from oraculovision.node.client import BitcoinCLIError
from oraculovision.services.tx_service import TxInspectContext, TxQueryError, TxService


def _sample_tx(txid: str) -> dict:
    return {
        "txid": txid,
        "vin": [
            {
                "txid": "bb" * 32,
                "vout": 0,
                "scriptSig": {"hex": ""},
                "prevout": {
                    "value": 1.0,
                    "scriptPubKey": {"address": "bc1qprevoutxxxxxxxxxxxxxxxxxxxxxxx"},
                },
            }
        ],
        "vout": [{"value": 1.0, "n": 0, "scriptPubKey": {"hex": "0014" + "11" * 20}}],
        "weight": 400,
        "vsize": 100,
    }


def test_inspect_uses_cached_raw_tx_without_rpc() -> None:
    txid = "aa" * 32
    client = MagicMock()
    client.get_raw_mempool.side_effect = BitcoinCLIError("mempool unavailable")
    client.get_raw_transaction.side_effect = AssertionError("should not call RPC")

    svc = TxService(client)
    result = svc.inspect_txid(
        txid,
        context=TxInspectContext(
            block_hash="c" * 64,
            block_height=900_000,
            raw_tx=_sample_tx(txid),
        ),
    )

    assert result.txid == txid
    assert not result.partial
    assert result.confirmed
    assert "cache" in (result.source_note or "").lower()


def test_inspect_falls_back_to_partial_cached_analysis() -> None:
    txid = "dd" * 32
    client = MagicMock()
    client.get_raw_mempool.return_value = {}
    client.get_raw_transaction.side_effect = BitcoinCLIError("No such mempool transaction")
    client.get_blockchain_info.return_value = {
        "pruned": True,
        "pruneheight": 800_000,
    }

    cached = TxAnalysis(
        txid,
        900,
        225,
        bip110_flags={"large_pushdata"},
        signals={"inscription"},
    )
    svc = TxService(client)

    result = svc.inspect_txid(
        txid,
        context=TxInspectContext(
            block_hash="e" * 64,
            block_height=900_001,
            cached_analysis=cached,
        ),
    )

    assert result.partial
    assert result.analysis is cached
    assert result.category == "spam"


def test_inspect_includes_flow_with_prevouts() -> None:
    txid = "cc" * 32
    client = MagicMock()
    client.get_raw_mempool.return_value = {}
    client.get_raw_transaction.return_value = {
        "txid": txid,
        "vin": [
            {
                "txid": "dd" * 32,
                "vout": 0,
                "prevout": {
                    "value": 1.0,
                    "scriptPubKey": {
                        "address": "bc1qsenderxxxxxxxxxxxxxxxxxxxxxxxx",
                    },
                },
            }
        ],
        "vout": [
            {
                "n": 0,
                "value": 0.9999,
                "scriptPubKey": {
                    "address": "bc1qrecipientxxxxxxxxxxxxxxxxxxxxxx",
                },
            }
        ],
        "weight": 400,
        "vsize": 100,
    }
    svc = TxService(client)
    result = svc.inspect_txid(txid)
    assert result.flow is not None
    assert result.flow.inputs_resolved
    assert result.flow.fee_btc == pytest.approx(0.0001)
    assert result.fee_btc == pytest.approx(0.0001)


def test_inspect_raises_when_unresolvable() -> None:
    client = MagicMock()
    client.get_raw_mempool.return_value = {}
    client.get_raw_transaction.side_effect = BitcoinCLIError("not found")
    client.get_blockchain_info.return_value = {"pruned": False}

    svc = TxService(client)
    with pytest.raises(TxQueryError, match="not found"):
        svc.inspect_txid("ff" * 32)