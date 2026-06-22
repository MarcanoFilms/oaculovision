"""Tests for pluggable transaction detectors."""

from __future__ import annotations

from oraculovision.analysis.bip110 import analyze_transaction
from oraculovision.analysis.detectors import configure_detectors, run_detectors


def test_builtin_detector_matches_large_op_return() -> None:
    configure_detectors(["builtin"])
    tx = {
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
    analysis = analyze_transaction(tx)
    assert "large_scriptpubkey" in analysis.bip110_flags
    assert analysis.has_bip110_violation


def test_dust_detector_flags_small_outputs() -> None:
    configure_detectors(["builtin", "example_dust"])
    tx = {
        "txid": "dd" * 32,
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
                "value": 0.000001,
                "n": 0,
                "scriptPubKey": {"hex": "0014" + "22" * 20},
            }
        ],
        "weight": 200,
        "vsize": 50,
    }
    result = run_detectors(tx)
    assert "dust" in result.signals


def test_dust_detector_disabled_by_default_config() -> None:
    configure_detectors(["builtin"])
    tx = {
        "txid": "dd" * 32,
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
                "value": 0.000001,
                "n": 0,
                "scriptPubKey": {"hex": "0014" + "22" * 20},
            }
        ],
        "weight": 200,
        "vsize": 50,
    }
    analysis = analyze_transaction(tx)
    assert "dust" not in analysis.signals