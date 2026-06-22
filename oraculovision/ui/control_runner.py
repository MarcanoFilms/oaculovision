"""Shared control-action confirmation and execution flow."""

from __future__ import annotations

from typing import Callable

from oraculovision.node.control.actions import ControlAction
from oraculovision.node.control.gate import ControlGate, ControlResult
from oraculovision.ui.widgets.confirm_modal import ConfirmModal


def run_control_action(
    app,
    gate: ControlGate,
    action: ControlAction,
    *,
    on_complete: Callable[[ControlResult], None] | None = None,
    on_cancelled: Callable[[], None] | None = None,
    on_blocked: Callable[[str], None] | None = None,
) -> None:
    """Show confirm modal and execute action if approved."""
    ok, msg, prepared = gate.prepare(action)
    if not ok or prepared is None:
        if on_blocked:
            on_blocked(msg)
        return

    def _finished(confirmed: bool | None) -> None:
        if not confirmed:
            if on_cancelled:
                on_cancelled()
            return
        result = gate.execute(action)
        if on_complete:
            on_complete(result)

    app.push_screen(ConfirmModal(action), _finished)