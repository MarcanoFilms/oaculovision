"""Shared block template fetch and analysis cache."""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any

from oraculovision.analysis.mempool_compose import MempoolComposition, analyze_block_template
from oraculovision.data.bitcoin import BitcoinCLI, BitcoinCLIError


@dataclass
class TemplateSnapshot:
    """Cached block template with composition analysis."""

    template: dict[str, Any]
    composition: MempoolComposition
    fetched_at: float = field(default_factory=time.time)
    error: str | None = None


class TemplateService:
    """Fetches GBT once and shares data between Mempool Glass and Block Template."""

    def __init__(self, cli: BitcoinCLI) -> None:
        self.cli = cli
        self._snapshot: TemplateSnapshot | None = None
        self._cache_ttl = 3.0

    def fetch(self, *, force: bool = False) -> TemplateSnapshot:
        now = time.time()
        if (
            not force
            and self._snapshot
            and not self._snapshot.error
            and (now - self._snapshot.fetched_at) < self._cache_ttl
        ):
            return self._snapshot

        try:
            tmpl = self.cli.get_block_template()
            comp = analyze_block_template(
                tmpl,
                self.cli.decode_raw_transaction,
            )
            self._snapshot = TemplateSnapshot(
                template=tmpl,
                composition=comp,
                fetched_at=now,
            )
        except BitcoinCLIError as exc:
            msg = str(exc)
            if exc.hint:
                msg += f" → {exc.hint}"
            self._snapshot = TemplateSnapshot(
                template={},
                composition=MempoolComposition(error=msg),
                fetched_at=now,
                error=msg,
            )
        return self._snapshot

    def invalidate(self) -> None:
        self._snapshot = None