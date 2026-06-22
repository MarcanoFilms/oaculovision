"""Typed control action definitions with human-readable descriptions."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any


class ControlActionType(str, Enum):
    DISCONNECT_PEER = "disconnect_peer"
    BAN_PEER = "ban_peer"
    CLEAR_BANS = "clear_bans"
    SET_MEMPOOL_LIMIT = "set_mempool_limit"


@dataclass(frozen=True)
class ControlAction:
    """A node control action awaiting user confirmation."""

    action_type: ControlActionType
    rpc_method: str
    rpc_params: tuple[Any, ...]
    title: str
    summary: str
    consequences: str
    severity: str = "medium"  # low | medium | high

    @property
    def is_high_severity(self) -> bool:
        return self.severity == "high"

    def confirmation_text(self) -> str:
        lines = [
            f"[bold yellow]CONTROL ACTION[/] — {self.title}",
            "",
            self.summary,
            "",
            f"[bold]Consequences:[/] {self.consequences}",
            "",
            f"RPC: [cyan]{self.rpc_method}[/]",
            "",
            "Press [bold]Y[/] to confirm, [bold]N[/] or Esc to cancel.",
        ]
        return "\n".join(lines)

    @classmethod
    def disconnect_peer(cls, address: str) -> ControlAction:
        return cls(
            action_type=ControlActionType.DISCONNECT_PEER,
            rpc_method="disconnectnode",
            rpc_params=(address,),
            title="Disconnect Peer",
            summary=f"Disconnect peer at {address}.",
            consequences="The peer will be disconnected but can reconnect.",
            severity="low",
        )

    @classmethod
    def ban_peer(cls, subnet: str, ban_time_seconds: int = 86_400) -> ControlAction:
        hours = ban_time_seconds // 3600
        return cls(
            action_type=ControlActionType.BAN_PEER,
            rpc_method="setban",
            rpc_params=(subnet, "add", ban_time_seconds),
            title="Ban Peer / Subnet",
            summary=f"Ban {subnet} for {hours}h ({ban_time_seconds}s).",
            consequences="The peer/subnet cannot reconnect until the ban expires.",
            severity="medium",
        )

    @classmethod
    def clear_bans(cls) -> ControlAction:
        return cls(
            action_type=ControlActionType.CLEAR_BANS,
            rpc_method="clearbanned",
            rpc_params=(),
            title="Clear All Bans",
            summary="Remove all active peer bans.",
            consequences="Previously banned peers may reconnect immediately.",
            severity="medium",
        )

    @classmethod
    def set_mempool_limit(cls, max_megabytes: int) -> ControlAction:
        return cls(
            action_type=ControlActionType.SET_MEMPOOL_LIMIT,
            rpc_method="setmempoollimit",
            rpc_params=(max_megabytes,),
            title="Set Mempool Limit",
            summary=f"Set mempool memory limit to {max_megabytes} MB.",
            consequences="Low-fee transactions may be evicted if over limit.",
            severity="high",
        )