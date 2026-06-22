"""Confirmation modal for control actions."""

from __future__ import annotations

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Vertical
from textual.screen import ModalScreen
from textual.widgets import Label, Static

from oraculovision.node.control.actions import ControlAction


class ConfirmModal(ModalScreen[bool]):
    """Require explicit Y/N confirmation before control actions."""

    BINDINGS = [
        Binding("y", "confirm", "Yes", show=True),
        Binding("n", "cancel", "No", show=True),
        Binding("escape", "cancel", "Cancel", show=False),
    ]

    DEFAULT_CSS = """
    ConfirmModal {
        align: center middle;
    }
    ConfirmModal #confirm-dialog {
        width: 70;
        height: auto;
        max-height: 80%;
        padding: 1 2;
    }
    """

    def __init__(self, action: ControlAction, **kwargs) -> None:
        super().__init__(**kwargs)
        self.action = action

    def compose(self) -> ComposeResult:
        with Vertical(id="confirm-dialog"):
            yield Label("CONTROL ACTION", classes="confirm-title")
            yield Static(self.action.confirmation_text(), id="confirm-body")

    def action_confirm(self) -> None:
        self.dismiss(True)

    def action_cancel(self) -> None:
        self.dismiss(False)