"""Tests for persistent block index cache."""

from __future__ import annotations

from pathlib import Path

from oraculovision.analysis.bip110 import BlockAnalysis, TxAnalysis, analyze_block
from oraculovision.data.block_index import BlockIndex


def _sample_block() -> BlockAnalysis:
    coinbase = {
        "txid": "cb" * 32,
        "vin": [{"coinbase": "00", "sequence": 0xffffffff}],
        "vout": [],
        "weight": 100,
        "vsize": 25,
    }
    flagged_tx = {
        "txid": "ff" * 32,
        "vin": [
            {
                "txid": "aa" * 32,
                "vout": 0,
                "scriptSig": {"asm": "", "hex": ""},
                "sequence": 0xffffffff,
            }
        ],
        "vout": [
            {
                "value": 0.0,
                "n": 0,
                "scriptPubKey": {
                    "type": "nulldata",
                    "hex": "6a" + "ff" * 120,
                },
            }
        ],
        "weight": 500,
        "vsize": 125,
    }
    block = {
        "height": 800001,
        "hash": "b" * 64,
        "version": 0x20000004,
        "weight": 4000,
        "tx": [coinbase, flagged_tx],
    }
    return analyze_block(block)


def test_block_index_round_trip(tmp_path: Path) -> None:
    index = BlockIndex(tmp_path / "blocks.db", max_entries=100)
    original = _sample_block()

    index.put(original)
    by_hash = index.get(original.hash)
    by_height = index.get_by_height(original.height)

    assert by_hash is not None
    assert by_height is not None
    assert by_hash.hash == original.hash
    assert by_hash.height == original.height
    assert by_hash.spam_score == original.spam_score
    assert by_hash.violation_count == original.violation_count
    assert len(by_hash.transactions) == len(original.transactions)
    assert by_hash.transactions[0].txid == original.transactions[0].txid
    assert by_hash.flagged_raw == {}


def test_block_index_prune(tmp_path: Path) -> None:
    index = BlockIndex(tmp_path / "blocks.db", max_entries=2)

    for height in (1, 2, 3):
        analysis = BlockAnalysis(
            height=height,
            hash=f"{height:064x}",
            miner_tag="pool",
            version=1,
            weight=1000,
            tx_count=1,
            bip110_signaling=False,
            transactions=[
                TxAnalysis("aa" * 32, 100, 25, bip110_flags={"large_pushdata"}),
            ],
        )
        index.put(analysis)

    assert index.count() == 2
    assert index.get_by_height(1) is None
    assert index.get_by_height(2) is not None
    assert index.get_by_height(3) is not None


def test_block_index_recent_order(tmp_path: Path) -> None:
    index = BlockIndex(tmp_path / "blocks.db", max_entries=10)

    for height in (10, 11, 12):
        index.put(
            BlockAnalysis(
                height=height,
                hash=f"{height:064x}",
                miner_tag="pool",
                version=1,
                weight=1000,
                tx_count=0,
                bip110_signaling=False,
            )
        )

    recent = index.recent(2)
    assert [block.height for block in recent] == [12, 11]