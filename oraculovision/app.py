"""OraculoVision — sovereign Bitcoin operator dashboard."""

from __future__ import annotations

from datetime import datetime, timezone

from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Container, Horizontal, Vertical, VerticalScroll
from textual.widgets import Footer, Header, Label

from oraculovision.config import AppConfig, load_config
from oraculovision.data.bitcoin import BitcoinCLI
from oraculovision.screens.help_screen import HelpScreen
from oraculovision.screens.ocean_address_screen import OceanAddressScreen
from oraculovision.services.template_service import TemplateService
from oraculovision.widgets.bip110_detector import Bip110Detector
from oraculovision.widgets.block_template import BlockTemplatePanel
from oraculovision.widgets.datum_mining import DatumMining
from oraculovision.widgets.live_charts import LiveCharts
from oraculovision.widgets.mempool_glass import MempoolGlass
from oraculovision.widgets.node_status import NodeStatus


class OraculoVisionApp(App):
    """Main Textual application."""

    TITLE = "OraculoVision"
    SUB_TITLE = "Don't Trust, Verify"

    CSS_PATH = "theme.tcss"

    BINDINGS = [
        Binding("r", "refresh", "Refresh", show=True),
        Binding("t", "refresh_template", "Template", show=True),
        Binding("o", "ocean_address", "Ocean", show=True),
        Binding("u", "refresh_utxo", "UTXO", show=True),
        Binding("q", "quit", "Quit", show=True),
        Binding("question_mark", "show_help", "Help", show=True),
    ]

    def __init__(self, config: AppConfig | None = None) -> None:
        super().__init__()
        self.config = config or load_config()
        self.cli = BitcoinCLI(
            cli_path=self.config.bitcoin.cli_path or None,
            datadir=self.config.bitcoin.datadir or None,
        )
        self.template_service = TemplateService(self.cli)

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        with Container(id="main-container"):
            yield Label(
                "ORACULOVISION  ·  Don't Trust, Verify  ·  BIP-110 + Knots + DATUM",
                id="tagline",
            )
            yield Label("", id="global-alert")
            with Horizontal(id="dashboard"):
                with Vertical(id="left-col"):
                    yield NodeStatus(
                        id="node-status", cli=self.cli, config=self.config,
                    )
                    yield Bip110Detector(
                        id="bip110", cli=self.cli, config=self.config,
                    )
                with VerticalScroll(id="right-col"):
                    yield DatumMining(id="datum", config=self.config)
                    yield MempoolGlass(
                        id="mempool-glass",
                        template_service=self.template_service,
                        cli=self.cli,
                        config=self.config,
                    )
                    yield BlockTemplatePanel(
                        id="block-template",
                        template_service=self.template_service,
                    )
                    yield LiveCharts(id="charts", cli=self.cli)
        yield Footer()

    def on_mount(self) -> None:
        interval = self.config.refresh.interval_seconds
        self.set_interval(interval, self.action_refresh)
        self.action_refresh()

    def action_refresh(self) -> None:
        self.query_one("#node-status", NodeStatus).refresh_data()
        self.query_one("#bip110", Bip110Detector).refresh_data()
        self.query_one("#datum", DatumMining).refresh_data()
        self.query_one("#mempool-glass", MempoolGlass).refresh_data(force=False)
        self.query_one("#block-template", BlockTemplatePanel).refresh_data(force=False)
        try:
            self.query_one("#charts", LiveCharts).refresh_data()
        except Exception:
            pass
        self._update_tagline()
        self.set_timer(3.0, self._update_global_alerts)

    def action_refresh_template(self) -> None:
        """Refresh block template + mempool glass (shared GBT fetch)."""
        self.template_service.invalidate()
        self.query_one("#mempool-glass", MempoolGlass).refresh_data(force=True)
        self.query_one("#block-template", BlockTemplatePanel).refresh_data(force=True)
        self.set_timer(2.0, self._update_global_alerts)

    def _update_tagline(self) -> None:
        utc = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
        self.query_one("#tagline", Label).update(
            f"ORACULOVISION  ·  {utc}  ·  [r] refresh  [t] template  [u] utxo  [o] ocean  [?] help"
        )

    def action_refresh_utxo(self) -> None:
        """Refresh UTXO set stats (slow RPC, background thread)."""
        self.query_one("#node-status", NodeStatus).refresh_utxo()

    def _update_global_alerts(self) -> None:
        alert = self.query_one("#global-alert", Label)
        node = self.query_one("#node-status", NodeStatus)
        bip = self.query_one("#bip110", Bip110Detector)
        glass = self.query_one("#mempool-glass", MempoolGlass)

        msgs: list[str] = []
        if node.alert_message:
            msgs.append(node.alert_message)
        if bip.alert_spam_block and bip._tip:
            msgs.append(
                f"⚠ Dirty tip block: spam {bip._tip.spam_score}/100 ({bip._tip.miner_tag[:24]})"
            )
        if glass.spam_pct > 30:
            msgs.append(f"⚠ Template: {glass.spam_pct:.0f}% spam weight")

        if msgs:
            alert.update("[bold red]" + "  ·  ".join(msgs) + "[/]")
        else:
            alert.update("")

    def action_show_help(self) -> None:
        self.push_screen(HelpScreen())

    def action_ocean_address(self) -> None:
        """Open modal to set or change the Ocean payout address."""
        datum = self.query_one("#datum", DatumMining)
        self.push_screen(
            OceanAddressScreen(datum.active_ocean_address),
            self._on_ocean_address_set,
        )

    def _on_ocean_address_set(self, address: str | None) -> None:
        if address is None:
            return
        datum = self.query_one("#datum", DatumMining)
        datum.set_ocean_address(address)
        datum.refresh_data()


def run() -> None:
    OraculoVisionApp().run()