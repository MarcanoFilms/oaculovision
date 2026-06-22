"""Map live node policy to suggested bitcoin.conf adjustments + template impact."""

from __future__ import annotations

from dataclasses import dataclass

from oraculovision.analysis.policies.knots import KnotsPolicySnapshot
from oraculovision.analysis.policies.models import PolicyPreset, PolicySimulationResult


@dataclass(frozen=True)
class ConfAdjustment:
    """A single recommended bitcoin.conf change with projected template impact."""

    conf_key: str
    current: str
    suggested: str
    rationale: str
    preset: PolicyPreset | None = None
    reject_pct: float | None = None
    reject_weight_pct: float | None = None

    @property
    def impact_line(self) -> str:
        if self.reject_pct is None:
            return ""
        wt = self.reject_weight_pct or 0.0
        return f"~{self.reject_pct:.1f}% txs · {wt:.1f}% weight in template"


def _entry_map(snapshot: KnotsPolicySnapshot) -> dict[str, str]:
    return {e.key: e.value for e in snapshot.entries}


def _sim_metrics(
    preset: PolicyPreset | None,
    results: dict[PolicyPreset, PolicySimulationResult],
) -> tuple[float | None, float | None]:
    if preset is None:
        return None, None
    result = results.get(preset)
    if not result or result.error:
        return None, None
    return result.reject_pct_by_count, result.reject_pct_by_weight


def _is_yes(value: str) -> bool:
    return value.lower() in {"yes", "true", "1"}


def _as_int(value: str) -> int | None:
    try:
        return int(value)
    except (ValueError, TypeError):
        return None


def build_conf_adjustments(
    snapshot: KnotsPolicySnapshot,
    sim_results: dict[PolicyPreset, PolicySimulationResult] | None = None,
) -> list[ConfAdjustment]:
    """Compare live Knots policy to stricter BIP-110-friendly targets."""
    if snapshot.error:
        return []

    results = sim_results or {}
    by_key = _entry_map(snapshot)
    out: list[ConfAdjustment] = []

    datacarrier = by_key.get("datacarrier", "")
    if datacarrier and _is_yes(datacarrier):
        pct, wt = _sim_metrics(PolicyPreset.NO_OP_RETURN, results)
        out.append(
            ConfAdjustment(
                conf_key="datacarrier",
                current=datacarrier,
                suggested="0",
                rationale="Stop relaying OP_RETURN data-carrier outputs (spam vector).",
                preset=PolicyPreset.NO_OP_RETURN,
                reject_pct=pct,
                reject_weight_pct=wt,
            )
        )

    for size_key in ("maxdatacarriersize", "datacarriersize"):
        raw = by_key.get(size_key)
        if raw is None:
            continue
        current_int = _as_int(raw)
        if current_int is None or current_int <= 42:
            continue
        pct, wt = _sim_metrics(PolicyPreset.NO_OP_RETURN, results)
        out.append(
            ConfAdjustment(
                conf_key=size_key,
                current=raw,
                suggested="42",
                rationale="Tighten OP_RETURN payload limit (BIP-110 recommends ≤42 bytes).",
                preset=PolicyPreset.NO_OP_RETURN,
                reject_pct=pct,
                reject_weight_pct=wt,
            )
        )
        break

    bare_multisig = by_key.get("permitbaremultisig", "")
    if bare_multisig and _is_yes(bare_multisig):
        out.append(
            ConfAdjustment(
                conf_key="permitbaremultisig",
                current=bare_multisig,
                suggested="0",
                rationale="Disable bare multisig inputs — reduces legacy script abuse surface.",
            )
        )

    if snapshot.knots_detected:
        pct, wt = _sim_metrics(PolicyPreset.NO_INSCRIPTIONS, results)
        if pct and pct > 0:
            out.append(
                ConfAdjustment(
                    conf_key="rejectnonstd (inscriptions)",
                    current="node default",
                    suggested="stricter Knots filters",
                    rationale=(
                        "Template still carries inscription/token spam — "
                        "tighten Knots non-standard filters."
                    ),
                    preset=PolicyPreset.NO_INSCRIPTIONS,
                    reject_pct=pct,
                    reject_weight_pct=wt,
                )
            )

        pct, wt = _sim_metrics(PolicyPreset.ECONOMIC_ONLY, results)
        if pct and pct > 5:
            out.append(
                ConfAdjustment(
                    conf_key="mempool policy (aggressive)",
                    current="live relay policy",
                    suggested="economic-only relay",
                    rationale=(
                        "Large non-economic share in next block — "
                        "consider stricter relay for spam patterns."
                    ),
                    preset=PolicyPreset.ECONOMIC_ONLY,
                    reject_pct=pct,
                    reject_weight_pct=wt,
                )
            )

    return out


def render_conf_preview(
    adjustments: list[ConfAdjustment],
    *,
    knots_detected: bool = True,
) -> str:
    """Render adjustment preview for the Policies screen."""
    lines = [
        "[bold #ffd700]bitcoin.conf Adjustment Preview[/]",
        "[dim]Read-only preview — edit bitcoin.conf and restart Knots to apply.[/]",
        "",
    ]

    if not knots_detected:
        lines.append(
            "[yellow]Non-Knots client — suggestions target Bitcoin Knots policy options.[/]"
        )
        lines.append("")

    if not adjustments:
        lines.extend([
            "[green]No urgent policy gaps detected[/] against BIP-110-friendly defaults.",
            "",
            "[dim]Use template simulation (right) to preview stricter enforcement levels.[/]",
        ])
        return "\n".join(lines)

    for adj in adjustments:
        lines.append(
            f"[bold]{adj.conf_key}[/]  {adj.current} → [cyan]{adj.suggested}[/]"
        )
        if adj.impact_line:
            lines.append(f"  Template impact: [yellow]{adj.impact_line}[/]")
        lines.append(f"  [dim]{adj.rationale}[/]")
        lines.append("")

    lines.append(
        "[dim]Impact numbers come from your current block template simulation.[/]"
    )
    return "\n".join(lines)