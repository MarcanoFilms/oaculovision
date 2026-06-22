"""Policy data models for simulation and display."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum


class PolicyPreset(str, Enum):
    """Simulation presets — stricter than typical live Knots defaults."""

    CURRENT_BIP110 = "current_bip110"
    STRICT_BIP110 = "strict_bip110"
    NO_INSCRIPTIONS = "no_inscriptions"
    NO_OP_RETURN = "no_op_return"
    ECONOMIC_ONLY = "economic_only"


@dataclass(frozen=True)
class PolicyRule:
    """A single enforceable policy rule."""

    id: str
    label: str
    description: str
    enabled: bool = True


@dataclass
class SimulatedTxOutcome:
    txid: str
    weight: int
    category: str
    would_reject: bool
    reject_reasons: list[str] = field(default_factory=list)
    flags: list[str] = field(default_factory=list)


@dataclass
class PolicySimulationResult:
    preset: PolicyPreset
    label: str
    description: str
    total_tx: int
    analyzed_tx: int
    rejected_tx: int
    rejected_weight: int
    total_weight: int
    reject_pct_by_count: float
    reject_pct_by_weight: float
    top_reasons: list[tuple[str, int]] = field(default_factory=list)
    sample_rejects: list[SimulatedTxOutcome] = field(default_factory=list)
    error: str | None = None

    @property
    def impact_summary(self) -> str:
        if self.error:
            return self.error
        return (
            f"{self.rejected_tx:,}/{self.analyzed_tx:,} txs rejected "
            f"({self.reject_pct_by_count:.1f}%) · "
            f"{self.reject_pct_by_weight:.1f}% weight"
        )