"""Block detail modal markup safety."""

from __future__ import annotations

from oraculovision.analysis.bip110 import analyze_block
from oraculovision.screens.block_detail_modal import BlockDetailModal


def test_hint_text_has_no_nested_markup() -> None:
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
                "scriptSig": {"hex": ""},
                "sequence": 0xffffffff,
            }
        ],
        "vout": [
            {
                "value": 0.0,
                "n": 0,
                "scriptPubKey": {"type": "nulldata", "hex": "6a" + "ff" * 120},
            }
        ],
        "weight": 500,
        "vsize": 125,
    }
    block = analyze_block(
        {
            "height": 1,
            "hash": "a" * 64,
            "version": 4,
            "weight": 1000,
            "tx": [coinbase, flagged_tx],
        }
    )
    modal = BlockDetailModal(block)
    hint = modal._hint_text()
    assert "[/]" not in hint
    assert "[bold]" not in hint
    meta = modal._meta_text()
    assert "Miner:" in meta
    from textual.markup import to_content
    to_content(meta)