"""Unit tests for BIP-110 analysis (no node required)."""

from __future__ import annotations

from oraculovision.analysis.bip110 import BlockAnalysis, TxAnalysis, analyze_block


def _minimal_block(txs: list[dict]) -> dict:
    return {
        "height": 100,
        "hash": "a" * 64,
        "version": 0x20000004,
        "weight": 4000,
        "tx": txs,
    }


def test_analyze_block_stores_flagged_raw() -> None:
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
    clean_tx = {
        "txid": "11" * 32,
        "vin": [
            {
                "txid": "bb" * 32,
                "vout": 0,
                "scriptSig": {"asm": "", "hex": ""},
                "sequence": 0xffffffff,
            }
        ],
        "vout": [{"value": 1.0, "n": 0, "scriptPubKey": {"hex": "0014" + "22" * 20}}],
        "weight": 400,
        "vsize": 100,
    }

    block = analyze_block(_minimal_block([coinbase, flagged_tx, clean_tx]))

    assert isinstance(block, BlockAnalysis)
    assert "ff" * 32 in block.flagged_raw
    assert "11" * 32 not in block.flagged_raw
    assert block.flagged_raw["ff" * 32]["txid"] == "ff" * 32


def test_tx_analysis_violation_property() -> None:
    tx = TxAnalysis("aa" * 32, 100, 25, bip110_flags={"large_pushdata"})
    assert tx.has_bip110_violation
    assert not tx.is_spam_signal