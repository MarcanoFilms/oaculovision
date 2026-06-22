"""Policy adjustment preview tests."""

from __future__ import annotations

from oraculovision.analysis.policies.knots import KnotsPolicySnapshot, PolicyEntry
from oraculovision.analysis.policies.models import PolicyPreset, PolicySimulationResult
from oraculovision.analysis.policies.preview import (
    build_conf_adjustments,
    render_conf_preview,
)


def _sim(preset: PolicyPreset, rejected: int, analyzed: int = 100) -> PolicySimulationResult:
    return PolicySimulationResult(
        preset=preset,
        label=preset.value,
        description="test",
        total_tx=analyzed,
        analyzed_tx=analyzed,
        rejected_tx=rejected,
        rejected_weight=rejected * 1000,
        total_weight=analyzed * 1000,
        reject_pct_by_count=(rejected / analyzed) * 100,
        reject_pct_by_weight=(rejected / analyzed) * 100,
    )


def test_build_conf_adjustments_datacarrier_enabled() -> None:
    snap = KnotsPolicySnapshot(
        knots_detected=True,
        entries=[
            PolicyEntry("datacarrier", "yes", "getnodeinfo"),
            PolicyEntry("maxdatacarriersize", "80", "getnodeinfo"),
        ],
    )
    sims = {PolicyPreset.NO_OP_RETURN: _sim(PolicyPreset.NO_OP_RETURN, 12)}
    adj = build_conf_adjustments(snap, sims)
    keys = {a.conf_key for a in adj}
    assert "datacarrier" in keys
    assert "maxdatacarriersize" in keys
    dc = next(a for a in adj if a.conf_key == "datacarrier")
    assert dc.suggested == "0"
    assert dc.reject_pct == 12.0


def test_render_conf_preview_no_gaps() -> None:
    snap = KnotsPolicySnapshot(
        knots_detected=True,
        entries=[PolicyEntry("datacarrier", "no", "rpc")],
    )
    text = render_conf_preview(build_conf_adjustments(snap, {}), knots_detected=True)
    assert "No urgent policy gaps" in text