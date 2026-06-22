"""Screen registry and navigation helpers."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ScreenSpec:
    id: str
    label: str
    key: str
    description: str
    tier: str = "analyze"
    available: bool = True


TIER_LABELS: dict[str, str] = {
    "overview": "OVERVIEW",
    "analyze": "ANALYZE",
    "operate": "OPERATE",
}

TIER_ORDER: tuple[str, ...] = ("overview", "analyze", "operate")

SCREEN_REGISTRY: list[ScreenSpec] = [
    ScreenSpec(
        "dashboard", "Dashboard", "1",
        "Node health, BIP-110, DATUM overview",
        tier="overview",
    ),
    ScreenSpec(
        "policies", "Policies", "2",
        "Knots policies and simulation",
        tier="analyze",
    ),
    ScreenSpec(
        "mempool_glass", "Mempool Glass", "3",
        "Block template composition",
        tier="analyze",
    ),
    ScreenSpec(
        "block_explorer", "Block Explorer", "4",
        "Search and inspect blocks",
        tier="analyze",
    ),
    ScreenSpec(
        "tx_inspector", "Tx Inspector", "5",
        "Deep transaction analysis",
        tier="analyze",
    ),
    ScreenSpec(
        "spam_health", "Spam & Health", "6",
        "Chain health trends",
        tier="analyze",
    ),
    ScreenSpec(
        "mining", "Mining", "7",
        "DATUM + Ocean panel",
        tier="operate",
    ),
    ScreenSpec(
        "node_control", "Node Control", "8",
        "Peer and policy control",
        tier="operate",
    ),
]


def screen_by_key(key: str) -> ScreenSpec | None:
    for spec in SCREEN_REGISTRY:
        if spec.key == key and spec.available:
            return spec
    return None


def screen_by_id(screen_id: str) -> ScreenSpec | None:
    for spec in SCREEN_REGISTRY:
        if spec.id == screen_id:
            return spec
    return None


def available_screens() -> list[ScreenSpec]:
    return [s for s in SCREEN_REGISTRY if s.available]


def screens_by_tier() -> list[tuple[str, list[ScreenSpec]]]:
    """Return (tier_id, screens) groups in display order."""
    groups: list[tuple[str, list[ScreenSpec]]] = []
    for tier in TIER_ORDER:
        specs = [s for s in available_screens() if s.tier == tier]
        if specs:
            groups.append((tier, specs))
    return groups