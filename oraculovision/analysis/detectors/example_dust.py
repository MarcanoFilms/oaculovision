"""Example custom detector — dust outputs below standard relay threshold."""

from __future__ import annotations

from typing import Any

from oraculovision.analysis.detectors import DetectorResult, TxDetector
from oraculovision.analysis.script_parser import is_op_return

_DUST_BTC = 0.00000546


class DustDetector:
    """Flag non-OP_RETURN outputs below 546 sats as dust signals."""

    name = "example_dust"

    def detect(self, tx: dict[str, Any]) -> DetectorResult:
        signals: set[str] = set()
        for vout in tx.get("vout", []):
            if is_op_return(vout):
                continue
            value = float(vout.get("value", 0) or 0)
            if 0 < value < _DUST_BTC:
                signals.add("dust")
                break
        return DetectorResult(signals=signals)