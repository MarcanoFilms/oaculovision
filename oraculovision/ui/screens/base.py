"""Base panel with shared refresh hooks."""

from __future__ import annotations

from textual.containers import Container


class BaseScreen(Container):
    """Base class for sovereign content panels inside ContentSwitcher."""

    screen_id: str = ""

    def refresh_screen(self, *, force: bool = False) -> None:
        """Override in subclasses to refresh panel data."""

    def export_context(self) -> object | None:
        """Return exportable data for the active screen, if any."""
        return None