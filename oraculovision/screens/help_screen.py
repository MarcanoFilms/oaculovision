"""Full help screen with keyboard shortcuts."""

from __future__ import annotations

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import VerticalScroll
from textual.screen import ModalScreen
from textual.widgets import Footer, Header, Static

HELP_TEXT = """
[bold #ffd700]ORACULOVISION — AYUDA[/]

[bold]Navegación global[/]
  [yellow]r[/]     Refrescar todos los paneles
  [yellow]t[/]     Refrescar Block Template + Mempool Glass
  [yellow]q[/]     Salir del dashboard
  [yellow]?[/]     Abrir/cerrar esta ayuda
  [yellow]Tab[/]   Cambiar foco entre paneles

[bold]BIP-110 Detector[/]
  [yellow]↑ ↓[/]   Navegar tabla de bloques
  [yellow]Enter[/] Abrir detalle del bloque seleccionado

[bold]Modal de bloque[/]
  [yellow]c[/]     Copiar hash del bloque al portapapeles
  [yellow]Esc[/]   Cerrar modal

[bold]Paneles[/]
  [cyan]Node Status[/]       Sync, peers, mempool, UTXO set, alertas
  [cyan]BIP-110 Detector[/]  Spam score, violaciones, miner tags
  [cyan]DATUM Mining[/]      Gateway, workers, hashrate, shares
  [cyan]Mempool Glass[/]     Composición del Block Template real (GBT)
  [cyan]Block Template[/]    Resumen GBT compacto + top 5 fees
  [cyan]Live Metrics[/]      Gráficos mempool y peers

[bold]Alertas visuales[/]
  Borde [red]rojo[/]    — pocos peers o bloque spam reciente
  Borde [yellow]amarillo[/] — mempool congestionado

[bold]Configuración[/]
  config.toml en el proyecto o ~/.config/oraculovision/config.toml
  Variable ORACULOVISION_CONFIG para ruta personalizada

[dim]Don't Trust, Verify — BIP-110 + Knots + DATUM[/]
"""


class HelpScreen(ModalScreen):
    """Modal help screen."""

    BINDINGS = [
        Binding("escape", "dismiss", "Cerrar"),
        Binding("question_mark", "dismiss", "Cerrar"),
        Binding("q", "dismiss", "Cerrar"),
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