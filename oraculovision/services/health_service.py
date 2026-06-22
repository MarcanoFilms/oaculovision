"""Chain health scanning service."""

from __future__ import annotations

from oraculovision.analysis.bip110 import BlockAnalysis
from oraculovision.analysis.chain_health import ChainHealthReport, build_chain_health_report
from oraculovision.node.client import BitcoinCLIError, NodeClient
from oraculovision.services.block_service import BlockService


class HealthService:
    """Scan recent blocks and produce chain health reports."""

    def __init__(
        self,
        client: NodeClient,
        block_service: BlockService | None = None,
        *,
        default_scan_depth: int = 48,
    ) -> None:
        self.client = client
        self.block_service = block_service or BlockService(client)
        self.default_scan_depth = default_scan_depth
        self._last_report: ChainHealthReport | None = None
        self._last_tip: int | None = None

    def scan(
        self,
        depth: int | None = None,
        *,
        force: bool = False,
    ) -> ChainHealthReport:
        """Analyze the last ``depth`` blocks and return a health report."""
        depth = depth or self.default_scan_depth
        depth = max(1, min(depth, 144))  # cap at ~1 day of blocks

        try:
            tip = self.client.get_block_count()
            chain = self.client.get_blockchain_info()
            if chain.get("pruned"):
                prune_h = int(chain.get("pruneheight", 0) or 0)
                available = max(1, tip - prune_h + 1)
                depth = min(depth, available)
        except BitcoinCLIError as exc:
            return ChainHealthReport(error=str(exc))

        if (
            not force
            and self._last_report
            and not self._last_report.error
            and self._last_tip == tip
            and self._last_report.scanned_blocks == depth
        ):
            return self._last_report

        try:
            blocks = self.block_service.fetch_recent(depth)
        except BitcoinCLIError as exc:
            return ChainHealthReport(tip_height=tip, error=str(exc))

        report = build_chain_health_report(blocks, tip_height=tip)
        self._last_report = report
        self._last_tip = tip
        return report

    def get_block_for_row(self, height: str, report: ChainHealthReport) -> BlockAnalysis | None:
        for block in report.worst_blocks:
            if str(block.height) == height:
                return block
        return None