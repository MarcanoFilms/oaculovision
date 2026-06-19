"""Block detail modal for BIP-110 detector."""

from __future__ import annotations

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Vertical, VerticalScroll
from textual.screen import ModalScreen
from textual.widgets import Footer, Header, Label, Static

from oraculovision.analysis.bip110 import BlockAnalysis
from oraculovision.utils.clipboard import copy_to_clipboard


class BlockDetailModal(ModalScreen[None]):
    """Shows detailed analysis for a single block."""

    BINDINGS = [
        Binding("escape", "dismiss", "Close"),
        Binding("c", "copy_hash", "Copy hash"),
    ]

    DEFAULT_CSS = """
    BlockDetailModal {
        align: center middle;
    }
    #block-dialog {
        width: 80;
        height: 85%;
        background: #111;
        border: thick #ffd700;
        padding: 1 2;
    }
    #block-scroll {
        height: 1fr;
    }
    #copy-status {
        height: 1;
        color: #3dd68c;
    }
    .detail-title {
        color: #ffd700;
        text-style: bold;
    }
    """

    def __init__(self, block: BlockAnalysis) -> None:
        super().__init__()
        self.block = block

    def compose(self) -> ComposeResult:
        yield Header()
        with Vertical(id="block-dialog"):
            yield Label(self._title(), classes="detail-title")
            yield Label("", id="copy-status")
            with VerticalScroll(id="block-scroll"):
                yield Static(self._body(), id="block-body")
        yield Footer()

    def _title(self) -> str:
        b = self.block
        sig = "YES" if b.bip110_signaling else "no"
        return (
            f"Block #{b.height}  ·  Spam {b.spam_score}/100  ·  "
            f"{b.status}  ·  BIP110 bit4: {sig}"
        )

    def _body(self) -> str:
        b = self.block
        lines = [
            f"[bold]Hash[/]       {b.hash}",
            f"[bold]Miner[/]     {b.miner_tag}",
            f"[bold]Weight[/]    {b.weight:,}  ({b.tx_count} txs)",
            f"[bold]Witness[/]   {b.witness_pct:.1f}% of block weight",
            "",
            "[bold #ffd700]Spam breakdown[/]",
            f"  Inscriptions:  {b.inscription_count}",
            f"  BRC-20:        {b.brc20_count}",
            f"  Runes:         {b.runes_count}",
            f"  OP_RETURN:     {b.op_return_count}",
            f"  BIP-110 viol:  {b.violation_count} txs  ({b.violation_weight:,} wt)",
            "",
            "[bold #ffd700]Problematic transactions[/]",
        ]

        bad = [
            t for t in b.transactions
            if t.has_bip110_violation or t.is_spam_signal
        ]
        bad.sort(key=lambda t: t.weight, reverse=True)

        if not bad:
            lines.append("  [green]No problematic transactions detected[/]")
        else:
            for tx in bad[:25]:
                flags = ", ".join(sorted(tx.bip110_flags)) or "—"
                signals = ", ".join(sorted(tx.signals)) or "—"
                lines.append(
                    f"  [red]{tx.txid[:16]}…[/]  wt={tx.weight:,}"
                )
                lines.append(f"    flags: {flags}")
                lines.append(f"    signals: {signals}")
            if len(bad) > 25:
                lines.append(f"  … and {len(bad) - 25} more")

        lines.extend([
            "",
            "[dim]c = copy hash · Esc = close[/]",
        ])
        return "\n".join(lines)

    def action_copy_hash(self) -> None:
        status = self.query_one("#copy-status", Label)
        if copy_to_clipboard(self.block.hash):
            status.update("✓ Hash copied to clipboard")
        else:
            status.update("[yellow]Could not copy (install wl-copy/xclip)[/]")

    def action_dismiss(self) -> None:
        self.dismiss()