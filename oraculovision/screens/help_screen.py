"""Full help screen with keyboard shortcuts."""

from __future__ import annotations

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import VerticalScroll
from textual.screen import ModalScreen
from textual.widgets import Footer, Header, Static

HELP_TEXT = """
[bold #ffd700]ORACULOVISION — HELP[/]

[bold]Global navigation[/]
  [yellow]r[/]     Refresh all panels (light RPCs + cached template)
  [yellow]t[/]     Refresh Block Template + Mempool Glass (full GBT)
  [yellow]u[/]     Refresh UTXO set stats (slow RPC, ~2 min, background)
  [yellow]o[/]     Enter or change Ocean payout address
  [yellow]q[/]     Quit the dashboard
  [yellow]?[/]     Open/close this help screen
  [yellow]Tab[/]   Move focus between panels

[bold]BIP-110 Detector[/]
  [yellow]↑ ↓[/]   Navigate the block table
  [yellow]Enter[/] Open detail for the selected block

[bold]Block modal[/]
  [yellow]c[/]     Copy block hash to clipboard
  [yellow]Esc[/]   Close modal

[bold]Ocean address modal[/]
  [yellow]Enter[/]  Apply address (empty clears session address)
  [yellow]Esc[/]    Cancel without changes

[bold]Panels[/]
  [cyan]Node Status[/]       Sync, peers, mempool, UTXO set, alerts
  [cyan]BIP-110 Detector[/]  Spam score, violations, miner tags
  [cyan]DATUM Mining[/]      Gateway, workers, hashrate, Ocean stats
  [cyan]Mempool Glass[/]     Real Block Template composition (GBT)
  [cyan]Block Template[/]    Compact GBT summary + top 5 fees
  [cyan]Live Metrics[/]      Mempool and peer charts

[bold]Visual alerts[/]
  [red]Red[/] border       — low peers or recent spam block
  [yellow]Yellow[/] border — congested mempool

[bold]Performance notes[/]
  Auto-refresh skips slow RPCs: UTXO set ([yellow]u[/] only),
  Block Template (use [yellow]t[/] or 30s cache), BIP-110 blocks
  (only when chain tip changes), Ocean blocks-found (5 min cache).

[bold]Configuration[/]
  config.toml in the project or ~/.config/oraculovision/config.toml
  ORACULOVISION_CONFIG for a custom path

[dim]Don't Trust, Verify — BIP-110 + Knots + DATUM[/]
"""


class HelpScreen(ModalScreen):
    """Modal help screen."""

    BINDINGS = [
        Binding("escape", "dismiss", "Close"),
        Binding("question_mark", "dismiss", "Close"),
        Binding("q", "dismiss", "Close"),
    ]

    DEFAULT_CSS = """
    HelpScreen {
        align: center middle;
    }
    #help-dialog {
        width: 72;
        height: 85%;
        background: #111;
        border: thick #ffd700;
        padding: 1 2;
    }
    #help-content {
        height: 1fr;
    }
    """

    def compose(self) -> ComposeResult:
        yield Header()
        with VerticalScroll(id="help-dialog"):
            yield Static(HELP_TEXT, id="help-content")
        yield Footer()

    def action_dismiss(self) -> None:
        self.dismiss()