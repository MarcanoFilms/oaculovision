"""Simulate stricter policy presets against a block template."""

from __future__ import annotations

from collections import Counter
from typing import Any, Callable

from oraculovision.analysis.bip110 import analyze_transaction
from oraculovision.analysis.mempool_compose import categorize_transaction
from oraculovision.analysis.policies.models import (
    PolicyPreset,
    PolicySimulationResult,
    SimulatedTxOutcome,
)
from oraculovision.analysis.script_parser import MAX_OPRETURN_SIZE, MAX_PUSHDATA_SIZE


PRESET_META: dict[PolicyPreset, tuple[str, str]] = {
    PolicyPreset.CURRENT_BIP110: (
        "Current BIP-110",
        "Reject txs with standard BIP-110 consensus violations.",
    ),
    PolicyPreset.STRICT_BIP110: (
        "Strict BIP-110",
        "BIP-110 violations plus annex, op_success, and op_if/op_notif in tapscript.",
    ),
    PolicyPreset.NO_INSCRIPTIONS: (
        "No Inscriptions",
        "Reject inscription and token-pattern transactions.",
    ),
    PolicyPreset.NO_OP_RETURN: (
        "No OP_RETURN",
        "Reject any transaction with OP_RETURN outputs.",
    ),
    PolicyPreset.ECONOMIC_ONLY: (
        "Economic Only",
        "Reject spam, coinjoins, consolidations, and non-economic patterns.",
    ),
}


def _evaluate_preset(
    preset: PolicyPreset,
    tx: dict[str, Any],
) -> tuple[bool, list[str], list[str]]:
    """Return (would_reject, reasons, flags)."""
    analysis = analyze_transaction(tx)
    category = categorize_transaction(tx)
    flags = sorted(analysis.bip110_flags | analysis.signals)
    reasons: list[str] = []

    if preset == PolicyPreset.CURRENT_BIP110:
        if analysis.has_bip110_violation:
            reasons.extend(sorted(analysis.bip110_flags))
        return bool(reasons), reasons, flags

    if preset == PolicyPreset.STRICT_BIP110:
        strict_flags = set(analysis.bip110_flags)
        if analysis.has_bip110_violation:
            reasons.extend(sorted(analysis.bip110_flags))
        return bool(strict_flags), reasons or sorted(strict_flags), flags

    if preset == PolicyPreset.NO_INSCRIPTIONS:
        spam_signals = analysis.signals - {"op_return"}
        if spam_signals:
            reasons.extend(sorted(spam_signals))
        if "inscription" in analysis.signals:
            reasons.append("inscription")
        return bool(reasons), reasons, flags

    if preset == PolicyPreset.NO_OP_RETURN:
        if "op_return" in analysis.signals:
            reasons.append("op_return")
        return bool(reasons), reasons, flags

    if preset == PolicyPreset.ECONOMIC_ONLY:
        if category != "economic":
            reasons.append(category)
        if analysis.has_bip110_violation:
            reasons.extend(sorted(analysis.bip110_flags))
        if analysis.signals - {"op_return"}:
            reasons.extend(sorted(analysis.signals - {"op_return"}))
        # Deduplicate while preserving order
        seen: set[str] = set()
        unique: list[str] = []
        for r in reasons:
            if r not in seen:
                seen.add(r)
                unique.append(r)
        reasons = unique
        return bool(reasons), reasons, flags

    return False, [], flags


def simulate_policy(
    preset: PolicyPreset,
    template: dict[str, Any],
    decode_tx: Callable[[str], dict[str, Any]],
    *,
    sample_reject_limit: int = 5,
) -> PolicySimulationResult:
    """Simulate a single preset against all GBT transactions."""
    label, description = PRESET_META[preset]
    result = PolicySimulationResult(
        preset=preset,
        label=label,
        description=description,
        total_tx=0,
        analyzed_tx=0,
        rejected_tx=0,
        rejected_weight=0,
        total_weight=0,
        reject_pct_by_count=0.0,
        reject_pct_by_weight=0.0,
    )

    txs = template.get("transactions", [])
    result.total_tx = len(txs)
    if not txs:
        result.error = "Block template is empty"
        return result

    reason_counter: Counter[str] = Counter()
    rejects: list[SimulatedTxOutcome] = []

    for entry in txs:
        hex_data = entry.get("data", "")
        if not hex_data:
            continue
        try:
            tx = decode_tx(hex_data)
            if entry.get("txid"):
                tx["txid"] = entry["txid"]
            weight = int(entry.get("weight") or tx.get("weight") or 0)
            if weight and not tx.get("weight"):
                tx["weight"] = weight
        except Exception:
            continue

        result.analyzed_tx += 1
        w = int(tx.get("weight") or 0)
        result.total_weight += w

        would_reject, reasons, flags = _evaluate_preset(preset, tx)
        category = categorize_transaction(tx)

        if would_reject:
            result.rejected_tx += 1
            result.rejected_weight += w
            for r in reasons:
                reason_counter[r] += 1
            if len(rejects) < sample_reject_limit:
                rejects.append(
                    SimulatedTxOutcome(
                        txid=tx.get("txid", "?")[:16],
                        weight=w,
                        category=category,
                        would_reject=True,
                        reject_reasons=reasons,
                        flags=flags,
                    )
                )

    if result.analyzed_tx == 0:
        result.error = "Could not decode template transactions"
        return result

    result.reject_pct_by_count = (result.rejected_tx / result.analyzed_tx) * 100
    result.reject_pct_by_weight = (
        (result.rejected_weight / result.total_weight) * 100
        if result.total_weight else 0.0
    )
    result.top_reasons = reason_counter.most_common(8)
    result.sample_rejects = rejects
    return result


def simulate_policy_presets(
    template: dict[str, Any],
    decode_tx: Callable[[str], dict[str, Any]],
    presets: list[PolicyPreset] | None = None,
) -> list[PolicySimulationResult]:
    """Run all (or selected) presets against a block template."""
    if presets is None:
        presets = list(PolicyPreset)
    return [simulate_policy(p, template, decode_tx) for p in presets]


# Re-export limits for UI reference
POLICY_LIMITS = {
    "max_pushdata": MAX_PUSHDATA_SIZE,
    "max_opreturn": MAX_OPRETURN_SIZE,
}