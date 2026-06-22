"""Export audit trails as JSON and CSV."""

from __future__ import annotations

import csv
import json
from dataclasses import asdict, is_dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from oraculovision.analysis.bip110 import BlockAnalysis, TxAnalysis
from oraculovision.analysis.chain_health import ChainHealthReport
from oraculovision.analysis.tx_flow import TxFlowSummary, TxIO
from oraculovision.services.address_service import AddressInspection
from oraculovision.services.tx_service import TxInspection

_DEFAULT_DIR = Path.home() / ".local" / "share" / "oraculovision" / "exports"


def default_export_dir() -> Path:
    return _DEFAULT_DIR


def _timestamp_slug() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def _sets_to_lists(value: Any) -> Any:
    if isinstance(value, set):
        return sorted(value)
    if isinstance(value, dict):
        return {key: _sets_to_lists(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_sets_to_lists(item) for item in value]
    if is_dataclass(value) and not isinstance(value, type):
        return _sets_to_lists(asdict(value))
    return value


def _tx_dict(tx: TxAnalysis) -> dict[str, Any]:
    return {
        "txid": tx.txid,
        "weight": tx.weight,
        "vsize": tx.vsize,
        "bip110_flags": sorted(tx.bip110_flags),
        "signals": sorted(tx.signals),
        "witness_bytes": tx.witness_bytes,
        "has_bip110_violation": tx.has_bip110_violation,
        "is_spam_signal": tx.is_spam_signal,
    }


def block_to_dict(block: BlockAnalysis) -> dict[str, Any]:
    return {
        "height": block.height,
        "hash": block.hash,
        "miner_tag": block.miner_tag,
        "version": block.version,
        "weight": block.weight,
        "tx_count": block.tx_count,
        "bip110_signaling": block.bip110_signaling,
        "spam_score": block.spam_score,
        "status": block.status,
        "violation_count": block.violation_count,
        "violation_weight": block.violation_weight,
        "inscription_count": block.inscription_count,
        "brc20_count": block.brc20_count,
        "runes_count": block.runes_count,
        "op_return_count": block.op_return_count,
        "large_witness_bytes": block.large_witness_bytes,
        "witness_pct": block.witness_pct,
        "flagged_transactions": [
            _tx_dict(tx)
            for tx in block.transactions
            if tx.has_bip110_violation or tx.is_spam_signal
        ],
    }


def report_to_dict(report: ChainHealthReport) -> dict[str, Any]:
    return {
        "tip_height": report.tip_height,
        "scanned_blocks": report.scanned_blocks,
        "health_score": report.health_score,
        "health_label": report.health_label,
        "avg_spam_score": report.avg_spam_score,
        "median_spam_score": report.median_spam_score,
        "max_spam_score": report.max_spam_score,
        "clean_count": report.clean_count,
        "suspicious_count": report.suspicious_count,
        "violation_count": report.violation_count,
        "bip110_signaling_count": report.bip110_signaling_count,
        "avg_witness_pct": report.avg_witness_pct,
        "total_violation_txs": report.total_violation_txs,
        "timeline": report.timeline,
        "worst_blocks": [block_to_dict(block) for block in report.worst_blocks],
        "error": report.error,
    }


def _io_dict(io: TxIO) -> dict[str, Any]:
    return {
        "index": io.index,
        "address": io.address,
        "display_address": io.display_address,
        "value_btc": io.value_btc,
        "script_type": io.script_type,
        "role": io.role,
        "label": io.label,
    }


def flow_to_dict(flow: TxFlowSummary | None) -> dict[str, Any] | None:
    if flow is None:
        return None
    return {
        "total_input_btc": flow.total_input_btc,
        "total_output_btc": flow.total_output_btc,
        "fee_btc": flow.fee_btc,
        "senders": flow.senders,
        "recipients": flow.recipients,
        "inputs_resolved": flow.inputs_resolved,
        "inputs_partial": flow.inputs_partial,
        "inputs": [_io_dict(io) for io in flow.inputs],
        "outputs": [_io_dict(io) for io in flow.outputs],
    }


def inspection_to_dict(inspection: TxInspection) -> dict[str, Any]:
    return {
        "txid": inspection.txid,
        "category": inspection.category,
        "compliance_label": inspection.compliance_label,
        "in_mempool": inspection.in_mempool,
        "confirmed": inspection.confirmed,
        "block_hash": inspection.block_hash,
        "block_height": inspection.block_height,
        "fee_btc": inspection.fee_btc,
        "fee_rate": inspection.fee_rate,
        "mempool_descendant_count": inspection.mempool_descendant_count,
        "partial": inspection.partial,
        "source_note": inspection.source_note,
        "error": inspection.error,
        "analysis": _tx_dict(inspection.analysis),
        "flow": flow_to_dict(inspection.flow),
    }


def address_inspection_to_dict(inspection: AddressInspection) -> dict[str, Any]:
    return {
        "address": inspection.address,
        "valid": inspection.valid,
        "script_type": inspection.script_type,
        "balance_btc": inspection.balance_btc,
        "utxo_count": inspection.utxo_count,
        "mempool_tx_count": inspection.mempool_tx_count,
        "mempool_pending_btc": inspection.mempool_pending_btc,
        "scan_seconds": inspection.scan_seconds,
        "error": inspection.error,
    }


class ExportService:
    """Write OracleVision audit exports to disk."""

    def __init__(
        self,
        directory: Path | str | None = None,
        *,
        write_json: bool = True,
        write_csv: bool = True,
    ) -> None:
        self.directory = Path(directory) if directory else default_export_dir()
        self.write_json = write_json
        self.write_csv = write_csv

    def _ensure_dir(self) -> Path:
        self.directory.mkdir(parents=True, exist_ok=True)
        return self.directory

    def _write_json(self, stem: str, payload: dict[str, Any]) -> Path:
        path = self._ensure_dir() / f"{stem}.json"
        path.write_text(
            json.dumps(_sets_to_lists(payload), indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        return path

    def _write_csv_rows(self, stem: str, fieldnames: list[str], rows: list[dict[str, Any]]) -> Path:
        path = self._ensure_dir() / f"{stem}.csv"
        with path.open("w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=fieldnames, extrasaction="ignore")
            writer.writeheader()
            for row in rows:
                writer.writerow(row)
        return path

    def export_chain_health(self, report: ChainHealthReport) -> list[Path]:
        if report.error:
            raise ValueError(report.error)
        stem = f"chain_health_{report.tip_height}_{_timestamp_slug()}"
        paths: list[Path] = []
        payload = {
            "export_type": "chain_health",
            "exported_at": _timestamp_slug(),
            "report": report_to_dict(report),
        }
        if self.write_json:
            paths.append(self._write_json(stem, payload))
        if self.write_csv:
            rows = [
                {
                    "height": block.height,
                    "hash": block.hash,
                    "miner_tag": block.miner_tag,
                    "spam_score": block.spam_score,
                    "status": block.status,
                    "violation_count": block.violation_count,
                    "witness_pct": round(block.witness_pct, 2),
                    "bip110_signaling": block.bip110_signaling,
                }
                for block in report.worst_blocks
            ]
            paths.append(
                self._write_csv_rows(
                    stem,
                    [
                        "height",
                        "hash",
                        "miner_tag",
                        "spam_score",
                        "status",
                        "violation_count",
                        "witness_pct",
                        "bip110_signaling",
                    ],
                    rows,
                )
            )
        return paths

    def export_block_analysis(self, block: BlockAnalysis) -> list[Path]:
        stem = f"block_{block.height}_{_timestamp_slug()}"
        paths: list[Path] = []
        payload = {
            "export_type": "block",
            "exported_at": _timestamp_slug(),
            "block": block_to_dict(block),
        }
        if self.write_json:
            paths.append(self._write_json(stem, payload))
        if self.write_csv:
            rows = [
                {
                    "txid": tx.txid,
                    "vsize": tx.vsize,
                    "bip110_flags": ",".join(sorted(tx.bip110_flags)),
                    "signals": ",".join(sorted(tx.signals)),
                    "witness_bytes": tx.witness_bytes,
                }
                for tx in block.transactions
                if tx.has_bip110_violation or tx.is_spam_signal
            ]
            paths.append(
                self._write_csv_rows(
                    stem,
                    ["txid", "vsize", "bip110_flags", "signals", "witness_bytes"],
                    rows,
                )
            )
        return paths

    def export_tx_analysis(self, inspection: TxInspection) -> list[Path]:
        if inspection.error:
            raise ValueError(inspection.error)
        stem = f"tx_{inspection.txid[:16]}_{_timestamp_slug()}"
        paths: list[Path] = []
        payload = {
            "export_type": "transaction",
            "exported_at": _timestamp_slug(),
            "inspection": inspection_to_dict(inspection),
        }
        if self.write_json:
            paths.append(self._write_json(stem, payload))
        if self.write_csv:
            analysis = inspection.analysis
            rows = [
                {
                    "txid": inspection.txid,
                    "category": inspection.category,
                    "compliance_label": inspection.compliance_label,
                    "confirmed": inspection.confirmed,
                    "in_mempool": inspection.in_mempool,
                    "block_height": inspection.block_height or "",
                    "fee_rate": inspection.fee_rate or "",
                    "bip110_flags": ",".join(sorted(analysis.bip110_flags)),
                    "signals": ",".join(sorted(analysis.signals)),
                }
            ]
            paths.append(
                self._write_csv_rows(
                    stem,
                    [
                        "txid",
                        "category",
                        "compliance_label",
                        "confirmed",
                        "in_mempool",
                        "block_height",
                        "fee_rate",
                        "bip110_flags",
                        "signals",
                    ],
                    rows,
                )
            )
        return paths

    def export_address_analysis(self, inspection: AddressInspection) -> list[Path]:
        if inspection.error:
            raise ValueError(inspection.error)
        stem = f"address_{inspection.address[:16]}_{_timestamp_slug()}"
        paths: list[Path] = []
        payload = {
            "export_type": "address",
            "exported_at": _timestamp_slug(),
            "inspection": address_inspection_to_dict(inspection),
        }
        if self.write_json:
            paths.append(self._write_json(stem, payload))
        if self.write_csv:
            rows = [
                {
                    "address": inspection.address,
                    "valid": inspection.valid,
                    "balance_btc": inspection.balance_btc,
                    "utxo_count": inspection.utxo_count,
                    "mempool_tx_count": inspection.mempool_tx_count,
                    "mempool_pending_btc": inspection.mempool_pending_btc,
                }
            ]
            paths.append(
                self._write_csv_rows(
                    stem,
                    [
                        "address",
                        "valid",
                        "balance_btc",
                        "utxo_count",
                        "mempool_tx_count",
                        "mempool_pending_btc",
                    ],
                    rows,
                )
            )
        return paths