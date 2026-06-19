"""Node status widget — real-time Knots/Core metrics."""

from __future__ import annotations

import time

from textual.app import ComposeResult
from textual.containers import Vertical
from textual.widgets import Label, Static

from oraculovision.config import AppConfig, BitcoinConfig
from oraculovision.data.bitcoin import BitcoinCLI, BitcoinCLIError


class NodeStatus(Static):
    """Displays live node sync, peers, mempool, UTXO set, and alerts."""

    DEFAULT_CSS = """
    NodeStatus {
        height: auto;
        border: solid #ffd700;
        padding: 1 2;
    }
    NodeStatus .metric { color: #e0e0e0; }
    NodeStatus .error { color: #ff6b6b; }
    NodeStatus .ok { color: #3dd68c; }
    NodeStatus .alert-line { color: #ff6b6b; text-style: bold; }
    NodeStatus.alert-peers { border: solid #ff6b6b; }
    NodeStatus.alert-mempool { border: solid #ffd700; }
    """

    def __init__(
        self,
        cli: BitcoinCLI | None = None,
        config: AppConfig | None = None,
        **kwargs,
    ) -> None:
        super().__init__(**kwargs)
        self.config = config or AppConfig()
        self.cli = cli or BitcoinCLI()
        self.border_title = "NODE STATUS"
        self._utxo_cache: dict | None = None
        self._utxo_fetched_at: float = 0.0
        self._prev_utxo_count: int | None = None
        self.alert_peers: bool = False
        self.alert_mempool: bool = False
        self.alert_message: str = ""

    def compose(self) -> ComposeResult:
        with Vertical():
            yield Label("", id="alert-line", classes="alert-line")
            yield Label("Loading...", id="node-content", classes="metric")

    def refresh_data(self) -> None:
        label = self.query_one("#node-content", Label)
        alert_line = self.query_one("#alert-line", Label)
        alerts = self.config.alerts

        try:
            chain = self.cli.get_blockchain_info()
            network = self.cli.get_network_info()
            mempool = self.cli.get_mempool_info()
        except BitcoinCLIError as exc:
            msg = str(exc)
            if exc.hint:
                msg += f"\n→ {exc.hint}"
            label.update(msg)
            label.remove_class("ok")
            label.add_class("error")
            alert_line.update("")
            self._clear_alerts()
            return

        blocks = chain.get("blocks", 0)
        headers = chain.get("headers", 0)
        progress = chain.get("verificationprogress", 0) * 100
        ibd = chain.get("initialblockdownload", False)
        subver = network.get("subversion", "unknown")
        peers = network.get("connections", 0)
        mempool_tx = mempool.get("size", 0)
        mempool_mb = mempool.get("bytes", 0) / 1_000_000

        utxo_line = self._utxo_line()

        is_knots = "knots" in subver.lower()
        sync_cls = "ok" if not ibd and progress > 99.9 else "metric"

        lines = [
            f"Chain:     {blocks:,} / {headers:,} blocks",
            f"Sync:      {progress:.2f}%{'  [IBD]' if ibd else '  [synced]'}",
            f"Peers:     {peers}",
            f"Mempool:   {mempool_tx:,} tx  ({mempool_mb:.2f} MB)",
            utxo_line,
            f"Client:    {subver}",
            f"Knots:     {'YES' if is_knots else 'no'}",
        ]
        label.update("\n".join(lines))
        label.remove_class("error")
        label.add_class(sync_cls)

        self.alert_peers = peers < alerts.min_peers
        self.alert_mempool = (
            mempool_mb >= alerts.mempool_congested_mb
            or mempool_tx >= alerts.mempool_congested_tx
        )
        self._apply_border_alerts()

        alerts_msgs: list[str] = []
        if self.alert_peers:
            alerts_msgs.append(f"⚠ Low peers ({peers} < {alerts.min_peers})")
        if self.alert_mempool:
            alerts_msgs.append(
                f"⚠ Congested mempool ({mempool_tx:,} tx / {mempool_mb:.1f} MB)"
            )
        self.alert_message = "  ·  ".join(alerts_msgs)
        alert_line.update(self.alert_message)

    def _utxo_line(self) -> str:
        now = time.time()
        btc_cfg: BitcoinConfig = self.config.bitcoin
        if self._utxo_cache is None or (now - self._utxo_fetched_at) > 1800:
            try:
                self._utxo_cache = self.cli.get_txoutset_info(timeout=btc_cfg.utxo_timeout)
                self._utxo_fetched_at = now
            except BitcoinCLIError:
                if self._utxo_cache:
                    age = int((now - self._utxo_fetched_at) / 60)
                    txouts = self._utxo_cache.get("txouts", 0)
                    return f"UTXO set:  {txouts:,}  (cached {age}m ago)"
                return "UTXO set:  [dim]updating… (gettxoutsetinfo is slow)[/]"

        txouts = self._utxo_cache.get("txouts", 0)
        disk = self._utxo_cache.get("disk_size", 0) / 1_000_000_000
        growth = ""
        if self._prev_utxo_count is not None and txouts:
            delta = txouts - self._prev_utxo_count
            if delta != 0:
                growth = f"  ({delta:+,} since last refresh)"
        self._prev_utxo_count = txouts
        return f"UTXO set:  {txouts:,}  ({disk:.2f} GB){growth}"

    def _apply_border_alerts(self) -> None:
        self.remove_class("alert-peers", "alert-mempool")
        if self.alert_peers:
            self.add_class("alert-peers")
        elif self.alert_mempool:
            self.add_class("alert-mempool")

    def _clear_alerts(self) -> None:
        self.alert_peers = False
        self.alert_mempool = False
        self.alert_message = ""
        self.remove_class("alert-peers", "alert-mempool")