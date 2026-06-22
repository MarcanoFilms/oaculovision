"""Bordered panel with optional severity styling."""

from __future__ import annotations

from textual.app import ComposeResult
from textual.widgets import Label, Static


class SovereignPanel(Static):
    """Panel with title and severity border classes."""

    def __init__(
        self,
        title: str = "",
        *,
        severity: str = "",
        **kwargs,
    ) -> None:
        super().__init__(**kwargs)
        self._title = title
        self._severity = severity

    def compose(self) -> ComposeResult:
        if self._title:
            yield Label(self._title, classes="sov-panel-title")
        yield Static("", id="sov-panel-body")

    def on_mount(self) -> None:
        self._apply_severity()

    def set_severity(self, severity: str) -> None:
        self._severity = severity
        self._apply_severity()

    def _apply_severity(self) -> None:
        self.remove_class("-ok", "-warn", "-danger")
        if self._severity == "ok":
            self.add_class("-ok")
        elif self._severity == "warn":
            self.add_class("-warn")
        elif self._severity == "danger":
            self.add_class("-danger")

    def update_content(self, text: str) -> None:
        self.query_one("#sov-panel-body", Static).update(text)