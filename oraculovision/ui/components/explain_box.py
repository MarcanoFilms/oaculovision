"""Educational aside panel."""

from __future__ import annotations

from textual.app import ComposeResult
from textual.widgets import Label, Static


class ExplainBox(Static):
    """Short contextual explanation for intermediate users."""

    def __init__(self, title: str = "Explain", text: str = "", **kwargs) -> None:
        super().__init__(**kwargs)
        self._title = title
        self._text = text

    def compose(self) -> ComposeResult:
        yield Label(self._title, classes="explain-title")
        yield Static(self._text, id="explain-body")

    def update_text(self, text: str) -> None:
        self.query_one("#explain-body", Static).update(text)