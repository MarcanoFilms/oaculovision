"""Control gate — enforces read-only mode and executes confirmed actions."""

from __future__ import annotations

from dataclasses import dataclass

from oraculovision.node.client import BitcoinCLIError, NodeClient
from oraculovision.node.control.actions import ControlAction


@dataclass
class ControlResult:
    success: bool
    message: str
    action: ControlAction | None = None


class ControlGate:
    """Executes control actions only when not in read-only mode."""

    def __init__(self, client: NodeClient, *, read_only: bool = True) -> None:
        self.client = client
        self.read_only = read_only

    def can_execute(self) -> tuple[bool, str]:
        if self.read_only:
            return False, (
                "Control actions disabled (read_only=true). "
                "Set [control] read_only = false in config.toml to enable."
            )
        return True, ""

    def prepare(self, action: ControlAction) -> tuple[bool, str, ControlAction | None]:
        """Check if action can proceed; return (ok, message, action)."""
        ok, msg = self.can_execute()
        if not ok:
            return False, msg, None
        return True, action.confirmation_text(), action

    def execute(self, action: ControlAction) -> ControlResult:
        """Execute a confirmed control action."""
        ok, msg = self.can_execute()
        if not ok:
            return ControlResult(success=False, message=msg, action=action)

        try:
            self.client.call_write(action.rpc_method, *action.rpc_params)
            return ControlResult(
                success=True,
                message=f"OK: {action.title}",
                action=action,
            )
        except BitcoinCLIError as exc:
            detail = str(exc)
            if exc.hint:
                detail += f" → {exc.hint}"
            return ControlResult(
                success=False,
                message=detail,
                action=action,
            )