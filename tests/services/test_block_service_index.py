"""Tests for BlockService persistent index integration."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock

from oraculovision.analysis.bip110 import BlockAnalysis
from oraculovision.config import BlockIndexConfig
from oraculovision.data.block_index import BlockIndex
from oraculovision.services.block_service import BlockService


def test_fetch_by_height_uses_persistent_cache(tmp_path: Path) -> None:
    client = MagicMock()
    index = BlockIndex(tmp_path / "blocks.db")
    cached = BlockAnalysis(
        height=42,
        hash="c" * 64,
        miner_tag="cached-pool",
        version=1,
        weight=2000,
        tx_count=3,
        bip110_signaling=True,
        spam_score=12,
        status="CLEAN",
    )
    index.put(cached)

    service = BlockService(client, block_index=index)
    result = service.fetch_by_height(42)

    assert result.hash == cached.hash
    assert result.miner_tag == "cached-pool"
    client.get_block_hash.assert_not_called()
    client.get_block.assert_not_called()


def test_block_service_respects_disabled_index_config() -> None:
    service = BlockService(
        MagicMock(),
        block_index_config=BlockIndexConfig(enabled=False),
    )
    assert service._index is None