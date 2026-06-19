"""Live charts for mempool size and peer count."""

from __future__ import annotations

from collections import deque
from datetime import datetime, timezone

from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical
from textual.widgets import Label, Static

from oraculovision.data.bitcoin import BitcoinCLI, BitcoinCLIError

try:
    from textual_plotext import PlotextPlot
except ImportError:
    PlotextPlot = None  # type: ignore[misc, assignment]


MAX_POINTS = 120  # ~60 min at 30s interval


class LiveCharts(Static):
    """Rolling charts for mempool bytes and peer connections."""

    DEFAULT_CSS = """
    LiveCharts {
        height: 1fr;
        border: solid #ffd700;
        padding: 1 1;
    }
    LiveCharts PlotextPlot {
        height: 1fr;
    }
    LiveCharts .chart-error {
        color: #ff6b6b;
    }
    """

    def __init__(self, cli: BitcoinCLI | None = None, **kwargs) -> None:
        super().__init__(**kwargs)
        self.cli = cli or BitcoinCLI()
        self.border_title = "LIVE METRICS"
        self._mempool: deque[float] = deque(maxlen=MAX_POINTS)
        self._peers: deque[float] = deque(maxlen=MAX_POINTS)
        self._last_sample: str = ""

    def compose(self) -> ComposeResult:
        if PlotextPlot is None:
            yield Label(
                "textual-plotext not installed. pip install textual-plotext",
                classes="chart-error",
            )
            return
        with Vertical():
            with Horizontal():
                yield PlotextPlot(id="mempool-chart")
                yield PlotextPlot(id="peers-chart")

    def on_mount(self) -> None:
        if PlotextPlot is None:
            return
        self._setup_charts()
        self.refresh_data()

    def _setup_charts(self) -> None:
        mp = self.query_one("#mempool-chart", PlotextPlot)
        peers = self.query_one("#peers-chart", PlotextPlot)
        mp.plt.title("Mempool (MB)")
        mp.plt.xlabel("samples")
        mp.plt.ylabel("MB")
        peers.plt.title("Peers")
        peers.plt.xlabel("samples")
        peers.plt.ylabel("count")

    def refresh_data(self) -> None:
        if PlotextPlot is None:
            return
        try:
            mempool = self.cli.get_mempool_info()
            network = self.cli.get_network_info()
        except BitcoinCLIError:
            return

        mb = mempool.get("bytes", 0) / 1_000_000
        peer_count = float(network.get("connections", 0))
        self._last_sample = datetime.now(timezone.utc).strftime("%H:%M UTC")

        self._mempool.append(mb)
        self._peers.append(peer_count)

        try:
            self._redraw()
        except Exception:
            pass

    def _redraw(self) -> None:
        if len(self._mempool) < 2:
            return

        mempool_y = list(self._mempool)
        peers_y = list(self._peers)
        # Numeric x-axis avoids plotext mis-parsing "HH:MM" as dates
        x = list(range(len(mempool_y)))

        mp = self.query_one("#mempool-chart", PlotextPlot)
        peers = self.query_one("#peers-chart", PlotextPlot)

        mp.plt.clear_figure()
        mp.plt.title(f"Mempool (MB)  @{self._last_sample}")
        mp.plt.plot(x, mempool_y, marker="dot", color="yellow")
        mp.plt.xlabel("samples (~30s)")
        mp.plt.ylabel("MB")
        mp.plt.theme("dark")
        mp.refresh()

        peers.plt.clear_figure()
        peers.plt.title(f"Peers  @{self._last_sample}")
        peers.plt.plot(x, peers_y, marker="dot", color="green")
        peers.plt.xlabel("samples (~30s)")
        peers.plt.ylabel("count")
        peers.plt.theme("dark")
        peers.refresh()