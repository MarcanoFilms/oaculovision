"""Block fetch, lookup, and analysis cache."""

from __future__ import annotations

import re
from pathlib import Path

from oraculovision.analysis.bip110 import BlockAnalysis, analyze_block
from oraculovision.config import BlockIndexConfig
from oraculovision.data.block_index import BlockIndex, default_index_path
from oraculovision.node.client import BitcoinCLIError, NodeClient

_HASH_RE = re.compile(r"^[0-9a-f]{64}$")


class BlockQueryError(ValueError):
    """Invalid or unresolvable block query."""


def parse_block_query(raw: str) -> tuple[str, int | str]:
    """Parse user input into (kind, value) where kind is 'height' or 'hash'."""
    text = (raw or "").strip().lower()
    if not text:
        raise BlockQueryError("Enter a block height or 64-character block hash")

    if text.isdigit():
        height = int(text)
        if height < 0:
            raise BlockQueryError("Block height must be non-negative")
        return "height", height

    if _HASH_RE.fullmatch(text):
        return "hash", text

    raise BlockQueryError(
        "Invalid query — use a block height (e.g. 954724) "
        "or full 64-char hex hash"
    )


def _build_block_index(config: BlockIndexConfig | None) -> BlockIndex | None:
    if config is None or not config.enabled:
        return None
    path = Path(config.path) if config.path else default_index_path()
    return BlockIndex(path, max_entries=config.max_entries)


class BlockService:
    """Fetch and analyze blocks via the local node."""

    def __init__(
        self,
        client: NodeClient,
        *,
        cache_size: int = 128,
        block_index: BlockIndex | None = None,
        block_index_config: BlockIndexConfig | None = None,
    ) -> None:
        self.client = client
        self._cache: dict[str, BlockAnalysis] = {}
        self._cache_size = cache_size
        self._index = block_index or _build_block_index(block_index_config)

    def _store(self, analysis: BlockAnalysis) -> BlockAnalysis:
        if len(self._cache) >= self._cache_size:
            # Drop an arbitrary oldest entry (simple bounded cache).
            self._cache.pop(next(iter(self._cache)))
        self._cache[analysis.hash] = analysis
        if self._index is not None:
            self._index.put(analysis)
        return analysis

    def _from_persistent(self, block_hash: str | None = None, *, height: int | None = None) -> BlockAnalysis | None:
        if self._index is None:
            return None
        if block_hash:
            cached = self._index.get(block_hash)
        elif height is not None:
            cached = self._index.get_by_height(height)
        else:
            return None
        if cached is not None:
            self._cache[cached.hash] = cached
        return cached

    def analyze_raw_block(self, block: dict) -> BlockAnalysis:
        analysis = analyze_block(block)
        return self._store(analysis)

    def fetch_by_height(self, height: int) -> BlockAnalysis:
        cached = self._from_persistent(height=height)
        if cached is not None:
            return cached

        try:
            block_hash = self.client.get_block_hash(height)
        except BitcoinCLIError as exc:
            raise BlockQueryError(str(exc)) from exc

        if block_hash in self._cache:
            return self._cache[block_hash]

        cached = self._from_persistent(block_hash=block_hash)
        if cached is not None:
            return cached

        try:
            block = self.client.get_block(block_hash, 2)
        except BitcoinCLIError as exc:
            raise BlockQueryError(str(exc)) from exc

        return self.analyze_raw_block(block)

    def fetch_by_hash(self, block_hash: str) -> BlockAnalysis:
        block_hash = block_hash.lower()
        if block_hash in self._cache:
            return self._cache[block_hash]

        cached = self._from_persistent(block_hash=block_hash)
        if cached is not None:
            return cached

        try:
            block = self.client.get_block(block_hash, 2)
        except BitcoinCLIError as exc:
            raise BlockQueryError(str(exc)) from exc

        return self.analyze_raw_block(block)

    def fetch_query(self, raw: str) -> BlockAnalysis:
        kind, value = parse_block_query(raw)
        if kind == "height":
            tip = self.client.get_block_count()
            if int(value) > tip:
                raise BlockQueryError(
                    f"Height {value} is above chain tip ({tip})"
                )
            return self.fetch_by_height(int(value))
        return self.fetch_by_hash(str(value))

    def fetch_recent(self, count: int = 25) -> list[BlockAnalysis]:
        tip_height = self.client.get_block_count()
        analyses: list[BlockAnalysis] = []
        for height in range(tip_height, max(tip_height - count, -1), -1):
            analyses.append(self.fetch_by_height(height))
        return analyses