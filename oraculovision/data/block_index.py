"""Persistent SQLite cache for analyzed block summaries."""

from __future__ import annotations

import json
import sqlite3
import threading
import time
from pathlib import Path
from typing import Any

from oraculovision.analysis.bip110 import BlockAnalysis, TxAnalysis

_DEFAULT_DIR = Path.home() / ".local" / "share" / "oraculovision"
_SCHEMA = """
CREATE TABLE IF NOT EXISTS blocks (
    hash TEXT PRIMARY KEY,
    height INTEGER NOT NULL,
    miner_tag TEXT NOT NULL,
    spam_score INTEGER NOT NULL,
    status TEXT NOT NULL,
    violation_count INTEGER NOT NULL,
    tx_count INTEGER NOT NULL,
    analyzed_at REAL NOT NULL,
    summary_json TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_blocks_height ON blocks(height);
CREATE INDEX IF NOT EXISTS idx_blocks_analyzed ON blocks(analyzed_at);
"""


def default_index_path() -> Path:
    return _DEFAULT_DIR / "block_index.db"


def _tx_to_dict(tx: TxAnalysis) -> dict[str, Any]:
    return {
        "txid": tx.txid,
        "weight": tx.weight,
        "vsize": tx.vsize,
        "bip110_flags": sorted(tx.bip110_flags),
        "signals": sorted(tx.signals),
        "witness_bytes": tx.witness_bytes,
    }


def _tx_from_dict(data: dict[str, Any]) -> TxAnalysis:
    return TxAnalysis(
        txid=str(data.get("txid", "")),
        weight=int(data.get("weight", 0)),
        vsize=int(data.get("vsize", 0)),
        bip110_flags=set(data.get("bip110_flags") or []),
        signals=set(data.get("signals") or []),
        witness_bytes=int(data.get("witness_bytes", 0)),
    )


def _summary_from_analysis(analysis: BlockAnalysis) -> dict[str, Any]:
    return {
        "version": analysis.version,
        "weight": analysis.weight,
        "bip110_signaling": analysis.bip110_signaling,
        "violation_weight": analysis.violation_weight,
        "inscription_count": analysis.inscription_count,
        "brc20_count": analysis.brc20_count,
        "runes_count": analysis.runes_count,
        "op_return_count": analysis.op_return_count,
        "large_witness_bytes": analysis.large_witness_bytes,
        "witness_pct": analysis.witness_pct,
        "transactions": [_tx_to_dict(tx) for tx in analysis.transactions],
    }


def _analysis_from_row(row: sqlite3.Row) -> BlockAnalysis:
    summary = json.loads(row["summary_json"])
    transactions = [
        _tx_from_dict(item) for item in summary.get("transactions", [])
    ]
    return BlockAnalysis(
        height=int(row["height"]),
        hash=str(row["hash"]),
        miner_tag=str(row["miner_tag"]),
        version=int(summary.get("version", 0)),
        weight=int(summary.get("weight", 0)),
        tx_count=int(row["tx_count"]),
        bip110_signaling=bool(summary.get("bip110_signaling", False)),
        spam_score=int(row["spam_score"]),
        status=str(row["status"]),
        violation_count=int(row["violation_count"]),
        violation_weight=int(summary.get("violation_weight", 0)),
        inscription_count=int(summary.get("inscription_count", 0)),
        brc20_count=int(summary.get("brc20_count", 0)),
        runes_count=int(summary.get("runes_count", 0)),
        op_return_count=int(summary.get("op_return_count", 0)),
        large_witness_bytes=int(summary.get("large_witness_bytes", 0)),
        witness_pct=float(summary.get("witness_pct", 0.0)),
        transactions=transactions,
        flagged_raw={},
    )


class BlockIndex:
    """Disk-backed index of block analysis summaries."""

    def __init__(
        self,
        path: Path | str | None = None,
        *,
        max_entries: int = 5000,
    ) -> None:
        self.path = Path(path) if path else default_index_path()
        self.max_entries = max(1, max_entries)
        self._lock = threading.Lock()
        self._conn: sqlite3.Connection | None = None

    def _connect(self) -> sqlite3.Connection:
        if self._conn is None:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            conn = sqlite3.connect(self.path, check_same_thread=False)
            conn.row_factory = sqlite3.Row
            conn.execute("PRAGMA journal_mode=WAL")
            conn.executescript(_SCHEMA)
            self._conn = conn
        return self._conn

    def close(self) -> None:
        with self._lock:
            if self._conn is not None:
                self._conn.close()
                self._conn = None

    def get(self, block_hash: str) -> BlockAnalysis | None:
        block_hash = block_hash.lower()
        with self._lock:
            conn = self._connect()
            row = conn.execute(
                "SELECT * FROM blocks WHERE hash = ?",
                (block_hash,),
            ).fetchone()
        if row is None:
            return None
        return _analysis_from_row(row)

    def get_by_height(self, height: int) -> BlockAnalysis | None:
        with self._lock:
            conn = self._connect()
            row = conn.execute(
                "SELECT * FROM blocks WHERE height = ? ORDER BY analyzed_at DESC LIMIT 1",
                (height,),
            ).fetchone()
        if row is None:
            return None
        return _analysis_from_row(row)

    def put(self, analysis: BlockAnalysis) -> None:
        summary = _summary_from_analysis(analysis)
        payload = (
            analysis.hash.lower(),
            analysis.height,
            analysis.miner_tag,
            analysis.spam_score,
            analysis.status,
            analysis.violation_count,
            analysis.tx_count,
            time.time(),
            json.dumps(summary, separators=(",", ":")),
        )
        with self._lock:
            conn = self._connect()
            conn.execute(
                """
                INSERT INTO blocks (
                    hash, height, miner_tag, spam_score, status,
                    violation_count, tx_count, analyzed_at, summary_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(hash) DO UPDATE SET
                    height = excluded.height,
                    miner_tag = excluded.miner_tag,
                    spam_score = excluded.spam_score,
                    status = excluded.status,
                    violation_count = excluded.violation_count,
                    tx_count = excluded.tx_count,
                    analyzed_at = excluded.analyzed_at,
                    summary_json = excluded.summary_json
                """,
                payload,
            )
            conn.commit()
            self._prune_locked(conn)

    def recent(self, limit: int) -> list[BlockAnalysis]:
        limit = max(1, limit)
        with self._lock:
            conn = self._connect()
            rows = conn.execute(
                "SELECT * FROM blocks ORDER BY height DESC LIMIT ?",
                (limit,),
            ).fetchall()
        return [_analysis_from_row(row) for row in rows]

    def count(self) -> int:
        with self._lock:
            conn = self._connect()
            row = conn.execute("SELECT COUNT(*) AS c FROM blocks").fetchone()
        return int(row["c"]) if row else 0

    def _prune_locked(self, conn: sqlite3.Connection) -> None:
        total = conn.execute("SELECT COUNT(*) AS c FROM blocks").fetchone()
        if not total or int(total["c"]) <= self.max_entries:
            return
        overflow = int(total["c"]) - self.max_entries
        conn.execute(
            """
            DELETE FROM blocks
            WHERE hash IN (
                SELECT hash FROM blocks
                ORDER BY analyzed_at ASC
                LIMIT ?
            )
            """,
            (overflow,),
        )
        conn.commit()

    def prune(self) -> None:
        with self._lock:
            conn = self._connect()
            self._prune_locked(conn)