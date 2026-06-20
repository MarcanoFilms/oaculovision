"""Node status widget — real-time Knots/Core metrics."""

from __future__ import annotations

import time

from textual import work
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
        self._utxo_updating: bool = False
        self._prev_utxo_count: int | None = None
        self._chain_data: dict | None = None
        self._network_data: dict | None = None
        self._mempool_data: dict | None = None
        self.alert_peers: bool = False
        self.alert_mempool: bool = False
        self.alert_message: str = ""

    def compose(self) -> ComposeResult:
        with Vertical():
            yield Label("", id="alert-line", classes="alert-line")
            yield Label("Loading...", id="node-content", classes="metric")

    def refresh_utxo(self) -> None:
        """Fetch UTXO set in background (triggered by u key)."""
        if self._utxo_updating:
            return
        self._utxo_updating = True
        self._update_display()
        self._fetch_utxo_background()

    def refresh_data(self) -> None:
        label = self.query_one("#node-content", Label)
        alert_line = self.query_one("#alert-line", Label)
        alerts = self.config.alerts

        try:
            self._chain_data = self.cli.get_blockchain_info()
            self._network_data = self.cli.get_network_info()
            self._mempool_data = self.cli.get_mempool_info()
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

        self._update_display()

    def _update_display(self) -> None:
        if not self._chain_data or not self._network_data or not self._mempool_data:
            return

        label = self.query_one("#node-content", Label)
        alert_line = self.query_one("#alert-line", Label)
        alerts = self.config.alerts

        chain = self._chain_data
        network = self._network_data
        mempool = self._mempool_data

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
        if self._utxo_updating:
            return "UTXO set:  updating… (may take ~2 min, press u)"

        if self._utxo_cache:
            now = time.time()
            txouts = self._utxo_cache.get("txouts", 0)
            disk = self._utxo_cache.get("disk_size", 0) / 1_000_000_000
            age_min = int((now - self._utxo_fetched_at) / 60)
            growth = ""
            if self._prev_utxo_count is not None and txouts:
                delta = txouts - self._prev_utxo_count
                if delta != 0:
                    growth = f"  ({delta:+,} since last)"
            self._prev_utxo_count = txouts
            return f"UTXO set:  {txouts:,}  ({disk:.2f} GB)  [dim](cached {age_min}m, u=refresh)[/]"

        return "UTXO set:  [dim]press u to refresh (slow RPC)[/]"

    @work(thread=True, exclusive=True)
    def _fetch_utxo_background(self) -> None:
        btc_cfg: BitcoinConfig = self.config.bitcoin
        try:
            cache = self.cli.get_txoutset_info(timeout=btc_cfg.utxo_timeout)
            self._utxo_cache = cache
            self._utxo_fetched_at = time.time()
        except BitcoinCLIError:
            pass
        finally:
            self._utxo_updating = False
            self.app.call_from_thread(self._update_display)

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