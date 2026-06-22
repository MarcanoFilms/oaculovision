"""Policy simulator unit tests."""

from __future__ import annotations

from oraculovision.analysis.policies.models import PolicyPreset
from oraculovision.analysis.policies.simulator import simulate_policy


def _op_return_tx() -> dict:
    return {
        "txid": "aa" * 32,
        "vin": [{"txid": "bb" * 32, "vout": 0, "scriptSig": {"hex": ""}}],
        "vout": [
            {
                "value": 0.0,
                "n": 0,
                "scriptPubKey": {"type": "nulldata", "hex": "6a04deadbeef"},
            }
        ],
        "weight": 200,
        "vsize": 50,
    }


def test_simulate_no_op_return_rejects_op_return_tx() -> None:
    template = {
        "transactions": [
            {"txid": "aa" * 32, "data": "00", "weight": 200},
        ]
    }

    def decode(_hex: str) -> dict:
        return _op_return_tx()

    result = simulate_policy(PolicyPreset.NO_OP_RETURN, template, decode)
    assert result.rejected_tx == 1
    assert result.reject_pct_by_count == 100.0