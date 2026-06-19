"""DATUM mining panel widget."""

from __future__ import annotations

from textual.app import ComposeResult
from textual.containers import Vertical
from textual.widgets import Label, Static

from oraculovision.data.datum import fetch_datum_status


class DatumMining(Static):
    """Shows DATUM gateway status, workers, hashrate, and shares."""

    DEFAULT_CSS = """
    DatumMining {
        height: auto;
        min-height: 14;
        border: solid #ffd700;
        padding: 1 2;
    }
    DatumMining .datum-ok { color: #3dd68c; }
    DatumMining .datum-warn { color: #ffd700; }
    DatumMining .datum-err { color: #ff6b6b; }
    DatumMining .datum-metric { color: #e0e0e0; }
    DatumMining .datum-hint { color: #888; }
    """

    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        self.border_title = "DATUM MINING"

    def compose(self) -> ComposeResult:
        with Vertical():
            yield Label("Querying DATUM...", id="datum-content", classes="datum-metric")

    def refresh_data(self) -> None:
        label = self.query_one("#datum-content", Label)
        status = fetch_datum_status()

        if not status.available:
            label.update(status.setup_hint or "DATUM unavailable.")
            label.remove_class("datum-ok")
            label.add_class("datum-warn")
            return

        state_lower = status.gateway_state.lower()
        if "ready" in state_lower or "connected" in state_lower:
            state_cls = "datum-ok"
        elif "error" in state_lower or "not" in state_lower:
            state_cls = "datum-err"
        else:
            state_cls = "datum-warn"

        workers = status.workers
        if status.worker_names:
            worker_detail = ", ".join(status.worker_names[:5])
            if len(status.worker_names) > 5:
                worker_detail += f" +{len(status.worker_names) - 5}"
        else:
            worker_detail = str(workers)

        lines = [
            f"Gateway:   {status.gateway_state}",
            f"Workers:   {worker_detail}",
            f"Hashrate:  {status.hashrate}",
            f"Shares:    ✓ {status.shares_accepted}",
            f"Rejected:  ✗ {status.shares_rejected}",
            f"Pool:      {status.pool_host}",
            f"Miner tag: {status.miner_tag}",
            f"Job h:     {status.job_height}  uptime: {status.uptime}",
        ]
        if status.last_events:
            lines.append("— Recent events —")
            lines.extend(f"  {e[:72]}" for e in status.last_events[-4:])

        label.update("\n".join(lines))
        label.remove_class("datum-ok", "datum-warn", "datum-err")
        label.add_class(state_cls)