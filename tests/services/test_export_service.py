"""Tests for audit export service."""

from __future__ import annotations

import json
from pathlib import Path

from oraculovision.analysis.bip110 import BlockAnalysis, TxAnalysis, analyze_block
from oraculovision.analysis.chain_health import build_chain_health_report
from oraculovision.services.export_service import ExportService
from oraculovision.services.tx_service import TxInspection


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
    return analyze_block(
        {
            "height": 900100,
            "hash": "d" * 64,
            "version": 0x20000004,
            "weight": 4000,
            "tx": [coinbase, flagged_tx],
        }
    )


def test_export_chain_health_writes_json_and_csv(tmp_path: Path) -> None:
    block = _sample_block()
    report = build_chain_health_report([block], tip_height=900100)
    service = ExportService(tmp_path)

    paths = service.export_chain_health(report)

    assert len(paths) == 2
    json_path = next(path for path in paths if path.suffix == ".json")
    csv_path = next(path for path in paths if path.suffix == ".csv")
    payload = json.loads(json_path.read_text())
    assert payload["export_type"] == "chain_health"
    assert payload["report"]["tip_height"] == 900100
    assert csv_path.read_text().startswith("height,hash")


def test_export_block_and_tx(tmp_path: Path) -> None:
    block = _sample_block()
    service = ExportService(tmp_path, write_csv=False)

    block_paths = service.export_block_analysis(block)
    assert len(block_paths) == 1
    block_payload = json.loads(block_paths[0].read_text())
    assert block_payload["block"]["height"] == 900100

    inspection = TxInspection(
        txid="ff" * 32,
        raw={"txid": "ff" * 32},
        analysis=TxAnalysis("ff" * 32, 500, 125, bip110_flags={"large_scriptpubkey"}),
        category="spam",
        confirmed=True,
        block_height=900100,
    )
    tx_paths = service.export_tx_analysis(inspection)
    assert len(tx_paths) == 1
    tx_payload = json.loads(tx_paths[0].read_text())
    assert tx_payload["inspection"]["compliance_label"] == "BIP-110 VIOLATION"