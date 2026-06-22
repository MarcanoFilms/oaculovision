"""Chain health scoring from block spam analysis."""

from __future__ import annotations

from dataclasses import dataclass, field
from statistics import median

from oraculovision.analysis.bip110 import BlockAnalysis


@dataclass
class ChainHealthReport:
    """Aggregated spam/health metrics over a block window."""

    tip_height: int = 0
    scanned_blocks: int = 0
    health_score: int = 0
    health_label: str = "UNKNOWN"
    avg_spam_score: float = 0.0
    median_spam_score: float = 0.0
    max_spam_score: int = 0
    clean_count: int = 0
    suspicious_count: int = 0
    violation_count: int = 0
    bip110_signaling_count: int = 0
    avg_witness_pct: float = 0.0
    total_violation_txs: int = 0
    worst_blocks: list[BlockAnalysis] = field(default_factory=list)
    timeline: list[tuple[int, int]] = field(default_factory=list)
    error: str | None = None

    @property
    def clean_pct(self) -> float:
        if not self.scanned_blocks:
            return 0.0
        return (self.clean_count / self.scanned_blocks) * 100

    @property
    def violation_pct(self) -> float:
        if not self.scanned_blocks:
            return 0.0
        return (self.violation_count / self.scanned_blocks) * 100

    @property
    def bip110_signaling_pct(self) -> float:
        if not self.scanned_blocks:
            return 0.0
        return (self.bip110_signaling_count / self.scanned_blocks) * 100


def health_label(score: int) -> str:
    if score >= 80:
        return "EXCELLENT"
    if score >= 60:
        return "GOOD"
    if score >= 40:
        return "DEGRADED"
    return "POOR"


def health_label_style(score: int) -> str:
    if score >= 80:
        return "green bold"
    if score >= 60:
        return "green"
    if score >= 40:
        return "yellow"
    return "red bold"


def compute_health_score(blocks: list[BlockAnalysis]) -> int:
    """Return 0–100 chain health (higher is healthier)."""
    if not blocks:
        return 0

    avg_spam = sum(b.spam_score for b in blocks) / len(blocks)
    violation_ratio = sum(1 for b in blocks if b.status == "VIOLATION") / len(blocks)
    suspicious_ratio = sum(1 for b in blocks if b.status == "SUSPICIOUS") / len(blocks)

    penalty = (
        avg_spam * 0.55
        + violation_ratio * 100 * 0.30
        + suspicious_ratio * 100 * 0.15
    )
    return max(0, min(100, int(round(100 - penalty))))


def build_chain_health_report(
    blocks: list[BlockAnalysis],
    *,
    tip_height: int,
    worst_limit: int = 12,
) -> ChainHealthReport:
    """Build a health report from analyzed blocks (newest first)."""
    if not blocks:
        return ChainHealthReport(
            tip_height=tip_height,
            error="No blocks analyzed",
        )

    scores = [b.spam_score for b in blocks]
    health = compute_health_score(blocks)

    worst = sorted(blocks, key=lambda b: b.spam_score, reverse=True)[:worst_limit]
    # Chart oldest→newest (left to right)
    timeline = [(b.height, b.spam_score) for b in reversed(blocks)]

    return ChainHealthReport(
        tip_height=tip_height,
        scanned_blocks=len(blocks),
        health_score=health,
        health_label=health_label(health),
        avg_spam_score=sum(scores) / len(scores),
        median_spam_score=float(median(scores)),
        max_spam_score=max(scores),
        clean_count=sum(1 for b in blocks if b.status == "CLEAN"),
        suspicious_count=sum(1 for b in blocks if b.status == "SUSPICIOUS"),
        violation_count=sum(1 for b in blocks if b.status == "VIOLATION"),
        bip110_signaling_count=sum(1 for b in blocks if b.bip110_signaling),
        avg_witness_pct=sum(b.witness_pct for b in blocks) / len(blocks),
        total_violation_txs=sum(b.violation_count for b in blocks),
        worst_blocks=worst,
        timeline=timeline,
    )


def render_summary(report: ChainHealthReport) -> str:
    """Render health summary markup."""
    if report.error:
        return f"[red]{report.error}[/]"

    style = health_label_style(report.health_score)
    lines = [
        (
            f"[bold]Chain Health[/]  [{style}]{report.health_score}/100  "
            f"{report.health_label}[/]"
        ),
        (
            f"Scanned [bold]{report.scanned_blocks}[/] blocks to tip "
            f"[bold]#{report.tip_height:,}[/]"
        ),
        "",
        (
            f"Avg spam [bold]{report.avg_spam_score:.1f}[/]  ·  "
            f"median {report.median_spam_score:.0f}  ·  "
            f"max {report.max_spam_score}"
        ),
        (
            f"Status mix: [green]{report.clean_count} clean[/] "
            f"({report.clean_pct:.0f}%)  ·  "
            f"[yellow]{report.suspicious_count} suspicious[/]  ·  "
            f"[red]{report.violation_count} violation[/] "
            f"({report.violation_pct:.0f}%)"
        ),
        (
            f"BIP-110 signaling: {report.bip110_signaling_pct:.0f}% of blocks  ·  "
            f"avg witness {report.avg_witness_pct:.1f}%  ·  "
            f"{report.total_violation_txs:,} violation txs total"
        ),
    ]
    return "\n".join(lines)