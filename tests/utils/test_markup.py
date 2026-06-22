"""Markup escaping for miner tags and node strings."""

from __future__ import annotations

from textual.markup import MarkupError, to_content

from oraculovision.screens.block_detail_modal import BlockDetailModal
from oraculovision.analysis.bip110 import BlockAnalysis
from oraculovision.utils.markup import safe_markup_text


def test_safe_markup_escapes_digit_bracket_miner_tags() -> None:
    raw = "[8jSpiderPool/578/mm(J,!"
    escaped = safe_markup_text(raw)
    assert escaped.startswith("\\[8j")
    to_content(f"Miner: {escaped}")


def test_block_modal_meta_with_bracket_miner() -> None:
    block = BlockAnalysis(
        height=1,
        hash="a" * 64,
        miner_tag="[8jSpiderPool/578/mm(J,!",
        version=4,
        weight=1000,
        tx_count=10,
        bip110_signaling=False,
    )
    modal = BlockDetailModal(block)
    to_content(modal._meta_text())