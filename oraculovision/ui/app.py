"""OracleVision v2 — multi-screen sovereign dashboard."""

from __future__ import annotations

from pathlib import Path

from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Container, Horizontal
from textual.widgets import ContentSwitcher, Footer, Header

from oraculovision.config import AppConfig, config_source, load_config
from oraculovision.node.client import NodeClient
from oraculovision.node.control.gate import ControlGate
from oraculovision.node.profiles import build_client, profile_cycle
from oraculovision.widgets.bip110_detector import Bip110Detector
from oraculovision.widgets.live_charts import LiveCharts
from oraculovision.widgets.mempool_glass import MempoolGlass
from oraculovision.widgets.node_status import NodeStatus
from oraculovision.screens.help_screen import HelpScreen
from oraculovision.screens.ocean_address_screen import OceanAddressScreen
from oraculovision.analysis.bip110 import BlockAnalysis, TxAnalysis
from oraculovision.analysis.detectors import configure_detectors
from oraculovision.analysis.chain_health import ChainHealthReport
from oraculovision.services.block_service import BlockService
from oraculovision.services.export_service import ExportService, default_export_dir
from oraculovision.services.health_service import HealthService
from oraculovision.services.template_service import TemplateService
from oraculovision.services.address_service import AddressInspection, AddressService
from oraculovision.services.tx_service import TxInspectContext, TxInspection, TxService
from oraculovision.ui.screens.block_explorer import BlockExplorerScreen
from oraculovision.ui.screens.dashboard import DashboardScreen
from oraculovision.ui.screens.mempool_glass import MempoolGlassScreen
from oraculovision.ui.screens.mining import MiningScreen
from oraculovision.ui.screens.node_control import NodeControlScreen
from oraculovision.ui.screens.policies import PoliciesScreen
from oraculovision.ui.screens.spam_health import SpamHealthScreen
from oraculovision.ui.screens.tx_inspector import TxInspectorScreen
from oraculovision.ui.components.sovereign_status_bar import SovereignStatusBar
from oraculovision.ui.widgets.sidebar import Sidebar

_THEME_DIR = Path(__file__).resolve().parent / "theme"


class SovereignApp(App):
    """Main Textual application with sidebar navigation."""

    TITLE = "OraculoVision"
    SUB_TITLE = "Don't Trust, Verify"

    CSS_PATH = _THEME_DIR / "sovereign.tcss"

    BINDINGS = [
        Binding("r", "refresh", "Refresh", show=True),
        Binding("t", "refresh_template", "Template", show=True),
        Binding("u", "refresh_utxo", "UTXO", show=True),
        Binding("o", "ocean_address", "Ocean", show=True),
        Binding("q", "quit", "Quit", show=True),
        Binding("question_mark", "show_help", "Help", show=True),
        Binding("1", "goto_dashboard", "Dash", show=False),
        Binding("2", "goto_policies", "Policy", show=False),
        Binding("3", "goto_mempool", "Glass", show=False),
        Binding("4", "goto_explorer", "Blocks", show=False),
        Binding("5", "goto_tx_inspector", "Tx", show=False),
        Binding("6", "goto_health", "Health", show=False),
        Binding("8", "goto_control", "Control", show=False),
        Binding("slash", "focus_search", "Find", show=False),
        Binding("d", "control_disconnect", "Disc", show=False),
        Binding("b", "control_ban", "Ban", show=False),
        Binding("c", "control_clear_bans", "Unban", show=False),
        Binding("m", "control_mempool", "Mempool", show=False),
        Binding("7", "goto_mining", "Mine", show=False),
        Binding("e", "export_data", "Export", show=True),
        Binding("p", "switch_profile", "Profile", show=True),
    ]

    def __init__(self, config: AppConfig | None = None) -> None:
        super().__init__()
        self.config = config or load_config()
        configure_detectors(self.config.detectors.enabled)
        self._profile_names = sorted(self.config.profiles)
        self.cli = self._build_node_client()
        self._init_services()
        self.export_service = self._build_export_service()
        self._active_screen = "dashboard"
        self._config_path, self._config_mtime = config_source()

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        yield SovereignStatusBar(
            self.cli,
            self.config,
            profile_name=self.config.bitcoin.active_profile,
            id="sovereign-status",
        )
        with Container(id="sovereign-shell"):
            with Horizontal(id="sovereign-layout"):
                yield Sidebar(id="sidebar", active_id=self._active_screen)
                with ContentSwitcher(
                    initial=self._active_screen,
                    id="screen-switcher",
                ):
                    yield DashboardScreen(
                        self.cli,
                        self.config,
                        self.template_service,
                        self.block_service,
                        id="dashboard",
                    )
                    yield PoliciesScreen(
                        self.cli,
                        self.config,
                        self.template_service,
                        id="policies",
                    )
                    yield MempoolGlassScreen(
                        self.cli,
                        self.config,
                        self.template_service,
                        id="mempool_glass",
                    )
                    yield BlockExplorerScreen(
                        self.block_service,
                        self.config,
                        id="block_explorer",
                    )
                    yield TxInspectorScreen(
                        self.tx_service,
                        self.address_service,
                        id="tx_inspector",
                    )
                    yield SpamHealthScreen(
                        self.health_service,
                        self.config,
                        id="spam_health",
                    )
                    yield MiningScreen(self.config, id="mining")
                    yield NodeControlScreen(
                        self.cli,
                        self.control_gate,
                        self.config,
                        id="node_control",
                    )
        yield Footer()

    def on_mount(self) -> None:
        interval = self.config.refresh.interval_seconds
        self.set_interval(interval, self.action_refresh)
        self._refresh_status_bar()
        self.action_refresh()

    def _refresh_status_bar(self) -> None:
        try:
            self.query_one("#sovereign-status", SovereignStatusBar).refresh_data()
        except Exception:
            pass

    def on_sidebar_screen_selected(self, event: Sidebar.ScreenSelected) -> None:
        self._switch_screen(event.screen_id)

    def _switch_screen(self, screen_id: str) -> None:
        self._active_screen = screen_id
        switcher = self.query_one("#screen-switcher", ContentSwitcher)
        switcher.current = screen_id
        self.query_one("#sidebar", Sidebar).set_active(screen_id)
        screen = self._current_screen()
        if screen:
            screen.refresh_screen()

    def _current_screen(self):
        try:
            child = self.query_one(f"#{self._active_screen}")
            return child if hasattr(child, "refresh_screen") else None
        except Exception:
            return None

    def action_goto_dashboard(self) -> None:
        self._switch_screen("dashboard")

    def action_goto_policies(self) -> None:
        self._switch_screen("policies")

    def action_goto_mempool(self) -> None:
        self._switch_screen("mempool_glass")

    def action_goto_explorer(self) -> None:
        self._switch_screen("block_explorer")

    def action_focus_search(self) -> None:
        if self._active_screen == "block_explorer":
            self.query_one("#block_explorer", BlockExplorerScreen).action_focus_search()
        elif self._active_screen == "tx_inspector":
            self.query_one("#tx_inspector", TxInspectorScreen).action_focus_search()
        elif self._active_screen == "node_control":
            self.query_one("#node_control", NodeControlScreen).action_focus_search()
        else:
            self._switch_screen("block_explorer")
            self.query_one("#block_explorer", BlockExplorerScreen).action_focus_search()

    def action_goto_tx_inspector(self) -> None:
        self._switch_screen("tx_inspector")

    def inspect_transaction(
        self,
        txid: str,
        *,
        block_hash: str | None = None,
        block_height: int | None = None,
        raw_tx: dict | None = None,
        cached_analysis: TxAnalysis | None = None,
    ) -> None:
        """Switch to Tx Inspector and analyze the given txid."""
        context = TxInspectContext(
            block_hash=block_hash,
            block_height=block_height,
            raw_tx=raw_tx,
            cached_analysis=cached_analysis,
        )
        self._switch_screen("tx_inspector")
        self.query_one("#tx_inspector", TxInspectorScreen).inspect_txid(
            txid,
            context=context,
        )

    def action_goto_health(self) -> None:
        self._switch_screen("spam_health")

    def action_goto_control(self) -> None:
        self._switch_screen("node_control")

    def action_control_disconnect(self) -> None:
        if self._active_screen != "node_control":
            return
        self.query_one("#node_control", NodeControlScreen).action_disconnect_peer()

    def action_control_ban(self) -> None:
        if self._active_screen != "node_control":
            return
        self.query_one("#node_control", NodeControlScreen).action_ban_peer()

    def action_control_clear_bans(self) -> None:
        if self._active_screen != "node_control":
            return
        self.query_one("#node_control", NodeControlScreen).action_clear_bans()

    def action_control_mempool(self) -> None:
        if self._active_screen != "node_control":
            return
        self.query_one("#node_control", NodeControlScreen).action_set_mempool_limit()

    def action_goto_mining(self) -> None:
        self._switch_screen("mining")

    def action_refresh(self) -> None:
        self._maybe_reload_config()
        self._refresh_status_bar()
        screen = self._current_screen()
        if screen:
            screen.refresh_screen()

    def _build_node_client(self) -> NodeClient:
        profile = self.config.profiles[self.config.bitcoin.active_profile]
        return build_client(profile)

    def _init_services(self) -> None:
        self.template_service = TemplateService(self.cli)
        self.block_service = BlockService(
            self.cli,
            block_index_config=self.config.block_index,
        )
        self.tx_service = TxService(self.cli, self.config.address)
        self.address_service = AddressService(self.cli, self.config.address)
        self.health_service = HealthService(
            self.cli,
            self.block_service,
            default_scan_depth=self.config.chain_health.scan_blocks,
        )
        self.control_gate = ControlGate(
            self.cli,
            read_only=self.config.control.read_only,
        )

    def _rebind_node_clients(self) -> None:
        self.query_one("#sovereign-status", SovereignStatusBar).client = self.cli
        self.query_one("#sovereign-status", SovereignStatusBar).set_profile_name(
            self.config.bitcoin.active_profile,
        )

        dashboard = self.query_one("#dashboard", DashboardScreen)
        dashboard.cli = self.cli
        dashboard.template_service = self.template_service
        dashboard.block_service = self.block_service
        for widget_type in (NodeStatus, Bip110Detector, MempoolGlass, LiveCharts):
            try:
                widget = dashboard.query_one(widget_type)
                widget.cli = self.cli
            except Exception:
                pass
        try:
            bip = dashboard.query_one(Bip110Detector)
            bip.block_service = self.block_service
        except Exception:
            pass
        try:
            dashboard.query_one(MempoolGlass).template_service = self.template_service
        except Exception:
            pass
        try:
            from oraculovision.widgets.block_template import BlockTemplatePanel

            dashboard.query_one(BlockTemplatePanel).template_service = (
                self.template_service
            )
        except Exception:
            pass

        policies = self.query_one("#policies", PoliciesScreen)
        policies.cli = self.cli
        policies.template_service = self.template_service

        mempool = self.query_one("#mempool_glass", MempoolGlassScreen)
        mempool.cli = self.cli
        mempool.template_service = self.template_service

        explorer = self.query_one("#block_explorer", BlockExplorerScreen)
        explorer.block_service = self.block_service

        inspector = self.query_one("#tx_inspector", TxInspectorScreen)
        inspector.tx_service = self.tx_service
        inspector.address_service = self.address_service

        health = self.query_one("#spam_health", SpamHealthScreen)
        health.health_service = self.health_service

        control = self.query_one("#node_control", NodeControlScreen)
        control.client = self.cli
        control.gate = self.control_gate

    def action_switch_profile(self) -> None:
        if len(self._profile_names) < 2:
            self.notify(
                "Add more [profiles.*] sections in config.toml to switch nodes",
                title="Profile",
                severity="warning",
                timeout=4,
            )
            return

        next_name = profile_cycle(
            self._profile_names,
            self.config.bitcoin.active_profile,
        )
        self.config.bitcoin.active_profile = next_name
        self.cli = self._build_node_client()
        self._init_services()
        self._rebind_node_clients()
        self.notify(
            f"Active profile: {next_name}",
            title="Node profile",
            timeout=4,
        )
        self._refresh_status_bar()
        screen = self._current_screen()
        if screen:
            screen.refresh_screen(force=True)

    def _build_export_service(self) -> ExportService:
        export_cfg = self.config.export
        directory = export_cfg.directory or str(default_export_dir())
        return ExportService(
            directory,
            write_json=export_cfg.json,
            write_csv=export_cfg.csv,
        )

    def _maybe_reload_config(self) -> None:
        path, mtime = config_source()
        if path is None or mtime <= self._config_mtime:
            return
        self.config = load_config()
        configure_detectors(self.config.detectors.enabled)
        self._profile_names = sorted(self.config.profiles)
        self._config_path = path
        self._config_mtime = mtime
        self.cli = self._build_node_client()
        self._init_services()
        self._rebind_node_clients()
        self.export_service = self._build_export_service()
        self.notify(
            f"Config reloaded from {path.name}",
            title="OracleVision",
            timeout=4,
        )

    def action_export_data(self) -> None:
        screen = self._current_screen()
        if screen is None:
            self.notify(
                "Open Block Explorer, Tx Inspector, or Spam & Health to export",
                title="Export",
                severity="warning",
                timeout=4,
            )
            return

        context = screen.export_context() if hasattr(screen, "export_context") else None
        try:
            paths = self._export_context(context)
        except ValueError as exc:
            self.notify(str(exc), title="Export failed", severity="error", timeout=5)
            return
        except Exception as exc:
            self.notify(str(exc), title="Export failed", severity="error", timeout=5)
            return

        if not paths:
            self.notify(
                "Nothing to export on this screen — load data first",
                title="Export",
                severity="warning",
                timeout=4,
            )
            return

        primary = paths[0]
        self.notify(
            f"Wrote {len(paths)} file(s) — {primary.name}",
            title="Export",
            timeout=5,
        )

    def _export_context(self, context: object | None) -> list:
        if isinstance(context, ChainHealthReport):
            return self.export_service.export_chain_health(context)
        if isinstance(context, BlockAnalysis):
            return self.export_service.export_block_analysis(context)
        if isinstance(context, TxInspection):
            return self.export_service.export_tx_analysis(context)
        if isinstance(context, AddressInspection):
            return self.export_service.export_address_analysis(context)
        return []

    def action_refresh_template(self) -> None:
        self.template_service.invalidate()
        screen = self._current_screen()
        if screen:
            screen.refresh_screen(force=True)
        if self._active_screen == "dashboard":
            self.query_one("#dashboard", DashboardScreen).refresh_template()

    def action_refresh_utxo(self) -> None:
        dash = self.query_one("#dashboard", DashboardScreen)
        dash.refresh_utxo()

    def action_show_help(self) -> None:
        self.push_screen(HelpScreen())

    def action_ocean_address(self) -> None:
        mining = self.query_one("#mining", MiningScreen)
        dash_datum = None
        try:
            dash = self.query_one("#dashboard", DashboardScreen)
            from oraculovision.widgets.datum_mining import DatumMining
            dash_datum = dash.query_one("#datum", DatumMining)
        except Exception:
            pass

        current = ""
        if dash_datum:
            current = dash_datum.active_ocean_address
        else:
            from oraculovision.widgets.datum_mining import DatumMining
            current = mining.query_one("#datum-full", DatumMining).active_ocean_address

        self.push_screen(
            OceanAddressScreen(current),
            self._on_ocean_address_set,
        )

    def _on_ocean_address_set(self, address: str | None) -> None:
        if address is None:
            return
        mining = self.query_one("#mining", MiningScreen)
        mining.set_ocean_address(address)
        try:
            dash = self.query_one("#dashboard", DashboardScreen)
            from oraculovision.widgets.datum_mining import DatumMining
            datum = dash.query_one("#datum", DatumMining)
            datum.set_ocean_address(address)
            datum.refresh_data()
        except Exception:
            pass


def run() -> None:
    SovereignApp().run()